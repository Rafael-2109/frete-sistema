# HORA — Transferência entre Filiais + Registro de Avaria — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implementar fluxo de transferência de motos entre lojas HORA com estado "em trânsito" (loja A emite, loja B confirma) e fluxo de registro de avaria em moto que já está no estoque (não bloqueia venda, fotos + descrição obrigatórias, múltiplas por chassi).

**Architecture:** 5 tabelas novas (`hora_transferencia`, `_item`, `_auditoria`, `hora_avaria`, `_foto`) seguindo padrão header+item+auditoria já estabelecido no módulo. 2 novos tipos de evento (`EM_TRANSITO`, `CANCELADA`) no log append-only `hora_moto_evento` (invariante 4). Services emitem eventos via `moto_service.registrar_evento()` e auditoria via padrão `recebimento_audit.registrar_auditoria()`. Avaria gera evento `AVARIADA` (já existente) e mantém moto vendável com badge na listagem de estoque.

**Tech Stack:** Python 3, Flask blueprints, SQLAlchemy, PostgreSQL, Jinja2, Bootstrap, S3 (AWS) para fotos, pytest (PostgreSQL de dev — `TESTING=true`). Convenções HORA: prefixo `hora_`, timezone naive Brasil via `agora_utc_naive()`, migrations dual (SQL + Python com `sys.path.insert`), schemas JSON auto-gerados em `.claude/skills/consultando-sql/schemas/tables/`.

**Spec:** `docs/superpowers/specs/2026-04-22-hora-transferencia-e-avaria-design.md` (commit `d3d3d8dc`).

---

## Mapa de Arquivos

### Criar (16)

| Caminho | Responsabilidade |
|---|---|
| `scripts/migrations/hora_15_transferencia_e_avaria.sql` | DDL idempotente das 5 tabelas |
| `scripts/migrations/hora_15_transferencia_e_avaria.py` | Migration Python: before/after + `create_app()` + `sys.path.insert` |
| `app/hora/models/transferencia.py` | `HoraTransferencia`, `HoraTransferenciaItem`, `HoraTransferenciaAuditoria` |
| `app/hora/models/avaria.py` | `HoraAvaria`, `HoraAvariaFoto` |
| `app/hora/services/avaria_service.py` | CRUD + regras de negócio de avaria + emissão evento |
| `app/hora/services/transferencia_audit.py` | `registrar_auditoria()` append-only (padrão `recebimento_audit`) |
| `app/hora/services/transferencia_service.py` | `criar_transferencia`, `confirmar_item_destino`, `finalizar_se_tudo_confirmado`, `cancelar_transferencia` |
| `app/hora/routes/avarias.py` | 6 endpoints CRUD + foto/resolver/ignorar |
| `app/hora/routes/transferencias.py` | 7 endpoints (lista, detalhe, nova, wizard, confirmar-item, cancelar, auditoria JSON) |
| `app/templates/hora/avarias_lista.html` | Lista com filtros |
| `app/templates/hora/avaria_nova.html` | Form: chassi autocomplete + descrição + upload N fotos |
| `app/templates/hora/avaria_detalhe.html` | Detalhe + galeria + ações |
| `app/templates/hora/transferencias_lista.html` | Lista com filtros |
| `app/templates/hora/transferencia_nova.html` | Form emissão: destino + multi-select chassis |
| `app/templates/hora/transferencia_detalhe.html` | Header + itens + timeline auditoria + botão cancelar |
| `app/templates/hora/transferencia_confirmar_wizard.html` | Wizard A-B-C no destino (scan QR + foto opcional + observação) |
| `tests/hora/__init__.py` | Pacote tests/hora |
| `tests/hora/conftest.py` | Fixtures: `loja_origem`, `loja_destino`, `chassi_em_estoque`, `usuario_admin`, `usuario_escopado` |
| `tests/hora/test_avaria_service.py` | Unit tests para `avaria_service` |
| `tests/hora/test_transferencia_service.py` | Unit tests para `transferencia_service` |
| `tests/hora/test_moto_service_novos_tipos.py` | Valida `EM_TRANSITO` e `CANCELADA` em `TIPOS_VALIDOS` |
| `tests/hora/test_estoque_eventos_em_estoque.py` | Valida `CANCELADA` incluído + `EM_TRANSITO` NÃO incluído |

### Modificar

| Caminho | O que muda |
|---|---|
| `app/hora/models/__init__.py` | Exportar 5 novas classes |
| `app/hora/services/moto_service.py:65-69` | `TIPOS_VALIDOS` += `EM_TRANSITO`, `CANCELADA` |
| `app/hora/services/estoque_service.py` | `EVENTOS_EM_ESTOQUE` += `CANCELADA`; novo helper `listar_em_transito()`; helper `avarias_abertas_por_chassi()` plugado |
| `app/hora/services/auth_helper.py` | Novo helper `loja_origem_permitida_para_transferencia()` |
| `app/hora/routes/__init__.py` | Importar blueprints `avarias` e `transferencias` |
| `app/templates/hora/estoque_lista.html` | Badges "↔ Em trânsito" + "⚠ Avariada (N)"; filtro `incluir_em_transito` |
| `app/templates/hora/estoque_chassi_detalhe.html` | Seções "Transferências" e "Avarias" na timeline |
| `app/templates/base.html` | 2 itens no dropdown "Lojas HORA" |
| `app/hora/CLAUDE.md` | Atualizar fase implementada (adicionar transferência + avaria) |

---

## Task 1: Estrutura de testes tests/hora/

**Files:**
- Create: `tests/hora/__init__.py`
- Create: `tests/hora/conftest.py`

- [ ] **Step 1: Criar pacote vazio**

```bash
mkdir -p tests/hora
```

Criar arquivo vazio:

```python
# tests/hora/__init__.py
```

- [ ] **Step 2: Criar conftest com fixtures reutilizáveis**

```python
# tests/hora/conftest.py
"""Fixtures compartilhadas dos testes HORA."""
import pytest

from app import db as _db
from app.hora.models import (
    HoraLoja, HoraModelo, HoraMoto, HoraMotoEvento,
)
from app.hora.services.moto_service import registrar_evento, get_or_create_moto


@pytest.fixture
def loja_origem(db):
    loja = HoraLoja(
        cnpj='11111111000101',
        apelido='LojaOrigem',
        razao_social='Loja Origem LTDA',
        nome_fantasia='Loja Origem',
        ativa=True,
    )
    _db.session.add(loja)
    _db.session.flush()
    return loja


@pytest.fixture
def loja_destino(db):
    loja = HoraLoja(
        cnpj='22222222000102',
        apelido='LojaDestino',
        razao_social='Loja Destino LTDA',
        nome_fantasia='Loja Destino',
        ativa=True,
    )
    _db.session.add(loja)
    _db.session.flush()
    return loja


@pytest.fixture
def modelo_moto(db):
    m = HoraModelo(nome_modelo='TESTE-MODEL', ativo=True)
    _db.session.add(m)
    _db.session.flush()
    return m


@pytest.fixture
def chassi_em_estoque(db, loja_origem, modelo_moto):
    """Cria moto e registra RECEBIDA + CONFERIDA na loja_origem."""
    chassi = '9ABCDTEST' + '1' * 12
    moto = get_or_create_moto(
        numero_chassi=chassi,
        modelo_nome=modelo_moto.nome_modelo,
        cor='PRETA',
        criado_por='fixture',
    )
    registrar_evento(
        numero_chassi=chassi, tipo='RECEBIDA',
        loja_id=loja_origem.id, operador='fixture',
    )
    registrar_evento(
        numero_chassi=chassi, tipo='CONFERIDA',
        loja_id=loja_origem.id, operador='fixture',
    )
    _db.session.flush()
    return chassi
```

- [ ] **Step 3: Rodar estrutura para validar imports**

Run: `pytest tests/hora/ --collect-only 2>&1 | head`

Expected: `collected 0 items` (sem erro de import).

- [ ] **Step 4: Commit**

```bash
git add tests/hora/__init__.py tests/hora/conftest.py
git commit -m "test(hora): estrutura inicial tests/hora com fixtures compartilhadas"
```

---

## Task 2: Migration SQL

**Files:**
- Create: `scripts/migrations/hora_15_transferencia_e_avaria.sql`

- [ ] **Step 1: Escrever DDL idempotente das 5 tabelas**

```sql
-- scripts/migrations/hora_15_transferencia_e_avaria.sql
-- Migration HORA 15: transferencia entre filiais + avaria em estoque.
-- Adiciona:
--   hora_transferencia (header: EM_TRANSITO|CONFIRMADA|CANCELADA)
--   hora_transferencia_item (N chassis por transferencia)
--   hora_transferencia_auditoria (append-only)
--   hora_avaria (header: ABERTA|RESOLVIDA|IGNORADA)
--   hora_avaria_foto (N fotos por avaria)
-- Idempotente: usa IF NOT EXISTS.

-- ============================================================
-- 1. hora_transferencia
-- ============================================================
CREATE TABLE IF NOT EXISTS hora_transferencia (
    id BIGSERIAL PRIMARY KEY,
    loja_origem_id INTEGER NOT NULL REFERENCES hora_loja(id),
    loja_destino_id INTEGER NOT NULL REFERENCES hora_loja(id),
    status VARCHAR(30) NOT NULL,
    emitida_em TIMESTAMP NOT NULL,
    emitida_por VARCHAR(100) NOT NULL,
    confirmada_em TIMESTAMP NULL,
    confirmada_por VARCHAR(100) NULL,
    cancelada_em TIMESTAMP NULL,
    cancelada_por VARCHAR(100) NULL,
    motivo_cancelamento VARCHAR(255) NULL,
    observacoes TEXT NULL,
    criado_em TIMESTAMP NOT NULL,
    atualizado_em TIMESTAMP NOT NULL,
    CONSTRAINT ck_hora_transferencia_lojas_distintas
        CHECK (loja_origem_id <> loja_destino_id),
    CONSTRAINT ck_hora_transferencia_motivo_quando_cancelada
        CHECK (
            (cancelada_em IS NULL AND motivo_cancelamento IS NULL)
            OR (cancelada_em IS NOT NULL
                AND motivo_cancelamento IS NOT NULL
                AND length(trim(motivo_cancelamento)) >= 3)
        ),
    CONSTRAINT ck_hora_transferencia_confirmada_apos_emitida
        CHECK (confirmada_em IS NULL OR confirmada_em >= emitida_em),
    CONSTRAINT ck_hora_transferencia_cancelada_apos_emitida
        CHECK (cancelada_em IS NULL OR cancelada_em >= emitida_em),
    CONSTRAINT ck_hora_transferencia_exclusivo_final
        CHECK (NOT (confirmada_em IS NOT NULL AND cancelada_em IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS ix_hora_transferencia_status
    ON hora_transferencia(status);
CREATE INDEX IF NOT EXISTS ix_hora_transferencia_loja_origem
    ON hora_transferencia(loja_origem_id);
CREATE INDEX IF NOT EXISTS ix_hora_transferencia_loja_destino
    ON hora_transferencia(loja_destino_id);

-- ============================================================
-- 2. hora_transferencia_item
-- ============================================================
CREATE TABLE IF NOT EXISTS hora_transferencia_item (
    id BIGSERIAL PRIMARY KEY,
    transferencia_id INTEGER NOT NULL REFERENCES hora_transferencia(id) ON DELETE CASCADE,
    numero_chassi VARCHAR(30) NOT NULL REFERENCES hora_moto(numero_chassi),
    conferido_destino_em TIMESTAMP NULL,
    conferido_destino_por VARCHAR(100) NULL,
    qr_code_lido BOOLEAN NOT NULL DEFAULT FALSE,
    foto_s3_key VARCHAR(500) NULL,
    observacao_item TEXT NULL,
    CONSTRAINT uq_hora_transferencia_item_chassi
        UNIQUE (transferencia_id, numero_chassi)
);

CREATE INDEX IF NOT EXISTS ix_hora_transferencia_item_transferencia
    ON hora_transferencia_item(transferencia_id);
CREATE INDEX IF NOT EXISTS ix_hora_transferencia_item_chassi
    ON hora_transferencia_item(numero_chassi);

-- ============================================================
-- 3. hora_transferencia_auditoria (append-only)
-- ============================================================
CREATE TABLE IF NOT EXISTS hora_transferencia_auditoria (
    id BIGSERIAL PRIMARY KEY,
    transferencia_id INTEGER NOT NULL REFERENCES hora_transferencia(id) ON DELETE CASCADE,
    item_id INTEGER NULL REFERENCES hora_transferencia_item(id),
    usuario VARCHAR(100) NOT NULL,
    acao VARCHAR(40) NOT NULL,
    campo_alterado VARCHAR(60) NULL,
    valor_antes TEXT NULL,
    valor_depois TEXT NULL,
    detalhe TEXT NULL,
    criado_em TIMESTAMP NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_hora_transferencia_auditoria_transf
    ON hora_transferencia_auditoria(transferencia_id);
CREATE INDEX IF NOT EXISTS ix_hora_transferencia_auditoria_item
    ON hora_transferencia_auditoria(item_id);
CREATE INDEX IF NOT EXISTS ix_hora_transferencia_auditoria_acao
    ON hora_transferencia_auditoria(acao);
CREATE INDEX IF NOT EXISTS ix_hora_transferencia_auditoria_timeline
    ON hora_transferencia_auditoria(transferencia_id, criado_em DESC);

-- ============================================================
-- 4. hora_avaria
-- ============================================================
CREATE TABLE IF NOT EXISTS hora_avaria (
    id BIGSERIAL PRIMARY KEY,
    numero_chassi VARCHAR(30) NOT NULL REFERENCES hora_moto(numero_chassi),
    loja_id INTEGER NOT NULL REFERENCES hora_loja(id),
    descricao TEXT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'ABERTA',
    criado_em TIMESTAMP NOT NULL,
    criado_por VARCHAR(100) NOT NULL,
    resolvido_em TIMESTAMP NULL,
    resolvido_por VARCHAR(100) NULL,
    resolucao_observacao TEXT NULL,
    CONSTRAINT ck_hora_avaria_descricao_nao_vazia
        CHECK (length(trim(descricao)) >= 3),
    CONSTRAINT ck_hora_avaria_resolvida_tem_status
        CHECK (resolvido_em IS NULL OR status IN ('RESOLVIDA','IGNORADA'))
);

CREATE INDEX IF NOT EXISTS ix_hora_avaria_chassi
    ON hora_avaria(numero_chassi);
CREATE INDEX IF NOT EXISTS ix_hora_avaria_loja
    ON hora_avaria(loja_id);
CREATE INDEX IF NOT EXISTS ix_hora_avaria_status
    ON hora_avaria(status);
CREATE INDEX IF NOT EXISTS ix_hora_avaria_criado_em
    ON hora_avaria(criado_em);

-- ============================================================
-- 5. hora_avaria_foto
-- ============================================================
CREATE TABLE IF NOT EXISTS hora_avaria_foto (
    id BIGSERIAL PRIMARY KEY,
    avaria_id INTEGER NOT NULL REFERENCES hora_avaria(id) ON DELETE CASCADE,
    foto_s3_key VARCHAR(500) NOT NULL,
    legenda VARCHAR(255) NULL,
    criado_em TIMESTAMP NOT NULL,
    criado_por VARCHAR(100) NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_hora_avaria_foto_avaria
    ON hora_avaria_foto(avaria_id);
```

- [ ] **Step 2: Commit**

```bash
git add scripts/migrations/hora_15_transferencia_e_avaria.sql
git commit -m "migration(hora_15): DDL transferencia + avaria (SQL)"
```

