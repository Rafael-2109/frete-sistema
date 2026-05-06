# HORA Peças — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Estender módulo HORA para vender, comprar, estocar e faturar peças (produtos fungíveis sem chassi) via TagPlus, mantendo cadastro paralelo a motos sem quebrar invariantes existentes.

**Architecture:** 5 tabelas novas (`hora_peca`, `hora_tagplus_peca_map`, `hora_peca_movimento`, `hora_nf_entrada_item_peca`, `hora_venda_item_peca`) + 1 ALTER em `hora_pedido_item` (XOR moto/peça). Estoque por SUM em movimentos (mesmo padrão moto). NFe TagPlus mista (moto + peça no mesmo POST). Backfill com proteção de chassi vinculado a pedido/NF entrada.

**Tech Stack:** Flask, SQLAlchemy, PostgreSQL, Jinja2, Bootstrap 5, Font Awesome 5, Redis Queue (TagPlus async), Fernet (TagPlus crypto), pytest.

**Spec de referência:** `docs/superpowers/specs/2026-05-05-hora-pecas-design.md`

---

## File Structure

### Criar
```
scripts/migrations/hora_21_pecas_cadastro.py
scripts/migrations/hora_21_pecas_cadastro.sql
scripts/migrations/hora_22_pecas_movimento_e_itens.py
scripts/migrations/hora_22_pecas_movimento_e_itens.sql
scripts/migrations/hora_23_pecas_permissoes.py

app/hora/models/peca.py                          (NOVO conteudo: HoraPeca, HoraTagPlusPecaMap,
                                                   HoraPecaMovimento, HoraNfEntradaItemPeca,
                                                   HoraVendaItemPeca + constantes)
app/hora/models/peca_faltando.py                 (RENOMEADO de peca.py atual: HoraPecaFaltando,
                                                   HoraPecaFaltandoFoto)

app/hora/services/peca_service.py                (NOVO: CRUD HoraPeca + tagplus_map + foto)
app/hora/services/peca_estoque_service.py        (NOVO: saldo, movimento, ajuste, transferencia)
app/hora/services/chassi_protecao_service.py     (NOVO: chassi_protegido, motivos_protecao)
app/hora/services/peca_faltando_service.py       (RENOMEADO de peca_service.py atual)

app/hora/routes/pecas_cadastro.py                (NOVO blueprint routes)
app/hora/routes/pecas_estoque.py                 (NOVO blueprint routes)

app/templates/hora/pecas_cadastro_lista.html
app/templates/hora/pecas_cadastro_form.html
app/templates/hora/pecas_cadastro_detalhe.html
app/templates/hora/pecas_estoque_lista.html
app/templates/hora/pecas_estoque_detalhe.html
app/templates/hora/pecas_estoque_ajuste_modal.html
app/templates/hora/pecas_estoque_transferencia_modal.html
app/templates/hora/tagplus_peca_map_lista.html
app/templates/hora/tagplus_backfill_produtos.html
app/templates/hora/tagplus_backfill_pecas_delta.html

tests/hora/test_peca_cadastro.py
tests/hora/test_peca_estoque.py
tests/hora/test_chassi_protecao.py
tests/hora/test_pedido_compra_pecas.py
tests/hora/test_nf_entrada_pecas.py
tests/hora/test_venda_pecas.py
tests/hora/test_tagplus_payload_misto.py
tests/hora/test_tagplus_backfill_protecao.py
tests/hora/test_tagplus_backfill_delta.py
```

### Modificar
```
app/hora/models/__init__.py                      (exports + re-exports HoraPecaFaltando)
app/hora/models/compra.py                        (HoraPedidoItem: peca_id, qtd_pedida, CHECK)
app/hora/models/permissao.py                     (MODULOS_HORA += pecas_cadastro, pecas_estoque)
app/hora/routes/__init__.py                      (importa pecas_cadastro, pecas_estoque)
app/hora/routes/pedidos.py                       (AJAX itens-peca + render seção peças)
app/hora/routes/vendas.py                        (AJAX itens-peca + render seção peças)
app/hora/routes/nfs.py                           (parse + listagem peça em nf_detalhe)
app/hora/routes/recebimentos.py                  (passo wizard peça)
app/hora/routes/tagplus_routes.py                (peca_map + backfill produtos + backfill delta)
app/hora/routes/autocomplete.py                  (autocomplete peca)
app/hora/services/autocomplete_service.py        (funcao pecas())
app/hora/services/venda_service.py               (adicionar/remover/editar item_peca, cancelar)
app/hora/services/pedido_service.py              (item_peca compra)
app/hora/services/nf_entrada_service.py          (parser distingue moto/peca)
app/hora/services/recebimento_service.py         (conferencia peca + emite ENTRADA_NF)
app/hora/services/tagplus/payload_builder.py     (_montar_itens com peças, cfop por item)
app/hora/services/tagplus/backfill_service.py    (proteção chassi + 2 backfills novos)
app/templates/hora/base.html                     (menu: Cadastros, Movimentação, Faturamento)
app/templates/hora/pedido_detalhe.html           (seção Peças)
app/templates/hora/venda_detalhe.html            (seção Peças)
app/templates/hora/nf_detalhe.html               (listagem peças)
app/templates/hora/recebimento_wizard.html       (passo conferência peça)
app/hora/CLAUDE.md                               (seção 11 Peças)
```

---

## Padrão de Estilo (Lembretes Críticos)

1. **Migrations**: SEMPRE par `.py` + `.sql` (regra CLAUDE.md). `.sql` idempotente (`CREATE TABLE IF NOT EXISTS`, `ADD COLUMN IF NOT EXISTS`). `.py` com `create_app()` e verificação before/after.
2. **`sys.path.insert`** no topo de scripts em `scripts/migrations/` antes do `from app import` (regra CLAUDE.md).
3. **Templates**: usar macros de `hora/_filtros.html` e `hora/_pagination.html`. Permissões em `tem_perm_hora('modulo', 'acao')`. CSRF em forms POST.
4. **Routes**: decorator `@require_hora_perm('pecas_cadastro|pecas_estoque', 'ver|criar|editar|apagar|aprovar')`.
5. **Datetime**: importar `agora_utc_naive` de `app.utils.timezone`. NUNCA usar `datetime.now()` (timezone hook bloqueia).
6. **JSON sanitization**: `sanitize_for_json(...)` em `db.JSON`/`JSONB` se houver Decimal.
7. **TDD**: escrever teste primeiro, validar que falha, implementar mínimo, validar que passa, commit.
8. **Commits frequentes**: cada step funcional gera 1 commit.

---

## Task 1: Migrations + Modelos SQLAlchemy (P1+P2)

**Files:**
- Create: `scripts/migrations/hora_21_pecas_cadastro.sql`
- Create: `scripts/migrations/hora_21_pecas_cadastro.py`
- Create: `scripts/migrations/hora_22_pecas_movimento_e_itens.sql`
- Create: `scripts/migrations/hora_22_pecas_movimento_e_itens.py`
- Create: `app/hora/models/peca.py` (novo conteúdo)
- Rename: `app/hora/models/peca.py` → `app/hora/models/peca_faltando.py` (conteúdo atual)
- Rename: `app/hora/services/peca_service.py` → `app/hora/services/peca_faltando_service.py` (conteúdo atual)
- Rename: `app/hora/routes/pecas.py` → `app/hora/routes/pecas_faltando.py` (conteúdo atual)
- Modify: `app/hora/models/__init__.py`
- Modify: `app/hora/models/compra.py`
- Modify: `app/hora/routes/__init__.py`

### Step 1.1: Criar migration SQL hora_21

- [ ] Criar `scripts/migrations/hora_21_pecas_cadastro.sql`:

```sql
-- ============================================================
-- HORA 21: Cadastro de peças (hora_peca + hora_tagplus_peca_map)
-- Idempotente: re-executar é seguro.
-- ============================================================

CREATE TABLE IF NOT EXISTS hora_peca (
    id                   SERIAL PRIMARY KEY,
    codigo_interno       VARCHAR(50) NOT NULL UNIQUE,
    descricao            VARCHAR(255) NOT NULL,
    ncm                  VARCHAR(10),
    cfop_default         VARCHAR(5) NOT NULL DEFAULT '5.102',
    unidade              VARCHAR(5) NOT NULL DEFAULT 'UN',
    preco_venda_padrao   NUMERIC(15, 2) NOT NULL DEFAULT 0,
    foto_s3_key          VARCHAR(500),
    ativo                BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em            TIMESTAMP NOT NULL DEFAULT now(),
    atualizado_em        TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_hora_peca_ativo ON hora_peca(ativo);
CREATE INDEX IF NOT EXISTS ix_hora_peca_codigo_interno ON hora_peca(codigo_interno);

CREATE TABLE IF NOT EXISTS hora_tagplus_peca_map (
    id                   SERIAL PRIMARY KEY,
    peca_id              INTEGER NOT NULL UNIQUE REFERENCES hora_peca(id),
    tagplus_produto_id   VARCHAR(50) NOT NULL,
    tagplus_codigo       VARCHAR(50),
    cfop_default         VARCHAR(5),
    criado_em            TIMESTAMP NOT NULL DEFAULT now(),
    atualizado_em        TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_hora_tagplus_peca_map_codigo
    ON hora_tagplus_peca_map(tagplus_codigo);
CREATE INDEX IF NOT EXISTS ix_hora_tagplus_peca_map_produto_id
    ON hora_tagplus_peca_map(tagplus_produto_id);
```

- [ ] Commit:
```bash
git add scripts/migrations/hora_21_pecas_cadastro.sql
git commit -m "feat(hora): migration SQL hora_21 — peca + tagplus_peca_map"
```

### Step 1.2: Criar migration Python hora_21

- [ ] Criar `scripts/migrations/hora_21_pecas_cadastro.py`:

```python
"""Migration HORA 21: cadastro de peças.

Cria hora_peca e hora_tagplus_peca_map.

Uso:
    python scripts/migrations/hora_21_pecas_cadastro.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from app import create_app, db


SQL = """
CREATE TABLE IF NOT EXISTS hora_peca (
    id                   SERIAL PRIMARY KEY,
    codigo_interno       VARCHAR(50) NOT NULL UNIQUE,
    descricao            VARCHAR(255) NOT NULL,
    ncm                  VARCHAR(10),
    cfop_default         VARCHAR(5) NOT NULL DEFAULT '5.102',
    unidade              VARCHAR(5) NOT NULL DEFAULT 'UN',
    preco_venda_padrao   NUMERIC(15, 2) NOT NULL DEFAULT 0,
    foto_s3_key          VARCHAR(500),
    ativo                BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em            TIMESTAMP NOT NULL DEFAULT now(),
    atualizado_em        TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_hora_peca_ativo ON hora_peca(ativo);
CREATE INDEX IF NOT EXISTS ix_hora_peca_codigo_interno ON hora_peca(codigo_interno);

CREATE TABLE IF NOT EXISTS hora_tagplus_peca_map (
    id                   SERIAL PRIMARY KEY,
    peca_id              INTEGER NOT NULL UNIQUE REFERENCES hora_peca(id),
    tagplus_produto_id   VARCHAR(50) NOT NULL,
    tagplus_codigo       VARCHAR(50),
    cfop_default         VARCHAR(5),
    criado_em            TIMESTAMP NOT NULL DEFAULT now(),
    atualizado_em        TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_hora_tagplus_peca_map_codigo
    ON hora_tagplus_peca_map(tagplus_codigo);
CREATE INDEX IF NOT EXISTS ix_hora_tagplus_peca_map_produto_id
    ON hora_tagplus_peca_map(tagplus_produto_id);
"""


def existe_tabela(conn, nome: str) -> bool:
    r = conn.execute(text(
        "SELECT 1 FROM information_schema.tables WHERE table_name = :n"
    ), {'n': nome}).fetchone()
    return r is not None


def main():
    app = create_app()
    with app.app_context():
        with db.engine.connect() as conn:
            print('[before]')
            print(f'  hora_peca exists:              {existe_tabela(conn, "hora_peca")}')
            print(f'  hora_tagplus_peca_map exists:  {existe_tabela(conn, "hora_tagplus_peca_map")}')
            for stmt in [s for s in SQL.split(';') if s.strip()]:
                conn.execute(text(stmt))
            conn.commit()
            print('[after]')
            print(f'  hora_peca exists:              {existe_tabela(conn, "hora_peca")}')
            print(f'  hora_tagplus_peca_map exists:  {existe_tabela(conn, "hora_tagplus_peca_map")}')
            print('OK — hora_21 aplicada.')


if __name__ == '__main__':
    main()
```

- [ ] Rodar migration local:
```bash
source .venv/bin/activate
python scripts/migrations/hora_21_pecas_cadastro.py
```
Expected output: `[before]` com False, `[after]` com True nas duas linhas.

- [ ] Commit:
```bash
git add scripts/migrations/hora_21_pecas_cadastro.py
git commit -m "feat(hora): migration Python hora_21 — peca + tagplus_peca_map"
```

### Step 1.3: Criar migration SQL hora_22

- [ ] Criar `scripts/migrations/hora_22_pecas_movimento_e_itens.sql`:

```sql
-- ============================================================
-- HORA 22: Movimento de peças + itens em NF entrada / venda
-- + ALTER hora_pedido_item para suportar peça (XOR moto/peca).
-- Idempotente.
-- ============================================================

CREATE TABLE IF NOT EXISTS hora_peca_movimento (
    id            SERIAL PRIMARY KEY,
    peca_id       INTEGER NOT NULL REFERENCES hora_peca(id),
    loja_id       INTEGER NOT NULL REFERENCES hora_loja(id),
    tipo          VARCHAR(25) NOT NULL,
    qtd           NUMERIC(15, 3) NOT NULL,
    ref_tabela    VARCHAR(50),
    ref_id        INTEGER,
    motivo        VARCHAR(500),
    operador      VARCHAR(100),
    criado_em     TIMESTAMP NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS ix_hora_peca_mov_saldo
    ON hora_peca_movimento(peca_id, loja_id, criado_em);
CREATE INDEX IF NOT EXISTS ix_hora_peca_mov_ref
    ON hora_peca_movimento(ref_tabela, ref_id);

CREATE TABLE IF NOT EXISTS hora_nf_entrada_item_peca (
    id                       SERIAL PRIMARY KEY,
    nf_id                    INTEGER NOT NULL REFERENCES hora_nf_entrada(id),
    peca_id                  INTEGER NOT NULL REFERENCES hora_peca(id),
    qtd_nf                   NUMERIC(15, 3) NOT NULL,
    preco_real               NUMERIC(15, 2) NOT NULL,
    modelo_texto_original    VARCHAR(255),
    qtd_conferida            NUMERIC(15, 3),
    divergencia_qtd          VARCHAR(20),
    foto_conferencia_s3_key  VARCHAR(500),
    conferida_em             TIMESTAMP,
    conferida_por            VARCHAR(100)
);

CREATE INDEX IF NOT EXISTS ix_hora_nf_ent_item_peca_nf
    ON hora_nf_entrada_item_peca(nf_id);
CREATE INDEX IF NOT EXISTS ix_hora_nf_ent_item_peca_peca
    ON hora_nf_entrada_item_peca(peca_id);

CREATE TABLE IF NOT EXISTS hora_venda_item_peca (
    id                          SERIAL PRIMARY KEY,
    venda_id                    INTEGER NOT NULL REFERENCES hora_venda(id),
    peca_id                     INTEGER NOT NULL REFERENCES hora_peca(id),
    qtd                         NUMERIC(15, 3) NOT NULL,
    preco_unitario_referencia   NUMERIC(15, 2) NOT NULL,
    desconto_aplicado           NUMERIC(15, 2) NOT NULL DEFAULT 0,
    preco_final                 NUMERIC(15, 2) NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_hora_venda_item_peca_venda
    ON hora_venda_item_peca(venda_id);
CREATE INDEX IF NOT EXISTS ix_hora_venda_item_peca_peca
    ON hora_venda_item_peca(peca_id);

-- ALTER hora_pedido_item: adicionar peca_id, qtd_pedida com CHECK XOR.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='hora_pedido_item' AND column_name='peca_id'
    ) THEN
        ALTER TABLE hora_pedido_item ADD COLUMN peca_id INTEGER REFERENCES hora_peca(id);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name='hora_pedido_item' AND column_name='qtd_pedida'
    ) THEN
        ALTER TABLE hora_pedido_item ADD COLUMN qtd_pedida NUMERIC(15, 3);
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name='hora_pedido_item' AND constraint_name='chk_hora_pedido_item_xor'
    ) THEN
        ALTER TABLE hora_pedido_item
            ADD CONSTRAINT chk_hora_pedido_item_xor CHECK (
                (peca_id IS NULL AND qtd_pedida IS NULL) OR
                (peca_id IS NOT NULL AND modelo_id IS NULL AND numero_chassi IS NULL
                 AND qtd_pedida IS NOT NULL)
            );
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS ix_hora_pedido_item_peca
    ON hora_pedido_item(peca_id);
```

