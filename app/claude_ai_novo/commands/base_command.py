#!/usr/bin/env python3
"""
Commands Base - Framework completo para todos os commands
Versão otimizada com utilities avançadas e patterns comuns
"""

# Standard library
import os
import re
import json
import time
import logging
import asyncio
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Any, Union
from collections import defaultdict
from pathlib import Path

# Third-party imports
import anthropic
try:
    from flask_login import current_user
    FLASK_LOGIN_AVAILABLE = True
except ImportError:
    from unittest.mock import Mock
    current_user = Mock()
    FLASK_LOGIN_AVAILABLE = False
try:
    from sqlalchemy import func, and_, or_, text
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    func, and_, or_, text = None
    SQLALCHEMY_AVAILABLE = False

# Local imports
from app.claude_ai_novo.utils.flask_fallback import get_db, get_model
from app.claude_ai_novo.config import ClaudeAIConfig, AdvancedConfig

# Utils imports
from app.utils.redis_cache import redis_cache, cache_aside, cached_query, intelligent_cache
from app.utils.grupo_empresarial import GrupoEmpresarialDetector, detectar_grupo_empresarial
from app.utils.ml_models_real import get_ml_models_system
from app.utils.api_helper import get_system_alerts
from app.utils.ai_logging import ai_logger, AILogger

# Models imports
# from app.[a-z]+.models import .*Frete - Usando flask_fallback, DespesaExtra
# from app.[a-z]+.models import .*Embarque - Usando flask_fallbackItem
# from app.[a-z]+.models import .*Transportadora - Usando flask_fallback
# from app.[a-z]+.models import .*Pedido - Usando flask_fallback
# from app.[a-z]+.models import .*EntregaMonitorada - Usando flask_fallback, AgendamentoEntrega
# from app.[a-z]+.models import .*RelatorioFaturamentoImportado - Usando flask_fallback

logger = logging.getLogger(__name__)

