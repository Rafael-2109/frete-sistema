"""
Teste básico para validar migração da Fase 1
"""
import unittest
import sys
import os

# Adicionar path para imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

class TestConfigMigration(unittest.TestCase):
    """Testes para validar migração de configurações"""
    
    def test_config_exists(self):
        """Testa se arquivo de config existe"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'advanced_config.py')
        self.assertTrue(os.path.exists(config_path), "Arquivo de configuração não encontrado")
    
    def test_config_content(self):
        """Testa se o conteúdo do arquivo foi migrado corretamente"""
        config_path = os.path.join(os.path.dirname(__file__), '..', 'config', 'advanced_config.py')
        
        # Ler conteúdo do arquivo
        with open(config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar se contém funções esperadas
        self.assertIn('def get_advanced_config', content, "Função get_advanced_config não encontrada")
        self.assertIn('def is_unlimited_mode', content, "Função is_unlimited_mode não encontrada")
        
        # Verificar se não está vazio
        self.assertGreater(len(content), 100, "Arquivo parece estar vazio ou muito pequeno")

if __name__ == '__main__':
    unittest.main()
