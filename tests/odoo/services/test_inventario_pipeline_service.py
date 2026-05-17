"""Testa InventarioPipelineService — orquestrador batch (5 metodos)."""
from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from app.odoo.services.inventario_pipeline_service import (
    ACAO_PARA_DIRECAO,
    InventarioPipelineService,
    resolver_location_destino,
)


# ============================================================
# f5a_criar_pickings (Task 4.1)
# ============================================================

def test_f5a_criar_pickings_para_lista_de_ajustes(db):
    """f5a recebe lista de ajustes e cria 1 picking por ajuste."""
    from app.odoo.models import AjusteEstoqueInventario

    ajustes = [
        AjusteEstoqueInventario(
            ciclo='TEST_F5A', cod_produto='101001001', tipo_produto=1,
            company_id=5, qtd_inventario=Decimal('5'),
            qtd_odoo=Decimal('10'), qtd_ajuste=Decimal('-5'),
            acao_decidida='PERDA_LF_FB',
            status='APROVADO', criado_por='pytest',
        ),
    ]
    db.session.add_all(ajustes)
    db.session.flush()

    odoo = MagicMock()
    # product.product lookup retorna id=1
    odoo.search_read.return_value = [
        {'id': 1, 'name': 'COGUMELO', 'default_code': '101001001'}
    ]

    picking_svc = MagicMock()
    picking_svc.criar_transferencia.return_value = 99999

    svc = InventarioPipelineService(odoo=odoo, picking_svc=picking_svc)
    result = svc.f5a_criar_pickings(ajustes, executado_por='pytest')

    assert ajustes[0].id in result
    assert result[ajustes[0].id] == 99999
    assert ajustes[0].fase_pipeline == 'F5a_PICKING_CRIADO'
    assert ajustes[0].picking_id_odoo == 99999


def test_f5a_skip_ajuste_com_picking_id_ja_setado(db):
    """Idempotente: ajuste com picking_id_odoo ja preenchido eh skip."""
    from app.odoo.models import AjusteEstoqueInventario

    aj = AjusteEstoqueInventario(
        ciclo='TEST_F5A_SKIP', cod_produto='101001001', tipo_produto=1,
        company_id=5, qtd_inventario=Decimal('5'),
        qtd_odoo=Decimal('10'), qtd_ajuste=Decimal('-5'),
        acao_decidida='PERDA_LF_FB',
        status='APROVADO', criado_por='pytest',
        picking_id_odoo=12345,  # ja existe
    )
    db.session.add(aj)
    db.session.flush()

    odoo = MagicMock()
    picking_svc = MagicMock()
    svc = InventarioPipelineService(odoo=odoo, picking_svc=picking_svc)
    result = svc.f5a_criar_pickings([aj], executado_por='pytest')

    assert result[aj.id] == 12345
    picking_svc.criar_transferencia.assert_not_called()


def test_f5a_acao_decidida_invalida_marca_falha(db):
    """Se acao_decidida nao esta no mapping, marca ajuste como F5a_FALHA."""
    from app.odoo.models import AjusteEstoqueInventario

    aj = AjusteEstoqueInventario(
        ciclo='TEST_F5A_FAIL', cod_produto='101001001', tipo_produto=1,
        company_id=5, qtd_inventario=Decimal('5'),
        qtd_odoo=Decimal('10'), qtd_ajuste=Decimal('-5'),
        acao_decidida='SEM_ACAO',  # nao mapeado em ACAO_PARA_DIRECAO
        status='APROVADO', criado_por='pytest',
    )
    db.session.add(aj)
    db.session.flush()

    odoo = MagicMock()
    picking_svc = MagicMock()
    svc = InventarioPipelineService(odoo=odoo, picking_svc=picking_svc)
    result = svc.f5a_criar_pickings([aj], executado_por='pytest')

    assert aj.id not in result
    assert aj.fase_pipeline == 'F5a_FALHA'
    assert aj.erro_msg and 'SEM_ACAO' in aj.erro_msg


def test_acao_para_direcao_mapping_completo():
    """Validar que todas as acoes do dominio estao mapeadas."""
    esperadas = {
        'TRANSFERIR_CD_FB', 'TRANSFERIR_FB_CD',
        'INDUSTRIALIZACAO_FB_LF', 'PERDA_LF_FB',
        'DEV_FB_LF', 'DEV_LF_FB', 'DEV_CD_LF', 'DEV_LF_CD',
    }
    assert set(ACAO_PARA_DIRECAO.keys()) == esperadas


