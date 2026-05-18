"""Tests para PreEtapaEstoqueService (D007).

Cenarios cobertos:
1. Sobra pura (Odoo > inv) consolida em MIGRAÇÃO do CD
2. Falta pura (Odoo < inv) pega da FB se disponivel
3. Falta pura sem FB vira ajuste positivo puro
4. Sobra + falta misto balanceia internamente (zero NF, zero positivo puro)
5. Lote inv sem nome usa 'P-15/05' agregado por produto
6. Multiplos lotes inv do mesmo produto
7. Quant sem lote pode doar para lote alvo
8. FIFO por quant_id para doacao interna
9. Lote alvo ja existente no CD mantido
10. Quants com reserva: warning emitido
11. company_id parametrizado funciona para FB (regressao)
12. Custo medio ponderado aplicado em ajuste puro

Spec: docs/inventario-2026-05/00-decisoes/D007-pre-etapa-cd-fb-minimizar-nf.md
"""
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from app.odoo.services.pre_etapa_estoque_service import (
    AjustePositivoPuroPlanejado,
    PlanoPreEtapa,
    PreEtapaEstoqueService,
    ResidualFbCdPlanejado,
    TransferenciaInternaPlanejada,
)


@pytest.fixture
def service():
    return PreEtapaEstoqueService(odoo=MagicMock())


def _quant(quant_id, lote_nome, qty, lot_id=None, reserved=0, location_id=32, value=0):
    """Helper para montar dict de quant."""
    return {
        'quant_id': quant_id,
        'lot_id': lot_id,
        'lote_nome': lote_nome,
        'quantity': float(qty),
        'reserved_quantity': float(reserved),
        'location_id': location_id,
        'value': float(value),
    }


def _inv(lote, qty, validade=None):
    """Helper para montar dict de linha de inventario."""
    return {
        'lote_inventariado': lote,
        'qtd_inventario': str(qty),
        'validade_inv': validade,
    }


# ============================================================
# 1. Sobra pura
# ============================================================

def test_sobra_pura_consolida_em_migracao_cd(service):
    """CD tem 100 un lote 'X', inv quer 0 (lote nao listado)
    → toda qty vira NEG para MIGRAÇÃO do CD."""
    quants_cd = [_quant(1, 'LOTE_X', 100, lot_id=10, value=64.34)]
    linhas_inv = []  # inv nao tem esse produto

    plano = service.planejar(
        cod_produto='4310177', company_id=4, location_id=32,
        quants_odoo=quants_cd, linhas_inv=linhas_inv,
    )

    assert len(plano.transferencias_internas) == 1
    t = plano.transferencias_internas[0]
    assert t.tipo == 'NEG'
    assert t.lote_origem_nome == 'LOTE_X'
    assert t.lote_destino_nome == 'MIGRAÇÃO'
    assert t.qty == 100.0
    assert t.lot_id_origem == 10
    assert plano.residual_fb_cd == []
    assert plano.ajustes_positivos_puros == []


# ============================================================
# 2. Falta pura pega da FB
# ============================================================

def test_falta_pura_pega_de_fb_se_disponivel(service):
    """CD tem 0, inv quer 100 de '26014', FB tem 200 → residual FB→CD 100 un."""
    quants_cd = []  # CD nao tem o produto
    linhas_inv = [_inv('26014', 100)]
    quants_fb = [_quant(99, 'LOTE_FB_QUALQUER', 200, lot_id=999, location_id=8, value=128.68)]

    plano = service.planejar(
        cod_produto='210030325', company_id=4, location_id=32,
        quants_odoo=quants_cd, linhas_inv=linhas_inv,
        quants_fb_disponivel=quants_fb,
    )

    assert plano.transferencias_internas == []
    assert len(plano.residual_fb_cd) == 1
    r = plano.residual_fb_cd[0]
    assert r.qty == 100.0
    assert r.lote_destino_cd_nome == '26014'
    assert r.lote_origem_fb_sugerido == 'LOTE_FB_QUALQUER'
    assert plano.ajustes_positivos_puros == []


# ============================================================
# 3. Falta pura sem FB vira ajuste positivo puro
# ============================================================

def test_falta_pura_sem_fb_vira_ajuste_positivo_puro(service):
    """CD tem 0, inv quer 50, FB tambem nao tem → ajuste positivo puro."""
    quants_cd = []
    linhas_inv = [_inv('26014', 50)]

    plano = service.planejar(
        cod_produto='210030325', company_id=4, location_id=32,
        quants_odoo=quants_cd, linhas_inv=linhas_inv,
        quants_fb_disponivel=[],
    )

    assert plano.transferencias_internas == []
    assert plano.residual_fb_cd == []
    assert len(plano.ajustes_positivos_puros) == 1
    a = plano.ajustes_positivos_puros[0]
    assert a.qty == 50.0
    assert a.lote_destino_nome == '26014'
    assert a.company_id == 4
    assert a.location_id == 32


# ============================================================
# 4. Sobra + falta misto: balanceia internamente
# ============================================================

