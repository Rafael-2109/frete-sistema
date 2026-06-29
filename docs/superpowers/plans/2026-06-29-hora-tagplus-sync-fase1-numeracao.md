<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-29
-->
# HORA ↔ TagPlus — Fase 1: Numeração visível do pedido — Implementation Plan

> **Papel:** plano task-by-task da Fase 1 (item 2 do design) — capturar e exibir o **número visível** do pedido TagPlus (`pedido['numero']`) no lugar do ID interno. Independente das Fases 2/3.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** persistir e exibir o número visível do pedido TagPlus em `hora_venda`, eliminando a inconsistência de mostrar o ID interno como se fosse o número do pedido.

**Architecture:** nova coluna `hora_venda.tagplus_pedido_numero` (INTEGER NULL). Capturada em 3 pontos — webhook `nfe_aprovada` (de `pedido_os_vinculada.numero`, que já chega no `GET /nfes/{id}`), backfill de enriquecimento (de `pedido['numero']`) e backfill histórico (do JSONB `tagplus_pedido_payload['numero']` já salvo, sem nova chamada à API). A listagem passa a exibir o número (fallback `—`).

**Tech Stack:** Flask 3.1 + SQLAlchemy 2.0 + Jinja2/Bootstrap 5; PostgreSQL; pytest (`tests/hora/`).

**Spec:** `docs/superpowers/specs/2026-06-29-hora-tagplus-sync-bidirecional-design.md`.

## Indice

