<!-- doc:meta
tipo: scratch
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-16
-->

# Roteirizacao "Ver no Mapa" — Fase 2 (Interatividade + persistencia) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Tornar a roteirizacao interativa (incluir/remover pedidos on-demand recalculando a rota) e persistente (salvar/nomear/listar/carregar rotas; cache de geocoding em banco).

**Architecture:** 2 models novos em `app/carteira/models.py` (`GeocodeCache`, `RotaSalva`) — criados no boot via `create_all` (+ migrations idempotentes para PROD). `geocodificar_endereco` ganha camada L2 persistente. Novas APIs REST em `mapa_routes.py` (salvar/listar/carregar/excluir rota + adicionar pedido). UI no `mapa_pedidos.html` (incluir/remover on-demand + salvar/carregar rotas).

**Tech Stack:** Flask 3.1 + SQLAlchemy 2.0 (PostgreSQL, JSONB), Jinja2 + jQuery, pytest (PostgreSQL local).

## Global Constraints

- Tabela NOVA = model em `app/carteira/models.py` (entra no `create_all` do boot) + migration idempotente `.sql`/`.py` (`CREATE TABLE IF NOT EXISTS`) em `scripts/migrations/` para PROD. Flask-Migrate CONGELADO.
- Scripts em `scripts/migrations/` precisam de `sys.path.insert(0, <raiz>)`.
- Datas via `app/utils/timezone.py` (`agora_utc_naive`).
- `db.JSON` para colunas de lista (lotes/ordem) — ler valor inteiro, nunca `.astext` (gotcha db.JSON generico).
- Testes: fixtures `db`/`client` (savepoint; `LOGIN_DISABLED=True`, CSRF off). Rodar pytest **da raiz do worktree**; venv da raiz principal; `Numeric`->float no JSON (jsonify nao serializa Decimal).
- `criado_por` = `current_user.id` (Integer, sem FK formal — filtrar rotas do usuario).
- Reaproveitar `mapa_service.obter_clientes_para_mapa(lotes=[...])` para adicionar pedido (NAO duplicar logica de agrupamento).
- Construido sobre a Fase 1 (mesmo branch). `calcular_custo_operacional`, `otimizar_rota`, `selecionar_veiculo` ja existem.

---

### Task 1: `GeocodeCache` — cache de geocoding persistente (L2)

**Files:**
- Modify: `app/carteira/models.py` (novo model no fim)
- Create: `scripts/migrations/2026_06_16_geocode_cache.py` + `.sql`
- Modify: `app/carteira/services/mapa_service.py:692-735` (`geocodificar_endereco`)
- Test: `tests/carteira/test_geocode_cache.py`

**Interfaces:**
- Produces: model `GeocodeCache(endereco_hash, endereco, lat, lng, fonte, geocodificado_em)`.
- `geocodificar_endereco(endereco)` inalterada na assinatura; ganha L1 (TTLCache) -> L2 (GeocodeCache) -> Google (grava L1+L2).

- [ ] **Step 1: Teste que falha** — `tests/carteira/test_geocode_cache.py`

```python
from unittest.mock import patch
from app.carteira.models import GeocodeCache
from app.carteira.services.mapa_service import MapaService


def test_geocode_grava_e_le_do_banco(db):
    svc = MapaService()
    svc.geocoding_cache.clear()  # zera L1 p/ forcar caminho do banco

    fake = {'status': 'OK', 'results': [{'geometry': {'location': {'lat': -23.4, 'lng': -46.8}}}]}
    with patch.object(__import__('requests'), 'get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = fake
        lat1, lng1 = svc.geocodificar_endereco('Rua X, 1, Sao Paulo, SP, Brasil')
    assert (lat1, lng1) == (-23.4, -46.8)
    # gravou no banco
    row = GeocodeCache.query.filter_by(endereco='Rua X, 1, Sao Paulo, SP, Brasil').first()
    assert row is not None and row.lat == -23.4

    # segunda chamada (L1 limpo) le do banco, sem chamar Google
    svc.geocoding_cache.clear()
    with patch.object(__import__('requests'), 'get') as mock_get2:
        lat2, lng2 = svc.geocodificar_endereco('Rua X, 1, Sao Paulo, SP, Brasil')
        assert mock_get2.call_count == 0
    assert (lat2, lng2) == (-23.4, -46.8)
```

