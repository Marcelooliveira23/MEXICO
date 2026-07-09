"""
Registro simples de auditoria de análises
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any


def append_audit_log(entry: Dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    log_path = output_dir / "audit_log.jsonl"

    payload = {
        "timestamp": datetime.now().isoformat(),
        **entry,
    }

    with log_path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")
