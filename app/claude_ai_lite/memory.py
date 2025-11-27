"""
Serviço de Memória do Claude AI Lite.

Gerencia:
- Histórico de conversas por usuário
- Aprendizados permanentes (por usuário e globais)
- Formatação de contexto para o Claude

v2.0 (27/11/2025):
- Busca por TEMPO (últimos 30min) ao invés de quantidade
- Agrupamento por INTERAÇÃO (nunca corta conversa pela metade)
- Detecção de INÍCIO DE CONVERSA por gap de inatividade
- Formatação inteligente para o Claude

Atualizado: 26/11/2025 - Configurações dinâmicas via config.py
Atualizado: 27/11/2025 - v2.0: Histórico inteligente por tempo/interação
"""

import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURAÇÕES DO HISTÓRICO v2
# =============================================================================

HISTORICO_MINUTOS_DEFAULT = 30  # Janela padrão: últimos 30 minutos
HISTORICO_GAP_NOVA_CONVERSA = 10  # Gap de 10min = nova conversa
HISTORICO_LIMITE_INTERACOES = 20  # Máximo de interações a incluir
HISTORICO_MAX_CHARS_MENSAGEM = 2000  # Truncar mensagens muito longas (aumentado)
HISTORICO_MAX_CHARS_RESULTADO = 1000  # Truncar resultados de busca (aumentado)


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


# =============================================================================
# FUNÇÕES AUXILIARES DO HISTÓRICO v2
# =============================================================================

def _agrupar_por_interacao(mensagens: List[Dict]) -> List[List[Dict]]:
    """
    Agrupa mensagens em interações completas (v2).

    Uma interação = usuario + (resultado?) + assistente
    Garante que nunca cortamos uma conversa pela metade.

    Args:
        mensagens: Lista de mensagens em ordem cronológica

    Returns:
        Lista de interações, cada uma sendo uma lista de mensagens
    """
    if not mensagens:
        return []

    interacoes = []
    interacao_atual = []

    for msg in mensagens:
        interacao_atual.append(msg)

        # Interação termina quando assistente responde
        if msg['tipo'] == 'assistente':
            interacoes.append(interacao_atual)
            interacao_atual = []

    # Última interação incompleta (usuário perguntou, ainda não respondeu)
    # Inclui mesmo assim - é a pergunta atual!
    if interacao_atual:
        interacoes.append(interacao_atual)

    return interacoes


def _detectar_inicio_conversa(mensagens: List[Dict], gap_minutos: int = HISTORICO_GAP_NOVA_CONVERSA) -> int:
    """
    Encontra onde começa a conversa ATUAL (v2).

    Procura por gap de inatividade > N minutos.
    Tudo antes do gap é "conversa anterior" e pode ser ignorado.

    Args:
        mensagens: Lista de mensagens em ordem cronológica
        gap_minutos: Minutos de inatividade que indicam nova conversa

    Returns:
        Índice da primeira mensagem da conversa atual (0 = tudo é uma conversa)
    """
    if len(mensagens) <= 1:
        return 0

    # Percorre de trás pra frente procurando gap
    for i in range(len(mensagens) - 1, 0, -1):
        try:
            # Parseia timestamps
            atual_str = mensagens[i].get('criado_em')
            anterior_str = mensagens[i - 1].get('criado_em')

            if not atual_str or not anterior_str:
                continue

            # Suporta tanto datetime quanto string ISO
            if isinstance(atual_str, str):
                atual = datetime.fromisoformat(atual_str.replace('Z', '+00:00'))
            else:
                atual = atual_str

            if isinstance(anterior_str, str):
                anterior = datetime.fromisoformat(anterior_str.replace('Z', '+00:00'))
            else:
                anterior = anterior_str

            # Calcula gap em minutos
            gap = (atual - anterior).total_seconds() / 60

            if gap > gap_minutos:
                logger.debug(f"[MEMORY] Gap de {gap:.1f}min detectado, conversa começa no índice {i}")
                return i  # Conversa atual começa aqui

        except (ValueError, TypeError, AttributeError) as e:
            logger.debug(f"[MEMORY] Erro ao parsear timestamp: {e}")
            continue

    return 0  # Tudo é uma conversa contínua


