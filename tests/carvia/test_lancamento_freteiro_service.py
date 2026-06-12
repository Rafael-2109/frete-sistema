"""Testes do LancamentoFreteiroCarviaService — espelho CarVia do fechamento
de freteiros (decisao Rafael 2026-06-12, origem IMP-2026-06-10-005).

Cobre: emissao feliz (FT CONFERIDA + fretes APROVADO/FATURADO + subs sinteticos
+ itens de detalhe), validacoes (outra transportadora, ja faturado, cancelado,
valor invalido), unicidade do numero_fatura, reuso de subcontrato existente e
o criterio de pendencia do listar (valor_cte IS NULL).

O service NAO comita (flush only) — compativel com o fixture `db` em savepoint.
"""
from datetime import date
from decimal import Decimal

import pytest

from app.carvia.services.financeiro.lancamento_freteiro_service import (
    emitir_fatura_freteiro_carvia,
    listar_fretes_carvia_pendentes_freteiro,
)


def _criar_embarque(db):
    from app.embarques.models import Embarque
    e = Embarque(status='ativo', criado_por='test@bot')
    db.session.add(e)
    db.session.flush()
    return e


def _criar_freteiro(db, cnpj='88888888000188'):
    from app.transportadoras.models import Transportadora
    t = Transportadora(
        cnpj=cnpj,
        razao_social='FRETEIRO CARVIA TESTE',
        cidade='SAO PAULO',
        uf='SP',
        freteiro=True,
    )
    db.session.add(t)
    db.session.flush()
    return t


def _criar_frete_carvia(db, transp, *, embarque_id=None, valor_cotado=162.55,
                        valor_cte=None, status='PENDENTE', numeros_nfs='5187',
                        cnpj_destino='22222222000122'):
    from app.carvia.models import CarviaFrete
    f = CarviaFrete(
        transportadora_id=transp.id,
        embarque_id=embarque_id,
        cnpj_emitente='11111111000111',
        nome_emitente='EMITENTE T',
        cnpj_destino=cnpj_destino,
        nome_destino='CLIENTE CARVIA T',
        uf_destino='SP',
        cidade_destino='SAO PAULO',
        tipo_carga='DIRETA',
        peso_total=164.0,
        valor_total_nfs=5000.0,
        quantidade_nfs=1,
        numeros_nfs=numeros_nfs,
        valor_cotado=valor_cotado,
        valor_cte=valor_cte,
        status=status,
        criado_por='test@bot',
    )
    db.session.add(f)
    db.session.flush()
    return f


def test_emitir_fatura_freteiro_carvia_feliz(db):
    from app.carvia.models import (
        CarviaFaturaTransportadora, CarviaFaturaTransportadoraItem,
        CarviaSubcontrato,
    )
    transp = _criar_freteiro(db)
    f1 = _criar_frete_carvia(db, transp, valor_cotado=162.55)
    f2 = _criar_frete_carvia(db, transp, valor_cotado=100.00, numeros_nfs='5188')

    res = emitir_fatura_freteiro_carvia(
        transportadora_id=transp.id,
        itens=[
            {'frete_id': f1.id, 'valor_considerado': 180.00},
            {'frete_id': f2.id, 'valor_considerado': 100.00},
        ],
        data_vencimento=date(2026, 6, 30),
        usuario_nome='Rafael Teste',
        observacoes='obs teste',
    )

    assert res['fretes'] == 2
    assert res['subcontratos_criados'] == 2
    assert res['valor_total'] == pytest.approx(280.00)

    ft = db.session.get(CarviaFaturaTransportadora, res['fatura_id'])
    assert ft.status_conferencia == 'CONFERIDO'
    assert ft.conferido_por == 'Rafael Teste'
    assert ft.status_pagamento == 'PENDENTE'  # pagamento via conciliacao R11
    assert float(ft.valor_total) == pytest.approx(280.00)
    assert ft.numero_fatura.startswith('Fech FRETEIRO CARVIA TESTE')
    assert ft.vencimento == date(2026, 6, 30)

    # Frete 1: valores + conferencia automatica + lifecycle
    assert float(f1.valor_considerado) == pytest.approx(180.00)
    assert float(f1.valor_cte) == pytest.approx(180.00)   # sai da lista de pendentes
    assert float(f1.valor_pago) == pytest.approx(180.00)
    assert f1.status_conferencia == 'APROVADO'
    assert f1.conferido_por == 'Rafael Teste'
    assert f1.status == 'FATURADO'
    assert f1.fatura_transportadora_id == ft.id
    assert f1.detalhes_conferencia['origem'] == 'lancamento_freteiros_unificado'
    assert f1.detalhes_conferencia['valor_cotado'] == pytest.approx(162.55)

    # Subcontrato sintetico (freteiro nao emite CTe — cte_numero "Frete (...)")
    sub = CarviaSubcontrato.query.filter_by(frete_id=f1.id).first()
    assert sub is not None
    assert sub.status == 'FATURADO'
    assert sub.fatura_transportadora_id == ft.id
    assert sub.cte_numero.startswith('Sub-')  # gerador nativo R8 (varchar(20))
    assert float(sub.valor_acertado) == pytest.approx(180.00)

    # Itens de detalhe da FT (LinkingService)
    itens = CarviaFaturaTransportadoraItem.query.filter_by(
        fatura_transportadora_id=ft.id
    ).all()
    assert len(itens) == 2


