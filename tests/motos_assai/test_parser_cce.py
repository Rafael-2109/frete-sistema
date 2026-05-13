"""Testes parser CCe deterministico.

Cobertura por layout/variante (texto real extraido via pdfplumber dos PDFs
1729/1737/1757/1772/1779 — formato Q.P.A. — e 1579/36673/36928 — formato
MOTOCHEFE/ENDERECO).

Mocka pdfplumber.open para testar regex sem precisar dos PDFs binarios.
Testes do fallback LLM nao incluidos — exigem ANTHROPIC_API_KEY.
"""
from unittest.mock import patch, MagicMock

import pytest

from app.motos_assai.services.parsers.cce_pdf_extractor import (
    extrair_cce,
    CceParseError,
    CONFIANCA_LIMIAR,
    FORMATO_QPA,
    FORMATO_MOTOCHEFE,
    FORMATO_DESCONHECIDO,
    TIPO_CHASSI,
    TIPO_DUPLICATAS,
    TIPO_ENDERECO,
)


# =============================================================================
# Texto bruto dos PDFs reais (extraido via pdfplumber em 2026-05-13)
# =============================================================================

TEXTO_NF_1729 = """RELATÓRIO DE CARTA DE CORREÇÃO ELETRÔNICA
EMITENTE
RAZÃO SOCIAL CNPJ INSCRIÇÃO ESTADUAL
Q.p.a Distribuicao Ltda 53780554000115 623319027116
NOTA FISCAL ELETRÔNICA
SÉRIE NÚMERO DA NOTA FISCAL ELETRÔNICA CHAVE DE ACESSO
001 001729 3526 0453 7805 5400 0115 5500 1000 0017 2916 4454 2738
CARTA DE CORREÇÃO ELETRÔNICA
ÓRGÃO TIPO DE AMBIENTE DATA E HORA DO REGISTRO DO EVENTO
35 SAO PAULO 1 - Ambiente de Produção 30/04/26 às 09:11:05
EVENTO DESCRIÇÃO DO EVENTO SEQUENCIA DO EVENTO VERSÃO DO EVENTO
110110 CARTA DE CORREÇÃO ELETRÔNICA 1 1.00
CARTA DE CORREÇÃO ELETRÔNICA STATUS PROTOCOLO
35260453780554000115550010000017291644542738-CCe1-ProcEventoNFe.xml Status da Carta 135261639015279
DESTINATÁRIO / REMETENTE
NOME / RAZÃO SOCIAL CNPJ / CPF INSCRIÇÃO ESTADUAL
SENDAS DISTRIBUIDORA S/A 06057223023899 140481482118
ENDEREÇO BAIRRO
AVENIDA MORVAN DIAS DE FIGUEIREDO 3231 VILA GUILHERME
MUNICÍPIO ESTADO CEP TELEFONE
SAO PAULO SP 2063000 (11) 3411-5000
CORREÇÃO
CORREÇÃO DE CHASSI
SAINDO: DOT LA2025SA110004195 BRANCO
ENTRANDO: DOT LA2025SA110004319 BRANCO
CONDIÇÕES DE USO
"""

TEXTO_NF_1737 = """RELATÓRIO DE CARTA DE CORREÇÃO ELETRÔNICA
EMITENTE
RAZÃO SOCIAL CNPJ INSCRIÇÃO ESTADUAL
Q.p.a Distribuicao Ltda 53780554000115 623319027116
NOTA FISCAL ELETRÔNICA
SÉRIE NÚMERO DA NOTA FISCAL ELETRÔNICA CHAVE DE ACESSO
001 001737 3526 0453 7805 5400 0115 5500 1000 0017 3711 8600 9402
CARTA DE CORREÇÃO ELETRÔNICA
ÓRGÃO TIPO DE AMBIENTE DATA E HORA DO REGISTRO DO EVENTO
35 SAO PAULO 1 - Ambiente de Produção 29/04/26 às 14:17:04
EVENTO DESCRIÇÃO DO EVENTO SEQUENCIA DO EVENTO VERSÃO DO EVENTO
110110 CARTA DE CORREÇÃO ELETRÔNICA 1 1.00
CARTA DE CORREÇÃO ELETRÔNICA STATUS PROTOCOLO
35260453780554000115550010000017371186009402-CCe1-ProcEventoNFe.xml Status da Carta 135261627626418
DESTINATÁRIO / REMETENTE
NOME / RAZÃO SOCIAL CNPJ / CPF INSCRIÇÃO ESTADUAL
SENDAS DISTRIBUIDORA S/A 06057223038225 123151901112
CORREÇÃO
CORREÇÃO DE CHASSI
SAINDO: DOT LA2025SA110004420 PRETO
X11-MINI MCBRX11M251107081 AZUL
ENTRANDO: DOT LA2025SA110006720 CINZA
X11-MINI MCBRX11M251106043 BRANCO
CONDIÇÕES DE USO
"""

