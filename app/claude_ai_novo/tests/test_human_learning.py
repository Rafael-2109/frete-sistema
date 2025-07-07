"""
Teste para validar migração do human_in_loop_learning
"""
import unittest
import os

class TestHumanLearningMigration(unittest.TestCase):
    """Testes para validar migração do human in loop learning"""
    
    def test_file_exists(self):
        """Testa se arquivo human_in_loop_learning existe"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'intelligence', 'human_in_loop_learning.py')
        self.assertTrue(os.path.exists(file_path), "Arquivo human_in_loop_learning.py não encontrado")
    
    def test_file_content(self):
        """Testa se o conteúdo foi migrado corretamente"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'intelligence', 'human_in_loop_learning.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar classes principais
        self.assertIn('class HumanInLoopLearning', content, "Classe HumanInLoopLearning não encontrada")
        
        # Verificar funções principais
        expected_functions = [
            'capture_feedback',
            'get_improvement_suggestions',
            'apply_improvement',
            'get_human_learning_system',
            'generate_learning_report'
        ]
        
        for func in expected_functions:
            self.assertIn(func, content, f"Função {func} não encontrada")
        
        # Verificar tamanho
        self.assertGreater(len(content), 1500, "Arquivo parece estar vazio ou muito pequeno")
    
    def test_function_count(self):
        """Testa se número de funções está correto"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'intelligence', 'human_in_loop_learning.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        func_count = content.count('def ')
        
        # Esperamos pelo menos 10 funções (original tinha 12)
        self.assertGreaterEqual(func_count, 10, f"Esperado pelo menos 10 funções, encontrado {func_count}")
    
    def test_class_count(self):
        """Testa se número de classes está correto"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'intelligence', 'human_in_loop_learning.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        class_count = content.count('class ')
        
        # Esperamos pelo menos 1 classe
        self.assertGreaterEqual(class_count, 1, f"Esperado pelo menos 1 classe, encontrado {class_count}")

if __name__ == '__main__':
    unittest.main()
