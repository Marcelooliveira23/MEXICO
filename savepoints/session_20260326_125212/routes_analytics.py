#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Analytics and Offline AI routes.

Provides technical analysis, recurring tail insights,
and troubleshooting recommendations.
"""

from __future__ import annotations
from copy import deepcopy as _deepcopy
import uuid as _uuid

import hashlib
import html as _html
import json
import os
import re
import time
import csv
import io
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import pymysql
from flask import Blueprint, current_app, jsonify, render_template, request, session

from ai_engine import ATA_KNOWLEDGE_BASE, get_ai
from ai_engine_v10_advanced import (
    AIEngineV10Full,
    get_ata_info,
    find_related_atas,
    infer_system_from_keyword,
    is_safety_critical,
    ATA_KNOWLEDGE_GRAPH,
)
from ai_engine_v10_utils import (
    fix_fh_fc_data_pipeline,
    build_monthly_failure_trend,
    build_exposure_and_hotspots,
    build_ata_quick_reference,
    semantic_ata_matcher,
    extract_multi_system_context,
    component_history_scorer,
    maintenance_action_recommender,
    detect_failure_pattern_recurrence,
    refine_confidence_scoring,
    ai_recalibration_engine,
    predictive_intervention_alerts,
    autonomous_maintenance_planner,
    daily_brief_generation,
    anomaly_detection_engine,
    page_context_analyzer,
    cadastro_semantic_case_matching,
    executive_dashboard_builder,
)

# Deterministic threshold-based exceedance verdict engine (AMM/AFM limits)
try:
    from exceedance_rules_engine import evaluate_exceedance_verdict as _evaluate_exceedance_verdict
    _EXCEEDANCE_ENGINE_AVAILABLE = True
except ImportError:
    _EXCEEDANCE_ENGINE_AVAILABLE = False
    def _evaluate_exceedance_verdict(*_a, **_kw):  # type: ignore
        return {"verdict": "UNDETERMINED", "family": "unknown",
                "triggered_rules": [], "all_rules": [], "evaluated_events": [],
                "parameter_peaks": {}, "evaluated_parameters": [],
                "summary": "Exceedance rules engine not available.",
                "amm_references": [], "signals_used": [], "rows_evaluated": 0}

analytics_bp = Blueprint("analytics", __name__)

# ── Fase 5: Security — Input sanitization ───────────────────────────────────
_QUERY_MAX_LEN = 1000
_FIELD_MAX_LEN = 100


def sanitize_input(text: str, max_len: int = _QUERY_MAX_LEN) -> str:
    """Strip HTML, control chars, and cap length. Safe string for AI input."""
    if not text:
        return ""
    text = str(text)[:max_len]
    text = _html.escape(text)
    # Remove any residual HTML entities injected through double-encoding
    text = re.sub(r'&(?:#\d+|#x[0-9a-fA-F]+|[a-zA-Z]+);', ' ', text)
    # Remove shell / injection metacharacters (not valid in aviation descriptions)
    text = re.sub(r'[<>{}\[\]\\^`|$]', ' ', text)
    return text.strip()


# ── Fase 5: Security — Rate limiter ─────────────────────────────────────────
_RATE_STORE: dict[str, list[float]] = {}
_RATE_MAX = 60      # requests per window
_RATE_WINDOW = 60   # seconds


def _check_rate_limit(ip: str) -> bool:
    """Returns True if the request is within the rate limit, False if exceeded."""
    now = time.time()
    window_start = now - _RATE_WINDOW
    bucket = _RATE_STORE.get(ip, [])
    bucket = [t for t in bucket if t > window_start]
    if len(bucket) >= _RATE_MAX:
        _RATE_STORE[ip] = bucket
        return False
    bucket.append(now)
    _RATE_STORE[ip] = bucket
    return True

# ── Fase 5: Security — Response security headers ─────────────────────────────


@analytics_bp.after_request
def _add_security_headers(response):
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-XSS-Protection", "1; mode=block")
    response.headers.setdefault(
        "Referrer-Policy", "strict-origin-when-cross-origin")
    return response


# ── Fase 4: Performance — Response cache (TTL 90s) ───────────────────────────
_RESP_CACHE: dict[str, tuple[dict, float]] = {}
_RESP_CACHE_TTL = 90  # seconds


def _cache_key(query: str, scope: str, tail: str, model: str) -> str:
    raw = f"{query.lower().strip()}|{scope}|{tail.upper()}|{model.lower()}"
    return hashlib.md5(raw.encode("utf-8", errors="replace")).hexdigest()


def _cache_get(key: str) -> dict | None:
    entry = _RESP_CACHE.get(key)
    if entry and (time.time() - entry[1]) < _RESP_CACHE_TTL:
        return entry[0]
    return None


def _cache_set(key: str, value: dict) -> None:
    # Limit cache size to 256 entries (evict oldest on overflow)
    if len(_RESP_CACHE) >= 256:
        oldest = min(_RESP_CACHE, key=lambda k: _RESP_CACHE[k][1])
        _RESP_CACHE.pop(oldest, None)
    _RESP_CACHE[key] = (value, time.time())

# ─────────────────────────────────────────────────────────────────────────────


# ── V10 Engine singleton ─────────────────────────────────────────────────────
_v10_engine: AIEngineV10Full | None = None


def get_v10_engine() -> AIEngineV10Full:
    """Returns the shared V10 engine instance, created on first call."""
    global _v10_engine
    if _v10_engine is None:
        known_tails = _collect_tail_filters(load_records(limit=4000))
        _v10_engine = AIEngineV10Full(known_tails=known_tails)
    return _v10_engine
# ─────────────────────────────────────────────────────────────────────────────


DEFAULT_E2_MODEL_FILTER = "E2_FAMILY"
MODEL_FILTER_PRESETS = {
    "E2": ["E190-E2", "E195-E2"],
    "E2FAMILY": ["E190-E2", "E195-E2"],
    "E2MODELS": ["E190-E2", "E195-E2"],
    "E2_FAMILY": ["E190-E2", "E195-E2"],
    "CLASSIC": ["E170", "E175", "E190", "E195"],
    "CLASSICEFAMILY": ["E170", "E175", "E190", "E195"],
    "CLASSIC_FAMILY": ["E170", "E175", "E190", "E195"],
    "EJET": ["E170", "E175", "E190", "E195"],
    "EJETS": ["E170", "E175", "E190", "E195"],
    "ERJ": ["ERJ145"],
    "ERJFAMILY": ["ERJ145"],
    "ERJ_FAMILY": ["ERJ145"],
}
MODEL_NAME_ALIASES = {
    "EMB145": "ERJ145",
    "ERJ145": "ERJ145",
    "EMB170": "E170",
    "ERJ170": "E170",
    "E170": "E170",
    "EMB175": "E175",
    "ERJ175": "E175",
    "E175": "E175",
    "EMB190": "E190",
    "E190": "E190",
    "EMB195": "E195",
    "E195": "E195",
    "E190E2": "E190-E2",
    "E190-E2": "E190-E2",
    "190E2": "E190-E2",
    "E195E2": "E195-E2",
    "E195-E2": "E195-E2",
    "195E2": "E195-E2",
}


def _fallback_records_path() -> str:
    return os.path.join(current_app.root_path, "records_fallback.json")


def _tails_fallback_path() -> str:
    return os.path.join(current_app.root_path, "tails_fallback.json")


def _feedback_path() -> str:
    return os.path.join(current_app.root_path, "ai_feedback.json")


def _chat_memory_path() -> str:
    return os.path.join(current_app.root_path, "ai_chat_memory.json")


def _exceedance_history_path() -> str:
    return os.path.join(current_app.root_path, "exceedance_analysis_history.json")


def _exceedance_audit_path() -> str:
    return os.path.join(current_app.root_path, "exceedance_analysis_audit.json")


def _exceedance_upload_dir() -> str:
    return os.path.join(current_app.root_path, "uploads", "exceedance")


_EXCEEDANCE_RETENTION_DAYS = 14


def _ensure_conversation_id() -> str:
    conv_id = str(session.get("ai_conversation_id", "")).strip()
    if conv_id:
        return conv_id
    base = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
    conv_id = f"conv_{base}"
    session["ai_conversation_id"] = conv_id
    return conv_id


def _load_chat_memory_store() -> Dict[str, List[Dict[str, Any]]]:
    path = _chat_memory_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
        return {}
    except Exception:
        return {}


def _save_chat_memory_store(store: Dict[str, List[Dict[str, Any]]]) -> None:
    path = _chat_memory_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def _load_exceedance_history_store() -> Dict[str, List[Dict[str, Any]]]:
    path = _exceedance_history_path()
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return {str(k): v for k, v in data.items() if isinstance(v, list)}
        return {}
    except Exception:
        return {}


def _save_exceedance_history_store(store: Dict[str, List[Dict[str, Any]]]) -> None:
    path = _exceedance_history_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def _anonymize_sensitive_text(text: str) -> str:
    value = str(text or "")
    value = re.sub(r"\bPR-[A-Z0-9]{2,}\b",
                   "TAIL-REDACTED", value, flags=re.IGNORECASE)
    value = re.sub(
        r"\b(?:S/N|SN|SERIAL)\s*[:#-]?\s*[A-Z0-9-]{3,}\b", "SERIAL-REDACTED", value, flags=re.IGNORECASE)
    return value


def _build_exceedance_actor_tag(ip: str = "") -> str:
    try:
        conv = _ensure_conversation_id()
    except RuntimeError:
        conv = "conv_anonymous"
    suffix = str(ip or "unknown").replace(":", "_").replace(".", "_")[:32]
    return f"{conv}:{suffix}"


def _cleanup_exceedance_retention(max_age_days: int = _EXCEEDANCE_RETENTION_DAYS) -> Dict[str, Any]:
    upload_dir = _exceedance_upload_dir()
    os.makedirs(upload_dir, exist_ok=True)
    threshold = time.time() - max_age_days * 86400
    removed_files = 0
    for name in os.listdir(upload_dir):
        path = os.path.join(upload_dir, name)
        try:
            if os.path.isfile(path) and os.path.getmtime(path) < threshold:
                os.remove(path)
                removed_files += 1
        except OSError:
            continue
    return {"retention_days": max_age_days, "removed_files": removed_files}


def _persist_exceedance_uploads(
    analysis_key: str,
    upload_specs: List[Dict[str, Any]],
    actor: str,
) -> List[Dict[str, Any]]:
    upload_dir = _exceedance_upload_dir()
    os.makedirs(upload_dir, exist_ok=True)
    persisted: List[Dict[str, Any]] = []
    for spec in upload_specs:
        raw = spec.get("data") if isinstance(
            spec.get("data"), (bytes, bytearray)) else b""
        if not raw:
            continue
        original_name = str(spec.get("filename", "upload.bin") or "upload.bin")
        ext = os.path.splitext(original_name)[1].lower() or ".bin"
        digest = hashlib.sha1(raw).hexdigest()
        stored_name = f"{analysis_key}_{spec.get('kind', 'evidence')}_{digest[:12]}{ext}"
        stored_path = os.path.join(upload_dir, stored_name)
        try:
            with open(stored_path, "wb") as f:
                f.write(raw)
        except OSError:
            continue
        persisted.append({
            "kind": str(spec.get("kind", "evidence")),
            "original_name": original_name,
            "stored_name": stored_name,
            "stored_path": stored_path,
            "sha1": digest,
            "size_bytes": len(raw),
            "uploaded_at": datetime.now(timezone.utc).isoformat(),
            "actor": actor,
            "anonymized_name": _anonymize_sensitive_text(original_name),
            "anonymized_preview": _anonymize_sensitive_text(spec.get("preview", ""))[:160],
        })
    return persisted


def _append_exceedance_audit_entries(entries: List[Dict[str, Any]]) -> None:
    if not entries:
        return
    all_entries = _load_json_list(_exceedance_audit_path())
    all_entries.extend(entries)
    _write_json_list(_exceedance_audit_path(), all_entries[-500:])


def _load_persisted_exceedance_evidence(stored_files: List[Dict[str, Any]]) -> Dict[str, Any]:
    csv_rows: List[Dict[str, str]] = []
    pdf_parts: List[str] = []
    loaded_files: List[Dict[str, Any]] = []
    for item in stored_files:
        path = str(item.get("stored_path", "") or "")
        if not path or not os.path.exists(path):
            continue
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except OSError:
            continue
        kind = str(item.get("kind", "") or "")
        if kind == "csv":
            csv_rows.extend(_extract_rows_from_csv_bytes(raw))
        elif kind == "pdf":
            text = _extract_text_from_pdf_bytes(raw)
            if text:
                pdf_parts.append(text)
        loaded_files.append(item)
    return {
        "csv_rows": csv_rows[:800],
        "pdf_text": "\n\n".join(pdf_parts)[:18000],
        "loaded_files": loaded_files,
    }


def _finalize_exceedance_result(
    result: Dict[str, Any],
    analysis_key: str,
    analysis_mode: str,
    failure_text: str,
    scenario: str,
    tail: str,
    ata: str,
    modelo: str,
    stored_files: List[Dict[str, Any]],
) -> Dict[str, Any]:
    history_store = _load_exceedance_history_store()
    history_items = history_store.get(analysis_key, [])
    previous_snapshot = history_items[-1] if history_items else None
    next_version = len(history_items) + 1
    historical_exceedance_correlation = _build_historical_exceedance_correlation(
        history_store=history_store,
        tail=tail,
        ata=ata,
        modelo=modelo,
        current_signals=result.get("signals", []),
    )
    mandatory_review_trigger = _build_mandatory_review_trigger(
        exceedance_verdict=result.get("exceedance_verdict", {}),
        signals=result.get("signals", []),
        recurring_pattern=result.get("recurring_pattern", {}),
        historical_correlation=historical_exceedance_correlation,
        analysis_version=next_version,
    )
    snapshot = {
        "analysis_key": analysis_key,
        "analysis_version": next_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "priority": result.get("priority", ""),
        "severity_estimate": result.get("severity_estimate", ""),
        "best_option": result.get("best_option", ""),
        "signals": result.get("signals", []),
        "recommended_actions": result.get("recommended_actions", []),
        "probable_cause": result.get("probable_cause", {}),
        "exceedance_verdict": (result.get("exceedance_verdict") or {}).get("verdict", ""),
        "failure_text": failure_text,
        "scenario": scenario,
        "tail": tail,
        "ata": ata,
        "modelo": modelo,
        "analysis_mode": analysis_mode,
        "mandatory_review_required": mandatory_review_trigger.get("required", False),
        "stored_files": stored_files,
    }
    version_comparison = _compare_exceedance_versions(
        previous_snapshot, snapshot)
    history_items.append(snapshot)
    history_store[analysis_key] = history_items[-20:]
    _save_exceedance_history_store(history_store)
    result["analysis_version"] = next_version
    result["analysis_key"] = analysis_key
    result["version_comparison"] = version_comparison
    result["diagnosis_change_alert"] = version_comparison.get("alert", "")
    result["historical_exceedance_correlation"] = historical_exceedance_correlation
    result["mandatory_review_trigger"] = mandatory_review_trigger
    result["closure_readiness"] = _apply_mandatory_review_gate(
        result.get("closure_readiness", {}), mandatory_review_trigger
    )
    mode_value = str(result.get(
        "analysis_mode", analysis_mode or "standard")).strip().lower()
    result["stored_evidence"] = [
        {
            "kind": item.get("kind"),
            "anonymized_name": item.get("anonymized_name"),
            "size_bytes": item.get("size_bytes"),
            "uploaded_at": item.get("uploaded_at"),
        }
        for item in stored_files
    ]
    result["audit_summary"] = {
        "files_logged": len(stored_files),
        "latest_actor": stored_files[-1].get("actor", "") if stored_files else "",
    }
    result["reprocess_ready"] = bool(stored_files)
    result["expert_view"] = _build_expert_view(result)
    result["executive_view"] = _build_executive_view(result)
    result["mode_output"] = result["expert_view"] if mode_value == "expert" else result["executive_view"] if mode_value == "executive" else {}
    result["structured_export"] = _build_structured_export_payload(
        result, mode_value)
    return result


def _build_historical_exceedance_correlation(
    history_store: Dict[str, List[Dict[str, Any]]],
    tail: str,
    ata: str,
    modelo: str,
    current_signals: List[str],
) -> Dict[str, Any]:
    """Item 355: correlate current context against historical exceedance analyses."""
    normalized_tail = str(tail or "").strip().upper()
    normalized_ata = str(ata or "").strip()
    normalized_ata_prefix = normalized_ata[:2]
    normalized_modelo = str(modelo or "").strip().upper()
    signal_set = {str(s or "").strip().lower() for s in current_signals if str(s or "").strip()}

    all_items: List[Dict[str, Any]] = []
    for key, versions in (history_store or {}).items():
        if not isinstance(versions, list):
            continue
        for item in versions:
            if not isinstance(item, dict):
                continue
            row = dict(item)
            row["analysis_key"] = key
            all_items.append(row)

    correlated: List[Dict[str, Any]] = []
    same_tail_count = 0
    same_tail_ata_count = 0
    overlap_signal_count = 0
    critical_or_high_count = 0

    for item in all_items:
        h_tail = str(item.get("tail", "") or "").strip().upper()
        h_ata = str(item.get("ata", "") or "").strip()
        h_ata_prefix = h_ata[:2]
        h_modelo = str(item.get("modelo", "") or "").strip().upper()
        h_signals = item.get("signals", []) or []
        h_signal_set = {str(s or "").strip().lower() for s in h_signals if str(s or "").strip()}

        score = 0
        if normalized_tail and h_tail == normalized_tail:
            score += 40
            same_tail_count += 1
        if normalized_ata_prefix and h_ata_prefix == normalized_ata_prefix:
            score += 25
        if normalized_tail and normalized_ata_prefix and h_tail == normalized_tail and h_ata_prefix == normalized_ata_prefix:
            same_tail_ata_count += 1
            score += 15
        if normalized_modelo and h_modelo and h_modelo == normalized_modelo:
            score += 10

        overlap = sorted(signal_set & h_signal_set)
        if overlap:
            overlap_signal_count += 1
            score += min(30, len(overlap) * 10)

        priority = str(item.get("priority", "") or "").strip().upper()
        if priority in {"CRITICAL", "HIGH"}:
            critical_or_high_count += 1
            score += 8

        if score >= 45:
            correlated.append({
                "analysis_key": item.get("analysis_key", ""),
                "analysis_version": int(item.get("analysis_version", 0) or 0),
                "created_at": item.get("created_at", ""),
                "tail": h_tail,
                "ata": h_ata,
                "modelo": h_modelo,
                "priority": priority,
                "overlap_signals": overlap,
                "match_score": score,
            })

    correlated.sort(key=lambda x: (x.get("match_score", 0), str(x.get("created_at", ""))), reverse=True)
    return {
        "total_history_entries": len(all_items),
        "matched_entries": len(correlated),
        "same_tail_count": same_tail_count,
        "same_tail_ata_count": same_tail_ata_count,
        "overlap_signal_count": overlap_signal_count,
        "critical_or_high_count": critical_or_high_count,
        "top_matches": correlated[:8],
    }


def _build_mandatory_review_trigger(
    exceedance_verdict: Dict[str, Any],
    signals: List[str],
    recurring_pattern: Dict[str, Any],
    historical_correlation: Dict[str, Any],
    analysis_version: int,
) -> Dict[str, Any]:
    """Item 356: trigger mandatory review for repeated/risky exceedance scenarios."""
    verdict = str((exceedance_verdict or {}).get("verdict", "")).strip().upper()
    signal_set = {str(s or "").strip().lower() for s in (signals or []) if str(s or "").strip()}
    risky_signals = {
        "hard landing", "flap overspeed", "landing overspeed", "gear overspeed", "over-g"
    }

    recurrence_count = int((recurring_pattern or {}).get("count", 0) or 0)
    same_tail_ata_count = int((historical_correlation or {}).get("same_tail_ata_count", 0) or 0)
    high_hist_count = int((historical_correlation or {}).get("critical_or_high_count", 0) or 0)

    reason_codes: List[str] = []
    if verdict == "YES":
        reason_codes.append("verdict_yes")
    if signal_set & risky_signals:
        reason_codes.append("risky_signal_detected")
    if recurrence_count >= 2:
        reason_codes.append("recurring_pattern_detected")
    if same_tail_ata_count >= 1:
        reason_codes.append("same_tail_ata_historical_repeat")
    if high_hist_count >= 2:
        reason_codes.append("historical_high_critical_cluster")
    if int(analysis_version or 1) >= 2:
        reason_codes.append("multi_version_case")

    required = bool(
        ("verdict_yes" in reason_codes and "risky_signal_detected" in reason_codes)
        or ("same_tail_ata_historical_repeat" in reason_codes and "risky_signal_detected" in reason_codes)
        or ("recurring_pattern_detected" in reason_codes)
        or ("historical_high_critical_cluster" in reason_codes)
    )

    message = ""
    if required:
        message = (
            "Mandatory technical review required before closure due to repeated or high-risk exceedance profile."
        )

    return {
        "required": required,
        "reason_codes": reason_codes,
        "message": message,
        "recommended_reviewers": ["Engineering", "QA", "Fleet Reliability"] if required else [],
        "sla_hours": 24 if required else 0,
    }


def _apply_mandatory_review_gate(
    closure_readiness: Dict[str, Any],
    mandatory_review_trigger: Dict[str, Any],
) -> Dict[str, Any]:
    if not isinstance(closure_readiness, dict):
        closure_readiness = {"score": 0, "status": "NOT_READY", "blocking_reasons": []}

    gate_required = bool((mandatory_review_trigger or {}).get("required", False))
    if not gate_required:
        return closure_readiness

    blocking = closure_readiness.get("blocking_reasons", []) or []
    gate_message = str((mandatory_review_trigger or {}).get("message", "")).strip()
    if gate_message and gate_message not in blocking:
        blocking.append(gate_message)

    status = str(closure_readiness.get("status", "NOT_READY") or "NOT_READY").strip().upper()
    if status in {"READY", "NEAR_READY"}:
        status = "REQUIRES_ACTION"

    score = int(closure_readiness.get("score", 0) or 0)
    score = min(score, 64)
    closure_readiness["status"] = status
    closure_readiness["score"] = score
    closure_readiness["blocking_reasons"] = blocking
    return closure_readiness


def _build_exceedance_analysis_key(
    failure_text: str,
    scenario: str,
    tail: str,
    ata: str,
    modelo: str,
) -> str:
    base = "|".join([
        str(tail or "").strip().upper(),
        str(ata or "").strip().upper(),
        str(modelo or "").strip().upper(),
        re.sub(r"\s+", " ", str(failure_text or "").strip().lower())[:180],
        re.sub(r"\s+", " ", str(scenario or "").strip().lower())[:180],
    ])
    digest = hashlib.sha1(base.encode(
        "utf-8", errors="replace")).hexdigest()[:16]
    return f"exd_{digest}"


def _compare_exceedance_versions(previous: Dict[str, Any] | None, current: Dict[str, Any]) -> Dict[str, Any]:
    if not previous:
        return {
            "has_previous": False,
            "version_delta": 0,
            "changed_fields": [],
            "diagnosis_changed": False,
            "alert": "",
        }

    changed_fields: List[str] = []
    tracked = [
        "priority",
        "severity_estimate",
        "best_option",
        "signals",
        "recommended_actions",
    ]
    for field in tracked:
        if previous.get(field) != current.get(field):
            changed_fields.append(field)

    prev_pc = str((previous.get("probable_cause") or {}
                   ).get("primary_cause", "") or "")
    curr_pc = str((current.get("probable_cause") or {}
                   ).get("primary_cause", "") or "")
    diagnosis_changed = bool(prev_pc and curr_pc and prev_pc != curr_pc)

    alert = ""
    if diagnosis_changed:
        alert = (
            "ALERT: Diagnostic direction changed between versions "
            f"('{prev_pc}' -> '{curr_pc}'). Review evidence before release decision."
        )

    prev_ver = int(previous.get("analysis_version", 0) or 0)
    curr_ver = int(current.get("analysis_version", 0) or 0)
    return {
        "has_previous": True,
        "version_delta": max(0, curr_ver - prev_ver),
        "changed_fields": changed_fields,
        "diagnosis_changed": diagnosis_changed,
        "previous_primary_cause": prev_pc,
        "current_primary_cause": curr_pc,
        "previous_priority": previous.get("priority", ""),
        "current_priority": current.get("priority", ""),
        "alert": alert,
    }


def _normalize_history_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    normalized: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        msg_type = str(item.get("type", "")).strip().lower()
        if msg_type not in {"user", "bot"}:
            continue
        text = str(item.get("text", "") or "").strip()
        if not text:
            continue
        normalized.append(
            {
                "type": msg_type,
                "text": text[:3000],
                "scope": str(item.get("scope", "global") or "global")[:32],
                "ts": str(item.get("ts") or datetime.now(timezone.utc).isoformat()),
                "sources": item.get("sources") if isinstance(item.get("sources"), dict) else {},
            }
        )
    return normalized


def _load_conversation_history(conversation_id: str, limit: int = 24) -> List[Dict[str, Any]]:
    if not conversation_id:
        return []
    store = _load_chat_memory_store()
    raw = store.get(conversation_id, [])
    if not isinstance(raw, list):
        return []
    items = _normalize_history_items(raw)
    return items[-max(1, int(limit)):]


def _set_conversation_history(conversation_id: str, items: List[Dict[str, Any]]) -> None:
    if not conversation_id:
        return
    store = _load_chat_memory_store()
    cleaned = _normalize_history_items(items)[-40:]
    store[conversation_id] = cleaned
    if len(store) > 150:
        ordered = sorted(
            store.items(),
            key=lambda pair: pair[1][-1].get("ts", "") if pair[1] else "",
            reverse=True,
        )
        store = dict(ordered[:150])
    _save_chat_memory_store(store)


def _append_conversation_turn(
    conversation_id: str,
    msg_type: str,
    text: str,
    scope: str = "global",
    sources: Dict[str, Any] | None = None,
) -> List[Dict[str, Any]]:
    items = _load_conversation_history(conversation_id, limit=40)
    items.append(
        {
            "type": str(msg_type or "user").strip().lower(),
            "text": str(text or "").strip()[:3000],
            "scope": str(scope or "global").strip().lower()[:32] or "global",
            "ts": datetime.now(timezone.utc).isoformat(),
            "sources": sources or {},
        }
    )
    items = _normalize_history_items(items)[-40:]
    _set_conversation_history(conversation_id, items)
    return items


def _build_chat_memory_context(history: List[Dict[str, Any]], max_turns: int = 6) -> str:
    if not history:
        return ""

    recent = history[-max(1, int(max_turns)):]
    lines: List[str] = []
    for item in recent:
        role = "USER" if item.get("type") == "user" else "ASSISTANT"
        text = str(item.get("text", "")).strip().replace("\n", " ")
        if not text:
            continue
        lines.append(f"{role}: {text[:350]}")

    if not lines:
        return ""
    return "Context from recent conversation:\n" + "\n".join(lines)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return default


def _normalize_model_token(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if not raw:
        return ""
    collapsed = raw.replace(" ", "").replace("-", "")
    canonical = MODEL_NAME_ALIASES.get(collapsed, collapsed)
    return canonical.replace(" ", "").replace("-", "")


def _canonical_model_name(value: Any) -> str:
    raw = str(value or "").strip().upper()
    if not raw:
        return ""
    collapsed = raw.replace(" ", "").replace("-", "")
    return MODEL_NAME_ALIASES.get(collapsed, raw)


def _parse_model_filter_tokens(model_filter: Any) -> List[str]:
    raw = str(model_filter or "").strip()
    if not raw:
        return []

    values = [item.strip() for item in re.split(r"[,;|]", raw) if item.strip()]
    if not values:
        values = [raw]

    tokens: List[str] = []
    for value in values:
        collapsed = str(value).strip().upper().replace(
            " ", "").replace("-", "")
        if collapsed in {"ALL", "ALLFLEET", "ALLMODELS"}:
            return []
        preset_models = MODEL_FILTER_PRESETS.get(collapsed, [])
        if preset_models:
            tokens.extend(_normalize_model_token(item)
                          for item in preset_models)
            continue
        tokens.append(_normalize_model_token(value))

    deduped: List[str] = []
    seen = set()
    for token in tokens:
        if not token or token in seen:
            continue
        seen.add(token)
        deduped.append(token)
    return deduped


def _effective_model_filter(model_filter: str = "", tail_filter: str = "") -> str:
    if str(model_filter or "").strip():
        return str(model_filter or "").strip()
    if str(tail_filter or "").strip():
        return ""
    return DEFAULT_E2_MODEL_FILTER


def _filter_records_by_model_tail(
    records: List[Dict[str, Any]],
    model_filter: str = "",
    tail_filter: str = "",
) -> List[Dict[str, Any]]:
    if not records:
        return []

    model_tokens = _parse_model_filter_tokens(model_filter)
    tail_token = str(tail_filter or "").strip().upper()
    if not model_tokens and not tail_token:
        return records

    filtered: List[Dict[str, Any]] = []
    for rec in records:
        rec_tail = str(rec.get("tail", "") or "").strip().upper()
        rec_model = _normalize_model_token(rec.get("modelo", ""))
        if tail_token and rec_tail != tail_token:
            continue
        if model_tokens and rec_model not in model_tokens:
            continue
        filtered.append(rec)
    return filtered


def _collect_model_filters(records: List[Dict[str, Any]]) -> List[str]:
    seen = set()
    models: List[str] = []
    for rec in records:
        raw = _canonical_model_name(rec.get("modelo", ""))
        if not raw:
            continue
        key = _normalize_model_token(raw)
        if not key or key in seen:
            continue
        seen.add(key)
        models.append(raw)
    models.sort()
    return models


def _collect_tail_filters(records: List[Dict[str, Any]]) -> List[str]:
    tails = sorted(
        {
            str(rec.get("tail", "") or "").strip().upper()
            for rec in records
            if str(rec.get("tail", "") or "").strip()
        }
    )
    return tails


def _build_fleet_snapshot(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not records:
        return {
            "fleet_rows": [],
            "excellent_count": 0,
            "good_count": 0,
            "fair_count": 0,
            "mel_open_count": 0,
        }

    open_statuses = {"open", "in progress", "pending", "pending review"}
    tails: Dict[str, Dict[str, Any]] = {}

    for rec in records:
        tail = str(rec.get("tail", "") or "").strip().upper()
        if not tail:
            continue

        row = tails.setdefault(
            tail,
            {
                "tail": tail,
                "modelo": _canonical_model_name(rec.get("modelo", "")) or "N/A",
                "serial_number": rec.get("serial"),
                "failures": 0,
                "open_troubleshooting": 0,
                "fh": 0.0,
                "fc": 0,
                "last_failure": None,
                "recent_failures": 0,
                "ata_counter": Counter(),
            },
        )

        current_model = _canonical_model_name(rec.get("modelo", ""))
        if current_model and row.get("modelo") in {"", "N/A"}:
            row["modelo"] = current_model

        row["failures"] += 1
        status = str(rec.get("status_atual", "") or "").strip().lower()
        if status in open_statuses:
            row["open_troubleshooting"] += 1

        row["fh"] = max(row["fh"], _safe_float(rec.get("fh"), 0.0))
        row["fc"] = max(row["fc"], int(round(_safe_float(rec.get("fc"), 0.0))))

        ata = str(rec.get("ata", "") or "").strip().split(".")[0]
        if ata:
            row["ata_counter"][ata] += 1

        dt = _extract_record_date(rec)
        if dt:
            if row["last_failure"] is None or dt > row["last_failure"]:
                row["last_failure"] = dt
            if dt >= (datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=30)):
                row["recent_failures"] += 1

    mel_items = _load_mel_context(limit=1500)
    aog_items = _load_aog_context(limit=1500)

    open_mel_by_tail: Counter = Counter()
    active_aog_by_tail: Counter = Counter()

    for item in mel_items:
        tail = str(item.get("tail", "") or "").strip().upper()
        if not tail:
            continue
        if not item.get("date_closed"):
            open_mel_by_tail[tail] += 1

    for item in aog_items:
        tail = str(item.get("tail", "") or "").strip().upper()
        if not tail:
            continue
        if not item.get("release_date"):
            active_aog_by_tail[tail] += 1

    all_tails = set(tails.keys()) | set(
        open_mel_by_tail.keys()) | set(active_aog_by_tail.keys())
    fleet_rows: List[Dict[str, Any]] = []

    excellent_count = 0
    good_count = 0
    fair_count = 0
    mel_open_count = 0

    for tail in sorted(all_tails):
        base = tails.get(
            tail,
            {
                "tail": tail,
                "modelo": "N/A",
                "serial_number": None,
                "failures": 0,
                "open_troubleshooting": 0,
                "fh": 0.0,
                "fc": 0,
                "last_failure": None,
                "recent_failures": 0,
                "ata_counter": Counter(),
            },
        )

        open_mel = int(open_mel_by_tail.get(tail, 0))
        active_aog = int(active_aog_by_tail.get(tail, 0))
        failures = int(base.get("failures", 0))
        open_troubleshooting = int(base.get("open_troubleshooting", 0))

        mel_open_count += open_mel

        if active_aog > 0:
            status_indicator = "aog"
            fair_count += 1
        else:
            status_indicator = "operational"
            excellent_count += 1

        if open_troubleshooting > 0:
            good_count += 1

        health_score = 100 - (failures * 2) - \
            (open_troubleshooting * 5) - (open_mel * 4)
        if active_aog:
            health_score -= 25
        health_score = max(10, min(100, health_score))

        if health_score >= 85:
            health_status = "EXCELLENT"
        elif health_score >= 70:
            health_status = "GOOD"
        elif health_score >= 50:
            health_status = "FAIR"
        else:
            health_status = "POOR"

        last_failure = base.get("last_failure")
        days_since_last_failure = 0
        if isinstance(last_failure, datetime):
            days_since_last_failure = max(
                0,
                (datetime.now(timezone.utc).replace(
                    tzinfo=None).date() - last_failure.date()).days,
            )

        top_atas = [item[0] for item in Counter(
            base.get("ata_counter", Counter())).most_common(2)]

        fleet_rows.append(
            {
                "tail": tail,
                "modelo": base.get("modelo", "N/A"),
                "serial_number": base.get("serial_number"),
                "status_indicator": status_indicator,
                "health_score": int(round(health_score)),
                "health_status": health_status,
                "failures": failures,
                "open_issues": open_troubleshooting,
                "open_troubleshooting": open_troubleshooting,
                "open_mel": open_mel,
                "has_open_troubleshooting": open_troubleshooting > 0,
                "fh": round(_safe_float(base.get("fh"), 0.0), 1),
                "fc": int(base.get("fc", 0)),
                "days_since_last_failure": days_since_last_failure,
                "top_atas": top_atas,
                "recent_failures": int(base.get("recent_failures", 0)),
            }
        )

    return {
        "fleet_rows": fleet_rows,
        "excellent_count": excellent_count,
        "good_count": good_count,
        "fair_count": fair_count,
        "mel_open_count": mel_open_count,
    }


def _extract_tail_hints(query: str, known_tails: List[str]) -> List[str]:
    explicit = _extract_tail_refs(query)
    explicit_set = {tail.upper() for tail in explicit}
    if explicit_set:
        return sorted(explicit_set)

    known = [str(tail or "").strip().upper()
             for tail in known_tails if str(tail or "").strip()]
    if not known:
        return []

    tokens = {
        token.upper()
        for token in re.findall(r"\b[A-Z0-9]{2,5}\b", str(query or "").upper())
        if token.upper() not in {"ATA", "MEL", "AOG", "AND", "THE", "WITH", "TAIL", "FLEET", "OPEN", "STATUS"}
    }
    matched: List[str] = []
    for token in tokens:
        for tail in known:
            suffix = tail.split("-", 1)[-1]
            if token == suffix or suffix.endswith(token):
                matched.append(tail)
            elif token in tail:
                matched.append(tail)
    return sorted(set(matched))[:3]


def _load_records_from_fallback() -> List[Dict[str, Any]]:
    path = _fallback_records_path()
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _load_json_list(path: str) -> List[Dict[str, Any]]:
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _write_json_list(path: str, items: List[Dict[str, Any]]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def _load_tail_metrics() -> Dict[str, Dict[str, float]]:
    data = _load_json_list(_tails_fallback_path())
    metrics: Dict[str, Dict[str, float]] = {}
    for item in data:
        tail = str(item.get("tail", "")).strip()
        if not tail:
            continue
        metrics[tail] = {
            "fh": _safe_float(item.get("fh"), 0.0),
            "fc": _safe_float(item.get("fc"), 0.0),
        }
    return metrics


def _merge_tail_metrics(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    tail_metrics = _load_tail_metrics()
    merged: List[Dict[str, Any]] = []
    for rec in records:
        item = dict(rec)
        tail = str(item.get("tail", "")).strip()
        metric = tail_metrics.get(tail, {})
        item["fh"] = _safe_float(
            item.get("fh"), _safe_float(metric.get("fh"), 0.0)
        )
        item["fc"] = _safe_float(
            item.get("fc"), _safe_float(metric.get("fc"), 0.0)
        )
        merged.append(item)
    return merged


def _compute_fh_fc_priorities(
    records: List[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    if not records:
        return []

    max_fh = max((_safe_float(r.get("fh"), 0.0) for r in records), default=0.0)
    max_fc = max((_safe_float(r.get("fc"), 0.0) for r in records), default=0.0)
    if max_fh <= 0:
        max_fh = 1.0
    if max_fc <= 0:
        max_fc = 1.0

    grouped: Dict[tuple, Dict[str, Any]] = {}
    for r in records:
        tail = str(r.get("tail", "N/A")).strip() or "N/A"
        ata = str(r.get("ata", "N/A")).strip().split(".")[0] or "N/A"
        key = (tail, ata)
        if key not in grouped:
            grouped[key] = {
                "tail": tail,
                "ata": ata,
                "count": 0,
                "fh": 0.0,
                "fc": 0.0,
            }
        grouped[key]["count"] += 1
        grouped[key]["fh"] = max(
            grouped[key]["fh"], _safe_float(r.get("fh"), 0.0)
        )
        grouped[key]["fc"] = max(
            grouped[key]["fc"], _safe_float(r.get("fc"), 0.0)
        )

    priorities: List[Dict[str, Any]] = []
    for item in grouped.values():
        exposure = (
            (0.6 * (item["fh"] / max_fh))
            + (0.4 * (item["fc"] / max_fc))
        )
        risk_score = round(item["count"] * exposure * 100, 1)
        level = "low"
        if risk_score >= 180:
            level = "high"
        elif risk_score >= 90:
            level = "medium"
        priorities.append(
            {
                "tail": item["tail"],
                "ata": item["ata"],
                "count": item["count"],
                "fh": round(item["fh"], 1),
                "fc": int(item["fc"]),
                "risk_score": risk_score,
                "risk_level": level,
            }
        )

    return sorted(priorities, key=lambda x: x["risk_score"], reverse=True)[:10]


def _extract_record_date(record: Dict[str, Any]) -> datetime | None:
    raw = str(record.get("data_cadastro")
              or record.get("data_criacao") or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(raw[:10], fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).replace(tzinfo=None)
    except Exception:
        return None


def _month_add(year: int, month: int, delta: int) -> tuple[int, int]:
    month_index = (year * 12 + (month - 1)) + delta
    return month_index // 12, (month_index % 12) + 1


def _build_projection_signals(
    records: List[Dict[str, Any]],
    fh_fc_priority: List[Dict[str, Any]],
) -> Dict[str, Any]:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    month_counter: Counter = Counter()
    for rec in records:
        dt = _extract_record_date(rec)
        if not dt:
            continue
        month_counter[dt.strftime("%Y-%m")] += 1

    history: List[Dict[str, Any]] = []
    for offset in range(-7, 1):
        y, m = _month_add(now.year, now.month, offset)
        key = f"{y:04d}-{m:02d}"
        history.append({"month": key, "count": int(month_counter.get(key, 0))})

    counts = [item["count"] for item in history]
    if not counts:
        counts = [0]
    avg_all = sum(counts) / max(len(counts), 1)
    avg_recent = sum(counts[-3:]) / max(len(counts[-3:]), 1)
    slope = (counts[-1] - counts[0]) / max(len(counts) - 1, 1)
    growth_rate_pct = round(
        ((avg_recent - avg_all) / avg_all) * 100, 1) if avg_all > 0 else 0.0

    if slope > 0.35:
        trend_direction = "up"
    elif slope < -0.35:
        trend_direction = "down"
    else:
        trend_direction = "stable"

    forecast: List[Dict[str, Any]] = []
    baseline = float(counts[-1])
    for step in range(1, 4):
        y, m = _month_add(now.year, now.month, step)
        projected = max(0.0, baseline + (slope * step))
        forecast.append({"month": f"{y:04d}-{m:02d}",
                        "count": int(round(projected))})

    hotspot_factor = 1.0 + max(-0.2, min(0.35, growth_rate_pct / 100.0))
    hotspot_forecast = []
    for item in fh_fc_priority[:5]:
        projected_risk = round(_safe_float(
            item.get("risk_score"), 0.0) * hotspot_factor, 1)
        hotspot_forecast.append(
            {
                "tail": item.get("tail", "N/A"),
                "ata": item.get("ata", "N/A"),
                "risk_score": _safe_float(item.get("risk_score"), 0.0),
                "projected_risk_score": projected_risk,
                "risk_level": item.get("risk_level", "low"),
            }
        )

    if trend_direction == "up":
        narrative = "Failure trend indicates upward pressure. Increase preventive checks on top ATA hotspots."
    elif trend_direction == "down":
        narrative = "Failure trend is improving. Preserve current actions and monitor recurring ATA hotspots."
    else:
        narrative = "Failure trend is stable. Focus on hotspot tails to reduce residual operational risk."

    return {
        "history": history,
        "forecast": forecast,
        "trend_direction": trend_direction,
        "growth_rate_pct": growth_rate_pct,
        "hotspot_forecast": hotspot_forecast,
        "next_30d_expected": forecast[0]["count"] if forecast else 0,
        "next_90d_expected": sum(item["count"] for item in forecast[:3]),
        "narrative": narrative,
    }


def _build_ata_projection(
    records: List[Dict[str, Any]],
    target_ata: str = "",
) -> Dict[str, Any]:
    if not records:
        return {"ata": "N/A", "history": [], "forecast": []}

    ata_ref = str(target_ata or "").strip().split(".")[0]
    if not ata_ref:
        ata_counter = Counter(
            str(rec.get("ata", "") or "").strip().split(".")[0]
            for rec in records
            if str(rec.get("ata", "") or "").strip()
        )
        ata_ref = ata_counter.most_common(1)[0][0] if ata_counter else ""

    if not ata_ref:
        return {"ata": "N/A", "history": [], "forecast": []}

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    month_counter: Counter = Counter()
    for rec in records:
        rec_ata = str(rec.get("ata", "") or "").strip().split(".")[0]
        if rec_ata != ata_ref:
            continue
        dt = _extract_record_date(rec)
        if not dt:
            continue
        month_counter[dt.strftime("%Y-%m")] += 1

    history: List[Dict[str, Any]] = []
    for offset in range(-7, 1):
        y, m = _month_add(now.year, now.month, offset)
        key = f"{y:04d}-{m:02d}"
        history.append({"month": key, "count": int(month_counter.get(key, 0))})

    counts = [item["count"] for item in history]
    if not counts:
        counts = [0]
    slope = (counts[-1] - counts[0]) / max(len(counts) - 1, 1)
    baseline = float(counts[-1])
    forecast: List[Dict[str, Any]] = []
    for step in range(1, 4):
        y, m = _month_add(now.year, now.month, step)
        forecast.append(
            {
                "month": f"{y:04d}-{m:02d}",
                "count": int(round(max(0.0, baseline + (slope * step)))),
            }
        )

    return {
        "ata": ata_ref,
        "history": history,
        "forecast": forecast,
    }


def _compute_autonomy_score(
    generated_description: bool,
    similar_cases_count: int,
    records_count: int,
    ata_count: int,
    tail_count: int,
    active_aog_count: int,
    open_mel_count: int,
    trend_direction: str,
) -> Dict[str, Any]:
    score = 35
    score += 18 if generated_description else 0
    score += 16 if similar_cases_count > 0 else 0
    score += 10 if records_count >= 25 else 6 if records_count >= 5 else 0
    score += 8 if ata_count > 0 else 0
    score += 6 if tail_count > 0 else 0
    score += 4 if (active_aog_count + open_mel_count) > 0 else 0
    if str(trend_direction or "").lower() in {"up", "down", "stable"}:
        score += 3

    score = max(0, min(100, score))
    level = "guided"
    if score >= 80:
        level = "autonomous"
    elif score >= 60:
        level = "semi-autonomous"

    return {
        "score": score,
        "level": level,
        "message": (
            "AI can proactively recommend decisions with low dependency on user text."
            if level == "autonomous"
            else "AI can suggest strong paths but benefits from minimal user context."
            if level == "semi-autonomous"
            else "AI still needs explicit contextual details to maximize precision."
        ),
    }


def _build_operational_impact(
    risk: Dict[str, Any],
    projection: Dict[str, Any],
    active_aog_count: int,
    open_mel_count: int,
) -> Dict[str, Any]:
    next_30d = _safe_float(projection.get("next_30d_expected"), 0.0)
    risk_score = _safe_float(risk.get("risk_score"), 0.0)
    growth = _safe_float(projection.get("growth_rate_pct"), 0.0)

    estimated_delay_hours = round(
        (active_aog_count * 3.2)
        + (open_mel_count * 0.7)
        + (next_30d * 0.25),
        1,
    )
    maintenance_pressure = int(
        max(0, min(100, (risk_score * 0.65) +
            (max(growth, 0) * 0.9) + (active_aog_count * 8)))
    )

    dispatch_risk = "LOW"
    if active_aog_count > 0 or maintenance_pressure >= 75:
        dispatch_risk = "HIGH"
    elif open_mel_count > 0 or maintenance_pressure >= 45:
        dispatch_risk = "MEDIUM"

    return {
        "dispatch_risk": dispatch_risk,
        "estimated_delay_hours": estimated_delay_hours,
        "maintenance_pressure": maintenance_pressure,
        "active_aog": int(active_aog_count),
        "open_mel": int(open_mel_count),
    }


def _build_forecast_drift_alert(projection: Dict[str, Any]) -> Dict[str, Any]:
    history = list(projection.get("history") or [])
    if len(history) < 4:
        return {
            "status": "insufficient",
            "deviation_pct": 0.0,
            "message": "Insufficient history for forecast drift calculation.",
            "action": "Collect more monthly records to evaluate forecast reliability.",
        }

    recent = [
        _safe_float(item.get("count"), 0.0)
        for item in history[-4:-1]
    ]
    actual_last = _safe_float(history[-1].get("count"), 0.0)
    expected = sum(recent) / max(len(recent), 1)
    if expected <= 0:
        expected = 1.0

    deviation_pct = round(((actual_last - expected) / expected) * 100, 1)
    abs_dev = abs(deviation_pct)
    if abs_dev >= 45:
        status = "critical"
    elif abs_dev >= 25:
        status = "warning"
    else:
        status = "stable"

    action = "Keep current forecast model and monitor monthly."
    if status == "warning":
        action = "Recalibrate forecasting weights and validate top ATA hotspot behavior."
    elif status == "critical":
        action = "Trigger immediate forecast recalibration and prioritize anomaly investigation."

    return {
        "status": status,
        "deviation_pct": deviation_pct,
        "message": (
            f"Last-month actual deviated {deviation_pct}% from recent baseline expectation."
        ),
        "action": action,
    }


def _build_autonomous_intervention_queue(
    fh_fc_priority: List[Dict[str, Any]],
    projection: Dict[str, Any],
    impact: Dict[str, Any],
) -> List[Dict[str, Any]]:
    growth = _safe_float(projection.get("growth_rate_pct"), 0.0)
    next_30 = _safe_float(projection.get("next_30d_expected"), 0.0)
    dispatch_risk = str(impact.get("dispatch_risk", "LOW")).upper()
    risk_boost = 0
    if dispatch_risk == "HIGH":
        risk_boost = 18
    elif dispatch_risk == "MEDIUM":
        risk_boost = 10

    queue: List[Dict[str, Any]] = []
    for idx, item in enumerate((fh_fc_priority or [])[:8], start=1):
        base = _safe_float(item.get("risk_score"), 0.0)
        urgency = round(base + (growth * 0.8) +
                        (next_30 * 0.6) + risk_boost, 1)
        sla = "72h"
        if urgency >= 180:
            sla = "6h"
        elif urgency >= 130:
            sla = "24h"
        elif urgency >= 90:
            sla = "48h"

        queue.append(
            {
                "rank": idx,
                "tail": item.get("tail", "N/A"),
                "ata": item.get("ata", "N/A"),
                "risk_score": base,
                "urgency_score": urgency,
                "priority": "P1" if urgency >= 180 else "P2" if urgency >= 130 else "P3",
                "recommended_sla": sla,
                "action": (
                    f"Execute focused ATA {item.get('ata', 'N/A')} inspection on tail {item.get('tail', 'N/A')} and close aged open findings."
                ),
            }
        )

    queue.sort(key=lambda x: x.get("urgency_score", 0), reverse=True)
    for pos, item in enumerate(queue, start=1):
        item["rank"] = pos
    return queue


def _build_mission_brief(
    queue: List[Dict[str, Any]],
    drift_alert: Dict[str, Any],
    autonomy: Dict[str, Any],
) -> Dict[str, Any]:
    top = queue[0] if queue else {}
    headline = "No immediate intervention queue available."
    if top:
        headline = (
            f"Prioritize tail {top.get('tail', 'N/A')} / ATA {top.get('ata', 'N/A')} "
            f"with {top.get('priority', 'P3')} urgency and SLA {top.get('recommended_sla', '72h')}."
        )
    return {
        "headline": headline,
        "autonomy_level": autonomy.get("level", "guided"),
        "drift_status": drift_alert.get("status", "stable"),
        "drift_message": drift_alert.get("message", ""),
        "next_action": top.get("action", "Keep monitoring and refresh analytics daily."),
    }


def _model_family_name(model_value: str) -> str:
    token = _normalize_model_token(model_value)
    if token in {"E190-E2", "E195-E2"}:
        return "E2"
    if token in {"E170", "E175", "E190", "E195"}:
        return "CLASSIC"
    if token == "ERJ145":
        return "ERJ"
    return "OTHER"


def _build_family_comparison(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not records:
        return []

    grouped: Dict[str, Dict[str, Any]] = {}
    for rec in records:
        family = _model_family_name(str(rec.get("modelo", "")))
        info = grouped.setdefault(
            family,
            {
                "family": family,
                "total": 0,
                "open_count": 0,
                "fh_sum": 0.0,
                "fc_sum": 0.0,
                "tails": set(),
            },
        )
        info["total"] += 1
        if str(rec.get("status_atual", "") or "").strip().lower() in {
            "open",
            "in progress",
            "pending",
            "pending review",
            "aberto",
        }:
            info["open_count"] += 1
        info["fh_sum"] += _safe_float(rec.get("fh"), 0.0)
        info["fc_sum"] += _safe_float(rec.get("fc"), 0.0)
        tail = str(rec.get("tail", "") or "").strip().upper()
        if tail:
            info["tails"].add(tail)

    out: List[Dict[str, Any]] = []
    for item in grouped.values():
        total = max(1, item["total"])
        out.append(
            {
                "family": item["family"],
                "total": item["total"],
                "open_rate": round((item["open_count"] / total) * 100, 1),
                "avg_fh": round(item["fh_sum"] / total, 1),
                "avg_fc": round(item["fc_sum"] / total, 1),
                "tails": len(item["tails"]),
            }
        )

    order = {"E2": 0, "CLASSIC": 1, "ERJ": 2, "OTHER": 3}
    out.sort(key=lambda x: (order.get(x["family"], 99), -x["total"]))
    return out


def _build_executive_opinion(
    risk: Dict[str, Any],
    projection: Dict[str, Any],
    similar_cases: List[Dict[str, Any]],
    active_aog: int,
    open_mel: int,
    focus_tail: str,
    focus_ata: str,
) -> Dict[str, Any]:
    risk_level = str(risk.get("risk_level", "medium")).lower()
    trend = str(projection.get("trend_direction", "stable")).lower()
    next_30d = int(projection.get("next_30d_expected", 0) or 0)
    growth = _safe_float(projection.get("growth_rate_pct"), 0.0)

    stance = "monitor"
    if risk_level in {"critical", "high"} or active_aog > 0:
        stance = "intervene-now"
    elif trend == "up" or growth >= 10:
        stance = "preventive-acceleration"

    confidence = 60
    if similar_cases:
        confidence += 15
    if open_mel:
        confidence += 10
    if active_aog:
        confidence += 10
    confidence = min(confidence, 95)

    why = [
        f"Risk level assessed as {risk_level.upper()} with score {risk.get('risk_score', 0)}.",
        f"Projected trend is {trend.upper()} with growth {growth}% and {next_30d} expected events in next 30 days.",
    ]
    if focus_tail:
        why.append(
            f"Tail focus {focus_tail} indicates concentrated operational exposure.")
    if focus_ata:
        why.append(
            f"ATA {focus_ata} should be treated as current technical hotspot.")
    if active_aog > 0:
        why.append(
            f"There are {active_aog} active AOG events in the filtered context.")
    if open_mel > 0:
        why.append(
            f"There are {open_mel} open MEL restrictions impacting dispatch flexibility.")

    what_if = [
        {
            "name": "If trend worsens 20%",
            "impact": f"Expected next 30-day events may rise from {next_30d} to {int(round(next_30d * 1.2))}.",
            "action": "Escalate ATA inspections and pre-position critical LRUs on high-risk tails.",
        },
        {
            "name": "If preventive campaign is applied",
            "impact": f"Expected next 90-day events may drop from {projection.get('next_90d_expected', 0)} to {int(round(_safe_float(projection.get('next_90d_expected'), 0.0) * 0.75))}.",
            "action": "Apply targeted checks on top hotspot ATA/tail combinations and close high-age open items.",
        },
    ]

    return {
        "stance": stance,
        "confidence": confidence,
        "why": why,
        "what_if": what_if,
    }


def _load_feedback() -> List[Dict[str, Any]]:
    return _load_json_list(_feedback_path())


def _save_feedback_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    all_entries = _load_feedback()
    max_id = max((int(x.get("id", 0)) for x in all_entries), default=0)
    entry["id"] = max_id + 1
    all_entries.append(entry)
    if len(all_entries) > 1000:
        all_entries = all_entries[-1000:]
    _write_json_list(_feedback_path(), all_entries)
    return entry


def _feedback_hint_for_ata(ata: str) -> str:
    ata_ref = str(ata or "").strip().split(".")[0]
    if not ata_ref:
        return "No ATA reference informed for learning lookup."

    entries = [
        x for x in _load_feedback() if str(x.get("ata", "")).strip() == ata_ref
    ]
    if not entries:
        return "No prior feedback for this ATA yet."

    positive = sum(1 for x in entries if bool(x.get("helpful")) is True)
    total = len(entries)
    score = round((positive / total) * 100, 1)
    if score >= 75:
        return (
            "Historical feedback indicates high recommendation "
            f"acceptance for ATA {ata_ref} ({score}%)."
        )
    if score >= 50:
        return (
            "Historical feedback indicates moderate recommendation "
            f"acceptance for ATA {ata_ref} ({score}%)."
        )
    return (
        "Historical feedback indicates low recommendation acceptance "
        f"for ATA {ata_ref} ({score}%). Review troubleshooting strategy."
    )


def _feedback_acceptance_for_ata(ata: str) -> float:
    ata_ref = str(ata or "").strip().split(".")[0]
    if not ata_ref:
        return 0.5

    entries = [
        x for x in _load_feedback() if str(x.get("ata", "")).strip() == ata_ref
    ]
    if not entries:
        return 0.5

    positive = sum(1 for x in entries if bool(x.get("helpful")) is True)
    return positive / max(len(entries), 1)


def _safe_schema_name(value: Any, default: str) -> str:
    candidate = str(value or "").strip()
    if candidate and all(ch.isalnum() or ch == "_" for ch in candidate):
        return candidate
    return default


def _db_connect():
    cfg = current_app.config
    return pymysql.connect(
        host=cfg.get("MYSQL_HOST", "localhost"),
        user=cfg.get("MYSQL_USER", "root"),
        password=cfg.get("MYSQL_PASSWORD", ""),
        database=_safe_schema_name(cfg.get("MYSQL_DB"), "troubleshooting_db"),
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=4,
    )


def _load_mel_context(limit: int = 300) -> List[Dict[str, Any]]:
    cfg = current_app.config
    mel_db = _safe_schema_name(cfg.get("MEL_DB_NAME"), "mel_db")
    try:
        connection = _db_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, tail, ata, system_inop, category, chapter,
                           date_opened, date_closed, notes, created_at
                    FROM {mel_db}.mel_items
                    ORDER BY COALESCE(created_at, date_opened, date_closed) DESC, id DESC
                    LIMIT %s
                    """,
                    (int(limit),),
                )
                return list(cursor.fetchall())
        finally:
            connection.close()
    except Exception:
        return _load_json_list(os.path.join(current_app.root_path, "mel_fallback.json"))


