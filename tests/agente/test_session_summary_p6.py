"""P6 (#787) — summary da sessao nao deve congelar no meio.

Deterministico: testa AgentSession.needs_summarization como funcao pura (sem DB)
via SimpleNamespace + metodo unbound. O metodo so' le message_count, summary e
summary_message_count.

Bug #787: o summary foi gerado cedo (message_count=2, provavelmente pelo gatilho
de custo — sessao de $8.45) afirmando SUCESSO; a sessao cresceu para 4 (a falha/
reclamacao "arquivo vazio" veio depois) mas NAO regenerou — `messages_since_summary`
= 2 era < threshold (3). O summary ficou congelado registrando sucesso onde houve
falha.

Roadmap: docs/superpowers/plans/2026-06-04-roadmap-correcoes-agente-787.md (P6)
"""
import os
import sys
from types import SimpleNamespace

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from app.agente.models import AgentSession  # noqa: E402


def _sess(**kw):
    base = dict(message_count=0, summary=None, summary_message_count=0)
    base.update(kw)
    return SimpleNamespace(**base)


class TestNeedsSummarizationStaleness:
    def test_787_regenerates_after_new_exchange(self):
        # Summary gerado em count=2 (sucesso); sessao cresceu p/ 4 (1 exchange novo).
        # DEVE regenerar para capturar o desfecho real — antes ficava congelado.
        s = _sess(message_count=4, summary={"resumo_geral": "gerou o arquivo"}, summary_message_count=2)
        assert AgentSession.needs_summarization(s, threshold=3) is True

    def test_no_regenerate_for_single_new_message(self):
        # 1 mensagem nova isolada nao justifica regenerar (evita custo Sonnet por msg).
        s = _sess(message_count=4, summary={"x": 1}, summary_message_count=3)
        assert AgentSession.needs_summarization(s, threshold=3) is False

    def test_fresh_summary_not_stale(self):
        s = _sess(message_count=4, summary={"x": 1}, summary_message_count=4)
        assert AgentSession.needs_summarization(s, threshold=3) is False


class TestNeedsSummarizationRegression:
    def test_first_summary_when_threshold_reached(self):
        assert AgentSession.needs_summarization(_sess(message_count=3, summary=None), threshold=3) is True

    def test_below_threshold_no_summary(self):
        assert AgentSession.needs_summarization(_sess(message_count=2, summary=None), threshold=3) is False
