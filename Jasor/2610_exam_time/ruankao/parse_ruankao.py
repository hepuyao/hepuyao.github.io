"""Parse soft-exam welcome HTML for batch options and city signup windows."""
from __future__ import annotations
import re
from typing import Any

_OPTION_RE = re.compile(
    r'<option(?P<attrs>[^>]*)\s+value="(?P<id>[^"]+)"[^>]*>(?P<name>[^<]+)</option>'
    r'|<option(?P<attrs2>[^>]*)>(?P<name2>[^<]+)</option>',
    re.IGNORECASE,
)
# Prefer simpler sequential parse:
_OPTION_SIMPLE = re.compile(
    r'<option(?P<attrs>[^>]*)value="(?P<id>[^"]+)"(?P<attrs2>[^>]*)>(?P<name>[^<]+)</option>',
    re.IGNORECASE,
)
_CITY_ROW = re.compile(
    r'<div class="layui-col-md3 col1">(?P<city>[^<]+)</div>'
    r'<div class="layui-col-md4 col2 timeW">(?P<signup>[^<]+)</div>',
    re.IGNORECASE,
)
_RANGE = re.compile(
    r'(?P<start>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})\s*~\s*(?P<end>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})'
)


def parseTaskOptions(html: str) -> list[dict[str, Any]]:
    tasks: list[dict[str, Any]] = []
    for match in _OPTION_SIMPLE.finditer(html):
        attrs = (match.group("attrs") or "") + (match.group("attrs2") or "")
        tasks.append(
            {
                "id": match.group("id").strip(),
                "name": match.group("name").strip(),
                "selected": "selected" in attrs.lower(),
            }
        )
    return tasks


def parseCitySignup(html: str, cityName: str) -> dict[str, str] | None:
    for match in _CITY_ROW.finditer(html):
        if match.group("city").strip() != cityName:
            continue
        rangeMatch = _RANGE.search(match.group("signup"))
        if rangeMatch is None:
            return None
        return {
            "signupStart": rangeMatch.group("start"),
            "signupEnd": rangeMatch.group("end"),
        }
    return None


def pickReferenceBatchName(currentBatchName: str) -> str:
    if "下半年" in currentBatchName:
        return "上半年"
    if "上半年" in currentBatchName:
        return "下半年"
    return ""
