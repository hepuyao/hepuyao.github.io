"""Pure parsers for Tianjin teacher job listing titles and announcement text."""

from __future__ import annotations

import re
from datetime import datetime, timezone, timedelta

TITLE_KEYWORDS: list[str] = [
    "中学",
    "教育系统",
    "教育局",
    "高层次教育",
    "教育体育局",
]

_PHYSICS_CONTEXT = re.compile(
    r"[^\s，,、；;。]{0,12}物理[^\s，,、；;。]{0,12}(?:教师|专技|学科)"
    r"|(?:教师|专技|学科)[^\s，,、；;。]{0,12}物理[^\s，,、；;。]{0,12}",
)
_SIGNUP_PHRASE = re.compile(r"(?:网上)?报名时间|网上报名|报名起止|报名日期")
_SIGNUP_WINDOW = 120
_CN_DATE = re.compile(
    r"(\d{4})年(\d{1,2})月(\d{1,2})日(?:\s*(\d{1,2}):(\d{2}))?",
)
_ISO_DATE = re.compile(
    r"(\d{4})-(\d{1,2})-(\d{1,2})(?:[T\s](\d{1,2}):(\d{2}))?",
)
_TZ_CN = timezone(timedelta(hours=8))


def matchTitle(title: str) -> list[str]:
    t = title or ""
    hits = [k for k in TITLE_KEYWORDS if k in t]
    if "幼儿园" in t and not hits:
        return []
    return hits


def _normalizePhysicsName(fragment: str) -> str:
    name = fragment.strip(" ，,、；;。（）()")
    return name if name else fragment.strip()


def extractPhysicsFromText(text: str) -> dict:
    body = text or ""
    seen: set[str] = set()
    posts: list[dict] = []
    for match in _PHYSICS_CONTEXT.finditer(body):
        name = _normalizePhysicsName(match.group(0))
        if name and name not in seen:
            seen.add(name)
            posts.append({"name": name})
    return {"found": bool(posts), "posts": posts}


def sheetRowsToText(rows: list[list[str]]) -> str:
    parts: list[str] = []
    for row in rows or []:
        parts.extend(cell for cell in row if cell)
    return " ".join(parts)


def _isPhysicsJobCell(cell: str) -> bool:
    c = cell or ""
    if "物理" not in c:
        return False
    # Exclude chemistry/materials phrases that only mention 物理 as part of another major.
    if re.search(r"物理化学|化学物理|高分子化学与物理|材料物理", c) and not re.search(
        r"物理教师|物理岗|物理学科教师|初高中物理|高中物理岗|中学物理",
        c,
    ):
        return False
    return bool(
        re.search(
            r"物理教师|物理岗|物理学科|初高中物理|高中物理|中学物理|从事[^，。]{0,8}物理",
            c,
        )
        or ("物理" in c and "专技" in c and "化学" not in c)
    )


def _rowHasPhysicsTeacherContext(row: list[str]) -> bool:
    return any(_isPhysicsJobCell(cell or "") for cell in row)


def _pickPhysicsNameFromRow(row: list[str]) -> str:
    ranked: list[tuple[int, int, str]] = []
    for cell in row:
        c = cell or ""
        if not _isPhysicsJobCell(c):
            continue
        name = _normalizePhysicsName(c.split("\n")[0][:40])
        if not name:
            continue
        # Prefer explicit job titles over duty descriptions / major lists.
        if re.search(r"物理教师|物理岗", name):
            rank = 0
        elif "从事" in name:
            rank = 2
        else:
            rank = 1
        ranked.append((rank, len(name), name))
    if not ranked:
        return ""
    ranked.sort()
    return ranked[0][2]


