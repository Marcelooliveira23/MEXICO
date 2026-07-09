"""
Teste específico para arquivo XA-ALU _HL_13AGO25_FLT651.CSV
"""
import sys
from pathlib import Path
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent / 'src'))

from services.hard_landing_analyzer import HardLandingAnalyzer
from services.csv_parser import CSVParser

def test_xa_alu():
    """Testa detecção com arquivo XA-ALU"""
    
    # Caminho do arquivo
    csv_file = Path(r"c:\Users\mrced\OneDrive\Documents\hard landing\XA-ALU _HL_13AGO25_FLT651.CSV")
    
    if not csv_file.exists():
        # Tentar caminho alternativo
        csv_file = Path("XA-ALU _HL_13AGO25_FLT651.CSV")
        if not csv_file.exists():
            print(f"❌ Arquivo não encontrado: {csv_file}")
            return
    
    print("=" * 80)
    print("ANÁLISE DO ARQUIVO XA-ALU")
    print("=" * 80)
    print(f"Arquivo: {csv_file}")
    
    # Carregar dados
    parser = CSVParser()
    try:
        df = parser.parse_file(csv_file)
        print(f"\n✅ Arquivo carregado: {len(df)} linhas")
        print(f"Colunas: {list(df.columns)[:10]}...")  # Primeiras 10 colunas
        
        # Mostrar estatísticas
        print(f"\n{'=' * 80}")
        print("ESTATÍSTICAS DOS DADOS")
        print(f"{'=' * 80}")
        
        # Verificar colunas de aceleração
        accel_cols = [col for col in df.columns if 'accel' in col.lower() or 'nz' in col.lower() or 'norm' in col.lower()]
        print(f"\nColunas de aceleração encontradas: {accel_cols}")
        
        if accel_cols:
            for col in accel_cols:
                print(f"\n{col}:")
                print(f"  Min: {df[col].min():.3f}")
                print(f"  Max: {df[col].max():.3f}")
                print(f"  Média: {df[col].mean():.3f}")
        
        # Verificar altitude
        alt_cols = [col for col in df.columns if 'alt' in col.lower()]
        if alt_cols:
            print(f"\nColunas de altitude: {alt_cols[0]}")
            print(f"  Min: {df[alt_cols[0]].min():.1f}")
            print(f"  Max: {df[alt_cols[0]].max():.1f}")
        
        # Verificar peso
        weight_cols = [col for col in df.columns if 'weight' in col.lower() or 'gross' in col.lower()]
        if weight_cols:
            print(f"\nColunas de peso: {weight_cols[0]}")
            print(f"  Valor: {df[weight_cols[0]].iloc[0]:.0f}")
        
        print(f"\n{'=' * 80}")
        print("EXECUTANDO ANÁLISE DE HARD LANDING")
        print(f"{'=' * 80}")
        
        # Executar análise
        analyzer = HardLandingAnalyzer()
        
        # Peso estimado: 75000 lb = 34019 kg
        weight_kg = 34019
        model = 'E175'
        
        print(f"\nModelo: {model}")
        print(f"Peso: {weight_kg:.0f} kg ({weight_kg * 2.20462:.0f} lb)")
        
        results = analyzer.analyze(df, weight_kg, model)
        
        print(f"\n{'=' * 80}")
        print(f"RESULTADOS")
        print(f"{'=' * 80}")
        print(f"\nVoos detectados: {len(results)}")
        
        if not results:
            print("\n❌ NENHUM VOO DETECTADO")
            print("\n🔍 Possíveis causas:")
            print("  1. Dados insuficientes para detecção de voo")
            print("  2. Falta de coluna de altitude")
            print("  3. Dados não contêm fase de pouso")
            
            # Tentar análise direta
            print(f"\n{'=' * 80}")
            print("TENTANDO ANÁLISE DIRETA (SEM DETECÇÃO DE VOO)")
            print(f"{'=' * 80}")
            
            # Criar resultado manual
            if accel_cols:
                max_g = df[accel_cols[0]].max()
                print(f"\nAceleração vertical máxima: {max_g:.3f} G")
                
                # Verificar thresholds
                if weight_kg:
                    weight_lb = weight_kg * 2.20462
                    low_threshold = analyzer.interpolate_threshold(weight_lb, analyzer.VERT_ACCEL_THRESHOLDS['low'])
                    high_threshold = analyzer.interpolate_threshold(weight_lb, analyzer.VERT_ACCEL_THRESHOLDS['high'])
                    engine_threshold = analyzer.interpolate_threshold(weight_lb, analyzer.VERT_ACCEL_THRESHOLDS['engine'])
                    
                    print(f"\nThresholds para {weight_lb:.0f} lb:")
                    print(f"  LOW: {low_threshold:.2f} G")
                    print(f"  HIGH: {high_threshold:.2f} G")
                    print(f"  ENGINE: {engine_threshold:.2f} G")
                    
                    if max_g >= engine_threshold:
                        print(f"\n🔴 CRÍTICO: {max_g:.3f}G >= {engine_threshold:.2f}G - ENGINE INSPECTION!")
                    elif max_g >= high_threshold:
                        print(f"\n⚠️ ALTO: {max_g:.3f}G >= {high_threshold:.2f}G - HARD LANDING HIGH!")
                    elif max_g >= low_threshold:
                        print(f"\n⚠️ BAIXO: {max_g:.3f}G >= {low_threshold:.2f}G - HARD LANDING LOW!")
                    else:
                        print(f"\n✅ NORMAL: {max_g:.3f}G < {low_threshold:.2f}G")
        else:
            for i, result in enumerate(results, 1):
                print(f"\n{'─' * 80}")
                print(f"VOO {i}")
                print(f"{'─' * 80}")
                print(f"Status: {result.status}")
                print(f"Severidade: {result.severity}")
                print(f"Mensagem: {result.message}")
                
                if result.critical_monitors:
                    print(f"Monitores críticos: {result.critical_monitors}")
                
                print(f"\n📊 Monitor 1 - Aceleração Vertical:")
                vert = result.vertical_accel
                print(f"   Status: {vert['status']}")
                if 'max_g' in vert:
                    print(f"   Max G: {vert['max_g']:.3f}")
                if 'thresholds' in vert:
                    th = vert['thresholds']
                    print(f"   Limites: Low={th.get('low', 'N/A'):.2f}, High={th.get('high', 'N/A'):.2f}, Engine={th.get('engine', 'N/A'):.2f}")
                
                if result.status != 'NORMAL':
                    print(f"\n🚨 HARD LANDING DETECTADO!")
                else:
                    print(f"\n✅ Voo normal")
        
    except Exception as e:
        print(f"\n❌ Erro ao processar arquivo: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"\n{'=' * 80}")

if __name__ == "__main__":
    test_xa_alu()
