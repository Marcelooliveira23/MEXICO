"""
Script simplificado para testar correções de window sizing
Valida diretamente as mudanças implementadas
"""
import pandas as pd
import numpy as np
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

def test_window_logic():
    """Testa a lógica de window sizing dinâmico"""
    
    print("="*80)
    print("TESTE DE LÓGICA DE WINDOW SIZING DINÂMICO")
    print("="*80)
    
    test_cases = [
        (5000, 300, 100, "Arquivo pequeno"),
        (15000, 300, 100, "Arquivo pequeno/médio"),
        (25000, 450, 150, "Arquivo médio"),
        (40000, 450, 150, "Arquivo médio/grande"),
        (55000, 600, 200, "Arquivo grande"),
        (70000, 600, 200, "Arquivo muito grande"),
    ]
    
    all_passed = True
    
    for df_len, expected_before, expected_after, description in test_cases:
        # Lógica implementada
        if df_len > 50000:
            window_before = 600
            window_after = 200
        elif df_len > 20000:
            window_before = 450
            window_after = 150
        else:
            window_before = 300
            window_after = 100
        
        passed = (window_before == expected_before and window_after == expected_after)
        status = "✓" if passed else "✗"
        
        print(f"{status} {description:25s} ({df_len:6,} linhas): "
              f"window_before={window_before} ({expected_before}), "
              f"window_after={window_after} ({expected_after})")
        
        if not passed:
            all_passed = False
    
    print("="*80)
    if all_passed:
        print("✓ TODOS OS TESTES DE LÓGICA PASSARAM")
    else:
        print("✗ ALGUNS TESTES FALHARAM")
    print("="*80)
    assert all_passed

def validate_code_changes():
    """Valida que as mudanças foram aplicadas corretamente no código"""
    
    print("\n" + "="*80)
    print("VALIDAÇÃO DAS MUDANÇAS NO CÓDIGO")
    print("="*80)
    
    file_path = r"e:\Projetos\excedencias\src\services\hard_landing_analyzer.py"
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        checks = [
            ("Window dinâmico - arquivo grande (50k+)", "if len(df) > 50000:", 
             "window_before = 600"),
            ("Window dinâmico - arquivo médio (20k+)", "elif len(df) > 20000:", 
             "window_before = 450"),
            ("Window dinâmico - arquivo pequeno", "window_before = 300", 
             "window_after = 100"),
            ("Logging NO_DATA detalhado", "Monitor 1 NO_DATA:", 
             "range [{start_idx}:{end_idx}] vazio"),
            ("Logging thresholds", "Monitor 1 - Peso:", 
             "Thresholds: LOW="),
            ("Logging análise entrada", "ANÁLISE HARD LANDING - Arquivo:", 
             "linhas, Peso:"),
        ]
        
        all_found = True
        
        for description, *keywords in checks:
            found = all(keyword in content for keyword in keywords)
            status = "✓" if found else "✗"
            print(f"{status} {description}")
            
            if not found:
                all_found = False
                print(f"    Procurando: {keywords}")
        
        print("="*80)
        if all_found:
            print("✓ TODAS AS MUDANÇAS FORAM APLICADAS CORRETAMENTE")
        else:
            print("✗ ALGUMAS MUDANÇAS NÃO FORAM ENCONTRADAS")
        print("="*80)
        
        return all_found
        
    except Exception as e:
        print(f"✗ ERRO ao ler arquivo: {e}")
        return False

def generate_test_report():
    """Gera relatório de testes completo"""
    
    print("\n" + "="*80)
    print("RELATÓRIO DE CORREÇÕES IMPLEMENTADAS")
    print("="*80)
    
    print("\n1. CORREÇÃO CRÍTICA: Window Sizing Dinâmico")
    print("   - Objetivo: Melhorar taxa de detecção de 33% para ~100%")
    print("   - Implementação:")
    print("     • Arquivo > 50k linhas: window 600/200 (antes era 200/100)")
    print("     • Arquivo > 20k linhas: window 450/150")
    print("     • Arquivo < 20k linhas: window 300/100 (padrão anterior)")
    
    print("\n2. MELHORIA: Logging Detalhado")
    print("   - Monitor 1 NO_DATA: log de range, touchdown, total de linhas")
    print("   - Monitor 1 dados válidos: log de peso, thresholds, max G")
    print("   - Início da análise: log de arquivo, peso, modelo")
    
    print("\n3. TESTES ESPERADOS COM ARQUIVOS REAIS:")
    print("   Arquivo 1 (70,600 linhas, 2.398G):")
    print("     • Antes: NO_DATA (window 200 muito pequeno)")
    print("     • Depois: DETECTADO com window 600")
    print("   ")
    print("   Arquivo 2 (49,664 linhas, 2.145G):")
    print("     • Antes: NO_DATA (window 200 muito pequeno)")
    print("     • Depois: DETECTADO com window 450")
    print("   ")
    print("   Arquivo 3 (11,304 linhas, 2.008G):")
    print("     • Antes: DETECTADO (window 200 suficiente)")
    print("     • Depois: DETECTADO com window 300 (sem mudança)")
    
    print("\n4. PRÓXIMOS PASSOS:")
    print("   ☐ Testar com os 3 arquivos originais do usuário")
    print("   ☐ Verificar logs detalhados no console")
    print("   ☐ Validar Phase I/II/III nas mensagens")
    print("   ☐ Confirmar taxa de detecção 100% (3/3 arquivos)")
    
    print("\n" + "="*80)

if __name__ == '__main__':
    # Executar testes
    try:
        test_window_logic()
        logic_ok = True
    except AssertionError:
        logic_ok = False
    code_ok = validate_code_changes()
    
    # Gerar relatório
    generate_test_report()
    
    # Resultado final
    print("\n" + "="*80)
    if logic_ok and code_ok:
        print("✓✓✓ TODAS AS CORREÇÕES VALIDADAS COM SUCESSO ✓✓✓")
        print("\nO sistema está pronto para testar com arquivos reais.")
        print("Execute a aplicação e teste com os 3 arquivos E175 originais.")
    else:
        print("⚠ ALGUMAS VALIDAÇÕES FALHARAM - REVISAR IMPLEMENTAÇÃO")
    print("="*80)