# ============================================================
# resolver_location_destino — fix BUG-1 (reviewer-A HIGH-1)
# ============================================================

def test_resolver_location_destino_perda_usa_virtual():
    """perda: location_destino = 5 (virtual Parceiros/Clientes)."""
    assert resolver_location_destino('perda', company_destino=1) == 5


def test_resolver_location_destino_transf_filial_usa_interna():
    """transf-filial: location_destino = COMPANY_LOCATIONS[destino]."""
    # FB -> CD: destino=4, COMPANY_LOCATIONS[4]=32
    assert resolver_location_destino('transf-filial', company_destino=4) == 32
    # CD -> FB: destino=1, COMPANY_LOCATIONS[1]=8
    assert resolver_location_destino('transf-filial', company_destino=1) == 8


def test_resolver_location_destino_industrializacao_usa_interna():
    """industrializacao: location_destino = COMPANY_LOCATIONS[5] = 42 (LF)."""
    assert resolver_location_destino('industrializacao', company_destino=5) == 42


def test_resolver_location_destino_dev_industrializacao_usa_interna():
    """dev-industrializacao: location_destino = COMPANY_LOCATIONS[destino]."""
    assert resolver_location_destino('dev-industrializacao', company_destino=5) == 42
    assert resolver_location_destino('dev-industrializacao', company_destino=1) == 8
    assert resolver_location_destino('dev-industrializacao', company_destino=4) == 32


def test_resolver_location_destino_company_invalida_raises():
    with pytest.raises(ValueError, match='company_destino=99'):
        resolver_location_destino('transf-filial', company_destino=99)


def test_f5a_passa_location_destino_correto_para_transferir(db):
    """BUG-1 fix: TRANSFERIR_CD_FB usa COMPANY_LOCATIONS[1]=8, nao 5."""
    from app.odoo.models import AjusteEstoqueInventario

    aj = AjusteEstoqueInventario(
        ciclo='TEST_BUG1', cod_produto='X1', tipo_produto=1, company_id=4,
        qtd_inventario=Decimal('5'), qtd_odoo=Decimal('10'),
        qtd_ajuste=Decimal('-5'), acao_decidida='TRANSFERIR_CD_FB',
        status='APROVADO', criado_por='pytest',
    )
    db.session.add(aj)
    db.session.flush()

    odoo = MagicMock()
    odoo.search_read.return_value = [{'id': 1}]
    picking_svc = MagicMock()
    picking_svc.criar_transferencia.return_value = 99999

    svc = InventarioPipelineService(odoo=odoo, picking_svc=picking_svc)
    svc.f5a_criar_pickings([aj], executado_por='pytest')

    # Confirma que criar_transferencia foi chamado com location_destino_id=8
    # (FB interna), NAO 5 (Parceiros virtual)
    call_kwargs = picking_svc.criar_transferencia.call_args.kwargs
    assert call_kwargs['location_destino_id'] == 8, (
        f"BUG-1 regressao: esperado 8 (COMPANY_LOCATIONS[1] FB), "
        f"got {call_kwargs['location_destino_id']}"
    )
    # Origem CD: COMPANY_LOCATIONS[4]=32
    assert call_kwargs['location_origem_id'] == 32


def test_f5a_passa_location_destino_5_para_perda(db):
    """perda mantem location_destino=5 (Parceiros virtual)."""
    from app.odoo.models import AjusteEstoqueInventario

    aj = AjusteEstoqueInventario(
        ciclo='TEST_PERDA', cod_produto='X1', tipo_produto=1, company_id=5,
        qtd_inventario=Decimal('5'), qtd_odoo=Decimal('10'),
        qtd_ajuste=Decimal('-5'), acao_decidida='PERDA_LF_FB',
        status='APROVADO', criado_por='pytest',
    )
    db.session.add(aj)
    db.session.flush()

    odoo = MagicMock()
    odoo.search_read.return_value = [{'id': 1}]
    picking_svc = MagicMock()
    picking_svc.criar_transferencia.return_value = 88888

    svc = InventarioPipelineService(odoo=odoo, picking_svc=picking_svc)
    svc.f5a_criar_pickings([aj], executado_por='pytest')

    call_kwargs = picking_svc.criar_transferencia.call_args.kwargs
    assert call_kwargs['location_destino_id'] == 5
    # Origem LF: COMPANY_LOCATIONS[5]=42
    assert call_kwargs['location_origem_id'] == 42


