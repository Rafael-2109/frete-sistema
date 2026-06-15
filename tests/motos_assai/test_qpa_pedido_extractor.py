import os
from decimal import Decimal
import pytest

from app.motos_assai.services.parsers.qpa_pedido_extractor import QpaPedidoExtractor


FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'pedido_voe_exemplo.pdf')

# Fixture binaria nao versionada (.gitignore exclui *.pdf). Sem o arquivo, os
# testes do extractor sao SKIP em vez de ERROR/FAILED ambiental.
pytestmark = pytest.mark.skipif(
    not os.path.exists(FIXTURE),
    reason='Fixture binaria pedido_voe_exemplo.pdf ausente (nao versionada)',
)


def test_fixture_exists():
    assert os.path.exists(FIXTURE), f"Fixture {FIXTURE} ausente"


def test_extract_retorna_38_lojas_x_3_modelos():
    """Pedido VOE 1 tem 38 páginas (lojas) × 3 modelos = 114 itens."""
    e = QpaPedidoExtractor()
    items = e.extract(FIXTURE)
    assert len(items) == 38 * 3, f"Esperava 114 items, veio {len(items)}"


def test_header_global_consistente():
    e = QpaPedidoExtractor()
    items = e.extract(FIXTURE)
    numeros = {i['numero_pedido'] for i in items}
    assert numeros == {'21439695/L'}, f"Esperava 1 número de pedido, veio {numeros}"
    datas = {i['data_emissao'] for i in items}
    assert datas == {'22/04/2026'}


def test_lojas_unicas_38():
    e = QpaPedidoExtractor()
    items = e.extract(FIXTURE)
    numeros_loja = {i['numero_loja'] for i in items}
    assert len(numeros_loja) == 38
    assert '12' in numeros_loja  # JUNDIAI
    assert '285' in numeros_loja  # FREGUESIA DO O


def test_codigos_qpa_3_modelos():
    e = QpaPedidoExtractor()
    items = e.extract(FIXTURE)
    codigos = {i['codigo_qpa'] for i in items}
    assert codigos == {'1342056', '1342059', '1342063'}


def test_qtd_x11_mini_e_10_por_loja():
    """X11 MINI (1342056): 10 motos por loja, 38 lojas → 380 motos total."""
    e = QpaPedidoExtractor()
    items = e.extract(FIXTURE)
    x11 = [i for i in items if i['codigo_qpa'] == '1342056']
    total_qtd = sum(i['qtd'] for i in x11)
    assert total_qtd == 380, f"Esperava 380 X11 MINI, veio {total_qtd}"


def test_qtd_dot_e_14_por_loja():
    e = QpaPedidoExtractor()
    items = e.extract(FIXTURE)
    dot = [i for i in items if i['codigo_qpa'] == '1342059']
    total_qtd = sum(i['qtd'] for i in dot)
    assert total_qtd == 14 * 38


def test_valor_unitario_dot():
    e = QpaPedidoExtractor()
    items = e.extract(FIXTURE)
    dot = next(i for i in items if i['codigo_qpa'] == '1342059')
    assert dot['valor_unitario'] == Decimal('6900.00') or \
           dot['valor_unitario'] == Decimal('6900.0000')


def test_validate_aceita_item_valido():
    e = QpaPedidoExtractor()
    items = e.extract(FIXTURE)
    assert e.validate(items[0]) is True


def test_validate_rejeita_qtd_zero():
    e = QpaPedidoExtractor()
    item = {'numero_pedido': '1', 'numero_loja': '1', 'codigo_qpa': '1',
            'qtd': 0, 'valor_unitario': Decimal('1')}
    assert e.validate(item) is False


def test_zero_warnings_zero_errors_em_pdf_canonico():
    """No PDF canônico, parser não deve gerar warnings ou errors."""
    e = QpaPedidoExtractor()
    items = e.extract(FIXTURE)
    assert len(items) > 0
    assert e.errors == [], f"Errors inesperados: {e.errors}"