def test_emitir_valida_transportadora_e_estado(db):
    transp = _criar_freteiro(db)
    outra = _criar_freteiro(db, cnpj='77777777000177')
    frete_outra = _criar_frete_carvia(db, outra)
    with pytest.raises(ValueError, match='outra transportadora'):
        emitir_fatura_freteiro_carvia(
            transportadora_id=transp.id,
            itens=[{'frete_id': frete_outra.id, 'valor_considerado': 10}],
            data_vencimento=date(2026, 6, 30),
            usuario_nome='T',
        )

    cancelado = _criar_frete_carvia(db, transp, status='CANCELADO')
    with pytest.raises(ValueError, match='cancelado'):
        emitir_fatura_freteiro_carvia(
            transportadora_id=transp.id,
            itens=[{'frete_id': cancelado.id, 'valor_considerado': 10}],
            data_vencimento=date(2026, 6, 30),
            usuario_nome='T',
        )

    valido = _criar_frete_carvia(db, transp)
    with pytest.raises(ValueError, match='invalido'):
        emitir_fatura_freteiro_carvia(
            transportadora_id=transp.id,
            itens=[{'frete_id': valido.id, 'valor_considerado': 0}],
            data_vencimento=date(2026, 6, 30),
            usuario_nome='T',
        )

    with pytest.raises(ValueError, match='Nenhum frete'):
        emitir_fatura_freteiro_carvia(
            transportadora_id=transp.id,
            itens=[],
            data_vencimento=date(2026, 6, 30),
            usuario_nome='T',
        )


def test_emitir_bloqueia_frete_ja_faturado(db):
    transp = _criar_freteiro(db)
    f1 = _criar_frete_carvia(db, transp)
    emitir_fatura_freteiro_carvia(
        transportadora_id=transp.id,
        itens=[{'frete_id': f1.id, 'valor_considerado': 162.55}],
        data_vencimento=date(2026, 6, 30),
        usuario_nome='T',
    )
    with pytest.raises(ValueError, match='ja vinculado a fatura'):
        emitir_fatura_freteiro_carvia(
            transportadora_id=transp.id,
            itens=[{'frete_id': f1.id, 'valor_considerado': 162.55}],
            data_vencimento=date(2026, 6, 30),
            usuario_nome='T',
        )


def test_numero_fatura_unico_ganha_sufixo(db):
    transp = _criar_freteiro(db)
    f1 = _criar_frete_carvia(db, transp)
    f2 = _criar_frete_carvia(db, transp, numeros_nfs='5189')

    r1 = emitir_fatura_freteiro_carvia(
        transportadora_id=transp.id,
        itens=[{'frete_id': f1.id, 'valor_considerado': 100}],
        data_vencimento=date(2026, 6, 30),
        usuario_nome='T',
    )
    r2 = emitir_fatura_freteiro_carvia(
        transportadora_id=transp.id,
        itens=[{'frete_id': f2.id, 'valor_considerado': 100}],
        data_vencimento=date(2026, 6, 30),
        usuario_nome='T',
    )
    assert r1['numero_fatura'] != r2['numero_fatura']
    assert r2['numero_fatura'].endswith('(2)')
    assert len(r2['numero_fatura']) <= 50


def test_emitir_reusa_subcontrato_existente(db):
    from app.carvia.models import CarviaSubcontrato
    transp = _criar_freteiro(db)
    f1 = _criar_frete_carvia(db, transp)
    sub_pre = CarviaSubcontrato(
        transportadora_id=transp.id,
        cte_numero=None,
        valor_cotado=Decimal('162.55'),
        status='PENDENTE',
        criado_por='test@bot',
        frete_id=f1.id,
    )
    db.session.add(sub_pre)
    db.session.flush()

    res = emitir_fatura_freteiro_carvia(
        transportadora_id=transp.id,
        itens=[{'frete_id': f1.id, 'valor_considerado': 170}],
        data_vencimento=date(2026, 6, 30),
        usuario_nome='T',
    )
    assert res['subcontratos_criados'] == 0  # reusou
    assert sub_pre.status == 'FATURADO'
    assert sub_pre.fatura_transportadora_id == res['fatura_id']
    assert sub_pre.cte_numero and sub_pre.cte_numero.startswith('Sub-')


def test_listar_pendentes_criterio(db):
    transp = _criar_freteiro(db)
    pendente = _criar_frete_carvia(db, transp, embarque_id=None)
    # pendente exige embarque_id (agrupamento por embarque na tela)
    assert listar_fretes_carvia_pendentes_freteiro(transp.id) == []

    embarque = _criar_embarque(db)
    pendente.embarque_id = embarque.id
    db.session.flush()
    _criar_frete_carvia(db, transp, embarque_id=embarque.id, valor_cte=150.0,
                        cnpj_destino='33333333000133')   # ja acertado
    _criar_frete_carvia(db, transp, embarque_id=embarque.id, status='CANCELADO',
                        cnpj_destino='44444444000144')

    res = listar_fretes_carvia_pendentes_freteiro(transp.id)
    assert len(res) == 1
    assert res[0]['id'] == pendente.id
    assert res[0]['valor_cotado'] == pytest.approx(162.55)
    assert res[0]['valor_considerado'] == pytest.approx(162.55)  # fallback cotado
    assert res[0]['embarque_id'] == embarque.id
