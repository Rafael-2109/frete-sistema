#!/usr/bin/env python3
"""
FileCommands - Comandos especializados
"""

import os
import anthropic
import logging
import re
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta, date
from flask_login import current_user
from sqlalchemy import func, and_, or_, text
from app import db
import json
from app.utils.redis_cache import redis_cache, cache_aside, cached_query
from app.utils.grupo_empresarial import GrupoEmpresarialDetector, detectar_grupo_empresarial
from app.utils.ml_models_real import get_ml_models_system
import config_ai
from app.utils.api_helper import get_system_alerts
from app.utils.ai_logging import ai_logger, AILogger
from app.utils.redis_cache import intelligent_cache
import re
import time
import asyncio
import re
from app.utils.grupo_empresarial import GrupoEmpresarialDetector
from app import db
from app.fretes.models import Frete
from app.embarques.models import Embarque
from app.transportadoras.models import Transportadora
from app.pedidos.models import Pedido
from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
from app.faturamento.models import RelatorioFaturamentoImportado
from app import db
from app.monitoramento.models import EntregaMonitorada
from app import db
from app.fretes.models import Frete, DespesaExtra
from app.transportadoras.models import Transportadora
from app import db
from app.monitoramento.models import AgendamentoEntrega
from app import db
from app.monitoramento.models import EntregaMonitorada
from app.fretes.models import Frete
from app.utils.grupo_empresarial import detectar_grupo_empresarial
from app.utils.grupo_empresarial import detectar_grupo_empresarial
import re
from app import db
from app.monitoramento.models import EntregaMonitorada, AgendamentoEntrega
from app.embarques.models import Embarque, EmbarqueItem
from app.pedidos.models import Pedido
from app import db
from app.faturamento.models import RelatorioFaturamentoImportado
from app.monitoramento.models import EntregaMonitorada
from app.pedidos.models import Pedido
from app.utils.grupo_empresarial import GrupoEmpresarialDetector
import re
import re
import re
import re
from app import db
from app.fretes.models import Frete, DespesaExtra
from app.transportadoras.models import Transportadora
from app import db
from app.transportadoras.models import Transportadora
from app.fretes.models import Frete
from app import db
from app.pedidos.models import Pedido
from app import db
from app.embarques.models import Embarque, EmbarqueItem
from datetime import date
from app import db
from app.faturamento.models import RelatorioFaturamentoImportado as RelatorioImportado
from app import db
from app.fretes.models import DespesaExtra
# from app.monitoramento.models import PendenciaFinanceira  # Comentado temporariamente

# Configurar logger
logger = logging.getLogger(__name__)

