"""
Script de Teste Rápido - Validação com CSV Real
"""
import sys
from pathlib import Path


def run_quick_validation(csv_path: Path) -> int:
    print("\n" + "="*80)
    print("TESTE RÁPIDO - VALIDAÇÃO COM CSV REAL")
    print("="*80)

    if not csv_path.exists():
        print(f"\n❌ Arquivo não encontrado: {csv_path}")
        return 1

    print(f"\n📂 Arquivo: {csv_path}")
    print(f"   Tamanho: {csv_path.stat().st_size / 1024 / 1024:.2f} MB")

    sys.path.insert(0, str(Path(__file__).parent / "src"))

    import pandas as pd
    from services.hard_landing_analyzer import HardLandingAnalyzer
    from services.csv_column_mapper import CSVColumnMapper

    try:
        # 1. Carregar CSV
        print("\n1️⃣ Carregando CSV...")
        df = pd.read_csv(csv_path, encoding='latin1', on_bad_lines='skip')
        print(f"   ✅ {len(df)} linhas carregadas")
        print(f"   Colunas: {len(df.columns)}")

        # 2. Mapear colunas
        print("\n2️⃣ Mapeando colunas...")
        mapper = CSVColumnMapper()
        df_mapped = mapper.map_columns(df)
        print(f"   ✅ Colunas mapeadas")
        mapped_cols = [col for col in df_mapped.columns if not col.startswith('unmapped_')]
        print(f"   Mapeadas: {len(mapped_cols)}")
        print(f"   Principais: {', '.join(mapped_cols[:10])}")

        # 3. Extrair peso
        print("\n3️⃣ Extraindo peso...")
        weight_cols = [col for col in df_mapped.columns if 'weight' in col.lower()]
        if weight_cols:
            weight_data = df_mapped[weight_cols[0]]
            if isinstance(weight_data, pd.DataFrame):
                weight_lb = weight_data.iloc[:, 0].dropna().iloc[0]
            else:
                weight_lb = weight_data.dropna().iloc[0]

            if isinstance(weight_lb, pd.Series):
                weight_lb = weight_lb.iloc[0]

            weight_lb_float = float(weight_lb)
            weight_kg = weight_lb_float * 0.453592
            print(f"   ✅ Peso: {weight_lb_float:.1f} lb = {weight_kg:.1f} kg")
        else:
            weight_kg = 75000 * 0.453592  # Default
            print(f"   ⚠️ Peso não encontrado, usando padrão: {weight_kg:.1f} kg")

        # 4. Detectar modelo
        print("\n4️⃣ Detectando modelo...")
        if weight_kg < 33000:
            model = 'E170'
        elif weight_kg < 39000:
            model = 'E175'
        elif weight_kg < 48000:
            model = 'E190'
        else:
            model = 'E195'
        print(f"   ✅ Modelo detectado: {model}")

        # 5. Detectar voos
        print("\n5️⃣ Detectando voos...")
        analyzer = HardLandingAnalyzer()
        flights = analyzer.detect_flights(df_mapped)
        print(f"   ✅ {len(flights)} voo(s) detectado(s)")

        for i, flight in enumerate(flights[:5]):  # Mostrar primeiros 5
            print(f"      Voo {i+1}: touchdown={flight['touchdown']}, "
                  f"range=[{flight['start_idx']}:{flight['end_idx']}]"
            )

        if len(flights) > 5:
            print(f"      ... e mais {len(flights) - 5} voos")

        # 6. Analisar hard landing
        print("\n6️⃣ Analisando hard landing...")
        results = analyzer.analyze(df_mapped, weight_kg, model)
        print(f"   ✅ {len(results)} análise(s) completa(s)")

        # 7. Exibir resultados
        print("\n7️⃣ Resultados:")

        hard_landings = 0
        for i, result in enumerate(results[:10]):  # Mostrar primeiros 10
            status = result.status
            max_g = result.vertical_accel.get('max_g', 0) if result.vertical_accel else 0

            if 'HARD_LANDING' in status or 'ENGINE_INSPECTION' in status:
                hard_landings += 1
                print(f"   🔴 Voo {i+1}: {status} - Max G: {max_g:.3f}G")
            else:
                print(f"   🟢 Voo {i+1}: {status} - Max G: {max_g:.3f}G")

        if len(results) > 10:
            remaining_hard = sum(1 for r in results[10:]
                               if 'HARD_LANDING' in r.status
                               or 'ENGINE_INSPECTION' in r.status)
            hard_landings += remaining_hard
            print(f"   ... e mais {len(results) - 10} resultados")

        # 8. Resumo final
        print("\n" + "="*80)
        print("RESUMO FINAL")
        print("="*80)
        print(f"📊 Total de voos: {len(results)}")
        print(f"🔴 Hard landings detectados: {hard_landings}")
        print(f"🟢 Pousos normais: {len(results) - hard_landings}")
        print(f"📈 Taxa de hard landing: {hard_landings/len(results)*100:.1f}%")

        if hard_landings > 0:
            print("\n✅ SISTEMA FUNCIONANDO - Hard landings detectados!")
        else:
            print("\n⚠️ ATENÇÃO - Nenhum hard landing detectado")
            print("   Verifique se o arquivo contém eventos de hard landing")

        print("\n" + "="*80)
        return 0

    except Exception as e:
        print("\n❌ ERRO durante análise:")
        print(f"   {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return 1


def test_quick_validation_requires_input():
    import pytest
    pytest.skip("Requer arquivo CSV real informado via CLI")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("\n❌ Uso: python test_quick_validation.py <caminho_do_arquivo.csv>")
        print("\nExemplo:")
        print("  python test_quick_validation.py data/e190_flight_data.csv")
        sys.exit(1)

    sys.exit(run_quick_validation(Path(sys.argv[1])))
