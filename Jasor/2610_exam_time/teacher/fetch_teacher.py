#!/usr/bin/env python3
"""Fetch TJ teacher job announcements (cate 3013) into data.json."""
from __future__ import annotations

import json
import re
import ssl
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from html import unescape
from pathlib import Path

from parse_teacher import (
    extractPhysicsFromSheetRows,
    extractPhysicsFromText,
    extractSignupFromText,
    extractSignupFromTimeList,
    matchTitle,
    parseWebListGgLinks,
    sheetRowsToText,
)

try:
    import certifi

    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl.create_default_context()

try:
    import xlrd
except ImportError:
    xlrd = None  # type: ignore[assignment,misc]

LIST_API = "https://www.tjtalents.com.cn/app/article/newArticleAction!getzxList.do"
CONTENT_BASE = "https://www.tjtalents.com.cn/app/article/content"
SOURCE = "https://www.tjtalents.com.cn/app/article/list/3013.shtml"
SEARCH_WORDS = ["中学", "教育系统", "教育局", "高层次教育", "教育体育局"]
CATE_ID = "3013"
LIMIT = 20
LIST_PAGE_CAP = 12
RETRIES = 4
RETRY_DELAY_SEC = 1.5
OUT = Path(__file__).resolve().parent / "data.json"
TZ8 = timezone(timedelta(hours=8))
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")
_SHEET_URL_RE = re.compile(
    r"(https?://[^\s\"'<>]+\.(?:xls|xlsx)(?:\?[^\s\"'<>]*)?)",
    re.IGNORECASE,
)
_REL_SHEET_RE = re.compile(
    r"['\"]([^'\"]+\.(?:xls|xlsx)(?:\?[^'\"]*)?)['\"]",
    re.IGNORECASE,
)


def _httpRequest(
    url: str,
    *,
    data: bytes | None = None,
    headers: dict[str, str] | None = None,
) -> bytes:
    hdrs = {"User-Agent": UA}
    if headers:
        hdrs.update(headers)
    method = "POST" if data is not None else "GET"
    req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    last_err: BaseException | None = None
    for attempt in range(RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=45, context=_SSL_CTX) as resp:
                return resp.read()
        except (urllib.error.URLError, TimeoutError, OSError) as err:
            last_err = err
            if attempt + 1 < RETRIES:
                time.sleep(RETRY_DELAY_SEC * (attempt + 1))
    raise last_err  # type: ignore[misc]


