"""
Testes do fast-path deterministico do baseline de conciliacao (FASE 1 do plano
2026-06-06-reducao-custo-agente-fast-path).

ZERO-DB: detector (regex + guards) e formatadores de tabela markdown sao funcoes
puras. A execucao real (Odoo + DB) e validada por spot-check, nao por pytest
(R-EXEC-1: prova deterministica, nunca LLM eval; execucao com I/O = spot-check).

Principio (R-EXEC-6): o fast-path so intercepta o CAMINHO TRIVIAL ("atualizar
baseline" curto, sem data/variacao). Qualquer ambiguidade cai no LLM. Falso
NEGATIVO (deixa de economizar) e aceitavel; falso POSITIVO (intercepta algo que
precisa de LLM) e o perigo — por isso os guards sao conservadores.
"""
import pytest

from app.agente.sdk.baseline_fastpath import (
    should_intercept_baseline,
    format_tabela_mes_journal,
    format_tabela_conciliacoes,
    montar_resposta_baseline,
)


# ─────────────────────────────────────────── Detector: intercepta (trivial)
@pytest.mark.parametrize("msg", [
    "atualizar baseline",
    "Atualizar Baseline",
    "  atualizar baseline  ",
    "atualizar o baseline",
    "atualiza baseline",
    "gerar baseline",
    "gera baseline",
    "rodar baseline",
    "atualizar baseline hoje",
])
def test_intercepta_pedido_trivial_de_baseline(msg):
    assert should_intercept_baseline(msg) is True


# ─────────────────────────────────────────── Detector: NAO intercepta (LLM)
@pytest.mark.parametrize("msg", [
    "atualizar baseline do dia 08/05",        # data passada (digito + / + dia + >4)
    "atualizar baseline de ontem",            # token de tempo
    "gerar baseline com formato novo",        # variacao de formato
    "atualizar baseline da carvia",           # outro dominio (skill gerindo-carvia)
    "atualizar baseline na ordem dos meses",  # variacao de ordenacao (>4)
    "atualizar baseline do mes passado",      # mes/passado
    "foto das conciliacoes",                  # sem 'baseline'
    "qual o baseline?",                       # sem verbo de acao
    "o sistema atualiza o baseline sozinho?", # pergunta diagnostica (>4)
    "baseline",                               # 1 palavra, sem verbo
    "atualizar baseline 17/04",               # data explicita
    "",                                       # vazio
    "   ",                                    # whitespace
    None,                                     # None defensivo
])
def test_nao_intercepta_ambiguo_ou_variacao(msg):
    assert should_intercept_baseline(msg) is False


# ─────────────────────────────────────────── Formatador Tabela 1 (Mes x Journal)
def test_format_tabela_mes_journal_inclui_journals_e_total():
    agg = {
        ("04/2026", "SICOOB"): {"linhas": 200, "pgtos": 150, "recebs": 50,
                                 "vl_deb": -1000.0, "vl_cred": 500.0},
        ("04/2026", "BRADESCO"): {"linhas": 100, "pgtos": 80, "recebs": 20,
                                   "vl_deb": -800.0, "vl_cred": 200.0},
    }
    md = format_tabela_mes_journal(agg)
    assert "SICOOB" in md
    assert "BRADESCO" in md
    assert "Mes" in md and "Journal" in md  # header
    assert "TOTAL" in md
    assert "300" in md  # total de linhas = 200 + 100


def test_format_tabela_mes_journal_vazio_nao_quebra():
    md = format_tabela_mes_journal({})
    assert isinstance(md, str)
    assert "TOTAL" in md  # total zero, mas estrutura presente


# ─────────────────────────────────────────── Formatador conciliacoes (D-1 / D-0)
def test_format_tabela_conciliacoes_ordena_desc_e_soma_total():
    d = {
        "Marcus Lima": {"linhas": 80, "pgtos": 60, "recebs": 20,
                        "vl_deb": -100.0, "vl_cred": 50.0},
        "Joao Silva": {"linhas": 30, "pgtos": 25, "recebs": 5,
                       "vl_deb": -50.0, "vl_cred": 10.0},
    }
    md = format_tabela_conciliacoes(d, "16/04/2026")
    assert md.index("Marcus Lima") < md.index("Joao Silva")  # 80 antes de 30
    assert "TOTAL" in md
    assert "110" in md  # 80 + 30


def test_format_tabela_conciliacoes_vazio_mostra_mensagem_explicita():
    md = format_tabela_conciliacoes({}, "16/04/2026")
    assert "16/04/2026" in md
    assert "enhuma" in md  # "Nenhuma conciliacao..."


# ─────────────────────────────────────────── Montagem da resposta (entrega I7)
def test_montar_resposta_inclui_link_total_e_tres_tabelas():
    agg = {("04/2026", "SICOOB"): {"linhas": 10, "pgtos": 7, "recebs": 3,
                                    "vl_deb": -1.0, "vl_cred": 1.0}}
    d1 = {"Marcus": {"linhas": 5, "pgtos": 4, "recebs": 1,
                     "vl_deb": -1.0, "vl_cred": 0.0}}
    d0 = {}
    resp = montar_resposta_baseline(
        total=10, url="https://x/file.xlsx", data_ref_label="06/06/2026",
        agg=agg, d1=d1, d0=d0, d1_label="05/06/2026", d0_label="06/06/2026",
    )
    assert "https://x/file.xlsx" in resp        # link (I7)
    assert "10" in resp                          # total pendentes
    assert "SICOOB" in resp                      # Tabela 1 (Mes x Journal)
    assert "Marcus" in resp                      # Tabela D-1
    assert "Nenhuma conciliacao registrada em 06/06/2026" in resp  # D-0 vazio


def test_montar_resposta_sem_link_omite_secao_de_download():
    # Guard de entrega (P7 #787): se o arquivo falhou, NAO inventar link.
    resp = montar_resposta_baseline(
        total=10, url=None, data_ref_label="06/06/2026",
        agg={}, d1={}, d0={}, d1_label="05/06/2026", d0_label="06/06/2026",
    )
    assert "http" not in resp  # nenhum link forjado
    assert "download" not in resp.lower() or "indispon" in resp.lower()
