"""Fase 3 (Task 8): helpers de parsing do form de edicao (Salvar Pedido)."""
from decimal import Decimal
from werkzeug.datastructures import MultiDict
from app.hora.routes.vendas import _parse_pagamentos_form, _parse_itens_edicao_form


def _form(pairs):
    md = MultiDict()
    for k, v in pairs: md.add(k, v)
    return md


def test_parse_itens_edicao_mix_existente_e_novo():
    form = _form([('item_id', '5'), ('item_id', ''),
                  ('item_chassi', 'AAA111'), ('item_chassi', 'BBB222'),
                  ('item_valor', '900,00'), ('item_valor', '800,00')])
    itens = _parse_itens_edicao_form(form)
    assert itens == [
        {'item_id': 5, 'numero_chassi': 'AAA111', 'valor_final': Decimal('900.00')},
        {'item_id': None, 'numero_chassi': 'BBB222', 'valor_final': Decimal('800.00')},
    ]


def test_parse_itens_ignora_chassi_vazio():
    form = _form([('item_id', ''), ('item_chassi', ''), ('item_valor', '10')])
    assert _parse_itens_edicao_form(form) == []


def test_parse_pagamentos_form_basico():
    form = _form([('pagamento_forma', 'DINHEIRO'), ('pagamento_valor', '1.700,00'),
                  ('pagamento_parcelas', '1'), ('pagamento_aut_id', '')])
    pags = _parse_pagamentos_form(form)
    assert pags == [{'forma_pagamento_hora': 'DINHEIRO', 'valor': Decimal('1700.00'),
                     'numero_parcelas': 1, 'aut_id': None}]
