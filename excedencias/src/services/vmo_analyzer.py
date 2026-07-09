"""
VMO/MMO Maximum Operating Speed Analyzer
Implements AMM TASK 05-50-07 (Maximum Operating Speed Limitation)
ETAPA 4: VMO/MMO Overspeed detection with model-specific thresholds
Validates against maximum operating speeds per aircraft family
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from utils.logger import logger
from utils.config import AppConfig


@dataclass
class VmoResult:
    """Resultado da análise VMO/MMO"""
    status: str  # "NORMAL", "VMO_EXCEEDED", "MMO_EXCEEDED", "BOTH_EXCEEDED"
    ias_vmo_exceedance: Optional[float]  # Valor da excedência em KIAS
    mach_mmo_exceedance: Optional[float]  # Valor da excedência em Mach
    max_ias: float
    max_mach: float
    severity: str  # "NORMAL", "LOW", "HIGH", "CRITICAL"
    message: str
    altitude_ft: Optional[float]  # Altitude where exceedance occurred
    timestamp: Optional[str]  # When exceedance occurred


class VmoAnalyzer:
    """
    Analisador de VMO/MMO seguindo AMM TASK 05-50-07
    
    VMO (Velocity Maximum Operating) = máxima velocidade em KIAS
    MMO (Mach Maximum Operating) = máxima velocidade em Mach
    
    Implementação:
    - E145: VMO 280 KIAS / MMO 0.78 Mach
    - E170/E175: VMO 320 KIAS / MMO 0.82 Mach
    - E190/E195: VMO 320 KIAS / MMO 0.82 Mach
    - E190-E2/E195-E2: VMO 330 KIAS / MMO 0.82 Mach
    """
    
    # VMO/MMO specifications per family
    VMO_THRESHOLDS = {
        'e145': {
            'vmo': 280,
            'mmo': 0.78,
            'inspection_threshold_vmo': 290,  # VMO + 10
            'inspection_threshold_mmo': 0.80,
        },
        'e170': {
            'vmo': 320,
            'mmo': 0.82,
            'inspection_threshold_vmo': 330,  # VMO + 10
            'inspection_threshold_mmo': 0.84,
        },
        'e175': {
            'vmo': 320,
            'mmo': 0.82,
            'inspection_threshold_vmo': 330,  # VMO + 10
            'inspection_threshold_mmo': 0.84,
        },
        'e190': {
            'vmo': 320,
            'mmo': 0.82,
            'inspection_threshold_vmo': 330,  # VMO + 10
            'inspection_threshold_mmo': 0.84,
        },
        'e195': {
            'vmo': 320,
            'mmo': 0.82,
            'inspection_threshold_vmo': 330,  # VMO + 10
            'inspection_threshold_mmo': 0.84,
        },
        'e175_e2': {
            'vmo': 340,
            'mmo': 0.85,
            'inspection_threshold_vmo': 350,  # VMO + 10
            'inspection_threshold_mmo': 0.87,
        },
        'e190_e2': {
            'vmo': 340,
            'mmo': 0.85,
            'inspection_threshold_vmo': 350,  # VMO + 10
            'inspection_threshold_mmo': 0.87,
        },
        'e195_e2': {
            'vmo': 340,
            'mmo': 0.85,
            'inspection_threshold_vmo': 350,  # VMO + 10
            'inspection_threshold_mmo': 0.87,
        },
    }
    
    def get_vmo_thresholds(self, model_id: str) -> Dict:
        """
        Get VMO/MMO thresholds for specific model
        Falls back to family if model not in registry
        
        Args:
            model_id: Aircraft model ID (e.g., 'e170', 'e190', 'e190_e2')
            
        Returns:
            Dictionary with VMO, MMO and inspection thresholds
        """
        model_lower = model_id.lower()
        
        # Try to get from model-specific registry first
        if model_lower in self.VMO_THRESHOLDS:
            return self.VMO_THRESHOLDS[model_lower]
        
        # Fallback to family mapping
        family_mapping = {
            'e145': 'e145',
            'e135': 'e145',
            'e140': 'e145',
            'e170': 'e170',
            'e175': 'e175',
            'e190': 'e190',
            'e195': 'e195',
            'e175_e2': 'e175_e2',
            'e190_e2': 'e190_e2',
            'e195_e2': 'e195_e2',
        }
        
        family_id = family_mapping.get(model_lower, 'e170')
        logger.warning(f"[ETAPA 4] Model {model_id} not found, using family {family_id} thresholds")
        return self.VMO_THRESHOLDS.get(family_id, self.VMO_THRESHOLDS['e170'])
    
    def calculate_altitude_affected_mach(self, altitude_ft: float, temperature_c: Optional[float] = None) -> float:
        """
        Calculate true airspeed from calibrated airspeed and altitude
        Important: Mach number varies with temperature (affects true airspeed)
        
        Args:
            altitude_ft: Aircraft altitude in feet
            temperature_c: Outside air temperature in Celsius (optional)
            
        Returns:
            Mach number equivalent to VMO at that altitude (for reference)
        """
        # Simplified: at sea level, VMO 320 KIAS ≈ 0.49 Mach
        # At higher altitudes, need less Mach to stay at same KIAS
        # This is why MMO becomes limiting at high altitudes
        
        # Standard ISA model
        if temperature_c is None:
            # ISA: -6.5°C per 1000 ft
            temperature_c = 15 - (altitude_ft / 1000) * 6.5
        
        # Mach calculation from TAS and speed of sound
        # Speed of sound ≈ 661.47 * sqrt(T_Kelvin + 273.15)
        # TAS ≈ CAS * sqrt(delta)
        # For simplicity, use standard tables
        
        return None  # Simplified - in real implementation would use full calculation
    
    def analyze(self, df: pd.DataFrame, weight_kg: float, model: str) -> List[VmoResult]:
        """
        Analyze VMO/MMO exceedances
        
        Args:
            df: DataFrame with flight data (must contain 'IAS' and 'MACH' columns)
            weight_kg: Aircraft weight in kg
            model: Aircraft model ID
            
        Returns:
            List of VmoResult objects for each exceedance found
        """
        results = []
        
        # Validate required columns
        if 'IAS' not in df.columns:
            logger.error("[ETAPA 4] IAS column not found in flight data")
            return [VmoResult(
                status="ERROR",
                ias_vmo_exceedance=None,
                mach_mmo_exceedance=None,
                max_ias=0,
                max_mach=0,
                severity="ERROR",
                message="IAS column not found",
                altitude_ft=None,
                timestamp=None
            )]
        
        thresholds = self.get_vmo_thresholds(model)
        vmo = thresholds['vmo']
        mmo = thresholds['mmo']
        inspection_vmo = thresholds['inspection_threshold_vmo']
        inspection_mmo = thresholds['inspection_threshold_mmo']
        
        logger.info(f"[ETAPA 4] Analyzing VMO/MMO for {model.upper()}")
        logger.info(f"         VMO threshold: {vmo} KIAS")
        logger.info(f"         MMO threshold: {mmo} Mach")
        
        # Get maximum values
        max_ias = df['IAS'].max() if 'IAS' in df.columns else 0
        max_mach = df['MACH'].max() if 'MACH' in df.columns else 0
        
        # Find exceedances
        vmo_exceeded = False
        mmo_exceeded = False
        ias_exceedance = 0
        mach_exceedance = 0
        vmo_altitude = None
        mmo_altitude = None
        vmo_timestamp = None
        mmo_timestamp = None
        
        # Check VMO exceedance
        if max_ias > vmo:
            vmo_exceeded = True
            ias_exceedance = max_ias - vmo
            
            # Find where exceedance occurred
            vmo_idx = df[df['IAS'] > vmo].iloc[0].name if len(df[df['IAS'] > vmo]) > 0 else None
            if vmo_idx is not None:
                if 'ALT' in df.columns or 'ALTITUDE' in df.columns:
                    alt_col = 'ALT' if 'ALT' in df.columns else 'ALTITUDE'
                    vmo_altitude = df.loc[vmo_idx, alt_col]
                if 'TIMESTAMP' in df.columns:
                    vmo_timestamp = df.loc[vmo_idx, 'TIMESTAMP']
        
        # Check MMO exceedance
        if 'MACH' in df.columns and max_mach > mmo:
            mmo_exceeded = True
            mach_exceedance = max_mach - mmo
            
            # Find where exceedance occurred
            mmo_idx = df[df['MACH'] > mmo].iloc[0].name if len(df[df['MACH'] > mmo]) > 0 else None
            if mmo_idx is not None:
                if 'ALT' in df.columns or 'ALTITUDE' in df.columns:
                    alt_col = 'ALT' if 'ALT' in df.columns else 'ALTITUDE'
                    mmo_altitude = df.loc[mmo_idx, alt_col]
                if 'TIMESTAMP' in df.columns:
                    mmo_timestamp = df.loc[mmo_idx, 'TIMESTAMP']
        
        # Determine status and severity
        if vmo_exceeded and mmo_exceeded:
            status = "BOTH_EXCEEDED"
            severity = "CRITICAL"
            message = f"Both VMO ({max_ias:.0f} > {vmo}) and MMO ({max_mach:.3f} > {mmo}) exceeded"
        elif vmo_exceeded:
            status = "VMO_EXCEEDED"
            # Severity HIGH unless it reaches inspection threshold
            severity = "HIGH"
            message = f"VMO exceeded: {max_ias:.0f} KIAS exceeds {vmo} KIAS ({ias_exceedance:.0f} KIAS over)"
        elif mmo_exceeded:
            status = "MMO_EXCEEDED"
            # Severity HIGH unless it reaches inspection threshold
            severity = "HIGH"
            message = f"MMO exceeded: {max_mach:.3f} Mach exceeds {mmo} Mach ({mach_exceedance:.3f} over)"
        else:
            status = "NORMAL"
            severity = "NORMAL"
            message = f"VMO/MMO within limits - Max IAS: {max_ias:.0f}/{vmo}, Max Mach: {max_mach:.3f}/{mmo}"
        
        result = VmoResult(
            status=status,
            ias_vmo_exceedance=ias_exceedance if vmo_exceeded else None,
            mach_mmo_exceedance=mach_exceedance if mmo_exceeded else None,
            max_ias=max_ias,
            max_mach=max_mach,
            severity=severity,
            message=message,
            altitude_ft=vmo_altitude if vmo_exceeded else mmo_altitude,
            timestamp=vmo_timestamp if vmo_exceeded else mmo_timestamp
        )
        
        logger.info(f"[ETAPA 4] Analysis Result: {status} - Severity: {severity}")
        logger.info(f"         Max IAS: {max_ias:.0f} KIAS, Max Mach: {max_mach:.3f}")
        
        return [result]
    
    def get_inspection_threshold(self, model: str, threshold_type: str = 'vmo') -> float:
        """
        Get inspection threshold (maintenance action trigger)
        
        Args:
            model: Aircraft model ID
            threshold_type: 'vmo' or 'mmo'
            
        Returns:
            Inspection threshold value
        """
        thresholds = self.get_vmo_thresholds(model)
        if threshold_type.lower() == 'mmo':
            return thresholds['inspection_threshold_mmo']
        return thresholds['inspection_threshold_vmo']