---

## Task 3: Migration Python

**Files:**
- Create: `scripts/migrations/hora_15_transferencia_e_avaria.py`

- [ ] **Step 1: Escrever migration Python com before/after**

```python
"""Migration HORA 15: transferencia entre filiais + avaria em estoque.

Executa o DDL de hora_15_transferencia_e_avaria.sql idempotentemente e reporta
existencia das 5 tabelas antes/depois.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


TABELAS = (
    'hora_transferencia',
    'hora_transferencia_item',
    'hora_transferencia_auditoria',
    'hora_avaria',
    'hora_avaria_foto',
)


def tabela_existe(nome: str) -> bool:
    return bool(db.session.execute(
        db.text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"),
        {'t': nome},
    ).scalar())


def verificar(label: str):
    print(f"[{label}]")
    for t in TABELAS:
        print(f"  {t}: {'existe' if tabela_existe(t) else 'NAO existe'}")


def executar_ddl():
    path = os.path.join(os.path.dirname(__file__), 'hora_15_transferencia_e_avaria.sql')
    with open(path, encoding='utf-8') as f:
        sql = f.read()
    # PostgreSQL aceita multiplos statements em um execute via db.text
    db.session.execute(db.text(sql))
    db.session.commit()


def main():
    app = create_app()
    with app.app_context():
        verificar('BEFORE')
        print("\n[APLICANDO DDL...]")
        executar_ddl()
        print("OK.\n")
        verificar('AFTER')


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: Rodar migration no banco local**

Run: `source .venv/bin/activate && python scripts/migrations/hora_15_transferencia_e_avaria.py`

Expected:
```
[BEFORE]
  hora_transferencia: NAO existe
  hora_transferencia_item: NAO existe
  hora_transferencia_auditoria: NAO existe
  hora_avaria: NAO existe
  hora_avaria_foto: NAO existe

[APLICANDO DDL...]
OK.

[AFTER]
  hora_transferencia: existe
  hora_transferencia_item: existe
  hora_transferencia_auditoria: existe
  hora_avaria: existe
  hora_avaria_foto: existe
```

- [ ] **Step 3: Validar reexecução é idempotente**

Run: `python scripts/migrations/hora_15_transferencia_e_avaria.py`

Expected: ambos BEFORE e AFTER reportam "existe" (sem erro).

- [ ] **Step 4: Commit**

```bash
git add scripts/migrations/hora_15_transferencia_e_avaria.py
git commit -m "migration(hora_15): Python driver + verificacao before/after"
```

---

## Task 4: Models SQLAlchemy

**Files:**
- Create: `app/hora/models/transferencia.py`
- Create: `app/hora/models/avaria.py`
- Modify: `app/hora/models/__init__.py`

- [ ] **Step 1: Criar `app/hora/models/transferencia.py`**

```python
"""Models de transferencia entre filiais HORA.

Padrao header + item + auditoria (append-only), espelhando hora_recebimento +
hora_recebimento_conferencia + hora_conferencia_auditoria.
"""
from app import db
from app.utils.timezone import agora_utc_naive


class HoraTransferencia(db.Model):
    __tablename__ = 'hora_transferencia'

    id = db.Column(db.BigInteger, primary_key=True)
    loja_origem_id = db.Column(db.Integer, db.ForeignKey('hora_loja.id'), nullable=False, index=True)
    loja_destino_id = db.Column(db.Integer, db.ForeignKey('hora_loja.id'), nullable=False, index=True)
    status = db.Column(db.String(30), nullable=False, index=True)
    emitida_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    emitida_por = db.Column(db.String(100), nullable=False)
    confirmada_em = db.Column(db.DateTime, nullable=True)
    confirmada_por = db.Column(db.String(100), nullable=True)
    cancelada_em = db.Column(db.DateTime, nullable=True)
    cancelada_por = db.Column(db.String(100), nullable=True)
    motivo_cancelamento = db.Column(db.String(255), nullable=True)
    observacoes = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive, onupdate=agora_utc_naive)

    loja_origem = db.relationship('HoraLoja', foreign_keys=[loja_origem_id])
    loja_destino = db.relationship('HoraLoja', foreign_keys=[loja_destino_id])
    itens = db.relationship(
        'HoraTransferenciaItem',
        backref='transferencia',
        cascade='all, delete-orphan',
        lazy='selectin',
    )
    auditoria = db.relationship(
        'HoraTransferenciaAuditoria',
        backref='transferencia',
        cascade='all, delete-orphan',
        lazy='selectin',
        order_by='HoraTransferenciaAuditoria.criado_em.desc()',
    )


class HoraTransferenciaItem(db.Model):
    __tablename__ = 'hora_transferencia_item'

    id = db.Column(db.BigInteger, primary_key=True)
    transferencia_id = db.Column(db.Integer, db.ForeignKey('hora_transferencia.id', ondelete='CASCADE'), nullable=False, index=True)
    numero_chassi = db.Column(db.String(30), db.ForeignKey('hora_moto.numero_chassi'), nullable=False, index=True)
    conferido_destino_em = db.Column(db.DateTime, nullable=True)
    conferido_destino_por = db.Column(db.String(100), nullable=True)
    qr_code_lido = db.Column(db.Boolean, nullable=False, default=False)
    foto_s3_key = db.Column(db.String(500), nullable=True)
    observacao_item = db.Column(db.Text, nullable=True)

    __table_args__ = (
        db.UniqueConstraint('transferencia_id', 'numero_chassi', name='uq_hora_transferencia_item_chassi'),
    )

    @property
    def esta_confirmado(self) -> bool:
        return self.conferido_destino_em is not None


class HoraTransferenciaAuditoria(db.Model):
    __tablename__ = 'hora_transferencia_auditoria'

    id = db.Column(db.BigInteger, primary_key=True)
    transferencia_id = db.Column(db.Integer, db.ForeignKey('hora_transferencia.id', ondelete='CASCADE'), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('hora_transferencia_item.id'), nullable=True, index=True)
    usuario = db.Column(db.String(100), nullable=False)
    acao = db.Column(db.String(40), nullable=False, index=True)
    campo_alterado = db.Column(db.String(60), nullable=True)
    valor_antes = db.Column(db.Text, nullable=True)
    valor_depois = db.Column(db.Text, nullable=True)
    detalhe = db.Column(db.Text, nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
```

- [ ] **Step 2: Criar `app/hora/models/avaria.py`**

```python
"""Models de avaria em moto do estoque HORA.

Padrao header + N fotos, espelhando hora_peca_faltando + hora_peca_faltando_foto.
Avaria NAO bloqueia venda — apenas registra + emite evento AVARIADA.
"""
from app import db
from app.utils.timezone import agora_utc_naive


class HoraAvaria(db.Model):
    __tablename__ = 'hora_avaria'

    id = db.Column(db.BigInteger, primary_key=True)
    numero_chassi = db.Column(db.String(30), db.ForeignKey('hora_moto.numero_chassi'), nullable=False, index=True)
    loja_id = db.Column(db.Integer, db.ForeignKey('hora_loja.id'), nullable=False, index=True)
    descricao = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='ABERTA', index=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive, index=True)
    criado_por = db.Column(db.String(100), nullable=False)
    resolvido_em = db.Column(db.DateTime, nullable=True)
    resolvido_por = db.Column(db.String(100), nullable=True)
    resolucao_observacao = db.Column(db.Text, nullable=True)

    loja = db.relationship('HoraLoja')
    fotos = db.relationship(
        'HoraAvariaFoto',
        backref='avaria',
        cascade='all, delete-orphan',
        lazy='selectin',
        order_by='HoraAvariaFoto.criado_em',
    )

    @property
    def esta_aberta(self) -> bool:
        return self.status == 'ABERTA'


class HoraAvariaFoto(db.Model):
    __tablename__ = 'hora_avaria_foto'

    id = db.Column(db.BigInteger, primary_key=True)
    avaria_id = db.Column(db.Integer, db.ForeignKey('hora_avaria.id', ondelete='CASCADE'), nullable=False, index=True)
    foto_s3_key = db.Column(db.String(500), nullable=False)
    legenda = db.Column(db.String(255), nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)
```

- [ ] **Step 3: Atualizar `app/hora/models/__init__.py` com exports**

Adicionar estas linhas (manter exports existentes):

```python
from app.hora.models.transferencia import (  # noqa: F401
    HoraTransferencia,
    HoraTransferenciaItem,
    HoraTransferenciaAuditoria,
)
from app.hora.models.avaria import (  # noqa: F401
    HoraAvaria,
    HoraAvariaFoto,
)
```

Incluir nomes em `__all__` (se existir no arquivo). Se não houver `__all__`, os imports acima são suficientes.

- [ ] **Step 4: Smoke test de import**

Run:
```bash
source .venv/bin/activate
python -c "from app import create_app; app=create_app(); \
  from app.hora.models import HoraTransferencia, HoraTransferenciaItem, HoraTransferenciaAuditoria, HoraAvaria, HoraAvariaFoto; \
  print('OK — 5 models importados')"
```

Expected: `OK — 5 models importados`

- [ ] **Step 5: Commit**

```bash
git add app/hora/models/transferencia.py app/hora/models/avaria.py app/hora/models/__init__.py
git commit -m "feat(hora/models): transferencia (header+item+auditoria) + avaria (header+foto)"
```

---

## Task 5: Adicionar EM_TRANSITO e CANCELADA em TIPOS_VALIDOS

**Files:**
- Modify: `app/hora/services/moto_service.py:65-69`
- Create: `tests/hora/test_moto_service_novos_tipos.py`

- [ ] **Step 1: Escrever teste que FALHA atualmente**

```python
# tests/hora/test_moto_service_novos_tipos.py
"""Valida que EM_TRANSITO e CANCELADA estao em TIPOS_VALIDOS."""
import pytest

from app.hora.services.moto_service import registrar_evento


def test_em_transito_e_tipo_valido(chassi_em_estoque, loja_destino):
    ev = registrar_evento(
        numero_chassi=chassi_em_estoque,
        tipo='EM_TRANSITO',
        loja_id=loja_destino.id,
        operador='teste',
    )
    assert ev.tipo == 'EM_TRANSITO'


def test_cancelada_e_tipo_valido(chassi_em_estoque, loja_origem):
    ev = registrar_evento(
        numero_chassi=chassi_em_estoque,
        tipo='CANCELADA',
        loja_id=loja_origem.id,
        operador='teste',
    )
    assert ev.tipo == 'CANCELADA'


def test_tipo_invalido_falha(chassi_em_estoque, loja_origem):
    with pytest.raises(ValueError, match="Tipo de evento inválido"):
        registrar_evento(
            numero_chassi=chassi_em_estoque,
            tipo='INEXISTENTE',
            loja_id=loja_origem.id,
            operador='teste',
        )
```

- [ ] **Step 2: Rodar o teste — deve falhar**

Run: `pytest tests/hora/test_moto_service_novos_tipos.py -v`

Expected: `test_em_transito_e_tipo_valido` e `test_cancelada_e_tipo_valido` FAIL com `ValueError: Tipo de evento inválido: EM_TRANSITO/CANCELADA`.

- [ ] **Step 3: Adicionar os 2 tipos em `TIPOS_VALIDOS`**

Editar `app/hora/services/moto_service.py` linhas 65-69:

```python
    TIPOS_VALIDOS = {
        'RECEBIDA', 'CONFERIDA', 'TRANSFERIDA',
        'EM_TRANSITO', 'CANCELADA',
        'RESERVADA', 'VENDIDA', 'DEVOLVIDA', 'AVARIADA',
        'FALTANDO_PECA',
    }
```

- [ ] **Step 4: Rodar teste — deve passar**

Run: `pytest tests/hora/test_moto_service_novos_tipos.py -v`

Expected: 3 tests PASS.

- [ ] **Step 5: Commit**

```bash
git add app/hora/services/moto_service.py tests/hora/test_moto_service_novos_tipos.py
git commit -m "feat(hora/moto_service): adiciona tipos EM_TRANSITO e CANCELADA"
```

---

## Task 6: Ajustar EVENTOS_EM_ESTOQUE + helper listar_em_transito

**Files:**
- Modify: `app/hora/services/estoque_service.py`
- Create: `tests/hora/test_estoque_eventos_em_estoque.py`

- [ ] **Step 1: Inspecionar `estoque_service.py` e localizar constante**

Run: `grep -n "EVENTOS_EM_ESTOQUE" app/hora/services/estoque_service.py`

Anote a linha onde a tupla está definida.

- [ ] **Step 2: Escrever teste que FALHA (CANCELADA deve ficar visível em estoque)**

```python
# tests/hora/test_estoque_eventos_em_estoque.py
"""Valida ajustes em EVENTOS_EM_ESTOQUE e novo helper listar_em_transito."""
import pytest

from app.hora.services import estoque_service
from app.hora.services.moto_service import registrar_evento


def test_cancelada_esta_em_eventos_em_estoque():
    """Moto com ultimo evento CANCELADA deve ser visivel no estoque (voltou origem)."""
    assert 'CANCELADA' in estoque_service.EVENTOS_EM_ESTOQUE


def test_em_transito_nao_esta_em_eventos_em_estoque():
    """Moto em transito esta em limbo — nao conta como estoque de nenhuma loja."""
    assert 'EM_TRANSITO' not in estoque_service.EVENTOS_EM_ESTOQUE


def test_listar_em_transito_retorna_moto_recem_emitida(db, chassi_em_estoque, loja_origem, loja_destino):
    registrar_evento(
        numero_chassi=chassi_em_estoque, tipo='EM_TRANSITO',
        loja_id=loja_destino.id, operador='teste',
    )
    db.session.flush()
    em_transito = estoque_service.listar_em_transito(lojas_permitidas_ids=[loja_destino.id])
    chassis = [m['numero_chassi'] for m in em_transito]
    assert chassi_em_estoque in chassis


def test_listar_em_transito_filtrado_por_loja_permitida(db, chassi_em_estoque, loja_origem, loja_destino):
    registrar_evento(
        numero_chassi=chassi_em_estoque, tipo='EM_TRANSITO',
        loja_id=loja_destino.id, operador='teste',
    )
    db.session.flush()
    # Loja diferente nao ve
    em_transito = estoque_service.listar_em_transito(lojas_permitidas_ids=[999])
    assert all(m['numero_chassi'] != chassi_em_estoque for m in em_transito)
```

- [ ] **Step 3: Rodar — deve falhar**

Run: `pytest tests/hora/test_estoque_eventos_em_estoque.py -v`

Expected: 4 FAIL (CANCELADA não em estoque; `listar_em_transito` AttributeError).

- [ ] **Step 4: Atualizar `EVENTOS_EM_ESTOQUE`**

Editar em `app/hora/services/estoque_service.py`:

```python
EVENTOS_EM_ESTOQUE = (
    'RECEBIDA', 'CONFERIDA', 'TRANSFERIDA',
    'CANCELADA',
    'AVARIADA', 'FALTANDO_PECA',
)
```

- [ ] **Step 5: Adicionar helper `listar_em_transito`**

Ao fim do `estoque_service.py`:

```python
def listar_em_transito(lojas_permitidas_ids=None):
    """Motos com ultimo evento EM_TRANSITO, filtrado por loja_id do evento."""
    from app.hora.models import HoraMoto, HoraMotoEvento, HoraModelo, HoraLoja

    sub = _subquery_ultimo_evento_id()  # helper existente: (chassi, max_id)

    q = (
        db.session.query(
            HoraMoto.numero_chassi,
            HoraModelo.nome_modelo,
            HoraMoto.cor,
            HoraLoja.id.label('loja_id'),
            HoraLoja.apelido.label('loja_nome'),
            HoraMotoEvento.timestamp,
        )
        .join(sub, HoraMoto.numero_chassi == sub.c.numero_chassi)
        .join(HoraMotoEvento, HoraMotoEvento.id == sub.c.ultimo_evento_id)
        .join(HoraModelo, HoraModelo.id == HoraMoto.modelo_id)
        .outerjoin(HoraLoja, HoraLoja.id == HoraMotoEvento.loja_id)
        .filter(HoraMotoEvento.tipo == 'EM_TRANSITO')
    )
    if lojas_permitidas_ids is not None:
        q = q.filter(HoraMotoEvento.loja_id.in_(lojas_permitidas_ids))
    return [dict(r._mapping) for r in q.all()]
