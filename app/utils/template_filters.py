from flask import current_app
from app.utils.file_storage import get_file_storage
from app.utils.timezone import utc_para_brasil, formatar_data_hora_brasil, formatar_data_brasil
from app.utils.valores_brasileiros import formatar_valor_brasileiro
import locale

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

    ⚠️ GARANTIA DE DECIMAIS: Sempre retorna com casas decimais especificadas
    """
    if valor is None or valor == '':
        return f"0,{'0' * decimais}"

    try:
        # Converter para float se necessário
        valor_num = float(valor) if not isinstance(valor, (int, float)) else valor

        # Formatar com decimais explícitos
        valor_str = f"{valor_num:.{decimais}f}"  # Ex: "182301.00"

        # Separar parte inteira e decimal
        partes = valor_str.split('.')
        inteiro = partes[0]
        decimal = partes[1] if len(partes) > 1 else '0' * decimais

        # Adicionar separador de milhares (ponto) a cada 3 dígitos
        if len(inteiro) > 3:
            inteiro_formatado = ''
            for i, digito in enumerate(reversed(inteiro)):
                if i > 0 and i % 3 == 0:
                    inteiro_formatado = '.' + inteiro_formatado
                inteiro_formatado = digito + inteiro_formatado
        else:
            inteiro_formatado = inteiro

        # Retornar no formato brasileiro
        if decimais > 0:
            return f"{inteiro_formatado},{decimal}"
        else:
            return inteiro_formatado

    except (ValueError, TypeError):
        return f"0,{'0' * decimais}"

def register_template_filters(app):
    """Registra filtros customizados no Flask"""
    app.jinja_env.filters['file_url'] = file_url
    app.jinja_env.filters['datetime_br'] = datetime_br
    app.jinja_env.filters['date_br'] = date_br
    app.jinja_env.filters['valor_br'] = valor_br 