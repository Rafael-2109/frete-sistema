# Motos Assaí — Plano 1: Foundation + Cadastros (Implementation Plan)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar a base do módulo `app/motos_assai/`: schema completo (16 tabelas), toggle de acesso `sistema_motos_assai`, blueprint isolado, autenticação integrada, dashboard navegável e CRUD completo de Lojas Assaí, Modelos e CD. Após este plano, o módulo é navegável e os cadastros estão prontos para receber pedidos no Plano 2.

**Architecture:** Módulo standalone Flask seguindo o padrão Hora (prefixo `assai_`, blueprint isolado, toggle master). Reuso de padrões existentes via convenções, sem import direto de modelos de outros módulos. Migrations duais (DDL `.sql` + Python verificador).

**Tech Stack:** Flask 3.x + SQLAlchemy 2.x + Flask-WTF + PostgreSQL 16, padrão de design tokens (light/dark) + Bootstrap 5.

**Spec aprovado:** `docs/superpowers/specs/2026-05-07-motos-assai-design.md`

**Pré-requisitos do dono do produto** (resolvidos em 2026-05-07):
- ~~Máscaras de chassi~~ — regex duráveis confirmados (aplicados na Task 22).
- ~~CNPJ + endereço do CD "Operação VOE"~~ — campos opcionais; CD pode ser cadastrado vazio e preenchido depois via tela admin (Task 25). CNPJ Motochefe também opcional.

**Status**: zero pendências bloqueantes.

---

## Visão de arquivos

```
app/motos_assai/
├── __init__.py                          # Task 1
├── decorators.py                        # Task 12
├── models/
│   ├── __init__.py                      # Task 6
│   ├── cd.py                            # Task 6
│   ├── loja.py                          # Task 6
│   ├── modelo.py                        # Task 7
│   ├── moto.py                          # Task 8
│   ├── pedido.py                        # Task 9
│   ├── compra.py                        # Task 10
│   ├── recibo.py                        # Task 10
│   ├── separacao.py                     # Task 11
│   └── nf_qpa.py                        # Task 11
├── routes/
│   ├── __init__.py                      # Task 13
│   ├── dashboard.py                     # Task 19
│   ├── lojas.py                         # Task 23
│   ├── modelos.py                       # Task 24
│   └── cd.py                            # Task 25
├── services/
│   ├── __init__.py                      # Task 23
│   ├── loja_service.py                  # Task 23
│   ├── modelo_service.py                # Task 24
│   └── cd_service.py                    # Task 25
└── forms/
    ├── __init__.py                      # Task 23
    ├── loja_forms.py                    # Task 23
    ├── modelo_forms.py                  # Task 24
    └── cd_forms.py                      # Task 25

app/templates/motos_assai/
├── base_motos_assai.html                # Task 19
├── dashboard.html                       # Task 19
├── lojas/{lista,form,detalhe}.html      # Task 23
├── modelos/{lista,form,detalhe}.html    # Task 24
└── cd/{detalhe,form}.html               # Task 25

app/static/css/modules/_motos_assai.css  # Task 19

scripts/migrations/
├── motos_assai_01_schema.sql            # Task 5
├── motos_assai_01_schema.py             # Task 5
├── motos_assai_02_toggle_usuario.sql    # Task 2
├── motos_assai_02_toggle_usuario.py     # Task 2
├── motos_assai_03_seed_cd.py            # Task 20
├── motos_assai_04_seed_lojas.py         # Task 21
└── motos_assai_05_seed_modelos.py       # Task 22

tests/motos_assai/
├── __init__.py                          # Task 26
├── conftest.py                          # Task 26
├── test_models.py                       # Task 26
├── test_decorator.py                    # Task 26
├── test_auth_integration.py             # Task 26
└── test_cadastros.py                    # Task 26

# Modificações em arquivos existentes:
# - app/__init__.py (Task 13)
# - app/auth/models.py (Tasks 3, 4)
# - app/auth/forms.py (Task 14)
# - app/auth/routes.py (Task 15)
# - app/auth/utils.py (Task 16)
# - app/templates/auth/editar_usuario.html (Task 17)
# - app/templates/base.html (Task 18)
# - app/static/css/main.css (Task 19, importar _motos_assai.css)
# - app/motos_assai/CLAUDE.md (Task 27)
```

---

## Task 1: Criar estrutura de diretórios

**Files:**
- Create: `app/motos_assai/__init__.py`
- Create: `app/motos_assai/models/__init__.py`
- Create: `app/motos_assai/routes/__init__.py`
- Create: `app/motos_assai/services/__init__.py`
- Create: `app/motos_assai/forms/__init__.py`
- Create: `app/templates/motos_assai/.gitkeep`

- [ ] **Step 1: Criar diretórios e __init__.py vazios**

```bash
mkdir -p app/motos_assai/{models,routes,services,forms}
mkdir -p app/templates/motos_assai
touch app/motos_assai/__init__.py
touch app/motos_assai/models/__init__.py
touch app/motos_assai/routes/__init__.py
touch app/motos_assai/services/__init__.py
touch app/motos_assai/forms/__init__.py
touch app/templates/motos_assai/.gitkeep
```

- [ ] **Step 2: Commit**

```bash
git add app/motos_assai/ app/templates/motos_assai/.gitkeep
git commit -m "feat(motos_assai): scaffold initial directory structure"
```

---

## Task 2: Migration — toggle `sistema_motos_assai` em `usuarios`

**Files:**
- Create: `scripts/migrations/motos_assai_02_toggle_usuario.sql`
- Create: `scripts/migrations/motos_assai_02_toggle_usuario.py`

- [ ] **Step 1: Criar SQL idempotente**

`scripts/migrations/motos_assai_02_toggle_usuario.sql`:

```sql
-- Migration: Toggle sistema_motos_assai em usuarios
-- Idempotente; pode ser executada múltiplas vezes sem efeito colateral.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM information_schema.columns
        WHERE table_name = 'usuarios'
          AND column_name = 'sistema_motos_assai'
    ) THEN
        ALTER TABLE usuarios
        ADD COLUMN sistema_motos_assai BOOLEAN DEFAULT FALSE NOT NULL;
    END IF;
END $$;
```

- [ ] **Step 2: Criar Python com verificação before/after**

`scripts/migrations/motos_assai_02_toggle_usuario.py`:

```python
"""
Migration: Adicionar sistema_motos_assai em usuarios
=====================================================
Executar: python scripts/migrations/motos_assai_02_toggle_usuario.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text, inspect


def adicionar_campo():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        colunas = [c['name'] for c in inspector.get_columns('usuarios')]
        if 'sistema_motos_assai' in colunas:
            print("Campo 'sistema_motos_assai' já existe.")
            return

        print("Adicionando campo sistema_motos_assai...")
        db.session.execute(text("""
            ALTER TABLE usuarios
            ADD COLUMN sistema_motos_assai BOOLEAN DEFAULT FALSE NOT NULL;
        """))
        db.session.commit()

        inspector = inspect(db.engine)
        colunas_depois = [c['name'] for c in inspector.get_columns('usuarios')]
        if 'sistema_motos_assai' in colunas_depois:
            print("OK: campo sistema_motos_assai adicionado.")
        else:
            print("ERRO: campo não foi adicionado.")
            sys.exit(1)


if __name__ == '__main__':
    adicionar_campo()
```

- [ ] **Step 3: Executar migration local**

```bash
source .venv/bin/activate
python scripts/migrations/motos_assai_02_toggle_usuario.py
```

Expected output: `OK: campo sistema_motos_assai adicionado.`

- [ ] **Step 4: Commit**

```bash
git add scripts/migrations/motos_assai_02_toggle_usuario.{py,sql}
git commit -m "feat(motos_assai): add sistema_motos_assai column to usuarios"
```

---

## Task 3: Adicionar coluna em `Usuario` model

**Files:**
- Modify: `app/auth/models.py:32` (após `sistema_lojas`)

- [ ] **Step 1: Adicionar coluna no model**

Em `app/auth/models.py`, logo após a linha `sistema_lojas = db.Column(...)`, adicionar:

```python
    sistema_motos_assai = db.Column(db.Boolean, default=False, nullable=False)  # Acesso ao módulo Motos Assaí
```

- [ ] **Step 2: Commit**

```bash
git add app/auth/models.py
git commit -m "feat(auth): add sistema_motos_assai field to Usuario model"
```

---

## Task 4: Adicionar método `pode_acessar_motos_assai()`

**Files:**
- Modify: `app/auth/models.py` (após `pode_acessar_lojas`)
- Test: `tests/motos_assai/test_models.py` (criado na Task 26, mas o teste é mencionado aqui para amarrar)

- [ ] **Step 1: Localizar `pode_acessar_lojas` no Usuario**

```bash
grep -n "def pode_acessar_lojas" app/auth/models.py
```

Expected: linha entre 200 e 220.

- [ ] **Step 2: Adicionar método logo após**

Em `app/auth/models.py`, após o `def pode_acessar_lojas(self):` e seu corpo:

```python
    def pode_acessar_motos_assai(self):
        """Acesso ao módulo Motos Assaí.

        Gate de status (idêntico ao Hora): admin sempre passa; usuário
        com status != 'ativo' é bloqueado mesmo que tenha o flag True.
        """
        if self.status != 'ativo':
            return False
        return self.sistema_motos_assai or self.perfil == 'administrador'
```

- [ ] **Step 3: Validar em REPL**

```bash
source .venv/bin/activate
python -c "
from app import create_app, db
from app.auth.models import Usuario
app = create_app()
with app.app_context():
    u = Usuario(email='x@x', nome='X', senha_hash='x', status='ativo', sistema_motos_assai=True)
    print('Ativo + flag:', u.pode_acessar_motos_assai())
    u.status = 'pendente'
    print('Pendente + flag:', u.pode_acessar_motos_assai())
    u.status = 'ativo'
    u.sistema_motos_assai = False
    u.perfil = 'administrador'
    print('Admin sem flag:', u.pode_acessar_motos_assai())
"
```

Expected:
```
Ativo + flag: True
Pendente + flag: False
Admin sem flag: True
```

- [ ] **Step 4: Commit**

```bash
git add app/auth/models.py
git commit -m "feat(auth): add Usuario.pode_acessar_motos_assai() with status gate"
```

---

## Task 5: Migration — schema completo (16 tabelas)

**Files:**
- Create: `scripts/migrations/motos_assai_01_schema.sql`
- Create: `scripts/migrations/motos_assai_01_schema.py`

- [ ] **Step 1: Criar SQL com todas as 16 tabelas**

`scripts/migrations/motos_assai_01_schema.sql`:

```sql
-- Motos Assaí — Schema completo (16 tabelas)
-- Idempotente; safe para re-execução.

-- ===== Cadastros =====

CREATE TABLE IF NOT EXISTS assai_cd (
    id SERIAL PRIMARY KEY,
    nome VARCHAR(80) NOT NULL UNIQUE,
    cnpj VARCHAR(14),
    endereco VARCHAR(255),
    bairro VARCHAR(80),
    cep VARCHAR(10),
    cidade VARCHAR(80),
    uf CHAR(2),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
);

CREATE TABLE IF NOT EXISTS assai_loja (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(10) NOT NULL UNIQUE,
    nome VARCHAR(120) NOT NULL,
    razao_social VARCHAR(200) NOT NULL,
    cnpj VARCHAR(18) NOT NULL,
    ie VARCHAR(20),
    endereco VARCHAR(255),
    bairro VARCHAR(80),
    cep VARCHAR(10),
    cidade VARCHAR(80),
    uf CHAR(2),
    regional VARCHAR(80),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
);
CREATE INDEX IF NOT EXISTS ix_assai_loja_cnpj ON assai_loja(cnpj);

CREATE TABLE IF NOT EXISTS assai_modelo (
    id SERIAL PRIMARY KEY,
    codigo VARCHAR(30) NOT NULL UNIQUE,
    nome VARCHAR(80) NOT NULL,
    descricao_qpa VARCHAR(200),
    codigo_qpa VARCHAR(20),
    regex_chassi VARCHAR(120),
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
);
CREATE INDEX IF NOT EXISTS ix_assai_modelo_codigo_qpa ON assai_modelo(codigo_qpa);

CREATE TABLE IF NOT EXISTS assai_modelo_alias (
    id SERIAL PRIMARY KEY,
    modelo_id INTEGER NOT NULL REFERENCES assai_modelo(id) ON DELETE CASCADE,
    alias VARCHAR(120) NOT NULL,
    tipo VARCHAR(30) NOT NULL,
    ativo BOOLEAN NOT NULL DEFAULT TRUE,
    UNIQUE (tipo, alias)
);
CREATE INDEX IF NOT EXISTS ix_assai_modelo_alias_modelo ON assai_modelo_alias(modelo_id);

-- ===== Identidade da moto =====

CREATE TABLE IF NOT EXISTS assai_moto (
    id SERIAL PRIMARY KEY,
    chassi VARCHAR(50) NOT NULL UNIQUE,
    modelo_id INTEGER NOT NULL REFERENCES assai_modelo(id),
    cor VARCHAR(40),
    motor VARCHAR(50),
    ano INTEGER,
    criada_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
);

CREATE TABLE IF NOT EXISTS assai_moto_evento (
    id SERIAL PRIMARY KEY,
    chassi VARCHAR(50) NOT NULL,
    tipo VARCHAR(40) NOT NULL,
    ocorrido_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    operador_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    observacao TEXT,
    dados_extras JSONB DEFAULT '{}'::jsonb
);
CREATE INDEX IF NOT EXISTS ix_assai_moto_evento_chassi ON assai_moto_evento(chassi);
CREATE INDEX IF NOT EXISTS ix_assai_moto_evento_chassi_ocorrido ON assai_moto_evento(chassi, ocorrido_em DESC);

-- ===== Pipeline pedido → compra → recibo =====

CREATE TABLE IF NOT EXISTS assai_pedido_venda (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(40) NOT NULL UNIQUE,
    data_emissao DATE,
    previsao_entrega DATE,
    fornecedor_cnpj VARCHAR(18),
    pdf_s3_key VARCHAR(500),
    parser_usado VARCHAR(30),
    parsing_confianca NUMERIC(3,2),
    status VARCHAR(30) NOT NULL DEFAULT 'ABERTO',
    criado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
);

CREATE TABLE IF NOT EXISTS assai_pedido_venda_item (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES assai_pedido_venda(id) ON DELETE CASCADE,
    loja_id INTEGER NOT NULL REFERENCES assai_loja(id),
    modelo_id INTEGER NOT NULL REFERENCES assai_modelo(id),
    qtd_pedida INTEGER NOT NULL,
    valor_unitario NUMERIC(12,2) NOT NULL,
    valor_total NUMERIC(14,2) NOT NULL,
    UNIQUE (pedido_id, loja_id, modelo_id)
);
CREATE INDEX IF NOT EXISTS ix_assai_pedido_venda_item_loja ON assai_pedido_venda_item(loja_id);
CREATE INDEX IF NOT EXISTS ix_assai_pedido_venda_item_modelo ON assai_pedido_venda_item(modelo_id);

CREATE TABLE IF NOT EXISTS assai_compra_motochefe (
    id SERIAL PRIMARY KEY,
    numero VARCHAR(30) NOT NULL UNIQUE,
    data_emissao DATE,
    motochefe_cnpj VARCHAR(18),
    status VARCHAR(30) NOT NULL DEFAULT 'ABERTA',
    criada_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criada_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
);

CREATE TABLE IF NOT EXISTS assai_compra_motochefe_pedido (
    id SERIAL PRIMARY KEY,
    compra_id INTEGER NOT NULL REFERENCES assai_compra_motochefe(id) ON DELETE CASCADE,
    pedido_id INTEGER NOT NULL REFERENCES assai_pedido_venda(id) ON DELETE CASCADE,
    UNIQUE (compra_id, pedido_id)
);

CREATE TABLE IF NOT EXISTS assai_recibo_motochefe (
    id SERIAL PRIMARY KEY,
    compra_id INTEGER NOT NULL REFERENCES assai_compra_motochefe(id) ON DELETE CASCADE,
    numero_recibo VARCHAR(40),
    data_recibo DATE,
    equipe VARCHAR(80),
    conferente_motochefe VARCHAR(80),
    total_motos_declarado INTEGER,
    doc_s3_key VARCHAR(500),
    tipo_documento VARCHAR(10),
    parser_usado VARCHAR(30),
    parsing_confianca NUMERIC(3,2),
    status VARCHAR(40) NOT NULL DEFAULT 'RECEBIDO_AGUARDANDO_CONFERENCIA',
    criado_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    criado_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo')
);
CREATE INDEX IF NOT EXISTS ix_assai_recibo_compra ON assai_recibo_motochefe(compra_id);

CREATE TABLE IF NOT EXISTS assai_recibo_item (
    id SERIAL PRIMARY KEY,
    recibo_id INTEGER NOT NULL REFERENCES assai_recibo_motochefe(id) ON DELETE CASCADE,
    chassi VARCHAR(50) NOT NULL,
    modelo_texto_recibo VARCHAR(120),
    modelo_id INTEGER REFERENCES assai_modelo(id),
    cor_texto VARCHAR(40),
    motor VARCHAR(50),
    conferido BOOLEAN NOT NULL DEFAULT FALSE,
    tipo_divergencia VARCHAR(30),
    qr_code_lido BOOLEAN NOT NULL DEFAULT FALSE,
    foto_s3_key VARCHAR(500)
);
CREATE INDEX IF NOT EXISTS ix_assai_recibo_item_recibo ON assai_recibo_item(recibo_id);
CREATE INDEX IF NOT EXISTS ix_assai_recibo_item_chassi ON assai_recibo_item(chassi);
CREATE UNIQUE INDEX IF NOT EXISTS ux_assai_recibo_item_recibo_chassi ON assai_recibo_item(recibo_id, chassi);

-- ===== Separação e faturamento =====

CREATE TABLE IF NOT EXISTS assai_separacao (
    id SERIAL PRIMARY KEY,
    pedido_id INTEGER NOT NULL REFERENCES assai_pedido_venda(id),
    loja_id INTEGER NOT NULL REFERENCES assai_loja(id),
    status VARCHAR(20) NOT NULL DEFAULT 'EM_SEPARACAO',
    iniciada_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    fechada_em TIMESTAMP,
    fechada_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    solicitacao_excel_s3_key VARCHAR(500),
    motivo_cancelamento TEXT
);
CREATE INDEX IF NOT EXISTS ix_assai_separacao_pedido ON assai_separacao(pedido_id);
CREATE INDEX IF NOT EXISTS ix_assai_separacao_loja ON assai_separacao(loja_id);
CREATE UNIQUE INDEX IF NOT EXISTS ux_assai_separacao_pedido_loja_ativa
    ON assai_separacao(pedido_id, loja_id)
    WHERE status <> 'CANCELADA';

CREATE TABLE IF NOT EXISTS assai_separacao_item (
    id SERIAL PRIMARY KEY,
    separacao_id INTEGER NOT NULL REFERENCES assai_separacao(id) ON DELETE CASCADE,
    chassi VARCHAR(50) NOT NULL,
    modelo_id INTEGER NOT NULL REFERENCES assai_modelo(id),
    valor_unitario_qpa NUMERIC(12,2) NOT NULL,
    registrada_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    registrada_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_assai_separacao_item_separacao ON assai_separacao_item(separacao_id);
CREATE INDEX IF NOT EXISTS ix_assai_separacao_item_chassi ON assai_separacao_item(chassi);

CREATE TABLE IF NOT EXISTS assai_nf_qpa (
    id SERIAL PRIMARY KEY,
    separacao_id INTEGER REFERENCES assai_separacao(id) ON DELETE SET NULL,
    chave_44 VARCHAR(44) NOT NULL UNIQUE,
    numero VARCHAR(20),
    serie VARCHAR(10),
    emitente_cnpj VARCHAR(18),
    destinatario_cnpj VARCHAR(18),
    destinatario_nome VARCHAR(200),
    loja_id INTEGER REFERENCES assai_loja(id),
    valor_total NUMERIC(14,2),
    data_emissao DATE,
    pdf_s3_key VARCHAR(500),
    status_match VARCHAR(20) NOT NULL DEFAULT 'NAO_RECONCILIADO',
    importada_em TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'America/Sao_Paulo'),
    importada_por_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL
);
CREATE INDEX IF NOT EXISTS ix_assai_nf_qpa_loja ON assai_nf_qpa(loja_id);
CREATE INDEX IF NOT EXISTS ix_assai_nf_qpa_separacao ON assai_nf_qpa(separacao_id);

CREATE TABLE IF NOT EXISTS assai_nf_qpa_item (
    id SERIAL PRIMARY KEY,
    nf_id INTEGER NOT NULL REFERENCES assai_nf_qpa(id) ON DELETE CASCADE,
    chassi VARCHAR(50) NOT NULL,
    modelo_extraido VARCHAR(120),
    valor_extraido NUMERIC(12,2),
    separacao_item_id INTEGER REFERENCES assai_separacao_item(id) ON DELETE SET NULL,
    tipo_divergencia VARCHAR(30)
);
CREATE INDEX IF NOT EXISTS ix_assai_nf_qpa_item_nf ON assai_nf_qpa_item(nf_id);
CREATE INDEX IF NOT EXISTS ix_assai_nf_qpa_item_chassi ON assai_nf_qpa_item(chassi);
```

