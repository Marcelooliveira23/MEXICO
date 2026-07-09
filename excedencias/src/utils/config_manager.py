"""
Advanced Configuration System
Handles user preferences, theme settings, and application configuration
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, asdict, field
from enum import Enum


class Theme(Enum):
    """Application themes"""
    LIGHT = "light"
    DARK = "dark"
    HIGH_CONTRAST = "high_contrast"
    MEXICANA = "mexicana"  # Default blue theme


class Language(Enum):
    """Supported languages"""
    ENGLISH = "en"
    PORTUGUESE = "pt-BR"
    SPANISH = "es"
    FRENCH = "fr"


@dataclass
class UISettings:
    """User interface settings"""
    theme: str = Theme.MEXICANA.value
    language: str = Language.ENGLISH.value
    font_size: int = 10
    button_size: str = "medium"  # small, medium, large
    show_tooltips: bool = True
    animations_enabled: bool = True
    window_width: int = 1024
    window_height: int = 768
    window_maximized: bool = False


@dataclass
class AnalysisSettings:
    """Analysis configuration"""
    auto_save_results: bool = True
    show_ai_recommendations: bool = True
    enable_dynamic_rules: bool = True
    rules_cache_enabled: bool = True
    confidence_threshold: float = 0.75
    max_exceedance_duration: float = 10.0  # seconds
    generate_charts: bool = True
    export_format: str = "PDF"  # PDF, CSV, JSON


@dataclass
class PDFSettings:
    """PDF processing settings"""
    auto_extract_graphics: bool = False
    graphics_min_size: int = 100  # pixels
    max_graphics_per_pdf: int = 50
    extract_tables: bool = True
    ocr_enabled: bool = False
    cache_extracted_content: bool = True


@dataclass
class PerformanceSettings:
    """Performance optimization settings"""
    enable_performance_monitoring: bool = False
    cache_size_mb: int = 100
    max_concurrent_operations: int = 4
    lazy_load_pdfs: bool = True
    preload_rules: bool = True
    log_level: str = "INFO"  # DEBUG, INFO, WARNING, ERROR


@dataclass
class NotificationSettings:
    """Notification preferences"""
    enable_notifications: bool = True
    show_analysis_complete: bool = True
    show_errors: bool = True
    sound_enabled: bool = False
    email_notifications: bool = False
    email_address: str = ""


@dataclass
class AppConfiguration:
    """Complete application configuration"""
    version: str = "2.0.0"
    ui: UISettings = field(default_factory=UISettings)
    analysis: AnalysisSettings = field(default_factory=AnalysisSettings)
    pdf: PDFSettings = field(default_factory=PDFSettings)
    performance: PerformanceSettings = field(default_factory=PerformanceSettings)
    notifications: NotificationSettings = field(default_factory=NotificationSettings)
    
    # Recent files
    recent_files: list = field(default_factory=list)
    max_recent_files: int = 10
    
    # User preferences
    default_aircraft: Optional[str] = None
    default_event: Optional[str] = None
    last_export_directory: str = ""
    last_import_directory: str = ""


class ConfigurationManager:
    """Manage application configuration"""
    
    def __init__(self, config_file: str = "config/app_config.json"):
        self.config_file = Path(config_file)
        self.config_file.parent.mkdir(exist_ok=True)
        self.config = self.load()
    
    def load(self) -> AppConfiguration:
        """Load configuration from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                
                # Reconstruct dataclasses
                config = AppConfiguration(
                    version=data.get('version', '2.0.0'),
                    ui=UISettings(**data.get('ui', {})),
                    analysis=AnalysisSettings(**data.get('analysis', {})),
                    pdf=PDFSettings(**data.get('pdf', {})),
                    performance=PerformanceSettings(**data.get('performance', {})),
                    notifications=NotificationSettings(**data.get('notifications', {})),
                    recent_files=data.get('recent_files', []),
                    max_recent_files=data.get('max_recent_files', 10),
                    default_aircraft=data.get('default_aircraft'),
                    default_event=data.get('default_event'),
                    last_export_directory=data.get('last_export_directory', ''),
                    last_import_directory=data.get('last_import_directory', '')
                )
                
                print(f"✅ Configuration loaded from {self.config_file}")
                return config
            
            except Exception as e:
                print(f"⚠️  Error loading config: {e}. Using defaults.")
                return AppConfiguration()
        else:
            print(f"📝 Creating default configuration")
            config = AppConfiguration()
            self.save(config)
            return config
    
    def save(self, config: Optional[AppConfiguration] = None):
        """Save configuration to file"""
        if config is None:
            config = self.config
        
        data = {
            'version': config.version,
            'ui': asdict(config.ui),
            'analysis': asdict(config.analysis),
            'pdf': asdict(config.pdf),
            'performance': asdict(config.performance),
            'notifications': asdict(config.notifications),
            'recent_files': config.recent_files,
            'max_recent_files': config.max_recent_files,
            'default_aircraft': config.default_aircraft,
            'default_event': config.default_event,
            'last_export_directory': config.last_export_directory,
            'last_import_directory': config.last_import_directory
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"💾 Configuration saved to {self.config_file}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot notation key"""
        parts = key.split('.')
        value = self.config
        
        for part in parts:
            if hasattr(value, part):
                value = getattr(value, part)
            else:
                return default
        
        return value
    
    def set(self, key: str, value: Any):
        """Set configuration value by dot notation key"""
        parts = key.split('.')
        target = self.config
        
        # Navigate to parent
        for part in parts[:-1]:
            if hasattr(target, part):
                target = getattr(target, part)
            else:
                raise ValueError(f"Invalid configuration key: {key}")
        
        # Set final value
        if hasattr(target, parts[-1]):
            setattr(target, parts[-1], value)
            self.save()
        else:
            raise ValueError(f"Invalid configuration key: {key}")
    
    def add_recent_file(self, file_path: str):
        """Add file to recent files list"""
        if file_path in self.config.recent_files:
            self.config.recent_files.remove(file_path)
        
        self.config.recent_files.insert(0, file_path)
        
        # Limit to max recent files
        if len(self.config.recent_files) > self.config.max_recent_files:
            self.config.recent_files = self.config.recent_files[:self.config.max_recent_files]
        
        self.save()
    
    def get_recent_files(self) -> list:
        """Get list of recent files"""
        return self.config.recent_files
    
    def clear_recent_files(self):
        """Clear recent files list"""
        self.config.recent_files = []
        self.save()
    
    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        self.config = AppConfiguration()
        self.save()
        print("🔄 Configuration reset to defaults")
    
    def export_config(self, export_path: str):
        """Export configuration to another file"""
        data = {
            'version': self.config.version,
            'ui': asdict(self.config.ui),
            'analysis': asdict(self.config.analysis),
            'pdf': asdict(self.config.pdf),
            'performance': asdict(self.config.performance),
            'notifications': asdict(self.config.notifications),
            'recent_files': self.config.recent_files,
            'max_recent_files': self.config.max_recent_files,
            'default_aircraft': self.config.default_aircraft,
            'default_event': self.config.default_event,
            'last_export_directory': self.config.last_export_directory,
            'last_import_directory': self.config.last_import_directory
        }
        
        with open(export_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"📤 Configuration exported to {export_path}")
    
    def import_config(self, import_path: str):
        """Import configuration from another file"""
        self.config_file = Path(import_path)
        self.config = self.load()
        print(f"📥 Configuration imported from {import_path}")


# Global configuration manager instance
_config_manager = None


def get_config() -> ConfigurationManager:
    """Get global configuration manager instance"""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigurationManager()
    return _config_manager


# ==================== EXAMPLE USAGE ====================

if __name__ == "__main__":
    print("=" * 70)
    print("CONFIGURATION SYSTEM TEST")
    print("=" * 70)
    
    # Create configuration manager
    config_mgr = ConfigurationManager("config/test_config.json")
    
    # Display current settings
    print("\n📋 Current Configuration:")
    print(f"   Theme: {config_mgr.config.ui.theme}")
    print(f"   Language: {config_mgr.config.ui.language}")
    print(f"   AI Recommendations: {config_mgr.config.analysis.show_ai_recommendations}")
    print(f"   Dynamic Rules: {config_mgr.config.analysis.enable_dynamic_rules}")
    print(f"   Performance Monitoring: {config_mgr.config.performance.enable_performance_monitoring}")
    
    # Modify settings
    print("\n🔧 Modifying Settings...")
    config_mgr.set('ui.theme', Theme.DARK.value)
    config_mgr.set('ui.font_size', 12)
    config_mgr.set('analysis.show_ai_recommendations', True)
    config_mgr.set('performance.enable_performance_monitoring', True)
    
    # Add recent files
    print("\n📁 Adding Recent Files...")
    config_mgr.add_recent_file("E:/Data/flight_001.csv")
    config_mgr.add_recent_file("E:/Data/flight_002.csv")
    config_mgr.add_recent_file("E:/Data/flight_003.csv")
    
    # Display recent files
    print("\n📂 Recent Files:")
    for i, file in enumerate(config_mgr.get_recent_files(), 1):
        print(f"   {i}. {file}")
    
    # Get specific values
    print("\n🔍 Get Specific Values:")
    print(f"   UI Theme: {config_mgr.get('ui.theme')}")
    print(f"   Font Size: {config_mgr.get('ui.font_size')}")
    print(f"   Cache Size: {config_mgr.get('performance.cache_size_mb')} MB")
    
    # Export configuration
    print("\n📤 Exporting Configuration...")
    config_mgr.export_config("config/exported_config.json")
    
    print("\n✅ Configuration test complete!")
    print("=" * 70)

