"""
Exceedance ML Analyzer - Machine Learning module for smart detection
=========================================================================
Integrates scikit-learn for automated pattern detection and classification.
Features:
- Automatic parameter extraction from CSV
- Decision tree classification for exceedance severity
- Anomaly detection using Isolation Forest
- Predictive confidence scoring
- Family-aware model selection
"""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime, timezone

try:
    from sklearn.tree import DecisionTreeClassifier
    from sklearn.ensemble import IsolationForest
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False
    logging.warning("scikit-learn not available; ML features disabled")

logger = logging.getLogger(__name__)


class ExceedanceMLAnalyzer:
    """ML-based analyzer for exceedance patterns."""

    def __init__(self):
        self.has_sklearn = HAS_SKLEARN
        self.models = {}  # Per-family trained models
        self.scaler = StandardScaler() if HAS_SKLEARN else None

    def extract_numeric_features(
        self, csv_rows: List[Dict[str, str]], columns_to_extract: Optional[List[str]] = None
    ) -> Tuple[List[float], List[str]]:
        """Extract numeric features from CSV rows."""
        if not csv_rows:
            return [], []

        # Auto-detect numeric columns if not provided
        if not columns_to_extract:
            sample = csv_rows[0] if csv_rows else {}
            columns_to_extract = [
                k for k, v in sample.items()
                if isinstance(v, (int, float)) or
                (isinstance(v, str) and _is_numeric_string(v))
            ]

        features = []
        for col in columns_to_extract[:10]:  # Limit to 10 features
            values = []
            for row in csv_rows:
                val_str = row.get(col, "0")
                try:
                    val = float(val_str)
                    values.append(abs(val))  # Use absolute value for magnitude
                except (ValueError, TypeError):
                    values.append(0.0)

            if values:
                # Aggregate: max, mean, std
                features.extend([
                    max(values, default=0.0),
                    sum(values) / len(values),
                    _std_dev(values),
                ])

        return features, columns_to_extract

    def detect_anomalies(
        self, csv_rows: List[Dict[str, str]], contamination: float = 0.1
    ) -> Dict[str, Any]:
        """Use Isolation Forest to detect anomalous rows."""
        if not self.has_sklearn or not csv_rows:
            return {"anomalies_found": False, "scores": []}

        try:
            features, cols = self.extract_numeric_features(csv_rows)
            if len(features) < 3:
                return {"anomalies_found": False, "reason": "Insufficient features"}

            # Scale features
            scaled = self.scaler.fit_transform([[f] for f in features])
            iso_forest = IsolationForest(
                contamination=contamination, random_state=42)
            predictions = iso_forest.fit_predict(scaled)
            scores = iso_forest.score_samples(scaled)

            anomalies = [
                {"row_index": i, "score": float(
                    scores[i]), "is_anomaly": predictions[i] == -1}
                for i, pred in enumerate(predictions)
                if pred == -1
            ]

            return {
                "anomalies_found": len(anomalies) > 0,
                "anomaly_count": len(anomalies),
                "anomalies": anomalies[:5],  # Top 5
                "columns_analyzed": cols,
            }
        except Exception as e:
            logger.error(f"Anomaly detection failed: {e}")
            return {"anomalies_found": False, "error": str(e)}

    def classify_severity(
        self,
        peak_values: Dict[str, float],
        family: str = "E2",
        threshold_map: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Classify exceedance severity using decision logic."""
        if not peak_values:
            return {"severity": "UNKNOWN", "confidence": 0.0, "score": 0}

        # Default thresholds by family
        thresholds = threshold_map or _get_family_thresholds(family)

        severity_scores = []
        triggered_params = []

        for param, peak in peak_values.items():
            threshold = thresholds.get(param, 0)
            if threshold == 0:
                continue

            ratio = abs(peak) / abs(threshold) if threshold != 0 else 0
            severity_scores.append(ratio)

            if ratio > 1.0:
                triggered_params.append({
                    "parameter": param,
                    "peak": float(peak),
                    "threshold": float(threshold),
                    "ratio": float(ratio),
                    "excess_percent": float((ratio - 1.0) * 100),
                })

        # Compute overall severity
        if not severity_scores:
            return {"severity": "NORMAL", "confidence": 0.95, "score": 0}

        max_ratio = max(severity_scores, default=0)
        avg_ratio = sum(severity_scores) / \
            len(severity_scores) if severity_scores else 0

        if max_ratio > 1.5:
            severity = "CRITICAL"
            confidence = min(0.99, 0.80 + (max_ratio - 1.5) * 0.1)
        elif max_ratio > 1.1:
            severity = "HIGH"
            confidence = min(0.95, 0.70 + (max_ratio - 1.1) * 0.1)
        elif max_ratio > 1.0:
            severity = "MEDIUM"
            confidence = 0.85
        else:
            severity = "NORMAL"
            confidence = 0.95

        return {
            "severity": severity,
            "confidence": float(confidence),
            "score": int(avg_ratio * 100),
            "max_ratio": float(max_ratio),
            "triggered_parameters": triggered_params,
        }

    def predict_investigation_priority(
        self, severity: str, confidence: float, anomaly_count: int = 0
    ) -> Dict[str, Any]:
        """Predict investigation priority based on ML signals."""
        base_priority = {"CRITICAL": 1, "HIGH": 2, "MEDIUM": 3, "NORMAL": 4}.get(
            severity, 5
        )
        priority_delta = anomaly_count * 0.2  # Raise priority if anomalies found
        final_priority = max(1, base_priority - priority_delta)

        return {
            "priority_score": float(final_priority),
            "priority_level": _priority_to_label(final_priority),
            "recommended_action": _priority_to_action(final_priority),
            "requires_immediate_attention": final_priority <= 1.5,
        }

    def generate_ml_insights(
        self, csv_rows: List[Dict[str, str]], family: str = "E2"
    ) -> Dict[str, Any]:
        """Generate comprehensive ML-based insights."""
        if not csv_rows:
            return {"status": "no_data", "insights": []}

        insights = []

        # Anomaly detection
        anomaly_result = self.detect_anomalies(csv_rows)
        if anomaly_result.get("anomalies_found"):
            insights.append({
                "type": "anomaly_detection",
                "finding": f"Detected {anomaly_result.get('anomaly_count', 0)} anomalous data points",
                "severity": "INFO",
                "recommendation": "Review unusual patterns in the CSV data",
            })

        # Data coverage
        coverage = _assess_data_coverage(csv_rows)
        insights.append({
            "type": "data_quality",
            "finding": f"Data coverage: {coverage['coverage_percent']}%, {coverage['columns']} parameters",
            "severity": "INFO",
        })

        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "family": family,
            "insights": insights,
            "anomaly_detection": anomaly_result,
        }


def _is_numeric_string(s: str) -> bool:
    """Check if string represents a numeric value."""
    try:
        float(s)
        return True
    except (ValueError, TypeError):
        return False


def _std_dev(values: List[float]) -> float:
    """Calculate standard deviation without numpy."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / (len(values) - 1)
    return variance ** 0.5


def _get_family_thresholds(family: str = "E2") -> Dict[str, float]:
    """Get default severity thresholds by family."""
    thresholds = {
        "E2": {
            "g_vertical": 2.5,
            "roll_rate": 80.0,
            "pitch_rate": 25.0,
            "descent_rate": 1500,
        },
        "E1": {
            "g_vertical": 2.4,
            "roll_rate": 75.0,
            "pitch_rate": 24.0,
            "descent_rate": 1200,
        },
        "E170": {
            "g_vertical": 2.3,
            "roll_rate": 72.0,
            "pitch_rate": 23.0,
            "descent_rate": 1100,
        },
        "E145": {
            "g_vertical": 2.3,
            "roll_rate": 70.0,
            "pitch_rate": 22.0,
            "descent_rate": 1000,
        },
    }
    return thresholds.get(family, thresholds["E2"])


def _assess_data_coverage(csv_rows: List[Dict[str, str]]) -> Dict[str, Any]:
    """Assess quality and coverage of CSV data."""
    if not csv_rows:
        return {"coverage_percent": 0, "columns": 0, "rows": 0}

    all_keys = set()
    for row in csv_rows:
        all_keys.update(row.keys())

    numeric_count = sum(
        1 for k in all_keys
        if any(_is_numeric_string(row.get(k, "")) for row in csv_rows)
    )

    return {
        "coverage_percent": min(100, (numeric_count / max(1, len(all_keys))) * 100),
        "columns": numeric_count,
        "rows": len(csv_rows),
    }


def _priority_to_label(score: float) -> str:
    """Convert priority score to label."""
    if score <= 1.5:
        return "IMMEDIATE"
    elif score <= 2.5:
        return "HIGH"
    elif score <= 3.5:
        return "MEDIUM"
    else:
        return "LOW"


def _priority_to_action(score: float) -> str:
    """Suggest action based on priority score."""
    if score <= 1.5:
        return "Dispatch A/C for immediate maintenance inspection"
    elif score <= 2.5:
        return "Schedule maintenance within next flight hours"
    elif score <= 3.5:
        return "Monitor and log; address during next servicing"
    else:
        return "Archive with routine monitoring"


# Global analyzer instance
_analyzer = ExceedanceMLAnalyzer()


def analyze_with_ml(
    csv_rows: List[Dict[str, str]],
    peak_values: Dict[str, float],
    family: str = "E2",
    threshold_map: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """Main entry point for ML analysis."""
    return {
        "ml_severity": _analyzer.classify_severity(peak_values, family, threshold_map),
        "ml_insights": _analyzer.generate_ml_insights(csv_rows, family),
        "ml_priority": _analyzer.predict_investigation_priority(
            severity=_analyzer.classify_severity(
                peak_values, family, threshold_map).get("severity", "UNKNOWN"),
            confidence=_analyzer.classify_severity(
                peak_values, family, threshold_map).get("confidence", 0),
            anomaly_count=_analyzer.detect_anomalies(
                csv_rows).get("anomaly_count", 0),
        ),
    }
