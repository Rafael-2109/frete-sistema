"""P5 (#787) — calibracao do detector de frustracao.

Deterministico (heuristica local, sem API). Ataca os DOIS lados do achado #787:
- FALSO NEGATIVO: "Nao gerou o excel, arquivo esta vazio" pontuava 0 (marcadores
  de FALHA DE ENTREGA ausentes).
- FALSO POSITIVO (parte dos 49%): 3 mensagens curtas neutras seguidas atingiam o
  threshold via Sinal 5 (<=3 palavras -> +1) + Sinal 6 (trend all(s>=1) -> +2).

Roadmap: docs/superpowers/plans/2026-06-04-roadmap-correcoes-agente-787.md (P5)
"""
import os
import sys

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from app.agente.services.sentiment_detector import detect_frustration  # noqa: E402


# =====================================================================
# FALSO NEGATIVO — marcadores de FALHA DE ENTREGA/RESULTADO
# =====================================================================

class TestDeliveryFailureMarkers:
    def test_787_arquivo_vazio_is_frustration(self):
        # O caso exato da #787 (agent_step 203) — pontuava 0 (falso negativo).
        is_frustrated, score = detect_frustration("Não gerou o excel, arquivo está vazio")
        assert is_frustrated is True
        assert score >= 3

    @pytest.mark.parametrize("msg", [
        "não gerou o relatório",
        "o arquivo veio vazio",
        "cadê o excel?",
        "o link não abre",
        "não baixou nada",
        "o excel não carrega",
        "deu erro de novo",
        "o pdf não abriu",
    ])
    def test_delivery_failure_phrases_score_frustration(self, msg):
        is_frustrated, score = detect_frustration(msg)
        assert is_frustrated is True, f"nao detectou frustracao em: {msg!r} (score={score})"


# =====================================================================
# FALSO POSITIVO — 3 mensagens curtas neutras NAO sao frustracao
# =====================================================================

class TestShortMessagesNotFrustration:
    def test_three_short_neutral_messages_do_not_trigger(self):
        # Sequencia neutra de chat operacional (cada msg da +1 no Sinal 5).
        # Com o trend exigindo s>=2, a 3a NAO deve disparar frustracao.
        s1 = detect_frustration("ok")[1]
        s2 = detect_frustration("e agora?", recent_scores=[s1])[1]
        is_frustrated, score = detect_frustration("mostra", recent_scores=[s1, s2])
        assert is_frustrated is False, f"falso positivo em mensagens curtas neutras (score={score})"

    def test_real_frustration_trend_still_triggers(self):
        # Trend REAL (turnos com marcadores) ainda dispara via Sinal 6.
        # Marcadores dao score 3; uma 3a msg curta deve somar o trend e manter deteccao.
        is_frustrated, score = detect_frustration("e?", recent_scores=[3, 3])
        assert is_frustrated is True, f"trend real deixou de detectar (score={score})"


# =====================================================================
# Regressao — marcadores e sinais existentes seguem funcionando
# =====================================================================

class TestExistingSignalsStillWork:
    @pytest.mark.parametrize("msg", [
        "não era isso",
        "está errado",
        "de novo",
        "não funciona",
        "responde direto por favor",
    ])
    def test_existing_markers_still_detected(self, msg):
        assert detect_frustration(msg)[0] is True

    def test_short_message_after_error_still_frustration(self):
        assert detect_frustration("e?", had_error=True)[0] is True

    def test_neutral_question_not_frustration(self):
        assert detect_frustration("Qual o estoque de palmito no CD?")[0] is False
