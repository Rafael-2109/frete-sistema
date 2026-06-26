"""Correcoes do Pedido de Venda HORA (2026-06-25).

F1 — editar itens (trocar/add/remover moto) em INCOMPLETO (antes so COTACAO).
F2 — preco de tabela resolvido pela forma representativa dos pagamentos
     SUBMETIDOS (qualquer A_PRAZO -> preco a prazo), evitando "desconto-fantasma".
F4 — AUT obrigatorio para AVANCAR (confirmar): forma exige_aut_id sem aut_id
     mantem o pedido INCOMPLETO e confirmar_venda bloqueia (hard no avanco;
     salvar rascunho continua permitido).
"""
from __future__ import annotations

import uuid
from decimal import Decimal

import pytest

from app import db as _db
from app.hora.models import HoraLoja, HoraModelo
from app.hora.models.tagplus import HoraTagPlusFormaPagamentoMap
from app.hora.services import venda_service
from app.hora.services.moto_service import get_or_create_moto, registrar_evento
from app.utils.timezone import agora_utc_naive


# --------------------------------------------------------------------------
# Fixtures inline (mesmo padrao dos demais testes hora: CNPJ/nome unicos
# porque os services commitam e escapam o savepoint do fixture `db`).
# --------------------------------------------------------------------------

_FORMA_SEQ = [0]


def _forma(nome: str, tipo: str | None, exige_aut: bool = False):
    """Cria forma de pagamento HORA classificada (tagplus_forma_id unico)."""
    _FORMA_SEQ[0] += 1
    m = HoraTagPlusFormaPagamentoMap(
        forma_pagamento_hora=nome,
        tagplus_forma_id=900000 + _FORMA_SEQ[0],
        tipo_pagamento=tipo,
        exige_aut_id=exige_aut,
    )
    _db.session.add(m)
    _db.session.flush()
    return m


def _loja():
    cnpj = str(uuid.uuid4().int)[:14].ljust(14, '0')
    loja = HoraLoja(cnpj=cnpj, apelido='SP-' + cnpj[:6], nome='Loja SP',
                    razao_social='SP LTDA', nome_fantasia='SP', ativa=True,
                    atualizado_em=agora_utc_naive())
    _db.session.add(loja)
    _db.session.flush()
    return loja


def _modelo(preco_a_vista=Decimal('1000'), preco_a_prazo=Decimal('1200')):
    m = HoraModelo(nome_modelo='MOD-' + uuid.uuid4().hex[:8].upper(), ativo=True,
                   preco_a_vista=preco_a_vista, preco_a_prazo=preco_a_prazo)
    _db.session.add(m)
    _db.session.flush()
    return m


def _chassi_em_estoque(modelo, loja):
    ch = ('CH' + uuid.uuid4().hex).upper()[:25]
    get_or_create_moto(numero_chassi=ch, modelo_nome=modelo.nome_modelo,
                       cor='PRETA', criado_por='t')
    registrar_evento(numero_chassi=ch, tipo='RECEBIDA', loja_id=loja.id, operador='t')
    registrar_evento(numero_chassi=ch, tipo='CONFERIDA', loja_id=loja.id, operador='t')
    _db.session.flush()
    return ch


# --------------------------------------------------------------------------
# F1 — edicao de itens em INCOMPLETO
# --------------------------------------------------------------------------

def test_f1_troca_moto_em_incompleto_persiste(db):
    """Pedido INCOMPLETO permite trocar a moto (remover+readicionar) e PERSISTE.

    Antes da correcao, salvar_pedido_completo ignorava silenciosamente os itens
    em INCOMPLETO (so aplicava em COTACAO).
    """
    loja, modelo = _loja(), _modelo()
    _forma('DINHEIRO_T', 'A_VISTA', exige_aut=False)
    c1 = _chassi_em_estoque(modelo, loja)
    c2 = _chassi_em_estoque(modelo, loja)
    # Cria pedido INCOMPLETO: soma das formas (500) != total (1000).
    venda = venda_service.criar_venda_manual(
        cpf_cliente='12345678909', nome_cliente='C', cep='01001000',
        endereco_logradouro='R', endereco_numero='1', endereco_complemento='',
        endereco_bairro='B', endereco_cidade='SP', endereco_uf='SP',
        itens=[{'numero_chassi': c1, 'valor_final': Decimal('1000')}],
        pagamentos=[{'forma_pagamento_hora': 'DINHEIRO_T', 'valor': Decimal('500'),
                     'numero_parcelas': 1, 'aut_id': None}],
        loja_id_override=loja.id, criado_por='t')
    assert venda.status == 'INCOMPLETO'

    # Em INCOMPLETO: remove c1, adiciona c2 (troca de moto).
    venda_service.salvar_pedido_completo(
        venda_id=venda.id, header={},
        itens=[{'item_id': None, 'numero_chassi': c2, 'valor_final': Decimal('1000')}],
        pagamentos=[{'forma_pagamento_hora': 'DINHEIRO_T', 'valor': Decimal('500'),
                     'numero_parcelas': 1, 'aut_id': None}],
        usuario='t')
    _db.session.refresh(venda)
    assert {it.numero_chassi for it in venda.itens} == {c2}  # troca PERSISTIU
    assert venda.status == 'INCOMPLETO'  # soma ainda != total


