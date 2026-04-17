"""
Mascaramento de dados sensiveis brasileiros (CPF, CNPJ, email).

Aplicado por default em todos os summaries de subagente visiveis a
usuarios nao-administradores. Preserva DV/filial/dominio para manter
contexto minimo debuggavel sem expor PII completo.

Regex conservadora — em duvida, NAO mascara (falsos negativos sao
preferiveis a falsos positivos que quebram contexto legitimo).
"""
import re
from typing import Optional

# CPF formatado: 123.456.789-00 → ***.***.***-00
_RE_CPF_FMT = re.compile(r'\d{3}\.\d{3}\.\d{3}-(\d{2})')

# CNPJ formatado: 12.345.678/0001-90 → **.***.***/0001-90
_RE_CNPJ_FMT = re.compile(r'\d{2}\.\d{3}\.\d{3}/(\d{4})-(\d{2})')

# Email: joao@x.com.br → ***@x.com.br
_RE_EMAIL = re.compile(r'[a-zA-Z0-9._%+-]+@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})')

# CPF sem pontuacao: 11 digitos consecutivos (word boundary)
_RE_CPF_RAW = re.compile(r'\b\d{11}\b')

# CNPJ sem pontuacao: 14 digitos consecutivos (word boundary)
_RE_CNPJ_RAW = re.compile(r'\b\d{14}\b')


def mask_pii(text: Optional[str]) -> str:
    """Aplica mascaramento em texto. Retorna '' se text for None."""
    if not text:
        return ''

    # Ordem importa: CNPJ formatado antes de CPF formatado (substring)
    # E CNPJ raw antes de CPF raw (14 dig contem 11)
    text = _RE_CNPJ_FMT.sub(r'**.***.***/\1-\2', text)
    text = _RE_CPF_FMT.sub(r'***.***.***-\1', text)
    text = _RE_EMAIL.sub(r'***@\1', text)
    text = _RE_CNPJ_RAW.sub('**************', text)
    text = _RE_CPF_RAW.sub('***********', text)

    return text
