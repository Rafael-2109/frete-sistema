"""Testes do ciclo Custo de Entrega <-> Fatura Transportadora SEM o status
VINCULADO_FT (removido em 2026-06-22).

Invariante nova: o vinculo a uma FT e indicado pela FK
`fatura_transportadora_id`, NAO por um status. CE vinculado = PENDENTE + FK.
Status validos: PENDENTE / PAGO / CANCELADO.
"""

from __future__ import annotations

from datetime import date


def _transportadora(db):
    from app.transportadoras.models import Transportadora
    t = Transportadora(
        cnpj='99999999000188', razao_social='TRANSP CE-FT',
        cidade='SAO PAULO', uf='SP',
    )
    db.session.add(t)
    db.session.flush()
    return t


def _ft(db, transp):
    from app.carvia.models import CarviaFaturaTransportadora
    ft = CarviaFaturaTransportadora(
        transportadora_id=transp.id, numero_fatura='FT-CEFT-1',
        data_emissao=date(2026, 6, 6), valor_total=100,
        criado_por='test',
    )
    db.session.add(ft)
    db.session.flush()
    return ft


def _ce(db, status='PENDENTE'):
    from app.carvia.models import CarviaCustoEntrega
    ce = CarviaCustoEntrega(
        numero_custo='CE-CEFT-1', tipo_custo='OUTROS', valor=100,
        data_custo=date(2026, 6, 6), status=status, criado_por='test',
    )
    db.session.add(ce)
    db.session.flush()
    return ce


def test_vincular_mantem_pendente_e_seta_fk(db):
    from app.carvia.services.financeiro.custo_entrega_fatura_service import (
        CustoEntregaFaturaService,
    )
    transp = _transportadora(db)
    ft = _ft(db, transp)
    ce = _ce(db)

    res = CustoEntregaFaturaService.vincular(ce.id, ft.id, 'test')
    assert res['sucesso'] is True
    assert ce.status == 'PENDENTE'           # nao vira VINCULADO_FT
    assert ce.fatura_transportadora_id == ft.id


def test_desvincular_volta_pendente_sem_fk(db):
    from app.carvia.services.financeiro.custo_entrega_fatura_service import (
        CustoEntregaFaturaService,
    )
    transp = _transportadora(db)
    ft = _ft(db, transp)
    ce = _ce(db)
    CustoEntregaFaturaService.vincular(ce.id, ft.id, 'test')

    CustoEntregaFaturaService.desvincular(ce.id, 'test')
    assert ce.status == 'PENDENTE'
    assert ce.fatura_transportadora_id is None


def test_propagacao_pago_e_despropagacao(db):
    """FT paga propaga PAGO ao CE PENDENTE+FK; desconciliar reverte a PENDENTE
    (a FK permanece)."""
    from app.carvia.services.financeiro.custo_entrega_fatura_service import (
        CustoEntregaFaturaService,
    )
    from app.carvia.services.financeiro.carvia_conciliacao_service import (
        CarviaConciliacaoService,
    )
    transp = _transportadora(db)
    ft = _ft(db, transp)
    ce = _ce(db)
    CustoEntregaFaturaService.vincular(ce.id, ft.id, 'test')

    # FT paga -> propaga PAGO
    CarviaConciliacaoService._propagar_status_ces_cobertos(ft.id, 'PAGO', 'test')
    assert ce.status == 'PAGO'
    assert (ce.pago_por or '').startswith('auto:')
    assert ce.fatura_transportadora_id == ft.id   # FK intacta

    # FT desconciliada -> reverte para PENDENTE (NAO VINCULADO_FT), FK intacta
    CarviaConciliacaoService._propagar_status_ces_cobertos(ft.id, 'PENDENTE', 'test')
    assert ce.status == 'PENDENTE'
    assert ce.pago_por is None
    assert ce.fatura_transportadora_id == ft.id


def test_vinculado_ft_nao_e_mais_status_valido(db):
    from app.carvia.models import CarviaCustoEntrega
    assert 'VINCULADO_FT' not in CarviaCustoEntrega.STATUS_CHOICES
    assert CarviaCustoEntrega.STATUS_CHOICES == ['PENDENTE', 'PAGO', 'CANCELADO']
