"""Regressao: race de persistencia que perdia a resposta do assistente quando o
cliente desconectava ANTES do turno terminar (sessao do Marcus, 2026-05-29).

Causa raiz: o path persistente tem 2 gravacoes — a thread daemon
(`run_async_stream`, PRIMARY, roda quando o turno completa) e o `finally` do
generator (DEFESA). Quando o cliente desconectava cedo, a DEFESA rodava antes
com `full_text=''`, persistia (user msg + commit) e marcava `_persisted=True`,
bloqueando o PRIMARY de salvar a resposta real quando ela ficava pronta.

Fix: a defesa so' persiste se o primary JA terminou (`not thread.is_alive()`).
Se a thread daemon ainda processa, delega a ela.
"""


def test_finally_delega_ao_primary_quando_thread_viva():
    """Thread daemon (primary) ainda processando -> generator finally NAO persiste
    (delega, para nao gravar full_text vazio e bloquear o primary)."""
    from app.agente.routes.chat import _should_persist_in_finally

    assert _should_persist_in_finally(thread_alive=True) is False


def test_finally_persiste_quando_thread_morta():
    """Thread daemon terminou -> generator finally persiste (defesa em profundidade)."""
    from app.agente.routes.chat import _should_persist_in_finally

    assert _should_persist_in_finally(thread_alive=False) is True
