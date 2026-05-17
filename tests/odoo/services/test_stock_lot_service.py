"""Testa StockLotService — wrapper para gestao de stock.lot no Odoo."""
import pytest
from unittest.mock import MagicMock
from app.odoo.services.stock_lot_service import StockLotService


# ============================================================
# buscar_por_nome
# ============================================================

def test_buscar_por_nome_encontra_via_operador_in():
    """Workaround bug do operador '=' em stock.lot.search."""
    odoo = MagicMock()
    odoo.search.return_value = [123]
    svc = StockLotService(odoo=odoo)
    result = svc.buscar_por_nome('LOTE001', product_id=42, company_id=5)
    assert result == 123
    # Confirma uso de operador 'in' (workaround)
    domain = odoo.search.call_args[0][1]
    assert ['name', 'in', ['LOTE001']] in domain


def test_buscar_por_nome_fallback_like():
    """Se 'in' nao encontra, tenta '=like'."""
    odoo = MagicMock()
    odoo.search.side_effect = [[], [456]]  # 1a vazia, 2a acha
    svc = StockLotService(odoo=odoo)
    result = svc.buscar_por_nome('LOTE002', product_id=42, company_id=5)
    assert result == 456
    assert odoo.search.call_count == 2


def test_buscar_por_nome_nao_encontra_retorna_none():
    odoo = MagicMock()
    odoo.search.side_effect = [[], []]
    svc = StockLotService(odoo=odoo)
    assert svc.buscar_por_nome('NAOEXISTE', product_id=42, company_id=5) is None


def test_buscar_por_nome_vazio_retorna_none_sem_chamar_odoo():
    odoo = MagicMock()
    svc = StockLotService(odoo=odoo)
    assert svc.buscar_por_nome('', product_id=42, company_id=5) is None
    odoo.search.assert_not_called()


# ============================================================
# criar
# ============================================================

def test_criar_basico():
    odoo = MagicMock()
    odoo.create.return_value = 789
    svc = StockLotService(odoo=odoo)
    lot_id = svc.criar(nome='LOTE003', product_id=42, company_id=5)
    assert lot_id == 789
    args = odoo.create.call_args[0]
    assert args[0] == 'stock.lot'
    payload = args[1]
    assert payload['name'] == 'LOTE003'
    assert payload['product_id'] == 42
    assert payload['company_id'] == 5


def test_criar_com_expiration_date():
    odoo = MagicMock()
    odoo.create.return_value = 790
    svc = StockLotService(odoo=odoo)
    svc.criar(nome='L004', product_id=42, company_id=5,
              expiration_date='2027-01-15 00:00:00')
    payload = odoo.create.call_args[0][1]
    assert payload['expiration_date'] == '2027-01-15 00:00:00'


def test_criar_fallback_unique_constraint_atualiza_validade():
    """Se unique constraint, busca existente e atualiza expiration."""
    odoo = MagicMock()
    odoo.create.side_effect = Exception('duplicate key value violates unique constraint')
    odoo.search.return_value = [555]
    svc = StockLotService(odoo=odoo)
    lot_id = svc.criar(nome='L005', product_id=42, company_id=5,
                       expiration_date='2027-12-31 00:00:00')
    assert lot_id == 555
    odoo.write.assert_called_with(
        'stock.lot', [555], {'expiration_date': '2027-12-31 00:00:00'}
    )


def test_criar_propaga_outras_excecoes():
    odoo = MagicMock()
    odoo.create.side_effect = Exception('Network error')
    svc = StockLotService(odoo=odoo)
    with pytest.raises(Exception, match='Network'):
        svc.criar(nome='L006', product_id=42, company_id=5)


def test_criar_sem_nome_raises():
    odoo = MagicMock()
    svc = StockLotService(odoo=odoo)
    with pytest.raises(ValueError, match='Nome'):
        svc.criar(nome='', product_id=42, company_id=5)


# ============================================================
# renomear
# ============================================================

def test_renomear_basico():
    odoo = MagicMock()
    odoo.search.return_value = []  # sem move pendente
    svc = StockLotService(odoo=odoo)
    assert svc.renomear(lot_id=123, novo_nome='LOTE_RENOMEADO') is True
    odoo.write.assert_called_with('stock.lot', [123], {'name': 'LOTE_RENOMEADO'})


def test_renomear_bloqueado_se_move_pendente():
    """Guard P9: bloqueia rename se ha stock.move.line nao-done."""
    odoo = MagicMock()
    odoo.search.return_value = [777]
    svc = StockLotService(odoo=odoo)
    with pytest.raises(RuntimeError, match='picking nao-done'):
        svc.renomear(lot_id=123, novo_nome='X')
    odoo.write.assert_not_called()


def test_renomear_sem_novo_nome_raises():
    odoo = MagicMock()
    svc = StockLotService(odoo=odoo)
    with pytest.raises(ValueError, match='novo_nome'):
        svc.renomear(lot_id=123, novo_nome='')


# ============================================================
# inativar / reativar / atualizar_validade
# ============================================================

def test_inativar():
    odoo = MagicMock()
    svc = StockLotService(odoo=odoo)
    assert svc.inativar(lot_id=123) is True
    odoo.write.assert_called_with('stock.lot', [123], {'active': False})


def test_reativar():
    odoo = MagicMock()
    svc = StockLotService(odoo=odoo)
    assert svc.reativar(lot_id=123) is True
    odoo.write.assert_called_with('stock.lot', [123], {'active': True})


def test_atualizar_validade():
    odoo = MagicMock()
    svc = StockLotService(odoo=odoo)
    svc.atualizar_validade(lot_id=123, expiration_date='2028-01-01 00:00:00')
    odoo.write.assert_called_with(
        'stock.lot', [123], {'expiration_date': '2028-01-01 00:00:00'}
    )
