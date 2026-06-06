"""
Regressao de timezone na projecao de estoque (BRT vs UTC).

Bug original: a cadeia de projeção usava `date.today()`, avaliado no fuso do
processo (UTC no Render, que NAO define TZ). As 21:30 BRT do dia 01
(= 00:30 UTC do dia 02), `date.today()` retornava o dia 02 e o filtro
`ProgramacaoProducao.data_programacao >= hoje` descartava a producao do dia 01.

Fix: trocar `date.today()` por `agora_utc_naive().date()` (horario de Brasilia
naive — convencao oficial do projeto, app/utils/timezone.py).

Estes testes sao unitarios puros (mocks) — nao tocam banco nem app context.
"""
from datetime import datetime, date
from unittest.mock import patch

from app.estoque.services.estoque_simples import ServicoEstoqueSimples


def test_projecao_considera_producao_do_dia_corrente_em_horario_noturno_brt():
    """
    As 21:30 BRT do dia 01 (= 00:30 UTC do dia 02), a projecao deve usar a data
    BRT (dia 01) como D0 e considerar a programacao de producao do dia 01.

    Antes do fix (date.today() em UTC), o corte virava dia 02 e a producao do
    dia 01 desaparecia da projecao.
    """
    # 21:30 BRT do dia 01 — em UTC ja seria 2026-06-02 00:30
    brt_noite_dia01 = datetime(2026, 6, 1, 21, 30, 0)

    with patch(
        "app.estoque.services.estoque_simples.agora_utc_naive",
        return_value=brt_noite_dia01,
    ), patch.object(
        ServicoEstoqueSimples, "_get_cache", return_value=None
    ), patch.object(
        ServicoEstoqueSimples, "_set_cache", return_value=None
    ), patch.object(
        ServicoEstoqueSimples, "calcular_estoque_atual", return_value=0.0
    ), patch.object(
        ServicoEstoqueSimples, "calcular_saidas_previstas", return_value={}
    ), patch.object(
        ServicoEstoqueSimples,
        "calcular_entradas_previstas",
        return_value={date(2026, 6, 1): 100.0},
    ):
        resultado = ServicoEstoqueSimples.calcular_projecao("TEST", dias=5)

    projecao = resultado["projecao"]

    # D0 deve ser o dia 01 (BRT), nao o dia 02 (UTC)
    assert projecao[0]["data"] == "2026-06-01", (
        f"D0 deveria ser 2026-06-01 (BRT), veio {projecao[0]['data']} "
        "— regressao de timezone (date.today() em UTC)"
    )

    # A producao programada do dia 01 deve aparecer como entrada em D0
    assert projecao[0]["entrada"] == 100.0, (
        "Producao do dia corrente (dia 01) sumiu da projecao "
        "— regressao de timezone"
    )


def test_projecao_independe_da_data_real_do_sistema():
    """
    Garante que a projecao usa o 'agora' injetado (mockavel) e NAO `date.today()`.
    Se o codigo voltasse a usar date.today(), o mock de agora_utc_naive nao teria
    efeito e o D0 seria a data real do sistema (este assert falharia).
    """
    agora_fixo = datetime(2026, 1, 15, 23, 59, 0)

    with patch(
        "app.estoque.services.estoque_simples.agora_utc_naive",
        return_value=agora_fixo,
    ), patch.object(
        ServicoEstoqueSimples, "_get_cache", return_value=None
    ), patch.object(
        ServicoEstoqueSimples, "_set_cache", return_value=None
    ), patch.object(
        ServicoEstoqueSimples, "calcular_estoque_atual", return_value=50.0
    ), patch.object(
        ServicoEstoqueSimples, "calcular_saidas_previstas", return_value={}
    ), patch.object(
        ServicoEstoqueSimples, "calcular_entradas_previstas", return_value={}
    ):
        resultado = ServicoEstoqueSimples.calcular_projecao("TEST", dias=3)

    assert resultado["projecao"][0]["data"] == "2026-01-15"
