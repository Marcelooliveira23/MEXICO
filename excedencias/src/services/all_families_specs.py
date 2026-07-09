"""
Especificações Técnicas Completas - Todas as Famílias Mexicana
Baseado em manuais AMM, AFM e FCOM oficiais
Versão 2.0 - 31 de Janeiro de 2026
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional


@dataclass
class TechnicalLimit:
    """Limite técnico com valor e unidade"""
    value: float
    unit: str
    description: str
    manual_reference: str


@dataclass
class WeightLimits:
    """Limites de peso para um modelo específico"""
    mtow: float  # Maximum Takeoff Weight (lbs)
    mlw: float   # Maximum Landing Weight (lbs)
    mzfw: float  # Maximum Zero Fuel Weight (lbs)
    oew: float   # Operating Empty Weight (lbs)


@dataclass
class CGLimits:
    """Limites de Centro de Gravidade"""
    forward_limit: float  # % MAC
    aft_limit: float      # % MAC
    normal_range: Tuple[float, float]  # (min, max) % MAC


class AllFamiliesSpecifications:
    """Especificações técnicas para todas as famílias Mexicana"""
    
    # ==================== FAMÍLIA E1 ====================
    
    # E170 SPECIFICATIONS (MODO AGRESSIVO)
    E170_HARD_LANDING = {
        "normal_limit": TechnicalLimit(1.7, "G", "Normal landing limit - AGRESSIVO", "AMM 05-51-00"),
        "hard_limit": TechnicalLimit(2.1, "G", "Hard landing inspection required - AGRESSIVO", "AMM 05-51-00"),
        "very_hard_limit": TechnicalLimit(2.4, "G", "Very hard landing - extensive inspection - AGRESSIVO", "AMM 05-51-00"),
        "descent_normal": TechnicalLimit(500, "ft/min", "Normal descent rate - AGRESSIVO", "AMM 05-51-00"),
        "descent_hard": TechnicalLimit(800, "ft/min", "Hard landing descent rate - AGRESSIVO", "AMM 05-51-00"),
        "descent_very_hard": TechnicalLimit(900, "ft/min", "Very hard landing descent rate - AGRESSIVO", "AMM 05-51-00"),
    }
    
    E170_WEIGHTS = WeightLimits(
        mtow=79344,  # 36,000 kg
        mlw=69224,   # 31,400 kg
        mzfw=64157,  # 29,100 kg
        oew=47399    # 21,500 kg
    )
    
    E170_CG = CGLimits(
        forward_limit=16.0,
        aft_limit=35.0,
        normal_range=(20.0, 32.0)
    )
    
    E170_GEAR_SPEEDS = {
        "vle": TechnicalLimit(250, "KIAS", "Maximum speed with gear extended", "AFM Section 5"),
        "vlo_extend": TechnicalLimit(250, "KIAS", "Maximum speed for gear extension", "AFM Section 5"),
        "vlo_retract": TechnicalLimit(220, "KIAS", "Maximum speed for gear retraction", "AFM Section 5"),
        "inspection_threshold": TechnicalLimit(260, "KIAS", "VLE + 10 KIAS", "Maintenance Manual"),
    }
    
    E170_TEMPERATURES = {
        "egt_takeoff": TechnicalLimit(950, "°C", "EGT takeoff limit (5 min)", "AMM 71-00-00"),
        "egt_continuous": TechnicalLimit(915, "°C", "EGT continuous limit", "AMM 71-00-00"),
        "egt_start": TechnicalLimit(725, "°C", "EGT start limit (2 sec)", "AMM 71-00-00"),
        "tat_max": TechnicalLimit(54, "°C", "TAT maximum (ISA+35)", "AMM 71-00-00"),
        "tat_min": TechnicalLimit(-54, "°C", "TAT minimum", "AMM 71-00-00"),
        "tat_continuous": TechnicalLimit(45, "°C", "TAT continuous operation", "AMM 71-00-00"),
    }
    
    E170_MAX_SPEEDS = {
        "vmo": TechnicalLimit(320, "KIAS", "Maximum operating speed", "AFM Section 5"),
        "mmo": TechnicalLimit(0.82, "Mach", "Maximum operating Mach", "AFM Section 5"),
        "inspection_threshold": TechnicalLimit(330, "KIAS", "VMO + 10 KIAS", "Maintenance Manual"),
    }
    
    E170_FLAP_SPEEDS = {
        "flap_1": TechnicalLimit(250, "KIAS", "Flap 1 maximum speed", "AFM Limitations"),
        "flap_2": TechnicalLimit(230, "KIAS", "Flap 2 maximum speed", "AFM Limitations"),
        "flap_3": TechnicalLimit(210, "KIAS", "Flap 3 maximum speed", "AFM Limitations"),
        "flap_4": TechnicalLimit(200, "KIAS", "Flap 4 maximum speed", "AFM Limitations"),
        "flap_full": TechnicalLimit(180, "KIAS", "Flap FULL maximum speed", "AFM Limitations"),
    }
    
    # E175 SPECIFICATIONS (MODO AGRESSIVO)
    E175_HARD_LANDING = {
        "normal_limit": TechnicalLimit(1.8, "G", "Normal landing limit - AGRESSIVO", "AMM 05-51-00"),
        "hard_limit": TechnicalLimit(2.2, "G", "Hard landing inspection required - AGRESSIVO", "AMM 05-51-00"),
        "very_hard_limit": TechnicalLimit(2.5, "G", "Very hard landing - extensive inspection - AGRESSIVO", "AMM 05-51-00"),
        "descent_normal": TechnicalLimit(500, "ft/min", "Normal descent rate - AGRESSIVO", "AMM 05-51-00"),
        "descent_hard": TechnicalLimit(900, "ft/min", "Hard landing descent rate", "AMM 05-51-00"),
        "descent_very_hard": TechnicalLimit(1000, "ft/min", "Very hard landing descent rate", "AMM 05-51-00"),
    }
    
    E175_WEIGHTS = WeightLimits(
        mtow=85517,  # 38,800 kg
        mlw=75000,   # 34,019 kg
        mzfw=68342,  # 31,000 kg
        oew=49604    # 22,500 kg
    )
    
    E175_CG = CGLimits(
        forward_limit=16.0,
        aft_limit=35.0,
        normal_range=(20.0, 32.0)
    )
    
    # E175 usa mesmas velocidades que E170
    E175_GEAR_SPEEDS = E170_GEAR_SPEEDS
    E175_TEMPERATURES = E170_TEMPERATURES
    E175_MAX_SPEEDS = E170_MAX_SPEEDS
    E175_FLAP_SPEEDS = E170_FLAP_SPEEDS
    
    # E190 SPECIFICATIONS
    E190_HARD_LANDING = {
        "normal_limit": TechnicalLimit(2.0, "G", "Normal landing limit", "AMM 05-51-00"),
        "hard_limit": TechnicalLimit(2.6, "G", "Hard landing inspection required", "AMM 05-51-00"),
        "very_hard_limit": TechnicalLimit(2.8, "G", "Very hard landing - extensive inspection", "AMM 05-51-00"),
        "descent_normal": TechnicalLimit(600, "ft/min", "Normal descent rate", "AMM 05-51-00"),
        "descent_hard": TechnicalLimit(900, "ft/min", "Hard landing descent rate", "AMM 05-51-00"),
        "descent_very_hard": TechnicalLimit(1000, "ft/min", "Very hard landing descent rate", "AMM 05-51-00"),
    }
    
    E190_WEIGHTS = WeightLimits(
        mtow=105359,  # 47,790 kg
        mlw=97000,    # 44,000 kg
        mzfw=90389,   # 41,000 kg
        oew=62169     # 28,200 kg
    )
    
    E190_CG = CGLimits(
        forward_limit=18.0,
        aft_limit=37.0,
        normal_range=(22.0, 34.0)
    )
    
    # E190 usa mesmas velocidades que E170/E175
    E190_GEAR_SPEEDS = E170_GEAR_SPEEDS
    E190_TEMPERATURES = E170_TEMPERATURES
    E190_MAX_SPEEDS = E170_MAX_SPEEDS
    E190_FLAP_SPEEDS = E170_FLAP_SPEEDS
    
    # E195 SPECIFICATIONS
    E195_HARD_LANDING = E190_HARD_LANDING  # Mesmos limites que E190
    
    E195_WEIGHTS = WeightLimits(
        mtow=107413,  # 48,721 kg
        mlw=100309,   # 45,500 kg
        mzfw=94139,   # 42,700 kg
        oew=63272     # 28,700 kg
    )
    
    E195_CG = E190_CG  # Mesmos limites de CG que E190
    E195_GEAR_SPEEDS = E170_GEAR_SPEEDS
    E195_TEMPERATURES = E170_TEMPERATURES
    E195_MAX_SPEEDS = E170_MAX_SPEEDS
    E195_FLAP_SPEEDS = E170_FLAP_SPEEDS
    
    # ==================== FAMÍLIA E145 ====================
    
    # E135 SPECIFICATIONS
    E135_HARD_LANDING = {
        "normal_limit": TechnicalLimit(1.6, "G", "Normal landing limit", "AMM 05-51-00"),
        "hard_limit": TechnicalLimit(2.2, "G", "Hard landing inspection required", "AMM 05-51-00"),
        "very_hard_limit": TechnicalLimit(2.4, "G", "Very hard landing - extensive inspection", "AMM 05-51-00"),
        "descent_normal": TechnicalLimit(600, "ft/min", "Normal descent rate", "AMM 05-51-00"),
        "descent_hard": TechnicalLimit(900, "ft/min", "Hard landing descent rate", "AMM 05-51-00"),
        "descent_very_hard": TechnicalLimit(1000, "ft/min", "Very hard landing descent rate", "AMM 05-51-00"),
    }
    
    E135_WEIGHTS = WeightLimits(
        mtow=42989,  # 19,500 kg
        mlw=40565,   # 18,400 kg
        mzfw=37260,  # 16,900 kg
        oew=24030    # 10,900 kg
    )
    
    E135_CG = CGLimits(
        forward_limit=16.0,
        aft_limit=34.0,
        normal_range=(20.0, 30.0)
    )
    
    E135_GEAR_SPEEDS = {
        "vle": TechnicalLimit(230, "KIAS", "Maximum speed with gear extended", "AFM Section 5"),
        "vlo_extend": TechnicalLimit(230, "KIAS", "Maximum speed for gear extension", "AFM Section 5"),
        "vlo_retract": TechnicalLimit(200, "KIAS", "Maximum speed for gear retraction", "AFM Section 5"),
        "inspection_threshold": TechnicalLimit(240, "KIAS", "VLE + 10 KIAS", "Maintenance Manual"),
    }
    
    E135_TEMPERATURES = {
        "egt_takeoff": TechnicalLimit(925, "°C", "EGT takeoff limit (5 min) - AE 3007A", "AMM 71-00-00"),
        "egt_continuous": TechnicalLimit(900, "°C", "EGT continuous limit", "AMM 71-00-00"),
        "egt_start": TechnicalLimit(700, "°C", "EGT start limit (2 sec)", "AMM 71-00-00"),
        "tat_max": TechnicalLimit(50, "°C", "TAT maximum (ISA+30)", "AMM 71-00-00"),
        "tat_min": TechnicalLimit(-54, "°C", "TAT minimum", "AMM 71-00-00"),
        "tat_continuous": TechnicalLimit(42, "°C", "TAT continuous operation", "AMM 71-00-00"),
    }
    
    E135_MAX_SPEEDS = {
        "vmo": TechnicalLimit(280, "KIAS", "Maximum operating speed", "AFM Section 5"),
        "mmo": TechnicalLimit(0.78, "Mach", "Maximum operating Mach", "AFM Section 5"),
        "inspection_threshold": TechnicalLimit(290, "KIAS", "VMO + 10 KIAS", "Maintenance Manual"),
    }
    
    E135_FLAP_SPEEDS = {
        "flap_9": TechnicalLimit(200, "KIAS", "Flap 9° maximum speed", "AFM Limitations"),
        "flap_18": TechnicalLimit(180, "KIAS", "Flap 18° maximum speed", "AFM Limitations"),
        "flap_22": TechnicalLimit(170, "KIAS", "Flap 22° maximum speed", "AFM Limitations"),
        "flap_45": TechnicalLimit(145, "KIAS", "Flap 45° maximum speed", "AFM Limitations"),
    }
    
    # E140 SPECIFICATIONS
    E140_HARD_LANDING = E135_HARD_LANDING  # Mesmos limites que E135
    
    E140_WEIGHTS = WeightLimits(
        mtow=44753,  # 20,300 kg
        mlw=42329,   # 19,200 kg
        mzfw=38802,  # 17,600 kg
        oew=24912    # 11,300 kg
    )
    
    E140_CG = E135_CG
    E140_GEAR_SPEEDS = E135_GEAR_SPEEDS
    
    E140_TEMPERATURES = {
        "egt_takeoff": TechnicalLimit(925, "°C", "EGT takeoff limit (5 min) - AE 3007A1", "AMM 71-00-00"),
        "egt_continuous": TechnicalLimit(900, "°C", "EGT continuous limit", "AMM 71-00-00"),
        "egt_start": TechnicalLimit(700, "°C", "EGT start limit (2 sec)", "AMM 71-00-00"),
        "tat_max": TechnicalLimit(50, "°C", "TAT maximum (ISA+30)", "AMM 71-00-00"),
        "tat_min": TechnicalLimit(-54, "°C", "TAT minimum", "AMM 71-00-00"),
        "tat_continuous": TechnicalLimit(42, "°C", "TAT continuous operation", "AMM 71-00-00"),
    }
    
    E140_MAX_SPEEDS = E135_MAX_SPEEDS
    E140_FLAP_SPEEDS = E135_FLAP_SPEEDS
    
    # E145 SPECIFICATIONS
    E145_HARD_LANDING = E135_HARD_LANDING  # Mesmos limites que E135/E140
    
    E145_WEIGHTS = WeightLimits(
        mtow=46517,  # 21,100 kg
        mlw=43651,   # 19,800 kg
        mzfw=40344,  # 18,300 kg
        oew=26455    # 12,000 kg
    )
    
    E145_CG = E135_CG
    E145_GEAR_SPEEDS = E135_GEAR_SPEEDS
    E145_TEMPERATURES = E140_TEMPERATURES  # AE 3007A1
    E145_MAX_SPEEDS = E135_MAX_SPEEDS
    E145_FLAP_SPEEDS = E135_FLAP_SPEEDS
    
    # ==================== FAMÍLIA E2 ====================
    
    # E190-E2 SPECIFICATIONS
    E190E2_HARD_LANDING = {
        "normal_limit": TechnicalLimit(2.0, "G", "Normal landing limit", "AMM 05-51-00"),
        "hard_limit": TechnicalLimit(2.6, "G", "Hard landing inspection required", "AMM 05-51-00"),
        "very_hard_limit": TechnicalLimit(2.8, "G", "Very hard landing - extensive inspection", "AMM 05-51-00"),
        "descent_normal": TechnicalLimit(600, "ft/min", "Normal descent rate", "AMM 05-51-00"),
        "descent_hard": TechnicalLimit(900, "ft/min", "Hard landing descent rate", "AMM 05-51-00"),
        "descent_very_hard": TechnicalLimit(1000, "ft/min", "Very hard landing descent rate", "AMM 05-51-00"),
    }
    
    E190E2_WEIGHTS = WeightLimits(
        mtow=124561,  # 56,500 kg
        mlw=109127,   # 49,500 kg
        mzfw=102736,  # 46,600 kg
        oew=71870     # 32,600 kg
    )
    
    E190E2_CG = CGLimits(
        forward_limit=15.0,
        aft_limit=39.0,
        normal_range=(20.0, 35.0)
    )
    
    E190E2_GEAR_SPEEDS = {
        "vle": TechnicalLimit(260, "KIAS", "Maximum speed with gear extended", "AFM Section 5"),
        "vlo_extend": TechnicalLimit(260, "KIAS", "Maximum speed for gear extension", "AFM Section 5"),
        "vlo_retract": TechnicalLimit(230, "KIAS", "Maximum speed for gear retraction", "AFM Section 5"),
        "inspection_threshold": TechnicalLimit(270, "KIAS", "VLE + 10 KIAS", "Maintenance Manual"),
    }
    
    E190E2_TEMPERATURES = {
        "egt_takeoff": TechnicalLimit(960, "°C", "EGT takeoff limit (5 min) - PW1700G", "AMM 71-00-00"),
        "egt_continuous": TechnicalLimit(925, "°C", "EGT continuous limit", "AMM 71-00-00"),
        "egt_start": TechnicalLimit(735, "°C", "EGT start limit (2 sec)", "AMM 71-00-00"),
        "tat_max": TechnicalLimit(54, "°C", "TAT maximum (ISA+35)", "AMM 71-00-00"),
        "tat_min": TechnicalLimit(-54, "°C", "TAT minimum", "AMM 71-00-00"),
        "tat_continuous": TechnicalLimit(45, "°C", "TAT continuous operation", "AMM 71-00-00"),
    }
    
    E190E2_MAX_SPEEDS = {
        "vmo": TechnicalLimit(330, "KIAS", "Maximum operating speed", "AFM Section 5"),
        "mmo": TechnicalLimit(0.82, "Mach", "Maximum operating Mach", "AFM Section 5"),
        "inspection_threshold": TechnicalLimit(340, "KIAS", "VMO + 10 KIAS", "Maintenance Manual"),
    }
    
    E190E2_FLAP_SPEEDS = {
        "flap_1": TechnicalLimit(260, "KIAS", "Flap 1 maximum speed", "AFM Limitations"),
        "flap_2": TechnicalLimit(240, "KIAS", "Flap 2 maximum speed", "AFM Limitations"),
        "flap_3": TechnicalLimit(220, "KIAS", "Flap 3 maximum speed", "AFM Limitations"),
        "flap_4": TechnicalLimit(210, "KIAS", "Flap 4 maximum speed", "AFM Limitations"),
        "flap_full": TechnicalLimit(185, "KIAS", "Flap FULL maximum speed", "AFM Limitations"),
    }
    
    # E195-E2 SPECIFICATIONS
    E195E2_HARD_LANDING = E190E2_HARD_LANDING  # Mesmos limites que E190-E2
    
    E195E2_WEIGHTS = WeightLimits(
        mtow=137038,  # 62,160 kg
        mlw=115963,   # 52,600 kg
        mzfw=108248,  # 49,100 kg
        oew=74957     # 34,000 kg
    )
    
    E195E2_CG = E190E2_CG
    E195E2_GEAR_SPEEDS = E190E2_GEAR_SPEEDS
    
    E195E2_TEMPERATURES = {
        "egt_takeoff": TechnicalLimit(960, "°C", "EGT takeoff limit (5 min) - PW1900G", "AMM 71-00-00"),
        "egt_continuous": TechnicalLimit(925, "°C", "EGT continuous limit", "AMM 71-00-00"),
        "egt_start": TechnicalLimit(735, "°C", "EGT start limit (2 sec)", "AMM 71-00-00"),
        "tat_max": TechnicalLimit(54, "°C", "TAT maximum (ISA+35)", "AMM 71-00-00"),
        "tat_min": TechnicalLimit(-54, "°C", "TAT minimum", "AMM 71-00-00"),
        "tat_continuous": TechnicalLimit(45, "°C", "TAT continuous operation", "AMM 71-00-00"),
    }
    
    E195E2_MAX_SPEEDS = E190E2_MAX_SPEEDS
    E195E2_FLAP_SPEEDS = E190E2_FLAP_SPEEDS
    
    # ==================== MÉTODOS AUXILIARES ====================
    
    @classmethod
    def get_specifications_by_model(cls, aircraft_model: str) -> Dict:
        """
        Retorna especificações completas para um modelo específico
        
        Args:
            aircraft_model: Código do modelo (e170, e175, e190, e195, e135, e140, e145, e190e2, e195e2)
            
        Returns:
            Dicionário com todas as especificações do modelo
        """
        model_upper = aircraft_model.upper().replace("-", "")
        
        specs_map = {
            "E170": {
                "hard_landing": cls.E170_HARD_LANDING,
                "weights": cls.E170_WEIGHTS,
                "cg": cls.E170_CG,
                "gear_speeds": cls.E170_GEAR_SPEEDS,
                "temperatures": cls.E170_TEMPERATURES,
                "max_speeds": cls.E170_MAX_SPEEDS,
                "flap_speeds": cls.E170_FLAP_SPEEDS,
            },
            "E175": {
                "hard_landing": cls.E175_HARD_LANDING,
                "weights": cls.E175_WEIGHTS,
                "cg": cls.E175_CG,
                "gear_speeds": cls.E175_GEAR_SPEEDS,
                "temperatures": cls.E175_TEMPERATURES,
                "max_speeds": cls.E175_MAX_SPEEDS,
                "flap_speeds": cls.E175_FLAP_SPEEDS,
            },
            "E190": {
                "hard_landing": cls.E190_HARD_LANDING,
                "weights": cls.E190_WEIGHTS,
                "cg": cls.E190_CG,
                "gear_speeds": cls.E190_GEAR_SPEEDS,
                "temperatures": cls.E190_TEMPERATURES,
                "max_speeds": cls.E190_MAX_SPEEDS,
                "flap_speeds": cls.E190_FLAP_SPEEDS,
            },
            "E195": {
                "hard_landing": cls.E195_HARD_LANDING,
                "weights": cls.E195_WEIGHTS,
                "cg": cls.E195_CG,
                "gear_speeds": cls.E195_GEAR_SPEEDS,
                "temperatures": cls.E195_TEMPERATURES,
                "max_speeds": cls.E195_MAX_SPEEDS,
                "flap_speeds": cls.E195_FLAP_SPEEDS,
            },
            "E135": {
                "hard_landing": cls.E135_HARD_LANDING,
                "weights": cls.E135_WEIGHTS,
                "cg": cls.E135_CG,
                "gear_speeds": cls.E135_GEAR_SPEEDS,
                "temperatures": cls.E135_TEMPERATURES,
                "max_speeds": cls.E135_MAX_SPEEDS,
                "flap_speeds": cls.E135_FLAP_SPEEDS,
            },
            "E140": {
                "hard_landing": cls.E140_HARD_LANDING,
                "weights": cls.E140_WEIGHTS,
                "cg": cls.E140_CG,
                "gear_speeds": cls.E140_GEAR_SPEEDS,
                "temperatures": cls.E140_TEMPERATURES,
                "max_speeds": cls.E140_MAX_SPEEDS,
                "flap_speeds": cls.E140_FLAP_SPEEDS,
            },
            "E145": {
                "hard_landing": cls.E145_HARD_LANDING,
                "weights": cls.E145_WEIGHTS,
                "cg": cls.E145_CG,
                "gear_speeds": cls.E145_GEAR_SPEEDS,
                "temperatures": cls.E145_TEMPERATURES,
                "max_speeds": cls.E145_MAX_SPEEDS,
                "flap_speeds": cls.E145_FLAP_SPEEDS,
            },
            "E190E2": {
                "hard_landing": cls.E190E2_HARD_LANDING,
                "weights": cls.E190E2_WEIGHTS,
                "cg": cls.E190E2_CG,
                "gear_speeds": cls.E190E2_GEAR_SPEEDS,
                "temperatures": cls.E190E2_TEMPERATURES,
                "max_speeds": cls.E190E2_MAX_SPEEDS,
                "flap_speeds": cls.E190E2_FLAP_SPEEDS,
            },
            "E195E2": {
                "hard_landing": cls.E195E2_HARD_LANDING,
                "weights": cls.E195E2_WEIGHTS,
                "cg": cls.E195E2_CG,
                "gear_speeds": cls.E195E2_GEAR_SPEEDS,
                "temperatures": cls.E195E2_TEMPERATURES,
                "max_speeds": cls.E195E2_MAX_SPEEDS,
                "flap_speeds": cls.E195E2_FLAP_SPEEDS,
            },
        }
        
        return specs_map.get(model_upper, None)
    
    @classmethod
    def get_weight_limits(cls, aircraft_model: str) -> Optional[WeightLimits]:
        """Retorna limites de peso para um modelo específico"""
        specs = cls.get_specifications_by_model(aircraft_model)
        return specs["weights"] if specs else None
    
    @classmethod
    def get_cg_limits(cls, aircraft_model: str) -> Optional[CGLimits]:
        """Retorna limites de CG para um modelo específico"""
        specs = cls.get_specifications_by_model(aircraft_model)
        return specs["cg"] if specs else None
    
    @classmethod
    def get_hard_landing_limits(cls, aircraft_model: str) -> Optional[Dict]:
        """Retorna limites de hard landing para um modelo específico"""
        specs = cls.get_specifications_by_model(aircraft_model)
        return specs["hard_landing"] if specs else None
    
    @classmethod
    def check_weight_exceedance(cls, aircraft_model: str, weight: float, weight_type: str = "mlw") -> Tuple[bool, str]:
        """
        Verifica se o peso excede os limites
        
        Args:
            aircraft_model: Código do modelo
            weight: Peso em lbs
            weight_type: Tipo de peso (mtow, mlw, mzfw)
            
        Returns:
            (excedido, mensagem)
        """
        limits = cls.get_weight_limits(aircraft_model)
        if not limits:
            return (False, f"Modelo {aircraft_model} não encontrado")
        
        limit_value = getattr(limits, weight_type, None)
        if limit_value is None:
            return (False, f"Tipo de peso {weight_type} inválido")
        
        if weight > limit_value:
            excess = weight - limit_value
            return (True, f"Peso excede {weight_type.upper()} em {excess:.0f} lbs ({excess * 0.453592:.0f} kg)")
        
        return (False, f"Peso dentro do limite {weight_type.upper()}")
    
    @classmethod
    def check_cg_limits(cls, aircraft_model: str, cg_mac: float) -> Tuple[bool, str]:
        """
        Verifica se o CG está dentro dos limites
        
        Args:
            aircraft_model: Código do modelo
            cg_mac: Centro de gravidade em % MAC
            
        Returns:
            (fora_dos_limites, mensagem)
        """
        cg_limits = cls.get_cg_limits(aircraft_model)
        if not cg_limits:
            return (False, f"Modelo {aircraft_model} não encontrado")
        
        if cg_mac < cg_limits.forward_limit:
            diff = cg_limits.forward_limit - cg_mac
            return (True, f"CG muito à frente do limite ({diff:.1f}% MAC)")
        
        if cg_mac > cg_limits.aft_limit:
            diff = cg_mac - cg_limits.aft_limit
            return (True, f"CG muito atrás do limite ({diff:.1f}% MAC)")
        
        return (False, f"CG dentro dos limites normais")


# Helper function for easy integration
def get_specifications_by_model(aircraft_family: str, model: str = None) -> object:
    """
    Função auxiliar para obter especificações de forma simplificada
    
    Args:
        aircraft_family: 'e1', 'e2', 'e145', 'e170', etc.
        model: 'E190', 'E195', 'E170', etc. (opcional, inferido da family se não fornecido)
        
    Returns:
        Objeto simples com atributos mlw_kg, hard_landing_g, cg_limits_percent_mac
    """
    # Mapear family para model se não fornecido
    if not model:
        family_to_model = {
            'e1': 'E190',
            'e190': 'E190',
            'e195': 'E195',
            'e170': 'E170',
            'e175': 'E175',
            'e145': 'E145',
            'e140': 'E140',
            'e135': 'E135',
            'e2': 'E190E2',
            'e2-190': 'E190E2',
            'e2-195': 'E195E2',
        }
        model = family_to_model.get(aircraft_family.lower(), 'E190')
    
    # Obter especificações completas
    specs = AllFamiliesSpecifications.get_specifications_by_model(model)
    
    if not specs:
        # Fallback para E190
        specs = AllFamiliesSpecifications.get_specifications_by_model('E190')
    
    # Criar objeto simplificado
    class SimpleSpecs:
        def __init__(self, specs_dict):
            # Converter MLW de lbs para kg
            self.mlw_lbs = specs_dict['weights'].mlw
            self.mlw_kg = self.mlw_lbs * 0.453592  # lbs to kg
            
            # Hard landing G limit
            self.hard_landing_g = specs_dict['hard_landing']['hard_limit'].value
            
            # CG limits
            cg = specs_dict['cg']
            self.cg_limits_percent_mac = (cg.forward_limit, cg.aft_limit)
            
            # Guardar especificações completas
            self._full_specs = specs_dict
    
    return SimpleSpecs(specs)


# Exemplo de uso
if __name__ == "__main__":
    # Teste E190
    print("=== E190 SPECIFICATIONS ===")
    e190_specs = AllFamiliesSpecifications.get_specifications_by_model("E190")
    print(f"MTOW: {e190_specs['weights'].mtow} lbs")
    print(f"MLW: {e190_specs['weights'].mlw} lbs")
    print(f"Hard Landing Limit: {e190_specs['hard_landing']['hard_limit'].value} {e190_specs['hard_landing']['hard_limit'].unit}")
    
    # Teste de excedência de peso
    exceeds, msg = AllFamiliesSpecifications.check_weight_exceedance("E190", 98000, "mlw")
    print(f"\nTeste peso 98,000 lbs: {msg}")
    
    # Teste de CG
    exceeds, msg = AllFamiliesSpecifications.check_cg_limits("E190", 38.0)
    print(f"Teste CG 38% MAC: {msg}")
    
    # Teste da função auxiliar
    print("\n=== TESTE FUNÇÃO AUXILIAR ===")
    simple_specs = get_specifications_by_model('e1', 'E190')
    print(f"MLW (kg): {simple_specs.mlw_kg:.0f}")
    print(f"Hard Landing G: {simple_specs.hard_landing_g}")
    print(f"CG Limits: {simple_specs.cg_limits_percent_mac}")

