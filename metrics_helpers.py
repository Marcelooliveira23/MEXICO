# Metrics helper functions for items 369-372
# These will be copied into routes_analytics.py

def _record_validation_result(workspace, field_name, expected_value, actual_value, valid):
    """Item 369: Record field validation result for precision calculation."""
    metrics = workspace.get("metrics", {})
    if "validation_results" not in metrics:
        metrics["validation_results"] = []
    validation_entry = {
        "field": str(field_name or "").strip(),
        "expected": str(expected_value or "")[:100],
        "actual": str(actual_value or "")[:100],
        "valid": bool(valid),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    metrics["validation_results"].append(validation_entry)
    metrics["validation_results"] = metrics["validation_results"][-50:]
    workspace["metrics"] = metrics


def _record_execution_feedback(workspace, recommendation_index, recommended_action, executed_action, success, notes=""):
    """Items 370-371: Record execution feedback (effectiveness + divergence tracking)."""
    metrics = workspace.get("metrics", {})
    if "execution_feedback" not in metrics:
        metrics["execution_feedback"] = []
    feedback_entry = {
        "recommendation_index": int(recommendation_index or 0),
        "recommended_action": str(recommended_action or "")[:200],
        "executed_action": str(executed_action or "")[:200],
        "success": bool(success),
        "divergence": _calculate_string_divergence(recommended_action, executed_action),
        "notes": str(notes or "")[:300],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    metrics["execution_feedback"].append(feedback_entry)
    metrics["execution_feedback"] = metrics["execution_feedback"][-50:]
    workspace["metrics"] = metrics


ndef _calculate_string_divergence(str_a, str_b):
    """Calculate divergence score (0-100) between two strings. Lower = more similar."""
    s_a = str(str_a or "").strip().lower()
    s_b = str(str_b or "").strip().lower()
    if s_a == s_b:
        return 0.0
    max_len = max(len(s_a), len(s_b))
    if max_len == 0:
        return 0.0
    levenshtein_dist = sum(1 for a, b in zip(
        s_a, s_b) if a != b) + abs(len(s_a) - len(s_b))
    divergence = min(100.0, (levenshtein_dist / max_len) * 100)
    return round(divergence, 1)


def _build_precision_metric(workspace):
    """Item 369: Calculate post-validation precision score (0-100)."""
    metrics = workspace.get("metrics", {})
    results = metrics.get("validation_results", [])
    if not results:
        return 0.0
    valid_count = sum(1 for r in results if r.get("valid", False))
    precision = (valid_count / len(results)) * 100 if results else 0.0
    return round(precision, 1)


def _build_effectiveness_index(workspace):
    """Item 370: Calculate recommendation effectiveness index (success rate 0-100)."""
    metrics = workspace.get("metrics", {})
    feedback = metrics.get("execution_feedback", [])
    if not feedback:
        return 0.0
    success_count = sum(1 for f in feedback if f.get("success", False))
    effectiveness = (success_count / len(feedback)) * 100 if feedback else 0.0
    return round(effectiveness, 1)


def _build_divergence_score(workspace):
    """Item 371: Calculate execution divergence score (average of all divergences, 0-100, lower=better)."""
    metrics = workspace.get("metrics", {})
    feedback = metrics.get("execution_feedback", [])
    if not feedback:
        return 0.0
    divergences = [f.get("divergence", 0) for f in feedback]
    avg_divergence = sum(divergences) / \
        len(divergences) if divergences else 0.0
    return round(avg_divergence, 1)


def _apply_adaptive_learning(workspace, current_result):
    """Item 372: Apply adaptive learning adjustments based on metrics feedback."""
    metrics = workspace.get("metrics", {})
    precision = _build_precision_metric(workspace)
    effectiveness = _build_effectiveness_index(workspace)
    divergence = _build_divergence_score(workspace)
    adjustments = []
    if precision < 50:
        adjustment = {"type": "increase_review_gate",
                      "reason": "low_precision", "value": precision}
        adjustments.append(adjustment)
        current_result["closure_readiness"] = current_result.get(
            "closure_readiness", {})
        current_result["closure_readiness"]["mandatory_reviews"] = current_result["closure_readiness"].get(
            "mandatory_reviews", 1) + 1
    if effectiveness < 60 and len(workspace.get("execution_feedback", [])) > 3:
        adjustment = {"type": "decrease_confidence",
                      "reason": "low_effectiveness", "value": effectiveness}
        adjustments.append(adjustment)
        current_result["severity_estimate"] = max(
            1, current_result.get("severity_estimate", 50) - 10)
    if divergence > 50:
        adjustment = {"type": "increase_detail_level",
                      "reason": "high_divergence", "value": divergence}
        adjustments.append(adjustment)
    if adjustments:
        metrics["learning_adjustments"] = (metrics.get(
            "learning_adjustments", []) + adjustments)[-20:]
        workspace["metrics"] = metrics
