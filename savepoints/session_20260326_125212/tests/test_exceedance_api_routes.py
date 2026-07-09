from __future__ import annotations

import io
import json
from pathlib import Path

from flask import Flask

from routes_analytics import (
    _extract_event_timeline,
    _extract_rows_from_csv_bytes,
    analytics_bp,
)


def _build_test_app(tmp_path: Path) -> Flask:
    app = Flask(__name__, root_path=str(tmp_path))
    app.register_blueprint(analytics_bp)
    app.config.update(TESTING=True)

    (tmp_path / "tails_fallback.json").write_text(
        json.dumps([
            {"tail": "PR-E2A", "fh": 12000.0, "fc": 8000},
            {"tail": "PR-E1B", "fh": 9000.0, "fc": 6000},
        ]),
        encoding="utf-8",
    )
    return app


def _sample_open_records() -> list[dict]:
    return [
        {
            "id": 1001,
            "tail": "PR-E2A",
            "modelo": "E195-E2",
            "ata": "29",
            "status_atual": "Open",
            "problema": "Hydraulic pressure low after hard landing event",
            "troubleshooting": "Checked pump and pressure line. Hard landing report attached.",
        },
        {
            "id": 1002,
            "tail": "PR-E2A",
            "modelo": "E195-E2",
            "ata": "27",
            "status_atual": "In Progress",
            "problema": "Flap asymmetry caution after flap overspeed",
            "troubleshooting": "Inspected actuator and track rollers.",
        },
        {
            "id": 2000,
            "tail": "PR-E1B",
            "ata": "34",
            "status_atual": "Closed",
            "problema": "Closed navigation event",
            "troubleshooting": "No longer active.",
        },
    ]


def test_open_cases_endpoint_filters(monkeypatch, tmp_path: Path) -> None:
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=5000: _sample_open_records())

    client = app.test_client()
    response = client.get("/api/ai/exceedance/open_cases?tail=PR-E2A&ata=29")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["count"] == 1
    assert payload["cases"][0]["id"] == 1001