def test_f1_adiciona_moto_em_incompleto(db):
    """Adicionar 2a moto em INCOMPLETO persiste e recalcula valor_total."""
    loja, modelo = _loja(), _modelo()
    _forma('DINHEIRO_T2', 'A_VISTA')
    c1 = _chassi_em_estoque(modelo, loja)
    c2 = _chassi_em_estoque(modelo, loja)
    venda = venda_service.criar_venda_manual(
        cpf_cliente='12345678909', nome_cliente='C', cep='01001000',
        endereco_logradouro='R', endereco_numero='1', endereco_complemento='',
        endereco_bairro='B', endereco_cidade='SP', endereco_uf='SP',
        itens=[{'numero_chassi': c1, 'valor_final': Decimal('1000')}],
        pagamentos=[{'forma_pagamento_hora': 'DINHEIRO_T2', 'valor': Decimal('500'),
                     'numero_parcelas': 1, 'aut_id': None}],
        loja_id_override=loja.id, criado_por='t')
    assert venda.status == 'INCOMPLETO'
    item_c1 = next(it for it in venda.itens if it.numero_chassi == c1)
    venda_service.salvar_pedido_completo(
        venda_id=venda.id, header={},
        itens=[{'item_id': item_c1.id, 'numero_chassi': c1, 'valor_final': Decimal('1000')},
               {'item_id': None, 'numero_chassi': c2, 'valor_final': Decimal('1000')}],
        pagamentos=[{'forma_pagamento_hora': 'DINHEIRO_T2', 'valor': Decimal('2000'),
                     'numero_parcelas': 1, 'aut_id': None}],
        usuario='t')
    _db.session.refresh(venda)
    assert {it.numero_chassi for it in venda.itens} == {c1, c2}
    assert venda.valor_total == Decimal('2000')
    assert venda.status == 'COTACAO'  # agora soma (2000) == total (2000)


# --------------------------------------------------------------------------
# F2 — forma representativa A_PRAZO resolve preco a prazo
# --------------------------------------------------------------------------

def test_f2_criar_a_prazo_grava_preco_a_prazo(db):
    """criar_venda_manual com forma A_PRAZO precifica pelo preco_a_prazo (1200),
    nao pelo a vista (1000) — desconto coerente (1200-1100=100)."""
    loja = _loja()
    modelo = _modelo(preco_a_vista=Decimal('1000'), preco_a_prazo=Decimal('1200'))
    _forma('CARTPZ_T', 'A_PRAZO', exige_aut=False)
    c1 = _chassi_em_estoque(modelo, loja)
    venda = venda_service.criar_venda_manual(
        cpf_cliente='12345678909', nome_cliente='C', cep='01001000',
        endereco_logradouro='R', endereco_numero='1', endereco_complemento='',
        endereco_bairro='B', endereco_cidade='SP', endereco_uf='SP',
        itens=[{'numero_chassi': c1, 'valor_final': Decimal('1100')}],
        pagamentos=[{'forma_pagamento_hora': 'CARTPZ_T', 'valor': Decimal('1100'),
                     'numero_parcelas': 2, 'aut_id': '123'}],
        loja_id_override=loja.id, criado_por='t')
    item = list(venda.itens)[0]
    assert item.preco_tabela_referencia == Decimal('1200')  # a prazo, nao 1000
    assert item.desconto_aplicado == Decimal('100')


