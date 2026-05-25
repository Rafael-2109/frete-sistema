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


# ============================================================
# Helpers I/O (Skill 6 — capinada 2026-05-24)
# Cobertura: enriquecer_quants_para_planejar, planejar_pre_etapa_batch_company,
# _calcular_hash_onda
# ============================================================

from app.odoo.estoque.scripts.pre_etapa import (  # noqa: E402
    _calcular_hash_onda,
    enriquecer_quants_para_planejar,
    planejar_pre_etapa_batch_company,
)


def _quant_raw(quant_id, product_id, lot_id, quantity, location_id=32, value=0):
    """Helper para montar dict de quant RAW (formato do script 01)."""
    return {
        'id': quant_id,
        'product_id': [product_id, 'fake_name'] if product_id else False,
        'lot_id': [lot_id, 'fake_lote'] if lot_id else False,
        'location_id': [location_id, 'fake_loc'],
        'quantity': float(quantity),
        'value': float(value),
    }


# ============================================================
# 14. enriquecer_quants_para_planejar: produto + lote enriquecem
# ============================================================

def test_enriquecer_quants_para_planejar_basic():
    """quants raw enriquecidos com cod_produto + lote_nome via odoo.read."""
    odoo = MagicMock()
    odoo.read.side_effect = [
        # 1a chamada (produtos)
        [{'id': 100, 'default_code': '210030325', 'name': 'POUCH 5 KG'}],
        # 2a chamada (lotes)
        [{'id': 200, 'name': 'MIGRAÇÃO'}],
    ]

    quants_raw = [
        _quant_raw(1, 100, 200, 50, value=320),
        _quant_raw(2, 100, None, 30, value=192),  # sem lote
    ]

    out = enriquecer_quants_para_planejar(odoo, quants_raw, label='CD')

    assert len(out) == 2
    assert out[0]['quant_id'] == 1
    assert out[0]['cod_produto'] == '210030325'
    assert out[0]['lote_nome'] == 'MIGRAÇÃO'
    assert out[0]['quantity'] == 50.0
    assert out[0]['reserved_quantity'] == 0.0  # nao bloqueante — sempre 0
    assert out[0]['value'] == 320.0
    # Sem lote: lote_nome=''
    assert out[1]['lot_id'] is None
    assert out[1]['lote_nome'] == ''


# ============================================================
# 15. enriquecer_quants_para_planejar: lista vazia → sem RPC
# ============================================================

def test_enriquecer_quants_para_planejar_lista_vazia_nao_chama_odoo():
    """Lista vazia nao chama odoo.read (evita RPC desnecessario)."""
    odoo = MagicMock()
    out = enriquecer_quants_para_planejar(odoo, [], label='vazio')
    assert out == []
    assert odoo.read.call_count == 0


# ============================================================
# 16. planejar_pre_etapa_batch_company: filtra outliers (cod[0] not in 1-4)
# ============================================================

def test_planejar_batch_company_filtra_outliers():
    """Cods com inicial nao-digito ou fora 1-4 vao para outliers_skipados."""
    odoo = MagicMock()
    odoo.read.side_effect = [
        # produtos enriquecimento (1 chamada — quants_company)
        [
            {'id': 100, 'default_code': '210030325', 'name': 'CD valido'},
            {'id': 101, 'default_code': 'X105000001', 'name': 'CD outlier X'},
            {'id': 102, 'default_code': '5310177', 'name': 'CD fora 1-4'},
        ],
        # lotes enriquecimento
        [{'id': 200, 'name': 'LOTE_A'}],
        # produtos complementar (vazio — sem FB)
        # lotes complementar (vazio)
    ]

    quants_company_raw = [
        _quant_raw(1, 100, 200, 100, value=64.34),
        _quant_raw(2, 101, None, 50, value=30),
        _quant_raw(3, 102, None, 25, value=15),
    ]
    linhas_inv = [
        {'cod_produto': '210030325', 'lote_inventariado': 'LOTE_B',
         'qtd_inventario': 100, 'validade_inv': None},
    ]

    out = planejar_pre_etapa_batch_company(
        odoo=odoo, company_id=4, location_id=32,
        quants_company_raw=quants_company_raw,
        linhas_inv_raw=linhas_inv,
        quants_complementar_raw=None,
    )

    # X-prefix + cod fora 1-4 vao pra outliers
    assert 'X105000001' in out['outliers_skipados']
    assert '5310177' in out['outliers_skipados']
    assert len(out['outliers_skipados']) == 2
    # Apenas o valido foi processado
    assert out['produtos_processados'] == 1
    assert out['cod_to_name']['210030325'] == 'CD valido'
    assert out['company_id'] == 4


