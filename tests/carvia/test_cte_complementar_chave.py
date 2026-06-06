"""Teste do fix I1 — chave de acesso do CTe complementar.

REVISAO_ARQUITETURA_2026 I1 (provado com dados de producao): COMP-026 e a
operacao pai 327 tinham a MESMA cte_chave_acesso (a do pai, CT-e 297), porque
get_chave_acesso() usava _get_tag_text('chCTe') generico, que num complementar
pega o <infCteComp>/<chCTe> (chave do PAI) antes do <protCTe>/<chCTe> (propria).
Resultado: o 2o complementar do mesmo pai colidia no dedup do import e era
descartado silenciosamente ("demonstra como inserido porem nao aparece").

O fix extrai a chave do PROPRIO documento (Id do <infCte>, com fallback no
<protCTe>). Teste de parser puro — sem DB.
"""
from app.carvia.services.parsers.cte_xml_parser_carvia import CTeXMLParserCarvia

# Chaves de 44 digitos (estrutura real; numeros distintos)
PARENT = '35260662312605000175570010000002971000002985'  # CT-e 297 (pai CAR-300-0)
OWN = '35260662312605000175570010000003021000003027'     # CT-e 302 (complementar)

XML_COMPLEMENTAR = f'''<?xml version="1.0" encoding="UTF-8"?>
<cteProc xmlns="http://www.portalfiscal.inf.br/cte" versao="3.00">
  <CTe>
    <infCte Id="CTe{OWN}" versao="3.00">
      <ide><tpCTe>1</tpCTe></ide>
      <infCteComp>
        <chCTe>{PARENT}</chCTe>
      </infCteComp>
    </infCte>
  </CTe>
  <protCTe versao="3.00">
    <infProt>
      <chCTe>{OWN}</chCTe>
      <cStat>100</cStat>
    </infProt>
  </protCTe>
</cteProc>'''

XML_NORMAL = f'''<?xml version="1.0" encoding="UTF-8"?>
<cteProc xmlns="http://www.portalfiscal.inf.br/cte" versao="3.00">
  <CTe>
    <infCte Id="CTe{OWN}" versao="3.00">
      <ide><tpCTe>0</tpCTe></ide>
    </infCte>
  </CTe>
  <protCTe versao="3.00">
    <infProt><chCTe>{OWN}</chCTe><cStat>100</cStat></infProt>
  </protCTe>
</cteProc>'''


def test_complementar_usa_chave_propria_nao_do_pai():
    parser = CTeXMLParserCarvia(XML_COMPLEMENTAR)
    chave = parser.get_chave_acesso()
    assert chave == OWN, f'esperava chave propria {OWN}, veio {chave}'
    assert chave != PARENT, 'NAO pode herdar a chave do CTe pai (infCteComp)'


def test_cte_normal_continua_retornando_chave_propria():
    # Sem <infCteComp> — garante que o fix nao regrediu o CTe comum.
    parser = CTeXMLParserCarvia(XML_NORMAL)
    assert parser.get_chave_acesso() == OWN