# ============================================================
# f5b_validar_pickings (Task 4.2)
# ============================================================

def test_f5b_valida_em_paralelo(db):
    """f5b confirma + reserva + valida cada picking. Atualiza fase."""
    from app.odoo.models import AjusteEstoqueInventario

    ajustes = [
        AjusteEstoqueInventario(
            ciclo='TEST_F5B', cod_produto='101001001', tipo_produto=1,
            company_id=5, qtd_inventario=Decimal('5'),
            qtd_odoo=Decimal('10'), qtd_ajuste=Decimal('-5'),
            acao_decidida='PERDA_LF_FB',
            status='APROVADO', criado_por='pytest',
            picking_id_odoo=1001, fase_pipeline='F5a_PICKING_CRIADO',
        ),
        AjusteEstoqueInventario(
            ciclo='TEST_F5B', cod_produto='101001002', tipo_produto=1,
            company_id=5, qtd_inventario=Decimal('3'),
            qtd_odoo=Decimal('5'), qtd_ajuste=Decimal('-2'),
            acao_decidida='PERDA_LF_FB',
            status='APROVADO', criado_por='pytest',
            picking_id_odoo=1002, fase_pipeline='F5a_PICKING_CRIADO',
        ),
    ]
    db.session.add_all(ajustes)
    db.session.flush()

    odoo = MagicMock()
    picking_svc = MagicMock()
    picking_svc.validar.return_value = True

    svc = InventarioPipelineService(odoo=odoo, picking_svc=picking_svc)
    result = svc.f5b_validar_pickings(ajustes)

    assert result == {1001: True, 1002: True}
    assert picking_svc.confirmar_e_reservar.call_count == 2
    assert picking_svc.validar.call_count == 2
    # Ajustes atualizados
    assert ajustes[0].fase_pipeline == 'F5b_VALIDADO'
    assert ajustes[1].fase_pipeline == 'F5b_VALIDADO'


def test_f5b_falha_marca_F5b_FALHA(db):
    """Se picking_svc.validar lanca, ajuste marcado como F5b_FALHA."""
    from app.odoo.models import AjusteEstoqueInventario

    aj = AjusteEstoqueInventario(
        ciclo='TEST_F5B_FAIL', cod_produto='101001001', tipo_produto=1,
        company_id=5, qtd_inventario=Decimal('5'),
        qtd_odoo=Decimal('10'), qtd_ajuste=Decimal('-5'),
        acao_decidida='PERDA_LF_FB',
        status='APROVADO', criado_por='pytest',
        picking_id_odoo=2001, fase_pipeline='F5a_PICKING_CRIADO',
    )
    db.session.add(aj)
    db.session.flush()

    odoo = MagicMock()
    picking_svc = MagicMock()
    picking_svc.validar.side_effect = Exception('Quality checks pending')

    svc = InventarioPipelineService(odoo=odoo, picking_svc=picking_svc)
    result = svc.f5b_validar_pickings([aj])

    assert result == {2001: False}
    assert aj.fase_pipeline == 'F5b_FALHA'
    assert 'Quality checks' in aj.erro_msg


# ============================================================
# f5c_liberar_faturamento (Task 4.3)
# ============================================================

def test_f5c_libera_em_paralelo(db):
    """f5c dispara liberar_faturamento em todos pickings + atualiza fase."""
    from app.odoo.models import AjusteEstoqueInventario

    ajustes = [
        AjusteEstoqueInventario(
            ciclo='TEST_F5C', cod_produto='X1', tipo_produto=1,
            company_id=5, qtd_inventario=Decimal('1'),
            qtd_odoo=Decimal('2'), qtd_ajuste=Decimal('-1'),
            acao_decidida='PERDA_LF_FB', status='APROVADO',
            criado_por='pytest',
            picking_id_odoo=pid, fase_pipeline='F5b_VALIDADO',
        )
        for pid in (3001, 3002)
    ]
    db.session.add_all(ajustes)
    db.session.flush()

    odoo = MagicMock()
    picking_svc = MagicMock()
    svc = InventarioPipelineService(odoo=odoo, picking_svc=picking_svc)
    svc.f5c_liberar_faturamento(ajustes)

    assert picking_svc.liberar_faturamento.call_count == 2
    assert all(a.fase_pipeline == 'F5c_LIBERADO' for a in ajustes)


