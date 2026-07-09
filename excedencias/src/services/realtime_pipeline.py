"""
Real-time Analysis Pipeline
Processamento assíncrono de análises de voo com queue de prioridade
"""

import asyncio
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from queue import PriorityQueue
from enum import IntEnum
import threading

from utils.logger import logger
from services.websocket_server import get_websocket_server
from utils.database import DatabaseManager


class Priority(IntEnum):
    """Prioridades de processamento"""
    CRITICAL = 1
    HIGH = 2
    NORMAL = 3
    LOW = 4


@dataclass(order=True)
class AnalysisTask:
    """Task de análise com prioridade"""
    priority: int
    timestamp: str = field(compare=False)
    flight_id: int = field(compare=False)
    aircraft_model: str = field(compare=False)
    event_type: str = field(compare=False)
    data: Dict[str, Any] = field(compare=False)
    callback: Optional[Callable] = field(default=None, compare=False)


class RealtimePipeline:
    """
    Pipeline de processamento em tempo real
    Gerencia queue de análises com priorização automática
    """
    
    def __init__(self, max_workers: int = 4):
        """
        Inicializar pipeline
        
        Args:
            max_workers: Número máximo de workers concorrentes
        """
        self.max_workers = max_workers
        self.task_queue: PriorityQueue = PriorityQueue()
        self.running = False
        self.workers: List[asyncio.Task] = []
        
        # Estatísticas
        self.total_processed = 0
        self.total_critical = 0
        self.total_high = 0
        self.total_normal = 0
        self.total_low = 0
        self.processing_times: List[float] = []
        
        # Integração
        self.ws_server = get_websocket_server()
        self.db = DatabaseManager()
        
        logger.info(f"RealtimePipeline initialized with {max_workers} workers")
    
    def submit_analysis(self, flight_id: int, aircraft_model: str,
                       event_type: str, data: Dict[str, Any],
                       priority: Priority = Priority.NORMAL,
                       callback: Optional[Callable] = None) -> bool:
        """
        Submeter análise para processamento
        
        Args:
            flight_id: ID do voo
            aircraft_model: Modelo da aeronave
            event_type: Tipo de evento
            data: Dados da análise
            priority: Prioridade (default: NORMAL)
            callback: Função callback após processamento
            
        Returns:
            True se task foi submetida com sucesso
        """
        task = AnalysisTask(
            priority=priority.value,
            timestamp=datetime.now().isoformat(),
            flight_id=flight_id,
            aircraft_model=aircraft_model,
            event_type=event_type,
            data=data,
            callback=callback
        )
        
        try:
            self.task_queue.put(task)
            logger.debug(f"Task submitted: Flight {flight_id}, Priority {priority.name}")
            return True
        
        except Exception as e:
            logger.error(f"Error submitting task: {e}")
            return False
    
    def determine_priority(self, severity: str, event_type: str) -> Priority:
        """
        Determinar prioridade baseado em severidade e tipo
        
        Args:
            severity: Severidade (CRITICAL, HIGH, MEDIUM, LOW)
            event_type: Tipo de evento
            
        Returns:
            Prioridade calculada
        """
        # Mapear severidade para prioridade
        severity_map = {
            "CRITICAL": Priority.CRITICAL,
            "HIGH": Priority.HIGH,
            "MEDIUM": Priority.NORMAL,
            "LOW": Priority.LOW
        }
        
        base_priority = severity_map.get(severity, Priority.NORMAL)
        
        # Eventos críticos sempre tem alta prioridade
        critical_events = ["hard_landing", "gear_overspeed"]
        if event_type.lower() in critical_events:
            base_priority = min(base_priority, Priority.HIGH)
        
        return base_priority
    
    async def process_task(self, task: AnalysisTask):
        """
        Processar task de análise
        
        Args:
            task: Task para processar
        """
        start_time = asyncio.get_event_loop().time()
        
        try:
            logger.info(f"Processing task: Flight {task.flight_id}, Event {task.event_type}")
            
            # Simular processamento de análise
            # Na implementação real, chamar RulesEngine e AI Assistant aqui
            await asyncio.sleep(0.1)  # Simular trabalho
            
            # Preparar resultados
            results = {
                "flight_id": task.flight_id,
                "aircraft_model": task.aircraft_model,
                "event_type": task.event_type,
                "severity": self._get_severity_from_priority(task.priority),
                "processed_at": datetime.now().isoformat(),
                "parameters": task.data.get("parameters", {}),
                "exceedances_found": task.data.get("exceedances_found", 0),
                "status": "completed"
            }
            
            # Salvar no banco de dados
            try:
                self.db.add_analysis(
                    flight_id=task.flight_id,
                    event_type=task.event_type,
                    parameter=results.get("parameters", {}),
                    threshold_value=0.0,  # Placeholder
                    actual_value=0.0,  # Placeholder
                    severity=results["severity"],
                    timestamp=datetime.now()
                )
            except Exception as e:
                logger.error(f"Error saving to database: {e}")
            
            # Broadcast via WebSocket
            await self.ws_server.broadcast_analysis_result(
                flight_id=task.flight_id,
                aircraft_model=task.aircraft_model,
                event_type=task.event_type,
                severity=results["severity"],
                results=results
            )
            
            # Se é crítico, enviar alerta
            if task.priority == Priority.CRITICAL.value:
                await self.ws_server.broadcast_alert(
                    alert_type="critical_exceedance",
                    severity="CRITICAL",
                    message_text=f"Exceedance crítica detectada no voo {task.flight_id}",
                    details=results
                )
            
            # Executar callback se fornecido
            if task.callback:
                try:
                    if asyncio.iscoroutinefunction(task.callback):
                        await task.callback(results)
                    else:
                        task.callback(results)
                except Exception as e:
                    logger.error(f"Error in callback: {e}")
            
            # Atualizar estatísticas
            self.total_processed += 1
            
            if task.priority == Priority.CRITICAL.value:
                self.total_critical += 1
            elif task.priority == Priority.HIGH.value:
                self.total_high += 1
            elif task.priority == Priority.NORMAL.value:
                self.total_normal += 1
            else:
                self.total_low += 1
            
            # Registrar tempo de processamento
            processing_time = asyncio.get_event_loop().time() - start_time
            self.processing_times.append(processing_time)
            
            # Manter apenas últimos 1000 tempos
            if len(self.processing_times) > 1000:
                self.processing_times.pop(0)
            
            logger.info(f"✅ Task completed: Flight {task.flight_id} in {processing_time:.3f}s")
        
        except Exception as e:
            logger.error(f"Error processing task: {e}")
            
            # Notificar erro
            await self.ws_server.broadcast_alert(
                alert_type="processing_error",
                severity="HIGH",
                message_text=f"Erro ao processar voo {task.flight_id}",
                details={"error": str(e), "flight_id": task.flight_id}
            )
    
    def _get_severity_from_priority(self, priority: int) -> str:
        """Converter prioridade numérica para severidade"""
        priority_map = {
            Priority.CRITICAL.value: "CRITICAL",
            Priority.HIGH.value: "HIGH",
            Priority.NORMAL.value: "MEDIUM",
            Priority.LOW.value: "LOW"
        }
        return priority_map.get(priority, "MEDIUM")
    
    async def worker(self, worker_id: int):
        """
        Worker que processa tasks da queue
        
        Args:
            worker_id: ID do worker
        """
        logger.info(f"Worker {worker_id} started")
        
        while self.running:
            try:
                # Pegar task da queue (com timeout)
                task = await asyncio.get_event_loop().run_in_executor(
                    None, self.task_queue.get, True, 1.0
                )
                
                # Processar task
                await self.process_task(task)
                
                # Marcar como done
                self.task_queue.task_done()
            
            except Exception:
                # Timeout ou queue vazia
                await asyncio.sleep(0.1)
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def start(self):
        """Iniciar pipeline"""
        if self.running:
            logger.warning("Pipeline already running")
            return
        
        self.running = True
        
        # Iniciar workers
        self.workers = [
            asyncio.create_task(self.worker(i))
            for i in range(self.max_workers)
        ]
        
        logger.info(f"✅ RealtimePipeline started with {self.max_workers} workers")
    
    async def stop(self):
        """Parar pipeline"""
        if not self.running:
            logger.warning("Pipeline not running")
            return
        
        logger.info("Stopping RealtimePipeline...")
        
        self.running = False
        
        # Aguardar workers terminarem
        if self.workers:
            await asyncio.gather(*self.workers, return_exceptions=True)
            self.workers.clear()
        
        logger.info("✅ RealtimePipeline stopped")
    
    def get_queue_size(self) -> int:
        """Obter tamanho da queue"""
        return self.task_queue.qsize()
    
    def get_stats(self) -> Dict[str, Any]:
        """Obter estatísticas do pipeline"""
        avg_time = (
            sum(self.processing_times) / len(self.processing_times)
            if self.processing_times else 0.0
        )
        
        return {
            "running": self.running,
            "workers": self.max_workers,
            "queue_size": self.get_queue_size(),
            "total_processed": self.total_processed,
            "by_priority": {
                "critical": self.total_critical,
                "high": self.total_high,
                "normal": self.total_normal,
                "low": self.total_low
            },
            "avg_processing_time_ms": avg_time * 1000,
            "last_100_avg_ms": (
                sum(self.processing_times[-100:]) / min(100, len(self.processing_times)) * 1000
                if self.processing_times else 0.0
            )
        }
    
    def start_background(self):
        """Iniciar pipeline em thread separada"""
        if self.running:
            logger.warning("Pipeline already running")
            return
        
        def run_pipeline():
            asyncio.run(self.start())
        
        thread = threading.Thread(target=run_pipeline, daemon=True)
        thread.start()
        
        logger.info("RealtimePipeline started in background thread")


# Singleton instance
_pipeline_instance: Optional[RealtimePipeline] = None


def get_realtime_pipeline(max_workers: int = 4) -> RealtimePipeline:
    """
    Obter instância singleton do pipeline
    
    Args:
        max_workers: Número de workers (só aplicado na primeira chamada)
        
    Returns:
        Instância do RealtimePipeline
    """
    global _pipeline_instance
    
    if _pipeline_instance is None:
        _pipeline_instance = RealtimePipeline(max_workers)
    
    return _pipeline_instance
