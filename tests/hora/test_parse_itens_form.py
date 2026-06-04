"""Fase 1 (FU-3): helper que monta a lista de itens do form de criacao."""
from __future__ import annotations
from decimal import Decimal
from werkzeug.datastructures import MultiDict

from app.hora.routes.tagplus_routes import _parse_itens_form


def _form(pairs):
    md = MultiDict()
    for k, v in pairs:
        md.add(k, v)
    return md


def test_dois_chassis_com_valor_br():
    form = _form([('chassi', 'AAA111'), ('chassi', 'BBB222'),
                  ('valor', '1.000,00'), ('valor', '900,50')])
    itens = _parse_itens_form(form)
    assert itens == [
        {'numero_chassi': 'AAA111', 'valor_final': Decimal('1000.00')},
        {'numero_chassi': 'BBB222', 'valor_final': Decimal('900.50')},
    ]


def test_ignora_chassi_vazio():
    form = _form([('chassi', 'AAA111'), ('chassi', ''), ('valor', '1000'), ('valor', '50')])
    itens = _parse_itens_form(form)
    assert [i['numero_chassi'] for i in itens] == ['AAA111']


def test_valor_invalido_vira_none():
    form = _form([('chassi', 'AAA111'), ('valor', 'abc')])
    itens = _parse_itens_form(form)
    assert itens == [{'numero_chassi': 'AAA111', 'valor_final': None}]
