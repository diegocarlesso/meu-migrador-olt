from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, List, Any
from ..models import NormalizedConfig, SectionSchema


class VendorAdapter(ABC):
    vendor_id: str
    label: str
    default_extension: str

    @abstractmethod
    def parse_to_normalized(self, text: str) -> NormalizedConfig:
        raise NotImplementedError

    @abstractmethod
    def schema(self) -> List[SectionSchema]:
        raise NotImplementedError

    @abstractmethod
    def from_normalized(self, normalized: NormalizedConfig) -> Dict[str, List[Dict[str, Any]]]:
        """Converte NormalizedConfig em 'target_data' no formato de seções/tab."""
        raise NotImplementedError

    @abstractmethod
    def render(self, target_data: Dict[str, List[Dict[str, Any]]]) -> str:
        raise NotImplementedError

    def normalize_sort(self, normalized: NormalizedConfig) -> NormalizedConfig:
        normalized.vlans.sort(key=lambda v: v.vid)
        return normalized