- [ ] **Step 2: Criar Python verificador**

`scripts/migrations/motos_assai_01_schema.py`:

```python
"""
Migration: Schema completo do módulo Motos Assaí (16 tabelas)
==============================================================
Executar: python scripts/migrations/motos_assai_01_schema.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text, inspect


TABELAS_ESPERADAS = [
    'assai_cd', 'assai_loja', 'assai_modelo', 'assai_modelo_alias',
    'assai_moto', 'assai_moto_evento',
    'assai_pedido_venda', 'assai_pedido_venda_item',
    'assai_compra_motochefe', 'assai_compra_motochefe_pedido',
    'assai_recibo_motochefe', 'assai_recibo_item',
    'assai_separacao', 'assai_separacao_item',
    'assai_nf_qpa', 'assai_nf_qpa_item',
]


def criar_schema():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        existentes_antes = set(inspector.get_table_names())
        a_criar = [t for t in TABELAS_ESPERADAS if t not in existentes_antes]

        if not a_criar:
            print("Todas as tabelas já existem. Nada a fazer.")
            return

        print(f"Criando {len(a_criar)} tabelas: {a_criar}")

        sql_path = os.path.join(os.path.dirname(__file__), 'motos_assai_01_schema.sql')
        with open(sql_path, 'r', encoding='utf-8') as f:
            sql = f.read()

        db.session.execute(text(sql))
        db.session.commit()

        inspector = inspect(db.engine)
        existentes_depois = set(inspector.get_table_names())
        criadas = [t for t in TABELAS_ESPERADAS if t in existentes_depois and t not in existentes_antes]
        faltando = [t for t in TABELAS_ESPERADAS if t not in existentes_depois]

        print(f"Criadas: {criadas}")
        if faltando:
            print(f"ERRO: tabelas não criadas: {faltando}")
            sys.exit(1)
        print("OK: schema completo.")


if __name__ == '__main__':
    criar_schema()
```

- [ ] **Step 3: Executar migration local**

```bash
source .venv/bin/activate
python scripts/migrations/motos_assai_01_schema.py
```

Expected: `OK: schema completo.` com todas as 16 tabelas listadas.

- [ ] **Step 4: Validar contagem**

```bash
python -c "
from app import create_app, db
from sqlalchemy import inspect
app = create_app()
with app.app_context():
    insp = inspect(db.engine)
    assai = sorted([t for t in insp.get_table_names() if t.startswith('assai_')])
    print(f'Total tabelas assai_: {len(assai)}')
    for t in assai: print(f'  - {t}')
"
```

Expected: `Total tabelas assai_: 16`

- [ ] **Step 5: Commit**

```bash
git add scripts/migrations/motos_assai_01_schema.{py,sql}
git commit -m "feat(motos_assai): create initial schema (16 tables)"
```

---

## Task 6: Models SQLAlchemy — `AssaiCd` e `AssaiLoja`

**Files:**
- Create: `app/motos_assai/models/cd.py`
- Create: `app/motos_assai/models/loja.py`
- Modify: `app/motos_assai/models/__init__.py`

- [ ] **Step 1: AssaiCd**

`app/motos_assai/models/cd.py`:

```python
from app import db
from app.utils.timezone import agora_brasil_naive


class AssaiCd(db.Model):
    __tablename__ = 'assai_cd'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(80), unique=True, nullable=False)
    cnpj = db.Column(db.String(14))
    endereco = db.Column(db.String(255))
    bairro = db.Column(db.String(80))
    cep = db.Column(db.String(10))
    cidade = db.Column(db.String(80))
    uf = db.Column(db.String(2))
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)

    def __repr__(self):
        return f'<AssaiCd {self.nome}>'
```

- [ ] **Step 2: AssaiLoja**

`app/motos_assai/models/loja.py`:

```python
from app import db
from app.utils.timezone import agora_brasil_naive


class AssaiLoja(db.Model):
    __tablename__ = 'assai_loja'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(10), unique=True, nullable=False)
    nome = db.Column(db.String(120), nullable=False)
    razao_social = db.Column(db.String(200), nullable=False)
    cnpj = db.Column(db.String(18), nullable=False, index=True)
    ie = db.Column(db.String(20))
    endereco = db.Column(db.String(255))
    bairro = db.Column(db.String(80))
    cep = db.Column(db.String(10))
    cidade = db.Column(db.String(80))
    uf = db.Column(db.String(2))
    regional = db.Column(db.String(80))
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)

    def __repr__(self):
        return f'<AssaiLoja {self.numero} {self.nome}>'
```

- [ ] **Step 3: __init__.py exporta**

`app/motos_assai/models/__init__.py`:

```python
from .cd import AssaiCd
from .loja import AssaiLoja

__all__ = ['AssaiCd', 'AssaiLoja']
```

- [ ] **Step 4: Validar import**

```bash
source .venv/bin/activate
python -c "
from app import create_app, db
from app.motos_assai.models import AssaiCd, AssaiLoja
app = create_app()
with app.app_context():
    print('Cd count:', AssaiCd.query.count())
    print('Loja count:', AssaiLoja.query.count())
"
```

Expected: `Cd count: 0` / `Loja count: 0` (sem erros).

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/models/cd.py app/motos_assai/models/loja.py app/motos_assai/models/__init__.py
git commit -m "feat(motos_assai): add AssaiCd and AssaiLoja models"
```

---

## Task 7: Models — `AssaiModelo` e `AssaiModeloAlias`

**Files:**
- Create: `app/motos_assai/models/modelo.py`
- Modify: `app/motos_assai/models/__init__.py`

- [ ] **Step 1: AssaiModelo + AssaiModeloAlias**

`app/motos_assai/models/modelo.py`:

```python
from app import db
from app.utils.timezone import agora_brasil_naive


# Tipos de alias permitidos
ALIAS_TIPO_NOME_LIVRE = 'NOME_LIVRE'
ALIAS_TIPO_CODIGO_QPA = 'CODIGO_QPA'
ALIAS_TIPO_DESCRICAO_RECIBO = 'DESCRICAO_RECIBO'
ALIAS_TIPOS_VALIDOS = [
    ALIAS_TIPO_NOME_LIVRE,
    ALIAS_TIPO_CODIGO_QPA,
    ALIAS_TIPO_DESCRICAO_RECIBO,
]


class AssaiModelo(db.Model):
    __tablename__ = 'assai_modelo'

    id = db.Column(db.Integer, primary_key=True)
    codigo = db.Column(db.String(30), unique=True, nullable=False)
    nome = db.Column(db.String(80), nullable=False)
    descricao_qpa = db.Column(db.String(200))
    codigo_qpa = db.Column(db.String(20), index=True)
    regex_chassi = db.Column(db.String(120))
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    criado_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)

    aliases = db.relationship(
        'AssaiModeloAlias',
        backref='modelo',
        cascade='all, delete-orphan',
        lazy='selectin',
    )

    def __repr__(self):
        return f'<AssaiModelo {self.codigo}>'


class AssaiModeloAlias(db.Model):
    __tablename__ = 'assai_modelo_alias'

    id = db.Column(db.Integer, primary_key=True)
    modelo_id = db.Column(db.Integer, db.ForeignKey('assai_modelo.id', ondelete='CASCADE'), nullable=False, index=True)
    alias = db.Column(db.String(120), nullable=False)
    tipo = db.Column(db.String(30), nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)

    __table_args__ = (
        db.UniqueConstraint('tipo', 'alias', name='uq_assai_modelo_alias_tipo_alias'),
    )

    def __repr__(self):
        return f'<AssaiModeloAlias {self.tipo}:{self.alias} -> modelo_id={self.modelo_id}>'
```

- [ ] **Step 2: Atualizar __init__.py**

`app/motos_assai/models/__init__.py`:

```python
from .cd import AssaiCd
from .loja import AssaiLoja
from .modelo import (
    AssaiModelo,
    AssaiModeloAlias,
    ALIAS_TIPO_NOME_LIVRE,
    ALIAS_TIPO_CODIGO_QPA,
    ALIAS_TIPO_DESCRICAO_RECIBO,
    ALIAS_TIPOS_VALIDOS,
)

__all__ = [
    'AssaiCd', 'AssaiLoja',
    'AssaiModelo', 'AssaiModeloAlias',
    'ALIAS_TIPO_NOME_LIVRE', 'ALIAS_TIPO_CODIGO_QPA',
    'ALIAS_TIPO_DESCRICAO_RECIBO', 'ALIAS_TIPOS_VALIDOS',
]
```

- [ ] **Step 3: Validar relationship**

```bash
python -c "
from app import create_app, db
from app.motos_assai.models import AssaiModelo, AssaiModeloAlias, ALIAS_TIPO_NOME_LIVRE
app = create_app()
with app.app_context():
    m = AssaiModelo(codigo='TEST', nome='Test')
    m.aliases.append(AssaiModeloAlias(alias='test alias', tipo=ALIAS_TIPO_NOME_LIVRE))
    db.session.add(m)
    db.session.flush()
    print('Modelo id:', m.id, 'aliases:', len(m.aliases))
    db.session.rollback()
"
```

Expected: `Modelo id: <N> aliases: 1`

- [ ] **Step 4: Commit**

```bash
git add app/motos_assai/models/modelo.py app/motos_assai/models/__init__.py
git commit -m "feat(motos_assai): add AssaiModelo + AssaiModeloAlias"
```

---

## Task 8: Models — `AssaiMoto` e `AssaiMotoEvento`

**Files:**
- Create: `app/motos_assai/models/moto.py`
- Modify: `app/motos_assai/models/__init__.py`

- [ ] **Step 1: Models**

`app/motos_assai/models/moto.py`:

```python
from app import db
from sqlalchemy.dialects.postgresql import JSONB
from app.utils.timezone import agora_brasil_naive


# Eventos canônicos
EVENTO_ESTOQUE = 'ESTOQUE'
EVENTO_MONTADA = 'MONTADA'
EVENTO_PENDENTE = 'PENDENTE'
EVENTO_PENDENCIA_RESOLVIDA = 'PENDENCIA_RESOLVIDA'
EVENTO_DISPONIVEL = 'DISPONIVEL'
EVENTO_REVERTIDA_PARA_MONTADA = 'REVERTIDA_PARA_MONTADA'
EVENTO_SEPARADA = 'SEPARADA'
EVENTO_FATURADA = 'FATURADA'
EVENTO_CANCELADA = 'CANCELADA'
EVENTO_MOTO_FALTANDO = 'MOTO_FALTANDO'

EVENTOS_VALIDOS = {
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE, EVENTO_PENDENCIA_RESOLVIDA,
    EVENTO_DISPONIVEL, EVENTO_REVERTIDA_PARA_MONTADA,
    EVENTO_SEPARADA, EVENTO_FATURADA, EVENTO_CANCELADA, EVENTO_MOTO_FALTANDO,
}

# Eventos que indicam moto presente em estoque (qualquer estágio interno)
EVENTOS_EM_ESTOQUE = {EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_DISPONIVEL}
EVENTOS_BLOQUEADO_DISPONIBILIZAR = {EVENTO_PENDENTE}
EVENTOS_FORA_ESTOQUE = {EVENTO_SEPARADA, EVENTO_FATURADA, EVENTO_CANCELADA, EVENTO_MOTO_FALTANDO}


class AssaiMoto(db.Model):
    __tablename__ = 'assai_moto'

    id = db.Column(db.Integer, primary_key=True)
    chassi = db.Column(db.String(50), unique=True, nullable=False)
    modelo_id = db.Column(db.Integer, db.ForeignKey('assai_modelo.id'), nullable=False)
    cor = db.Column(db.String(40))
    motor = db.Column(db.String(50))
    ano = db.Column(db.Integer)
    criada_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)

    modelo = db.relationship('AssaiModelo', backref='motos', lazy='joined')

    def __repr__(self):
        return f'<AssaiMoto {self.chassi}>'


class AssaiMotoEvento(db.Model):
    __tablename__ = 'assai_moto_evento'

    id = db.Column(db.Integer, primary_key=True)
    chassi = db.Column(db.String(50), nullable=False, index=True)
    tipo = db.Column(db.String(40), nullable=False)
    ocorrido_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)
    operador_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    observacao = db.Column(db.Text)
    dados_extras = db.Column(JSONB, default=dict)

    operador = db.relationship('Usuario', lazy='joined')

    def __repr__(self):
        return f'<AssaiMotoEvento {self.chassi} {self.tipo} @{self.ocorrido_em}>'
```

- [ ] **Step 2: Atualizar __init__.py**

Adicionar a `app/motos_assai/models/__init__.py`:

```python
from .moto import (
    AssaiMoto, AssaiMotoEvento,
    EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE, EVENTO_PENDENCIA_RESOLVIDA,
    EVENTO_DISPONIVEL, EVENTO_REVERTIDA_PARA_MONTADA,
    EVENTO_SEPARADA, EVENTO_FATURADA, EVENTO_CANCELADA, EVENTO_MOTO_FALTANDO,
    EVENTOS_VALIDOS, EVENTOS_EM_ESTOQUE,
    EVENTOS_BLOQUEADO_DISPONIBILIZAR, EVENTOS_FORA_ESTOQUE,
)
```

E adicionar todos esses símbolos a `__all__`.

- [ ] **Step 3: Validar**

```bash
python -c "
from app import create_app, db
from app.motos_assai.models import AssaiMoto, AssaiMotoEvento, EVENTO_ESTOQUE, EVENTOS_VALIDOS
app = create_app()
with app.app_context():
    print('Moto count:', AssaiMoto.query.count())
    print('Evento count:', AssaiMotoEvento.query.count())
    print('Eventos válidos:', len(EVENTOS_VALIDOS))
