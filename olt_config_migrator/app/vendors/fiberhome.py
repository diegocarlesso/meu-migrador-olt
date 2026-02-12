from __future__ import annotations
import re
from typing import Any, Dict, List, Tuple
from .base import VendorAdapter
from ..models import NormalizedConfig, Vlan, InterfaceIP, Route, Onu, OnuService, TcontProfile, SectionSchema, SectionColumn
from ..utils import expand_vlan_range

RX_MANAGE_VLAN = re.compile(r"^set\s+manage_vlan\s+(\d+)\s+(.+)$", re.I)
RX_VLAN_RANGE = re.compile(r"^add\s+vlan\s+vlan_begin\s+(\d+)\s+vlan_end\s+(\d+)\b", re.I)
RX_STATIC_ROUTE = re.compile(r"^add\s+static\s+route\s+destination\s+(\S+)\s+gateway\s+(\S+)\s+mask\s+(\S+)", re.I)
RX_MGMT_IP = re.compile(r"^set\s+manage\s+vlan\s+name\s+.+?\s+ip\s+(\S+)", re.I)
RX_DEBUGIP = re.compile(r"^set\s+debugip\s+(\S+)\s+mask\s+(\S+)", re.I)

# ONU auth line:
# set white phy addr FHTT04c6ba10 pas null ac add sl 1 p 5 o 26 ty 5506-04-F1
RX_ONU_AUTH = re.compile(r"^set\s+white\s+phy\s+addr\s+(\S+)\s+.*?\badd\s+sl\s+(\d+)\s+p\s+(\d+)\s+o\s+(\d+)\s+ty\s+(\S+)", re.I)

# Service VLAN mapping:
# set ep sl 1 p 1 o 11 p 1 serv 1 vlan_m tra 255 33024 4002
RX_EP_VLAN = re.compile(r"^set\s+ep\s+sl\s+(\d+)\s+p\s+(\d+)\s+o\s+([0-9,]+)\s+p\s+(\d+)\s+serv\s+(\d+)\s+vlan_m\s+(\S+)\s+\d+\s+\d+\s+([0-9,]+)", re.I)

# Bandwidth:
# set ep sl 1 pon 8 onu 47 band upstream_band 1024000 downstream_band 1024000 upstream_assured 640 upstream_fix 0
RX_EP_BAND = re.compile(r"^set\s+ep\s+sl\s+(\d+)\s+pon\s+(\d+)\s+onu\s+(\d+)\s+band\s+upstream_band\s+(\d+)\s+downstream_band\s+(\d+)\s+upstream_assured\s+(\d+)", re.I)

# PPPoE wan cfg:
# set wancfg sl 1 1 1 ind 1 ... ty r 3906 ... dsp pppoe ... acz/user key:pass ...
RX_WAN_PPPOE = re.compile(r"^set\s+wancfg\s+sl\s+(\d+)\s+(\d+)\s+(\d+)\s+ind\s+(\d+).+?\bty\s+r\s+(\d+)\b.+?\bdsp\s+pppoe\b.*?\bacz\/([^\s]+)\s+key:([^\s]+)", re.I)


def _mask_to_prefix(mask: str) -> int:
    try:
        parts = [int(x) for x in mask.split(".")]
        b = "".join(f"{p:08b}" for p in parts)
        return b.count("1")
    except Exception:
        return 24


