"""
Camada 1 do simulador de conservas Nacom: monta pallets PBR a partir de itens
de uma Separacao, aplicando as regras de palletizacao.

Pallet PBR: base 100x120 cm, estrado 15 cm. A mercadoria pode exceder a base
em ate FOLGA_LASTRO_CM por dimensao (caixas centralizadas). Limite de caixas
por pallet = CadastroPalletizacao.palletizacao (+ overbooking opcional ate 50%).
"""
from math import floor, ceil
from dataclasses import dataclass
from collections import defaultdict

PALLET_BASE_X = 100.0
PALLET_BASE_Y = 120.0
PALLET_ALTURA_ESTRADO = 15.0
FOLGA_LASTRO_CM = 5.0
OVERBOOKING_MAX = 0.50

_PALETA = ['#c0844a', '#4a90d9', '#5cb85c', '#d9534f',
           '#9b59b6', '#f0ad4e', '#16a085', '#e67e22']


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


@dataclass
class CaixaItem:
    cod_produto: str
    num_pedido: str
    cnpj: str
    qtd: float            # caixas (unidades de venda)
    largura_cm: float
    comprimento_cm: float
    altura_cm: float
    palletizacao: float   # caixas por pallet (limite base)
    peso_bruto: float     # por caixa


@dataclass
class Pallet:
    grupo: str
    fechado: bool
    conteudo: list        # [{'cod_produto', 'num_pedido', 'caixas'}]
    merc_x: float
    merc_y: float
    altura_merc: float
    altura_total: float
    peso: float
    color: str = '#c0844a'

    def to_dict(self):
        return {
            'tipo': 'pallet',
            'grupo': self.grupo, 'fechado': self.fechado, 'conteudo': self.conteudo,
            'base_x': PALLET_BASE_X, 'base_y': PALLET_BASE_Y,
            'altura_estrado': PALLET_ALTURA_ESTRADO,
            'merc_x': self.merc_x, 'merc_y': self.merc_y,
            'altura_merc': self.altura_merc, 'altura_total': self.altura_total,
            'peso': self.peso, 'color': self.color,
        }


def _cadastro_ok(i):
    return bool(i.palletizacao and i.altura_cm and i.largura_cm and i.comprimento_cm)


def _finalizar_pallet(conteudo_itens, grupo, fechado):
    """conteudo_itens: [(CaixaItem, caixas)] -- todos de mesma dimensao de caixa."""
    total = sum(c for _, c in conteudo_itens)
    base = conteudo_itens[0][0]
    lastro = calcular_lastro(base.largura_cm, base.comprimento_cm)
    altura = calcular_altura(total, lastro['lastro'], base.altura_cm)
    peso = sum(item.peso_bruto * c for item, c in conteudo_itens)
    conteudo = [{'cod_produto': item.cod_produto,
                 'num_pedido': item.num_pedido, 'caixas': int(c)}
                for item, c in conteudo_itens]
    return Pallet(
        grupo=grupo, fechado=fechado, conteudo=conteudo,
        merc_x=lastro['merc_x'], merc_y=lastro['merc_y'],
        altura_merc=round(altura['altura_total'] - PALLET_ALTURA_ESTRADO, 2),
        altura_total=round(altura['altura_total'], 2), peso=round(peso, 2),
    )


def _empacotar_fila(lista, limite, grupo):
    """First-fit: enche pallets ate `limite` caixas (fracoes de mesma dimensao)."""
    pallets, atual, cap = [], [], 0
    for item, qtd in lista:
        restante = int(qtd)
        while restante > 0:
            if cap >= limite:
                pallets.append(_finalizar_pallet(atual, grupo, fechado=False))
                atual, cap = [], 0
            usar = min(restante, limite - cap)
            atual.append((item, usar))
            cap += usar
            restante -= usar
    if atual:
        pallets.append(_finalizar_pallet(atual, grupo, fechado=False))
    return pallets


def _montar_escopo(itens, overbooking_pct, separado_por_pallet, grupo):
    pallets, fracoes = [], []
    for item in itens:
        limite = int(item.palletizacao * (1 + overbooking_pct))
        if limite <= 0:
            continue
        n_caixas = int(item.qtd)
        n_fechados = n_caixas // limite
        for _ in range(n_fechados):
            pallets.append(_finalizar_pallet([(item, limite)], grupo, fechado=True))
        resto = n_caixas - n_fechados * limite
        if resto > 0:
            fracoes.append((item, resto))
    # agrupar fracoes por dimensao de caixa (regras 2 e 3)
    por_dim = defaultdict(list)
    for item, qtd in fracoes:
        por_dim[(item.largura_cm, item.comprimento_cm)].append((item, qtd))
    for lista in por_dim.values():
        limite = int(lista[0][0].palletizacao * (1 + overbooking_pct))
        if separado_por_pallet:
            por_ped = defaultdict(list)
            for item, qtd in lista:
                por_ped[item.num_pedido].append((item, qtd))
            for sub in por_ped.values():
                pallets += _empacotar_fila(sub, limite, grupo)
        else:
            pallets += _empacotar_fila(lista, limite, grupo)
    return pallets


def _rotulo_grupo(item, modo):
    if modo == 'A':
        return f"PED {item.num_pedido}"
    if modo == 'B':
        return f"CNPJ {item.cnpj}"
    if modo == 'C':
        return "Remontagem"
    return "Lote"


def montar_pallets(itens, modo='A', separado_por_pallet=False, overbooking_pct=0.0):
    overbooking_pct = max(0.0, min(OVERBOOKING_MAX, overbooking_pct))
    pendencias = [{'cod_produto': i.cod_produto, 'motivo': 'cadastro_incompleto'}
                  for i in itens if not _cadastro_ok(i)]
    validos = [i for i in itens if _cadastro_ok(i)]

    if modo == 'D':
        por_prod = defaultdict(list)
        for i in validos:
            por_prod[i.cod_produto].append(i)
        escopos = []
        for cod, lista in por_prod.items():
            base = lista[0]
            total = sum(x.qtd for x in lista)
            escopos.append([CaixaItem(cod, '', '', total, base.largura_cm,
                                      base.comprimento_cm, base.altura_cm,
                                      base.palletizacao, base.peso_bruto)])
    elif modo == 'C':
        # remontagem: escopo unico global (mistura clientes/pedidos)
        escopos = [validos] if validos else []
    else:
        chave = {'A': lambda i: i.num_pedido, 'B': lambda i: i.cnpj}[modo]
        por_escopo = defaultdict(list)
        for i in validos:
            por_escopo[chave(i)].append(i)
        escopos = list(por_escopo.values())

    pallets = []
    for idx, escopo in enumerate(escopos):
        grupo = _rotulo_grupo(escopo[0], modo)
        cor = _PALETA[idx % len(_PALETA)]
        ps = _montar_escopo(escopo, overbooking_pct, separado_por_pallet, grupo)
        for p in ps:
            p.color = cor
        pallets += ps
    return pallets, pendencias