- [ ] **Step 2: Rodar — FAIL** (`ImportError: GeocodeCache`)

Run: `pytest tests/carteira/test_geocode_cache.py -q`

- [ ] **Step 3: Model** — fim de `app/carteira/models.py`

```python
class GeocodeCache(db.Model):
    """Cache persistente de geocoding (L2). Evita re-chamar Google a cada abertura."""
    __tablename__ = 'geocode_cache'

    id = db.Column(db.Integer, primary_key=True)
    endereco_hash = db.Column(db.String(32), unique=True, nullable=False, index=True)
    endereco = db.Column(db.Text, nullable=False)
    lat = db.Column(db.Float, nullable=False)
    lng = db.Column(db.Float, nullable=False)
    fonte = db.Column(db.String(20), default='google')
    geocodificado_em = db.Column(db.DateTime, default=agora_utc_naive)
```

- [ ] **Step 4: Migration** — `scripts/migrations/2026_06_16_geocode_cache.sql`

```sql
CREATE TABLE IF NOT EXISTS geocode_cache (
    id               SERIAL PRIMARY KEY,
    endereco_hash    VARCHAR(32) NOT NULL,
    endereco         TEXT NOT NULL,
    lat              DOUBLE PRECISION NOT NULL,
    lng              DOUBLE PRECISION NOT NULL,
    fonte            VARCHAR(20) DEFAULT 'google',
    geocodificado_em TIMESTAMP,
    CONSTRAINT uq_geocode_cache_hash UNIQUE (endereco_hash)
);
CREATE INDEX IF NOT EXISTS ix_geocode_cache_hash ON geocode_cache (endereco_hash);
```

E o runner `.py` (mesmo molde da migration da Fase 1: `sys.path.insert`, le o `.sql`, executa cada statement, `db.session.commit()`, valida `inspect`).

- [ ] **Step 5: Persistencia no service** — substituir corpo de `geocodificar_endereco` (`mapa_service.py:692`)

```python
    def geocodificar_endereco(self, endereco):
        try:
            cache_key = hashlib.md5(endereco.encode()).hexdigest()
            # L1 memoria
            if cache_key in self.geocoding_cache:
                return self.geocoding_cache[cache_key]
            # L2 banco
            from app.carteira.models import GeocodeCache
            row = GeocodeCache.query.filter_by(endereco_hash=cache_key).first()
            if row:
                self.geocoding_cache[cache_key] = (row.lat, row.lng)
                return row.lat, row.lng
            # Google
            params = {'address': endereco, 'key': self.api_key, 'region': 'br', 'language': 'pt-BR'}
            response = requests.get(self.base_geocoding_url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'OK' and data['results']:
                    loc = data['results'][0]['geometry']['location']
                    lat, lng = loc['lat'], loc['lng']
                    self.geocoding_cache[cache_key] = (lat, lng)
                    try:
                        db.session.add(GeocodeCache(endereco_hash=cache_key, endereco=endereco,
                                                    lat=lat, lng=lng, fonte='google'))
                        db.session.commit()
                    except Exception:
                        db.session.rollback()
                    return lat, lng
            return None, None
        except Exception as e:
            logger.error(f"Erro ao geocodificar endereço: {str(e)}")
            return None, None
```

- [ ] **Step 6: Criar tabela local + rodar testes**

Run: `python -c "from app import create_app; create_app()"` (boot cria a tabela) e `pytest tests/carteira/test_geocode_cache.py -q`
Expected: PASS (1).

- [ ] **Step 7: Commit**

```bash
git add app/carteira/models.py scripts/migrations/2026_06_16_geocode_cache.* app/carteira/services/mapa_service.py tests/carteira/test_geocode_cache.py
git commit -m "feat(roteirizacao): geocode_cache persistente (L2) no geocodificar_endereco (F2)"
```

---

### Task 2: `RotaSalva` — model + migration

**Files:**
- Modify: `app/carteira/models.py`
- Create: `scripts/migrations/2026_06_16_rota_salva.py` + `.sql`
- Test: `tests/carteira/test_rota_salva_model.py`

**Interfaces:**
- Produces: model `RotaSalva` com `nome, criado_por, criado_em, atualizado_em, veiculo_id, origem_endereco, inclui_volta, dias_viagem, lotes(JSON), ordem_otimizada(JSON), distancia_km, tempo_min, peso_total, pallet_total, valor_total, custo_* (Numeric), polyline, status`.

