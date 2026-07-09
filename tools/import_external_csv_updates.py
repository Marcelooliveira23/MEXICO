#!/usr/bin/env python3
"""Incremental CSV import for logbook (falhas) and LRU data.

Usage:
  python tools/import_external_csv_updates.py \
    --mirep "C:\\Users\\MEEOLIVE\\Downloads\\mirep.csv" \
    --lru "C:\\Users\\MEEOLIVE\\Downloads\\Copia de Instalacion y remocion (1).csv"
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
import unicodedata
from datetime import date, datetime
from typing import Dict, List, Optional, Set, Tuple

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(CURRENT_DIR)
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

import app


def _normalize_text(value: object) -> str:
    text = str(value or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def _normalize_header(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def _read_csv_rows(path: str) -> List[Dict[str, str]]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"CSV not found: {path}")

    last_error: Optional[Exception] = None
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            with open(path, "r", encoding=encoding, newline="") as file_obj:
                reader = csv.DictReader(file_obj)
                rows: List[Dict[str, str]] = []
                for raw in reader:
                    if not isinstance(raw, dict):
                        continue
                    normalized = {
                        _normalize_header(k): _normalize_text(v)
                        for k, v in raw.items()
                        if _normalize_header(k)
                    }
                    rows.append(normalized)
                return rows
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Failed to read CSV {path}: {last_error}")


def _parse_date_iso(value: str) -> Optional[str]:
    raw = _normalize_text(value)
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw[:10], fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _priority_map(value: str) -> str:
    ref = _normalize_text(value).lower()
    if "critical" in ref:
        return "Critical"
    if "high" in ref:
        return "High"
    if "low" in ref:
        return "Low"
    return "Medium"


def _status_from_solution(solution: str) -> str:
    return "Closed" if _normalize_text(solution) else "Open"


def _to_int(value: str, default: int = 0) -> int:
    try:
        return int(float(str(value or "0").replace(",", ".")))
    except Exception:
        return default


def _load_existing_falha_keys(cursor, ts_db: str) -> Set[Tuple[str, str, str, str]]:
    cursor.execute(
        f"""
        SELECT tail, ata, data_cadastro, problema
        FROM {ts_db}.falhas
        """
    )
    keys: Set[Tuple[str, str, str, str]] = set()
    for row in cursor.fetchall():
        day = row.get("data_cadastro")
        if isinstance(day, (datetime, date)):
            day_key = day.isoformat()
        else:
            day_key = _parse_date_iso(str(day or "")) or ""
        key = (
            _normalize_text(row.get("tail")).upper(),
            _normalize_text(row.get("ata")),
            day_key,
            _normalize_text(row.get("problema")).lower(),
        )
        keys.add(key)
    return keys


def _load_existing_lru_keys(cursor, ts_db: str) -> Set[Tuple[str, str, str, str, str, str]]:
    cursor.execute(
        f"""
        SELECT acft_registration, pn_off, sn_off, pn_on, sn_on, removal_date
        FROM {ts_db}.lru_removal_installation
        """
    )
    keys: Set[Tuple[str, str, str, str, str, str]] = set()
    for row in cursor.fetchall():
        day = row.get("removal_date")
        if isinstance(day, (datetime, date)):
            day_key = day.isoformat()
        else:
            day_key = _parse_date_iso(str(day or "")) or ""
        key = (
            _normalize_text(row.get("acft_registration")).upper(),
            _normalize_text(row.get("pn_off")).upper(),
            _normalize_text(row.get("sn_off")).upper(),
            _normalize_text(row.get("pn_on")).upper(),
            _normalize_text(row.get("sn_on")).upper(),
            day_key,
        )
        keys.add(key)
    return keys


def _row_value(row: Dict[str, str], *headers: str) -> str:
    for header in headers:
        key = _normalize_header(header)
        if key in row and _normalize_text(row.get(key)):
            return _normalize_text(row.get(key))
    return ""


def import_mirep_to_falhas(mirep_csv: str) -> Dict[str, int]:
    rows = _read_csv_rows(mirep_csv)
    inserted = 0
    skipped = 0

    with app.app.app_context():
        cursor = app.get_db_cursor()
        existing_keys = _load_existing_falha_keys(cursor, app.TS_DB)

        payload: List[Tuple[object, ...]] = []
        for row in rows:
            tail = _row_value(row, "TAIL").upper()
            ata = _row_value(row, "ATA")
            problem = _row_value(row, "problem", "problem ")
            solved = _row_value(row, "Solution", "solution")
            day = _parse_date_iso(_row_value(row, "DATE"))
            if not tail or not problem:
                skipped += 1
                continue
            if not day:
                day = datetime.now().date().isoformat()

            key = (tail, ata, day, _normalize_text(problem).lower())
            if key in existing_keys:
                skipped += 1
                continue
            existing_keys.add(key)

            payload.append(
                (
                    day,
                    tail,
                    _row_value(row, "FAMILIA", "family"),
                    _status_from_solution(solved),
                    problem,
                    _row_value(row, "category"),
                    _priority_map(_row_value(row, "Priority", "Priorit")),
                    ata,
                    _row_value(row, "LOCATION", "location"),
                    None,
                    _to_int(_row_value(row, "time", "hours"), default=0),
                    _row_value(row, "troubleshooting", "troubleshooting "),
                    solved,
                    "csv_import",
                )
            )

        if payload:
            cursor.executemany(
                f"""
                INSERT INTO {app.TS_DB}.falhas
                (data_cadastro, tail, modelo, status_atual, problema, categoria,
                 prioridade, ata, localizacao, tecnico_responsavel,
                 tempo_estimado_horas, troubleshooting, solucao, criado_por)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                payload,
            )
            app.mysql.connection.commit()
            inserted = len(payload)

    return {"read": len(rows), "inserted": inserted, "skipped": skipped}


