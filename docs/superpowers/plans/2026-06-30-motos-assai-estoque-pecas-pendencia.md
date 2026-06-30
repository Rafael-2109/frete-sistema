<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-30
-->
# Estoque de Peças + Pendência Categorizada — Plano de Implementação (Spec 1: back-end)

> **Papel:** plano de implementação TDD (back-end) do Spec 1 — Estoque de Peças + Pendência categorizada no módulo Motos Assaí (6 tabelas, 12 tarefas). Par do spec `docs/superpowers/specs/2026-06-30-motos-assai-estoque-pecas-pendencia-design.md`.

## Indice

- [Global Constraints](#global-constraints)
- [Task 1: Migration 34 — 6 tabelas + índice parcial](#task-1-migration-34--6-tabelas--índice-parcial)
- [Task 2: Model AssaiPeca/AssaiPecaModelo + peca_service](#task-2-model-assaipecaassaipecamodelo--peca_service)
- [Task 3: Model AssaiPendencia + constantes (model-only)](#task-3-model-assaipendencia--constantes-model-only)
- [Task 4: Model AssaiEstoqueMovimento + movimento_service (entrada/saldo/custo/descarte/ajuste)](#task-4-model-assaiestoquemovimento--movimento_service-entradasaldocustodescarteajuste)
- [Task 5: Model AssaiPecaCompra/Item + compra_peca_service](#task-5-model-assaipecacompraitem--compra_peca_service)
- [Task 6: Núcleo da pendência — abrir_pendencia + acoplamento com o evento PENDENTE](#task-6-núcleo-da-pendência--abrir_pendencia--acoplamento-com-o-evento-pendente)
- [Task 7: resolver_pendencia + cancelar_pendencia (gate de fechamento + MONTADA)](#task-7-resolver_pendencia--cancelar_pendencia-gate-de-fechamento--montada)
- [Task 8: Tratativas com movimento de estoque — consumir/canibalizar + solicitar_compra](#task-8-tratativas-com-movimento-de-estoque--consumircanibalizar--solicitar_compra)
- [Task 9: Migrar leituras de pendencia_service para a tabela assai_pendencia](#task-9-migrar-leituras-de-pendencia_service-para-a-tabela-assai_pendencia)
- [Task 10: Ganchos de integração (3 emissores) + shim retrocompatível de resolver_pendencia](#task-10-ganchos-de-integração-3-emissores--shim-retrocompatível-de-resolver_pendencia)
- [Task 11: Backfill motos_assai_35_backfill_pendencias.py (PENDENTE sem ficha → AssaiPendencia)](#task-11-backfill-motos_assai_35_backfill_pendenciaspy-pendente-sem-ficha--assaipendencia)
- [Task 12: Schema JSON + TABLE_DESCRIPTIONS + doc do módulo](#task-12-schema-json--table_descriptions--doc-do-módulo)


> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir o back-end (6 tabelas + camada de serviços) de Estoque de Peças e Pendência categorizada no módulo `motos_assai`, sem quebrar o pipeline existente.

**Architecture:** Três SOTs com papéis separados — o **evento da moto** (`assai_moto_evento.PENDENTE`) segue sendo o estado físico (intocado: 1 por chassi); a **ficha** `assai_pendencia` é o tratamento (N por chassi, compartilhando 1 evento, com categoria/origem/tratativa/resolução 1:1); o **ledger** `assai_estoque_movimento` é a peça (append-only, elo de toda movimentação com custo/receita). Serviços fazem flush-sem-commit (o caller commita); o acoplamento ficha↔evento roda sob `pg_advisory_xact_lock(hashtext(chassi))`.

**Tech Stack:** Python 3.12 · Flask 3.1 · Flask-SQLAlchemy 3.1 · SQLAlchemy 2.0 · PostgreSQL 18 · pytest (contra **banco local real**).

## Global Constraints

- Prefixo de tabela `assai_` em todas as 6 tabelas novas.
- `chassi*` é `db.String(50)` **por valor** (sem FK para `assai_moto`) — invariante central do módulo.
- Timezone: `from app.utils.timezone import agora_brasil_naive` (Brasil naive) em todo default de timestamp.
- JSONB sempre gravado via `from app.utils.json_helpers import sanitize_for_json`.
- **Sem CHECK** nas tabelas novas — validação de `categoria`/`origem`/`tipo`/`status` por **set Python no service** (molde `AssaiDivergencia`). `ck_assai_moto_evento_tipo` permanece **intocado** (reuso de PENDENTE/PENDENCIA_RESOLVIDA/MONTADA).
- Migration 34 segue o padrão das 30/32/33: aplicada **manualmente** em prod + local; **não** entra no `build.sh`; o arquivo fica versionado como registro do DDL idempotente.
- Serviços: `criar/abrir/registrar/solicitar_*` fazem `db.session.add` + `db.session.flush()` **sem commit** (o caller commita); `resolver/cancelar_*` idempotentes; exceção de domínio por service (`PecaError`, `EstoqueError`, `PendenciaError`, `CompraPecaError`).
- **Testes rodam contra o banco local real** (`create_app()`). Padrão: `def test_x(app, admin_user): with app.app_context(): ... db.session.rollback()`; chassi único `f'TST_{uuid.uuid4().hex[:8].upper()}'`; fixtures `app`/`admin_user` de `tests/motos_assai/conftest.py`; `AssaiModelo` `'DOT'` é seed. **Pré-requisito de toda task de model/serviço: a migration 34 já aplicada no banco local (Task 1).**
- Commits **sem `[skip render]`**. Ativar venv antes de pytest: `source .venv/bin/activate`.

> **Spec de origem:** `docs/superpowers/specs/2026-06-30-motos-assai-estoque-pecas-pendencia-design.md`. As decisões D1-D4 / O1-O4 / E1-E2 / R1-R4 / O-C estão na §2 e §14 do spec.

---

I have everything I need. Here is my section of the plan (Tasks 1-5).

---

### Task 1: Migration 34 — 6 tabelas + índice parcial

**Files:**
- Create: `scripts/migrations/motos_assai_34_estoque_pecas_pendencia.sql`
- Create: `scripts/migrations/motos_assai_34_estoque_pecas_pendencia.py`
- Test: `tests/motos_assai/test_migration_34.py`

**Interfaces:**
- Consumes: tabelas existentes `usuarios`, `assai_modelo`, `assai_moto_evento`, `assai_devolucao_item`, `assai_pos_venda_ocorrencia`, `assai_divergencia`.
- Produces: tabelas `assai_peca`, `assai_peca_modelo`, `assai_peca_compra`, `assai_pendencia`, `assai_peca_compra_item`, `assai_estoque_movimento` + índice parcial `ix_assai_pendencia_aberta`. Ordem de criação resolve FKs sem ALTER (nenhuma dependência circular real: `pendencia` não referencia `estoque_movimento` nem `compra_item`).

Steps:
- [ ] Escrever `tests/motos_assai/test_migration_34.py` que falha:
```python
from app import db
from sqlalchemy import text

TABELAS = [
    'assai_peca', 'assai_peca_modelo', 'assai_peca_compra',
    'assai_pendencia', 'assai_peca_compra_item', 'assai_estoque_movimento',
]


def test_seis_tabelas_existem(app):
    with app.app_context():
        existentes = {
            r[0] for r in db.session.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = ANY(:nomes)"
            ), {'nomes': TABELAS})
        }
        faltando = set(TABELAS) - existentes
        assert not faltando, f'Tabelas faltando: {sorted(faltando)}'


def test_indice_parcial_pendencia_aberta(app):
    with app.app_context():
        idx = db.session.execute(text(
            "SELECT indexdef FROM pg_indexes "
            "WHERE indexname = 'ix_assai_pendencia_aberta'"
        )).scalar()
        assert idx is not None, 'ix_assai_pendencia_aberta nao existe'
        assert 'resolvida_em IS NULL' in idx and 'cancelada_em IS NULL' in idx
```
- [ ] Rodar e ver falhar: `source .venv/bin/activate && pytest tests/motos_assai/test_migration_34.py -v` — Expected: FAIL (tabelas não existem).
- [ ] Implementar `scripts/migrations/motos_assai_34_estoque_pecas_pendencia.sql` (DDL completo, idempotente):
```sql
-- Migration 34: Estoque de Pecas + Pendencia categorizada (Spec 1 — back-end).
--
-- 6 tabelas novas. Sem CHECK (validacao por set Python no service, molde
-- Divergencia/Compra). Ordem de criacao evita FK pendente: peca -> peca_modelo
-- -> peca_compra -> pendencia -> peca_compra_item -> estoque_movimento.
-- (pendencia NAO referencia estoque_movimento nem compra_item -> sem ciclo.)
--
-- Convencao de deploy (padrao 30/32/33): aplicar manualmente em prod+local;
-- NAO consta no build.sh; arquivo versionado so como registro do DDL.

BEGIN;

-- 4.1 catalogo de pecas
CREATE TABLE IF NOT EXISTS assai_peca (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(40),
    nome VARCHAR(120) NOT NULL,
    custo_referencia NUMERIC(15,4),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    dados_extras JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_assai_peca_codigo ON assai_peca(codigo);

-- 4.2 compatibilidade N:N peca x modelo
CREATE TABLE IF NOT EXISTS assai_peca_modelo (
    id SERIAL PRIMARY KEY,
    peca_id INTEGER NOT NULL REFERENCES assai_peca(id) ON DELETE CASCADE,
    modelo_id INTEGER NOT NULL REFERENCES assai_modelo(id) ON DELETE CASCADE,
    CONSTRAINT uq_assai_peca_modelo UNIQUE (peca_id, modelo_id)
);

-- 4.5 pedido de compra (cabecalho)
CREATE TABLE IF NOT EXISTS assai_peca_compra (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(20) NOT NULL UNIQUE,
    tipo VARCHAR(20) NOT NULL,
    status VARCHAR(30) NOT NULL DEFAULT 'ABERTA',
    fornecedor VARCHAR(120) NOT NULL DEFAULT 'MOTOCHEFE',
    criada_em TIMESTAMP NOT NULL DEFAULT NOW(),
    criada_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    observacao TEXT,
    dados_extras JSONB DEFAULT '{}'::jsonb
);

-- 4.3 ficha de pendencia categorizada
CREATE TABLE IF NOT EXISTS assai_pendencia (
    id SERIAL PRIMARY KEY,
    chassi VARCHAR(50) NOT NULL,
    categoria VARCHAR(20) NOT NULL,
    origem VARCHAR(20) NOT NULL,
    tratativa VARCHAR(40),
    fase VARCHAR(20) NOT NULL DEFAULT 'ABERTA',
    retorno_fisico BOOLEAN NOT NULL DEFAULT FALSE,
    descricao TEXT NOT NULL,
    pendencia_pai_id INTEGER REFERENCES assai_pendencia(id) ON DELETE SET NULL,
    evento_pendente_id INTEGER REFERENCES assai_moto_evento(id) ON DELETE SET NULL,
    peca_id INTEGER REFERENCES assai_peca(id) ON DELETE SET NULL,
    chassi_doador VARCHAR(50),
    devolucao_item_id INTEGER REFERENCES assai_devolucao_item(id) ON DELETE SET NULL,
    pos_venda_ocorrencia_id INTEGER REFERENCES assai_pos_venda_ocorrencia(id) ON DELETE SET NULL,
    divergencia_origem_id INTEGER REFERENCES assai_divergencia(id) ON DELETE SET NULL,
    detalhes JSONB DEFAULT '{}'::jsonb,
    aberta_em TIMESTAMP NOT NULL DEFAULT NOW(),
    aberta_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    resolvida_em TIMESTAMP,
    resolvida_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    resolucao_descricao TEXT,
    cancelada_em TIMESTAMP,
    cancelada_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_assai_pendencia_chassi ON assai_pendencia(chassi);
CREATE INDEX IF NOT EXISTS ix_assai_pendencia_aberta
    ON assai_pendencia(chassi)
    WHERE resolvida_em IS NULL AND cancelada_em IS NULL;

-- 4.6 itens do pedido de compra
CREATE TABLE IF NOT EXISTS assai_peca_compra_item (
    id SERIAL PRIMARY KEY,
    compra_id INTEGER NOT NULL REFERENCES assai_peca_compra(id) ON DELETE CASCADE,
    peca_id INTEGER NOT NULL REFERENCES assai_peca(id) ON DELETE RESTRICT,
    quantidade NUMERIC(15,3) NOT NULL,
    quantidade_recebida NUMERIC(15,3) NOT NULL DEFAULT 0,
    custo_estimado NUMERIC(15,4),
    pendencia_id INTEGER REFERENCES assai_pendencia(id) ON DELETE SET NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_assai_peca_compra_item_compra ON assai_peca_compra_item(compra_id);

-- 4.4 ledger append-only de estoque
CREATE TABLE IF NOT EXISTS assai_estoque_movimento (
    id BIGSERIAL PRIMARY KEY,
    peca_id INTEGER NOT NULL REFERENCES assai_peca(id) ON DELETE RESTRICT,
    tipo VARCHAR(40) NOT NULL,
    quantidade NUMERIC(15,3) NOT NULL,
    delta_almoxarifado NUMERIC(15,3) NOT NULL DEFAULT 0,
    chassi_origem VARCHAR(50),
    chassi_destino VARCHAR(50),
    pendencia_id INTEGER REFERENCES assai_pendencia(id) ON DELETE SET NULL,
    compra_item_id INTEGER REFERENCES assai_peca_compra_item(id) ON DELETE SET NULL,
    custo_unitario NUMERIC(15,4),
    custo_total NUMERIC(15,2),
    receita_unitaria NUMERIC(15,4),
    receita_total NUMERIC(15,2),
    operador_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    ocorrido_em TIMESTAMP NOT NULL DEFAULT NOW(),
    observacao TEXT,
    dados_extras JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_assai_estoque_movimento_peca ON assai_estoque_movimento(peca_id);
CREATE INDEX IF NOT EXISTS ix_assai_estoque_movimento_chassi_origem ON assai_estoque_movimento(chassi_origem);
CREATE INDEX IF NOT EXISTS ix_assai_estoque_movimento_chassi_destino ON assai_estoque_movimento(chassi_destino);
CREATE INDEX IF NOT EXISTS ix_assai_estoque_movimento_pendencia ON assai_estoque_movimento(pendencia_id);

COMMIT;
```
- [ ] Implementar `scripts/migrations/motos_assai_34_estoque_pecas_pendencia.py` (runner, molde 28):
```python
"""Migration 34: Estoque de Pecas + Pendencia categorizada (Spec 1 — back-end).

Cria 6 tabelas: assai_peca, assai_peca_modelo, assai_peca_compra,
assai_pendencia, assai_peca_compra_item, assai_estoque_movimento.

Idempotente (CREATE TABLE/INDEX IF NOT EXISTS). NAO consta no build.sh —
aplicar manualmente em prod (DATABASE_URL_PROD) + local (padrao 30/32/33).

Spec: docs/superpowers/specs/2026-06-30-motos-assai-estoque-pecas-pendencia-design.md
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


SQL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'motos_assai_34_estoque_pecas_pendencia.sql',
)

TABELAS = [
    'assai_peca', 'assai_peca_modelo', 'assai_peca_compra',
    'assai_pendencia', 'assai_peca_compra_item', 'assai_estoque_movimento',
]


def main():
    app = create_app()
    with app.app_context():
        with open(SQL_PATH, 'r') as f:
            sql = f.read()

        db.session.execute(text(sql))
        db.session.commit()

        # Validacao pos: 6 tabelas presentes
        existentes = {
            r[0] for r in db.session.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_name = ANY(:nomes)"
            ), {'nomes': TABELAS})
        }
        faltando = set(TABELAS) - existentes
        if faltando:
            print(f'[ERRO] Tabelas faltando: {sorted(faltando)}')
            sys.exit(1)
        print(f'[ok] Migration 34 aplicada. {len(existentes)}/6 tabelas presentes:')
        for t in TABELAS:
            print(f'  - {t}')

        idx = db.session.execute(text(
            "SELECT indexname FROM pg_indexes "
            "WHERE indexname = 'ix_assai_pendencia_aberta'"
        )).scalar()
        print(f'  indice parcial: {idx or "AUSENTE"}')


if __name__ == '__main__':
    main()
```
- [ ] Aplicar no banco local: `source .venv/bin/activate && python scripts/migrations/motos_assai_34_estoque_pecas_pendencia.py` — Expected: `[ok] Migration 34 aplicada. 6/6 tabelas presentes`.
- [ ] Rodar e ver passar: `source .venv/bin/activate && pytest tests/motos_assai/test_migration_34.py -v` — Expected: PASS (2 testes).
- [ ] Commit: `git add scripts/migrations/motos_assai_34_estoque_pecas_pendencia.sql scripts/migrations/motos_assai_34_estoque_pecas_pendencia.py tests/motos_assai/test_migration_34.py && git commit -m "feat(motos_assai): migration 34 — 6 tabelas estoque/pecas/pendencia"`

---

### Task 2: Model `AssaiPeca`/`AssaiPecaModelo` + `peca_service`

**Files:**
- Create: `app/motos_assai/models/peca.py`
- Modify: `app/motos_assai/models/__init__.py`
- Create: `app/motos_assai/services/peca_service.py`
- Test: `tests/motos_assai/test_peca_service.py`

**Interfaces:**
- Consumes: tabelas `assai_peca`/`assai_peca_modelo` (Task 1), `AssaiModelo`.
- Produces: classes `AssaiPeca`, `AssaiPecaModelo`; service `peca_service` com `criar_peca`, `editar_peca`, `vincular_modelo`, `desvincular_modelo`, `listar_compativeis`, `listar`, exc `PecaError`. Usado por Task 4/5 (FK `peca_id`) e Task 8.

Steps:
- [ ] Escrever `tests/motos_assai/test_peca_service.py` que falha:
```python
import uuid
from decimal import Decimal

import pytest
from app import db
from app.motos_assai.models import AssaiModelo, AssaiPeca, AssaiPecaModelo
from app.motos_assai.services.peca_service import (
    criar_peca, editar_peca, vincular_modelo, desvincular_modelo,
    listar_compativeis, listar, PecaError,
)


def _nome():
    return f'PECA_{uuid.uuid4().hex[:8].upper()}'


def test_criar_peca_simples(app, admin_user):
    with app.app_context():
        p = criar_peca(nome=_nome(), codigo='C-1', custo_referencia='12.50',
                       operador_id=admin_user.id)
        assert p.id is not None
        assert p.ativo is True
        assert p.custo_referencia == Decimal('12.50')
        db.session.rollback()


def test_criar_peca_com_modelos(app, admin_user):
    with app.app_context():
        modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
        p = criar_peca(nome=_nome(), modelo_ids=[modelo.id], operador_id=admin_user.id)
        compat = listar_compativeis(modelo.id)
        assert p.id in [x.id for x in compat]
        db.session.rollback()


def test_vincular_desvincular_idempotente(app, admin_user):
    with app.app_context():
        modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
        p = criar_peca(nome=_nome(), operador_id=admin_user.id)
        vincular_modelo(peca_id=p.id, modelo_id=modelo.id)
        vincular_modelo(peca_id=p.id, modelo_id=modelo.id)  # idempotente
        assert AssaiPecaModelo.query.filter_by(peca_id=p.id, modelo_id=modelo.id).count() == 1
        desvincular_modelo(peca_id=p.id, modelo_id=modelo.id)
        assert AssaiPecaModelo.query.filter_by(peca_id=p.id, modelo_id=modelo.id).count() == 0
        db.session.rollback()


def test_editar_peca(app, admin_user):
    with app.app_context():
        p = criar_peca(nome=_nome(), operador_id=admin_user.id)
        editar_peca(peca_id=p.id, nome='NOVO NOME', ativo=False)
        assert p.nome == 'NOVO NOME'
        assert p.ativo is False
        db.session.rollback()


def test_criar_peca_sem_nome_falha(app, admin_user):
    with app.app_context():
        with pytest.raises(PecaError):
            criar_peca(nome='  ', operador_id=admin_user.id)
        db.session.rollback()


def test_listar_filtra_inativos_e_busca(app, admin_user):
    with app.app_context():
        nome = _nome()
        p = criar_peca(nome=nome, operador_id=admin_user.id)
        assert p.id in [x.id for x in listar(busca=nome)]
        editar_peca(peca_id=p.id, ativo=False)
        assert p.id not in [x.id for x in listar(ativo=True, busca=nome)]
        assert p.id in [x.id for x in listar(ativo=False, busca=nome)]
        db.session.rollback()
```
- [ ] Rodar e ver falhar: `source .venv/bin/activate && pytest tests/motos_assai/test_peca_service.py -v` — Expected: FAIL (ImportError: `AssaiPeca`/`peca_service`).
- [ ] Implementar `app/motos_assai/models/peca.py`:
```python
"""Catalogo de pecas + compatibilidade N:N por modelo (Spec 1 §4.1/§4.2).

Molde N:N: AssaiCompraMotochefePedido (UniqueConstraint).
"""
from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.utils.timezone import agora_brasil_naive


class AssaiPeca(db.Model):
    __tablename__ = 'assai_peca'

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(40), index=True)
    nome = db.Column(db.String(120), nullable=False)
    custo_referencia = db.Column(db.Numeric(15, 4))
    ativo = db.Column(db.Boolean, nullable=False, default=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)
    criado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    dados_extras = db.Column(JSONB, default=dict)

    modelos = db.relationship('AssaiPecaModelo', backref='peca',
                              cascade='all, delete-orphan', lazy='selectin')

    def __repr__(self):
        return f'<AssaiPeca #{self.id} {self.nome}>'


class AssaiPecaModelo(db.Model):
    __tablename__ = 'assai_peca_modelo'

    id = db.Column(db.Integer, primary_key=True)
    peca_id = db.Column(db.Integer, db.ForeignKey('assai_peca.id', ondelete='CASCADE'), nullable=False)
    modelo_id = db.Column(db.Integer, db.ForeignKey('assai_modelo.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('peca_id', 'modelo_id', name='uq_assai_peca_modelo'),
    )

    modelo = db.relationship('AssaiModelo', lazy='joined')

    def __repr__(self):
        return f'<AssaiPecaModelo peca={self.peca_id} modelo={self.modelo_id}>'
```
- [ ] Registrar no `app/motos_assai/models/__init__.py` — adicionar import após o bloco `from .devolucao import (...)`:
```python
from .peca import AssaiPeca, AssaiPecaModelo
```
e adicionar ao final da lista `__all__` (antes do `]` de fechamento):
```python
    'AssaiPeca', 'AssaiPecaModelo',
```
- [ ] Implementar `app/motos_assai/services/peca_service.py`:
```python
"""peca_service — catalogo de pecas e compatibilidade por modelo (Spec 1 §11).

`criar/vincular/...` fazem add+flush SEM commit (caller controla a transacao).
"""
from decimal import Decimal

from app import db
from app.motos_assai.models import AssaiModelo, AssaiPeca, AssaiPecaModelo
from app.utils.timezone import agora_brasil_naive


class PecaError(Exception):
    """Erro de dominio de peca_service."""


def criar_peca(*, nome, codigo=None, custo_referencia=None, modelo_ids=None, operador_id):
    if not nome or not nome.strip():
        raise PecaError('nome obrigatorio')
    peca = AssaiPeca(
        nome=nome.strip(),
        codigo=(codigo.strip() if codigo else None),
        custo_referencia=(Decimal(str(custo_referencia)) if custo_referencia is not None else None),
        ativo=True,
        criado_por_id=operador_id,
        criado_em=agora_brasil_naive(),
    )
    db.session.add(peca)
    db.session.flush()
    for mid in (modelo_ids or []):
        vincular_modelo(peca_id=peca.id, modelo_id=mid)
    db.session.flush()
    return peca


def editar_peca(*, peca_id, **campos):
    peca = AssaiPeca.query.get(peca_id)
    if not peca:
        raise PecaError(f'peca {peca_id} nao encontrada')
    for campo in ('nome', 'codigo', 'ativo'):
        if campo in campos:
            setattr(peca, campo, campos[campo])
    if 'custo_referencia' in campos:
        valor = campos['custo_referencia']
        peca.custo_referencia = Decimal(str(valor)) if valor is not None else None
    db.session.flush()
    return peca


def vincular_modelo(*, peca_id, modelo_id):
    existente = AssaiPecaModelo.query.filter_by(peca_id=peca_id, modelo_id=modelo_id).first()
    if existente:
        return existente
    if not AssaiPeca.query.get(peca_id):
        raise PecaError(f'peca {peca_id} nao encontrada')
    if not AssaiModelo.query.get(modelo_id):
        raise PecaError(f'modelo {modelo_id} nao encontrado')
    link = AssaiPecaModelo(peca_id=peca_id, modelo_id=modelo_id)
    db.session.add(link)
    db.session.flush()
    return link


def desvincular_modelo(*, peca_id, modelo_id):
    link = AssaiPecaModelo.query.filter_by(peca_id=peca_id, modelo_id=modelo_id).first()
    if link:
        db.session.delete(link)
        db.session.flush()
    return None


def listar_compativeis(modelo_id):
    return (
        AssaiPeca.query
        .join(AssaiPecaModelo, AssaiPecaModelo.peca_id == AssaiPeca.id)
        .filter(AssaiPecaModelo.modelo_id == modelo_id, AssaiPeca.ativo.is_(True))
        .order_by(AssaiPeca.nome)
        .all()
    )


def listar(*, ativo=True, busca=None):
    q = AssaiPeca.query
    if ativo is not None:
        q = q.filter(AssaiPeca.ativo.is_(ativo))
    if busca:
        like = f'%{busca}%'
        q = q.filter(db.or_(AssaiPeca.nome.ilike(like), AssaiPeca.codigo.ilike(like)))
    return q.order_by(AssaiPeca.nome).all()
```
- [ ] Rodar e ver passar: `source .venv/bin/activate && pytest tests/motos_assai/test_peca_service.py -v` — Expected: PASS (6 testes).
- [ ] Commit: `git add app/motos_assai/models/peca.py app/motos_assai/models/__init__.py app/motos_assai/services/peca_service.py tests/motos_assai/test_peca_service.py && git commit -m "feat(motos_assai): AssaiPeca + peca_service (catalogo + compatibilidade)"`

---

### Task 3: Model `AssaiPendencia` + constantes (model-only)

**Files:**
- Create: `app/motos_assai/models/pendencia.py`
- Modify: `app/motos_assai/models/__init__.py`
- Test: `tests/motos_assai/test_pendencia_model.py`

**Interfaces:**
- Consumes: tabela `assai_pendencia` (Task 1), `AssaiPeca` (Task 2 — FK `peca_id`).
- Produces: classe `AssaiPendencia`; constantes literais e sets `PENDENCIA_CATEGORIAS_VALIDAS`, `PENDENCIA_ORIGENS_VALIDAS`, `ORIGENS_FISICAS`, `PENDENCIA_FASES_VALIDAS`, `PENDENCIA_TRATATIVAS_VALIDAS` + relationship `pai`/`filhas`. Consumido por `pendencia_service` (Task 6/7) e `movimento_service.canibalizar` (Task 8).

Steps:
- [ ] Escrever `tests/motos_assai/test_pendencia_model.py` que falha:
```python
import uuid

from app import db
from app.motos_assai.models import (
    AssaiPendencia,
    PENDENCIA_CATEGORIA_REVISAO, PENDENCIA_CATEGORIA_AVARIA,
    PENDENCIA_ORIGEM_GALPAO, PENDENCIA_ORIGEM_DEVOLUCAO,
    PENDENCIA_CATEGORIAS_VALIDAS, PENDENCIA_ORIGENS_VALIDAS, ORIGENS_FISICAS,
    PENDENCIA_FASES_VALIDAS, PENDENCIA_TRATATIVAS_VALIDAS,
)


def _chassi():
    return f'TST_{uuid.uuid4().hex[:8].upper()}'


def test_sets_de_taxonomia():
    assert PENDENCIA_CATEGORIAS_VALIDAS == {
        'AVARIA', 'FALTA_PECA', 'REVISAO', 'VENDA', 'INDETERMINADA'}
    assert PENDENCIA_ORIGENS_VALIDAS == {
        'GALPAO', 'TRANSPORTE', 'POS_VENDA_CLIENTE', 'POS_VENDA_LOJA', 'DEVOLUCAO'}
    assert ORIGENS_FISICAS == {'GALPAO', 'TRANSPORTE', 'DEVOLUCAO'}
    assert PENDENCIA_FASES_VALIDAS == {'ABERTA', 'EM_TRATATIVA', 'AGUARDANDO_PECA'}
    assert PENDENCIA_TRATATIVAS_VALIDAS == {
        'USAR_ESTOQUE', 'USAR_OUTRA_MOTO', 'CONSERTAR', 'REVISAR'}


def test_criar_ficha_defaults(app, admin_user):
    with app.app_context():
        p = AssaiPendencia(
            chassi=_chassi(), categoria=PENDENCIA_CATEGORIA_AVARIA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Fio solto',
            aberta_por_id=admin_user.id,
        )
        db.session.add(p)
        db.session.flush()
        assert p.id is not None
        assert p.fase == 'ABERTA'
        assert p.retorno_fisico is False
        assert p.esta_aberta is True
        db.session.rollback()


def test_status_derivado(app, admin_user):
    with app.app_context():
        from app.utils.timezone import agora_brasil_naive
        p = AssaiPendencia(
            chassi=_chassi(), categoria=PENDENCIA_CATEGORIA_AVARIA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='X', aberta_por_id=admin_user.id,
        )
        db.session.add(p)
        db.session.flush()
        assert p.esta_aberta is True
        p.resolvida_em = agora_brasil_naive()
        db.session.flush()
        assert p.esta_aberta is False
        db.session.rollback()


def test_auto_relacao_pai_filhas(app, admin_user):
    with app.app_context():
        ch = _chassi()
        mae = AssaiPendencia(
            chassi=ch, categoria=PENDENCIA_CATEGORIA_REVISAO,
            origem=PENDENCIA_ORIGEM_DEVOLUCAO, descricao='Revisao devolucao',
            aberta_por_id=admin_user.id,
        )
        db.session.add(mae)
        db.session.flush()
        filha = AssaiPendencia(
            chassi=ch, categoria=PENDENCIA_CATEGORIA_AVARIA,
            origem=PENDENCIA_ORIGEM_DEVOLUCAO, descricao='Avaria achada na revisao',
            pendencia_pai_id=mae.id, aberta_por_id=admin_user.id,
        )
        db.session.add(filha)
        db.session.flush()
        db.session.refresh(mae)
        assert filha.pai.id == mae.id
        assert filha.id in [f.id for f in mae.filhas]
        db.session.rollback()
```
- [ ] Rodar e ver falhar: `source .venv/bin/activate && pytest tests/motos_assai/test_pendencia_model.py -v` — Expected: FAIL (ImportError `AssaiPendencia`).
- [ ] Implementar `app/motos_assai/models/pendencia.py`:
```python
"""AssaiPendencia — ficha de pendencia categorizada (Spec 1 §4.3/§5).

Molde AssaiDivergencia (status derivado de resolvida_em/cancelada_em, detalhes
JSONB). Validacao de categoria/origem/fase/tratativa por set Python no service
(sem CHECK no banco). Auto-relacao pai/filhas para REVISAO (D1).
"""
from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.utils.timezone import agora_brasil_naive


# Categorias
PENDENCIA_CATEGORIA_AVARIA = 'AVARIA'
PENDENCIA_CATEGORIA_FALTA_PECA = 'FALTA_PECA'
PENDENCIA_CATEGORIA_REVISAO = 'REVISAO'
PENDENCIA_CATEGORIA_VENDA = 'VENDA'
PENDENCIA_CATEGORIA_INDETERMINADA = 'INDETERMINADA'  # sentinela transitoria (backfill / pre-classificacao)
PENDENCIA_CATEGORIAS_VALIDAS = {
    PENDENCIA_CATEGORIA_AVARIA,
    PENDENCIA_CATEGORIA_FALTA_PECA,
    PENDENCIA_CATEGORIA_REVISAO,
    PENDENCIA_CATEGORIA_VENDA,
    PENDENCIA_CATEGORIA_INDETERMINADA,
}

# Origens
PENDENCIA_ORIGEM_GALPAO = 'GALPAO'
PENDENCIA_ORIGEM_TRANSPORTE = 'TRANSPORTE'
PENDENCIA_ORIGEM_POS_VENDA_CLIENTE = 'POS_VENDA_CLIENTE'
PENDENCIA_ORIGEM_POS_VENDA_LOJA = 'POS_VENDA_LOJA'
PENDENCIA_ORIGEM_DEVOLUCAO = 'DEVOLUCAO'
PENDENCIA_ORIGENS_VALIDAS = {
    PENDENCIA_ORIGEM_GALPAO,
    PENDENCIA_ORIGEM_TRANSPORTE,
    PENDENCIA_ORIGEM_POS_VENDA_CLIENTE,
    PENDENCIA_ORIGEM_POS_VENDA_LOJA,
    PENDENCIA_ORIGEM_DEVOLUCAO,
}
# origens que afetam o estado fisico da moto (emitem/compartilham PENDENTE)
ORIGENS_FISICAS = {
    PENDENCIA_ORIGEM_GALPAO,
    PENDENCIA_ORIGEM_TRANSPORTE,
    PENDENCIA_ORIGEM_DEVOLUCAO,
}

# Fases (informativa — nunca decide logica de estado da moto)
PENDENCIA_FASE_ABERTA = 'ABERTA'
PENDENCIA_FASE_EM_TRATATIVA = 'EM_TRATATIVA'
PENDENCIA_FASE_AGUARDANDO_PECA = 'AGUARDANDO_PECA'
PENDENCIA_FASES_VALIDAS = {
    PENDENCIA_FASE_ABERTA,
    PENDENCIA_FASE_EM_TRATATIVA,
    PENDENCIA_FASE_AGUARDANDO_PECA,
}

# Tratativas (acao que RESOLVE a ficha)
PENDENCIA_TRATATIVA_USAR_ESTOQUE = 'USAR_ESTOQUE'
PENDENCIA_TRATATIVA_USAR_OUTRA_MOTO = 'USAR_OUTRA_MOTO'
PENDENCIA_TRATATIVA_CONSERTAR = 'CONSERTAR'
PENDENCIA_TRATATIVA_REVISAR = 'REVISAR'
PENDENCIA_TRATATIVAS_VALIDAS = {
    PENDENCIA_TRATATIVA_USAR_ESTOQUE,
    PENDENCIA_TRATATIVA_USAR_OUTRA_MOTO,
    PENDENCIA_TRATATIVA_CONSERTAR,
    PENDENCIA_TRATATIVA_REVISAR,
}


class AssaiPendencia(db.Model):
    __tablename__ = 'assai_pendencia'

    id = db.Column(db.Integer, primary_key=True)
    chassi = db.Column(db.String(50), nullable=False, index=True)
    categoria = db.Column(db.String(20), nullable=False)
    origem = db.Column(db.String(20), nullable=False)
    tratativa = db.Column(db.String(40))
    fase = db.Column(db.String(20), nullable=False, default=PENDENCIA_FASE_ABERTA)
    retorno_fisico = db.Column(db.Boolean, nullable=False, default=False)
    descricao = db.Column(db.Text, nullable=False)

    pendencia_pai_id = db.Column(db.Integer, db.ForeignKey('assai_pendencia.id', ondelete='SET NULL'))
    evento_pendente_id = db.Column(db.Integer, db.ForeignKey('assai_moto_evento.id', ondelete='SET NULL'))
    peca_id = db.Column(db.Integer, db.ForeignKey('assai_peca.id', ondelete='SET NULL'))
    chassi_doador = db.Column(db.String(50))
    devolucao_item_id = db.Column(db.Integer, db.ForeignKey('assai_devolucao_item.id', ondelete='SET NULL'))
    pos_venda_ocorrencia_id = db.Column(db.Integer, db.ForeignKey('assai_pos_venda_ocorrencia.id', ondelete='SET NULL'))
    divergencia_origem_id = db.Column(db.Integer, db.ForeignKey('assai_divergencia.id', ondelete='SET NULL'))

    detalhes = db.Column(JSONB, default=dict)

    aberta_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)
    aberta_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    resolvida_em = db.Column(db.DateTime)
    resolvida_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    resolucao_descricao = db.Column(db.Text)
    cancelada_em = db.Column(db.DateTime)
    cancelada_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))

    filhas = db.relationship(
        'AssaiPendencia',
        backref=db.backref('pai', remote_side=[id]),
    )

    @property
    def esta_aberta(self):
        return self.resolvida_em is None and self.cancelada_em is None

    def __repr__(self):
        status = 'aberta' if self.esta_aberta else ('resolvida' if self.resolvida_em else 'cancelada')
        return f'<AssaiPendencia #{self.id} {self.categoria}/{self.origem} chassi={self.chassi} {status}>'
```
- [ ] Registrar no `app/motos_assai/models/__init__.py` — adicionar após o import de `peca`:
```python
from .pendencia import (
    AssaiPendencia,
    PENDENCIA_CATEGORIA_AVARIA, PENDENCIA_CATEGORIA_FALTA_PECA,
    PENDENCIA_CATEGORIA_REVISAO, PENDENCIA_CATEGORIA_VENDA,
    PENDENCIA_CATEGORIA_INDETERMINADA, PENDENCIA_CATEGORIAS_VALIDAS,
    PENDENCIA_ORIGEM_GALPAO, PENDENCIA_ORIGEM_TRANSPORTE,
    PENDENCIA_ORIGEM_POS_VENDA_CLIENTE, PENDENCIA_ORIGEM_POS_VENDA_LOJA,
    PENDENCIA_ORIGEM_DEVOLUCAO, PENDENCIA_ORIGENS_VALIDAS, ORIGENS_FISICAS,
    PENDENCIA_FASE_ABERTA, PENDENCIA_FASE_EM_TRATATIVA, PENDENCIA_FASE_AGUARDANDO_PECA,
    PENDENCIA_FASES_VALIDAS,
    PENDENCIA_TRATATIVA_USAR_ESTOQUE, PENDENCIA_TRATATIVA_USAR_OUTRA_MOTO,
    PENDENCIA_TRATATIVA_CONSERTAR, PENDENCIA_TRATATIVA_REVISAR,
    PENDENCIA_TRATATIVAS_VALIDAS,
)
```
e ao final de `__all__` (junto do bloco de peca):
```python
    'AssaiPendencia',
    'PENDENCIA_CATEGORIA_AVARIA', 'PENDENCIA_CATEGORIA_FALTA_PECA',
    'PENDENCIA_CATEGORIA_REVISAO', 'PENDENCIA_CATEGORIA_VENDA',
    'PENDENCIA_CATEGORIA_INDETERMINADA', 'PENDENCIA_CATEGORIAS_VALIDAS',
    'PENDENCIA_ORIGEM_GALPAO', 'PENDENCIA_ORIGEM_TRANSPORTE',
    'PENDENCIA_ORIGEM_POS_VENDA_CLIENTE', 'PENDENCIA_ORIGEM_POS_VENDA_LOJA',
    'PENDENCIA_ORIGEM_DEVOLUCAO', 'PENDENCIA_ORIGENS_VALIDAS', 'ORIGENS_FISICAS',
    'PENDENCIA_FASE_ABERTA', 'PENDENCIA_FASE_EM_TRATATIVA', 'PENDENCIA_FASE_AGUARDANDO_PECA',
    'PENDENCIA_FASES_VALIDAS',
    'PENDENCIA_TRATATIVA_USAR_ESTOQUE', 'PENDENCIA_TRATATIVA_USAR_OUTRA_MOTO',
    'PENDENCIA_TRATATIVA_CONSERTAR', 'PENDENCIA_TRATATIVA_REVISAR',
    'PENDENCIA_TRATATIVAS_VALIDAS',
```
- [ ] Rodar e ver passar: `source .venv/bin/activate && pytest tests/motos_assai/test_pendencia_model.py -v` — Expected: PASS (4 testes).
- [ ] Commit: `git add app/motos_assai/models/pendencia.py app/motos_assai/models/__init__.py tests/motos_assai/test_pendencia_model.py && git commit -m "feat(motos_assai): AssaiPendencia model + taxonomia (categoria/origem/fase/tratativa)"`

---

### Task 4: Model `AssaiEstoqueMovimento` + `movimento_service` (entrada/saldo/custo/descarte/ajuste)

**Files:**
- Create: `app/motos_assai/models/estoque_movimento.py`
- Modify: `app/motos_assai/models/__init__.py`
- Create: `app/motos_assai/services/movimento_service.py`
- Test: `tests/motos_assai/test_movimento_service.py`

**Interfaces:**
- Consumes: tabela `assai_estoque_movimento` (Task 1), `AssaiPeca` + `peca_service` (Task 2).
- Produces: classe `AssaiEstoqueMovimento`; sets `MOVIMENTO_*`/`MOVIMENTO_TIPOS_VALIDOS`; service `movimento_service` com `registrar_entrada`, `saldo`, `custo_medio`, `descartar`, `ajustar`, exc `EstoqueError`. `registrar_entrada` é consumido por `compra_peca_service.receber_item` (Task 5); `consumir`/`canibalizar` ficam para Task 8.

Steps:
- [ ] Escrever `tests/motos_assai/test_movimento_service.py` que falha:
```python
import uuid
from decimal import Decimal

import pytest
from app import db
from app.motos_assai.models import AssaiEstoqueMovimento, MOVIMENTO_ENTRADA, MOVIMENTO_DESCARTE
from app.motos_assai.services.peca_service import criar_peca
from app.motos_assai.services.movimento_service import (
    registrar_entrada, saldo, custo_medio, descartar, ajustar, EstoqueError,
)


def _nome():
    return f'PECA_{uuid.uuid4().hex[:8].upper()}'


def _peca(admin_user, custo_referencia=None):
    return criar_peca(nome=_nome(), custo_referencia=custo_referencia, operador_id=admin_user.id)


def test_entrada_soma_saldo_e_custo(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        registrar_entrada(peca_id=p.id, quantidade=10, custo_unitario='5.00', operador_id=admin_user.id)
        registrar_entrada(peca_id=p.id, quantidade=10, custo_unitario='7.00', operador_id=admin_user.id)
        assert saldo(p.id) == Decimal('20.000')
        assert custo_medio(p.id) == Decimal('6.0000')
        db.session.rollback()


def test_entrada_grava_linha_e_custo_total(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        mov = registrar_entrada(peca_id=p.id, quantidade=3, custo_unitario='4.00', operador_id=admin_user.id)
        assert mov.tipo == MOVIMENTO_ENTRADA
        assert mov.delta_almoxarifado == Decimal('3.000')
        assert mov.custo_total == Decimal('12.00')
        db.session.rollback()


def test_custo_medio_fallback_para_referencia(app, admin_user):
    with app.app_context():
        p = _peca(admin_user, custo_referencia='9.50')
        assert custo_medio(p.id) == Decimal('9.5000')
        db.session.rollback()


def test_custo_medio_zero_sem_dados(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        assert custo_medio(p.id) == Decimal('0')
        db.session.rollback()


def test_descartar_de_estoque_baixa_saldo(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        registrar_entrada(peca_id=p.id, quantidade=5, custo_unitario='2.00', operador_id=admin_user.id)
        d = descartar(peca_id=p.id, quantidade=2, operador_id=admin_user.id)
        assert d.tipo == MOVIMENTO_DESCARTE
        assert d.delta_almoxarifado == Decimal('-2.000')
        assert saldo(p.id) == Decimal('3.000')
        db.session.rollback()


def test_descartar_de_moto_nao_mexe_saldo(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        registrar_entrada(peca_id=p.id, quantidade=5, custo_unitario='2.00', operador_id=admin_user.id)
        d = descartar(peca_id=p.id, quantidade=1, operador_id=admin_user.id, chassi_origem='TST_X')
        assert d.delta_almoxarifado == Decimal('0.000')
        assert saldo(p.id) == Decimal('5.000')
        db.session.rollback()


def test_ajustar_positivo_e_negativo(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        ajustar(peca_id=p.id, delta=4, operador_id=admin_user.id, motivo='Contagem fisica')
        assert saldo(p.id) == Decimal('4.000')
        ajustar(peca_id=p.id, delta=-1, operador_id=admin_user.id, motivo='Correcao')
        assert saldo(p.id) == Decimal('3.000')
        db.session.rollback()


def test_entrada_quantidade_invalida_falha(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        with pytest.raises(EstoqueError):
            registrar_entrada(peca_id=p.id, quantidade=0, custo_unitario='1.00', operador_id=admin_user.id)
        db.session.rollback()
```
- [ ] Rodar e ver falhar: `source .venv/bin/activate && pytest tests/motos_assai/test_movimento_service.py -v` — Expected: FAIL (ImportError `AssaiEstoqueMovimento`/`movimento_service`).
- [ ] Implementar `app/motos_assai/models/estoque_movimento.py`:
```python
"""AssaiEstoqueMovimento — ledger append-only de pecas (Spec 1 §4.4/§5).

Saldo = SUM(delta_almoxarifado) por peca_id. Correcao = nova linha AJUSTE
(nunca UPDATE/DELETE). Custo congelado na linha (custo_unitario/custo_total).
"""
from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.utils.timezone import agora_brasil_naive


MOVIMENTO_ENTRADA = 'ENTRADA'
MOVIMENTO_CONSUMO = 'CONSUMO'
MOVIMENTO_CANIBALIZACAO = 'CANIBALIZACAO'
MOVIMENTO_DESCARTE = 'DESCARTE'
MOVIMENTO_AJUSTE = 'AJUSTE'
MOVIMENTO_TIPOS_VALIDOS = {
    MOVIMENTO_ENTRADA,
    MOVIMENTO_CONSUMO,
    MOVIMENTO_CANIBALIZACAO,
    MOVIMENTO_DESCARTE,
    MOVIMENTO_AJUSTE,
}


class AssaiEstoqueMovimento(db.Model):
    __tablename__ = 'assai_estoque_movimento'

    id = db.Column(db.BigInteger, primary_key=True)
    peca_id = db.Column(db.Integer, db.ForeignKey('assai_peca.id', ondelete='RESTRICT'),
                        nullable=False, index=True)
    tipo = db.Column(db.String(40), nullable=False)
    quantidade = db.Column(db.Numeric(15, 3), nullable=False)
    delta_almoxarifado = db.Column(db.Numeric(15, 3), nullable=False, default=0)
    chassi_origem = db.Column(db.String(50), index=True)
    chassi_destino = db.Column(db.String(50), index=True)
    pendencia_id = db.Column(db.Integer, db.ForeignKey('assai_pendencia.id', ondelete='SET NULL'), index=True)
    compra_item_id = db.Column(db.Integer, db.ForeignKey('assai_peca_compra_item.id', ondelete='SET NULL'))
    custo_unitario = db.Column(db.Numeric(15, 4))
    custo_total = db.Column(db.Numeric(15, 2))
    receita_unitaria = db.Column(db.Numeric(15, 4))
    receita_total = db.Column(db.Numeric(15, 2))
    operador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    ocorrido_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)
    observacao = db.Column(db.Text)
    dados_extras = db.Column(JSONB, default=dict)

    peca = db.relationship('AssaiPeca', lazy='joined')

    def __repr__(self):
        return f'<AssaiEstoqueMovimento #{self.id} {self.tipo} peca={self.peca_id} delta={self.delta_almoxarifado}>'
```
- [ ] Registrar no `app/motos_assai/models/__init__.py` — adicionar import após o de `pendencia`:
```python
from .estoque_movimento import (
    AssaiEstoqueMovimento,
    MOVIMENTO_ENTRADA, MOVIMENTO_CONSUMO, MOVIMENTO_CANIBALIZACAO,
    MOVIMENTO_DESCARTE, MOVIMENTO_AJUSTE, MOVIMENTO_TIPOS_VALIDOS,
)
```
e em `__all__`:
```python
    'AssaiEstoqueMovimento',
    'MOVIMENTO_ENTRADA', 'MOVIMENTO_CONSUMO', 'MOVIMENTO_CANIBALIZACAO',
    'MOVIMENTO_DESCARTE', 'MOVIMENTO_AJUSTE', 'MOVIMENTO_TIPOS_VALIDOS',
```
- [ ] Implementar `app/motos_assai/services/movimento_service.py`:
```python
"""movimento_service — ledger de estoque de pecas (Spec 1 §11/§8).

Custeio: media movel ponderada por peca, custo congelado por movimento.
add+flush SEM commit. consumir/canibalizar ficam na Task 8 (este arquivo
cobre entrada/saldo/custo_medio/descartar/ajustar).
"""
from decimal import Decimal

from sqlalchemy import func

from app import db
from app.motos_assai.models import (
    AssaiPeca, AssaiEstoqueMovimento,
    MOVIMENTO_ENTRADA, MOVIMENTO_DESCARTE, MOVIMENTO_AJUSTE,
)
from app.utils.json_helpers import sanitize_for_json
from app.utils.timezone import agora_brasil_naive


class EstoqueError(Exception):
    """Erro de dominio de movimento_service."""


def _decimal(valor, campo):
    try:
        return Decimal(str(valor))
    except Exception as exc:  # noqa: BLE001
        raise EstoqueError(f'{campo} invalido: {valor!r}') from exc


def _exigir_peca(peca_id):
    peca = AssaiPeca.query.get(peca_id)
    if not peca:
        raise EstoqueError(f'peca {peca_id} nao encontrada')
    return peca


def saldo(peca_id):
    total = db.session.query(
        func.coalesce(func.sum(AssaiEstoqueMovimento.delta_almoxarifado), 0)
    ).filter(AssaiEstoqueMovimento.peca_id == peca_id).scalar()
    return Decimal(total)


def custo_medio(peca_id):
    """Media movel ponderada: SUM(delta*custo)/SUM(delta) nas linhas com custo.

    Guarda de divisao por zero (Spec §8): se SUM(delta) <= 0 -> fallback
    custo_referencia -> ultimo custo de ENTRADA -> 0.
    """
    soma_valor, soma_delta = db.session.query(
        func.coalesce(func.sum(
            AssaiEstoqueMovimento.delta_almoxarifado * AssaiEstoqueMovimento.custo_unitario), 0),
        func.coalesce(func.sum(AssaiEstoqueMovimento.delta_almoxarifado), 0),
    ).filter(
        AssaiEstoqueMovimento.peca_id == peca_id,
        AssaiEstoqueMovimento.custo_unitario.isnot(None),
    ).one()

    if soma_delta and Decimal(soma_delta) > 0:
        return (Decimal(soma_valor) / Decimal(soma_delta)).quantize(Decimal('0.0001'))

    peca = AssaiPeca.query.get(peca_id)
    if peca and peca.custo_referencia is not None:
        return Decimal(peca.custo_referencia).quantize(Decimal('0.0001'))

    ultima = (
        AssaiEstoqueMovimento.query
        .filter_by(peca_id=peca_id, tipo=MOVIMENTO_ENTRADA)
        .filter(AssaiEstoqueMovimento.custo_unitario.isnot(None))
        .order_by(AssaiEstoqueMovimento.id.desc())
        .first()
    )
    if ultima and ultima.custo_unitario is not None:
        return Decimal(ultima.custo_unitario).quantize(Decimal('0.0001'))
    return Decimal('0')


def registrar_entrada(*, peca_id, quantidade, custo_unitario, operador_id,
                      compra_item_id=None, recebimento_ref=None):
    q = _decimal(quantidade, 'quantidade')
    if q <= 0:
        raise EstoqueError('quantidade deve ser > 0')
    cu = _decimal(custo_unitario, 'custo_unitario')
    if cu < 0:
        raise EstoqueError('custo_unitario nao pode ser negativo')
    _exigir_peca(peca_id)

    dados = {}
    if recebimento_ref:
        dados['recebimento_ref'] = recebimento_ref

    mov = AssaiEstoqueMovimento(
        peca_id=peca_id,
        tipo=MOVIMENTO_ENTRADA,
        quantidade=q,
        delta_almoxarifado=q,
        compra_item_id=compra_item_id,
        custo_unitario=cu,
        custo_total=(q * cu).quantize(Decimal('0.01')),
        operador_id=operador_id,
        ocorrido_em=agora_brasil_naive(),
        dados_extras=sanitize_for_json(dados),
    )
    db.session.add(mov)
    db.session.flush()
    return mov


def descartar(*, peca_id, quantidade, operador_id, chassi_origem=None, pendencia_id=None):
    """DESCARTE. chassi_origem definido => peca veio de uma moto (nunca foi saldo,
    delta 0); sem chassi_origem => baixa de saldo do almoxarifado (delta -qtd)."""
    q = _decimal(quantidade, 'quantidade')
    if q <= 0:
        raise EstoqueError('quantidade deve ser > 0')
    _exigir_peca(peca_id)

    delta = Decimal('0') if chassi_origem else -q
    cu = custo_medio(peca_id)
    mov = AssaiEstoqueMovimento(
        peca_id=peca_id,
        tipo=MOVIMENTO_DESCARTE,
        quantidade=q,
        delta_almoxarifado=delta,
        chassi_origem=(chassi_origem.strip().upper() if chassi_origem else None),
        pendencia_id=pendencia_id,
        custo_unitario=cu,
        custo_total=(q * cu).quantize(Decimal('0.01')),
        operador_id=operador_id,
        ocorrido_em=agora_brasil_naive(),
    )
    db.session.add(mov)
    db.session.flush()
    return mov


def ajustar(*, peca_id, delta, operador_id, motivo, custo_unitario=None):
    d = _decimal(delta, 'delta')
    if d == 0:
        raise EstoqueError('delta nao pode ser zero')
    if not motivo or len(motivo.strip()) < 3:
        raise EstoqueError('motivo obrigatorio (>=3 chars)')
    _exigir_peca(peca_id)

    cu = _decimal(custo_unitario, 'custo_unitario') if custo_unitario is not None else custo_medio(peca_id)
    mag = abs(d)
    mov = AssaiEstoqueMovimento(
        peca_id=peca_id,
        tipo=MOVIMENTO_AJUSTE,
        quantidade=mag,
        delta_almoxarifado=d,
        custo_unitario=cu,
        custo_total=(mag * cu).quantize(Decimal('0.01')),
        operador_id=operador_id,
        observacao=motivo.strip(),
        ocorrido_em=agora_brasil_naive(),
    )
    db.session.add(mov)
    db.session.flush()
    return mov
```
- [ ] Rodar e ver passar: `source .venv/bin/activate && pytest tests/motos_assai/test_movimento_service.py -v` — Expected: PASS (8 testes).
- [ ] Commit: `git add app/motos_assai/models/estoque_movimento.py app/motos_assai/models/__init__.py app/motos_assai/services/movimento_service.py tests/motos_assai/test_movimento_service.py && git commit -m "feat(motos_assai): AssaiEstoqueMovimento + movimento_service (entrada/saldo/custo/descarte/ajuste)"`

---

### Task 5: Model `AssaiPecaCompra`/`Item` + `compra_peca_service`

**Files:**
- Create: `app/motos_assai/models/peca_compra.py`
- Modify: `app/motos_assai/models/__init__.py`
- Create: `app/motos_assai/services/compra_peca_service.py`
- Test: `tests/motos_assai/test_compra_peca_service.py`

**Interfaces:**
- Consumes: tabelas `assai_peca_compra`/`assai_peca_compra_item` (Task 1), `AssaiPeca` + `peca_service` (Task 2), `movimento_service.registrar_entrada` + `saldo` (Task 4).
- Produces: classes `AssaiPecaCompra`, `AssaiPecaCompraItem`; sets `COMPRA_PECA_TIPOS_VALIDOS`/`COMPRA_PECA_STATUS_VALIDOS`; service `compra_peca_service` com `criar_compra`, `adicionar_item`, `receber_item`, `cancelar_compra`, `_gerar_numero`, exc `CompraPecaError`. `criar_compra`/`adicionar_item` são reusados por `pendencia_service.solicitar_compra` (Task 6/7).

Steps:
- [ ] Escrever `tests/motos_assai/test_compra_peca_service.py` que falha:
```python
import re
import uuid
from decimal import Decimal

import pytest
from app import db
from app.motos_assai.models import (
    AssaiPecaCompra, AssaiPecaCompraItem,
    COMPRA_PECA_TIPO_COMPRA, COMPRA_PECA_TIPO_GARANTIA,
    COMPRA_PECA_STATUS_ABERTA, COMPRA_PECA_STATUS_PARCIAL,
    COMPRA_PECA_STATUS_RECEBIDA, COMPRA_PECA_STATUS_CANCELADA,
)
from app.motos_assai.services.peca_service import criar_peca
from app.motos_assai.services.movimento_service import saldo
from app.motos_assai.services.compra_peca_service import (
    criar_compra, adicionar_item, receber_item, cancelar_compra, CompraPecaError,
)


def _peca(admin_user):
    return criar_peca(nome=f'PECA_{uuid.uuid4().hex[:8].upper()}', operador_id=admin_user.id)


def test_criar_compra_gera_numero(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        c = criar_compra(tipo=COMPRA_PECA_TIPO_COMPRA,
                         itens=[{'peca_id': p.id, 'quantidade': 5}],
                         operador_id=admin_user.id)
        assert re.match(r'^PC-\d{4}-\d{4}$', c.numero)
        assert c.status == COMPRA_PECA_STATUS_ABERTA
        assert c.tipo == COMPRA_PECA_TIPO_COMPRA
        assert len(c.itens) == 1
        db.session.rollback()


def test_numeros_sao_unicos(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        c1 = criar_compra(tipo=COMPRA_PECA_TIPO_GARANTIA,
                          itens=[{'peca_id': p.id, 'quantidade': 1}], operador_id=admin_user.id)
        c2 = criar_compra(tipo=COMPRA_PECA_TIPO_GARANTIA,
                          itens=[{'peca_id': p.id, 'quantidade': 1}], operador_id=admin_user.id)
        assert c1.numero != c2.numero
        db.session.rollback()


def test_receber_item_parcial_depois_total(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        c = criar_compra(tipo=COMPRA_PECA_TIPO_COMPRA,
                         itens=[{'peca_id': p.id, 'quantidade': 10}], operador_id=admin_user.id)
        item = c.itens[0]
        receber_item(compra_item_id=item.id, quantidade=4, custo_unitario='3.00', operador_id=admin_user.id)
        assert c.status == COMPRA_PECA_STATUS_PARCIAL
        assert item.quantidade_recebida == Decimal('4.000')
        assert saldo(p.id) == Decimal('4.000')
        receber_item(compra_item_id=item.id, quantidade=6, custo_unitario='3.00', operador_id=admin_user.id)
        assert c.status == COMPRA_PECA_STATUS_RECEBIDA
        assert saldo(p.id) == Decimal('10.000')
        db.session.rollback()


def test_adicionar_item(app, admin_user):
    with app.app_context():
        p1 = _peca(admin_user)
        p2 = _peca(admin_user)
        c = criar_compra(tipo=COMPRA_PECA_TIPO_COMPRA,
                         itens=[{'peca_id': p1.id, 'quantidade': 1}], operador_id=admin_user.id)
        adicionar_item(compra_id=c.id, peca_id=p2.id, quantidade=2, custo_estimado='8.00')
        assert len(c.itens) == 2
        db.session.rollback()


def test_cancelar_compra(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        c = criar_compra(tipo=COMPRA_PECA_TIPO_COMPRA,
                         itens=[{'peca_id': p.id, 'quantidade': 1}], operador_id=admin_user.id)
        cancelar_compra(compra_id=c.id, operador_id=admin_user.id)
        assert c.status == COMPRA_PECA_STATUS_CANCELADA
        cancelar_compra(compra_id=c.id, operador_id=admin_user.id)  # idempotente
        assert c.status == COMPRA_PECA_STATUS_CANCELADA
        db.session.rollback()


def test_criar_compra_tipo_invalido_falha(app, admin_user):
    with app.app_context():
        p = _peca(admin_user)
        with pytest.raises(CompraPecaError):
            criar_compra(tipo='XPTO', itens=[{'peca_id': p.id, 'quantidade': 1}],
                         operador_id=admin_user.id)
        db.session.rollback()
```
- [ ] Rodar e ver falhar: `source .venv/bin/activate && pytest tests/motos_assai/test_compra_peca_service.py -v` — Expected: FAIL (ImportError `AssaiPecaCompra`/`compra_peca_service`).
- [ ] Implementar `app/motos_assai/models/peca_compra.py`:
```python
"""AssaiPecaCompra (cabecalho) + AssaiPecaCompraItem (Spec 1 §4.5/§4.6).

Molde AssaiCompraMotochefe: numero 'PC-AAAA-NNNN', tipo no cabecalho (O3),
status default ABERTA, relationship itens cascade all,delete-orphan selectin.
"""
from sqlalchemy.dialects.postgresql import JSONB

from app import db
from app.utils.timezone import agora_brasil_naive


COMPRA_PECA_TIPO_GARANTIA = 'GARANTIA'
COMPRA_PECA_TIPO_COMPRA = 'COMPRA'
COMPRA_PECA_TIPOS_VALIDOS = {COMPRA_PECA_TIPO_GARANTIA, COMPRA_PECA_TIPO_COMPRA}

COMPRA_PECA_STATUS_ABERTA = 'ABERTA'
COMPRA_PECA_STATUS_PARCIAL = 'PARCIAL'
COMPRA_PECA_STATUS_RECEBIDA = 'RECEBIDA'
COMPRA_PECA_STATUS_CANCELADA = 'CANCELADA'
COMPRA_PECA_STATUS_VALIDOS = {
    COMPRA_PECA_STATUS_ABERTA,
    COMPRA_PECA_STATUS_PARCIAL,
    COMPRA_PECA_STATUS_RECEBIDA,
    COMPRA_PECA_STATUS_CANCELADA,
}


class AssaiPecaCompra(db.Model):
    __tablename__ = 'assai_peca_compra'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(20), unique=True, nullable=False)
    tipo = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(30), nullable=False, default=COMPRA_PECA_STATUS_ABERTA)
    fornecedor = db.Column(db.String(120), nullable=False, default='MOTOCHEFE')
    criada_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)
    criada_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    observacao = db.Column(db.Text)
    dados_extras = db.Column(JSONB, default=dict)

    itens = db.relationship('AssaiPecaCompraItem', backref='compra',
                            cascade='all, delete-orphan', lazy='selectin')

    def __repr__(self):
        return f'<AssaiPecaCompra {self.numero} {self.tipo} {self.status}>'


class AssaiPecaCompraItem(db.Model):
    __tablename__ = 'assai_peca_compra_item'

    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey('assai_peca_compra.id', ondelete='CASCADE'),
                          nullable=False, index=True)
    peca_id = db.Column(db.Integer, db.ForeignKey('assai_peca.id', ondelete='RESTRICT'), nullable=False)
    quantidade = db.Column(db.Numeric(15, 3), nullable=False)
    quantidade_recebida = db.Column(db.Numeric(15, 3), nullable=False, default=0)
    custo_estimado = db.Column(db.Numeric(15, 4))
    pendencia_id = db.Column(db.Integer, db.ForeignKey('assai_pendencia.id', ondelete='SET NULL'))
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_brasil_naive)

    peca = db.relationship('AssaiPeca', lazy='joined')

    def __repr__(self):
        return f'<AssaiPecaCompraItem #{self.id} compra={self.compra_id} peca={self.peca_id}>'
```
- [ ] Registrar no `app/motos_assai/models/__init__.py` — adicionar import após o de `estoque_movimento`:
```python
from .peca_compra import (
    AssaiPecaCompra, AssaiPecaCompraItem,
    COMPRA_PECA_TIPO_GARANTIA, COMPRA_PECA_TIPO_COMPRA, COMPRA_PECA_TIPOS_VALIDOS,
    COMPRA_PECA_STATUS_ABERTA, COMPRA_PECA_STATUS_PARCIAL,
    COMPRA_PECA_STATUS_RECEBIDA, COMPRA_PECA_STATUS_CANCELADA,
    COMPRA_PECA_STATUS_VALIDOS,
)
```
e em `__all__`:
```python
    'AssaiPecaCompra', 'AssaiPecaCompraItem',
    'COMPRA_PECA_TIPO_GARANTIA', 'COMPRA_PECA_TIPO_COMPRA', 'COMPRA_PECA_TIPOS_VALIDOS',
    'COMPRA_PECA_STATUS_ABERTA', 'COMPRA_PECA_STATUS_PARCIAL',
    'COMPRA_PECA_STATUS_RECEBIDA', 'COMPRA_PECA_STATUS_CANCELADA',
    'COMPRA_PECA_STATUS_VALIDOS',
```
- [ ] Implementar `app/motos_assai/services/compra_peca_service.py`:
```python
"""compra_peca_service — pedido de compra de peca (GARANTIA/COMPRA) (Spec 1 §11).

Numeracao 'PC-AAAA-NNNN' via sequence/retry com SAVEPOINT (nunca MAX()+1, §13.4).
receber_item alimenta o ledger (registrar_entrada) e recalcula status do cabecalho.
add+flush SEM commit.
"""
from decimal import Decimal

from sqlalchemy.exc import IntegrityError

from app import db
from app.motos_assai.models import (
    AssaiPeca, AssaiPecaCompra, AssaiPecaCompraItem,
    COMPRA_PECA_TIPOS_VALIDOS,
    COMPRA_PECA_STATUS_ABERTA, COMPRA_PECA_STATUS_PARCIAL,
    COMPRA_PECA_STATUS_RECEBIDA, COMPRA_PECA_STATUS_CANCELADA,
)
from app.motos_assai.services import movimento_service
from app.utils.timezone import agora_brasil_naive

_MAX_TENTATIVAS_NUMERO = 25


class CompraPecaError(Exception):
    """Erro de dominio de compra_peca_service."""


def _decimal(valor, campo):
    try:
        return Decimal(str(valor))
    except Exception as exc:  # noqa: BLE001
        raise CompraPecaError(f'{campo} invalido: {valor!r}') from exc


def _gerar_numero(ano=None):
    ano = ano or agora_brasil_naive().year
    prefixo = f'PC-{ano}-'
    base = AssaiPecaCompra.query.filter(AssaiPecaCompra.numero.like(f'{prefixo}%')).count()
    return prefixo, base


def criar_compra(*, tipo, itens, operador_id, fornecedor='MOTOCHEFE'):
    if tipo not in COMPRA_PECA_TIPOS_VALIDOS:
        raise CompraPecaError(
            f'tipo invalido: {tipo}. Validos: {sorted(COMPRA_PECA_TIPOS_VALIDOS)}')
    if not itens:
        raise CompraPecaError('pelo menos 1 item e obrigatorio')

    prefixo, base = _gerar_numero()
    compra = None
    for tentativa in range(_MAX_TENTATIVAS_NUMERO):
        numero = f'{prefixo}{base + 1 + tentativa:04d}'
        try:
            with db.session.begin_nested():
                compra = AssaiPecaCompra(
                    numero=numero, tipo=tipo, status=COMPRA_PECA_STATUS_ABERTA,
                    fornecedor=fornecedor, criada_por_id=operador_id,
                    criada_em=agora_brasil_naive(),
                )
                db.session.add(compra)
                db.session.flush()
            break
        except IntegrityError:
            compra = None
            continue
    if compra is None:
        raise CompraPecaError('nao foi possivel gerar numero unico para a compra')

    for it in itens:
        adicionar_item(
            compra_id=compra.id,
            peca_id=it['peca_id'],
            quantidade=it['quantidade'],
            custo_estimado=it.get('custo_estimado'),
            pendencia_id=it.get('pendencia_id'),
        )
    db.session.flush()
    return compra


def adicionar_item(*, compra_id, peca_id, quantidade, custo_estimado=None, pendencia_id=None):
    compra = AssaiPecaCompra.query.get(compra_id)
    if not compra:
        raise CompraPecaError(f'compra {compra_id} nao encontrada')
    if compra.status == COMPRA_PECA_STATUS_CANCELADA:
        raise CompraPecaError('compra cancelada nao aceita novos itens')
    if not AssaiPeca.query.get(peca_id):
        raise CompraPecaError(f'peca {peca_id} nao encontrada')
    q = _decimal(quantidade, 'quantidade')
    if q <= 0:
        raise CompraPecaError('quantidade deve ser > 0')

    item = AssaiPecaCompraItem(
        compra_id=compra.id,
        peca_id=peca_id,
        quantidade=q,
        quantidade_recebida=Decimal('0'),
        custo_estimado=(_decimal(custo_estimado, 'custo_estimado') if custo_estimado is not None else None),
        pendencia_id=pendencia_id,
        criado_em=agora_brasil_naive(),
    )
    db.session.add(item)
    db.session.flush()
    return item


def receber_item(*, compra_item_id, quantidade, custo_unitario, operador_id):
    item = AssaiPecaCompraItem.query.get(compra_item_id)
    if not item:
        raise CompraPecaError(f'item de compra {compra_item_id} nao encontrado')
    compra = item.compra
    if compra.status == COMPRA_PECA_STATUS_CANCELADA:
        raise CompraPecaError('compra cancelada nao aceita recebimento')
    q = _decimal(quantidade, 'quantidade')
    if q <= 0:
        raise CompraPecaError('quantidade deve ser > 0')

    mov = movimento_service.registrar_entrada(
        peca_id=item.peca_id,
        quantidade=q,
        custo_unitario=custo_unitario,
        operador_id=operador_id,
        compra_item_id=item.id,
    )
    item.quantidade_recebida = Decimal(item.quantidade_recebida) + q
    _recalcular_status(compra)
    db.session.flush()
    return mov


def cancelar_compra(*, compra_id, operador_id):
    compra = AssaiPecaCompra.query.get(compra_id)
    if not compra:
        raise CompraPecaError(f'compra {compra_id} nao encontrada')
    if compra.status == COMPRA_PECA_STATUS_CANCELADA:
        return compra  # idempotente
    if compra.status == COMPRA_PECA_STATUS_RECEBIDA:
        raise CompraPecaError('compra ja recebida nao pode ser cancelada')
    compra.status = COMPRA_PECA_STATUS_CANCELADA
    db.session.flush()
    return compra


def _recalcular_status(compra):
    if compra.status == COMPRA_PECA_STATUS_CANCELADA:
        return
    total = Decimal('0')
    recebido = Decimal('0')
    for it in compra.itens:
        total += Decimal(it.quantidade)
        recebido += Decimal(it.quantidade_recebida)
    if recebido <= 0:
        compra.status = COMPRA_PECA_STATUS_ABERTA
    elif recebido < total:
        compra.status = COMPRA_PECA_STATUS_PARCIAL
    else:
        compra.status = COMPRA_PECA_STATUS_RECEBIDA
```
- [ ] Rodar e ver passar: `source .venv/bin/activate && pytest tests/motos_assai/test_compra_peca_service.py -v` — Expected: PASS (6 testes).
- [ ] Rodar a suíte da faixa para garantir que nada quebrou: `source .venv/bin/activate && pytest tests/motos_assai/test_migration_34.py tests/motos_assai/test_peca_service.py tests/motos_assai/test_pendencia_model.py tests/motos_assai/test_movimento_service.py tests/motos_assai/test_compra_peca_service.py -v` — Expected: PASS (26 testes).
- [ ] Commit: `git add app/motos_assai/models/peca_compra.py app/motos_assai/models/__init__.py app/motos_assai/services/compra_peca_service.py tests/motos_assai/test_compra_peca_service.py && git commit -m "feat(motos_assai): AssaiPecaCompra + compra_peca_service (numero PC-AAAA-NNNN, receber_item)"`

---

I have everything I need. Here is my section of the plan (Tasks 6-8).

---

### Task 6: Núcleo da pendência — `abrir_pendencia` + acoplamento com o evento PENDENTE

**Files:**
- Modify: `app/motos_assai/services/pendencia_service.py` (adiciona funções de escrita ao módulo que hoje só tem leitura; NÃO remove `listar_abertas`/`listar_historico_resolvidas`/etc.)
- Test: `tests/motos_assai/test_pendencia_abrir.py` (criar)

**Interfaces:**
- **Consumes** (faixa A — models/migration 34 já aplicada local): `AssaiPendencia`, `AssaiMotoEvento`, constantes `PENDENCIA_CATEGORIA_*`/`PENDENCIA_ORIGEM_*`/`PENDENCIA_CATEGORIAS_VALIDAS`/`PENDENCIA_ORIGENS_VALIDAS`/`ORIGENS_FISICAS`, `EVENTO_PENDENTE`, `EVENTO_FATURADA`. Existentes: `emitir_evento`, `status_efetivo` (`moto_evento_service`), `sanitize_for_json`, `agora_brasil_naive`.
- **Produces** (Tasks 7-8 e Spec 2 dependem): `pendencia_service.PendenciaError`, `abrir_pendencia(...)`, `_get_or_emit_pendente_event(chassi, operador_id) -> int`, `count_fisicas_abertas(chassi) -> int`, `afeta_estado_moto(p) -> bool`.

**Steps:**

- [ ] Criar `tests/motos_assai/test_pendencia_abrir.py` com o teste que falha (import + 1º caso):
```python
import uuid
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiMotoEvento, AssaiPendencia,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE, EVENTO_FATURADA,
    PENDENCIA_CATEGORIA_FALTA_PECA, PENDENCIA_CATEGORIA_REVISAO,
    PENDENCIA_ORIGEM_GALPAO, PENDENCIA_ORIGEM_POS_VENDA_LOJA,
    PENDENCIA_ORIGEM_POS_VENDA_CLIENTE,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo
from app.motos_assai.services.pendencia_service import (
    abrir_pendencia, count_fisicas_abertas, afeta_estado_moto, PendenciaError,
)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _moto(chassi, admin_user, estado=EVENTO_MONTADA):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    moto = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA')
    db.session.add(moto)
    db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, admin_user.id)
    if estado != EVENTO_ESTOQUE:
        emitir_evento(chassi, estado, admin_user.id)
    db.session.flush()
    return moto


def _conta_pendentes(chassi):
    return AssaiMotoEvento.query.filter_by(chassi=chassi, tipo=EVENTO_PENDENTE).count()


def test_pendencia_fisica_emite_pendente(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta retrovisor',
            operador_id=admin_user.id,
        )
        assert ficha.evento_pendente_id is not None
        assert afeta_estado_moto(ficha) is True
        assert status_efetivo(chassi) == EVENTO_PENDENTE
        assert _conta_pendentes(chassi) == 1
        db.session.rollback()
```

- [ ] Rodar e ver falhar: `source .venv/bin/activate && pytest tests/motos_assai/test_pendencia_abrir.py::test_pendencia_fisica_emite_pendente -v` — **Expected: FAIL** (`ImportError: cannot import name 'abrir_pendencia'`).

- [ ] Em `app/motos_assai/services/pendencia_service.py`, adicionar os imports abaixo logo após o bloco de import existente (linha ~25, após o `from app.motos_assai.models import (...)`):
```python
from sqlalchemy import or_
from app.utils.json_helpers import sanitize_for_json
from app.utils.timezone import agora_brasil_naive
from app.motos_assai.models import (
    AssaiPendencia,
    EVENTO_MONTADA,
    PENDENCIA_CATEGORIAS_VALIDAS, PENDENCIA_ORIGENS_VALIDAS, ORIGENS_FISICAS,
    PENDENCIA_TRATATIVAS_VALIDAS, PENDENCIA_FASE_AGUARDANDO_PECA,
)
from app.motos_assai.services.moto_evento_service import emitir_evento
```

- [ ] No mesmo arquivo, anexar ao final a classe de exceção, o predicado físico, o helper de evento, a contagem e `abrir_pendencia`:
```python
# ===========================================================================
# Escrita: ciclo de vida da ficha de pendencia (Spec 1 — back-end)
# ===========================================================================


class PendenciaError(Exception):
    """Erro de dominio de pendencia_service (escrita)."""


def afeta_estado_moto(p) -> bool:
    """Predicado fisico (derivado, nao-coluna): a ficha trava o estado da moto?

    Fisica  => origem em ORIGENS_FISICAS, OU veio de devolucao (NFd), OU a moto
    retornou fisicamente sem NFd (retorno_fisico). So fichas fisicas emitem/
    compartilham o evento PENDENTE.
    """
    return (
        (p.origem in ORIGENS_FISICAS)
        or (p.devolucao_item_id is not None)
        or bool(p.retorno_fisico)
    )


def _get_or_emit_pendente_event(chassi: str, operador_id: int) -> int:
    """Reusa o PENDENTE vivo do chassi (D1: 1 evento por chassi) ou emite um novo.

    DEVE rodar sob pg_advisory_xact_lock(hashtext(chassi)) — garantido pelos
    callers (abrir_pendencia). Uma ficha so recebe evento_pendente_id quando e
    fisica, logo `evento_pendente_id IS NOT NULL` ja implica ficha fisica.
    """
    existente = (
        AssaiPendencia.query
        .filter(
            AssaiPendencia.chassi == chassi,
            AssaiPendencia.evento_pendente_id.isnot(None),
            AssaiPendencia.resolvida_em.is_(None),
            AssaiPendencia.cancelada_em.is_(None),
        )
        .first()
    )
    if existente is not None:
        return existente.evento_pendente_id
    ev = emitir_evento(chassi, EVENTO_PENDENTE, operador_id=operador_id)
    return ev.id


def count_fisicas_abertas(chassi: str) -> int:
    """Conta fichas FISICAS abertas (nao resolvidas e nao canceladas) do chassi."""
    return (
        AssaiPendencia.query
        .filter(
            AssaiPendencia.chassi == chassi,
            AssaiPendencia.resolvida_em.is_(None),
            AssaiPendencia.cancelada_em.is_(None),
            or_(
                AssaiPendencia.origem.in_(list(ORIGENS_FISICAS)),
                AssaiPendencia.devolucao_item_id.isnot(None),
                AssaiPendencia.retorno_fisico.is_(True),
            ),
        )
        .count()
    )


def abrir_pendencia(
    *,
    chassi: str,
    categoria: str,
    origem: str,
    descricao: str,
    operador_id: int,
    retorno_fisico: bool = False,
    evento_pendente_id: Optional[int] = None,
    peca_id: Optional[int] = None,
    pendencia_pai_id: Optional[int] = None,
    devolucao_item_id: Optional[int] = None,
    pos_venda_ocorrencia_id: Optional[int] = None,
    divergencia_origem_id: Optional[int] = None,
    detalhes: Optional[Dict[str, Any]] = None,
) -> AssaiPendencia:
    """Abre uma ficha de pendencia (add + flush, SEM commit — caller commita).

    Acoplamento com o evento PENDENTE (Spec 1 §6):
      - `evento_pendente_id` explicito (emissores legados que JA emitiram o
        PENDENTE): usa-o direto e PULA `_get_or_emit_pendente_event` (sem 2o PENDENTE);
      - senao, se `afeta_estado_moto(ficha)`: reusa/emite via helper travado
        (N fisicas no mesmo chassi = 1 evento, D1);
      - senao (nao fisica — pos-venda sem retorno): `evento_pendente_id = NULL`.
    """
    chassi_norm = (chassi or '').strip().upper()
    if not chassi_norm:
        raise PendenciaError('Chassi obrigatorio.')
    if categoria not in PENDENCIA_CATEGORIAS_VALIDAS:
        raise PendenciaError(
            f'Categoria invalida: {categoria}. Validas: {sorted(PENDENCIA_CATEGORIAS_VALIDAS)}'
        )
    if origem not in PENDENCIA_ORIGENS_VALIDAS:
        raise PendenciaError(
            f'Origem invalida: {origem}. Validas: {sorted(PENDENCIA_ORIGENS_VALIDAS)}'
        )
    descricao_norm = (descricao or '').strip()
    if len(descricao_norm) < 3:
        raise PendenciaError('Descricao obrigatoria (>= 3 caracteres).')

    # Serializa emissao/consulta do PENDENTE compartilhado por chassi.
    db.session.execute(
        db.text('SELECT pg_advisory_xact_lock(hashtext(:c))'),
        {'c': chassi_norm},
    )

    ficha = AssaiPendencia(
        chassi=chassi_norm,
        categoria=categoria,
        origem=origem,
        retorno_fisico=bool(retorno_fisico),
        descricao=descricao_norm,
        peca_id=peca_id,
        pendencia_pai_id=pendencia_pai_id,
        devolucao_item_id=devolucao_item_id,
        pos_venda_ocorrencia_id=pos_venda_ocorrencia_id,
        divergencia_origem_id=divergencia_origem_id,
        detalhes=sanitize_for_json(dict(detalhes or {})),
        aberta_em=agora_brasil_naive(),
        aberta_por_id=operador_id,
    )
    db.session.add(ficha)
    db.session.flush()  # ficha.id disponivel; evento_pendente_id ainda NULL

    if evento_pendente_id is not None:
        ficha.evento_pendente_id = evento_pendente_id
    elif afeta_estado_moto(ficha):
        ficha.evento_pendente_id = _get_or_emit_pendente_event(chassi_norm, operador_id)
    else:
        ficha.evento_pendente_id = None

    db.session.flush()
    return ficha
```

- [ ] Rodar e ver passar: `source .venv/bin/activate && pytest tests/motos_assai/test_pendencia_abrir.py::test_pendencia_fisica_emite_pendente -v` — **Expected: PASS**.

- [ ] Adicionar os casos restantes a `tests/motos_assai/test_pendencia_abrir.py`:
```python
def test_segunda_fisica_reusa_evento(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        f1 = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta A',
            operador_id=admin_user.id,
        )
        f2 = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_REVISAO,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Revisar B',
            operador_id=admin_user.id,
        )
        assert f1.evento_pendente_id == f2.evento_pendente_id
        assert _conta_pendentes(chassi) == 1
        assert AssaiPendencia.query.filter_by(chassi=chassi).count() == 2
        assert count_fisicas_abertas(chassi) == 2
        db.session.rollback()


def test_pos_venda_nao_emite_evento(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user, estado=EVENTO_FATURADA)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_POS_VENDA_LOJA, descricao='Cliente reclamou',
            operador_id=admin_user.id, retorno_fisico=False,
            pos_venda_ocorrencia_id=None,
        )
        assert ficha.evento_pendente_id is None
        assert afeta_estado_moto(ficha) is False
        assert status_efetivo(chassi) == EVENTO_FATURADA
        assert _conta_pendentes(chassi) == 0
        db.session.rollback()


def test_pos_venda_com_retorno_fisico_emite(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user, estado=EVENTO_FATURADA)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_POS_VENDA_CLIENTE, descricao='Retornou fisico',
            operador_id=admin_user.id, retorno_fisico=True,
        )
        assert ficha.evento_pendente_id is not None
        assert afeta_estado_moto(ficha) is True
        assert status_efetivo(chassi) == EVENTO_PENDENTE
        db.session.rollback()


def test_evento_explicito_e_reusado_sem_segundo_pendente(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        ev = emitir_evento(chassi, EVENTO_PENDENTE, admin_user.id)
        db.session.flush()
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_REVISAO,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Revisao devolucao',
            operador_id=admin_user.id, evento_pendente_id=ev.id,
        )
        assert ficha.evento_pendente_id == ev.id
        assert _conta_pendentes(chassi) == 1
        db.session.rollback()


def test_descricao_curta_falha(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        with pytest.raises(PendenciaError, match='Descricao'):
            abrir_pendencia(
                chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
                origem=PENDENCIA_ORIGEM_GALPAO, descricao='ab',
                operador_id=admin_user.id,
            )
        db.session.rollback()
```

- [ ] Rodar e ver passar tudo: `source .venv/bin/activate && pytest tests/motos_assai/test_pendencia_abrir.py -v` — **Expected: PASS** (6 passed).

- [ ] Commit:
```bash
git add app/motos_assai/services/pendencia_service.py tests/motos_assai/test_pendencia_abrir.py
git commit -m "feat(motos_assai): abrir_pendencia + acoplamento evento PENDENTE (Spec 1 Task 6)"
```

---

### Task 7: `resolver_pendencia` + `cancelar_pendencia` (gate de fechamento + MONTADA)

**Files:**
- Modify: `app/motos_assai/services/pendencia_service.py`
- Test: `tests/motos_assai/test_pendencia_resolver.py` (criar)

**Interfaces:**
- **Consumes**: `abrir_pendencia`, `count_fisicas_abertas`, `afeta_estado_moto`, `PendenciaError` (Task 6); `AssaiPendencia`, `PENDENCIA_TRATATIVAS_VALIDAS`, `EVENTO_PENDENCIA_RESOLVIDA`, `EVENTO_MONTADA`; `emitir_evento`, `agora_brasil_naive`, `sanitize_for_json`.
- **Produces**: `resolver_pendencia(*, pendencia_id, tratativa, resolucao_descricao, operador_id) -> AssaiPendencia`; `cancelar_pendencia(*, pendencia_id, motivo, operador_id) -> AssaiPendencia`. (`EVENTO_PENDENCIA_RESOLVIDA` já é importado no topo do módulo.)

**Steps:**

- [ ] Criar `tests/motos_assai/test_pendencia_resolver.py` com o 1º caso (resolver última de 1 → MONTADA):
```python
import uuid
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiMotoEvento,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE, EVENTO_FATURADA,
    EVENTO_PENDENCIA_RESOLVIDA,
    PENDENCIA_CATEGORIA_FALTA_PECA, PENDENCIA_CATEGORIA_REVISAO,
    PENDENCIA_ORIGEM_GALPAO, PENDENCIA_ORIGEM_POS_VENDA_LOJA,
    PENDENCIA_TRATATIVA_CONSERTAR, PENDENCIA_TRATATIVA_REVISAR,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo
from app.motos_assai.services.pendencia_service import (
    abrir_pendencia, resolver_pendencia, cancelar_pendencia, PendenciaError,
)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _moto(chassi, admin_user, estado=EVENTO_MONTADA):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    moto = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA')
    db.session.add(moto)
    db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, admin_user.id)
    if estado != EVENTO_ESTOQUE:
        emitir_evento(chassi, estado, admin_user.id)
    db.session.flush()
    return moto


def _conta(chassi, tipo):
    return AssaiMotoEvento.query.filter_by(chassi=chassi, tipo=tipo).count()


def test_resolver_ultima_de_uma_vira_montada(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta peca',
            operador_id=admin_user.id,
        )
        r = resolver_pendencia(
            pendencia_id=ficha.id, tratativa=PENDENCIA_TRATATIVA_CONSERTAR,
            resolucao_descricao='Consertado no galpao', operador_id=admin_user.id,
        )
        assert r.resolvida_em is not None
        assert r.tratativa == PENDENCIA_TRATATIVA_CONSERTAR
        assert status_efetivo(chassi) == EVENTO_MONTADA
        assert _conta(chassi, EVENTO_MONTADA) == 1  # so o da resolucao (moto entra em ESTOQUE->MONTADA)
        db.session.rollback()
```

- [ ] Rodar e ver falhar: `source .venv/bin/activate && pytest tests/motos_assai/test_pendencia_resolver.py::test_resolver_ultima_de_uma_vira_montada -v` — **Expected: FAIL** (`ImportError: cannot import name 'resolver_pendencia'` do `pendencia_service` — hoje só existe no `montagem_service`).

- [ ] Anexar ao final de `app/motos_assai/services/pendencia_service.py`:
```python
def _emitir_resolucao_fisica(ficha, observacao, operador_id):
    """Gate de fechamento fisico: se esta era a ULTIMA ficha fisica aberta do
    chassi, emite PENDENCIA_RESOLVIDA (marcador) + MONTADA (O1). Caso contrario
    nao emite (chassi segue PENDENTE). Chamado SOB advisory lock, APOS marcar a
    ficha como fechada (para que ela ja nao conte em count_fisicas_abertas).
    """
    if not afeta_estado_moto(ficha):
        return
    if count_fisicas_abertas(ficha.chassi) == 0:
        emitir_evento(
            ficha.chassi, EVENTO_PENDENCIA_RESOLVIDA,
            operador_id=operador_id, observacao=observacao,
        )
        emitir_evento(ficha.chassi, EVENTO_MONTADA, operador_id=operador_id)


def resolver_pendencia(
    *, pendencia_id: int, tratativa: Optional[str],
    resolucao_descricao: str, operador_id: int,
) -> AssaiPendencia:
    """Fecha a ficha (E1: resolucao mora na ficha) e dispara o gate fisico.

    Idempotente: ficha ja resolvida/cancelada => no-op (retorna a ficha).
    O movimento de estoque da tratativa (CONSUMO/CANIBALIZACAO) e responsabilidade
    de chamadas separadas a movimento_service (Task 8) ligadas por pendencia_id —
    esta funcao NAO movimenta estoque.
    """
    ficha = AssaiPendencia.query.get(pendencia_id)
    if ficha is None:
        raise PendenciaError(f'Pendencia {pendencia_id} nao encontrada.')
    if ficha.resolvida_em is not None or ficha.cancelada_em is not None:
        return ficha  # idempotente
    if tratativa is not None and tratativa not in PENDENCIA_TRATATIVAS_VALIDAS:
        raise PendenciaError(
            f'Tratativa invalida: {tratativa}. Validas: {sorted(PENDENCIA_TRATATIVAS_VALIDAS)}'
        )

    db.session.execute(
        db.text('SELECT pg_advisory_xact_lock(hashtext(:c))'),
        {'c': ficha.chassi},
    )

    ficha.resolvida_em = agora_brasil_naive()
    ficha.resolvida_por_id = operador_id
    ficha.tratativa = tratativa
    ficha.resolucao_descricao = (resolucao_descricao or '').strip() or None
    db.session.flush()  # ficha sai da contagem de fisicas abertas

    _emitir_resolucao_fisica(ficha, ficha.resolucao_descricao, operador_id)
    db.session.flush()
    return ficha


def cancelar_pendencia(
    *, pendencia_id: int, motivo: str, operador_id: int,
) -> AssaiPendencia:
    """Fecha a ficha SEM resolver (sem movimento de estoque). Mesmo gate fisico:
    se era a ultima fisica aberta, a moto volta a MONTADA. Idempotente.
    """
    ficha = AssaiPendencia.query.get(pendencia_id)
    if ficha is None:
        raise PendenciaError(f'Pendencia {pendencia_id} nao encontrada.')
    if ficha.resolvida_em is not None or ficha.cancelada_em is not None:
        return ficha  # idempotente
    motivo_norm = (motivo or '').strip()
    if len(motivo_norm) < 3:
        raise PendenciaError('Motivo de cancelamento obrigatorio (>= 3 caracteres).')

    db.session.execute(
        db.text('SELECT pg_advisory_xact_lock(hashtext(:c))'),
        {'c': ficha.chassi},
    )

    ficha.cancelada_em = agora_brasil_naive()
    ficha.cancelada_por_id = operador_id
    det = dict(ficha.detalhes or {})
    det['cancelamento_motivo'] = motivo_norm
    ficha.detalhes = sanitize_for_json(det)
    db.session.flush()

    _emitir_resolucao_fisica(ficha, motivo_norm, operador_id)
    db.session.flush()
    return ficha
```

- [ ] Rodar e ver passar: `source .venv/bin/activate && pytest tests/motos_assai/test_pendencia_resolver.py::test_resolver_ultima_de_uma_vira_montada -v` — **Expected: PASS**.

- [ ] Adicionar os casos restantes a `tests/motos_assai/test_pendencia_resolver.py`:
```python
def test_resolver_uma_de_duas_segue_pendente_depois_montada(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        f1 = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta A',
            operador_id=admin_user.id,
        )
        f2 = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_REVISAO,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Revisar B',
            operador_id=admin_user.id,
        )
        resolver_pendencia(
            pendencia_id=f1.id, tratativa=PENDENCIA_TRATATIVA_CONSERTAR,
            resolucao_descricao='ok A', operador_id=admin_user.id,
        )
        assert status_efetivo(chassi) == EVENTO_PENDENTE  # f2 ainda aberta
        assert _conta(chassi, EVENTO_MONTADA) == 0
        resolver_pendencia(
            pendencia_id=f2.id, tratativa=PENDENCIA_TRATATIVA_REVISAR,
            resolucao_descricao='ok B', operador_id=admin_user.id,
        )
        assert status_efetivo(chassi) == EVENTO_MONTADA
        assert _conta(chassi, EVENTO_PENDENCIA_RESOLVIDA) == 1
        db.session.rollback()


def test_resolver_idempotente(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta peca',
            operador_id=admin_user.id,
        )
        resolver_pendencia(
            pendencia_id=ficha.id, tratativa=PENDENCIA_TRATATIVA_CONSERTAR,
            resolucao_descricao='1a vez', operador_id=admin_user.id,
        )
        marca = ficha.resolvida_em
        r2 = resolver_pendencia(
            pendencia_id=ficha.id, tratativa=PENDENCIA_TRATATIVA_REVISAR,
            resolucao_descricao='2a vez', operador_id=admin_user.id,
        )
        assert r2.resolvida_em == marca          # nao re-grava
        assert r2.tratativa == PENDENCIA_TRATATIVA_CONSERTAR
        assert _conta(chassi, EVENTO_MONTADA) == 1  # nao emitiu 2o MONTADA
        db.session.rollback()


def test_resolver_pos_venda_nao_toca_evento(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user, estado=EVENTO_FATURADA)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_POS_VENDA_LOJA, descricao='Pos venda loja',
            operador_id=admin_user.id, retorno_fisico=False,
        )
        resolver_pendencia(
            pendencia_id=ficha.id, tratativa=PENDENCIA_TRATATIVA_CONSERTAR,
            resolucao_descricao='resolvido sem retorno', operador_id=admin_user.id,
        )
        assert status_efetivo(chassi) == EVENTO_FATURADA
        assert _conta(chassi, EVENTO_MONTADA) == 0
        assert _conta(chassi, EVENTO_PENDENCIA_RESOLVIDA) == 0
        db.session.rollback()


def test_cancelar_ultima_fisica_vira_montada(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta peca',
            operador_id=admin_user.id,
        )
        c = cancelar_pendencia(
            pendencia_id=ficha.id, motivo='Aberta por engano',
            operador_id=admin_user.id,
        )
        assert c.cancelada_em is not None
        assert c.detalhes.get('cancelamento_motivo') == 'Aberta por engano'
        assert status_efetivo(chassi) == EVENTO_MONTADA
        db.session.rollback()


def test_cancelar_motivo_curto_falha(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta peca',
            operador_id=admin_user.id,
        )
        with pytest.raises(PendenciaError, match='Motivo'):
            cancelar_pendencia(pendencia_id=ficha.id, motivo='x', operador_id=admin_user.id)
        db.session.rollback()
```

- [ ] Rodar e ver passar tudo: `source .venv/bin/activate && pytest tests/motos_assai/test_pendencia_resolver.py -v` — **Expected: PASS** (6 passed).

- [ ] Commit:
```bash
git add app/motos_assai/services/pendencia_service.py tests/motos_assai/test_pendencia_resolver.py
git commit -m "feat(motos_assai): resolver/cancelar_pendencia + gate fisico MONTADA (Spec 1 Task 7)"
```

---

### Task 8: Tratativas com movimento de estoque — `consumir`/`canibalizar` + `solicitar_compra`

**Files:**
- Modify: `app/motos_assai/services/movimento_service.py` (adiciona `consumir` + `canibalizar` à base da faixa A — `registrar_entrada`/`descartar`/`ajustar`/`saldo`/`custo_medio`/`EstoqueError`/`MOVIMENTO_*`)
- Modify: `app/motos_assai/services/pendencia_service.py` (adiciona `solicitar_compra`)
- Test: `tests/motos_assai/test_tratativas.py` (criar)

**Interfaces:**
- **Consumes** (faixa A): `movimento_service.registrar_entrada`, `movimento_service.saldo`, `movimento_service.custo_medio`, `movimento_service.EstoqueError`, `AssaiEstoqueMovimento`, `MOVIMENTO_CONSUMO`, `MOVIMENTO_CANIBALIZACAO`; `compra_peca_service.criar_compra`; `AssaiPeca`, `AssaiPendencia`, `PENDENCIA_CATEGORIA_VENDA`/`_FALTA_PECA`, `PENDENCIA_ORIGEM_GALPAO`, `PENDENCIA_FASE_AGUARDANDO_PECA`, `COMPRA_PECA_TIPO_COMPRA`. (Task 6) `abrir_pendencia`.
- **Produces**: `movimento_service.consumir(...)`, `movimento_service.canibalizar(...)`, `pendencia_service.solicitar_compra(...)`.

**Steps:**

- [ ] Criar `tests/motos_assai/test_tratativas.py` com o 1º caso (USAR_ESTOQUE → CONSUMO baixa saldo):
```python
import uuid
from decimal import Decimal
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiPeca, AssaiPendencia, AssaiEstoqueMovimento,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE,
    MOVIMENTO_CONSUMO, MOVIMENTO_CANIBALIZACAO,
    PENDENCIA_CATEGORIA_FALTA_PECA, PENDENCIA_CATEGORIA_VENDA,
    PENDENCIA_ORIGEM_GALPAO, PENDENCIA_ORIGEM_POS_VENDA_LOJA,
    PENDENCIA_FASE_AGUARDANDO_PECA, COMPRA_PECA_TIPO_COMPRA,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo
from app.motos_assai.services.movimento_service import (
    registrar_entrada, consumir, canibalizar, saldo, EstoqueError,
)
from app.motos_assai.services.pendencia_service import abrir_pendencia, solicitar_compra


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _moto(chassi, admin_user, estado=EVENTO_MONTADA):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    moto = AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA')
    db.session.add(moto)
    db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, admin_user.id)
    if estado != EVENTO_ESTOQUE:
        emitir_evento(chassi, estado, admin_user.id)
    db.session.flush()
    return moto


def _peca(admin_user, nome='Bateria 60V'):
    p = AssaiPeca(nome=nome, ativo=True, criado_por_id=admin_user.id)
    db.session.add(p)
    db.session.flush()
    return p


def test_usar_estoque_consumo_baixa_saldo(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        peca = _peca(admin_user)
        registrar_entrada(
            peca_id=peca.id, quantidade=5, custo_unitario=100,
            operador_id=admin_user.id,
        )
        assert saldo(peca.id) == Decimal('5')
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta bateria',
            operador_id=admin_user.id, peca_id=peca.id,
        )
        mov = consumir(
            peca_id=peca.id, quantidade=1, pendencia_id=ficha.id,
            chassi_destino=chassi, operador_id=admin_user.id,
        )
        assert mov.tipo == MOVIMENTO_CONSUMO
        assert mov.delta_almoxarifado == Decimal('-1')
        assert mov.custo_unitario == Decimal('100.0000')
        assert mov.receita_unitaria is None
        assert saldo(peca.id) == Decimal('4')
        db.session.rollback()
```

- [ ] Rodar e ver falhar: `source .venv/bin/activate && pytest tests/motos_assai/test_tratativas.py::test_usar_estoque_consumo_baixa_saldo -v` — **Expected: FAIL** (`ImportError: cannot import name 'consumir'`).

- [ ] Anexar ao final de `app/motos_assai/services/movimento_service.py`:
```python
def consumir(
    *, peca_id, quantidade, pendencia_id, chassi_destino, operador_id,
    receita_unitaria=None,
):
    """Baixa de saldo (CONSUMO, delta -qtd) atendendo uma pendencia (USAR_ESTOQUE).

    Congela custo_unitario = custo_medio(peca) na linha (auditavel). Se a ficha
    atendida e categoria=VENDA e receita_unitaria foi informada, grava receita.
    add + flush, SEM commit (caller commita).
    """
    from decimal import Decimal
    from app.motos_assai.models import (
        AssaiPendencia, AssaiEstoqueMovimento, MOVIMENTO_CONSUMO,
        PENDENCIA_CATEGORIA_VENDA,
    )

    qtd = Decimal(str(quantidade))
    if qtd <= 0:
        raise EstoqueError('Quantidade deve ser positiva.')
    ficha = AssaiPendencia.query.get(pendencia_id)
    if ficha is None:
        raise EstoqueError(f'Pendencia {pendencia_id} nao encontrada.')

    custo = custo_medio(peca_id)
    mov = AssaiEstoqueMovimento(
        peca_id=peca_id,
        tipo=MOVIMENTO_CONSUMO,
        quantidade=qtd,
        delta_almoxarifado=-qtd,
        chassi_destino=(chassi_destino or '').strip().upper() or None,
        pendencia_id=pendencia_id,
        custo_unitario=custo,
        custo_total=(qtd * custo).quantize(Decimal('0.01')),
        operador_id=operador_id,
        ocorrido_em=agora_brasil_naive(),
        dados_extras={},
    )
    if ficha.categoria == PENDENCIA_CATEGORIA_VENDA and receita_unitaria is not None:
        rec = Decimal(str(receita_unitaria))
        mov.receita_unitaria = rec
        mov.receita_total = (qtd * rec).quantize(Decimal('0.01'))

    db.session.add(mov)
    db.session.flush()
    return mov


def canibalizar(
    *, peca_id, quantidade, chassi_origem, chassi_destino, pendencia_id,
    operador_id, receita_unitaria=None,
):
    """Transfere peca de outra moto (CANIBALIZACAO, delta 0, custo 0) E abre uma
    FALTA_PECA ROOT no doador — a falta "viaja" (O4). Transacao unica.

    Guard: chassi_origem (doador) != chassi_destino (receptor). Se a ficha
    atendida e categoria=VENDA e receita_unitaria informada, grava receita na
    linha. add + flush, SEM commit.
    """
    from decimal import Decimal
    from app.motos_assai.models import (
        AssaiPendencia, AssaiEstoqueMovimento, MOVIMENTO_CANIBALIZACAO,
        PENDENCIA_CATEGORIA_VENDA, PENDENCIA_CATEGORIA_FALTA_PECA,
        PENDENCIA_ORIGEM_GALPAO,
    )

    origem = (chassi_origem or '').strip().upper()
    destino = (chassi_destino or '').strip().upper()
    if not origem or not destino:
        raise EstoqueError('chassi_origem e chassi_destino obrigatorios.')
    if origem == destino:
        raise EstoqueError('Chassi doador nao pode ser igual ao receptor.')
    qtd = Decimal(str(quantidade))
    if qtd <= 0:
        raise EstoqueError('Quantidade deve ser positiva.')
    ficha = AssaiPendencia.query.get(pendencia_id)
    if ficha is None:
        raise EstoqueError(f'Pendencia {pendencia_id} nao encontrada.')

    mov = AssaiEstoqueMovimento(
        peca_id=peca_id,
        tipo=MOVIMENTO_CANIBALIZACAO,
        quantidade=qtd,
        delta_almoxarifado=Decimal('0'),
        chassi_origem=origem,
        chassi_destino=destino,
        pendencia_id=pendencia_id,
        custo_unitario=Decimal('0'),
        custo_total=Decimal('0'),
        operador_id=operador_id,
        ocorrido_em=agora_brasil_naive(),
        dados_extras={'custo_estimado': True},
    )
    if ficha.categoria == PENDENCIA_CATEGORIA_VENDA and receita_unitaria is not None:
        rec = Decimal(str(receita_unitaria))
        mov.receita_unitaria = rec
        mov.receita_total = (qtd * rec).quantize(Decimal('0.01'))

    db.session.add(mov)
    db.session.flush()

    # A falta "viaja": FALTA_PECA root no doador (origem/descricao default — ambos NOT NULL).
    from app.motos_assai.services.pendencia_service import abrir_pendencia
    abrir_pendencia(
        chassi=origem,
        categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
        origem=PENDENCIA_ORIGEM_GALPAO,
        descricao=f'Peca canibalizada para chassi {destino}',
        peca_id=peca_id,
        operador_id=operador_id,
        detalhes={'movimento_origem_id': mov.id, 'canibalizado_para': destino},
    )
    return mov
```

- [ ] Anexar ao final de `app/motos_assai/services/pendencia_service.py` (`solicitar_compra`):
```python
def solicitar_compra(
    *, pendencia_id: int, tipo: str, itens, operador_id: int,
    fornecedor: str = 'MOTOCHEFE',
):
    """Provisao (R3): cria assai_peca_compra (tipo GARANTIA/COMPRA) + itens
    ligados a esta ficha por pendencia_id, e seta fase=AGUARDANDO_PECA. NAO
    resolve a ficha (nao grava resolvida_em). Delega ao compra_peca_service.
    add + flush, SEM commit.
    """
    from app.motos_assai.services import compra_peca_service

    ficha = AssaiPendencia.query.get(pendencia_id)
    if ficha is None:
        raise PendenciaError(f'Pendencia {pendencia_id} nao encontrada.')

    itens_com_pendencia = []
    for it in (itens or []):
        d = dict(it)
        d.setdefault('pendencia_id', pendencia_id)
        itens_com_pendencia.append(d)

    compra = compra_peca_service.criar_compra(
        tipo=tipo, itens=itens_com_pendencia,
        operador_id=operador_id, fornecedor=fornecedor,
    )
    ficha.fase = PENDENCIA_FASE_AGUARDANDO_PECA
    db.session.flush()
    return compra
```

- [ ] Rodar e ver passar: `source .venv/bin/activate && pytest tests/motos_assai/test_tratativas.py::test_usar_estoque_consumo_baixa_saldo -v` — **Expected: PASS**.

- [ ] Adicionar os casos restantes a `tests/motos_assai/test_tratativas.py`:
```python
def test_usar_outra_moto_canibalizacao_delta0_abre_falta_no_doador(app, admin_user):
    with app.app_context():
        receptor = f'TST_R{_uid()}'
        doador = f'TST_D{_uid()}'
        _moto(receptor, admin_user)
        _moto(doador, admin_user)
        peca = _peca(admin_user)
        registrar_entrada(
            peca_id=peca.id, quantidade=3, custo_unitario=100,
            operador_id=admin_user.id,
        )
        saldo_antes = saldo(peca.id)
        ficha_r = abrir_pendencia(
            chassi=receptor, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta peca receptor',
            operador_id=admin_user.id, peca_id=peca.id,
        )
        mov = canibalizar(
            peca_id=peca.id, quantidade=1, chassi_origem=doador,
            chassi_destino=receptor, pendencia_id=ficha_r.id,
            operador_id=admin_user.id,
        )
        assert mov.tipo == MOVIMENTO_CANIBALIZACAO
        assert mov.delta_almoxarifado == Decimal('0')
        assert mov.custo_unitario == Decimal('0.0000')
        assert saldo(peca.id) == saldo_antes  # canibalizacao nao mexe no saldo
        # Doador ganhou uma FALTA_PECA root e virou PENDENTE
        falta_doador = (
            AssaiPendencia.query
            .filter_by(chassi=doador, categoria=PENDENCIA_CATEGORIA_FALTA_PECA)
            .first()
        )
        assert falta_doador is not None
        assert falta_doador.pendencia_pai_id is None
        assert falta_doador.detalhes.get('canibalizado_para') == receptor
        assert status_efetivo(doador) == EVENTO_PENDENTE
        db.session.rollback()


def test_venda_grava_receita_no_consumo(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        peca = _peca(admin_user, nome='Carregador')
        registrar_entrada(
            peca_id=peca.id, quantidade=2, custo_unitario=80,
            operador_id=admin_user.id,
        )
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_VENDA,
            origem=PENDENCIA_ORIGEM_POS_VENDA_LOJA, descricao='Venda de peca avulsa',
            operador_id=admin_user.id, peca_id=peca.id, retorno_fisico=False,
        )
        mov = consumir(
            peca_id=peca.id, quantidade=1, pendencia_id=ficha.id,
            chassi_destino=chassi, operador_id=admin_user.id,
            receita_unitaria=150,
        )
        assert mov.receita_unitaria == Decimal('150.0000')
        assert mov.receita_total == Decimal('150.00')
        db.session.rollback()


def test_solicitar_compra_seta_aguardando_peca_sem_resolver(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        peca = _peca(admin_user)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Sem estoque, pedir compra',
            operador_id=admin_user.id, peca_id=peca.id,
        )
        compra = solicitar_compra(
            pendencia_id=ficha.id, tipo=COMPRA_PECA_TIPO_COMPRA,
            itens=[{'peca_id': peca.id, 'quantidade': 2}],
            operador_id=admin_user.id,
        )
        assert compra.tipo == COMPRA_PECA_TIPO_COMPRA
        assert compra.itens[0].pendencia_id == ficha.id
        assert ficha.fase == PENDENCIA_FASE_AGUARDANDO_PECA
        assert ficha.resolvida_em is None  # provisao nao resolve
        db.session.rollback()


def test_canibalizar_guard_doador_igual_receptor(app, admin_user):
    with app.app_context():
        chassi = f'TST_{_uid()}'
        _moto(chassi, admin_user)
        peca = _peca(admin_user)
        ficha = abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta peca',
            operador_id=admin_user.id, peca_id=peca.id,
        )
        with pytest.raises(EstoqueError, match='doador'):
            canibalizar(
                peca_id=peca.id, quantidade=1, chassi_origem=chassi,
                chassi_destino=chassi, pendencia_id=ficha.id,
                operador_id=admin_user.id,
            )
        db.session.rollback()
```

- [ ] Rodar e ver passar tudo: `source .venv/bin/activate && pytest tests/motos_assai/test_tratativas.py -v` — **Expected: PASS** (5 passed).

- [ ] Rodar a suíte das 3 tarefas em conjunto (regressão da faixa): `source .venv/bin/activate && pytest tests/motos_assai/test_pendencia_abrir.py tests/motos_assai/test_pendencia_resolver.py tests/motos_assai/test_tratativas.py tests/motos_assai/test_montagem_service.py -v` — **Expected: PASS**.

- [ ] Commit:
```bash
git add app/motos_assai/services/movimento_service.py app/motos_assai/services/pendencia_service.py tests/motos_assai/test_tratativas.py
git commit -m "feat(motos_assai): tratativas consumir/canibalizar + solicitar_compra (Spec 1 Task 8)"
```

**Notas de integração (para o autor do plano consolidar entre faixas):**
- Minha faixa importa serviços novos **diretamente dos submódulos** (`from app.motos_assai.services.pendencia_service import ...`, `...movimento_service import ...`) e não edita `app/motos_assai/services/__init__.py` — para evitar conflito com a faixa A. A reexportação no `__init__.py` (e a migração dos leitores `listar_abertas`/`contar_pendencias_abertas` para ler a tabela `assai_pendencia`, §10) fica para a tarefa de integração/leitura, fora desta faixa.
- `resolver_pendencia` **não** executa movimento de estoque (a assinatura congelada não tem kwargs de tratativa); `consumir`/`canibalizar` são chamadas separadas ligadas por `pendencia_id`. Isso evita import circular `pendencia_service ⇄ movimento_service` (o único acoplamento é `movimento_service.canibalizar → pendencia_service.abrir_pendencia`, feito por import lazy dentro da função).

---

I have everything I need. Here is the plan for Tasks 9-12.

### Task 9: Migrar leituras de pendencia_service para a tabela `assai_pendencia`

**Files:**
- Modify: `app/motos_assai/services/pendencia_service.py` (substituir as 5 funções de leitura — atualmente baseadas em `assai_moto_evento` — por versões que leem `assai_pendencia`; manter intactas as funções de escrita `abrir_pendencia`/`solicitar_compra`/`resolver_pendencia`/`cancelar_pendencia`/`_get_or_emit_pendente_event`/`count_fisicas_abertas` produzidas nas Faixas A/B).
- Test: `tests/motos_assai/test_pendencia_reads.py` (Create).

**Interfaces:**
- Consumes (Faixas A/B): `pendencia_service.abrir_pendencia(*, chassi, categoria, origem, descricao, operador_id, ...)->AssaiPendencia`; `pendencia_service.resolver_pendencia(*, pendencia_id, tratativa, resolucao_descricao, operador_id)->AssaiPendencia`; model `AssaiPendencia`; constantes `PENDENCIA_CATEGORIA_INDETERMINADA`, `PENDENCIA_ORIGEM_GALPAO` exportadas em `app.motos_assai.models`.
- Produces (consumido por `routes/pendencias.py` + templates `pendencias/{abertas,historico}.html`, intocados no Spec 1): `listar_abertas(filtros=None)->list[dict]` com chaves `{evento_id, chassi, modelo_id, modelo_codigo, modelo_nome, cor, observacao, chassi_doador, operador, operador_id, ocorrido_em(datetime)}`; `listar_historico_resolvidas(limit=200, filtros=None)->list[dict]` com chaves `{evento_id, chassi, modelo_id, modelo_codigo, modelo_nome, cor, observacao_pendencia, descricao_resolucao, operador_pendencia, operador_resolucao, operador_resolucao_id, data_pendencia(str), data_resolucao(str)}`; `contar_pendencias_abertas()->int`; `operadores_que_registraram_pendencia(tipos=None)->list[dict]{id,nome,email}`; `modelos_com_pendencias(tipos=None)->list[dict]{id,codigo,nome}`.

> Nota de retrocompat: `operadores_que_registraram_pendencia` e `modelos_com_pendencias` MANTÊM o kwarg `tipos=None` (a rota do Spec 1 ainda chama com `tipos=[EVENTO_PENDENTE]`); o parâmetro passa a ser ignorado (a tabela já distingue aberta/resolvida). Compatível com a assinatura `()` do contrato.

**Precondição:** migration 34 (`assai_pendencia` etc.) já aplicada no banco LOCAL (Faixa A) — os testes rodam contra o banco real.

Steps:
- [ ] Escrever `tests/motos_assai/test_pendencia_reads.py` com o teste que falha (lê a tabela):

```python
import uuid
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiPendencia,
    EVENTO_ESTOQUE,
    PENDENCIA_CATEGORIA_INDETERMINADA, PENDENCIA_ORIGEM_GALPAO,
)
from app.motos_assai.services import pendencia_service
from app.motos_assai.services.moto_evento_service import emitir_evento


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _moto_estoque(chassi, admin_user):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
    db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, admin_user.id)
    db.session.commit()


def test_listar_abertas_le_a_tabela(app, admin_user):
    with app.app_context():
        chassi = f'TST_PR_{_uid()}'
        _moto_estoque(chassi, admin_user)
        ficha = pendencia_service.abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_INDETERMINADA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Bateria com defeito',
            operador_id=admin_user.id,
        )
        db.session.commit()
        try:
            abertas = pendencia_service.listar_abertas()
            achou = [a for a in abertas if a['chassi'] == chassi]
            assert len(achou) == 1
            assert achou[0]['observacao'] == 'Bateria com defeito'
            assert achou[0]['modelo_codigo'] == 'DOT'
            assert pendencia_service.contar_pendencias_abertas() >= 1
        finally:
            AssaiPendencia.query.filter_by(id=ficha.id).delete()
            db.session.commit()


def test_historico_le_resolucao_da_ficha(app, admin_user):
    with app.app_context():
        chassi = f'TST_PR_{_uid()}'
        _moto_estoque(chassi, admin_user)
        ficha = pendencia_service.abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_INDETERMINADA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Falta parafuso',
            operador_id=admin_user.id,
        )
        db.session.commit()
        pendencia_service.resolver_pendencia(
            pendencia_id=ficha.id, tratativa='CONSERTAR',
            resolucao_descricao='Parafuso colocado', operador_id=admin_user.id,
        )
        db.session.commit()
        try:
            hist = pendencia_service.listar_historico_resolvidas()
            achou = [h for h in hist if h['chassi'] == chassi]
            assert len(achou) == 1
            assert achou[0]['descricao_resolucao'] == 'Parafuso colocado'
            assert achou[0]['observacao_pendencia'] == 'Falta parafuso'
            assert pendencia_service.listar_abertas() is not None
            assert chassi not in [a['chassi'] for a in pendencia_service.listar_abertas()]
        finally:
            AssaiPendencia.query.filter_by(id=ficha.id).delete()
            db.session.commit()
```

- [ ] Rodar e ver falhar: `pytest tests/motos_assai/test_pendencia_reads.py -v` — Expected: FAIL (`listar_abertas` ainda lê `assai_moto_evento`, não acha a ficha pela tabela / chaves divergentes).
- [ ] Ajustar o bloco de imports do topo de `pendencia_service.py` para incluir o model e constantes (substituir o import `from app.motos_assai.models import (... EVENTO_PENDENTE, EVENTO_PENDENCIA_RESOLVIDA,)` por):

```python
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiPendencia,
)
```
(manter `from app.auth.models import Usuario`, `from sqlalchemy import func`, `from sqlalchemy.orm import joinedload`, `from datetime import date, datetime, time`, `from app import db`.)

- [ ] Substituir a função `listar_abertas` pela versão baseada na tabela:

```python
def listar_abertas(filtros: Optional[FiltrosPendencias] = None) -> List[Dict[str, Any]]:
    """Fichas de pendencia ABERTAS (resolvida_em IS NULL AND cancelada_em IS NULL).

    Le a tabela assai_pendencia (E1: a ficha e a verdade do tratamento). Filtros:
    chassi (ilike), modelo_id (via assai_moto), data_inicio/data_fim (aberta_em),
    operador_id (aberta_por_id).

    Retorna dicts com as chaves consumidas por pendencias/abertas.html.
    """
    q = (
        AssaiPendencia.query
        .options(joinedload(AssaiPendencia.aberta_por))
        .filter(
            AssaiPendencia.resolvida_em.is_(None),
            AssaiPendencia.cancelada_em.is_(None),
        )
    )

    if filtros:
        chassi = (filtros.get('chassi') or '').strip().upper()
        if chassi:
            q = q.filter(AssaiPendencia.chassi.ilike(f'%{chassi}%'))
        operador_id = filtros.get('operador_id')
        if operador_id:
            q = q.filter(AssaiPendencia.aberta_por_id == operador_id)
        data_inicio = filtros.get('data_inicio')
        if data_inicio:
            q = q.filter(
                AssaiPendencia.aberta_em >= datetime.combine(data_inicio, time.min)
            )
        data_fim = filtros.get('data_fim')
        if data_fim:
            q = q.filter(
                AssaiPendencia.aberta_em <= datetime.combine(data_fim, time.max)
            )

    fichas = q.order_by(AssaiPendencia.aberta_em.desc()).all()
    if not fichas:
        return []

    chassis = [f.chassi for f in fichas]
    motos = (
        AssaiMoto.query
        .options(joinedload(AssaiMoto.modelo))
        .filter(AssaiMoto.chassi.in_(chassis))
        .all()
    )
    moto_por_chassi = {m.chassi: m for m in motos}

    filtro_modelo_id = (filtros or {}).get('modelo_id')

    result = []
    for f in fichas:
        moto = moto_por_chassi.get(f.chassi)
        if filtro_modelo_id and (not moto or moto.modelo_id != filtro_modelo_id):
            continue
        result.append({
            'evento_id': f.id,
            'chassi': f.chassi,
            'modelo_id': moto.modelo_id if moto else None,
            'modelo_codigo': moto.modelo.codigo if moto and moto.modelo else '-',
            'modelo_nome': moto.modelo.nome if moto and moto.modelo else '-',
            'cor': (moto.cor if moto else None) or '-',
            'observacao': f.descricao or '(sem observacao)',
            'chassi_doador': f.chassi_doador,
            'operador': f.aberta_por.nome if f.aberta_por else '-',
            'operador_id': f.aberta_por_id,
            'ocorrido_em': f.aberta_em,
        })
    return result
```

- [ ] Substituir a função `listar_historico_resolvidas` (1:1 com a ficha, E1):

```python
def listar_historico_resolvidas(
    limit: int = 200,
    filtros: Optional[FiltrosPendencias] = None,
) -> List[Dict[str, Any]]:
    """Fichas RESOLVIDAS (resolvida_em IS NOT NULL), 1:1 com a ficha (E1).

    Filtros operador/data se aplicam a RESOLUCAO (resolvida_por_id / resolvida_em).
    Retorna chaves consumidas por pendencias/historico.html.
    """
    q = (
        AssaiPendencia.query
        .options(
            joinedload(AssaiPendencia.aberta_por),
            joinedload(AssaiPendencia.resolvida_por),
        )
        .filter(AssaiPendencia.resolvida_em.isnot(None))
    )

    if filtros:
        chassi = (filtros.get('chassi') or '').strip().upper()
        if chassi:
            q = q.filter(AssaiPendencia.chassi.ilike(f'%{chassi}%'))
        operador_id = filtros.get('operador_id')
        if operador_id:
            q = q.filter(AssaiPendencia.resolvida_por_id == operador_id)
        data_inicio = filtros.get('data_inicio')
        if data_inicio:
            q = q.filter(
                AssaiPendencia.resolvida_em >= datetime.combine(data_inicio, time.min)
            )
        data_fim = filtros.get('data_fim')
        if data_fim:
            q = q.filter(
                AssaiPendencia.resolvida_em <= datetime.combine(data_fim, time.max)
            )

    fichas = q.order_by(AssaiPendencia.resolvida_em.desc()).limit(limit).all()
    if not fichas:
        return []

    chassis = list({f.chassi for f in fichas})
    motos = (
        AssaiMoto.query
        .options(joinedload(AssaiMoto.modelo))
        .filter(AssaiMoto.chassi.in_(chassis))
        .all()
    )
    moto_por_chassi = {m.chassi: m for m in motos}

    filtro_modelo_id = (filtros or {}).get('modelo_id')

    result = []
    for f in fichas:
        moto = moto_por_chassi.get(f.chassi)
        if filtro_modelo_id and (not moto or moto.modelo_id != filtro_modelo_id):
            continue
        result.append({
            'evento_id': f.id,
            'chassi': f.chassi,
            'modelo_id': moto.modelo_id if moto else None,
            'modelo_codigo': moto.modelo.codigo if moto and moto.modelo else '-',
            'modelo_nome': moto.modelo.nome if moto and moto.modelo else '-',
            'cor': (moto.cor if moto else None) or '-',
            'observacao_pendencia': f.descricao or '(sem registro)',
            'descricao_resolucao': f.resolucao_descricao or '(sem descricao)',
            'operador_pendencia': f.aberta_por.nome if f.aberta_por else '-',
            'operador_resolucao': f.resolvida_por.nome if f.resolvida_por else '-',
            'operador_resolucao_id': f.resolvida_por_id,
            'data_pendencia': f.aberta_em.strftime('%d/%m/%Y %H:%M') if f.aberta_em else '-',
            'data_resolucao': f.resolvida_em.strftime('%d/%m/%Y %H:%M') if f.resolvida_em else '-',
        })
    return result
```

- [ ] Substituir `contar_pendencias_abertas`:

```python
def contar_pendencias_abertas() -> int:
    """Conta fichas assai_pendencia abertas (resolvida_em IS NULL AND cancelada_em IS NULL)."""
    return (
        db.session.query(func.count(AssaiPendencia.id))
        .filter(
            AssaiPendencia.resolvida_em.is_(None),
            AssaiPendencia.cancelada_em.is_(None),
        )
        .scalar() or 0
    )
```

- [ ] Substituir `operadores_que_registraram_pendencia` (lê distintos de `assai_pendencia`; `tipos` retrocompat ignorado):

```python
def operadores_que_registraram_pendencia(tipos: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Usuarios distintos que abriram ou resolveram uma ficha de pendencia.

    `tipos` mantido por retrocompat com a rota do Spec 1 (ignorado: a tabela ja
    distingue abertura/resolucao). Retorna [{id, nome, email}] ordenado por nome.
    """
    abertos = db.session.query(AssaiPendencia.aberta_por_id).filter(
        AssaiPendencia.aberta_por_id.isnot(None)
    )
    resolvidos = db.session.query(AssaiPendencia.resolvida_por_id).filter(
        AssaiPendencia.resolvida_por_id.isnot(None)
    )
    ids = {oid for (oid,) in abertos.distinct().all()}
    ids |= {oid for (oid,) in resolvidos.distinct().all()}
    if not ids:
        return []
    usuarios = (
        Usuario.query
        .filter(Usuario.id.in_(ids))
        .order_by(Usuario.nome)
        .all()
    )
    return [{'id': u.id, 'nome': u.nome, 'email': u.email} for u in usuarios]
```

- [ ] Substituir `modelos_com_pendencias`:

```python
def modelos_com_pendencias(tipos: Optional[List[str]] = None) -> List[Dict[str, Any]]:
    """Modelos distintos com ao menos uma ficha de pendencia (qualquer estado).

    `tipos` mantido por retrocompat (ignorado). Retorna [{id, codigo, nome}].
    """
    chassis_subq = (
        db.session.query(AssaiPendencia.chassi).distinct().subquery()
    )
    modelos = (
        db.session.query(AssaiModelo)
        .join(AssaiMoto, AssaiMoto.modelo_id == AssaiModelo.id)
        .filter(AssaiMoto.chassi.in_(db.session.query(chassis_subq.c.chassi)))
        .distinct()
        .order_by(AssaiModelo.codigo)
        .all()
    )
    return [{'id': m.id, 'codigo': m.codigo, 'nome': m.nome} for m in modelos]
```

- [ ] Remover os helpers agora mortos `_aplicar_filtros_evento` e `_ultimo_evento_subquery` (e o import de `AssaiMotoEvento`/`EVENTO_*` se não forem mais usados pelas funções de escrita; conferir com `grep -n "AssaiMotoEvento\|_aplicar_filtros_evento\|_ultimo_evento_subquery" app/motos_assai/services/pendencia_service.py` e só remover o que tiver 0 usos restantes).
- [ ] Rodar e ver passar: `pytest tests/motos_assai/test_pendencia_reads.py -v` — Expected: PASS.
- [ ] Garantir que nada quebrou nos demais: `pytest tests/motos_assai/ -v` — Expected: PASS.
- [ ] Commit: `git add app/motos_assai/services/pendencia_service.py tests/motos_assai/test_pendencia_reads.py && git commit -m "feat(motos_assai): leituras de pendencia leem assai_pendencia (Spec 1 Task 9)"`

---

### Task 10: Ganchos de integração (3 emissores) + shim retrocompatível de `resolver_pendencia`

**Files:**
- Modify: `app/motos_assai/services/montagem_service.py` (`registrar_montagem`, `enviar_para_pendencia` abrem ficha; `resolver_pendencia` vira SHIM).
- Modify: `app/motos_assai/services/devolucao_service.py` (`criar_devolucao` abre ficha REVISAO/DEVOLUCAO por chassi).
- Test: `tests/motos_assai/test_integracao_ganchos.py` (Create).
- Test (garantir verde, sem editar lógica): `tests/motos_assai/test_montagem_service.py`.

**Interfaces:**
- Consumes: `pendencia_service.abrir_pendencia(...)`, `pendencia_service.resolver_pendencia(*, pendencia_id, tratativa, resolucao_descricao, operador_id)`, model `AssaiPendencia`, constantes `PENDENCIA_CATEGORIA_INDETERMINADA/REVISAO`, `PENDENCIA_ORIGEM_GALPAO/DEVOLUCAO` (de `app.motos_assai.models`); `status_efetivo`, `ultimo_evento` (moto_evento_service).
- Produces: comportamento idêntico ao atual para "1 pendência por moto" — `montagem_service.resolver_pendencia(chassi, descricao_resolucao, operador_id)->{evento_id, chassi, tipo=MONTADA}` (export em `services/__init__.py` e rota `POST /pendencias/resolver` INTACTOS); toda PENDENTE física agora nasce com uma ficha `assai_pendencia` correspondente (`evento_pendente_id` = o evento já emitido).

Steps:
- [ ] Escrever `tests/motos_assai/test_integracao_ganchos.py` com os testes que falham:

```python
import uuid
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiPendencia,
    EVENTO_ESTOQUE, EVENTO_PENDENTE, EVENTO_MONTADA,
    PENDENCIA_CATEGORIA_INDETERMINADA, PENDENCIA_ORIGEM_GALPAO,
)
from app.motos_assai.services import (
    registrar_montagem, resolver_pendencia, MontagemValidationError,
)
from app.motos_assai.services.moto_evento_service import emitir_evento, status_efetivo


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _moto_estoque(chassi, admin_user):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
    db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, admin_user.id)
    db.session.commit()


def _fichas_abertas(chassi):
    return AssaiPendencia.query.filter(
        AssaiPendencia.chassi == chassi,
        AssaiPendencia.resolvida_em.is_(None),
        AssaiPendencia.cancelada_em.is_(None),
    ).all()


def test_montagem_pendente_abre_ficha(app, admin_user):
    with app.app_context():
        chassi = f'TST_IG_{_uid()}'
        _moto_estoque(chassi, admin_user)
        r = registrar_montagem(chassi, True, 'Bateria com defeito', None, admin_user.id)
        try:
            assert r['tipo'] == EVENTO_PENDENTE
            fichas = _fichas_abertas(chassi)
            assert len(fichas) == 1
            f = fichas[0]
            assert f.categoria == PENDENCIA_CATEGORIA_INDETERMINADA
            assert f.origem == PENDENCIA_ORIGEM_GALPAO
            assert f.descricao == 'Bateria com defeito'
            assert f.evento_pendente_id == r['evento_id']
            # nenhum 2o PENDENTE emitido
            from app.motos_assai.models import AssaiMotoEvento
            n_pend = AssaiMotoEvento.query.filter_by(
                chassi=chassi, tipo=EVENTO_PENDENTE).count()
            assert n_pend == 1
        finally:
            AssaiPendencia.query.filter_by(chassi=chassi).delete()
            db.session.commit()


def test_shim_resolver_resolve_unica_ficha(app, admin_user):
    with app.app_context():
        chassi = f'TST_IG_{_uid()}'
        _moto_estoque(chassi, admin_user)
        registrar_montagem(chassi, True, 'Defeito X', None, admin_user.id)
        resolver_pendencia(chassi, 'Peca trocada', admin_user.id)
        try:
            assert status_efetivo(chassi) == EVENTO_MONTADA
            assert _fichas_abertas(chassi) == []
            f = AssaiPendencia.query.filter_by(chassi=chassi).first()
            assert f.resolvida_em is not None
            assert f.resolucao_descricao == 'Peca trocada'
        finally:
            AssaiPendencia.query.filter_by(chassi=chassi).delete()
            db.session.commit()


def test_shim_resolver_multiplas_fichas_erro(app, admin_user):
    with app.app_context():
        chassi = f'TST_IG_{_uid()}'
        _moto_estoque(chassi, admin_user)
        registrar_montagem(chassi, True, 'Defeito A', None, admin_user.id)
        # 2a ficha fisica aberta no mesmo chassi (cenario Spec 2)
        from app.motos_assai.services import pendencia_service
        from app.motos_assai.models import AssaiMotoEvento
        ev = AssaiMotoEvento.query.filter_by(
            chassi=chassi, tipo=EVENTO_PENDENTE).first()
        pendencia_service.abrir_pendencia(
            chassi=chassi, categoria=PENDENCIA_CATEGORIA_INDETERMINADA,
            origem=PENDENCIA_ORIGEM_GALPAO, descricao='Defeito B',
            evento_pendente_id=ev.id, operador_id=admin_user.id,
        )
        db.session.commit()
        try:
            with pytest.raises(MontagemValidationError, match='[Mm].ltiplas'):
                resolver_pendencia(chassi, 'tenta resolver', admin_user.id)
        finally:
            AssaiPendencia.query.filter_by(chassi=chassi).delete()
            db.session.commit()
```

- [ ] Rodar e ver falhar: `pytest tests/motos_assai/test_integracao_ganchos.py -v` — Expected: FAIL (`registrar_montagem` não abre ficha; shim ainda emite eventos direto).
- [ ] Em `montagem_service.py`, no bloco `if pendencia:` de `registrar_montagem`, inserir a abertura da ficha logo após `ev = emitir_evento(...)` e ANTES de `db.session.commit()`. Substituir:

```python
        ev = emitir_evento(
            chassi_norm, EVENTO_PENDENTE,
            operador_id=operador_id,
            observacao=descricao_pendencia.strip(),
            dados_extras={
                'descricao': descricao_pendencia.strip(),
                'chassi_doador': (chassi_doador or '').strip().upper() or None,
            },
        )
    else:
```
por:
```python
        ev = emitir_evento(
            chassi_norm, EVENTO_PENDENTE,
            operador_id=operador_id,
            observacao=descricao_pendencia.strip(),
            dados_extras={
                'descricao': descricao_pendencia.strip(),
                'chassi_doador': (chassi_doador or '').strip().upper() or None,
            },
        )
        # Spec 1: toda PENDENTE fisica nasce com uma ficha assai_pendencia.
        # Categoria INDETERMINADA (reclassificada na UI do Spec 2). Passa o
        # evento_pendente_id JA emitido -> abrir_pendencia nao emite 2o PENDENTE.
        from app.motos_assai.services import pendencia_service
        from app.motos_assai.models import (
            PENDENCIA_CATEGORIA_INDETERMINADA, PENDENCIA_ORIGEM_GALPAO,
        )
        doador_norm = (chassi_doador or '').strip().upper() or None
        pendencia_service.abrir_pendencia(
            chassi=chassi_norm,
            categoria=PENDENCIA_CATEGORIA_INDETERMINADA,
            origem=PENDENCIA_ORIGEM_GALPAO,
            descricao=descricao_pendencia.strip(),
            evento_pendente_id=ev.id,
            operador_id=operador_id,
            detalhes={'chassi_doador': doador_norm} if doador_norm else None,
        )
    else:
```

- [ ] Em `montagem_service.py`, em `enviar_para_pendencia`, inserir a abertura da ficha logo após o `ev = emitir_evento(...)` (que termina na linha do `)` antes de `db.session.commit()`). Substituir o trecho:

```python
    ev = emitir_evento(
        chassi_norm, EVENTO_PENDENTE,
        operador_id=operador_id,
        observacao=descricao_pendencia.strip(),
        dados_extras={
            'descricao': descricao_pendencia.strip(),
            'chassi_doador': (chassi_doador or '').strip().upper() or None,
            'origem_status': status,
            'separacao_liberada_id': sep_liberada_id,
        },
    )
    db.session.commit()
```
por:
```python
    ev = emitir_evento(
        chassi_norm, EVENTO_PENDENTE,
        operador_id=operador_id,
        observacao=descricao_pendencia.strip(),
        dados_extras={
            'descricao': descricao_pendencia.strip(),
            'chassi_doador': (chassi_doador or '').strip().upper() or None,
            'origem_status': status,
            'separacao_liberada_id': sep_liberada_id,
        },
    )
    # Spec 1: abre a ficha INDETERMINADA/GALPAO reusando o PENDENTE ja emitido.
    from app.motos_assai.services import pendencia_service
    from app.motos_assai.models import (
        PENDENCIA_CATEGORIA_INDETERMINADA, PENDENCIA_ORIGEM_GALPAO,
    )
    doador_norm = (chassi_doador or '').strip().upper() or None
    pendencia_service.abrir_pendencia(
        chassi=chassi_norm,
        categoria=PENDENCIA_CATEGORIA_INDETERMINADA,
        origem=PENDENCIA_ORIGEM_GALPAO,
        descricao=descricao_pendencia.strip(),
        evento_pendente_id=ev.id,
        operador_id=operador_id,
        detalhes={'chassi_doador': doador_norm, 'origem_status': status}
        if (doador_norm or status) else None,
    )
    db.session.commit()
```

- [ ] Em `montagem_service.py`, transformar `resolver_pendencia` em SHIM. Substituir o corpo inteiro da função (da docstring até o `return`) por:

```python
def resolver_pendencia(
    chassi: str, descricao_resolucao: str, operador_id: int,
) -> Dict[str, Any]:
    """SHIM retrocompativel (Spec 1): resolve a UNICA ficha fisica aberta do chassi.

    Delegado real: pendencia_service.resolver_pendencia(pendencia_id=...). A rota
    POST /pendencias/resolver e os imports de services/__init__.py seguem intactos
    (assinatura por chassi). No gap Spec 1->Spec 2 nao ha multi-pendencia por moto
    (a UI que cria N so chega no Spec 2); >1 ficha fisica aberta -> erro claro.

    Sequencia efetiva: pendencia_service fecha a ficha e, sendo a ultima fisica,
    emite PENDENCIA_RESOLVIDA + MONTADA. status_efetivo final = MONTADA.
    """
    from app.motos_assai.services import pendencia_service
    from app.motos_assai.models import AssaiPendencia

    chassi_norm = chassi.strip().upper()
    status = status_efetivo(chassi_norm)
    if status != EVENTO_PENDENTE:
        raise MontagemValidationError(
            _msg_a6_por_status_montagem(chassi_norm, status, esperado='PENDENTE')
        )
    if not descricao_resolucao or len(descricao_resolucao.strip()) < 3:
        raise MontagemValidationError('Descrição da resolução obrigatória (≥3 chars)')

    # Fichas FISICAS abertas = as que carregam o evento PENDENTE (evento_pendente_id).
    fichas = (
        AssaiPendencia.query
        .filter(
            AssaiPendencia.chassi == chassi_norm,
            AssaiPendencia.resolvida_em.is_(None),
            AssaiPendencia.cancelada_em.is_(None),
            AssaiPendencia.evento_pendente_id.isnot(None),
        )
        .all()
    )
    if not fichas:
        raise MontagemValidationError(
            f'Chassi {chassi_norm} esta PENDENTE mas nao tem ficha de pendencia '
            'fisica aberta (rode o backfill motos_assai_35).'
        )
    if len(fichas) > 1:
        raise MontagemValidationError(
            f'Multiplas ({len(fichas)}) pendencias abertas para o chassi '
            f'{chassi_norm} — use a tela de resolucao por ficha (Spec 2).'
        )

    pendencia_service.resolver_pendencia(
        pendencia_id=fichas[0].id,
        tratativa=None,
        resolucao_descricao=descricao_resolucao.strip(),
        operador_id=operador_id,
    )
    db.session.commit()

    ev_final = ultimo_evento(chassi_norm)
    return {
        'evento_id': ev_final.id if ev_final else None,
        'chassi': chassi_norm,
        'tipo': EVENTO_MONTADA,
    }
```
E adicionar `ultimo_evento` ao import existente do moto_evento_service no topo do arquivo (`from app.motos_assai.services.moto_evento_service import (emitir_evento, status_efetivo, ultimo_evento,)`).

- [ ] Em `devolucao_service.py`, dentro do `for chassi in chassis_unicos:` de `criar_devolucao`, inserir a abertura da ficha REVISAO/DEVOLUCAO após criar/flush o `item`. Substituir:

```python
        item = AssaiDevolucaoItem(
            devolucao_id=devolucao.id,
            chassi=chassi,
            nf_qpa_item_id=nf_item.id,
            evento_pendencia_id=evento.id,
            criado_em=agora_brasil_naive(),
        )
        db.session.add(item)
        db.session.flush()
```
por:
```python
        item = AssaiDevolucaoItem(
            devolucao_id=devolucao.id,
            chassi=chassi,
            nf_qpa_item_id=nf_item.id,
            evento_pendencia_id=evento.id,
            criado_em=agora_brasil_naive(),
        )
        db.session.add(item)
        db.session.flush()

        # Spec 1: toda devolucao gera ficha REVISAO/DEVOLUCAO (origem fisica).
        # Reusa o PENDENTE ja emitido (evento.id) -> sem 2o PENDENTE.
        from app.motos_assai.services import pendencia_service
        from app.motos_assai.models import (
            PENDENCIA_CATEGORIA_REVISAO, PENDENCIA_ORIGEM_DEVOLUCAO,
        )
        pendencia_service.abrir_pendencia(
            chassi=chassi,
            categoria=PENDENCIA_CATEGORIA_REVISAO,
            origem=PENDENCIA_ORIGEM_DEVOLUCAO,
            descricao=motivo_norm,
            evento_pendente_id=evento.id,
            devolucao_item_id=item.id,
            operador_id=operador_id,
        )
```

- [ ] Rodar e ver passar: `pytest tests/motos_assai/test_integracao_ganchos.py -v` — Expected: PASS.
- [ ] Garantir retrocompat dos testes existentes: `pytest tests/motos_assai/test_montagem_service.py -v` — Expected: PASS (`test_resolver_pendencia` agora flui pelo shim → ficha aberta por `registrar_montagem`, resolvida pelo delegado, `status_efetivo==MONTADA`).
- [ ] Rodar a suíte do módulo: `pytest tests/motos_assai/ -v` — Expected: PASS.
- [ ] Commit: `git add app/motos_assai/services/montagem_service.py app/motos_assai/services/devolucao_service.py tests/motos_assai/test_integracao_ganchos.py && git commit -m "feat(motos_assai): ganchos de ficha em montagem/enviar/devolucao + shim resolver_pendencia (Spec 1 Task 10)"`

---

### Task 11: Backfill `motos_assai_35_backfill_pendencias.py` (PENDENTE sem ficha → AssaiPendencia)

**Files:**
- Create: `scripts/migrations/motos_assai_35_backfill_pendencias.py`
- Test: `tests/motos_assai/test_backfill_pendencias.py` (Create)

**Interfaces:**
- Consumes: `pendencia_service.abrir_pendencia(...)`, models `AssaiMoto`, `AssaiMotoEvento`, `AssaiPendencia`, `AssaiDevolucaoItem`, constantes `EVENTO_PENDENTE`, `PENDENCIA_CATEGORIA_INDETERMINADA/REVISAO`, `PENDENCIA_ORIGEM_GALPAO/DEVOLUCAO`.
- Produces: funções importáveis `chassis_pendentes_sem_ficha()->list[AssaiMotoEvento]`, `backfill(confirmar=False)->dict{plano:int, criadas:int}`, `verificar()->int` (0 = cobertura completa); `main()` com argparse (`--confirmar`, `--check`; dry-run default).

Steps:
- [ ] Escrever `tests/motos_assai/test_backfill_pendencias.py` com o teste que falha:

```python
import uuid
import importlib.util
import os
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiPendencia,
    EVENTO_ESTOQUE, EVENTO_PENDENTE,
    PENDENCIA_CATEGORIA_INDETERMINADA, PENDENCIA_ORIGEM_GALPAO,
)
from app.motos_assai.services.moto_evento_service import emitir_evento

_SPEC = importlib.util.spec_from_file_location(
    'motos_assai_35_backfill_pendencias',
    os.path.join(
        os.path.dirname(__file__), '..', '..',
        'scripts', 'migrations', 'motos_assai_35_backfill_pendencias.py',
    ),
)
backfill_mod = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(backfill_mod)


def _uid():
    return uuid.uuid4().hex[:8].upper()


def _moto_pendente_legacy(chassi, admin_user):
    """Simula chassi legado: PENDENTE direto via evento, SEM ficha."""
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
    db.session.flush()
    emitir_evento(chassi, EVENTO_ESTOQUE, admin_user.id)
    ev = emitir_evento(
        chassi, EVENTO_PENDENTE, admin_user.id,
        observacao='Defeito legado', dados_extras={'descricao': 'Defeito legado'},
    )
    db.session.commit()
    return ev


def test_backfill_cria_ficha_indeterminada(app, admin_user):
    with app.app_context():
        chassi = f'TST_BF_{_uid()}'
        ev = _moto_pendente_legacy(chassi, admin_user)
        try:
            assert AssaiPendencia.query.filter_by(chassi=chassi).count() == 0
            res = backfill_mod.backfill(confirmar=True)
            assert res['criadas'] >= 1
            f = AssaiPendencia.query.filter_by(chassi=chassi).first()
            assert f is not None
            assert f.categoria == PENDENCIA_CATEGORIA_INDETERMINADA
            assert f.origem == PENDENCIA_ORIGEM_GALPAO
            assert f.evento_pendente_id == ev.id
            assert f.descricao == 'Defeito legado'
            assert (f.detalhes or {}).get('legacy_backfill') is True
        finally:
            AssaiPendencia.query.filter_by(chassi=chassi).delete()
            db.session.commit()


def test_backfill_idempotente(app, admin_user):
    with app.app_context():
        chassi = f'TST_BF_{_uid()}'
        _moto_pendente_legacy(chassi, admin_user)
        try:
            backfill_mod.backfill(confirmar=True)
            n1 = AssaiPendencia.query.filter_by(chassi=chassi).count()
            backfill_mod.backfill(confirmar=True)
            n2 = AssaiPendencia.query.filter_by(chassi=chassi).count()
            assert n1 == 1 and n2 == 1
        finally:
            AssaiPendencia.query.filter_by(chassi=chassi).delete()
            db.session.commit()


def test_dry_run_nao_grava(app, admin_user):
    with app.app_context():
        chassi = f'TST_BF_{_uid()}'
        _moto_pendente_legacy(chassi, admin_user)
        try:
            res = backfill_mod.backfill(confirmar=False)
            assert res['plano'] >= 1
            assert AssaiPendencia.query.filter_by(chassi=chassi).count() == 0
        finally:
            AssaiPendencia.query.filter(
                AssaiPendencia.chassi == chassi).delete()
            db.session.commit()
```

- [ ] Rodar e ver falhar: `pytest tests/motos_assai/test_backfill_pendencias.py -v` — Expected: FAIL (arquivo do script ainda não existe → ImportError no exec_module).
- [ ] Criar `scripts/migrations/motos_assai_35_backfill_pendencias.py` com conteúdo completo:

```python
"""Backfill 35: cria assai_pendencia para todo chassi cujo ULTIMO evento e
PENDENTE e que ainda nao tem ficha de pendencia (legado pre-Spec 1).

Regra (espelha §12.4 do spec):
  - se o evento PENDENTE veio de devolucao (dados_extras['origem']=='devolucao_nfd')
    -> categoria=REVISAO, origem=DEVOLUCAO, devolucao_item_id resolvido pelo
       AssaiDevolucaoItem.evento_pendencia_id == evento.id;
  - senao -> categoria=INDETERMINADA, origem=GALPAO; descricao do observacao /
    dados_extras['descricao']; chassi_doador de dados_extras; detalhes.legacy_backfill=true.

Reusa pendencia_service.abrir_pendencia passando evento_pendente_id explicito
(nao emite 2o PENDENTE). NAO consta no build.sh (padrao 32/33: aplicar manual).

Flags: dry-run (default), --confirmar (efetiva), --check (sai !=0 se sobrou PENDENTE
sem ficha).
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import func  # noqa: E402

from app import create_app, db  # noqa: E402
from app.motos_assai.models import (  # noqa: E402
    AssaiMotoEvento, AssaiPendencia, AssaiDevolucaoItem,
    EVENTO_PENDENTE,
    PENDENCIA_CATEGORIA_INDETERMINADA, PENDENCIA_CATEGORIA_REVISAO,
    PENDENCIA_ORIGEM_GALPAO, PENDENCIA_ORIGEM_DEVOLUCAO,
)
from app.motos_assai.services import pendencia_service  # noqa: E402


def chassis_pendentes_sem_ficha():
    """Eventos PENDENTE que sao o ULTIMO evento do chassi e nao tem ficha aberta."""
    sub = (
        db.session.query(
            AssaiMotoEvento.chassi.label('chassi'),
            func.max(AssaiMotoEvento.id).label('ultimo_id'),
        )
        .group_by(AssaiMotoEvento.chassi)
        .subquery()
    )
    ultimos_pendentes = (
        db.session.query(AssaiMotoEvento)
        .join(sub, AssaiMotoEvento.id == sub.c.ultimo_id)
        .filter(AssaiMotoEvento.tipo == EVENTO_PENDENTE)
        .all()
    )
    # Exclui chassis que ja tem QUALQUER ficha aberta (idempotencia).
    com_ficha = {
        c for (c,) in db.session.query(AssaiPendencia.chassi).filter(
            AssaiPendencia.resolvida_em.is_(None),
            AssaiPendencia.cancelada_em.is_(None),
        ).distinct().all()
    }
    return [ev for ev in ultimos_pendentes if ev.chassi not in com_ficha]


def _params_ficha(ev):
    """Deriva (categoria, origem, descricao, devolucao_item_id, chassi_doador)."""
    dados = ev.dados_extras if isinstance(ev.dados_extras, dict) else {}
    descricao = ev.observacao or dados.get('descricao') or 'Pendencia legada (backfill)'
    chassi_doador = dados.get('chassi_doador')

    if dados.get('origem') == 'devolucao_nfd':
        item = (
            AssaiDevolucaoItem.query
            .filter_by(evento_pendencia_id=ev.id)
            .first()
        )
        return (
            PENDENCIA_CATEGORIA_REVISAO, PENDENCIA_ORIGEM_DEVOLUCAO,
            descricao, (item.id if item else None), chassi_doador,
        )
    return (
        PENDENCIA_CATEGORIA_INDETERMINADA, PENDENCIA_ORIGEM_GALPAO,
        descricao, None, chassi_doador,
    )


def backfill(confirmar=False):
    """Cria as fichas faltantes. Dry-run (default) nao grava. Retorna {plano, criadas}."""
    alvos = chassis_pendentes_sem_ficha()
    criadas = 0
    for ev in alvos:
        categoria, origem, descricao, dev_item_id, doador = _params_ficha(ev)
        if not confirmar:
            continue
        detalhes = {'legacy_backfill': True}
        if doador:
            detalhes['chassi_doador'] = doador
        pendencia_service.abrir_pendencia(
            chassi=ev.chassi,
            categoria=categoria,
            origem=origem,
            descricao=descricao,
            evento_pendente_id=ev.id,
            devolucao_item_id=dev_item_id,
            operador_id=ev.operador_id,
            detalhes=detalhes,
        )
        criadas += 1
    if confirmar:
        db.session.commit()
    else:
        db.session.rollback()
    return {'plano': len(alvos), 'criadas': criadas}


def verificar():
    """Retorna quantos chassis PENDENTE ainda estao sem ficha (0 = cobertura ok)."""
    return len(chassis_pendentes_sem_ficha())


def main():
    parser = argparse.ArgumentParser(description='Backfill 35 — fichas de pendencia legadas.')
    parser.add_argument('--confirmar', action='store_true', help='Efetiva (default: dry-run).')
    parser.add_argument('--check', action='store_true',
                        help='So verifica cobertura; sai 1 se sobrou PENDENTE sem ficha.')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        if args.check:
            restantes = verificar()
            if restantes:
                print(f'[FAIL] {restantes} chassi(s) PENDENTE sem ficha.')
                sys.exit(1)
            print('[ok] cobertura completa: 0 PENDENTE sem ficha.')
            sys.exit(0)

        res = backfill(confirmar=args.confirmar)
        modo = 'CONFIRMADO' if args.confirmar else 'DRY-RUN'
        print(f'[{modo}] plano={res["plano"]} criadas={res["criadas"]}')
        if not args.confirmar and res['plano']:
            print('  (rode novamente com --confirmar para efetivar)')


if __name__ == '__main__':
    main()
```

- [ ] Rodar e ver passar: `pytest tests/motos_assai/test_backfill_pendencias.py -v` — Expected: PASS.
- [ ] Smoke do CLI `--check` (não deve estourar; pode sair 1 se houver PENDENTE legado no banco local): `source .venv/bin/activate && python scripts/migrations/motos_assai_35_backfill_pendencias.py --check; echo "exit=$?"` — Expected: imprime `[ok]` (exit=0) ou `[FAIL] N ...` (exit=1), sem traceback.
- [ ] Commit: `git add scripts/migrations/motos_assai_35_backfill_pendencias.py tests/motos_assai/test_backfill_pendencias.py && git commit -m "feat(motos_assai): backfill 35 cria assai_pendencia para PENDENTE legado (Spec 1 Task 11)"`

---

### Task 12: Schema JSON + TABLE_DESCRIPTIONS + doc do módulo

**Files:**
- Generate: `.claude/skills/consultando-sql/schemas/tables/assai_peca.json`, `assai_peca_modelo.json`, `assai_pendencia.json`, `assai_estoque_movimento.json`, `assai_peca_compra.json`, `assai_peca_compra_item.json` (+ `catalog.json`/`relationships.json` atualizados) via `generate_schemas.py`.
- Modify: `.claude/skills/consultando-sql/scripts/generate_schemas.py` (6 entradas em `TABLE_DESCRIPTIONS`).
- Modify: `app/motos_assai/CLAUDE.md` (29→35 tabelas; constantes novas; seção nova; remover stub `assai_avaria` do roadmap).

**Interfaces:**
- Consumes: os 6 models registrados em `app/motos_assai/models/__init__.py` (Faixas A/B) — auto-descobertos pelo gerador.
- Produces: 6 JSONs de schema + descrições no catálogo (consumidos pelo agente web via `mcp__sql__consultar_sql`); doc do módulo coerente.

**Precondição:** migration 34 aplicada no banco LOCAL (o gerador introspecta o banco).

Steps:
- [ ] Adicionar as 6 entradas em `TABLE_DESCRIPTIONS` (dentro do dict, antes do `}` final do bloco — escolher um ponto estável, ex.: logo após a seção de Devoluções/`# Recebimento`). Inserir:

```python
    # Motos Assaí — Estoque de Peças + Pendência categorizada (Spec 1, Migration 34)
    'assai_peca': 'Catalogo de pecas de reposicao Motos Assai (B2B Q.P.A.). Compatibilidade por modelo via assai_peca_modelo. Campos: codigo, nome, custo_referencia (fallback do custo medio), ativo. Saldo NAO mora aqui: e SUM(delta_almoxarifado) em assai_estoque_movimento.',
    'assai_peca_modelo': 'Compatibilidade N:N peca x modelo (assai_peca <-> assai_modelo). UNIQUE (peca_id, modelo_id).',
    'assai_pendencia': 'Ficha categorizada de pendencia de uma moto (chassi por valor). categoria (AVARIA/FALTA_PECA/REVISAO/VENDA/INDETERMINADA), origem (GALPAO/TRANSPORTE/POS_VENDA_CLIENTE/POS_VENDA_LOJA/DEVOLUCAO), tratativa (preenchida na resolucao), fase. Aberta = resolvida_em IS NULL AND cancelada_em IS NULL. evento_pendente_id NULL = nao afeta o estado da moto (pos-venda). pendencia_pai_id = filhas de REVISAO. Substitui a leitura de pendencias por eventos.',
    'assai_estoque_movimento': 'Ledger append-only de pecas (o elo central). tipo: ENTRADA/CONSUMO/CANIBALIZACAO/DESCARTE/AJUSTE. Saldo da peca = SUM(delta_almoxarifado) por peca_id (CANIBALIZACAO tem delta 0). custo_unitario congelado por linha; receita_* so em pendencia VENDA. Liga chassi_origem/chassi_destino, pendencia_id, compra_item_id.',
    'assai_peca_compra': 'Cabecalho de pedido de compra/garantia de pecas a Motochefe. numero PC-AAAA-NNNN (sequence/retry). tipo GARANTIA/COMPRA; status ABERTA/PARCIAL/RECEBIDA/CANCELADA. Itens em assai_peca_compra_item.',
    'assai_peca_compra_item': 'Item de assai_peca_compra. quantidade vs quantidade_recebida (recebimento gera ENTRADA no ledger e recalcula o status do cabecalho). pendencia_id = a ficha que motivou o item.',
```

- [ ] Aplicar migration 34 localmente se ainda não aplicada (precondição da Faixa A): `source .venv/bin/activate && python scripts/migrations/motos_assai_34_estoque_pecas_pendencia.py` — Expected: tabelas criadas/idempotente.
- [ ] Rodar e ver falhar o `--check` (as 6 tabelas existem no banco mas não há JSON em disco → drift): `source .venv/bin/activate && python .claude/skills/consultando-sql/scripts/generate_schemas.py --check; echo "exit=$?"` — Expected: FAIL (exit=1, drift listando os 6 `assai_*`).
- [ ] Gerar os schemas: `source .venv/bin/activate && python .claude/skills/consultando-sql/scripts/generate_schemas.py` — Expected: escreve os 6 JSONs novos + atualiza catalog/relationships.
- [ ] Verificar criação: `ls .claude/skills/consultando-sql/schemas/tables/ | grep -E "assai_(peca|peca_modelo|pendencia|estoque_movimento|peca_compra|peca_compra_item)\.json"` — Expected: 6 arquivos listados.
- [ ] Rodar e ver passar o `--check`: `source .venv/bin/activate && python .claude/skills/consultando-sql/scripts/generate_schemas.py --check; echo "exit=$?"` — Expected: PASS (exit=0, "sem drift").
- [ ] Atualizar `app/motos_assai/CLAUDE.md`: trocar todas as ocorrências de "29 tabelas" por "35 tabelas" (cabeçalho do índice, seção "Modelo de dados", "Convenções obrigatórias §1", "visão geral arquitetural"); na seção "Modelo de dados" acrescentar o bloco das 6 tabelas novas:

```markdown
Estoque de Peças + Pendência (Spec 1, Migration 34 — 6 tabelas): `assai_peca` +
`assai_peca_modelo` (catálogo + compatibilidade N:N por modelo); `assai_pendencia`
(ficha categorizada — categoria/origem/tratativa/fase, `pendencia_pai_id` p/ filhas
de REVISÃO, `evento_pendente_id` NULL = não afeta estado da moto); `assai_estoque_movimento`
(ledger append-only — saldo = `SUM(delta_almoxarifado)`); `assai_peca_compra` +
`assai_peca_compra_item` (pedido de compra/garantia à Motochefe, nº `PC-AAAA-NNNN`).
A pendência deixou de ser só o evento `PENDENTE`: o evento segue como verdade do
**estado físico** (1 por chassi), a ficha é a verdade do **tratamento** (N por chassi).
```

- [ ] Em `app/motos_assai/CLAUDE.md`, adicionar à "Lista de constantes/aliases por arquivo" as entradas dos 4 models novos:

```markdown
- `app/motos_assai/models/pendencia.py`: `PENDENCIA_CATEGORIA_*`, `PENDENCIA_CATEGORIAS_VALIDAS`, `PENDENCIA_ORIGEM_*`, `PENDENCIA_ORIGENS_VALIDAS`, `ORIGENS_FISICAS`, `PENDENCIA_FASE_*`, `PENDENCIA_FASES_VALIDAS`, `PENDENCIA_TRATATIVA_*`, `PENDENCIA_TRATATIVAS_VALIDAS`
- `app/motos_assai/models/estoque_movimento.py`: `MOVIMENTO_*`, `MOVIMENTO_TIPOS_VALIDOS`
- `app/motos_assai/models/peca_compra.py`: `COMPRA_PECA_TIPO_*`, `COMPRA_PECA_TIPOS_VALIDOS`, `COMPRA_PECA_STATUS_*`, `COMPRA_PECA_STATUS_VALIDOS`
```

- [ ] Em `app/motos_assai/CLAUDE.md`, adicionar uma seção nova "## Estoque de Peças + Pendência categorizada (Spec 1, 2026-06-30)" com o resumo: 3 verdades (evento físico / ficha de tratamento / ledger de peça); ciclo `abrir → [solicitar_compra] → resolver/cancelar`; predicado `afeta_estado_moto` (origem ∈ {GALPAO,TRANSPORTE,DEVOLUCAO} ou `devolucao_item_id` ou `retorno_fisico`); shim `montagem_service.resolver_pendencia` por chassi (delega a `pendencia_service.resolver_pendencia(pendencia_id=...)`, >1 ficha física = erro); leituras de `pendencia_service` migradas para a tabela; backfill `scripts/migrations/motos_assai_35_backfill_pendencias.py` (`--confirmar`/`--check`, NÃO no build.sh). Referência: `docs/superpowers/specs/2026-06-30-motos-assai-estoque-pecas-pendencia-design.md`.
- [ ] Em `app/motos_assai/CLAUDE.md`, no "Manutenção / Roadmap futuro", remover a linha do stub `- \`assai_avaria\` — tabela para avarias detectadas pós-recebimento (acréscimo ao wizard)` (substituída por `assai_pendencia(categoria=AVARIA)`); e remover/atualizar `- Resolver pendência via UI (atualmente só via service diretamente)` para apontar que a resolução por ficha + telas é o Spec 2.
- [ ] Confirmação final do gate: `source .venv/bin/activate && python .claude/skills/consultando-sql/scripts/generate_schemas.py --check; echo "exit=$?"` — Expected: PASS (exit=0).
- [ ] Commit: `git add .claude/skills/consultando-sql/scripts/generate_schemas.py .claude/skills/consultando-sql/schemas/ app/motos_assai/CLAUDE.md && git commit -m "docs(motos_assai): schema JSON + TABLE_DESCRIPTIONS das 6 tabelas + CLAUDE.md 35 tabelas (Spec 1 Task 12)"`
