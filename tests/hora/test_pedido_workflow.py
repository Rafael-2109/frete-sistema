"""Tests do workflow de pedido de venda: COTACAO -> CONFIRMADO -> FATURADO -> CANCELADO.

Cobre:
  - criar_venda_manual cria COTACAO + reserva chassi (RESERVADA).
  - confirmar_venda transiciona COTACAO -> CONFIRMADO.
  - cancelar_venda transiciona qualquer -> CANCELADO + DEVOLVIDA chassi.
  - editar_venda respeita matriz de campos por status.
  - adicionar/remover/editar_item so em COTACAO.
  - lock pessimista impede double-reserva.
  - auditoria registra todas as transicoes.

NOTA: services usam db.session.commit() (nao apenas flush), entao escapam do
nested transaction do fixture db. Cada teste limpa via autouse fixture e
escolhe CNPJ/chassi unicos (suffix com test_id).
"""
from decimal import Decimal

import pytest

from app import db as _db
from app.hora.models import (
    HoraMotoEvento,
    HoraVendaAuditoria,
    HoraVendaItem,
    VENDA_STATUS_CANCELADO,
    VENDA_STATUS_CONFIRMADO,
    VENDA_STATUS_COTACAO,
)
from app.hora.services import venda_service
from app.hora.services.moto_service import get_or_create_moto, registrar_evento


@pytest.fixture(autouse=True)
def _cleanup_hora_tables(db):
    """Limpa tabelas hora_* relevantes ao teste antes de cada execucao.

    Services usam db.session.commit(), entao escapam do nested transaction do
    fixture `db` global. Limpa por CNPJ/chassi-prefixo determinados pelos
    helpers (LojaOrigemTest/LojaDestinoTest, '9ABCDTEST').
    """
    _db.session.execute(_db.text("""
        DELETE FROM hora_venda_auditoria
            WHERE venda_id IN (SELECT id FROM hora_venda
                WHERE loja_id IN (
                    SELECT id FROM hora_loja
                    WHERE apelido IN ('LojaOrigemTest','LojaDestinoTest')
                )
            );
        DELETE FROM hora_venda_divergencia
            WHERE venda_id IN (SELECT id FROM hora_venda
                WHERE loja_id IN (
                    SELECT id FROM hora_loja
                    WHERE apelido IN ('LojaOrigemTest','LojaDestinoTest')
                )
            );
        DELETE FROM hora_venda_item
            WHERE venda_id IN (SELECT id FROM hora_venda
                WHERE loja_id IN (
                    SELECT id FROM hora_loja
                    WHERE apelido IN ('LojaOrigemTest','LojaDestinoTest')
                )
            );
        DELETE FROM hora_venda
            WHERE loja_id IN (
                SELECT id FROM hora_loja
                WHERE apelido IN ('LojaOrigemTest','LojaDestinoTest')
            );
        DELETE FROM hora_moto_evento WHERE numero_chassi LIKE '9ABCDTEST%';
        DELETE FROM hora_moto WHERE numero_chassi LIKE '9ABCDTEST%';
        DELETE FROM hora_loja WHERE apelido IN ('LojaOrigemTest','LojaDestinoTest');
        DELETE FROM hora_modelo WHERE nome_modelo = 'TESTE-MODEL';
    """))
    _db.session.commit()
    yield
    _db.session.rollback()


# ----- Helpers -----

def _criar_pedido_cotacao(chassi, valor=Decimal('12500.00')):
    return venda_service.criar_venda_manual(
        cpf_cliente='12345678909',
        nome_cliente='Cliente Teste',
        cep='01310100',
        endereco_logradouro='Av Paulista',
        endereco_numero='1000',
        endereco_complemento=None,
        endereco_bairro='Bela Vista',
        endereco_cidade='Sao Paulo',
        endereco_uf='SP',
        numero_chassi=chassi,
        valor_final=valor,
        forma_pagamento='PIX',
        criado_por='operador_x',
    )


def _segundo_chassi(loja, modelo, sufixo='SECONDARY00000000'):
    chassi = f'9ABCDTEST{sufixo}'[:30]
    get_or_create_moto(
        numero_chassi=chassi,
        modelo_nome=modelo.nome_modelo, cor='PRATA',
        criado_por='fixture',
    )
    registrar_evento(numero_chassi=chassi, tipo='RECEBIDA', loja_id=loja.id)
    registrar_evento(numero_chassi=chassi, tipo='CONFERIDA', loja_id=loja.id)
    _db.session.flush()
    return chassi


# ============================================================
# Criacao
# ============================================================