def test_f5c_falha_marca_F5c_FALHA(db):
    from app.odoo.models import AjusteEstoqueInventario

    aj = AjusteEstoqueInventario(
        ciclo='TEST_F5C_FAIL', cod_produto='X1', tipo_produto=1,
        company_id=5, qtd_inventario=Decimal('1'),
        qtd_odoo=Decimal('2'), qtd_ajuste=Decimal('-1'),
        acao_decidida='PERDA_LF_FB', status='APROVADO',
        criado_por='pytest',
        picking_id_odoo=3500, fase_pipeline='F5b_VALIDADO',
    )
    db.session.add(aj)
    db.session.flush()

    odoo = MagicMock()
    picking_svc = MagicMock()
    picking_svc.liberar_faturamento.side_effect = Exception(
        'Picking nao validado'
    )
    svc = InventarioPipelineService(odoo=odoo, picking_svc=picking_svc)
    svc.f5c_liberar_faturamento([aj])

    assert aj.fase_pipeline == 'F5c_FALHA'
    assert 'nao validado' in aj.erro_msg


# ============================================================
# f5d_aguardar_invoices (Task 4.4)
# ============================================================

def test_f5d_polling_acha_todos_em_uma_passada(db):
    """f5d aguarda invoices serem criadas pelo robo (mock retorna invoice)."""
    from app.odoo.models import AjusteEstoqueInventario

    ajustes = [
        AjusteEstoqueInventario(
            ciclo='TEST_F5D', cod_produto='X1', tipo_produto=1,
            company_id=5, qtd_inventario=Decimal('1'),
            qtd_odoo=Decimal('2'), qtd_ajuste=Decimal('-1'),
            acao_decidida='PERDA_LF_FB', status='APROVADO',
            criado_por='pytest',
            picking_id_odoo=pid, fase_pipeline='F5c_LIBERADO',
        )
        for pid in (4001, 4002)
    ]
    db.session.add_all(ajustes)
    db.session.flush()

    odoo = MagicMock()
    picking_svc = MagicMock()
    # Cada chamada de aguardar_invoice_do_robo retorna um invoice diferente
    picking_svc.aguardar_invoice_do_robo.side_effect = [999, 1000]

    svc = InventarioPipelineService(odoo=odoo, picking_svc=picking_svc)
    result = svc.f5d_aguardar_invoices(ajustes, timeout=10, poll_interval=1)

    assert result == {4001: 999, 4002: 1000}
    # Ajustes atualizados
    assert ajustes[0].fase_pipeline == 'F5d_INVOICE_GERADA'
    assert ajustes[0].invoice_id_odoo == 999
    assert ajustes[1].fase_pipeline == 'F5d_INVOICE_GERADA'
    assert ajustes[1].invoice_id_odoo == 1000


def test_f5d_timeout_marca_None(db):
    """Se aguardar_invoice retorna None ate timeout, ajuste fica como F5c_LIBERADO."""
    from app.odoo.models import AjusteEstoqueInventario

    aj = AjusteEstoqueInventario(
        ciclo='TEST_F5D_TIMEOUT', cod_produto='X1', tipo_produto=1,
        company_id=5, qtd_inventario=Decimal('1'),
        qtd_odoo=Decimal('2'), qtd_ajuste=Decimal('-1'),
        acao_decidida='PERDA_LF_FB', status='APROVADO',
        criado_por='pytest',
        picking_id_odoo=4500, fase_pipeline='F5c_LIBERADO',
    )
    db.session.add(aj)
    db.session.flush()

    odoo = MagicMock()
    picking_svc = MagicMock()
    picking_svc.aguardar_invoice_do_robo.return_value = None

    svc = InventarioPipelineService(odoo=odoo, picking_svc=picking_svc)
    result = svc.f5d_aguardar_invoices([aj], timeout=2, poll_interval=1)

    assert result == {4500: None}
    # Ajuste mantem F5c_LIBERADO (nao mudou para F5d_INVOICE_GERADA)
    assert aj.fase_pipeline == 'F5c_LIBERADO'
    assert aj.invoice_id_odoo is None


