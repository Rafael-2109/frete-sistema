"""
Teste para validar migração do semantic_mapper (mapeamento_semantico.py)
"""
import unittest
import os

class TestSemanticMapperMigration(unittest.TestCase):
    """Testes para validar migração do semantic mapper"""
    
    def test_file_exists(self):
        """Testa se arquivo semantic_mapper existe"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'semantic_mapper.py')
        self.assertTrue(os.path.exists(file_path), "Arquivo semantic_mapper.py não encontrado")
    
    def test_file_content(self):
        """Testa se o conteúdo foi migrado corretamente"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'semantic_mapper.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar classe principal
        self.assertIn('class MapeamentoSemantico', content, "Classe MapeamentoSemantico não encontrada")
        
        # Verificar funções principais
        expected_functions = [
            'mapear_termo_natural',
            'mapear_consulta_completa', 
            'gerar_prompt_mapeamento',
            '_criar_mapeamentos_com_dados_reais',
            'get_mapeamento_semantico'
        ]
        
        for func in expected_functions:
            self.assertIn(func, content, f"Função {func} não encontrada")
        
        # Verificar tamanho
        self.assertGreater(len(content), 1000, "Arquivo parece estar vazio ou muito pequeno")
    
    def test_function_count(self):
        """Testa se número de funções está correto"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'semantic_mapper.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        func_count = content.count('def ')
        
        # Esperamos pelo menos 12 funções (original tinha 14)
        self.assertGreaterEqual(func_count, 12, f"Esperado pelo menos 12 funções, encontrado {func_count}")

if __name__ == '__main__':
    unittest.main()
