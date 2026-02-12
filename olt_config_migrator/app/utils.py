from __future__ import annotations
import re
from typing import List, Tuple


def read_text_smart(path: str) -> str:
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(path, "r", errors="ignore") as f:
        return f.read()


def parse_vlan_list(token: str) -> List[int]:
    out: List[int] = []
    for part in re.split(r"[\s,]+", token.strip()):
        if not part:
            continue
        if part.isdigit():
            out.append(int(part))
    return sorted(set(out))


def expand_vlan_range(a: int, b: int) -> List[int]:
    if a > b:
        a, b = b, a
    return list(range(a, b + 1))


def maybe_prefix_or_mask(ip_line: str) -> Tuple[str, str]:
    m = re.search(r"ip\s+address\s+(\S+?)(?:\s+(\S+))?$", ip_line.strip(), re.I)
    if not m:
        return "", ""
    ip = m.group(1)
    tail = m.group(2) or ""
    if "/" in ip and not tail:
        ip, prefix = ip.split("/", 1)
        return ip, "/" + prefix
    return ip, tail