class FiberhomeAdapter(VendorAdapter):
    vendor_id = "fiberhome"
    label = "Fiberhome (AN5516 / WOS)"
    default_extension = ".txt"

    def parse_to_normalized(self, text: str) -> NormalizedConfig:
        n = NormalizedConfig()
        lines = text.splitlines()

        # manage vlan
        for line in lines:
            m = RX_MANAGE_VLAN.match(line.strip())
            if m:
                vid = int(m.group(1))
                name = m.group(2).strip()
                n.vlans.append(Vlan(vid=vid, name=name, kind="mgmt"))
                n.extras["manage_vlan"] = {"vid": vid, "name": name}
                break

        # vlan ranges
        vlan_set = set(v.vid for v in n.vlans)
        for line in lines:
            m = RX_VLAN_RANGE.match(line.strip())
            if m:
                a, b = int(m.group(1)), int(m.group(2))
                for vid in expand_vlan_range(a, b):
                    vlan_set.add(vid)
        n.vlans = [Vlan(vid=v, name="", kind=("mgmt" if n.extras.get("manage_vlan", {}).get("vid")==v else "")) for v in sorted(vlan_set)]

        # IPs
        for line in lines:
            m = RX_MGMT_IP.match(line.strip())
            if m:
                ip = m.group(1)
                if "/" in ip:
                    a, pfx = ip.split("/", 1)
                    n.interfaces.append(InterfaceIP(ifname="mgmt", ip=a, prefix_or_mask="/" + pfx, vlan=n.extras.get("manage_vlan", {}).get("vid")))
                else:
                    n.interfaces.append(InterfaceIP(ifname="mgmt", ip=ip, prefix_or_mask="", vlan=n.extras.get("manage_vlan", {}).get("vid")))
                break
        for line in lines:
            m = RX_DEBUGIP.match(line.strip())
            if m:
                ip, mask = m.group(1), m.group(2)
                n.interfaces.append(InterfaceIP(ifname="debug", ip=ip, prefix_or_mask="/" + str(_mask_to_prefix(mask)), vlan=None))
                break

        # route
        for line in lines:
            m = RX_STATIC_ROUTE.match(line.strip())
            if m:
                dest, gw, mask = m.group(1), m.group(2), m.group(3)
                if mask == "0.0.0.0":
                    prefix = f"{dest}/0"
                else:
                    prefix = f"{dest}/{_mask_to_prefix(mask)}"
                n.routes.append(Route(prefix=prefix, next_hop=gw))
                break

        # ONUs auth
        onu_map: Dict[Tuple[int,int,int], Onu] = {}
        for line in lines:
            m = RX_ONU_AUTH.match(line.strip())
            if m:
                sn = m.group(1)
                sl = int(m.group(2))
                pon = int(m.group(3))
                onu_id = int(m.group(4))
                ty = m.group(5)
                onu = Onu(slot=sl, pon=pon, onu_id=onu_id, sn=sn, onu_type=ty)
                onu_map[(sl, pon, onu_id)] = onu

        # Bandwidth
        for line in lines:
            m = RX_EP_BAND.match(line.strip())
            if m:
                sl = int(m.group(1))
                pon = int(m.group(2))
                onu_id = int(m.group(3))
                up = int(m.group(4))
                down = int(m.group(5))
                assured = int(m.group(6))
                key = (sl, pon, onu_id)
                if key in onu_map:
                    onu_map[key].upstream_kbps = up
                    onu_map[key].downstream_kbps = down
                    onu_map[key].upstream_assured = assured

        # Services via vlan_m
        services_tmp: List[OnuService] = []
        for line in lines:
            m = RX_EP_VLAN.match(line.strip())
            if m:
                sl = int(m.group(1))
                pon = int(m.group(2))
                onu_list = [int(x) for x in m.group(3).split(",") if x.strip().isdigit()]
                uni = int(m.group(4))
                _serv = int(m.group(5))  # original serv id (ignored later)
                mode = m.group(6).lower()
                vlan_list = [int(x) for x in m.group(7).split(",") if x.strip().isdigit()]
                # align lengths: if one vlan, replicate
                if len(vlan_list) == 1 and len(onu_list) > 1:
                    vlan_list = vlan_list * len(onu_list)
                for idx, onu_id in enumerate(onu_list):
                    vlan = vlan_list[idx] if idx < len(vlan_list) else (vlan_list[-1] if vlan_list else 0)
                    if vlan:
                        services_tmp.append(OnuService(slot=sl, pon=pon, onu_id=onu_id, uni_port=uni, svc_local_id=1, vlan=vlan,
                                                       mode=("tag" if mode == "tag" else "translate" if mode == "tra" else mode)))

        # PPPoE attach
        pppoe_by_onu_vlan: Dict[Tuple[int,int,int,int], Tuple[str,str]] = {}
        for line in lines:
            m = RX_WAN_PPPOE.match(line.strip())
            if m:
                sl, pon, onu_id = int(m.group(1)), int(m.group(2)), int(m.group(3))
                ind = int(m.group(4))
                vlan = int(m.group(5))
                user = m.group(6)
                pw = m.group(7)
                pppoe_by_onu_vlan[(sl, pon, onu_id, vlan)] = (user, pw)

        # Consolidate ONUs list
        n.onus = sorted(onu_map.values(), key=lambda o: (o.slot, o.pon, o.onu_id))

        # Renumber services per ONU and attach PPPoE creds
        # group by (slot,pon,onu)
        grouped: Dict[Tuple[int,int,int], List[OnuService]] = {}
        for s in services_tmp:
            grouped.setdefault((s.slot, s.pon, s.onu_id), []).append(s)

        final_services: List[OnuService] = []
        for key, svc_list in grouped.items():
            # stable order: vlan, uni_port
            svc_list.sort(key=lambda x: (x.vlan, x.uni_port, x.mode))
            for i, s in enumerate(svc_list, start=1):
                s.svc_local_id = i
                creds = pppoe_by_onu_vlan.get((s.slot, s.pon, s.onu_id, s.vlan))
                if creds:
                    s.pppoe_user, s.pppoe_pass = creds
                final_services.append(s)

        # Also include PPPoE services that might not have appeared in vlan_m section
        existing = {(s.slot,s.pon,s.onu_id,s.vlan) for s in final_services}
        for (sl, pon, onu_id, vlan), (user, pw) in pppoe_by_onu_vlan.items():
            if (sl,pon,onu_id,vlan) not in existing:
                # append as a single service on uni 1
                svc_list = grouped.setdefault((sl,pon,onu_id), [])
                new_id = len(svc_list) + 1
                final_services.append(OnuService(slot=sl, pon=pon, onu_id=onu_id, uni_port=1, svc_local_id=new_id, vlan=vlan, mode="tag",
                                                 pppoe_user=user, pppoe_pass=pw))

        n.services = sorted(final_services, key=lambda s: (s.slot, s.pon, s.onu_id, s.svc_local_id))

        # Create TCONT profiles from bandwidth (upstream) pairs
        prof_map: Dict[Tuple[int,int], TcontProfile] = {}
        for onu in n.onus:
            if onu.upstream_kbps <= 0:
                continue
            keyp = (onu.upstream_kbps, onu.upstream_assured)
            if keyp not in prof_map:
                name = f"U{onu.upstream_kbps}K_A{onu.upstream_assured}"
                prof_map[keyp] = TcontProfile(name=name, dba_type=3, assured_kbps=onu.upstream_assured, max_kbps=onu.upstream_kbps)
        if not prof_map:
            prof_map[(1024000, 640)] = TcontProfile(name="U1024000K_A640", dba_type=3, assured_kbps=640, max_kbps=1024000)
        n.tcont_profiles = list(prof_map.values())

        return n

    def schema(self) -> List[SectionSchema]:
        # Fiberhome editor is best-effort; most people use it as source.
        return [
            SectionSchema("vlans","VLANs",[SectionColumn("vid","VLAN ID",True,col_type="int"), SectionColumn("name","Nome",True), SectionColumn("kind","Tipo",False)]),
            SectionSchema("interfaces","IPs",[SectionColumn("ifname","Interface",True), SectionColumn("vlan","VLAN",True,col_type="int"), SectionColumn("ip","IP",True), SectionColumn("prefix_or_mask","Prefixo",True)]),
            SectionSchema("routes","Rotas",[SectionColumn("prefix","Prefixo",True), SectionColumn("next_hop","Next-hop",True)]),
        ]

    def from_normalized(self, normalized: NormalizedConfig) -> Dict[str, List[Dict[str, Any]]]:
        return {
            "vlans":[{"vid":v.vid,"name":v.name,"kind":v.kind} for v in normalized.vlans],
            "interfaces":[{"ifname":i.ifname,"vlan":i.vlan or 0,"ip":i.ip,"prefix_or_mask":i.prefix_or_mask} for i in normalized.interfaces],
            "routes":[{"prefix":r.prefix,"next_hop":r.next_hop} for r in normalized.routes],
        }

    def render(self, target_data: Dict[str, List[Dict[str, Any]]], fast: Dict[str, Any] | None = None) -> str:
        # Not the main goal in this turbo build.
        out=["! Fiberhome render (best-effort) - use as source mostly"]
        for v in target_data.get("vlans", []):
            vid=int(v.get("vid",0) or 0)
            nm=str(v.get("name","")).strip()
            if vid:
                out.append(f"vlan {vid} {nm}".strip())
        return "\n".join(out)
