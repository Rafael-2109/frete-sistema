"""Helper de rateio de conciliacao bancaria por sub/CE de uma Fatura Transportadora.

A `CarviaConciliacao` eh feita no nivel da `CarviaFaturaTransportadora` — o
campo desnormalizado `fatura.total_conciliado` reflete `SUM(valor_alocado)` de
todas as linhas de extrato vinculadas a fatura. Mas para exibir "Valor
Conciliado" por subcontrato ou custo de entrega individualmente, precisamos
ratear proporcionalmente pela base de `valor_considerado` (do Frete do sub)
e `valor` (CEs).

Phase 14 (2026-04-14): `CarviaSubcontrato.valor_considerado` foi removido;
a fonte canonica passou a ser `CarviaFrete.valor_considerado`. O helper
agora le via `sub.frete.valor_considerado` (fallback para `sub.valor_acertado`
e `sub.valor_cotado` — campos de CTe nao removidos — quando o sub nao tem
frete vinculado, caso legado).

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


def _valor_base_sub(s) -> Decimal:
    """Extrai o valor-base do subcontrato para rateio.

    Hierarquia pos-Phase 14 (Frete = unidade de analise de conferencia):
    1. `sub.frete.valor_considerado` (fonte canonica)
    2. `sub.valor_acertado` (valor negociado no CTe — legado, se sem frete)
    3. `sub.valor_cotado` (cotacao da tabela — legado, se sem frete)
    4. 0 (ultimo fallback)
    """
    if s.frete is not None and s.frete.valor_considerado is not None:
        return Decimal(str(s.frete.valor_considerado))
    if s.valor_acertado is not None:
        return Decimal(str(s.valor_acertado))
    if s.valor_cotado is not None:
        return Decimal(str(s.valor_cotado))
    return Decimal('0')


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

    # Pre-computa valores-base para evitar duplicacao (e N+1 em sub.frete)
    base_por_sub = {s.id: _valor_base_sub(s) for s in subs_list}
    base_por_ce = {c.id: Decimal(str(c.valor or 0)) for c in ces_list}

    base_subs = sum(base_por_sub.values(), Decimal('0'))
    base_ces = sum(base_por_ce.values(), Decimal('0'))
    base = base_subs + base_ces

    if base <= 0:
        return {'por_sub': {}, 'por_ce': {}, 'total': total}

    q = Decimal('0.01')
    por_sub = {
        sid: (total * valor / base).quantize(q, rounding=ROUND_HALF_UP)
        for sid, valor in base_por_sub.items()
    }
    por_ce = {
        cid: (total * valor / base).quantize(q, rounding=ROUND_HALF_UP)
        for cid, valor in base_por_ce.items()
    }

    return {'por_sub': por_sub, 'por_ce': por_ce, 'total': total}
