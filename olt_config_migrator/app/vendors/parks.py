from __future__ import annotations

from typing import Any, Dict, List

from .base import VendorAdapter
from ..models import NormalizedConfig, SectionSchema, SectionColumn
from ..utils import format_vlan_ranges


class ParksAdapter(VendorAdapter):
    vendor_id = "parks"
    label = "Parks"
    default_extension = "txt"

    def parse_to_normalized(self, text: str) -> NormalizedConfig:
        # Ainda não implementado como origem (por enquanto a origem principal é Fiberhome).
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
                    SectionColumn("ifname", "Interface", editable=True, placeholder="Ex.: giga-ethernet1/0"),
                    SectionColumn("tagged", "VLANs tagged", editable=True, placeholder="Ex.: ALL ou 800-808,1554"),
                ],
            ),
            SectionSchema(
                key="interface_ips",
                title="Interfaces IP (Gerência)",
                description="Endereços IP e máscara/prefixo.",
                columns=[
                    SectionColumn("ifname", "Interface", editable=True, placeholder="Ex.: vlan50 / mgmt"),
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
        fast = fast or {}
        vlans = [int(v.get("vid", 0) or 0) for v in target_data.get("vlans", []) if int(v.get("vid", 0) or 0) > 0]
        trunks = target_data.get("trunks", []) or []
        ifaces = target_data.get("interface_ips", []) or []
        routes = target_data.get("routes", []) or []

        out: List[str] = []
        out.append("! ===== Parks (gerado pelo OLT Config Migrator) =====")
        out.append("! OBS: ONUs/serviços ainda não estão implementados para Parks (somente VLANs/uplinks/IP/rotas).")
        out.append("!")

        # VLAN database (quebra em linhas para não ficar gigante)
        if vlans:
            out.append("vlan database")
            # Parks costuma aceitar lista separada por vírgula. Usamos ranges para reduzir tamanho.
            vlan_str = format_vlan_ranges(vlans, sep=",", range_sep="-", space=False)
            # quebra por comprimento (bem conservador)
            chunk: List[str] = []
            cur = ""
            for part in vlan_str.split(","):
                if not cur:
                    cur = part
                elif len(cur) + 1 + len(part) <= 220:
                    cur += "," + part
                else:
                    chunk.append(cur)
                    cur = part
            if cur:
                chunk.append(cur)
            for c in chunk:
                out.append(f" vlan {c}")
            out.append("exit")
            out.append("!")

        # Trunks
        for t in trunks:
            ifname = str(t.get("ifname", "")).strip()
            tagged = str(t.get("tagged", "")).strip()
            if not ifname:
                continue
            out.append(f"interface {ifname}")
            out.append(" switchport mode trunk")
            if tagged:
                if tagged.upper() == "ALL":
                    tagged = format_vlan_ranges(vlans, sep=",", range_sep="-", space=False) if vlans else ""
                if tagged:
                    out.append(f" switchport trunk allowed vlan {tagged}")
            out.append(" no shutdown")
            out.append("exit")
            out.append("!")

        # IP interfaces
        for i in ifaces:
            ifname = str(i.get("ifname", "")).strip()
            ip = str(i.get("ip", "")).strip()
            mask = str(i.get("prefix_or_mask", "")).strip()
            if not ifname or not ip or not mask:
                continue
            out.append(f"interface {ifname}")
            out.append(f" ip address {ip} {mask}")
            out.append(" no shutdown")
            out.append("exit")
            out.append("!")

        # Routes
        for r in routes:
            pfx = str(r.get("prefix", "")).strip()
            nh = str(r.get("next_hop", "")).strip()
            if pfx and nh:
                out.append(f"ip route {pfx} {nh}")

        out.append("! ===== fim =====")
        return "\n".join(out) + "\n"
