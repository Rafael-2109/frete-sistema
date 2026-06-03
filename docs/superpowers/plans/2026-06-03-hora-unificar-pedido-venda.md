<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# HORA — Unificar Pedido de Venda + filtro loja/vendedor + fix desconto — Implementation Plan

> **Papel:** plano de implementação task-by-task das 3 mudanças no Pedido de Venda das Lojas HORA — fix do drift de centavos no desconto, critério de listagem loja/vendedor por usuário, e unificação da tela "Ver pedido" na tela "Novo pedido de venda".

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** No módulo Lojas HORA, corrigir o drift de centavos no desconto, adicionar critério opcional de listagem de pedidos por loja **ou** vendedor (configurável por usuário em permissões), e unificar a tela "Ver pedido" na tela "Novo pedido de venda" (cria + edita), removendo `venda_detalhe.html`.

**Architecture:** Backend Flask/SQLAlchemy + Jinja2. Reuso máximo do backend de venda já maduro (`venda_service`, rotas granulares por seção, matriz `_CAMPOS_EDITAVEIS_HEADER`). A unificação é majoritariamente trabalho de template/JS: o componente rico de seleção de moto+desconto é extraído para um partial Jinja + arquivo JS de módulo, reusado em criação e edição. 1 migration dual adiciona 2 colunas (`usuarios.criterio_pedidos_hora`, `hora_venda.criado_por_id`). Fronteira do módulo preservada (sem FK cross-módulo).

**Tech Stack:** Python 3.12, Flask 3.1, SQLAlchemy 2.0, Jinja2, Bootstrap 5.3, Vanilla JS, pytest. Migrations duais (`.py` + `.sql` idempotente). Spec: `docs/superpowers/specs/2026-06-03-hora-unificar-pedido-venda-design.md`.

**Ordem:** Parte 2 (fix desconto) → Parte 3 (filtro) → Parte 1 (unificação). Cada Task termina em commit.

**Ambiente de teste (worktree):** sem `.env`, pytest cai em SQLite. Passar `DATABASE_URL` da raiz ao rodar. Convenção observada em `tests/hora/`: services usam `db.session.commit()` (escapam do nested transaction), por isso os testes usam fixtures que limpam por prefixo de CNPJ/chassi e escolhem dados únicos. Rodar testes da **raiz** do repo (não fazer `cd` para subdir — quebra hooks).

## Indice

