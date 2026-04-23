"""
Parser de markdown para mensagens de chat.

Extrai mentions (@usuario) e renderiza markdown para HTML sanitizado.
Mentions dentro de backticks (`@x`) ou emails (bob@email.com) sao ignoradas.
"""
import re
from typing import List

import markdown as md_lib
import bleach


# Regex: @palavra (letras, numeros, _, -, .) NAO precedido por alfanumerico/@/.
# (evita email) e NAO dentro de backticks (pre-processado separadamente)
_MENTION_RE = re.compile(r'(?<![a-zA-Z0-9_@.])@([a-zA-Z0-9_][a-zA-Z0-9_.-]*)')
_BACKTICK_BLOCK_RE = re.compile(r'`[^`]*`')

ALLOWED_TAGS = [
    'p', 'br', 'strong', 'em', 'u', 's', 'code', 'pre',
    'ul', 'ol', 'li', 'blockquote', 'a', 'h1', 'h2', 'h3', 'h4',
]
ALLOWED_ATTRS = {'a': ['href', 'title', 'rel', 'target']}


def extract_mentions(text: str) -> List[str]:
    """Extrai usernames mencionados (@usuario), sem duplicatas, ignorando backticks e emails."""
    cleaned = _BACKTICK_BLOCK_RE.sub('', text)
    matches = _MENTION_RE.findall(cleaned)
    # Preservar ordem, remover duplicatas
    seen = set()
    result = []
    for m in matches:
        if m not in seen:
            seen.add(m)
            result.append(m)
    return result


def render_markdown(text: str) -> str:
    """Renderiza markdown para HTML (sem sanitizar — usar sanitize_html depois)."""
    return md_lib.markdown(text, extensions=['extra', 'sane_lists'])


def _add_rel_noopener(attrs, _new=False):
    """Callback bleach: adiciona rel=noopener nofollow e target=_blank em links.

    Assinatura segue contrato de bleach.linkify — `_new` e obrigatorio mesmo
    quando nao usado (leading underscore silencia linters).
    """
    attrs[(None, 'rel')] = 'noopener nofollow'
    attrs[(None, 'target')] = '_blank'
    return attrs


def sanitize_html(html: str) -> str:
    """Remove tags/atributos perigosos. Adiciona rel=noopener em links."""
    cleaned = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)
    cleaned = bleach.linkify(cleaned, callbacks=[_add_rel_noopener])
    return cleaned
