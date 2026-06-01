"""
Testes do fix de idle-in-transaction timeout no Recebimento LF.

Contexto (bug PROD 2026-06-01, RecLF 248/249):
    O step 4 (_step_04_gerar_po) abre uma transacao local (_get_recebimento)
    e em seguida bloqueia ate FIRE_TIMEOUT=120s em action_gerar_po_dfe via
    _fire_and_poll. Com a transacao ABERTA durante a chamada Odoo longa, o
    Postgres mata a conexao por idle_in_transaction_session_timeout=120s
    (config.py), gerando o erro secundario:
        "Can't reconnect until invalid transaction is rolled back."

    Fix 1 (raiz): _fire_and_poll libera a sessao (rollback) ANTES do fire e
                  antes de cada sleep do polling -> conexao nunca fica
                  "idle in transaction" durante a espera Odoo.
    Fix 2 (defesa): _is_recoverable_db_error classifica esse erro como
                    recuperavel, para que _safe_update/_checkpoint recuperem
                    (rollback + close + dispose + retry) em vez de propagar.
"""
from unittest.mock import MagicMock

import pytest

import app.recebimento.services.recebimento_lf_odoo_service as mod


# Mensagem EXATA observada em PROD (recebimento_lf.erro_mensagem dos RecLF 248/249)
PENDING_ROLLBACK_MSG = (
    "Can't reconnect until invalid transaction is rolled back.  "
    "Please rollback() fully before proceeding "
    "(Background on this error at: https://sqlalche.me/e/20/8s2b)"
)
IDLE_TX_MSG = "terminating connection due to idle-in-transaction timeout"


class TestIsRecoverableDbError:
    """Fix 2 — classificacao do erro como recuperavel."""

    @pytest.mark.parametrize("msg", [
        PENDING_ROLLBACK_MSG,
        IDLE_TX_MSG,
        "server closed the connection unexpectedly",
        "SSL error: decryption failed or bad record mac",
        "Instance <RecebimentoLf> is not bound to a Session",
    ])
    def test_classifica_recuperavel(self, msg):
        assert mod._is_recoverable_db_error(Exception(msg)) is True
        # tambem deve aceitar string crua
        assert mod._is_recoverable_db_error(msg) is True

    @pytest.mark.parametrize("msg", [
        'column "foo" does not exist',
        "Recebimento 248 nao encontrado",
        "Purchase Order nao foi criado apos action_gerar_po_dfe",
    ])
    def test_classifica_nao_recuperavel(self, msg):
        assert mod._is_recoverable_db_error(Exception(msg)) is False


class TestFireAndPollReleasesSession:
    """Fix 1 — libera transacao local ANTES da chamada Odoo longa."""

    def test_rollback_acontece_antes_do_fire(self, monkeypatch):
        fake_db = MagicMock()
        monkeypatch.setattr(mod, "db", fake_db)

        ordem = []
        fake_db.session.rollback.side_effect = lambda: ordem.append("rollback")

        def fire_fn():
            ordem.append("fire")
            return 999  # completa dentro do timeout (truthy)

        def poll_fn():
            return 999

        svc = mod.RecebimentoLfOdooService()
        resultado = svc._fire_and_poll(
            odoo=MagicMock(), fire_fn=fire_fn, poll_fn=poll_fn, step_name="TestStep"
        )

        assert resultado == 999
        # rollback DEVE ter ocorrido, e ANTES do fire (sem idle-in-transaction)
        assert "rollback" in ordem, "sessao nao foi liberada antes do fire"
        assert ordem.index("rollback") < ordem.index("fire")
