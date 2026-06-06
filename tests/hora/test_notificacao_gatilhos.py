"""Testa que os gatilhos enfileiram a notificacao (best-effort).

Cobre:
  - confirmar_venda chama enfileirar_notificacao('PEDIDO', venda.id) apos commit.
  - confirmar_venda nao propaga excecao quando enfileirar_notificacao falha.
  - _disparar_notificacao_nfe_safe chama enfileirar_notificacao('NFE', emissao_id).
  - _disparar_notificacao_nfe_safe engole excecao do enfileiramento sem propagar.
"""
from decimal import Decimal
from unittest.mock import patch, MagicMock

import pytest

from app import db as _db
from app.hora.models import (
    VENDA_STATUS_CONFIRMADO,
)
from app.hora.services import venda_service


# ---------------------------------------------------------------------------
# Fixture de limpeza (espelha test_pedido_workflow.py)
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _cleanup_hora_tables(db):
    """Limpa tabelas hora_* relevantes antes de cada teste."""
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


# ---------------------------------------------------------------------------
# Helper: cria venda em COTACAO (reusa padrao de test_pedido_workflow.py)
# ---------------------------------------------------------------------------

def _criar_pedido_cotacao(chassi, valor=Decimal('12500.00')):
    return venda_service.criar_venda_manual(
        cpf_cliente='12345678909',
        nome_cliente='Cliente Gatilho',
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
        criado_por='operador_gatilho',
    )


# ===========================================================================
# Gatilho C — confirmar_venda enfileira notificacao PEDIDO
# ===========================================================================

def test_confirmar_venda_enfileira_notificacao_pedido(
    db, chassi_em_estoque, loja_origem,
):
    """confirmar_venda deve chamar enfileirar_notificacao('PEDIDO', venda.id) apos commit."""
    venda = _criar_pedido_cotacao(chassi_em_estoque)

    with patch(
        'app.hora.services.tagplus.notificacao_whatsapp.enfileirar_notificacao',
    ) as mock_enf:
        confirmada = venda_service.confirmar_venda(venda.id, usuario='vendedor_gatilho')

    assert confirmada.status == VENDA_STATUS_CONFIRMADO
    mock_enf.assert_called_once_with('PEDIDO', confirmada.id)


def test_confirmar_venda_nao_propaga_excecao_de_notificacao(
    db, chassi_em_estoque, loja_origem,
):
    """Excecao no enfileiramento NAO deve reverter nem propagar — best-effort."""
    venda = _criar_pedido_cotacao(chassi_em_estoque)

    with patch(
        'app.hora.services.tagplus.notificacao_whatsapp.enfileirar_notificacao',
        side_effect=RuntimeError('falha simulada no RQ'),
    ):
        # NAO deve levantar excecao
        confirmada = venda_service.confirmar_venda(venda.id, usuario='vendedor_gatilho')

    # Transicao persistida mesmo com falha na notificacao
    assert confirmada.status == VENDA_STATUS_CONFIRMADO


# ===========================================================================
# Gatilho B — _disparar_notificacao_nfe_safe (helper unitario, sem DB)
# ===========================================================================

def test_disparar_notificacao_nfe_safe_chama_enfileirar(db):
    """_disparar_notificacao_nfe_safe deve chamar enfileirar_notificacao('NFE', emissao_id)."""
    from app.hora.services.tagplus.webhook_handler import _disparar_notificacao_nfe_safe

    with patch(
        'app.hora.services.tagplus.notificacao_whatsapp.enfileirar_notificacao',
    ) as mock_enf:
        _disparar_notificacao_nfe_safe(42)

    mock_enf.assert_called_once_with('NFE', 42)


def test_disparar_notificacao_nfe_safe_engole_excecao(db):
    """Excecao no enfileiramento deve ser engolida — nunca propaga."""
    from app.hora.services.tagplus.webhook_handler import _disparar_notificacao_nfe_safe

    with patch(
        'app.hora.services.tagplus.notificacao_whatsapp.enfileirar_notificacao',
        side_effect=Exception('falha simulada'),
    ):
        # NAO deve levantar excecao
        _disparar_notificacao_nfe_safe(99)
