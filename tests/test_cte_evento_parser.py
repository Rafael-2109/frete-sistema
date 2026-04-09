"""
Testes do parser generico de XML de CTe.

Cobre:
- Detect tipo (procEventoCTe, cteProc, invalido)
- Parse de evento de cancelamento (110111)
- Parse de CTe original
- Edge cases: XML invalido, namespace, encoding ISO-8859-1, BOM
"""

from app.utils.cte_evento_parser import (
    CteEventoParser,
    TP_EVENTO_CANCELAMENTO,
    CSTAT_EVENTO_HOMOLOGADO,
)


# ======================================================================
# Fixtures de XMLs (especificacao oficial SEFAZ MOC CT-e v3.00)
# ======================================================================


XML_PROC_EVENTO_CANCELAMENTO = """<?xml version="1.0" encoding="UTF-8"?>
<procEventoCTe xmlns="http://www.portalfiscal.inf.br/cte" versao="1.00">
  <eventoCTe xmlns="http://www.portalfiscal.inf.br/cte" versao="1.00">
    <infEvento Id="ID11011135250100000000000000000000000000000000000001">
      <cOrgao>35</cOrgao>
      <tpAmb>1</tpAmb>
      <CNPJ>61724241000119</CNPJ>
      <chCTe>35250100000000000000000000000000000000000000</chCTe>
      <dhEvento>2026-04-09T10:15:00-03:00</dhEvento>
      <tpEvento>110111</tpEvento>
      <nSeqEvento>1</nSeqEvento>
      <verEvento>1.00</verEvento>
      <detEvento versaoEvento="1.00">
        <evCancCTe>
          <descEvento>Cancelamento</descEvento>
          <nProt>135250000000001</nProt>
          <xJust>Erro no preenchimento das informacoes do destinatario</xJust>
        </evCancCTe>
      </detEvento>
    </infEvento>
  </eventoCTe>
  <retEventoCTe versao="1.00">
    <infEvento>
      <tpAmb>1</tpAmb>
      <verAplic>SP_NFE_PL009_V4</verAplic>
      <cOrgao>35</cOrgao>
      <cStat>135</cStat>
      <xMotivo>Evento registrado e vinculado ao CT-e</xMotivo>
      <chCTe>35250100000000000000000000000000000000000000</chCTe>
      <tpEvento>110111</tpEvento>
      <xEvento>Cancelamento</xEvento>
      <nSeqEvento>1</nSeqEvento>
      <dhRegEvento>2026-04-09T10:15:30-03:00</dhRegEvento>
      <nProt>135250000000002</nProt>
    </infEvento>
  </retEventoCTe>
</procEventoCTe>
"""


XML_PROC_EVENTO_NAO_HOMOLOGADO = """<?xml version="1.0" encoding="UTF-8"?>
<procEventoCTe xmlns="http://www.portalfiscal.inf.br/cte" versao="1.00">
  <eventoCTe xmlns="http://www.portalfiscal.inf.br/cte" versao="1.00">
    <infEvento Id="ID11011135250100000000000000000000000000000000000002">
      <cOrgao>35</cOrgao>
      <tpAmb>1</tpAmb>
      <CNPJ>61724241000119</CNPJ>
      <chCTe>35250100000000000000000000000000000000000001</chCTe>
      <dhEvento>2026-04-09T11:00:00-03:00</dhEvento>
      <tpEvento>110111</tpEvento>
      <nSeqEvento>1</nSeqEvento>
      <verEvento>1.00</verEvento>
      <detEvento versaoEvento="1.00">
        <evCancCTe>
          <descEvento>Cancelamento</descEvento>
          <nProt>135250000000001</nProt>
          <xJust>teste</xJust>
        </evCancCTe>
      </detEvento>
    </infEvento>
  </eventoCTe>
  <retEventoCTe versao="1.00">
    <infEvento>
      <tpAmb>1</tpAmb>
      <cOrgao>35</cOrgao>
      <cStat>490</cStat>
      <xMotivo>Rejeicao: evento ja processado</xMotivo>
      <chCTe>35250100000000000000000000000000000000000001</chCTe>
      <tpEvento>110111</tpEvento>
      <nSeqEvento>1</nSeqEvento>
    </infEvento>
  </retEventoCTe>
</procEventoCTe>
"""


