"""
Testes de integracao dos hooks chat — Tasks 21, 22, 23.

Valida que os helpers em app/chat/hooks/ chamam SystemNotifier com o
payload correto para cada cenario (recebimento ok/erro, DFE bloqueado,
CTe divergente).
"""
import uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from app.chat.hooks.recebimento import notify_recebimento_finalizado
from app.chat.hooks.dfe_bloqueado import notify_dfe_bloqueado
from app.chat.hooks.cte_divergente import notify_cte_divergente
from app.chat.models import ChatMessage

_RUN = uuid.uuid4().hex[:8]


# =============================================================================
# Task 21 — recebimento finalizado
# =============================================================================

@patch('app.chat.realtime.publisher.publish')
def test_notify_recebimento_ok(mock_pub, db_session, user_factory):
    u = user_factory(email=f'hook_r_ok_{_RUN}@t.local')
    recebimento = SimpleNamespace(
        id=999001,
        status='processado',
        transfer_status='concluido',
        numero_nf='12345',
        transfer_erro_mensagem=None,
    )
    notify_recebimento_finalizado(recebimento, destinatarios=[u.id])
    msg = ChatMessage.query.filter_by(sender_system_source='recebimento').order_by(
        ChatMessage.id.desc()
    ).first()
    assert msg is not None
    assert msg.nivel == 'INFO'
    assert msg.deep_link == '/recebimento/999001'
    assert '12345' in msg.content


@patch('app.chat.realtime.publisher.publish')
def test_notify_recebimento_erro(mock_pub, db_session, user_factory):
    u = user_factory(email=f'hook_r_err_{_RUN}@t.local')
    recebimento = SimpleNamespace(
        id=999002,
        status='processado',
        transfer_status='erro',
        numero_nf='54321',
        transfer_erro_mensagem='Timeout ao validar NF',
    )
    notify_recebimento_finalizado(recebimento, destinatarios=[u.id])
    msg = ChatMessage.query.filter_by(sender_system_source='recebimento').order_by(
        ChatMessage.id.desc()
    ).first()
    assert msg is not None
    assert msg.nivel == 'CRITICO'
    assert 'ERRO' in msg.content.upper()
    assert 'Timeout' in msg.content


@patch('app.chat.realtime.publisher.publish')
def test_notify_recebimento_nao_quebra_se_notifier_falhar(
    mock_pub, db_session, user_factory, caplog
):
    """Hook nao deve levantar excecao mesmo se SystemNotifier falhar."""
    u = user_factory(email=f'hook_r_ex_{_RUN}@t.local')
    recebimento = SimpleNamespace(
        id=999003, status='erro', transfer_status='erro',
        numero_nf='99', transfer_erro_mensagem='x',
    )
    with patch(
        'app.chat.hooks.recebimento.SystemNotifier.alert',
        side_effect=RuntimeError('banco fora'),
    ):
        # Nao deve levantar
        notify_recebimento_finalizado(recebimento, destinatarios=[u.id])


# =============================================================================
# Task 22 — DFE bloqueado
# =============================================================================

@patch('app.chat.realtime.publisher.publish')
def test_notify_dfe_bloqueado(mock_pub, db_session, user_factory):
    u = user_factory(email=f'hook_dfe_{_RUN}@t.local')
    notify_dfe_bloqueado(
        dfe_id=777,
        nf_numero='88888',
        motivo='Divergencia de preco no item 3 (esperado 10, recebido 15)',
        fornecedor='ATACADAO S.A.',
        destinatarios=[u.id],
    )
    msg = ChatMessage.query.filter_by(sender_system_source='dfe').order_by(
        ChatMessage.id.desc()
    ).first()
    assert msg is not None
    assert msg.nivel == 'ATENCAO'
    assert msg.deep_link == '/recebimento/dfe/777'
    assert '88888' in msg.content or '88888' in (msg.dados or {}).get('nf_numero', '')


# =============================================================================
# Task 23 — CTe divergente
# =============================================================================

@patch('app.chat.realtime.publisher.publish')
def test_notify_cte_divergencia_critica(mock_pub, db_session, user_factory):
    """>= 20% eh CRITICO."""
    u = user_factory(email=f'hook_cte_c_{_RUN}@t.local')
    cte = SimpleNamespace(id=111, numero='CTE-001')
    notify_cte_divergente(
        cte, valor_cotado=Decimal('500.00'), valor_cte=Decimal('650.00'),
        destinatarios=[u.id],
    )
    msg = ChatMessage.query.filter_by(sender_system_source='cte').order_by(
        ChatMessage.id.desc()
    ).first()
    assert msg is not None
    assert msg.nivel == 'CRITICO'  # 30% > 20%
    assert '650' in msg.content
    assert '500' in msg.content


@patch('app.chat.realtime.publisher.publish')
def test_notify_cte_divergencia_atencao(mock_pub, db_session, user_factory):
    """< 20% eh ATENCAO."""
    u = user_factory(email=f'hook_cte_a_{_RUN}@t.local')
    cte = SimpleNamespace(id=222, numero='CTE-002')
    notify_cte_divergente(
        cte, valor_cotado=Decimal('500.00'), valor_cte=Decimal('550.00'),
        destinatarios=[u.id],
    )
    msg = ChatMessage.query.filter_by(sender_system_source='cte').order_by(
        ChatMessage.id.desc()
    ).first()
    assert msg is not None
    assert msg.nivel == 'ATENCAO'  # 10% < 20%


@patch('app.chat.realtime.publisher.publish')
def test_notify_cte_cotado_zero(mock_pub, db_session, user_factory):
    """Guard: valor_cotado=0 nao levanta DivisionByZero."""
    u = user_factory(email=f'hook_cte_z_{_RUN}@t.local')
    cte = SimpleNamespace(id=333, numero='CTE-003')
    notify_cte_divergente(
        cte, valor_cotado=Decimal('0'), valor_cte=Decimal('100.00'),
        destinatarios=[u.id],
    )
    # Deve criar msg (nivel CRITICO pois pct=100%)
    msg = ChatMessage.query.filter_by(sender_system_source='cte').order_by(
        ChatMessage.id.desc()
    ).first()
    assert msg is not None
    assert msg.nivel == 'CRITICO'