class FileCommands:
    """Classe para comandos especializados"""
    
    def __init__(self, claude_client=None):
        self.client = claude_client
        
    def _is_file_command(self, consulta: str) -> bool:
        """Detecta comandos de leitura de arquivo"""
        comandos_arquivo = [
            # Comandos diretos
            'verificar', 'ver arquivo', 'ler arquivo', 'mostrar arquivo',
            'abrir arquivo', 'conteudo de', 'conteúdo de', 'código de',
            'listar arquivos', 'listar diretorio', 'listar diretório',
            
            # Referências a arquivos
            'routes.py', 'models.py', 'forms.py', '.html',
            'app/', 'app/carteira/', 'app/pedidos/', 'app/fretes/',
            
            # Perguntas sobre código
            'onde está', 'onde fica', 'qual arquivo', 'em que arquivo',
            'procurar função', 'buscar função', 'encontrar função'
        ]
        
        consulta_lower = consulta.lower()
        return any(cmd in consulta_lower for cmd in comandos_arquivo)
    def _processar_comando_arquivo(self, consulta: str, user_context: Optional[Dict] = None) -> str:
        """Processa comandos relacionados a arquivos"""
        logger.info("📁 Processando comando de arquivo...")
        
        if not self.project_scanner:
            return "❌ Sistema de descoberta de projeto não está disponível."
        
        consulta_lower = consulta.lower()
        
        # Detectar tipo de comando
        if any(term in consulta_lower for term in ['listar arquivo', 'listar diretorio', 'listar diretório']):
            # Comando de listagem
            import re
            # Tentar extrair caminho
            match = re.search(r'app/[\w/]+', consulta)
            if match:
                dir_path = match.group()
                # Remover 'app/' do início se presente
                if dir_path.startswith('app/'):
                    dir_path = dir_path[4:]
                result = self.project_scanner.list_directory_contents(dir_path)
            else:
                # Listar app/ por padrão
                result = self.project_scanner.list_directory_contents('')
            
            if 'error' not in result:
                resposta = f"📁 **Conteúdo de {result.get('path', 'app')}**\n\n"
                
                if result.get('directories'):
                    resposta += "📂 **Diretórios:**\n"
                    for dir in result['directories']:
                        resposta += f"  • {dir}/\n"
                
                if result.get('files'):
                    resposta += "\n📄 **Arquivos:**\n"
                    for file in result['files']:
                        resposta += f"  • {file['name']} ({file['size_kb']} KB)\n"
                
                resposta += f"\n📊 Total: {len(result.get('files', []))} arquivos, {len(result.get('directories', []))} diretórios"
                return resposta
            else:
                return f"❌ Erro ao listar diretório: {result['error']}"
        
        elif any(term in consulta_lower for term in ['buscar', 'procurar', 'encontrar']):
            # Comando de busca
            import re
            # Tentar extrair padrão de busca
            match = re.search(r'(buscar|procurar|encontrar)\s+["\']?([^"\']+)["\']?', consulta_lower)
            if match:
                pattern = match.group(2).strip()
                result = self.project_scanner.search_in_files(pattern)
                
                if result.get('success'):
                    if result['results']:
                        resposta = f"🔍 **Busca por '{pattern}'**\n\n"
                        resposta += f"Encontradas {result['total_matches']} ocorrências em {result['files_searched']} arquivos:\n\n"
                        
                        for i, match in enumerate(result['results'][:10], 1):
                            resposta += f"{i}. **{match['file']}** (linha {match['line_number']})\n"
                            resposta += f"   ```python\n   {match['line_content']}\n   ```\n"
                        
                        if result.get('truncated') or len(result['results']) > 10:
                            resposta += f"\n... e mais {result['total_matches'] - 10} resultados"
                        
                        return resposta
                    else:
                        return f"❌ Nenhuma ocorrência de '{pattern}' encontrada nos arquivos."
                else:
                    return f"❌ Erro na busca: {result.get('error', 'Erro desconhecido')}"
            else:
                return "❌ Não consegui identificar o que você quer buscar. Use: 'buscar nome_da_funcao' ou 'procurar texto_específico'"
        
        else:
            # Comando de leitura de arquivo
            import re
            # Tentar extrair caminho do arquivo
            # Padrões: app/carteira/routes.py, carteira/routes.py, routes.py
            patterns = [
                r'app/[\w/]+\.py',
                r'app/[\w/]+\.html',
                r'[\w/]+/[\w]+\.py',
                r'[\w]+\.py'
            ]
            
            file_path = None
            for pattern in patterns:
                match = re.search(pattern, consulta)
                if match:
                    file_path = match.group()
                    break
            
            if not file_path:
                # Tentar detectar módulo mencionado
                modulos = ['carteira', 'pedidos', 'fretes', 'embarques', 'monitoramento', 'transportadoras']
                for modulo in modulos:
                    if modulo in consulta_lower:
                        # Tentar adivinhar arquivo
                        if 'routes' in consulta_lower:
                            file_path = f'{modulo}/routes.py'
                        elif 'models' in consulta_lower:
                            file_path = f'{modulo}/models.py'
                        elif 'forms' in consulta_lower:
                            file_path = f'{modulo}/forms.py'
                        break
            
            if file_path:
                # Remover 'app/' do início se presente (project_scanner já assume app/)
                if file_path.startswith('app/'):
                    file_path = file_path[4:]
                
                # Ler arquivo completo (project_scanner não tem suporte a linhas específicas)
                content = self.project_scanner.read_file_content(file_path)
                
                if not content.startswith("❌"):
                    # Detectar linhas específicas solicitadas
                    line_match = re.search(r'linhas?\s+(\d+)(?:\s*[-a]\s*(\d+))?', consulta_lower)
                    
                    resposta = f"📄 **app/{file_path}**\n\n"
                    
                    if line_match:
                        # Mostrar apenas linhas específicas
                        start_line = int(line_match.group(1))
                        end_line = int(line_match.group(2)) if line_match.group(2) else start_line + 50
                        
                        lines = content.split('\n')
                        total_lines = len(lines)
                        
                        # Ajustar índices (converter de 1-based para 0-based)
                        start_idx = max(0, start_line - 1)
                        end_idx = min(total_lines, end_line)
                        
                        resposta += f"📍 Mostrando linhas {start_line}-{end_line} de {total_lines} totais\n\n"
                        resposta += "```python\n"
                        
                        # Adicionar linhas com números
                        for i in range(start_idx, end_idx):
                            if i < len(lines):
                                resposta += f"{i+1:4d}: {lines[i]}\n"
                        
                        resposta += "\n```\n"
                    else:
                        # Mostrar arquivo completo (limitado)
                        lines = content.split('\n')
                        total_lines = len(lines)
                        
                        if total_lines > 100:
                            # Mostrar apenas primeiras 100 linhas
                            resposta += f"📍 Arquivo grande ({total_lines} linhas). Mostrando primeiras 100 linhas.\n\n"
                            resposta += "```python\n"
                            for i in range(min(100, total_lines)):
                                resposta += f"{i+1:4d}: {lines[i]}\n"
                            resposta += "\n```\n"
                            resposta += f"\n💡 Use 'linhas X-Y' para ver trechos específicos."
                        else:
                            resposta += "```python\n"
                            resposta += content
                            resposta += "\n```\n"
                    
                    return resposta
                else:
                    return content  # Retornar mensagem de erro
            else:
                return """❓ Não consegui identificar o arquivo solicitado.

💡 **Dica:** Use formatos como:
- app/carteira/routes.py
- routes.py do carteira
- listar arquivos do carteira"""
    
    def _extrair_arquivo_da_consulta(self, consulta: str) -> Optional[str]:
        """Extrai nome do arquivo da consulta"""
        import re
        
        # Procurar por padrões de arquivo
        patterns = [
            r'app/[\w/]+\.py',
            r'[\w/]+\.py',
            r'[\w]+\.py'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, consulta)
            if match:
                return match.group(0)
        
        return None

# Instância global
_filecommands = None

def get_filecommands():
    """Retorna instância de FileCommands"""
    global _filecommands
    if _filecommands is None:
        _filecommands = FileCommands()
    return _filecommands
