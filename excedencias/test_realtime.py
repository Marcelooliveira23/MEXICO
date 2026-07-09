"""
Testes para Phase 9: Real-time Monitoring
Cobertura completa para WebSocket, Pipeline, AlertManager e Dashboard
"""

import pytest
import asyncio
import json
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from services.websocket_server import WebSocketServer, WebSocketMessage, get_websocket_server
from services.realtime_pipeline import RealtimePipeline, Priority, AnalysisTask, get_realtime_pipeline
from services.alert_manager import AlertManager, AlertLevel, Alert, get_alert_manager


class TestWebSocketServer:
    """Testes para WebSocketServer"""
    
    @pytest.fixture
    def server(self):
        """Fixture para servidor"""
        return WebSocketServer(host="localhost", port=8766)
    
    def test_server_initialization(self, server):
        """Testar inicialização do servidor"""
        assert server.host == "localhost"
        assert server.port == 8766
        assert server.running == False
        assert len(server.clients) == 0
        assert server.total_messages_sent == 0
        assert server.total_clients_served == 0
    
    def test_message_creation(self):
        """Testar criação de mensagem"""
        msg = WebSocketMessage(
            type="test",
            timestamp=datetime.now().isoformat(),
            data={"key": "value"},
            priority="HIGH"
        )
        
        assert msg.type == "test"
        assert msg.priority == "HIGH"
        assert msg.data["key"] == "value"
    
    @pytest.mark.asyncio
    async def test_broadcast_no_clients(self, server):
        """Testar broadcast sem clientes"""
        msg = WebSocketMessage(
            type="test",
            timestamp=datetime.now().isoformat(),
            data={"test": True}
        )
        
        # Não deve dar erro
        await server.broadcast(msg)
        assert server.total_messages_sent == 0
    
    @pytest.mark.asyncio
    async def test_broadcast_analysis_result(self, server):
        """Testar broadcast de resultado de análise"""
        # Mock de cliente
        mock_client = MagicMock()
        server.clients.add(mock_client)
        
        await server.broadcast_analysis_result(
            flight_id=123,
            aircraft_model="E170",
            event_type="hard_landing",
            severity="CRITICAL",
            results={"test": True}
        )
        
        # Verificar que send foi chamado
        assert mock_client.send.called
        assert server.total_messages_sent > 0
    
    @pytest.mark.asyncio
    async def test_broadcast_alert(self, server):
        """Testar broadcast de alerta"""
        mock_client = MagicMock()
        server.clients.add(mock_client)
        
        await server.broadcast_alert(
            alert_type="critical_event",
            severity="CRITICAL",
            message_text="Test alert",
            details={"key": "value"}
        )
        
        assert mock_client.send.called
    
    def test_get_stats(self, server):
        """Testar obtenção de estatísticas"""
        stats = server.get_stats()
        
        assert "active_connections" in stats
        assert "total_clients_served" in stats
        assert "total_messages_sent" in stats
        assert "running" in stats
        assert stats["host"] == "localhost"
        assert stats["port"] == 8766
    
    def test_singleton_pattern(self):
        """Testar padrão singleton"""
        server1 = get_websocket_server()
        server2 = get_websocket_server()
        
        assert server1 is server2


