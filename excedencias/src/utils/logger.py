"""
Configuração de logging da aplicação
"""

import sys
from pathlib import Path
from loguru import logger
from typing import Any


def setup_logger(log_level: str = "INFO") -> Any:
    """
    Configura o sistema de logging
    
    Args:
        log_level: Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    
    Returns:
        Logger configurado
    """
    # Remover handler padrão
    logger.remove()
    
    # Criar diretório de logs
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Console output - colorido e formatado
    logger.add(
        sys.stdout,
        level=log_level,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:"
            "<cyan>{line}</cyan> | <level>{message}</level>"
        ),
        colorize=True,
    )
    
    # Arquivo de log - todas as mensagens
    logger.add(
        log_dir / "app_{time:YYYY-MM-DD}.log",
        level="DEBUG",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{name}:{function}:{line} | {message}"
        ),
        rotation="00:00",  # Novo arquivo a cada dia
        retention="30 days",  # Manter por 30 dias
        compression="zip",  # Comprimir logs antigos
    )
    
    # Arquivo de erros - apenas erros e críticos
    logger.add(
        log_dir / "errors_{time:YYYY-MM-DD}.log",
        level="ERROR",
        format=(
            "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | "
            "{name}:{function}:{line} | {message}\n{exception}"
        ),
        rotation="00:00",
        retention="90 days",
        compression="zip",
    )
    
    logger.info("Sistema de logging configurado")
    return logger
