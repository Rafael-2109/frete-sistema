"""Testes de `app/motos_assai/routes/_form_helpers.py` (fast-follow pos-review
Spec 2: dedupe do parser BR<->Decimal antes espalhado em 3 copias)."""
from decimal import Decimal

from app.motos_assai.routes._form_helpers import br_para_decimal_str, decimal_para_br


def test_round_trip_decimal_para_br_e_volta():
    assert br_para_decimal_str(decimal_para_br(Decimal('12.50'))) == '12.50'


def test_br_para_decimal_str_milhar_e_decimal():
    assert br_para_decimal_str('1.234,50') == '1234.50'


def test_br_para_decimal_str_vazio_retorna_none():
    assert br_para_decimal_str('') is None
