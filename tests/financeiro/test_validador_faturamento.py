"""
Testes da fonte de faturamento (contas_a_receber) do Validador de Titulos x Bancos.

Cobre a transformacao pura registro -> dict com chave NF-PARC.
A query ao banco e testada em integracao (requer app context).
"""

from types import SimpleNamespace

from app.financeiro.services.validador_titulos.faturamento import montar_faturamento


def _registro(titulo_nf, parcela, **extra):
    base = dict(
        titulo_nf=titulo_nf, parcela=parcela, empresa=3, cnpj="00.000/0001-00",
        raz_social="ACME LTDA", uf_cliente="SP", vencimento=None,
        valor_original=100.0, tipo_titulo="AGIS", parcela_paga=False,
    )
    base.update(extra)
    return SimpleNamespace(**base)


class TestMontarFaturamento:

    def test_monta_nf_parc(self):
        regs = [_registro("148990", "1")]
        fat = montar_faturamento(regs)
        assert fat[0]["nf_parc"] == "148990-1"

    def test_inclui_dados_do_cliente(self):
        regs = [_registro("148990", "1", raz_social="BETA SA", cnpj="11.111/0001-11")]
        f = montar_faturamento(regs)[0]
        assert f["cliente"] == "BETA SA"
        assert f["cnpj"] == "11.111/0001-11"

    def test_inclui_valor_e_tipo(self):
        regs = [_registro("148990", "1", valor_original=250.5, tipo_titulo="SRM")]
        f = montar_faturamento(regs)[0]
        assert f["valor"] == 250.5
        assert f["tipo_titulo"] == "SRM"

    def test_varios_registros(self):
        regs = [_registro("100", "1"), _registro("200", "2")]
        fat = montar_faturamento(regs)
        assert [f["nf_parc"] for f in fat] == ["100-1", "200-2"]
