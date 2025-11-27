"""
Serviço de Memória do Claude AI Lite.

Gerencia:
- Histórico de conversas por usuário
- Aprendizados permanentes (por usuário e globais)
- Formatação de contexto para o Claude

Atualizado: 26/11/2025 - Configurações dinâmicas via config.py
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# FUNÇÕES DE CONFIGURAÇÃO DINÂMICA
# =============================================================================

def _get_max_historico() -> int:
    """Retorna limite de histórico baseado na config."""
    try:
        from .config import get_max_historico
        return get_max_historico()
    except ImportError:
        return 40  # Fallback


def _get_max_tokens(modelo: str = "sonnet") -> int:
    """Retorna limite de tokens baseado no modelo."""
    try:
        from .config import get_max_tokens
        return get_max_tokens(modelo)
    except ImportError:
        return 8192  # Fallback


def _get_chars_por_token() -> int:
    """Retorna estimativa de chars por token."""
    try:
        from .config import get_config
        return get_config().memoria.chars_por_token
    except ImportError:
        return 4  # Fallback


# Constantes de fallback (mantidas para compatibilidade)
MAX_HISTORICO = 40
MAX_TOKENS_CONTEXTO = 8192
CHARS_POR_TOKEN = 4


class MemoryService:
    """Gerencia memória de conversas e aprendizados."""

    @staticmethod
    def registrar_mensagem(usuario_id: int, tipo: str, conteudo: str, metadados: dict = None):
        """
        Registra uma mensagem no histórico.

        Args:
            usuario_id: ID do usuário
            tipo: 'usuario', 'assistente', 'sistema', 'resultado'
            conteudo: Texto da mensagem
            metadados: Dados extras (intenção, entidades, etc)
        """
        try:
            from .models import ClaudeHistoricoConversa
            ClaudeHistoricoConversa.adicionar_mensagem(
                usuario_id=usuario_id,
                tipo=tipo,
                conteudo=conteudo,
                metadados=metadados
            )
            logger.debug(f"[MEMORY] Mensagem registrada para usuário {usuario_id}")
        except Exception as e:
            logger.error(f"[MEMORY] Erro ao registrar mensagem: {e}")

    @staticmethod
    def buscar_historico(usuario_id: int, limite: int = MAX_HISTORICO) -> List[Dict]:
        """
        Busca histórico de conversas do usuário.

        Returns:
            Lista de mensagens em ordem cronológica
        """
        try:
            from .models import ClaudeHistoricoConversa
            mensagens = ClaudeHistoricoConversa.buscar_historico(usuario_id, limite)
            return [m.to_dict() for m in mensagens]
        except Exception as e:
            logger.error(f"[MEMORY] Erro ao buscar histórico: {e}")
            return []

    @staticmethod
    def buscar_aprendizados(usuario_id: int = None, incluir_globais: bool = True) -> List[Dict]:
        """
        Busca aprendizados ativos.

        Args:
            usuario_id: ID do usuário (None = apenas globais)
            incluir_globais: Se deve incluir aprendizados globais

        Returns:
            Lista de aprendizados ordenados por prioridade
        """
        try:
            from .models import ClaudeAprendizado
            aprendizados = ClaudeAprendizado.buscar_aprendizados(usuario_id, incluir_globais)
            return [a.to_dict() for a in aprendizados]
        except Exception as e:
            logger.error(f"[MEMORY] Erro ao buscar aprendizados: {e}")
            return []

    @staticmethod
    def formatar_contexto_memoria(usuario_id: int, incluir_aprendizados: bool = True, modelo: str = "sonnet") -> str:
        """
        Formata todo o contexto de memória para enviar ao Claude.

        Inclui:
        1. Aprendizados permanentes (globais + usuário) - OPCIONAL
        2. Histórico recente de conversas

        Args:
            usuario_id: ID do usuário
            incluir_aprendizados: Se False, não carrega aprendizados (usar quando já cacheados)
            modelo: Modelo Claude em uso (para ajustar tokens)

        Returns:
            String formatada para incluir no system prompt
        """
        partes = []
        tokens_usados = 0

        # Usa configurações dinâmicas
        max_tokens = _get_max_tokens(modelo)
        chars_por_token = _get_chars_por_token()
        max_chars = max_tokens * chars_por_token

        # 1. APRENDIZADOS (prioridade máxima) - Opcional para evitar duplicação
        aprendizados = []
        if incluir_aprendizados:
            aprendizados = MemoryService.buscar_aprendizados(usuario_id, incluir_globais=True)

        if aprendizados:
            partes.append("=== CONHECIMENTO PERMANENTE ===")

            # Agrupa por categoria
            por_categoria = {}
            for a in aprendizados:
                cat = a['categoria']
                if cat not in por_categoria:
                    por_categoria[cat] = []
                por_categoria[cat].append(a)

            for categoria, items in por_categoria.items():
                partes.append(f"\n[{categoria.upper()}]")
                for item in items:
                    escopo = "(global)" if item['escopo'] == 'global' else "(seu)"
                    partes.append(f"- {item['valor']} {escopo}")

            partes.append("")

        # 2. HISTÓRICO DE CONVERSAS (usa limite dinâmico)
        max_historico = _get_max_historico()
        historico = MemoryService.buscar_historico(usuario_id, max_historico)

        if historico:
            partes.append("=== HISTÓRICO RECENTE DA CONVERSA ===")

            for msg in historico:
                tipo = msg['tipo']
                conteudo = msg['conteudo']

                # Trunca mensagens muito longas
                if len(conteudo) > 500:
                    conteudo = conteudo[:500] + "..."

                if tipo == 'usuario':
                    partes.append(f"USUÁRIO: {conteudo}")
                elif tipo == 'assistente':
                    partes.append(f"ASSISTENTE: {conteudo}")
                elif tipo == 'resultado':
                    # Resultados de busca são resumidos
                    partes.append(f"[Resultado de busca: {conteudo[:200]}...]")

                # Verifica limite de tokens
                texto_atual = "\n".join(partes)
                if len(texto_atual) > max_chars:
                    # Remove mensagens mais antigas até caber
                    partes = partes[:-1]
                    partes.append("... (histórico anterior omitido)")
                    break

            partes.append("")

        return "\n".join(partes) if partes else ""

    @staticmethod
    def extrair_ultimo_resultado(usuario_id: int) -> Optional[Dict]:
        """
        Extrai o último resultado de busca do histórico.
        Útil para referências como "esses pedidos", "pedido 2".
        """
        try:
            from .models import ClaudeHistoricoConversa

            ultimo = ClaudeHistoricoConversa.query.filter_by(
                usuario_id=usuario_id,
                tipo='resultado'
            ).order_by(
                ClaudeHistoricoConversa.criado_em.desc()
            ).first()

            if ultimo and ultimo.metadados:
                return ultimo.metadados

            return None
        except Exception as e:
            logger.error(f"[MEMORY] Erro ao extrair último resultado: {e}")
            return None

    @staticmethod
    def registrar_conversa_completa(
        usuario_id: int,
        pergunta: str,
        resposta: str,
        intencao: dict = None,
        resultado_busca: dict = None
    ):
        """
        Registra uma conversa completa (pergunta + resposta + resultado).
        Chamado após cada interação bem-sucedida.
        """
        try:
            from .models import ClaudeHistoricoConversa

            # Registra pergunta do usuário
            ClaudeHistoricoConversa.adicionar_mensagem(
                usuario_id=usuario_id,
                tipo='usuario',
                conteudo=pergunta,
                metadados={'intencao': intencao} if intencao else None
            )

            # Registra resultado da busca (se houver)
            if resultado_busca:
                # Salva apenas resumo do resultado para não ocupar muito espaço
                resumo = MemoryService._resumir_resultado(resultado_busca)
                ClaudeHistoricoConversa.adicionar_mensagem(
                    usuario_id=usuario_id,
                    tipo='resultado',
                    conteudo=resumo,
                    metadados=resultado_busca
                )

            # Registra resposta do assistente
            ClaudeHistoricoConversa.adicionar_mensagem(
                usuario_id=usuario_id,
                tipo='assistente',
                conteudo=resposta[:2000],  # Limita tamanho
                metadados=None
            )

            logger.info(f"[MEMORY] Conversa registrada para usuário {usuario_id}")

        except Exception as e:
            logger.error(f"[MEMORY] Erro ao registrar conversa: {e}")

    @staticmethod
    def _resumir_resultado(resultado: dict) -> str:
        """Resume um resultado de busca para armazenamento."""
        total = resultado.get('total_encontrado', 0)
        campo = resultado.get('campo_busca', '')
        valor = resultado.get('valor_buscado', '')

        if total == 0:
            return f"Busca por {campo}='{valor}': nenhum resultado"

        # Extrai lista de pedidos/produtos se houver
        dados = resultado.get('dados', [])
        if dados:
            if isinstance(dados, list):
                # Pega primeiros itens
                itens = []
                for i, item in enumerate(dados[:10], 1):
                    if isinstance(item, dict):
                        num = item.get('num_pedido') or item.get('cod_produto') or item.get('nome_produto', f'item_{i}')
                        itens.append(f"{i}. {num}")

                return f"Busca por {campo}='{valor}': {total} resultado(s) - {', '.join(itens)}"

        return f"Busca por {campo}='{valor}': {total} resultado(s)"

    @staticmethod
    def limpar_historico_usuario(usuario_id: int):
        """Limpa todo o histórico de um usuário."""
        try:
            from .models import ClaudeHistoricoConversa
            from app import db

            deletados = ClaudeHistoricoConversa.query.filter_by(
                usuario_id=usuario_id
            ).delete()

            db.session.commit()
            logger.info(f"[MEMORY] Histórico limpo para usuário {usuario_id}: {deletados} mensagens")
            return deletados
        except Exception as e:
            logger.error(f"[MEMORY] Erro ao limpar histórico: {e}")
            return 0

    @staticmethod
    def estatisticas_usuario(usuario_id: int) -> Dict:
        """Retorna estatísticas de memória do usuário."""
        try:
            from .models import ClaudeHistoricoConversa, ClaudeAprendizado
            from sqlalchemy import func

            # Conta mensagens
            total_mensagens = ClaudeHistoricoConversa.query.filter_by(
                usuario_id=usuario_id
            ).count()

            # Conta aprendizados do usuário
            aprendizados_usuario = ClaudeAprendizado.query.filter_by(
                usuario_id=usuario_id,
                ativo=True
            ).count()

            # Conta aprendizados globais
            aprendizados_globais = ClaudeAprendizado.query.filter_by(
                usuario_id=None,
                ativo=True
            ).count()

            return {
                'total_mensagens': total_mensagens,
                'aprendizados_usuario': aprendizados_usuario,
                'aprendizados_globais': aprendizados_globais,
                'max_historico': _get_max_historico(),
                'max_tokens': _get_max_tokens()
            }

        except Exception as e:
            logger.error(f"[MEMORY] Erro ao buscar estatísticas: {e}")
            return {}
