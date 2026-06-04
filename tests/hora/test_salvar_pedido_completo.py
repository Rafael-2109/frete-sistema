"""Fase 3 (FU-5): salvar_pedido_completo reconcilia header+itens+pagamentos numa transacao."""
from __future__ import annotations
import uuid
from decimal import Decimal

from app import db as _db
from app.hora.models import HoraLoja, HoraModelo, HoraVenda
from app.hora.services import venda_service
from app.hora.services.moto_service import get_or_create_moto, registrar_evento


def _setup_pedido_2_itens():
    from app.utils.timezone import agora_utc_naive
    cnpj = str(uuid.uuid4().int)[:14].ljust(14, '0')
    loja = HoraLoja(cnpj=cnpj, apelido='SP-' + cnpj[:6], nome='Loja SP', razao_social='SP LTDA',
                    nome_fantasia='SP', ativa=True, atualizado_em=agora_utc_naive())
    _db.session.add(loja); _db.session.flush()
    m = HoraModelo(nome_modelo='MOD-SP-' + uuid.uuid4().hex[:8].upper(), ativo=True,
                   preco_a_vista=Decimal('1000'))
    _db.session.add(m); _db.session.flush()
    def chassi():
        ch = ('SP' + uuid.uuid4().hex).upper()[:25]
        get_or_create_moto(numero_chassi=ch, modelo_nome=m.nome_modelo, cor='PRETA', criado_por='t')
        registrar_evento(numero_chassi=ch, tipo='RECEBIDA', loja_id=loja.id, operador='t')
        registrar_evento(numero_chassi=ch, tipo='CONFERIDA', loja_id=loja.id, operador='t')
        _db.session.flush(); return ch
    c1, c2, c3 = chassi(), chassi(), chassi()
    venda = venda_service.criar_venda_manual(
        cpf_cliente='12345678909', nome_cliente='C', cep='01001000',
        endereco_logradouro='R', endereco_numero='1', endereco_complemento='',
        endereco_bairro='B', endereco_cidade='SP', endereco_uf='SP',
        itens=[{'numero_chassi': c1, 'valor_final': Decimal('1000')},
               {'numero_chassi': c2, 'valor_final': Decimal('1000')}],
        pagamentos=[{'forma_pagamento_hora': 'DINHEIRO', 'valor': Decimal('2000'),
                     'numero_parcelas': 1, 'aut_id': None}],
        loja_id_override=loja.id, criado_por='t')
    return venda, c1, c2, c3


def test_reconcilia_remove_adiciona_atualiza(db):
    venda, c1, c2, c3 = _setup_pedido_2_itens()
    assert venda.status == 'COTACAO'
    item_c1 = next(it for it in venda.itens if it.numero_chassi == c1)
    venda_service.salvar_pedido_completo(
        venda_id=venda.id, header={},
        itens=[{'item_id': item_c1.id, 'numero_chassi': c1, 'valor_final': Decimal('900')},
               {'item_id': None, 'numero_chassi': c3, 'valor_final': Decimal('800')}],
        pagamentos=[{'forma_pagamento_hora': 'DINHEIRO', 'valor': Decimal('1700'),
                     'numero_parcelas': 1, 'aut_id': None}],
        usuario='t')
    _db.session.refresh(venda)
    assert {it.numero_chassi for it in venda.itens} == {c1, c3}
    assert venda.valor_total == Decimal('1700')
    assert venda.status == 'COTACAO'  # soma pagamentos == total


def test_soma_pagamentos_difere_marca_incompleto(db):
    venda, c1, c2, c3 = _setup_pedido_2_itens()
    item_c1 = next(it for it in venda.itens if it.numero_chassi == c1)
    item_c2 = next(it for it in venda.itens if it.numero_chassi == c2)
    venda_service.salvar_pedido_completo(
        venda_id=venda.id, header={},
        itens=[{'item_id': item_c1.id, 'numero_chassi': c1, 'valor_final': Decimal('1000')},
               {'item_id': item_c2.id, 'numero_chassi': c2, 'valor_final': Decimal('1000')}],
        pagamentos=[{'forma_pagamento_hora': 'DINHEIRO', 'valor': Decimal('500'),
                     'numero_parcelas': 1, 'aut_id': None}],  # soma != 2000
        usuario='t')
    _db.session.refresh(venda)
    assert venda.status == 'INCOMPLETO'


def test_nao_remove_ultimo_item(db):
    venda, c1, c2, c3 = _setup_pedido_2_itens()
    # submeter lista vazia de itens -> nao pode zerar
    import pytest
    with pytest.raises(ValueError):
        venda_service.salvar_pedido_completo(
            venda_id=venda.id, header={}, itens=[],
            pagamentos=[{'forma_pagamento_hora': 'DINHEIRO', 'valor': Decimal('0'),
                         'numero_parcelas': 1, 'aut_id': None}],
            usuario='t')


def test_item_sem_valor_levanta_value_error(db):
    """valor_final=None -> ValueError gracioso (NAO InvalidOperation/HTTP 500)."""
    import pytest
    venda, c1, c2, c3 = _setup_pedido_2_itens()
    item_c1 = next(it for it in venda.itens if it.numero_chassi == c1)
    item_c2 = next(it for it in venda.itens if it.numero_chassi == c2)
    with pytest.raises(ValueError):
        venda_service.salvar_pedido_completo(
            venda_id=venda.id, header={},
            itens=[{'item_id': item_c1.id, 'numero_chassi': c1, 'valor_final': None},
                   {'item_id': item_c2.id, 'numero_chassi': c2, 'valor_final': Decimal('1000')}],
            pagamentos=[{'forma_pagamento_hora': 'DINHEIRO', 'valor': Decimal('1000'),
                         'numero_parcelas': 1, 'aut_id': None}],
            usuario='t')