def test_sobra_e_falta_misto_balanceiam_internamente(service):
    """CD tem 100 lote A, inv quer 100 lote B → tudo interno POS (zero NF, zero puro)."""
    quants_cd = [_quant(1, 'LOTE_A', 100, lot_id=10, value=64.34)]
    linhas_inv = [_inv('LOTE_B', 100)]

    plano = service.planejar(
        cod_produto='4310177', company_id=4, location_id=32,
        quants_odoo=quants_cd, linhas_inv=linhas_inv,
    )

    assert len(plano.transferencias_internas) == 1
    t = plano.transferencias_internas[0]
    assert t.tipo == 'POS'
    assert t.lote_origem_nome == 'LOTE_A'
    assert t.lote_destino_nome == 'LOTE_B'
    assert t.qty == 100.0
    assert plano.residual_fb_cd == []
    assert plano.ajustes_positivos_puros == []


# ============================================================
# 5. Lote inv sem nome usa 'P-15/05'
# ============================================================

def test_lote_inv_sem_nome_usa_P_15_05_agregado_por_produto(service):
    """3 linhas inv sem lote, qty 30+20+10 → agregado em 1 lote 'P-15/05' qty 60."""
    quants_cd = [_quant(1, 'LOTE_A', 60, lot_id=10, value=38.60)]
    linhas_inv = [_inv('', 30), _inv('', 20), _inv('', 10)]

    plano = service.planejar(
        cod_produto='4310177', company_id=4, location_id=32,
        quants_odoo=quants_cd, linhas_inv=linhas_inv,
    )

    # Deve gerar 1 transferencia POS LOTE_A → P-15/05 com qty 60
    assert len(plano.transferencias_internas) == 1
    t = plano.transferencias_internas[0]
    assert t.tipo == 'POS'
    assert t.lote_destino_nome == 'P-15/05'
    assert t.qty == 60.0


# ============================================================
# 6. Multiplos lotes inv do mesmo produto
# ============================================================

def test_multiplos_lotes_inv_do_mesmo_produto(service):
    """Inv quer 30 lote A + 20 lote B; CD tem 50 lote X → 2 transferencias POS."""
    quants_cd = [_quant(1, 'LOTE_X', 50, lot_id=10, value=32.17)]
    linhas_inv = [_inv('A', 30), _inv('B', 20)]

    plano = service.planejar(
        cod_produto='4310177', company_id=4, location_id=32,
        quants_odoo=quants_cd, linhas_inv=linhas_inv,
    )

    assert len(plano.transferencias_internas) == 2
    destinos = sorted(t.lote_destino_nome for t in plano.transferencias_internas)
    assert destinos == ['A', 'B']
    qty_total = sum(t.qty for t in plano.transferencias_internas)
    assert qty_total == 50.0


# ============================================================
# 7. Quant sem lote pode doar para lote alvo
# ============================================================

def test_quant_sem_lote_pode_doar_para_lote_alvo(service):
    """CD tem 100 sem lote (lot_id=None) → vira POS para lote alvo do inv."""
    quants_cd = [_quant(1, '', 100, lot_id=None, value=64.34)]
    linhas_inv = [_inv('26014', 100)]

    plano = service.planejar(
        cod_produto='210030325', company_id=4, location_id=32,
        quants_odoo=quants_cd, linhas_inv=linhas_inv,
    )

    assert len(plano.transferencias_internas) == 1
    t = plano.transferencias_internas[0]
    assert t.tipo == 'POS'
    assert t.lot_id_origem is None
    assert t.lote_origem_nome == ''
    assert t.lote_destino_nome == '26014'


# ============================================================
# 8. FIFO por quant_id para doacao interna
# ============================================================

def test_fifo_quant_id_para_doacao_interna(service):
    """Dois quants doadores, deficit menor que total → consome primeiro o
    de menor quant_id (FIFO)."""
    quants_cd = [
        _quant(100, 'LOTE_VELHO', 60, lot_id=999, value=38.60),    # FIFO 1o
        _quant(200, 'LOTE_NOVO', 60, lot_id=1000, value=38.60),    # FIFO 2o
    ]
    linhas_inv = [_inv('26014', 50)]  # quer so 50

    plano = service.planejar(
        cod_produto='4310177', company_id=4, location_id=32,
        quants_odoo=quants_cd, linhas_inv=linhas_inv,
    )

    # 50 deve vir do LOTE_VELHO (FIFO) — POS
    pos_transfers = [t for t in plano.transferencias_internas if t.tipo == 'POS']
    assert len(pos_transfers) == 1
    assert pos_transfers[0].lote_origem_nome == 'LOTE_VELHO'
    assert pos_transfers[0].qty == 50.0
    # Sobra: 10 do LOTE_VELHO + 60 do LOTE_NOVO → 2 NEG para MIGRAÇÃO
    neg_transfers = [t for t in plano.transferencias_internas if t.tipo == 'NEG']
    assert len(neg_transfers) == 2
    qty_neg = sum(t.qty for t in neg_transfers)
    assert qty_neg == 70.0


