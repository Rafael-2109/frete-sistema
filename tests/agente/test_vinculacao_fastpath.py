"""TDD do fast-path determinístico de vinculação NF×PO (N0 regex + N1 Haiku).

Zero-DB / mock. O detector é regex puro; o parser Haiku e o orquestrador são
testados com mock da chamada Anthropic e dos colaboradores do módulo.
"""
from app.agente.sdk.vinculacao_fastpath import should_intercept_vinculacao as det


# ───────────────────────────── N0: detector regex ─────────────────────────────
def test_vincular_molde_padrao():
    r = det("vincular o pedido C2620066 na nota 52019744 no odoo e no frete, "
            "validar se tem algum erro e faça o ajuste")
    assert r == {"acao": "vincular", "po": "C2620066", "nf": "52019744"}


def test_vincular_curto():
    r = det("vincular pedido C2620094 na nota 6935")
    assert r == {"acao": "vincular", "po": "C2620094", "nf": "6935"}


def test_desvincular_molde():
    r = det("Desfazer a vinculação NF 52019744 x C2620066")
    assert r == {"acao": "desvincular", "nf": "52019744", "po": "C2620066"}


def test_cancelar_isolado_nao_casa():
    assert det("cancelar") is None  # ambíguo -> LLM/AskUser


def test_pergunta_diagnostica_nao_casa():
    assert det("por que a nota 6935 está bloqueada?") is None


def test_vazio_nao_casa():
    assert det("") is None and det(None) is None
