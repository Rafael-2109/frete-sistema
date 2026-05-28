"""Testes do agregador `em_transito_por_destino` (Fix 2 + Fix 3 do 2026-05-28).

- Fix 2: NFs com flag `NfTransferenciaDesconsiderada` saem do calculo.
- Fix 3: linhas com CFOPs de retorno de insumo industrializacao
  (5902/5903/6902/6903) NAO entram no em_transito do destino
  (insumos foram consumidos, so o produto acabado existe).
"""
from datetime import date
from decimal import Decimal

import pytest

from app import db as _db
from app.recebimento.models import (
    NfTransferenciaSnapshot, NfTransferenciaProdutoSnapshot,
    NfTransferenciaDesconsiderada,
)
from app.recebimento.services.nf_transferencia_service import (
    NfTransferenciaService,
)


def _make_nf(account_move_id, *, status='PENDENTE_PICKING',
             destino='FB', origem='LF', name='SDTRA/2026/T01'):
    nf = NfTransferenciaSnapshot(
        account_move_id_origem=account_move_id,
        account_move_name_origem=name,
        company_origem=origem,
        company_destino=destino,
        data_emissao=date(2026, 5, 27),
        valor_total=Decimal('1000'),
        state_nf_origem='posted',
        status_consolidado=status,
    )
    _db.session.add(nf)
    _db.session.flush()
    return nf


def _add_produto(nf, cod, qtd, *, cfop=None, nome=None):
    p = NfTransferenciaProdutoSnapshot(
        nf_snapshot_id=nf.id,
        cod_produto=cod,
        nome_produto=nome or f'PROD {cod}',
        quantidade=Decimal(str(qtd)),
        cfop=cfop,
    )
    _db.session.add(p)
    return p


@pytest.fixture(autouse=True)
def _wipe(db):
    """Limpa snapshot ANTES de cada teste (testes leem PROD-shape)."""
    _db.session.query(NfTransferenciaDesconsiderada).delete()
    _db.session.query(NfTransferenciaProdutoSnapshot).delete()
    _db.session.query(NfTransferenciaSnapshot).delete()
    _db.session.flush()


def test_agregador_soma_produtos_de_nf_pendente(db):
    nf = _make_nf(account_move_id=900001)
    _add_produto(nf, 'TESTPROD-A', 100, cfop='5152')
    _add_produto(nf, 'TESTPROD-A', 50, cfop='5152')   # mesmo cod => soma
    _add_produto(nf, 'TESTPROD-B', 30, cfop='5949')
    _db.session.flush()

    out = NfTransferenciaService.agregar_em_transito_por_destino()
    assert 'TESTPROD-A' in out
    assert out['TESTPROD-A']['fb'] == Decimal('150')
    assert 'TESTPROD-B' in out
    assert out['TESTPROD-B']['fb'] == Decimal('30')


def test_agregador_ignora_nf_concluida_ou_cancelada(db):
    """Apenas status PENDENTE_* entra no em_transito."""
    nf_pend = _make_nf(account_move_id=900010, status='PENDENTE_PICKING')
    nf_concl = _make_nf(account_move_id=900011, status='CONCLUIDO')
    nf_canc = _make_nf(account_move_id=900012, status='CANCELADA')
    _add_produto(nf_pend, 'TESTPROD-S', 10, cfop='5152')
    _add_produto(nf_concl, 'TESTPROD-S', 99, cfop='5152')
    _add_produto(nf_canc, 'TESTPROD-S', 77, cfop='5152')
    _db.session.flush()

    out = NfTransferenciaService.agregar_em_transito_por_destino()
    assert out['TESTPROD-S']['fb'] == Decimal('10')


def test_agregador_exclui_nf_flagada_como_desconsiderada(db):
    """Fix 2: NF marcada em NfTransferenciaDesconsiderada NAO entra."""
    nf_normal = _make_nf(account_move_id=900020)
    nf_descon = _make_nf(account_move_id=900021, name='SDTRA/2026/T02')
    _add_produto(nf_normal, 'TESTPROD-D', 100, cfop='5152')
    _add_produto(nf_descon, 'TESTPROD-D', 500, cfop='5152')

    _db.session.add(NfTransferenciaDesconsiderada(
        account_move_id_origem=900021,
        motivo='Ja ajustada manualmente no estoque',
        criado_por='pytest',
    ))
    _db.session.flush()

    out = NfTransferenciaService.agregar_em_transito_por_destino()
    # Soh a NF nao flagada conta: 100, e nao 600.
    assert out['TESTPROD-D']['fb'] == Decimal('100')


def test_agregador_ignora_cfops_retorno_insumo_industrializacao(db):
    """Fix 3: linhas com CFOP 5902/5903/6902/6903 NAO entram (insumos
    consumidos na industrializacao; so o PA existe no destino)."""
    nf = _make_nf(account_move_id=900030, name='RETNA/2026/TST', origem='LF',
                  destino='FB')
    # 1 PA (5124) -> conta; 2 insumos (5902 e 5903) -> NAO contam
    _add_produto(nf, 'TESTPROD-PA', 80, cfop='5124')
    _add_produto(nf, 'TESTPROD-INSUMO-A', 200, cfop='5902')
    _add_produto(nf, 'TESTPROD-INSUMO-B', 350, cfop='5903')
    _db.session.flush()

    out = NfTransferenciaService.agregar_em_transito_por_destino()
    assert out['TESTPROD-PA']['fb'] == Decimal('80')
    # Insumos nao devem aparecer no agregado em_transito
    assert 'TESTPROD-INSUMO-A' not in out
    assert 'TESTPROD-INSUMO-B' not in out


def test_agregador_aceita_cfop_com_espaco_extra(db):
    """Snapshot grava CFOP com espaco extra ('5902 '). Filtro usa TRIM."""
    nf = _make_nf(account_move_id=900040, name='RETNA/2026/TST2')
    _add_produto(nf, 'TESTPROD-X', 99, cfop='5902 ')  # espaco extra
    _db.session.flush()

    out = NfTransferenciaService.agregar_em_transito_por_destino()
    # Mesmo com espaco extra, deve ser identificado como retorno de insumo.
    assert 'TESTPROD-X' not in out
