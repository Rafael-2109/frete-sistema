"""Testes parser CCe deterministico (Plano 4 Task 7).

Mocka pdfplumber.open para testar regex sem precisar de reportlab.
Testes do fallback LLM nao incluidos — exigem ANTHROPIC_API_KEY.
"""
from unittest.mock import patch, MagicMock

import pytest

from app.motos_assai.services.parsers.cce_pdf_extractor import (
    extrair_cce, CceParseError, CONFIANCA_LIMIAR,
)


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


def test_extrair_cce_pdf_com_pares_explicitos():
    """CCe com pares 'antigo -> novo' explicitos."""
    texto = """
    CARTA DE CORRECAO ELETRONICA - CCe-001-2026

    Referente a Nota Fiscal Eletronica: NF-e 12345

    Data de emissao: 15/05/2026

    JUSTIFICATIVA: Correcao de chassis devido a erro de digitacao
    no momento da emissao da NF original.

    Chassis corrigidos:
    9BXXX12345AAAAA12 -> 9BXXX67890BBBBB34
    9BXXX99999CCCCC56 -> 9BXXX11111DDDDD78
    """
    with patch('app.motos_assai.services.parsers.cce_pdf_extractor.pdfplumber.open',
               return_value=_mock_pdfplumber(texto)):
        dados = extrair_cce(b'fake-pdf-bytes')

    assert dados['numero_nf_referenciada'] == '12345'
    assert dados['numero_cce'] is not None
    assert len(dados['chassis_corrigidos']) == 2
    assert dados['chassis_corrigidos'][0] == ('9BXXX12345AAAAA12', '9BXXX67890BBBBB34')
    assert dados['chassis_corrigidos'][1] == ('9BXXX99999CCCCC56', '9BXXX11111DDDDD78')
    assert dados['data_emissao'] == '15/05/2026'
    assert dados['confianca'] >= 0.8


def test_extrair_cce_pdf_vazio_falha():
    """PDF sem texto -> CceParseError."""
    with patch('app.motos_assai.services.parsers.cce_pdf_extractor.pdfplumber.open',
               return_value=_mock_pdfplumber('')):
        with pytest.raises(CceParseError):
            extrair_cce(b'fake-pdf-bytes')


def test_extrair_cce_sem_nf_referenciada_falha():
    """Texto sem NF -> CceParseError."""
    texto = """
    Documento qualquer sem nota fiscal referenciada.
    Apenas texto solto sem padrao reconhecivel.
    """
    with patch('app.motos_assai.services.parsers.cce_pdf_extractor.pdfplumber.open',
               return_value=_mock_pdfplumber(texto)):
        with pytest.raises(CceParseError, match='NF'):
            extrair_cce(b'fake-pdf-bytes')


def test_extrair_cce_baixa_confianca_quando_so_nf_e_chassis():
    """CCe com NF + chassis (heuristica), sem numero CCe explicito ou justificativa."""
    texto = """
    Doc referente NF 12345 com chassis substituidos:
    9BXXX12345AAAAA12 9BXXX67890BBBBB34
    """
    with patch('app.motos_assai.services.parsers.cce_pdf_extractor.pdfplumber.open',
               return_value=_mock_pdfplumber(texto)):
        dados = extrair_cce(b'fake-pdf-bytes')

    assert dados['numero_nf_referenciada'] == '12345'
    # Heuristica par-impar: 2 chassis -> 1 par
    assert len(dados['chassis_corrigidos']) == 1
    # Confianca menor que limiar (sem CCe explicito + sem justificativa)
    assert dados['confianca'] < CONFIANCA_LIMIAR


def test_extrair_cce_pdf_bytes_vazio():
    """pdf_bytes vazio -> CceParseError."""
    with pytest.raises(CceParseError, match='PDF vazio'):
        extrair_cce(b'')