XML_CTE_PROC = """<?xml version="1.0" encoding="UTF-8"?>
<cteProc xmlns="http://www.portalfiscal.inf.br/cte" versao="3.00">
  <CTe xmlns="http://www.portalfiscal.inf.br/cte">
    <infCte Id="CTe35250100000000000000000000000000000000000000" versao="3.00">
      <ide>
        <cUF>35</cUF>
        <cCT>00000001</cCT>
        <CFOP>5353</CFOP>
        <natOp>Prestacao de servico de transporte</natOp>
        <mod>57</mod>
        <serie>1</serie>
        <nCT>12345</nCT>
        <dhEmi>2026-04-09T08:00:00-03:00</dhEmi>
      </ide>
      <emit>
        <CNPJ>12345678000100</CNPJ>
        <IE>123456789</IE>
        <xNome>Transportadora Exemplo LTDA</xNome>
      </emit>
      <vPrest>
        <vTPrest>1500.00</vTPrest>
        <vRec>1500.00</vRec>
      </vPrest>
    </infCte>
  </CTe>
  <protCTe versao="3.00">
    <infProt>
      <tpAmb>1</tpAmb>
      <verAplic>SP_NFE_PL009_V4</verAplic>
      <chCTe>35250100000000000000000000000000000000000000</chCTe>
      <dhRecbto>2026-04-09T08:00:05-03:00</dhRecbto>
      <nProt>135250999999999</nProt>
      <cStat>100</cStat>
      <xMotivo>Autorizado o uso do CT-e</xMotivo>
    </infProt>
  </protCTe>
</cteProc>
"""


XML_INVALIDO = """<?xml version="1.0"?>
<foo>
  <bar>isto nao e um CTe</bar>
</foo>
"""


XML_QUEBRADO = "<< this is not xml >>"


CHAVE_VALIDA_1 = "35250100000000000000000000000000000000000000"
CHAVE_VALIDA_2 = "35250100000000000000000000000000000000000001"


# ======================================================================
# Testes de deteccao de tipo
# ======================================================================


class TestDetectarTipo:
    def setup_method(self):
        self.parser = CteEventoParser()

    def test_detecta_proc_evento_cte(self):
        assert self.parser.detectar_tipo(XML_PROC_EVENTO_CANCELAMENTO) == 'procEventoCTe'

    def test_detecta_cte_proc(self):
        assert self.parser.detectar_tipo(XML_CTE_PROC) == 'cteProc'

    def test_detecta_invalido_outra_tag(self):
        assert self.parser.detectar_tipo(XML_INVALIDO) == 'invalido'

    def test_detecta_invalido_xml_quebrado(self):
        assert self.parser.detectar_tipo(XML_QUEBRADO) == 'invalido'

    def test_detecta_a_partir_de_bytes(self):
        assert self.parser.detectar_tipo(XML_CTE_PROC.encode('utf-8')) == 'cteProc'

    def test_detecta_com_bom(self):
        xml_com_bom = '\ufeff' + XML_PROC_EVENTO_CANCELAMENTO
        assert self.parser.detectar_tipo(xml_com_bom) == 'procEventoCTe'

    def test_iso_8859_1(self):
        xml_iso = XML_PROC_EVENTO_CANCELAMENTO.replace(
            'encoding="UTF-8"', 'encoding="ISO-8859-1"'
        ).encode('iso-8859-1')
        assert self.parser.detectar_tipo(xml_iso) == 'procEventoCTe'


# ======================================================================
# Testes de parse_evento
# ======================================================================


class TestParseEvento:
    def setup_method(self):
        self.parser = CteEventoParser()

    def test_parse_cancelamento_homologado(self):
        info = self.parser.parse_evento(XML_PROC_EVENTO_CANCELAMENTO)
        assert info is not None
        assert info['tipo'] == 'procEventoCTe'
        assert info['chave'] == CHAVE_VALIDA_1
        assert info['tp_evento'] == TP_EVENTO_CANCELAMENTO
        assert info['cancelamento'] is True
        assert info['cstat'] == CSTAT_EVENTO_HOMOLOGADO
        assert info['protocolo'] == '135250000000002'  # nProt do retEventoCTe
        assert 'Erro no preenchimento' in info['justificativa']
        assert info['data_evento'] == '2026-04-09T10:15:00-03:00'
        assert info['n_seq_evento'] == '1'

    def test_parse_evento_nao_homologado_retorna_cancelamento_false(self):
        info = self.parser.parse_evento(XML_PROC_EVENTO_NAO_HOMOLOGADO)
        assert info is not None
        assert info['tp_evento'] == TP_EVENTO_CANCELAMENTO
        # cStat 490 != 135 (homologado) → cancelamento deve ser False
        assert info['cstat'] == '490'
        assert info['cancelamento'] is False

    def test_parse_evento_xml_invalido_retorna_none(self):
        info = self.parser.parse_evento(XML_INVALIDO)
        assert info is None

    def test_parse_evento_xml_quebrado_retorna_none(self):
        info = self.parser.parse_evento(XML_QUEBRADO)
        assert info is None

    def test_parse_evento_cte_proc_retorna_none(self):
        """Passar cteProc no parser de evento deve retornar None."""
        info = self.parser.parse_evento(XML_CTE_PROC)
        assert info is None


