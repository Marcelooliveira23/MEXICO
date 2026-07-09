import json
from typing import Any

import app as app_module


flask_app = app_module.app


PAGE_CHECKS = {
    "/login": ["<form", "username", "password"],
    "/menu": ["AI Analysis", "Exceedance Analysis", "LRU"],
    "/ai_analysis": [
        "btn-analyze",
        "btn-summary",
        "chat-send",
        "btn-mission-load",
        "btn-mission-push",
        "btn-mission-clear",
        "btn-recalibrate",
    ],
    "/exceedance_analysis": [
        "exceedance-form",
        "btn-load-open-cases",
        "btn-analyze-open-case",
        "btn-export-json",
        "btn-reprocess-analysis",
    ],
    "/cadastro": ["cadastro-form", "btn-ai-analyze-inline"],
    "/horas_ciclos": ["Export PDF", "Export Excel"],
    "/fleet_status_report": ["filterForm", "btnCards", "btnTable"],
    "/logbook_data": ["Export PDF", "Export Excel", "Export CSV", "Print"],
    "/out_of_service": ["markOperationalModal", "newOutOfServiceModal"],
    "/tail_cadastro": ["addTailModal", "tailForm"],
    "/mel_itens": ["filterForm", "closeMelModal"],
    "/etd": ["filterForm", "Search", "Clear"],
    "/lru_removal_installation": ["lru-filter-tail", "lru-filter-pn", "Database Total"],
    "/user_management": ["Create New User", "Registered Users"],
    "/change_password": ["current_password", "new_password", "confirm_password"],
}


