"""
Utilitários de seleção manual de modelo/família
"""

from typing import Optional, List, Tuple

MODEL_ID_OPTIONS: List[Tuple[str, str]] = [
    ("e145", "E145"),
    ("e170", "E170"),
    ("e175", "E175"),
    ("e190", "E190"),
    ("e195", "E195"),
    ("e175_e2", "E175-E2"),
    ("e190_e2", "E190-E2"),
    ("e195_e2", "E195-E2"),
]


def normalize_model_id(model_id: Optional[str]) -> Optional[str]:
    if not model_id:
        return None
    return model_id.lower().replace("-", "_").strip()


def get_family_id_for_rules(model_id: Optional[str]) -> Optional[str]:
    """Mapeia modelo para aircraft_id esperado pelo RulesEngine."""
    mid = normalize_model_id(model_id)
    if not mid:
        return None
    if mid == "e145":
        return "e145"
    if mid in {"e170", "e175"}:
        return "e170"
    if mid in {"e190", "e195"}:
        return "e1"
    if mid in {"e175_e2", "e190_e2", "e195_e2"}:
        return "e2"
    return None


def get_model_name_for_analyzers(model_id: Optional[str]) -> Optional[str]:
    """Normaliza para o nome esperado pelos analyzers (E170, E190-E2, etc.)."""
    mid = normalize_model_id(model_id)
    mapping = {
        "e145": "E145",
        "e170": "E170",
        "e175": "E175",
        "e190": "E190",
        "e195": "E195",
        "e175_e2": "E175-E2",
        "e190_e2": "E190-E2",
        "e195_e2": "E195-E2",
    }
    return mapping.get(mid)
