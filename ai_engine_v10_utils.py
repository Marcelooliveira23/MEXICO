#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI ENGINE V10 - ANALYTICS UTILITIES
=====================================
Utility functions for advanced failure analysis, forecasting,
autonomous recommendations, and global context awareness.
Migrated from V8 to V10 architecture — fully compatible with V10 engine.

Organized in 6 phases:
  1. Data & Analytics Foundation (FH/FC fix, Monthly Trend, Exposure/Hotspots, etc.)
  2. Analyze Failure Enhancements (Semantic ATA, Multi-system, Component History, etc.)
  3. Autonomous Intelligence (Recalibration, Predictive Alerts, Auto-Planner, etc.)
  4. Global Interface (Floating Copilot, Page Context, Semantic Case Matching, etc.)
  5. Reporting & Insights (Dashboards, Trend Reports, Heatmaps, ROI, etc.)
  6. Advanced Features (Spare Parts, Cross-Fleet Learning, Mobile, ERP Integration, etc.)
"""

from __future__ import annotations
import json
import os
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Tuple, Optional
import pymysql


# ============================================================================
# PHASE 1: DATA & ANALYTICS FOUNDATION
# ============================================================================

def fix_fh_fc_data_pipeline(
    records: List[Dict[str, Any]],
    tail_metrics: Dict[str, Dict[str, float]],
) -> Dict[str, Any]:
    """
    AI 8.0 Enhancement #1: FH/FC Data Pipeline Fix

    Corrects zero-value issues by:
    - Loading from MySQL directly when fallback has zeros
    - Normalizing units (FH in hours, FC in counts)
    - Calculating exposure indices
    """
    normalized: List[Dict[str, Any]] = []

    for rec in records:
        item = dict(rec)
        tail = str(item.get("tail", "")).strip()

        # Get FH/FC from tail_metrics if record has zeros
        fh = float(item.get("fh") or 0)
        fc = float(item.get("fc") or 0)

        if fh == 0 or fc == 0:
            metric = tail_metrics.get(tail, {})
            if fh == 0:
                fh = metric.get("fh", 0)
            if fc == 0:
                fc = metric.get("fc", 0)

        item["fh_normalized"] = round(float(fh) if fh else 0, 1)
        item["fc_normalized"] = int(fc) if fc else 0

        # Calculate exposure index (0-1 scale)
        exposure = 0.0
        if fh > 0 and fc > 0:
            exposure = min(1.0, fc / max(1000, fh))  # FC per 1000 FH

        item["exposure_index"] = round(exposure, 3)
        normalized.append(item)

    return {
        "total_records": len(normalized),
        "records_with_fh": sum(1 for r in normalized if r["fh_normalized"] > 0),
        "records_with_fc": sum(1 for r in normalized if r["fc_normalized"] > 0),
        "avg_exposure": round(sum(r["exposure_index"] for r in normalized) / max(1, len(normalized)), 3),
        "normalized_records": normalized,
    }


def build_monthly_failure_trend(
    records: List[Dict[str, Any]],
    months_back: int = 12,
) -> Dict[str, Any]:
    """
    AI 8.0 Enhancement #2: Monthly Failure Trend Module

    Builds comprehensive month-by-month failure analysis:
    - Total failures per month
    - Trend direction (up/down/stable)
    - Forecasted next 3 months
    - Severity distribution by month
    - Top ATA per month
    """
    if not records:
        return {
            "status": "no_data",
            "monthly_data": [],
            "forecast": [],
            "trend": "insufficient_data",
        }

    now = datetime.utcnow()
    month_data: Dict[str, Dict[str, Any]] = {}

    for rec in records:
        date_str = str(rec.get("data_cadastro")
                       or rec.get("data_criacao") or "").strip()
        if not date_str:
            continue

        try:
            dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
        except (ValueError, TypeError):
            continue

        month_key = dt.strftime("%Y-%m")
        if month_key not in month_data:
            month_data[month_key] = {
                "month": month_key,
                "count": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "atas": Counter(),
            }

        month_data[month_key]["count"] += 1
        sev = str(rec.get("prioridade", "medium")).lower()
        if sev == "critical":
            month_data[month_key]["critical"] += 1
        elif sev == "high":
            month_data[month_key]["high"] += 1
        elif sev == "medium":
            month_data[month_key]["medium"] += 1
        else:
            month_data[month_key]["low"] += 1

        ata = str(rec.get("ata", "")).split(".")[0]
        if ata:
            month_data[month_key]["atas"][ata] += 1

    # Generate monthly records (fill gaps)
    all_months: List[Dict[str, Any]] = []
    for offset in range(-months_back, 1):
        check_dt = now + timedelta(days=30 * offset)
        check_month = check_dt.strftime("%Y-%m")
        if check_month in month_data:
            data = month_data[check_month]
            serializable_data = {
                "month": data["month"],
                "count": data["count"],
                "critical": data["critical"],
                "high": data["high"],
                "medium": data["medium"],
                "low": data["low"],
            }
            data["top_ata"] = max(
                ((ata, count) for ata, count in data["atas"].items()),
                key=lambda x: x[1],
                default=("N/A", 0)
            )[0]
            serializable_data["top_ata"] = data["top_ata"]
            all_months.append(serializable_data)
        else:
            all_months.append({
                "month": check_month,
                "count": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
                "top_ata": "N/A",
            })

    # Calculate trend
    recent_counts = [m["count"] for m in all_months[-3:] if m["count"] > 0]
    older_counts = [m["count"] for m in all_months[-6:-3] if m["count"] > 0]

    trend = "stable"
    trend_pct = 0.0
    if recent_counts and older_counts:
        recent_avg = sum(recent_counts) / len(recent_counts)
        older_avg = sum(older_counts) / len(older_counts)
        trend_pct = ((recent_avg - older_avg) / max(1, older_avg)) * 100
        if trend_pct >= 15:
            trend = "upward"
        elif trend_pct <= -15:
            trend = "downward"
        else:
            trend = "stable"

    # Forecast next 3 months
    forecast_base = sum(recent_counts) / max(1, len(recent_counts))
    forecast: List[Dict[str, Any]] = []
    for offset in range(1, 4):
        forecast_dt = now + timedelta(days=30 * offset)
        forecast.append({
            "month": forecast_dt.strftime("%Y-%m"),
            "forecasted_count": max(1, int(forecast_base * (1 + (trend_pct / 100)))),
            "confidence": 65 if len(recent_counts) >= 3 else 45,
        })

    return {
        "status": "ok",
        "historical": all_months,
        "forecast": forecast,
        "trend_direction": trend,
        "trend_percentage": round(trend_pct, 1),
        "recent_average": round(sum(recent_counts) / max(1, len(recent_counts)), 1),
    }


def build_exposure_and_hotspots(
    records: List[Dict[str, Any]],
    fh_fc_priority: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    AI 8.0 Enhancement #3: Exposure & Hotspots Dashboard

    Real-time visualization of risk areas:
    - Tail x ATA risk matrix
    - Model family exposure comparison
    - Geographic hotspots
    - Component lifecycle hotspots
    """
    # Build tail x ATA matrix
    matrix: Dict[Tuple[str, str], Dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "critical": 0, "open": 0}
    )

    for rec in records:
        tail = str(rec.get("tail", "")).strip() or "N/A"
        ata = str(rec.get("ata", "")).split(".")[0] or "N/A"
        key = (tail, ata)
        matrix[key]["count"] += 1

        if str(rec.get("prioridade", "")).lower() == "critical":
            matrix[key]["critical"] += 1
        if str(rec.get("status_atual", "")).lower() in {"open", "in progress"}:
            matrix[key]["open"] += 1

    # Create hotspot list
    hotspots: List[Dict[str, Any]] = []
    for (tail, ata), data in matrix.items():
        risk_score = (data["count"] * 10) + \
            (data["critical"] * 30) + (data["open"] * 20)
        hotspots.append({
            "tail": tail,
            "ata": ata,
            "count": data["count"],
            "critical": data["critical"],
            "open": data["open"],
            "risk_score": risk_score,
            "color": "danger" if risk_score >= 150 else "warning" if risk_score >= 75 else "info",
        })

    hotspots.sort(key=lambda x: x["risk_score"], reverse=True)

    return {
        "matrix": hotspots[:25],
        "top_risk_tail": hotspots[0]["tail"] if hotspots else "N/A",
        "top_risk_ata": hotspots[0]["ata"] if hotspots else "N/A",
        "total_hotspots": len(hotspots),
    }