```

Se `_subquery_ultimo_evento_id` não for a função exata, inspecionar `estoque_service.py` e usar a função privada equivalente (ela já está pronta no código — deriva subquery de `(numero_chassi, max(id))`).

- [ ] **Step 6: Rodar — deve passar**

Run: `pytest tests/hora/test_estoque_eventos_em_estoque.py -v`

Expected: 4 PASS.

- [ ] **Step 7: Commit**

```bash
git add app/hora/services/estoque_service.py tests/hora/test_estoque_eventos_em_estoque.py
git commit -m "feat(hora/estoque): inclui CANCELADA em estoque + helper listar_em_transito"
```

---

## Task 7: Helper `loja_origem_permitida_para_transferencia`

**Files:**
- Modify: `app/hora/services/auth_helper.py`
- Create: `tests/hora/test_auth_helper_transferencia.py`

- [ ] **Step 1: Inspecionar auth_helper atual**

Run: `grep -n "^def " app/hora/services/auth_helper.py`

- [ ] **Step 2: Escrever teste (sem fixtures de login pesadas — mock `current_user`)**

```python
# tests/hora/test_auth_helper_transferencia.py
"""Valida helper loja_origem_permitida_para_transferencia."""
from unittest.mock import patch, MagicMock


def _mock_user(perfil, loja_hora_id):
    u = MagicMock()
    u.perfil = perfil
    u.loja_hora_id = loja_hora_id
    u.is_authenticated = True
    return u


def test_admin_pode_escolher_qualquer_origem(app):
    from app.hora.services.auth_helper import loja_origem_permitida_para_transferencia
    with app.test_request_context():
        with patch('app.hora.services.auth_helper.current_user', _mock_user('administrador', None)):
            assert loja_origem_permitida_para_transferencia() is None


def test_escopado_recebe_sua_loja(app):
    from app.hora.services.auth_helper import loja_origem_permitida_para_transferencia
    with app.test_request_context():
        with patch('app.hora.services.auth_helper.current_user', _mock_user('operador', 42)):
            assert loja_origem_permitida_para_transferencia() == 42


def test_usuario_sem_loja_nao_permite(app):
    from app.hora.services.auth_helper import loja_origem_permitida_para_transferencia
    with app.test_request_context():
        with patch('app.hora.services.auth_helper.current_user', _mock_user('operador', None)):
            # Sem loja_hora_id definido, usuario nao-admin nao pode emitir
            result = loja_origem_permitida_para_transferencia()
            assert result is None or result == 0
            # Service vai rejeitar depois com "usuario sem loja atribuida"
```

- [ ] **Step 3: Rodar — deve falhar (função não existe)**

Run: `pytest tests/hora/test_auth_helper_transferencia.py -v`

Expected: `ImportError: cannot import name 'loja_origem_permitida_para_transferencia'`.

- [ ] **Step 4: Implementar helper**

Adicionar ao fim de `app/hora/services/auth_helper.py`:

```python
def loja_origem_permitida_para_transferencia():
    """Loja obrigatoria como origem quando usuario e escopado.

    Returns:
        - None se user e admin (pode escolher qualquer origem) ou sem loja atribuida
        - int (loja_hora_id) se user e escopado a 1 loja
    """
    if not current_user.is_authenticated:
        return None
    if getattr(current_user, 'perfil', None) == 'administrador':
        return None
    return getattr(current_user, 'loja_hora_id', None)
```

- [ ] **Step 5: Rodar — deve passar**

Run: `pytest tests/hora/test_auth_helper_transferencia.py -v`

Expected: 3 PASS.

- [ ] **Step 6: Commit**

```bash
git add app/hora/services/auth_helper.py tests/hora/test_auth_helper_transferencia.py
git commit -m "feat(hora/auth_helper): loja_origem_permitida_para_transferencia"
```

---

## Task 8: avaria_service.py completo

**Files:**
- Create: `app/hora/services/avaria_service.py`
- Create: `tests/hora/test_avaria_service.py`

- [ ] **Step 1: Escrever testes (mais amplos, TDD)**

```python
# tests/hora/test_avaria_service.py
"""Tests do avaria_service: regras de negocio da avaria."""
import pytest

from app import db as _db
from app.hora.models import HoraAvaria, HoraAvariaFoto, HoraMotoEvento
from app.hora.services import avaria_service


FOTOS_OK = [('s3://hora/avarias/test/1.jpg', 'foto frontal')]


def test_registrar_avaria_cria_header_foto_e_evento(db, chassi_em_estoque, loja_origem):
    avaria = avaria_service.registrar_avaria(
        numero_chassi=chassi_em_estoque,
        descricao='arranhao profundo no para-lama',
        fotos=FOTOS_OK,
        usuario='operador_x',
        loja_id=loja_origem.id,
    )
    assert avaria.id is not None
    assert avaria.status == 'ABERTA'
    assert len(avaria.fotos) == 1
    assert avaria.fotos[0].foto_s3_key == 's3://hora/avarias/test/1.jpg'
    # Evento AVARIADA emitido
    ev = (HoraMotoEvento.query
          .filter_by(numero_chassi=chassi_em_estoque, tipo='AVARIADA')
          .order_by(HoraMotoEvento.id.desc()).first())
    assert ev is not None
    assert ev.origem_tabela == 'hora_avaria'
    assert ev.origem_id == avaria.id


def test_registrar_sem_foto_falha(db, chassi_em_estoque, loja_origem):
    with pytest.raises(ValueError, match=r"pelo menos 1 foto"):
        avaria_service.registrar_avaria(
            numero_chassi=chassi_em_estoque,
            descricao='dano',
            fotos=[],
            usuario='x',
            loja_id=loja_origem.id,
        )


def test_descricao_curta_falha(db, chassi_em_estoque, loja_origem):
    with pytest.raises(ValueError, match=r"descricao"):
        avaria_service.registrar_avaria(
            numero_chassi=chassi_em_estoque,
            descricao='.',
            fotos=FOTOS_OK,
            usuario='x',
            loja_id=loja_origem.id,
        )


def test_chassi_inexistente_falha(db, loja_origem):
    with pytest.raises(ValueError, match=r"chassi"):
        avaria_service.registrar_avaria(
            numero_chassi='9CHASSIINEXISTENTE000000000',
            descricao='dano',
            fotos=FOTOS_OK,
            usuario='x',
            loja_id=loja_origem.id,
        )


def test_multiplas_avarias_no_mesmo_chassi(db, chassi_em_estoque, loja_origem):
    a1 = avaria_service.registrar_avaria(
        numero_chassi=chassi_em_estoque,
        descricao='primeira ocorrencia',
        fotos=FOTOS_OK, usuario='x', loja_id=loja_origem.id,
    )
    a2 = avaria_service.registrar_avaria(
        numero_chassi=chassi_em_estoque,
        descricao='segunda ocorrencia diferente',
        fotos=FOTOS_OK, usuario='x', loja_id=loja_origem.id,
    )
    assert a1.id != a2.id
    # Ambas contam como abertas
    abertas = avaria_service.avarias_abertas_por_chassi([chassi_em_estoque])
    assert abertas[chassi_em_estoque] == 2


def test_resolver_avaria_muda_status_e_preenche_auditoria(db, chassi_em_estoque, loja_origem):
    a = avaria_service.registrar_avaria(
        numero_chassi=chassi_em_estoque, descricao='dano',
        fotos=FOTOS_OK, usuario='x', loja_id=loja_origem.id,
    )
    assert a.status == 'ABERTA'
    avaria_service.resolver_avaria(a.id, 'consertada na oficina', 'chefe')
    _db.session.refresh(a)
    assert a.status == 'RESOLVIDA'
    assert a.resolvido_por == 'chefe'
    assert a.resolucao_observacao == 'consertada na oficina'


def test_ignorar_avaria(db, chassi_em_estoque, loja_origem):
    a = avaria_service.registrar_avaria(
        numero_chassi=chassi_em_estoque, descricao='dano',
        fotos=FOTOS_OK, usuario='x', loja_id=loja_origem.id,
    )
    avaria_service.ignorar_avaria(a.id, 'pre-existente', 'chefe')
    _db.session.refresh(a)
    assert a.status == 'IGNORADA'


def test_adicionar_foto_depois(db, chassi_em_estoque, loja_origem):
    a = avaria_service.registrar_avaria(
        numero_chassi=chassi_em_estoque, descricao='dano',
        fotos=FOTOS_OK, usuario='x', loja_id=loja_origem.id,
    )
    foto = avaria_service.adicionar_foto(a.id, 's3://hora/avarias/test/extra.jpg', 'lado direito', 'outro')
    assert foto.id is not None
    _db.session.refresh(a)
    assert len(a.fotos) == 2


def test_avarias_abertas_por_chassi_batch(db, chassi_em_estoque, loja_origem):
    assert avaria_service.avarias_abertas_por_chassi([chassi_em_estoque]) == {}
    avaria_service.registrar_avaria(
        numero_chassi=chassi_em_estoque, descricao='x1',
        fotos=FOTOS_OK, usuario='u', loja_id=loja_origem.id,
    )
    avaria_service.registrar_avaria(
        numero_chassi=chassi_em_estoque, descricao='x2',
        fotos=FOTOS_OK, usuario='u', loja_id=loja_origem.id,
    )
    result = avaria_service.avarias_abertas_por_chassi([chassi_em_estoque])
    assert result[chassi_em_estoque] == 2


def test_chassi_nao_em_estoque_falha(db, chassi_em_estoque, loja_origem, modelo_moto):
    """Nao pode avariar moto ja vendida/devolvida."""
    from app.hora.services.moto_service import registrar_evento
    registrar_evento(
        numero_chassi=chassi_em_estoque, tipo='VENDIDA',
        loja_id=loja_origem.id, operador='teste',
    )
    _db.session.flush()
    with pytest.raises(ValueError, match=r"estoque"):
        avaria_service.registrar_avaria(
            numero_chassi=chassi_em_estoque, descricao='tentativa',
            fotos=FOTOS_OK, usuario='x', loja_id=loja_origem.id,
        )
```

- [ ] **Step 2: Rodar — deve falhar (service não existe)**

Run: `pytest tests/hora/test_avaria_service.py -v`

Expected: todos FAIL com `ModuleNotFoundError`.

- [ ] **Step 3: Implementar `avaria_service.py`**

```python
# app/hora/services/avaria_service.py
"""Service de avaria em moto de estoque HORA.

Regra-chave: avaria NAO bloqueia venda. Apenas registra + emite evento
AVARIADA em hora_moto_evento (para consulta historica). Moto continua
em estoque vendavel (AVARIADA esta em EVENTOS_EM_ESTOQUE).
"""
from __future__ import annotations

from typing import Iterable, Optional

from app import db
from app.hora.models import HoraAvaria, HoraAvariaFoto, HoraMoto, HoraMotoEvento
from app.hora.services.moto_service import registrar_evento
from app.hora.services.estoque_service import EVENTOS_EM_ESTOQUE


def _ultimo_evento_tipo(numero_chassi: str) -> Optional[str]:
    ev = (
        HoraMotoEvento.query
        .filter_by(numero_chassi=numero_chassi)
        .order_by(HoraMotoEvento.timestamp.desc())
        .first()
    )
    return ev.tipo if ev else None


def registrar_avaria(
    numero_chassi: str,
    descricao: str,
    fotos: Iterable[tuple],  # list of (foto_s3_key, legenda_opcional)
    usuario: str,
    loja_id: int,
) -> HoraAvaria:
    """Cria avaria + N fotos na mesma transaction. Emite evento AVARIADA.

    Raises:
        ValueError: se ≥1 foto nao fornecida, descricao < 3 chars,
                    chassi inexistente, ou chassi fora de estoque.
    """
    fotos_list = list(fotos)
    if not fotos_list:
        raise ValueError("Avaria requer pelo menos 1 foto")

    desc_limpa = (descricao or '').strip()
    if len(desc_limpa) < 3:
        raise ValueError("descricao deve ter pelo menos 3 caracteres")

    chassi_norm = numero_chassi.strip().upper()
    moto = HoraMoto.query.get(chassi_norm)
    if not moto:
        raise ValueError(f"chassi inexistente: {chassi_norm}")

    ultimo = _ultimo_evento_tipo(chassi_norm)
    if ultimo is None or ultimo not in EVENTOS_EM_ESTOQUE:
        raise ValueError(
            f"chassi {chassi_norm} nao esta em estoque (ultimo evento: {ultimo})"
        )

    avaria = HoraAvaria(
        numero_chassi=chassi_norm,
        loja_id=loja_id,
        descricao=desc_limpa,
        status='ABERTA',
        criado_por=usuario,
    )
    db.session.add(avaria)
    db.session.flush()  # obtem avaria.id

    for foto_s3_key, legenda in fotos_list:
        foto = HoraAvariaFoto(
            avaria_id=avaria.id,
            foto_s3_key=foto_s3_key,
            legenda=legenda,
            criado_por=usuario,
        )
        db.session.add(foto)

    # Evento append-only
    registrar_evento(
        numero_chassi=chassi_norm,
        tipo='AVARIADA',
        origem_tabela='hora_avaria',
        origem_id=avaria.id,
        loja_id=loja_id,
        operador=usuario,
        detalhe=f"Avaria #{avaria.id}: {desc_limpa[:180]}",
    )
    db.session.flush()
    return avaria


def adicionar_foto(
    avaria_id: int,
    foto_s3_key: str,
    legenda: Optional[str],
    usuario: str,
) -> HoraAvariaFoto:
    avaria = HoraAvaria.query.get(avaria_id)
    if not avaria:
        raise ValueError(f"avaria inexistente: {avaria_id}")
    foto = HoraAvariaFoto(
        avaria_id=avaria.id,
        foto_s3_key=foto_s3_key,
        legenda=legenda,
        criado_por=usuario,
    )
    db.session.add(foto)
    db.session.flush()
    return foto


def resolver_avaria(avaria_id: int, observacao: str, usuario: str) -> HoraAvaria:
    return _finalizar_avaria(avaria_id, 'RESOLVIDA', observacao, usuario)


def ignorar_avaria(avaria_id: int, observacao: str, usuario: str) -> HoraAvaria:
    return _finalizar_avaria(avaria_id, 'IGNORADA', observacao, usuario)


def _finalizar_avaria(
    avaria_id: int, novo_status: str, observacao: str, usuario: str,
) -> HoraAvaria:
    from app.utils.timezone import agora_utc_naive

    avaria = HoraAvaria.query.get(avaria_id)
    if not avaria:
        raise ValueError(f"avaria inexistente: {avaria_id}")
    if avaria.status != 'ABERTA':
        raise ValueError(
            f"avaria {avaria_id} ja esta {avaria.status} — nao pode re-finalizar"
        )

    obs_limpa = (observacao or '').strip()
    if len(obs_limpa) < 3:
        raise ValueError("observacao de resolucao obrigatoria (min 3 chars)")

    avaria.status = novo_status
    avaria.resolvido_em = agora_utc_naive()
    avaria.resolvido_por = usuario
    avaria.resolucao_observacao = obs_limpa
    db.session.flush()
    return avaria


