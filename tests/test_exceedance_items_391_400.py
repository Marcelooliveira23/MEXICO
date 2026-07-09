"""Test suite for items 391-400: Final wave of exceedance analysis improvements."""

import io
import json
from pathlib import Path
import pytest


def _build_test_app(tmp_path: Path):
    """Build test Flask app with temporary paths."""
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent))

    (tmp_path / "exceedance_workspaces").mkdir(exist_ok=True)
    (tmp_path / "uploads").mkdir(exist_ok=True)
    (tmp_path / "tails_fallback.json").write_text(
        json.dumps([{"tail": "N12345", "fh": 5000.0, "fc": 3000}]), encoding="utf-8"
    )

    from flask import Flask
    from routes_analytics import analytics_bp

    app = Flask(
        __name__,
        root_path=str(tmp_path),
        template_folder=str(Path(__file__).resolve().parents[1] / "Templates"),
    )

    @app.route("/login")
    def login():
        return "login"

    @app.route("/menu")
    def menu():
        return "menu"

    app.register_blueprint(analytics_bp)
    app.config["TESTING"] = True

    import routes_analytics
    routes_analytics.EXCEEDANCE_WORKSPACE_DIR = str(tmp_path / "exceedance_workspaces")
    routes_analytics.UPLOADS_DIR = str(tmp_path / "uploads")

    return app


def _sample_open_records():
    """Generate sample open records."""
    return [
        {
            "id": "F001",
            "tail": "N12345",
            "ata": "32-41",
            "message": "Hard landing detected",
            "description": "Structural impact during landing",
        }
    ]


