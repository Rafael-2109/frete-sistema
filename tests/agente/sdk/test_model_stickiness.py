"""
TDD do "modelo decidido 1x por sessao" (bug 2026-06-15).

O smart routing rebaixou Opus->Sonnet no MEIO de uma sessao ("deu certo?"),
matando o cache MODEL-SCOPED e fazendo o Sonnet rebaixado responder sobre a
propria troca de modelo em vez da tarefa.

Regra (diretriz Rafael):
- Web: a config do modelo PERSISTE pela sessao; so troca se o usuario alterar
  EXPLICITAMENTE (aí custa cache, conscientemente). Routing automatico nunca
  rebaixa mid-sessao.
- Client (set_model): so troca quando o modelo pedido difere do atual da sessao
  (permite a troca explicita; evita churn redundante que mataria o cache a toa).
"""
from app.agente.sdk.model_router import pick_warm_model, should_switch_model


# ─── pick_warm_model (web, sessao quente): config persiste ────────────────

def test_warm_sem_config_usuario_mantem_modelo_da_sessao():
    # Usuario nao mandou modelo (None) -> persiste o modelo da sessao.
    assert pick_warm_model(session_model="claude-opus-4-8", user_model=None) == "claude-opus-4-8"


def test_warm_config_igual_mantem_modelo_da_sessao():
    # CASO DO BUG: follow-up nao muda o seletor -> mantem (nao rebaixa).
    assert pick_warm_model(
        session_model="claude-opus-4-8", user_model="claude-opus-4-8"
    ) == "claude-opus-4-8"


def test_warm_troca_explicita_respeita_usuario():
    # Usuario MUDOU o seletor mid-sessao -> respeita (custa cache, consciente).
    assert pick_warm_model(
        session_model="claude-opus-4-8", user_model="claude-fable-5"
    ) == "claude-fable-5"


def test_warm_sessao_em_sonnet_persiste_sonnet():
    # Sessao criada em Sonnet (1a msg rebaixada) persiste em Sonnet sem config.
    assert pick_warm_model(session_model="claude-sonnet-4-6", user_model=None) == "claude-sonnet-4-6"


# ─── should_switch_model (client.py): so troca real ───────────────────────

def test_switch_mesmo_modelo_nao_troca():
    # Evita churn redundante (cache MODEL-SCOPED).
    assert should_switch_model("claude-opus-4-8", "claude-opus-4-8") is False


def test_switch_modelo_diferente_troca():
    # Troca explicita chega aqui (caller ja garantiu que routing nao rebaixa).
    assert should_switch_model("claude-fable-5", "claude-opus-4-8") is True


def test_switch_requested_none_nao_troca():
    assert should_switch_model(None, "claude-opus-4-8") is False


def test_switch_sessao_sem_modelo_registrado_troca():
    # pooled legado sem model (None) + pedido valido -> garante o modelo.
    assert should_switch_model("claude-opus-4-8", None) is True