def _load_aog_context(limit: int = 300) -> List[Dict[str, Any]]:
    cfg = current_app.config
    ts_db = _safe_schema_name(cfg.get("MYSQL_DB"), "troubleshooting_db")
    try:
        connection = _db_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, date, tail, interruption_type, ata, fail_code, location,
                           event_description, maintenance_actions, expected_return, release_date
                    FROM {ts_db}.out_of_service
                    ORDER BY COALESCE(release_date, date) DESC, id DESC
                    LIMIT %s
                    """,
                    (int(limit),),
                )
                return list(cursor.fetchall())
        finally:
            connection.close()
    except Exception:
        return _load_json_list(os.path.join(current_app.root_path, "aog_fallback.json"))


def _load_lru_context(limit: int = 400) -> List[Dict[str, Any]]:
    cfg = current_app.config
    ts_db = _safe_schema_name(cfg.get("MYSQL_DB"), "troubleshooting_db")
    try:
        connection = _db_connect()
        try:
            with connection.cursor() as cursor:
                cursor.execute(
                    f"""
                    SELECT id, acft_registration, pn_off, sn_off, pn_on, sn_on,
                           removal_classification, tsi, tso, tsn, position,
                           removal_date, removal_reason
                    FROM {ts_db}.lru_removal_installation
                    ORDER BY removal_date DESC, id DESC
                    LIMIT %s
                    """,
                    (int(limit),),
                )
                rows = list(cursor.fetchall())
                for row in rows:
                    row["tail"] = str(
                        row.get("acft_registration", "") or "").strip().upper()
                return rows
        finally:
            connection.close()
    except Exception:
        return []


def _extract_tail_refs(text: str) -> List[str]:
    matches = re.findall(
        r"\b[A-Z0-9]{2,4}-[A-Z0-9]{2,5}\b", str(text or "").upper())
    return sorted(set(matches))


def _extract_ata_refs(text: str) -> List[str]:
    return sorted(set(match.split(".")[0] for match in re.findall(r"\b\d{2}(?:\.\d+)?\b", str(text or ""))))


def _score_text_match(text: str, tokens: List[str]) -> float:
    text_tokens = _tokenize(text)
    return _semantic_score(tokens, text_tokens)


def _find_context_matches(
    items: List[Dict[str, Any]],
    text_fields: List[str],
    query: str,
    ata_refs: List[str],
    tail_refs: List[str],
    limit: int = 5,
) -> List[Dict[str, Any]]:
    query_tokens = _tokenize(query)
    ranked: List[Dict[str, Any]] = []

    for item in items:
        text_blob = " ".join(str(item.get(field, "") or "")
                             for field in text_fields)
        ata_value = str(item.get("ata", "") or "").strip().split(".")[0]
        tail_value = str(item.get("tail", "") or "").strip().upper()
        score = _score_text_match(text_blob, query_tokens)

        if ata_refs and ata_value in ata_refs:
            score += 0.22
        if tail_refs and tail_value in tail_refs:
            score += 0.22
        if not query_tokens and (ata_refs or tail_refs):
            score += 0.12

        if score < 0.06:
            continue

        enriched = dict(item)
        enriched["match_score"] = round(min(score, 0.99) * 100, 1)
        ranked.append(enriched)

    ranked.sort(key=lambda entry: entry["match_score"], reverse=True)
    return ranked[:limit]


def _detect_recurrence_alerts(
    records: List[Dict[str, Any]],
    mel_items: List[Dict[str, Any]],
    aog_items: List[Dict[str, Any]],
    window_days: int = 30,
) -> List[Dict[str, Any]]:
    """
    Detect hotspot patterns: ATA chapters or tail+ATA combos with 3+ occurrences
    in the last `window_days` days. Returns ranked alert list.
    """
    cutoff = datetime.utcnow() - timedelta(days=window_days)
    alerts: List[Dict[str, Any]] = []

    ata_counter: Counter = Counter()
    combo_counter: Counter = Counter()

    for rec in records:
        dt_str = str(rec.get("data_cadastro") or rec.get("data_criacao") or "")
        try:
            dt = datetime.strptime(dt_str[:10], "%Y-%m-%d")
        except Exception:
            continue
        if dt < cutoff:
            continue
        raw_ata = str(rec.get("ata", "") or "").strip().split(".")[0]
        tail = str(rec.get("tail", "") or "").strip().upper()
        if raw_ata:
            ata_counter[raw_ata] += 1
        if raw_ata and tail:
            combo_counter[(tail, raw_ata)] += 1

    # AOG contribution — each active AOG bumps the ATA count by 2 (severity)
    for item in aog_items:
        if not item.get("release_date"):
            raw_ata = str(item.get("ata", "") or "").strip().split(".")[0]
            tail = str(item.get("tail", "") or "").strip().upper()
            if raw_ata:
                ata_counter[raw_ata] += 2
            if raw_ata and tail:
                combo_counter[(tail, raw_ata)] += 2

    for ata, count in ata_counter.most_common(8):
        if count >= 3:
            system = ATA_KNOWLEDGE_BASE.get(
                ata, {}).get("system", f"ATA {ata}")
            severity = "CRITICAL" if count >= 7 else "HIGH" if count >= 5 else "WATCH"
            alerts.append({
                "type": "ata_hotspot",
                "ata": ata,
                "system": system,
                "count": count,
                "severity": severity,
                "window_days": window_days,
                "message": (
                    f"[{severity}] ATA {ata} — {system}: "
                    f"{count} occurrences in last {window_days} days. Trend detected."
                ),
            })

    seen_combos: set = set()
    for (tail, ata), count in combo_counter.most_common(8):
        key = f"{tail}:{ata}"
        if count >= 3 and key not in seen_combos:
            seen_combos.add(key)
            system = ATA_KNOWLEDGE_BASE.get(
                ata, {}).get("system", f"ATA {ata}")
            severity = "CRITICAL" if count >= 5 else "HIGH"
            alerts.append({
                "type": "combo_hotspot",
                "tail": tail,
                "ata": ata,
                "system": system,
                "count": count,
                "severity": severity,
                "window_days": window_days,
                "message": (
                    f"[{severity}] Tail {tail} + ATA {ata} ({system}): "
                    f"{count} recurrences in {window_days} days. Recurring issue."
                ),
            })

    return sorted(alerts, key=lambda x: x["count"], reverse=True)[:10]


def _build_operational_snapshot(
    scope: str,
    records: List[Dict[str, Any]],
    mel_items: List[Dict[str, Any]],
    aog_items: List[Dict[str, Any]],
    lru_items: List[Dict[str, Any]],
    ata_focus: str = "",
) -> List[str]:
    analytics = get_ai().get_analytics(records) if records else {}
    open_mel = [item for item in mel_items if not item.get("date_closed")]
    active_aog = [item for item in aog_items if not item.get("release_date")]
    scope_label = {
        "global": "Global",
        "logbook": "Logbook",
        "mel": "MEL",
        "aog": "AOG",
        "fleet": "Fleet",
        "tail": "Tail",
    }.get(scope, "Global")

    lines = [f"Scope analyzed: {scope_label}."]
    if analytics and not analytics.get("error"):
        top_ata = analytics.get("top_ata", [])
        if ata_focus:
            focus_hits = 0
            for item in records:
                ata_value = str(item.get("ata", "")
                                or "").strip().split(".")[0]
                if ata_value == str(ata_focus):
                    focus_hits += 1
            lines.append(
                f"Logbook: {analytics.get('total', 0)} records; ATA focus {ata_focus} ({focus_hits} occurrences in current scope)."
            )
        elif top_ata:
            top = top_ata[0]
            lines.append(
                f"Logbook: {analytics.get('total', 0)} records; dominant ATA {top.get('ata', 'N/A')} ({top.get('count', 0)} occurrences)."
            )
    lines.append(f"Open MEL items: {len(open_mel)}.")
    lines.append(f"Active AOG aircraft: {len(active_aog)}.")
    lines.append(f"Recent LRU replacements tracked: {len(lru_items)}.")
    return lines


def _build_operational_timeline(
    priority_label: str,
    top_recommendation: str,
    record_matches: List[Dict[str, Any]],
    mel_matches: List[Dict[str, Any]],
    aog_matches: List[Dict[str, Any]],
) -> List[str]:
    first_logbook = record_matches[0] if record_matches else {}
    first_mel = mel_matches[0] if mel_matches else {}
    first_aog = aog_matches[0] if aog_matches else {}

    timeline = [
        f"0-2h: Priority {priority_label}. {top_recommendation}",
        (
            "2-8h: Validate technical closure with troubleshooting evidence "
            f"(logbook #{first_logbook.get('id', 'N/A')})."
        ),
        "8-24h: Update preventive ATA plan and register lessons learned.",
    ]

    if first_mel:
        timeline[1] = (
            "2-8h: Confirm operational impact in MEL "
            f"#{first_mel.get('id', 'N/A')} before aircraft release."
        )
    if first_aog:
        timeline[0] = (
            "0-2h: Immediate containment for AOG "
            f"#{first_aog.get('id', 'N/A')} and return-to-service validation."
        )

    return timeline


def _build_learning_profile(
    conversation_history: List[Dict[str, Any]],
    current_query: str,
    scope: str,
) -> Dict[str, Any]:
    user_messages = [
        str(item.get("text", "") or "")
        for item in (conversation_history or [])
        if item.get("type") == "user"
    ]
    user_messages.append(str(current_query or ""))

    joined = "\n".join(user_messages)
    tails = _extract_tail_refs(joined)
    atas = _extract_ata_refs(joined)

    scope_counter = Counter(
        str(item.get("scope", "global") or "global")
        for item in (conversation_history or [])
        if item.get("type") == "user"
    )
    scope_counter[scope or "global"] += 1
    preferred_scope = scope_counter.most_common(
        1)[0][0] if scope_counter else "global"

    interaction_count = len(user_messages)
    learning_stage = "beginner"
    if interaction_count >= 16:
        learning_stage = "advanced"
    elif interaction_count >= 8:
        learning_stage = "intermediate"

    focus_tail = tails[0] if tails else None
    focus_ata = atas[0] if atas else None
    feedback_signal = 0.0
    if focus_ata:
        feedback_signal = round(
            _feedback_acceptance_for_ata(focus_ata) * 100, 1)

    profile_score = min(
        100,
        int((interaction_count * 4) +
            (12 if focus_tail else 0) + (12 if focus_ata else 0)),
    )

    return {
        "preferred_scope": preferred_scope,
        "focus_tail": focus_tail,
        "focus_ata": focus_ata,
        "learning_stage": learning_stage,
        "interaction_count": interaction_count,
        "profile_score": profile_score,
        "feedback_signal": feedback_signal,
    }


def _build_deep_insight(
    query: str,
    learning_profile: Dict[str, Any],
    record_matches: List[Dict[str, Any]],
    mel_matches: List[Dict[str, Any]],
    aog_matches: List[Dict[str, Any]],
    lru_matches: List[Dict[str, Any]],
    priority_label: str,
    priority_score: int,
    deep_mode: bool,
) -> Dict[str, Any]:
    hypotheses: List[Dict[str, Any]] = []
    data_gaps: List[str] = []
    evidence: List[str] = []

    if record_matches:
        first = record_matches[0]
        hypotheses.append(
            {
                "title": "Recurring failure pattern in logbook",
                "confidence": min(95, int(first.get("match_score", 0))),
                "evidence": (
                    f"Record #{first.get('id', 'N/A')} on {first.get('tail', 'N/A')} "
                    f"with ATA {str(first.get('ata', 'N/A')).split('.')[0]}."
                ),
            }
        )
        evidence.append("Logbook presents strong semantic match.")
    else:
        data_gaps.append(
            "No strong similar case found in logbook for the current description.")

    if mel_matches:
        first = mel_matches[0]
        hypotheses.append(
            {
                "title": "Operational impact linked to MEL item",
                "confidence": min(90, int(first.get("match_score", 0))),
                "evidence": f"MEL #{first.get('id', 'N/A')} open for tail {first.get('tail', 'N/A')}.",
            }
        )
        evidence.append("There is correlation with an open MEL item.")

    if aog_matches:
        first = aog_matches[0]
        hypotheses.append(
            {
                "title": "Availability risk (AOG)",
                "confidence": min(92, int(first.get("match_score", 0))),
                "evidence": f"AOG #{first.get('id', 'N/A')} with similar symptoms in the same context.",
            }
        )
        evidence.append("AOG increases urgency for immediate containment.")

    if lru_matches:
        first = lru_matches[0]
        hypotheses.append(
            {
                "title": "Component replacement evidence available",
                "confidence": min(88, int(first.get("match_score", 0))),
                "evidence": (
                    f"LRU #{first.get('id', 'N/A')} on tail {first.get('acft_registration', 'N/A')} "
                    f"for PN OFF {first.get('pn_off', 'N/A')}."
                ),
            }
        )
        evidence.append(
            "LRU history suggests component-level confirmation path.")

    if not hypotheses:
        hypotheses.append(
            {
                "title": "Insufficient diagnostic context",
                "confidence": 35,
                "evidence": "Provide ATA, tail and main symptom to improve precision.",
            }
        )

    if not _extract_tail_refs(query):
        data_gaps.append(
            "Provide the tail to correlate FH/FC and local history.")
    if not _extract_ata_refs(query):
        data_gaps.append(
            "Provide ATA to retrieve technical pattern and applicable manuals.")
    if len(str(query or "").strip()) < 24:
        data_gaps.append(
            "Add symptom detail (when it happens, condition, message, effect).")

    if not data_gaps:
        data_gaps.append("No critical data gaps detected for this analysis.")

    follow_strategy = [
        "Validate root cause with ATA checklist and latest event evidence.",
        "Confirm MEL/AOG cross-impact before releasing the aircraft.",
        "Register effective action and outcome to feed offline learning.",
    ]
    if deep_mode:
        follow_strategy.insert(
            1,
            "Run deep recurrence scan by tail and time window (deep-thinking mode).",
        )

    decision_matrix = {
        "safety": min(100, priority_score + (10 if aog_matches else 0)),
        "operational": min(100, priority_score + (8 if mel_matches else 0)),
        "maintenance": min(100, priority_score + (6 if record_matches else 0) + (5 if lru_matches else 0)),
    }

    reasoning_trace = [
        "1) Signal collection: logbook, MEL, AOG and LRU linked to ATA/tail from the question.",
        "2) Prioritization: higher weight for active AOG, recurrence and historical severity.",
        "3) Hypotheses: selected from highest-similarity matches.",
        "4) Plan: staged response (0-2h, 2-8h, 8-24h) focused on operations.",
    ]
    if deep_mode:
        reasoning_trace.append(
            "5) Deep-thinking step: include data gaps and closure questions."
        )

    return {
        "mode": "deep" if deep_mode else "standard",
        "priority_label": priority_label,
        "priority_score": priority_score,
        "learning_stage": learning_profile.get("learning_stage", "beginner"),
        "hypotheses": hypotheses[:4],
        "evidence_signals": evidence[:5],
        "data_gaps": data_gaps[:5],
        "follow_strategy": follow_strategy,
        "decision_matrix": decision_matrix,
        "reasoning_trace": reasoning_trace,
    }


def _build_copilot_answer(
    query: str,
    scope: str = "global",
    conversation_history: List[Dict[str, Any]] | None = None,
    model_filter: str = "",
    tail_filter: str = "",
    deep_mode: bool = False,
) -> Dict[str, Any]:
    all_records = load_records(limit=4000)
    all_known_tails = _collect_tail_filters(all_records)
    inferred_tail_refs = _extract_tail_hints(query, all_known_tails)
    effective_tail_filter = tail_filter or (
        inferred_tail_refs[0] if len(inferred_tail_refs) == 1 else ""
    )
    effective_model_filter = _effective_model_filter(
        model_filter=model_filter,
        tail_filter=effective_tail_filter,
    )
    records = _filter_records_by_model_tail(
        all_records,
        model_filter=effective_model_filter,
        tail_filter=effective_tail_filter,
    )
    v10_engine = get_v10_engine()
    v10_user_id = session.get("user_id", "anon")
    v10_session_id = session.get("ai_session_id")
    if not v10_session_id:
        v10_session_id = v10_engine.start_user_session(v10_user_id)
        session["ai_session_id"] = v10_session_id
    v10_result = v10_engine.process_query(
        query,
        session_id=v10_session_id,
        user_id=v10_user_id,
    )
    mel_items = _load_mel_context(limit=400)
    aog_items = _load_aog_context(limit=400)
    lru_items = _load_lru_context(limit=700)

    filtered_tail_set = {
        str(item.get("tail", "") or "").strip().upper()
        for item in records
        if str(item.get("tail", "") or "").strip()
    }
    if effective_tail_filter:
        tail_ref = str(effective_tail_filter).strip().upper()
        mel_items = [m for m in mel_items if str(
            m.get("tail", "") or "").strip().upper() == tail_ref]
        aog_items = [m for m in aog_items if str(
            m.get("tail", "") or "").strip().upper() == tail_ref]
        lru_items = [m for m in lru_items if str(
            m.get("tail", "") or "").strip().upper() == tail_ref]
    elif effective_model_filter and filtered_tail_set:
        mel_items = [m for m in mel_items if str(
            m.get("tail", "") or "").strip().upper() in filtered_tail_set]
        aog_items = [m for m in aog_items if str(
            m.get("tail", "") or "").strip().upper() in filtered_tail_set]
        lru_items = [m for m in lru_items if str(
            m.get("tail", "") or "").strip().upper() in filtered_tail_set]

    tail_metrics = _load_tail_metrics()
    ai = get_ai()
    memory_block = _build_chat_memory_context(
        conversation_history or [], max_turns=12)
    model_query = query
    if memory_block:
        model_query = f"{memory_block}\n\nCurrent user request: {query}"

    base = ai.chat(model_query, records=records)
    base_response = str(base.get("response", "") or "").strip()
    if "couldn't identify a specific system" in base_response.lower():
        base_response = (
            "No exact ATA keyword was detected, but contextual matches were found. "
            "Proceeding with a correlation-based diagnosis using logbook, MEL and AOG evidence."
        )
    known_tails = _collect_tail_filters(all_records)
    ata_refs = _extract_ata_refs(query)
    tail_refs = [effective_tail_filter] if effective_tail_filter else _extract_tail_hints(
        query, known_tails)

    record_matches = _find_context_matches(
        records,
        ["problema", "troubleshooting", "solucao", "categoria", "localizacao"],
        query,
        ata_refs,
        tail_refs,
    )
    mel_matches = _find_context_matches(
        mel_items,
        ["system_inop", "notes", "category", "chapter"],
        query,
        ata_refs,
        tail_refs,
    )
    aog_matches = _find_context_matches(
        aog_items,
        ["event_description", "maintenance_actions",
            "interruption_type", "location"],
        query,
        ata_refs,
        tail_refs,
    )
    lru_matches = _find_context_matches(
        lru_items,
        ["pn_off", "sn_off", "pn_on", "sn_on", "removal_reason",
            "position", "removal_classification"],
        query,
        [],
        tail_refs,
    )

    # If an ATA is explicitly requested, keep contextual evidence tightly bound to that ATA.
    if ata_refs:
        focused_record_matches = [
            item for item in record_matches
            if str(item.get("ata", "") or "").strip().split(".")[0] in ata_refs
        ]
        focused_mel_matches = [
            item for item in mel_matches
            if str(item.get("ata", item.get("chapter", "")) or "").strip().split(".")[0] in ata_refs
        ]
        focused_aog_matches = [
            item for item in aog_matches
            if str(item.get("ata", item.get("chapter", "")) or "").strip().split(".")[0] in ata_refs
        ]
        if focused_record_matches:
            record_matches = focused_record_matches
        if focused_mel_matches:
            mel_matches = focused_mel_matches
        if focused_aog_matches:
            aog_matches = focused_aog_matches

    if scope == "logbook":
        mel_matches = []
        aog_matches = []
        lru_matches = []
    elif scope == "mel":
        record_matches = []
        aog_matches = []
        lru_matches = []
    elif scope == "aog":
        record_matches = []
        mel_matches = []
        lru_matches = []

    if scope == "tail" and tail_refs:
        allowed_tails = {ref.upper() for ref in tail_refs}
        record_matches = [m for m in record_matches if str(
            m.get("tail", "")).upper() in allowed_tails]
        mel_matches = [m for m in mel_matches if str(
            m.get("tail", "")).upper() in allowed_tails]
        aog_matches = [m for m in aog_matches if str(
            m.get("tail", "")).upper() in allowed_tails]
        lru_matches = [m for m in lru_matches if str(
            m.get("tail", "")).upper() in allowed_tails]

    if scope == "tail" and not tail_refs and not effective_tail_filter:
        return {
            "response": (
                "Tail scope selected, but no tail reference was found. "
                "Inform a valid tail (example: PR-E2A) or use tail filter to get precise status."
            ),
            "confidence": 55,
            "type": "copilot_contextual",
            "related_atas": sorted(set(base.get("related_atas", []) + ata_refs)),
            "suggestions": base.get("suggestions", []),
            "sources": {
                "records": 0,
                "mel": 0,
                "aog": 0,
                "lru": 0,
                "scope": scope,
                "model_filter": effective_model_filter or "",
                "tail_filter": effective_tail_filter or "",
            },
            "context_consulted": [],
            "memory_used": bool(memory_block),
            "ops_signals": {
                "priority_label": "LOW",
                "priority_score": 0,
                "resolution_rate": 0,
                "matched_open": 0,
                "matched_closed": 0,
                "critical_or_high": 0,
                "active_aog": 0,
            },
            "next_questions": [
                "Which tail should be checked first?",
                "Do you want open logbook items only for a specific tail?",
                "Should I cross-check MEL/AOG status for that tail now?",
            ],
            "learning_profile": _build_learning_profile(
                conversation_history=conversation_history or [],
                current_query=query,
                scope=scope,
            ),
            "deep_insight": _build_deep_insight(
                query=query,
                learning_profile=_build_learning_profile(
                    conversation_history=conversation_history or [],
                    current_query=query,
                    scope=scope,
                ),
                record_matches=[],
                mel_matches=[],
                aog_matches=[],
                lru_matches=[],
                priority_label="LOW",
                priority_score=0,
                deep_mode=deep_mode,
            ),
            "deep_mode": bool(deep_mode),
        }

    matched_open = sum(
        1
        for item in record_matches
        if str(item.get("status_atual", "") or "").strip().lower() in {"open", "in progress", "pending review"}
    )
    matched_closed = max(0, len(record_matches) - matched_open)
    resolution_rate = round(
        (matched_closed / len(record_matches)) * 100, 1) if record_matches else 0.0

    critical_like = sum(
        1
        for item in record_matches
        if str(item.get("prioridade", "") or "").strip().lower() in {"critical", "high"}
    )
    aog_active = sum(1 for item in aog_matches if not item.get("release_date"))
    priority_score = min(100, (critical_like * 15) + (matched_open * 10) +
                         (aog_active * 22) + (len(mel_matches) * 8) + (len(lru_matches) * 4))
    if priority_score >= 70:
        priority_label = "HIGH"
    elif priority_score >= 40:
        priority_label = "MEDIUM"
    else:
        priority_label = "LOW"

    recommendations: List[str] = []
    if aog_matches:
        first = aog_matches[0]
        recommendations.append(
            f"Prioritize AOG release for aircraft {first.get('tail', 'N/A')} by attacking ATA {str(first.get('ata', 'N/A')).split('.')[0]}."
        )
    if mel_matches:
        first = mel_matches[0]
        recommendations.append(
            f"Cross-check with MEL item #{first.get('id', 'N/A')} before operational closure to avoid recurrence."
        )
    if record_matches:
        first = record_matches[0]
        recommendations.append(
            f"Use record #{first.get('id', 'N/A')} as baseline: similar issue on {first.get('tail', 'N/A')} with {first.get('match_score', 0)}% similarity."
        )
    if lru_matches:
        first = lru_matches[0]
        recommendations.append(
            f"Review LRU #{first.get('id', 'N/A')} for tail {first.get('acft_registration', 'N/A')} and PN {first.get('pn_off', 'N/A')} before closure."
        )
    if resolution_rate > 0:
        recommendations.append(
            f"Historical closure rate for similar cases: {resolution_rate}% ({matched_closed}/{len(record_matches)})."
        )
    if tail_refs:
        for tail in tail_refs[:1]:
            metrics = tail_metrics.get(tail, {})
            if metrics:
                recommendations.append(
                    f"Consider operational exposure for {tail}: FH {round(_safe_float(metrics.get('fh'), 0.0), 1)} and FC {int(_safe_float(metrics.get('fc'), 0.0))}."
                )

    if not recommendations:
        recommendations.append(
            "No strong exact match yet; refine the request with ATA, tail and symptom to increase diagnostic precision."
        )

    focused_tail = (effective_tail_filter or (
        tail_refs[0] if tail_refs else "")).strip().upper()
    if focused_tail:
        tail_open = sum(
            1
            for item in records
            if str(item.get("tail", "") or "").strip().upper() == focused_tail
            and str(item.get("status_atual", "") or "").strip().lower() in {"open", "in progress", "pending review"}
        )
        tail_mel_open = sum(
            1
            for item in mel_items
            if str(item.get("tail", "") or "").strip().upper() == focused_tail
            and not item.get("date_closed")
        )
        tail_aog_open = sum(
            1
            for item in aog_items
            if str(item.get("tail", "") or "").strip().upper() == focused_tail
            and not item.get("release_date")
        )
        recommendations.insert(
            0,
            f"Tail {focused_tail} status snapshot: open logbook {tail_open}, open MEL {tail_mel_open}, active AOG {tail_aog_open}.",
        )

    op_timeline = _build_operational_timeline(
        priority_label=priority_label,
        top_recommendation=recommendations[0],
        record_matches=record_matches,
        mel_matches=mel_matches,
        aog_matches=aog_matches,
    )

    learning_profile = _build_learning_profile(
        conversation_history=conversation_history or [],
        current_query=query,
        scope=scope,
    )
    deep_insight = _build_deep_insight(
        query=query,
        learning_profile=learning_profile,
        record_matches=record_matches,
        mel_matches=mel_matches,
        aog_matches=aog_matches,
        lru_matches=lru_matches,
        priority_label=priority_label,
        priority_score=priority_score,
        deep_mode=deep_mode,
    )

    context_consulted: List[Dict[str, Any]] = []
    for item in record_matches[:4]:
        context_consulted.append(
            {
                "source": "logbook",
                "reference": f"#{item.get('id', 'N/A')} | {item.get('tail', 'N/A')} | ATA {str(item.get('ata', 'N/A')).split('.')[0]}",
                "score": item.get("match_score", 0),
                "summary": str(item.get("problema", "") or "")[:130],
                "status": str(item.get("status_atual", "") or "").lower() or "open",
            }
        )
    for item in mel_matches[:3]:
        context_consulted.append(
            {
                "source": "mel",
                "reference": f"MEL #{item.get('id', 'N/A')} | {item.get('tail', 'N/A')} | ATA {str(item.get('ata', 'N/A')).split('.')[0]}",
                "score": item.get("match_score", 0),
                "summary": str(item.get("system_inop", "") or "")[:130],
                "status": "closed" if item.get("date_closed") else "open",
            }
        )
    for item in aog_matches[:3]:
        context_consulted.append(
            {
                "source": "aog",
                "reference": f"AOG #{item.get('id', 'N/A')} | {item.get('tail', 'N/A')} | ATA {str(item.get('ata', 'N/A')).split('.')[0]}",
                "score": item.get("match_score", 0),
                "summary": str(item.get("event_description", "") or "")[:130],
                "status": "operational" if item.get("release_date") else "ground",
            }
        )
    for item in lru_matches[:3]:
        context_consulted.append(
            {
                "source": "lru",
                "reference": f"LRU #{item.get('id', 'N/A')} | {item.get('acft_registration', 'N/A')} | PN {item.get('pn_off', 'N/A')}",
                "score": item.get("match_score", 0),
                "summary": str(item.get("removal_reason", "") or "")[:130],
                "status": str(item.get("removal_classification", "") or "").lower() or "unknown",
            }
        )

    recurrence_alerts = _detect_recurrence_alerts(
        records, mel_items, aog_items, window_days=30)
    fh_fc_priority = _compute_fh_fc_priorities(records)
    projection_signals = _build_projection_signals(records, fh_fc_priority)
    ata_projection = _build_ata_projection(
        records, ata_refs[0] if ata_refs else "")
    autonomy_score = _compute_autonomy_score(
        generated_description=False,
        similar_cases_count=len(record_matches),
        records_count=len(records),
        ata_count=len(ata_refs),
        tail_count=len(tail_refs),
        active_aog_count=aog_active,
        open_mel_count=len(mel_matches),
        trend_direction=str(projection_signals.get(
            "trend_direction", "stable")),
    )
    operational_impact = _build_operational_impact(
        risk={"risk_score": priority_score},
        projection=projection_signals,
        active_aog_count=aog_active,
        open_mel_count=len(mel_matches),
    )

    answer_lines = [base_response or "No response generated.",
                    "", "Operational summary:"]
    answer_lines.extend(
        f"- {line}"
        for line in _build_operational_snapshot(
            scope,
            records,
            mel_items,
            aog_items,
            lru_items,
            ata_focus=(ata_refs[0] if ata_refs else ""),
        )
    )

    if recurrence_alerts:
        answer_lines.append("")
        answer_lines.append("Trend & recurrence alerts (last 30 days):")
        for alert in recurrence_alerts[:5]:
            answer_lines.append(f"- {alert['message']}")

    forecast_items = projection_signals.get("forecast", [])
    if forecast_items:
        forecast_text = ", ".join(
            f"{item.get('month', 'N/A')}: {item.get('count', 0)}" for item in forecast_items[:3]
        )
        answer_lines.append("")
        answer_lines.append("Projected trend (next 3 months):")
        answer_lines.append(
            f"- Direction: {projection_signals.get('trend_direction', 'stable').upper()} | Growth rate: {projection_signals.get('growth_rate_pct', 0)}%."
        )
        answer_lines.append(f"- Forecasted events: {forecast_text}.")
        answer_lines.append(
            f"- Outlook: {projection_signals.get('narrative', 'No projection narrative available.')}")

    if record_matches:
        answer_lines.append("")
        answer_lines.append("Logbook findings:")
        for item in record_matches[:3]:
            answer_lines.append(
                f"- #{item.get('id', 'N/A')} | {item.get('tail', 'N/A')} | ATA {str(item.get('ata', 'N/A')).split('.')[0]} | similaridade {item.get('match_score', 0)}% | {str(item.get('problema', '') or '')[:140]}"
            )

    if mel_matches:
        answer_lines.append("")
        answer_lines.append("MEL findings:")
        for item in mel_matches[:3]:
            status = "closed" if item.get("date_closed") else "open"
            answer_lines.append(
                f"- MEL #{item.get('id', 'N/A')} | {item.get('tail', 'N/A')} | ATA {str(item.get('ata', 'N/A')).split('.')[0]} | status {status} | {str(item.get('system_inop', '') or '')[:120]}"
            )

    if aog_matches:
        answer_lines.append("")
        answer_lines.append("AOG findings:")
        for item in aog_matches[:3]:
            status = "operational" if item.get("release_date") else "ground"
            answer_lines.append(
                f"- AOG #{item.get('id', 'N/A')} | {item.get('tail', 'N/A')} | ATA {str(item.get('ata', 'N/A')).split('.')[0]} | status {status} | {str(item.get('event_description', '') or '')[:120]}"
            )

    if lru_matches:
        answer_lines.append("")
        answer_lines.append("LRU findings:")
        for item in lru_matches[:3]:
            answer_lines.append(
                f"- LRU #{item.get('id', 'N/A')} | {item.get('acft_registration', 'N/A')} | PN OFF {item.get('pn_off', 'N/A')} -> PN ON {item.get('pn_on', 'N/A')} | reason {str(item.get('removal_reason', '') or '')[:90]}"
            )

    answer_lines.append("")
    answer_lines.append("Operational diagnosis:")
    answer_lines.append(
        f"- Priority: {priority_label} (score {priority_score}/100) | open: {matched_open} | critical/high: {critical_like} | active AOG: {aog_active}."
    )
    if resolution_rate > 0:
        answer_lines.append(
            f"- Historical closure capability for similar cases: {resolution_rate}%.")

    answer_lines.append("")
    answer_lines.append("Recommended timeline:")
    answer_lines.extend(f"- {item}" for item in op_timeline)

    answer_lines.append("")
    answer_lines.append("Structured reasoning trace:")
    answer_lines.extend(
        f"- {item}" for item in deep_insight.get("reasoning_trace", [])
    )

    answer_lines.append("")
    answer_lines.append("Recommendations:")
    answer_lines.extend(f"- {item}" for item in recommendations)

    next_questions = [
        "Which ATA and tail should I prioritize next?",
        "Which similar cases were closed successfully and what action resolved them?",
        "Is there any open MEL or AOG blocking release?",
    ]
    if tail_refs:
        next_questions[
            0] = f"Which preventive inspections should be applied next on tail {tail_refs[0]}?"

    response_package = v10_engine.compose_response_package(
        query=query,
        result=v10_result,
        operational_context={
            "base_response": "\n".join(answer_lines).strip(),
            "record_matches": record_matches,
            "mel_matches": mel_matches,
            "aog_matches": aog_matches,
            "lru_matches": lru_matches,
            "tail_filter": effective_tail_filter,
            "recommendations": recommendations,
            "timeline": op_timeline,
            "ops_signals": {
                "priority_label": priority_label,
                "priority_score": priority_score,
            },
            "projection_signals": projection_signals,
            "estimated_time": None,
        },
        user_id=v10_user_id,
    )

    return {
        "response": response_package.get("response_text") or "\n".join(answer_lines).strip(),
        "confidence": min(99, int((v10_result.get("confidence", 0.6) or 0.6) * 100) + (4 if record_matches else 0)),
        "confidence_score": int((v10_result.get("confidence", 0.0) or 0.0) * 100),
        "confidence_grade": v10_result.get("confidence_grade", "C"),
        "primary_intent": v10_result.get("primary_intent"),
        "secondary_intents": v10_result.get("secondary_intents", []),
        "type": "copilot_contextual",
        "related_atas": sorted(set(base.get("related_atas", []) + ata_refs)),
        "suggestions": list(dict.fromkeys((base.get("suggestions", []) or []) + response_package.get("next_questions", []))),
        "sources": {
            "records": len(record_matches),
            "mel": len(mel_matches),
            "aog": len(aog_matches),
            "lru": len(lru_matches),
            "scope": scope,
            "model_filter": effective_model_filter or "",
            "tail_filter": effective_tail_filter or "",
        },
        "context_consulted": context_consulted,
        "memory_used": bool(memory_block),
        "ops_signals": {
            "priority_label": priority_label,
            "priority_score": priority_score,
            "resolution_rate": resolution_rate,
            "matched_open": matched_open,
            "matched_closed": matched_closed,
            "critical_or_high": critical_like,
            "active_aog": aog_active,
            "trend_direction": projection_signals.get("trend_direction", "stable"),
            "growth_rate_pct": projection_signals.get("growth_rate_pct", 0.0),
            "next_30d_expected": projection_signals.get("next_30d_expected", 0),
            "next_90d_expected": projection_signals.get("next_90d_expected", 0),
            "autonomy_score": autonomy_score.get("score", 0),
            "dispatch_risk": operational_impact.get("dispatch_risk", "LOW"),
            "estimated_delay_hours": operational_impact.get("estimated_delay_hours", 0.0),
        },
        "next_questions": list(dict.fromkeys(response_package.get("next_questions", []) + next_questions)),
        "learning_profile": learning_profile,
        "deep_insight": deep_insight,
        "deep_mode": bool(deep_mode),
        "recurrence_alerts": recurrence_alerts,
        "language_variant": response_package.get("language_variant", v10_result.get("language", "pt-BR")),
        "response_sections": response_package.get("response_sections", {}),
        "chart_focus": response_package.get("chart_focus", {}),
        "projection_signals": {
            **projection_signals,
            "ata_projection": ata_projection,
            "autonomy": autonomy_score,
            "operational_impact": operational_impact,
            "chart_brief": response_package.get("chart_brief", {}),
            "chart_focus": response_package.get("chart_focus", {}),
            "suggested_visuals": response_package.get("suggested_visuals", []),
        },
    }


def _tokenize(text: str) -> List[str]:
    if not text:
        return []
    # Include 2-char aviation terms (AC, DC), numbers, and standard words
    words = re.findall(r"\b(?:[a-zA-Z]{2,}|\d{2,})\b", text.lower())
    stop_words = {
        "with", "from", "that", "this", "have", "were", "been", "they",
        "their", "after", "before", "while", "during", "reported", "the",
        "and", "for", "are", "was", "has", "not", "its", "can", "but",
        "due", "per", "via", "ref", "see", "per",
    }
    return [w for w in words if w not in stop_words]


# ==============================================================================
# AVIATION SEMANTIC SYNONYM TABLE
# Enables "electrical" to match "power", "bus tripped" to match "circuit fault", etc.
# ==============================================================================
_AVIATION_SYNONYMS: Dict[str, List[str]] = {
    # Electrical / Power
    "electrical": ["electric", "power", "voltage", "current", "bus", "dc", "ac", "circuit"],
    "electric":   ["electrical", "power", "voltage", "bus", "circuit"],
    "power":      ["electrical", "electric", "voltage", "bus", "supply"],
    "bus":        ["busbar", "electrical", "power", "dc", "ac", "circuit"],
    "dc":         ["direct", "battery", "voltage", "electrical", "power"],
    "ac":         ["alternating", "generator", "electrical", "power"],
    "generator":  ["gen", "alternator", "power", "ac", "electrical", "genset"],
    "battery":    ["batt", "dc", "accumulator", "charge", "power"],
    "tripped":    ["trip", "fault", "open", "disconnect", "failed", "triggered"],
    "trip":       ["tripped", "fault", "open", "disconnect", "failed"],
    "circuit":    ["electrical", "bus", "breaker", "cb", "power"],
    "breaker":    ["cb", "circuit", "tripped", "open", "overcurrent"],
    # Hydraulic
    "hydraulic":  ["hyd", "fluid", "pressure", "pump", "actuator", "line"],
    "hyd":        ["hydraulic", "fluid", "pressure", "pump", "actuator"],
    "actuator":   ["actuated", "servo", "ram", "hydraulic", "hyd"],
    "pump":       ["hydraulic", "pressure", "fluid", "motor", "electric"],
    # Fuel
    "fuel":       ["jpa", "jpb", "flow", "pump", "combustion", "tank", "quantity"],
    # Engine
    "engine":     ["motor", "turbofan", "egt", "fadec", "fan", "turbine", "powerplant"],
    "motor":      ["engine", "turbine", "egt", "fadec", "powerplant"],
    "egt":        ["temperature", "exhaust", "engine", "hot", "thermal"],
    "fadec":      ["eec", "engine", "control", "electronic", "fuel", "management"],
    "vibration":  ["vib", "imbalance", "shake", "vibrate", "oscillation"],
    "fan":        ["n1", "blade", "engine", "compressor", "fod"],
    "turbine":    ["engine", "hot", "section", "hpt", "lpt", "egt"],
    # Pneumatic / Bleed
    "bleed":      ["air", "pack", "pneumatic", "pressure", "valve", "supply"],
    "pneumatic":  ["bleed", "air", "pressure", "pack", "supply"],
    "pack":       ["air", "conditioning", "bleed", "cooling", "acs", "thermal"],
    "air":        ["pneumatic", "bleed", "pack", "ventilation", "supply"],
    "pressurization": ["cabin", "pack", "bleed", "cpcs", "outflow", "valve"],
    # Avionics / Navigation
    "avionics":   ["display", "fms", "navigation", "gps", "computer", "system"],
    "navigation": ["nav", "gps", "irs", "inertial", "vnav", "adiru"],
    "inertial":   ["irs", "navigation", "gyro", "heading", "attitude", "adiru"],
    "display":    ["efis", "mfd", "pfd", "cdu", "screen", "avionics"],
    "fms":        ["flight", "management", "navigation", "computer", "cdu"],
    "gps":        ["navigation", "position", "gnss", "satellite"],
    # Flight Controls
    "flap":       ["flaps", "slat", "lift", "high", "control", "fcs"],
    "slat":       ["flap", "leading", "edge", "lift", "control"],
    "rudder":     ["yaw", "control", "surface", "pedal", "fcs"],
    "elevator":   ["pitch", "control", "surface", "fcs", "horizontal"],
    "aileron":    ["roll", "control", "surface", "lateral", "fcs"],
    "spoiler":    ["speedbrake", "roll", "surface", "fcs", "drag"],
    # Landing Gear
    "gear":       ["landing", "wheel", "retract", "extend", "lgciu", "undercarriage"],
    "brake":      ["braking", "wheel", "decel", "antiskid", "autobrake", "carbon"],
    "tire":       ["tyre", "wheel", "brake", "gear", "landing"],
    "lgciu":      ["gear", "landing", "control", "indication", "sensor"],
    # APU
    "apu":        ["auxiliary", "power", "unit", "starter", "bleed", "apuc", "ground"],
    "apuc":       ["apu", "controller", "starter", "unit"],
    # Oxygen
    "oxygen":     ["o2", "oxy", "mask", "portable", "passenger", "crew"],
    # General failure language
    "fault":      ["fail", "failure", "defect", "malfunction", "error", "flt", "snag"],
    "fail":       ["fault", "failure", "defect", "malfunction", "inop"],
    "failure":    ["fault", "fail", "defect", "malfunction", "inop", "snag"],
    "inop":       ["inoperative", "fail", "fault", "failure", "unserviceable"],
    "inoperative": ["inop", "fail", "fault", "failed", "unserviceable"],
    "warning":    ["caution", "alert", "message", "cmc", "ecam", "eicas"],
    "caution":    ["warning", "alert", "message", "ecam", "eicas"],
    "alert":      ["warning", "caution", "message", "ecam", "eicas"],
    "ecam":       ["warning", "caution", "alert", "message", "system"],
    "leak":       ["leaking", "seep", "drip", "loss", "fluid", "external"],
    "pressure":   ["psi", "bar", "low", "high", "press", "indication"],
    "temperature": ["temp", "hot", "cold", "egt", "thermal", "overheat"],
    "valve":      ["shutoff", "bypass", "check", "solenoid", "control", "actuated"],
    "sensor":     ["probe", "transducer", "detector", "switch", "transmitter"],
    "check":      ["inspect", "verify", "test", "examine", "bite", "function"],
    "inspect":    ["check", "visual", "test", "verify", "examination"],
    "replace":    ["swap", "change", "lru", "removal", "install", "exchange"],
    "aog":        ["grounded", "ground", "unserviceable", "inop", "no-go"],
    "mel":        ["minimum", "equipment", "dispatch", "deferral"],
    "snag":       ["fault", "defect", "failure", "squawk", "write-up"],
    "squawk":     ["snag", "fault", "defect", "write-up", "report"],
    "intermittent": ["occasional", "erratic", "sporadic", "random", "recurrent"],
    "recurrent":  ["recurring", "repeat", "intermittent", "chronic", "persistent"],
    "low":        ["insufficient", "under", "below", "reduced", "minimum"],
    "high":       ["excessive", "above", "over", "elevated", "maximum"],
    "open":       ["disconnected", "failed", "circuit", "tripped", "broken"],
    "stuck":      ["jammed", "seized", "binding", "frozen", "blocked"],
    "oil":        ["lubricant", "lubrication", "chip", "pressure", "consumption"],
    "vibration":  ["vib", "imbalance", "shake", "oscillation", "buffet"],
    "noise":      ["sound", "vibration", "abnormal", "unusual", "heard"],
    "smoke":      ["fire", "fumes", "burning", "smell", "odor", "indication"],
    "overheating": ["overheat", "temperature", "hot", "thermal", "egt"],
    "overheat":   ["overheating", "temperature", "hot", "thermal", "egt"],
}

# Simple stem normalization table (suffix stripping for common aviation terms)
_STEM_MAP: Dict[str, str] = {
    "tripped": "trip", "failed": "fail", "failing": "fail", "fails": "fail",
    "leaking": "leak", "leaks": "leak", "leaked": "leak",
    "vibrating": "vibrate", "vibrations": "vibration", "vibrated": "vibrate",
    "checking": "check", "checked": "check", "checks": "check",
    "replacing": "replace", "replaced": "replace", "replaces": "replace",
    "warnings": "warning", "cautions": "caution", "alerts": "alert",
    "faults": "fault", "failures": "failure", "defects": "defect",
    "actuating": "actuate", "actuated": "actuate", "actuates": "actuate",
    "pressures": "pressure", "temperatures": "temperature",
    "sensors": "sensor", "valves": "valve", "probes": "probe",
    "generators": "generator", "batteries": "battery",
    "engines": "engine", "motors": "motor", "turbines": "turbine",
    "inspected": "inspect", "inspecting": "inspect", "inspections": "inspect",
    "observed": "observe", "observing": "observe", "noted": "note",
    "reported": "report", "reports": "report",
    "installed": "install", "installing": "install", "installation": "install",
    "removed": "remove", "removing": "remove", "removal": "remove",
    "operations": "operation", "operational": "operation",
    "indications": "indication", "indicated": "indicate",
    "flaps": "flap", "slats": "slat", "spoilers": "spoiler",
    "brakes": "brake", "tires": "tire", "tyres": "tire",
    "pumps": "pump", "actuators": "actuator", "connectors": "connector",
    "breakers": "breaker", "switches": "switch", "relays": "relay",
}


def _normalize_token(token: str) -> str:
    """Apply simple stem normalization."""
    return _STEM_MAP.get(token, token)


def _expand_tokens(tokens: List[str]) -> List[str]:
    """Expand token list with synonyms for aviation-aware semantic matching."""
    expanded: List[str] = []
    seen: set = set()
    for tok in tokens:
        normalized = _normalize_token(tok)
        if normalized not in seen:
            expanded.append(normalized)
            seen.add(normalized)
        for syn in _AVIATION_SYNONYMS.get(normalized, []):
            if syn not in seen:
                expanded.append(syn)
                seen.add(syn)
    return expanded


def _jaccard_similarity(tokens_a: List[str], tokens_b: List[str]) -> float:
    """Kept for backward compatibility. Prefer _semantic_score for new code."""
    set_a = set(tokens_a)
    set_b = set(tokens_b)
    if not set_a or not set_b:
        return 0.0
    inter = len(set_a.intersection(set_b))
    union = len(set_a.union(set_b))
    return inter / union if union > 0 else 0.0


def _semantic_score(tokens_a: List[str], tokens_b: List[str]) -> float:
    """
    Multi-layer semantic similarity:
    1. Expanded Jaccard with synonym expansion (60%)
    2. Containment: how much of the smaller set is covered (40%)
    Returns value in [0.0, 1.0].
    """
    if not tokens_a or not tokens_b:
        return 0.0
    exp_a = set(_expand_tokens(tokens_a))
    exp_b = set(_expand_tokens(tokens_b))
    inter = len(exp_a & exp_b)
    union = len(exp_a | exp_b)
    expanded_jaccard = inter / union if union > 0 else 0.0
    smaller = min(len(exp_a), len(exp_b))
    containment = inter / smaller if smaller > 0 else 0.0
    return round(0.6 * expanded_jaccard + 0.4 * containment, 4)


def _severity_weight(level: str) -> float:
    ref = str(level or "").strip().lower()
    if ref == "critical":
        return 1.0
    if ref == "high":
        return 0.75
    if ref == "medium":
        return 0.5
    if ref == "low":
        return 0.25
    return 0.5


def _find_similar_cases(
    records: List[Dict[str, Any]],
    ata: str,
    description: str,
    tail: str,
    limit: int = 5,
) -> List[Dict[str, Any]]:
    if not records:
        return []

    ata_ref = str(ata or "").strip().split(".")[0]
    tail_ref = str(tail or "").strip()
    query_tokens = _tokenize(description)
    scored: List[Dict[str, Any]] = []

    for rec in records:
        rec_desc = str(rec.get("problema", "")).strip()
        if not rec_desc:
            continue
        rec_ata = str(rec.get("ata", "")).strip().split(".")[0]
        rec_tail = str(rec.get("tail", "")).strip()
        rec_tokens = _tokenize(rec_desc)

        score = _semantic_score(query_tokens, rec_tokens)
        if ata_ref and rec_ata == ata_ref:
            score += 0.18
        if tail_ref and rec_tail == tail_ref:
            score += 0.12

        if score < 0.08:
            continue

        scored.append(
            {
                "id": rec.get("id"),
                "tail": rec_tail or "N/A",
                "ata": rec_ata or "N/A",
                "status": rec.get("status_atual", "N/A"),
                "priority": rec.get("prioridade", "N/A"),
                "problem": rec_desc[:220],
                "similarity": round(min(score, 0.99) * 100, 1),
            }
        )

    scored.sort(key=lambda x: x["similarity"], reverse=True)
    return scored[:limit]


def _build_comparative_troubleshooting(
    records: List[Dict[str, Any]],
    similar_cases: List[Dict[str, Any]],
) -> Dict[str, Any]:
    if not records or not similar_cases:
        return {
            "summary": "Insufficient similar history to build comparative troubleshooting.",
            "historical_patterns": [],
            "recommended_focus": [],
        }

    records_by_id: Dict[str, Dict[str, Any]] = {
        str(rec.get("id")): rec for rec in records if rec.get("id") is not None
    }

    patterns: List[Dict[str, Any]] = []
    focus_actions: List[str] = []
    for case in similar_cases[:3]:
        ref = records_by_id.get(str(case.get("id")))
        if not ref:
            continue

        troubleshooting = str(ref.get("troubleshooting", "") or "").strip()
        solution = str(ref.get("solucao", "") or "").strip()
        status = str(ref.get("status_atual", "") or "N/A").strip()

        if troubleshooting:
            focus_actions.append(troubleshooting.split(".")[0][:180])
        elif solution:
            focus_actions.append(solution.split(".")[0][:180])

        patterns.append(
            {
                "case_id": case.get("id"),
                "similarity": case.get("similarity", 0),
                "tail": case.get("tail", "N/A"),
                "ata": case.get("ata", "N/A"),
                "historical_problem": case.get("problem", ""),
                "historical_troubleshooting": troubleshooting or "No troubleshooting text available.",
                "historical_solution": solution or "No solution text available.",
                "status": status,
            }
        )

    focus_unique: List[str] = []
    for item in focus_actions:
        norm = item.lower()
        if not item or norm in {x.lower() for x in focus_unique}:
            continue
        focus_unique.append(item)

    if patterns:
        summary = (
            f"Comparative analysis built from {len(patterns)} high-similarity historical cases. "
            "Use recurring troubleshooting path before escalating to deep maintenance."
        )
    else:
        summary = "Similar cases found, but historical troubleshooting fields are limited."

    return {
        "summary": summary,
        "historical_patterns": patterns,
        "recommended_focus": focus_unique[:4],
    }


def _compute_failure_risk(
    severity: str,
    confidence: float,
    tail_count: int,
    ata_count: int,
    fh: float,
    fc: float,
    max_fh: float,
    max_fc: float,
    feedback_acceptance: float,
) -> Dict[str, Any]:
    sev_factor = _severity_weight(severity)
    tail_factor = min(tail_count / 6.0, 1.0)
    ata_factor = min(ata_count / 10.0, 1.0)
    fh_factor = 0.0 if max_fh <= 0 else min(fh / max_fh, 1.0)
    fc_factor = 0.0 if max_fc <= 0 else min(fc / max_fc, 1.0)
    exposure_factor = (0.6 * fh_factor) + (0.4 * fc_factor)
    confidence_penalty = 1.0 - min(max(confidence / 100.0, 0.0), 1.0)
    feedback_penalty = 1.0 - min(max(feedback_acceptance, 0.0), 1.0)

    risk_score = round(
        (
            (28 * sev_factor)
            + (16 * tail_factor)
            + (16 * ata_factor)
            + (20 * exposure_factor)
            + (12 * confidence_penalty)
            + (8 * feedback_penalty)
        ),
        1,
    )
    risk_score = min(risk_score, 100.0)

    if risk_score >= 75:
        risk_level = "critical"
        inspection_depth = "deep"
    elif risk_score >= 55:
        risk_level = "high"
        inspection_depth = "enhanced"
    elif risk_score >= 35:
        risk_level = "medium"
        inspection_depth = "standard"
    else:
        risk_level = "low"
        inspection_depth = "targeted"

    return {
        "risk_score": risk_score,
        "risk_level": risk_level,
        "inspection_depth": inspection_depth,
        "drivers": {
            "severity_factor": round(sev_factor, 3),
            "tail_recurrence_factor": round(tail_factor, 3),
            "ata_recurrence_factor": round(ata_factor, 3),
            "exposure_factor": round(exposure_factor, 3),
            "confidence_penalty": round(confidence_penalty, 3),
            "feedback_penalty": round(feedback_penalty, 3),
        },
    }


def _build_recommended_plan(
    risk: Dict[str, Any],
    analysis: Dict[str, Any],
    similar_cases: List[Dict[str, Any]],
    tail: str,
    ata: str,
) -> List[Dict[str, Any]]:
    risk_level = str(risk.get("risk_level", "medium")).lower()
    inspection_depth = risk.get("inspection_depth", "standard")
    actions = analysis.get("quick_actions", []) or []
    steps = analysis.get("troubleshooting_steps", []) or []
    first_action = (
        actions[0]
        if actions
        else "Run ATA standard troubleshooting sequence."
    )
    first_step = (
        steps[0]
        if steps
        else "Capture fault snapshot and maintenance log evidence."
    )

    plan: List[Dict[str, Any]] = [
        {
            "phase": "Immediate containment",
            "priority": "P1",
            "action": first_action,
            "depth": inspection_depth,
        },
        {
            "phase": "Technical verification",
            "priority": "P1" if risk_level in ("critical", "high") else "P2",
            "action": first_step,
            "depth": inspection_depth,
        },
        {
            "phase": "Reliability prevention",
            "priority": "P2",
            "action": (
                f"Create recurrent control for tail {tail or 'N/A'} "
                f"and ATA {ata or analysis.get('matched_ata', 'N/A')} "
                "with pre-flight trigger checklist."
            ),
            "depth": "fleet",
        },
    ]

    if similar_cases:
        plan.append(
            {
                "phase": "Lessons learned",
                "priority": "P3",
                "action": (
                    f"Compare with top similar case "
                    f"#{similar_cases[0].get('id', 'N/A')} "
                    "before closing the record."
                ),
                "depth": "knowledge",
            }
        )

    return plan


def _button_identity_for_risk(risk_level: str) -> Dict[str, str]:
    level = str(risk_level or "medium").lower()
    if level == "critical":
        return {"icon": "bi-exclamation-triangle-fill", "tone": "danger"}
    if level == "high":
        return {"icon": "bi-lightning-charge-fill", "tone": "warning"}
    if level == "medium":
        return {"icon": "bi-shield-check", "tone": "info"}
    return {"icon": "bi-check2-circle", "tone": "success"}


def _load_records_from_mysql(limit: int = 2000) -> List[Dict[str, Any]]:
    cfg = current_app.config
    db_name = str(cfg.get("MYSQL_DB", "troubleshooting_db")).strip()
    table_name = f"{db_name}.falhas"

    connection = pymysql.connect(
        host=cfg.get("MYSQL_HOST", "localhost"),
        user=cfg.get("MYSQL_USER", "root"),
        password=cfg.get("MYSQL_PASSWORD", ""),
        database=db_name,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        connect_timeout=4,
    )
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                SELECT
                    id,
                    tail,
                    modelo,
                    prioridade,
                    categoria,
                    problema,
                    ata,
                    localizacao,
                    tecnico_responsavel,
                    tempo_estimado_horas,
                    status_atual,
                    troubleshooting,
                    solucao,
                    data_cadastro,
                    data_criacao,
                    criado_por,
                    0 AS safety
                FROM {table_name}
                ORDER BY data_cadastro DESC, id DESC
                LIMIT %s
                """,
                (int(limit),),
            )
            return list(cursor.fetchall())
    finally:
        connection.close()


