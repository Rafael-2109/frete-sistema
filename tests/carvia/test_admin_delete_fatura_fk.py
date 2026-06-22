"""Testes do fix I4 — hard-delete de fatura CarVia com frete vinculado.

REVISAO_ARQUITETURA_2026 I4: a FK carvia_fretes.fatura_*_id e declarada sem
ON DELETE (NO ACTION no Postgres). Antes do fix, excluir uma fatura com frete
vinculado lancava IntegrityError no commit (HTTP 500). O fix nullifica
CarviaFrete (+ ContaCorrente + status do CustoEntrega) ANTES do delete.

Estrategia de teste: o fixture `db` roda em begin_nested()+rollback(). O service
faz db.session.commit() ao final, que escaparia do savepoint — por isso o commit
e substituido por flush() durante a chamada, mantendo tudo dentro do savepoint
revertido no teardown.
"""
from datetime import date
from unittest.mock import patch


def _criar_transportadora(db):
    from app.transportadoras.models import Transportadora
    transp = Transportadora(
        cnpj='99999999000199',
        razao_social='TRANSP TESTE I4',
        cidade='SAO PAULO',
        uf='SP',
    )
    db.session.add(transp)
    db.session.flush()
    return transp


def _criar_frete(db, transp, **fks):
    from app.carvia.models import CarviaFrete
    frete = CarviaFrete(
        transportadora_id=transp.id,
        cnpj_emitente='11111111000111',
        cnpj_destino='22222222000122',
        uf_destino='SP',
        cidade_destino='SAO PAULO',
        tipo_carga='DIRETA',
        criado_por='test@bot',
        **fks,
    )
    db.session.add(frete)
    db.session.flush()
    return frete


def test_excluir_fatura_transportadora_com_frete_nao_quebra_fk(db):
    from app.carvia.models import (
        CarviaFaturaTransportadora, CarviaFrete, CarviaCustoEntrega,
    )
    from app.carvia.services.admin.admin_service import AdminService

    transp = _criar_transportadora(db)
    fatura = CarviaFaturaTransportadora(
        transportadora_id=transp.id,
        numero_fatura='FT-TESTE-I4',
        data_emissao=date(2026, 6, 6),
        valor_total=100,
        criado_por='test@bot',
    )
    db.session.add(fatura)
    db.session.flush()

    frete = _criar_frete(db, transp, fatura_transportadora_id=fatura.id)
    frete_id = frete.id

    # CE vinculado a FT (PENDENTE + FK) deve continuar PENDENTE e perder a FK ao
    # excluir a fatura (status VINCULADO_FT removido em 2026-06-22).
    ce = CarviaCustoEntrega(
        numero_custo='CE-TESTE-I4',
        tipo_custo='OUTROS',
        valor=50,
        data_custo=date(2026, 6, 6),
        status='PENDENTE',
        fatura_transportadora_id=fatura.id,
        criado_por='test@bot',
    )
    db.session.add(ce)
    db.session.flush()
    ce_id = ce.id

    svc = AdminService()
    with patch.object(db.session, 'commit', db.session.flush):
        resultado = svc.excluir_fatura_transportadora(
            fatura.id, 'teste de exclusao i4', 'test@bot',
        )

    # bulk update usou synchronize_session=False — expirar p/ reler do banco
    db.session.expire_all()

    assert resultado['sucesso'] is True, resultado.get('mensagem')
    # Fatura realmente removida
    assert db.session.get(CarviaFaturaTransportadora, fatura.id) is None
    # Frete teve a FK desvinculada (sem IntegrityError)
    frete_db = db.session.get(CarviaFrete, frete_id)
    assert frete_db is not None
    assert frete_db.fatura_transportadora_id is None
    # CE voltou para PENDENTE e sem FK
    ce_db = db.session.get(CarviaCustoEntrega, ce_id)
    assert ce_db.fatura_transportadora_id is None
    assert ce_db.status == 'PENDENTE'


def test_excluir_fatura_cliente_com_frete_nao_quebra_fk(db):
    from app.carvia.models import CarviaFaturaCliente, CarviaFrete
    from app.carvia.services.admin.admin_service import AdminService

    transp = _criar_transportadora(db)
    fatura = CarviaFaturaCliente(
        cnpj_cliente='33333333000133',
        numero_fatura='FC-TESTE-I4',
        data_emissao=date(2026, 6, 6),
        valor_total=200,
        status='PENDENTE',
        criado_por='test@bot',
    )
    db.session.add(fatura)
    db.session.flush()

    frete = _criar_frete(db, transp, fatura_cliente_id=fatura.id)
    frete_id = frete.id

    svc = AdminService()
    with patch.object(db.session, 'commit', db.session.flush):
        resultado = svc.excluir_fatura_cliente(
            fatura.id, 'teste de exclusao i4', 'test@bot',
        )

    db.session.expire_all()

    assert resultado['sucesso'] is True, resultado.get('mensagem')
    assert db.session.get(CarviaFaturaCliente, fatura.id) is None
    frete_db = db.session.get(CarviaFrete, frete_id)
    assert frete_db is not None
    assert frete_db.fatura_cliente_id is None
