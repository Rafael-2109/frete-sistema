"""
MATRIZ_INTERCOMPANY — operacoes fiscais entre empresas do grupo NACOM.

Dado, nao codigo. Adicionar nova operacao = adicionar entrada no dict.

Origem dos valores: docs/inventario-2026-05/00-decisoes/D002-matriz-intercompany-final.md
Premissas: P001-P011 em docs/inventario-2026-05/01-premissas/

Estrutura:
- `fiscal_position_id`: dict com chave tupla (company_origem, company_destino).
  Service usa esta para setar fiscal_position no account.move; Odoo decide
  CFOP automaticamente a partir disso. NAO setar CFOP no account.move.
- `cfop_esperado`: informacional, apenas para humanos e logs.

Spec: docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md §6.3
"""
from typing import Dict, Any, Tuple


CODIGO_PARA_COMPANY_ID: Dict[str, int] = {'FB': 1, 'CD': 4, 'LF': 5}

COMPANY_PARTNER_ID: Dict[int, int] = {
    1: 1,    # FB → res.partner.id=1
    4: 34,   # CD → res.partner.id=34
    5: 35,   # LF → res.partner.id=35
}


MATRIZ_INTERCOMPANY: Dict[str, Dict[str, Any]] = {
    'industrializacao': {
        'l10n_br_tipo_pedido': 'industrializacao',
        'move_type': 'out_invoice',
        'tipo_produto': [1, 2, 3],
        'fiscal_position_id': {
            (1, 5): 25,  # FB → LF: 'REMESSA PARA INDUSTRIALIZAÇÃO'
        },
        'cfop_esperado': {(1, 5): '5901'},
        'nf_referencia': 94457,
        'account_move_id_referencia': 607443,
    },
    'perda': {
        'l10n_br_tipo_pedido': 'perda',
        'move_type': 'out_invoice',
        'tipo_produto': [1, 2, 3],
        'fiscal_position_id': {
            (5, 1): 91,  # LF → FB: 'SAÍDA - PERDAS'
        },
        'cfop_esperado': {(5, 1): '5903'},
        'nf_referencia': 13075,
        'account_move_id_referencia': 588209,
    },
    'dev-industrializacao': {
        'l10n_br_tipo_pedido': 'dev-industrializacao',
        'move_type': 'out_invoice',
        'tipo_produto': [4],
        'fiscal_position_id': {
            # Direcoes COM precedente historico
            (4, 5): 74,   # CD → LF: 'SAÍDA - REMESSA PARA RETRABALHO'
            (5, 4): 89,   # LF → CD: 'SAÍDA - RETRABALHO'
            # Direcoes SEM precedente — assumidas por simetria (P011)
            (1, 5): 74,   # FB → LF: simetria com (4,5)
            (5, 1): 89,   # LF → FB: simetria com (5,4)
        },
        'cfop_esperado': {
            (4, 5): '5949',
            (5, 4): '5949',
            (1, 5): '5949',  # P011
            (5, 1): '5949',  # P011
        },
        'nf_referencia': 147772,
        'account_move_id_referencia': 590839,
        'direcoes_sem_precedente_historico': [(1, 5), (5, 1)],
    },
    'transf-filial': {
        'l10n_br_tipo_pedido': 'transf-filial',
        'move_type': 'out_invoice',
        'tipo_produto': [1, 2, 3, 4],
        'fiscal_position_id': {
            (1, 4): 20,  # FB → CD: 'SAÍDA - TRANSFERÊNCIA ENTRE FILIAIS'
            (4, 1): 49,  # CD → FB: 'SAÍDA - TRANSFERÊNCIA ENTRE FILIAIS'
        },
        'cfop_esperado': {
            (1, 4): '5152',
            (4, 1): '5151',
        },
        'nf_referencia': 94410,
        'account_move_id_referencia': 604472,
    },
}


def get_operacao(tipo_operacao: str) -> Dict[str, Any]:
    """Retorna entrada da matriz.

    Raises:
        KeyError: se tipo_operacao nao existe.
    """
    if tipo_operacao not in MATRIZ_INTERCOMPANY:
        raise KeyError(
            f"tipo_operacao={tipo_operacao!r} nao em MATRIZ_INTERCOMPANY. "
            f"Validos: {sorted(MATRIZ_INTERCOMPANY)}"
        )
    return MATRIZ_INTERCOMPANY[tipo_operacao]


def resolver_operacao_por_tipo_produto(*, tipo: int, company_id: int, sinal: int) -> str:
    """
    Dada uma diferenca de inventario, decide qual operacao usar.

    Args:
        tipo: 1/2/3/4 (primeiro digito do cod_produto)
        company_id: 1 (FB), 4 (CD), 5 (LF)
        sinal: +1 se ajuste positivo (estoque deve aumentar),
               -1 se negativo (estoque deve diminuir)

    Returns:
        chave de MATRIZ_INTERCOMPANY.

    Raises:
        ValueError: se combinacao desconhecida.
    """
    if company_id == 5:  # LF
        if tipo == 4:
            return 'dev-industrializacao'
        if tipo in (1, 2, 3):
            return 'industrializacao' if sinal > 0 else 'perda'
        raise ValueError(f'tipo={tipo} nao suportado para LF (company_id=5)')

    if company_id in (1, 4):
        return 'transf-filial'

    raise ValueError(f'company_id={company_id} nao reconhecido (esperado: 1, 4 ou 5)')


def resolver_fiscal_position(tipo_operacao: str, company_origem: int,
                              company_destino: int) -> int:
    """Resolve `fiscal_position_id` para uma direcao especifica.

    Args:
        tipo_operacao: chave de MATRIZ_INTERCOMPANY.
        company_origem: company_id origem.
        company_destino: company_id destino.

    Returns:
        fiscal_position_id Odoo.

    Raises:
        KeyError: se tipo_operacao nao existe.
        ValueError: se direcao (origem, destino) nao mapeada para o tipo.
    """
    op = get_operacao(tipo_operacao)
    key: Tuple[int, int] = (company_origem, company_destino)
    fp = op['fiscal_position_id'].get(key)
    if fp is None:
        raise ValueError(
            f"fiscal_position nao mapeada para tipo={tipo_operacao!r} "
            f"direcao=({company_origem}, {company_destino}). "
            f"Direcoes validas: {sorted(op['fiscal_position_id'].keys())}"
        )
    return fp
