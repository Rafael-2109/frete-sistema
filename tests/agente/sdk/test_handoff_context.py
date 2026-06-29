from app.agente.sdk.handoff_context import (
    estimate_tokens, build_handoff_context, render_handoff_block)


def test_estimate_tokens_heuristica():
    assert estimate_tokens("a" * 350) == 100

def test_build_inclui_campos_e_conta_tokens():
    ctx = build_handoff_context(
        objetivo="vincular NF 48862 ao PO C2615437",
        entidades={"nf": "48862", "po": "C2615437"},
        saldo={"validacao_id": 991})
    assert ctx["objetivo"].startswith("vincular")
    assert ctx["entidades"]["nf"] == "48862"
    assert ctx["saldo"]["validacao_id"] == 991
    assert ctx["tokens_estimados"] > 0
    assert ctx["truncado"] is False

def test_build_trunca_quando_excede_orcamento():
    grande = {f"k{i}": "x" * 500 for i in range(200)}  # ~28k tokens
    ctx = build_handoff_context(objetivo="obj", entidades=grande, max_tokens=2000)
    assert ctx["truncado"] is True
    assert len(ctx["entidades"]) < len(grande)   # removeu de fato (nao so' flag)
    assert ctx["tokens_estimados"] <= 2000

def test_render_block_envelopa_em_tag():
    ctx = build_handoff_context(objetivo="obj", entidades={"nf": "1"})
    bloco = render_handoff_block(ctx)
    assert bloco.startswith("<handoff_context>")
    assert bloco.rstrip().endswith("</handoff_context>")
    assert "obj" in bloco
