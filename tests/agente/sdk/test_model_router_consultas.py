"""
FASE 2 do plano 2026-06-06-reducao-custo-agente-fast-path: downgrade Opus->Sonnet
das rotinas de CONSULTA/COTACAO via model_router (decisao do Rafael: "Tudo Sonnet"
conservador — sem camada Haiku).

Invariantes (R-EXEC-5 / T2.3):
- Categorias de consulta read-only + cotacao + CarVia -> Sonnet (fast_model).
- SEFAZ (faturar), financeiro (julgamento) e conversa_analise -> PERMANECEM Opus.
- Regex ancorados nos _TEMPLATES ja testados de session_automation_audit.py (T2.1),
  mais conservadores no routing (ex.: 'saldo' isolado removido — ambiguo c/ financeiro).
"""
import pytest

from app.agente.sdk.model_router import select_model

OPUS = "claude-opus-4-8"
SONNET = "claude-sonnet-4-6"


def _model(msg):
    return select_model(msg, OPUS, SONNET)[0]


def _reason(msg):
    return select_model(msg, OPUS, SONNET)[1]


# ─────────────────────────── Categorias-alvo F2 -> Sonnet
@pytest.mark.parametrize("msg", [
    # consulta_estoque
    "quanto tem de palmito em estoque",
    "tem em estoque o produto 4729098",
    "qual a disponibilidade de azeitona verde",
    # consulta_movimentacao
    "movimentacao do lote 099 desse produto",
    "qual a validade do lote 136 desse item",
    # monitoramento_entrega
    "a nota 12345 ja foi entregue",
    "que dia embarcou o pedido do atacadao",
    "cade a entrega do cliente assai",
    # cotacao
    "cotacao de frete para manaus cinco mil kg",
    "quanto custa o frete para sao paulo",
    # recalculo_frete_carvia
    "recalcular o frete do embarque carvia agora",
])
def test_categorias_consulta_vao_para_sonnet(msg):
    assert _model(msg) == SONNET, f"esperava Sonnet p/ {msg!r} (reason={_reason(msg)})"


# ─────────────────────────── NAO rebaixar (permanece Opus) — T2.3
@pytest.mark.parametrize("msg", [
    "faturar a nota fiscal do pedido do atacadao",          # SEFAZ (irreversivel)
    "preciso entender por que o pedido travou na separacao",  # analise
    "analise a margem do cliente assai nesse mes",           # analise/julgamento
    "qual o saldo da conta corrente do bradesco",            # financeiro (saldo ambiguo)
])
def test_nao_rebaixa_sefaz_financeiro_analise(msg):
    assert _model(msg) == OPUS, f"esperava Opus p/ {msg!r} (reason={_reason(msg)})"


# ─────────────────────────── Regressao: patterns pre-existentes intactos
def test_regressao_nf_po_segue_sonnet():
    assert _model("vincular pedido C123 na nota 456 pelo odoo") == SONNET


def test_regressao_conversa_generica_segue_opus():
    assert _model("me explica como funciona o fluxo de devolucao de mercadoria") == OPUS
