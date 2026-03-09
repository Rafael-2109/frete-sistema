"""
Indexer de rotas e templates para busca semantica.

Extrai rotas Flask via AST, mapeia templates, menus e AJAX endpoints,
e gera embeddings para busca por linguagem natural.

Fases:
1. collect_blueprints() — Descobre todos Blueprint(...) definidos no codebase
2. collect_routes() — Extrai rotas e metadados via AST
3. collect_menu_links() — Parseia base.html para hierarquia de menus
4. collect_ajax_endpoints() — Busca URLs AJAX em templates HTML
5. build_cards() — Monta texto para embedding
6. index_routes() — Gera embeddings e salva no banco

Executar:
    source .venv/bin/activate
    python -m app.embeddings.indexers.route_template_indexer [--dry-run] [--reindex] [--stats]
"""

import ast
import hashlib
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


def _has_app_context() -> bool:
    """Verifica se esta dentro de um Flask app_context."""
    try:
        from flask import current_app
        _ = current_app.name
        return True
    except (RuntimeError, ImportError):
        return False


# Diretorio raiz do projeto
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
APP_DIR = os.path.join(PROJECT_ROOT, 'app')


# =====================================================================
# FASE 1: COLETAR BLUEPRINTS
# =====================================================================

def collect_blueprints() -> Dict[str, Dict[str, str]]:
    """
    Descobre todos os Blueprint(...) definidos no codebase via AST.

    Escaneia TODOS os .py em app/ para encontrar chamadas Blueprint(name, ..., url_prefix=...).

    Returns:
        Dict mapeando blueprint_registered_name -> {var_name, prefix, source_file}
        Exemplo: {"fretes": {"var_name": "fretes_bp", "prefix": "/fretes", "source_file": "app/fretes/routes.py"}}
    """
    blueprints = {}

    for dirpath, _dirnames, filenames in os.walk(APP_DIR):
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
            filepath = os.path.join(dirpath, filename)
            rel_path = os.path.relpath(filepath, PROJECT_ROOT)

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    source = f.read()
                tree = ast.parse(source, filename=rel_path)
            except (SyntaxError, UnicodeDecodeError):
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.Assign):
                    continue
                if not node.targets or not isinstance(node.targets[0], ast.Name):
                    continue
                if not isinstance(node.value, ast.Call):
                    continue

                call = node.value
                func = call.func

                # Detectar Blueprint(...) ou flask.Blueprint(...)
                is_blueprint = False
                if isinstance(func, ast.Name) and func.id == 'Blueprint':
                    is_blueprint = True
                elif isinstance(func, ast.Attribute) and func.attr == 'Blueprint':
                    is_blueprint = True

                if not is_blueprint:
                    continue

                var_name = node.targets[0].id

                # Extrair primeiro argumento (registered name)
                bp_name = None
                if call.args and isinstance(call.args[0], ast.Constant):
                    bp_name = str(call.args[0].value)

                if not bp_name:
                    continue

                # Extrair url_prefix dos kwargs
                prefix = ''
                for kw in call.keywords:
                    if kw.arg == 'url_prefix' and isinstance(kw.value, ast.Constant):
                        prefix = str(kw.value.value)
                        break

                blueprints[bp_name] = {
                    'var_name': var_name,
                    'prefix': prefix or '',
                    'source_file': rel_path,
                }

    logger.info(f"[ROUTE_INDEXER] {len(blueprints)} blueprints encontrados")
    return blueprints


# =====================================================================
# FASE 2: COLETAR ROTAS VIA AST
# =====================================================================

def _extract_decorator_info(decorator: ast.expr) -> Tuple[Optional[str], Optional[str], Optional[List[str]]]:
    """
    Extrai informacao de um decorator AST.

    Returns:
        (bp_var_name, route_path, http_methods) para @bp.route(...)
        ou
        (None, None, None) para decorators que nao sao .route()
    """
    # @bp.route("/path", methods=["GET", "POST"])
    if isinstance(decorator, ast.Call):
        func = decorator.func
        if isinstance(func, ast.Attribute) and func.attr == 'route':
            bp_var = func.value.id if isinstance(func.value, ast.Name) else None

            # Extrair path (primeiro arg)
            path: str = '/'
            if decorator.args and isinstance(decorator.args[0], ast.Constant):
                path = str(decorator.args[0].value)

            # Extrair methods
            methods: List[str] = ['GET']
            for kw in decorator.keywords:
                if kw.arg == 'methods' and isinstance(kw.value, (ast.List, ast.Tuple)):
                    methods = []
                    for elt in kw.value.elts:
                        if isinstance(elt, ast.Constant):
                            methods.append(str(elt.value))

            return bp_var, path, methods

    return None, None, None


