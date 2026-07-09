"""
Modelos de Aeronaves com Suporte a Sub-modelos
Infraestrutura de Etapa 1 - Conformidade AMM
"""

from dataclasses import dataclass
from typing import Dict, Optional, List
from enum import Enum


class AircraftFamily(Enum):
    """Famílias de aeronaves Mexicana"""
    E145 = "e145"
    E170_E175 = "e170_e175"  # E1 Familie narrowbody
    E190_E195 = "e190_e195"  # E1 Familie widebody
    E2_FAMILY = "e2"         # E2 Familie


class AircraftModel(Enum):
    """Modelos específicos de aeronaves"""
    # E145
    E145 = "e145"
    
    # E1 narrowbody
    E170 = "e170"
    E175 = "e175"
    
    # E1 widebody
    E190 = "e190"
    E195 = "e195"
    
    # E2
    E175_E2 = "e175_e2"
    E190_E2 = "e190_e2"
    E195_E2 = "e195_e2"


@dataclass
class ModelSpecifications:
    """Especificações de um modelo de aeronave específico"""
    model_id: str
    model_name: str
    family_id: str
    family_name: str
    
    # Pesos (lbs)
    mtow: float  # Maximum Takeoff Weight
    mlw: float   # Maximum Landing Weight
    mzfw: float  # Maximum Zero Fuel Weight
    oew: float   # Operating Empty Weight
    
    # Referências técnicas
    pdf_hard_landing: str  # Qual PDF usar para Hard Landing (ex: "801" ou "804")
    
    # Descrição
    description: str
    

