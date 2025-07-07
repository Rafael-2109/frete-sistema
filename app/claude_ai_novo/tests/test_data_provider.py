"""
Teste para validar migração do data_provider (sistema_real_data.py)
"""
import unittest
import os

class TestDataProviderMigration(unittest.TestCase):
    """Testes para validar migração do data provider"""
    
    def test_file_exists(self):
        """Testa se arquivo data_provider existe"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'data_provider.py')
        self.assertTrue(os.path.exists(file_path), "Arquivo data_provider.py não encontrado")
    
    def test_file_content(self):
        """Testa se o conteúdo foi migrado corretamente"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'data_provider.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar classe principal
        self.assertIn('class SistemaRealData', content, "Classe SistemaRealData não encontrada")
        
        # Verificar funções principais
        expected_functions = [
            'buscar_todos_modelos_reais',
            'buscar_clientes_reais', 
            'buscar_transportadoras_reais',
            'gerar_system_prompt_real',
            'get_sistema_real_data'
        ]
        
        for func in expected_functions:
            self.assertIn(func, content, f"Função {func} não encontrada")
        
        # Verificar tamanho
        self.assertGreater(len(content), 1000, "Arquivo parece estar vazio ou muito pequeno")
    
    def test_function_count(self):
        """Testa se número de funções está correto"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'data_provider.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        func_count = content.count('def ')
        
        # Esperamos pelo menos 10 funções (original tinha 12)
        self.assertGreaterEqual(func_count, 10, f"Esperado pelo menos 10 funções, encontrado {func_count}")

if __name__ == '__main__':
    unittest.main()
