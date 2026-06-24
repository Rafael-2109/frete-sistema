"""
asset_bundler.py — versionamento de @import em CSS entry-points.

PROBLEMA QUE RESOLVE
--------------------
`main.css` e' so' uma lista de `@import url('./modules/_x.css') layer(...)`. Em
producao o Caddy serve `/static/*` direto do disco com
`Cache-Control: public, max-age=604800, immutable` (ver Caddyfile). `immutable`
diz ao navegador para NUNCA revalidar. Como as URLs dos @import sao FIXAS (sem
`?v=`), editar um modulo CSS nao muda a URL -> o navegador serve a versao velha
do cache por 7 dias, nem F5 resolve. (Versionar so' o `main.css` nao adianta: ele
rebaixa o main.css, mas os @import internos continuam com URL fixa e cacheados.)

SOLUCAO
-------
Servir o `main.css` por uma rota dinamica que reescreve cada @import LOCAL para
`/static/css/<...>?v=<hash-do-conteudo>`. Agora a URL do import muda quando o
conteudo muda -> o navegador rebaixa SO o que mudou; o `immutable` do Caddy passa
a valer corretamente (URL versionada). URLs http(s) (fontes/CDN) sao preservadas.
"""
import os
import re
import hashlib

# @import url('X') — captura a URL; o ` layer(...)` que vem depois fica fora do
# match e e' preservado intacto.
_IMPORT_RE = re.compile(r"""@import\s+url\(\s*['"]?([^'")]+)['"]?\s*\)""")

# Cache por processo (so' usado quando debug=False — assets imutaveis no runtime).
# Chave: rel_path -> (content, etag)
_bundle_cache = {}


def build_versioned_css(static_root, rel_path='css/main.css'):
    """Le o entry-point CSS e devolve (conteudo_reescrito, etag).

    Cada `@import url('./X')` local vira `@import url('/static/<...>?v=<hash>')`.
    URLs http(s)/protocol-relative/data: sao mantidas. @import para arquivo
    inexistente e' deixado como esta' (degrada sem quebrar).
    """
    main_path = os.path.join(static_root, rel_path)
    with open(main_path, 'r', encoding='utf-8') as f:
        content = f.read()

    base_dir = os.path.dirname(main_path)  # .../static/css

    def repl(m):
        url = m.group(1).strip()
        if url.startswith(('http://', 'https://', '//', 'data:')):
            return m.group(0)
        target = os.path.normpath(os.path.join(base_dir, url))
        try:
            with open(target, 'rb') as ff:
                file_hash = hashlib.md5(ff.read()).hexdigest()[:8]
        except OSError:
            return m.group(0)  # arquivo inexistente: nao reescreve
        rel_to_static = os.path.relpath(target, static_root).replace(os.sep, '/')
        new_url = f"/static/{rel_to_static}?v={file_hash}"
        return m.group(0).replace(url, new_url)

    out = _IMPORT_RE.sub(repl, content)
    etag = hashlib.md5(out.encode('utf-8')).hexdigest()
    return out, etag


def get_versioned_css(app, rel_path='css/main.css'):
    """Wrapper com cache por processo em producao; recomputa em dev (reflete
    edicoes ao vivo)."""
    debug = bool(getattr(app, 'debug', False))
    if not debug and rel_path in _bundle_cache:
        return _bundle_cache[rel_path]
    static_root = os.path.join(app.root_path, 'static')
    result = build_versioned_css(static_root, rel_path)
    if not debug:
        _bundle_cache[rel_path] = result
    return result