def test_f2_salvar_usa_forma_submetida_nao_cache(db):
    """salvar_pedido_completo precifica a nova moto pela forma SUBMETIDA (A_PRAZO),
    nao pelo cache venda.forma_pagamento antigo — corrige o gotcha de ordem."""
    loja = _loja()
    modelo = _modelo(preco_a_vista=Decimal('1000'), preco_a_prazo=Decimal('1200'))
    _forma('CARTPZ_T2', 'A_PRAZO', exige_aut=False)
    c1 = _chassi_em_estoque(modelo, loja)
    c2 = _chassi_em_estoque(modelo, loja)
    # Pedido nasce com 1 item, forma A_PRAZO (valor cheio a prazo).
    venda = venda_service.criar_venda_manual(
        cpf_cliente='12345678909', nome_cliente='C', cep='01001000',
        endereco_logradouro='R', endereco_numero='1', endereco_complemento='',
        endereco_bairro='B', endereco_cidade='SP', endereco_uf='SP',
        itens=[{'numero_chassi': c1, 'valor_final': Decimal('1200')}],
        pagamentos=[{'forma_pagamento_hora': 'CARTPZ_T2', 'valor': Decimal('1200'),
                     'numero_parcelas': 1, 'aut_id': '1'}],
        loja_id_override=loja.id, criado_por='t')
    assert venda.status == 'COTACAO'
    item_c1 = next(it for it in venda.itens if it.numero_chassi == c1)
    # Adiciona c2 a prazo, valor cheio 1200.
    venda_service.salvar_pedido_completo(
        venda_id=venda.id, header={},
        itens=[{'item_id': item_c1.id, 'numero_chassi': c1, 'valor_final': Decimal('1200')},
               {'item_id': None, 'numero_chassi': c2, 'valor_final': Decimal('1200')}],
        pagamentos=[{'forma_pagamento_hora': 'CARTPZ_T2', 'valor': Decimal('2400'),
                     'numero_parcelas': 1, 'aut_id': '1'}],
        usuario='t')
    _db.session.refresh(venda)
    novo = next(it for it in venda.itens if it.numero_chassi == c2)
    assert novo.preco_tabela_referencia == Decimal('1200')  # a prazo, nao 1000
    assert novo.desconto_aplicado == Decimal('0')


def test_f2_forma_a_prazo_com_valor_em_branco_precifica_a_prazo(db):
    """Residuo de F2 (review 2026-06-25): forma A_PRAZO selecionada com o VALOR do
    pagamento em branco (0) ainda precifica a prazo — antes caia no fallback
    A_VISTA porque _normalizar_pagamentos descarta linha de valor<=0."""
    loja = _loja()
    modelo = _modelo(preco_a_vista=Decimal('1000'), preco_a_prazo=Decimal('1200'))
    _forma('CARTPZ_T3', 'A_PRAZO', exige_aut=False)
    c1 = _chassi_em_estoque(modelo, loja)
    c2 = _chassi_em_estoque(modelo, loja)
    venda = venda_service.criar_venda_manual(
        cpf_cliente='12345678909', nome_cliente='C',
        cep='01001000', endereco_logradouro='R', endereco_numero='1',
        endereco_complemento='', endereco_bairro='B', endereco_cidade='SP', endereco_uf='SP',
        itens=[{'numero_chassi': c1, 'valor_final': Decimal('1200')}],
        pagamentos=[{'forma_pagamento_hora': 'CARTPZ_T3', 'valor': Decimal('1200'),
                     'numero_parcelas': 1, 'aut_id': '1'}],
        loja_id_override=loja.id, criado_por='t')
    item_c1 = next(it for it in venda.itens if it.numero_chassi == c1)
    # Adiciona c2; a forma A_PRAZO e submetida com valor 0 (operador nao digitou).
    venda_service.salvar_pedido_completo(
        venda_id=venda.id, header={},
        itens=[{'item_id': item_c1.id, 'numero_chassi': c1, 'valor_final': Decimal('1200')},
               {'item_id': None, 'numero_chassi': c2, 'valor_final': Decimal('1200')}],
        pagamentos=[{'forma_pagamento_hora': 'CARTPZ_T3', 'valor': Decimal('0'),
                     'numero_parcelas': 1, 'aut_id': '1'}],
        usuario='t')
    _db.session.refresh(venda)
    novo = next(it for it in venda.itens if it.numero_chassi == c2)
    assert novo.preco_tabela_referencia == Decimal('1200')  # a prazo (nao caiu no fallback)


# --------------------------------------------------------------------------
# F4 — AUT obrigatorio para confirmar (hard no avanco; soft no save)
# --------------------------------------------------------------------------

