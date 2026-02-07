# -*- coding: utf-8 -*-
"""
Parser de Comprovantes PIX — SICOOB
=====================================

Extrai dados de comprovantes PIX do Sicoob a partir de PDFs nativos (text-native).
PDFs PIX Sicoob NÃO requerem OCR — o texto é selecionável diretamente.

Formato detectado:
- Título: "COMPROVANTE DE EFETIVAÇÃO DE PAGAMENTO PIX"
- 1 comprovante por página
- Campos: Tipo Pagamento, Pagador (Nome, CPF/CNPJ, Instituição),
  Destinatário (Nome, CPF/CNPJ, Instituição/Banco),
  Data do pagamento, Valor, ID Transação, Situação do pagamento

Dependências:
    pip install pypdf
"""

import re
import logging
from typing import Optional

from app.financeiro.parsers.models import ComprovantePix

logger = logging.getLogger(__name__)

# ── Padrão de detecção ──────────────────────────────────────────────────────
# Variações observadas no título dos comprovantes PIX Sicoob
_TITULO_PIX_SICOOB = re.compile(
    r'COMPROVANTE\s+DE\s+EFETIVA[CÇ][AÃ]O\s+DE\s+PAGAMENTO\s+PIX',
    re.IGNORECASE,
)


def detectar_pix_sicoob(texto_pagina: str) -> bool:
    """Verifica se o texto de uma página é um comprovante PIX do Sicoob."""
    return bool(_TITULO_PIX_SICOOB.search(texto_pagina))


# ── Regex de extração ────────────────────────────────────────────────────────

# Tipo Pagamento (ex: "Pix via chave", "Pix via manual")
_RE_TIPO_PAGAMENTO = re.compile(
    r'Tipo\s+(?:de\s+)?[Pp]agamento\s*[:\-]?\s*(.+)',
    re.IGNORECASE,
)

# Data/Hora do comprovante (cabeçalho: "DD/MM/YYYY às HH:MM:SS" ou "DD/MM/YYYY HH:MM:SS")
_RE_DATA_COMPROVANTE = re.compile(
    r'(?:Data\s+do?\s+comprovante|Emitido\s+em)\s*[:\-]?\s*(\d{2}/\d{2}/\d{4})\s*(?:[àa]s\s+)?(\d{2}:\d{2}:\d{2})?',
    re.IGNORECASE,
)

# Data do pagamento
_RE_DATA_PAGAMENTO = re.compile(
    r'Data\s+do\s+pagamento\s*[:\-]?\s*(\d{2}/\d{2}/\d{4}\s*\d{2}:\d{2}:\d{2})',
    re.IGNORECASE,
)

# Valor
_RE_VALOR = re.compile(
    r'Valor\s*[:\-]?\s*R\$\s*([\d.,]+)',
    re.IGNORECASE,
)

# ID Transação (EndToEndId)
_RE_ID_TRANSACAO = re.compile(
    r'ID\s+(?:da\s+)?[Tt]ransa[cç][aã]o\s*[:\-]?\s*(\S+)',
    re.IGNORECASE,
)

# Situação do pagamento
_RE_SITUACAO = re.compile(
    r'Situa[cç][aã]o\s+do\s+pagamento\s*[:\-]?\s*(.+)',
    re.IGNORECASE,
)

# Nome (genérico — usado em seção Pagador e Destinatário)
_RE_NOME = re.compile(
    r'Nome\s*[:\-]?\s*(.+)',
    re.IGNORECASE,
)

# CPF/CNPJ
_RE_CPF_CNPJ = re.compile(
    r'CPF/CNPJ\s*[:\-]?\s*([\d.*\-/]+)',
    re.IGNORECASE,
)

# Instituição / Banco
_RE_INSTITUICAO = re.compile(
    r'(?:Institui[cç][aã]o|Banco)\s*(?:/Banco)?\s*[:\-]?\s*(.+)',
    re.IGNORECASE,
)


def _extrair_secoes(texto: str) -> dict:
    """
    Divide o texto da página em seções baseado nos cabeçalhos:
    - "Pagador" (ou "Dados do pagador")
    - "Destinatário" (ou "Dados do destinatário" / "Recebedor")
    - "Dados do pagamento" (ou "Informações do pagamento")

    Retorna dict com chaves 'cabecalho', 'pagador', 'destinatario', 'pagamento'.
    """
    # Normalizar quebras de linha
    linhas = texto.split('\n')

    secoes = {
        'cabecalho': [],
        'pagador': [],
        'destinatario': [],
        'pagamento': [],
    }

    secao_atual = 'cabecalho'

    for linha in linhas:
        linha_lower = linha.strip().lower()

        # Detectar mudança de seção
        if re.match(r'(?:dados\s+d[oe]\s+)?pagador', linha_lower):
            secao_atual = 'pagador'
            continue
        elif re.match(r'(?:dados\s+d[oe]\s+)?(?:destinat[aá]rio|recebedor)', linha_lower):
            secao_atual = 'destinatario'
            continue
        elif re.match(r'(?:dados|informa[cç][oõ]es)\s+d[oe]\s+pagamento', linha_lower):
            secao_atual = 'pagamento'
            continue

        secoes[secao_atual].append(linha)

    # Juntar linhas de cada seção
    return {k: '\n'.join(v) for k, v in secoes.items()}


