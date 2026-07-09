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
    app = Flask(
        __name__,
        root_path=str(tmp_path),
        template_folder=str(Path(__file__).resolve().parents[1] / "Templates"),
    )

    @app.route("/login")
    def login() -> str:
        return "login"

    @app.route("/menu")
    def menu() -> str:
        return "menu"

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
    assert payload["data"]["ata_decision_tree"]["ata_family"] in {
        "29", "unknown"}
    assert "trend_window_analysis" in payload["data"]
    assert "trend" in payload["data"]["trend_window_analysis"]
    assert "document_summary" in payload["data"]
    assert "key_sections" in payload["data"]["document_summary"]
    assert isinstance(
        payload["data"]["document_summary"]["key_sections"], list)
    assert "extracted_constraints" in payload["data"]
    assert isinstance(
        payload["data"]["extracted_constraints"]["constraints"], list)
    assert "procedure_comparison" in payload["data"]
    assert "comparison_score" in payload["data"]["procedure_comparison"]
    assert "procedure_incompatibility_alert" in payload["data"]
    assert "incompatible" in payload["data"]["procedure_incompatibility_alert"]
    assert "input_quality_evaluation" in payload["data"]
    assert "quality_score" in payload["data"]["input_quality_evaluation"]
    assert "recommendations" in payload["data"]["input_quality_evaluation"]
    assert "validation_status" in payload["data"]["counterfactual_analysis"]
    assert "corrective_action_impact" in payload["data"]
    assert "baseline_risk_score" in payload["data"]["corrective_action_impact"]
    assert "action_dependency_plan" in payload["data"]
    assert "interdependencies" in payload["data"]["action_dependency_plan"]
    assert "conflicts" in payload["data"]["action_dependency_plan"]
    assert "ordered_actions" in payload["data"]["action_dependency_plan"]
    assert "min_execution_window_hours" in payload["data"]["action_dependency_plan"]
    assert payload["data"]["family_context"]["family"] == "E2"
    assert payload["data"]["csv_schema_validation"]["valid"] is True
    assert payload["data"]["analysis_version"] == 1
    assert payload["data"]["version_comparison"]["has_previous"] is False
    assert "additional_inspections" in payload["data"]
    assert isinstance(payload["data"]["additional_inspections"], list)
    assert "structured_export" in payload["data"]
    assert payload["data"]["structured_export"]["analysis_mode"] == "expert"
    assert "manual_compliance" in payload["data"]["structured_export"]
    assert "input_quality" in payload["data"]["structured_export"]
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
    assert "investigation_workspace" in payload["data"]
    assert payload["data"]["investigation_workspace"]["status"] == "open"
    assert payload["data"]["investigation_workspace"]["locked"] is False
    assert "learning_metrics_snapshot" in payload["data"]
    assert "post_validation_precision" in payload["data"]["learning_metrics_snapshot"]
    assert "effectiveness_index" in payload["data"]["learning_metrics_snapshot"]
    assert "exceedance_suite" in payload["data"]
    assert "touchdown_assessment" in payload["data"]
    assert "graphics_panel" in payload["data"]
    suite = payload["data"]["exceedance_suite"]
    assert suite["family"] == "E2"
    assert suite["total_events"] >= 1
    assert isinstance(suite["event_summaries"], list)
    assert isinstance(suite["critical_findings"], list)
    assert isinstance(suite["warnings"], list)

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
    assert "counterfactual_analysis" in payload2["data"]
    assert "corrective_action_impact" in payload2["data"]
    assert "action_dependency_plan" in payload2["data"]


def test_exceedance_touchdown_assessment_infers_right_main_gear(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=5000: _sample_open_records())
    monkeypatch.setattr(
        "routes_analytics._load_family_manual_context",
        lambda family, signals, max_chars=3000: {
            "family": family,
            "matched_sections": ["05-50-03"],
            "text_excerpt": "AMM touchdown zone excerpt",
            "source_files": ["MPP8725_05-50-03-06-1-200-801-A.PDF"],
            "manual_refs": {"gear_location": "E2 hard landing assessment"},
            "touchdown_mapping": {"roll_positive": "MLG RH", "roll_negative": "MLG LH"},
            "inspection_zones": ["MLG RH", "MLG LH", "NLG", "BOTH MLG"],
        },
    )

    client = app.test_client()
    csv_content = (
        "timestamp,vertical_acceleration_g,mlg_rh_wow,mlg_lh_wow,nlg_wow,roll_rate\n"
        "2026-03-26T10:00:00Z,2.45,1,0,0,2.8\n"
    )
    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Hard landing with right main gear first contact",
            "scenario": "Crew reported asymmetric touchdown",
            "tail": "PR-E2A",
            "modelo": "E195-E2",
            "family": "E2",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "touchdown.csv"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    touchdown = payload["data"]["touchdown_assessment"]
    assert touchdown["primary_zone"] == "MLG RH"
    assert touchdown["confidence"] in {"high", "medium"}
    assert "graphics_panel" in payload["data"]