def extractPhysicsFromSheetRows(rows: list[list[str]]) -> dict:
    posts: list[dict] = []
    seen: set[str] = set()
    for row in rows or []:
        if not row or not _rowHasPhysicsTeacherContext(row):
            continue
        joined = " ".join(cell or "" for cell in row)
        name = _pickPhysicsNameFromRow(row)
        if not name or name in seen:
            continue
        seen.add(name)
        post: dict = {"name": name}
        # Prefer a small integer headcount cell (1-99), skip long serials.
        for cell in row:
            c = (cell or "").strip()
            if re.fullmatch(r"\d{1,2}(?:\.0+)?", c):
                post["count"] = str(int(float(c)))
                break
        for cell in row:
            c = cell or ""
            if ("中学" in c or "学校" in c) and len(c) <= 40:
                post["school"] = c.strip()
                break
        if "教师资格" in joined:
            m = re.search(r"[^，,、；;。]{0,30}教师资格[^，,、；;。]{0,30}", joined)
            if m:
                post["qualificationHint"] = m.group(0).strip()
        posts.append(post)
    return {"found": bool(posts), "posts": posts}


def _toIsoCn(y: str, mo: str, d: str, h: str | None, mi: str | None) -> str:
    hour = int(h) if h is not None else 0
    minute = int(mi) if mi is not None else 0
    dt = datetime(int(y), int(mo), int(d), hour, minute, tzinfo=_TZ_CN)
    return dt.isoformat(timespec="minutes")


def _parseDatesFromFragment(fragment: str) -> list[str]:
    out: list[str] = []
    for m in _CN_DATE.finditer(fragment):
        out.append(_toIsoCn(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)))
    for m in _ISO_DATE.finditer(fragment):
        out.append(_toIsoCn(m.group(1), m.group(2), m.group(3), m.group(4), m.group(5)))
    return out


def extractSignupFromText(text: str) -> dict:
    body = text or ""
    for match in _SIGNUP_PHRASE.finditer(body):
        fragment = body[match.start() : match.start() + _SIGNUP_WINDOW]
        dates = _parseDatesFromFragment(fragment)
        if not dates:
            continue
        raw = fragment.strip()
        if len(raw) > 80:
            raw = raw[:80]
        start = dates[0] if len(dates) >= 1 else None
        end = dates[1] if len(dates) >= 2 else None
        return {"found": True, "raw": raw, "start": start, "end": end}
    return {"found": False, "raw": None, "start": None, "end": None}


_WEBLIST_OPEN_RE = re.compile(
    r"win_open\('([^']+)'\)",
    re.IGNORECASE,
)
_TIMELINE_SIGNUP_RE = re.compile(
    r"name:\s*'报名时间'\s*,\s*kdate:\s*'([^']*)'\s*,\s*zdate:\s*'([^']*)'",
)


def parseWebListGgLinks(html: str) -> dict[str, list[str]]:
    """Parse BeifangHdl GetGgList HTML for plan sheets and detail pages."""
    sheets: list[str] = []
    pages: list[str] = []
    seenSheets: set[str] = set()
    seenPages: set[str] = set()
    for match in _WEBLIST_OPEN_RE.finditer(html or ""):
        href = match.group(1).strip()
        low = href.lower()
        isSheet = (
            low.endswith(".xlsx")
            or ".xlsx?" in low
            or low.endswith(".xls")
            or ".xls?" in low
        )
        if isSheet:
            if href not in seenSheets:
                seenSheets.add(href)
                sheets.append(href)
        elif "webpage.aspx" in low or low.endswith(".shtml"):
            if href not in seenPages:
                seenPages.add(href)
                pages.append(href)
    return {"sheets": sheets, "pages": pages}


def extractSignupFromTimeList(sjxData: str) -> dict:
    """Parse BeifangHdl GetTimeList sjxData string for 报名时间 window."""
    body = sjxData or ""
    match = _TIMELINE_SIGNUP_RE.search(body)
    if match is None:
        return {"found": False, "raw": None, "start": None, "end": None}
    kdate = match.group(1).replace("&nbsp;", " ").strip()
    zdate = match.group(2).replace("&nbsp;", " ").strip()
    raw = f"报名时间：{kdate} 至 {zdate}".strip()
    startDates = _parseDatesFromFragment(kdate)
    endDates = _parseDatesFromFragment(zdate)
    return {
        "found": True,
        "raw": raw[:80],
        "start": startDates[0] if startDates else None,
        "end": endDates[0] if endDates else None,
    }
