def float_or_none(valor_str):
    """
    Converte uma string para float.
    Aceita vírgula como separador decimal.
    Retorna None se o valor não for numérico.
    """
    try:
        return float(valor_str.replace(',', '.'))
    except (ValueError, AttributeError):
        return None