def test_exceedance_touchdown_assessment_falls_back_to_roll_rate(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=5000: _sample_open_records())
    monkeypatch.setattr(
        "routes_analytics._load_family_manual_context",
        lambda family, signals, max_chars=3000: {
            "family": family,
            "matched_sections": ["05-50-03"],
            "text_excerpt": "AMM touchdown zone excerpt",
            "source_files": ["MPP8725_05-50-03-06-1-200-801-A.PDF"],
        },
    )

    client = app.test_client()
    csv_content = (
        "timestamp,vertical_acceleration_g,roll_rate,vertical_speed\n"
        "2026-03-26T10:00:00Z,1.10,0.1,-120\n"
        "2026-03-26T10:00:02Z,2.48,2.9,-780\n"
    )
    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Hard landing with asymmetric touchdown",
            "scenario": "No WOW discrete available in this recorder export",
            "tail": "PR-E2A",
            "modelo": "E195-E2",
            "family": "E2",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "touchdown_roll_only.csv"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    touchdown = payload["data"]["touchdown_assessment"]
    assert touchdown["primary_zone"] == "MLG RH"
    assert touchdown["confidence"] in {"medium", "low"}
    assert any("roll rate" in item.lower() for item in touchdown["evidence"])


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
    assert "investigation_workspace" in payload2["data"]


def test_extract_rows_from_csv_bytes_maps_external_headers() -> None:
    csv_content = (
        "UTC,Vertical Acceleration (G),Airspeed (Calibrated; 1 or only) (knots),"
        "Roll Rate (deg/s),Pitch Rate (deg/s),Landing Gear Position\n"
        "2026-03-26T10:00:00Z,2.62,182,1.5,-0.4,DOWN\n"
    )

    rows = _extract_rows_from_csv_bytes(csv_content.encode("utf-8"))

    assert len(rows) == 1
    assert rows[0]["timestamp"] == "2026-03-26T10:00:00Z"
    assert rows[0]["vertical_acceleration_g"] == "2.62"
    assert rows[0]["ias"] == "182"
    assert rows[0]["gear_position"] == "DOWN"


def test_extract_rows_from_csv_bytes_maps_acms_headers_from_real_files() -> None:
    csv_content = (
        "Time,IAS_C (knot),IVV_C (ft/min),GW_C (kg),ACCVERT,AhrsBodyPitchRate1a (Deg/Se),AhrsBodyRollRate1a (Deg/Se),FdrAccelNormal1a (G's)\n"
        "2026-03-26 10:00:00,182,-780,40256,2.53,-7.2,0.9,2.53\n"
    )

    rows = _extract_rows_from_csv_bytes(csv_content.encode("utf-8"))

    assert len(rows) == 1
    assert rows[0]["ias"] == "182"
    assert rows[0]["vertical_speed"] == "-780"
    assert rows[0]["gross_weight"] == "40256"
    assert rows[0]["vertical_acceleration_g"] == "2.53"
    assert rows[0]["pitch_rate"] == "-7.2"
    assert rows[0]["roll_rate"] == "0.9"


def test_extract_rows_from_csv_bytes_accepts_semicolon_delimiter() -> None:
    csv_content = (
        "Time;IAS_C (knot);IVV_C (ft/min);ACCVERT;FdrAccelNormal1a (G's)\n"
        "2026-03-26 10:00:00;182;-780;2.53;2.53\n"
    )

    rows = _extract_rows_from_csv_bytes(csv_content.encode("utf-8"))

    assert len(rows) == 1
    assert rows[0]["timestamp"] == "2026-03-26 10:00:00"
    assert rows[0]["ias"] == "182"
    assert rows[0]["vertical_speed"] == "-780"
    assert rows[0]["vertical_acceleration_g"] == "2.53"


