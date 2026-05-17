"""Testa InventarioPipelineService — orquestrador batch (5 metodos)."""
from decimal import Decimal
from unittest.mock import MagicMock

from app.odoo.services.inventario_pipeline_service import (
    ACAO_PARA_DIRECAO,
    InventarioPipelineService,
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