"
```

Expected: `Eventos válidos: 10`

- [ ] **Step 4: Commit**

```bash
git add app/motos_assai/models/moto.py app/motos_assai/models/__init__.py
git commit -m "feat(motos_assai): add AssaiMoto + AssaiMotoEvento with event constants"
```

---

## Task 9: Models — `AssaiPedidoVenda` e `AssaiPedidoVendaItem`

**Files:**
- Create: `app/motos_assai/models/pedido.py`
- Modify: `app/motos_assai/models/__init__.py`

- [ ] **Step 1: Model**

`app/motos_assai/models/pedido.py`:

```python
from app import db
from app.utils.timezone import agora_brasil_naive


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


class AssaiPedidoVenda(db.Model):
    __tablename__ = 'assai_pedido_venda'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(40), unique=True, nullable=False)
    data_emissao = db.Column(db.Date)
    previsao_entrega = db.Column(db.Date)
    fornecedor_cnpj = db.Column(db.String(18))
    pdf_s3_key = db.Column(db.String(500))
    parser_usado = db.Column(db.String(30))
    parsing_confianca = db.Column(db.Numeric(3, 2))
    status = db.Column(db.String(30), default=PEDIDO_STATUS_ABERTO, nullable=False)
    criado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    criado_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)

    itens = db.relationship('AssaiPedidoVendaItem', backref='pedido',
                            cascade='all, delete-orphan', lazy='selectin')
    criado_por = db.relationship('Usuario', lazy='joined')

    def __repr__(self):
        return f'<AssaiPedidoVenda {self.numero} {self.status}>'


class AssaiPedidoVendaItem(db.Model):
    __tablename__ = 'assai_pedido_venda_item'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('assai_pedido_venda.id', ondelete='CASCADE'), nullable=False)
    loja_id = db.Column(db.Integer, db.ForeignKey('assai_loja.id'), nullable=False, index=True)
    modelo_id = db.Column(db.Integer, db.ForeignKey('assai_modelo.id'), nullable=False, index=True)
    qtd_pedida = db.Column(db.Integer, nullable=False)
    valor_unitario = db.Column(db.Numeric(12, 2), nullable=False)
    valor_total = db.Column(db.Numeric(14, 2), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('pedido_id', 'loja_id', 'modelo_id',
                            name='uq_assai_pedido_item_pedido_loja_modelo'),
    )

    loja = db.relationship('AssaiLoja', lazy='joined')
    modelo = db.relationship('AssaiModelo', lazy='joined')

    def __repr__(self):
        return f'<AssaiPedidoVendaItem pedido={self.pedido_id} loja={self.loja_id} modelo={self.modelo_id} qtd={self.qtd_pedida}>'
```

- [ ] **Step 2: Atualizar __init__.py**

Adicionar:
```python
from .pedido import (
    AssaiPedidoVenda, AssaiPedidoVendaItem,
    PEDIDO_STATUS_ABERTO, PEDIDO_STATUS_EM_PRODUCAO, PEDIDO_STATUS_SEPARANDO,
    PEDIDO_STATUS_FATURADO_PARCIAL, PEDIDO_STATUS_FATURADO, PEDIDO_STATUS_CANCELADO,
    PEDIDO_STATUS_VALIDOS,
)
```

E acrescentar a `__all__`.

- [ ] **Step 3: Commit**

```bash
git add app/motos_assai/models/pedido.py app/motos_assai/models/__init__.py
git commit -m "feat(motos_assai): add AssaiPedidoVenda + item with status constants"
```

---

## Task 10: Models — Compra e Recibo Motochefe

**Files:**
- Create: `app/motos_assai/models/compra.py`
- Create: `app/motos_assai/models/recibo.py`
- Modify: `app/motos_assai/models/__init__.py`

- [ ] **Step 1: AssaiCompraMotochefe + link**

`app/motos_assai/models/compra.py`:

```python
from app import db
from app.utils.timezone import agora_brasil_naive


COMPRA_STATUS_ABERTA = 'ABERTA'
COMPRA_STATUS_RECEBIMENTO_PARCIAL = 'RECEBIMENTO_PARCIAL'
COMPRA_STATUS_FECHADA = 'FECHADA'
COMPRA_STATUS_CANCELADA = 'CANCELADA'
COMPRA_STATUS_VALIDOS = {
    COMPRA_STATUS_ABERTA, COMPRA_STATUS_RECEBIMENTO_PARCIAL,
    COMPRA_STATUS_FECHADA, COMPRA_STATUS_CANCELADA,
}


class AssaiCompraMotochefe(db.Model):
    __tablename__ = 'assai_compra_motochefe'

    id = db.Column(db.Integer, primary_key=True)
    numero = db.Column(db.String(30), unique=True, nullable=False)
    data_emissao = db.Column(db.Date)
    motochefe_cnpj = db.Column(db.String(18))
    status = db.Column(db.String(30), default=COMPRA_STATUS_ABERTA, nullable=False)
    criada_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    criada_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)

    pedido_links = db.relationship('AssaiCompraMotochefePedido', backref='compra',
                                   cascade='all, delete-orphan', lazy='selectin')
    recibos = db.relationship('AssaiReciboMotochefe', backref='compra',
                              cascade='all, delete-orphan', lazy='selectin')
    criada_por = db.relationship('Usuario', lazy='joined')

    def __repr__(self):
        return f'<AssaiCompraMotochefe {self.numero} {self.status}>'


class AssaiCompraMotochefePedido(db.Model):
    __tablename__ = 'assai_compra_motochefe_pedido'

    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey('assai_compra_motochefe.id', ondelete='CASCADE'), nullable=False)
    pedido_id = db.Column(db.Integer, db.ForeignKey('assai_pedido_venda.id', ondelete='CASCADE'), nullable=False)

    __table_args__ = (
        db.UniqueConstraint('compra_id', 'pedido_id', name='uq_assai_compra_pedido'),
    )

    pedido = db.relationship('AssaiPedidoVenda', lazy='joined')

    def __repr__(self):
        return f'<AssaiCompraMotochefePedido compra={self.compra_id} pedido={self.pedido_id}>'
```

- [ ] **Step 2: AssaiReciboMotochefe + Item**

`app/motos_assai/models/recibo.py`:

```python
from app import db
from app.utils.timezone import agora_brasil_naive


RECIBO_STATUS_AGUARDANDO = 'RECEBIDO_AGUARDANDO_CONFERENCIA'
RECIBO_STATUS_EM_CONFERENCIA = 'EM_CONFERENCIA'
RECIBO_STATUS_CONCLUIDO = 'CONCLUIDO'
RECIBO_STATUS_COM_DIVERGENCIA = 'COM_DIVERGENCIA'
RECIBO_STATUS_VALIDOS = {
    RECIBO_STATUS_AGUARDANDO, RECIBO_STATUS_EM_CONFERENCIA,
    RECIBO_STATUS_CONCLUIDO, RECIBO_STATUS_COM_DIVERGENCIA,
}

DIVERGENCIA_MODELO_DIFERENTE = 'MODELO_DIFERENTE'
DIVERGENCIA_COR_DIFERENTE = 'COR_DIFERENTE'
DIVERGENCIA_CHASSI_EXTRA = 'CHASSI_EXTRA'
DIVERGENCIA_MOTO_FALTANDO = 'MOTO_FALTANDO'
DIVERGENCIA_AVARIA_FISICA = 'AVARIA_FISICA'
DIVERGENCIAS_VALIDAS = {
    DIVERGENCIA_MODELO_DIFERENTE, DIVERGENCIA_COR_DIFERENTE,
    DIVERGENCIA_CHASSI_EXTRA, DIVERGENCIA_MOTO_FALTANDO, DIVERGENCIA_AVARIA_FISICA,
}


class AssaiReciboMotochefe(db.Model):
    __tablename__ = 'assai_recibo_motochefe'

    id = db.Column(db.Integer, primary_key=True)
    compra_id = db.Column(db.Integer, db.ForeignKey('assai_compra_motochefe.id', ondelete='CASCADE'), nullable=False, index=True)
    numero_recibo = db.Column(db.String(40))
    data_recibo = db.Column(db.Date)
    equipe = db.Column(db.String(80))
    conferente_motochefe = db.Column(db.String(80))
    total_motos_declarado = db.Column(db.Integer)
    doc_s3_key = db.Column(db.String(500))
    tipo_documento = db.Column(db.String(10))
    parser_usado = db.Column(db.String(30))
    parsing_confianca = db.Column(db.Numeric(3, 2))
    status = db.Column(db.String(40), default=RECIBO_STATUS_AGUARDANDO, nullable=False)
    criado_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    criado_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)

    itens = db.relationship('AssaiReciboItem', backref='recibo',
                            cascade='all, delete-orphan', lazy='selectin')
    criado_por = db.relationship('Usuario', lazy='joined')

    def __repr__(self):
        return f'<AssaiReciboMotochefe {self.numero_recibo} {self.status}>'


class AssaiReciboItem(db.Model):
    __tablename__ = 'assai_recibo_item'

    id = db.Column(db.Integer, primary_key=True)
    recibo_id = db.Column(db.Integer, db.ForeignKey('assai_recibo_motochefe.id', ondelete='CASCADE'), nullable=False, index=True)
    chassi = db.Column(db.String(50), nullable=False, index=True)
    modelo_texto_recibo = db.Column(db.String(120))
    modelo_id = db.Column(db.Integer, db.ForeignKey('assai_modelo.id'))
    cor_texto = db.Column(db.String(40))
    motor = db.Column(db.String(50))
    conferido = db.Column(db.Boolean, default=False, nullable=False)
    tipo_divergencia = db.Column(db.String(30))
    qr_code_lido = db.Column(db.Boolean, default=False, nullable=False)
    foto_s3_key = db.Column(db.String(500))

    modelo = db.relationship('AssaiModelo', lazy='joined')

    def __repr__(self):
        return f'<AssaiReciboItem recibo={self.recibo_id} chassi={self.chassi}>'
```

- [ ] **Step 3: Atualizar __init__.py**

Adicionar:
```python
from .compra import (
    AssaiCompraMotochefe, AssaiCompraMotochefePedido,
    COMPRA_STATUS_ABERTA, COMPRA_STATUS_RECEBIMENTO_PARCIAL,
    COMPRA_STATUS_FECHADA, COMPRA_STATUS_CANCELADA, COMPRA_STATUS_VALIDOS,
)
from .recibo import (
    AssaiReciboMotochefe, AssaiReciboItem,
    RECIBO_STATUS_AGUARDANDO, RECIBO_STATUS_EM_CONFERENCIA,
    RECIBO_STATUS_CONCLUIDO, RECIBO_STATUS_COM_DIVERGENCIA, RECIBO_STATUS_VALIDOS,
    DIVERGENCIA_MODELO_DIFERENTE, DIVERGENCIA_COR_DIFERENTE,
    DIVERGENCIA_CHASSI_EXTRA, DIVERGENCIA_MOTO_FALTANDO,
    DIVERGENCIA_AVARIA_FISICA, DIVERGENCIAS_VALIDAS,
)
```

E acrescentar a `__all__`.

- [ ] **Step 4: Commit**

```bash
git add app/motos_assai/models/compra.py app/motos_assai/models/recibo.py app/motos_assai/models/__init__.py
git commit -m "feat(motos_assai): add Compra + Recibo Motochefe models"
```

---

## Task 11: Models — `AssaiSeparacao` e `AssaiNfQpa`

**Files:**
- Create: `app/motos_assai/models/separacao.py`
- Create: `app/motos_assai/models/nf_qpa.py`
- Modify: `app/motos_assai/models/__init__.py`

- [ ] **Step 1: Separacao**

`app/motos_assai/models/separacao.py`:

```python
from app import db
from app.utils.timezone import agora_brasil_naive


SEPARACAO_STATUS_EM_SEPARACAO = 'EM_SEPARACAO'
SEPARACAO_STATUS_FECHADA = 'FECHADA'
SEPARACAO_STATUS_FATURADA = 'FATURADA'
SEPARACAO_STATUS_CANCELADA = 'CANCELADA'
SEPARACAO_STATUS_VALIDOS = {
    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
    SEPARACAO_STATUS_FATURADA, SEPARACAO_STATUS_CANCELADA,
}


class AssaiSeparacao(db.Model):
    __tablename__ = 'assai_separacao'

    id = db.Column(db.Integer, primary_key=True)
    pedido_id = db.Column(db.Integer, db.ForeignKey('assai_pedido_venda.id'), nullable=False, index=True)
    loja_id = db.Column(db.Integer, db.ForeignKey('assai_loja.id'), nullable=False, index=True)
    status = db.Column(db.String(20), default=SEPARACAO_STATUS_EM_SEPARACAO, nullable=False)
    iniciada_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)
    fechada_em = db.Column(db.DateTime)
    fechada_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))
    solicitacao_excel_s3_key = db.Column(db.String(500))
    motivo_cancelamento = db.Column(db.Text)

    itens = db.relationship('AssaiSeparacaoItem', backref='separacao',
                            cascade='all, delete-orphan', lazy='selectin')
    pedido = db.relationship('AssaiPedidoVenda', lazy='joined')
    loja = db.relationship('AssaiLoja', lazy='joined')
    fechada_por = db.relationship('Usuario', lazy='joined')

    def __repr__(self):
        return f'<AssaiSeparacao pedido={self.pedido_id} loja={self.loja_id} {self.status}>'


class AssaiSeparacaoItem(db.Model):
    __tablename__ = 'assai_separacao_item'

    id = db.Column(db.Integer, primary_key=True)
    separacao_id = db.Column(db.Integer, db.ForeignKey('assai_separacao.id', ondelete='CASCADE'), nullable=False, index=True)
    chassi = db.Column(db.String(50), nullable=False, index=True)
    modelo_id = db.Column(db.Integer, db.ForeignKey('assai_modelo.id'), nullable=False)
    valor_unitario_qpa = db.Column(db.Numeric(12, 2), nullable=False)
    registrada_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)
    registrada_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))

    modelo = db.relationship('AssaiModelo', lazy='joined')
    registrada_por = db.relationship('Usuario', lazy='joined')

    def __repr__(self):
        return f'<AssaiSeparacaoItem separacao={self.separacao_id} chassi={self.chassi}>'
```

- [ ] **Step 2: NfQpa**

`app/motos_assai/models/nf_qpa.py`:

```python
from app import db
from app.utils.timezone import agora_brasil_naive


NF_STATUS_BATEU = 'BATEU'
NF_STATUS_DIVERGENTE = 'DIVERGENTE'
NF_STATUS_NAO_RECONCILIADO = 'NAO_RECONCILIADO'
NF_STATUS_VALIDOS = {NF_STATUS_BATEU, NF_STATUS_DIVERGENTE, NF_STATUS_NAO_RECONCILIADO}


class AssaiNfQpa(db.Model):
    __tablename__ = 'assai_nf_qpa'

    id = db.Column(db.Integer, primary_key=True)
    separacao_id = db.Column(db.Integer, db.ForeignKey('assai_separacao.id', ondelete='SET NULL'), index=True)
    chave_44 = db.Column(db.String(44), unique=True, nullable=False)
    numero = db.Column(db.String(20))
    serie = db.Column(db.String(10))
    emitente_cnpj = db.Column(db.String(18))
    destinatario_cnpj = db.Column(db.String(18))
    destinatario_nome = db.Column(db.String(200))
    loja_id = db.Column(db.Integer, db.ForeignKey('assai_loja.id'), index=True)
    valor_total = db.Column(db.Numeric(14, 2))
    data_emissao = db.Column(db.Date)
    pdf_s3_key = db.Column(db.String(500))
    status_match = db.Column(db.String(20), default=NF_STATUS_NAO_RECONCILIADO, nullable=False)
    importada_em = db.Column(db.DateTime, default=agora_brasil_naive, nullable=False)
    importada_por_id = db.Column(db.Integer, db.ForeignKey('usuarios.id', ondelete='SET NULL'))

    itens = db.relationship('AssaiNfQpaItem', backref='nf',
                            cascade='all, delete-orphan', lazy='selectin')
    separacao = db.relationship('AssaiSeparacao', lazy='joined')
    loja = db.relationship('AssaiLoja', lazy='joined')

    def __repr__(self):
        return f'<AssaiNfQpa {self.chave_44} {self.status_match}>'


class AssaiNfQpaItem(db.Model):
    __tablename__ = 'assai_nf_qpa_item'

    id = db.Column(db.Integer, primary_key=True)
    nf_id = db.Column(db.Integer, db.ForeignKey('assai_nf_qpa.id', ondelete='CASCADE'), nullable=False, index=True)
    chassi = db.Column(db.String(50), nullable=False, index=True)
    modelo_extraido = db.Column(db.String(120))
    valor_extraido = db.Column(db.Numeric(12, 2))
    separacao_item_id = db.Column(db.Integer, db.ForeignKey('assai_separacao_item.id', ondelete='SET NULL'))
    tipo_divergencia = db.Column(db.String(30))

    def __repr__(self):
        return f'<AssaiNfQpaItem nf={self.nf_id} chassi={self.chassi}>'
