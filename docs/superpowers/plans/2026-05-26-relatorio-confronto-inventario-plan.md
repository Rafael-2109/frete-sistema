<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Relatório de Confronto de Inventário — Implementation Plan

> **Papel:** Relatório de Confronto de Inventário — Implementation Plan.

## Indice

- [Phase 1 — Foundation (esqueleto, modelos, migrations, schema fix)](#phase-1-foundation-esqueleto-modelos-migrations-schema-fix)
  - [Task 1: Criar esqueleto do módulo `app/inventario/`](#task-1-criar-esqueleto-do-módulo-appinventario)
  - [Task 2: Criar modelos (4 tabelas)](#task-2-criar-modelos-4-tabelas)
  - [Task 3: Migrations DDL (Python + SQL idempotente)](#task-3-migrations-ddl-python-sql-idempotente)
  - [Task 4: Fix schema JSON desatualizado de `movimentacao_estoque`](#task-4-fix-schema-json-desatualizado-de-movimentacao_estoque)
- [Phase 2 — Services (lógica de negócio)](#phase-2-services-lógica-de-negócio)
  - [Task 5: `inventario_loader.py` — parser xlsx do inventário base](#task-5-inventario_loaderpy-parser-xlsx-do-inventário-base)
  - [Task 6: `confronto_service.py` — agregador principal](#task-6-confronto_servicepy-agregador-principal)
  - [Task 7: `snapshot_odoo_service.py` — refresh Odoo](#task-7-snapshot_odoo_servicepy-refresh-odoo)
  - [Task 8: `movimentacoes_odoo_service.py` — drill-down paginado](#task-8-movimentacoes_odoo_servicepy-drill-down-paginado)
  - [Task 9: `export_xlsx_service.py` — XLSX 6 abas](#task-9-export_xlsx_servicepy-xlsx-6-abas)
- [Phase 3 — Routes](#phase-3-routes)
  - [Task 10: `ciclo_routes.py` (CRUD + upload xlsx)](#task-10-ciclo_routespy-crud-upload-xlsx)
  - [Task 11: `confronto_routes.py` (tela principal + export)](#task-11-confronto_routespy-tela-principal-export)
  - [Task 12: `ajustes_manuais_routes.py` (CRUD inline)](#task-12-ajustes_manuais_routespy-crud-inline)
  - [Task 13: `snapshot_routes.py` (botão refresh + status job)](#task-13-snapshot_routespy-botão-refresh-status-job)
  - [Task 14: `movimentacoes_routes.py` (drill-down)](#task-14-movimentacoes_routespy-drill-down)
- [Phase 4 — Worker](#phase-4-worker)
  - [Task 15: Worker `refresh_snapshot_worker` + integração](#task-15-worker-refresh_snapshot_worker-integração)
- [Phase 5 — Frontend refinado (templates + JS + CSS)](#phase-5-frontend-refinado-templates-js-css)
  - [Task 16: Reformular `ciclos.html` com upload xlsx + criar ciclo](#task-16-reformular-cicloshtml-com-upload-xlsx-criar-ciclo)
  - [Task 17: Reformular `confronto.html` (tela principal interativa)](#task-17-reformular-confrontohtml-tela-principal-interativa)
  - [Task 18: Reformular `ajustes_manuais.html` (CRUD inline)](#task-18-reformular-ajustes_manuaishtml-crud-inline)
- [Phase 6 — Integração + Validação](#phase-6-integração-validação)
  - [Task 19: Adicionar link no menu `base.html`](#task-19-adicionar-link-no-menu-basehtml)
  - [Task 20: Test de rotas (integração)](#task-20-test-de-rotas-integração)
  - [Task 21: Rodar migration em PROD (Render)](#task-21-rodar-migration-em-prod-render)
  - [Task 22: Smoke test end-to-end](#task-22-smoke-test-end-to-end)
  - [Task 23: Validação PROD — comparar tela com dados reais Render](#task-23-validação-prod-comparar-tela-com-dados-reais-render)
- [Self-Review (concluído pelo writer)](#self-review-concluído-pelo-writer)
  - [Cobertura da spec](#cobertura-da-spec)
  - [Placeholder scan](#placeholder-scan)
  - [Type/method consistency](#typemethod-consistency)
- [Execução](#execução)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir módulo `app/inventario/` que replica a planilha-referência de confronto de inventário (Planilha1 em `MOVS_ESTOQUE_RENDER`), com tela HTML interativa, drill-down de movimentações on-demand, ajustes manuais persistidos e export XLSX 6 abas.

**Architecture:** Novo Flask Blueprint `inventario_bp` (url_prefix `/inventario`) com 4 modelos persistidos (CicloInventario, InventarioBase, AjusteManualInventario, InventarioSnapshotOdoo). Cache Odoo refrescável via worker RQ assíncrono (fila `inventario` — pesada). Drill-down e movimentações granulares consultam Odoo on-demand com paginação. Reaproveita lógica dos scripts CLI em `scripts/inventario_2026_05/monitor/`.

**Tech Stack:** Flask 3.1.2, SQLAlchemy 2.0, Flask-Login, RQ 2.6, Odoo XML-RPC, openpyxl/xlsxwriter, pytest, HTMX 1.9, Bootstrap 5.3, jQuery, design tokens CSS @layer.

**Spec:** `docs/superpowers/specs/2026-05-26-relatorio-confronto-inventario-design.md`

**Mapping validated against PROD 2026-05-26:** `tipo_movimentacao` values are ENTRADA / SAIDA / AJUSTE / **PRODUÇÃO** (com Ç) / **CONSUMO** / **FATURAMENTO** / REMESSA. Schema JSON outdated — fixed in Task 4.

**Companies:** FB=1, CD=4, LF=5. `DATA_INICIO_INV='2026-05-16 00:00:00'`.

---

## Phase 1 — Foundation (esqueleto, modelos, migrations, schema fix)

### Task 1: Criar esqueleto do módulo `app/inventario/`

**Files:**
- Create: `app/inventario/__init__.py`
- Create: `app/inventario/routes/__init__.py`
- Create: `app/inventario/services/__init__.py`
- Create: `app/inventario/workers/__init__.py`
- Modify: `app/__init__.py` (registrar blueprint)

- [ ] **Step 1: Criar diretórios e __init__.py do módulo**

```bash
mkdir -p app/inventario/routes app/inventario/services app/inventario/workers
mkdir -p app/templates/inventario
mkdir -p app/static/js/inventario
mkdir -p tests/inventario
```

- [ ] **Step 2: Criar `app/inventario/__init__.py`**

```python
"""Módulo de Inventário — Relatório de Confronto.

Cruza inventário físico FB/CD/LF com movimentações Odoo pós-inventário,
estoque atual Odoo, movimentações do sistema_fretes e ajustes manuais.
Spec: docs/superpowers/specs/2026-05-26-relatorio-confronto-inventario-design.md
"""
from flask import Blueprint

inventario_bp = Blueprint(
    'inventario',
    __name__,
    url_prefix='/inventario',
    template_folder='../templates/inventario',
)

# Importar routes para registrar handlers (após criar blueprint para evitar circular)
from app.inventario.routes import (  # noqa: E402, F401
    ciclo_routes,
    confronto_routes,
    ajustes_manuais_routes,
    snapshot_routes,
    movimentacoes_routes,
)
```

- [ ] **Step 3: Criar stubs vazios em routes/ e services/**

Criar arquivos vazios em:
- `app/inventario/routes/__init__.py` (vazio)
- `app/inventario/routes/ciclo_routes.py` (apenas `from app.inventario import inventario_bp`)
- `app/inventario/routes/confronto_routes.py` (idem)
- `app/inventario/routes/ajustes_manuais_routes.py` (idem)
- `app/inventario/routes/snapshot_routes.py` (idem)
- `app/inventario/routes/movimentacoes_routes.py` (idem)
- `app/inventario/services/__init__.py` (vazio)
- `app/inventario/workers/__init__.py` (vazio)

- [ ] **Step 4: Registrar blueprint em `app/__init__.py`**

Localizar bloco onde outros blueprints são registrados (procurar `register_blueprint(estoque_bp)`) e adicionar:

```python
from app.inventario import inventario_bp
app.register_blueprint(inventario_bp)
```

- [ ] **Step 5: Verificar app inicia sem erro**

Run: `source .venv/bin/activate && python -c "from app import create_app; app = create_app(); print('OK')"`
Expected: imprime `OK` sem erros.

- [ ] **Step 6: Commit**

```bash
git add app/inventario/ app/__init__.py app/templates/inventario tests/inventario
git commit -m "feat(inventario): esqueleto do módulo + blueprint registrado"
```

---

### Task 2: Criar modelos (4 tabelas)

**Files:**
- Create: `app/inventario/models.py`
- Test: `tests/inventario/test_models.py`
- Test: `tests/inventario/conftest.py`

- [ ] **Step 1: Criar `tests/inventario/conftest.py` com fixtures**

```python
"""Fixtures compartilhadas para testes do módulo inventario."""
import pytest
from datetime import date
from app import db, create_app
from app.inventario.models import (
    CicloInventario, InventarioBase, AjusteManualInventario,
    InventarioSnapshotOdoo,
)


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def ciclo(app):
    c = CicloInventario(
        codigo='INV-TESTE-2026-05',
        data_snapshot=date(2026, 5, 16),
        descricao='Ciclo de teste',
        status='ATIVO',
        criado_por='pytest',
    )
    db.session.add(c)
    db.session.flush()
    return c
```

- [ ] **Step 2: Escrever teste `test_models.py` (failing)**

```python
"""Testes dos modelos do módulo inventario."""
from datetime import date
from decimal import Decimal
from app import db
from app.inventario.models import (
    CicloInventario, InventarioBase, AjusteManualInventario,
    InventarioSnapshotOdoo,
)


def test_criar_ciclo_inventario(app):
    c = CicloInventario(
        codigo='INV-2026-05',
        data_snapshot=date(2026, 5, 16),
        descricao='Ciclo maio',
        status='ATIVO',
    )
    db.session.add(c)
    db.session.commit()
    assert c.id is not None
    assert c.criado_em is not None


def test_inventario_base_unique_constraint(app, ciclo):
    b1 = InventarioBase(
        ciclo_id=ciclo.id, cod_produto='4320147', empresa='FB',
        qtd=Decimal('100.000'),
    )
    db.session.add(b1)
    db.session.commit()

    b2 = InventarioBase(
        ciclo_id=ciclo.id, cod_produto='4320147', empresa='FB',
        qtd=Decimal('200.000'),
    )
    db.session.add(b2)
    import sqlalchemy.exc
    try:
        db.session.commit()
        assert False, 'esperava IntegrityError'
    except sqlalchemy.exc.IntegrityError:
        db.session.rollback()


def test_ajuste_manual_basico(app, ciclo):
    a = AjusteManualInventario(
        ciclo_id=ciclo.id, cod_produto='208000041',
        nome_produto='FILME TERMO ENCOLHIVEL', local='CD',
        qtd=Decimal('2120.800'), tipo_ajuste='POSITIVO',
        observacao='Ajuste pos-recontagem',
    )
    db.session.add(a)
    db.session.commit()
    assert a.id is not None
    assert a.atualizado_em is not None


def test_snapshot_odoo_unique_constraint(app, ciclo):
    s1 = InventarioSnapshotOdoo(
        ciclo_id=ciclo.id, cod_produto='4320147',
        estoque_fb=Decimal('500'), estoque_cd=Decimal('0'), estoque_lf=Decimal('200'),
    )
    db.session.add(s1)
    db.session.commit()

    s2 = InventarioSnapshotOdoo(
        ciclo_id=ciclo.id, cod_produto='4320147',
        estoque_fb=Decimal('999'),
    )
    db.session.add(s2)
    import sqlalchemy.exc
    try:
        db.session.commit()
        assert False, 'esperava IntegrityError'
    except sqlalchemy.exc.IntegrityError:
        db.session.rollback()
```

- [ ] **Step 3: Run test, fail (modelos ainda não existem)**

Run: `source .venv/bin/activate && pytest tests/inventario/test_models.py -v`
Expected: `ImportError: cannot import name 'CicloInventario'` ou similar.

- [ ] **Step 4: Implementar `app/inventario/models.py`**

```python
"""Modelos do módulo Inventário."""
from app import db
from app.utils.timezone import agora_utc_naive


class CicloInventario(db.Model):
    """Ciclo de inventário (ex.: INV-2026-05-16)."""
    __tablename__ = 'inventario_ciclo'

    id            = db.Column(db.Integer, primary_key=True)
    codigo        = db.Column(db.String(50), unique=True, nullable=False)
    data_snapshot = db.Column(db.Date, nullable=False)
    descricao     = db.Column(db.String(200))
    status        = db.Column(db.String(20), default='ATIVO', nullable=False)
    criado_em     = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    criado_por    = db.Column(db.String(100))

    __table_args__ = (
        db.Index('ix_inventario_ciclo_status', 'status'),
    )

    def __repr__(self):
        return f'<CicloInventario {self.codigo}>'


class InventarioBase(db.Model):
    """Snapshot físico FB/CD/LF (uma linha por cod + empresa)."""
    __tablename__ = 'inventario_base'

    id           = db.Column(db.Integer, primary_key=True)
    ciclo_id     = db.Column(db.Integer, db.ForeignKey('inventario_ciclo.id'),
                             nullable=False, index=True)
    cod_produto  = db.Column(db.String(50), nullable=False, index=True)
    nome_produto = db.Column(db.String(200))
    empresa      = db.Column(db.String(10), nullable=False)
    qtd          = db.Column(db.Numeric(15, 3), nullable=False, default=0)

    __table_args__ = (
        db.UniqueConstraint('ciclo_id', 'cod_produto', 'empresa',
                            name='uq_inv_base_ciclo_cod_empresa'),
    )


class AjusteManualInventario(db.Model):
    """Ajustes manuais (Planilha2)."""
    __tablename__ = 'inventario_ajuste_manual'

    id            = db.Column(db.Integer, primary_key=True)
    ciclo_id      = db.Column(db.Integer, db.ForeignKey('inventario_ciclo.id'),
                              nullable=False, index=True)
    cod_produto   = db.Column(db.String(50), nullable=False, index=True)
    nome_produto  = db.Column(db.String(200))
    local         = db.Column(db.String(20))
    qtd           = db.Column(db.Numeric(15, 3), nullable=False)
    tipo_ajuste   = db.Column(db.String(20))
    observacao    = db.Column(db.String(500))
    criado_em     = db.Column(db.DateTime, default=agora_utc_naive, nullable=False)
    atualizado_em = db.Column(db.DateTime, default=agora_utc_naive,
                              onupdate=agora_utc_naive, nullable=False)
    criado_por    = db.Column(db.String(100))


class InventarioSnapshotOdoo(db.Model):
    """Cache de estoque + apontamentos + compras do Odoo."""
    __tablename__ = 'inventario_snapshot_odoo'

    id             = db.Column(db.Integer, primary_key=True)
    ciclo_id       = db.Column(db.Integer, db.ForeignKey('inventario_ciclo.id'),
                               nullable=False, index=True)
    cod_produto    = db.Column(db.String(50), nullable=False, index=True)
    nome_produto   = db.Column(db.String(200))
    estoque_fb     = db.Column(db.Numeric(15, 3), default=0)
    estoque_cd     = db.Column(db.Numeric(15, 3), default=0)
    estoque_lf     = db.Column(db.Numeric(15, 3), default=0)
    pa_qtd         = db.Column(db.Numeric(15, 3), default=0)
    componente_qtd = db.Column(db.Numeric(15, 3), default=0)
    compras_qtd    = db.Column(db.Numeric(15, 3), default=0)
    refresh_em     = db.Column(db.DateTime, default=agora_utc_naive)

    __table_args__ = (
        db.UniqueConstraint('ciclo_id', 'cod_produto',
                            name='uq_inv_snapshot_ciclo_cod'),
    )
```

- [ ] **Step 5: Run tests, expect pass**

Run: `source .venv/bin/activate && pytest tests/inventario/test_models.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add app/inventario/models.py tests/inventario/conftest.py tests/inventario/test_models.py
git commit -m "feat(inventario): modelos CicloInventario, InventarioBase, AjusteManualInventario, InventarioSnapshotOdoo"
```

---

### Task 3: Migrations DDL (Python + SQL idempotente)

**Files:**
- Create: `scripts/migrations/inventario_create_tables.py`
- Create: `scripts/migrations/inventario_create_tables.sql`

- [ ] **Step 1: Criar `scripts/migrations/inventario_create_tables.py`**

```python
"""Migration: criar tabelas do módulo inventario.

Tabelas: inventario_ciclo, inventario_base, inventario_ajuste_manual,
         inventario_snapshot_odoo
Spec: docs/superpowers/specs/2026-05-26-relatorio-confronto-inventario-design.md
"""
import sys
from pathlib import Path

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app, db  # noqa: E402
from app.inventario.models import (  # noqa: E402
    CicloInventario, InventarioBase, AjusteManualInventario, InventarioSnapshotOdoo,
)
from sqlalchemy import inspect  # noqa: E402


TABELAS = [
    'inventario_ciclo',
    'inventario_base',
    'inventario_ajuste_manual',
    'inventario_snapshot_odoo',
]


def main():
    app = create_app()
    with app.app_context():
        insp = inspect(db.engine)
        before = {t: t in insp.get_table_names() for t in TABELAS}
        print('ANTES:')
        for t, exists in before.items():
            print(f'  {t}: {"existe" if exists else "AUSENTE"}')

        # Criar apenas as tabelas dos modelos do módulo inventario
        for model in [CicloInventario, InventarioBase, AjusteManualInventario,
                      InventarioSnapshotOdoo]:
            model.__table__.create(db.engine, checkfirst=True)

        insp = inspect(db.engine)
        after = {t: t in insp.get_table_names() for t in TABELAS}
        print('\nDEPOIS:')
        for t, exists in after.items():
            print(f'  {t}: {"existe" if exists else "AUSENTE"}')

        criadas = [t for t in TABELAS if not before[t] and after[t]]
        print(f'\nCriadas: {len(criadas)} ({", ".join(criadas) or "nenhuma"})')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Criar `scripts/migrations/inventario_create_tables.sql`**

```sql
-- Migration: tabelas do módulo inventario (idempotente)
-- Roda em Render Shell: \i scripts/migrations/inventario_create_tables.sql

CREATE TABLE IF NOT EXISTS inventario_ciclo (
    id            SERIAL PRIMARY KEY,
    codigo        VARCHAR(50) UNIQUE NOT NULL,
    data_snapshot DATE NOT NULL,
    descricao     VARCHAR(200),
    status        VARCHAR(20) NOT NULL DEFAULT 'ATIVO',
    criado_em     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por    VARCHAR(100)
);
CREATE INDEX IF NOT EXISTS ix_inventario_ciclo_status ON inventario_ciclo(status);

CREATE TABLE IF NOT EXISTS inventario_base (
    id           SERIAL PRIMARY KEY,
    ciclo_id     INTEGER NOT NULL REFERENCES inventario_ciclo(id),
    cod_produto  VARCHAR(50) NOT NULL,
    nome_produto VARCHAR(200),
    empresa      VARCHAR(10) NOT NULL,
    qtd          NUMERIC(15, 3) NOT NULL DEFAULT 0,
    CONSTRAINT uq_inv_base_ciclo_cod_empresa UNIQUE (ciclo_id, cod_produto, empresa)
);
CREATE INDEX IF NOT EXISTS ix_inventario_base_ciclo_id ON inventario_base(ciclo_id);
CREATE INDEX IF NOT EXISTS ix_inventario_base_cod_produto ON inventario_base(cod_produto);

CREATE TABLE IF NOT EXISTS inventario_ajuste_manual (
    id            SERIAL PRIMARY KEY,
    ciclo_id      INTEGER NOT NULL REFERENCES inventario_ciclo(id),
    cod_produto   VARCHAR(50) NOT NULL,
    nome_produto  VARCHAR(200),
    local         VARCHAR(20),
    qtd           NUMERIC(15, 3) NOT NULL,
    tipo_ajuste   VARCHAR(20),
    observacao    VARCHAR(500),
    criado_em     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    criado_por    VARCHAR(100)
);
CREATE INDEX IF NOT EXISTS ix_inventario_ajuste_manual_ciclo_id ON inventario_ajuste_manual(ciclo_id);
CREATE INDEX IF NOT EXISTS ix_inventario_ajuste_manual_cod_produto ON inventario_ajuste_manual(cod_produto);

CREATE TABLE IF NOT EXISTS inventario_snapshot_odoo (
    id             SERIAL PRIMARY KEY,
    ciclo_id       INTEGER NOT NULL REFERENCES inventario_ciclo(id),
    cod_produto    VARCHAR(50) NOT NULL,
    nome_produto   VARCHAR(200),
    estoque_fb     NUMERIC(15, 3) DEFAULT 0,
    estoque_cd     NUMERIC(15, 3) DEFAULT 0,
    estoque_lf     NUMERIC(15, 3) DEFAULT 0,
    pa_qtd         NUMERIC(15, 3) DEFAULT 0,
    componente_qtd NUMERIC(15, 3) DEFAULT 0,
    compras_qtd    NUMERIC(15, 3) DEFAULT 0,
    refresh_em     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_inv_snapshot_ciclo_cod UNIQUE (ciclo_id, cod_produto)
);
CREATE INDEX IF NOT EXISTS ix_inventario_snapshot_odoo_ciclo_id ON inventario_snapshot_odoo(ciclo_id);
CREATE INDEX IF NOT EXISTS ix_inventario_snapshot_odoo_cod_produto ON inventario_snapshot_odoo(cod_produto);
```

- [ ] **Step 3: Rodar migration Python local**

Run: `source .venv/bin/activate && python scripts/migrations/inventario_create_tables.py`
Expected: stdout mostra `Criadas: 4 (inventario_ciclo, inventario_base, inventario_ajuste_manual, inventario_snapshot_odoo)`.

- [ ] **Step 4: Validar tabelas existem (local)**

Run: `source .venv/bin/activate && python -c "from app import create_app, db; from sqlalchemy import inspect; app = create_app(); ctx = app.app_context(); ctx.push(); print([t for t in inspect(db.engine).get_table_names() if t.startswith('inventario_')])"`
Expected: `['inventario_ajuste_manual', 'inventario_base', 'inventario_ciclo', 'inventario_snapshot_odoo']`

- [ ] **Step 5: Commit**

```bash
git add scripts/migrations/inventario_create_tables.py scripts/migrations/inventario_create_tables.sql
git commit -m "feat(inventario): migration DDL (Python + SQL idempotente)"
```

---

### Task 4: Fix schema JSON desatualizado de `movimentacao_estoque`

**Files:**
- Modify: `.claude/skills/consultando-sql/schemas/tables/movimentacao_estoque.json`

- [ ] **Step 1: Atualizar valores válidos de `tipo_movimentacao`**

Editar o arquivo: na entrada `name: tipo_movimentacao` linha ~26-30, mudar a `description` de:
```
"description": "ENTRADA, SAIDA, AJUSTE, PRODUCAO"
```
para:
```
"description": "ENTRADA, SAIDA, AJUSTE, PRODUÇÃO (com Ç), CONSUMO, FATURAMENTO, REMESSA — validado em PROD 2026-05-26"
```

- [ ] **Step 2: Atualizar valores válidos de `local_movimentacao`**

Mudar a `description` de:
```
"description": "COMPRA, VENDA, PRODUCAO, AJUSTE, DEVOLUCAO"
```
para:
```
"description": "COMPRA, VENDA, AJUSTE, DEVOLUCAO, TRANSFERENCIA, REVERSAO, PALLET + códigos de operação (1101-*, 1104, 1105, 1106) — validado em PROD 2026-05-26"
```

- [ ] **Step 3: Verificar JSON é válido**

Run: `source .venv/bin/activate && python -c "import json; json.load(open('.claude/skills/consultando-sql/schemas/tables/movimentacao_estoque.json'))"`
Expected: sem erro.

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/consultando-sql/schemas/tables/movimentacao_estoque.json
git commit -m "fix(schema): atualizar tipo_movimentacao/local_movimentacao com valores reais PROD"
```

---

## Phase 2 — Services (lógica de negócio)

### Task 5: `inventario_loader.py` — parser xlsx do inventário base

**Files:**
- Create: `app/inventario/services/inventario_loader.py`
- Test: `tests/inventario/test_inventario_loader.py`

- [ ] **Step 1: Criar fixture xlsx de teste**

Criar `tests/inventario/conftest.py` (append ao existente):

```python
import io
import openpyxl


def _make_test_xlsx(rows_por_aba):
    """Cria xlsx em memória com abas FB/CD/LF e dados.

    rows_por_aba = {'FB': [(cod, lote, qtd), ...], 'CD': [...], 'LF': [...]}
    """
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for aba, rows in rows_por_aba.items():
        ws = wb.create_sheet(aba)
        ws.append(['CODIGO', 'LOTE', 'QTD'])
        for r in rows:
            ws.append(list(r))
    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf


@pytest.fixture
def xlsx_valido():
    return _make_test_xlsx({
        'FB': [('4320147', '139/26', 100), ('208000041', '', 50)],
        'CD': [('4320147', '139/26', 200), ('103000037', '023/26', 75.5)],
        'LF': [('4320147', '139/26', 50)],
    })


@pytest.fixture
def xlsx_com_invalidos():
    """Inclui código que começa com letra (deve pular) e qtd negativa."""
    return _make_test_xlsx({
        'FB': [('CHAVE-X', '', 10), ('4320147', '139/26', 100)],
        'CD': [('208000041', '', -5)],
        'LF': [],
    })
```

- [ ] **Step 2: Escrever testes (failing)**

`tests/inventario/test_inventario_loader.py`:

```python
"""Testes do parser xlsx de inventário base."""
from decimal import Decimal
from app import db
from app.inventario.models import InventarioBase
from app.inventario.services.inventario_loader import InventarioLoader


def test_parse_xlsx_valido(app, ciclo, xlsx_valido):
    resultado = InventarioLoader.carregar(ciclo.id, xlsx_valido, criado_por='test')
    assert resultado['inseridos'] == 5
    assert resultado['pulados'] == 0
    assert len(resultado['erros']) == 0

    rows = InventarioBase.query.filter_by(ciclo_id=ciclo.id).all()
    assert len(rows) == 5
    fb_4320147 = next(r for r in rows if r.cod_produto == '4320147' and r.empresa == 'FB')
    assert fb_4320147.qtd == Decimal('100.000')


def test_parse_xlsx_pula_codigo_invalido(app, ciclo, xlsx_com_invalidos):
    resultado = InventarioLoader.carregar(ciclo.id, xlsx_com_invalidos, criado_por='test')
    assert resultado['pulados'] == 1  # CHAVE-X
    assert resultado['inseridos'] == 1  # 4320147
    assert any('CHAVE-X' in e or 'pulado' in e.lower() for e in resultado['erros'])


def test_parse_xlsx_qtd_negativa_erro(app, ciclo, xlsx_com_invalidos):
    resultado = InventarioLoader.carregar(ciclo.id, xlsx_com_invalidos, criado_por='test')
    assert any('-5' in e or 'negativ' in e.lower() for e in resultado['erros'])


def test_reupload_substitui_linhas(app, ciclo, xlsx_valido):
    InventarioLoader.carregar(ciclo.id, xlsx_valido, criado_por='test')
    assert InventarioBase.query.filter_by(ciclo_id=ciclo.id).count() == 5

    # Re-upload com 1 produto só
    from tests.inventario.conftest import _make_test_xlsx
    novo = _make_test_xlsx({'FB': [('NOVO_PROD', '', 999)], 'CD': [], 'LF': []})
    resultado = InventarioLoader.carregar(ciclo.id, novo, criado_por='test')
    # Atenção: cod NOVO_PROD começa com 'N' -> pulado. Esperado: 0 inseridos.
    # Mas DELETE das linhas antigas deve ter rodado mesmo assim.
    assert InventarioBase.query.filter_by(ciclo_id=ciclo.id).count() == 0
```

- [ ] **Step 3: Run tests, expect fail**

Run: `source .venv/bin/activate && pytest tests/inventario/test_inventario_loader.py -v`
Expected: ImportError.

- [ ] **Step 4: Implementar `app/inventario/services/inventario_loader.py`**

```python
"""Parser do xlsx de inventário base (3 abas FB/CD/LF).

Reaproveita lógica do scripts/inventario_2026_05/02_carregar_inventario_xlsx.py.
"""
from decimal import Decimal, InvalidOperation
from typing import IO, Dict
import openpyxl
from app import db
from app.inventario.models import InventarioBase


TIPOS_CODIGO_ACEITOS = {'1', '2', '3', '4'}

HEADER_ALIASES = {
    'codigo': 'cod_produto',
    'cod': 'cod_produto',
    'cod_produto': 'cod_produto',
    'lote': 'lote',
    'qtd': 'qtd',
    'quantidade': 'qtd',
    'qtd_contada': 'qtd',
    'descricao': 'nome_produto',
    'produto': 'nome_produto',
    'nome_produto': 'nome_produto',
}

EMPRESAS_ESPERADAS = ('FB', 'CD', 'LF')


class InventarioLoader:
    """Carrega xlsx em InventarioBase, substituindo linhas do ciclo."""

    @staticmethod
    def carregar(ciclo_id: int, file_storage: IO, criado_por: str) -> Dict:
        """Parse xlsx + DELETE linhas antigas do ciclo + INSERT novas.

        Returns: {'inseridos': N, 'pulados': M, 'erros': [str, ...]}
        """
        wb = openpyxl.load_workbook(file_storage, data_only=True)
        abas_presentes = set(wb.sheetnames)
        abas_faltando = set(EMPRESAS_ESPERADAS) - abas_presentes
        if abas_faltando:
            return {
                'inseridos': 0, 'pulados': 0,
                'erros': [f'Abas faltando: {sorted(abas_faltando)}. '
                          f'Esperado: FB, CD, LF.'],
            }

        # DELETE linhas antigas (substitutiva)
        InventarioBase.query.filter_by(ciclo_id=ciclo_id).delete()
        db.session.flush()

        inseridos = pulados = 0
        erros = []
        for empresa in EMPRESAS_ESPERADAS:
            ws = wb[empresa]
            rows_iter = ws.iter_rows(values_only=True)
            try:
                header = next(rows_iter)
            except StopIteration:
                erros.append(f'Aba {empresa} vazia.')
                continue

            col_idx = {}
            for i, h in enumerate(header):
                if not h:
                    continue
                key = HEADER_ALIASES.get(str(h).strip().lower())
                if key:
                    col_idx[key] = i

            if 'cod_produto' not in col_idx or 'qtd' not in col_idx:
                erros.append(f'Aba {empresa}: faltam colunas CODIGO/QTD.')
                continue

            for nrow, row in enumerate(rows_iter, start=2):
                cod = row[col_idx['cod_produto']]
                if cod is None:
                    continue
                cod = str(cod).strip()
                if not cod:
                    continue
                if not cod[0] in TIPOS_CODIGO_ACEITOS:
                    pulados += 1
                    erros.append(f'Aba {empresa} linha {nrow}: '
                                 f'cod_produto={cod} pulado (não começa com 1-4)')
                    continue

                qtd_raw = row[col_idx['qtd']]
                try:
                    qtd = Decimal(str(qtd_raw or 0))
                except (InvalidOperation, ValueError):
                    erros.append(f'Aba {empresa} linha {nrow}: qtd inválida={qtd_raw}')
                    continue
                if qtd < 0:
                    erros.append(f'Aba {empresa} linha {nrow}: '
                                 f'qtd negativa={qtd} para cod={cod}')
                    continue

                nome = row[col_idx['nome_produto']] if 'nome_produto' in col_idx else None
                db.session.add(InventarioBase(
                    ciclo_id=ciclo_id,
                    cod_produto=cod,
                    nome_produto=str(nome).strip() if nome else None,
                    empresa=empresa,
                    qtd=qtd,
                ))
                inseridos += 1

        db.session.flush()  # commit fica para o caller
        return {'inseridos': inseridos, 'pulados': pulados, 'erros': erros}
```

- [ ] **Step 5: Run tests, expect pass**

Run: `source .venv/bin/activate && pytest tests/inventario/test_inventario_loader.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add app/inventario/services/inventario_loader.py tests/inventario/test_inventario_loader.py tests/inventario/conftest.py
git commit -m "feat(inventario): InventarioLoader (parser xlsx FB/CD/LF)"
```

---

### Task 6: `confronto_service.py` — agregador principal

**Files:**
- Create: `app/inventario/services/confronto_service.py`
- Test: `tests/inventario/test_confronto_service.py`

- [ ] **Step 1: Escrever testes (failing)**

```python
"""Testes do ConfrontoService."""
from datetime import date, datetime
from decimal import Decimal
from app import db
from app.inventario.models import (
    InventarioBase, AjusteManualInventario, InventarioSnapshotOdoo,
)
from app.estoque.models import MovimentacaoEstoque
from app.inventario.services.confronto_service import ConfrontoService


def _add_mov(cod, tipo, local, qtd, data='2026-05-20'):
    m = MovimentacaoEstoque(
        cod_produto=cod, nome_produto=f'PROD {cod}',
        data_movimentacao=datetime.fromisoformat(data),
        tipo_movimentacao=tipo, local_movimentacao=local,
        qtd_movimentacao=Decimal(str(qtd)),
        tipo_origem='ODOO',
        criado_em=datetime.fromisoformat(data),
        atualizado_em=datetime.fromisoformat(data),
        ativo=True,
    )
    db.session.add(m)
    return m


def test_linha_so_com_inventario_base(app, ciclo):
    db.session.add(InventarioBase(
        ciclo_id=ciclo.id, cod_produto='4320147', empresa='FB',
        qtd=Decimal('100'), nome_produto='PROD 4320147'))
    db.session.commit()

    linhas = ConfrontoService.montar_linhas(ciclo.id)
    assert len(linhas) == 1
    l = linhas[0]
    assert l['cod_produto'] == '4320147'
    assert l['inv_fb'] == Decimal('100')
    assert l['inv_cd'] == Decimal('0')
    assert l['inv_lf'] == Decimal('0')
    assert l['inv_total'] == Decimal('100')
    assert l['compras'] == Decimal('0')
    assert l['sist'] == Decimal('0')


def test_linha_com_compras_venda_consumo_producao(app, ciclo):
    db.session.add(InventarioBase(
        ciclo_id=ciclo.id, cod_produto='4320147', empresa='FB', qtd=Decimal('100')))
    _add_mov('4320147', 'ENTRADA', 'COMPRA', 50)
    _add_mov('4320147', 'FATURAMENTO', 'VENDA', -20)
    _add_mov('4320147', 'CONSUMO', 'LF', -30)
    _add_mov('4320147', 'PRODUÇÃO', '1106', 80)
    db.session.commit()

    linhas = ConfrontoService.montar_linhas(ciclo.id)
    l = next(x for x in linhas if x['cod_produto'] == '4320147')
    assert l['compras'] == Decimal('50')
    assert l['vendas'] == Decimal('-20')
    assert l['consumo'] == Decimal('-30')
    assert l['producao'] == Decimal('80')
    # sist = soma de todas movs
    assert l['sist'] == Decimal('80')  # 50 - 20 - 30 + 80 = 80


def test_linha_com_snapshot_odoo(app, ciclo):
    db.session.add(InventarioSnapshotOdoo(
        ciclo_id=ciclo.id, cod_produto='4320147',
        estoque_fb=Decimal('150'), estoque_cd=Decimal('50'),
        estoque_lf=Decimal('30'), pa_qtd=Decimal('80'),
        componente_qtd=Decimal('40'), compras_qtd=Decimal('50'),
    ))
    db.session.commit()

    linhas = ConfrontoService.montar_linhas(ciclo.id)
    l = linhas[0]
    assert l['odoo'] == Decimal('230')  # 150+50+30
    assert l['est_fb'] == Decimal('150')
    assert l['pa'] == Decimal('80')
    assert l['componente'] == Decimal('-40')  # negado para apresentação


def test_linha_com_ajuste_manual(app, ciclo):
    db.session.add(AjusteManualInventario(
        ciclo_id=ciclo.id, cod_produto='208000041',
        local='CD', qtd=Decimal('2120.8'), tipo_ajuste='POSITIVO',
        observacao='Ajuste pos-recontagem',
    ))
    db.session.commit()
    linhas = ConfrontoService.montar_linhas(ciclo.id)
    l = next(x for x in linhas if x['cod_produto'] == '208000041')
    assert l['ajuste_local'] == 'CD'
    assert l['ajuste_qtd'] == Decimal('2120.8')
    assert l['ajuste_tipo'] == 'POSITIVO'


def test_calculo_mov_e_diferencas(app, ciclo):
    db.session.add(InventarioBase(
        ciclo_id=ciclo.id, cod_produto='X', empresa='FB', qtd=Decimal('100')))
    db.session.add(InventarioSnapshotOdoo(
        ciclo_id=ciclo.id, cod_produto='X',
        estoque_fb=Decimal('150'), pa_qtd=Decimal('80'),
        componente_qtd=Decimal('40'),
    ))
    _add_mov('X', 'ENTRADA', 'COMPRA', 50)
    db.session.commit()

    linhas = ConfrontoService.montar_linhas(ciclo.id)
    l = linhas[0]
    # MOV = inv_total + compras + pa + componente_apresentacao(negativo)
    # = 100 + 50 + 80 + (-40) = 190
    assert l['mov'] == Decimal('190')
    # odoo - mov = 150 - 190 = -40
    assert l['odoo_menos_mov'] == Decimal('-40')


def test_unificacao_codigos(app, ciclo):
    """Quando cod_produto_raiz preenchido, agrega no raiz."""
    db.session.add(InventarioBase(
        ciclo_id=ciclo.id, cod_produto='RAIZ', empresa='FB', qtd=Decimal('100')))
    _add_mov('FILHO1', 'ENTRADA', 'COMPRA', 30)
    db.session.commit()
    # adicionar cod_produto_raiz='RAIZ' à mov FILHO1
    m = MovimentacaoEstoque.query.filter_by(cod_produto='FILHO1').first()
    m.cod_produto_raiz = 'RAIZ'
    db.session.commit()

    linhas = ConfrontoService.montar_linhas(ciclo.id)
    l = next(x for x in linhas if x['cod_produto'] == 'RAIZ')
    assert l['compras'] == Decimal('30')  # FILHO1 agregado em RAIZ
```

- [ ] **Step 2: Run tests, expect fail**

Run: `source .venv/bin/activate && pytest tests/inventario/test_confronto_service.py -v`
Expected: ImportError.

- [ ] **Step 3: Implementar `app/inventario/services/confronto_service.py`**

```python
"""Agregador principal do Relatório de Confronto de Inventário."""
from decimal import Decimal
from typing import List, Dict, Any
from sqlalchemy import func, case, or_
from app import db
from app.inventario.models import (
    CicloInventario, InventarioBase, AjusteManualInventario,
    InventarioSnapshotOdoo,
)
from app.estoque.models import MovimentacaoEstoque


class ConfrontoService:
    """Monta as linhas do Relatório de Confronto."""

    EMPRESAS = ('FB', 'CD', 'LF')

    @staticmethod
    def montar_linhas(ciclo_id: int) -> List[Dict[str, Any]]:
        ciclo = CicloInventario.query.get(ciclo_id)
        if ciclo is None:
            return []
        data_inicio = ciclo.data_snapshot

        inv = ConfrontoService._agg_inventario_base(ciclo_id)
        snap = ConfrontoService._agg_snapshot(ciclo_id)
        movs = ConfrontoService._agg_movimentacoes(data_inicio)
        ajustes = ConfrontoService._agg_ajustes(ciclo_id)

        # set master de cod_produto (união das 4 fontes)
        cods = set(inv.keys()) | set(snap.keys()) | set(movs.keys()) | set(ajustes.keys())

        linhas = []
        for cod in sorted(cods):
            i = inv.get(cod, {})
            s = snap.get(cod, {})
            m = movs.get(cod, {})
            a = ajustes.get(cod, {})

            inv_fb = i.get('fb', Decimal('0'))
            inv_cd = i.get('cd', Decimal('0'))
            inv_lf = i.get('lf', Decimal('0'))
            inv_total = inv_fb + inv_cd + inv_lf

            compras = m.get('compras', Decimal('0'))
            vendas = m.get('vendas', Decimal('0'))
            consumo = m.get('consumo', Decimal('0'))
            producao = m.get('producao', Decimal('0'))
            sist_total = m.get('sist_total', Decimal('0'))

            est_fb = s.get('estoque_fb', Decimal('0'))
            est_cd = s.get('estoque_cd', Decimal('0'))
            est_lf = s.get('estoque_lf', Decimal('0'))
            odoo_total = est_fb + est_cd + est_lf
            pa = s.get('pa_qtd', Decimal('0'))
            componente_pos = s.get('componente_qtd', Decimal('0'))
            componente_apres = -componente_pos  # apresentação negativa

            mov = inv_total + compras + pa + componente_apres
            odoo_menos_mov = odoo_total - mov
            sist_menos_mov = sist_total - mov

            nome = (i.get('nome') or s.get('nome') or
                    m.get('nome') or a.get('nome') or '')

            linhas.append({
                'cod_produto': cod,
                'nome_produto': nome,
                'inv_fb': inv_fb, 'inv_cd': inv_cd, 'inv_lf': inv_lf,
                'inv_total': inv_total,
                'compras': compras,
                'pa': pa,
                'componente': componente_apres,
                'vendas': vendas,
                'consumo': consumo,
                'producao': producao,
                'ajuste_local': a.get('local'),
                'ajuste_qtd': a.get('qtd'),
                'ajuste_tipo': a.get('tipo_ajuste'),
                'ajuste_obs': a.get('observacao'),
                'odoo': odoo_total,
                'mov': mov,
                'sist': sist_total,
                'odoo_menos_mov': odoo_menos_mov,
                'sist_menos_mov': sist_menos_mov,
                'est_fb': est_fb,
                'est_cd': est_cd,
                'est_lf': est_lf,
                'snapshot_compras': s.get('compras_qtd'),
                'flag_divergencia_compras': (
                    s.get('compras_qtd') is not None
                    and abs((s.get('compras_qtd') or 0) - compras) > Decimal('1')
                ),
            })
        return linhas

    @staticmethod
    def _agg_inventario_base(ciclo_id):
        """{cod: {fb, cd, lf, nome}}"""
        q = db.session.query(
            InventarioBase.cod_produto,
            func.max(InventarioBase.nome_produto),
            func.sum(case((InventarioBase.empresa == 'FB', InventarioBase.qtd),
                          else_=0)),
            func.sum(case((InventarioBase.empresa == 'CD', InventarioBase.qtd),
                          else_=0)),
            func.sum(case((InventarioBase.empresa == 'LF', InventarioBase.qtd),
                          else_=0)),
        ).filter(InventarioBase.ciclo_id == ciclo_id).group_by(InventarioBase.cod_produto)
        return {r[0]: {'nome': r[1], 'fb': r[2] or Decimal('0'),
                       'cd': r[3] or Decimal('0'), 'lf': r[4] or Decimal('0')}
                for r in q.all()}

    @staticmethod
    def _agg_snapshot(ciclo_id):
        """{cod: {estoque_fb, estoque_cd, estoque_lf, pa_qtd, componente_qtd,
                  compras_qtd, nome}}"""
        rows = InventarioSnapshotOdoo.query.filter_by(ciclo_id=ciclo_id).all()
        return {r.cod_produto: {
            'nome': r.nome_produto,
            'estoque_fb': r.estoque_fb or Decimal('0'),
            'estoque_cd': r.estoque_cd or Decimal('0'),
            'estoque_lf': r.estoque_lf or Decimal('0'),
            'pa_qtd': r.pa_qtd or Decimal('0'),
            'componente_qtd': r.componente_qtd or Decimal('0'),
            'compras_qtd': r.compras_qtd,
        } for r in rows}

    @staticmethod
    def _agg_movimentacoes(data_inicio):
        """{cod_raiz: {compras, vendas, consumo, producao, sist_total, nome}}

        Usa COALESCE(cod_produto_raiz, cod_produto) para resolver unificação.
        sist_total considera TODO histórico (não filtrado por data) — é o saldo.
        """
        # Agregado filtrado por data (compras/vendas/consumo/producao)
        cod_raiz = func.coalesce(
            MovimentacaoEstoque.cod_produto_raiz, MovimentacaoEstoque.cod_produto
        ).label('raiz')

        q_periodo = db.session.query(
            cod_raiz,
            func.max(MovimentacaoEstoque.nome_produto),
            func.sum(case((db.and_(
                MovimentacaoEstoque.tipo_movimentacao == 'ENTRADA',
                MovimentacaoEstoque.local_movimentacao == 'COMPRA',
            ), MovimentacaoEstoque.qtd_movimentacao), else_=0)),
            func.sum(case((MovimentacaoEstoque.tipo_movimentacao == 'FATURAMENTO',
                           MovimentacaoEstoque.qtd_movimentacao), else_=0)),
            func.sum(case((MovimentacaoEstoque.tipo_movimentacao == 'CONSUMO',
                           MovimentacaoEstoque.qtd_movimentacao), else_=0)),
            func.sum(case((MovimentacaoEstoque.tipo_movimentacao == 'PRODUÇÃO',
                           MovimentacaoEstoque.qtd_movimentacao), else_=0)),
        ).filter(
            MovimentacaoEstoque.ativo.is_(True),
            MovimentacaoEstoque.data_movimentacao >= data_inicio,
        ).group_by(cod_raiz)

        periodo = {r[0]: {
            'nome': r[1],
            'compras': r[2] or Decimal('0'),
            'vendas': r[3] or Decimal('0'),
            'consumo': r[4] or Decimal('0'),
            'producao': r[5] or Decimal('0'),
        } for r in q_periodo.all()}

        # sist_total: saldo de movimentacao_estoque (sem filtro de data)
        q_saldo = db.session.query(
            cod_raiz,
            func.sum(MovimentacaoEstoque.qtd_movimentacao),
        ).filter(MovimentacaoEstoque.ativo.is_(True)).group_by(cod_raiz)

        for cod, sist in q_saldo.all():
            if cod not in periodo:
                periodo[cod] = {'nome': '', 'compras': Decimal('0'),
                                'vendas': Decimal('0'), 'consumo': Decimal('0'),
                                'producao': Decimal('0')}
            periodo[cod]['sist_total'] = sist or Decimal('0')

        # default sist_total = 0 para os que só apareceram no período
        for cod in periodo:
            periodo[cod].setdefault('sist_total', Decimal('0'))
        return periodo

    @staticmethod
    def _agg_ajustes(ciclo_id):
        """{cod: {local, qtd (último), tipo_ajuste, observacao, nome}}

        Se >1 linha por cod: concatena obs e usa último.
        """
        rows = AjusteManualInventario.query.filter_by(ciclo_id=ciclo_id).order_by(
            AjusteManualInventario.criado_em).all()
        out = {}
        for r in rows:
            cur = out.setdefault(r.cod_produto, {
                'local': r.local, 'qtd': r.qtd, 'tipo_ajuste': r.tipo_ajuste,
                'observacao': r.observacao or '', 'nome': r.nome_produto or '',
            })
            # sobrescrever com último, mas concatenar observação
            cur['local'] = r.local
            cur['qtd'] = r.qtd
            cur['tipo_ajuste'] = r.tipo_ajuste
            if r.observacao and r.observacao not in cur['observacao']:
                cur['observacao'] = (cur['observacao'] + ' | ' + r.observacao).strip(' |')
        return out
```

- [ ] **Step 4: Run tests, expect pass**

Run: `source .venv/bin/activate && pytest tests/inventario/test_confronto_service.py -v`
Expected: 6 passed.

- [ ] **Step 5: Commit**

```bash
git add app/inventario/services/confronto_service.py tests/inventario/test_confronto_service.py
git commit -m "feat(inventario): ConfrontoService (agregador principal das linhas)"
```

---

### Task 7: `snapshot_odoo_service.py` — refresh Odoo

**Files:**
- Create: `app/inventario/services/snapshot_odoo_service.py`
- Test: `tests/inventario/test_snapshot_odoo_service.py`

- [ ] **Step 1: Escrever teste com mock Odoo (failing)**

```python
"""Testes do SnapshotOdooService com mock Odoo."""
from decimal import Decimal
from unittest.mock import patch, MagicMock
from app import db
from app.inventario.models import InventarioSnapshotOdoo
from app.inventario.services.snapshot_odoo_service import SnapshotOdooService


def _mk_odoo_mock():
    odoo = MagicMock()
    # stock.quant: 1 produto com saldo em FB e LF
    odoo.search.return_value = [10, 20]
    odoo.read.side_effect = lambda model, ids, fields: {
        'stock.quant': [
            {'id': 10, 'company_id': [1, 'FB'], 'product_id': [100, '[4320147] PROD'],
             'location_id': [50, 'FB/Estoque'], 'quantity': 150.0,
             'reserved_quantity': 0},
            {'id': 20, 'company_id': [5, 'LF'], 'product_id': [100, '[4320147] PROD'],
             'location_id': [60, 'LF/Estoque'], 'quantity': 30.0,
             'reserved_quantity': 0},
        ],
        'product.product': [{'id': 100, 'name': 'PROD AZEITONA',
                             'default_code': '4320147'}],
    }.get(model, [])
    return odoo


def test_refresh_grava_estoque_por_empresa(app, ciclo):
    odoo = _mk_odoo_mock()
    with patch('app.inventario.services.snapshot_odoo_service.get_odoo_connection',
               return_value=odoo):
        with patch.object(SnapshotOdooService, '_baixar_apontamentos',
                          return_value={}):
            with patch.object(SnapshotOdooService, '_baixar_compras',
                              return_value={}):
                resultado = SnapshotOdooService.refresh(ciclo.id, job=None)
    assert resultado['inseridos'] >= 1
    s = InventarioSnapshotOdoo.query.filter_by(
        ciclo_id=ciclo.id, cod_produto='4320147').first()
    assert s is not None
    assert s.estoque_fb == Decimal('150')
    assert s.estoque_lf == Decimal('30')
    assert s.estoque_cd == Decimal('0')


def test_refresh_idempotente_substitui_linhas(app, ciclo):
    odoo = _mk_odoo_mock()
    with patch('app.inventario.services.snapshot_odoo_service.get_odoo_connection',
               return_value=odoo):
        with patch.object(SnapshotOdooService, '_baixar_apontamentos',
                          return_value={}):
            with patch.object(SnapshotOdooService, '_baixar_compras',
                              return_value={}):
                SnapshotOdooService.refresh(ciclo.id, job=None)
                # Re-run
                SnapshotOdooService.refresh(ciclo.id, job=None)
    cnt = InventarioSnapshotOdoo.query.filter_by(ciclo_id=ciclo.id).count()
    assert cnt == 1  # não duplicou


def test_refresh_filtra_locations_indisponivel(app, ciclo):
    """Locations cujo name contém 'Indisponivel' devem ser excluídas."""
    odoo = MagicMock()
    odoo.search.return_value = [10, 20]
    odoo.read.side_effect = lambda model, ids, fields: {
        'stock.quant': [
            {'id': 10, 'company_id': [1, 'FB'], 'product_id': [100, '[X] X'],
             'location_id': [50, 'FB/Estoque'], 'quantity': 100.0,
             'reserved_quantity': 0},
            {'id': 20, 'company_id': [1, 'FB'], 'product_id': [100, '[X] X'],
             'location_id': [99, 'FB/Indisponivel'], 'quantity': 999.0,
             'reserved_quantity': 0},
        ],
        'product.product': [{'id': 100, 'name': 'X', 'default_code': 'X'}],
    }.get(model, [])
    with patch('app.inventario.services.snapshot_odoo_service.get_odoo_connection',
               return_value=odoo):
        with patch.object(SnapshotOdooService, '_baixar_apontamentos',
                          return_value={}):
            with patch.object(SnapshotOdooService, '_baixar_compras',
                              return_value={}):
                SnapshotOdooService.refresh(ciclo.id, job=None)
    s = InventarioSnapshotOdoo.query.filter_by(
        ciclo_id=ciclo.id, cod_produto='X').first()
    assert s.estoque_fb == Decimal('100')  # só Estoque, não Indisponivel
```

- [ ] **Step 2: Run tests, expect fail**

Run: `source .venv/bin/activate && pytest tests/inventario/test_snapshot_odoo_service.py -v`
Expected: ImportError.

- [ ] **Step 3: Implementar `snapshot_odoo_service.py`**

```python
"""Refresh cache Odoo (estoque + apontamentos + compras).

Reaproveita lógica de:
- scripts/inventario_2026_05/monitor/export_excel_completo.py (estoque)
- scripts/inventario_2026_05/monitor/relatorio_apontamentos_compras.py (apt + compras)
"""
from decimal import Decimal
from collections import defaultdict
from typing import Dict
from app import db
from app.inventario.models import CicloInventario, InventarioSnapshotOdoo
from app.odoo.utils.connection import get_odoo_connection
from app.utils.timezone import agora_utc_naive


COMPANIES = [1, 4, 5]
COMPANY_NAME = {1: 'FB', 4: 'CD', 5: 'LF'}
ODOO_BATCH = 200


def _m2o_id(v):
    return v[0] if isinstance(v, (list, tuple)) and v else None


def _m2o_name(v):
    return v[1] if isinstance(v, (list, tuple)) and len(v) > 1 else ''


def _norm_cod(s):
    return str(s or '').strip()


class SnapshotOdooService:

    @staticmethod
    def refresh(ciclo_id: int, job=None) -> Dict:
        ciclo = CicloInventario.query.get(ciclo_id)
        if ciclo is None:
            return {'erro': f'Ciclo {ciclo_id} não encontrado'}
        data_inicio = ciclo.data_snapshot.isoformat() + ' 00:00:00'

        def _progress(p, msg):
            if job is not None:
                job.meta['progress'] = p
                job.meta['msg'] = msg
                job.save_meta()

        _progress(5, 'Conectando ao Odoo')
        odoo = get_odoo_connection()

        _progress(20, 'Baixando estoque por empresa')
        estoques = SnapshotOdooService._baixar_estoque(odoo)

        _progress(50, 'Baixando apontamentos (mrp.production)')
        apontamentos = SnapshotOdooService._baixar_apontamentos(odoo, data_inicio)

        _progress(75, 'Baixando compras externas')
        compras = SnapshotOdooService._baixar_compras(odoo, data_inicio)

        _progress(90, 'Persistindo snapshot')
        # set master de cods
        cods = set(estoques.keys()) | set(apontamentos.keys()) | set(compras.keys())

        InventarioSnapshotOdoo.query.filter_by(ciclo_id=ciclo_id).delete()
        db.session.flush()

        for cod in cods:
            est = estoques.get(cod, {})
            apt = apontamentos.get(cod, {})
            db.session.add(InventarioSnapshotOdoo(
                ciclo_id=ciclo_id,
                cod_produto=cod,
                nome_produto=(est.get('nome') or apt.get('nome') or
                              compras.get(cod, {}).get('nome')),
                estoque_fb=est.get('fb', Decimal('0')),
                estoque_cd=est.get('cd', Decimal('0')),
                estoque_lf=est.get('lf', Decimal('0')),
                pa_qtd=apt.get('pa', Decimal('0')),
                componente_qtd=apt.get('componente', Decimal('0')),
                compras_qtd=compras.get(cod, {}).get('qtd', Decimal('0')),
                refresh_em=agora_utc_naive(),
            ))
        db.session.commit()
        _progress(100, 'Concluído')
        return {'inseridos': len(cods), 'refresh_em': agora_utc_naive().isoformat()}

    @staticmethod
    def _baixar_estoque(odoo) -> Dict:
        """{cod: {fb, cd, lf, nome}} — exclui locations Indisponivel."""
        domain = [('company_id', 'in', COMPANIES),
                  ('location_id.usage', '=', 'internal')]
        qids = odoo.search('stock.quant', domain)
        out = defaultdict(lambda: {'fb': Decimal('0'), 'cd': Decimal('0'),
                                    'lf': Decimal('0'), 'nome': ''})
        product_ids = set()
        quants = []
        for i in range(0, len(qids), ODOO_BATCH):
            quants.extend(odoo.read('stock.quant', qids[i:i+ODOO_BATCH],
                                    ['company_id', 'product_id', 'location_id',
                                     'quantity']))
        for q in quants:
            loc_name = _m2o_name(q.get('location_id'))
            if 'Indisponivel' in loc_name or 'indisponivel' in loc_name.lower():
                continue
            cid = _m2o_id(q.get('company_id'))
            emp = COMPANY_NAME.get(cid)
            if emp is None:
                continue
            pid = _m2o_id(q.get('product_id'))
            if pid:
                product_ids.add(pid)
            cod_default = _m2o_name(q.get('product_id')).split(']')[0].strip('[').strip()
            qtd = Decimal(str(q.get('quantity') or 0))
            key = cod_default or f'pid_{pid}'
            out[key][emp.lower()] += qtd

        # buscar default_code real (mais confiável que name)
        if product_ids:
            prods = odoo.read('product.product', list(product_ids),
                              ['name', 'default_code'])
            pid_to_cod = {p['id']: (_norm_cod(p.get('default_code')), p.get('name') or '')
                          for p in prods}
            # Reconstruir out com cods reais
            real = defaultdict(lambda: {'fb': Decimal('0'), 'cd': Decimal('0'),
                                         'lf': Decimal('0'), 'nome': ''})
            for q in quants:
                loc_name = _m2o_name(q.get('location_id'))
                if 'Indisponivel' in loc_name or 'indisponivel' in loc_name.lower():
                    continue
                cid = _m2o_id(q.get('company_id'))
                emp = COMPANY_NAME.get(cid)
                pid = _m2o_id(q.get('product_id'))
                if not emp or not pid:
                    continue
                cod, nome = pid_to_cod.get(pid, ('', ''))
                if not cod:
                    continue
                qtd = Decimal(str(q.get('quantity') or 0))
                real[cod][emp.lower()] += qtd
                real[cod]['nome'] = nome
            return dict(real)
        return dict(out)

    @staticmethod
    def _baixar_apontamentos(odoo, data_inicio) -> Dict:
        """{cod: {pa, componente, nome}} — agrega PA e COMPONENTE por cod."""
        base = [['date', '>=', data_inicio], ['company_id', 'in', COMPANIES],
                ['state', '=', 'done']]
        raw_ids = odoo.search('stock.move',
                              base + [['raw_material_production_id', '!=', False]])
        fin_ids = odoo.search('stock.move',
                              base + [['production_id', '!=', False]])

        move_meta = {}    # move_id -> 'COMPONENTE' | 'FINISHED'
        move_to_mo = {}   # move_id -> mo_id
        mo_ids = set()
        for ids, tag, link in (
            (raw_ids, 'COMPONENTE', 'raw_material_production_id'),
            (fin_ids, 'FINISHED', 'production_id'),
        ):
            for i in range(0, len(ids), ODOO_BATCH):
                for m in odoo.read('stock.move', ids[i:i+ODOO_BATCH], [link]):
                    moid = _m2o_id(m.get(link))
                    if moid:
                        move_meta[m['id']] = tag
                        move_to_mo[m['id']] = moid
                        mo_ids.add(moid)

        mo_pa = {}  # mo_id -> pa_pid
        for i in range(0, len(list(mo_ids)), ODOO_BATCH):
            batch = list(mo_ids)[i:i+ODOO_BATCH]
            for mo in odoo.read('mrp.production', batch, ['product_id']):
                mo_pa[mo['id']] = _m2o_id(mo.get('product_id'))

        # move_line agregado
        if not move_to_mo:
            return {}
        ml_ids = odoo.search('stock.move.line',
                             [['move_id', 'in', list(move_to_mo.keys())],
                              ['state', '=', 'done']])
        agg = defaultdict(lambda: {'pa': Decimal('0'), 'componente': Decimal('0'),
                                    'nome': ''})
        product_ids = set()
        mls = []
        for i in range(0, len(ml_ids), ODOO_BATCH):
            mls.extend(odoo.read('stock.move.line', ml_ids[i:i+ODOO_BATCH],
                                  ['product_id', 'qty_done', 'move_id']))
        for ml in mls:
            pid = _m2o_id(ml.get('product_id'))
            mid = _m2o_id(ml.get('move_id'))
            if not pid or not mid:
                continue
            product_ids.add(pid)
            mo_id = move_to_mo.get(mid)
            tag = move_meta.get(mid)
            qtd = Decimal(str(ml.get('qty_done') or 0))
            tipo = ('PA' if tag == 'FINISHED' and pid == mo_pa.get(mo_id)
                    else 'COMPONENTE' if tag == 'COMPONENTE' else 'SUBPRODUTO')
            if tipo == 'PA':
                agg[pid]['pa'] += qtd
            elif tipo == 'COMPONENTE':
                agg[pid]['componente'] += qtd

        # Resolver product_id → default_code
        if product_ids:
            prods = odoo.read('product.product', list(product_ids),
                              ['name', 'default_code'])
            pid_to_cod = {p['id']: (_norm_cod(p.get('default_code')), p.get('name') or '')
                          for p in prods}
            out = {}
            for pid, v in agg.items():
                cod, nome = pid_to_cod.get(pid, ('', ''))
                if not cod:
                    continue
                v['nome'] = nome
                out[cod] = v
            return out
        return {}

    @staticmethod
    def _baixar_compras(odoo, data_inicio) -> Dict:
        """{cod: {qtd, nome}} — entradas de fornecedor externo.

        Reaproveita lógica do script CLI relatorio_apontamentos_compras.py
        (resolve fornecedor via purchase.order, exclui inter-company).
        """
        ml_ids = odoo.search('stock.move.line',
                             [['date', '>=', data_inicio],
                              ['company_id', 'in', COMPANIES],
                              ['state', '=', 'done'],
                              ['location_id.usage', '=', 'supplier']])
        if not ml_ids:
            return {}
        mls = []
        for i in range(0, len(ml_ids), ODOO_BATCH):
            mls.extend(odoo.read('stock.move.line', ml_ids[i:i+ODOO_BATCH],
                                  ['product_id', 'qty_done', 'move_id',
                                   'picking_id']))

        # Resolver partner via PO (autoritativo) ou picking (fallback)
        move_ids = sorted({_m2o_id(ml.get('move_id')) for ml in mls
                           if _m2o_id(ml.get('move_id'))})
        mv_to_pl = {}
        for i in range(0, len(move_ids), ODOO_BATCH):
            for m in odoo.read('stock.move', move_ids[i:i+ODOO_BATCH],
                                ['purchase_line_id']):
                mv_to_pl[m['id']] = _m2o_id(m.get('purchase_line_id'))
        pl_ids = sorted({v for v in mv_to_pl.values() if v})
        pl_to_order = {}
        for i in range(0, len(pl_ids), ODOO_BATCH):
            for p in odoo.read('purchase.order.line', pl_ids[i:i+ODOO_BATCH],
                                ['order_id']):
                pl_to_order[p['id']] = _m2o_id(p.get('order_id'))
        order_ids = sorted({v for v in pl_to_order.values() if v})
        order_partner = {}
        for i in range(0, len(order_ids), ODOO_BATCH):
            for o in odoo.read('purchase.order', order_ids[i:i+ODOO_BATCH],
                                ['partner_id']):
                order_partner[o['id']] = _m2o_id(o.get('partner_id'))

        # Partners das empresas do grupo (inter-company)
        partners_empresas = set()
        for c in COMPANIES:
            recs = odoo.search_read('res.company', [['id', '=', c]], ['partner_id'])
            if recs:
                pid = _m2o_id(recs[0].get('partner_id'))
                if pid:
                    partners_empresas.add(pid)
        # commercial_partner_id
        all_part = set(order_partner.values())
        comm = {}
        if all_part:
            for i in range(0, len(list(all_part)), ODOO_BATCH):
                batch = list(all_part)[i:i+ODOO_BATCH]
                for r in odoo.read('res.partner', batch, ['commercial_partner_id']):
                    cp = r.get('commercial_partner_id')
                    comm[r['id']] = _m2o_id(cp) if cp else r['id']

        agg = defaultdict(lambda: {'qtd': Decimal('0'), 'nome': ''})
        product_ids = set()
        for ml in mls:
            mid = _m2o_id(ml.get('move_id'))
            plid = mv_to_pl.get(mid)
            partner_id = None
            if plid:
                partner_id = order_partner.get(pl_to_order.get(plid))
            # Filtro inter-company
            if partner_id and comm.get(partner_id, partner_id) in partners_empresas:
                continue
            pid = _m2o_id(ml.get('product_id'))
            if not pid:
                continue
            product_ids.add(pid)
            agg[pid]['qtd'] += Decimal(str(ml.get('qty_done') or 0))

        # Resolver pid → cod
        if product_ids:
            prods = odoo.read('product.product', list(product_ids),
                              ['name', 'default_code'])
            pid_to_cod = {p['id']: (_norm_cod(p.get('default_code')), p.get('name') or '')
                          for p in prods}
            out = {}
            for pid, v in agg.items():
                cod, nome = pid_to_cod.get(pid, ('', ''))
                if not cod:
                    continue
                v['nome'] = nome
                out[cod] = v
            return out
        return {}
```

- [ ] **Step 4: Run tests**

Run: `source .venv/bin/activate && pytest tests/inventario/test_snapshot_odoo_service.py -v`
Expected: 3 passed.

- [ ] **Step 5: Commit**

```bash
git add app/inventario/services/snapshot_odoo_service.py tests/inventario/test_snapshot_odoo_service.py
git commit -m "feat(inventario): SnapshotOdooService (refresh estoque + apontamentos + compras)"
```

---

### Task 8: `movimentacoes_odoo_service.py` — drill-down paginado

**Files:**
- Create: `app/inventario/services/movimentacoes_odoo_service.py`
- Test: `tests/inventario/test_movimentacoes_drill_down.py`

- [ ] **Step 1: Escrever testes (failing)**

```python
"""Testes do drill-down de movimentações Odoo."""
from unittest.mock import patch, MagicMock
from app.inventario.services.movimentacoes_odoo_service import (
    MovimentacoesOdooService,
)


def _mk_odoo_mls(qtde=150):
    odoo = MagicMock()
    odoo.search_count.return_value = qtde
    odoo.search.return_value = list(range(1, min(qtde, 100) + 1))
    odoo.read.side_effect = lambda model, ids, fields: {
        'stock.move.line': [
            {'id': i, 'date': '2026-05-18 10:00:00',
             'company_id': [4, 'CD'], 'product_id': [100, '[X] X'],
             'lot_id': [50, 'L01'], 'qty_done': 5.0,
             'location_id': [10, 'CD/Estoque'],
             'location_dest_id': [20, 'CD/Saida'],
             'move_id': [200, 'MOVE'], 'create_uid': [1, 'admin']}
            for i in ids
        ],
        'product.product': [{'id': 100, 'default_code': 'X', 'name': 'X'}],
        'stock.move': [],
    }.get(model, [])
    return odoo


def test_paginacao_default_100(app):
    odoo = _mk_odoo_mls(qtde=150)
    with patch('app.inventario.services.movimentacoes_odoo_service.'
               'get_odoo_connection', return_value=odoo):
        out = MovimentacoesOdooService.buscar_paginado({
            'data_inicio': '2026-05-16', 'page': 1, 'page_size': 100,
        })
    assert out['total'] == 150
    assert out['page_size'] == 100
    assert len(out['rows']) == 100


def test_paginacao_500_e_1000(app):
    odoo = _mk_odoo_mls(qtde=1500)
    odoo.search.return_value = list(range(1, 501))
    with patch('app.inventario.services.movimentacoes_odoo_service.'
               'get_odoo_connection', return_value=odoo):
        out = MovimentacoesOdooService.buscar_paginado({
            'data_inicio': '2026-05-16', 'page': 1, 'page_size': 500,
        })
    assert out['page_size'] == 500
    assert len(out['rows']) == 500


def test_filtro_empresa(app):
    odoo = _mk_odoo_mls(qtde=10)
    with patch('app.inventario.services.movimentacoes_odoo_service.'
               'get_odoo_connection', return_value=odoo):
        MovimentacoesOdooService.buscar_paginado({
            'data_inicio': '2026-05-16', 'empresa': 'CD',
        })
    # Verificar que empresa=4 (CD) entrou no domain
    call_args = odoo.search_count.call_args
    domain = call_args[0][1] if len(call_args[0]) > 1 else call_args.kwargs.get('args', [])
    flat = str(domain)
    assert 'company_id' in flat
    assert '4' in flat


def test_filtro_tipo_producao(app):
    odoo = _mk_odoo_mls(qtde=5)
    with patch('app.inventario.services.movimentacoes_odoo_service.'
               'get_odoo_connection', return_value=odoo):
        MovimentacoesOdooService.buscar_paginado({
            'data_inicio': '2026-05-16', 'tipo': 'PRODUCAO',
        })
    # Verificar que filtro de produção entrou no domain
    flat = str(odoo.search_count.call_args)
    assert 'production_id' in flat or 'raw_material' in flat
```

- [ ] **Step 2: Implementar `movimentacoes_odoo_service.py`**

```python
"""Drill-down: busca movimentações Odoo on-demand paginadas (sem persistir)."""
from datetime import datetime
from typing import Dict, List, Any
from app.odoo.utils.connection import get_odoo_connection


COMPANIES = [1, 4, 5]
COMPANY_TO_ID = {'FB': 1, 'CD': 4, 'LF': 5}


def _m2o_id(v):
    return v[0] if isinstance(v, (list, tuple)) and v else None


def _m2o_name(v):
    return v[1] if isinstance(v, (list, tuple)) and len(v) > 1 else ''


class MovimentacoesOdooService:

    PAGE_SIZES_VALIDOS = (100, 500, 1000)

    @staticmethod
    def buscar_paginado(filtros: Dict[str, Any]) -> Dict:
        page = int(filtros.get('page') or 1)
        page_size = int(filtros.get('page_size') or 100)
        if page_size not in MovimentacoesOdooService.PAGE_SIZES_VALIDOS:
            page_size = 100
        page = max(1, page)

        odoo = get_odoo_connection()

        # Resolver cod_produto -> product_id
        product_id = None
        if filtros.get('cod'):
            prods = odoo.search_read('product.product',
                                      [['default_code', '=', str(filtros['cod'])]],
                                      ['id'], limit=1)
            if prods:
                product_id = prods[0]['id']

        domain = [['state', '=', 'done']]
        if filtros.get('data_inicio'):
            domain.append(['date', '>=', str(filtros['data_inicio'])])
        if filtros.get('data_fim'):
            domain.append(['date', '<=', str(filtros['data_fim'])])

        # Empresa filter
        emp = filtros.get('empresa')
        if emp and emp != 'ALL':
            company_ids = [COMPANY_TO_ID.get(emp, 0)]
            domain.append(['company_id', 'in', company_ids])
        else:
            domain.append(['company_id', 'in', COMPANIES])

        if product_id:
            domain.append(['product_id', '=', product_id])
        if filtros.get('origem'):
            domain.append(['location_id.name', 'ilike', str(filtros['origem'])])
        if filtros.get('destino'):
            domain.append(['location_dest_id.name', 'ilike', str(filtros['destino'])])

        # Filtro PRODUCAO: move_id liga a mrp.production
        tipo = filtros.get('tipo')
        if tipo == 'PRODUCAO':
            # Buscar moves de produção e filtrar mls
            mv_ids = odoo.search('stock.move',
                [['date', '>=', str(filtros.get('data_inicio') or '2000-01-01')],
                 ['state', '=', 'done'],
                 '|',
                 ['raw_material_production_id', '!=', False],
                 ['production_id', '!=', False]])
            if mv_ids:
                domain.append(['move_id', 'in', mv_ids])
            else:
                return {'total': 0, 'page': page, 'page_size': page_size, 'rows': []}

        # Usuário (resolve por name)
        if filtros.get('usuario'):
            user_ids = odoo.search('res.users',
                [['name', 'ilike', str(filtros['usuario'])]], limit=20)
            if user_ids:
                # Filtro no move (create_uid do stock.move)
                mv_filter = odoo.search('stock.move',
                    [['create_uid', 'in', user_ids]])
                if mv_filter:
                    domain.append(['move_id', 'in', mv_filter])
                else:
                    return {'total': 0, 'page': page, 'page_size': page_size, 'rows': []}

        # Total
        ts = datetime.now()
        total = odoo.search_count('stock.move.line', domain)
        offset = (page - 1) * page_size
        ids = odoo.search('stock.move.line', domain,
                          offset=offset, limit=page_size, order='date desc')
        if not ids:
            return {'total': total, 'page': page, 'page_size': page_size, 'rows': []}

        rows = odoo.read('stock.move.line', ids,
                         ['date', 'company_id', 'product_id', 'lot_id',
                          'qty_done', 'location_id', 'location_dest_id',
                          'move_id', 'create_uid'])

        # Enriquecer produto (default_code + nome limpo)
        pids = [_m2o_id(r.get('product_id')) for r in rows]
        pids = [p for p in pids if p]
        prods = odoo.read('product.product', list(set(pids)),
                          ['default_code', 'name'])
        pid_to_info = {p['id']: {'cod': p.get('default_code') or '',
                                  'nome': p.get('name') or ''}
                        for p in prods}

        out = []
        for r in rows:
            pid = _m2o_id(r.get('product_id'))
            info = pid_to_info.get(pid, {'cod': '', 'nome': ''})
            cid = _m2o_id(r.get('company_id'))
            emp_name = {1: 'FB', 4: 'CD', 5: 'LF'}.get(cid, '?')
            out.append({
                'data': r.get('date'),
                'empresa': emp_name,
                'cod': info['cod'],
                'produto': info['nome'],
                'lote': _m2o_name(r.get('lot_id')),
                'qtd': float(r.get('qty_done') or 0),
                'origem': _m2o_name(r.get('location_id')),
                'destino': _m2o_name(r.get('location_dest_id')),
                'usuario': _m2o_name(r.get('create_uid')),
                'move_id': _m2o_id(r.get('move_id')),
            })

        duracao = (datetime.now() - ts).total_seconds() * 1000
        return {
            'total': total, 'page': page, 'page_size': page_size,
            'rows': out, 'duracao_ms': int(duracao),
        }
```

- [ ] **Step 3: Run tests**

Run: `source .venv/bin/activate && pytest tests/inventario/test_movimentacoes_drill_down.py -v`
Expected: 4 passed.

- [ ] **Step 4: Commit**

```bash
git add app/inventario/services/movimentacoes_odoo_service.py tests/inventario/test_movimentacoes_drill_down.py
git commit -m "feat(inventario): MovimentacoesOdooService (drill-down paginado on-demand)"
```

---

### Task 9: `export_xlsx_service.py` — XLSX 6 abas

**Files:**
- Create: `app/inventario/services/export_xlsx_service.py`
- Test: `tests/inventario/test_export_xlsx.py`

- [ ] **Step 1: Implementar service**

```python
"""Export do Relatório de Confronto em XLSX (6 abas) idêntico à planilha-referência."""
import io
from decimal import Decimal
import xlsxwriter
from app.inventario.models import (
    CicloInventario, InventarioBase, AjusteManualInventario,
    InventarioSnapshotOdoo,
)
from app.inventario.services.confronto_service import ConfrontoService
from app.estoque.models import MovimentacaoEstoque
from app import db


HEADER_FMT = {'bold': True, 'bg_color': '#E0E0E0', 'border': 1}
NUM_FMT = '#,##0.000'
DIFF_FMT_RED = {'num_format': NUM_FMT, 'bg_color': '#FFE6E6'}


class ExportXlsxService:

    @staticmethod
    def gerar(ciclo_id: int) -> bytes:
        buf = io.BytesIO()
        wb = xlsxwriter.Workbook(buf, {'in_memory': True})
        hfmt = wb.add_format(HEADER_FMT)
        nfmt = wb.add_format({'num_format': NUM_FMT})
        rfmt = wb.add_format(DIFF_FMT_RED)

        # Aba 1: Confronto
        ws = wb.add_worksheet('Confronto')
        cols = ['cod', 'produto', 'FB', 'CD', 'LF', 'TOTAL', 'COMPRAS',
                'PA', 'COMPONENTE', 'VENDAS', 'CONSUMO', 'PRODUCAO',
                'AJUSTE_LOCAL', 'AJUSTE_QTD', 'AJUSTE_TIPO',
                'ODOO', 'MOV', 'SIST', 'ODOO-MOV', 'SIST-MOV',
                'ODOO_FB', 'ODOO_CD', 'ODOO_LF']
        for i, c in enumerate(cols):
            ws.write(0, i, c, hfmt)
        linhas = ConfrontoService.montar_linhas(ciclo_id)
        for r, l in enumerate(linhas, start=1):
            ws.write(r, 0, l['cod_produto'])
            ws.write(r, 1, l['nome_produto'])
            ws.write_number(r, 2, float(l['inv_fb']), nfmt)
            ws.write_number(r, 3, float(l['inv_cd']), nfmt)
            ws.write_number(r, 4, float(l['inv_lf']), nfmt)
            ws.write_number(r, 5, float(l['inv_total']), nfmt)
            ws.write_number(r, 6, float(l['compras']), nfmt)
            ws.write_number(r, 7, float(l['pa']), nfmt)
            ws.write_number(r, 8, float(l['componente']), nfmt)
            ws.write_number(r, 9, float(l['vendas']), nfmt)
            ws.write_number(r, 10, float(l['consumo']), nfmt)
            ws.write_number(r, 11, float(l['producao']), nfmt)
            ws.write(r, 12, l.get('ajuste_local') or '')
            if l.get('ajuste_qtd') is not None:
                ws.write_number(r, 13, float(l['ajuste_qtd']), nfmt)
            ws.write(r, 14, l.get('ajuste_tipo') or '')
            ws.write_number(r, 15, float(l['odoo']), nfmt)
            ws.write_number(r, 16, float(l['mov']), nfmt)
            ws.write_number(r, 17, float(l['sist']), nfmt)
            d1 = float(l['odoo_menos_mov'])
            d2 = float(l['sist_menos_mov'])
            ws.write_number(r, 18, d1, rfmt if abs(d1) > 1 else nfmt)
            ws.write_number(r, 19, d2, rfmt if abs(d2) > 1 else nfmt)
            ws.write_number(r, 20, float(l['est_fb']), nfmt)
            ws.write_number(r, 21, float(l['est_cd']), nfmt)
            ws.write_number(r, 22, float(l['est_lf']), nfmt)
        ws.freeze_panes(1, 2)

        # Aba 2: Ajustes Manuais
        ws2 = wb.add_worksheet('Ajustes_Manuais')
        ws2.write_row(0, 0, ['cod', 'produto', 'local', 'qtd', 'tipo',
                              'observacao', 'criado_em', 'criado_por'], hfmt)
        ajs = AjusteManualInventario.query.filter_by(ciclo_id=ciclo_id).all()
        for r, a in enumerate(ajs, start=1):
            ws2.write(r, 0, a.cod_produto)
            ws2.write(r, 1, a.nome_produto or '')
            ws2.write(r, 2, a.local or '')
            ws2.write_number(r, 3, float(a.qtd or 0), nfmt)
            ws2.write(r, 4, a.tipo_ajuste or '')
            ws2.write(r, 5, a.observacao or '')
            ws2.write(r, 6, a.criado_em.isoformat() if a.criado_em else '')
            ws2.write(r, 7, a.criado_por or '')

        # Aba 3-6: dumps simples (Apontamentos / Compras / Movimentacoes_Sist / Estoque_por_Local)
        # Para minimum viable: dump do InventarioSnapshotOdoo + MovimentacaoEstoque
        ws3 = wb.add_worksheet('Apontamentos_PA_Comp')
        ws3.write_row(0, 0, ['cod', 'nome', 'pa_qtd', 'componente_qtd',
                              'compras_qtd_odoo'], hfmt)
        snaps = InventarioSnapshotOdoo.query.filter_by(ciclo_id=ciclo_id).all()
        for r, s in enumerate(snaps, start=1):
            ws3.write(r, 0, s.cod_produto)
            ws3.write(r, 1, s.nome_produto or '')
            ws3.write_number(r, 2, float(s.pa_qtd or 0), nfmt)
            ws3.write_number(r, 3, float(s.componente_qtd or 0), nfmt)
            ws3.write_number(r, 4, float(s.compras_qtd or 0), nfmt)

        ws4 = wb.add_worksheet('Movimentacoes_Sistema')
        ws4.write_row(0, 0, ['data', 'tipo', 'local', 'cod', 'produto',
                              'qtd', 'nf', 'origem'], hfmt)
        ciclo = CicloInventario.query.get(ciclo_id)
        if ciclo:
            movs = (MovimentacaoEstoque.query
                    .filter(MovimentacaoEstoque.ativo.is_(True))
                    .filter(MovimentacaoEstoque.data_movimentacao >= ciclo.data_snapshot)
                    .order_by(MovimentacaoEstoque.data_movimentacao.desc())
                    .limit(20000).all())
            for r, m in enumerate(movs, start=1):
                ws4.write(r, 0, m.data_movimentacao.isoformat() if m.data_movimentacao else '')
                ws4.write(r, 1, m.tipo_movimentacao or '')
                ws4.write(r, 2, m.local_movimentacao or '')
                ws4.write(r, 3, m.cod_produto or '')
                ws4.write(r, 4, m.nome_produto or '')
                ws4.write_number(r, 5, float(m.qtd_movimentacao or 0), nfmt)
                ws4.write(r, 6, m.numero_nf or '')
                ws4.write(r, 7, m.tipo_origem or '')

        ws5 = wb.add_worksheet('Estoque_Odoo_por_Empresa')
        ws5.write_row(0, 0, ['cod', 'produto', 'FB', 'CD', 'LF', 'TOTAL'], hfmt)
        for r, s in enumerate(snaps, start=1):
            ws5.write(r, 0, s.cod_produto)
            ws5.write(r, 1, s.nome_produto or '')
            ws5.write_number(r, 2, float(s.estoque_fb or 0), nfmt)
            ws5.write_number(r, 3, float(s.estoque_cd or 0), nfmt)
            ws5.write_number(r, 4, float(s.estoque_lf or 0), nfmt)
            total = (float(s.estoque_fb or 0) + float(s.estoque_cd or 0) +
                     float(s.estoque_lf or 0))
            ws5.write_number(r, 5, total, nfmt)

        ws6 = wb.add_worksheet('Inventario_Base')
        ws6.write_row(0, 0, ['cod', 'produto', 'empresa', 'qtd'], hfmt)
        bases = InventarioBase.query.filter_by(ciclo_id=ciclo_id).order_by(
            InventarioBase.cod_produto, InventarioBase.empresa).all()
        for r, b in enumerate(bases, start=1):
            ws6.write(r, 0, b.cod_produto)
            ws6.write(r, 1, b.nome_produto or '')
            ws6.write(r, 2, b.empresa)
            ws6.write_number(r, 3, float(b.qtd or 0), nfmt)

        wb.close()
        return buf.getvalue()
```

- [ ] **Step 2: Escrever teste rápido (abrir xlsx e verificar 6 abas)**

```python
"""Teste do ExportXlsxService."""
import io
import openpyxl
from decimal import Decimal
from app import db
from app.inventario.models import InventarioBase
from app.inventario.services.export_xlsx_service import ExportXlsxService


def test_export_gera_6_abas(app, ciclo):
    db.session.add(InventarioBase(
        ciclo_id=ciclo.id, cod_produto='4320147', empresa='FB',
        qtd=Decimal('100'), nome_produto='PROD',
    ))
    db.session.commit()
    blob = ExportXlsxService.gerar(ciclo.id)
    assert isinstance(blob, bytes)
    wb = openpyxl.load_workbook(io.BytesIO(blob), read_only=True)
    nomes_esperados = {'Confronto', 'Ajustes_Manuais', 'Apontamentos_PA_Comp',
                       'Movimentacoes_Sistema', 'Estoque_Odoo_por_Empresa',
                       'Inventario_Base'}
    assert nomes_esperados.issubset(set(wb.sheetnames))
```

- [ ] **Step 3: Run test + commit**

Run: `source .venv/bin/activate && pytest tests/inventario/test_export_xlsx.py -v`
Expected: 1 passed.

```bash
git add app/inventario/services/export_xlsx_service.py tests/inventario/test_export_xlsx.py
git commit -m "feat(inventario): ExportXlsxService (XLSX 6 abas)"
```

---

## Phase 3 — Routes

### Task 10: `ciclo_routes.py` (CRUD + upload xlsx)

**Files:**
- Modify: `app/inventario/routes/ciclo_routes.py`
- Create: `app/templates/inventario/ciclos.html` (placeholder mínimo; Task 16 reformula)

- [ ] **Step 1: Implementar rotas**

```python
"""CRUD CicloInventario + upload do XLSX de inventário base."""
from datetime import datetime, date
from flask import render_template, request, jsonify, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.inventario import inventario_bp
from app.inventario.models import CicloInventario, InventarioBase
from app.inventario.services.inventario_loader import InventarioLoader
from app.utils.json_helpers import sanitize_for_json


@inventario_bp.route('/ciclos')
@login_required
def listar_ciclos():
    ciclos = CicloInventario.query.order_by(CicloInventario.criado_em.desc()).all()
    return render_template('inventario/ciclos.html', ciclos=ciclos)


@inventario_bp.route('/ciclos/novo', methods=['POST'])
@login_required
def criar_ciclo():
    codigo = (request.form.get('codigo') or '').strip()
    data_str = (request.form.get('data_snapshot') or '').strip()
    descricao = (request.form.get('descricao') or '').strip() or None
    if not codigo or not data_str:
        return jsonify({'erro': 'codigo e data_snapshot obrigatórios'}), 400
    try:
        d = datetime.fromisoformat(data_str).date() if 'T' in data_str else date.fromisoformat(data_str)
    except ValueError:
        return jsonify({'erro': 'data_snapshot inválida (ISO YYYY-MM-DD)'}), 400
    if CicloInventario.query.filter_by(codigo=codigo).first():
        return jsonify({'erro': f'codigo {codigo} já existe'}), 409
    c = CicloInventario(
        codigo=codigo, data_snapshot=d, descricao=descricao,
        status='ATIVO', criado_por=current_user.nome if current_user.is_authenticated else None,
    )
    db.session.add(c)
    db.session.commit()
    return jsonify(sanitize_for_json({'id': c.id, 'codigo': c.codigo})), 201


@inventario_bp.route('/ciclos/<int:ciclo_id>/upload', methods=['POST'])
@login_required
def upload_xlsx(ciclo_id):
    ciclo = CicloInventario.query.get_or_404(ciclo_id)
    if 'arquivo' not in request.files:
        return jsonify({'erro': 'arquivo ausente'}), 400
    f = request.files['arquivo']
    if not f.filename.lower().endswith('.xlsx'):
        return jsonify({'erro': 'envie .xlsx'}), 400
    resultado = InventarioLoader.carregar(
        ciclo.id, f.stream,
        criado_por=current_user.nome if current_user.is_authenticated else 'unknown',
    )
    db.session.commit()
    return jsonify(sanitize_for_json(resultado))


@inventario_bp.route('/ciclos/<int:ciclo_id>/arquivar', methods=['POST'])
@login_required
def arquivar_ciclo(ciclo_id):
    c = CicloInventario.query.get_or_404(ciclo_id)
    c.status = 'ARQUIVADO'
    db.session.commit()
    return jsonify({'ok': True})
```

- [ ] **Step 2: Criar template mínimo `ciclos.html`** (será reformulado em Task 16)

```html
{% extends "base.html" %}
{% block content %}
<div class="container py-4">
  <h2>Inventário — Ciclos</h2>
  <p><a href="{{ url_for('inventario.confronto_index') }}" class="btn btn-primary">
    Ver Confronto do Ciclo Atual</a></p>
  <table class="table">
    <thead><tr><th>Código</th><th>Data Snapshot</th><th>Status</th><th>Ações</th></tr></thead>
    <tbody>
      {% for c in ciclos %}
      <tr>
        <td>{{ c.codigo }}</td>
        <td>{{ c.data_snapshot }}</td>
        <td>{{ c.status }}</td>
        <td>
          <a href="{{ url_for('inventario.confronto_por_id', ciclo_id=c.id) }}"
             class="btn btn-sm btn-primary">Abrir</a>
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
```

- [ ] **Step 3: Commit**

```bash
git add app/inventario/routes/ciclo_routes.py app/templates/inventario/ciclos.html
git commit -m "feat(inventario): ciclo_routes (CRUD ciclo + upload xlsx)"
```

---

### Task 11: `confronto_routes.py` (tela principal + export)

**Files:**
- Modify: `app/inventario/routes/confronto_routes.py`
- Create: `app/templates/inventario/confronto.html` (placeholder; Task 17 reformula)

- [ ] **Step 1: Implementar rotas**

```python
"""Tela principal do Relatório de Confronto + export XLSX."""
from flask import render_template, request, jsonify, redirect, url_for, send_file, abort
from flask_login import login_required
import io
from app.inventario import inventario_bp
from app.inventario.models import CicloInventario, InventarioSnapshotOdoo
from app.inventario.services.confronto_service import ConfrontoService
from app.inventario.services.export_xlsx_service import ExportXlsxService
from app.utils.json_helpers import sanitize_for_json


@inventario_bp.route('/confronto', endpoint='confronto_index')
@login_required
def index():
    ultimo = (CicloInventario.query.filter_by(status='ATIVO')
              .order_by(CicloInventario.criado_em.desc()).first())
    if ultimo is None:
        return redirect(url_for('inventario.listar_ciclos'))
    return redirect(url_for('inventario.confronto_por_id', ciclo_id=ultimo.id))


@inventario_bp.route('/confronto/<int:ciclo_id>', endpoint='confronto_por_id')
@login_required
def por_id(ciclo_id):
    ciclo = CicloInventario.query.get_or_404(ciclo_id)
    # snapshot timestamp
    snap_first = (InventarioSnapshotOdoo.query.filter_by(ciclo_id=ciclo.id)
                  .order_by(InventarioSnapshotOdoo.refresh_em.desc()).first())
    last_refresh = snap_first.refresh_em if snap_first else None
    return render_template('inventario/confronto.html',
                            ciclo=ciclo, last_refresh=last_refresh)


@inventario_bp.route('/confronto/<int:ciclo_id>/api', endpoint='confronto_api')
@login_required
def api(ciclo_id):
    CicloInventario.query.get_or_404(ciclo_id)
    linhas = ConfrontoService.montar_linhas(ciclo_id)
    return jsonify(sanitize_for_json({'linhas': linhas, 'total': len(linhas)}))


@inventario_bp.route('/confronto/<int:ciclo_id>/export.xlsx', endpoint='confronto_export')
@login_required
def export_xlsx(ciclo_id):
    ciclo = CicloInventario.query.get_or_404(ciclo_id)
    blob = ExportXlsxService.gerar(ciclo_id)
    return send_file(
        io.BytesIO(blob),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name=f'CONFRONTO_INVENTARIO_{ciclo.codigo}.xlsx',
    )
```

- [ ] **Step 2: Criar template placeholder**

```html
{% extends "base.html" %}
{% block content %}
<div class="container-fluid py-3">
  <h2>Confronto — {{ ciclo.codigo }} ({{ ciclo.data_snapshot }})</h2>
  <p>
    Snapshot Odoo: {{ last_refresh or 'nunca gerado' }}
    <button id="btn-refresh" class="btn btn-sm btn-secondary">Atualizar Odoo</button>
    <a href="{{ url_for('inventario.confronto_export', ciclo_id=ciclo.id) }}"
       class="btn btn-sm btn-success">Exportar XLSX</a>
  </p>
  <div id="tabela-confronto">Carregando...</div>
  <script>
    const cicloId = {{ ciclo.id }};
    fetch(`/inventario/confronto/${cicloId}/api`)
      .then(r => r.json())
      .then(data => {
        const linhas = data.linhas || [];
        let html = '<table class="table table-sm table-striped">' +
          '<thead><tr><th>Cod</th><th>Produto</th><th>FB</th><th>CD</th><th>LF</th>' +
          '<th>Total</th><th>Compras</th><th>PA</th><th>Comp.</th><th>Vendas</th>' +
          '<th>Consumo</th><th>Producao</th><th>Odoo</th><th>Mov</th><th>Sist</th>' +
          '<th>Odoo-Mov</th><th>Sist-Mov</th></tr></thead><tbody>';
        for (const l of linhas) {
          const f = (v) => v != null ? Number(v).toLocaleString('pt-BR',
            {minimumFractionDigits: 3, maximumFractionDigits: 3}) : '';
          const flagDiff = Math.abs(l.odoo_menos_mov || 0) > 1 ||
                           Math.abs(l.sist_menos_mov || 0) > 1;
          html += `<tr ${flagDiff ? 'style="background:#fff3cd"' : ''}>` +
            `<td>${l.cod_produto}</td><td>${l.nome_produto || ''}</td>` +
            `<td>${f(l.inv_fb)}</td><td>${f(l.inv_cd)}</td><td>${f(l.inv_lf)}</td>` +
            `<td>${f(l.inv_total)}</td><td>${f(l.compras)}</td>` +
            `<td>${f(l.pa)}</td><td>${f(l.componente)}</td><td>${f(l.vendas)}</td>` +
            `<td>${f(l.consumo)}</td><td>${f(l.producao)}</td>` +
            `<td>${f(l.odoo)}</td><td>${f(l.mov)}</td><td>${f(l.sist)}</td>` +
            `<td>${f(l.odoo_menos_mov)}</td><td>${f(l.sist_menos_mov)}</td></tr>`;
        }
        html += '</tbody></table>';
        document.getElementById('tabela-confronto').innerHTML = html;
      });
    document.getElementById('btn-refresh').addEventListener('click', () => {
      fetch(`/inventario/snapshot/${cicloId}/refresh`, {method: 'POST'})
        .then(r => r.json()).then(d => alert('Job enfileirado: ' + d.job_id));
    });
  </script>
</div>
{% endblock %}
```

- [ ] **Step 3: Commit**

```bash
git add app/inventario/routes/confronto_routes.py app/templates/inventario/confronto.html
git commit -m "feat(inventario): confronto_routes (tela principal + export xlsx + API)"
```

---

### Task 12: `ajustes_manuais_routes.py` (CRUD inline)

**Files:**
- Modify: `app/inventario/routes/ajustes_manuais_routes.py`

- [ ] **Step 1: Implementar**

```python
"""CRUD AjusteManualInventario."""
from decimal import Decimal, InvalidOperation
from flask import request, jsonify, render_template, abort
from flask_login import login_required, current_user
from app import db
from app.inventario import inventario_bp
from app.inventario.models import AjusteManualInventario, CicloInventario
from app.utils.json_helpers import sanitize_for_json


@inventario_bp.route('/ajustes/<int:ciclo_id>')
@login_required
def listar_ajustes(ciclo_id):
    CicloInventario.query.get_or_404(ciclo_id)
    rows = AjusteManualInventario.query.filter_by(ciclo_id=ciclo_id).order_by(
        AjusteManualInventario.criado_em.desc()).all()
    return render_template('inventario/ajustes_manuais.html',
                            ciclo_id=ciclo_id, ajustes=rows)


@inventario_bp.route('/ajustes/<int:ciclo_id>', methods=['POST'])
@login_required
def criar_ajuste(ciclo_id):
    CicloInventario.query.get_or_404(ciclo_id)
    cod = (request.form.get('cod_produto') or '').strip()
    qtd_str = (request.form.get('qtd') or '').strip()
    if not cod or not qtd_str:
        return jsonify({'erro': 'cod_produto e qtd obrigatórios'}), 400
    try:
        qtd = Decimal(qtd_str)
    except InvalidOperation:
        return jsonify({'erro': 'qtd inválida'}), 400
    a = AjusteManualInventario(
        ciclo_id=ciclo_id, cod_produto=cod,
        nome_produto=(request.form.get('nome_produto') or '').strip() or None,
        local=(request.form.get('local') or '').strip() or None,
        qtd=qtd,
        tipo_ajuste=(request.form.get('tipo_ajuste') or '').strip() or None,
        observacao=(request.form.get('observacao') or '').strip() or None,
        criado_por=current_user.nome if current_user.is_authenticated else None,
    )
    db.session.add(a)
    db.session.commit()
    return jsonify(sanitize_for_json({'id': a.id})), 201


@inventario_bp.route('/ajustes/<int:ciclo_id>/<int:aj_id>', methods=['PUT'])
@login_required
def editar_ajuste(ciclo_id, aj_id):
    a = AjusteManualInventario.query.filter_by(id=aj_id, ciclo_id=ciclo_id).first_or_404()
    data = request.form
    if 'qtd' in data:
        try:
            a.qtd = Decimal(data['qtd'])
        except InvalidOperation:
            return jsonify({'erro': 'qtd inválida'}), 400
    for f in ('cod_produto', 'nome_produto', 'local', 'tipo_ajuste', 'observacao'):
        if f in data:
            setattr(a, f, (data[f] or '').strip() or None)
    db.session.commit()
    return jsonify({'ok': True})


@inventario_bp.route('/ajustes/<int:ciclo_id>/<int:aj_id>', methods=['DELETE'])
@login_required
def deletar_ajuste(ciclo_id, aj_id):
    a = AjusteManualInventario.query.filter_by(id=aj_id, ciclo_id=ciclo_id).first_or_404()
    db.session.delete(a)
    db.session.commit()
    return jsonify({'ok': True})
```

Criar template mínimo `ajustes_manuais.html` (será reformulado em Task 18):

```html
{% extends "base.html" %}
{% block content %}
<div class="container py-3">
  <h3>Ajustes Manuais — Ciclo {{ ciclo_id }}</h3>
  <table class="table table-sm">
    <thead><tr><th>Cod</th><th>Produto</th><th>Local</th><th>Qtd</th><th>Tipo</th><th>Obs</th></tr></thead>
    <tbody>
      {% for a in ajustes %}
      <tr>
        <td>{{ a.cod_produto }}</td><td>{{ a.nome_produto }}</td>
        <td>{{ a.local }}</td><td>{{ a.qtd }}</td>
        <td>{{ a.tipo_ajuste }}</td><td>{{ a.observacao }}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add app/inventario/routes/ajustes_manuais_routes.py app/templates/inventario/ajustes_manuais.html
git commit -m "feat(inventario): ajustes_manuais_routes (CRUD inline)"
```

---

### Task 13: `snapshot_routes.py` (botão refresh + status job)

**Files:**
- Modify: `app/inventario/routes/snapshot_routes.py`

- [ ] **Step 1: Implementar**

```python
"""Refresh assíncrono do snapshot Odoo via worker RQ."""
from flask import jsonify, request
from flask_login import login_required
from rq import Queue
from redis import Redis
import os
from app.inventario import inventario_bp
from app.inventario.models import CicloInventario


def _redis_conn():
    url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    return Redis.from_url(url)


@inventario_bp.route('/snapshot/<int:ciclo_id>/refresh', methods=['POST'])
@login_required
def refresh(ciclo_id):
    CicloInventario.query.get_or_404(ciclo_id)
    q = Queue('inventario', connection=_redis_conn())
    job = q.enqueue(
        'app.inventario.workers.refresh_snapshot_worker.refresh_snapshot_worker',
        ciclo_id, job_timeout=900,
    )
    return jsonify({'job_id': job.id, 'status': 'enqueued'}), 202


@inventario_bp.route('/snapshot/<int:ciclo_id>/status/<job_id>')
@login_required
def status(ciclo_id, job_id):
    from rq.job import Job
    try:
        job = Job.fetch(job_id, connection=_redis_conn())
    except Exception:
        return jsonify({'erro': 'job não encontrado'}), 404
    return jsonify({
        'status': job.get_status(),
        'progress': (job.meta or {}).get('progress'),
        'msg': (job.meta or {}).get('msg'),
        'result': job.result,
    })
```

- [ ] **Step 2: Commit**

```bash
git add app/inventario/routes/snapshot_routes.py
git commit -m "feat(inventario): snapshot_routes (refresh async + status polling)"
```

---

### Task 14: `movimentacoes_routes.py` (drill-down)

**Files:**
- Modify: `app/inventario/routes/movimentacoes_routes.py`
- Create: `app/templates/inventario/movimentacoes.html` (placeholder; Task 17 reformula)

- [ ] **Step 1: Implementar**

```python
"""Drill-down: tela de movimentações Odoo paginadas em nova aba."""
from flask import render_template, request, jsonify, send_file
from flask_login import login_required
import io
import xlsxwriter
from app.inventario import inventario_bp
from app.inventario.services.movimentacoes_odoo_service import (
    MovimentacoesOdooService,
)
from app.utils.json_helpers import sanitize_for_json


def _build_filtros(args):
    return {
        'cod': args.get('cod'),
        'empresa': args.get('empresa'),
        'tipo': args.get('tipo'),  # ESTOQUE / PRODUCAO
        'data_inicio': args.get('data_inicio'),
        'data_fim': args.get('data_fim'),
        'origem': args.get('origem'),
        'destino': args.get('destino'),
        'usuario': args.get('usuario'),
        'page': args.get('page', 1, type=int),
        'page_size': args.get('page_size', 100, type=int),
    }


@inventario_bp.route('/movimentacoes')
@login_required
def movimentacoes():
    filtros = _build_filtros(request.args)
    return render_template('inventario/movimentacoes.html', filtros=filtros)


@inventario_bp.route('/movimentacoes/api')
@login_required
def movimentacoes_api():
    filtros = _build_filtros(request.args)
    resultado = MovimentacoesOdooService.buscar_paginado(filtros)
    return jsonify(sanitize_for_json(resultado))


@inventario_bp.route('/movimentacoes/export.xlsx')
@login_required
def movimentacoes_export():
    filtros = _build_filtros(request.args)
    filtros['page_size'] = 1000
    filtros['page'] = 1
    # Limita 5K linhas no export
    todas = []
    for p in range(1, 6):  # max 5 páginas de 1000
        filtros['page'] = p
        r = MovimentacoesOdooService.buscar_paginado(filtros)
        todas.extend(r.get('rows', []))
        if len(r.get('rows', [])) < 1000:
            break

    buf = io.BytesIO()
    wb = xlsxwriter.Workbook(buf, {'in_memory': True})
    ws = wb.add_worksheet('Movimentacoes')
    headers = ['data', 'empresa', 'cod', 'produto', 'lote', 'qtd',
               'origem', 'destino', 'usuario']
    hfmt = wb.add_format({'bold': True, 'bg_color': '#E0E0E0', 'border': 1})
    for i, h in enumerate(headers):
        ws.write(0, i, h, hfmt)
    nfmt = wb.add_format({'num_format': '#,##0.000'})
    for r, row in enumerate(todas, start=1):
        ws.write(r, 0, row.get('data') or '')
        ws.write(r, 1, row.get('empresa') or '')
        ws.write(r, 2, row.get('cod') or '')
        ws.write(r, 3, row.get('produto') or '')
        ws.write(r, 4, row.get('lote') or '')
        ws.write_number(r, 5, float(row.get('qtd') or 0), nfmt)
        ws.write(r, 6, row.get('origem') or '')
        ws.write(r, 7, row.get('destino') or '')
        ws.write(r, 8, row.get('usuario') or '')
    wb.close()
    return send_file(
        io.BytesIO(buf.getvalue()),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        as_attachment=True,
        download_name='MOVIMENTACOES_ODOO.xlsx',
    )
```

- [ ] **Step 2: Template placeholder `movimentacoes.html`**

```html
{% extends "base.html" %}
{% block content %}
<div class="container-fluid py-3">
  <h3>Movimentações Odoo</h3>
  <form id="form-filtros" class="row g-2 mb-3">
    <div class="col-2"><input class="form-control" name="cod" value="{{ filtros.cod or '' }}" placeholder="Código"></div>
    <div class="col-2">
      <select class="form-select" name="empresa">
        <option value="">Todas empresas</option>
        <option value="FB" {% if filtros.empresa=='FB' %}selected{% endif %}>FB</option>
        <option value="CD" {% if filtros.empresa=='CD' %}selected{% endif %}>CD</option>
        <option value="LF" {% if filtros.empresa=='LF' %}selected{% endif %}>LF</option>
      </select>
    </div>
    <div class="col-2">
      <select class="form-select" name="tipo">
        <option value="">Todos tipos</option>
        <option value="ESTOQUE" {% if filtros.tipo=='ESTOQUE' %}selected{% endif %}>Estoque</option>
        <option value="PRODUCAO" {% if filtros.tipo=='PRODUCAO' %}selected{% endif %}>Produção</option>
      </select>
    </div>
    <div class="col-2"><input class="form-control" type="date" name="data_inicio" value="{{ filtros.data_inicio or '' }}"></div>
    <div class="col-2"><input class="form-control" type="date" name="data_fim" value="{{ filtros.data_fim or '' }}"></div>
    <div class="col-2"><input class="form-control" name="usuario" value="{{ filtros.usuario or '' }}" placeholder="Usuário"></div>
    <div class="col-2"><input class="form-control" name="origem" value="{{ filtros.origem or '' }}" placeholder="Origem"></div>
    <div class="col-2"><input class="form-control" name="destino" value="{{ filtros.destino or '' }}" placeholder="Destino"></div>
    <div class="col-2">
      <select class="form-select" name="page_size">
        <option value="100" {% if filtros.page_size==100 %}selected{% endif %}>100</option>
        <option value="500" {% if filtros.page_size==500 %}selected{% endif %}>500</option>
        <option value="1000" {% if filtros.page_size==1000 %}selected{% endif %}>1000</option>
      </select>
    </div>
    <div class="col-2"><button type="submit" class="btn btn-primary w-100">Aplicar</button></div>
  </form>
  <div id="resumo" class="mb-2"></div>
  <div id="tabela">Carregando...</div>
  <script>
    function carregar() {
      const params = new URLSearchParams(new FormData(document.getElementById('form-filtros')));
      fetch('/inventario/movimentacoes/api?' + params)
        .then(r => r.json())
        .then(data => {
          document.getElementById('resumo').innerHTML =
            `Total: ${data.total} | Página ${data.page} | Tamanho: ${data.page_size}`;
          let html = '<table class="table table-sm table-hover"><thead><tr>' +
            '<th>Data</th><th>Empr.</th><th>Cod</th><th>Produto</th><th>Lote</th>' +
            '<th>Qtd</th><th>Origem</th><th>Destino</th><th>Usuário</th></tr></thead><tbody>';
          for (const r of (data.rows || [])) {
            html += `<tr><td>${r.data || ''}</td><td>${r.empresa || ''}</td>` +
              `<td>${r.cod || ''}</td><td>${r.produto || ''}</td>` +
              `<td>${r.lote || ''}</td>` +
              `<td>${Number(r.qtd || 0).toLocaleString('pt-BR',{minimumFractionDigits:3})}</td>` +
              `<td>${r.origem || ''}</td><td>${r.destino || ''}</td>` +
              `<td>${r.usuario || ''}</td></tr>`;
          }
          html += '</tbody></table>';
          document.getElementById('tabela').innerHTML = html;
        });
    }
    document.getElementById('form-filtros').addEventListener('submit', (e) => {
      e.preventDefault();
      carregar();
    });
    carregar();
  </script>
</div>
{% endblock %}
```

- [ ] **Step 3: Commit**

```bash
git add app/inventario/routes/movimentacoes_routes.py app/templates/inventario/movimentacoes.html
git commit -m "feat(inventario): movimentacoes_routes (drill-down on-demand + export)"
```

---

## Phase 4 — Worker

### Task 15: Worker `refresh_snapshot_worker` + integração

**Files:**
- Create: `app/inventario/workers/refresh_snapshot_worker.py`
- Modify: `worker_render.py` (linhas ~143 e ~211)
- Modify: `start_worker_render.sh` (linha ~301)

- [ ] **Step 1: Criar worker**

```python
"""Worker RQ que refresca snapshot Odoo."""
from app import create_app


def refresh_snapshot_worker(ciclo_id: int):
    app = create_app()
    with app.app_context():
        from rq import get_current_job
        from app.inventario.services.snapshot_odoo_service import SnapshotOdooService
        job = get_current_job()
        return SnapshotOdooService.refresh(ciclo_id, job=job)
```

- [ ] **Step 2: Editar `worker_render.py`**

Localizar (~linha 143) a string `--queues default='...'` e adicionar `inventario`:

```python
# Original (procurar):
'--queues', os.environ.get('RQ_QUEUES_DEFAULT', 'atacadao,high,impostos,default')
# Modificar para:
'--queues', os.environ.get('RQ_QUEUES_DEFAULT', 'atacadao,high,inventario,impostos,default')
```

Localizar (~linha 211) `FILAS_PESADAS = {...}` e adicionar:

```python
# Original:
FILAS_PESADAS = {'atacadao', 'impostos'}
# Modificar para:
FILAS_PESADAS = {'atacadao', 'impostos', 'inventario'}
```

- [ ] **Step 3: Editar `start_worker_render.sh`**

Localizar (~linha 301) `--queues high,...,default` e adicionar `inventario`:

```bash
# Original:
--queues high,atacadao,impostos,default
# Modificar para:
--queues high,atacadao,inventario,impostos,default
```

- [ ] **Step 4: Verificar que worker local processa (smoke local)**

Rodar em terminal separado:
```bash
source .venv/bin/activate && python worker_atacadao.py --queues inventario,high,default
```

Em outro terminal, enfileirar um job manualmente:
```bash
source .venv/bin/activate && python -c "
from app import create_app
app = create_app()
ctx = app.app_context(); ctx.push()
from rq import Queue
from redis import Redis
import os
q = Queue('inventario', connection=Redis.from_url(os.environ.get('REDIS_URL', 'redis://localhost:6379/0')))
job = q.enqueue('app.inventario.workers.refresh_snapshot_worker.refresh_snapshot_worker', 1, job_timeout=900)
print('Job:', job.id)
"
```

Worker deve processar (mesmo que falhe por ciclo 1 não existir — confirma fila monitorada).

- [ ] **Step 5: Commit**

```bash
git add app/inventario/workers/refresh_snapshot_worker.py worker_render.py start_worker_render.sh
git commit -m "feat(inventario): worker RQ refresh_snapshot + integração worker_render"
```

---

## Phase 5 — Frontend refinado (templates + JS + CSS)

### Task 16: Reformular `ciclos.html` com upload xlsx + criar ciclo

**Files:**
- Modify: `app/templates/inventario/ciclos.html`

- [ ] **Step 1: Template completo**

```html
{% extends "base.html" %}
{% block title %}Inventário — Ciclos{% endblock %}
{% block content %}
<div class="container-fluid py-3">
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h2>Inventário — Ciclos</h2>
    <button class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#modalNovoCiclo">
      + Novo Ciclo
    </button>
  </div>

  <table class="table table-striped table-hover">
    <thead>
      <tr>
        <th>Código</th><th>Data Snapshot</th><th>Descrição</th>
        <th>Status</th><th>Criado em</th><th>Ações</th>
      </tr>
    </thead>
    <tbody>
      {% for c in ciclos %}
      <tr>
        <td><strong>{{ c.codigo }}</strong></td>
        <td>{{ c.data_snapshot }}</td>
        <td>{{ c.descricao or '—' }}</td>
        <td>
          {% if c.status == 'ATIVO' %}
            <span class="badge bg-success">ATIVO</span>
          {% else %}
            <span class="badge bg-secondary">{{ c.status }}</span>
          {% endif %}
        </td>
        <td>{{ c.criado_em.strftime('%d/%m/%Y %H:%M') if c.criado_em else '' }}</td>
        <td>
          <a href="{{ url_for('inventario.confronto_por_id', ciclo_id=c.id) }}"
             class="btn btn-sm btn-primary">Abrir</a>
          <button class="btn btn-sm btn-outline-secondary"
                  data-bs-toggle="modal" data-bs-target="#modalUpload"
                  data-ciclo-id="{{ c.id }}">Upload XLSX</button>
        </td>
      </tr>
      {% else %}
      <tr><td colspan="6" class="text-center text-muted">Nenhum ciclo cadastrado</td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<!-- Modal Novo Ciclo -->
<div class="modal fade" id="modalNovoCiclo" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <form id="form-novo-ciclo">
        <div class="modal-header">
          <h5 class="modal-title">Novo Ciclo de Inventário</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <div class="mb-3">
            <label class="form-label">Código (ex.: INV-2026-05)</label>
            <input class="form-control" name="codigo" required>
          </div>
          <div class="mb-3">
            <label class="form-label">Data do Snapshot</label>
            <input class="form-control" type="date" name="data_snapshot" required>
          </div>
          <div class="mb-3">
            <label class="form-label">Descrição</label>
            <input class="form-control" name="descricao">
          </div>
        </div>
        <div class="modal-footer">
          <button type="submit" class="btn btn-primary">Criar</button>
        </div>
      </form>
    </div>
  </div>
</div>

<!-- Modal Upload XLSX -->
<div class="modal fade" id="modalUpload" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <form id="form-upload" enctype="multipart/form-data">
        <div class="modal-header">
          <h5 class="modal-title">Upload XLSX Inventário</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <p>XLSX deve ter abas <strong>FB</strong>, <strong>CD</strong> e
            <strong>LF</strong> com colunas <code>CODIGO</code>, <code>LOTE</code>,
            <code>QTD</code>. Re-upload <strong>substitui</strong> as linhas
            existentes do ciclo.</p>
          <input type="file" class="form-control" name="arquivo" accept=".xlsx" required>
          <input type="hidden" name="ciclo_id">
          <div id="upload-resultado" class="mt-3"></div>
        </div>
        <div class="modal-footer">
          <button type="submit" class="btn btn-primary">Enviar</button>
        </div>
      </form>
    </div>
  </div>
</div>

<script>
document.getElementById('form-novo-ciclo').addEventListener('submit', (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  fetch('/inventario/ciclos/novo', {method: 'POST', body: fd})
    .then(r => r.json())
    .then(d => {
      if (d.erro) { alert('Erro: ' + d.erro); return; }
      location.reload();
    });
});

document.getElementById('modalUpload').addEventListener('show.bs.modal', (e) => {
  const cid = e.relatedTarget.getAttribute('data-ciclo-id');
  document.querySelector('#form-upload input[name="ciclo_id"]').value = cid;
});

document.getElementById('form-upload').addEventListener('submit', (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  const cid = fd.get('ciclo_id');
  fd.delete('ciclo_id');
  fetch(`/inventario/ciclos/${cid}/upload`, {method: 'POST', body: fd})
    .then(r => r.json())
    .then(d => {
      document.getElementById('upload-resultado').innerHTML =
        `<div class="alert alert-info">Inseridos: ${d.inseridos}, ` +
        `Pulados: ${d.pulados}, Erros: ${d.erros ? d.erros.length : 0}</div>`;
    });
});
</script>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add app/templates/inventario/ciclos.html
git commit -m "feat(inventario): tela completa ciclos.html com modais criar/upload"
```

---

### Task 17: Reformular `confronto.html` (tela principal interativa)

**Files:**
- Modify: `app/templates/inventario/confronto.html`
- Create: `app/static/js/inventario/confronto.js`
- Create: `app/static/css/modules/_inventario.css`

- [ ] **Step 1: CSS módulo `_inventario.css`**

```css
/* Módulo Inventário — usa design tokens */
.inv-tabela {
  font-size: 0.85rem;
}
.inv-tabela th {
  background: var(--bg-light);
  position: sticky;
  top: 0;
  z-index: 10;
}
.inv-tabela td.num {
  text-align: right;
  font-family: var(--font-mono, monospace);
}
.inv-row-divergente {
  background: var(--bg-warning-soft, #fff3cd);
}
.inv-cell-drill {
  cursor: pointer;
  text-decoration: underline dotted;
}
.inv-cell-drill:hover {
  color: var(--text-link, #0d6efd);
}
.inv-snapshot-status {
  font-size: 0.85rem;
  color: var(--text-muted);
}
.inv-snapshot-status.stale {
  color: var(--text-warning, #997404);
}
```

Adicionar import no `app/static/css/main.css` na seção `@layer modules`:

```css
@import url('modules/_inventario.css') layer(modules);
```

- [ ] **Step 2: Reformular `confronto.html`**

```html
{% extends "base.html" %}
{% block title %}Inventário — Confronto {{ ciclo.codigo }}{% endblock %}
{% block content %}
<div class="container-fluid py-3">
  <div class="d-flex justify-content-between align-items-center mb-3">
    <div>
      <h2 class="mb-0">Confronto — {{ ciclo.codigo }}</h2>
      <small class="text-muted">Snapshot: {{ ciclo.data_snapshot.strftime('%d/%m/%Y') }}</small>
    </div>
    <div>
      <span class="inv-snapshot-status">
        Snapshot Odoo: <span id="ts-snapshot">
          {{ last_refresh.strftime('%d/%m/%Y %H:%M') if last_refresh else 'nunca gerado' }}
        </span>
      </span>
      <button id="btn-refresh" class="btn btn-sm btn-outline-secondary">
        Atualizar Odoo
      </button>
      <a href="{{ url_for('inventario.confronto_export', ciclo_id=ciclo.id) }}"
         class="btn btn-sm btn-success">Exportar XLSX</a>
      <a href="{{ url_for('inventario.listar_ajustes', ciclo_id=ciclo.id) }}"
         class="btn btn-sm btn-outline-primary">Ajustes Manuais</a>
    </div>
  </div>

  <div class="row g-2 mb-3">
    <div class="col-3">
      <input id="filtro-busca" class="form-control form-control-sm"
             placeholder="Filtrar cod/produto...">
    </div>
    <div class="col-3">
      <div class="form-check form-check-inline">
        <input id="filtro-divergente" class="form-check-input" type="checkbox">
        <label class="form-check-label">Só com diferença</label>
      </div>
    </div>
    <div class="col-6 text-end">
      <span id="resumo" class="text-muted small"></span>
    </div>
  </div>

  <div id="job-progress" class="d-none alert alert-info">
    <div class="progress" style="height:8px"><div class="progress-bar" style="width:0%"></div></div>
    <small class="mt-1 d-block">Atualizando Odoo... <span id="job-msg"></span></small>
  </div>

  <div class="table-responsive">
    <table id="tabela-confronto" class="table table-sm table-striped inv-tabela">
      <thead>
        <tr>
          <th>cod</th><th>produto</th>
          <th>FB</th><th>CD</th><th>LF</th><th>TOTAL</th>
          <th>COMPRAS</th><th>PA</th><th>COMP.</th>
          <th>VENDAS</th><th>CONSUMO</th><th>PRODUÇÃO</th>
          <th>AJ.LOCAL</th><th>AJ.QTD</th>
          <th>ODOO</th><th>MOV</th><th>SIST</th>
          <th>ODOO-MOV</th><th>SIST-MOV</th>
          <th>FB-O</th><th>CD-O</th><th>LF-O</th>
        </tr>
      </thead>
      <tbody id="tbody-confronto"><tr><td colspan="22">Carregando...</td></tr></tbody>
    </table>
  </div>
</div>

<script>
const CICLO_ID = {{ ciclo.id }};
</script>
<script src="{{ url_for('static', filename='js/inventario/confronto.js') }}"></script>
{% endblock %}
```

- [ ] **Step 3: JS `confronto.js`**

```javascript
// app/static/js/inventario/confronto.js
let LINHAS_CACHE = [];

function fmt(v) {
  if (v == null || v === '') return '';
  return Number(v).toLocaleString('pt-BR',
    {minimumFractionDigits: 3, maximumFractionDigits: 3});
}

function drillUrl(cod, empresa, tipo) {
  const params = new URLSearchParams({
    cod: cod, empresa: empresa || '', tipo: tipo || 'ESTOQUE',
    data_inicio: '2026-05-16',
  });
  return `/inventario/movimentacoes?${params}`;
}

function renderLinhas(linhas) {
  const tbody = document.getElementById('tbody-confronto');
  if (!linhas.length) {
    tbody.innerHTML = '<tr><td colspan="22">Nenhuma linha</td></tr>';
    return;
  }
  let html = '';
  for (const l of linhas) {
    const divergente = Math.abs(l.odoo_menos_mov || 0) > 1 ||
                       Math.abs(l.sist_menos_mov || 0) > 1;
    html += `<tr ${divergente ? 'class="inv-row-divergente"' : ''}>` +
      `<td><strong>${l.cod_produto}</strong></td>` +
      `<td>${l.nome_produto || ''}</td>` +
      `<td class="num">${fmt(l.inv_fb)}</td>` +
      `<td class="num">${fmt(l.inv_cd)}</td>` +
      `<td class="num">${fmt(l.inv_lf)}</td>` +
      `<td class="num"><strong>${fmt(l.inv_total)}</strong></td>` +
      `<td class="num inv-cell-drill" onclick="window.open('${drillUrl(l.cod_produto, '', 'ESTOQUE')}','_blank')">${fmt(l.compras)}</td>` +
      `<td class="num inv-cell-drill" onclick="window.open('${drillUrl(l.cod_produto, '', 'PRODUCAO')}','_blank')">${fmt(l.pa)}</td>` +
      `<td class="num inv-cell-drill" onclick="window.open('${drillUrl(l.cod_produto, '', 'PRODUCAO')}','_blank')">${fmt(l.componente)}</td>` +
      `<td class="num">${fmt(l.vendas)}</td>` +
      `<td class="num">${fmt(l.consumo)}</td>` +
      `<td class="num">${fmt(l.producao)}</td>` +
      `<td>${l.ajuste_local || ''}</td>` +
      `<td class="num">${fmt(l.ajuste_qtd)}</td>` +
      `<td class="num"><strong>${fmt(l.odoo)}</strong></td>` +
      `<td class="num"><strong>${fmt(l.mov)}</strong></td>` +
      `<td class="num"><strong>${fmt(l.sist)}</strong></td>` +
      `<td class="num">${fmt(l.odoo_menos_mov)}</td>` +
      `<td class="num">${fmt(l.sist_menos_mov)}</td>` +
      `<td class="num inv-cell-drill" onclick="window.open('${drillUrl(l.cod_produto, 'FB', 'ESTOQUE')}','_blank')">${fmt(l.est_fb)}</td>` +
      `<td class="num inv-cell-drill" onclick="window.open('${drillUrl(l.cod_produto, 'CD', 'ESTOQUE')}','_blank')">${fmt(l.est_cd)}</td>` +
      `<td class="num inv-cell-drill" onclick="window.open('${drillUrl(l.cod_produto, 'LF', 'ESTOQUE')}','_blank')">${fmt(l.est_lf)}</td>` +
      `</tr>`;
  }
  tbody.innerHTML = html;
  document.getElementById('resumo').textContent = `${linhas.length} produtos`;
}

function aplicarFiltros() {
  const busca = (document.getElementById('filtro-busca').value || '').toLowerCase();
  const soDiv = document.getElementById('filtro-divergente').checked;
  let f = LINHAS_CACHE;
  if (busca) {
    f = f.filter(l => (l.cod_produto || '').toLowerCase().includes(busca) ||
                       (l.nome_produto || '').toLowerCase().includes(busca));
  }
  if (soDiv) {
    f = f.filter(l => Math.abs(l.odoo_menos_mov || 0) > 1 ||
                      Math.abs(l.sist_menos_mov || 0) > 1);
  }
  renderLinhas(f);
}

function carregar() {
  fetch(`/inventario/confronto/${CICLO_ID}/api`)
    .then(r => r.json())
    .then(data => {
      LINHAS_CACHE = data.linhas || [];
      aplicarFiltros();
    });
}

function pollJob(jobId) {
  const interval = setInterval(() => {
    fetch(`/inventario/snapshot/${CICLO_ID}/status/${jobId}`)
      .then(r => r.json())
      .then(d => {
        const bar = document.querySelector('#job-progress .progress-bar');
        bar.style.width = (d.progress || 0) + '%';
        document.getElementById('job-msg').textContent = d.msg || d.status;
        if (d.status === 'finished') {
          clearInterval(interval);
          document.getElementById('job-progress').classList.add('d-none');
          carregar();
        } else if (d.status === 'failed') {
          clearInterval(interval);
          document.getElementById('job-msg').textContent = 'FALHOU';
        }
      });
  }, 2000);
}

document.getElementById('btn-refresh').addEventListener('click', () => {
  document.getElementById('job-progress').classList.remove('d-none');
  fetch(`/inventario/snapshot/${CICLO_ID}/refresh`, {method: 'POST'})
    .then(r => r.json()).then(d => pollJob(d.job_id));
});
document.getElementById('filtro-busca').addEventListener('input', aplicarFiltros);
document.getElementById('filtro-divergente').addEventListener('change', aplicarFiltros);
carregar();
```

- [ ] **Step 4: Commit**

```bash
git add app/templates/inventario/confronto.html app/static/js/inventario/confronto.js app/static/css/modules/_inventario.css app/static/css/main.css
git commit -m "feat(inventario): tela confronto.html interativa + JS drill-down + CSS módulo"
```

---

### Task 18: Reformular `ajustes_manuais.html` (CRUD inline)

**Files:**
- Modify: `app/templates/inventario/ajustes_manuais.html`

- [ ] **Step 1: Template completo**

```html
{% extends "base.html" %}
{% block title %}Inventário — Ajustes Manuais{% endblock %}
{% block content %}
<div class="container py-3">
  <div class="d-flex justify-content-between mb-3">
    <h3>Ajustes Manuais — Ciclo {{ ciclo_id }}</h3>
    <button class="btn btn-primary btn-sm" data-bs-toggle="modal" data-bs-target="#modalAjuste">
      + Novo Ajuste
    </button>
  </div>

  <table class="table table-striped table-sm">
    <thead>
      <tr>
        <th>Cod</th><th>Produto</th><th>Local</th>
        <th class="text-end">Qtd</th><th>Tipo</th><th>Observação</th>
        <th>Criado em</th><th>Por</th><th>Ações</th>
      </tr>
    </thead>
    <tbody id="tbody-ajustes">
      {% for a in ajustes %}
      <tr data-id="{{ a.id }}">
        <td>{{ a.cod_produto }}</td>
        <td>{{ a.nome_produto or '' }}</td>
        <td>{{ a.local or '' }}</td>
        <td class="text-end">{{ "{:,.3f}".format(a.qtd|float).replace(',', '|').replace('.', ',').replace('|', '.') }}</td>
        <td>{{ a.tipo_ajuste or '' }}</td>
        <td>{{ a.observacao or '' }}</td>
        <td>{{ a.criado_em.strftime('%d/%m/%Y %H:%M') if a.criado_em }}</td>
        <td>{{ a.criado_por or '' }}</td>
        <td>
          <button class="btn btn-sm btn-outline-danger btn-delete">×</button>
        </td>
      </tr>
      {% else %}
      <tr><td colspan="9" class="text-muted text-center">Nenhum ajuste cadastrado</td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>

<div class="modal fade" id="modalAjuste" tabindex="-1">
  <div class="modal-dialog">
    <div class="modal-content">
      <form id="form-ajuste">
        <div class="modal-header"><h5>Novo Ajuste Manual</h5>
          <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
        </div>
        <div class="modal-body">
          <div class="row g-2">
            <div class="col-6"><label>Código</label>
              <input class="form-control" name="cod_produto" required></div>
            <div class="col-6"><label>Local</label>
              <select class="form-select" name="local">
                <option value="">—</option><option>FB</option><option>CD</option><option>LF</option>
              </select></div>
            <div class="col-12"><label>Produto (descrição)</label>
              <input class="form-control" name="nome_produto"></div>
            <div class="col-6"><label>Qtd</label>
              <input class="form-control" name="qtd" type="number" step="0.001" required></div>
            <div class="col-6"><label>Tipo</label>
              <select class="form-select" name="tipo_ajuste">
                <option value="">—</option><option>POSITIVO</option>
                <option>NEGATIVO</option><option>OK</option>
              </select></div>
            <div class="col-12"><label>Observação</label>
              <textarea class="form-control" name="observacao" rows="2"></textarea></div>
          </div>
        </div>
        <div class="modal-footer">
          <button type="submit" class="btn btn-primary">Salvar</button>
        </div>
      </form>
    </div>
  </div>
</div>

<script>
const CICLO_ID = {{ ciclo_id }};

document.getElementById('form-ajuste').addEventListener('submit', (e) => {
  e.preventDefault();
  const fd = new FormData(e.target);
  fetch(`/inventario/ajustes/${CICLO_ID}`, {method: 'POST', body: fd})
    .then(r => r.json()).then(d => {
      if (d.erro) { alert(d.erro); return; }
      location.reload();
    });
});

document.querySelectorAll('.btn-delete').forEach(btn => {
  btn.addEventListener('click', (e) => {
    const tr = e.target.closest('tr');
    if (!confirm('Excluir ajuste?')) return;
    fetch(`/inventario/ajustes/${CICLO_ID}/${tr.dataset.id}`, {method: 'DELETE'})
      .then(() => tr.remove());
  });
});
</script>
{% endblock %}
```

- [ ] **Step 2: Commit**

```bash
git add app/templates/inventario/ajustes_manuais.html
git commit -m "feat(inventario): tela ajustes_manuais.html (CRUD inline com modal)"
```

---

## Phase 6 — Integração + Validação

### Task 19: Adicionar link no menu `base.html`

**Files:**
- Modify: `app/templates/base.html`

- [ ] **Step 1: Localizar seção de menu apropriada e adicionar item**

Buscar no `base.html` a seção do menu (sidebar ou top nav). Localizar onde "Estoque" ou "Operações" estão e adicionar:

```html
{% if current_user.is_authenticated and current_user.tipo in
       ['administrador', 'logistica', 'financeiro', 'gerente_comercial'] %}
<li class="nav-item">
  <a class="nav-link" href="{{ url_for('inventario.listar_ciclos') }}">
    <i class="fas fa-clipboard-list"></i> Inventário — Confronto
  </a>
</li>
{% endif %}
```

- [ ] **Step 2: Verificar manualmente que o item aparece**

Run: `source .venv/bin/activate && python run.py`
Abrir `http://localhost:5000` → autenticar → verificar item de menu visível.

- [ ] **Step 3: Commit**

```bash
git add app/templates/base.html
git commit -m "feat(inventario): link no menu base.html"
```

---

### Task 20: Test de rotas (integração)

**Files:**
- Create: `tests/inventario/test_routes.py`

- [ ] **Step 1: Escrever testes de rota**

```python
"""Testes de integração das rotas do módulo inventario."""
from datetime import date
from io import BytesIO
import openpyxl
import pytest
from app import db
from app.inventario.models import CicloInventario, AjusteManualInventario
from app.auth.models import Usuario  # ajustar import conforme modelo real


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def user_logado(app, client):
    """Cria user admin e loga via session."""
    u = Usuario(nome='Test', email='t@t.com', tipo='administrador')
    u.set_senha('x')
    db.session.add(u); db.session.commit()
    with client.session_transaction() as s:
        s['_user_id'] = str(u.id)
    return u


def test_listar_ciclos_sem_login_redirect(client):
    resp = client.get('/inventario/ciclos')
    assert resp.status_code in (302, 401)


def test_criar_ciclo_sucesso(client, user_logado):
    resp = client.post('/inventario/ciclos/novo', data={
        'codigo': 'INV-TESTE-X', 'data_snapshot': '2026-05-16',
        'descricao': 'Teste',
    })
    assert resp.status_code == 201
    assert resp.json['codigo'] == 'INV-TESTE-X'


def test_criar_ciclo_duplicado_409(client, user_logado, ciclo):
    resp = client.post('/inventario/ciclos/novo', data={
        'codigo': ciclo.codigo, 'data_snapshot': '2026-05-16',
    })
    assert resp.status_code == 409


def test_upload_xlsx_sucesso(client, user_logado, ciclo):
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for emp in ('FB', 'CD', 'LF'):
        ws = wb.create_sheet(emp)
        ws.append(['CODIGO', 'LOTE', 'QTD'])
        ws.append(['4320147', '139/26', 100])
    buf = BytesIO(); wb.save(buf); buf.seek(0)
    resp = client.post(f'/inventario/ciclos/{ciclo.id}/upload',
                        data={'arquivo': (buf, 'inv.xlsx')},
                        content_type='multipart/form-data')
    assert resp.status_code == 200
    assert resp.json['inseridos'] == 3


def test_confronto_api_retorna_linhas(client, user_logado, ciclo):
    resp = client.get(f'/inventario/confronto/{ciclo.id}/api')
    assert resp.status_code == 200
    assert 'linhas' in resp.json


def test_confronto_export_xlsx_content_type(client, user_logado, ciclo):
    resp = client.get(f'/inventario/confronto/{ciclo.id}/export.xlsx')
    assert resp.status_code == 200
    assert 'spreadsheetml' in resp.content_type


def test_criar_ajuste_manual(client, user_logado, ciclo):
    resp = client.post(f'/inventario/ajustes/{ciclo.id}', data={
        'cod_produto': '208000041', 'qtd': '500',
        'local': 'CD', 'tipo_ajuste': 'POSITIVO',
    })
    assert resp.status_code == 201

    listing = client.get(f'/inventario/ajustes/{ciclo.id}')
    assert listing.status_code == 200
```

- [ ] **Step 2: Run tests**

Run: `source .venv/bin/activate && pytest tests/inventario/test_routes.py -v`
Expected: 7 passed (ajustar import de Usuario conforme estrutura real do projeto).

- [ ] **Step 3: Commit**

```bash
git add tests/inventario/test_routes.py
git commit -m "test(inventario): testes de integração de rotas"
```

---

### Task 21: Rodar migration em PROD (Render)

**Files:** (sem mudança de código)

- [ ] **Step 1: Rodar migration no Render Shell**

Conectar ao Render Shell do serviço `sistema-fretes` e executar:

```bash
python scripts/migrations/inventario_create_tables.py
```

Expected: `Criadas: 4`.

- [ ] **Step 2: Validar via psql (Render Shell)**

```bash
psql $DATABASE_URL -c "SELECT tablename FROM pg_tables WHERE tablename LIKE 'inventario_%'"
```

Expected: 4 linhas — `inventario_ciclo`, `inventario_base`, `inventario_ajuste_manual`, `inventario_snapshot_odoo`.

- [ ] **Step 3: Confirmar e seguir** (sem commit — operacional)

---

### Task 22: Smoke test end-to-end

**Files:** (sem mudança de código)

- [ ] **Step 1: Criar ciclo INV-TESTE no banco LOCAL**

Run: `source .venv/bin/activate && python -c "
from app import create_app, db
from app.inventario.models import CicloInventario
from datetime import date
app = create_app()
with app.app_context():
    c = CicloInventario(codigo='INV-TESTE-2026-05', data_snapshot=date(2026,5,16),
                        descricao='Smoke test', criado_por='claude')
    db.session.add(c); db.session.commit()
    print('Ciclo criado:', c.id)
"`

- [ ] **Step 2: Upload xlsx existente da pasta inventário**

Pegar planilha real:
```bash
ls /mnt/c/Users/rafael.nascimento/Downloads/INVENTARIO\ 16-05-26/*.xlsx 2>/dev/null || \
  echo "AVISO: planilha não no caminho default"
```

Subir via UI: abrir `http://localhost:5000/inventario/ciclos` → upload no ciclo
INV-TESTE-2026-05.

Validar inseridos.

- [ ] **Step 3: Refresh Odoo (worker local rodando)**

Em outro terminal:
```bash
source .venv/bin/activate && python worker_atacadao.py --queues inventario,high,default
```

Pela UI clicar em "Atualizar Odoo" → aguardar progresso até 100%.

Validar:
```bash
source .venv/bin/activate && python -c "
from app import create_app, db
from app.inventario.models import InventarioSnapshotOdoo
app = create_app()
with app.app_context():
    cnt = InventarioSnapshotOdoo.query.count()
    print(f'Snapshots: {cnt}')
"`
```

- [ ] **Step 4: Comparar com planilha referência**

Abrir `http://localhost:5000/inventario/confronto/<ciclo_id>` em browser.

Comparar 5 produtos aleatórios com a aba `Planilha1` em:
`docs/inventario-2026-05/07-relatorios/MOVS_ESTOQUE_RENDER_2026-05-25_20-20.xlsx`

Validar que valores batem (FB/CD/LF inventário, COMPRAS, PA, COMPONENTE, ODOO,
SIST).

- [ ] **Step 5: Validar drill-down**

Clicar em uma célula COMPRAS de um produto → nova aba abre →
movimentações do Odoo retornadas paginadas → trocar pagesize para 500/1000 →
verificar funciona.

- [ ] **Step 6: Validar export XLSX**

Clicar em "Exportar XLSX" → abrir no Excel → conferir 6 abas com dados:
- Confronto (com formatação de divergência amarela)
- Ajustes_Manuais
- Apontamentos_PA_Comp
- Movimentacoes_Sistema
- Estoque_Odoo_por_Empresa
- Inventario_Base

- [ ] **Step 7: Cadastrar 2 ajustes manuais via UI**

Abrir `/inventario/ajustes/<ciclo_id>` → criar 2 ajustes → voltar ao confronto →
ver que aparecem nas colunas AJ.LOCAL/AJ.QTD.

- [ ] **Step 8: Documentar resultado em comentário no spec**

Editar o spec (`docs/superpowers/specs/2026-05-26-relatorio-confronto-inventario-design.md`)
adicionando seção "## 16. Smoke test (resultado)" com checkpoints OK/falhas.

- [ ] **Step 9: Commit final**

```bash
git add docs/superpowers/specs/2026-05-26-relatorio-confronto-inventario-design.md
git commit -m "docs(inventario): registrar resultado do smoke test end-to-end"
```

---

### Task 23: Validação PROD — comparar tela com dados reais Render

**Files:** (sem mudança de código)

- [ ] **Step 1: Push das branches/migrations para PROD**

Run: `git push origin main`. Auto-deploy do Render dispara.

Aguardar deploy concluir (ver `mcp__render__list_deploys` ou `https://dashboard.render.com`).

- [ ] **Step 2: Rodar migration em PROD via Render Shell**

Já feita em Task 21. Validar:
```bash
psql $DATABASE_URL -c "\d inventario_base"
```

- [ ] **Step 3: Criar ciclo no PROD via UI**

Abrir tela em PROD (`https://sistema-fretes.onrender.com/inventario/ciclos`) →
criar ciclo `INV-2026-05` data 2026-05-16 → upload xlsx real.

- [ ] **Step 4: Apertar "Atualizar Odoo" em PROD**

Aguardar worker `sistema-fretes-worker-atacadao` processar (deve ter `inventario`
em queues após deploy).

Acompanhar via `mcp__render__list_logs` filtrando worker.

- [ ] **Step 5: Validar contra dados reais Render**

Comparar 10 produtos representativos contra:
- `movimentacao_estoque` via `mcp__render__query_render_postgres`
- aba Planilha1 do XLSX referência

Espera-se: SIST bate com sum movimentacao_estoque; ODOO bate com snapshot.

- [ ] **Step 6: Documentar validação em comentário no spec ou release notes**

Anotar no spec resultado da validação PROD (números reais validados ou
discrepâncias encontradas).

```bash
git add docs/superpowers/specs/2026-05-26-relatorio-confronto-inventario-design.md
git commit -m "docs(inventario): registrar validação PROD com dados reais"
git push origin main
```

---

## Self-Review (concluído pelo writer)

### Cobertura da spec
- [x] Seção 2 (Arquitetura): Tasks 1, 19 (esqueleto + menu)
- [x] Seção 3 (Modelos): Tasks 2, 3 (modelos + migrations)
- [x] Seção 4 (Routes 5 arquivos): Tasks 10, 11, 12, 13, 14
- [x] Seção 5 (Services 5 arquivos): Tasks 5, 6, 7, 8, 9
- [x] Seção 6 (UI Templates): Tasks 11, 14, 16, 17, 18
- [x] Seção 7 (Worker + integração): Task 15
- [x] Seção 8 (Mapeamento dados): codificado em ConfrontoService Task 6
- [x] Seção 9 (Erros e bordas): cobertos em testes Tasks 5, 6, 7, 8
- [x] Seção 10 (Testes): Tasks 2, 5, 6, 7, 8, 9, 20
- [x] Seção 11 (Migrations): Task 3
- [x] Schema fix mencionado: Task 4
- [x] Validação PROD: Tasks 21, 22, 23

### Placeholder scan
- Sem "TBD/TODO/FIXME" em código. Comentários como `# ajustar import` em testes são marcadores legítimos (test fixture).

### Type/method consistency
- `ConfrontoService.montar_linhas(ciclo_id)` consistente em Task 6 + uso em Tasks 9, 11
- `SnapshotOdooService.refresh(ciclo_id, job)` consistente Task 7 + 15
- `InventarioLoader.carregar(ciclo_id, file_storage, criado_por)` consistente Task 5 + 10
- `MovimentacoesOdooService.buscar_paginado(filtros)` consistente Task 8 + 14
- `ExportXlsxService.gerar(ciclo_id)` consistente Task 9 + 11
- Modelos: nomes de coluna idênticos entre Task 2 (definição) + Tasks 5-9 (uso)

---

## Execução

**Plan complete and saved to `docs/superpowers/plans/2026-05-26-relatorio-confronto-inventario-plan.md`.**

Estratégia recomendada: **executing-plans inline com checkpoints** (Phase-by-Phase), porque:
- 23 tasks com forte ordem sequencial (foundation → services → routes → frontend → validação)
- Phase 1 (Tasks 1-4) é foundation crítica; quebra cedo trava todo o resto
- Phase 6 (Tasks 21-23) requer interação com PROD que precisa ser supervisionada
- Subagent-driven seria overkill — cada task é específica e auto-contida no plano
