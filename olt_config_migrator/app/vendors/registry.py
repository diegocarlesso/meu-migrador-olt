from __future__ import annotations
from typing import Dict
from .base import VendorAdapter
from .fiberhome import FiberhomeAdapter
from .zte import ZTEAdapter
from .datacom import DatacomAdapter
from .parks import ParksAdapter
from .vsol import VSolutionAdapter
from .huawei import HuaweiAdapter

def get_registry() -> Dict[str, VendorAdapter]:
    adapters = [
        FiberhomeAdapter(),
        ZTEAdapter(),
        DatacomAdapter(),
        ParksAdapter(),
        VSolutionAdapter(),
        HuaweiAdapter(),
    ]
    return {a.vendor_id: a for a in adapters}
