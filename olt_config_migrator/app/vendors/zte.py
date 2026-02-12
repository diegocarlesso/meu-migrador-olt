from __future__ import annotations
from typing import Any, Dict, List, Tuple
from .base import VendorAdapter
from ..models import NormalizedConfig, Vlan, Trunk, TcontProfile, Onu, OnuService, InterfaceIP, Route, SectionSchema, SectionColumn

def _uniq_ints(vals: List[int]) -> List[int]:
    return sorted({int(v) for v in vals if int(v) > 0})

class ZTEAdapter(VendorAdapter):
    vendor_id = "zte"
    label = "ZTE (GPON - Wiki Adapter)"
    default_extension = ".txt"

    def parse_to_normalized(self, text: str) -> NormalizedConfig:
        # As destino, usamos principalmente render; parse aqui é best-effort
        n = NormalizedConfig()
        return n

    def schema(self) -> List[SectionSchema]:
        return [
            SectionSchema("vlans","VLANs",
                [SectionColumn("vid","VLAN ID",True,col_type="int"), SectionColumn("name","Nome",True), SectionColumn("kind","Tipo",False)],
                "VLANs a criar no destino."),
            SectionSchema("trunks","Trunks / Uplinks",
                [SectionColumn("ifname","Interface",True), SectionColumn("tagged","Tagged VLANs (csv ou 'ALL')",True)],
                "Se marcar 'ALL', o render aplica todas VLANs em modo trunk."),
            SectionSchema("tcont_profiles","Profiles TCONT",
                [SectionColumn("name","Nome",True), SectionColumn("dba_type","Type",True,col_type="int"),
                 SectionColumn("assured_kbps","Assured(kbps)",True,col_type="int"), SectionColumn("max_kbps","Max(kbps)",True,col_type="int")]),
            SectionSchema("interfaces","IPs / Interfaces",
                [SectionColumn("ifname","Interface",True), SectionColumn("ip","IP",True), SectionColumn("prefix_or_mask","Prefixo/Máscara",True)]),
            SectionSchema("routes","Rotas",
                [SectionColumn("prefix","Prefixo",True), SectionColumn("next_hop","Next-hop",True)]),
            SectionSchema("onus","ONUs",
                [SectionColumn("slot","Slot",True,col_type="int"), SectionColumn("pon","PON",True,col_type="int"),
                 SectionColumn("onu_id","ONU ID",True,col_type="int"), SectionColumn("sn","SN",True),
                 SectionColumn("onu_type","Type",True), SectionColumn("name","Name/Desc",True),
                 SectionColumn("upstream_kbps","Up(kbps)",True,col_type="int"), SectionColumn("upstream_assured","Assured",True,col_type="int")],
                "Cadastro das ONUs (slot/pon/onu/sn/type)."),
            SectionSchema("services","Serviços das ONUs",
                [SectionColumn("slot","Slot",True,col_type="int"), SectionColumn("pon","PON",True,col_type="int"),
                 SectionColumn("onu_id","ONU",True,col_type="int"), SectionColumn("svc_local_id","Svc#",True,col_type="int"),
                 SectionColumn("uni_port","UNI",True,col_type="int"), SectionColumn("vlan","VLAN",True,col_type="int"),
                 SectionColumn("mode","Mode(tag/untag)",True),
                 SectionColumn("pppoe_user","PPPoE user",True), SectionColumn("pppoe_pass","PPPoE pass",True)],
                "Service-port/wan-ip reiniciam por ONU. PPPoE preenchido -> gera wan-ip pppoe.")
        ]

    def from_normalized(self, normalized: NormalizedConfig) -> Dict[str, List[Dict[str, Any]]]:
        # VLANs: do normalized + VLANs usadas em services
        vlan_ids = [v.vid for v in normalized.vlans]
        vlan_ids += [s.vlan for s in normalized.services]
        vlans = [{"vid":vid,"name":"","kind":""} for vid in _uniq_ints(vlan_ids)]

        trunks = [{"ifname":t.ifname,"tagged":"ALL"} for t in normalized.trunks] or []

        # TCONT profiles
        tcont = []
        for p in normalized.tcont_profiles:
            tcont.append({"name":p.name,"dba_type":p.dba_type,"assured_kbps":p.assured_kbps,"max_kbps":p.max_kbps})
        if not tcont:
            tcont = [{"name":"U1024000K_A640","dba_type":3,"assured_kbps":640,"max_kbps":1024000}]

        onus = [{
            "slot":o.slot,"pon":o.pon,"onu_id":o.onu_id,"sn":o.sn,"onu_type":o.onu_type,"name":o.name,
            "upstream_kbps":o.upstream_kbps,"upstream_assured":o.upstream_assured
        } for o in normalized.onus]

        services = [{
            "slot":s.slot,"pon":s.pon,"onu_id":s.onu_id,"svc_local_id":s.svc_local_id,"uni_port":s.uni_port,
            "vlan":s.vlan,"mode":s.mode,"pppoe_user":s.pppoe_user,"pppoe_pass":s.pppoe_pass
        } for s in normalized.services]

        interfaces = [{"ifname":i.ifname,"ip":i.ip,"prefix_or_mask":i.prefix_or_mask} for i in normalized.interfaces]
        routes = [{"prefix":r.prefix,"next_hop":r.next_hop} for r in normalized.routes]

        return {"vlans":vlans,"trunks":trunks,"tcont_profiles":tcont,"interfaces":interfaces,"routes":routes,"onus":onus,"services":services}

    def render(self, target_data: Dict[str, List[Dict[str, Any]]], fast: Dict[str, Any] | None = None) -> str:
        fast = fast or {}
        frame = str(fast.get("frame","")).strip() or "[FRAME]"
        slot = str(fast.get("slot","")).strip() or "[SLOT]"
        pon_offset = int(fast.get("pon_offset", 0) or 0)
        vlan_offset = int(fast.get("vlan_offset", 0) or 0)
        trunk_desc = str(fast.get("trunk_desc", "")).strip()
        trunk_no_shutdown = bool(fast.get("trunk_no_shutdown", True))
        discover_enable = bool(fast.get("discover_enable", False))
        discover_new = int(fast.get("discover_new_onu", 15) or 15)
        discover_miss = int(fast.get("discover_miss_onu", 60) or 60)
        tcont_name_bridge = str(fast.get("tcont_name_bridge", "BRIDGE")).strip() or "BRIDGE"
        tcont_name_pppoe = str(fast.get("tcont_name_pppoe", "PPPOE")).strip() or "PPPOE"

        def fmt_gpon_olt(pon: int) -> str:
            return f"gpon_olt-{frame}/{slot}/{pon}"

        def fmt_gpon_onu(pon: int, onu_id: int) -> str:
            return f"gpon_onu-{frame}/{slot}/{pon}:{onu_id}"

        def fmt_vport(pon: int, onu_id: int, svc: int) -> str:
            return f"vport-{frame}/{slot}/{pon}.{onu_id}:{svc}"

        out: List[str] = []
        out.append("! Generated by OLT Config Migrator (Turbo)")
        out.append("!")

        # VLANs
        vlan_ids = []
        for v in target_data.get("vlans", []):
            vid = int(v.get("vid",0) or 0)
            if vid:
                vlan_ids.append(vid + vlan_offset)
        vlan_ids = _uniq_ints(vlan_ids)

        if vlan_ids:
            out.append("vlan database")
            out.append(" vlan list " + ",".join(str(x) for x in vlan_ids))
            out.append("$")
            for vid in vlan_ids:
                out.append(f"vlan {vid}")
                out.append("$")
            out.append("!")

        # Trunks (apply ALL or csv)
        trunks = target_data.get("trunks", [])
        apply_all = bool(fast.get("apply_all_vlans_to_trunks", True))
        for tr in trunks:
            ifname = str(tr.get("ifname","")).strip()
            if not ifname:
                continue
            tagged = str(tr.get("tagged","ALL")).strip().upper()
            out.append(f"interface {ifname}")
            if trunk_desc:
                out.append(f" description {trunk_desc}")
            if trunk_no_shutdown:
                out.append(" no shutdown")
            out.append(" switchport mode trunk")
            if apply_all or tagged == "ALL":
                if vlan_ids:
                    out.append(" switchport vlan " + ",".join(str(x) for x in vlan_ids) + " tag")
            else:
                # parse csv into ints
                ids=[]
                for p in tagged.replace(";",",").split(","):
                    p=p.strip()
                    if p.isdigit():
                        ids.append(int(p)+vlan_offset)
                ids=_uniq_ints(ids)
                if ids:
                    out.append(" switchport vlan " + ",".join(str(x) for x in ids) + " tag")
            out.append("$")
        if trunks:
            out.append("!")

        # TCONT profiles
        for p in target_data.get("tcont_profiles", []):
            name = str(p.get("name","")).strip() or "U1024000K_A640"
            dba_type = int(p.get("dba_type", 3) or 3)
            assured = int(p.get("assured_kbps", 0) or 0)
            maxbw = int(p.get("max_kbps", 0) or 0)
            out.append(f"profile tcont {name} type {dba_type} assured {assured} maximum {maxbw}")
            out.append("$")
        out.append("!")

        # IP interfaces
        for itf in target_data.get("interfaces", []):
            ifname = str(itf.get("ifname","")).strip()
            ip = str(itf.get("ip","")).strip()
            mask = str(itf.get("prefix_or_mask","")).strip()
            if not ifname or not ip:
                continue
            out.append(f"interface {ifname}")
            if mask:
                if mask.startswith("/"):
                    out.append(f" ip address {ip}{mask}")
                else:
                    out.append(f" ip address {ip} {mask}")
            else:
                out.append(f" ip address {ip}")
            out.append("$")
        if target_data.get("interfaces"):
            out.append("!")

        for r in target_data.get("routes", []):
            prefix = str(r.get("prefix","")).strip()
            nh = str(r.get("next_hop","")).strip()
            if prefix and nh:
                out.append(f"ip route {prefix} {nh}")
        if target_data.get("routes"):
            out.append("!")

        # Build ONU map for bandwidth->tcont profile
        # choose profile by matching max/assured if possible, else first
        profiles = target_data.get("tcont_profiles", []) or [{"name":"U1024000K_A640","assured_kbps":640,"max_kbps":1024000}]
        def pick_profile(up_kbps:int, assured:int) -> str:
            for p in profiles:
                if int(p.get("max_kbps",0) or 0)==up_kbps and int(p.get("assured_kbps",0) or 0)==assured:
                    return str(p.get("name"))
            return str(profiles[0].get("name"))

        # Group services by ONU
        services_by_onu: Dict[Tuple[int,int,int], List[Dict[str, Any]]] = {}
        for s in target_data.get("services", []):
            sl=int(s.get("slot",0) or 0)
            pon=int(s.get("pon",0) or 0)+pon_offset
            onu=int(s.get("onu_id",0) or 0)
            if sl<=0 or pon<=0 or onu<=0:
                continue
            s2=dict(s)
            s2["pon"]=pon
            s2["vlan"]=int(s2.get("vlan",0) or 0)+vlan_offset
            services_by_onu.setdefault((sl,pon,onu), []).append(s2)
        for k in services_by_onu:
            services_by_onu[k].sort(key=lambda x: int(x.get("svc_local_id",1) or 1))

        # ONUs render: create on gpon_olt + per onu blocks
        # First: gpon_olt blocks per PON
        onus = target_data.get("onus", [])
        # group by pon
        onus_by_pon: Dict[int, List[Dict[str, Any]]] = {}
        for o in onus:
            pon=int(o.get("pon",0) or 0)+pon_offset
            onu_id=int(o.get("onu_id",0) or 0)
            sn=str(o.get("sn","")).strip()
            ty=str(o.get("onu_type","")).strip() or "unknown"
            name=str(o.get("name","")).strip()
            up=int(o.get("upstream_kbps",0) or 0)
            assured=int(o.get("upstream_assured",0) or 0)
            if pon<=0 or onu_id<=0:
                continue
            o2={"pon":pon,"onu_id":onu_id,"sn":sn,"onu_type":ty,"name":name,"up":up,"assured":assured}
            onus_by_pon.setdefault(pon, []).append(o2)
        for pon in sorted(onus_by_pon):
            out.append(f"interface {fmt_gpon_olt(pon)}")
            for o in sorted(onus_by_pon[pon], key=lambda x: x["onu_id"]):
                # In ZTE, "onu <id> type <type> sn <sn>"
                if o["sn"]:
                    out.append(f" onu {o['onu_id']} type {o['onu_type']} sn {o['sn']}")
                else:
                    out.append(f" onu {o['onu_id']} type {o['onu_type']}")
            if discover_enable:
                out.append(f" discover-period new-onu {discover_new} miss-onu {discover_miss}")
            out.append("$")
        if onus_by_pon:
            out.append("!")

        # Per ONU detailed blocks
        for pon in sorted(onus_by_pon):
            for o in sorted(onus_by_pon[pon], key=lambda x: x["onu_id"]):
                onu_id=o["onu_id"]
                onu_if = fmt_gpon_onu(pon, onu_id)
                out.append(f"interface {onu_if}")
                if o["name"]:
                    out.append(f" description {o['name']}")
                if o["sn"]:
                    out.append(f" sn-bind enable sn {o['sn']}")
                prof = pick_profile(o["up"], o["assured"]) if o["up"] else str(profiles[0].get("name"))
                # Serviços por ONU (sempre por ONU)
                svc_list = services_by_onu.get((1, pon, onu_id), []) or services_by_onu.get((0, pon, onu_id), []) or []
                has_pppoe = any(str(x.get("pppoe_user","")).strip() for x in svc_list)
                tcont_name = tcont_name_pppoe if has_pppoe else tcont_name_bridge
                # TCONT 1
                out.append(f" tcont 1 name {tcont_name} profile {prof}")
                # Create gemport per service (or at least 1)
                if not svc_list:
                    out.append(" gemport 1 tcont 1")
                else:
                    for s in svc_list:
                        sid=int(s.get("svc_local_id",1) or 1)
                        out.append(f" gemport {sid} tcont 1")
                out.append("$")

                # vport + service-port
                if svc_list:
                    for s in svc_list:
                        sid=int(s.get("svc_local_id",1) or 1)
                        vlan=int(s.get("vlan",0) or 0)
                        if vlan<=0:
                            continue
                        out.append(f"interface {fmt_vport(pon, onu_id, sid)}")
                        out.append(f" service-port {sid} user-vlan {vlan} vlan {vlan}")
                        out.append("$")

                # pon-onu-mng services
                if svc_list:
                    out.append(f"pon-onu-mng {onu_if}")
                    for s in svc_list:
                        sid=int(s.get("svc_local_id",1) or 1)
                        vlan=int(s.get("vlan",0) or 0)
                        uni=int(s.get("uni_port",1) or 1)
                        mode=str(s.get("mode","tag")).strip().lower()
                        user=str(s.get("pppoe_user","")).strip()
                        pw=str(s.get("pppoe_pass","")).strip()
                        if vlan<=0:
                            continue
                        out.append(f" service {sid} gemport {sid} vlan {vlan}")
                        # VLAN port mode
                        if mode == "untag":
                            out.append(f" vlan port eth_0/{uni} mode untag vlan {vlan}")
                        else:
                            out.append(f" vlan port eth_0/{uni} mode tag vlan {vlan}")
                        # PPPoE: wan-ip index matches sid (per ONU)
                        if user:
                            out.append(f" wan-ip {sid} ipv4 mode pppoe username {user} password {pw} vlan-profile {vlan} host 1")
                    out.append("$")
        out.append("!")
        return "\n".join(out)