# ============================================================
# 9. Lote alvo ja existente no CD com saldo correto: sem transferencia
# ============================================================

def test_lote_alvo_ja_existente_com_saldo_correto_nao_gera_transferencia(service):
    """CD tem 100 lote A, inv quer 100 lote A → sem transferencia."""
    quants_cd = [_quant(1, 'A', 100, lot_id=10, value=64.34)]
    linhas_inv = [_inv('A', 100)]

    plano = service.planejar(
        cod_produto='4310177', company_id=4, location_id=32,
        quants_odoo=quants_cd, linhas_inv=linhas_inv,
    )

    assert plano.transferencias_internas == []
    assert plano.residual_fb_cd == []
    assert plano.ajustes_positivos_puros == []


# ============================================================
# 10. Quant com reserva: warning emitido
# ============================================================

def test_quants_com_reserva_emitem_warning(service):
    """Quant com qty=100 e reserved=80 — doar 50 deixaria 50 < 80 reservada → warning."""
    quants_cd = [_quant(1, 'LOTE_X', 100, lot_id=10, reserved=80, value=64.34)]
    linhas_inv = []  # quer doar tudo

    plano = service.planejar(
        cod_produto='4310177', company_id=4, location_id=32,
        quants_odoo=quants_cd, linhas_inv=linhas_inv,
    )

    # Deve gerar a transferencia mas emitir warning
    assert any('reserv' in w.lower() for w in plano.warnings)


# ============================================================
# 11. company_id parametrizado funciona para FB (regressao Onda 6)
# ============================================================

def test_company_id_parametrizado_funciona_para_fb(service):
    """Mesmo algoritmo aplica para FB (cid=1). Doa de lote A para B sem NF."""
    quants_fb = [_quant(1, 'LOTE_VELHO_FB', 100, lot_id=20, location_id=8, value=64.34)]
    linhas_inv_fb = [_inv('LOTE_NOVO_FB', 100)]

    plano = service.planejar(
        cod_produto='4320162', company_id=1, location_id=8,
        quants_odoo=quants_fb, linhas_inv=linhas_inv_fb,
    )

    assert len(plano.transferencias_internas) == 1
    t = plano.transferencias_internas[0]
    assert t.tipo == 'POS'
    assert t.company_id == 1  # FB
    assert t.location_id == 8  # FB/Estoque


# ============================================================
# 12. Custo medio ponderado aplicado
# ============================================================

def test_custo_medio_ponderado_aplicado_em_transferencia(service):
    """Quants com valores diferentes geram custo medio ponderado."""
    quants_cd = [
        _quant(1, 'A', 100, lot_id=10, value=600),   # custo 6.00
        _quant(2, 'B', 100, lot_id=20, value=800),   # custo 8.00
    ]
    # Media ponderada: (600+800)/(100+100) = 1400/200 = 7.00
    linhas_inv = [_inv('C', 200)]  # vai consumir os 2 lotes

    plano = service.planejar(
        cod_produto='4310177', company_id=4, location_id=32,
        quants_odoo=quants_cd, linhas_inv=linhas_inv,
    )

    for t in plano.transferencias_internas:
        assert t.custo_medio == Decimal('7.00')


# ============================================================
# 13. Caso composto: produto piloto-like (sobra + falta + custo)
# ============================================================

def test_caso_composto_piloto_like(service):
    """Caso parecido com 210030325 LF, mas no CD com FB cobrindo deficit.

    CD tem 50 lote 'OLD' + 30 sem lote = 80 un total.
    Inv quer 100 lote 'NEW'. Deficit = 20.
    FB tem 50 disponivel.
    Esperado:
    - POS: OLD (50) → NEW + SEM (30) → NEW = 80 internamente
    - Residual: FB → CD 20 un para NEW
    """
    quants_cd = [
        _quant(1, 'OLD', 50, lot_id=10, value=200),       # custo 4.00
        _quant(2, '', 30, lot_id=None, value=120),        # custo 4.00
    ]
    linhas_inv = [_inv('NEW', 100)]
    quants_fb = [_quant(99, 'FB_QUALQUER', 50, lot_id=999, location_id=8, value=200)]

    plano = service.planejar(
        cod_produto='4320162', company_id=4, location_id=32,
        quants_odoo=quants_cd, linhas_inv=linhas_inv,
        quants_fb_disponivel=quants_fb,
    )

    # 2 transferencias internas POS
    pos = [t for t in plano.transferencias_internas if t.tipo == 'POS']
    assert len(pos) == 2
    assert sum(t.qty for t in pos) == 80.0
    assert all(t.lote_destino_nome == 'NEW' for t in pos)
    # NEG: nada (todo o estoque OLD/SEM foi para NEW)
    neg = [t for t in plano.transferencias_internas if t.tipo == 'NEG']
    assert neg == []
    # Residual FB→CD: 20 un
    assert len(plano.residual_fb_cd) == 1
    assert plano.residual_fb_cd[0].qty == 20.0
    assert plano.ajustes_positivos_puros == []