TEXTO_NF_1757 = """RELATÓRIO DE CARTA DE CORREÇÃO ELETRÔNICA
EMITENTE
RAZÃO SOCIAL CNPJ INSCRIÇÃO ESTADUAL
Q.p.a Distribuicao Ltda 53780554000115 623319027116
NOTA FISCAL ELETRÔNICA
SÉRIE NÚMERO DA NOTA FISCAL ELETRÔNICA CHAVE DE ACESSO
001 001757 3526 0453 7805 5400 0115 5500 1000 0017 5711 6584 5174
CARTA DE CORREÇÃO ELETRÔNICA
ÓRGÃO TIPO DE AMBIENTE DATA E HORA DO REGISTRO DO EVENTO
35 SAO PAULO 1 - Ambiente de Produção 30/04/26 às 13:24:44
EVENTO DESCRIÇÃO DO EVENTO SEQUENCIA DO EVENTO VERSÃO DO EVENTO
110110 CARTA DE CORREÇÃO ELETRÔNICA 1 1.00
CARTA DE CORREÇÃO ELETRÔNICA STATUS PROTOCOLO
35260453780554000115550010000017571165845174-CCe1-ProcEventoNFe.xml Status da Carta 135261643394533
CORREÇÃO
DUPLICATAS
Número 001
Vencimento 09/06/2026
Valor 34.800,00
CONDIÇÕES DE USO
"""

TEXTO_NF_1772 = """RELATÓRIO DE CARTA DE CORREÇÃO ELETRÔNICA
EMITENTE
RAZÃO SOCIAL CNPJ INSCRIÇÃO ESTADUAL
Q.p.a Distribuicao Ltda 53780554000115 623319027116
NOTA FISCAL ELETRÔNICA
SÉRIE NÚMERO DA NOTA FISCAL ELETRÔNICA CHAVE DE ACESSO
001 001772 3526 0553 7805 5400 0115 5500 1000 0017 7214 5419 2838
CARTA DE CORREÇÃO ELETRÔNICA
ÓRGÃO TIPO DE AMBIENTE DATA E HORA DO REGISTRO DO EVENTO
35 SAO PAULO 1 - Ambiente de Produção 06/05/26 às 11:48:19
EVENTO DESCRIÇÃO DO EVENTO SEQUENCIA DO EVENTO VERSÃO DO EVENTO
110110 CARTA DE CORREÇÃO ELETRÔNICA 1 1.00
CARTA DE CORREÇÃO ELETRÔNICA STATUS PROTOCOLO
35260553780554000115550010000017721454192838-CCe1-ProcEventoNFe.xml Status da Carta 135261730601390
CORREÇÃO
CORREÇÃO DE CHASSI
SAINDO: SOL 172922504672358 CINZA
ENTRANDO: SOL 172922504672850 CINZA
CONDIÇÕES DE USO
"""

TEXTO_NF_1779 = """RELATÓRIO DE CARTA DE CORREÇÃO ELETRÔNICA
EMITENTE
RAZÃO SOCIAL CNPJ INSCRIÇÃO ESTADUAL
Q.p.a Distribuicao Ltda 53780554000115 623319027116
NOTA FISCAL ELETRÔNICA
SÉRIE NÚMERO DA NOTA FISCAL ELETRÔNICA CHAVE DE ACESSO
001 001779 3526 0553 7805 5400 0115 5500 1000 0017 7914 9706 3640
CARTA DE CORREÇÃO ELETRÔNICA
ÓRGÃO TIPO DE AMBIENTE DATA E HORA DO REGISTRO DO EVENTO
35 SAO PAULO 1 - Ambiente de Produção 06/05/26 às 11:46:39
EVENTO DESCRIÇÃO DO EVENTO SEQUENCIA DO EVENTO VERSÃO DO EVENTO
110110 CARTA DE CORREÇÃO ELETRÔNICA 1 1.00
CARTA DE CORREÇÃO ELETRÔNICA STATUS PROTOCOLO
35260553780554000115550010000017791497063640-CCe1-ProcEventoNFe.xml Status da Carta 135261730574354
CORREÇÃO
DUPLICATAS
Número 001
Vencimento 15/06/2026
Valor 133.700,00
CONDIÇÕES DE USO
"""