def test_f4_sem_aut_fica_incompleto_e_nao_confirma(db):
    """Forma exige_aut_id sem aut_id => INCOMPLETO; confirmar_venda bloqueia."""
    loja = _loja()
    modelo = _modelo()
    _forma('CARTAUT_T', 'A_PRAZO', exige_aut=True)
    c1 = _chassi_em_estoque(modelo, loja)
    venda = venda_service.criar_venda_manual(
        cpf_cliente='12345678909', nome_cliente='C', cep='01001000',
        endereco_logradouro='R', endereco_numero='1', endereco_complemento='',
        endereco_bairro='B', endereco_cidade='SP', endereco_uf='SP',
        itens=[{'numero_chassi': c1, 'valor_final': Decimal('1200')}],
        pagamentos=[{'forma_pagamento_hora': 'CARTAUT_T', 'valor': Decimal('1200'),
                     'numero_parcelas': 1, 'aut_id': None}],  # SEM aut
        loja_id_override=loja.id, criado_por='t')
    assert venda.status == 'INCOMPLETO'  # soma bate, mas falta AUT
    with pytest.raises(venda_service.TransicaoInvalidaError):
        venda_service.confirmar_venda(venda.id, usuario='t')


def test_f4_com_aut_confirma(db):
    """Mesma forma com aut_id preenchido + soma OK => COTACAO => confirma."""
    loja = _loja()
    modelo = _modelo()
    _forma('CARTAUT_T2', 'A_PRAZO', exige_aut=True)
    c1 = _chassi_em_estoque(modelo, loja)
    venda = venda_service.criar_venda_manual(
        cpf_cliente='12345678909', nome_cliente='C', cep='01001000',
        endereco_logradouro='R', endereco_numero='1', endereco_complemento='',
        endereco_bairro='B', endereco_cidade='SP', endereco_uf='SP',
        itens=[{'numero_chassi': c1, 'valor_final': Decimal('1200')}],
        pagamentos=[{'forma_pagamento_hora': 'CARTAUT_T2', 'valor': Decimal('1200'),
                     'numero_parcelas': 1, 'aut_id': 'AUT-9988'}],
        loja_id_override=loja.id, criado_por='t')
    assert venda.status == 'COTACAO'
    venda_service.confirmar_venda(venda.id, usuario='t')
    _db.session.refresh(venda)
    assert venda.status == 'CONFIRMADO'


# --------------------------------------------------------------------------
# Feature: Inscricao Estadual (registro/exibicao — migration hora_52)
# --------------------------------------------------------------------------

def test_ie_grava_na_criacao(db):
    """criar_venda_manual persiste inscricao_estadual."""
    loja, modelo = _loja(), _modelo()
    _forma('DINHEIRO_IE', 'A_VISTA')
    c1 = _chassi_em_estoque(modelo, loja)
    venda = venda_service.criar_venda_manual(
        cpf_cliente='12345678909', nome_cliente='Empresa X',
        inscricao_estadual='110.042.490.114',
        cep='01001000', endereco_logradouro='R', endereco_numero='1',
        endereco_complemento='', endereco_bairro='B', endereco_cidade='SP', endereco_uf='SP',
        itens=[{'numero_chassi': c1, 'valor_final': Decimal('1000')}],
        pagamentos=[{'forma_pagamento_hora': 'DINHEIRO_IE', 'valor': Decimal('1000'),
                     'numero_parcelas': 1, 'aut_id': None}],
        loja_id_override=loja.id, criado_por='t')
    _db.session.refresh(venda)
    assert venda.inscricao_estadual == '110.042.490.114'


def test_ie_editavel_em_incompleto(db):
    """salvar_pedido_completo atualiza inscricao_estadual em INCOMPLETO."""
    loja, modelo = _loja(), _modelo()
    _forma('DINHEIRO_IE2', 'A_VISTA')
    c1 = _chassi_em_estoque(modelo, loja)
    venda = venda_service.criar_venda_manual(
        cpf_cliente='12345678909', nome_cliente='Empresa Y',
        cep='01001000', endereco_logradouro='R', endereco_numero='1',
        endereco_complemento='', endereco_bairro='B', endereco_cidade='SP', endereco_uf='SP',
        itens=[{'numero_chassi': c1, 'valor_final': Decimal('1000')}],
        pagamentos=[{'forma_pagamento_hora': 'DINHEIRO_IE2', 'valor': Decimal('500'),
                     'numero_parcelas': 1, 'aut_id': None}],
        loja_id_override=loja.id, criado_por='t')
    assert venda.status == 'INCOMPLETO'
    assert venda.inscricao_estadual is None
    item = next(iter(venda.itens))
    venda_service.salvar_pedido_completo(
        venda_id=venda.id,
        header={'inscricao_estadual': 'ISENTO'},
        itens=[{'item_id': item.id, 'numero_chassi': c1, 'valor_final': Decimal('1000')}],
        pagamentos=[{'forma_pagamento_hora': 'DINHEIRO_IE2', 'valor': Decimal('500'),
                     'numero_parcelas': 1, 'aut_id': None}],
        usuario='t')
    _db.session.refresh(venda)
    assert venda.inscricao_estadual == 'ISENTO'
