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
