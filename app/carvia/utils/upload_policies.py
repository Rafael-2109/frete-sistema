"""C3 (2026-04-19): Politicas de upload centralizadas para CarVia.

Antes: limites e extensoes estavam espalhados em:
  - importacao_routes.py (PDF/XML, 50MB)
  - custo_entrega_routes.py (10MB, pdf/jpg/png/doc/xls/msg/eml)
  - forms.py:268 FileAllowed em despesas

Agora: fonte unica de verdade. Import lazy nos modulos consumidores para
evitar circular import.

Uso:
    from app.carvia.utils.upload_policies import (
        UPLOAD_MAX_MB_IMPORTACAO, ALLOWED_EXT_IMPORTACAO,
        UPLOAD_MAX_MB_ANEXO, ALLOWED_EXT_ANEXO,
        is_extensao_permitida,
    )
"""

from __future__ import annotations

# Importacao de XML/PDF de CTe e fatura PDF SSW (pipeline principal)
UPLOAD_MAX_MB_IMPORTACAO = 50
ALLOWED_EXT_IMPORTACAO: frozenset[str] = frozenset({'pdf', 'xml'})

# Anexos de custo entrega, despesas, comprovantes — multi-formato
UPLOAD_MAX_MB_ANEXO = 10
ALLOWED_EXT_ANEXO: frozenset[str] = frozenset({
    'pdf', 'jpg', 'jpeg', 'png',
    'doc', 'docx', 'xls', 'xlsx',
    'msg', 'eml',
})

# Helper para bytes
MB = 1024 * 1024
MAX_BYTES_IMPORTACAO = UPLOAD_MAX_MB_IMPORTACAO * MB
MAX_BYTES_ANEXO = UPLOAD_MAX_MB_ANEXO * MB


def is_extensao_permitida(filename: str, allowed: frozenset[str]) -> bool:
    """Valida extensao de arquivo contra conjunto permitido.

    Case-insensitive. Retorna False para filenames sem extensao ou None/vazio.
    """
    if not filename or '.' not in filename:
        return False
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in allowed


def mensagem_erro_extensao(allowed: frozenset[str]) -> str:
    """Mensagem de erro padronizada para extensao nao permitida."""
    return (
        f'Extensao nao permitida. Aceitas: {", ".join(sorted(allowed))}'
    )


def mensagem_erro_tamanho(max_mb: int) -> str:
    """Mensagem de erro padronizada para arquivo grande demais."""
    return f'Arquivo maior que o limite de {max_mb}MB.'