class BaseCommand:

    @property
    def db(self):
        """Obtém db com fallback"""
        if not hasattr(self, "_db"):
            self._db = get_db()
        return self._db

    """Classe base avançada para todos os commands"""
    
    def __init__(self, claude_client=None):
        self.client = claude_client
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # Criar diretório de relatórios com fallback seguro para produção
        try:
            self.output_dir = Path("static/reports")
            self.output_dir.mkdir(exist_ok=True, parents=True)
        except (PermissionError, OSError) as e:
            # Fallback para ambientes sem permissão de escrita (Render, etc.)
            self.logger.warning(f"Não foi possível criar static/reports: {e}")
            # Usar diretório temporário
            import tempfile
            self.output_dir = Path(tempfile.gettempdir()) / "claude_reports"
            try:
                self.output_dir.mkdir(exist_ok=True, parents=True)
                self.logger.info(f"Usando diretório temporário: {self.output_dir}")
            except Exception as e2:
                self.logger.error(f"Erro ao criar diretório temporário: {e2}")
                # Último recurso - usar diretório atual
                self.output_dir = Path(".")
    
    # ==============================
    # VALIDAÇÃO E INPUT
    # ==============================
    
    def _validate_input(self, consulta: str) -> bool:
        """Valida entrada básica"""
        return bool(consulta and consulta.strip())
    
    def _sanitize_input(self, consulta: str) -> str:
        """Sanitiza entrada removendo caracteres problemáticos"""
        if not consulta:
            return ""
        # Remove caracteres especiais perigosos
        consulta = re.sub(r'[<>"\']', '', consulta)
        # Limita tamanho
        return consulta.strip()[:1000]
    
    def _extract_client_from_query(self, consulta: str) -> Optional[str]:
        """Extrai nome do cliente da consulta"""
        clientes_comuns = [
            'assai', 'atacadão', 'carrefour', 'tenda', 'mateus', 'coco bambu',
            'fort'
        ]
        
        consulta_lower = consulta.lower()
        for cliente in clientes_comuns:
            if cliente in consulta_lower:
                return cliente.title()
        
        # Busca padrões como "cliente X"
        match = re.search(r'\b(?:cliente|company|empresa)\s+([A-Za-z]+)', consulta_lower)
        if match:
            return match.group(1).title()
        
        return None
    
    def _extract_filters_advanced(self, consulta: str) -> Dict[str, Any]:
        """Extrai filtros avançados da consulta"""
        filtros = {}
        consulta_lower = consulta.lower()
        
        # Cliente
        cliente = self._extract_client_from_query(consulta)
        if cliente:
            filtros['cliente'] = cliente
        
        # Período temporal
        if 'hoje' in consulta_lower:
            filtros['periodo'] = 'hoje'
            filtros['data_inicio'] = datetime.now().date()
            filtros['data_fim'] = datetime.now().date()
        elif 'semana' in consulta_lower or 'últimos 7 dias' in consulta_lower:
            filtros['periodo'] = 'semana'
            filtros['data_inicio'] = datetime.now().date() - timedelta(days=7)
            filtros['data_fim'] = datetime.now().date()
        elif 'mês' in consulta_lower or 'mes' in consulta_lower or 'últimos 30 dias' in consulta_lower:
            filtros['periodo'] = 'mes'
            filtros['data_inicio'] = datetime.now().date() - timedelta(days=30)
            filtros['data_fim'] = datetime.now().date()
        
        # Status
        if 'pendente' in consulta_lower or 'em aberto' in consulta_lower:
            filtros['status'] = 'pendente'
        elif 'aprovado' in consulta_lower or 'confirmado' in consulta_lower:
            filtros['status'] = 'aprovado'
        elif 'entregue' in consulta_lower or 'finalizado' in consulta_lower:
            filtros['status'] = 'entregue'
        elif 'atrasado' in consulta_lower or 'vencido' in consulta_lower:
            filtros['status'] = 'atrasado'
        
        # Estados/UF
        estados = [
            'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA',
            'MT', 'MS', 'MG', 'PA', 'PB', 'PR', 'PE', 'PI', 'RJ', 'RN',
            'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO'
        ]
        for estado in estados:
            if f' {estado.lower()} ' in f' {consulta_lower} ' or f' {estado} ' in consulta:
                filtros['uf'] = estado
                break
        
        # Valores monetários
        valor_match = re.search(r'valor\s*(?:maior|acima|superior)\s*(?:de|que)?\s*r?\$?\s*([0-9.,]+)', consulta_lower)
        if valor_match:
            valor_str = valor_match.group(1).replace('.', '').replace(',', '.')
            try:
                filtros['valor_minimo'] = float(valor_str)
            except ValueError:
                pass
        
        return filtros
    
    # ==============================
    # LOGGING E ERROR HANDLING
    # ==============================
    
    def _log_command(self, consulta: str, command_type: str, filtros: Optional[Dict] = None):
        """Log avançado de comandos"""
        cliente = filtros.get('cliente', 'N/A') if filtros else 'N/A'
        periodo = filtros.get('periodo', 'N/A') if filtros else 'N/A'
        
        self.logger.info(
            f"🎯 {command_type} | Cliente: {cliente} | Período: {periodo} | "
            f"Query: {consulta[:50]}{'...' if len(consulta) > 50 else ''}"
        )
    
    def _handle_error(self, error: Exception, command_type: str, contexto: Optional[str] = None) -> str:
        """Tratamento avançado de erros"""
        erro_id = f"{command_type}_{int(time.time())}"
        
        self.logger.error(
            f"❌ [{erro_id}] {command_type} | Erro: {error} | Contexto: {contexto or 'N/A'}"
        )
        
        return f"""❌ **Erro no processamento {command_type}**

🔍 **ID do Erro:** {erro_id}
⚠️ **Descrição:** {error}
📋 **Contexto:** {contexto or 'Informação não disponível'}

💡 **Sugestões:**
• Verifique se os dados estão disponíveis
• Tente reformular a consulta
• Contacte o suporte com o ID do erro

---
🕒 {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
    
    # ==============================
    # CACHE E PERFORMANCE
    # ==============================
    
    def _get_cached_result(self, cache_key: str, ttl: int = 300) -> Optional[Any]:
        """Busca resultado em cache"""
        try:
            if hasattr(intelligent_cache, 'get'):
                if REDIS_AVAILABLE and intelligent_cache:
                return
            intelligent_cache.get(cache_key)
            elif hasattr(redis_cache, 'get'):
                return if REDIS_AVAILABLE and redis_cache:
            redis_cache.get(cache_key)
        except Exception as e:
            self.logger.warning(f"Erro ao buscar cache: {e}")
        return None
    
    def _set_cached_result(self, cache_key: str, data: Any, ttl: int = 300) -> bool:
        """Armazena resultado em cache"""
        try:
            if hasattr(intelligent_cache, 'set'):
                # if REDIS_AVAILABLE and intelligent_cache:
            intelligent_cache.set com categoria e ttl corretos
                try:
                    if REDIS_AVAILABLE and intelligent_cache:
            intelligent_cache.set(cache_key, data, "command_cache", ttl)
                except TypeError:
                    # Fallback se a interface for diferente
                    if REDIS_AVAILABLE and intelligent_cache:
            intelligent_cache.set(cache_key, data)
                return True
            elif hasattr(redis_cache, 'set'):
                if REDIS_AVAILABLE and redis_cache:
            redis_cache.set(cache_key, data, ttl)
                return True
        except Exception as e:
            self.logger.warning(f"Erro ao salvar cache: {e}")
        return False
    
    def _generate_cache_key(self, command_type: str, consulta: str, filtros: Optional[Dict] = None) -> str:
        """Gera chave de cache única"""
        base = f"{command_type}:{consulta[:50]}"
        if filtros:
            filtros_str = ":".join([f"{k}={v}" for k, v in sorted(filtros.items())])
            base += f":{filtros_str}"
        return base.replace(" ", "_").lower()
    
    # ==============================
    # FORMATAÇÃO E TEMPLATES
    # ==============================
    
    def _format_currency(self, valor: Union[int, float]) -> str:
        """Formata valor monetário"""
        try:
            return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        except (ValueError, TypeError):
            return "R$ 0,00"
    
    def _format_percentage(self, valor: Union[int, float], decimais: int = 1) -> str:
        """Formata porcentagem"""
        try:
            return f"{float(valor):.{decimais}f}%"
        except (ValueError, TypeError):
            return "0%"
    
    def _format_weight(self, peso: Union[int, float]) -> str:
        """Formata peso"""
        try:
            peso_float = float(peso)
            if peso_float >= 1000:
                return f"{peso_float/1000:.1f}t"
            return f"{peso_float:.1f}kg"
        except (ValueError, TypeError):
            return "0kg"
    
    def _format_date_br(self, data: Optional[datetime]) -> str:
        """Formata data em formato brasileiro"""
        if data:
            return data.strftime('%d/%m/%Y')
        return "N/A"
    
    def _create_summary_stats(self, dados: List[Any], tipo: str) -> Dict[str, Any]:
        """Cria estatísticas resumidas"""
        if not dados:
            return {'total': 0, 'tipo': tipo}
        
        stats = {
            'total': len(dados),
            'tipo': tipo,
            'data_analise': datetime.now().strftime('%d/%m/%Y %H:%M')
        }
        
        # Estatísticas específicas por tipo
        if tipo == 'fretes':
            valores_cotados = [float(getattr(item, 'valor_cotado', 0) or 0) for item in dados]
            valores_considerados = [float(getattr(item, 'valor_considerado', 0) or 0) for item in dados]
            
            stats.update({
                'valor_total_cotado': sum(valores_cotados),
                'valor_total_considerado': sum(valores_considerados),
                'valor_medio_cotado': sum(valores_cotados) / len(valores_cotados) if valores_cotados else 0,
                'economia_total': sum(valores_cotados) - sum(valores_considerados)
            })
        
        elif tipo == 'pedidos':
            valores = [float(getattr(item, 'valor_pedido', 0) or 0) for item in dados]
            pesos = [float(getattr(item, 'peso_total', 0) or 0) for item in dados]
            
            stats.update({
                'valor_total': sum(valores),
                'peso_total': sum(pesos),
                'valor_medio': sum(valores) / len(valores) if valores else 0,
                'peso_medio': sum(pesos) / len(pesos) if pesos else 0
            })
        
        elif tipo == 'entregas':
            entregues = sum(1 for item in dados if getattr(item, 'entregue', False))
            stats.update({
                'entregues': entregues,
                'pendentes': len(dados) - entregues,
                'taxa_entrega': (entregues / len(dados)) * 100 if dados else 0
            })
        
        return stats

# Utilities globais
def format_response(content: str, command_type: str = "command") -> str:
    """Formata resposta simples com footer básico"""
    footer = f"""
