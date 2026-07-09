"""
Teste de integração do sistema atualizado
"""

__test__ = False

import sys
import pandas as pd
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.rules_engine import RulesEngine
from services.all_families_specs import get_specifications_by_model

def test_hard_landing_integration():
    """Testa integração do HardLandingAnalyzer no RulesEngine"""
    
    print("="*80)
    print("TESTE DE INTEGRAÇÃO - RulesEngine + HardLandingAnalyzer")
    print("="*80)
    
    # Carregar CSV de teste
    csv_path = Path(r"E:\Projetos\excedencias\test_data_e175_hard_landing.csv")
    
    if not csv_path.exists():
        print(f"❌ Arquivo não encontrado: {csv_path}")
        return
    
    print(f"\n📁 Carregando: {csv_path.name}")
    
    try:
        # Tentar múltiplos encodings
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                df = pd.read_csv(csv_path, encoding=encoding)
                print(f"✓ CSV carregado com encoding: {encoding}")
                print(f"  Linhas: {len(df)}, Colunas: {len(df.columns)}")
                break
            except UnicodeDecodeError:
                continue
        else:
            print("❌ Erro ao carregar CSV com encodings conhecidos")
            return
        
        # Testar especificações
        print("\n" + "="*80)
        print("TESTE 1: Especificações dinâmicas")
        print("="*80)
        
        specs = get_specifications_by_model('e1', 'E190')
        print(f"✓ Especificações E190:")
        print(f"  MLW: {specs.mlw_kg} kg")
        print(f"  Hard Landing G: {specs.hard_landing_g}")
        print(f"  CG Limits: {specs.cg_limits_percent_mac}")
        
        # Testar RulesEngine
        print("\n" + "="*80)
        print("TESTE 2: RulesEngine com Hard Landing Analyzer")
        print("="*80)
        
        analysis = RulesEngine.analyze(df, 'e1', 'hard_landing')
        
        print(f"\n✓ Análise completa:")
        print(f"  Aircraft: {analysis.aircraft_id}")
        print(f"  Event Type: {analysis.event_type}")
        print(f"  Tail: {analysis.tail_number}")
        print(f"  Overall Status: {analysis.overall_status}")
        print(f"  Resultados: {len(analysis.results)}")
        
        # Exibir resultados detalhados
        print("\n📊 RESULTADOS DETALHADOS:")
        print("-" * 80)
        for result in analysis.results:
            status_icon = "❌" if result.status == "VIOLATION" else "✓"
            print(f"\n{status_icon} {result.parameter}")
            print(f"  Status: {result.status}")
            print(f"  Valor: {result.value}")
            print(f"  Limite: {result.limit}")
            print(f"  Severidade: {result.severity}")
            print(f"  Mensagem: {result.message}")
        
        # Exibir recomendações
        print("\n💡 RECOMENDAÇÕES:")
        print("-" * 80)
        for rec in analysis.recommendations:
            print(f"  {rec}")
        
        print("\n" + "="*80)
        print("✅ TESTE DE INTEGRAÇÃO CONCLUÍDO COM SUCESSO")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ ERRO no teste: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_hard_landing_integration()
