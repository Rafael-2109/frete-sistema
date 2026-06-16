"""
Testes do parser de DANFE PDF para o layout gerado pelo Bling.

DANFEs do Bling tem 2 peculiaridades que quebravam o regex do parser
(NF 6586 GA MOTORS -> PABLO VASCONCELLOS LEAL ME, importada em 15/06/2026):

1. Endereco do emitente em ordem 'CEP - Cidade - UF'
   ("03.412-030 - São Paulo - SP"), invertida do esperado 'Cidade - UF - CEP'.
   get_uf_cidade_emitente() retornava (None, None) -> caia em LLM (Haiku).

2. Volumes impressos como 'N Volume(s)' ("6 Volume(s) 0,000 0,000"), com a
   linha de cabecalho ('Quantidade Especie ...') separada da linha de valores
   por uma linha intermediaria ('Marca Numeracao'). get_quantidade_volumes()
   retornava None (e nao escalonava LLM) -> volume perdido.

O numero da NF NAO entra aqui: ja sai correto end-to-end pela cross-validacao
chave x numero em get_todas_informacoes() (danfe_pdf_parser.py:2258).

Fixture: tests/carvia/fixtures/danfe_bling_pablo.txt (texto real extraido por
pdfplumber==0.11.9 / pdfminer.six==20251230 — mesmas versoes de local e Render).
"""

import os

from app.carvia.services.parsers.danfe_pdf_parser import DanfePDFParser

_FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'danfe_bling_pablo.txt')


def _parser_bling() -> DanfePDFParser:
    """Instancia o parser sobre o texto real da DANFE Bling, sem reabrir o PDF."""
    with open(_FIXTURE, encoding='utf-8') as fh:
        texto = fh.read()
    p = DanfePDFParser.__new__(DanfePDFParser)
    p.texto_completo = texto
    p.paginas = [texto]
    p.confianca = 0.0
    p._client = None
    p.pdf_path = None
    p.pdf_bytes = None
    return p


class TestDanfeBlingLayout:
    def test_uf_cidade_emitente_ordem_cep_cidade_uf(self):
        # Layout Bling: "03.412-030 - São Paulo - SP 1-Saída ..."
        uf, cidade = _parser_bling().get_uf_cidade_emitente()
        assert uf == 'SP'
        assert cidade == 'São Paulo'

    def test_quantidade_volumes_n_volumes(self):
        # Layout Bling: "6 Volume(s) 0,000 0,000"
        assert _parser_bling().get_quantidade_volumes() == 6

    def test_nao_regride_destinatario(self):
        # Garante que o emitente (acima) nao "rouba" cidade/uf do destinatario.
        uf, cidade = _parser_bling().get_uf_cidade_destinatario()
        assert uf == 'RS'
        assert cidade == 'Rio Grande'


class TestDanfeBlingItens:
    """Layout Bling: secao titulada 'Itens da nota fiscal' (nao 'Dados dos
    Produtos'), com codigo/descricao acima da linha-NCM e UN/valores colados.
    NF PABLO: 4 autopropelidos eletricos modelo AG11 (CARBONO/BRANCA/CINZA/CAMUFLADA)."""

    def test_extrai_quatro_itens(self):
        itens = _parser_bling().get_itens_produto()
        assert len(itens) == 4

    def test_codigos_dos_itens(self):
        codigos = [it['codigo_produto'] for it in _parser_bling().get_itens_produto()]
        assert codigos == ['133', '132', '131', '136']

    def test_modelo_ag11_na_descricao(self):
        itens = _parser_bling().get_itens_produto()
        assert all('AG11' in (it['descricao'] or '') for it in itens)
        cores = ' '.join(it['descricao'] for it in itens)
        for cor in ('CARBONO', 'BRANCA', 'CINZA', 'CAMUFLADA'):
            assert cor in cores

    def test_ncm_cfop_unidade(self):
        it = _parser_bling().get_itens_produto()[0]
        assert it['ncm'] == '87116000'
        assert it['cfop'] == '6102'
        assert it['unidade'] == 'PÇ'

    def test_quantidades_e_valores(self):
        itens = _parser_bling().get_itens_produto()
        assert [float(it['quantidade']) for it in itens] == [2.0, 2.0, 1.0, 1.0]
        assert all(float(it['valor_unitario']) == 1200.0 for it in itens)
        # Soma dos valores bate com o valor_total da NF (7.200,00) e qtde com volumes (6)
        assert sum(float(it['valor_total_item']) for it in itens) == 7200.0
        assert sum(float(it['quantidade']) for it in itens) == 6.0


class TestDanfeBlingVeiculos:
    """Autopropelido eletrico (NCM 8711) SEM chassi declarado: nao deve
    escalar LLM atras de chassi inexistente, mesmo com itens NCM 8711 lidos
    (que fariam _quantidade_esperada_veiculos retornar 6)."""

    def test_sem_chassi_retorna_vazio_sem_llm(self):
        p = _parser_bling()

        def _boom(*_args, **_kwargs):
            raise AssertionError(
                'LLM de veiculos NAO deve ser chamado: NF sem chassi declarado'
            )

        p._extrair_veiculos_llm = _boom
        assert p.get_veiculos_info() == []
