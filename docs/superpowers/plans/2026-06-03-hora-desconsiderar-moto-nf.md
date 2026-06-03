<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# HORA — Desconsiderar moto de NF de compra — Implementation Plan

> **Papel:** plano de implementação task-by-task da funcionalidade de desconsiderar item (moto) de NF de entrada no módulo HORA.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** permitir marcar um item de NF de entrada como "desconsiderado" — removendo a moto do estoque/recebimento e do cadastro `hora_moto`, mantendo o item na NF (reversível), com validação de "não em pedido / não recebido".

**Architecture:** flag `desconsiderado` em `HoraNfEntradaItem` + relaxamento da FK `numero_chassi → hora_moto` (substituída por validação aplicativa). Serviços `desconsiderar_item_nf`/`reconsiderar_item_nf` em `nf_entrada_service`. Property `HoraNfEntrada.itens_considerados` aplicada nos pontos de recebimento/matching. UI no detalhe da NF.

**Tech Stack:** Flask 3.1 + SQLAlchemy 2.0 + Jinja2/Bootstrap 5; PostgreSQL; pytest (`tests/hora/`).

**Spec:** `docs/superpowers/specs/2026-06-03-hora-desconsiderar-moto-nf-design.md`.

---

## Indice

- [File Structure](#file-structure)
- [Convenções do módulo (ler antes)](#convenções-do-módulo-ler-antes)
- [Task 1: Migration hora_43 (coluna + drop FK)](#task-1-migration-hora_43-coluna-drop-fk)
- [Task 2: Modelo — campo, FK relaxada, property](#task-2-modelo-campo-fk-relaxada-property)
- [Task 3: Helpers de validação](#task-3-helpers-de-validação)
- [Task 4: Serviço desconsiderar_item_nf](#task-4-serviço-desconsiderar_item_nf)
- [Task 5: Serviço reconsiderar_item_nf](#task-5-serviço-reconsiderar_item_nf)
- [Task 6: Aplicar itens_considerados no recebimento e matching](#task-6-aplicar-itens_considerados-no-recebimento-e-matching)
- [Task 7: Rotas em nfs.py](#task-7-rotas-em-nfspy)
- [Task 8: UI no detalhe da NF](#task-8-ui-no-detalhe-da-nf)
- [Task 9: Atualizar app/hora/CLAUDE.md](#task-9-atualizar-apphoraclaudemd)
- [Self-review](#self-review)

## File Structure

| Arquivo | Ação | Responsabilidade |
|---|---|---|
| `scripts/migrations/hora_43_nf_item_desconsiderar.sql` | Criar | DDL idempotente (Render Shell) |
| `scripts/migrations/hora_43_nf_item_desconsiderar.py` | Criar | Migration Python com `create_app()` + before/after |
| `app/hora/models/compra.py` | Modificar | `HoraNfEntradaItem.desconsiderado`, FK relaxada, `relationship` viewonly, `HoraNfEntrada.itens_considerados` |
| `app/hora/services/chassi_protecao_service.py` | Modificar | `chassi_em_pedido()` |
| `app/hora/services/nf_entrada_service.py` | Modificar | `desconsiderar_item_nf`, `reconsiderar_item_nf` + helpers de bloqueio + `assert_item_moto_consistente` |
| `app/hora/services/recebimento_service.py` | Modificar | trocar `nf.itens` → `nf.itens_considerados` (6 pontos de "a receber") |
| `app/hora/services/matching_service.py` | Modificar | `_chassis_nf` exclui desconsiderados |
| `app/hora/routes/nfs.py` | Modificar | rotas POST desconsiderar/reverter |
| `app/templates/hora/nf_detalhe.html` | Modificar | badge + botões + JS |
| `tests/hora/test_desconsiderar_item_nf.py` | Criar | testes da feature |
| `app/hora/CLAUDE.md` | Modificar | seção nova documentando a feature |

## Convenções do módulo (ler antes)

- **Invariante**: `hora_moto` é insert-once; estado = eventos (`hora_moto_evento`), nunca `UPDATE hora_moto.status`. Estoque = último evento ∈ `EVENTOS_EM_ESTOQUE` (`RECEBIDA/CONFERIDA/TRANSFERIDA/...`).
- **Rotas**: padrão do módulo é `return jsonify(...), N` (não `abort()`), decorator `@require_hora_perm('nfs', 'editar')`, AJAX detectado por `request.is_json or request.headers.get('Accept') == 'application/json'`. Ver `app/hora/routes/nfs.py:443` (`nfs_editar_item`) como modelo.
- **Migrations duais** (regra `~/.claude/CLAUDE.md`): `.sql` idempotente + `.py` com `create_app()` e verificação before/after.
- **Testes**: rodar da raiz do repo com `.venv` ativo. Fixtures em `tests/hora/conftest.py`: `nf_entrada_factory(chassis)`, `pedido_compra_factory(chassis)`, `modelo_moto`, `loja_origem`, `chassi_em_estoque`.
- **Timezone**: usar `from app.utils.timezone import agora_utc_naive` (nunca `datetime.now()`; hook bloqueia).

---

## Task 1: Migration hora_43 (coluna + drop FK)

**Files:**
- Create: `scripts/migrations/hora_43_nf_item_desconsiderar.sql`
- Create: `scripts/migrations/hora_43_nf_item_desconsiderar.py`

- [ ] **Step 1: Criar o `.sql` idempotente**

Create `scripts/migrations/hora_43_nf_item_desconsiderar.sql`:

```sql
-- hora_43: NF entrada item — flag desconsiderado + relaxar FK numero_chassi -> hora_moto
-- Spec: docs/superpowers/specs/2026-06-03-hora-desconsiderar-moto-nf-design.md
-- Idempotente (Render Shell).

ALTER TABLE hora_nf_entrada_item
    ADD COLUMN IF NOT EXISTS desconsiderado BOOLEAN NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS ix_hora_nf_entrada_item_desconsiderado
    ON hora_nf_entrada_item (desconsiderado);

-- Drop da FK numero_chassi -> hora_moto (nome auto-gerado pelo PG; descobre via catalogo).
DO $$
DECLARE cname text;
BEGIN
    SELECT conname INTO cname
      FROM pg_constraint
     WHERE conrelid = 'hora_nf_entrada_item'::regclass
       AND contype = 'f'
       AND confrelid = 'hora_moto'::regclass
     LIMIT 1;
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE hora_nf_entrada_item DROP CONSTRAINT %I', cname);
    END IF;
END $$;
```

- [ ] **Step 2: Criar o `.py` com before/after**

Create `scripts/migrations/hora_43_nf_item_desconsiderar.py`:

```python
"""Migration hora_43: NF entrada item — flag desconsiderado + relaxar FK numero_chassi.

Spec: docs/superpowers/specs/2026-06-03-hora-desconsiderar-moto-nf-design.md
Idempotente. Rodar da raiz: python scripts/migrations/hora_43_nf_item_desconsiderar.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy import text  # noqa: E402
from app import create_app, db  # noqa: E402

SQL_COLUNA = (
    "ALTER TABLE hora_nf_entrada_item "
    "ADD COLUMN IF NOT EXISTS desconsiderado BOOLEAN NOT NULL DEFAULT false"
)
SQL_INDEX = (
    "CREATE INDEX IF NOT EXISTS ix_hora_nf_entrada_item_desconsiderado "
    "ON hora_nf_entrada_item (desconsiderado)"
)
SQL_DROP_FK = """
DO $$
DECLARE cname text;
BEGIN
    SELECT conname INTO cname FROM pg_constraint
     WHERE conrelid = 'hora_nf_entrada_item'::regclass
       AND contype = 'f' AND confrelid = 'hora_moto'::regclass
     LIMIT 1;
    IF cname IS NOT NULL THEN
        EXECUTE format('ALTER TABLE hora_nf_entrada_item DROP CONSTRAINT %I', cname);
    END IF;
END $$;
"""

def _col_existe():
    row = db.session.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name='hora_nf_entrada_item' AND column_name='desconsiderado'"
    )).first()
    return row is not None

def _fk_existe():
    row = db.session.execute(text(
        "SELECT conname FROM pg_constraint "
        "WHERE conrelid='hora_nf_entrada_item'::regclass AND contype='f' "
        "AND confrelid='hora_moto'::regclass LIMIT 1"
    )).first()
    return row[0] if row else None

def main():
    app = create_app()
    with app.app_context():
        print(f"[before] coluna desconsiderado existe: {_col_existe()}")
        print(f"[before] FK numero_chassi->hora_moto: {_fk_existe()}")
        db.session.execute(text(SQL_COLUNA))
        db.session.execute(text(SQL_INDEX))
        db.session.execute(text(SQL_DROP_FK))
        db.session.commit()
        print(f"[after] coluna desconsiderado existe: {_col_existe()}")
        print(f"[after] FK numero_chassi->hora_moto: {_fk_existe()}")
        assert _col_existe() is True, "coluna nao criada"
        assert _fk_existe() is None, "FK nao removida"
        print("OK — migration hora_43 aplicada.")

if __name__ == '__main__':
    main()
```

- [ ] **Step 3: Rodar a migration no banco local**

Run: `source .venv/bin/activate && python scripts/migrations/hora_43_nf_item_desconsiderar.py`
Expected: imprime `[before] ... FK ...: hora_nf_entrada_item_numero_chassi_fkey` (ou similar), `[after] ... FK ...: None`, e `OK — migration hora_43 aplicada.`

- [ ] **Step 4: Commit**

```bash
git add scripts/migrations/hora_43_nf_item_desconsiderar.sql scripts/migrations/hora_43_nf_item_desconsiderar.py
git commit -m "feat(hora): migration hora_43 — desconsiderado em nf_item + relaxa FK chassi"
```

---

## Task 2: Modelo — campo, FK relaxada, property

**Files:**
- Modify: `app/hora/models/compra.py:117-212`
- Test: `tests/hora/test_desconsiderar_item_nf.py`

- [ ] **Step 1: Escrever o teste do modelo**

Create `tests/hora/test_desconsiderar_item_nf.py`:

```python
"""Testes da feature de desconsiderar item de NF de entrada."""
import pytest

from app import db
from app.hora.models import HoraMoto, HoraNfEntrada, HoraNfEntradaItem
from app.hora.services.moto_service import registrar_evento


def test_item_tem_flag_desconsiderado_default_false(db, nf_entrada_factory):
    nf = nf_entrada_factory(['9TESTMODEL000001'])
    item = nf.itens[0]
    assert item.desconsiderado is False


def test_itens_considerados_exclui_desconsiderado(db, nf_entrada_factory):
    nf = nf_entrada_factory(['9TESTMODEL000001', '9TESTMODEL000002'])
    nf.itens[0].desconsiderado = True
    db.session.flush()
    db.session.refresh(nf)
    assert len(nf.itens) == 2
    assert len(nf.itens_considerados) == 1
    assert nf.itens_considerados[0].numero_chassi == '9TESTMODEL000002'
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `source .venv/bin/activate && pytest tests/hora/test_desconsiderar_item_nf.py -v`
Expected: FAIL — `AttributeError: 'HoraNfEntradaItem' object has no attribute 'desconsiderado'` / sem `itens_considerados`.

- [ ] **Step 3: Adicionar o campo e a property no modelo**

In `app/hora/models/compra.py`, dentro de `HoraNfEntrada` (após o relationship `itens`, perto da linha 167), adicionar a property:

```python
    @property
    def itens_considerados(self):
        """Itens não-desconsiderados — base para recebimento/estoque."""
        return [i for i in self.itens if not i.desconsiderado]
```

Em `HoraNfEntradaItem` (linha ~191), trocar a coluna `numero_chassi` (remover a `ForeignKey`) e adicionar o campo `desconsiderado`:

```python
    numero_chassi = db.Column(
        db.String(30),
        # FK p/ hora_moto REMOVIDA na migration hora_43: item desconsiderado
        # mantém o chassi declarado na NF sem HoraMoto. Integridade item↔moto
        # garantida na aplicação (ver nf_entrada_service.assert_item_moto_consistente).
        nullable=False,
        index=True,
    )
    preco_real = db.Column(db.Numeric(15, 2), nullable=False)
    desconsiderado = db.Column(
        db.Boolean, nullable=False, default=False, server_default='false', index=True,
    )
```

- [ ] **Step 4: Ajustar o relationship `moto` para viewonly + primaryjoin**

In `app/hora/models/compra.py`, a linha `moto = db.relationship('HoraMoto', backref='nfs_entrada_itens')` (linha ~205) passa a:

```python
    moto = db.relationship(
        'HoraMoto',
        primaryjoin='foreign(HoraNfEntradaItem.numero_chassi) == HoraMoto.numero_chassi',
        viewonly=True,
        backref=db.backref('nfs_entrada_itens', viewonly=True),
    )
```

- [ ] **Step 5: Rodar e ver passar**

Run: `source .venv/bin/activate && pytest tests/hora/test_desconsiderar_item_nf.py -v`
Expected: PASS (2 testes).

- [ ] **Step 6: Smoke — garantir que `moto` relationship ainda resolve**

Run: `source .venv/bin/activate && pytest tests/hora/test_chassi_protecao.py tests/hora/test_recebimento_reprocessamento.py -v`
Expected: PASS (relationship viewonly não quebrou leituras existentes). Se algum teste escrevia via `moto.nfs_entrada_itens`, ajustar para escrever direto em `HoraNfEntradaItem` (viewonly não aceita append).

- [ ] **Step 7: Commit**

```bash
git add app/hora/models/compra.py tests/hora/test_desconsiderar_item_nf.py
git commit -m "feat(hora): nf_item desconsiderado + itens_considerados + moto viewonly"
```

---

## Task 3: Helpers de validação

**Files:**
- Modify: `app/hora/services/chassi_protecao_service.py`
- Modify: `app/hora/services/nf_entrada_service.py`
- Test: `tests/hora/test_desconsiderar_item_nf.py`

- [ ] **Step 1: Escrever os testes dos helpers**

Append em `tests/hora/test_desconsiderar_item_nf.py`:

```python
def test_chassi_em_pedido(db, pedido_compra_factory):
    from app.hora.services.chassi_protecao_service import chassi_em_pedido
    pedido_compra_factory(['9TESTPED00000001'])
    assert chassi_em_pedido('9TESTPED00000001') is True
    assert chassi_em_pedido('9NAOEXISTE000001') is False


def test_motivo_bloqueio_recebido(db, nf_entrada_factory):
    from app.hora.services.nf_entrada_service import _motivo_bloqueio_desconsiderar
    nf = nf_entrada_factory(['9TESTBLOQ0000001'])
    item = nf.itens[0]
    # sem pedido, sem recebimento -> sem bloqueio
    assert _motivo_bloqueio_desconsiderar(item) is None
    registrar_evento(numero_chassi='9TESTBLOQ0000001', tipo='RECEBIDA',
                     loja_id=nf.loja_destino_id)
    db.session.flush()
    assert _motivo_bloqueio_desconsiderar(item) is not None
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `source .venv/bin/activate && pytest tests/hora/test_desconsiderar_item_nf.py -k "em_pedido or bloqueio_recebido" -v`
Expected: FAIL — `ImportError`/`AttributeError` (funções não existem).

- [ ] **Step 3: Implementar `chassi_em_pedido`**

In `app/hora/services/chassi_protecao_service.py`, adicionar após `chassi_protegido`:

```python
def chassi_em_pedido(numero_chassi: str | None) -> bool:
    """True se o chassi consta em alguma linha de pedido de compra (HoraPedidoItem).

    Diferente de `chassi_protegido`: NÃO considera HoraNfEntradaItem (que daria
    sempre True ao validar o próprio item da NF).
    """
    chassi = (numero_chassi or '').strip().upper()
    if not chassi:
        return False
    return db.session.query(HoraPedidoItem.id).filter(
        HoraPedidoItem.numero_chassi == chassi,
    ).limit(1).first() is not None
```

- [ ] **Step 4: Implementar `_motivo_bloqueio_desconsiderar` e `assert_item_moto_consistente`**

In `app/hora/services/nf_entrada_service.py`, adicionar (perto do topo dos helpers; imports locais para evitar ciclo):

```python
def _motivo_bloqueio_desconsiderar(item) -> Optional[str]:
    """Retorna o motivo (str) que impede desconsiderar o item, ou None se liberado.

    Bloqueia se: chassi em pedido (HoraPedidoItem); NF já entrou em recebimento;
    chassi conferido; moto tem qualquer evento (recebida/vendida/avariada/...);
    chassi presente em outro item de NF considerado.
    """
    from app.hora.models import (
        HoraPedidoItem, HoraRecebimento, HoraRecebimentoConferencia,
    )
    from app.hora.services.chassi_protecao_service import chassi_em_pedido
    from app.hora.services.moto_service import status_atual

    chassi = (item.numero_chassi or '').strip().upper()

    if chassi_em_pedido(chassi):
        ped = (
            db.session.query(HoraPedidoItem)
            .filter(HoraPedidoItem.numero_chassi == chassi).first()
        )
        return (
            f'Moto {chassi} consta no pedido '
            f'{ped.pedido.numero_pedido if ped and ped.pedido else ped.pedido_id}; '
            f'desvincule do pedido antes de desconsiderar.'
        )

    if HoraRecebimento.query.filter_by(nf_id=item.nf_id).first():
        return (
            f'NF #{item.nf_id} já entrou em recebimento; '
            f'desconsidere o item antes de iniciar o recebimento.'
        )

    if HoraRecebimentoConferencia.query.filter_by(
        numero_chassi=chassi, substituida=False,
    ).first():
        return f'Moto {chassi} já foi conferida em um recebimento.'

    ev = status_atual(chassi)
    if ev:
        return f"Moto {chassi} tem evento '{ev}'; não pode ser desconsiderada."

    outro = (
        HoraNfEntradaItem.query
        .filter(
            HoraNfEntradaItem.numero_chassi == chassi,
            HoraNfEntradaItem.id != item.id,
            HoraNfEntradaItem.desconsiderado.is_(False),
        ).first()
    )
    if outro:
        return (
            f'Moto {chassi} também consta na NF #{outro.nf_id} (item considerado); '
            f'não é seguro remover o cadastro da moto.'
        )

    return None


def assert_item_moto_consistente(item) -> None:
    """Invariante (substitui a FK): item considerado ⇒ moto existe;
    item desconsiderado ⇒ moto não existe. Levanta AssertionError se violado.
    """
    from app.hora.models import HoraMoto
    existe = HoraMoto.query.get((item.numero_chassi or '').strip().upper()) is not None
    if item.desconsiderado and existe:
        raise AssertionError(f'item desconsiderado {item.id} ainda tem HoraMoto')
    if not item.desconsiderado and not existe:
        raise AssertionError(f'item considerado {item.id} sem HoraMoto')
```

> `Optional` já é importado em `nf_entrada_service.py`. Confirmar o import de `HoraNfEntradaItem` no topo do módulo (já presente).

- [ ] **Step 5: Rodar e ver passar**

Run: `source .venv/bin/activate && pytest tests/hora/test_desconsiderar_item_nf.py -k "em_pedido or bloqueio_recebido" -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/hora/services/chassi_protecao_service.py app/hora/services/nf_entrada_service.py tests/hora/test_desconsiderar_item_nf.py
git commit -m "feat(hora): helpers de validacao para desconsiderar item NF"
```

---

## Task 4: Serviço desconsiderar_item_nf

**Files:**
- Modify: `app/hora/services/nf_entrada_service.py`
- Test: `tests/hora/test_desconsiderar_item_nf.py`

- [ ] **Step 1: Escrever os testes do serviço**

Append em `tests/hora/test_desconsiderar_item_nf.py`:

```python
def test_desconsiderar_marca_e_remove_moto(db, nf_entrada_factory):
    from app.hora.services.nf_entrada_service import desconsiderar_item_nf
    nf = nf_entrada_factory(['9TESTDESC0000001'])
    item = nf.itens[0]
    assert HoraMoto.query.get('9TESTDESC0000001') is not None
    res = desconsiderar_item_nf(item.id, operador='tester')
    assert res['ok'] is True
    db.session.refresh(item)
    assert item.desconsiderado is True
    assert HoraMoto.query.get('9TESTDESC0000001') is None


def test_desconsiderar_bloqueia_se_em_pedido(db, nf_entrada_factory, pedido_compra_factory):
    from app.hora.services.nf_entrada_service import desconsiderar_item_nf
    chassi = '9TESTDESCPED0001'
    pedido_compra_factory([chassi])
    nf = nf_entrada_factory([chassi])
    item = nf.itens[0]
    with pytest.raises(ValueError, match='pedido'):
        desconsiderar_item_nf(item.id)
    db.session.rollback()
    assert HoraMoto.query.get(chassi) is not None  # moto preservada


def test_desconsiderar_bloqueia_se_recebido(db, nf_entrada_factory):
    from app.hora.services.nf_entrada_service import desconsiderar_item_nf
    chassi = '9TESTDESCREC0001'
    nf = nf_entrada_factory([chassi])
    item = nf.itens[0]
    registrar_evento(numero_chassi=chassi, tipo='RECEBIDA', loja_id=nf.loja_destino_id)
    db.session.flush()
    with pytest.raises(ValueError):
        desconsiderar_item_nf(item.id)


def test_desconsiderar_idempotente(db, nf_entrada_factory):
    from app.hora.services.nf_entrada_service import desconsiderar_item_nf
    nf = nf_entrada_factory(['9TESTDESCIDEM01'])
    item = nf.itens[0]
    desconsiderar_item_nf(item.id)
    res2 = desconsiderar_item_nf(item.id)
    assert res2['ok'] is True
    assert res2.get('ja_desconsiderado') is True
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `source .venv/bin/activate && pytest tests/hora/test_desconsiderar_item_nf.py -k desconsiderar -v`
Expected: FAIL — `ImportError` (`desconsiderar_item_nf` não existe).

- [ ] **Step 3: Implementar o serviço**

In `app/hora/services/nf_entrada_service.py`, adicionar:

```python
def desconsiderar_item_nf(nf_item_id: int, operador: Optional[str] = None) -> dict:
    """Marca um item de NF como desconsiderado e remove a HoraMoto.

    Pré-condições (senão ValueError): não em pedido, não recebido / NF sem
    recebimento, sem evento de moto, sem outro item de NF considerado.
    Reversível via `reconsiderar_item_nf`.
    """
    from app.hora.models import HoraMoto, HoraMotoEvento

    item = HoraNfEntradaItem.query.get(nf_item_id)
    if not item:
        raise ValueError(f'Item de NF {nf_item_id} não encontrado.')
    if item.desconsiderado:
        return {'ok': True, 'ja_desconsiderado': True, 'nf_item_id': nf_item_id,
                'numero_chassi': item.numero_chassi}

    motivo = _motivo_bloqueio_desconsiderar(item)
    if motivo:
        raise ValueError(motivo)

    chassi = (item.numero_chassi or '').strip().upper()
    item.desconsiderado = True

    moto = HoraMoto.query.get(chassi)
    if moto is not None:
        # Defensivo: nunca remover moto com eventos (já barrado por status_atual,
        # mas garante contra estados inesperados).
        if HoraMotoEvento.query.filter_by(numero_chassi=chassi).first():
            db.session.rollback()
            raise ValueError(f'Moto {chassi} tem eventos; não pode ser removida.')
        db.session.delete(moto)

    db.session.commit()
    current_app.logger.info(
        f'hora: item NF #{nf_item_id} (chassi {chassi}) desconsiderado por '
        f'{operador or "?"}; HoraMoto removida.'
    )
    return {'ok': True, 'nf_item_id': nf_item_id, 'numero_chassi': chassi}
```

- [ ] **Step 4: Rodar e ver passar**

Run: `source .venv/bin/activate && pytest tests/hora/test_desconsiderar_item_nf.py -k desconsiderar -v`
Expected: PASS (4 testes).

- [ ] **Step 5: Commit**

```bash
git add app/hora/services/nf_entrada_service.py tests/hora/test_desconsiderar_item_nf.py
git commit -m "feat(hora): servico desconsiderar_item_nf"
```

---

## Task 5: Serviço reconsiderar_item_nf

**Files:**
- Modify: `app/hora/services/nf_entrada_service.py`
- Test: `tests/hora/test_desconsiderar_item_nf.py`

- [ ] **Step 1: Escrever o teste**

Append em `tests/hora/test_desconsiderar_item_nf.py`:

```python
def test_reconsiderar_recria_moto(db, nf_entrada_factory):
    from app.hora.services.nf_entrada_service import (
        desconsiderar_item_nf, reconsiderar_item_nf, assert_item_moto_consistente,
    )
    chassi = '9TESTRECONS0001'
    nf = nf_entrada_factory([chassi])
    item = nf.itens[0]
    desconsiderar_item_nf(item.id)
    assert HoraMoto.query.get(chassi) is None
    res = reconsiderar_item_nf(item.id, operador='tester')
    assert res['ok'] is True
    db.session.refresh(item)
    assert item.desconsiderado is False
    assert HoraMoto.query.get(chassi) is not None
    assert_item_moto_consistente(item)  # invariante OK


def test_reconsiderar_item_nao_desconsiderado_erro(db, nf_entrada_factory):
    from app.hora.services.nf_entrada_service import reconsiderar_item_nf
    nf = nf_entrada_factory(['9TESTRECONS0002'])
    with pytest.raises(ValueError):
        reconsiderar_item_nf(nf.itens[0].id)
```

- [ ] **Step 2: Rodar e ver falhar**

Run: `source .venv/bin/activate && pytest tests/hora/test_desconsiderar_item_nf.py -k reconsiderar -v`
Expected: FAIL — `ImportError`.

- [ ] **Step 3: Implementar o serviço**

In `app/hora/services/nf_entrada_service.py`:

```python
def reconsiderar_item_nf(nf_item_id: int, operador: Optional[str] = None) -> dict:
    """Reverte a desconsideração: recria a HoraMoto e zera o flag."""
    from app.hora.models import PENDENTE_ORIGEM_NF_ENTRADA
    from app.hora.services.moto_service import get_or_create_moto

    item = HoraNfEntradaItem.query.get(nf_item_id)
    if not item:
        raise ValueError(f'Item de NF {nf_item_id} não encontrado.')
    if not item.desconsiderado:
        raise ValueError('Item não está desconsiderado.')

    get_or_create_moto(
        numero_chassi=item.numero_chassi,
        modelo_nome=item.modelo_texto_original,
        cor=item.cor_texto_original or 'NAO_INFORMADA',
        numero_motor=item.numero_motor_texto_original,
        criado_por=operador,
        origem_pendencia=PENDENTE_ORIGEM_NF_ENTRADA,
        origem_id=item.nf_id,
        fallback_sentinela=True,
    )
    item.desconsiderado = False
    db.session.commit()
    current_app.logger.info(
        f'hora: item NF #{nf_item_id} (chassi {item.numero_chassi}) reconsiderado '
        f'por {operador or "?"}; HoraMoto recriada.'
    )
    return {'ok': True, 'nf_item_id': nf_item_id, 'numero_chassi': item.numero_chassi}
```

- [ ] **Step 4: Rodar e ver passar**

Run: `source .venv/bin/activate && pytest tests/hora/test_desconsiderar_item_nf.py -k reconsiderar -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Commit**

```bash
git add app/hora/services/nf_entrada_service.py tests/hora/test_desconsiderar_item_nf.py
git commit -m "feat(hora): servico reconsiderar_item_nf (reverter)"
```

---

## Task 6: Aplicar itens_considerados no recebimento e matching

**Files:**
- Modify: `app/hora/services/recebimento_service.py` (linhas 151, 505, 920, 1004, 1036, 1148, 1157, 1246, 1276, 1322, 1340, 1346)
- Modify: `app/hora/services/matching_service.py:46-47`
- Test: `tests/hora/test_desconsiderar_item_nf.py`

- [ ] **Step 1: Escrever o teste de integração**

Append em `tests/hora/test_desconsiderar_item_nf.py`:

```python
def test_recebimento_automatico_ignora_desconsiderado(db, nf_entrada_factory):
    from app.hora.services.nf_entrada_service import desconsiderar_item_nf
    from app.hora.services import recebimento_service
    nf = nf_entrada_factory(['9TESTRECIG00001', '9TESTRECIG00002'])
    desconsiderar_item_nf(nf.itens[0].id)
    db.session.refresh(nf)
    res = recebimento_service.criar_recebimento_automatico_da_nf(nf.id, operador='tester')
    # apenas 1 moto considerada deve ser conferida
    assert res['qtd_nf'] == 1 if 'qtd_nf' in res else True
    rec = nf.recebimentos[0]
    chassis_conf = {c.numero_chassi for c in rec.conferencias if not c.substituida}
    assert '9TESTRECIG00001' not in chassis_conf
    assert '9TESTRECIG00002' in chassis_conf


def test_chassis_esperados_ignora_desconsiderado(db, nf_entrada_factory):
    from app.hora.services.nf_entrada_service import desconsiderar_item_nf
    from app.hora.services import recebimento_service
    nf = nf_entrada_factory(['9TESTESP000001', '9TESTESP000002'])
    desconsiderar_item_nf(nf.itens[0].id)
    db.session.refresh(nf)
    rec = recebimento_service.iniciar_recebimento(
        nf_id=nf.id, loja_id=nf.loja_destino_id, operador='tester')
    esperados = recebimento_service.chassis_esperados_mas_nao_conferidos(rec.id)
    assert '9TESTESP000001' not in esperados
    assert '9TESTESP000002' in esperados
```

> Se a assinatura de `iniciar_recebimento` exigir mais argumentos, ajustar conforme `recebimento_service.iniciar_recebimento` (ver código). O ponto verificado é a exclusão do desconsiderado.

- [ ] **Step 2: Rodar e ver falhar**

Run: `source .venv/bin/activate && pytest tests/hora/test_desconsiderar_item_nf.py -k "recebimento_automatico or chassis_esperados" -v`
Expected: FAIL — o item desconsiderado ainda é conferido/esperado.

- [ ] **Step 3: Trocar `nf.itens`/`rec.nf.itens` por `itens_considerados` nos pontos de "a receber"**

In `app/hora/services/recebimento_service.py`, aplicar a substituição **apenas** nestes pontos (lógica de recebimento; NÃO em pontos de exibição da NF):

| Linha (aprox.) | Antes | Depois |
|---|---|---|
| 151 | `for i in rec.nf.itens:` | `for i in rec.nf.itens_considerados:` |
| 505 | `chassis_nf = {i.numero_chassi for i in rec.nf.itens}` | `... for i in rec.nf.itens_considerados}` |
| 920 | `qtd_nf = sum(1 for _ in rec.nf.itens) if rec.nf else 0` | `qtd_nf = sum(1 for _ in rec.nf.itens_considerados) if rec.nf else 0` |
| 1004 | `chassis_nf = [i.numero_chassi for i in rec.nf.itens if i.numero_chassi]` | `... for i in rec.nf.itens_considerados if i.numero_chassi]` |
| 1036 | `nf_por_chassi = {i.numero_chassi: i for i in rec.nf.itens if i.numero_chassi}` | `... for i in rec.nf.itens_considerados if i.numero_chassi}` |
| 1148 | `chassis_nf = {i.numero_chassi for i in rec.nf.itens}` | `... for i in rec.nf.itens_considerados}` |
| 1157 | `chassis_nf = {i.numero_chassi for i in rec.nf.itens}` | `... for i in rec.nf.itens_considerados}` |
| 1246 | `for it in nf.itens:` (em `listar_nfs_para_recebimento_automatico`) | `for it in nf.itens_considerados:` |
| 1276 | `'qtd_motos_nf': len(nf.itens),` | `'qtd_motos_nf': len(nf.itens_considerados),` |
| 1322 | `if not nf.itens:` (em `criar_recebimento_automatico_da_nf`) | `if not nf.itens_considerados:` |
| 1340 | `qtd_nf = len(nf.itens)` | `qtd_nf = len(nf.itens_considerados)` |
| 1346 | `for ordem, item in enumerate(nf.itens, start=1):` | `for ordem, item in enumerate(nf.itens_considerados, start=1):` |

> Cada linha é única no arquivo — usar Edit com o contexto da linha. Reconferir o número via `grep -n "rec.nf.itens\|nf.itens" app/hora/services/recebimento_service.py` antes de editar (linhas podem deslocar entre tasks).

- [ ] **Step 4: `_chassis_nf` no matching exclui desconsiderados**

In `app/hora/services/matching_service.py:46-47`:

```python
def _chassis_nf(nf: HoraNfEntrada) -> set:
    return {i.numero_chassi for i in nf.itens_considerados if i.numero_chassi}
```

- [ ] **Step 5: Rodar os testes da feature + regressão de recebimento**

Run: `source .venv/bin/activate && pytest tests/hora/test_desconsiderar_item_nf.py tests/hora/test_recebimento_reprocessamento.py tests/hora/test_estoque_eventos_em_estoque.py -v`
Expected: PASS (toda a suíte da feature + regressões).

- [ ] **Step 6: Commit**

```bash
git add app/hora/services/recebimento_service.py app/hora/services/matching_service.py tests/hora/test_desconsiderar_item_nf.py
git commit -m "feat(hora): recebimento/matching ignoram itens desconsiderados"
```

---

## Task 7: Rotas em nfs.py

**Files:**
- Modify: `app/hora/routes/nfs.py` (após `nfs_editar_item`, linha ~500)
- Test: `tests/hora/test_desconsiderar_item_nf.py`

- [ ] **Step 1: Escrever teste de rota (smoke via test client)**

Append em `tests/hora/test_desconsiderar_item_nf.py`:

```python
def test_rota_desconsiderar_e_reverter(db, client_admin, nf_entrada_factory):
    """client_admin: fixture de client autenticado como admin (ver tests/conftest)."""
    nf = nf_entrada_factory(['9TESTROTA000001'])
    item = nf.itens[0]
    r = client_admin.post(
        f'/hora/nfs/{nf.id}/itens/{item.id}/desconsiderar',
        headers={'Accept': 'application/json'},
    )
    assert r.status_code == 200
    assert r.get_json()['ok'] is True
    assert HoraMoto.query.get('9TESTROTA000001') is None
    r2 = client_admin.post(
        f'/hora/nfs/{nf.id}/itens/{item.id}/reverter',
        headers={'Accept': 'application/json'},
    )
    assert r2.status_code == 200
    assert HoraMoto.query.get('9TESTROTA000001') is not None
```

> Se não existir fixture `client_admin` em `tests/conftest.py`, marcar o teste com `@pytest.mark.skipif` e validar as rotas manualmente em dev (ver Step 4). Não inventar fixture de auth.

- [ ] **Step 2: Rodar e ver falhar**

Run: `source .venv/bin/activate && pytest tests/hora/test_desconsiderar_item_nf.py -k rota -v`
Expected: FAIL — 404 (rotas não existem).

- [ ] **Step 3: Implementar as rotas**

In `app/hora/routes/nfs.py`, após `nfs_editar_item` (linha ~500), seguindo o mesmo padrão de validação de loja:

```python
@hora_bp.route('/nfs/<int:nf_id>/itens/<int:item_id>/desconsiderar', methods=['POST'])
@require_hora_perm('nfs', 'editar')
def nfs_desconsiderar_item(nf_id: int, item_id: int):
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    is_ajax = request.is_json or request.headers.get('Accept') == 'application/json'
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        if is_ajax:
            return jsonify({'ok': False, 'erro': 'acesso negado'}), 403
        flash('Acesso negado: NF de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.nfs_lista'))
    try:
        res = nf_entrada_service.desconsiderar_item_nf(
            item_id, operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        if is_ajax:
            return jsonify(res)
        flash(f"Moto {res['numero_chassi']} desconsiderada.", 'success')
    except ValueError as exc:
        if is_ajax:
            return jsonify({'ok': False, 'erro': str(exc)}), 400
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))


@hora_bp.route('/nfs/<int:nf_id>/itens/<int:item_id>/reverter', methods=['POST'])
@require_hora_perm('nfs', 'editar')
def nfs_reverter_item(nf_id: int, item_id: int):
    nf = HoraNfEntrada.query.get_or_404(nf_id)
    is_ajax = request.is_json or request.headers.get('Accept') == 'application/json'
    if nf.loja_destino_id and not usuario_tem_acesso_a_loja(nf.loja_destino_id):
        if is_ajax:
            return jsonify({'ok': False, 'erro': 'acesso negado'}), 403
        flash('Acesso negado: NF de loja fora do seu escopo.', 'danger')
        return redirect(url_for('hora.nfs_lista'))
    try:
        res = nf_entrada_service.reconsiderar_item_nf(
            item_id, operador=current_user.nome if hasattr(current_user, 'nome') else None,
        )
        if is_ajax:
            return jsonify(res)
        flash(f"Moto {res['numero_chassi']} reconsiderada.", 'success')
    except ValueError as exc:
        if is_ajax:
            return jsonify({'ok': False, 'erro': str(exc)}), 400
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.nfs_detalhe', nf_id=nf.id))
```

> `current_user`, `request`, `jsonify`, `flash`, `redirect`, `url_for`, `usuario_tem_acesso_a_loja`, `nf_entrada_service` já estão importados em `nfs.py` (usados por `nfs_editar_item`). Confirmar.

- [ ] **Step 4: Rodar e ver passar (ou validar manual se sem fixture de auth)**

Run: `source .venv/bin/activate && pytest tests/hora/test_desconsiderar_item_nf.py -k rota -v`
Expected: PASS (ou SKIP se `client_admin` não existir; nesse caso, validar em dev: `python run.py`, abrir uma NF e usar os botões).

- [ ] **Step 5: Commit**

```bash
git add app/hora/routes/nfs.py tests/hora/test_desconsiderar_item_nf.py
git commit -m "feat(hora): rotas desconsiderar/reverter item de NF"
```

---

## Task 8: UI no detalhe da NF

**Files:**
- Modify: `app/templates/hora/nf_detalhe.html:366-442` (tabela de itens)

- [ ] **Step 1: Passar flag de elegibilidade do backend (sem query extra)**

Em `app/hora/routes/nfs.py`, na `nfs_detalhe` (linha ~193, no `render_template`), adicionar a variável `nf_tem_recebimento`:

```python
    return render_template(
        'hora/nf_detalhe.html',
        nf=nf,
        nf_tem_recebimento=bool(nf.recebimentos),
        pedidos_disponiveis=pedidos_disponiveis,
        ...
```

> `nf.recebimentos` já é carregado em `recebimentos_da_nf` (linha ~188). Reusar.

- [ ] **Step 2: Linha de item — badge "Desconsiderada" + atenuação**

In `app/templates/hora/nf_detalhe.html`, na linha do item (linha ~368), tornar a `<tr>` atenuada e adicionar badge na coluna Chassi:

```jinja
        <tr class="border-top border-2 {% if item.desconsiderado %}table-secondary text-muted{% endif %}">
          <td class="chassi-mono">
            <i class="fas fa-motorcycle text-secondary"></i> {{ item.numero_chassi }}
            {% if item.desconsiderado %}
              <span class="badge bg-secondary ms-1" title="Moto desconsiderada (fora do estoque/recebimento)">
                <i class="fas fa-ban"></i> desconsiderada
              </span>
            {% endif %}
          </td>
```

- [ ] **Step 3: Coluna Ações — botões Desconsiderar / Reverter**

In `app/templates/hora/nf_detalhe.html`, dentro de `{% if pode_editar_nf %}<td class="text-end">...` (linha ~390), adicionar após o botão de editar:

```jinja
            {% if item.desconsiderado %}
            <form method="post" class="d-inline"
                  action="{{ url_for('hora.nfs_reverter_item', nf_id=nf.id, item_id=item.id) }}">
              <button type="submit" class="btn btn-sm btn-outline-success"
                      title="Reverter: recria a moto e volta ao estoque/recebimento">
                <i class="fas fa-rotate-left"></i> Reverter
              </button>
            </form>
            {% elif not v and not nf_tem_recebimento %}
            <form method="post" class="d-inline"
                  action="{{ url_for('hora.nfs_desconsiderar_item', nf_id=nf.id, item_id=item.id) }}"
                  onsubmit="return confirm('Desconsiderar esta moto? Ela sai do estoque/recebimento e o cadastro da moto é removido.');">
              <button type="submit" class="btn btn-sm btn-outline-secondary"
                      title="Desconsiderar: moto de outra empresa, não entra no estoque">
                <i class="fas fa-ban"></i> Desconsiderar
              </button>
            </form>
            {% elif not item.desconsiderado %}
            <span class="text-muted small"
                  title="{% if v %}Em pedido — desvincule antes{% elif nf_tem_recebimento %}NF já em recebimento{% endif %}">
              <i class="fas fa-lock"></i>
            </span>
            {% endif %}
```

> `v` é o vínculo do item (`vinculos_por_chassi.get(item.numero_chassi)`), já calculado na linha 367. `v` truthy ⇒ chassi consta em pedido ⇒ botão Desconsiderar oculto (backend revalida).

- [ ] **Step 4: Validar visualmente em dev**

Run: `source .venv/bin/activate && python run.py` → abrir `/hora/nfs/<id>` de uma NF sem recebimento com item "sem pedido" → ver botão Desconsiderar; clicar → badge "desconsiderada" + botão Reverter. Conferir que item em pedido mostra cadeado.

- [ ] **Step 5: Commit**

```bash
git add app/templates/hora/nf_detalhe.html app/hora/routes/nfs.py
git commit -m "feat(hora): UI desconsiderar/reverter item no detalhe da NF"
```

---

## Task 9: Atualizar app/hora/CLAUDE.md

**Files:**
- Modify: `app/hora/CLAUDE.md`

- [ ] **Step 1: Adicionar seção documentando a feature**

In `app/hora/CLAUDE.md`, adicionar uma seção numerada nova (após a última, "16. ...") documentando:
- Campo `HoraNfEntradaItem.desconsiderado` + FK `numero_chassi` relaxada (integridade por validação aplicativa `assert_item_moto_consistente`).
- Regra: desconsiderar = item de outra empresa; remove `HoraMoto`; reversível.
- Gates: não em pedido (`chassi_em_pedido`), NF sem recebimento, sem evento de moto, sem outro item de NF considerado.
- `HoraNfEntrada.itens_considerados` é a base para recebimento/matching.
- Migration `hora_43`.

Manter o estilo das demais seções (curto, factual, com caminhos).

- [ ] **Step 2: Rodar a suíte completa do módulo**

Run: `source .venv/bin/activate && pytest tests/hora/ -v`
Expected: PASS (toda a suíte HORA verde, incluindo a nova).

- [ ] **Step 3: Commit**

```bash
git add app/hora/CLAUDE.md
git commit -m "docs(hora): documenta desconsideracao de item de NF"
```

---

## Self-review

**Spec coverage:**
- D1 (não entra no estoque) → Task 4 (remove moto) + Task 6 (fora do recebimento → sem evento RECEBIDA).
- D2 (por item) → Task 2 (flag no item) + Task 8 (ação por item).
- D3 ("com pedido" = HoraPedidoItem) → Task 3 (`chassi_em_pedido`).
- D4 (remover HoraMoto) → Task 4.
- D5 (flag reversível) → Task 2 (flag) + Task 5 (reverter).
- D6 (ordem: não em pedido/recebido) → Task 3/4 (`_motivo_bloqueio_desconsiderar`).
- Validação aplicativa no lugar da FK → Task 3 (`assert_item_moto_consistente`) + Task 2 (FK relaxada).
- Efeito nos demais locais → Task 6 (recebimento + matching). Estoque: sem ação (deriva de evento) — coberto pelo teste `test_recebimento_automatico_ignora_desconsiderado`.
- UI/rotas → Task 7 + Task 8. Migration → Task 1. Testes → Tasks 2-7. Não-objetivos: respeitados (sem pedido/loja por item; sem financeiro).

**Placeholder scan:** nenhum "TBD/TODO"; todo step tem código/comando. As anotações `>` marcam verificações obrigatórias (linha pode deslocar; fixture de auth pode não existir), não placeholders de conteúdo.

**Type consistency:** `desconsiderar_item_nf`/`reconsiderar_item_nf` retornam `dict` com `ok`/`numero_chassi`/`nf_item_id` (consumido nas rotas e testes). `itens_considerados` usado consistentemente. `_motivo_bloqueio_desconsiderar(item)` → `Optional[str]`. `chassi_em_pedido(chassi)` → `bool`.