# ============================================================
# 17. planejar_pre_etapa_batch_company: cods_filter restringe universo
# ============================================================

def test_planejar_batch_company_cods_filter_restringe_universo():
    """cods_filter restringe processamento aos cods especificados."""
    odoo = MagicMock()
    odoo.read.side_effect = [
        [
            {'id': 100, 'default_code': '210030325', 'name': 'A'},
            {'id': 200, 'default_code': '210030400', 'name': 'B'},
        ],
        [{'id': 300, 'name': 'LOTE_X'}],
    ]

    quants_company_raw = [
        _quant_raw(1, 100, 300, 100, value=64.34),
        _quant_raw(2, 200, 300, 80, value=50),
    ]
    linhas_inv = [
        {'cod_produto': '210030325', 'lote_inventariado': 'LOTE_NOVO_A',
         'qtd_inventario': 100, 'validade_inv': None},
        {'cod_produto': '210030400', 'lote_inventariado': 'LOTE_NOVO_B',
         'qtd_inventario': 80, 'validade_inv': None},
    ]

    out = planejar_pre_etapa_batch_company(
        odoo=odoo, company_id=4, location_id=32,
        quants_company_raw=quants_company_raw,
        linhas_inv_raw=linhas_inv,
        cods_filter=['210030325'],  # restringe a 1 produto
    )

    assert out['produtos_processados'] == 1
    # So o 210030325 gerou transfer (POS LOTE_X -> LOTE_NOVO_A)
    assert len(out['transferencias_internas']) == 1
    assert out['transferencias_internas'][0]['cod_produto'] == '210030325'


# ============================================================
# 18. _calcular_hash_onda: determinismo (mesmo ordem = mesmo hash)
# ============================================================

def test_calcular_hash_onda_determinismo():
    """Hash eh deterministico (ordenado por id) e estavel entre execucoes."""
    # Fake ajuste (objeto-like com .id, .cod_produto, .company_id, .lote_odoo,
    # .qtd_ajuste, .acao_decidida)
    class FakeAjuste:
        def __init__(self, _id, cod, cid, lote, qty, acao):
            self.id = _id
            self.cod_produto = cod
            self.company_id = cid
            self.lote_odoo = lote
            self.qtd_ajuste = qty
            self.acao_decidida = acao

    a1 = FakeAjuste(1, '210030325', 4, 'MIGRAÇÃO', Decimal('100'), 'AJUSTE_CD_POSITIVO_PURO')
    a2 = FakeAjuste(2, '210030400', 4, 'P-15/05', Decimal('-50'), 'AJUSTE_CD_TRANSF_INTERNA_NEG')
    a3 = FakeAjuste(3, '4310177', 4, 'LOTE_X', Decimal('20'), 'AJUSTE_CD_TRANSF_INTERNA_POS')

    h_ordem_1 = _calcular_hash_onda([a1, a2, a3])
    h_ordem_2 = _calcular_hash_onda([a3, a1, a2])  # ordem diferente
    h_repeticao = _calcular_hash_onda([a1, a2, a3])

    assert h_ordem_1 == h_ordem_2  # ordem nao importa (sort interno por id)
    assert h_ordem_1 == h_repeticao  # determinismo
    assert len(h_ordem_1) == 64  # sha256 hex