def test_extract_rows_from_csv_bytes_skips_unit_only_row_from_real_exports() -> None:
    csv_content = (
        "Recorder Time,Date Time,Gross Weight - Kg,Vertical Acceleration,Roll Rate,Pitch Rate,Vertical Speed\n"
        ",,kg,g,deg/sec,deg/sec,ft/min\n"
        "0,2/20/2025 9:46,40256,2.41,0.4,-6.2,-780\n"
    )

    rows = _extract_rows_from_csv_bytes(csv_content.encode("utf-8"))

    assert len(rows) == 1
    assert rows[0]["gross_weight"] == "40256"
    assert rows[0]["vertical_acceleration_g"] == "2.41"
    assert rows[0]["roll_rate"] == "0.4"
    assert rows[0]["pitch_rate"] == "-6.2"
    assert rows[0]["vertical_speed"] == "-780"


def test_exceedance_analyze_detects_hard_landing_with_acms_headers(monkeypatch, tmp_path: Path) -> None:
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
        "Time,IAS_C (knot),IVV_C (ft/min),GW_C (kg),ACCVERT,AhrsBodyPitchRate1a (Deg/Se),AhrsBodyRollRate1a (Deg/Se),FdrAccelNormal1a (G's)\n"
        "2026-03-26 10:00:00,182,-780,40256,2.53,-7.2,0.9,2.53\n"
    )

    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Hard landing reported by crew",
            "scenario": "Touchdown with high vertical acceleration",
            "tail": "PR-E1B",
            "modelo": "E190",
            "family": "E1",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "acms_event.csv"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    verdict = payload["data"]["exceedance_verdict"]
    assert verdict["verdict"] == "YES"
    assert payload["data"]["aircraft_family_used"] == "E1"


def test_exceedance_analyze_detects_late_e1_peak_beyond_first_400_rows(monkeypatch, tmp_path: Path) -> None:
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

    lines = ["timestamp,vertical_acceleration_g"]
    for index in range(450):
        value = "1.00"
        if index == 449:
            value = "2.55"
        lines.append(f"2026-03-26T10:00:{index % 60:02d}Z,{value}")
    csv_content = "\n".join(lines)

    response = app.test_client().post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Hard landing reported by crew",
            "scenario": "Peak vertical acceleration happened late in the file",
            "tail": "PR-E1B",
            "modelo": "E190",
            "family": "E1",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "late_peak.csv"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    verdict = payload["data"]["exceedance_verdict"]
    assert payload["inputs"]["csv_rows"] >= 450
    assert verdict["verdict"] == "YES"
    assert verdict["family"] == "E1"


def test_exceedance_graphics_panel_includes_e195e2_envelope_assessment(monkeypatch, tmp_path: Path) -> None:
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=5000: _sample_open_records())
    monkeypatch.setattr(
        "routes_analytics._load_family_manual_context",
        lambda family, signals, max_chars=3000: {
            "family": family,
            "matched_sections": ["05-50-03"],
            "text_excerpt": "AMM E195-E2 envelope excerpt",
            "source_files": ["MPP8725_05-50-03-06-1-200-801-A.PDF"],
        },
    )

    client = app.test_client()
    csv_content = (
        "Time,GW_C (kg),FdrAccelNormal1a (G's),AhrsBodyRollRate1a (Deg/Se),maingearwow2\n"
        "2026-03-26 10:00:00,40000,1.20,0.8,0\n"
        "2026-03-26 10:00:01,40000,2.70,3.0,1\n"
    )

    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Potential E195-E2 hard landing envelope exceedance",
            "scenario": "Touchdown roll rate and gross weight available in ACMS export",
            "tail": "PR-E2A",
            "modelo": "E195-E2",
            "family": "E2",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "e195e2_envelope.csv"),
        },
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    payload = response.get_json()
    envelope = payload["data"]["graphics_panel"]["e2_hard_landing_envelope"]
    assert envelope["available"] is True
    assert envelope["model"] == "E195-E2"
    assert envelope["roll_band"] == "2.5 < ROLL RATE < 7.5"
    assert envelope["verdict"] == "EXCEEDED"
    assert abs(float(envelope["threshold_g"]) - 2.65) < 0.02


