"""
Matriz de Simulação Abrangente - 32 Cenários
Valida todos os eventos × famílias com isolamento completo
"""
import sys
from pathlib import Path
import pandas as pd
import json

root = Path('.').resolve()
sys.path.insert(0, str(root))
sys.path.insert(0, str(root/'src'))

from services.rules_engine import RulesEngine

# Configuração de famílias e pesos específicos
FAMILIES = ['e145', 'e170', 'e1', 'e2']
FAMILY_WEIGHTS = {
    'e145': 22000,  # kg
    'e170': 40000,  # kg
    'e1': 60000,    # kg (E190)
    'e2': 65000,    # kg (E190-E2)
}

def create_test_data():
    """Cria dados de teste para cada tipo de evento"""
    scenarios = {}
    
    # 1. HARD_LANDING
    scenarios['hard_landing'] = {
        'normal': pd.DataFrame({
            'vertical_acceleration': [-1.3, -1.4, -1.5],
            'nz': [0.5, 0.6, 0.7],
            'touchdown_rate': [-400, -450, -500],
        }),
        'violation': pd.DataFrame({
            'vertical_acceleration': [-2.3, -2.5, -2.7],
            'nz': [-0.3, -0.5, -0.7],
            'touchdown_rate': [-800, -900, -1000],
        })
    }
    
    # 2. GEAR_OVERSPEED (lg_down_overspeed)
    scenarios['gear_overspeed'] = {
        'normal': pd.DataFrame({
            'IAS': [180, 185, 190],
            'airspeed': [180, 185, 190],
            'gear_position': [1, 1, 1],
        }),
        'violation': pd.DataFrame({
            'IAS': [260, 270, 280],
            'airspeed': [260, 270, 280],
            'gear_position': [1, 1, 1],
        })
    }
    
    # 3. MAX_SPEED (vmo)
    scenarios['max_speed'] = {
        'normal': pd.DataFrame({
            'IAS': [280, 285, 290],
            'airspeed': [280, 285, 290],
            'altitude': [15000, 16000, 17000],
        }),
        'violation': pd.DataFrame({
            'IAS': [340, 350, 360],
            'airspeed': [340, 350, 360],
            'altitude': [15000, 16000, 17000],
        })
    }
    
    # 4. FLAP_OVERSPEED
    scenarios['flap_overspeed'] = {
        'normal': pd.DataFrame({
            'IAS': [190, 195, 200],
            'airspeed': [190, 195, 200],
            'FLAP_POSITION': [9, 9, 9],
            'flap_position': [9, 9, 9],
        }),
        'violation': pd.DataFrame({
            'IAS': [250, 260, 270],
            'airspeed': [250, 260, 270],
            'FLAP_POSITION': [9, 9, 9],
            'flap_position': [9, 9, 9],
        })
    }
    
    # 5. OVERWEIGHT_LANDING - valores específicos por família
    scenarios['overweight_landing'] = {}
    for fam in FAMILIES:
        weight = FAMILY_WEIGHTS[fam]
        scenarios['overweight_landing'][fam] = {
            'normal': pd.DataFrame({
                'weight': [weight * 0.85, weight * 0.87, weight * 0.90],
                'landing_weight': [weight * 0.85, weight * 0.87, weight * 0.90],
            }),
            'violation': pd.DataFrame({
                'weight': [weight * 1.05, weight * 1.08, weight * 1.10],
                'landing_weight': [weight * 1.05, weight * 1.08, weight * 1.10],
            })
        }
    
    # 6. TURBULENCE
    scenarios['turbulence'] = {
        'normal': pd.DataFrame({
            'vertical_acceleration': [1.05, 1.08, 1.10],
            'nz': [1.05, 1.08, 1.10],
            'g_load': [1.05, 1.08, 1.10],
            'airspeed': [220, 225, 230],
            'IAS': [220, 225, 230],
        }),
        'violation': pd.DataFrame({
            'vertical_acceleration': [2.8, 2.9, 3.0],
            'nz': [2.8, 2.9, 3.0],
            'g_load': [2.8, 2.9, 3.0],
            'airspeed': [320, 325, 330],
            'IAS': [320, 325, 330],
        })
    }
    
    # 7. OVER_G
    scenarios['over_g'] = {
        'normal': pd.DataFrame({
            'vertical_acceleration': [1.8, 1.9, 2.0],
            'nz': [1.8, 1.9, 2.0],
            'g_load': [1.8, 1.9, 2.0],
        }),
        'violation': pd.DataFrame({
            'vertical_acceleration': [2.8, 2.9, 3.0],
            'nz': [2.8, 2.9, 3.0],
            'g_load': [2.8, 2.9, 3.0],
        })
    }
    
    # 8. HIGH_BANK_ANGLE
    scenarios['high_bank_angle'] = {
        'normal': pd.DataFrame({
            'bank_angle': [30, 32, 35],
            'roll': [30, 32, 35],
            'altitude': [1200, 1300, 1400],
        }),
        'violation': pd.DataFrame({
            'bank_angle': [50, 52, 55],
            'roll': [50, 52, 55],
            'altitude': [1200, 1300, 1400],
        })
    }
    
    return scenarios

