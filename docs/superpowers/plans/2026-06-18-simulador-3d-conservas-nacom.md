<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-18
-->
# Simulador 3D — Conservas Nacom (carga mista pallet + moto) Implementation Plan

> **Papel:** Plano de implementação task-by-task (TDD) da expansão do simulador 3D para montar pallets PBR de conservas Nacom e arranjá-los no mesmo baú das motos (Nacom embaixo), com caminho crítico e flags configuráveis.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Indice

- [Global Constraints](#global-constraints)
- [File Structure](#file-structure)
- [Task 1 — Geometria do pallet (lastro + altura)](#task-1-camada-1--geometria-do-pallet-lastro--altura)
- [Task 2 — Montagem de pallets (regras 1–3 + modos A–D)](#task-2-camada-1--montagem-de-pallets-regras-13--modos-ad)
- [Task 3 — Loader da Separação](#task-3-camada-1--loader-da-separação)
- [Task 4 — bin-packer: perfil multi-slab](#task-4-bin-packer--perfil-multi-slab-regressão-moto-only-verde)
- [Task 5 — bin-packer: item pallet (caminho crítico)](#task-5-bin-packer--item-pallet-orientação-única--caminho-crítico)
- [Task 6 — bin-packer: 2 fases + pallet sobre pallet](#task-6-bin-packer--2-fases-nacom-embaixo--pallet-sobre-pallet)
- [Task 7 — Endpoint pallets-por-separacao](#task-7-api--endpoint-pallets-por-separacao)
- [Task 8 — Modo embarque misto](#task-8-api--nacom-no-modo-embarque-misto)
- [Task 9 — Render estrado + coluna](#task-9-render--estrado--coluna-no-threejs)
- [Task 10 — UI: flags + merge](#task-10-ui--flags-merge-palletsmotos-seletor-de-separação)
- [Self-Review](#self-review)

**Goal:** Expandir o simulador 3D de carga (hoje só motos CarVia) para montar pallets PBR de conservas Nacom a partir de uma Separação e arranjá-los no mesmo baú (pallets no piso, motos por cima), com caminho crítico e flags configuráveis.

**Architecture:** Duas camadas. Camada 1 (Python, `app/carteira/services/palletizacao_service.py`): funções puras + loader que transformam itens de uma Separação em pallets, aplicando regras de palletização. Camada 2 (JS, `bin-packer.js`): perfil multi-slab por item (estrado + coluna) com colisão por altura (caminho crítico) e empacotamento em 2 fases (pallets antes das motos). Rotas em `app/carvia/routes/simulador_routes.py` ligam as duas; render em `carga-renderer.js`.

**Tech Stack:** Python 3.12 / Flask 3.1 / SQLAlchemy 2.0 / pytest; JavaScript IIFE (sem bundler) / Three.js 0.128 / Node puro para testes do packer.

## Global Constraints

- **Ativar venv** antes de qualquer `pytest`/`python`: `source .venv/bin/activate` (uma vez por shell).
- **Sem migration de schema** — todos os campos já existem (`CadastroPalletizacao`, `Separacao`).
- **Pallet PBR** = base `100×120` cm, estrado `15` cm (`PALLET_BASE_X=100.0`, `PALLET_BASE_Y=120.0`, `PALLET_ALTURA_ESTRADO=15.0`).
- **Folga de lastro** = `5.0` cm (mercadoria pode exceder a base em até +5 por dimensão).
- **Overbooking** = teto `0.50` (50%) sobre `CadastroPalletizacao.palletizacao`.
- **Default de agrupamento** = modo `A` (separado por pedido). Demais comportamentos OFF por padrão.
- **NÃO** estender `app/carteira/main_routes.py` (regra do projeto). Rotas novas em `app/carvia/routes/simulador_routes.py`.
- **Campos de tabela** vêm dos schemas JSON; os usados aqui já foram verificados: `Separacao` (`separacao_lote_id`, `num_pedido`, `cnpj_cpf`, `cod_produto`, `qtd_saldo`), `CadastroPalletizacao` (`cod_produto`, `palletizacao`, `peso_bruto`, `altura_cm`, `largura_cm`, `comprimento_cm`, `ativo`).
- **Testes pytest** usam a fixture `db` (savepoint/rollback, PostgreSQL local) de `tests/conftest.py`; `cod_produto` único via `uuid` para não colidir.
- **Testes do packer**: `node app/static/js/simulador-carga/bin-packer.test.js` (mini-runner `test`/`assert`; exit 0 = verde).
- **CNPJ do modo B** = `Separacao.cnpj_cpf` (decisão confirmada).

---

## File Structure

**Criar:**
- `app/carteira/services/palletizacao_service.py` — Camada 1 (montagem de pallets). Funções puras + loader.
- `tests/carteira/test_palletizacao_service.py` — testes da Camada 1.
- `app/templates/carvia/simulador/_pallet_controls.html` — partial das flags.

**Modificar:**
- `app/static/js/simulador-carga/bin-packer.js` — perfil multi-slab, colisão por altura, item pallet, 2 fases.
- `app/static/js/simulador-carga/bin-packer.test.js` — casos pallet/caminho crítico/Nacom-embaixo.
- `app/carvia/routes/simulador_routes.py` — endpoint `pallets-por-separacao` + Nacom no modo embarque.
- `app/static/js/simulador-carga/carga-renderer.js` — render estrado + coluna.
- `app/static/js/simulador-carga/simulador-ui.js` — flags, merge pallets+motos, legenda por grupo.
- `app/templates/carvia/simulador/simulador_livre.html`, `simulador_embarque.html` — seletor de separação + partial.
- `app/static/css/modules/_simulador_carga.css` — estilo estrado/coluna e controles.

---

## Task 1: Camada 1 — geometria do pallet (lastro + altura)

**Files:**
- Create: `app/carteira/services/palletizacao_service.py`
- Test: `tests/carteira/test_palletizacao_service.py`

**Interfaces:**
- Produces:
  - constantes `PALLET_BASE_X=100.0`, `PALLET_BASE_Y=120.0`, `PALLET_ALTURA_ESTRADO=15.0`, `FOLGA_LASTRO_CM=5.0`, `OVERBOOKING_MAX=0.50`
  - `calcular_lastro(largura_cm, comprimento_cm, folga=FOLGA_LASTRO_CM) -> dict` com chaves `{'lastro': int, 'merc_x': float, 'merc_y': float}`
  - `calcular_altura(caixas: int, lastro: int, altura_cm: float) -> dict` com chaves `{'camadas': int, 'altura_total': float}`

- [ ] **Step 1: Write the failing test**

```python
# tests/carteira/test_palletizacao_service.py
"""Testes da Camada 1 do simulador de conservas (palletizacao_service)."""
from app.carteira.services.palletizacao_service import (
    calcular_lastro, calcular_altura,
)


class TestGeometria:
    def test_lastro_caixa_quadrada_4830103(self):
        # caixa 26x26 -> lastro efetivo (100+5)/26=4 x (120+5)/26=4 = 16
        r = calcular_lastro(largura_cm=26, comprimento_cm=26)
        assert r['lastro'] == 16
        assert r['merc_x'] == 104
        assert r['merc_y'] == 104

    def test_lastro_escolhe_melhor_orientacao(self):
        # caixa 40x30: orient A (40 em X,30 em Y)=floor(105/40)*floor(125/30)=2*4=8
        #              orient B (30 em X,40 em Y)=floor(105/30)*floor(125/40)=3*3=9 -> vence
        r = calcular_lastro(largura_cm=40, comprimento_cm=30)
        assert r['lastro'] == 9

    def test_lastro_caixa_invalida(self):
        assert calcular_lastro(0, 26)['lastro'] == 0

    def test_altura_4_camadas(self):
        # 64 caixas / lastro 16 = 4 camadas; 15 + 4*30.5 = 137.0
        r = calcular_altura(caixas=64, lastro=16, altura_cm=30.5)
        assert r['camadas'] == 4
        assert r['altura_total'] == 137.0

    def test_altura_arredonda_para_cima(self):
        # 65 caixas / 16 = 4.06 -> 5 camadas
        assert calcular_altura(caixas=65, lastro=16, altura_cm=30.5)['camadas'] == 5

    def test_altura_lastro_zero(self):
        assert calcular_altura(caixas=10, lastro=0, altura_cm=30)['altura_total'] == 15.0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest tests/carteira/test_palletizacao_service.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.carteira.services.palletizacao_service'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/carteira/services/palletizacao_service.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest tests/carteira/test_palletizacao_service.py -v`
Expected: PASS (6 passed)

- [ ] **Step 5: Commit**

```bash
git add app/carteira/services/palletizacao_service.py tests/carteira/test_palletizacao_service.py
git commit -m "feat(simulador): geometria de pallet PBR (lastro+altura) para conservas"
```

---

## Task 2: Camada 1 — montagem de pallets (regras 1–3 + modos A–D)

**Files:**
- Modify: `app/carteira/services/palletizacao_service.py`
- Test: `tests/carteira/test_palletizacao_service.py`

**Interfaces:**
- Consumes: `calcular_lastro`, `calcular_altura` (Task 1).
- Produces:
  - dataclass `CaixaItem(cod_produto:str, num_pedido:str, cnpj:str, qtd:float, largura_cm:float, comprimento_cm:float, altura_cm:float, palletizacao:float, peso_bruto:float)`
  - dataclass `Pallet(grupo:str, fechado:bool, conteudo:list, merc_x:float, merc_y:float, altura_merc:float, altura_total:float, peso:float, color:str)` com `to_dict() -> dict`
  - `montar_pallets(itens: list[CaixaItem], modo='A', separado_por_pallet=False, overbooking_pct=0.0) -> tuple[list[Pallet], list[dict]]` (retorna `(pallets, pendencias)`)
  - `conteudo` de cada pallet = `[{'cod_produto': str, 'num_pedido': str, 'caixas': int}]`

- [ ] **Step 1: Write the failing test**

```python
# adicionar em tests/carteira/test_palletizacao_service.py
from app.carteira.services.palletizacao_service import CaixaItem, montar_pallets


def _item(cod='A', ped='P1', cnpj='C1', qtd=64, larg=26, comp=26, alt=30.5,
          palt=64, peso=1.0):
    return CaixaItem(cod, ped, cnpj, qtd, larg, comp, alt, palt, peso)


class TestMontagem:
    def test_pallet_fechado_regra1(self):
        # 128 caixas, limite 64 -> 2 pallets fechados, sem fracao
        pallets, pend = montar_pallets([_item(qtd=128, palt=64)])
        assert len(pallets) == 2
        assert all(p.fechado for p in pallets)
        assert pend == []

    def test_fechado_mais_fracao(self):
        # 70 caixas, limite 64 -> 1 fechado (64) + 1 fracao (6)
        pallets, _ = montar_pallets([_item(qtd=70, palt=64)])
        assert len(pallets) == 2
        assert [p.fechado for p in pallets] == [True, False]

    def test_fracoes_mesma_dimensao_juntam_regra2(self):
        # 2 produtos mesma caixa (26x26), 56+56=112 <= limite 120 -> 1 pallet
        a = _item(cod='4320147', qtd=56, palt=120)
        b = _item(cod='4360147', qtd=56, palt=120)
        pallets, _ = montar_pallets([a, b], modo='A', separado_por_pallet=False)
        assert len(pallets) == 1
        cods = {c['cod_produto'] for c in pallets[0].conteudo}
        assert cods == {'4320147', '4360147'}

    def test_overbooking_50pct(self):
        # 150 caixas, palletizacao 100, overbooking 0.5 -> limite 150 -> 1 fechado
        pallets, _ = montar_pallets([_item(qtd=150, palt=100)], overbooking_pct=0.5)
        assert len([p for p in pallets if p.fechado]) == 1

    def test_modo_A_nao_mistura_pedidos(self):
        a = _item(cod='X', ped='P1', qtd=10, palt=120)
        b = _item(cod='X', ped='P2', qtd=10, palt=120)
        pallets, _ = montar_pallets([a, b], modo='A')
        # pedidos diferentes -> escopos diferentes -> 2 pallets (nunca compartilham)
        assert len(pallets) == 2

    def test_modo_B_mesmo_cnpj_compartilha(self):
        a = _item(cod='X', ped='P1', cnpj='C1', qtd=10, palt=120)
        b = _item(cod='X', ped='P2', cnpj='C1', qtd=10, palt=120)
        pallets, _ = montar_pallets([a, b], modo='B', separado_por_pallet=False)
        assert len(pallets) == 1  # mesmo CNPJ, off -> compartilham

    def test_modo_B_separado_por_pallet(self):
        a = _item(cod='X', ped='P1', cnpj='C1', qtd=10, palt=120)
        b = _item(cod='X', ped='P2', cnpj='C1', qtd=10, palt=120)
        pallets, _ = montar_pallets([a, b], modo='B', separado_por_pallet=True)
        assert len(pallets) == 2  # on -> pedidos nao dividem pallet

    def test_modo_D_ignora_pedido_e_cliente(self):
        a = _item(cod='X', ped='P1', cnpj='C1', qtd=60, palt=120)
        b = _item(cod='X', ped='P2', cnpj='C2', qtd=60, palt=120)
        pallets, _ = montar_pallets([a, b], modo='D')
        assert len(pallets) == 1  # so produto: 120 caixas num pallet
        assert pallets[0].conteudo[0]['num_pedido'] == ''

    def test_pendencia_cadastro_incompleto(self):
        bom = _item(cod='OK', qtd=10)
        ruim = _item(cod='RUIM', qtd=10, palt=0)
        pallets, pend = montar_pallets([bom, ruim])
        assert len(pend) == 1 and pend[0]['cod_produto'] == 'RUIM'
        assert all('RUIM' not in [c['cod_produto'] for c in p.conteudo] for p in pallets)

    def test_to_dict_serializa(self):
        pallets, _ = montar_pallets([_item(qtd=64, palt=64)])
        d = pallets[0].to_dict()
        assert d['tipo'] == 'pallet'
        assert d['altura_total'] == 137.0
        assert d['merc_x'] == 104
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest tests/carteira/test_palletizacao_service.py::TestMontagem -v`
Expected: FAIL — `ImportError: cannot import name 'CaixaItem'`

- [ ] **Step 3: Write minimal implementation**

```python
# adicionar em app/carteira/services/palletizacao_service.py
from dataclasses import dataclass
from collections import defaultdict

_PALETA = ['#c0844a', '#4a90d9', '#5cb85c', '#d9534f',
           '#9b59b6', '#f0ad4e', '#16a085', '#e67e22']


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
    """conteudo_itens: [(CaixaItem, caixas)] — todos de mesma dimensao de caixa."""
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
    """First-fit: enche pallets ate `limite` caixas (frações de mesma dimensao)."""
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
    else:
        chave = {'A': lambda i: i.num_pedido,
                 'B': lambda i: i.cnpj,
                 'C': lambda i: '__GLOBAL__'}[modo]
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest tests/carteira/test_palletizacao_service.py -v`
Expected: PASS (todos, incl. Task 1)

- [ ] **Step 5: Commit**

```bash
git add app/carteira/services/palletizacao_service.py tests/carteira/test_palletizacao_service.py
git commit -m "feat(simulador): montagem de pallets (regras 1-3 + modos A-D + overbooking)"
```

---

## Task 3: Camada 1 — loader da Separação

**Files:**
- Modify: `app/carteira/services/palletizacao_service.py`
- Test: `tests/carteira/test_palletizacao_service.py`

**Interfaces:**
- Consumes: `montar_pallets`, `CaixaItem` (Task 2).
- Produces:
  - `montar_pallets_da_separacao(lote_id: str, modo='A', separado_por_pallet=False, overbooking_pct=0.0) -> dict` com `{'pallets': list[dict], 'pendencias': list[dict], 'resumo': {'n_pallets': int, 'peso_total': float}}`

- [ ] **Step 1: Write the failing test**

```python
# adicionar em tests/carteira/test_palletizacao_service.py
import uuid
from app.carteira.services.palletizacao_service import montar_pallets_da_separacao
from app.separacao.models import Separacao
from app.producao.models import CadastroPalletizacao


class TestLoader:
    def _cod(self):
        return f"TEST{uuid.uuid4().hex[:8]}"

    def test_carrega_separacao_e_monta(self, db):
        cod = self._cod()
        lote = f"LOTE_{uuid.uuid4().hex[:10]}"
        db.session.add(CadastroPalletizacao(
            cod_produto=cod, nome_produto='CONSERVA TESTE',
            palletizacao=64, peso_bruto=1.0,
            altura_cm=30.5, largura_cm=26, comprimento_cm=26, ativo=True))
        db.session.add(Separacao(
            separacao_lote_id=lote, num_pedido='PED1', cnpj_cpf='C1',
            cod_produto=cod, qtd_saldo=128))
        db.session.flush()

        out = montar_pallets_da_separacao(lote)
        assert out['resumo']['n_pallets'] == 2
        assert out['pendencias'] == []
        assert out['pallets'][0]['tipo'] == 'pallet'

    def test_separacao_vazia(self, db):
        out = montar_pallets_da_separacao(f"LOTE_INEXISTENTE_{uuid.uuid4().hex[:6]}")
        assert out['resumo']['n_pallets'] == 0
```

> Se `Separacao(...)` falhar por NOT NULL, preencher os campos obrigatórios mínimos observados no erro (ler `app/separacao/models.py` para os defaults) — não inventar.

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest tests/carteira/test_palletizacao_service.py::TestLoader -v`
Expected: FAIL — `ImportError: cannot import name 'montar_pallets_da_separacao'`

- [ ] **Step 3: Write minimal implementation**

```python
# adicionar em app/carteira/services/palletizacao_service.py
from sqlalchemy import and_
from app import db
from app.separacao.models import Separacao
from app.producao.models import CadastroPalletizacao


def _carregar_itens(lote_id):
    rows = (db.session.query(
                Separacao.num_pedido, Separacao.cnpj_cpf, Separacao.cod_produto,
                Separacao.qtd_saldo,
                CadastroPalletizacao.altura_cm, CadastroPalletizacao.largura_cm,
                CadastroPalletizacao.comprimento_cm,
                CadastroPalletizacao.palletizacao, CadastroPalletizacao.peso_bruto,
            )
            .outerjoin(CadastroPalletizacao,
                       and_(Separacao.cod_produto == CadastroPalletizacao.cod_produto,
                            CadastroPalletizacao.ativo.is_(True)))
            .filter(Separacao.separacao_lote_id == lote_id)
            .all())
    itens = []
    for r in rows:
        itens.append(CaixaItem(
            cod_produto=r.cod_produto, num_pedido=r.num_pedido or '',
            cnpj=r.cnpj_cpf or '', qtd=float(r.qtd_saldo or 0),
            largura_cm=float(r.largura_cm or 0),
            comprimento_cm=float(r.comprimento_cm or 0),
            altura_cm=float(r.altura_cm or 0),
            palletizacao=float(r.palletizacao or 0),
            peso_bruto=float(r.peso_bruto or 0)))
    return itens


def montar_pallets_da_separacao(lote_id, modo='A', separado_por_pallet=False,
                                overbooking_pct=0.0):
    itens = _carregar_itens(lote_id)
    pallets, pendencias = montar_pallets(itens, modo, separado_por_pallet,
                                         overbooking_pct)
    pallets_dict = [p.to_dict() for p in pallets]
    return {
        'pallets': pallets_dict,
        'pendencias': pendencias,
        'resumo': {
            'n_pallets': len(pallets_dict),
            'peso_total': round(sum(p['peso'] for p in pallets_dict), 2),
        },
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest tests/carteira/test_palletizacao_service.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/carteira/services/palletizacao_service.py tests/carteira/test_palletizacao_service.py
git commit -m "feat(simulador): loader de Separacao -> pallets (JOIN palletizacao + resumo)"
```

---

## Task 4: bin-packer — perfil multi-slab (regressão moto-only verde)

**Files:**
- Modify: `app/static/js/simulador-carga/bin-packer.js`
- Test: `app/static/js/simulador-carga/bin-packer.test.js`

**Interfaces:**
- Produces (internas ao IIFE):
  - cada item posicionado em `placed[i]` ganha `slabs: [{x,y,z,w,d,h}]` (volumes absolutos).
  - `itemSlabs(item, ori, x, y, z) -> [{x,y,z,w,d,h}]` — para moto (1 slab) usa o footprint da orientação.
  - `slabsColidem(slabsA, slabsB) -> bool` — sobreposição volumétrica entre quaisquer pares.
- Mantém API pública `BinPacker.pack` / `BinPacker.packOptimized` idêntica para listas de motos.

**Objetivo:** introduzir a infraestrutura de slabs SEM alterar o resultado para motos. Os testes existentes (CASO 1/2/estabilidade) devem continuar verdes.

- [ ] **Step 1: Write the failing test**

```js
// adicionar em app/static/js/simulador-carga/bin-packer.test.js (antes do rodapé de exit)
test('multi-slab: moto posicionada expoe slabs absolutos coerentes', () => {
  const r = BinPacker.pack({ w: 200, d: 200, h: 200 },
    [{ id: 1, nome: 'M', comprimento: 100, largura: 40, altura: 50, peso_medio: 100, qty: 1 }]);
  assert(r.stats.posicionadas === 1, 'deveria posicionar 1');
  const p = r.placed[0];
  assert(Array.isArray(p.slabs) && p.slabs.length === 1, 'moto tem 1 slab');
  const s = p.slabs[0];
  assert(s.w === p.w && s.d === p.d && s.h === p.h, 'slab = footprint da moto');
  assert(s.x === p.x && s.y === p.y && s.z === p.z, 'slab na posicao da moto');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node app/static/js/simulador-carga/bin-packer.test.js`
Expected: FAIL — `p.slabs` undefined.

- [ ] **Step 3: Write minimal implementation**

Em `bin-packer.js`, adicionar os helpers (após `getOrientations`, l.233) e popular `slabs` no objeto posicionado em `packItems` (l.147-152):

```js
// Slabs absolutos de um item numa dada orientacao/posicao.
// Moto = 1 slab (footprint da orientacao). Pallet sobrescreve (Task 5).
function itemSlabs(item, ori, x, y, z) {
  if (item.tipo === 'pallet') return palletSlabs(item, x, y, z); // def. na Task 5
  return [{ x: x, y: y, z: z, w: ori.ow, d: ori.od, h: ori.oh }];
}

// Dois conjuntos de slabs colidem se algum par se sobrepoe nos 3 eixos.
function slabsColidem(a, b) {
  for (var i = 0; i < a.length; i++) {
    for (var j = 0; j < b.length; j++) {
      var s = a[i], t = b[j];
      if (s.x < t.x + t.w - 0.1 && s.x + s.w > t.x + 0.1 &&
          s.y < t.y + t.h - 0.1 && s.y + s.h > t.y + 0.1 &&
          s.z < t.z + t.d - 0.1 && s.z + s.d > t.z + 0.1) {
        return true;
      }
    }
  }
  return false;
}
```

Alterar a assinatura de `findBestFit` para receber `item` e gravar os slabs do candidato escolhido. Em `packItems` (l.144), chamar `findBestFit(item, getOrientations(item), freeSpaces, bay, placed, opt)`. Dentro de `findBestFit`, no bloco que monta `best` (l.285):

```js
best = {
  x: sp.x, y: sp.y, z: sp.z,
  ow: ori.ow, od: ori.od, oh: ori.oh,
  orientIdx: ori.idx,
  slabs: itemSlabs(item, ori, sp.x, sp.y, sp.z),  // <-- novo
};
```

E ao montar `p` em `packItems` (l.147), acrescentar `slabs: best.slabs`:

```js
var p = {
  moto: item,
  x: best.x, y: best.y, z: best.z,
  w: best.ow, d: best.od, h: best.oh,
  orientacao: best.orientIdx,
  slabs: best.slabs,            // <-- novo
};
```

- [ ] **Step 4: Run test to verify it passes + regressão**

Run: `node app/static/js/simulador-carga/bin-packer.test.js`
Expected: PASS — o novo teste passa E os CASO 1/2/estabilidade continuam verdes (exit 0).

- [ ] **Step 5: Commit**

```bash
git add app/static/js/simulador-carga/bin-packer.js app/static/js/simulador-carga/bin-packer.test.js
git commit -m "feat(simulador): infraestrutura multi-slab no bin-packer (moto = 1 slab)"
```

---

## Task 5: bin-packer — item pallet (orientação única + caminho crítico)

**Files:**
- Modify: `app/static/js/simulador-carga/bin-packer.js`
- Test: `app/static/js/simulador-carga/bin-packer.test.js`

**Interfaces:**
- Consumes: `itemSlabs`, `slabsColidem` (Task 4).
- Produces:
  - `palletSlabs(item, x, y, z) -> [estrado, coluna]` — estrado `100×120×15` no canto; coluna `merc_x×merc_y` centralizada (offset `(100-merc_x)/2, (120-merc_y)/2`, podendo ser negativo) de `y+15` a `y+altura_total`.
  - `getOrientations` retorna **1** orientação quando `item.tipo === 'pallet'`.
  - `findBestFit` valida colisão dos slabs do candidato contra `placed[*].slabs` (além do baú).
  - `expandItems` propaga `tipo`, `base_x`, `base_y`, `altura_estrado`, `merc_x`, `merc_y`, `altura_merc`, `altura_total`, `grupo` quando presentes.

- [ ] **Step 1: Write the failing test**

```js
// adicionar em bin-packer.test.js
function pallet(mx, my, altMerc, id) {
  return { tipo: 'pallet', id: id, nome: id,
           base_x: 100, base_y: 120, altura_estrado: 15,
           merc_x: mx, merc_y: my, altura_merc: altMerc,
           altura_total: 15 + altMerc, comprimento: 100, largura: 120, altura: 15 + altMerc,
           peso_medio: 100, qty: 1 };
}

test('caminho critico: pallets 104 e 90 cabem encostados (media 97 < 100)', () => {
  const r = BinPacker.pack({ w: 200, d: 130, h: 250 },
    [pallet(104, 104, 100, 'A'), pallet(90, 90, 100, 'B')]);
  assert(r.stats.posicionadas === 2, `esperava 2, veio ${r.stats.posicionadas}`);
});

test('caminho critico: dois pallets 104 NAO cabem encostados em bau de 200', () => {
  const r = BinPacker.pack({ w: 200, d: 130, h: 250 },
    [pallet(104, 104, 100, 'A'), pallet(104, 104, 100, 'B')]);
  assert(r.stats.posicionadas === 1, `esperava 1, veio ${r.stats.posicionadas}`);
});

test('pallet tem orientacao unica (estrado no chao) e 2 slabs', () => {
  const r = BinPacker.pack({ w: 200, d: 200, h: 250 }, [pallet(104, 104, 100, 'A')]);
  const p = r.placed[0];
  assert(p.slabs.length === 2, '2 slabs (estrado + coluna)');
  assert(p.slabs[0].y === 0 && p.slabs[0].h === 15, 'estrado em Y 0..15');
  assert(p.slabs[1].y === 15, 'coluna comeca em Y=15');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node app/static/js/simulador-carga/bin-packer.test.js`
Expected: FAIL — pallets tratados como motos (4 orientações, sem coluna), contagens erradas.

- [ ] **Step 3: Write minimal implementation**

Em `bin-packer.js`:

```js
// Slabs de um pallet: estrado (canto) + coluna de mercadoria (centralizada).
function palletSlabs(item, x, y, z) {
  var bx = item.base_x, by = item.base_y, est = item.altura_estrado;
  var mx = item.merc_x, my = item.merc_y, alt = item.altura_total;
  var ox = (bx - mx) / 2, oy = (by - my) / 2; // offset (pode ser negativo)
  return [
    { x: x, y: y, z: z, w: bx, d: by, h: est },                       // estrado
    { x: x + ox, y: y + est, z: z + oy, w: mx, d: my, h: alt - est }, // coluna
  ];
}
```

`getOrientations` (l.225) — pallet não rotaciona, base sempre no chão:

```js
function getOrientations(item) {
  if (item.tipo === 'pallet') {
    return [{ ow: item.base_x, od: item.base_y, oh: item.altura_total, idx: 0 }];
  }
  var C = item.comprimento, L = item.largura, A = item.altura;
  return [
    { ow: C, od: L, oh: A, idx: 0 },
    { ow: C, od: A, oh: L, idx: 1 },
    { ow: L, od: C, oh: A, idx: 2 },
    { ow: A, od: C, oh: L, idx: 3 },
  ];
}
```

`findBestFit` — após validar fit no freeSpace e apoio, validar colisão real dos slabs contra `placed` e baú (é o que captura o caminho crítico: a coluna pode invadir o ar sobre o estrado vizinho, mas não pode atravessar outra coluna nem o baú). Inserir antes da comparação Bottom-Left:

```js
var cand = itemSlabs(item, ori, sp.x, sp.y, sp.z);
var foraDoBau = false;
for (var c = 0; c < cand.length; c++) {
  var sc = cand[c];
  if (sc.x < -0.1 || sc.z < -0.1 ||
      sc.x + sc.w > bay.w + 0.1 || sc.z + sc.d > bay.d + 0.1 ||
      sc.y + sc.h > bay.h + 0.1) { foraDoBau = true; break; }
}
if (foraDoBau) continue;
var colide = false;
for (var pi = 0; pi < placed.length; pi++) {
  if (slabsColidem(cand, placed[pi].slabs)) { colide = true; break; }
}
if (colide) continue;
```

`expandItems` (l.184) propaga os campos de pallet:

```js
function expandItems(motoList) {
  var items = [];
  for (var i = 0; i < motoList.length; i++) {
    var m = motoList[i];
    var qty = (m.qty == null) ? 1 : m.qty;
    for (var q = 0; q < qty; q++) {
      var it = {
        id: m.id, nome: m.nome,
        comprimento: m.comprimento, largura: m.largura, altura: m.altura,
        peso_medio: m.peso_medio || 0, color: m.color || '#4a90d9',
        volume: (m.comprimento || 0) * (m.largura || 0) * (m.altura || 0),
        tipo: m.tipo || 'moto',
      };
      if (m.tipo === 'pallet') {
        it.base_x = m.base_x; it.base_y = m.base_y;
        it.altura_estrado = m.altura_estrado;
        it.merc_x = m.merc_x; it.merc_y = m.merc_y;
        it.altura_merc = m.altura_merc; it.altura_total = m.altura_total;
        it.altura = m.altura_total; it.comprimento = m.base_x; it.largura = m.base_y;
        it.volume = m.base_x * m.base_y * m.altura_total;
        it.grupo = m.grupo;
      }
      items.push(it);
    }
  }
  return items;
}
```

> O `subtractBox` (l.443) deve subtrair **cada slab** do candidato. No `packItems`, trocar `freeSpaces = subtractBox(freeSpaces, p)` por: `for (var k=0;k<p.slabs.length;k++){ freeSpaces = subtractBox(freeSpaces, p.slabs[k]); }`. `subtractBox` já opera sobre `{x,y,z,w,d,h}` (forma do slab).

- [ ] **Step 4: Run test to verify it passes + regressão**

Run: `node app/static/js/simulador-carga/bin-packer.test.js`
Expected: PASS — novos casos verdes E motos (CASO 1/2/estabilidade/Task 4) continuam verdes.

- [ ] **Step 5: Commit**

```bash
git add app/static/js/simulador-carga/bin-packer.js app/static/js/simulador-carga/bin-packer.test.js
git commit -m "feat(simulador): item pallet com caminho critico (multi-slab + colisao por altura)"
```

---

## Task 6: bin-packer — 2 fases (Nacom embaixo) + pallet sobre pallet

**Files:**
- Modify: `app/static/js/simulador-carga/bin-packer.js`
- Test: `app/static/js/simulador-carga/bin-packer.test.js`

**Interfaces:**
- Consumes: tudo de Task 4–5.
- Produces:
  - `BinPacker.pack(bay, items, options)` aceita lista mista (`tipo` 'pallet'|'moto'): empacota **todos os pallets primeiro** (fase 1), depois as motos no `freeSpaces` remanescente (fase 2). Regressão: lista só-moto = comportamento atual.
  - `options.palletSobrePallet` (bool, default `false`): fase 1 permite `Y>0` para pallets só quando `true`.
  - helpers DRY: `buildResult(bay, placed, rejected, total) -> {placed,rejected,bay,stats}`; `packItemsInto(bay, items, opt, freeSpaces0, placed0, phase)`.

- [ ] **Step 1: Write the failing test**

```js
// adicionar em bin-packer.test.js (reusa helper pallet() da Task 5)
test('Nacom embaixo: nenhuma moto fica sob um pallet', () => {
  const bay = { w: 300, d: 130, h: 250 };
  const items = [
    pallet(90, 110, 120, 'P1'),
    { id: 2, nome: 'M', tipo: 'moto', comprimento: 80, largura: 40, altura: 50, peso_medio: 150, qty: 4 },
  ];
  const r = BinPacker.pack(bay, items);
  const pallets = r.placed.filter(p => p.moto.tipo === 'pallet');
  const motos = r.placed.filter(p => p.moto.tipo !== 'pallet');
  motos.forEach(m => {
    pallets.forEach(p => {
      const sobrepoeXZ = (p.x < m.x + m.w && p.x + p.w > m.x &&
                          p.z < m.z + m.d && p.z + p.d > m.z);
      assert(!(sobrepoeXZ && p.y >= m.y + m.h - 0.1),
        'pallet nao pode estar acima de uma moto');
    });
  });
});

test('pallet sobre pallet: OFF mantem todos no chao', () => {
  const bay = { w: 110, d: 130, h: 400 };
  const r = BinPacker.pack(bay, [pallet(90, 110, 120, 'A'), pallet(90, 110, 120, 'B')]);
  // base 100x120 so cabe 1 no chao desse bau estreito; sem empilhar -> 1
  assert(r.stats.posicionadas === 1, `OFF esperava 1, veio ${r.stats.posicionadas}`);
});

test('pallet sobre pallet: ON empilha (+15cm estrado)', () => {
  const bay = { w: 110, d: 130, h: 400 };
  const r = BinPacker.pack(bay, [pallet(90, 110, 120, 'A'), pallet(90, 110, 120, 'B')],
    { palletSobrePallet: true, minSupport: 0.5, maxOverhang: 20, maxGap: 60 });
  assert(r.stats.posicionadas === 2, `ON esperava 2, veio ${r.stats.posicionadas}`);
  const ys = r.placed.map(p => p.y).sort((a, b) => a - b);
  assert(ys[0] === 0, 'um no chao');
  assert(ys[1] >= 135 - 0.1, 'outro empilhado acima do topo (15+120)');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node app/static/js/simulador-carga/bin-packer.test.js`
Expected: FAIL — hoje `pack` trata tudo numa passada só; pallets podem empilhar sem flag e motos podem cair sob pallets.

- [ ] **Step 3: Write minimal implementation**

Extrair `buildResult` (DRY, a partir do bloco de stats de `packItems`, l.160-180), fazer `packItemsInto` retornar `freeSpaces`, e reescrever `pack` (l.53) em 2 fases:

```js
function buildResult(bay, placed, rejected, total) {
  var bayVol = bay.w * bay.d * bay.h;
  var usedVol = 0, totalPeso = 0;
  for (var j = 0; j < placed.length; j++) {
    usedVol += placed[j].w * placed[j].d * placed[j].h;
    totalPeso += placed[j].moto.peso_medio || 0;
  }
  return {
    placed: placed, rejected: rejected, bay: bay,
    stats: {
      total: total, posicionadas: placed.length, rejeitadas: rejected.length,
      volumeOcupado: usedVol, volumeTotal: bayVol,
      percentualOcupacao: bayVol > 0 ? Math.round((usedVol / bayVol) * 100) : 0,
      pesoTotal: Math.round(totalPeso * 100) / 100,
    },
  };
}

function pack(bay, lista, options) {
  var opt = normalizeOptions(options);
  var all = expandItems(lista);
  if (all.length > MAX_ITEMS) all = all.slice(0, MAX_ITEMS);
  var pallets = all.filter(function (i) { return i.tipo === 'pallet'; });
  var motos = sortByLayingHeight(all.filter(function (i) { return i.tipo !== 'pallet'; }));

  // Fase 1: pallets (orientacao unica). So Y=0, salvo palletSobrePallet.
  var res1 = packItemsInto(bay, pallets, opt,
    [{ x: 0, y: 0, z: 0, w: bay.w, d: bay.d, h: bay.h }], [],
    { onlyFloor: !opt.palletSobrePallet });

  // Fase 2: motos no espaco livre remanescente; placed ja tem os pallets.
  var res2 = packItemsInto(bay, motos, opt, res1.freeSpaces, res1.placed.slice(), {});

  var placed = res1.placedNew.concat(res2.placedNew);
  var rejected = res1.rejected.concat(res2.rejected);
  return buildResult(bay, placed, rejected, all.length);
}
```

`packItemsInto(bay, items, opt, freeSpaces0, placed0, phase)` = o loop atual de `packItems`, começando de `freeSpaces0`/`placed0`, retornando `{placedNew, rejected, freeSpaces}` (placedNew = só os adicionados nesta fase, para o concat não duplicar os pallets de placed0). `phase.onlyFloor`: em `findBestFit`, rejeitar `sp.y > 0.1` quando `phase.onlyFloor` (repassar `phase` para `findBestFit` via parâmetro).

Detalhes:
- `normalizeOptions` inclui `palletSobrePallet: !!o.palletSobrePallet`.
- Manter `packItems` antigo como wrapper para `packOptimized`: `function packItems(bay, items, opt){ var r = packItemsInto(bay, items, opt, [{x:0,y:0,z:0,w:bay.w,d:bay.d,h:bay.h}], [], {}); return buildResult(bay, r.placedNew, r.rejected, items.length); }`.
- A regra "Nacom embaixo" sai de graça: pallets já em `placed0` (fase 2) ocupam o fundo-baixo (Bottom-Left-Back na fase 1), então nenhuma moto fica sob um pallet.
- `packOptimized` (l.72): para a v1, aplica SA só sobre a ordem das motos; pallets entram na ordem de chegada (grupos juntos). Documentar no header do arquivo.

- [ ] **Step 4: Run test to verify it passes + regressão completa**

Run: `node app/static/js/simulador-carga/bin-packer.test.js`
Expected: PASS — todos os casos (motos, pallet, caminho crítico, Nacom embaixo, pallet-sobre-pallet) verdes.

- [ ] **Step 5: Commit**

```bash
git add app/static/js/simulador-carga/bin-packer.js app/static/js/simulador-carga/bin-packer.test.js
git commit -m "feat(simulador): empacotamento em 2 fases (Nacom embaixo) + pallet sobre pallet"
```

---

## Task 7: API — endpoint pallets-por-separacao

**Files:**
- Modify: `app/carvia/routes/simulador_routes.py`
- Test: `tests/carteira/test_palletizacao_service.py` (classe nova de rota, usa `client`)

**Interfaces:**
- Consumes: `montar_pallets_da_separacao` (Task 3).
- Produces: `GET /carvia/api/simulador-carga/pallets-por-separacao?lote=<id>&modo=A&separado=0&overbooking=0` → JSON `{'pallets':[...], 'pendencias':[...], 'resumo':{...}}`.

- [ ] **Step 1: Write the failing test**

```python
# adicionar em tests/carteira/test_palletizacao_service.py
class TestEndpoint:
    def test_pallets_por_separacao_ok(self, client, db):
        import uuid
        from app.separacao.models import Separacao
        from app.producao.models import CadastroPalletizacao
        cod = f"TEST{uuid.uuid4().hex[:8]}"
        lote = f"LOTE_{uuid.uuid4().hex[:10]}"
        db.session.add(CadastroPalletizacao(
            cod_produto=cod, nome_produto='X', palletizacao=64, peso_bruto=1.0,
            altura_cm=30.5, largura_cm=26, comprimento_cm=26, ativo=True))
        db.session.add(Separacao(separacao_lote_id=lote, num_pedido='P1',
                                 cnpj_cpf='C1', cod_produto=cod, qtd_saldo=128))
        db.session.flush()
        resp = client.get(f'/carvia/api/simulador-carga/pallets-por-separacao?lote={lote}')
        assert resp.status_code == 200
        data = resp.get_json()
        assert data['resumo']['n_pallets'] == 2

    def test_pallets_por_separacao_sem_lote(self, client):
        resp = client.get('/carvia/api/simulador-carga/pallets-por-separacao')
        assert resp.status_code == 400
```

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest tests/carteira/test_palletizacao_service.py::TestEndpoint -v`
Expected: FAIL — 404 (rota inexistente).

- [ ] **Step 3: Write minimal implementation**

Em `app/carvia/routes/simulador_routes.py`, dentro de `register_simulador_routes(bp)` (l.20), adicionar:

```python
@bp.route('/api/simulador-carga/pallets-por-separacao')
def api_simulador_pallets_por_separacao():
    from app.carteira.services.palletizacao_service import montar_pallets_da_separacao
    lote = request.args.get('lote', type=str)
    if not lote:
        return jsonify({'erro': 'parametro lote obrigatorio'}), 400
    modo = request.args.get('modo', 'A', type=str)
    separado = request.args.get('separado', '0') in ('1', 'true', 'True')
    try:
        overbooking = float(request.args.get('overbooking', 0) or 0)
    except (TypeError, ValueError):
        overbooking = 0.0
    out = montar_pallets_da_separacao(lote, modo=modo,
                                      separado_por_pallet=separado,
                                      overbooking_pct=overbooking)
    return jsonify(out)
```

> `request` e `jsonify` já são importados no topo de `simulador_routes.py` (usados pelos endpoints existentes). Se faltar, adicionar `from flask import request, jsonify`.

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest tests/carteira/test_palletizacao_service.py::TestEndpoint -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/carvia/routes/simulador_routes.py tests/carteira/test_palletizacao_service.py
git commit -m "feat(simulador): endpoint pallets-por-separacao (modo/overbooking/separado)"
```

---

## Task 8: API — Nacom no modo embarque misto

**Files:**
- Modify: `app/carvia/routes/simulador_routes.py:189-219` (`_resolver_dados_embarque`)
- Test: `tests/carteira/test_palletizacao_service.py`

**Interfaces:**
- Consumes: `montar_pallets_da_separacao` (Task 3), itens ativos já carregados em `_resolver_dados_embarque`.
- Produces: o dict de init do modo embarque passa a conter `pallets: [...]` além de `motos: [...]` e `veiculo`.

- [ ] **Step 1: Write the failing test**

```python
# adicionar em tests/carteira/test_palletizacao_service.py
class TestEmbarqueMisto:
    def test_resolver_inclui_pallets_nacom(self, db):
        import uuid
        from app.embarques.models import Embarque, EmbarqueItem
        from app.separacao.models import Separacao
        from app.producao.models import CadastroPalletizacao
        from app.veiculos.models import Veiculo
        from app.carvia.routes.simulador_routes import _resolver_dados_embarque

        cod = f"TEST{uuid.uuid4().hex[:8]}"
        lote = f"LOTE_{uuid.uuid4().hex[:10]}"
        db.session.add(Veiculo(nome='TOCO', peso_maximo=6000,
                               comprimento_bau=630, largura_bau=240, altura_bau=230))
        db.session.add(CadastroPalletizacao(
            cod_produto=cod, nome_produto='X', palletizacao=64, peso_bruto=1.0,
            altura_cm=30.5, largura_cm=26, comprimento_cm=26, ativo=True))
        emb = Embarque(numero=int(uuid.uuid4().int % 100000), modalidade='TOCO', status='ativo')
        db.session.add(emb)
        db.session.flush()
        db.session.add(EmbarqueItem(embarque_id=emb.id, separacao_lote_id=lote, status='ativo'))
        db.session.add(Separacao(separacao_lote_id=lote, num_pedido='P1',
                                 cnpj_cpf='C1', cod_produto=cod, qtd_saldo=128))
        db.session.flush()

        dados = _resolver_dados_embarque(emb)
        assert 'pallets' in dados
        assert len(dados['pallets']) == 2
```

> Ler `app/embarques/models.py` para os campos NOT NULL de `Embarque`/`EmbarqueItem` (ex.: `numero`, `status`) e ajustar o construtor — não inventar nomes.

- [ ] **Step 2: Run test to verify it fails**

Run: `source .venv/bin/activate && pytest tests/carteira/test_palletizacao_service.py::TestEmbarqueMisto -v`
Expected: FAIL — `KeyError: 'pallets'` (ou ausência da chave).

- [ ] **Step 3: Write minimal implementation**

Em `_resolver_dados_embarque` (l.189), após resolver motos e antes do return, coletar os lotes Nacom (`LOTE_*`) dos `EmbarqueItem` ativos já carregados (`itens_ativos`, l.200-207) e montar pallets de cada um:

```python
from app.carteira.services.palletizacao_service import montar_pallets_da_separacao
lotes_nacom = {it.separacao_lote_id for it in itens_ativos
               if (it.separacao_lote_id or '').startswith('LOTE_')}
pallets = []
for lote in lotes_nacom:
    out = montar_pallets_da_separacao(lote)  # modo A default; flags vêm da UI no recalculo
    pallets.extend(out['pallets'])
# acrescentar 'pallets': pallets ao dict de retorno existente
```

> Reusar `itens_ativos`; não refazer a query. Acrescentar a chave `'pallets'` ao dict já retornado.

- [ ] **Step 4: Run test to verify it passes**

Run: `source .venv/bin/activate && pytest tests/carteira/test_palletizacao_service.py::TestEmbarqueMisto -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/carvia/routes/simulador_routes.py tests/carteira/test_palletizacao_service.py
git commit -m "feat(simulador): modo embarque misto inclui pallets Nacom (LOTE_*)"
```

---

## Task 9: Render — estrado + coluna no Three.js

**Files:**
- Modify: `app/static/js/simulador-carga/carga-renderer.js`
- Modify: `app/static/css/modules/_simulador_carga.css`

**Interfaces:**
- Consumes: `result.placed[i]` onde `p.moto.tipo === 'pallet'` traz `base_x/base_y/altura_estrado/merc_x/merc_y/altura_total/color`.
- Produces: cada pallet renderizado como 2 `BoxGeometry` (estrado cinza PBR + coluna colorida centralizada). Motos inalteradas.

> **Verificação manual** (render visual não tem teste automatizado).

- [ ] **Step 1: Extrair `addBox` e bifurcar por tipo**

Em `carga-renderer.js`, no laço que cria as caixas posicionadas (motos, ~l.213-248), extrair a criação de `BoxGeometry`+`MeshPhongMaterial`+wireframe+label numa função local `addBox(x,y,z,w,d,h,color,label)` (DRY) e bifurcar:

```js
placed.forEach(function (p) {
  if (p.moto && p.moto.tipo === 'pallet') {
    addBox(p.x, p.y, p.z, p.moto.base_x, p.moto.base_y, p.moto.altura_estrado,
           '#9e9e9e', p.moto.nome);                     // estrado PBR cinza
    var ox = (p.moto.base_x - p.moto.merc_x) / 2;
    var oy = (p.moto.base_y - p.moto.merc_y) / 2;
    addBox(p.x + ox, p.y + p.moto.altura_estrado, p.z + oy,
           p.moto.merc_x, p.moto.merc_y, p.moto.altura_total - p.moto.altura_estrado,
           p.moto.color || '#c0844a', null);            // coluna de mercadoria
  } else {
    addBox(p.x, p.y, p.z, p.w, p.d, p.h, p.moto.color, p.moto.nome);  // moto (atual)
  }
});
```

- [ ] **Step 2: Verificação manual**

Run: `source .venv/bin/activate && python run.py` (porta 5000). Abrir `/carvia/simulador-carga` (a UI completa vem na Task 10; aqui valide via init de embarque misto da Task 8 ou um stub no console).
Expected: estrado cinza no chão + bloco colorido por cima, coluna podendo exceder levemente o estrado.

- [ ] **Step 3: Commit**

```bash
git add app/static/js/simulador-carga/carga-renderer.js app/static/css/modules/_simulador_carga.css
git commit -m "feat(simulador): render de pallet (estrado PBR + coluna de mercadoria)"
```

---

## Task 10: UI — flags, merge pallets+motos, seletor de separação

**Files:**
- Create: `app/templates/carvia/simulador/_pallet_controls.html`
- Modify: `app/static/js/simulador-carga/simulador-ui.js`
- Modify: `app/templates/carvia/simulador/simulador_livre.html`, `simulador_embarque.html`
- Modify: `app/static/css/modules/_simulador_carga.css`

**Interfaces:**
- Consumes: endpoint `pallets-por-separacao` (Task 7), init com `pallets` (Task 8), `BinPacker.pack`/`packOptimized` mista (Task 6), render de pallet (Task 9).
- Produces: controles de flag (modo A–D, separado por pallet, overbooking, pallet sobre pallet), merge de `pallets + motos` numa única lista para o packer, legenda por grupo, lista de pendências.

> **Verificação manual** (UI).

- [ ] **Step 1: Criar partial de flags**

```html
<!-- app/templates/carvia/simulador/_pallet_controls.html -->
<fieldset class="sim-pallet-controls">
  <legend>Conservas Nacom</legend>
  <label>Agrupamento
    <select id="palletModo">
      <option value="A" selected>A — por pedido</option>
      <option value="B">B — por CNPJ</option>
      <option value="C">C — remontagem</option>
      <option value="D">D — lote (só produto)</option>
    </select>
  </label>
  <label><input type="checkbox" id="palletSeparado"> Separado por pallet (B/C)</label>
  <label><input type="checkbox" id="palletOverbooking"> Overbooking
    <input type="range" id="palletOverbookingPct" min="0" max="50" value="0">
    <span id="palletOverbookingVal">0%</span>
  </label>
  <label><input type="checkbox" id="palletSobrePallet"> Pallet sobre pallet</label>
  <div id="palletPendencias" class="sim-pendencias"></div>
</fieldset>
```

- [ ] **Step 2: Ligar flags + merge no simulador-ui.js**

Em `simulador-ui.js`: ao montar a lista para o packer, concatenar `pallets` (do init ou do endpoint) com as `motos`, e passar `palletSobrePallet`. Ao mudar qualquer flag, refazer fetch e re-renderizar. Reusar os helpers existentes (`el()`, sliders, `renderer`, `bay`, mapa de cores).

```js
function montarListaItens() {
  return [].concat(window.__pallets || [], motosSelecionadas());
}
function reempacotar() {
  var opt = Object.assign({}, sliders(), { palletSobrePallet: el('palletSobrePallet').checked });
  var res = BinPacker.packOptimized(bay, montarListaItens(), opt);
  renderer.render(res, bay, colorMap);
  atualizarLegendaPorGrupo(res); // agrupa pallets por p.moto.grupo
}
async function recarregarPallets() {
  if (!window.__loteSeparacao) { reempacotar(); return; }
  const q = new URLSearchParams({ lote: window.__loteSeparacao,
    modo: el('palletModo').value,
    separado: el('palletSeparado').checked ? '1' : '0',
    overbooking: (el('palletOverbookingPct').value / 100) });
  const r = await fetch('/carvia/api/simulador-carga/pallets-por-separacao?' + q);
  const data = await r.json();
  window.__pallets = data.pallets;
  mostrarPendencias(data.pendencias);
  reempacotar();
}
// ligar change/input das flags a recarregarPallets; slider atualiza #palletOverbookingVal
```

- [ ] **Step 3: Incluir partial + seletor de separação nos templates**

Em `simulador_livre.html` e `simulador_embarque.html`, incluir `{% include 'carvia/simulador/_pallet_controls.html' %}` na sidebar. No modo livre, adicionar um campo para informar/buscar o `separacao_lote_id` (set `window.__loteSeparacao` e chamar `recarregarPallets`). No modo embarque, `window.__pallets` vem do init (Task 8).

> Nota (modo embarque com N lotes): para a v1, ao mudar flag no modo embarque, manter as flags fixas no default (modo A) OU criar endpoint `pallets-por-embarque` que re-monta todos os lotes com as flags. Decidir na execução conforme custo; se mantiver fixo, desabilitar os controles de flag no modo embarque e documentar.

- [ ] **Step 4: Verificação manual completa**

Run: `source .venv/bin/activate && python run.py`. Abrir `/carvia/simulador-carga`, informar um `separacao_lote_id` real, alternar modos A–D e flags.
Expected: pallets montam/recalculam; render mostra estrado+coluna no piso e motos por cima; legenda por grupo; pendências listadas quando há produto sem cadastro.

- [ ] **Step 5: Commit**

```bash
git add app/templates/carvia/simulador/ app/static/js/simulador-carga/simulador-ui.js app/static/css/modules/_simulador_carga.css
git commit -m "feat(simulador): UI de conservas (flags A-D, overbooking, pallet sobre pallet, merge+legenda)"
```

---

## Self-Review

**1. Spec coverage:**
- Geometria PBR + folga 5cm (lastro com excesso) → Task 1 ✓
- Regras 1–3 (fechados, frações por dimensão) + overbooking 50% → Task 2 ✓
- Modos A–D → Task 2 ✓
- Fonte = Separação (loader + pendências) → Task 3 ✓
- Caminho crítico no arranjo (multi-slab, colisão por altura) → Task 4–5 ✓
- Nacom embaixo + pallet sobre pallet → Task 6 ✓
- API (endpoint + embarque misto) → Task 7–8 ✓
- Render estrado+coluna → Task 9 ✓
- Flags na tela + merge + legenda + pendências → Task 10 ✓
- Sem migration → respeitado (nenhuma task cria migration) ✓

**2. Placeholder scan:** sem "TBD/TODO". As notas sobre ler `models.py` para campos NOT NULL e sobre reuso de helpers são instruções concretas de verificação, não placeholders de lógica. Código de teste e implementação presentes em todos os steps de código.

**3. Type consistency:** `CaixaItem`/`Pallet` (Task 2) usados consistentemente em Task 3/7/8. `to_dict()` emite `tipo:'pallet'` + `base_x/base_y/altura_estrado/merc_x/merc_y/altura_total/color/grupo`, exatamente os campos lidos por `expandItems`/`palletSlabs` (Task 5) e pelo render (Task 9). `slabs`/`itemSlabs`/`slabsColidem`/`palletSlabs` nomeados igual em Task 4→6. `pack(bay, items, options)` com `tipo` por item, consistente entre Task 6 e Task 10. `buildResult`/`packItemsInto` introduzidos na Task 6 e usados pelo wrapper `packItems`.

**Riscos conhecidos (do spec):** complexidade do multi-slab (mitigada por TDD: caminho crítico P1/P2 + regressão moto-only); recalculo de flags no modo embarque com N lotes (Task 10, nota de fallback); `MAX_ITEMS=200` no modo D (o `resumo`/UI reportam contagem).
