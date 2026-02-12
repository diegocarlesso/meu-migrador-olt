from __future__ import annotations
from typing import Any, Dict, List
from .base import VendorAdapter
from ..models import NormalizedConfig, SectionSchema, SectionColumn

class HuaweiAdapter(VendorAdapter):
    vendor_id="huawei"
    label="Huawei (placeholder)"
    default_extension=".txt"
    def parse_to_normalized(self, text: str) -> NormalizedConfig:
        return NormalizedConfig()
    def schema(self) -> List[SectionSchema]:
        return [SectionSchema("vlans","VLANs",[SectionColumn("vid","VLAN ID",True,col_type="int"),SectionColumn("name","Nome",True)])]
    def from_normalized(self, normalized: NormalizedConfig) -> Dict[str, List[Dict[str, Any]]]:
        return {"vlans":[{"vid":v.vid,"name":v.name} for v in normalized.vlans]}
    def render(self, target_data: Dict[str, List[Dict[str, Any]]], fast: Dict[str, Any] | None = None) -> str:
        return "! Huawei render (placeholder)"