# ============================================================
# f5e_transmitir_sefaz (Task 4.5 — adaptado p/ transmitir_nfe_via_playwright)
# ============================================================

def test_f5e_chama_playwright_para_cada_invoice(db):
    """f5e usa transmitir_nfe_via_playwright (assinatura real)."""
    from app.odoo.models import AjusteEstoqueInventario

    ajustes = [
        AjusteEstoqueInventario(
            ciclo='TEST_F5E', cod_produto='X1', tipo_produto=1,
            company_id=5, qtd_inventario=Decimal('1'),
            qtd_odoo=Decimal('2'), qtd_ajuste=Decimal('-1'),
            acao_decidida='PERDA_LF_FB', status='APROVADO',
            criado_por='pytest',
            picking_id_odoo=pid, invoice_id_odoo=inv,
            fase_pipeline='F5d_INVOICE_GERADA',
        )
        for pid, inv in [(5001, 8001), (5002, 8002)]
    ]
    db.session.add_all(ajustes)
    db.session.flush()

    odoo = MagicMock()
    svc = InventarioPipelineService(odoo=odoo)
    with patch(
        'app.odoo.services.inventario_pipeline_service'
        '.transmitir_nfe_via_playwright'
    ) as mock_tx:
        mock_tx.side_effect = [
            {'sucesso': True, 'chave_nf': '35260112345678000112550010000000018001',
             'situacao_nf': 'autorizado'},
            {'sucesso': True, 'chave_nf': '35260112345678000112550010000000018002',
             'situacao_nf': 'autorizado'},
        ]
        result = svc.f5e_transmitir_sefaz(ajustes)

    assert mock_tx.call_count == 2
    assert all(v and v.startswith('35') for v in result.values())
    # Ajustes atualizados
    for aj in ajustes:
        assert aj.fase_pipeline == 'F5e_SEFAZ_OK'
        assert aj.status == 'EXECUTADO'
        assert aj.chave_nfe and aj.chave_nfe.startswith('35')


def test_f5e_falha_marca_F5e_FALHA(db):
    """Se Playwright retorna sucesso=False, ajuste fica F5e_FALHA."""
    from app.odoo.models import AjusteEstoqueInventario

    aj = AjusteEstoqueInventario(
        ciclo='TEST_F5E_FAIL', cod_produto='X1', tipo_produto=1,
        company_id=5, qtd_inventario=Decimal('1'),
        qtd_odoo=Decimal('2'), qtd_ajuste=Decimal('-1'),
        acao_decidida='PERDA_LF_FB', status='APROVADO',
        criado_por='pytest',
        picking_id_odoo=5500, invoice_id_odoo=8500,
        fase_pipeline='F5d_INVOICE_GERADA',
    )
    db.session.add(aj)
    db.session.flush()

    odoo = MagicMock()
    svc = InventarioPipelineService(odoo=odoo)
    with patch(
        'app.odoo.services.inventario_pipeline_service'
        '.transmitir_nfe_via_playwright'
    ) as mock_tx:
        mock_tx.return_value = {
            'sucesso': False, 'erro': 'login_falhou', 'tentativas': 1
        }
        result = svc.f5e_transmitir_sefaz([aj])

    assert result == {8500: None}
    assert aj.fase_pipeline == 'F5e_FALHA'
    assert 'login_falhou' in aj.erro_msg


def test_f5e_skip_ajuste_sem_invoice_id(db):
    """Ajuste sem invoice_id_odoo eh pulado."""
    from app.odoo.models import AjusteEstoqueInventario

    aj = AjusteEstoqueInventario(
        ciclo='TEST_F5E_SKIP', cod_produto='X1', tipo_produto=1,
        company_id=5, qtd_inventario=Decimal('1'),
        qtd_odoo=Decimal('2'), qtd_ajuste=Decimal('-1'),
        acao_decidida='PERDA_LF_FB', status='APROVADO',
        criado_por='pytest',
        picking_id_odoo=5800, invoice_id_odoo=None,  # sem invoice
        fase_pipeline='F5c_LIBERADO',
    )
    db.session.add(aj)
    db.session.flush()

    odoo = MagicMock()
    svc = InventarioPipelineService(odoo=odoo)
    with patch(
        'app.odoo.services.inventario_pipeline_service'
        '.transmitir_nfe_via_playwright'
    ) as mock_tx:
        result = svc.f5e_transmitir_sefaz([aj])

    assert result == {}
    mock_tx.assert_not_called()
    assert aj.fase_pipeline == 'F5c_LIBERADO'  # nao muda


