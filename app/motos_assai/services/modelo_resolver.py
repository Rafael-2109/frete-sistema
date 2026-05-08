"""Resolve nome/código observado em PDF/Excel para o `AssaiModelo` canônico.

Estratégia em 3 camadas (primeiro match retorna):
1. Match exato em `assai_modelo.codigo` (ex: 'X11_MINI', 'DOT', 'SOL')
2. Match em `assai_modelo_alias.alias` por (tipo, alias) case-insensitive
3. Substring em `assai_modelo.descricao_qpa` (ilike)

Retorna None se nada bate — caller decide se cria pendência ou skipa item.
"""

from __future__ import annotations

import re
from typing import Optional

from app import db
from app.motos_assai.models import (
    AssaiModelo, AssaiModeloAlias,
    ALIAS_TIPO_CODIGO_QPA, ALIAS_TIPO_DESCRICAO_RECIBO, ALIAS_TIPO_NOME_LIVRE,
)


def _normalizar(s: Optional[str]) -> str:
    """Uppercase + trim + colapsa espaços múltiplos."""
    if not s:
        return ''
    return re.sub(r'\s+', ' ', s.strip().upper())


def resolver_modelo(texto: str, origem: str = 'GENERICO') -> Optional[AssaiModelo]:
    """Resolve texto observado para AssaiModelo. None se nada bate.

    `origem` é informativo (logging/debug); não altera lookup.
    """
    if not texto:
        return None

    norm = _normalizar(texto)

    # 1. Match exato em codigo
    m = AssaiModelo.query.filter(
        db.func.upper(AssaiModelo.codigo) == norm,
        AssaiModelo.ativo == True,
    ).first()
    if m:
        return m

    # 2. Match em alias (case-insensitive)
    alias = AssaiModeloAlias.query.filter(
        db.func.upper(AssaiModeloAlias.alias) == norm,
        AssaiModeloAlias.ativo == True,
    ).first()
    if alias:
        return alias.modelo

    # 3. Substring de descricao_qpa
    m = AssaiModelo.query.filter(
        AssaiModelo.descricao_qpa.ilike(f'%{texto.strip()}%'),
        AssaiModelo.ativo == True,
    ).first()
    if m:
        return m

    return None


def resolver_por_codigo_qpa(codigo_qpa: str) -> Optional[AssaiModelo]:
    """Lookup direto por código Q.P.A. (ex: '1342056'). Mais rápido."""
    if not codigo_qpa:
        return None
    cod = str(codigo_qpa).strip()

    # Match direto em assai_modelo.codigo_qpa
    m = AssaiModelo.query.filter_by(codigo_qpa=cod, ativo=True).first()
    if m:
        return m

    # Fallback: match em alias do tipo CODIGO_QPA
    alias = AssaiModeloAlias.query.filter_by(
        alias=cod, tipo=ALIAS_TIPO_CODIGO_QPA, ativo=True,
    ).first()
    if alias:
        return alias.modelo

    return None
