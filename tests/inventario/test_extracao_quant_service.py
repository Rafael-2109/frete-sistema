"""Testes da lógica PURA de extração de quants (sem Odoo nem DB)."""
from decimal import Decimal
from app.inventario.services.extracao_quant_service import (
    agregar_quants, norm_lote, classificar_local, is_location_emp_root,
)

PID_MAP = {100: ('4320147', 'AZEITONA'), 200: ('501', 'GORDAL')}


def _q(company_id, pid, lot, loc_id, loc_name, qty, res=0):
    return {
        'company_id': [company_id, 'NACOM'],
        'product_id': [pid, 'PROD'],
        'lot_id': ([10, lot] if lot else False),
        'location_id': [loc_id, loc_name],
        'quantity': qty, 'reserved_quantity': res,
    }


def test_agrega_por_location_cod_lote():
    quants = [
        _q(1, 100, '139/26', 12, 'FB/Estoque', 30),
        _q(1, 100, '139/26', 12, 'FB/Estoque', 20),   # mesmo quant-key -> soma 50
        _q(1, 100, '140/26', 12, 'FB/Estoque', 10),    # lote diferente
    ]
    linhas = agregar_quants(quants, PID_MAP)
    by = {(l['cod_produto'], l['lote']): l for l in linhas}
    assert by[('4320147', '139/26')]['qtd'] == Decimal('50')
    assert by[('4320147', '140/26')]['qtd'] == Decimal('10')


def test_exclui_indisponivel_por_default():
    quants = [
        _q(1, 100, '139/26', 12, 'FB/Estoque', 30),
        _q(1, 100, 'MIGRACAO', 31088, 'FB/Indisponivel', 5),
    ]
    linhas = agregar_quants(quants, PID_MAP, incluir_indisponivel=False)
    assert len(linhas) == 1
    assert linhas[0]['local_tipo'] == 'Estoque'


def test_inclui_indisponivel_quando_flag():
    quants = [_q(1, 100, 'MIGRACAO', 31088, 'FB/Indisponivel', 5)]
    linhas = agregar_quants(quants, PID_MAP, incluir_indisponivel=True)
    assert len(linhas) == 1
    assert linhas[0]['is_migracao'] is True
    assert linhas[0]['local_tipo'] == 'Indisponivel'


def test_reservado_agregado():
    quants = [_q(1, 100, '139/26', 12, 'FB/Estoque', 100, res=14)]
    linhas = agregar_quants(quants, PID_MAP)
    assert linhas[0]['reservado'] == Decimal('14')


def test_ignora_location_virtual():
    quants = [_q(1, 100, '', 99, 'Virtual Locations/Producao', 5)]
    assert agregar_quants(quants, PID_MAP) == []


def test_ignora_produto_sem_default_code():
    quants = [_q(1, 999, '139/26', 12, 'FB/Estoque', 5)]  # 999 não está no PID_MAP
    assert agregar_quants(quants, PID_MAP) == []


def test_filtro_locais():
    quants = [
        _q(1, 100, '139/26', 12, 'FB/Estoque', 30),
        _q(1, 100, '139/26', 13, 'FB/Pré-Produção/Linha Balde', 7),
    ]
    linhas = agregar_quants(quants, PID_MAP, filtro_locais=['FB/Estoque'])
    assert len(linhas) == 1
    assert linhas[0]['location_name'] == 'FB/Estoque'


def test_helpers():
    assert norm_lote('P-15/05') == ''     # proxy vazio
    assert norm_lote(None) == ''
    assert norm_lote('139/26') == '139/26'
    assert classificar_local(31088) == 'Indisponivel'
    assert classificar_local(12) == 'Estoque'
    assert is_location_emp_root('FB/Estoque') is True
    assert is_location_emp_root('Virtual Locations/X') is False