def _extract_permission_decorators(decorators: List[ast.expr]) -> Optional[str]:
    """
    Extrai decoradores de permissao de uma lista de decorators.

    Detecta: @login_required, @require_financeiro(), @require_profiles(...)
    """
    permissions = []
    for dec in decorators:
        if isinstance(dec, ast.Name):
            if dec.id == 'login_required':
                permissions.append('login_required')
        elif isinstance(dec, ast.Call):
            if isinstance(dec.func, ast.Name):
                name = dec.func.id
                if name.startswith('require_') or name in ('login_required', 'check_permission'):
                    # Extrair argumentos se houver
                    args_str = ''
                    if dec.args:
                        parts = []
                        for a in dec.args:
                            if isinstance(a, ast.Constant):
                                parts.append(repr(a.value))
                        args_str = ', '.join(parts)
                    permissions.append(f"{name}({args_str})" if args_str else name)
            elif isinstance(dec.func, ast.Attribute):
                attr_name = dec.func.attr
                if attr_name.startswith('require_') or attr_name == 'login_required':
                    permissions.append(attr_name)
        elif isinstance(dec, ast.Attribute):
            if dec.attr == 'login_required':
                permissions.append('login_required')

    return ', '.join(permissions) if permissions else None


def _extract_function_calls(body: List[ast.stmt]) -> Tuple[Optional[str], bool]:
    """
    Escaneia corpo de funcao para render_template() e jsonify().

    Returns:
        (template_path or None, has_jsonify)
    """
    template_path = None
    has_jsonify = False

    for node in ast.walk(ast.Module(body=body, type_ignores=[])):
        if not isinstance(node, ast.Call):
            continue

        func = node.func

        # render_template("path/to/template.html", ...)
        if isinstance(func, ast.Name) and func.id == 'render_template':
            if node.args and isinstance(node.args[0], ast.Constant):
                val = str(node.args[0].value)
                if template_path is None:
                    template_path = val

        # jsonify(...)
        elif isinstance(func, ast.Name) and func.id == 'jsonify':
            has_jsonify = True

    return template_path, has_jsonify