- [ ] Commit:
```bash
git add scripts/migrations/hora_22_pecas_movimento_e_itens.sql
git commit -m "feat(hora): migration SQL hora_22 — movimento + itens peça"
```

### Step 1.4: Criar migration Python hora_22

- [ ] Criar `scripts/migrations/hora_22_pecas_movimento_e_itens.py`:

```python
"""Migration HORA 22: movimento + itens peça (NF entrada / venda) + ALTER pedido_item."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text
from app import create_app, db


def main():
    app = create_app()
    with app.app_context():
        sql_path = os.path.join(os.path.dirname(__file__), 'hora_22_pecas_movimento_e_itens.sql')
        with open(sql_path, encoding='utf-8') as f:
            sql_full = f.read()

        with db.engine.connect() as conn:
            print('[before]')
            for tab in ('hora_peca_movimento', 'hora_nf_entrada_item_peca', 'hora_venda_item_peca'):
                exists = conn.execute(text(
                    "SELECT 1 FROM information_schema.tables WHERE table_name = :n"
                ), {'n': tab}).fetchone() is not None
                print(f'  {tab:35s} exists: {exists}')
            col_peca = conn.execute(text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='hora_pedido_item' AND column_name='peca_id'"
            )).fetchone() is not None
            print(f'  hora_pedido_item.peca_id col exists: {col_peca}')

            # Executa o SQL inteiro (DO $$ ... $$ exige execução como bloco).
            conn.execute(text(sql_full))
            conn.commit()

            print('[after]')
            for tab in ('hora_peca_movimento', 'hora_nf_entrada_item_peca', 'hora_venda_item_peca'):
                exists = conn.execute(text(
                    "SELECT 1 FROM information_schema.tables WHERE table_name = :n"
                ), {'n': tab}).fetchone() is not None
                print(f'  {tab:35s} exists: {exists}')
            col_peca = conn.execute(text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name='hora_pedido_item' AND column_name='peca_id'"
            )).fetchone() is not None
            print(f'  hora_pedido_item.peca_id col exists: {col_peca}')
            print('OK — hora_22 aplicada.')


if __name__ == '__main__':
    main()
```

- [ ] Rodar migration:
```bash
python scripts/migrations/hora_22_pecas_movimento_e_itens.py
```

- [ ] Commit:
```bash
git add scripts/migrations/hora_22_pecas_movimento_e_itens.py
git commit -m "feat(hora): migration Python hora_22 — movimento + itens peça"
```

### Step 1.5: Renomear peca.py atual para peca_faltando.py

- [ ] Mover arquivo:
```bash
git mv app/hora/models/peca.py app/hora/models/peca_faltando.py
git mv app/hora/services/peca_service.py app/hora/services/peca_faltando_service.py
git mv app/hora/routes/pecas.py app/hora/routes/pecas_faltando.py
```

- [ ] Atualizar `app/hora/models/__init__.py` linha de import (`from app.hora.models.peca import` → `from app.hora.models.peca_faltando import`).

- [ ] Atualizar imports nos arquivos renomeados:
  - Em `app/hora/services/peca_faltando_service.py`: `from app.hora.models import HoraPecaFaltando, HoraPecaFaltandoFoto` (já vem do `__init__`)
  - Em `app/hora/routes/pecas_faltando.py`: trocar `from app.hora.services import peca_service` por `from app.hora.services import peca_faltando_service as peca_service`

- [ ] Atualizar `app/hora/routes/__init__.py`: `pecas` → `pecas_faltando`.

- [ ] Rodar smoke test:
```bash
python -c "from app import create_app; create_app()"
```
Expected: sem erro de import.

- [ ] Commit:
```bash
git commit -am "refactor(hora): renomeia peca.py para peca_faltando.py (libera nome para cadastro de peças)"
```

### Step 1.6: Criar novo `app/hora/models/peca.py`

- [ ] Criar arquivo:

```python
"""Cadastro de peças (produtos fungíveis sem chassi) + estoque + itens.

Este modulo cobre o ciclo COMPLETO de peças:
- HoraPeca               cadastro principal
- HoraTagPlusPecaMap     mapeamento opcional para emissao NFe TagPlus
- HoraPecaMovimento      log de entradas/saidas (saldo derivado por SUM)
- HoraNfEntradaItemPeca  linha de peca em NF de entrada (com conferencia 1:1)
- HoraVendaItemPeca      linha de peca em pedido de venda

NAO confundir com HoraPecaFaltando (peca faltando em moto — vide peca_faltando.py).
"""
from app import db
from app.utils.timezone import agora_utc_naive


# ============================================================
# Constantes
# ============================================================

PECA_MOV_TIPO_ENTRADA_NF = 'ENTRADA_NF'
PECA_MOV_TIPO_SAIDA_VENDA = 'SAIDA_VENDA'
PECA_MOV_TIPO_TRANSF_OUT = 'TRANSFERENCIA_OUT'
PECA_MOV_TIPO_TRANSF_IN = 'TRANSFERENCIA_IN'
PECA_MOV_TIPO_AJUSTE_POS = 'AJUSTE_POS'
PECA_MOV_TIPO_AJUSTE_NEG = 'AJUSTE_NEG'
PECA_MOV_TIPO_DEVOLUCAO_VENDA = 'DEVOLUCAO_VENDA'
PECA_MOV_TIPO_DEVOLUCAO_FORN = 'DEVOLUCAO_FORNECEDOR'

PECA_MOV_TIPOS_VALIDOS = (
    PECA_MOV_TIPO_ENTRADA_NF, PECA_MOV_TIPO_SAIDA_VENDA,
    PECA_MOV_TIPO_TRANSF_OUT, PECA_MOV_TIPO_TRANSF_IN,
    PECA_MOV_TIPO_AJUSTE_POS, PECA_MOV_TIPO_AJUSTE_NEG,
    PECA_MOV_TIPO_DEVOLUCAO_VENDA, PECA_MOV_TIPO_DEVOLUCAO_FORN,
)

PECA_DIVERGENCIA_OK = 'OK'
PECA_DIVERGENCIA_FALTA = 'FALTA'
PECA_DIVERGENCIA_SOBRA = 'SOBRA'
PECA_DIVERGENCIA_AVARIA = 'AVARIA'

PECA_DIVERGENCIA_VALIDAS = (
    PECA_DIVERGENCIA_OK, PECA_DIVERGENCIA_FALTA,
    PECA_DIVERGENCIA_SOBRA, PECA_DIVERGENCIA_AVARIA,
)


# ============================================================
# HoraPeca
# ============================================================

class HoraPeca(db.Model):
    """Catalogo de peças (capacete, retrovisor, bateria, ...)."""
    __tablename__ = 'hora_peca'

    id = db.Column(db.Integer, primary_key=True)
    codigo_interno = db.Column(db.String(50), nullable=False, unique=True, index=True)
    descricao = db.Column(db.String(255), nullable=False)
    ncm = db.Column(db.String(10), nullable=True)
    cfop_default = db.Column(db.String(5), nullable=False, default='5.102')
    unidade = db.Column(db.String(5), nullable=False, default='UN')
    preco_venda_padrao = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    foto_s3_key = db.Column(db.String(500), nullable=True)
    ativo = db.Column(db.Boolean, nullable=False, default=True, index=True)

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    def __repr__(self):
        return f'<HoraPeca {self.codigo_interno} {self.descricao!r}>'


# ============================================================
# HoraTagPlusPecaMap
# ============================================================

class HoraTagPlusPecaMap(db.Model):
    """Mapeamento opcional de peca para integracao TagPlus.

    Peca pode existir sem mapeamento (somente uso interno). Para emitir
    NFe via TagPlus, exige tagplus_produto_id preenchido.
    """
    __tablename__ = 'hora_tagplus_peca_map'

    id = db.Column(db.Integer, primary_key=True)
    peca_id = db.Column(
        db.Integer, db.ForeignKey('hora_peca.id'),
        nullable=False, unique=True, index=True,
    )
    tagplus_produto_id = db.Column(db.String(50), nullable=False)
    tagplus_codigo = db.Column(db.String(50), nullable=True, index=True)
    cfop_default = db.Column(db.String(5), nullable=True)
    # Se preenchido, sobrescreve hora_peca.cfop_default na emissao NFe.

    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    atualizado_em = db.Column(db.DateTime, nullable=True, onupdate=agora_utc_naive)

    peca = db.relationship('HoraPeca', backref=db.backref('tagplus_map', uselist=False))

    def __repr__(self):
        return f'<HoraTagPlusPecaMap peca={self.peca_id} tagplus={self.tagplus_produto_id}>'


# ============================================================
# HoraPecaMovimento — saldo derivado por SUM
# ============================================================

class HoraPecaMovimento(db.Model):
    """Movimento de peça (signed: + entrada, - saida).

    Saldo de uma combinacao (peca_id, loja_id) = SUM(qtd) deste log.
    Sem tabela de saldo materializado (mesmo padrao moto: estoque deriva
    de eventos).
    """
    __tablename__ = 'hora_peca_movimento'

    id = db.Column(db.Integer, primary_key=True)
    peca_id = db.Column(
        db.Integer, db.ForeignKey('hora_peca.id'),
        nullable=False, index=True,
    )
    loja_id = db.Column(
        db.Integer, db.ForeignKey('hora_loja.id'),
        nullable=False, index=True,
    )
    tipo = db.Column(db.String(25), nullable=False)
    qtd = db.Column(db.Numeric(15, 3), nullable=False)
    ref_tabela = db.Column(db.String(50), nullable=True)
    ref_id = db.Column(db.Integer, nullable=True)
    motivo = db.Column(db.String(500), nullable=True)
    operador = db.Column(db.String(100), nullable=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)

    peca = db.relationship('HoraPeca', backref='movimentos')
    loja = db.relationship('HoraLoja')

    __table_args__ = (
        db.Index('ix_hora_peca_mov_saldo', 'peca_id', 'loja_id', 'criado_em'),
        db.Index('ix_hora_peca_mov_ref', 'ref_tabela', 'ref_id'),
    )

    def __repr__(self):
        return (
            f'<HoraPecaMovimento peca={self.peca_id} loja={self.loja_id} '
            f'{self.tipo} {self.qtd}>'
        )


# ============================================================
# HoraNfEntradaItemPeca — peca em NF de entrada (com conferencia 1:1)
# ============================================================

class HoraNfEntradaItemPeca(db.Model):
    """Linha de peca em NF de entrada com conferencia embutida.

    Conferencia e 1:1 (uma linha de NF = uma conferencia, qtd_nf vs
    qtd_conferida). Por isso campos de conferencia moram aqui em vez
    de tabela paralela.
    """
    __tablename__ = 'hora_nf_entrada_item_peca'

    id = db.Column(db.Integer, primary_key=True)
    nf_id = db.Column(
        db.Integer, db.ForeignKey('hora_nf_entrada.id'),
        nullable=False, index=True,
    )
    peca_id = db.Column(
        db.Integer, db.ForeignKey('hora_peca.id'),
        nullable=False, index=True,
    )
    qtd_nf = db.Column(db.Numeric(15, 3), nullable=False)
    preco_real = db.Column(db.Numeric(15, 2), nullable=False)
    modelo_texto_original = db.Column(db.String(255), nullable=True)

    # Conferencia embutida (1:1).
    qtd_conferida = db.Column(db.Numeric(15, 3), nullable=True)
    divergencia_qtd = db.Column(db.String(20), nullable=True)
    foto_conferencia_s3_key = db.Column(db.String(500), nullable=True)
    conferida_em = db.Column(db.DateTime, nullable=True)
    conferida_por = db.Column(db.String(100), nullable=True)

    nf = db.relationship('HoraNfEntrada', backref='itens_peca')
    peca = db.relationship('HoraPeca')

    @property
    def conferida(self) -> bool:
        return self.qtd_conferida is not None

    def __repr__(self):
        return f'<HoraNfEntradaItemPeca nf={self.nf_id} peca={self.peca_id} qtd={self.qtd_nf}>'


# ============================================================
# HoraVendaItemPeca — peca em pedido de venda
# ============================================================

class HoraVendaItemPeca(db.Model):
    """Linha de peca em pedido de venda.

    `preco_unitario_referencia` e snapshot de hora_peca.preco_venda_padrao
    no momento da venda (auditoria). `preco_final` = qtd * (referencia - desconto).
    """
    __tablename__ = 'hora_venda_item_peca'

    id = db.Column(db.Integer, primary_key=True)
    venda_id = db.Column(
        db.Integer, db.ForeignKey('hora_venda.id'),
        nullable=False, index=True,
    )
    peca_id = db.Column(
        db.Integer, db.ForeignKey('hora_peca.id'),
        nullable=False, index=True,
    )
    qtd = db.Column(db.Numeric(15, 3), nullable=False)
    preco_unitario_referencia = db.Column(db.Numeric(15, 2), nullable=False)
    desconto_aplicado = db.Column(db.Numeric(15, 2), nullable=False, default=0)
    preco_final = db.Column(db.Numeric(15, 2), nullable=False)

    venda = db.relationship('HoraVenda', backref='itens_peca')
    peca = db.relationship('HoraPeca')

    def __repr__(self):
        return (
            f'<HoraVendaItemPeca venda={self.venda_id} peca={self.peca_id} '
            f'qtd={self.qtd} R${self.preco_final}>'
        )
```

- [ ] Commit:
```bash
git add app/hora/models/peca.py
git commit -m "feat(hora): models de cadastro/estoque/itens de peça"
```

### Step 1.7: Atualizar `app/hora/models/__init__.py`

- [ ] Adicionar imports e exports:

```python
# Adicionar APOS o import de peca_faltando:
from app.hora.models.peca import (
    HoraPeca,
    HoraTagPlusPecaMap,
    HoraPecaMovimento,
    HoraNfEntradaItemPeca,
    HoraVendaItemPeca,
    PECA_MOV_TIPO_ENTRADA_NF,
    PECA_MOV_TIPO_SAIDA_VENDA,
    PECA_MOV_TIPO_TRANSF_OUT,
    PECA_MOV_TIPO_TRANSF_IN,
    PECA_MOV_TIPO_AJUSTE_POS,
    PECA_MOV_TIPO_AJUSTE_NEG,
    PECA_MOV_TIPO_DEVOLUCAO_VENDA,
    PECA_MOV_TIPO_DEVOLUCAO_FORN,
    PECA_MOV_TIPOS_VALIDOS,
    PECA_DIVERGENCIA_OK,
    PECA_DIVERGENCIA_FALTA,
    PECA_DIVERGENCIA_SOBRA,
    PECA_DIVERGENCIA_AVARIA,
    PECA_DIVERGENCIA_VALIDAS,
)
```

- [ ] Acrescentar nomes em `__all__`.

- [ ] Smoke test:
```bash
python -c "from app.hora.models import HoraPeca, HoraPecaMovimento; print('OK')"
```

- [ ] Commit:
```bash
git commit -am "feat(hora): exporta novos models de peças no __init__"
```

### Step 1.8: ALTER hora_pedido_item no model

- [ ] Editar `app/hora/models/compra.py` na classe `HoraPedidoItem`:

```python
# Adicionar APOS preco_compra_esperado:
peca_id = db.Column(
    db.Integer, db.ForeignKey('hora_peca.id'),
    nullable=True, index=True,
)
qtd_pedida = db.Column(db.Numeric(15, 3), nullable=True)

# Adicionar APOS modelo = relationship:
peca = db.relationship('HoraPeca')

# CHECK em __table_args__ (acrescentar OU criar __table_args__):
__table_args__ = (
    db.CheckConstraint(
        '(peca_id IS NULL AND qtd_pedida IS NULL) OR '
        '(peca_id IS NOT NULL AND modelo_id IS NULL AND numero_chassi IS NULL '
        'AND qtd_pedida IS NOT NULL)',
        name='chk_hora_pedido_item_xor',
    ),
)
```

- [ ] Smoke test:
```bash
python -c "from app.hora.models import HoraPedidoItem; print(HoraPedidoItem.peca_id)"
```

- [ ] Commit:
```bash
git commit -am "feat(hora): HoraPedidoItem — peca_id, qtd_pedida (XOR moto/peca)"
```

---

## Task 2: Services — peca, peca_estoque, chassi_protecao (P3)

**Files:**
- Create: `app/hora/services/peca_service.py`
- Create: `app/hora/services/peca_estoque_service.py`
- Create: `app/hora/services/chassi_protecao_service.py`
- Create: `tests/hora/test_peca_cadastro.py`
- Create: `tests/hora/test_peca_estoque.py`
- Create: `tests/hora/test_chassi_protecao.py`