def test_criar_venda_manual_cria_cotacao_e_reserva_chassi(
    db, chassi_em_estoque, loja_origem,
):
    venda = _criar_pedido_cotacao(chassi_em_estoque)
    assert venda.status == VENDA_STATUS_COTACAO
    assert venda.id is not None
    assert venda.confirmado_em is None
    assert venda.cancelado_em is None
    assert venda.faturado_em is None
    assert len(venda.itens) == 1
    assert venda.itens[0].numero_chassi == chassi_em_estoque

    # Evento RESERVADA emitido.
    ev = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi_em_estoque, tipo='RESERVADA')
        .first()
    )
    assert ev is not None
    assert ev.origem_tabela == 'hora_venda_item'

    # Auditoria CRIOU registrada.
    audit = HoraVendaAuditoria.query.filter_by(venda_id=venda.id, acao='CRIOU').first()
    assert audit is not None
    assert audit.usuario == 'operador_x'


def test_criar_pedido_chassi_indisponivel_falha(
    db, chassi_em_estoque, loja_origem,
):
    # Primeiro pedido reserva.
    _criar_pedido_cotacao(chassi_em_estoque)
    # Segundo pedido no mesmo chassi falha (ultimo evento RESERVADA — fora estoque).
    with pytest.raises(venda_service.ChassiIndisponivelError):
        _criar_pedido_cotacao(chassi_em_estoque)


# ============================================================
# Confirmacao
# ============================================================

def test_confirmar_venda_transiciona_para_confirmado(
    db, chassi_em_estoque, loja_origem,
):
    venda = _criar_pedido_cotacao(chassi_em_estoque)
    confirmada = venda_service.confirmar_venda(venda.id, usuario='vendedor_y')
    assert confirmada.status == VENDA_STATUS_CONFIRMADO
    assert confirmada.confirmado_em is not None
    assert confirmada.confirmado_por == 'vendedor_y'
    audit = HoraVendaAuditoria.query.filter_by(venda_id=venda.id, acao='CONFIRMOU').first()
    assert audit is not None


def test_confirmar_venda_ja_confirmada_falha(
    db, chassi_em_estoque, loja_origem,
):
    venda = _criar_pedido_cotacao(chassi_em_estoque)
    venda_service.confirmar_venda(venda.id, usuario='x')
    with pytest.raises(venda_service.TransicaoInvalidaError):
        venda_service.confirmar_venda(venda.id, usuario='x')


# ============================================================
# Cancelamento
# ============================================================

def test_cancelar_venda_cotacao_devolve_chassi(
    db, chassi_em_estoque, loja_origem,
):
    venda = _criar_pedido_cotacao(chassi_em_estoque)
    cancelada = venda_service.cancelar_venda(
        venda.id, motivo='cliente desistiu', usuario='gerente',
    )
    assert cancelada.status == VENDA_STATUS_CANCELADO
    assert cancelada.cancelado_em is not None
    assert cancelada.cancelado_por == 'gerente'
    assert cancelada.cancelamento_motivo == 'cliente desistiu'

    # DEVOLVIDA emitido (chassi volta ao estoque).
    ev = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi_em_estoque, tipo='DEVOLVIDA')
        .order_by(HoraMotoEvento.id.desc()).first()
    )
    assert ev is not None


def test_cancelar_venda_motivo_curto_falha(
    db, chassi_em_estoque, loja_origem,
):
    venda = _criar_pedido_cotacao(chassi_em_estoque)
    with pytest.raises(ValueError, match=r'(?i)motivo'):
        venda_service.cancelar_venda(venda.id, motivo='', usuario='x')


def test_cancelar_venda_idempotente(
    db, chassi_em_estoque, loja_origem,
):
    venda = _criar_pedido_cotacao(chassi_em_estoque)
    venda_service.cancelar_venda(venda.id, motivo='primeiro motivo', usuario='x')
    venda2 = venda_service.cancelar_venda(venda.id, motivo='segundo motivo', usuario='y')
    # Idempotente: nao quebra, mas tambem nao re-aplica.
    assert venda2.status == VENDA_STATUS_CANCELADO
    assert venda2.cancelamento_motivo == 'primeiro motivo'


# ============================================================
# Edicao do header
# ============================================================

def test_editar_observacoes_em_qualquer_status_exceto_cancelado(
    db, chassi_em_estoque, loja_origem,
):
    venda = _criar_pedido_cotacao(chassi_em_estoque)
    venda_service.editar_venda(
        venda.id, observacoes='nova obs', usuario='op',
    )
    assert venda.observacoes == 'nova obs'

    venda_service.confirmar_venda(venda.id, usuario='op')
    venda_service.editar_venda(
        venda.id, observacoes='outra obs', usuario='op',
    )
    assert venda.observacoes == 'outra obs'