def import_lru_delta(lru_csv: str) -> Dict[str, int]:
    rows = _read_csv_rows(lru_csv)
    inserted = 0
    skipped = 0

    with app.app.app_context():
        cursor = app.get_db_cursor()
        existing_keys = _load_existing_lru_keys(cursor, app.TS_DB)

        payload: List[Tuple[object, ...]] = []
        for row in rows:
            reg = _row_value(row, "Matricula", "acft_registration").upper()
            pn_off = _row_value(row, "PN OFF", "pn off", "pn_off").upper()
            sn_off = _row_value(row, "SN OFF", "sn off", "sn_off").upper()
            pn_on = _row_value(row, "PN ON", "pn on", "pn_on").upper()
            sn_on = _row_value(row, "PN ON2", "sn on", "sn_on").upper()
            day = _parse_date_iso(
                _row_value(
                    row,
                    "data de remocao",
                    "data de remoção",
                    "removal_date",
                )
            )
            if not reg or not pn_off:
                skipped += 1
                continue
            if not day:
                day = datetime.now().date().isoformat()

            key = (reg, pn_off, sn_off, pn_on, sn_on, day)
            if key in existing_keys:
                skipped += 1
                continue
            existing_keys.add(key)

            payload.append(
                (
                    reg,
                    pn_off,
                    sn_off,
                    pn_on,
                    sn_on,
                    _row_value(row, "Clasificacion", "classification",
                               "removal_classification"),
                    _row_value(row, "TSI", "tsi"),
                    _row_value(row, "TSO", "tso"),
                    _row_value(row, "TSN", "tsn"),
                    _row_value(row, "Ubicación", "Ubicacion", "position"),
                    day,
                    _row_value(row, "removal reason", "removal_reason"),
                )
            )

        if payload:
            cursor.executemany(
                f"""
                INSERT INTO {app.TS_DB}.lru_removal_installation
                (acft_registration, pn_off, sn_off, pn_on, sn_on,
                 removal_classification, tsi, tso, tsn, position,
                 removal_date, removal_reason)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                payload,
            )
            app.mysql.connection.commit()
            inserted = len(payload)

    return {"read": len(rows), "inserted": inserted, "skipped": skipped}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Import external CSV updates into troubleshooting database.")
    parser.add_argument("--mirep", required=True, help="Path to mirep.csv")
    parser.add_argument("--lru", required=True,
                        help="Path to LRU csv (instalacion/remocion)")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    mirep_result = import_mirep_to_falhas(args.mirep)
    lru_result = import_lru_delta(args.lru)

    summary = {
        "mirep": mirep_result,
        "lru": lru_result,
        "timestamp": datetime.now().isoformat(),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