class AircraftModelRegistry:
    """Registro centralizado de modelos com suas especificações"""
    
    # Especificações de peso e características de cada modelo
    MODELS: Dict[str, ModelSpecifications] = {
        # E145
        "e145": ModelSpecifications(
            model_id="e145",
            model_name="E145",
            family_id="e145",
            family_name="E145",
            mtow=48500,      # 22,000 kg
            mlw=44000,       # 20,000 kg
            mzfw=41000,      # 18,600 kg
            oew=27830,       # 12,625 kg
            pdf_hard_landing="e145_05_50_03",
            description="Mexicana E145 Regional Jet"
        ),
        
        # E1 narrowbody - E170
        "e170": ModelSpecifications(
            model_id="e170",
            model_name="E170",
            family_id="e170_e175",
            family_name="E170/E175",
            mtow=79344,      # 36,000 kg
            mlw=69224,       # 31,400 kg
            mzfw=64157,      # 29,100 kg
            oew=47399,       # 21,500 kg
            pdf_hard_landing="801",  # PDF 801 é para E170/E175
            description="Mexicana E170 Regional Jet"
        ),
        
        # E1 narrowbody - E175
        "e175": ModelSpecifications(
            model_id="e175",
            model_name="E175",
            family_id="e170_e175",
            family_name="E170/E175",
            mtow=88288,      # 40,050 kg (2000 kg more than E170)
            mlw=77161,       # 35,000 kg
            mzfw=71650,      # 32,500 kg
            oew=49500,       # 22,450 kg
            pdf_hard_landing="801",  # Mesmo PDF que E170
            description="Mexicana E175 Regional Jet"
        ),
        
        # E1 widebody - E190
        "e190": ModelSpecifications(
            model_id="e190",
            model_name="E190",
            family_id="e190_e195",
            family_name="E190/E195",
            mtow=123676,     # 56,150 kg
            mlw=108247,      # 49,100 kg
            mzfw=103413,     # 46,900 kg
            oew=62173,       # 28,200 kg
            pdf_hard_landing="804",  # PDF 804 para E190/E195 (DIFERENTE de E170!)
            description="Mexicana E190 Regional Jet"
        ),
        
        # E1 widebody - E195
        "e195": ModelSpecifications(
            model_id="e195",
            model_name="E195",
            family_id="e190_e195",
            family_name="E190/E195",
            mtow=133289,     # 60,500 kg (4350 kg more than E190!)
            mlw=116640,      # 52,900 kg
            mzfw=110882,     # 50,300 kg
            oew=62173,       # 28,200 kg
            pdf_hard_landing="804",  # Mesmo PDF que E190
            description="Mexicana E195 Regional Jet"
        ),
        
        # E2 - E175-E2
        "e175_e2": ModelSpecifications(
            model_id="e175_e2",
            model_name="E175-E2",
            family_id="e2",
            family_name="E2",
            mtow=90000,      # 40,823 kg (estimated)
            mlw=79380,       # 36,000 kg (estimated)
            mzfw=72600,      # 32,910 kg (estimated)
            oew=50000,       # 22,680 kg (estimated)
            pdf_hard_landing="e2_05_50_03",
            description="Mexicana E175-E2 Regional Jet"
        ),
        
        # E2 - E190-E2
        "e190_e2": ModelSpecifications(
            model_id="e190_e2",
            model_name="E190-E2",
            family_id="e2",
            family_name="E2",
            mtow=126200,     # 57,240 kg
            mlw=110674,      # 50,200 kg
            mzfw=105823,     # 48,000 kg
            oew=62000,       # 28,123 kg
            pdf_hard_landing="e2_05_50_03",
            description="Mexicana E190-E2 Regional Jet"
        ),
        
        # E2 - E195-E2
        "e195_e2": ModelSpecifications(
            model_id="e195_e2",
            model_name="E195-E2",
            family_id="e2",
            family_name="E2",
            mtow=135622,     # 61,534 kg
            mlw=119050,      # 54,000 kg
            mzfw=113398,     # 51,400 kg
            oew=62000,       # 28,123 kg
            pdf_hard_landing="e2_05_50_03",
            description="Mexicana E195-E2 Regional Jet"
        ),
    }
    
    @classmethod
    def get_model(cls, model_id: str) -> Optional[ModelSpecifications]:
        """Retorna especificações de um modelo específico"""
        return cls.MODELS.get(model_id.lower())
    
    @classmethod
    def get_models_by_family(cls, family_id: str) -> List[ModelSpecifications]:
        """Retorna todos os modelos de uma família"""
        family_id = family_id.lower()
        
        # Mapeamento de family_id legado para family_id interno
        family_mapping = {
            "e145": "e145",
            "e170": "e170_e175",  # Legacy "e170" maps to "e170_e175" internal
            "e1": "e190_e195",    # Legacy "e1" maps to "e190_e195" internal
            "e2": "e2",
        }
        
        internal_family_id = family_mapping.get(family_id, family_id)
        return [spec for spec in cls.MODELS.values() 
                if spec.family_id == internal_family_id]
    
    @classmethod
    def list_all_models(cls) -> List[str]:
        """Retorna lista de todos os model IDs"""
        return list(cls.MODELS.keys())
    
    @classmethod
    def get_model_name(cls, model_id: str) -> str:
        """Retorna nome do modelo (ex: 'E190')"""
        spec = cls.get_model(model_id)
        return spec.model_name if spec else ""
    
    @classmethod
    def get_mtow(cls, model_id: str) -> float:
        """Retorna MTOW em lbs para um modelo"""
        spec = cls.get_model(model_id)
        return spec.mtow if spec else 0
    
    @classmethod
    def get_mlw(cls, model_id: str) -> float:
        """Retorna MLW em lbs para um modelo"""
        spec = cls.get_model(model_id)
        return spec.mlw if spec else 0
    
    @classmethod
    def get_hard_landing_pdf_reference(cls, model_id: str) -> str:
        """Retorna qual PDF usar para Hard Landing"""
        spec = cls.get_model(model_id)
        return spec.pdf_hard_landing if spec else ""


# Mapeamento de família antiga (string) para novos modelos
LEGACY_FAMILY_TO_MODELS = {
    "e145": ["e145"],
    "e170": ["e170", "e175"],  # Ambos E170/E175 na antiga "família E170"
    "e1": ["e190", "e195"],    # Ambos E190/E195 na antiga "família E1"
    "e2": ["e175_e2", "e190_e2", "e195_e2"],
}


def get_models_for_legacy_family(family_id: str) -> List[str]:
    """Converte family_id legado para lista de model_ids modernos"""
    return LEGACY_FAMILY_TO_MODELS.get(family_id.lower(), [])

