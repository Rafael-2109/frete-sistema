"""TDD do fast-path determinístico de vinculação NF×PO (N0 regex + N1 Haiku).

Zero-DB / mock. O detector é regex puro; o parser Haiku e o orquestrador são
testados com mock da chamada Anthropic e dos colaboradores do módulo.
"""
from unittest.mock import patch

import app.agente.sdk.vinculacao_fastpath as fp
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


# ───────────────────────── N1: parser Haiku (fallback) ─────────────────────────
def test_parse_haiku_extrai_json():
    with patch.object(fp, "_call_haiku",
                      return_value='{"acao":"vincular","nf":"6935","po":"C2620094"}'):
        r = fp.parse_vinculacao_haiku("pode vincular a 6935 com o C2620094?")
    assert r == {"acao": "vincular", "nf": "6935", "po": "C2620094"}


def test_parse_haiku_acao_nula_retorna_none():
    with patch.object(fp, "_call_haiku", return_value='{"acao":null}'):
        assert fp.parse_vinculacao_haiku("bom dia, tudo certo com a nota?") is None


def test_parse_haiku_so_chama_se_keyword_recebimento():
    # sem keyword (nota/nf/pedido/vincul) nao gasta Haiku
    with patch.object(fp, "_call_haiku") as mock:
        assert fp.parse_vinculacao_haiku("qual o estoque de palmito?") is None
        mock.assert_not_called()


# ─────────────────────────── orquestrador (N0->N1) ───────────────────────────
def test_orquestrador_caminho_feliz():
    with patch.object(fp, "should_intercept_vinculacao",
                      return_value={"acao": "vincular", "nf": "6935", "po": "C2620094"}), \
         patch.object(fp, "executar_vinculacao_por_nf",
                      return_value={"ok": True, "status": "consolidado", "nf": "6935",
                                    "po": "C2620094", "resumo": {"cenario": "exact_1po"}}):
        r = fp.executar_vinculacao_fastpath("vincular pedido C2620094 na nota 6935",
                                            session_id="s", user_id=69)
    assert r["ok"] is True and "6935" in r["resposta"] and "C2620094" in r["resposta"]


def test_orquestrador_anomalia_cai_no_llm():
    with patch.object(fp, "should_intercept_vinculacao",
                      return_value={"acao": "vincular", "nf": "1", "po": "C1"}), \
         patch.object(fp, "executar_vinculacao_por_nf",
                      return_value={"ok": False, "anomalia": {"tipo": "status_nao_aprovado"}}):
        r = fp.executar_vinculacao_fastpath("vincular pedido C1 na nota 1",
                                            session_id="s", user_id=69)
    assert r["ok"] is False  # caller cai no gestor-recebimento (N2)


def test_orquestrador_sem_match_e_sem_haiku_retorna_none():
    with patch.object(fp, "should_intercept_vinculacao", return_value=None), \
         patch.object(fp, "parse_vinculacao_haiku", return_value=None):
        r = fp.executar_vinculacao_fastpath("bom dia", session_id="s", user_id=69)
    assert r is None  # nada a interceptar -> fluxo LLM normal


# ─── Multi-PO: "juntar/unir pedidos A/B criar conciliador e vincular na nota N"
# Frases REAIS da Gabriella (sessoes 09-11/06) que o N0 single-PO nao alcancava.

def test_juntar_pedidos_multi_po():
    from app.agente.sdk.vinculacao_fastpath import should_intercept_vinculacao
    r = should_intercept_vinculacao(
        "juntar os pedidos C2618286/C2618568/C2618501/C2619292 "
        "criar conciliador e vincular na nota 2993")
    assert r is not None and r["acao"] == "vincular"
    assert r["nf"] == "2993"
    assert r["po"] == ["C2618286", "C2618568", "C2618501", "C2619292"]


def test_unir_pedidos_multi_po():
    from app.agente.sdk.vinculacao_fastpath import should_intercept_vinculacao
    r = should_intercept_vinculacao(
        "Unir pedidos C2618286/C2618568 criar conciliador e vincular na nota 2993")
    assert r is not None and r["acao"] == "vincular"
    assert r["po"] == ["C2618286", "C2618568"]


def test_juntar_sem_vincular_nao_casa():
    from app.agente.sdk.vinculacao_fastpath import should_intercept_vinculacao
    assert should_intercept_vinculacao("juntar os pedidos C1/C2") is None


# ─── Contexto N2: anomalia diagnosticada NAO pode ser descartada ────────────

def test_montar_contexto_n2_inclui_diagnostico():
    from app.agente.sdk.vinculacao_fastpath import montar_contexto_n2
    vinc = {
        "ok": False,
        "anomalia": {
            "tipo": "status_nao_aprovado",
            "detalhe": "bloqueado",
            "validacao_id": 1539,
            "validacao": {"status": "bloqueado",
                          "divergencias": ["Nenhum PO com preco/data validos para 209000410"]},
        },
        "parsed": {"acao": "vincular", "po": "C2618524", "nf": "442228"},
    }
    ctx = montar_contexto_n2(vinc)
    assert "442228" in ctx and "C2618524" in ctx
    assert "1539" in ctx and "status_nao_aprovado" in ctx
    assert "209000410" in ctx
    # marcado como contexto de sistema (nao instrucao do usuario)
    assert ctx.startswith("\n\n<diagnostico_fastpath>")
    assert ctx.rstrip().endswith("</diagnostico_fastpath>")


def test_montar_contexto_n2_vazio_para_none():
    from app.agente.sdk.vinculacao_fastpath import montar_contexto_n2
    assert montar_contexto_n2(None) == ""
