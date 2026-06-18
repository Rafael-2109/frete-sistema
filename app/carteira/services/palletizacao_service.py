"""
Camada 1 do simulador de conservas Nacom: monta pallets PBR a partir de itens
de uma Separacao, aplicando as regras de palletizacao.

Pallet PBR: base 100x120 cm, estrado 15 cm. A mercadoria pode exceder a base
em ate FOLGA_LASTRO_CM por dimensao (caixas centralizadas). Limite de caixas
por pallet = CadastroPalletizacao.palletizacao (+ overbooking opcional ate 50%).
"""
from math import floor, ceil

PALLET_BASE_X = 100.0
PALLET_BASE_Y = 120.0
PALLET_ALTURA_ESTRADO = 15.0
FOLGA_LASTRO_CM = 5.0
OVERBOOKING_MAX = 0.50


def calcular_lastro(largura_cm, comprimento_cm, folga=FOLGA_LASTRO_CM):
    """Caixas por camada no pallet PBR, testando as 2 orientacoes da base."""
    def _opcao(dim_x, dim_y):
        if not dim_x or not dim_y or dim_x <= 0 or dim_y <= 0:
            return (0, 0, 0)
        nx = floor((PALLET_BASE_X + folga) / dim_x)
        ny = floor((PALLET_BASE_Y + folga) / dim_y)
        return (nx * ny, nx, ny)

    op1 = _opcao(largura_cm, comprimento_cm)   # largura no eixo X
    op2 = _opcao(comprimento_cm, largura_cm)   # comprimento no eixo X
    if op1[0] >= op2[0]:
        lastro, nx, ny = op1
        merc_x, merc_y = nx * largura_cm, ny * comprimento_cm
    else:
        lastro, nx, ny = op2
        merc_x, merc_y = nx * comprimento_cm, ny * largura_cm
    return {'lastro': lastro, 'merc_x': merc_x, 'merc_y': merc_y}


def calcular_altura(caixas, lastro, altura_cm):
    """Altura total do pallet montado (estrado + N camadas de caixas)."""
    if lastro <= 0:
        return {'camadas': 0, 'altura_total': PALLET_ALTURA_ESTRADO}
    camadas = ceil(caixas / lastro)
    return {'camadas': camadas,
            'altura_total': PALLET_ALTURA_ESTRADO + camadas * altura_cm}
