"""
Teste para validar migração do suggestion_engine
"""
import unittest
import os

class TestSuggestionEngineMigration(unittest.TestCase):
    """Testes para validar migração do suggestion engine"""
    
    def test_file_exists(self):
        """Testa se arquivo suggestion_engine existe"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'suggestion_engine.py')
        self.assertTrue(os.path.exists(file_path), "Arquivo suggestion_engine.py não encontrado")
    
    def test_file_content(self):
        """Testa se o conteúdo foi migrado corretamente"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'suggestion_engine.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar classes principais
        self.assertIn('class Suggestion', content, "Classe Suggestion não encontrada")
        self.assertIn('class SuggestionEngine', content, "Classe SuggestionEngine não encontrada")
        
        # Verificar funções principais
        expected_functions = [
            'get_intelligent_suggestions',
            '_generate_suggestions', 
            '_generate_data_based_suggestions',
            '_get_contextual_suggestions',
            'get_suggestion_engine'
        ]
        
        for func in expected_functions:
            self.assertIn(func, content, f"Função {func} não encontrada")
        
        # Verificar tamanho
        self.assertGreater(len(content), 1000, "Arquivo parece estar vazio ou muito pequeno")
    
    def test_function_count(self):
        """Testa se número de funções está correto"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'suggestion_engine.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        func_count = content.count('def ')
        
        # Esperamos pelo menos 10 funções (original tinha 13)
        self.assertGreaterEqual(func_count, 10, f"Esperado pelo menos 10 funções, encontrado {func_count}")

if __name__ == '__main__':
    unittest.main()