### Step 2.1: Test peca_service — criar peça mínima

- [ ] Criar `tests/hora/test_peca_cadastro.py`:

```python
"""Testes do peca_service (cadastro de peças)."""
from decimal import Decimal

import pytest

from app import db
from app.hora.models import HoraPeca, HoraTagPlusPecaMap


def test_criar_peca_minima(app):
    from app.hora.services import peca_service
    with app.app_context():
        p = peca_service.criar_peca(
            codigo_interno='CAP-PRETO-M',
            descricao='Capacete preto tamanho M',
        )
        assert p.id is not None
        assert p.codigo_interno == 'CAP-PRETO-M'
        assert p.cfop_default == '5.102'
        assert p.unidade == 'UN'
        assert p.preco_venda_padrao == Decimal('0')
        assert p.ativo is True


def test_codigo_interno_unique(app):
    from app.hora.services import peca_service
    with app.app_context():
        peca_service.criar_peca(codigo_interno='DUP-TEST', descricao='1')
        with pytest.raises(ValueError, match='ja existe'):
            peca_service.criar_peca(codigo_interno='DUP-TEST', descricao='2')


def test_set_tagplus_map(app):
    from app.hora.services import peca_service
    with app.app_context():
        p = peca_service.criar_peca(codigo_interno='MAP-TEST', descricao='X')
        peca_service.set_tagplus_map(
            peca_id=p.id, tagplus_produto_id='999', tagplus_codigo='CAP-X',
        )
        m = HoraTagPlusPecaMap.query.filter_by(peca_id=p.id).first()
        assert m is not None
        assert m.tagplus_produto_id == '999'


def test_inativar_peca(app):
    from app.hora.services import peca_service
    with app.app_context():
        p = peca_service.criar_peca(codigo_interno='INA-TEST', descricao='X')
        peca_service.inativar_peca(p.id)
        p2 = HoraPeca.query.get(p.id)
        assert p2.ativo is False
```

- [ ] Rodar e verificar falha:
```bash
pytest tests/hora/test_peca_cadastro.py -v
```
Expected: ImportError (peca_service não existe ainda).

### Step 2.2: Implementar peca_service mínimo

- [ ] Criar `app/hora/services/peca_service.py`:

```python
"""Cadastro de peças (CRUD + foto + mapeamento TagPlus opcional).

NAO confundir com peca_faltando_service.py (peça FALTANDO em moto).
"""
from __future__ import annotations

from decimal import Decimal
from typing import Optional, List

from flask import current_app

from app import db
from app.hora.models import HoraPeca, HoraTagPlusPecaMap
from app.utils.file_storage import FileStorage


ALLOWED_FOTO_EXT = {'jpg', 'jpeg', 'png', 'webp', 'heic'}


def criar_peca(
    codigo_interno: str,
    descricao: str,
    ncm: Optional[str] = None,
    cfop_default: str = '5.102',
    unidade: str = 'UN',
    preco_venda_padrao: Decimal = Decimal('0'),
    ativo: bool = True,
) -> HoraPeca:
    """Cria peca. Levanta ValueError em duplicata de codigo_interno."""
    codigo = (codigo_interno or '').strip().upper()
    if not codigo:
        raise ValueError('codigo_interno e obrigatorio')
    if not (descricao or '').strip():
        raise ValueError('descricao e obrigatoria')

    existente = HoraPeca.query.filter_by(codigo_interno=codigo).first()
    if existente:
        raise ValueError(f'peca com codigo_interno={codigo!r} ja existe (id={existente.id})')

    p = HoraPeca(
        codigo_interno=codigo,
        descricao=descricao.strip(),
        ncm=(ncm or '').strip() or None,
        cfop_default=(cfop_default or '5.102').strip(),
        unidade=(unidade or 'UN').strip().upper(),
        preco_venda_padrao=Decimal(str(preco_venda_padrao or 0)),
        ativo=bool(ativo),
    )
    db.session.add(p)
    db.session.commit()
    return p


def editar_peca(peca_id: int, **campos) -> HoraPeca:
    """Atualiza campos editaveis de peca. Ignora chaves desconhecidas."""
    p = HoraPeca.query.get(peca_id)
    if not p:
        raise ValueError(f'peca {peca_id} nao encontrada')

    editaveis = {
        'descricao', 'ncm', 'cfop_default', 'unidade',
        'preco_venda_padrao', 'ativo',
    }
    for k, v in campos.items():
        if k in editaveis:
            if k == 'preco_venda_padrao':
                v = Decimal(str(v or 0))
            setattr(p, k, v)
    db.session.commit()
    return p


def inativar_peca(peca_id: int) -> HoraPeca:
    return editar_peca(peca_id, ativo=False)


def ativar_peca(peca_id: int) -> HoraPeca:
    return editar_peca(peca_id, ativo=True)


def set_tagplus_map(
    peca_id: int,
    tagplus_produto_id: str,
    tagplus_codigo: Optional[str] = None,
    cfop_default: Optional[str] = None,
) -> HoraTagPlusPecaMap:
    """Cria ou atualiza mapeamento TagPlus para uma peca."""
    p = HoraPeca.query.get(peca_id)
    if not p:
        raise ValueError(f'peca {peca_id} nao encontrada')
    if not (tagplus_produto_id or '').strip():
        raise ValueError('tagplus_produto_id e obrigatorio')

    m = HoraTagPlusPecaMap.query.filter_by(peca_id=peca_id).first()
    if not m:
        m = HoraTagPlusPecaMap(peca_id=peca_id)
        db.session.add(m)
    m.tagplus_produto_id = str(tagplus_produto_id).strip()
    m.tagplus_codigo = (tagplus_codigo or '').strip() or None
    m.cfop_default = (cfop_default or '').strip() or None
    db.session.commit()
    return m


def remover_tagplus_map(peca_id: int) -> None:
    m = HoraTagPlusPecaMap.query.filter_by(peca_id=peca_id).first()
    if m:
        db.session.delete(m)
        db.session.commit()


def upload_foto(peca_id: int, file_obj, criado_por: Optional[str] = None) -> str:
    """Salva foto no S3 e atualiza foto_s3_key. Retorna a key."""
    p = HoraPeca.query.get(peca_id)
    if not p:
        raise ValueError(f'peca {peca_id} nao encontrada')

    storage = FileStorage()
    folder = f'hora/pecas/{p.id}'
    s3_key = storage.save_file(
        file=file_obj, folder=folder, allowed_extensions=ALLOWED_FOTO_EXT,
    )
    if not s3_key:
        raise ValueError('Falha ao salvar foto')
    p.foto_s3_key = s3_key
    db.session.commit()
    return s3_key


def get_foto_url(peca: HoraPeca) -> Optional[str]:
    if not peca or not peca.foto_s3_key:
        return None
    try:
        return FileStorage().get_file_url(peca.foto_s3_key)
    except Exception as exc:
        current_app.logger.warning(f'Erro foto peca {peca.id}: {exc}')
        return None


def listar_pecas(
    busca: Optional[str] = None,
    ativo: Optional[bool] = None,
    sem_tagplus: bool = False,
    limit: int = 200,
) -> List[HoraPeca]:
    q = HoraPeca.query
    if busca:
        b = f'%{busca.strip()}%'
        q = q.filter(
            db.or_(
                HoraPeca.codigo_interno.ilike(b),
                HoraPeca.descricao.ilike(b),
            )
        )
    if ativo is not None:
        q = q.filter(HoraPeca.ativo == ativo)
    if sem_tagplus:
        sub = db.session.query(HoraTagPlusPecaMap.peca_id).subquery()
        q = q.filter(~HoraPeca.id.in_(sub))
    return q.order_by(HoraPeca.codigo_interno).limit(limit).all()


def get_peca(peca_id: int) -> Optional[HoraPeca]:
    return HoraPeca.query.get(peca_id)
```

- [ ] Rodar testes:
```bash
pytest tests/hora/test_peca_cadastro.py -v
```
Expected: 4 passed.

- [ ] Commit:
```bash
git add tests/hora/test_peca_cadastro.py app/hora/services/peca_service.py
git commit -m "feat(hora): peca_service — CRUD cadastro + tagplus_map + foto"
```

### Step 2.3: Test peca_estoque_service — saldo e movimento

- [ ] Criar `tests/hora/test_peca_estoque.py`:

```python
"""Testes do peca_estoque_service (saldo derivado por SUM)."""
from decimal import Decimal

import pytest

from app.hora.models import HoraPecaMovimento


def test_saldo_inicial_zero(app, peca_factory, loja_factory):
    from app.hora.services import peca_estoque_service
    with app.app_context():
        p = peca_factory()
        l = loja_factory()
        assert peca_estoque_service.saldo(p.id, l.id) == Decimal('0')


def test_registrar_entrada(app, peca_factory, loja_factory):
    from app.hora.services import peca_estoque_service
    with app.app_context():
        p = peca_factory()
        l = loja_factory()
        peca_estoque_service.registrar_movimento(
            peca_id=p.id, loja_id=l.id, tipo='ENTRADA_NF',
            qtd=Decimal('5'), motivo='teste',
        )
        assert peca_estoque_service.saldo(p.id, l.id) == Decimal('5')


def test_saida_subtrai(app, peca_factory, loja_factory):
    from app.hora.services import peca_estoque_service
    with app.app_context():
        p = peca_factory()
        l = loja_factory()
        peca_estoque_service.registrar_movimento(
            peca_id=p.id, loja_id=l.id, tipo='ENTRADA_NF', qtd=Decimal('10'),
        )
        peca_estoque_service.registrar_movimento(
            peca_id=p.id, loja_id=l.id, tipo='SAIDA_VENDA', qtd=Decimal('-3'),
        )
        assert peca_estoque_service.saldo(p.id, l.id) == Decimal('7')


def test_ajuste_manual_positivo(app, peca_factory, loja_factory):
    from app.hora.services import peca_estoque_service
    with app.app_context():
        p = peca_factory()
        l = loja_factory()
        peca_estoque_service.ajuste_manual(
            peca_id=p.id, loja_id=l.id,
            qtd_signed=Decimal('5'), motivo='inventario inicial', operador='admin',
        )
        movs = HoraPecaMovimento.query.filter_by(peca_id=p.id).all()
        assert len(movs) == 1
        assert movs[0].tipo == 'AJUSTE_POS'


def test_transferencia_atomica(app, peca_factory, loja_factory):
    from app.hora.services import peca_estoque_service
    with app.app_context():
        p = peca_factory()
        l_origem = loja_factory()
        l_destino = loja_factory()
        peca_estoque_service.registrar_movimento(
            peca_id=p.id, loja_id=l_origem.id, tipo='ENTRADA_NF', qtd=Decimal('10'),
        )
        peca_estoque_service.transferencia(
            peca_id=p.id, loja_origem_id=l_origem.id, loja_destino_id=l_destino.id,
            qtd=Decimal('3'), motivo='transf teste', operador='admin',
        )
        assert peca_estoque_service.saldo(p.id, l_origem.id) == Decimal('7')
        assert peca_estoque_service.saldo(p.id, l_destino.id) == Decimal('3')


def test_transferencia_sem_saldo_falha(app, peca_factory, loja_factory):
    from app.hora.services import peca_estoque_service
    with app.app_context():
        p = peca_factory()
        l1 = loja_factory()
        l2 = loja_factory()
        with pytest.raises(ValueError, match='saldo insuficiente'):
            peca_estoque_service.transferencia(
                peca_id=p.id, loja_origem_id=l1.id, loja_destino_id=l2.id,
                qtd=Decimal('5'), motivo='x', operador='admin',
            )
```

- [ ] Rodar e verificar falha (módulo não existe):
```bash
pytest tests/hora/test_peca_estoque.py -v
```

### Step 2.4: Implementar peca_estoque_service

- [ ] Criar `app/hora/services/peca_estoque_service.py`:

```python
"""Estoque de pecas: saldo derivado por SUM em hora_peca_movimento.

Mesmo padrao do estoque de motos (que deriva de eventos). Sem tabela de
saldo materializado.
"""
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from sqlalchemy import func

from app import db
from app.hora.models import (
    HoraPeca,
    HoraPecaMovimento,
    HoraLoja,
    PECA_MOV_TIPO_AJUSTE_NEG,
    PECA_MOV_TIPO_AJUSTE_POS,
    PECA_MOV_TIPO_TRANSF_IN,
    PECA_MOV_TIPO_TRANSF_OUT,
    PECA_MOV_TIPOS_VALIDOS,
)


def saldo(peca_id: int, loja_id: int) -> Decimal:
    """Saldo atual de uma combinacao (peca, loja)."""
    r = db.session.query(
        func.coalesce(func.sum(HoraPecaMovimento.qtd), 0)
    ).filter(
        HoraPecaMovimento.peca_id == peca_id,
        HoraPecaMovimento.loja_id == loja_id,
    ).scalar()
    return Decimal(str(r or 0))


def saldos_por_loja(peca_id: int) -> dict[int, Decimal]:
    """Saldo por loja para uma peca (apenas saldo > 0)."""
    rows = db.session.query(
        HoraPecaMovimento.loja_id,
        func.sum(HoraPecaMovimento.qtd).label('total'),
    ).filter(
        HoraPecaMovimento.peca_id == peca_id,
    ).group_by(HoraPecaMovimento.loja_id).all()
    return {loja_id: Decimal(str(t)) for loja_id, t in rows if t}


def registrar_movimento(
    peca_id: int,
    loja_id: int,
    tipo: str,
    qtd: Decimal,
    ref_tabela: Optional[str] = None,
    ref_id: Optional[int] = None,
    motivo: Optional[str] = None,
    operador: Optional[str] = None,
) -> HoraPecaMovimento:
    """Registra movimento. NAO faz commit (chamador controla transacao se quiser).

    Excecao: chamadas isoladas (ajuste_manual, transferencia) commitam aqui.
    """
    if tipo not in PECA_MOV_TIPOS_VALIDOS:
        raise ValueError(f'tipo invalido: {tipo!r}')
    if not HoraPeca.query.get(peca_id):
        raise ValueError(f'peca {peca_id} nao existe')
    if not HoraLoja.query.get(loja_id):
        raise ValueError(f'loja {loja_id} nao existe')

    qtd_dec = Decimal(str(qtd))
    if qtd_dec == 0:
        raise ValueError('qtd nao pode ser zero')

    mov = HoraPecaMovimento(
        peca_id=peca_id, loja_id=loja_id, tipo=tipo, qtd=qtd_dec,
        ref_tabela=ref_tabela, ref_id=ref_id,
        motivo=motivo, operador=operador,
    )
    db.session.add(mov)
    db.session.flush()
    return mov


def ajuste_manual(
    peca_id: int,
    loja_id: int,
    qtd_signed: Decimal,
    motivo: str,
    operador: str,
) -> HoraPecaMovimento:
    """Ajuste positivo (qtd > 0) ou negativo (qtd < 0). Motivo obrigatorio."""
    if not (motivo or '').strip():
        raise ValueError('motivo do ajuste e obrigatorio')
    qtd_dec = Decimal(str(qtd_signed))
    if qtd_dec == 0:
        raise ValueError('qtd_signed nao pode ser zero')
    tipo = PECA_MOV_TIPO_AJUSTE_POS if qtd_dec > 0 else PECA_MOV_TIPO_AJUSTE_NEG

    if qtd_dec < 0:
        atual = saldo(peca_id, loja_id)
        if atual + qtd_dec < 0:
            raise ValueError(
                f'saldo insuficiente para ajuste negativo: '
                f'saldo={atual}, qtd_negativa={qtd_dec}'
            )

    mov = registrar_movimento(
        peca_id=peca_id, loja_id=loja_id, tipo=tipo, qtd=qtd_dec,
        motivo=motivo, operador=operador,
    )
    db.session.commit()
    return mov


def transferencia(
    peca_id: int,
    loja_origem_id: int,
    loja_destino_id: int,
    qtd: Decimal,
    motivo: str,
    operador: str,
) -> tuple[HoraPecaMovimento, HoraPecaMovimento]:
    """Transferencia atomica: emite OUT na origem e IN no destino."""
    if loja_origem_id == loja_destino_id:
        raise ValueError('loja origem e destino devem ser diferentes')
    qtd_dec = Decimal(str(qtd))
    if qtd_dec <= 0:
        raise ValueError('qtd deve ser positiva')
    atual = saldo(peca_id, loja_origem_id)
    if atual < qtd_dec:
        raise ValueError(
            f'saldo insuficiente: origem tem {atual}, transferencia exige {qtd_dec}'
        )
    if not (motivo or '').strip():
        raise ValueError('motivo e obrigatorio')

    mov_out = registrar_movimento(
        peca_id=peca_id, loja_id=loja_origem_id,
        tipo=PECA_MOV_TIPO_TRANSF_OUT, qtd=-qtd_dec,
        motivo=motivo, operador=operador,
    )
    mov_in = registrar_movimento(
        peca_id=peca_id, loja_id=loja_destino_id,
        tipo=PECA_MOV_TIPO_TRANSF_IN, qtd=qtd_dec,
        ref_tabela='hora_peca_movimento', ref_id=mov_out.id,
        motivo=motivo, operador=operador,
    )
    db.session.commit()
    return mov_out, mov_in


def listar_estoque(
    loja_id: Optional[int] = None,
    peca_id: Optional[int] = None,
    busca: Optional[str] = None,
    somente_positivo: bool = True,
    lojas_permitidas_ids: Optional[List[int]] = None,
) -> list[dict]:
    """Lista saldo agregado por (peca, loja) com filtros.

    Retorna list[dict] com keys: peca_id, codigo_interno, descricao,
    foto_s3_key, loja_id, loja_nome, saldo.
    """
    q = (
        db.session.query(
            HoraPeca.id.label('peca_id'),
            HoraPeca.codigo_interno,
            HoraPeca.descricao,
            HoraPeca.foto_s3_key,
            HoraPeca.unidade,
            HoraLoja.id.label('loja_id'),
            HoraLoja.apelido,
            HoraLoja.nome,
            func.coalesce(func.sum(HoraPecaMovimento.qtd), 0).label('saldo'),
        )
        .select_from(HoraPecaMovimento)
        .join(HoraPeca, HoraPeca.id == HoraPecaMovimento.peca_id)
        .join(HoraLoja, HoraLoja.id == HoraPecaMovimento.loja_id)
    )
    if loja_id:
        q = q.filter(HoraPecaMovimento.loja_id == loja_id)
    if peca_id:
        q = q.filter(HoraPecaMovimento.peca_id == peca_id)
    if busca:
        b = f'%{busca.strip()}%'
        q = q.filter(db.or_(
            HoraPeca.codigo_interno.ilike(b),
            HoraPeca.descricao.ilike(b),
        ))
    if lojas_permitidas_ids is not None:
        if not lojas_permitidas_ids:
            return []
        q = q.filter(HoraPecaMovimento.loja_id.in_(lojas_permitidas_ids))

    q = q.group_by(
        HoraPeca.id, HoraPeca.codigo_interno, HoraPeca.descricao,
        HoraPeca.foto_s3_key, HoraPeca.unidade,
        HoraLoja.id, HoraLoja.apelido, HoraLoja.nome,
    )
    if somente_positivo:
        q = q.having(func.coalesce(func.sum(HoraPecaMovimento.qtd), 0) > 0)
    q = q.order_by(HoraPeca.codigo_interno, HoraLoja.apelido)

    return [
        {
            'peca_id': r.peca_id,
            'codigo_interno': r.codigo_interno,
            'descricao': r.descricao,
            'foto_s3_key': r.foto_s3_key,
            'unidade': r.unidade,
            'loja_id': r.loja_id,
            'loja_nome': r.apelido or r.nome,
            'saldo': Decimal(str(r.saldo)),
        }
        for r in q.all()
    ]


def historico(
    peca_id: int,
    loja_id: Optional[int] = None,
    limit: int = 100,
) -> list[HoraPecaMovimento]:
    q = HoraPecaMovimento.query.filter(HoraPecaMovimento.peca_id == peca_id)
    if loja_id:
        q = q.filter(HoraPecaMovimento.loja_id == loja_id)
    return q.order_by(HoraPecaMovimento.criado_em.desc()).limit(limit).all()
```