- [ ] **Step 1: Teste que falha** — `tests/carteira/test_rota_salva_model.py`

```python
from app.carteira.models import RotaSalva


def test_cria_rota_salva(db):
    r = RotaSalva(nome='SP Capital', criado_por=1, lotes=['L1', 'L2'],
                  ordem_otimizada=['L2', 'L1'], inclui_volta=True, dias_viagem=2,
                  distancia_km=120.5, custo_total=850.0, status='salva')
    db.session.add(r)
    db.session.flush()
    assert r.id is not None
    assert r.lotes == ['L1', 'L2']
    assert r.inclui_volta is True
    assert float(r.custo_total) == 850.0
```

- [ ] **Step 2: Rodar — FAIL**

Run: `pytest tests/carteira/test_rota_salva_model.py -q`

- [ ] **Step 3: Model** — `app/carteira/models.py`

```python
class RotaSalva(db.Model):
    """Rota de entrega salva (mono-veiculo) — agrupamento nomeado de lotes + custo snapshot."""
    __tablename__ = 'rota_salva'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=True)
    criado_por = db.Column(db.Integer, index=True, nullable=True)  # usuarios.id
    criado_em = db.Column(db.DateTime, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive, onupdate=agora_utc_naive)
    veiculo_id = db.Column(db.Integer, db.ForeignKey('veiculos.id'), nullable=True)
    origem_endereco = db.Column(db.Text, nullable=True)
    inclui_volta = db.Column(db.Boolean, default=False)
    dias_viagem = db.Column(db.Integer, default=0)
    lotes = db.Column(db.JSON, nullable=False)
    ordem_otimizada = db.Column(db.JSON, nullable=True)
    distancia_km = db.Column(db.Float)
    tempo_min = db.Column(db.Float)
    peso_total = db.Column(db.Float)
    pallet_total = db.Column(db.Float)
    valor_total = db.Column(db.Float)
    custo_combustivel = db.Column(db.Numeric(12, 2))
    custo_motorista = db.Column(db.Numeric(12, 2))
    custo_fixo = db.Column(db.Numeric(12, 2))
    custo_depreciacao = db.Column(db.Numeric(12, 2))
    custo_pedagio = db.Column(db.Numeric(12, 2))
    custo_total = db.Column(db.Numeric(12, 2))
    polyline = db.Column(db.Text)
    status = db.Column(db.String(20), default='salva')

    def to_dict(self):
        return {
            'id': self.id, 'nome': self.nome, 'veiculo_id': self.veiculo_id,
            'inclui_volta': self.inclui_volta, 'dias_viagem': self.dias_viagem,
            'lotes': self.lotes or [], 'ordem_otimizada': self.ordem_otimizada or [],
            'distancia_km': self.distancia_km, 'tempo_min': self.tempo_min,
            'peso_total': self.peso_total, 'pallet_total': self.pallet_total,
            'valor_total': self.valor_total,
            'custo_total': float(self.custo_total) if self.custo_total is not None else None,
            'criado_em': self.criado_em.strftime('%d/%m/%Y %H:%M') if self.criado_em else None,
        }
```

- [ ] **Step 4: Migration** — `scripts/migrations/2026_06_16_rota_salva.sql`

```sql
CREATE TABLE IF NOT EXISTS rota_salva (
    id                SERIAL PRIMARY KEY,
    nome              VARCHAR(100),
    criado_por        INTEGER,
    criado_em         TIMESTAMP,
    atualizado_em     TIMESTAMP,
    veiculo_id        INTEGER REFERENCES veiculos(id),
    origem_endereco   TEXT,
    inclui_volta      BOOLEAN DEFAULT FALSE,
    dias_viagem       INTEGER DEFAULT 0,
    lotes             JSONB NOT NULL,
    ordem_otimizada   JSONB,
    distancia_km      DOUBLE PRECISION,
    tempo_min         DOUBLE PRECISION,
    peso_total        DOUBLE PRECISION,
    pallet_total      DOUBLE PRECISION,
    valor_total       DOUBLE PRECISION,
    custo_combustivel NUMERIC(12,2),
    custo_motorista   NUMERIC(12,2),
    custo_fixo        NUMERIC(12,2),
    custo_depreciacao NUMERIC(12,2),
    custo_pedagio     NUMERIC(12,2),
    custo_total       NUMERIC(12,2),
    polyline          TEXT,
    status            VARCHAR(20) DEFAULT 'salva'
);
CREATE INDEX IF NOT EXISTS ix_rota_salva_criado_por ON rota_salva (criado_por);
```