def _formatar_interacao(interacao: List[Dict], incluir_resultado: bool = True) -> List[str]:
    """
    Formata uma interação para texto legível (v2).

    Args:
        interacao: Lista de mensagens da interação
        incluir_resultado: Se deve incluir mensagens tipo 'resultado'

    Returns:
        Lista de linhas formatadas
    """
    linhas = []

    for msg in interacao:
        tipo = msg.get('tipo', '')
        conteudo = msg.get('conteudo', '')

        if tipo == 'usuario':
            # Trunca se muito longo
            if len(conteudo) > HISTORICO_MAX_CHARS_MENSAGEM:
                conteudo = conteudo[:HISTORICO_MAX_CHARS_MENSAGEM] + "..."
            linhas.append(f"USUÁRIO: {conteudo}")

        elif tipo == 'assistente':
            # Trunca se muito longo
            if len(conteudo) > HISTORICO_MAX_CHARS_MENSAGEM:
                conteudo = conteudo[:HISTORICO_MAX_CHARS_MENSAGEM] + "..."
            linhas.append(f"ASSISTENTE: {conteudo}")

        elif tipo == 'resultado' and incluir_resultado:
            # Resultados são mais resumidos
            if len(conteudo) > HISTORICO_MAX_CHARS_RESULTADO:
                conteudo = conteudo[:HISTORICO_MAX_CHARS_RESULTADO] + "..."
            linhas.append(f"[Resultado: {conteudo}]")

    return linhas


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
    def buscar_historico(usuario_id: int, limite: int = None) -> List[Dict]:
        """
        Busca histórico de conversas do usuário.

        Returns:
            Lista de mensagens em ordem cronológica
        """
        try:
            from .models import ClaudeHistoricoConversa
            # Usa config dinâmica se limite não foi especificado
            if limite is None:
                limite = _get_max_historico()
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
        Formata todo o contexto de memória para enviar ao Claude (v2).

        v2.0 Melhorias:
        - Busca por TEMPO (últimos 30min) ao invés de quantidade
        - Agrupa por INTERAÇÃO (nunca corta conversa pela metade)
        - Detecta INÍCIO DE CONVERSA por gap de inatividade
        - Limita por interações completas, não por caracteres

        Inclui:
        1. Aprendizados permanentes (globais + usuário) - OPCIONAL
        2. Histórico recente de conversas (v2: por tempo/interação)

        Args:
            usuario_id: ID do usuário
            incluir_aprendizados: Se False, não carrega aprendizados
            modelo: Modelo Claude em uso (para ajustar tokens)

        Returns:
            String formatada para incluir no system prompt
        """
        partes = []

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

        # 2. HISTÓRICO DE CONVERSAS (v2: por tempo e interação)
        historico = MemoryService.buscar_historico_inteligente(usuario_id)

        if historico:
            partes.append("=== HISTÓRICO RECENTE DA CONVERSA ===")
            partes.extend(historico)
            partes.append("")

        return "\n".join(partes) if partes else ""

    @staticmethod
    def buscar_historico_inteligente(
        usuario_id: int,
        minutos: int = HISTORICO_MINUTOS_DEFAULT,
        max_interacoes: int = HISTORICO_LIMITE_INTERACOES
    ) -> List[str]:
        """
        Busca e formata histórico de forma inteligente (v2).

        Algoritmo:
        1. Busca mensagens dos últimos N minutos
        2. Detecta início da conversa atual (gap de inatividade)
        3. Agrupa em interações completas
        4. Limita por número de interações (não chars)
        5. Formata para texto legível

        Args:
            usuario_id: ID do usuário
            minutos: Janela de tempo para buscar
            max_interacoes: Máximo de interações a incluir

        Returns:
            Lista de linhas formatadas do histórico
        """
        try:
            from .models import ClaudeHistoricoConversa

            # 1. Busca por TEMPO (não quantidade)
            mensagens_raw = ClaudeHistoricoConversa.buscar_historico_recente(
                usuario_id,
                minutos=minutos,
                limite_max=max_interacoes * 4  # ~4 msgs por interação
            )

            if not mensagens_raw:
                return []

            # Converte para dict
            mensagens = [m.to_dict() for m in mensagens_raw]

            # 2. Detecta início da conversa atual (após gap)
            inicio = _detectar_inicio_conversa(mensagens)
            if inicio > 0:
                mensagens = mensagens[inicio:]
                logger.debug(f"[MEMORY] Conversa atual: {len(mensagens)} msgs (ignorou {inicio} anteriores)")

            # 3. Agrupa em interações completas
            interacoes = _agrupar_por_interacao(mensagens)

            if not interacoes:
                return []

            # 4. Limita por número de interações (pega as mais recentes)
            if len(interacoes) > max_interacoes:
                interacoes = interacoes[-max_interacoes:]
                logger.debug(f"[MEMORY] Limitado a {max_interacoes} interações")

            # 5. Formata cada interação
            linhas = []
            for i, interacao in enumerate(interacoes):
                linhas_interacao = _formatar_interacao(interacao)
                linhas.extend(linhas_interacao)

                # Separador entre interações (exceto última)
                if i < len(interacoes) - 1:
                    linhas.append("")

            logger.debug(f"[MEMORY] Histórico v2: {len(interacoes)} interações, {len(linhas)} linhas")
            return linhas

        except Exception as e:
            logger.error(f"[MEMORY] Erro ao buscar histórico inteligente: {e}")
            return []

    @staticmethod
    def buscar_historico_para_extrator(usuario_id: int) -> str:
        """
        Busca histórico formatado especificamente para o extrator (v2).

        Diferente do formatar_contexto_memoria():
        - NÃO inclui aprendizados (extrator já recebe conhecimento separado)
        - Foco em interações recentes para entender follow-ups
        - Retorna string pronta para incluir no prompt

        Args:
            usuario_id: ID do usuário

        Returns:
            String com histórico formatado ou string vazia
        """
        linhas = MemoryService.buscar_historico_inteligente(usuario_id)
        return "\n".join(linhas) if linhas else ""

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
