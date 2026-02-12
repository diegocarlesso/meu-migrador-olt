from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class Vlan:
    vid: int
    name: str = ""
    kind: str = ""  # e.g. 'mgmt', 'service', etc.


@dataclass
class InterfaceIP:
    ifname: str
    ip: str
    prefix_or_mask: str  # '/30' or '255.255.255.0'
    vlan: Optional[int] = None


@dataclass
class Route:
    prefix: str  # '0.0.0.0/0'
    next_hop: str


@dataclass
class BandwidthProfile:
    name: str
    traffic_type: str = "internet"  # internet/management/...
    assured_kbps: Optional[int] = None
    max_kbps: Optional[int] = None


@dataclass
class ServiceVlanGroup:
    svc_id: int
    name: str
    vlan_begin: int
    vlan_end: int
    svc_type: str = "data"


@dataclass
class DbaProfile:
    prof_id: int
    name: str
    dba_type: int
    assured: Optional[int] = None
    maximum: Optional[int] = None


@dataclass
class LineProfile:
    prof_id: int
    name: str
    user_vlan: Optional[int] = None
    dba_name: str = "default1"


@dataclass
class OnuProfile:
    prof_id: int
    name: str
    eth_ports: Optional[int] = None


@dataclass
class NormalizedConfig:
    vlans: List[Vlan] = field(default_factory=list)
    interfaces: List[InterfaceIP] = field(default_factory=list)
    routes: List[Route] = field(default_factory=list)

    bandwidth_profiles: List[BandwidthProfile] = field(default_factory=list)
    service_vlans: List[ServiceVlanGroup] = field(default_factory=list)

    dba_profiles: List[DbaProfile] = field(default_factory=list)
    line_profiles: List[LineProfile] = field(default_factory=list)
    onu_profiles: List[OnuProfile] = field(default_factory=list)

    # Espaço livre para guardar dados que você ainda não normalizou:
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SectionColumn:
    key: str
    label: str
    editable: bool = True
    placeholder: str = ""
    col_type: str = "str"  # 'str', 'int'


@dataclass
class SectionSchema:
    key: str
    title: str
    columns: List[SectionColumn]
    description: str = ""