def test_exceedance_page_alias_route(tmp_path: Path) -> None:
    app = _build_test_app(tmp_path)
    client = app.test_client()

    response = client.get("/exceedance_analys")

    assert response.status_code == 200
    assert b"Analyze Exceedance" in response.data


def test_exceedance_investigation_workflow(monkeypatch, tmp_path: Path) -> None:
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
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Hydraulic fluctuations after hard landing",
            "scenario": "Approach unstable with touchdown G peak",
            "tail": "PR-E2A",
            "modelo": "E195-E2",
            "csv_files": (io.BytesIO(b"timestamp,event,message\n2026-03-26T10:00:00Z,hard landing,Vertical acceleration exceedance\n"), "event_log.csv"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    analysis_key = response.get_json()["data"]["analysis_key"]

    workspace_response = client.get(
        f"/api/ai/exceedance/investigation/{analysis_key}")
    assert workspace_response.status_code == 200
    workspace_payload = workspace_response.get_json()
    assert workspace_payload["success"] is True
    assert workspace_payload["investigation"]["status"] == "open"
    assert workspace_payload["investigation"]["comment_version"] == 0

    comment_response = client.post(
        f"/api/ai/exceedance/investigation/{analysis_key}/comment",
        json={"author": "eng-reviewer",
              "comment": "Need structural review before release."},
    )
    assert comment_response.status_code == 200
    comment_payload = comment_response.get_json()
    assert comment_payload["comment"]["version"] == 1
    assert comment_payload["investigation"]["comment_count"] == 1

    approval_response = client.post(
        f"/api/ai/exceedance/investigation/{analysis_key}/approval",
        json={"actor": "chief-eng", "role": "Engineering", "stage": "stage_1"},
    )
    assert approval_response.status_code == 200
    approval_payload = approval_response.get_json()
    assert len(approval_payload["approval"]["signature_hash"]) == 16
    assert approval_payload["investigation"]["approval_count"] == 1

    peer_review_response = client.post(
        f"/api/ai/exceedance/investigation/{analysis_key}/peer_review",
        json={"actor": "qa-review", "role": "QA"},
    )
    assert peer_review_response.status_code == 200
    peer_review_payload = peer_review_response.get_json()
    assert peer_review_payload["investigation"]["peer_review_status"]["ready"] is True
    assert peer_review_payload["investigation"]["approval_count"] == 2

    close_response = client.put(
        f"/api/ai/exceedance/investigation/{analysis_key}/state",
        json={"status": "closed", "locked": True, "actor": "chief-eng"},
    )
    assert close_response.status_code == 200
    close_payload = close_response.get_json()
    assert close_payload["investigation"]["status"] == "closed"
    assert close_payload["investigation"]["locked"] is True

    blocked_comment = client.post(
        f"/api/ai/exceedance/investigation/{analysis_key}/comment",
        json={"author": "eng-reviewer", "comment": "This should be blocked."},
    )
    assert blocked_comment.status_code == 409

    queue_response = client.get("/api/ai/exceedance/investigations/queue")
    assert queue_response.status_code == 200
    queue_payload = queue_response.get_json()
    assert queue_payload["success"] is True
    assert queue_payload["count"] >= 1

    dashboard_response = client.get(
        "/api/ai/exceedance/investigations/dashboard")
    assert dashboard_response.status_code == 200
    dashboard_payload = dashboard_response.get_json()
    assert dashboard_payload["dashboard"]["total_investigations"] >= 1

    response_times = client.get(
        "/api/ai/exceedance/investigations/response_times")
    assert response_times.status_code == 200
    assert response_times.get_json()["success"] is True


def test_exceedance_outcome_metrics_learning_cycle(monkeypatch, tmp_path: Path) -> None:
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
    analyze = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Hydraulic fluctuations after hard landing",
            "scenario": "Approach unstable with touchdown G peak",
            "tail": "PR-E2A",
            "modelo": "E195-E2",
            "csv_files": (io.BytesIO(b"timestamp,event,message\n2026-03-26T10:00:00Z,hard landing,Vertical acceleration exceedance\n"), "event_log.csv"),
        },
        content_type="multipart/form-data",
    )
    assert analyze.status_code == 200
    analysis_key = analyze.get_json()["data"]["analysis_key"]

    outcome = client.post(
        "/api/ai/exceedance/outcomes",
        json={
            "analysis_key": analysis_key,
            "validated_by": "field-team-a",
            "outcome_status": "resolved",
            "confirmed_exceedance": True,
            "executed_actions": [
                "Hold aircraft release pending Engineering initial disposition.",
                "Ground aircraft for hard-landing structural inspection matrix before next flight leg.",
            ],
            "notes": "Field validation confirms exceedance and successful corrective path.",
        },
    )
    assert outcome.status_code == 200
    outcome_payload = outcome.get_json()
    assert outcome_payload["success"] is True
    assert outcome_payload["outcome"]["analysis_key"] == analysis_key
    assert "metrics" in outcome_payload
    assert "post_validation_precision" in outcome_payload["metrics"]

    metrics = client.get("/api/ai/exceedance/outcomes/metrics")
    assert metrics.status_code == 200
    metrics_payload = metrics.get_json()
    assert metrics_payload["success"] is True
    assert metrics_payload["count"] >= 1
    assert "post_validation_precision" in metrics_payload["metrics"]
    assert "effectiveness_index" in metrics_payload["metrics"]
    assert "divergence_monitor" in metrics_payload["metrics"]
    assert "adaptive_learning" in metrics_payload["metrics"]


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
    assert "weak_signal_alerts" in payload["data"]
    assert "root_cause_classifier" in payload["data"]
    assert "counterfactual_analysis" in payload["data"]
    assert "corrective_action_impact" in payload["data"]
    assert "action_dependency_plan" in payload["data"]
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