def test_exceedance_analyze_with_csv(monkeypatch, tmp_path: Path) -> None:
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=5000: _sample_open_records())
    monkeypatch.setattr(
        "routes_analytics._load_family_manual_context",
        lambda family, signals, max_chars=3000: {
            "family": family,
            "matched_sections": ["05-50-03"],
            "text_excerpt": "AMM hard landing inspection excerpt",
            "source_files": ["MPP21_05-50-03.PDF"],
        },
    )

    client = app.test_client()
    csv_content = (
        "timestamp,event,message\n"
        "2026-03-26T10:00:00Z,hard landing,Vertical acceleration exceedance\n"
        "2026-03-26T10:00:05Z,flap overspeed,VFE exceeded on approach\n"
    )

    data = {
        "failure_text": "Hydraulic fluctuations after hard landing",
        "scenario": "Approach unstable with touchdown G peak",
        "tail": "PR-E2A",
        "modelo": "E195-E2",
        "analysis_mode": "expert",
        "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "event_log.csv"),
    }
    response = client.post(
        "/api/ai/exceedance/analyze",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["priority"] in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
    assert isinstance(payload["data"]["signals"], list)
    assert "pdf_sections" in payload["data"]
    assert "playbooks" in payload["data"]
    assert "reconciliation" in payload["data"]
    assert "closure_readiness" in payload["data"]
    assert "causal_chain" in payload["data"]
    assert "severity_assessment" in payload["data"]
    assert payload["data"]["severity_assessment"]["level"] in {
        "CRITICAL", "HIGH", "MEDIUM", "LOW"}
    assert "priority_assessment" in payload["data"]
    assert payload["data"]["analysis_mode"] == "expert"
    assert "expert_view" in payload["data"]
    assert payload["data"]["mode_output"] == payload["data"]["expert_view"]
    assert "probable_cause" in payload["data"]
    assert payload["data"]["probable_cause"]["primary_cause"] in payload["data"]["signals"]
    assert "immediate_containment_actions" in payload["data"]
    assert isinstance(payload["data"]["immediate_containment_actions"], list)
    assert payload["data"]["immediate_containment_actions"]
    assert "action_support_evidence" in payload["data"]
    assert isinstance(payload["data"]["action_support_evidence"], list)
    assert payload["data"]["action_support_evidence"]
    assert "pdf_relevance" in payload["data"]
    assert "ata_decision_tree" in payload["data"]
    assert payload["data"]["ata_decision_tree"]["ata_family"] in {"29", "unknown"}
    assert "trend_window_analysis" in payload["data"]
    assert "trend" in payload["data"]["trend_window_analysis"]
    assert payload["data"]["family_context"]["family"] == "E2"
    assert payload["data"]["csv_schema_validation"]["valid"] is True
    assert payload["data"]["analysis_version"] == 1
    assert payload["data"]["version_comparison"]["has_previous"] is False
    assert "additional_inspections" in payload["data"]
    assert isinstance(payload["data"]["additional_inspections"], list)
    assert "structured_export" in payload["data"]
    assert payload["data"]["structured_export"]["analysis_mode"] == "expert"
    assert payload["data"]["reprocess_ready"] is True
    assert len(payload["data"]["stored_evidence"]) >= 1
    assert payload["data"]["audit_summary"]["files_logged"] >= 1
    assert payload["data"]["retention_policy"]["retention_days"] >= 1
    assert payload["inputs"]["csv_rows"] >= 1

    # exceedance_verdict must be in every analysis response
    assert "exceedance_verdict" in payload["data"]
    ev = payload["data"]["exceedance_verdict"]
    assert "verdict" in ev
    assert ev["verdict"] in {"YES", "NO", "UNDETERMINED"}
    assert isinstance(ev["triggered_rules"], list)
    assert isinstance(ev["parameter_peaks"], dict)
    assert isinstance(ev["amm_references"], list)
    assert "summary" in ev
    assert "family" in ev
    assert "evaluated_events" in ev
    assert isinstance(ev["evaluated_events"], list)
    assert "historical_exceedance_correlation" in payload["data"]
    hist = payload["data"]["historical_exceedance_correlation"]
    assert "same_tail_ata_count" in hist
    assert "top_matches" in hist
    assert isinstance(hist["top_matches"], list)
    assert "mandatory_review_trigger" in payload["data"]
    mrt = payload["data"]["mandatory_review_trigger"]
    assert "required" in mrt
    assert "reason_codes" in mrt
    assert isinstance(mrt["reason_codes"], list)

    # same key analyzed again should version-up and provide comparison payload
    data2 = {
        "failure_text": "Hydraulic fluctuations after hard landing",
        "scenario": "Approach unstable with touchdown G peak",
        "tail": "PR-E2A",
        "modelo": "E195-E2",
        "analysis_mode": "executive",
        "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "event_log.csv"),
    }
    response2 = client.post(
        "/api/ai/exceedance/analyze",
        data=data2,
        content_type="multipart/form-data",
    )
    assert response2.status_code == 200
    payload2 = response2.get_json()
    assert payload2["data"]["analysis_version"] == 2
    assert payload2["data"]["version_comparison"]["has_previous"] is True
    assert payload2["data"]["analysis_mode"] == "executive"
    assert payload2["data"]["mode_output"] == payload2["data"]["executive_view"]
    assert "diagnosis_change_alert" in payload2["data"]
    assert "mandatory_review_trigger" in payload2["data"]
    assert payload2["data"]["mandatory_review_trigger"]["required"] is True


def test_exceedance_reprocess_uses_stored_evidence(monkeypatch, tmp_path: Path) -> None:
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=5000: _sample_open_records())
    monkeypatch.setattr(
        "routes_analytics._load_family_manual_context",
        lambda family, signals, max_chars=3000: {
            "family": family,
            "matched_sections": [],
            "text_excerpt": "",
            "source_files": [],
        },
    )

    client = app.test_client()
    csv_content = (
        "timestamp,event,message\n"
        "2026-03-26T10:00:00Z,hard landing,Vertical acceleration exceedance\n"
    )
    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Hydraulic fluctuations after hard landing",
            "scenario": "Approach unstable with touchdown G peak",
            "tail": "PR-E2A",
            "modelo": "E195-E2",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "event_log.csv"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    analysis_key = response.get_json()["data"]["analysis_key"]

    response2 = client.post(
        "/api/ai/exceedance/reprocess",
        data={"analysis_key": analysis_key, "analysis_mode": "executive"},
        content_type="multipart/form-data",
    )
    assert response2.status_code == 200
    payload2 = response2.get_json()
    assert payload2["success"] is True
    assert payload2["reprocessed_from"] == analysis_key
    assert payload2["loaded_stored_files"] >= 1
    assert payload2["data"]["analysis_version"] == 2
    assert payload2["data"]["analysis_mode"] == "executive"