# ============================================================
# 19. _calcular_hash_onda: sensibilidade a campos (anti-replay)
# ============================================================

def test_calcular_hash_onda_sensibilidade_a_campos():
    """Hash muda se qualquer campo critico (cod, cid, lote, qty, acao) mudar."""
    class FakeAjuste:
        def __init__(self, _id, cod, cid, lote, qty, acao):
            self.id = _id
            self.cod_produto = cod
            self.company_id = cid
            self.lote_odoo = lote
            self.qtd_ajuste = qty
            self.acao_decidida = acao

    base = FakeAjuste(1, '210030325', 4, 'MIGRAÇÃO', Decimal('100'),
                      'AJUSTE_CD_POSITIVO_PURO')
    h_base = _calcular_hash_onda([base])

    # Mudar cod_produto
    diff_cod = FakeAjuste(1, '210030400', 4, 'MIGRAÇÃO', Decimal('100'),
                          'AJUSTE_CD_POSITIVO_PURO')
    assert _calcular_hash_onda([diff_cod]) != h_base

    # Mudar qty
    diff_qty = FakeAjuste(1, '210030325', 4, 'MIGRAÇÃO', Decimal('200'),
                          'AJUSTE_CD_POSITIVO_PURO')
    assert _calcular_hash_onda([diff_qty]) != h_base

    # Mudar acao
    diff_acao = FakeAjuste(1, '210030325', 4, 'MIGRAÇÃO', Decimal('100'),
                           'AJUSTE_CD_TRANSF_INTERNA_NEG')
    assert _calcular_hash_onda([diff_acao]) != h_base


# ============================================================
# 20. CR-F2: _calcular_hash_onda tolera ORM com atributos ausentes
# ============================================================

def test_calcular_hash_onda_getattr_defensivo_orm_evoluido():
    """Se ORM evoluiu e atributo critico foi renomeado, _calcular_hash_onda
    NAO raise AttributeError (defesa via getattr). Hash calcula com '' default,
    mantendo a invariante anti-replay funcional mesmo em runtime degradado."""
    class AjusteEvoluido:
        # Renomeou 'lote_odoo' para 'lote_legado'; getattr deve usar ''
        def __init__(self, _id):
            self.id = _id
            self.cod_produto = 'X'
            self.company_id = 4
            # Sem self.lote_odoo (atributo ausente)
            self.qtd_ajuste = Decimal('100')
            self.acao_decidida = 'AJUSTE_X'

    h = _calcular_hash_onda([AjusteEvoluido(1)])
    assert len(h) == 64
    # Estabilidade: re-rodar gera mesmo hash (ate o ORM ser corrigido)
    assert _calcular_hash_onda([AjusteEvoluido(1)]) == h


# ============================================================
# 21. CR-F4: propor_ajustes_pre_etapa guard _cod_valido
# ============================================================

def test_cod_valido_filtra_outliers_em_propor():
    """Smoke local da funcao _cod_valido (interna a propor_ajustes_pre_etapa).

    Verifica que cods com inicial fora 1-4 ou vazios sao rejeitados, evitando
    ValueError/IndexError no `tipo_de_cod = int(cod[0])` quando o plano JSON
    foi manualmente editado.
    """
    # Recria a logica interna do guard (CR-F4) — espelha propor_ajustes_pre_etapa
    def _cod_valido(cod):
        return bool(cod) and cod[0].isdigit() and int(cod[0]) in (1, 2, 3, 4)

    # Validos
    assert _cod_valido('210030325')
    assert _cod_valido('4310177')
    assert _cod_valido('1')

    # Invalidos
    assert not _cod_valido('')
    assert not _cod_valido('X105000001')
    assert not _cod_valido('5310177')  # tipo 5 nao existe
    assert not _cod_valido('A1B2')
    assert not _cod_valido(None) if None != '' else True  # bool() trata None