---
🤖 **{command_type}**
🕒 {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
    
    return content + footer

def format_response_advanced(content: str, command_type: str, stats: Optional[Dict] = None) -> str:
    """Formata resposta avançada com estatísticas"""
    footer = f"""
---
🤖 **{command_type} - Claude 4 Sonnet**"""
    
    if stats:
        footer += f"""
📊 **Estatísticas:** {stats.get('total', 0)} registros processados"""
    
    footer += f"""
🕒 {datetime.now().strftime('%d/%m/%Y %H:%M')}"""
    
    return content + footer

def create_excel_summary(dados: List[Any], tipo: str, filtros: Optional[Dict] = None) -> str:
    """Cria resumo para Excel baseado nos dados"""
    if not dados:
        return f"⚠️ **Nenhum {tipo} encontrado** para os critérios especificados."
    
    base_cmd = BaseCommand()
    stats = base_cmd._create_summary_stats(dados, tipo)
    
    resumo = f"""📊 **Relatório de {tipo.title()} Gerado com Sucesso!**

📋 **Detalhes:**
• **Registros:** {stats['total']}
• **Data/Hora:** {stats['data_analise']}"""
    
    if filtros:
        resumo += f"""
• **Filtros aplicados:** {', '.join([f"{k}={v}" for k, v in filtros.items()])}"""
    
    # Estatísticas específicas
    if tipo == 'fretes' and 'valor_total_cotado' in stats:
        resumo += f"""

📈 **Resumo Financeiro:**
• **Valor cotado:** {base_cmd._format_currency(stats['valor_total_cotado'])}
• **Valor considerado:** {base_cmd._format_currency(stats['valor_total_considerado'])}
• **Economia total:** {base_cmd._format_currency(stats['economia_total'])}
• **Valor médio:** {base_cmd._format_currency(stats['valor_medio_cotado'])}"""
    
    elif tipo == 'pedidos' and 'valor_total' in stats:
        resumo += f"""

📈 **Resumo Geral:**
• **Valor total:** {base_cmd._format_currency(stats['valor_total'])}
• **Peso total:** {base_cmd._format_weight(stats['peso_total'])}
• **Valor médio:** {base_cmd._format_currency(stats['valor_medio'])}
• **Peso médio:** {base_cmd._format_weight(stats['peso_medio'])}"""
    
    elif tipo == 'entregas' and 'entregues' in stats:
        resumo += f"""

📈 **Performance de Entregas:**
• **Entregues:** {stats['entregues']}
• **Pendentes:** {stats['pendentes']}
• **Taxa de entrega:** {base_cmd._format_percentage(stats['taxa_entrega'])}"""
    
    return resumo

def detect_command_type(consulta: str) -> str:
    """Detecta tipo de comando baseado na consulta"""
    consulta_lower = consulta.lower()
    
    # Excel commands
    excel_keywords = ['excel', 'planilha', 'exportar', 'relatório', 'xls', 'xlsx']
    if any(kw in consulta_lower for kw in excel_keywords):
        return 'excel'
    
    # File commands
    file_keywords = ['ver arquivo', 'ler arquivo', 'mostrar arquivo', 'listar arquivos']
    if any(kw in consulta_lower for kw in file_keywords):
        return 'file'
    
    # Dev commands
    dev_keywords = ['criar módulo', 'desenvolver', 'programar', 'código para']
    if any(kw in consulta_lower for kw in dev_keywords):
        return 'dev'
    
    # Cursor commands
    cursor_keywords = ['cursor mode', 'ativar cursor', 'analisar código']
    if any(kw in consulta_lower for kw in cursor_keywords):
        return 'cursor'
    
    return 'general'

# Exports organizados
__all__ = [
    # Classes
    'BaseCommand',
    
    # Functions
    'format_response',
    'format_response_advanced',
    'create_excel_summary', 
    'detect_command_type',
    
    # Utils
    'logging',
    'datetime',
    'current_user',
    
    # Config
    'ClaudeAIConfig',
    'AdvancedConfig',
    
    # Cache
    'intelligent_cache',
    'redis_cache'
]