# ============================================================
# F5e BUG-2 + BUG-3 + MEDIUM fixes (post-review)
# ============================================================

def test_f5e_idempotency_skip_se_ja_SEFAZ_OK(db):
    """BUG-2: ajuste em F5e_SEFAZ_OK NAO chama Playwright novamente."""
    from app.odoo.models import AjusteEstoqueInventario

    aj = AjusteEstoqueInventario(
        ciclo='TEST_F5E_IDEMP', cod_produto='X1', tipo_produto=1,
        company_id=5, qtd_inventario=Decimal('1'),
        qtd_odoo=Decimal('2'), qtd_ajuste=Decimal('-1'),
        acao_decidida='PERDA_LF_FB', status='EXECUTADO',
        criado_por='pytest',
        picking_id_odoo=6001, invoice_id_odoo=9001,
        fase_pipeline='F5e_SEFAZ_OK',
        chave_nfe='35260112345678000112550010000000019001',
    )
    db.session.add(aj)
    db.session.flush()

    odoo = MagicMock()
    svc = InventarioPipelineService(odoo=odoo)
    with patch(
        'app.odoo.services.inventario_pipeline_service'
        '.transmitir_nfe_via_playwright'
    ) as mock_tx:
        result = svc.f5e_transmitir_sefaz([aj])

    mock_tx.assert_not_called()  # CRITICAL: nao abriu Playwright
    assert result == {9001: '35260112345678000112550010000000019001'}
    assert aj.fase_pipeline == 'F5e_SEFAZ_OK'  # mantem


def test_f5e_abort_batch_em_playwright_indisponivel(db):
    """BUG-3: erro de config aborta batch via RuntimeError."""
    from app.odoo.models import AjusteEstoqueInventario

    ajustes = [
        AjusteEstoqueInventario(
            ciclo='TEST_F5E_ABORT', cod_produto='X1', tipo_produto=1,
            company_id=5, qtd_inventario=Decimal('1'),
            qtd_odoo=Decimal('2'), qtd_ajuste=Decimal('-1'),
            acao_decidida='PERDA_LF_FB', status='APROVADO',
            criado_por='pytest',
            picking_id_odoo=pid, invoice_id_odoo=inv,
            fase_pipeline='F5d_INVOICE_GERADA',
        )
        for pid, inv in [(7001, 9101), (7002, 9102), (7003, 9103)]
    ]
    db.session.add_all(ajustes)
    db.session.flush()

    odoo = MagicMock()
    svc = InventarioPipelineService(odoo=odoo)
    with patch(
        'app.odoo.services.inventario_pipeline_service'
        '.transmitir_nfe_via_playwright'
    ) as mock_tx:
        mock_tx.return_value = {
            'sucesso': False, 'erro': 'playwright_indisponivel', 'tentativas': 0
        }
        with pytest.raises(RuntimeError, match='configuracao invalida'):
            svc.f5e_transmitir_sefaz(ajustes)

    # Apenas o 1o ajuste foi marcado como F5e_FALHA (abort batch)
    assert mock_tx.call_count == 1
    assert ajustes[0].fase_pipeline == 'F5e_FALHA'
    assert 'playwright_indisponivel' in ajustes[0].erro_msg
    # Os outros 2 nao foram processados
    assert ajustes[1].fase_pipeline == 'F5d_INVOICE_GERADA'
    assert ajustes[2].fase_pipeline == 'F5d_INVOICE_GERADA'


