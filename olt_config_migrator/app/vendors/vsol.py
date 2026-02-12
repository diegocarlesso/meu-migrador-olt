from __future__ import annotations
import re
from typing import Any, Dict, List, Optional
from .base import VendorAdapter
from ..models import (
    NormalizedConfig, Vlan, InterfaceIP, Route,
    DbaProfile, LineProfile, OnuProfile,
    SectionSchema, SectionColumn
)
from ..utils import expand_vlan_range, maybe_prefix_or_mask


class VSolutionAdapter(VendorAdapter):
    vendor_id = "vsol"
    label = "V-Solution"
    default_extension = ".cfg"

    def parse_to_normalized(self, text: str) -> NormalizedConfig:
        n = NormalizedConfig()
        lines = text.splitlines()

        # VLANs (vlan X) e (vlan A - B)
        vlan_set = set()
        for line in lines:
            l = line.strip()
            m = re.match(r"vlan\s+(\d+)\s*-\s*(\d+)\s*$", l, re.I)
            if m:
                a, b = int(m.group(1)), int(m.group(2))
                vlan_set.update(expand_vlan_range(a, b))
                continue
            m2 = re.match(r"vlan\s+(\d+)\s*$", l, re.I)
            if m2:
                vlan_set.add(int(m2.group(1)))

        for vid in sorted(vlan_set):
            n.vlans.append(Vlan(vid=vid))

        # Interfaces e IP
        cur_if: Optional[str] = None
        cur_vlan: Optional[int] = None
        for line in lines:
            l = line.strip()
            m = re.match(r"interface\s+(\S+)", l, re.I)
            if m:
                cur_if = m.group(1)
                cur_vlan = None
                if cur_if.lower() == "aux":
                    cur_vlan = None
                elif cur_if.lower().startswith("vlan"):
                    try:
                        cur_vlan = int(cur_if.split("vlan", 1)[1])
                    except Exception:
                        cur_vlan = None
                continue

            if cur_if and l.lower().startswith("ip address"):
                ip, tail = maybe_prefix_or_mask(l)
                if ip:
                    n.interfaces.append(InterfaceIP(ifname=cur_if, vlan=cur_vlan, ip=ip, prefix_or_mask=tail))
            if l.lower() == "exit":
                cur_if = None
                cur_vlan = None

        # Routes
        for line in lines:
            m = re.match(r"ip\s+route\s+(\S+)\s+(\S+)", line.strip(), re.I)
            if m:
                n.routes.append(Route(prefix=m.group(1), next_hop=m.group(2)))

        # DBA profiles
        cur_dba: Optional[DbaProfile] = None
        for line in lines:
            l = line.rstrip()
            m = re.match(r"profile\s+dba\s+id\s+(\d+)\s+name\s+(.+)$", l.strip(), re.I)
            if m:
                cur_dba = DbaProfile(
                    prof_id=int(m.group(1)),
                    name=m.group(2).strip(),
                    dba_type=3,
                    assured=None,
                    maximum=None,
                )
                n.dba_profiles.append(cur_dba)
                continue
            if cur_dba:
                m2 = re.match(r"type\s+(\d+)(?:\s+assured\s+(\d+))?(?:\s+maximum\s+(\d+))?", l.strip(), re.I)
                if m2:
                    cur_dba.dba_type = int(m2.group(1))
                    if m2.group(2):
                        cur_dba.assured = int(m2.group(2))
                    if m2.group(3):
                        cur_dba.maximum = int(m2.group(3))
                if l.strip().lower() == "exit":
                    cur_dba = None

        # Line profiles (pega user VLAN se existir)
        cur_line: Optional[LineProfile] = None
        for line in lines:
            l = line.rstrip()
            m = re.match(r"profile\s+line\s+id\s+(\d+)\s+name\s+(.+)$", l.strip(), re.I)
            if m:
                cur_line = LineProfile(prof_id=int(m.group(1)), name=m.group(2).strip())
                n.line_profiles.append(cur_line)
                continue
            if cur_line:
                m2 = re.search(r"service-port\s+\d+\s+gemport\s+\d+\s+uservlan\s+\S+\s+vlan\s+(\d+)", l, re.I)
                if m2:
                    cur_line.user_vlan = int(m2.group(1))
                if l.strip().lower() == "exit":
                    cur_line = None

        # ONU profiles
        cur_onu: Optional[OnuProfile] = None
        for line in lines:
            l = line.strip()
            m = re.match(r"profile\s+onu\s+id\s+(\d+)\s+name\s+(.+)$", l, re.I)
            if m:
                cur_onu = OnuProfile(prof_id=int(m.group(1)), name=m.group(2).strip())
                n.onu_profiles.append(cur_onu)
                continue
            if cur_onu:
                m2 = re.match(r"port-num\s+eth\s+(\d+)", l, re.I)
                if m2:
                    cur_onu.eth_ports = int(m2.group(1))
                if l.lower() == "exit":
                    cur_onu = None

        return self.normalize_sort(n)

    def schema(self) -> List[SectionSchema]:
        return [
            SectionSchema(
                key="vlans",
                title="VLANs",
                columns=[
                    SectionColumn("vid", "VLAN ID", editable=True, col_type="int"),
                    SectionColumn("name", "Nome", editable=True),
                    SectionColumn("kind", "Tipo", editable=False),
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
            SectionSchema(
                key="dba_profiles",
                title="Perfis DBA",
                columns=[
                    SectionColumn("prof_id", "ID", editable=True, col_type="int"),
                    SectionColumn("name", "Nome", editable=True),
                    SectionColumn("dba_type", "Type", editable=True, col_type="int"),
                    SectionColumn("assured", "Assured", editable=True, col_type="int"),
                    SectionColumn("maximum", "Maximum", editable=True, col_type="int"),
                ],
            ),
            SectionSchema(
                key="line_profiles",
                title="Line Profiles",
                columns=[
                    SectionColumn("prof_id", "ID", editable=True, col_type="int"),
                    SectionColumn("name", "Nome", editable=True),
                    SectionColumn("dba_name", "DBA", editable=True),
                    SectionColumn("user_vlan", "User VLAN", editable=True, col_type="int"),
                ],
            ),
            SectionSchema(
                key="onu_profiles",
                title="ONU Profiles",
                columns=[
                    SectionColumn("prof_id", "ID", editable=True, col_type="int"),
                    SectionColumn("name", "Nome", editable=True),
                    SectionColumn("eth_ports", "ETH ports", editable=True, col_type="int"),
                ],
            ),
        ]

    def from_normalized(self, normalized: NormalizedConfig) -> Dict[str, List[Dict[str, Any]]]:
        data: Dict[str, List[Dict[str, Any]]] = {s.key: [] for s in self.schema()}

        data["vlans"] = [{"vid": v.vid, "name": v.name, "kind": v.kind} for v in normalized.vlans]

        # Interfaces: tenta manter; se vier sem ifname, cria interface vlan 800
        if normalized.interfaces:
            data["interfaces"] = [{
                "ifname": i.ifname,
                "vlan": i.vlan or 0,
                "ip": i.ip,
                "prefix_or_mask": i.prefix_or_mask,
            } for i in normalized.interfaces]
        else:
            data["interfaces"] = [{"ifname": "vlan800", "vlan": 800, "ip": "10.0.0.2", "prefix_or_mask": "/30"}]

        data["routes"] = [{"prefix": r.prefix, "next_hop": r.next_hop} for r in normalized.routes] or [
            {"prefix": "0.0.0.0/0", "next_hop": "10.0.0.1"}
        ]

        # DBA: se não houver, cria um default1
        if normalized.dba_profiles:
            data["dba_profiles"] = [{
                "prof_id": p.prof_id,
                "name": p.name,
                "dba_type": p.dba_type,
                "assured": p.assured or 0,
                "maximum": p.maximum or 0,
            } for p in normalized.dba_profiles]
        else:
            data["dba_profiles"] = [{
                "prof_id": 511,
                "name": "default1",
                "dba_type": 3,
                "assured": 1024,
                "maximum": 1024000,
            }]

        data["line_profiles"] = [{
            "prof_id": lp.prof_id,
            "name": lp.name,
            "dba_name": lp.dba_name,
            "user_vlan": lp.user_vlan or 0,
        } for lp in normalized.line_profiles] or [{
            "prof_id": 1,
            "name": "line_pon1",
            "dba_name": "default1",
            "user_vlan": (normalized.vlans[0].vid if normalized.vlans else 0),
        }]

        data["onu_profiles"] = [{
            "prof_id": op.prof_id,
            "name": op.name,
            "eth_ports": op.eth_ports or 0,
        } for op in normalized.onu_profiles] or [{
            "prof_id": 1,
            "name": "onu_profile_1",
            "eth_ports": 4,
        }]

        return data

    def render(self, target_data: Dict[str, List[Dict[str, Any]]]) -> str:
        out: List[str] = []
        out.append("! Generated by OLT Config Migrator")
        out.append("!")

        # VLANs
        for v in sorted(target_data.get("vlans", []), key=lambda x: int(x.get("vid", 0) or 0)):
            vid = int(v.get("vid", 0) or 0)
            if vid > 0:
                out.append(f"vlan {vid}")
                out.append("exit")
        out.append("!")

        # Interfaces
        for itf in target_data.get("interfaces", []):
            ifname = str(itf.get("ifname", "")).strip()
            ip = str(itf.get("ip", "")).strip()
            pref = str(itf.get("prefix_or_mask", "")).strip()
            if not ifname or not ip:
                continue
            out.append(f"interface {ifname}")
            if pref:
                if pref.startswith("/"):
                    out.append(f"ip address {ip}{pref}")
                else:
                    out.append(f"ip address {ip} {pref}")
            else:
                out.append(f"ip address {ip}")
            out.append("exit")
        out.append("!")

        # Routes
        for r in target_data.get("routes", []):
            prefix = str(r.get("prefix", "")).strip()
            nh = str(r.get("next_hop", "")).strip()
            if prefix and nh:
                out.append(f"ip route {prefix} {nh}")
        out.append("!")

        # DBA profiles
        for p in sorted(target_data.get("dba_profiles", []), key=lambda x: int(x.get("prof_id", 0) or 0)):
            pid = int(p.get("prof_id", 0) or 0)
            name = str(p.get("name", "")).strip() or f"dba_{pid}"
            dba_type = int(p.get("dba_type", 3) or 3)
            assured = int(p.get("assured", 0) or 0)
            maximum = int(p.get("maximum", 0) or 0)
            out.append(f"profile dba id {pid} name {name}")
            if assured > 0:
                out.append(f"type {dba_type} assured {assured} maximum {maximum}")
            else:
                out.append(f"type {dba_type} maximum {maximum}")
            out.append("exit")
            out.append("!")

        # Line profiles (template simples)
        for lp in sorted(target_data.get("line_profiles", []), key=lambda x: int(x.get("prof_id", 0) or 0)):
            pid = int(lp.get("prof_id", 0) or 0)
            name = str(lp.get("name", "")).strip() or f"line_{pid}"
            dba_name = str(lp.get("dba_name", "default1")).strip() or "default1"
            user_vlan = int(lp.get("user_vlan", 0) or 0)
            out.append(f"profile line id {pid} name {name}")
            out.append(f"  tcont 1 name tcont-1 dba {dba_name}")
            out.append("    gemport 1 tcont 1 gemport_name gem_1")
            out.append("      service ser_1 gemport 1 untag ethuni 1")
            if user_vlan > 0:
                out.append(f"      service-port 1 gemport 1 uservlan untag vlan {user_vlan}")
            out.append("commit")
            out.append("exit")
            out.append("!")

        # ONU profiles (template simples)
        for op in sorted(target_data.get("onu_profiles", []), key=lambda x: int(x.get("prof_id", 0) or 0)):
            pid = int(op.get("prof_id", 0) or 0)
            name = str(op.get("name", "")).strip() or f"onu_{pid}"
            eth_ports = int(op.get("eth_ports", 0) or 0)
            out.append(f"profile onu id {pid} name {name}")
            out.append(f"description {name}")
            if eth_ports > 0:
                out.append(f"port-num eth {eth_ports}")
            out.append("service-ability N:1 yes 1:P yes 1:M yes")
            out.append("commit")
            out.append("exit")
            out.append("!")

        return "\n".join(out)
