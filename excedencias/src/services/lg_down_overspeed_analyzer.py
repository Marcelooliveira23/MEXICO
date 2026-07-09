"""
Landing Gear Down Overspeed Analyzer
Implements maximum speed with landing gear extended (VLE)
ETAPA 6: Detects overspeed when landing gear is deployed
"""

import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
from utils.logger import logger


@dataclass
class LGOverspeedResult:
    """Resultado da análise de LG overspeed"""
    status: str
    max_ias: float
    vle_limit: float
    exceedance: Optional[float]
    severity: str
    message: str
    altitude_ft: Optional[float]
    timestamp: Optional[str]


class LGDownOverspeedAnalyzer:
    """
    Analisador de Landing Gear Down Overspeed
    VLE = Velocity Landing Gear Extended
    """
    
    VLE_LIMITS = {
        'e145': 230,
        'e135': 230,
        'e140': 230,
        'e170': 250,
        'e175': 250,
        'e190': 260,
        'e195': 260,
        'e175_e2': 260,
        'e190_e2': 260,
        'e195_e2': 260,
    }
    
    def analyze(self, df: pd.DataFrame, weight_kg: float, model: str) -> List[LGOverspeedResult]:
        """Analyze landing gear down overspeed"""
        results = []
        
        if 'IAS' not in df.columns:
            return [LGOverspeedResult(
                status="ERROR",
                max_ias=0,
                vle_limit=0,
                exceedance=None,
                severity="ERROR",
                message="IAS column not found",
                altitude_ft=None,
                timestamp=None
            )]
        
        vle = self.VLE_LIMITS.get(model.lower(), 250)

        gear_mask = self._get_gear_down_mask(df)
        if gear_mask is not None:
            ias_series = df.loc[gear_mask, 'IAS']
        else:
            ias_series = None

        if ias_series is None or ias_series.dropna().empty:
            if self._is_clear_cruise_without_gear(df):
                max_ias = float(df['IAS'].max())
                status = "NORMAL"
                severity = "NORMAL"
                exceedance = None
                message = (
                    f"Gear state unavailable; cruise profile detected (flaps up), "
                    f"skipping VLE check"
                )
                result = LGOverspeedResult(
                    status=status,
                    max_ias=max_ias,
                    vle_limit=vle,
                    exceedance=exceedance,
                    severity=severity,
                    message=message,
                    altitude_ft=df['ALT'].iloc[0] if 'ALT' in df.columns else None,
                    timestamp=df['TIMESTAMP'].iloc[0] if 'TIMESTAMP' in df.columns else None
                )
                logger.info(f"[ETAPA 6] {status}: {message}")
                return [result]

            max_ias = float(df['IAS'].max())
            if max_ias > vle:
                status = "VLE_EXCEEDED"
                severity = "HIGH"
                exceedance = max_ias - vle
                message = (
                    f"Gear state unavailable; conservative check found overspeed: "
                    f"{max_ias:.0f} KIAS exceeds {vle} KIAS"
                )
            else:
                status = "NORMAL"
                severity = "NORMAL"
                exceedance = None
                message = (
                    f"Gear state unavailable; conservative check within VLE: "
                    f"{max_ias:.0f} KIAS <= {vle} KIAS"
                )
        else:
            max_ias = float(ias_series.max())

            logger.info(f"[ETAPA 6] LG Overspeed for {model.upper()}: VLE={vle} KIAS")

            if max_ias > vle:
                status = "VLE_EXCEEDED"
                severity = "HIGH"
                exceedance = max_ias - vle
                message = f"VLE overspeed: {max_ias:.0f} KIAS exceeds {vle} KIAS"
            else:
                status = "NORMAL"
                severity = "NORMAL"
                exceedance = None
                message = f"LG speed normal: {max_ias:.0f} KIAS < {vle} KIAS"
        
        result = LGOverspeedResult(
            status=status,
            max_ias=max_ias,
            vle_limit=vle,
            exceedance=exceedance,
            severity=severity,
            message=message,
            altitude_ft=df['ALT'].iloc[0] if 'ALT' in df.columns else None,
            timestamp=df['TIMESTAMP'].iloc[0] if 'TIMESTAMP' in df.columns else None
        )
        
        logger.info(f"[ETAPA 6] {status}: {message}")
        return [result]

    def _is_clear_cruise_without_gear(self, df: pd.DataFrame) -> bool:
        flap_columns = [
            col for col in df.columns
            if 'flap' in col.lower()
        ]

        for flap_col in flap_columns:
            series = df[flap_col].dropna()
            if len(series) == 0:
                continue

            normalized = series.astype(str).str.strip().str.upper()
            if (normalized == 'FLAP_0').all() or (normalized == '0').all():
                return True

        return False

    def _get_gear_down_mask(self, df: pd.DataFrame) -> Optional[pd.Series]:
        candidates = [
            "gear",
            "gear_pos",
            "gear_position",
            "gear_down",
            "landing_gear",
            "lg_down",
            "gear_state",
        ]
        cols = {col.lower(): col for col in df.columns}
        column = None
        for candidate in candidates:
            if candidate in cols:
                column = cols[candidate]
                break

        if not column:
            return None

        def is_down(value) -> bool:
            if isinstance(value, str):
                normalized = value.strip().lower()
                return normalized in {"down", "extended", "gear_down", "on", "1", "true"}
            if value is True:
                return True
            try:
                return float(value) > 0
            except (TypeError, ValueError):
                return False

        return df[column].apply(is_down)
