"""
Test suite para o Database Manager
Testa operações CRUD, estatísticas e auditoria
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'src'))

import pytest
from datetime import datetime
from utils.database import DatabaseManager, FlightRecord, AnalysisRecord, AuditTrail


@pytest.fixture
def temp_db():
    """Criar banco de dados temporário para testes"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        manager = DatabaseManager(db_path)
        yield manager


class TestFlightOperations:
    """Testes para operações de voos"""
    
    def test_add_flight(self, temp_db):
        """Testar adição de um voo"""
        flight = FlightRecord(
            id=None,
            tail_number="PT-XYZ",
            aircraft_model="E170",
            event_type="hard_landing",
            timestamp="2024-01-01T10:00:00",
            latitude=-23.5,
            longitude=-46.6,
            altitude_at_event=1000.0,
            flight_phase="LANDING",
            severity="HIGH",
            is_confirmed=False,
            created_at=datetime.now().isoformat()
        )
        
        flight_id = temp_db.add_flight(flight)
        
        assert flight_id is not None
        assert flight_id > 0
    
    def test_get_flight(self, temp_db):
        """Testar recuperação de um voo"""
        flight = FlightRecord(
            id=None,
            tail_number="PT-ABC",
            aircraft_model="E145",
            event_type="gear_overspeed",
            timestamp="2024-01-02T11:00:00",
            latitude=-23.5,
            longitude=-46.6,
            altitude_at_event=2000.0,
            flight_phase="APPROACH",
            severity="MEDIUM",
            is_confirmed=True,
            created_at=datetime.now().isoformat()
        )
        
        flight_id = temp_db.add_flight(flight)
        retrieved = temp_db.get_flight(flight_id)
        
        assert retrieved is not None
        assert retrieved.tail_number == "PT-ABC"
        assert retrieved.aircraft_model == "E145"
    
    def test_get_flights_by_aircraft(self, temp_db):
        """Testar recuperação de voos por modelo"""
        # Adicionar 3 voos do E170
        for i in range(3):
            flight = FlightRecord(
                id=None,
                tail_number=f"PT-{i}",
                aircraft_model="E170",
                event_type="hard_landing",
                timestamp=f"2024-01-{i+1}T10:00:00",
                latitude=-23.5,
                longitude=-46.6,
                altitude_at_event=1000.0,
                flight_phase="LANDING",
                severity="HIGH",
                is_confirmed=False,
                created_at=datetime.now().isoformat()
            )
            temp_db.add_flight(flight)
        
        flights = temp_db.get_flights_by_aircraft("E170")
        
        assert len(flights) == 3
        assert all(f.aircraft_model == "E170" for f in flights)
    
    def test_get_flights_by_tail(self, temp_db):
        """Testar recuperação de voos por cauda"""
        # Adicionar voos da mesma cauda
        for i in range(2):
            flight = FlightRecord(
                id=None,
                tail_number="PT-XYZ",
                aircraft_model="E190",
                event_type=["hard_landing", "temp_envelope"][i],
                timestamp=f"2024-01-{i+1}T10:00:00",
                latitude=-23.5,
                longitude=-46.6,
                altitude_at_event=1000.0,
                flight_phase="LANDING",
                severity="CRITICAL",
                is_confirmed=False,
                created_at=datetime.now().isoformat()
            )
            temp_db.add_flight(flight)
        
        flights = temp_db.get_flights_by_tail("PT-XYZ")
        
        assert len(flights) == 2
        assert all(f.tail_number == "PT-XYZ" for f in flights)
    
    def test_update_flight_confirmation(self, temp_db):
        """Testar atualização de confirmação de voo"""
        flight = FlightRecord(
            id=None,
            tail_number="PT-TEST",
            aircraft_model="E145",
            event_type="hard_landing",
            timestamp="2024-01-01T10:00:00",
            latitude=-23.5,
            longitude=-46.6,
            altitude_at_event=1000.0,
            flight_phase="LANDING",
            severity="HIGH",
            is_confirmed=False,
            created_at=datetime.now().isoformat()
        )
        
        flight_id = temp_db.add_flight(flight)
        temp_db.update_flight_confirmation(flight_id, True)
        
        updated = temp_db.get_flight(flight_id)
        assert updated.is_confirmed == True