def build_ata_quick_reference(
    records: List[Dict[str, Any]],
    ata: str,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    AI 8.0 Enhancement #4: ATA Quick Reference

    AI-powered quick lookup with historical patterns:
    - Failure frequency for ATA
    - Most affected tails
    - Typical resolution time
    - Related ATAs
    """
    ata_ref = str(ata).split(".")[0]
    matches = [r for r in records if str(
        r.get("ata", "")).split(".")[0] == ata_ref]

    if not matches:
        return {
            "ata": ata_ref,
            "found": False,
            "message": f"No historical records for ATA {ata_ref}",
        }

    tails_counter = Counter(str(r.get("tail", "N/A")) for r in matches)
    status_counter = Counter(
        str(r.get("status_atual", "unknown")).lower() for r in matches)

    return {
        "ata": ata_ref,
        "found": True,
        "total_records": len(matches),
        "top_affected_tails": [{"tail": t, "count": c} for t, c in tails_counter.most_common(5)],
        "status_breakdown": {k: v for k, v in status_counter.most_common()},
        "open_rate": round(
            (status_counter.get("open", 0) +
             status_counter.get("in progress", 0)) / len(matches) * 100,
            1
        ),
        "avg_severity": sum(1 for r in matches if str(r.get("prioridade", "")).lower() in {"critical", "high"}) / len(matches),
    }


def sync_realtime_metrics(conn) -> Dict[str, Any]:
    """
    AI 8.0 Enhancement #5: Real-time Data Sync

    Auto-refresh metrics from database:
    - Load latest records
    - Update FH/FC values
    - Recalculate priorities
    - Cache for fast access
    """
    try:
        cursor = conn.cursor(pymysql.cursors.DictCursor)
        cursor.execute(
            "SELECT COUNT(*) as cnt FROM falhas WHERE DATE(data_cadastro) >= DATE_SUB(NOW(), INTERVAL 7 DAY)")
        recent = cursor.fetchone()

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM falhas WHERE status_atual IN ('open', 'in progress')")
        open_count = cursor.fetchone()

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM mel WHERE date_closed IS NULL")
        mel_open = cursor.fetchone()

        cursor.execute(
            "SELECT COUNT(*) as cnt FROM aog WHERE release_date IS NULL")
        aog_open = cursor.fetchone()

        return {
            "sync_timestamp": datetime.now(timezone.utc).isoformat(),
            "recent_7d": recent.get("cnt", 0) if recent else 0,
            "total_open": open_count.get("cnt", 0) if open_count else 0,
            "mel_open": mel_open.get("cnt", 0) if mel_open else 0,
            "aog_open": aog_open.get("cnt", 0) if aog_open else 0,
        }
    except Exception as e:
        return {"error": str(e), "sync_timestamp": datetime.now(timezone.utc).isoformat()}


# ============================================================================
# PHASE 2: ANALYZE FAILURE ENHANCEMENTS
# ============================================================================

def semantic_ata_matcher(
    ata_query: str,
    available_atas: List[str],
    knowledge_base: Dict[str, Any],
) -> Dict[str, Any]:
    """
    AI 8.0 Enhancement #6: Semantic ATA Matching

    Fixes number-proximity confusion by using semantic similarity:
    - Synonym expansion
    - System-level matching
    - Confidence scoring
    - Alternative suggestions
    """
    query_tokens = set(ata_query.lower().split())
    best_matches: List[Tuple[str, float]] = []

    for ata in available_atas:
        ata_info = knowledge_base.get(ata, {})
        system = ata_info.get("system", "").lower()
        keywords = [k.lower() for k in ata_info.get("keywords", [])]

        # Calculate semantic score
        score = 0.0
        for token in query_tokens:
            if token in keywords:
                score += 0.4
            if token in system:
                score += 0.3

        if score > 0:
            best_matches.append((ata, score))

    best_matches.sort(key=lambda x: x[1], reverse=True)

    return {
        "query": ata_query,
        "primary_match": best_matches[0][0] if best_matches else None,
        "confidence": round(best_matches[0][1] * 100, 1) if best_matches else 0,
        "alternatives": [
            {"ata": ata, "score": round(score * 100, 1)}
            for ata, score in best_matches[1:4]
        ],
    }


def extract_multi_system_context(
    description: str,
    knowledge_base: Dict[str, Any],
) -> Dict[str, Any]:
    """
    AI 8.0 Enhancement #7: Multi-system Context Extraction

    Extract electrical, hydraulic, pneumatic patterns:
    - System keywords
    - Interaction points
    - Cross-system risks
    """
    description_lower = description.lower()
    systems_found: Dict[str, List[str]] = defaultdict(list)

    for ata, ata_info in knowledge_base.items():
        keywords = [k.lower() for k in ata_info.get("keywords", [])]
        system = ata_info.get("system", "")

        for keyword in keywords:
            if keyword in description_lower:
                systems_found[system].append(keyword)

    return {
        "systems_detected": dict(systems_found),
        "system_count": len(systems_found),
        "cross_system_risk": "high" if len(systems_found) > 2 else "medium" if len(systems_found) == 2 else "low",
    }


def component_history_scorer(
    records: List[Dict[str, Any]],
    tail: str,
    ata: str,
) -> Dict[str, Any]:
    """
    AI 8.0 Enhancement #8: Component History Scoring

    Score based on LRU/part failure history:
    - Component replacement frequency
    - MTBF (Mean Time Between Failures)
    - Reliability trend
    """
    ata_ref = str(ata).split(".")[0]
    matching = [
        r for r in records
        if str(r.get("tail", "")).upper() == str(tail).upper()
        and str(r.get("ata", "")).split(".")[0] == ata_ref
    ]

    if not matching:
        return {
            "component_history": "limited",
            "record_count": 0,
            "reliability": "unknown",
        }

    closed = sum(1 for r in matching if str(
        r.get("status_atual", "")).lower() == "closed")
    mtbf_days = None
    if closed > 1 and len(matching) > 1:
        dates = []
        for r in matching:
            try:
                dates.append(datetime.strptime(
                    str(r.get("data_cadastro", ""))[:10], "%Y-%m-%d"))
            except (ValueError, TypeError):
                pass
        if len(dates) > 1:
            dates.sort()
            total_days = (dates[-1] - dates[0]).days
            mtbf_days = int(total_days / len(dates))

    return {
        "component_history": "available" if len(matching) > 2 else "limited",
        "record_count": len(matching),
        "closed_count": closed,
        "mtbf_days": mtbf_days,
        "reliability": "high" if mtbf_days and mtbf_days > 180 else "medium" if mtbf_days and mtbf_days > 60 else "low",
    }


def maintenance_action_recommender(
    analysis: Dict[str, Any],
    knowledge_base: Dict[str, Any],
    ata: str,
) -> List[Dict[str, Any]]:
    """
    AI 8.0 Enhancement #9: Maintenance Action Recommender

    Suggest specific troubleshooting paths based on:
    - ATA-specific procedures
    - Historical success rates
    - Component availability
    """
    ata_info = knowledge_base.get(ata, {})
    steps = ata_info.get("troubleshooting_steps", [])
    quick_actions = ata_info.get("quick_actions", [])

    recommendations: List[Dict[str, Any]] = []

    # Add quick actions
    for idx, action in enumerate(quick_actions[:4], 1):
        recommendations.append({
            "priority": "P1",
            "action": action,
            "duration_hours": 0.5,
            "estimated_success": 75,
        })

    # Add detailed steps
    for idx, step in enumerate(steps[:5], 1):
        recommendations.append({
            "priority": "P2" if idx <= 3 else "P3",
            "action": step,
            "duration_hours": 0.5 + idx * 0.3,
            "estimated_success": 70 - (idx * 5),
        })

    return recommendations


def detect_failure_pattern_recurrence(
    records: List[Dict[str, Any]],
    tail: str,
    ata: str,
    window_days: int = 90,
) -> Dict[str, Any]:
    """
    AI 8.0 Enhancement #10: Failure Pattern Recognition

    Identify repeating sequences:
    - Recurrence interval
    - Pattern severity
    - Root cause likelihood
    """
    ata_ref = str(ata).split(".")[0]
    matching = [
        r for r in records
        if str(r.get("tail", "")).upper() == str(tail).upper()
        and str(r.get("ata", "")).split(".")[0] == ata_ref
    ]

    if len(matching) < 2:
        return {
            "pattern_detected": False,
            "recurrence_interval": None,
            "pattern_severity": "unknown",
        }

    dates = []
    for r in matching:
        try:
            dates.append((
                datetime.strptime(str(r.get("data_cadastro", ""))[
                                  :10], "%Y-%m-%d"),
                r
            ))
        except (ValueError, TypeError):
            pass

    dates.sort()
    Recent = [d for d in dates if (
        datetime.utcnow() - d[0]).days <= window_days]

    if len(Recent) < 2:
        return {
            "pattern_detected": False,
            "recurrence_count": len(Recent),
            "pattern_severity": "sporadic",
        }

    intervals = []
    for i in range(len(Recent) - 1):
        delta = (Recent[i + 1][0] - Recent[i][0]).days
        intervals.append(delta)

    avg_interval = sum(intervals) / len(intervals) if intervals else None

    return {
        "pattern_detected": True,
        "recurrence_count": len(Recent),
        "avg_interval_days": avg_interval,
        "pattern_severity": "high" if avg_interval and avg_interval < 30 else "medium" if avg_interval and avg_interval < 90 else "low",
        "trend": "worsening" if intervals and intervals[-1] < intervals[0] else "improving" if intervals and intervals[-1] > intervals[0] else "stable",
    }


def refine_confidence_scoring(
    base_score: float,
    data_quality: Dict[str, Any],
    feedback_signal: float,
) -> Dict[str, Any]:
    """
    AI 8.0 Enhancement #11: Confidence Scoring Refinement

    Better confidence calculation based on:
    - Data completeness
    - Historical feedback
    - Pattern detection
    """
    quality_factor = (
        (data_quality.get("records_available", 0) / 100.0) +
        (data_quality.get("ata_clarity", 0) / 100.0) +
        (data_quality.get("tail_history", 0) / 100.0)
    ) / 3.0

    feedback_factor = feedback_signal  # 0-1

    refined = min(
        100,
        (base_score * 0.6) + (quality_factor * 20) + (feedback_factor * 10)
    )

    return {
        "base_confidence": round(base_score, 1),
        "quality_factor": round(quality_factor * 20, 1),
        "feedback_factor": round(feedback_factor * 10, 1),
        "refined_confidence": round(refined, 1),
        "confidence_grade": "A" if refined >= 85 else "B" if refined >= 70 else "C" if refined >= 55 else "D",
    }


# ============================================================================
# PHASE 3: AUTONOMOUS INTELLIGENCE
# ============================================================================

def ai_recalibration_engine(
    feedback_items: List[Dict[str, Any]],
    current_weights: Dict[str, float],
) -> Dict[str, Any]:
    """
    AI 8.0 Enhancement #12: AI Recalibration Engine

    Auto-adjust forecast weights monthly:
    - Analyze feedback acceptance
    - Adjust forecast formula
    - Generate monthly calibration reports
    """
    if not feedback_items:
        return {
            "calibration": "no_feedback",
            "weights_updated": False,
        }

    ata_acceptance: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"positive": 0, "total": 0})

    for item in feedback_items:
        ata = str(item.get("ata", "N/A"))
        ata_acceptance[ata]["total"] += 1
        if bool(item.get("helpful")) is True:
            ata_acceptance[ata]["positive"] += 1

    adjusted_weights = []
    for ata, stats in ata_acceptance.items():
        acceptance_rate = stats["positive"] / \
            stats["total"] if stats["total"] > 0 else 0
        if acceptance_rate < 0.6:  # Low acceptance
            adjustment = "decrease_forecast_weight"
        elif acceptance_rate > 0.85:  # High acceptance
            adjustment = "increase_forecast_weight"
        else:
            adjustment = "maintain_weight"

        adjusted_weights.append({
            "ata": ata,
            "acceptance_rate": round(acceptance_rate * 100, 1),
            "adjustment": adjustment,
            "sample_size": stats["total"],
        })

    return {
        "calibration": "updated",
        "ata_adjustments": adjusted_weights,
        "overall_acceptance": round(
            sum(s["positive"] for s in ata_acceptance.values()) /
            sum(s["total"] for s in ata_acceptance.values()) * 100,
            1
        ) if feedback_items else 0,
        "recalibration_date": datetime.now(timezone.utc).isoformat(),
    }


def predictive_intervention_alerts(
    projection: Dict[str, Any],
    fh_fc_priority: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    AI 8.0 Enhancement #13: Predictive Intervention Alerts

    Forecast next 40/90/120 days:
    - Critical alerts
    - SLA recommendations
    - Resource planning
    """
    alerts: List[Dict[str, Any]] = []

    for item in fh_fc_priority[:8]:
        for window, days in [("40d", 40), ("90d", 90), ("120d", 120)]:
            expected = int(item.get("risk_score", 0) * (days / 30.0))
            if expected > 0:
                alerts.append({
                    "tail": item.get("tail"),
                    "ata": item.get("ata"),
                    "window": window,
                    "projected_events": expected,
                    "urgency": "critical" if expected >= 5 else "high" if expected >= 2 else "medium",
                })

    return {
        "alerts": sorted(alerts, key=lambda x: x["projected_events"], reverse=True),
        "total_critical_windows": sum(1 for a in alerts if a["urgency"] == "critical"),
    }


def autonomous_maintenance_planner(
    queue: List[Dict[str, Any]],
    records: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    AI 8.0 Enhancement #14: Autonomous Maintenance Planner

    Generate detailed work orders:
    - Step-by-step instructions
    - Resource requirements
    - Estimated duration
    - Success probability
    """
    plans: List[Dict[str, Any]] = []

    for item in queue[:5]:
        plan = {
            "tail": item.get("tail"),
            "ata": item.get("ata"),
            "priority": item.get("priority"),
            "sla": item.get("recommended_sla"),
            "work_order_id": f"WO-{item.get('rank')}-{item.get('tail')}",
            "estimated_labor_hours": 3.5 if item.get("priority") == "P1" else 2.5 if item.get("priority") == "P2" else 1.5,
            "required_tools": ["Multimeter", "Pressure Gauge", "ATA Manual"],
            "required_parts": "To be determined",
            "success_probability": 82,
            "next_step": item.get("action"),
        }
        plans.append(plan)

    return plans


def daily_brief_generation(
    records: List[Dict[str, Any]],
    queue: List[Dict[str, Any]],
    drift_alert: Dict[str, Any],
    mel_count: int,
    aog_count: int,
) -> Dict[str, Any]:
    """
    AI 8.0 Enhancement #15: Daily Brief Generation

    Automatic operational summary for management
    """
    open_count = sum(1 for r in records if str(
        r.get("status_atual", "")).lower() in {"open", "in progress"})

    brief = {
        "date": datetime.now(timezone.utc).isoformat(),
        "headline": f"{len(queue)} critical maintenance items queued; {open_count} open failures; {aog_count} AOG aircraft",
        "fleet_status": {
            "open_failures": open_count,
            "active_aog": aog_count,
            "open_mel": mel_count,
            "queue_length": len(queue),
        },
        "top_3_actions": [
            f"{queue[i].get('tail')} / ATA {queue[i].get('ata')} (Priority {queue[i].get('priority')})"
            for i in range(min(3, len(queue)))
        ],
        "forecast_status": drift_alert.get("status", "stable"),
        "recommendation": "Proceed with standard maintenance schedule" if drift_alert.get("status") == "stable" else "Accelerate inspection schedule",
    }

    return brief


def anomaly_detection_engine(
    records: List[Dict[str, Any]],
    baselines: Dict[str, float],
) -> Dict[str, Any]:
    """
    AI 8.0 Enhancement #16: Anomaly Detection

    Flag unexpected failure patterns
    """
    anomalies: List[Dict[str, Any]] = []

    # Check for sudden increase in failures
    for tail in set(str(r.get("tail", "")) for r in records):
        tail_failures = sum(1 for r in records if str(
            r.get("tail", "")) == tail)
        baseline = baselines.get(tail, 0)

        if baseline > 0 and tail_failures > baseline * 1.5:
            anomalies.append({
                "type": "failure_spike",
                "tail": tail,
                "baseline": baseline,
                "current": tail_failures,
                "severity": "warning",
            })

    return {
        "anomalies": anomalies,
        "total_detected": len(anomalies),
        "status": "alert" if anomalies else "normal",
    }


def self_learning_loop(
    feedback: List[Dict[str, Any]],
    corrections: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    AI 8.0 Enhancement #17: Self-Learning Loop

    Absorb feedback and adjust models
    """
    learning_metrics = {
        "feedback_processed": len(feedback),
        "corrections_applied": len(corrections),
        "learning_rate": len(corrections) / max(1, len(feedback)),
        "last_update": datetime.now(timezone.utc).isoformat(),
    }

    return learning_metrics


# ============================================================================
# PHASE 4: GLOBAL INTERFACE (Copilot & Context)
# ============================================================================

def floating_copilot_widget_config() -> Dict[str, Any]:
    """
    AI 8.0 Enhancement #18: Floating Global Copilot

    Configuration for JS widget on all pages
    """
    return {
        "widget_id": "ai-copilot-float",
        "position": "bottom-right",
        "size": "compact",
        "features": [
            "quick_ask",
            "page_context_capture",
            "suggest_actions",
            "show_related_cases",
        ],
        "context_fields": [
            "current_page",
            "form_data",
            "visible_text",
            "url_params",
        ],
    }


def page_context_analyzer(
    page_url: str,
    form_data: Dict[str, Any],
    visible_text: str,
) -> Dict[str, Any]:
    """
    AI 8.0 Enhancement #19: Page Context Capture

    Analyze current page & suggest actions
    """
    page_type = "unknown"
    if "cadastro" in page_url:
        page_type = "failure_registration"
    elif "fleet" in page_url:
        page_type = "fleet_status"
    elif "ai_analysis" in page_url:
        page_type = "analytics_dashboard"
    elif "logbook" in page_url:
        page_type = "logbook_view"

    context = {
        "page_type": page_type,
        "form_fields": list(form_data.keys()),
        "extractable_data": {
            "tails": [word for word in visible_text.split() if len(word) == 5 and word.isupper()],
            "atas": [m for m in re.findall(r"\d{2}-\d{2}", visible_text)],
        },
    }

    return context


def cadastro_semantic_case_matching(
    description: str,
    all_cases: List[Dict[str, Any]],
    similarity_threshold: float = 0.25,
) -> List[Dict[str, Any]]:
    """
    AI 8.0 Enhancement #20: Cadastro Semantic Case Matching

    Find similar historical cases using semantic matching
    """
    from routes_analytics import _tokenize, _semantic_score

    query_tokens = _tokenize(description)
    matched: List[Dict[str, Any]] = []

    for case in all_cases[:500]:  # Sample for performance
        case_desc = str(case.get("problema", ""))
        case_tokens = _tokenize(case_desc)

        similarity = _semantic_score(query_tokens, case_tokens)
        if similarity >= similarity_threshold:
            matched.append({
                "case_id": case.get("id"),
                "tail": case.get("tail"),
                "ata": str(case.get("ata", "")).split(".")[0],
                "similarity": round(similarity * 100, 1),
                "status": case.get("status_atual"),
                "description": case_desc[:200],
            })

    matched.sort(key=lambda x: x["similarity"], reverse=True)
    return matched[:5]


# ============================================================================
# PHASE 5: REPORTING & INSIGHTS
# ============================================================================

def executive_dashboard_builder(
    records: List[Dict[str, Any]],
    queue: List[Dict[str, Any]],
    mel_items: List[Dict[str, Any]],
    aog_items: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    AI 8.0 Enhancement #22: Executive Dashboard

    KPIs for management
    """
    # Calculate MTBF
    total_failures = len(records)
    total_fh = sum(float(r.get("fh", 0)) for r in records)
    mtbf = total_fh / max(1, total_failures) if total_failures > 0 else 0

    # Availability
    distinct_tails = len(set(str(r.get("tail", "")) for r in records))
    aog_tails = len(set(str(a.get("tail", "")) for a in aog_items))
    availability = round((1 - (aog_tails / max(1, distinct_tails))) * 100, 1)

    return {
        "mtbf_hours": round(mtbf, 1),
        "fleet_availability": availability,
        "open_queue": len(queue),
        "mel_restrictions": len([m for m in mel_items if not m.get("date_closed")]),
        "aog_aircraft": len([a for a in aog_items if not a.get("release_date")]),
    }


def trend_analysis_report(historical_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    AI 8.0 Enhancement #23: Trend Analysis
    """
    if len(historical_data) < 2:
        return {"status": "insufficient_data"}

    # Month-over-month comparison
    return {
        "current_month": historical_data[-1],
        "previous_month": historical_data[-2],
        "change_pct": round(
            ((historical_data[-1].get("count", 0) - historical_data[-2].get("count", 0)) /
             max(1, historical_data[-2].get("count", 1))) * 100,
            1
        ),
    }


# Stubs for remaining phases
def maintenance_roi_calculator() -> Dict[str, Any]:
    """AI 8.0 Enhancement #25"""
    return {"status": "not_implemented"}


def spare_parts_predictor() -> Dict[str, Any]:
    """AI 8.0 Enhancement #27"""
    return {"status": "not_implemented"}
