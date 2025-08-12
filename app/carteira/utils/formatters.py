"""
Formatadores e utilitários de apresentação
"""

def formatar_moeda(valor):
    """Formata valor monetário"""
    if valor is None:
        return "R$ 0,00"
    try:
        return f"R$ {float(valor):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except Exception:
        return "R$ 0,00"


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