"""Teste do wrapper publico validar_desconto_tabela (Onda F)."""
import datetime
from decimal import Decimal
from unittest.mock import patch

from app.hora.services import venda_service


def test_delega_a_resolver_e_mapeia_para_dict():
    with patch.object(
        venda_service, "_resolver_preco_tabela",
        return_value=(Decimal("12990.00"), Decimal("990.00"), Decimal("7.62"), 5, False),
    ) as m:
        res = venda_service.validar_desconto_tabela(
            10, Decimal("12000.00"), "A_VISTA", na_data=datetime.date(2026, 6, 2)
        )
    assert res == {
        "modelo_id": 10,
        "preco_referencia": Decimal("12990.00"),
        "desconto_rs": Decimal("990.00"),
        "desconto_pct": Decimal("7.62"),
        "tabela_id": 5,
        "divergencia": False,
    }
    m.assert_called_once_with(10, datetime.date(2026, 6, 2), Decimal("12000.00"), "A_VISTA")


def test_na_data_default_usa_agora_brasil():
    with patch.object(venda_service, "_resolver_preco_tabela",
                      return_value=(Decimal("1"), Decimal("0"), Decimal("0"), None, None)), \
         patch.object(venda_service, "agora_brasil",
                      return_value=datetime.datetime(2026, 6, 2, 10, 0, 0)) as mz:
        venda_service.validar_desconto_tabela(10, Decimal("1"))
    mz.assert_called_once()
