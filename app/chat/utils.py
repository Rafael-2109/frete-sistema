"""Utilidades compartilhadas do modulo chat."""
from urllib.parse import urlparse


_CONTROL_CHARS = ('\t', '\n', '\r', '\x00', '\x0b', '\x0c')


def url_safe(url: str) -> bool:
    """Valida deep_link: aceita http, https e paths absolutos do proprio site.

    REJEITA:
    - `javascript:`, `data:`, `file:`, etc (XSS / exfiltracao)
    - Protocol-relative (`//evil.com/x`) — browser resolve como https (open redirect)
    - TAB/CR/LF/NUL antes do scheme (`/\t/evil.com` bypass — urlparse interpreta netloc='evil.com')
    - String vazia / None / nao-str
    """
    if not url or not isinstance(url, str):
        return False
    # Browsers normalizam caracteres de controle; rejeitar antes de urlparse.
    if any(c in url for c in _CONTROL_CHARS):
        return False
    try:
        parsed = urlparse(url)
    except ValueError:
        return False
    scheme = parsed.scheme.lower()
    if scheme in ('http', 'https'):
        return True
    # Scheme vazio: so aceita path absoluto, NAO protocol-relative (`//host`).
    # urlparse('/\t/evil.com').netloc == 'evil.com' — ja bloqueado acima pelo check de control chars,
    # mas mantemos o guard de netloc como defesa em profundidade.
    if scheme != '' or not url.startswith('/') or url.startswith('//'):
        return False
    if parsed.netloc:
        return False
    return True
