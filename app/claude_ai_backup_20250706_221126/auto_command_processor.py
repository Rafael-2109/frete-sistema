"""
🤖 AUTO COMMAND PROCESSOR - Processamento Automático de Comandos
Permite ao Claude AI usar automaticamente as APIs de autonomia durante conversas
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from .claude_code_generator import get_code_generator
from .security_guard import get_security_guard
import requests
from flask import current_app, url_for

logger = logging.getLogger(__name__)

class AutoCommandProcessor:
    """Processador automático de comandos para Claude AI"""
    
    def __init__(self):
        """Inicializa processador de comandos"""
        self.command_patterns = {
            'criar_modulo': [
                r'cri[ae] (?:um )?módulo (.+)',
                r'gera(?:r)? (?:um )?módulo (.+)',
                r'novo módulo (.+)',
                r'implementa(?:r)? módulo (.+)'
            ],
            'ler_arquivo': [
                r'l[eê] (?:o )?arquivo (.+)',
                r'mostra(?:r)? (?:o )?arquivo (.+)',
                r'ver (?:o )?arquivo (.+)',
                r'exibi(?:r)? (?:o )?arquivo (.+)'
            ],
            'descobrir_projeto': [
                r'descobr[ie]r? (?:o )?projeto',
                r'descobr[ie]r? projeto',
                r'descubra (?:o )?projeto',
                r'analisa(?:r)? (?:a )?estrutura',
                r'mape[ae]r? (?:o )?sistema',
                r'quais módulos (?:existem|tem)',
                r'projeto completo',
                r'estrutura do projeto'
            ],
            'inspecionar_banco': [
                r'inspeciona(?:r)? (?:o )?banco',
                r'verifica(?:r)? (?:o )?schema',
                r'mostra(?:r)? (?:as )?tabelas',
                r'esquema do banco'
            ],
            'listar_diretorio': [
                r'lista(?:r)? (?:o )?diretório (.+)',
                r'ver (?:a )?pasta (.+)',
                r'conteúdo (?:da pasta|do diretório) (.+)'
            ]
        }
        
        logger.info("🤖 Auto Command Processor inicializado")
    
    def detect_command(self, user_input: str) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Detecta comando automatizável na entrada do usuário
        Returns: (comando_detectado, parametros)
        """
        try:
            user_input_lower = user_input.lower().strip()
            
            for command, patterns in self.command_patterns.items():
                for pattern in patterns:
                    match = re.search(pattern, user_input_lower)
                    if match:
                        # Extrair parâmetros baseado no comando
                        params = self._extract_parameters(command, match, user_input)
                        logger.info(f"🎯 Comando detectado: {command} - {params}")
                        return command, params
            
            return None, {}
            
        except Exception as e:
            logger.error(f"❌ Erro na detecção de comando: {e}")
            return None, {}
    
    def _extract_parameters(self, command: str, match: re.Match, original_input: str) -> Dict[str, Any]:
        """Extrai parâmetros específicos do comando"""
        try:
            if command == 'criar_modulo':
                module_info = match.group(1).strip()
                
                # Tentar extrair campos se mencionados
                fields = []
                
                # Padrões para detectar campos
                field_patterns = [
                    r'com campos? (.+)',
                    r'tendo (.+)',
                    r'campos?: (.+)'
                ]
                
                for pattern in field_patterns:
                    field_match = re.search(pattern, original_input.lower())
                    if field_match:
                        field_text = field_match.group(1)
                        fields = self._parse_fields_from_text(field_text)
                        break
                
                # Se não encontrou campos, usar padrão básico
                if not fields:
                    fields = [
                        {'name': 'nome', 'type': 'string', 'nullable': False},
                        {'name': 'descricao', 'type': 'text', 'nullable': True},
                        {'name': 'ativo', 'type': 'boolean', 'nullable': False}
                    ]
                
                return {
                    'nome_modulo': module_info.replace(' ', '_').lower(),
                    'campos': fields
                }
            
            elif command == 'ler_arquivo':
                arquivo = match.group(1).strip()
                return {'arquivo': arquivo}
            
            elif command == 'listar_diretorio':
                diretorio = match.group(1).strip()
                return {'diretorio': diretorio}
            
            else:
                return {}
                
        except Exception as e:
            logger.error(f"❌ Erro ao extrair parâmetros: {e}")
            return {}
    
    def _parse_fields_from_text(self, field_text: str) -> List[Dict[str, Any]]:
        """Parse de campos a partir de texto natural"""
        try:
            fields = []
            
            # Padrões comuns de campos
            field_patterns = [
                (r'(\w+)\s*\((\w+)\)', lambda m: {'name': m.group(1), 'type': m.group(2), 'nullable': True}),
                (r'(\w+)\s*string', lambda m: {'name': m.group(1), 'type': 'string', 'nullable': True}),
                (r'(\w+)\s*text', lambda m: {'name': m.group(1), 'type': 'text', 'nullable': True}),
                (r'(\w+)\s*int', lambda m: {'name': m.group(1), 'type': 'integer', 'nullable': True}),
                (r'(\w+)\s*bool', lambda m: {'name': m.group(1), 'type': 'boolean', 'nullable': True}),
            ]
            
            for pattern, field_builder in field_patterns:
                matches = re.finditer(pattern, field_text.lower())
                for match in matches:
                    field = field_builder(match)
                    if field not in fields:
                        fields.append(field)
            
            # Se não encontrou nada, extrair palavras como campos string
            if not fields:
                words = re.findall(r'\b\w+\b', field_text)
                for word in words[:5]:  # Máximo 5 campos
                    if len(word) > 2:
                        fields.append({
                            'name': word.lower(),
                            'type': 'string',
                            'nullable': True
                        })
            
            return fields or [
                {'name': 'nome', 'type': 'string', 'nullable': False}
            ]
            
        except Exception as e:
            logger.error(f"❌ Erro ao parsear campos: {e}")
            return [{'name': 'nome', 'type': 'string', 'nullable': False}]
    
    def execute_command(self, command: str, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Executa comando automaticamente
        Returns: (sucesso, mensagem, dados)
        """
        try:
            # Verificar segurança primeiro
            security_guard = get_security_guard()
            
            # Mapear comando para função
            command_map = {
                'descobrir_projeto': self._execute_descobrir_projeto,
                'ler_arquivo': self._execute_ler_arquivo,
                'listar_diretorio': self._execute_listar_diretorio,
                'inspecionar_banco': self._execute_inspecionar_banco,
                'criar_modulo': self._execute_criar_modulo
            }
            
            if command not in command_map:
                return False, f"❌ Comando não suportado: {command}", {}
            
            # Executar comando
            return command_map[command](params)
            
        except Exception as e:
            logger.error(f"❌ Erro na execução do comando {command}: {e}")
            return False, f"❌ Erro interno: {e}", {}
    
    def _execute_descobrir_projeto(self, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Executa descoberta do projeto"""
        try:
            # Fazer requisição interna para API de descoberta
            from flask import current_app
            
            with current_app.test_request_context():
                from .routes import descobrir_projeto
                response = descobrir_projeto()
                
                # Verificar se response é dict diretamente ou tem atributo json
                if isinstance(response, dict):
                    data = response
                elif hasattr(response, 'json') and response.json:
                    data = response.json
                else:
                    data = {}
                
                if data.get('status') == 'success' and 'projeto' in data:
                    projeto = data['projeto']
                    resumo = f"""
🔍 **PROJETO DESCOBERTO**

📊 **Resumo:**
- **{projeto['total_modulos']} módulos** encontrados
- **{projeto['total_tabelas']} tabelas** no banco
- **{projeto['total_templates']} templates** disponíveis

🗂️ **Módulos Principais:**
{self._format_modules_summary(projeto['estrutura_modulos'])}

🗄️ **Tabelas do Banco:**
{', '.join(projeto['tabelas_banco'][:10])}{"..." if len(projeto['tabelas_banco']) > 10 else ""}
"""
                    return True, resumo, projeto
                else:
                    return False, f"❌ Erro: {data.get('message', 'Falha na descoberta')}", {}
            
        except Exception as e:
            logger.error(f"❌ Erro na descoberta do projeto: {e}")
            return False, f"❌ Erro interno: {e}", {}
    
    def _format_modules_summary(self, modules: Dict[str, Any]) -> str:
        """Formata resumo dos módulos"""
        summary_lines = []
        for name, info in list(modules.items())[:8]:  # Primeiros 8 módulos
            status_icons = []
            if info.get('tem_models'): status_icons.append('📋')
            if info.get('tem_forms'): status_icons.append('📝')
            if info.get('tem_routes'): status_icons.append('🌐')
            if info.get('tem_templates'): status_icons.append('🎨')
            
            summary_lines.append(f"- **{name}**: {' '.join(status_icons)}")
        
        return '\n'.join(summary_lines)
    
    def _execute_ler_arquivo(self, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Executa leitura de arquivo"""
        try:
            code_gen = get_code_generator()
            if not code_gen:
                return False, "❌ Gerador de código não disponível", {}
            
            arquivo = params.get('arquivo', '')
            conteudo = code_gen.read_file(arquivo)
            
            if conteudo.startswith('❌'):
                return False, conteudo, {}
            
            # Limitar conteúdo para apresentação
            preview = conteudo[:1000] + '\n...' if len(conteudo) > 1000 else conteudo
            
            resultado = f"""
📖 **ARQUIVO: {arquivo}**

```python
{preview}
```

📊 **Informações:**
- **Tamanho**: {len(conteudo):,} caracteres
- **Linhas**: {len(conteudo.split(chr(10))):,}
"""
            
            return True, resultado, {
                'arquivo': arquivo,
                'conteudo': conteudo,
                'tamanho': len(conteudo),
                'linhas': len(conteudo.split('\n'))
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na leitura do arquivo: {e}")
            return False, f"❌ Erro interno: {e}", {}
    
    def _execute_listar_diretorio(self, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Executa listagem de diretório"""
        try:
            code_gen = get_code_generator()
            if not code_gen:
                return False, "❌ Gerador de código não disponível", {}
            
            diretorio = params.get('diretorio', '')
            conteudo = code_gen.list_directory_contents(diretorio)
            
            if 'error' in conteudo:
                return False, f"❌ {conteudo['error']}", {}
            
            resultado = f"""
📁 **DIRETÓRIO: {conteudo.get('path', diretorio)}**

📂 **Subdiretórios ({len(conteudo['directories'])}):**
{', '.join(conteudo['directories']) if conteudo['directories'] else 'Nenhum'}

📄 **Arquivos ({len(conteudo['files'])}):**
"""
            
            for arquivo in conteudo['files'][:10]:  # Mostrar primeiros 10
                resultado += f"\n- **{arquivo['name']}** ({arquivo['tamanho_kb']:.1f}KB)"
            
            if len(conteudo['files']) > 10:
                resultado += f"\n... e mais {len(conteudo['files']) - 10} arquivos"
            
            return True, resultado, conteudo
            
        except Exception as e:
            logger.error(f"❌ Erro na listagem do diretório: {e}")
            return False, f"❌ Erro interno: {e}", {}
    
    def _execute_inspecionar_banco(self, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Executa inspeção do banco"""
        try:
            from flask import current_app
            
            with current_app.test_request_context():
                from .routes import inspecionar_banco
                response = inspecionar_banco()
                
                # Verificar se response é dict diretamente ou tem atributo json
                if isinstance(response, dict):
                    data = response
                elif hasattr(response, 'json') and response.json:
                    data = response.json
                else:
                    data = {}
                
                if data.get('status') == 'success' and 'esquema' in data:
                    esquema = data['esquema']
                    
                    resultado = f"""
🗄️ **BANCO DE DADOS INSPECIONADO**

📊 **Informações Gerais:**
- **Tipo**: {esquema['info_banco']['dialeto']}
- **Driver**: {esquema['info_banco']['driver']}
- **Tabelas**: {len(esquema['tabelas'])}

🗂️ **Tabelas Principais:**
"""
                    
                    for nome_tabela, info_tabela in list(esquema['tabelas'].items())[:8]:
                        if isinstance(info_tabela, dict) and 'colunas' in info_tabela:
                            num_colunas = len(info_tabela['colunas'])
                            num_fks = len(info_tabela.get('foreign_keys', []))
                            resultado += f"\n- **{nome_tabela}**: {num_colunas} colunas"
                            if num_fks > 0:
                                resultado += f", {num_fks} FK"
                    
                    return True, resultado, esquema
                else:
                    return False, f"❌ Erro: {data.get('message', 'Falha na inspeção')}", {}
            
        except Exception as e:
            logger.error(f"❌ Erro na inspeção do banco: {e}")
            return False, f"❌ Erro interno: {e}", {}
    
    def _execute_criar_modulo(self, params: Dict[str, Any]) -> Tuple[bool, str, Dict[str, Any]]:
        """Executa criação de módulo"""
        try:
            # Verificar segurança
            security_guard = get_security_guard()
            nome_modulo = params.get('nome_modulo', '')
            
            if security_guard:
                # Validar cada arquivo que será criado
                arquivos_para_criar = [
                    f"app/{nome_modulo}/models.py",
                    f"app/{nome_modulo}/forms.py", 
                    f"app/{nome_modulo}/routes.py",
                    f"app/{nome_modulo}/__init__.py",
                    f"app/templates/{nome_modulo}/form.html",
                    f"app/templates/{nome_modulo}/list.html"
                ]
                
                blocked_files = []
                pending_actions = []
                
                for arquivo in arquivos_para_criar:
                    allowed, reason, action_id = security_guard.validate_file_operation(
                        arquivo, 'CREATE_MODULE', 'Código gerado automaticamente'
                    )
                    
                    if not allowed:
                        if 'AGUARDANDO APROVAÇÃO' in reason:
                            pending_actions.append(action_id)
                        else:
                            blocked_files.append(f"{arquivo}: {reason}")
                
                if blocked_files:
                    return False, f"❌ Arquivos bloqueados pela segurança:\n" + '\n'.join(blocked_files), {}
                
                if pending_actions:
                    return False, f"⚠️ Criação de módulo pendente de aprovação.\n**Ações criadas**: {', '.join(pending_actions)}\n\nAguarde aprovação de um administrador.", {
                        'pending_actions': pending_actions,
                        'status': 'PENDING_APPROVAL'
                    }
            
            # Se chegou aqui, pode criar
            code_gen = get_code_generator()
            if not code_gen:
                return False, "❌ Gerador de código não disponível", {}
            
            arquivos_gerados = code_gen.generate_flask_module(
                params['nome_modulo'],
                params['campos']
            )
            
            arquivos_salvos = []
            for caminho_arquivo, conteudo in arquivos_gerados.items():
                if code_gen.write_file(caminho_arquivo, conteudo):
                    arquivos_salvos.append(caminho_arquivo)
            
            resultado = f"""
🚀 **MÓDULO CRIADO COM SUCESSO!**

📦 **Módulo**: {params['nome_modulo']}
📁 **Arquivos Criados**: {len(arquivos_salvos)}

✅ **Arquivos:**
{chr(10).join(f'- {arquivo}' for arquivo in arquivos_salvos)}

🎯 **Próximos Passos:**
1. Registrar blueprint no `__init__.py` principal
2. Executar migração do banco: `flask db migrate -m "Add {params['nome_modulo']}"`
3. Aplicar migração: `flask db upgrade`
"""
            
            return True, resultado, {
                'modulo': params['nome_modulo'],
                'arquivos_criados': arquivos_salvos,
                'campos': params['campos']
            }
            
        except Exception as e:
            logger.error(f"❌ Erro na criação do módulo: {e}")
            return False, f"❌ Erro interno: {e}", {}

# Instância global
auto_processor = None

def init_auto_processor() -> AutoCommandProcessor:
    """Inicializa o processador automático"""
    global auto_processor
    auto_processor = AutoCommandProcessor()
    return auto_processor

def get_auto_processor() -> Optional[AutoCommandProcessor]:
    """Retorna instância do processador automático"""
    return auto_processor 