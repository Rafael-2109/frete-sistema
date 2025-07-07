"""
Teste para validar migração do multi_agent_system
"""
import unittest
import os

class TestMultiAgentSystemMigration(unittest.TestCase):
    """Testes para validar migração do multi agent system"""
    
    def test_file_exists(self):
        """Testa se arquivo multi_agent_system existe"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'multi_agent_system.py')
        self.assertTrue(os.path.exists(file_path), "Arquivo multi_agent_system.py não encontrado")
    
    def test_file_content(self):
        """Testa se o conteúdo foi migrado corretamente"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'multi_agent_system.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar classes principais
        self.assertIn('class MultiAgentSystem', content, "Classe MultiAgentSystem não encontrada")
        self.assertIn('class SpecialistAgent', content, "Classe SpecialistAgent não encontrada")
        self.assertIn('class CriticAgent', content, "Classe CriticAgent não encontrada")
        
        # Verificar funções principais
        expected_functions = [
            'process_query',
            'validate_responses',
            'get_multi_agent_system',
            'analyze',
            'get_system_stats'
        ]
        
        for func in expected_functions:
            self.assertIn(func, content, f"Função {func} não encontrada")
        
        # Verificar tamanho
        self.assertGreater(len(content), 2000, "Arquivo parece estar vazio ou muito pequeno")
    
    def test_function_count(self):
        """Testa se número de funções está correto"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'multi_agent_system.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        func_count = content.count('def ')
        
        # Esperamos pelo menos 15 funções (original tinha 17)
        self.assertGreaterEqual(func_count, 15, f"Esperado pelo menos 15 funções, encontrado {func_count}")
    
    def test_class_count(self):
        """Testa se número de classes está correto"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'multi_agent_system.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        class_count = content.count('class ')
        
        # Esperamos pelo menos 3 classes (MultiAgentSystem, Agent, etc.)
        self.assertGreaterEqual(class_count, 3, f"Esperado pelo menos 3 classes, encontrado {class_count}")

if __name__ == '__main__':
    unittest.main()