E o runner `.py` (mesmo molde).

- [ ] **Step 5: Boot cria tabela + teste PASS**

Run: `python -c "from app import create_app; create_app()"` + `pytest tests/carteira/test_rota_salva_model.py -q`

- [ ] **Step 6: Commit**

```bash
git add app/carteira/models.py scripts/migrations/2026_06_16_rota_salva.* tests/carteira/test_rota_salva_model.py
git commit -m "feat(roteirizacao): model RotaSalva + migration (F2)"
```

---

### Task 3: APIs salvar / listar / carregar / excluir rota

**Files:**
- Modify: `app/carteira/routes/mapa_routes.py`
- Test: `tests/carteira/test_api_rotas_salvas.py`

**Interfaces:**
- Consumes: `RotaSalva`, `current_user`.
- Produces:
  - `POST /carteira/mapa/api/rota/salvar` — body `{nome?, veiculo_id?, inclui_volta, dias_viagem, lotes[], ordem_otimizada[], distancia_km, tempo_min, peso_total, pallet_total, valor_total, custo{...}, polyline}` -> `{sucesso, id}`.
  - `GET /carteira/mapa/api/rotas` -> `{sucesso, rotas:[to_dict...]}` (do usuario).
  - `GET /carteira/mapa/api/rota/<id>` -> `{sucesso, rota: to_dict}`.
  - `DELETE /carteira/mapa/api/rota/<id>` -> `{sucesso}`.

- [ ] **Step 1: Teste que falha** — `tests/carteira/test_api_rotas_salvas.py`

```python
import json
from app.carteira.models import RotaSalva


def test_salvar_listar_carregar_excluir(client, db):
    payload = {'nome': 'Rota Teste', 'inclui_volta': True, 'dias_viagem': 2,
               'lotes': ['L1', 'L2'], 'ordem_otimizada': ['L2', 'L1'],
               'distancia_km': 100.0, 'custo': {'total': 800.0}}
    # salvar
    r = client.post('/carteira/mapa/api/rota/salvar', data=json.dumps(payload),
                    content_type='application/json')
    assert r.status_code == 200
    rid = r.get_json()['id']
    assert RotaSalva.query.get(rid) is not None
    # listar
    r2 = client.get('/carteira/mapa/api/rotas')
    nomes = [x['nome'] for x in r2.get_json()['rotas']]
    assert 'Rota Teste' in nomes
    # carregar
    r3 = client.get(f'/carteira/mapa/api/rota/{rid}')
    body = r3.get_json()['rota']
    assert body['lotes'] == ['L1', 'L2']
    assert float(body['custo_total']) == 800.0
    # excluir
    r4 = client.delete(f'/carteira/mapa/api/rota/{rid}')
    assert r4.get_json()['sucesso'] is True
    assert RotaSalva.query.get(rid) is None
```

- [ ] **Step 2: Rodar — FAIL** (404)

- [ ] **Step 3: Implementar** — `app/carteira/routes/mapa_routes.py` (import `RotaSalva` no topo + rotas)

