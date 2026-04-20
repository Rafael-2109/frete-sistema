"""Testes stub do CarviaNfTransferenciaService (NF Triangular).

Cobre happy path das funcoes criticas:
  - eh_candidata_transferencia: raiz CNPJ emit == dest
  - validar_vinculo: happy path (NF candidata + CNPJ match + peso OK)
  - criar_vinculos: atomico (rollback em erro de validacao)

Usa o fixture `db` do conftest.py (cada teste em transacao revertida).
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from datetime import date


def _gerar_chave_44(prefixo: str = '3525') -> str:
    return (prefixo + uuid.uuid4().hex).ljust(44, '0')[:44]


def _criar_nf(
    db,
    numero_nf: str,
    cnpj_emitente: str,
    cnpj_destinatario: str,
    peso_bruto: float,
    chave: str = None,
):
    from app.carvia.models import CarviaNf
    nf = CarviaNf(
        numero_nf=numero_nf,
        serie_nf='1',
        chave_acesso_nf=chave or _gerar_chave_44(),
        data_emissao=date(2026, 4, 15),
        cnpj_emitente=cnpj_emitente,
        nome_emitente=f'Empresa {cnpj_emitente[:4]}',
        uf_emitente='SP',
        cidade_emitente='SAO PAULO',
        cnpj_destinatario=cnpj_destinatario,
        nome_destinatario=f'Empresa {cnpj_destinatario[:4]}',
        uf_destinatario='RJ',
        cidade_destinatario='RIO DE JANEIRO',
        valor_total=Decimal('10000.00'),
        peso_bruto=Decimal(str(peso_bruto)),
        peso_liquido=Decimal(str(peso_bruto * 0.9)),
        tipo_fonte='XML_NFE',
        status='ATIVA',
        criado_por='test',
    )
    db.session.add(nf)
    db.session.flush()
    return nf


# ---------------------------------------------------------------------------
# 1) eh_candidata_transferencia — raiz CNPJ emit/dest
# ---------------------------------------------------------------------------

def test_eh_candidata_transferencia_raiz_igual(db):
    """CNPJ emit e dest com mesma raiz de 8 digitos -> candidata."""
    from app.carvia.services.documentos.nf_transferencia_service import (
        CarviaNfTransferenciaService,
    )
    nf = _criar_nf(
        db, numero_nf='T001',
        cnpj_emitente='12345678000199',   # raiz: 12345678
        cnpj_destinatario='12345678000288',  # raiz: 12345678
        peso_bruto=1000.0,
    )
    assert CarviaNfTransferenciaService.eh_candidata_transferencia(nf) is True


def test_eh_candidata_transferencia_raiz_diferente(db):
    """CNPJ emit e dest de empresas diferentes -> NAO candidata."""
    from app.carvia.services.documentos.nf_transferencia_service import (
        CarviaNfTransferenciaService,
    )
    nf = _criar_nf(
        db, numero_nf='V001',
        cnpj_emitente='11111111000100',
        cnpj_destinatario='99999999000100',
        peso_bruto=500.0,
    )
    assert CarviaNfTransferenciaService.eh_candidata_transferencia(nf) is False


def test_eh_candidata_transferencia_cnpj_vazio(db):
    """CNPJ emit ou dest vazios -> NAO candidata."""
    from app.carvia.services.documentos.nf_transferencia_service import (
        CarviaNfTransferenciaService,
    )
    assert CarviaNfTransferenciaService.eh_candidata_transferencia(None) is False


# ---------------------------------------------------------------------------
# 2) validar_vinculo + criar_vinculos happy path (1:1)
# ---------------------------------------------------------------------------

def test_criar_vinculos_happy_path_1_para_1(db):
    """Fluxo 1:1: NF transf (raiz igual) -> 1 NF venda (peso OK, CNPJ match)."""
    from app.carvia.services.documentos.nf_transferencia_service import (
        CarviaNfTransferenciaService,
    )

    # NF transf (filial SP -> filial RJ): mesma raiz CNPJ
    nf_transf = _criar_nf(
        db, numero_nf='T100',
        cnpj_emitente='22222222000100',   # filial SP
        cnpj_destinatario='22222222000288',  # filial RJ
        peso_bruto=1000.0,
    )
    # NF venda (filial RJ -> cliente): emit = dest da transf
    nf_venda = _criar_nf(
        db, numero_nf='V100',
        cnpj_emitente='22222222000288',   # filial RJ = dest transf
        cnpj_destinatario='77777777000155',  # cliente final
        peso_bruto=900.0,
    )

    ok, motivo, dados = CarviaNfTransferenciaService.validar_vinculo(
        nf_transf.id, [nf_venda.id],
    )
    assert ok is True, f'Validacao falhou: {motivo}'
    assert dados['peso']['peso_transf'] == 1000.0
    assert dados['peso']['peso_vendas_soma'] == 900.0
    assert dados['peso']['excede'] is False


def test_criar_vinculos_excede_peso_bloqueia(db):
    """Peso vendas > peso transf -> rollback, sem vinculos persistidos."""
    from app.carvia.services.documentos.nf_transferencia_service import (
        CarviaNfTransferenciaService,
    )
    from app.carvia.models.documentos import CarviaNfVinculoTransferencia

    nf_transf = _criar_nf(
        db, numero_nf='T200',
        cnpj_emitente='33333333000100',
        cnpj_destinatario='33333333000288',
        peso_bruto=500.0,
    )
    nf_venda = _criar_nf(
        db, numero_nf='V200',
        cnpj_emitente='33333333000288',
        cnpj_destinatario='88888888000155',
        peso_bruto=800.0,  # excede 500
    )

    ok, motivo, vinculos = CarviaNfTransferenciaService.criar_vinculos(
        nf_transf.id, [nf_venda.id], criado_por='test',
    )
    assert ok is False
    assert 'excede' in motivo.lower()
    # Nao ha vinculos persistidos
    count = CarviaNfVinculoTransferencia.query.filter_by(
        nf_transferencia_id=nf_transf.id
    ).count()
    assert count == 0


def test_criar_vinculos_cnpj_emit_venda_diferente(db):
    """NF venda cujo emitente nao bate com dest da transf -> bloqueia."""
    from app.carvia.services.documentos.nf_transferencia_service import (
        CarviaNfTransferenciaService,
    )

    nf_transf = _criar_nf(
        db, numero_nf='T300',
        cnpj_emitente='44444444000100',
        cnpj_destinatario='44444444000288',
        peso_bruto=1000.0,
    )
    nf_venda = _criar_nf(
        db, numero_nf='V300',
        cnpj_emitente='55555555000100',  # empresa diferente — nao bate
        cnpj_destinatario='99999999000155',
        peso_bruto=500.0,
    )
    ok, motivo, _ = CarviaNfTransferenciaService.validar_vinculo(
        nf_transf.id, [nf_venda.id],
    )
    assert ok is False
    assert 'emitente' in motivo.lower() or 'destinatario' in motivo.lower()
