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
        raise NotImplementedError

    @abstractmethod
    def render(self, target_data: Dict[str, List[Dict[str, Any]]], fast: Dict[str, Any] | None = None) -> str:
        raise NotImplementedError
