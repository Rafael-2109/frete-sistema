"""Fase 1 (FU-3): criar_venda_manual aceita lista de itens (N motos)."""
from __future__ import annotations

import uuid
from decimal import Decimal

from app import db as _db
from app.hora.models import HoraLoja, HoraModelo, HoraVenda
from app.hora.services import venda_service
from app.hora.services.moto_service import get_or_create_moto, registrar_evento


def _loja(modelo_nome=None):
    from app.utils.timezone import agora_utc_naive
    cnpj = str(uuid.uuid4().int)[:14].ljust(14, '0')
    loja = HoraLoja(cnpj=cnpj, apelido='MI-' + cnpj[:6], nome='Loja MI ' + cnpj[:6],
                    razao_social='Loja MI LTDA', nome_fantasia='Loja MI', ativa=True,
                    atualizado_em=agora_utc_naive())
    _db.session.add(loja); _db.session.flush()
    return loja


def _modelo():
    m = HoraModelo(nome_modelo='MOD-MI-' + uuid.uuid4().hex[:8].upper(), ativo=True,
                   preco_a_vista=Decimal('1000.00'))
    _db.session.add(m); _db.session.flush()
    return m


def _chassi_estoque(modelo_nome, loja_id, cor='PRETA'):
    chassi = ('MI' + uuid.uuid4().hex).upper()[:25]
    get_or_create_moto(numero_chassi=chassi, modelo_nome=modelo_nome, cor=cor, criado_por='t')
    registrar_evento(numero_chassi=chassi, tipo='RECEBIDA', loja_id=loja_id, operador='t')
    registrar_evento(numero_chassi=chassi, tipo='CONFERIDA', loja_id=loja_id, operador='t')
    _db.session.flush()
    return chassi


def _endereco():
    return dict(cep='01001000', endereco_logradouro='Rua A', endereco_numero='1',
                endereco_complemento='', endereco_bairro='Centro', endereco_cidade='SP',
                endereco_uf='SP')


def test_criar_venda_com_dois_itens(db):
    loja = _loja(); modelo = _modelo()
    c1 = _chassi_estoque(modelo.nome_modelo, loja.id)
    c2 = _chassi_estoque(modelo.nome_modelo, loja.id)
    venda = venda_service.criar_venda_manual(
        cpf_cliente='12345678909', nome_cliente='Cliente Dois',
        itens=[{'numero_chassi': c1, 'valor_final': Decimal('1000.00')},
               {'numero_chassi': c2, 'valor_final': Decimal('900.00')}],
        pagamentos=[{'forma_pagamento_hora': 'DINHEIRO', 'valor': Decimal('1900.00'),
                     'numero_parcelas': 1, 'aut_id': None}],
        loja_id_override=loja.id, criado_por='t', **_endereco(),
    )
    assert {it.numero_chassi for it in venda.itens} == {c1, c2}
    assert venda.valor_total == Decimal('1900.00')


def test_criar_venda_legado_chassi_singular_ainda_funciona(db):
    """Retrocompat: numero_chassi/valor_final (sem itens) cria 1 item."""
    loja = _loja(); modelo = _modelo()
    c1 = _chassi_estoque(modelo.nome_modelo, loja.id)
    venda = venda_service.criar_venda_manual(
        cpf_cliente='12345678909', nome_cliente='Cliente Um',
        numero_chassi=c1, valor_final=Decimal('1000.00'),
        pagamentos=[{'forma_pagamento_hora': 'DINHEIRO', 'valor': Decimal('1000.00'),
                     'numero_parcelas': 1, 'aut_id': None}],
        loja_id_override=loja.id, criado_por='t', **_endereco(),
    )
    assert len(venda.itens) == 1 and venda.itens[0].numero_chassi == c1
