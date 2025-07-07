"""
Teste para validar migração do project_scanner
"""
import unittest
import os

class TestProjectScannerMigration(unittest.TestCase):
    """Testes para validar migração do project scanner"""
    
    def test_file_exists(self):
        """Testa se arquivo project_scanner existe"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'project_scanner.py')
        self.assertTrue(os.path.exists(file_path), "Arquivo project_scanner.py não encontrado")
    
    def test_file_content(self):
        """Testa se o conteúdo foi migrado corretamente"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'project_scanner.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar classes principais
        self.assertIn('class ClaudeProjectScanner', content, "Classe ClaudeProjectScanner não encontrada")
        
        # Verificar funções principais
        expected_functions = [
            'scan_complete_project',
            'read_file_content',
            'list_directory_contents',
            'get_project_scanner',
            'search_in_files'
        ]
        
        for func in expected_functions:
            self.assertIn(func, content, f"Função {func} não encontrada")
        
        # Verificar tamanho
        self.assertGreater(len(content), 1500, "Arquivo parece estar vazio ou muito pequeno")
    
    def test_function_count(self):
        """Testa se número de funções está correto"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'project_scanner.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        func_count = content.count('def ')
        
        # Esperamos pelo menos 18 funções (original tinha 21)
        self.assertGreaterEqual(func_count, 18, f"Esperado pelo menos 18 funções, encontrado {func_count}")
    
    def test_class_count(self):
        """Testa se número de classes está correto"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'project_scanner.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        class_count = content.count('class ')
        
        # Esperamos pelo menos 1 classe
        self.assertGreaterEqual(class_count, 1, f"Esperado pelo menos 1 classe, encontrado {class_count}")

if __name__ == '__main__':
    unittest.main()