def load_records(limit: int = 2000) -> List[Dict[str, Any]]:
    try:
        records = _load_records_from_mysql(limit=limit)
    except Exception:
        records = _load_records_from_fallback()
    return _merge_tail_metrics(records)


# ══════════════════════════════════════════════════════════════════════════════
# Phase 3 — Autonomous Mission Queue  (REST API + in-memory store)
# ══════════════════════════════════════════════════════════════════════════════

# In-memory mission queue store: { task_id: task_dict }
_MISSION_STORE: dict[str, dict] = {}

_VALID_STATUSES = {"pending", "in_progress", "done", "cancelled"}
_VALID_PRIORITIES = {"P1", "P2", "P3", "P4"}


def _mission_task_defaults(data: dict) -> dict:
    """Build a normalised task dict from raw POST/PUT payload."""
    now_iso = __import__("datetime").datetime.utcnow(
    ).isoformat(timespec="seconds") + "Z"
    task_id = data.get("id") or str(_uuid.uuid4())
    priority = data.get("priority", "P3")
    if priority not in _VALID_PRIORITIES:
        priority = "P3"
    urgency = float(data.get("urgency_score") or 0.0)
    sla_map = {"P1": "6h", "P2": "24h", "P3": "72h", "P4": "168h"}
    return {
        "id": task_id,
        "rank": int(data.get("rank") or 1),
        "tail": sanitize_input(str(data.get("tail") or "N/A"), _FIELD_MAX_LEN),
        "ata": sanitize_input(str(data.get("ata") or "N/A"), 8),
        "urgency_score": round(urgency, 1),
        "priority": priority,
        "recommended_sla": data.get("recommended_sla") or sla_map.get(priority, "72h"),
        "action": sanitize_input(str(data.get("action") or "Check and resolve open findings."), 500),
        "status": data.get("status", "pending") if data.get("status") in _VALID_STATUSES else "pending",
        "created_at": data.get("created_at") or now_iso,
        "updated_at": now_iso,
    }


