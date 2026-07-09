from __future__ import annotations
import routes_analytics as _ra
import importlib

import json
from pathlib import Path

from flask import Flask

from routes_analytics import analytics_bp


def _build_test_app(tmp_path: Path) -> Flask:
    app = Flask(__name__, root_path=str(tmp_path))
    app.register_blueprint(analytics_bp)
    app.config.update(TESTING=True, SECRET_KEY="test-secret-key")

    # Keep fallback files local to this test app root.
    (tmp_path / "tails_fallback.json").write_text(
        json.dumps(
            [
                {"tail": "PR-E2A", "fh": 15000.0, "fc": 9000},
                {"tail": "PR-E1B", "fh": 8000.0, "fc": 5000},
            ]
        ),
        encoding="utf-8",
    )

    return app


def test_ai_summary_contains_fh_fc_priority(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    sample_records = [
        {
            "id": 1,
            "tail": "PR-E2A",
            "ata": "29",
            "problema": "Hydraulic pressure fluctuation on system B",
            "prioridade": "High",
            "categoria": "Hydraulic",
            "modelo": "E195-E2",
            "status_atual": "Open",
            "tempo_estimado_horas": 2.5,
            "fh": 15000,
            "fc": 9000,
        },
        {
            "id": 2,
            "tail": "PR-E2A",
            "ata": "29",
            "problema": "Hydraulic pressure fluctuation on system B",
            "prioridade": "High",
            "categoria": "Hydraulic",
            "modelo": "E195-E2",
            "status_atual": "Open",
            "tempo_estimado_horas": 2.5,
            "fh": 15000,
            "fc": 9000,
        },
        {
            "id": 3,
            "tail": "PR-E1B",
            "ata": "34",
            "problema": "Navigation mismatch in descent",
            "prioridade": "Medium",
            "categoria": "Avionics",
            "modelo": "EMB190",
            "status_atual": "Closed",
            "tempo_estimado_horas": 1.5,
            "fh": 8000,
            "fc": 5000,
        },
    ]

    monkeypatch.setattr(
        "routes_analytics.load_records",
        lambda limit=5000: sample_records,
    )

    client = app.test_client()
    response = client.get("/api/ai/summary")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["success"] is True
    assert payload["summary"]["fh_fc_priority"]
    assert payload["summary"]["fh_fc_priority"][0]["tail"] == "PR-E2A"
    assert "intelligence_depth" in payload["summary"]
    assert (
        "feedback_acceptance_rate"
        in payload["summary"]["intelligence_depth"]
    )


def test_parse_model_filter_tokens_all_fleet_returns_empty() -> None:
    assert _ra._parse_model_filter_tokens("ALL_FLEET") == []
    assert _ra._parse_model_filter_tokens("ALL-FLEET") == []
    assert _ra._parse_model_filter_tokens("ALL FLEET") == []


def test_ai_summary_without_filter_uses_all_families(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    sample_records = [
        {
            "id": 1,
            "tail": "PR-E2A",
            "ata": "29",
            "problema": "Hydraulic pressure fluctuation on system B",
            "prioridade": "High",
            "categoria": "Hydraulic",
            "modelo": "E195-E2",
            "status_atual": "Open",
            "tempo_estimado_horas": 2.5,
            "fh": 15000,
            "fc": 9000,
        },
        {
            "id": 2,
            "tail": "PR-E1B",
            "ata": "34",
            "problema": "Navigation mismatch in descent",
            "prioridade": "Medium",
            "categoria": "Avionics",
            "modelo": "E190",
            "status_atual": "Closed",
            "tempo_estimado_horas": 1.5,
            "fh": 8000,
            "fc": 5000,
        },
        {
            "id": 3,
            "tail": "PR-ERJ",
            "ata": "52",
            "problema": "Service door damping below standard",
            "prioridade": "Low",
            "categoria": "Mechanical",
            "modelo": "ERJ145",
            "status_atual": "Open",
            "tempo_estimado_horas": 1.0,
            "fh": 6000,
            "fc": 4200,
        },
    ]

    monkeypatch.setattr(
        "routes_analytics.load_records",
        lambda limit=5000: sample_records,
    )

    client = app.test_client()
    response = client.get("/api/ai/summary")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["success"] is True
    assert payload["records_count"] == 3
    families = {
        item["family"]
        for item in payload["summary"]["intelligence_depth"]["family_comparison"]
    }
    assert {"E2", "CLASSIC", "ERJ"}.issubset(families)


def test_ai_summary_all_fleet_query_param_is_unfiltered(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    sample_records = [
        {
            "id": 1,
            "tail": "PR-E2A",
            "ata": "29",
            "problema": "Hydraulic pressure fluctuation on system B",
            "prioridade": "High",
            "categoria": "Hydraulic",
            "modelo": "E195-E2",
            "status_atual": "Open",
            "tempo_estimado_horas": 2.5,
            "fh": 15000,
            "fc": 9000,
        },
        {
            "id": 2,
            "tail": "PR-E1B",
            "ata": "34",
            "problema": "Navigation mismatch in descent",
            "prioridade": "Medium",
            "categoria": "Avionics",
            "modelo": "E190",
            "status_atual": "Closed",
            "tempo_estimado_horas": 1.5,
            "fh": 8000,
            "fc": 5000,
        },
    ]

    monkeypatch.setattr(
        "routes_analytics.load_records",
        lambda limit=5000: sample_records,
    )

    client = app.test_client()
    response = client.get("/api/ai/summary?model=ALL_FLEET")
    assert response.status_code == 200

    payload = response.get_json()
    assert payload["success"] is True
    assert payload["records_count"] == 2


def test_ai_feedback_flow(monkeypatch, tmp_path: Path) -> None:
    app = _build_test_app(tmp_path)

    sample_records = [
        {
            "id": 1,
            "tail": "PR-E2A",
            "ata": "29",
            "problema": "Hydraulic issue",
            "prioridade": "High",
            "categoria": "Hydraulic",
            "modelo": "E195-E2",
            "status_atual": "Open",
            "tempo_estimado_horas": 2.0,
            "fh": 15000,
            "fc": 9000,
        }
    ]
    monkeypatch.setattr(
        "routes_analytics.load_records",
        lambda limit=2000: sample_records,
    )

    client = app.test_client()

    analysis_response = client.post(
        "/api/ai/analyze_failure",
        json={
            "ata": "29",
            "tail": "PR-E2A",
            "model": "E195-E2",
            "category": "Hydraulic",
            "description": "Hydraulic pressure unstable after landing",
        },
    )
    assert analysis_response.status_code == 200
    analysis_json = analysis_response.get_json()
    assert analysis_json["success"] is True
    assert analysis_json["data"]["tail_metrics"]["tail"] == "PR-E2A"
    assert "learning_hint" in analysis_json["data"]
    assert "intelligence" in analysis_json["data"]
    assert "risk_score" in analysis_json["data"]["intelligence"]
    assert "recommended_plan" in analysis_json["data"]["intelligence"]
    assert "similar_cases" in analysis_json["data"]["intelligence"]

    fb_response = client.post(
        "/api/ai/feedback",
        json={
            "ata": "29",
            "helpful": True,
            "query": "Hydraulic pressure unstable",
            "response_excerpt": "Check pumps and filters",
            "source": "test_suite",
        },
    )
    assert fb_response.status_code == 200
    fb_json = fb_response.get_json()
    assert fb_json["success"] is True

    stats_response = client.get("/api/ai/feedback/stats")
    assert stats_response.status_code == 200
    stats_json = stats_response.get_json()
    assert stats_json["success"] is True
    assert stats_json["stats"]["total_feedback"] >= 1


def test_analysis_unknown_ata(monkeypatch, tmp_path: Path) -> None:
    """ATA not in knowledge base should still return a valid response."""
    app = _build_test_app(tmp_path)

    monkeypatch.setattr(
        "routes_analytics.load_records",
        lambda limit=3000: [],
    )

    client = app.test_client()
    response = client.post(
        "/api/ai/analyze_failure",
        json={
            "ata": "99",
            "tail": "XX-TST",
            "model": "Test",
            "category": "Other",
            "description": "Unknown system pressure fluctuation detected",
        },
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert "intelligence" in payload["data"]
    intel = payload["data"]["intelligence"]
    assert "risk_score" in intel
    assert "risk_level" in intel
    assert 0.0 <= intel["risk_score"] <= 100.0


def test_analysis_zero_fh_fc(monkeypatch, tmp_path: Path) -> None:
    """Records with zero FH/FC should not cause division errors."""
    app = _build_test_app(tmp_path)

    records = [
        {
            "id": 10,
            "tail": "PR-ZRO",
            "ata": "29",
            "problema": "Hydraulic pressure low",
            "prioridade": "High",
            "categoria": "Hydraulic",
            "modelo": "E195-E2",
            "status_atual": "Open",
            "tempo_estimado_horas": 1.0,
            "fh": 0,
            "fc": 0,
        }
    ]
    monkeypatch.setattr(
        "routes_analytics.load_records",
        lambda limit=3000: records,
    )

    client = app.test_client()
    response = client.post(
        "/api/ai/analyze_failure",
        json={
            "ata": "29",
            "tail": "PR-ZRO",
            "model": "E195-E2",
            "category": "Hydraulic",
            "description": "Hydraulic pressure low on system A returns zero FH",
        },
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    intel = payload["data"]["intelligence"]
    assert intel["risk_score"] >= 0.0
    assert intel["similar_cases"] == [] or isinstance(
        intel["similar_cases"], list
    )


def test_analysis_missing_description_returns_400(
    monkeypatch, tmp_path: Path
) -> None:
    """Empty description must return HTTP 400."""
    app = _build_test_app(tmp_path)
    monkeypatch.setattr(
        "routes_analytics.load_records",
        lambda limit=3000: [],
    )

    client = app.test_client()
    response = client.post(
        "/api/ai/analyze_failure",
        json={"ata": "29", "tail": "PR-E2A"},
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False


def test_recalibrate_no_feedback(tmp_path: Path) -> None:
    """Recalibrate with no stored feedback should succeed gracefully."""
    app = _build_test_app(tmp_path)
    # Ensure feedback file is absent
    feedback_path = tmp_path / "ai_feedback.json"
    if feedback_path.exists():
        feedback_path.unlink()

    client = app.test_client()
    response = client.post("/api/ai/recalibrate")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["total_samples_analyzed"] == 0
    assert payload["calibration"] == {}


def test_recalibrate_with_feedback(monkeypatch, tmp_path: Path) -> None:
    """Recalibrate should produce per-ATA signals from real feedback."""
    app = _build_test_app(tmp_path)

    feedback_data = [
        {"id": 1, "ata": "29", "helpful": True},
        {"id": 2, "ata": "29", "helpful": True},
        {"id": 3, "ata": "29", "helpful": False},
        {"id": 4, "ata": "34", "helpful": False},
        {"id": 5, "ata": "34", "helpful": False},
    ]
    (tmp_path / "ai_feedback.json").write_text(
        json.dumps(feedback_data), encoding="utf-8"
    )

    client = app.test_client()
    response = client.post("/api/ai/recalibrate")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["ata_count"] == 2
    assert "29" in payload["calibration"]
    assert "34" in payload["calibration"]
    ata34 = payload["calibration"]["34"]
    assert ata34["signal"] == "review"
    assert ata34["review_required"] is True
    assert payload["review_required_count"] >= 1


def test_ai_chat_guardrail_blocks_contradictory_response(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    monkeypatch.setattr(
        "routes_analytics._build_copilot_answer",
        lambda **kwargs: {
            "response": (
                "No records matched current filter. "
                "Based on matched records, ATA 29 is the top recurrent issue."
            ),
            "confidence": 88,
            "sources": {"records": 0},
        },
    )

    client = app.test_client()
    response = client.post(
        "/api/ai/chat",
        json={"query": "show ATA 29 risk", "scope": "global"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["guardrail"]["consistency_applied"] is True
    assert data["guardrail"]["reason"] == "contradictory_data_claims"
    assert "Detectei inconsistencias" in data["response"]


def test_ai_chat_uses_context_fallback_when_memory_empty(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    class _DummyAI:
        def __init__(self) -> None:
            self.last_query = ""

        def chat(self, query: str, records=None):
            self.last_query = query
            return {
                "response": "ok",
                "confidence": 0.8,
                "related_atas": ["29"],
                "suggestions": ["Check ATA 29"],
            }

        def get_analytics(self, records):
            return {}

    class _DummyV10:
        def start_user_session(self, user_id: str) -> str:
            return "session-test"

        def process_query(self, query: str, session_id: str, user_id: str):
            return {
                "confidence": 0.7,
                "confidence_grade": "B",
                "primary_intent": "diagnostic",
                "secondary_intents": [],
                "language": "pt-BR",
            }

        def compose_response_package(self, query, result, operational_context, user_id):
            return {
                "response_text": "",
                "next_questions": [],
                "language_variant": "pt-BR",
                "response_sections": {},
                "chart_focus": {},
                "chart_brief": {},
                "suggested_visuals": [],
            }

    dummy_ai = _DummyAI()
    monkeypatch.setattr("routes_analytics.get_ai", lambda: dummy_ai)
    monkeypatch.setattr("routes_analytics.get_v10_engine", lambda: _DummyV10())
    monkeypatch.setattr(
        "routes_analytics.load_records",
        lambda limit=4000: [
            {
                "id": 1,
                "tail": "PR-E2A",
                "ata": "29",
                "problema": "Hydraulic pressure oscillation during taxi",
                "prioridade": "High",
                "status_atual": "Open",
                "modelo": "E195-E2",
            }
        ],
    )
    monkeypatch.setattr(
        "routes_analytics._load_mel_context", lambda limit=400: [])
    monkeypatch.setattr(
        "routes_analytics._load_aog_context", lambda limit=400: [])
    monkeypatch.setattr(
        "routes_analytics._load_lru_context", lambda limit=700: [])
    monkeypatch.setattr("routes_analytics._load_tail_metrics", lambda: {})

    client = app.test_client()
    response = client.post(
        "/api/ai/chat",
        json={"query": "need quick technical summary", "scope": "global"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["context_fallback_used"] is True
    assert "Technical fallback context" in dummy_ai.last_query


def test_ai_chat_normalizes_malformed_payload(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    monkeypatch.setattr(
        "routes_analytics._build_copilot_answer",
        lambda **kwargs: {
            "response": None,
            "confidence": "invalid",
            "sources": "broken",
            "suggestions": "not-list",
            "next_questions": None,
            "guardrail": "bad-shape",
        },
    )

    client = app.test_client()
    response = client.post(
        "/api/ai/chat",
        json={"query": "status ata 29", "scope": "global"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["payload_normalized"] is True
    assert isinstance(data["response"], str) and data["response"]
    assert isinstance(data["sources"], dict)
    assert data["sources"]["scope"] == "global"
    assert isinstance(data["suggestions"], list)
    assert isinstance(data["next_questions"], list)


def test_ai_chat_truncates_very_large_response(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    huge_text = "X" * 15050
    monkeypatch.setattr(
        "routes_analytics._build_copilot_answer",
        lambda **kwargs: {
            "response": huge_text,
            "confidence": 80,
            "sources": {"records": 1},
        },
    )

    client = app.test_client()
    response = client.post(
        "/api/ai/chat",
        json={"query": "long output check", "scope": "global"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["response_truncated"] is True
    assert data["response_original_size"] == 15050
    assert len(data["response"]) < 13000


def test_ai_chat_returns_controlled_fallback_on_exception(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    def _boom(**kwargs):
        raise RuntimeError("simulated failure")

    monkeypatch.setattr("routes_analytics._build_copilot_answer", _boom)

    client = app.test_client()
    response = client.post(
        "/api/ai/chat",
        json={"query": "ata 29", "scope": "global"},
    )
    assert response.status_code == 503
    payload = response.get_json()
    assert payload["success"] is False
    data = payload["data"]
    assert data["guardrail"]["reason"] == "exception_fallback"
    assert isinstance(data["request_id"],
                      str) and data["request_id"].startswith("ai-chat-")
    assert isinstance(data["processing_ms"], int)


def test_ai_chat_success_contains_stability_metadata(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    monkeypatch.setattr(
        "routes_analytics._build_copilot_answer",
        lambda **kwargs: {
            "response": "ok",
            "confidence": 70,
            "sources": {"records": 1},
        },
    )

    client = app.test_client()
    response = client.post(
        "/api/ai/chat",
        json={"query": "ata 29 status", "scope": "global"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    data = payload["data"]
    assert isinstance(data["request_id"],
                      str) and data["request_id"].startswith("ai-chat-")
    assert isinstance(data["processing_ms"], int)


def test_ai_chat_query_required_returns_contract_error(tmp_path: Path) -> None:
    app = _build_test_app(tmp_path)

    client = app.test_client()
    response = client.post(
        "/api/ai/chat",
        json={"query": "", "scope": "global"},
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert isinstance(payload["data"], dict)
    assert payload["data"]["error_code"] == "query_required"
    assert payload["data"]["retryable"] is False
    assert isinstance(payload["data"]["request_id"], str)


def test_ai_chat_exception_returns_retryable_contract_error(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    def _boom(**kwargs):
        raise RuntimeError("forced")

    monkeypatch.setattr("routes_analytics._build_copilot_answer", _boom)

    client = app.test_client()
    response = client.post(
        "/api/ai/chat",
        json={"query": "ATA 29", "scope": "global"},
    )
    assert response.status_code == 503
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["data"]["error_code"] == "exception_fallback"
    assert payload["data"]["retryable"] is True


def test_ai_chat_retries_once_before_fallback(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)
    state = {"calls": 0}

    def _flaky(**kwargs):
        state["calls"] += 1
        if state["calls"] == 1:
            raise RuntimeError("transient")
        return {
            "response": "recovered",
            "confidence": 70,
            "sources": {"records": 1},
        }

    monkeypatch.setattr("routes_analytics._build_copilot_answer", _flaky)

    client = app.test_client()
    response = client.post(
        "/api/ai/chat",
        json={"query": "ATA 29 retry", "scope": "global"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert state["calls"] == 2


def test_ai_copilot_query_required_returns_contract_error(tmp_path: Path) -> None:
    app = _build_test_app(tmp_path)

    client = app.test_client()
    response = client.post(
        "/api/ai/copilot",
        json={"query": "", "scope": "global"},
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["data"]["error_code"] == "query_required"
    assert payload["data"]["retryable"] is False


def test_ai_copilot_exception_returns_contract_error(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    def _boom(**kwargs):
        raise RuntimeError("forced")

    monkeypatch.setattr(
        "routes_analytics._build_copilot_answer_with_retry", _boom)

    client = app.test_client()
    response = client.post(
        "/api/ai/copilot",
        json={"query": "ATA 29", "scope": "global"},
    )
    assert response.status_code == 503
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["data"]["error_code"] == "exception_fallback"
    assert payload["data"]["retryable"] is True


def test_ai_chat_deep_mode_coercion_from_string(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)
    seen = {"deep_mode": None}

    def _capture(**kwargs):
        seen["deep_mode"] = kwargs.get("deep_mode")
        return {
            "response": "ok",
            "confidence": 70,
            "sources": {"records": 1},
        }

    monkeypatch.setattr(
        "routes_analytics._build_copilot_answer_with_retry", _capture)

    client = app.test_client()
    response = client.post(
        "/api/ai/chat",
        json={"query": "ATA 29", "scope": "global", "deep_mode": "true"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert seen["deep_mode"] is True


def test_ai_chat_success_has_version_and_timestamp(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    monkeypatch.setattr(
        "routes_analytics._build_copilot_answer_with_retry",
        lambda **kwargs: {
            "response": "ok",
            "confidence": 70,
            "sources": {"records": 1},
        },
    )

    client = app.test_client()
    response = client.post(
        "/api/ai/chat",
        json={"query": "version check", "scope": "global"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["api_version"] == "v12.0"
    assert isinstance(data["server_ts"], str) and data["server_ts"]


def test_ai_chat_cache_status_miss(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    monkeypatch.setattr(
        "routes_analytics._build_copilot_answer_with_retry",
        lambda **kwargs: {
            "response": "ok",
            "confidence": 70,
            "sources": {"records": 1},
        },
    )

    client = app.test_client()
    response = client.post(
        "/api/ai/chat",
        json={"query": "cache miss unique 1001",
              "scope": "global", "deep_mode": False},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["cache_status"] == "miss"


def test_ai_chat_cache_status_bypass_on_deep_mode(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    monkeypatch.setattr(
        "routes_analytics._build_copilot_answer_with_retry",
        lambda **kwargs: {
            "response": "ok",
            "confidence": 70,
            "sources": {"records": 1},
        },
    )

    client = app.test_client()
    response = client.post(
        "/api/ai/chat",
        json={"query": "cache bypass deep",
              "scope": "global", "deep_mode": True},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["cache_status"] == "bypass"


def test_ai_chat_unknown_scope_is_normalized(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    monkeypatch.setattr(
        "routes_analytics._build_copilot_answer_with_retry",
        lambda **kwargs: {
            "response": "ok",
            "confidence": 70,
            "sources": {"records": 1},
        },
    )

    client = app.test_client()
    response = client.post(
        "/api/ai/chat",
        json={"query": "scope test", "scope": "invalid-scope"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["scope_effective"] == "global"
    assert payload["data"]["input_normalized"] is True


def test_ai_chat_accepts_fleet_scope(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    monkeypatch.setattr(
        "routes_analytics._build_copilot_answer_with_retry",
        lambda **kwargs: {
            "response": "ok",
            "confidence": 70,
            "sources": {"records": 10},
        },
    )

    client = app.test_client()
    response = client.post(
        "/api/ai/chat",
        json={"query": "fleet ata overview", "scope": "fleet"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["scope_effective"] == "fleet"


def test_build_copilot_answer_filters_records_by_exact_ata(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    sample_records = [
        {
            "id": 1,
            "tail": "PR-E2A",
            "ata": "29",
            "problema": "Hydraulic issue on system B",
            "modelo": "E195-E2",
            "status_atual": "Open",
        },
        {
            "id": 2,
            "tail": "PR-E2A",
            "ata": "49",
            "problema": "APU generator issue",
            "modelo": "E195-E2",
            "status_atual": "Open",
        },
    ]
    captured = {}

    class _DummyAI:
        def chat(self, query, records=None):
            captured["query"] = query
            captured["records"] = list(records or [])
            return {
                "response": "ok",
                "confidence": 88,
                "related_atas": ["29"],
                "suggestions": [],
            }

        def get_analytics(self, records):
            return {"total": len(records), "top_ata": []}

    class _DummyV10:
        def start_user_session(self, user_id: str) -> str:
            return "session-test"

        def process_query(self, query: str, session_id: str, user_id: str):
            return {
                "confidence": 0.8,
                "confidence_grade": "A",
                "primary_intent": "diagnostic",
                "secondary_intents": [],
                "language": "pt-BR",
            }

        def compose_response_package(self, query, result, operational_context, user_id):
            return {
                "response_text": "ok",
                "next_questions": [],
                "language_variant": "pt-BR",
                "response_sections": {},
                "chart_focus": {},
                "chart_brief": {},
                "suggested_visuals": [],
            }

    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=15000: sample_records)
    monkeypatch.setattr("routes_analytics.get_ai", lambda: _DummyAI())
    monkeypatch.setattr("routes_analytics.get_v10_engine", lambda: _DummyV10())
    monkeypatch.setattr(
        "routes_analytics._load_mel_context", lambda limit=400: [])
    monkeypatch.setattr(
        "routes_analytics._load_aog_context", lambda limit=400: [])
    monkeypatch.setattr(
        "routes_analytics._load_lru_context", lambda limit=700: [])
    monkeypatch.setattr("routes_analytics._load_tail_metrics", lambda: {})

    with app.test_request_context("/api/ai/chat", method="POST"):
        result = _ra._build_copilot_answer(
            query="ATA 29 hydraulic status", scope="global")

    assert result["structured_query"]["ata_exact"] is True
    assert result["structured_query"]["fuzzy_enabled"] is False
    assert [str(item.get("ata")) for item in captured["records"]] == ["29"]


def test_resolve_tail_focus_keeps_ambiguous_suffix_out() -> None:
    known_tails = ["PR-E2A", "XA-E2A", "PR-E9B"]

    assert _ra._resolve_tail_focus("show tail E2A status", known_tails) == []
    assert _ra._resolve_tail_focus(
        "show tail PR-E2A status", known_tails) == ["PR-E2A"]


def test_build_copilot_answer_treats_unique_short_tail_as_exact(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    sample_records = [
        {
            "id": 1,
            "tail": "PR-E2A",
            "ata": "29",
            "problema": "Hydraulic pressure fluctuation",
            "modelo": "E195-E2",
            "status_atual": "Open",
        },
        {
            "id": 2,
            "tail": "PR-E1B",
            "ata": "34",
            "problema": "Navigation mismatch",
            "modelo": "E190",
            "status_atual": "Open",
        },
    ]
    captured = {}

    class _DummyAI:
        def chat(self, query, records=None):
            captured["query"] = query
            captured["records"] = list(records or [])
            return {
                "response": "ok",
                "confidence": 88,
                "related_atas": [],
                "suggestions": [],
            }

        def get_analytics(self, records):
            return {"total": len(records), "top_ata": []}

    class _DummyV10:
        def start_user_session(self, user_id: str) -> str:
            return "session-test"

        def process_query(self, query: str, session_id: str, user_id: str):
            return {
                "confidence": 0.8,
                "confidence_grade": "A",
                "primary_intent": "diagnostic",
                "secondary_intents": [],
                "language": "pt-BR",
            }

        def compose_response_package(self, query, result, operational_context, user_id):
            return {
                "response_text": "ok",
                "next_questions": [],
                "language_variant": "pt-BR",
                "response_sections": {},
                "chart_focus": {},
                "chart_brief": {},
                "suggested_visuals": [],
            }

    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=15000: sample_records)
    monkeypatch.setattr("routes_analytics.get_ai", lambda: _DummyAI())
    monkeypatch.setattr("routes_analytics.get_v10_engine", lambda: _DummyV10())
    monkeypatch.setattr(
        "routes_analytics._load_mel_context", lambda limit=400: [])
    monkeypatch.setattr(
        "routes_analytics._load_aog_context", lambda limit=400: [])
    monkeypatch.setattr(
        "routes_analytics._load_lru_context", lambda limit=700: [])
    monkeypatch.setattr("routes_analytics._load_tail_metrics", lambda: {})

    with app.test_request_context("/api/ai/chat", method="POST"):
        result = _ra._build_copilot_answer(query="E2A", scope="global")

    assert result["structured_query"]["tail_exact"] is True
    assert result["structured_query"]["fuzzy_enabled"] is False
    assert [str(item.get("tail"))
            for item in captured["records"]] == ["PR-E2A"]


def test_build_copilot_answer_treats_explicit_tail_filter_as_exact(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    sample_records = [
        {
            "id": 1,
            "tail": "PR-E2A",
            "ata": "29",
            "problema": "Hydraulic pressure fluctuation",
            "modelo": "E195-E2",
            "status_atual": "Open",
        },
        {
            "id": 2,
            "tail": "PR-E1B",
            "ata": "29",
            "problema": "Hydraulic pump low pressure",
            "modelo": "E190",
            "status_atual": "Open",
        },
    ]
    captured = {}

    class _DummyAI:
        def chat(self, query, records=None):
            captured["query"] = query
            captured["records"] = list(records or [])
            return {
                "response": "ok",
                "confidence": 88,
                "related_atas": [],
                "suggestions": [],
            }

        def get_analytics(self, records):
            return {"total": len(records), "top_ata": []}

    class _DummyV10:
        def start_user_session(self, user_id: str) -> str:
            return "session-test"

        def process_query(self, query: str, session_id: str, user_id: str):
            return {
                "confidence": 0.8,
                "confidence_grade": "A",
                "primary_intent": "diagnostic",
                "secondary_intents": [],
                "language": "pt-BR",
            }

        def compose_response_package(self, query, result, operational_context, user_id):
            return {
                "response_text": "ok",
                "next_questions": [],
                "language_variant": "pt-BR",
                "response_sections": {},
                "chart_focus": {},
                "chart_brief": {},
                "suggested_visuals": [],
            }

    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=15000: sample_records)
    monkeypatch.setattr("routes_analytics.get_ai", lambda: _DummyAI())
    monkeypatch.setattr("routes_analytics.get_v10_engine", lambda: _DummyV10())
    monkeypatch.setattr(
        "routes_analytics._load_mel_context", lambda limit=400: [])
    monkeypatch.setattr(
        "routes_analytics._load_aog_context", lambda limit=400: [])
    monkeypatch.setattr(
        "routes_analytics._load_lru_context", lambda limit=700: [])
    monkeypatch.setattr("routes_analytics._load_tail_metrics", lambda: {})

    with app.test_request_context("/api/ai/chat", method="POST"):
        result = _ra._build_copilot_answer(
            query="show hydraulic status",
            scope="global",
            tail_filter="PR-E2A",
        )

    assert result["structured_query"]["tail_exact"] is True
    assert result["structured_query"]["fuzzy_enabled"] is False


def test_build_copilot_answer_excludes_lru_without_ata_on_exact_ata_query(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    sample_records = [
        {
            "id": 1,
            "tail": "PR-E2A",
            "ata": "29",
            "problema": "Hydraulic pressure fluctuation",
            "modelo": "E195-E2",
            "status_atual": "Open",
        }
    ]

    class _DummyAI:
        def chat(self, query, records=None):
            return {
                "response": "ok",
                "confidence": 88,
                "related_atas": ["29"],
                "suggestions": [],
            }

        def get_analytics(self, records):
            return {"total": len(records), "top_ata": []}

    class _DummyV10:
        def start_user_session(self, user_id: str) -> str:
            return "session-test"

        def process_query(self, query: str, session_id: str, user_id: str):
            return {
                "confidence": 0.8,
                "confidence_grade": "A",
                "primary_intent": "diagnostic",
                "secondary_intents": [],
                "language": "pt-BR",
            }

        def compose_response_package(self, query, result, operational_context, user_id):
            return {
                "response_text": "ok",
                "next_questions": [],
                "language_variant": "pt-BR",
                "response_sections": {},
                "chart_focus": {},
                "chart_brief": {},
                "suggested_visuals": [],
            }

    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=15000: sample_records)
    monkeypatch.setattr("routes_analytics.get_ai", lambda: _DummyAI())
    monkeypatch.setattr("routes_analytics.get_v10_engine", lambda: _DummyV10())
    monkeypatch.setattr(
        "routes_analytics._load_mel_context", lambda limit=400: [])
    monkeypatch.setattr(
        "routes_analytics._load_aog_context", lambda limit=400: [])
    monkeypatch.setattr(
        "routes_analytics._load_lru_context",
        lambda limit=700: [
            {
                "id": 99,
                "acft_registration": "PR-E2A",
                "tail": "PR-E2A",
                "pn_off": "M21101",
                "pn_on": "M21101",
                "removal_reason": "Hydraulic pump replacement",
            }
        ],
    )
    monkeypatch.setattr("routes_analytics._load_tail_metrics", lambda: {})

    with app.test_request_context("/api/ai/chat", method="POST"):
        result = _ra._build_copilot_answer(
            query="ATA 29 hydraulic status",
            scope="global",
        )

    assert result["structured_query"]["ata_exact"] is True
    assert result["structured_query"]["fuzzy_enabled"] is False
    assert result["sources"]["lru"] == 0
    assert all(entry.get("source") != "lru" for entry in result["context_consulted"])


def test_build_copilot_answer_ignores_unrelated_memory_for_exact_ata_query(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    sample_records = [
        {
            "id": 1,
            "tail": "PR-E2A",
            "ata": "29",
            "problema": "Hydraulic pressure fluctuation",
            "modelo": "E195-E2",
            "status_atual": "Open",
        }
    ]
    captured = {}

    class _DummyAI:
        def chat(self, query, records=None):
            captured["query"] = query
            return {
                "response": "ok",
                "confidence": 88,
                "related_atas": ["29"],
                "suggestions": [],
            }

        def get_analytics(self, records):
            return {"total": len(records), "top_ata": []}

    class _DummyV10:
        def start_user_session(self, user_id: str) -> str:
            return "session-test"

        def process_query(self, query: str, session_id: str, user_id: str):
            return {
                "confidence": 0.8,
                "confidence_grade": "A",
                "primary_intent": "diagnostic",
                "secondary_intents": [],
                "language": "pt-BR",
            }

        def compose_response_package(self, query, result, operational_context, user_id):
            return {
                "response_text": "ok",
                "next_questions": [],
                "language_variant": "pt-BR",
                "response_sections": {},
                "chart_focus": {},
                "chart_brief": {},
                "suggested_visuals": [],
            }

    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=15000: sample_records)
    monkeypatch.setattr("routes_analytics.get_ai", lambda: _DummyAI())
    monkeypatch.setattr("routes_analytics.get_v10_engine", lambda: _DummyV10())
    monkeypatch.setattr(
        "routes_analytics._load_mel_context", lambda limit=400: [])
    monkeypatch.setattr(
        "routes_analytics._load_aog_context", lambda limit=400: [])
    monkeypatch.setattr(
        "routes_analytics._load_lru_context", lambda limit=700: [])
    monkeypatch.setattr("routes_analytics._load_tail_metrics", lambda: {})

    conversation_history = [
        {"type": "user", "text": "ATA 24 electrical issue on PR-E2C", "scope": "global", "sources": {}},
        {"type": "bot", "text": "ATA 24 electrical guidance for PR-E2C", "scope": "global", "sources": {"related_atas": ["24"], "tail_filter": "PR-E2C"}},
    ]

    with app.test_request_context("/api/ai/chat", method="POST"):
        result = _ra._build_copilot_answer(
            query="ATA 29 hydraulic status",
            scope="global",
            conversation_history=conversation_history,
        )

    assert result["structured_query"]["ata_exact"] is True
    assert result["memory_used"] is False
    assert "Context from recent conversation" not in captured["query"]
    assert "ATA 24" not in captured["query"]


def test_cleanup_preview_and_confirm_flow(tmp_path: Path) -> None:
    app = _build_test_app(tmp_path)

    (tmp_path / "_runtime_check.json").write_text("{}", encoding="utf-8")
    backup_dir = tmp_path / "Troubleshooting_Backup_20251113_085420"
    backup_dir.mkdir()
    (backup_dir / "note.txt").write_text("legacy", encoding="utf-8")

    client = app.test_client()

    preview = client.get("/api/system/cleanup/preview")
    assert preview.status_code == 200
    preview_payload = preview.get_json()
    assert preview_payload["success"] is True
    categories = preview_payload["data"]["categories"]
    assert "backup_directories" in categories
    assert "generated_artifacts" in categories

    no_confirm = client.post(
        "/api/system/cleanup",
        json={"categories": ["backup_directories"]},
    )
    assert no_confirm.status_code == 400
    no_confirm_payload = no_confirm.get_json()
    assert no_confirm_payload["success"] is False
    assert "confirm=true" in no_confirm_payload["error"]

    run_cleanup = client.post(
        "/api/system/cleanup",
        json={"confirm": True, "categories": [
            "backup_directories", "generated_artifacts"]},
    )
    assert run_cleanup.status_code == 200
    run_payload = run_cleanup.get_json()
    assert run_payload["success"] is True
    assert not backup_dir.exists()
    assert not (tmp_path / "_runtime_check.json").exists()
    assert isinstance(run_payload["data"].get("preview_after"), dict)
    assert "backup_directories" not in run_payload["data"]["preview_after"]["categories"]
    assert "generated_artifacts" not in run_payload["data"]["preview_after"]["categories"]


def test_ai_engine_ata_direct_includes_database_evidence() -> None:
    from ai_engine import TroubleshootingAI

    engine = TroubleshootingAI()
    records = [
        {
            "ata": "29",
            "tail": "PR-E2A",
            "modelo": "E195-E2",
            "status_atual": "Open",
        },
        {
            "ata": "29",
            "tail": "PR-E2A",
            "modelo": "E195-E2",
            "status_atual": "In Progress",
        },
        {
            "ata": "29",
            "tail": "PR-E1B",
            "modelo": "E190",
            "status_atual": "Closed",
        },
    ]

    result = engine.chat("ATA 29", records=records)

    assert result["type"] == "ata_detail"
    assert "Fleet Database Evidence" in result["response"]
    assert "Total records for ATA 29: **3**" in result["response"]
    assert "Open records: **2**" in result["response"]


def test_ai_engine_ata_direct_accepts_isolated_ata_number() -> None:
    from ai_engine import TroubleshootingAI

    engine = TroubleshootingAI()

    result = engine.chat("29", records=[])

    assert result["type"] == "ata_detail"
    assert "ATA 29" in result["response"]


def test_ai_chat_success_sets_request_id_header(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)

    monkeypatch.setattr(
        "routes_analytics._build_copilot_answer_with_retry",
        lambda **kwargs: {
            "response": "ok",
            "confidence": 70,
            "sources": {"records": 1},
        },
    )

    client = app.test_client()
    response = client.post(
        "/api/ai/chat",
        json={"query": "header test", "scope": "global"},
    )
    assert response.status_code == 200
    assert isinstance(response.headers.get("X-Request-Id"), str)
    assert response.headers.get("X-Request-Id").startswith("ai-chat-")


def test_ai_chat_rate_limit_sets_retry_after_header(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics._check_rate_limit", lambda ip: False)

    client = app.test_client()
    response = client.post(
        "/api/ai/chat",
        json={"query": "rate header", "scope": "global"},
    )
    assert response.status_code == 429
    retry_after = response.headers.get("Retry-After")
    assert isinstance(retry_after, str) and int(retry_after) > 0
    request_id = response.headers.get("X-Request-Id")
    assert isinstance(request_id, str) and request_id.startswith("ai-chat-")


def test_ai_chat_query_too_long_returns_contract_error(tmp_path: Path) -> None:
    app = _build_test_app(tmp_path)

    client = app.test_client()
    response = client.post(
        "/api/ai/chat",
        json={"query": "X" * 1100, "scope": "global"},
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["data"]["error_code"] == "query_too_long"
    assert payload["data"]["http_status"] == 400


def test_ai_chat_rate_limit_contract_has_retry_after(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics._check_rate_limit", lambda ip: False)

    client = app.test_client()
    response = client.post(
        "/api/ai/chat",
        json={"query": "ATA 29", "scope": "global"},
    )
    assert response.status_code == 429
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["data"]["error_code"] == "rate_limit_exceeded"
    assert payload["data"]["retry_after_seconds"] > 0
    assert payload["data"]["http_status"] == 429


def test_ai_chat_cache_status_hit_on_second_request(
    monkeypatch, tmp_path: Path
) -> None:
    app = _build_test_app(tmp_path)
    state = {"calls": 0}

    def _builder(**kwargs):
        state["calls"] += 1
        return {
            "response": "ok",
            "confidence": 70,
            "sources": {"records": 1},
        }

    monkeypatch.setattr(
        "routes_analytics._build_copilot_answer_with_retry", _builder)

    client = app.test_client()
    first = client.post(
        "/api/ai/chat",
        json={"query": "cache-hit-check-unique-20260329",
              "scope": "global", "deep_mode": False},
    )
    assert first.status_code == 200
    first_payload = first.get_json()
    assert first_payload["success"] is True
    assert first_payload["data"]["cache_status"] == "miss"
    assert first_payload["data"]["cached"] is False

    second = client.post(
        "/api/ai/chat",
        json={"query": "cache-hit-check-unique-20260329",
              "scope": "global", "deep_mode": False},
    )
    assert second.status_code == 200
    second_payload = second.get_json()
    assert second_payload["success"] is True
    assert second_payload["data"]["cache_status"] == "hit"
    assert second_payload["data"]["cached"] is True
    assert state["calls"] == 1


# ── P02 / 037-040 ─────────────────────────────────────────────────────────────


def test_detect_recurrence_alerts_uses_aware_utc_cutoff(
    monkeypatch, tmp_path: Path
) -> None:
    """037 — _detect_recurrence_alerts must not raise DeprecationWarning."""
    import warnings
    import routes_analytics as ra

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ra._detect_recurrence_alerts([], [], [])

    dep_warnings = [
        w for w in caught
        if issubclass(w.category, DeprecationWarning)
        and "utcnow" in str(w.message).lower()
    ]
    assert dep_warnings == [], "datetime.utcnow() DeprecationWarning still present"


def test_ai_copilot_success_has_scope_effective_and_input_normalized(
    monkeypatch, tmp_path: Path
) -> None:
    """038 — copilot success response carries scope_effective and input_normalized."""
    app = _build_test_app(tmp_path)

    def _ok(**kwargs):
        return {"response": "ok", "confidence": 80, "sources": {"records": 2}}

    monkeypatch.setattr(
        "routes_analytics._build_copilot_answer_with_retry", _ok)

    client = app.test_client()
    response = client.post(
        "/api/ai/copilot",
        json={"query": "ATA 28 fuel leak", "scope": "tail"},
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True
    assert payload["data"]["scope_effective"] == "tail"
    assert payload["data"]["input_normalized"] is True


def test_mission_queue_rejects_out_of_range_urgency_score(
    tmp_path: Path,
) -> None:
    """039 — POST /api/mission/queue with urgency_score > 10 returns 400."""
    app = _build_test_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/api/mission/queue",
        json={"tail": "PR-E2A", "ata": "29", "urgency_score": 99.9},
    )
    assert response.status_code == 400
    payload = response.get_json()
    assert payload["success"] is False
    assert payload["error_code"] == "invalid_urgency_score"
    assert payload["retryable"] is False


def test_mission_queue_post_then_get_integration(
    tmp_path: Path,
) -> None:
    """040 — POST a task then GET /api/mission/queue returns it."""
    app = _build_test_app(tmp_path)
    client = app.test_client()

    post_resp = client.post(
        "/api/mission/queue",
        json={
            "tail": "PR-E2A",
            "ata": "29",
            "urgency_score": 7.5,
            "action": "Inspect hydraulic actuator",
            "priority": "P2",
        },
    )
    assert post_resp.status_code == 201
    created = post_resp.get_json()
    assert created["success"] is True
    task_id = created["task"]["id"]
    assert task_id

    get_resp = client.get("/api/mission/queue")
    assert get_resp.status_code == 200
    queue = get_resp.get_json()
    assert queue["success"] is True
    ids = [t["id"] for t in queue["queue"]]
    assert task_id in ids


# ── P03 / 041-060 — Telemetria Frontend ───────────────────────────────────────


def _fresh_telemetry_app(tmp_path: Path) -> Flask:
    """Build test app with a clean telemetry store and reset rate limiter."""
    _ra._TELEMETRY_STORE.clear()
    _ra._RATE_STORE.clear()
    return _build_test_app(tmp_path)


_VALID_EVENT = {
    "event_type": "button_click",
    "page": "/menu",
    "session_id": "sess-abc-001",
}


def test_telemetry_post_event_returns_event_id(tmp_path: Path) -> None:
    """041 — POST /api/telemetry/event returns 201 with event_id."""
    app = _fresh_telemetry_app(tmp_path)
    r = app.test_client().post("/api/telemetry/event", json=_VALID_EVENT)
    assert r.status_code == 201
    p = r.get_json()
    assert p["success"] is True
    assert "event_id" in p and p["event_id"]


def test_telemetry_post_missing_event_type_returns_400(tmp_path: Path) -> None:
    """043 — event_type obrigatório."""
    app = _fresh_telemetry_app(tmp_path)
    r = app.test_client().post(
        "/api/telemetry/event",
        json={"page": "/menu", "session_id": "s1"},
    )
    assert r.status_code == 400
    assert r.get_json()["error_code"] == "missing_event_type"


def test_telemetry_post_missing_page_returns_400(tmp_path: Path) -> None:
    """043 — page obrigatória."""
    app = _fresh_telemetry_app(tmp_path)
    r = app.test_client().post(
        "/api/telemetry/event",
        json={"event_type": "button_click", "session_id": "s1"},
    )
    assert r.status_code == 400
    assert r.get_json()["error_code"] == "missing_page"


def test_telemetry_post_missing_session_id_returns_400(tmp_path: Path) -> None:
    """043 — session_id obrigatório."""
    app = _fresh_telemetry_app(tmp_path)
    r = app.test_client().post(
        "/api/telemetry/event",
        json={"event_type": "button_click", "page": "/menu"},
    )
    assert r.status_code == 400
    assert r.get_json()["error_code"] == "missing_session_id"


def test_telemetry_post_unknown_event_type_returns_400(tmp_path: Path) -> None:
    """050 — event_type fora do whitelist retorna 400."""
    app = _fresh_telemetry_app(tmp_path)
    r = app.test_client().post(
        "/api/telemetry/event",
        json={"event_type": "hacker_probe",
              "page": "/menu", "session_id": "s1"},
    )
    assert r.status_code == 400
    assert r.get_json()["error_code"] == "unknown_event_type"


def test_telemetry_event_has_server_ts(tmp_path: Path) -> None:
    """048 — evento armazenado contém server_ts."""
    app = _fresh_telemetry_app(tmp_path)
    app.test_client().post("/api/telemetry/event", json=_VALID_EVENT)
    r = app.test_client().get("/api/telemetry/events")
    events = r.get_json()["events"]
    assert len(events) == 1
    assert events[0]["server_ts"].endswith("Z")


def test_telemetry_get_events_returns_list(tmp_path: Path) -> None:
    """045 — GET /api/telemetry/events retorna lista."""
    app = _fresh_telemetry_app(tmp_path)
    app.test_client().post("/api/telemetry/event", json=_VALID_EVENT)
    r = app.test_client().get("/api/telemetry/events")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["count"] >= 1


def test_telemetry_get_events_filter_by_event_type(tmp_path: Path) -> None:
    """046 — filtro por event_type no GET."""
    app = _fresh_telemetry_app(tmp_path)
    c = app.test_client()
    c.post("/api/telemetry/event", json=_VALID_EVENT)
    c.post("/api/telemetry/event", json={
        "event_type": "page_view", "page": "/menu", "session_id": "s2"})
    r = c.get("/api/telemetry/events?event_type=page_view")
    events = r.get_json()["events"]
    assert all(e["event_type"] == "page_view" for e in events)


def test_telemetry_get_events_filter_by_page(tmp_path: Path) -> None:
    """047 — filtro por page no GET."""
    app = _fresh_telemetry_app(tmp_path)
    c = app.test_client()
    c.post("/api/telemetry/event", json=_VALID_EVENT)
    c.post("/api/telemetry/event", json={
        "event_type": "page_view", "page": "/fleet", "session_id": "s2"})
    r = c.get("/api/telemetry/events?page=/menu")
    events = r.get_json()["events"]
    assert all(e["page"] == "/menu" for e in events)


def test_telemetry_summary_counts_by_type(tmp_path: Path) -> None:
    """053 — GET /api/telemetry/summary retorna contagens por event_type."""
    app = _fresh_telemetry_app(tmp_path)
    c = app.test_client()
    c.post("/api/telemetry/event", json=_VALID_EVENT)
    c.post("/api/telemetry/event", json=_VALID_EVENT)
    c.post("/api/telemetry/event", json={
        "event_type": "page_view", "page": "/menu", "session_id": "s1"})
    r = c.get("/api/telemetry/summary")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["summary"]["button_click"] == 2
    assert p["summary"]["page_view"] == 1
    assert p["total"] == 3


def test_telemetry_delete_clears_store(tmp_path: Path) -> None:
    """054 — DELETE /api/telemetry/events limpa store."""
    app = _fresh_telemetry_app(tmp_path)
    c = app.test_client()
    c.post("/api/telemetry/event", json=_VALID_EVENT)
    del_r = c.delete("/api/telemetry/events")
    assert del_r.status_code == 200
    assert del_r.get_json()["removed"] == 1
    get_r = c.get("/api/telemetry/events")
    assert get_r.get_json()["count"] == 0


def test_telemetry_duration_ms_stored(tmp_path: Path) -> None:
    """058 — duration_ms opcional é armazenado."""
    app = _fresh_telemetry_app(tmp_path)
    c = app.test_client()
    payload = {**_VALID_EVENT, "duration_ms": 420.5}
    c.post("/api/telemetry/event", json=payload)
    events = c.get("/api/telemetry/events").get_json()["events"]
    assert events[0]["duration_ms"] == 420.5


def test_telemetry_negative_duration_ms_returns_400(tmp_path: Path) -> None:
    """058 — duration_ms negativo retorna 400."""
    app = _fresh_telemetry_app(tmp_path)
    r = app.test_client().post(
        "/api/telemetry/event",
        json={**_VALID_EVENT, "duration_ms": -1},
    )
    assert r.status_code == 400
    assert r.get_json()["error_code"] == "invalid_duration_ms"


def test_telemetry_user_agent_stored(tmp_path: Path) -> None:
    """057 — user_agent opcional é armazenado no evento."""
    app = _fresh_telemetry_app(tmp_path)
    c = app.test_client()
    c.post("/api/telemetry/event", json={
        **_VALID_EVENT, "user_agent": "Mozilla/5.0 (Test)"})
    events = c.get("/api/telemetry/events").get_json()["events"]
    assert "Mozilla" in events[0]["user_agent"]


def test_telemetry_invalid_json_returns_400(tmp_path: Path) -> None:
    """059 — payload não-JSON retorna 400 com error_code."""
    app = _fresh_telemetry_app(tmp_path)
    r = app.test_client().post(
        "/api/telemetry/event",
        data="not json",
        content_type="application/json",
    )
    assert r.status_code == 400
    assert r.get_json()["error_code"] == "invalid_payload"


def test_telemetry_store_is_isolated_between_tests(tmp_path: Path) -> None:
    """044/056 — store limpo entre testes via _fresh_telemetry_app."""
    app = _fresh_telemetry_app(tmp_path)
    r = app.test_client().get("/api/telemetry/events")
    assert r.get_json()["count"] == 0


def test_telemetry_label_sanitized_in_event(tmp_path: Path) -> None:
    """052 — campo label é sanitizado e armazenado."""
    app = _fresh_telemetry_app(tmp_path)
    c = app.test_client()
    c.post("/api/telemetry/event", json={
        **_VALID_EVENT, "label": "ATA 29 - Hydraulic"})
    events = c.get("/api/telemetry/events").get_json()["events"]
    assert events[0]["label"] == "ATA 29 - Hydraulic"


def test_telemetry_event_id_is_unique(tmp_path: Path) -> None:
    """049/055 — cada POST gera um event_id único."""
    app = _fresh_telemetry_app(tmp_path)
    c = app.test_client()
    r1 = c.post("/api/telemetry/event", json=_VALID_EVENT).get_json()
    r2 = c.post("/api/telemetry/event", json=_VALID_EVENT).get_json()
    assert r1["event_id"] != r2["event_id"]


def test_telemetry_summary_empty_store(tmp_path: Path) -> None:
    """053 — summary com store vazio retorna dict vazio e total 0."""
    app = _fresh_telemetry_app(tmp_path)
    r = app.test_client().get("/api/telemetry/summary")
    p = r.get_json()
    assert p["success"] is True
    assert p["summary"] == {}
    assert p["total"] == 0


# ── P04 / 061-080 — Log Estruturado e Correlação ──────────────────────────────


def _fresh_log_app(tmp_path: Path, monkeypatch=None) -> Flask:
    """Build test app with clean log + telemetry stores and reset rate limiter."""
    _ra._LOG_STORE.clear()
    _ra._TELEMETRY_STORE.clear()
    _ra._RATE_STORE.clear()
    app = _build_test_app(tmp_path)
    if monkeypatch is not None:
        monkeypatch.setattr(
            "routes_analytics._build_copilot_answer_with_retry",
            lambda **kw: {"response": "ok",
                          "confidence": 75, "sources": {"records": 1}},
        )
    return app


def test_log_entry_created_on_ai_chat(monkeypatch, tmp_path: Path) -> None:
    """061/062 — chamada a /api/ai/chat gera entrada no LOG_STORE."""
    app = _fresh_log_app(tmp_path, monkeypatch)
    app.test_client().post(
        "/api/ai/chat", json={"query": "ATA 29", "scope": "global"})
    assert len(_ra._LOG_STORE) >= 1
    entry = _ra._LOG_STORE[-1]
    assert entry["endpoint"] == "/api/ai/chat"
    assert entry["method"] == "POST"


def test_log_contains_status_code(monkeypatch, tmp_path: Path) -> None:
    """062/063 — log contém status_code da resposta."""
    app = _fresh_log_app(tmp_path, monkeypatch)
    app.test_client().post(
        "/api/ai/chat", json={"query": "ATA 29", "scope": "global"})
    entry = _ra._LOG_STORE[-1]
    assert entry["status_code"] == 200


def test_log_request_id_correlates_with_response_header(
    monkeypatch, tmp_path: Path
) -> None:
    """070 — request_id no log é igual ao X-Request-Id do header de resposta."""
    app = _fresh_log_app(tmp_path, monkeypatch)
    resp = app.test_client().post(
        "/api/ai/chat", json={"query": "ATA 29", "scope": "global"})
    header_rid = resp.headers.get("X-Request-Id")
    entry = _ra._LOG_STORE[-1]
    assert header_rid is not None
    assert entry["request_id"] == header_rid


def test_log_scope_captured_on_ai_chat(monkeypatch, tmp_path: Path) -> None:
    """073/079 — campo scope no log é preenchido para chat."""
    app = _fresh_log_app(tmp_path, monkeypatch)
    app.test_client().post(
        "/api/ai/chat", json={"query": "ATA 29", "scope": "tail"})
    entry = _ra._LOG_STORE[-1]
    assert entry["scope"] == "tail"


def test_log_processing_ms_captured(monkeypatch, tmp_path: Path) -> None:
    """063 — processing_ms extraído do body JSON e armazenado no log."""
    app = _fresh_log_app(tmp_path, monkeypatch)
    app.test_client().post(
        "/api/ai/chat", json={"query": "ATA 29", "scope": "global"})
    entry = _ra._LOG_STORE[-1]
    assert isinstance(entry["processing_ms"], (int, float))
    assert entry["processing_ms"] >= 0


def test_log_error_code_captured_on_400(tmp_path: Path) -> None:
    """069 — error_code preenchido no log quando response é erro."""
    _ra._LOG_STORE.clear()
    _ra._RATE_STORE.clear()
    app = _build_test_app(tmp_path)
    app.test_client().post(
        "/api/ai/chat", json={"query": "", "scope": "global"})
    entry = _ra._LOG_STORE[-1]
    assert entry["status_code"] == 400
    assert entry["error_code"] == "query_required"


def test_log_get_lists_entries(monkeypatch, tmp_path: Path) -> None:
    """065 — GET /api/logs retorna entradas registradas."""
    app = _fresh_log_app(tmp_path, monkeypatch)
    c = app.test_client()
    c.post("/api/ai/chat", json={"query": "ATA 29", "scope": "global"})
    r = c.get("/api/logs")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["count"] >= 1


def test_log_filter_by_endpoint(monkeypatch, tmp_path: Path) -> None:
    """066 — filtro por endpoint retorna apenas entradas daquele endpoint."""
    app = _fresh_log_app(tmp_path, monkeypatch)
    c = app.test_client()
    c.post("/api/ai/chat", json={"query": "ATA 29", "scope": "global"})
    c.post("/api/telemetry/event", json=_VALID_EVENT)
    r = c.get("/api/logs?endpoint=/api/ai/chat")
    entries = r.get_json()["logs"]
    assert all(e["endpoint"] == "/api/ai/chat" for e in entries)


def test_log_filter_by_status_code(monkeypatch, tmp_path: Path) -> None:
    """067/078 — filtro por status_code retorna apenas entradas com aquele código."""
    app = _fresh_log_app(tmp_path, monkeypatch)
    c = app.test_client()
    c.post("/api/ai/chat", json={"query": "ATA 29", "scope": "global"})
    c.post("/api/ai/chat", json={"query": "", "scope": "global"})
    r = c.get("/api/logs?status_code=400")
    entries = r.get_json()["logs"]
    assert all(e["status_code"] == 400 for e in entries)
    assert len(entries) >= 1


def test_log_filter_by_error_code(tmp_path: Path) -> None:
    """076 — filtro por error_code."""
    _ra._LOG_STORE.clear()
    _ra._RATE_STORE.clear()
    app = _build_test_app(tmp_path)
    c = app.test_client()
    c.post("/api/ai/chat", json={"query": "", "scope": "global"})
    r = c.get("/api/logs?error_code=query_required")
    entries = r.get_json()["logs"]
    assert len(entries) >= 1
    assert all(e["error_code"] == "query_required" for e in entries)


def test_log_summary_counts_by_endpoint(monkeypatch, tmp_path: Path) -> None:
    """068/080 — GET /api/logs/summary retorna contagens por endpoint."""
    app = _fresh_log_app(tmp_path, monkeypatch)
    c = app.test_client()
    c.post("/api/ai/chat", json={"query": "ATA 29", "scope": "global"})
    c.post("/api/ai/chat", json={"query": "ATA 28", "scope": "global"})
    r = c.get("/api/logs/summary")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["summary"].get("/api/ai/chat", 0) >= 2


def test_log_delete_clears_store(monkeypatch, tmp_path: Path) -> None:
    """071 — DELETE /api/logs limpa o store."""
    app = _fresh_log_app(tmp_path, monkeypatch)
    c = app.test_client()
    c.post("/api/ai/chat", json={"query": "ATA 29", "scope": "global"})
    del_r = c.delete("/api/logs")
    assert del_r.status_code == 200
    assert del_r.get_json()["removed"] >= 1
    get_r = c.get("/api/logs")
    assert get_r.get_json()["count"] == 0


def test_log_server_ts_present(monkeypatch, tmp_path: Path) -> None:
    """062 — server_ts presente em cada entrada de log."""
    app = _fresh_log_app(tmp_path, monkeypatch)
    app.test_client().post(
        "/api/ai/chat", json={"query": "ATA 29", "scope": "global"})
    entry = _ra._LOG_STORE[-1]
    assert entry["server_ts"].endswith("Z")


def test_log_cached_flag_on_cache_hit(monkeypatch, tmp_path: Path) -> None:
    """074 — campo cached no log é True na segunda requisição (cache hit)."""
    app = _fresh_log_app(tmp_path, monkeypatch)
    c = app.test_client()
    unique_q = "p04-cache-hit-unique-2026"
    c.post("/api/ai/chat",
           json={"query": unique_q, "scope": "global", "deep_mode": False})
    _ra._LOG_STORE.clear()
    c.post("/api/ai/chat",
           json={"query": unique_q, "scope": "global", "deep_mode": False})
    entry = _ra._LOG_STORE[-1]
    assert entry["cached"] is True


def test_log_no_query_field_in_entry(monkeypatch, tmp_path: Path) -> None:
    """075 — log NÃO expõe o campo query (dados sensíveis não vazam)."""
    app = _fresh_log_app(tmp_path, monkeypatch)
    app.test_client().post(
        "/api/ai/chat", json={"query": "ATA 29 secret", "scope": "global"})
    entry = _ra._LOG_STORE[-1]
    assert "query" not in entry


def test_log_telemetry_endpoint_also_logged(tmp_path: Path) -> None:
    """061 — eventos de /api/telemetry/event também são logados."""
    _ra._LOG_STORE.clear()
    _ra._TELEMETRY_STORE.clear()
    _ra._RATE_STORE.clear()
    app = _build_test_app(tmp_path)
    app.test_client().post("/api/telemetry/event", json=_VALID_EVENT)
    endpoints_logged = [e["endpoint"] for e in _ra._LOG_STORE]
    assert "/api/telemetry/event" in endpoints_logged


# ── P07 UI Preferences ────────────────────────────────────────────────────────

def test_ui_prefs_get_returns_defaults(tmp_path: Path) -> None:
    """121 — GET /api/ui/prefs retorna defaults sem prefs salvas."""
    _ra._UI_PREFS_STORE.clear()
    _ra._RATE_STORE.clear()
    c = _build_test_app(tmp_path).test_client()
    r = c.get("/api/ui/prefs")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["prefs"]["table_density"] == "normal"
    assert p["prefs"]["language"] == "pt"
    assert p["prefs"]["page_size"] == 50


def test_ui_prefs_post_saves_density(tmp_path: Path) -> None:
    """122 — POST /api/ui/prefs salva table_density."""
    _ra._UI_PREFS_STORE.clear()
    _ra._RATE_STORE.clear()
    c = _build_test_app(tmp_path).test_client()
    r = c.post("/api/ui/prefs", json={"table_density": "compact"})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["prefs"]["table_density"] == "compact"
    assert "table_density" in p["saved_keys"]


def test_ui_prefs_post_invalid_density_returns_400(tmp_path: Path) -> None:
    """123 — POST com table_density inválido retorna 400."""
    _ra._RATE_STORE.clear()
    c = _build_test_app(tmp_path).test_client()
    r = c.post("/api/ui/prefs", json={"table_density": "xlarge"})
    assert r.status_code == 400
    assert "invalid" in r.get_json()["error"].lower()


def test_ui_prefs_post_invalid_language_returns_400(tmp_path: Path) -> None:
    """124 — POST com language inválido retorna 400."""
    _ra._RATE_STORE.clear()
    c = _build_test_app(tmp_path).test_client()
    r = c.post("/api/ui/prefs", json={"language": "zh"})
    assert r.status_code == 400


def test_ui_prefs_reset_restores_defaults(tmp_path: Path) -> None:
    """125 — DELETE /api/ui/prefs/reset restaura defaults."""
    _ra._UI_PREFS_STORE.clear()
    _ra._RATE_STORE.clear()
    c = _build_test_app(tmp_path).test_client()
    c.post("/api/ui/prefs",
           json={"table_density": "compact", "dark_mode": True})
    r = c.delete("/api/ui/prefs/reset")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["prefs"]["table_density"] == "normal"
    assert p["prefs"]["dark_mode"] is False


def test_ui_config_has_version_v12(tmp_path: Path) -> None:
    """126 — GET /api/ui/config retorna versão v12."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/ui/config")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["config"]["version"] == "v12"
    assert "features" in p["config"]
    assert "limits" in p["config"]


def test_ui_render_hints_has_is_mobile(tmp_path: Path) -> None:
    """127 — GET /api/ui/render-hints retorna campo is_mobile."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/ui/render-hints")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "is_mobile" in p["hints"]


# ── P08 AI Copilot V12 ────────────────────────────────────────────────────────

def test_ai_explain_returns_explanation(tmp_path: Path) -> None:
    """141 — POST /api/ai/explain retorna explanation."""
    _ra._EXPLAIN_STORE.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/ai/explain", json={"ata": "29", "tail": "PR-E2A"})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "explanation" in p
    assert "29" in p["explanation"]


def test_ai_explain_missing_ata_returns_400(tmp_path: Path) -> None:
    """142 — POST /api/ai/explain sem ata retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/ai/explain", json={"tail": "PR-E2A"})
    assert r.status_code == 400


def test_ai_explain_stored_in_explain_store(tmp_path: Path) -> None:
    """143 — POST /api/ai/explain armazena no _EXPLAIN_STORE."""
    _ra._EXPLAIN_STORE.clear()
    _ra._RATE_STORE.clear()
    _build_test_app(tmp_path).test_client().post(
        "/api/ai/explain", json={"ata": "44"})
    assert len(_ra._EXPLAIN_STORE) == 1
    assert _ra._EXPLAIN_STORE[-1]["ata"] == "44"


def test_ai_chat_export_returns_list(tmp_path: Path) -> None:
    """144 — GET /api/ai/chat/export retorna lista."""
    _ra._EXPLAIN_STORE.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/ai/chat/export")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert isinstance(p["history"], list)
    assert p["count"] == 0


def test_ai_semantic_score_basic(tmp_path: Path) -> None:
    """145 — GET /api/ai/semantic-score?q=hydraulic retorna score."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/ai/semantic-score?q=hydraulic+pressure+29")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "semantic_score" in p
    assert p["semantic_score"] > 0


def test_ai_semantic_score_missing_q_returns_400(tmp_path: Path) -> None:
    """146 — GET /api/ai/semantic-score sem q retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/ai/semantic-score")
    assert r.status_code == 400


# ── P09 Forecast V12 ──────────────────────────────────────────────────────────

def test_forecast_predict_basic(tmp_path: Path) -> None:
    """161 — POST /api/forecast/predict retorna risk."""
    _ra._FORECAST_STORE.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/forecast/predict", json={"tail": "PR-E2A", "ata": "29", "fh": 12000})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["risk"] == "high"
    assert "ttf_fh" in p


def test_forecast_predict_missing_tail_returns_400(tmp_path: Path) -> None:
    """162 — POST sem tail retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/forecast/predict", json={"ata": "29", "fh": 5000})
    assert r.status_code == 400


def test_forecast_risk_score_empty_tail(tmp_path: Path) -> None:
    """163 — GET /api/forecast/risk/score sem histórico retorna risk_score 0."""
    _ra._FORECAST_STORE.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/forecast/risk/score?tail=PR-NENHUM")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["risk_score"] == 0


def test_forecast_risk_score_after_high_fh(tmp_path: Path) -> None:
    """164 — risk_score > 0 após predição com fh alto."""
    _ra._FORECAST_STORE.clear()
    _ra._RATE_STORE.clear()
    c = _build_test_app(tmp_path).test_client()
    c.post("/api/forecast/predict",
           json={"tail": "PR-TEST", "ata": "29", "fh": 15000})
    r = c.get("/api/forecast/risk/score?tail=PR-TEST")
    assert r.get_json()["risk_score"] > 0


# ── P10 Mission Console V12 ───────────────────────────────────────────────────

def test_mission_auto_prioritize_sorts_by_priority(tmp_path: Path) -> None:
    """181 — POST /api/mission/auto-prioritize ordena por prioridade."""
    _ra._RATE_STORE.clear()
    issues = [
        {"id": 1, "prioridade": "low", "status": "open", "eta_hours": 10},
        {"id": 2, "prioridade": "high", "status": "open", "eta_hours": 2},
        {"id": 3, "prioridade": "medium", "status": "open", "eta_hours": 5},
    ]
    r = _build_test_app(tmp_path).test_client().post(
        "/api/mission/auto-prioritize", json={"issues": issues})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["prioritized"][0]["id"] == 2  # high first


def test_mission_auto_prioritize_no_issues_returns_400(tmp_path: Path) -> None:
    """182 — POST sem issues retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/mission/auto-prioritize", json={})
    assert r.status_code == 400


def test_mission_status_bulk_basic(tmp_path: Path) -> None:
    """183 — POST /api/mission/status/bulk muda status."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/mission/status/bulk", json={"ids": [1, 2, 3], "status": "closed"})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["updated"] == 3


def test_mission_status_bulk_invalid_status_returns_400(tmp_path: Path) -> None:
    """184 — POST com status inválido retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/mission/status/bulk", json={"ids": [1], "status": "banana"})
    assert r.status_code == 400


# ── P11 Exceedance Analysis V12 ───────────────────────────────────────────────

def test_exceedance_root_cause_basic(tmp_path: Path) -> None:
    """201 — POST /api/exceedance/root-cause retorna root_cause."""
    _ra._EXCEEDANCE_STORE.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/exceedance/root-cause",
        json={"event_id": "EVT-001", "tail": "PR-E2A", "ata": "29"})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "root_cause" in p
    assert "confidence" in p


def test_exceedance_root_cause_missing_event_id_returns_400(tmp_path: Path) -> None:
    """202 — POST sem event_id retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/exceedance/root-cause", json={"tail": "PR-E2A"})
    assert r.status_code == 400


def test_exceedance_similar_returns_list(tmp_path: Path) -> None:
    """203 — POST /api/exceedance/similar retorna lista."""
    _ra._EXCEEDANCE_STORE.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/exceedance/similar", json={"ata": "29"})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert isinstance(p["similar"], list)


def test_exceedance_similar_finds_after_root_cause(tmp_path: Path) -> None:
    """204 — similar encontra evento pós root-cause."""
    _ra._EXCEEDANCE_STORE.clear()
    _ra._RATE_STORE.clear()
    c = _build_test_app(tmp_path).test_client()
    c.post("/api/exceedance/root-cause",
           json={"event_id": "EVT-002", "tail": "PR-TEST", "ata": "34"})
    r = c.post("/api/exceedance/similar", json={"ata": "34"})
    p = r.get_json()
    assert p["count"] >= 1
    assert p["similar"][0]["ata"] == "34"


# ── P12 Security Hardening ────────────────────────────────────────────────────

def test_security_audit_returns_log_list(tmp_path: Path) -> None:
    """221 — GET /api/security/audit retorna lista de log."""
    _ra._SECURITY_LOG.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/security/audit")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert isinstance(p["log"], list)


def test_security_validate_clean_input(tmp_path: Path) -> None:
    """222 — POST texto limpo retorna is_clean True."""
    _ra._SECURITY_LOG.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/security/validate-input",
        json={"text": "hydraulic pressure anomaly on ATA 29"})
    assert r.status_code == 200
    p = r.get_json()
    assert p["is_clean"] is True
    assert p["is_suspicious"] is False


def test_security_validate_xss_detected(tmp_path: Path) -> None:
    """223 — POST com <script> detecta como suspeito."""
    _ra._SECURITY_LOG.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/security/validate-input",
        json={"text": "<script>alert('xss')</script>"})
    assert r.status_code == 200
    p = r.get_json()
    assert p["is_suspicious"] is True
    assert p["is_clean"] is False


def test_security_validate_sql_injection_detected(tmp_path: Path) -> None:
    """224 — POST com union select detecta como suspeito."""
    _ra._SECURITY_LOG.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/security/validate-input",
        json={"text": "'; union select * from users --"})
    assert r.status_code == 200
    assert r.get_json()["is_suspicious"] is True


def test_security_validate_missing_text_returns_400(tmp_path: Path) -> None:
    """225 — POST sem text retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/security/validate-input", json={})
    assert r.status_code == 400


# ── P13 UX States ─────────────────────────────────────────────────────────────

def test_ux_states_get_returns_empty(tmp_path: Path) -> None:
    """241 — GET /api/ux/states retorna estado vazio."""
    _ra._UX_STATE_STORE.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/ux/states")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["state"] == {}


def test_ux_states_post_saves_key(tmp_path: Path) -> None:
    """242 — POST salva chave-valor."""
    _ra._UX_STATE_STORE.clear()
    _ra._RATE_STORE.clear()
    c = _build_test_app(tmp_path).test_client()
    r = c.post("/api/ux/states",
               json={"sidebar_open": True, "active_tab": "fleet"})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "sidebar_open" in p["saved_keys"]


def test_ux_states_get_returns_saved_state(tmp_path: Path) -> None:
    """243 — GET após POST retorna estado salvo."""
    _ra._UX_STATE_STORE.clear()
    _ra._RATE_STORE.clear()
    c = _build_test_app(tmp_path).test_client()
    c.post("/api/ux/states", json={"my_key": "my_value"})
    r = c.get("/api/ux/states")
    assert r.get_json()["state"].get("my_key") == "my_value"


def test_ux_layout_has_sidebar_width(tmp_path: Path) -> None:
    """244 — GET /api/ux/layout tem campo sidebar_width."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/ux/layout")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["layout"]["sidebar_width"] == 260


# ── P14 Accessibility Config ──────────────────────────────────────────────────

def test_a11y_config_has_wcag_aa(tmp_path: Path) -> None:
    """261 — GET /api/a11y/config tem wcag_level=AA."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/a11y/config")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["a11y"]["wcag_level"] == "AA"
    assert p["a11y"]["keyboard_nav"] is True


def test_a11y_feedback_accepted(tmp_path: Path) -> None:
    """262 — POST /api/a11y/feedback registra issue."""
    _ra._A11Y_FEEDBACK.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/a11y/feedback",
        json={"issue": "button not focusable", "element": "#submit-btn"})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["received"] is True


def test_a11y_feedback_missing_issue_returns_400(tmp_path: Path) -> None:
    """263 — POST sem issue retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/a11y/feedback", json={})
    assert r.status_code == 400


# ── P15 i18n Messages ─────────────────────────────────────────────────────────

def test_i18n_messages_pt(tmp_path: Path) -> None:
    """281 — GET /api/i18n/messages?lang=pt retorna loading em PT."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/i18n/messages?lang=pt")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "loading" in p["messages"]
    assert "Carregando" in p["messages"]["loading"]


def test_i18n_messages_en(tmp_path: Path) -> None:
    """282 — GET /api/i18n/messages?lang=en retorna loading em EN."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/i18n/messages?lang=en")
    p = r.get_json()
    assert "Loading" in p["messages"]["loading"]


def test_i18n_languages_list_has_three(tmp_path: Path) -> None:
    """283 — GET /api/i18n/languages retorna pt, en, es."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/i18n/languages")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert set(p["languages"]) == {"pt", "en", "es"}


# ── P21 ATA Recommendation ────────────────────────────────────────────────────

def test_ata_recommend_hydraulic(tmp_path: Path) -> None:
    """401 — GET /api/ata/recommend?symptom=hydraulic → ATA 29."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/ata/recommend?symptom=hydraulic+pressure+loss")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["recommended_ata"] == "29"


def test_ata_recommend_unknown_symptom(tmp_path: Path) -> None:
    """402 — sintoma desconhecido → recommended_ata None."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/ata/recommend?symptom=unknown+xyz+abc")
    p = r.get_json()
    assert p["recommended_ata"] is None
    assert p["confidence"] == 0


def test_ata_chapters_contains_44(tmp_path: Path) -> None:
    """403 — GET /api/ata/chapters contém capítulo 44."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/ata/chapters")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "44" in p["chapters"]
    assert p["chapters"]["44"] == "Cabin Systems"


# ── P22 Operational Risk ──────────────────────────────────────────────────────

def test_ops_risk_computes_score(tmp_path: Path) -> None:
    """421 — POST /api/ops/risk retorna score e level."""
    _ra._RISK_STORE.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/ops/risk",
        json={"tail": "PR-E2A", "open_issues": 5, "mel_count": 2, "fh": 8000})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "score" in p
    assert p["level"] in {"low", "medium", "high", "critical"}


def test_ops_risk_missing_tail_returns_400(tmp_path: Path) -> None:
    """422 — POST sem tail retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/ops/risk", json={"open_issues": 3})
    assert r.status_code == 400


def test_ops_risk_history_empty(tmp_path: Path) -> None:
    """423 — GET /api/ops/risk/history sem dados retorna lista vazia."""
    _ra._RISK_STORE.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/ops/risk/history?tail=PR-NENHUM")
    assert r.status_code == 200
    p = r.get_json()
    assert p["history"] == []


# ── P23 Bulk Workflows ────────────────────────────────────────────────────────

def test_bulk_recommend_basic(tmp_path: Path) -> None:
    """441 — POST /api/bulk/recommend retorna recomendações."""
    _ra._RATE_STORE.clear()
    issues = [{"tail": "PR-E2A", "ata": "29"}, {"tail": "PR-E1B", "ata": "34"}]
    r = _build_test_app(tmp_path).test_client().post(
        "/api/bulk/recommend", json={"issues": issues})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["count"] == 2
    assert len(p["results"]) == 2


def test_bulk_recommend_over_limit_returns_400(tmp_path: Path) -> None:
    """442 — POST com >20 issues retorna 400."""
    _ra._RATE_STORE.clear()
    issues = [{"tail": f"PR-{i}", "ata": "29"} for i in range(21)]
    r = _build_test_app(tmp_path).test_client().post(
        "/api/bulk/recommend", json={"issues": issues})
    assert r.status_code == 400


def test_bulk_close_basic(tmp_path: Path) -> None:
    """443 — POST /api/bulk/close retorna contagem fechada."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/bulk/close", json={"ids": [10, 20, 30]})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["closed"] == 3


# ── P24 Health Extended ───────────────────────────────────────────────────────

def test_health_extended_returns_healthy(tmp_path: Path) -> None:
    """461 — GET /api/health/extended retorna status healthy."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/health/extended")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["status"] == "healthy"


def test_health_extended_has_checks(tmp_path: Path) -> None:
    """462 — /api/health/extended tem cache, metrics_store, telemetry_store."""
    _ra._RATE_STORE.clear()
    p = _build_test_app(tmp_path).test_client().get(
        "/api/health/extended").get_json()
    checks = p["checks"]
    assert "cache" in checks
    assert "metrics_store" in checks
    assert "telemetry_store" in checks


def test_health_startup_ready(tmp_path: Path) -> None:
    """463 — GET /api/health/startup retorna ready True."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/health/startup")
    assert r.status_code == 200
    p = r.get_json()
    assert p["ready"] is True
    assert p["version"] == "v12"


# ── P25 Version / Changelog ───────────────────────────────────────────────────

def test_version_returns_v12(tmp_path: Path) -> None:
    """481 — GET /api/version retorna v12.0.0."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/version")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["version"] == "v12.0.0"


def test_changelog_returns_list(tmp_path: Path) -> None:
    """482 — GET /api/changelog retorna lista."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/changelog")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert isinstance(p["changelog"], list)
    assert len(p["changelog"]) >= 1


def test_changelog_limit_param(tmp_path: Path) -> None:
    """483 — GET /api/changelog?limit=1 retorna exatamente 1."""
    _ra._RATE_STORE.clear()
    p = _build_test_app(tmp_path).test_client().get(
        "/api/changelog?limit=1").get_json()
    assert p["count"] == 1
    assert len(p["changelog"]) == 1


# ── P26 IA Guardrails V2 ──────────────────────────────────────────────────────

def test_guardrails_check_clean_text(tmp_path: Path) -> None:
    """501 — POST texto limpo → risk_level low, passed True."""
    _ra._GUARDRAIL_LOG.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/ia/guardrails/check",
        json={"text": "ATA 29 hydraulic pressure fluctuation"})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["risk_level"] == "low"
    assert p["passed"] is True


def test_guardrails_check_risky_term(tmp_path: Path) -> None:
    """502 — POST com 'emergency grounded' → risk_level high."""
    _ra._GUARDRAIL_LOG.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/ia/guardrails/check",
        json={"text": "aircraft emergency grounded due to hull loss concern"})
    p = r.get_json()
    assert p["risk_level"] == "high"
    assert p["passed"] is False


def test_guardrails_log_after_check(tmp_path: Path) -> None:
    """503 — GET /api/ia/guardrails/log retorna entradas após check."""
    _ra._GUARDRAIL_LOG.clear()
    _ra._RATE_STORE.clear()
    c = _build_test_app(tmp_path).test_client()
    c.post("/api/ia/guardrails/check", json={"text": "test input"})
    r = c.get("/api/ia/guardrails/log")
    assert r.status_code == 200
    p = r.get_json()
    assert p["count"] >= 1


# ── P27 IA Context Memory ─────────────────────────────────────────────────────

def test_ia_context_set_and_get(tmp_path: Path) -> None:
    """521 — POST /api/ia/context e GET retorna contexto salvo."""
    _ra._IA_CONTEXT_STORE.clear()
    _ra._RATE_STORE.clear()
    c = _build_test_app(tmp_path).test_client()
    c.post("/api/ia/context", json={"ata": "44", "scope": "cabin"})
    r = c.get("/api/ia/context")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["context"].get("ata") == "44"


def test_ia_context_clear(tmp_path: Path) -> None:
    """522 — DELETE /api/ia/context/clear limpa contexto."""
    _ra._IA_CONTEXT_STORE.clear()
    _ra._RATE_STORE.clear()
    c = _build_test_app(tmp_path).test_client()
    c.post("/api/ia/context", json={"data": "something"})
    del_r = c.delete("/api/ia/context/clear")
    assert del_r.get_json()["cleared"] is True
    get_r = c.get("/api/ia/context")
    assert get_r.get_json()["context"] == {}


def test_ia_context_too_large_returns_413(tmp_path: Path) -> None:
    """523 — POST payload enorme retorna 413."""
    _ra._IA_CONTEXT_STORE.clear()
    _ra._RATE_STORE.clear()
    big = {"data": "x" * 9000}
    r = _build_test_app(tmp_path).test_client().post(
        "/api/ia/context", json=big)
    assert r.status_code == 413


# ── P28 IA Actions ────────────────────────────────────────────────────────────

def test_ia_actions_suggest_mel_context(tmp_path: Path) -> None:
    """541 — POST com contexto MEL sugere escalate_mel."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/ia/actions/suggest",
        json={"context": "MEL item open on ATA 29, needs review"})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    ids = [s["action_id"] for s in p["suggestions"]]
    assert "escalate_mel" in ids


def test_ia_actions_execute_valid_action(tmp_path: Path) -> None:
    """542 — POST com action_id válido retorna executed True."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/ia/actions/execute",
        json={"action_id": "create_work_order"})
    assert r.status_code == 200
    p = r.get_json()
    assert p["executed"] is True
    assert p["action_id"] == "create_work_order"


def test_ia_actions_execute_invalid_action_returns_400(tmp_path: Path) -> None:
    """543 — POST com action_id inválido retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/ia/actions/execute",
        json={"action_id": "destroy_database"})
    assert r.status_code == 400


# ── P29 IA Reliability + ATA Disambiguation ───────────────────────────────────

def test_primary_ata_from_query_finds_44() -> None:
    """561 — _primary_ata_from_query('ATA 44') retorna '44'."""
    result = _ra._primary_ata_from_query("check ATA 44 cabin systems")
    assert result == "44"


def test_primary_ata_from_query_returns_none_for_no_ata() -> None:
    """562 — _primary_ata_from_query sem ATA retorna None."""
    result = _ra._primary_ata_from_query(
        "hydraulic pressure issue in the fleet")
    assert result is None


def test_ata_response_drift_detected() -> None:
    """563 — _check_ata_response_drift detecta desvio ATA 44→49."""
    drifted, found = _ra._check_ata_response_drift(
        "This relates to ATA 49 APU startup issue.", "44")
    assert drifted is True
    assert "49" in found


def test_ata_response_drift_not_detected_clean() -> None:
    """564 — _check_ata_response_drift sem desvio retorna False."""
    drifted, found = _ra._check_ata_response_drift(
        "ATA 44 cabin entertainment system issue.", "44")
    assert drifted is False


def test_ia_reliability_structure(tmp_path: Path) -> None:
    """565 — GET /api/ia/reliability retorna grounding_rate_pct."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/ia/reliability")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "grounding_rate_pct" in p["reliability"]
    assert "drift_rate_pct" in p["reliability"]


def test_ia_ata_grounding_report_returns_entries(tmp_path: Path) -> None:
    """566 — GET /api/ia/ata-grounding/report retorna entries e stats."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/ia/ata-grounding/report")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "entries" in p
    assert "stats" in p


# ── P30 IA Explainability ─────────────────────────────────────────────────────

def test_ia_explain_feature_basic(tmp_path: Path) -> None:
    """581 — POST /api/ia/explain/feature retorna feature_importances."""
    _ra._FEATURE_EXPLANATIONS.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/ia/explain/feature",
        json={"recommendation_id": "REC-001",
              "features": ["ata", "fh", "tail"]})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "feature_importances" in p
    assert "ata" in p["feature_importances"]


def test_ia_explain_feature_missing_id_returns_400(tmp_path: Path) -> None:
    """582 — POST sem recommendation_id retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/ia/explain/feature", json={"features": ["ata"]})
    assert r.status_code == 400


def test_ia_explain_history_returns_list(tmp_path: Path) -> None:
    """583 — GET /api/ia/explain/history retorna lista."""
    _ra._FEATURE_EXPLANATIONS.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/ia/explain/history")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert isinstance(p["history"], list)


# ── P31 Forecast Enhanced ─────────────────────────────────────────────────────

def test_forecast_component_wear_basic(tmp_path: Path) -> None:
    """601 — POST /api/forecast/component/wear retorna wear_pct."""
    _ra._WEAR_PREDICTIONS.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/forecast/component/wear",
        json={"component": "hydraulic_pump", "cycles": 5000, "fh": 8000})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "wear_pct" in p
    assert "recommend_replacement" in p


def test_forecast_component_wear_missing_component_returns_400(tmp_path: Path) -> None:
    """602 — POST sem component retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/forecast/component/wear", json={"cycles": 1000, "fh": 3000})
    assert r.status_code == 400


def test_forecast_fleet_summary_structure(tmp_path: Path) -> None:
    """603 — GET /api/forecast/fleet/summary tem risk_distribution."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/forecast/fleet/summary")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "risk_distribution" in p["forecast_summary"]
    assert "total_forecasts" in p["forecast_summary"]


# ── P32 Investigation Engine ──────────────────────────────────────────────────

def test_investigate_start_returns_inv_id(tmp_path: Path) -> None:
    """621 — POST /api/investigate/start retorna investigation_id."""
    _ra._INVESTIGATION_STORE.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/investigate/start",
        json={"issue_id": "ISS-001", "ata": "29"})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "investigation_id" in p
    assert len(p["investigation_id"]) > 0


def test_investigate_status_by_id(tmp_path: Path) -> None:
    """622 — GET /api/investigate/status retorna investigação pelo id."""
    _ra._INVESTIGATION_STORE.clear()
    _ra._RATE_STORE.clear()
    c = _build_test_app(tmp_path).test_client()
    start = c.post("/api/investigate/start",
                   json={"issue_id": "ISS-002"}).get_json()
    inv_id = start["investigation_id"]
    r = c.get(f"/api/investigate/status?investigation_id={inv_id}")
    assert r.status_code == 200
    p = r.get_json()
    assert p["investigation_id"] == inv_id


def test_investigate_status_not_found_returns_404(tmp_path: Path) -> None:
    """623 — id inexistente retorna 404."""
    _ra._INVESTIGATION_STORE.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/investigate/status?investigation_id=nonexistent999")
    assert r.status_code == 404


# ── P33 Maintenance Score ─────────────────────────────────────────────────────

def test_maintenance_score_computes(tmp_path: Path) -> None:
    """641 — POST /api/maintenance/score retorna score e readiness."""
    _ra._MAINTENANCE_SCORE_STORE.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/maintenance/score",
        json={"tail": "PR-E2A", "overdue_tasks": 0,
              "pending_mels": 0, "last_c_check_days": 0})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["score"] == 100
    assert p["readiness"] == "excellent"


def test_maintenance_score_missing_tail_returns_400(tmp_path: Path) -> None:
    """642 — POST sem tail retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/maintenance/score", json={"overdue_tasks": 2})
    assert r.status_code == 400


def test_maintenance_history_empty(tmp_path: Path) -> None:
    """643 — GET /api/maintenance/history sem dados retorna lista vazia."""
    _ra._MAINTENANCE_SCORE_STORE.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/maintenance/history?tail=PR-NENHUM")
    assert r.status_code == 200
    p = r.get_json()
    assert p["history"] == []


# ── P34 HITL Review ───────────────────────────────────────────────────────────

def test_hitl_review_approved(tmp_path: Path) -> None:
    """661 — POST /api/hitl/review verdict=approved."""
    _ra._HITL_STORE.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/hitl/review",
        json={"item_id": "ITEM-001", "verdict": "approved",
              "comment": "Looks good"})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["verdict"] == "approved"
    assert p["reviewed"] is True


def test_hitl_review_invalid_verdict_returns_400(tmp_path: Path) -> None:
    """662 — POST com verdict inválido retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/hitl/review",
        json={"item_id": "ITEM-002", "verdict": "maybe"})
    assert r.status_code == 400


def test_hitl_pending_list(tmp_path: Path) -> None:
    """663 — GET /api/hitl/pending lista revisões pendentes."""
    _ra._HITL_STORE.clear()
    _ra._RATE_STORE.clear()
    c = _build_test_app(tmp_path).test_client()
    c.post("/api/hitl/review",
           json={"item_id": "ITEM-003", "verdict": "needs_revision"})
    r = c.get("/api/hitl/pending")
    assert r.status_code == 200
    p = r.get_json()
    assert p["count"] >= 1
    assert p["pending"][0]["verdict"] == "needs_revision"


# ── P35 Governance Metrics ────────────────────────────────────────────────────

def test_governance_metrics_structure(tmp_path: Path) -> None:
    """681 — GET /api/governance/metrics retorna campos de governança."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/governance/metrics")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    gov = p["governance"]
    assert "flagged_responses" in gov
    assert "security_events" in gov
    assert "hitl_approved" in gov
    assert "guardrail_invocations" in gov


def test_governance_flag_basic(tmp_path: Path) -> None:
    """682 — POST /api/governance/flag sinaliza resposta."""
    _ra._GOVERNANCE_FLAGS.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/governance/flag",
        json={"response_id": "RESP-001",
              "reason": "ATA drift detected in response"})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["flagged"] is True
    assert p["entry"]["response_id"] == "RESP-001"


def test_governance_flag_missing_reason_returns_400(tmp_path: Path) -> None:
    """683 — POST sem reason retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/governance/flag",
        json={"response_id": "RESP-002"})
    assert r.status_code == 400


def test_log_copilot_endpoint_logged(monkeypatch, tmp_path: Path) -> None:
    """062 — chamada a /api/ai/copilot também é logada."""
    app = _fresh_log_app(tmp_path, monkeypatch)
    app.test_client().post(
        "/api/ai/copilot", json={"query": "ATA 29", "scope": "global"})
    endpoints = [e["endpoint"] for e in _ra._LOG_STORE]
    assert "/api/ai/copilot" in endpoints


# ── P05 / 081-100 — Qualidade e Normalização de Dados ─────────────────────────


def _fresh_quality_app(tmp_path: Path) -> Flask:
    """Build test app with clean quality + rate-limit stores."""
    _ra._QUALITY_STORE.clear()
    _ra._RATE_STORE.clear()
    return _build_test_app(tmp_path)


def test_normalize_tail_uppercase(tmp_path: Path) -> None:
    """081 — tail normalizado para uppercase sem espaços."""
    assert _ra._normalize_tail("pt-mee") == "PT-MEE"
    assert _ra._normalize_tail("  PP-XYZ  ") == "PP-XYZ"


def test_normalize_tail_removes_invalid_chars(tmp_path: Path) -> None:
    """081 — tail normalizado remove caracteres inválidos."""
    assert _ra._normalize_tail("PP XYZ!") == "PPXYZ"


def test_normalize_tail_max_length(tmp_path: Path) -> None:
    """081 — tail truncado em 20 caracteres."""
    assert len(_ra._normalize_tail("A" * 30)) == 20


def test_normalize_ata_two_parts(tmp_path: Path) -> None:
    """082 — ATA com 2 partes formatado como XX-XX."""
    assert _ra._normalize_ata("29-10") == "29-10"
    assert _ra._normalize_ata("5-3") == "05-03"


def test_normalize_ata_three_parts(tmp_path: Path) -> None:
    """082 — ATA com 3 partes formatado como XX-XX-XX."""
    assert _ra._normalize_ata("29-10-1") == "29-10-01"


def test_normalize_ata_single(tmp_path: Path) -> None:
    """082 — ATA com 1 parte formatado como XX."""
    assert _ra._normalize_ata("29") == "29"


def test_normalize_status_maps_pt_to_en(tmp_path: Path) -> None:
    """083 — status em português mapeado para inglês canônico."""
    assert _ra._normalize_status("Aberto") == "open"
    assert _ra._normalize_status("Fechado") == "closed"
    assert _ra._normalize_status("Em andamento") == "in_progress"


def test_validate_record_missing_fields(tmp_path: Path) -> None:
    """084/092 — _validate_data_record detecta campos obrigatórios ausentes."""
    errors = _ra._validate_data_record({})
    for field in ("tail", "ata", "description"):
        assert any(field in e for e in errors)


def test_validate_record_description_too_long(tmp_path: Path) -> None:
    """093 — _validate_data_record detecta descrição muito longa."""
    rec = {"tail": "PP-XYZ", "ata": "29-10", "description": "x" * 5001}
    errors = _ra._validate_data_record(rec)
    assert any("field_too_long" in e for e in errors)


def test_validate_record_invalid_ata(tmp_path: Path) -> None:
    """094 — _validate_data_record detecta ATA com formato inválido."""
    rec = {"tail": "PP-XYZ", "ata": "INVALID", "description": "test"}
    errors = _ra._validate_data_record(rec)
    assert any("invalid_ata_format" in e for e in errors)


def test_validate_record_valid(tmp_path: Path) -> None:
    """084 — _validate_data_record sem erros para registro válido."""
    rec = {"tail": "PP-XYZ", "ata": "29-10", "description": "Hydraulic leak"}
    assert _ra._validate_data_record(rec) == []


def test_normalize_endpoint_returns_normalized_tail(tmp_path: Path) -> None:
    """086/087 — POST /api/data/normalize normaliza tail no response."""
    app = _fresh_quality_app(tmp_path)
    r = app.test_client().post(
        "/api/data/normalize", json={"tail": "pt-mee", "ata": "29-10", "description": "ok"})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["normalized"]["tail"] == "PT-MEE"


def test_normalize_endpoint_records_quality_event(tmp_path: Path) -> None:
    """089/091 — normalização registra evento no QUALITY_STORE."""
    app = _fresh_quality_app(tmp_path)
    app.test_client().post(
        "/api/data/normalize", json={"tail": "pt-mee", "description": "ok"})
    assert len(_ra._QUALITY_STORE) >= 1
    assert "tail" in _ra._QUALITY_STORE[-1]["fields_changed"]


def test_normalize_endpoint_no_changes_no_quality_event(tmp_path: Path) -> None:
    """089 — sem alterações, nenhum evento de qualidade registrado."""
    app = _fresh_quality_app(tmp_path)
    app.test_client().post(
        "/api/data/normalize", json={"tail": "PP-XYZ", "ata": "29-10"})
    assert len(_ra._QUALITY_STORE) == 0


def test_normalize_strips_control_chars(tmp_path: Path) -> None:
    """099 — normalize remove caracteres de controle da descrição."""
    app = _fresh_quality_app(tmp_path)
    r = app.test_client().post(
        "/api/data/normalize",
        json={"description": "text\x00with\x01control", "tail": "PP-XYZ"})
    p = r.get_json()
    assert "\x00" not in p["normalized"]["description"]
    assert "\x01" not in p["normalized"]["description"]


def test_validate_endpoint_returns_errors(tmp_path: Path) -> None:
    """090/091 — POST /api/data/validate retorna erros de validação."""
    app = _fresh_quality_app(tmp_path)
    r = app.test_client().post("/api/data/validate", json={"tail": "PP-XYZ"})
    p = r.get_json()
    assert p["success"] is True
    assert p["valid"] is False
    assert p["error_count"] > 0


def test_validate_endpoint_valid_record(tmp_path: Path) -> None:
    """090 — POST /api/data/validate retorna valid True para registro correto."""
    app = _fresh_quality_app(tmp_path)
    r = app.test_client().post(
        "/api/data/validate",
        json={"tail": "PP-XYZ", "ata": "29-10", "description": "ok"})
    p = r.get_json()
    assert p["valid"] is True
    assert p["error_count"] == 0


def test_quality_stats_counts_fields(tmp_path: Path) -> None:
    """096/097/098 — GET /api/data/quality retorna contagens por campo."""
    app = _fresh_quality_app(tmp_path)
    c = app.test_client()
    c.post("/api/data/normalize", json={"tail": "pt-mee"})
    c.post("/api/data/normalize", json={"tail": "pp-abc"})
    r = c.get("/api/data/quality")
    p = r.get_json()
    assert p["success"] is True
    assert p["field_counts"].get("tail", 0) >= 2


def test_quality_delete_clears_store(tmp_path: Path) -> None:
    """098 — DELETE /api/data/quality limpa o store."""
    app = _fresh_quality_app(tmp_path)
    c = app.test_client()
    c.post("/api/data/normalize", json={"tail": "pt-mee"})
    del_r = c.delete("/api/data/quality")
    assert del_r.get_json()["removed"] >= 1
    assert c.get(
        "/api/data/quality").get_json()["total_normalization_events"] == 0


# ── P06 / 101-120 — Otimização de API ─────────────────────────────────────────


def _fresh_metrics_app(tmp_path: Path) -> Flask:
    """Build test app com stores de métricas e rate-limit limpos."""
    _ra._METRICS_STORE.clear()
    _ra._METRICS_LOCK_STORE.clear()
    _ra._RATE_STORE.clear()
    return _build_test_app(tmp_path)


def test_health_endpoint_returns_ok(tmp_path: Path) -> None:
    """106 — GET /api/health retorna status ok."""
    _ra._RATE_STORE.clear()
    app = _build_test_app(tmp_path)
    r = app.test_client().get("/api/health")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["status"] == "ok"


def test_health_endpoint_has_stores_info(tmp_path: Path) -> None:
    """107 — GET /api/health inclui tamanho dos stores."""
    _ra._RATE_STORE.clear()
    app = _build_test_app(tmp_path)
    r = app.test_client().get("/api/health")
    p = r.get_json()
    assert "stores" in p
    assert "telemetry" in p["stores"]
    assert "logs" in p["stores"]


def test_record_api_metric_stores_latency(tmp_path: Path) -> None:
    """101/102 — _record_api_metric armazena latência no METRICS_STORE."""
    _ra._METRICS_STORE.clear()
    _ra._METRICS_LOCK_STORE.clear()
    _ra._record_api_metric("/api/test", 42.5, 200)
    assert "/api/test" in _ra._METRICS_STORE
    assert _ra._METRICS_STORE["/api/test"] == [42.5]


def test_record_api_metric_increments_error_count(tmp_path: Path) -> None:
    """103 — _record_api_metric incrementa error_count para status >= 400."""
    _ra._METRICS_STORE.clear()
    _ra._METRICS_LOCK_STORE.clear()
    _ra._record_api_metric("/api/test", 10.0, 400)
    assert _ra._METRICS_LOCK_STORE["/api/test"] == 1


def test_metrics_endpoint_returns_endpoint_stats(monkeypatch, tmp_path: Path) -> None:
    """108/109 — GET /api/metrics retorna estatísticas por endpoint."""
    app = _fresh_metrics_app(tmp_path)
    c = app.test_client()
    c.post("/api/ai/chat", json={"query": "ATA 29", "scope": "global"})
    r = c.get("/api/metrics")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "/api/ai/chat" in p["metrics"]


def test_metrics_endpoint_has_percentiles(monkeypatch, tmp_path: Path) -> None:
    """110/111/112 — métricas contêm p50, p95, avg_ms, max_ms."""
    app = _fresh_metrics_app(tmp_path)
    c = app.test_client()
    c.post("/api/ai/chat", json={"query": "ATA 29", "scope": "global"})
    p = c.get("/api/metrics").get_json()
    stats = p["metrics"].get("/api/ai/chat", {})
    assert "p50_ms" in stats
    assert "p95_ms" in stats
    assert "avg_ms" in stats
    assert "max_ms" in stats


def test_metrics_filter_by_endpoint(monkeypatch, tmp_path: Path) -> None:
    """113 — filtro ?endpoint= retorna apenas aquele endpoint."""
    app = _fresh_metrics_app(tmp_path)
    c = app.test_client()
    c.post("/api/ai/chat", json={"query": "ATA 29", "scope": "global"})
    r = c.get("/api/metrics?endpoint=/api/ai/chat")
    p = r.get_json()
    assert list(p["metrics"].keys()) == ["/api/ai/chat"]


def test_metrics_error_count_incremented_on_400(tmp_path: Path) -> None:
    """103/114 — error_count incrementado para respostas de erro."""
    app = _fresh_metrics_app(tmp_path)
    c = app.test_client()
    c.post("/api/ai/chat", json={"query": "", "scope": "global"})
    p = c.get("/api/metrics").get_json()
    assert p["metrics"]["/api/ai/chat"]["error_count"] >= 1


def test_metrics_delete_clears_store(monkeypatch, tmp_path: Path) -> None:
    """116 — DELETE /api/metrics limpa todos os stores de métricas."""
    app = _fresh_metrics_app(tmp_path)
    c = app.test_client()
    c.post("/api/ai/chat", json={"query": "ATA 29", "scope": "global"})
    del_r = c.delete("/api/metrics")
    assert del_r.get_json()["removed_endpoints"] >= 1
    # O próprio GET /api/metrics é telemetrado; validamos que /api/ai/chat foi removido.
    get_r = c.get("/api/metrics?endpoint=/api/ai/chat")
    assert get_r.get_json()["endpoint_count"] == 0


def test_cache_stats_returns_size(tmp_path: Path) -> None:
    """117/118 — GET /api/cache/stats retorna cache_size."""
    _ra._RATE_STORE.clear()
    app = _build_test_app(tmp_path)
    r = app.test_client().get("/api/cache/stats")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert isinstance(p["cache_size"], int)
    assert p["cache_enabled"] is True


def test_cache_clear_returns_success(tmp_path: Path) -> None:
    """119/120 — DELETE /api/cache/clear retorna success True."""
    _ra._RATE_STORE.clear()
    app = _build_test_app(tmp_path)
    r = app.test_client().delete("/api/cache/clear")
    assert r.status_code == 200
    assert r.get_json()["success"] is True


def test_metrics_max_200_per_endpoint(tmp_path: Path) -> None:
    """104 — METRICS_STORE mantém no máximo 200 entradas por endpoint."""
    _ra._METRICS_STORE.clear()
    _ra._METRICS_LOCK_STORE.clear()
    for i in range(250):
        _ra._record_api_metric("/api/test", float(i), 200)
    assert len(_ra._METRICS_STORE["/api/test"]) == 200


# ══════════════════════════════════════════════════════════════════════════════
# P36 — AOG Inline Field Edit API  (IDs 701-720)
# ══════════════════════════════════════════════════════════════════════════════

def test_aog_update_field_invalid_field_returns_400(tmp_path):
    """701 — POST com field inválido retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/aog/1/update_field",
        json={"field": "injected_bad_field", "value": "test"})
    assert r.status_code == 400
    assert r.get_json()["success"] is False


def test_aog_update_field_missing_field_returns_400(tmp_path):
    """702 — POST sem field retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/aog/1/update_field",
        json={"value": "test value"})
    assert r.status_code == 400


def test_aog_update_field_too_long_value_returns_400(tmp_path):
    """703 — POST com valor acima de 2000 chars retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/aog/1/update_field",
        json={"field": "ata", "value": "x" * 2001})
    assert r.status_code == 400


def test_aog_update_field_success_returns_200(monkeypatch, tmp_path):
    """704A — POST válido atualiza campo e registra auditoria."""
    _ra._RATE_STORE.clear()
    _ra._AOG_FIELD_AUDIT.clear()

    class _Cursor:
        def __init__(self):
            self.rowcount = 1

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params):
            self.query = query
            self.params = params

    class _Conn:
        def cursor(self):
            return _Cursor()

        def commit(self):
            return None

        def close(self):
            return None

    monkeypatch.setattr(_ra, "_db_connect", lambda: _Conn())

    r = _build_test_app(tmp_path).test_client().post(
        "/api/aog/1/update_field",
        json={"field": "location", "value": "GRU"},
    )

    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["record_id"] == 1
    assert p["field"] == "location"
    assert p["value"] == "GRU"
    assert _ra._AOG_FIELD_AUDIT[-1]["record_id"] == 1


def test_aog_update_field_not_found_returns_404(monkeypatch, tmp_path):
    """704B — rowcount=0 retorna registro não encontrado/released."""
    _ra._RATE_STORE.clear()

    class _Cursor:
        def __init__(self):
            self.rowcount = 0

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params):
            self.query = query
            self.params = params

    class _Conn:
        def cursor(self):
            return _Cursor()

        def commit(self):
            return None

        def close(self):
            return None

    monkeypatch.setattr(_ra, "_db_connect", lambda: _Conn())

    r = _build_test_app(tmp_path).test_client().post(
        "/api/aog/999/update_field",
        json={"field": "location", "value": "GRU"},
    )

    assert r.status_code == 404
    p = r.get_json()
    assert p["success"] is False
    assert "not found" in p["error"].lower()


def test_aog_update_field_db_connection_error_returns_503(monkeypatch, tmp_path):
    """704C — falha de conexão MySQL retorna 503 específico."""
    _ra._RATE_STORE.clear()

    def _raise_operational_error():
        raise _ra.pymysql.OperationalError(2003, "connection failed")

    monkeypatch.setattr(_ra, "_db_connect", _raise_operational_error)

    r = _build_test_app(tmp_path).test_client().post(
        "/api/aog/1/update_field",
        json={"field": "location", "value": "GRU"},
    )

    assert r.status_code == 503
    p = r.get_json()
    assert p["success"] is False
    assert p["error"] == "db_connection_error"


def test_aog_field_audit_returns_structure(tmp_path):
    """704 — GET /api/aog/field_audit retorna estrutura esperada."""
    _ra._AOG_FIELD_AUDIT.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/aog/field_audit")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "total" in p
    assert "entries" in p
    assert isinstance(p["entries"], list)


def test_aog_field_audit_limit_param(tmp_path):
    """705 — GET /api/aog/field_audit?limit= aceita parâmetro."""
    _ra._AOG_FIELD_AUDIT.clear()
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/aog/field_audit?limit=10")
    assert r.status_code == 200
    assert r.get_json()["success"] is True


def test_allowed_aog_fields_whitelist_defined():
    """706 — _ALLOWED_AOG_FIELDS contém campos esperados."""
    expected = {"interruption_type", "fail_code", "location", "ata",
                "event_description", "maintenance_actions"}
    assert expected == _ra._ALLOWED_AOG_FIELDS


# ── End P36 Tests ─────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# P37 — Predictive AOG Duration Estimator  (IDs 721-740)
# ══════════════════════════════════════════════════════════════════════════════

def test_aog_predict_duration_returns_prediction(tmp_path):
    """721 — GET /api/aog/predict_duration retorna predicted_hours."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/aog/predict_duration?ata=32")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "predicted_hours" in p
    assert isinstance(p["predicted_hours"], (int, float))


def test_aog_predict_duration_confidence_low_without_db(tmp_path):
    """722 — Sem DB, confidence é low."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/aog/predict_duration?ata=72")
    p = r.get_json()
    assert p["success"] is True
    assert p["confidence"] == "low"


def test_aog_predict_duration_uses_baseline(tmp_path):
    """723 — ATA=72 usa baseline de 72 horas."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/aog/predict_duration?ata=72")
    p = r.get_json()
    assert p["baseline_hours"] == 72.0


def test_aog_duration_stats_returns_success(tmp_path):
    """724 — GET /api/aog/duration_stats retorna success."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/aog/duration_stats")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "stats" in p


# ── End P37 Tests ─────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# P38 — Fleet Availability Score  (IDs 741-760)
# ══════════════════════════════════════════════════════════════════════════════

def test_fleet_availability_score_returns_structure(tmp_path):
    """741 — GET /api/fleet/availability_score retorna estrutura completa."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/fleet/availability_score")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "availability_pct" in p
    assert "fleet_total" in p
    assert "status" in p


def test_fleet_availability_trend_returns_list(tmp_path):
    """742 — GET /api/fleet/availability_trend retorna trend list."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/fleet/availability_trend")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "trend" in p
    assert isinstance(p["trend"], list)


# ── End P38 Tests ─────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# P39 — Maintenance Backlog Intelligence  (IDs 761-780)
# ══════════════════════════════════════════════════════════════════════════════

def test_maintenance_backlog_intelligence_returns_structure(tmp_path):
    """761 — GET /api/maintenance/backlog_intelligence retorna campos."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/maintenance/backlog_intelligence")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "total_open" in p
    assert "critical" in p
    assert "backlog_risk" in p


def test_maintenance_backlog_by_tail_returns_list(tmp_path):
    """762 — GET /api/maintenance/backlog_by_tail retorna lista."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/maintenance/backlog_by_tail")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "backlog" in p


# ── End P39 Tests ─────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# P40 — ATA Hot Spot Detector  (IDs 781-800)
# ══════════════════════════════════════════════════════════════════════════════

def test_ata_hotspots_returns_list(tmp_path):
    """781 — GET /api/analytics/ata_hotspots retorna hotspots list."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/ata_hotspots")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "hotspots" in p
    assert "days_analyzed" in p


def test_ata_hotspots_days_param(tmp_path):
    """782 — GET /api/analytics/ata_hotspots?days=30 aceita param."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/ata_hotspots?days=30")
    assert r.status_code == 200
    assert r.get_json()["days_analyzed"] == 30


def test_ata_hotspots_trend_missing_ata_returns_400(tmp_path):
    """783 — GET /api/analytics/ata_hotspots/trend sem ata retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/ata_hotspots/trend")
    assert r.status_code == 400


def test_ata_hotspots_trend_with_ata_returns_success(tmp_path):
    """784 — GET /api/analytics/ata_hotspots/trend?ata=32 retorna success."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/ata_hotspots/trend?ata=32")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["ata"] == "32"
    assert "trend" in p


# ── End P40 Tests ─────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# P41 — Cost per Tail Calculator  (IDs 801-820)
# ══════════════════════════════════════════════════════════════════════════════

def test_cost_per_tail_returns_structure(tmp_path):
    """801 — GET /api/analytics/cost_per_tail retorna estrutura."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/cost_per_tail")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "cost_per_tail" in p
    assert "cost_rate_usd_per_hour" in p


def test_total_aog_cost_returns_structure(tmp_path):
    """802 — GET /api/analytics/total_aog_cost retorna campos numéricos."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/total_aog_cost")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "total_aog_events" in p
    assert "total_estimated_cost_usd" in p
    assert isinstance(p["total_estimated_cost_usd"], (int, float))


# ── End P41 Tests ─────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# P42 — MEL Utilization Tracker  (IDs 821-840)
# ══════════════════════════════════════════════════════════════════════════════

def test_mel_utilization_tracker_returns_structure(tmp_path):
    """821 — GET /api/mel/utilization_tracker retorna campos esperados."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/mel/utilization_tracker")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "total_mel" in p
    assert "open_count" in p
    assert "utilization_rate_pct" in p


def test_mel_expiring_soon_returns_structure(tmp_path):
    """822 — GET /api/mel/expiring_soon retorna estrutura."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get("/api/mel/expiring_soon")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "count" in p
    assert "items" in p
    assert isinstance(p["items"], list)


def test_mel_expiring_soon_days_param(tmp_path):
    """823 — GET /api/mel/expiring_soon?days=7 aceita param."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/mel/expiring_soon?days=7")
    assert r.status_code == 200
    p = r.get_json()
    assert p["expiring_within_days"] == 7


# ── End P42 Tests ─────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# P43 — Repeat Failure Detector  (IDs 841-860)
# ══════════════════════════════════════════════════════════════════════════════

def test_repeat_failures_returns_structure(tmp_path):
    """841 — GET /api/analytics/repeat_failures retorna campos."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/repeat_failures")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "repeat_failures" in p
    assert "days_analyzed" in p
    assert "high_risk_count" in p


def test_repeat_failures_days_param(tmp_path):
    """842 — GET /api/analytics/repeat_failures?days=30 aceita param."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/repeat_failures?days=30")
    assert r.status_code == 200
    assert r.get_json()["days_analyzed"] == 30


def test_repeat_failures_by_tail_missing_tail_returns_400(tmp_path):
    """843 — GET /api/analytics/repeat_failures/tail sem tail retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/repeat_failures/tail")
    assert r.status_code == 400


def test_repeat_failures_by_tail_with_tail(tmp_path):
    """844 — GET /api/analytics/repeat_failures/tail?tail=PP-ABX retorna success."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/repeat_failures/tail?tail=PP-ABX")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["tail"] == "PP-ABX"


# ── End P43 Tests ─────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# P44 — Dispatch Reliability Score  (IDs 861-880)
# ══════════════════════════════════════════════════════════════════════════════

def test_dispatch_reliability_returns_structure(tmp_path):
    """861 — GET /api/analytics/dispatch_reliability retorna lista."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/dispatch_reliability")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "dispatch_reliability" in p
    assert isinstance(p["dispatch_reliability"], list)


def test_dispatch_reliability_fleet_returns_structure(tmp_path):
    """862 — GET /api/analytics/dispatch_reliability/fleet retorna score."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/dispatch_reliability/fleet")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "fleet_reliability_score" in p
    assert isinstance(p["fleet_reliability_score"], (int, float))


# ── End P44 Tests ─────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# P45 — Ground Time Efficiency Index  (IDs 881-900)
# ══════════════════════════════════════════════════════════════════════════════

def test_ground_time_efficiency_returns_structure(tmp_path):
    """881 — GET /api/analytics/ground_time_efficiency retorna campos."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/ground_time_efficiency")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "efficiency_pct" in p
    assert "target_hours" in p
    assert "efficiency_grade" in p


def test_ground_time_efficiency_by_ata_returns_list(tmp_path):
    """882 — GET /api/analytics/ground_time_efficiency/by_ata retorna lista."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/ground_time_efficiency/by_ata")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "by_ata" in p
    assert isinstance(p["by_ata"], list)


# ── End P45 Tests ─────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# P46 — Seasonal Failure Pattern Detector  (IDs 901-920)
# ══════════════════════════════════════════════════════════════════════════════

def test_seasonal_patterns_returns_structure(tmp_path):
    """901 — GET /api/analytics/seasonal_patterns retorna monthly_patterns."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/seasonal_patterns")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "monthly_patterns" in p
    assert "analysis_period_months" in p


def test_seasonal_patterns_ata_missing_ata_returns_400(tmp_path):
    """902 — GET /api/analytics/seasonal_patterns/ata sem ata retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/seasonal_patterns/ata")
    assert r.status_code == 400


def test_seasonal_patterns_ata_with_ata(tmp_path):
    """903 — GET /api/analytics/seasonal_patterns/ata?ata=29 retorna dados."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/seasonal_patterns/ata?ata=29")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["ata"] == "29"
    assert "seasonal_data" in p


# ── End P46 Tests ─────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# P47 — Parts Availability Risk Index  (IDs 921-940)
# ══════════════════════════════════════════════════════════════════════════════

def test_parts_risk_index_returns_structure(tmp_path):
    """921 — GET /api/analytics/parts_risk_index retorna parts_risk."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/parts_risk_index")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "parts_risk" in p
    assert "critical_count" in p


def test_parts_risk_by_ata_returns_list(tmp_path):
    """922 — GET /api/analytics/parts_risk_index/by_ata retorna lista."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/parts_risk_index/by_ata")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "by_ata" in p
    assert isinstance(p["by_ata"], list)


# ── End P47 Tests ─────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# P48 — Technician Workload Estimator  (IDs 941-960)
# ══════════════════════════════════════════════════════════════════════════════

def test_workload_estimate_returns_structure(tmp_path):
    """941 — GET /api/analytics/workload_estimate retorna total_estimated_hours."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/workload_estimate")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "total_estimated_hours" in p
    assert "full_time_technicians_needed" in p
    assert "workload_by_ata" in p


def test_workload_estimate_by_tail_missing_returns_400(tmp_path):
    """942 — GET /api/analytics/workload_estimate/tail sem tail retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/workload_estimate/tail")
    assert r.status_code == 400


def test_workload_estimate_by_tail_with_tail(tmp_path):
    """943 — GET /api/analytics/workload_estimate/tail?tail=PP-XYZ retorna success."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/analytics/workload_estimate/tail?tail=PP-XYZ")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["tail"] == "PP-XYZ"
    assert "estimated_hours" in p


# ── End P48 Tests ─────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# P49 — AI Dispatch Risk Score  (IDs 961-980)
# ══════════════════════════════════════════════════════════════════════════════

def test_dispatch_risk_missing_tail_returns_400(tmp_path):
    """961 — POST /api/ai/dispatch_risk sem tail retorna 400."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/ai/dispatch_risk", json={})
    assert r.status_code == 400


def test_dispatch_risk_returns_structure(tmp_path):
    """962 — POST /api/ai/dispatch_risk retorna risk_level e score."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/ai/dispatch_risk", json={"tail": "PP-XYZ"})
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "dispatch_risk_score" in p
    assert "risk_level" in p
    assert "recommendation" in p
    assert isinstance(p["dispatch_risk_score"], (int, float))


def test_dispatch_risk_score_bounded(tmp_path):
    """963 — Score sempre entre 0 e 100."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().post(
        "/api/ai/dispatch_risk", json={"tail": "PP-TEST"})
    p = r.get_json()
    assert 0 <= p["dispatch_risk_score"] <= 100


def test_dispatch_risk_fleet_returns_list(tmp_path):
    """964 — GET /api/ai/dispatch_risk/fleet retorna at_risk_fleet."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/ai/dispatch_risk/fleet")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "at_risk_fleet" in p
    assert "at_risk_count" in p


# ── End P49 Tests ─────────────────────────────────────────────────────────────


# ══════════════════════════════════════════════════════════════════════════════
# P50 — V12 Final Quality Gate  (IDs 981-1000)
# ══════════════════════════════════════════════════════════════════════════════

def test_v12_health_gate_returns_certified(tmp_path):
    """981 — GET /api/system/v12_health_gate retorna v12_certified."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/system/v12_health_gate")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert "v12_certified" in p
    assert "packages_implemented" in p
    assert p["packages_implemented"] == 50
    assert p["total_improvements"] == 1000


def test_v12_health_gate_checks_passed(tmp_path):
    """982 — v12_health_gate checks_passed >= checks_failed."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/system/v12_health_gate")
    p = r.get_json()
    assert p["checks_passed"] >= p["checks_failed"]


def test_v12_health_gate_version(tmp_path):
    """983 — v12_health_gate retorna version 12.0."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/system/v12_health_gate")
    p = r.get_json()
    assert p["version"] == "12.0"


def test_v12_package_registry_returns_50_packages(tmp_path):
    """984 — GET /api/system/v12_package_registry retorna 50 pacotes."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/system/v12_package_registry")
    assert r.status_code == 200
    p = r.get_json()
    assert p["success"] is True
    assert p["total_packages"] == 50
    assert p["total_improvements"] == 1000
    assert len(p["packages"]) == 50


def test_v12_package_registry_contains_all_ids(tmp_path):
    """985 — Registro contém P01 a P50."""
    _ra._RATE_STORE.clear()
    r = _build_test_app(tmp_path).test_client().get(
        "/api/system/v12_package_registry")
    p = r.get_json()
    ids = {pkg["id"] for pkg in p["packages"]}
    assert "P01" in ids
    assert "P50" in ids
    assert len(ids) == 50


# ── End P50 Tests ─────────────────────────────────────────────────────────────
