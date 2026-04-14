"""
Unit Tests — Upload de arquivos do Agente (Fase A/B/C/D — 2026-04-14)

Cobertura:
- Fase A: whitelist expandida, magic bytes anti-spoofing
- Fase C: novos tipos (word, text, bank_cnab, bank_ofx)
- Fase D: constantes de quota por sessao

Roda com: pytest tests/agente/test_file_uploads.py -v
"""
import io

import pytest

from app.agente.routes._constants import (
    ALLOWED_EXTENSIONS,
    TEXT_EXTENSIONS,
    MIME_SIGNATURES,
    MAX_FILE_SIZE,
    MAX_FILES_PER_SESSION,
    MAX_TOTAL_SIZE_PER_SESSION,
)
from app.agente.routes.files import (
    _allowed_file,
    _validate_magic_bytes,
    _get_file_type,
    _get_mimetype,
)


# =====================================================================
# Whitelist (Fase A)
# =====================================================================

@pytest.mark.unit
class TestAllowedExtensions:
    """Valida whitelist expandida em Fase A (2026-04-14)."""

    def test_pdf_accepted(self):
        assert _allowed_file("doc.pdf")
        assert _allowed_file("DOC.PDF")  # case insensitive

    def test_excel_csv_accepted(self):
        assert _allowed_file("planilha.xlsx")
        assert _allowed_file("legado.xls")
        assert _allowed_file("dados.csv")

    def test_word_accepted(self):
        assert _allowed_file("contrato.docx")
        assert _allowed_file("legado.doc")
        assert _allowed_file("rich.rtf")

    def test_text_accepted(self):
        assert _allowed_file("notas.txt")
        assert _allowed_file("readme.md")
        assert _allowed_file("config.json")
        assert _allowed_file("data.xml")
        assert _allowed_file("app.log")

    def test_banking_accepted(self):
        assert _allowed_file("retorno.ret")
        assert _allowed_file("remessa.rem")
        assert _allowed_file("extrato.ofx")
        assert _allowed_file("generico.cnab")

    def test_images_accepted(self):
        assert _allowed_file("print.png")
        assert _allowed_file("foto.jpg")
        assert _allowed_file("foto.jpeg")
        assert _allowed_file("anim.gif")
        assert _allowed_file("photo.webp")

    def test_unknown_rejected(self):
        assert not _allowed_file("malware.exe")
        assert not _allowed_file("arquivo.zip")
        assert not _allowed_file("video.mp4")
        assert not _allowed_file("audio.mp3")
        assert not _allowed_file("sem_extensao")
        assert not _allowed_file("")


# =====================================================================
# Magic bytes anti-spoofing (Fase A)
# =====================================================================

