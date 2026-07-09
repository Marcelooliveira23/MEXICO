"""
Cache simples de análises para melhorar performance
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple
from collections import OrderedDict


@dataclass
class CacheEntry:
    """Entrada de cache"""
    result_text: str
    analysis_obj: Any
    metadata: Dict[str, Any]


class AnalysisCache:
    """LRU cache para resultados de análise"""

    def __init__(self, max_size: int = 20):
        self.max_size = max_size
        self._cache: "OrderedDict[Tuple, CacheEntry]" = OrderedDict()

    def get(self, key: Tuple) -> Optional[CacheEntry]:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, key: Tuple, entry: CacheEntry) -> None:
        self._cache[key] = entry
        self._cache.move_to_end(key)
        if len(self._cache) > self.max_size:
            self._cache.popitem(last=False)

    def clear(self) -> None:
        self._cache.clear()
