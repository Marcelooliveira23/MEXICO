"""
Turbulence Analyzer
Detects turbulence encounters based on G-load exceedances and optional turbulence speed limits.
"""

from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict
from datetime import datetime
import pandas as pd


@dataclass
class TurbulenceResult:
    """Resultado da análise de turbulência"""
    is_turbulence: bool
    max_positive_g: float
    max_negative_g: float
    positive_exceeded: bool
    negative_exceeded: bool
    positive_threshold: float
    negative_threshold: float
    max_turbulence_speed: Optional[float]
    max_speed_observed: Optional[float]
    exceedance_count: int
    exceedance_events: List[Tuple[float, float, str]]  # (time, g_value, type)
    severity_level: str  # NONE, LOW, MODERATE, HIGH, SEVERE
    aircraft_model: str
    analysis_timestamp: str
    recommended_actions: List[str]


class TurbulenceAnalyzer:
    """Analisa eventos de turbulência com base em limites técnicos"""

    DEFAULT_THRESHOLDS = {
        "e145": {"max_positive_g": 2.2, "max_negative_g": -0.8, "max_turbulence_speed": 280},
        "e170": {"max_positive_g": 2.5, "max_negative_g": -1.0, "max_turbulence_speed": 280},
        "e1": {"max_positive_g": 2.5, "max_negative_g": -1.0, "max_turbulence_speed": 280},
        "e2": {"max_positive_g": 2.5, "max_negative_g": -1.0, "max_turbulence_speed": 280},
    }

    def analyze_turbulence(
        self,
        flight_data: pd.DataFrame,
        aircraft_id: str,
        aircraft_model: str,
        rules: Optional[Dict] = None,
    ) -> TurbulenceResult:
        """
        Analisa turbulência baseada em limites de G e velocidade.
        """
        if flight_data is None or len(flight_data) == 0:
            return self._empty_result(aircraft_model, "Empty data")

        thresholds = dict(self.DEFAULT_THRESHOLDS.get(aircraft_id, {}))
        if rules:
            thresholds.update({k: v for k, v in rules.items() if v is not None})

        pos_limit = float(thresholds.get("max_positive_g", 2.5))
        neg_limit = float(thresholds.get("max_negative_g", -1.0))
        speed_limit = thresholds.get("max_turbulence_speed")

        accel_col = self._find_column(
            flight_data,
            [
                "vertical_acceleration",
                "norm_accel",
                "normal_accel",
                "nz",
                "g_load",
                "g",
                "g_force",
                "vertical_g",
            ],
        )

        if not accel_col:
            return self._empty_result(aircraft_model, "No G-load column found")

        g_series = flight_data[accel_col].dropna()
        if len(g_series) == 0:
            return self._empty_result(aircraft_model, "No valid G-load samples")

        max_positive_g = float(g_series.max())
        max_negative_g = float(g_series.min())

        positive_exceeded = max_positive_g > pos_limit
        negative_exceeded = max_negative_g < neg_limit

        # Speed limit (optional)
        max_speed_observed = None
        speed_exceeded = False
        if speed_limit is not None:
            speed_col = self._find_column(
                flight_data,
                ["ias", "kias", "airspeed", "indicated_airspeed", "speed"],
            )
            if speed_col:
                speed_series = flight_data[speed_col].dropna()
                if len(speed_series) > 0:
                    max_speed_observed = float(speed_series.max())
                    speed_exceeded = max_speed_observed > float(speed_limit)

        exceedance_events = self._find_exceedance_events(
            flight_data, accel_col, pos_limit, neg_limit
        )

        is_turbulence = positive_exceeded or negative_exceeded or speed_exceeded
        severity = self._calculate_severity(
            max_positive_g,
            max_negative_g,
            pos_limit,
            neg_limit,
            len(exceedance_events),
        )

        recommended_actions = self._get_recommended_actions(
            is_turbulence, severity, speed_exceeded
        )

        return TurbulenceResult(
            is_turbulence=is_turbulence,
            max_positive_g=max_positive_g,
            max_negative_g=max_negative_g,
            positive_exceeded=positive_exceeded,
            negative_exceeded=negative_exceeded,
            positive_threshold=pos_limit,
            negative_threshold=neg_limit,
            max_turbulence_speed=float(speed_limit) if speed_limit is not None else None,
            max_speed_observed=max_speed_observed,
            exceedance_count=len(exceedance_events),
            exceedance_events=exceedance_events,
            severity_level=severity,
            aircraft_model=aircraft_model,
            analysis_timestamp=datetime.now().isoformat(),
            recommended_actions=recommended_actions,
        )

    def _find_exceedance_events(
        self,
        flight_data: pd.DataFrame,
        accel_col: str,
        pos_limit: float,
        neg_limit: float,
    ) -> List[Tuple[float, float, str]]:
        events = []
        time_col = self._find_column(
            flight_data, ["time", "time_sec", "elapsed_time", "timestamp"]
        )

        g_values = flight_data[accel_col].values
        for idx, g in enumerate(g_values):
            if pd.notna(g):
                if g > pos_limit:
                    time_val = flight_data[time_col].iloc[idx] if time_col else idx
                    events.append((float(time_val), float(g), "POSITIVE"))
                elif g < neg_limit:
                    time_val = flight_data[time_col].iloc[idx] if time_col else idx
                    events.append((float(time_val), float(g), "NEGATIVE"))
        return events

    def _calculate_severity(
        self,
        max_pos_g: float,
        max_neg_g: float,
        pos_limit: float,
        neg_limit: float,
        event_count: int,
    ) -> str:
        if max_pos_g <= pos_limit and max_neg_g >= neg_limit:
            return "NONE"

        pos_ratio = max_pos_g / pos_limit if pos_limit else 0
        neg_ratio = abs(max_neg_g / neg_limit) if neg_limit else 0
        ratio = max(pos_ratio, neg_ratio)

        if ratio >= 1.2 or event_count >= 10:
            return "SEVERE"
        if ratio >= 1.1 or event_count >= 5:
            return "HIGH"
        if ratio >= 1.05 or event_count >= 2:
            return "MODERATE"
        return "LOW"

    def _get_recommended_actions(
        self, is_turbulence: bool, severity: str, speed_exceeded: bool
    ) -> List[str]:
        if not is_turbulence:
            return ["No turbulence exceedance detected."]

        actions = ["Turbulence exceedance detected. Inspection required per maintenance manual."]
        if speed_exceeded:
            actions.append("Review turbulence penetration speed compliance.")
        if severity in ["HIGH", "SEVERE"]:
            actions.append("Perform detailed structural inspection.")
        else:
            actions.append("Perform general post-flight inspection.")
        return actions

    def _find_column(self, df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        cols = {col.lower(): col for col in df.columns}
        for candidate in candidates:
            if candidate.lower() in cols:
                return cols[candidate.lower()]
        return None

    def _empty_result(self, aircraft_model: str, reason: str) -> TurbulenceResult:
        return TurbulenceResult(
            is_turbulence=False,
            max_positive_g=0.0,
            max_negative_g=0.0,
            positive_exceeded=False,
            negative_exceeded=False,
            positive_threshold=0.0,
            negative_threshold=0.0,
            max_turbulence_speed=None,
            max_speed_observed=None,
            exceedance_count=0,
            exceedance_events=[],
            severity_level="NONE",
            aircraft_model=aircraft_model,
            analysis_timestamp=datetime.now().isoformat(),
            recommended_actions=[reason],
        )
