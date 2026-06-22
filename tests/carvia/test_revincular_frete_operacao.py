"""Testes do resolvedor ESTRITO frete<->operacao (CarviaFreteService).

Contexto (auditoria 2026-06-22): a importacao do CTe CarVia cria a CarviaOperacao
+ junction carvia_operacao_nfs mas NUNCA atualiza CarviaFrete.operacao_id; em
producao 110 de 114 fretes "sem operacao" tinham o CTe existente. O backfill e o
hook do import reconciliam via `revincular_frete_estrito`, que SO grava quando ha
UMA operacao candidata (regra Rafael: ambiguo -> pula e lista, nao adivinha).

Usa o fixture `db` do conftest.py (transacao revertida por teste).
"""
from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import datetime
from types import SimpleNamespace

from app.carvia.services.documentos.carvia_frete_service import CarviaFreteService


def _sfx() -> str:
    return uuid.uuid4().hex[:6]


def _chave44(p='3525') -> str:
    return (p + uuid.uuid4().hex).ljust(44, '0')[:44]


def _criar_nf(db, numero, status='ATIVA'):
    from app.carvia.models import CarviaNf
    nf = CarviaNf(
        numero_nf=numero,
        cnpj_emitente='12345678000100',
        tipo_fonte='TEST',
        status=status,
        criado_por='test',
    )
    db.session.add(nf)
    db.session.flush()
    return nf


def _criar_operacao(db, cte_numero, status='RASCUNHO', cte_valor=1000.0):
    from app.carvia.models import CarviaOperacao
    op = CarviaOperacao(
        cte_numero=cte_numero,
        cte_chave_acesso=_chave44(),
        cte_valor=Decimal(str(cte_valor)),
        cte_data_emissao=datetime(2026, 4, 1).date(),
        cnpj_cliente='12345678000100',
        nome_cliente='Cliente Teste',
        uf_origem='SP',
        cidade_origem='SAO PAULO',
        uf_destino='RJ',
        cidade_destino='RIO DE JANEIRO',
        status=status,
        tipo_entrada='IMPORTADO',
        criado_por='test',
    )
    db.session.add(op)
    db.session.flush()
    return op


def _vincular(db, op, nf):
    from app.carvia.models import CarviaOperacaoNf
    j = CarviaOperacaoNf(operacao_id=op.id, nf_id=nf.id)
    db.session.add(j)
    db.session.flush()
    return j


def _frete_mock(numeros_nfs, operacao_id=None):
    return SimpleNamespace(
        id=999, numeros_nfs=numeros_nfs, operacao_id=operacao_id,
        valor_venda=None, fatura_cliente_id=None,
    )


# --- resolver_operacao_unica_por_nfs -------------------------------------

def test_resolver_unica(db):
    n = f'N{_sfx()}'
    nf = _criar_nf(db, n)
    op = _criar_operacao(db, f'CTe-{_sfx()}')
    _vincular(db, op, nf)
    res = CarviaFreteService.resolver_operacao_unica_por_nfs([n])
    assert res['status'] == 'UNICA'
    assert res['operacao'].id == op.id


def test_resolver_ambigua(db):
    n1, n2 = f'A{_sfx()}', f'B{_sfx()}'
    nf1, nf2 = _criar_nf(db, n1), _criar_nf(db, n2)
    op1, op2 = _criar_operacao(db, f'CTe-{_sfx()}'), _criar_operacao(db, f'CTe-{_sfx()}')
    _vincular(db, op1, nf1)
    _vincular(db, op2, nf2)
    res = CarviaFreteService.resolver_operacao_unica_por_nfs([n1, n2])
    assert res['status'] == 'AMBIGUA'
    assert set(res['candidatas']) == {op1.id, op2.id}
    assert res['operacao'] is None


def test_resolver_nenhuma_sem_junction(db):
    n = f'S{_sfx()}'
    _criar_nf(db, n)  # NF existe mas sem CTe vinculado
    res = CarviaFreteService.resolver_operacao_unica_por_nfs([n])
    assert res['status'] == 'NENHUMA'


def test_resolver_ignora_operacao_cancelada(db):
    n = f'C{_sfx()}'
    nf = _criar_nf(db, n)
    op = _criar_operacao(db, f'CTe-{_sfx()}', status='CANCELADO')
    _vincular(db, op, nf)
    res = CarviaFreteService.resolver_operacao_unica_por_nfs([n])
    assert res['status'] == 'NENHUMA'  # operacao cancelada nao conta


def test_resolver_ignora_nf_cancelada(db):
    n = f'X{_sfx()}'
    nf = _criar_nf(db, n, status='CANCELADA')
    op = _criar_operacao(db, f'CTe-{_sfx()}')
    _vincular(db, op, nf)
    res = CarviaFreteService.resolver_operacao_unica_por_nfs([n])
    assert res['status'] == 'NENHUMA'  # NF nao-ATIVA nao resolve


# --- revincular_frete_estrito --------------------------------------------

def test_revincular_no_op_se_ja_vinculado(db):
    frete = _frete_mock('123', operacao_id=42)
    res = CarviaFreteService.revincular_frete_estrito(frete)
    assert res['status'] == 'JA_VINCULADO'
    assert frete.operacao_id == 42  # nao sobrescreve


def test_revincular_grava_se_unica(db):
    n = f'G{_sfx()}'
    nf = _criar_nf(db, n)
    op = _criar_operacao(db, f'CTe-{_sfx()}')
    _vincular(db, op, nf)
    frete = _frete_mock(n)
    res = CarviaFreteService.revincular_frete_estrito(frete)
    assert res['status'] == 'UNICA'
    assert frete.operacao_id == op.id  # gravou
    assert frete.valor_venda == 1000.0  # propagou cte_valor


def test_revincular_pula_se_ambigua(db):
    n1, n2 = f'P{_sfx()}', f'Q{_sfx()}'
    nf1, nf2 = _criar_nf(db, n1), _criar_nf(db, n2)
    op1, op2 = _criar_operacao(db, f'CTe-{_sfx()}'), _criar_operacao(db, f'CTe-{_sfx()}')
    _vincular(db, op1, nf1)
    _vincular(db, op2, nf2)
    frete = _frete_mock(f'{n1},{n2}')
    res = CarviaFreteService.revincular_frete_estrito(frete)
    assert res['status'] == 'AMBIGUA'
    assert frete.operacao_id is None  # NAO gravou (regra: pula)