class TestAnalysisOperations:
    """Testes para operações de análise"""
    
    def test_add_analysis(self, temp_db):
        """Testar adição de análise"""
        # Primeiro adicionar um voo
        flight = FlightRecord(
            id=None,
            tail_number="PT-001",
            aircraft_model="E170",
            event_type="hard_landing",
            timestamp="2024-01-01T10:00:00",
            latitude=-23.5,
            longitude=-46.6,
            altitude_at_event=1000.0,
            flight_phase="LANDING",
            severity="HIGH",
            is_confirmed=False,
            created_at=datetime.now().isoformat()
        )
        flight_id = temp_db.add_flight(flight)
        
        # Adicionar análise
        analysis = AnalysisRecord(
            id=None,
            flight_id=flight_id,
            event_type="hard_landing",
            parameter_name="vertical_g",
            measured_value=2.8,
            threshold_value=2.0,
            status="VIOLATION",
            severity="HIGH",
            explanation="Exceedance of 40% above threshold",
            recommendations="Inspect landing gear and structure",
            created_at=datetime.now().isoformat()
        )
        
        analysis_id = temp_db.add_analysis(analysis)
        
        assert analysis_id is not None
        assert analysis_id > 0
    
    def test_get_analyses_by_flight(self, temp_db):
        """Testar recuperação de análises por voo"""
        # Adicionar voo
        flight = FlightRecord(
            id=None,
            tail_number="PT-002",
            aircraft_model="E190",
            event_type="hard_landing",
            timestamp="2024-01-01T10:00:00",
            latitude=-23.5,
            longitude=-46.6,
            altitude_at_event=1000.0,
            flight_phase="LANDING",
            severity="CRITICAL",
            is_confirmed=False,
            created_at=datetime.now().isoformat()
        )
        flight_id = temp_db.add_flight(flight)
        
        # Adicionar múltiplas análises
        for i in range(2):
            analysis = AnalysisRecord(
                id=None,
                flight_id=flight_id,
                event_type="hard_landing",
                parameter_name=["vertical_g", "pitch_angle"][i],
                measured_value=[2.8, 15.0][i],
                threshold_value=[2.0, 12.0][i],
                status="VIOLATION",
                severity="HIGH",
                explanation=f"Parameter {i+1} exceeded",
                recommendations="Inspect structure",
                created_at=datetime.now().isoformat()
            )
            temp_db.add_analysis(analysis)
        
        analyses = temp_db.get_analyses_by_flight(flight_id)
        
        assert len(analyses) == 2
        assert all(a.flight_id == flight_id for a in analyses)


class TestFleetStatistics:
    """Testes para estatísticas de frota"""
    
    def test_update_fleet_statistics(self, temp_db):
        """Testar cálculo de estatísticas"""
        # Adicionar voos variados
        for model in ["E145", "E170"]:
            for severity in ["CRITICAL", "HIGH", "MEDIUM"]:
                flight = FlightRecord(
                    id=None,
                    tail_number=f"PT-{model}-{severity}",
                    aircraft_model=model,
                    event_type="hard_landing",
                    timestamp=datetime.now().isoformat(),
                    latitude=-23.5,
                    longitude=-46.6,
                    altitude_at_event=1000.0,
                    flight_phase="LANDING",
                    severity=severity,
                    is_confirmed=False,
                    created_at=datetime.now().isoformat()
                )
                temp_db.add_flight(flight)
        
        # Atualizar estatísticas
        temp_db.update_fleet_statistics()
        
        # Verificar estatísticas
        stats = temp_db.get_fleet_statistics("E145")
        
        assert len(stats) > 0
        assert any("E145" in key for key in stats.keys())


class TestAuditTrail:
    """Testes para auditoria"""
    
    def test_log_audit(self, temp_db):
        """Testar registro de auditoria"""
        temp_db.log_audit(
            action="test_action",
            user="test_user",
            details="Test details"
        )
        
        trail = temp_db.get_audit_trail()
        
        assert len(trail) > 0
        assert trail[0].action == "test_action"
        assert trail[0].user == "test_user"
    
    def test_get_audit_trail_by_flight(self, temp_db):
        """Testar obtenção de auditoria por voo"""
        # Adicionar voo
        flight = FlightRecord(
            id=None,
            tail_number="PT-AUDIT",
            aircraft_model="E170",
            event_type="hard_landing",
            timestamp="2024-01-01T10:00:00",
            latitude=-23.5,
            longitude=-46.6,
            altitude_at_event=1000.0,
            flight_phase="LANDING",
            severity="HIGH",
            is_confirmed=False,
            created_at=datetime.now().isoformat()
        )
        flight_id = temp_db.add_flight(flight)
        
        # Log múltiplas ações
        temp_db.log_audit("action1", flight_id=flight_id)
        temp_db.log_audit("action2", flight_id=flight_id)
        
        trail = temp_db.get_audit_trail(flight_id)
        
        assert len(trail) == 2
        assert all(t.flight_id == flight_id for t in trail)


class TestSummaryReport:
    """Testes para relatórios"""
    
    def test_get_summary_report(self, temp_db):
        """Testar geração de relatório resumido"""
        # Adicionar alguns voos
        for i in range(3):
            flight = FlightRecord(
                id=None,
                tail_number=f"PT-{i}",
                aircraft_model="E170",
                event_type="hard_landing",
                timestamp=f"2024-01-{i+1}T10:00:00",
                latitude=-23.5,
                longitude=-46.6,
                altitude_at_event=1000.0,
                flight_phase="LANDING",
                severity="CRITICAL" if i == 0 else "HIGH",
                is_confirmed=False,
                created_at=datetime.now().isoformat()
            )
            temp_db.add_flight(flight)
        
        report = temp_db.get_summary_report()
        
        assert report['total_flights'] == 3
        assert report['critical_flights'] == 1
        assert 'top_models' in report
        assert 'top_events' in report


class TestDataBackup:
    """Testes para backup de dados"""
    
    def test_backup_database(self, temp_db):
        """Testar backup do banco de dados"""
        # Adicionar um voo
        flight = FlightRecord(
            id=None,
            tail_number="PT-BACKUP",
            aircraft_model="E145",
            event_type="hard_landing",
            timestamp="2024-01-01T10:00:00",
            latitude=-23.5,
            longitude=-46.6,
            altitude_at_event=1000.0,
            flight_phase="LANDING",
            severity="HIGH",
            is_confirmed=False,
            created_at=datetime.now().isoformat()
        )
        temp_db.add_flight(flight)
        
        # Fazer backup
        backup_path = temp_db.backup_database()
        
        assert backup_path.exists()
        assert backup_path != temp_db.db_path


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