```

- [ ] **Step 3: Atualizar __init__.py**

Adicionar:
```python
from .separacao import (
    AssaiSeparacao, AssaiSeparacaoItem,
    SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
    SEPARACAO_STATUS_FATURADA, SEPARACAO_STATUS_CANCELADA, SEPARACAO_STATUS_VALIDOS,
)
from .nf_qpa import (
    AssaiNfQpa, AssaiNfQpaItem,
    NF_STATUS_BATEU, NF_STATUS_DIVERGENTE, NF_STATUS_NAO_RECONCILIADO, NF_STATUS_VALIDOS,
)
```

E acrescentar a `__all__`.

- [ ] **Step 4: Validar todos imports**

```bash
python -c "
from app.motos_assai.models import (
    AssaiCd, AssaiLoja, AssaiModelo, AssaiModeloAlias,
    AssaiMoto, AssaiMotoEvento,
    AssaiPedidoVenda, AssaiPedidoVendaItem,
    AssaiCompraMotochefe, AssaiCompraMotochefePedido,
    AssaiReciboMotochefe, AssaiReciboItem,
    AssaiSeparacao, AssaiSeparacaoItem,
    AssaiNfQpa, AssaiNfQpaItem,
)
print('Todos os 16 models importam corretamente.')
"
```

Expected: `Todos os 16 models importam corretamente.`

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/models/separacao.py app/motos_assai/models/nf_qpa.py app/motos_assai/models/__init__.py
git commit -m "feat(motos_assai): add Separacao + NfQpa models (completes 16 tables)"
```

---

## Task 12: Decorator `require_motos_assai`

**Files:**
- Create: `app/motos_assai/decorators.py`
- Test: `tests/motos_assai/test_decorator.py` (criado na Task 26 mas testes esboçados aqui)

- [ ] **Step 1: Decorator**

`app/motos_assai/decorators.py`:

```python
"""Decorator de proteção de rotas do módulo Motos Assaí.

Padrão idêntico ao Hora `require_lojas`: gate de status + admin bypass.
"""

from functools import wraps
from flask import flash, redirect, url_for, jsonify, request
from flask_login import current_user


def require_motos_assai(func):
    """Bloqueia rotas para usuários sem `sistema_motos_assai`.

    Comportamento:
    - Não autenticado: redirect para login
    - Sem flag (e não admin): JSON 403 ou flash + redirect para dashboard principal
    - Status != 'ativo': mesma resposta de "sem flag"
    - Admin (perfil='administrador'): sempre passa
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for('auth.login'))

        if not current_user.pode_acessar_motos_assai():
            wants_json = (
                request.is_json
                or 'application/json' in request.headers.get('Accept', '')
            )
            if wants_json:
                return jsonify({'error': 'Acesso negado ao módulo Motos Assaí'}), 403
            flash('Acesso negado ao módulo Motos Assaí.', 'danger')
            return redirect(url_for('main.dashboard'))

        return func(*args, **kwargs)
    return wrapper
```

- [ ] **Step 2: Validar import**

```bash
python -c "
from app.motos_assai.decorators import require_motos_assai
print('Decorator imports OK:', require_motos_assai)
"
```

- [ ] **Step 3: Commit**

```bash
git add app/motos_assai/decorators.py
git commit -m "feat(motos_assai): add require_motos_assai decorator"
```

---

## Task 13: Blueprint registrado em `app/__init__.py`

**Files:**
- Create: `app/motos_assai/routes/__init__.py` (com blueprint)
- Modify: `app/__init__.py` (registrar)

- [ ] **Step 1: Criar blueprint**

`app/motos_assai/routes/__init__.py`:

```python
"""Blueprint do módulo Motos Assaí.

Todas as rotas usam `@require_motos_assai`. URL prefix: `/motos-assai`.
Templates resolvidos em `app/templates/motos_assai/`.
"""

from flask import Blueprint

motos_assai_bp = Blueprint(
    'motos_assai',
    __name__,
    url_prefix='/motos-assai',
    template_folder='../../templates/motos_assai',
    static_folder=None,
)

# Sub-rotas serão importadas conforme criadas (Task 19, 23, 24, 25)
```

- [ ] **Step 2: Registrar em app/__init__.py**

Localizar onde outros blueprints são registrados (procurar por `register_blueprint`):

```bash
grep -n "register_blueprint" app/__init__.py | head -20
```

No mesmo bloco onde `hora` é registrado, adicionar:

```python
    # Motos Assaí (módulo isolado, B2B Q.P.A. → Sendas/Assaí)
    from app.motos_assai.routes import motos_assai_bp
    app.register_blueprint(motos_assai_bp)
```

- [ ] **Step 3: Validar startup do app**

```bash
python -c "
from app import create_app
app = create_app()
rules = [r.rule for r in app.url_map.iter_rules() if r.rule.startswith('/motos-assai')]
print('Rotas /motos-assai/*:', rules)
"
```

Expected: lista vazia `[]` (blueprint registrado mas sem rotas ainda — OK).

- [ ] **Step 4: Commit**

```bash
git add app/motos_assai/routes/__init__.py app/__init__.py
git commit -m "feat(motos_assai): register blueprint at /motos-assai"
```

---

## Task 14: Atualizar `auth/forms.py` — checkbox sistema_motos_assai

**Files:**
- Modify: `app/auth/forms.py`

- [ ] **Step 1: Localizar BooleanFields existentes**

```bash
grep -n "sistema_lojas\|sistema_carvia" app/auth/forms.py | head -10
```

- [ ] **Step 2: Adicionar campo em AprovarUsuarioForm**

Localizar `class AprovarUsuarioForm` e, no bloco com `sistema_lojas = BooleanField(...)`, adicionar logo após:

```python
    sistema_motos_assai = BooleanField('Acesso ao Sistema Motos Assaí')
```

- [ ] **Step 3: Adicionar em EditarUsuarioForm**

Mesma adição em `class EditarUsuarioForm`.

- [ ] **Step 4: Validar imports**

```bash
python -c "
from app.auth.forms import AprovarUsuarioForm, EditarUsuarioForm
f = AprovarUsuarioForm.__dict__
print('sistema_motos_assai in AprovarUsuarioForm:', 'sistema_motos_assai' in f)
g = EditarUsuarioForm.__dict__
print('sistema_motos_assai in EditarUsuarioForm:', 'sistema_motos_assai' in g)
"
```

Expected: `True` para ambos.

- [ ] **Step 5: Commit**

```bash
git add app/auth/forms.py
git commit -m "feat(auth): add sistema_motos_assai field to user forms"
```

---

## Task 15: Atualizar `auth/routes.py` — leitura/escrita do flag

**Files:**
- Modify: `app/auth/routes.py`

- [ ] **Step 1: Localizar atribuições de sistema_lojas**

```bash
grep -n "sistema_lojas" app/auth/routes.py
```

Cada ocorrência de `usuario.sistema_lojas = form.sistema_lojas.data` precisa de uma irmã para `sistema_motos_assai`.
Cada ocorrência de `form.sistema_lojas.data = usuario.sistema_lojas` (preenchimento GET) também.

- [ ] **Step 2: Adicionar em route `aprovar_usuario` (POST e GET)**

POST (após `usuario.sistema_lojas = form.sistema_lojas.data`):
```python
            usuario.sistema_motos_assai = form.sistema_motos_assai.data
```

GET (após `form.sistema_lojas.data = usuario.sistema_lojas`):
```python
        form.sistema_motos_assai.data = usuario.sistema_motos_assai
```

- [ ] **Step 3: Adicionar em route `editar_usuario` (mesma lógica)**

Idêntico ao Step 2 mas em `def editar_usuario`.

- [ ] **Step 4: Validar via REPL — criar e editar usuário com flag**

```bash
python -c "
from app import create_app, db
from app.auth.models import Usuario
app = create_app()
with app.app_context():
    u = Usuario.query.filter_by(email='admin@example.com').first()
    if u:
        antes = u.sistema_motos_assai
        u.sistema_motos_assai = not antes
        db.session.commit()
        u2 = Usuario.query.get(u.id)
        print(f'Toggle OK: {antes} -> {u2.sistema_motos_assai}')
        u2.sistema_motos_assai = antes
        db.session.commit()
"
```

Expected: `Toggle OK: <bool> -> <bool>` (alternou).

- [ ] **Step 5: Commit**

```bash
git add app/auth/routes.py
git commit -m "feat(auth): wire sistema_motos_assai in aprovar/editar usuario routes"
```

---

## Task 16: Atualizar `auth/utils.py` — redirect pós-login

**Files:**
- Modify: `app/auth/utils.py`

- [ ] **Step 1: Localizar `url_primeiro_dashboard_disponivel`**

```bash
grep -n "url_primeiro_dashboard_disponivel\|sistema_lojas\|sistema_carvia" app/auth/utils.py
```

- [ ] **Step 2: Adicionar prioridade entre Hora e CarVia**

Logo após o bloco `if getattr(user, 'sistema_lojas', False): return url_for('hora.dashboard')` (ou similar), adicionar:

```python
    if getattr(user, 'sistema_motos_assai', False):
        return url_for('motos_assai.dashboard')
```

(A prioridade exata é `lojas → motochefe → motos_assai → carvia → comercial → pessoal` conforme spec §7.5.)

- [ ] **Step 3: Validar**

```bash
python -c "
from app import create_app, db
from app.auth.models import Usuario
from app.auth.utils import url_primeiro_dashboard_disponivel
app = create_app()
with app.app_context():
    u = Usuario(email='x@x', nome='X', senha_hash='x', status='ativo',
                sistema_motos_assai=True, perfil='vendedor')
    with app.test_request_context():
        url = url_primeiro_dashboard_disponivel(u)
    print('URL pós-login user motos_assai-only:', url)
"
```

Expected: `/motos-assai/` (após Task 19, no dashboard ficar disponível). Por enquanto pode dar erro `BuildError` — ok, se cai em qualquer URL de Hora/Carvia/etc é porque a rota dashboard ainda não existe. Validamos em Task 19.

- [ ] **Step 4: Commit**

```bash
git add app/auth/utils.py
git commit -m "feat(auth): redirect motos_assai-only users to /motos-assai dashboard"
```

---

## Task 17: Atualizar `editar_usuario.html` — checkbox visual

**Files:**
- Modify: `app/templates/auth/editar_usuario.html`

- [ ] **Step 1: Localizar checkbox sistema_lojas**

```bash
grep -n "sistemasLojas\|sistema_lojas" app/templates/auth/editar_usuario.html
```

- [ ] **Step 2: Adicionar checkbox novo logo após o de Hora**

```html
<div class="form-check mb-2">
    {{ form.sistema_motos_assai(class="form-check-input", id="sistemaMotosAssai") }}
    {{ form.sistema_motos_assai.label(class="form-check-label", for="sistemaMotosAssai") }}
</div>
```

- [ ] **Step 3: Adicionar mesmo bloco em `aprovar_usuario.html` se existir**

```bash
ls app/templates/auth/ | grep -E "(aprovar|editar)"
```

Adicionar no template de aprovação também (Task 14 garantiu que o form tem o campo).

- [ ] **Step 4: Commit**

```bash
git add app/templates/auth/editar_usuario.html
# se aprovar_usuario.html existe:
git add app/templates/auth/aprovar_usuario.html 2>/dev/null
git commit -m "feat(auth): add Motos Assai checkbox to user edit/approve UI"
```

---

## Task 18: Adicionar item de menu no `base.html`

**Files:**
- Modify: `app/templates/base.html`

- [ ] **Step 1: Localizar bloco de Hora no menu**

```bash
grep -n "pode_acessar_lojas\|Lojas HORA" app/templates/base.html | head -5
```

- [ ] **Step 2: Adicionar item de menu logo após o bloco do Hora**

```jinja
{% if current_user.is_authenticated and current_user.pode_acessar_motos_assai() %}
  <li>
    <a class="dropdown-item" href="{{ url_for('motos_assai.dashboard') }}">
      <i class="fas fa-motorcycle"></i> Motos Assaí
    </a>
  </li>
{% endif %}
```

- [ ] **Step 3: Validar render do app**

```bash
python -c "
from app import create_app
app = create_app()
with app.test_client() as c:
    r = c.get('/auth/login')
    print('Login page status:', r.status_code)
"
```

Expected: `Login page status: 200`

- [ ] **Step 4: Commit**

```bash
git add app/templates/base.html
git commit -m "feat(menu): add Motos Assai entry conditional on permission"
```

---

## Task 19: Dashboard rota + template + CSS

**Files:**
- Create: `app/motos_assai/routes/dashboard.py`
- Modify: `app/motos_assai/routes/__init__.py`
- Create: `app/templates/motos_assai/base_motos_assai.html`
- Create: `app/templates/motos_assai/dashboard.html`
- Create: `app/static/css/modules/_motos_assai.css`
- Modify: `app/static/css/main.css` (importar)

- [ ] **Step 1: Criar route**

`app/motos_assai/routes/dashboard.py`:

```python
from flask import render_template
from flask_login import login_required, current_user
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.models import (
    AssaiCd, AssaiLoja, AssaiModelo, AssaiPedidoVenda,
    AssaiCompraMotochefe, AssaiSeparacao,
    PEDIDO_STATUS_VALIDOS,
)
from app import db
from sqlalchemy import func


@motos_assai_bp.route('/')
@login_required
@require_motos_assai
def dashboard():
    """Dashboard inicial — métricas básicas. Será enriquecido nos Planos 2 e 3."""
    cd = AssaiCd.query.filter_by(ativo=True).first()
    lojas_ativas = AssaiLoja.query.filter_by(ativo=True).count()
    modelos_ativos = AssaiModelo.query.filter_by(ativo=True).count()

    # Counts por status (placeholder — vazio até Plano 2)
    pedidos_por_status = dict(
        db.session.query(AssaiPedidoVenda.status, func.count(AssaiPedidoVenda.id))
        .group_by(AssaiPedidoVenda.status)
        .all()
    )
    compras_abertas = AssaiCompraMotochefe.query.filter_by(status='ABERTA').count()
    separacoes_em = AssaiSeparacao.query.filter_by(status='EM_SEPARACAO').count()

    return render_template(
        'motos_assai/dashboard.html',
        cd=cd,
        lojas_ativas=lojas_ativas,
        modelos_ativos=modelos_ativos,
        pedidos_por_status=pedidos_por_status,
        compras_abertas=compras_abertas,
        separacoes_em=separacoes_em,
    )
```

- [ ] **Step 2: Importar route no blueprint __init__**

Em `app/motos_assai/routes/__init__.py`, adicionar ao final:

```python
# Importar sub-rotas (registra handlers no blueprint)
from app.motos_assai.routes import dashboard  # noqa: E402,F401
```

- [ ] **Step 3: Criar template base**

`app/templates/motos_assai/base_motos_assai.html`:

```jinja
{% extends "base.html" %}

{% block title %}Motos Assaí{% endblock %}

{% block content %}
<div class="container-fluid motos-assai-wrapper py-3">
  <nav class="motos-assai-nav mb-3">
    <a class="motos-assai-nav-link" href="{{ url_for('motos_assai.dashboard') }}">
      <i class="fas fa-tachometer-alt"></i> Dashboard
    </a>
    {# Links adicionais conforme rotas forem criadas (Plano 2 e 3) #}
  </nav>

  {% block motos_assai_content %}{% endblock %}
</div>
{% endblock %}
```

- [ ] **Step 4: Criar template dashboard**

`app/templates/motos_assai/dashboard.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<div class="motos-assai-dashboard">
  <header class="dashboard-header">
    <h2>Operação VOE
      {% if cd %}<small class="text-muted"> · CD: {{ cd.nome }}</small>{% endif %}
    </h2>
  </header>

  <section class="dashboard-cards row g-3">
    <div class="col-md-3">
      <div class="card dashboard-card">
        <div class="card-body">
          <h6 class="card-subtitle text-muted">Cadastros</h6>
          <p class="card-text">
            <strong>{{ lojas_ativas }}</strong> lojas ativas<br>
            <strong>{{ modelos_ativos }}</strong> modelos ativos
          </p>
        </div>
      </div>
    </div>

    <div class="col-md-3">
      <div class="card dashboard-card">
        <div class="card-body">
          <h6 class="card-subtitle text-muted">Pedidos por status</h6>
          {% if pedidos_por_status %}
            <ul class="list-unstyled mb-0">
              {% for status, count in pedidos_por_status.items() %}
                <li>{{ status }}: <strong>{{ count }}</strong></li>
              {% endfor %}
            </ul>
          {% else %}
            <p class="card-text text-muted">Sem pedidos cadastrados.</p>
          {% endif %}
        </div>
      </div>
    </div>

    <div class="col-md-3">
      <div class="card dashboard-card">
        <div class="card-body">
          <h6 class="card-subtitle text-muted">Pipeline</h6>
          <p class="card-text">
            <strong>{{ compras_abertas }}</strong> compras Motochefe abertas<br>
            <strong>{{ separacoes_em }}</strong> separações em andamento
          </p>
        </div>
      </div>
    </div>

    <div class="col-md-3">
      <div class="card dashboard-card">
        <div class="card-body">
          <h6 class="card-subtitle text-muted">Atalhos</h6>
          <p class="card-text text-muted">
            (rotas habilitadas no Plano 2: pedidos, compras, recibos, recebimento)
          </p>
        </div>
      </div>
    </div>
  </section>
</div>
{% endblock %}
```

- [ ] **Step 5: CSS do módulo**

`app/static/css/modules/_motos_assai.css`:

