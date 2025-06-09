

def limpar_valor(val):
    try:
        if isinstance(val, (int, float)):
            return float(val)
        val = str(val).replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
        return float(val)
    except:
        return None