- [Parte 2 — Fix do drift de centavos no desconto](#parte-2--fix-do-drift-de-centavos-no-desconto)
  - [Task 1: Ancorar o recálculo de preço no valor final](#task-1-ancorar-o-recálculo-de-preço-no-valor-final-não-no-)
- [Parte 3 — Filtro opcional loja/vendedor](#parte-3--filtro-opcional-lojavendedor)
  - [Task 2: Migration dual](#task-2-migration-dual--usuarioscriterio_pedidos_hora--hora_vendacriado_por_id)
  - [Task 3: Colunas nos modelos](#task-3-adicionar-colunas-aos-modelos-usuario-e-horavenda)
  - [Task 4: criar_venda_manual grava criado_por_id](#task-4-criar_venda_manual-grava-criado_por_id)
  - [Task 5: Filtro por vendedor em _query_vendas](#task-5-filtro-por-vendedor-em-_query_vendas--paginar_vendas)
  - [Task 6: vendas_lista aplica o critério](#task-6-vendas_lista-aplica-o-critério-do-usuário)
  - [Task 7: UI de permissões](#task-7-ui-de-permissões--escolher-o-critério-por-usuário)
- [Parte 1 — Unificação das telas](#parte-1--unificação-das-telas)
  - [Task 8: Corrigir bug latente de rota](#task-8-corrigir-bug-latente-horavenda_detalhe--horavendas_detalhe)
  - [Task 9: Extrair componente moto+desconto](#task-9-extrair-componente-de-motodesconto-para-partial--js-de-módulo)
  - [Task 10: Tela unificada via vendas_detalhe](#task-10-tela-unificada-renderizada-por-vendas_detalhe-modo-edição)
  - [Task 11: Migrar ações/seções](#task-11-migrar-todas-as-açõesseções-de-venda_detalhehtml-para-a-tela-unificada)
  - [Task 12: Remover venda_detalhe.html](#task-12-remover-venda_detalhehtml-e-reapontar-onboarding)
  - [Task 13: Docs + self-review](#task-13-atualizar-claudemd-do-módulo--índice-de-planos--self-review)
- [Self-Review do plano](#self-review-do-plano-preenchido)

---

## Parte 2 — Fix do drift de centavos no desconto

### Task 1: Ancorar o recálculo de preço no valor final (não no %)

**Files:**
- Modify: `app/templates/hora/tagplus/pedido_venda_novo.html:684-739` (função `atualizarPrecoTabela`)

**Contexto:** `atualizarPrecoTabela()` re-busca o preço de tabela e sempre termina com `recalcular('pct')` (`:737-738`), reconstruindo o R$ a partir do `%` arredondado → drift (500,00 → 500,05). A âncora correta é o **valor final** que o operador digitou. Exceção: na primeira escolha de modelo (valor ainda vazio/0), inicializar pelo preço cheio via `'pct'` (desconto 0).

- [ ] **Step 1: Substituir a âncora do recálculo**

Localizar (`pedido_venda_novo.html`, fim de `atualizarPrecoTabela`, ~`:737-738`):

```javascript
    // Recalcula valor final mantendo o desconto % atual (preserva intencao do operador).
    recalcular('pct');
  }
```

Substituir por:

```javascript
    // Recalcula preservando o VALOR FINAL ja digitado (ancora 'valor') para
    // nao introduzir drift de centavos ao re-buscar o preco de tabela (ex.: ao
    // trocar a forma de pagamento entre a vista/a prazo). Na 1a carga, quando o
    // valor ainda esta vazio/zero, inicializa pelo preco cheio via 'pct' (desconto 0).
    const valorAtual = parseBR(elValor.value);
    if (isNaN(valorAtual) || valorAtual <= 0) {
      recalcular('pct');
    } else {
      recalcular('valor');
    }
  }
```

- [ ] **Step 2: Verificação manual (sem harness JS)**

Rodar o app local (`python run.py`), abrir `/hora/tagplus/pedido-venda/novo`:
1. Escolher modelo/cor/chassi → preço de tabela carrega, desconto 0, valor = preço cheio. (caso 1a carga via `'pct'`).
2. Digitar Desconto R$ = `500,00` → valor final ajusta; % calcula.
3. Adicionar uma forma de pagamento e trocar o `<select>` de forma → **Desconto R$ permanece `500,00`** (antes virava 500,05). Valor final permanece estável.
4. Trocar a forma entre uma A_VISTA e uma A_PRAZO (se houver preços distintos no modelo) → preço de tabela atualiza, **valor final preservado**, desconto R$/% reajustam sobre o valor mantido.

- [ ] **Step 3: Commit**

```bash
git add app/templates/hora/tagplus/pedido_venda_novo.html
git commit -m "fix(hora): desconto nao sofre drift de centavos ao trocar forma de pagamento

atualizarPrecoTabela() reancorava o recalculo no % arredondado (recalcular('pct')),
reconstruindo o R\$ e introduzindo drift (500,00 -> 500,05). Passa a ancorar no
valor final digitado (recalcular('valor')); 1a carga (valor vazio) usa 'pct'.

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Parte 3 — Filtro opcional loja/vendedor

### Task 2: Migration dual — `usuarios.criterio_pedidos_hora` + `hora_venda.criado_por_id`

**Files:**
- Create: `scripts/migrations/hora_44_criterio_pedidos_e_criador.py`
- Create: `scripts/migrations/hora_44_criterio_pedidos_e_criador.sql`

- [ ] **Step 1: Escrever o `.sql` idempotente**

`scripts/migrations/hora_44_criterio_pedidos_e_criador.sql`:

```sql
-- Migration HORA 44: criterio de listagem de pedidos por usuario + criador do pedido.
-- Idempotente (IF NOT EXISTS). Rodar no Render Shell.

-- 1) Preferencia de criterio de filtragem de pedidos de venda por usuario.
--    'loja' (default, comportamento atual) | 'vendedor' (pedidos do proprio usuario).
ALTER TABLE usuarios
    ADD COLUMN IF NOT EXISTS criterio_pedidos_hora VARCHAR(10) NOT NULL DEFAULT 'loja';

-- 2) Usuario criador do pedido de venda (robustez para o filtro 'vendedor').
--    Sem FK (padrao do modulo HORA: nao acopla a usuarios).
ALTER TABLE hora_venda
    ADD COLUMN IF NOT EXISTS criado_por_id INTEGER;

CREATE INDEX IF NOT EXISTS idx_hora_venda_criado_por_id
    ON hora_venda (criado_por_id);

-- 3) Backfill best-effort do criador via auditoria (acao='CRIOU' casando nome).
UPDATE hora_venda v
   SET criado_por_id = u.id
  FROM hora_venda_auditoria a
  JOIN usuarios u ON u.nome = a.usuario
 WHERE a.venda_id = v.id
   AND a.acao = 'CRIOU'
   AND v.criado_por_id IS NULL;
```

- [ ] **Step 2: Escrever o `.py` (create_app + before/after + backfill)**

`scripts/migrations/hora_44_criterio_pedidos_e_criador.py`:

```python
"""Migration HORA 44: criterio de listagem de pedidos por usuario + criador do pedido.

Mudancas:
  1. usuarios       -> +criterio_pedidos_hora VARCHAR(10) NOT NULL DEFAULT 'loja'
  2. hora_venda     -> +criado_por_id INTEGER (sem FK; padrao do modulo) + indice
  3. backfill criado_por_id via hora_venda_auditoria (acao='CRIOU', match por nome)

Idempotente — pode rodar 2x (IF NOT EXISTS + backfill so onde criado_por_id IS NULL).

Uso:
    python scripts/migrations/hora_44_criterio_pedidos_e_criador.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    "ALTER TABLE usuarios "
    "ADD COLUMN IF NOT EXISTS criterio_pedidos_hora VARCHAR(10) NOT NULL DEFAULT 'loja';",
    "ALTER TABLE hora_venda "
    "ADD COLUMN IF NOT EXISTS criado_por_id INTEGER;",
    "CREATE INDEX IF NOT EXISTS idx_hora_venda_criado_por_id "
    "ON hora_venda (criado_por_id);",
]

SQL_BACKFILL = """
UPDATE hora_venda v
   SET criado_por_id = u.id
  FROM hora_venda_auditoria a
  JOIN usuarios u ON u.nome = a.usuario
 WHERE a.venda_id = v.id
   AND a.acao = 'CRIOU'
   AND v.criado_por_id IS NULL;
"""


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        cols_user = {c['name'] for c in inspector.get_columns('usuarios')}
        cols_venda = {c['name'] for c in inspector.get_columns('hora_venda')}
        print('Estado antes:')
        print(f'  usuarios.criterio_pedidos_hora? {"criterio_pedidos_hora" in cols_user}')
        print(f'  hora_venda.criado_por_id? {"criado_por_id" in cols_venda}')

        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))
            res = conn.execute(text(SQL_BACKFILL))
            backfilled = res.rowcount if res.rowcount is not None else -1

        inspector = inspect(db.engine)
        cols_user = {c['name'] for c in inspector.get_columns('usuarios')}
        cols_venda = {c['name'] for c in inspector.get_columns('hora_venda')}
        print('\nEstado depois:')
        print(f'  usuarios.criterio_pedidos_hora? {"criterio_pedidos_hora" in cols_user}')
        print(f'  hora_venda.criado_por_id? {"criado_por_id" in cols_venda}')
        print(f'  criado_por_id backfilled (linhas): {backfilled}')

        if 'criterio_pedidos_hora' not in cols_user or 'criado_por_id' not in cols_venda:
            print('\nERRO: colunas nao criadas.')
            sys.exit(1)

        with db.engine.begin() as conn:
            sem_criador = conn.execute(text(
                'SELECT COUNT(*) FROM hora_venda WHERE criado_por_id IS NULL'
            )).scalar() or 0
        print(f'  vendas ainda sem criado_por_id (legado sem match): {sem_criador}')
        print('\nMigration HORA 44 concluida com sucesso.')


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Rodar a migration no banco local**

Run (da raiz do repo, venv ativo):
```bash
source .venv/bin/activate && python scripts/migrations/hora_44_criterio_pedidos_e_criador.py
```
Expected: "Estado depois" com ambas as colunas `True`, contagem de backfill impressa, "concluida com sucesso".

- [ ] **Step 4: Commit**

```bash
git add scripts/migrations/hora_44_criterio_pedidos_e_criador.py scripts/migrations/hora_44_criterio_pedidos_e_criador.sql
git commit -m "feat(hora): migration 43 — criterio_pedidos_hora + hora_venda.criado_por_id

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Adicionar colunas aos modelos `Usuario` e `HoraVenda`

**Files:**
- Modify: `app/auth/models.py:40` (após `loja_hora_id`)
- Modify: `app/hora/models/venda.py:152` (próximo a `vendedor`)

- [ ] **Step 1: Campo em `Usuario`**

Em `app/auth/models.py`, logo após `loja_hora_id = db.Column(db.Integer, nullable=True)` (linha 40):

```python
    # Criterio de filtragem dos Pedidos de Venda HORA na listagem /hora/vendas:
    #   'loja'     -> escopo por loja_hora_id (comportamento padrao).
    #   'vendedor' -> apenas pedidos cujo vendedor (ou vendedor_vinculado) ou
    #                 criado_por_id e este usuario (ignora escopo de loja).
    # Definido na tela /hora/permissoes. Sem efeito fora da listagem de pedidos.
    criterio_pedidos_hora = db.Column(
        db.String(10), nullable=False, default='loja', server_default='loja',
    )
```

- [ ] **Step 2: Campo em `HoraVenda`**

Em `app/hora/models/venda.py`, logo após o bloco do `vendedor` (após linha 155):

```python
    criado_por_id = db.Column(db.Integer, nullable=True, index=True)
    # Id do usuario (app.auth Usuario.id) que criou o pedido manual. Sem FK
    # (padrao do modulo: nao acopla a usuarios). Usado pelo filtro 'vendedor'
    # da listagem. Pedidos legados podem ter NULL (backfill best-effort).
```

- [ ] **Step 3: Verificar import (smoke)**

Run:
```bash
source .venv/bin/activate && python -c "from app import create_app; from app.hora.models import HoraVenda; from app.auth.models import Usuario; print(hasattr(HoraVenda,'criado_por_id'), hasattr(Usuario,'criterio_pedidos_hora'))"
```
Expected: `True True`

- [ ] **Step 4: Commit**

```bash
git add app/auth/models.py app/hora/models/venda.py
git commit -m "feat(hora): colunas criterio_pedidos_hora (Usuario) e criado_por_id (HoraVenda)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: `criar_venda_manual` grava `criado_por_id`

**Files:**
- Modify: `app/hora/services/venda_service.py:604-630` (assinatura) e `:786-811` (construtor `HoraVenda`)
- Modify: `app/hora/routes/tagplus_routes.py:1183-1211` (chamada)
- Test: `tests/hora/test_pedido_filtro_vendedor.py`

- [ ] **Step 1: Escrever o teste (falha)**

Create `tests/hora/test_pedido_filtro_vendedor.py` (reusa o padrão de fixtures de `test_pedido_workflow.py` — examinar esse arquivo para os helpers de criar loja/moto). Primeiro teste:

```python
from decimal import Decimal

import pytest

from app import db as _db
from app.hora.services import venda_service


@pytest.fixture(autouse=True)
def _cleanup(db):
    _db.session.execute(_db.text(
        "DELETE FROM hora_venda_item WHERE venda_id IN "
        "(SELECT id FROM hora_venda WHERE vendedor LIKE 'VENDTEST%');"
    ))
    _db.session.execute(_db.text(
        "DELETE FROM hora_venda WHERE vendedor LIKE 'VENDTEST%' "
        "OR criado_por_id IN (910001, 910002);"
    ))
    _db.session.execute(_db.text(
        "DELETE FROM hora_moto_evento WHERE numero_chassi LIKE '9VENDTEST%';"
    ))
    _db.session.execute(_db.text(
        "DELETE FROM hora_moto WHERE numero_chassi LIKE '9VENDTEST%';"
    ))
    _db.session.commit()
    yield


def _criar_moto_disponivel(db, chassi, modelo_id, loja_id):
    """Cria HoraMoto + evento RECEBIDA (em estoque) — ver moto_service helpers."""
    from app.hora.services.moto_service import get_or_create_moto, registrar_evento
    moto = get_or_create_moto(numero_chassi=chassi, modelo_id=modelo_id, cor='PRETO')
    registrar_evento(numero_chassi=moto.numero_chassi, tipo='RECEBIDA',
                     origem_tabela='test', origem_id=0, loja_id=loja_id)
    db.session.commit()
    return moto


def test_criar_venda_manual_grava_criado_por_id(db):
    # Pre-cond: precisa de um modelo e uma loja existentes — reusar helper de
    # criacao de loja/modelo do conftest/test_pedido_workflow (LojaOrigemTest).
    # (Detalhe de setup conforme padrao do modulo — ver test_pedido_workflow.)
    venda = venda_service.criar_venda_manual(
        cpf_cliente='52998224725', nome_cliente='Cliente VENDTEST',
        cep=None, endereco_logradouro=None, endereco_numero=None,
        endereco_complemento=None, endereco_bairro=None, endereco_cidade=None,
        endereco_uf=None, numero_chassi='9VENDTEST0001',
        valor_final=Decimal('1000.00'),
        vendedor='VENDTEST Joao', criado_por=' VENDTEST Joao',
        loja_id_override=_LOJA_ID, criado_por_id=910001,
    )
    assert venda.criado_por_id == 910001
```

> NOTA de setup: o teste depende de `_LOJA_ID` (loja ativa) e um `modelo_id` válido + moto disponível. Replicar o setup de loja/modelo/moto exatamente como `tests/hora/test_pedido_workflow.py` faz (mesmos helpers e prefixos). Não inventar IDs fixos — criar os registros no teste.

- [ ] **Step 2: Rodar o teste e ver falhar**

Run:
```bash
source .venv/bin/activate && DATABASE_URL="$DATABASE_URL" pytest tests/hora/test_pedido_filtro_vendedor.py::test_criar_venda_manual_grava_criado_por_id -v
```
Expected: FAIL — `criar_venda_manual() got an unexpected keyword argument 'criado_por_id'`.

- [ ] **Step 3: Adicionar param à assinatura de `criar_venda_manual`**

Em `app/hora/services/venda_service.py`, na assinatura (após `criado_por: Optional[str] = None,` na linha 624):

```python
    criado_por_id: Optional[int] = None,
```

- [ ] **Step 4: Gravar no construtor de `HoraVenda`**

No construtor `HoraVenda(...)` (bloco que termina em `:811`), adicionar antes do fechamento `)`:

```python
        criado_por_id=criado_por_id,
```

- [ ] **Step 5: Rodar o teste e ver passar**

Run:
```bash
source .venv/bin/activate && DATABASE_URL="$DATABASE_URL" pytest tests/hora/test_pedido_filtro_vendedor.py::test_criar_venda_manual_grava_criado_por_id -v
```
Expected: PASS.

- [ ] **Step 6: Passar `criado_por_id` na rota de criação**

Em `app/hora/routes/tagplus_routes.py`, na chamada `venda_service.criar_venda_manual(...)` (~`:1184-1211`), adicionar:

```python
            criado_por_id=getattr(current_user, 'id', None),
```

(Garantir que `current_user` está importado no módulo — `from flask_login import current_user`. Se não, adicionar o import.)

- [ ] **Step 7: Commit**

```bash
git add app/hora/services/venda_service.py app/hora/routes/tagplus_routes.py tests/hora/test_pedido_filtro_vendedor.py
git commit -m "feat(hora): criar_venda_manual grava criado_por_id do usuario logado

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Filtro por vendedor em `_query_vendas` / `paginar_vendas`

**Files:**
- Modify: `app/hora/services/venda_service.py:2140-2216` (`_query_vendas`), `:2219-2248` (`paginar_vendas`)
- Test: `tests/hora/test_pedido_filtro_vendedor.py`

**Semântica:** quando `filtro_vendedor` é passado, a query **ignora** o escopo de loja e filtra `OR(vendedor IN nomes, criado_por_id == user_id)`. `filtro_vendedor` é um dict `{'nomes': [str, ...], 'user_id': int}`. `nomes` inclui `Usuario.nome` e `Usuario.vendedor_vinculado` (quando setado). Se `filtro_vendedor` não resolve nenhuma condição (sem nomes e sem user_id) → retorna `None` (lista vazia).

- [ ] **Step 1: Escrever o teste (falha)**

Append em `tests/hora/test_pedido_filtro_vendedor.py`:

```python
def test_query_vendas_filtro_vendedor_por_nome_ou_criador(db):
    # 3 pedidos: A (vendedor 'VENDTEST Joao'), B (criado_por_id=910002),
    # C (vendedor 'VENDTEST Maria', criado_por_id None) — alheio.
    # (criar via criar_venda_manual com chassis distintos 9VENDTEST0002..0004)
    # ... setup ...
    q = venda_service._query_vendas(
        filtro_vendedor={'nomes': ['VENDTEST Joao'], 'user_id': 910002},
    )
    ids = {v.id for v in q.all()}
    assert id_A in ids        # casa por nome
    assert id_B in ids        # casa por criado_por_id
    assert id_C not in ids    # nao casa nenhum


def test_query_vendas_filtro_loja_inalterado(db):
    # Regressao: com lojas_permitidas_ids, comportamento atual mantido.
    q = venda_service._query_vendas(lojas_permitidas_ids=[_LOJA_ID])
    assert q is not None
    # nenhum pedido de outra loja aparece
```

- [ ] **Step 2: Rodar e ver falhar**

Run:
```bash
source .venv/bin/activate && DATABASE_URL="$DATABASE_URL" pytest tests/hora/test_pedido_filtro_vendedor.py -v -k filtro
```
Expected: FAIL — `_query_vendas() got an unexpected keyword argument 'filtro_vendedor'`.

- [ ] **Step 3: Adicionar `filtro_vendedor` a `_query_vendas`**

Em `_query_vendas`, adicionar ao final dos kwargs keyword-only (após `eager_itens: bool = False,`):

```python
    filtro_vendedor: Optional[dict] = None,
```

Substituir o bloco de loja (`:2182-2186`) por:

```python
    if filtro_vendedor is not None:
        # Criterio 'vendedor': ignora escopo de loja; pedidos do proprio usuario.
        nomes = [n for n in (filtro_vendedor.get('nomes') or []) if n]
        uid = filtro_vendedor.get('user_id')
        conds = []
        if nomes:
            conds.append(HoraVenda.vendedor.in_(nomes))
        if uid is not None:
            conds.append(HoraVenda.criado_por_id == uid)
        if not conds:
            return None  # sem criterio resolvivel -> nada a mostrar
        query = query.filter(or_(*conds))
    elif lojas_permitidas_ids is not None:
        ids_list = list(lojas_permitidas_ids)
        if not ids_list:
            return None
        query = query.filter(HoraVenda.loja_id.in_(ids_list))
```

(`or_` já está importado localmente em `:2163`.)

- [ ] **Step 4: Repassar `filtro_vendedor` em `paginar_vendas`**

Em `paginar_vendas`, adicionar o kwarg keyword-only (após `chassi: Optional[str] = None,`):

```python
    filtro_vendedor: Optional[dict] = None,
```

E na chamada interna `_query_vendas(...)` adicionar:

```python
        filtro_vendedor=filtro_vendedor,
```

- [ ] **Step 5: Rodar e ver passar**

Run:
```bash
source .venv/bin/activate && DATABASE_URL="$DATABASE_URL" pytest tests/hora/test_pedido_filtro_vendedor.py -v
```
Expected: PASS (todos).

- [ ] **Step 6: Commit**

```bash
git add app/hora/services/venda_service.py tests/hora/test_pedido_filtro_vendedor.py
git commit -m "feat(hora): _query_vendas/paginar_vendas suportam filtro_vendedor

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 6: `vendas_lista` aplica o critério do usuário

**Files:**
- Modify: `app/hora/routes/vendas.py:89-99` (montagem do filtro) e `:112-124` (contexto)

- [ ] **Step 1: Ler o critério e montar o filtro**

Em `vendas.py`, substituir o bloco `permitidas = lojas_permitidas_ids()` + chamada `paginar_vendas` (`:89-99`) por:

```python
    criterio = (getattr(current_user, 'criterio_pedidos_hora', 'loja') or 'loja')
    if criterio == 'vendedor':
        nomes = [n for n in (
            getattr(current_user, 'nome', None),
            getattr(current_user, 'vendedor_vinculado', None),
        ) if n]
        filtro_vendedor = {'nomes': nomes, 'user_id': getattr(current_user, 'id', None)}
        permitidas = None
        pagination = venda_service.paginar_vendas(
            page=page, per_page=per_page,
            status=status_filtro, busca=busca, loja_id=loja_id,
            data_inicio=data_inicio, data_fim=data_fim, chassi=filtro_chassi,
            filtro_vendedor=filtro_vendedor,
        )
    else:
        permitidas = lojas_permitidas_ids()
        pagination = venda_service.paginar_vendas(
            page=page, per_page=per_page,
            lojas_permitidas_ids=permitidas,
            status=status_filtro, busca=busca, loja_id=loja_id,
            data_inicio=data_inicio, data_fim=data_fim, chassi=filtro_chassi,
        )
```

> Nota: no critério 'vendedor', `loja_id` (filtro manual da UI) continua aplicável como refinamento adicional — `_query_vendas` aplica `loja_id` independentemente. Isso é desejável (o usuário pode refinar por loja dentro dos seus pedidos).

- [ ] **Step 2: Passar o critério ao template (badge informativo)**

No `render_template('hora/vendas_lista.html', ...)`, adicionar:

```python
        criterio_pedidos=criterio,
```

- [ ] **Step 3: Mostrar o critério ativo na listagem (1 linha no template)**

Em `app/templates/hora/vendas_lista.html`, perto do cabeçalho/filtros, adicionar um badge informativo:

```jinja
{% if criterio_pedidos == 'vendedor' %}
  <span class="badge bg-info text-dark">Exibindo apenas os seus pedidos (critério: vendedor)</span>
{% endif %}
```

- [ ] **Step 4: Verificação manual**

Rodar app, com um usuário não-admin escopado: alterar (Task 7) seu critério para 'vendedor' e confirmar que `/hora/vendas` mostra só pedidos onde ele é vendedor/criador; voltar para 'loja' e confirmar o comportamento antigo.

- [ ] **Step 5: Commit**

```bash
git add app/hora/routes/vendas.py app/templates/hora/vendas_lista.html
git commit -m "feat(hora): vendas_lista respeita criterio_pedidos_hora (loja|vendedor)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 7: UI de permissões — escolher o critério por usuário

**Files:**
- Modify: `app/hora/routes/permissoes.py:1-11` (docstring), nova rota após `permissoes_set_loja` (`:201`)
- Modify: `app/templates/hora/permissoes_lista.html:108-122` (bloco do card)

- [ ] **Step 1: Novo endpoint `permissoes_set_criterio_pedidos`**

Em `app/hora/routes/permissoes.py`, após `permissoes_set_loja` (`:201`):

```python
@hora_bp.route('/permissoes/<int:user_id>/criterio-pedidos', methods=['POST'])
@require_hora_perm('usuarios', 'editar')
def permissoes_set_criterio_pedidos(user_id: int):
    """Define o criterio de listagem de pedidos de venda do usuario.

    'loja' (padrao) = escopo por loja_hora_id; 'vendedor' = pedidos do proprio
    usuario (vendedor/criador), ignorando loja.
    """
    usuario = Usuario.query.get_or_404(user_id)
    bloqueio = _bloqueia_se_alvo_invalido(usuario)
    if bloqueio:
        flash(bloqueio, 'danger')
        return redirect(url_for('hora.permissoes_lista'))
    criterio = (request.form.get('criterio_pedidos_hora') or '').strip().lower()
    if criterio not in ('loja', 'vendedor'):
        flash('Criterio invalido (use loja ou vendedor).', 'danger')
        return redirect(url_for('hora.permissoes_lista'))
    usuario.criterio_pedidos_hora = criterio
    db.session.commit()
    rotulo = 'por loja' if criterio == 'loja' else 'por vendedor (seus pedidos)'
    flash(f'{usuario.nome}: pedidos filtrados {rotulo}.', 'success')
    return redirect(url_for('hora.permissoes_lista'))
```

Atualizar a docstring do topo do módulo (`:3-10`) listando a nova rota.

- [ ] **Step 2: Select no template**

Em `app/templates/hora/permissoes_lista.html`, dentro do `<div class="ms-auto d-flex gap-2 flex-wrap">`, após o form "Loja segregada" (`:122`), adicionar:

```jinja
        {# Criterio de pedidos: loja (padrao) vs vendedor #}
        <form method="post" action="{{ url_for('hora.permissoes_set_criterio_pedidos', user_id=u.id) }}"
              class="d-flex gap-1 m-0">
          <select name="criterio_pedidos_hora" class="form-select form-select-sm"
                  {% if not u.sistema_lojas %}disabled{% endif %}
                  title="Como filtrar a lista de Pedidos de Venda deste usuario">
            <option value="loja" {% if (u.criterio_pedidos_hora or 'loja') == 'loja' %}selected{% endif %}>Pedidos: por loja</option>
            <option value="vendedor" {% if u.criterio_pedidos_hora == 'vendedor' %}selected{% endif %}>Pedidos: por vendedor</option>
          </select>
          <button type="submit" class="btn btn-sm btn-outline-primary"
                  {% if not u.sistema_lojas %}disabled{% endif %}>Salvar critério</button>
        </form>
```

- [ ] **Step 3: Verificação manual**

Rodar app, abrir `/hora/permissoes`, trocar o critério de um usuário para "por vendedor", salvar → flash de sucesso; recarregar e confirmar persistência.

- [ ] **Step 4: Commit**

```bash
git add app/hora/routes/permissoes.py app/templates/hora/permissoes_lista.html
git commit -m "feat(hora): UI de permissoes define criterio_pedidos_hora por usuario

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Parte 1 — Unificação das telas

### Task 8: Corrigir bug latente `hora.venda_detalhe` → `hora.vendas_detalhe`

**Files:**
- Modify: `app/hora/routes/vendas.py:1009`, `:1029`

- [ ] **Step 1: Corrigir os 2 redirects**

Em `vendas.py`, nas funções `venda_adicionar_item_peca` (`:1009`) e `venda_remover_item_peca` (`:1029`), trocar `url_for('hora.venda_detalhe', ...)` por `url_for('hora.vendas_detalhe', venda_id=...)`. (Conferir o nome exato do kwarg de id usado nas demais rotas: `venda_id`.)

- [ ] **Step 2: Smoke test de url_for**

Run:
```bash
source .venv/bin/activate && python -c "
from app import create_app
app = create_app()
with app.test_request_context():
    from flask import url_for
    print(url_for('hora.vendas_detalhe', venda_id=1))
"
```
Expected: imprime `/hora/vendas/1` sem `BuildError`. (Garante que o nome de rota existe; as 2 callsites agora o usam.)

- [ ] **Step 3: Commit**

```bash
git add app/hora/routes/vendas.py
git commit -m "fix(hora): rotas de item-peca usavam hora.venda_detalhe inexistente (BuildError)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 9: Extrair componente de moto+desconto para partial + JS de módulo

**Files:**
- Create: `app/static/js/hora/pedido_venda.js`
- Create: `app/templates/hora/tagplus/_componente_moto_desconto.html`
- Modify: `app/templates/hora/tagplus/pedido_venda_novo.html` (usar o partial + `<script src>`)

**Objetivo:** isolar o JS (~`:326-939`) num arquivo de módulo e o HTML da seção "Moto vendida" (`:151-218`) num partial Jinja, sem mudar comportamento. O fix da Task 1 já está no JS — preservar.

- [ ] **Step 1: Mover o markup da seção moto para o partial**

Criar `_componente_moto_desconto.html` com o bloco `:151-218` (linhas de Modelo/Cor/Chassi + Preço/Desconto%/DescontoR$/Valor). Manter exatamente os ids atuais (`f-modelo`, `f-cor`, `f-chassi`, `f-preco-tabela`, `f-desconto-pct`, `f-desconto-rs`, `f-valor`) para não quebrar o JS.

- [ ] **Step 2: Mover o JS para `pedido_venda.js`**

Mover o conteúdo de `<script>` (`:326-939`) para `app/static/js/hora/pedido_venda.js`. Trocar as referências Jinja de URL (`{{ url_for('hora.tagplus_pedido_venda_api_*') }}`) por `data-*` attributes lidos do DOM (ex.: `data-url-cores`, `data-url-chassis`, `data-url-preco`) num elemento âncora — pois um `.js` estático não passa por Jinja. Adicionar esses `data-*` no container do form em `pedido_venda_novo.html`.

- [ ] **Step 3: Wire no template de criação**

Em `pedido_venda_novo.html`: substituir o bloco da seção moto por `{% include 'hora/tagplus/_componente_moto_desconto.html' %}`; remover o `<script>` inline; adicionar `<script src="{{ url_for('static', filename='js/hora/pedido_venda.js') }}?v=2026-06-03"></script>` no fim; adicionar os `data-url-*` no container.

- [ ] **Step 4: Verificação manual (paridade total)**

Rodar app, `/hora/tagplus/pedido-venda/novo`: cascata modelo→cor→chassi funciona; desconto sincroniza; ViaCEP funciona; submit cria pedido. **Sem regressão** vs antes. Conferir console do navegador sem erros JS.

- [ ] **Step 5: Commit**

```bash
git add app/static/js/hora/pedido_venda.js app/templates/hora/tagplus/_componente_moto_desconto.html app/templates/hora/tagplus/pedido_venda_novo.html
git commit -m "refactor(hora): extrai componente moto+desconto (partial + JS de modulo)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 10: Tela unificada renderizada por `vendas_detalhe` (modo edição)

**Files:**
- Modify: `app/hora/routes/vendas.py:222` (`vendas_detalhe`) e/ou criar helper de contexto compartilhado
- Modify: `app/templates/hora/tagplus/pedido_venda_novo.html` (aceitar `venda` opcional → modo edição)

**Estratégia:** a tela passa a receber um objeto `venda` opcional. Sem `venda` = modo criação (atual). Com `venda` = modo edição: pré-preenche cliente/endereço/pagamento/itens e renderiza a barra de ações + edição por seção.

- [ ] **Step 1: `vendas_detalhe` monta o contexto da tela unificada**

Em `vendas_detalhe` (`vendas.py:222`), montar o MESMO contexto que `tagplus_pedido_venda_novo` monta (listas de `modelos`, `formas_pagamento`, `vendedores_disponiveis`, `lojas`) + o objeto `venda` (com itens, pagamentos, divergências, auditoria, emissão NFe). Renderizar `hora/tagplus/pedido_venda_novo.html`. **Extrair** a montagem das listas de lookup para um helper compartilhado (ex.: `_contexto_pedido_venda()`) reusado pelas duas rotas (DRY). Conferir, em `tagplus_routes.tagplus_pedido_venda_novo` (`:1008`), exatamente quais variáveis o template espera hoje, para replicá-las.

- [ ] **Step 2: Template — bifurcar criação vs edição**

No `pedido_venda_novo.html`, envolver com `{% if venda %}` (edição) / `{% else %}` (criação). Em edição:
- Pré-preencher os `value=` de cada campo com os dados de `venda`.
- Renderizar a barra de ações por status (Task 11).
- Form de criação (POST `tagplus_pedido_venda_criar`) só no modo criação; em edição, cada seção posta para a rota granular correspondente.

- [ ] **Step 3: Verificação manual**

`/hora/vendas/<id>` (qualquer pedido) renderiza a nova tela com os dados carregados. `/hora/tagplus/pedido-venda/novo` continua criando. Ambas usam o partial/JS da Task 9.

- [ ] **Step 4: Commit**

```bash
git add app/hora/routes/vendas.py app/templates/hora/tagplus/pedido_venda_novo.html
git commit -m "feat(hora): vendas_detalhe renderiza a tela unificada (modo edicao)

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 11: Migrar TODAS as ações/seções de `venda_detalhe.html` para a tela unificada

**Files:**
- Modify: `app/templates/hora/tagplus/pedido_venda_novo.html` (bloco de edição)
- Reference: `app/templates/hora/venda_detalhe.html` (origem das ações)

**Checklist de paridade — cada item deve existir na tela unificada (modo edição), com a MESMA condição de status/permissão de `venda_detalhe.html`:**

- [ ] Timeline de status (Criado/Confirmado/Faturado/Cancelado).
- [ ] Confirmar pedido → POST `hora.vendas_confirmar` (if `is_cotacao and pode_editar`).
- [ ] Emitir NFe → link `hora.venda_nfe_preview` (if `is_confirmado and pode_criar`).
- [ ] Voltar para cotação → POST `hora.vendas_voltar_cotacao` (if `is_confirmado and pode_aprovar`).
- [ ] Gerenciar NFe → `hora.venda_nfe_status` (if `is_faturado and tem_emissao and pode_criar`).
- [ ] Cancelar pedido → POST `hora.vendas_cancelar` (if `not is_cancelado and pode_apagar`).
- [ ] Descartar NF teste → POST `hora.vendas_descartar_teste` (perm `vendas_descarte/apagar`).
- [ ] Reimportar do TagPlus → POST `hora.tagplus_backfill_nfe_unica` (if condições).
- [ ] DANFE original → `hora.vendas_download_pdf` (if `arquivo_pdf_s3_key`).
- [ ] Divergências abertas → POST `hora.vendas_resolver_divergencia` por item.
- [ ] Definir/Trocar loja → POST `hora.vendas_definir_loja` (if `pode_editar and not is_cancelado`).
- [ ] Vendedor (mini-form) → POST `hora.vendas_editar`.
- [ ] Header cliente/endereço/frete/obs → POST `hora.vendas_editar` (respeitando matriz por status: `is_cotacao`/`is_confirmado`/`is_faturado`).
- [ ] Formas de pagamento → POST `hora.vendas_pagamentos_editar` (if `permite_editar_pagamentos and pode_editar`).
- [ ] Itens: editar chassi/valor → POST `hora.vendas_item_editar` (if `is_cotacao`), usando o componente de cascata (Task 9) em vez do input manual.
- [ ] Itens: remover → POST `hora.vendas_item_remover` (if `is_cotacao`).
- [ ] Adicionar item moto → POST `hora.vendas_item_adicionar` (if `is_cotacao`), usando o componente de cascata.
- [ ] Itens-peça: remover → POST `hora.venda_remover_item_peca`; adicionar → POST `hora.venda_adicionar_item_peca`.
- [ ] Histórico de auditoria + histórico de divergências (`<details>`).

- [ ] **Step 1:** Para cada item do checklist, copiar o bloco correspondente de `venda_detalhe.html` para o bloco `{% if venda %}` da tela unificada, preservando condição de status/permissão. Conferir os `{% set pode_* = current_user.tem_perm_hora('vendas', ...) %}` no topo (`venda_detalhe.html:4-7`).
- [ ] **Step 2:** Para "adicionar item moto" e "editar item", trocar o input manual de chassi pelo `{% include 'hora/tagplus/_componente_moto_desconto.html' %}` + JS (Task 9). O submit envia `numero_chassi`/`valor_final` (o backend deriva o desconto — `venda_service.py:1284`). Ajustar os `name=` do componente para casar com o que `vendas_item_adicionar`/`vendas_item_editar` leem (`numero_chassi`/`valor_final` e `novo_chassi`/`valor_final` — conferir `vendas.py:511-512,554-555`).
- [ ] **Step 3:** Migrar os 2 blocos `<script>` de `venda_detalhe.html` (`:1001-1218`: editor de pagamentos multi-formas + preview de frete CIF) para a tela unificada (reusar do `pedido_venda.js` quando possível; senão incluir no bloco de edição).
- [ ] **Step 4: Verificação manual exaustiva por status** — criar/abrir pedidos em COTACAO, CONFIRMADO, FATURADO, CANCELADO e validar que cada ação aparece/some conforme o status e que cada POST funciona (confirmar, cancelar, editar header, add/remove/edit item com cascata, editar pagamentos, definir loja, resolver divergência). Conferir console sem erros JS.
- [ ] **Step 5: Rodar a suíte HORA** (garante que o backend de workflow não regrediu):

```bash
source .venv/bin/activate && DATABASE_URL="$DATABASE_URL" pytest tests/hora/ -v
```
Expected: verde (incluindo `test_pedido_workflow.py` e `test_pedido_filtro_vendedor.py`).

- [ ] **Step 6: Commit**

```bash
git add app/templates/hora/tagplus/pedido_venda_novo.html
git commit -m "feat(hora): tela unificada ganha todas as acoes de workflow do pedido

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 12: Remover `venda_detalhe.html` e reapontar onboarding

**Files:**
- Delete: `app/templates/hora/venda_detalhe.html`
- Modify: `app/static/onboarding/tours/hora/vendas_aprovar.js` (reapontar IDs para a tela unificada)
- Verify: nenhuma rota faz `render_template('hora/venda_detalhe.html')`

- [ ] **Step 1: Confirmar que nada mais renderiza o template**

Run:
```bash
grep -rn "venda_detalhe.html" app/ || echo "nenhuma referencia"
```
Expected: nenhuma referência em `render_template`. (Se restar, migrar antes de deletar.)

- [ ] **Step 2: Deletar o template**

```bash
git rm app/templates/hora/venda_detalhe.html
```

- [ ] **Step 3: Reapontar o tour**

Ajustar `vendas_aprovar.js` para os novos IDs/seções da tela unificada (ou consolidar com `venda_manual_nova.js`). Validar em `/admin/onboarding/health` e `/admin/onboarding/preview?tour=hora.vendas_aprovar`. Conferir que o tour está incluído em `app/templates/admin/onboarding_health.html` e `onboarding_preview.html` (regra do CLAUDE.md HORA seção Onboarding).

- [ ] **Step 4: Verificação manual** — abrir `/hora/vendas/<id>` e disparar o tour; confirmar que aponta para elementos existentes.

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "refactor(hora): remove venda_detalhe.html (unificado) + reaponta onboarding

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 13: Atualizar CLAUDE.md do módulo + índice de planos + self-review

**Files:**
- Modify: `app/hora/CLAUDE.md` (registrar a unificação e o critério de pedidos)
- Modify: `docs/superpowers/plans/INDEX.md` (ponteiro para este plano)

- [ ] **Step 1: Documentar no CLAUDE.md HORA** uma seção curta: "Pedido de Venda — tela unificada (criação+edição) e critério loja/vendedor", apontando para spec e plano, e registrando `usuarios.criterio_pedidos_hora` + `hora_venda.criado_por_id` (migration hora_44).
- [ ] **Step 2: Registrar o plano** em `docs/superpowers/plans/INDEX.md` (1 linha ponteiro).
- [ ] **Step 3: Self-review final** — reler o spec (`2026-06-03-hora-unificar-pedido-venda-design.md`) e marcar que cada requisito foi entregue: (2) fix desconto ✓, (3) filtro loja/vendedor ✓ (migration+model+service+rota+UI), (1) unificação ✓ (partial+JS, vendas_detalhe→tela unificada, paridade de ações, venda_detalhe.html removida, bug latente corrigido).
- [ ] **Step 4: Rodar a suíte HORA inteira + lint UI**:

```bash
source .venv/bin/activate && DATABASE_URL="$DATABASE_URL" pytest tests/hora/ -q
python scripts/audits/ui_policy_lint.py --enforce-new
```
Expected: testes verdes; lint sem violações novas.

- [ ] **Step 5: Commit**

```bash
git add app/hora/CLAUDE.md docs/superpowers/plans/INDEX.md
git commit -m "docs(hora): registra unificacao do pedido de venda + criterio loja/vendedor

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review do plano (preenchido)

**Cobertura do spec:**
- Parte 2 (fix desconto) → Task 1. ✓
- Parte 3 (filtro): migration → Task 2; modelos → Task 3; `criado_por_id` na criação → Task 4; filtro em `_query_vendas` → Task 5; `vendas_lista` → Task 6; UI permissões → Task 7. ✓
- Parte 1 (unificação): bug latente → Task 8; extração componente → Task 9; modo edição → Task 10; paridade de ações → Task 11; remoção `venda_detalhe.html` + onboarding → Task 12; docs → Task 13. ✓

**Consistência de tipos:** `filtro_vendedor` é `dict {'nomes': list[str], 'user_id': int}` em `_query_vendas`, `paginar_vendas` (Task 5) e na montagem em `vendas_lista` (Task 6). `criado_por_id` é `int|None` em modelo (Task 3), criação (Task 4) e filtro (Task 5). `criterio_pedidos_hora` é `str ('loja'|'vendedor')` em modelo (Task 3), rota (Task 6/7) e migration (Task 2).

**Riscos:** Task 11 (paridade) é o ponto de maior risco — mitigado pelo checklist explícito + suíte `tests/hora/` (Task 11 Step 5) + verificação manual por status. Task 9 (JS estático perde Jinja) — mitigado por `data-*` attributes para URLs.