@analytics_bp.route("/api/mission/queue", methods=["GET"])
def api_mission_queue_list():
    """GET /api/mission/queue — return all tasks sorted by urgency desc."""
    if not _check_rate_limit(request.remote_addr):
        return jsonify({"success": False, "error": "Rate limit exceeded"}), 429
    tasks = sorted(_MISSION_STORE.values(), key=lambda t: t.get(
        "urgency_score", 0), reverse=True)
    # Re-rank after sort
    for pos, task in enumerate(tasks, start=1):
        task["rank"] = pos
    return jsonify({"success": True, "queue": tasks, "count": len(tasks)})


@analytics_bp.route("/api/mission/queue", methods=["POST"])
def api_mission_queue_create():
    """POST /api/mission/queue — create a new task."""
    if not _check_rate_limit(request.remote_addr):
        return jsonify({"success": False, "error": "Rate limit exceeded"}), 429
    data = request.get_json(silent=True) or {}
    task = _mission_task_defaults(data)
    _MISSION_STORE[task["id"]] = task
    return jsonify({"success": True, "task": task}), 201


@analytics_bp.route("/api/mission/queue/<string:task_id>", methods=["PUT"])
def api_mission_queue_update(task_id: str):
    """PUT /api/mission/queue/<id> — update status/action/priority of a task."""
    if not _check_rate_limit(request.remote_addr):
        return jsonify({"success": False, "error": "Rate limit exceeded"}), 429
    task_id = sanitize_input(task_id, 64)
    if task_id not in _MISSION_STORE:
        return jsonify({"success": False, "error": "Task not found"}), 404
    data = request.get_json(silent=True) or {}
    task = _deepcopy(_MISSION_STORE[task_id])
    if "status" in data and data["status"] in _VALID_STATUSES:
        task["status"] = data["status"]
    if "action" in data:
        task["action"] = sanitize_input(str(data["action"]), 500)
    if "priority" in data and data["priority"] in _VALID_PRIORITIES:
        task["priority"] = data["priority"]
    if "urgency_score" in data:
        try:
            task["urgency_score"] = round(float(data["urgency_score"]), 1)
        except (ValueError, TypeError):
            pass
    task["updated_at"] = __import__(
        "datetime").datetime.utcnow().isoformat(timespec="seconds") + "Z"
    _MISSION_STORE[task_id] = task
    return jsonify({"success": True, "task": task})


@analytics_bp.route("/api/mission/queue/<string:task_id>", methods=["DELETE"])
def api_mission_queue_delete(task_id: str):
    """DELETE /api/mission/queue/<id> — remove a task from the queue."""
    if not _check_rate_limit(request.remote_addr):
        return jsonify({"success": False, "error": "Rate limit exceeded"}), 429
    task_id = sanitize_input(task_id, 64)
    removed = _MISSION_STORE.pop(task_id, None)
    if removed is None:
        return jsonify({"success": False, "error": "Task not found"}), 404
    return jsonify({"success": True, "removed_id": task_id})


