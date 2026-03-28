from dataclasses import dataclass, field
from typing import List, Dict
from .scan_item import ScanItem, format_size


@dataclass
class ScanResult:
    items: List[ScanItem] = field(default_factory=list)

    def add(self, item: ScanItem):
        self.items.append(item)

    def extend(self, items: List[ScanItem]):
        self.items.extend(items)

    @property
    def total_size(self) -> int:
        return sum(i.size_bytes for i in self.items)

    @property
    def selected_size(self) -> int:
        return sum(i.size_bytes for i in self.items if i.selected)

    @property
    def total_size_display(self) -> str:
        return format_size(self.total_size)

    @property
    def selected_size_display(self) -> str:
        return format_size(self.selected_size)

    def by_category(self) -> Dict[str, List[ScanItem]]:
        result: Dict[str, List[ScanItem]] = {}
        for item in self.items:
            result.setdefault(item.category, []).append(item)
        return result

    def by_app(self) -> Dict[str, List[ScanItem]]:
        result: Dict[str, List[ScanItem]] = {}
        for item in self.items:
            result.setdefault(item.app_name, []).append(item)
        return result

    @property
    def selected_items(self) -> List[ScanItem]:
        return [i for i in self.items if i.selected]
