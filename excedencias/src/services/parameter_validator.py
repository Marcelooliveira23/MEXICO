"""
Parameter Validator - Validação Específica por Modelo de Aeronave
Versão 1.0 - Sistema de Validação Inteligente
"""
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from .all_families_specs import AllFamiliesSpecifications
from utils.logger import logger


@dataclass
class ValidationResult:
    """Resultado de validação de um parâmetro"""
    parameter: str
    value: float
    limit: float
    unit: str
    status: str  # "OK", "WARNING", "CRITICAL"
    exceedance_percent: float
    message: str
    manual_reference: str


@dataclass
class ModelValidationReport:
    """Relatório completo de validação para um modelo"""
    aircraft_model: str
    event_type: str
    total_parameters_checked: int
    parameters_ok: int
    parameters_warning: int
    parameters_critical: int
    validation_results: List[ValidationResult]
    overall_status: str
    recommendations: List[str]


class ParameterValidator:
    """
    Validador de parâmetros específico por modelo de aeronave
    
    Valida se os dados estão dentro dos limites técnicos
    de cada modelo específico (E170, E175, E190, E195, E145, E2, etc.)
    """
    
    def __init__(self):
        """Inicializar validador"""
        self.specs = AllFamiliesSpecifications()
        logger.info("Parameter Validator initialized")
        
        # Mapeamento de modelos para especificações
        # Nota: use modelo específico (E170, E175, etc) não família (e1)
        self.model_mapping = {
            "e170": "E170",
            "e175": "E175",
            "e190": "E190",
            "e195": "E195",
            "e135": "E135",
            "e140": "E140",
            "e145": "E145",
            "e190-e2": "E190_E2",
            "e195-e2": "E195_E2",
        }
        
        # Mapeamento de família para modelo default
        self.family_defaults = {
            "e145": "E145",
            "e170": "E170",  # E170/E175
            "e1": "E190",    # E190/E195
            "e2": "E190_E2"
        }
    
    def validate_hard_landing(
        self, df: pd.DataFrame, aircraft_model: str
    ) -> ModelValidationReport:
        """
        Validar parâmetros de Hard Landing
        
        Args:
            df: DataFrame com dados de voo
            aircraft_model: Modelo da aeronave (e.g., "e170", "e175")
            
        Returns:
            ModelValidationReport com resultados detalhados
        """
        model_key = self.model_mapping.get(aircraft_model.lower(), "E190")
        results = []
        
        # Obter especificações do modelo
        hard_landing_spec = getattr(
            self.specs, f"{model_key}_HARD_LANDING", None
        )
        
        if not hard_landing_spec:
            logger.warning(f"Specifications not found for {model_key}")
            return self._empty_report(aircraft_model, "hard_landing")
        
        # Validar aceleração vertical
        accel_col = self._find_column(
            df, ["vertical_acceleration", "vert_accel", "nz", "g_force"]
        )
        
        if accel_col:
            max_accel = df[accel_col].max()
            
            # Verificar contra limites
            normal_limit = hard_landing_spec["normal_limit"].value
            hard_limit = hard_landing_spec["hard_limit"].value
            very_hard_limit = hard_landing_spec["very_hard_limit"].value
            
            if max_accel > very_hard_limit:
                status = "CRITICAL"
                exceedance = ((max_accel - very_hard_limit) / very_hard_limit) * 100
                message = (
                    f"VERY HARD LANDING detectado! "
                    f"Aceleração {max_accel:.2f}G excede limite "
                    f"crítico de {very_hard_limit}G em {exceedance:.1f}%"
                )
            elif max_accel > hard_limit:
                status = "CRITICAL"
                exceedance = ((max_accel - hard_limit) / hard_limit) * 100
                message = (
                    f"HARD LANDING detectado! "
                    f"Aceleração {max_accel:.2f}G excede limite "
                    f"de {hard_limit}G em {exceedance:.1f}%"
                )
            elif max_accel > normal_limit:
                status = "WARNING"
                exceedance = ((max_accel - normal_limit) / normal_limit) * 100
                message = (
                    f"Aceleração {max_accel:.2f}G próxima do limite "
                    f"normal de {normal_limit}G (+{exceedance:.1f}%)"
                )
            else:
                status = "OK"
                exceedance = 0
                message = (
                    f"Aceleração {max_accel:.2f}G dentro do limite "
                    f"normal de {normal_limit}G"
                )
            
            results.append(ValidationResult(
                parameter="Vertical Acceleration",
                value=max_accel,
                limit=very_hard_limit if max_accel > hard_limit else hard_limit,
                unit="G",
                status=status,
                exceedance_percent=exceedance,
                message=message,
                manual_reference=hard_landing_spec["very_hard_limit"].manual_reference
            ))
        
        # Validar descent rate
        descent_col = self._find_column(
            df, ["descent_rate", "vertical_speed", "vs", "roc"]
        )
        
        if descent_col:
            # Pegar valores negativos (descent)
            descent_values = df[descent_col][df[descent_col] < 0].abs()
            
            if len(descent_values) > 0:
                max_descent = descent_values.max()
                
                normal_descent = hard_landing_spec["descent_normal"].value
                hard_descent = hard_landing_spec["descent_hard"].value
                very_hard_descent = hard_landing_spec.get(
                    "descent_very_hard", hard_landing_spec["descent_hard"]
                ).value
                
                if max_descent > very_hard_descent:
                    status = "CRITICAL"
                    exceedance = ((max_descent - very_hard_descent) / very_hard_descent) * 100
                    message = (
                        f"Descent rate CRÍTICO: {max_descent:.0f} ft/min "
                        f"excede {very_hard_descent:.0f} ft/min em {exceedance:.1f}%"
                    )
                elif max_descent > hard_descent:
                    status = "WARNING"
                    exceedance = ((max_descent - hard_descent) / hard_descent) * 100
                    message = (
                        f"Descent rate elevado: {max_descent:.0f} ft/min "
                        f"excede {hard_descent:.0f} ft/min em {exceedance:.1f}%"
                    )
                else:
                    status = "OK"
                    exceedance = 0
                    message = (
                        f"Descent rate {max_descent:.0f} ft/min "
                        f"dentro do normal ({normal_descent:.0f} ft/min)"
                    )
                
                results.append(ValidationResult(
                    parameter="Descent Rate",
                    value=max_descent,
                    limit=very_hard_descent if max_descent > hard_descent else hard_descent,
                    unit="ft/min",
                    status=status,
                    exceedance_percent=exceedance,
                    message=message,
                    manual_reference=hard_landing_spec["descent_hard"].manual_reference
                ))
        
        return self._build_report(aircraft_model, "hard_landing", results)
    
    def validate_gear_overspeed(
        self, df: pd.DataFrame, aircraft_model: str
    ) -> ModelValidationReport:
        """Validar velocidades do trem de pouso"""
        model_key = self.model_mapping.get(aircraft_model.lower(), "E190")
        results = []
        
        # Obter especificações
        gear_speeds = getattr(self.specs, f"{model_key}_GEAR_SPEEDS", None)
        
        if not gear_speeds:
            return self._empty_report(aircraft_model, "gear_overspeed")
        
        # Validar VLE
        airspeed_col = self._find_column(
            df, ["airspeed", "ias", "kias", "speed"]
        )
        gear_col = self._find_column(
            df, ["gear_position", "landing_gear", "gear_pos"]
        )
        
        if airspeed_col and gear_col:
            # Filtrar dados com trem estendido
            gear_extended = df[df[gear_col] > 0]
            
            if len(gear_extended) > 0:
                max_speed_gear_down = gear_extended[airspeed_col].max()
                vle = gear_speeds["vle"].value
                inspection_threshold = gear_speeds.get(
                    "inspection_threshold", gear_speeds["vle"]
                ).value
                
                if max_speed_gear_down > inspection_threshold:
                    status = "CRITICAL"
                    exceedance = ((max_speed_gear_down - vle) / vle) * 100
                    message = (
                        f"GEAR OVERSPEED CRÍTICO: {max_speed_gear_down:.0f} KIAS "
                        f"excede VLE de {vle:.0f} KIAS em {exceedance:.1f}%"
                    )
                elif max_speed_gear_down > vle:
                    status = "WARNING"
                    exceedance = ((max_speed_gear_down - vle) / vle) * 100
                    message = (
                        f"Gear overspeed detectado: {max_speed_gear_down:.0f} KIAS "
                        f"excede VLE de {vle:.0f} KIAS em {exceedance:.1f}%"
                    )
                else:
                    status = "OK"
                    exceedance = 0
                    message = (
                        f"Velocidade {max_speed_gear_down:.0f} KIAS "
                        f"dentro do VLE de {vle:.0f} KIAS"
                    )
                
                results.append(ValidationResult(
                    parameter="Landing Gear Speed (VLE)",
                    value=max_speed_gear_down,
                    limit=vle,
                    unit="KIAS",
                    status=status,
                    exceedance_percent=exceedance,
                    message=message,
                    manual_reference=gear_speeds["vle"].manual_reference
                ))
        
        return self._build_report(aircraft_model, "gear_overspeed", results)
    
    def validate_temperature_envelope(
        self, df: pd.DataFrame, aircraft_model: str
    ) -> ModelValidationReport:
        """Validar envelope de temperatura"""
        model_key = self.model_mapping.get(aircraft_model.lower(), "E190")
        results = []
        
        # Obter especificações
        temps = getattr(self.specs, f"{model_key}_TEMPERATURES", None)
        
        if not temps:
            return self._empty_report(aircraft_model, "temp_envelope")
        
        # Validar EGT
        egt_col = self._find_column(df, ["egt", "exhaust_gas_temp", "turbine_temp"])
        
        if egt_col:
            max_egt = df[egt_col].max()
            egt_limit = temps["egt_takeoff"].value
            
            if max_egt > egt_limit:
                status = "CRITICAL"
                exceedance = ((max_egt - egt_limit) / egt_limit) * 100
                message = (
                    f"EGT EXCEDÊNCIA: {max_egt:.0f}°C excede "
                    f"limite de {egt_limit:.0f}°C em {exceedance:.1f}%"
                )
            else:
                status = "OK"
                exceedance = 0
                message = f"EGT {max_egt:.0f}°C dentro do limite de {egt_limit:.0f}°C"
            
            results.append(ValidationResult(
                parameter="Exhaust Gas Temperature (EGT)",
                value=max_egt,
                limit=egt_limit,
                unit="°C",
                status=status,
                exceedance_percent=exceedance,
                message=message,
                manual_reference=temps["egt_takeoff"].manual_reference
            ))
        
        # Validar TAT
        tat_col = self._find_column(df, ["tat", "total_air_temp", "oat", "sat"])
        
        if tat_col:
            max_tat = df[tat_col].max()
            min_tat = df[tat_col].min()
            tat_max_limit = temps["tat_max"].value
            tat_min_limit = temps["tat_min"].value
            
            if max_tat > tat_max_limit:
                status = "WARNING"
                exceedance = ((max_tat - tat_max_limit) / tat_max_limit) * 100
                message = (
                    f"TAT elevada: {max_tat:.0f}°C excede "
                    f"máximo de {tat_max_limit:.0f}°C em {exceedance:.1f}%"
                )
                results.append(ValidationResult(
                    parameter="Total Air Temperature (TAT) - High",
                    value=max_tat,
                    limit=tat_max_limit,
                    unit="°C",
                    status=status,
                    exceedance_percent=exceedance,
                    message=message,
                    manual_reference=temps["tat_max"].manual_reference
                ))
            
            if min_tat < tat_min_limit:
                status = "WARNING"
                exceedance = ((tat_min_limit - min_tat) / abs(tat_min_limit)) * 100
                message = (
                    f"TAT baixa: {min_tat:.0f}°C abaixo do "
                    f"mínimo de {tat_min_limit:.0f}°C em {exceedance:.1f}%"
                )
                results.append(ValidationResult(
                    parameter="Total Air Temperature (TAT) - Low",
                    value=min_tat,
                    limit=tat_min_limit,
                    unit="°C",
                    status=status,
                    exceedance_percent=exceedance,
                    message=message,
                    manual_reference=temps["tat_min"].manual_reference
                ))
        
        return self._build_report(aircraft_model, "temp_envelope", results)
    
    def validate_max_speed(
        self, df: pd.DataFrame, aircraft_model: str
    ) -> ModelValidationReport:
        """Validar velocidades máximas"""
        model_key = self.model_mapping.get(aircraft_model.lower(), "E190")
        results = []
        
        speeds = getattr(self.specs, f"{model_key}_MAX_SPEEDS", None)
        
        if not speeds:
            return self._empty_report(aircraft_model, "max_speed")
        
        # Validar VMO
        airspeed_col = self._find_column(df, ["airspeed", "ias", "kias"])
        
        if airspeed_col:
            max_speed = df[airspeed_col].max()
            vmo = speeds["vmo"].value
            inspection_threshold = speeds.get(
                "inspection_threshold", speeds["vmo"]
            ).value
            
            if max_speed > inspection_threshold:
                status = "CRITICAL"
                exceedance = ((max_speed - vmo) / vmo) * 100
                message = (
                    f"VMO EXCEDÊNCIA CRÍTICA: {max_speed:.0f} KIAS "
                    f"excede VMO de {vmo:.0f} KIAS em {exceedance:.1f}%"
                )
            elif max_speed > vmo:
                status = "WARNING"
                exceedance = ((max_speed - vmo) / vmo) * 100
                message = (
                    f"VMO excedido: {max_speed:.0f} KIAS "
                    f"acima de {vmo:.0f} KIAS em {exceedance:.1f}%"
                )
            else:
                status = "OK"
                exceedance = 0
                message = f"Velocidade {max_speed:.0f} KIAS dentro do VMO de {vmo:.0f} KIAS"
            
            results.append(ValidationResult(
                parameter="Maximum Operating Speed (VMO)",
                value=max_speed,
                limit=vmo,
                unit="KIAS",
                status=status,
                exceedance_percent=exceedance,
                message=message,
                manual_reference=speeds["vmo"].manual_reference
            ))
        
        # Validar MMO
        mach_col = self._find_column(df, ["mach", "mmo"])
        
        if mach_col:
            max_mach = df[mach_col].max()
            mmo = speeds["mmo"].value
            
            if max_mach > mmo:
                status = "CRITICAL"
                exceedance = ((max_mach - mmo) / mmo) * 100
                message = (
                    f"MMO EXCEDIDO: Mach {max_mach:.3f} "
                    f"excede MMO de {mmo:.3f} em {exceedance:.1f}%"
                )
            else:
                status = "OK"
                exceedance = 0
                message = f"Mach {max_mach:.3f} dentro do MMO de {mmo:.3f}"
            
            results.append(ValidationResult(
                parameter="Maximum Operating Mach (MMO)",
                value=max_mach,
                limit=mmo,
                unit="Mach",
                status=status,
                exceedance_percent=exceedance,
                message=message,
                manual_reference=speeds["mmo"].manual_reference
            ))
        
        return self._build_report(aircraft_model, "max_speed", results)

    def validate_flap_overspeed(
        self, df: pd.DataFrame, aircraft_model: str
    ) -> ModelValidationReport:
        """Validar overspeed com flaps/slats estendidos"""
        model_key = self.model_mapping.get(aircraft_model.lower(), "E190")
        results = []

        flap_speeds = getattr(self.specs, f"{model_key}_FLAP_SPEEDS", None)
        if not flap_speeds:
            return self._empty_report(aircraft_model, "flap_overspeed")

        airspeed_col = self._find_column(df, ["airspeed", "ias", "kias"])
        flap_col = self._find_column(df, ["flap_position", "flap", "flaps"])
        if not airspeed_col or not flap_col:
            return self._empty_report(aircraft_model, "flap_overspeed")

        flap_map = {
            "flap_1": ["1", "flap_1", "flap1"],
            "flap_2": ["2", "flap_2", "flap2"],
            "flap_3": ["3", "flap_3", "flap3"],
            "flap_4": ["4", "flap_4", "flap4"],
            "flap_full": ["full", "flap_full", "flapfull", "full_flap"],
            "flap_9": ["9", "flap_9", "flap9"],
            "flap_18": ["18", "flap_18", "flap18"],
            "flap_22": ["22", "flap_22", "flap22"],
            "flap_45": ["45", "flap_45", "flap45"],
        }

        for flap_key, keys in flap_map.items():
            if flap_key not in flap_speeds:
                continue

            limit = flap_speeds[flap_key].value
            mask = df[flap_col].astype(str).str.lower().str.contains("|".join(keys), na=False)
            if not mask.any():
                continue

            max_speed = df.loc[mask, airspeed_col].max()
            if max_speed > limit:
                status = "CRITICAL"
                exceedance = ((max_speed - limit) / limit) * 100
                message = (
                    f"Flap overspeed: {max_speed:.0f} KIAS excede {limit:.0f} KIAS"
                )
            else:
                status = "OK"
                exceedance = 0
                message = (
                    f"Flap {flap_key.upper()}: {max_speed:.0f} KIAS dentro do limite {limit:.0f} KIAS"
                )

            results.append(ValidationResult(
                parameter=f"Flap Speed ({flap_key.upper()})",
                value=max_speed,
                limit=limit,
                unit="KIAS",
                status=status,
                exceedance_percent=exceedance,
                message=message,
                manual_reference=flap_speeds[flap_key].manual_reference
            ))

        return self._build_report(aircraft_model, "flap_overspeed", results)

    def validate_overweight_landing(
        self, df: pd.DataFrame, aircraft_model: str
    ) -> ModelValidationReport:
        """Validar pouso acima do MLW"""
        model_key = self.model_mapping.get(aircraft_model.lower(), "E190")
        results = []

        weights = getattr(self.specs, f"{model_key}_WEIGHTS", None)
        if not weights:
            return self._empty_report(aircraft_model, "overweight_landing")

        weight_col = self._find_column(df, ["gross_weight", "weight", "landing_weight", "gw"])
        if not weight_col:
            return self._empty_report(aircraft_model, "overweight_landing")

        weight_raw = df[weight_col].max()
        weight_lbs = float(weight_raw)
        if weight_lbs < 60000:
            weight_lbs = weight_lbs * 2.20462

        mlw = weights.mlw
        if weight_lbs > mlw:
            status = "CRITICAL"
            exceedance = ((weight_lbs - mlw) / mlw) * 100
            message = (
                f"Overweight landing: {weight_lbs:.0f} lbs excede MLW {mlw:.0f} lbs"
            )
        else:
            status = "OK"
            exceedance = 0
            message = f"Peso {weight_lbs:.0f} lbs dentro do MLW {mlw:.0f} lbs"

        results.append(ValidationResult(
            parameter="Landing Weight (MLW)",
            value=weight_lbs,
            limit=mlw,
            unit="lbs",
            status=status,
            exceedance_percent=exceedance,
            message=message,
            manual_reference="AFM Limitations"
        ))

        return self._build_report(aircraft_model, "overweight_landing", results)
    
    def _find_column(self, df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        """Encontrar coluna no DataFrame (case-insensitive)"""
        df_cols_lower = {col.lower(): col for col in df.columns}
        for candidate in candidates:
            if candidate.lower() in df_cols_lower:
                return df_cols_lower[candidate.lower()]
        return None
    
    def _build_report(
        self, aircraft_model: str, event_type: str, results: List[ValidationResult]
    ) -> ModelValidationReport:
        """Construir relatório de validação"""
        params_ok = sum(1 for r in results if r.status == "OK")
        params_warning = sum(1 for r in results if r.status == "WARNING")
        params_critical = sum(1 for r in results if r.status == "CRITICAL")
        
        if params_critical > 0:
            overall_status = "CRITICAL"
        elif params_warning > 0:
            overall_status = "WARNING"
        else:
            overall_status = "OK"
        
        # Gerar recomendações
        recommendations = []
        if params_critical > 0:
            recommendations.append(
                f"⚠️ {params_critical} parâmetro(s) CRÍTICO(S) detectado(s). "
                "Inspeção imediata obrigatória."
            )
        if params_warning > 0:
            recommendations.append(
                f"⚡ {params_warning} parâmetro(s) em WARNING. "
                "Agende inspeção detalhada."
            )
        
        return ModelValidationReport(
            aircraft_model=aircraft_model.upper(),
            event_type=event_type,
            total_parameters_checked=len(results),
            parameters_ok=params_ok,
            parameters_warning=params_warning,
            parameters_critical=params_critical,
            validation_results=results,
            overall_status=overall_status,
            recommendations=recommendations
        )
    
    def _empty_report(
        self, aircraft_model: str, event_type: str
    ) -> ModelValidationReport:
        """Criar relatório vazio"""
        return ModelValidationReport(
            aircraft_model=aircraft_model.upper(),
            event_type=event_type,
            total_parameters_checked=0,
            parameters_ok=0,
            parameters_warning=0,
            parameters_critical=0,
            validation_results=[],
            overall_status="UNKNOWN",
            recommendations=["Dados insuficientes para validação"]
        )
