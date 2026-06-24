"""
Testes do comparador do Validador de Titulos x Bancos.

Cobre os 3 cruzamentos:
1. titulos em 2+ bancos (com validacao de recompra no CP)
2. notas faturadas sem boleto
3. boletos sem nota faturada
+ boletos nao identificados (sem chave NF-PARC).
"""

import pytest

from app.financeiro.services.validador_titulos.comparador import comparar


def _boleto(nf_parc, banco, **extra):
    d = {"nf_parc": nf_parc, "banco": banco}
    d.update(extra)
    return d


def _fat(nf_parc, **extra):
    d = {"nf_parc": nf_parc}
    d.update(extra)
    return d


class TestDuplicados:
    """Comparativo 1: titulo em mais de um banco."""

    def test_titulo_em_dois_bancos_entra_como_duplicado(self):
        boletos = [_boleto("100-1", "SRM"), _boleto("100-1", "AGIS")]
        r = comparar(boletos, faturamento=[], cp_recompras=set())
        assert len(r.duplicados) == 1
        dup = r.duplicados[0]
        assert dup["nf_parc"] == "100-1"
        assert dup["bancos"] == ["AGIS", "SRM"]  # ordenado
        assert dup["qtd_bancos"] == 2

    def test_titulo_em_um_banco_nao_e_duplicado(self):
        boletos = [_boleto("100-1", "SRM"), _boleto("200-1", "AGIS")]
        r = comparar(boletos, faturamento=[], cp_recompras=set())
        assert r.duplicados == []

    def test_mesmo_titulo_mesmo_banco_nao_conta_dois_bancos(self):
        """Duas linhas do mesmo banco para o mesmo titulo = 1 banco, nao duplicado."""
        boletos = [_boleto("100-1", "SRM"), _boleto("100-1", "SRM")]
        r = comparar(boletos, faturamento=[], cp_recompras=set())
        assert r.duplicados == []

    def test_duplicado_com_recompra_no_cp_e_marcado_ok(self):
        boletos = [_boleto("100-1", "SRM"), _boleto("100-1", "AGIS")]
        r = comparar(boletos, faturamento=[], cp_recompras={"100-1"})
        assert r.duplicados[0]["tem_recompra"] is True

    def test_duplicado_sem_recompra_e_marcado_para_verificar(self):
        boletos = [_boleto("100-1", "SRM"), _boleto("100-1", "AGIS")]
        r = comparar(boletos, faturamento=[], cp_recompras={"999-1"})
        assert r.duplicados[0]["tem_recompra"] is False

    def test_titulo_em_tres_bancos(self):
        boletos = [
            _boleto("100-1", "SRM"),
            _boleto("100-1", "AGIS"),
            _boleto("100-1", "VORTX"),
        ]
        r = comparar(boletos, faturamento=[], cp_recompras=set())
        assert r.duplicados[0]["qtd_bancos"] == 3
        assert r.duplicados[0]["bancos"] == ["AGIS", "SRM", "VORTX"]


class TestFaturadoSemBoleto:
    """Comparativo 2: nota faturada sem boleto em nenhum banco."""

    def test_faturado_sem_boleto_entra_na_lista(self):
        boletos = [_boleto("100-1", "SRM")]
        faturamento = [_fat("100-1"), _fat("200-1", cliente="ACME")]
        r = comparar(boletos, faturamento, cp_recompras=set())
        assert len(r.faturado_sem_boleto) == 1
        assert r.faturado_sem_boleto[0]["nf_parc"] == "200-1"
        assert r.faturado_sem_boleto[0]["cliente"] == "ACME"

    def test_faturado_com_boleto_nao_entra(self):
        boletos = [_boleto("100-1", "SRM")]
        faturamento = [_fat("100-1")]
        r = comparar(boletos, faturamento, cp_recompras=set())
        assert r.faturado_sem_boleto == []


class TestBoletoSemNota:
    """Comparativo 3: boleto que nao bate com nenhuma nota faturada."""

    def test_boleto_sem_nota_entra_na_lista(self):
        boletos = [_boleto("100-1", "SRM"), _boleto("300-1", "AGIS")]
        faturamento = [_fat("100-1")]
        r = comparar(boletos, faturamento, cp_recompras=set())
        nfs = [b["nf_parc"] for b in r.boleto_sem_nota]
        assert nfs == ["300-1"]

    def test_boleto_com_nota_nao_entra(self):
        boletos = [_boleto("100-1", "SRM")]
        faturamento = [_fat("100-1")]
        r = comparar(boletos, faturamento, cp_recompras=set())
        assert r.boleto_sem_nota == []


class TestNaoIdentificados:
    """Boletos sem chave NF-PARC (dados sujos) nao podem casar — viram lista a parte."""

    def test_boleto_sem_nf_parc_vai_para_nao_identificados(self):
        boletos = [_boleto(None, "VORTX", original="147569.0"), _boleto("100-1", "SRM")]
        r = comparar(boletos, faturamento=[], cp_recompras=set())
        assert len(r.nao_identificados) == 1
        assert r.nao_identificados[0]["original"] == "147569.0"

    def test_boleto_sem_nf_parc_nao_entra_em_duplicados_nem_boleto_sem_nota(self):
        boletos = [_boleto(None, "VORTX"), _boleto(None, "AGIS")]
        r = comparar(boletos, faturamento=[], cp_recompras=set())
        assert r.duplicados == []
        assert r.boleto_sem_nota == []
        assert len(r.nao_identificados) == 2
