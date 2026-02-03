from flask import current_app
from app.utils.file_storage import get_file_storage
from app.utils.timezone import utc_para_brasil, formatar_data_hora_brasil, formatar_data_brasil
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


def asset_url(filename):
    """
    Filtro Jinja2 para versioning automatico de assets estaticos.
    Gera URL com hash MD5 do conteudo do arquivo como query string.

    Uso no template: {{ 'css/main.css'|asset_url }}
    Resultado: /static/css/main.css?v=a3f2b1c8

    Beneficio: Quando o arquivo muda, o hash muda automaticamente,
    forcando o navegador a baixar a versao nova.
    """
    import hashlib
    import os
    from flask import url_for

    filepath = os.path.join(current_app.root_path, 'static', filename)
    try:
        with open(filepath, 'rb') as f:
            file_hash = hashlib.md5(f.read()).hexdigest()[:8]
        return f"{url_for('static', filename=filename)}?v={file_hash}"
    except FileNotFoundError:
        return url_for('static', filename=filename)


def register_template_filters(app):
    """Registra filtros customizados no Flask"""
    app.jinja_env.filters['file_url'] = file_url
    app.jinja_env.filters['datetime_br'] = datetime_br
    app.jinja_env.filters['date_br'] = date_br
    app.jinja_env.filters['valor_br'] = valor_br
    app.jinja_env.filters['numero_br'] = numero_br
    app.jinja_env.filters['from_json'] = from_json
    app.jinja_env.filters['asset_url'] = asset_url