@analytics_bp.route("/api/mission/queue/batch", methods=["POST"])
def api_mission_queue_batch():
    """POST /api/mission/queue/batch — bulk-import tasks from AI projection_signals."""
    if not _check_rate_limit(request.remote_addr):
        return jsonify({"success": False, "error": "Rate limit exceeded"}), 429
    data = request.get_json(silent=True) or {}
    tasks_raw = data.get("tasks") or []
    if not isinstance(tasks_raw, list):
        return jsonify({"success": False, "error": "tasks must be a list"}), 400
    created = []
    for raw in tasks_raw[:20]:  # cap batch at 20
        task = _mission_task_defaults(raw)
        _MISSION_STORE[task["id"]] = task
        created.append(task)
    return jsonify({"success": True, "created": len(created), "tasks": created}), 201


# ── End Phase 3 Mission Queue ─────────────────────────────────────────────────

@analytics_bp.route("/ai_analysis", methods=["GET"])
def ai_analysis_page():
    all_records = load_records(limit=2000)
    records = _filter_records_by_model_tail(
        all_records,
        model_filter=DEFAULT_E2_MODEL_FILTER,
    )
    ai = get_ai()
    analytics = ai.get_analytics(records)
    ata_systems = ai.list_ata_systems()
    model_filters = _collect_model_filters(all_records)
    tail_filters = _collect_tail_filters(all_records)
    fleet_snapshot = _build_fleet_snapshot(records)

    top_failure = "N/A"
    if isinstance(analytics, dict):
        top_keywords = analytics.get("top_keywords", [])
        if top_keywords:
            top_failure = top_keywords[0][0]

    return render_template(
        "ai_analysis.html",
        analytics=analytics,
        ata_systems=ata_systems,
        records_count=len(records),
        top_failure_keyword=top_failure,
        model_filters=model_filters,
        tail_filters=tail_filters,
        default_model_filter=DEFAULT_E2_MODEL_FILTER,
        fleet_rows=fleet_snapshot.get("fleet_rows", []),
        excellent_count=fleet_snapshot.get("excellent_count", 0),
        good_count=fleet_snapshot.get("good_count", 0),
        fair_count=fleet_snapshot.get("fair_count", 0),
        mel_open_count=fleet_snapshot.get("mel_open_count", 0),
    )


@analytics_bp.route("/ui/v10", methods=["GET"])
def ui_v10_professional_page():
    """Dedicated route for the professional V10 chat UI."""
    return render_template("ui_v10_professional.html")


@analytics_bp.route("/exceedance_analysis", methods=["GET"])
def exceedance_analysis_page():
    """Dedicated page for exceedance-event and document-assisted troubleshooting."""
    return render_template("exceedance_analysis.html")


def _extract_text_from_pdf_bytes(pdf_bytes: bytes) -> str:
    """Extract text from PDF using pypdf; flag scanned PDFs when text is minimal."""
    if not pdf_bytes:
        return ""
    text = ""
    try:
        from pypdf import PdfReader  # type: ignore
        reader = PdfReader(io.BytesIO(pdf_bytes))
        parts: List[str] = []
        for page in reader.pages[:30]:
            parts.append(page.extract_text() or "")
        text = "\n".join(parts).strip()
    except Exception:
        return ""

    # Heuristic: fewer than 60 chars per page → likely a scanned PDF
    page_count = max(1, len(text.splitlines()) // 50) if text else 1
    if text and len(text) < page_count * 60:
        return text + "\n[NOTICE: PDF appears to be scanned or image-based. Text extraction may be incomplete. Manual review recommended.]"
    return text


_ACMS_FDR_COLUMN_MAP: Dict[str, List[str]] = {
    "timestamp": ["time", "datetime", "event_time", "utc_time", "local_time", "date_time", "timestamp_utc", "recorded_at", "data_hora", "hora", "tempo"],
    "event": ["event_name", "event_type", "occurrence", "occurrence_name", "evento", "evento_nome"],
    "message": ["msg", "alert", "alert_message", "description", "fault_message", "detail", "details", "mensagem", "descricao"],
    "tail": ["aircraft", "aircraft_tail", "aircraft_reg", "registration", "tail_number", "matricula"],
    "flight_phase": ["phase", "phase_of_flight", "flight_leg_phase", "fase_voo"],
    "ias": ["indicated_airspeed", "computed_airspeed", "speed_ias", "vcas", "airspeed", "velocidade_indicada"],
    "cas": ["calibrated_airspeed", "speed_cas", "velocidade_calibrada"],
    "mach": ["mach_number", "mach_no"],
    "vertical_speed": ["vs", "vertical_spd", "sink_rate", "rate_of_descent", "vertical_velocity", "razao_descida"],
    "vertical_acceleration_g": ["vertical_accel_g", "vert_accel_g", "normal_accel_g", "nz", "g_load", "vertical_g", "normal_acceleration_g", "aceleracao_vertical_g"],
    "touchdown_g": ["touchdown_load", "touchdown_g_load", "touchdown_vertical_g"],
    "flap_position": ["flap", "flap_pos", "flaps", "slat_flap_position", "posicao_flap"],
    "gear_position": ["gear", "landing_gear_position", "gear_pos", "posicao_trem"],
    "radio_altitude": ["radalt", "radio_alt", "height_agl", "agl", "altura_radio"],
    "altitude": ["pressure_altitude", "alt", "altitude_ft", "altitude_msl", "altitude_pressao"],
    "gross_weight": ["gross_wt", "aircraft_weight", "landing_weight", "peso_bruto", "peso_aeronave"],
    "engine_n1": ["n1", "eng_n1", "engine_1_n1", "engine_2_n1"],
    "engine_egt": ["egt", "engine_egt_c", "itt", "itt_c", "temp_turbina"],
}

_ACMS_FDR_COLUMN_ALIASES: Dict[str, str] = {
    alias: canonical
    for canonical, aliases in _ACMS_FDR_COLUMN_MAP.items()
    for alias in [canonical, *aliases]
}

_CSV_EVENT_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "generic_exceedance": {
        "required_any": [
            ["timestamp"],
            ["event", "message"],
        ],
        "recommended": ["tail", "flight_phase", "ias", "altitude"],
    },
    "hard_landing": {
        "required_any": [
            ["timestamp"],
            ["event", "message"],
            ["vertical_acceleration_g", "touchdown_g", "vertical_speed"],
        ],
        "recommended": ["radio_altitude", "gross_weight", "tail"],
    },
    "flap_overspeed": {
        "required_any": [
            ["timestamp"],
            ["event", "message"],
            ["flap_position"],
            ["ias", "cas"],
        ],
        "recommended": ["flight_phase", "tail", "altitude"],
    },
    "landing_overspeed": {
        "required_any": [
            ["timestamp"],
            ["event", "message"],
            ["ias", "cas"],
            ["gear_position", "radio_altitude", "vertical_speed"],
        ],
        "recommended": ["tail", "gross_weight"],
    },
    "engine_exceedance": {
        "required_any": [
            ["timestamp"],
            ["event", "message"],
            ["engine_n1", "engine_egt"],
        ],
        "recommended": ["altitude", "flight_phase", "tail"],
    },
}


def _normalize_csv_header(header: str) -> str:
    """Normalize vendor-specific ACMS/FDR column names into canonical names."""
    raw = str(header or "").strip().lower()
    if not raw:
        return ""
    raw = re.sub(r"\([^)]*\)|\[[^\]]*\]", " ", raw)
    raw = raw.replace("%", " percent ")
    raw = re.sub(r"[^a-z0-9]+", "_", raw).strip("_")
    return _ACMS_FDR_COLUMN_ALIASES.get(raw, raw)


def _parse_time_value(value: str) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    candidate = text.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(candidate)
    except ValueError:
        pass
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S",
        "%d/%m/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%d/%m/%Y %H:%M",
        "%H:%M:%S",
    ):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _detect_csv_event_type(csv_rows: List[Dict[str, str]]) -> str:
    """Infer the operational event type from normalized CSV columns."""
    if not csv_rows:
        return "generic_exceedance"
    keys = {str(k).strip().lower()
            for row in csv_rows[:40] for k in row.keys()}
    if {"vertical_acceleration_g", "touchdown_g", "vertical_speed"} & keys:
        return "hard_landing"
    if "flap_position" in keys and ({"ias", "cas"} & keys):
        return "flap_overspeed"
    if "gear_position" in keys and ({"ias", "cas", "vertical_speed", "radio_altitude"} & keys):
        return "landing_overspeed"
    if {"engine_n1", "engine_egt"} & keys:
        return "engine_exceedance"
    return "generic_exceedance"


def _validate_csv_schema(csv_rows: List[Dict[str, str]], event_type: str = "") -> Dict[str, Any]:
    """Validate normalized CSV rows against a minimal operational schema."""
    if not csv_rows:
        return {
            "event_type": event_type or "generic_exceedance",
            "valid": False,
            "required_missing": ["no_rows"],
            "recommended_missing": [],
            "detected_columns": [],
        }
    detected_columns = sorted({str(k).strip().lower(
    ) for row in csv_rows[:60] for k in row.keys() if str(k).strip()})
    schema_name = event_type or _detect_csv_event_type(csv_rows)
    schema = _CSV_EVENT_SCHEMAS.get(
        schema_name, _CSV_EVENT_SCHEMAS["generic_exceedance"])
    required_missing: List[str] = []
    for group in schema.get("required_any", []):
        if not any(col in detected_columns for col in group):
            required_missing.append(" | ".join(group))
    recommended_missing = [col for col in schema.get(
        "recommended", []) if col not in detected_columns]
    return {
        "event_type": schema_name,
        "valid": not required_missing,
        "required_missing": required_missing,
        "recommended_missing": recommended_missing,
        "detected_columns": detected_columns[:30],
    }


def _detect_time_column(csv_rows: List[Dict[str, str]]) -> str:
    """Detect the most reliable time-like column from normalized CSV rows."""
    if not csv_rows:
        return ""
    candidates = ["timestamp", "event_time", "utc_time",
                  "local_time", "datetime", "date", "time"]
    best_key = ""
    best_score = -1
    for key in candidates:
        score = sum(1 for row in csv_rows[:120]
                    if str(row.get(key, "")).strip())
        if score > best_score:
            best_score = score
            best_key = key
    return best_key if best_score > 0 else ""


def _extract_rows_from_csv_bytes(csv_bytes: bytes) -> List[Dict[str, str]]:
    """Parse CSV bytes into a list of dict rows (best effort)."""
    if not csv_bytes:
        return []
    text = ""
    for encoding in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = csv_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if not text:
        text = csv_bytes.decode("utf-8", errors="replace")
    sample = text[:2048]
    try:
        dialect = csv.Sniffer().sniff(sample)
    except Exception:
        dialect = csv.excel
    reader = csv.DictReader(io.StringIO(text), dialect=dialect)
    rows: List[Dict[str, str]] = []
    for row in reader:
        norm_row: Dict[str, str] = {}
        for k, v in row.items():
            norm_key = _normalize_csv_header(str(k))
            norm_val = sanitize_input(str(v), 240)
            if not norm_key:
                continue
            if norm_key in norm_row and norm_row[norm_key] and norm_val and norm_val not in norm_row[norm_key]:
                norm_row[norm_key] = f"{norm_row[norm_key]} | {norm_val}"
            elif norm_key not in norm_row:
                norm_row[norm_key] = norm_val
        rows.append(norm_row)
        if len(rows) >= 400:
            break
    time_column = _detect_time_column(rows)
    if time_column:
        indexed_rows = list(enumerate(rows))
        indexed_rows.sort(
            key=lambda item: (
                _parse_time_value(item[1].get(time_column, "")) is None,
                _parse_time_value(item[1].get(
                    time_column, "")) or datetime.max,
                item[0],
            )
        )
        rows = [row for _, row in indexed_rows]
    return rows


def _extract_pdf_sections(pdf_text: str) -> Dict[str, Any]:
    """Extract key technical sections from PDF text (items 308, 309).

    Returns finding, action, limitation, procedure, reference, notes,
    and ata_refs (ATA/AMM chapter numbers found in the document).
    """
    text = str(pdf_text or "").strip()
    if not text:
        return {
            "finding": "", "action": "", "limitation": "",
            "procedure": "", "reference": "", "notes": "", "ata_refs": [],
        }

    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    joined = "\n".join(lines)

    def pick(patterns: List[str], max_len: int = 700) -> str:
        for pat in patterns:
            m = re.search(pat, joined, flags=re.IGNORECASE | re.DOTALL)
            if m:
                return sanitize_input(m.group(1), max_len)
        return ""

    finding = pick([
        r"(?:finding|defect|issue|fault)\s*[:\-]\s*(.{20,500})",
        r"(?:observa(?:tion|[cç][aã]o)|reported)\s*[:\-]\s*(.{20,500})",
    ])
    action = pick([
        r"(?:action|corrective action|maintenance action)\s*[:\-]\s*(.{20,500})",
        r"(?:a[cç][aã]o|procedimento corretivo)\s*[:\-]\s*(.{20,500})",
    ])
    limitation = pick([
        r"(?:limitation|restriction|constraint)\s*[:\-]\s*(.{10,500})",
        r"(?:limita[cç][aã]o|restri[cç][aã]o)\s*[:\-]\s*(.{10,500})",
    ])
    procedure = pick([
        r"(?:procedure|task|work\s*instruction|step)\s*[:\-]\s*(.{10,600})",
        r"(?:procedimento|tarefa|etapa|instru[cç][aã]o)\s*[:\-]\s*(.{10,600})",
    ])
    reference = pick([
        r"(?:reference|ref\.?|amm|cmm|ipc|ipp|srm|easa)\s*[:\-]\s*(.{5,200})",
        r"(?:refer[eê]ncia|manual)\s*[:\-]\s*(.{5,200})",
    ])
    notes = pick([
        r"(?:note|remark|comment|obs\.?)\s*[:\-]\s*(.{10,400})",
        r"(?:nota|observa[cç][aã]o|coment[aá]rio)\s*[:\-]\s*(.{10,400})",
    ])

    # ATA chapter references (item 309): ATA 27-50, AMM 05-51, Chapter 72, etc.
    _ata_re = re.compile(
        r"\b(?:ata|amm|cmm|ipc|srm|chapter|cap[ií]tulo)\s*[-:]?\s*"
        r"(\d{2,3}(?:[-\s]\d{2,3})?)\b",
        flags=re.IGNORECASE,
    )
    ata_refs: List[str] = sorted(
        {m.group(1).strip() for m in _ata_re.finditer(joined)}
    )[:20]

    return {
        "finding": finding,
        "action": action,
        "limitation": limitation,
        "procedure": procedure,
        "reference": reference,
        "notes": notes,
        "ata_refs": ata_refs,
    }


def _detect_exceedance_signals(text_blob: str) -> List[str]:
    """Detect common exceedance events from free text and uploaded docs."""
    t = (text_blob or "").lower()
    signals: List[str] = []
    checks = [
        ("hard landing", ["hard landing", "hard-landing", "vertical acceleration", "sink rate", "touchdown g",
                          "vert g exceedance", "g-exceedance", "vertical g load"]),
        ("flap overspeed", ["flap overspeed", "vfe exceeded", "flap speed exceeded", "flaps overspeed",
                            "vfe exceedance", "flap limit exceeded"]),
        ("landing overspeed", ["ldg overspeed", "landing overspeed", "vref exceed", "approach overspeed",
                               "vref+", "fast approach", "speed exceedance on approach"]),
        ("unstable approach", ["unstable approach", "unstabilized", "go-around recommended",
                               "not stabilized", "call for go-around", "go around below"]),
        ("high energy approach", ["high energy", "energy state high", "long landing",
                                  "high approach speed", "fast touchdown"]),
        ("engine exceedance", ["egt exceedance", "n1 exceedance", "n2 exceedance", "itt exceedance",
                               "torque exceedance", "engine over-speed", "engine overspeed",
                               "oei event", "surge event", "engine stall"]),
        ("gear overspeed", ["gear overspeed", "vlg exceeded", "gear extension speed",
                            "gear retract speed exceeded"]),
        ("turbulence exceedance", ["severe turbulence", "turbulence exceedance", "gust load",
                                   "severe turbulence encounter"]),
        ("weight exceedance", ["overweight landing", "max landing weight exceeded",
                               "max takeoff weight exceeded", "mlw exceeded", "mtow exceeded"]),
        ("brake energy exceedance", ["brake energy", "hot brakes", "brake overheat",
                                     "brake fuse", "brake temp exceed"]),
    ]
    for label, keys in checks:
        if any(k in t for k in keys):
            signals.append(label)
    return signals


