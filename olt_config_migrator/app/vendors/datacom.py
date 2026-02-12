from __future__ import annotations
import re
from typing import Any, Dict, List
from .base import VendorAdapter
from ..models import NormalizedConfig, Vlan, Route, InterfaceIP, SectionSchema, SectionColumn
from ..utils import expand_vlan_range

RX_VLAN = re.compile(r"\bvlan\s+(\d+)(?:\s*-\s*(\d+))?", re.I)
RX_IP = re.compile(r"ipv4\s+address\s+(\S+)\s*$", re.I)
RX_ROUTE = re.compile(r"(0\.0\.0\.0/0)\s+next-hop\s+(\S+)", re.I)

class DatacomAdapter(VendorAdapter):
    vendor_id="datacom"
    label="Datacom (DM4xxx) — best-effort"
    default_extension=".txt"

    def parse_to_normalized(self, text: str) -> NormalizedConfig:
        n=NormalizedConfig()
        vlan_set=set()
        for line in text.splitlines():
            m=RX_VLAN.search(line)
            if m:
                a=int(m.group(1))
                b=int(m.group(2)) if m.group(2) else a
                for v in expand_vlan_range(a,b):
                    vlan_set.add(v)
        n.vlans=[Vlan(vid=v) for v in sorted(vlan_set)]

        for line in text.splitlines():
            m=RX_ROUTE.search(line)
            if m:
                n.routes.append(Route(prefix=m.group(1), next_hop=m.group(2)))
                break
        return n

    def schema(self) -> List[SectionSchema]:
        return [
            SectionSchema("vlans","VLANs",[SectionColumn("vid","VLAN ID",True,col_type="int"),SectionColumn("name","Nome",True)]),
            SectionSchema("routes","Rotas",[SectionColumn("prefix","Prefixo",True),SectionColumn("next_hop","Next-hop",True)]),
        ]

    def from_normalized(self, normalized: NormalizedConfig) -> Dict[str, List[Dict[str, Any]]]:
        return {"vlans":[{"vid":v.vid,"name":v.name} for v in normalized.vlans],
                "routes":[{"prefix":r.prefix,"next_hop":r.next_hop} for r in normalized.routes]}

    def render(self, target_data: Dict[str, List[Dict[str, Any]]], fast: Dict[str, Any] | None = None) -> str:
        out=["! Datacom render (best-effort placeholder)"]
        return "\n".join(out)
