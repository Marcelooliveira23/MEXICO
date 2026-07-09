"""
Alert Manager
Sistema de alertas com notificações visuais e sonoras
"""

from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json

from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from PyQt6.QtWidgets import QMessageBox, QSystemTrayIcon, QApplication
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtCore import QUrl

from utils.logger import logger


class AlertLevel(Enum):
    """Níveis de alerta"""
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


@dataclass
class Alert:
    """Estrutura de alerta"""
    id: str
    level: AlertLevel
    title: str
    message: str
    timestamp: datetime
    flight_id: Optional[int] = None
    aircraft_model: Optional[str] = None
    event_type: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None


class AlertManager(QObject):
    """
    Gerenciador de alertas com notificações
    Integra com sistema operacional e UI
    """
    
    # Sinais PyQt
    new_alert = pyqtSignal(object)  # Emitido quando novo alerta é criado
    alert_acknowledged = pyqtSignal(str)  # Emitido quando alerta é confirmado
    alerts_cleared = pyqtSignal()  # Emitido quando alertas são limpos
    
    def __init__(self, parent=None):
        """Inicializar Alert Manager"""
        super().__init__(parent)
        
        self.alerts: List[Alert] = []
        self.alert_callbacks: Dict[AlertLevel, List[Callable]] = {
            level: [] for level in AlertLevel
        }
        
        # Configurações
        self.max_alerts = 1000  # Máximo de alertas em memória
        self.auto_clear_days = 7  # Limpar alertas antigos automaticamente
        self.sound_enabled = True
        self.desktop_notifications = True

        self.ui_enabled = QApplication.instance() is not None
        
        # Estatísticas
        self.total_alerts = 0
        self.alerts_by_level = {level: 0 for level in AlertLevel}
        
        # Timer para limpeza automática
        self.cleanup_timer = None
        if self.ui_enabled:
            self.cleanup_timer = QTimer()
            self.cleanup_timer.timeout.connect(self._auto_cleanup)
            self.cleanup_timer.start(3600000)  # A cada 1 hora
        
        # Sound effects (opcional)
        self.sounds: Dict[AlertLevel, Optional[QSoundEffect]] = {
            level: None for level in AlertLevel
        }
        
        logger.info("AlertManager initialized")
    
    def create_alert(self, level: AlertLevel, title: str, message: str,
                    flight_id: Optional[int] = None,
                    aircraft_model: Optional[str] = None,
                    event_type: Optional[str] = None,
                    details: Optional[Dict[str, Any]] = None) -> Alert:
        """
        Criar novo alerta
        
        Args:
            level: Nível do alerta
            title: Título
            message: Mensagem
            flight_id: ID do voo (opcional)
            aircraft_model: Modelo da aeronave (opcional)
            event_type: Tipo de evento (opcional)
            details: Detalhes adicionais (opcional)
            
        Returns:
            Alerta criado
        """
        # Gerar ID único
        alert_id = f"alert_{datetime.now().strftime('%Y%m%d%H%M%S%f')}"
        
        # Criar alerta
        alert = Alert(
            id=alert_id,
            level=level,
            title=title,
            message=message,
            timestamp=datetime.now(),
            flight_id=flight_id,
            aircraft_model=aircraft_model,
            event_type=event_type,
            details=details
        )
        
        # Adicionar à lista
        self.alerts.append(alert)
        
        # Atualizar estatísticas
        self.total_alerts += 1
        self.alerts_by_level[level] += 1
        
        # Limitar tamanho da lista
        if len(self.alerts) > self.max_alerts:
            self.alerts.pop(0)  # Remove mais antigo
        
        # Log
        logger.info(f"Alert created: [{level.value}] {title}")
        
        # Emitir sinal
        self.new_alert.emit(alert)
        
        # Executar callbacks registrados
        for callback in self.alert_callbacks.get(level, []):
            try:
                callback(alert)
            except Exception as e:
                logger.error(f"Error in alert callback: {e}")
        
        # Notificações
        self._show_notification(alert)
        self._play_sound(alert)
        
        return alert
    
    def acknowledge_alert(self, alert_id: str, user: str = "system"):
        """
        Confirmar alerta
        
        Args:
            alert_id: ID do alerta
            user: Usuário que confirmou
        """
        for alert in self.alerts:
            if alert.id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_at = datetime.now()
                alert.acknowledged_by = user
                
                logger.info(f"Alert acknowledged: {alert_id} by {user}")
                self.alert_acknowledged.emit(alert_id)
                return
        
        logger.warning(f"Alert not found: {alert_id}")
    
    def get_active_alerts(self, level: Optional[AlertLevel] = None) -> List[Alert]:
        """
        Obter alertas ativos (não confirmados)
        
        Args:
            level: Filtrar por nível (opcional)
            
        Returns:
            Lista de alertas ativos
        """
        active = [a for a in self.alerts if not a.acknowledged]
        
        if level:
            active = [a for a in active if a.level == level]
        
        return sorted(active, key=lambda a: a.timestamp, reverse=True)
    
    def get_all_alerts(self, level: Optional[AlertLevel] = None,
                      limit: int = 100) -> List[Alert]:
        """
        Obter todos os alertas
        
        Args:
            level: Filtrar por nível (opcional)
            limit: Limite de resultados
            
        Returns:
            Lista de alertas
        """
        alerts = self.alerts
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        # Ordenar por timestamp (mais recente primeiro)
        alerts = sorted(alerts, key=lambda a: a.timestamp, reverse=True)
        
        return alerts[:limit]
    
    def clear_acknowledged(self):
        """Limpar alertas confirmados"""
        before_count = len(self.alerts)
        self.alerts = [a for a in self.alerts if not a.acknowledged]
        after_count = len(self.alerts)
        
        cleared = before_count - after_count
        logger.info(f"Cleared {cleared} acknowledged alerts")
        
        if cleared > 0:
            self.alerts_cleared.emit()
    
    def clear_all(self):
        """Limpar todos os alertas"""
        count = len(self.alerts)
        self.alerts.clear()
        
        logger.info(f"Cleared all {count} alerts")
        self.alerts_cleared.emit()
    
    def _auto_cleanup(self):
        """Limpeza automática de alertas antigos"""
        cutoff = datetime.now() - timedelta(days=self.auto_clear_days)
        before_count = len(self.alerts)
        
        self.alerts = [
            a for a in self.alerts
            if a.timestamp > cutoff or not a.acknowledged
        ]
        
        after_count = len(self.alerts)
        if after_count < before_count:
            logger.info(f"Auto-cleanup removed {before_count - after_count} old alerts")
    
    def _show_notification(self, alert: Alert):
        """Mostrar notificação no desktop"""
        if not self.desktop_notifications or not self.ui_enabled:
            return
        
        # Só notificar para alertas críticos e high
        if alert.level not in [AlertLevel.CRITICAL, AlertLevel.HIGH]:
            return
        
        try:
            # Criar QMessageBox para alertas críticos
            if alert.level == AlertLevel.CRITICAL:
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Icon.Critical)
                msg.setWindowTitle(f"🚨 {alert.title}")
                msg.setText(alert.message)
                
                if alert.details:
                    details_text = json.dumps(alert.details, indent=2)
                    msg.setDetailedText(details_text)
                
                msg.setStandardButtons(QMessageBox.StandardButton.Ok)
                
                # Mostrar de forma não-bloqueante
                msg.show()
        
        except Exception as e:
            logger.error(f"Error showing notification: {e}")
    
    def _play_sound(self, alert: Alert):
        """Reproduzir som do alerta"""
        if not self.sound_enabled or not self.ui_enabled:
            return
        
        # Só tocar som para alertas críticos
        if alert.level != AlertLevel.CRITICAL:
            return
        
        try:
            sound = self.sounds.get(alert.level)
            if sound and sound.isLoaded():
                sound.play()
        
        except Exception as e:
            logger.error(f"Error playing alert sound: {e}")
    
    def register_callback(self, level: AlertLevel, callback: Callable):
        """
        Registrar callback para tipo de alerta
        
        Args:
            level: Nível do alerta
            callback: Função callback que recebe Alert
        """
        self.alert_callbacks[level].append(callback)
        logger.debug(f"Callback registered for {level.value} alerts")
    
    def set_sound_file(self, level: AlertLevel, file_path: str):
        """
        Configurar arquivo de som para nível de alerta
        
        Args:
            level: Nível do alerta
            file_path: Caminho do arquivo .wav
        """
        try:
            sound = QSoundEffect()
            sound.setSource(QUrl.fromLocalFile(file_path))
            sound.setVolume(0.5)
            
            self.sounds[level] = sound
            logger.info(f"Sound configured for {level.value}: {file_path}")
        
        except Exception as e:
            logger.error(f"Error setting sound file: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obter estatísticas"""
        active_count = len(self.get_active_alerts())
        
        return {
            "total_alerts": self.total_alerts,
            "current_alerts": len(self.alerts),
            "active_alerts": active_count,
            "acknowledged_alerts": len(self.alerts) - active_count,
            "by_level": {
                level.value: count
                for level, count in self.alerts_by_level.items()
            },
            "settings": {
                "sound_enabled": self.sound_enabled,
                "desktop_notifications": self.desktop_notifications,
                "auto_clear_days": self.auto_clear_days
            }
        }
    
    def export_alerts(self, file_path: str, include_acknowledged: bool = False):
        """
        Exportar alertas para JSON
        
        Args:
            file_path: Caminho do arquivo
            include_acknowledged: Incluir alertas confirmados
        """
        if include_acknowledged:
            alerts_to_export = list(self.alerts)
        else:
            # Preserve insertion order for deterministic exports
            alerts_to_export = [a for a in self.alerts if not a.acknowledged]
        
        data = []
        for alert in alerts_to_export:
            data.append({
                "id": alert.id,
                "level": alert.level.value,
                "title": alert.title,
                "message": alert.message,
                "timestamp": alert.timestamp.isoformat(),
                "flight_id": alert.flight_id,
                "aircraft_model": alert.aircraft_model,
                "event_type": alert.event_type,
                "details": alert.details,
                "acknowledged": alert.acknowledged,
                "acknowledged_at": alert.acknowledged_at.isoformat() if alert.acknowledged_at else None,
                "acknowledged_by": alert.acknowledged_by
            })
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Exported {len(data)} alerts to {file_path}")
        
        except Exception as e:
            logger.error(f"Error exporting alerts: {e}")
            raise


# Singleton instance
_alert_manager_instance: Optional[AlertManager] = None


def get_alert_manager() -> AlertManager:
    """
    Obter instância singleton do Alert Manager
    
    Returns:
        Instância do AlertManager
    """
    global _alert_manager_instance
    
    if _alert_manager_instance is None:
        _alert_manager_instance = AlertManager()
    
    return _alert_manager_instance
