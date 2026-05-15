"""
Rotas do E-commerce Preview.

Serve o XEROX local de motochefemaringa.com.br atraves do Flask, com:
  - Path traversal blocking (safe_join)
  - Reescrita de URLs absolutas (-> rota local) em respostas HTML
  - Encoding ISO-8859-1 -> UTF-8 para HTML (charset original do Tray)
  - Login obrigatorio (qualquer usuario autenticado)

Estrutura do mirror (esperado):
    scripts/ecommerce/mirror/
    ├── www.motochefemaringa.com.br/   # HTML pages
    ├── images.tcdn.com.br/             # CSS, JS, imagens (CDN externo)
    ├── fonts.googleapis.com/           # CSS de fontes
    └── fonts.gstatic.com/              # Arquivos .woff2

URL de entrada: /ecommerce-preview/
Mapeamento: /ecommerce-preview/<host>/<path> -> mirror/<host>/<path>
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

from flask import Blueprint, Response, abort, current_app, redirect, request, send_file, url_for
from flask_login import login_required
from werkzeug.security import safe_join

log = logging.getLogger(__name__)

ecommerce_preview_bp = Blueprint(
    "ecommerce_preview",
    __name__,
    url_prefix="/ecommerce-preview",
)

# Caminho do mirror, relativo ao root do projeto
MIRROR_RELATIVE = Path("scripts/ecommerce/mirror")

# Host principal do XEROX (servido como root quando nao especificado)
DEFAULT_HOST = "www.motochefemaringa.com.br"
DEFAULT_PAGE = "index.html"

# URLs absolutas a reescrever no HTML servido (host -> manter, prefixar com /ecommerce-preview/<host>/)
HOSTS_REWRITE = (
    "www.motochefemaringa.com.br",
    "images.tcdn.com.br",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
)

# Paginas dinamicas que NAO existem no XEROX — redirect para placeholder
PATHS_PLACEHOLDER = (
    "/checkout",
    "/loja/carrinho.php",
    "/loja/pedido.php",
    "/cadastro",
    "/my-account",
    "/central-do-cliente",
    "/loja/logout.php",
)


def _mirror_root() -> Path:
    """Resolve caminho absoluto do mirror em runtime (nao em import)."""
    return Path(current_app.root_path).parent / MIRROR_RELATIVE


def _resolver_com_glob(target: Path) -> Path | None:
    """Tenta encontrar arquivo no disco tolerando variantes geradas pelo wget:
       foo.png?abc123, foo.png?def456, foo.png%3Fabc.css, foo.html, etc.

    Estrategia: glob no diretorio pai por arquivos que comecem com o nome
    base. Retorna o primeiro arquivo encontrado (suficiente para servir
    conteudo identico — query strings sao apenas cache busters).
    """
    parent = target.parent
    if not parent.is_dir():
        return None
    base = target.name
    # Tentar variantes mais comuns
    for pattern in (
        f"{base}?*",        # foo.png?abc123
        f"{base}%3F*",      # foo.png%3Fabc123 (URL-encoded)
        f"{base}.html",     # foo (sem ext) -> foo.html
        f"{base}.htm",
    ):
        for candidate in parent.glob(pattern):
            if candidate.is_file():
                return candidate
    return None


def _reescrever_html(html: str) -> str:
    """Reescreve URLs absolutas E relativas (`../host/`) para passar pelo blueprint local.

    Casos cobertos:
      https://images.tcdn.com.br/img/x.jpg
        -> /ecommerce-preview/images.tcdn.com.br/img/x.jpg
      //images.tcdn.com.br/img/x.jpg
        -> /ecommerce-preview/images.tcdn.com.br/img/x.jpg
      ../images.tcdn.com.br/files/...     (gerado por wget --convert-links)
        -> /ecommerce-preview/images.tcdn.com.br/files/...
      https://www.motochefemaringa.com.br/checkout?...
        -> /ecommerce-preview/__placeholder__?origem=checkout
    """
    base = "/ecommerce-preview"

    # Reescrever URLs absolutas https?:// e //host para hosts conhecidos
    for host in HOSTS_REWRITE:
        html = re.sub(
            rf"https?://{re.escape(host)}(/[^\s\"'>]*)?",
            lambda m: f"{base}/{host}{m.group(1) or '/'}",
            html,
        )
        html = re.sub(
            rf"(?<!:)//{re.escape(host)}(/[^\s\"'>]*)?",
            lambda m: f"{base}/{host}{m.group(1) or '/'}",
            html,
        )

    # CRITICO: reescrever URLs relativas `../host/...` que o wget --convert-links gera
    # Sem isso, browser resolve `../images.tcdn...` contra a URL atual e nao acha
    for host in HOSTS_REWRITE:
        # `../host/...` ou `../../host/...` (qualquer numero de ../) — tudo vira absoluto
        html = re.sub(
            rf'((?:\.\./)+){re.escape(host)}(/[^\s\"\'>]*)?',
            lambda m: f"{base}/{host}{m.group(2) or '/'}",
            html,
        )

    # Redirecionar paths dinamicos para placeholder
    for path in PATHS_PLACEHOLDER:
        html = re.sub(
            rf'href=["\'][^"\']*{re.escape(path)}[^"\']*["\']',
            f'href="{base}/__placeholder__?origem={path.strip("/").replace("/", "_")}"',
            html,
        )

    return html


def _serve_html(file_path: Path) -> Response:
    """Le HTML do mirror, decoda ISO-8859-1, reescreve URLs, devolve UTF-8."""
    raw = file_path.read_bytes()
    try:
        html = raw.decode("iso-8859-1")
    except UnicodeDecodeError:
        html = raw.decode("utf-8", errors="replace")

    rewritten = _reescrever_html(html)

    # Trocar charset declarado (ISO-8859-1 -> UTF-8) ja que reentregamos em UTF-8
    rewritten = re.sub(
        r'charset\s*=\s*["\']?iso-8859-1["\']?',
        'charset="utf-8"',
        rewritten,
        flags=re.IGNORECASE,
    )

    return Response(rewritten, mimetype="text/html; charset=utf-8")


@ecommerce_preview_bp.route("/")
@login_required
def index():
    """Entrada do preview — redireciona para a home do XEROX."""
    return redirect(url_for("ecommerce_preview.serve",
                            filename=f"{DEFAULT_HOST}/{DEFAULT_PAGE}"))


@ecommerce_preview_bp.route("/__placeholder__")
@login_required
def placeholder():
    """Pagina mostrada quando link aponta para funcionalidade dinamica nao clonada."""
    return Response(
        """
        <!doctype html>
        <html lang="pt-br"><head>
            <meta charset="utf-8">
            <title>Preview — funcionalidade nao disponivel</title>
            <style>
                body { font-family: -apple-system, sans-serif; padding: 40px; max-width: 600px; margin: auto; }
                .badge { background: #f4c400; color: #000; padding: 4px 8px; border-radius: 4px; font-size: 12px; }
                a { color: #060201; }
            </style>
        </head><body>
            <p><span class="badge">PREVIEW</span> Funcionalidade nao clonada</p>
            <h2>Esta acao depende do backend Tray Commerce</h2>
            <p>Carrinho, checkout, login, cadastro e outras paginas dinamicas nao
            sao parte do XEROX visual. Sao funcionalidades que serao reconstruidas
            na Bagy.</p>
            <p><a href="/ecommerce-preview/">&larr; Voltar para a home do preview</a></p>
        </body></html>
        """,
        mimetype="text/html; charset=utf-8",
    )


@ecommerce_preview_bp.route("/<path:filename>")
@login_required
def serve(filename: str):
    """Serve qualquer arquivo do mirror.

    Estrutura esperada do filename: <host>/<path>
    Ex: 'www.motochefemaringa.com.br/index.html'
        'images.tcdn.com.br/img/img_prod/1263757/foo.jpg'
    """
    mirror = _mirror_root()
    if not mirror.exists():
        abort(503, description=(
            "Mirror nao encontrado. Rode: bash scripts/ecommerce/xerox_site.sh"
        ))

    # safe_join bloqueia path traversal (../../etc/passwd)
    full_path_str = safe_join(str(mirror), filename)
    if full_path_str is None:
        abort(404)
    full_path = Path(full_path_str)

    # Se filename termina em / ou aponta para diretorio, servir index.html dentro
    if full_path.is_dir():
        candidate = full_path / "index.html"
        if candidate.exists():
            full_path = candidate

    # Wget salva URLs com query string como parte do nome do arquivo
    # (foo.png?abc123 vira o arquivo "foo.png?abc123" literalmente).
    # Pior: o mesmo logo aparece varias vezes no site com cache-busters diferentes
    # (?abc1, ?def2, ...) e wget baixa varias versoes — ou apenas algumas.
    # Tambem: --convert-links pode adicionar sufixo .css/.html (ex: style.min.css?abc.css)
    #
    # Estrategia: tentar o exato, depois ampliar com glob (qualquer variante do nome base)
    if not full_path.exists():
        full_path = _resolver_com_glob(full_path) or full_path

    # Fallback: imagens/CSS que o wget nao baixou — redirect para o CDN original
    # (preview e DEV-only, nao tem problema vazar requisicao para tcdn.com.br)
    if not full_path.exists():
        if filename.startswith(("images.tcdn.com.br/", "fonts.googleapis.com/",
                                 "fonts.gstatic.com/")):
            host_e_path = filename.split("/", 1)
            if len(host_e_path) == 2:
                host, path = host_e_path
                qs = "?" + request.query_string.decode("ascii", errors="ignore") \
                     if request.query_string else ""
                external_url = f"https://{host}/{path}{qs}"
                log.info("Preview proxy redirect: %s -> %s", filename, external_url)
                return redirect(external_url, code=302)
        log.info("Preview 404: %s (query=%s)", filename, request.query_string[:60])
        abort(404)

    if not full_path.is_file():
        abort(404)

    # HTML: reescrever URLs absolutas e ajustar charset
    if full_path.suffix.lower() in (".html", ".htm"):
        return _serve_html(full_path)

    # Demais (CSS, JS, imagens): servir direto
    return send_file(full_path)
