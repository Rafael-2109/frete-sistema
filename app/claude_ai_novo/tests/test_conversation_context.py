"""
Teste para validar migração do conversation_context
"""
import unittest
import os

class TestConversationContextMigration(unittest.TestCase):
    """Testes para validar migração do conversation context"""
    
    def test_file_exists(self):
        """Testa se arquivo conversation_context existe"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'intelligence', 'conversation_context.py')
        self.assertTrue(os.path.exists(file_path), "Arquivo conversation_context.py não encontrado")
    
    def test_file_content(self):
        """Testa se o conteúdo foi migrado corretamente"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'intelligence', 'conversation_context.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar classes principais
        self.assertIn('class ConversationContext', content, "Classe ConversationContext não encontrada")
        
        # Verificar funções principais
        expected_functions = [
            'add_message',
            'get_context',
            'clear_context',
            'get_conversation_context',
            'build_context_prompt'
        ]
        
        for func in expected_functions:
            self.assertIn(func, content, f"Função {func} não encontrada")
        
        # Verificar tamanho
        self.assertGreater(len(content), 1000, "Arquivo parece estar vazio ou muito pequeno")
    
    def test_function_count(self):
        """Testa se número de funções está correto"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'intelligence', 'conversation_context.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        func_count = content.count('def ')
        
        # Esperamos pelo menos 6 funções (original tinha 8)
        self.assertGreaterEqual(func_count, 6, f"Esperado pelo menos 6 funções, encontrado {func_count}")
    
    def test_class_count(self):
        """Testa se número de classes está correto"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'intelligence', 'conversation_context.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        class_count = content.count('class ')
        
        # Esperamos pelo menos 1 classe
        self.assertGreaterEqual(class_count, 1, f"Esperado pelo menos 1 classe, encontrado {class_count}")

if __name__ == '__main__':
    unittest.main()
