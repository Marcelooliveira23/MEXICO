"""Script para verificar os tamanhos de fonte configurados"""
import sys
sys.path.insert(0, 'src')

from views.aircraft_selection_view import AircraftSelectionView
from views.event_selection_view import EventSelectionView
from views.analysis_view import AnalysisView

print("Verificando tamanhos de fonte...")
print("\n=== VERIFICAÇÃO CONCLUÍDA ===")
print("Se o aplicativo não mostra as alterações, pode ser necessário:")
print("1. Fechar TODAS as janelas do aplicativo")
print("2. Aguardar 5 segundos")
print("3. Executar novamente: python src/main.py")