class TestRealtimePipeline:
    """Testes para RealtimePipeline"""
    
    @pytest.fixture
    def pipeline(self):
        """Fixture para pipeline"""
        return RealtimePipeline(max_workers=2)
    
    def test_pipeline_initialization(self, pipeline):
        """Testar inicialização do pipeline"""
        assert pipeline.max_workers == 2
        assert pipeline.running == False
        assert pipeline.total_processed == 0
        assert pipeline.task_queue.qsize() == 0
    
    def test_submit_analysis(self, pipeline):
        """Testar submissão de análise"""
        result = pipeline.submit_analysis(
            flight_id=101,
            aircraft_model="E190",
            event_type="hard_landing",
            data={"test": True},
            priority=Priority.HIGH
        )
        
        assert result == True
        assert pipeline.task_queue.qsize() == 1
    
    def test_submit_multiple_analyses(self, pipeline):
        """Testar submissão de múltiplas análises"""
        for i in range(5):
            pipeline.submit_analysis(
                flight_id=100 + i,
                aircraft_model="E170",
                event_type="max_speed",
                data={},
                priority=Priority.NORMAL
            )
        
        assert pipeline.task_queue.qsize() == 5
    
    def test_determine_priority_critical(self, pipeline):
        """Testar determinação de prioridade crítica"""
        priority = pipeline.determine_priority("CRITICAL", "hard_landing")
        assert priority == Priority.CRITICAL
    
    def test_determine_priority_high_event(self, pipeline):
        """Testar prioridade alta para eventos críticos"""
        priority = pipeline.determine_priority("MEDIUM", "hard_landing")
        assert priority == Priority.HIGH  # Upgrade devido ao evento crítico
    
    def test_determine_priority_normal(self, pipeline):
        """Testar determinação de prioridade normal"""
        priority = pipeline.determine_priority("MEDIUM", "max_speed")
        assert priority == Priority.NORMAL
    
    @pytest.mark.asyncio
    async def test_process_task(self, pipeline):
        """Testar processamento de task"""
        task = AnalysisTask(
            priority=Priority.NORMAL.value,
            timestamp=datetime.now().isoformat(),
            flight_id=201,
            aircraft_model="E195",
            event_type="gear_overspeed",
            data={"parameters": {}}
        )
        
        # Mock do WebSocket e Database
        with patch.object(pipeline, 'ws_server') as mock_ws, \
             patch.object(pipeline, 'db') as mock_db:
            
            mock_ws.broadcast_analysis_result = AsyncMock()
            mock_db.add_analysis = Mock()
            
            await pipeline.process_task(task)
            
            assert pipeline.total_processed == 1
            assert mock_ws.broadcast_analysis_result.called
    
    def test_get_queue_size(self, pipeline):
        """Testar obtenção do tamanho da queue"""
        assert pipeline.get_queue_size() == 0
        
        pipeline.submit_analysis(
            flight_id=999,
            aircraft_model="E2",
            event_type="hard_landing",
            data={}
        )
        
        assert pipeline.get_queue_size() == 1
    
    def test_get_stats(self, pipeline):
        """Testar obtenção de estatísticas"""
        # Submeter algumas tasks
        pipeline.submit_analysis(101, "E170", "hard_landing", {}, Priority.CRITICAL)
        pipeline.submit_analysis(102, "E190", "max_speed", {}, Priority.NORMAL)
        
        stats = pipeline.get_stats()
        
        assert "running" in stats
        assert "workers" in stats
        assert "queue_size" in stats
        assert "total_processed" in stats
        assert "by_priority" in stats
        assert stats["workers"] == 2
        assert stats["queue_size"] == 2
    
    def test_singleton_pattern(self):
        """Testar padrão singleton"""
        pipeline1 = get_realtime_pipeline()
        pipeline2 = get_realtime_pipeline()
        
        assert pipeline1 is pipeline2


