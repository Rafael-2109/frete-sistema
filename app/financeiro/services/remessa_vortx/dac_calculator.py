def calcular_dac_nosso_numero(carteira: str, nosso_numero: str) -> str:
    if len(carteira) != 2 or not carteira.isdigit():
        raise ValueError('carteira deve ter 2 dígitos numéricos')
    if len(nosso_numero) != 11 or not nosso_numero.isdigit():
        raise ValueError('nosso_numero deve ter 11 dígitos numéricos')

    full = carteira + nosso_numero
    digits = [int(c) for c in full]
    digits.reverse()
    weights = [2, 3, 4, 5, 6, 7]
    total = sum(d * weights[i % 6] for i, d in enumerate(digits))
    remainder = total % 11
    if remainder == 0:
        return '0'
    dac = 11 - remainder
    return '0' if dac >= 10 else str(dac)
