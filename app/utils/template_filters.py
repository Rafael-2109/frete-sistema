from flask import current_app
from app.utils.file_storage import get_file_storage
from app.utils.timezone import formatar_data_hora_brasil, formatar_data_brasil
from app.utils.valores_brasileiros import formatar_valor_brasileiro
import locale
import json

def file_url(file_path):
    """
    Filtro Jinja2 para gerar URL de arquivo
    Compatível com sistema local e S3
    """
    if not file_path:
        return None

    try:
        storage = get_file_storage()
        return storage.get_file_url(file_path)
    except Exception:
        # Fallback para sistema antigo
        if file_path.startswith('uploads/'):
            from flask import url_for
            return url_for('static', filename=file_path)
        return None

def datetime_br(dt, formato="%d/%m/%Y %H:%M"):
    """
    Filtro para exibir datetime no horário de Brasília (GMT-3)
    Uso no template: {{ minha_data|datetime_br }}
    """
    return formatar_data_hora_brasil(dt, formato)

def date_br(dt, formato="%d/%m/%Y"):
    """
    Filtro para exibir data no formato brasileiro
    Uso no template: {{ minha_data|date_br }}
    """
    return formatar_data_brasil(dt, formato)

def valor_br(valor, decimais=2):
    """
    Filtro para exibir valores monetários no formato brasileiro (1.234,56)
    Uso no template: {{ meu_valor|valor_br }}
    Uso com decimais: {{ meu_valor|valor_br(0) }} -> 1.234

    ✅ MÉTODO COMPROVADO: Mesma lógica de carteira/utils/formatters.py
    """
    if valor is None or valor == '':
        return f"0,{'0' * decimais}"

    try:
        # ✅ MÉTODO COMPROVADO (mesmo da carteira que funciona)
        valor_float = float(valor)
        if decimais == 0:
            return f"{valor_float:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        else:
            return f"{valor_float:,.{decimais}f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return f"0,{'0' * decimais}"

def from_json(json_string):
    """
    Filtro para converter string JSON em objeto Python
    Uso no template: {% set tags = pedido.tags_pedido|from_json %}
    """
    if not json_string:
        return []

    try:
        return json.loads(json_string)
    except (ValueError, TypeError, json.JSONDecodeError):
        return []


def numero_br(valor, decimais=3):
    """
    Filtro para exibir numeros no formato brasileiro (1.234,567)
    SEM prefixo R$ - para quantidades e valores genericos

    Uso no template: {{ quantidade|numero_br }}
    Uso com decimais: {{ quantidade|numero_br(0) }} -> 1.234

    Exemplos:
        1234.567 -> 1.234,567 (padrao 3 decimais)
        1234.5678 |numero_br(4) -> 1.234,5678
        1234 |numero_br(0) -> 1.234
    """
    if valor is None or valor == '':
        return f"0,{'0' * decimais}" if decimais > 0 else "0"

    try:
        valor_float = float(valor)
        if decimais == 0:
            return f"{valor_float:,.0f}".replace(',', 'X').replace('.', ',').replace('X', '.')
        else:
            return f"{valor_float:,.{decimais}f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return f"0,{'0' * decimais}" if decimais > 0 else "0"


_asset_hash_cache = {}  # filename -> hash (so populado quando debug=False)
_IMPORT_RE = None       # regex compilada lazy para @import url(...)


def asset_url(filename):
    """
    Filtro Jinja2 para versioning automatico de assets estaticos.
    Gera URL com hash MD5 do conteudo do arquivo como query string.

    Uso no template: {{ 'css/main.css'|asset_url }}
    Resultado: /static/css/main.css?v=a3f2b1c8

    Beneficio: Quando o arquivo muda, o hash muda automaticamente,
    forcando o navegador a baixar a versao nova.

    IMPORTANTE — entry-points CSS com @import (ex: main.css):
    o hash combina o conteudo do arquivo MAIS o de todos os @import
    transitivos. Sem isso, editar um modulo importado (ex: _monitoramento.css)
    NAO mudaria o hash de main.css (cujo proprio conteudo nunca muda),
    e o navegador continuaria servindo o CSS antigo do cache. URLs http(s)
    (fontes/CDN) sao ignoradas. Arquivos sem @import (JS, CSS folha) seguem
    com o hash do proprio conteudo — comportamento retrocompativel.

    Cache: em producao (debug=False) o resultado e memoizado por processo,
    pois os assets sao imutaveis durante o ciclo de vida do worker. Em dev
    (debug=True) recomputa a cada chamada para refletir edicoes ao vivo.
    """
    import hashlib
    import os
    import re
    from flask import url_for

    global _IMPORT_RE
    if _IMPORT_RE is None:
        _IMPORT_RE = re.compile(rb"""@import\s+url\(\s*['"]?([^'")]+)['"]?\s*\)""")

    debug = bool(getattr(current_app, 'debug', False))
    if not debug and filename in _asset_hash_cache:
        return f"{url_for('static', filename=filename)}?v={_asset_hash_cache[filename]}"

    static_root = os.path.join(current_app.root_path, 'static')
    filepath = os.path.join(static_root, filename)

    md5 = hashlib.md5()
    visited = set()
    found_any = [False]

    def coletar(path):
        real = os.path.realpath(path)
        if real in visited:
            return
        visited.add(real)
        try:
            with open(path, 'rb') as f:
                data = f.read()
        except (FileNotFoundError, IsADirectoryError, OSError):
            return
        found_any[0] = True
        md5.update(data)  # hash sempre do conteudo ORIGINAL (com comentarios)
        # Expande @import apenas em arquivos CSS (entry-points como main.css)
        if path.endswith('.css'):
            base_dir = os.path.dirname(path)
            # Ignora @import dentro de comentarios /* ... */ (ex: modulo desativado
            # temporariamente) — so' a VARREDURA limpa comentarios; o hash acima usa
            # o conteudo integral, entao alternar o comentario ainda muda o ?v=.
            data_scan = re.sub(rb'/\*.*?\*/', b'', data, flags=re.DOTALL)
            for m in _IMPORT_RE.finditer(data_scan):
                ref = m.group(1).decode('utf-8', 'ignore').strip()
                if not ref or ref.startswith('http://') or ref.startswith('https://') or ref.startswith('//'):
                    continue  # CDN/fontes externas — fora do versionamento local
                coletar(os.path.normpath(os.path.join(base_dir, ref)))

    coletar(filepath)

    if not found_any[0]:
        return url_for('static', filename=filename)

    file_hash = md5.hexdigest()[:8]
    if not debug:
        _asset_hash_cache[filename] = file_hash
    return f"{url_for('static', filename=filename)}?v={file_hash}"


def register_template_filters(app):
    """Registra filtros customizados no Flask"""
    app.jinja_env.filters['file_url'] = file_url
    app.jinja_env.filters['datetime_br'] = datetime_br
    app.jinja_env.filters['date_br'] = date_br
    app.jinja_env.filters['valor_br'] = valor_br
    app.jinja_env.filters['numero_br'] = numero_br
    app.jinja_env.filters['from_json'] = from_json
    app.jinja_env.filters['asset_url'] = asset_url
    from app.utils.cnpj_utils import formatar_cnpj
    app.jinja_env.filters['cnpj_br'] = formatar_cnpj