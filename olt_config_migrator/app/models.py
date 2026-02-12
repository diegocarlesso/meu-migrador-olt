from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Vlan:
    vid: int
    name: str = ""
    kind: str = ""  # mgmt/service/...


@dataclass
class InterfaceIP:
    ifname: str
    ip: str
    prefix_or_mask: str
    vlan: Optional[int] = None


@dataclass
class Route:
    prefix: str
    next_hop: str


@dataclass
class Trunk:
    ifname: str
    tagged_vlans: List[int] = field(default_factory=list)


@dataclass
class TcontProfile:
    name: str
    dba_type: int = 3
    assured_kbps: int = 0
    max_kbps: int = 0


@dataclass
class Onu:
    slot: int
    pon: int
    onu_id: int
    sn: str = ""
    onu_type: str = ""
    name: str = ""
    upstream_kbps: int = 0
    downstream_kbps: int = 0
    upstream_assured: int = 0


@dataclass
class OnuService:
    slot: int
    pon: int
    onu_id: int
    uni_port: int = 1      # eth port index (1..n)
    svc_local_id: int = 1  # MUST be local to ONU: 1..N
    vlan: int = 0
    mode: str = "tag"      # tag/untag/translate
    pppoe_user: str = ""
    pppoe_pass: str = ""


@dataclass
class NormalizedConfig:
    vlans: List[Vlan] = field(default_factory=list)
    trunks: List[Trunk] = field(default_factory=list)
    interfaces: List[InterfaceIP] = field(default_factory=list)
    routes: List[Route] = field(default_factory=list)

    tcont_profiles: List[TcontProfile] = field(default_factory=list)
    onus: List[Onu] = field(default_factory=list)
    services: List[OnuService] = field(default_factory=list)

    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SectionColumn:
    key: str
    label: str
    editable: bool = True
    placeholder: str = ""
    col_type: str = "str"  # str/int


@dataclass
class SectionSchema:
    key: str
    title: str
    columns: List[SectionColumn]
    description: str = ""
