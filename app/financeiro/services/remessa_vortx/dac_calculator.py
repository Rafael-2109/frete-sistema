def calcular_dac_nosso_numero(carteira: str, nosso_numero: str) -> str:
    """Calcula o DAC (Modulo 11) do Nosso Numero para o Banco VORTX (310).

    Algoritmo proprietario VORTX confirmado contra o validador oficial em
    https://boleto-parser.vercel.app/validador-nosso-numero/VORTX :

        prefixo "21" (carteira) + nosso_numero (11 digitos) = 13 digitos
        pesos por posicao (esquerda -> direita): [2, 7, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
        DAC = 0  se resto <= 1
        DAC = 11 - resto  caso contrario
        DAC = 0  se resto >= 10 (fallback de borda)

    Implementacao usa pesos ciclicos [2,3,4,5,6,7] aplicados ao array REVERSO
    — matematicamente equivalente ao protocolo direto (provado por testes
    exaustivos em test_dac_calculator.py para NNs cobrindo todas as 13
    posicoes do array completo).
    """
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
