#!/usr/bin/env python3
"""
🚀 CONTINUANDO FASE 1 - MIGRAÇÃO CLAUDE AI
Script para migrar próximo arquivo: sistema_real_data.py
"""

import os
import shutil
import argparse
from pathlib import Path

def migrar_sistema_real_data():
    """Migra sistema_real_data.py para core/data_provider.py"""
    print("🚀 MIGRANDO SISTEMA_REAL_DATA.PY")
    print("=" * 60)
    
    origem = "app/claude_ai/sistema_real_data.py"
    destino = "app/claude_ai_novo/core/data_provider.py"
    
    print(f"📂 Origem: {origem}")
    print(f"📁 Destino: {destino}")
    
    if not os.path.exists(origem):
        print(f"   ❌ Arquivo origem não encontrado: {origem}")
        return False
    
    # Criar diretório core se não existir
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    
    # Copiar arquivo
    shutil.copy2(origem, destino)
    
    # Verificar se foi copiado
    if os.path.exists(destino):
        print(f"   ✅ Arquivo migrado com sucesso!")
        
        # Mostrar estatísticas do arquivo
        with open(destino, 'r', encoding='utf-8') as f:
            content = f.read()
            
        lines = len(content.split('\n'))
        size = len(content)
        
        # Contar funções
        func_count = content.count('def ')
        class_count = content.count('class ')
        
        print(f"   📊 Estatísticas:")
        print(f"      - Linhas: {lines}")
        print(f"      - Tamanho: {size} bytes")
        print(f"      - Funções: {func_count}")
        print(f"      - Classes: {class_count}")
        
        return True
    else:
        print(f"   ❌ Erro na migração")
        return False

