"""
ConversationContext v5 - Camada de Interpretação Léxica.

FILOSOFIA v3.5.2:
- NÃO GUARDA ESTADO (delega 100% para EstadoManager)
- APENAS interpreta texto (regex, padrões, heurísticas)
- SEMPRE consulta EstadoManager para obter/atualizar dados

O que faz:
1. Classificar tipo de mensagem (regex)
2. Extrair opções (A, B, C)
3. Detectar padrões especiais ("pedido total", referência numérica)

O que NÃO faz mais:
- Guardar entidades (usa EstadoManager.ENTIDADES)
- Guardar opções (usa EstadoManager.OPCOES)
- Guardar histórico (usa EstadoManager.DIALOGO)
- Reconstruir perguntas (usa EstadoManager.REFERENCIA)

Criado em: 24/11/2025
Reescrito em: 24/11/2025 - v5 minimalista
Limite: 150 linhas
"""

import re
import logging
from typing import Dict, Optional, Tuple, List

logger = logging.getLogger(__name__)


# ============================================================
# PADRÕES DE REGEX (única responsabilidade deste arquivo)
# ============================================================

PADROES_ACAO = [
    r'^op[cç][aã]o\s*([abc])\b',
    r'^quero\s+(a\s+)?op[cç][aã]o\s*([abc])\b',
    r'^([abc])\s*$',
    r'\bcriar?\s+separa[cç][aã]o\b',
    r'\bgerar?\s+separa[cç][aã]o\b',
    r'\bconfirm[ao]r?\b',
    r'^sim\b',
    r'^n[aã]o\b',
    r'\bcancelar?\b',
]

PADROES_TOTAL_PEDIDO = [
    r'\btodos?\s+(os\s+)?itens?\b',
    r'\bpedido\s+total\b',
    r'\bpedido\s+completo\b',
    r'\btudo\b',
    r'\binteiro\b',
]

PADROES_REFERENCIA_NUMERO = [
    r'\b(?:o\s+)?(?:pedido|item)\s+(?:numero\s+)?(\d+)\b',
    r'\b(?:o\s+)?(\d+)(?:º|°|o|a)?\s*(?:pedido|item|da\s+lista)?\b',
    r'^(\d+)\s*$',
]


# ============================================================
# FUNÇÕES DE INTERPRETAÇÃO (sem estado)
# ============================================================

def extrair_opcao(texto: str) -> Optional[str]:
    """
    Extrai opção escolhida (A, B, C) do texto.

    Função PURA - não acessa estado.

    Returns:
        'A', 'B', 'C' ou None
    """
    texto_lower = texto.lower().strip()

    patterns = [
        r'^op[cç][aã]o\s*([abc])\b',
        r'^quero\s+(a\s+)?op[cç][aã]o\s*([abc])\b',
        r'^([abc])\s*$',
        r'\bop[cç][aã]o\s*([abc])\b',
    ]

    for pattern in patterns:
        match = re.search(pattern, texto_lower)
        if match:
            grupos = [g for g in match.groups() if g and len(g) == 1]
            if grupos:
                return grupos[-1].upper()

    return None


def detectar_pedido_total(texto: str) -> bool:
    """
    Detecta se o usuário quer o pedido total/completo.

    Função PURA - não acessa estado.
    """
    texto_lower = texto.lower()
    for padrao in PADROES_TOTAL_PEDIDO:
        if re.search(padrao, texto_lower):
            return True
    return False


def extrair_referencia_numerica(texto: str) -> Optional[int]:
    """
    Extrai referência numérica como "o pedido 2" ou "o 3º".

    Função PURA - não acessa estado.

    Returns:
        Número extraído ou None
    """
    texto_lower = texto.lower()

    for padrao in PADROES_REFERENCIA_NUMERO:
        match = re.search(padrao, texto_lower)
        if match:
            grupos = match.groups()
            if grupos and grupos[0]:
                try:
                    return int(grupos[0])
                except ValueError:
                    pass

    return None


def e_mensagem_acao(texto: str) -> bool:
    """
    Verifica se é uma mensagem de ação (opção, confirmação, etc).

    Função PURA - não acessa estado.
    """
    texto_lower = texto.lower().strip()

    for padrao in PADROES_ACAO:
        if re.search(padrao, texto_lower):
            return True

    return False


# ============================================================
# CLASSE DE COMPATIBILIDADE (delega para EstadoManager)
# ============================================================

class ConversationContextManager:
    """
    Classe de compatibilidade que delega 100% para EstadoManager.

    DEPRECATED: Use EstadoManager diretamente quando possível.
    """

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
        """Delega atualização para EstadoManager."""
        from .structured_state import EstadoManager, FonteEntidade

        # Atualiza entidades
        if entidades:
            for k, v in entidades.items():
                if v and str(v).lower() not in ('null', 'none', ''):
                    EstadoManager.atualizar_entidade(
                        usuario_id, k, v, FonteEntidade.CONSULTA.value
                    )

        # Atualiza opções
        if opcoes:
            EstadoManager.definir_opcoes(
                usuario_id,
                motivo="Opções oferecidas",
                lista=[{"letra": chr(65+i), "descricao": str(o.get('descricao', o))}
                       for i, o in enumerate(opcoes[:3])],
                esperado_do_usuario="Escolher uma opção"
            )

        logger.debug(f"[CONTEXT] Delegado para EstadoManager (usuario={usuario_id})")

    @staticmethod
    def registrar_itens_numerados(usuario_id: int, dados: List[Dict]):
        """Delega para EstadoManager."""
        from .structured_state import EstadoManager

        # Registra como dados da última consulta
        if dados:
            EstadoManager.definir_consulta(
                usuario_id,
                tipo="itens",
                total=len(dados),
                itens=dados[:10]  # Limita a 10
            )

        logger.debug(f"[CONTEXT] {len(dados)} itens delegados para EstadoManager")

    @staticmethod
    def limpar_estado(usuario_id: int):
        """Delega para EstadoManager."""
        from .structured_state import EstadoManager
        EstadoManager.limpar_tudo(usuario_id)

    @staticmethod
    def formatar_contexto_para_prompt(usuario_id: int) -> str:
        """
        DEPRECATED: Use obter_estado_json() do structured_state.

        Mantido apenas para compatibilidade com código legado.
        """
        from .structured_state import obter_estado_json
        return obter_estado_json(usuario_id)

    @staticmethod
    def extrair_opcao(texto: str) -> Optional[str]:
        """Wrapper para função pura."""
        return extrair_opcao(texto)


# ============================================================
# FUNÇÃO DE COMPATIBILIDADE
# ============================================================

def classificar_e_reconstruir(texto: str, usuario_id: int) -> Tuple[str, str, Dict, Dict]:
    """
    DEPRECATED: Use extração inteligente diretamente.

    Mantido apenas para compatibilidade com classificador legado.
    """
    from .structured_state import EstadoManager

    # Tipo básico baseado em regex
    if e_mensagem_acao(texto):
        tipo = 'ACAO'
    else:
        tipo = 'NOVA_CONSULTA'

    # Obtém entidades do EstadoManager
    estado = EstadoManager.obter(usuario_id)
    entidades = {k: v.get('valor') for k, v in estado.entidades.items() if v.get('valor')}

    return tipo, texto, entidades, {}