def test_f5e_falha_persiste_cstat_xmotivo(db):
    """MED C-2: erro_msg inclui cstat/xmotivo do ultimo_estado."""
    from app.odoo.models import AjusteEstoqueInventario

    aj = AjusteEstoqueInventario(
        ciclo='TEST_F5E_CSTAT', cod_produto='X1', tipo_produto=1,
        company_id=5, qtd_inventario=Decimal('1'),
        qtd_odoo=Decimal('2'), qtd_ajuste=Decimal('-1'),
        acao_decidida='PERDA_LF_FB', status='APROVADO',
        criado_por='pytest',
        picking_id_odoo=8001, invoice_id_odoo=9201,
        fase_pipeline='F5d_INVOICE_GERADA',
    )
    db.session.add(aj)
    db.session.flush()

    odoo = MagicMock()
    svc = InventarioPipelineService(odoo=odoo)
    with patch(
        'app.odoo.services.inventario_pipeline_service'
        '.transmitir_nfe_via_playwright'
    ) as mock_tx:
        mock_tx.return_value = {
            'sucesso': False,
            'erro': 'nao_autorizada_apos_15_tentativas',
            'tentativas': 15,
            'ultimo_estado': {
                'situacao_nf': 'rejeitado',
                'cstat': '225',
                'xmotivo': 'Falha no Schema XML',
            },
        }
        svc.f5e_transmitir_sefaz([aj])

    assert aj.fase_pipeline == 'F5e_FALHA'
    assert 'cstat=225' in aj.erro_msg
    assert 'Falha no Schema XML' in aj.erro_msg


def test_f5e_sucesso_excecao_autorizado_registra_audit(db):
    """MED C-1: situacao_nf=excecao_autorizado vai para erro_msg (audit)."""
    from app.odoo.models import AjusteEstoqueInventario

    aj = AjusteEstoqueInventario(
        ciclo='TEST_F5E_EXC', cod_produto='X1', tipo_produto=1,
        company_id=5, qtd_inventario=Decimal('1'),
        qtd_odoo=Decimal('2'), qtd_ajuste=Decimal('-1'),
        acao_decidida='PERDA_LF_FB', status='APROVADO',
        criado_por='pytest',
        picking_id_odoo=8501, invoice_id_odoo=9301,
        fase_pipeline='F5d_INVOICE_GERADA',
    )
    db.session.add(aj)
    db.session.flush()

    odoo = MagicMock()
    svc = InventarioPipelineService(odoo=odoo)
    with patch(
        'app.odoo.services.inventario_pipeline_service'
        '.transmitir_nfe_via_playwright'
    ) as mock_tx:
        mock_tx.return_value = {
            'sucesso': True,
            'chave_nf': '35260112345678000112550010000000019301',
            'situacao_nf': 'excecao_autorizado',
            'tentativa': 3,
            'inv_name': 'INV-X',
        }
        svc.f5e_transmitir_sefaz([aj])

    assert aj.fase_pipeline == 'F5e_SEFAZ_OK'
    assert aj.status == 'EXECUTADO'
    assert aj.chave_nfe == '35260112345678000112550010000000019301'
    # MED C-1: audit registra excecao
    assert 'excecao_autorizado' in aj.erro_msg
    assert 'tentativa=3' in aj.erro_msg


def test_f5b_warning_em_ajuste_sem_picking_id(db, caplog):
    """B-MED-2: skip silencioso virou WARNING."""
    import logging
    from app.odoo.models import AjusteEstoqueInventario

    aj = AjusteEstoqueInventario(
        ciclo='TEST_F5B_NOPID', cod_produto='X1', tipo_produto=1,
        company_id=5, qtd_inventario=Decimal('1'),
        qtd_odoo=Decimal('2'), qtd_ajuste=Decimal('-1'),
        acao_decidida='PERDA_LF_FB', status='APROVADO',
        criado_por='pytest',
        picking_id_odoo=None,  # sem picking_id
        fase_pipeline='F5a_FALHA',
    )
    db.session.add(aj)
    db.session.flush()

    odoo = MagicMock()
    picking_svc = MagicMock()
    svc = InventarioPipelineService(odoo=odoo, picking_svc=picking_svc)
    with caplog.at_level(logging.WARNING):
        result = svc.f5b_validar_pickings([aj])

    assert result == {}
    picking_svc.confirmar_e_reservar.assert_not_called()
    assert any(
        'F5b skip ajuste' in r.message and 'sem picking_id_odoo' in r.message
        for r in caplog.records
    )