```css
/* ============================================================
   Módulo Motos Assaí — estilos
   Usa design tokens de tokens/_design-tokens.css (light/dark).
   Sem cores hardcoded.
   ============================================================ */

.motos-assai-wrapper {
  background: var(--bg-light);
  color: var(--text);
  min-height: calc(100vh - var(--navbar-h, 56px));
}

.motos-assai-nav {
  display: flex;
  gap: 1rem;
  padding: 0.75rem 1rem;
  background: var(--surface);
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
}

.motos-assai-nav-link {
  color: var(--text);
  text-decoration: none;
  padding: 0.25rem 0.75rem;
  border-radius: var(--radius-sm);
  transition: background-color 120ms ease;
}

.motos-assai-nav-link:hover {
  background: var(--bg-hover);
  color: var(--text);
}

.dashboard-header {
  margin-bottom: 1rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid var(--border);
}

.dashboard-header h2 {
  color: var(--text);
  font-weight: 600;
}

.dashboard-card {
  background: var(--surface);
  border: 1px solid var(--border);
  height: 100%;
}

.dashboard-card .card-subtitle {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}
```

- [ ] **Step 6: Importar no main.css**

Localizar a seção `@layer modules` em `app/static/css/main.css` e adicionar:

```css
@import url("modules/_motos_assai.css") layer(modules);
```

(Verificar padrão exato dos demais imports — copiar idêntico.)

- [ ] **Step 7: Validar dashboard responde**

```bash
python -c "
from app import create_app, db
from app.auth.models import Usuario
app = create_app()
with app.app_context():
    u = Usuario.query.filter_by(perfil='administrador').first()
    if not u:
        print('Sem admin cadastrado para teste')
    else:
        with app.test_client() as c:
            with c.session_transaction() as sess:
                sess['_user_id'] = str(u.id)
                sess['_fresh'] = True
            r = c.get('/motos-assai/')
            print('Status dashboard:', r.status_code)
            print('Tem Operação VOE no body:', b'Opera' in r.data)
"
```

Expected: `Status dashboard: 200`, `Tem Operação VOE no body: True`

- [ ] **Step 8: Commit**

```bash
git add app/motos_assai/routes/dashboard.py app/motos_assai/routes/__init__.py
git add app/templates/motos_assai/base_motos_assai.html app/templates/motos_assai/dashboard.html
git add app/static/css/modules/_motos_assai.css app/static/css/main.css
git commit -m "feat(motos_assai): add dashboard route, base template, and module CSS"
```

---

## Task 20: Migration seed CD

**Files:**
- Create: `scripts/migrations/motos_assai_03_seed_cd.py`

**Decidido em 2026-05-07**: campos opcionais. Cria CD com apenas `nome='Operação VOE'`. Endereço/CNPJ podem ser preenchidos depois via tela admin (Task 25).

- [ ] **Step 1: Criar seed**

`scripts/migrations/motos_assai_03_seed_cd.py`:

```python
"""
Migration: Seed do CD único 'Operação VOE'
==========================================
Executar: python scripts/migrations/motos_assai_03_seed_cd.py

Cria 1 CD com nome 'Operação VOE'. Endereço/CNPJ ficam vazios e
podem ser preenchidos via tela admin (`/motos-assai/cd/editar`).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from app.motos_assai.models import AssaiCd


CD_DADOS = {
    'nome': 'Operação VOE',
    'cnpj': None,
    'endereco': None,
    'bairro': None,
    'cep': None,
    'cidade': None,
    'uf': None,
    'ativo': True,
}


def seed_cd():
    app = create_app()
    with app.app_context():
        existente = AssaiCd.query.filter_by(nome=CD_DADOS['nome']).first()
        if existente:
            print(f"CD '{CD_DADOS['nome']}' já existe (id={existente.id}). Nada a fazer.")
            return

        cd = AssaiCd(**CD_DADOS)
        db.session.add(cd)
        db.session.commit()
        print(f"CD criado: id={cd.id} nome={cd.nome}")


if __name__ == '__main__':
    seed_cd()
```

- [ ] **Step 2: Executar local**

```bash
python scripts/migrations/motos_assai_03_seed_cd.py
```

Expected: `CD criado: id=1 nome=Operação VOE`

- [ ] **Step 3: Commit**

```bash
git add scripts/migrations/motos_assai_03_seed_cd.py
git commit -m "feat(motos_assai): seed CD 'Operação VOE'"
```

---

## Task 21: Migration seed lojas (39 lojas Assaí)

**Files:**
- Create: `scripts/migrations/motos_assai_04_seed_lojas.py`
- Reference: `/mnt/c/Users/rafael.nascimento/Downloads/285.xlsx` aba `BASE LOJAS`

- [ ] **Step 1: Extrair dados da planilha (one-shot, gera lista Python)**

```bash
python -c "
import openpyxl
wb = openpyxl.load_workbook('/mnt/c/Users/rafael.nascimento/Downloads/285.xlsx', data_only=True)
ws = wb['BASE LOJAS']
print('LOJAS_DATA = [')
for row in ws.iter_rows(min_row=2, values_only=True):
    if row[0] is None:
        continue
    numero, nome, regional, cnpj, ie, razao, end, bairro, cep, cidade, uf = row[:11]
    nome_s = (str(nome).strip() if nome else None)
    cnpj_s = (str(cnpj).strip() if cnpj else None)
    ie_s = (str(ie).strip() if ie else None)
    razao_s = (str(razao).strip() if razao else None)
    end_s = (str(end).strip() if end else None)
    bairro_s = (str(bairro).strip() if bairro else None)
    cep_s = (str(cep).strip() if cep else None)
    cidade_s = (str(cidade).strip() if cidade else None)
    uf_s = (str(uf).strip() if uf else None)
    regional_s = (str(regional).strip() if regional else None)
    print(f'    dict(numero={str(numero)!r}, nome={nome_s!r}, razao_social={razao_s!r}, cnpj={cnpj_s!r}, ie={ie_s!r}, endereco={end_s!r}, bairro={bairro_s!r}, cep={cep_s!r}, cidade={cidade_s!r}, uf={uf_s!r}, regional={regional_s!r}),')
print(']')
" > /tmp/lojas_data.py
wc -l /tmp/lojas_data.py
```

Expected: ~41 linhas (39 lojas + 2 de wrapper).

- [ ] **Step 2: Criar seed**

`scripts/migrations/motos_assai_04_seed_lojas.py`:

```python
"""
Migration: Seed das 39 lojas Assaí (extraídas de 285.xlsx aba BASE LOJAS)
=========================================================================
Executar: python scripts/migrations/motos_assai_04_seed_lojas.py

Idempotente: cria apenas lojas com `numero` ainda inexistente.
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from app.motos_assai.models import AssaiLoja


# COLAR aqui o output do step 1 (lista LOJAS_DATA gerada)
LOJAS_DATA = [
    # exemplo (substituir pelo output real):
    # dict(numero='12', nome='JUNDIAÍ', razao_social='SENDAS DISTRIBUIDORA S/A LJ12',
    #      cnpj='06.057.223/0272-90', ie='407546146113',
    #      endereco='RUA QUINZE DE NOVEMBRO-430', bairro='CENTRO',
    #      cep='13201-005', cidade='JUNDIAÍ', uf='SP',
    #      regional='SP7-JUNDIAÍ/SOROCABA'),
    # ... 38 outras
]


def seed_lojas():
    app = create_app()
    with app.app_context():
        existentes = {l.numero for l in AssaiLoja.query.all()}
        novas = []
        for dados in LOJAS_DATA:
            if dados['numero'] in existentes:
                continue
            novas.append(AssaiLoja(**dados))

        if not novas:
            print(f"Todas as {len(LOJAS_DATA)} lojas já existem. Nada a fazer.")
            return

        db.session.add_all(novas)
        db.session.commit()
        print(f"OK: {len(novas)} lojas inseridas. Total agora: {AssaiLoja.query.count()}")


if __name__ == '__main__':
    seed_lojas()
```

- [ ] **Step 3: Substituir `LOJAS_DATA` pelo output real**

Copiar o conteúdo de `/tmp/lojas_data.py` (gerado no Step 1) para o lugar da lista.

- [ ] **Step 4: Executar**

```bash
python scripts/migrations/motos_assai_04_seed_lojas.py
```

Expected: `OK: 39 lojas inseridas. Total agora: 39`

- [ ] **Step 5: Validar**

```bash
python -c "
from app import create_app
from app.motos_assai.models import AssaiLoja
app = create_app()
with app.app_context():
    print('Total lojas:', AssaiLoja.query.count())
    for l in AssaiLoja.query.order_by(AssaiLoja.numero).limit(5):
        print(f'  {l.numero} {l.nome} ({l.uf})')
"
```

Expected: 39 lojas, primeira deve ser número 12 (JUNDIAÍ).

- [ ] **Step 6: Commit**

```bash
git add scripts/migrations/motos_assai_04_seed_lojas.py
git commit -m "feat(motos_assai): seed 39 Assaí stores from 285.xlsx BASE LOJAS"
```

---

## Task 22: Migration seed modelos (X11_MINI, DOT, SOL)

**Files:**
- Create: `scripts/migrations/motos_assai_05_seed_modelos.py`

**Regex aprovados em 2026-05-07** (duráveis, ano/mês variáveis, com colisão admitida em `LA*V1000W*`):
- `X11_MINI`: `^(MCBRX11M\d{9}|LA\d+V1000W\d{4})$`
- `DOT`: `^(LA\d+SA\d+\d{5}|LA\d+V1000W\d{4}|HL5TCAH3[0-9X]S9W57\d{3}|MCBRDOT\d{10})$`
- `SOL`: `^17292\d{10}$`

- [ ] **Step 1: Criar seed**

`scripts/migrations/motos_assai_05_seed_modelos.py`:

```python
"""
Migration: Seed dos 3 modelos canônicos (X11 MINI, DOT, SOL) + aliases
======================================================================
Executar: python scripts/migrations/motos_assai_05_seed_modelos.py

regex_chassi: PREENCHER após dono enviar máscaras (Claude monta os regex).
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from app.motos_assai.models import (
    AssaiModelo, AssaiModeloAlias,
    ALIAS_TIPO_NOME_LIVRE, ALIAS_TIPO_CODIGO_QPA, ALIAS_TIPO_DESCRICAO_RECIBO,
)


MODELOS = [
    {
        'codigo': 'X11_MINI',
        'nome': 'X11 MINI 1000W',
        'descricao_qpa': 'AUTOPROPELIDO X11 MINI 1000W 60V 20AH',
        'codigo_qpa': '1342056',
        # Aprovado 2026-05-07: cobre X11M-A (MCBRX11M+9 dígitos) e X11M-B (LA+ano/mês+V1000W+4 dígitos).
        # Colisão admitida com DOT no padrão LA*V1000W* — modelo vem do recibo Motochefe.
        'regex_chassi': r'^(MCBRX11M\d{9}|LA\d+V1000W\d{4})$',
        'aliases': [
            ('X11 NAC', ALIAS_TIPO_NOME_LIVRE),
            ('X11 MINI', ALIAS_TIPO_NOME_LIVRE),
            ('X11', ALIAS_TIPO_NOME_LIVRE),
            ('AUTOPROPELIDO X11 MINI 1000W', ALIAS_TIPO_DESCRICAO_RECIBO),
            ('AUTOPROPELIDO X11 MINI 1000W 60V 20AH', ALIAS_TIPO_DESCRICAO_RECIBO),
            ('1342056', ALIAS_TIPO_CODIGO_QPA),
        ],
    },
    {
        'codigo': 'DOT',
        'nome': 'DOT 1000W',
        'descricao_qpa': 'AUTOPROPELIDO DOT 1000W 60V 20AH',
        'codigo_qpa': '1342059',
        # Aprovado 2026-05-07: 4 alternativas — DOT-A (LA*SA*+5dig), DOT-B/C (LA*V1000W*+4dig),
        # DOT-D (HL5TCAH3 VIN-like), DOT-E (MCBRDOT+10dig).
        'regex_chassi': r'^(LA\d+SA\d+\d{5}|LA\d+V1000W\d{4}|HL5TCAH3[0-9X]S9W57\d{3}|MCBRDOT\d{10})$',
        'aliases': [
            ('DOT', ALIAS_TIPO_NOME_LIVRE),
            ('DOT 1000W', ALIAS_TIPO_NOME_LIVRE),
            ('AUTOPROPELIDO DOT 1000W', ALIAS_TIPO_DESCRICAO_RECIBO),
            ('AUTOPROPELIDO DOT 1000W 60V 20AH', ALIAS_TIPO_DESCRICAO_RECIBO),
            ('1342059', ALIAS_TIPO_CODIGO_QPA),
        ],
    },
    {
        'codigo': 'SOL',
        'nome': 'SOL 1000W',
        'descricao_qpa': 'AUTOPROPELIDO SOL 1000W 60V 20AH',
        'codigo_qpa': '1342063',
        # Aprovado 2026-05-07: 15 dígitos numéricos começando com 17292.
        # Cobre lotes diferentes (17292250467*, 17292251217*, etc.) sem manutenção.
        'regex_chassi': r'^17292\d{10}$',
        'aliases': [
            ('SOL', ALIAS_TIPO_NOME_LIVRE),
            ('SOL 1000W', ALIAS_TIPO_NOME_LIVRE),
            ('AUTOPROPELIDO SOL 1000W', ALIAS_TIPO_DESCRICAO_RECIBO),
            ('AUTOPROPELIDO SOL 1000W 60V 20AH', ALIAS_TIPO_DESCRICAO_RECIBO),
            ('1342063', ALIAS_TIPO_CODIGO_QPA),
        ],
    },
]


def seed_modelos():
    app = create_app()
    with app.app_context():
        criados = 0
        for m_data in MODELOS:
            existente = AssaiModelo.query.filter_by(codigo=m_data['codigo']).first()
            if existente:
                print(f"Modelo {m_data['codigo']} já existe (id={existente.id}).")
                continue

            aliases_data = m_data.pop('aliases')
            modelo = AssaiModelo(**m_data)
            for alias, tipo in aliases_data:
                modelo.aliases.append(AssaiModeloAlias(alias=alias, tipo=tipo))

            db.session.add(modelo)
            criados += 1

        db.session.commit()
        print(f"OK: {criados} modelos criados. Total: {AssaiModelo.query.count()}")
        print(f"Aliases criados: {AssaiModeloAlias.query.count()}")


if __name__ == '__main__':
    seed_modelos()
```

- [ ] **Step 2: Executar**

```bash
python scripts/migrations/motos_assai_05_seed_modelos.py
```

Expected: `OK: 3 modelos criados. Total: 3` / `Aliases criados: 12`

- [ ] **Step 3: Commit**

```bash
git add scripts/migrations/motos_assai_05_seed_modelos.py
git commit -m "feat(motos_assai): seed X11_MINI/DOT/SOL models with aliases"
```

---

## Task 23: CRUD Loja Assaí

**Files:**
- Create: `app/motos_assai/forms/loja_forms.py`
- Create: `app/motos_assai/forms/__init__.py`
- Create: `app/motos_assai/services/loja_service.py`
- Create: `app/motos_assai/services/__init__.py`
- Create: `app/motos_assai/routes/lojas.py`
- Modify: `app/motos_assai/routes/__init__.py`
- Create: `app/templates/motos_assai/lojas/lista.html`
- Create: `app/templates/motos_assai/lojas/form.html`
- Create: `app/templates/motos_assai/lojas/detalhe.html`
- Modify: `app/templates/motos_assai/base_motos_assai.html` (link no nav)

- [ ] **Step 1: Form**

`app/motos_assai/forms/loja_forms.py`:

```python
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Optional, Regexp


UFs = [
    ('AC','AC'),('AL','AL'),('AP','AP'),('AM','AM'),('BA','BA'),('CE','CE'),
    ('DF','DF'),('ES','ES'),('GO','GO'),('MA','MA'),('MT','MT'),('MS','MS'),
    ('MG','MG'),('PA','PA'),('PB','PB'),('PR','PR'),('PE','PE'),('PI','PI'),
    ('RJ','RJ'),('RN','RN'),('RS','RS'),('RO','RO'),('RR','RR'),('SC','SC'),
    ('SP','SP'),('SE','SE'),('TO','TO'),
]


class LojaForm(FlaskForm):
    numero = StringField('Número (LJ)', validators=[DataRequired(), Length(max=10)])
    nome = StringField('Nome', validators=[DataRequired(), Length(max=120)])
    razao_social = StringField('Razão Social', validators=[DataRequired(), Length(max=200)])
    cnpj = StringField('CNPJ', validators=[
        DataRequired(),
        Regexp(r'^\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}$',
               message='Use formato 00.000.000/0000-00'),
    ])
    ie = StringField('IE', validators=[Optional(), Length(max=20)])
    endereco = StringField('Endereço', validators=[Optional(), Length(max=255)])
    bairro = StringField('Bairro', validators=[Optional(), Length(max=80)])
    cep = StringField('CEP', validators=[Optional(), Length(max=10)])
    cidade = StringField('Cidade', validators=[Optional(), Length(max=80)])
    uf = SelectField('UF', choices=UFs, validators=[DataRequired()])
    regional = StringField('Regional', validators=[Optional(), Length(max=80)])
    ativo = BooleanField('Ativo', default=True)
```

- [ ] **Step 2: __init__ forms**

`app/motos_assai/forms/__init__.py`:

```python
from .loja_forms import LojaForm

__all__ = ['LojaForm']
```

