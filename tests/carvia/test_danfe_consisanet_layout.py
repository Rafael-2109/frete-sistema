"""
Testes do parser de DANFE PDF para o layout gerado pelo ERP Consisanet (Alisul SC).

Regressao real — NF 986 (carvia_nfs.id=598, importada 29/06/2026). Antes dos fixes
o parser retornava numero_nf=None, valor_total=1.00 e 0 itens. Tres bugs do layout
Consisanet (IMP-2026-06-29-001):

1. get_numero_nf(): prefixo "Num." nao reconhecido — `N[°ºo.]` nao casa o `u` de
   "Num. 000.000.986". Fix: `N(?:[°ºo.]|UM\\.?)`.

2. get_valor_total(): a Strategy 2 (tabular) pegava o PRIMEIRO "VALOR TOTAL DA NOTA"
   (canhoto), cuja proxima linha e a serie ("Serie 1") -> retornava 1.0. Fix: iterar
   TODAS as ocorrencias e pular a do canhoto (proxima linha contem "RIE" de "Serie").

3. _parsear_linha_produto(): CFOP e UNIDADE colados sem espaco ("6403UNIDADE") —
   `\\s+(\\w{1,5})` exigia espaco e o limite {1,5} truncava 'UNIDADE'. Fix: `\\s*(\\w+)`
   (`\\w`, nao `[A-Za-z]`, preserva unidades com digito/acento como M2/M3/PÇ).

Fixture sintetico (inline): reproduz os 3 sintomas do layout Consisanet. A linha de
produto e a registrada no log de falha da sessao de origem.
"""

from app.carvia.services.parsers.danfe_pdf_parser import DanfePDFParser

# Layout Consisanet: canhoto com "VALOR TOTAL DA NOTA" seguido de "Serie 1" (bug 2),
# numero com prefixo "Num." (bug 1) e linha de produto com CFOP+UNIDADE colados (bug 3).
_TEXTO_CONSISANET = (
    "RECEBEMOS DE NACOM GOYA LTDA OS PRODUTOS CONSTANTES DA NOTA FISCAL INDICADA AO LADO\n"
    "NF-e VALOR TOTAL DA NOTA\n"
    "Serie 1\n"
    "DATA DE RECEBIMENTO IDENTIFICACAO E ASSINATURA DO RECEBEDOR\n"
    "DANFE\n"
    "Documento Auxiliar da Nota Fiscal Eletronica\n"
    "0 - ENTRADA\n"
    "1 - SAIDA\n"
    "Num. 000.000.986\n"
    "NATUREZA DA OPERACAO\n"
    "VENDA DE MERCADORIA ADQUIRIDA\n"
    "DADOS DOS PRODUTOS / SERVICOS\n"
    "COD PRODUTO DESCRICAO DO PRODUTO NCM/SH CST CFOP UN QTD V.UNIT V.DESC V.TOTAL\n"
    "412 SCOOTER/BICICLETA ELETRICA,MOD. 87116000 110 6403UNIDADE 10,000 1.029,600000 10.296,00\n"
    "DADOS ADICIONAIS\n"
    "INFORMACOES COMPLEMENTARES\n"
    "CALCULO DO IMPOSTO\n"
    "BASE DE CALCULO DO ICMS VALOR DO ICMS VALOR TOTAL DOS PRODUTOS VALOR TOTAL DA NOTA\n"
    "0,00 0,00 10.296,00 16.473,63\n"
)


def _parser_consisanet() -> DanfePDFParser:
    """Instancia o parser sobre o texto Consisanet, sem reabrir um PDF."""
    p = DanfePDFParser.__new__(DanfePDFParser)
    p.texto_completo = _TEXTO_CONSISANET
    p.paginas = [_TEXTO_CONSISANET]
    p.confianca = 0.0
    p._client = None
    p.pdf_path = None
    p.pdf_bytes = None
    return p


class TestDanfeConsisanetLayout:
    def test_numero_nf_prefixo_num(self):
        # Bug 1: "Num. 000.000.986" -> '986' (antes: None)
        assert _parser_consisanet().get_numero_nf() == '986'

    def test_valor_total_ignora_canhoto(self):
        # Bug 2: nao pegar o canhoto (serie 1); pegar o corpo (16.473,63) (antes: 1.0)
        assert _parser_consisanet().get_valor_total() == 16473.63

    def test_extrai_o_item_com_cfop_unidade_colados(self):
        # Bug 3: "6403UNIDADE" colado -> 1 item parseado (antes: 0 itens)
        itens = _parser_consisanet().get_itens_produto()
        assert len(itens) == 1
        it = itens[0]
        assert it['ncm'] == '87116000'
        assert it['cfop'] == '6403'
        assert it['unidade'] == 'UNIDADE'


class TestDanfeWithCfopRetrocompat:
    """Garante que o fix do bug 3 (`\\s*(\\w+)`) nao regride o layout normal
    'NCM CST CFOP UN QTD V.UNIT V.TOTAL' com espaco entre CFOP e unidade, NEM
    unidades com digito/acento (M2/M3/PÇ) que um `[A-Za-z]+` descartaria em
    silencio — regressao pega na revisao 4-maos 2026-06-29."""

    def _parse(self, ncm_line: str):
        p = DanfePDFParser.__new__(DanfePDFParser)
        p.texto_completo = ''
        p.paginas = []
        p.confianca = 0.0
        p._client = None
        p.pdf_path = None
        p.pdf_bytes = None
        return p._parsear_linha_produto(ncm_line)

    def test_cfop_e_unidade_separados_por_espaco(self):
        # Layout com CFOP e UN separados por espaco (caso classico)
        it = self._parse('JET MOTO CHEFE 87116000 460 5405 UN 3,00 7.220,0000 0,00 21.660,00')
        assert it is not None
        assert it['ncm'] == '87116000'
        assert it['cfop'] == '5405'
        assert it['unidade'] == 'UN'

    def test_unidade_com_digito_m2_nao_e_descartada(self):
        # Regressao 2026-06-29: `[A-Za-z]+` parava na 1a letra e perdia 'M2' (metro
        # quadrado) -> item descartado em silencio. `\\w+` casa o digito.
        it = self._parse('PISO CERAMICO 87116000 460 5405 M2 3,00 100,0000 0,00 300,00')
        assert it is not None
        assert it['cfop'] == '5405'
        assert it['unidade'] == 'M2'

    def test_unidade_acentuada_pc_nao_e_descartada(self):
        # Regressao 2026-06-29: `[A-Za-z]+` nao casa 'Ç' (acento) e perdia 'PÇ'
        # (peca — unidade BR comum, plausivel p/ pecas de moto). `\\w` casa 'Ç'.
        it = self._parse('PECA REPOSICAO MOTO 87116000 460 5405 PÇ 2,00 40,0000 0,00 80,00')
        assert it is not None
        assert it['cfop'] == '5405'
        assert it['unidade'] == 'PÇ'