def _extrair_de_secao(texto_secao: str, regex: re.Pattern) -> Optional[str]:
    """Extrai primeiro match de regex na seção, retorna grupo 1 stripped."""
    match = regex.search(texto_secao)
    if match:
        valor = match.group(1).strip()
        return valor if valor else None
    return None


def _extrair_comprovante_pagina(texto: str, pagina: int) -> Optional[ComprovantePix]:
    """
    Extrai um ComprovantePix dos dados de texto de uma página.

    Args:
        texto: Texto completo da página.
        pagina: Número da página (0-indexed).

    Returns:
        ComprovantePix ou None se não for um comprovante PIX válido.
    """
    if not detectar_pix_sicoob(texto):
        return None

    secoes = _extrair_secoes(texto)
    comp = ComprovantePix(banco_origem='sicoob', pagina=pagina)

    # ── Cabeçalho ──────────────────────────────────────────
    cabecalho = secoes['cabecalho']
    match_data = _RE_DATA_COMPROVANTE.search(cabecalho)
    if match_data:
        comp.data_comprovante = match_data.group(1)
        comp.hora_comprovante = match_data.group(2)

    comp.tipo_pagamento = _extrair_de_secao(cabecalho, _RE_TIPO_PAGAMENTO)

    # ── Pagador ────────────────────────────────────────────
    pagador = secoes['pagador']
    comp.pagador_nome = _extrair_de_secao(pagador, _RE_NOME)
    comp.pagador_cnpj_cpf = _extrair_de_secao(pagador, _RE_CPF_CNPJ)
    comp.pagador_instituicao = _extrair_de_secao(pagador, _RE_INSTITUICAO)

    # ── Destinatário ───────────────────────────────────────
    destinatario = secoes['destinatario']
    comp.destinatario_nome = _extrair_de_secao(destinatario, _RE_NOME)
    comp.destinatario_cnpj_cpf = _extrair_de_secao(destinatario, _RE_CPF_CNPJ)
    comp.destinatario_instituicao = _extrair_de_secao(destinatario, _RE_INSTITUICAO)

    # ── Dados do pagamento ─────────────────────────────────
    pagamento = secoes['pagamento']
    # Se a seção pagamento está vazia, tentar no texto todo
    texto_busca = pagamento if pagamento.strip() else texto

    comp.data_pagamento = _extrair_de_secao(texto_busca, _RE_DATA_PAGAMENTO)
    comp.valor = _extrair_de_secao(texto_busca, _RE_VALOR)
    comp.id_transacao = _extrair_de_secao(texto_busca, _RE_ID_TRANSACAO)
    comp.situacao = _extrair_de_secao(texto_busca, _RE_SITUACAO)

    # Validação mínima: precisa ter ao menos id_transacao OU valor
    if not comp.id_transacao and not comp.valor:
        logger.warning(
            f"[PIX Sicoob] Página {pagina}: sem ID transação e sem valor — ignorando"
        )
        return None

    return comp


def extrair_comprovantes_pix_sicoob(pdf_bytes: bytes) -> list[ComprovantePix]:
    """
    Extrai todos os comprovantes PIX de um PDF do Sicoob.

    Usa pypdf para extração de texto (PDFs PIX Sicoob são text-native).
    Processa cada página independentemente (1 comprovante por página).

    Args:
        pdf_bytes: Conteúdo binário do PDF.

    Returns:
        Lista de ComprovantePix extraídos.
    """
    try:
        from pypdf import PdfReader
        from io import BytesIO
    except ImportError:
        # Fallback para pypdfium2 se pypdf não disponível
        return _extrair_via_pypdfium2(pdf_bytes)

    comprovantes = []

    try:
        reader = PdfReader(BytesIO(pdf_bytes))
        total_paginas = len(reader.pages)

        logger.info(f"[PIX Sicoob] PDF com {total_paginas} página(s)")

        for i, page in enumerate(reader.pages):
            try:
                texto = page.extract_text() or ''
                if not texto.strip():
                    continue

                comp = _extrair_comprovante_pagina(texto, pagina=i)
                if comp:
                    comprovantes.append(comp)

            except Exception as e:
                logger.warning(f"[PIX Sicoob] Erro na página {i}: {e}")
                continue

    except Exception as e:
        logger.error(f"[PIX Sicoob] Erro ao ler PDF: {e}")
        raise

    logger.info(f"[PIX Sicoob] {len(comprovantes)} comprovante(s) extraído(s)")
    return comprovantes


def _extrair_via_pypdfium2(pdf_bytes: bytes) -> list[ComprovantePix]:
    """Fallback: extração via pypdfium2 caso pypdf não esteja instalado."""
    import pypdfium2 as pdfium

    comprovantes = []
    pdf = pdfium.PdfDocument(pdf_bytes)
    total_paginas = len(pdf)

    logger.info(f"[PIX Sicoob] (pypdfium2) PDF com {total_paginas} página(s)")

    for i in range(total_paginas):
        try:
            page = pdf[i]
            texto = page.get_textpage().get_text_range()
            if not texto.strip():
                continue

            comp = _extrair_comprovante_pagina(texto, pagina=i)
            if comp:
                comprovantes.append(comp)

        except Exception as e:
            logger.warning(f"[PIX Sicoob] (pypdfium2) Erro na página {i}: {e}")
            continue

    logger.info(f"[PIX Sicoob] (pypdfium2) {len(comprovantes)} comprovante(s) extraído(s)")
    return comprovantes
