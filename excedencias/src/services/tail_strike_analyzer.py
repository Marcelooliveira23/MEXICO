"""
Tail Strike Analyzer
Baseado em AMM TASK 05-50-03 e Mexicana FCOM
Versão 1.0 - Fevereiro 2026
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class TailStrikeThresholds:
    """Thresholds para detecção de tail strike por modelo"""
    model: str
    max_pitch_takeoff: float  # Graus
    max_pitch_landing: float  # Graus
    max_pitch_rate: float     # Graus/segundo
    critical_pitch: float     # Acima disso = tail strike provável
    manual_reference: str


@dataclass
class TailStrikeLegacyResult:
    """Resultado simplificado para compatibilidade com API antiga."""
    is_tail_strike: bool
    max_pitch_attitude: float


class TailStrikeAnalyzer:
    """
    Analisador de Tail Strike para todas as famílias Mexicana
    
    Tail Strike ocorre quando:
    1. Pitch angle excede limites estruturais
    2. Pitch rate excessivo durante rotação/flare
    3. Combinação de pitch alto + baixa altura (radar altitude)
    """
    
    # THRESHOLDS POR FAMÍLIA - Baseado em geometria da aeronave e AMM
    THRESHOLDS = {
        "E135": TailStrikeThresholds(
            model="E135",
            max_pitch_takeoff=12.5,
            max_pitch_landing=11.0,
            max_pitch_rate=5.0,
            critical_pitch=13.5,
            manual_reference="AMM 05-50-03 E135 Rev 45"
        ),
        "E140": TailStrikeThresholds(
            model="E140",
            max_pitch_takeoff=12.5,
            max_pitch_landing=11.0,
            max_pitch_rate=5.0,
            critical_pitch=13.5,
            manual_reference="AMM 05-50-03 E140 Rev 45"
        ),
        "E145": TailStrikeThresholds(
            model="E145",
            max_pitch_takeoff=12.5,
            max_pitch_landing=11.0,
            max_pitch_rate=5.0,
            critical_pitch=13.5,
            manual_reference="AMM 05-50-03 E145 Rev 45"
        ),
        "E170": TailStrikeThresholds(
            model="E170",
            max_pitch_takeoff=13.0,
            max_pitch_landing=11.5,
            max_pitch_rate=5.5,
            critical_pitch=14.0,
            manual_reference="AMM 05-50-03 E170 Rev 62"
        ),
        "E175": TailStrikeThresholds(
            model="E175",
            max_pitch_takeoff=13.0,
            max_pitch_landing=11.5,
            max_pitch_rate=5.5,
            critical_pitch=14.0,
            manual_reference="AMM 05-50-03 E175 Rev 62"
        ),
        "E190": TailStrikeThresholds(
            model="E190",
            max_pitch_takeoff=13.5,
            max_pitch_landing=12.0,
            max_pitch_rate=6.0,
            critical_pitch=14.5,
            manual_reference="AMM 05-50-03 E190 Rev 121"
        ),
        "E195": TailStrikeThresholds(
            model="E195",
            max_pitch_takeoff=13.5,
            max_pitch_landing=12.0,
            max_pitch_rate=6.0,
            critical_pitch=14.5,
            manual_reference="AMM 05-50-03 E195 Rev 121"
        ),
        "E190-E2": TailStrikeThresholds(
            model="E190-E2",
            max_pitch_takeoff=14.0,
            max_pitch_landing=12.5,
            max_pitch_rate=6.5,
            critical_pitch=15.0,
            manual_reference="AMM 05-50-03 E2 Rev 12"
        ),
        "E195-E2": TailStrikeThresholds(
            model="E195-E2",
            max_pitch_takeoff=14.0,
            max_pitch_landing=12.5,
            max_pitch_rate=6.5,
            critical_pitch=15.0,
            manual_reference="AMM 05-50-03 E2 Rev 12"
        ),
    }
    
    def __init__(self, model: str = "E190"):
        """
        Inicializa analisador para modelo específico
        
        Args:
            model: Código do modelo (E170, E190, etc.)
        """
        self._set_model(model)

    @staticmethod
    def _normalize_model(model: str) -> str:
        return str(model).upper().replace("_", "-")

    def _set_model(self, model: str) -> None:
        model_key = self._normalize_model(model)
        thresholds = self.THRESHOLDS.get(model_key)
        if not thresholds:
            raise ValueError(
                f"Modelo {model} não suportado. Modelos disponíveis: {list(self.THRESHOLDS.keys())}"
            )
        self.model = model_key
        self.thresholds = thresholds
    
    def detect_flight_phase(self, df: pd.DataFrame, pitch_col: str, 
                           alt_col: str, air_ground_col: str) -> Dict[str, List[int]]:
        """
        Detecta fases de voo relevantes para tail strike
        
        Returns:
            Dict com índices de: takeoff_rotation, landing_flare, go_around
        """
        phases = {
            "takeoff_rotation": [],
            "landing_flare": [],
            "go_around": []
        }
        
        # Encontrar transições AIR/GROUND
        ground_to_air = []
        air_to_ground = []
        
        for i in range(1, len(df)):
            prev_state = df[air_ground_col].iloc[i-1]
            curr_state = df[air_ground_col].iloc[i]
            
            if prev_state == 0 and curr_state == 1:  # GROUND → AIR (Takeoff)
                ground_to_air.append(i)
            elif prev_state == 1 and curr_state == 0:  # AIR → GROUND (Landing)
                air_to_ground.append(i)
        
        # TAKEOFF ROTATION: 5s antes de liftoff até 10s depois
        for liftoff_idx in ground_to_air:
            start = max(0, liftoff_idx - 40)  # 5s antes @ 8sps
            end = min(len(df), liftoff_idx + 80)  # 10s depois
            phases["takeoff_rotation"].extend(range(start, end))
        
        # LANDING FLARE: 15s antes de touchdown
        for touchdown_idx in air_to_ground:
            start = max(0, touchdown_idx - 120)  # 15s antes @ 8sps
            end = touchdown_idx
            phases["landing_flare"].extend(range(start, end))
        
        # GO-AROUND: Detectar aumentos abruptos de pitch durante approach
        # (pitch aumentando > 3°/s por > 2s em baixa altitude)
        if len(df) > 16:
            pitch_diff = df[pitch_col].diff()
            pitch_rate = pitch_diff / 0.125  # 8 sps = 0.125s
            
            for i in range(16, len(df) - 16):
                altitude = df[alt_col].iloc[i]
                pr = pitch_rate.iloc[i]
                
                # Go-around típico: baixa alt + pitch rate alto positivo
                if altitude < 1000 and pr > 3.0:
                    start = max(0, i - 16)
                    end = min(len(df), i + 40)
                    phases["go_around"].extend(range(start, end))
        
        # Remover duplicatas
        for phase in phases:
            phases[phase] = sorted(list(set(phases[phase])))
        
        return phases
    
    def analyze_tail_strike(
        self,
        df: pd.DataFrame,
        pitch_or_model: str,
        alt_col: Optional[str] = None,
        air_ground_col: Optional[str] = None
    ) -> Dict:
        """
        Wrapper compatível com API antiga.

        Se apenas modelo for fornecido, detecta colunas automaticamente e
        retorna TailStrikeLegacyResult. Caso contrário, usa nomes de colunas.
        """
        if alt_col is None and air_ground_col is None:
            self._set_model(pitch_or_model)
            pitch_col = self._find_column(
                df, ["pitch_attitude", "pitch", "theta"]
            )
            alt_col = self._find_column(
                df, ["radio_altitude", "radar_altitude", "radalt", "agl", "altitude"]
            )
            air_ground_col = self._find_column(
                df, ["air_ground_switch", "air_ground", "airground", "weight_on_wheels", "wow"]
            )
            if not pitch_col or not alt_col or not air_ground_col:
                return TailStrikeLegacyResult(False, 0.0)

            result = self._analyze_tail_strike(df, pitch_col, alt_col, air_ground_col)
            max_pitch = 0.0
            if result.get("max_pitch_takeoff") is not None:
                max_pitch = max(max_pitch, result["max_pitch_takeoff"])
            if result.get("max_pitch_landing") is not None:
                max_pitch = max(max_pitch, result["max_pitch_landing"])

            return TailStrikeLegacyResult(
                is_tail_strike=bool(result.get("tail_strike_detected")),
                max_pitch_attitude=float(max_pitch)
            )

        return self._analyze_tail_strike(df, pitch_or_model, alt_col, air_ground_col)

    def _analyze_tail_strike(self, df: pd.DataFrame, pitch_col: str, 
                           alt_col: str, air_ground_col: str) -> Dict:
        """
        Análise completa de tail strike
        
        Args:
            df: DataFrame com dados do voo
            pitch_col: Nome da coluna de pitch angle
            alt_col: Nome da coluna de radar altitude
            air_ground_col: Nome da coluna AIR/GROUND (0=ground, 1=air)
        
        Returns:
            Dict com resultado da análise
        """
        result = {
            "tail_strike_detected": False,
            "severity": "NORMAL",
            "events": [],
            "max_pitch_takeoff": None,
            "max_pitch_landing": None,
            "max_pitch_rate": None,
            "inspection_required": False,
            "manual_reference": self.thresholds.manual_reference
        }
        
        # Limpar dados
        clean_df = df.copy()
        clean_df[pitch_col] = pd.to_numeric(clean_df[pitch_col], errors='coerce')
        clean_df[alt_col] = pd.to_numeric(clean_df[alt_col], errors='coerce')
        clean_df = clean_df.dropna(subset=[pitch_col, alt_col, air_ground_col])
        
        if len(clean_df) < 10:
            result["error"] = "Dados insuficientes"
            return result
        
        # Detectar fases de voo
        phases = self.detect_flight_phase(clean_df, pitch_col, alt_col, air_ground_col)
        
        # ANÁLISE TAKEOFF
        if phases["takeoff_rotation"]:
            takeoff_data = clean_df.iloc[phases["takeoff_rotation"]]
            max_pitch_to = float(takeoff_data[pitch_col].max())
            result["max_pitch_takeoff"] = round(max_pitch_to, 2)
            
            if max_pitch_to > self.thresholds.critical_pitch:
                result["tail_strike_detected"] = True
                result["severity"] = "CRITICAL"
                result["inspection_required"] = True
                result["events"].append({
                    "phase": "TAKEOFF",
                    "max_pitch": round(max_pitch_to, 2),
                    "threshold": self.thresholds.critical_pitch,
                    "exceedance": round(max_pitch_to - self.thresholds.critical_pitch, 2),
                    "classification": "TAIL STRIKE PROBABLE"
                })
            elif max_pitch_to > self.thresholds.max_pitch_takeoff:
                result["tail_strike_detected"] = True
                result["severity"] = "HIGH" if result["severity"] == "NORMAL" else result["severity"]
                result["inspection_required"] = True
                result["events"].append({
                    "phase": "TAKEOFF",
                    "max_pitch": round(max_pitch_to, 2),
                    "threshold": self.thresholds.max_pitch_takeoff,
                    "exceedance": round(max_pitch_to - self.thresholds.max_pitch_takeoff, 2),
                    "classification": "EXCESSIVE PITCH - INSPECTION REQUIRED"
                })
        
        # ANÁLISE LANDING
        if phases["landing_flare"]:
            landing_data = clean_df.iloc[phases["landing_flare"]]
            max_pitch_ldg = float(landing_data[pitch_col].max())
            result["max_pitch_landing"] = round(max_pitch_ldg, 2)
            
            # Verificar pitch em baixa altitude (<50ft)
            low_alt_mask = landing_data[alt_col] < 50
            if low_alt_mask.any():
                max_pitch_low_alt = float(landing_data[low_alt_mask][pitch_col].max())
                
                if max_pitch_low_alt > self.thresholds.critical_pitch:
                    result["tail_strike_detected"] = True
                    result["severity"] = "CRITICAL"
                    result["inspection_required"] = True
                    result["events"].append({
                        "phase": "LANDING",
                        "max_pitch": round(max_pitch_low_alt, 2),
                        "threshold": self.thresholds.critical_pitch,
                        "altitude": "< 50 ft",
                        "exceedance": round(max_pitch_low_alt - self.thresholds.critical_pitch, 2),
                        "classification": "TAIL STRIKE PROBABLE"
                    })
                elif max_pitch_low_alt > self.thresholds.max_pitch_landing:
                    result["tail_strike_detected"] = True
                    result["severity"] = "HIGH" if result["severity"] == "NORMAL" else result["severity"]
                    result["inspection_required"] = True
                    result["events"].append({
                        "phase": "LANDING",
                        "max_pitch": round(max_pitch_low_alt, 2),
                        "threshold": self.thresholds.max_pitch_landing,
                        "altitude": "< 50 ft",
                        "exceedance": round(max_pitch_low_alt - self.thresholds.max_pitch_landing, 2),
                        "classification": "EXCESSIVE PITCH - INSPECTION REQUIRED"
                    })
        
        # ANÁLISE PITCH RATE
        pitch_diff = clean_df[pitch_col].diff()
        pitch_rate = pitch_diff / 0.125  # 8 sps
        max_pitch_rate = float(pitch_rate.abs().max())
        result["max_pitch_rate"] = round(max_pitch_rate, 2)
        
        if max_pitch_rate > self.thresholds.max_pitch_rate * 1.5:  # 50% acima
            result["tail_strike_detected"] = True
            result["severity"] = "HIGH" if result["severity"] == "NORMAL" else result["severity"]
            result["inspection_required"] = True
            result["events"].append({
                "phase": "EXCESSIVE_ROTATION",
                "max_pitch_rate": round(max_pitch_rate, 2),
                "threshold": self.thresholds.max_pitch_rate,
                "exceedance": round(max_pitch_rate - self.thresholds.max_pitch_rate, 2),
                "classification": "EXCESSIVE PITCH RATE - CHECK FOR DAMAGE"
            })
        
        # GO-AROUND ANALYSIS
        if phases["go_around"]:
            ga_data = clean_df.iloc[phases["go_around"]]
            max_pitch_ga = float(ga_data[pitch_col].max())
            
            if max_pitch_ga > self.thresholds.critical_pitch:
                result["tail_strike_detected"] = True
                result["severity"] = "HIGH" if result["severity"] == "NORMAL" else result["severity"]
                result["inspection_required"] = True
                result["events"].append({
                    "phase": "GO-AROUND",
                    "max_pitch": round(max_pitch_ga, 2),
                    "threshold": self.thresholds.critical_pitch,
                    "exceedance": round(max_pitch_ga - self.thresholds.critical_pitch, 2),
                    "classification": "EXCESSIVE PITCH DURING GO-AROUND"
                })
        
        return result

    @staticmethod
    def _find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        """Encontra coluna no DataFrame (case-insensitive)."""
        df_cols_lower = {col.lower(): col for col in df.columns}
        for candidate in candidates:
            if candidate.lower() in df_cols_lower:
                return df_cols_lower[candidate.lower()]
        return None
    
    @classmethod
    def get_all_thresholds(cls) -> Dict[str, TailStrikeThresholds]:
        """Retorna todos os thresholds disponíveis"""
        return cls.THRESHOLDS.copy()
    
    @classmethod
    def get_supported_models(cls) -> List[str]:
        """Retorna lista de modelos suportados"""
        return list(cls.THRESHOLDS.keys())


def analyze_tail_strike_simple(df: pd.DataFrame, model: str, 
                               pitch_col: str = "pitch", 
                               alt_col: str = "radar_altitude",
                               air_ground_col: str = "air_ground") -> Dict:
    """
    Função helper para análise rápida de tail strike
    
    Args:
        df: DataFrame com dados do voo
        model: Modelo da aeronave (E170, E190, etc.)
        pitch_col: Nome da coluna de pitch angle
        alt_col: Nome da coluna de altitude radar
        air_ground_col: Nome da coluna AIR/GROUND
    
    Returns:
        Dict com resultado da análise
    """
    analyzer = TailStrikeAnalyzer(model)
    return analyzer.analyze_tail_strike(df, pitch_col, alt_col, air_ground_col)

