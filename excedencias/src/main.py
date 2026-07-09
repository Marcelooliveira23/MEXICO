"""
Sistema de Análise de Inspeção de Aeronaves
Ponto de entrada principal da aplicação
"""

import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from views.main_window import MainWindow
from utils.logger import setup_logger


def main():
    """
    Função principal da aplicação
    """
    # Configurar high DPI
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    
    # Criar aplicação
    app = QApplication(sys.argv)
    app.setApplicationName("Análise de Inspeção de Aeronaves")
    app.setOrganizationName("Aviation Inspection")
    
    # Criar e mostrar janela principal
    window = MainWindow()
    window.show()
    
    # Executar loop de eventos
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
