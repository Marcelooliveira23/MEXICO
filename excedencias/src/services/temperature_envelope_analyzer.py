"""
Temperature Envelope Analyzer
Implements off-temperature envelope flight detection
ETAPA 9: Detects flights outside normal operating temperature ranges (TAT and EGT limits)
"""

import pandas as pd
from typing import Dict, List, Optional
from dataclasses import dataclass
from utils.logger import logger


@dataclass
class TempEnvelopeResult:
    """Resultado da análise de temperature envelope"""
    status: str
    max_temp: float
    min_temp: float
    max_limit: float
    min_limit: float
    severity: str
    message: str
    violation_type: str  # "TAT_HIGH", "TAT_LOW", "EGT_HIGH", "EGT_LOW"
    timestamp: Optional[str]


class TemperatureEnvelopeAnalyzer:
    """
    Analisador de Temperature Envelope
    TAT = Total Air Temperature (OAT + ram air effect)
    EGT = Exhaust Gas Temperature
    """
    
    TEMP_LIMITS = {
        'e145': {
            'tat_max': 54,    # °C (ISA+35)
            'tat_min': -54,   # °C
            'egt_takeoff': 925,     # °C (5 min)
            'egt_continuous': 900,  # °C
        },
        'e135': {
            'tat_max': 54,
            'tat_min': -54,
            'egt_takeoff': 925,
            'egt_continuous': 900,
        },
        'e140': {
            'tat_max': 54,
            'tat_min': -54,
            'egt_takeoff': 925,
            'egt_continuous': 900,
        },
        'e170': {
            'tat_max': 54,
            'tat_min': -54,
            'egt_takeoff': 950,
            'egt_continuous': 915,
        },
        'e175': {
            'tat_max': 54,
            'tat_min': -54,
            'egt_takeoff': 950,
            'egt_continuous': 915,
        },
        'e190': {
            'tat_max': 54,
            'tat_min': -54,
            'egt_takeoff': 950,
            'egt_continuous': 915,
        },
        'e195': {
            'tat_max': 54,
            'tat_min': -54,
            'egt_takeoff': 950,
            'egt_continuous': 915,
        },
        'e175_e2': {
            'tat_max': 54,
            'tat_min': -54,
            'egt_takeoff': 960,  # PW1700G
            'egt_continuous': 925,
        },
        'e190_e2': {
            'tat_max': 54,
            'tat_min': -54,
            'egt_takeoff': 960,
            'egt_continuous': 925,
        },
        'e195_e2': {
            'tat_max': 54,
            'tat_min': -54,
            'egt_takeoff': 960,
            'egt_continuous': 925,
        },
    }
    
    def analyze(self, df: pd.DataFrame, weight_kg: float, model: str) -> List[TempEnvelopeResult]:
        """Analyze temperature envelope violations"""
        results = []
        
        limits = self.TEMP_LIMITS.get(model.lower(), self.TEMP_LIMITS['e170'])
        
        logger.info(f"[ETAPA 9] Temperature Envelope for {model.upper()}")
        logger.info(f"         TAT limits: {limits['tat_min']}°C to {limits['tat_max']}°C")
        logger.info(f"         EGT limit: {limits['egt_continuous']}°C continuous")
        
        # Check TAT (Total Air Temperature)
        tat_cols = ['TAT', 'OAT', 'TEMP', 'TEMPERATURE']
        tat_col = next((col for col in tat_cols if col in df.columns), None)
        
        if tat_col:
            max_tat = df[tat_col].max()
            min_tat = df[tat_col].min()
            
            tat_max_limit = limits['tat_max']
            tat_min_limit = limits['tat_min']
            
            if max_tat > tat_max_limit:
                result = TempEnvelopeResult(
                    status="TAT_EXCEEDED",
                    max_temp=max_tat,
                    min_temp=min_tat,
                    max_limit=tat_max_limit,
                    min_limit=tat_min_limit,
                    severity="HIGH",
                    message=f"TAT HIGH: {max_tat:.1f}°C exceeds {tat_max_limit}°C",
                    violation_type="TAT_HIGH",
                    timestamp=df['TIMESTAMP'].iloc[0] if 'TIMESTAMP' in df.columns else None
                )
                results.append(result)
                logger.warning(f"[ETAPA 9] {result.message}")
            
            elif min_tat < tat_min_limit:
                result = TempEnvelopeResult(
                    status="TAT_LOW",
                    max_temp=max_tat,
                    min_temp=min_tat,
                    max_limit=tat_max_limit,
                    min_limit=tat_min_limit,
                    severity="HIGH",
                    message=f"TAT LOW: {min_tat:.1f}°C below {tat_min_limit}°C",
                    violation_type="TAT_LOW",
                    timestamp=df['TIMESTAMP'].iloc[0] if 'TIMESTAMP' in df.columns else None
                )
                results.append(result)
                logger.warning(f"[ETAPA 9] {result.message}")
        
        # Check EGT (Exhaust Gas Temperature)
        egt_cols = ['EGT', 'EGT1', 'EGT_LEFT', 'EGT_RIGHT']
        egt_col = next((col for col in egt_cols if col in df.columns), None)
        
        if egt_col:
            max_egt = df[egt_col].max()
            egt_limit = limits['egt_continuous']
            
            if max_egt > egt_limit:
                result = TempEnvelopeResult(
                    status="EGT_EXCEEDED",
                    max_temp=max_egt,
                    min_temp=0,
                    max_limit=egt_limit,
                    min_limit=0,
                    severity="HIGH",
                    message=f"EGT HIGH: {max_egt:.0f}°C exceeds continuous limit ({egt_limit}°C)",
                    violation_type="EGT_HIGH",
                    timestamp=df['TIMESTAMP'].iloc[0] if 'TIMESTAMP' in df.columns else None
                )
                results.append(result)
                logger.warning(f"[ETAPA 9] {result.message}")
        
        # If no violations
        if not results:
            result = TempEnvelopeResult(
                status="NORMAL",
                max_temp=0,
                min_temp=0,
                max_limit=limits['tat_max'],
                min_limit=limits['tat_min'],
                severity="NORMAL",
                message="Temperature envelope normal",
                violation_type="NONE",
                timestamp=df['TIMESTAMP'].iloc[0] if 'TIMESTAMP' in df.columns else None
            )
            results.append(result)
            logger.info(f"[ETAPA 9] Temperature envelope: NORMAL")
        
        return results