- [Global Constraints](#global-constraints)
- [Task 1: Migration + coluna no modelo](#task-1-migration--coluna-no-modelo)
- [Task 2: Captura do número no webhook nfe_aprovada](#task-2-captura-do-numero-no-webhook-nfe_aprovada)
- [Task 3: Captura do número no backfill de enriquecimento](#task-3-captura-do-numero-no-backfill-de-enriquecimento)
- [Task 4: Backfill histórico do JSONB](#task-4-backfill-historico-do-jsonb)
- [Task 5: Exibir número na listagem de vendas](#task-5-exibir-numero-na-listagem-de-vendas)
- [Task 6: Doc + suíte completa](#task-6-doc--suite-completa)
- [Self-Review](#self-review)

## Global Constraints

- **Migration = par DDL + Python** (`scripts/migrations/hora_62_*.{sql,py}`), idempotente (`ADD COLUMN IF NOT EXISTS`). Padrão: `scripts/migrations/hora_58_venda_telefone_lead.{sql,py}`.
- **Schema JSON é fonte de verdade dos campos** — após alterar `hora_venda`, regenerar com `python .claude/skills/consultando-sql/scripts/generate_schemas.py` (regra CLAUDE.md).
- **Tipo do campo:** `pedido['numero']` é INTEGER no contrato TagPlus (ver spec). Coluna `INTEGER NULL`.
- **Não tocar** o fluxo de emissão NFe nem `cancelar_venda` (isso é Fase 2/3). Fase 1 é só captura + exibição.
- **Invariante HORA:** nada de `UPDATE hora_moto`; esta fase não mexe em estoque.
- Rodar testes com `source .venv/bin/activate` antes do `pytest`.

---

### Task 1: Migration + coluna no modelo

**Files:**
- Create: `scripts/migrations/hora_62_venda_tagplus_pedido_numero.sql`
- Create: `scripts/migrations/hora_62_venda_tagplus_pedido_numero.py`
- Modify: `app/hora/models/venda.py:197-203` (adicionar coluna após `tagplus_pedido_id`/`tagplus_pedido_payload`)
- Modify (gerado): `.claude/skills/consultando-sql/schemas/tables/hora_venda.json`

**Interfaces:**
- Produces: `HoraVenda.tagplus_pedido_numero` (Integer, nullable, indexed) — consumido pelas Tasks 2-5.

- [ ] **Step 1: Escrever o SQL da migration**

```sql
-- scripts/migrations/hora_62_venda_tagplus_pedido_numero.sql
-- Idempotente. Adiciona tagplus_pedido_numero (INTEGER, NULL) a hora_venda.
-- Numero VISIVEL do pedido no TagPlus (pedido['numero'] / pedido_os_vinculada.numero),
-- distinto do tagplus_pedido_id (ID interno). Resolve a inconsistencia de exibir
-- o ID como se fosse o numero. Migration HORA 62 (2026-06-29).
ALTER TABLE hora_venda ADD COLUMN IF NOT EXISTS tagplus_pedido_numero INTEGER;
CREATE INDEX IF NOT EXISTS ix_hora_venda_tagplus_pedido_numero
    ON hora_venda (tagplus_pedido_numero);
```

- [ ] **Step 2: Escrever o runner Python da migration**

```python
"""Migration HORA 62: coluna tagplus_pedido_numero em hora_venda.

Adiciona `tagplus_pedido_numero` (INTEGER, NULL) — numero VISIVEL do pedido no
TagPlus, distinto do `tagplus_pedido_id` (ID interno). Idempotente
(ADD COLUMN IF NOT EXISTS + CREATE INDEX IF NOT EXISTS).

Uso:
    # Local:
    python scripts/migrations/hora_62_venda_tagplus_pedido_numero.py
    # PROD (Render):
    DATABASE_URL="$DATABASE_URL_PROD" python scripts/migrations/hora_62_venda_tagplus_pedido_numero.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    "ALTER TABLE hora_venda ADD COLUMN IF NOT EXISTS tagplus_pedido_numero INTEGER",
    "CREATE INDEX IF NOT EXISTS ix_hora_venda_tagplus_pedido_numero "
    "ON hora_venda (tagplus_pedido_numero)",
]


def _colunas() -> list:
    return [c['name'] for c in inspect(db.engine).get_columns('hora_venda')]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        print('Estado antes:')
        print(f'  hora_venda.tagplus_pedido_numero existe? {"tagplus_pedido_numero" in _colunas()}')

        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))

        existe = 'tagplus_pedido_numero' in _colunas()
        print('\nEstado depois:')
        print(f'  hora_venda.tagplus_pedido_numero existe? {existe}')

        if not existe:
            print('\nERRO: coluna nao foi criada.')
            sys.exit(1)

        print('\nMigration HORA 62 concluida com sucesso.')


if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Adicionar a coluna no modelo**

Em `app/hora/models/venda.py`, logo após o bloco `tagplus_pedido_payload` (linha ~203), inserir:

```python
    tagplus_pedido_numero = db.Column(db.Integer, nullable=True, index=True)
    # Numero VISIVEL do pedido no TagPlus (pedido['numero'] / pedido_os_vinculada.numero).
    # Distinto de tagplus_pedido_id (ID interno). Exibido ao usuario como "Pedido TP".
    # Capturado no webhook nfe_aprovada, no backfill de enriquecimento e no backfill
    # historico (do JSONB tagplus_pedido_payload['numero']). Migration hora_62.
```

- [ ] **Step 4: Rodar a migration no banco local**

Run: `python scripts/migrations/hora_62_venda_tagplus_pedido_numero.py`
Expected: `Migration HORA 62 concluida com sucesso.`

- [ ] **Step 5: Regenerar o schema JSON e verificar ausência de drift**

Run: `python .claude/skills/consultando-sql/scripts/generate_schemas.py && python .claude/skills/consultando-sql/scripts/generate_schemas.py --check`
Expected: o `--check` sai com código 0 (sem drift) e `hora_venda.json` contém `tagplus_pedido_numero`.

- [ ] **Step 6: Commit**

```bash
git add scripts/migrations/hora_62_venda_tagplus_pedido_numero.sql scripts/migrations/hora_62_venda_tagplus_pedido_numero.py app/hora/models/venda.py .claude/skills/consultando-sql/schemas/tables/hora_venda.json
git commit -m "feat(hora): coluna tagplus_pedido_numero (numero visivel do pedido TagPlus) — migration hora_62"
```

---

### Task 2: Captura do número no webhook nfe_aprovada

**Files:**
- Modify: `app/hora/services/tagplus/webhook_handler.py` (helper novo + bloco de captura em `_handle_aprovada`, ~linha 157-177)
- Test: `tests/hora/test_tagplus_pedido_numero.py`

**Interfaces:**
- Consumes: `HoraVenda.tagplus_pedido_numero` (Task 1).
- Produces: `webhook_handler._extrair_pedido_id_numero(detalhes: dict) -> tuple[int | None, int | None]` (id, numero) — reusada na captura.

- [ ] **Step 1: Escrever o teste do helper puro (falha)**

```python
# tests/hora/test_tagplus_pedido_numero.py
from app.hora.services.tagplus.webhook_handler import _extrair_pedido_id_numero


def test_extrai_id_e_numero_do_pedido_vinculado():
    detalhes = {'pedido_os_vinculada': {'id': 5, 'numero': 941, 'tipo': 'P'}}
    assert _extrair_pedido_id_numero(detalhes) == (5, 941)


def test_extrai_none_quando_sem_pedido_vinculado():
    assert _extrair_pedido_id_numero({}) == (None, None)
    assert _extrair_pedido_id_numero({'pedido_os_vinculada': None}) == (None, None)
    assert _extrair_pedido_id_numero({'pedido_os_vinculada': {'id': 5}}) == (5, None)
```

- [ ] **Step 2: Rodar o teste para confirmar a falha**

Run: `pytest tests/hora/test_tagplus_pedido_numero.py -v`
Expected: FAIL com `ImportError: cannot import name '_extrair_pedido_id_numero'`.

- [ ] **Step 3: Implementar o helper**

No topo de `app/hora/services/tagplus/webhook_handler.py` (após os imports, antes da classe `WebhookHandler`), adicionar:

```python
def _extrair_pedido_id_numero(detalhes: dict) -> tuple:
    """Extrai (id, numero) de detalhes['pedido_os_vinculada'].

    A NFe (GET /nfes/{id}) traz pedido_os_vinculada={id, numero, tipo} — o
    `numero` e o numero VISIVEL do pedido. Retorna (None, None) quando ausente.
    """
    pv = detalhes.get('pedido_os_vinculada') or {}
    if not isinstance(pv, dict):
        return None, None
    pid = pv.get('id')
    pnum = pv.get('numero')
    return (
        pid if isinstance(pid, int) else None,
        pnum if isinstance(pnum, int) else None,
    )
```

- [ ] **Step 4: Rodar o teste para confirmar que passa**

Run: `pytest tests/hora/test_tagplus_pedido_numero.py -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Wire no `_handle_aprovada`**

Em `app/hora/services/tagplus/webhook_handler.py`, substituir o bloco atual de captura do pedido (linhas ~160-164):

```python
        pedido_vincul = detalhes.get('pedido_os_vinculada') or {}
        if isinstance(pedido_vincul, dict):
            pid = pedido_vincul.get('id')
            if isinstance(pid, int):
                emissao.tagplus_pedido_id = pid
```

por:

```python
        pid, pnum = _extrair_pedido_id_numero(detalhes)
        if pid is not None:
            emissao.tagplus_pedido_id = pid
```

E no bloco `if venda:` (após a linha que espelha `venda.tagplus_pedido_id`, ~linha 176-177), adicionar o espelhamento do numero:

```python
            if pnum is not None and not venda.tagplus_pedido_numero:
                venda.tagplus_pedido_numero = pnum
```

- [ ] **Step 6: Escrever o teste de integração do webhook (captura na venda)**

Acrescentar a `tests/hora/test_tagplus_pedido_numero.py`:

```python
from decimal import Decimal
from unittest.mock import patch

from app import db as _db
from app.hora.models.venda import HoraVenda, VENDA_STATUS_CONFIRMADO
from app.hora.models.tagplus import (
    HoraTagPlusConta, HoraTagPlusNfeEmissao, NFE_STATUS_ENVIADA_SEFAZ,
)
from app.hora.services.tagplus.webhook_handler import WebhookHandler


def _conta():
    c = HoraTagPlusConta(
        client_id='cid', client_secret_encrypted='x', webhook_secret='s',
    )
    _db.session.add(c)
    _db.session.flush()
    return c


def test_webhook_aprovada_grava_numero_visivel_na_venda(db):
    conta = _conta()
    venda = HoraVenda(
        cpf_cliente='12345678901', nome_cliente='Cli',
        valor_total=Decimal('100.00'), status=VENDA_STATUS_CONFIRMADO,
    )
    _db.session.add(venda)
    _db.session.flush()
    emissao = HoraTagPlusNfeEmissao(
        venda_id=venda.id, conta_id=conta.id, status=NFE_STATUS_ENVIADA_SEFAZ,
        tagplus_nfe_id=99,
    )
    _db.session.add(emissao)
    _db.session.flush()

    detalhes = {
        'numero': 1234, 'serie': 1, 'chave_acesso': '4' * 44,
        'pedido_os_vinculada': {'id': 5, 'numero': 941, 'tipo': 'P'},
    }
    with patch.object(WebhookHandler, '_buscar_detalhes', return_value=detalhes):
        WebhookHandler._handle_aprovada(emissao, client=None, tagplus_nfe_id=99)

    assert emissao.tagplus_pedido_id == 5
    assert venda.tagplus_pedido_numero == 941
```

> NOTA p/ executor: confirmar a assinatura real de `_handle_aprovada` antes de chamar (no código lido é `_handle_aprovada(emissao, client, tagplus_nfe_id)` espelhando `_handle_denegada`). Se `_buscar_detalhes` já tiver sido chamado fora do método, ajustar o ponto de patch. O objetivo do teste — `venda.tagplus_pedido_numero == 941` — não muda.

- [ ] **Step 7: Rodar os testes**

Run: `pytest tests/hora/test_tagplus_pedido_numero.py -v`
Expected: PASS (3 testes).

- [ ] **Step 8: Commit**

```bash
git add app/hora/services/tagplus/webhook_handler.py tests/hora/test_tagplus_pedido_numero.py
git commit -m "feat(hora): captura numero visivel do pedido TagPlus no webhook nfe_aprovada"
```

---

### Task 3: Captura do número no backfill de enriquecimento

**Files:**
- Modify: `app/hora/services/tagplus/pedido_backfill_service.py:155-158` (em `_aplicar_pedido_em_venda`)
- Test: `tests/hora/test_tagplus_pedido_numero.py` (acrescentar)

**Interfaces:**
- Consumes: `HoraVenda.tagplus_pedido_numero` (Task 1); `pedido_service.importar_pedido` (existente, retorna dict com `numero`).

- [ ] **Step 1: Escrever o teste (falha)**

Acrescentar a `tests/hora/test_tagplus_pedido_numero.py`:

```python
from unittest.mock import MagicMock
from app.hora.services.tagplus import pedido_backfill_service


def test_backfill_enriquecimento_grava_numero(db, monkeypatch):
    venda = HoraVenda(
        cpf_cliente='12345678901', nome_cliente='Cli',
        valor_total=Decimal('100.00'),
    )
    _db.session.add(venda)
    _db.session.flush()

    pedido = {'id': 5, 'numero': 777, 'status': 'B'}
    monkeypatch.setattr(
        pedido_backfill_service.pedido_service, 'importar_pedido',
        lambda api, pid: pedido,
    )

    res = pedido_backfill_service._aplicar_pedido_em_venda(
        api=MagicMock(), venda=venda, pedido_id_tp=5, operador='tester',
    )

    assert res['status'] == 'enriquecida'
    assert venda.tagplus_pedido_numero == 777
```

- [ ] **Step 2: Rodar para confirmar a falha**

Run: `pytest tests/hora/test_tagplus_pedido_numero.py::test_backfill_enriquecimento_grava_numero -v`
Expected: FAIL com `assert None == 777`.

- [ ] **Step 3: Implementar a captura**

Em `app/hora/services/tagplus/pedido_backfill_service.py`, dentro de `_aplicar_pedido_em_venda`, logo após `venda.tagplus_pedido_payload = sanitize_for_json(pedido)` (linha ~158), inserir:

```python
    pnum = pedido.get('numero')
    if isinstance(pnum, int) and venda.tagplus_pedido_numero != pnum:
        venda.tagplus_pedido_numero = pnum
        alteracoes.append(f'tagplus_pedido_numero={pnum}')
```

- [ ] **Step 4: Rodar para confirmar que passa**

Run: `pytest tests/hora/test_tagplus_pedido_numero.py::test_backfill_enriquecimento_grava_numero -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/hora/services/tagplus/pedido_backfill_service.py tests/hora/test_tagplus_pedido_numero.py
git commit -m "feat(hora): captura numero visivel no backfill de enriquecimento de pedido TagPlus"
```

---

### Task 4: Backfill histórico do JSONB

**Files:**
- Modify: `app/hora/services/tagplus/pedido_backfill_service.py` (nova função `backfill_numero_do_payload`)
- Test: `tests/hora/test_tagplus_pedido_numero.py` (acrescentar)

**Interfaces:**
- Produces: `pedido_backfill_service.backfill_numero_do_payload(limite: int | None = None) -> dict` — retorna `{'atualizadas': int, 'sem_numero': int}`. Popula `tagplus_pedido_numero` a partir de `tagplus_pedido_payload['numero']` para vendas já processadas (sem chamar a API).

- [ ] **Step 1: Escrever o teste (falha)**

Acrescentar a `tests/hora/test_tagplus_pedido_numero.py`:

```python
def test_backfill_numero_do_payload_preenche_da_jsonb(db):
    v1 = HoraVenda(
        cpf_cliente='12345678901', nome_cliente='Com payload',
        valor_total=Decimal('100.00'),
        tagplus_pedido_id=5, tagplus_pedido_payload={'id': 5, 'numero': 888},
    )
    v2 = HoraVenda(
        cpf_cliente='12345678902', nome_cliente='Sem numero no payload',
        valor_total=Decimal('100.00'),
        tagplus_pedido_id=6, tagplus_pedido_payload={'id': 6},
    )
    _db.session.add_all([v1, v2])
    _db.session.flush()

    res = pedido_backfill_service.backfill_numero_do_payload()

    assert v1.tagplus_pedido_numero == 888
    assert v2.tagplus_pedido_numero is None
    assert res['atualizadas'] == 1
    assert res['sem_numero'] == 1
```

- [ ] **Step 2: Rodar para confirmar a falha**

Run: `pytest tests/hora/test_tagplus_pedido_numero.py::test_backfill_numero_do_payload_preenche_da_jsonb -v`
Expected: FAIL com `AttributeError: module ... has no attribute 'backfill_numero_do_payload'`.

- [ ] **Step 3: Implementar a função**

Em `app/hora/services/tagplus/pedido_backfill_service.py`, adicionar (no fim do módulo):

```python
def backfill_numero_do_payload(limite=None) -> dict:
    """Popula tagplus_pedido_numero a partir do JSONB tagplus_pedido_payload['numero'].

    Para vendas que ja tem o payload do pedido salvo mas ainda nao tem o numero
    visivel extraido — NAO chama a API. Retorna {'atualizadas', 'sem_numero'}.
    """
    from app.hora.models.venda import HoraVenda
    q = (
        HoraVenda.query
        .filter(HoraVenda.tagplus_pedido_numero.is_(None))
        .filter(HoraVenda.tagplus_pedido_payload.isnot(None))
    )
    if limite:
        q = q.limit(limite)

    atualizadas = 0
    sem_numero = 0
    for venda in q.all():
        payload = venda.tagplus_pedido_payload or {}
        pnum = payload.get('numero') if isinstance(payload, dict) else None
        if isinstance(pnum, int):
            venda.tagplus_pedido_numero = pnum
            atualizadas += 1
        else:
            sem_numero += 1

    if atualizadas:
        db.session.commit()
    return {'atualizadas': atualizadas, 'sem_numero': sem_numero}
```

- [ ] **Step 4: Rodar para confirmar que passa**

Run: `pytest tests/hora/test_tagplus_pedido_numero.py::test_backfill_numero_do_payload_preenche_da_jsonb -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/hora/services/tagplus/pedido_backfill_service.py tests/hora/test_tagplus_pedido_numero.py
git commit -m "feat(hora): backfill historico de tagplus_pedido_numero a partir do JSONB salvo"
```

---

### Task 5: Exibir número na listagem de vendas

**Files:**
- Modify: `app/templates/hora/vendas_lista.html:95` (header) e `:126-133` (célula "Pedido TP")
- Test: `tests/hora/test_tagplus_pedido_numero.py` (acrescentar — testa a lógica da célula via `render_template_string`)

**Interfaces:**
- Consumes: `HoraVenda.tagplus_pedido_numero` (Task 1).

- [ ] **Step 1: Escrever o teste da lógica de exibição (falha)**

Acrescentar a `tests/hora/test_tagplus_pedido_numero.py`:

```python
from types import SimpleNamespace
from flask import render_template_string

# Espelha a logica da celula "Pedido TP" de vendas_lista.html (Task 5).
CELL_TPL = (
    "{% if v.tagplus_pedido_numero %}"
    "<small title=\"Numero do pedido no TagPlus\">nº {{ v.tagplus_pedido_numero }}</small>"
    "{% elif v.tagplus_pedido_id %}"
    "<small class=\"text-muted\" title=\"ID interno (numero ausente)\">#{{ v.tagplus_pedido_id }}</small>"
    "{% else %}<small class=\"text-muted\">—</small>{% endif %}"
)


def test_celula_pedido_tp_prefere_numero(app):
    with app.app_context():
        out = render_template_string(
            CELL_TPL, v=SimpleNamespace(tagplus_pedido_numero=941, tagplus_pedido_id=5),
        )
        assert 'nº 941' in out
        assert '#5' not in out


def test_celula_pedido_tp_fallback_id_quando_sem_numero(app):
    with app.app_context():
        out = render_template_string(
            CELL_TPL, v=SimpleNamespace(tagplus_pedido_numero=None, tagplus_pedido_id=5),
        )
        assert '#5' in out


def test_celula_pedido_tp_traco_quando_vazio(app):
    with app.app_context():
        out = render_template_string(
            CELL_TPL, v=SimpleNamespace(tagplus_pedido_numero=None, tagplus_pedido_id=None),
        )
        assert '—' in out
```

- [ ] **Step 2: Rodar para confirmar a falha**

Run: `pytest tests/hora/test_tagplus_pedido_numero.py -k celula -v`
Expected: PASS imediato dos 3 testes (a lógica está no próprio teste). Servem de especificação executável da célula — copiar a MESMA lógica para o template no Step 3 e validar visualmente.

- [ ] **Step 3: Atualizar o template**

Em `app/templates/hora/vendas_lista.html`, trocar o header (linha 95) de `<th>Pedido TP</th>` por `<th>Pedido TP (nº)</th>` e substituir o bloco da célula (linhas ~126-133):

```jinja
            {% if v.tagplus_pedido_numero %}
              <small title="Número do pedido no TagPlus">nº {{ v.tagplus_pedido_numero }}</small>
            {% elif v.tagplus_pedido_id %}
              <small class="text-muted" title="ID interno do TagPlus (número ainda não capturado)">
                #{{ v.tagplus_pedido_id }}
              </small>
            {% else %}
              <small class="text-muted">—</small>
            {% endif %}
```

- [ ] **Step 4: Validar render da página (smoke)**

Run: `python -c "import app as _; print('import ok')"` e abrir `/hora/vendas` no dev server (`python run.py`) confirmando a coluna "Pedido TP (nº)" exibindo `nº <numero>` quando houver, `#id` no fallback.
Expected: coluna renderiza sem erro de template.

- [ ] **Step 5: Commit**

```bash
git add app/templates/hora/vendas_lista.html tests/hora/test_tagplus_pedido_numero.py
git commit -m "feat(hora): exibe numero visivel do pedido TagPlus na listagem (fallback ID)"
```

---

### Task 6: Doc + suíte completa

**Files:**
- Modify: `app/hora/CLAUDE.md` (nova seção de changelog)
- Test: toda a suíte `tests/hora/`

- [ ] **Step 1: Rodar a suíte HORA completa**

Run: `pytest tests/hora/ -q`
Expected: PASS (incluindo os testes novos de `test_tagplus_pedido_numero.py`), zero regressões.

- [ ] **Step 2: Registrar no CLAUDE.md do módulo**

Em `app/hora/CLAUDE.md`, adicionar ao índice e ao corpo uma seção:

```markdown
## 40. Número visível do pedido TagPlus (`tagplus_pedido_numero`) — 2026-06-29

Fase 1 do design `docs/superpowers/specs/2026-06-29-hora-tagplus-sync-bidirecional-design.md`.
Nova coluna `hora_venda.tagplus_pedido_numero` (migration `hora_62`) guarda o número
VISÍVEL do pedido no TagPlus (`pedido['numero']`), distinto de `tagplus_pedido_id`
(ID interno). Capturado no webhook `nfe_aprovada` (de `pedido_os_vinculada.numero`),
no backfill de enriquecimento (de `pedido['numero']`) e no backfill histórico
`pedido_backfill_service.backfill_numero_do_payload()` (do JSONB já salvo, sem API).
A listagem `vendas_lista.html` passa a exibir o número (fallback `#id`).
```

- [ ] **Step 3: Commit**

```bash
git add app/hora/CLAUDE.md
git commit -m "docs(hora): registra Fase 1 da sync TagPlus (numero visivel do pedido)"
```

---

## Self-Review

- **Cobertura do design (item 2):** coluna (Task 1) + captura webhook (Task 2) + captura backfill (Task 3) + backfill histórico (Task 4) + exibição (Task 5) + doc (Task 6). Item 2 do spec coberto ponta a ponta.
- **Sem placeholders:** todo passo tem SQL/Python/Jinja real e comando com saída esperada.
- **Consistência de tipos:** `tagplus_pedido_numero` é `Integer`/`int` em todas as tasks; `_extrair_pedido_id_numero` retorna `(int|None, int|None)`; `backfill_numero_do_payload` retorna `{'atualizadas','sem_numero'}`.
- **Pendência conhecida:** a assinatura exata de `_handle_aprovada` deve ser confirmada na hora (nota no Step 6 da Task 2) — o invariante testado (`venda.tagplus_pedido_numero`) não muda.
- **Não regride Fase 2/3:** nenhuma escrita ao TagPlus nova; só leitura/captura e exibição.