TEXTO_NF_1579_ENDERECO = """RELATÓRIO DE CARTA DE CORREÇÃO ELETRÔNICA
EMITENTE
RAZÃO SOCIAL CNPJ INSCRIÇÃO ESTADUAL
Q.p.a Distribuicao Ltda 53780554000204 14755101
NOTA FISCAL ELETRÔNICA
SÉRIE NÚMERO DA NOTA FISCAL ELETRÔNICA CHAVE DE ACESSO
001 001579 3325 0553 7805 5400 0204 5500 1000 0015 7917 4536 4393
CARTA DE CORREÇÃO ELETRÔNICA
ÓRGÃO TIPO DE AMBIENTE DATA E HORA DO REGISTRO DO EVENTO
33 RIO DE JANEIRO 1 - Ambiente de Produção 08/04/26 às 10:23:08
EVENTO DESCRIÇÃO DO EVENTO SEQUENCIA DO EVENTO VERSÃO DO EVENTO
110110 CARTA DE CORREÇÃO ELETRÔNICA 1 1.00
CARTA DE CORREÇÃO ELETRÔNICA STATUS PROTOCOLO
33250553780554000204550010000015791745364393-CCe1-ProcEventoNFe.xml Status da Carta 233260155418865
CORREÇÃO
Correção de endereço
Av Arthur Zanlutti, 1375, Sertãozinho. Matinhos/PR. CEP 83260000
CONDIÇÕES DE USO
"""

TEXTO_NF_36928_MOTOCHEFE = """Dados da Carta de Correção Eletrônica
Chave 33260409089839000112550000000369281387401233
Nota Fiscal Número 000036928 - Série 000
CNPJ emissor 09.089.839/0001-12 UF: Rio de Janeiro
CNPJ receptor 62.634.044/0001-20
Sequencial da Carta de Correção 1
Data da Carta de Correção 04/05/2026
CORRECAO DE CHASSI - SAINDO : ROMA HL5TCAH37S9W75986 BEGE ENTRANDO :
Texto
ROMA HL5TCAH30S9W75986 BEGE
A Carta de Correção é disciplinada pelo parágrafo 1o-A do art. 7o do Convênio S/N, de 15 de dezembro de
1970 e pode ser utilizada para regularização de erro ocorrido na emissão de documento fiscal
"""


def _mock_pdfplumber(texto: str):
    """Helper: contextmanager que faz pdfplumber.open retornar PDF com texto fake."""
    fake_page = MagicMock()
    fake_page.extract_text.return_value = texto
    fake_pdf = MagicMock()
    fake_pdf.pages = [fake_page]
    fake_ctx = MagicMock()
    fake_ctx.__enter__ = MagicMock(return_value=fake_pdf)
    fake_ctx.__exit__ = MagicMock(return_value=False)
    return fake_ctx


def _extrair(texto: str):
    with patch(
        'app.motos_assai.services.parsers.cce_pdf_extractor.pdfplumber.open',
        return_value=_mock_pdfplumber(texto),
    ):
        return extrair_cce(b'fake-pdf-bytes')


# =============================================================================
# Layout Q.P.A. — CORRECAO DE CHASSI (1 par)
# =============================================================================

def test_qpa_chassi_single_par_nf_1729():
    """NF 1729: 1 par DOT, mesma cor (BRANCO -> BRANCO)."""
    dados = _extrair(TEXTO_NF_1729)

    assert dados['formato_detectado'] == FORMATO_QPA
    assert dados['tipo_correcao'] == TIPO_CHASSI
    assert dados['numero_nf_referenciada'] == '1729'
    assert dados['chave_nfe'] == '35260453780554000115550010000017291644542738'
    assert dados['protocolo_cce'] == '135261639015279'
    assert dados['numero_cce'] == 'CCe-1-NF1729'
    assert dados['data_emissao'] == '30/04/2026'

    assert dados['chassis_corrigidos'] == [
        ('LA2025SA110004195', 'LA2025SA110004319'),
    ]
    assert len(dados['chassis_detalhes']) == 1
    detalhe = dados['chassis_detalhes'][0]
    assert detalhe['modelo'] == 'DOT'
    assert detalhe['chassi_antigo'] == 'LA2025SA110004195'
    assert detalhe['chassi_novo'] == 'LA2025SA110004319'
    assert detalhe['cor_antiga'] == 'BRANCO'
    assert detalhe['cor_nova'] == 'BRANCO'

    assert dados['confianca'] >= CONFIANCA_LIMIAR
    assert dados['parser_usado'] == 'DETERMINISTICO_QPA'


