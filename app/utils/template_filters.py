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

def register_template_filters(app):
    """Registra filtros customizados no Flask"""
    app.jinja_env.filters['file_url'] = file_url
    app.jinja_env.filters['datetime_br'] = datetime_br
    app.jinja_env.filters['date_br'] = date_br
    app.jinja_env.filters['valor_br'] = valor_br
    app.jinja_env.filters['from_json'] = from_json 