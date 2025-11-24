"""
ConversationContext - Gerenciador de contexto conversacional genérico.

Responsabilidades:
1. Manter estado da conversa (pergunta anterior, resultado, entidades)
2. Detectar tipo de mensagem (nova consulta, continuação, modificação, ação)
3. Reconstruir consultas com contexto anterior
4. Suportar fluxos multi-turno (pergunta -> detalhe -> ação)

Padrões detectados:
- NOVA_CONSULTA: Pergunta sem referência a contexto anterior
- CONTINUACAO: "Quais itens tem nesse pedido?" (referencia pedido anterior)
- MODIFICACAO: "Refaça com nome_produto" (modifica consulta anterior)
- ACAO: "Opção A", "Criar separação", "Confirmo"
- DETALHAMENTO: "Mais detalhes", "Me fala mais sobre"

Criado em: 24/11/2025
Limite: 300 linhas
"""

import re
import logging
from typing import Dict, Optional, Tuple, List, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger(__name__)


@dataclass
class ConversationState:
    """Estado atual da conversa de um usuário."""
    usuario_id: int
    ultima_pergunta: str = ""
    ultima_intencao: Dict = field(default_factory=dict)
    ultimo_resultado: Dict = field(default_factory=dict)
    entidades_ativas: Dict = field(default_factory=dict)  # Entidades acumuladas
    opcoes_oferecidas: List[Dict] = field(default_factory=list)  # Opções A, B, C
    aguardando_confirmacao: bool = False
    acao_pendente: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


# Cache em memória por usuário
_estados_conversa: Dict[int, ConversationState] = {}


# Padrões para detectar tipo de mensagem
PADROES_CONTINUACAO = [
    r'\b(esse|essa|esses|essas|este|esta|estes|estas)\b',
    r'\b(nesse|nessa|nesses|nessas|neste|nesta|nestes|nestas)\b',
    r'\b(dele|dela|deles|delas)\b',
    r'\b(desse|dessa|desses|dessas|deste|desta|destes|destas)\s+(pedido|cliente|produto)',
    r'\bquais\s+(itens|produtos|items)\b',
    r'\bquando\s+(da|posso|pode)\b',
    r'\bo\s+que\s+(tem|está|esta)\b',
]

PADROES_MODIFICACAO = [
    r'\brefa[cç][ao]?\b',
    r'\binclu[ia]\s+(o\s+)?campo\b',
    r'\badicion[ea]\s+(o\s+)?campo\b',
    r'\bmostre?\s+tamb[eé]m\b',
    r'\btraga?\s+(o\s+)?campo\b',
    r'\bcom\s+mais\s+detalhes?\b',
]

PADROES_ACAO = [
    r'^op[cç][aã]o\s*([abc])\b',
    r'^quero\s+(a\s+)?op[cç][aã]o\s*([abc])\b',
    r'^([abc])\s*$',  # Apenas "A", "B" ou "C"
    r'\bcriar?\s+separa[cç][aã]o\b',
    r'\bgerar?\s+separa[cç][aã]o\b',
    r'\bconfirm[ao]r?\b',
    r'^sim\b',
    r'^n[aã]o\b',
    r'\bcancelar?\b',
]

PADROES_DETALHAMENTO = [
    r'\bmais\s+detalhes?\b',
    r'\bme\s+fal[ea]\s+mais\b',
    r'\bexplique?\b',
    r'\bdetalhe?\b',
    r'\bo\s+que\s+significa\b',
]

PADROES_TOTAL_PEDIDO = [
    r'\btodos?\s+(os\s+)?itens?\b',
    r'\bpedido\s+total\b',
    r'\bpedido\s+completo\b',
    r'\btudo\b',
    r'\binteiro\b',
    r'\btotal\b',
]


