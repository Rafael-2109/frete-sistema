"""Utilidades compartilhadas do modulo chat."""
from urllib.parse import urlparse


_CONTROL_CHARS = ('\t', '\n', '\r', '\x00', '\x0b', '\x0c')


# Rotulos legiveis para alertas de sistema (sender_system_source).
# Usado tanto na lista de threads quanto no remetente das mensagens.
SYSTEM_SOURCE_LABELS = {
    'recebimento': 'Recebimento',
    'dfe': 'DFe bloqueado',
    'cte': 'CTe divergente',
    'sistema': 'Sistema',
}

# Rotulos legiveis para entity_type de threads de entidade.
ENTITY_TYPE_LABELS = {
    'pedido': 'Pedido',
    'nf': 'NF',
    'embarque': 'Embarque',
    'recebimento': 'Recebimento',
    'separacao': 'Separacao',
    'frete': 'Frete',
    'cotacao': 'Cotacao',
}


def system_source_label(source: str) -> str:
    """Converte sender_system_source tecnico em rotulo legivel.

    Fallback: title-case com underscores virando espaco ('meu_source' -> 'Meu Source').
    """
    if not source:
        return 'Sistema'
    return SYSTEM_SOURCE_LABELS.get(source, source.replace('_', ' ').title())


def entity_label(entity_type: str, entity_id: str) -> str:
    """Monta rotulo legivel para thread de entidade ('pedido' + 'VCD123' -> 'Pedido VCD123')."""
    base = ENTITY_TYPE_LABELS.get(entity_type, (entity_type or 'Entidade').title())
    return f'{base} {entity_id}' if entity_id else base


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
