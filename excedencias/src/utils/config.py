"""
Configurações da aplicação
"""

from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional
from models.aircraft_model import AircraftModelRegistry, ModelSpecifications


@dataclass
class AircraftFamily:
    """Configuração de uma família de aeronave"""
    id: str
    name: str
    display_name: str
    color: str
    pdf_folder: Path
    models: List[str] = None  # Lista de model_ids pertencentes a esta família
    
    def __post_init__(self):
        """Inicializar models se não fornecido"""
        if self.models is None:
            # Mapear para novos modelos disponíveis
            legacy_mapping = {
                "e145": ["e145"],
                "e170": ["e170", "e175"],
                "e1": ["e190", "e195"],
                "e2": ["e175_e2", "e190_e2", "e195_e2"],
            }
            self.models = legacy_mapping.get(self.id, [])


@dataclass
class EventCategory:
    """Categoria de evento para análise"""
    id: str
    name: str
    description: str
    icon: str = ""


class AppConfig:
    """Configurações globais da aplicação"""
    
    # Informações da aplicação
    APP_NAME = "Aircraft Inspection Analysis System"
    APP_VERSION = "1.0.0"
    ORGANIZATION = "Aviation Inspection"
    
    # Diretórios
    BASE_DIR = Path(__file__).parent.parent.parent
    SRC_DIR = BASE_DIR / "src"
    DATA_DIR = BASE_DIR / "data"
    ASSETS_DIR = BASE_DIR / "assets"
    LOGS_DIR = BASE_DIR / "logs"
    OUTPUT_DIR = BASE_DIR / "output"
    
    # Famílias de aeronaves
    AIRCRAFT_FAMILIES: List[AircraftFamily] = [
        AircraftFamily(
            id="e145",
            name="E145",
            display_name="Mexicana E145 Family",
            color="#1B4965",
            pdf_folder=BASE_DIR / "E145"
        ),
        AircraftFamily(
            id="e170",
            name="E170",
            display_name="Mexicana E170 Family (E170/E175)",
            color="#4A90A4",
            pdf_folder=BASE_DIR / "E170"
        ),
        AircraftFamily(
            id="e1",
            name="E1",
            display_name="Mexicana E-Jets E1 Family (E190/E195)",
            color="#62B6CB",
            pdf_folder=BASE_DIR / "E1"
        ),
        AircraftFamily(
            id="e2",
            name="E2",
            display_name="Mexicana E-Jets E2 (E190-E2/E195-E2)",
            color="#5FA8D3",
            pdf_folder=BASE_DIR / "E2"
        ),
    ]
    
    # Categorias de eventos
    EVENT_CATEGORIES: List[EventCategory] = [
        EventCategory(
            id="hard_landing",
            name="Hard Landing",
            description="Análise de pouso duro - impacto excessivo",
            icon="landing"
        ),
        EventCategory(
            id="over_g",
            name="Over-G",
            description="Excedência de carga G (manobra agressiva)",
            icon="g_force"
        ),
        EventCategory(
            id="high_bank_angle",
            name="High Bank Angle",
            description="Ângulo de bank excessivo",
            icon="bank_angle"
        ),
        EventCategory(
            id="gear_overspeed",
            name="LG overspeed",
            description="Landing gear overspeed condition",
            icon="speed_warning"
        ),
        EventCategory(
            id="temp_envelope",
            name="TEMP Envelope",
            description="Temperature envelope exceedance",
            icon="temperature"
        ),
        EventCategory(
            id="max_speed",
            name="Maximum Operating Speed",
            description="Excesso de velocidade operacional máxima (VMO)",
            icon="speed"
        ),
        EventCategory(
            id="flap_overspeed",
            name="Maximum Flap/Slat Extended Speed",
            description="Velocidade excessiva com flaps/slats estendidos",
            icon="flaps"
        ),
        EventCategory(
            id="overweight_landing",
            name="Overweight Landing",
            description="Pouso acima do peso máximo permitido",
            icon="weight"
        ),
        EventCategory(
            id="turbulence",
            name="Turbulence",
            description="Turbulence encounter exceedance analysis",
            icon="turbulence"
        ),
    ]
    
    # Formatos de arquivo suportados
    SUPPORTED_FILE_FORMATS = [".csv", ".txt"]
    
    # Configurações de análise
    DECIMAL_PLACES = 3
    DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
    
    # Configurações de exportação
    EXPORT_FORMATS = ["PDF", "Excel", "TXT"]
    
    @classmethod
    def get_aircraft_by_id(cls, aircraft_id: str) -> AircraftFamily | None:
        """Retorna família de aeronave por ID (case-insensitive)"""
        aircraft_id_upper = aircraft_id.upper()
        for family in cls.AIRCRAFT_FAMILIES:
            if family.id.upper() == aircraft_id_upper:
                return family
        return None
    
    @classmethod
    def get_model_spec(cls, model_id: str) -> Optional[ModelSpecifications]:
        """Retorna especificações de um modelo específico"""
        return AircraftModelRegistry.get_model(model_id)
    
    @classmethod
    def get_models_for_family(cls, family_id: str) -> List[ModelSpecifications]:
        """Retorna todos os modelos de uma família"""
        family_id = family_id.lower()
        return AircraftModelRegistry.get_models_by_family(family_id)
    
    @classmethod
    def get_model_mtow(cls, model_id: str) -> float:
        """Retorna MTOW em lbs para um modelo"""
        return AircraftModelRegistry.get_mtow(model_id)
    
    @classmethod
    def get_model_mlw(cls, model_id: str) -> float:
        """Retorna MLW em lbs para um modelo"""
        return AircraftModelRegistry.get_mlw(model_id)
    
    @classmethod
    def get_hard_landing_pdf(cls, model_id: str) -> str:
        """Retorna qual PDF usar para Hard Landing de um modelo"""
        return AircraftModelRegistry.get_hard_landing_pdf_reference(model_id)
    
    @classmethod
    def list_all_models(cls) -> List[str]:
        """Retorna lista de todos os model IDs disponíveis"""
        return AircraftModelRegistry.list_all_models()
    
    @classmethod
    def get_family_for_model(cls, model_id: str) -> Optional[AircraftFamily]:
        """Retorna a família a que um modelo pertence"""
        spec = cls.get_model_spec(model_id)
        if spec:
            return cls.get_aircraft_by_id(spec.family_id)
        return None
    
    @classmethod
    def get_event_by_id(cls, event_id: str) -> EventCategory | None:
        """Retorna categoria de evento por ID"""
        for event in cls.EVENT_CATEGORIES:
            if event.id == event_id:
                return event
        return None
    
    @classmethod
    def ensure_directories(cls):
        """Cria diretórios necessários se não existirem"""
        for directory in [cls.LOGS_DIR, cls.OUTPUT_DIR]:
            directory.mkdir(parents=True, exist_ok=True)