def test_exceedance_analyze_open_case(monkeypatch, tmp_path: Path) -> None:
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=5000: _sample_open_records())
    monkeypatch.setattr(
        "routes_analytics._load_family_manual_context",
        lambda family, signals, max_chars=3000: {
            "family": family,
            "matched_sections": [],
            "text_excerpt": "",
            "source_files": [],
        },
    )

    client = app.test_client()
    response = client.post(
        "/api/ai/exceedance/analyze_open_case",
        data={"case_id": "1001", "analysis_mode": "executive"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["case"]["id"] == 1001
    assert "recommended_actions" in payload["data"]
    assert "closure_readiness" in payload["data"]
    assert "severity_estimate" in payload["data"]
    assert "ata_decision_tree" in payload["data"]
    assert "trend_window_analysis" in payload["data"]
    assert "probable_cause" in payload["data"]
    assert "additional_inspections" in payload["data"]
    assert payload["data"]["analysis_mode"] == "executive"
    assert "structured_export" in payload["data"]
    assert payload["data"]["family_context"]["family"] == "E2"


def test_exceedance_analyze_open_case_not_found(monkeypatch, tmp_path: Path) -> None:
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=5000: _sample_open_records())

    client = app.test_client()
    response = client.post(
        "/api/ai/exceedance/analyze_open_case",
        data={"case_id": "999999"},
        content_type="multipart/form-data",
    )
    assert response.status_code == 404
    payload = response.get_json()
    assert payload["success"] is False


def test_exceedance_playbooks_and_reconciliation(monkeypatch, tmp_path: Path) -> None:
    """Playbooks are returned per signal; reconciliation detects CSV-only vs PDF-only."""
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=5000: _sample_open_records())

    client = app.test_client()
    # CSV says hard landing; PDF text says flap overspeed only — expect a conflict
    csv_content = (
        "timestamp,event\n"
        "2026-03-26T09:00:00Z,Hard landing — vertical g 2.6\n"
    )
    pdf_like_text = "Flap overspeed noted during approach. VFE exceeded."
    data = {
        "failure_text": "Dual exceedance event reported by crew",
        "scenario": pdf_like_text,
        "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "acms_log.csv"),
    }
    response = client.post(
        "/api/ai/exceedance/analyze",
        data=data,
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    d = payload["data"]
    # Playbooks should exist for every detected signal
    assert isinstance(d["playbooks"], dict)
    for sig in d["signals"]:
        assert sig in d["playbooks"], f"Missing playbook for signal: {sig}"
        assert len(d["playbooks"][sig]) > 0
    # Reconciliation structure present
    assert "reconciliation" in d
    assert "has_conflict" in d["reconciliation"]
    assert isinstance(d["reconciliation"]["conflict_notes"], list)


def test_csv_normalization_and_temporal_sorting() -> None:
    csv_content = (
        "Date Time,Event Name,Alert Message,Vertical Accel G,Flap Pos\n"
        "2026-03-26 10:00:05,Hard landing,Vertical acceleration exceedance,2.1,0\n"
        "2026-03-26 10:00:01,Flap overspeed,VFE exceeded,1.0,5\n"
    )
    rows = _extract_rows_from_csv_bytes(csv_content.encode("utf-8"))
    assert len(rows) == 2
    assert "timestamp" in rows[0]
    assert "event" in rows[0]
    assert "message" in rows[0]
    assert "vertical_acceleration_g" in rows[0]
    assert "flap_position" in rows[0]
    timeline = _extract_event_timeline(rows)
    assert timeline[0]["time"] == "2026-03-26 10:00:01"
    assert timeline[1]["time"] == "2026-03-26 10:00:05"


def test_exceedance_verdict_yes_with_hard_landing_numerical_csv(
    monkeypatch, tmp_path: Path
) -> None:
    """CSV with Nz peak of 2.35 G on E170 family (g_high=2.10) must yield verdict=YES."""
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=5000: _sample_open_records())
    monkeypatch.setattr(
        "routes_analytics._load_family_manual_context",
        lambda family, signals, max_chars=3000: {
            "family": family,
            "matched_sections": [],
            "text_excerpt": "",
            "source_files": [],
        },
    )

    # nz_g is a recognised alias for normal_accel in the rules engine
    # E175 modelo → E170 family → g_high = 2.10 G
    # Peak 2.35 G exceeds threshold → verdict MUST be YES
    csv_content = (
        "nz_g,ias\n"
        "1.05,210.0\n"
        "1.80,215.0\n"
        "2.35,218.0\n"  # hard landing peak – above E170 g_high=2.10
        "1.10,220.0\n"
    )
    response = app.test_client().post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Hard landing reported by crew",
            "scenario": "Heavy touchdown on runway 27L",
            "tail": "PR-E75",
            "modelo": "E175",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "fdr.csv"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    ev = payload["data"]["exceedance_verdict"]
    assert ev["verdict"] == "YES", (
        f"Expected YES but got {ev['verdict']!r}. Summary: {ev.get('summary')!r}"
    )
    assert ev["family"] == "E170"
    assert len(ev["triggered_rules"]) >= 1
    # Verify at least one rule flags hard_landing
    events = {r["event"] for r in ev["triggered_rules"]}
    assert "hard_landing" in events, f"hard_landing not in triggered events: {events}"
    # Parameter peaks must include normal_accel
    assert "normal_accel" in ev["parameter_peaks"]
    assert ev["parameter_peaks"]["normal_accel"] == 2.35


def test_exceedance_verdict_no_with_safe_numerical_csv(
    monkeypatch, tmp_path: Path
) -> None:
    """CSV with Nz well below all E170 hard-landing thresholds must yield verdict=NO."""
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=5000: _sample_open_records())
    monkeypatch.setattr(
        "routes_analytics._load_family_manual_context",
        lambda family, signals, max_chars=3000: {
            "family": family,
            "matched_sections": [],
            "text_excerpt": "",
            "source_files": [],
        },
    )

    # E175 → E170 family → g_low=1.80, all values below 1.50 → verdict NO
    csv_content = (
        "nz_g,ias\n"
        "1.05,210.0\n"
        "1.20,215.0\n"
        "1.50,218.0\n"  # well below E170 g_low=1.80
        "1.10,210.0\n"
    )
    response = app.test_client().post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Routine landing check",
            "scenario": "Normal approach and touchdown",
            "tail": "PR-E75",
            "modelo": "E175",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "fdr.csv"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    ev = payload["data"]["exceedance_verdict"]
    assert ev["verdict"] == "NO", (
        f"Expected NO but got {ev['verdict']!r}. Summary: {ev.get('summary')!r}"
    )
    assert ev["family"] == "E170"
    assert ev["triggered_rules"] == []
