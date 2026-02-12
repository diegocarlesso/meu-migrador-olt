from __future__ import annotations
import re
import ipaddress
from typing import Any, Dict, List, Optional
from .base import VendorAdapter
from ..models import (
    NormalizedConfig, Vlan, ServiceVlanGroup, InterfaceIP, Route,
    SectionSchema, SectionColumn
)
from ..utils import expand_vlan_range


class FiberhomeAdapter(VendorAdapter):
    vendor_id = "fiberhome"
    label = "Fiberhome (AN5516)"
    default_extension = ".txt"

    def parse_to_normalized(self, text: str) -> NormalizedConfig:
        n = NormalizedConfig()
        lines = text.splitlines()

        # manage_vlan
        for line in lines:
            m = re.match(r"set\s+manage_vlan\s+(\d+)\s+(.+)$", line.strip(), re.I)
            if m:
                vid = int(m.group(1))
                name = m.group(2).strip()
                n.vlans.append(Vlan(vid=vid, name=name, kind="mgmt"))
                n.extras["manage_vlan"] = {"vid": vid, "name": name}
                break

        # add vlan ranges
        vlan_set = set()
        for line in lines:
            m = re.match(r"add\s+vlan\s+vlan_begin\s+(\d+)\s+vlan_end\s+(\d+)\b", line.strip(), re.I)
            if m:
                a, b = int(m.group(1)), int(m.group(2))
                vlan_set.update(expand_vlan_range(a, b))
        for vid in sorted(vlan_set):
            # evita duplicar manage vlan
            if not any(v.vid == vid for v in n.vlans):
                n.vlans.append(Vlan(vid=vid))

        # service_vlan objects
        svc: Dict[int, ServiceVlanGroup] = {}
        for line in lines:
            l = line.strip()
            m = re.match(r"create\s+service_vlan\s+(\d+)", l, re.I)
            if m:
                sid = int(m.group(1))
                svc[sid] = ServiceVlanGroup(svc_id=sid, name=f"svc_{sid}", vlan_begin=0, vlan_end=0)
                continue
            m2 = re.match(r"set\s+service_vlan\s+(\d+)\s+(.+?)\s+type\s+(\S+)", l, re.I)
            if m2:
                sid = int(m2.group(1))
                if sid in svc:
                    svc[sid].name = m2.group(2).strip()
                    svc[sid].svc_type = m2.group(3).strip()
                continue
            m3 = re.match(r"set\s+service_vlan\s+(\d+)\s+vlan_begin\s+(\d+)\s+vlan_end\s+(\d+)", l, re.I)
            if m3:
                sid = int(m3.group(1))
                if sid in svc:
                    svc[sid].vlan_begin = int(m3.group(2))
                    svc[sid].vlan_end = int(m3.group(3))
                continue

        
        n.service_vlans = list(sorted(svc.values(), key=lambda x: x.svc_id))

        # --- IPs (gerência / debug) ---
        manage = n.extras.get("manage_vlan", {}) or {}
        manage_vid = manage.get("vid")
        # Ex.: 'set manage vlan name GERENCIA ip 10.16.39.2/24'
        # ou   'set manage vlan name GERENCIA ip 10.16.39.2 mask 255.255.255.0'
        for line in lines:
            l = line.strip()
            m = re.match(r"set\s+manage\s+vlan\s+name\s+(.+?)\s+ip\s+(\d+\.\d+\.\d+\.\d+)(?:/(\d+))?(?:\s+mask\s+(\d+\.\d+\.\d+\.\d+))?\s*$", l, re.I)
            if m:
                ip = m.group(2)
                prefix = m.group(3)
                mask = m.group(4)
                tail = ""
                if prefix:
                    tail = "/" + prefix
                elif mask:
                    tail = mask
                ifname = f"vlan{manage_vid}" if manage_vid else "mgmt"
                n.interfaces.append(InterfaceIP(ifname=ifname, vlan=manage_vid, ip=ip, prefix_or_mask=tail))
                break

        # Ex.: 'set debugip 10.25.1.1 mask 255.255.255.224'
        for line in lines:
            l = line.strip()
            m = re.match(r"set\s+debugip\s+(\d+\.\d+\.\d+\.\d+)\s+mask\s+(\d+\.\d+\.\d+\.\d+)\s*$", l, re.I)
            if m:
                n.interfaces.append(InterfaceIP(ifname="debug", vlan=None, ip=m.group(1), prefix_or_mask=m.group(2)))
                break

        # --- Rotas estáticas ---
        # Ex.: 'add static route destination 0.0.0.0 gateway 10.16.39.1 mask 0.0.0.0'
        for line in lines:
            l = line.strip()
            m = re.match(r"add\s+static\s+route\s+destination\s+(\d+\.\d+\.\d+\.\d+)\s+gateway\s+(\d+\.\d+\.\d+\.\d+)(?:\s+mask\s+(\d+\.\d+\.\d+\.\d+))?\s*$", l, re.I)
            if m:
                dst = m.group(1)
                gw = m.group(2)
                mask = m.group(3)
                if mask:
                    try:
                        plen = ipaddress.IPv4Network((dst, mask), strict=False).prefixlen
                        prefix = f"{dst}/{plen}"
                    except Exception:
                        prefix = f"{dst}/{mask}"
                else:
                    prefix = dst
                n.routes.append(Route(prefix=prefix, next_hop=gw))

        return self.normalize_sort(n)


    def schema(self) -> List[SectionSchema]:
        return [
            SectionSchema(
                key="manage_vlan",
                title="VLAN de Gerência",
                description="Fiberhome usa um objeto 'manage_vlan'.",
                columns=[
                    SectionColumn("vid", "VLAN ID", editable=True, col_type="int"),
                    SectionColumn("name", "Nome", editable=True),
                ],
            ),
            SectionSchema(
                key="service_vlans",
                title="Service VLANs",
                description="Objetos service_vlan (id, nome, range).",
                columns=[
                    SectionColumn("svc_id", "Service ID", editable=False, col_type="int"),
                    SectionColumn("name", "Nome", editable=True),
                    SectionColumn("svc_type", "Tipo", editable=True),
                    SectionColumn("vlan_begin", "VLAN Begin", editable=True, col_type="int"),
                    SectionColumn("vlan_end", "VLAN End", editable=True, col_type="int"),
                ],
            ),
        ]

    def from_normalized(self, normalized: NormalizedConfig) -> Dict[str, List[Dict[str, Any]]]:
        data: Dict[str, List[Dict[str, Any]]] = {s.key: [] for s in self.schema()}

        # manage vlan
        mv = normalized.extras.get("manage_vlan")
        if mv:
            data["manage_vlan"] = [{"vid": int(mv.get("vid", 4000)), "name": str(mv.get("name", "GERENCIA"))}]
        else:
            # tenta achar uma vlan marcada como mgmt
            mg = next((v for v in normalized.vlans if v.kind == "mgmt"), None)
            data["manage_vlan"] = [{"vid": (mg.vid if mg else 4000), "name": (mg.name if mg else "GERENCIA")}]

        # service vlans: se vier vazio, cria 1 por VLAN (best-effort)
        if normalized.service_vlans:
            data["service_vlans"] = [{
                "svc_id": sv.svc_id,
                "name": sv.name,
                "svc_type": sv.svc_type,
                "vlan_begin": sv.vlan_begin,
                "vlan_end": sv.vlan_end,
            } for sv in normalized.service_vlans]
        else:
            base_id = 101
            rows = []
            for i, v in enumerate(sorted(normalized.vlans, key=lambda x: x.vid)):
                if v.kind == "mgmt":
                    continue
                rows.append({
                    "svc_id": base_id + i,
                    "name": (v.name or f"VLAN{v.vid}"),
                    "svc_type": "data",
                    "vlan_begin": v.vid,
                    "vlan_end": v.vid,
                })
            data["service_vlans"] = rows

        return data

    def render(self, target_data: Dict[str, List[Dict[str, Any]]]) -> str:
        out: List[str] = []
        out.append("! Generated by OLT Config Migrator")
        out.append("!")

        mv = (target_data.get("manage_vlan") or [{}])[0]
        vid = int(mv.get("vid", 4000) or 4000)
        name = str(mv.get("name", "GERENCIA")).strip() or "GERENCIA"
        out.append(f"set manage_vlan {vid} {name}")
        out.append("!")

        for row in target_data.get("service_vlans", []):
            sid = int(row.get("svc_id", 0) or 0)
            nm = str(row.get("name", "")).strip() or f"svc_{sid}"
            tp = str(row.get("svc_type", "data")).strip() or "data"
            vb = int(row.get("vlan_begin", 0) or 0)
            ve = int(row.get("vlan_end", 0) or 0)
            if sid <= 0:
                continue
            out.append(f"create service_vlan {sid}")
            out.append(f"set service_vlan {sid} {nm} type {tp}")
            out.append(f"set service_vlan {sid} vlan_begin {vb} vlan_end {ve}")
            out.append("!")

        return "\n".join(out)
