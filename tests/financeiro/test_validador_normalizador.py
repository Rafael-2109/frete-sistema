"""
Testes para o normalizador de chave NF-PARC do Validador de Titulos x Bancos.

A chave NF-PARC = "<numero da NF>-<parcela sem zeros a esquerda>".
Casos reais extraidos do gabarito da planilha W:\\VALIDADOR TITULOS BANCOS.xlsb
(colunas auxiliares NF-PARC ja calculadas a mao pelo operador).
"""

import pytest

from app.financeiro.services.validador_titulos.normalizador import (
    montar_nf_parc,
    montar_nf_parc_partes,
)


class TestMontarNfParc:
    """Conversao do identificador cru de cada banco para a chave NF-PARC."""

    # --- GRAFENO / VORTX: formato NF/PPP (barra, parcela com zeros) ---
    def test_grafeno_barra(self):
        assert montar_nf_parc("146299/003") == "146299-3"

    def test_vortx_barra(self):
        assert montar_nf_parc("148298/002") == "148298-2"

    # --- SRM: formato NF-PPP (hifen, parcela com zeros) ---
    def test_srm_hifen(self):
        assert montar_nf_parc("148466-001") == "148466-1"

    def test_srm_parcela_dois(self):
        assert montar_nf_parc("148535-002") == "148535-2"

    # --- AGIS: barra com parcela sem zeros ---
    def test_agis_barra_parcela_simples(self):
        assert montar_nf_parc("146826/5") == "146826-5"

    # --- AGIS / VORTX: mesmo banco usa hifen as vezes ---
    def test_agis_hifen(self):
        assert montar_nf_parc("148576-2") == "148576-2"

    def test_vortx_hifen(self):
        assert montar_nf_parc("147443-003") == "147443-3"

    # --- VORTX traz NFs com zeros a esquerda (00NNN-00P) ---
    def test_nf_com_zeros_a_esquerda_preserva_zeros(self):
        """Preserva zeros da NF: 00106 nao deve casar falsamente com 106.
        Separa pelo ultimo '-' (rpartition), entao 00106-003 -> 00106-3."""
        assert montar_nf_parc("00106-003") == "00106-3"
        assert montar_nf_parc("00103-002") == "00103-2"

    # --- Robustez: separa pelo ULTIMO separador (NF com hifen interno) ---
    def test_separa_pelo_ultimo_hifen(self):
        assert montar_nf_parc("00103--2") == "00103--2"

    # --- Robustez: espacos ao redor ---
    def test_espacos_sao_ignorados(self):
        assert montar_nf_parc("  146299/003  ") == "146299-3"

    # --- Entradas invalidas / sinalizacao ---
    def test_none_retorna_none(self):
        assert montar_nf_parc(None) is None

    def test_vazio_retorna_none(self):
        assert montar_nf_parc("") is None
        assert montar_nf_parc("   ") is None

    def test_sem_separador_retorna_none(self):
        """Float puro sem separador (ex: 147569.0) nao da para derivar parcela."""
        assert montar_nf_parc("147569.0") is None

    def test_parcela_nao_numerica_retorna_none(self):
        assert montar_nf_parc("146299/abc") is None

    def test_nf_vazia_retorna_none(self):
        assert montar_nf_parc("/3") is None


class TestMontarNfParcPartes:
    """NF e parcela em colunas separadas (faturamento e CP-NACOM)."""

    def test_strings_simples(self):
        assert montar_nf_parc_partes("148990", "1") == "148990-1"

    def test_parcela_float(self):
        assert montar_nf_parc_partes("148990", 1.0) == "148990-1"

    def test_nf_e_parcela_float_do_excel(self):
        """No CP-NACOM, Titulo e Parc vem como float (2023.0, 10.0)."""
        assert montar_nf_parc_partes(2023.0, 10.0) == "2023-10"

    def test_preserva_zeros_a_esquerda_da_nf(self):
        assert montar_nf_parc_partes("00106", "3") == "00106-3"

    def test_espacos_sao_ignorados(self):
        assert montar_nf_parc_partes(" 148990 ", " 2 ") == "148990-2"

    def test_nf_vazia_retorna_none(self):
        assert montar_nf_parc_partes(None, "1") is None
        assert montar_nf_parc_partes("", "1") is None

    def test_parcela_vazia_retorna_none(self):
        assert montar_nf_parc_partes("148990", None) is None
        assert montar_nf_parc_partes("148990", "") is None


class TestCaracteresDeControle:
    """Bancos as vezes trazem caracteres invisiveis (NUL) grudados no numero.
    A chave precisa sair limpa (senao quebra o Excel e nao casa entre fontes)."""

    def test_nul_no_identificador_combinado(self):
        assert montar_nf_parc("\x00\x00147768/2") == "147768-2"

    def test_nul_no_meio_e_fim(self):
        assert montar_nf_parc("147768\x00-2\x00") == "147768-2"

    def test_nul_em_partes_separadas(self):
        assert montar_nf_parc_partes("\x00147768", "2\x00") == "147768-2"

    def test_outros_controles(self):
        assert montar_nf_parc("\t148990-1\r") == "148990-1"