def test_editar_cliente_em_confirmado_falha(
    db, chassi_em_estoque, loja_origem,
):
    venda = _criar_pedido_cotacao(chassi_em_estoque)
    venda_service.confirmar_venda(venda.id, usuario='op')
    with pytest.raises(venda_service.TransicaoInvalidaError):
        venda_service.editar_venda(
            venda.id, nome_cliente='Novo Nome', usuario='op',
        )


def test_editar_cancelado_falha(
    db, chassi_em_estoque, loja_origem,
):
    venda = _criar_pedido_cotacao(chassi_em_estoque)
    venda_service.cancelar_venda(venda.id, motivo='teste', usuario='op')
    with pytest.raises(venda_service.TransicaoInvalidaError):
        venda_service.editar_venda(
            venda.id, observacoes='nova', usuario='op',
        )


# ============================================================
# Edicao de itens (so em COTACAO)
# ============================================================

def test_adicionar_item_em_cotacao(
    db, chassi_em_estoque, loja_origem, modelo_moto,
):
    venda = _criar_pedido_cotacao(chassi_em_estoque)
    chassi2 = _segundo_chassi(loja_origem, modelo_moto, 'CHASSI2')

    item = venda_service.adicionar_item_pedido(
        venda_id=venda.id, numero_chassi=chassi2,
        valor_final=Decimal('15000.00'), usuario='op',
    )
    assert item.numero_chassi == chassi2
    assert venda.valor_total == Decimal('27500.00')

    # Ev RESERVADA no novo.
    ev = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi2, tipo='RESERVADA')
        .first()
    )
    assert ev is not None


def test_adicionar_item_em_confirmado_falha(
    db, chassi_em_estoque, loja_origem, modelo_moto,
):
    venda = _criar_pedido_cotacao(chassi_em_estoque)
    venda_service.confirmar_venda(venda.id, usuario='op')
    chassi2 = _segundo_chassi(loja_origem, modelo_moto, 'CHASSI3')
    with pytest.raises(venda_service.TransicaoInvalidaError):
        venda_service.adicionar_item_pedido(
            venda_id=venda.id, numero_chassi=chassi2,
            valor_final=Decimal('1.00'), usuario='op',
        )


def test_remover_item_devolve_chassi(
    db, chassi_em_estoque, loja_origem, modelo_moto,
):
    venda = _criar_pedido_cotacao(chassi_em_estoque)
    chassi2 = _segundo_chassi(loja_origem, modelo_moto, 'CHASSI4')
    item = venda_service.adicionar_item_pedido(
        venda_id=venda.id, numero_chassi=chassi2,
        valor_final=Decimal('5000.00'), usuario='op',
    )
    venda_service.remover_item_pedido(
        venda_id=venda.id, item_id=item.id, usuario='op',
    )
    assert venda.valor_total == Decimal('12500.00')
    assert HoraVendaItem.query.get(item.id) is None
    ev = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi2, tipo='DEVOLVIDA')
        .first()
    )
    assert ev is not None


def test_remover_ultimo_item_falha(
    db, chassi_em_estoque, loja_origem,
):
    venda = _criar_pedido_cotacao(chassi_em_estoque)
    item_unico = venda.itens[0]
    with pytest.raises(ValueError, match=r'(?i)cancele o pedido'):
        venda_service.remover_item_pedido(
            venda_id=venda.id, item_id=item_unico.id, usuario='op',
        )


def test_editar_item_troca_chassi(
    db, chassi_em_estoque, loja_origem, modelo_moto,
):
    venda = _criar_pedido_cotacao(chassi_em_estoque)
    chassi2 = _segundo_chassi(loja_origem, modelo_moto, 'CHASSITROCA')
    item = venda.itens[0]
    venda_service.editar_item_pedido(
        venda_id=venda.id, item_id=item.id,
        novo_chassi=chassi2, usuario='op',
    )
    item_db = HoraVendaItem.query.get(item.id)
    assert item_db.numero_chassi == chassi2

    # Antigo recebeu DEVOLVIDA, novo recebeu RESERVADA.
    ev_dev = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi_em_estoque, tipo='DEVOLVIDA')
        .first()
    )
    ev_res = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=chassi2, tipo='RESERVADA')
        .first()
    )
    assert ev_dev is not None
    assert ev_res is not None
