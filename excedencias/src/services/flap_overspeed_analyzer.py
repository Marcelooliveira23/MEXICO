"""
Flap/Slat Extended Speed Analyzer
Implements AMM TASK 05-50-05 (Flap Configuration) and 05-50-13 (Flap/Slat Extended Speed)
ETAPA 5: Flap/Slat overspeed detection with model-specific flap speed limits
Validates against maximum flap extension speeds per flap position
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from utils.logger import logger


@dataclass
class FlapResult:
    """Resultado da análise de flap overspeed"""
    status: str  # "NORMAL", "FLAP_1_EXCEEDED", "FLAP_2_EXCEEDED", etc.
    max_ias: float
    flap_position: str  # "FLAP_1", "FLAP_2", "FLAP_3", "FLAP_4", "FLAP_FULL"
    exceeded_limit: Optional[float]  # Speed limit that was exceeded
    exceedance: Optional[float]  # How much limit was exceeded
    severity: str  # "NORMAL", "LOW", "HIGH", "CRITICAL"
    message: str
    altitude_ft: Optional[float]
    timestamp: Optional[str]


class FlapAnalyzer:
    """
    Analisador de Flap/Slat Extended Speed seguindo AMM TASK 05-50-05/13
    
    Flap speed limits vary by flap position:
    - Flap 1: ~250 KIAS
    - Flap 2: ~230 KIAS
    - Flap 3: ~210 KIAS
    - Flap 4: ~200 KIAS
    - Flap FULL: ~180 KIAS
    """
    
    # Flap speed specifications per model family
    FLAP_SPEEDS = {
        'e145': {
            'flap_9': 200,
            'flap_18': 180,
            'flap_22': 170,
            'flap_45': 145,
            'inspection_threshold': 160,
        },
        'e135': {
            'flap_9': 200,
            'flap_18': 180,
            'flap_22': 170,
            'flap_45': 145,
            'inspection_threshold': 160,
        },
        'e140': {
            'flap_9': 200,
            'flap_18': 180,
            'flap_22': 170,
            'flap_45': 145,
            'inspection_threshold': 160,
        },
        'e170': {
            'flap_1': 250,
            'flap_2': 230,
            'flap_3': 210,
            'flap_4': 200,
            'flap_full': 180,
            'inspection_threshold': 190,
        },
        'e175': {
            'flap_1': 250,
            'flap_2': 230,
            'flap_3': 210,
            'flap_4': 200,
            'flap_full': 180,
            'inspection_threshold': 190,
        },
        'e190': {
            'flap_1': 250,
            'flap_2': 230,
            'flap_3': 210,
            'flap_4': 200,
            'flap_full': 180,
            'inspection_threshold': 190,
        },
        'e195': {
            'flap_1': 250,
            'flap_2': 230,
            'flap_3': 210,
            'flap_4': 200,
            'flap_full': 180,
            'inspection_threshold': 190,
        },
        'e175_e2': {
            'flap_1': 260,
            'flap_2': 240,
            'flap_3': 220,
            'flap_4': 210,
            'flap_full': 190,
            'inspection_threshold': 200,
        },
        'e190_e2': {
            'flap_1': 260,
            'flap_2': 240,
            'flap_3': 220,
            'flap_4': 210,
            'flap_full': 190,
            'inspection_threshold': 200,
        },
        'e195_e2': {
            'flap_1': 260,
            'flap_2': 240,
            'flap_3': 220,
            'flap_4': 210,
            'flap_full': 190,
            'inspection_threshold': 200,
        },
    }
    
    def get_flap_speeds(self, model_id: str) -> Dict:
        """Get flap speed limits for specific model"""
        model_lower = model_id.lower()
        if model_lower in self.FLAP_SPEEDS:
            return self.FLAP_SPEEDS[model_lower]
        return self.FLAP_SPEEDS['e170']  # Fallback
    
    def analyze(self, df: pd.DataFrame, weight_kg: float, model: str) -> List[FlapResult]:
        """Analyze flap overspeed events"""
        results = []

        def _resolve_column(candidates: List[str]) -> Optional[str]:
            lower_map = {str(col).lower(): col for col in df.columns}
            for candidate in candidates:
                mapped = lower_map.get(candidate.lower())
                if mapped is not None:
                    return mapped
            return None
        
        # Validate required columns
        ias_col = _resolve_column(['IAS', 'airspeed', 'speed', 'velocidade'])
        flap_col = _resolve_column(['FLAP_POSITION', 'flap_position', 'flaps'])

        if ias_col is None or flap_col is None:
            logger.error("[ETAPA 5] IAS or FLAP_POSITION column not found")
            return [FlapResult(
                status="ERROR",
                max_ias=0,
                flap_position="UNKNOWN",
                exceeded_limit=None,
                exceedance=None,
                severity="ERROR",
                message="Missing IAS or FLAP_POSITION column",
                altitude_ft=None,
                timestamp=None
            )]
        
        flap_limits = self.get_flap_speeds(model)
        logger.info(f"[ETAPA 5] Analyzing Flap Overspeed for {model.upper()}")
        
        ias_series = pd.to_numeric(df[ias_col], errors='coerce')
        max_ias = float(ias_series.max()) if not ias_series.dropna().empty else 0.0
        flap_series = df[flap_col].astype(str)
        flap_pos = flap_series.iloc[0] if len(flap_series) > 0 else "UNKNOWN"
        
        # Map flap position to limit
        flap_limit = None
        status = "NORMAL"
        severity = "NORMAL"
        exceedance = None
        flap_pos_detected = None
        max_ias_at_pos = None
        
        # Check against flap limits
        for position, limit in flap_limits.items():
            if position not in ['inspection_threshold']:
                mask = flap_series.str.contains(position, case=False, na=False)
                if mask.any():
                    ias_at_position = pd.to_numeric(df.loc[mask, ias_col], errors='coerce').max()
                    if flap_pos_detected is None or ias_at_position > (max_ias_at_pos or -1):
                        flap_pos_detected = position
                        max_ias_at_pos = ias_at_position
                        flap_limit = limit
                    if ias_at_position > limit:
                        status = "FLAP_EXCEEDED"
                        severity = "HIGH"
                        flap_pos = position.upper()
                        flap_limit = limit
                        exceedance = ias_at_position - limit
        if flap_pos_detected and status == "NORMAL":
            flap_pos = flap_pos_detected.upper()
            max_ias = max_ias_at_pos if max_ias_at_pos is not None else max_ias
        
        message = f"Flap {flap_pos}: {max_ias:.0f} KIAS"
        if status == "FLAP_EXCEEDED":
            message = f"Flap overspeed: {max_ias:.0f} KIAS exceeds limit ({flap_limit} KIAS)"
        
        result_limit = flap_limit
        if result_limit is None and flap_pos_detected:
            result_limit = flap_limits.get(flap_pos_detected)

        result = FlapResult(
            status=status,
            max_ias=max_ias,
            flap_position=flap_pos,
            exceeded_limit=result_limit,
            exceedance=exceedance,
            severity=severity,
            message=message,
            altitude_ft=df['ALT'].iloc[0] if 'ALT' in df.columns else None,
            timestamp=df['TIMESTAMP'].iloc[0] if 'TIMESTAMP' in df.columns else None
        )
        
        logger.info(f"[ETAPA 5] Analysis Result: {status} - {message}")
        return [result]