- [ ] Rodar testes:
```bash
pytest tests/hora/test_peca_estoque.py -v
```
Expected: 6 passed (precisa de `peca_factory` e `loja_factory` em conftest).

- [ ] Caso falhe por fixture, criar fixtures em `tests/hora/conftest.py` (verificar se já existem):
```python
@pytest.fixture
def peca_factory(app):
    from app.hora.services import peca_service
    counter = [0]
    def make(**kw):
        counter[0] += 1
        defaults = {'codigo_interno': f'TEST-PEC-{counter[0]}', 'descricao': 'Test'}
        defaults.update(kw)
        return peca_service.criar_peca(**defaults)
    return make


@pytest.fixture
def loja_factory(app):
    from app import db
    from app.hora.models import HoraLoja
    counter = [0]
    def make(**kw):
        counter[0] += 1
        defaults = {
            'cnpj': f'00000000{counter[0]:06d}',
            'nome': f'Loja Teste {counter[0]}',
            'ativa': True,
        }
        defaults.update(kw)
        l = HoraLoja(**defaults)
        db.session.add(l)
        db.session.commit()
        return l
    return make
```

- [ ] Commit:
```bash
git add tests/hora/test_peca_estoque.py app/hora/services/peca_estoque_service.py tests/hora/conftest.py
git commit -m "feat(hora): peca_estoque_service — saldo por SUM, ajuste, transferência"
```

### Step 2.5: Test chassi_protecao_service

- [ ] Criar `tests/hora/test_chassi_protecao.py`:

```python
"""Testes de chassi_protegido — chassi vinculado a pedido/NF entrada e protegido."""
from decimal import Decimal


def test_chassi_novo_nao_protegido(app):
    from app.hora.services import chassi_protecao_service
    with app.app_context():
        assert chassi_protecao_service.chassi_protegido('CHASSI-NUNCA-VISTO') is False


def test_chassi_em_pedido_protegido(app, pedido_compra_factory):
    from app.hora.services import chassi_protecao_service
    with app.app_context():
        chassi = '9ABCDPED1111111111'
        pedido_compra_factory(chassis=[chassi])
        assert chassi_protecao_service.chassi_protegido(chassi) is True


def test_chassi_em_nf_entrada_protegido(app, nf_entrada_factory):
    from app.hora.services import chassi_protecao_service
    with app.app_context():
        chassi = '9ABCDNF22222222222'
        nf_entrada_factory(chassis=[chassi])
        assert chassi_protecao_service.chassi_protegido(chassi) is True


def test_chassi_vazio_nao_protegido(app):
    from app.hora.services import chassi_protecao_service
    with app.app_context():
        assert chassi_protecao_service.chassi_protegido('') is False
        assert chassi_protecao_service.chassi_protegido(None) is False


def test_motivos_protecao_lista(app, pedido_compra_factory, nf_entrada_factory):
    from app.hora.services import chassi_protecao_service
    with app.app_context():
        chassi = '9ABCDDUO33333333333'
        pedido_compra_factory(chassis=[chassi])
        nf_entrada_factory(chassis=[chassi])
        motivos = chassi_protecao_service.motivos_protecao(chassi)
        origens = {m['origem'] for m in motivos}
        assert origens == {'pedido', 'nf_entrada'}
```

- [ ] Rodar e verificar falha:
```bash
pytest tests/hora/test_chassi_protecao.py -v
```

### Step 2.6: Implementar chassi_protecao_service

- [ ] Criar `app/hora/services/chassi_protecao_service.py`:

```python
"""Helper para identificar chassi protegido (vinculado a pedido/NF entrada).

Chassi vinculado a HoraPedidoItem ou HoraNfEntradaItem e fonte de verdade.
Backfill de NFe de venda NUNCA sobrescreve atributos de HoraMoto desse chassi.
"""
from __future__ import annotations

from typing import List

from app import db
from app.hora.models import HoraNfEntradaItem, HoraPedidoItem


def chassi_protegido(numero_chassi: str | None) -> bool:
    """True se chassi tem registro em HoraPedidoItem ou HoraNfEntradaItem."""
    chassi = (numero_chassi or '').strip().upper()
    if not chassi:
        return False
    em_pedido = db.session.query(HoraPedidoItem.id).filter(
        HoraPedidoItem.numero_chassi == chassi,
    ).limit(1).first() is not None
    if em_pedido:
        return True
    em_nf = db.session.query(HoraNfEntradaItem.id).filter(
        HoraNfEntradaItem.numero_chassi == chassi,
    ).limit(1).first() is not None
    return em_nf


def motivos_protecao(numero_chassi: str | None) -> List[dict]:
    """Lista motivos. Retorna [] se nao protegido."""
    chassi = (numero_chassi or '').strip().upper()
    if not chassi:
        return []
    motivos: List[dict] = []
    for pi in HoraPedidoItem.query.filter(HoraPedidoItem.numero_chassi == chassi).all():
        motivos.append({
            'origem': 'pedido',
            'pedido_id': pi.pedido_id,
            'item_id': pi.id,
        })
    for ni in HoraNfEntradaItem.query.filter(HoraNfEntradaItem.numero_chassi == chassi).all():
        motivos.append({
            'origem': 'nf_entrada',
            'nf_id': ni.nf_id,
            'item_id': ni.id,
        })
    return motivos
```

- [ ] Rodar testes:
```bash
pytest tests/hora/test_chassi_protecao.py -v
```
Expected: 5 passed (após criar fixtures `pedido_compra_factory` e `nf_entrada_factory` em `conftest.py`).

- [ ] Commit:
```bash
git add tests/hora/test_chassi_protecao.py app/hora/services/chassi_protecao_service.py
git commit -m "feat(hora): chassi_protecao_service — protege chassi vinculado a pedido/NF entrada"
```

---

## Task 3: Permissões + Migration data fix (P4)

**Files:**
- Modify: `app/hora/models/permissao.py`
- Create: `scripts/migrations/hora_23_pecas_permissoes.py`

### Step 3.1: Adicionar módulos em MODULOS_HORA

- [ ] Editar `app/hora/models/permissao.py`, acrescentar em `MODULOS_HORA`:

```python
# Adicionar APOS ('vendas', 'Vendas (NF saida)'):
('pecas_cadastro', 'Cadastro de Peças'),
('pecas_estoque', 'Estoque de Peças'),
```

- [ ] Smoke test:
```bash
python -c "from app.hora.models.permissao import MODULOS_HORA; assert ('pecas_cadastro', 'Cadastro de Peças') in MODULOS_HORA"
```

- [ ] Commit:
```bash
git commit -am "feat(hora): adiciona modulos de permissao pecas_cadastro e pecas_estoque"
```

### Step 3.2: Migration Python data fix (concede permissão a admins existentes)

- [ ] Criar `scripts/migrations/hora_23_pecas_permissoes.py`:

```python
"""Migration HORA 23: data fix — admins ja recebem perm de pecas_cadastro/pecas_estoque
automaticamente (decorator nao exige entry para admin); este script é apenas
documentacao e ponto de extensao caso queira ativar perm para usuarios nao-admin.

Sem DDL — apenas registra que os modulos novos foram adicionados em MODULOS_HORA.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app
from app.hora.models.permissao import MODULOS_HORA


def main():
    app = create_app()
    with app.app_context():
        modulos_alvo = {'pecas_cadastro', 'pecas_estoque'}
        existentes = {m for m, _ in MODULOS_HORA}
        faltando = modulos_alvo - existentes
        if faltando:
            raise SystemExit(f'ERRO: modulos {faltando} ausentes em MODULOS_HORA. '
                             f'Atualize app/hora/models/permissao.py.')
        print(f'OK — {modulos_alvo} presentes em MODULOS_HORA.')
        print('Admins (perfil="administrador") ja tem acesso por default.')
        print('Para conceder a usuarios nao-admin: tela /hora/permissoes')


if __name__ == '__main__':
    main()
```

- [ ] Rodar:
```bash
python scripts/migrations/hora_23_pecas_permissoes.py
```

- [ ] Commit:
```bash
git add scripts/migrations/hora_23_pecas_permissoes.py
git commit -m "feat(hora): migration hora_23 valida permissoes pecas_cadastro/estoque"
```

---

## Task 4: Cadastro de Peças — UI completa (P5)

**Files:**
- Create: `app/hora/routes/pecas_cadastro.py`
- Create: `app/templates/hora/pecas_cadastro_lista.html`
- Create: `app/templates/hora/pecas_cadastro_form.html`
- Create: `app/templates/hora/pecas_cadastro_detalhe.html`
- Modify: `app/hora/routes/__init__.py`
- Modify: `app/hora/services/autocomplete_service.py`
- Modify: `app/hora/routes/autocomplete.py`

### Step 4.1: Criar routes pecas_cadastro

- [ ] Criar `app/hora/routes/pecas_cadastro.py`:

```python
"""Rotas de Cadastro de Peças (cadastros)."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app.hora.decorators import require_hora_perm
from app.hora.models import HoraPeca
from app.hora.routes import hora_bp
from app.hora.services import peca_service


def _operador() -> str:
    if hasattr(current_user, 'nome'):
        return current_user.nome
    return getattr(current_user, 'email', 'desconhecido')


@hora_bp.route('/pecas/cadastro')
@require_hora_perm('pecas_cadastro', 'ver')
def pecas_cadastro_lista():
    busca = (request.args.get('busca') or '').strip() or None
    apenas_ativos = request.args.get('apenas_ativos') == '1'
    sem_tagplus = request.args.get('sem_tagplus') == '1'

    pecas = peca_service.listar_pecas(
        busca=busca,
        ativo=True if apenas_ativos else None,
        sem_tagplus=sem_tagplus,
    )
    rows = []
    for p in pecas:
        rows.append({
            'peca': p,
            'foto_url': peca_service.get_foto_url(p),
            'tagplus_map': p.tagplus_map,
        })
    return render_template(
        'hora/pecas_cadastro_lista.html',
        rows=rows,
        filtro_busca=busca,
        filtro_apenas_ativos=apenas_ativos,
        filtro_sem_tagplus=sem_tagplus,
    )


@hora_bp.route('/pecas/cadastro/novo', methods=['GET', 'POST'])
@require_hora_perm('pecas_cadastro', 'criar')
def pecas_cadastro_novo():
    if request.method == 'POST':
        try:
            preco = (request.form.get('preco_venda_padrao') or '0').replace(',', '.')
            p = peca_service.criar_peca(
                codigo_interno=(request.form.get('codigo_interno') or ''),
                descricao=(request.form.get('descricao') or ''),
                ncm=(request.form.get('ncm') or '') or None,
                cfop_default=(request.form.get('cfop_default') or '5.102'),
                unidade=(request.form.get('unidade') or 'UN'),
                preco_venda_padrao=Decimal(preco),
                ativo=request.form.get('ativo') == '1',
            )
            tp_id = (request.form.get('tagplus_produto_id') or '').strip()
            if tp_id:
                peca_service.set_tagplus_map(
                    peca_id=p.id,
                    tagplus_produto_id=tp_id,
                    tagplus_codigo=(request.form.get('tagplus_codigo') or '') or None,
                    cfop_default=(request.form.get('tagplus_cfop_default') or '') or None,
                )
            flash(f'Peça {p.codigo_interno} criada.', 'success')
            return redirect(url_for('hora.pecas_cadastro_detalhe', peca_id=p.id))
        except (ValueError, InvalidOperation) as exc:
            flash(f'Erro: {exc}', 'danger')

    return render_template(
        'hora/pecas_cadastro_form.html',
        peca=None, tagplus_map=None,
        pode_editar_tagplus=current_user.tem_perm_hora('tagplus', 'editar'),
    )


@hora_bp.route('/pecas/cadastro/<int:peca_id>')
@require_hora_perm('pecas_cadastro', 'ver')
def pecas_cadastro_detalhe(peca_id: int):
    p = HoraPeca.query.get_or_404(peca_id)
    return render_template(
        'hora/pecas_cadastro_detalhe.html',
        peca=p,
        foto_url=peca_service.get_foto_url(p),
        tagplus_map=p.tagplus_map,
    )


@hora_bp.route('/pecas/cadastro/<int:peca_id>/editar', methods=['GET', 'POST'])
@require_hora_perm('pecas_cadastro', 'editar')
def pecas_cadastro_editar(peca_id: int):
    p = HoraPeca.query.get_or_404(peca_id)
    if request.method == 'POST':
        try:
            preco = (request.form.get('preco_venda_padrao') or '0').replace(',', '.')
            peca_service.editar_peca(
                peca_id=p.id,
                descricao=(request.form.get('descricao') or '').strip(),
                ncm=(request.form.get('ncm') or '') or None,
                cfop_default=(request.form.get('cfop_default') or '5.102'),
                unidade=(request.form.get('unidade') or 'UN'),
                preco_venda_padrao=Decimal(preco),
                ativo=request.form.get('ativo') == '1',
            )
            tp_id = (request.form.get('tagplus_produto_id') or '').strip()
            if tp_id:
                peca_service.set_tagplus_map(
                    peca_id=p.id,
                    tagplus_produto_id=tp_id,
                    tagplus_codigo=(request.form.get('tagplus_codigo') or '') or None,
                    cfop_default=(request.form.get('tagplus_cfop_default') or '') or None,
                )
            elif p.tagplus_map:
                peca_service.remover_tagplus_map(p.id)
            flash(f'Peça {p.codigo_interno} atualizada.', 'success')
            return redirect(url_for('hora.pecas_cadastro_detalhe', peca_id=p.id))
        except (ValueError, InvalidOperation) as exc:
            flash(f'Erro: {exc}', 'danger')

    return render_template(
        'hora/pecas_cadastro_form.html',
        peca=p, tagplus_map=p.tagplus_map,
        pode_editar_tagplus=current_user.tem_perm_hora('tagplus', 'editar'),
    )


@hora_bp.route('/pecas/cadastro/<int:peca_id>/foto', methods=['POST'])
@require_hora_perm('pecas_cadastro', 'editar')
def pecas_cadastro_upload_foto(peca_id: int):
    arquivo = request.files.get('foto')
    if not arquivo or not arquivo.filename:
        flash('Selecione uma foto.', 'danger')
        return redirect(url_for('hora.pecas_cadastro_detalhe', peca_id=peca_id))
    try:
        peca_service.upload_foto(peca_id, arquivo, criado_por=_operador())
        flash('Foto atualizada.', 'success')
    except ValueError as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.pecas_cadastro_detalhe', peca_id=peca_id))


@hora_bp.route('/pecas/cadastro/<int:peca_id>/toggle-ativo', methods=['POST'])
@require_hora_perm('pecas_cadastro', 'apagar')
def pecas_cadastro_toggle_ativo(peca_id: int):
    p = HoraPeca.query.get_or_404(peca_id)
    if p.ativo:
        peca_service.inativar_peca(p.id)
        flash(f'Peça {p.codigo_interno} inativada.', 'warning')
    else:
        peca_service.ativar_peca(p.id)
        flash(f'Peça {p.codigo_interno} ativada.', 'success')
    return redirect(url_for('hora.pecas_cadastro_lista'))


@hora_bp.route('/pecas/cadastro/autocomplete')
@require_hora_perm('pecas_cadastro', 'ver')
def pecas_cadastro_autocomplete():
    """Autocomplete de peças para forms (pedido compra/venda)."""
    q = (request.args.get('q') or '').strip()
    if len(q) < 2:
        return jsonify([])
    pecas = peca_service.listar_pecas(busca=q, ativo=True, limit=20)
    return jsonify([
        {
            'id': p.id,
            'codigo_interno': p.codigo_interno,
            'descricao': p.descricao,
            'unidade': p.unidade,
            'preco_venda_padrao': str(p.preco_venda_padrao),
        }
        for p in pecas
    ])
```