# ======================================================================
# Testes de parse_cte
# ======================================================================


class TestParseCte:
    def setup_method(self):
        self.parser = CteEventoParser()

    def test_parse_cte_completo(self):
        info = self.parser.parse_cte(XML_CTE_PROC)
        assert info is not None
        assert info['tipo'] == 'cteProc'
        assert info['chave'] == CHAVE_VALIDA_1
        assert info['cancelamento'] is False  # cteProc nunca traz cancelamento
        assert info['numero'] == '12345'
        assert info['serie'] == '1'
        assert info['modelo'] == '57'
        assert info['emitente_cnpj'] == '12345678000100'
        assert info['emitente_nome'] == 'Transportadora Exemplo LTDA'
        assert info['valor_total'] == '1500.00'
        assert info['protocolo'] == '135250999999999'

    def test_parse_cte_proc_evento_retorna_none(self):
        info = self.parser.parse_cte(XML_PROC_EVENTO_CANCELAMENTO)
        assert info is None

    def test_parse_cte_invalido_retorna_none(self):
        assert self.parser.parse_cte(XML_INVALIDO) is None
        assert self.parser.parse_cte(XML_QUEBRADO) is None


# ======================================================================
# Testes de parse() helper e extrair_chave_acesso
# ======================================================================


class TestParseHelper:
    def setup_method(self):
        self.parser = CteEventoParser()

    def test_parse_roteia_evento(self):
        info = self.parser.parse(XML_PROC_EVENTO_CANCELAMENTO)
        assert info is not None
        assert info['tipo'] == 'procEventoCTe'
        assert info['cancelamento'] is True

    def test_parse_roteia_cte(self):
        info = self.parser.parse(XML_CTE_PROC)
        assert info is not None
        assert info['tipo'] == 'cteProc'
        assert info['cancelamento'] is False

    def test_parse_invalido_retorna_none(self):
        assert self.parser.parse(XML_INVALIDO) is None

    def test_extrair_chave_de_evento(self):
        chave = self.parser.extrair_chave_acesso(XML_PROC_EVENTO_CANCELAMENTO)
        assert chave == CHAVE_VALIDA_1

    def test_extrair_chave_de_cte_proc(self):
        chave = self.parser.extrair_chave_acesso(XML_CTE_PROC)
        assert chave == CHAVE_VALIDA_1

    def test_extrair_chave_de_invalido_retorna_none(self):
        assert self.parser.extrair_chave_acesso(XML_INVALIDO) is None

    def test_extrair_chave_invalida_comprimento(self):
        """Chave com tamanho != 44 deve retornar None."""
        xml_chave_curta = XML_PROC_EVENTO_CANCELAMENTO.replace(
            '35250100000000000000000000000000000000000000',
            '123',
        )
        assert self.parser.extrair_chave_acesso(xml_chave_curta) is None


# ======================================================================
# Edge cases
# ======================================================================


class TestEdgeCases:
    def setup_method(self):
        self.parser = CteEventoParser()

    def test_xml_vazio(self):
        assert self.parser.detectar_tipo('') == 'invalido'
        assert self.parser.detectar_tipo(b'') == 'invalido'

    def test_xml_apenas_whitespace(self):
        assert self.parser.detectar_tipo('   \n  \t  ') == 'invalido'

    def test_namespace_diferente_ainda_detecta(self):
        """O parser deve ignorar namespace ao comparar tags."""
        xml_sem_ns = XML_PROC_EVENTO_CANCELAMENTO.replace(
            ' xmlns="http://www.portalfiscal.inf.br/cte"',
            '',
        )
        assert self.parser.detectar_tipo(xml_sem_ns) == 'procEventoCTe'
        info = self.parser.parse_evento(xml_sem_ns)
        assert info is not None
        assert info['chave'] == CHAVE_VALIDA_1
