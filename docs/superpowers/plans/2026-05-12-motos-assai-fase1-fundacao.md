<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Motos Assaí — Fase 1 (Fundação) Implementation Plan

> **Papel:** Motos Assaí — Fase 1 (Fundação) Implementation Plan.

## Indice

- [File Structure](#file-structure)
  - [Migrations a criar (em `scripts/migrations/`)](#migrations-a-criar-em-scriptsmigrations)
  - [Models a criar (em `app/motos_assai/models/`)](#models-a-criar-em-appmotos_assaimodels)
  - [Models a modificar (em `app/motos_assai/models/`)](#models-a-modificar-em-appmotos_assaimodels)
  - [Services a criar/modificar](#services-a-criarmodificar)
  - [Refactor cross-projeto (Big Bang A18)](#refactor-cross-projeto-big-bang-a18)
  - [Tests a criar](#tests-a-criar)
- [Tasks](#tasks)
  - [Task 1: Pré-requisito — confirmar Migration 17 em prod](#task-1-pré-requisito-confirmar-migration-17-em-prod)
  - [Task 2: Migration 18 — `assai_carregamento` + `assai_carregamento_item`](#task-2-migration-18-assai_carregamento-assai_carregamento_item)
  - [Task 3: Migration 19 — `assai_divergencia`](#task-3-migration-19-assai_divergencia)
  - [Task 4: Migration 20 — `assai_pedido_excel`](#task-4-migration-20-assai_pedido_excel)
  - [Task 5: Migration 22 — Campos de cancelamento em `assai_nf_qpa`](#task-5-migration-22-campos-de-cancelamento-em-assai_nf_qpa)
  - [Task 6: Migration 24 — CHECK constraints aceitar novos status](#task-6-migration-24-check-constraints-aceitar-novos-status)
  - [Task 7: Migration 26 — `assai_nf_qpa_item_vinculo_historico`](#task-7-migration-26-assai_nf_qpa_item_vinculo_historico)
  - [Task 8: Migration 27 — UNIQUE parcial NF ativa por sep](#task-8-migration-27-unique-parcial-nf-ativa-por-sep)
  - [Task 9: Criar models Python — `AssaiCarregamento` + `AssaiCarregamentoItem`](#task-9-criar-models-python-assaicarregamento-assaicarregamentoitem)
  - [Task 10: Criar model — `AssaiDivergencia`](#task-10-criar-model-assaidivergencia)
  - [Task 11: Criar model — `AssaiPedidoExcel`](#task-11-criar-model-assaipedidoexcel)
  - [Task 12: Criar model — `AssaiNfQpaItemVinculoHistorico`](#task-12-criar-model-assainfqpaitemvinculohistorico)
  - [Task 13: Atualizar `models/separacao.py` — `SEPARACAO_STATUS_CARREGADA`](#task-13-atualizar-modelsseparacaopy-separacao_status_carregada)
  - [Task 14: Atualizar `models/nf_qpa.py` — `NF_STATUS_CANCELADA` + 3 colunas](#task-14-atualizar-modelsnf_qpapy-nf_status_cancelada-3-colunas)
  - [Task 15: Atualizar `models/moto.py` — `EVENTO_CARREGADA`](#task-15-atualizar-modelsmotopy-evento_carregada)
  - [Task 16: Atualizar `models/pedido.py` — 4 status novos](#task-16-atualizar-modelspedidopy-4-status-novos)
  - [Task 17: Service `recalcular_status_pedido`](#task-17-service-recalcular_status_pedido)
  - [Task 18: Migration 21 — Backfill status pedido](#task-18-migration-21-backfill-status-pedido)
  - [Task 19: Big Bang A18 — Pre-flight scan callsites legados](#task-19-big-bang-a18-pre-flight-scan-callsites-legados)
  - [Task 20: Big Bang — Refactor callsites + remove updates EM_PRODUCAO](#task-20-big-bang-refactor-callsites-remove-updates-em_producao)
  - [Task 21: A6 — Guards em `disponibilizar_service` para `CARREGADA`](#task-21-a6-guards-em-disponibilizar_service-para-carregada)
  - [Task 22: A6 — Guards em `montagem_service` para `CARREGADA`](#task-22-a6-guards-em-montagem_service-para-carregada)
  - [Task 23: Migration 25 — Backfill divergências legadas](#task-23-migration-25-backfill-divergências-legadas)
  - [Task 24: Smoke tests Fase 1 — `test_models_constantes`](#task-24-smoke-tests-fase-1-test_models_constantes)
  - [Task 25: Deploy Fase 1 em prod (Render)](#task-25-deploy-fase-1-em-prod-render)
- [Self-review (executor — pre-execucao)](#self-review-executor-pre-execucao)
- [Plano completo](#plano-completo)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar fundação estrutural para o módulo Carregamento + Divergências: 8 migrations (7 DDL estruturais + 1 backfill de status pedido), atualização de constantes em models, criação de 5 modelos Python novos, service `recalcular_status_pedido`, guards em services existentes (`disponibilizar`, `montagem`), Big Bang erradicando status legados (`EM_PRODUCAO`/`SEPARANDO`/`FATURADO_PARCIAL`), e backfill de divergências legadas.

**Architecture:** Migrations idempotentes (.py + .sql) seguindo padrão Migration 17. Sem código novo de Carregamento (reservado para Fase 2). Sem alteração de UI (reservado para Fases 3-4). Foco em fundação estável que não quebra nada existente. Big Bang em PR dedicado com testes regressão.

**Tech Stack:** Flask 2.x, SQLAlchemy 2.x, PostgreSQL 14+, alembic-style migrations.

**Spec referenciada:** `docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md` (v1.2)

**Pré-requisito antes de começar:**
- Migration 17 (`motos_assai_17_cleanup_sep_2_orfa.py`) deve estar aplicada em prod (cleanup Sep 2 órfã)
- Backup do banco de produção (PG dump) feito antes de começar a Fase 1
- Branch dedicada: `git checkout -b feature/motos-assai-fase1-fundacao`

---

## File Structure

### Migrations a criar (em `scripts/migrations/`)

| # | Arquivo .py | Arquivo .sql | O que faz |
|---|---|---|---|
| 18 | `motos_assai_18_carregamento.py` | `motos_assai_18_carregamento.sql` | Cria `assai_carregamento` + `assai_carregamento_item` |
| 19 | `motos_assai_19_divergencia.py` | `motos_assai_19_divergencia.sql` | Cria `assai_divergencia` (8 tipos no CHECK: 4 novos + 4 legados) |
| 20 | `motos_assai_20_pedido_excel.py` | `motos_assai_20_pedido_excel.sql` | Cria `assai_pedido_excel` |
| 21 | `motos_assai_21_simplificar_status_pedido.py` | (sem .sql — apenas backfill Python) | Backfill status pedido via `recalcular_status_pedido` |
| 22 | `motos_assai_22_nf_cancelamento_campos.py` | `motos_assai_22_nf_cancelamento_campos.sql` | Adiciona 3 campos cancelamento em `assai_nf_qpa` |
| 24 | `motos_assai_24_check_status_aceitar_novos.py` | `motos_assai_24_check_status_aceitar_novos.sql` | ALTER CHECK constraints (se existem) |
| 25 | `motos_assai_25_backfill_divergencias_legadas.py` | (sem .sql — backfill Python) | Migra `tipo_divergencia` items → `assai_divergencia` |
| 26 | `motos_assai_26_vinculo_historico.py` | `motos_assai_26_vinculo_historico.sql` | Cria `assai_nf_qpa_item_vinculo_historico` |
| 27 | `motos_assai_27_unique_nf_sep_ativa.py` | `motos_assai_27_unique_nf_sep_ativa.sql` | UNIQUE parcial em `assai_nf_qpa(separacao_id)` WHERE status_match != 'CANCELADA' |

### Models a criar (em `app/motos_assai/models/`)

- `carregamento.py` — `AssaiCarregamento`, `AssaiCarregamentoItem` + constantes `CARREGAMENTO_STATUS_*`
- `divergencia.py` — `AssaiDivergencia` + constantes `DIVERGENCIA_TIPO_*`, `DIVERGENCIA_RESOLUCAO_*`
- `pedido_excel.py` — `AssaiPedidoExcel`
- `nf_qpa_vinculo.py` — `AssaiNfQpaItemVinculoHistorico` + constantes `VINCULO_MOTIVO_*`

### Models a modificar (em `app/motos_assai/models/`)

- `separacao.py` — adicionar `SEPARACAO_STATUS_CARREGADA`
- `nf_qpa.py` — adicionar `NF_STATUS_CANCELADA` + 3 colunas `cancelada_em / cancelada_por_id / motivo_cancelamento`
- `moto.py` — adicionar `EVENTO_CARREGADA` ao set `EVENTOS_VALIDOS` e `EVENTOS_FORA_ESTOQUE`
- `pedido.py` — substituir 6 status por 4: `ABERTO`, `PARCIALMENTE_FATURADO`, `FATURADO`, `CANCELADO`
- `__init__.py` — re-export dos novos models e constantes

### Services a criar/modificar

- **CRIAR** `app/motos_assai/services/pedido_status_service.py` — `recalcular_status_pedido()`
- **MODIFICAR** `app/motos_assai/services/disponibilizar_service.py` — A6 guards para `CARREGADA`
- **MODIFICAR** `app/motos_assai/services/montagem_service.py` — A6 guards para `CARREGADA`
- **CRIAR (declaração apenas)** `app/motos_assai/services/carregamento_service.py` — `CarregamentoExcedenteError` (implementação completa Fase 2)

### Refactor cross-projeto (Big Bang A18)

- Pre-flight scan list em `docs/superpowers/plans/2026-05-12-bigbang-callsites-list.md`
- Refactor TODOS callsites identificados em routes / services / templates / queries

### Tests a criar

- `tests/motos_assai/test_pedido_status_service.py` — testes de `recalcular_status_pedido`
- `tests/motos_assai/test_disponibilizar_service_carregada.py` — A6 guards
- `tests/motos_assai/test_montagem_service_carregada.py` — A6 guards
- `tests/motos_assai/test_models_constantes.py` — smoke test de imports + constantes

---

## Tasks

### Task 1: Pré-requisito — confirmar Migration 17 em prod

**Files:**
- Existing: `scripts/migrations/motos_assai_17_cleanup_sep_2_orfa.py`

- [ ] **Step 1: Verificar Migration 17 em prod**

Conectar no Render Shell e rodar:

```bash
cd /opt/render/project/src
python scripts/migrations/motos_assai_17_cleanup_sep_2_orfa.py
```

Expected output:
```
[skip] AssaiSeparacao 2 ja nao existe — idempotente OK
```

OU (se ainda não foi aplicada):
```
[ok] AssaiSeparacao 2 deletada
```

- [ ] **Step 2: Backup do banco de produção**

```bash
# No Render dashboard, criar manual backup do PostgreSQL
# Ou via CLI:
pg_dump $DATABASE_URL > backup_pre_fase1_$(date +%Y%m%d).sql
```

- [ ] **Step 3: Criar branch local**

```bash
git checkout main
git pull
git checkout -b feature/motos-assai-fase1-fundacao
```

---

### Task 2: Migration 18 — `assai_carregamento` + `assai_carregamento_item`

**Files:**
- Create: `scripts/migrations/motos_assai_18_carregamento.py`
- Create: `scripts/migrations/motos_assai_18_carregamento.sql`

- [ ] **Step 1: Criar `motos_assai_18_carregamento.sql`** (idempotente, para Render Shell)

```sql
-- Migration 18: Cria assai_carregamento + assai_carregamento_item.
-- Decisao: SEM UNIQUE em (pedido, loja, EM_CARREGAMENTO) — A2.
-- Enforcement: lock pessimista em assai_moto via service (S3=c).

BEGIN;

CREATE TABLE IF NOT EXISTS assai_carregamento (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES assai_pedido_venda(id),
    loja_id INTEGER NOT NULL REFERENCES assai_loja(id),
    separacao_id INTEGER REFERENCES assai_separacao(id),
    status VARCHAR(20) NOT NULL DEFAULT 'EM_CARREGAMENTO',
    iniciado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    iniciado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    finalizado_em TIMESTAMP,
    finalizado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    cancelado_em TIMESTAMP,
    cancelado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    motivo_cancelamento TEXT,
    CONSTRAINT ck_assai_carregamento_status
        CHECK (status IN ('EM_CARREGAMENTO', 'FINALIZADO', 'CANCELADO'))
);

CREATE INDEX IF NOT EXISTS ix_assai_carregamento_pedido_loja
    ON assai_carregamento(pedido_id, loja_id);
CREATE INDEX IF NOT EXISTS ix_assai_carregamento_status
    ON assai_carregamento(status);
CREATE INDEX IF NOT EXISTS ix_assai_carregamento_separacao
    ON assai_carregamento(separacao_id) WHERE separacao_id IS NOT NULL;

-- Q2: 1 carregamento FINALIZADO ↔ 1 sep
CREATE UNIQUE INDEX IF NOT EXISTS uq_assai_carregamento_sep
    ON assai_carregamento(separacao_id)
    WHERE separacao_id IS NOT NULL AND status = 'FINALIZADO';

CREATE TABLE IF NOT EXISTS assai_carregamento_item (
    id SERIAL PRIMARY KEY,
    carregamento_id INTEGER NOT NULL REFERENCES assai_carregamento(id) ON DELETE CASCADE,
    chassi VARCHAR(50) NOT NULL,
    modelo_id INTEGER NOT NULL REFERENCES assai_modelo(id),
    escaneado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    escaneado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS ix_assai_carregamento_item_carregamento
    ON assai_carregamento_item(carregamento_id);
CREATE INDEX IF NOT EXISTS ix_assai_carregamento_item_chassi
    ON assai_carregamento_item(chassi);

-- A2: SEM UNIQUE chassi-em-carregamento-ativo. Enforcement via service
-- (lock pessimista em assai_moto). Subquery em indice parcial nao e suportada em PG.

COMMIT;
```

- [ ] **Step 2: Criar `motos_assai_18_carregamento.py`** (Python wrapper para deploy automatico)

```python
"""Migration 18: cria assai_carregamento + assai_carregamento_item.

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md §2.1
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase1-fundacao.md Task 2

Idempotente. Padrao Migration 17.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'motos_assai_18_carregamento.sql')


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH, 'r') as f:
            sql = f.read()

        # Verifica before
        result_before = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name IN ('assai_carregamento', 'assai_carregamento_item')"
        )).scalar()
        print(f'[before] tabelas existentes: {result_before}/2')

        # Executa o SQL
        db.session.execute(text(sql))
        db.session.commit()

        # Verifica after
        result_after = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name IN ('assai_carregamento', 'assai_carregamento_item')"
        )).scalar()
        print(f'[after] tabelas existentes: {result_after}/2')

        if result_after != 2:
            print('[ERROR] migration falhou — verificar logs')
            sys.exit(1)
        print('[ok] Migration 18 aplicada com sucesso')


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Rodar migration local**

```bash
source .venv/bin/activate
python scripts/migrations/motos_assai_18_carregamento.py
```

Expected output:
```
[before] tabelas existentes: 0/2
[after] tabelas existentes: 2/2
[ok] Migration 18 aplicada com sucesso
```

- [ ] **Step 4: Validar tabelas no banco**

```bash
psql $DATABASE_URL -c "\d assai_carregamento" -c "\d assai_carregamento_item"
```

Expected: ambas tabelas com colunas, FKs e índices listados.

- [ ] **Step 5: Commit**

```bash
git add scripts/migrations/motos_assai_18_carregamento.{py,sql}
git commit -m "feat(motos-assai): Migration 18 — assai_carregamento + item

Cria tabelas para o conceito de Carregamento (entidade entre Sep e NF).
Sem UNIQUE em (pedido, loja, EM_CARREGAMENTO) — A2 permite N caminhoes
paralelos. Enforcement de chassi unico via lock pessimista em service."
```

---

### Task 3: Migration 19 — `assai_divergencia`

**Files:**
- Create: `scripts/migrations/motos_assai_19_divergencia.py`
- Create: `scripts/migrations/motos_assai_19_divergencia.sql`

- [ ] **Step 1: Criar `motos_assai_19_divergencia.sql`**

```sql
-- Migration 19: Cria assai_divergencia (centraliza todas divergencias).
-- 8 tipos no CHECK: 4 novos (Carregamento×NF + cross-loja) + 4 legados de _calcular_match
-- (LOJA_DIVERGENTE, VALOR_DIVERGENTE, MODELO_DIVERGENTE, CHASSI_SEM_SEPARACAO).
-- 5 tipos de resolucao.

BEGIN;

CREATE TABLE IF NOT EXISTS assai_divergencia (
    id SERIAL PRIMARY KEY,
    tipo VARCHAR(40) NOT NULL,
    chassi VARCHAR(50),
    separacao_id INTEGER REFERENCES assai_separacao(id),
    carregamento_id INTEGER REFERENCES assai_carregamento(id),
    nf_id INTEGER REFERENCES assai_nf_qpa(id),
    detalhes JSONB DEFAULT '{}'::jsonb,
    criada_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    resolvida_em TIMESTAMP,
    resolvida_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    tipo_resolucao VARCHAR(40),
    observacao_resolucao TEXT,
    CONSTRAINT ck_assai_divergencia_tipo
        CHECK (tipo IN (
            'NF_CHASSI_FORA_CARREGAMENTO',
            'CARREGAMENTO_CHASSI_FORA_NF',
            'CHASSI_NAO_CADASTRADO',
            'CHASSI_OUTRA_LOJA',
            'LOJA_DIVERGENTE',
            'VALOR_DIVERGENTE',
            'MODELO_DIVERGENTE',
            'CHASSI_SEM_SEPARACAO'
        )),
    CONSTRAINT ck_assai_divergencia_resolucao
        CHECK (tipo_resolucao IS NULL OR tipo_resolucao IN (
            'CANCELAR_NF', 'CCE', 'ALTERAR_CARREGAMENTO',
            'SUBSTITUIR_CHASSI', 'IGNORAR'
        ))
);

CREATE INDEX IF NOT EXISTS ix_assai_divergencia_chassi
    ON assai_divergencia(chassi);
CREATE INDEX IF NOT EXISTS ix_assai_divergencia_pendentes
    ON assai_divergencia(criada_em DESC) WHERE resolvida_em IS NULL;
CREATE INDEX IF NOT EXISTS ix_assai_divergencia_sep
    ON assai_divergencia(separacao_id) WHERE separacao_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS ix_assai_divergencia_nf
    ON assai_divergencia(nf_id) WHERE nf_id IS NOT NULL;

COMMIT;
```

- [ ] **Step 2: Criar `motos_assai_19_divergencia.py`**

Mesmo padrão da Task 2 Step 2, ajustando:
- `SQL_PATH` para `motos_assai_19_divergencia.sql`
- Verificação `WHERE table_name = 'assai_divergencia'` (1/1)
- Print messages com identificador "Migration 19"

```python
"""Migration 19: cria assai_divergencia.

Spec: §2.1, §7.1
Plano: Task 3
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'motos_assai_19_divergencia.sql')


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH, 'r') as f:
            sql = f.read()

        result_before = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'assai_divergencia'"
        )).scalar()
        print(f'[before] assai_divergencia existe: {result_before}/1')

        db.session.execute(text(sql))
        db.session.commit()

        result_after = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'assai_divergencia'"
        )).scalar()
        print(f'[after] assai_divergencia existe: {result_after}/1')

        if result_after != 1:
            print('[ERROR] migration falhou')
            sys.exit(1)
        print('[ok] Migration 19 aplicada com sucesso')


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Rodar local + validar + commit**

```bash
python scripts/migrations/motos_assai_19_divergencia.py
psql $DATABASE_URL -c "\d assai_divergencia"
git add scripts/migrations/motos_assai_19_divergencia.{py,sql}
git commit -m "feat(motos-assai): Migration 19 — assai_divergencia (8 tipos centralizados: 4 novos + 4 legados)"
```

---

### Task 4: Migration 20 — `assai_pedido_excel`

**Files:**
- Create: `scripts/migrations/motos_assai_20_pedido_excel.py`
- Create: `scripts/migrations/motos_assai_20_pedido_excel.sql`

- [ ] **Step 1: Criar `motos_assai_20_pedido_excel.sql`**

```sql
-- Migration 20: Cria assai_pedido_excel (historico versionado de Excel).
-- UNIQUE (separacao_id, versao) — S13=a — proteger race em versao.
-- UNIQUE parcial (separacao_id) WHERE ativo=TRUE — apenas 1 ativo por sep.

BEGIN;

CREATE TABLE IF NOT EXISTS assai_pedido_excel (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES assai_pedido_venda(id),
    separacao_id INTEGER NOT NULL REFERENCES assai_separacao(id),
    s3_key VARCHAR(500) NOT NULL,
    versao INTEGER NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    gerado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    gerado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    motivo_regeneracao TEXT
);

CREATE INDEX IF NOT EXISTS ix_assai_pedido_excel_pedido
    ON assai_pedido_excel(pedido_id);
CREATE INDEX IF NOT EXISTS ix_assai_pedido_excel_sep
    ON assai_pedido_excel(separacao_id);

CREATE UNIQUE INDEX IF NOT EXISTS uq_assai_pedido_excel_sep_ativo
    ON assai_pedido_excel(separacao_id) WHERE ativo = TRUE;

CREATE UNIQUE INDEX IF NOT EXISTS uq_assai_pedido_excel_sep_versao
    ON assai_pedido_excel(separacao_id, versao);

-- Backfill: copiar valor existente de assai_separacao.solicitacao_excel_s3_key
-- para novas linhas com versao=1, ativo=TRUE.
INSERT INTO assai_pedido_excel (pedido_id, separacao_id, s3_key, versao, ativo, motivo_regeneracao)
SELECT
    s.pedido_id,
    s.id,
    s.solicitacao_excel_s3_key,
    1,
    TRUE,
    'Backfill Migration 20 (legado solicitacao_excel_s3_key)'
FROM assai_separacao s
WHERE s.solicitacao_excel_s3_key IS NOT NULL
  AND NOT EXISTS (
    SELECT 1 FROM assai_pedido_excel pe WHERE pe.separacao_id = s.id
  );

COMMIT;
```

- [ ] **Step 2: Criar `motos_assai_20_pedido_excel.py`**

```python
"""Migration 20: cria assai_pedido_excel + backfill de solicitacao_excel_s3_key.

Spec: §2.1, §12
Plano: Task 4
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'motos_assai_20_pedido_excel.sql')


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH, 'r') as f:
            sql = f.read()

        result_before = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'assai_pedido_excel'"
        )).scalar()
        print(f'[before] assai_pedido_excel existe: {result_before}/1')

        db.session.execute(text(sql))
        db.session.commit()

        # M2 fix: validar que tabela foi criada
        result_after = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'assai_pedido_excel'"
        )).scalar()
        if result_after != 1:
            print('[ERROR] Migration 20 nao criou a tabela')
            sys.exit(1)

        backfill_count = db.session.execute(text(
            "SELECT COUNT(*) FROM assai_pedido_excel WHERE motivo_regeneracao LIKE 'Backfill Migration 20%'"
        )).scalar()
        print(f'[after] tabela criada + {backfill_count} linhas de backfill')
        print('[ok] Migration 20 aplicada com sucesso')


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Rodar local + validar + commit**

```bash
python scripts/migrations/motos_assai_20_pedido_excel.py
psql $DATABASE_URL -c "\d assai_pedido_excel" -c "SELECT COUNT(*) FROM assai_pedido_excel;"
git add scripts/migrations/motos_assai_20_pedido_excel.{py,sql}
git commit -m "feat(motos-assai): Migration 20 — assai_pedido_excel versionado + backfill"
```

---

### Task 5: Migration 22 — Campos de cancelamento em `assai_nf_qpa`

**Files:**
- Create: `scripts/migrations/motos_assai_22_nf_cancelamento_campos.py`
- Create: `scripts/migrations/motos_assai_22_nf_cancelamento_campos.sql`

- [ ] **Step 1: Criar `motos_assai_22_nf_cancelamento_campos.sql`**

```sql
-- Migration 22: 3 colunas de auditoria de cancelamento de NF.
-- D3 + R5 + S15.

BEGIN;

ALTER TABLE assai_nf_qpa
    ADD COLUMN IF NOT EXISTS cancelada_em TIMESTAMP,
    ADD COLUMN IF NOT EXISTS cancelada_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    ADD COLUMN IF NOT EXISTS motivo_cancelamento TEXT;

CREATE INDEX IF NOT EXISTS ix_assai_nf_qpa_cancelada
    ON assai_nf_qpa(cancelada_em DESC) WHERE cancelada_em IS NOT NULL;

COMMIT;
```

- [ ] **Step 2: Criar `motos_assai_22_nf_cancelamento_campos.py`**

```python
"""Migration 22: adiciona 3 colunas de cancelamento em assai_nf_qpa.

Spec: §9.4
Plano: Task 5
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'motos_assai_22_nf_cancelamento_campos.sql')


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH, 'r') as f:
            sql = f.read()

        result_before = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name = 'assai_nf_qpa' "
            "AND column_name IN ('cancelada_em', 'cancelada_por_id', 'motivo_cancelamento')"
        )).scalar()
        print(f'[before] colunas existentes: {result_before}/3')

        db.session.execute(text(sql))
        db.session.commit()

        result_after = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.columns "
            "WHERE table_name = 'assai_nf_qpa' "
            "AND column_name IN ('cancelada_em', 'cancelada_por_id', 'motivo_cancelamento')"
        )).scalar()
        print(f'[after] colunas existentes: {result_after}/3')

        if result_after != 3:
            sys.exit(1)
        print('[ok] Migration 22 aplicada com sucesso')


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Rodar + validar + commit**

```bash
python scripts/migrations/motos_assai_22_nf_cancelamento_campos.py
psql $DATABASE_URL -c "\d assai_nf_qpa" | grep cancelada
git add scripts/migrations/motos_assai_22_nf_cancelamento_campos.{py,sql}
git commit -m "feat(motos-assai): Migration 22 — campos cancelamento em assai_nf_qpa"
```

---

### Task 6: Migration 24 — CHECK constraints aceitar novos status

**Files:**
- Create: `scripts/migrations/motos_assai_24_check_status_aceitar_novos.py`
- Create: `scripts/migrations/motos_assai_24_check_status_aceitar_novos.sql`

- [ ] **Step 1: Verificar se existem CHECK constraints atuais**

```bash
psql $DATABASE_URL -c "
SELECT con.conname, pg_get_constraintdef(con.oid)
FROM pg_constraint con
JOIN pg_class rel ON rel.oid = con.conrelid
WHERE rel.relname IN ('assai_separacao', 'assai_nf_qpa', 'assai_moto_evento', 'assai_pedido_venda')
  AND con.contype = 'c'
  AND pg_get_constraintdef(con.oid) LIKE '%status%';
"
```

Documentar o resultado. Se NÃO houver CHECK constraints (esperado), Migration 24 vira no-op documentado.

- [ ] **Step 2: Criar `motos_assai_24_check_status_aceitar_novos.sql`** (idempotente)

```sql
-- Migration 24: ALTER CHECK constraints para aceitar novos valores de status.
-- Padrao: DROP IF EXISTS antiga + ADD CHECK nova.
-- Se nao houver CHECK constraint, e no-op (idempotente).

BEGIN;

-- assai_separacao.status — adicionar CARREGADA
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_assai_separacao_status') THEN
        ALTER TABLE assai_separacao DROP CONSTRAINT ck_assai_separacao_status;
    END IF;
    ALTER TABLE assai_separacao
        ADD CONSTRAINT ck_assai_separacao_status
        CHECK (status IN ('EM_SEPARACAO', 'FECHADA', 'CARREGADA', 'FATURADA', 'CANCELADA'));
END $$;

-- assai_nf_qpa.status_match — adicionar CANCELADA
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_assai_nf_qpa_status_match') THEN
        ALTER TABLE assai_nf_qpa DROP CONSTRAINT ck_assai_nf_qpa_status_match;
    END IF;
    ALTER TABLE assai_nf_qpa
        ADD CONSTRAINT ck_assai_nf_qpa_status_match
        CHECK (status_match IN ('BATEU', 'DIVERGENTE', 'NAO_RECONCILIADO', 'CANCELADA'));
END $$;

-- assai_moto_evento.tipo — adicionar CARREGADA
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_assai_moto_evento_tipo') THEN
        ALTER TABLE assai_moto_evento DROP CONSTRAINT ck_assai_moto_evento_tipo;
    END IF;
    ALTER TABLE assai_moto_evento
        ADD CONSTRAINT ck_assai_moto_evento_tipo
        CHECK (tipo IN (
            'ESTOQUE', 'MONTADA', 'PENDENTE', 'PENDENCIA_RESOLVIDA',
            'DISPONIVEL', 'REVERTIDA_PARA_MONTADA',
            'SEPARADA', 'CARREGADA', 'FATURADA', 'CANCELADA', 'MOTO_FALTANDO'
        ));
END $$;

-- assai_pedido_venda.status — simplificar para 4 status
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'ck_assai_pedido_venda_status') THEN
        ALTER TABLE assai_pedido_venda DROP CONSTRAINT ck_assai_pedido_venda_status;
    END IF;
    ALTER TABLE assai_pedido_venda
        ADD CONSTRAINT ck_assai_pedido_venda_status
        CHECK (status IN ('ABERTO', 'PARCIALMENTE_FATURADO', 'FATURADO', 'CANCELADO'));
END $$;

COMMIT;
```

**ATENÇÃO**: o último CHECK em `assai_pedido_venda.status` quebrará se houver pedidos com status legado (`EM_PRODUCAO`, `SEPARANDO`, `FATURADO_PARCIAL`). Migration 21 (Task 15) faz o backfill ANTES de Migration 24 rodar. **Ordem crítica**.

- [ ] **Step 3: Criar `motos_assai_24_check_status_aceitar_novos.py`**

```python
"""Migration 24: ALTER CHECK constraints para aceitar novos status.

ATENCAO: rodar APOS Migration 21 (backfill status pedido) — caso contrario,
pedidos com status legado violarao o novo CHECK.

Spec: §2.2 ("Sem mudança de schema do enum" — assumi VARCHAR sem CHECK,
mas Migration 24 cobre caso CHECK exista).
Plano: Task 6
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'motos_assai_24_check_status_aceitar_novos.sql')


def main():
    app = create_app()
    with app.app_context():
        # Validacao: verificar que nao ha pedidos com status legado antes de aplicar
        legados = db.session.execute(text(
            "SELECT COUNT(*) FROM assai_pedido_venda "
            "WHERE status IN ('EM_PRODUCAO', 'SEPARANDO', 'FATURADO_PARCIAL')"
        )).scalar()
        if legados > 0:
            print(f'[ABORT] {legados} pedidos com status legado. Rodar Migration 21 antes.')
            sys.exit(1)

        with open(SQL_PATH, 'r') as f:
            sql = f.read()

        db.session.execute(text(sql))
        db.session.commit()

        print('[ok] Migration 24 aplicada (CHECK constraints atualizados)')


if __name__ == '__main__':
    main()
```

- [ ] **Step 4: NÃO rodar local ainda** (depende de Migration 21 — Task 15)

Apenas commit.

- [ ] **Step 5: Commit**

```bash
git add scripts/migrations/motos_assai_24_check_status_aceitar_novos.{py,sql}
git commit -m "feat(motos-assai): Migration 24 — CHECK constraints aceitar novos status

ATENCAO: depende de Migration 21 (backfill status pedido). Rodar 21 antes."
```

---

### Task 7: Migration 26 — `assai_nf_qpa_item_vinculo_historico`

**Files:**
- Create: `scripts/migrations/motos_assai_26_vinculo_historico.py`
- Create: `scripts/migrations/motos_assai_26_vinculo_historico.sql`

- [ ] **Step 1: Criar `motos_assai_26_vinculo_historico.sql`**

```sql
-- Migration 26: assai_nf_qpa_item_vinculo_historico.
-- S16=c — auditoria de vinculo NF-item ↔ Sep-item antes de cancelamento.

BEGIN;

CREATE TABLE IF NOT EXISTS assai_nf_qpa_item_vinculo_historico (
    id SERIAL PRIMARY KEY,
    nf_qpa_item_id INTEGER NOT NULL REFERENCES assai_nf_qpa_item(id),
    separacao_item_id INTEGER REFERENCES assai_separacao_item(id) ON DELETE SET NULL,
    motivo VARCHAR(40) NOT NULL,
    chassi_no_momento VARCHAR(50) NOT NULL,
    registrado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    registrado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    detalhes JSONB DEFAULT '{}'::jsonb,
    CONSTRAINT ck_assai_nf_qpa_item_vinculo_motivo
        CHECK (motivo IN ('NF_CANCELADA', 'CCE_ALTEROU_CHASSI', 'SUBSTITUICAO_CROSS_LOJA'))
);

CREATE INDEX IF NOT EXISTS ix_assai_nf_qpa_item_vinculo_hist_nf
    ON assai_nf_qpa_item_vinculo_historico(nf_qpa_item_id);
CREATE INDEX IF NOT EXISTS ix_assai_nf_qpa_item_vinculo_hist_sep
    ON assai_nf_qpa_item_vinculo_historico(separacao_item_id) WHERE separacao_item_id IS NOT NULL;

COMMIT;
```

- [ ] **Step 2: Criar `motos_assai_26_vinculo_historico.py`**

Mesmo template das anteriores, ajustando paths e mensagens. Verifica que tabela existe após.

```python
"""Migration 26: cria assai_nf_qpa_item_vinculo_historico.

Spec: §2.1
Plano: Task 7
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'motos_assai_26_vinculo_historico.sql')


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH, 'r') as f:
            sql = f.read()

        result_before = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'assai_nf_qpa_item_vinculo_historico'"
        )).scalar()
        print(f'[before] tabela existe: {result_before}/1')

        db.session.execute(text(sql))
        db.session.commit()

        result_after = db.session.execute(text(
            "SELECT COUNT(*) FROM information_schema.tables "
            "WHERE table_name = 'assai_nf_qpa_item_vinculo_historico'"
        )).scalar()
        print(f'[after] tabela existe: {result_after}/1')

        if result_after != 1:
            sys.exit(1)
        print('[ok] Migration 26 aplicada com sucesso')


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Rodar + validar + commit**

```bash
python scripts/migrations/motos_assai_26_vinculo_historico.py
psql $DATABASE_URL -c "\d assai_nf_qpa_item_vinculo_historico"
git add scripts/migrations/motos_assai_26_vinculo_historico.{py,sql}
git commit -m "feat(motos-assai): Migration 26 — assai_nf_qpa_item_vinculo_historico (S16=c)"
```

---

### Task 8: Migration 27 — UNIQUE parcial NF ativa por sep

**Files:**
- Create: `scripts/migrations/motos_assai_27_unique_nf_sep_ativa.py`
- Create: `scripts/migrations/motos_assai_27_unique_nf_sep_ativa.sql`

- [ ] **Step 1: Criar `motos_assai_27_unique_nf_sep_ativa.sql`**

```sql
-- Migration 27: UNIQUE parcial em assai_nf_qpa(separacao_id) WHERE status_match != 'CANCELADA'.
-- A3 — garante apenas 1 NF ativa por sep.
-- Cenario: Sep nasce FATURADA com NF A; NF A cancelada; NF B chega para a mesma sep.

BEGIN;

-- Validacao: verificar que nao ha violacoes ANTES de aplicar
DO $$
DECLARE
    violacoes INTEGER;
BEGIN
    SELECT COUNT(*) INTO violacoes FROM (
        SELECT separacao_id, COUNT(*) AS qty
        FROM assai_nf_qpa
        WHERE separacao_id IS NOT NULL
          AND status_match != 'CANCELADA'
        GROUP BY separacao_id
        HAVING COUNT(*) > 1
    ) sub;

    IF violacoes > 0 THEN
        RAISE EXCEPTION 'Violacao: % seps com >1 NF ativa. Resolver antes de aplicar UNIQUE.', violacoes;
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_assai_nf_qpa_separacao_ativa
    ON assai_nf_qpa(separacao_id)
    WHERE separacao_id IS NOT NULL AND status_match != 'CANCELADA';

COMMIT;
```

- [ ] **Step 2: Criar `motos_assai_27_unique_nf_sep_ativa.py`**

```python
"""Migration 27: UNIQUE parcial em assai_nf_qpa(separacao_id) WHERE status_match != 'CANCELADA'.

Spec: §2.2 (A3)
Plano: Task 8
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'motos_assai_27_unique_nf_sep_ativa.sql')


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH, 'r') as f:
            sql = f.read()

        # Pre-check
        violacoes = db.session.execute(text(
            "SELECT COUNT(*) FROM (SELECT separacao_id FROM assai_nf_qpa "
            "WHERE separacao_id IS NOT NULL AND status_match != 'CANCELADA' "
            "GROUP BY separacao_id HAVING COUNT(*) > 1) sub"
        )).scalar()
        if violacoes > 0:
            print(f'[ABORT] {violacoes} seps com >1 NF ativa. Resolver antes.')
            sys.exit(1)

        db.session.execute(text(sql))
        db.session.commit()
        print('[ok] Migration 27 aplicada com sucesso')


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Rodar + validar + commit**

```bash
python scripts/migrations/motos_assai_27_unique_nf_sep_ativa.py
psql $DATABASE_URL -c "\d assai_nf_qpa" | grep uq_assai_nf_qpa
git add scripts/migrations/motos_assai_27_unique_nf_sep_ativa.{py,sql}
git commit -m "feat(motos-assai): Migration 27 — UNIQUE parcial NF ativa por sep (A3)"
```

---

### Task 9: Criar models Python — `AssaiCarregamento` + `AssaiCarregamentoItem`

**Files:**
- Create: `app/motos_assai/models/carregamento.py`
- Modify: `app/motos_assai/models/__init__.py`

- [ ] **Step 1: Criar `app/motos_assai/models/carregamento.py`**

```python
"""AssaiCarregamento — entidade entre Sep e NF (carga real).

Spec: docs/superpowers/specs/2026-05-12-motos-assai-carregamento-divergencia-design.md §2.1
Plano: docs/superpowers/plans/2026-05-12-motos-assai-fase1-fundacao.md Task 9
"""
from app import db
from app.utils.timezone import agora_brasil_naive


CARREGAMENTO_STATUS_EM_CARREGAMENTO = 'EM_CARREGAMENTO'
CARREGAMENTO_STATUS_FINALIZADO = 'FINALIZADO'
CARREGAMENTO_STATUS_CANCELADO = 'CANCELADO'

CARREGAMENTO_STATUS_VALIDOS = {
    CARREGAMENTO_STATUS_EM_CARREGAMENTO,
    CARREGAMENTO_STATUS_FINALIZADO,
    CARREGAMENTO_STATUS_CANCELADO,
}


class AssaiCarregamento(db.Model):
    __tablename__ = 'assai_carregamento'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('assai_pedido_venda.id'), nullable=False, index=True)
    loja_id = db.Column(db.Integer, db.ForeignKey('assai_loja.id'), nullable=False, index=True)
    separacao_id = db.Column(db.Integer, db.ForeignKey('assai_separacao.id'), index=True)
    status = db.Column(db.String(20), nullable=False, default=CARREGAMENTO_STATUS_EM_CARREGAMENTO, index=True)
    iniciado_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)
    iniciado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    finalizado_em = db.Column(db.DateTime)
    finalizado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    cancelado_em = db.Column(db.DateTime)
    cancelado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    motivo_cancelamento = db.Column(db.Text)

    pedido = db.relationship('AssaiPedidoVenda', backref='carregamentos')
    loja = db.relationship('AssaiLoja')
    separacao = db.relationship('AssaiSeparacao', backref='carregamento_finalizado', uselist=False)
    itens = db.relationship('AssaiCarregamentoItem', backref='carregamento', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<AssaiCarregamento #{self.id} pedido={self.pedido_id} loja={self.loja_id} status={self.status}>'


class AssaiCarregamentoItem(db.Model):
    __tablename__ = 'assai_carregamento_item'

    id = db.Column(db.Integer, primary_key=True)
    carregamento_id = db.Column(db.Integer, db.ForeignKey('assai_carregamento.id', ondelete='CASCADE'),
                                nullable=False, index=True)
    chassi = db.Column(db.String(50), nullable=False, index=True)
    modelo_id = db.Column(db.Integer, db.ForeignKey('assai_modelo.id'), nullable=False)
    escaneado_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)
    escaneado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))

    modelo = db.relationship('AssaiModelo')

    def __repr__(self):
        return f'<AssaiCarregamentoItem #{self.id} chassi={self.chassi}>'
```

- [ ] **Step 2: Atualizar `app/motos_assai/models/__init__.py` — adicionar imports**

Localizar a seção de re-exports e adicionar:

```python
from app.motos_assai.models.carregamento import (
    AssaiCarregamento,
    AssaiCarregamentoItem,
    CARREGAMENTO_STATUS_EM_CARREGAMENTO,
    CARREGAMENTO_STATUS_FINALIZADO,
    CARREGAMENTO_STATUS_CANCELADO,
    CARREGAMENTO_STATUS_VALIDOS,
)
```

E adicionar ao `__all__` se houver:

```python
__all__ = [
    # ... existentes ...
    'AssaiCarregamento',
    'AssaiCarregamentoItem',
    'CARREGAMENTO_STATUS_EM_CARREGAMENTO',
    'CARREGAMENTO_STATUS_FINALIZADO',
    'CARREGAMENTO_STATUS_CANCELADO',
    'CARREGAMENTO_STATUS_VALIDOS',
]
```

- [ ] **Step 3: Smoke test do import**

```bash
source .venv/bin/activate
python -c "
from app import create_app
app = create_app()
with app.app_context():
    from app.motos_assai.models import AssaiCarregamento, AssaiCarregamentoItem
    print('Imports OK')
    print('Tabela:', AssaiCarregamento.__tablename__)
"
```

Expected: `Imports OK\nTabela: assai_carregamento`

- [ ] **Step 4: Commit**

```bash
git add app/motos_assai/models/carregamento.py app/motos_assai/models/__init__.py
git commit -m "feat(motos-assai): models AssaiCarregamento + AssaiCarregamentoItem"
```

---

### Task 10: Criar model — `AssaiDivergencia`

**Files:**
- Create: `app/motos_assai/models/divergencia.py`
- Modify: `app/motos_assai/models/__init__.py`

- [ ] **Step 1: Criar `app/motos_assai/models/divergencia.py`**

```python
"""AssaiDivergencia — sistema centralizado de divergencias.

Spec: §2.1, §7
Plano: Task 10

8 tipos de divergencia (4 novos + 4 legados) + 5 tipos de resolucao.
"""
from app import db
from app.utils.timezone import agora_brasil_naive


# Tipos novos (Carregamento × NF + cross-loja)
DIVERGENCIA_TIPO_NF_CHASSI_FORA_CARREGAMENTO = 'NF_CHASSI_FORA_CARREGAMENTO'
DIVERGENCIA_TIPO_CARREGAMENTO_CHASSI_FORA_NF = 'CARREGAMENTO_CHASSI_FORA_NF'
DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO = 'CHASSI_NAO_CADASTRADO'
DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA = 'CHASSI_OUTRA_LOJA'

# Tipos legados de _calcular_match (S8=a centralizar)
DIVERGENCIA_TIPO_LOJA_DIVERGENTE = 'LOJA_DIVERGENTE'
DIVERGENCIA_TIPO_VALOR_DIVERGENTE = 'VALOR_DIVERGENTE'
DIVERGENCIA_TIPO_MODELO_DIVERGENTE = 'MODELO_DIVERGENTE'
DIVERGENCIA_TIPO_CHASSI_SEM_SEPARACAO = 'CHASSI_SEM_SEPARACAO'

DIVERGENCIA_TIPOS_VALIDOS = {
    DIVERGENCIA_TIPO_NF_CHASSI_FORA_CARREGAMENTO,
    DIVERGENCIA_TIPO_CARREGAMENTO_CHASSI_FORA_NF,
    DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO,
    DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA,
    DIVERGENCIA_TIPO_LOJA_DIVERGENTE,
    DIVERGENCIA_TIPO_VALOR_DIVERGENTE,
    DIVERGENCIA_TIPO_MODELO_DIVERGENTE,
    DIVERGENCIA_TIPO_CHASSI_SEM_SEPARACAO,
}

# Tipos de resolucao
DIVERGENCIA_RESOLUCAO_CANCELAR_NF = 'CANCELAR_NF'
DIVERGENCIA_RESOLUCAO_CCE = 'CCE'
DIVERGENCIA_RESOLUCAO_ALTERAR_CARREGAMENTO = 'ALTERAR_CARREGAMENTO'
DIVERGENCIA_RESOLUCAO_SUBSTITUIR_CHASSI = 'SUBSTITUIR_CHASSI'
DIVERGENCIA_RESOLUCAO_IGNORAR = 'IGNORAR'

DIVERGENCIA_RESOLUCAO_VALIDAS = {
    DIVERGENCIA_RESOLUCAO_CANCELAR_NF,
    DIVERGENCIA_RESOLUCAO_CCE,
    DIVERGENCIA_RESOLUCAO_ALTERAR_CARREGAMENTO,
    DIVERGENCIA_RESOLUCAO_SUBSTITUIR_CHASSI,
    DIVERGENCIA_RESOLUCAO_IGNORAR,
}


class AssaiDivergencia(db.Model):
    __tablename__ = 'assai_divergencia'

    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(40), nullable=False)
    chassi = db.Column(db.String(50), index=True)
    separacao_id = db.Column(db.Integer, db.ForeignKey('assai_separacao.id'), index=True)
    carregamento_id = db.Column(db.Integer, db.ForeignKey('assai_carregamento.id'))
    nf_id = db.Column(db.Integer, db.ForeignKey('assai_nf_qpa.id'), index=True)
    detalhes = db.Column(db.JSON, default=dict)
    criada_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)
    resolvida_em = db.Column(db.DateTime)
    resolvida_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    tipo_resolucao = db.Column(db.String(40))
    observacao_resolucao = db.Column(db.Text)

    separacao = db.relationship('AssaiSeparacao')
    carregamento = db.relationship('AssaiCarregamento')
    nf = db.relationship('AssaiNfQpa')

    def __repr__(self):
        status = 'resolvida' if self.resolvida_em else 'pendente'
        return f'<AssaiDivergencia #{self.id} tipo={self.tipo} chassi={self.chassi} {status}>'
```

- [ ] **Step 2: Atualizar `app/motos_assai/models/__init__.py`**

Adicionar imports:

```python
from app.motos_assai.models.divergencia import (
    AssaiDivergencia,
    DIVERGENCIA_TIPO_NF_CHASSI_FORA_CARREGAMENTO,
    DIVERGENCIA_TIPO_CARREGAMENTO_CHASSI_FORA_NF,
    DIVERGENCIA_TIPO_CHASSI_NAO_CADASTRADO,
    DIVERGENCIA_TIPO_CHASSI_OUTRA_LOJA,
    DIVERGENCIA_TIPO_LOJA_DIVERGENTE,
    DIVERGENCIA_TIPO_VALOR_DIVERGENTE,
    DIVERGENCIA_TIPO_MODELO_DIVERGENTE,
    DIVERGENCIA_TIPO_CHASSI_SEM_SEPARACAO,
    DIVERGENCIA_TIPOS_VALIDOS,
    DIVERGENCIA_RESOLUCAO_CANCELAR_NF,
    DIVERGENCIA_RESOLUCAO_CCE,
    DIVERGENCIA_RESOLUCAO_ALTERAR_CARREGAMENTO,
    DIVERGENCIA_RESOLUCAO_SUBSTITUIR_CHASSI,
    DIVERGENCIA_RESOLUCAO_IGNORAR,
    DIVERGENCIA_RESOLUCAO_VALIDAS,
)
```

- [ ] **Step 3: Smoke test**

```bash
python -c "
from app import create_app
app = create_app()
with app.app_context():
    from app.motos_assai.models import AssaiDivergencia, DIVERGENCIA_TIPOS_VALIDOS
    print('Tipos validos:', len(DIVERGENCIA_TIPOS_VALIDOS), '=', sorted(DIVERGENCIA_TIPOS_VALIDOS))
"
```

Expected: 8 tipos listados.

- [ ] **Step 4: Commit**

```bash
git add app/motos_assai/models/divergencia.py app/motos_assai/models/__init__.py
git commit -m "feat(motos-assai): model AssaiDivergencia (8 tipos centralizados, 5 resolucoes)"
```

---

### Task 11: Criar model — `AssaiPedidoExcel`

**Files:**
- Create: `app/motos_assai/models/pedido_excel.py`
- Modify: `app/motos_assai/models/__init__.py`

- [ ] **Step 1: Criar `app/motos_assai/models/pedido_excel.py`**

```python
"""AssaiPedidoExcel — historico versionado de Excel Q.P.A. por sep.

Spec: §2.1, §12
Plano: Task 11
"""
from app import db
from app.utils.timezone import agora_brasil_naive


class AssaiPedidoExcel(db.Model):
    __tablename__ = 'assai_pedido_excel'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('assai_pedido_venda.id'), nullable=False, index=True)
    separacao_id = db.Column(db.Integer, db.ForeignKey('assai_separacao.id'), nullable=False, index=True)
    s3_key = db.Column(db.String(500), nullable=False)
    versao = db.Column(db.Integer, nullable=False)
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    gerado_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)
    gerado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    motivo_regeneracao = db.Column(db.Text)

    pedido = db.relationship('AssaiPedidoVenda', backref='excels_historico')
    separacao = db.relationship('AssaiSeparacao')

    def __repr__(self):
        flag = '*' if self.ativo else ' '
        return f'<AssaiPedidoExcel #{self.id} sep={self.separacao_id} v{self.versao}{flag}>'
```

- [ ] **Step 2: Atualizar `__init__.py`**

```python
from app.motos_assai.models.pedido_excel import AssaiPedidoExcel
```

- [ ] **Step 3: Smoke test + Commit**

```bash
python -c "from app import create_app; app=create_app(); ctx=app.app_context(); ctx.push(); from app.motos_assai.models import AssaiPedidoExcel; print('OK')"
git add app/motos_assai/models/pedido_excel.py app/motos_assai/models/__init__.py
git commit -m "feat(motos-assai): model AssaiPedidoExcel (historico versionado)"
```

---

### Task 12: Criar model — `AssaiNfQpaItemVinculoHistorico`

**Files:**
- Create: `app/motos_assai/models/nf_qpa_vinculo.py`
- Modify: `app/motos_assai/models/__init__.py`

- [ ] **Step 1: Criar `app/motos_assai/models/nf_qpa_vinculo.py`**

```python
"""AssaiNfQpaItemVinculoHistorico — auditoria de vinculo NF-item ↔ Sep-item.

Spec: §2.1 (S16=c)
Plano: Task 12
"""
from app import db
from app.utils.timezone import agora_brasil_naive


VINCULO_MOTIVO_NF_CANCELADA = 'NF_CANCELADA'
VINCULO_MOTIVO_CCE_ALTEROU_CHASSI = 'CCE_ALTEROU_CHASSI'
VINCULO_MOTIVO_SUBSTITUICAO_CROSS_LOJA = 'SUBSTITUICAO_CROSS_LOJA'

VINCULO_MOTIVOS_VALIDOS = {
    VINCULO_MOTIVO_NF_CANCELADA,
    VINCULO_MOTIVO_CCE_ALTEROU_CHASSI,
    VINCULO_MOTIVO_SUBSTITUICAO_CROSS_LOJA,
}


class AssaiNfQpaItemVinculoHistorico(db.Model):
    __tablename__ = 'assai_nf_qpa_item_vinculo_historico'

    id = db.Column(db.Integer, primary_key=True)
    nf_qpa_item_id = db.Column(db.Integer, db.ForeignKey('assai_nf_qpa_item.id'), nullable=False, index=True)
    separacao_item_id = db.Column(db.Integer, db.ForeignKey('assai_separacao_item.id', ondelete='SET NULL'))
    motivo = db.Column(db.String(40), nullable=False)
    chassi_no_momento = db.Column(db.String(50), nullable=False)
    registrado_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)
    registrado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    # N-H2 fix: JSONB
    from sqlalchemy.dialects.postgresql import JSONB
    detalhes = db.Column(JSONB, default=dict)

    nf_qpa_item = db.relationship('AssaiNfQpaItem')
    separacao_item = db.relationship('AssaiSeparacaoItem')

    def __repr__(self):
        return f'<AssaiNfQpaItemVinculoHistorico #{self.id} motivo={self.motivo} chassi={self.chassi_no_momento}>'
```

- [ ] **Step 2: Atualizar `__init__.py`**

```python
from app.motos_assai.models.nf_qpa_vinculo import (
    AssaiNfQpaItemVinculoHistorico,
    VINCULO_MOTIVO_NF_CANCELADA,
    VINCULO_MOTIVO_CCE_ALTEROU_CHASSI,
    VINCULO_MOTIVO_SUBSTITUICAO_CROSS_LOJA,
    VINCULO_MOTIVOS_VALIDOS,
)
```

- [ ] **Step 3: Smoke test + Commit**

```bash
python -c "from app import create_app; app=create_app(); ctx=app.app_context(); ctx.push(); from app.motos_assai.models import AssaiNfQpaItemVinculoHistorico; print('OK')"
git add app/motos_assai/models/nf_qpa_vinculo.py app/motos_assai/models/__init__.py
git commit -m "feat(motos-assai): model AssaiNfQpaItemVinculoHistorico (S16=c auditoria)"
```

---

### Task 13: Atualizar `models/separacao.py` — `SEPARACAO_STATUS_CARREGADA`

**Files:**
- Modify: `app/motos_assai/models/separacao.py`

- [ ] **Step 1: Adicionar constante**

Localizar bloco de constantes em `app/motos_assai/models/separacao.py`:

```python
SEPARACAO_STATUS_EM_SEPARACAO = 'EM_SEPARACAO'
SEPARACAO_STATUS_FECHADA = 'FECHADA'
SEPARACAO_STATUS_FATURADA = 'FATURADA'
SEPARACAO_STATUS_CANCELADA = 'CANCELADA'
```

Substituir por:

```python
SEPARACAO_STATUS_EM_SEPARACAO = 'EM_SEPARACAO'
SEPARACAO_STATUS_FECHADA = 'FECHADA'
SEPARACAO_STATUS_CARREGADA = 'CARREGADA'  # NOVO Fase 1: estado intermediario entre FECHADA e FATURADA
SEPARACAO_STATUS_FATURADA = 'FATURADA'
SEPARACAO_STATUS_CANCELADA = 'CANCELADA'

SEPARACAO_STATUS_VALIDOS = {
    SEPARACAO_STATUS_EM_SEPARACAO,
    SEPARACAO_STATUS_FECHADA,
    SEPARACAO_STATUS_CARREGADA,
    SEPARACAO_STATUS_FATURADA,
    SEPARACAO_STATUS_CANCELADA,
}
```

- [ ] **Step 2: Atualizar `__init__.py`** — adicionar `SEPARACAO_STATUS_CARREGADA` e `SEPARACAO_STATUS_VALIDOS` aos re-exports

- [ ] **Step 3: Smoke test**

```bash
python -c "
from app.motos_assai.models import SEPARACAO_STATUS_CARREGADA, SEPARACAO_STATUS_VALIDOS
print('CARREGADA:', SEPARACAO_STATUS_CARREGADA)
print('Validos:', sorted(SEPARACAO_STATUS_VALIDOS))
"
```

Expected: `CARREGADA: CARREGADA` + lista com 5 elementos.

- [ ] **Step 4: Commit**

```bash
git add app/motos_assai/models/separacao.py app/motos_assai/models/__init__.py
git commit -m "feat(motos-assai): SEPARACAO_STATUS_CARREGADA (D-A pipeline EM_SEPARACAO->FECHADA->CARREGADA->FATURADA)"
```

---

### Task 14: Atualizar `models/nf_qpa.py` — `NF_STATUS_CANCELADA` + 3 colunas

**Files:**
- Modify: `app/motos_assai/models/nf_qpa.py`

- [ ] **Step 1: Adicionar constante e colunas**

Localizar:
```python
NF_STATUS_BATEU = 'BATEU'
NF_STATUS_DIVERGENTE = 'DIVERGENTE'
NF_STATUS_NAO_RECONCILIADO = 'NAO_RECONCILIADO'
```

Substituir por:
```python
NF_STATUS_BATEU = 'BATEU'
NF_STATUS_DIVERGENTE = 'DIVERGENTE'
NF_STATUS_NAO_RECONCILIADO = 'NAO_RECONCILIADO'
NF_STATUS_CANCELADA = 'CANCELADA'  # NOVO Fase 1 (D3 + R5): NF cancelada via cancelar_nf_qpa

NF_STATUS_VALIDOS = {
    NF_STATUS_BATEU,
    NF_STATUS_DIVERGENTE,
    NF_STATUS_NAO_RECONCILIADO,
    NF_STATUS_CANCELADA,
}
```

Localizar a classe `AssaiNfQpa(db.Model):` e adicionar colunas (manter posicionamento consistente com colunas existentes):

```python
class AssaiNfQpa(db.Model):
    __tablename__ = 'assai_nf_qpa'

    # ... colunas existentes ...

    # Cancelamento (Fase 1 — Migration 22 + R5)
    cancelada_em = db.Column(db.DateTime)
    cancelada_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    motivo_cancelamento = db.Column(db.Text)
```

- [ ] **Step 2: Atualizar `__init__.py`** — adicionar `NF_STATUS_CANCELADA` e `NF_STATUS_VALIDOS`

- [ ] **Step 3: Smoke test**

```bash
python -c "
from app import create_app
app = create_app()
with app.app_context():
    from app.motos_assai.models import AssaiNfQpa, NF_STATUS_CANCELADA, NF_STATUS_VALIDOS
    print('CANCELADA:', NF_STATUS_CANCELADA)
    print('Colunas:', [c.name for c in AssaiNfQpa.__table__.columns if 'cancel' in c.name])
"
```

Expected: `CANCELADA: CANCELADA` + `['cancelada_em', 'cancelada_por_id', 'motivo_cancelamento']`

- [ ] **Step 4: Commit**

```bash
git add app/motos_assai/models/nf_qpa.py app/motos_assai/models/__init__.py
git commit -m "feat(motos-assai): NF_STATUS_CANCELADA + 3 colunas auditoria cancelamento"
```

---

### Task 15: Atualizar `models/moto.py` — `EVENTO_CARREGADA`

**Files:**
- Modify: `app/motos_assai/models/moto.py`

- [ ] **Step 1: Adicionar evento**

Localizar bloco:
```python
EVENTO_ESTOQUE = 'ESTOQUE'
EVENTO_MONTADA = 'MONTADA'
# ... outros ...
EVENTO_FATURADA = 'FATURADA'
EVENTO_CANCELADA = 'CANCELADA'
EVENTO_MOTO_FALTANDO = 'MOTO_FALTANDO'

EVENTOS_VALIDOS = {
    EVENTO_ESTOQUE, EVENTO_MONTADA, # ... etc
}

EVENTOS_FORA_ESTOQUE = {EVENTO_SEPARADA, EVENTO_FATURADA, EVENTO_CANCELADA, EVENTO_MOTO_FALTANDO}
```

Adicionar `EVENTO_CARREGADA`:

```python
EVENTO_ESTOQUE = 'ESTOQUE'
EVENTO_MONTADA = 'MONTADA'
EVENTO_PENDENTE = 'PENDENTE'
EVENTO_PENDENCIA_RESOLVIDA = 'PENDENCIA_RESOLVIDA'
EVENTO_DISPONIVEL = 'DISPONIVEL'
EVENTO_REVERTIDA_PARA_MONTADA = 'REVERTIDA_PARA_MONTADA'
EVENTO_SEPARADA = 'SEPARADA'
EVENTO_CARREGADA = 'CARREGADA'  # NOVO Fase 1: entre SEPARADA e FATURADA (Q8)
EVENTO_FATURADA = 'FATURADA'
EVENTO_CANCELADA = 'CANCELADA'
EVENTO_MOTO_FALTANDO = 'MOTO_FALTANDO'

EVENTOS_VALIDOS = {
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE, EVENTO_PENDENCIA_RESOLVIDA,
    EVENTO_DISPONIVEL, EVENTO_REVERTIDA_PARA_MONTADA,
    EVENTO_SEPARADA, EVENTO_CARREGADA, EVENTO_FATURADA, EVENTO_CANCELADA,
    EVENTO_MOTO_FALTANDO,
}

EVENTOS_EM_ESTOQUE = {EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE, EVENTO_DISPONIVEL}

EVENTOS_FORA_ESTOQUE = {
    EVENTO_SEPARADA,
    EVENTO_CARREGADA,  # NOVO: chassi carregado nao conta como estoque
    EVENTO_FATURADA,
    EVENTO_CANCELADA,
    EVENTO_MOTO_FALTANDO,
}
```

- [ ] **Step 2: Atualizar `__init__.py`** — adicionar `EVENTO_CARREGADA`

- [ ] **Step 3: Smoke test**

```bash
python -c "
from app.motos_assai.models import EVENTO_CARREGADA, EVENTOS_VALIDOS, EVENTOS_FORA_ESTOQUE
print('CARREGADA:', EVENTO_CARREGADA)
print('Validos:', len(EVENTOS_VALIDOS))
print('Fora estoque:', sorted(EVENTOS_FORA_ESTOQUE))
"
```

Expected: 11 eventos validos, CARREGADA na lista de fora_estoque.

- [ ] **Step 4: Commit**

```bash
git add app/motos_assai/models/moto.py app/motos_assai/models/__init__.py
git commit -m "feat(motos-assai): EVENTO_CARREGADA (Q8 — entre SEPARADA e FATURADA)"
```

---

### Task 16: Atualizar `models/pedido.py` — 4 status novos

**Files:**
- Modify: `app/motos_assai/models/pedido.py`

- [ ] **Step 1: Substituir constantes de status**

Localizar:
```python
PEDIDO_STATUS_ABERTO = 'ABERTO'
PEDIDO_STATUS_EM_PRODUCAO = 'EM_PRODUCAO'
PEDIDO_STATUS_SEPARANDO = 'SEPARANDO'
PEDIDO_STATUS_FATURADO_PARCIAL = 'FATURADO_PARCIAL'
PEDIDO_STATUS_FATURADO = 'FATURADO'
PEDIDO_STATUS_CANCELADO = 'CANCELADO'

PEDIDO_STATUS_VALIDOS = {
    PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_EM_PRODUCAO, PEDIDO_STATUS_SEPARANDO,
    PEDIDO_STATUS_FATURADO_PARCIAL, PEDIDO_STATUS_FATURADO, PEDIDO_STATUS_CANCELADO,
}
```

Substituir por:
```python
# 4 status simplificados (Fase 1 — D2 + R4.2 + Q18)
# Status legados (EM_PRODUCAO, SEPARANDO, FATURADO_PARCIAL) REMOVIDOS — Big Bang Task 19.
PEDIDO_STATUS_ABERTO = 'ABERTO'
PEDIDO_STATUS_PARCIALMENTE_FATURADO = 'PARCIALMENTE_FATURADO'  # renomeado de FATURADO_PARCIAL
PEDIDO_STATUS_FATURADO = 'FATURADO'
PEDIDO_STATUS_CANCELADO = 'CANCELADO'  # roadmap futuro (R4.1) — manual via cancelar_pedido_assai

PEDIDO_STATUS_VALIDOS = {
    PEDIDO_STATUS_ABERTO,
    PEDIDO_STATUS_PARCIALMENTE_FATURADO,
    PEDIDO_STATUS_FATURADO,
    PEDIDO_STATUS_CANCELADO,
}
```

- [ ] **Step 2: Atualizar `__init__.py`** — atualizar imports (remover legados, adicionar novo)

ATENCAO: ao remover `PEDIDO_STATUS_EM_PRODUCAO` etc, callsites que importam essas constantes vão quebrar. Isso é POR DESIGN — o Big Bang (Task 19) vai consertar todos eles. Por enquanto, manter os imports legados como aliases temporários para evitar quebra:

```python
from app.motos_assai.models.pedido import (
    PEDIDO_STATUS_ABERTO,
    PEDIDO_STATUS_PARCIALMENTE_FATURADO,
    PEDIDO_STATUS_FATURADO,
    PEDIDO_STATUS_CANCELADO,
    PEDIDO_STATUS_VALIDOS,
)

# Aliases temporarios para callsites legados (REMOVER apos Big Bang Task 19)
PEDIDO_STATUS_EM_PRODUCAO = 'EM_PRODUCAO'  # DEPRECATED — sera mapeado pra ABERTO via Migration 21
PEDIDO_STATUS_SEPARANDO = 'SEPARANDO'  # DEPRECATED — idem
PEDIDO_STATUS_FATURADO_PARCIAL = PEDIDO_STATUS_PARCIALMENTE_FATURADO  # DEPRECATED — alias direto
```

- [ ] **Step 3: Smoke test**

```bash
python -c "
from app.motos_assai.models import (
    PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_PARCIALMENTE_FATURADO,
    PEDIDO_STATUS_FATURADO, PEDIDO_STATUS_CANCELADO,
    PEDIDO_STATUS_VALIDOS,
)
print('Validos:', sorted(PEDIDO_STATUS_VALIDOS))
"
```

Expected: `['ABERTO', 'CANCELADO', 'FATURADO', 'PARCIALMENTE_FATURADO']`

- [ ] **Step 4: Commit**

```bash
git add app/motos_assai/models/pedido.py app/motos_assai/models/__init__.py
git commit -m "feat(motos-assai): pedido status simplificado (4 estados) + aliases temporarios

D2 + R4.2 + Q18: ABERTO/PARCIALMENTE_FATURADO/FATURADO/CANCELADO.
Aliases temporarios para callsites legados — removidos no Big Bang Task 19."
```

---

### Task 17: Service `recalcular_status_pedido`

**Files:**
- Create: `app/motos_assai/services/pedido_status_service.py`
- Create: `tests/motos_assai/test_pedido_status_service.py`

- [ ] **Step 1: Escrever teste falhando**

Criar `tests/motos_assai/test_pedido_status_service.py`:

```python
"""Testes para recalcular_status_pedido.

Spec: §14
Plano: Task 17
"""
import pytest
from app import create_app, db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaItem, AssaiPedidoVendaLoja,
    AssaiSeparacao, AssaiSeparacaoItem,
    AssaiCd, AssaiLoja, AssaiModelo, AssaiMoto,
    PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_PARCIALMENTE_FATURADO,
    PEDIDO_STATUS_FATURADO, PEDIDO_STATUS_CANCELADO,
    SEPARACAO_STATUS_FATURADA, SEPARACAO_STATUS_FECHADA,
)
from app.motos_assai.services.pedido_status_service import recalcular_status_pedido


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


@pytest.fixture
def setup_pedido(app):
    """Cria pedido com 10 motos pedidas, 2 seps."""
    cd = AssaiCd(nome='CD Teste', cnpj='12345678000100')
    loja = AssaiLoja(numero=999, cnpj='98765432000100', nome='Loja Teste')
    modelo = AssaiModelo(codigo='SOL', regex_chassi=r'^TEST\d+$')
    db.session.add_all([cd, loja, modelo])
    db.session.flush()

    pedido = AssaiPedidoVenda(numero='TEST001', cd_id=cd.id, status=PEDIDO_STATUS_ABERTO)
    db.session.add(pedido)
    db.session.flush()

    pedido_loja = AssaiPedidoVendaLoja(pedido_id=pedido.id, loja_id=loja.id)
    db.session.add(pedido_loja)
    db.session.flush()

    item = AssaiPedidoVendaItem(
        pedido_id=pedido.id, pedido_loja_id=pedido_loja.id,
        loja_id=loja.id, modelo_id=modelo.id,
        qtd_pedida=10, valor_unitario=1000.0,
    )
    db.session.add(item)
    db.session.commit()

    return pedido, modelo, loja


def test_recalcular_zero_faturada_retorna_aberto(setup_pedido):
    pedido, modelo, loja = setup_pedido
    recalcular_status_pedido(pedido.id)
    db.session.commit()
    assert pedido.status == PEDIDO_STATUS_ABERTO


def test_recalcular_parcial_retorna_parcialmente_faturado(setup_pedido):
    pedido, modelo, loja = setup_pedido

    # Criar sep FATURADA com 3 chassis (parcial: 3/10)
    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FATURADA)
    db.session.add(sep)
    db.session.flush()

    for i in range(3):
        moto = AssaiMoto(chassi=f'TEST00{i}', modelo_id=modelo.id, cor='Preto')
        db.session.add(moto)
        db.session.flush()
        sep_item = AssaiSeparacaoItem(
            separacao_id=sep.id, chassi=moto.chassi, modelo_id=modelo.id,
            valor_unitario_qpa=1000.0,
        )
        db.session.add(sep_item)
    db.session.commit()

    recalcular_status_pedido(pedido.id)
    db.session.commit()
    assert pedido.status == PEDIDO_STATUS_PARCIALMENTE_FATURADO


def test_recalcular_total_retorna_faturado(setup_pedido):
    pedido, modelo, loja = setup_pedido

    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FATURADA)
    db.session.add(sep)
    db.session.flush()

    for i in range(10):
        moto = AssaiMoto(chassi=f'TEST10{i}', modelo_id=modelo.id, cor='Preto')
        db.session.add(moto)
        db.session.flush()
        sep_item = AssaiSeparacaoItem(
            separacao_id=sep.id, chassi=moto.chassi, modelo_id=modelo.id,
            valor_unitario_qpa=1000.0,
        )
        db.session.add(sep_item)
    db.session.commit()

    recalcular_status_pedido(pedido.id)
    db.session.commit()
    assert pedido.status == PEDIDO_STATUS_FATURADO


def test_recalcular_pedido_cancelado_nao_muda(setup_pedido):
    pedido, modelo, loja = setup_pedido
    pedido.status = PEDIDO_STATUS_CANCELADO
    db.session.commit()

    recalcular_status_pedido(pedido.id)
    db.session.commit()
    assert pedido.status == PEDIDO_STATUS_CANCELADO  # Status manual nao muda


def test_recalcular_sep_fechada_nao_conta(setup_pedido):
    """Sep FECHADA (sem NF batida) NAO conta como faturada."""
    pedido, modelo, loja = setup_pedido

    sep = AssaiSeparacao(pedido_id=pedido.id, loja_id=loja.id, status=SEPARACAO_STATUS_FECHADA)
    db.session.add(sep)
    db.session.flush()

    for i in range(5):
        moto = AssaiMoto(chassi=f'TESTF0{i}', modelo_id=modelo.id, cor='Preto')
        db.session.add(moto)
        db.session.flush()
        sep_item = AssaiSeparacaoItem(
            separacao_id=sep.id, chassi=moto.chassi, modelo_id=modelo.id,
            valor_unitario_qpa=1000.0,
        )
        db.session.add(sep_item)
    db.session.commit()

    recalcular_status_pedido(pedido.id)
    db.session.commit()
    assert pedido.status == PEDIDO_STATUS_ABERTO  # FECHADA nao conta
```

- [ ] **Step 2: Rodar testes — devem falhar (service não existe)**

```bash
pytest tests/motos_assai/test_pedido_status_service.py -v
```

Expected: ImportError ou ModuleNotFoundError.

- [ ] **Step 3: Implementar service**

Criar `app/motos_assai/services/pedido_status_service.py`:

```python
"""Service: recalcular_status_pedido.

Spec: §14
Plano: Task 17

Calcula automaticamente status do pedido baseado em qtd_faturada vs qtd_pedida:
- qtd_faturada == 0          -> ABERTO
- 0 < qtd_faturada < pedida  -> PARCIALMENTE_FATURADO
- qtd_faturada == pedida     -> FATURADO
- Manual                     -> CANCELADO (nao recalcula)

S10: chamar de TODOS callsites que afetam qtd_faturada.
A13: chamar defensivamente em finalizar_carregamento (nao muda nada por si, mas defensivo).
A14: nao re-calcula em pedido CANCELADO (estado terminal manual).
"""
from sqlalchemy import func
from app import db
from app.motos_assai.models import (
    AssaiPedidoVenda, AssaiPedidoVendaItem,
    AssaiSeparacao, AssaiSeparacaoItem,
    PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_PARCIALMENTE_FATURADO,
    PEDIDO_STATUS_FATURADO, PEDIDO_STATUS_CANCELADO,
    SEPARACAO_STATUS_FATURADA,
)


def recalcular_status_pedido(pedido_id):
    """Recalcula pedido.status baseado em chassis FATURADA vs qtd pedida.

    NAO commita — caller decide.

    Args:
        pedido_id: ID do AssaiPedidoVenda

    Returns:
        novo_status: str (status calculado, mesmo se nao mudou)
    """
    pedido = AssaiPedidoVenda.query.get(pedido_id)
    if not pedido:
        raise ValueError(f'Pedido {pedido_id} nao encontrado')

    if pedido.status == PEDIDO_STATUS_CANCELADO:
        # A13/A14: status manual terminal, nao recalcula
        return pedido.status

    qtd_pedida = (
        db.session.query(func.coalesce(func.sum(AssaiPedidoVendaItem.qtd_pedida), 0))
        .filter(AssaiPedidoVendaItem.pedido_id == pedido_id)
        .scalar() or 0
    )

    qtd_faturada = (
        db.session.query(func.count(AssaiSeparacaoItem.id))
        .join(AssaiSeparacao, AssaiSeparacao.id == AssaiSeparacaoItem.separacao_id)
        .filter(
            AssaiSeparacao.pedido_id == pedido_id,
            AssaiSeparacao.status == SEPARACAO_STATUS_FATURADA,
        )
        .scalar() or 0
    )

    if qtd_faturada == 0:
        novo_status = PEDIDO_STATUS_ABERTO
    elif qtd_faturada < qtd_pedida:
        novo_status = PEDIDO_STATUS_PARCIALMENTE_FATURADO
    else:
        novo_status = PEDIDO_STATUS_FATURADO

    if pedido.status != novo_status:
        pedido.status = novo_status

    return novo_status
```

- [ ] **Step 4: Rodar testes — devem passar**

```bash
pytest tests/motos_assai/test_pedido_status_service.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/pedido_status_service.py tests/motos_assai/test_pedido_status_service.py
git commit -m "feat(motos-assai): service recalcular_status_pedido + 5 testes"
```

---

### Task 18: Migration 21 — Backfill status pedido

**Files:**
- Create: `scripts/migrations/motos_assai_21_simplificar_status_pedido.py`

NOTA: NÃO tem `.sql` — é puro backfill Python via service `recalcular_status_pedido`.

- [ ] **Step 1: Criar `motos_assai_21_simplificar_status_pedido.py`**

```python
"""Migration 21: backfill status pedido — chama recalcular_status_pedido para cada pedido.

Spec: §2.2, §14.3
Plano: Task 18

Substitui os 6 status legados (ABERTO/EM_PRODUCAO/SEPARANDO/FATURADO_PARCIAL/FATURADO/CANCELADO)
pelos 4 novos (ABERTO/PARCIALMENTE_FATURADO/FATURADO/CANCELADO).

Pedidos com status CANCELADO nao sao tocados (status manual terminal).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from app.motos_assai.models import AssaiPedidoVenda  # noqa: E402
from app.motos_assai.services.pedido_status_service import recalcular_status_pedido  # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        # Verificar quantos pedidos com status legado
        total = AssaiPedidoVenda.query.count()
        print(f'[start] {total} pedidos no banco')

        pedidos = AssaiPedidoVenda.query.all()
        contadores = {'mudou': 0, 'manteve': 0, 'cancelado_skip': 0}

        for pedido in pedidos:
            status_antes = pedido.status
            if pedido.status == 'CANCELADO':
                contadores['cancelado_skip'] += 1
                continue

            novo_status = recalcular_status_pedido(pedido.id)
            if novo_status != status_antes:
                contadores['mudou'] += 1
                print(f'  pedido #{pedido.id}: {status_antes} -> {novo_status}')
            else:
                contadores['manteve'] += 1

        db.session.commit()

        print(f'[done] mudou: {contadores["mudou"]}, manteve: {contadores["manteve"]}, '
              f'cancelado_skip: {contadores["cancelado_skip"]}')

        # Validacao final: nao deve haver status legado
        legados = AssaiPedidoVenda.query.filter(
            AssaiPedidoVenda.status.in_(['EM_PRODUCAO', 'SEPARANDO', 'FATURADO_PARCIAL'])
        ).count()

        if legados > 0:
            print(f'[ERROR] {legados} pedidos AINDA com status legado apos backfill')
            sys.exit(1)
        print('[ok] Migration 21 aplicada — nenhum status legado restante')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Rodar local + validar**

```bash
python scripts/migrations/motos_assai_21_simplificar_status_pedido.py
psql $DATABASE_URL -c "SELECT status, COUNT(*) FROM assai_pedido_venda GROUP BY status;"
```

Expected: apenas 4 status restantes (sem EM_PRODUCAO/SEPARANDO/FATURADO_PARCIAL).

- [ ] **Step 3: Agora rodar Migration 24 (que depende de 21)**

```bash
python scripts/migrations/motos_assai_24_check_status_aceitar_novos.py
```

Expected: `[ok] Migration 24 aplicada (CHECK constraints atualizados)`

- [ ] **Step 4: Commit**

```bash
git add scripts/migrations/motos_assai_21_simplificar_status_pedido.py
git commit -m "feat(motos-assai): Migration 21 — backfill status pedido (4 novos)"
```

---

### Task 19: Big Bang A18 — Pre-flight scan callsites legados

**Files:**
- Create: `docs/superpowers/plans/2026-05-12-bigbang-callsites-list.md`

- [ ] **Step 1: Rodar grep exaustivo**

```bash
echo "=== Python (motos_assai) ===" > /tmp/grep_legados.txt
grep -rn "EM_PRODUCAO\|SEPARANDO\|FATURADO_PARCIAL" app/motos_assai/ --include='*.py' >> /tmp/grep_legados.txt 2>&1

echo "" >> /tmp/grep_legados.txt
echo "=== Templates Jinja2 (motos_assai) ===" >> /tmp/grep_legados.txt
grep -rn "EM_PRODUCAO\|SEPARANDO\|FATURADO_PARCIAL" app/templates/motos_assai/ >> /tmp/grep_legados.txt 2>&1

echo "" >> /tmp/grep_legados.txt
echo "=== JS (motos_assai) ===" >> /tmp/grep_legados.txt
grep -rn "EM_PRODUCAO\|SEPARANDO\|FATURADO_PARCIAL" app/static/motos_assai/ >> /tmp/grep_legados.txt 2>&1

echo "" >> /tmp/grep_legados.txt
echo "=== Cross-modulo (todo app/) ===" >> /tmp/grep_legados.txt
grep -rn "status.*=.*'EM_PRODUCAO'\|status.*=.*'SEPARANDO'\|status.*=.*'FATURADO_PARCIAL'" app/ --include='*.py' --include='*.html' >> /tmp/grep_legados.txt 2>&1

echo "" >> /tmp/grep_legados.txt
echo "=== Queries SQL inline ===" >> /tmp/grep_legados.txt
grep -rn "WHERE.*EM_PRODUCAO\|WHERE.*SEPARANDO\|WHERE.*FATURADO_PARCIAL" app/ --include='*.py' --include='*.html' >> /tmp/grep_legados.txt 2>&1

cat /tmp/grep_legados.txt
```

- [ ] **Step 2: Documentar resultado**

Criar `docs/superpowers/plans/2026-05-12-bigbang-callsites-list.md`:

```markdown
# Big Bang Callsites List — Status Legados

**Data**: 2026-05-12
**Spec**: §14.4 + A18
**Plano**: Task 19 (Plano 1 Fase 1)

## Resultado do grep

[colar conteudo de /tmp/grep_legados.txt]

## Refatoracoes necessarias

[para cada arquivo:linha encontrado, listar acao]

| Arquivo | Linha | Match | Acao |
|---|---|---|---|
| app/motos_assai/services/compra_service.py | 123 | `pedido.status = 'EM_PRODUCAO'` | REMOVER (R4.2 — pedido fica ABERTO ate primeira NF) |
| app/motos_assai/services/separacao_service.py | 456 | `pedido.status = SEPARANDO` | REMOVER (sem update SEPARANDO) |
| app/templates/motos_assai/pedidos/lista.html | 78 | `{% if pedido.status == 'EM_PRODUCAO' %}` | TROCAR para `'ABERTO'` ou `'PARCIALMENTE_FATURADO'` conforme contexto |
| ... | ... | ... | ... |

## Decisoes de mapeamento

- `EM_PRODUCAO` → REMOVER updates; trocar comparacoes para `ABERTO` (compra criada mas nao faturado)
- `SEPARANDO` → REMOVER updates; trocar comparacoes para `ABERTO`
- `FATURADO_PARCIAL` → trocar para `PARCIALMENTE_FATURADO`
```

- [ ] **Step 3: Commit do scan**

```bash
git add docs/superpowers/plans/2026-05-12-bigbang-callsites-list.md
git commit -m "docs(motos-assai): pre-flight scan callsites legados (Big Bang Task 19)"
```

---

### Task 20: Big Bang — Refactor callsites + remove updates EM_PRODUCAO

**Files:**
- Modify: TODOS callsites listados em Task 19

- [ ] **Step 1: Para cada arquivo da lista, aplicar refatoração**

**ATENÇÃO**: este passo é IDIOSSINCRÁTICO — depende do resultado real do grep. Cada callsite precisa de análise contextual.

Padrões comuns:

**Padrão 1**: remover update de status legado
```python
# ANTES
pedido.status = 'EM_PRODUCAO'

# DEPOIS
# (linha removida — pedido fica ABERTO ate primeira NF — R4.2)
```

**Padrão 2**: mudar comparação
```python
# ANTES
if pedido.status == 'EM_PRODUCAO':
    do_thing()

# DEPOIS
if pedido.status == PEDIDO_STATUS_ABERTO:
    do_thing()
```

**Padrão 3**: trocar nome
```python
# ANTES
PEDIDO_STATUS_FATURADO_PARCIAL

# DEPOIS
PEDIDO_STATUS_PARCIALMENTE_FATURADO
```

**Padrão 4**: templates Jinja2
```jinja2
{# ANTES #}
{% if pedido.status == 'EM_PRODUCAO' %}
  Em produção
{% elif pedido.status == 'FATURADO_PARCIAL' %}
  Faturado parcial
{% endif %}

{# DEPOIS #}
{% if pedido.status == 'ABERTO' %}
  Aberto
{% elif pedido.status == 'PARCIALMENTE_FATURADO' %}
  Parcialmente faturado
{% endif %}
```

- [ ] **Step 2: 1D.4 Validação final — re-rodar grep**

```bash
grep -rn "EM_PRODUCAO\|SEPARANDO\|FATURADO_PARCIAL" app/motos_assai/ app/templates/motos_assai/ app/static/motos_assai/ --include='*.py' --include='*.html' --include='*.js'
```

Expected: zero matches.

- [ ] **Step 3: Remover aliases temporários do `__init__.py`** (Task 16 Step 2)

```python
# REMOVER do app/motos_assai/models/__init__.py:
PEDIDO_STATUS_EM_PRODUCAO = 'EM_PRODUCAO'
PEDIDO_STATUS_SEPARANDO = 'SEPARANDO'
PEDIDO_STATUS_FATURADO_PARCIAL = PEDIDO_STATUS_PARCIALMENTE_FATURADO
```

- [ ] **Step 4: Rodar testes existentes do módulo**

```bash
pytest tests/motos_assai/ -v
```

Expected: todos passam (aliases temporários removidos não devem quebrar nada se Big Bang foi completo).

- [ ] **Step 5: Smoke test manual via UI**

```bash
python run.py
# Acessar http://localhost:5000/motos-assai/pedidos
# Verificar que lista renderiza sem erros
# Acessar http://localhost:5000/motos-assai/faturamento
# Idem
```

- [ ] **Step 6: Commit**

```bash
git add -A app/motos_assai/ app/templates/motos_assai/ app/static/motos_assai/
git commit -m "refactor(motos-assai): Big Bang status legados (A18 + S17=c)

Remove updates EM_PRODUCAO/SEPARANDO em services. Substitui comparacoes
em routes/templates/JS por status novos. Remove aliases temporarios do __init__.

Pre-flight scan: docs/superpowers/plans/2026-05-12-bigbang-callsites-list.md"
```

---

### Task 21: A6 — Guards em `disponibilizar_service` para `CARREGADA`

**Files:**
- Modify: `app/motos_assai/services/disponibilizar_service.py`
- Create: `tests/motos_assai/test_disponibilizar_service_carregada.py`

- [ ] **Step 1: Escrever teste falhando**

Criar `tests/motos_assai/test_disponibilizar_service_carregada.py`:

```python
"""Testes A6: disponibilizar_service deve bloquear chassi CARREGADA com mensagem especifica."""
import pytest
from app import create_app, db
from app.motos_assai.models import (
    AssaiCd, AssaiLoja, AssaiModelo, AssaiMoto,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL, EVENTO_CARREGADA,
)
from app.motos_assai.services.moto_evento_service import emitir_evento
from app.motos_assai.services.disponibilizar_service import disponibilizar, DisponibilizarError


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


@pytest.fixture
def chassi_carregado(app):
    """Cria chassi com status CARREGADA."""
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    modelo = AssaiModelo(codigo='SOL')
    db.session.add_all([cd, modelo])
    db.session.flush()

    moto = AssaiMoto(chassi='TEST001', modelo_id=modelo.id, cor='Preto')
    db.session.add(moto)
    db.session.flush()

    # Sequencia ate CARREGADA
    emitir_evento('TEST001', EVENTO_ESTOQUE, operador_id=1)
    emitir_evento('TEST001', EVENTO_MONTADA, operador_id=1)
    emitir_evento('TEST001', EVENTO_DISPONIVEL, operador_id=1)
    emitir_evento('TEST001', EVENTO_CARREGADA, operador_id=1)
    db.session.commit()

    return moto


def test_disponibilizar_chassi_carregada_levanta_erro(chassi_carregado):
    """A6: tentar disponibilizar chassi CARREGADA deve levantar com mensagem especifica."""
    with pytest.raises(DisponibilizarError) as exc_info:
        disponibilizar('TEST001', operador_id=1)

    msg = str(exc_info.value)
    assert 'CARREGADA' in msg
    assert 'cancele o Carregamento' in msg or 'substitua' in msg
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
pytest tests/motos_assai/test_disponibilizar_service_carregada.py -v
```

Expected: ImportError ou AssertionError (msg não contém "CARREGADA").

- [ ] **Step 3: Modificar `app/motos_assai/services/disponibilizar_service.py`**

Localizar a função `disponibilizar()` e o ponto onde valida estado atual. Adicionar dispatch por status:

```python
# (na funcao disponibilizar)
status_atual = status_efetivo(chassi)

# A6: dispatch por status com mensagem especifica
if status_atual not in (EVENTO_MONTADA, EVENTO_REVERTIDA_PARA_MONTADA):
    msg_por_status = {
        EVENTO_DISPONIVEL: f'Chassi {chassi} ja esta DISPONIVEL.',
        EVENTO_SEPARADA: (
            f'Chassi {chassi} esta SEPARADA. '
            'Para reverter, cancele a Sep ou desfaca o item.'
        ),
        EVENTO_CARREGADA: (
            f'Chassi {chassi} esta CARREGADA. '
            'Para reverter, cancele o Carregamento ou substitua o chassi (cross-loja).'
        ),
        EVENTO_FATURADA: (
            f'Chassi {chassi} esta FATURADA. '
            'Para reverter, cancele a NF (cancelar_nf_qpa).'
        ),
    }
    raise DisponibilizarError(
        msg_por_status.get(status_atual, f'Chassi {chassi} em estado {status_atual} (esperado MONTADA).')
    )
```

- [ ] **Step 4: Rodar teste — deve passar**

```bash
pytest tests/motos_assai/test_disponibilizar_service_carregada.py -v
```

- [ ] **Step 5: Rodar todos testes do módulo (regressão)**

```bash
pytest tests/motos_assai/ -v
```

- [ ] **Step 6: Commit**

```bash
git add app/motos_assai/services/disponibilizar_service.py tests/motos_assai/test_disponibilizar_service_carregada.py
git commit -m "feat(motos-assai): A6 guards em disponibilizar_service (mensagens especificas por status)"
```

---

### Task 22: A6 — Guards em `montagem_service` para `CARREGADA`

**Files:**
- Modify: `app/motos_assai/services/montagem_service.py`
- Create: `tests/motos_assai/test_montagem_service_carregada.py`

- [ ] **Step 1: Escrever teste falhando** (similar à Task 21)

```python
"""Testes A6: montagem_service deve bloquear chassi CARREGADA."""
import pytest
from app import create_app, db
from app.motos_assai.models import AssaiCd, AssaiModelo, AssaiMoto, EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL, EVENTO_CARREGADA
from app.motos_assai.services.moto_evento_service import emitir_evento
from app.motos_assai.services.montagem_service import registrar_montagem, MontagemError


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.session.rollback()
        db.drop_all()


def test_registrar_montagem_chassi_carregada_levanta_erro(app):
    cd = AssaiCd(nome='CD', cnpj='12345678000100')
    modelo = AssaiModelo(codigo='SOL')
    db.session.add_all([cd, modelo])
    db.session.flush()

    moto = AssaiMoto(chassi='TEST001', modelo_id=modelo.id, cor='Preto')
    db.session.add(moto)
    db.session.flush()

    for ev in [EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL, EVENTO_CARREGADA]:
        emitir_evento('TEST001', ev, operador_id=1)
    db.session.commit()

    with pytest.raises(MontagemError) as exc_info:
        registrar_montagem('TEST001', operador_id=1, com_defeito=False)

    assert 'CARREGADA' in str(exc_info.value)
```

- [ ] **Step 2: Rodar — deve falhar**

```bash
pytest tests/motos_assai/test_montagem_service_carregada.py -v
```

- [ ] **Step 3: Modificar `montagem_service.py`** (mesmo padrão da Task 21 Step 3)

Localizar função `registrar_montagem` e o ponto de validação de estado. Adicionar dispatch.

- [ ] **Step 4: Rodar testes (incluindo regressão)**

```bash
pytest tests/motos_assai/ -v
```

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/montagem_service.py tests/motos_assai/test_montagem_service_carregada.py
git commit -m "feat(motos-assai): A6 guards em montagem_service (mensagens especificas)"
```

---

### Task 23: Migration 25 — Backfill divergências legadas

**Files:**
- Create: `scripts/migrations/motos_assai_25_backfill_divergencias_legadas.py`

NOTA: NÃO tem `.sql` — backfill puro Python via insert em `assai_divergencia` baseado em `assai_nf_qpa_item.tipo_divergencia`.

- [ ] **Step 1: Criar `motos_assai_25_backfill_divergencias_legadas.py`**

```python
"""Migration 25: backfill divergencias legadas — assai_nf_qpa_item.tipo_divergencia -> assai_divergencia.

Spec: §2.2 (S8=a + A12)
Plano: Task 23

Para cada AssaiNfQpaItem.tipo_divergencia nao nulo, cria linha em assai_divergencia.
Idempotente: nao cria duplicatas (verifica por (nf_id, chassi, tipo)).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from app.motos_assai.models import (  # noqa: E402
    AssaiNfQpaItem, AssaiDivergencia, DIVERGENCIA_TIPOS_VALIDOS,
)
from sqlalchemy import and_  # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        items_legados = AssaiNfQpaItem.query.filter(
            AssaiNfQpaItem.tipo_divergencia.isnot(None)
        ).all()

        print(f'[start] {len(items_legados)} items com tipo_divergencia legado')

        criadas = 0
        skipadas = 0

        for item in items_legados:
            tipo = item.tipo_divergencia

            # Validacao: tipo deve estar nos validos da nova tabela
            if tipo not in DIVERGENCIA_TIPOS_VALIDOS:
                print(f'  [skip] item #{item.id} tipo invalido: {tipo}')
                skipadas += 1
                continue

            # Idempotente: verificar se ja existe
            ja_existe = AssaiDivergencia.query.filter(and_(
                AssaiDivergencia.nf_id == item.nf_id,
                AssaiDivergencia.chassi == item.chassi,
                AssaiDivergencia.tipo == tipo,
            )).first()

            if ja_existe:
                skipadas += 1
                continue

            div = AssaiDivergencia(
                tipo=tipo,
                chassi=item.chassi,
                nf_id=item.nf_id,
                separacao_id=item.separacao_item.separacao_id if item.separacao_item else None,
                detalhes={
                    'origem': 'backfill_migration_25',
                    'nf_qpa_item_id': item.id,
                    'modelo_extraido': item.modelo_extraido,
                    'valor_extraido': float(item.valor_extraido) if item.valor_extraido else None,
                },
            )
            db.session.add(div)
            criadas += 1

        db.session.commit()
        print(f'[done] criadas: {criadas}, skipadas (ja existentes ou invalidas): {skipadas}')
        print('[ok] Migration 25 aplicada')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Rodar local**

```bash
python scripts/migrations/motos_assai_25_backfill_divergencias_legadas.py
psql $DATABASE_URL -c "SELECT tipo, COUNT(*) FROM assai_divergencia GROUP BY tipo;"
```

Expected: linhas em `assai_divergencia` por tipo.

- [ ] **Step 3: Commit**

```bash
git add scripts/migrations/motos_assai_25_backfill_divergencias_legadas.py
git commit -m "feat(motos-assai): Migration 25 — backfill tipo_divergencia legado -> assai_divergencia"
```

---

### Task 24: Smoke tests Fase 1 — `test_models_constantes`

**Files:**
- Create: `tests/motos_assai/test_models_constantes.py`

- [ ] **Step 1: Criar smoke test de imports + constantes**

```python
"""Smoke test Fase 1: confirma que todos imports funcionam e constantes batem com schema.

Plano Task 24
"""
import pytest
from app import create_app, db


@pytest.fixture
def app():
    app = create_app('testing')
    with app.app_context():
        db.create_all()
        yield app
        db.drop_all()


def test_imports_modelos_novos(app):
    """Todos modelos novos da Fase 1 devem importar sem erros."""
    from app.motos_assai.models import (
        AssaiCarregamento, AssaiCarregamentoItem,
        AssaiDivergencia,
        AssaiPedidoExcel,
        AssaiNfQpaItemVinculoHistorico,
    )

    # Tabelas devem existir no metadata
    assert 'assai_carregamento' in db.metadata.tables
    assert 'assai_carregamento_item' in db.metadata.tables
    assert 'assai_divergencia' in db.metadata.tables
    assert 'assai_pedido_excel' in db.metadata.tables
    assert 'assai_nf_qpa_item_vinculo_historico' in db.metadata.tables


def test_constantes_status_separacao_inclui_carregada(app):
    from app.motos_assai.models import (
        SEPARACAO_STATUS_VALIDOS,
        SEPARACAO_STATUS_CARREGADA,
    )
    assert SEPARACAO_STATUS_CARREGADA in SEPARACAO_STATUS_VALIDOS
    assert len(SEPARACAO_STATUS_VALIDOS) == 5


def test_constantes_status_nf_inclui_cancelada(app):
    from app.motos_assai.models import NF_STATUS_VALIDOS, NF_STATUS_CANCELADA
    assert NF_STATUS_CANCELADA in NF_STATUS_VALIDOS
    assert len(NF_STATUS_VALIDOS) == 4


def test_constantes_evento_inclui_carregada(app):
    from app.motos_assai.models import EVENTOS_VALIDOS, EVENTO_CARREGADA, EVENTOS_FORA_ESTOQUE
    assert EVENTO_CARREGADA in EVENTOS_VALIDOS
    assert EVENTO_CARREGADA in EVENTOS_FORA_ESTOQUE


def test_constantes_status_pedido_simplificado(app):
    from app.motos_assai.models import (
        PEDIDO_STATUS_VALIDOS,
        PEDIDO_STATUS_ABERTO,
        PEDIDO_STATUS_PARCIALMENTE_FATURADO,
        PEDIDO_STATUS_FATURADO,
        PEDIDO_STATUS_CANCELADO,
    )
    assert PEDIDO_STATUS_VALIDOS == {
        PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_PARCIALMENTE_FATURADO,
        PEDIDO_STATUS_FATURADO, PEDIDO_STATUS_CANCELADO,
    }


def test_constantes_carregamento(app):
    from app.motos_assai.models import (
        CARREGAMENTO_STATUS_VALIDOS,
        CARREGAMENTO_STATUS_EM_CARREGAMENTO,
        CARREGAMENTO_STATUS_FINALIZADO,
        CARREGAMENTO_STATUS_CANCELADO,
    )
    assert len(CARREGAMENTO_STATUS_VALIDOS) == 3


def test_constantes_divergencia_9_tipos(app):
    from app.motos_assai.models import DIVERGENCIA_TIPOS_VALIDOS
    assert len(DIVERGENCIA_TIPOS_VALIDOS) == 8  # 4 novos + 4 legados


def test_constantes_divergencia_5_resolucoes(app):
    from app.motos_assai.models import DIVERGENCIA_RESOLUCAO_VALIDAS
    assert len(DIVERGENCIA_RESOLUCAO_VALIDAS) == 5
```

- [ ] **Step 2: Rodar testes**

```bash
pytest tests/motos_assai/test_models_constantes.py -v
```

Expected: 8 passed.

- [ ] **Step 3: Rodar TODOS testes do módulo (regressão final)**

```bash
pytest tests/motos_assai/ -v
```

Expected: zero falhas.

- [ ] **Step 4: Commit**

```bash
git add tests/motos_assai/test_models_constantes.py
git commit -m "test(motos-assai): smoke tests Fase 1 (imports + constantes)"
```

---

### Task 25: Deploy Fase 1 em prod (Render)

**Files:** (nenhum — apenas operação de deploy)

- [ ] **Step 1: Push da branch + criar PR**

```bash
git push origin feature/motos-assai-fase1-fundacao
gh pr create --title "feat(motos-assai): Fase 1 — Fundacao (10 migrations + models + Big Bang status)" --body "$(cat <<'EOF'
## Summary

Fase 1 do design Carregamento + Divergencia + NF (spec 2026-05-12-motos-assai-carregamento-divergencia-design.md v1.2).

Adiciona fundacao estrutural sem alterar comportamento de UI:
- 10 migrations (18-27): 4 tabelas novas + 4 colunas de cancelamento + UNIQUE NF + CHECK constraints
- Models Python para 4 entidades novas (AssaiCarregamento, AssaiDivergencia, AssaiPedidoExcel, AssaiNfQpaItemVinculoHistorico)
- Constantes: SEPARACAO_STATUS_CARREGADA, NF_STATUS_CANCELADA, EVENTO_CARREGADA, 4 status pedido simplificados
- Service `recalcular_status_pedido` + Migration 21 backfill
- A6 guards em `disponibilizar_service` e `montagem_service` para mensagens especificas
- Big Bang A18: erradicacao de `EM_PRODUCAO`/`SEPARANDO`/`FATURADO_PARCIAL` em routes/services/templates/JS
- Migration 25: backfill divergencias legadas em assai_nf_qpa_item.tipo_divergencia -> assai_divergencia

Sem mudancas de UI. Sem novos services de Carregamento (Fase 2). Sem _calcular_match v2 (Fase 4).

## Test plan
- [x] Todas migrations idempotentes (rodam 2x sem erro)
- [x] Smoke tests `test_models_constantes` (8 testes)
- [x] Testes `test_pedido_status_service` (5 testes)
- [x] Testes A6 `test_disponibilizar_service_carregada` + `test_montagem_service_carregada`
- [x] Pre-flight scan validado: zero matches de status legado apos Big Bang
- [ ] Smoke test manual em prod: `/motos-assai/pedidos`, `/motos-assai/faturamento`, `/motos-assai/separacao` renderizam OK

🤖 Generated with [Claude Code](https://claude.com/claude-code)
EOF
)"
```

- [ ] **Step 2: Aguardar CI passar**

Verificar no GitHub que pipelines (lint, tests) passam.

- [ ] **Step 3: Merge para main**

Apos approval do reviewer.

- [ ] **Step 4: Aplicar migrations em prod (Render Shell)**

Conectar no Render Shell e rodar **NA ORDEM**:

```bash
cd /opt/render/project/src
source .venv/bin/activate

python scripts/migrations/motos_assai_18_carregamento.py
python scripts/migrations/motos_assai_19_divergencia.py
python scripts/migrations/motos_assai_20_pedido_excel.py
python scripts/migrations/motos_assai_22_nf_cancelamento_campos.py
python scripts/migrations/motos_assai_26_vinculo_historico.py
python scripts/migrations/motos_assai_27_unique_nf_sep_ativa.py

# Migration 21 e 24 sao acopladas (24 depende de 21)
python scripts/migrations/motos_assai_21_simplificar_status_pedido.py
python scripts/migrations/motos_assai_24_check_status_aceitar_novos.py

python scripts/migrations/motos_assai_25_backfill_divergencias_legadas.py
```

- [ ] **Step 5: Smoke test manual em prod**

Acessar https://app.nacomgoya.com.br/motos-assai/pedidos — confirmar que:
- Lista renderiza sem erros 500
- Status mostrados são os 4 novos (ABERTO/PARCIALMENTE_FATURADO/FATURADO/CANCELADO)
- Painel de NFs órfãs em `/motos-assai/faturamento` continua funcionando

- [ ] **Step 6: Validar tabelas em prod**

```bash
psql $DATABASE_URL -c "
SELECT
    'assai_carregamento' AS tabela, COUNT(*) FROM assai_carregamento
UNION ALL SELECT
    'assai_divergencia', COUNT(*) FROM assai_divergencia
UNION ALL SELECT
    'assai_pedido_excel', COUNT(*) FROM assai_pedido_excel
UNION ALL SELECT
    'assai_nf_qpa_item_vinculo_historico', COUNT(*) FROM assai_nf_qpa_item_vinculo_historico;
"

# Verificar status pedido apos backfill
psql $DATABASE_URL -c "SELECT status, COUNT(*) FROM assai_pedido_venda GROUP BY status;"

# Verificar divergencias migradas (esperado: linhas com origem='backfill_migration_25')
psql $DATABASE_URL -c "
SELECT tipo, COUNT(*) FROM assai_divergencia
WHERE detalhes->>'origem' = 'backfill_migration_25'
GROUP BY tipo;
"
```

- [ ] **Step 7: Pos-deploy task**

Documentar em `app/motos_assai/CLAUDE.md` que a Fase 1 está completa, Fase 2 (Carregamento services) é o próximo passo. Atualizar a seção "Plano X implementado".

---

## Self-review (executor — pre-execucao)

Antes de iniciar a Task 1, executor deve:

1. **Confirmar pré-requisitos**:
   - Migration 17 aplicada em prod
   - Backup recente do banco
   - Branch `feature/motos-assai-fase1-fundacao` criada
   - `python -c "from app import create_app; create_app()"` roda sem erros

2. **Verificar dependências**:
   - PostgreSQL >= 14 (para suporte a `WHERE` em UNIQUE INDEX)
   - SQLAlchemy >= 2.0 (para sintaxe de relationships)

3. **Estimativa de tempo**:
   - Tasks 1-8 (migrations + models): ~4-6 horas
   - Tasks 9-12 (modelos Python): ~2-3 horas
   - Tasks 13-16 (constantes models): ~1-2 horas
   - Task 17 (service + tests): ~2 horas
   - Task 18 (Migration 21): ~30 min
   - Tasks 19-20 (Big Bang): ~3-6 horas (depende do tamanho do scan)
   - Tasks 21-22 (A6 guards): ~2 horas
   - Task 23 (Migration 25): ~30 min
   - Task 24 (smoke tests): ~30 min
   - Task 25 (deploy): ~1 hora

   **Total estimado**: 16-22 horas de desenvolvimento.

---

## Plano completo

**25 tasks** distribuídas em **6 sub-fases** da spec (1A-1F + Pré-req + Deploy):
- 1 pré-requisito
- 7 migrations DDL (Tasks 2-8)
- 4 modelos novos (Tasks 9-12)
- 4 atualizações de modelos (Tasks 13-16)
- 1 service novo (Task 17)
- 1 backfill status (Task 18)
- 2 sub-tasks Big Bang (Tasks 19-20)
- 2 A6 guards (Tasks 21-22)
- 1 backfill divergências (Task 23)
- 1 smoke tests (Task 24)
- 1 deploy (Task 25)

Após Task 25, **Fase 1 estará deployada em prod**. Próximos planos:
- **Plano 2**: Fase 2-3 (Carregamento service + UI)
- **Plano 3**: Fase 4 (NF + Divergências + Cancelar NF + Migration 23 backfill NFs órfãs)
- **Plano 4**: Fase 5 (Substituir chassi cross-loja + Parser CCe roadmap)
