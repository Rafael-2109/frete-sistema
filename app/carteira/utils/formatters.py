"""
Formatadores e utilitários de apresentação
"""

def formatar_moeda(valor, casas_decimais=2):
    """
    Formata valor monetário

    Args:
        valor: Valor a ser formatado
        casas_decimais: Número de casas decimais (padrão: 2)

    Returns:
        String formatada como moeda brasileira
    """
    if valor is None:
        zeros = '0' * casas_decimais
        return f"R$ 0,{zeros}"
    try:
        return f"R$ {float(valor):,.{casas_decimais}f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        zeros = '0' * casas_decimais
        return f"R$ 0,{zeros}"


def formatar_peso(peso):
    """Formata peso em kg"""
    if peso is None:
        return "0 kg"
    try:
        return f"{float(peso):,.1f} kg".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return "0 kg"


def formatar_pallet(pallet):
    """Formata quantidade de pallets"""
    if pallet is None:
        return "0 plt"
    try:
        return f"{float(pallet):,.2f} plt".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return "0 plt"