### Step 4.2: Registrar blueprint

- [ ] Editar `app/hora/routes/__init__.py`:

```python
# Adicionar 'pecas_cadastro' na tupla de imports.
from . import (  # noqa: E402, F401
    dashboard,
    cadastros,
    pedidos,
    nfs,
    recebimentos,
    permissoes,
    estoque,
    devolucoes,
    pecas_faltando,           # antes era 'pecas'
    pecas_cadastro,           # NOVO
    transferencias,
    avarias,
    emprestimos,
    vendas,
    tagplus_routes,
    autocomplete,
)
```

- [ ] Smoke test (Flask carrega):
```bash
python -c "from app import create_app; app=create_app(); print(app.url_map)" | grep pecas_cadastro
```
Expected: várias linhas com `/hora/pecas/cadastro/...`

- [ ] Commit:
```bash
git add app/hora/routes/pecas_cadastro.py app/hora/routes/__init__.py
git commit -m "feat(hora): rotas de cadastro de peças"
```

### Step 4.3: Template lista (segue padrão modelos_lista.html)

- [ ] Criar `app/templates/hora/pecas_cadastro_lista.html`:

```jinja
{% extends "hora/base.html" %}
{% from "hora/_filtros.html" import filtros_form %}

{% block hora_content %}
<div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
  <h2><i class="fas fa-cogs"></i> Peças</h2>
  <div class="d-flex gap-2">
    {% if current_user.tem_perm_hora('tagplus', 'editar') %}
    <a href="{{ url_for('hora.tagplus_peca_map_lista') }}" class="btn btn-outline-secondary"
       title="Mapear TagPlus em massa">
      <i class="fas fa-link"></i> Mapear TagPlus em massa
    </a>
    {% endif %}
    {% if current_user.tem_perm_hora('pecas_cadastro', 'criar') %}
    <a href="{{ url_for('hora.pecas_cadastro_novo') }}" class="btn btn-primary">
      <i class="fas fa-plus"></i> Nova peça
    </a>
    {% endif %}
  </div>
</div>

{% call filtros_form(url_for('hora.pecas_cadastro_lista')) %}
  <div class="col-md-4">
    <label class="form-label small mb-1">Busca (código ou descrição)</label>
    <input type="text" name="busca" value="{{ filtro_busca or '' }}"
           placeholder="Digite ao menos 2 caracteres"
           class="form-control form-control-sm">
  </div>
  <div class="col-md-3">
    <label class="form-label small mb-1">Status</label>
    <div class="form-check form-check-inline mt-1">
      <input class="form-check-input" type="checkbox" name="apenas_ativos" value="1"
             id="chkApenasAtivos" {% if filtro_apenas_ativos %}checked{% endif %}>
      <label class="form-check-label" for="chkApenasAtivos">Apenas ativas</label>
    </div>
  </div>
  <div class="col-md-3">
    <label class="form-label small mb-1">Mapeamento TagPlus</label>
    <div class="form-check form-check-inline mt-1">
      <input class="form-check-input" type="checkbox" name="sem_tagplus" value="1"
             id="chkSemTagplus" {% if filtro_sem_tagplus %}checked{% endif %}>
      <label class="form-check-label" for="chkSemTagplus">Apenas sem mapeamento</label>
    </div>
  </div>
  <div class="col-md-auto d-flex gap-2 align-items-end">
    <button type="submit" class="btn btn-sm btn-primary"><i class="fas fa-filter"></i> Filtrar</button>
    <a href="{{ url_for('hora.pecas_cadastro_lista') }}" class="btn btn-sm btn-outline-secondary">
      <i class="fas fa-eraser"></i> Limpar
    </a>
  </div>
{% endcall %}

<div class="table-responsive">
  <table class="table table-hover align-middle">
    <thead><tr>
      <th style="width:60px;">Foto</th>
      <th>Código</th>
      <th>Descrição</th>
      <th>NCM</th>
      <th>CFOP</th>
      <th>Un.</th>
      <th class="text-end">Preço padrão</th>
      <th>Status</th>
      <th>TagPlus</th>
      <th class="text-end">Ações</th>
    </tr></thead>
    <tbody>
      {% for r in rows %}
        {% set p = r.peca %}
        {% set tm = r.tagplus_map %}
        <tr>
          <td>
            {% if r.foto_url %}
              <img src="{{ r.foto_url }}" alt="" style="height:40px;width:40px;object-fit:cover;border-radius:4px;">
            {% else %}
              <span class="text-muted"><i class="fas fa-image"></i></span>
            {% endif %}
          </td>
          <td><code>{{ p.codigo_interno }}</code></td>
          <td>{{ p.descricao }}</td>
          <td><small>{{ p.ncm or '—' }}</small></td>
          <td><span class="badge bg-light text-dark">{{ p.cfop_default }}</span></td>
          <td>{{ p.unidade }}</td>
          <td class="text-end">{{ p.preco_venda_padrao|valor_br }}</td>
          <td>
            {% if p.ativo %}<span class="badge bg-success">Ativa</span>
            {% else %}<span class="badge bg-secondary">Inativa</span>{% endif %}
          </td>
          <td>
            {% if tm %}
              <code class="small">{{ tm.tagplus_produto_id }}</code>
              {% if tm.tagplus_codigo %}<br><small class="text-muted">{{ tm.tagplus_codigo }}</small>{% endif %}
            {% else %}
              <span class="text-warning small"><i class="fas fa-exclamation-triangle"></i> não mapeada</span>
            {% endif %}
          </td>
          <td class="text-end">
            <div class="btn-group btn-group-sm" role="group">
              <a href="{{ url_for('hora.pecas_cadastro_detalhe', peca_id=p.id) }}"
                 class="btn btn-outline-primary"><i class="fas fa-eye"></i></a>
              {% if current_user.tem_perm_hora('pecas_cadastro', 'editar') %}
              <a href="{{ url_for('hora.pecas_cadastro_editar', peca_id=p.id) }}"
                 class="btn btn-outline-primary"><i class="fas fa-pen"></i></a>
              {% endif %}
              {% if current_user.tem_perm_hora('pecas_cadastro', 'apagar') %}
              <form method="post"
                    action="{{ url_for('hora.pecas_cadastro_toggle_ativo', peca_id=p.id) }}"
                    class="d-inline"
                    onsubmit="return confirm('{% if p.ativo %}Inativar{% else %}Ativar{% endif %} {{ p.codigo_interno }}?');">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                {% if p.ativo %}
                <button type="submit" class="btn btn-outline-warning"><i class="fas fa-ban"></i></button>
                {% else %}
                <button type="submit" class="btn btn-outline-success"><i class="fas fa-check"></i></button>
                {% endif %}
              </form>
              {% endif %}
            </div>
          </td>
        </tr>
      {% else %}
        <tr><td colspan="10" class="text-center text-muted">Nenhuma peça cadastrada.</td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>
{% endblock %}
```

### Step 4.4: Templates form e detalhe

- [ ] Criar `app/templates/hora/pecas_cadastro_form.html` (segue padrão modelos_novo.html):

```jinja
{% extends "hora/base.html" %}
{% block hora_content %}
<h2 class="mb-3">{% if peca %}Editar peça{% else %}Nova peça{% endif %}</h2>
<form method="post" class="card p-3" style="max-width: 800px;" enctype="multipart/form-data">
  <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">

  <div class="row g-3">
    <div class="col-md-4">
      <label class="form-label">Código interno <span class="text-danger">*</span></label>
      <input type="text" name="codigo_interno" class="form-control text-uppercase" required maxlength="50"
             value="{{ peca.codigo_interno if peca else '' }}"
             placeholder="Ex.: CAP-PRETO-M"
             {% if peca %}readonly title="Código não pode ser alterado"{% endif %}>
    </div>
    <div class="col-md-8">
      <label class="form-label">Descrição <span class="text-danger">*</span></label>
      <input type="text" name="descricao" class="form-control" required maxlength="255"
             value="{{ peca.descricao if peca else '' }}"
             placeholder="Ex.: Capacete preto tamanho M">
    </div>

    <div class="col-md-3">
      <label class="form-label">NCM</label>
      <input type="text" name="ncm" class="form-control" maxlength="10"
             value="{{ peca.ncm if peca else '' }}" placeholder="00000000">
    </div>
    <div class="col-md-3">
      <label class="form-label">CFOP padrão</label>
      <input type="text" name="cfop_default" class="form-control" maxlength="5"
             pattern="[0-9]\.[0-9]{3}"
             value="{{ peca.cfop_default if peca else '5.102' }}" placeholder="5.102">
      <small class="text-muted">5.102 (intra) / 6.102 (inter — auto pelo builder)</small>
    </div>
    <div class="col-md-2">
      <label class="form-label">Unidade</label>
      <input type="text" name="unidade" class="form-control text-uppercase" maxlength="5"
             value="{{ peca.unidade if peca else 'UN' }}" placeholder="UN">
    </div>
    <div class="col-md-4">
      <label class="form-label">Preço de venda padrão</label>
      <input type="text" name="preco_venda_padrao" class="form-control"
             value="{{ peca.preco_venda_padrao if peca else '0,00' }}"
             placeholder="0,00" inputmode="decimal">
      <small class="text-muted">Snapshot na venda preserva este valor.</small>
    </div>

    <div class="col-12">
      <div class="form-check">
        <input class="form-check-input" type="checkbox" name="ativo" value="1" id="chkAtivo"
               {% if (peca and peca.ativo) or not peca %}checked{% endif %}>
        <label class="form-check-label" for="chkAtivo">Peça ativa</label>
      </div>
    </div>
  </div>

  {% if pode_editar_tagplus %}
  <hr class="my-4">
  <h5><i class="fas fa-link"></i> Mapeamento TagPlus (opcional)</h5>
  <div class="row g-3">
    <div class="col-md-4">
      <label class="form-label">ID TagPlus</label>
      <input type="text" name="tagplus_produto_id" class="form-control" maxlength="50"
             value="{{ tagplus_map.tagplus_produto_id if tagplus_map else '' }}"
             placeholder="ex.: 1234">
      <small class="text-muted">Sem isso, peça não pode ser faturada via TagPlus.</small>
    </div>
    <div class="col-md-4">
      <label class="form-label">Código DANFE</label>
      <input type="text" name="tagplus_codigo" class="form-control" maxlength="50"
             value="{{ tagplus_map.tagplus_codigo if tagplus_map else '' }}"
             placeholder="ex.: CAP-PRETO-M">
      <small class="text-muted">Para backfill de NFs já emitidas.</small>
    </div>
    <div class="col-md-4">
      <label class="form-label">CFOP override (TagPlus)</label>
      <input type="text" name="tagplus_cfop_default" class="form-control" maxlength="5"
             pattern="[0-9]\.[0-9]{3}"
             value="{{ tagplus_map.cfop_default if tagplus_map else '' }}"
             placeholder="(usa o cadastro)">
      <small class="text-muted">Sobrescreve o CFOP do cadastro só na emissão TagPlus.</small>
    </div>
  </div>
  {% endif %}

  <div class="d-flex gap-2 mt-4">
    <button type="submit" class="btn btn-primary">{% if peca %}Salvar alterações{% else %}Criar peça{% endif %}</button>
    <a href="{{ url_for('hora.pecas_cadastro_lista') }}" class="btn btn-secondary">Cancelar</a>
  </div>
</form>
{% endblock %}
```

- [ ] Criar `app/templates/hora/pecas_cadastro_detalhe.html`:

```jinja
{% extends "hora/base.html" %}
{% block hora_content %}
<div class="d-flex justify-content-between align-items-start mb-3">
  <h2>
    <i class="fas fa-cogs"></i> {{ peca.codigo_interno }}
    {% if peca.ativo %}<span class="badge bg-success">Ativa</span>
    {% else %}<span class="badge bg-secondary">Inativa</span>{% endif %}
  </h2>
  <div class="d-flex gap-2">
    {% if current_user.tem_perm_hora('pecas_cadastro', 'editar') %}
    <a href="{{ url_for('hora.pecas_cadastro_editar', peca_id=peca.id) }}" class="btn btn-sm btn-outline-primary">
      <i class="fas fa-pen"></i> Editar
    </a>
    {% endif %}
    <a href="{{ url_for('hora.pecas_cadastro_lista') }}" class="btn btn-sm btn-outline-secondary">← Voltar</a>
  </div>
</div>

<div class="row">
  <div class="col-md-4">
    <div class="card p-3 mb-3 text-center">
      {% if foto_url %}
        <img src="{{ foto_url }}" alt="{{ peca.descricao }}" class="img-fluid rounded mb-2" style="max-height:300px;">
      {% else %}
        <div class="text-muted py-5"><i class="fas fa-image fa-3x"></i><br><small>Sem foto</small></div>
      {% endif %}
      {% if current_user.tem_perm_hora('pecas_cadastro', 'editar') %}
      <form method="post" enctype="multipart/form-data"
            action="{{ url_for('hora.pecas_cadastro_upload_foto', peca_id=peca.id) }}">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <input type="file" name="foto" accept="image/*" class="form-control form-control-sm mb-2" required>
        <button type="submit" class="btn btn-sm btn-outline-primary w-100">
          <i class="fas fa-upload"></i> {{ 'Trocar' if foto_url else 'Enviar' }} foto
        </button>
      </form>
      {% endif %}
    </div>
  </div>
  <div class="col-md-8">
    <div class="card p-3 mb-3">
      <dl class="row mb-0">
        <dt class="col-sm-4">Descrição</dt>
        <dd class="col-sm-8">{{ peca.descricao }}</dd>
        <dt class="col-sm-4">NCM</dt>
        <dd class="col-sm-8">{{ peca.ncm or '—' }}</dd>
        <dt class="col-sm-4">CFOP padrão</dt>
        <dd class="col-sm-8"><span class="badge bg-light text-dark">{{ peca.cfop_default }}</span></dd>
        <dt class="col-sm-4">Unidade</dt>
        <dd class="col-sm-8">{{ peca.unidade }}</dd>
        <dt class="col-sm-4">Preço de venda padrão</dt>
        <dd class="col-sm-8"><strong>{{ peca.preco_venda_padrao|valor_br }}</strong></dd>
        <dt class="col-sm-4">Criada em</dt>
        <dd class="col-sm-8">{{ peca.criado_em.strftime('%d/%m/%Y %H:%M') }}</dd>
      </dl>
    </div>

    <div class="card p-3 mb-3">
      <h5><i class="fas fa-link"></i> Mapeamento TagPlus</h5>
      {% if tagplus_map %}
      <dl class="row mb-0">
        <dt class="col-sm-4">ID TagPlus</dt>
        <dd class="col-sm-8"><code>{{ tagplus_map.tagplus_produto_id }}</code></dd>
        <dt class="col-sm-4">Código DANFE</dt>
        <dd class="col-sm-8">{% if tagplus_map.tagplus_codigo %}<code>{{ tagplus_map.tagplus_codigo }}</code>{% else %}<span class="text-muted">—</span>{% endif %}</dd>
        <dt class="col-sm-4">CFOP override</dt>
        <dd class="col-sm-8">{% if tagplus_map.cfop_default %}<span class="badge bg-light text-dark">{{ tagplus_map.cfop_default }}</span>{% else %}<span class="text-muted">— (usa o cadastro)</span>{% endif %}</dd>
      </dl>
      {% else %}
      <p class="text-warning mb-0"><i class="fas fa-exclamation-triangle"></i> Sem mapeamento TagPlus — peça não pode ser faturada via TagPlus enquanto não for mapeada.</p>
      {% endif %}
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] Adicionar autocomplete de peças em `autocomplete.py` e `autocomplete_service.py`. Editar `app/hora/services/autocomplete_service.py` adicionando função `pecas(q, limit)` e `app/hora/routes/autocomplete.py` adicionando endpoint que chama essa função e responde JSON. Padrão idêntico ao de `chassis()` e `modelos()`.

- [ ] Smoke test:
```bash
python -c "from app import create_app; app=create_app(); print([r for r in app.url_map.iter_rules() if 'pecas/cadastro' in str(r)])"
```

- [ ] Commit:
```bash
git add app/templates/hora/pecas_cadastro_*.html app/hora/services/autocomplete_service.py app/hora/routes/autocomplete.py
git commit -m "feat(hora): templates + autocomplete cadastro de peças"
```

---

## Task 5: Estoque de Peças — UI (P6)

**Files:**
- Create: `app/hora/routes/pecas_estoque.py`
- Create: `app/templates/hora/pecas_estoque_lista.html`
- Create: `app/templates/hora/pecas_estoque_detalhe.html`
- Create: `app/templates/hora/pecas_estoque_ajuste_modal.html`
- Create: `app/templates/hora/pecas_estoque_transferencia_modal.html`
- Modify: `app/hora/routes/__init__.py`

### Step 5.1: Criar routes pecas_estoque

- [ ] Criar `app/hora/routes/pecas_estoque.py`:

```python
"""Rotas de Estoque de Peças (movimentação)."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation

from flask import flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user

from app.hora.decorators import require_hora_perm
from app.hora.models import HoraLoja, HoraPeca
from app.hora.routes import hora_bp
from app.hora.services import peca_estoque_service, peca_service
from app.hora.services.auth_helper import (
    lojas_permitidas_ids,
    usuario_tem_acesso_a_loja,
)


def _operador() -> str:
    if hasattr(current_user, 'nome'):
        return current_user.nome
    return getattr(current_user, 'email', 'desconhecido')


@hora_bp.route('/pecas/estoque')
@require_hora_perm('pecas_estoque', 'ver')
def pecas_estoque_lista():
    permitidas = lojas_permitidas_ids()
    loja_id_str = (request.args.get('loja_id') or '').strip()
    loja_id = int(loja_id_str) if loja_id_str.isdigit() else None
    busca = (request.args.get('busca') or '').strip() or None
    somente_pos = request.args.get('somente_positivo') != '0'

    if loja_id and not usuario_tem_acesso_a_loja(loja_id):
        flash('Acesso negado a essa loja.', 'danger')
        return redirect(url_for('hora.pecas_estoque_lista'))

    rows = peca_estoque_service.listar_estoque(
        loja_id=loja_id, busca=busca,
        somente_positivo=somente_pos,
        lojas_permitidas_ids=permitidas,
    )

    lojas_q = HoraLoja.query.filter_by(ativa=True)
    if permitidas is not None:
        lojas_q = lojas_q.filter(HoraLoja.id.in_(permitidas))
    lojas_ativas = lojas_q.order_by(HoraLoja.nome).all()

    return render_template(
        'hora/pecas_estoque_lista.html',
        rows=rows,
        lojas_ativas=lojas_ativas,
        filtro_loja_id=loja_id,
        filtro_busca=busca,
        filtro_somente_positivo=somente_pos,
    )


@hora_bp.route('/pecas/estoque/<int:peca_id>/<int:loja_id>')
@require_hora_perm('pecas_estoque', 'ver')
def pecas_estoque_detalhe(peca_id: int, loja_id: int):
    p = HoraPeca.query.get_or_404(peca_id)
    l = HoraLoja.query.get_or_404(loja_id)
    if not usuario_tem_acesso_a_loja(loja_id):
        flash('Acesso negado a essa loja.', 'danger')
        return redirect(url_for('hora.pecas_estoque_lista'))

    saldo = peca_estoque_service.saldo(peca_id, loja_id)
    movimentos = peca_estoque_service.historico(peca_id, loja_id, limit=200)
    return render_template(
        'hora/pecas_estoque_detalhe.html',
        peca=p, loja=l, saldo=saldo, movimentos=movimentos,
        foto_url=peca_service.get_foto_url(p),
    )


@hora_bp.route('/pecas/estoque/ajuste', methods=['POST'])
@require_hora_perm('pecas_estoque', 'editar')
def pecas_estoque_ajuste():
    try:
        peca_id = int(request.form.get('peca_id'))
        loja_id = int(request.form.get('loja_id'))
        qtd = Decimal((request.form.get('qtd_signed') or '0').replace(',', '.'))
        motivo = (request.form.get('motivo') or '').strip()
        if not usuario_tem_acesso_a_loja(loja_id):
            flash('Acesso negado a essa loja.', 'danger')
            return redirect(url_for('hora.pecas_estoque_lista'))
        peca_estoque_service.ajuste_manual(
            peca_id=peca_id, loja_id=loja_id,
            qtd_signed=qtd, motivo=motivo, operador=_operador(),
        )
        flash('Ajuste registrado.', 'success')
    except (ValueError, InvalidOperation, TypeError) as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(request.referrer or url_for('hora.pecas_estoque_lista'))


@hora_bp.route('/pecas/estoque/transferencia', methods=['POST'])
@require_hora_perm('pecas_estoque', 'editar')
def pecas_estoque_transferencia():
    try:
        peca_id = int(request.form.get('peca_id'))
        origem = int(request.form.get('loja_origem_id'))
        destino = int(request.form.get('loja_destino_id'))
        qtd = Decimal((request.form.get('qtd') or '0').replace(',', '.'))
        motivo = (request.form.get('motivo') or '').strip()
        if not usuario_tem_acesso_a_loja(origem):
            flash('Acesso negado à loja origem.', 'danger')
            return redirect(url_for('hora.pecas_estoque_lista'))
        peca_estoque_service.transferencia(
            peca_id=peca_id, loja_origem_id=origem, loja_destino_id=destino,
            qtd=qtd, motivo=motivo, operador=_operador(),
        )
        flash(f'Transferência de {qtd} peças realizada.', 'success')
    except (ValueError, InvalidOperation, TypeError) as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(request.referrer or url_for('hora.pecas_estoque_lista'))


@hora_bp.route('/pecas/estoque/saldo/<int:peca_id>')
@require_hora_perm('pecas_estoque', 'ver')
def pecas_estoque_saldo_json(peca_id: int):
    """JSON com saldo por loja (para autocomplete em wizard de venda)."""
    saldos = peca_estoque_service.saldos_por_loja(peca_id)
    return jsonify({str(k): str(v) for k, v in saldos.items()})
```

- [ ] Registrar em `app/hora/routes/__init__.py`: adicionar `pecas_estoque` na lista de imports.

- [ ] Smoke test + commit:
```bash
python -c "from app import create_app; create_app()"
git add app/hora/routes/pecas_estoque.py app/hora/routes/__init__.py
git commit -m "feat(hora): rotas de estoque de peças"
```

### Step 5.2: Templates de estoque

- [ ] Criar `app/templates/hora/pecas_estoque_lista.html`:

```jinja
{% extends "hora/base.html" %}
{% from "hora/_filtros.html" import filtros_form, filtro_loja %}

{% block hora_content %}
<div class="d-flex align-items-center justify-content-between mb-3 flex-wrap gap-2">
  <h2><i class="fas fa-warehouse"></i> Estoque de Peças</h2>
  <div class="d-flex gap-2">
    {% if current_user.tem_perm_hora('pecas_estoque', 'editar') %}
    <button type="button" class="btn btn-outline-primary" data-bs-toggle="modal" data-bs-target="#modalAjuste">
      <i class="fas fa-edit"></i> Ajuste manual
    </button>
    <button type="button" class="btn btn-outline-primary" data-bs-toggle="modal" data-bs-target="#modalTransf">
      <i class="fas fa-exchange-alt"></i> Transferência
    </button>
    {% endif %}
  </div>
</div>

{% call filtros_form(url_for('hora.pecas_estoque_lista')) %}
  {{ filtro_loja(name='loja_id', valor=filtro_loja_id, lojas=lojas_ativas) }}
  <div class="col-md-4">
    <label class="form-label small mb-1">Busca peça</label>
    <input type="text" name="busca" value="{{ filtro_busca or '' }}"
           class="form-control form-control-sm" placeholder="Código ou descrição">
  </div>
  <div class="col-md-3">
    <label class="form-label small mb-1">Estoque</label>
    <div class="form-check form-check-inline mt-1">
      <input class="form-check-input" type="checkbox" name="somente_positivo" value="1"
             id="chkPos" {% if filtro_somente_positivo %}checked{% endif %}>
      <label class="form-check-label" for="chkPos">Apenas com saldo > 0</label>
    </div>
  </div>
  <div class="col-md-auto d-flex gap-2 align-items-end">
    <button type="submit" class="btn btn-sm btn-primary"><i class="fas fa-filter"></i> Filtrar</button>
    <a href="{{ url_for('hora.pecas_estoque_lista') }}" class="btn btn-sm btn-outline-secondary">
      <i class="fas fa-eraser"></i> Limpar
    </a>
  </div>
{% endcall %}

<div class="table-responsive">
  <table class="table table-hover align-middle">
    <thead><tr>
      <th>Código</th><th>Peça</th><th>Loja</th><th class="text-end">Saldo</th><th>Un.</th>
      <th class="text-end">Ações</th>
    </tr></thead>
    <tbody>
      {% for r in rows %}
      <tr>
        <td><code>{{ r.codigo_interno }}</code></td>
        <td>{{ r.descricao }}</td>
        <td>{{ r.loja_nome }}</td>
        <td class="text-end"><strong>{{ r.saldo|numero_br(3) }}</strong></td>
        <td>{{ r.unidade }}</td>
        <td class="text-end">
          <a href="{{ url_for('hora.pecas_estoque_detalhe', peca_id=r.peca_id, loja_id=r.loja_id) }}"
             class="btn btn-sm btn-outline-primary"><i class="fas fa-eye"></i> Detalhe</a>
        </td>
      </tr>
      {% else %}
        <tr><td colspan="6" class="text-center text-muted">Nenhum saldo encontrado.</td></tr>
      {% endfor %}
    </tbody>
  </table>
</div>

{% include 'hora/pecas_estoque_ajuste_modal.html' %}
{% include 'hora/pecas_estoque_transferencia_modal.html' %}
{% endblock %}
```

- [ ] Criar `app/templates/hora/pecas_estoque_detalhe.html`:

```jinja
{% extends "hora/base.html" %}
{% block hora_content %}
<div class="d-flex justify-content-between align-items-start mb-3">
  <h2>
    <i class="fas fa-warehouse"></i> {{ peca.codigo_interno }} <small class="text-muted">@ {{ loja.rotulo_display }}</small>
  </h2>
  <a href="{{ url_for('hora.pecas_estoque_lista') }}" class="btn btn-sm btn-outline-secondary">← Voltar</a>
</div>

<div class="row">
  <div class="col-md-4">
    <div class="card p-3 mb-3 text-center">
      {% if foto_url %}<img src="{{ foto_url }}" class="img-fluid rounded mb-2" style="max-height:200px;">{% endif %}
      <h5 class="mb-0">{{ peca.descricao }}</h5>
      <p class="display-6 my-3">{{ saldo|numero_br(3) }} <small class="text-muted">{{ peca.unidade }}</small></p>
    </div>
  </div>
  <div class="col-md-8">
    <h5>Histórico de movimentos</h5>
    <div class="card mb-3">
      <div class="table-responsive">
        <table class="table table-sm mb-0">
          <thead class="table-light">
            <tr><th>Quando</th><th>Tipo</th><th class="text-end">Qtd</th><th>Motivo / Ref</th><th>Operador</th></tr>
          </thead>
          <tbody>
            {% for m in movimentos %}
            <tr>
              <td><small>{{ m.criado_em.strftime('%d/%m/%Y %H:%M') }}</small></td>
              <td><span class="badge bg-{% if m.qtd > 0 %}success{% else %}warning text-dark{% endif %}">{{ m.tipo }}</span></td>
              <td class="text-end {% if m.qtd > 0 %}text-success{% else %}text-danger{% endif %}">
                <strong>{% if m.qtd > 0 %}+{% endif %}{{ m.qtd|numero_br(3) }}</strong>
              </td>
              <td>
                {% if m.ref_tabela %}<code class="small">{{ m.ref_tabela }}#{{ m.ref_id }}</code><br>{% endif %}
                <small>{{ m.motivo or '' }}</small>
              </td>
              <td><small>{{ m.operador or '—' }}</small></td>
            </tr>
            {% else %}
              <tr><td colspan="5" class="text-center text-muted">Sem movimentos.</td></tr>
            {% endfor %}
          </tbody>
        </table>
      </div>
    </div>
  </div>
</div>
{% endblock %}
```

- [ ] Criar `app/templates/hora/pecas_estoque_ajuste_modal.html` e `pecas_estoque_transferencia_modal.html` — modais Bootstrap padrão com form POST + csrf_token + autocomplete de peça via `data-hora-autocomplete="peca"`.

- [ ] Commit:
```bash
git add app/templates/hora/pecas_estoque*.html
git commit -m "feat(hora): templates estoque de peças (lista + detalhe + modais)"
```

---

## Task 6: Pedido de Compra com peças (P7)

**Files:**
- Modify: `app/hora/services/pedido_service.py` — funções `adicionar_item_peca_pedido`, `remover_item_peca_pedido`
- Modify: `app/hora/routes/pedidos.py` — endpoints AJAX
- Modify: `app/templates/hora/pedido_detalhe.html` — seção "Peças"
- Create: `tests/hora/test_pedido_compra_pecas.py`

### Step 6.1: Test pedido com peças

- [ ] Criar `tests/hora/test_pedido_compra_pecas.py` com testes:
  - `test_adicionar_item_peca_xor_moto` — não pode ter `numero_chassi` E `peca_id`
  - `test_qtd_pedida_obrigatoria_se_peca`
  - `test_remover_item_peca_pedido`
  - `test_listar_itens_inclui_motos_e_pecas`

(Estrutura igual aos testes anteriores: arrange/act/assert; verificar erro com `pytest.raises`.)

### Step 6.2: Implementar pedido_service para peças

- [ ] Em `app/hora/services/pedido_service.py` adicionar:

```python
def adicionar_item_peca_pedido(
    pedido_id: int,
    peca_id: int,
    qtd_pedida,
    preco_compra_esperado,
    operador: Optional[str] = None,
) -> 'HoraPedidoItem':
    """Adiciona item peca em pedido. CHECK XOR moto/peca aplicado pelo banco."""
    from decimal import Decimal
    from app.hora.models import HoraPedido, HoraPedidoItem, HoraPeca

    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        raise ValueError(f'pedido {pedido_id} nao encontrado')
    if pedido.status not in ('ABERTO',):
        raise ValueError(f'pedido em status {pedido.status} nao aceita novos itens')
    if not HoraPeca.query.get(peca_id):
        raise ValueError(f'peca {peca_id} nao existe')
    qtd = Decimal(str(qtd_pedida or 0))
    if qtd <= 0:
        raise ValueError('qtd_pedida deve ser positiva')
    preco = Decimal(str(preco_compra_esperado or 0))
    if preco <= 0:
        raise ValueError('preco_compra_esperado deve ser positivo')

    item = HoraPedidoItem(
        pedido_id=pedido.id,
        peca_id=peca_id, qtd_pedida=qtd,
        preco_compra_esperado=preco,
        # numero_chassi e modelo_id ficam NULL (CHECK XOR satisfeito)
    )
    db.session.add(item)
    db.session.commit()
    return item


def remover_item_peca_pedido(item_id: int, operador: Optional[str] = None) -> None:
    from app.hora.models import HoraPedidoItem
    item = HoraPedidoItem.query.get(item_id)
    if not item:
        raise ValueError(f'item {item_id} nao existe')
    if item.peca_id is None:
        raise ValueError(f'item {item_id} nao e de peça')
    db.session.delete(item)
    db.session.commit()
```

### Step 6.3: Routes AJAX

- [ ] Em `app/hora/routes/pedidos.py` adicionar endpoints `pedido_adicionar_item_peca`, `pedido_remover_item_peca` (POST, retornam JSON com novo HTML da seção ou redirect).

### Step 6.4: Template — seção Peças em pedido_detalhe.html

- [ ] Editar `pedido_detalhe.html` adicionando após a tabela de itens-moto:

```jinja
<h5 class="mt-4"><i class="fas fa-cogs"></i> Itens — Peças ({{ pedido.itens|selectattr('peca_id')|list|length }})</h5>
<div class="card mb-3">
  <div class="table-responsive">
    <table class="table table-sm mb-0">
      <thead class="table-light">
        <tr><th>Código</th><th>Descrição</th><th class="text-end">Qtd</th><th class="text-end">Preço esperado</th><th class="text-end">Total</th><th></th></tr>
      </thead>
      <tbody>
        {% for it in pedido.itens %}
          {% if it.peca_id %}
          <tr>
            <td><code>{{ it.peca.codigo_interno }}</code></td>
            <td>{{ it.peca.descricao }}</td>
            <td class="text-end">{{ it.qtd_pedida|numero_br(3) }}</td>
            <td class="text-end">{{ it.preco_compra_esperado|valor_br }}</td>
            <td class="text-end">{{ (it.qtd_pedida * it.preco_compra_esperado)|valor_br }}</td>
            <td class="text-end">
              {% if pedido.status == 'ABERTO' and current_user.tem_perm_hora('pedidos', 'editar') %}
              <form method="post" action="{{ url_for('hora.pedido_remover_item_peca', pedido_id=pedido.id, item_id=it.id) }}"
                    class="d-inline" onsubmit="return confirm('Remover {{ it.peca.codigo_interno }}?');">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <button class="btn btn-sm btn-outline-danger"><i class="fas fa-trash"></i></button>
              </form>
              {% endif %}
            </td>
          </tr>
          {% endif %}
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% if pedido.status == 'ABERTO' and current_user.tem_perm_hora('pedidos', 'editar') %}
  <div class="card-body border-top">
    <form method="post" action="{{ url_for('hora.pedido_adicionar_item_peca', pedido_id=pedido.id) }}"
          class="row g-2 align-items-end">
      <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
      <div class="col-md-4">
        <label class="form-label small mb-0">Peça</label>
        <input type="text" id="add-peca-txt" class="form-control form-control-sm"
               data-hora-autocomplete="peca" data-hora-target-id="add-peca-id" placeholder="Buscar peça">
        <input type="hidden" name="peca_id" id="add-peca-id" required>
      </div>
      <div class="col-md-2">
        <label class="form-label small mb-0">Qtd</label>
        <input type="text" name="qtd_pedida" class="form-control form-control-sm" inputmode="decimal" required>
      </div>
      <div class="col-md-3">
        <label class="form-label small mb-0">Preço esperado un.</label>
        <input type="text" name="preco_compra_esperado" class="form-control form-control-sm" inputmode="decimal" required>
      </div>
      <div class="col-md-auto">
        <button class="btn btn-sm btn-primary"><i class="fas fa-plus"></i> Adicionar peça</button>
      </div>
    </form>
  </div>
  {% endif %}
</div>
```

- [ ] Rodar testes + commit:
```bash
pytest tests/hora/test_pedido_compra_pecas.py -v
git commit -am "feat(hora): pedido de compra com peças (XOR moto/peça)"
```

---

## Task 7: NF de Entrada com peças (P8)

**Files:**
- Modify: `app/hora/services/nf_entrada_service.py` — parser distingue moto/peça
- Modify: `app/hora/services/recebimento_service.py` — passo conferência peça → emite ENTRADA_NF
- Modify: `app/templates/hora/nf_detalhe.html` — listar `nf.itens_peca`
- Modify: `app/templates/hora/recebimento_wizard.html` — passo de conferência de peça
- Create: `tests/hora/test_nf_entrada_pecas.py`

### Step 7.1: Test parser distingue motos de peças

- [ ] Criar `tests/hora/test_nf_entrada_pecas.py`:
  - `test_parser_item_sem_chassi_vai_para_peca` — item TagPlus com código mapeado em `hora_tagplus_peca_map` cria `HoraNfEntradaItemPeca`
  - `test_parser_item_sem_mapping_registra_divergencia` — sem map em motos nem peças
  - `test_recebimento_conferencia_peca_emite_entrada_nf` — após conferência, saldo de peça aumenta na loja destino

### Step 7.2: Implementar parser distintivo

- [ ] Em `app/hora/services/nf_entrada_service.py`, na função que cria itens da NF (procurar onde `HoraNfEntradaItem` é criado):
  - Antes de criar item, lookup do `tagplus_codigo` em `HoraTagPlusProdutoMap` (moto). Se achar → cria `HoraNfEntradaItem` (fluxo atual)
  - Senão, lookup em `HoraTagPlusPecaMap` (peça). Se achar → cria `HoraNfEntradaItemPeca` com `qtd_nf`, `preco_real`, `modelo_texto_original`
  - Senão → registra divergência `PRODUTO_NAO_MAPEADO` (criar tipo se não existir)

### Step 7.3: Conferência → estoque

- [ ] Em `recebimento_service.py`, quando `HoraRecebimentoConferencia` (motos) é finalizada, adicionar passo paralelo: para cada `HoraNfEntradaItemPeca` da mesma NF, se `qtd_conferida` preenchida e `divergencia_qtd != 'OK'` ou `qtd_conferida > 0`, emitir movimento `ENTRADA_NF` em `peca_estoque_service.registrar_movimento(qtd=qtd_conferida, loja_id=nf.loja_destino_id, ref_tabela='hora_nf_entrada_item_peca', ref_id=item.id)`.

### Step 7.4: Templates

- [ ] Em `nf_detalhe.html` adicionar seção `<h5>Peças</h5>` listando `nf.itens_peca` similar à seção de motos.
- [ ] Em `recebimento_wizard.html` adicionar passo "Conferir peças" com inputs `qtd_conferida` + `divergencia_qtd` (select OK/FALTA/SOBRA/AVARIA) + upload foto opcional.

- [ ] Rodar testes + commit:
```bash
pytest tests/hora/test_nf_entrada_pecas.py -v
git commit -am "feat(hora): NF entrada parser distingue moto/peça + conferência peça"
```

---

## Task 8: Pedido de Venda com peças (P9)

**Files:**
- Modify: `app/hora/services/venda_service.py` — `adicionar_item_peca`, `remover_item_peca`, `editar_item_peca`, integrar em `cancelar_venda` e `criar_venda_manual`
- Modify: `app/hora/routes/vendas.py` — AJAX
- Modify: `app/templates/hora/venda_detalhe.html` — seção Peças
- Create: `tests/hora/test_venda_pecas.py`

### Step 8.1: Test venda com peças

- [ ] Criar `tests/hora/test_venda_pecas.py`:
  - `test_adicionar_peca_em_pedido_cotacao`
  - `test_peca_em_pedido_emite_saida_venda` — cria venda com peça → verifica saldo da loja diminui
  - `test_remover_peca_volta_para_estoque` — remove item peça → emite DEVOLUCAO_VENDA
  - `test_cancelar_venda_devolve_pecas` — cancela venda com peças → todas voltam ao estoque
  - `test_editar_qtd_peca_ajusta_estoque` — edita qtd de 2 para 5 → emite saída adicional de 3

### Step 8.2: Implementar venda_service para peças

- [ ] Em `venda_service.py` adicionar funções:

```python
def adicionar_item_peca(
    venda_id: int,
    peca_id: int,
    qtd,
    valor_unitario_final,
    usuario: Optional[str] = None,
) -> 'HoraVendaItemPeca':
    """Adiciona peça em pedido COTACAO. Emite SAIDA_VENDA na loja do pedido."""
    from decimal import Decimal
    from app.hora.models import HoraVenda, HoraVendaItemPeca, HoraPeca
    from app.hora.services import peca_estoque_service

    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'venda {venda_id} nao encontrada')
    _exigir_cotacao(venda, 'Adicionar peça')

    peca = HoraPeca.query.get(peca_id)
    if not peca:
        raise ValueError(f'peca {peca_id} nao existe')
    qtd_dec = Decimal(str(qtd or 0))
    if qtd_dec <= 0:
        raise ValueError('qtd deve ser positiva')
    valor_uni = Decimal(str(valor_unitario_final or 0))
    if valor_uni <= 0:
        raise ValueError('valor_unitario_final deve ser positivo')

    if not venda.loja_id:
        raise ValueError('venda sem loja_id — defina loja antes de adicionar peças')
    saldo_atual = peca_estoque_service.saldo(peca.id, venda.loja_id)
    if saldo_atual < qtd_dec:
        raise ValueError(
            f'saldo insuficiente: loja tem {saldo_atual} {peca.unidade}, '
            f'pedido exige {qtd_dec}'
        )

    preco_ref = Decimal(str(peca.preco_venda_padrao))
    desconto_uni = max(Decimal('0'), preco_ref - valor_uni)
    preco_final = qtd_dec * valor_uni

    item = HoraVendaItemPeca(
        venda_id=venda.id, peca_id=peca.id, qtd=qtd_dec,
        preco_unitario_referencia=preco_ref,
        desconto_aplicado=desconto_uni,
        preco_final=preco_final,
    )
    db.session.add(item)
    db.session.flush()

    peca_estoque_service.registrar_movimento(
        peca_id=peca.id, loja_id=venda.loja_id,
        tipo='SAIDA_VENDA', qtd=-qtd_dec,
        ref_tabela='hora_venda_item_peca', ref_id=item.id,
        motivo=f'Pedido #{venda.id}', operador=usuario,
    )

    venda.valor_total = Decimal(str(venda.valor_total)) + preco_final
    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='ADICIONOU_ITEM_PECA',
        detalhe=f'peca={peca.codigo_interno} qtd={qtd_dec} total={preco_final}',
    )
    db.session.commit()
    return item


def remover_item_peca(venda_id: int, item_id: int, usuario: Optional[str] = None) -> None:
    from decimal import Decimal
    from app.hora.models import HoraVenda, HoraVendaItemPeca
    from app.hora.services import peca_estoque_service

    venda = HoraVenda.query.get(venda_id)
    if not venda:
        raise ValueError(f'venda {venda_id} nao encontrada')
    _exigir_cotacao(venda, 'Remover peça')

    item = HoraVendaItemPeca.query.get(item_id)
    if not item or item.venda_id != venda.id:
        raise ValueError(f'item {item_id} nao pertence ao pedido')

    peca_estoque_service.registrar_movimento(
        peca_id=item.peca_id, loja_id=venda.loja_id,
        tipo='DEVOLUCAO_VENDA', qtd=Decimal(str(item.qtd)),
        ref_tabela='hora_venda_item_peca', ref_id=item.id,
        motivo=f'Item removido do pedido #{venda.id}', operador=usuario,
    )

    venda.valor_total = Decimal(str(venda.valor_total)) - Decimal(str(item.preco_final))
    venda_audit.registrar_auditoria(
        venda_id=venda.id, usuario=usuario or '',
        acao='REMOVEU_ITEM_PECA',
        detalhe=f'peca={item.peca.codigo_interno} qtd={item.qtd}',
    )
    db.session.delete(item)
    db.session.commit()
```

- [ ] Em `cancelar_venda`: ao iterar itens para emitir DEVOLVIDA, também iterar `venda.itens_peca` e emitir `DEVOLUCAO_VENDA` para cada.

### Step 8.3: Routes + template venda_detalhe

- [ ] Em `vendas.py` adicionar `venda_adicionar_item_peca` e `venda_remover_item_peca` (POST forms).
- [ ] Em `venda_detalhe.html` adicionar seção "Peças" igual à do pedido_detalhe (form de adicionar com autocomplete + tabela de itens com botão remover) — incluir aviso de saldo (chama `/hora/pecas/estoque/saldo/<peca_id>` via JS).

- [ ] Rodar testes + commit:
```bash
pytest tests/hora/test_venda_pecas.py -v
git commit -am "feat(hora): pedido de venda com peças (estoque integrado)"
```

---

## Task 9: TagPlus payload misto (P10)

**Files:**
- Modify: `app/hora/services/tagplus/payload_builder.py` — `_montar_itens` concatena motos + peças, CFOP por item
- Create: `tests/hora/test_tagplus_payload_misto.py`

### Step 9.1: Test payload misto

- [ ] Criar `tests/hora/test_tagplus_payload_misto.py`:
  - `test_payload_so_motos_inalterado` — venda só com motos produz payload igual ao atual
  - `test_payload_so_pecas` — venda só com peças produz `itens[]` com `qtd: N`, sem `detalhes` chassi
  - `test_payload_misto` — venda com 1 moto + 2 peças produz `itens[]` com 3 entradas
  - `test_peca_sem_map_levanta_erro` — peça sem `HoraTagPlusPecaMap` → `PayloadBuilderError('peca_nao_mapeada')`
  - `test_cfop_por_item` — peça com cfop_default=5.102 e moto com 5.403 → CFOP root = 5.403 (primeiro item) mas cada item tem `cfop` próprio

### Step 9.2: Implementar payload misto

- [ ] Em `payload_builder.py:_montar_itens`:

```python
def _montar_itens(self, venda: 'HoraVenda') -> list[dict]:
    itens = []
    # 1. Itens MOTO (fluxo atual mantido)
    for vi in venda.itens:
        modelo_id = vi.moto.modelo_id if vi.moto else None
        if modelo_id is None:
            raise PayloadBuilderError(
                'item_sem_modelo',
                f'Item {vi.id} sem moto/modelo associado.',
            )
        map_ = HoraTagPlusProdutoMap.query.filter_by(modelo_id=modelo_id).first()
        if not map_:
            raise PayloadBuilderError(
                'produto_nao_mapeado',
                f'Modelo {modelo_id} sem mapeamento TagPlus.',
            )
        chassi = vi.numero_chassi or '-'
        motor = (vi.moto.numero_motor if vi.moto else None) or '-'
        itens.append({
            'produto_servico': str(map_.tagplus_produto_id),
            'qtd': 1,
            'valor_unitario': self._round2_float(vi.preco_tabela_referencia),
            'valor_acrescimo': 0,
            'valor_desconto': self._round2_float(vi.desconto_aplicado or Decimal('0')),
            'detalhes': f'Chassi: {chassi} / Motor: {motor}',
            'cfop': map_.cfop_default or '5.403',
        })

    # 2. Itens PEÇA (novo)
    from app.hora.models import HoraTagPlusPecaMap
    for vp in venda.itens_peca:
        peca_map = HoraTagPlusPecaMap.query.filter_by(peca_id=vp.peca_id).first()
        if not peca_map:
            raise PayloadBuilderError(
                'peca_nao_mapeada',
                f'Peça {vp.peca.codigo_interno} (id={vp.peca_id}) sem mapeamento TagPlus. '
                f'Configurar em /hora/pecas/cadastro/{vp.peca_id}/editar.',
            )
        cfop_peca = peca_map.cfop_default or vp.peca.cfop_default
        itens.append({
            'produto_servico': str(peca_map.tagplus_produto_id),
            'qtd': float(vp.qtd),
            'valor_unitario': self._round2_float(
                Decimal(str(vp.preco_unitario_referencia))
            ),
            'valor_acrescimo': 0,
            'valor_desconto': self._round2_float(
                Decimal(str(vp.desconto_aplicado or 0))
            ),
            'cfop': cfop_peca,
        })

    if not itens:
        raise PayloadBuilderError('venda_sem_itens', 'Venda sem itens.')
    return itens
```

- [ ] Em `build()`:
  - Atualizar `valor_desconto` e `valor_nota` para somar peças também
  - `cfop` root continua usando primeiro item (compatibilidade)
  - `if not venda.itens` → trocar por `if not venda.itens and not venda.itens_peca`

- [ ] Rodar testes + commit:
```bash
pytest tests/hora/test_tagplus_payload_misto.py -v
git commit -am "feat(hora): TagPlus payload com motos + peças (CFOP por item)"
```

---

## Task 10: TagPlus backfill (proteção chassi + 2 backfills) (P11)

**Files:**
- Modify: `app/hora/services/tagplus/backfill_service.py` — proteção chassi + classificador peça/moto + 2 backfills
- Modify: `app/hora/routes/tagplus_routes.py` — rotas `tagplus_peca_map_lista`, `tagplus_backfill_produtos`, `tagplus_backfill_pecas_delta`
- Create: `app/templates/hora/tagplus_peca_map_lista.html`
- Create: `app/templates/hora/tagplus_backfill_produtos.html`
- Create: `app/templates/hora/tagplus_backfill_pecas_delta.html`
- Create: `tests/hora/test_tagplus_backfill_protecao.py`
- Create: `tests/hora/test_tagplus_backfill_delta.py`

### Step 10.1: Tests proteção e delta

- [ ] Criar `tests/hora/test_tagplus_backfill_protecao.py`:
  - `test_chassi_protegido_parser_divergente_nao_atualiza` — moto criada por NF entrada com modelo X. Backfill recebe chassi com modelo Y → não atualiza, registra divergência
  - `test_chassi_nao_existe_registra_divergencia` — chassi novo extraído de NFe venda → não cria HoraMoto, registra divergência

- [ ] Criar `tests/hora/test_tagplus_backfill_delta.py`:
  - `test_backfill_delta_sem_diferenca_nao_processa`
  - `test_backfill_delta_processa_venda_com_diferenca` — venda valor_total=1000, items moto=800 → delta=200 reprocessa, cria item peça

### Step 10.2: Implementar proteção chassi

- [ ] Em `backfill_service.py`, nas funções `_atualizar_moto_complementar` e `_atualizar_campos_vazios`:

```python
from app.hora.services.chassi_protecao_service import chassi_protegido

# No INICIO da função:
if chassi_protegido(moto.numero_chassi):
    novo_modelo = ...  # campo extraído pelo parser
    if novo_modelo and novo_modelo != moto.modelo_id:
        # Registra divergência e SKIP
        _registrar_divergencia_protecao(venda_id, moto.numero_chassi,
            valor_esperado=f'modelo={moto.modelo_id} cor={moto.cor}',
            valor_conferido=f'parser sugeriu modelo={novo_modelo}',
        )
        return
```

- [ ] Adicionar tipo `CHASSI_PROTEGIDO_PARSER_DIVERGENTE` em `HoraVendaDivergencia` (apenas constante string, modelo já aceita qualquer tipo).

- [ ] **NÃO** criar `HoraMoto` ad-hoc no fluxo de NFe de venda. Verificar `_resolver_modelo_id` e remover criação. Se chassi não existe → registrar divergência `CHASSI_NAO_CADASTRADO` (já existe).

### Step 10.3: Backfill produtos

- [ ] Em `backfill_service.py` adicionar:

```python
def executar_backfill_produtos_pecas(
    operador: Optional[str] = None,
    apenas_preview: bool = False,
) -> dict:
    """Itera GET /produtos do TagPlus e popula hora_peca + hora_tagplus_peca_map.

    Heurística: produtos com NCM iniciando em '8711' (motos elétricas) NAO entram
    como peça (sao motos). Operador valida na tela antes de confirmar.
    """
    from app.hora.models import HoraPeca, HoraTagPlusPecaMap, HoraTagPlusConta
    conta = HoraTagPlusConta.ativa()
    api = ApiClient(conta)
    page = 1
    relatorio = {'criadas': 0, 'atualizadas': 0, 'puladas_moto': 0, 'erros': 0}
    while True:
        r = api.get('/produtos', params={'per_page': 100, 'page': page})
        if r.status_code != 200:
            relatorio['erros'] += 1
            break
        data = r.json() or []
        if isinstance(data, dict):
            data = data.get('data') or data.get('produtos') or []
        if not data:
            break
        for prod in data:
            ncm = (prod.get('ncm') or '').strip()
            if ncm.startswith('8711'):
                relatorio['puladas_moto'] += 1
                continue
            codigo = (prod.get('codigo') or '').strip()
            descricao = (prod.get('descricao') or prod.get('nome') or '').strip()
            tagplus_id = str(prod.get('id') or '')
            if not codigo or not tagplus_id:
                continue
            if apenas_preview:
                continue
            existing = HoraPeca.query.filter_by(codigo_interno=codigo).first()
            if existing:
                relatorio['atualizadas'] += 1
                p = existing
            else:
                p = HoraPeca(
                    codigo_interno=codigo,
                    descricao=descricao or codigo,
                    ncm=ncm or None,
                    cfop_default='5.102',
                    unidade=(prod.get('unidade') or 'UN'),
                )
                db.session.add(p)
                db.session.flush()
                relatorio['criadas'] += 1
            m = HoraTagPlusPecaMap.query.filter_by(peca_id=p.id).first()
            if not m:
                m = HoraTagPlusPecaMap(peca_id=p.id, tagplus_produto_id=tagplus_id)
                db.session.add(m)
            m.tagplus_codigo = codigo
        db.session.commit()
        page += 1
        if len(data) < 100:
            break
    return relatorio
```

### Step 10.4: Backfill delta

- [ ] Em `backfill_service.py` adicionar:

```python
def executar_backfill_pecas_faltantes(operador: Optional[str] = None) -> dict:
    """Reprocessa NFes com delta valor_total - sum(itens) > 0 para classificar peças."""
    from sqlalchemy import func
    from app.hora.models import (
        HoraVenda, HoraVendaItem, HoraVendaItemPeca, HoraTagPlusNfeEmissao,
    )
    sub_motos = (
        db.session.query(
            HoraVendaItem.venda_id,
            func.sum(HoraVendaItem.preco_final).label('soma_motos'),
        ).group_by(HoraVendaItem.venda_id).subquery()
    )
    sub_pecas = (
        db.session.query(
            HoraVendaItemPeca.venda_id,
            func.sum(HoraVendaItemPeca.preco_final).label('soma_pecas'),
        ).group_by(HoraVendaItemPeca.venda_id).subquery()
    )
    rows = db.session.query(
        HoraVenda, sub_motos.c.soma_motos, sub_pecas.c.soma_pecas,
    ).outerjoin(sub_motos, sub_motos.c.venda_id == HoraVenda.id) \
     .outerjoin(sub_pecas, sub_pecas.c.venda_id == HoraVenda.id).all()

    relatorio = {'reprocessadas': 0, 'pecas_criadas': 0, 'erros': 0}
    for venda, sm, sp in rows:
        soma = (Decimal(str(sm or 0)) + Decimal(str(sp or 0)))
        delta = Decimal(str(venda.valor_total)) - soma
        if abs(delta) <= Decimal('0.01'):
            continue
        emissao = HoraTagPlusNfeEmissao.query.filter_by(venda_id=venda.id).first()
        if not emissao or not emissao.tagplus_nfe_id:
            continue
        try:
            # GET /nfes/{id} e re-classifica itens
            relatorio['reprocessadas'] += 1
            # ... (chamar _reprocessar_venda_para_pecas)
        except Exception:
            relatorio['erros'] += 1
    return relatorio
```

### Step 10.5: Rotas + templates

- [ ] Em `tagplus_routes.py` adicionar:
```
tagplus_peca_map_lista (GET) + tagplus_peca_map_salvar (POST)
tagplus_backfill_produtos (GET form + POST executar)
tagplus_backfill_pecas_delta (GET form + POST executar)
```

- [ ] Templates correspondentes seguindo padrão de `tagplus_produto_map` existentes (lista editável + form de execução com confirmação).

- [ ] Rodar testes + commit:
```bash
pytest tests/hora/test_tagplus_backfill_*.py -v
git commit -am "feat(hora): TagPlus backfill — proteção chassi + produtos + delta"
```

---

## Task 11: Menu wiring + smoke tests + CLAUDE.md (P12)

**Files:**
- Modify: `app/templates/hora/base.html` — adicionar 5 entradas de menu
- Modify: `app/hora/CLAUDE.md` — seção 11 Peças
- Create: `tests/hora/test_smoke_pecas.py`

### Step 11.1: Menu base.html

- [ ] Editar `app/templates/hora/base.html`:

**Cadastros** — adicionar APÓS "Modelos":
```jinja
{% if current_user.tem_perm_hora('pecas_cadastro', 'ver') %}
  <li><a class="dropdown-item" href="{{ url_for('hora.pecas_cadastro_lista') }}">
    <i class="fas fa-cogs fa-fw"></i> Peças
  </a></li>
{% endif %}
```
Atualizar `set show_cadastros` adicionando `current_user.tem_perm_hora('pecas_cadastro', 'ver')`.

**Movimentação** — adicionar APÓS "Estoque":
```jinja
{% if current_user.tem_perm_hora('pecas_estoque', 'ver') %}
  <li><a class="dropdown-item" href="{{ url_for('hora.pecas_estoque_lista') }}">
    <i class="fas fa-warehouse fa-fw"></i> Estoque de Peças
  </a></li>
{% endif %}
```
Atualizar `set show_mov`.

**Faturamento** — adicionar APÓS "Mapeamento de produtos":
```jinja
<li><a class="dropdown-item" href="{{ url_for('hora.tagplus_peca_map_lista') }}">
  <i class="fas fa-link fa-fw"></i> Mapeamento de peças
</a></li>
<li><a class="dropdown-item" href="{{ url_for('hora.tagplus_backfill_produtos') }}">
  <i class="fas fa-cloud-download-alt fa-fw"></i> Backfill catálogo TagPlus (peças)
</a></li>
<li><a class="dropdown-item" href="{{ url_for('hora.tagplus_backfill_pecas_delta') }}">
  <i class="fas fa-magic fa-fw"></i> Backfill peças faltantes (delta)
</a></li>
```

### Step 11.2: Smoke test geral

- [ ] Criar `tests/hora/test_smoke_pecas.py`:

```python
"""Smoke test: todas as rotas de peças renderizam sem 500 e estão registradas."""
import pytest


@pytest.mark.parametrize('endpoint', [
    'hora.pecas_cadastro_lista',
    'hora.pecas_cadastro_novo',
    'hora.pecas_estoque_lista',
    'hora.tagplus_peca_map_lista',
    'hora.tagplus_backfill_produtos',
    'hora.tagplus_backfill_pecas_delta',
])
def test_endpoint_registrado(app, endpoint):
    with app.app_context():
        from flask import url_for
        url = url_for(endpoint)
        assert url.startswith('/hora/')


def test_menu_renderiza(app, client_admin):
    """base.html não levanta UndefinedError com novos itens."""
    r = client_admin.get('/hora/dashboard')
    assert r.status_code == 200
    body = r.get_data(as_text=True)
    assert 'Peças' in body
    assert 'Estoque de Peças' in body
```

- [ ] Rodar:
```bash
pytest tests/hora/test_smoke_pecas.py -v
```

### Step 11.3: Atualizar CLAUDE.md

- [ ] Adicionar em `app/hora/CLAUDE.md` antes da seção "Referências":

```markdown
## 11. Peças (cadastro, estoque, faturamento) — 2026-05-05

Peças (capacete, retrovisor, bateria) são produtos fungíveis sem chassi, paralelos a motos no ciclo HORA.

**Tabelas novas (5)**:
- `hora_peca` — cadastro (codigo_interno, descricao, ncm, cfop_default, unidade, preco_venda_padrao, foto, ativo)
- `hora_tagplus_peca_map` — mapeamento opcional para emissão TagPlus (peça pode existir sem TagPlus)
- `hora_peca_movimento` — log de entradas/saídas signed; saldo derivado por SUM (mesmo padrão moto-evento)
- `hora_nf_entrada_item_peca` — peça em NF entrada com conferência embutida (1:1)
- `hora_venda_item_peca` — peça em pedido de venda

**ALTER `hora_pedido_item`**: adicionado `peca_id`, `qtd_pedida` com CHECK XOR (item é OU moto OU peça).

**Permissões**: `pecas_cadastro` e `pecas_estoque` em `MODULOS_HORA` (separados de `pecas` que é "peças faltando").

**Ciclo de vida**:
1. Pedido compra (HoraPedido) — itens podem ser moto OU peça (`peca_id` + `qtd_pedida`)
2. NF entrada — parser distingue por mapeamento TagPlus: produto_map (moto) vs peca_map (peça). Cria item em tabela correspondente
3. Recebimento — wizard tem passo de conferência de peça (qtd_conferida + foto). Após confirmar, emite movimento `ENTRADA_NF` no estoque
4. Venda — `criar_venda_manual` aceita motos e peças. Item peça emite `SAIDA_VENDA` (saldo - qtd) na criação. Cancelar = `DEVOLUCAO_VENDA`
5. NFe TagPlus — payload misto (motos + peças no mesmo POST). CFOP por item (peca_map.cfop_default override peca.cfop_default)
6. Backfill TagPlus:
   - Catálogo de produtos: `executar_backfill_produtos_pecas` popula `hora_peca` + `hora_tagplus_peca_map` (heurística: NCM 8711* = moto, pula)
   - NFes legadas com delta: `executar_backfill_pecas_faltantes` reprocessa vendas com `valor_total - sum(itens) > 0`

**Proteção de chassi (CRÍTICA)**:
Helper `chassi_protegido()` em `chassi_protecao_service.py` retorna True se chassi tem registro em `HoraPedidoItem` ou `HoraNfEntradaItem`.

Backfill de NFe de venda **NUNCA**:
- altera `HoraMoto.modelo_id`/`cor`/`numero_motor` de chassi protegido (registra divergência `CHASSI_PROTEGIDO_PARSER_DIVERGENTE` e segue)
- cria `HoraMoto` ad-hoc para chassi extraído de NFe de venda (registra `CHASSI_NAO_CADASTRADO` e segue)

Apenas NF de entrada cria `HoraMoto`. NFe de venda só lê.

**Não-objetivos v1**: versionamento de preço de peça, custo médio, devolução parcial, inventário cíclico, multi-emitente.
```

### Step 11.4: Commit final + rodar suite completa

- [ ] Rodar tudo:
```bash
pytest tests/hora/ -v
```

- [ ] Commit final:
```bash
git add app/templates/hora/base.html app/hora/CLAUDE.md tests/hora/test_smoke_pecas.py
git commit -m "feat(hora): menu peças + smoke tests + CLAUDE.md atualizado"
```

---

## Self-Review (rodar após terminar plano)

### Spec coverage
- [x] Tabela `hora_peca` (Task 1.6) ✓
- [x] Tabela `hora_tagplus_peca_map` (Task 1.6) ✓
- [x] Tabela `hora_peca_movimento` (Task 1.6) ✓
- [x] Tabela `hora_nf_entrada_item_peca` (Task 1.6) ✓
- [x] Tabela `hora_venda_item_peca` (Task 1.6) ✓
- [x] ALTER `hora_pedido_item` com CHECK XOR (Task 1.8) ✓
- [x] 3 migrations (Task 1.1-1.4 + 3.2) ✓
- [x] Services: peca, peca_estoque, chassi_protecao (Task 2) ✓
- [x] Permissões pecas_cadastro + pecas_estoque (Task 3) ✓
- [x] UI Cadastro (Task 4) ✓
- [x] UI Estoque (Task 5) ✓
- [x] Pedido Compra com peça (Task 6) ✓
- [x] NF Entrada com peça (Task 7) ✓
- [x] Venda com peça (Task 8) ✓
- [x] TagPlus payload misto (Task 9) ✓
- [x] TagPlus backfill produtos + delta + proteção chassi (Task 10) ✓
- [x] Menu + CLAUDE.md (Task 11) ✓

### Padrão visual
- [x] Macros `_filtros.html` usadas (Tasks 4, 5)
- [x] Forms com `card p-3` (Tasks 4, 5)
- [x] Detalhe com `dl row mb-0` (Task 4)
- [x] Tabelas `table-hover align-middle` (Tasks 4, 5)
- [x] Badges Bootstrap padrão (Tasks 4, 5, 7, 8)
- [x] CSRF em todos os forms POST
- [x] Permissões em torno de cada ação destrutiva

### TDD
- [x] Cada task de service tem testes (Tasks 2, 6, 7, 8, 9, 10)
- [x] Testes escritos ANTES da implementação (Steps X.1 antes de X.2)

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-05-05-hora-pecas.md`.**

Two execution options:

**1. Subagent-Driven (recommended)** — Dispatchamos um subagente fresh por task (Task 1, 2, ..., 11). Reviso entre tasks. Iteração rápida.

**2. Inline Execution** — Executamos tasks nesta sessão usando `superpowers:executing-plans`, batch com checkpoints para review.

**Qual abordagem?**