def avarias_abertas_por_chassi(chassis: list[str]) -> dict:
    """Para badge na listagem de estoque. Retorna {chassi: count}."""
    if not chassis:
        return {}
    chassis_norm = [c.strip().upper() for c in chassis]
    rows = (
        db.session.query(HoraAvaria.numero_chassi, db.func.count(HoraAvaria.id))
        .filter(
            HoraAvaria.numero_chassi.in_(chassis_norm),
            HoraAvaria.status == 'ABERTA',
        )
        .group_by(HoraAvaria.numero_chassi)
        .all()
    )
    return {chassi: count for chassi, count in rows}
```

- [ ] **Step 4: Rodar — deve passar**

Run: `pytest tests/hora/test_avaria_service.py -v`

Expected: 10 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/hora/services/avaria_service.py tests/hora/test_avaria_service.py
git commit -m "feat(hora/avaria_service): CRUD + emissao evento AVARIADA + regras"
```

---

## Task 9: transferencia_audit.py

**Files:**
- Create: `app/hora/services/transferencia_audit.py`

- [ ] **Step 1: Ler padrão do `recebimento_audit` para espelhar**

Run: `cat app/hora/services/recebimento_audit.py`

- [ ] **Step 2: Escrever `transferencia_audit.py` (sem testes separados; cobertura vem via transferencia_service)**

```python
# app/hora/services/transferencia_audit.py
"""Auditoria append-only de transferencias entre filiais HORA.

Padrao identico ao recebimento_audit: nunca UPDATE/DELETE, registra em
hora_transferencia_auditoria.
"""
from __future__ import annotations

from typing import Optional

from app import db
from app.hora.models import HoraTransferenciaAuditoria


ACOES_VALIDAS = {
    'EMITIU', 'CONFIRMOU_ITEM', 'FINALIZOU', 'CANCELOU',
    'ADICIONOU_FOTO', 'EDITOU_OBSERVACAO',
}


def registrar_auditoria(
    transferencia_id: int,
    usuario: str,
    acao: str,
    *,
    item_id: Optional[int] = None,
    campo_alterado: Optional[str] = None,
    valor_antes: Optional[str] = None,
    valor_depois: Optional[str] = None,
    detalhe: Optional[str] = None,
) -> HoraTransferenciaAuditoria:
    if acao not in ACOES_VALIDAS:
        raise ValueError(f"acao invalida: {acao}. Aceitos: {ACOES_VALIDAS}")
    audit = HoraTransferenciaAuditoria(
        transferencia_id=transferencia_id,
        item_id=item_id,
        usuario=usuario,
        acao=acao,
        campo_alterado=campo_alterado,
        valor_antes=valor_antes,
        valor_depois=valor_depois,
        detalhe=detalhe,
    )
    db.session.add(audit)
    db.session.flush()
    return audit
```

- [ ] **Step 3: Smoke test inline**

Run:
```bash
python -c "from app import create_app; app=create_app(); \
  from app.hora.services.transferencia_audit import registrar_auditoria, ACOES_VALIDAS; \
  print('OK', sorted(ACOES_VALIDAS))"
```

Expected: `OK ['ADICIONOU_FOTO', 'CANCELOU', 'CONFIRMOU_ITEM', 'EDITOU_OBSERVACAO', 'EMITIU', 'FINALIZOU']`

- [ ] **Step 4: Commit**

```bash
git add app/hora/services/transferencia_audit.py
git commit -m "feat(hora/transferencia_audit): registrar_auditoria append-only"
```

---

## Task 10: transferencia_service — criar_transferencia

**Files:**
- Create: `app/hora/services/transferencia_service.py`
- Create: `tests/hora/test_transferencia_service.py`

- [ ] **Step 1: Escrever testes do `criar_transferencia`**

```python
# tests/hora/test_transferencia_service.py
"""Tests do transferencia_service."""
import pytest

from app import db as _db
from app.hora.models import (
    HoraTransferencia, HoraTransferenciaItem, HoraMotoEvento,
)
from app.hora.services import transferencia_service
from app.hora.services.moto_service import registrar_evento


# ---------- criar_transferencia ----------

def test_criar_transferencia_sucesso(db, chassi_em_estoque, loja_origem, loja_destino):
    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id,
        loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque],
        usuario='joao',
    )
    assert t.status == 'EM_TRANSITO'
    assert t.emitida_por == 'joao'
    assert len(t.itens) == 1
    # Evento EM_TRANSITO emitido com loja_id=destino
    ev = (HoraMotoEvento.query
          .filter_by(numero_chassi=chassi_em_estoque, tipo='EM_TRANSITO')
          .order_by(HoraMotoEvento.id.desc()).first())
    assert ev is not None
    assert ev.loja_id == loja_destino.id
    assert ev.origem_tabela == 'hora_transferencia_item'


def test_criar_lista_vazia_falha(db, loja_origem, loja_destino):
    with pytest.raises(ValueError, match=r"pelo menos 1 chassi"):
        transferencia_service.criar_transferencia(
            loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
            chassis=[], usuario='x',
        )


def test_criar_mesma_loja_falha(db, chassi_em_estoque, loja_origem):
    with pytest.raises(ValueError, match=r"origem.*destino"):
        transferencia_service.criar_transferencia(
            loja_origem_id=loja_origem.id, loja_destino_id=loja_origem.id,
            chassis=[chassi_em_estoque], usuario='x',
        )


def test_criar_chassi_fora_de_estoque_falha(db, chassi_em_estoque, loja_origem, loja_destino):
    registrar_evento(
        numero_chassi=chassi_em_estoque, tipo='VENDIDA',
        loja_id=loja_origem.id, operador='pre',
    )
    _db.session.flush()
    with pytest.raises(ValueError, match=r"estoque"):
        transferencia_service.criar_transferencia(
            loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
            chassis=[chassi_em_estoque], usuario='x',
        )


def test_criar_chassi_em_outra_loja_falha(db, chassi_em_estoque, loja_origem, loja_destino, modelo_moto):
    """Chassi esta na loja_origem; tentar transferir como origem=loja_destino falha."""
    with pytest.raises(ValueError, match=r"nao esta na loja origem"):
        transferencia_service.criar_transferencia(
            loja_origem_id=loja_destino.id,
            loja_destino_id=loja_origem.id,
            chassis=[chassi_em_estoque], usuario='x',
        )


def test_criar_chassi_em_transito_duplicado_falha(db, chassi_em_estoque, loja_origem, loja_destino):
    transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque], usuario='x',
    )
    _db.session.flush()
    with pytest.raises(ValueError, match=r"ja esta em transito"):
        transferencia_service.criar_transferencia(
            loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
            chassis=[chassi_em_estoque], usuario='x',
        )


def test_criar_registra_auditoria_EMITIU(db, chassi_em_estoque, loja_origem, loja_destino):
    from app.hora.models import HoraTransferenciaAuditoria
    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque], usuario='joao',
    )
    aud = HoraTransferenciaAuditoria.query.filter_by(
        transferencia_id=t.id, acao='EMITIU'
    ).first()
    assert aud is not None
    assert aud.usuario == 'joao'
```

- [ ] **Step 2: Rodar — deve falhar**

Run: `pytest tests/hora/test_transferencia_service.py -v -k criar`

Expected: todos FAIL (service não existe).

- [ ] **Step 3: Implementar `criar_transferencia` no service**

```python
# app/hora/services/transferencia_service.py
"""Service de transferencia de motos entre filiais HORA.

Fluxo (2 eventos):
  1. Loja origem emite → evento EM_TRANSITO (loja_id=destino)
  2. Loja destino confirma → evento TRANSFERIDA (loja_id=destino)
Cancelamento (origem enquanto EM_TRANSITO):
  → evento CANCELADA (loja_id=origem)
"""
from __future__ import annotations

from typing import Iterable, Optional

from app import db
from app.hora.models import (
    HoraMoto, HoraMotoEvento,
    HoraTransferencia, HoraTransferenciaItem,
)
from app.hora.services.moto_service import registrar_evento
from app.hora.services.estoque_service import EVENTOS_EM_ESTOQUE
from app.hora.services.transferencia_audit import registrar_auditoria
from app.utils.timezone import agora_utc_naive


def _ultimo_evento(chassi: str) -> Optional[HoraMotoEvento]:
    return (HoraMotoEvento.query
            .filter_by(numero_chassi=chassi)
            .order_by(HoraMotoEvento.timestamp.desc())
            .first())


def _chassi_esta_em_transferencia_ativa(chassi: str) -> bool:
    q = (
        db.session.query(HoraTransferenciaItem.id)
        .join(HoraTransferencia,
              HoraTransferencia.id == HoraTransferenciaItem.transferencia_id)
        .filter(
            HoraTransferenciaItem.numero_chassi == chassi,
            HoraTransferencia.status == 'EM_TRANSITO',
        )
    )
    return db.session.query(q.exists()).scalar()


def criar_transferencia(
    loja_origem_id: int,
    loja_destino_id: int,
    chassis: Iterable[str],
    usuario: str,
    observacoes: Optional[str] = None,
) -> HoraTransferencia:
    """Emite transferencia (status=EM_TRANSITO) com N chassis."""
    chassis_list = [c.strip().upper() for c in chassis]
    if not chassis_list:
        raise ValueError("Transferencia requer pelo menos 1 chassi")
    if loja_origem_id == loja_destino_id:
        raise ValueError("loja origem e destino devem ser diferentes")

    # Validar cada chassi
    for chassi in chassis_list:
        moto = HoraMoto.query.get(chassi)
        if not moto:
            raise ValueError(f"chassi inexistente: {chassi}")
        ev = _ultimo_evento(chassi)
        if ev is None or ev.tipo not in EVENTOS_EM_ESTOQUE:
            tipo = ev.tipo if ev else None
            raise ValueError(
                f"chassi {chassi} nao esta em estoque (ultimo evento: {tipo})"
            )
        if ev.loja_id != loja_origem_id:
            raise ValueError(
                f"chassi {chassi} nao esta na loja origem "
                f"(esta em loja_id={ev.loja_id})"
            )
        if _chassi_esta_em_transferencia_ativa(chassi):
            raise ValueError(f"chassi {chassi} ja esta em transito")

    transferencia = HoraTransferencia(
        loja_origem_id=loja_origem_id,
        loja_destino_id=loja_destino_id,
        status='EM_TRANSITO',
        emitida_em=agora_utc_naive(),
        emitida_por=usuario,
        observacoes=observacoes,
    )
    db.session.add(transferencia)
    db.session.flush()  # transferencia.id

    # Criar itens + eventos
    from app.hora.models import HoraLoja
    origem = HoraLoja.query.get(loja_origem_id)
    destino = HoraLoja.query.get(loja_destino_id)
    origem_lbl = getattr(origem, 'rotulo_display', f'id={loja_origem_id}')
    destino_lbl = getattr(destino, 'rotulo_display', f'id={loja_destino_id}')

    for chassi in chassis_list:
        item = HoraTransferenciaItem(
            transferencia_id=transferencia.id,
            numero_chassi=chassi,
        )
        db.session.add(item)
        db.session.flush()  # item.id

        registrar_evento(
            numero_chassi=chassi,
            tipo='EM_TRANSITO',
            origem_tabela='hora_transferencia_item',
            origem_id=item.id,
            loja_id=loja_destino_id,
            operador=usuario,
            detalhe=f"Transf #{transferencia.id}: de {origem_lbl} para {destino_lbl}",
        )

    registrar_auditoria(
        transferencia_id=transferencia.id,
        usuario=usuario,
        acao='EMITIU',
        detalhe=(
            f"emitiu transferencia de {origem_lbl} para {destino_lbl} "
            f"com {len(chassis_list)} chassi(s)"
        ),
    )

    db.session.flush()
    return transferencia
```

- [ ] **Step 4: Rodar testes — criar_transferencia deve passar**

Run: `pytest tests/hora/test_transferencia_service.py -v -k criar`

Expected: 7 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/hora/services/transferencia_service.py tests/hora/test_transferencia_service.py
git commit -m "feat(hora/transferencia): criar_transferencia + emissao EM_TRANSITO"
```

---

## Task 11: transferencia_service — confirmar_item_destino + finalizar_se_tudo_confirmado

**Files:**
- Modify: `app/hora/services/transferencia_service.py`
- Modify: `tests/hora/test_transferencia_service.py`

- [ ] **Step 1: Adicionar testes**

Append em `tests/hora/test_transferencia_service.py`:

```python
# ---------- confirmar_item_destino + finalizar ----------

def test_confirmar_item_emite_TRANSFERIDA(db, chassi_em_estoque, loja_origem, loja_destino):
    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque], usuario='emissor',
    )
    item = t.itens[0]
    transferencia_service.confirmar_item_destino(
        transferencia_id=t.id,
        numero_chassi=chassi_em_estoque,
        usuario='recebedor',
        qr_code_lido=True,
    )
    _db.session.refresh(item)
    assert item.conferido_destino_em is not None
    assert item.qr_code_lido is True
    # Evento TRANSFERIDA existe
    ev = (HoraMotoEvento.query
          .filter_by(numero_chassi=chassi_em_estoque, tipo='TRANSFERIDA')
          .order_by(HoraMotoEvento.id.desc()).first())
    assert ev is not None
    assert ev.loja_id == loja_destino.id


def test_confirmar_idempotente(db, chassi_em_estoque, loja_origem, loja_destino):
    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque], usuario='emissor',
    )
    transferencia_service.confirmar_item_destino(
        transferencia_id=t.id, numero_chassi=chassi_em_estoque,
        usuario='r1', qr_code_lido=False,
    )
    # Segunda chamada: no-op (nao emite novo evento, nao altera campo conferido_destino_por)
    transferencia_service.confirmar_item_destino(
        transferencia_id=t.id, numero_chassi=chassi_em_estoque,
        usuario='r2', qr_code_lido=True,
    )
    _db.session.flush()
    item = t.itens[0]
    _db.session.refresh(item)
    assert item.conferido_destino_por == 'r1'
    evs = HoraMotoEvento.query.filter_by(
        numero_chassi=chassi_em_estoque, tipo='TRANSFERIDA'
    ).count()
    assert evs == 1


def test_finalizar_muda_status_para_CONFIRMADA(db, chassi_em_estoque, loja_origem, loja_destino):
    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque], usuario='emissor',
    )
    transferencia_service.confirmar_item_destino(
        transferencia_id=t.id, numero_chassi=chassi_em_estoque,
        usuario='recebedor', qr_code_lido=True,
    )
    ok = transferencia_service.finalizar_se_tudo_confirmado(t.id)
    assert ok is True
    _db.session.refresh(t)
    assert t.status == 'CONFIRMADA'
    assert t.confirmada_em is not None
    assert t.confirmada_por == 'recebedor'