def _payload_summary(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        return {}

    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    summary = payload.get("summary") if isinstance(
        payload.get("summary"), dict) else {}
    extra: dict[str, Any] = {}

    if "response" in data:
        extra["response_len"] = len(str(data.get("response") or ""))
    if "conversation_history" in data and isinstance(data.get("conversation_history"), list):
        extra["conversation_history_len"] = len(
            data.get("conversation_history"))
    if "projection_signals" in data and isinstance(data.get("projection_signals"), dict):
        extra["projection_keys"] = sorted(
            data.get("projection_signals").keys())[:12]
    if summary:
        depth = summary.get("intelligence_depth") or {}
        extra["summary_records"] = payload.get("records_count")
        extra["queue_len"] = len(depth.get("intervention_queue") or [])
        extra["projection_present"] = isinstance(
            depth.get("projection_signals"), dict)

    return extra


def run_audit() -> dict[str, Any]:
    results: dict[str, Any] = {"pages": {}, "api": {}, "notes": []}

    with flask_app.test_client() as client:
        with client.session_transaction() as session:
            session["username"] = "admin"
            session["user_id"] = 1
            session["access_level"] = "Administrator"

        for path, markers in PAGE_CHECKS.items():
            response = client.get(path, follow_redirects=True)
            text = response.get_data(as_text=True)
            results["pages"][path] = {
                "status": response.status_code,
                "ok": 200 <= response.status_code < 300,
                "markers": {marker: (marker in text) for marker in markers},
                "missing_markers": [marker for marker in markers if marker not in text],
                "length": len(text),
            }

        def store_api(name: str, method: str, path: str, **kwargs: Any) -> Any:
            caller = getattr(client, method.lower())
            response = caller(path, **kwargs)
            payload = response.get_json(silent=True)
            results["api"][name] = {
                "path": path,
                "status": response.status_code,
                "ok": 200 <= response.status_code < 300,
                "success": None if not isinstance(payload, dict) else payload.get("success"),
                "keys": sorted(payload.keys()) if isinstance(payload, dict) else [],
                "extra": _payload_summary(payload),
            }
            return payload

        store_api(
            "analyze_failure",
            "post",
            "/api/ai/analyze_failure",
            json={
                "ata": "49",
                "description": "APU bleed valve failure during start sequence",
                "tail": "PR-TEST",
                "model": "E190-E2",
                "model_filter": "E190-E2",
                "category": "performance",
            },
        )
        store_api("ai_summary", "get", "/api/ai/summary")
        store_api("ai_analytics", "get", "/api/ai/analytics")
        store_api("ai_feedback_stats", "get", "/api/ai/feedback/stats")
        store_api("ai_recalibrate", "post", "/api/ai/recalibrate")
        store_api(
            "ai_chat",
            "post",
            "/api/ai/chat",
            json={
                "query": "Give a concise troubleshooting answer for ATA 49",
                "scope": "global",
                "deep_mode": True,
            },
        )
        store_api("ai_chat_history", "get", "/api/ai/chat/history")
        store_api("ata_details", "get", "/api/ai/ata/49")
        store_api("mission_queue_get", "get", "/api/mission/queue")
        store_api(
            "mission_queue_batch_empty",
            "post",
            "/api/mission/queue/batch",
            json={"tasks": []},
        )
        store_api("daily_brief", "get", "/api/ai/daily_brief")
        store_api("executive_dashboard", "get", "/api/ai/executive_dashboard")
        store_api("monthly_trend", "get", "/api/ai/monthly_trend")
        store_api("exposure_hotspots", "get", "/api/ai/exposure_hotspots")

        exceedance = store_api(
            "exceedance_analyze",
            "post",
            "/api/ai/exceedance/analyze",
            data={
                "failure_text": "Engine parameter spike after takeoff",
                "scenario": "Crew observed exceedance alert and maintenance needs guidance",
                "tail": "PR-TEST",
                "ata": "72",
                "analysis_mode": "standard",
            },
        )
        store_api("exceedance_open_cases", "get",
                  "/api/ai/exceedance/open_cases?limit=5")
        store_api("exceedance_dashboard", "get",
                  "/api/ai/exceedance/investigations/dashboard")
        store_api("exceedance_queue", "get",
                  "/api/ai/exceedance/investigations/queue")

        open_cases = store_api(
            "exceedance_open_cases_full",
            "get",
            "/api/ai/exceedance/open_cases?limit=5",
        )
        case_id = None
        if isinstance(open_cases, dict):
            cases = open_cases.get("cases") if isinstance(
                open_cases.get("cases"), list) else []
            if cases:
                case_id = cases[0].get("id")
        if case_id:
            store_api(
                "exceedance_analyze_open_case",
                "post",
                "/api/ai/exceedance/analyze_open_case",
                data={"case_id": case_id, "analysis_mode": "standard"},
            )

        analysis_key = None
        if isinstance(exceedance, dict):
            data = exceedance.get("data") if isinstance(
                exceedance.get("data"), dict) else {}
            analysis_key = data.get("analysis_key")
        if analysis_key:
            store_api(
                "exceedance_reprocess",
                "post",
                "/api/ai/exceedance/reprocess",
                data={"analysis_key": analysis_key,
                      "analysis_mode": "standard"},
            )
            store_api(
                "exceedance_investigation",
                "get",
                f"/api/ai/exceedance/investigation/{analysis_key}",
            )
        else:
            results["notes"].append(
                "No analysis_key returned by exceedance analyze; reprocess test skipped.")

        store_api("logbook_export_csv", "get", "/logbook_data/export/csv")
        store_api("logbook_print", "get", "/logbook_data/print")
        store_api(
            "logbook_update_status_invalid",
            "post",
            "/logbook_data/update_status",
            json={"id": -1, "status": "open"},
        )
        store_api(
            "mel_update_status_invalid",
            "post",
            "/mel_itens/update_status",
            json={
                "id": -1,
                "status": "closed",
                "replaced_item": "TEST-COMPONENT",
                "solution_response": "Test closeout validation",
            },
        )
        store_api(
            "etd_update_status_invalid",
            "post",
            "/etd/0/status",
            data={"etd_emitida": "NO"},
            follow_redirects=True,
        )
        store_api("horas_export_pdf", "post",
                  "/horas_ciclos/export/pdf", follow_redirects=True)
        store_api("horas_export_excel", "post",
                  "/horas_ciclos/export/excel", follow_redirects=True)
        store_api("lru_export_pdf", "post",
                  "/lru_removal_installation/export/pdf", follow_redirects=True)
        store_api("lru_export_excel", "post",
                  "/lru_removal_installation/export/excel", follow_redirects=True)

    return results


if __name__ == "__main__":
    print(json.dumps(run_audit(), indent=2, ensure_ascii=False))
