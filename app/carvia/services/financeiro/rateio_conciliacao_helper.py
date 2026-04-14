"""Helper de rateio de conciliacao bancaria por sub/CE de uma Fatura Transportadora.

A `CarviaConciliacao` eh feita no nivel da `CarviaFaturaTransportadora` — o
campo desnormalizado `fatura.total_conciliado` reflete `SUM(valor_alocado)` de
todas as linhas de extrato vinculadas a fatura. Mas para exibir "Valor
Conciliado" por subcontrato ou custo de entrega individualmente, precisamos
ratear proporcionalmente pela base de `valor_considerado` (subs) e `valor`
(CEs).

Uso tipico:
    from app.carvia.services.financeiro.rateio_conciliacao_helper import (
        ratear_conciliacao_fatura,
    )

    rateio = ratear_conciliacao_fatura(fatura, subs_ativos, ces_ativos)
    valor_sub = rateio['por_sub'].get(sub.id, Decimal('0'))
    valor_ce  = rateio['por_ce'].get(ce.id, Decimal('0'))
    total     = rateio['total']

Regras:
- Se `fatura.total_conciliado <= 0`: retorna dicts vazios e total=0.
- Se base (soma de considerados + valores) <= 0: retorna total mas sem rateio
  (evita divisao por zero).
- Rateio eh arredondado para 2 casas decimais (quantize).
- Subs/CEs com status CANCELADO devem ser filtrados PELO CALLER — o helper
  nao aplica filtro de status.
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, Iterable


def ratear_conciliacao_fatura(
    fatura,
    subs_ativos: Iterable,
    ces_ativos: Iterable,
) -> Dict:
    """Rateia `fatura.total_conciliado` proporcionalmente entre subs e CEs.

    Args:
        fatura: CarviaFaturaTransportadora (precisa expor .total_conciliado)
        subs_ativos: iterable de CarviaSubcontrato nao-cancelados
        ces_ativos: iterable de CarviaCustoEntrega nao-cancelados

    Returns:
        {
            'por_sub': {sub.id: Decimal (2 casas)},
            'por_ce':  {ce.id:  Decimal (2 casas)},
            'total':   Decimal,
        }
    """
    total = Decimal(str(fatura.total_conciliado or 0))
    if total <= 0:
        return {'por_sub': {}, 'por_ce': {}, 'total': Decimal('0')}

    subs_list = list(subs_ativos)
    ces_list = list(ces_ativos)

    base_subs = sum(
        (Decimal(str(s.valor_considerado or 0)) for s in subs_list),
        Decimal('0'),
    )
    base_ces = sum(
        (Decimal(str(c.valor or 0)) for c in ces_list),
        Decimal('0'),
    )
    base = base_subs + base_ces

    if base <= 0:
        return {'por_sub': {}, 'por_ce': {}, 'total': total}

    q = Decimal('0.01')
    por_sub = {
        s.id: (
            total * Decimal(str(s.valor_considerado or 0)) / base
        ).quantize(q, rounding=ROUND_HALF_UP)
        for s in subs_list
    }
    por_ce = {
        c.id: (
            total * Decimal(str(c.valor or 0)) / base
        ).quantize(q, rounding=ROUND_HALF_UP)
        for c in ces_list
    }

    return {'por_sub': por_sub, 'por_ce': por_ce, 'total': total}
