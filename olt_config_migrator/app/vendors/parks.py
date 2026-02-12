from __future__ import annotations
import re
from typing import Any, Dict, List
from .base import VendorAdapter
from ..models import (
    NormalizedConfig, Vlan, InterfaceIP, Route, BandwidthProfile,
    SectionSchema, SectionColumn
)
from ..utils import parse_vlan_list


class ParksAdapter(VendorAdapter):
    vendor_id = "parks"
    label = "Parks"
    default_extension = ".txt"

    def parse_to_normalized(self, text: str) -> NormalizedConfig:
        n = NormalizedConfig()
        lines = text.splitlines()

        # VLAN database
        in_vlan_db = False
        vlan_ids: List[int] = []
        vlan_names: Dict[int, str] = {}
        for line in lines:
            l = line.strip()
            if l.lower() == "vlan database":
                in_vlan_db = True
                continue
            if in_vlan_db:
                if l.startswith("!"):
                    in_vlan_db = False
                    continue
                m = re.match(r"vlan\s+([0-9,]+)\s*$", l, re.I)
                if m:
                    vlan_ids.extend(parse_vlan_list(m.group(1)))
                    continue
                m2 = re.match(r"vlan\s+(\d+)\s+(.+)$", l, re.I)
                if m2:
                    vid = int(m2.group(1))
                    vlan_ids.append(vid)
                    vlan_names[vid] = m2.group(2).strip()
                    continue

        for vid in sorted(set(vlan_ids)):
            n.vlans.append(Vlan(vid=vid, name=vlan_names.get(vid, "")))

        # Interfaces + IP
        current_if = None
        for line in lines:
            if m := re.match(r"interface\s+(\S+)", line.strip(), re.I):
                current_if = m.group(1)
                continue
            if current_if:
                if m2 := re.search(r"ip\s+address\s+(\S+)", line.strip(), re.I):
                    ip = m2.group(1)
                    if "/" in ip:
                        ip_addr, prefix = ip.split("/", 1)
                        n.interfaces.append(InterfaceIP(ifname=current_if, ip=ip_addr, prefix_or_mask="/" + prefix))
                    else:
                        # fallback
                        n.interfaces.append(InterfaceIP(ifname=current_if, ip=ip, prefix_or_mask=""))
                if line.strip().startswith("!"):
                    current_if = None

        # Routes
        for line in lines:
            m = re.match(r"ip\s+route\s+(\S+)\s+(\S+)", line.strip(), re.I)
            if m:
                n.routes.append(Route(prefix=m.group(1), next_hop=m.group(2)))

        # Bandwidth profiles
        cur_name = None
        for i, line in enumerate(lines):
            m = re.match(r"gpon\s+profile\s+bandwidth\s+(.+)$", line.strip(), re.I)
            if m:
                cur_name = m.group(1).strip()
                continue
            if cur_name:
                m2 = re.match(r"traffic-type\s+(\S+)\s+(.*)$", line.strip(), re.I)
                if m2:
                    traffic = m2.group(1)
                    rest = m2.group(2)
                    assured = None
                    maxbw = None
                    m_ass = re.search(r"assured-bandwidth\s+(\d+)", rest, re.I)
                    m_max = re.search(r"maximum-bandwidth\s+(\d+)", rest, re.I)
                    if m_ass:
                        assured = int(m_ass.group(1))
                    if m_max:
                        maxbw = int(m_max.group(1))
                    n.bandwidth_profiles.append(BandwidthProfile(
                        name=cur_name, traffic_type=traffic, assured_kbps=assured, max_kbps=maxbw
                    ))
                if line.strip().startswith("!"):
                    cur_name = None

        return self.normalize_sort(n)

    def schema(self) -> List[SectionSchema]:
        return [
            SectionSchema(
                key="vlans",
                title="VLANs",
                description="VLAN database + nomes (quando existir).",
                columns=[
                    SectionColumn("vid", "VLAN ID", editable=True, col_type="int"),
                    SectionColumn("name", "Nome", editable=True),
                    SectionColumn("kind", "Tipo", editable=False),
                ],
            ),
            SectionSchema(
                key="bandwidth_profiles",
                title="Perfis de Banda (GPON)",
                columns=[
                    SectionColumn("name", "Nome", editable=True),
                    SectionColumn("traffic_type", "Traffic-Type", editable=True),
                    SectionColumn("assured_kbps", "Assured (kbps)", editable=True, col_type="int"),
                    SectionColumn("max_kbps", "Max (kbps)", editable=True, col_type="int"),
                ],
            ),
            SectionSchema(
                key="interfaces",
                title="IPs / Interfaces",
                columns=[
                    SectionColumn("ifname", "Interface", editable=False),
                    SectionColumn("vlan", "VLAN", editable=True, col_type="int"),
                    SectionColumn("ip", "IP", editable=True),
                    SectionColumn("prefix_or_mask", "Prefixo/Máscara", editable=True),
                ],
            ),
            SectionSchema(
                key="routes",
                title="Rotas",
                columns=[
                    SectionColumn("prefix", "Prefixo", editable=True),
                    SectionColumn("next_hop", "Next-hop", editable=True),
                ],
            ),
        ]

    def from_normalized(self, normalized: NormalizedConfig) -> Dict[str, List[Dict[str, Any]]]:
        data: Dict[str, List[Dict[str, Any]]] = {s.key: [] for s in self.schema()}

        data["vlans"] = [{"vid": v.vid, "name": v.name, "kind": v.kind} for v in normalized.vlans]

        if normalized.bandwidth_profiles:
            data["bandwidth_profiles"] = [{
                "name": p.name,
                "traffic_type": p.traffic_type,
                "assured_kbps": p.assured_kbps or 0,
                "max_kbps": p.max_kbps or 0,
            } for p in normalized.bandwidth_profiles]
        else:
            data["bandwidth_profiles"] = [{
                "name": "Perfil_Internet",
                "traffic_type": "internet",
                "assured_kbps": 0,
                "max_kbps": 1024000,
            }]

        data["interfaces"] = [{
            "ifname": i.ifname,
            "vlan": i.vlan or 0,
            "ip": i.ip,
            "prefix_or_mask": i.prefix_or_mask,
        } for i in normalized.interfaces]

        data["routes"] = [{"prefix": r.prefix, "next_hop": r.next_hop} for r in normalized.routes]

        return data

    def render(self, target_data: Dict[str, List[Dict[str, Any]]]) -> str:
        out: List[str] = []
        out.append("! Generated by OLT Config Migrator")
        out.append("!")

        # VLAN database
        vlans = target_data.get("vlans", [])
        vlan_ids = [int(v.get("vid", 0)) for v in vlans if int(v.get("vid", 0)) > 0]
        if vlan_ids:
            out.append("vlan database")
            out.append(" vlan " + ",".join(str(x) for x in sorted(set(vlan_ids))))
            # named vlans
            for v in vlans:
                vid = int(v.get("vid", 0))
                name = str(v.get("name", "")).strip()
                if vid and name:
                    out.append(f" vlan {vid} {name}")
            out.append("!")
        else:
            out.append("! (no VLANs defined)")

        # Bandwidth profiles
        for p in target_data.get("bandwidth_profiles", []):
            name = str(p.get("name", "")).strip() or "Perfil"
            traffic = str(p.get("traffic_type", "internet")).strip() or "internet"
            assured = int(p.get("assured_kbps", 0) or 0)
            maxbw = int(p.get("max_kbps", 0) or 0)
            out.append(f"gpon profile bandwidth {name}")
            if assured > 0:
                out.append(f" traffic-type {traffic} assured-bandwidth {assured} maximum-bandwidth {maxbw}")
            else:
                out.append(f" traffic-type {traffic} maximum-bandwidth {maxbw}")
            out.append("!")

        # Interfaces (apenas o bloco IP, best-effort)
        for itf in target_data.get("interfaces", []):
            ifname = str(itf.get("ifname", "")).strip()
            ip = str(itf.get("ip", "")).strip()
            pref = str(itf.get("prefix_or_mask", "")).strip()
            vlan = int(itf.get("vlan", 0) or 0)
            if not ifname or not ip:
                continue
            out.append(f"interface {ifname}")
            if pref.startswith("/"):
                out.append(f" ip address {ip}{pref}")
            elif pref:
                out.append(f" ip address {ip} {pref}")
            else:
                out.append(f" ip address {ip}")
            out.append(" no shutdown")
            out.append("!")

        # Routes
        for r in target_data.get("routes", []):
            prefix = str(r.get("prefix", "")).strip()
            nh = str(r.get("next_hop", "")).strip()
            if prefix and nh:
                out.append(f"ip route {prefix} {nh}")

        out.append("!")
        return "\n".join(out)
