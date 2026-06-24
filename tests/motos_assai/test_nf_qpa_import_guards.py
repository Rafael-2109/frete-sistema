"""Guards do import de NF Q.P.A. (carga historica Rayssa id 78):

- IMP-2026-06-23-004: parser grava NF com 0/parcial chassis SILENCIOSAMENTE.
  importar_nf_qpa deve FALHAR ALTO (NfQpaParseError) em vez de gravar NF vazia.
- IMP-2026-06-23-008: tela de NF aceita PDF de CCe. importar_nf_qpa deve
  REJEITAR (NfQpaDocumentoCceError) um documento que e' Carta de Correcao.
- IMP-2026-06-23-002: upload em lote sem cap de PDFs por request agrava o OOM.
  O form deve rejeitar lotes acima do limite.
"""
import pytest
from unittest.mock import patch
from wtforms.validators import ValidationError

from app.motos_assai.services.parsers.nf_qpa_adapter import (
    _validar_completude_chassis,
    importar_nf_qpa,
    NfQpaParseError,
    NfQpaDocumentoCceError,
)
from app.motos_assai.services.parsers.cce_pdf_extractor import eh_documento_cce
from app.motos_assai.forms.faturamento_forms import (
    _limitar_qtd_pdfs,
    MAX_PDFS_POR_UPLOAD,
)


# --- IMP-23-004: fail-loud de completude de chassis -------------------------

def test_completude_zero_chassis_falha():
    """0 chassis extraidos -> NfQpaParseError (nao grava NF vazia)."""
    resultado = {'veiculos': [], 'qtd_declarada_itens_veiculo': 3}
    with pytest.raises(NfQpaParseError) as exc:
        _validar_completude_chassis(resultado)
    assert 'sem chassis' in str(exc.value).lower()


def test_completude_parcial_falha():
    """Extraidos < declarados -> NfQpaParseError (nao perde chassis em silencio)."""
    resultado = {
        'veiculos': [{'chassi': 'LA2025SA110004195'}, {'chassi': 'LA2025SA110004196'}],
        'qtd_declarada_itens_veiculo': 3,
    }
    with pytest.raises(NfQpaParseError) as exc:
        _validar_completude_chassis(resultado)
    assert '2' in str(exc.value) and '3' in str(exc.value)


def test_completude_completo_passa():
    """Extraidos == declarados -> nao levanta."""
    resultado = {
        'veiculos': [{'chassi': 'A'}, {'chassi': 'B'}, {'chassi': 'C'}],
        'qtd_declarada_itens_veiculo': 3,
    }
    # nao deve levantar
    _validar_completude_chassis(resultado)


def test_completude_sem_gabarito_so_exige_nao_zero():
    """Sem qtd_declarada (None): basta haver >=1 chassi."""
    _validar_completude_chassis({'veiculos': [{'chassi': 'A'}], 'qtd_declarada_itens_veiculo': None})
    with pytest.raises(NfQpaParseError):
        _validar_completude_chassis({'veiculos': [], 'qtd_declarada_itens_veiculo': None})


# --- IMP-23-008: porteiro CCe-vs-NF -----------------------------------------

@patch('app.motos_assai.services.parsers.cce_pdf_extractor._extrair_texto_pdf')
def test_eh_documento_cce_detecta_cce(mock_texto):
    mock_texto.return_value = (
        'RELATORIO DE CARTA DE CORRECAO ELETRONICA\nCHAVE DE ACESSO\n...'
    )
    assert eh_documento_cce(b'%PDF fake') is True


@patch('app.motos_assai.services.parsers.cce_pdf_extractor._extrair_texto_pdf')
def test_eh_documento_cce_nf_nao_e_cce(mock_texto):
    mock_texto.return_value = (
        'DANFE DOCUMENTO AUXILIAR DA NOTA FISCAL ELETRONICA\nCHAVE DE ACESSO\n...'
    )
    assert eh_documento_cce(b'%PDF fake') is False


@patch('app.motos_assai.services.parsers.nf_qpa_adapter.eh_documento_cce', return_value=True)
def test_importar_nf_qpa_rejeita_cce(mock_eh_cce, app):
    """PDF de CCe no endpoint de NF -> NfQpaDocumentoCceError (nao cria NF orfa)."""
    with app.app_context():
        with pytest.raises(NfQpaDocumentoCceError):
            importar_nf_qpa(
                pdf_bytes=b'%PDF fake cce',
                nome_arquivo='cce.pdf',
                importada_por_id=1,
            )


def test_documento_cce_error_e_subclasse_de_parse_error():
    """Garante que o loop de upload (except NfQpaParseError) nunca perde o arquivo."""
    assert issubclass(NfQpaDocumentoCceError, NfQpaParseError)


# --- IMP-23-002: cap de PDFs por request ------------------------------------

class _FakeFile:
    def __init__(self, nome):
        self.filename = nome


def test_form_cap_rejeita_excesso():
    field = type('F', (), {'data': [_FakeFile(f'nf{i}.pdf') for i in range(MAX_PDFS_POR_UPLOAD + 1)]})()
    with pytest.raises(ValidationError):
        _limitar_qtd_pdfs(None, field)


def test_form_cap_aceita_limite():
    field = type('F', (), {'data': [_FakeFile(f'nf{i}.pdf') for i in range(MAX_PDFS_POR_UPLOAD)]})()
    # nao deve levantar
    _limitar_qtd_pdfs(None, field)