def run_comprehensive_matrix():
    """Executa matriz completa de 32 cenários"""
    
    print("=" * 100)
    print("MATRIZ DE SIMULAÇÃO ABRANGENTE - 32 CENÁRIOS (8 eventos × 4 famílias)")
    print("=" * 100)
    print()
    
    scenarios = create_test_data()
    results_summary = []
    threshold_comparison = {}
    
    event_types = [
        'hard_landing',
        'gear_overspeed',
        'max_speed',
        'flap_overspeed',
        'overweight_landing',
        'turbulence',
        'over_g',
        'high_bank_angle'
    ]
    
    for event_type in event_types:
        print(f"\n{'=' * 100}")
        print(f"EVENTO: {event_type.upper()}")
        print(f"{'=' * 100}\n")
        
        threshold_comparison[event_type] = {}
        
        for family in FAMILIES:
            # Limpa cache para garantir isolamento
            RulesEngine._pdf_rules_cache = {}
            
            # Carrega regras dinâmicas
            rules = RulesEngine.load_dynamic_rules(family, event_type)
            threshold_comparison[event_type][family] = rules
            
            print(f"  Família: {family.upper()}")
            print(f"  Thresholds: {rules}")
            
            # Define dados de teste
            if event_type == 'overweight_landing':
                # Usa dados específicos por família
                test_normal = scenarios[event_type][family]['normal']
                test_violation = scenarios[event_type][family]['violation']
            else:
                test_normal = scenarios[event_type]['normal']
                test_violation = scenarios[event_type]['violation']
            
            # Executa análise normal
            result_normal = RulesEngine.analyze(test_normal, family, event_type)
            status_normal = [r.status for r in result_normal.results] if result_normal.results else ['NO_DATA']
            
            # Executa análise violação
            result_violation = RulesEngine.analyze(test_violation, family, event_type)
            status_violation = [r.status for r in result_violation.results] if result_violation.results else ['NO_DATA']
            
            # Verifica se comportamento está correto
            has_ok_in_normal = 'OK' in status_normal or 'NO_DATA' in status_normal
            has_violation = 'VIOLATION' in status_violation
            behavior_correct = has_ok_in_normal and has_violation
            
            print(f"    ✓ Normal   : {status_normal}")
            print(f"    ✓ Violação : {status_violation}")
            
            if behavior_correct:
                print(f"    ✅ COMPORTAMENTO CORRETO")
            else:
                print(f"    ⚠️  COMPORTAMENTO INESPERADO")
            
            results_summary.append({
                'event_type': event_type,
                'family': family,
                'thresholds': rules,
                'normal_status': status_normal,
                'violation_status': status_violation,
                'behavior_correct': behavior_correct
            })
            
            print()
    
    # Resumo final
    print("\n" + "=" * 100)
    print("RESUMO DA VALIDAÇÃO")
    print("=" * 100)
    
    total_scenarios = len(results_summary)
    correct_behaviors = sum(1 for r in results_summary if r['behavior_correct'])
    
    print(f"\nTotal de cenários testados: {total_scenarios}")
    print(f"Comportamentos corretos: {correct_behaviors}")
    print(f"Taxa de sucesso: {(correct_behaviors/total_scenarios)*100:.1f}%")
    
    # Validação de isolamento entre famílias
    print("\n" + "=" * 100)
    print("VALIDAÇÃO DE ISOLAMENTO E THRESHOLDS EXCLUSIVOS")
    print("=" * 100)
    
    for event_type, family_thresholds in threshold_comparison.items():
        print(f"\n{event_type.upper()}:")
        unique_thresholds = list(set([str(t) for t in family_thresholds.values()]))
        
        for family, thresholds in family_thresholds.items():
            print(f"  {family}: {thresholds}")
        
        if len(unique_thresholds) > 1:
            print(f"  ✅ FAMÍLIAS TÊM THRESHOLDS DIFERENCIADOS ({len(unique_thresholds)} variações)")
        else:
            print(f"  ⚠️  TODAS AS FAMÍLIAS TÊM THRESHOLDS IDÊNTICOS")
    
    # Salva resultados
    output = {
        'total_scenarios': total_scenarios,
        'correct_behaviors': correct_behaviors,
        'success_rate': (correct_behaviors/total_scenarios)*100,
        'results': results_summary,
        'threshold_comparison': {k: {fam: str(t) for fam, t in v.items()} 
                                  for k, v in threshold_comparison.items()}
    }
    
    output_file = Path('tmp_comprehensive_simulation_results.json')
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Resultados salvos em: {output_file}")
    
    return output

if __name__ == '__main__':
    run_comprehensive_matrix()
