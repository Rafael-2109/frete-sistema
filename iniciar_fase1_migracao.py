#!/usr/bin/env python3
"""
🚀 INICIANDO FASE 1 - MIGRAÇÃO CLAUDE AI
Script para migrar primeiro arquivo conforme plano detalhado
"""

import os
import shutil
from pathlib import Path

def iniciar_fase1():
    """Inicia a Fase 1 da migração"""
    print("🚀 INICIANDO FASE 1 - MIGRAÇÃO CLAUDE AI")
    print("=" * 60)
    
    # Primeiro arquivo: advanced_config.py
    print("\n📦 1. MIGRANDO CONFIGURAÇÕES")
    print("Arquivo: advanced_config.py")
    
    origem = "app/claude_ai/advanced_config.py"
    destino = "app/claude_ai_novo/config/advanced_config.py"
    
    if os.path.exists(origem):
        print(f"   ✅ Arquivo encontrado: {origem}")
        
        # Criar diretório de destino
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        
        # Copiar arquivo
        shutil.copy2(origem, destino)
        print(f"   ✅ Copiado para: {destino}")
        
        # Verificar se foi copiado
        if os.path.exists(destino):
            print("   ✅ Migração concluída com sucesso!")
            return True
        else:
            print("   ❌ Erro na cópia")
            return False
    else:
        print(f"   ❌ Arquivo não encontrado: {origem}")
        return False

def verificar_estrutura():
    """Verifica se a estrutura nova existe"""
    print("\n🔍 VERIFICANDO ESTRUTURA NOVA")
    
    estrutura_nova = "app/claude_ai_novo"
    
    if os.path.exists(estrutura_nova):
        print(f"   ✅ Estrutura existe: {estrutura_nova}")
        
        # Listar diretórios
        dirs = [d for d in os.listdir(estrutura_nova) if os.path.isdir(os.path.join(estrutura_nova, d))]
        print(f"   📁 Diretórios: {', '.join(dirs)}")
        
        return True
    else:
        print(f"   ❌ Estrutura não encontrada: {estrutura_nova}")
        return False

def criar_teste_basico():
    """Cria teste básico para validar migração"""
    print("\n🧪 CRIANDO TESTE BÁSICO")
    
    teste_dir = "app/claude_ai_novo/tests"
    os.makedirs(teste_dir, exist_ok=True)
    
    teste_arquivo = os.path.join(teste_dir, "test_config.py")
    
    conteudo_teste = '''"""
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
    
    def test_config_import(self):
        """Testa se pode importar configurações"""
        try:
            from config.advanced_config import get_advanced_config
            self.assertTrue(callable(get_advanced_config), "Função get_advanced_config não encontrada")
        except ImportError as e:
            self.fail(f"Erro ao importar configurações: {e}")

if __name__ == '__main__':
    unittest.main()
'''
    
    with open(teste_arquivo, 'w', encoding='utf-8') as f:
        f.write(conteudo_teste)
    
    print(f"   ✅ Teste criado: {teste_arquivo}")

def executar_teste():
    """Executa o teste básico"""
    print("\n🧪 EXECUTANDO TESTE BÁSICO")
    
    try:
        import subprocess
        result = subprocess.run([
            'python', '-m', 'pytest', 
            'app/claude_ai_novo/tests/test_config.py', 
            '-v'
        ], capture_output=True, text=True, cwd='.')
        
        print(f"   📋 Resultado: {result.returncode}")
        if result.stdout:
            print(f"   📝 Output: {result.stdout}")
        if result.stderr:
            print(f"   ⚠️ Errors: {result.stderr}")
            
        return result.returncode == 0
    except Exception as e:
        print(f"   ❌ Erro ao executar teste: {e}")
        return False

def main():
    """Função principal"""
    print("🎯 FASE 1 - MIGRAÇÃO CLAUDE AI")
    print("Conforme PLANO_MIGRACAO_CLAUDE_AI_DETALHADO.md")
    print()
    
    # Verificar estrutura
    if not verificar_estrutura():
        print("❌ Estrutura nova não encontrada. Execute primeiro implementar_nova_estrutura.py")
        return False
    
    # Migrar primeiro arquivo
    if iniciar_fase1():
        print("✅ Primeira migração concluída!")
        
        # Criar teste
        criar_teste_basico()
        
        # Executar teste
        if executar_teste():
            print("✅ Testes passaram!")
        else:
            print("⚠️ Testes falharam, mas migração foi feita")
        
        print("\n🎯 PRÓXIMOS PASSOS:")
        print("1. Migrar sistema_real_data.py")
        print("2. Migrar mapeamento_semantico.py")
        print("3. Continuar com Fase 1 conforme plano")
        
        return True
    else:
        print("❌ Migração falhou")
        return False

if __name__ == "__main__":
    main() 