"""
Teste para validar migração do lifelong_learning
"""
import unittest
import os

class TestLifelongLearningMigration(unittest.TestCase):
    """Testes para validar migração do lifelong learning"""
    
    def test_file_exists(self):
        """Testa se arquivo lifelong_learning existe"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'intelligence', 'lifelong_learning.py')
        self.assertTrue(os.path.exists(file_path), "Arquivo lifelong_learning.py não encontrado")
    
    def test_file_content(self):
        """Testa se o conteúdo foi migrado corretamente"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'intelligence', 'lifelong_learning.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar classes principais
        self.assertIn('class LifelongLearningSystem', content, "Classe LifelongLearningSystem não encontrada")
        
        # Verificar funções principais
        expected_functions = [
            'aprender_com_interacao',
            'aplicar_conhecimento',
            'obter_estatisticas_aprendizado',
            'get_lifelong_learning',
            '_extrair_padroes'
        ]
        
        for func in expected_functions:
            self.assertIn(func, content, f"Função {func} não encontrada")
        
        # Verificar tamanho
        self.assertGreater(len(content), 1000, "Arquivo parece estar vazio ou muito pequeno")
    
    def test_function_count(self):
        """Testa se número de funções está correto"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'intelligence', 'lifelong_learning.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        func_count = content.count('def ')
        
        # Esperamos pelo menos 8 funções (original tinha 10)
        self.assertGreaterEqual(func_count, 8, f"Esperado pelo menos 8 funções, encontrado {func_count}")
    
    def test_class_count(self):
        """Testa se número de classes está correto"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'intelligence', 'lifelong_learning.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        class_count = content.count('class ')
        
        # Esperamos pelo menos 1 classe
        self.assertGreaterEqual(class_count, 1, f"Esperado pelo menos 1 classe, encontrado {class_count}")

if __name__ == '__main__':
    unittest.main()
