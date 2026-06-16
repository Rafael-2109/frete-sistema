"""BUG-2 (avaliação 360): guard de sessão SQLAlchemy abortada nas MCP tools
de memória (`_run_with_session_guard`).

Garante que uma transação abortada herdada (Teams gthread / thread de
processamento reusando o app context) não derruba a tool — ela faz rollback
e re-tenta UMA vez —, e que erros normais NÃO são re-tentados.

Sintoma original: Sentry PYTHON-FLASK-EG ("Can't reconnect until invalid
transaction is rolled back", regressed, 3 usuários) em list_memories no Teams.
"""
import pytest
from sqlalchemy.exc import (
    PendingRollbackError, InvalidRequestError, OperationalError,
)

from app import create_app
from app.agente.tools.memory_mcp_tool import _run_with_session_guard


@pytest.fixture
def app_ctx():
    app = create_app()
    with app.app_context():
        yield app


def test_guard_recupera_sessao_abortada_pending_rollback(app_ctx):
    """PendingRollbackError -> rollback + retry único -> sucesso."""
    chamadas = []

    def func():
        chamadas.append(1)
        if len(chamadas) == 1:
            raise PendingRollbackError(
                "Can't reconnect until invalid transaction is rolled back"
            )
        return "ok"

    resultado = _run_with_session_guard(func)
    assert resultado == "ok"
    assert len(chamadas) == 2  # falhou 1x, re-tentou após rollback, sucedeu


def test_guard_recupera_invalid_request_transacao_invalida(app_ctx):
    """InvalidRequestError com mensagem de transação inválida também recupera."""
    chamadas = []

    def func():
        chamadas.append(1)
        if len(chamadas) == 1:
            raise InvalidRequestError(
                "This Session's transaction has been rolled back due to a "
                "previous exception during flush."
            )
        return "recuperado"

    assert _run_with_session_guard(func) == "recuperado"
    assert len(chamadas) == 2


def test_guard_nao_retenta_erro_de_negocio(app_ctx):
    """Erro não relacionado a transação abortada propaga SEM retry."""
    chamadas = []

    def func():
        chamadas.append(1)
        raise ValueError("erro de negócio normal")

    with pytest.raises(ValueError):
        _run_with_session_guard(func)
    assert len(chamadas) == 1  # NÃO re-tentou


def test_guard_nao_retenta_invalid_request_nao_transacional(app_ctx):
    """InvalidRequestError SEM mensagem de transação (ex: objeto já anexado)
    NÃO deve ser re-tentado — não é o caso do BUG-2."""
    chamadas = []

    def func():
        chamadas.append(1)
        raise InvalidRequestError("Object '<X>' is already attached to session")

    with pytest.raises(InvalidRequestError):
        _run_with_session_guard(func)
    assert len(chamadas) == 1


def test_guard_caminho_normal_chama_func_uma_vez(app_ctx):
    """Sem erro: func() é chamada exatamente uma vez (sem overhead)."""
    chamadas = []

    def func():
        chamadas.append(1)
        return 123

    assert _run_with_session_guard(func) == 123
    assert len(chamadas) == 1


def test_guard_recupera_conexao_ssl_morta(app_ctx, monkeypatch):
    """PYTHON-FLASK-Y5/HW/Y7: OperationalError de SSL drop -> rollback +
    engine.dispose() + retry único -> sucesso."""
    from app import db
    dispostos = []
    monkeypatch.setattr(db.engine, "dispose", lambda *a, **k: dispostos.append(1))
    chamadas = []

    def func():
        chamadas.append(1)
        if len(chamadas) == 1:
            raise OperationalError(
                "SELECT 1", {},
                Exception("SSL connection has been closed unexpectedly"),
            )
        return "reconectado"

    assert _run_with_session_guard(func) == "reconectado"
    assert len(chamadas) == 2       # falhou 1x, re-tentou após descartar o pool
    assert dispostos == [1]         # engine.dispose() chamado no SSL drop


def test_guard_nao_retenta_operational_error_nao_conexao(app_ctx):
    """OperationalError que NÃO é SSL drop/conexão morta propaga SEM retry
    (ex: serialization failure não é o caso de reconexão)."""
    chamadas = []

    def func():
        chamadas.append(1)
        raise OperationalError(
            "SELECT 1", {},
            Exception("could not serialize access due to concurrent update"),
        )

    with pytest.raises(OperationalError):
        _run_with_session_guard(func)
    assert len(chamadas) == 1       # NÃO re-tentou
