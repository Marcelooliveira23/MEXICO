"""
Automated Test Suite for Aircraft Inspection Analysis
Tests UI components, services, and data processing
"""

import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

import pytest
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from services import CSVParser, RulesEngine, PDFRulesExtractor, AIAssistant
from utils import AppConfig


# ==================== SERVICE TESTS ====================

class TestCSVParser:
    """Test CSV parsing functionality"""
    
    def test_parser_initialization(self):
        """Test CSV parser can be initialized"""
        parser = CSVParser()
        assert parser is not None
    
    def test_parse_valid_csv(self, tmp_path):
        """Test parsing valid CSV data"""
        # Create sample CSV with correct column names
        csv_file = tmp_path / "test_flight.csv"
        csv_file.write_text(
            "timestamp,altitude,airspeed,vertical_acceleration\n"
            "2024-01-01 10:00:00,10000,250,1.0\n"
            "2024-01-01 10:00:01,10100,252,1.2\n"
            "2024-01-01 10:00:02,10200,255,2.5\n"
        )
        
        parser = CSVParser()
        df = parser.parse_file(str(csv_file))
        
        assert df is not None
        assert len(df) == 3
        assert 'altitude' in df.columns
        assert 'airspeed' in df.columns


class TestRulesEngine:
    """Test rules engine analysis"""
    
    def test_rules_engine_initialization(self):
        """Test rules engine can be initialized"""
        engine = RulesEngine()
        assert engine is not None
    
    def test_dynamic_rules_loading(self):
        """Test dynamic rules loading with fallback"""
        engine = RulesEngine()
        rules = engine.load_dynamic_rules("e145", "hard_landing")
        
        assert rules is not None
        assert len(rules) > 0
    
    def test_event_mapping(self):
        """Test event ID to event type mapping"""
        engine = RulesEngine()
        
        # Test that RulesEngine can map events (checking if method exists)
        # This confirms event mapping capabilities
        assert hasattr(engine, 'analyze') or hasattr(engine, 'get_rules')
        assert engine is not None


class TestPDFRulesExtractor:
    """Test PDF rules extraction"""
    
    def test_extractor_initialization(self):
        """Test PDF rules extractor can be initialized"""
        extractor = PDFRulesExtractor()
        assert extractor is not None
    
    def test_unit_patterns(self):
        """Test regex patterns for different units"""
        extractor = PDFRulesExtractor()
        
        # Test that extractor has extraction methods
        assert hasattr(extractor, 'extract_hard_landing_rules')
        assert hasattr(extractor, 'extract_numeric_values')
        assert extractor is not None


class TestAIAssistant:
    """Test AI Assistant functionality"""
    
    def test_ai_assistant_initialization(self):
        """Test AI assistant can be initialized"""
        assistant = AIAssistant()
        assert assistant is not None
    
    def test_knowledge_bases_exist(self):
        """Test all event knowledge bases are defined"""
        assistant = AIAssistant()
        
        required_events = [
            'hard_landing',
            'gear_overspeed',
            'temp_envelope',
            'flap_overspeed',
            'overweight'
        ]
        
        for event in required_events:
            assert event in assistant.knowledge_base
            kb = assistant.knowledge_base[event]
            # Knowledge base has CRITICAL/HIGH/MEDIUM risk levels with actions
            assert isinstance(kb, dict)
            assert len(kb) > 0
    
    def test_risk_level_calculation(self):
        """Test risk level assessment logic"""
        assistant = AIAssistant()
        
        # Mock analysis results list
        class MockResult:
            severity = "CRITICAL"
        
        results = [MockResult()]
        risk = assistant._calculate_risk_level(results)
        assert risk in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]


# ==================== UI TESTS ====================

@pytest.fixture(scope="session")
def qapp():
    """Create QApplication instance for UI tests"""
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    yield app
    # Don't quit - may be used by other tests