- [ ] **Step 3: Service**

`app/motos_assai/services/loja_service.py`:

```python
from app import db
from app.motos_assai.models import AssaiLoja


class LojaJaExisteError(Exception):
    pass


def listar_lojas(somente_ativas: bool = False, busca: str | None = None):
    q = AssaiLoja.query
    if somente_ativas:
        q = q.filter_by(ativo=True)
    if busca:
        like = f'%{busca}%'
        q = q.filter(
            db.or_(
                AssaiLoja.numero.ilike(like),
                AssaiLoja.nome.ilike(like),
                AssaiLoja.cidade.ilike(like),
            )
        )
    return q.order_by(AssaiLoja.numero).all()


def criar_loja(dados: dict) -> AssaiLoja:
    if AssaiLoja.query.filter_by(numero=dados['numero']).first():
        raise LojaJaExisteError(f"Loja com número {dados['numero']} já existe")
    loja = AssaiLoja(**dados)
    db.session.add(loja)
    db.session.commit()
    return loja


def atualizar_loja(loja_id: int, dados: dict) -> AssaiLoja:
    loja = AssaiLoja.query.get_or_404(loja_id)
    for k, v in dados.items():
        if hasattr(loja, k):
            setattr(loja, k, v)
    db.session.commit()
    return loja


def get_loja(loja_id: int) -> AssaiLoja:
    return AssaiLoja.query.get_or_404(loja_id)
```

- [ ] **Step 4: __init__ services**

`app/motos_assai/services/__init__.py`:

```python
from .loja_service import (
    listar_lojas, criar_loja, atualizar_loja, get_loja, LojaJaExisteError,
)

__all__ = [
    'listar_lojas', 'criar_loja', 'atualizar_loja', 'get_loja',
    'LojaJaExisteError',
]
```

- [ ] **Step 5: Rotas**

`app/motos_assai/routes/lojas.py`:

```python
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms import LojaForm
from app.motos_assai.services import (
    listar_lojas, criar_loja, atualizar_loja, get_loja, LojaJaExisteError,
)


@motos_assai_bp.route('/lojas')
@login_required
@require_motos_assai
def lojas_lista():
    busca = request.args.get('q', '').strip() or None
    somente_ativas = request.args.get('ativas') == '1'
    lojas = listar_lojas(somente_ativas=somente_ativas, busca=busca)
    return render_template('motos_assai/lojas/lista.html',
                           lojas=lojas, busca=busca, somente_ativas=somente_ativas)


@motos_assai_bp.route('/lojas/nova', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def lojas_nova():
    form = LojaForm()
    if form.validate_on_submit():
        try:
            loja = criar_loja({
                'numero': form.numero.data.strip(),
                'nome': form.nome.data.strip(),
                'razao_social': form.razao_social.data.strip(),
                'cnpj': form.cnpj.data.strip(),
                'ie': form.ie.data.strip() if form.ie.data else None,
                'endereco': form.endereco.data.strip() if form.endereco.data else None,
                'bairro': form.bairro.data.strip() if form.bairro.data else None,
                'cep': form.cep.data.strip() if form.cep.data else None,
                'cidade': form.cidade.data.strip() if form.cidade.data else None,
                'uf': form.uf.data,
                'regional': form.regional.data.strip() if form.regional.data else None,
                'ativo': form.ativo.data,
            })
            flash(f'Loja {loja.numero} criada.', 'success')
            return redirect(url_for('motos_assai.lojas_detalhe', loja_id=loja.id))
        except LojaJaExisteError as e:
            flash(str(e), 'danger')
    return render_template('motos_assai/lojas/form.html', form=form, modo='nova')


@motos_assai_bp.route('/lojas/<int:loja_id>')
@login_required
@require_motos_assai
def lojas_detalhe(loja_id):
    loja = get_loja(loja_id)
    return render_template('motos_assai/lojas/detalhe.html', loja=loja)


@motos_assai_bp.route('/lojas/<int:loja_id>/editar', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def lojas_editar(loja_id):
    loja = get_loja(loja_id)
    form = LojaForm(obj=loja)
    if form.validate_on_submit():
        atualizar_loja(loja_id, {
            'nome': form.nome.data.strip(),
            'razao_social': form.razao_social.data.strip(),
            'cnpj': form.cnpj.data.strip(),
            'ie': form.ie.data.strip() if form.ie.data else None,
            'endereco': form.endereco.data.strip() if form.endereco.data else None,
            'bairro': form.bairro.data.strip() if form.bairro.data else None,
            'cep': form.cep.data.strip() if form.cep.data else None,
            'cidade': form.cidade.data.strip() if form.cidade.data else None,
            'uf': form.uf.data,
            'regional': form.regional.data.strip() if form.regional.data else None,
            'ativo': form.ativo.data,
        })
        flash(f'Loja {loja.numero} atualizada.', 'success')
        return redirect(url_for('motos_assai.lojas_detalhe', loja_id=loja_id))
    return render_template('motos_assai/lojas/form.html', form=form, loja=loja, modo='editar')
```

- [ ] **Step 6: Importar route no blueprint**

Em `app/motos_assai/routes/__init__.py`, ao final:

```python
from app.motos_assai.routes import lojas  # noqa: E402,F401
```

- [ ] **Step 7: Templates lista**

`app/templates/motos_assai/lojas/lista.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<header class="d-flex justify-content-between align-items-center mb-3">
  <h2>Lojas Assaí</h2>
  <a href="{{ url_for('motos_assai.lojas_nova') }}" class="btn btn-primary">
    <i class="fas fa-plus"></i> Nova loja
  </a>
</header>

<form method="GET" class="row g-2 mb-3">
  <div class="col-md-6">
    <input type="text" name="q" value="{{ busca or '' }}" class="form-control"
           placeholder="Buscar por número, nome ou cidade...">
  </div>
  <div class="col-md-3 d-flex align-items-center">
    <div class="form-check">
      <input type="checkbox" name="ativas" value="1" id="ativas"
             {% if somente_ativas %}checked{% endif %} class="form-check-input">
      <label for="ativas" class="form-check-label">Somente ativas</label>
    </div>
  </div>
  <div class="col-md-3">
    <button class="btn btn-outline-secondary w-100">Filtrar</button>
  </div>
</form>

<table class="table table-hover">
  <thead>
    <tr>
      <th>Nº</th><th>Nome</th><th>CNPJ</th><th>Cidade</th><th>UF</th>
      <th>Regional</th><th>Status</th>
    </tr>
  </thead>
  <tbody>
    {% for l in lojas %}
    <tr>
      <td><a href="{{ url_for('motos_assai.lojas_detalhe', loja_id=l.id) }}">{{ l.numero }}</a></td>
      <td>{{ l.nome }}</td>
      <td>{{ l.cnpj }}</td>
      <td>{{ l.cidade or '-' }}</td>
      <td>{{ l.uf or '-' }}</td>
      <td>{{ l.regional or '-' }}</td>
      <td>
        {% if l.ativo %}
          <span class="badge bg-success">ATIVA</span>
        {% else %}
          <span class="badge bg-secondary">INATIVA</span>
        {% endif %}
      </td>
    </tr>
    {% else %}
    <tr><td colspan="7" class="text-center text-muted">Nenhuma loja.</td></tr>
    {% endfor %}
  </tbody>
</table>

<p class="text-muted">Total: {{ lojas|length }} loja(s)</p>
{% endblock %}
```

- [ ] **Step 8: Template form**

`app/templates/motos_assai/lojas/form.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<h2>{% if modo == 'nova' %}Nova loja{% else %}Editar loja {{ loja.numero }}{% endif %}</h2>

<form method="POST" class="row g-3">
  {{ form.hidden_tag() }}

  <div class="col-md-3">
    {{ form.numero.label(class="form-label") }}
    {{ form.numero(class="form-control") }}
    {% for e in form.numero.errors %}<div class="text-danger small">{{ e }}</div>{% endfor %}
  </div>

  <div class="col-md-9">
    {{ form.nome.label(class="form-label") }}
    {{ form.nome(class="form-control") }}
    {% for e in form.nome.errors %}<div class="text-danger small">{{ e }}</div>{% endfor %}
  </div>

  <div class="col-12">
    {{ form.razao_social.label(class="form-label") }}
    {{ form.razao_social(class="form-control") }}
  </div>

  <div class="col-md-4">
    {{ form.cnpj.label(class="form-label") }}
    {{ form.cnpj(class="form-control", placeholder="00.000.000/0000-00") }}
    {% for e in form.cnpj.errors %}<div class="text-danger small">{{ e }}</div>{% endfor %}
  </div>

  <div class="col-md-4">
    {{ form.ie.label(class="form-label") }}
    {{ form.ie(class="form-control") }}
  </div>

  <div class="col-md-4">
    {{ form.regional.label(class="form-label") }}
    {{ form.regional(class="form-control") }}
  </div>

  <div class="col-12">
    {{ form.endereco.label(class="form-label") }}
    {{ form.endereco(class="form-control") }}
  </div>

  <div class="col-md-3">
    {{ form.bairro.label(class="form-label") }}
    {{ form.bairro(class="form-control") }}
  </div>
  <div class="col-md-2">
    {{ form.cep.label(class="form-label") }}
    {{ form.cep(class="form-control") }}
  </div>
  <div class="col-md-5">
    {{ form.cidade.label(class="form-label") }}
    {{ form.cidade(class="form-control") }}
  </div>
  <div class="col-md-2">
    {{ form.uf.label(class="form-label") }}
    {{ form.uf(class="form-select") }}
  </div>

  <div class="col-12 form-check ms-3">
    {{ form.ativo(class="form-check-input") }}
    {{ form.ativo.label(class="form-check-label") }}
  </div>

  <div class="col-12">
    <button type="submit" class="btn btn-primary">Salvar</button>
    <a href="{{ url_for('motos_assai.lojas_lista') }}" class="btn btn-outline-secondary">Cancelar</a>
  </div>
</form>
{% endblock %}
```

- [ ] **Step 9: Template detalhe**

`app/templates/motos_assai/lojas/detalhe.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<header class="d-flex justify-content-between mb-3">
  <h2>Loja {{ loja.numero }} — {{ loja.nome }}
    {% if loja.ativo %}<span class="badge bg-success">ATIVA</span>
    {% else %}<span class="badge bg-secondary">INATIVA</span>{% endif %}
  </h2>
  <a href="{{ url_for('motos_assai.lojas_editar', loja_id=loja.id) }}" class="btn btn-outline-primary">
    <i class="fas fa-edit"></i> Editar
  </a>
</header>

<dl class="row">
  <dt class="col-sm-3">Razão Social</dt><dd class="col-sm-9">{{ loja.razao_social }}</dd>
  <dt class="col-sm-3">CNPJ</dt><dd class="col-sm-9">{{ loja.cnpj }}</dd>
  <dt class="col-sm-3">IE</dt><dd class="col-sm-9">{{ loja.ie or '-' }}</dd>
  <dt class="col-sm-3">Endereço</dt>
  <dd class="col-sm-9">{{ loja.endereco or '-' }}{% if loja.bairro %} — {{ loja.bairro }}{% endif %}</dd>
  <dt class="col-sm-3">Cidade/UF</dt>
  <dd class="col-sm-9">{{ loja.cidade or '-' }}/{{ loja.uf or '-' }} {% if loja.cep %}— CEP {{ loja.cep }}{% endif %}</dd>
  <dt class="col-sm-3">Regional</dt><dd class="col-sm-9">{{ loja.regional or '-' }}</dd>
  <dt class="col-sm-3">Criada em</dt><dd class="col-sm-9">{{ loja.criado_em.strftime('%d/%m/%Y %H:%M') }}</dd>
</dl>

<a href="{{ url_for('motos_assai.lojas_lista') }}" class="btn btn-outline-secondary">Voltar</a>
{% endblock %}
```

- [ ] **Step 10: Adicionar link no nav**

Em `app/templates/motos_assai/base_motos_assai.html`, adicionar no `<nav>`:

```jinja
    <a class="motos-assai-nav-link" href="{{ url_for('motos_assai.lojas_lista') }}">
      <i class="fas fa-store"></i> Lojas
    </a>
```

- [ ] **Step 11: Validar funcional**

```bash
python -c "
from app import create_app
from app.auth.models import Usuario
app = create_app()
with app.app_context():
    u = Usuario.query.filter_by(perfil='administrador').first()
    with app.test_client() as c:
        with c.session_transaction() as s:
            s['_user_id'] = str(u.id); s['_fresh'] = True
        r = c.get('/motos-assai/lojas')
        print('Lista lojas status:', r.status_code, '— body has 39:', b'39 loja' in r.data or len(r.data) > 1000)
"
```

Expected: `Lista lojas status: 200`

- [ ] **Step 12: Commit**

```bash
git add app/motos_assai/forms/ app/motos_assai/services/ app/motos_assai/routes/lojas.py
git add app/motos_assai/routes/__init__.py app/templates/motos_assai/lojas/ app/templates/motos_assai/base_motos_assai.html
git commit -m "feat(motos_assai): CRUD AssaiLoja (lista, novo, detalhe, editar)"
```

---

## Task 24: CRUD Modelo + tela admin de regex_chassi

**Files:**
- Create: `app/motos_assai/forms/modelo_forms.py`
- Modify: `app/motos_assai/forms/__init__.py`
- Create: `app/motos_assai/services/modelo_service.py`
- Modify: `app/motos_assai/services/__init__.py`
- Create: `app/motos_assai/routes/modelos.py`
- Modify: `app/motos_assai/routes/__init__.py`
- Create: `app/templates/motos_assai/modelos/lista.html`
- Create: `app/templates/motos_assai/modelos/form.html`
- Create: `app/templates/motos_assai/modelos/detalhe.html`
- Modify: `app/templates/motos_assai/base_motos_assai.html`

- [ ] **Step 1: Form**

`app/motos_assai/forms/modelo_forms.py`:

```python
import re
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField
from wtforms.validators import DataRequired, Length, Optional, ValidationError


def validar_regex_python(form, field):
    if not field.data:
        return
    try:
        re.compile(field.data)
    except re.error as e:
        raise ValidationError(f'Regex inválido: {e}')


class ModeloForm(FlaskForm):
    codigo = StringField('Código canônico', validators=[
        DataRequired(),
        Length(max=30),
    ])
    nome = StringField('Nome', validators=[DataRequired(), Length(max=80)])
    descricao_qpa = StringField('Descrição Q.P.A.', validators=[Optional(), Length(max=200)])
    codigo_qpa = StringField('Código no sistema Q.P.A.', validators=[Optional(), Length(max=20)])
    regex_chassi = StringField('Regex de validação de chassi (Python re)', validators=[
        Optional(), Length(max=120), validar_regex_python,
    ])
    ativo = BooleanField('Ativo', default=True)


class TestarRegexForm(FlaskForm):
    regex = StringField('Regex', validators=[DataRequired(), validar_regex_python])
    chassi = StringField('Chassi de teste', validators=[DataRequired()])
```

- [ ] **Step 2: Atualizar __init__ forms**

```python
from .loja_forms import LojaForm
from .modelo_forms import ModeloForm, TestarRegexForm

__all__ = ['LojaForm', 'ModeloForm', 'TestarRegexForm']
```

- [ ] **Step 3: Service**

`app/motos_assai/services/modelo_service.py`:

```python
import re
from app import db
from app.motos_assai.models import AssaiModelo


class ModeloJaExisteError(Exception):
    pass


def listar_modelos(somente_ativos: bool = False):
    q = AssaiModelo.query
    if somente_ativos:
        q = q.filter_by(ativo=True)
    return q.order_by(AssaiModelo.codigo).all()


def get_modelo(modelo_id: int) -> AssaiModelo:
    return AssaiModelo.query.get_or_404(modelo_id)


def criar_modelo(dados: dict) -> AssaiModelo:
    if AssaiModelo.query.filter_by(codigo=dados['codigo']).first():
        raise ModeloJaExisteError(f"Modelo {dados['codigo']} já existe")
    m = AssaiModelo(**dados)
    db.session.add(m)
    db.session.commit()
    return m


def atualizar_modelo(modelo_id: int, dados: dict) -> AssaiModelo:
    m = AssaiModelo.query.get_or_404(modelo_id)
    for k, v in dados.items():
        if hasattr(m, k):
            setattr(m, k, v)
    db.session.commit()
    return m


def testar_regex(regex: str, chassi: str) -> bool:
    """Valida se o chassi bate com o regex (anchors aplicados se faltarem)."""
    pattern = regex
    if not pattern.startswith('^'):
        pattern = '^' + pattern
    if not pattern.endswith('$'):
        pattern = pattern + '$'
    return bool(re.match(pattern, chassi))
```

- [ ] **Step 4: Atualizar __init__ services**

```python
from .loja_service import (
    listar_lojas, criar_loja, atualizar_loja, get_loja, LojaJaExisteError,
)
from .modelo_service import (
    listar_modelos, get_modelo, criar_modelo, atualizar_modelo,
    testar_regex, ModeloJaExisteError,
)

__all__ = [
    'listar_lojas', 'criar_loja', 'atualizar_loja', 'get_loja', 'LojaJaExisteError',
    'listar_modelos', 'get_modelo', 'criar_modelo', 'atualizar_modelo',
    'testar_regex', 'ModeloJaExisteError',
]
```

- [ ] **Step 5: Rotas**

`app/motos_assai/routes/modelos.py`:

```python
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms import ModeloForm, TestarRegexForm
from app.motos_assai.services import (
    listar_modelos, get_modelo, criar_modelo, atualizar_modelo,
    testar_regex, ModeloJaExisteError,
)


@motos_assai_bp.route('/modelos')
@login_required
@require_motos_assai
def modelos_lista():
    somente_ativos = request.args.get('ativos') == '1'
    modelos = listar_modelos(somente_ativos=somente_ativos)
    return render_template('motos_assai/modelos/lista.html',
                           modelos=modelos, somente_ativos=somente_ativos)


@motos_assai_bp.route('/modelos/novo', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def modelos_novo():
    form = ModeloForm()
    teste_form = TestarRegexForm()
    if form.validate_on_submit():
        try:
            m = criar_modelo({
                'codigo': form.codigo.data.strip().upper(),
                'nome': form.nome.data.strip(),
                'descricao_qpa': form.descricao_qpa.data.strip() if form.descricao_qpa.data else None,
                'codigo_qpa': form.codigo_qpa.data.strip() if form.codigo_qpa.data else None,
                'regex_chassi': form.regex_chassi.data.strip() if form.regex_chassi.data else None,
                'ativo': form.ativo.data,
            })
            flash(f'Modelo {m.codigo} criado.', 'success')
            return redirect(url_for('motos_assai.modelos_detalhe', modelo_id=m.id))
        except ModeloJaExisteError as e:
            flash(str(e), 'danger')
    return render_template('motos_assai/modelos/form.html',
                           form=form, teste_form=teste_form, modo='novo')


@motos_assai_bp.route('/modelos/<int:modelo_id>')
@login_required
@require_motos_assai
def modelos_detalhe(modelo_id):
    modelo = get_modelo(modelo_id)
    return render_template('motos_assai/modelos/detalhe.html', modelo=modelo)


@motos_assai_bp.route('/modelos/<int:modelo_id>/editar', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def modelos_editar(modelo_id):
    modelo = get_modelo(modelo_id)
    form = ModeloForm(obj=modelo)
    teste_form = TestarRegexForm()
    if form.validate_on_submit():
        atualizar_modelo(modelo_id, {
            'codigo': form.codigo.data.strip().upper(),
            'nome': form.nome.data.strip(),
            'descricao_qpa': form.descricao_qpa.data.strip() if form.descricao_qpa.data else None,
            'codigo_qpa': form.codigo_qpa.data.strip() if form.codigo_qpa.data else None,
            'regex_chassi': form.regex_chassi.data.strip() if form.regex_chassi.data else None,
            'ativo': form.ativo.data,
        })
        flash(f'Modelo {modelo.codigo} atualizado.', 'success')
        return redirect(url_for('motos_assai.modelos_detalhe', modelo_id=modelo_id))
    return render_template('motos_assai/modelos/form.html',
                           form=form, teste_form=teste_form, modelo=modelo, modo='editar')


@motos_assai_bp.route('/modelos/api/testar-regex', methods=['POST'])
@login_required
@require_motos_assai
def modelos_api_testar_regex():
    """Endpoint AJAX para testar regex contra chassi sem salvar."""
    data = request.get_json(silent=True) or {}
    regex = (data.get('regex') or '').strip()
    chassi = (data.get('chassi') or '').strip()
    if not regex or not chassi:
        return jsonify({'ok': False, 'erro': 'regex e chassi obrigatórios'}), 400
    try:
        bate = testar_regex(regex, chassi)
        return jsonify({'ok': True, 'bate': bate, 'regex': regex, 'chassi': chassi})
    except Exception as e:
        return jsonify({'ok': False, 'erro': f'regex inválido: {e}'}), 400
```

- [ ] **Step 6: Importar route no blueprint**

```python
from app.motos_assai.routes import modelos  # noqa: E402,F401
```

- [ ] **Step 7: Template lista**

`app/templates/motos_assai/modelos/lista.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<header class="d-flex justify-content-between mb-3">
  <h2>Modelos</h2>
  <a href="{{ url_for('motos_assai.modelos_novo') }}" class="btn btn-primary">
    <i class="fas fa-plus"></i> Novo modelo
  </a>
</header>

<table class="table">
  <thead>
    <tr>
      <th>Código</th><th>Nome</th><th>Descrição Q.P.A.</th><th>Código Q.P.A.</th>
      <th>Regex chassi</th><th>Aliases</th><th>Status</th>
    </tr>
  </thead>
  <tbody>
    {% for m in modelos %}
    <tr>
      <td><a href="{{ url_for('motos_assai.modelos_detalhe', modelo_id=m.id) }}">{{ m.codigo }}</a></td>
      <td>{{ m.nome }}</td>
      <td>{{ m.descricao_qpa or '-' }}</td>
      <td>{{ m.codigo_qpa or '-' }}</td>
      <td>
        {% if m.regex_chassi %}
          <code>{{ m.regex_chassi }}</code>
        {% else %}
          <span class="text-warning">não configurado</span>
        {% endif %}
      </td>
      <td>{{ m.aliases|length }}</td>
      <td>
        {% if m.ativo %}<span class="badge bg-success">ATIVO</span>
        {% else %}<span class="badge bg-secondary">INATIVO</span>{% endif %}
      </td>
    </tr>
    {% endfor %}
  </tbody>
</table>
{% endblock %}
```

- [ ] **Step 8: Template form com testador de regex inline**

`app/templates/motos_assai/modelos/form.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<h2>{% if modo == 'novo' %}Novo modelo{% else %}Editar modelo {{ modelo.codigo }}{% endif %}</h2>

<form method="POST" class="row g-3">
  {{ form.hidden_tag() }}

  <div class="col-md-3">
    {{ form.codigo.label(class="form-label") }}
    {{ form.codigo(class="form-control", placeholder="X11_MINI") }}
    {% for e in form.codigo.errors %}<div class="text-danger small">{{ e }}</div>{% endfor %}
  </div>
  <div class="col-md-9">
    {{ form.nome.label(class="form-label") }}
    {{ form.nome(class="form-control") }}
  </div>

  <div class="col-md-8">
    {{ form.descricao_qpa.label(class="form-label") }}
    {{ form.descricao_qpa(class="form-control") }}
  </div>
  <div class="col-md-4">
    {{ form.codigo_qpa.label(class="form-label") }}
    {{ form.codigo_qpa(class="form-control") }}
  </div>

  <div class="col-12">
    {{ form.regex_chassi.label(class="form-label") }}
    {{ form.regex_chassi(class="form-control", id="regex_chassi", placeholder="^LA2025SA1\\d+$") }}
    {% for e in form.regex_chassi.errors %}<div class="text-danger small">{{ e }}</div>{% endfor %}
    <small class="text-muted">Use anchors `^` e `$` para validação completa.</small>
  </div>

  <div class="col-12 form-check ms-3">
    {{ form.ativo(class="form-check-input") }}
    {{ form.ativo.label(class="form-check-label") }}
  </div>

  <div class="col-12">
    <button type="submit" class="btn btn-primary">Salvar</button>
    <a href="{{ url_for('motos_assai.modelos_lista') }}" class="btn btn-outline-secondary">Cancelar</a>
  </div>
</form>

<hr>

<h4>Testador de regex</h4>
<div class="row g-2">
  <div class="col-md-6">
    <input type="text" id="teste_chassi" class="form-control" placeholder="Chassi para testar (ex: LA2025SA110007354)">
  </div>
  <div class="col-md-2">
    <button type="button" class="btn btn-outline-info w-100" id="btn_testar">Testar</button>
  </div>
  <div class="col-md-4">
    <div id="resultado_teste" class="form-control-plaintext"></div>
  </div>
</div>

<script>
document.getElementById('btn_testar').addEventListener('click', async () => {
  const regex = document.getElementById('regex_chassi').value;
  const chassi = document.getElementById('teste_chassi').value;
  const resultEl = document.getElementById('resultado_teste');
  resultEl.textContent = '...';
  try {
    const r = await fetch('{{ url_for("motos_assai.modelos_api_testar_regex") }}', {
      method: 'POST',
      headers: {'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'},
      body: JSON.stringify({regex, chassi})
    });
    const data = await r.json();
    if (data.ok) {
      resultEl.innerHTML = data.bate
        ? '<span class="text-success">✓ BATE</span>'
        : '<span class="text-danger">✗ NÃO BATE</span>';
    } else {
      resultEl.innerHTML = '<span class="text-danger">' + (data.erro || 'erro') + '</span>';
    }
  } catch (e) {
    resultEl.innerHTML = '<span class="text-danger">erro: ' + e + '</span>';
  }
});
</script>
{% endblock %}
```

- [ ] **Step 9: Template detalhe**

`app/templates/motos_assai/modelos/detalhe.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<header class="d-flex justify-content-between mb-3">
  <h2>{{ modelo.codigo }} — {{ modelo.nome }}
    {% if modelo.ativo %}<span class="badge bg-success">ATIVO</span>
    {% else %}<span class="badge bg-secondary">INATIVO</span>{% endif %}
  </h2>
  <a href="{{ url_for('motos_assai.modelos_editar', modelo_id=modelo.id) }}" class="btn btn-outline-primary">
    <i class="fas fa-edit"></i> Editar
  </a>
</header>

<dl class="row">
  <dt class="col-sm-3">Descrição Q.P.A.</dt><dd class="col-sm-9">{{ modelo.descricao_qpa or '-' }}</dd>
  <dt class="col-sm-3">Código Q.P.A.</dt><dd class="col-sm-9">{{ modelo.codigo_qpa or '-' }}</dd>
  <dt class="col-sm-3">Regex chassi</dt>
  <dd class="col-sm-9">
    {% if modelo.regex_chassi %}<code>{{ modelo.regex_chassi }}</code>
    {% else %}<span class="text-warning">não configurado</span>{% endif %}
  </dd>
</dl>

<h4>Aliases ({{ modelo.aliases|length }})</h4>
<table class="table table-sm">
  <thead><tr><th>Alias</th><th>Tipo</th><th>Ativo</th></tr></thead>
  <tbody>
    {% for a in modelo.aliases %}
    <tr>
      <td>{{ a.alias }}</td>
      <td><code>{{ a.tipo }}</code></td>
      <td>{% if a.ativo %}sim{% else %}não{% endif %}</td>
    </tr>
    {% endfor %}
  </tbody>
</table>

<a href="{{ url_for('motos_assai.modelos_lista') }}" class="btn btn-outline-secondary">Voltar</a>
{% endblock %}
```

- [ ] **Step 10: Adicionar link no nav**

Em `app/templates/motos_assai/base_motos_assai.html`:

```jinja
    <a class="motos-assai-nav-link" href="{{ url_for('motos_assai.modelos_lista') }}">
      <i class="fas fa-tags"></i> Modelos
    </a>
```

- [ ] **Step 11: Validar API regex**

```bash
python -c "
from app import create_app
from app.auth.models import Usuario
import json
app = create_app()
with app.app_context():
    u = Usuario.query.filter_by(perfil='administrador').first()
    with app.test_client() as c:
        with c.session_transaction() as s:
            s['_user_id'] = str(u.id); s['_fresh'] = True
        r = c.post('/motos-assai/modelos/api/testar-regex',
                   json={'regex': '^LA\\d+\$', 'chassi': 'LA12345'})
        print('Status:', r.status_code, 'Body:', r.get_json())
"
```

Expected: `Status: 200 Body: {'ok': True, 'bate': True, ...}`

- [ ] **Step 12: Commit**

```bash
git add app/motos_assai/forms/modelo_forms.py app/motos_assai/forms/__init__.py
git add app/motos_assai/services/modelo_service.py app/motos_assai/services/__init__.py
git add app/motos_assai/routes/modelos.py app/motos_assai/routes/__init__.py
git add app/templates/motos_assai/modelos/ app/templates/motos_assai/base_motos_assai.html
git commit -m "feat(motos_assai): CRUD AssaiModelo with regex_chassi tester"
```

---

## Task 25: CRUD CD (apenas detalhe + editar — single record)

**Files:**
- Create: `app/motos_assai/forms/cd_forms.py`
- Modify: `app/motos_assai/forms/__init__.py`
- Create: `app/motos_assai/services/cd_service.py`
- Modify: `app/motos_assai/services/__init__.py`
- Create: `app/motos_assai/routes/cd.py`
- Modify: `app/motos_assai/routes/__init__.py`
- Create: `app/templates/motos_assai/cd/detalhe.html`
- Create: `app/templates/motos_assai/cd/form.html`
- Modify: `app/templates/motos_assai/base_motos_assai.html`

- [ ] **Step 1: Form**

`app/motos_assai/forms/cd_forms.py`:

```python
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, BooleanField
from wtforms.validators import DataRequired, Length, Optional, Regexp


UFs = [(s, s) for s in ['SP','RJ','MG','PR','SC','RS','BA','GO','DF','MT','MS','ES','CE','PE','PB','RN','SE','AL','MA','PI','PA','AP','AM','RR','RO','AC','TO']]


class CdForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired(), Length(max=80)])
    cnpj = StringField('CNPJ', validators=[Optional(),
        Regexp(r'^\d{14}$', message='Use 14 dígitos sem formatação')])
    endereco = StringField('Endereço', validators=[Optional(), Length(max=255)])
    bairro = StringField('Bairro', validators=[Optional(), Length(max=80)])
    cep = StringField('CEP', validators=[Optional(), Length(max=10)])
    cidade = StringField('Cidade', validators=[Optional(), Length(max=80)])
    uf = SelectField('UF', choices=[('', '-')] + UFs, validators=[Optional()])
    ativo = BooleanField('Ativo', default=True)
```

- [ ] **Step 2: Atualizar __init__ forms**

```python
from .loja_forms import LojaForm
from .modelo_forms import ModeloForm, TestarRegexForm
from .cd_forms import CdForm

__all__ = ['LojaForm', 'ModeloForm', 'TestarRegexForm', 'CdForm']
```

- [ ] **Step 3: Service**

`app/motos_assai/services/cd_service.py`:

```python
from app import db
from app.motos_assai.models import AssaiCd


def get_cd_principal() -> AssaiCd | None:
    """Retorna o CD ativo (na v1 esperamos 1 único 'Operação VOE')."""
    return AssaiCd.query.filter_by(ativo=True).order_by(AssaiCd.id).first()


def atualizar_cd(cd_id: int, dados: dict) -> AssaiCd:
    cd = AssaiCd.query.get_or_404(cd_id)
    for k, v in dados.items():
        if hasattr(cd, k):
            setattr(cd, k, v)
    db.session.commit()
    return cd
```

- [ ] **Step 4: Atualizar __init__ services**

Adicionar imports correspondentes.

- [ ] **Step 5: Rotas**

`app/motos_assai/routes/cd.py`:

```python
from flask import render_template, redirect, url_for, flash, abort
from flask_login import login_required
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms import CdForm
from app.motos_assai.services import get_cd_principal, atualizar_cd


@motos_assai_bp.route('/cd')
@login_required
@require_motos_assai
def cd_detalhe():
    cd = get_cd_principal()
    if not cd:
        flash('CD não cadastrado. Rode a migration de seed.', 'warning')
        return redirect(url_for('motos_assai.dashboard'))
    return render_template('motos_assai/cd/detalhe.html', cd=cd)


@motos_assai_bp.route('/cd/editar', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def cd_editar():
    cd = get_cd_principal()
    if not cd:
        abort(404)
    form = CdForm(obj=cd)
    if form.validate_on_submit():
        atualizar_cd(cd.id, {
            'nome': form.nome.data.strip(),
            'cnpj': form.cnpj.data.strip() if form.cnpj.data else None,
            'endereco': form.endereco.data.strip() if form.endereco.data else None,
            'bairro': form.bairro.data.strip() if form.bairro.data else None,
            'cep': form.cep.data.strip() if form.cep.data else None,
            'cidade': form.cidade.data.strip() if form.cidade.data else None,
            'uf': form.uf.data or None,
            'ativo': form.ativo.data,
        })
        flash('CD atualizado.', 'success')
        return redirect(url_for('motos_assai.cd_detalhe'))
    return render_template('motos_assai/cd/form.html', form=form, cd=cd)
```

- [ ] **Step 6: Importar route no blueprint**

```python
from app.motos_assai.routes import cd  # noqa: E402,F401
```

- [ ] **Step 7: Templates**

`app/templates/motos_assai/cd/detalhe.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<header class="d-flex justify-content-between mb-3">
  <h2>CD — {{ cd.nome }}
    {% if cd.ativo %}<span class="badge bg-success">ATIVO</span>{% endif %}
  </h2>
  <a href="{{ url_for('motos_assai.cd_editar') }}" class="btn btn-outline-primary">
    <i class="fas fa-edit"></i> Editar
  </a>
</header>

<dl class="row">
  <dt class="col-sm-3">CNPJ</dt><dd class="col-sm-9">{{ cd.cnpj or '-' }}</dd>
  <dt class="col-sm-3">Endereço</dt>
  <dd class="col-sm-9">{{ cd.endereco or '-' }}{% if cd.bairro %} — {{ cd.bairro }}{% endif %}</dd>
  <dt class="col-sm-3">Cidade/UF</dt>
  <dd class="col-sm-9">{{ cd.cidade or '-' }}/{{ cd.uf or '-' }} {% if cd.cep %}— CEP {{ cd.cep }}{% endif %}</dd>
</dl>
{% endblock %}
```

`app/templates/motos_assai/cd/form.html`:

