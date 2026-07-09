"""
Overweight Landing Analyzer
Implements detection of landings above Maximum Landing Weight (MLW)
ETAPA 8: Uses MLW data from ETAPA 1 aircraft model registry
"""

import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
from utils.logger import logger
from utils.config import AppConfig


@dataclass
class OverweightResult:
    """Resultado da análise de overweight landing"""
    status: str
    gross_weight: Optional[float]
    mlw_limit: float
    overweight: Optional[float]
    severity: str
    message: str
    timestamp: Optional[str]


class OverweightLandingAnalyzer:
    """
    Analisador de Overweight Landing
    MLW = Maximum Landing Weight
    """
    
    def get_mlw_for_model(self, model_id: str) -> float:
        """Get MLW in lbs from ETAPA 1 registry"""
        try:
            mlw = AppConfig.get_model_mlw(model_id)
            logger.info(f"[ETAPA 8] Retrieved MLW for {model_id}: {mlw:.0f} lbs ({mlw/2.2:.0f} kg)")
            return mlw
        except Exception as e:
            logger.error(f"[ETAPA 8] Error getting MLW: {e}")
            # Fallback values
            fallbacks = {
                'e145': 43651,
                'e170': 69224,
                'e175': 75000,
                'e190': 108247,
                'e195': 100309,
                'e175_e2': 79380,
                'e190_e2': 110674,
                'e195_e2': 119050,
            }
            return fallbacks.get(model_id.lower(), 69224)
    
    def analyze(self, df: pd.DataFrame, weight_kg: float, model: str) -> List[OverweightResult]:
        """Analyze overweight landing"""
        results = []
        mlw_lbs = self.get_mlw_for_model(model.lower())
        weight_lbs = weight_kg * 2.20462  # Convert kg to lbs

        ag_col = self._find_air_ground_column(df)
        if ag_col is None:
            if self._is_clear_inflight_profile(df):
                result = OverweightResult(
                    status="NORMAL",
                    gross_weight=weight_lbs,
                    mlw_limit=mlw_lbs,
                    overweight=None,
                    severity="NORMAL",
                    message="No air/ground data; in-flight profile detected, skipping landing overweight check",
                    timestamp=df['TIMESTAMP'].iloc[0] if 'TIMESTAMP' in df.columns else None
                )
                logger.info("[ETAPA 8] NORMAL: No air/ground data; in-flight profile detected, skipping landing overweight check")
                return [result]

            if weight_lbs > mlw_lbs:
                overweight = weight_lbs - mlw_lbs
                status = "OVERWEIGHT"
                severity = "CRITICAL"
                message = (
                    f"No air/ground data; conservative check found overweight: "
                    f"{weight_lbs:.0f} lbs exceeds MLW ({mlw_lbs:.0f} lbs) by {overweight:.0f} lbs"
                )
            else:
                overweight = None
                status = "NORMAL"
                severity = "NORMAL"
                message = (
                    f"No air/ground data; conservative check within MLW: "
                    f"{weight_lbs:.0f} lbs <= {mlw_lbs:.0f} lbs"
                )
            result = OverweightResult(
                status=status,
                gross_weight=weight_lbs,
                mlw_limit=mlw_lbs,
                overweight=overweight,
                severity=severity,
                message=message,
                timestamp=df['TIMESTAMP'].iloc[0] if 'TIMESTAMP' in df.columns else None
            )
            logger.info(f"[ETAPA 8] {status}: {message}")
            return [result]

        ag_series = df[ag_col]
        if isinstance(ag_series, pd.DataFrame):
            ag_series = ag_series.iloc[:, 0]
        if not self._has_ground_segment(ag_series):
            if weight_lbs > mlw_lbs:
                overweight = weight_lbs - mlw_lbs
                status = "OVERWEIGHT"
                severity = "CRITICAL"
                message = (
                    f"No landing segment detected; conservative check found overweight: "
                    f"{weight_lbs:.0f} lbs exceeds MLW ({mlw_lbs:.0f} lbs) by {overweight:.0f} lbs"
                )
            else:
                overweight = None
                status = "NORMAL"
                severity = "NORMAL"
                message = (
                    f"No landing segment detected; conservative check within MLW: "
                    f"{weight_lbs:.0f} lbs <= {mlw_lbs:.0f} lbs"
                )
            result = OverweightResult(
                status=status,
                gross_weight=weight_lbs,
                mlw_limit=mlw_lbs,
                overweight=overweight,
                severity=severity,
                message=message,
                timestamp=df['TIMESTAMP'].iloc[0] if 'TIMESTAMP' in df.columns else None
            )
            logger.info(f"[ETAPA 8] {status}: {message}")
            return [result]
        
        logger.info(f"[ETAPA 8] Overweight check for {model.upper()}")
        logger.info(f"         MLW: {mlw_lbs:.0f} lbs")
        logger.info(f"         Landing weight: {weight_lbs:.0f} lbs")
        
        if weight_lbs > mlw_lbs:
            status = "OVERWEIGHT"
            severity = "CRITICAL"
            overweight = weight_lbs - mlw_lbs
            message = f"OVERWEIGHT LANDING: {weight_lbs:.0f} lbs exceeds MLW ({mlw_lbs:.0f} lbs) by {overweight:.0f} lbs"
        else:
            status = "NORMAL"
            severity = "NORMAL"
            overweight = None
            margin = mlw_lbs - weight_lbs
            message = f"Weight OK: {weight_lbs:.0f} lbs < MLW {mlw_lbs:.0f} lbs (margin: {margin:.0f} lbs)"
        
        result = OverweightResult(
            status=status,
            gross_weight=weight_lbs,
            mlw_limit=mlw_lbs,
            overweight=overweight,
            severity=severity,
            message=message,
            timestamp=df['TIMESTAMP'].iloc[0] if 'TIMESTAMP' in df.columns else None
        )
        
        logger.info(f"[ETAPA 8] {status}: {message}")
        return [result]

    def _is_clear_inflight_profile(self, df: pd.DataFrame) -> bool:
        altitude_columns = [
            col for col in df.columns
            if col.lower() in {'alt', 'altitude', 'altitude_ft', 'radio_alt', 'ra'} or 'alt' in col.lower()
        ]

        for altitude_col in altitude_columns:
            series = df[altitude_col].dropna()
            if len(series) == 0:
                continue
            try:
                min_alt = float(series.astype(float).min())
            except (TypeError, ValueError):
                continue

            if min_alt > 1000:
                return True

        return False

    def _find_air_ground_column(self, df: pd.DataFrame) -> Optional[str]:
        for col in df.columns:
            col_lower = col.lower()
            if ('air' in col_lower and 'ground' in col_lower) or col_lower == 'air_ground_switch':
                test_data = df[col].dropna()
                if len(test_data) > 0:
                    return col
        return None

    def _has_ground_segment(self, series: pd.Series) -> bool:
        valid = series.dropna()
        if len(valid) == 0:
            return False

        for value in valid:
            text = str(value).strip().upper()
            if text in ['GROUND', '1', '1.0']:
                return True
            if isinstance(value, (int, float)) and value == 1:
                return True
        return False
