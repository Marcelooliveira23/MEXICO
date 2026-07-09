"""
Motor de análise de dados baseado em regras dos PDFs
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
from utils.logger import logger
from utils.model_selection import normalize_model_id, get_model_name_for_analyzers

# Import dynamic rules extractor
try:
    from services.pdf_rules_extractor import PDFRulesExtractor, TechnicalLimit
    PDF_RULES_AVAILABLE = True

except ImportError:
    PDF_RULES_AVAILABLE = False
    logger.warning("PDFRulesExtractor not available, using fallback rules")

# Import specifications and analyzers
try:
    from services.all_families_specs import get_specifications_by_model
    SPECS_AVAILABLE = True
except ImportError:
    SPECS_AVAILABLE = False
    logger.warning("all_families_specs not available")

try:
    from services.hard_landing_analyzer import HardLandingAnalyzer, HardLandingResult, HardLandingLegacyResult
    HARD_LANDING_ANALYZER_AVAILABLE = True
except ImportError:
    HARD_LANDING_ANALYZER_AVAILABLE = False
    logger.warning("HardLandingAnalyzer not available, using basic analysis")

try:
    from services.over_g_analyzer import OverGAnalyzer, OverGResult
    OVER_G_ANALYZER_AVAILABLE = True
except ImportError:
    OVER_G_ANALYZER_AVAILABLE = False
    logger.warning("OverGAnalyzer not available")

try:
    from services.high_bank_angle_analyzer import HighBankAngleAnalyzer, HighBankAngleResult
    HIGH_BANK_ANGLE_ANALYZER_AVAILABLE = True
except ImportError:
    HIGH_BANK_ANGLE_ANALYZER_AVAILABLE = False
    logger.warning("HighBankAngleAnalyzer not available")

try:
    from services.turbulence_analyzer import TurbulenceAnalyzer, TurbulenceResult
    TURBULENCE_ANALYZER_AVAILABLE = True
except ImportError:
    TURBULENCE_ANALYZER_AVAILABLE = False
    logger.warning("TurbulenceAnalyzer not available")

try:
    from services.vmo_analyzer import VmoAnalyzer, VmoResult
    VMO_ANALYZER_AVAILABLE = True
except ImportError:
    VMO_ANALYZER_AVAILABLE = False
    logger.warning("VmoAnalyzer not available")

try:
    from services.flap_overspeed_analyzer import FlapAnalyzer, FlapResult
    FLAP_ANALYZER_AVAILABLE = True
except ImportError:
    FLAP_ANALYZER_AVAILABLE = False
    logger.warning("FlapAnalyzer not available")

try:
    from services.lg_down_overspeed_analyzer import LGDownOverspeedAnalyzer, LGOverspeedResult
    LG_OVERSPEED_ANALYZER_AVAILABLE = True
except ImportError:
    LG_OVERSPEED_ANALYZER_AVAILABLE = False
    logger.warning("LGDownOverspeedAnalyzer not available")

try:
    from services.overweight_landing_analyzer import OverweightLandingAnalyzer, OverweightResult
    OVERWEIGHT_ANALYZER_AVAILABLE = True
except ImportError:
    OVERWEIGHT_ANALYZER_AVAILABLE = False
    logger.warning("OverweightLandingAnalyzer not available")

try:
    from services.temperature_envelope_analyzer import TemperatureEnvelopeAnalyzer, TempEnvelopeResult
    TEMP_ENVELOPE_ANALYZER_AVAILABLE = True
except ImportError:
    TEMP_ENVELOPE_ANALYZER_AVAILABLE = False
    logger.warning("TemperatureEnvelopeAnalyzer not available")


@dataclass
class AnalysisResult:
    """Resultado de uma análise"""
    status: str  # "OK", "WARNING", "VIOLATION"
    parameter: str
    value: Any
    limit: Optional[Any]
    message: str
    severity: str  # "LOW", "MEDIUM", "HIGH", "CRITICAL"


@dataclass
class FlightAnalysis:
    """Análise completa de um voo"""
    aircraft_id: str
    event_type: str
    timestamp: datetime
    tail_number: str
    flight_number: Optional[str]
    results: List[AnalysisResult]
    overall_status: str
    recommendations: List[str]


class RulesEngine:
    """Motor de regras para análise de dados de inspeção"""
    
    # Regras básicas por tipo de evento (serão expandidas conforme análise dos PDFs)
    RULES = {
        # Hard Landing - valores exemplo (ajustar conforme PDFs)
        "hard_landing": {
            "e145": {
                "vertical_speed_limit": -600,  # fpm
                "g_force_limit": 2.0,
                "touchdown_rate_limit": 360  # fpm
            },
            "e170": {
                "vertical_speed_limit": -600,
                "g_force_limit": 2.1,
                "touchdown_rate_limit": 360
            },
            "e1": {
                "vertical_speed_limit": -600,
                "g_force_limit": 2.2,
                "touchdown_rate_limit": 360
            },
            "e2": {
                "vertical_speed_limit": -600,
                "g_force_limit": 2.0,
                "touchdown_rate_limit": 360
            }
        },
        
        # Landing Gear Down Overspeed
        "gear_overspeed": {
            "e145": {
                "max_speed_gear_down": 230,  # KIAS
                "max_speed_gear_extension": 230
            },
            "e170": {
                "max_speed_gear_down": 250,
                "max_speed_gear_extension": 250
            },
            "e1": {
                "max_speed_gear_down": 260,
                "max_speed_gear_extension": 260
            },
            "e2": {
                "max_speed_gear_down": 260,
                "max_speed_gear_extension": 260
            }
        },
        
        # Off-Temperature Envelope Flight
        "temp_envelope": {
            "e145": {
                "min_temperature": -54,  # °C
                "max_temperature": 54
            },
            "e170": {
                "min_temperature": -54,
                "max_temperature": 54
            },
            "e1": {
                "min_temperature": -54,
                "max_temperature": 54
            },
            "e2": {
                "min_temperature": -54,
                "max_temperature": 54
            }
        },
        
        # Maximum Operating Speed
        "max_speed": {
            "e145": {
                "vmo": 280,  # KIAS
                "mmo": 0.78  # Mach
            },
            "e170": {
                "vmo": 320,
                "mmo": 0.82
            },
            "e1": {
                "vmo": 320,
                "mmo": 0.82
            },
            "e2": {
                "vmo": 330,
                "mmo": 0.82
            }
        },
        
        # Maximum Flap/Slat Extended Speed
        "flap_overspeed": {
            "e145": {
                "flaps_1": 200,  # KIAS
                "flaps_2": 180,
                "flaps_3": 170,
                "flaps_full": 145
            },
            "e170": {
                "flaps_1": 250,
                "flaps_2": 230,
                "flaps_3": 210,
                "flaps_full": 180
            },
            "e1": {
                "flaps_1": 250,
                "flaps_2": 230,
                "flaps_3": 210,
                "flaps_full": 180
            },
            "e2": {
                "flaps_1": 260,
                "flaps_2": 240,
                "flaps_3": 220,
                "flaps_full": 190
            }
        },
        
        # Overweight Landing
        "overweight_landing": {
            "e145": {
                "max_landing_weight": 44000  # lbs
            },
            "e170": {
                "max_landing_weight": 69224
            },
            "e1": {
                "max_landing_weight": 108247
            },
            "e2": {
                "max_landing_weight": 110674
            }
        },

        # Turbulence Encounter
        "turbulence": {
            "e145": {
                "max_positive_g": 2.2,
                "max_negative_g": -0.8,
                "max_turbulence_speed": 280
            },
            "e170": {
                "max_positive_g": 2.5,
                "max_negative_g": -1.0,
                "max_turbulence_speed": 280
            },
            "e1": {
                "max_positive_g": 2.5,
                "max_negative_g": -1.0,
                "max_turbulence_speed": 280
            },
            "e2": {
                "max_positive_g": 2.5,
                "max_negative_g": -1.0,
                "max_turbulence_speed": 280
            }
        },

        # Over-G Maneuver
        "over_g": {
            "e145": {
                "max_positive_g": 3.5,
                "max_negative_g": -3.5
            },
            "e170": {
                "max_positive_g": 3.5,
                "max_negative_g": -3.5
            },
            "e1": {
                "max_positive_g": 3.5,
                "max_negative_g": -3.5
            },
            "e2": {
                "max_positive_g": 3.8,
                "max_negative_g": -3.8
            }
        },

        # High Bank Angle
        "high_bank_angle": {
            "e145": {
                "normal": 60.0,
                "emergency": 67.0
            },
            "e170": {
                "normal": 60.0,
                "emergency": 67.0
            },
            "e1": {
                "normal": 60.0,
                "emergency": 67.0
            },
            "e2": {
                "normal": 60.0,
                "emergency": 67.0
            }
        },
        
        # CG Limits
        "cg_limits": {
            "e145": {
                "forward_limit": 16.0,  # % MAC
                "aft_limit": 34.0
            },
            "e170": {
                "forward_limit": 16.0,
                "aft_limit": 35.0
            },
            "e1": {
                "forward_limit": 18.0,
                "aft_limit": 37.0
            },
            "e2": {
                "forward_limit": 15.0,
                "aft_limit": 39.0
            }
        }
    }
    
    _pdf_rules_cache = {}  # Cache for extracted PDF rules
    
    @classmethod
    def load_dynamic_rules(cls, aircraft_id: str, event_type: str) -> Dict:
        """
        Load dynamic rules from PDFs if available
        
        Args:
            aircraft_id: Aircraft family ID
            event_type: Event type
            
        Returns:
            Dictionary of rules
        """
        if not PDF_RULES_AVAILABLE:
            return cls.RULES.get(event_type, {}).get(aircraft_id, {})
        
        # Check cache
        cache_key = f"{aircraft_id}_{event_type}"
        if cache_key in cls._pdf_rules_cache:
            return cls._pdf_rules_cache[cache_key]
        
        try:
            extractor = PDFRulesExtractor()
            all_rules = extractor.extract_all_rules(aircraft_id)
            
            # Map event types
            event_map = {
                "hard_landing": "HARD_LANDING",
                "gear_overspeed": "GEAR_OVERSPEED",
                "temp_envelope": "TEMPERATURE",
                "max_speed": "SPEED",
                "flap_overspeed": "FLAP_SPEED",
                "overweight_landing": "OVERWEIGHT",
                "turbulence": "TURBULENCE",
                "over_g": "OVER_G",
                "high_bank_angle": "HIGH_BANK_ANGLE"
            }
            
            pdf_event_type = event_map.get(event_type)
            if pdf_event_type and pdf_event_type in all_rules:
                inspection_rule = all_rules[pdf_event_type]
                
                # Convert to rules dict
                dynamic_rules = {}
                for limit in inspection_rule.limits:
                    dynamic_rules[limit.parameter] = limit.value

                # Merge with static rules (sanitized where needed)
                static_rules = cls.RULES.get(event_type, {}).get(aircraft_id, {})
                dynamic_rules = cls._sanitize_dynamic_rules(event_type, static_rules, dynamic_rules)
                merged_rules = {**static_rules, **dynamic_rules}

                cls._pdf_rules_cache[cache_key] = merged_rules
                logger.info(f"Loaded {len(dynamic_rules)} dynamic rules for {aircraft_id}/{event_type}")
                return merged_rules
            
        except Exception as e:
            logger.error(f"Error loading dynamic rules: {e}")
        
        # Fallback to static rules
        return cls.RULES.get(event_type, {}).get(aircraft_id, {})

    @staticmethod
    def _sanitize_dynamic_rules(event_type: str, static_rules: Dict, dynamic_rules: Dict) -> Dict:
        """Sanitize dynamic PDF rules to avoid invalid overrides."""
        if not dynamic_rules:
            return dynamic_rules

        sanitized = dict(dynamic_rules)

        if event_type == "turbulence":
            pos = sanitized.get("max_positive_g")
            neg = sanitized.get("max_negative_g")
            spd = sanitized.get("max_turbulence_speed")

            if not isinstance(pos, (int, float)) or pos <= 0.5 or pos > 6.0:
                sanitized.pop("max_positive_g", None)
            if not isinstance(neg, (int, float)) or neg >= -0.1 or neg < -6.0:
                sanitized.pop("max_negative_g", None)
            if not isinstance(spd, (int, float)) or spd < 100 or spd > 400:
                sanitized.pop("max_turbulence_speed", None)

            if "max_positive_g" in sanitized and "max_positive_g" in static_rules:
                if float(sanitized["max_positive_g"]) < 0.5 * float(static_rules["max_positive_g"]):
                    sanitized.pop("max_positive_g", None)

        return sanitized
    
    @classmethod
    def analyze(cls, df: pd.DataFrame, aircraft_id: str, event_type: str) -> FlightAnalysis:
        """
        Analisa dados do voo baseado nas regras
        
        Args:
            df: DataFrame com dados do voo
            aircraft_id: ID da família da aeronave
            event_type: Tipo de evento a analisar
            
        Returns:
            FlightAnalysis com resultados
        """
        results = []
        recommendations = []
        
        # Load rules (dynamic from PDFs or static fallback)
        rules = cls.load_dynamic_rules(aircraft_id, event_type)
        
        if not rules:
            return FlightAnalysis(
                aircraft_id=aircraft_id,
                event_type=event_type,
                timestamp=datetime.now(),
                tail_number="N/A",
                flight_number=None,
                results=[],
                overall_status="NO_RULES",
                recommendations=["Regras não disponíveis para esta combinação"]
            )
        
        # Extrair informações básicas
        tail = cls._extract_value(df, ['tail', 'tail_number', 'matricula', 'registration', 'aircraft'])
        flight_number = cls._extract_value(df, ['flight_number', 'flight', 'flight_no', 'flt', 'voo', 'numero_voo'])
        event_timestamp = cls._extract_timestamp(df)
        
        # Aplicar regras específicas por tipo de evento
        if event_type == "hard_landing":
            # Extrair modelo da aeronave se disponível
            model = cls._extract_value(df, ['model', 'modelo', 'aircraft_model'])
            model = model or cls._get_default_model_for_family(aircraft_id)
            results.extend(cls._analyze_hard_landing(df, rules, aircraft_id, str(model)))
        elif event_type == "gear_overspeed":
            model = cls._extract_value(df, ['model', 'modelo', 'aircraft_model'])
            model = model or cls._get_default_model_for_family(aircraft_id)
            results.extend(cls._analyze_gear_overspeed(df, rules, aircraft_id, str(model)))
        elif event_type == "temp_envelope":
            model = cls._extract_value(df, ['model', 'modelo', 'aircraft_model'])
            model = model or cls._get_default_model_for_family(aircraft_id)
            results.extend(cls._analyze_temperature_envelope(df, rules, aircraft_id, str(model)))
        elif event_type == "max_speed":
            model = cls._extract_value(df, ['model', 'modelo', 'aircraft_model'])
            model = model or cls._get_default_model_for_family(aircraft_id)
            results.extend(cls._analyze_max_speed(df, rules, aircraft_id, str(model)))
        elif event_type == "flap_overspeed":
            model = cls._extract_value(df, ['model', 'modelo', 'aircraft_model'])
            model = model or cls._get_default_model_for_family(aircraft_id)
            results.extend(cls._analyze_flap_overspeed(df, rules, aircraft_id, str(model)))
        elif event_type == "overweight_landing":
            model = cls._extract_value(df, ['model', 'modelo', 'aircraft_model'])
            model = model or cls._get_default_model_for_family(aircraft_id)
            results.extend(cls._analyze_overweight_landing(df, rules, aircraft_id, str(model)))
        elif event_type == "cg_limits":
            model = cls._extract_value(df, ['model', 'modelo', 'aircraft_model'])
            model = model or cls._get_default_model_for_family(aircraft_id)
            results.extend(cls._analyze_cg_limits(df, rules, aircraft_id, str(model)))
        elif event_type == "turbulence":
            model = cls._extract_value(df, ['model', 'modelo', 'aircraft_model'])
            model = model or cls._get_default_model_for_family(aircraft_id)
            results.extend(cls._analyze_turbulence(df, rules, aircraft_id, str(model)))
        elif event_type == "over_g":
            model = cls._extract_value(df, ['model', 'modelo', 'aircraft_model'])
            model = model or cls._get_default_model_for_family(aircraft_id)
            results.extend(cls._analyze_over_g(df, rules, aircraft_id, str(model)))
        elif event_type == "high_bank_angle":
            model = cls._extract_value(df, ['model', 'modelo', 'aircraft_model'])
            model = model or cls._get_default_model_for_family(aircraft_id)
            results.extend(cls._analyze_high_bank_angle(df, rules, aircraft_id, str(model)))
        
        # Determinar status geral
        overall_status = cls._determine_overall_status(results)
        
        # Gerar recomendações
        recommendations = cls._generate_recommendations(results, event_type)
        
        return FlightAnalysis(
            aircraft_id=aircraft_id,
            event_type=event_type,
            timestamp=event_timestamp,
            tail_number=tail or "N/A",
            flight_number=flight_number,
            results=results,
            overall_status=overall_status,
            recommendations=recommendations
        )
    
    @staticmethod
    def _extract_value(df: pd.DataFrame, column_names: List[str]) -> Optional[Any]:
        """Extrai valor de uma das colunas possíveis (case-insensitive)"""
        columns_lower = {col.lower(): col for col in df.columns}
        for name in column_names:
            if name in columns_lower:
                try:
                    return df[columns_lower[name]].iloc[0]
                except:
                    pass
        return None

    @staticmethod
    def _extract_timestamp(df: pd.DataFrame) -> datetime:
        """Extracts event timestamp from available columns or falls back to now."""
        value = RulesEngine._extract_value(
            df,
            ['timestamp', 'datetime', 'date_time', 'date', 'time']
        )
        if value is None and 'TIMESTAMP' in df.columns:
            try:
                value = df['TIMESTAMP'].iloc[0]
            except Exception:
                value = None
        if value is None:
            return datetime.now()
        try:
            parsed = pd.to_datetime(value, errors='coerce')
            if pd.isna(parsed):
                return datetime.now()
            return parsed.to_pydatetime()
        except Exception:
            return datetime.now()
    
    @staticmethod
    def _find_column(df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        """Encontra coluna no DataFrame (case-insensitive)"""
        df_cols_lower = {col.lower(): col for col in df.columns}
        for candidate in candidates:
            if candidate.lower() in df_cols_lower:
                return df_cols_lower[candidate.lower()]
        return None

    @staticmethod
    def _get_default_model_for_family(aircraft_id: str) -> str:
        """Retorna modelo padrão baseado na família"""
        family = (aircraft_id or '').lower()
        mapping = {
            'e145': 'E145',
            'e170': 'E170',
            'e1': 'E190',
            'e2': 'E190-E2'
        }
        return mapping.get(family, 'E190')

    @staticmethod
    def _normalize_model_id(model: str | None, aircraft_id: str) -> str:
        """Normaliza model_id para uso nos analyzers (lower + underscore)."""
        if model is None:
            model = RulesEngine._get_default_model_for_family(aircraft_id)
        normalized = normalize_model_id(str(model))
        if normalized:
            return normalized
        return normalize_model_id(RulesEngine._get_default_model_for_family(aircraft_id)) or "e190"

    @staticmethod
    def _normalize_model_name(model: str | None, aircraft_id: str) -> str:
        """Normaliza nome de modelo para uso em analyzers que esperam E170/E190-E2."""
        model_id = RulesEngine._normalize_model_id(model, aircraft_id)
        return get_model_name_for_analyzers(model_id) or str(model or "E190")

    @staticmethod
    def _extract_weight_kg(df: pd.DataFrame) -> float | None:
        """Extrai peso do DataFrame e normaliza para kg."""
        weight_cols = [
            col for col in df.columns
            if "weight" in col.lower() or "gross" in col.lower()
        ]
        if not weight_cols:
            return None

        col_name = weight_cols[0]
        weight_value = df[col_name].dropna().iloc[0] if len(df[col_name].dropna()) > 0 else None
        if weight_value is None:
            return None

        try:
            weight_float = float(weight_value)
        except Exception:
            return None

        col_lower = col_name.lower()
        if "kg" in col_lower and "lb" not in col_lower:
            return weight_float
        if "lb" in col_lower or "lbs" in col_lower:
            return weight_float * 0.453592

        # Heuristica: valores altos normalmente sao lbs
        if weight_float > 60000:
            return weight_float * 0.453592
        return weight_float
    
    @staticmethod
    def _analyze_hard_landing(df: pd.DataFrame, rules: Dict, aircraft_id: str = 'e1', model: str = 'E190') -> List[AnalysisResult]:
        """Analisa parâmetros de hard landing com sistema de 3 monitores"""
        results = []
        
        logger.info(f"=== ANÁLISE HARD LANDING ===")
        logger.info(f"Aircraft: {aircraft_id}, Model: {model}")
        logger.info(f"DataFrame shape: {df.shape}")
        logger.info(f"Colunas disponíveis: {list(df.columns)}")
        
        # Se disponível, usar HardLandingAnalyzer completo
        if HARD_LANDING_ANALYZER_AVAILABLE and SPECS_AVAILABLE:
            try:
                model_name = RulesEngine._normalize_model_name(model, aircraft_id)
                # Obter especificações
                logger.info("Obtendo especificações do modelo...")
                specs = get_specifications_by_model(aircraft_id, model_name)
                logger.info(f"MLW do modelo: {specs.mlw_kg} kg")
                
                # Extrair peso do voo (ou usar MLW como fallback)
                weight = RulesEngine._extract_value(df, ['gross_weight', 'weight', 'peso', 'landing_weight', 'grossweight'])
                if weight:
                    # Converter para float
                    weight_val = float(weight)
                    # Se peso está em lbs (> 60000), converter para kg
                    if weight_val > 60000:
                        weight_kg = weight_val * 0.453592
                        logger.info(f"Peso encontrado: {weight_val} lbs = {weight_kg:.0f} kg")
                    else:
                        weight_kg = weight_val
                        logger.info(f"Peso encontrado: {weight_kg:.0f} kg")
                else:
                    # Usar MLW como estimativa
                    weight_kg = specs.mlw_kg
                    logger.warning(f"Peso não encontrado no CSV, usando MLW: {weight_kg} kg")
                
                # Analisar com HardLandingAnalyzer
                logger.info("Iniciando análise com HardLandingAnalyzer...")
                analyzer = HardLandingAnalyzer()
                hl_results = analyzer.analyze(df, weight_kg, model_name)
                logger.info(f"Análise retornou {len(hl_results)} resultado(s)")
                
                # Converter resultados para AnalysisResult
                if not hl_results:
                    logger.warning("HardLandingAnalyzer não retornou resultados")
                    results.append(AnalysisResult(
                        status="NO_DATA",
                        parameter="Hard Landing Analysis",
                        value=None,
                        limit=None,
                        message="Nenhum voo detectado no arquivo. Verifique se o arquivo contém dados de voo válidos.",
                        severity="LOW"
                    ))
                    return results
                
                for hl_result in hl_results:
                    logger.info(f"Processando resultado do voo #{hl_result.vertical_accel.get('flight_num', 1) if isinstance(hl_result.vertical_accel, dict) else 1}")
                    
                    # Vertical Acceleration
                    if hl_result.vertical_accel.get('status') != 'NO_DATA':
                        vert = hl_result.vertical_accel
                        status = "VIOLATION" if vert['status'] in ['HARD_LANDING_LOW', 'HARD_LANDING_HIGH', 'ENGINE_INSPECTION'] else "OK"
                        results.append(AnalysisResult(
                            status=status,
                            parameter="Vertical Acceleration",
                            value=vert.get('max_g'),
                            limit=vert.get('thresholds', {}),
                            message=f"Max G: {vert.get('max_g', 0):.3f}G - Status: {vert['status']}",
                            severity=hl_result.severity
                        ))
                    
                    # Roll Rate
                    if hl_result.roll_rate.get('status') not in ['NO_DATA', 'VALIDATION_FAILED']:
                        roll = hl_result.roll_rate
                        status = "VIOLATION" if roll['status'] in ['HARD_LANDING_LOW', 'HARD_LANDING_HIGH'] else "OK"
                        results.append(AnalysisResult(
                            status=status,
                            parameter="Roll Rate",
                            value=roll.get('max_rate'),
                            limit=roll.get('thresholds', {}),
                            message=f"Max Rate: {roll.get('max_rate', 0):.2f}°/s - Status: {roll['status']}",
                            severity=hl_result.severity
                        ))
                    
                    # Pitch Rate
                    if hl_result.pitch_rate.get('status') != 'NO_DATA':
                        pitch = hl_result.pitch_rate
                        status = "VIOLATION" if pitch['status'] in ['HARD_LANDING_LOW', 'HARD_LANDING_HIGH'] else "OK"
                        results.append(AnalysisResult(
                            status=status,
                            parameter="Pitch Rate",
                            value=pitch.get('min_rate'),
                            limit=pitch.get('thresholds', {}),
                            message=f"Min Rate: {pitch.get('min_rate', 0):.2f}°/s - Status: {pitch['status']}",
                            severity=hl_result.severity
                        ))
                    
                    # Resultado geral
                    results.append(AnalysisResult(
                        status="VIOLATION" if hl_result.status != "NORMAL" else "OK",
                        parameter="Hard Landing Overall",
                        value=hl_result.status,
                        limit=None,
                        message=hl_result.message,
                        severity=hl_result.severity
                    ))
                
                # Se processou mas não encontrou violações, adicionar resultado informativo
                if not results or all(r.status == "OK" for r in results):
                    # Procurar valor máximo de aceleração para informar
                    accel_col = RulesEngine._find_column(df, ['vertical_acceleration', 'normaccel', 'norm_accel'])
                    if accel_col:
                        max_g = df[accel_col].max()
                        results.append(AnalysisResult(
                            status="OK",
                            parameter="Análise Completa",
                            value=f"Max G: {max_g:.3f}",
                            limit=None,
                            message=f"Análise concluída. Aceleração máxima: {max_g:.3f}G. Nenhuma violação detectada nos 3 monitores (Vertical Accel, Roll Rate, Pitch Rate).",
                            severity="LOW"
                        ))
                
                return results
                
            except Exception as e:
                logger.error(f"Erro no HardLandingAnalyzer: {e}", exc_info=True)
                # Fallback para análise básica
        
        # Análise básica (fallback)
        vs = RulesEngine._extract_value(df, ['vertical_speed', 'vs', 'taxa_descida'])
        if vs is not None:
            try:
                vs_val = float(vs)
                limit = rules.get('vertical_speed_limit', -600)
                if vs_val < limit:
                    results.append(AnalysisResult(
                        status="VIOLATION",
                        parameter="Vertical Speed",
                        value=vs_val,
                        limit=limit,
                        message=f"Vertical speed de {vs_val} fpm excede limite de {limit} fpm",
                        severity="HIGH"
                    ))
                else:
                    results.append(AnalysisResult(
                        status="OK",
                        parameter="Vertical Speed",
                        value=vs_val,
                        limit=limit,
                        message="Vertical speed dentro dos limites",
                        severity="LOW"
                    ))
            except ValueError:
                pass
        
        return results
    
    @staticmethod
    def _analyze_gear_overspeed(df: pd.DataFrame, rules: Dict, aircraft_id: str = 'e1', model: str = 'E190') -> List[AnalysisResult]:
        """Analisa overspeed com trem de pouso usando especificações dinâmicas"""
        results = []

        model_id = RulesEngine._normalize_model_id(model, aircraft_id)
        if LG_OVERSPEED_ANALYZER_AVAILABLE:
            analyzer = LGDownOverspeedAnalyzer()
            lg_results = analyzer.analyze(df, weight_kg=0, model=model_id)
            for lg in lg_results:
                if lg.status == "ERROR":
                    results.append(AnalysisResult(
                        status="NO_DATA",
                        parameter="Landing Gear Overspeed",
                        value=None,
                        limit=None,
                        message=lg.message,
                        severity="LOW"
                    ))
                else:
                    results.append(AnalysisResult(
                        status="OK" if lg.status == "NORMAL" else "VIOLATION",
                        parameter="VLE - Landing Gear Extended Speed",
                        value=lg.max_ias,
                        limit=lg.vle_limit,
                        message=lg.message,
                        severity=lg.severity
                    ))
            return results
        
        # Obter especificações do modelo se disponível
        vle_limit = None
        vlo_extend_limit = None
        vlo_retract_limit = None
        
        if SPECS_AVAILABLE:
            try:
                from services.all_families_specs import AllFamiliesSpecifications
                specs = AllFamiliesSpecifications.get_specifications_by_model(model)
                if specs and 'gear_speeds' in specs:
                    gear_speeds = specs['gear_speeds']
                    vle_limit = gear_speeds.get('vle')
                    vlo_extend_limit = gear_speeds.get('vlo_extend')
                    vlo_retract_limit = gear_speeds.get('vlo_retract')
            except Exception as e:
                logger.warning(f"Erro ao obter specs de gear: {e}")
        
        # Fallback para valores das rules
        if not vle_limit:
            vle_limit_value = rules.get('max_speed_gear_down', 250)
            vlo_extend_limit_value = rules.get('max_speed_gear_extension', 250)
            vlo_retract_limit_value = rules.get('max_speed_gear_retraction', 220)
        else:
            vle_limit_value = vle_limit.value if hasattr(vle_limit, 'value') else vle_limit
            vlo_extend_limit_value = vlo_extend_limit.value if hasattr(vlo_extend_limit, 'value') else vlo_extend_limit
            vlo_retract_limit_value = vlo_retract_limit.value if hasattr(vlo_retract_limit, 'value') else vlo_retract_limit
        
        # Procurar colunas de velocidade e posição do trem
        speed = RulesEngine._extract_value(df, ['speed', 'velocidade', 'ias', 'calibrated_airspeed', 'cas'])
        gear_pos = RulesEngine._extract_value(df, ['gear', 'landing_gear', 'gear_position', 'trem_pouso'])
        
        if speed is not None:
            try:
                # Verificar velocidade máxima no dataset
                if isinstance(df[df.columns[0]], pd.Series):
                    # Encontrar coluna de velocidade
                    speed_col = None
                    for col in df.columns:
                        if any(term in col.lower() for term in ['speed', 'velocidade', 'ias', 'cas']):
                            speed_col = col
                            break
                    
                    if speed_col:
                        max_speed = float(df[speed_col].max())
                    else:
                        max_speed = float(speed)
                else:
                    max_speed = float(speed)
                
                # Verificar se trem estava abaixado
                gear_down = False
                if gear_pos is not None:
                    gear_str = str(gear_pos).upper()
                    gear_down = gear_str in ['DOWN', 'ABAIXADO', 'EXTENDED', '1', 'LOCKED']
                else:
                    # Se não temos info de gear, assumir que estava abaixado se velocidade < VMO
                    # (conservador, evita falsos negativos)
                    gear_down = True
                
                # Análise de VLE (gear extended)
                if gear_down:
                    if max_speed > vle_limit_value:
                        results.append(AnalysisResult(
                            status="VIOLATION",
                            parameter="VLE - Landing Gear Extended Speed",
                            value=max_speed,
                            limit=vle_limit_value,
                            message=f"Velocidade de {max_speed} KIAS excede VLE de {vle_limit_value} KIAS com trem abaixado",
                            severity="CRITICAL"
                        ))
                    else:
                        results.append(AnalysisResult(
                            status="OK",
                            parameter="VLE - Landing Gear Extended Speed",
                            value=max_speed,
                            limit=vle_limit_value,
                            message=f"Velocidade dentro do limite VLE ({max_speed} ≤ {vle_limit_value} KIAS)",
                            severity="LOW"
                        ))
                
                # TODO: Detectar momentos de extensão/retração para verificar VLO
                # Por enquanto, apenas reportar os limites
                results.append(AnalysisResult(
                    status="OK",
                    parameter="VLO Limits",
                    value=f"Extension: {vlo_extend_limit_value} KIAS, Retraction: {vlo_retract_limit_value} KIAS",
                    limit=None,
                    message=f"Limites VLO: Extensão {vlo_extend_limit_value} KIAS, Retração {vlo_retract_limit_value} KIAS",
                    severity="LOW"
                ))
                
            except (ValueError, TypeError) as e:
                logger.warning(f"Erro ao analisar gear overspeed: {e}")
        
        return results
    
    @staticmethod
    def _analyze_temperature_envelope(df: pd.DataFrame, rules: Dict, aircraft_id: str = 'e1', model: str = 'E190') -> List[AnalysisResult]:
        """Analisa envelope de temperatura"""
        results = []

        if TEMP_ENVELOPE_ANALYZER_AVAILABLE:
            analyzer = TemperatureEnvelopeAnalyzer()
            model_id = RulesEngine._normalize_model_id(model, aircraft_id)
            temp_results = analyzer.analyze(df, weight_kg=0, model=model_id)
            for temp in temp_results:
                status = "OK" if temp.status == "NORMAL" else "VIOLATION"
                limit = f"{temp.min_limit}°C a {temp.max_limit}°C"
                value = f"max={temp.max_temp:.1f}°C, min={temp.min_temp:.1f}°C"
                results.append(AnalysisResult(
                    status=status,
                    parameter="Temperature Envelope",
                    value=value,
                    limit=limit,
                    message=temp.message,
                    severity=temp.severity
                ))
            return results
        
        temp = RulesEngine._extract_value(df, ['temperature', 'temp', 'temperatura', 'sat'])
        if temp is not None:
            try:
                temp_val = float(temp)
                min_temp = rules.get('min_temperature', -54)
                max_temp = rules.get('max_temperature', 45)
                
                if temp_val < min_temp or temp_val > max_temp:
                    results.append(AnalysisResult(
                        status="VIOLATION",
                        parameter="Temperature",
                        value=temp_val,
                        limit=f"{min_temp}°C a {max_temp}°C",
                        message=f"Temperatura de {temp_val}°C fora do envelope ({min_temp}°C a {max_temp}°C)",
                        severity="HIGH"
                    ))
                else:
                    results.append(AnalysisResult(
                        status="OK",
                        parameter="Temperature",
                        value=temp_val,
                        limit=f"{min_temp}°C a {max_temp}°C",
                        message="Temperatura dentro do envelope",
                        severity="LOW"
                    ))
            except ValueError:
                pass
        
        return results
    
    @staticmethod
    def _analyze_max_speed(df: pd.DataFrame, rules: Dict, aircraft_id: str = 'e1', model: str = 'E190') -> List[AnalysisResult]:
        """Analisa velocidade máxima operacional"""
        results = []

        if VMO_ANALYZER_AVAILABLE:
            analyzer = VmoAnalyzer()
            model_id = RulesEngine._normalize_model_id(model, aircraft_id)
            vmo_results = analyzer.analyze(df, weight_kg=0, model=model_id)
            thresholds = analyzer.get_vmo_thresholds(model_id)
            for vmo in vmo_results:
                if vmo.status == "ERROR":
                    results.append(AnalysisResult(
                        status="NO_DATA",
                        parameter="VMO/MMO",
                        value=None,
                        limit=None,
                        message=vmo.message,
                        severity="LOW"
                    ))
                else:
                    results.append(AnalysisResult(
                        status="OK" if vmo.status == "NORMAL" else "VIOLATION",
                        parameter="VMO/MMO",
                        value=f"IAS={vmo.max_ias:.0f} KIAS, Mach={vmo.max_mach:.3f}",
                        limit=f"VMO={thresholds['vmo']} KIAS, MMO={thresholds['mmo']}",
                        message=vmo.message,
                        severity=vmo.severity
                    ))
            return results
        
        speed = RulesEngine._extract_value(df, ['speed', 'velocidade', 'ias'])
        if speed is not None:
            try:
                speed_val = float(speed)
                vmo = rules.get('vmo', 320)
                if speed_val > vmo:
                    results.append(AnalysisResult(
                        status="VIOLATION",
                        parameter="VMO",
                        value=speed_val,
                        limit=vmo,
                        message=f"Velocidade de {speed_val} KIAS excede VMO de {vmo} KIAS",
                        severity="CRITICAL"
                    ))
                else:
                    results.append(AnalysisResult(
                        status="OK",
                        parameter="VMO",
                        value=speed_val,
                        limit=vmo,
                        message="Velocidade dentro dos limites",
                        severity="LOW"
                    ))
            except ValueError:
                pass
        
        return results
    
    @staticmethod
    def _analyze_flap_overspeed(df: pd.DataFrame, rules: Dict, aircraft_id: str = 'e1', model: str = 'E190') -> List[AnalysisResult]:
        """Analisa overspeed com flaps estendidos"""
        results = []

        if FLAP_ANALYZER_AVAILABLE:
            analyzer = FlapAnalyzer()
            model_id = RulesEngine._normalize_model_id(model, aircraft_id)
            flap_results = analyzer.analyze(df, weight_kg=0, model=model_id)
            for flap in flap_results:
                if flap.status == "ERROR":
                    results.append(AnalysisResult(
                        status="NO_DATA",
                        parameter="Flap Overspeed",
                        value=None,
                        limit=None,
                        message=flap.message,
                        severity="LOW"
                    ))
                else:
                    limit = flap.exceeded_limit if flap.exceeded_limit is not None else "N/A"
                    results.append(AnalysisResult(
                        status="OK" if flap.status == "NORMAL" else "VIOLATION",
                        parameter="Flap Overspeed",
                        value=flap.max_ias,
                        limit=limit,
                        message=flap.message,
                        severity=flap.severity
                    ))
            return results
        
        # Implementação simplificada - expandir conforme PDFs
        speed = RulesEngine._extract_value(df, ['speed', 'velocidade', 'ias'])
        flap_position = RulesEngine._extract_value(df, ['flaps', 'flap_position', 'posicao_flaps'])
        
        if speed is not None and flap_position is not None:
            try:
                speed_val = float(speed)
                # Determinar limite baseado na posição do flap
                # Implementação simplificada
                limit = rules.get('flaps_full', 145)
                if speed_val > limit:
                    results.append(AnalysisResult(
                        status="VIOLATION",
                        parameter="Flap Speed",
                        value=speed_val,
                        limit=limit,
                        message=f"Velocidade de {speed_val} KIAS excede limite de {limit} KIAS com flaps estendidos",
                        severity="HIGH"
                    ))
                else:
                    results.append(AnalysisResult(
                        status="OK",
                        parameter="Flap Speed",
                        value=speed_val,
                        limit=limit,
                        message="Velocidade dentro dos limites para configuração de flaps",
                        severity="LOW"
                    ))
            except ValueError:
                pass
        
        return results
    
    @staticmethod
    def _analyze_overweight_landing(df: pd.DataFrame, rules: Dict, aircraft_id: str = 'e1', model: str = 'E190') -> List[AnalysisResult]:
        """Analisa pouso com peso excessivo usando especificações dinâmicas"""
        results = []

        if OVERWEIGHT_ANALYZER_AVAILABLE:
            analyzer = OverweightLandingAnalyzer()
            model_id = RulesEngine._normalize_model_id(model, aircraft_id)
            weight_kg = RulesEngine._extract_weight_kg(df)
            if weight_kg is None:
                results.append(AnalysisResult(
                    status="NO_DATA",
                    parameter="Landing Weight",
                    value=None,
                    limit=None,
                    message="Peso de pouso não encontrado no CSV",
                    severity="LOW"
                ))
                return results

            ow_results = analyzer.analyze(df, weight_kg=weight_kg, model=model_id)
            for ow in ow_results:
                results.append(AnalysisResult(
                    status="OK" if ow.status == "NORMAL" else "VIOLATION",
                    parameter="Landing Weight",
                    value=ow.gross_weight,
                    limit=ow.mlw_limit,
                    message=ow.message,
                    severity=ow.severity
                ))
            return results
        
        # Obter MLW do modelo
        mlw_limit = None
        if SPECS_AVAILABLE:
            try:
                from services.all_families_specs import AllFamiliesSpecifications
                specs = AllFamiliesSpecifications.get_specifications_by_model(model)
                if specs and 'weights' in specs:
                    # MLW está em lbs nas specs
                    mlw_limit = specs['weights'].mlw
            except Exception as e:
                logger.warning(f"Erro ao obter MLW: {e}")
        
        # Fallback
        if not mlw_limit:
            mlw_limit = rules.get('max_landing_weight', 97000)  # lbs
        
        # Procurar peso no CSV
        weight = RulesEngine._extract_value(df, ['weight', 'peso', 'landing_weight', 'gross_weight', 'gw'])
        
        if weight is not None:
            try:
                weight_val = float(weight)
                
                # Detectar unidade (assumir kg se < 60000, lbs se >= 60000)
                if weight_val < 60000:
                    # Provavelmente em kg, converter para lbs
                    weight_lbs = weight_val * 2.20462
                    unit = "kg"
                else:
                    # Provavelmente em lbs
                    weight_lbs = weight_val
                    unit = "lbs"
                
                # Verificar excedência
                if weight_lbs > mlw_limit:
                    excess = weight_lbs - mlw_limit
                    results.append(AnalysisResult(
                        status="VIOLATION",
                        parameter="Landing Weight",
                        value=f"{weight_val:.0f} {unit} ({weight_lbs:.0f} lbs)",
                        limit=f"{mlw_limit:.0f} lbs",
                        message=f"Peso de pouso de {weight_lbs:.0f} lbs excede MLW de {mlw_limit:.0f} lbs (excesso: {excess:.0f} lbs ou {excess*0.453592:.0f} kg)",
                        severity="CRITICAL"
                    ))
                else:
                    margin = mlw_limit - weight_lbs
                    results.append(AnalysisResult(
                        status="OK",
                        parameter="Landing Weight",
                        value=f"{weight_val:.0f} {unit} ({weight_lbs:.0f} lbs)",
                        limit=f"{mlw_limit:.0f} lbs",
                        message=f"Peso de pouso dentro do limite MLW (margem: {margin:.0f} lbs ou {margin*0.453592:.0f} kg)",
                        severity="LOW"
                    ))
            except (ValueError, TypeError) as e:
                logger.warning(f"Erro ao analisar overweight: {e}")
        else:
            results.append(AnalysisResult(
                status="NO_DATA",
                parameter="Landing Weight",
                value=None,
                limit=f"{mlw_limit:.0f} lbs",
                message="Peso de pouso não encontrado no CSV",
                severity="LOW"
            ))
        
        return results

    @staticmethod
    def _analyze_turbulence(df: pd.DataFrame, rules: Dict, aircraft_id: str = 'e1', model: str = 'E190') -> List[AnalysisResult]:
        """Analisa turbulência usando especificações dinâmicas"""
        results = []

        if TURBULENCE_ANALYZER_AVAILABLE:
            analyzer = TurbulenceAnalyzer()
            model_name = RulesEngine._normalize_model_name(model, aircraft_id)
            turb = analyzer.analyze_turbulence(
                df,
                aircraft_id,
                model_name,
                rules=rules
            )
            status = "VIOLATION" if turb.is_turbulence else "OK"
            limit = f"+{turb.positive_threshold}G / {turb.negative_threshold}G"
            if turb.max_turbulence_speed is not None:
                limit += f", {turb.max_turbulence_speed} KIAS"
            value = f"max+G={turb.max_positive_g:.2f}, max-G={turb.max_negative_g:.2f}"
            results.append(AnalysisResult(
                status=status,
                parameter="Turbulence",
                value=value,
                limit=limit,
                message="; ".join(turb.recommended_actions),
                severity=turb.severity_level
            ))
            return results

        accel_col = RulesEngine._find_column(df, ['vertical_acceleration', 'norm_accel', 'nz', 'g_load'])
        if not accel_col:
            results.append(AnalysisResult(
                status="NO_DATA",
                parameter="Turbulence",
                value=None,
                limit=None,
                message="Coluna de aceleracao vertical nao encontrada",
                severity="LOW"
            ))
            return results

        g_series = pd.to_numeric(df[accel_col], errors='coerce').dropna()
        if g_series.empty:
            results.append(AnalysisResult(
                status="NO_DATA",
                parameter="Turbulence",
                value=None,
                limit=None,
                message="Sem dados validos de aceleracao",
                severity="LOW"
            ))
            return results

        max_positive_g = float(g_series.max())
        max_negative_g = float(g_series.min())
        pos_limit = rules.get('max_positive_g', 2.5)
        neg_limit = rules.get('max_negative_g', -1.0)

        if max_positive_g > pos_limit or max_negative_g < neg_limit:
            results.append(AnalysisResult(
                status="VIOLATION",
                parameter="Turbulence",
                value=f"max+G={max_positive_g:.2f}, max-G={max_negative_g:.2f}",
                limit=f"+{pos_limit}G / {neg_limit}G",
                message="Excedencia de limites de turbulencia",
                severity="HIGH"
            ))
        else:
            results.append(AnalysisResult(
                status="OK",
                parameter="Turbulence",
                value=f"max+G={max_positive_g:.2f}, max-G={max_negative_g:.2f}",
                limit=f"+{pos_limit}G / {neg_limit}G",
                message="Sem excedencia de turbulencia",
                severity="LOW"
            ))

        return results

    @staticmethod
    def _analyze_over_g(df: pd.DataFrame, rules: Dict, aircraft_id: str = 'e1', model: str = 'E190') -> List[AnalysisResult]:
        """Analisa over-G usando especificações dinâmicas"""
        results = []

        if OVER_G_ANALYZER_AVAILABLE:
            analyzer = OverGAnalyzer()
            model_name = RulesEngine._normalize_model_name(model, aircraft_id)
            og = analyzer.analyze_over_g(df, model_name)
            status = "VIOLATION" if og.is_over_g else "OK"
            limit = f"+{og.positive_threshold:.2f}G / {og.negative_threshold:.2f}G"
            value = f"max+G={og.max_positive_g:.2f}, max-G={og.max_negative_g:.2f}"
            results.append(AnalysisResult(
                status=status,
                parameter="Over-G",
                value=value,
                limit=limit,
                message="; ".join(og.recommended_actions),
                severity=og.severity_level
            ))
            return results

        accel_col = RulesEngine._find_column(df, ['vertical_acceleration', 'norm_accel', 'nz', 'g_load'])
        if not accel_col:
            results.append(AnalysisResult(
                status="NO_DATA",
                parameter="Over-G",
                value=None,
                limit=None,
                message="Coluna de aceleracao vertical nao encontrada",
                severity="LOW"
            ))
            return results

        g_series = pd.to_numeric(df[accel_col], errors='coerce').dropna()
        if g_series.empty:
            results.append(AnalysisResult(
                status="NO_DATA",
                parameter="Over-G",
                value=None,
                limit=None,
                message="Sem dados validos de aceleracao",
                severity="LOW"
            ))
            return results

        max_positive_g = float(g_series.max())
        max_negative_g = float(g_series.min())
        pos_limit = rules.get('max_positive_g', 3.5)
        neg_limit = rules.get('max_negative_g', -3.5)

        if max_positive_g > pos_limit or max_negative_g < neg_limit:
            results.append(AnalysisResult(
                status="VIOLATION",
                parameter="Over-G",
                value=f"max+G={max_positive_g:.2f}, max-G={max_negative_g:.2f}",
                limit=f"+{pos_limit}G / {neg_limit}G",
                message="Excedencia de limites de over-G",
                severity="HIGH"
            ))
        else:
            results.append(AnalysisResult(
                status="OK",
                parameter="Over-G",
                value=f"max+G={max_positive_g:.2f}, max-G={max_negative_g:.2f}",
                limit=f"+{pos_limit}G / {neg_limit}G",
                message="Sem excedencia de over-G",
                severity="LOW"
            ))

        return results

    @staticmethod
    def _analyze_high_bank_angle(df: pd.DataFrame, rules: Dict, aircraft_id: str = 'e1', model: str = 'E190') -> List[AnalysisResult]:
        """Analisa high bank angle usando especificações dinâmicas"""
        results = []

        if HIGH_BANK_ANGLE_ANALYZER_AVAILABLE:
            analyzer = HighBankAngleAnalyzer()
            model_name = RulesEngine._normalize_model_name(model, aircraft_id)
            hba = analyzer.analyze_high_bank_angle(df, model_name)
            status = "VIOLATION" if hba.is_high_bank_angle else "OK"
            limit = f"{hba.bank_threshold_normal:.1f}°/{hba.bank_threshold_emergency:.1f}°"
            value = f"max_bank={abs(hba.max_bank_angle):.1f}°"
            results.append(AnalysisResult(
                status=status,
                parameter="High Bank Angle",
                value=value,
                limit=limit,
                message="; ".join(hba.recommended_actions),
                severity=hba.severity_level
            ))
            return results

        roll_col = RulesEngine._find_column(df, ['roll_attitude', 'roll'])
        if not roll_col:
            results.append(AnalysisResult(
                status="NO_DATA",
                parameter="High Bank Angle",
                value=None,
                limit=None,
                message="Coluna de roll/bank nao encontrada",
                severity="LOW"
            ))
            return results

        roll_series = pd.to_numeric(df[roll_col], errors='coerce').dropna()
        if roll_series.empty:
            results.append(AnalysisResult(
                status="NO_DATA",
                parameter="High Bank Angle",
                value=None,
                limit=None,
                message="Sem dados validos de roll",
                severity="LOW"
            ))
            return results

        max_bank = float(max(abs(roll_series.min()), abs(roll_series.max())))
        normal_limit = rules.get('normal', 60.0)
        emergency_limit = rules.get('emergency', 67.0)

        if max_bank > normal_limit:
            results.append(AnalysisResult(
                status="VIOLATION",
                parameter="High Bank Angle",
                value=f"max_bank={max_bank:.1f}°",
                limit=f"{normal_limit:.1f}°/{emergency_limit:.1f}°",
                message="Excedencia de limite de bank angle",
                severity="HIGH"
            ))
        else:
            results.append(AnalysisResult(
                status="OK",
                parameter="High Bank Angle",
                value=f"max_bank={max_bank:.1f}°",
                limit=f"{normal_limit:.1f}°/{emergency_limit:.1f}°",
                message="Sem excedencia de bank angle",
                severity="LOW"
            ))

        return results
    
    @staticmethod
    def _analyze_cg_limits(df: pd.DataFrame, rules: Dict, aircraft_id: str = 'e1', model: str = 'E190') -> List[AnalysisResult]:
        """Analisa limites de Centro de Gravidade usando especificações dinâmicas"""
        results = []
        
        # Obter limites de CG do modelo
        forward_limit = None
        aft_limit = None
        
        if SPECS_AVAILABLE:
            try:
                from services.all_families_specs import AllFamiliesSpecifications
                specs = AllFamiliesSpecifications.get_specifications_by_model(model)
                if specs and 'cg' in specs:
                    cg_limits = specs['cg']
                    forward_limit = cg_limits.forward_limit
                    aft_limit = cg_limits.aft_limit
            except Exception as e:
                logger.warning(f"Erro ao obter limites de CG: {e}")
        
        # Fallback
        if not forward_limit:
            forward_limit = rules.get('forward_limit', 18.0)
            aft_limit = rules.get('aft_limit', 37.0)
        
        # Procurar CG no CSV
        cg = RulesEngine._extract_value(df, ['cg', 'center_gravity', 'cg_mac', 'cg_percent_mac', 'centro_gravidade'])
        
        if cg is not None:
            try:
                cg_val = float(cg)
                
                # Verificar se está fora dos limites
                if cg_val < forward_limit:
                    diff = forward_limit - cg_val
                    results.append(AnalysisResult(
                        status="VIOLATION",
                        parameter="CG Position",
                        value=f"{cg_val:.1f}% MAC",
                        limit=f"{forward_limit:.1f}% - {aft_limit:.1f}% MAC",
                        message=f"CG muito à frente ({cg_val:.1f}% MAC) do limite forward ({forward_limit:.1f}% MAC). Diferença: {diff:.1f}% MAC",
                        severity="HIGH"
                    ))
                elif cg_val > aft_limit:
                    diff = cg_val - aft_limit
                    results.append(AnalysisResult(
                        status="VIOLATION",
                        parameter="CG Position",
                        value=f"{cg_val:.1f}% MAC",
                        limit=f"{forward_limit:.1f}% - {aft_limit:.1f}% MAC",
                        message=f"CG muito atrás ({cg_val:.1f}% MAC) do limite aft ({aft_limit:.1f}% MAC). Diferença: {diff:.1f}% MAC",
                        severity="HIGH"
                    ))
                else:
                    # Calcular margens
                    forward_margin = cg_val - forward_limit
                    aft_margin = aft_limit - cg_val
                    min_margin = min(forward_margin, aft_margin)
                    
                    results.append(AnalysisResult(
                        status="OK",
                        parameter="CG Position",
                        value=f"{cg_val:.1f}% MAC",
                        limit=f"{forward_limit:.1f}% - {aft_limit:.1f}% MAC",
                        message=f"CG dentro dos limites (margem mínima: {min_margin:.1f}% MAC)",
                        severity="LOW"
                    ))
            except (ValueError, TypeError) as e:
                logger.warning(f"Erro ao analisar CG limits: {e}")
        else:
            results.append(AnalysisResult(
                status="NO_DATA",
                parameter="CG Position",
                value=None,
                limit=f"{forward_limit:.1f}% - {aft_limit:.1f}% MAC",
                message="CG não encontrado no CSV",
                severity="LOW"
            ))
        
        return results
    
    @staticmethod
    def _determine_overall_status(results: List[AnalysisResult]) -> str:
        """Determina status geral da análise"""
        if not results:
            return "NO_DATA"
        
        has_violation = any(r.status == "VIOLATION" for r in results)
        has_warning = any(r.status == "WARNING" for r in results)
        
        if has_violation:
            return "VIOLATION"
        elif has_warning:
            return "WARNING"
        else:
            return "OK"
    
    @staticmethod
    def _generate_recommendations(results: List[AnalysisResult], event_type: str) -> List[str]:
        """Gera recomendações baseadas nos resultados"""
        recommendations = []
        
        violations = [r for r in results if r.status == "VIOLATION"]
        
        if violations:
            recommendations.append("⚠️ Foram detectadas violações que requerem inspeção")
            
            for v in violations:
                if v.severity in ["HIGH", "CRITICAL"]:
                    recommendations.append(f"  • {v.parameter}: {v.message}")
            
            # Recomendações específicas por tipo
            if event_type == "hard_landing":
                recommendations.append("📋 Verificar estrutura da aeronave conforme manual de manutenção")
                recommendations.append("📋 Inspecionar trem de pouso e fuselagem")
            elif event_type == "gear_overspeed":
                recommendations.append("📋 Inspecionar trem de pouso e portas")
            elif event_type == "overweight_landing":
                recommendations.append("📋 Inspeção estrutural completa requerida")
            elif event_type == "turbulence":
                recommendations.append("📋 Inspecionar estrutura para eventos de turbulência severa")
                recommendations.append("📋 Verificar limites de velocidade em turbulência")
            elif event_type == "over_g":
                recommendations.append("📋 Inspeção estrutural recomendada após excedência de G")
            elif event_type == "high_bank_angle":
                recommendations.append("📋 Verificar possíveis danos estruturais por high bank angle")
        else:
            recommendations.append("✓ Nenhuma violação detectada")
            recommendations.append("✓ Parâmetros dentro dos limites operacionais")
        
        return recommendations
    
    @staticmethod
    def apply_all_rules(df: pd.DataFrame, aircraft_model: str, touchdown_weight: float) -> Dict:
        """
        Aplica TODAS as regras disponíveis: Hard Landing, Over-G, High Bank Angle
        
        Args:
            df: DataFrame com dados de voo
            aircraft_model: Modelo da aeronave (E170, E175, E190, E195, etc.)
            touchdown_weight: Peso de pouso em kg
        
        Returns:
            Dicionário com todos os resultados
        """
        results = {}
        
        # 1. HARD LANDING ANALYZER
        if HARD_LANDING_ANALYZER_AVAILABLE:
            try:
                analyzer = HardLandingAnalyzer()
                hl_results = analyzer.analyze(df, touchdown_weight, aircraft_model)
                results['hard_landing_details'] = hl_results
                legacy = HardLandingLegacyResult(False, 'NONE', 0.0)
                if hl_results:
                    severity_rank = {
                        'NORMAL': 0,
                        'LOW': 1,
                        'HIGH': 2,
                        'CRITICAL': 3
                    }
                    best = max(hl_results, key=lambda r: severity_rank.get(r.severity, 0))
                    severity_level = 'NONE' if best.severity == 'NORMAL' else best.severity
                    max_g = best.vertical_accel.get('max_g') if isinstance(best.vertical_accel, dict) else None
                    if max_g is None:
                        max_g = 0.0
                    legacy = HardLandingLegacyResult(
                        is_hard_landing=best.severity != 'NORMAL',
                        severity_level=severity_level,
                        max_vertical_accel=float(max_g)
                    )
                results['hard_landing'] = legacy
                if hl_results:
                    logger.info(f"Hard Landing: {hl_results[0].severity}")
                else:
                    logger.info("Hard Landing: sem resultados")
            except Exception as e:
                logger.error(f"Erro em Hard Landing Analyzer: {e}")
                results['hard_landing'] = None
        
        # 2. OVER-G ANALYZER
        if OVER_G_ANALYZER_AVAILABLE:
            try:
                analyzer = OverGAnalyzer()
                og_result = analyzer.analyze_over_g(df, aircraft_model)
                results['over_g'] = og_result
                logger.info(f"Over-G: {og_result.severity_level} (+{og_result.max_positive_g:.2f}G / {og_result.max_negative_g:.2f}G)")
            except Exception as e:
                logger.error(f"Erro em Over-G Analyzer: {e}")
                results['over_g'] = None
        
        # 3. HIGH BANK ANGLE ANALYZER
        if HIGH_BANK_ANGLE_ANALYZER_AVAILABLE:
            try:
                analyzer = HighBankAngleAnalyzer()
                hba_result = analyzer.analyze_high_bank_angle(df, aircraft_model)
                results['high_bank_angle'] = hba_result
                logger.info(f"High Bank Angle: {hba_result.severity_level} ({abs(hba_result.max_bank_angle):.1f}°)")
            except Exception as e:
                logger.error(f"Erro em High Bank Angle Analyzer: {e}")
                results['high_bank_angle'] = None
        
        return results

