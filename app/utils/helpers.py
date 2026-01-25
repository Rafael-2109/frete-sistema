

def limpar_valor(val):
    try:
        if isinstance(val, (int, float)):
            return float(val)
        val = str(val).replace('R$', '').replace(' ', '').replace('.', '').replace(',', '.')
        return float(val)
    except Exception as e:
        print(f"Erro ao limpar valor: {e}")
        return None
