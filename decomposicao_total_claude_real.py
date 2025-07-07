#!/usr/bin/env python3
"""
Decomposição Total do claude_real_integration.py
Migração inteligente para arquitetura modular profissional
"""

import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Set, Any

class DecomposicaoTotal:
    """Classe para decomposição total do claude_real_integration.py"""
    
    def __init__(self):
        self.arquivo_origem = "app/claude_ai/claude_real_integration.py"
        self.destino_base = "app/claude_ai_novo"
        self.estrutura_modulos = {
            "core": ["claude_integration.py"],
            "commands": ["excel_commands.py", "dev_commands.py", "cursor_commands.py", "file_commands.py"],
            "data_loaders": ["database_loader.py", "context_loader.py"],
            "analyzers": ["query_analyzer.py", "intention_analyzer.py"],
            "processors": ["context_processor.py", "response_processor.py"],
            "utils": ["response_utils.py", "validation_utils.py"]
        }
        
        self.mapeamento_funcoes = {
            "core/claude_integration.py": [
                "class ClaudeRealIntegration",
                "def __init__",
                "def set_enhanced_claude",
                "def processar_consulta_real",
                "def _processar_consulta_padrao",
                "def _processar_com_reflexao_avancada",
                "def _fallback_simulado"
            ],
            "commands/excel_commands.py": [
                "def _is_excel_command",
                "def _processar_comando_excel"
            ],
            "commands/dev_commands.py": [
                "def _is_dev_command",
                "def _processar_comando_desenvolvimento"
            ],
            "commands/cursor_commands.py": [
                "def _is_cursor_command",
                "def _processar_comando_cursor"
            ],
            "commands/file_commands.py": [
                "def _is_file_command",
                "def _processar_comando_arquivo",
                "def _extrair_arquivo_da_consulta"
            ],
            "data_loaders/database_loader.py": [
                "def _carregar_dados_entregas",
                "def _carregar_dados_fretes",
                "def _carregar_dados_pedidos",
                "def _carregar_dados_embarques",
                "def _carregar_dados_faturamento",
                "def _carregar_dados_transportadoras",
                "def _carregar_dados_financeiro",
                "def _carregar_entregas_banco",
                "def _carregar_fretes_banco",
                "def _carregar_agendamentos"
            ],
            "data_loaders/context_loader.py": [
                "def _carregar_contexto_inteligente",
                "def _carregar_todos_clientes_sistema"
            ],
            "analyzers/query_analyzer.py": [
                "def _analisar_consulta",
                "def _analisar_consulta_profunda"
            ],
            "analyzers/intention_analyzer.py": [
                "def _detectar_intencao_refinada",
                "def _deve_usar_sistema_avancado"
            ],
            "processors/context_processor.py": [
                "def _build_contexto_por_intencao",
                "def _descrever_contexto_carregado"
            ],
            "processors/response_processor.py": [
                "def _gerar_resposta_inicial",
                "def _avaliar_qualidade_resposta",
                "def _melhorar_resposta",
                "def _validar_resposta_final"
            ],
            "utils/response_utils.py": [
                "def _gerar_resposta_erro",
                "def _gerar_resposta_sucesso",
                "def _formatar_resultado_cursor",
                "def _formatar_analise_projeto",
                "def _formatar_status_cursor"
            ],
            "utils/validation_utils.py": [
                "def _verificar_prazo_entrega",
                "def _calcular_dias_atraso",
                "def _calcular_metricas_prazo",
                "def _calcular_estatisticas_especificas",
                "def _calcular_estatisticas_por_dominio",
                "def _obter_filtros_usuario"
            ]
        }
    
    def executar_decomposicao(self):
        """Executa a decomposição total"""
        print("🚀 INICIANDO DECOMPOSIÇÃO TOTAL DO CLAUDE_REAL_INTEGRATION.PY")
        print("=" * 80)
        
        # 1. Criar estrutura de diretórios
        self._criar_estrutura_diretorios()
        
        # 2. Ler arquivo original
        conteudo_original = self._ler_arquivo_original()
        
        # 3. Extrair imports e configurações globais
        imports_globais = self._extrair_imports_globais(conteudo_original)
        
        # 4. Extrair funções por módulo
        self._extrair_funcoes_por_modulo(conteudo_original, imports_globais)
        
        # 5. Criar arquivo principal (core)
        self._criar_arquivo_principal(conteudo_original, imports_globais)
        
        # 6. Criar arquivos de comandos
        self._criar_arquivos_comandos(conteudo_original, imports_globais)
        
        # 7. Criar data loaders
        self._criar_data_loaders(conteudo_original, imports_globais)
        
        # 8. Criar analyzers
        self._criar_analyzers(conteudo_original, imports_globais)
        
        # 9. Criar processors
        self._criar_processors(conteudo_original, imports_globais)
        
        # 10. Criar utils
        self._criar_utils(conteudo_original, imports_globais)
        
        # 11. Criar __init__.py em todos os módulos
        self._criar_init_files()
        
        # 12. Criar arquivo de integração
        self._criar_arquivo_integracao()
        
        # 13. Criar testes
        self._criar_testes_decomposicao()
        
        print("\n✅ DECOMPOSIÇÃO TOTAL CONCLUÍDA COM SUCESSO!")
        
    def _criar_estrutura_diretorios(self):
        """Cria estrutura de diretórios para os módulos"""
        print("\n📁 Criando estrutura de diretórios...")
        
        for modulo_dir in self.estrutura_modulos.keys():
            dir_path = Path(self.destino_base) / modulo_dir
            dir_path.mkdir(parents=True, exist_ok=True)
            print(f"   ✅ {modulo_dir}/")
    
    def _ler_arquivo_original(self) -> str:
        """Lê o arquivo original"""
        print("\n📖 Lendo arquivo original...")
        
        with open(self.arquivo_origem, 'r', encoding='utf-8') as f:
            conteudo = f.read()
        
        print(f"   ✅ {len(conteudo)} caracteres lidos")
        return conteudo
    
    def _extrair_imports_globais(self, conteudo: str) -> str:
        """Extrai imports globais"""
        print("\n📦 Extraindo imports globais...")
        
        # Extrair todas as linhas de import
        linhas = conteudo.split('\n')
        imports = []
        
        for linha in linhas:
            linha = linha.strip()
            if linha.startswith(('import ', 'from ')) and not linha.startswith('from .'):
                imports.append(linha)
        
        imports_str = '\n'.join(imports)
        print(f"   ✅ {len(imports)} imports extraídos")
        
        return imports_str
    
    def _extrair_funcoes_por_modulo(self, conteudo: str, imports: str):
        """Extrai funções organizadas por módulo"""
        print("\n🔧 Extraindo funções por módulo...")
        
        # Usar regex para extrair funções completas
        funcoes_extraidas = {}
        
        # Padrão para capturar funções completas
        padrao_funcao = r'(def\s+\w+.*?)(?=\n\s*def|\nclass|\n\n\w|\Z)'
        
        for match in re.finditer(padrao_funcao, conteudo, re.DOTALL):
            funcao_completa = match.group(1).strip()
            nome_funcao = re.match(r'def\s+(\w+)', funcao_completa).group(1)
            
            # Mapear função para o módulo correto
            for modulo, funcoes in self.mapeamento_funcoes.items():
                if any(f"def {nome_funcao}" in funcao for funcao in funcoes):
                    if modulo not in funcoes_extraidas:
                        funcoes_extraidas[modulo] = []
                    funcoes_extraidas[modulo].append(funcao_completa)
                    break
        
        self.funcoes_extraidas = funcoes_extraidas
        print(f"   ✅ {sum(len(v) for v in funcoes_extraidas.values())} funções extraídas")
    
    def _criar_arquivo_principal(self, conteudo: str, imports: str):
        """Cria arquivo principal (core)"""
        print("\n🏗️ Criando arquivo principal...")
        
        # Extrair a classe principal
        padrao_classe = r'(class ClaudeRealIntegration:.*?)(?=\n\s*def\s+\w+(?:\s*\(|\s*:)|\n\n\w|\Z)'
        match_classe = re.search(padrao_classe, conteudo, re.DOTALL)
        
        if match_classe:
            classe_principal = match_classe.group(1)
            
            # Criar conteúdo do arquivo principal
            conteudo_principal = f'''#!/usr/bin/env python3
"""
Claude Integration - Core
Classe principal da integração com Claude AI
"""

{imports}

# Imports dos módulos decompostos
from ..commands.excel_commands import ExcelCommands
from ..commands.dev_commands import DevCommands
from ..commands.cursor_commands import CursorCommands
from ..commands.file_commands import FileCommands
from ..data_loaders.database_loader import DatabaseLoader
from ..data_loaders.context_loader import ContextLoader
from ..analyzers.query_analyzer import QueryAnalyzer
from ..analyzers.intention_analyzer import IntentionAnalyzer
from ..processors.context_processor import ContextProcessor
from ..processors.response_processor import ResponseProcessor
from ..utils.response_utils import ResponseUtils
from ..utils.validation_utils import ValidationUtils

{classe_principal}

# Instância global para compatibilidade
_claude_integration = None

def get_claude_integration():
    """Retorna instância da integração Claude"""
    global _claude_integration
    if _claude_integration is None:
        _claude_integration = ClaudeRealIntegration()
    return _claude_integration

def processar_com_claude_real(consulta: str, user_context: dict = None) -> str:
    """Função de compatibilidade com o sistema existente"""
    integration = get_claude_integration()
    return integration.processar_consulta_real(consulta, user_context)
'''
            
            # Salvar arquivo
            arquivo_destino = Path(self.destino_base) / "core" / "claude_integration.py"
            with open(arquivo_destino, 'w', encoding='utf-8') as f:
                f.write(conteudo_principal)
            
            print(f"   ✅ Arquivo principal criado: {arquivo_destino}")
    
    def _criar_arquivos_comandos(self, conteudo: str, imports: str):
        """Cria arquivos de comandos"""
        print("\n⚡ Criando arquivos de comandos...")
        
        comandos = {
            "excel_commands.py": "ExcelCommands",
            "dev_commands.py": "DevCommands", 
            "cursor_commands.py": "CursorCommands",
            "file_commands.py": "FileCommands"
        }
        
        for arquivo, classe in comandos.items():
            modulo_key = f"commands/{arquivo}"
            
            if modulo_key in self.funcoes_extraidas:
                funcoes = self.funcoes_extraidas[modulo_key]
                
                conteudo_comando = f'''#!/usr/bin/env python3
"""
{classe} - Comandos especializados
"""

{imports}

class {classe}:
    """Classe para comandos especializados"""
    
    def __init__(self, claude_client=None):
        self.client = claude_client
        
{chr(10).join(["    " + f.replace("def ", "def ") for f in funcoes])}

# Instância global
_{classe.lower()} = None

def get_{classe.lower()}():
    """Retorna instância de {classe}"""
    global _{classe.lower()}
    if _{classe.lower()} is None:
        _{classe.lower()} = {classe}()
    return _{classe.lower()}
'''
                
                arquivo_destino = Path(self.destino_base) / "commands" / arquivo
                with open(arquivo_destino, 'w', encoding='utf-8') as f:
                    f.write(conteudo_comando)
                
                print(f"   ✅ {arquivo} criado")
    
    def _criar_data_loaders(self, conteudo: str, imports: str):
        """Cria data loaders"""
        print("\n💾 Criando data loaders...")
        
        loaders = {
            "database_loader.py": "DatabaseLoader",
            "context_loader.py": "ContextLoader"
        }
        
        for arquivo, classe in loaders.items():
            modulo_key = f"data_loaders/{arquivo}"
            
            if modulo_key in self.funcoes_extraidas:
                funcoes = self.funcoes_extraidas[modulo_key]
                
                conteudo_loader = f'''#!/usr/bin/env python3
"""
{classe} - Carregamento de dados
"""

{imports}

class {classe}:
    """Classe para carregamento de dados"""
    
    def __init__(self):
        pass
        
{chr(10).join(["    " + f for f in funcoes])}

# Instância global
_{classe.lower()} = None

def get_{classe.lower()}():
    """Retorna instância de {classe}"""
    global _{classe.lower()}
    if _{classe.lower()} is None:
        _{classe.lower()} = {classe}()
    return _{classe.lower()}
'''
                
                arquivo_destino = Path(self.destino_base) / "data_loaders" / arquivo
                with open(arquivo_destino, 'w', encoding='utf-8') as f:
                    f.write(conteudo_loader)
                
                print(f"   ✅ {arquivo} criado")
    
    def _criar_analyzers(self, conteudo: str, imports: str):
        """Cria analyzers"""
        print("\n🔍 Criando analyzers...")
        
        analyzers = {
            "query_analyzer.py": "QueryAnalyzer",
            "intention_analyzer.py": "IntentionAnalyzer"
        }
        
        for arquivo, classe in analyzers.items():
            modulo_key = f"analyzers/{arquivo}"
            
            if modulo_key in self.funcoes_extraidas:
                funcoes = self.funcoes_extraidas[modulo_key]
                
                conteudo_analyzer = f'''#!/usr/bin/env python3
"""
{classe} - Análise especializada
"""

{imports}

class {classe}:
    """Classe para análise especializada"""
    
    def __init__(self):
        pass
        
{chr(10).join(["    " + f for f in funcoes])}

# Instância global
_{classe.lower()} = None

def get_{classe.lower()}():
    """Retorna instância de {classe}"""
    global _{classe.lower()}
    if _{classe.lower()} is None:
        _{classe.lower()} = {classe}()
    return _{classe.lower()}
'''
                
                arquivo_destino = Path(self.destino_base) / "analyzers" / arquivo
                with open(arquivo_destino, 'w', encoding='utf-8') as f:
                    f.write(conteudo_analyzer)
                
                print(f"   ✅ {arquivo} criado")
    
    def _criar_processors(self, conteudo: str, imports: str):
        """Cria processors"""
        print("\n⚙️ Criando processors...")
        
        processors = {
            "context_processor.py": "ContextProcessor",
            "response_processor.py": "ResponseProcessor"
        }
        
        for arquivo, classe in processors.items():
            modulo_key = f"processors/{arquivo}"
            
            if modulo_key in self.funcoes_extraidas:
                funcoes = self.funcoes_extraidas[modulo_key]
                
                conteudo_processor = f'''#!/usr/bin/env python3
"""
{classe} - Processamento especializado
"""

{imports}

class {classe}:
    """Classe para processamento especializado"""
    
    def __init__(self):
        pass
        
{chr(10).join(["    " + f for f in funcoes])}

# Instância global
_{classe.lower()} = None

def get_{classe.lower()}():
    """Retorna instância de {classe}"""
    global _{classe.lower()}
    if _{classe.lower()} is None:
        _{classe.lower()} = {classe}()
    return _{classe.lower()}
'''
                
                arquivo_destino = Path(self.destino_base) / "processors" / arquivo
                with open(arquivo_destino, 'w', encoding='utf-8') as f:
                    f.write(conteudo_processor)
                
                print(f"   ✅ {arquivo} criado")
    
    def _criar_utils(self, conteudo: str, imports: str):
        """Cria utils"""
        print("\n🛠️ Criando utils...")
        
        utils = {
            "response_utils.py": "ResponseUtils",
            "validation_utils.py": "ValidationUtils"
        }
        
        for arquivo, classe in utils.items():
            modulo_key = f"utils/{arquivo}"
            
            if modulo_key in self.funcoes_extraidas:
                funcoes = self.funcoes_extraidas[modulo_key]
                
                conteudo_util = f'''#!/usr/bin/env python3
"""
{classe} - Utilitários especializados
"""

{imports}

class {classe}:
    """Classe para utilitários especializados"""
    
    def __init__(self):
        pass
        
{chr(10).join(["    " + f for f in funcoes])}

# Instância global
_{classe.lower()} = None

def get_{classe.lower()}():
    """Retorna instância de {classe}"""
    global _{classe.lower()}
    if _{classe.lower()} is None:
        _{classe.lower()} = {classe}()
    return _{classe.lower()}
'''
                
                arquivo_destino = Path(self.destino_base) / "utils" / arquivo
                with open(arquivo_destino, 'w', encoding='utf-8') as f:
                    f.write(conteudo_util)
                
                print(f"   ✅ {arquivo} criado")
    
    def _criar_init_files(self):
        """Cria arquivos __init__.py"""
        print("\n📦 Criando arquivos __init__.py...")
        
        for modulo_dir in self.estrutura_modulos.keys():
            init_path = Path(self.destino_base) / modulo_dir / "__init__.py"
            
            with open(init_path, 'w', encoding='utf-8') as f:
                f.write(f'''"""
{modulo_dir.title()} - Módulo {modulo_dir}
"""

# Imports automáticos para facilitar uso
__all__ = []
''')
            
            print(f"   ✅ {modulo_dir}/__init__.py")
    
    def _criar_arquivo_integracao(self):
        """Cria arquivo de integração principal"""
        print("\n🔗 Criando arquivo de integração...")
        
        conteudo_integracao = '''#!/usr/bin/env python3
"""
Claude AI - Integração Completa
Sistema integrado com arquitetura modular
"""

# Imports principais
from .core.claude_integration import ClaudeRealIntegration, get_claude_integration, processar_com_claude_real
from .commands.excel_commands import get_excelcommands
from .commands.dev_commands import get_devcommands
from .commands.cursor_commands import get_cursorcommands
from .commands.file_commands import get_filecommands
from .data_loaders.database_loader import get_databaseloader
from .data_loaders.context_loader import get_contextloader
from .analyzers.query_analyzer import get_queryanalyzer
from .analyzers.intention_analyzer import get_intentionanalyzer
from .processors.context_processor import get_contextprocessor
from .processors.response_processor import get_responseprocessor
from .utils.response_utils import get_responseutils
from .utils.validation_utils import get_validationutils

# Instância global integrada
_claude_ai_system = None

class ClaudeAISystem:
    """Sistema Claude AI Integrado"""
    
    def __init__(self):
        """Inicializa sistema completo"""
        self.integration = get_claude_integration()
        
        # Inicializar todos os módulos
        self.excel_commands = get_excelcommands()
        self.dev_commands = get_devcommands()
        self.cursor_commands = get_cursorcommands()
        self.file_commands = get_filecommands()
        self.database_loader = get_databaseloader()
        self.context_loader = get_contextloader()
        self.query_analyzer = get_queryanalyzer()
        self.intention_analyzer = get_intentionanalyzer()
        self.context_processor = get_contextprocessor()
        self.response_processor = get_responseprocessor()
        self.response_utils = get_responseutils()
        self.validation_utils = get_validationutils()
        
        print("🚀 Sistema Claude AI Modular inicializado com sucesso!")
    
    def processar_consulta(self, consulta: str, user_context: dict = None) -> str:
        """Processa consulta usando sistema modular"""
        return self.integration.processar_consulta_real(consulta, user_context)

def get_claude_ai_system():
    """Retorna sistema Claude AI integrado"""
    global _claude_ai_system
    if _claude_ai_system is None:
        _claude_ai_system = ClaudeAISystem()
    return _claude_ai_system

# Função de compatibilidade
def processar_consulta_modular(consulta: str, user_context: dict = None) -> str:
    """Função de compatibilidade com sistema existente"""
    system = get_claude_ai_system()
    return system.processar_consulta(consulta, user_context)

__all__ = [
    'ClaudeAISystem',
    'get_claude_ai_system', 
    'processar_consulta_modular',
    'ClaudeRealIntegration',
    'get_claude_integration',
    'processar_com_claude_real'
]
'''
        
        arquivo_destino = Path(self.destino_base) / "claude_ai_modular.py"
        with open(arquivo_destino, 'w', encoding='utf-8') as f:
            f.write(conteudo_integracao)
        
        print(f"   ✅ claude_ai_modular.py criado")
    
    def _criar_testes_decomposicao(self):
        """Cria testes para a decomposição"""
        print("\n🧪 Criando testes para decomposição...")
        
        conteudo_teste = '''#!/usr/bin/env python3
"""
Testes da Decomposição Total
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_decomposicao_total():
    """Testa decomposição total"""
    print("🧪 TESTANDO DECOMPOSIÇÃO TOTAL")
    print("=" * 50)
    
    try:
        # Testar importação do sistema principal
        from app.claude_ai_novo.claude_ai_modular import get_claude_ai_system
        
        # Inicializar sistema
        system = get_claude_ai_system()
        
        print("✅ Sistema Claude AI Modular carregado com sucesso!")
        
        # Testar processamento básico
        resultado = system.processar_consulta("teste básico")
        print(f"✅ Processamento básico: {len(resultado)} caracteres")
        
        # Testar módulos individuais
        print("\\n📦 Testando módulos individuais:")
        
        modules = [
            'excel_commands', 'dev_commands', 'cursor_commands', 'file_commands',
            'database_loader', 'context_loader', 'query_analyzer', 'intention_analyzer',
            'context_processor', 'response_processor', 'response_utils', 'validation_utils'
        ]
        
        for module in modules:
            if hasattr(system, module):
                print(f"   ✅ {module}")
            else:
                print(f"   ❌ {module}")
        
        print("\\n🎯 DECOMPOSIÇÃO TOTAL VALIDADA!")
        return True
        
    except Exception as e:
        print(f"❌ Erro na decomposição: {e}")
        return False

if __name__ == "__main__":
    success = test_decomposicao_total()
    exit(0 if success else 1)
'''
        
        arquivo_teste = Path(self.destino_base) / "tests" / "test_decomposicao_total.py"
        with open(arquivo_teste, 'w', encoding='utf-8') as f:
            f.write(conteudo_teste)
        
        print(f"   ✅ test_decomposicao_total.py criado")

def executar_decomposicao_total():
    """Executa decomposição total"""
    decomposicao = DecomposicaoTotal()
    decomposicao.executar_decomposicao()

if __name__ == "__main__":
    executar_decomposicao_total() 