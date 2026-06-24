"""
Testes da extracao de recompras da aba CP-NACOM (Contas a Pagar).
"""

import pytest

from app.financeiro.services.validador_titulos.cp_nacom import extrair_recompras


def _cabecalho():
    return ["Vencimento", "EMISSAO", "F. PAGTO", "Fornecedor", "Titulo", "Parc",
            "DESPESA FINANCEIRA", "VALOR"]


class TestExtrairRecompras:

    def test_extrai_chave_nf_parc(self):
        linhas = [_cabecalho(),
                  [45231.0, "", "BOLETO", "ACME", 148466.0, 1.0, "FRETE", 550.0]]
        recompras = extrair_recompras(linhas)
        assert recompras == {"148466-1"}

    def test_varias_linhas(self):
        linhas = [_cabecalho(),
                  [45231.0, "", "BOLETO", "ACME", 148466.0, 1.0, "X", 100.0],
                  [45231.0, "", "BOLETO", "BETA", 148535.0, 2.0, "Y", 200.0]]
        assert extrair_recompras(linhas) == {"148466-1", "148535-2"}

    def test_ignora_linha_sem_titulo(self):
        linhas = [_cabecalho(),
                  [45231.0, "", "BOLETO", "ACME", "", "", "X", 100.0],
                  [45231.0, "", "BOLETO", "BETA", 148535.0, 2.0, "Y", 200.0]]
        assert extrair_recompras(linhas) == {"148535-2"}

    def test_titulo_e_parc_como_string(self):
        linhas = [_cabecalho(),
                  ["45231", "", "BOLETO", "ACME", "148466", "1", "X", "100"]]
        assert extrair_recompras(linhas) == {"148466-1"}

    def test_colunas_nao_encontradas_levanta_erro(self):
        linhas = [["A", "B", "C"], ["1", "2", "3"]]
        with pytest.raises(ValueError):
            extrair_recompras(linhas)