def test_qpa_chassi_chassi_curto_sol_nf_1772():
    """NF 1772: chassi SOL tem 15 caracteres (so digitos) — regex VIN 17 falharia."""
    dados = _extrair(TEXTO_NF_1772)

    assert dados['tipo_correcao'] == TIPO_CHASSI
    assert dados['numero_nf_referenciada'] == '1772'
    assert dados['chassis_corrigidos'] == [
        ('172922504672358', '172922504672850'),
    ]
    assert dados['chassis_detalhes'][0]['modelo'] == 'SOL'
    assert len(dados['chassis_corrigidos'][0][0]) == 15  # comprovacao do gap antigo
    assert dados['confianca'] >= CONFIANCA_LIMIAR


# =============================================================================
# Layout Q.P.A. — CORRECAO DE CHASSI (N pares)
# =============================================================================

def test_qpa_chassi_multi_par_nf_1737():
    """NF 1737: 2 pares (DOT + X11-MINI), modelo com hifen, cores diferentes."""
    dados = _extrair(TEXTO_NF_1737)

    assert dados['tipo_correcao'] == TIPO_CHASSI
    assert dados['numero_nf_referenciada'] == '1737'
    assert len(dados['chassis_corrigidos']) == 2

    # Pair 1: DOT
    assert dados['chassis_corrigidos'][0] == (
        'LA2025SA110004420', 'LA2025SA110006720',
    )
    assert dados['chassis_detalhes'][0]['modelo'] == 'DOT'
    assert dados['chassis_detalhes'][0]['cor_antiga'] == 'PRETO'
    assert dados['chassis_detalhes'][0]['cor_nova'] == 'CINZA'

    # Pair 2: X11-MINI (hifen no nome do modelo)
    assert dados['chassis_corrigidos'][1] == (
        'MCBRX11M251107081', 'MCBRX11M251106043',
    )
    assert dados['chassis_detalhes'][1]['modelo'] == 'X11-MINI'
    assert dados['chassis_detalhes'][1]['cor_antiga'] == 'AZUL'
    assert dados['chassis_detalhes'][1]['cor_nova'] == 'BRANCO'

    assert dados['confianca'] >= CONFIANCA_LIMIAR


# =============================================================================
# Layout Q.P.A. — DUPLICATAS
# =============================================================================

def test_qpa_duplicatas_nf_1757():
    """NF 1757: correcao de duplicata — sem chassis."""
    dados = _extrair(TEXTO_NF_1757)

    assert dados['tipo_correcao'] == TIPO_DUPLICATAS
    assert dados['numero_nf_referenciada'] == '1757'
    assert dados['chassis_corrigidos'] == []
    assert dados['chassis_detalhes'] == []

    assert len(dados['duplicatas']) == 1
    dup = dados['duplicatas'][0]
    assert dup['numero'] == '001'
    assert dup['vencimento'] == '09/06/2026'
    assert dup['valor'] == '34.800,00'

    assert dados['confianca'] >= CONFIANCA_LIMIAR


def test_qpa_duplicatas_valor_alto_nf_1779():
    """NF 1779: outra duplicata — verifica valor com 6 digitos."""
    dados = _extrair(TEXTO_NF_1779)

    assert dados['tipo_correcao'] == TIPO_DUPLICATAS
    assert dados['numero_nf_referenciada'] == '1779'
    assert dados['duplicatas'][0]['valor'] == '133.700,00'
    assert dados['duplicatas'][0]['vencimento'] == '15/06/2026'
    assert dados['confianca'] >= CONFIANCA_LIMIAR


# =============================================================================
# Layout Q.P.A. — Correcao de endereco
# =============================================================================

def test_qpa_endereco_nf_1579():
    """NF 1579: correcao de endereco — sem chassis."""
    dados = _extrair(TEXTO_NF_1579_ENDERECO)

    assert dados['tipo_correcao'] == TIPO_ENDERECO
    assert dados['numero_nf_referenciada'] == '1579'
    assert dados['chassis_corrigidos'] == []
    assert 'Arthur Zanlutti' in dados['endereco_corrigido']
    assert 'Matinhos/PR' in dados['endereco_corrigido']
    assert '83260000' in dados['endereco_corrigido']
    assert dados['confianca'] >= CONFIANCA_LIMIAR