def test_finalizar_nao_altera_se_falta_item(db, chassi_em_estoque, loja_origem, loja_destino, modelo_moto):
    """Com 2 chassis, confirma so 1 — nao finaliza."""
    from app.hora.services.moto_service import get_or_create_moto
    chassi2 = '9OUTROCHASSI' + '2' * 14
    get_or_create_moto(
        numero_chassi=chassi2, modelo_nome=modelo_moto.nome_modelo,
        cor='BRANCA', criado_por='fix',
    )
    registrar_evento(chassi2, 'RECEBIDA', loja_id=loja_origem.id, operador='fix')
    registrar_evento(chassi2, 'CONFERIDA', loja_id=loja_origem.id, operador='fix')
    _db.session.flush()

    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque, chassi2], usuario='emissor',
    )
    transferencia_service.confirmar_item_destino(
        transferencia_id=t.id, numero_chassi=chassi_em_estoque,
        usuario='r1', qr_code_lido=True,
    )
    ok = transferencia_service.finalizar_se_tudo_confirmado(t.id)
    assert ok is False
    _db.session.refresh(t)
    assert t.status == 'EM_TRANSITO'
```

- [ ] **Step 2: Rodar — FAIL esperado**

Run: `pytest tests/hora/test_transferencia_service.py -v -k "confirmar or finalizar"`

Expected: 4 FAIL com `AttributeError`.

- [ ] **Step 3: Implementar funções no `transferencia_service.py`**

Adicionar ao mesmo arquivo:

```python
def confirmar_item_destino(
    transferencia_id: int,
    numero_chassi: str,
    usuario: str,
    qr_code_lido: bool = False,
    foto_s3_key: Optional[str] = None,
    observacao: Optional[str] = None,
) -> HoraTransferenciaItem:
    """Confirma chegada de 1 chassi no destino. Idempotente."""
    chassi = numero_chassi.strip().upper()
    transferencia = HoraTransferencia.query.get(transferencia_id)
    if not transferencia:
        raise ValueError(f"transferencia {transferencia_id} inexistente")
    if transferencia.status != 'EM_TRANSITO':
        raise ValueError(
            f"transferencia {transferencia_id} nao esta em transito "
            f"(status={transferencia.status})"
        )
    item = (
        HoraTransferenciaItem.query
        .filter_by(transferencia_id=transferencia_id, numero_chassi=chassi)
        .first()
    )
    if not item:
        raise ValueError(
            f"chassi {chassi} nao pertence a transferencia {transferencia_id}"
        )
    if item.conferido_destino_em is not None:
        # Idempotente — no-op
        return item

    item.conferido_destino_em = agora_utc_naive()
    item.conferido_destino_por = usuario
    item.qr_code_lido = bool(qr_code_lido)
    if foto_s3_key:
        item.foto_s3_key = foto_s3_key
    if observacao:
        item.observacao_item = observacao

    registrar_evento(
        numero_chassi=chassi,
        tipo='TRANSFERIDA',
        origem_tabela='hora_transferencia_item',
        origem_id=item.id,
        loja_id=transferencia.loja_destino_id,
        operador=usuario,
        detalhe=f"Chegou via Transf #{transferencia.id}",
    )

    registrar_auditoria(
        transferencia_id=transferencia_id,
        usuario=usuario,
        acao='CONFIRMOU_ITEM',
        item_id=item.id,
        detalhe=(
            f"confirmou chassi {chassi} (qr_code_lido={qr_code_lido}, "
            f"foto={'sim' if foto_s3_key else 'nao'})"
        ),
    )
    db.session.flush()
    return item


def finalizar_se_tudo_confirmado(transferencia_id: int) -> bool:
    """Muda status → CONFIRMADA se todos itens confirmados. Retorna True se finalizou."""
    transferencia = HoraTransferencia.query.get(transferencia_id)
    if not transferencia or transferencia.status != 'EM_TRANSITO':
        return False
    pendentes = [i for i in transferencia.itens if i.conferido_destino_em is None]
    if pendentes:
        return False

    # Ultimo usuario a confirmar = o que "finalizou"
    ultimo_confirmador = (
        max(transferencia.itens, key=lambda i: i.conferido_destino_em)
        .conferido_destino_por
    )

    transferencia.status = 'CONFIRMADA'
    transferencia.confirmada_em = agora_utc_naive()
    transferencia.confirmada_por = ultimo_confirmador

    registrar_auditoria(
        transferencia_id=transferencia_id,
        usuario=ultimo_confirmador,
        acao='FINALIZOU',
        detalhe=f"todos os {len(transferencia.itens)} chassi(s) confirmados",
    )
    db.session.flush()
    return True
```

- [ ] **Step 4: Rodar — deve passar**

Run: `pytest tests/hora/test_transferencia_service.py -v -k "confirmar or finalizar"`

Expected: 4 PASS.

- [ ] **Step 5: Commit**

```bash
git add app/hora/services/transferencia_service.py tests/hora/test_transferencia_service.py
git commit -m "feat(hora/transferencia): confirmar_item_destino + finalizar_se_tudo_confirmado"
```

---

## Task 12: transferencia_service — cancelar_transferencia

**Files:**
- Modify: `app/hora/services/transferencia_service.py`
- Modify: `tests/hora/test_transferencia_service.py`

- [ ] **Step 1: Adicionar testes**

Append em `tests/hora/test_transferencia_service.py`:

```python
# ---------- cancelar_transferencia ----------

def test_cancelar_em_transito_volta_moto_para_origem(db, chassi_em_estoque, loja_origem, loja_destino):
    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque], usuario='emissor',
    )
    transferencia_service.cancelar_transferencia(
        transferencia_id=t.id, motivo='enviado por engano', usuario='chefe',
    )
    _db.session.refresh(t)
    assert t.status == 'CANCELADA'
    assert t.cancelada_em is not None
    assert t.cancelada_por == 'chefe'
    assert t.motivo_cancelamento == 'enviado por engano'
    # Evento CANCELADA na loja_origem
    ev = (HoraMotoEvento.query
          .filter_by(numero_chassi=chassi_em_estoque, tipo='CANCELADA')
          .order_by(HoraMotoEvento.id.desc()).first())
    assert ev is not None
    assert ev.loja_id == loja_origem.id


def test_cancelar_exige_motivo_com_3_chars(db, chassi_em_estoque, loja_origem, loja_destino):
    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque], usuario='x',
    )
    with pytest.raises(ValueError, match=r"motivo"):
        transferencia_service.cancelar_transferencia(t.id, motivo='ok', usuario='y')


def test_cancelar_so_em_transito(db, chassi_em_estoque, loja_origem, loja_destino):
    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque], usuario='x',
    )
    transferencia_service.confirmar_item_destino(
        t.id, chassi_em_estoque, usuario='r1', qr_code_lido=True,
    )
    transferencia_service.finalizar_se_tudo_confirmado(t.id)
    with pytest.raises(ValueError, match=r"nao pode cancelar"):
        transferencia_service.cancelar_transferencia(
            t.id, motivo='muito tarde', usuario='y',
        )


def test_cancelar_nao_emite_CANCELADA_para_item_ja_confirmado(
    db, chassi_em_estoque, loja_origem, loja_destino, modelo_moto,
):
    """Edge case: 2 chassis, 1 ja confirmado; cancela → so o NAO-confirmado vira CANCELADA."""
    from app.hora.services.moto_service import get_or_create_moto
    chassi2 = '9OUTROCHASSI' + '3' * 14
    get_or_create_moto(
        numero_chassi=chassi2, modelo_nome=modelo_moto.nome_modelo,
        cor='BRANCA', criado_por='fix',
    )
    registrar_evento(chassi2, 'RECEBIDA', loja_id=loja_origem.id, operador='fix')
    registrar_evento(chassi2, 'CONFERIDA', loja_id=loja_origem.id, operador='fix')
    _db.session.flush()

    t = transferencia_service.criar_transferencia(
        loja_origem_id=loja_origem.id, loja_destino_id=loja_destino.id,
        chassis=[chassi_em_estoque, chassi2], usuario='x',
    )
    # Confirma apenas chassi2
    transferencia_service.confirmar_item_destino(
        t.id, chassi2, usuario='r1', qr_code_lido=True,
    )
    # Cancela — chassi_em_estoque deve emitir CANCELADA; chassi2 NAO
    transferencia_service.cancelar_transferencia(
        t.id, motivo='parcialmente errado', usuario='y',
    )
    evs_chassi1 = HoraMotoEvento.query.filter_by(
        numero_chassi=chassi_em_estoque, tipo='CANCELADA'
    ).count()
    evs_chassi2 = HoraMotoEvento.query.filter_by(
        numero_chassi=chassi2, tipo='CANCELADA'
    ).count()
    assert evs_chassi1 == 1
    assert evs_chassi2 == 0
```

- [ ] **Step 2: Rodar — FAIL**

Run: `pytest tests/hora/test_transferencia_service.py -v -k cancelar`

Expected: 4 FAIL.

- [ ] **Step 3: Implementar `cancelar_transferencia`**

Adicionar ao `transferencia_service.py`:

```python
def cancelar_transferencia(
    transferencia_id: int,
    motivo: str,
    usuario: str,
) -> HoraTransferencia:
    """Cancela transferencia em transito. Emite CANCELADA para itens nao confirmados."""
    motivo_limpo = (motivo or '').strip()
    if len(motivo_limpo) < 3:
        raise ValueError("motivo de cancelamento obrigatorio (min 3 chars)")

    transferencia = HoraTransferencia.query.get(transferencia_id)
    if not transferencia:
        raise ValueError(f"transferencia {transferencia_id} inexistente")
    if transferencia.status != 'EM_TRANSITO':
        raise ValueError(
            f"nao pode cancelar transferencia com status={transferencia.status}"
        )

    transferencia.status = 'CANCELADA'
    transferencia.cancelada_em = agora_utc_naive()
    transferencia.cancelada_por = usuario
    transferencia.motivo_cancelamento = motivo_limpo[:255]

    # Para cada item ainda NAO confirmado no destino: emite CANCELADA (moto volta a origem)
    for item in transferencia.itens:
        if item.conferido_destino_em is not None:
            continue  # ja confirmado — nao reverte
        registrar_evento(
            numero_chassi=item.numero_chassi,
            tipo='CANCELADA',
            origem_tabela='hora_transferencia',
            origem_id=transferencia.id,
            loja_id=transferencia.loja_origem_id,
            operador=usuario,
            detalhe=f"Transf #{transferencia.id} cancelada: {motivo_limpo[:180]}",
        )

    registrar_auditoria(
        transferencia_id=transferencia.id,
        usuario=usuario,
        acao='CANCELOU',
        detalhe=f"motivo: {motivo_limpo}",
    )
    db.session.flush()
    return transferencia
```

- [ ] **Step 4: Rodar — deve passar**

Run: `pytest tests/hora/test_transferencia_service.py -v`

Expected: todos PASS (15+ testes).

- [ ] **Step 5: Commit**

```bash
git add app/hora/services/transferencia_service.py tests/hora/test_transferencia_service.py
git commit -m "feat(hora/transferencia): cancelar_transferencia + emissao CANCELADA"
```

---

## Task 13: Routes avarias.py

**Files:**
- Create: `app/hora/routes/avarias.py`
- Modify: `app/hora/routes/__init__.py`

- [ ] **Step 1: Inspecionar route existente para copiar padrão**

Run: `head -80 app/hora/routes/pecas.py`

- [ ] **Step 2: Criar `app/hora/routes/avarias.py`**

```python
"""Rotas de avaria em moto do estoque HORA."""
from __future__ import annotations

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort,
)
from flask_login import current_user
from werkzeug.exceptions import NotFound

from app.hora.decorators import require_lojas
from app.hora.models import HoraAvaria, HoraLoja, HoraMoto
from app.hora.services import avaria_service
from app.hora.services.auth_helper import (
    lojas_permitidas_ids, usuario_tem_acesso_a_loja,
)

bp = Blueprint('hora_avarias', __name__, url_prefix='/hora/avarias')


@bp.route('/', methods=['GET'])
@require_lojas
def lista():
    permitidas = lojas_permitidas_ids()
    q = HoraAvaria.query.join(HoraLoja, HoraLoja.id == HoraAvaria.loja_id)

    status = request.args.get('status')
    if status:
        q = q.filter(HoraAvaria.status == status)
    loja_id = request.args.get('loja_id', type=int)
    if loja_id:
        if not usuario_tem_acesso_a_loja(loja_id):
            flash('Acesso negado a essa loja', 'danger')
            return redirect(url_for('hora_avarias.lista'))
        q = q.filter(HoraAvaria.loja_id == loja_id)
    if permitidas is not None:
        q = q.filter(HoraAvaria.loja_id.in_(permitidas))

    chassi_query = request.args.get('chassi')
    if chassi_query:
        q = q.filter(HoraAvaria.numero_chassi.ilike(f"%{chassi_query.strip().upper()}%"))

    avarias = q.order_by(HoraAvaria.criado_em.desc()).limit(500).all()
    lojas = HoraLoja.query.filter_by(ativa=True).order_by(HoraLoja.apelido).all()
    return render_template(
        'hora/avarias_lista.html',
        avarias=avarias, lojas=lojas,
        filtros={'status': status, 'loja_id': loja_id, 'chassi': chassi_query},
    )


@bp.route('/<int:avaria_id>', methods=['GET'])
@require_lojas
def detalhe(avaria_id):
    avaria = HoraAvaria.query.get_or_404(avaria_id)
    if not usuario_tem_acesso_a_loja(avaria.loja_id):
        abort(403)
    return render_template('hora/avaria_detalhe.html', avaria=avaria)


@bp.route('/nova', methods=['GET', 'POST'])
@require_lojas
def nova():
    permitidas = lojas_permitidas_ids()

    if request.method == 'POST':
        numero_chassi = (request.form.get('numero_chassi') or '').strip().upper()
        descricao = (request.form.get('descricao') or '').strip()
        loja_id = request.form.get('loja_id', type=int)
        if permitidas is not None and loja_id not in permitidas:
            flash('Loja fora do escopo', 'danger')
            return redirect(url_for('hora_avarias.nova'))

        fotos_raw = request.form.getlist('foto_s3_key')
        legendas_raw = request.form.getlist('foto_legenda')
        fotos = [
            (fk, leg if leg else None)
            for fk, leg in zip(fotos_raw, legendas_raw) if fk
        ]

        try:
            avaria = avaria_service.registrar_avaria(
                numero_chassi=numero_chassi,
                descricao=descricao,
                fotos=fotos,
                usuario=current_user.nome if current_user.is_authenticated else 'anonimo',
                loja_id=loja_id,
            )
            from app import db
            db.session.commit()
            flash(f'Avaria #{avaria.id} registrada.', 'success')
            return redirect(url_for('hora_avarias.detalhe', avaria_id=avaria.id))
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(url_for('hora_avarias.nova'))

    lojas_filtradas = (
        HoraLoja.query.filter_by(ativa=True).order_by(HoraLoja.apelido).all()
        if permitidas is None
        else HoraLoja.query.filter(HoraLoja.id.in_(permitidas)).all()
    )
    return render_template('hora/avaria_nova.html', lojas=lojas_filtradas)


@bp.route('/<int:avaria_id>/foto', methods=['POST'])
@require_lojas
def adicionar_foto(avaria_id):
    avaria = HoraAvaria.query.get_or_404(avaria_id)
    if not usuario_tem_acesso_a_loja(avaria.loja_id):
        abort(403)
    foto_s3_key = (request.form.get('foto_s3_key') or '').strip()
    legenda = (request.form.get('legenda') or '').strip() or None
    if not foto_s3_key:
        flash('foto_s3_key obrigatorio', 'danger')
        return redirect(url_for('hora_avarias.detalhe', avaria_id=avaria_id))
    avaria_service.adicionar_foto(
        avaria_id, foto_s3_key, legenda,
        usuario=current_user.nome,
    )
    from app import db
    db.session.commit()
    flash('Foto adicionada.', 'success')
    return redirect(url_for('hora_avarias.detalhe', avaria_id=avaria_id))