def test_exceedance_causal_chain_analysis(monkeypatch, tmp_path: Path) -> None:
    """Item 391: Analyze causal chaining using technical causality graph."""
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
        "2026-03-26T10:15:10Z,structural failure\n"
    )
    pdf_content = b"FINDING: Hard landing with structural damage"

    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Causal chain test",
            "scenario": "Causality analysis",
            "tail": "N11111",
            "ata": "31",
            "modelo": "B777",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "events.csv"),
            "pdf_files": (io.BytesIO(pdf_content), "doc.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    # Verify causal chain analysis
    assert "causal_chain_analysis" in payload["data"]
    causal = payload["data"]["causal_chain_analysis"]
    assert "causal_chains" in causal
    assert isinstance(causal["causal_chains"], list)
    assert "root_causes" in causal
    assert isinstance(causal["root_causes"], list)
    assert "graph_complexity" in causal
    assert causal["graph_complexity"] in {
        "minimal", "simple", "moderate", "complex"}


def test_exceedance_temporal_causality_validation(monkeypatch, tmp_path: Path) -> None:
    """Item 392: Validate temporal causality between messages."""
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
        "timestamp,event_message\n"
        "2026-03-26T10:15:00Z,System failure detected\n"
        "2026-03-26T10:15:05Z,Recovery initiated\n"
    )
    pdf_content = b"FINDING: Event sequence analysis"

    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Temporal validation test",
            "scenario": "Causality sequence analysis",
            "tail": "N22222",
            "ata": "29",
            "modelo": "A320",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "events.csv"),
            "pdf_files": (io.BytesIO(pdf_content), "doc.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    # Verify temporal causality validation
    assert "temporal_causality_validation" in payload["data"]
    temporal = payload["data"]["temporal_causality_validation"]
    assert "temporal_violations" in temporal
    assert isinstance(temporal["temporal_violations"], list)
    assert "causality_valid" in temporal
    assert isinstance(temporal["causality_valid"], bool)
    assert "events_analyzed" in temporal
    assert temporal["events_analyzed"] >= 0


def test_exceedance_residual_risk_matrix(monkeypatch, tmp_path: Path) -> None:
    """Item 393: Compute residual risk matrix after proposed actions."""
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
        "2026-03-26T10:15:00Z,inspection finding\n"
    )
    pdf_content = b"FINDING: Risk assessment required"

    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Risk residual assessment",
            "scenario": "Residual risk evaluation",
            "tail": "N33333",
            "ata": "32",
            "modelo": "E195",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "events.csv"),
            "pdf_files": (io.BytesIO(pdf_content), "doc.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    # Verify residual risk matrix
    assert "residual_risk_matrix" in payload["data"]
    risk = payload["data"]["residual_risk_matrix"]
    assert "initial_risk_level" in risk
    assert "residual_risk_level" in risk
    assert risk["residual_risk_level"] in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
    assert "total_risk_reduction_pct" in risk
    assert 0 <= risk["total_risk_reduction_pct"] <= 100
    assert "actions_risk_impact" in risk
    assert isinstance(risk["actions_risk_impact"], list)


def test_exceedance_validation_maintenance_recommendations(monkeypatch, tmp_path: Path) -> None:
    """Item 395: Recommend final validation and maintenance verification."""
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
        "2026-03-26T10:15:00Z,replacement action\n"
    )
    pdf_content = b"ACTION: Component replacement required"

    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Validation requirements test",
            "scenario": "Maintenance validation planning",
            "tail": "N44444",
            "ata": "29-30",
            "modelo": "B787",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "events.csv"),
            "pdf_files": (io.BytesIO(pdf_content), "doc.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    # Verify validation maintenance recommendations
    assert "validation_maintenance_recommendations" in payload["data"]
    validation = payload["data"]["validation_maintenance_recommendations"]
    assert "validation_steps" in validation
    assert isinstance(validation["validation_steps"], list)
    assert "total_estimated_hours" in validation
    assert validation["total_estimated_hours"] >= 0
    assert "sign_off_required" in validation
    assert isinstance(validation["sign_off_required"], list)
    assert "documentation_checklist" in validation
    assert isinstance(validation["documentation_checklist"], list)


def test_exceedance_file_robustness_assessment(monkeypatch, tmp_path: Path) -> None:
    """Item 398: Test robustness of parser with corrupted files."""
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=2000: _sample_open_records())
    monkeypatch.setattr("routes_analytics.get_ai", lambda: type("AIStub", (), {
        "chat": lambda *args, **kwargs: {"response": "", "related_atas": [], "suggestions": []},
        "get_analytics": lambda *args: {"error": "stub"},
        "list_ata_systems": lambda *args: [],
    })())

    client = app.test_client()
    csv_content = "timestamp,event\n2026-03-26T10:15:00Z,test\n"
    pdf_content = b"Test content"

    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "File robustness test",
            "scenario": "Parser resilience validation",
            "tail": "N55555",
            "ata": "31",
            "modelo": "A380",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "events.csv"),
            "pdf_files": (io.BytesIO(pdf_content), "doc.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    # Verify file robustness assessment
    assert "file_robustness_assessment" in payload["data"]
    robustness = payload["data"]["file_robustness_assessment"]
    assert "robustness_tests" in robustness
    assert isinstance(robustness["robustness_tests"], list)
    assert "passed" in robustness
    assert "total" in robustness
    assert robustness["passed"] <= robustness["total"]
    assert "pass_rate_pct" in robustness
    assert 0 <= robustness["pass_rate_pct"] <= 100
    assert "resilience_grade" in robustness
    assert robustness["resilience_grade"] in {"A", "B", "C"}


def test_exceedance_regression_test_report(monkeypatch, tmp_path: Path) -> None:
    """Item 399: Build regression test suite report for diagnostic quality."""
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=2000: _sample_open_records())
    monkeypatch.setattr("routes_analytics.get_ai", lambda: type("AIStub", (), {
        "chat": lambda *args, **kwargs: {"response": "", "related_atas": [], "suggestions": []},
        "get_analytics": lambda *args: {"error": "stub"},
        "list_ata_systems": lambda *args: [],
    })())

    client = app.test_client()
    csv_content = "timestamp,event\n2026-03-26T10:15:00Z,signal detection\n"
    pdf_content = b"Test regression suite"

    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Regression test report",
            "scenario": "Diagnostic quality validation",
            "tail": "N66666",
            "ata": "35",
            "modelo": "CRJ900",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "events.csv"),
            "pdf_files": (io.BytesIO(pdf_content), "doc.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    # Verify regression test report
    assert "regression_test_report" in payload["data"]
    regression = payload["data"]["regression_test_report"]
    assert "test_categories" in regression
    assert isinstance(regression["test_categories"], dict)
    assert "total_tests" in regression
    assert regression["total_tests"] > 0
    assert "overall_pass_rate_pct" in regression
    assert 0 <= regression["overall_pass_rate_pct"] <= 100
    assert "quality_grade" in regression
    assert regression["quality_grade"] in {"A+", "A", "B", "C"}
    assert "critical_test_pass_rate" in regression
    assert 0 <= regression["critical_test_pass_rate"] <= 100


def test_exceedance_continuous_improvement_program(monkeypatch, tmp_path: Path) -> None:
    """Item 400: Continuous improvement program based on metrics."""
    app = _build_test_app(tmp_path)
    monkeypatch.setattr("routes_analytics.load_records",
                        lambda limit=2000: _sample_open_records())
    monkeypatch.setattr("routes_analytics.get_ai", lambda: type("AIStub", (), {
        "chat": lambda *args, **kwargs: {"response": "", "related_atas": [], "suggestions": []},
        "get_analytics": lambda *args: {"error": "stub"},
        "list_ata_systems": lambda *args: [],
    })())

    client = app.test_client()
    csv_content = "timestamp,event\n2026-03-26T10:15:00Z,improvement tracking\n"
    pdf_content = b"Continuous improvement documentation"

    response = client.post(
        "/api/ai/exceedance/analyze",
        data={
            "failure_text": "Continuous improvement program",
            "scenario": "Metrics-based improvement planning",
            "tail": "N77777",
            "ata": "27",
            "modelo": "Q400",
            "csv_files": (io.BytesIO(csv_content.encode("utf-8")), "events.csv"),
            "pdf_files": (io.BytesIO(pdf_content), "doc.pdf"),
        },
        content_type="multipart/form-data",
    )
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["success"] is True

    # Verify continuous improvement program
    assert "continuous_improvement_program" in payload["data"]
    improvement = payload["data"]["continuous_improvement_program"]
    assert "improvement_areas" in improvement
    assert isinstance(improvement["improvement_areas"], list)
    assert "total_areas_tracked" in improvement
    assert improvement["total_areas_tracked"] > 0
    assert "high_priority_count" in improvement
    assert improvement["high_priority_count"] >= 0
    assert "prioritized_initiatives" in improvement
    assert isinstance(improvement["prioritized_initiatives"], list)
    assert "program_status" in improvement
    assert improvement["program_status"] in {"active", "paused", "completed"}