# =============================================================================
# Layout MOTOCHEFE — CORRECAO DE CHASSI
# =============================================================================

def test_motochefe_chassi_nf_36928():
    """NF 36928: layout Motochefe compactado — SAINDO/ENTRANDO em 1 linha."""
    dados = _extrair(TEXTO_NF_36928_MOTOCHEFE)

    assert dados['formato_detectado'] == FORMATO_MOTOCHEFE
    assert dados['tipo_correcao'] == TIPO_CHASSI
    assert dados['numero_nf_referenciada'] == '36928'
    assert dados['chave_nfe'] == '33260409089839000112550000000369281387401233'
    assert dados['data_emissao'] == '04/05/2026'

    assert dados['chassis_corrigidos'] == [
        ('HL5TCAH37S9W75986', 'HL5TCAH30S9W75986'),
    ]
    assert dados['chassis_detalhes'][0]['modelo'] == 'ROMA'
    assert dados['chassis_detalhes'][0]['cor_antiga'] == 'BEGE'
    assert dados['chassis_detalhes'][0]['cor_nova'] == 'BEGE'

    assert dados['confianca'] >= CONFIANCA_LIMIAR
    assert dados['parser_usado'] == 'DETERMINISTICO_MOTOCHEFE'


# =============================================================================
# Erros e edge cases
# =============================================================================

def test_pdf_bytes_vazio():
    """pdf_bytes vazio -> CceParseError."""
    with pytest.raises(CceParseError, match='PDF vazio'):
        extrair_cce(b'')


def test_pdf_sem_texto_falha():
    """PDF sem texto extraivel -> CceParseError."""
    with pytest.raises(CceParseError, match='sem texto'):
        _extrair('')


def test_pdf_sem_nf_falha():
    """Documento sem qualquer numero de NF -> CceParseError ('NF referenciada nao encontrada')."""
    texto = "Documento qualquer sem nota fiscal referenciada."
    with pytest.raises(CceParseError, match='NF referenciada'):
        _extrair(texto)


def test_formato_desconhecido_aciona_parser_generico_se_tiver_nf():
    """Formato desconhecido com NF + chassis em pares retorna confianca baixa
    para acionar LLM fallback no caller."""
    texto = """
    Documento estranho fora dos layouts Q.P.A./MOTOCHEFE.
    Nota Fiscal Numero 99999
    Chassis: AAAAAAAAAAAAA1234 BBBBBBBBBBBBB5678
    """
    dados = _extrair(texto)
    assert dados['formato_detectado'] == FORMATO_DESCONHECIDO
    assert dados['numero_nf_referenciada'] == '99999'
    # Parser generico achou chassis em par-impar (heuristica fraca)
    assert dados['chassis_corrigidos'] == [
        ('AAAAAAAAAAAAA1234', 'BBBBBBBBBBBBB5678'),
    ]
    # Mas confianca deve ser BAIXA — caller vai escalar para LLM
    assert dados['confianca'] < CONFIANCA_LIMIAR
    assert dados['parser_usado'] == 'DETERMINISTICO_DESCONHECIDO'


# =============================================================================
# Backward compat: schema antigo (chassis_corrigidos como List[Tuple]) preservado
# =============================================================================

def test_backward_compat_schema_chassis_corrigidos():
    """Schema antigo: chassis_corrigidos como List[Tuple[str, str]] preservado.

    Caller (routes/divergencias.py:aplicar_correcao_cce) consome esse formato
    diretamente. Adicao de chassis_detalhes/tipo_correcao nao deve quebrar.
    """
    dados = _extrair(TEXTO_NF_1729)
    chassis = dados['chassis_corrigidos']
    # Lista de tuplas (str, str) — formato esperado por aplicar_correcao_cce
    assert isinstance(chassis, list)
    assert all(isinstance(par, tuple) and len(par) == 2 for par in chassis)
    assert all(
        isinstance(a, str) and isinstance(n, str) and len(a) >= 13 and len(n) >= 13
        for a, n in chassis
    )
    # Campos do schema original ainda presentes
    assert 'numero_cce' in dados
    assert 'numero_nf_referenciada' in dados
    assert 'chassis_corrigidos' in dados
    assert 'justificativa' in dados
    assert 'data_emissao' in dados
    assert 'confianca' in dados