```jinja
{% extends "motos_assai/base_motos_assai.html" %}

{% block motos_assai_content %}
<h2>Editar CD — {{ cd.nome }}</h2>

<form method="POST" class="row g-3">
  {{ form.hidden_tag() }}
  <div class="col-md-8">
    {{ form.nome.label(class="form-label") }}
    {{ form.nome(class="form-control") }}
  </div>
  <div class="col-md-4">
    {{ form.cnpj.label(class="form-label") }}
    {{ form.cnpj(class="form-control", placeholder="14 dígitos") }}
    {% for e in form.cnpj.errors %}<div class="text-danger small">{{ e }}</div>{% endfor %}
  </div>
  <div class="col-12">
    {{ form.endereco.label(class="form-label") }}
    {{ form.endereco(class="form-control") }}
  </div>
  <div class="col-md-3">{{ form.bairro.label(class="form-label") }}{{ form.bairro(class="form-control") }}</div>
  <div class="col-md-2">{{ form.cep.label(class="form-label") }}{{ form.cep(class="form-control") }}</div>
  <div class="col-md-5">{{ form.cidade.label(class="form-label") }}{{ form.cidade(class="form-control") }}</div>
  <div class="col-md-2">{{ form.uf.label(class="form-label") }}{{ form.uf(class="form-select") }}</div>
  <div class="col-12 form-check ms-3">
    {{ form.ativo(class="form-check-input") }}
    {{ form.ativo.label(class="form-check-label") }}
  </div>
  <div class="col-12">
    <button type="submit" class="btn btn-primary">Salvar</button>
    <a href="{{ url_for('motos_assai.cd_detalhe') }}" class="btn btn-outline-secondary">Cancelar</a>
  </div>
</form>
{% endblock %}
```

- [ ] **Step 8: Adicionar link no nav**

Em `app/templates/motos_assai/base_motos_assai.html`:

```jinja
    <a class="motos-assai-nav-link" href="{{ url_for('motos_assai.cd_detalhe') }}">
      <i class="fas fa-warehouse"></i> CD
    </a>
```

- [ ] **Step 9: Commit**

```bash
git add app/motos_assai/forms/cd_forms.py app/motos_assai/forms/__init__.py
git add app/motos_assai/services/cd_service.py app/motos_assai/services/__init__.py
git add app/motos_assai/routes/cd.py app/motos_assai/routes/__init__.py
git add app/templates/motos_assai/cd/ app/templates/motos_assai/base_motos_assai.html
git commit -m "feat(motos_assai): CRUD AssaiCd (single-record edit)"
```

---

## Task 26: Testes core

**Files:**
- Create: `tests/motos_assai/__init__.py`
- Create: `tests/motos_assai/conftest.py`
- Create: `tests/motos_assai/test_models.py`
- Create: `tests/motos_assai/test_decorator.py`
- Create: `tests/motos_assai/test_auth_integration.py`
- Create: `tests/motos_assai/test_cadastros.py`

- [ ] **Step 1: __init__ + conftest**

`tests/motos_assai/__init__.py`:
```python
# tests pacote
```

`tests/motos_assai/conftest.py`:
```python
import pytest
from app import create_app, db
from app.auth.models import Usuario


@pytest.fixture
def app():
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(app):
    with app.app_context():
        u = Usuario.query.filter_by(perfil='administrador').first()
        assert u, "Pré-requisito: ter pelo menos 1 admin no banco"
        yield u


@pytest.fixture
def login_admin(client, admin_user):
    with client.session_transaction() as s:
        s['_user_id'] = str(admin_user.id)
        s['_fresh'] = True
    return client
```

- [ ] **Step 2: Test models**

`tests/motos_assai/test_models.py`:
```python
from app import db
from app.motos_assai.models import (
    AssaiCd, AssaiLoja, AssaiModelo, AssaiModeloAlias,
    AssaiMoto, AssaiMotoEvento,
    EVENTO_ESTOQUE, EVENTOS_VALIDOS,
    ALIAS_TIPO_NOME_LIVRE,
)


def test_cd_criar_e_ler(app):
    with app.app_context():
        cd = AssaiCd(nome='CD Teste 123 ' + str(id(test_cd_criar_e_ler)))
        db.session.add(cd)
        db.session.flush()
        assert cd.id > 0
        assert cd.ativo is True
        db.session.rollback()


def test_loja_unique_numero(app):
    with app.app_context():
        l1 = AssaiLoja(numero='9999', nome='L1', razao_social='X', cnpj='00.000.000/0001-00', uf='SP')
        l2 = AssaiLoja(numero='9999', nome='L2', razao_social='Y', cnpj='00.000.000/0002-00', uf='RJ')
        db.session.add(l1)
        db.session.flush()
        db.session.add(l2)
        try:
            db.session.flush()
            assert False, 'Esperava IntegrityError por número duplicado'
        except Exception:
            db.session.rollback()


def test_modelo_alias_relationship(app):
    with app.app_context():
        m = AssaiModelo(codigo='ZZZ_TEST_' + str(id(test_modelo_alias_relationship)),
                        nome='Z Test')
        m.aliases.append(AssaiModeloAlias(alias='ZZZ', tipo=ALIAS_TIPO_NOME_LIVRE))
        m.aliases.append(AssaiModeloAlias(alias='ZZZ ALT', tipo=ALIAS_TIPO_NOME_LIVRE))
        db.session.add(m)
        db.session.flush()
        assert len(m.aliases) == 2
        db.session.rollback()


def test_eventos_validos_completos():
    assert EVENTO_ESTOQUE in EVENTOS_VALIDOS
    assert len(EVENTOS_VALIDOS) == 10
```

- [ ] **Step 3: Test decorator**

`tests/motos_assai/test_decorator.py`:
```python
from app.auth.models import Usuario


def test_decorator_redireciona_sem_login(client):
    r = client.get('/motos-assai/', follow_redirects=False)
    assert r.status_code in (302, 308)
    assert '/auth/login' in r.location


def test_pode_acessar_motos_assai_sem_flag(app):
    with app.app_context():
        u = Usuario(email='x@x', nome='X', senha_hash='x',
                    status='ativo', sistema_motos_assai=False, perfil='vendedor')
        assert u.pode_acessar_motos_assai() is False


def test_pode_acessar_motos_assai_com_flag(app):
    with app.app_context():
        u = Usuario(email='x@x', nome='X', senha_hash='x',
                    status='ativo', sistema_motos_assai=True, perfil='vendedor')
        assert u.pode_acessar_motos_assai() is True


def test_status_nao_ativo_bloqueia_mesmo_com_flag(app):
    with app.app_context():
        u = Usuario(email='x@x', nome='X', senha_hash='x',
                    status='pendente', sistema_motos_assai=True, perfil='vendedor')
        assert u.pode_acessar_motos_assai() is False


def test_admin_passa_sem_flag(app):
    with app.app_context():
        u = Usuario(email='x@x', nome='X', senha_hash='x',
                    status='ativo', sistema_motos_assai=False, perfil='administrador')
        assert u.pode_acessar_motos_assai() is True


def test_admin_pendente_e_bloqueado(app):
    with app.app_context():
        u = Usuario(email='x@x', nome='X', senha_hash='x',
                    status='pendente', sistema_motos_assai=True, perfil='administrador')
        assert u.pode_acessar_motos_assai() is False
```

- [ ] **Step 4: Test auth integration**

`tests/motos_assai/test_auth_integration.py`:
```python
from app import db
from app.auth.models import Usuario
from app.auth.utils import url_primeiro_dashboard_disponivel


def test_redirect_pos_login_motos_assai_only(app):
    with app.app_context():
        u = Usuario(email='only@x', nome='Only', senha_hash='x',
                    status='ativo', sistema_motos_assai=True,
                    sistema_logistica=False, sistema_lojas=False,
                    sistema_motochefe=False, sistema_carvia=False,
                    perfil='vendedor')
        with app.test_request_context():
            url = url_primeiro_dashboard_disponivel(u)
        assert url and '/motos-assai' in url
```

- [ ] **Step 5: Test cadastros**

`tests/motos_assai/test_cadastros.py`:
```python
def test_lista_lojas_acesso(login_admin):
    r = login_admin.get('/motos-assai/lojas')
    assert r.status_code == 200


def test_lista_modelos_acesso(login_admin):
    r = login_admin.get('/motos-assai/modelos')
    assert r.status_code == 200


def test_dashboard_renderiza(login_admin):
    r = login_admin.get('/motos-assai/')
    assert r.status_code == 200
    assert b'Opera' in r.data


def test_api_testar_regex(login_admin):
    r = login_admin.post('/motos-assai/modelos/api/testar-regex',
                         json={'regex': r'^LA\d+$', 'chassi': 'LA12345'})
    assert r.status_code == 200
    body = r.get_json()
    assert body['ok'] is True
    assert body['bate'] is True


def test_api_testar_regex_no_match(login_admin):
    r = login_admin.post('/motos-assai/modelos/api/testar-regex',
                         json={'regex': r'^LA\d+$', 'chassi': 'XX12345'})
    assert r.status_code == 200
    body = r.get_json()
    assert body['bate'] is False


def test_api_testar_regex_invalido(login_admin):
    r = login_admin.post('/motos-assai/modelos/api/testar-regex',
                         json={'regex': '[invalid', 'chassi': 'X'})
    assert r.status_code == 400
```

- [ ] **Step 6: Rodar testes**

```bash
source .venv/bin/activate
pytest tests/motos_assai/ -v
```

Expected: todos PASS.

- [ ] **Step 7: Commit**

```bash
git add tests/motos_assai/
git commit -m "test(motos_assai): foundation tests (models, decorator, auth, cadastros)"
```

---

## Task 27: CLAUDE.md do módulo

**Files:**
- Create: `app/motos_assai/CLAUDE.md`

- [ ] **Step 1: Criar CLAUDE.md**

`app/motos_assai/CLAUDE.md`:

````markdown
# Módulo Motos Assaí

**Data**: 2026-05-07
**Status**: Foundation + Cadastros (Plano 1) implementado.
**Propósito**: gerenciar a operação B2B Q.P.A. → Sendas/Assaí com motos elétricas, isolada de outros módulos.

---

## Fronteira do módulo (o que NÃO fazer)

| Módulo vizinho | Motivo da fronteira |
|---|---|
| `app/hora/` | PJ diferente; HORA é B2C varejo, Motos Assaí é B2B atacadista |
| `app/carvia/` | CarVia só transporta. Reuso permitido APENAS via adapter |
| `app/motochefe/` | PJ diferente |
| `app/pedidos/leitura/` | Reuso permitido via subclasse de `PDFExtractor` |

---

## Convenções obrigatórias

### 1. Prefixo de tabela `assai_`

Todas as tabelas começam com `assai_`. 16 tabelas no schema atual.

### 2. Blueprint isolado

Rotas em `app/motos_assai/routes/`, services em `app/motos_assai/services/`,
models em `app/motos_assai/models/`. Blueprint `motos_assai_bp` registrado em
`app/__init__.py` com `url_prefix='/motos-assai'`.

### 3. Toggle master `sistema_motos_assai`

Coluna em `usuarios`. Método `Usuario.pode_acessar_motos_assai()`:
admin sempre passa; status != 'ativo' bloqueia mesmo com flag.

Decorator `@require_motos_assai` em TODAS as rotas (sem exceção).

### 4. Menu

Link em `app/templates/base.html` condicionado a
`current_user.pode_acessar_motos_assai()`.

---

## Invariante central

**`assai_moto.chassi` é a chave universal do módulo.**

1. Toda tabela transacional tem `chassi` indexada.
2. `assai_moto` é insert-once com atributos imutáveis (UPDATE apenas em `cor`/`modelo_id`
   quando recebimento físico diverge do recibo Motochefe — SOT, padrão Hora).
3. Estado atual de uma moto = consulta à tabela de eventos
   (`assai_moto_evento` ordenado por `ocorrido_em DESC`), nunca UPDATE em coluna `status`.
4. `assai_moto_evento` é append-only — nunca DELETE; reversão cria nova linha
   (`REVERTIDA_PARA_MONTADA`).

---

## Eventos por chassi (`assai_moto_evento.tipo`)

| Tipo | Significado | Conta como em estoque? |
|------|-------------|------------------------|
| `ESTOQUE` | Recebida no CD | Sim |
| `MONTADA` | Montada e OK | Sim |
| `PENDENTE` | Peça com defeito a resolver | Sim, mas bloqueia DISPONIVEL |
| `PENDENCIA_RESOLVIDA` | Voltou a MONTADA após pendência | Sim (efetivo MONTADA) |
| `DISPONIVEL` | Tag + manual + pronta para separação | Sim |
| `REVERTIDA_PARA_MONTADA` | Operador reverteu disponibilização | Sim (efetivo MONTADA) |
| `SEPARADA` | Vinculada a separação ativa | Não |
| `FATURADA` | NF Q.P.A. importada e bateu | Não |
| `CANCELADA` | Separação cancelada (volta como DISPONIVEL via novo evento) | Depende |
| `MOTO_FALTANDO` | Declarada no recibo mas não chegou | Não |

---

## Modelo de dados (16 tabelas)

Ver spec em `docs/superpowers/specs/2026-05-07-motos-assai-design.md` §4.

Cadastros: `assai_cd`, `assai_loja`, `assai_modelo`, `assai_modelo_alias`.
Identidade: `assai_moto`, `assai_moto_evento`.
Pipeline: `assai_pedido_venda*`, `assai_compra_motochefe*`, `assai_recibo_motochefe*`.
Saída: `assai_separacao*`, `assai_nf_qpa*`.

---

## Lista de constantes/aliases por arquivo

- `app/motos_assai/models/moto.py`: `EVENTO_*`, `EVENTOS_VALIDOS`, `EVENTOS_EM_ESTOQUE`
- `app/motos_assai/models/pedido.py`: `PEDIDO_STATUS_*`, `PEDIDO_STATUS_VALIDOS`
- `app/motos_assai/models/compra.py`: `COMPRA_STATUS_*`, `COMPRA_STATUS_VALIDOS`
- `app/motos_assai/models/recibo.py`: `RECIBO_STATUS_*`, `DIVERGENCIA_*`
- `app/motos_assai/models/separacao.py`: `SEPARACAO_STATUS_*`
- `app/motos_assai/models/nf_qpa.py`: `NF_STATUS_*`
- `app/motos_assai/models/modelo.py`: `ALIAS_TIPO_*`

---

## Próximos passos (Planos 2 e 3)

- **Plano 2**: parsers de pedido VOE Q.P.A. + recibo Motochefe + wizard de recebimento físico
- **Plano 3**: montagem, disponibilizar, separação, Excel Q.P.A., importação de NF Q.P.A.

---

## Referências

- Spec: `docs/superpowers/specs/2026-05-07-motos-assai-design.md`
- Plano 1: `docs/superpowers/plans/2026-05-07-motos-assai-foundation.md`
- Padrão arquitetural de referência: `app/hora/CLAUDE.md`
- Parser base de PDF: `app/pedidos/leitura/base.py:PDFExtractor`
- Parser DANFE Q.P.A. (CarVia, sem modificar): `app/carvia/services/parsers/danfe_pdf_parser.py`
- Wizard QR de referência: `app/templates/hora/recebimento_wizard.html`
````

- [ ] **Step 2: Commit**

```bash
git add app/motos_assai/CLAUDE.md
git commit -m "docs(motos_assai): add module CLAUDE.md with conventions and invariants"
```

---

## Self-review do plano (auto)

**Spec coverage**:
- §1 Contexto: implícito no propósito do plano. ✓
- §2 Decisões aprovadas: refletidas em models (constantes de status), decorator (gate de status + admin bypass), CRUD (regex configurável). ✓
- §3 Arquitetura: estrutura de pastas mapeada na visão de arquivos no topo. ✓
- §4 Modelo de dados (16 tabelas): Tasks 5–11 cobrem todas. ✓
- §5 Fluxos: este plano cobre só foundation/cadastros (Fases 1+2 do spec). Fases 3-8 ficam para Planos 2+3 — explicitado em "Próximos passos". ✓
- §7 Permissões: Tasks 2-4 + 12-18. ✓
- §9 Migrations: Tasks 2, 5, 20-22. ✓
- §10 Sequência: Tasks 1-25 implementam Fases 1+2; Tasks 26-27 são polish (testes + CLAUDE.md). ✓

**Placeholder scan**:
- Task 20 e 22 marcam explicitamente "PREENCHER quando dono fornecer" para CNPJ do CD e máscaras de chassi — esses são DADOS de seed, não placeholders de código. Aceitável.
- Nenhum "TBD/TODO/implement later" sem contexto.

**Type consistency**:
- `pode_acessar_motos_assai` consistente em Tasks 4, 12, 16, 18, 26.
- `motos_assai_bp` consistente em Tasks 13, 19, 23, 24, 25.
- Constantes de evento (`EVENTO_*`) consistentes entre modelo (Task 8), CLAUDE.md (Task 27).
- `regex_chassi` consistente em models (Task 7), seed (Task 22), form/service (Task 24).

---

## Execução

Plano salvo em `docs/superpowers/plans/2026-05-07-motos-assai-foundation.md`. Aproximadamente 27 tasks bite-sized com TDD onde aplicável (decorator, models, services).

Quando o Plano 1 estiver implementado e validado, gerar Planos 2 e 3 para as fases restantes (parsers + wizard + pipeline saída).