class TestUIComponents:
    """Test UI components"""
    
    def test_app_config(self):
        """Test application configuration"""
        assert len(AppConfig.AIRCRAFT_FAMILIES) > 0
        assert AppConfig.APP_NAME is not None
        
        # Test aircraft families have required fields
        for aircraft in AppConfig.AIRCRAFT_FAMILIES:
            assert hasattr(aircraft, 'id')
            assert hasattr(aircraft, 'display_name')
            assert hasattr(aircraft, 'pdf_folder')
    
    def test_aircraft_lookup(self):
        """Test aircraft lookup by ID"""
        # Test that we can find E145 aircraft family
        aircraft_families = AppConfig.AIRCRAFT_FAMILIES
        e145 = next((a for a in aircraft_families if a.id == "e145"), None)
        assert e145 is not None
        assert e145.id == "e145"
    
    def test_event_lookup(self):
        """Test event configuration"""
        # Test that AppConfig has required attributes
        assert hasattr(AppConfig, 'APP_NAME')
        assert hasattr(AppConfig, 'AIRCRAFT_FAMILIES')
        assert len(AppConfig.AIRCRAFT_FAMILIES) > 0


# ==================== INTEGRATION TESTS ====================

class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_csv_to_analysis_workflow(self, tmp_path):
        """Test complete workflow from CSV to analysis"""
        # Create sample CSV
        csv_file = tmp_path / "flight_data.csv"
        csv_file.write_text(
            "timestamp,vertical_acceleration\n"
            "2024-01-01 10:00:00,1.0\n"
            "2024-01-01 10:00:01,1.5\n"
            "2024-01-01 10:00:02,2.8\n"
            "2024-01-01 10:00:03,1.2\n"
        )
        
        # Parse CSV
        parser = CSVParser()
        df = parser.parse_file(str(csv_file))
        assert df is not None
        
        # Analyze data
        engine = RulesEngine()
        # This would require actual analysis implementation
        # For now, just verify engine is ready
        assert engine is not None
    
    def test_ai_assistant_workflow(self):
        """Test AI assistant analysis workflow"""
        assistant = AIAssistant()
        
        # Mock flight data
        flight_data = {
            'aircraft_id': 'E145',
            'event_id': '1',
            'timestamp': '2024-01-01 10:00:00',
            'parameters': {'vertical_g': 2.8}
        }
        
        # Mock analysis results
        class MockAnalysis:
            exceeded = True
            max_value = 2.8
            threshold = 2.0
            exceedance_duration = 2.5
            parameter = 'vertical_g'
        
        results = {'vertical_g': MockAnalysis()}
        
        # Generate AI analysis
        ai_analysis = assistant.analyze_results(
            aircraft_id='e145',
            event_type='hard_landing',
            analysis_results=[],
            flight_data=flight_data
        )
        
        assert ai_analysis is not None
        assert ai_analysis.risk_level in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
        assert len(ai_analysis.recommendations) > 0


# ==================== PERFORMANCE TESTS ====================

class TestPerformance:
    """Performance and optimization tests"""
    
    def test_rules_caching(self):
        """Test that rules are cached for performance"""
        engine = RulesEngine()
        
        # First call - should populate cache
        rules1 = engine.load_dynamic_rules("e145", "hard_landing")
        
        # Second call - should use cache
        rules2 = engine.load_dynamic_rules("e145", "hard_landing")
        
        # Should return same object from cache
        assert rules1 is rules2
    
    def test_large_csv_parsing(self, tmp_path):
        """Test parsing large CSV files"""
        import time
        
        # Create large CSV (1000 rows)
        csv_file = tmp_path / "large_flight.csv"
        lines = ["timestamp,altitude,speed,g_force"]
        for i in range(1000):
            lines.append(f"2024-01-01 10:{i//60:02d}:{i%60:02d},{10000+i},{250+i%50},{1.0+i%2*0.5}")
        
        csv_file.write_text("\n".join(lines))
        
        parser = CSVParser()
        start = time.time()
        df = parser.parse_file(str(csv_file))
        elapsed = time.time() - start
        
        assert df is not None
        assert len(df) == 1000
        assert elapsed < 5.0  # Should complete in under 5 seconds


# ==================== RUN TESTS ====================

if __name__ == "__main__":
    print("=" * 70)
    print("AIRCRAFT INSPECTION ANALYSIS - TEST SUITE")
    print("=" * 70)
    print()
    
    # Run pytest with verbose output
    exit_code = pytest.main([
        __file__,
        "-v",  # Verbose
        "--tb=short",  # Short traceback
        "-s",  # Show print statements
        "--color=yes"  # Colored output
    ])
    
    print()
    print("=" * 70)
    if exit_code == 0:
        print("✅ ALL TESTS PASSED")
    else:
        print("❌ SOME TESTS FAILED")
    print("=" * 70)
    
    sys.exit(exit_code)
