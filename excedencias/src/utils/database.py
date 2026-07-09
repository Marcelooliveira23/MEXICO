"""
Database Management Module - SQLite Integration
Handles persistent storage of flight analyses, audit trails, and fleet statistics
"""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass, asdict
import json
from contextlib import contextmanager

from utils.logger import logger


@dataclass
class FlightRecord:
    """Estrutura de um registro de voo"""
    id: Optional[int]
    tail_number: str
    aircraft_model: str
    event_type: str
    timestamp: str
    latitude: Optional[float]
    longitude: Optional[float]
    altitude_at_event: Optional[float]
    flight_phase: str
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    is_confirmed: bool
    created_at: str


@dataclass
class AnalysisRecord:
    """Estrutura de um registro de análise"""
    id: Optional[int]
    flight_id: int
    event_type: str
    parameter_name: str
    measured_value: float
    threshold_value: float
    status: str  # OK, WARNING, VIOLATION
    severity: str
    explanation: str
    recommendations: str
    created_at: str


@dataclass
class AuditTrail:
    """Registro de auditoria"""
    id: Optional[int]
    action: str
    user: str
    timestamp: str
    flight_id: Optional[int]
    details: str
    status: str  # SUCCESS, ERROR


class DatabaseManager:
    """
    Gerenciador de banco de dados SQLite para análises de voo
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """
        Inicializar gerenciador de banco de dados
        
        Args:
            db_path: Caminho para arquivo SQLite (default: data/inspections.db)
        """
        if db_path is None:
            from utils.config import AppConfig
            db_path = AppConfig.DATA_DIR / "inspections.db"
        
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Criar banco de dados e tabelas se não existirem
        self._init_database()
        logger.info(f"DatabaseManager initialized: {self.db_path}")
    
    @contextmanager
    def get_connection(self):
        """Context manager para conexão com banco de dados"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def _init_database(self):
        """Criar tabelas se não existirem"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabela de voos
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS flights (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tail_number TEXT NOT NULL,
                    aircraft_model TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    altitude_at_event REAL,
                    flight_phase TEXT,
                    severity TEXT,
                    is_confirmed BOOLEAN DEFAULT 0,
                    created_at TEXT NOT NULL,
                    UNIQUE(tail_number, timestamp, event_type)
                )
            """)
            
            # Tabela de análises
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    flight_id INTEGER NOT NULL,
                    event_type TEXT NOT NULL,
                    parameter_name TEXT NOT NULL,
                    measured_value REAL NOT NULL,
                    threshold_value REAL NOT NULL,
                    status TEXT,
                    severity TEXT,
                    explanation TEXT,
                    recommendations TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (flight_id) REFERENCES flights(id)
                )
            """)
            
            # Tabela de auditoria
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_trail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    user TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    flight_id INTEGER,
                    details TEXT,
                    status TEXT,
                    FOREIGN KEY (flight_id) REFERENCES flights(id)
                )
            """)
            
            # Tabela de estatísticas de frota
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS fleet_statistics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    aircraft_model TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    total_events INTEGER DEFAULT 0,
                    critical_events INTEGER DEFAULT 0,
                    high_events INTEGER DEFAULT 0,
                    medium_events INTEGER DEFAULT 0,
                    low_events INTEGER DEFAULT 0,
                    last_updated TEXT NOT NULL,
                    UNIQUE(aircraft_model, event_type)
                )
            """)
            
            # Índices para melhor performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_flights_tail ON flights(tail_number)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_flights_model ON flights(aircraft_model)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_flights_event ON flights(event_type)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_flights_timestamp ON flights(timestamp)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_analyses_flight ON analyses(flight_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_audit_flight ON audit_trail(flight_id)")
            
            conn.commit()
            logger.info("Database tables initialized")
    
    # ==================== FLIGHT OPERATIONS ====================
    
    def add_flight(self, flight: FlightRecord) -> int:
        """
        Adicionar um novo voo ao banco de dados
        
        Args:
            flight: Registro do voo
            
        Returns:
            ID do voo inserido
        """
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO flights (
                    tail_number, aircraft_model, event_type, timestamp,
                    latitude, longitude, altitude_at_event, flight_phase,
                    severity, is_confirmed, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                flight.tail_number, flight.aircraft_model, flight.event_type,
                flight.timestamp, flight.latitude, flight.longitude,
                flight.altitude_at_event, flight.flight_phase,
                flight.severity, flight.is_confirmed, flight.created_at
            ))
            
            flight_id = cursor.lastrowid
            logger.info(f"Flight added: {flight_id} ({flight.tail_number})")
            return flight_id
    
    def get_flight(self, flight_id: int) -> Optional[FlightRecord]:
        """Obter registro de um voo"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM flights WHERE id = ?", (flight_id,))
            row = cursor.fetchone()
            
            if row:
                return FlightRecord(**dict(row))
            return None
    
    def get_flights_by_aircraft(self, aircraft_model: str, limit: int = 100) -> List[FlightRecord]:
        """Obter voos de uma aeronave específica"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM flights 
                WHERE aircraft_model = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (aircraft_model, limit))
            
            return [FlightRecord(**dict(row)) for row in cursor.fetchall()]
    
    def get_flights_by_tail(self, tail_number: str, limit: int = 100) -> List[FlightRecord]:
        """Obter voos de uma cauda específica"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM flights 
                WHERE tail_number = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (tail_number, limit))
            
            return [FlightRecord(**dict(row)) for row in cursor.fetchall()]
    
    def get_flights_by_event(self, event_type: str, limit: int = 100) -> List[FlightRecord]:
        """Obter voos com um tipo de evento específico"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM flights 
                WHERE event_type = ? 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (event_type, limit))
            
            return [FlightRecord(**dict(row)) for row in cursor.fetchall()]
    
    def get_critical_flights(self, limit: int = 50) -> List[FlightRecord]:
        """Obter voos com eventos críticos"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM flights 
                WHERE severity = 'CRITICAL' 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            return [FlightRecord(**dict(row)) for row in cursor.fetchall()]
    
    def update_flight_confirmation(self, flight_id: int, is_confirmed: bool):
        """Atualizar status de confirmação de um voo"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE flights 
                SET is_confirmed = ? 
                WHERE id = ?
            """, (is_confirmed, flight_id))
            
            # Log audit na mesma transação
            cursor.execute("""
                INSERT INTO audit_trail 
                (action, user, timestamp, flight_id, details, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                "confirm_flight" if is_confirmed else "unconfirm_flight",
                "system",
                datetime.now().isoformat(),
                flight_id,
                "",
                "SUCCESS"
            ))
    
    # ==================== ANALYSIS OPERATIONS ====================
    
    def add_analysis(self, analysis: AnalysisRecord) -> int:
        """Adicionar resultado de análise"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO analyses (
                    flight_id, event_type, parameter_name, measured_value,
                    threshold_value, status, severity, explanation,
                    recommendations, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                analysis.flight_id, analysis.event_type, analysis.parameter_name,
                analysis.measured_value, analysis.threshold_value,
                analysis.status, analysis.severity, analysis.explanation,
                analysis.recommendations, analysis.created_at
            ))
            
            return cursor.lastrowid
    
    def get_analyses_by_flight(self, flight_id: int) -> List[AnalysisRecord]:
        """Obter análises de um voo específico"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM analyses 
                WHERE flight_id = ? 
                ORDER BY created_at DESC
            """, (flight_id,))
            
            return [AnalysisRecord(**dict(row)) for row in cursor.fetchall()]
    
    def get_violation_analyses(self, limit: int = 100) -> List[Tuple[FlightRecord, AnalysisRecord]]:
        """Obter análises com violações"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT f.*, a.* 
                FROM flights f 
                JOIN analyses a ON f.id = a.flight_id 
                WHERE a.status = 'VIOLATION' 
                ORDER BY f.timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            results = []
            for row in cursor.fetchall():
                # Dividir resultado em duas estruturas
                flight_data = {k: row[k] for k in row.keys() if k in FlightRecord.__dataclass_fields__}
                analysis_data = {k: row[k] for k in row.keys() if k in AnalysisRecord.__dataclass_fields__}
                results.append((FlightRecord(**flight_data), AnalysisRecord(**analysis_data)))
            
            return results
    
    # ==================== FLEET STATISTICS ====================
    
    def update_fleet_statistics(self):
        """Atualizar estatísticas de frota"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Obter combinações únicas de modelo e tipo de evento
            cursor.execute("""
                SELECT DISTINCT aircraft_model, event_type 
                FROM flights
            """)
            
            for row in cursor.fetchall():
                model, event_type = row
                
                # Contar eventos por severidade
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN severity = 'CRITICAL' THEN 1 ELSE 0 END) as critical,
                        SUM(CASE WHEN severity = 'HIGH' THEN 1 ELSE 0 END) as high,
                        SUM(CASE WHEN severity = 'MEDIUM' THEN 1 ELSE 0 END) as medium,
                        SUM(CASE WHEN severity = 'LOW' THEN 1 ELSE 0 END) as low
                    FROM flights
                    WHERE aircraft_model = ? AND event_type = ?
                """, (model, event_type))
                
                stats = cursor.fetchone()
                
                # Upsert nas estatísticas
                cursor.execute("""
                    INSERT OR REPLACE INTO fleet_statistics 
                    (aircraft_model, event_type, total_events, critical_events,
                     high_events, medium_events, low_events, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    model, event_type,
                    stats[0] or 0, stats[1] or 0, stats[2] or 0,
                    stats[3] or 0, stats[4] or 0,
                    datetime.now().isoformat()
                ))
            
            conn.commit()
            logger.info("Fleet statistics updated")
    
    def get_fleet_statistics(self, aircraft_model: Optional[str] = None) -> Dict[str, Any]:
        """Obter estatísticas de frota"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if aircraft_model:
                cursor.execute("""
                    SELECT * FROM fleet_statistics 
                    WHERE aircraft_model = ?
                    ORDER BY event_type
                """, (aircraft_model,))
            else:
                cursor.execute("""
                    SELECT * FROM fleet_statistics 
                    ORDER BY aircraft_model, event_type
                """)
            
            stats = {}
            for row in cursor.fetchall():
                key = f"{row['aircraft_model']}_{row['event_type']}"
                stats[key] = {
                    'model': row['aircraft_model'],
                    'event_type': row['event_type'],
                    'total': row['total_events'],
                    'critical': row['critical_events'],
                    'high': row['high_events'],
                    'medium': row['medium_events'],
                    'low': row['low_events']
                }
            
            return stats
    
    # ==================== AUDIT TRAIL ====================
    
    def log_audit(self, action: str, user: str = "system", flight_id: Optional[int] = None, 
                  details: str = "", status: str = "SUCCESS"):
        """Registrar ação de auditoria"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO audit_trail 
                (action, user, timestamp, flight_id, details, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (action, user, datetime.now().isoformat(), flight_id, details, status))
            
            conn.commit()
    
    def get_audit_trail(self, flight_id: Optional[int] = None, limit: int = 100) -> List[AuditTrail]:
        """Obter histórico de auditoria"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            if flight_id:
                cursor.execute("""
                    SELECT * FROM audit_trail 
                    WHERE flight_id = ? 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (flight_id, limit))
            else:
                cursor.execute("""
                    SELECT * FROM audit_trail 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))
            
            return [AuditTrail(**dict(row)) for row in cursor.fetchall()]
    
    # ==================== REPORTING ====================
    
    def get_summary_report(self) -> Dict[str, Any]:
        """Gerar relatório resumido"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Total de voos
            cursor.execute("SELECT COUNT(*) FROM flights")
            total_flights = cursor.fetchone()[0]
            
            # Voos críticos
            cursor.execute("SELECT COUNT(*) FROM flights WHERE severity = 'CRITICAL'")
            critical_flights = cursor.fetchone()[0]
            
            # Análises
            cursor.execute("SELECT COUNT(*) FROM analyses")
            total_analyses = cursor.fetchone()[0]
            
            # Violações
            cursor.execute("SELECT COUNT(*) FROM analyses WHERE status = 'VIOLATION'")
            violation_analyses = cursor.fetchone()[0]
            
            # Modelos mais afetados
            cursor.execute("""
                SELECT aircraft_model, COUNT(*) as count 
                FROM flights 
                GROUP BY aircraft_model 
                ORDER BY count DESC 
                LIMIT 5
            """)
            top_models = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Eventos mais frequentes
            cursor.execute("""
                SELECT event_type, COUNT(*) as count 
                FROM flights 
                GROUP BY event_type 
                ORDER BY count DESC
            """)
            top_events = {row[0]: row[1] for row in cursor.fetchall()}
            
            return {
                'total_flights': total_flights,
                'critical_flights': critical_flights,
                'total_analyses': total_analyses,
                'violation_analyses': violation_analyses,
                'top_models': top_models,
                'top_events': top_events,
                'generated_at': datetime.now().isoformat()
            }
    
    def export_data(self, output_path: Path):
        """Exportar dados para JSON"""
        report = self.get_summary_report()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Data exported to {output_path}")
    
    def backup_database(self, backup_path: Optional[Path] = None):
        """Fazer backup do banco de dados"""
        if backup_path is None:
            backup_path = self.db_path.parent / f"inspections_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        
        import shutil
        shutil.copy(self.db_path, backup_path)
        logger.info(f"Database backed up to {backup_path}")
        return backup_path
    
    def cleanup_old_records(self, days: int = 365):
        """Remover registros antigos (mais de X dias)"""
        from datetime import timedelta
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Encontrar voos a remover
            cursor.execute("""
                SELECT id FROM flights WHERE created_at < ?
            """, (cutoff_date,))
            
            old_flight_ids = [row[0] for row in cursor.fetchall()]
            
            # Remover análises relacionadas
            for flight_id in old_flight_ids:
                cursor.execute("DELETE FROM analyses WHERE flight_id = ?", (flight_id,))
            
            # Remover voos
            cursor.execute("DELETE FROM flights WHERE created_at < ?", (cutoff_date,))
            
            conn.commit()
            logger.info(f"Cleaned up {len(old_flight_ids)} old records")