```python
@bp.route('/api/rota/salvar', methods=['POST'])
@login_required
def rota_salvar():
    try:
        data = request.get_json() or {}
        if not data.get('lotes'):
            return jsonify({'erro': 'Rota sem lotes'}), 400
        custo = data.get('custo') or {}
        rota = RotaSalva(
            nome=(data.get('nome') or None),
            criado_por=getattr(current_user, 'id', None),
            veiculo_id=data.get('veiculo_id'),
            origem_endereco=data.get('origem'),
            inclui_volta=bool(data.get('inclui_volta')),
            dias_viagem=int(data.get('dias_viagem') or 0),
            lotes=data.get('lotes'),
            ordem_otimizada=data.get('ordem_otimizada'),
            distancia_km=data.get('distancia_km'),
            tempo_min=data.get('tempo_min'),
            peso_total=data.get('peso_total'),
            pallet_total=data.get('pallet_total'),
            valor_total=data.get('valor_total'),
            custo_combustivel=custo.get('combustivel'),
            custo_motorista=custo.get('motorista'),
            custo_fixo=custo.get('fixo'),
            custo_depreciacao=custo.get('depreciacao'),
            custo_pedagio=custo.get('pedagio'),
            custo_total=custo.get('total'),
            polyline=data.get('polyline'),
            status='salva',
        )
        db.session.add(rota)
        db.session.commit()
        return jsonify({'sucesso': True, 'id': rota.id})
    except Exception as e:
        db.session.rollback()
        logger.error(f"Erro ao salvar rota: {e}")
        return jsonify({'erro': str(e)}), 500


@bp.route('/api/rotas', methods=['GET'])
@login_required
def rota_listar():
    uid = getattr(current_user, 'id', None)
    q = RotaSalva.query
    if uid is not None:
        q = q.filter(or_(RotaSalva.criado_por == uid, RotaSalva.criado_por.is_(None)))
    rotas = q.order_by(RotaSalva.criado_em.desc()).limit(200).all()
    return jsonify({'sucesso': True, 'rotas': [r.to_dict() for r in rotas]})


@bp.route('/api/rota/<int:rota_id>', methods=['GET'])
@login_required
def rota_carregar(rota_id):
    rota = RotaSalva.query.get(rota_id)
    if not rota:
        return jsonify({'erro': 'Rota nao encontrada'}), 404
    return jsonify({'sucesso': True, 'rota': rota.to_dict()})


@bp.route('/api/rota/<int:rota_id>', methods=['DELETE'])
@login_required
def rota_excluir(rota_id):
    rota = RotaSalva.query.get(rota_id)
    if not rota:
        return jsonify({'erro': 'Rota nao encontrada'}), 404
    db.session.delete(rota)
    db.session.commit()
    return jsonify({'sucesso': True})
```

Imports no topo: `from app.carteira.models import RotaSalva` e garantir `from sqlalchemy import or_` (ja usado em mapa_service; em mapa_routes adicionar se faltar). `db` ja disponivel? Adicionar `from app import db`.

- [ ] **Step 4: Rodar — PASS**

Run: `pytest tests/carteira/test_api_rotas_salvas.py -q`

- [ ] **Step 5: Commit**

```bash
git add app/carteira/routes/mapa_routes.py tests/carteira/test_api_rotas_salvas.py
git commit -m "feat(roteirizacao): API salvar/listar/carregar/excluir rota (F2)"
```

---

### Task 4: API adicionar pedido on-demand

**Files:**
- Modify: `app/carteira/routes/mapa_routes.py`
- Test: `tests/carteira/test_api_adicionar_pedido.py`

**Interfaces:**
- Consumes: `mapa_service.obter_clientes_para_mapa`.
- Produces: `POST /carteira/mapa/api/rota/adicionar-cliente` — body `{lotes:[...]}` (ou `{pedidos:[...]}`) -> `{sucesso, clientes:[...]}` no MESMO formato de `/api/clientes` (para o front plotar/incluir). Erro 404 se nada encontrado.

- [ ] **Step 1: Teste que falha** — `tests/carteira/test_api_adicionar_pedido.py`

```python
import json
from unittest.mock import patch


def test_adicionar_cliente_por_lote(client, db):
    fake_clientes = [{'cliente_id': 'abc', 'cliente': {'nome': 'X'},
                      'coordenadas': {'lat': -23.4, 'lng': -46.8},
                      'totais': {'peso': 100, 'pallet': 2, 'valor': 500, 'qtd_pedidos': 1},
                      'pedidos': [], 'endereco': {}}]
    with patch('app.carteira.routes.mapa_routes.mapa_service.obter_clientes_para_mapa',
               return_value=fake_clientes):
        r = client.post('/carteira/mapa/api/rota/adicionar-cliente',
                        data=json.dumps({'lotes': ['LX']}), content_type='application/json')
    assert r.status_code == 200
    body = r.get_json()
    assert body['sucesso'] is True
    assert body['clientes'][0]['cliente_id'] == 'abc'


def test_adicionar_sem_lote_400(client, db):
    r = client.post('/carteira/mapa/api/rota/adicionar-cliente',
                    data=json.dumps({}), content_type='application/json')
    assert r.status_code == 400
```

