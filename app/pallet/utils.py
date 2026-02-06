"""
Utilitarios para o modulo de Pallet

Funcoes auxiliares para normalizacao de CNPJ, busca de destinatario
e calculo de prazo de cobranca.
"""
from typing import Optional, Tuple


def normalizar_cnpj(cnpj: str) -> str:
    """
    Remove formatacao e retorna apenas digitos do CNPJ.

    Args:
        cnpj: CNPJ com ou sem formatacao

    Returns:
        Apenas os digitos do CNPJ
    """
    if not cnpj:
        return ''
    return ''.join(c for c in cnpj if c.isdigit())


def raiz_cnpj(cnpj: str) -> str:
    """
    Retorna os 8 primeiros digitos do CNPJ (raiz/prefixo).
    A raiz identifica a empresa matriz independente de filiais.

    Formato CNPJ: XX.XXX.XXX/YYYY-ZZ
    - XX.XXX.XXX = Raiz (8 digitos) - Identifica a empresa
    - YYYY = Filial (4 digitos)
    - ZZ = Digitos verificadores

    Args:
        cnpj: CNPJ com ou sem formatacao

    Returns:
        Os 8 primeiros digitos (raiz)
    """
    cnpj_norm = normalizar_cnpj(cnpj)
    return cnpj_norm[:8] if len(cnpj_norm) >= 8 else cnpj_norm


def buscar_tipo_destinatario(cnpj: str) -> Tuple[str, str, str]:
    """
    Busca tipo de destinatario pelo CNPJ.

    Prioridade de busca:
    1. Transportadora (tabela transportadoras)
    2. Cliente (tabela contatos_agendamento)
    3. Assume CLIENTE se nao encontrar

    O match e feito pela raiz do CNPJ (8 primeiros digitos),
    permitindo encontrar qualquer filial da mesma empresa.

    Args:
        cnpj: CNPJ do destinatario

    Returns:
        Tuple com (tipo_destinatario, cnpj_completo, nome)
        - tipo_destinatario: 'TRANSPORTADORA' ou 'CLIENTE'
        - cnpj_completo: CNPJ encontrado no cadastro
        - nome: Razao social ou nome do contato
    """
    from app.transportadoras.models import Transportadora
    from app.cadastros_agendamento.models import ContatoAgendamento

    raiz = raiz_cnpj(cnpj)
    if not raiz:
        return ('CLIENTE', cnpj, '')

    # 1. Buscar em Transportadora (prioridade)
    for transp in Transportadora.query.filter(Transportadora.ativo == True).all():
        if raiz_cnpj(transp.cnpj) == raiz:
            return ('TRANSPORTADORA', transp.cnpj, transp.razao_social)

    # 2. Buscar em ContatoAgendamento
    for contato in ContatoAgendamento.query.all():
        if raiz_cnpj(contato.cnpj) == raiz:
            return ('CLIENTE', contato.cnpj, contato.contato or '')

    # 3. Nao encontrado - assume CLIENTE
    return ('CLIENTE', cnpj, '')


# =============================================================================
# Versao otimizada com cache pre-carregado (para uso em batch/sync)
# =============================================================================

_transportadoras_cache = None
_contatos_cache = None


def _carregar_caches():
    """Carrega todas transportadoras e contatos em dicts por raiz CNPJ."""
    global _transportadoras_cache, _contatos_cache
    from app.transportadoras.models import Transportadora
    from app.cadastros_agendamento.models import ContatoAgendamento

    _transportadoras_cache = {}
    for t in Transportadora.query.filter(Transportadora.ativo == True).all():
        raiz = raiz_cnpj(t.cnpj)
        if raiz:
            _transportadoras_cache[raiz] = (t.cnpj, t.razao_social)

    _contatos_cache = {}
    for c in ContatoAgendamento.query.all():
        raiz = raiz_cnpj(c.cnpj)
        if raiz:
            _contatos_cache[raiz] = (c.cnpj, c.contato or '')


def buscar_tipo_destinatario_batch(cnpj: str) -> Tuple[str, str, str]:
    """
    Versao otimizada de buscar_tipo_destinatario com cache pre-carregado.

    Na primeira chamada, carrega TODAS as transportadoras e contatos em dict.
    Chamadas subsequentes fazem lookup O(1) no dict.

    Usar em contextos de batch (sincronizacao) onde muitas chamadas
    consecutivas seriam feitas. Chamar limpar_cache_destinatario() ao final.
    """
    global _transportadoras_cache, _contatos_cache
    if _transportadoras_cache is None:
        _carregar_caches()

    raiz = raiz_cnpj(cnpj)
    if not raiz:
        return ('CLIENTE', cnpj, '')

    if raiz in _transportadoras_cache:
        t_cnpj, t_nome = _transportadoras_cache[raiz]
        return ('TRANSPORTADORA', t_cnpj, t_nome)

    if raiz in _contatos_cache:
        c_cnpj, c_nome = _contatos_cache[raiz]
        return ('CLIENTE', c_cnpj, c_nome)

    return ('CLIENTE', cnpj, '')


def limpar_cache_destinatario():
    """Limpa cache para forcar recarga na proxima chamada."""
    global _transportadoras_cache, _contatos_cache
    _transportadoras_cache = None
    _contatos_cache = None


# Constantes de prazo de cobranca
PRAZO_COBRANCA_SP_RED = 7   # SP ou rota RED: 7 dias
PRAZO_COBRANCA_OUTROS = 30  # Demais estados/rotas: 30 dias


def calcular_prazo_cobranca(uf: Optional[str], rota: Optional[str] = None) -> int:
    """
    Calcula prazo de cobranca de pallet baseado em UF e rota.

    Regras:
    - UF = SP ou Rota = RED: 7 dias apos entrega
    - Demais casos: 30 dias apos entrega

    Args:
        uf: UF do destinatario (ex: 'SP', 'RJ')
        rota: Rota da entrega (ex: 'RED', 'NORMAL')

    Returns:
        Numero de dias de prazo para cobranca
    """
    if uf and uf.upper() == 'SP':
        return PRAZO_COBRANCA_SP_RED
    if rota and rota.upper() == 'RED':
        return PRAZO_COBRANCA_SP_RED
    return PRAZO_COBRANCA_OUTROS
