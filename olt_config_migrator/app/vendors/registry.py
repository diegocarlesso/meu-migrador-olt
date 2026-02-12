from __future__ import annotations
from typing import Dict
from .base import VendorAdapter
from .parks import ParksAdapter
from .vsol import VSolutionAdapter
from .fiberhome import FiberhomeAdapter
from .zte import ZTEAdapter


def get_registry() -> Dict[str, VendorAdapter]:
    adapters = [
        ParksAdapter(),
        VSolutionAdapter(),
        FiberhomeAdapter(),
        ZTEAdapter(),
    ]
    return {a.vendor_id: a for a in adapters}