def fetchListPage(searchWord: str, currentPage: int) -> dict:
    body = urllib.parse.urlencode(
        {
            "currentPage": currentPage,
            "cate_id": CATE_ID,
            "searchstr": searchWord,
        }
    ).encode("utf-8")
    raw = _httpRequest(
        LIST_API,
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json, text/plain, */*",
        },
    )
    return json.loads(raw.decode("utf-8", errors="replace"))


def collectListArticles() -> tuple[list[dict], bool]:
    """Return merged raw articles and whether any list request succeeded."""
    byZxid: dict[str, dict] = {}
    anyOk = False
    for word in SEARCH_WORDS:
        pageTotal = 1
        for page in range(1, LIST_PAGE_CAP + 1):
            if page > pageTotal:
                break
            try:
                payload = fetchListPage(word, page)
            except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError):
                continue
            anyOk = True
            pageTotal = int(payload.get("pageTotal") or 1)
            for row in payload.get("articlelist") or []:
                zxid = str(row.get("zxid") or "")
                if zxid:
                    byZxid[zxid] = row
    return list(byZxid.values()), anyOk


def pickRecentMatched(articles: list[dict]) -> list[dict]:
    matched = [a for a in articles if matchTitle(str(a.get("zxmc") or ""))]
    matched.sort(key=lambda a: str(a.get("fbsj") or ""), reverse=True)
    return matched[:LIMIT]


def articleUrl(row: dict) -> str:
    link = (row.get("zx_link") or "").strip()
    if link:
        return link
    aid = (row.get("article_id") or "").strip()
    if aid:
        return f"{CONTENT_BASE}/{aid}.shtml"
    return SOURCE


def htmlToText(html: str) -> str:
    text = _TAG_RE.sub(" ", html or "")
    text = unescape(text)
    return _WS_RE.sub(" ", text).strip()


def resolveSheetUrls(html: str, pageUrl: str) -> list[str]:
    found: list[str] = []
    seen: set[str] = set()
    for m in _SHEET_URL_RE.finditer(html or ""):
        u = m.group(1)
        if u not in seen:
            seen.add(u)
            found.append(u)
    base = urllib.parse.urlparse(pageUrl)
    for m in _REL_SHEET_RE.finditer(html or ""):
        rel = m.group(1)
        if rel.startswith("http://") or rel.startswith("https://"):
            abs_u = rel
        else:
            abs_u = urllib.parse.urljoin(pageUrl, rel)
        if abs_u not in seen:
            seen.add(abs_u)
            found.append(abs_u)
    return found


def readXlsRows(data: bytes) -> list[list[str]]:
    if xlrd is None:
        raise RuntimeError("xlrd not installed")
    book = xlrd.open_workbook(file_contents=data)
    rows: list[list[str]] = []
    for sheet in book.sheets():
        for rx in range(sheet.nrows):
            row: list[str] = []
            for cx in range(sheet.ncols):
                val = sheet.cell_value(rx, cx)
                if isinstance(val, float) and val == int(val):
                    row.append(str(int(val)))
                else:
                    row.append(str(val).strip())
            rows.append(row)
    return rows


def readXlsxRows(data: bytes) -> list[list[str]]:
    try:
        import openpyxl
    except ImportError:
        raise RuntimeError("openpyxl not installed")
    from io import BytesIO

    wb = openpyxl.load_workbook(BytesIO(data), read_only=True, data_only=True)
    rows: list[list[str]] = []
    for sheet in wb.worksheets:
        for row in sheet.iter_rows(values_only=True):
            rows.append(["" if c is None else str(c).strip() for c in row])
    wb.close()
    return rows


def mergePhysics(sheetPhys: dict, textPhys: dict) -> dict:
    posts: list[dict] = []
    seen: set[str] = set()
    for block in (sheetPhys, textPhys):
        for post in block.get("posts") or []:
            name = str(post.get("name") or "").strip()
            if not name or name in seen:
                continue
            seen.add(name)
            posts.append(post)
    return {"found": bool(posts), "posts": posts}


def preferSignup(primary: dict, secondary: dict) -> dict:
    if primary.get("found"):
        return primary
    if secondary.get("found"):
        return secondary
    return primary


def isWebListUrl(url: str) -> bool:
    return "weblist.aspx" in (url or "").lower()


def webListHandlerUrl(listUrl: str) -> str:
    """Map WebList.aspx?... to sibling BeifangHdl.ashx."""
    cleaned = (listUrl or "").replace("wsbm_ggfb//", "wsbm_ggfb/")
    parsed = urllib.parse.urlparse(cleaned)
    path = parsed.path
    if path.lower().endswith("weblist.aspx"):
        path = path[: -len("WebList.aspx")] + "BeifangHdl.ashx"
        # preserve original casing of directory; force handler name
        dirPart = parsed.path.rsplit("/", 1)[0]
        path = f"{dirPart}/BeifangHdl.ashx"
    return urllib.parse.urlunparse(
        (parsed.scheme, parsed.netloc, path, "", "", "")
    )


def webListId(listUrl: str) -> str:
    qs = urllib.parse.parse_qs(urllib.parse.urlparse(listUrl).query)
    vals = qs.get("id") or []
    return vals[0] if vals else ""


def expandWebList(listUrl: str, notes: list[str]) -> tuple[list[str], list[str], dict]:
    """Return (sheetUrls, pageUrls, signupFromTimeline) for a WebList shell."""
    handler = webListHandlerUrl(listUrl)
    listId = webListId(listUrl)
    sheets: list[str] = []
    pages: list[str] = []
    signup = {"found": False, "raw": None, "start": None, "end": None}
    if not listId:
        notes.append("WebList missing id query")
        return sheets, pages, signup
    try:
        ggBody = urllib.parse.urlencode(
            {"fun": "GetGgList", "id": listId, "pagesize": "50", "page": "1"}
        ).encode("utf-8")
        ggHtml = _httpRequest(
            handler,
            data=ggBody,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ).decode("utf-8", errors="replace")
        links = parseWebListGgLinks(ggHtml)
        for href in links.get("sheets") or []:
            sheets.append(urllib.parse.urljoin(handler, href))
        for href in links.get("pages") or []:
            pages.append(urllib.parse.urljoin(handler, href))
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        notes.append(f"WebList GetGgList failed: {err}")
    try:
        timeBody = urllib.parse.urlencode(
            {"fun": "GetTimeList", "id": listId}
        ).encode("utf-8")
        raw = _httpRequest(
            handler,
            data=timeBody,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ).decode("utf-8", errors="replace")
        payload = json.loads(raw)
        sjx = payload.get("sjxData") or ""
        if isinstance(sjx, list):
            sjx = json.dumps(sjx, ensure_ascii=False)
        signup = extractSignupFromTimeList(str(sjx))
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError, TypeError) as err:
        notes.append(f"WebList GetTimeList failed: {err}")
    return sheets, pages, signup


def loadSheetRows(sheetUrl: str, notes: list[str]) -> list[list[str]]:
    low = sheetUrl.lower()
    try:
        blob = _httpRequest(sheetUrl, headers={"Accept": "*/*"})
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        notes.append(f"attachment download failed ({sheetUrl}): {err}")
        return []
    try:
        if ".xlsx" in low:
            return readXlsxRows(blob)
        return readXlsRows(blob)
    except RuntimeError as err:
        notes.append(str(err))
        return []
    except Exception as err:  # noqa: BLE001 — keep batch alive
        notes.append(f"attachment parse failed ({sheetUrl}): {err}")
        return []


def fetchItem(row: dict) -> dict:
    title = str(row.get("zxmc") or "").strip()
    publishedAt = str(row.get("fbsj") or row.get("fbrq") or "").strip()
    url = articleUrl(row)
    item: dict = {
        "title": title,
        "publishedAt": publishedAt,
        "url": url,
        "titleMatchedBy": matchTitle(title),
        "physics": {"found": False, "posts": []},
        "signup": {"found": False, "raw": None, "start": None, "end": None},
        "parseNotes": [],
    }
    try:
        htmlBytes = _httpRequest(url, headers={"Accept": "text/html"})
        html = htmlBytes.decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError) as err:
        item["parseNotes"].append(f"detail fetch failed: {err}")
        return item
    pageTextParts: list[str] = [htmlToText(html)]
    sheetUrls = resolveSheetUrls(html, url)
    timelineSignup = {"found": False, "raw": None, "start": None, "end": None}
    if isWebListUrl(url):
        extraSheets, pageUrls, timelineSignup = expandWebList(url, item["parseNotes"])
        for s in extraSheets:
            if s not in sheetUrls:
                sheetUrls.append(s)
        for pageUrl in pageUrls[:5]:
            try:
                pageHtml = _httpRequest(pageUrl, headers={"Accept": "text/html"}).decode(
                    "utf-8", errors="replace"
                )
                pageTextParts.append(htmlToText(pageHtml))
                for s in resolveSheetUrls(pageHtml, pageUrl):
                    if s not in sheetUrls:
                        sheetUrls.append(s)
            except (urllib.error.URLError, TimeoutError, OSError) as err:
                item["parseNotes"].append(f"WebPage fetch failed ({pageUrl}): {err}")
    sheetRows: list[list[str]] = []
    sheetTextParts: list[str] = []
    for sheetUrl in sheetUrls:
        rows = loadSheetRows(sheetUrl, item["parseNotes"])
        if not rows:
            continue
        sheetRows.extend(rows)
        sheetTextParts.append(sheetRowsToText(rows))
    # Prefer sheet rows for physics; only scan page HTML text (not raw sheet dump)
    # to avoid major-list false positives like 物理化学.
    pageOnlyText = " ".join(pageTextParts)
    combinedText = " ".join([pageOnlyText, *sheetTextParts])
    sheetPhys = extractPhysicsFromSheetRows(sheetRows)
    textPhys = extractPhysicsFromText(pageOnlyText)
    item["physics"] = mergePhysics(sheetPhys, textPhys)
    textSignup = extractSignupFromText(combinedText)
    item["signup"] = preferSignup(timelineSignup, textSignup)
    return item


def buildData() -> dict:
    articles, anyListOk = collectListArticles()
    if not anyListOk:
        raise RuntimeError("list API failed for all search words")
    picked = pickRecentMatched(articles)
    if not picked:
        raise RuntimeError("no title-matched listings")
    items = [fetchItem(row) for row in picked]
    return {
        "updatedAt": datetime.now(TZ8).isoformat(timespec="seconds"),
        "source": SOURCE,
        "items": items,
    }


def main() -> int:
    try:
        data = buildData()
    except (urllib.error.URLError, TimeoutError, OSError, RuntimeError, ValueError) as err:
        print(f"fetch failed: {err}", file=sys.stderr)
        return 1
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(data['items'])} items)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
