"""
Teste para validar migração do advanced_integration
"""
import unittest
import os

class TestAdvancedIntegrationMigration(unittest.TestCase):
    """Testes para validar migração do advanced integration"""
    
    def test_file_exists(self):
        """Testa se arquivo advanced_integration existe"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'advanced_integration.py')
        self.assertTrue(os.path.exists(file_path), "Arquivo advanced_integration.py não encontrado")
    
    def test_file_content(self):
        """Testa se o conteúdo foi migrado corretamente"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'advanced_integration.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar classes principais
        self.assertIn('class AdvancedAIIntegration', content, "Classe AdvancedAIIntegration não encontrada")
        self.assertIn('class MetacognitiveAnalyzer', content, "Classe MetacognitiveAnalyzer não encontrada")
        
        # Verificar funções principais
        expected_functions = [
            'process_advanced_query',
            'analyze_own_performance',
            'capture_advanced_feedback',
            'get_advanced_ai_integration',
            'get_advanced_analytics'
        ]
        
        for func in expected_functions:
            self.assertIn(func, content, f"Função {func} não encontrada")
        
        # Verificar tamanho
        self.assertGreater(len(content), 2000, "Arquivo parece estar vazio ou muito pequeno")
    
    def test_function_count(self):
        """Testa se número de funções está correto"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'advanced_integration.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        func_count = content.count('def ')
        
        # Esperamos pelo menos 14 funções (original tinha 16)
        self.assertGreaterEqual(func_count, 14, f"Esperado pelo menos 14 funções, encontrado {func_count}")
    
    def test_class_count(self):
        """Testa se número de classes está correto"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'advanced_integration.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        class_count = content.count('class ')
        
        # Esperamos pelo menos 2 classes
        self.assertGreaterEqual(class_count, 2, f"Esperado pelo menos 2 classes, encontrado {class_count}")

if __name__ == '__main__':
    unittest.main()
