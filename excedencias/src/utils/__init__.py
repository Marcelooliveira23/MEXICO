"""
Módulo de utilitários
"""

from .colors import AppColors, AircraftColors
from .config import AppConfig
from .logger import setup_logger
from .styles import get_app_stylesheet, get_button_style

# Optional imports - may not be available in all environments
try:
    from .performance_monitor import PerformanceMonitor, get_monitor, measure_performance
    PERFORMANCE_MONITOR_AVAILABLE = True
except ImportError:
    PerformanceMonitor = None
    get_monitor = None
    measure_performance = None
    PERFORMANCE_MONITOR_AVAILABLE = False

try:
    from .config_manager import ConfigurationManager, get_config, Theme, Language
    CONFIG_MANAGER_AVAILABLE = True
except ImportError:
    ConfigurationManager = None
    get_config = None
    Theme = None
    Language = None
    CONFIG_MANAGER_AVAILABLE = False

try:
    from .database import DatabaseManager, FlightRecord, AnalysisRecord, AuditTrail
    DATABASE_AVAILABLE = True
except ImportError:
    DatabaseManager = None
    FlightRecord = None
    AnalysisRecord = None
    AuditTrail = None
    DATABASE_AVAILABLE = False

__all__ = [
    "AppColors",
    "AircraftColors",
    "AppConfig",
    "setup_logger",
    "get_app_stylesheet",
    "get_button_style",
    "PerformanceMonitor",
    "get_monitor",
    "measure_performance",
    "ConfigurationManager",
    "get_config",
    "Theme",
    "Language",
    "DatabaseManager",
    "FlightRecord",
    "AnalysisRecord",
    "AuditTrail",
    "PERFORMANCE_MONITOR_AVAILABLE",
    "CONFIG_MANAGER_AVAILABLE",
    "DATABASE_AVAILABLE",
]
