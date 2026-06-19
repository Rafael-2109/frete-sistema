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


def _parser_fixture(nome: str) -> DanfePDFParser:
    """Instancia o parser sobre o texto real de uma fixture, sem reabrir o PDF."""
    with open(os.path.join(os.path.dirname(__file__), 'fixtures', nome), encoding='utf-8') as fh:
        texto = fh.read()
    p = DanfePDFParser.__new__(DanfePDFParser)
    p.texto_completo = texto
    p.paginas = [texto]
    p.confianca = 0.0
    p._client = None
    p.pdf_path = None
    p.pdf_bytes = None
    return p


class TestDanfeBling468ItensMistos:
    """Regressao real (NF 468 DRUMER): a NF tem 4 itens de 3 NCMs distintos —
    1 brinquedo (TOMATE UFO-MN02, NCM 9503), 2 autopropelidos AG11 (8711) e
    1 lote de capacetes (6506). A versao anterior ancorava no codigo numerico
    e so capturava os 2 AG11 (codigo 5042/5043); o TOMATE e o CAPACETE — sem
    codigo "NNN -" proprio — sumiam (capacete era engolido na descricao do AG11)."""

    def _itens(self):
        return _parser_fixture('danfe_bling_drumer_468.txt').get_itens_produto()

    def test_extrai_os_quatro_itens(self):
        assert len(self._itens()) == 4

    def test_ncms_na_ordem(self):
        ncms = [it['ncm'] for it in self._itens()]
        assert ncms == ['95030097', '87116000', '87116000', '65061090']

    def test_quantidades(self):
        assert [float(it['quantidade']) for it in self._itens()] == [3.0, 1.0, 1.0, 5.0]

    def test_soma_valor_total_bate_com_a_nf(self):
        # Cross-check: soma dos itens == valor total da NF (R$ 3.950,00).
        soma = sum(float(it['valor_total_item']) for it in self._itens())
        assert soma == 3950.0

    def test_itens_nao_moto_preservam_ncm_e_descricao(self):
        itens = self._itens()
        descs = ' | '.join(it['descricao'] for it in itens)
        assert ('TOMATE' in descs) or ('UFO' in descs)
        assert 'CAPACETE' in descs
        ncms = {it['ncm'] for it in itens}
        assert '95030097' in ncms   # brinquedo nao virou 8711
        assert '65061090' in ncms   # capacete nao foi engolido no AG11

    def test_codigo_dos_ag11_preservado(self):
        codigos = [it['codigo_produto'] for it in self._itens()]
        # itens com codigo "NNN -" mantem o codigo; itens inline ficam sem.
        assert codigos == [None, '5042', '5043', None]


class TestGateChassiNacional:
    """NF HORA (Mainô) "BIG TRI 1000W XL2025107152 ...": o chassi nacional NAO e
    VIN-17. O gate `_secao_tem_indicio_chassi` so aceitava CHASSI/VIN-17 e
    bloqueava a extracao (NFs voltavam "sem veiculo"). O 3o sinal (serie
    alfanumerica) destrava sem reativar o LLM para autopropelido sem chassi."""

    def test_secao_big_tri_tem_indicio_de_chassi(self):
        p = _parser_fixture('danfe_maino_bigtri_38752.txt')
        sec = p._extrair_texto_dados_adicionais()
        assert p._secao_tem_indicio_chassi(sec) is True

    def test_gate_nao_bloqueia_extracao_de_moto_nacional(self):
        p = _parser_fixture('danfe_maino_bigtri_38752.txt')
        chamadas = {'n': 0}

        def _fake_llm(*_args, **_kwargs):
            chamadas['n'] += 1
            return [
                {'chassi': 'XL2025107152', 'modelo': 'BIG TRI 1000W', 'cor': 'CINZA'},
                {'chassi': 'XL2025107153', 'modelo': 'BIG TRI 1000W', 'cor': 'CINZA'},
                {'chassi': 'XL2025085001', 'modelo': 'BIG TRI 1000W', 'cor': 'PRETO'},
                {'chassi': 'XL2025085002', 'modelo': 'BIG TRI 1000W', 'cor': 'PRETO'},
            ]

        p._extrair_veiculos_llm = _fake_llm
        veiculos = p.get_veiculos_info()
        assert chamadas['n'] >= 1          # gate NAO bloqueou (antes: 0 chamadas)
        assert len(veiculos) == 4

    def test_numero_puro_nao_e_indicio(self):
        # id de nota na URL Bling ("26023316088") nao deve disparar o gate.
        p = DanfePDFParser.__new__(DanfePDFParser)
        assert p._secao_tem_indicio_chassi(
            'Total de tributos R$ 1.877,71 idNota1=26023316088 fechaPopup'
        ) is False
        assert p._secao_tem_indicio_chassi(
            'Inf. Contribuinte: BIG TRI 1000W XL2025107152 HRD CINZA'
        ) is True


class TestDanfeBlingPrimeiroItemSemCodigo:
    """1o item SEM código numérico cuja descrição vem em linhas ACIMA da
    linha-NCM (não inline na própria linha-NCM): a descrição NÃO pode ser
    perdida — sem ela o item não é reconhecido como moto (subcontagem)."""

    def _parser(self):
        texto = (
            "Itens da nota fiscal\n"
            "Codigo Descricao do produto/servico NCM/SH CST CFOP UN Qtde\n"
            "un total ICMS\n"
            "MOTO ELETRICA SCOOTER\n"
            "MODELO ZX9 PRETO\n"
            "87116000 200 6.102PÇ 1,00 5.000,00 5.000,005.000,00\n"
            "5042 - AUTOPROPELIDO AG11\n"
            "COM MOTOR 87116000 200 6.102PÇ 1,00 1.200,00 1.200,001.200,00\n"
            "Calculo do ISSQN\n"
        )
        p = DanfePDFParser.__new__(DanfePDFParser)
        p.texto_completo = texto
        p.paginas = [texto]
        p.confianca = 0.0
        p._client = None
        p.pdf_path = None
        p.pdf_bytes = None
        return p

    def test_descricao_do_primeiro_item_nao_e_perdida(self):
        itens = self._parser().get_itens_produto()
        assert len(itens) == 2
        assert 'SCOOTER' in itens[0]['descricao']
        assert 'ZX9' in itens[0]['descricao']
        # cabeçalho ("un total ICMS", "Codigo Descricao... NCM/SH") fora da descrição
        assert 'ICMS' not in itens[0]['descricao']
        assert 'NCM' not in itens[0]['descricao'].upper()
