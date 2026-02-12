from __future__ import annotations

from typing import Any, Dict, List

from .base import VendorAdapter
from ..models import NormalizedConfig, SectionSchema, SectionColumn
from ..utils import format_vlan_ranges


class HuaweiAdapter(VendorAdapter):
    vendor_id = "huawei"
    label = "Huawei"
    default_extension = "txt"

    def parse_to_normalized(self, text: str) -> NormalizedConfig:
        # TODO: Implementar parser Huawei como origem.
        return NormalizedConfig()

    def schema(self) -> List[SectionSchema]:
        return [
            SectionSchema(
                key="vlans",
                title="VLANs",
                description="VLANs no destino (editar/ajustar).",
                columns=[
                    SectionColumn("vid", "ID", editable=True, col_type="int"),
                    SectionColumn("name", "Nome", editable=True),
                ],
            ),
            SectionSchema(
                key="trunks",
                title="Trunks/Uplinks",
                description="Uplinks para liberar VLANs tagged.",
                columns=[
                    SectionColumn("ifname", "Interface", editable=True, placeholder="Ex.: eth-trunk 1 / xgei 0/1/0"),
                    SectionColumn("tagged", "VLANs tagged", editable=True, placeholder="Ex.: ALL ou 800-808,1554"),
                ],
            ),
            SectionSchema(
                key="interface_ips",
                title="Interfaces IP (Gerência)",
                description="Endereços IP e máscara/prefixo.",
                columns=[
                    SectionColumn("ifname", "Interface", editable=True, placeholder="Ex.: vlanif 50"),
                    SectionColumn("ip", "IP", editable=True, placeholder="Ex.: 192.168.1.2"),
                    SectionColumn("prefix_or_mask", "Máscara/Prefixo", editable=True, placeholder="Ex.: 255.255.255.0 ou 24"),
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
        out.append("# ===== Huawei (gerado pelo OLT Config Migrator) =====")
        out.append("# OBS: ONUs/serviços ainda não estão implementados para Huawei (somente VLANs/uplinks/IP/rotas).")
        out.append("#")

        if vlans:
            # Em Huawei normalmente você cria vlan batch. Mantemos simples.
            out.append(f"vlan batch {format_vlan_ranges(vlans, sep=' ', range_sep=' to ', space=True)}")
            out.append("#")

        for t in trunks:
            ifname = str(t.get("ifname","")).strip()
            tagged = str(t.get("tagged","")).strip()
            if not ifname:
                continue
            out.append(f"interface {ifname}")
            if tagged:
                if tagged.upper() == "ALL":
                    tagged = format_vlan_ranges(vlans, sep=' ', range_sep=' to ', space=True) if vlans else ""
                if tagged:
                    out.append(f" port trunk allow-pass vlan {tagged}")
            out.append(" quit")
            out.append("#")

        for i in ifaces:
            ifname = str(i.get("ifname","")).strip()
            ip = str(i.get("ip","")).strip()
            mask = str(i.get("prefix_or_mask","")).strip()
            if not ifname or not ip or not mask:
                continue
            out.append(f"interface {ifname}")
            # Huawei usa máscara ou prefixo; aqui aceitamos o que vier
            out.append(f" ip address {ip} {mask}")
            out.append(" quit")
            out.append("#")

        for r in routes:
            pfx = str(r.get("prefix","")).strip()
            nh = str(r.get("next_hop","")).strip()
            if pfx and nh:
                # Se vier em CIDR, Huawei costuma aceitar ip route-static <dest> <mask> <nexthop>
                out.append(f"ip route-static {pfx} {nh}")

        out.append("# ===== fim =====")
        return "\n".join(out) + "\n"
