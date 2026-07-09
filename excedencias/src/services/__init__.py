"""
Módulo de serviços
"""

from .csv_parser import CSVParser
from .csv_column_mapper import CSVColumnMapper, get_mapper
from .data_pipeline import DataPipeline, DataPipelineConfig, PipelineResult
from .rules_engine import RulesEngine, FlightAnalysis, AnalysisResult
from .report_generator import ReportGenerator
from .turbulence_analyzer import TurbulenceAnalyzer, TurbulenceResult

try:
    from .pdf_mapper import PDFMapper, PDFDocument
except Exception:
    PDFMapper = None
    PDFDocument = None

try:
    from .pdf_extractor import PDFExtractor
except Exception:
    PDFExtractor = None

try:
    from .pdf_rules_extractor import PDFRulesExtractor, TechnicalLimit, InspectionRule
except Exception:
    PDFRulesExtractor = None
    TechnicalLimit = None
    InspectionRule = None

try:
    from .pdf_graphics_extractor import PDFGraphicsExtractor, PDFImage
except Exception:
    PDFGraphicsExtractor = None
    PDFImage = None

try:
    from .ai_assistant import AIAssistant, AIRecommendation, AIAnalysis
except Exception:
    AIAssistant = None
    AIRecommendation = None
    AIAnalysis = None

__all__ = [
    "CSVParser", "CSVColumnMapper", "get_mapper",
    "DataPipeline", "DataPipelineConfig", "PipelineResult",
    "PDFMapper", "PDFDocument", "PDFExtractor",
    "RulesEngine", "FlightAnalysis", "AnalysisResult", "ReportGenerator",
    "PDFRulesExtractor", "TechnicalLimit", "InspectionRule",
    "PDFGraphicsExtractor", "PDFImage",
    "AIAssistant", "AIRecommendation", "AIAnalysis",
    "TurbulenceAnalyzer", "TurbulenceResult"
]
