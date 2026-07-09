"""
Exceedance Rules Engine
-----------------------
Self-contained, deterministic threshold-based evaluation of flight-data CSV rows.
Produces a clear YES / NO / UNDETERMINED verdict for each candidate exceedance event
based on official Mexicana AMM / AFM limits for the E145, E170, E1 and E2 families.

Design principles
-----------------
- Pure Python, no external dependencies (no pandas, no numpy required)
- Works with the List[Dict[str, str]] rows already produced by routes_analytics.py
- Source limits are extracted from D:\\Projetos\\excedencias (AMM-compliant)
- All threshold constants are documented with their AMM/AFM reference

Typical usage inside routes_analytics.py
------------------------------------------
    from exceedance_rules_engine import evaluate_exceedance_verdict

    verdict = evaluate_exceedance_verdict(
        csv_rows=csv_rows,          # List[Dict[str, str]]
        signals=signals,            # List[str] from _detect_exceedance_signals()
        tail=tail_hint,             # aircraft registration / tail number
        modelo=modelo_hint,         # model string e.g. "E190", "E175-E2"
        family=aircraft_family,     # optional override: "E1"|"E2"|"E145"|"E170"|""
    )
    result["exceedance_verdict"] = verdict
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Section 1 – AMM / AFM Threshold Tables
# ---------------------------------------------------------------------------
# Source: D:\Projetos\excedencias
#   src/services/hard_landing_analyzer.py  (VERT_ACCEL_THRESHOLDS, ROLL_RATE, PITCH_RATE)
#   src/services/over_g_analyzer.py        (OVER_G_THRESHOLDS)
#   src/services/vmo_analyzer.py           (VMO_THRESHOLDS)
#   src/services/all_families_specs.py     (per-model speed, weight, temp limits)
#   src/services/rules_engine.py           (RULES dict – fallback static limits)

# Each family entry has event-type sub-dicts with float limits and an AMM ref string.
# Convention: positive thresholds are maximums; negative thresholds are minimums.

_THRESHOLDS: Dict[str, Dict[str, Any]] = {

    # ── E145 Family (ERJ-135/140/145) ────────────────────────────────────────
    "E145": {
        "hard_landing": {
            # AMM 05-50-02 Table 4-1   (from VERT_ACCEL_THRESHOLDS_E145)
            "g_low":    2.30,   # G  – Inspection required (normal takeoff weight range)
            "g_high":   2.40,   # G  – Extensive inspection
            "descent_low_fpm":   600,   # ft/min
            "descent_high_fpm": 1000,   # ft/min
            "ref": "AMM 05-50-02 Table 4-1",
        },
        "over_g": {
            # AMM 05-50-02
            "positive": 3.5,
            "negative": -3.5,
            "moderate": 3.2,
            "ref": "AMM 05-50-02",
        },
        "vmo_mmo": {
            # AFM Section 5
            "vmo": 280,         # KIAS
            "mmo": 0.78,        # Mach
            "inspection_vmo": 290,
            "inspection_mmo": 0.80,
            "ref": "AFM Section 5 – E145",
        },
        "flap_overspeed": {
            "flap_1": 200, "flap_2": 180, "flap_3": 170, "flap_full": 145,
            "ref": "AFM Limitations – E145",
        },
        "gear_overspeed": {
            "vle": 230,
            "vlo_extend": 230,
            "vlo_retract": 200,
            "ref": "AFM Section 5 – E145",
        },
        "overweight_landing": {
            "mlw_lbs": 44000,
            "ref": "AMM 05-50-02 – E145",
        },
        "turbulence": {
            "positive": 2.2,
            "negative": -0.8,
            "ref": "AMM 05-50-02 – E145",
        },
        "high_bank_angle": {
            "normal": 60.0,
            "emergency": 67.0,
            "ref": "AMM 05-50-02 – E145",
        },
        "temperature": {
            "tat_max": 54.0,
            "tat_min": -54.0,
            "ref": "AMM 71-00-00 – E145",
        },
    },

    # ── E170 Family (E170 / E175) ─────────────────────────────────────────────
    "E170": {
        "hard_landing": {
            # AMM 05-50-03-200-801-A Rev 121  (PDF 801 – Figure 607)
            # Threshold at mid-range landing weight (~36 000 kg)
            "g_low":    1.80,   # G  – Inspection required (low level)
            "g_high":   2.10,   # G  – Inspection required (high level / roll/pitch check)
            "g_engine": 2.40,   # G  – Engine inspection required
            "descent_low_fpm":  600,
            "descent_high_fpm": 900,
            "roll_rate_low_dps":  10.0,   # deg/s
            "roll_rate_high_dps": 16.0,
            "pitch_rate_low_dps": -5.5,   # deg/s  (negative = nose-down)
            "pitch_rate_high_dps": -6.1,
            "ref": "AMM 05-50-03-200-801-A Rev 121 (PDF 801)",
        },
        "over_g": {
            "positive": 3.5, "negative": -3.5,
            "moderate": 3.2, "high": 3.3,
            "ref": "AMM 05-50-02 – E170/E175",
        },
        "vmo_mmo": {
            "vmo": 320, "mmo": 0.82,
            "inspection_vmo": 330, "inspection_mmo": 0.84,
            "ref": "AFM Section 5 – E170/E175",
        },
        "flap_overspeed": {
            "flap_1": 250, "flap_2": 230, "flap_3": 210, "flap_full": 180,
            "ref": "AFM Limitations – E170/E175",
        },
        "gear_overspeed": {
            "vle": 250, "vlo_extend": 250, "vlo_retract": 220,
            "ref": "AFM Section 5 – E170/E175",
        },
        "overweight_landing": {
            "mlw_lbs": 69224,
            "ref": "AMM 05-50-02 – E170/E175",
        },
        "turbulence": {
            "positive": 2.5, "negative": -1.0,
            "ref": "AMM 05-50-02 – E170/E175",
        },
        "high_bank_angle": {
            "normal": 60.0, "emergency": 67.0,
            "ref": "AMM 05-50-02 – E170/E175",
        },
        "temperature": {
            "tat_max": 54.0, "tat_min": -54.0,
            "ref": "AMM 71-00-00 – E170/E175",
        },
    },

    # ── E1 Family (E190 / E195) ───────────────────────────────────────────────
    "E1": {
        "hard_landing": {
            # AMM 05-50-03-200-804-A  (PDF 804 – E190/E195)
            "g_low":    2.00,
            "g_high":   2.60,
            "g_very_hard": 2.80,
            "descent_low_fpm":  600,
            "descent_high_fpm": 900,
            "pitch_rate_low_dps": -6.0,
            "pitch_rate_high_dps": -6.6,
            "ref": "AMM 05-50-03-200-804-A (PDF 804)",
        },
        "over_g": {
            "positive": 3.5, "negative": -3.5,
            "moderate": 3.2, "high": 3.3,
            "ref": "AMM 05-50-02 – E190/E195",
        },
        "vmo_mmo": {
            "vmo": 320, "mmo": 0.82,
            "inspection_vmo": 330, "inspection_mmo": 0.84,
            "ref": "AFM Section 5 – E190/E195",
        },
        "flap_overspeed": {
            "flap_1": 250, "flap_2": 230, "flap_3": 210, "flap_full": 180,
            "ref": "AFM Limitations – E190/E195",
        },
        "gear_overspeed": {
            "vle": 260, "vlo_extend": 260, "vlo_retract": 230,
            "ref": "AFM Section 5 – E190/E195",
        },
        "overweight_landing": {
            "mlw_lbs": 108247,
            "ref": "AMM 05-50-02 – E190/E195",
        },
        "turbulence": {
            "positive": 2.5, "negative": -1.0,
            "ref": "AMM 05-50-02 – E190/E195",
        },
        "high_bank_angle": {
            "normal": 60.0, "emergency": 67.0,
            "ref": "AMM 05-50-02 – E190/E195",
        },
        "temperature": {
            "tat_max": 54.0, "tat_min": -54.0,
            "ref": "AMM 71-00-00 – E190/E195",
        },
    },

    # ── E2 Family (E175-E2 / E190-E2 / E195-E2) ─────────────────────────────
    "E2": {
        "hard_landing": {
            "g_low":    1.78,
            "g_high":   2.10,
            "g_engine": 2.40,
            "descent_low_fpm":  600,
            "descent_high_fpm": 900,
            "ref": "AMM 05-50-03-200-804-A (E2 variant)",
        },
        "over_g": {
            # E2 has higher envelope per AMM 05-50-02
            "positive": 3.8, "negative": -3.8,
            "moderate": 3.5, "high": 3.6,
            "ref": "AMM 05-50-02 – E175-E2/E190-E2/E195-E2",
        },
        "vmo_mmo": {
            "vmo": 340, "mmo": 0.85,
            "inspection_vmo": 350, "inspection_mmo": 0.87,
            "ref": "AFM Section 5 – E175-E2/E190-E2/E195-E2",
        },
        "flap_overspeed": {
            "flap_1": 260, "flap_2": 240, "flap_3": 220, "flap_full": 190,
            "ref": "AFM Limitations – E2 family",
        },
        "gear_overspeed": {
            "vle": 260, "vlo_extend": 260, "vlo_retract": 230,
            "ref": "AFM Section 5 – E2 family",
        },
        "overweight_landing": {
            "mlw_lbs": 110674,
            "ref": "AMM 05-50-02 – E2 family",
        },
        "turbulence": {
            "positive": 2.5, "negative": -1.0,
            "ref": "AMM 05-50-02 – E2 family",
        },
        "high_bank_angle": {
            "normal": 60.0, "emergency": 67.0,
            "ref": "AMM 05-50-02 – E2 family",
        },
        "temperature": {
            "tat_max": 54.0, "tat_min": -54.0,
            "ref": "AMM 71-00-00 – E2 family",
        },
    },
}

# Default when family cannot be determined
_THRESHOLDS[""] = _THRESHOLDS["E1"]

# ---------------------------------------------------------------------------
# Section 2 – Family detection helpers
# ---------------------------------------------------------------------------

_FAMILY_PATTERNS: Dict[str, List[str]] = {
    "E2":   ["e190-e2", "e195-e2", "e175-e2", "e190e2", "e195e2", "e175e2", "-e2"],
    "E145": ["erj145", "erj-145", "e145", "e135", "e140"],
    "E170": ["e170", "e175", "emb170", "emb175", "erj170", "erj175"],
    "E1":   ["emb190", "emb195", "emb-190", "emb-195", "e190", "e195"],
}


def _resolve_family(tail: str = "", modelo: str = "", family: str = "") -> str:
    """Return the best-matching aircraft family key for threshold lookups."""
    if family and family in _THRESHOLDS:
        return family
    combined = (tail + " " + modelo).lower().strip()
    for fam in ("E2", "E145", "E170", "E1"):
        for pat in _FAMILY_PATTERNS[fam]:
            if pat in combined:
                return fam
    return ""  # unknown → fallback to E1 defaults via _THRESHOLDS[""]


# ---------------------------------------------------------------------------
# Section 3 – Flexible CSV column mapping
# ---------------------------------------------------------------------------
# Source: D:\Projetos\excedencias\src\services\csv_column_mapper.py  (adapted)

_COLUMN_ALIASES: Dict[str, List[str]] = {
    "normal_accel": [
        "normal_accel", "norm_accel", "normal acceleration", "vert_g",
        "vertical_g", "nz", "nz_g", "g_load", "g_force", "g-force",
        "accel_z", "az", "vertical acceleration", "accel vertical",
        "aceleracao vertical", "normal_acceleration", "normalaccel",
        "accel_normal", "load_factor", "load factor", "n_z", "nz1",
        "accelerometer", "a_z", "acc_z", "vert accel", "vertical g",
        "g vert", "g_vertical", "accel_lat_norm", "gz", "gz_g",
        "Long Accel", "long_accel",
    ],
    "roll_rate": [
        "roll_rate", "rollrate", "roll rate", "p", "roll_rate_deg",
        "phi_dot", "roll rate (deg/s)", "roll_rate_degs",
        "roll angular rate", "rollrate_dps",
    ],
    "pitch_rate": [
        "pitch_rate", "pitchrate", "pitch rate", "q", "pitch_rate_deg",
        "theta_dot", "pitch rate (deg/s)", "q_degs", "pitchrate_dps",
    ],
    "airspeed": [
        "airspeed", "air speed", "speed", "ias", "kias",
        "indicated_airspeed", "indicated airspeed", "cas",
        "calibrated_airspeed", "airspeed (kts)", "ias_kts",
        "velocidade", "vel", "ias [knots]", "airspeed_kt",
        "indicated airspeed (kts)", "air_speed", "spd", "ias kt",
        "airspeed (calibrated; 1 or only) (knots)", "spd_kts",
    ],
    "mach": [
        "mach", "mach_number", "mach number", "mach no", "mach_no",
        "mach_speed", "mach_num", "m",
    ],
    "bank_angle": [
        "bank_angle", "phi", "roll_angle", "bank angle", "roll angle",
        "bank", "phi_deg", "bank_angle_deg", "bank (deg)", "roll (deg)",
        "roll attitude",
    ],
    "flap_position": [
        "flap_position", "flap", "flaps", "flap_pos", "flap position",
        "flaps_position", "flap_lever", "flap_angle", "flap angle",
        "flap_deflection", "flap deg", "flap (deg)", "slat_position",
    ],
    "gear_position": [
        "gear_position", "gear", "ldg_gear", "gear pos", "gear position",
        "landing_gear", "gear_status", "gear_down", "gear_down_flag",
        "lg_down", "lgdown",
    ],
    "weight": [
        "weight", "gross_weight", "gw", "aircraft_weight", "gross weight",
        "weight_lbs", "weight_kg", "mass", "a/c weight", "acft weight",
        "acwt", "gw_lbs", "gw_kg", "aircraft weight",
    ],
    "oat": [
        "oat", "tat", "temperature", "outside_air_temp", "oat_c", "tat_c",
        "total_air_temp", "ambient_temp", "temp air", "temp_air",
        "temperature (c)", "oat (c)", "tat (c)",
    ],
    "vertical_speed": [
        "vertical_speed", "vs", "vspd", "rate_of_descent", "vert_speed",
        "sink_rate", "rate of descent", "sink rate", "descent_rate",
        "fpm", "vrate", "vertical speed (fpm)", "vertical vel",
        "vertical_velocity", "vert vel", "vert_vel", "vertical_rate",
        "roc", "rate_of_climb",
    ],
    "altitude": [
        "altitude", "alt", "height", "pressure_altitude", "baro_alt",
        "altitude_ft", "alt_ft", "altitude_msl", "altitude (ft)",
        "alt (ft)", "baro altitude", "pressure alt",
    ],
}


def _try_float(v: Any) -> Optional[float]:
    """Convert value to float; return None on failure or non-finite."""
    try:
        f = float(str(v).replace(",", ".").strip())
        return f if math.isfinite(f) else None
    except (ValueError, TypeError):
        return None


def _resolve_col(headers: List[str], param: str) -> Optional[str]:
    """Find the first column header that matches any known alias for *param*."""
    aliases = _COLUMN_ALIASES.get(param, [])
    lc_map: Dict[str, str] = {h.strip().lower(): h for h in headers}
    for alias in aliases:
        alias_lc = alias.lower()
        if alias_lc in lc_map:
            return lc_map[alias_lc]
    # Partial / substring fallback
    for alias in aliases:
        alias_lc = alias.lower()
        for lc, original in lc_map.items():
            if alias_lc in lc or lc in alias_lc:
                return original
    return None


def _extract_values(csv_rows: List[Dict[str, str]], param: str) -> Tuple[List[float], Optional[str]]:
    """
    Extract all finite numeric values for *param* from csv_rows.
    Returns (values_list, resolved_column_name_or_None).
    """
    if not csv_rows:
        return [], None
    headers = list(csv_rows[0].keys())
    col = _resolve_col(headers, param)
    if col is None:
        return [], None
    vals: List[float] = []
    for row in csv_rows:
        v = _try_float(row.get(col))
        if v is not None:
            vals.append(v)
    return vals, col


# ---------------------------------------------------------------------------
# Section 4 – Individual event evaluators
# ---------------------------------------------------------------------------

_SEVERITY_MAP = {
    "CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1, "NONE": 0,
}


def _make_rule(event: str, verdict: str, parameter: str, peak: float,
               limit: float, unit: str, ref: str, family: str,
               severity: str, note: str = "") -> Dict[str, Any]:
    return {
        "event": event,
        "verdict": verdict,            # "YES" | "NO" | "UNDETERMINED"
        "parameter": parameter,
        "peak_value": round(peak, 4),
        "limit": round(limit, 4),
        "unit": unit,
        "exceedance_margin": round(abs(peak - limit), 4) if verdict == "YES" else 0.0,
        "ref": ref,
        "family": family,
        "severity": severity,
        "note": note,
    }


def _eval_hard_landing(
    csv_rows: List[Dict[str, str]], thresholds: Dict[str, Any], family: str,
    signals: List[str],
) -> List[Dict[str, Any]]:
    rules: List[Dict[str, Any]] = []
    t = thresholds.get("hard_landing", {})
    if not t:
        return rules

    # ── Normal acceleration check ────────────────────────────────────────
    g_vals, g_col = _extract_values(csv_rows, "normal_accel")
    if g_vals:
        peak_g = max(g_vals)
        g_engine = t.get("g_engine", t.get("g_very_hard", t.get("g_high", 99)))
        g_high = t.get("g_high", 99)
        g_low = t.get("g_low", 99)

        if peak_g >= g_engine:
            sev = "CRITICAL"
            rules.append(_make_rule(
                "hard_landing", "YES", g_col or "normal_accel", peak_g,
                g_engine, "G", t["ref"], family, sev,
                "Engine / extensive structural inspection required",
            ))
        elif peak_g >= g_high:
            rules.append(_make_rule(
                "hard_landing", "YES", g_col or "normal_accel", peak_g,
                g_high, "G", t["ref"], family, "HIGH",
                "Hard landing inspection required (high level)",
            ))
        elif peak_g >= g_low:
            rules.append(_make_rule(
                "hard_landing", "YES", g_col or "normal_accel", peak_g,
                g_low, "G", t["ref"], family, "MEDIUM",
                "Hard landing inspection required (low level)",
            ))
        else:
            rules.append(_make_rule(
                "hard_landing", "NO", g_col or "normal_accel", peak_g,
                g_low, "G", t["ref"], family, "NONE",
                f"Peak {peak_g:.3f}G is within normal limit {g_low:.3f}G",
            ))

    # ── Descent rate check ────────────────────────────────────────────────
    vs_vals, vs_col = _extract_values(csv_rows, "vertical_speed")
    if vs_vals:
        # Most negative value (fastest descent)
        min_vs = min(vs_vals)
        # Normalise sign: FDR records can be negative or positive FPM
        descent = abs(min_vs) if min_vs < 0 else min_vs
        high_fpm = t.get("descent_high_fpm", 1000)
        low_fpm = t.get("descent_low_fpm", 600)
        if descent >= high_fpm:
            rules.append(_make_rule(
                "hard_landing", "YES", vs_col or "vertical_speed", descent,
                high_fpm, "ft/min", t["ref"], family, "HIGH",
                "Descent rate exceeded high threshold",
            ))
        elif descent >= low_fpm:
            rules.append(_make_rule(
                "hard_landing", "YES", vs_col or "vertical_speed", descent,
                low_fpm, "ft/min", t["ref"], family, "MEDIUM",
                "Descent rate exceeded low threshold",
            ))

    # ── Roll rate check (E170 / E2 families) ─────────────────────────────
    rr_low = t.get("roll_rate_low_dps")
    if rr_low is not None:
        rr_vals, rr_col = _extract_values(csv_rows, "roll_rate")
        if rr_vals:
            peak_rr = max(abs(v) for v in rr_vals)
            rr_high = t.get("roll_rate_high_dps", rr_low * 1.6)
            if peak_rr >= rr_high:
                rules.append(_make_rule(
                    "hard_landing", "YES", rr_col or "roll_rate", peak_rr,
                    rr_high, "deg/s", t["ref"], family, "HIGH",
                    "Roll rate exceeded high threshold at landing",
                ))
            elif peak_rr >= rr_low:
                rules.append(_make_rule(
                    "hard_landing", "YES", rr_col or "roll_rate", peak_rr,
                    rr_low, "deg/s", t["ref"], family, "MEDIUM",
                    "Roll rate exceeded low threshold at landing",
                ))

    # ── Pitch rate check ─────────────────────────────────────────────────
    pr_low = t.get("pitch_rate_low_dps")
    if pr_low is not None:
        pr_vals, pr_col = _extract_values(csv_rows, "pitch_rate")
        if pr_vals:
            min_pr = min(pr_vals)   # Most nose-down (negative)
            pr_high = t.get("pitch_rate_high_dps", pr_low * 1.1)
            if min_pr <= pr_high:
                rules.append(_make_rule(
                    "hard_landing", "YES", pr_col or "pitch_rate", min_pr,
                    pr_high, "deg/s", t["ref"], family, "HIGH",
                    "Pitch rate exceeded high threshold at landing",
                ))
            elif min_pr <= pr_low:
                rules.append(_make_rule(
                    "hard_landing", "YES", pr_col or "pitch_rate", min_pr,
                    pr_low, "deg/s", t["ref"], family, "MEDIUM",
                    "Pitch rate exceeded low threshold at landing",
                ))

    return rules


def _eval_over_g(
    csv_rows: List[Dict[str, str]], thresholds: Dict[str, Any], family: str,
) -> List[Dict[str, Any]]:
    rules: List[Dict[str, Any]] = []
    t = thresholds.get("over_g", {})
    if not t:
        return rules

    g_vals, g_col = _extract_values(csv_rows, "normal_accel")
    if not g_vals:
        return rules

    peak_pos = max(g_vals)
    peak_neg = min(g_vals)
    pos_limit = t["positive"]
    neg_limit = t["negative"]
    moderate = t.get("moderate", pos_limit * 0.9)

    if peak_pos >= pos_limit:
        sev = "CRITICAL" if peak_pos >= pos_limit * 1.05 else "HIGH"
        rules.append(_make_rule(
            "over_g", "YES", g_col or "normal_accel", peak_pos,
            pos_limit, "G", t["ref"], family, sev,
            "Positive Over-G exceedance",
        ))
    elif peak_pos >= moderate:
        rules.append(_make_rule(
            "over_g", "YES", g_col or "normal_accel", peak_pos,
            moderate, "G", t["ref"], family, "MEDIUM",
            "Positive G approaching Over-G limit",
        ))
    else:
        rules.append(_make_rule(
            "over_g", "NO", g_col or "normal_accel", peak_pos,
            pos_limit, "G", t["ref"], family, "NONE",
            f"Max +{peak_pos:.3f}G within limit +{pos_limit:.3f}G",
        ))

    if peak_neg <= neg_limit:
        rules.append(_make_rule(
            "over_g", "YES", g_col or "normal_accel", peak_neg,
            neg_limit, "G", t["ref"], family, "HIGH",
            "Negative Over-G exceedance",
        ))

    return rules


def _eval_vmo_mmo(
    csv_rows: List[Dict[str, str]], thresholds: Dict[str, Any], family: str,
) -> List[Dict[str, Any]]:
    rules: List[Dict[str, Any]] = []
    t = thresholds.get("vmo_mmo", {})
    if not t:
        return rules

    # IAS / VMO
    ias_vals, ias_col = _extract_values(csv_rows, "airspeed")
    if ias_vals:
        peak_ias = max(ias_vals)
        insp_vmo = t.get("inspection_vmo", t["vmo"] + 10)
        if peak_ias >= insp_vmo:
            rules.append(_make_rule(
                "vmo_overspeed", "YES", ias_col or "airspeed", peak_ias,
                insp_vmo, "KIAS", t["ref"], family, "CRITICAL",
                "Airspeed exceeded VMO inspection threshold (VMO+10)",
            ))
        elif peak_ias >= t["vmo"]:
            rules.append(_make_rule(
                "vmo_overspeed", "YES", ias_col or "airspeed", peak_ias,
                t["vmo"], "KIAS", t["ref"], family, "HIGH",
                f"Airspeed exceeded VMO ({t['vmo']} KIAS)",
            ))
        else:
            rules.append(_make_rule(
                "vmo_overspeed", "NO", ias_col or "airspeed", peak_ias,
                t["vmo"], "KIAS", t["ref"], family, "NONE",
                f"Peak IAS {peak_ias:.1f} KIAS within VMO {t['vmo']} KIAS",
            ))

    # Mach / MMO
    mach_vals, mach_col = _extract_values(csv_rows, "mach")
    if mach_vals:
        peak_mach = max(mach_vals)
        insp_mmo = t.get("inspection_mmo", t["mmo"] + 0.02)
        if peak_mach >= insp_mmo:
            rules.append(_make_rule(
                "mmo_overspeed", "YES", mach_col or "mach", peak_mach,
                insp_mmo, "Mach", t["ref"], family, "CRITICAL",
                "Mach exceeded MMO inspection threshold",
            ))
        elif peak_mach >= t["mmo"]:
            rules.append(_make_rule(
                "mmo_overspeed", "YES", mach_col or "mach", peak_mach,
                t["mmo"], "Mach", t["ref"], family, "HIGH",
                f"Mach exceeded MMO ({t['mmo']})",
            ))

    return rules


def _eval_flap_overspeed(
    csv_rows: List[Dict[str, str]], thresholds: Dict[str, Any], family: str,
) -> List[Dict[str, Any]]:
    rules: List[Dict[str, Any]] = []
    t = thresholds.get("flap_overspeed", {})
    if not t:
        return rules

    ias_vals, ias_col = _extract_values(csv_rows, "airspeed")
    flap_vals, flap_col = _extract_values(csv_rows, "flap_position")

    if not ias_vals:
        return rules

    # If we have flap position data, evaluate row-by-row
    if flap_vals and flap_col:
        row_pairs: List[Tuple[float, float]] = []
        ias_col_resolved = _resolve_col(list(csv_rows[0].keys()), "airspeed")
        flap_col_resolved = flap_col
        for row in csv_rows:
            ias_v = _try_float(row.get(ias_col_resolved or ""))
            flap_v = _try_float(row.get(flap_col_resolved or ""))
            if ias_v is not None and flap_v is not None:
                row_pairs.append((ias_v, flap_v))

        violations: List[Tuple[float, float, float]] = []  # (ias, flap, limit)
        for ias_v, flap_v in row_pairs:
            limit = _flap_speed_limit(flap_v, t)
            if limit is not None and ias_v > limit:
                violations.append((ias_v, flap_v, limit))

        if violations:
            worst = max(violations, key=lambda x: x[0] - x[2])
            rules.append(_make_rule(
                "flap_overspeed", "YES",
                f"{ias_col or 'airspeed'} @ {flap_col}",
                worst[0], worst[2], "KIAS", t["ref"], family, "HIGH",
                f"Exceeded VFE with flap ~{worst[1]:.0f}° deployed",
            ))
        else:
            # All pairs OK
            rules.append(_make_rule(
                "flap_overspeed", "NO", ias_col or "airspeed",
                max(ias_vals), t.get("flap_1", 999), "KIAS",
                t["ref"], family, "NONE",
                "No VFE exceedance detected with available flap/speed data",
            ))
    else:
        # Flap position unavailable — check IAS vs most conservative VFE
        peak_ias = max(ias_vals)
        vfe_min = min(v for k, v in t.items() if k != "ref" and isinstance(v, (int, float)))
        if peak_ias > vfe_min:
            rules.append(_make_rule(
                "flap_overspeed", "UNDETERMINED", ias_col or "airspeed",
                peak_ias, vfe_min, "KIAS", t["ref"], family, "LOW",
                "Flap position column not found; high IAS may indicate VFE exceedance",
            ))

    return rules


def _flap_speed_limit(flap_deg: float, t: Dict[str, Any]) -> Optional[float]:
    """Return VFE limit for the given flap deflection angle."""
    if flap_deg <= 0:
        return None  # Flaps up — no VFE applies
    if flap_deg <= 1:
        return t.get("flap_1")
    if flap_deg <= 2:
        return t.get("flap_2")
    if flap_deg <= 3:
        return t.get("flap_3")
    return t.get("flap_full")


def _eval_gear_overspeed(
    csv_rows: List[Dict[str, str]], thresholds: Dict[str, Any], family: str,
) -> List[Dict[str, Any]]:
    rules: List[Dict[str, Any]] = []
    t = thresholds.get("gear_overspeed", {})
    if not t:
        return rules

    ias_vals, ias_col = _extract_values(csv_rows, "airspeed")
    gear_vals, gear_col = _extract_values(csv_rows, "gear_position")

    if not ias_vals:
        return rules

    vle = t["vle"]

    if gear_vals and gear_col:
        ias_col_r = _resolve_col(list(csv_rows[0].keys()), "airspeed")
        gear_col_r = gear_col
        violations: List[float] = []
        for row in csv_rows:
            ias_v = _try_float(row.get(ias_col_r or ""))
            gear_v = _try_float(row.get(gear_col_r or ""))
            # Gear down = value > 0.5 (flag) or keyword "down"
            str_gear = str(row.get(gear_col_r or "", "")).lower()
            gear_down = (gear_v is not None and gear_v > 0.5) or "down" in str_gear
            if ias_v is not None and gear_down and ias_v > vle:
                violations.append(ias_v)

        if violations:
            rules.append(_make_rule(
                "gear_overspeed", "YES", ias_col or "airspeed",
                max(violations), vle, "KIAS", t["ref"], family, "HIGH",
                "VLE exceeded with landing gear down",
            ))
        else:
            rules.append(_make_rule(
                "gear_overspeed", "NO", ias_col or "airspeed",
                max(ias_vals), vle, "KIAS", t["ref"], family, "NONE",
                "No VLE exceedance detected with gear-down / speed data",
            ))
    else:
        peak_ias = max(ias_vals)
        if peak_ias > vle:
            rules.append(_make_rule(
                "gear_overspeed", "UNDETERMINED", ias_col or "airspeed",
                peak_ias, vle, "KIAS", t["ref"], family, "LOW",
                "Gear position column not found; high IAS may be above VLE",
            ))

    return rules


def _eval_turbulence(
    csv_rows: List[Dict[str, str]], thresholds: Dict[str, Any], family: str,
) -> List[Dict[str, Any]]:
    """
    Turbulence check — only evaluate G values at altitude (not during landing roll).
    Landing is characterised by radio altitude < ~50 ft or very low groundspeed.
    Without altitude column we still evaluate, but note the limitation.
    """
    rules: List[Dict[str, Any]] = []
    t = thresholds.get("turbulence", {})
    if not t:
        return rules

    g_vals, g_col = _extract_values(csv_rows, "normal_accel")
    alt_vals, alt_col = _extract_values(csv_rows, "altitude")

    if not g_vals:
        return rules

    # Filter to airborne rows when altitude data is available
    if alt_vals and alt_col and len(alt_vals) == len(csv_rows):
        alt_col_r = _resolve_col(list(csv_rows[0].keys()), "altitude")
        g_col_r = _resolve_col(list(csv_rows[0].keys()), "normal_accel")
        airborne_g: List[float] = []
        for row in csv_rows:
            alt_v = _try_float(row.get(alt_col_r or ""))
            g_v = _try_float(row.get(g_col_r or ""))
            if alt_v is not None and g_v is not None and alt_v > 400:
                airborne_g.append(g_v)
        eval_g = airborne_g if airborne_g else g_vals
        altitude_note = " (airborne phase only)"
    else:
        eval_g = g_vals
        altitude_note = " (altitude column not found – whole flight evaluated)"

    pos_limit = t["positive"]
    neg_limit = t["negative"]
    peak_pos = max(eval_g) if eval_g else 0.0
    peak_neg = min(eval_g) if eval_g else 0.0

    if peak_pos >= pos_limit:
        rules.append(_make_rule(
            "turbulence_exceedance", "YES", g_col or "normal_accel",
            peak_pos, pos_limit, "G", t["ref"], family, "HIGH",
            f"Turbulence: positive G exceeded{altitude_note}",
        ))
    if peak_neg <= neg_limit:
        rules.append(_make_rule(
            "turbulence_exceedance", "YES", g_col or "normal_accel",
            peak_neg, neg_limit, "G", t["ref"], family, "HIGH",
            f"Turbulence: negative G exceeded{altitude_note}",
        ))
    if not rules:
        rules.append(_make_rule(
            "turbulence_exceedance", "NO", g_col or "normal_accel",
            peak_pos, pos_limit, "G", t["ref"], family, "NONE",
            f"Peak G {peak_pos:.3f}G within turbulence limit{altitude_note}",
        ))

    return rules


def _eval_overweight_landing(
    csv_rows: List[Dict[str, str]], thresholds: Dict[str, Any], family: str,
) -> List[Dict[str, Any]]:
    rules: List[Dict[str, Any]] = []
    t = thresholds.get("overweight_landing", {})
    if not t:
        return rules

    weight_vals, weight_col = _extract_values(csv_rows, "weight")
    if not weight_vals:
        return rules

    mlw = t["mlw_lbs"]
    # CSV values can be lbs or kg — use an implicit check:
    # If values are below 10 000 it is likely kg, convert to lbs
    sample_max = max(weight_vals)
    if sample_max < 10_000:
        weight_vals = [w * 2.20462 for w in weight_vals]
    peak_w = max(weight_vals)

    if peak_w > mlw:
        rules.append(_make_rule(
            "overweight_landing", "YES", weight_col or "weight",
            peak_w, mlw, "lbs", t["ref"], family, "HIGH",
            f"Aircraft weight {peak_w:,.0f} lbs exceeded MLW {mlw:,.0f} lbs",
        ))
    else:
        rules.append(_make_rule(
            "overweight_landing", "NO", weight_col or "weight",
            peak_w, mlw, "lbs", t["ref"], family, "NONE",
            f"Landing weight {peak_w:,.0f} lbs within MLW {mlw:,.0f} lbs",
        ))

    return rules


def _eval_high_bank_angle(
    csv_rows: List[Dict[str, str]], thresholds: Dict[str, Any], family: str,
) -> List[Dict[str, Any]]:
    rules: List[Dict[str, Any]] = []
    t = thresholds.get("high_bank_angle", {})
    if not t:
        return rules

    bank_vals, bank_col = _extract_values(csv_rows, "bank_angle")
    if not bank_vals:
        return rules

    peak_bank = max(abs(v) for v in bank_vals)
    emerg = t["emergency"]
    normal = t["normal"]

    if peak_bank >= emerg:
        rules.append(_make_rule(
            "high_bank_angle", "YES", bank_col or "bank_angle",
            peak_bank, emerg, "deg", t["ref"], family, "CRITICAL",
            "Bank angle exceeded emergency limit",
        ))
    elif peak_bank >= normal:
        rules.append(_make_rule(
            "high_bank_angle", "YES", bank_col or "bank_angle",
            peak_bank, normal, "deg", t["ref"], family, "HIGH",
            "Bank angle exceeded normal operating limit",
        ))
    else:
        rules.append(_make_rule(
            "high_bank_angle", "NO", bank_col or "bank_angle",
            peak_bank, normal, "deg", t["ref"], family, "NONE",
            f"Max bank {peak_bank:.1f}° within limit {normal}°",
        ))

    return rules


def _eval_temperature(
    csv_rows: List[Dict[str, str]], thresholds: Dict[str, Any], family: str,
) -> List[Dict[str, Any]]:
    rules: List[Dict[str, Any]] = []
    t = thresholds.get("temperature", {})
    if not t:
        return rules

    temp_vals, temp_col = _extract_values(csv_rows, "oat")
    if not temp_vals:
        return rules

    peak_high = max(temp_vals)
    peak_low = min(temp_vals)
    tat_max = t["tat_max"]
    tat_min = t["tat_min"]

    if peak_high >= tat_max:
        rules.append(_make_rule(
            "temperature_envelope", "YES", temp_col or "oat",
            peak_high, tat_max, "°C", t["ref"], family, "HIGH",
            "TAT/OAT exceeded maximum temperature envelope",
        ))
    if peak_low <= tat_min:
        rules.append(_make_rule(
            "temperature_envelope", "YES", temp_col or "oat",
            peak_low, tat_min, "°C", t["ref"], family, "HIGH",
            "TAT/OAT exceeded minimum temperature envelope",
        ))
    if not rules:
        rules.append(_make_rule(
            "temperature_envelope", "NO", temp_col or "oat",
            peak_high, tat_max, "°C", t["ref"], family, "NONE",
            f"Temperature {peak_high:.1f}°C within envelope [{tat_min}, {tat_max}]°C",
        ))

    return rules


# ---------------------------------------------------------------------------
# Section 5 – Signal-to-event mapping
# ---------------------------------------------------------------------------

# Maps keywords returned by _detect_exceedance_signals() to evaluator functions.
# If a signal is detected in text but the evaluator finds no numeric data,
# the event is flagged as UNDETERMINED rather than NO.

_SIGNAL_TO_EVENTS: Dict[str, List[str]] = {
    "hard landing":           ["hard_landing"],
    "over-g":                 ["over_g"],
    "flap overspeed":         ["flap_overspeed"],
    "vmo overspeed":          ["vmo_overspeed"],
    "landing overspeed":      ["vmo_overspeed"],
    "gear overspeed":         ["gear_overspeed"],
    "turbulence exceedance":  ["turbulence_exceedance"],
    "weight exceedance":      ["overweight_landing"],
    "high bank angle":        ["high_bank_angle"],
    "temperature envelope":   ["temperature_envelope"],
}

# Map event names to their evaluator functions
_EVALUATORS = {
    "hard_landing":         _eval_hard_landing,
    "over_g":               _eval_over_g,
    "vmo_mmo":              _eval_vmo_mmo,
    "flap_overspeed":       _eval_flap_overspeed,
    "gear_overspeed":       _eval_gear_overspeed,
    "turbulence_exceedance": _eval_turbulence,
    "overweight_landing":   _eval_overweight_landing,
    "high_bank_angle":      _eval_high_bank_angle,
    "temperature_envelope": _eval_temperature,
}

# Default set of events to always evaluate when signals are absent
_DEFAULT_EVENTS = ["hard_landing", "over_g", "vmo_mmo"]


# ---------------------------------------------------------------------------
# Section 6 – Public API
# ---------------------------------------------------------------------------

def evaluate_exceedance_verdict(
    csv_rows: List[Dict[str, str]],
    signals: Optional[List[str]] = None,
    tail: str = "",
    modelo: str = "",
    family: str = "",
) -> Dict[str, Any]:
    """
    Evaluate flight-data CSV rows against AMM/AFM thresholds and return
    a definitive exceedance verdict.

    Parameters
    ----------
    csv_rows : list of dict
        Normalised CSV rows produced by _extract_rows_from_csv_bytes().
    signals : list of str, optional
        Event signals already detected by _detect_exceedance_signals().
    tail : str
        Aircraft tail number / registration (used for family detection).
    modelo : str
        Aircraft model string (used for family detection).
    family : str
        Optional explicit family override ("E1"|"E2"|"E145"|"E170").

    Returns
    -------
    dict with keys:
        verdict : "YES" | "NO" | "UNDETERMINED"
        family  : detected family string
        triggered_rules : list of rule dicts for events that triggered
        evaluated_events : list of all event names evaluated
        parameter_peaks : dict of detected parameter → peak value
        evaluated_parameters : list of CSV columns found and their peaks
        summary : human-readable summary string
        amm_references : list of unique AMM/AFM references cited
    """
    signals = signals or []
    resolved_family = _resolve_family(tail, modelo, family)
    thresholds = _THRESHOLDS.get(resolved_family, _THRESHOLDS[""])

    # Determine which event types to evaluate
    events_to_check: List[str] = list(_DEFAULT_EVENTS)
    for sig in signals:
        for ev in _SIGNAL_TO_EVENTS.get(sig.lower(), []):
            if ev not in events_to_check:
                events_to_check.append(ev)
    # Always evaluate all below when any CSV data is present
    if csv_rows:
        for ev in _EVALUATORS:
            if ev not in events_to_check:
                events_to_check.append(ev)

    all_rules: List[Dict[str, Any]] = []
    evaluated_events: List[str] = []

    for event_name in events_to_check:
        evaluator = _EVALUATORS.get(event_name)
        if evaluator is None:
            continue
        evaluated_events.append(event_name)
        if event_name in ("hard_landing",):
            rules = evaluator(csv_rows, thresholds, resolved_family, signals)
        else:
            rules = evaluator(csv_rows, thresholds, resolved_family)
        all_rules.extend(rules)

    # ── Collect parameter peaks ────────────────────────────────────────────
    param_peaks: Dict[str, float] = {}
    for param in _COLUMN_ALIASES:
        vals, _ = _extract_values(csv_rows, param)
        if vals:
            if param in ("normal_accel", "bank_angle", "roll_rate"):
                peak = max(abs(v) for v in vals)
            elif param in ("pitch_rate", "vertical_speed"):
                peak = min(vals)
            else:
                peak = max(vals)
            param_peaks[param] = round(peak, 4)

    # ── Aggregate verdict ─────────────────────────────────────────────────
    yes_rules = [r for r in all_rules if r["verdict"] == "YES"]
    undet_rules = [r for r in all_rules if r["verdict"] == "UNDETERMINED"]

    if not csv_rows:
        overall_verdict = "UNDETERMINED"
        summary = (
            "No CSV flight data provided. "
            "Upload FDR/ACMS data to enable threshold-based evaluation."
        )
    elif not param_peaks:
        overall_verdict = "UNDETERMINED"
        summary = (
            "CSV data present but no recognisable flight-parameter columns found. "
            "Check column headers against standard names (nz, ias, alt, vspd, …)."
        )
    elif yes_rules:
        overall_verdict = "YES"
        events_triggered = sorted({r["event"] for r in yes_rules})
        summary = (
            f"EXCEEDANCE CONFIRMED — {len(yes_rules)} threshold violation(s) detected "
            f"for: {', '.join(events_triggered)}. "
            f"Aircraft family: {resolved_family or 'unknown (E1 limits applied)'}."
        )
    elif undet_rules and not [r for r in all_rules if r["verdict"] == "NO"]:
        overall_verdict = "UNDETERMINED"
        summary = (
            "Relevant signal(s) detected but required flight-parameter columns "
            "were not found in the CSV. Include NZ, IAS, Mach, roll/pitch rate "
            "and altitude columns for a definitive verdict."
        )
    else:
        overall_verdict = "NO"
        summary = (
            f"No threshold violation detected across {len(evaluated_events)} event types. "
            f"All evaluated parameters are within AMM/AFM limits for {resolved_family or 'default'} family."
        )

    amm_refs = sorted({r["ref"] for r in all_rules if r.get("ref")})

    return {
        "verdict": overall_verdict,
        "family": resolved_family or "unknown",
        "triggered_rules": yes_rules,
        "all_rules": all_rules,
        "evaluated_events": evaluated_events,
        "parameter_peaks": param_peaks,
        "evaluated_parameters": [
            {"parameter": p, "peak": v} for p, v in param_peaks.items()
        ],
        "summary": summary,
        "amm_references": amm_refs,
        "signals_used": signals,
        "rows_evaluated": len(csv_rows),
    }

