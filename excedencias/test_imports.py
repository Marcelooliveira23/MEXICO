"""Script para testar importações de todos os módulos"""
import sys
import os

# Adicionar o diretório src ao path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

print("Testando importações...")
print("-" * 50)

try:
    print("✓ Importando chardet...")
    import chardet
    print(f"  Versão: {chardet.__version__}")
except ImportError as e:
    print(f"✗ Erro ao importar chardet: {e}")
    sys.exit(1)

try:
    print("✓ Importando PyQt6...")
    from PyQt6.QtWidgets import QApplication
    print("  PyQt6 OK")
except ImportError as e:
    print(f"✗ Erro ao importar PyQt6: {e}")
    sys.exit(1)

try:
    print("✓ Importando pandas...")
    import pandas as pd
    print(f"  Versão: {pd.__version__}")
except ImportError as e:
    print(f"✗ Erro ao importar pandas: {e}")
    sys.exit(1)

try:
    print("✓ Importando services...")
    from services import CSVParser, RulesEngine, ReportGenerator
    print("  Services OK")
except ImportError as e:
    print(f"✗ Erro ao importar services: {e}")
    sys.exit(1)

try:
    print("✓ Importando views...")
    from views.main_window import MainWindow
    print("  Views OK")
except ImportError as e:
    print(f"✗ Erro ao importar views: {e}")
    sys.exit(1)

print("-" * 50)
print("✓ Todas as importações foram bem-sucedidas!")
print("\nO aplicativo está pronto para ser executado.")