class ConversationContextManager:
    """Gerencia contexto de conversas."""

    @staticmethod
    def obter_estado(usuario_id: int) -> ConversationState:
        """Obtém ou cria estado da conversa do usuário."""
        if usuario_id not in _estados_conversa:
            _estados_conversa[usuario_id] = ConversationState(usuario_id=usuario_id)
        return _estados_conversa[usuario_id]

    @staticmethod
    def atualizar_estado(
        usuario_id: int,
        pergunta: str = None,
        intencao: Dict = None,
        resultado: Dict = None,
        entidades: Dict = None,
        opcoes: List[Dict] = None,
        aguardando_confirmacao: bool = None,
        acao_pendente: str = None
    ):
        """Atualiza estado da conversa."""
        estado = ConversationContextManager.obter_estado(usuario_id)

        if pergunta is not None:
            estado.ultima_pergunta = pergunta
        if intencao is not None:
            estado.ultima_intencao = intencao
        if resultado is not None:
            estado.ultimo_resultado = resultado
        if entidades is not None:
            # Merge entidades (preserva anteriores + adiciona novas)
            estado.entidades_ativas.update({
                k: v for k, v in entidades.items()
                if v and str(v).lower() not in ('null', 'none', '')
            })
        if opcoes is not None:
            estado.opcoes_oferecidas = opcoes
        if aguardando_confirmacao is not None:
            estado.aguardando_confirmacao = aguardando_confirmacao
        if acao_pendente is not None:
            estado.acao_pendente = acao_pendente

        estado.timestamp = datetime.now()
        logger.debug(f"[CONTEXT] Estado atualizado para usuário {usuario_id}")

    @staticmethod
    def limpar_estado(usuario_id: int):
        """Limpa estado da conversa."""
        if usuario_id in _estados_conversa:
            del _estados_conversa[usuario_id]
        logger.debug(f"[CONTEXT] Estado limpo para usuário {usuario_id}")

    @staticmethod
    def classificar_mensagem(texto: str, usuario_id: int) -> Tuple[str, Dict]:
        """
        Classifica o tipo de mensagem baseado no contexto.

        Args:
            texto: Texto da mensagem
            usuario_id: ID do usuário

        Returns:
            Tuple (tipo, metadados) onde tipo é:
            - NOVA_CONSULTA
            - CONTINUACAO
            - MODIFICACAO
            - ACAO
            - DETALHAMENTO
        """
        texto_lower = texto.lower().strip()
        estado = ConversationContextManager.obter_estado(usuario_id)

        # 1. Verifica se é AÇÃO (opção, confirmação, etc)
        for padrao in PADROES_ACAO:
            match = re.search(padrao, texto_lower)
            if match:
                opcao = match.group(1) if match.groups() else None
                return 'ACAO', {
                    'opcao_escolhida': opcao.upper() if opcao and len(opcao) == 1 else None,
                    'texto_original': texto
                }

        # 2. Verifica se é MODIFICAÇÃO da consulta anterior
        for padrao in PADROES_MODIFICACAO:
            if re.search(padrao, texto_lower):
                return 'MODIFICACAO', {
                    'pergunta_original': estado.ultima_pergunta,
                    'modificacao_solicitada': texto
                }

        # 3. Verifica se é DETALHAMENTO
        for padrao in PADROES_DETALHAMENTO:
            if re.search(padrao, texto_lower):
                return 'DETALHAMENTO', {
                    'contexto_anterior': estado.ultimo_resultado
                }

        # 4. Verifica se é CONTINUAÇÃO (referência a contexto anterior)
        for padrao in PADROES_CONTINUACAO:
            if re.search(padrao, texto_lower):
                return 'CONTINUACAO', {
                    'entidades_anteriores': estado.entidades_ativas,
                    'resultado_anterior': estado.ultimo_resultado
                }

        # 5. Por padrão, é NOVA_CONSULTA
        return 'NOVA_CONSULTA', {}

    @staticmethod
    def reconstruir_consulta(
        texto: str,
        tipo: str,
        metadados: Dict,
        usuario_id: int
    ) -> Tuple[str, Dict]:
        """
        Reconstrói a consulta incorporando contexto.

        Args:
            texto: Texto original da mensagem
            tipo: Tipo classificado (CONTINUACAO, MODIFICACAO, etc)
            metadados: Metadados da classificação
            usuario_id: ID do usuário

        Returns:
            Tuple (consulta_reconstruida, entidades_combinadas)
        """
        estado = ConversationContextManager.obter_estado(usuario_id)

        if tipo == 'NOVA_CONSULTA':
            return texto, {}

        elif tipo == 'CONTINUACAO':
            # Combina entidades anteriores com a nova pergunta
            # Ex: "Quais itens tem nesse pedido?" + num_pedido do contexto
            entidades = estado.entidades_ativas.copy()

            # Tenta extrair referência do resultado anterior
            if estado.ultimo_resultado:
                dados = estado.ultimo_resultado.get('dados', [])
                if dados and isinstance(dados, list) and len(dados) > 0:
                    primeiro = dados[0] if isinstance(dados[0], dict) else {}
                    if 'num_pedido' in primeiro:
                        entidades['num_pedido'] = primeiro['num_pedido']
                    if 'cnpj_cpf' in primeiro:
                        entidades['cnpj'] = primeiro['cnpj_cpf']

            return texto, entidades

        elif tipo == 'MODIFICACAO':
            # Reconstrói pergunta original + modificação
            pergunta_original = metadados.get('pergunta_original', '')
            if pergunta_original:
                # Ex: "Ha pedidos do Idenildo?" + "Refaça com nome_produto"
                # -> "Ha pedidos do Idenildo? Inclua o campo nome_produto"
                consulta_reconstruida = f"{pergunta_original} {texto}"
                return consulta_reconstruida, estado.entidades_ativas

            return texto, estado.entidades_ativas

        elif tipo == 'ACAO':
            # Para ações, retorna entidades acumuladas
            return texto, estado.entidades_ativas

        elif tipo == 'DETALHAMENTO':
            # Adiciona contexto do resultado anterior
            return texto, estado.entidades_ativas

        return texto, {}

    @staticmethod
    def detectar_pedido_total(texto: str) -> bool:
        """
        Detecta se o usuário quer o pedido total/completo.

        Útil para separação: "todos os itens", "pedido total", etc.
        """
        texto_lower = texto.lower()
        for padrao in PADROES_TOTAL_PEDIDO:
            if re.search(padrao, texto_lower):
                return True
        return False

    @staticmethod
    def extrair_opcao(texto: str) -> Optional[str]:
        """
        Extrai opção escolhida (A, B, C) do texto.

        Returns:
            'A', 'B', 'C' ou None
        """
        texto_lower = texto.lower().strip()

        # Padrões diretos
        patterns = [
            r'^op[cç][aã]o\s*([abc])\b',
            r'^quero\s+(a\s+)?op[cç][aã]o\s*([abc])\b',
            r'^([abc])\s*$',
            r'\bop[cç][aã]o\s*([abc])\b',
        ]

        for pattern in patterns:
            match = re.search(pattern, texto_lower)
            if match:
                # Pega o último grupo que matchou
                grupos = [g for g in match.groups() if g and len(g) == 1]
                if grupos:
                    return grupos[-1].upper()

        return None

    @staticmethod
    def formatar_contexto_para_prompt(usuario_id: int) -> str:
        """
        Formata contexto da conversa para incluir no prompt do Claude.

        Returns:
            String formatada com contexto relevante
        """
        estado = ConversationContextManager.obter_estado(usuario_id)

        if not estado.ultima_pergunta and not estado.entidades_ativas:
            return ""

        linhas = ["=== CONTEXTO DA CONVERSA ATUAL ==="]

        if estado.ultima_pergunta:
            linhas.append(f"Última pergunta: {estado.ultima_pergunta}")

        if estado.entidades_ativas:
            linhas.append(f"Entidades identificadas: {estado.entidades_ativas}")

        if estado.opcoes_oferecidas:
            linhas.append(f"Opções oferecidas: {len(estado.opcoes_oferecidas)} opções")

        if estado.aguardando_confirmacao:
            linhas.append(f"Aguardando confirmação para: {estado.acao_pendente}")

        if estado.ultimo_resultado:
            total = estado.ultimo_resultado.get('total_encontrado', 0)
            linhas.append(f"Último resultado: {total} item(s) encontrado(s)")

        linhas.append("=== FIM DO CONTEXTO ===")

        return "\n".join(linhas)


# Funções de conveniência
def classificar_e_reconstruir(texto: str, usuario_id: int) -> Tuple[str, str, Dict, Dict]:
    """
    Classifica e reconstrói consulta em uma única chamada.

    Returns:
        Tuple (tipo, consulta_reconstruida, entidades, metadados)
    """
    tipo, metadados = ConversationContextManager.classificar_mensagem(texto, usuario_id)
    consulta, entidades = ConversationContextManager.reconstruir_consulta(
        texto, tipo, metadados, usuario_id
    )
    return tipo, consulta, entidades, metadados
