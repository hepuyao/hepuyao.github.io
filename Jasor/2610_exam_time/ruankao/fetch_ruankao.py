#!/usr/bin/env python3
"""Fetch ruankao welcome page and write data.json for Beijing/Tianjin."""
from __future__ import annotations
import json
import ssl
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

from parse_ruankao import parseCitySignup, parseTaskOptions, pickReferenceBatchName

try:
    import certifi

    _SSL_CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    _SSL_CTX = ssl.create_default_context()

SOURCE = "https://bm.ruankao.org.cn/sign/welcome"
CITIES = ("北京", "天津")
OUT = Path(__file__).resolve().parent / "data.json"
TZ8 = timezone(timedelta(hours=8))
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def fetchHtml(taskId: str | None = None) -> str:
    data = None
    headers = {"User-Agent": UA, "Accept": "text/html"}
    if taskId:
        data = urllib.parse.urlencode(
            {"seltaskid": taskId, "taskid": taskId}
        ).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    req = urllib.request.Request(SOURCE, data=data, headers=headers, method="POST" if data else "GET")
    with urllib.request.urlopen(req, timeout=30, context=_SSL_CTX) as resp:
        return resp.read().decode("utf-8", errors="replace")


def toIso(localText: str) -> str:
    dt = datetime.strptime(localText, "%Y-%m-%d %H:%M").replace(tzinfo=TZ8)
    return dt.isoformat(timespec="minutes")


def cityPayload(html: str, city: str) -> dict | None:
    row = parseCitySignup(html, city)
    if row is None:
        return None
    return {
        "signupStart": toIso(row["signupStart"]),
        "signupEnd": toIso(row["signupEnd"]),
        "estimated": False,
    }


def buildData() -> dict:
    htmlLatest = fetchHtml()
    tasks = parseTaskOptions(htmlLatest)
    if not tasks:
        raise RuntimeError("no task options found")
    latest = tasks[0]
    htmlLatest = fetchHtml(latest["id"])
    cities: dict = {}
    for city in CITIES:
        payload = cityPayload(htmlLatest, city)
        if payload is not None:
            cities[city] = payload
    halfKey = pickReferenceBatchName(latest["name"])
    reference: dict = {}
    if halfKey:
        refTask = next((t for t in tasks if halfKey in t["name"]), None)
        if refTask is not None:
            htmlRef = fetchHtml(refTask["id"])
            for city in CITIES:
                row = parseCitySignup(htmlRef, city)
                if row is None:
                    continue
                reference[city] = {
                    "signupStart": toIso(row["signupStart"]),
                    "signupEnd": toIso(row["signupEnd"]),
                    "batchName": refTask["name"],
                }
    return {
        "updatedAt": datetime.now(TZ8).isoformat(timespec="seconds"),
        "source": SOURCE,
        "batch": {"id": latest["id"], "name": latest["name"]},
        "cities": cities,
        "reference": reference,
    }


def main() -> int:
    try:
        data = buildData()
    except (urllib.error.URLError, TimeoutError, RuntimeError, ValueError) as err:
        print(f"fetch failed: {err}", file=sys.stderr)
        return 1
    if "北京" not in data["cities"] and "天津" not in data["cities"]:
        print("fetch failed: no Beijing/Tianjin rows", file=sys.stderr)
        return 1
    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
