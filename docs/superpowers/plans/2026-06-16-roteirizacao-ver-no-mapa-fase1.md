<!-- doc:meta
tipo: scratch
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-16
-->

# Roteirizacao "Ver no Mapa" — Fase 1 (Fundacao de custo + motor) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Substituir o custo de rota hardcoded por custo parametrico real vindo da tabela `veiculos`, com selecao de veiculo multidimensional, flag de volta, dias de viagem e um motor de roteirizacao que supera o limite de 25 paradas — tudo exposto na tela do mapa.

**Architecture:** Novo `app/carteira/services/roteirizacao_service.py` concentra calculo de custo (funcao pura), selecao de veiculo e um motor de otimizacao com abstracao de backend (Directions+chunking funcional agora; Route Optimization plugavel depois). `mapa_service.py` mantem geocoding/agrupamento. Uma API nova `/api/rota/otimizar` orquestra. Tabela `veiculos` ganha 8 colunas via migration idempotente.

**Tech Stack:** Flask 3.1 + SQLAlchemy 2.0 (PostgreSQL), Google Maps APIs (Directions/Geocoding via `requests`), Jinja2 + jQuery + Google Maps JS API, pytest (PostgreSQL local).

## Global Constraints

- Migration de COLUNA nova = par `.sql` + `.py` idempotente em `scripts/migrations/` (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`). Flask-Migrate esta CONGELADO — NUNCA `flask db migrate`.
- Scripts em `scripts/migrations/` precisam de `sys.path.insert(0, <raiz>)` antes de importar `app`.
- Fonte de custo = **tipo** de veiculo (tabela `veiculos`), nunca veiculo fisico nesta fase.
- Composicao do custo = combustivel + motorista/dia + fixo/dia + depreciacao(/30) + pedagio.
- Datas/timestamps via `app/utils/timezone.py` (Brasil naive) — nunca `datetime.now()` cru.
- Testes rodam com PostgreSQL local (fixtures `db`, `client`; `LOGIN_DISABLED=True`, CSRF off). Rodar pytest **da raiz**.
- Campos de custo no banco = `Numeric`; calculo em runtime usa float + `round(x, 2)` (consistente com `mapa_service.py`).
- Schema JSON da tabela alterada = atualizar `.claude/skills/consultando-sql/schemas/tables/veiculos.json` na mesma task.

---

### Task 1: Migration — ampliar `veiculos` com 8 colunas de custo/capacidade

**Files:**
- Create: `scripts/migrations/2026_06_16_veiculo_parametros_custo.py`
- Create: `scripts/migrations/2026_06_16_veiculo_parametros_custo.sql`
- Modify: `app/veiculos/models.py:6-26`
- Modify: `.claude/skills/consultando-sql/schemas/tables/veiculos.json`
- Test: `tests/veiculos/test_migration_parametros_custo.py`

**Interfaces:**
- Produces: model `Veiculo` com atributos `custo_km`, `custo_motorista_dia`, `custo_fixo_dia`, `depreciacao_mensal`, `capacidade_pallets`, `capacidade_m3`, `velocidade_media_kmh`, `ativo` (default True).

- [ ] **Step 1: Escrever o teste que falha** — `tests/veiculos/test_migration_parametros_custo.py`

```python
from sqlalchemy import inspect
from app import db
from app.veiculos.models import Veiculo


def test_veiculo_tem_colunas_de_custo(db):
    cols = {c['name'] for c in inspect(db.engine).get_columns('veiculos')}
    esperadas = {
        'custo_km', 'custo_motorista_dia', 'custo_fixo_dia', 'depreciacao_mensal',
        'capacidade_pallets', 'capacidade_m3', 'velocidade_media_kmh', 'ativo',
    }
    assert esperadas.issubset(cols), f"faltando: {esperadas - cols}"


def test_veiculo_model_aceita_novos_campos(db):
    v = Veiculo(nome='TESTE_TOCO', peso_maximo=6500, custo_km=3.20,
                custo_motorista_dia=180, custo_fixo_dia=50,
                depreciacao_mensal=1500, capacidade_pallets=14,
                capacidade_m3=42.0, velocidade_media_kmh=55.0, ativo=True)
    db.session.add(v)
    db.session.flush()
    assert v.id is not None
    assert float(v.custo_km) == 3.20
    assert v.ativo is True
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `pytest tests/veiculos/test_migration_parametros_custo.py -v`
Expected: FAIL (colunas inexistentes / `TypeError` no construtor).

- [ ] **Step 3: Escrever o SQL idempotente** — `scripts/migrations/2026_06_16_veiculo_parametros_custo.sql`

```sql
ALTER TABLE veiculos ADD COLUMN IF NOT EXISTS custo_km             NUMERIC(10,2);
ALTER TABLE veiculos ADD COLUMN IF NOT EXISTS custo_motorista_dia  NUMERIC(10,2);
ALTER TABLE veiculos ADD COLUMN IF NOT EXISTS custo_fixo_dia       NUMERIC(10,2);
ALTER TABLE veiculos ADD COLUMN IF NOT EXISTS depreciacao_mensal   NUMERIC(15,2);
ALTER TABLE veiculos ADD COLUMN IF NOT EXISTS capacidade_pallets   INTEGER;
ALTER TABLE veiculos ADD COLUMN IF NOT EXISTS capacidade_m3        DOUBLE PRECISION;
ALTER TABLE veiculos ADD COLUMN IF NOT EXISTS velocidade_media_kmh DOUBLE PRECISION;
ALTER TABLE veiculos ADD COLUMN IF NOT EXISTS ativo                BOOLEAN NOT NULL DEFAULT TRUE;
```

- [ ] **Step 4: Escrever o runner `.py`** — `scripts/migrations/2026_06_16_veiculo_parametros_custo.py`

```python
"""Migration: amplia `veiculos` com parametros de custo e capacidade.

Adiciona custo_km, custo_motorista_dia, custo_fixo_dia, depreciacao_mensal,
capacidade_pallets, capacidade_m3, velocidade_media_kmh, ativo.
Idempotente (ADD COLUMN IF NOT EXISTS). Uso:
    python scripts/migrations/2026_06_16_veiculo_parametros_custo.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402
from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)
COLS = ['custo_km', 'custo_motorista_dia', 'custo_fixo_dia', 'depreciacao_mensal',
        'capacidade_pallets', 'capacidade_m3', 'velocidade_media_kmh', 'ativo']


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        antes = {c['name'] for c in inspect(db.engine).get_columns('veiculos')}
        print('Faltando antes:', [c for c in COLS if c not in antes])
        sql_path = os.path.join(os.path.dirname(__file__), '2026_06_16_veiculo_parametros_custo.sql')
        with open(sql_path, encoding='utf-8') as f:
            statements = [s.strip() for s in f.read().split(';') if s.strip()]
        for stmt in statements:
            db.session.execute(text(stmt))
        db.session.commit()
        depois = {c['name'] for c in inspect(db.engine).get_columns('veiculos')}
        print('Faltando depois:', [c for c in COLS if c not in depois])
        assert all(c in depois for c in COLS), 'Migration nao aplicou todas as colunas'
        print('OK — migration aplicada.')


if __name__ == '__main__':
    main()
```

- [ ] **Step 5: Adicionar as colunas ao model** — `app/veiculos/models.py` (apos `multiplicador_pedagio`, antes das dims do bau)

```python
    # Parametros de custo (fonte da roteirizacao — custo por TIPO de veiculo)
    custo_km = db.Column(db.Numeric(10, 2), nullable=True)             # R$/km rodado
    custo_motorista_dia = db.Column(db.Numeric(10, 2), nullable=True)  # diaria motorista
    custo_fixo_dia = db.Column(db.Numeric(10, 2), nullable=True)       # seguro/rastreador/dia
    depreciacao_mensal = db.Column(db.Numeric(15, 2), nullable=True)   # /30 no calculo
    capacidade_pallets = db.Column(db.Integer, nullable=True)
    capacidade_m3 = db.Column(db.Float, nullable=True)
    velocidade_media_kmh = db.Column(db.Float, nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
```

- [ ] **Step 6: Atualizar o schema JSON** — `.claude/skills/consultando-sql/schemas/tables/veiculos.json`

Acrescentar ao array `fields` os 8 objetos:

```json
{ "name": "custo_km", "type": "numeric(10,2)", "description": "R$/km rodado (combustivel+manutencao)" },
{ "name": "custo_motorista_dia", "type": "numeric(10,2)", "description": "Diaria do motorista" },
{ "name": "custo_fixo_dia", "type": "numeric(10,2)", "description": "Custos fixos/dia (seguro, rastreador)" },
{ "name": "depreciacao_mensal", "type": "numeric(15,2)", "description": "Depreciacao do tipo/mes (/30 no calculo)" },
{ "name": "capacidade_pallets", "type": "integer", "description": "Capacidade em pallets" },
{ "name": "capacidade_m3", "type": "float", "description": "Capacidade volumetrica em m3" },
{ "name": "velocidade_media_kmh", "type": "float", "description": "Velocidade media p/ estimar dias" },
{ "name": "ativo", "type": "boolean", "default": true, "description": "True = listavel na roteirizacao" }
```

- [ ] **Step 7: Rodar a migration no banco local**

Run: `source .venv/bin/activate && python scripts/migrations/2026_06_16_veiculo_parametros_custo.py`
Expected: `OK — migration aplicada.`

- [ ] **Step 8: Rodar o teste e verificar que passa**

Run: `pytest tests/veiculos/test_migration_parametros_custo.py -v`
Expected: PASS (2 testes).

- [ ] **Step 9: Commit**

```bash
git add scripts/migrations/2026_06_16_veiculo_parametros_custo.* app/veiculos/models.py .claude/skills/consultando-sql/schemas/tables/veiculos.json tests/veiculos/test_migration_parametros_custo.py
git commit -m "feat(veiculos): parametros de custo e capacidade na tabela de tipos (roteirizacao F1)"
```

---

### Task 2: `calcular_custo_operacional` — funcao pura de custo

**Files:**
- Create: `app/carteira/services/roteirizacao_service.py`
- Test: `tests/carteira/test_roteirizacao_custo.py`

**Interfaces:**
- Consumes: model `Veiculo` (Task 1).
- Produces: `calcular_custo_operacional(distancia_km: float, tempo_min: float, veiculo, dias_viagem: int = 0, jornada_horas_dia: float = 10.0) -> dict` com chaves `dias`, `custo_combustivel`, `custo_motorista`, `custo_fixo`, `custo_depreciacao`, `custo_operacional` (soma SEM pedagio).

- [ ] **Step 1: Escrever os testes que falham** — `tests/carteira/test_roteirizacao_custo.py`

```python
from app.carteira.services.roteirizacao_service import calcular_custo_operacional


class _V:  # stub simples de veiculo
    def __init__(self, custo_km=0, custo_motorista_dia=0, custo_fixo_dia=0, depreciacao_mensal=0):
        self.custo_km = custo_km
        self.custo_motorista_dia = custo_motorista_dia
        self.custo_fixo_dia = custo_fixo_dia
        self.depreciacao_mensal = depreciacao_mensal


def test_combustivel_por_km():
    r = calcular_custo_operacional(100, 120, _V(custo_km=3.0))
    assert r['custo_combustivel'] == 300.0


def test_dias_informado_domina_estimativa():
    r = calcular_custo_operacional(100, 600, _V(custo_motorista_dia=200), dias_viagem=3)
    assert r['dias'] == 3
    assert r['custo_motorista'] == 600.0


def test_dias_estimado_por_tempo_e_jornada():
    # 1500 min = 25h; jornada 10h/dia => ceil(2.5) = 3 dias
    r = calcular_custo_operacional(100, 1500, _V(custo_motorista_dia=100), jornada_horas_dia=10)
    assert r['dias'] == 3


def test_depreciacao_rateada_por_dia():
    r = calcular_custo_operacional(0, 60, _V(depreciacao_mensal=3000), dias_viagem=2)
    assert r['custo_depreciacao'] == 200.0  # 3000/30 * 2


def test_campos_none_viram_zero():
    r = calcular_custo_operacional(50, 60, _V(), dias_viagem=1)
    assert r['custo_operacional'] == 0.0


def test_operacional_soma_componentes():
    v = _V(custo_km=2.0, custo_motorista_dia=150, custo_fixo_dia=40, depreciacao_mensal=3000)
    r = calcular_custo_operacional(100, 60, v, dias_viagem=2)
    # 200 + 300 + 80 + 200 = 780
    assert r['custo_operacional'] == 780.0
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `pytest tests/carteira/test_roteirizacao_custo.py -v`
Expected: FAIL (`ModuleNotFoundError` / função inexistente).

- [ ] **Step 3: Implementar a funcao** — `app/carteira/services/roteirizacao_service.py`

```python
"""Servico de roteirizacao: custo parametrico, selecao de veiculo e motor de
otimizacao (abstracao de backend). Separa responsabilidade de mapa_service.py
(geocoding/agrupamento)."""
import math
import logging

logger = logging.getLogger(__name__)


def _f(v):
    """Converte Numeric/None em float (None -> 0.0)."""
    return float(v) if v is not None else 0.0


def calcular_custo_operacional(distancia_km, tempo_min, veiculo,
                               dias_viagem=0, jornada_horas_dia=10.0):
    """Custo operacional da rota (SEM pedagio). Tudo parametrico do tipo de veiculo.

    dias_viagem > 0 domina; senao estima por tempo de direcao / jornada diaria.
    """
    if dias_viagem and dias_viagem > 0:
        dias = int(dias_viagem)
    else:
        horas = (tempo_min or 0) / 60.0
        dias = max(1, math.ceil(horas / jornada_horas_dia)) if horas else 1

    custo_combustivel = round(_f(distancia_km) * _f(veiculo.custo_km), 2)
    custo_motorista = round(dias * _f(veiculo.custo_motorista_dia), 2)
    custo_fixo = round(dias * _f(veiculo.custo_fixo_dia), 2)
    custo_depreciacao = round(dias * (_f(veiculo.depreciacao_mensal) / 30.0), 2)
    custo_operacional = round(
        custo_combustivel + custo_motorista + custo_fixo + custo_depreciacao, 2
    )
    return {
        'dias': dias,
        'custo_combustivel': custo_combustivel,
        'custo_motorista': custo_motorista,
        'custo_fixo': custo_fixo,
        'custo_depreciacao': custo_depreciacao,
        'custo_operacional': custo_operacional,
    }
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `pytest tests/carteira/test_roteirizacao_custo.py -v`
Expected: PASS (6 testes).

- [ ] **Step 5: Commit**

```bash
git add app/carteira/services/roteirizacao_service.py tests/carteira/test_roteirizacao_custo.py
git commit -m "feat(roteirizacao): custo operacional parametrico por tipo de veiculo (F1)"
```

---

### Task 3: `selecionar_veiculo` — selecao multidimensional (peso + pallets + m3)

**Files:**
- Modify: `app/carteira/services/roteirizacao_service.py`
- Test: `tests/carteira/test_roteirizacao_selecao.py`

**Interfaces:**
- Consumes: model `Veiculo`.
- Produces: `selecionar_veiculo(peso, pallets=0, m3=0) -> Veiculo | None` — menor `Veiculo.ativo` que atende as 3 dimensoes (capacidade None = ignora a dimensao); fallback maior por peso.

- [ ] **Step 1: Escrever os testes que falham** — `tests/carteira/test_roteirizacao_selecao.py`

```python
import uuid
from app.veiculos.models import Veiculo
from app.carteira.services.roteirizacao_service import selecionar_veiculo


def _mk(db, nome, peso, pallets=None, m3=None, ativo=True):
    v = Veiculo(nome=f'{nome}_{uuid.uuid4().hex[:6]}', peso_maximo=peso,
                capacidade_pallets=pallets, capacidade_m3=m3, ativo=ativo)
    db.session.add(v)
    db.session.flush()
    return v


def test_escolhe_menor_que_comporta_peso(db):
    _mk(db, 'TOCO', 6500, pallets=14)
    _mk(db, 'TRUCK', 14500, pallets=28)
    v = selecionar_veiculo(5000, pallets=10)
    assert v.peso_maximo == 6500


def test_pula_quem_nao_comporta_pallets(db):
    _mk(db, 'TOCO', 6500, pallets=14)
    truck = _mk(db, 'TRUCK', 14500, pallets=28)
    v = selecionar_veiculo(3000, pallets=20)  # peso cabe no TOCO, pallets nao
    assert v.id == truck.id


def test_ignora_inativos(db):
    _mk(db, 'TOCO', 6500, pallets=14, ativo=False)
    truck = _mk(db, 'TRUCK', 14500, pallets=28)
    v = selecionar_veiculo(3000, pallets=10)
    assert v.id == truck.id


def test_fallback_maior_quando_nada_comporta(db):
    _mk(db, 'TOCO', 6500)
    truck = _mk(db, 'TRUCK', 14500)
    v = selecionar_veiculo(99999)
    assert v.id == truck.id
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `pytest tests/carteira/test_roteirizacao_selecao.py -v`
Expected: FAIL (função inexistente).

- [ ] **Step 3: Implementar** — acrescentar a `roteirizacao_service.py`

```python
from app.veiculos.models import Veiculo


def selecionar_veiculo(peso, pallets=0, m3=0):
    """Menor veiculo ativo que comporta peso + pallets + m3. Capacidade None
    = dimensao nao restringe. Fallback: maior por peso entre os ativos."""
    candidatos = (
        Veiculo.query.filter(Veiculo.ativo.is_(True))
        .order_by(Veiculo.peso_maximo.asc())
        .all()
    )
    for v in candidatos:
        if v.peso_maximo < (peso or 0):
            continue
        if pallets and v.capacidade_pallets is not None and v.capacidade_pallets < pallets:
            continue
        if m3 and v.capacidade_m3 is not None and v.capacidade_m3 < m3:
            continue
        return v
    return candidatos[-1] if candidatos else None
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `pytest tests/carteira/test_roteirizacao_selecao.py -v`
Expected: PASS (4 testes).

- [ ] **Step 5: Commit**

```bash
git add app/carteira/services/roteirizacao_service.py tests/carteira/test_roteirizacao_selecao.py
git commit -m "feat(roteirizacao): selecao de veiculo multidimensional (peso/pallets/m3) (F1)"
```

---

### Task 4: Motor de otimizacao — abstracao + chunking

**Files:**
- Modify: `app/carteira/services/roteirizacao_service.py`
- Test: `tests/carteira/test_roteirizacao_motor.py`

**Interfaces:**
- Consumes: backend de roteirizacao (Task 5).
- Produces: `otimizar_rota(paradas: list[dict], origem: str, inclui_volta: bool = False, backend=None) -> dict` com `ordem` (lista de ids na sequencia), `distancia_km`, `tempo_min`, `polyline`, `trechos`. `paradas` = `[{'id': str, 'lat': float, 'lng': float}, ...]`. `backend` injetavel para teste.
- Produces: helper `_chunk_waypoints(paradas, tam=23)` — divide em blocos de ate `tam` com overlap de 1.

- [ ] **Step 1: Escrever os testes que falham** — `tests/carteira/test_roteirizacao_motor.py`

```python
from app.carteira.services.roteirizacao_service import _chunk_waypoints, otimizar_rota


def test_chunk_sem_overlap_quando_cabe():
    paradas = [{'id': str(i), 'lat': 0, 'lng': i} for i in range(5)]
    chunks = _chunk_waypoints(paradas, tam=23)
    assert len(chunks) == 1
    assert len(chunks[0]) == 5


def test_chunk_com_overlap_quando_excede():
    paradas = [{'id': str(i), 'lat': 0, 'lng': i} for i in range(50)]
    chunks = _chunk_waypoints(paradas, tam=23)
    assert len(chunks) >= 2
    assert chunks[0][-1]['id'] == chunks[1][0]['id']  # overlap


def test_otimizar_usa_backend_injetado():
    paradas = [{'id': 'A', 'lat': -23.4, 'lng': -46.8},
               {'id': 'B', 'lat': -23.5, 'lng': -46.6}]

    def fake_backend(origem, destino, waypoints, inclui_volta):
        return {'ordem_indices': list(range(len(waypoints))),
                'distancia_km': 42.0, 'tempo_min': 60.0, 'polyline': 'xyz', 'trechos': 1}

    r = otimizar_rota(paradas, origem='CD', inclui_volta=False, backend=fake_backend)
    assert r['distancia_km'] == 42.0
    assert r['ordem'] == ['A', 'B']
    assert r['polyline'] == 'xyz'
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `pytest tests/carteira/test_roteirizacao_motor.py -v`
Expected: FAIL (símbolos inexistentes).

- [ ] **Step 3: Implementar** — acrescentar a `roteirizacao_service.py`

```python
def _chunk_waypoints(paradas, tam=23):
    """Divide paradas em blocos de ate `tam` com overlap de 1 ponto entre blocos
    (fim de um = inicio do proximo), para concatenar trechos sem buraco. Limite
    Directions = 25 waypoints (origin+destination+23 intermediarios)."""
    if len(paradas) <= tam:
        return [list(paradas)]
    chunks, i = [], 0
    while i < len(paradas):
        bloco = paradas[i:i + tam]
        chunks.append(bloco)
        if i + tam >= len(paradas):
            break
        i = i + tam - 1  # overlap de 1
    return chunks


def otimizar_rota(paradas, origem, inclui_volta=False, backend=None):
    """Otimiza a ordem das paradas e mede a rota. `backend(origem, destino,
    waypoints, inclui_volta) -> {ordem_indices, distancia_km, tempo_min, polyline, trechos}`.
    Default backend = Directions+chunking (Task 5)."""
    if backend is None:
        from app.carteira.services.roteirizacao_backends import directions_chunking_backend
        backend = directions_chunking_backend
    if not paradas:
        return {'ordem': [], 'distancia_km': 0.0, 'tempo_min': 0.0,
                'polyline': '', 'trechos': 0}

    destino = origem if inclui_volta else None
    res = backend(origem, destino, paradas, inclui_volta)
    ordem = [paradas[i]['id'] for i in res['ordem_indices']]
    return {
        'ordem': ordem,
        'distancia_km': round(res.get('distancia_km', 0.0), 2),
        'tempo_min': round(res.get('tempo_min', 0.0), 1),
        'polyline': res.get('polyline', ''),
        'trechos': res.get('trechos', 1),
    }
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `pytest tests/carteira/test_roteirizacao_motor.py -v`
Expected: PASS (3 testes).

- [ ] **Step 5: Commit**

```bash
git add app/carteira/services/roteirizacao_service.py tests/carteira/test_roteirizacao_motor.py
git commit -m "feat(roteirizacao): motor de otimizacao com abstracao de backend + chunking de 25 (F1)"
```

---

### Task 5: Backend Directions+chunking real (e plug do Route Optimization)

**Files:**
- Create: `app/carteira/services/roteirizacao_backends.py`
- Test: `tests/carteira/test_roteirizacao_backends.py`

**Interfaces:**
- Consumes: `GOOGLE_MAPS_API_KEY`, Google Directions API.
- Produces: `directions_chunking_backend(origem, destino, waypoints, inclui_volta) -> {ordem_indices, distancia_km, tempo_min, polyline, trechos}`. Para <=23 intermediarios usa 1 request `optimize:true`; acima, chunking sequencial. `_route_optimization_backend` fica stub (R1) com `NotImplementedError`.

- [ ] **Step 1: Escrever o teste que falha** — `tests/carteira/test_roteirizacao_backends.py`

```python
from unittest.mock import patch
from app.carteira.services import roteirizacao_backends as b


def _fake_directions_response(n_legs=2):
    legs = [{'distance': {'value': 10000}, 'duration': {'value': 600}} for _ in range(n_legs)]
    return {
        'status': 'OK',
        'routes': [{
            'legs': legs,
            'waypoint_order': list(range(max(0, n_legs - 1))),
            'overview_polyline': {'points': 'abc'},
        }],
    }


def test_backend_single_request_ate_23():
    paradas = [{'id': str(i), 'lat': -23 - i * 0.01, 'lng': -46 - i * 0.01} for i in range(3)]
    with patch.object(b.requests, 'get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = _fake_directions_response(n_legs=3)
        r = b.directions_chunking_backend('CD', None, paradas, inclui_volta=False)
    assert r['trechos'] == 1
    assert r['distancia_km'] == 30.0  # 3 legs * 10km
    assert len(r['ordem_indices']) == len(paradas)
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `pytest tests/carteira/test_roteirizacao_backends.py -v`
Expected: FAIL (módulo inexistente).

- [ ] **Step 3: Implementar** — `app/carteira/services/roteirizacao_backends.py`

```python
"""Backends do motor de roteirizacao.

- directions_chunking_backend: usa Google Directions (key atual). <=23
  intermediarios = 1 request com optimize:true. Acima = chunking sequencial.
- _route_optimization_backend: PLUG do Google Route Optimization API
  (SKU Single Vehicle). Requer service account/OAuth2 (risco R1). Stub ate habilitar.
"""
import os
import logging
import requests

logger = logging.getLogger(__name__)
_BASE_DIRECTIONS = "https://maps.googleapis.com/maps/api/directions/json"


def _api_key():
    return os.getenv('GOOGLE_MAPS_API_KEY', '')


def directions_chunking_backend(origem, destino, waypoints, inclui_volta=False):
    """Retorna ordem otimizada + metricas via Directions API, com chunking de 23."""
    from app.carteira.services.roteirizacao_service import _chunk_waypoints

    pontos = list(waypoints)
    final = destino or (f"{pontos[-1]['lat']},{pontos[-1]['lng']}" if pontos else origem)

    blocos = _chunk_waypoints(pontos, tam=23)
    ordem_indices, dist_total, tempo_total, polylines = [], 0.0, 0.0, []
    cursor_origem = origem

    for bi, bloco in enumerate(blocos):
        ultimo_bloco = (bi == len(blocos) - 1)
        usar_destino_fixo = ultimo_bloco and bool(destino)
        destino_bloco = final if usar_destino_fixo else f"{bloco[-1]['lat']},{bloco[-1]['lng']}"
        intermediarios = bloco if usar_destino_fixo else bloco[:-1]
        wp = '|'.join(f"{p['lat']},{p['lng']}" for p in intermediarios)
        params = {
            'origin': cursor_origem, 'destination': destino_bloco,
            'key': _api_key(), 'mode': 'driving', 'units': 'metric',
            'avoid': 'ferries', 'language': 'pt-BR',
        }
        if wp:
            params['waypoints'] = 'optimize:true|' + wp
        resp = requests.get(_BASE_DIRECTIONS, params=params, timeout=30)
        if resp.status_code != 200:
            raise RuntimeError(f"Directions HTTP {resp.status_code}")
        data = resp.json()
        if data.get('status') != 'OK' or not data.get('routes'):
            raise RuntimeError(f"Directions status {data.get('status')}")
        route = data['routes'][0]
        dist_total += sum(l['distance']['value'] for l in route['legs']) / 1000.0
        tempo_total += sum(l['duration']['value'] for l in route['legs']) / 60.0
        polylines.append(route['overview_polyline']['points'])
        base = pontos.index(bloco[0])
        order = route.get('waypoint_order', list(range(len(intermediarios))))
        ordem_indices.extend(base + idx for idx in order)
        cursor_origem = destino_bloco

    # dedup preservando ordem (overlap pode repetir o ponto de juncao)
    visto, ordem_final = set(), []
    for i in ordem_indices:
        if i not in visto:
            visto.add(i); ordem_final.append(i)

    return {
        'ordem_indices': ordem_final,
        'distancia_km': round(dist_total, 2),
        'tempo_min': round(tempo_total, 1),
        'polyline': polylines[0] if len(polylines) == 1 else '|'.join(polylines),
        'trechos': len(blocos),
    }


def _route_optimization_backend(origem, destino, waypoints, inclui_volta=False):
    """PLUG futuro: Google Route Optimization API (Single Vehicle). Requer
    service account/OAuth2 (R1). Habilitar quando credencial existir."""
    raise NotImplementedError("Route Optimization API pendente de service account (R1)")
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `pytest tests/carteira/test_roteirizacao_backends.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/carteira/services/roteirizacao_backends.py tests/carteira/test_roteirizacao_backends.py
git commit -m "feat(roteirizacao): backend Directions+chunking + plug Route Optimization (F1)"
```

---

### Task 6: API `/api/rota/otimizar` — orquestra paradas, motor, veiculo e custo

**Files:**
- Modify: `app/carteira/routes/mapa_routes.py` (acrescentar rota)
- Test: `tests/carteira/test_api_rota_otimizar.py`

**Interfaces:**
- Consumes: `otimizar_rota`, `selecionar_veiculo`, `calcular_custo_operacional`, `MapaService` (pedagio + CD).
- Produces: `POST /carteira/mapa/api/rota/otimizar` — body `{clientes:[{id,lat,lng,peso,pallet,m3}], veiculo_id?, inclui_volta, dias_viagem, origem?}` → `{sucesso, rota:{ordem,distancia_km,tempo_min,polyline}, veiculo:{...}, custo:{combustivel,motorista,fixo,depreciacao,pedagio,total,dias}}`.

- [ ] **Step 1: Escrever o teste que falha** — `tests/carteira/test_api_rota_otimizar.py`

```python
import json
from unittest.mock import patch
from app.veiculos.models import Veiculo


def test_api_otimizar_retorna_custo(client, db):
    v = Veiculo(nome='TOCO_API', peso_maximo=6500, custo_km=3.0,
                custo_motorista_dia=200, custo_fixo_dia=50,
                depreciacao_mensal=3000, capacidade_pallets=14, ativo=True)
    db.session.add(v); db.session.flush()

    payload = {
        'clientes': [
            {'id': 'A', 'lat': -23.4, 'lng': -46.8, 'peso': 1000, 'pallet': 4, 'm3': 5},
            {'id': 'B', 'lat': -23.5, 'lng': -46.6, 'peso': 800, 'pallet': 3, 'm3': 4},
        ],
        'veiculo_id': v.id, 'inclui_volta': False, 'dias_viagem': 1,
    }
    fake = {'ordem': ['A', 'B'], 'distancia_km': 100.0, 'tempo_min': 120.0,
            'polyline': 'p', 'trechos': 1}
    with patch('app.carteira.routes.mapa_routes.otimizar_rota', return_value=fake):
        resp = client.post('/carteira/mapa/api/rota/otimizar',
                           data=json.dumps(payload), content_type='application/json')
    assert resp.status_code == 200
    body = resp.get_json()
    assert body['sucesso'] is True
    assert body['rota']['distancia_km'] == 100.0
    # combustivel 100*3=300; motorista 1*200; fixo 1*50; deprec 3000/30*1=100 => 650 + pedagio
    assert body['custo']['combustivel'] == 300.0
    assert body['custo']['total'] >= 650.0
    assert body['veiculo']['nome'] == 'TOCO_API'
```

- [ ] **Step 2: Rodar e verificar que falha**

Run: `pytest tests/carteira/test_api_rota_otimizar.py -v`
Expected: FAIL (404 / rota inexistente).

- [ ] **Step 3: Implementar a rota** — em `app/carteira/routes/mapa_routes.py` (imports no topo + rota)

```python
from app.carteira.services.roteirizacao_service import (
    otimizar_rota, selecionar_veiculo, calcular_custo_operacional,
)
from app.veiculos.models import Veiculo


@bp.route('/api/rota/otimizar', methods=['POST'])
@login_required
def rota_otimizar():
    """Otimiza a rota das paradas + custo parametrico por tipo de veiculo."""
    try:
        data = request.get_json() or {}
        clientes = data.get('clientes', [])
        if not clientes:
            return jsonify({'erro': 'Nenhuma parada informada'}), 400

        origem = data.get('origem') or mapa_service.endereco_cd
        inclui_volta = bool(data.get('inclui_volta'))
        dias_viagem = int(data.get('dias_viagem') or 0)

        paradas = [{'id': c['id'], 'lat': c['lat'], 'lng': c['lng']} for c in clientes]
        rota = otimizar_rota(paradas, origem=origem, inclui_volta=inclui_volta)

        peso = sum(float(c.get('peso') or 0) for c in clientes)
        pallets = sum(float(c.get('pallet') or 0) for c in clientes)
        m3 = sum(float(c.get('m3') or 0) for c in clientes)

        veiculo = (Veiculo.query.get(data['veiculo_id'])
                   if data.get('veiculo_id') else selecionar_veiculo(peso, pallets, m3))

        custo = calcular_custo_operacional(rota['distancia_km'], rota['tempo_min'],
                                           veiculo, dias_viagem=dias_viagem) if veiculo else {}
        pedagio = mapa_service._calcular_pedagio_estimado(rota['distancia_km'], veiculo)
        valor_pedagio = pedagio.get('valor_total', 0) if isinstance(pedagio, dict) else 0
        total = round(custo.get('custo_operacional', 0) + valor_pedagio, 2)

        return jsonify({
            'sucesso': True,
            'rota': rota,
            'veiculo': {
                'id': veiculo.id, 'nome': veiculo.nome,
                'peso_maximo': veiculo.peso_maximo,
            } if veiculo else None,
            'custo': {
                'dias': custo.get('dias', dias_viagem),
                'combustivel': custo.get('custo_combustivel', 0),
                'motorista': custo.get('custo_motorista', 0),
                'fixo': custo.get('custo_fixo', 0),
                'depreciacao': custo.get('custo_depreciacao', 0),
                'pedagio': valor_pedagio,
                'total': total,
            },
        })
    except Exception as e:
        logger.error(f"Erro em rota_otimizar: {e}")
        import traceback; logger.error(traceback.format_exc())
        return jsonify({'erro': str(e)}), 500
```

- [ ] **Step 4: Rodar e verificar que passa**

Run: `pytest tests/carteira/test_api_rota_otimizar.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/carteira/routes/mapa_routes.py tests/carteira/test_api_rota_otimizar.py
git commit -m "feat(roteirizacao): API /api/rota/otimizar com custo parametrico (F1)"
```

---

### Task 7: Frontend — painel de parametros + card de custo detalhado

**Files:**
- Modify: `app/templates/carteira/mapa_pedidos.html` (controles + chamada + card)
- Modify: `app/veiculos/routes.py:16-141,173-188` (CRUD le os novos campos; `api/lista` expoe custos)
- Modify: `app/templates/veiculos/admin_veiculos.html` (inputs dos novos campos)

**Interfaces:**
- Consumes: `POST /carteira/mapa/api/rota/otimizar`, `GET /veiculos/api/lista`.
- Produces: UI que envia veiculo_id/dias/volta e renderiza o detalhamento de custo.

- [ ] **Step 1: Ampliar o CRUD de Veiculo** — em `app/veiculos/routes.py`, ler os novos campos em `criar_veiculo`/`editar_veiculo` (ex.: `veiculo.custo_km = request.form.get('custo_km') or None`) e, em `api_lista_veiculos`, acrescentar `custo_km`, `custo_motorista_dia`, `custo_fixo_dia`, `depreciacao_mensal`, `capacidade_pallets`, `capacidade_m3`, `ativo` ao dict retornado.

- [ ] **Step 2: Inputs no template admin** — em `app/templates/veiculos/admin_veiculos.html`, nos forms criar/editar, inputs `number step=0.01` para os campos de custo/capacidade e checkbox `ativo`.

- [ ] **Step 3: Painel de parametros no mapa** — em `app/templates/carteira/mapa_pedidos.html`, no bloco de controles: `<select id="rotaVeiculo">` (carregado de `/veiculos/api/lista`, com opcao "Automatico"), `<input id="rotaDias" type="number" min="0">`, `<label><input id="rotaVolta" type="checkbox"> Considerar volta</label>`.

- [ ] **Step 4: Trocar a chamada de rota** — `calcularRotaOtimizada()` monta `clientes` (id,lat,lng,peso,pallet) dos selecionados e faz `POST /carteira/mapa/api/rota/otimizar` com `veiculo_id/inclui_volta/dias_viagem`; renderiza `response.custo` num card "Custo da rota" (combustivel/motorista/fixo/depreciacao/pedagio/total + dias) e desenha `response.rota.polyline`.

- [ ] **Step 5: Smoke manual**

Run: `source .venv/bin/activate && python run.py` → lista de pedidos → selecionar 2-3 → "Ver no Mapa" → cadastrar custos num veiculo (admin) → "Rota Otimizada".
Expected: card mostra os 6 componentes + total != 0; muda ao alternar volta/dias/veiculo.

- [ ] **Step 6: Commit**

```bash
git add app/templates/carteira/mapa_pedidos.html app/veiculos/routes.py app/templates/veiculos/admin_veiculos.html
git commit -m "feat(roteirizacao): painel de parametros + card de custo detalhado no mapa (F1)"
```

---

## Self-Review

- **Cobertura do spec (Fase 1):** custo parametrico (Tasks 1-2,6) ✓ · fixo+depreciacao (Task 2) ✓ · selecao multidimensional (Task 3) ✓ · supera limite 25 (Tasks 4-5, chunking) ✓ · flag volta (Tasks 4-6) ✓ · dias de viagem (Tasks 2,6) ✓ · UI custo (Task 7) ✓ · Route Optimization plugavel sem travar (Task 5 stub) ✓.
- **Placeholders:** nenhum — todo step de codigo traz o codigo.
- **Consistencia de tipos:** `otimizar_rota` retorna `{ordem,distancia_km,tempo_min,polyline,trechos}` (Tasks 4 e 6); backend retorna `ordem_indices` (mapeado p/ `ordem` no service); `calcular_custo_operacional` retorna as chaves consumidas na Task 6.
- **Fora da Fase 1:** rotas salvas, geocoding persistente, on-demand (Fase 2); cotacao por rota salva, drag-and-drop, origem configuravel (Fase 3); habilitar Route Optimization API (depende de R1).
