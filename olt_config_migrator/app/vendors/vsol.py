from __future__ import annotations

from typing import Any, Dict, List

from .base import VendorAdapter
from ..models import NormalizedConfig, SectionSchema, SectionColumn
from ..utils import compress_vlan_list


class VSolutionAdapter(VendorAdapter):
    vendor_id = "vsol"
    label = "V-Solution"
    default_extension = "cfg"

    def parse_to_normalized(self, text: str) -> NormalizedConfig:
        # Ainda não implementado como origem.
        return NormalizedConfig()

    def schema(self) -> List[SectionSchema]:
        return [
            SectionSchema(
                key="vlans",
                title="VLANs",
                description="VLANs existentes no destino (editar/ajustar).",
                columns=[
                    SectionColumn("vid", "ID", editable=True, col_type="int"),
                    SectionColumn("name", "Nome", editable=True),
                ],
            ),
            SectionSchema(
                key="trunks",
                title="Trunks/Uplinks",
                description="Interfaces de uplink para liberar VLANs tagged.",
                columns=[
                    SectionColumn("ifname", "Interface", editable=True, placeholder="Ex.: gigabitethernet 0/1"),
                    SectionColumn("tagged", "VLANs tagged", editable=True, placeholder="Ex.: ALL ou 800-808,1554"),
                    SectionColumn("pvid", "PVID", editable=True, placeholder="Ex.: 1", col_type="int"),
                ],
            ),
            SectionSchema(
                key="interface_ips",
                title="Interfaces IP (Gerência)",
                description="Endereços IP e máscara/prefixo.",
                columns=[
                    SectionColumn("ifname", "Interface", editable=True, placeholder="Ex.: interface vlan 50"),
                    SectionColumn("ip", "IP", editable=True, placeholder="Ex.: 192.168.1.2"),
                    SectionColumn("prefix_or_mask", "Máscara/Prefixo", editable=True, placeholder="Ex.: 255.255.255.0 ou /24"),
                ],
            ),
            SectionSchema(
                key="routes",
                title="Rotas",
                description="Rotas estáticas.",
                columns=[
                    SectionColumn("prefix", "Prefixo", editable=True, placeholder="Ex.: 0.0.0.0/0"),
                    SectionColumn("next_hop", "Next-hop", editable=True, placeholder="Ex.: 192.168.1.1"),
                ],
            ),
        ]

    def from_normalized(self, normalized: NormalizedConfig) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "vlans": [{"vid": v.vid, "name": v.name} for v in normalized.vlans],
            "trunks": [],
            "interface_ips": [{"ifname": i.ifname, "ip": i.ip, "prefix_or_mask": i.prefix_or_mask} for i in normalized.interfaces],
            "routes": [{"prefix": r.prefix, "next_hop": r.next_hop} for r in normalized.routes],
        }

    def render(self, target_data: Dict[str, List[Dict[str, Any]]], fast: Dict[str, Any] | None = None) -> str:
        vlans = [int(v.get("vid", 0) or 0) for v in target_data.get("vlans", []) if int(v.get("vid", 0) or 0) > 0]
        trunks = target_data.get("trunks", []) or []
        ifaces = target_data.get("interface_ips", []) or []
        routes = target_data.get("routes", []) or []

        out: List[str] = []
        out.append("! ===== V-Solution (gerado pelo OLT Config Migrator) =====")
        out.append("! OBS: ONUs/serviços ainda não estão implementados para V-Solution (somente VLANs/uplinks/IP/rotas).")
        out.append("!")

        # VLANs
        if vlans:
            for a,b in compress_vlan_list(vlans):
                if a == b:
                    out.append(f"vlan {a}")
                else:
                    out.append(f"vlan {a} - {b}")
            out.append("exit")
            out.append("!")

        # Trunks: V-Solution costuma usar 'switchport trunk vlan <vid>' repetido
        for t in trunks:
            ifname = str(t.get("ifname","")).strip()
            tagged = str(t.get("tagged","")).strip()
            pvid = int(t.get("pvid", 1) or 1)
            if not ifname:
                continue
            out.append(f"interface {ifname}")
            out.append("switchport mode trunk")
            if tagged:
                vids: List[int] = []
                if tagged.upper() == "ALL":
                    vids = vlans
                else:
                    # aceita '800-808,1554'
                    tmp = []
                    for part in tagged.replace(";",",").split(","):
                        part = part.strip()
                        if not part:
                            continue
                        if "-" in part:
                            s,e = part.split("-",1)
                            try:
                                s=int(s); e=int(e)
                                tmp.extend(list(range(min(s,e), max(s,e)+1)))
                            except:
                                pass
                        else:
                            try:
                                tmp.append(int(part))
                            except:
                                pass
                    vids = sorted(set(tmp))
                for vid in vids:
                    out.append(f"switchport trunk vlan {vid}")
            out.append(f"switchport trunk pvid vlan {pvid}")
            out.append("no shutdown")
            out.append("exit")
            out.append("!")

        # IP interfaces
        for i in ifaces:
            ifname = str(i.get("ifname","")).strip()
            ip = str(i.get("ip","")).strip()
            mask = str(i.get("prefix_or_mask","")).strip()
            if not ifname or not ip or not mask:
                continue
            out.append(f"interface {ifname}")
            out.append(f"ip address {ip} {mask}")
            out.append("no shutdown")
            out.append("exit")
            out.append("!")

        for r in routes:
            pfx = str(r.get("prefix","")).strip()
            nh = str(r.get("next_hop","")).strip()
            if pfx and nh:
                out.append(f"ip route {pfx} {nh}")

        out.append("! ===== fim =====")
        return "\n".join(out) + "\n"