@pytest.mark.unit
class TestMagicBytes:
    """Valida _validate_magic_bytes: rejeitar spoofing de extensao."""

    def test_pdf_valid(self):
        fake = io.BytesIO(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\nrest")
        valido, erro = _validate_magic_bytes(fake, 'pdf')
        assert valido is True
        assert erro == ""

    def test_pdf_spoofed_rejected(self):
        """Arquivo .exe renomeado para .pdf deve ser rejeitado."""
        fake = io.BytesIO(b"MZ\x90\x00" + b"fake exe content")
        valido, erro = _validate_magic_bytes(fake, 'pdf')
        assert valido is False
        assert erro  # mensagem de erro nao vazia

    def test_png_valid(self):
        fake = io.BytesIO(b"\x89PNG\r\n\x1a\n" + b"IHDR rest")
        valido, erro = _validate_magic_bytes(fake, 'png')
        assert valido is True

    def test_jpeg_valid(self):
        fake = io.BytesIO(b"\xff\xd8\xff\xe0" + b"JFIF rest")
        valido, erro = _validate_magic_bytes(fake, 'jpg')
        assert valido is True
        valido2, _ = _validate_magic_bytes(io.BytesIO(b"\xff\xd8\xff\xe0" + b"x"), 'jpeg')
        assert valido2 is True

    def test_gif_valid(self):
        fake = io.BytesIO(b"GIF89a" + b"rest")
        valido, erro = _validate_magic_bytes(fake, 'gif')
        assert valido is True

    def test_docx_xlsx_zip_header(self):
        """docx e xlsx compartilham signature ZIP (PK\\x03\\x04)."""
        fake = io.BytesIO(b"PK\x03\x04" + b"zip content")
        valido_docx, _ = _validate_magic_bytes(fake, 'docx')
        assert valido_docx is True
        fake2 = io.BytesIO(b"PK\x03\x04" + b"x")
        valido_xlsx, _ = _validate_magic_bytes(fake2, 'xlsx')
        assert valido_xlsx is True

    def test_doc_xls_ole_compound(self):
        """doc/xls legado usam OLE Compound File signature."""
        ole = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
        fake = io.BytesIO(ole + b"rest")
        valido_doc, _ = _validate_magic_bytes(fake, 'doc')
        assert valido_doc is True
        fake2 = io.BytesIO(ole + b"x")
        valido_xls, _ = _validate_magic_bytes(fake2, 'xls')
        assert valido_xls is True

    def test_rtf_valid(self):
        fake = io.BytesIO(b"{\\rtf1\\ansi\\deff0" + b"rest")
        valido, _ = _validate_magic_bytes(fake, 'rtf')
        assert valido is True

    def test_text_skipped_validation(self):
        """TEXT_EXTENSIONS pulam validacao (texto puro sem signature)."""
        fake = io.BytesIO(b"qualquer conteudo textual")
        for ext in ('txt', 'md', 'json', 'xml', 'log', 'csv', 'ret', 'rem', 'cnab', 'ofx'):
            valido, erro = _validate_magic_bytes(fake, ext)
            assert valido is True, f".{ext} deveria passar sem validar magic bytes"

    def test_empty_file_rejected(self):
        fake = io.BytesIO(b"")
        valido, erro = _validate_magic_bytes(fake, 'pdf')
        assert valido is False
        assert 'vazio' in erro.lower()

    def test_unknown_ext_fallback_accepts(self):
        """Extensao sem signature definida: aceita (fallback permissivo)."""
        fake = io.BytesIO(b"qualquer binario")
        valido, _ = _validate_magic_bytes(fake, 'extensao_desconhecida')
        assert valido is True


# =====================================================================
# _get_file_type (Fase A + C)
# =====================================================================

@pytest.mark.unit
class TestGetFileType:
    """Valida classificacao de tipos."""

    def test_image_types(self):
        assert _get_file_type("foto.png") == 'image'
        assert _get_file_type("foto.jpg") == 'image'
        assert _get_file_type("foto.jpeg") == 'image'
        assert _get_file_type("anim.gif") == 'image'
        assert _get_file_type("photo.webp") == 'image'

    def test_pdf_type(self):
        assert _get_file_type("doc.pdf") == 'pdf'

    def test_excel_csv(self):
        assert _get_file_type("planilha.xlsx") == 'excel'
        assert _get_file_type("legado.xls") == 'excel'
        assert _get_file_type("dados.csv") == 'csv'

    def test_word_type(self):
        assert _get_file_type("contrato.docx") == 'word'
        assert _get_file_type("legado.doc") == 'word'
        assert _get_file_type("rich.rtf") == 'word'

    def test_text_type(self):
        assert _get_file_type("notas.txt") == 'text'
        assert _get_file_type("readme.md") == 'text'
        assert _get_file_type("config.json") == 'text'
        assert _get_file_type("data.xml") == 'text'
        assert _get_file_type("app.log") == 'text'

    def test_banking_cnab_types(self):
        assert _get_file_type("retorno.ret") == 'bank_cnab'
        assert _get_file_type("remessa.rem") == 'bank_cnab'
        assert _get_file_type("generico.cnab") == 'bank_cnab'

    def test_banking_ofx_type(self):
        assert _get_file_type("extrato.ofx") == 'bank_ofx'

    def test_unknown_fallback(self):
        assert _get_file_type("sem.extensao_desconhecida") == 'file'


# =====================================================================
# _get_mimetype (Fase A + C)
# =====================================================================

@pytest.mark.unit
class TestGetMimetype:
    """Valida MIME types retornados para download."""

    def test_pdf_mime(self):
        assert _get_mimetype("doc.pdf") == 'application/pdf'

    def test_excel_mime(self):
        assert 'spreadsheet' in _get_mimetype("planilha.xlsx")
        assert _get_mimetype("legado.xls") == 'application/vnd.ms-excel'

    def test_word_mime(self):
        assert 'wordprocessing' in _get_mimetype("contrato.docx")
        assert _get_mimetype("legado.doc") == 'application/msword'

    def test_image_mime(self):
        assert _get_mimetype("foto.png") == 'image/png'
        assert _get_mimetype("foto.jpg") == 'image/jpeg'
        assert _get_mimetype("photo.webp") == 'image/webp'

    def test_text_mime(self):
        assert 'text/plain' in _get_mimetype("notas.txt")
        assert 'markdown' in _get_mimetype("readme.md")
        assert _get_mimetype("config.json") == 'application/json'

    def test_banking_mime(self):
        assert 'text/plain' in _get_mimetype("retorno.ret")
        assert _get_mimetype("extrato.ofx") == 'application/x-ofx'

    def test_unknown_fallback(self):
        assert _get_mimetype("sem.extensao_x") == 'application/octet-stream'


# =====================================================================
# Constants (Fase A + D)
# =====================================================================

@pytest.mark.unit
class TestConstants:
    """Valida constantes de whitelist, magic bytes e quota."""

    def test_allowed_extensions_count(self):
        # Fase A expandiu de 8 para 20 tipos
        assert len(ALLOWED_EXTENSIONS) >= 20

    def test_allowed_extensions_contains_all_categories(self):
        for ext in ('pdf', 'xlsx', 'xls', 'csv', 'png', 'jpg', 'jpeg', 'gif'):
            assert ext in ALLOWED_EXTENSIONS, f".{ext} (original) deve permanecer"
        for ext in ('docx', 'doc', 'rtf', 'txt', 'md', 'json', 'xml', 'log'):
            assert ext in ALLOWED_EXTENSIONS, f".{ext} (novo Fase A) deve estar"
        for ext in ('rem', 'ret', 'cnab', 'ofx'):
            assert ext in ALLOWED_EXTENSIONS, f".{ext} (bancario) deve estar"
        assert 'webp' in ALLOWED_EXTENSIONS

    def test_text_extensions_subset_of_allowed(self):
        """TEXT_EXTENSIONS devem estar todas em ALLOWED_EXTENSIONS."""
        assert TEXT_EXTENSIONS.issubset(ALLOWED_EXTENSIONS)

    def test_mime_signatures_cover_binary_types(self):
        """Tipos binarios criticos devem ter signature."""
        for ext in ('pdf', 'png', 'jpg', 'jpeg', 'gif', 'docx', 'xlsx', 'doc', 'xls', 'rtf'):
            assert ext in MIME_SIGNATURES, f".{ext} precisa de signature para anti-spoofing"

    def test_quota_positive(self):
        assert MAX_FILES_PER_SESSION > 0
        assert isinstance(MAX_FILES_PER_SESSION, int)

    def test_quota_total_sanity(self):
        """Quota total deve ser >= max file size e <= 500MB."""
        assert MAX_TOTAL_SIZE_PER_SESSION >= MAX_FILE_SIZE
        assert MAX_TOTAL_SIZE_PER_SESSION <= 500 * 1024 * 1024

    def test_max_file_size_unchanged(self):
        """MAX_FILE_SIZE continua em 10MB (nao alterado nas fases)."""
        assert MAX_FILE_SIZE == 10 * 1024 * 1024