def test_exceedance_document_summarization(monkeypatch, tmp_path: Path) -> None:
    """Test Item 381: Document summarization from PDF technical text."""
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=2000: _sample_open_records())
    monkeypatch.setattr("routes_analytics.get_ai", lambda: type("AIStub", (), {
        "chat": lambda *args, **kwargs: {"response": "", "related_atas": [], "suggestions": []},
        "get_analytics": lambda *args: {"error": "stub"},
        "list_ata_systems": lambda *args: [],
    })())

    client = app.test_client()
    pdf_content = b"""
    FINDING: The aircraft experienced a hard landing event at aerodrome.
    Vertical acceleration exceeded 2.5 G during final touchdown phase.
    
    ACTION: Inspect landing gear and fuselage structure for damage.
    Perform full structural inspection per AMM 32-21-00.
    
    LIMITATION: Maximum landing weight must not exceed 55,000 kg for this aircraft.
    Do not dispatch if structural damage is evident.
    
    PROCEDURE: Follow the standard hard landing checklist provided in section 05-51-00.
    """

    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Hard landing vertical acceleration exceedance",
            "scenario": "Touchdown with high vertical descent rate",
            "tail": "PR-E2A",
            "modelo": "E195-E2",
            "pdf_files": (io.BytesIO(pdf_content), "technical_manual.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    # Verify document summary is present
    assert "document_summary" in payload["data"]
    doc_summary = payload["data"]["document_summary"]
    assert doc_summary["token_count"] >= 0
    assert doc_summary["relevance_score"] >= 0.0
    assert "key_sections" in doc_summary


def test_exceedance_constraint_extraction(monkeypatch, tmp_path: Path) -> None:
    """Test Item 382: Automatic constraint extraction from PDF manual."""
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=2000: _sample_open_records())
    monkeypatch.setattr("routes_analytics.get_ai", lambda: type("AIStub", (), {
        "chat": lambda *args, **kwargs: {"response": "", "related_atas": [], "suggestions": []},
        "get_analytics": lambda *args: {"error": "stub"},
        "list_ata_systems": lambda *args: [],
    })())

    client = app.test_client()
    pdf_content = b"""
    LIMITATION AND RESTRICTIONS:
    
    Maximum landing weight: 55,000 kg
    Minimum speed for landing: 130 knots
    Maximum speed in flap configuration: 280 knots
    Landing distance required: 2,500 feet
    
    PREREQUISITES:
    Before performing hard landing inspection, must verify structural integrity.
    Required: Two technicians present during inspection.
    Prerequisite checklist completion before maintenance.
    """

    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Hard landing with weight/speed concerns",
            "scenario": "Landing with high gross weight",
            "tail": "PR-E2A",
            "modelo": "E195-E2",
            "pdf_files": (io.BytesIO(pdf_content), "limitations.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    # Verify constraint extraction
    assert "extracted_constraints" in payload["data"]
    constraints = payload["data"]["extracted_constraints"]
    assert "hard_limits" in constraints
    assert "prerequisites" in constraints
    assert len(constraints.get("constraints", [])) >= 0


def test_exceedance_procedure_comparison(monkeypatch, tmp_path: Path) -> None:
    """Test Item 383: Compare recommended actions vs official procedure."""
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=2000: _sample_open_records())
    monkeypatch.setattr("routes_analytics.get_ai", lambda: type("AIStub", (), {
        "chat": lambda *args, **kwargs: {
            "response": "",
            "related_atas": ["29"],
            "suggestions": []
        },
        "get_analytics": lambda *args: {"error": "stub"},
        "list_ata_systems": lambda *args: [],
    })())

    client = app.test_client()
    pdf_content = b"""
    PROCEDURE: Step 1 - Inspect pump for leakage and pressure reading.
    Step 2 - Check pressure line connections and integrity.
    Step 3 - Verify fluid level and condition.
    Step 4 - Test pump operation and log results.
    """

    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Hydraulic pressure fluctuation after landing",
            "scenario": "Pressure drops post-flight",
            "tail": "PR-E2A",
            "modelo": "E195-E2",
            "pdf_files": (io.BytesIO(pdf_content), "procedure.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    # Verify procedure comparison
    assert "procedure_comparison" in payload["data"]
    comparison = payload["data"]["procedure_comparison"]
    assert "comparison_score" in comparison
    assert "aligned_actions" in comparison
    assert "unaligned_actions" in comparison
    assert "coverage" in comparison


def test_exceedance_incompatibility_alert(monkeypatch, tmp_path: Path) -> None:
    """Test Item 384: Alert when procedure incompatibility is detected."""
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=2000: _sample_open_records())
    monkeypatch.setattr("routes_analytics.get_ai", lambda: type("AIStub", (), {
        "chat": lambda *args, **kwargs: {
            "response": "",
            "related_atas": ["27"],
            "suggestions": []
        },
        "get_analytics": lambda *args: {"error": "stub"},
        "list_ata_systems": lambda *args: [],
    })())

    client = app.test_client()
    pdf_content = b"""
    OFFICIAL PROCEDURE: Check flap position indicator.
    Verify slat extension. Measure flap angle.
    """

    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Flap overspeed with asymmetry indication",
            "scenario": "Unusual flap retraction sequence observed",
            "tail": "PR-E2A",
            "modelo": "E195-E2",
            "pdf_files": (io.BytesIO(pdf_content), "flap_procedure.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    # Verify incompatibility alert
    assert "procedure_incompatibility_alert" in payload["data"]
    alert = payload["data"]["procedure_incompatibility_alert"]
    assert "incompatible" in alert
    assert "divergence_pct" in alert
    assert "severity" in alert
    assert "alert_message" in alert


def test_exceedance_input_quality_evaluation(monkeypatch, tmp_path: Path) -> None:
    """Test Item 385: Automatic data quality evaluation of input."""
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=2000: _sample_open_records())
    monkeypatch.setattr("routes_analytics.get_ai", lambda: type("AIStub", (), {
        "chat": lambda *args, **kwargs: {"response": "", "related_atas": [], "suggestions": []},
        "get_analytics": lambda *args: {"error": "stub"},
        "list_ata_systems": lambda *args: [],
    })())

    client = app.test_client()
    csv_content = (
        "timestamp,event,vertical_acceleration_g,touchdown_g\n"
        "2026-03-26T10:15:00Z,hard landing,2.8,3.2\n"
        "2026-03-26T10:15:05Z,structural inspection,,,\n"
    )
    pdf_content = b"""
    FINDING: Vertical acceleration exceeded 2.5 G.
    Hard landing event with high descent rate.
    
    ACTION: Perform inspections per ATA 32 checklist.
    Verify structural integrity before release.
    
    LIMITATION: Landing weight constraint 55 tons.
    PROCEDURE: Follow standard hard landing protocol ATA 32.
    """

    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Hard landing quality assessment",
            "scenario": "Input quality validation test",
            "tail": "PR-E2A",
            "modelo": "E195-E2",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "events.csv"),
            "pdf_files": (io.BytesIO(pdf_content), "documentation.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    # Verify input quality evaluation
    assert "input_quality_evaluation" in payload["data"]
    quality = payload["data"]["input_quality_evaluation"]
    assert "quality_score" in quality
    assert quality["quality_score"] >= 0.0 and quality["quality_score"] <= 100.0
    assert "csv_quality" in quality
    assert "pdf_quality" in quality
    assert "completeness" in quality
    assert "recommendations" in quality
    assert len(quality["recommendations"]) >= 1


def test_exceedance_robustness_scoring(monkeypatch, tmp_path: Path) -> None:
    """Item 386: Score recommendation robustness against historical outcomes."""
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=2000: _sample_open_records())
    monkeypatch.setattr("routes_analytics.get_ai", lambda: type("AIStub", (), {
        "chat": lambda *args, **kwargs: {"response": "", "related_atas": [], "suggestions": []},
        "get_analytics": lambda *args: {"error": "stub"},
        "list_ata_systems": lambda *args: [],
    })())

    # Mock outcomes with historical data
    outcomes_store = [
        {
            "analysis_key": "prev-001",
            "executed_actions": ["inspection", "structural check"],
            "outcome_status": "resolved"
        },
        {
            "analysis_key": "prev-002",
            "executed_actions": ["inspection"],
            "outcome_status": "closed"
        }
    ]
    monkeypatch.setattr("routes_analytics._load_exceedance_outcomes",
                        lambda: outcomes_store)

    client = app.test_client()
    csv_content = (
        "timestamp,event\n"
        "2026-03-26T10:15:00Z,structural failure\n"
    )
    pdf_content = b"FINDING: Structural defect\nACTION: Inspection required"

    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Structural assessment",
            "scenario": "Robustness scoring test",
            "tail": "N12345",
            "modelo": "B777-F",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "events.csv"),
            "pdf_files": (io.BytesIO(pdf_content), "doc.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    # Verify robustness score
    assert "robustness_score" in payload["data"]
    robustness = payload["data"]["robustness_score"]
    assert "robustness_score" in robustness
    assert robustness["robustness_score"] >= 0.0 and robustness["robustness_score"] <= 100.0
    assert "action_success_rates" in robustness
    assert "historical_validation" in robustness
    assert robustness["historical_validation"] in {"low", "medium", "high"}
    assert "confidence_level" in robustness
    assert robustness["confidence_level"] in {"low", "medium", "high"}


def test_exceedance_cost_ranking(monkeypatch, tmp_path: Path) -> None:
    """Item 387: Rank actions by estimated operational cost."""
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=2000: _sample_open_records())
    monkeypatch.setattr("routes_analytics.get_ai", lambda: type("AIStub", (), {
        "chat": lambda *args, **kwargs: {"response": "", "related_atas": [], "suggestions": []},
        "get_analytics": lambda *args: {"error": "stub"},
        "list_ata_systems": lambda *args: [],
    })())

    client = app.test_client()
    csv_content = (
        "timestamp,event\n"
        "2026-03-26T10:15:00Z,lru failure\n"
    )
    pdf_content = b"FINDING: LRU failure\nACTION: Replacement required"

    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "LRU replacement needed",
            "scenario": "Cost ranking test",
            "tail": "N54321",
            "modelo": "A320-232",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "events.csv"),
            "pdf_files": (io.BytesIO(pdf_content), "doc.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    # Verify cost ranking
    assert "cost_ranking" in payload["data"]
    cost = payload["data"]["cost_ranking"]
    assert "ranked_actions" in cost
    assert isinstance(cost["ranked_actions"], list)
    assert "total_estimated_cost_hours" in cost
    assert cost["total_estimated_cost_hours"] >= 0.0
    assert "total_cost_estimate" in cost
    assert cost["total_cost_estimate"] >= 0
    assert "cost_optimization_suggestions" in cost


def test_exceedance_evidence_gaps(monkeypatch, tmp_path: Path) -> None:
    """Item 388: Detect evidence gaps by ATA family."""
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=2000: _sample_open_records())
    monkeypatch.setattr("routes_analytics.get_ai", lambda: type("AIStub", (), {
        "chat": lambda *args, **kwargs: {"response": "", "related_atas": [], "suggestions": []},
        "get_analytics": lambda *args: {"error": "stub"},
        "list_ata_systems": lambda *args: [],
    })())

    client = app.test_client()
    csv_content = "timestamp\n2026-03-26T10:15:00Z\n"
    pdf_content = b"Minimal documentation"

    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Incomplete data test",
            "scenario": "Evidence gaps detection",
            "tail": "N99999",
            "ata": "29-10",
            "modelo": "C172",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "events.csv"),
            "pdf_files": (io.BytesIO(pdf_content), "doc.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    # Verify evidence gaps
    assert "evidence_gaps" in payload["data"]
    gaps = payload["data"]["evidence_gaps"]
    assert "ata_chapter" in gaps
    assert "evidence_gaps" in gaps
    assert isinstance(gaps["evidence_gaps"], list)
    assert "quality_level" in gaps
    assert gaps["quality_level"] in {"complete", "partial", "poor"}
    assert "closure_readiness" in gaps
    assert isinstance(gaps["closure_readiness"], bool)


def test_exceedance_audit_checklist(monkeypatch, tmp_path: Path) -> None:
    """Item 389: Generate regulatory audit checklist."""
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=2000: _sample_open_records())
    monkeypatch.setattr("routes_analytics.get_ai", lambda: type("AIStub", (), {
        "chat": lambda *args, **kwargs: {"response": "", "related_atas": [], "suggestions": []},
        "get_analytics": lambda *args: {"error": "stub"},
        "list_ata_systems": lambda *args: [],
    })())

    client = app.test_client()
    csv_content = (
        "timestamp,event\n"
        "2026-03-26T10:15:00Z,hard landing\n"
    )
    pdf_content = b"""
    FINDING: High descent rate detected
    ACTION: Structural inspection required
    PROCEDURE: ATA 32 hard landing protocol
    """

    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Hard landing audit",
            "scenario": "Regulatory compliance test",
            "tail": "N11111",
            "ata": "31",
            "modelo": "ERJ-145",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "events.csv"),
            "pdf_files": (io.BytesIO(pdf_content), "doc.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    # Verify audit checklist
    assert "audit_checklist" in payload["data"]
    checklist = payload["data"]["audit_checklist"]
    assert "checklist" in checklist
    assert isinstance(checklist["checklist"], list)
    assert len(checklist["checklist"]) > 0
    assert "audit_ready" in checklist
    assert isinstance(checklist["audit_ready"], bool)
    assert "compliance_summary" in checklist
    assert "pass_count" in checklist["compliance_summary"]
    assert "fail_count" in checklist["compliance_summary"]
    assert "total_items" in checklist["compliance_summary"]

    # Verify checklist items have required fields
    for item in checklist["checklist"]:
        assert "item" in item
        assert "description" in item
        assert "status" in item
        assert item["status"] in {"pass", "fail", "pending", "conditional"}


def test_exceedance_engineering_export(monkeypatch, tmp_path: Path) -> None:
    """Item 390: Generate engineering export package."""
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=2000: _sample_open_records())
    monkeypatch.setattr("routes_analytics.get_ai", lambda: type("AIStub", (), {
        "chat": lambda *args, **kwargs: {"response": "", "related_atas": [], "suggestions": []},
        "get_analytics": lambda *args: {"error": "stub"},
        "list_ata_systems": lambda *args: [],
    })())

    client = app.test_client()
    csv_content = (
        "timestamp,event,value\n"
        "2026-03-26T10:15:00Z,sensor failure,45\n"
    )
    pdf_content = b"""
    FINDING: Sensor malfunction detected
    ACTION: Sensor replacement
    LIMITATION: Must be replaced within 100 flight hours
    REFERENCE: AMM 30-12-00-001
    """

    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Sensor exceedance package",
            "scenario": "Engineering export test",
            "tail": "PR-ABC",
            "ata": "30-10",
            "modelo": "E190",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "events.csv"),
            "pdf_files": (io.BytesIO(pdf_content), "doc.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    # Verify engineering export package
    assert "engineering_export" in payload["data"]
    export = payload["data"]["engineering_export"]
    assert "package_id" in export
    assert "generated_at" in export
    assert "target_audience" in export
    assert "aircraft" in export
    assert "ata_chapter" in export
    assert "content" in export
    assert "distribution" in export

    # Verify content sections
    content = export["content"]
    assert "analysis_summary" in content
    assert "document_analysis" in content
    assert "execution_planning" in content
    assert "regulatory_compliance" in content
    assert "closure_readiness" in content
    assert "training_package" in content

    # Verify distribution metadata
    distribution = export["distribution"]
    assert "format" in distribution
    assert "recipients" in distribution
    assert isinstance(distribution["recipients"], list)
    assert "retention_period_days" in distribution