@bp.route('/<int:avaria_id>/resolver', methods=['POST'])
@require_lojas
def resolver(avaria_id):
    avaria = HoraAvaria.query.get_or_404(avaria_id)
    if not usuario_tem_acesso_a_loja(avaria.loja_id):
        abort(403)
    obs = (request.form.get('observacao') or '').strip()
    try:
        avaria_service.resolver_avaria(avaria_id, obs, current_user.nome)
        from app import db
        db.session.commit()
        flash('Avaria resolvida.', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    return redirect(url_for('hora_avarias.detalhe', avaria_id=avaria_id))


@bp.route('/<int:avaria_id>/ignorar', methods=['POST'])
@require_lojas
def ignorar(avaria_id):
    avaria = HoraAvaria.query.get_or_404(avaria_id)
    if not usuario_tem_acesso_a_loja(avaria.loja_id):
        abort(403)
    obs = (request.form.get('observacao') or '').strip()
    try:
        avaria_service.ignorar_avaria(avaria_id, obs, current_user.nome)
        from app import db
        db.session.commit()
        flash('Avaria ignorada.', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    return redirect(url_for('hora_avarias.detalhe', avaria_id=avaria_id))
```

- [ ] **Step 3: Registrar no `__init__.py` do blueprint**

Editar `app/hora/routes/__init__.py`. Localizar onde outros blueprints são importados e adicionar:

```python
from app.hora.routes.avarias import bp as _avarias_bp  # noqa: E402
hora_bp.register_blueprint(_avarias_bp)
```

Se o padrão for importar rotas diretamente em vez de sub-blueprints (como `pecas.py`), seguir o padrão existente. Revisar `app/hora/routes/__init__.py` e replicar.

- [ ] **Step 4: Smoke test**

Run:
```bash
python -c "
from app import create_app
app = create_app()
with app.test_request_context():
    from flask import url_for
    print(url_for('hora_avarias.lista'))
    print(url_for('hora_avarias.nova'))
    print(url_for('hora_avarias.detalhe', avaria_id=1))
"
```

Expected: 3 URLs sob `/hora/avarias/...`.

- [ ] **Step 5: Commit**

```bash
git add app/hora/routes/avarias.py app/hora/routes/__init__.py
git commit -m "feat(hora/routes): avarias — 6 endpoints (lista/detalhe/nova/foto/resolver/ignorar)"
```

---

## Task 14: Routes transferencias.py

**Files:**
- Create: `app/hora/routes/transferencias.py`
- Modify: `app/hora/routes/__init__.py`

- [ ] **Step 1: Criar `app/hora/routes/transferencias.py`**

```python
"""Rotas de transferencia entre filiais HORA."""
from __future__ import annotations

from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, jsonify, abort,
)
from flask_login import current_user

from app.hora.decorators import require_lojas
from app.hora.models import (
    HoraTransferencia, HoraTransferenciaAuditoria, HoraLoja,
)
from app.hora.services import transferencia_service
from app.hora.services.auth_helper import (
    lojas_permitidas_ids, usuario_tem_acesso_a_loja,
    loja_origem_permitida_para_transferencia,
)

bp = Blueprint('hora_transferencias', __name__, url_prefix='/hora/transferencias')


@bp.route('/', methods=['GET'])
@require_lojas
def lista():
    permitidas = lojas_permitidas_ids()
    q = HoraTransferencia.query

    status = request.args.get('status')
    if status:
        q = q.filter(HoraTransferencia.status == status)
    loja_id = request.args.get('loja_id', type=int)
    if loja_id:
        q = q.filter(
            (HoraTransferencia.loja_origem_id == loja_id)
            | (HoraTransferencia.loja_destino_id == loja_id)
        )
    if permitidas is not None:
        from sqlalchemy import or_
        q = q.filter(or_(
            HoraTransferencia.loja_origem_id.in_(permitidas),
            HoraTransferencia.loja_destino_id.in_(permitidas),
        ))

    transferencias = q.order_by(HoraTransferencia.emitida_em.desc()).limit(500).all()
    lojas = HoraLoja.query.filter_by(ativa=True).order_by(HoraLoja.apelido).all()
    return render_template(
        'hora/transferencias_lista.html',
        transferencias=transferencias, lojas=lojas,
        filtros={'status': status, 'loja_id': loja_id},
    )


@bp.route('/<int:transferencia_id>', methods=['GET'])
@require_lojas
def detalhe(transferencia_id):
    t = HoraTransferencia.query.get_or_404(transferencia_id)
    # usuario com acesso a origem OU destino ve
    if not (usuario_tem_acesso_a_loja(t.loja_origem_id)
            or usuario_tem_acesso_a_loja(t.loja_destino_id)):
        abort(403)
    return render_template('hora/transferencia_detalhe.html', t=t)


@bp.route('/nova', methods=['GET', 'POST'])
@require_lojas
def nova():
    permitidas = lojas_permitidas_ids()
    origem_fixa = loja_origem_permitida_para_transferencia()

    if request.method == 'POST':
        loja_origem_id = request.form.get('loja_origem_id', type=int)
        loja_destino_id = request.form.get('loja_destino_id', type=int)
        chassis_raw = request.form.get('chassis') or ''
        observacoes = (request.form.get('observacoes') or '').strip() or None

        chassis = [c.strip().upper() for c in chassis_raw.splitlines() if c.strip()]

        # Valida escopo
        if origem_fixa is not None and loja_origem_id != origem_fixa:
            flash('Voce so pode emitir transferencias da sua loja', 'danger')
            return redirect(url_for('hora_transferencias.nova'))
        if permitidas is not None and loja_origem_id not in permitidas:
            flash('Loja origem fora do escopo', 'danger')
            return redirect(url_for('hora_transferencias.nova'))

        try:
            t = transferencia_service.criar_transferencia(
                loja_origem_id=loja_origem_id,
                loja_destino_id=loja_destino_id,
                chassis=chassis,
                usuario=current_user.nome,
                observacoes=observacoes,
            )
            from app import db
            db.session.commit()
            flash(f'Transferencia #{t.id} emitida.', 'success')
            return redirect(url_for('hora_transferencias.detalhe', transferencia_id=t.id))
        except ValueError as e:
            flash(str(e), 'danger')
            return redirect(url_for('hora_transferencias.nova'))

    lojas_todas = HoraLoja.query.filter_by(ativa=True).order_by(HoraLoja.apelido).all()
    return render_template(
        'hora/transferencia_nova.html',
        lojas=lojas_todas, origem_fixa=origem_fixa,
    )


@bp.route('/<int:transferencia_id>/confirmar', methods=['GET'])
@require_lojas
def confirmar_wizard(transferencia_id):
    t = HoraTransferencia.query.get_or_404(transferencia_id)
    if not usuario_tem_acesso_a_loja(t.loja_destino_id):
        abort(403)
    return render_template('hora/transferencia_confirmar_wizard.html', t=t)


@bp.route('/<int:transferencia_id>/confirmar-item', methods=['POST'])
@require_lojas
def confirmar_item(transferencia_id):
    t = HoraTransferencia.query.get_or_404(transferencia_id)
    if not usuario_tem_acesso_a_loja(t.loja_destino_id):
        return jsonify(error='forbidden'), 403

    numero_chassi = (request.form.get('numero_chassi') or '').strip().upper()
    qr_code_lido = request.form.get('qr_code_lido') == 'true'
    foto_s3_key = (request.form.get('foto_s3_key') or '').strip() or None
    observacao = (request.form.get('observacao') or '').strip() or None

    try:
        item = transferencia_service.confirmar_item_destino(
            transferencia_id=transferencia_id,
            numero_chassi=numero_chassi,
            usuario=current_user.nome,
            qr_code_lido=qr_code_lido,
            foto_s3_key=foto_s3_key,
            observacao=observacao,
        )
        transferencia_service.finalizar_se_tudo_confirmado(transferencia_id)
        from app import db
        db.session.commit()
        return jsonify(
            ok=True,
            item_id=item.id,
            status=HoraTransferencia.query.get(transferencia_id).status,
        )
    except ValueError as e:
        return jsonify(error=str(e)), 400


@bp.route('/<int:transferencia_id>/cancelar', methods=['POST'])
@require_lojas
def cancelar(transferencia_id):
    t = HoraTransferencia.query.get_or_404(transferencia_id)
    if not usuario_tem_acesso_a_loja(t.loja_origem_id):
        abort(403)
    motivo = (request.form.get('motivo') or '').strip()
    try:
        transferencia_service.cancelar_transferencia(
            transferencia_id, motivo, current_user.nome,
        )
        from app import db
        db.session.commit()
        flash('Transferencia cancelada.', 'success')
    except ValueError as e:
        flash(str(e), 'danger')
    return redirect(url_for('hora_transferencias.detalhe', transferencia_id=transferencia_id))


@bp.route('/<int:transferencia_id>/auditoria', methods=['GET'])
@require_lojas
def auditoria_json(transferencia_id):
    t = HoraTransferencia.query.get_or_404(transferencia_id)
    if not (usuario_tem_acesso_a_loja(t.loja_origem_id)
            or usuario_tem_acesso_a_loja(t.loja_destino_id)):
        return jsonify(error='forbidden'), 403
    itens = (
        HoraTransferenciaAuditoria.query
        .filter_by(transferencia_id=transferencia_id)
        .order_by(HoraTransferenciaAuditoria.criado_em.desc())
        .all()
    )
    return jsonify(auditoria=[
        dict(
            id=a.id, usuario=a.usuario, acao=a.acao,
            campo_alterado=a.campo_alterado,
            valor_antes=a.valor_antes, valor_depois=a.valor_depois,
            detalhe=a.detalhe, criado_em=a.criado_em.isoformat(),
        )
        for a in itens
    ])
```

- [ ] **Step 2: Registrar no `app/hora/routes/__init__.py`** (mesmo padrão da Task 13)

- [ ] **Step 3: Smoke test**

Run:
```bash
python -c "
from app import create_app
app = create_app()
with app.test_request_context():
    from flask import url_for
    print(url_for('hora_transferencias.lista'))
    print(url_for('hora_transferencias.nova'))
    print(url_for('hora_transferencias.detalhe', transferencia_id=1))
    print(url_for('hora_transferencias.confirmar_wizard', transferencia_id=1))
    print(url_for('hora_transferencias.cancelar', transferencia_id=1))
"
```

Expected: 5 URLs sob `/hora/transferencias/...`.

- [ ] **Step 4: Commit**

```bash
git add app/hora/routes/transferencias.py app/hora/routes/__init__.py
git commit -m "feat(hora/routes): transferencias — 7 endpoints (lista/detalhe/nova/wizard/cancelar/auditoria)"
```

---

## Task 15: Templates — avarias_lista.html

**Files:**
- Create: `app/templates/hora/avarias_lista.html`

- [ ] **Step 1: Ler padrão visual de uma listagem existente**

Run: `head -60 app/templates/hora/pecas_faltando_lista.html`

- [ ] **Step 2: Criar template**

```jinja
{# app/templates/hora/avarias_lista.html #}
{% extends "hora/base.html" %}
{% block title %}Avarias — HORA{% endblock %}
{% block conteudo %}
<div class="container-fluid mt-3">
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h3><i class="fas fa-exclamation-triangle"></i> Avarias</h3>
    <a href="{{ url_for('hora_avarias.nova') }}" class="btn btn-primary">
      <i class="fas fa-plus"></i> Nova avaria
    </a>
  </div>

  <form method="GET" class="card card-body mb-3">
    <div class="row g-2">
      <div class="col-md-3">
        <label class="form-label small">Status</label>
        <select name="status" class="form-select form-select-sm">
          <option value="">Todas</option>
          <option value="ABERTA" {% if filtros.status=='ABERTA' %}selected{% endif %}>Abertas</option>
          <option value="RESOLVIDA" {% if filtros.status=='RESOLVIDA' %}selected{% endif %}>Resolvidas</option>
          <option value="IGNORADA" {% if filtros.status=='IGNORADA' %}selected{% endif %}>Ignoradas</option>
        </select>
      </div>
      <div class="col-md-3">
        <label class="form-label small">Loja</label>
        <select name="loja_id" class="form-select form-select-sm">
          <option value="">Todas</option>
          {% for l in lojas %}
            <option value="{{ l.id }}" {% if filtros.loja_id==l.id %}selected{% endif %}>
              {{ l.rotulo_display }}
            </option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-4">
        <label class="form-label small">Chassi (contém)</label>
        <input type="text" name="chassi" value="{{ filtros.chassi or '' }}" class="form-control form-control-sm">
      </div>
      <div class="col-md-2 d-flex align-items-end">
        <button class="btn btn-sm btn-outline-primary">Filtrar</button>
      </div>
    </div>
  </form>

  <div class="card">
    <table class="table table-hover table-sm mb-0">
      <thead>
        <tr>
          <th>#</th><th>Chassi</th><th>Loja</th><th>Status</th>
          <th>Descrição</th><th>Fotos</th><th>Registrada em</th><th>Por</th><th></th>
        </tr>
      </thead>
      <tbody>
        {% for a in avarias %}
        <tr>
          <td>{{ a.id }}</td>
          <td><code>{{ a.numero_chassi }}</code></td>
          <td>{{ a.loja.rotulo_display if a.loja else '—' }}</td>
          <td>
            {% if a.status=='ABERTA' %}<span class="badge bg-warning text-dark">Aberta</span>
            {% elif a.status=='RESOLVIDA' %}<span class="badge bg-success">Resolvida</span>
            {% else %}<span class="badge bg-secondary">Ignorada</span>{% endif %}
          </td>
          <td>{{ a.descricao[:80] }}{% if a.descricao|length>80 %}…{% endif %}</td>
          <td>{{ a.fotos|length }}</td>
          <td>{{ a.criado_em.strftime('%d/%m/%Y %H:%M') }}</td>
          <td>{{ a.criado_por }}</td>
          <td>
            <a href="{{ url_for('hora_avarias.detalhe', avaria_id=a.id) }}" class="btn btn-sm btn-outline-primary">Ver</a>
          </td>
        </tr>
        {% else %}
        <tr><td colspan="9" class="text-center text-muted py-3">Nenhuma avaria encontrada.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 3: Testar render manual**

Run: `python run.py` (em outro terminal) e acessar `/hora/avarias` no navegador. Expected: página carrega sem erro de template.

(Se não for possível rodar servidor, pular para Step 4.)

- [ ] **Step 4: Commit**

```bash
git add app/templates/hora/avarias_lista.html
git commit -m "feat(hora/templates): avarias_lista com filtros status/loja/chassi"
```

---

## Task 16: Templates — avaria_nova.html + avaria_detalhe.html

**Files:**
- Create: `app/templates/hora/avaria_nova.html`
- Create: `app/templates/hora/avaria_detalhe.html`

- [ ] **Step 1: Criar `avaria_nova.html`**

```jinja
{# app/templates/hora/avaria_nova.html #}
{% extends "hora/base.html" %}
{% block title %}Nova avaria — HORA{% endblock %}
{% block conteudo %}
<div class="container mt-3">
  <h3><i class="fas fa-exclamation-triangle"></i> Nova avaria</h3>
  <form method="POST" class="card card-body">
    <div class="mb-3">
      <label class="form-label">Chassi *</label>
      <input type="text" name="numero_chassi" required
             class="form-control text-uppercase" placeholder="9XXXXXXX...">
      <small class="text-muted">Moto deve estar em estoque da loja selecionada.</small>
    </div>
    <div class="mb-3">
      <label class="form-label">Loja *</label>
      <select name="loja_id" required class="form-select">
        {% for l in lojas %}
          <option value="{{ l.id }}">{{ l.rotulo_display }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="mb-3">
      <label class="form-label">Descrição *</label>
      <textarea name="descricao" required minlength="3" rows="3" class="form-control"
                placeholder="Ex: arranhão profundo no para-lama esquerdo, bateria com problema..."></textarea>
    </div>
    <div class="mb-3">
      <label class="form-label">Fotos * (mín. 1)</label>
      <div id="fotos-container">
        <div class="input-group mb-2">
          <input type="text" name="foto_s3_key" class="form-control" placeholder="S3 key (ex: hora/avarias/tmp/abc.jpg)" required>
          <input type="text" name="foto_legenda" class="form-control" placeholder="Legenda (opcional)">
        </div>
      </div>
      <button type="button" class="btn btn-sm btn-outline-secondary" onclick="adicionarFoto()">+ Adicionar foto</button>
      <small class="d-block text-muted mt-1">
        Placeholder: implementar upload real conforme padrão de hora_peca_faltando_foto.
      </small>
    </div>
    <div class="d-flex justify-content-between">
      <a href="{{ url_for('hora_avarias.lista') }}" class="btn btn-outline-secondary">Cancelar</a>
      <button class="btn btn-primary">Registrar avaria</button>
    </div>
  </form>
</div>
<script>
function adicionarFoto() {
  const c = document.getElementById('fotos-container');
  const row = document.createElement('div');
  row.className = 'input-group mb-2';
  row.innerHTML = `
    <input type="text" name="foto_s3_key" class="form-control" placeholder="S3 key">
    <input type="text" name="foto_legenda" class="form-control" placeholder="Legenda">
    <button type="button" class="btn btn-outline-danger" onclick="this.parentElement.remove()">×</button>
  `;
  c.appendChild(row);
}
</script>
{% endblock %}
```

- [ ] **Step 2: Criar `avaria_detalhe.html`**

```jinja
{# app/templates/hora/avaria_detalhe.html #}
{% extends "hora/base.html" %}
{% block title %}Avaria #{{ avaria.id }} — HORA{% endblock %}
{% block conteudo %}
<div class="container mt-3">
  <div class="d-flex justify-content-between align-items-start mb-3">
    <h3>
      <i class="fas fa-exclamation-triangle"></i> Avaria #{{ avaria.id }}
      {% if avaria.status=='ABERTA' %}<span class="badge bg-warning text-dark">Aberta</span>
      {% elif avaria.status=='RESOLVIDA' %}<span class="badge bg-success">Resolvida</span>
      {% else %}<span class="badge bg-secondary">Ignorada</span>{% endif %}
    </h3>
    <a href="{{ url_for('hora_avarias.lista') }}" class="btn btn-sm btn-outline-secondary">← Voltar</a>
  </div>

  <div class="row">
    <div class="col-md-6">
      <div class="card card-body mb-3">
        <dl class="row mb-0">
          <dt class="col-sm-4">Chassi</dt>
          <dd class="col-sm-8"><code>{{ avaria.numero_chassi }}</code></dd>
          <dt class="col-sm-4">Loja</dt>
          <dd class="col-sm-8">{{ avaria.loja.rotulo_display }}</dd>
          <dt class="col-sm-4">Registrada em</dt>
          <dd class="col-sm-8">{{ avaria.criado_em.strftime('%d/%m/%Y %H:%M') }} por {{ avaria.criado_por }}</dd>
          {% if avaria.resolvido_em %}
            <dt class="col-sm-4">Resolvida em</dt>
            <dd class="col-sm-8">{{ avaria.resolvido_em.strftime('%d/%m/%Y %H:%M') }} por {{ avaria.resolvido_por }}</dd>
            <dt class="col-sm-4">Observação</dt>
            <dd class="col-sm-8">{{ avaria.resolucao_observacao }}</dd>
          {% endif %}
        </dl>
      </div>
      <div class="card card-body mb-3">
        <strong>Descrição:</strong>
        <p class="mb-0">{{ avaria.descricao }}</p>
      </div>
    </div>
    <div class="col-md-6">
      <div class="card card-body mb-3">
        <strong>Fotos ({{ avaria.fotos|length }})</strong>
        <ul class="list-unstyled mt-2">
          {% for f in avaria.fotos %}
            <li class="mb-2">
              <code>{{ f.foto_s3_key }}</code>
              {% if f.legenda %}<br><small class="text-muted">{{ f.legenda }}</small>{% endif %}
            </li>
          {% endfor %}
        </ul>
        {% if avaria.status=='ABERTA' %}
          <form method="POST" action="{{ url_for('hora_avarias.adicionar_foto', avaria_id=avaria.id) }}" class="mt-2">
            <div class="input-group input-group-sm">
              <input name="foto_s3_key" class="form-control" placeholder="nova foto S3 key" required>
              <input name="legenda" class="form-control" placeholder="legenda">
              <button class="btn btn-outline-primary">+ Foto</button>
            </div>
          </form>
        {% endif %}
      </div>
    </div>
  </div>

  {% if avaria.status=='ABERTA' %}
  <div class="card card-body mb-3">
    <h5>Ações</h5>
    <div class="row">
      <div class="col-md-6">
        <form method="POST" action="{{ url_for('hora_avarias.resolver', avaria_id=avaria.id) }}">
          <label class="form-label">Resolver (observação obrigatória)</label>
          <textarea name="observacao" required minlength="3" class="form-control form-control-sm" rows="2"
                    placeholder="Ex: consertada pela oficina X"></textarea>
          <button class="btn btn-success btn-sm mt-2">Marcar como resolvida</button>
        </form>
      </div>
      <div class="col-md-6">
        <form method="POST" action="{{ url_for('hora_avarias.ignorar', avaria_id=avaria.id) }}">
          <label class="form-label">Ignorar (observação obrigatória)</label>
          <textarea name="observacao" required minlength="3" class="form-control form-control-sm" rows="2"
                    placeholder="Ex: avaria pré-existente"></textarea>
          <button class="btn btn-secondary btn-sm mt-2">Marcar como ignorada</button>
        </form>
      </div>
    </div>
  </div>
  {% endif %}
</div>
{% endblock %}
```

- [ ] **Step 3: Commit**

```bash
git add app/templates/hora/avaria_nova.html app/templates/hora/avaria_detalhe.html
git commit -m "feat(hora/templates): avaria_nova + avaria_detalhe com fotos e acoes"
```

---

## Task 17: Templates — transferencias_lista + transferencia_nova

**Files:**
- Create: `app/templates/hora/transferencias_lista.html`
- Create: `app/templates/hora/transferencia_nova.html`

- [ ] **Step 1: Criar `transferencias_lista.html`**

```jinja
{# app/templates/hora/transferencias_lista.html #}
{% extends "hora/base.html" %}
{% block title %}Transferências — HORA{% endblock %}
{% block conteudo %}
<div class="container-fluid mt-3">
  <div class="d-flex justify-content-between align-items-center mb-3">
    <h3><i class="fas fa-exchange-alt"></i> Transferências entre Filiais</h3>
    <a href="{{ url_for('hora_transferencias.nova') }}" class="btn btn-primary">
      <i class="fas fa-plus"></i> Nova transferência
    </a>
  </div>

  <form method="GET" class="card card-body mb-3">
    <div class="row g-2">
      <div class="col-md-3">
        <label class="form-label small">Status</label>
        <select name="status" class="form-select form-select-sm">
          <option value="">Todas</option>
          <option value="EM_TRANSITO" {% if filtros.status=='EM_TRANSITO' %}selected{% endif %}>Em trânsito</option>
          <option value="CONFIRMADA" {% if filtros.status=='CONFIRMADA' %}selected{% endif %}>Confirmadas</option>
          <option value="CANCELADA" {% if filtros.status=='CANCELADA' %}selected{% endif %}>Canceladas</option>
        </select>
      </div>
      <div class="col-md-3">
        <label class="form-label small">Loja (origem ou destino)</label>
        <select name="loja_id" class="form-select form-select-sm">
          <option value="">Todas</option>
          {% for l in lojas %}
            <option value="{{ l.id }}" {% if filtros.loja_id==l.id %}selected{% endif %}>{{ l.rotulo_display }}</option>
          {% endfor %}
        </select>
      </div>
      <div class="col-md-2 d-flex align-items-end">
        <button class="btn btn-sm btn-outline-primary">Filtrar</button>
      </div>
    </div>
  </form>

  <div class="card">
    <table class="table table-hover table-sm mb-0">
      <thead>
        <tr>
          <th>#</th><th>Status</th>
          <th>De</th><th>→</th><th>Para</th>
          <th>Qtd</th><th>Confirmados</th>
          <th>Emitida em</th><th>Por</th><th></th>
        </tr>
      </thead>
      <tbody>
        {% for t in transferencias %}
        <tr>
          <td>{{ t.id }}</td>
          <td>
            {% if t.status=='EM_TRANSITO' %}<span class="badge bg-info">Em trânsito</span>
            {% elif t.status=='CONFIRMADA' %}<span class="badge bg-success">Confirmada</span>
            {% else %}<span class="badge bg-secondary">Cancelada</span>{% endif %}
          </td>
          <td>{{ t.loja_origem.rotulo_display }}</td>
          <td>→</td>
          <td>{{ t.loja_destino.rotulo_display }}</td>
          <td>{{ t.itens|length }}</td>
          <td>{{ t.itens|selectattr('conferido_destino_em')|list|length }}</td>
          <td>{{ t.emitida_em.strftime('%d/%m %H:%M') }}</td>
          <td>{{ t.emitida_por }}</td>
          <td>
            <a href="{{ url_for('hora_transferencias.detalhe', transferencia_id=t.id) }}" class="btn btn-sm btn-outline-primary">Ver</a>
          </td>
        </tr>
        {% else %}
        <tr><td colspan="10" class="text-center text-muted py-3">Nenhuma transferência encontrada.</td></tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 2: Criar `transferencia_nova.html`**

```jinja
{# app/templates/hora/transferencia_nova.html #}
{% extends "hora/base.html" %}
{% block title %}Nova transferência — HORA{% endblock %}
{% block conteudo %}
<div class="container mt-3">
  <h3><i class="fas fa-exchange-alt"></i> Nova transferência</h3>
  <form method="POST" class="card card-body">
    <div class="row mb-3">
      <div class="col-md-6">
        <label class="form-label">Loja origem *</label>
        <select name="loja_origem_id" required class="form-select"
                {% if origem_fixa %}disabled{% endif %}>
          {% for l in lojas %}
            <option value="{{ l.id }}"
                    {% if origem_fixa==l.id %}selected{% endif %}>
              {{ l.rotulo_display }}
            </option>
          {% endfor %}
        </select>
        {% if origem_fixa %}
          <input type="hidden" name="loja_origem_id" value="{{ origem_fixa }}">
          <small class="text-muted">Sua loja é a origem (escopo).</small>
        {% endif %}
      </div>
      <div class="col-md-6">
        <label class="form-label">Loja destino *</label>
        <select name="loja_destino_id" required class="form-select">
          <option value="">(selecione)</option>
          {% for l in lojas %}
            <option value="{{ l.id }}">{{ l.rotulo_display }}</option>
          {% endfor %}
        </select>
      </div>
    </div>
    <div class="mb-3">
      <label class="form-label">Chassis * (1 por linha)</label>
      <textarea name="chassis" required rows="6" class="form-control text-uppercase"
                placeholder="9ABCDTEST1111111111111111&#10;9ABCDTEST2222222222222222"></textarea>
      <small class="text-muted">Cole a lista de chassis, um por linha. Todos devem estar em estoque da loja origem.</small>
    </div>
    <div class="mb-3">
      <label class="form-label">Observações</label>
      <textarea name="observacoes" rows="2" class="form-control"></textarea>
    </div>
    <div class="d-flex justify-content-between">
      <a href="{{ url_for('hora_transferencias.lista') }}" class="btn btn-outline-secondary">Cancelar</a>
      <button class="btn btn-primary">Emitir transferência</button>
    </div>
  </form>
</div>
{% endblock %}
```

- [ ] **Step 3: Commit**

```bash
git add app/templates/hora/transferencias_lista.html app/templates/hora/transferencia_nova.html
git commit -m "feat(hora/templates): transferencias_lista + transferencia_nova"
```

---

## Task 18: Templates — transferencia_detalhe + transferencia_confirmar_wizard

**Files:**
- Create: `app/templates/hora/transferencia_detalhe.html`
- Create: `app/templates/hora/transferencia_confirmar_wizard.html`

- [ ] **Step 1: Criar `transferencia_detalhe.html`**

```jinja
{# app/templates/hora/transferencia_detalhe.html #}
{% extends "hora/base.html" %}
{% block title %}Transferência #{{ t.id }} — HORA{% endblock %}
{% block conteudo %}
<div class="container mt-3">
  <div class="d-flex justify-content-between align-items-start mb-3">
    <h3>
      <i class="fas fa-exchange-alt"></i> Transferência #{{ t.id }}
      {% if t.status=='EM_TRANSITO' %}<span class="badge bg-info">Em trânsito</span>
      {% elif t.status=='CONFIRMADA' %}<span class="badge bg-success">Confirmada</span>
      {% else %}<span class="badge bg-secondary">Cancelada</span>{% endif %}
    </h3>
    <div>
      {% if t.status=='EM_TRANSITO' %}
        <a href="{{ url_for('hora_transferencias.confirmar_wizard', transferencia_id=t.id) }}"
           class="btn btn-sm btn-success">
          <i class="fas fa-qrcode"></i> Confirmar chegada (wizard)
        </a>
      {% endif %}
      <a href="{{ url_for('hora_transferencias.lista') }}" class="btn btn-sm btn-outline-secondary">← Voltar</a>
    </div>
  </div>

  <div class="row">
    <div class="col-md-6">
      <div class="card card-body mb-3">
        <dl class="row mb-0">
          <dt class="col-sm-4">De</dt>
          <dd class="col-sm-8">{{ t.loja_origem.rotulo_display }}</dd>
          <dt class="col-sm-4">Para</dt>
          <dd class="col-sm-8">{{ t.loja_destino.rotulo_display }}</dd>
          <dt class="col-sm-4">Emitida em</dt>
          <dd class="col-sm-8">{{ t.emitida_em.strftime('%d/%m/%Y %H:%M') }} por {{ t.emitida_por }}</dd>
          {% if t.confirmada_em %}
            <dt class="col-sm-4">Confirmada em</dt>
            <dd class="col-sm-8">{{ t.confirmada_em.strftime('%d/%m/%Y %H:%M') }} por {{ t.confirmada_por }}</dd>
          {% endif %}
          {% if t.cancelada_em %}
            <dt class="col-sm-4">Cancelada em</dt>
            <dd class="col-sm-8">{{ t.cancelada_em.strftime('%d/%m/%Y %H:%M') }} por {{ t.cancelada_por }}</dd>
            <dt class="col-sm-4">Motivo</dt>
            <dd class="col-sm-8">{{ t.motivo_cancelamento }}</dd>
          {% endif %}
          {% if t.observacoes %}
            <dt class="col-sm-4">Observações</dt>
            <dd class="col-sm-8">{{ t.observacoes }}</dd>
          {% endif %}
        </dl>
      </div>
    </div>
    <div class="col-md-6">
      {% if t.status=='EM_TRANSITO' %}
      <div class="card card-body mb-3">
        <h5>Cancelar transferência</h5>
        <p class="small text-muted">Só a loja origem pode cancelar enquanto em trânsito. Motos já confirmadas no destino permanecem.</p>
        <form method="POST" action="{{ url_for('hora_transferencias.cancelar', transferencia_id=t.id) }}">
          <textarea name="motivo" required minlength="3" rows="2" class="form-control"
                    placeholder="Motivo do cancelamento (mín. 3 chars)"></textarea>
          <button class="btn btn-danger btn-sm mt-2"
                  onclick="return confirm('Cancelar essa transferência? Motos não confirmadas voltarão para origem.')">
            Cancelar transferência
          </button>
        </form>
      </div>
      {% endif %}
    </div>
  </div>

  <h5>Itens ({{ t.itens|length }})</h5>
  <table class="table table-sm card">
    <thead>
      <tr><th>Chassi</th><th>Status</th><th>Confirmado em</th><th>Por</th><th>QR?</th></tr>
    </thead>
    <tbody>
      {% for item in t.itens %}
      <tr>
        <td><code>{{ item.numero_chassi }}</code></td>
        <td>
          {% if item.conferido_destino_em %}
            <span class="badge bg-success">Confirmado</span>
          {% else %}
            <span class="badge bg-warning text-dark">Pendente</span>
          {% endif %}
        </td>
        <td>{% if item.conferido_destino_em %}{{ item.conferido_destino_em.strftime('%d/%m %H:%M') }}{% endif %}</td>
        <td>{{ item.conferido_destino_por or '—' }}</td>
        <td>{% if item.qr_code_lido %}<i class="fas fa-check text-success"></i>{% else %}—{% endif %}</td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <h5 class="mt-4">Auditoria</h5>
  <div class="card" id="auditoria-panel">
    <table class="table table-sm mb-0">
      <thead><tr><th>Quando</th><th>Quem</th><th>Ação</th><th>Detalhe</th></tr></thead>
      <tbody>
        {% for a in t.auditoria %}
        <tr>
          <td>{{ a.criado_em.strftime('%d/%m %H:%M:%S') }}</td>
          <td>{{ a.usuario }}</td>
          <td><code>{{ a.acao }}</code></td>
          <td>{{ a.detalhe or '' }}</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
</div>
{% endblock %}
```

- [ ] **Step 2: Criar `transferencia_confirmar_wizard.html`**

```jinja
{# app/templates/hora/transferencia_confirmar_wizard.html #}
{% extends "hora/base.html" %}
{% block title %}Confirmar transferência #{{ t.id }} — HORA{% endblock %}
{% block conteudo %}
<div class="container mt-3" id="wizard-app">
  <h3><i class="fas fa-qrcode"></i> Confirmar chegada — Transferência #{{ t.id }}</h3>
  <p class="text-muted">
    De: <strong>{{ t.loja_origem.rotulo_display }}</strong> →
    Para: <strong>{{ t.loja_destino.rotulo_display }}</strong>
  </p>

  <div class="card card-body mb-3">
    <h5>Escanear / digitar chassi</h5>
    <p class="small text-muted">Escaneie o QR code do chassi ou digite manualmente.</p>
    <div class="input-group">
      <input type="text" id="chassi-input" class="form-control text-uppercase" placeholder="9XXXXXXX...">
      <button id="btn-confirmar" class="btn btn-success">Confirmar chegada</button>
    </div>
    <div class="form-check mt-2">
      <input type="checkbox" id="qr-lido" class="form-check-input">
      <label class="form-check-label small">Escaneado via QR code</label>
    </div>
    <textarea id="observacao" rows="2" class="form-control form-control-sm mt-2" placeholder="Observação (opcional)"></textarea>
    <div id="msg" class="mt-2 small"></div>
  </div>

  <h5>Itens</h5>
  <table class="table table-sm" id="itens-table">
    <thead><tr><th>Chassi</th><th>Status</th></tr></thead>
    <tbody>
      {% for item in t.itens %}
      <tr data-chassi="{{ item.numero_chassi }}">
        <td><code>{{ item.numero_chassi }}</code></td>
        <td class="status-cell">
          {% if item.conferido_destino_em %}
            <span class="badge bg-success">Confirmado</span>
          {% else %}
            <span class="badge bg-warning text-dark">Pendente</span>
          {% endif %}
        </td>
      </tr>
      {% endfor %}
    </tbody>
  </table>

  <a href="{{ url_for('hora_transferencias.detalhe', transferencia_id=t.id) }}"
     class="btn btn-outline-secondary">Concluir e voltar</a>
</div>

<script>
document.getElementById('btn-confirmar').addEventListener('click', async () => {
  const chassi = document.getElementById('chassi-input').value.trim().toUpperCase();
  const qrLido = document.getElementById('qr-lido').checked;
  const obs = document.getElementById('observacao').value;
  const msg = document.getElementById('msg');

  if (!chassi) { msg.textContent = 'Digite ou escaneie um chassi'; return; }

  const form = new FormData();
  form.append('numero_chassi', chassi);
  form.append('qr_code_lido', qrLido ? 'true' : 'false');
  form.append('observacao', obs);

  const res = await fetch(
    "{{ url_for('hora_transferencias.confirmar_item', transferencia_id=t.id) }}",
    { method: 'POST', body: form, credentials: 'same-origin' }
  );
  if (!res.ok) {
    const err = await res.json();
    msg.innerHTML = `<span class="text-danger">Erro: ${err.error}</span>`;
    return;
  }
  const data = await res.json();
  msg.innerHTML = `<span class="text-success">Confirmado. Status transf: ${data.status}</span>`;

  // Atualiza status do item na tabela
  const row = document.querySelector(`tr[data-chassi="${chassi}"]`);
  if (row) row.querySelector('.status-cell').innerHTML = '<span class="badge bg-success">Confirmado</span>';

  document.getElementById('chassi-input').value = '';
  document.getElementById('chassi-input').focus();
});
</script>
{% endblock %}
```

- [ ] **Step 3: Commit**

```bash
git add app/templates/hora/transferencia_detalhe.html app/templates/hora/transferencia_confirmar_wizard.html
git commit -m "feat(hora/templates): transferencia_detalhe + confirmar_wizard (AJAX scan)"
```

---

## Task 19: Menu + integrações estoque_lista/chassi_detalhe

**Files:**
- Modify: `app/templates/base.html`
- Modify: `app/templates/hora/estoque_lista.html`
- Modify: `app/templates/hora/estoque_chassi_detalhe.html`
- Modify: `app/hora/services/estoque_service.py` (plugar `avarias_abertas_por_chassi`)
- Modify: `app/hora/routes/estoque.py` (passar badges para template)

- [ ] **Step 1: Menu em `base.html`**

Localizar o dropdown "Lojas HORA" em `app/templates/base.html:158-165` e adicionar 2 items dentro do `<div class="dropdown-menu">`:

```html
<a class="dropdown-item" href="{{ url_for('hora_transferencias.lista') }}">
  <i class="fas fa-exchange-alt"></i> Transferências
</a>
<a class="dropdown-item" href="{{ url_for('hora_avarias.lista') }}">
  <i class="fas fa-exclamation-triangle"></i> Avarias
</a>
```

- [ ] **Step 2: Em `estoque_service.listar_estoque()`, plugar badge**

Localizar a função `listar_estoque` no `app/hora/services/estoque_service.py`. Após a montagem do dict resultado, injetar count de avarias abertas:

```python
def listar_estoque(...):
    # ... código existente ...
    resultado = [dict(...) for row in q.all()]

    # Injeção de avarias abertas (badge)
    from app.hora.services.avaria_service import avarias_abertas_por_chassi
    chassis = [r['numero_chassi'] for r in resultado]
    abertas = avarias_abertas_por_chassi(chassis)
    for r in resultado:
        r['avarias_abertas'] = abertas.get(r['numero_chassi'], 0)
        r['em_transito'] = (r.get('ultimo_evento') == 'EM_TRANSITO')
    return resultado
```

(Adaptar nomes dos campos ao que já existir. Se `ultimo_evento` não for o nome, ajustar.)

- [ ] **Step 3: Atualizar `estoque_lista.html` para mostrar badges**

Localizar a coluna de status/evento na tabela e adicionar badges:

```jinja
{% if r.avarias_abertas > 0 %}
  <span class="badge bg-warning text-dark" title="Avarias abertas">⚠ {{ r.avarias_abertas }}</span>
{% endif %}
{% if r.em_transito %}
  <span class="badge bg-info">↔ Em trânsito</span>
{% endif %}
```

Adicionar filtro `incluir_em_transito` (checkbox) se ainda não existe. Atualizar `routes/estoque.py` para passar esse filtro à `listar_estoque` (se necessário).

- [ ] **Step 4: Atualizar `estoque_chassi_detalhe.html`**

Adicionar 2 seções antes (ou depois) do histórico de eventos:

```jinja
<h5>Avarias</h5>
{% set avarias = moto_avarias %}{# passar de estoque.py #}
{% if avarias %}
  <ul>
    {% for a in avarias %}
      <li>
        <a href="{{ url_for('hora_avarias.detalhe', avaria_id=a.id) }}">
          Avaria #{{ a.id }}
        </a> — {{ a.status }} — {{ a.criado_em.strftime('%d/%m/%Y') }}
        <small>{{ a.descricao[:80] }}</small>
      </li>
    {% endfor %}
  </ul>
{% else %}<p class="text-muted">Nenhuma avaria registrada.</p>{% endif %}

<h5>Transferências</h5>
{% set transferencias = moto_transferencias %}
{% if transferencias %}
  <ul>
    {% for t in transferencias %}
      <li>
        <a href="{{ url_for('hora_transferencias.detalhe', transferencia_id=t.id) }}">
          Transf #{{ t.id }}
        </a> — {{ t.status }} — {{ t.loja_origem.apelido }} → {{ t.loja_destino.apelido }}
      </li>
    {% endfor %}
  </ul>
{% else %}<p class="text-muted">Sem transferências.</p>{% endif %}
```

Em `routes/estoque.py`, na view `chassi_detalhe`:

```python
from app.hora.models import HoraAvaria, HoraTransferenciaItem, HoraTransferencia
# ...
moto_avarias = HoraAvaria.query.filter_by(numero_chassi=chassi).order_by(HoraAvaria.criado_em.desc()).all()
moto_transferencias = (
    HoraTransferencia.query
    .join(HoraTransferenciaItem)
    .filter(HoraTransferenciaItem.numero_chassi == chassi)
    .distinct()
    .order_by(HoraTransferencia.emitida_em.desc())
    .all()
)
return render_template(
    'hora/estoque_chassi_detalhe.html',
    moto=moto,
    eventos=eventos,
    moto_avarias=moto_avarias,
    moto_transferencias=moto_transferencias,
)
```

- [ ] **Step 5: Smoke — carregar `/hora/estoque` e confirmar que não quebra**

Run: `python run.py` e acessar `/hora/estoque`. Expected: lista carrega sem erro (sem motos com avaria ainda é ok).

- [ ] **Step 6: Commit**

```bash
git add app/templates/base.html app/templates/hora/estoque_lista.html \
        app/templates/hora/estoque_chassi_detalhe.html \
        app/hora/services/estoque_service.py app/hora/routes/estoque.py
git commit -m "feat(hora/ui): menu + badges avaria/em-transito + secoes no chassi_detalhe"
```

---

## Task 20: Schemas JSON + CLAUDE.md do módulo

**Files:**
- Create: `.claude/skills/consultando-sql/schemas/tables/hora_transferencia.json` (e as outras 4)
- Modify: `app/hora/CLAUDE.md`

- [ ] **Step 1: Verificar como schemas são gerados**

Run: `ls .claude/skills/consultando-sql/schemas/ | head && find .claude/skills/consultando-sql -name "*.py" -o -name "regen*" | head -5`

Expected: identificar script de geração. Se houver `regen.py` ou similar, rodá-lo.

Se for manual, criar os 5 arquivos seguindo o schema de `hora_peca_faltando.json` (espelhar estrutura: nome, colunas, índices, PK, FKs).

- [ ] **Step 2: Rodar regen automático (se existir) OU criar 5 arquivos manualmente**

Se automático:
```bash
python .claude/skills/consultando-sql/regen_schemas.py  # ou equivalente
```

Se manual: usar `.claude/skills/consultando-sql/schemas/tables/hora_peca_faltando.json` como template e criar os 5. (Conteúdo pode ser adaptado da migration SQL — Task 2.)

- [ ] **Step 3: Atualizar `app/hora/CLAUDE.md` — seção "Ordem de implementação planejada"**

Adicionar novo bloco após o P4 existente, ou integrar. Exemplo:

```markdown
6. **P5** (2026-04-22): Transferência entre filiais + Registro de avaria em estoque.
   - 5 tabelas novas: `hora_transferencia`, `hora_transferencia_item`, `hora_transferencia_auditoria`, `hora_avaria`, `hora_avaria_foto`.
   - 2 tipos de evento novos em `hora_moto_evento.tipo`: `EM_TRANSITO`, `CANCELADA`.
   - Services: `transferencia_service`, `transferencia_audit`, `avaria_service`.
   - Invariantes preservados.
   - Spec: `docs/superpowers/specs/2026-04-22-hora-transferencia-e-avaria-design.md`.
```

- [ ] **Step 4: Rodar toda suite HORA**

Run: `pytest tests/hora/ -v`

Expected: todos os testes PASS (soma de Task 5, 6, 7, 8, 10-12 = ~25-30 testes).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/consultando-sql/schemas/tables/hora_*.json app/hora/CLAUDE.md
git commit -m "docs(hora): schemas JSON das 5 novas tabelas + atualizacao CLAUDE.md"
```

---

## Task 21: Self-audit final

- [ ] **Step 1: Validar checklist da seção 14 do spec**

Abrir `docs/superpowers/specs/2026-04-22-hora-transferencia-e-avaria-design.md` seção 14 e marcar cada item. Qualquer gap: abrir task adicional.

- [ ] **Step 2: Rodar suite HORA completa**

Run: `pytest tests/hora/ -v --tb=short`

Expected: 100% PASS.

- [ ] **Step 3: Rodar app em modo dev e validar manualmente (smoke E2E)**

```bash
python run.py
```

Acessar:
- `/hora/transferencias` → lista vazia ok
- `/hora/transferencias/nova` → formulário carrega
- `/hora/avarias` → lista vazia ok
- `/hora/avarias/nova` → formulário carrega
- `/hora/estoque` → badges funcionam (criar 1 avaria e 1 transferência manualmente via UI para testar)

- [ ] **Step 4: Verificar que o hook `ban_datetime_now.py` não bloqueou nada**

Run: `git log --oneline -20`

Expected: ~19 commits da Task 1-20, todos com hook pre-commit passado (se hook falhou, o commit não aconteceu).

- [ ] **Step 5: Commit final consolidado (se necessário)**

Se algum ajuste final foi feito:

```bash
git add -A
git commit -m "chore(hora): ajustes finais pos self-audit transferencia/avaria"
```

---

## Verificação pós-implementação

Após completar todas as tasks:

1. **Spec coverage** — reabrir spec e validar que cada item da seção 14 (Checklist de aceitação) está ✅.
2. **Invariantes preservados**:
   - Nenhum UPDATE em `hora_moto` (grep: `UPDATE hora_moto` nos services → 0 resultados esperados, exceto em código legítimo que ajusta `atualizado_em` etc.).
   - Estado via evento append-only: `hora_moto_evento` apenas INSERT.
3. **Migrations idempotentes**: rodar hora_15 pela 2ª vez → sem erro.
4. **Schemas JSON**: 5 arquivos existem em `.claude/skills/consultando-sql/schemas/tables/`.

**Quando tudo ok**: invocar `superpowers:finishing-a-development-branch` para decidir merge/PR.