def collect_routes(blueprints: Dict[str, Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Extrai rotas de TODOS os arquivos de rota via AST.

    Para cada funcao com @bp.route():
    - Resolve o blueprint (nome registrado + prefix)
    - Extrai path, methods, template, jsonify, permissions, docstring

    Args:
        blueprints: Resultado de collect_blueprints()

    Returns:
        Lista de dicts com metadados de cada rota
    """
    # Construir mapa inverso: var_name -> bp_registered_name
    var_to_bp = {}
    for bp_name, info in blueprints.items():
        var_to_bp[info['var_name']] = bp_name

    # Coletar rotas de todos os arquivos que contem Blueprint usage
    route_files = set()
    for dirpath, _dirnames, filenames in os.walk(APP_DIR):
        for filename in filenames:
            if not filename.endswith('.py'):
                continue
            filepath = os.path.join(dirpath, filename)
            route_files.add(filepath)

    routes = []

    for filepath in sorted(route_files):
        rel_path = os.path.relpath(filepath, PROJECT_ROOT)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                source = f.read()
            tree = ast.parse(source, filename=rel_path)
        except (SyntaxError, UnicodeDecodeError):
            continue

        # Resolver imports locais: detectar `from app.X.routes import Y_bp`
        local_var_to_bp = dict(var_to_bp)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    imported_name = alias.asname or alias.name
                    if imported_name in var_to_bp:
                        local_var_to_bp[imported_name] = var_to_bp[imported_name]

            # Tambem detectar Blueprint(...) definido localmente
            if isinstance(node, ast.Assign):
                if node.targets and isinstance(node.targets[0], ast.Name):
                    vname = node.targets[0].id
                    if vname in var_to_bp:
                        local_var_to_bp[vname] = var_to_bp[vname]

        # Processar funcoes com decorators
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue

            for decorator in node.decorator_list:
                bp_var, route_path, http_methods = _extract_decorator_info(decorator)
                if bp_var is None:
                    continue

                # Resolver blueprint
                bp_name = local_var_to_bp.get(bp_var)
                if bp_name is None:
                    continue  # Blueprint nao reconhecido

                bp_info = blueprints.get(bp_name, {})
                prefix = bp_info.get('prefix', '')

                # Montar URL completa
                full_path = prefix.rstrip('/') + '/' + route_path.lstrip('/')
                if full_path != '/' and full_path.endswith('/') and route_path != '/':
                    pass  # Manter trailing slash se a rota original tem
                if not full_path.startswith('/'):
                    full_path = '/' + full_path

                # Extrair template e jsonify do corpo
                template_path, has_jsonify = _extract_function_calls(node.body)

                # Determinar tipo
                if template_path:
                    tipo = 'rota_template'
                elif has_jsonify:
                    tipo = 'rota_api'
                else:
                    tipo = 'rota_api'  # Funcoes sem render_template sao tratadas como API

                # Extrair docstring
                docstring = ast.get_docstring(node)

                # Extrair permissoes
                permission = _extract_permission_decorators(node.decorator_list)

                routes.append({
                    'tipo': tipo,
                    'blueprint_name': bp_name,
                    'function_name': node.name,
                    'url_path': full_path,
                    'http_methods': ','.join(sorted(http_methods)),
                    'template_path': template_path,
                    'source_file': rel_path,
                    'source_line': node.lineno,
                    'docstring': docstring,
                    'permission_decorator': permission,
                })
                break  # So processar o primeiro @bp.route() por funcao

    logger.info(f"[ROUTE_INDEXER] {len(routes)} rotas extraidas")
    return routes


# =====================================================================
# FASE 3: COLETAR LINKS DE MENU
# =====================================================================

def collect_menu_links() -> Dict[str, str]:
    """
    Parseia app/templates/base.html para extrair hierarquia de menus.

    Busca padroes:
    - <a class="nav-link dropdown-toggle"> → menu de nivel superior
    - <h6 class="dropdown-header"> → secao dentro do dropdown
    - <a ... href="{{ url_for('blueprint.function') }}"> → item do menu

    O parser trabalha com linhas indexadas para poder "olhar adiante" quando
    o texto do menu de nivel superior esta em linha separada do <a>.

    Returns:
        Dict mapeando "blueprint.function" -> "Menu > Secao > Item"
    """
    base_html_path = os.path.join(APP_DIR, 'templates', 'base.html')
    if not os.path.exists(base_html_path):
        logger.warning("[ROUTE_INDEXER] base.html nao encontrado")
        return {}

    with open(base_html_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    menu_map = {}

    # Regex para extrair url_for e texto do link
    url_for_pattern = re.compile(r"url_for\(['\"]([^'\"]+)['\"]\s*(?:,\s*[^)]+)?\)")

    # Estado do parser
    current_top_menu = ''
    current_section = ''

    for idx, raw_line in enumerate(lines):
        stripped = raw_line.strip()

        # Detectar menu de nivel superior
        # Padrao pode estar em 1 linha ou em 2-3 linhas:
        #   Linha N: <a class="nav-link dropdown-toggle" ...>
        #   Linha N+1:   <i class="fas fa-tasks"></i> Operacional
        #   Linha N+2: </a>
        if 'nav-link dropdown-toggle' in stripped:
            top_name = _extract_menu_text(stripped)
            # Se nao encontrou na mesma linha, olhar nas proximas 3
            if not top_name:
                for lookahead in range(1, 4):
                    if idx + lookahead < len(lines):
                        next_line = lines[idx + lookahead].strip()
                        top_name = _extract_menu_text(next_line)
                        if top_name:
                            break
                        # Parar se encontrou </a> sem texto
                        if '</a>' in next_line:
                            break
            if top_name:
                current_top_menu = top_name
                current_section = ''

        # Detectar secao dentro do dropdown
        # <h6 class="dropdown-header">📦 Pedidos e Separação</h6>
        if 'dropdown-header' in stripped:
            match = re.search(r'dropdown-header[^>]*>(?:<[^>]+>)?\s*(.+?)\s*</h6>', stripped)
            if match:
                section_text = match.group(1).strip()
                # Remover tags HTML inline (icones, spans)
                section_text = re.sub(r'<[^>]+>', '', section_text).strip()
                # Remover emojis unicode (inclui emoticons, dingbats, symbols, variation selectors)
                section_text = re.sub(
                    r'[\U0001F300-\U0001F9FF\u2600-\u27BF\uFE00-\uFE0F\u200D]+',
                    '', section_text,
                ).strip()
                if section_text:
                    current_section = section_text

        # Detectar item de menu com url_for
        # <a class="dropdown-item" href="{{ url_for('fretes.index') }}">
        if 'url_for' in stripped and ('dropdown-item' in stripped or 'nav-link' in stripped):
            # Ignorar dropdown-toggle (ja tratado acima)
            if 'dropdown-toggle' in stripped:
                continue

            endpoint_match = url_for_pattern.search(stripped)
            if endpoint_match:
                endpoint = endpoint_match.group(1)

                # Extrair texto visivel — pode estar na mesma linha ou na proxima
                item_text = _extract_menu_text(stripped)
                if not item_text:
                    for lookahead in range(1, 3):
                        if idx + lookahead < len(lines):
                            next_line = lines[idx + lookahead].strip()
                            item_text = _extract_menu_text(next_line)
                            if item_text:
                                break
                            if '</a>' in next_line:
                                break

                # Montar path do menu
                parts = []
                if current_top_menu:
                    parts.append(current_top_menu)
                if current_section:
                    parts.append(current_section)
                if item_text:
                    parts.append(item_text)

                if parts:
                    menu_map[endpoint] = ' > '.join(parts)

    logger.info(f"[ROUTE_INDEXER] {len(menu_map)} links de menu extraidos")
    return menu_map


def _extract_menu_text(line: str) -> str:
    """
    Extrai texto visivel de uma linha de menu HTML.

    Trata padroes:
    - </i> Texto Aqui
    - </i> <strong>Texto</strong>
    - </i> <span>Texto</span>
    - </strong> Texto
    - Texto simples (sem tags)

    Returns:
        Texto limpo ou string vazia se nao encontrou.
    """
    # Padrao 1: </i> seguido de texto (com ou sem <strong>/<span>)
    match = re.search(r'</i>\s*(?:<(?:strong|span)>)?\s*([^<]+)', line)
    if match:
        text = match.group(1).strip()
        if text:
            return text

    # Padrao 2: </strong> seguido de texto
    match = re.search(r'</strong>\s*([^<]+)', line)
    if match:
        text = match.group(1).strip()
        if text:
            return text

    return ''


# =====================================================================
# FASE 4: COLETAR AJAX ENDPOINTS DOS TEMPLATES
# =====================================================================

def collect_ajax_endpoints() -> Dict[str, List[str]]:
    """
    Busca URLs AJAX referenciadas em templates HTML.

    Padroes detectados:
    - fetch('/api/...
    - $.ajax({ url: '/api/...
    - $.get('/api/...
    - $.post('/api/...
    - url_for('blueprint.function')  (em contexto JS)

    Returns:
        Dict mapeando template_path_relativo -> lista de URLs AJAX
    """
    templates_dir = os.path.join(APP_DIR, 'templates')
    if not os.path.isdir(templates_dir):
        return {}

    ajax_map: Dict[str, List[str]] = {}

    # Patterns para detectar AJAX
    ajax_patterns = [
        re.compile(r"""fetch\s*\(\s*['"`](/[^'"`\s]+)"""),
        re.compile(r"""\$\.ajax\s*\(\s*\{[^}]*url\s*:\s*['"`](/[^'"`\s]+)""", re.DOTALL),
        re.compile(r"""\$\.(?:get|post)\s*\(\s*['"`](/[^'"`\s]+)"""),
        re.compile(r"""url_for\s*\(\s*['"]([^'"]+)['"]\s*\)"""),
    ]

    for dirpath, _, filenames in os.walk(templates_dir):
        for filename in filenames:
            if not filename.endswith('.html'):
                continue

            filepath = os.path.join(dirpath, filename)
            # Path relativo a templates/ (como usado em render_template)
            rel_path = os.path.relpath(filepath, templates_dir)

            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
            except (UnicodeDecodeError, IOError):
                continue

            urls = set()
            for pattern in ajax_patterns:
                for match in pattern.finditer(content):
                    url = match.group(1)
                    # Filtrar URLs estaticas
                    if url.startswith('/static') or url.startswith('/css') or url.startswith('/js'):
                        continue
                    # Ignorar anchors e imagens
                    if url.endswith(('.png', '.jpg', '.gif', '.svg', '.ico')):
                        continue
                    urls.add(url)

            if urls:
                ajax_map[rel_path] = sorted(urls)

    total = sum(len(v) for v in ajax_map.values())
    logger.info(f"[ROUTE_INDEXER] {total} AJAX endpoints em {len(ajax_map)} templates")
    return ajax_map


# =====================================================================
# FASE 5: MONTAR CARTOES
# =====================================================================

def _humanize_function_name(name: str) -> str:
    """Converte function_name em titulo legivel."""
    # index -> Index
    # listar_fretes -> Listar Fretes
    # contas_pagar_hub -> Contas Pagar Hub
    return name.replace('_', ' ').title()


def build_cards(
    routes: List[Dict[str, Any]],
    menu_map: Dict[str, str],
    ajax_map: Dict[str, List[str]],
) -> List[Dict[str, Any]]:
    """
    Monta cartoes de texto para embedding a partir dos dados coletados.

    Enriquece cada rota com:
    - menu_path (se existir no base.html)
    - ajax_endpoints (se o template fizer chamadas AJAX)
    - texto_embedado (cartao formatado para embedding)
    - content_hash (MD5 do texto para deteccao de mudancas)

    Args:
        routes: Resultado de collect_routes()
        menu_map: Resultado de collect_menu_links()
        ajax_map: Resultado de collect_ajax_endpoints()

    Returns:
        Lista de routes enriquecidas com texto_embedado e content_hash
    """
    cards = []

    for route in routes:
        # Resolver menu_path
        endpoint = f"{route['blueprint_name']}.{route['function_name']}"
        menu_path = menu_map.get(endpoint)
        route['menu_path'] = menu_path

        # Resolver ajax_endpoints
        ajax_urls = None
        if route['template_path']:
            ajax_list = ajax_map.get(route['template_path'], [])
            if ajax_list:
                ajax_urls = json.dumps(ajax_list, ensure_ascii=False)
        route['ajax_endpoints'] = ajax_urls

        # Determinar modulo
        parts = route['source_file'].split('/')
        modulo = parts[1] if len(parts) > 1 else 'root'

        # Montar cartao de texto
        if route['tipo'] == 'rota_template':
            titulo = menu_path.split(' > ')[-1] if menu_path else _humanize_function_name(route['function_name'])
            lines = [
                f"Tela: {titulo}",
                f"URL: {route['http_methods']} {route['url_path']}",
                f"Blueprint: {route['blueprint_name']}",
                f"Modulo: {modulo}",
                f"Template: {route['template_path']}",
            ]
            if menu_path:
                lines.append(f"Menu: {menu_path}")
            else:
                lines.append("Menu: Acesso direto (sem link no menu)")
            if route['permission_decorator']:
                lines.append(f"Permissao: {route['permission_decorator']}")
            if route['docstring']:
                # Limitar a 200 chars
                doc = route['docstring'][:200].strip()
                lines.append(f"Descricao: {doc}")
            if ajax_urls:
                ajax_list = json.loads(ajax_urls)
                lines.append(f"APIs que alimentam esta tela: {', '.join(ajax_list[:10])}")

        else:  # rota_api
            lines = [
                f"API: {_humanize_function_name(route['function_name'])}",
                f"URL: {route['http_methods']} {route['url_path']}",
                f"Blueprint: {route['blueprint_name']}",
                f"Modulo: {modulo}",
                f"Retorna: JSON",
            ]
            if route['permission_decorator']:
                lines.append(f"Permissao: {route['permission_decorator']}")
            if route['docstring']:
                doc = route['docstring'][:200].strip()
                lines.append(f"Descricao: {doc}")

            # Buscar quais templates consomem esta API
            consumers = []
            for tpl, ajax_list in ajax_map.items():
                for url in ajax_list:
                    if url == route['url_path'] or route['url_path'].rstrip('/') == url.rstrip('/'):
                        consumers.append(tpl)
                        break
            if consumers:
                lines.append(f"Consumida por: {', '.join(consumers[:5])}")

        texto = '\n'.join(lines)
        route['texto_embedado'] = texto

        # Content hash para deteccao de mudancas
        route['content_hash'] = hashlib.md5(texto.encode('utf-8')).hexdigest()

        cards.append(route)

    logger.info(f"[ROUTE_INDEXER] {len(cards)} cartoes montados")
    return cards


def collect_and_build_cards() -> List[Dict[str, Any]]:
    """
    Executa fases 1-5 de coleta e retorna cartoes prontos para indexacao.

    Funcao de conveniencia para o scheduler, que encapsula:
    1. collect_blueprints()
    2. collect_routes()
    3. collect_menu_links()
    4. collect_ajax_endpoints()
    5. build_cards()

    Nao requer Flask app context (puro filesystem/AST).

    Returns:
        Lista de dicts com todos os campos necessarios para index_routes()
    """
    blueprints = collect_blueprints()
    routes = collect_routes(blueprints)
    menu_map = collect_menu_links()
    ajax_map = collect_ajax_endpoints()
    return build_cards(routes, menu_map, ajax_map)


# =====================================================================
# FASE 6: INDEXACAO
# =====================================================================

def index_routes(
    cards: List[Dict[str, Any]],
    reindex: bool = False,
) -> Dict[str, Any]:
    """
    Gera embeddings e salva rotas no banco.

    Usa content_hash para skip de itens nao modificados.
    Upsert via ON CONFLICT ON CONSTRAINT uq_route_blueprint_function.

    Args:
        cards: Resultado de build_cards()
        reindex: Se True, re-embeda todos (ignora content_hash)

    Returns:
        Estatisticas: embedded, skipped, errors, total_tokens_est
    """
    from app import db as _db
    from app.embeddings.service import EmbeddingService
    from app.embeddings.config import VOYAGE_DEFAULT_MODEL
    from sqlalchemy import text

    stats = {"embedded": 0, "skipped": 0, "errors": 0, "total_tokens_est": 0}

    if not cards:
        return stats

    def _do_index():
        svc = EmbeddingService()

        # Verificar hashes existentes para skip
        existing_hashes = {}
        if not reindex:
            try:
                result = _db.session.execute(
                    text("SELECT blueprint_name, function_name, content_hash FROM route_template_embeddings WHERE content_hash IS NOT NULL")
                )
                for row in result.fetchall():
                    key = f"{row[0]}.{row[1]}"
                    existing_hashes[key] = row[2]
            except Exception:
                pass  # Tabela pode nao existir ainda

        # Filtrar itens que precisam de (re)embedding
        to_embed = []
        for card in cards:
            key = f"{card['blueprint_name']}.{card['function_name']}"
            if not reindex and key in existing_hashes and existing_hashes[key] == card['content_hash']:
                stats["skipped"] += 1
                continue
            to_embed.append(card)

        if not to_embed:
            logger.info(f"[ROUTE_INDEXER] Nada novo (skipped={stats['skipped']})")
            return stats

        # Batch embedding
        batch_size = 128
        for i in range(0, len(to_embed), batch_size):
            batch = to_embed[i:i + batch_size]
            texts = [c["texto_embedado"] for c in batch]

            try:
                embeddings = svc.embed_texts(texts, input_type="document")
            except Exception as e:
                logger.error(f"[ROUTE_INDEXER] Erro batch {i}: {e}")
                stats["errors"] += len(batch)
                continue

            for card, embedding in zip(batch, embeddings):
                try:
                    embedding_json = json.dumps(embedding)
                    tokens_est = max(1, len(card["texto_embedado"]) // 4)
                    stats["total_tokens_est"] += tokens_est

                    _db.session.execute(
                        text("""
                            INSERT INTO route_template_embeddings
                                (tipo, blueprint_name, function_name,
                                 url_path, http_methods, template_path,
                                 menu_path, permission_decorator,
                                 source_file, source_line, docstring, ajax_endpoints,
                                 texto_embedado, embedding, model_used, content_hash,
                                 created_at, updated_at)
                            VALUES
                                (:tipo, :blueprint_name, :function_name,
                                 :url_path, :http_methods, :template_path,
                                 :menu_path, :permission_decorator,
                                 :source_file, :source_line, :docstring, :ajax_endpoints,
                                 :texto_embedado, :embedding, :model_used, :content_hash,
                                 NOW(), NOW())
                            ON CONFLICT ON CONSTRAINT uq_route_blueprint_function
                            DO UPDATE SET
                                tipo = EXCLUDED.tipo,
                                url_path = EXCLUDED.url_path,
                                http_methods = EXCLUDED.http_methods,
                                template_path = EXCLUDED.template_path,
                                menu_path = EXCLUDED.menu_path,
                                permission_decorator = EXCLUDED.permission_decorator,
                                source_file = EXCLUDED.source_file,
                                source_line = EXCLUDED.source_line,
                                docstring = EXCLUDED.docstring,
                                ajax_endpoints = EXCLUDED.ajax_endpoints,
                                texto_embedado = EXCLUDED.texto_embedado,
                                embedding = EXCLUDED.embedding,
                                model_used = EXCLUDED.model_used,
                                content_hash = EXCLUDED.content_hash,
                                updated_at = NOW()
                        """),
                        {
                            "tipo": card["tipo"],
                            "blueprint_name": card["blueprint_name"],
                            "function_name": card["function_name"],
                            "url_path": card["url_path"],
                            "http_methods": card["http_methods"],
                            "template_path": card.get("template_path"),
                            "menu_path": card.get("menu_path"),
                            "permission_decorator": card.get("permission_decorator"),
                            "source_file": card["source_file"],
                            "source_line": card.get("source_line"),
                            "docstring": card.get("docstring"),
                            "ajax_endpoints": card.get("ajax_endpoints"),
                            "texto_embedado": card["texto_embedado"],
                            "embedding": embedding_json,
                            "model_used": VOYAGE_DEFAULT_MODEL,
                            "content_hash": card["content_hash"],
                        }
                    )
                    stats["embedded"] += 1

                except Exception as e:
                    logger.error(f"[ROUTE_INDEXER] Erro salvando {card['blueprint_name']}.{card['function_name']}: {e}")
                    stats["errors"] += 1

            _db.session.commit()
            if i + batch_size < len(to_embed):
                time.sleep(0.5)

        logger.info(f"[ROUTE_INDEXER] Concluido: {stats}")
        return stats

    if _has_app_context():
        return _do_index()
    else:
        from app import create_app
        app = create_app()
        with app.app_context():
            return _do_index()


# =====================================================================
# CLI
# =====================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Indexer de rotas e templates para busca semantica'
    )
    parser.add_argument('--dry-run', action='store_true', help='Simula sem salvar')
    parser.add_argument('--reindex', action='store_true', help='Re-embeda todas')
    parser.add_argument('--stats', action='store_true', help='Mostra estatisticas do indice')
    parser.add_argument('--verbose', action='store_true', help='Mostra detalhes de cada rota')

    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(message)s')

    if args.stats:
        from app import create_app, db as _db
        from sqlalchemy import text as sql_text
        app = create_app()
        with app.app_context():
            try:
                result = _db.session.execute(sql_text("""
                    SELECT
                        COUNT(*) as total,
                        COUNT(embedding) as com_embedding,
                        COUNT(CASE WHEN tipo = 'rota_template' THEN 1 END) as templates,
                        COUNT(CASE WHEN tipo = 'rota_api' THEN 1 END) as apis,
                        COUNT(menu_path) as com_menu,
                        COUNT(ajax_endpoints) as com_ajax
                    FROM route_template_embeddings
                """)).fetchone()
                print(f"\n=== Route Template Embeddings ===")
                if result:
                    print(f"Total: {result[0]}")
                    print(f"Com embedding: {result[1]}")
                    print(f"Rotas template: {result[2]}")
                    print(f"Rotas API: {result[3]}")
                    print(f"Com menu: {result[4]}")
                    print(f"Com AJAX: {result[5]}")
                else:
                    print("Tabela vazia")

                # Top blueprints
                result2 = _db.session.execute(sql_text("""
                    SELECT blueprint_name, COUNT(*) as cnt
                    FROM route_template_embeddings
                    GROUP BY blueprint_name
                    ORDER BY cnt DESC
                    LIMIT 10
                """)).fetchall()
                print(f"\nTop blueprints:")
                for row in result2:
                    print(f"  {row[0]}: {row[1]} rotas")
            except Exception as e:
                print(f"Erro: {e}")
                print("Tabela route_template_embeddings pode nao existir. Rode a migration primeiro.")
        return

    # Fases 1-5 nao precisam de Flask app (puro filesystem)
    print("\n" + "=" * 60)
    print("INDEXACAO SEMANTICA DE ROTAS E TEMPLATES")
    print("=" * 60)

    print("\n[1/5] Coletando blueprints...")
    blueprints = collect_blueprints()
    print(f"       {len(blueprints)} blueprints encontrados")

    print("\n[2/5] Extraindo rotas via AST...")
    routes = collect_routes(blueprints)
    n_templates = sum(1 for r in routes if r['tipo'] == 'rota_template')
    n_apis = sum(1 for r in routes if r['tipo'] == 'rota_api')
    print(f"       {len(routes)} rotas ({n_templates} template, {n_apis} API)")

    print("\n[3/5] Parseando menus do base.html...")
    menu_map = collect_menu_links()
    print(f"       {len(menu_map)} links de menu extraidos")

    print("\n[4/5] Buscando AJAX endpoints nos templates...")
    ajax_map = collect_ajax_endpoints()
    total_ajax = sum(len(v) for v in ajax_map.values())
    print(f"       {total_ajax} AJAX endpoints em {len(ajax_map)} templates")

    print("\n[5/5] Montando cartoes...")
    cards = build_cards(routes, menu_map, ajax_map)
    n_with_menu = sum(1 for c in cards if c.get('menu_path'))
    n_with_ajax = sum(1 for c in cards if c.get('ajax_endpoints'))
    print(f"       {len(cards)} cartoes ({n_with_menu} com menu, {n_with_ajax} com AJAX)")

    if args.verbose:
        print("\n--- Detalhes ---")
        for card in cards:
            menu = card.get('menu_path', '-')
            tpl = card.get('template_path', '-')
            print(f"  [{card['tipo'][:3]}] {card['http_methods']:8s} {card['url_path'][:50]:50s} tpl={tpl[:30] if tpl else '-':30s} menu={menu[:40] if menu else '-'}")

    if args.dry_run:
        total_chars = sum(len(c["texto_embedado"]) for c in cards)
        tokens_est = total_chars // 4
        cost_est = tokens_est * 0.02 / 1_000_000
        print(f"\n[DRY-RUN]")
        print(f"Cartoes a indexar: {len(cards)}")
        print(f"  - Rotas template: {n_templates}")
        print(f"  - Rotas API: {n_apis}")
        print(f"  - Com menu: {n_with_menu}")
        print(f"  - Com AJAX: {n_with_ajax}")
        print(f"Tokens estimados: {tokens_est:,}")
        print(f"Custo estimado: ${cost_est:.6f}")
        print(f"\nPrimeiros 15 cartoes:")
        for c in cards[:15]:
            menu = c.get('menu_path', '-')
            print(f"  [{c['tipo'][:3]}] {c['blueprint_name']}.{c['function_name']}")
            print(f"        URL: {c['url_path']}")
            if c.get('template_path'):
                print(f"        Template: {c['template_path']}")
            if menu != '-':
                print(f"        Menu: {menu}")
        if len(cards) > 15:
            print(f"  ... +{len(cards) - 15} cartoes")
        return

    # Fase 6 precisa de Flask app (banco de dados)
    from app import create_app
    app = create_app()
    with app.app_context():
        stats = index_routes(cards, reindex=args.reindex)
        print(f"\nResultado:")
        print(f"  Embedded: {stats['embedded']}")
        print(f"  Skipped: {stats['skipped']}")
        print(f"  Errors: {stats['errors']}")
        print(f"  Tokens (est): {stats['total_tokens_est']:,}")


if __name__ == '__main__':
    main()