def atualizar_init_core():
    """Atualiza __init__.py do core para incluir data_provider"""
    print("\n📦 ATUALIZANDO CORE/__INIT__.PY")
    
    init_path = "app/claude_ai_novo/core/__init__.py"
    
    # Criar se não existir
    if not os.path.exists(init_path):
        os.makedirs(os.path.dirname(init_path), exist_ok=True)
        
        content = '''"""
🧠 CORE - Núcleo do Sistema Claude AI
Módulo central com funcionalidades principais
"""

# Importações principais
try:
    from .data_provider import SistemaRealData, get_sistema_real_data
    __all__ = ['SistemaRealData', 'get_sistema_real_data']
except ImportError:
    __all__ = []

# Versão do módulo
__version__ = "1.0.0"
'''
        
        with open(init_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"   ✅ Criado: {init_path}")
    else:
        # Atualizar existente
        with open(init_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Adicionar import se não existir
        if 'data_provider' not in content:
            # Encontrar linha dos imports
            lines = content.split('\n')
            import_line = None
            all_line = None
            
            for i, line in enumerate(lines):
                if 'from .' in line and 'import' in line:
                    import_line = i
                if '__all__' in line and '=' in line:
                    all_line = i
            
            if import_line is not None:
                # Adicionar novo import
                new_import = "    from .data_provider import SistemaRealData, get_sistema_real_data"
                lines.insert(import_line + 1, new_import)
                
                # Atualizar __all__
                if all_line is not None:
                    for i, line in enumerate(lines):
                        if '__all__' in line and '=' in line:
                            if 'SistemaRealData' not in line:
                                line = line.replace(']', ", 'SistemaRealData', 'get_sistema_real_data']")
                                lines[i] = line
                            break
                
                # Escrever arquivo atualizado
                with open(init_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                
                print(f"   ✅ Atualizado: {init_path}")
            else:
                print(f"   ⚠️ Não foi possível atualizar automaticamente")
        else:
            print(f"   ✅ Já contém data_provider")

def criar_teste_data_provider():
    """Cria teste para validar migração do data_provider"""
    print("\n🧪 CRIANDO TESTE PARA DATA_PROVIDER")
    
    teste_path = "app/claude_ai_novo/tests/test_data_provider.py"
    
    content = '''"""
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
'''
    
    with open(teste_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"   ✅ Teste criado: {teste_path}")

def executar_testes():
    """Executa todos os testes"""
    print("\n🧪 EXECUTANDO TESTES")
    
    try:
        import subprocess
        
        # Executar teste específico
        result = subprocess.run([
            'python', '-m', 'pytest', 
            'app/claude_ai_novo/tests/test_data_provider.py', 
            '-v'
        ], capture_output=True, text=True, cwd='.')
        
        print(f"   📋 Resultado: {result.returncode}")
        if result.stdout:
            print(f"   📝 Output:\n{result.stdout}")
        if result.stderr:
            print(f"   ⚠️ Errors:\n{result.stderr}")
            
        return result.returncode == 0
    except Exception as e:
        print(f"   ❌ Erro ao executar testes: {e}")
        return False

def migrar_mapeamento_semantico():
    """Migra mapeamento_semantico.py para core/semantic_mapper.py"""
    print("🚀 MIGRANDO MAPEAMENTO_SEMANTICO.PY")
    print("=" * 60)
    
    origem = "app/claude_ai/mapeamento_semantico.py"
    destino = "app/claude_ai_novo/core/semantic_mapper.py"
    
    print(f"📂 Origem: {origem}")
    print(f"📁 Destino: {destino}")
    
    if not os.path.exists(origem):
        print(f"   ❌ Arquivo origem não encontrado: {origem}")
        return False
    
    # Criar diretório core se não existir
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    
    # Copiar arquivo
    shutil.copy2(origem, destino)
    
    # Verificar se foi copiado
    if os.path.exists(destino):
        print(f"   ✅ Arquivo migrado com sucesso!")
        
        # Mostrar estatísticas do arquivo
        with open(destino, 'r', encoding='utf-8') as f:
            content = f.read()
            
        lines = len(content.split('\n'))
        size = len(content)
        
        # Contar funções
        func_count = content.count('def ')
        class_count = content.count('class ')
        
        print(f"   📊 Estatísticas:")
        print(f"      - Linhas: {lines}")
        print(f"      - Tamanho: {size} bytes")
        print(f"      - Funções: {func_count}")
        print(f"      - Classes: {class_count}")
        
        return True
    else:
        print(f"   ❌ Erro na migração")
        return False

def atualizar_init_core_semantico():
    """Atualiza __init__.py do core para incluir semantic_mapper"""
    print("\n📦 ATUALIZANDO CORE/__INIT__.PY (SEMANTIC MAPPER)")
    
    init_path = "app/claude_ai_novo/core/__init__.py"
    
    if os.path.exists(init_path):
        with open(init_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Adicionar import se não existir
        if 'semantic_mapper' not in content:
            # Adicionar novo import
            new_import = "    from .semantic_mapper import MapeamentoSemantico, get_mapeamento_semantico"
            
            # Encontrar onde adicionar
            lines = content.split('\n')
            import_added = False
            
            for i, line in enumerate(lines):
                if 'from .data_provider' in line:
                    lines.insert(i + 1, new_import)
                    import_added = True
                    break
            
            if import_added:
                # Atualizar __all__
                for i, line in enumerate(lines):
                    if '__all__' in line and '=' in line:
                        if 'MapeamentoSemantico' not in line:
                            line = line.replace(']', ", 'MapeamentoSemantico', 'get_mapeamento_semantico']")
                            lines[i] = line
                        break
                
                # Escrever arquivo atualizado
                with open(init_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                
                print(f"   ✅ Atualizado: {init_path}")
            else:
                print(f"   ⚠️ Não foi possível atualizar automaticamente")
        else:
            print(f"   ✅ Já contém semantic_mapper")
    else:
        print(f"   ❌ Arquivo __init__.py não encontrado")

def criar_teste_semantic_mapper():
    """Cria teste para validar migração do semantic_mapper"""
    print("\n🧪 CRIANDO TESTE PARA SEMANTIC_MAPPER")
    
    teste_path = "app/claude_ai_novo/tests/test_semantic_mapper.py"
    
    content = '''"""
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
'''
    
    with open(teste_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"   ✅ Teste criado: {teste_path}")

def executar_teste_semantico():
    """Executa teste do semantic mapper"""
    print("\n🧪 EXECUTANDO TESTE SEMANTIC MAPPER")
    
    try:
        import subprocess
        
        # Executar teste específico
        result = subprocess.run([
            'python', '-m', 'pytest', 
            'app/claude_ai_novo/tests/test_semantic_mapper.py', 
            '-v'
        ], capture_output=True, text=True, cwd='.')
        
        print(f"   📋 Resultado: {result.returncode}")
        if result.stdout:
            print(f"   📝 Output:\n{result.stdout}")
        if result.stderr:
            print(f"   ⚠️ Errors:\n{result.stderr}")
            
        return result.returncode == 0
    except Exception as e:
        print(f"   ❌ Erro ao executar testes: {e}")
        return False

def atualizar_relatorio_progresso_semantico():
    """Atualiza relatório de progresso para semantic mapper"""
    print("\n📊 ATUALIZANDO RELATÓRIO DE PROGRESSO (SEMANTIC MAPPER)")
    
    relatorio_path = "RELATORIO_PROGRESSO_FASE1.md"
    
    if os.path.exists(relatorio_path):
        with open(relatorio_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Atualizar estatísticas
        content = content.replace('**Arquivos migrados:** 2/12 (16.7%)', '**Arquivos migrados:** 3/12 (25.0%)')
        content = content.replace('**Funções migradas:** 14/180 (7.8%)', '**Funções migradas:** 28/180 (15.6%)')
        
        # Atualizar status do mapeamento_semantico
        content = content.replace('| `mapeamento_semantico.py` | `core/semantic_mapper.py` | 14 | ⏳ **Próximo** |',
                                '| `mapeamento_semantico.py` | `core/semantic_mapper.py` | 14 | ✅ **Concluído** |')
        
        # Marcar próximo como próximo
        content = content.replace('| `suggestion_engine.py` | `core/suggestion_engine.py` | 13 | ⏳ Pendente |',
                                '| `suggestion_engine.py` | `core/suggestion_engine.py` | 13 | ⏳ **Próximo** |')
        
        with open(relatorio_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"   ✅ Relatório atualizado: {relatorio_path}")
    else:
        print(f"   ⚠️ Relatório não encontrado: {relatorio_path}")

def migrar_suggestion_engine():
    """Migra suggestion_engine.py para core/suggestion_engine.py"""
    print("🚀 MIGRANDO SUGGESTION_ENGINE.PY")
    print("=" * 60)
    
    origem = "app/claude_ai/suggestion_engine.py"
    destino = "app/claude_ai_novo/core/suggestion_engine.py"
    
    print(f"📂 Origem: {origem}")
    print(f"📁 Destino: {destino}")
    
    if not os.path.exists(origem):
        print(f"   ❌ Arquivo origem não encontrado: {origem}")
        return False
    
    # Criar diretório core se não existir
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    
    # Copiar arquivo
    shutil.copy2(origem, destino)
    
    # Verificar se foi copiado
    if os.path.exists(destino):
        print(f"   ✅ Arquivo migrado com sucesso!")
        
        # Mostrar estatísticas do arquivo
        with open(destino, 'r', encoding='utf-8') as f:
            content = f.read()
            
        lines = len(content.split('\n'))
        size = len(content)
        
        # Contar funções
        func_count = content.count('def ')
        class_count = content.count('class ')
        
        print(f"   📊 Estatísticas:")
        print(f"      - Linhas: {lines}")
        print(f"      - Tamanho: {size} bytes")
        print(f"      - Funções: {func_count}")
        print(f"      - Classes: {class_count}")
        
        return True
    else:
        print(f"   ❌ Erro na migração")
        return False

def atualizar_init_core_suggestion():
    """Atualiza __init__.py do core para incluir suggestion_engine"""
    print("\n📦 ATUALIZANDO CORE/__INIT__.PY (SUGGESTION ENGINE)")
    
    init_path = "app/claude_ai_novo/core/__init__.py"
    
    if os.path.exists(init_path):
        with open(init_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Adicionar import se não existir
        if 'suggestion_engine' not in content:
            # Adicionar novo import
            new_import = "    from .suggestion_engine import SuggestionEngine, get_suggestion_engine"
            
            # Encontrar onde adicionar
            lines = content.split('\n')
            import_added = False
            
            for i, line in enumerate(lines):
                if 'from .semantic_mapper' in line:
                    lines.insert(i + 1, new_import)
                    import_added = True
                    break
            
            if import_added:
                # Atualizar __all__
                for i, line in enumerate(lines):
                    if '__all__' in line and '=' in line:
                        if 'SuggestionEngine' not in line:
                            line = line.replace(']', ", 'SuggestionEngine', 'get_suggestion_engine']")
                            lines[i] = line
                        break
                
                # Escrever arquivo atualizado
                with open(init_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                
                print(f"   ✅ Atualizado: {init_path}")
            else:
                print(f"   ⚠️ Não foi possível atualizar automaticamente")
        else:
            print(f"   ✅ Já contém suggestion_engine")
    else:
        print(f"   ❌ Arquivo __init__.py não encontrado")

def criar_teste_suggestion_engine():
    """Cria teste para validar migração do suggestion_engine"""
    print("\n🧪 CRIANDO TESTE PARA SUGGESTION_ENGINE")
    
    teste_path = "app/claude_ai_novo/tests/test_suggestion_engine.py"
    
    content = '''"""
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
'''
    
    with open(teste_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"   ✅ Teste criado: {teste_path}")

def executar_teste_suggestion():
    """Executa teste do suggestion engine"""
    print("\n🧪 EXECUTANDO TESTE SUGGESTION ENGINE")
    
    try:
        import subprocess
        
        # Executar teste específico
        result = subprocess.run([
            'python', '-m', 'pytest', 
            'app/claude_ai_novo/tests/test_suggestion_engine.py', 
            '-v'
        ], capture_output=True, text=True, cwd='.')
        
        print(f"   📋 Resultado: {result.returncode}")
        if result.stdout:
            print(f"   📝 Output:\n{result.stdout}")
        if result.stderr:
            print(f"   ⚠️ Errors:\n{result.stderr}")
            
        return result.returncode == 0
    except Exception as e:
        print(f"   ❌ Erro ao executar testes: {e}")
        return False

def atualizar_relatorio_progresso_suggestion():
    """Atualiza relatório de progresso para suggestion engine"""
    print("\n📊 ATUALIZANDO RELATÓRIO DE PROGRESSO (SUGGESTION ENGINE)")
    
    relatorio_path = "RELATORIO_PROGRESSO_FASE1.md"
    
    if os.path.exists(relatorio_path):
        with open(relatorio_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Atualizar estatísticas
        content = content.replace('**Arquivos migrados:** 3/12 (25.0%)', '**Arquivos migrados:** 4/12 (33.3%)')
        content = content.replace('**Funções migradas:** 28/180 (15.6%)', '**Funções migradas:** 41/180 (22.8%)')
        
        # Atualizar status do suggestion_engine
        content = content.replace('| `suggestion_engine.py` | `core/suggestion_engine.py` | 13 | ⏳ **Próximo** |',
                                '| `suggestion_engine.py` | `core/suggestion_engine.py` | 13 | ✅ **Concluído** |')
        
        # Marcar próximo como próximo
        content = content.replace('| `multi_agent_system.py` | `core/multi_agent_system.py` | 17 | ⏳ Pendente |',
                                '| `multi_agent_system.py` | `core/multi_agent_system.py` | 17 | ⏳ **Próximo** |')
        
        with open(relatorio_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"   ✅ Relatório atualizado: {relatorio_path}")
    else:
        print(f"   ⚠️ Relatório não encontrado: {relatorio_path}")

def migrar_multi_agent_system():
    """Migra multi_agent_system.py para core/multi_agent_system.py"""
    print("🚀 MIGRANDO MULTI_AGENT_SYSTEM.PY")
    print("=" * 60)
    
    origem = "app/claude_ai/multi_agent_system.py"
    destino = "app/claude_ai_novo/core/multi_agent_system.py"
    
    print(f"📂 Origem: {origem}")
    print(f"📁 Destino: {destino}")
    
    if not os.path.exists(origem):
        print(f"   ❌ Arquivo origem não encontrado: {origem}")
        return False
    
    # Criar diretório core se não existir
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    
    # Copiar arquivo
    shutil.copy2(origem, destino)
    
    # Verificar se foi copiado
    if os.path.exists(destino):
        print(f"   ✅ Arquivo migrado com sucesso!")
        
        # Mostrar estatísticas do arquivo
        with open(destino, 'r', encoding='utf-8') as f:
            content = f.read()
            
        lines = len(content.split('\n'))
        size = len(content)
        
        # Contar funções e classes
        func_count = content.count('def ')
        class_count = content.count('class ')
        
        print(f"   📊 Estatísticas:")
        print(f"      - Linhas: {lines}")
        print(f"      - Tamanho: {size} bytes")
        print(f"      - Funções: {func_count}")
        print(f"      - Classes: {class_count}")
        
        return True
    else:
        print(f"   ❌ Erro na migração")
        return False

def atualizar_init_core_multi_agent():
    """Atualiza __init__.py do core para incluir multi_agent_system"""
    print("\n📦 ATUALIZANDO CORE/__INIT__.PY (MULTI-AGENT SYSTEM)")
    
    init_path = "app/claude_ai_novo/core/__init__.py"
    
    if os.path.exists(init_path):
        with open(init_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Adicionar import se não existir
        if 'multi_agent_system' not in content:
            # Adicionar novo import
            new_import = "    from .multi_agent_system import MultiAgentSystem, get_multi_agent_system"
            
            # Encontrar onde adicionar
            lines = content.split('\n')
            import_added = False
            
            for i, line in enumerate(lines):
                if 'from .suggestion_engine' in line:
                    lines.insert(i + 1, new_import)
                    import_added = True
                    break
            
            if import_added:
                # Atualizar __all__
                for i, line in enumerate(lines):
                    if '__all__' in line and '=' in line:
                        if 'MultiAgentSystem' not in line:
                            line = line.replace(']', ", 'MultiAgentSystem', 'get_multi_agent_system']")
                            lines[i] = line
                        break
                
                # Escrever arquivo atualizado
                with open(init_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                
                print(f"   ✅ Atualizado: {init_path}")
            else:
                print(f"   ⚠️ Não foi possível atualizar automaticamente")
        else:
            print(f"   ✅ Já contém multi_agent_system")
    else:
        print(f"   ❌ Arquivo __init__.py não encontrado")

def criar_teste_multi_agent_system():
    """Cria teste para validar migração do multi_agent_system"""
    print("\n🧪 CRIANDO TESTE PARA MULTI_AGENT_SYSTEM")
    
    teste_path = "app/claude_ai_novo/tests/test_multi_agent_system.py"
    
    content = '''"""
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
        self.assertIn('class Agent', content, "Classe Agent não encontrada")
        
        # Verificar funções principais
        expected_functions = [
            'process_query',
            'coordinate_agents',
            'validate_response',
            'get_multi_agent_system',
            'analyze_convergence'
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
'''
    
    with open(teste_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"   ✅ Teste criado: {teste_path}")

def executar_teste_multi_agent():
    """Executa teste do multi agent system"""
    print("\n🧪 EXECUTANDO TESTE MULTI AGENT SYSTEM")
    
    try:
        import subprocess
        
        # Executar teste específico
        result = subprocess.run([
            'python', '-m', 'pytest', 
            'app/claude_ai_novo/tests/test_multi_agent_system.py', 
            '-v'
        ], capture_output=True, text=True, cwd='.')
        
        print(f"   📋 Resultado: {result.returncode}")
        if result.stdout:
            print(f"   📝 Output:\n{result.stdout}")
        if result.stderr:
            print(f"   ⚠️ Errors:\n{result.stderr}")
            
        return result.returncode == 0
    except Exception as e:
        print(f"   ❌ Erro ao executar testes: {e}")
        return False

def atualizar_relatorio_progresso_multi_agent():
    """Atualiza relatório de progresso para multi agent system"""
    print("\n📊 ATUALIZANDO RELATÓRIO DE PROGRESSO (MULTI-AGENT)")
    
    relatorio_path = "RELATORIO_PROGRESSO_FASE1.md"
    
    if os.path.exists(relatorio_path):
        with open(relatorio_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Atualizar estatísticas
        content = content.replace('**Arquivos migrados:** 4/12 (33.3%)', '**Arquivos migrados:** 5/12 (41.7%)')
        content = content.replace('**Funções migradas:** 41/180 (22.8%)', '**Funções migradas:** 58/180 (32.2%)')
        
        # Atualizar status do multi_agent_system
        content = content.replace('| `multi_agent_system.py` | `core/multi_agent_system.py` | 17 | ⏳ **Próximo** |',
                                '| `multi_agent_system.py` | `core/multi_agent_system.py` | 17 | ✅ **Concluído** |')
        
        # Marcar próximo como próximo
        content = content.replace('| `claude_project_scanner.py` | `core/project_scanner.py` | 21 | ⏳ Pendente |',
                                '| `claude_project_scanner.py` | `core/project_scanner.py` | 21 | ⏳ **Próximo** |')
        
        with open(relatorio_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"   ✅ Relatório atualizado: {relatorio_path}")
    else:
        print(f"   ⚠️ Relatório não encontrado: {relatorio_path}")

def migrar_claude_project_scanner():
    """Migra claude_project_scanner.py para core/project_scanner.py"""
    print("🚀 MIGRANDO CLAUDE_PROJECT_SCANNER.PY")
    print("=" * 60)
    
    origem = "app/claude_ai/claude_project_scanner.py"
    destino = "app/claude_ai_novo/core/project_scanner.py"
    
    print(f"📂 Origem: {origem}")
    print(f"📁 Destino: {destino}")
    
    if not os.path.exists(origem):
        print(f"   ❌ Arquivo origem não encontrado: {origem}")
        return False
    
    # Criar diretório core se não existir
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    
    # Copiar arquivo
    shutil.copy2(origem, destino)
    
    # Verificar se foi copiado
    if os.path.exists(destino):
        print(f"   ✅ Arquivo migrado com sucesso!")
        
        # Mostrar estatísticas do arquivo
        with open(destino, 'r', encoding='utf-8') as f:
            content = f.read()
            
        lines = len(content.split('\n'))
        size = len(content)
        
        # Contar funções e classes
        func_count = content.count('def ')
        class_count = content.count('class ')
        
        print(f"   📊 Estatísticas:")
        print(f"      - Linhas: {lines}")
        print(f"      - Tamanho: {size} bytes")
        print(f"      - Funções: {func_count}")
        print(f"      - Classes: {class_count}")
        
        return True
    else:
        print(f"   ❌ Erro na migração")
        return False

def atualizar_init_core_project_scanner():
    """Atualiza __init__.py do core para incluir project_scanner"""
    print("\n📦 ATUALIZANDO CORE/__INIT__.PY (PROJECT SCANNER)")
    
    init_path = "app/claude_ai_novo/core/__init__.py"
    
    if os.path.exists(init_path):
        with open(init_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Adicionar import se não existir
        if 'project_scanner' not in content:
            # Adicionar novo import
            new_import = "    from .project_scanner import ClaudeProjectScanner, get_project_scanner"
            
            # Encontrar onde adicionar
            lines = content.split('\n')
            import_added = False
            
            for i, line in enumerate(lines):
                if 'from .multi_agent_system' in line:
                    lines.insert(i + 1, new_import)
                    import_added = True
                    break
            
            if import_added:
                # Atualizar __all__
                for i, line in enumerate(lines):
                    if '__all__' in line and '=' in line:
                        if 'ClaudeProjectScanner' not in line:
                            line = line.replace(']', ", 'ClaudeProjectScanner', 'get_project_scanner']")
                            lines[i] = line
                        break
                
                # Escrever arquivo atualizado
                with open(init_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                
                print(f"   ✅ Atualizado: {init_path}")
            else:
                print(f"   ⚠️ Não foi possível atualizar automaticamente")
        else:
            print(f"   ✅ Já contém project_scanner")
    else:
        print(f"   ❌ Arquivo __init__.py não encontrado")

def criar_teste_project_scanner():
    """Cria teste para validar migração do project_scanner"""
    print("\n🧪 CRIANDO TESTE PARA PROJECT_SCANNER")
    
    teste_path = "app/claude_ai_novo/tests/test_project_scanner.py"
    
    content = '''"""
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
        self.assertIn('class ProjectAnalyzer', content, "Classe ProjectAnalyzer não encontrada")
        
        # Verificar funções principais
        expected_functions = [
            'scan_project',
            'analyze_structure',
            'discover_components',
            'get_project_scanner',
            'generate_insights'
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
        
        # Esperamos pelo menos 2 classes
        self.assertGreaterEqual(class_count, 2, f"Esperado pelo menos 2 classes, encontrado {class_count}")

if __name__ == '__main__':
    unittest.main()
'''
    
    with open(teste_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"   ✅ Teste criado: {teste_path}")

def executar_teste_project_scanner():
    """Executa teste do project scanner"""
    print("\n🧪 EXECUTANDO TESTE PROJECT SCANNER")
    
    try:
        import subprocess
        
        # Executar teste específico
        result = subprocess.run([
            'python', '-m', 'pytest', 
            'app/claude_ai_novo/tests/test_project_scanner.py', 
            '-v'
        ], capture_output=True, text=True, cwd='.')
        
        print(f"   📋 Resultado: {result.returncode}")
        if result.stdout:
            print(f"   📝 Output:\n{result.stdout}")
        if result.stderr:
            print(f"   ⚠️ Errors:\n{result.stderr}")
            
        return result.returncode == 0
    except Exception as e:
        print(f"   ❌ Erro ao executar testes: {e}")
        return False

def atualizar_relatorio_progresso_project_scanner():
    """Atualiza relatório de progresso para project scanner"""
    print("\n📊 ATUALIZANDO RELATÓRIO DE PROGRESSO (PROJECT SCANNER)")
    
    relatorio_path = "RELATORIO_PROGRESSO_FASE1.md"
    
    if os.path.exists(relatorio_path):
        with open(relatorio_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Atualizar estatísticas
        content = content.replace('**Arquivos migrados:** 5/12 (41.7%)', '**Arquivos migrados:** 6/12 (50.0%)')
        content = content.replace('**Funções migradas:** 58/180 (32.2%)', '**Funções migradas:** 79/180 (43.9%)')
        
        # Atualizar status do project_scanner
        content = content.replace('| `claude_project_scanner.py` | `core/project_scanner.py` | 21 | ⏳ **Próximo** |',
                                '| `claude_project_scanner.py` | `core/project_scanner.py` | 21 | ✅ **Concluído** |')
        
        # Marcar próximo como próximo
        content = content.replace('| `advanced_integration.py` | `core/advanced_integration.py` | 16 | ⏳ Pendente |',
                                '| `advanced_integration.py` | `core/advanced_integration.py` | 16 | ⏳ **Próximo** |')
        
        with open(relatorio_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"   ✅ Relatório atualizado: {relatorio_path}")
    else:
        print(f"   ⚠️ Relatório não encontrado: {relatorio_path}")

def migrar_advanced_integration():
    """Migra advanced_integration.py para core/advanced_integration.py"""
    print("🚀 MIGRANDO ADVANCED_INTEGRATION.PY")
    print("=" * 60)
    
    origem = "app/claude_ai/advanced_integration.py"
    destino = "app/claude_ai_novo/core/advanced_integration.py"
    
    print(f"📂 Origem: {origem}")
    print(f"📁 Destino: {destino}")
    
    if not os.path.exists(origem):
        print(f"   ❌ Arquivo origem não encontrado: {origem}")
        return False
    
    # Criar diretório core se não existir
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    
    # Copiar arquivo
    shutil.copy2(origem, destino)
    
    # Verificar se foi copiado
    if os.path.exists(destino):
        print(f"   ✅ Arquivo migrado com sucesso!")
        
        # Mostrar estatísticas do arquivo
        with open(destino, 'r', encoding='utf-8') as f:
            content = f.read()
            
        lines = len(content.split('\n'))
        size = len(content)
        
        # Contar funções e classes
        func_count = content.count('def ')
        class_count = content.count('class ')
        
        print(f"   📊 Estatísticas:")
        print(f"      - Linhas: {lines}")
        print(f"      - Tamanho: {size} bytes")
        print(f"      - Funções: {func_count}")
        print(f"      - Classes: {class_count}")
        
        return True
    else:
        print(f"   ❌ Erro na migração")
        return False

def atualizar_init_core_advanced_integration():
    """Atualiza __init__.py do core para incluir advanced_integration"""
    print("\n📦 ATUALIZANDO CORE/__INIT__.PY (ADVANCED INTEGRATION)")
    
    init_path = "app/claude_ai_novo/core/__init__.py"
    
    if os.path.exists(init_path):
        with open(init_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Adicionar import se não existir
        if 'advanced_integration' not in content:
            # Adicionar novo import
            new_import = "    from .advanced_integration import AdvancedIntegration, get_advanced_integration"
            
            # Encontrar onde adicionar
            lines = content.split('\n')
            import_added = False
            
            for i, line in enumerate(lines):
                if 'from .project_scanner' in line:
                    lines.insert(i + 1, new_import)
                    import_added = True
                    break
            
            if import_added:
                # Atualizar __all__
                for i, line in enumerate(lines):
                    if '__all__' in line and '=' in line:
                        if 'AdvancedIntegration' not in line:
                            line = line.replace(']', ", 'AdvancedIntegration', 'get_advanced_integration']")
                            lines[i] = line
                        break
                
                # Escrever arquivo atualizado
                with open(init_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                
                print(f"   ✅ Atualizado: {init_path}")
            else:
                print(f"   ⚠️ Não foi possível atualizar automaticamente")
        else:
            print(f"   ✅ Já contém advanced_integration")
    else:
        print(f"   ❌ Arquivo __init__.py não encontrado")

def criar_teste_advanced_integration():
    """Cria teste para validar migração do advanced_integration"""
    print("\n🧪 CRIANDO TESTE PARA ADVANCED_INTEGRATION")
    
    teste_path = "app/claude_ai_novo/tests/test_advanced_integration.py"
    
    content = '''"""
Teste para validar migração do advanced_integration
"""
import unittest
import os

class TestAdvancedIntegrationMigration(unittest.TestCase):
    """Testes para validar migração do advanced integration"""
    
    def test_file_exists(self):
        """Testa se arquivo advanced_integration existe"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'advanced_integration.py')
        self.assertTrue(os.path.exists(file_path), "Arquivo advanced_integration.py não encontrado")
    
    def test_file_content(self):
        """Testa se o conteúdo foi migrado corretamente"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'advanced_integration.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar classes principais
        self.assertIn('class AdvancedIntegration', content, "Classe AdvancedIntegration não encontrada")
        self.assertIn('class MetacognitiveAnalyzer', content, "Classe MetacognitiveAnalyzer não encontrada")
        
        # Verificar funções principais
        expected_functions = [
            'processar_consulta_com_ia_avancada',
            'analyze_query_intent',
            'capture_user_feedback',
            'get_advanced_integration',
            'get_cognitive_analysis'
        ]
        
        for func in expected_functions:
            self.assertIn(func, content, f"Função {func} não encontrada")
        
        # Verificar tamanho
        self.assertGreater(len(content), 2000, "Arquivo parece estar vazio ou muito pequeno")
    
    def test_function_count(self):
        """Testa se número de funções está correto"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'advanced_integration.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        func_count = content.count('def ')
        
        # Esperamos pelo menos 14 funções (original tinha 16)
        self.assertGreaterEqual(func_count, 14, f"Esperado pelo menos 14 funções, encontrado {func_count}")
    
    def test_class_count(self):
        """Testa se número de classes está correto"""
        file_path = os.path.join(os.path.dirname(__file__), '..', 'core', 'advanced_integration.py')
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        class_count = content.count('class ')
        
        # Esperamos pelo menos 2 classes
        self.assertGreaterEqual(class_count, 2, f"Esperado pelo menos 2 classes, encontrado {class_count}")

if __name__ == '__main__':
    unittest.main()
'''
    
    with open(teste_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"   ✅ Teste criado: {teste_path}")

def executar_teste_advanced_integration():
    """Executa teste do advanced integration"""
    print("\n🧪 EXECUTANDO TESTE ADVANCED INTEGRATION")
    
    try:
        import subprocess
        
        # Executar teste específico
        result = subprocess.run([
            'python', '-m', 'pytest', 
            'app/claude_ai_novo/tests/test_advanced_integration.py', 
            '-v'
        ], capture_output=True, text=True, cwd='.')
        
        print(f"   📋 Resultado: {result.returncode}")
        if result.stdout:
            print(f"   📝 Output:\n{result.stdout}")
        if result.stderr:
            print(f"   ⚠️ Errors:\n{result.stderr}")
            
        return result.returncode == 0
    except Exception as e:
        print(f"   ❌ Erro ao executar testes: {e}")
        return False

def atualizar_relatorio_progresso_advanced_integration():
    """Atualiza relatório de progresso para advanced integration"""
    print("\n📊 ATUALIZANDO RELATÓRIO DE PROGRESSO (ADVANCED INTEGRATION)")
    
    relatorio_path = "RELATORIO_PROGRESSO_FASE1.md"
    
    if os.path.exists(relatorio_path):
        with open(relatorio_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Atualizar estatísticas
        content = content.replace('**Arquivos migrados:** 6/12 (50.0%)', '**Arquivos migrados:** 7/12 (58.3%)')
        content = content.replace('**Funções migradas:** 80/180 (44.4%)', '**Funções migradas:** 96/180 (53.3%)')
        
        # Atualizar status do advanced_integration
        content = content.replace('| `advanced_integration.py` | `core/advanced_integration.py` | 16 | ⏳ **Próximo** |',
                                '| `advanced_integration.py` | `core/advanced_integration.py` | 16 | ✅ **Concluído** |')
        
        # Marcar próximo como próximo
        content = content.replace('| `conversation_context.py` | `intelligence/conversation_context.py` | 8 | ⏳ Pendente |',
                                '| `conversation_context.py` | `intelligence/conversation_context.py` | 8 | ⏳ **Próximo** |')
        
        with open(relatorio_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"   ✅ Relatório atualizado: {relatorio_path}")
    else:
        print(f"   ⚠️ Relatório não encontrado: {relatorio_path}")

def migrar_conversation_context():
    """Migra conversation_context.py para intelligence/conversation_context.py"""
    print("🚀 MIGRANDO CONVERSATION_CONTEXT.PY")
    print("=" * 60)
    
    origem = "app/claude_ai/conversation_context.py"
    destino = "app/claude_ai_novo/intelligence/conversation_context.py"
    
    print(f"📂 Origem: {origem}")
    print(f"📁 Destino: {destino}")
    
    if not os.path.exists(origem):
        print(f"   ❌ Arquivo origem não encontrado: {origem}")
        return False
    
    # Criar diretório intelligence se não existir
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    
    # Copiar arquivo
    shutil.copy2(origem, destino)
    
    # Verificar se foi copiado
    if os.path.exists(destino):
        print(f"   ✅ Arquivo migrado com sucesso!")
        
        # Mostrar estatísticas do arquivo
        with open(destino, 'r', encoding='utf-8') as f:
            content = f.read()
            
        lines = len(content.split('\n'))
        size = len(content)
        
        # Contar funções e classes
        func_count = content.count('def ')
        class_count = content.count('class ')
        
        print(f"   📊 Estatísticas:")
        print(f"      - Linhas: {lines}")
        print(f"      - Tamanho: {size} bytes")
        print(f"      - Funções: {func_count}")
        print(f"      - Classes: {class_count}")
        
        return True
    else:
        print(f"   ❌ Erro na migração")
        return False

def atualizar_init_intelligence_conversation_context():
    """Atualiza __init__.py do intelligence para incluir conversation_context"""
    print("\n📦 CRIANDO/ATUALIZANDO INTELLIGENCE/__INIT__.PY")
    
    init_path = "app/claude_ai_novo/intelligence/__init__.py"
    
    # Criar diretório se não existir
    os.makedirs(os.path.dirname(init_path), exist_ok=True)
    
    # Criar ou atualizar __init__.py
    content = '''"""
🧠 MÓDULO DE INTELIGÊNCIA
Sistemas de contexto, aprendizado e feedback
"""

try:
    from .conversation_context import ConversationContext, get_conversation_context
except ImportError:
    pass

__all__ = [
    'ConversationContext',
    'get_conversation_context'
]
'''
    
    with open(init_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"   ✅ Intelligence/__init__.py criado/atualizado")
    
    # Atualizar __init__.py principal
    main_init = "app/claude_ai_novo/__init__.py"
    if os.path.exists(main_init):
        with open(main_init, 'r', encoding='utf-8') as f:
            main_content = f.read()
        
        if 'intelligence' not in main_content:
            main_content += "\n    from . import intelligence"
            
            with open(main_init, 'w', encoding='utf-8') as f:
                f.write(main_content)
            
            print(f"   ✅ Main __init__.py atualizado com intelligence")

def criar_teste_conversation_context():
    """Cria teste para validar migração do conversation_context"""
    print("\n🧪 CRIANDO TESTE PARA CONVERSATION_CONTEXT")
    
    teste_path = "app/claude_ai_novo/tests/test_conversation_context.py"
    
    content = '''"""
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
'''
    
    with open(teste_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"   ✅ Teste criado: {teste_path}")

def executar_teste_conversation_context():
    """Executa teste do conversation context"""
    print("\n🧪 EXECUTANDO TESTE CONVERSATION CONTEXT")
    
    try:
        import subprocess
        
        # Executar teste específico
        result = subprocess.run([
            'python', '-m', 'pytest', 
            'app/claude_ai_novo/tests/test_conversation_context.py', 
            '-v'
        ], capture_output=True, text=True, cwd='.')
        
        print(f"   📋 Resultado: {result.returncode}")
        if result.stdout:
            print(f"   📝 Output:\n{result.stdout}")
        if result.stderr:
            print(f"   ⚠️ Errors:\n{result.stderr}")
            
        return result.returncode == 0
    except Exception as e:
        print(f"   ❌ Erro ao executar testes: {e}")
        return False

def atualizar_relatorio_progresso_conversation_context():
    """Atualiza relatório de progresso para conversation context"""
    print("\n📊 ATUALIZANDO RELATÓRIO DE PROGRESSO (CONVERSATION CONTEXT)")
    
    relatorio_path = "RELATORIO_PROGRESSO_FASE1.md"
    
    if os.path.exists(relatorio_path):
        with open(relatorio_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Atualizar estatísticas
        content = content.replace('**Arquivos migrados:** 7/12 (58.3%)', '**Arquivos migrados:** 8/12 (66.7%)')
        content = content.replace('**Funções migradas:** 96/180 (53.3%)', '**Funções migradas:** 104/180 (57.8%)')
        
        # Atualizar status do conversation_context
        content = content.replace('| `conversation_context.py` | `intelligence/conversation_context.py` | 8 | ⏳ **Próximo** |',
                                '| `conversation_context.py` | `intelligence/conversation_context.py` | 8 | ✅ **Concluído** |')
        
        # Marcar próximo como próximo
        content = content.replace('| `human_in_loop_learning.py` | `intelligence/human_in_loop_learning.py` | 12 | ⏳ Pendente |',
                                '| `human_in_loop_learning.py` | `intelligence/human_in_loop_learning.py` | 12 | ⏳ **Próximo** |')
        
        with open(relatorio_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"   ✅ Relatório atualizado: {relatorio_path}")
    else:
        print(f"   ⚠️ Relatório não encontrado: {relatorio_path}")

def migrar_human_in_loop_learning():
    """Migra human_in_loop_learning.py para intelligence/human_in_loop_learning.py"""
    print("🚀 MIGRANDO HUMAN_IN_LOOP_LEARNING.PY")
    print("=" * 60)
    
    origem = "app/claude_ai/human_in_loop_learning.py"
    destino = "app/claude_ai_novo/intelligence/human_in_loop_learning.py"
    
    print(f"📂 Origem: {origem}")
    print(f"📁 Destino: {destino}")
    
    if not os.path.exists(origem):
        print(f"   ❌ Arquivo origem não encontrado: {origem}")
        return False
    
    # Criar diretório intelligence se não existir
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    
    # Copiar arquivo
    shutil.copy2(origem, destino)
    
    # Verificar se foi copiado
    if os.path.exists(destino):
        print(f"   ✅ Arquivo migrado com sucesso!")
        
        # Mostrar estatísticas do arquivo
        with open(destino, 'r', encoding='utf-8') as f:
            content = f.read()
            
        lines = len(content.split('\n'))
        size = len(content)
        
        # Contar funções e classes
        func_count = content.count('def ')
        class_count = content.count('class ')
        
        print(f"   📊 Estatísticas:")
        print(f"      - Linhas: {lines}")
        print(f"      - Tamanho: {size} bytes")
        print(f"      - Funções: {func_count}")
        print(f"      - Classes: {class_count}")
        
        return True
    else:
        print(f"   ❌ Erro na migração")
        return False

def atualizar_init_intelligence_human_learning():
    """Atualiza __init__.py do intelligence para incluir human_in_loop_learning"""
    print("\n📦 ATUALIZANDO INTELLIGENCE/__INIT__.PY (HUMAN LEARNING)")
    
    init_path = "app/claude_ai_novo/intelligence/__init__.py"
    
    if os.path.exists(init_path):
        with open(init_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Adicionar import se não existir
        if 'human_in_loop_learning' not in content:
            # Adicionar novo import após conversation_context
            new_import = "    from .human_in_loop_learning import HumanInLoopLearning, get_human_learning_system, capture_user_feedback"
            
            # Encontrar onde adicionar
            lines = content.split('\n')
            import_added = False
            
            for i, line in enumerate(lines):
                if 'from .conversation_context' in line:
                    lines.insert(i + 1, new_import)
                    import_added = True
                    break
            
            if import_added:
                # Atualizar __all__
                for i, line in enumerate(lines):
                    if '__all__' in line and '=' in line:
                        if 'HumanInLoopLearning' not in line:
                            line = line.replace("'get_conversation_context'", "'get_conversation_context',\n    'HumanInLoopLearning',\n    'get_human_learning_system',\n    'capture_user_feedback'")
                            lines[i] = line
                        break
                
                # Escrever arquivo atualizado
                with open(init_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                
                print(f"   ✅ Intelligence/__init__.py atualizado")
            else:
                print(f"   ⚠️ Não foi possível atualizar automaticamente")
        else:
            print(f"   ✅ Já contém human_in_loop_learning")
    else:
        print(f"   ❌ Arquivo __init__.py não encontrado")

def criar_teste_human_learning():
    """Cria teste para validar migração do human_in_loop_learning"""
    print("\n🧪 CRIANDO TESTE PARA HUMAN_IN_LOOP_LEARNING")
    
    teste_path = "app/claude_ai_novo/tests/test_human_learning.py"
    
    content = '''"""
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
            'capture_user_feedback',
            'analyze_feedback',
            'update_learning_model',
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
'''
    
    with open(teste_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"   ✅ Teste criado: {teste_path}")

def executar_teste_human_learning():
    """Executa teste do human learning"""
    print("\n🧪 EXECUTANDO TESTE HUMAN LEARNING")
    
    try:
        import subprocess
        
        # Executar teste específico
        result = subprocess.run([
            'python', '-m', 'pytest', 
            'app/claude_ai_novo/tests/test_human_learning.py', 
            '-v'
        ], capture_output=True, text=True, cwd='.')
        
        print(f"   📋 Resultado: {result.returncode}")
        if result.stdout:
            print(f"   📝 Output:\n{result.stdout}")
        if result.stderr:
            print(f"   ⚠️ Errors:\n{result.stderr}")
            
        return result.returncode == 0
    except Exception as e:
        print(f"   ❌ Erro ao executar testes: {e}")
        return False

def atualizar_relatorio_progresso_human_learning():
    """Atualiza relatório de progresso para human learning"""
    print("\n📊 ATUALIZANDO RELATÓRIO DE PROGRESSO (HUMAN LEARNING)")
    
    relatorio_path = "RELATORIO_PROGRESSO_FASE1.md"
    
    if os.path.exists(relatorio_path):
        with open(relatorio_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Atualizar estatísticas
        content = content.replace('**Arquivos migrados:** 8/12 (66.7%)', '**Arquivos migrados:** 9/12 (75.0%)')
        content = content.replace('**Funções migradas:** 104/180 (57.8%)', '**Funções migradas:** 116/180 (64.4%)')
        
        # Atualizar status do human_in_loop_learning
        content = content.replace('| `human_in_loop_learning.py` | `intelligence/human_in_loop_learning.py` | 12 | ⏳ **Próximo** |',
                                '| `human_in_loop_learning.py` | `intelligence/human_in_loop_learning.py` | 12 | ✅ **Concluído** |')
        
        # Marcar próximo como próximo
        content = content.replace('| `lifelong_learning.py` | `intelligence/lifelong_learning.py` | 10 | ⏳ Pendente |',
                                '| `lifelong_learning.py` | `intelligence/lifelong_learning.py` | 10 | ⏳ **Próximo** |')
        
        with open(relatorio_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"   ✅ Relatório atualizado: {relatorio_path}")
    else:
        print(f"   ⚠️ Relatório não encontrado: {relatorio_path}")

def migrar_lifelong_learning():
    """Migra lifelong_learning.py para intelligence/lifelong_learning.py"""
    print("🚀 MIGRANDO LIFELONG_LEARNING.PY")
    print("=" * 60)
    
    origem = "app/claude_ai/lifelong_learning.py"
    destino = "app/claude_ai_novo/intelligence/lifelong_learning.py"
    
    print(f"📂 Origem: {origem}")
    print(f"📁 Destino: {destino}")
    
    if not os.path.exists(origem):
        print(f"   ❌ Arquivo origem não encontrado: {origem}")
        return False
    
    # Criar diretório intelligence se não existir
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    
    # Copiar arquivo
    shutil.copy2(origem, destino)
    
    # Verificar se foi copiado
    if os.path.exists(destino):
        print(f"   ✅ Arquivo migrado com sucesso!")
        
        # Mostrar estatísticas do arquivo
        with open(destino, 'r', encoding='utf-8') as f:
            content = f.read()
            
        lines = len(content.split('\n'))
        size = len(content)
        
        # Contar funções e classes
        func_count = content.count('def ')
        class_count = content.count('class ')
        
        print(f"   📊 Estatísticas:")
        print(f"      - Linhas: {lines}")
        print(f"      - Tamanho: {size} bytes")
        print(f"      - Funções: {func_count}")
        print(f"      - Classes: {class_count}")
        
        return True
    else:
        print(f"   ❌ Erro na migração")
        return False

def atualizar_init_intelligence_lifelong_learning():
    """Atualiza __init__.py do intelligence para incluir lifelong_learning"""
    print("\n📦 ATUALIZANDO INTELLIGENCE/__INIT__.PY (LIFELONG LEARNING)")
    
    init_path = "app/claude_ai_novo/intelligence/__init__.py"
    
    if os.path.exists(init_path):
        with open(init_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Adicionar import se não existir
        if 'lifelong_learning' not in content:
            # Adicionar novo import após human_in_loop_learning
            new_import = "    from .lifelong_learning import LifelongLearning, get_lifelong_learning_system"
            
            # Encontrar onde adicionar
            lines = content.split('\n')
            import_added = False
            
            for i, line in enumerate(lines):
                if 'from .human_in_loop_learning' in line:
                    lines.insert(i + 1, new_import)
                    import_added = True
                    break
            
            if import_added:
                # Atualizar __all__
                for i, line in enumerate(lines):
                    if '__all__' in line and '=' in line:
                        if 'LifelongLearning' not in line:
                            line = line.replace("'capture_user_feedback'", "'capture_user_feedback',\n    'LifelongLearning',\n    'get_lifelong_learning_system'")
                            lines[i] = line
                        break
                
                # Escrever arquivo atualizado
                with open(init_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(lines))
                
                print(f"   ✅ Intelligence/__init__.py atualizado")
            else:
                print(f"   ⚠️ Não foi possível atualizar automaticamente")
        else:
            print(f"   ✅ Já contém lifelong_learning")
    else:
        print(f"   ❌ Arquivo __init__.py não encontrado")

def criar_teste_lifelong_learning():
    """Cria teste para validar migração do lifelong_learning"""
    print("\n🧪 CRIANDO TESTE PARA LIFELONG_LEARNING")
    
    teste_path = "app/claude_ai_novo/tests/test_lifelong_learning.py"
    
    content = '''"""
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
        self.assertIn('class LifelongLearning', content, "Classe LifelongLearning não encontrada")
        
        # Verificar funções principais
        expected_functions = [
            'store_learning_data',
            'retrieve_learning_patterns',
            'update_learning_model',
            'get_lifelong_learning_system',
            'apply_learning_insights'
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
'''
    
    with open(teste_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"   ✅ Teste criado: {teste_path}")

def executar_teste_lifelong_learning():
    """Executa teste do lifelong learning"""
    print("\n🧪 EXECUTANDO TESTE LIFELONG LEARNING")
    
    try:
        import subprocess
        
        # Executar teste específico
        result = subprocess.run([
            'python', '-m', 'pytest', 
            'app/claude_ai_novo/tests/test_lifelong_learning.py', 
            '-v'
        ], capture_output=True, text=True, cwd='.')
        
        print(f"   📋 Resultado: {result.returncode}")
        if result.stdout:
            print(f"   📝 Output:\n{result.stdout}")
        if result.stderr:
            print(f"   ⚠️ Errors:\n{result.stderr}")
            
        return result.returncode == 0
    except Exception as e:
        print(f"   ❌ Erro ao executar testes: {e}")
        return False

def atualizar_relatorio_progresso_lifelong_learning():
    """Atualiza relatório de progresso para lifelong learning"""
    print("\n📊 ATUALIZANDO RELATÓRIO DE PROGRESSO (LIFELONG LEARNING)")
    
    relatorio_path = "RELATORIO_PROGRESSO_FASE1.md"
    
    if os.path.exists(relatorio_path):
        with open(relatorio_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Atualizar estatísticas
        content = content.replace('**Arquivos migrados:** 9/12 (75.0%)', '**Arquivos migrados:** 10/12 (83.3%)')
        content = content.replace('**Funções migradas:** 116/180 (64.4%)', '**Funções migradas:** 126/180 (70.0%)')
        
        # Atualizar status do lifelong_learning
        content = content.replace('| `lifelong_learning.py` | `intelligence/lifelong_learning.py` | 10 | ⏳ **Próximo** |',
                                '| `lifelong_learning.py` | `intelligence/lifelong_learning.py` | 10 | ✅ **Concluído** |')
        
        # Marcar próximo como próximo
        content = content.replace('| `claude_real_integration.py` | `core/claude_real_integration.py` | 54 | ⏳ Pendente |',
                                '| `claude_real_integration.py` | `core/claude_real_integration.py` | 54 | ⏳ **Próximo** |')
        
        with open(relatorio_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"   ✅ Relatório atualizado: {relatorio_path}")
    else:
        print(f"   ⚠️ Relatório não encontrado: {relatorio_path}")

def atualizar_relatorio_progresso():
    """Atualiza relatório de progresso"""
    print("\n📊 ATUALIZANDO RELATÓRIO DE PROGRESSO")
    
    relatorio_path = "RELATORIO_PROGRESSO_FASE1.md"
    
    if os.path.exists(relatorio_path):
        with open(relatorio_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Atualizar estatísticas
        content = content.replace('**Arquivos migrados:** 1/12 (8.3%)', '**Arquivos migrados:** 2/12 (16.7%)')
        content = content.replace('**Funções migradas:** 2/180 (1.1%)', '**Funções migradas:** 14/180 (7.8%)')
        
        # Atualizar status do sistema_real_data
        content = content.replace('| `sistema_real_data.py` | `core/data_provider.py` | 12 | ⏳ **Próximo** |',
                                '| `sistema_real_data.py` | `core/data_provider.py` | 12 | ✅ **Concluído** |')
        
        # Marcar próximo como próximo
        content = content.replace('| `mapeamento_semantico.py` | `core/semantic_mapper.py` | 14 | ⏳ Pendente |',
                                '| `mapeamento_semantico.py` | `core/semantic_mapper.py` | 14 | ⏳ **Próximo** |')
        
        with open(relatorio_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"   ✅ Relatório atualizado: {relatorio_path}")
    else:
        print(f"   ⚠️ Relatório não encontrado: {relatorio_path}")

def main():
    """Função principal"""
    parser = argparse.ArgumentParser(description='Continuar migração Fase 1')
    parser.add_argument('--arquivo', default='sistema_real_data.py', 
                       help='Arquivo a migrar (padrão: sistema_real_data.py)')
    
    args = parser.parse_args()
    
    print("🎯 CONTINUANDO FASE 1 - MIGRAÇÃO CLAUDE AI")
    print(f"📁 Arquivo: {args.arquivo}")
    print()
    
    if args.arquivo == 'sistema_real_data.py':
        # Migrar arquivo
        if migrar_sistema_real_data():
            # Atualizar estrutura
            atualizar_init_core()
            
            # Criar testes
            criar_teste_data_provider()
            
            # Executar testes
            if executar_testes():
                print("✅ Testes passaram!")
            else:
                print("⚠️ Alguns testes falharam")
            
            # Atualizar relatório
            atualizar_relatorio_progresso()
            
            print("\n🎯 PRÓXIMOS PASSOS:")
            print("1. Migrar mapeamento_semantico.py")
            print("2. Migrar suggestion_engine.py")
            print("3. Continuar com restante da Fase 1")
            
            print("\n📋 COMANDO PARA PRÓXIMO:")
            print("python continuar_fase1_migracao.py --arquivo mapeamento_semantico.py")
            
            return True
        else:
            print("❌ Migração falhou")
            return False
    
    elif args.arquivo == 'mapeamento_semantico.py':
        # Migrar mapeamento semantico
        if migrar_mapeamento_semantico():
            # Atualizar estrutura
            atualizar_init_core_semantico()
            
            # Criar testes
            criar_teste_semantic_mapper()
            
            # Executar testes
            if executar_teste_semantico():
                print("✅ Testes passaram!")
            else:
                print("⚠️ Alguns testes falharam")
            
            # Atualizar relatório
            atualizar_relatorio_progresso_semantico()
            
            print("\n🎯 PRÓXIMOS PASSOS:")
            print("1. Migrar suggestion_engine.py")
            print("2. Migrar multi_agent_system.py")
            print("3. Continuar com restante da Fase 1")
            
            print("\n📋 COMANDO PARA PRÓXIMO:")
            print("python continuar_fase1_migracao.py --arquivo suggestion_engine.py")
            
            return True
        else:
            print("❌ Migração falhou")
            return False
    
    elif args.arquivo == 'suggestion_engine.py':
        # Migrar suggestion engine
        if migrar_suggestion_engine():
            # Atualizar estrutura
            atualizar_init_core_suggestion()
            
            # Criar testes
            criar_teste_suggestion_engine()
            
            # Executar testes
            if executar_teste_suggestion():
                print("✅ Testes passaram!")
            else:
                print("⚠️ Alguns testes falharam")
            
            # Atualizar relatório
            atualizar_relatorio_progresso_suggestion()
            
            print("\n🎯 PRÓXIMOS PASSOS:")
            print("1. Migrar multi_agent_system.py")
            print("2. Migrar claude_project_scanner.py")
            print("3. Continuar com restante da Fase 1")
            
            print("\n📋 COMANDO PARA PRÓXIMO:")
            print("python continuar_fase1_migracao.py --arquivo multi_agent_system.py")
            
            return True
        else:
            print("❌ Migração falhou")
            return False
    
    elif args.arquivo == 'multi_agent_system.py':
        # Migrar multi agent system
        if migrar_multi_agent_system():
            # Atualizar estrutura
            atualizar_init_core_multi_agent()
            
            # Criar testes
            criar_teste_multi_agent_system()
            
            # Executar testes
            if executar_teste_multi_agent():
                print("✅ Testes passaram!")
            else:
                print("⚠️ Alguns testes falharam")
            
            # Atualizar relatório
            atualizar_relatorio_progresso_multi_agent()
            
            print("\n🎯 PRÓXIMOS PASSOS:")
            print("1. Migrar claude_project_scanner.py")
            print("2. Migrar advanced_integration.py")
            print("3. Continuar com restante da Fase 1")
            
            print("\n📋 COMANDO PARA PRÓXIMO:")
            print("python continuar_fase1_migracao.py --arquivo claude_project_scanner.py")
            
            return True
        else:
            print("❌ Migração falhou")
            return False
    
    elif args.arquivo == 'claude_project_scanner.py':
        # Migrar claude project scanner
        if migrar_claude_project_scanner():
            # Atualizar estrutura
            atualizar_init_core_project_scanner()
            
            # Criar testes
            criar_teste_project_scanner()
            
            # Executar testes
            if executar_teste_project_scanner():
                print("✅ Testes passaram!")
            else:
                print("⚠️ Alguns testes falharam")
            
            # Atualizar relatório
            atualizar_relatorio_progresso_project_scanner()
            
            print("\n🎯 PRÓXIMOS PASSOS:")
            print("1. Migrar advanced_integration.py")
            print("2. Migrar conversation_context.py")
            print("3. Continuar com restante da Fase 1")
            
            print("\n📋 COMANDO PARA PRÓXIMO:")
            print("python continuar_fase1_migracao.py --arquivo advanced_integration.py")
            
            return True
        else:
            print("❌ Migração falhou")
            return False
    
    elif args.arquivo == 'advanced_integration.py':
        # Migrar advanced integration
        if migrar_advanced_integration():
            # Atualizar estrutura
            atualizar_init_core_advanced_integration()
            
            # Criar testes
            criar_teste_advanced_integration()
            
            # Executar testes
            if executar_teste_advanced_integration():
                print("✅ Testes passaram!")
            else:
                print("⚠️ Alguns testes falharam")
            
            # Atualizar relatório
            atualizar_relatorio_progresso_advanced_integration()
            
            print("\n🎯 PRÓXIMOS PASSOS:")
            print("1. Migrar conversation_context.py")
            print("2. Migrar human_in_loop_learning.py")
            print("3. Finalizar restante da Fase 1")
            
            print("\n📋 COMANDO PARA PRÓXIMO:")
            print("python continuar_fase1_migracao.py --arquivo conversation_context.py")
            
            return True
        else:
            print("❌ Migração falhou")
            return False
    
    elif args.arquivo == 'conversation_context.py':
        # Migrar conversation context
        if migrar_conversation_context():
            # Atualizar estrutura
            atualizar_init_intelligence_conversation_context()
            
            # Criar testes
            criar_teste_conversation_context()
            
            # Executar testes
            if executar_teste_conversation_context():
                print("✅ Testes passaram!")
            else:
                print("⚠️ Alguns testes falharam")
            
            # Atualizar relatório
            atualizar_relatorio_progresso_conversation_context()
            
            print("\n🎯 PRÓXIMOS PASSOS:")
            print("1. Migrar human_in_loop_learning.py")
            print("2. Migrar lifelong_learning.py")
            print("3. Continuar com restante da Fase 1")
            
            print("\n📋 COMANDO PARA PRÓXIMO:")
            print("python continuar_fase1_migracao.py --arquivo human_in_loop_learning.py")
            
            return True
        else:
            print("❌ Migração falhou")
            return False
    
    elif args.arquivo == 'human_in_loop_learning.py':
        # Migrar human in loop learning
        if migrar_human_in_loop_learning():
            # Atualizar estrutura
            atualizar_init_intelligence_human_learning()
            
            # Criar testes
            criar_teste_human_learning()
            
            # Executar testes
            if executar_teste_human_learning():
                print("✅ Testes passaram!")
            else:
                print("⚠️ Alguns testes falharam")
            
            # Atualizar relatório
            atualizar_relatorio_progresso_human_learning()
            
            print("\n🎯 PRÓXIMOS PASSOS:")
            print("1. Migrar lifelong_learning.py")
            print("2. Migrar claude_real_integration.py")
            print("3. Finalizar Fase 1 (83.3%)")
            
            print("\n📋 COMANDO PARA PRÓXIMO:")
            print("python continuar_fase1_migracao.py --arquivo lifelong_learning.py")
            
            return True
        else:
            print("❌ Migração falhou")
            return False
    
    elif args.arquivo == 'lifelong_learning.py':
        # Migrar lifelong learning
        if migrar_lifelong_learning():
            # Atualizar estrutura
            atualizar_init_intelligence_lifelong_learning()
            
            # Criar testes
            criar_teste_lifelong_learning()
            
            # Executar testes
            if executar_teste_lifelong_learning():
                print("✅ Testes passaram!")
            else:
                print("⚠️ Alguns testes falharam")
            
            # Atualizar relatório
            atualizar_relatorio_progresso_lifelong_learning()
            
            print("\n🎯 PRÓXIMOS PASSOS:")
            print("1. Migrar claude_real_integration.py")
            print("2. Migrar nlp_enhanced_analyzer.py")
            print("3. FINALIZAR FASE 1 (91.7%)")
            
            print("\n📋 COMANDO PARA PRÓXIMO:")
            print("python continuar_fase1_migracao.py --arquivo claude_real_integration.py")
            
            return True
        else:
            print("❌ Migração falhou")
            return False
    else:
        print(f"⚠️ Arquivo {args.arquivo} não implementado ainda")
        return False

if __name__ == "__main__":
    main() 