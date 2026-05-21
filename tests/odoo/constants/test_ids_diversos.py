"""Tests para app/odoo/constants/ids_diversos.py (sanity dos IDs fixos)."""
from app.odoo.constants import ids_diversos


def test_ids_diversos_valores():
    assert ids_diversos.INCOTERM_CIF == 6
    assert ids_diversos.CARRIER_NACOM == 996
    assert ids_diversos.PAYMENT_PROVIDER_SEM_PAGAMENTO == 38
