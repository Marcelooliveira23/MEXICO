"""
WebSocket Server for Real-time Data Streaming
Broadcasts flight analysis results to connected clients
"""

import asyncio
import json
import websockets
from websockets.exceptions import ConnectionClosed
from typing import Set, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import threading
from queue import Queue

from utils.logger import logger


@dataclass
class WebSocketMessage:
    """Estrutura de mensagem WebSocket"""
    type: str  # analysis_result, alert, status_update
    timestamp: str
    data: Dict[str, Any]
    priority: str = "NORMAL"  # CRITICAL, HIGH, NORMAL, LOW


class WebSocketServer:
    """
    Servidor WebSocket para streaming em tempo real
    Suporta múltiplos clients simultâneos com broadcasting
    """
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        """
        Inicializar servidor WebSocket
        
        Args:
            host: Host do servidor (default: localhost)
            port: Porta do servidor (default: 8765)
        """
        self.host = host
        self.port = port
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.message_queue: Queue = Queue()
        self.running = False
        self.server = None
        self.server_task = None
        
        # Estatísticas
        self.total_messages_sent = 0
        self.total_clients_served = 0
        self.active_connections = 0
        
        logger.info(f"WebSocketServer initialized on {host}:{port}")
    
    async def register_client(self, websocket: websockets.WebSocketServerProtocol):
        """Registrar novo cliente"""
        self.clients.add(websocket)
        self.active_connections = len(self.clients)
        self.total_clients_served += 1
        
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"Client connected: {client_info} (Total: {self.active_connections})")
        
        # Enviar mensagem de boas-vindas
        welcome_msg = WebSocketMessage(
            type="connection_status",
            timestamp=datetime.now().isoformat(),
            data={
                "status": "connected",
                "server_time": datetime.now().isoformat(),
                "active_clients": self.active_connections
            }
        )
        await websocket.send(json.dumps(asdict(welcome_msg)))
    
    async def unregister_client(self, websocket: websockets.WebSocketServerProtocol):
        """Remover cliente desconectado"""
        self.clients.discard(websocket)
        self.active_connections = len(self.clients)
        
        client_info = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"Client disconnected: {client_info} (Remaining: {self.active_connections})")
    
    async def handle_client(self, websocket: websockets.WebSocketServerProtocol, path: str):
        """
        Handler para conexões de clientes
        
        Args:
            websocket: Conexão WebSocket
            path: Path da requisição
        """
        await self.register_client(websocket)
        
        try:
            # Manter conexão aberta e processar mensagens
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self.process_client_message(websocket, data)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON from client: {message}")
                except Exception as e:
                    logger.error(f"Error processing client message: {e}")
        
        except ConnectionClosed:
            logger.debug("Client connection closed normally")
        
        except Exception as e:
            logger.error(f"Unexpected error in client handler: {e}")
        
        finally:
            await self.unregister_client(websocket)
    
    async def process_client_message(self, websocket: websockets.WebSocketServerProtocol, 
                                     data: Dict[str, Any]):
        """
        Processar mensagem recebida de cliente
        
        Args:
            websocket: Conexão do cliente
            data: Dados da mensagem
        """
        msg_type = data.get("type", "unknown")
        
        if msg_type == "ping":
            # Responder com pong
            pong = WebSocketMessage(
                type="pong",
                timestamp=datetime.now().isoformat(),
                data={"server_time": datetime.now().isoformat()}
            )
            await websocket.send(json.dumps(asdict(pong)))
        
        elif msg_type == "subscribe":
            # Cliente quer se inscrever em eventos específicos
            event_types = data.get("event_types", [])
            logger.info(f"Client subscribed to: {event_types}")
            # TODO: Implementar lógica de subscription
        
        elif msg_type == "get_status":
            # Cliente quer status do servidor
            status = WebSocketMessage(
                type="server_status",
                timestamp=datetime.now().isoformat(),
                data={
                    "active_clients": self.active_connections,
                    "total_messages_sent": self.total_messages_sent,
                    "uptime": "N/A"  # TODO: Calcular uptime
                }
            )
            await websocket.send(json.dumps(asdict(status)))
        
        else:
            logger.warning(f"Unknown message type from client: {msg_type}")
    
    async def broadcast(self, message: WebSocketMessage):
        """
        Broadcast mensagem para todos os clientes conectados
        
        Args:
            message: Mensagem para enviar
        """
        if not self.clients:
            logger.debug("No clients connected, skipping broadcast")
            return
        
        # Serializar mensagem
        msg_json = json.dumps(asdict(message))
        
        # Enviar para todos os clientes
        disconnected_clients = set()
        
        for client in self.clients:
            try:
                send_result = client.send(msg_json)
                if asyncio.iscoroutine(send_result) or asyncio.isfuture(send_result):
                    await send_result
                self.total_messages_sent += 1
            
            except ConnectionClosed:
                disconnected_clients.add(client)
                logger.warning("Client disconnected during broadcast")
            
            except Exception as e:
                logger.error(f"Error broadcasting to client: {e}")
                disconnected_clients.add(client)
        
        # Remover clientes desconectados
        for client in disconnected_clients:
            await self.unregister_client(client)
        
        logger.debug(f"Broadcast sent to {len(self.clients)} clients")
    
    async def broadcast_analysis_result(self, flight_id: int, aircraft_model: str,
                                       event_type: str, severity: str, 
                                       results: Dict[str, Any]):
        """
        Broadcast resultado de análise
        
        Args:
            flight_id: ID do voo
            aircraft_model: Modelo da aeronave
            event_type: Tipo de evento
            severity: Severidade
            results: Resultados da análise
        """
        message = WebSocketMessage(
            type="analysis_result",
            timestamp=datetime.now().isoformat(),
            priority=severity,
            data={
                "flight_id": flight_id,
                "aircraft_model": aircraft_model,
                "event_type": event_type,
                "severity": severity,
                "results": results,
                "timestamp": datetime.now().isoformat()
            }
        )
        
        await self.broadcast(message)
        logger.info(f"Broadcast analysis result: Flight {flight_id}, Severity {severity}")
    
    async def broadcast_alert(self, alert_type: str, severity: str, 
                            message_text: str, details: Dict[str, Any]):
        """
        Broadcast alerta crítico
        
        Args:
            alert_type: Tipo de alerta
            severity: Severidade (CRITICAL, HIGH, etc)
            message_text: Mensagem do alerta
            details: Detalhes adicionais
        """
        message = WebSocketMessage(
            type="alert",
            timestamp=datetime.now().isoformat(),
            priority=severity,
            data={
                "alert_type": alert_type,
                "severity": severity,
                "message": message_text,
                "details": details
            }
        )
        
        await self.broadcast(message)
        logger.warning(f"Broadcast alert: {alert_type} - {severity}")
    
    def start_background(self):
        """Iniciar servidor em thread separada"""
        if self.running:
            logger.warning("Server already running")
            return
        
        def run_server():
            asyncio.run(self.start())
        
        thread = threading.Thread(target=run_server, daemon=True)
        thread.start()
        
        logger.info("WebSocket server started in background thread")
    
    async def start(self):
        """Iniciar servidor WebSocket"""
        if self.running:
            logger.warning("Server already running")
            return
        
        self.running = True
        
        try:
            # Criar servidor WebSocket
            self.server = await websockets.serve(
                self.handle_client,
                self.host,
                self.port,
                ping_interval=30,  # Ping a cada 30s
                ping_timeout=10    # Timeout de 10s
            )
            
            logger.info(f"✅ WebSocket server started on ws://{self.host}:{self.port}")
            
            # Manter servidor rodando
            await asyncio.Future()  # Run forever
        
        except Exception as e:
            logger.error(f"Error starting WebSocket server: {e}")
            self.running = False
            raise
    
    async def stop(self):
        """Parar servidor WebSocket"""
        if not self.running:
            logger.warning("Server not running")
            return
        
        logger.info("Stopping WebSocket server...")
        
        # Fechar todas as conexões de clientes
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients],
                return_exceptions=True
            )
        
        # Fechar servidor
        if self.server:
            self.server.close()
            await self.server.wait_closed()
        
        self.running = False
        self.clients.clear()
        
        logger.info("✅ WebSocket server stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Obter estatísticas do servidor"""
        return {
            "active_connections": self.active_connections,
            "total_clients_served": self.total_clients_served,
            "total_messages_sent": self.total_messages_sent,
            "running": self.running,
            "host": self.host,
            "port": self.port
        }


# Singleton instance
_server_instance: Optional[WebSocketServer] = None


def get_websocket_server(host: str = "localhost", port: int = 8765) -> WebSocketServer:
    """
    Obter instância singleton do servidor WebSocket
    
    Args:
        host: Host do servidor
        port: Porta do servidor
        
    Returns:
        Instância do WebSocketServer
    """
    global _server_instance
    
    if _server_instance is None:
        _server_instance = WebSocketServer(host, port)
    
    return _server_instance