def _extract_event_timeline(csv_rows: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """Build a normalized timeline from CSV rows when timestamp-like fields exist."""
    if not csv_rows:
        return []
    event_keys = {"event", "message", "alert",
                  "description", "fault", "parameter", "detail"}
    timeline: List[Dict[str, str]] = []
    time_key = _detect_time_column(csv_rows)

    for row in csv_rows:
        lower_map = {str(k).strip().lower(): str(v or "").strip()
                     for k, v in row.items()}
        tval = lower_map.get(time_key, "") if time_key else ""
        eval_ = ""
        for k, v in lower_map.items():
            if any(token in k for token in event_keys) and v:
                eval_ = v
                break
        if tval or eval_:
            timeline.append({"time": sanitize_input(tval, 80),
                            "event": sanitize_input(eval_, 240)})

    # Keep order as-is, but truncate to practical payload size.
    return timeline[:120]


def _extract_ata_from_text(text: str) -> str:
    m = re.search(
        r"(?:ata|chapter|cap[ií]tulo)\s*[-:]?\s*(\d{2,3})\b", str(text or ""), flags=re.IGNORECASE)
    return m.group(1) if m else ""


def _find_open_troubleshooting_cases(
    failure_text: str,
    scenario: str,
    limit: int = 8,
) -> List[Dict[str, Any]]:
    """Find best matching open troubleshooting records to support recommendations."""
    records = load_records(limit=4000)
    if not records:
        return []

    query = f"{failure_text} {scenario}".lower()
    ata_hint = _extract_ata_from_text(query)
    tail_hint_match = re.search(
        r"\bpr-[a-z0-9]+\b", query, flags=re.IGNORECASE)
    tail_hint = tail_hint_match.group(0).upper() if tail_hint_match else ""

    open_status = {"open", "in progress",
                   "pending", "pending review", "aberto"}
    scored: List[tuple[int, Dict[str, Any]]] = []
    for rec in records:
        status = str(rec.get("status_atual", "") or "").strip().lower()
        if status not in open_status:
            continue
        score = 0
        ata = str(rec.get("ata", "") or "").strip()
        tail = str(rec.get("tail", "") or "").strip().upper()
        problema = str(rec.get("problema", "") or "")
        troubleshooting = str(rec.get("troubleshooting", "") or "")
        if ata_hint and ata == ata_hint:
            score += 55
        if tail_hint and tail_hint == tail:
            score += 45

        # Keyword overlap (lightweight TF)
        words = [w for w in re.findall(r"[a-z0-9]{4,}", query) if len(w) >= 4]
        hay = f"{problema} {troubleshooting}".lower()
        overlap = sum(1 for w in set(words[:30]) if w in hay)
        score += min(overlap * 6, 36)

        scored.append((score, rec))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = []
    for score, rec in scored[:limit]:
        top.append({
            "id": rec.get("id"),
            "tail": rec.get("tail"),
            "ata": rec.get("ata"),
            "status": rec.get("status_atual"),
            "problema": str(rec.get("problema", "") or "")[:240],
            "troubleshooting": str(rec.get("troubleshooting", "") or "")[:240],
            "match_score": score,
        })
    return top


# ── Item 351: Aircraft family rules engine ───────────────────────────────────
_KB_MANUALS_DIR = os.path.join(os.path.dirname(
    os.path.abspath(__file__)), "knowledge_base", "manuals")

_SIGNAL_TO_AMM_SECTION: Dict[str, str] = {
    "hard landing": "05-50-03",
    "flap overspeed": "05-50-06",
    "landing overspeed": "05-50-07",
    "gear overspeed": "05-50-07",
    "engine exceedance": "05-50-10",
    "turbulence exceedance": "05-50-13",
    "unstable approach": "05-50-03",
    "high energy approach": "05-50-28",
    "weight exceedance": "05-50-04",
    "brake energy exceedance": "05-50-07",
    "pressurization": "05-50-27",
}

_FAMILY_MODEL_PATTERNS: Dict[str, List[str]] = {
    "E2": ["e190-e2", "e195-e2", "e190e2", "e195e2", "-e2"],
    "E145": ["erj145", "erj-145", "e145"],
    "E170": ["e170", "e175", "emb170", "emb175", "erj170", "erj175"],
    "E1": ["emb190", "emb195", "e190", "e195", "emb-190", "emb-195"],
}


def _detect_aircraft_family(tail: str = "", model: str = "") -> str:
    """Infer Mexicana aircraft family (E1/E2/E145/E170) from tail or model string."""
    combined = (tail + " " + model).lower().strip()
    # E2 must be checked before E1 to avoid "e190" substring matching "-e2" variants
    for family in ("E2", "E145", "E170", "E1"):
        for pat in _FAMILY_MODEL_PATTERNS[family]:
            if pat in combined:
                return family
    return ""


def _load_family_manual_context(family: str, signals: List[str], max_chars: int = 3000) -> Dict[str, Any]:
    """Read relevant AMM sections from knowledge_base for the given aircraft family and signals."""
    empty: Dict[str, Any] = {"family": family, "matched_sections": [
    ], "text_excerpt": "", "source_files": []}
    if not family or not signals:
        return empty
    base_dir = os.path.join(_KB_MANUALS_DIR, family)
    if not os.path.isdir(base_dir):
        return empty
    section_codes = list(
        {_SIGNAL_TO_AMM_SECTION[s] for s in signals if s in _SIGNAL_TO_AMM_SECTION})
    if not section_codes:
        return empty
    matched_files: List[str] = []
    for root, _dirs, files in os.walk(base_dir):
        # skip nested duplicate folder (e.g. E1/E1/)
        rel = os.path.relpath(root, base_dir)
        if rel != "." and rel.split(os.sep)[0] == family:
            continue
        for fname in files:
            if not fname.upper().endswith(".PDF"):
                continue
            for sec in section_codes:
                if sec in fname:
                    matched_files.append(os.path.join(root, fname))
                    break
    texts: List[str] = []
    source_files: List[str] = []
    seen: set = set()
    per_file_limit = max_chars // max(1, min(len(matched_files), 3))
    for fpath in matched_files[:3]:
        fbasename = os.path.basename(fpath)
        if fbasename in seen:
            continue
        seen.add(fbasename)
        try:
            with open(fpath, "rb") as fh:
                raw = fh.read()
            t = _extract_text_from_pdf_bytes(raw)
            if t:
                texts.append(t[:per_file_limit])
                source_files.append(fbasename)
        except Exception:
            continue
    return {
        "family": family,
        "matched_sections": section_codes,
        "text_excerpt": "\n\n---\n\n".join(texts)[:max_chars],
        "source_files": source_files,
    }


def _build_confidence_score(signals: List[str], csv_rows: List[Dict[str, str]], pdf_text: str, open_cases: List[Dict[str, Any]]) -> int:
    score = 35
    if signals:
        score += min(len(signals) * 12, 30)
    if csv_rows:
        score += min(len(csv_rows) // 20, 15)
    if pdf_text:
        score += 10
    if open_cases:
        score += min((open_cases[0].get("match_score", 0)) // 8, 10)
    return int(max(10, min(score, 98)))


def _score_pdf_paragraph_relevance(
    pdf_text: str,
    failure_text: str,
    scenario: str,
    signals: List[str],
    max_paragraphs: int = 5,
) -> Dict[str, Any]:
    """Item 310: score PDF paragraphs by relevance to the active failure context."""
    text = str(pdf_text or "").strip()
    if not text:
        return {"top_paragraphs": [], "avg_score": 0.0, "query_terms": []}

    query_blob = f"{failure_text} {scenario}".lower()
    query_terms = sorted(set(re.findall(r"[a-z0-9]{4,}", query_blob)))[:24]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n+", text) if p.strip()]
    scored: List[Dict[str, Any]] = []

    for idx, paragraph in enumerate(paragraphs[:120]):
        low = paragraph.lower()
        term_hits = sum(1 for token in query_terms if token in low)
        signal_hits = sum(1 for sig in signals if sig in low)
        has_ata_hint = 1 if re.search(r"\b(?:ata|amm|chapter)\b", low) else 0
        score = min(100.0, term_hits * 11.0 +
                    signal_hits * 18.0 + has_ata_hint * 7.0)
        if score <= 0:
            continue
        scored.append({
            "paragraph_index": idx,
            "score": round(score, 1),
            "excerpt": sanitize_input(paragraph, 800),
            "term_hits": term_hits,
            "signal_hits": signal_hits,
        })

    scored.sort(key=lambda x: float(x.get("score", 0.0)), reverse=True)
    top = scored[:max_paragraphs]
    avg = round(sum(float(x["score"])
                for x in top) / len(top), 1) if top else 0.0
    return {"top_paragraphs": top, "avg_score": avg, "query_terms": query_terms[:12]}


def _infer_probable_cause_from_sequence(
    signals: List[str],
    timeline: List[Dict[str, str]],
    csv_rows: List[Dict[str, str]],
    pdf_sections: Dict[str, Any],
) -> Dict[str, Any]:
    """Item 312: infer probable cause from message/event sequence and supporting evidence."""
    precedence = [
        "hard landing",
        "landing overspeed",
        "flap overspeed",
        "engine exceedance",
        "gear overspeed",
        "high energy approach",
        "unstable approach",
        "turbulence exceedance",
        "weight exceedance",
        "brake energy exceedance",
    ]
    primary = "undetermined"
    for sig in precedence:
        if sig in signals:
            primary = sig
            break

    factors: List[str] = []
    if timeline:
        first_evt = sanitize_input(timeline[0].get("event", ""), 160)
        last_evt = sanitize_input(timeline[-1].get("event", ""), 160)
        if first_evt:
            factors.append(f"Initial event in sequence: {first_evt}.")
        if last_evt and last_evt != first_evt:
            factors.append(f"Final event in sequence: {last_evt}.")
    if pdf_sections.get("finding"):
        factors.append(
            "PDF finding corroborates an operational/maintenance anomaly.")
    if pdf_sections.get("action"):
        factors.append(
            "Corrective action already documented in maintenance records.")
    if csv_rows:
        factors.append(
            f"Sequence inferred from {len(csv_rows)} CSV/FDR row(s).")

    confidence = 30
    if primary != "undetermined":
        confidence += 35
    confidence += min(len(timeline) * 3, 18)
    confidence += 10 if pdf_sections.get("finding") else 0
    confidence += 7 if pdf_sections.get("ata_refs") else 0
    confidence = int(max(10, min(confidence, 95)))

    rationale = (
        "Probable cause inferred from temporal sequence, detected signals, and maintenance narrative correlation."
        if primary != "undetermined"
        else "No dominant signal sequence identified; maintain generic troubleshooting flow until additional evidence is provided."
    )
    return {
        "primary_cause": primary,
        "confidence": confidence,
        "contributing_factors": factors[:6],
        "rationale": rationale,
    }


def _estimate_exceedance_severity(
    signals: List[str],
    reconciliation: Dict[str, Any],
    evidence_completeness: Dict[str, Any],
    open_cases: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Estimate severity level and rationale for severity-conditioned recommendations (item 314)."""
    score = 20
    reasons: List[str] = []
    critical_signals = {"hard landing",
                        "engine exceedance", "landing overspeed"}
    high_signals = {"flap overspeed", "gear overspeed", "high energy approach"}

    if any(s in signals for s in critical_signals):
        score += 45
        reasons.append(
            "Critical exceedance signal present (hard landing/engine/landing overspeed).")
    elif any(s in signals for s in high_signals):
        score += 28
        reasons.append("High-impact exceedance signal detected.")
    elif signals:
        score += 16
        reasons.append("Operational exceedance signal detected.")

    if reconciliation.get("has_conflict"):
        score += 8
        reasons.append(
            "Conflict between CSV and PDF evidence requires conservative severity posture.")
    if len(open_cases) >= 2:
        score += 7
        reasons.append(
            "Multiple open troubleshooting cases linked to this context.")

    ev_score = int(evidence_completeness.get("score", 0))
    if ev_score < 40:
        score += 12
        reasons.append(
            "Low evidence completeness increases operational uncertainty.")

    if score >= 80:
        level = "CRITICAL"
    elif score >= 60:
        level = "HIGH"
    elif score >= 35:
        level = "MEDIUM"
    else:
        level = "LOW"
    return {"level": level, "score": min(score, 100), "reasons": reasons[:6]}


def _build_immediate_containment_actions(
    severity_level: str,
    signals: List[str],
    reconciliation: Dict[str, Any],
) -> List[str]:
    """Item 320: immediate containment actions for critical/high-risk exceedance contexts."""
    actions: List[str] = []
    level = str(severity_level or "").upper()
    if level in {"CRITICAL", "HIGH"}:
        actions.append(
            "Hold aircraft release pending Engineering initial disposition.")
        actions.append(
            "Apply temporary dispatch restriction until mandatory inspections are closed.")
    if "hard landing" in signals:
        actions.append(
            "Ground aircraft for hard-landing structural inspection matrix before next flight leg.")
    if "engine exceedance" in signals:
        actions.append(
            "Block dispatch and perform immediate engine exceedance checks (borescope/EEC fault review).")
    if "flap overspeed" in signals or "landing overspeed" in signals:
        actions.append(
            "Limit operation envelope and complete flight-control/landing-gear stress inspection before release.")
    if reconciliation.get("has_conflict"):
        actions.append(
            "Escalate evidence conflict to MCC/Engineering for joint source validation (CSV vs PDF).")

    deduped: List[str] = []
    seen = set()
    for action in actions:
        if action not in seen:
            deduped.append(action)
            seen.add(action)
    return deduped[:6]


def _build_action_support_evidence(
    actions: List[str],
    signals: List[str],
    reconciliation: Dict[str, Any],
    probable_cause: Dict[str, Any],
    pdf_relevance: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """Item 324: attach support evidence snippets to each recommended action."""
    support_rows: List[Dict[str, Any]] = []
    top_excerpt = ""
    top_paragraphs = pdf_relevance.get(
        "top_paragraphs", []) if isinstance(pdf_relevance, dict) else []
    if top_paragraphs:
        top_excerpt = sanitize_input(
            str(top_paragraphs[0].get("excerpt", "")), 260)
    primary_cause = sanitize_input(
        str(probable_cause.get("primary_cause", "")), 80)
    for action in actions[:8]:
        evidence: List[str] = []
        if signals:
            evidence.append(f"Signals detected: {', '.join(signals[:3])}.")
        if primary_cause and primary_cause != "undetermined":
            evidence.append(f"Probable cause inference: {primary_cause}.")
        if reconciliation.get("has_conflict"):
            evidence.append(
                "Evidence conflict detected between CSV and PDF sources.")
        else:
            agreements = reconciliation.get("agreements", [])
            if agreements:
                evidence.append(
                    f"Cross-source agreement: {', '.join(agreements[:2])}.")
        if top_excerpt:
            evidence.append(f"PDF context: {top_excerpt}")
        support_rows.append({
            "action": sanitize_input(action, 300),
            "support_evidence": evidence[:4],
        })
    return support_rows


def _build_additional_inspection_recommendations(
    signals: List[str],
    recurring_pattern: Dict[str, Any],
    tail: str,
    ata: str,
) -> List[str]:
    """Item 333: recommend additional inspections based on accumulated exposure and recurrence."""
    recommendations: List[str] = []
    tail_metrics = _load_tail_metrics().get(
        str(tail or "").strip().upper(), {}) if tail else {}
    fh = _safe_float(tail_metrics.get("fh"), 0.0)
    fc = _safe_float(tail_metrics.get("fc"), 0.0)
    recurrence_count = int((recurring_pattern or {}).get("count", 0) or 0)

    if recurrence_count >= 3:
        recommendations.append(
            "Trigger expanded inspection package for repeated events (include adjacent ATA systems and structural interfaces)."
        )
    elif recurrence_count == 2:
        recommendations.append(
            "Add one additional targeted inspection card due to repeated event signature on same tail/ATA family."
        )

    if fh >= 14000 or fc >= 9000:
        recommendations.append(
            "Include high-utilization exposure inspection set (fatigue-prone fittings, connectors, and wear-prone mechanisms)."
        )

    if "hard landing" in signals:
        recommendations.append(
            "Add follow-up boroscope/NDT spot-check on landing gear attach interfaces after initial hard-landing closeout."
        )
    if "engine exceedance" in signals:
        recommendations.append(
            "Schedule post-flight trend monitoring run for engine exceedance parameters (N1/EGT margins) for next cycles."
        )
    if "flap overspeed" in signals or "gear overspeed" in signals:
        recommendations.append(
            "Perform secondary functional run with independent inspector witness for flight-control/gear actuation path."
        )

    if ata and ata.startswith("2"):
        recommendations.append(
            "Verify ATA 2x interacting systems for latent faults before return-to-service closure."
        )

    # unique + capped
    out: List[str] = []
    seen = set()
    for rec in recommendations:
        if rec not in seen:
            out.append(rec)
            seen.add(rec)
    return out[:6]


_CRITICAL_ATA_PREFIXES = {"05", "27", "29", "32", "34", "52", "57", "71", "72"}


def _compute_operational_priority(
    signals: List[str],
    ata_hint: str,
    severity_level: str,
    open_cases: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Item 334: prioritize using event severity plus critical ATA combinations."""
    level = str(severity_level or "MEDIUM").upper()
    ata_prefix = str(ata_hint or "").strip()[:2]
    critical_signal = any(s in signals for s in {
                          "hard landing", "engine exceedance", "landing overspeed"})
    critical_ata = ata_prefix in _CRITICAL_ATA_PREFIXES

    reasons: List[str] = []
    if critical_signal:
        reasons.append("Critical exceedance event detected.")
    if critical_ata:
        reasons.append(f"ATA {ata_prefix} treated as operationally critical.")
    if len(open_cases) >= 2:
        reasons.append("Multiple linked troubleshooting cases remain open.")

    if level == "CRITICAL" and (critical_signal or critical_ata):
        priority = "CRITICAL"
    elif level in {"CRITICAL", "HIGH"} or critical_signal or critical_ata:
        priority = "HIGH"
    elif signals or open_cases:
        priority = "MEDIUM"
    else:
        priority = "LOW"
    return {"priority": priority, "critical_ata": critical_ata, "ata_prefix": ata_prefix, "reasons": reasons[:5]}


def _build_expert_view(result: Dict[str, Any]) -> Dict[str, Any]:
    """Item 337: detailed expert mode with full evidence trace."""
    return {
        "headline": f"{result.get('priority', 'MEDIUM')} priority technical investigation package",
        "signals": result.get("signals", []),
        "severity": result.get("severity_assessment", {}),
        "probable_cause": result.get("probable_cause", {}),
        "reconciliation": result.get("reconciliation", {}),
        "pdf_relevance": result.get("pdf_relevance", {}),
        "action_support_evidence": result.get("action_support_evidence", []),
        "family_context": result.get("family_context", {}),
        "version_context": {
            "analysis_version": result.get("analysis_version", 1),
            "version_comparison": result.get("version_comparison", {}),
        },
    }


def _build_executive_view(result: Dict[str, Any]) -> Dict[str, Any]:
    """Item 338: concise executive mode focused on decision and operational status."""
    severity = result.get("severity_estimate", "MEDIUM")
    primary_cause = (result.get("probable_cause") or {}).get(
        "primary_cause", "undetermined")
    return {
        "summary": (
            f"Priority {result.get('priority', 'MEDIUM')} / Severity {severity}. "
            f"Primary cause trend: {primary_cause}."
        ),
        "decision": result.get("best_option", ""),
        "containment": (result.get("immediate_containment_actions") or [])[:3],
        "blocking_reasons": (result.get("closure_readiness") or {}).get("blocking_reasons", [])[:3],
        "diagnosis_change_alert": result.get("diagnosis_change_alert", ""),
    }


def _build_structured_export_payload(result: Dict[str, Any], analysis_mode: str) -> Dict[str, Any]:
    """Item 340: integration-oriented structured export block."""
    return {
        "schema_version": "1.0",
        "analysis_mode": analysis_mode,
        "decision": {
            "priority": result.get("priority", "MEDIUM"),
            "severity": result.get("severity_estimate", "MEDIUM"),
            "best_option": result.get("best_option", ""),
            "closure_status": (result.get("closure_readiness") or {}).get("status", ""),
        },
        "signals": result.get("signals", []),
        "probable_cause": result.get("probable_cause", {}),
        "recommended_actions": result.get("recommended_actions", []),
        "containment_actions": result.get("immediate_containment_actions", []),
        "additional_inspections": result.get("additional_inspections", []),
        "traceability": {
            "analysis_key": result.get("analysis_key", ""),
            "analysis_version": result.get("analysis_version", 1),
            "changed_fields": (result.get("version_comparison") or {}).get("changed_fields", []),
        },
    }


def _build_exceedance_recommendation(
    failure_text: str,
    scenario: str,
    csv_rows: List[Dict[str, str]],
    pdf_text: str,
    open_cases: List[Dict[str, Any]],
    pdf_sections: Dict[str, Any],
    recurring_pattern: Dict[str, Any] | None = None,
    trend_window_analysis: Dict[str, Any] | None = None,
    tail: str = "",
    modelo: str = "",
    analysis_mode: str = "standard",
) -> Dict[str, Any]:
    """Create a technical troubleshooting recommendation from textual cascade evidence."""
    csv_schema_validation = _validate_csv_schema(csv_rows)
    csv_text_blob = "\n".join(
        " | ".join(f"{k}:{v}" for k, v in r.items()) for r in csv_rows[:80]
    )
    combined = "\n".join([
        failure_text or "",
        scenario or "",
        pdf_text[:6000],
        csv_text_blob,
    ])

    signals = _detect_exceedance_signals(combined)

    # Deterministic numerical verdict against AMM/AFM thresholds
    exceedance_verdict = _evaluate_exceedance_verdict(
        csv_rows=csv_rows,
        signals=signals,
        tail=tail,
        modelo=modelo,
        family=_detect_aircraft_family(tail, modelo),
    )

    timeline = _extract_event_timeline(csv_rows)
    priority = "MEDIUM"

    # Item 351: aircraft family rules engine — load relevant AMM sections
    aircraft_family = _detect_aircraft_family(tail, modelo)
    family_context = _load_family_manual_context(aircraft_family, signals)

    # Items 373-374: playbooks per signal
    playbooks: Dict[str, List[str]] = {
        sig: _get_event_playbook(sig) for sig in signals}

    # Item 322: reconcile CSV vs PDF evidence
    reconciliation = _reconcile_evidence_sources(csv_text_blob, pdf_text)

    # Item 323: causal chain narrative
    causal_chain = _build_causal_chain(
        signals, timeline, pdf_sections, csv_rows)

    # Item 312: probable cause inference by message/event sequence
    probable_cause = _infer_probable_cause_from_sequence(
        signals, timeline, csv_rows, pdf_sections
    )

    # Item 332: closure checklist
    closure_checklist = _build_closure_checklist(signals, open_cases)

    # Item 310: paragraph relevance score from PDF text
    pdf_relevance = _score_pdf_paragraph_relevance(
        pdf_text, failure_text, scenario, signals
    )

    # Item 380: evidence completeness
    evidence_completeness = _check_evidence_completeness(
        csv_rows, pdf_text, failure_text, pdf_sections
    )

    # Item 314: severity-conditioned recommendation
    severity_assessment = _estimate_exceedance_severity(
        signals, reconciliation, evidence_completeness, open_cases
    )
    severity_level = severity_assessment.get("level", "MEDIUM")
    ata_hint = _extract_ata_from_text(f"{failure_text} {scenario}")
    ata_decision_tree = _build_ata_decision_tree(
        ata_hint=ata_hint,
        signals=signals,
        severity_level=severity_level,
        reconciliation=reconciliation,
    )
    priority_assessment = _compute_operational_priority(
        signals,
        ata_hint,
        severity_level,
        open_cases,
    )
    priority = str(priority_assessment.get("priority", priority))

    # Item 320: immediate containment actions for high/critical contexts
    immediate_containment_actions = _build_immediate_containment_actions(
        severity_level, signals, reconciliation
    )

    # Item 333: additional inspections for accumulated exposure
    additional_inspections = _build_additional_inspection_recommendations(
        signals, recurring_pattern or {}, tail, ata_hint
    )

    confidence_score = _build_confidence_score(
        signals, csv_rows, pdf_text, open_cases)

    # Item 394: closure readiness
    closure_readiness = _compute_closure_readiness(
        signals, confidence_score, open_cases, reconciliation, evidence_completeness
    )

    cascata = []
    if signals:
        cascata.append(f"Detected exceedance signals: {', '.join(signals)}")
    if csv_rows:
        cascata.append(f"CSV evidences parsed: {len(csv_rows)} rows")
    if pdf_text:
        cascata.append("PDF maintenance narrative extracted")
    if timeline:
        cascata.append(f"Timeline entries parsed: {len(timeline)}")
    if open_cases:
        cascata.append(f"Open troubleshooting matches: {len(open_cases)}")
    pdf_sec_values = [
        v for v in pdf_sections.values() if isinstance(v, str) and v]
    if pdf_sec_values or pdf_sections.get("ata_refs"):
        cascata.append(
            "PDF key sections extracted (finding/action/limitation/procedure/ATA refs).")
    if reconciliation["has_conflict"]:
        cascata.append(
            f"Evidence reconciliation conflict: "
            f"{len(reconciliation['conflict_notes'])} discrepancy(ies) found."
        )
    if recurring_pattern and recurring_pattern.get("has_recurrence"):
        cascata.append(recurring_pattern["recommendation"])
    if not cascata:
        cascata.append(
            "No explicit exceedance signal detected; proceed with standard troubleshooting flow")

    technical_actions = [
        "Validate FDR/ACMS event markers and correlate timestamp with pilot report.",
        "Cross-check ATA chapter exposure and open MEL/ETD constraints before release.",
        "Inspect structural or systems limits potentially impacted by exceedance profile.",
        "Prioritize open troubleshooting task with targeted borescope/NDT when applicable.",
        "Issue return-to-service recommendation only after closure evidence is documented.",
    ]
    if "hard landing" in signals:
        technical_actions.insert(
            0, "Execute hard-landing inspection matrix (structure, landing gear, fuselage interfaces).")
    if "flap overspeed" in signals:
        technical_actions.insert(
            0, "Run flap/slat track and actuator inspection, including asymmetry/overload checks.")
    if "landing overspeed" in signals:
        technical_actions.insert(
            0, "Review approach profile and braking/gear stress indicators for potential exceedance impact.")

    if severity_level == "CRITICAL":
        technical_actions.insert(
            0, "Escalate to Engineering Review Board and suspend return-to-service decision until full disposition.")
    elif severity_level == "HIGH":
        technical_actions.insert(
            0, "Require senior certifying engineer review before return-to-service authorization.")

    tree_action = str(ata_decision_tree.get("recommended_action", "") or "").strip()
    if tree_action:
        technical_actions.insert(0, tree_action)

    trend_window_analysis = trend_window_analysis or {"trend": "insufficient_data", "window_months": 6, "series": []}
    if str(trend_window_analysis.get("trend", "")) == "increasing":
        technical_actions.insert(
            0,
            "Trend indicates increasing recurrence in recent window; initiate reliability review and preventive work order.",
        )

    for containment in reversed(immediate_containment_actions):
        technical_actions.insert(0, containment)

    action_support = _build_action_support_evidence(
        technical_actions,
        signals,
        reconciliation,
        probable_cause,
        pdf_relevance,
    )

    best_option = technical_actions[0] if technical_actions else "Escalate to engineering review board."

    mode_value = str(analysis_mode or "standard").strip().lower()

    result = {
        "priority": priority,
        "confidence_score": confidence_score,
        "signals": signals,
        "timeline": timeline[:25],
        "pdf_sections": pdf_sections,
        "open_troubleshooting_matches": open_cases,
        "cascade_summary": cascata,
        "recommended_actions": technical_actions[:8],
        "best_option": best_option,
        "severity_estimate": severity_level,
        "severity_assessment": severity_assessment,
        "priority_assessment": priority_assessment,
        "immediate_containment_actions": immediate_containment_actions,
        "additional_inspections": additional_inspections,
        "action_support_evidence": action_support,
        "playbooks": playbooks,
        "reconciliation": reconciliation,
        "ata_decision_tree": ata_decision_tree,
        "causal_chain": causal_chain,
        "probable_cause": probable_cause,
        "pdf_relevance": pdf_relevance,
        "closure_checklist": closure_checklist,
        "evidence_completeness": evidence_completeness,
        "closure_readiness": closure_readiness,
        "trend_window_analysis": trend_window_analysis,
        "recurring_pattern": recurring_pattern or {"has_recurrence": False, "count": 0, "events": [], "recommendation": ""},
        "family_context": family_context,
        "csv_schema_validation": csv_schema_validation,
        "analysis_mode": mode_value,
    }
    result["exceedance_verdict"] = exceedance_verdict
    result["expert_view"] = _build_expert_view(result)
    result["executive_view"] = _build_executive_view(result)
    result["mode_output"] = result["expert_view"] if mode_value == "expert" else result["executive_view"] if mode_value == "executive" else {}
    result["structured_export"] = _build_structured_export_payload(
        result, mode_value)
    return result


_PLAYBOOK_MAP: Dict[str, List[str]] = {
    "hard landing": [
        "Pull ACMS/FDR download and validate vertical g-load peak vs structural limit.",
        "Execute Hard Landing Inspection per AMM 05-51 (full structural survey).",
        "Inspect main landing gear actuators, drag braces, and torque links for deformation.",
        "Check wing-to-fuselage attachment fittings and belly fairing for cracks/buckling.",
        "Inspect floor structure, cargo compartment frames, and attach angles.",
        "Review engine mount and pylon attach points for evidence of transferred load.",
        "Document findings in ORT and await Engineering disposition before release.",
        "Coordinate with Quality if structural damage is confirmed — NDT may be required.",
    ],
    "flap overspeed": [
        "Pull FDR airspeed/flap position traces and document peak VFE exceedance value.",
        "Execute Flap Overspeed Inspection per AMM 27-50.",
        "Inspect flap tracks, rollers, and carriage fittings for signs of overload.",
        "Check flap actuators and PDU gearbox output shaft for torque overload indications.",
        "Inspect asymmetry brakes and WOW interfaces.",
        "Perform flap rigging check and full-range operational test.",
        "Verify no hard stops or binding in the entire flap range before re-service.",
        "Log exceedance in aircraft tech log with exact VFE margin exceeded.",
    ],
    "landing overspeed": [
        "Pull FDR groundspeed and IAS at touchdown to calculate approach speed excess.",
        "Inspect tire pressure and conditions; check for tread chunking or sidewall stress.",
        "Inspect brake assemblies — check wear indicators and heat sink condition.",
        "Review brake fuse and antiskid system BTB cycling patterns.",
        "Inspect nose gear steering assembly for dynamic overload.",
        "Check runway length used vs available — coordinate with crew and dispatch report.",
        "Perform brake temperature check before further flight.",
    ],
    "unstable approach": [
        "Retrieve ACMS QAR data for approach glidepath deviation, airspeed trend, and sink rate.",
        "Crew debrief mandatory per Safety Management System procedures.",
        "Verify go-around call was correctly applied per SOP — document in ASAP/FOQA.",
        "Review stabilized approach criteria compliance at 1,000 ft (IMC) / 500 ft (VMC).",
        "Coordinate with Training department for crew monitoring event if criteria not met.",
    ],
    "high energy approach": [
        "Download FDR/QAR for in-range energy state profile — verify kinetic/potential energy.",
        "Inspect brake assemblies for heat soak and wear pattern anomalies.",
        "Check tire temperatures and tire pressure if available.",
        "Verify runway stopping distance calculation used for dispatch.",
        "Coordinate with Safety and Training for event reporting as required.",
    ],
    "gear overspeed": [
        "Pull FDR trace and confirm gear operation window vs VLG limit.",
        "Inspect landing gear doors, door actuators, and downlock/uplock mechanisms.",
        "Check gear extension actuators for signs of dynamic overload.",
        "Verify door seal condition and panel fasteners.",
        "Perform full gear retraction/extension functional check.",
    ],
    "turbulence exceedance": [
        "Pull FDR/ACMS gust load vs MTOW structural limits.",
        "Execute severe turbulence inspection per AMM 05-51.",
        "Inspect wing, stabilizer, and airframe fairing attach points.",
        "Check passenger/cargo floor structure and seat track fittings.",
        "Review galley and lavatory attachment points.",
        "Coordinate with crew for injury report and ATC turbulence data.",
    ],
    "weight exceedance": [
        "Pull loadsheet and confirm actual takeoff/landing weight vs limits.",
        "Execute overweight landing inspection per AMM.",
        "Inspect main gear shock absorber oleo deflection and service level.",
        "Inspect main gear wheel well frames and attachment clips.",
        "Verify center of gravity (CG) corridor compliance for the event.",
    ],
    "engine exceedance": [
        "Pull EEC/FADEC fault history and identify specific limit exceeded (EGT, N1, N2).",
        "Perform post-exceedance borescope per AMM chapter 72.",
        "Check engine mount fittings and nacelle attach points for overload signs.",
        "Review recent maintenance history for any fuel nozzle or combustor issues.",
        "Coordinate with OEM engine team if exceedance approached red-line threshold.",
        "Do not clear for dispatch without Engineering written disposition.",
    ],
    "brake energy exceedance": [
        "Check brake heat sink condition and brake assembly wear indicators.",
        "Verify brake temperature monitoring system BITE / BITE log for overtemp events.",
        "Inspect tire condition adjacent to hot brake assemblies.",
        "Allow adequate cooling time before further dispatch — comply with AMM cooling requirements.",
        "Document energy value vs limit in tech log and notify quality.",
    ],
}


def _get_event_playbook(signal: str) -> List[str]:
    """Return ordered inspection playbook steps for a given exceedance signal type."""
    return _PLAYBOOK_MAP.get(signal.lower().strip(), [
        "Review ACMS/FDR data for exceedance confirmation and record-keeping.",
        "Apply applicable AMM inspection task per exceedance type.",
        "Document all findings in tech log and coordinate release with Quality.",
    ])


def _reconcile_evidence_sources(
    csv_text: str, pdf_text: str
) -> Dict[str, Any]:
    """
    Compare signals detected independently from CSV data vs PDF narrative.
    Returns agreements (both sources agree), csv_only, pdf_only, and a conflict flag.
    """
    csv_signals = set(_detect_exceedance_signals(csv_text))
    pdf_signals = set(_detect_exceedance_signals(pdf_text))

    agreements = list(csv_signals & pdf_signals)
    csv_only = list(csv_signals - pdf_signals)
    pdf_only = list(pdf_signals - csv_signals)
    has_conflict = bool(csv_only or pdf_only)

    conflict_notes: List[str] = []
    for sig in csv_only:
        conflict_notes.append(
            f"Signal '{sig}' found in CSV data but NOT in PDF narrative — verify FDR data vs maintenance record."
        )
    for sig in pdf_only:
        conflict_notes.append(
            f"Signal '{sig}' found in PDF narrative but NOT in CSV data — confirm pilot report against QAR."
        )

    return {
        "has_conflict": has_conflict,
        "agreements": agreements,
        "csv_only_signals": csv_only,
        "pdf_only_signals": pdf_only,
        "conflict_notes": conflict_notes,
    }


# ── File-upload validation constants (item 342) ─────────────────────────────
_ALLOWED_CSV_EXTENSIONS = frozenset({".csv", ".txt", ".log", ".tsv"})
_ALLOWED_PDF_EXTENSIONS = frozenset({".pdf"})
_MAX_SINGLE_FILE_BYTES = 12 * 1024 * 1024  # 12 MB per file


# ── Technical closure checklist lookup (item 332) ───────────────────────────
_CLOSURE_CHECKLIST_BY_SIGNAL: Dict[str, List[str]] = {
    "hard landing": [
        "Hard Landing Inspection work order opened and signed off.",
        "All structural areas per AMM 05-51 records completed with findings documented.",
        "NDT completed where required by engineering disposition.",
        "Engineering written clearance received before return to service.",
    ],
    "flap overspeed": [
        "FDR exceedance value documented and compared to certified VFE limit.",
        "Flap Overspeed Inspection per AMM 27-50 completed and signed off.",
        "Full-range flap functional test passed and recorded.",
    ],
    "engine exceedance": [
        "Engine exceedance type and magnitude (EGT/N1/N2) documented in tech log.",
        "Post-exceedance borescope completed with all findings recorded.",
        "Engineering clearance received prior to dispatch.",
        "Engine life tracking updated per OEM requirements.",
    ],
    "gear overspeed": [
        "Gear Overspeed Inspection per AMM 32-00 completed.",
        "Gear retraction/extension functional test performed and passed.",
        "Structural integrity of gear bay framing confirmed.",
    ],
    "turbulence exceedance": [
        "Turbulence Inspection per AMM 05-51 completed.",
        "Wing and tail attach-point inspection signed off.",
        "Crew injury report filed per company safety procedures.",
    ],
    "weight exceedance": [
        "Loadsheet discrepancy report filed with Load Control.",
        "Overweight Landing Inspection per AMM completed.",
        "Landing gear oleo strut deflection check performed and recorded.",
    ],
    "brake energy exceedance": [
        "Brake assembly heat-sink condition verified and documented.",
        "Cooling time complied with per AMM before further flight.",
        "Tire condition inspected adjacent to hot brake assemblies.",
    ],
    "landing overspeed": [
        "Approach speed exceedance magnitude documented from FDR data.",
        "Brake and tire condition inspected and recorded.",
        "Brake temperature check completed before further flight.",
    ],
    "unstable approach": [
        "Crew debrief completed per Safety Management System procedures.",
        "QAR/FOQA data retained for safety review.",
        "ASAP event report filed if applicable.",
    ],
    "high energy approach": [
        "Energy state profile from FDR/QAR analyzed and documented.",
        "Brake, tire, and wheel condition inspected.",
        "Event reported to Safety department if runway margin was compromised.",
    ],
}
_CLOSURE_CHECKLIST_GENERIC = [
    "All detected exceedance signals investigated per applicable AMM task.",
    "Open troubleshooting job cards closed or formally deferred with engineering authority.",
    "All inspection findings documented in aircraft tech log.",
    "Quality review completed in case of confirmed damage.",
    "Return-to-service certification issued by appropriately rated certifying engineer.",
    "PIREP/ASAP filed if event meets safety reporting criteria.",
]


def _build_closure_checklist(
    signals: List[str], open_cases: List[Dict[str, Any]]
) -> List[str]:
    """Build a technical closure checklist keyed to detected signals (item 332)."""
    checklist: List[str] = []
    seen: set = set()
    for sig in signals:
        for item in _CLOSURE_CHECKLIST_BY_SIGNAL.get(sig, []):
            if item not in seen:
                checklist.append(item)
                seen.add(item)
    for item in _CLOSURE_CHECKLIST_GENERIC:
        if item not in seen:
            checklist.append(item)
            seen.add(item)
    if open_cases:
        msg = (
            f"Verify {len(open_cases)} open troubleshooting case(s) are resolved "
            "or deferred with proper technical authority."
        )
        if msg not in seen:
            checklist.append(msg)
    return checklist


def _build_causal_chain(
    signals: List[str],
    timeline: List[Dict[str, str]],
    pdf_sections: Dict[str, Any],
    csv_rows: List[Dict[str, str]],
) -> List[str]:
    """Build a step-by-step causal narrative from available evidence (item 323)."""
    chain: List[str] = []

    # Step 1 — evidence sources collected
    sources = []
    if csv_rows:
        sources.append(f"{len(csv_rows)} CSV/FDR data rows")
    if pdf_sections.get("finding"):
        sources.append("PDF maintenance finding")
    if sources:
        chain.append(f"Evidence collected from: {', '.join(sources)}.")

    # Step 2 — timeline scope
    if timeline:
        first_evt = timeline[0]
        last_evt = timeline[-1]
        t_prefix = f"at {first_evt['time']} " if first_evt.get("time") else ""
        span = (
            f" through '{sanitize_input(last_evt.get('event', ''), 80)}'"
            if len(timeline) > 1 else ""
        )
        chain.append(
            f"Event timeline begins {t_prefix}: "
            f"'{sanitize_input(first_evt.get('event', '(unknown event)'), 120)}'"
            f"{span}."
        )

    # Step 3 — signals detected
    if signals:
        chain.append(
            f"Analysis identified {len(signals)} exceedance signal(s): {', '.join(signals)}."
        )
        for sig in signals[:3]:
            chain.append(
                f"  \u2192 '{sig}' requires verification against applicable structural/systems inspection limits."
            )
    else:
        chain.append(
            "No specific exceedance signal was detected from the provided event data.")

    # Step 4 — PDF finding
    if pdf_sections.get("finding"):
        chain.append(
            f"Maintenance finding from records: \"{sanitize_input(pdf_sections['finding'], 200)}\""
        )

    # Step 5 — documented action
    if pdf_sections.get("action"):
        chain.append(
            f"Documented corrective action: \"{sanitize_input(pdf_sections['action'], 200)}\""
        )

    # Step 6 — ATA references
    if pdf_sections.get("ata_refs"):
        chain.append(
            f"ATA references identified in documentation: {', '.join(pdf_sections['ata_refs'][:8])}."
        )

    # Step 7 — causal conclusion
    if signals:
        chain.append(
            "Causal conclusion: Exceedance event(s) confirmed from evidence require mandatory "
            "inspection per applicable AMM before return to service. "
            "Priority is driven by signal type and structural/system exposure."
        )
    else:
        chain.append(
            "Causal conclusion: No definitive exceedance signal confirmed. "
            "Proceed with standard troubleshooting protocol per applicable AMM."
        )
    return chain


def _check_evidence_completeness(
    csv_rows: List[Dict[str, str]],
    pdf_text: str,
    failure_text: str,
    pdf_sections: Dict[str, Any],
) -> Dict[str, Any]:
    """Assess the completeness of the evidence package and score it 0-100 (item 380)."""
    score = 0
    notes: List[str] = []

    # CSV/FDR data — up to 25 pts
    if csv_rows:
        score += min(25, 10 + len(csv_rows) // 8)
    else:
        notes.append(
            "MISSING: No CSV/FDR data — quantitative event data is strongly recommended.")

    # PDF maintenance document — up to 20 pts
    if len(pdf_text) > 200:
        score += 20
    elif pdf_text:
        score += 8
        notes.append(
            "WEAK: PDF text is very short — verify the document is not image-based/scanned.")
    else:
        notes.append(
            "MISSING: No PDF maintenance document — narrative evidence is absent.")

    # Event description — up to 15 pts
    if len(failure_text) > 80:
        score += 15
    elif failure_text:
        score += 6
        notes.append(
            "WEAK: Event description is brief — additional operational detail is recommended.")
    else:
        notes.append("MISSING: No event description provided.")

    # Extracted PDF finding section — 15 pts
    if pdf_sections.get("finding"):
        score += 15
    else:
        notes.append(
            "INCOMPLETE: No 'Finding' section parsed from PDF — check document format.")

    # Extracted PDF action section — 10 pts
    if pdf_sections.get("action"):
        score += 10
    else:
        notes.append("INCOMPLETE: No 'Action' section parsed from PDF.")

    # ATA references — 10 pts
    if pdf_sections.get("ata_refs"):
        score += 10
    else:
        notes.append(
            "INCOMPLETE: No ATA chapter references found in documentation.")

    # Limitation or procedure — 5 pts
    if pdf_sections.get("limitation") or pdf_sections.get("procedure"):
        score += 5

    score = min(100, score)
    if score >= 80:
        rating = "COMPLETE"
    elif score >= 55:
        rating = "ADEQUATE"
    elif score >= 30:
        rating = "PARTIAL"
    else:
        rating = "INSUFFICIENT"

    return {"score": score, "rating": rating, "notes": notes}


def _compute_closure_readiness(
    signals: List[str],
    confidence_score: int,
    open_cases: List[Dict[str, Any]],
    reconciliation: Dict[str, Any],
    evidence_completeness: Dict[str, Any],
) -> Dict[str, Any]:
    """Compute closure readiness score 0-100 and list of blocking reasons (item 394)."""
    score = 100
    blocking: List[str] = []

    # Unresolved exceedance signals
    if signals:
        penalty = min(30, len(signals) * 8)
        score -= penalty
        blocking.append(
            f"{len(signals)} exceedance signal(s) require inspection and sign-off before release."
        )

    # Low confidence
    if confidence_score < 40:
        score -= 20
        blocking.append(
            f"Confidence score is low ({confidence_score}%) — additional evidence required."
        )
    elif confidence_score < 65:
        score -= 8
        blocking.append(
            f"Confidence score is moderate ({confidence_score}%) — review evidence quality."
        )

    # Open troubleshooting cases
    if open_cases:
        score -= min(20, len(open_cases) * 5)
        blocking.append(
            f"{len(open_cases)} open troubleshooting case(s) linked — "
            "must be resolved or formally deferred."
        )

    # Evidence source conflict
    if reconciliation.get("has_conflict"):
        n = len(reconciliation.get("conflict_notes", []))
        score -= min(15, n * 5)
        blocking.append(
            f"Evidence reconciliation detected {n} discrepancy(ies) between CSV and PDF sources."
        )

    # Incomplete evidence package
    ev_score = evidence_completeness.get("score", 100)
    if ev_score < 40:
        score -= 15
        blocking.append(
            f"Evidence package is insufficient (completeness {ev_score}/100).")
    elif ev_score < 65:
        score -= 5

    score = max(0, min(100, score))
    if score >= 85:
        status = "READY"
    elif score >= 65:
        status = "NEAR_READY"
    elif score >= 40:
        status = "REQUIRES_ACTION"
    else:
        status = "NOT_READY"

    return {"score": score, "status": status, "blocking_reasons": blocking}


def _detect_recurring_pattern(
    tail: str,
    ata: str,
    records: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Detect recurring event patterns for the given tail/ATA from historical records (item 354)."""
    if not tail or not records:
        return {"has_recurrence": False, "count": 0, "events": [], "recommendation": ""}

    target_tail = str(tail).strip().upper()
    # first 2 digits for broad ATA matching
    target_ata_prefix = str(ata).strip()[:2]

    matching = []
    for r in records:
        r_tail = str(r.get("tail", "") or "").strip().upper()
        r_ata = str(r.get("ata", "") or r.get("ata_chapter", "") or "").strip()
        r_desc = str(r.get("description", "") or r.get(
            "problema", "") or r.get("fault", "") or "").strip()
        if r_tail != target_tail:
            continue
        if target_ata_prefix and not r_ata.startswith(target_ata_prefix):
            continue
        matching.append({
            "ata": r_ata,
            "date": str(r.get("date", "") or r.get("created_at", "") or "")[:10],
            "description": sanitize_input(r_desc, 160),
            "status": str(r.get("status", "") or ""),
        })

    has_recurrence = len(matching) >= 2
    recommendation = ""
    if len(matching) >= 3:
        recommendation = (
            f"RECURRING: {len(matching)} similar events detected for tail {target_tail} "
            f"in ATA {ata}. Escalate to engineering for root-cause analysis and potential AD/SB review."
        )
    elif len(matching) == 2:
        recommendation = (
            f"REPEATED: 2 similar events found for tail {target_tail}. "
            "Document pattern and monitor operational trend."
        )

    return {
        "has_recurrence": has_recurrence,
        "count": len(matching),
        "events": matching[:10],
        "recommendation": recommendation,
    }


def _build_ata_decision_tree(
    ata_hint: str,
    signals: List[str],
    severity_level: str,
    reconciliation: Dict[str, Any],
) -> Dict[str, Any]:
    """Item 352: lightweight technical decision tree by ATA family."""
    ata = str(ata_hint or "").strip()
    ata_family = ata[:2] if ata else "unknown"
    signal_set = {str(s or "").strip().lower() for s in signals if str(s or "").strip()}
    severity = str(severity_level or "MEDIUM").strip().upper()

    branch = "general_system_integrity"
    recommended_action = "Run baseline troubleshooting checklist with targeted ATA verification before release."
    nodes = [
        {"node": "ata_family", "value": ata_family},
        {"node": "severity", "value": severity},
    ]

    if ata_family == "27":
        branch = "flight_controls"
        recommended_action = "Apply flight-control decision path: inspect flap/slat tracks, actuator loads and asymmetry protections."
        if "flap overspeed" in signal_set:
            branch = "flight_controls_flap_overspeed"
            recommended_action = "Perform flap overspeed branch inspection per AMM limits and verify actuator/track free movement."
    elif ata_family == "29":
        branch = "hydraulic_system"
        recommended_action = "Apply hydraulic branch: pressure integrity test, leak source isolation and pump/line health verification."
    elif ata_family == "32":
        branch = "landing_gear"
        recommended_action = "Apply landing gear branch: evaluate stress markers, brake energy profile and gear structural interfaces."
    elif ata_family == "71":
        branch = "powerplant"
        recommended_action = "Apply powerplant branch: verify exceedance impact on engine mounts, vibration and thermal constraints."

    if severity in {"CRITICAL", "HIGH"}:
        nodes.append({"node": "risk_gate", "value": "engineering_review_required"})

    if bool((reconciliation or {}).get("has_conflict", False)):
        nodes.append({"node": "evidence_conflict", "value": "manual_reconciliation_required"})

    return {
        "ata_family": ata_family,
        "selected_branch": branch,
        "decision_nodes": nodes,
        "recommended_action": recommended_action,
    }


def _build_trend_window_analysis(
    tail: str,
    ata: str,
    records: List[Dict[str, Any]],
    window_months: int = 6,
) -> Dict[str, Any]:
    """Item 357: moving-window trend analysis for tail/ATA occurrences."""
    if not tail or not records:
        return {"trend": "insufficient_data", "window_months": int(window_months), "series": []}

    target_tail = str(tail or "").strip().upper()
    target_ata_prefix = str(ata or "").strip()[:2]
    buckets: Dict[str, int] = {}

    for r in records:
        r_tail = str(r.get("tail", "") or "").strip().upper()
        if r_tail != target_tail:
            continue
        r_ata = str(r.get("ata", "") or r.get("ata_chapter", "") or "").strip()
        if target_ata_prefix and not r_ata.startswith(target_ata_prefix):
            continue

        raw_date = str(r.get("date", "") or r.get("created_at", "") or r.get("updated_at", "") or "").strip()
        dt = _parse_time_value(raw_date)
        if not dt:
            m = re.search(r"(\d{4})[-/](\d{2})", raw_date)
            if not m:
                continue
            month_key = f"{m.group(1)}-{m.group(2)}"
        else:
            month_key = dt.strftime("%Y-%m")
        buckets[month_key] = int(buckets.get(month_key, 0) or 0) + 1

    if not buckets:
        return {"trend": "insufficient_data", "window_months": int(window_months), "series": []}

    months = sorted(buckets.keys())[-max(1, int(window_months)):]
    series = [{"month": m, "count": buckets.get(m, 0)} for m in months]
    counts = [int(item["count"]) for item in series]

    trend = "stable"
    if len(counts) >= 3:
        half = max(1, len(counts) // 2)
        first_avg = sum(counts[:half]) / max(1, half)
        second_avg = sum(counts[half:]) / max(1, len(counts) - half)
        if second_avg >= first_avg + 0.75:
            trend = "increasing"
        elif second_avg <= first_avg - 0.75:
            trend = "decreasing"
    elif len(counts) >= 2:
        if counts[-1] > counts[0]:
            trend = "increasing"
        elif counts[-1] < counts[0]:
            trend = "decreasing"

    return {
        "trend": trend,
        "window_months": int(window_months),
        "series": series,
        "total_events_in_window": sum(counts),
    }


@analytics_bp.route("/api/ai/exceedance/analyze", methods=["POST"])
def api_ai_exceedance_analyze():
    """Analyze troubleshooting context + CSV/PDF files to suggest best technical action."""
    client_ip = request.remote_addr or "unknown"
    if not _check_rate_limit(client_ip):
        return jsonify({"success": False, "error": "Too many requests. Please try again in a moment."}), 429

    failure_text = sanitize_input(request.form.get(
        "failure_text", ""), max_len=_QUERY_MAX_LEN)
    scenario = sanitize_input(request.form.get(
        "scenario", ""), max_len=_QUERY_MAX_LEN)
    tail_hint = sanitize_input(request.form.get(
        "tail", ""), max_len=_FIELD_MAX_LEN)
    ata_hint = sanitize_input(request.form.get(
        "ata", ""), max_len=_FIELD_MAX_LEN)

    modelo_hint = sanitize_input(request.form.get(
        "modelo", ""), max_len=_FIELD_MAX_LEN)
    analysis_mode = sanitize_input(request.form.get(
        "analysis_mode", "standard"), max_len=24).lower()
    analysis_key = _build_exceedance_analysis_key(
        failure_text=failure_text,
        scenario=scenario,
        tail=tail_hint,
        ata=ata_hint,
        modelo=modelo_hint,
    )
    retention_info = _cleanup_exceedance_retention()
    actor = _build_exceedance_actor_tag(client_ip)

    # support both legacy single-file and new multi-file fields
    csv_rows: List[Dict[str, str]] = []
    pdf_parts: List[str] = []
    upload_specs: List[Dict[str, Any]] = []

    if (request.content_length or 0) > 18 * 1024 * 1024:
        return jsonify({"success": False, "error": "Payload too large. Max 18 MB."}), 413

    csv_files = request.files.getlist("csv_files") or []
    single_csv = request.files.get("csv_file")
    if single_csv and single_csv.filename:
        csv_files.append(single_csv)

    # Item 342: per-file type + size validation
    for f in csv_files[:5]:
        if not f or not f.filename:
            continue
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in _ALLOWED_CSV_EXTENSIONS:
            return jsonify({
                "success": False,
                "error": f"File type '{ext}' is not allowed for CSV upload. "
                f"Accepted: {', '.join(sorted(_ALLOWED_CSV_EXTENSIONS))}",
            }), 400
        data = f.read()
        if len(data) > _MAX_SINGLE_FILE_BYTES:
            return jsonify({
                "success": False,
                "error": f"File '{sanitize_input(f.filename, 80)}' exceeds the maximum size of 12 MB.",
            }), 400
        try:
            csv_rows.extend(_extract_rows_from_csv_bytes(data))
            upload_specs.append({
                "kind": "csv",
                "filename": f.filename,
                "data": data,
                "preview": data[:160].decode("utf-8", errors="replace"),
            })
        except Exception:
            continue
    csv_rows = csv_rows[:800]

    pdf_files = request.files.getlist("pdf_files") or []
    single_pdf = request.files.get("pdf_file")
    if single_pdf and single_pdf.filename:
        pdf_files.append(single_pdf)

    for f in pdf_files[:5]:
        if not f or not f.filename:
            continue
        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in _ALLOWED_PDF_EXTENSIONS:
            return jsonify({
                "success": False,
                "error": f"File type '{ext}' is not allowed for PDF upload. Accepted: .pdf",
            }), 400
        data = f.read()
        if len(data) > _MAX_SINGLE_FILE_BYTES:
            return jsonify({
                "success": False,
                "error": f"File '{sanitize_input(f.filename, 80)}' exceeds the maximum size of 12 MB.",
            }), 400
        try:
            text = _extract_text_from_pdf_bytes(data)
            if text:
                pdf_parts.append(text)
            upload_specs.append({
                "kind": "pdf",
                "filename": f.filename,
                "data": data,
                "preview": text[:160] if text else "",
            })
        except Exception:
            continue
    pdf_text = "\n\n".join(pdf_parts)[:18000]

    open_cases = _find_open_troubleshooting_cases(
        failure_text=failure_text,
        scenario=scenario,
        limit=8,
    )
    pdf_sections = _extract_pdf_sections(pdf_text)

    # Item 354: recurring pattern detection
    records_for_recurrence = load_records(limit=3000)
    ata_for_recurrence = ata_hint or _extract_ata_from_text(
        failure_text) or _extract_ata_from_text(scenario)
    recurring_pattern = _detect_recurring_pattern(
        tail_hint, ata_for_recurrence, records_for_recurrence)
    trend_window_analysis = _build_trend_window_analysis(
        tail=tail_hint,
        ata=ata_for_recurrence,
        records=records_for_recurrence,
        window_months=6,
    )

    result = _build_exceedance_recommendation(
        failure_text=failure_text,
        scenario=scenario,
        csv_rows=csv_rows,
        pdf_text=pdf_text,
        open_cases=open_cases,
        pdf_sections=pdf_sections,
        recurring_pattern=recurring_pattern,
        trend_window_analysis=trend_window_analysis,
        tail=tail_hint,
        modelo=modelo_hint,
        analysis_mode=analysis_mode,
    )
    stored_files = _persist_exceedance_uploads(
        analysis_key, upload_specs, actor)
    _append_exceedance_audit_entries([
        {
            "analysis_key": analysis_key,
            "actor": item.get("actor", actor),
            "timestamp": item.get("uploaded_at", datetime.now(timezone.utc).isoformat()),
            "kind": item.get("kind", "evidence"),
            "stored_name": item.get("stored_name", ""),
            "anonymized_name": item.get("anonymized_name", ""),
            "size_bytes": item.get("size_bytes", 0),
            "sha1": item.get("sha1", ""),
        }
        for item in stored_files
    ])
    result = _finalize_exceedance_result(
        result=result,
        analysis_key=analysis_key,
        analysis_mode=analysis_mode,
        failure_text=failure_text,
        scenario=scenario,
        tail=tail_hint,
        ata=ata_hint,
        modelo=modelo_hint,
        stored_files=stored_files,
    )
    result["retention_policy"] = retention_info

    return jsonify({
        "success": True,
        "data": result,
        "inputs": {
            "failure_text_len": len(failure_text),
            "scenario_len": len(scenario),
            "csv_rows": len(csv_rows),
            "csv_files": len(csv_files),
            "pdf_files": len(pdf_files),
            "pdf_text_len": len(pdf_text),
            "open_matches": len(open_cases),
            "analysis_mode": analysis_mode,
        },
    })


def _get_open_case_by_id(case_id: str) -> Dict[str, Any] | None:
    token = str(case_id or "").strip()
    if not token:
        return None
    records = load_records(limit=5000)
    open_status = {"open", "in progress",
                   "pending", "pending review", "aberto"}
    for rec in records:
        status = str(rec.get("status_atual", "") or "").strip().lower()
        if status not in open_status:
            continue
        if str(rec.get("id", "")).strip() == token:
            return rec
    return None


@analytics_bp.route("/api/ai/exceedance/open_cases", methods=["GET"])
def api_ai_exceedance_open_cases():
    """List open troubleshooting cases filtered by tail/ata for exceedance workflow."""
    client_ip = request.remote_addr or "unknown"
    if not _check_rate_limit(client_ip):
        return jsonify({"success": False, "error": "Too many requests. Please try again in a moment."}), 429

    tail = sanitize_input(request.args.get("tail", ""), 32).upper()
    ata = sanitize_input(request.args.get("ata", ""), 8)
    limit = max(1, min(int(request.args.get("limit", 20) or 20), 100))

    records = load_records(limit=5000)
    open_status = {"open", "in progress",
                   "pending", "pending review", "aberto"}
    out: List[Dict[str, Any]] = []
    for rec in records:
        status = str(rec.get("status_atual", "") or "").strip().lower()
        if status not in open_status:
            continue
        rec_tail = str(rec.get("tail", "") or "").strip().upper()
        rec_ata = str(rec.get("ata", "") or "").strip()
        if tail and rec_tail != tail:
            continue
        if ata and rec_ata != ata:
            continue
        out.append({
            "id": rec.get("id"),
            "tail": rec.get("tail"),
            "ata": rec.get("ata"),
            "status": rec.get("status_atual"),
            "problema": str(rec.get("problema", "") or "")[:300],
            "troubleshooting": str(rec.get("troubleshooting", "") or "")[:300],
        })
        if len(out) >= limit:
            break

    return jsonify({"success": True, "count": len(out), "cases": out})


@analytics_bp.route("/api/ai/exceedance/analyze_open_case", methods=["POST"])
def api_ai_exceedance_analyze_open_case():
    """Analyze a specific open troubleshooting case with optional attached CSV/PDF evidence."""
    client_ip = request.remote_addr or "unknown"
    if not _check_rate_limit(client_ip):
        return jsonify({"success": False, "error": "Too many requests. Please try again in a moment."}), 429

    case_id = sanitize_input(request.form.get("case_id", ""), 40)
    case = _get_open_case_by_id(case_id)
    if not case:
        return jsonify({"success": False, "error": "Open case not found"}), 404

    failure_text = sanitize_input(
        str(case.get("problema", "")), max_len=_QUERY_MAX_LEN)
    scenario = sanitize_input(
        str(case.get("troubleshooting", "")), max_len=_QUERY_MAX_LEN)
    analysis_mode = sanitize_input(request.form.get(
        "analysis_mode", "standard"), 24).lower()

    csv_rows: List[Dict[str, str]] = []
    pdf_parts: List[str] = []

    csv_files = request.files.getlist("csv_files") or []
    for f in csv_files[:5]:
        if not f or not f.filename:
            continue
        try:
            csv_rows.extend(_extract_rows_from_csv_bytes(f.read()))
        except Exception:
            continue
    csv_rows = csv_rows[:800]

    pdf_files = request.files.getlist("pdf_files") or []
    for f in pdf_files[:5]:
        if not f or not f.filename:
            continue
        try:
            text = _extract_text_from_pdf_bytes(f.read())
            if text:
                pdf_parts.append(text)
        except Exception:
            continue
    pdf_text = "\n\n".join(pdf_parts)[:18000]

    open_cases = _find_open_troubleshooting_cases(
        failure_text=failure_text, scenario=scenario, limit=8)
    pdf_sections = _extract_pdf_sections(pdf_text)
    records_for_recurrence = load_records(limit=3000)
    ata_for_recurrence = str(case.get("ata", "") or "") or _extract_ata_from_text(
        failure_text) or _extract_ata_from_text(scenario)
    recurring_pattern = _detect_recurring_pattern(
        str(case.get("tail", "") or ""), ata_for_recurrence, records_for_recurrence)
    trend_window_analysis = _build_trend_window_analysis(
        tail=str(case.get("tail", "") or ""),
        ata=ata_for_recurrence,
        records=records_for_recurrence,
        window_months=6,
    )
    result = _build_exceedance_recommendation(
        failure_text=failure_text,
        scenario=scenario,
        csv_rows=csv_rows,
        pdf_text=pdf_text,
        open_cases=open_cases,
        pdf_sections=pdf_sections,
        recurring_pattern=recurring_pattern,
        trend_window_analysis=trend_window_analysis,
        tail=str(case.get("tail", "") or ""),
        modelo=str(case.get("modelo", "") or ""),
        analysis_mode=analysis_mode,
    )

    return jsonify({
        "success": True,
        "case": {
            "id": case.get("id"),
            "tail": case.get("tail"),
            "ata": case.get("ata"),
            "status": case.get("status_atual"),
        },
        "data": result,
    })


@analytics_bp.route("/api/ai/exceedance/reprocess", methods=["POST"])
def api_ai_exceedance_reprocess():
    """Reprocess a prior exceedance analysis using stored evidence plus optional new attachments."""
    client_ip = request.remote_addr or "unknown"
    if not _check_rate_limit(client_ip):
        return jsonify({"success": False, "error": "Too many requests. Please try again in a moment."}), 429

    analysis_key = sanitize_input(request.form.get("analysis_key", ""), 64)
    if not analysis_key:
        return jsonify({"success": False, "error": "analysis_key is required"}), 400

    history_store = _load_exceedance_history_store()
    history_items = history_store.get(analysis_key, [])
    if not history_items:
        return jsonify({"success": False, "error": "Analysis key not found"}), 404

    latest = history_items[-1]
    analysis_mode = sanitize_input(request.form.get(
        "analysis_mode", latest.get("analysis_mode", "standard")), 24).lower()
    retention_info = _cleanup_exceedance_retention()
    actor = _build_exceedance_actor_tag(client_ip)

    loaded = _load_persisted_exceedance_evidence(
        latest.get("stored_files", []))
    csv_rows = list(loaded.get("csv_rows", []))
    pdf_parts: List[str] = [
        str(loaded.get("pdf_text", "") or "")] if loaded.get("pdf_text") else []
    upload_specs: List[Dict[str, Any]] = []

    csv_files = request.files.getlist("csv_files") or []
    for f in csv_files[:5]:
        if not f or not f.filename:
            continue
        data = f.read()
        try:
            csv_rows.extend(_extract_rows_from_csv_bytes(data))
            upload_specs.append({
                "kind": "csv",
                "filename": f.filename,
                "data": data,
                "preview": data[:160].decode("utf-8", errors="replace"),
            })
        except Exception:
            continue

    pdf_files = request.files.getlist("pdf_files") or []
    for f in pdf_files[:5]:
        if not f or not f.filename:
            continue
        data = f.read()
        try:
            text = _extract_text_from_pdf_bytes(data)
            if text:
                pdf_parts.append(text)
            upload_specs.append({
                "kind": "pdf",
                "filename": f.filename,
                "data": data,
                "preview": text[:160] if text else "",
            })
        except Exception:
            continue

    csv_rows = csv_rows[:800]
    pdf_text = "\n\n".join([p for p in pdf_parts if p])[:18000]
    failure_text = sanitize_input(request.form.get(
        "failure_text", latest.get("failure_text", "")), _QUERY_MAX_LEN)
    scenario = sanitize_input(request.form.get(
        "scenario", latest.get("scenario", "")), _QUERY_MAX_LEN)
    tail = sanitize_input(request.form.get(
        "tail", latest.get("tail", "")), _FIELD_MAX_LEN)
    ata = sanitize_input(request.form.get(
        "ata", latest.get("ata", "")), _FIELD_MAX_LEN)
    modelo = sanitize_input(request.form.get(
        "modelo", latest.get("modelo", "")), _FIELD_MAX_LEN)

    open_cases = _find_open_troubleshooting_cases(
        failure_text=failure_text, scenario=scenario, limit=8)
    pdf_sections = _extract_pdf_sections(pdf_text)
    records_for_recurrence = load_records(limit=3000)
    ata_for_recurrence = ata or _extract_ata_from_text(
        failure_text) or _extract_ata_from_text(scenario)
    recurring_pattern = _detect_recurring_pattern(
        tail, ata_for_recurrence, records_for_recurrence)
    trend_window_analysis = _build_trend_window_analysis(
        tail=tail,
        ata=ata_for_recurrence,
        records=records_for_recurrence,
        window_months=6,
    )
    result = _build_exceedance_recommendation(
        failure_text=failure_text,
        scenario=scenario,
        csv_rows=csv_rows,
        pdf_text=pdf_text,
        open_cases=open_cases,
        pdf_sections=pdf_sections,
        recurring_pattern=recurring_pattern,
        trend_window_analysis=trend_window_analysis,
        tail=tail,
        modelo=modelo,
        analysis_mode=analysis_mode,
    )
    new_files = _persist_exceedance_uploads(analysis_key, upload_specs, actor)
    combined_files = list(latest.get("stored_files", [])) + new_files
    _append_exceedance_audit_entries([
        {
            "analysis_key": analysis_key,
            "actor": item.get("actor", actor),
            "timestamp": item.get("uploaded_at", datetime.now(timezone.utc).isoformat()),
            "kind": item.get("kind", "evidence"),
            "stored_name": item.get("stored_name", ""),
            "anonymized_name": item.get("anonymized_name", ""),
            "size_bytes": item.get("size_bytes", 0),
            "sha1": item.get("sha1", ""),
        }
        for item in new_files
    ])
    result = _finalize_exceedance_result(
        result=result,
        analysis_key=analysis_key,
        analysis_mode=analysis_mode,
        failure_text=failure_text,
        scenario=scenario,
        tail=tail,
        ata=ata,
        modelo=modelo,
        stored_files=combined_files,
    )
    result["retention_policy"] = retention_info

    return jsonify({
        "success": True,
        "data": result,
        "reprocessed_from": analysis_key,
        "loaded_stored_files": len(loaded.get("loaded_files", [])),
        "new_files": len(new_files),
    })


@analytics_bp.route("/api/ai/analyze_failure", methods=["POST"])
def api_analyze_failure():
    # ── Fase 5: rate limiting + sanitização ──────────────────────────────────
    client_ip = request.remote_addr or "unknown"
    if not _check_rate_limit(client_ip):
        return jsonify({"success": False, "error": "Too many requests. Please try again in a moment."}), 429

    payload = request.get_json(silent=True) or {}
    ai = get_ai()

    ata = sanitize_input(str(payload.get("ata", "")), max_len=8)
    description = sanitize_input(
        str(payload.get("description", "")), max_len=_QUERY_MAX_LEN)
    model = sanitize_input(str(payload.get("model", "")),
                           max_len=_FIELD_MAX_LEN)
    model_filter = sanitize_input(
        str(payload.get("model_filter", "")), max_len=_FIELD_MAX_LEN)
    category = sanitize_input(str(payload.get("category", "")), max_len=64)
    tail = sanitize_input(str(payload.get("tail", "")), max_len=32).upper()
    allow_auto_description = bool(payload.get("allow_auto_description", False))

    if not description and not allow_auto_description:
        return jsonify({
            "success": False,
            "error": "Description is required. Set 'allow_auto_description=true' to enable inferred prompts."
        }), 400

    effective_model_filter = _effective_model_filter(
        model_filter=model_filter or model,
        tail_filter=tail,
    )
    records = _filter_records_by_model_tail(
        load_records(limit=3000),
        model_filter=effective_model_filter,
        tail_filter=tail,
    )

    analytics = ai.get_analytics(records) if records else {}
    top_ata = ((analytics.get("top_ata") or [{}])[
               0] if isinstance(analytics, dict) else {})
    top_tail = ((analytics.get("top_tails") or [{}])[
                0] if isinstance(analytics, dict) else {})
    top_kw = ((analytics.get("top_keywords") or [["diagnostic", 0]])[
              0][0] if isinstance(analytics, dict) else "diagnostic")

    ata_ref_input = (ata or str(top_ata.get("ata", ""))).strip().split(".")[0]
    generated_description = False
    if not description and allow_auto_description:
        generated_description = True
        focus_model = effective_model_filter or model or DEFAULT_E2_MODEL_FILTER
        focus_tail = tail or str(top_tail.get("tail", "")).strip() or "fleet"
        focus_ata = ata_ref_input or "N/A"
        description = (
            f"Automatic fleet-level analysis for {focus_model}. "
            f"Focus tail: {focus_tail}. Focus ATA: {focus_ata}. "
            f"Primary issue family: {top_kw}. "
            "Generate troubleshooting path, risk outlook, and preventive actions based on historical records, FH and FC exposure."
        )

    result = ai.analyze_failure(
        ata=ata_ref_input,
        description=description,
        model=model,
        categoria=category,
    )

    metrics = _load_tail_metrics().get(tail, {}) if tail else {}
    tail_fh = _safe_float(metrics.get("fh"), 0.0)
    tail_fc = _safe_float(metrics.get("fc"), 0.0)
    if tail and records and (tail_fh <= 0 or tail_fc <= 0):
        for rec in records:
            if str(rec.get("tail", "")).strip() == tail:
                tail_fh = max(tail_fh, _safe_float(rec.get("fh"), 0.0))
                tail_fc = max(tail_fc, _safe_float(rec.get("fc"), 0.0))

    ata_ref = (ata_ref_input or result.get(
        "matched_ata", "")).strip().split(".")[0]
    tail_count = sum(
        1 for r in records if str(r.get("tail", "")).strip() == tail
    ) if tail else 0
    ata_count = sum(
        1
        for r in records
        if str(r.get("ata", "")).strip().split(".")[0] == ata_ref
    ) if ata_ref else 0

    max_fh = max((_safe_float(r.get("fh"), 0.0) for r in records), default=1.0)
    max_fc = max((_safe_float(r.get("fc"), 0.0) for r in records), default=1.0)

    feedback_acceptance = _feedback_acceptance_for_ata(ata_ref)
    risk = _compute_failure_risk(
        severity=result.get("severity_estimate", "Medium"),
        confidence=_safe_float(result.get("confidence"), 0.0),
        tail_count=tail_count,
        ata_count=ata_count,
        fh=tail_fh,
        fc=tail_fc,
        max_fh=max_fh,
        max_fc=max_fc,
        feedback_acceptance=feedback_acceptance,
    )

    similar_cases = _find_similar_cases(
        records=records,
        ata=ata_ref,
        description=description,
        tail=tail,
        limit=5,
    )
    comparative_troubleshooting = _build_comparative_troubleshooting(
        records=records,
        similar_cases=similar_cases,
    )
    recommended_plan = _build_recommended_plan(
        risk=risk,
        analysis=result,
        similar_cases=similar_cases,
        tail=tail,
        ata=ata_ref,
    )

    result["tail_metrics"] = {
        "tail": tail or "N/A",
        "fh": round(tail_fh, 1),
        "fc": int(tail_fc),
    }
    result["learning_hint"] = _feedback_hint_for_ata(
        ata_ref or result.get("matched_ata", "")
    )
    fh_fc_priority = _compute_fh_fc_priorities(records)
    projection_signals = _build_projection_signals(records, fh_fc_priority)
    ata_projection = _build_ata_projection(records, ata_ref)
    mel_items = _load_mel_context(limit=700)
    aog_items = _load_aog_context(limit=700)
    relevant_tails = {
        str(item.get("tail", "") or "").strip().upper()
        for item in records
        if str(item.get("tail", "") or "").strip()
    }
    if tail:
        relevant_tails = {tail.strip().upper()}
    active_aog_count = sum(
        1
        for item in aog_items
        if str(item.get("tail", "") or "").strip().upper() in relevant_tails
        and not item.get("release_date")
    )
    open_mel_count = sum(
        1
        for item in mel_items
        if str(item.get("tail", "") or "").strip().upper() in relevant_tails
        and not item.get("date_closed")
    )
    executive_opinion = _build_executive_opinion(
        risk=risk,
        projection=projection_signals,
        similar_cases=similar_cases,
        active_aog=active_aog_count,
        open_mel=open_mel_count,
        focus_tail=(tail or "").strip().upper(),
        focus_ata=ata_ref,
    )
    autonomy_score = _compute_autonomy_score(
        generated_description=generated_description,
        similar_cases_count=len(similar_cases),
        records_count=len(records),
        ata_count=ata_count,
        tail_count=tail_count,
        active_aog_count=active_aog_count,
        open_mel_count=open_mel_count,
        trend_direction=str(projection_signals.get(
            "trend_direction", "stable")),
    )
    operational_impact = _build_operational_impact(
        risk=risk,
        projection=projection_signals,
        active_aog_count=active_aog_count,
        open_mel_count=open_mel_count,
    )
    drift_alert = _build_forecast_drift_alert(projection_signals)
    intervention_queue = _build_autonomous_intervention_queue(
        fh_fc_priority=fh_fc_priority,
        projection=projection_signals,
        impact=operational_impact,
    )
    mission_brief = _build_mission_brief(
        queue=intervention_queue,
        drift_alert=drift_alert,
        autonomy=autonomy_score,
    )
    result["intelligence"] = {
        **risk,
        "tail_recurrence": tail_count,
        "ata_recurrence": ata_count,
        "similar_cases": similar_cases,
        "comparative_troubleshooting": comparative_troubleshooting,
        "recommended_plan": recommended_plan,
        "feedback_acceptance": round(feedback_acceptance * 100, 1),
        "active_aog": active_aog_count,
        "open_mel": open_mel_count,
        "projection": {
            "trend_direction": projection_signals.get("trend_direction", "stable"),
            "growth_rate_pct": projection_signals.get("growth_rate_pct", 0.0),
            "next_30d_expected": projection_signals.get("next_30d_expected", 0),
            "next_90d_expected": projection_signals.get("next_90d_expected", 0),
            "narrative": projection_signals.get("narrative", ""),
        },
        "executive_opinion": executive_opinion,
        "autonomy": autonomy_score,
        "operational_impact": operational_impact,
        "drift_alert": drift_alert,
        "intervention_queue": intervention_queue,
        "mission_brief": mission_brief,
        "button_identity": _button_identity_for_risk(
            risk.get("risk_level", "medium")
        ),
    }
    result["projection_signals"] = {
        **projection_signals,
        "ata_projection": ata_projection,
        "autonomy": autonomy_score,
        "operational_impact": operational_impact,
        "drift_alert": drift_alert,
        "intervention_queue": intervention_queue,
        "mission_brief": mission_brief,
    }
    result["auto_context"] = {
        "description_generated": generated_description,
        "effective_model_filter": effective_model_filter,
        "tail_filter": tail,
        "inferred_ata": ata_ref,
        "seed_keyword": str(top_kw),
        "records_used": len(records),
    }
    result["strategic_outlook"] = {
        "executive_opinion": executive_opinion,
        "hotspot_focus": fh_fc_priority[:3],
        "autonomy": autonomy_score,
        "operational_impact": operational_impact,
        "drift_alert": drift_alert,
        "intervention_queue": intervention_queue,
        "mission_brief": mission_brief,
        "autonomy_actions": [
            "Prioritize preventive tasks on highest projected hotspot risk.",
            "Keep MEL/AOG restriction dashboard synchronized with top ATA recurrence.",
            "Run daily projection refresh and escalate if trend remains UP for 2 consecutive cycles.",
        ],
    }

    return jsonify({"success": True, "data": result})


@analytics_bp.route("/api/ai/analytics", methods=["GET"])
def api_ai_analytics():
    model_filter = _effective_model_filter(
        model_filter=str(request.args.get("model", "") or "").strip(),
        tail_filter=str(request.args.get("tail", "") or "").strip().upper(),
    )
    tail_filter = str(request.args.get("tail", "") or "").strip().upper()
    records = _filter_records_by_model_tail(
        load_records(limit=3000),
        model_filter=model_filter,
        tail_filter=tail_filter,
    )
    ai = get_ai()
    analytics = ai.get_analytics(records)

    return jsonify(
        {
            "success": True,
            "records_count": len(records),
            "analytics": analytics,
        }
    )


@analytics_bp.route("/api/ai/chat", methods=["POST"])
def api_ai_chat():
    # ── Fase 5: rate limiting ────────────────────────────────────────────────
    client_ip = request.remote_addr or "unknown"
    if not _check_rate_limit(client_ip):
        return jsonify({"success": False, "error": "Too many requests. Please try again in a moment."}), 429

    payload = request.get_json(silent=True) or {}

    # ── Fase 5: input sanitization ───────────────────────────────────────────
    query = sanitize_input(str(payload.get("query", "")),
                           max_len=_QUERY_MAX_LEN)
    scope = sanitize_input(
        str(payload.get("scope", "global")), max_len=32).lower() or "global"
    requested_conversation_id = sanitize_input(
        str(payload.get("conversation_id", "")), max_len=64)
    model_filter = sanitize_input(
        str(payload.get("model_filter", "")), max_len=_FIELD_MAX_LEN)
    tail_filter = sanitize_input(
        str(payload.get("tail_filter", "")), max_len=32).upper()
    deep_mode = bool(payload.get("deep_mode", False))

    if not query:
        return jsonify({"success": False, "error": "Query is required."}), 400

    conversation_id = requested_conversation_id or _ensure_conversation_id()
    if requested_conversation_id and session.get("ai_conversation_id") != requested_conversation_id:
        session["ai_conversation_id"] = requested_conversation_id
    conversation_history = _load_conversation_history(
        conversation_id, limit=24)

    # ── Fase 4: response cache (skip for deep_mode to always return fresh analysis) ──
    cache_hit = None
    if not deep_mode:
        ck = _cache_key(query, scope, tail_filter, model_filter)
        cache_hit = _cache_get(ck)

    if cache_hit:
        response = dict(cache_hit)
        response["cached"] = True
    else:
        response = _build_copilot_answer(
            query=query,
            scope=scope,
            conversation_history=conversation_history,
            model_filter=model_filter,
            tail_filter=tail_filter,
            deep_mode=deep_mode,
        )
        if not deep_mode:
            _cache_set(ck, response)

    _append_conversation_turn(
        conversation_id=conversation_id,
        msg_type="user",
        text=query,
        scope=scope,
    )
    updated_history = _append_conversation_turn(
        conversation_id=conversation_id,
        msg_type="bot",
        text=str(response.get("response", "")),
        scope=scope,
        sources=response.get("sources") if isinstance(
            response.get("sources"), dict) else {},
    )
    response["conversation_id"] = conversation_id
    response["conversation_history"] = updated_history[-24:]

    return jsonify({"success": True, "data": response})


@analytics_bp.route("/api/ai/chat/history", methods=["GET", "DELETE"])
def api_ai_chat_history():
    conversation_id = _ensure_conversation_id()

    if request.method == "DELETE":
        _set_conversation_history(conversation_id, [])
        return jsonify(
            {
                "success": True,
                "conversation_id": conversation_id,
                "conversation_history": [],
            }
        )

    history = _load_conversation_history(conversation_id, limit=24)
    return jsonify(
        {
            "success": True,
            "conversation_id": conversation_id,
            "conversation_history": history,
        }
    )


@analytics_bp.route("/api/ai/ata/<string:ata>", methods=["GET"])
def api_ata_details(ata: str):
    ai = get_ai()
    procedure = ai.get_ata_procedure(ata)
    if "error" in procedure:
        return jsonify({"success": False, "error": procedure["error"]}), 404

    return jsonify({"success": True, "data": procedure})


@analytics_bp.route("/api/ai/summary", methods=["GET"])
def api_ai_summary():
    model_filter = _effective_model_filter(
        model_filter=str(request.args.get("model", "") or "").strip(),
        tail_filter=str(request.args.get("tail", "") or "").strip().upper(),
    )
    tail_filter = str(request.args.get("tail", "") or "").strip().upper()
    records = _filter_records_by_model_tail(
        load_records(limit=5000),
        model_filter=model_filter,
        tail_filter=tail_filter,
    )
    ai = get_ai()
    analytics = ai.get_analytics(records)
    fh_fc_priority = _compute_fh_fc_priorities(records)
    projection_signals = _build_projection_signals(records, fh_fc_priority)
    ata_projection = _build_ata_projection(
        records, str(request.args.get("ata", "") or ""))

    if "error" in analytics:
        fallback_summary = {
            "most_common_failure_keyword": "N/A",
            "most_common_ata": {"ata": "N/A", "system": "Not available"},
            "most_recurring_tail": {"tail": "N/A", "count": 0},
            "recurring_tails": [],
            "fh_fc_priority": [],
            "intelligence_depth": {
                "feedback_acceptance_rate": 0.0,
                "feedback_samples": 0,
                "priority_hotspots": [],
                "projection_signals": projection_signals,
                "ata_projection": {"ata": "N/A", "history": [], "forecast": []},
                "family_comparison": [],
                "executive_opinion": {
                    "stance": "monitor",
                    "confidence": 0,
                    "why": [
                        "No records matched current model/tail filter.",
                        "Run autonomous analysis with broader family scope to generate projections.",
                    ],
                    "what_if": [],
                },
                "autonomy": {
                    "score": 20,
                    "level": "guided",
                    "message": "AI still needs explicit contextual details to maximize precision.",
                },
                "operational_impact": {
                    "dispatch_risk": "LOW",
                    "estimated_delay_hours": 0.0,
                    "maintenance_pressure": 0,
                    "active_aog": 0,
                    "open_mel": 0,
                },
                "drift_alert": {
                    "status": "insufficient",
                    "deviation_pct": 0.0,
                    "message": "Insufficient history for forecast drift calculation.",
                    "action": "Collect more monthly records to evaluate forecast reliability.",
                },
                "intervention_queue": [],
                "mission_brief": {
                    "headline": "No immediate intervention queue available.",
                    "autonomy_level": "guided",
                    "drift_status": "insufficient",
                    "drift_message": "Insufficient history for forecast drift calculation.",
                    "next_action": "Keep monitoring and refresh analytics daily.",
                },
                "focus_message": "No sufficient data for deep prioritization.",
            },
            "recommended_actions": [
                "Clear very restrictive filters and rerun summary.",
                "Populate new failures with ATA/tail/model to improve AI context.",
                "Use AI Copilot with autonomous prompt to bootstrap recommendations.",
            ],
        }
        return jsonify(
            {
                "success": True,
                "summary": fallback_summary,
                "records_count": 0,
            }
        )

    top_tail = (
        analytics.get("top_tails", [{}])[0]
        if analytics.get("top_tails")
        else {}
    )
    top_ata = (
        analytics.get("top_ata", [{}])[0]
        if analytics.get("top_ata")
        else {}
    )
    recurring = analytics.get("recurring_tails", [])
    feedback_items = _load_feedback()
    feedback_total = len(feedback_items)
    feedback_positive = sum(
        1 for x in feedback_items if bool(x.get("helpful")) is True
    )
    feedback_acceptance = (
        round((feedback_positive / feedback_total) * 100, 1)
        if feedback_total
        else 0.0
    )
    family_comparison = _build_family_comparison(records)
    summary_autonomy = _compute_autonomy_score(
        generated_description=True,
        similar_cases_count=0,
        records_count=len(records),
        ata_count=1 if str(top_ata.get("ata", "")) else 0,
        tail_count=1 if str(top_tail.get("tail", "")) else 0,
        active_aog_count=0,
        open_mel_count=0,
        trend_direction=str(projection_signals.get(
            "trend_direction", "stable")),
    )
    summary_impact = _build_operational_impact(
        risk={
            "risk_score": fh_fc_priority[0].get("risk_score", 0) if fh_fc_priority else 0,
        },
        projection=projection_signals,
        active_aog_count=0,
        open_mel_count=0,
    )
    summary_opinion = _build_executive_opinion(
        risk={
            "risk_level": fh_fc_priority[0].get("risk_level", "medium") if fh_fc_priority else "medium",
            "risk_score": fh_fc_priority[0].get("risk_score", 0) if fh_fc_priority else 0,
        },
        projection=projection_signals,
        similar_cases=[],
        active_aog=0,
        open_mel=0,
        focus_tail=str(top_tail.get("tail", "") or ""),
        focus_ata=str(top_ata.get("ata", "") or ""),
    )
    summary_drift = _build_forecast_drift_alert(projection_signals)
    summary_queue = _build_autonomous_intervention_queue(
        fh_fc_priority=fh_fc_priority,
        projection=projection_signals,
        impact=summary_impact,
    )
    summary_mission = _build_mission_brief(
        queue=summary_queue,
        drift_alert=summary_drift,
        autonomy=summary_autonomy,
    )

    summary = {
        "most_common_failure_keyword": (
            analytics.get("top_keywords") or [["N/A", 0]]
        )[0][0],
        "most_common_ata": top_ata,
        "most_recurring_tail": top_tail,
        "recurring_tails": recurring,
        "fh_fc_priority": fh_fc_priority,
        "intelligence_depth": {
            "feedback_acceptance_rate": feedback_acceptance,
            "feedback_samples": feedback_total,
            "priority_hotspots": fh_fc_priority[:3],
            "projection_signals": projection_signals,
            "ata_projection": ata_projection,
            "family_comparison": family_comparison,
            "executive_opinion": summary_opinion,
            "autonomy": summary_autonomy,
            "operational_impact": summary_impact,
            "drift_alert": summary_drift,
            "intervention_queue": summary_queue,
            "mission_brief": summary_mission,
            "focus_message": (
                "Use critical/high hotspots to drive deep "
                "inspection planning and preventive routines."
            ),
        },
        "recommended_actions": [
            "Prioritize preventive inspections on recurring tails.",
            "Standardize troubleshooting checklist for top ATA chapters.",
            (
                "Escalate recurrent critical/high failures "
                "for engineering review."
            ),
            "Correlate FH/FC exposure with ATA recurrence trends.",
            (
                "Feed operator feedback continuously to recalibrate "
                "offline AI recommendations."
            ),
        ],
    }

    return jsonify(
        {"success": True, "records_count": len(records), "summary": summary}
    )


@analytics_bp.route("/api/ai/feedback", methods=["POST"])
def api_ai_feedback():
    payload = request.get_json(silent=True) or {}
    ata = str(payload.get("ata", "")).strip().split(".")[0]
    helpful = payload.get("helpful")
    if not isinstance(helpful, bool):
        return (
            jsonify(
                {
                    "success": False,
                    "error": "Field 'helpful' must be boolean.",
                }
            ),
            400,
        )

    entry = {
        "ata": ata,
        "helpful": helpful,
        "query": str(payload.get("query", "")).strip()[:500],
        "response_excerpt": str(
            payload.get("response_excerpt", "")
        ).strip()[:1000],
        "source": str(payload.get("source", "dashboard")).strip()[:50],
        "timestamp": (
            str(payload.get("timestamp", "")).strip()
            or datetime.now(timezone.utc).isoformat()
        ),
    }
    saved = _save_feedback_entry(entry)
    return jsonify({"success": True, "data": saved})


@analytics_bp.route("/api/ai/recalibrate", methods=["POST"])
def api_ai_recalibrate():
    """Batch-recalibration endpoint.

    Analyses stored feedback and emits per-ATA calibration signals.
    Signals ``boost`` / ``stable`` / ``review`` guide the weight the
    AI engine should give to its own recommendations for each chapter.
    """
    items = _load_feedback()
    if not items:
        return jsonify(
            {
                "success": True,
                "message": "No feedback data available for recalibration.",
                "calibration": {},
                "overall_acceptance_pct": 0.0,
                "total_samples_analyzed": 0,
                "ata_count": 0,
                "review_required_count": 0,
                "review_list": [],
                "calibration_timestamp": (
                    datetime.now(timezone.utc).isoformat()
                ),
            }
        )

    ata_groups: Dict[str, Dict[str, int]] = {}
    for it in items:
        ata = str(it.get("ata", "")).strip() or "unknown"
        ata_groups.setdefault(ata, {"positive": 0, "negative": 0, "total": 0})
        ata_groups[ata]["total"] += 1
        if bool(it.get("helpful")) is True:
            ata_groups[ata]["positive"] += 1
        else:
            ata_groups[ata]["negative"] += 1

    calibration: Dict[str, Any] = {}
    for ata, stats in ata_groups.items():
        acceptance = stats["positive"] / max(stats["total"], 1)
        if acceptance >= 0.75:
            signal = "boost"
            weight_adjustment = round(1.0 + (acceptance - 0.75) * 0.8, 3)
            review_required = False
        elif acceptance >= 0.50:
            signal = "stable"
            weight_adjustment = 1.0
            review_required = False
        else:
            signal = "review"
            weight_adjustment = round(max(0.4, acceptance + 0.1), 3)
            review_required = True

        calibration[ata] = {
            "ata": ata,
            "total_samples": stats["total"],
            "acceptance_rate": round(acceptance * 100, 1),
            "signal": signal,
            "weight_adjustment": weight_adjustment,
            "review_required": review_required,
        }

    review_list = [v for v in calibration.values() if v["review_required"]]
    total_samples = sum(v["total_samples"] for v in calibration.values())
    overall_positive = sum(g["positive"] for g in ata_groups.values())
    overall_acceptance = round(
        overall_positive / max(total_samples, 1) * 100, 1
    )

    return jsonify(
        {
            "success": True,
            "calibration_timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_acceptance_pct": overall_acceptance,
            "total_samples_analyzed": total_samples,
            "ata_count": len(calibration),
            "review_required_count": len(review_list),
            "calibration": calibration,
            "review_list": sorted(
                review_list, key=lambda x: x["acceptance_rate"]
            ),
        }
    )


@analytics_bp.route("/api/ai/feedback/stats", methods=["GET"])
def api_ai_feedback_stats():
    items = _load_feedback()
    total = len(items)
    positives = sum(1 for x in items if bool(x.get("helpful")) is True)
    negatives = sum(1 for x in items if bool(x.get("helpful")) is False)
    acceptance = round((positives / total) * 100, 1) if total else 0.0

    ata_breakdown: Dict[str, Dict[str, Any]] = {}
    for it in items:
        ata = str(it.get("ata", "N/A")).strip() or "N/A"
        ata_breakdown.setdefault(ata, {"ata": ata, "total": 0, "positive": 0})
        ata_breakdown[ata]["total"] += 1
        if bool(it.get("helpful")) is True:
            ata_breakdown[ata]["positive"] += 1

    top = sorted(
        (
            {
                "ata": v["ata"],
                "total": v["total"],
                "acceptance": (
                    round((v["positive"] / v["total"]) * 100, 1)
                    if v["total"]
                    else 0.0
                ),
            }
            for v in ata_breakdown.values()
        ),
        key=lambda x: x["total"],
        reverse=True,
    )[:10]

    return jsonify(
        {
            "success": True,
            "stats": {
                "total_feedback": total,
                "positive": positives,
                "negative": negatives,
                "acceptance_rate": acceptance,
                "top_ata_feedback": top,
            },
        }
    )


# ============================================================================
# V10 FOUNDATION ENDPOINTS - LEGACY COMPATIBILITY LAYER
# ============================================================================

@analytics_bp.route("/api/ai/monthly_trend", methods=["GET"])
def api_monthly_trend():
    """V10 foundation metric: Monthly Failure Trend."""
    records = load_records(limit=3000)
    months_param = request.args.get("months", "12", type=int)

    trend = build_monthly_failure_trend(records, months_back=months_param)
    return jsonify({"success": True, "data": trend})


@analytics_bp.route("/api/ai/exposure_hotspots", methods=["GET"])
def api_exposure_hotspots():
    """V10 foundation metric: Exposure & Hotspots."""
    records = load_records(limit=2000)
    model_filter = request.args.get("model_filter", "")
    tail_filter = request.args.get("tail_filter", "")

    filtered = _filter_records_by_model_tail(
        records, model_filter, tail_filter)
    fh_fc_priority = _compute_fh_fc_priorities(filtered)
    hotspots = build_exposure_and_hotspots(filtered, fh_fc_priority)

    return jsonify({"success": True, "data": hotspots})


@analytics_bp.route("/api/ai/ata/<string:ata>/quick_ref", methods=["GET"])
def api_ata_quick_ref(ata: str):
    """V10 foundation metric: ATA Quick Reference."""
    records = load_records(limit=2000)
    ref = build_ata_quick_reference(records, ata)
    return jsonify({"success": True, "data": ref})


@analytics_bp.route("/api/ai/daily_brief", methods=["GET"])
def api_daily_brief():
    """V10 foundation metric: Daily Brief Generation."""
    records = load_records(limit=1000)
    mel_items = _load_mel_context(limit=100)
    aog_items = _load_aog_context(limit=100)
    fh_fc_priority = _compute_fh_fc_priorities(records)
    projection = _build_projection_signals(records, fh_fc_priority)
    drift = _build_forecast_drift_alert(projection)
    impact = _build_operational_impact({"risk_score": 50}, projection, 0, 0)

    brief = daily_brief_generation(
        records,
        _build_autonomous_intervention_queue(
            fh_fc_priority, projection, impact),
        drift,
        len([m for m in mel_items if not m.get("date_closed")]),
        len([a for a in aog_items if not a.get("release_date")])
    )

    return jsonify({"success": True, "data": brief})


@analytics_bp.route("/api/ai/executive_dashboard", methods=["GET"])
def api_executive_dashboard():
    """V10 foundation metric: Executive Dashboard."""
    records = load_records(limit=2000)
    mel_items = _load_mel_context(limit=100)
    aog_items = _load_aog_context(limit=100)
    fh_fc_priority = _compute_fh_fc_priorities(records)
    projection = _build_projection_signals(records, fh_fc_priority)
    impact = _build_operational_impact({"risk_score": 50}, projection, 0, 0)
    queue = _build_autonomous_intervention_queue(
        fh_fc_priority, projection, impact)

    dashboard = executive_dashboard_builder(
        records, queue, mel_items, aog_items)
    return jsonify({"success": True, "data": dashboard})


@analytics_bp.route("/api/ai/page_context", methods=["POST"])
def api_page_context():
    """V10 foundation metric: Page Context Analysis."""
    payload = request.get_json() or {}
    page_url = payload.get("page_url", "")
    form_data = payload.get("form_data", {})
    visible_text = payload.get("visible_text", "")

    context = page_context_analyzer(page_url, form_data, visible_text)
    return jsonify({"success": True, "data": context})


@analytics_bp.route("/api/ai/cadastro/similar_cases", methods=["POST"])
def api_cadastro_similar_cases():
    """V10 foundation metric: Cadastro Semantic Case Matching."""
    payload = request.get_json() or {}
    description = payload.get("description", "")

    all_records = load_records(limit=2000)
    similar = cadastro_semantic_case_matching(
        description, all_records, similarity_threshold=0.20)

    return jsonify({"success": True, "data": {"similar_cases": similar, "count": len(similar)}})


@analytics_bp.route("/api/ai/copilot", methods=["POST"])
def api_copilot():
    """
    V10 Floating Global Copilot Endpoint

    Processes requests from the floating copilot widget displayed on all pages.
    Captures page context and provides contextual AI recommendations.
    """
    payload = request.get_json() or {}
    query = payload.get("query", "")
    page_context = payload.get("page_context", {})
    scope = payload.get("scope", "global")

    # Build copilot answer with page context
    result = _build_copilot_answer(
        query=query,
        scope=scope,
        conversation_history=_load_conversation_history(
            _ensure_conversation_id(), limit=12),
        model_filter="",
        tail_filter="",
        deep_mode=False,
    )

    # If cadastro page, enhance with similar cases
    if "cadastro" in page_context.get("page_url", ""):
        all_records = load_records(limit=2000)
        similar_cases = cadastro_semantic_case_matching(
            query, all_records, threshold=0.20)
        result["similar_cases"] = similar_cases

    # Record conversation turn
    _append_conversation_turn(
        _ensure_conversation_id(),
        "user",
        query,
        scope=scope,
        sources={"page_context": bool(page_context)}
    )

    return jsonify({
        "success": True,
        "data": result
    })


# ═══════════════════════════════════════════════════════════════════════════════
# V10.0 API ENDPOINTS — NOVOS RECURSOS
# ═══════════════════════════════════════════════════════════════════════════════

@analytics_bp.route("/ai/v10/analyze", methods=["POST"])
def ai_v10_analyze():
    """
    V10 Advanced AI analysis — 100 melhorias ativas.
    POST body: { "query": str, "session_id": str, "user_id": str }
    """
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    if not query:
        return jsonify({"success": False, "error": "query is required"}), 400
    if len(query) > 2000:
        return jsonify({"success": False, "error": "query too long"}), 400

    user_id = data.get("user_id") or session.get("user_id", "anon")
    session_id = data.get("session_id") or session.get("ai_session_id")

    engine = get_v10_engine()
    if session_id is None:
        session_id = engine.start_user_session(user_id)
        session["ai_session_id"] = session_id

    result = engine.process_query(
        query, session_id=session_id, user_id=user_id)
    copilot = _build_copilot_answer(
        query=query,
        scope=str(data.get("scope") or "global"),
        conversation_history=[],
        model_filter=str(data.get("model_filter") or ""),
        tail_filter=str(data.get("tail_filter") or ""),
        deep_mode=bool(data.get("deep_mode", False)),
    )
    return jsonify({
        "success": True,
        "data": {
            **result,
            "response": copilot.get("response", ""),
            "confidence_score": copilot.get("confidence_score", int((result.get("confidence", 0.0) or 0.0) * 100)),
            "confidence_grade": copilot.get("confidence_grade", result.get("confidence_grade", "C")),
            "next_questions": copilot.get("next_questions", []),
            "projection_signals": copilot.get("projection_signals", {}),
            "chart_focus": copilot.get("chart_focus", {}),
            "response_sections": copilot.get("response_sections", {}),
            "language_variant": copilot.get("language_variant", result.get("language", "pt-BR")),
        }
    })


@analytics_bp.route("/ai/v10/ata-info/<ata_code>", methods=["GET"])
def ai_v10_ata_info(ata_code: str):
    """
    Retorna informações completas de um capítulo ATA.
    GET /ai/v10/ata-info/29
    """
    info = get_ata_info(ata_code)
    if not info:
        return jsonify({"success": False, "error": f"ATA {ata_code} não encontrado"}), 404
    related_info = []
    for r in find_related_atas(ata_code):
        ri = get_ata_info(r)
        if ri:
            related_info.append(
                {"ata": r, "name": ri["name"], "pt": ri.get("pt", "")})
    return jsonify({
        "success": True,
        "ata": ata_code,
        "info": info,
        "related": related_info,
    })


@analytics_bp.route("/ai/v10/ata-list", methods=["GET"])
def ai_v10_ata_list():
    """Retorna lista completa do knowledge graph ATA."""
    result = []
    for code, info in sorted(ATA_KNOWLEDGE_GRAPH.items(), key=lambda x: int(x[0])):
        result.append({
            "ata": code,
            "name": info["name"],
            "pt": info.get("pt", ""),
            "criticality": info.get("criticality", ""),
        })
    return jsonify({"success": True, "count": len(result), "ata_chapters": result})


@analytics_bp.route("/ai/v10/feedback", methods=["POST"])
def ai_v10_feedback():
    """
    Registra feedback de acerto/erro do AI para aprendizado.
    POST body: { "query": str, "intent": str, "correct": bool, "correct_intent": str }
    """
    data = request.get_json(silent=True) or {}
    query = (data.get("query") or "").strip()
    intent = (data.get("intent") or "").strip()
    was_correct = bool(data.get("correct", True))
    correct_intent = data.get("correct_intent")

    if not query or not intent:
        return jsonify({"success": False, "error": "query and intent required"}), 400

    engine = get_v10_engine()
    engine.submit_feedback(query, intent, was_correct, correct_intent)
    return jsonify({"success": True, "message": "Feedback registrado"})


@analytics_bp.route("/ai/v10/performance", methods=["GET"])
def ai_v10_performance():
    """Retorna dashboard de performance do AI engine V10."""
    engine = get_v10_engine()
    dashboard = engine.learning_engine.get_performance_dashboard()
    calibration = engine.learning_engine.auto_calibrate_thresholds()
    return jsonify({
        "success": True,
        "dashboard": dashboard,
        "calibration": calibration,
        "version": "10.0",
    })