class TestAlertManager:
    """Testes para AlertManager"""
    
    @pytest.fixture
    def alert_manager(self):
        """Fixture para alert manager"""
        # Criar sem QApplication para testes simples
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            manager = AlertManager()
        return manager
    
    def test_alert_manager_initialization(self, alert_manager):
        """Testar inicialização do alert manager"""
        assert len(alert_manager.alerts) == 0
        assert alert_manager.total_alerts == 0
        assert alert_manager.max_alerts == 1000
        assert alert_manager.sound_enabled == True
        assert alert_manager.desktop_notifications == True
    
    def test_create_alert_basic(self, alert_manager):
        """Testar criação de alerta básico"""
        alert = alert_manager.create_alert(
            level=AlertLevel.HIGH,
            title="Test Alert",
            message="This is a test"
        )
        
        assert alert.level == AlertLevel.HIGH
        assert alert.title == "Test Alert"
        assert alert.message == "This is a test"
        assert alert.acknowledged == False
        assert len(alert_manager.alerts) == 1
        assert alert_manager.total_alerts == 1
    
    def test_create_alert_with_details(self, alert_manager):
        """Testar criação de alerta com detalhes"""
        alert = alert_manager.create_alert(
            level=AlertLevel.CRITICAL,
            title="Critical Event",
            message="Emergency",
            flight_id=123,
            aircraft_model="E170",
            event_type="hard_landing",
            details={"key": "value"}
        )
        
        assert alert.flight_id == 123
        assert alert.aircraft_model == "E170"
        assert alert.event_type == "hard_landing"
        assert alert.details["key"] == "value"
    
    def test_create_multiple_alerts(self, alert_manager):
        """Testar criação de múltiplos alertas"""
        for i in range(5):
            alert_manager.create_alert(
                level=AlertLevel.INFO,
                title=f"Alert {i}",
                message=f"Message {i}"
            )
        
        assert len(alert_manager.alerts) == 5
        assert alert_manager.total_alerts == 5
    
    def test_acknowledge_alert(self, alert_manager):
        """Testar confirmação de alerta"""
        alert = alert_manager.create_alert(
            level=AlertLevel.HIGH,
            title="Test",
            message="Test"
        )
        
        alert_manager.acknowledge_alert(alert.id, "test_user")
        
        assert alert.acknowledged == True
        assert alert.acknowledged_by == "test_user"
        assert alert.acknowledged_at is not None
    
    def test_get_active_alerts(self, alert_manager):
        """Testar obtenção de alertas ativos"""
        # Criar 3 alertas
        alert1 = alert_manager.create_alert(AlertLevel.HIGH, "A1", "M1")
        alert2 = alert_manager.create_alert(AlertLevel.HIGH, "A2", "M2")
        alert3 = alert_manager.create_alert(AlertLevel.HIGH, "A3", "M3")
        
        # Confirmar um
        alert_manager.acknowledge_alert(alert2.id)
        
        # Obter ativos
        active = alert_manager.get_active_alerts()
        
        assert len(active) == 2
        assert alert2.id not in [a.id for a in active]
    
    def test_get_active_alerts_by_level(self, alert_manager):
        """Testar filtragem de alertas por nível"""
        alert_manager.create_alert(AlertLevel.CRITICAL, "C1", "M1")
        alert_manager.create_alert(AlertLevel.HIGH, "H1", "M2")
        alert_manager.create_alert(AlertLevel.HIGH, "H2", "M3")
        
        critical_alerts = alert_manager.get_active_alerts(level=AlertLevel.CRITICAL)
        high_alerts = alert_manager.get_active_alerts(level=AlertLevel.HIGH)
        
        assert len(critical_alerts) == 1
        assert len(high_alerts) == 2
    
    def test_clear_acknowledged(self, alert_manager):
        """Testar limpeza de alertas confirmados"""
        # Criar 5 alertas
        for i in range(5):
            alert_manager.create_alert(AlertLevel.INFO, f"A{i}", f"M{i}")
        
        # Confirmar 3
        for alert in alert_manager.alerts[:3]:
            alert_manager.acknowledge_alert(alert.id)
        
        # Limpar confirmados
        alert_manager.clear_acknowledged()
        
        assert len(alert_manager.alerts) == 2
    
    def test_clear_all(self, alert_manager):
        """Testar limpeza de todos os alertas"""
        for i in range(10):
            alert_manager.create_alert(AlertLevel.INFO, f"A{i}", f"M{i}")
        
        alert_manager.clear_all()
        
        assert len(alert_manager.alerts) == 0
    
    def test_get_stats(self, alert_manager):
        """Testar obtenção de estatísticas"""
        # Criar alertas de diferentes níveis
        alert_manager.create_alert(AlertLevel.CRITICAL, "C1", "M1")
        alert_manager.create_alert(AlertLevel.CRITICAL, "C2", "M2")
        alert_manager.create_alert(AlertLevel.HIGH, "H1", "M3")
        alert_manager.create_alert(AlertLevel.INFO, "I1", "M4")
        
        # Confirmar um
        alert_manager.acknowledge_alert(alert_manager.alerts[0].id)
        
        stats = alert_manager.get_stats()
        
        assert stats["total_alerts"] == 4
        assert stats["current_alerts"] == 4
        assert stats["active_alerts"] == 3
        assert stats["acknowledged_alerts"] == 1
        assert stats["by_level"]["CRITICAL"] == 2
        assert stats["by_level"]["HIGH"] == 1
        assert stats["by_level"]["INFO"] == 1
    
    def test_register_callback(self, alert_manager):
        """Testar registro de callback"""
        callback_called = []
        
        def test_callback(alert):
            callback_called.append(alert)
        
        alert_manager.register_callback(AlertLevel.CRITICAL, test_callback)
        
        alert = alert_manager.create_alert(
            AlertLevel.CRITICAL,
            "Test",
            "Test"
        )
        
        assert len(callback_called) == 1
        assert callback_called[0].id == alert.id
    
    def test_max_alerts_limit(self, alert_manager):
        """Testar limite máximo de alertas"""
        alert_manager.max_alerts = 10
        
        # Criar 15 alertas
        for i in range(15):
            alert_manager.create_alert(AlertLevel.INFO, f"A{i}", f"M{i}")
        
        # Deve ter apenas 10 (os mais recentes)
        assert len(alert_manager.alerts) == 10
        assert alert_manager.total_alerts == 15
    
    def test_export_alerts(self, alert_manager, tmp_path):
        """Testar exportação de alertas"""
        # Criar alguns alertas
        for i in range(3):
            alert_manager.create_alert(AlertLevel.HIGH, f"A{i}", f"M{i}")
        
        # Exportar
        export_file = tmp_path / "alerts.json"
        alert_manager.export_alerts(str(export_file))
        
        # Verificar arquivo
        assert export_file.exists()
        
        with open(export_file, 'r') as f:
            data = json.load(f)
        
        assert len(data) == 3
        assert data[0]["title"] == "A0"
    
    def test_singleton_pattern(self):
        """Testar padrão singleton"""
        manager1 = get_alert_manager()
        manager2 = get_alert_manager()
        
        assert manager1 is manager2


# Helper para testes assíncronos
class AsyncMock(MagicMock):
    async def __call__(self, *args, **kwargs):
        return super(AsyncMock, self).__call__(*args, **kwargs)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