- [ ] **Step 2: Rodar — FAIL**

- [ ] **Step 3: Implementar** — `mapa_routes.py`

```python
@bp.route('/api/rota/adicionar-cliente', methods=['POST'])
@login_required
def rota_adicionar_cliente():
    """Busca cliente(s) por lote/pedido p/ incluir on-demand no mapa (mesmo formato de /api/clientes)."""
    try:
        data = request.get_json() or {}
        lotes = data.get('lotes', []) or []
        pedidos = data.get('pedidos', []) or []
        if not lotes and not pedidos:
            return jsonify({'erro': 'Informe lotes ou pedidos'}), 400
        clientes = mapa_service.obter_clientes_para_mapa(pedidos, lotes=lotes)
        if not clientes:
            return jsonify({'erro': 'Nenhum cliente encontrado'}), 404
        return jsonify({'sucesso': True, 'clientes': clientes})
    except Exception as e:
        logger.error(f"Erro ao adicionar cliente: {e}")
        return jsonify({'erro': str(e)}), 500
```

- [ ] **Step 4: Rodar — PASS**

- [ ] **Step 5: Commit**

```bash
git add app/carteira/routes/mapa_routes.py tests/carteira/test_api_adicionar_pedido.py
git commit -m "feat(roteirizacao): API adicionar pedido on-demand no mapa (F2)"
```

---

### Task 5: UI — incluir/remover on-demand + salvar/listar/carregar rotas

**Files:**
- Modify: `app/templates/carteira/mapa_pedidos.html`

**Interfaces:**
- Consumes: `/api/rota/adicionar-cliente`, `/api/rota/salvar`, `/api/rotas`, `/api/rota/<id>`.
- Produces: UI funcional. (Smoke render server-side; smoke visual no browser = pendencia registrada.)

- [ ] **Step 1: Botoes + modal** — em `mapa_pedidos.html`, no bloco de controles: `Adicionar pedido` (input num_pedido/lote + botao), `Salvar rota` (pede nome) e `Rotas salvas` (modal lista com carregar/excluir).

- [ ] **Step 2: JS incluir/remover** — `adicionarPedidoMapa()` faz `POST /api/rota/adicionar-cliente`, faz push em `clientesData`, re-plota (`plotarClientesNoMapa`), `atualizarListaClientes`, `recalcularTotais`, `atualizarCustoRota`. Remover: o checkbox ja existe; ligar `onchange` para tambem chamar `atualizarCustoRota()` (recalcula custo ao remover).

- [ ] **Step 3: JS salvar/listar/carregar** — `salvarRota()` coleta `rotaCalculada` + custo atual + lotes (separacao_lote_id dos clientes selecionados) e `POST /api/rota/salvar`; `abrirRotasSalvas()` faz `GET /api/rotas` e popula modal; `carregarRota(id)` faz `GET /api/rota/<id>` e reabre `/carteira/mapa/visualizar?lotes[]=...`; `excluirRota(id)` faz `DELETE`.

- [ ] **Step 4: Smoke render**

Run: `python - <<'PY'` boot + `test_client().get('/carteira/mapa/visualizar?lotes[]=X')` == 200.

- [ ] **Step 5: Commit**

```bash
git add app/templates/carteira/mapa_pedidos.html
git commit -m "feat(roteirizacao): UI incluir/remover on-demand + salvar/carregar rotas (F2)"
```

---

## Self-Review

- **Cobertura do escopo F2:** geocoding persistente (T1) ✓ · incluir on-demand (T4 API + T5 UI) ✓ · remover on-demand recalculando (T5) ✓ · rota salva model+migration (T2) ✓ · salvar/listar/carregar/excluir (T3 API + T5 UI) ✓.
- **Placeholders:** nenhum nos passos de codigo (T1-T4 com codigo completo; T5 e UI — passos descritivos + smoke, sem teste automatizado por ser template).
- **Consistencia:** `to_dict()` de RotaSalva consumido em T3 (listar/carregar) e T5 (UI); `obter_clientes_para_mapa` reusado em T4; custo no formato `{combustivel,motorista,fixo,depreciacao,pedagio,total}` igual a Fase 1.
- **Fora da F2 (Fase 3):** cotacao por rota salva (reusa wizard), reordenar drag-and-drop, origem configuravel.
