"""
Script para atualizar testes de hard landing para nova interface
"""
import re
from pathlib import Path

def update_test_file():
    """Atualiza o arquivo de testes para usar a nova interface"""
    
    test_file = Path("tests/test_hard_landing_analyzer.py")
    content = test_file.read_text(encoding='utf-8')
    
    # Criar novo conteúdo do teste
    new_content = '''"""
Testes Unitários - Hard Landing Analyzer
Tests para validar detecção de Hard Landing com MODO AGRESSIVO
"""

import unittest
import pandas as pd
import sys
from pathlib import Path

# Adicionar src ao path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from services.hard_landing_analyzer import HardLandingAnalyzer
from services.all_families_specs import AllFamiliesSpecifications


class TestHardLandingDetection(unittest.TestCase):
    """Testes de detecção de Hard Landing"""
    
    def setUp(self):
        """Setup executado antes de cada teste"""
        self.analyzer = HardLandingAnalyzer()
    
    def create_flight_data(self, max_g, max_roll=0, max_pitch=0, 
                          touchdown_weight=40000, aircraft_model='E175'):
        """Helper para criar dados de voo para teste"""
        # Criar 100 pontos de dados simulando um voo
        num_points = 100
        
        # Simular descida e pouso
        altitude = list(range(10000, 0, -100)) + [0] * (num_points - 100)
        altitude = altitude[:num_points]
        
        # Pico de aceleração no touchdown
        touchdown_idx = 95
        vert_accel = [1.0] * num_points
        vert_accel[touchdown_idx] = max_g
        
        # Roll
        roll = [0.0] * num_points
        if max_roll != 0:
            roll[touchdown_idx] = max_roll
        
        # Pitch
        pitch = [0.0] * num_points
        if max_pitch != 0:
            pitch[touchdown_idx] = max_pitch
        
        # Criar DataFrame
        df = pd.DataFrame({
            'time': range(num_points),
            'altitude': altitude,
            'vertical_acceleration': vert_accel,
            'roll': roll,
            'pitch': pitch,
            'gross_weight': [touchdown_weight] * num_points,
            'airspeed': [150] * num_points
        })
        
        return df
    
    # ==================== TESTES E170 ====================
    
    def test_e170_no_hard_landing(self):
        """E170: Sem hard landing (1.5G < 1.8G threshold)"""
        df = self.create_flight_data(max_g=1.5, aircraft_model='E170')
        weight_kg = 35000 * 0.453592  # lb to kg
        
        results = self.analyzer.analyze(df, weight_kg, 'E170')
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, 'NORMAL')
    
    def test_e170_hard_landing_low(self):
        """E170: Hard landing LOW (1.85G)"""
        df = self.create_flight_data(max_g=1.85, aircraft_model='E170')
        weight_kg = 35000 * 0.453592
        
        results = self.analyzer.analyze(df, weight_kg, 'E170')
        
        self.assertEqual(len(results), 1)
        self.assertIn(results[0].status, ['HARD_LANDING_LOW', 'HARD_LANDING_HIGH', 'ENGINE_INSPECTION'])
    
    def test_e170_hard_landing_high(self):
        """E170: Hard landing HIGH (2.3G)"""
        df = self.create_flight_data(max_g=2.3, aircraft_model='E170')
        weight_kg = 35000 * 0.453592
        
        results = self.analyzer.analyze(df, weight_kg, 'E170')
        
        self.assertEqual(len(results), 1)
        self.assertIn(results[0].status, ['HARD_LANDING_HIGH', 'ENGINE_INSPECTION'])
    
    def test_e170_engine_inspection(self):
        """E170: ENGINE INSPECTION (2.6G)"""
        df = self.create_flight_data(max_g=2.6, aircraft_model='E170')
        weight_kg = 35000 * 0.453592
        
        results = self.analyzer.analyze(df, weight_kg, 'E170')
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, 'ENGINE_INSPECTION')
        self.assertGreaterEqual(results[0].vertical_accel['max_g'], 2.6)
    
    # ==================== TESTES E175 ====================
    
    def test_e175_no_hard_landing(self):
        """E175: Sem hard landing (1.7G < threshold)"""
        df = self.create_flight_data(max_g=1.7, aircraft_model='E175')
        weight_kg = 40000 * 0.453592
        
        results = self.analyzer.analyze(df, weight_kg, 'E175')
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, 'NORMAL')
    
    def test_e175_hard_landing_low(self):
        """E175: Hard landing LOW (1.9G)"""
        df = self.create_flight_data(max_g=1.9, aircraft_model='E175')
        weight_kg = 40000 * 0.453592
        
        results = self.analyzer.analyze(df, weight_kg, 'E175')
        
        self.assertEqual(len(results), 1)
        self.assertNotEqual(results[0].status, 'NORMAL')
    
    def test_e175_hard_landing_high(self):
        """E175: Hard landing HIGH (2.2G)"""
        df = self.create_flight_data(max_g=2.2, aircraft_model='E175')
        weight_kg = 40000 * 0.453592
        
        results = self.analyzer.analyze(df, weight_kg, 'E175')
        
        self.assertEqual(len(results), 1)
        self.assertIn(results[0].status, ['HARD_LANDING_HIGH', 'ENGINE_INSPECTION'])
    
    def test_e175_engine_inspection(self):
        """E175: ENGINE INSPECTION (2.7G)"""
        df = self.create_flight_data(max_g=2.7, aircraft_model='E175')
        weight_kg = 40000 * 0.453592
        
        results = self.analyzer.analyze(df, weight_kg, 'E175')
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, 'ENGINE_INSPECTION')
    
    # ==================== TESTES E190 ====================
    
    def test_e190_no_hard_landing(self):
        """E190: Sem hard landing"""
        df = self.create_flight_data(max_g=1.6, aircraft_model='E190')
        weight_kg = 45000 * 0.453592
        
        results = self.analyzer.analyze(df, weight_kg, 'E190')
        
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].status, 'NORMAL')
    
    def test_e190_hard_landing(self):
        """E190: Hard landing detectado (2.1G)"""
        df = self.create_flight_data(max_g=2.1, aircraft_model='E190')
        weight_kg = 45000 * 0.453592
        
        results = self.analyzer.analyze(df, weight_kg, 'E190')
        
        self.assertEqual(len(results), 1)
        self.assertNotEqual(results[0].status, 'NORMAL')
    
    # ==================== TESTES E195 ====================
    
    def test_e195_hard_landing(self):
        """E195: Hard landing (2.0G)"""
        df = self.create_flight_data(max_g=2.0, aircraft_model='E195')
        weight_kg = 46000 * 0.453592
        
        results = self.analyzer.analyze(df, weight_kg, 'E195')
        
        self.assertEqual(len(results), 1)
        self.assertNotEqual(results[0].status, 'NORMAL')
    
    # ==================== TESTES DE EDGE CASES ====================
    
    def test_empty_dataframe(self):
        """Teste com DataFrame vazio"""
        df = pd.DataFrame()
        weight_kg = 40000 * 0.453592
        
        results = self.analyzer.analyze(df, weight_kg, 'E175')
        
        self.assertEqual(len(results), 0)
    
    def test_missing_columns(self):
        """Teste com colunas faltando"""
        df = pd.DataFrame({
            'time': range(100),
            'altitude': list(range(10000, 0, -100))
        })
        weight_kg = 40000 * 0.453592
        
        results = self.analyzer.analyze(df, weight_kg, 'E175')
        
        # Deve retornar vazio ou normal sem aceleração vertical
        self.assertTrue(len(results) == 0 or results[0].status == 'NORMAL')
    
    def test_exact_threshold(self):
        """Teste com valor exato no threshold"""
        df = self.create_flight_data(max_g=1.8, aircraft_model='E175')
        weight_kg = 38000 * 0.453592  # Peso mínimo da tabela
        
        results = self.analyzer.analyze(df, weight_kg, 'E175')
        
        self.assertEqual(len(results), 1)
        # No threshold exato pode ser NORMAL ou LOW dependendo da implementação
        self.assertIn(results[0].status, ['NORMAL', 'HARD_LANDING_LOW'])


class TestWeightInterpolation(unittest.TestCase):
    """Testes de interpolação de thresholds por peso"""
    
    def setUp(self):
        """Setup"""
        self.analyzer = HardLandingAnalyzer()
    
    def test_interpolation_min_weight(self):
        """Interpolação no peso mínimo (38000 lb)"""
        weight_kg = 38000 * 0.453592
        threshold = self.analyzer._interpolate_threshold(
            weight_kg, self.analyzer.VERT_ACCEL_THRESHOLDS['low']
        )
        self.assertAlmostEqual(threshold, 1.800, places=2)
    
    def test_interpolation_max_weight(self):
        """Interpolação no peso máximo (54000 lb)"""
        weight_kg = 54000 * 0.453592
        threshold = self.analyzer._interpolate_threshold(
            weight_kg, self.analyzer.VERT_ACCEL_THRESHOLDS['low']
        )
        self.assertAlmostEqual(threshold, 2.200, places=2)
    
    def test_interpolation_mid_weight(self):
        """Interpolação no peso médio (46000 lb)"""
        weight_kg = 46000 * 0.453592
        threshold = self.analyzer._interpolate_threshold(
            weight_kg, self.analyzer.VERT_ACCEL_THRESHOLDS['low']
        )
        # Deve estar entre 1.8 e 2.2
        self.assertGreater(threshold, 1.8)
        self.assertLess(threshold, 2.2)


if __name__ == '__main__':
    unittest.main()
'''
    
    # Salvar arquivo atualizado
    test_file.write_text(new_content, encoding='utf-8')
    print(f"✅ Arquivo atualizado: {test_file}")

if __name__ == "__main__":
    update_test_file()
