<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-30
-->
# Motos Assaí — Estoque de Peças + Pendência (Spec 2: UI) Implementation Plan

> **Papel:** plano de implementação task-by-task (TDD) do Spec 2 (UI) do módulo Motos Assaí — deriva da spec homônima; executado via subagent-driven-development. Ponteiro de estado durante a execução das 16 tasks.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expor pela UI o back-end do Spec 1 (Estoque de Peças + Pendência categorizada): resolução por ficha com ramos de tratativa, detalhe read-only, catálogo/estoque/compra de peça, gancho de pós-venda, timeline unificada do chassi; reescrever a rota de resolução e aposentar o shim; dobrar os follow-ups técnicos do Spec 1.

**Architecture:** Orquestrador fino — a lógica de "resolver com tratativa" mora num service novo (`resolucao_service`) que compõe os átomos do Spec 1 (`movimento_service.consumir`/`canibalizar` + `pendencia_service.resolver_pendencia`); as rotas só fazem HTTP + `db.session.commit()`. Serviços fazem add+flush SEM commit (padrão do Spec 1); o caller HTTP commita.

**Tech Stack:** Python 3.12 · Flask 3.1 · Flask-SQLAlchemy 3.1 (SA 2.0) · Flask-WTF (FlaskForm) · Jinja2 · Bootstrap 5 · pytest (Postgres local, isolamento por SAVEPOINT).

## Global Constraints

- **Prefixo de tabela** `assai_`; **decorator** `@login_required` + `@require_motos_assai` em TODA rota (sem exceção; ordem: login_required primeiro).
- **Campos de tabela**: só os schemas em `.claude/skills/consultando-sql/schemas/tables/assai_*.json` — nunca inventar.
- **Timezone**: datas via `from app.utils.timezone import agora_brasil_naive` (Brasil naive).
- **JSONB**: sempre via `from app.utils.json_helpers import sanitize_for_json`.
- **Services**: add+flush SEM commit; a rota commita (padrão do módulo — "zero `db.session` na rota; lógica no service").
- **Sem CHECK no banco** nas tabelas do Spec 1 (validação por set Python no service).
- **Blueprint**: rotas novas registradas por import no fim de `app/motos_assai/routes/__init__.py` (`# noqa: E402,F401`); forms exportados em `forms/__init__.py`; services em `services/__init__.py`.
- **Constantes de domínio** (import de `app.motos_assai.models`): `PENDENCIA_CATEGORIA_*`/`PENDENCIA_CATEGORIAS_VALIDAS`, `PENDENCIA_ORIGEM_*`/`PENDENCIA_ORIGENS_VALIDAS`/`ORIGENS_FISICAS`, `PENDENCIA_TRATATIVA_*`/`PENDENCIA_TRATATIVAS_VALIDAS`, `PENDENCIA_FASE_*`, `MOVIMENTO_*`, `COMPRA_PECA_TIPO_*`/`COMPRA_PECA_STATUS_*`.
- **Sem push** sem aval do dono. Commits locais na `main` (padrão da sessão).
- Spec de referência: `docs/superpowers/specs/2026-06-30-motos-assai-estoque-pendencia-spec2-ui-design.md`.

## Indice

- [File Structure](#file-structure)
- [FASE 0 — Guards + polish](#fase-0-guards-polish-base-dos-services-do-spec-1)
  - [Task 1: Guards em movimento_service](#task-1-guards-em-movimento_serviceconsumircanibalizar)
  - [Task 2: Polish SA2.0](#task-2-polish-sa20-querygetdbsessionget-relations-lazy)
- [FASE 1 — Serviços de pendência](#fase-1-serviços-de-pendência)
  - [Task 3: resolucao_service.resolver_com_tratativa](#task-3-resolucao_serviceresolver_com_tratativa)
  - [Task 4: pendencia_service.reclassificar](#task-4-pendencia_servicereclassificar)
  - [Task 5: pendencia_service.detalhe_pendencia](#task-5-pendencia_servicedetalhe_pendencia)
  - [Task 6: Leituras enriquecidas + filtros](#task-6-leituras-enriquecidas-filtros-novos)
- [FASE 2 — Telas de pendência](#fase-2-telas-de-pendência)
  - [Task 7: Página de resolução](#task-7-página-de-resolução-pendenciaspidresolver)
  - [Task 8: Detalhe read-only](#task-8-detalhe-read-only-pendenciaspid)
  - [Task 9: Refactor listas + remover shim](#task-9-refactor-listas-reclassificar-avulso-remover-shimrotajs)
- [FASE 3 — Peças](#fase-3-peças-catálogoestoquecompra)
  - [Task 10: Catálogo de Peça](#task-10-catálogo-de-peça-crud-nn-modelos)
  - [Task 11: Estoque de Peça](#task-11-estoque-de-peça-ledger-entradaajustedescarte)
  - [Task 12: Pedido de Compra de Peça](#task-12-pedido-de-compra-de-peça)
- [FASE 4 — Pós-venda + Timeline + Menu](#fase-4-pós-venda-timeline-menu)
  - [Task 13: Pós-venda](#task-13-pós-venda-gerar-pendência-acompanhar)
  - [Task 14: Timeline no rastreamento](#task-14-timeline-unificada-no-rastreamento-de-chassi)
  - [Task 15: Menu](#task-15-menu-3-itens-novos)
- [FASE 5 — Fechamento](#fase-5-fechamento)
  - [Task 16: Hint schema + doc](#task-16-hint-do-schema-doc-do-módulo)
- [Deploy](#deploy-após-aval-do-dono-não-neste-plano)
- [Self-Review](#self-review-executada-na-escrita)

---

## File Structure

**Novos:**
- `app/motos_assai/services/resolucao_service.py` — orquestrador `resolver_com_tratativa`.
- `app/motos_assai/routes/{peca,estoque_peca,compra_peca}.py` — CRUDs de peça/estoque/compra.
- `app/motos_assai/forms/peca_forms.py` — `PecaForm` (+ CSRF forms de estoque/compra).
- `app/templates/motos_assai/pecas/{lista,form,detalhe}.html`
- `app/templates/motos_assai/estoque_pecas/{lista,detalhe}.html`
- `app/templates/motos_assai/compras_pecas/{lista,nova,detalhe}.html`
- `app/templates/motos_assai/pendencias/{resolver,detalhe}.html`
- `app/static/motos_assai/js/pendencia_resolver.js`
- Testes: `tests/motos_assai/test_resolucao_service.py`, `test_pendencia_reclassificar.py`, `test_pendencia_detalhe.py`, `test_movimento_guards.py`, `test_pendencia_rotas.py`, `test_pecas_rotas.py`, `test_estoque_peca_rotas.py`, `test_compra_peca_rotas.py`, `test_pos_venda_pendencia.py`, `test_rastreamento_timeline_pendencia.py`.

**Modificados:**
- `app/motos_assai/services/movimento_service.py` — guards (Task 1); `.query.get`→`db.session.get` (Task 2).
- `app/motos_assai/services/pendencia_service.py` — `reclassificar`, `detalhe_pendencia`, leituras enriquecidas + filtros; `.query.get`→`db.session.get` (Tasks 2,4,5,6).
- `app/motos_assai/services/{peca,compra_peca}_service.py` — `.query.get`→`db.session.get` (Task 2).
- `app/motos_assai/models/pendencia.py` — 3 relations Usuario `lazy='joined'`→`select` (Task 2).
- `app/motos_assai/services/montagem_service.py` — remove `resolver_pendencia` (Task 9).
- `app/motos_assai/services/pos_venda_service.py` — `gerar_pendencia_de_ocorrencia`, `pendencias_da_ocorrencia`, `contar_pendencias_abertas_por_chassi` (Task 13).
- `app/motos_assai/services/rastreamento_chassi_service.py` — `fichas_pendencia` + `movimentos_peca` (Task 14).
- `app/motos_assai/routes/{pendencias,pos_venda}.py`; `app/motos_assai/routes/__init__.py`; `services/__init__.py`; `forms/__init__.py`.
- `app/templates/motos_assai/pendencias/{abertas,historico}.html`; `pos_venda/{lista,_macros}.html`; `resumo/_modal_rastreamento.html`; `base_motos_assai.html`.
- Remove `app/static/motos_assai/js/pendencias_resolver.js` (Task 9).
- Testes do shim: `tests/motos_assai/{test_integracao_ganchos,test_montagem_service,test_montagem_service_carregada}.py` (Task 9).
- `.claude/skills/consultando-sql/schemas/tables/assai_pendencia.json`; `app/motos_assai/CLAUDE.md` (Task 16).

---

## FASE 0 — Guards + polish (base dos services do Spec 1)

### Task 1: Guards em `movimento_service.consumir`/`canibalizar`

**Files:**
- Modify: `app/motos_assai/services/movimento_service.py`
- Test: `tests/motos_assai/test_movimento_guards.py` (create)

**Interfaces:**
- Consumes: `movimento_service.{consumir,canibalizar,_exigir_peca,registrar_entrada,saldo}` (Spec 1); `pendencia_service.abrir_pendencia`; models `AssaiPeca`, `AssaiPendencia`, `AssaiMoto`, `PENDENCIA_CATEGORIA_FALTA_PECA`, `PENDENCIA_ORIGEM_GALPAO`.
- Produces: `consumir`/`canibalizar` que rejeitam `peca_id` inexistente (`EstoqueError`), doador inexistente e cascata A→B→A.

- [ ] **Step 1: Write the failing tests**

```python
# tests/motos_assai/test_movimento_guards.py
import uuid
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiPendencia,
    PENDENCIA_CATEGORIA_FALTA_PECA, PENDENCIA_ORIGEM_GALPAO,
)
from app.motos_assai.services.peca_service import criar_peca
from app.motos_assai.services.pendencia_service import abrir_pendencia
from app.motos_assai.services.movimento_service import consumir, canibalizar, EstoqueError


def _peca(admin_user):
    return criar_peca(nome=f'PZ_{uuid.uuid4().hex[:8].upper()}', operador_id=admin_user.id)


def _moto(chassi, admin_user):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
    db.session.flush()


def _ficha(chassi, admin_user, categoria=PENDENCIA_CATEGORIA_FALTA_PECA):
    return abrir_pendencia(
        chassi=chassi, categoria=categoria, origem=PENDENCIA_ORIGEM_GALPAO,
        descricao='defeito', operador_id=admin_user.id,
    )


def test_consumir_peca_inexistente_erro_claro(app, admin_user):
    with app.app_context():
        chassi = f'TSTG{uuid.uuid4().hex[:6].upper()}'
        _moto(chassi, admin_user)
        f = _ficha(chassi, admin_user)
        with pytest.raises(EstoqueError, match='peca'):
            consumir(peca_id=999999999, quantidade=1, pendencia_id=f.id,
                     chassi_destino=chassi, operador_id=admin_user.id)
        db.session.rollback()


def test_canibalizar_peca_inexistente_erro_claro(app, admin_user):
    with app.app_context():
        recep = f'TSTR{uuid.uuid4().hex[:6].upper()}'
        doad = f'TSTD{uuid.uuid4().hex[:6].upper()}'
        _moto(recep, admin_user); _moto(doad, admin_user)
        f = _ficha(recep, admin_user)
        with pytest.raises(EstoqueError, match='peca'):
            canibalizar(peca_id=999999999, quantidade=1, chassi_origem=doad,
                        chassi_destino=recep, pendencia_id=f.id, operador_id=admin_user.id)
        db.session.rollback()


def test_canibalizar_doador_inexistente_erro(app, admin_user):
    with app.app_context():
        recep = f'TSTR{uuid.uuid4().hex[:6].upper()}'
        _moto(recep, admin_user)
        p = _peca(admin_user); f = _ficha(recep, admin_user)
        with pytest.raises(EstoqueError, match='[Dd]oador'):
            canibalizar(peca_id=p.id, quantidade=1, chassi_origem='NAOEXISTE999',
                        chassi_destino=recep, pendencia_id=f.id, operador_id=admin_user.id)
        db.session.rollback()


def test_canibalizar_anti_cascata_doador_ja_em_falta_da_peca(app, admin_user):
    with app.app_context():
        recep = f'TSTR{uuid.uuid4().hex[:6].upper()}'
        doad = f'TSTD{uuid.uuid4().hex[:6].upper()}'
        _moto(recep, admin_user); _moto(doad, admin_user)
        p = _peca(admin_user); f = _ficha(recep, admin_user)
        # doador ja tem FALTA_PECA aberta DA MESMA peca
        abrir_pendencia(chassi=doad, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
                        origem=PENDENCIA_ORIGEM_GALPAO, descricao='ja falta',
                        peca_id=p.id, operador_id=admin_user.id)
        with pytest.raises(EstoqueError, match='[Cc]ascata|[Ff]alta'):
            canibalizar(peca_id=p.id, quantidade=1, chassi_origem=doad,
                        chassi_destino=recep, pendencia_id=f.id, operador_id=admin_user.id)
        db.session.rollback()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/motos_assai/test_movimento_guards.py -v`
Expected: FAIL (hoje `consumir`/`canibalizar` não validam peça/doador/cascata — `test_consumir_peca_inexistente` levanta `IntegrityError`, não `EstoqueError`).

- [ ] **Step 3: Add guards to `movimento_service`**

Em `consumir` (após validar `qtd` e antes de buscar a ficha), adicionar `_exigir_peca(peca_id)`. Em `canibalizar` (após validar origem≠destino/qtd, antes de criar a linha), adicionar os 3 guards + `sanitize_for_json` no `dados_extras`:

```python
# --- topo de consumir(...), logo após validar qtd ---
    _exigir_peca(peca_id)

# --- topo de canibalizar(...), logo após validar origem/destino/qtd ---
    _exigir_peca(peca_id)
    from app.motos_assai.models import AssaiMoto, PENDENCIA_CATEGORIA_FALTA_PECA
    if not AssaiMoto.query.filter_by(chassi=origem).first():
        raise EstoqueError(f'Doador {origem} nao encontrado em assai_moto.')
    # anti-cascata A->B->A: doador ja tem FALTA_PECA aberta DESTA peca
    ja_falta = (
        AssaiPendencia.query.filter(
            AssaiPendencia.chassi == origem,
            AssaiPendencia.peca_id == peca_id,
            AssaiPendencia.categoria == PENDENCIA_CATEGORIA_FALTA_PECA,
            AssaiPendencia.resolvida_em.is_(None),
            AssaiPendencia.cancelada_em.is_(None),
        ).first()
    )
    if ja_falta is not None:
        raise EstoqueError(
            f'Cascata bloqueada: doador {origem} ja tem FALTA_PECA aberta desta peca.'
        )
```

Adicionar os imports no topo do módulo: `from app.motos_assai.models import ..., AssaiPendencia`. Trocar `dados_extras={'custo_estimado': True}` por `dados_extras=sanitize_for_json({'custo_estimado': True})` na linha do `AssaiEstoqueMovimento` de canibalização, e `dados_extras={}` por `dados_extras=sanitize_for_json({})` em `consumir`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/motos_assai/test_movimento_guards.py -v`
Expected: PASS (4 testes).

- [ ] **Step 5: Regression**

Run: `pytest tests/motos_assai/test_movimento_service.py tests/motos_assai/test_compra_peca_service.py -q`
Expected: PASS (guards não quebram os caminhos felizes).

- [ ] **Step 6: Commit**

```bash
git add app/motos_assai/services/movimento_service.py tests/motos_assai/test_movimento_guards.py
git commit -m "feat(motos_assai): guards de canibalizacao/consumo (Spec 2 follow-up)"
```

---

### Task 2: Polish SA2.0 (`.query.get`→`db.session.get`) + relations lazy

**Files:**
- Modify: `app/motos_assai/services/{pendencia,movimento,compra_peca,peca}_service.py`
- Modify: `app/motos_assai/models/pendencia.py`

**Interfaces:**
- Consumes: nada novo.
- Produces: mesmos comportamentos; sem `LegacyAPIWarning` de `Query.get`.

- [ ] **Step 1: Substituir `.query.get(x)` por `db.session.get(Model, x)`**

Nos 4 services, trocar cada `Model.query.get(<id>)` por `db.session.get(Model, <id>)`. Ocorrências conhecidas: `pendencia_service` (`AssaiPendencia.query.get` em `resolver_pendencia`/`cancelar_pendencia`/`solicitar_compra`), `movimento_service` (`AssaiPeca.query.get`, `AssaiPendencia.query.get`), `compra_peca_service` (`AssaiPecaCompra.query.get`, `AssaiPeca.query.get`, `AssaiPecaCompraItem.query.get`), `peca_service` (`AssaiPeca.query.get`, `AssaiModelo.query.get`). Confirmar com: `grep -rn "\.query\.get(" app/motos_assai/services/`.

- [ ] **Step 2: `pendencia.py` — relations Usuario `lazy='joined'`→`select`**

Em `app/motos_assai/models/pendencia.py`, nas 3 relations `aberta_por`/`resolvida_por`/`cancelada_por`, trocar `lazy='joined'` por `lazy='select'` (as leituras já usam `joinedload` explícito onde precisam).

- [ ] **Step 3: Run the full module suite**

Run: `pytest tests/motos_assai/ -q`
Expected: PASS (373 + os 4 da Task 1 = 377; nenhum a menos).

- [ ] **Step 4: Commit**

```bash
git add app/motos_assai/services/ app/motos_assai/models/pendencia.py
git commit -m "refactor(motos_assai): SA2.0 session.get + relations lazy=select (Spec 2 follow-up)"
```

---

## FASE 1 — Serviços de pendência

### Task 3: `resolucao_service.resolver_com_tratativa`

**Files:**
- Create: `app/motos_assai/services/resolucao_service.py`
- Modify: `app/motos_assai/services/__init__.py` (export)
- Test: `tests/motos_assai/test_resolucao_service.py`

**Interfaces:**
- Consumes: `pendencia_service.resolver_pendencia(pendencia_id, tratativa, resolucao_descricao, operador_id)`; `movimento_service.{consumir,canibalizar,saldo}`; models `AssaiPendencia`, `PENDENCIA_TRATATIVA_*`, `PENDENCIA_CATEGORIA_VENDA`.
- Produces: `resolver_com_tratativa(*, pendencia_id, tratativa, resolucao_descricao, operador_id, peca_id=None, quantidade=None, chassi_doador=None, receita_unitaria=None) -> dict` (chaves: `ok`, `pendencia_id`, `tratativa`, `saldo_apos` (ou None), `montou`). Exceção `ResolucaoError`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/motos_assai/test_resolucao_service.py
import uuid
from decimal import Decimal
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo,
    PENDENCIA_TRATATIVA_CONSERTAR, PENDENCIA_TRATATIVA_USAR_ESTOQUE,
    PENDENCIA_TRATATIVA_USAR_OUTRA_MOTO,
    PENDENCIA_CATEGORIA_AVARIA, PENDENCIA_CATEGORIA_FALTA_PECA,
    PENDENCIA_ORIGEM_GALPAO, EVENTO_MONTADA,
)
from app.motos_assai.services.peca_service import criar_peca
from app.motos_assai.services.movimento_service import registrar_entrada, saldo
from app.motos_assai.services.pendencia_service import abrir_pendencia
from app.motos_assai.services.moto_evento_service import status_efetivo
from app.motos_assai.services.resolucao_service import resolver_com_tratativa, ResolucaoError


def _moto(chassi, admin_user):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
    db.session.flush()


def _uid(p): return f'{p}{uuid.uuid4().hex[:6].upper()}'


def test_consertar_sem_movimento_monta(app, admin_user):
    with app.app_context():
        chassi = _uid('TSTA')
        _moto(chassi, admin_user)
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_AVARIA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='fio solto',
                            operador_id=admin_user.id)
        r = resolver_com_tratativa(pendencia_id=f.id, tratativa=PENDENCIA_TRATATIVA_CONSERTAR,
                                   resolucao_descricao='soldado', operador_id=admin_user.id)
        db.session.flush()
        assert r['ok'] and r['montou'] is True
        assert status_efetivo(chassi) == EVENTO_MONTADA
        db.session.rollback()


def test_usar_estoque_consome_e_monta(app, admin_user):
    with app.app_context():
        chassi = _uid('TSTB')
        _moto(chassi, admin_user)
        p = criar_peca(nome=_uid('PZ'), operador_id=admin_user.id)
        registrar_entrada(peca_id=p.id, quantidade=5, custo_unitario='10.00', operador_id=admin_user.id)
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='falta peca',
                            operador_id=admin_user.id)
        r = resolver_com_tratativa(pendencia_id=f.id, tratativa=PENDENCIA_TRATATIVA_USAR_ESTOQUE,
                                   resolucao_descricao='aplicada', operador_id=admin_user.id,
                                   peca_id=p.id, quantidade=1)
        db.session.flush()
        assert r['saldo_apos'] == Decimal('4.000')
        assert saldo(p.id) == Decimal('4.000')
        assert status_efetivo(chassi) == EVENTO_MONTADA
        db.session.rollback()


def test_usar_outra_moto_canibaliza_e_abre_falta_no_doador(app, admin_user):
    with app.app_context():
        recep = _uid('TSTR'); doad = _uid('TSTD')
        _moto(recep, admin_user); _moto(doad, admin_user)
        p = criar_peca(nome=_uid('PZ'), operador_id=admin_user.id)
        f = abrir_pendencia(chassi=recep, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='falta',
                            operador_id=admin_user.id)
        r = resolver_com_tratativa(pendencia_id=f.id, tratativa=PENDENCIA_TRATATIVA_USAR_OUTRA_MOTO,
                                   resolucao_descricao='canibalizada', operador_id=admin_user.id,
                                   peca_id=p.id, quantidade=1, chassi_doador=doad)
        db.session.flush()
        assert r['ok']
        from app.motos_assai.models import AssaiPendencia
        assert AssaiPendencia.query.filter_by(chassi=doad, peca_id=p.id).count() == 1
        db.session.rollback()


def test_usar_estoque_exige_peca_e_quantidade(app, admin_user):
    with app.app_context():
        chassi = _uid('TSTC')
        _moto(chassi, admin_user)
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='falta',
                            operador_id=admin_user.id)
        with pytest.raises(ResolucaoError):
            resolver_com_tratativa(pendencia_id=f.id, tratativa=PENDENCIA_TRATATIVA_USAR_ESTOQUE,
                                   resolucao_descricao='x', operador_id=admin_user.id)
        db.session.rollback()


def test_saldo_insuficiente_nao_bloqueia_avisa(app, admin_user):
    with app.app_context():
        chassi = _uid('TSTE')
        _moto(chassi, admin_user)
        p = criar_peca(nome=_uid('PZ'), operador_id=admin_user.id)  # saldo 0
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='falta',
                            operador_id=admin_user.id)
        r = resolver_com_tratativa(pendencia_id=f.id, tratativa=PENDENCIA_TRATATIVA_USAR_ESTOQUE,
                                   resolucao_descricao='aplicada', operador_id=admin_user.id,
                                   peca_id=p.id, quantidade=1)
        db.session.flush()
        assert r['saldo_apos'] == Decimal('-1.000')  # negativo, sem travar
        db.session.rollback()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/motos_assai/test_resolucao_service.py -v`
Expected: FAIL (`ModuleNotFoundError: resolucao_service`).

- [ ] **Step 3: Implement `resolucao_service`**

```python
# app/motos_assai/services/resolucao_service.py
"""resolucao_service — orquestra a resolucao de pendencia com tratativa (Spec 2 §4.1).

Compoe os atomos do Spec 1: movimento (consumir/canibalizar) + resolver_pendencia.
add+flush SEM commit (a rota commita). NAO adiciona corrida — o gate fisico e o
advisory lock ja vivem em pendencia_service.resolver_pendencia.
"""
from app import db
from app.motos_assai.models import (
    AssaiPendencia,
    PENDENCIA_TRATATIVA_USAR_ESTOQUE, PENDENCIA_TRATATIVA_USAR_OUTRA_MOTO,
    PENDENCIA_TRATATIVAS_VALIDAS, PENDENCIA_CATEGORIA_VENDA, EVENTO_MONTADA,
)
from app.motos_assai.services import movimento_service, pendencia_service
from app.motos_assai.services.moto_evento_service import status_efetivo

_MOVIMENTA = {PENDENCIA_TRATATIVA_USAR_ESTOQUE, PENDENCIA_TRATATIVA_USAR_OUTRA_MOTO}


class ResolucaoError(Exception):
    """Erro de dominio da orquestracao de resolucao."""


def resolver_com_tratativa(
    *, pendencia_id, tratativa, resolucao_descricao, operador_id,
    peca_id=None, quantidade=None, chassi_doador=None, receita_unitaria=None,
) -> dict:
    if tratativa not in PENDENCIA_TRATATIVAS_VALIDAS:
        raise ResolucaoError(
            f'Tratativa invalida: {tratativa}. Validas: {sorted(PENDENCIA_TRATATIVAS_VALIDAS)}')
    ficha = db.session.get(AssaiPendencia, pendencia_id)
    if ficha is None:
        raise ResolucaoError(f'Pendencia {pendencia_id} nao encontrada.')

    saldo_apos = None
    if tratativa in _MOVIMENTA:
        if not peca_id or quantidade is None:
            raise ResolucaoError('Tratativa exige peca_id e quantidade.')
        rec = receita_unitaria if ficha.categoria == PENDENCIA_CATEGORIA_VENDA else None
        if tratativa == PENDENCIA_TRATATIVA_USAR_ESTOQUE:
            movimento_service.consumir(
                peca_id=peca_id, quantidade=quantidade, pendencia_id=pendencia_id,
                chassi_destino=ficha.chassi, operador_id=operador_id, receita_unitaria=rec)
        else:  # USAR_OUTRA_MOTO
            if not chassi_doador:
                raise ResolucaoError('USAR_OUTRA_MOTO exige chassi_doador.')
            movimento_service.canibalizar(
                peca_id=peca_id, quantidade=quantidade, chassi_origem=chassi_doador,
                chassi_destino=ficha.chassi, pendencia_id=pendencia_id,
                operador_id=operador_id, receita_unitaria=rec)
        saldo_apos = movimento_service.saldo(peca_id)

    pendencia_service.resolver_pendencia(
        pendencia_id=pendencia_id, tratativa=tratativa,
        resolucao_descricao=resolucao_descricao, operador_id=operador_id)
    db.session.flush()

    return {
        'ok': True,
        'pendencia_id': pendencia_id,
        'tratativa': tratativa,
        'saldo_apos': saldo_apos,
        'montou': status_efetivo(ficha.chassi) == EVENTO_MONTADA,
    }
```

Adicionar em `services/__init__.py`: `from .resolucao_service import resolver_com_tratativa, ResolucaoError` + entradas em `__all__`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/motos_assai/test_resolucao_service.py -v`
Expected: PASS (5 testes).

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/resolucao_service.py app/motos_assai/services/__init__.py tests/motos_assai/test_resolucao_service.py
git commit -m "feat(motos_assai): resolucao_service orquestra resolver+tratativa (Spec 2)"
```

---

### Task 4: `pendencia_service.reclassificar`

**Files:**
- Modify: `app/motos_assai/services/pendencia_service.py`
- Test: `tests/motos_assai/test_pendencia_reclassificar.py`

**Interfaces:**
- Consumes: `afeta_estado_moto(ficha)`; models + constantes de categoria/origem.
- Produces: `reclassificar(*, pendencia_id, categoria, origem, operador_id) -> AssaiPendencia`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/motos_assai/test_pendencia_reclassificar.py
import uuid
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo,
    PENDENCIA_CATEGORIA_INDETERMINADA, PENDENCIA_CATEGORIA_AVARIA,
    PENDENCIA_ORIGEM_GALPAO, PENDENCIA_ORIGEM_POS_VENDA_LOJA,
)
from app.motos_assai.services.pendencia_service import (
    abrir_pendencia, reclassificar, PendenciaError,
)


def _moto(chassi, admin_user):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
    db.session.flush()


def _uid(): return f'TSTX{uuid.uuid4().hex[:6].upper()}'


def test_reclassificar_categoria(app, admin_user):
    with app.app_context():
        chassi = _uid(); _moto(chassi, admin_user)
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_INDETERMINADA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='defeito',
                            operador_id=admin_user.id)
        reclassificar(pendencia_id=f.id, categoria=PENDENCIA_CATEGORIA_AVARIA,
                      origem=PENDENCIA_ORIGEM_GALPAO, operador_id=admin_user.id)
        db.session.refresh(f)
        assert f.categoria == PENDENCIA_CATEGORIA_AVARIA
        assert f.detalhes.get('reclassificacao') is not None
        db.session.rollback()


def test_reclassificar_nao_pode_destravar_moto_via_origem(app, admin_user):
    with app.app_context():
        chassi = _uid(); _moto(chassi, admin_user)
        # ficha fisica (GALPAO) => emitiu PENDENTE (evento_pendente_id set)
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_INDETERMINADA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='defeito',
                            operador_id=admin_user.id)
        assert f.evento_pendente_id is not None
        with pytest.raises(PendenciaError, match='fisica|trava|nao-fisica'):
            reclassificar(pendencia_id=f.id, categoria=PENDENCIA_CATEGORIA_AVARIA,
                          origem=PENDENCIA_ORIGEM_POS_VENDA_LOJA, operador_id=admin_user.id)
        db.session.rollback()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/motos_assai/test_pendencia_reclassificar.py -v`
Expected: FAIL (`ImportError: reclassificar`).

- [ ] **Step 3: Implement `reclassificar` em `pendencia_service.py`**

Adicionar após `abrir_pendencia`:

```python
def reclassificar(*, pendencia_id, categoria, origem, operador_id):
    """Reclassifica categoria/origem de uma ficha (S2 — INDETERMINADA -> real).

    Guard S6: se a ficha ja trava a moto (evento_pendente_id) e a nova origem a
    tornaria nao-fisica, levanta — nao da para destravar via troca de origem.
    add+flush, SEM commit.
    """
    ficha = db.session.get(AssaiPendencia, pendencia_id)
    if ficha is None:
        raise PendenciaError(f'Pendencia {pendencia_id} nao encontrada.')
    if categoria not in PENDENCIA_CATEGORIAS_VALIDAS:
        raise PendenciaError(f'Categoria invalida: {categoria}.')
    if origem not in PENDENCIA_ORIGENS_VALIDAS:
        raise PendenciaError(f'Origem invalida: {origem}.')

    de = {'categoria': ficha.categoria, 'origem': ficha.origem}
    ficha.categoria = categoria
    ficha.origem = origem
    # guard S6: nao tornar nao-fisica uma ficha que ja trava a moto
    if ficha.evento_pendente_id is not None and not afeta_estado_moto(ficha):
        raise PendenciaError(
            'Nao e possivel tornar nao-fisica uma pendencia que ja trava a moto '
            '(evento PENDENTE ja emitido).')

    det = dict(ficha.detalhes or {})
    det['reclassificacao'] = {
        'de': de, 'para': {'categoria': categoria, 'origem': origem},
        'por_id': operador_id, 'em': agora_brasil_naive().isoformat(),
    }
    ficha.detalhes = sanitize_for_json(det)
    db.session.flush()
    return ficha
```

`PENDENCIA_CATEGORIAS_VALIDAS`/`PENDENCIA_ORIGENS_VALIDAS` já estão no import de topo.

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/motos_assai/test_pendencia_reclassificar.py -v`
Expected: PASS (2 testes). Nota: a mutação `ficha.categoria/origem` antes do guard só sai no flush; o guard levanta antes do flush e o teste faz rollback, então não persiste.

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/pendencia_service.py tests/motos_assai/test_pendencia_reclassificar.py
git commit -m "feat(motos_assai): pendencia_service.reclassificar + guard S6 (Spec 2)"
```

---

### Task 5: `pendencia_service.detalhe_pendencia`

**Files:**
- Modify: `app/motos_assai/services/pendencia_service.py`
- Test: `tests/motos_assai/test_pendencia_detalhe.py`

**Interfaces:**
- Consumes: models `AssaiPendencia`, `AssaiEstoqueMovimento`, `AssaiPecaCompraItem`, `AssaiPecaCompra`, `AssaiMoto`.
- Produces: `detalhe_pendencia(pendencia_id) -> dict` (chaves: `ficha`, `moto`, `movimentos`, `custo_total`, `compras`, `filhas`, `pai`). Retorna `None` se a ficha não existe.

- [ ] **Step 1: Write the failing test**

```python
# tests/motos_assai/test_pendencia_detalhe.py
import uuid
from decimal import Decimal
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo,
    PENDENCIA_CATEGORIA_FALTA_PECA, PENDENCIA_ORIGEM_GALPAO,
    PENDENCIA_TRATATIVA_USAR_ESTOQUE,
)
from app.motos_assai.services.peca_service import criar_peca
from app.motos_assai.services.movimento_service import registrar_entrada
from app.motos_assai.services.pendencia_service import abrir_pendencia, detalhe_pendencia
from app.motos_assai.services.resolucao_service import resolver_com_tratativa


def _moto(chassi, admin_user):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
    db.session.flush()


def test_detalhe_traz_ficha_movimentos_e_custo(app, admin_user):
    with app.app_context():
        chassi = f'TSTDET{uuid.uuid4().hex[:6].upper()}'
        _moto(chassi, admin_user)
        p = criar_peca(nome=f'PZ{uuid.uuid4().hex[:6].upper()}', operador_id=admin_user.id)
        registrar_entrada(peca_id=p.id, quantidade=3, custo_unitario='10.00', operador_id=admin_user.id)
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_FALTA_PECA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='falta',
                            operador_id=admin_user.id)
        resolver_com_tratativa(pendencia_id=f.id, tratativa=PENDENCIA_TRATATIVA_USAR_ESTOQUE,
                               resolucao_descricao='ok', operador_id=admin_user.id,
                               peca_id=p.id, quantidade=1)
        db.session.flush()
        d = detalhe_pendencia(f.id)
        assert d is not None
        assert d['ficha']['categoria'] == PENDENCIA_CATEGORIA_FALTA_PECA
        assert len(d['movimentos']) == 1
        assert d['movimentos'][0]['tipo'] == 'CONSUMO'
        assert d['custo_total'] == Decimal('10.00')
        assert detalhe_pendencia(999999999) is None
        db.session.rollback()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/motos_assai/test_pendencia_detalhe.py -v`
Expected: FAIL (`ImportError: detalhe_pendencia`).

- [ ] **Step 3: Implement `detalhe_pendencia`**

```python
def detalhe_pendencia(pendencia_id):
    """Visao 360 read-only de uma ficha (Spec 2 §4.4). Retorna dict ou None."""
    from decimal import Decimal
    from app.motos_assai.models import (
        AssaiEstoqueMovimento, AssaiPecaCompraItem, AssaiPecaCompra,
    )
    ficha = db.session.get(AssaiPendencia, pendencia_id)
    if ficha is None:
        return None
    moto = AssaiMoto.query.options(joinedload(AssaiMoto.modelo)).filter_by(chassi=ficha.chassi).first()

    movs = (AssaiEstoqueMovimento.query
            .options(joinedload(AssaiEstoqueMovimento.peca))
            .filter(AssaiEstoqueMovimento.pendencia_id == pendencia_id)
            .order_by(AssaiEstoqueMovimento.id.desc()).all())
    custo_total = sum((m.custo_total or Decimal('0')) for m in movs) or Decimal('0')

    itens = (AssaiPecaCompraItem.query
             .filter(AssaiPecaCompraItem.pendencia_id == pendencia_id).all())
    compra_ids = {it.compra_id for it in itens}
    compras = (AssaiPecaCompra.query.filter(AssaiPecaCompra.id.in_(compra_ids)).all()
               if compra_ids else [])

    return {
        'ficha': {
            'id': ficha.id, 'chassi': ficha.chassi, 'categoria': ficha.categoria,
            'origem': ficha.origem, 'fase': ficha.fase, 'tratativa': ficha.tratativa,
            'descricao': ficha.descricao, 'resolucao_descricao': ficha.resolucao_descricao,
            'esta_aberta': ficha.esta_aberta, 'chassi_doador': ficha.chassi_doador,
            'aberta_em': ficha.aberta_em, 'aberta_por': ficha.aberta_por.nome if ficha.aberta_por else '-',
            'resolvida_em': ficha.resolvida_em,
            'resolvida_por': ficha.resolvida_por.nome if ficha.resolvida_por else None,
            'cancelada_em': ficha.cancelada_em,
            'devolucao_item_id': ficha.devolucao_item_id,
            'pos_venda_ocorrencia_id': ficha.pos_venda_ocorrencia_id,
            'divergencia_origem_id': ficha.divergencia_origem_id,
            'detalhes': ficha.detalhes or {},
        },
        'moto': {
            'modelo_codigo': moto.modelo.codigo if moto and moto.modelo else '-',
            'modelo_nome': moto.modelo.nome if moto and moto.modelo else '-',
            'cor': (moto.cor if moto else None) or '-',
        } if moto else None,
        'movimentos': [{
            'tipo': m.tipo, 'peca_nome': m.peca.nome if m.peca else '-',
            'quantidade': m.quantidade, 'custo_unitario': m.custo_unitario,
            'custo_total': m.custo_total, 'receita_total': m.receita_total,
            'chassi_origem': m.chassi_origem, 'chassi_destino': m.chassi_destino,
            'ocorrido_em': m.ocorrido_em,
        } for m in movs],
        'custo_total': custo_total,
        'compras': [{
            'id': c.id, 'numero': c.numero, 'tipo': c.tipo, 'status': c.status,
        } for c in compras],
        'filhas': [{'id': fi.id, 'categoria': fi.categoria, 'esta_aberta': fi.esta_aberta}
                   for fi in ficha.filhas],
        'pai': ({'id': ficha.pai.id} if ficha.pai else None),
    }
```

Imports no topo do módulo (`joinedload` já presente; `Decimal` importado localmente na função).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/motos_assai/test_pendencia_detalhe.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/pendencia_service.py tests/motos_assai/test_pendencia_detalhe.py
git commit -m "feat(motos_assai): detalhe_pendencia (visao 360 read-only) (Spec 2)"
```

---

### Task 6: Leituras enriquecidas + filtros novos

**Files:**
- Modify: `app/motos_assai/services/pendencia_service.py` (`FiltrosPendencias`, `listar_abertas`, `listar_historico_resolvidas`)
- Modify: `tests/motos_assai/test_pendencia_reads.py`

**Interfaces:**
- Produces: dicts de `listar_abertas`/`listar_historico_resolvidas` com as chaves `pendencia_id`, `categoria`, `origem`, `tratativa`, `fase`; `FiltrosPendencias` com `categoria`/`origem`/`tratativa`.

- [ ] **Step 1: Add asserts to the reads test (failing)**

Em `tests/motos_assai/test_pendencia_reads.py`, no teste que cria uma ficha aberta, adicionar após obter a linha do `listar_abertas`:

```python
        linha = abertas[0]
        assert 'pendencia_id' in linha and linha['pendencia_id']
        assert linha['categoria'] and linha['origem']
        assert 'fase' in linha and 'tratativa' in linha
```

E um teste novo de filtro por categoria:

```python
def test_listar_abertas_filtra_categoria(app, admin_user):
    from app.motos_assai.services.pendencia_service import listar_abertas
    from app.motos_assai.models import PENDENCIA_CATEGORIA_AVARIA
    with app.app_context():
        r = listar_abertas(filtros={'categoria': PENDENCIA_CATEGORIA_AVARIA})
        assert all(x['categoria'] == PENDENCIA_CATEGORIA_AVARIA for x in r)
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/motos_assai/test_pendencia_reads.py -v`
Expected: FAIL (`KeyError: 'pendencia_id'` / filtro não aplicado).

- [ ] **Step 3: Enrich the reads**

Em `FiltrosPendencias` (TypedDict) adicionar `categoria: Optional[str]`, `origem: Optional[str]`, `tratativa: Optional[str]`.

Em `listar_abertas` e `listar_historico_resolvidas`, no bloco de filtros, adicionar (após os existentes):

```python
        categoria = filtros.get('categoria')
        if categoria:
            q = q.filter(AssaiPendencia.categoria == categoria)
        origem = filtros.get('origem')
        if origem:
            q = q.filter(AssaiPendencia.origem == origem)
        tratativa = filtros.get('tratativa')
        if tratativa:
            q = q.filter(AssaiPendencia.tratativa == tratativa)
```

No dict de retorno de `listar_abertas`, adicionar (mantendo `evento_id` por retrocompat):

```python
            'pendencia_id': f.id,
            'categoria': f.categoria,
            'origem': f.origem,
            'tratativa': f.tratativa,
            'fase': f.fase,
```

Idem em `listar_historico_resolvidas` (inclui `tratativa`). Manter as chaves já existentes.

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/motos_assai/test_pendencia_reads.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/motos_assai/services/pendencia_service.py tests/motos_assai/test_pendencia_reads.py
git commit -m "feat(motos_assai): leituras de pendencia expoem categoria/origem/tratativa/fase + filtros (Spec 2)"
```

---

## FASE 2 — Telas de pendência

> **Padrão de rota** (todas as rotas abaixo): `@login_required` + `@require_motos_assai`; GET renderiza template estendendo `motos_assai/base_motos_assai.html` (bloco `motos_assai_content`); POST chama service + `db.session.commit()` + `flash(...)` + `redirect(...)`; erro de domínio → `flash(str(e), 'danger')`. Smoke tests usam a fixture `login_admin` (ver `tests/motos_assai/conftest.py`).

### Task 7: Página de resolução `/pendencias/<pid>/resolver`

**Files:**
- Modify: `app/motos_assai/routes/pendencias.py`
- Create: `app/templates/motos_assai/pendencias/resolver.html`
- Create: `app/static/motos_assai/js/pendencia_resolver.js`
- Test: `tests/motos_assai/test_pendencia_rotas.py`

**Interfaces:**
- Consumes: `resolucao_service.resolver_com_tratativa`; `pendencia_service.{reclassificar,solicitar_compra,detalhe_pendencia}`; `peca_service.listar_compativeis`; `movimento_service.saldo`.
- Produces: endpoint `motos_assai.pendencia_resolver_tela` (GET/POST `/pendencias/<int:pid>/resolver`).

- [ ] **Step 1: Write the failing smoke test**

```python
# tests/motos_assai/test_pendencia_rotas.py
import uuid
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, PENDENCIA_CATEGORIA_AVARIA, PENDENCIA_ORIGEM_GALPAO,
    EVENTO_MONTADA,
)
from app.motos_assai.services.pendencia_service import abrir_pendencia
from app.motos_assai.services.moto_evento_service import status_efetivo


def _moto(chassi):
    modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
    db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
    db.session.commit()


def test_get_resolver_200(login_admin, app, admin_user):
    with app.app_context():
        chassi = f'TSTRT{uuid.uuid4().hex[:6].upper()}'
        _moto(chassi)
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_AVARIA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='fio solto',
                            operador_id=admin_user.id)
        db.session.commit(); pid = f.id
    resp = login_admin.get(f'/motos-assai/pendencias/{pid}/resolver')
    assert resp.status_code == 200


def test_post_resolver_consertar_monta(login_admin, app, admin_user):
    with app.app_context():
        chassi = f'TSTRT{uuid.uuid4().hex[:6].upper()}'
        _moto(chassi)
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_AVARIA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='fio',
                            operador_id=admin_user.id)
        db.session.commit(); pid = f.id; ch = chassi
    resp = login_admin.post(f'/motos-assai/pendencias/{pid}/resolver', data={
        'acao': 'resolver', 'tratativa': 'CONSERTAR', 'resolucao_descricao': 'soldado'})
    assert resp.status_code in (302, 200)
    with app.app_context():
        assert status_efetivo(ch) == EVENTO_MONTADA
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/motos_assai/test_pendencia_rotas.py -v`
Expected: FAIL (404 — rota inexistente).

- [ ] **Step 3: Add the route**

Em `routes/pendencias.py`, adicionar imports (`current_user`, `flash`, `redirect`, `url_for` — conferir topo) e a rota:

```python
@motos_assai_bp.route('/pendencias/<int:pid>/resolver', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def pendencia_resolver_tela(pid):
    from app.motos_assai.services import pendencia_service, peca_service, movimento_service
    from app.motos_assai.services.resolucao_service import resolver_com_tratativa, ResolucaoError
    from app.motos_assai.services.pendencia_service import PendenciaError
    from app.motos_assai.models import AssaiMoto

    detalhe = pendencia_service.detalhe_pendencia(pid)
    if detalhe is None:
        flash('Pendência não encontrada.', 'danger')
        return redirect(url_for('motos_assai.pendencias_abertas'))

    if request.method == 'POST':
        acao = request.form.get('acao')
        try:
            if acao == 'reclassificar':
                pendencia_service.reclassificar(
                    pendencia_id=pid, categoria=request.form.get('categoria'),
                    origem=request.form.get('origem'), operador_id=current_user.id)
                db.session.commit(); flash('Pendência reclassificada.', 'success')
            elif acao == 'solicitar-compra':
                itens = [{'peca_id': request.form.get('peca_id', type=int),
                          'quantidade': request.form.get('quantidade', type=float)}]
                pendencia_service.solicitar_compra(
                    pendencia_id=pid, tipo=request.form.get('tipo'), itens=itens,
                    operador_id=current_user.id)
                db.session.commit(); flash('Compra/garantia solicitada.', 'success')
            elif acao == 'resolver':
                if detalhe['ficha']['categoria'] == 'INDETERMINADA':
                    pendencia_service.reclassificar(
                        pendencia_id=pid, categoria=request.form.get('categoria'),
                        origem=request.form.get('origem'), operador_id=current_user.id)
                resolver_com_tratativa(
                    pendencia_id=pid, tratativa=request.form.get('tratativa'),
                    resolucao_descricao=request.form.get('resolucao_descricao', ''),
                    operador_id=current_user.id,
                    peca_id=request.form.get('peca_id', type=int),
                    quantidade=request.form.get('quantidade', type=float),
                    chassi_doador=(request.form.get('chassi_doador') or '').strip().upper() or None)
                db.session.commit(); flash('Pendência resolvida.', 'success')
                return redirect(url_for('motos_assai.pendencias_abertas'))
        except (ResolucaoError, PendenciaError) as e:
            db.session.rollback(); flash(str(e), 'danger')
        return redirect(url_for('motos_assai.pendencia_resolver_tela', pid=pid))

    moto = AssaiMoto.query.filter_by(chassi=detalhe['ficha']['chassi']).first()
    pecas = []
    if moto:
        for p in peca_service.listar_compativeis(moto.modelo_id):
            pecas.append({'id': p.id, 'nome': p.nome, 'saldo': movimento_service.saldo(p.id)})
    return render_template('motos_assai/pendencias/resolver.html', d=detalhe, pecas=pecas)
```

- [ ] **Step 4: Create `resolver.html`** — estende `motos_assai/base_motos_assai.html`, bloco `motos_assai_content` (molde `modelos/form.html`; mobile-friendly): cabeçalho (`d.ficha.categoria` badge, origem, fase, chassi + `d.moto.modelo_codigo`/`cor`, `d.ficha.descricao`); se `d.ficha.categoria == 'INDETERMINADA'`, bloco de reclassificação (selects categoria de `{AVARIA,FALTA_PECA,REVISAO,VENDA}` + origem) cujos campos entram no form de resolver; form `POST` (`hidden acao=resolver` + radios tratativa CONSERTAR/REVISAR/USAR_ESTOQUE/USAR_OUTRA_MOTO + `<select name="peca_id" data-...>` com options `nome (saldo N)` e `data-saldo` + `<input name="quantidade">` + `<input name="chassi_doador">` + `<textarea name="resolucao_descricao">`); form "Pedir compra/garantia" (`acao=solicitar-compra` + select tipo GARANTIA/COMPRA + peça/qtd). CSRF `{{ csrf_token() }}` em cada form. Incluir `<script src="{{ url_for('static', filename='motos_assai/js/pendencia_resolver.js') }}" defer></script>`.

- [ ] **Step 5: Create `pendencia_resolver.js`** — ao mudar o radio `tratativa`, mostra/esconde campos: USAR_ESTOQUE→peça+qtd; USAR_OUTRA_MOTO→peça+qtd+doador; CONSERTAR/REVISAR→esconde. Ao escolher peça+qtd, se `qtd > data-saldo`, exibe `#aviso-saldo` (não bloqueia). Form posta normalmente (sem fetch).

- [ ] **Step 6: Run smoke tests**

Run: `pytest tests/motos_assai/test_pendencia_rotas.py -v`
Expected: PASS (o GET 200 exercita a renderização Jinja).

- [ ] **Step 7: Commit**

```bash
git add app/motos_assai/routes/pendencias.py app/templates/motos_assai/pendencias/resolver.html app/static/motos_assai/js/pendencia_resolver.js tests/motos_assai/test_pendencia_rotas.py
git commit -m "feat(motos_assai): pagina de resolucao por ficha /pendencias/<id>/resolver (Spec 2)"
```

---

### Task 8: Detalhe read-only `/pendencias/<pid>`

**Files:**
- Modify: `app/motos_assai/routes/pendencias.py`
- Create: `app/templates/motos_assai/pendencias/detalhe.html`
- Test: `tests/motos_assai/test_pendencia_rotas.py` (adicionar)

**Interfaces:**
- Consumes: `pendencia_service.detalhe_pendencia`.
- Produces: endpoint `motos_assai.pendencia_detalhe` (GET `/pendencias/<int:pid>`).

- [ ] **Step 1: Add failing smoke test**

```python
def test_get_detalhe_200(login_admin, app, admin_user):
    import uuid
    from app.motos_assai.services.pendencia_service import abrir_pendencia
    from app.motos_assai.models import PENDENCIA_CATEGORIA_AVARIA, PENDENCIA_ORIGEM_GALPAO
    with app.app_context():
        chassi = f'TSTDT{uuid.uuid4().hex[:6].upper()}'
        _moto(chassi)
        f = abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_AVARIA,
                            origem=PENDENCIA_ORIGEM_GALPAO, descricao='x',
                            operador_id=admin_user.id)
        db.session.commit(); pid = f.id
    resp = login_admin.get(f'/motos-assai/pendencias/{pid}')
    assert resp.status_code == 200
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/motos_assai/test_pendencia_rotas.py::test_get_detalhe_200 -v`
Expected: FAIL (404).

- [ ] **Step 3: Add the route** (`<int:pid>` desambigua de `/abertas`,`/historico`,`/criar`):

```python
@motos_assai_bp.route('/pendencias/<int:pid>')
@login_required
@require_motos_assai
def pendencia_detalhe(pid):
    from app.motos_assai.services import pendencia_service
    d = pendencia_service.detalhe_pendencia(pid)
    if d is None:
        flash('Pendência não encontrada.', 'danger')
        return redirect(url_for('motos_assai.pendencias_abertas'))
    return render_template('motos_assai/pendencias/detalhe.html', d=d)
```

- [ ] **Step 4: Create `detalhe.html`** — read-only (§4.4 da spec): cabeçalho (badge categoria/origem/fase/status, chassi+modelo+cor, descrição, datas/operadores, tratativa+resolucao_descricao); origem vinculada (links condicionais a `devolucao_item_id`/`pos_venda_ocorrencia_id`/`divergencia_origem_id`); tabela de `d.movimentos` + `d.custo_total`; tabela de `d.compras`; `d.filhas`/`d.pai`. Se `d.ficha.esta_aberta`, botão "Resolver" → `url_for('motos_assai.pendencia_resolver_tela', pid=d.ficha.id)`.

- [ ] **Step 5: Run to verify it passes**

Run: `pytest tests/motos_assai/test_pendencia_rotas.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/motos_assai/routes/pendencias.py app/templates/motos_assai/pendencias/detalhe.html tests/motos_assai/test_pendencia_rotas.py
git commit -m "feat(motos_assai): detalhe read-only da pendencia /pendencias/<id> (Spec 2)"
```

---

### Task 9: Refactor listas + reclassificar avulso + remover shim/rota/JS

**Files:**
- Modify: `app/motos_assai/routes/pendencias.py`
- Modify: `app/templates/motos_assai/pendencias/{abertas,historico}.html`
- Delete: `app/static/motos_assai/js/pendencias_resolver.js`
- Modify: `app/motos_assai/services/montagem_service.py`; `app/motos_assai/services/__init__.py`
- Modify: `tests/motos_assai/{test_integracao_ganchos,test_montagem_service,test_montagem_service_carregada}.py`

**Interfaces:**
- Consumes: `pendencia_service.reclassificar`; leituras enriquecidas (Task 6).
- Produces: endpoint `motos_assai.pendencia_reclassificar` (POST `/pendencias/<int:pid>/reclassificar`); remove `motos_assai.pendencias_resolver` e `montagem_service.resolver_pendencia`.

- [ ] **Step 1: Remove shim references from tests**

- `tests/motos_assai/test_integracao_ganchos.py`: remover `test_shim_resolver_resolve_unica_ficha` e `test_shim_resolver_multiplas_fichas_erro`; do import (linha 12) remover `resolver_pendencia` (manter `registrar_montagem, MontagemValidationError`). **Preservar** `test_montagem_pendente_abre_ficha`.
- `tests/motos_assai/test_montagem_service.py`: remover `test_resolver_pendencia`; do import (linha 9) remover `resolver_pendencia`.
- `tests/motos_assai/test_montagem_service_carregada.py`: remover `test_resolver_pendencia_chassi_carregada_levanta_mensagem_especifica` e `test_resolver_pendencia_chassi_faturada_orienta_cancelar_nf`; do import (linha 18) remover `resolver_pendencia`. Preservar os testes de `registrar_montagem`.

- [ ] **Step 2: Remove the shim + export**

- `montagem_service.py`: remover a função `resolver_pendencia` (≈ linhas 130-191). Rodar `grep -n "_msg_a6_por_status_montagem\|EVENTO_PENDENCIA_RESOLVIDA\|EVENTO_MONTADA" app/motos_assai/services/montagem_service.py` — remover do import só o que ficar sem uso (NÃO remover `_msg_a6_por_status_montagem` se `registrar_montagem` o usa; conferir).
- `services/__init__.py`: remover `resolver_pendencia` do import (linha 51) e de `__all__` (linha 137).

- [ ] **Step 3: Add `pendencia_reclassificar` + remove `pendencias_resolver`**

Em `routes/pendencias.py`: **remover** `pendencias_resolver` (rota `POST /pendencias/resolver`) e retirar `resolver_pendencia` do import do topo (manter `enviar_para_pendencia, MontagemValidationError`). Adicionar:

```python
@motos_assai_bp.route('/pendencias/<int:pid>/reclassificar', methods=['POST'])
@login_required
@require_motos_assai
def pendencia_reclassificar(pid):
    from app.motos_assai.services import pendencia_service
    from app.motos_assai.services.pendencia_service import PendenciaError
    try:
        pendencia_service.reclassificar(
            pendencia_id=pid, categoria=request.form.get('categoria'),
            origem=request.form.get('origem'), operador_id=current_user.id)
        db.session.commit(); flash('Pendência reclassificada.', 'success')
    except PendenciaError as e:
        db.session.rollback(); flash(str(e), 'danger')
    return redirect(request.referrer or url_for('motos_assai.pendencias_abertas'))
```

Em `_coletar_filtros`, adicionar `categoria`/`origem`/`tratativa` de `request.args`; passar as constantes `sorted(...)` (categorias/origens/tratativas) ao template para os selects.

- [ ] **Step 4: Refactor `abertas.html`** — remover o modal `#modal-resolver-pendencia`, o `window.MOTOS_ASSAI_PENDENCIAS` e o `<script src=".../pendencias_resolver.js">`; botão "Resolver" → link `url_for('motos_assai.pendencia_resolver_tela', pid=p.pendencia_id)`; colunas Categoria/Origem/Fase (badge destacado se `p.categoria == 'INDETERMINADA'`); botão "Reclassificar" → modal pequeno `POST url_for('motos_assai.pendencia_reclassificar', pid=p.pendencia_id)`; selects categoria/origem/tratativa no filtro; coluna `#` linka `pendencia_detalhe`.

- [ ] **Step 5: Refactor `historico.html`** — coluna Tratativa (`h.tratativa`) + mesmos selects de filtro; `#` linka `pendencia_detalhe`.

- [ ] **Step 6: Delete the old JS**

```bash
git rm app/static/motos_assai/js/pendencias_resolver.js
```

- [ ] **Step 7: Run the affected suites**

Run: `pytest tests/motos_assai/test_integracao_ganchos.py tests/motos_assai/test_montagem_service.py tests/motos_assai/test_montagem_service_carregada.py tests/motos_assai/test_pendencia_rotas.py -q`
Expected: PASS (sem os testes removidos).
Run: `grep -rn "pendencias_resolver\|montagem_service.resolver_pendencia\|import resolver_pendencia" app/ tests/` → só `pendencia_service.resolver_pendencia` (o átomo) deve restar.

- [ ] **Step 8: Commit**

```bash
git add -A app/motos_assai/routes/pendencias.py app/motos_assai/services/montagem_service.py app/motos_assai/services/__init__.py app/templates/motos_assai/pendencias/ tests/motos_assai/
git commit -m "refactor(motos_assai): remove shim resolver_pendencia; rota por pendencia_id; listas com categoria/filtros (Spec 2)"
```

---

## FASE 3 — Peças (catálogo/estoque/compra)

### Task 10: Catálogo de Peça (CRUD + N:N modelos)

**Files:**
- Create: `app/motos_assai/routes/peca.py`; `app/motos_assai/forms/peca_forms.py`; `app/templates/motos_assai/pecas/{lista,form,detalhe}.html`
- Modify: `app/motos_assai/routes/__init__.py`; `app/motos_assai/forms/__init__.py`
- Test: `tests/motos_assai/test_pecas_rotas.py`

**Interfaces:**
- Consumes: `peca_service.{criar_peca,editar_peca,vincular_modelo,desvincular_modelo,listar,listar_compativeis}`; `movimento_service.{saldo,custo_medio}`.
- Produces: endpoints `motos_assai.peca_lista`, `peca_novo`, `peca_editar`, `peca_detalhe` (URLs `/pecas`…).

- [ ] **Step 1: Write the failing smoke test**

```python
# tests/motos_assai/test_pecas_rotas.py
import uuid
from app import db
from app.motos_assai.models import AssaiPeca, AssaiModelo


def test_lista_pecas_200(login_admin):
    assert login_admin.get('/motos-assai/pecas').status_code == 200


def test_criar_peca_via_post(login_admin, app):
    nome = f'PZROTA{uuid.uuid4().hex[:6].upper()}'
    with app.app_context():
        mid = AssaiModelo.query.filter_by(codigo='DOT').first().id
    resp = login_admin.post('/motos-assai/pecas/novo', data={
        'nome': nome, 'codigo': 'C1', 'custo_referencia': '12,50',
        'ativo': 'y', 'modelo_ids': [mid]})
    assert resp.status_code in (302, 200)
    with app.app_context():
        p = AssaiPeca.query.filter_by(nome=nome).first()
        assert p is not None and len(p.modelos) == 1
        db.session.delete(p); db.session.commit()
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/motos_assai/test_pecas_rotas.py -v`
Expected: FAIL (404).

- [ ] **Step 3: Create the form**

```python
# app/motos_assai/forms/peca_forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, BooleanField, SelectMultipleField
from wtforms.validators import DataRequired, Optional as Opt


class PecaForm(FlaskForm):
    nome = StringField('Nome', validators=[DataRequired()])
    codigo = StringField('Código', validators=[Opt()])
    custo_referencia = StringField('Custo referência (R$)', validators=[Opt()])
    ativo = BooleanField('Ativa', default=True)
    modelo_ids = SelectMultipleField('Modelos compatíveis', coerce=int, validators=[Opt()])
```

Exportar em `forms/__init__.py`.

- [ ] **Step 4: Create the route** (`routes/peca.py`), registrando `from app.motos_assai.routes import peca  # noqa: E402,F401` em `routes/__init__.py`:

```python
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app import db
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.forms.peca_forms import PecaForm
from app.motos_assai.services import peca_service, movimento_service
from app.motos_assai.services.peca_service import PecaError
from app.motos_assai.models import AssaiModelo, AssaiPeca


def _modelo_choices():
    return [(m.id, f'{m.codigo} — {m.nome}') for m in AssaiModelo.query.order_by(AssaiModelo.codigo).all()]


def _br_decimal(s):
    s = (s or '').strip().replace('.', '').replace(',', '.')
    return s or None


@motos_assai_bp.route('/pecas')
@login_required
@require_motos_assai
def peca_lista():
    busca = (request.args.get('q') or '').strip() or None
    pecas = peca_service.listar(ativo=None, busca=busca)
    linhas = [{'p': p, 'saldo': movimento_service.saldo(p.id)} for p in pecas]
    return render_template('motos_assai/pecas/lista.html', linhas=linhas, q=busca or '')


@motos_assai_bp.route('/pecas/novo', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def peca_novo():
    form = PecaForm()
    form.modelo_ids.choices = _modelo_choices()
    if form.validate_on_submit():
        try:
            peca_service.criar_peca(
                nome=form.nome.data, codigo=form.codigo.data or None,
                custo_referencia=_br_decimal(form.custo_referencia.data),
                modelo_ids=form.modelo_ids.data, operador_id=current_user.id)
            db.session.commit(); flash('Peça criada.', 'success')
            return redirect(url_for('motos_assai.peca_lista'))
        except PecaError as e:
            db.session.rollback(); flash(str(e), 'danger')
    return render_template('motos_assai/pecas/form.html', form=form, modo='novo')


@motos_assai_bp.route('/pecas/<int:pid>/editar', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def peca_editar(pid):
    peca = db.session.get(AssaiPeca, pid)
    if not peca:
        flash('Peça não encontrada.', 'danger')
        return redirect(url_for('motos_assai.peca_lista'))
    form = PecaForm(obj=peca)
    form.modelo_ids.choices = _modelo_choices()
    if request.method == 'GET':
        form.modelo_ids.data = [pm.modelo_id for pm in peca.modelos]
    if form.validate_on_submit():
        try:
            peca_service.editar_peca(
                peca_id=pid, nome=form.nome.data, codigo=form.codigo.data or None,
                custo_referencia=_br_decimal(form.custo_referencia.data), ativo=form.ativo.data)
            atuais = {pm.modelo_id for pm in peca.modelos}
            novos = set(form.modelo_ids.data or [])
            for mid in (novos - atuais):
                peca_service.vincular_modelo(peca_id=pid, modelo_id=mid)
            for mid in (atuais - novos):
                peca_service.desvincular_modelo(peca_id=pid, modelo_id=mid)
            db.session.commit(); flash('Peça atualizada.', 'success')
            return redirect(url_for('motos_assai.peca_detalhe', pid=pid))
        except PecaError as e:
            db.session.rollback(); flash(str(e), 'danger')
    return render_template('motos_assai/pecas/form.html', form=form, modo='editar', peca=peca)


@motos_assai_bp.route('/pecas/<int:pid>')
@login_required
@require_motos_assai
def peca_detalhe(pid):
    peca = db.session.get(AssaiPeca, pid)
    if not peca:
        flash('Peça não encontrada.', 'danger')
        return redirect(url_for('motos_assai.peca_lista'))
    return render_template('motos_assai/pecas/detalhe.html', peca=peca,
                           saldo=movimento_service.saldo(pid),
                           custo_medio=movimento_service.custo_medio(pid))
```

- [ ] **Step 5: Create the 3 templates** (molde `modelos/{lista,form,detalhe}.html`): `lista.html` (tabela nome/código/ativo/saldo + link editar/detalhe + botão "Nova peça"); `form.html` (campos + `SelectMultipleField` de modelos + `{{ form.hidden_tag() }}`); `detalhe.html` (dados + modelos compatíveis + saldo/custo médio + link `estoque_peca_detalhe`).

- [ ] **Step 6: Run to verify it passes**

Run: `pytest tests/motos_assai/test_pecas_rotas.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/motos_assai/routes/peca.py app/motos_assai/routes/__init__.py app/motos_assai/forms/ app/templates/motos_assai/pecas/ tests/motos_assai/test_pecas_rotas.py
git commit -m "feat(motos_assai): catalogo de peca (CRUD + compatibilidade N:N) (Spec 2)"
```

---

### Task 11: Estoque de Peça (ledger + entrada/ajuste/descarte)

**Files:**
- Create: `app/motos_assai/routes/estoque_peca.py`; `app/templates/motos_assai/estoque_pecas/{lista,detalhe}.html`
- Modify: `app/motos_assai/routes/__init__.py`
- Test: `tests/motos_assai/test_estoque_peca_rotas.py`

**Interfaces:**
- Consumes: `movimento_service.{registrar_entrada,ajustar,descartar,saldo,custo_medio}`; `peca_service.listar`; models `AssaiPeca`, `AssaiEstoqueMovimento`.
- Produces: endpoints `estoque_peca_lista`, `estoque_peca_detalhe`, `estoque_peca_entrada`, `estoque_peca_ajustar`, `estoque_peca_descartar`.

- [ ] **Step 1: Write the failing smoke test**

```python
# tests/motos_assai/test_estoque_peca_rotas.py
import uuid
from decimal import Decimal
from app import db
from app.motos_assai.services.peca_service import criar_peca
from app.motos_assai.services.movimento_service import saldo


def test_lista_estoque_200(login_admin):
    assert login_admin.get('/motos-assai/estoque-pecas').status_code == 200


def test_entrada_avulsa_incrementa_saldo(login_admin, app, admin_user):
    with app.app_context():
        p = criar_peca(nome=f'PZE{uuid.uuid4().hex[:6].upper()}', operador_id=admin_user.id)
        db.session.commit(); pid = p.id
    resp = login_admin.post('/motos-assai/estoque-pecas/entrada', data={
        'peca_id': pid, 'quantidade': '5', 'custo_unitario': '10,00', 'recebimento_ref': 'LOTE1'})
    assert resp.status_code in (302, 200)
    with app.app_context():
        assert saldo(pid) == Decimal('5.000')
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/motos_assai/test_estoque_peca_rotas.py -v`
Expected: FAIL (404).

- [ ] **Step 3: Create `routes/estoque_peca.py`** (registrar em `routes/__init__.py`). CSRF via `FlaskForm()` vazia (padrão `NovaCompraForm`), leitura de `request.form`:

```python
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from app import db
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services import peca_service, movimento_service
from app.motos_assai.services.movimento_service import EstoqueError
from app.motos_assai.models import AssaiPeca, AssaiEstoqueMovimento


def _br(s):
    s = (s or '').strip().replace('.', '').replace(',', '.')
    return s or None


@motos_assai_bp.route('/estoque-pecas')
@login_required
@require_motos_assai
def estoque_peca_lista():
    linhas = [{'p': p, 'saldo': movimento_service.saldo(p.id),
               'custo_medio': movimento_service.custo_medio(p.id)}
              for p in peca_service.listar(ativo=None)]
    return render_template('motos_assai/estoque_pecas/lista.html', linhas=linhas, form=FlaskForm())


@motos_assai_bp.route('/estoque-pecas/<int:peca_id>')
@login_required
@require_motos_assai
def estoque_peca_detalhe(peca_id):
    peca = db.session.get(AssaiPeca, peca_id)
    if not peca:
        flash('Peça não encontrada.', 'danger')
        return redirect(url_for('motos_assai.estoque_peca_lista'))
    movs = (AssaiEstoqueMovimento.query.filter_by(peca_id=peca_id)
            .order_by(AssaiEstoqueMovimento.id.desc()).limit(300).all())
    return render_template('motos_assai/estoque_pecas/detalhe.html', peca=peca, movs=movs,
                           saldo=movimento_service.saldo(peca_id),
                           custo_medio=movimento_service.custo_medio(peca_id), form=FlaskForm())


@motos_assai_bp.route('/estoque-pecas/entrada', methods=['POST'])
@login_required
@require_motos_assai
def estoque_peca_entrada():
    try:
        movimento_service.registrar_entrada(
            peca_id=request.form.get('peca_id', type=int),
            quantidade=_br(request.form.get('quantidade')),
            custo_unitario=_br(request.form.get('custo_unitario')),
            operador_id=current_user.id,
            recebimento_ref=(request.form.get('recebimento_ref') or None))
        db.session.commit(); flash('Entrada registrada.', 'success')
    except EstoqueError as e:
        db.session.rollback(); flash(str(e), 'danger')
    return redirect(request.referrer or url_for('motos_assai.estoque_peca_lista'))


@motos_assai_bp.route('/estoque-pecas/ajustar', methods=['POST'])
@login_required
@require_motos_assai
def estoque_peca_ajustar():
    try:
        movimento_service.ajustar(
            peca_id=request.form.get('peca_id', type=int),
            delta=_br(request.form.get('delta')),
            motivo=request.form.get('motivo', ''), operador_id=current_user.id)
        db.session.commit(); flash('Ajuste registrado.', 'success')
    except EstoqueError as e:
        db.session.rollback(); flash(str(e), 'danger')
    return redirect(request.referrer or url_for('motos_assai.estoque_peca_lista'))


@motos_assai_bp.route('/estoque-pecas/descartar', methods=['POST'])
@login_required
@require_motos_assai
def estoque_peca_descartar():
    try:
        movimento_service.descartar(
            peca_id=request.form.get('peca_id', type=int),
            quantidade=_br(request.form.get('quantidade')), operador_id=current_user.id)
        db.session.commit(); flash('Descarte registrado.', 'success')
    except EstoqueError as e:
        db.session.rollback(); flash(str(e), 'danger')
    return redirect(request.referrer or url_for('motos_assai.estoque_peca_lista'))
```

- [ ] **Step 4: Create templates** `estoque_pecas/{lista,detalhe}.html`: `lista.html` (peça · saldo · custo médio + botão "Entrada" abrindo modal; link detalhe); `detalhe.html` (topo saldo/custo médio + tabela do ledger + modais Entrada/Ajuste/Descarte com forms POST + `{{ form.hidden_tag() }}`).

- [ ] **Step 5: Run to verify it passes**

Run: `pytest tests/motos_assai/test_estoque_peca_rotas.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/motos_assai/routes/estoque_peca.py app/motos_assai/routes/__init__.py app/templates/motos_assai/estoque_pecas/ tests/motos_assai/test_estoque_peca_rotas.py
git commit -m "feat(motos_assai): estoque de peca (ledger + entrada/ajuste/descarte) (Spec 2)"
```

---

### Task 12: Pedido de Compra de Peça

**Files:**
- Create: `app/motos_assai/routes/compra_peca.py`; `app/templates/motos_assai/compras_pecas/{lista,nova,detalhe}.html`
- Modify: `app/motos_assai/routes/__init__.py`
- Test: `tests/motos_assai/test_compra_peca_rotas.py`

**Interfaces:**
- Consumes: `compra_peca_service.{criar_compra,receber_item,cancelar_compra}`; `peca_service.listar`; models `AssaiPecaCompra`.
- Produces: endpoints `compra_peca_lista`, `compra_peca_nova`, `compra_peca_detalhe`, `compra_peca_receber_item`, `compra_peca_cancelar`.

- [ ] **Step 1: Write the failing smoke test**

```python
# tests/motos_assai/test_compra_peca_rotas.py
import re, uuid
from app import db
from app.motos_assai.services.peca_service import criar_peca
from app.motos_assai.models import AssaiPecaCompra


def test_lista_compras_200(login_admin):
    assert login_admin.get('/motos-assai/compras-peca').status_code == 200


def test_criar_compra_via_post(login_admin, app, admin_user):
    with app.app_context():
        p = criar_peca(nome=f'PZC{uuid.uuid4().hex[:6].upper()}', operador_id=admin_user.id)
        db.session.commit(); pid = p.id
    resp = login_admin.post('/motos-assai/compras-peca/nova', data={
        'tipo': 'COMPRA', 'fornecedor': 'MOTOCHEFE',
        'peca_id': [pid], 'quantidade': ['3'], 'custo_estimado': ['9,00']})
    assert resp.status_code in (302, 200)
    with app.app_context():
        c = AssaiPecaCompra.query.order_by(AssaiPecaCompra.id.desc()).first()
        assert re.match(r'^PC-\d{4}-\d{4,}$', c.numero) and len(c.itens) == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/motos_assai/test_compra_peca_rotas.py -v`
Expected: FAIL (404).

- [ ] **Step 3: Create `routes/compra_peca.py`** (registrar em `routes/__init__.py`; molde `routes/compras.py`):

```python
from flask import render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from flask_wtf import FlaskForm
from app import db
from app.motos_assai.routes import motos_assai_bp
from app.motos_assai.decorators import require_motos_assai
from app.motos_assai.services import compra_peca_service, peca_service
from app.motos_assai.services.compra_peca_service import CompraPecaError
from app.motos_assai.models import AssaiPecaCompra


def _br(s):
    s = (s or '').strip().replace('.', '').replace(',', '.')
    return s or None


@motos_assai_bp.route('/compras-peca')
@login_required
@require_motos_assai
def compra_peca_lista():
    compras = AssaiPecaCompra.query.order_by(AssaiPecaCompra.id.desc()).all()
    return render_template('motos_assai/compras_pecas/lista.html', compras=compras)


@motos_assai_bp.route('/compras-peca/nova', methods=['GET', 'POST'])
@login_required
@require_motos_assai
def compra_peca_nova():
    if request.method == 'POST':
        peca_ids = request.form.getlist('peca_id', type=int)
        qtds = request.form.getlist('quantidade')
        custos = request.form.getlist('custo_estimado')
        itens = [{'peca_id': pid, 'quantidade': _br(qtds[i]),
                  'custo_estimado': _br(custos[i]) if i < len(custos) else None}
                 for i, pid in enumerate(peca_ids) if pid and _br(qtds[i])]
        try:
            c = compra_peca_service.criar_compra(
                tipo=request.form.get('tipo'), itens=itens,
                operador_id=current_user.id,
                fornecedor=request.form.get('fornecedor') or 'MOTOCHEFE')
            db.session.commit(); flash(f'Compra {c.numero} criada.', 'success')
            return redirect(url_for('motos_assai.compra_peca_detalhe', cid=c.id))
        except CompraPecaError as e:
            db.session.rollback(); flash(str(e), 'danger')
    pecas = peca_service.listar(ativo=True)
    return render_template('motos_assai/compras_pecas/nova.html', pecas=pecas, form=FlaskForm())


@motos_assai_bp.route('/compras-peca/<int:cid>')
@login_required
@require_motos_assai
def compra_peca_detalhe(cid):
    c = db.session.get(AssaiPecaCompra, cid)
    if not c:
        flash('Compra não encontrada.', 'danger')
        return redirect(url_for('motos_assai.compra_peca_lista'))
    return render_template('motos_assai/compras_pecas/detalhe.html', c=c, form=FlaskForm())


@motos_assai_bp.route('/compras-peca/<int:cid>/receber-item', methods=['POST'])
@login_required
@require_motos_assai
def compra_peca_receber_item(cid):
    try:
        compra_peca_service.receber_item(
            compra_item_id=request.form.get('compra_item_id', type=int),
            quantidade=_br(request.form.get('quantidade')),
            custo_unitario=_br(request.form.get('custo_unitario')),
            operador_id=current_user.id)
        db.session.commit(); flash('Item recebido (entrada no estoque).', 'success')
    except CompraPecaError as e:
        db.session.rollback(); flash(str(e), 'danger')
    return redirect(url_for('motos_assai.compra_peca_detalhe', cid=cid))


@motos_assai_bp.route('/compras-peca/<int:cid>/cancelar', methods=['POST'])
@login_required
@require_motos_assai
def compra_peca_cancelar(cid):
    try:
        compra_peca_service.cancelar_compra(compra_id=cid, operador_id=current_user.id)
        db.session.commit(); flash('Compra cancelada.', 'success')
    except CompraPecaError as e:
        db.session.rollback(); flash(str(e), 'danger')
    return redirect(url_for('motos_assai.compra_peca_detalhe', cid=cid))
```

- [ ] **Step 4: Create templates** `compras_pecas/{lista,nova,detalhe}.html`: `lista.html` (nº/tipo/status/fornecedor/data + botão "Novo pedido"); `nova.html` (select tipo/fornecedor + N linhas peça/qtd/custo com JS add/remove — molde `compras/nova.html`); `detalhe.html` (cabeçalho + itens com form "receber item" por linha + botão cancelar; badge status).

- [ ] **Step 5: Run to verify it passes**

Run: `pytest tests/motos_assai/test_compra_peca_rotas.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/motos_assai/routes/compra_peca.py app/motos_assai/routes/__init__.py app/templates/motos_assai/compras_pecas/ tests/motos_assai/test_compra_peca_rotas.py
git commit -m "feat(motos_assai): pedido de compra de peca (criar/receber item) (Spec 2)"
```

---

## FASE 4 — Pós-venda + Timeline + Menu

### Task 13: Pós-venda — gerar pendência + acompanhar

**Files:**
- Modify: `app/motos_assai/services/pos_venda_service.py`; `app/motos_assai/routes/pos_venda.py`
- Modify: `app/templates/motos_assai/pos_venda/{_macros,lista}.html`; `app/static/motos_assai/js/pos_venda.js`
- Test: `tests/motos_assai/test_pos_venda_pendencia.py`

**Interfaces:**
- Consumes: `pendencia_service.abrir_pendencia`; models `AssaiPendencia`, `AssaiPosVendaOcorrencia`, `PENDENCIA_ORIGEM_POS_VENDA_LOJA`/`_CLIENTE`.
- Produces: `pos_venda_service.{gerar_pendencia_de_ocorrencia, pendencias_da_ocorrencia, contar_pendencias_abertas_por_chassi}`; endpoint `pos_venda_gerar_pendencia` (POST).

> **Pré-leitura obrigatória:** abrir `app/motos_assai/services/pos_venda_service.py` ANTES de implementar — confirmar o nome real da exceção (`PosVendaValidationError`), os atributos de `AssaiPosVendaOcorrencia` (`chassi`, `categoria`, `descricao`) e a assinatura de `criar_ocorrencia`. A montagem de `AssaiNfQpa`+`AssaiNfQpaItem` da fixture segue o padrão de `tests/motos_assai/test_aplicar_correcao_cce.py:90-108` (campos NOT NULL confirmados no schema: `assai_nf_qpa` = `chave_44`/`status_match`/`importada_em`; `assai_nf_qpa_item` = `nf_id`/`chassi`/`devolvido`).

- [ ] **Step 1: Write the failing test**

```python
# tests/motos_assai/test_pos_venda_pendencia.py
import uuid
import pytest
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, AssaiNfQpa, AssaiNfQpaItem, NF_STATUS_BATEU,
    PENDENCIA_ORIGEM_POS_VENDA_LOJA,
)
from app.utils.timezone import agora_brasil_naive
from app.motos_assai.services import pos_venda_service


@pytest.fixture
def chassi_vendido(app, admin_user):
    """AssaiMoto + AssaiNfQpa + AssaiNfQpaItem minimos p/ passar chassi_foi_vendido
    (que so checa presenca em assai_nf_qpa_item). Retorna o chassi (str)."""
    with app.app_context():
        chassi = f'TSTPV{uuid.uuid4().hex[:6].upper()}'
        modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
        db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
        nf = AssaiNfQpa(
            chave_44=('9' * 38 + uuid.uuid4().hex[:6]).upper()[:44],
            status_match=NF_STATUS_BATEU, importada_em=agora_brasil_naive(),
            importada_por_id=admin_user.id)
        db.session.add(nf); db.session.flush()
        db.session.add(AssaiNfQpaItem(nf_id=nf.id, chassi=chassi))
        db.session.commit()
        yield chassi


def test_gerar_pendencia_sem_retorno_nao_trava(app, admin_user, chassi_vendido):
    with app.app_context():
        oc = pos_venda_service.criar_ocorrencia(
            chassi=chassi_vendido, categoria='LOJA', descricao='barulho',
            operador_id=admin_user.id)
        db.session.commit()
        f = pos_venda_service.gerar_pendencia_de_ocorrencia(
            ocorrencia_id=oc.id, categoria='AVARIA', retorno_fisico=False,
            operador_id=admin_user.id)
        db.session.commit()
        assert f.origem == PENDENCIA_ORIGEM_POS_VENDA_LOJA
        assert f.evento_pendente_id is None  # nao-fisica
        assert pos_venda_service.pendencias_da_ocorrencia(oc.id)[0].id == f.id
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/motos_assai/test_pos_venda_pendencia.py -v`
Expected: FAIL (`AttributeError: gerar_pendencia_de_ocorrencia`).

- [ ] **Step 3: Add service helpers** em `pos_venda_service.py`:

```python
def gerar_pendencia_de_ocorrencia(*, ocorrencia_id, categoria, retorno_fisico, operador_id):
    """Abre uma AssaiPendencia a partir de uma ocorrencia de pos-venda (Spec 2 §5).
    Origem derivada da categoria da ocorrencia (LOJA/CLIENTE). add+flush, sem commit."""
    from app.motos_assai.models import (
        AssaiPosVendaOcorrencia, PENDENCIA_ORIGEM_POS_VENDA_LOJA,
        PENDENCIA_ORIGEM_POS_VENDA_CLIENTE,
    )
    from app.motos_assai.services.pendencia_service import abrir_pendencia
    oc = db.session.get(AssaiPosVendaOcorrencia, ocorrencia_id)
    if oc is None:
        raise PosVendaValidationError(f'Ocorrência {ocorrencia_id} não encontrada.')
    origem = (PENDENCIA_ORIGEM_POS_VENDA_LOJA if oc.categoria == 'LOJA'
              else PENDENCIA_ORIGEM_POS_VENDA_CLIENTE)
    return abrir_pendencia(
        chassi=oc.chassi, categoria=categoria, origem=origem,
        descricao=(oc.descricao or 'Ocorrência pós-venda')[:2000],
        pos_venda_ocorrencia_id=oc.id, retorno_fisico=bool(retorno_fisico),
        operador_id=operador_id)


def pendencias_da_ocorrencia(ocorrencia_id):
    from app.motos_assai.models import AssaiPendencia
    return (AssaiPendencia.query
            .filter(AssaiPendencia.pos_venda_ocorrencia_id == ocorrencia_id)
            .order_by(AssaiPendencia.aberta_em.desc()).all())


def contar_pendencias_abertas_por_chassi(chassi):
    from app.motos_assai.models import AssaiPendencia
    return (AssaiPendencia.query.filter(
        AssaiPendencia.chassi == (chassi or '').strip().upper(),
        AssaiPendencia.resolvida_em.is_(None),
        AssaiPendencia.cancelada_em.is_(None)).count())
```

Conferir os nomes reais (`PosVendaValidationError`, `oc.chassi`, `oc.categoria`, `oc.descricao`) contra o service antes de rodar.

- [ ] **Step 4: Add the route** em `routes/pos_venda.py`:

```python
@motos_assai_bp.route('/pos-venda/ocorrencias/<int:oc_id>/gerar-pendencia', methods=['POST'])
@login_required
@require_motos_assai
def pos_venda_gerar_pendencia(oc_id):
    from app.motos_assai.services import pos_venda_service
    data = request.get_json(silent=True) or request.form
    try:
        f = pos_venda_service.gerar_pendencia_de_ocorrencia(
            ocorrencia_id=oc_id, categoria=data.get('categoria'),
            retorno_fisico=str(data.get('retorno_fisico')) in ('1', 'true', 'on', 'True'),
            operador_id=current_user.id)
        db.session.commit()
        return jsonify({'ok': True, 'pendencia_id': f.id})
    except Exception as e:
        db.session.rollback()
        return jsonify({'ok': False, 'erro': str(e)}), 400
```

- [ ] **Step 5: UI** — `_macros.html render_ocorrencia`: botão "Gerar pendência" + mini-form (select categoria AVARIA/FALTA_PECA/REVISAO + checkbox retorno físico); listar as pendências vinculadas (passar via contexto) com badge+link `pendencia_detalhe`. `pos_venda.js`: delegação em `#modal-ocorrencias-body` p/ POST `gerar-pendencia`. `lista.html`: badge "Pendências (N)" na coluna Ações (N de `contar_pendencias_abertas_por_chassi`, enriquecendo a linha na rota `pos_venda_lista`).

- [ ] **Step 6: Run to verify it passes**

Run: `pytest tests/motos_assai/test_pos_venda_pendencia.py -v`
Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add app/motos_assai/services/pos_venda_service.py app/motos_assai/routes/pos_venda.py app/templates/motos_assai/pos_venda/ app/static/motos_assai/js/pos_venda.js tests/motos_assai/test_pos_venda_pendencia.py
git commit -m "feat(motos_assai): pos-venda gera + acompanha pendencia (Spec 2)"
```

---

### Task 14: Timeline unificada no rastreamento de chassi

**Files:**
- Modify: `app/motos_assai/services/rastreamento_chassi_service.py`
- Modify: `app/templates/motos_assai/resumo/_modal_rastreamento.html`
- Test: `tests/motos_assai/test_rastreamento_timeline_pendencia.py`

**Interfaces:**
- Consumes: models `AssaiPendencia`, `AssaiEstoqueMovimento`; helper `_dt` do módulo.
- Produces: `rastrear_chassi(chassi)` inclui `fichas_pendencia[]` + `movimentos_peca[]` + contadores.

- [ ] **Step 1: Write the failing test**

```python
# tests/motos_assai/test_rastreamento_timeline_pendencia.py
import uuid
from app import db
from app.motos_assai.models import (
    AssaiMoto, AssaiModelo, PENDENCIA_CATEGORIA_AVARIA, PENDENCIA_ORIGEM_GALPAO,
)
from app.motos_assai.services.pendencia_service import abrir_pendencia
from app.motos_assai.services.rastreamento_chassi_service import rastrear_chassi


def test_rastreamento_inclui_fichas_pendencia(app, admin_user):
    with app.app_context():
        chassi = f'TSTTL{uuid.uuid4().hex[:6].upper()}'
        modelo = AssaiModelo.query.filter_by(codigo='DOT').first()
        db.session.add(AssaiMoto(chassi=chassi, modelo_id=modelo.id, cor='CINZA'))
        db.session.flush()
        abrir_pendencia(chassi=chassi, categoria=PENDENCIA_CATEGORIA_AVARIA,
                        origem=PENDENCIA_ORIGEM_GALPAO, descricao='x', operador_id=admin_user.id)
        db.session.commit()
        r = rastrear_chassi(chassi)
        assert 'fichas_pendencia' in r and len(r['fichas_pendencia']) == 1
        assert r['fichas_pendencia'][0]['categoria'] == PENDENCIA_CATEGORIA_AVARIA
        assert 'movimentos_peca' in r
        assert r['contadores']['fichas_pendencia'] == 1
```

- [ ] **Step 2: Run to verify it fails**

Run: `pytest tests/motos_assai/test_rastreamento_timeline_pendencia.py -v`
Expected: FAIL (`KeyError: 'fichas_pendencia'`).

- [ ] **Step 3: Add the sections** em `rastrear_chassi` (após `divergencias = _buscar_divergencias(...)`): calcular `fichas_pendencia = _buscar_fichas_pendencia(chassi_norm)` e `movimentos_peca = _buscar_movimentos_peca(chassi_norm)`; incluir no `encontrado` (`or fichas_pendencia or movimentos_peca`), no dict de retorno e nos `contadores` (`'fichas_pendencia': len(fichas_pendencia)`, `'movimentos_peca': len(movimentos_peca)`). Helpers:

```python
def _buscar_fichas_pendencia(chassi):
    from app.motos_assai.models import AssaiPendencia
    fichas = (AssaiPendencia.query.filter(AssaiPendencia.chassi == chassi)
              .order_by(AssaiPendencia.aberta_em.desc()).all())
    out = []
    for f in fichas:
        status = 'aberta' if f.esta_aberta else ('resolvida' if f.resolvida_em else 'cancelada')
        out.append({
            'pendencia_id': f.id, 'categoria': f.categoria, 'origem': f.origem,
            'fase': f.fase, 'tratativa': f.tratativa, 'status': status,
            'descricao': f.descricao, 'resolucao_descricao': f.resolucao_descricao,
            'aberta_em': _dt(f.aberta_em), 'resolvida_em': _dt(f.resolvida_em),
        })
    return out


def _buscar_movimentos_peca(chassi):
    from app.motos_assai.models import AssaiEstoqueMovimento
    from sqlalchemy import or_
    movs = (AssaiEstoqueMovimento.query.filter(
        or_(AssaiEstoqueMovimento.chassi_origem == chassi,
            AssaiEstoqueMovimento.chassi_destino == chassi))
        .order_by(AssaiEstoqueMovimento.id.desc()).all())
    return [{
        'tipo': m.tipo, 'peca_nome': m.peca.nome if m.peca else '-',
        'quantidade': m.quantidade, 'custo_total': m.custo_total,
        'chassi_origem': m.chassi_origem, 'chassi_destino': m.chassi_destino,
        'ocorrido_em': _dt(m.ocorrido_em),
    } for m in movs]
```

- [ ] **Step 4: Run to verify it passes**

Run: `pytest tests/motos_assai/test_rastreamento_timeline_pendencia.py -v`
Expected: PASS.

- [ ] **Step 5: Template** — `resumo/_modal_rastreamento.html`: 2 seções novas (Fichas de Pendência com link `pendencia_detalhe`; Movimentos de Peça) + os 2 contadores. Molde: as seções existentes no mesmo arquivo.

- [ ] **Step 6: Commit**

```bash
git add app/motos_assai/services/rastreamento_chassi_service.py app/templates/motos_assai/resumo/_modal_rastreamento.html tests/motos_assai/test_rastreamento_timeline_pendencia.py
git commit -m "feat(motos_assai): rastreamento do chassi com fichas de pendencia + movimentos de peca (Spec 2)"
```

---

### Task 15: Menu — 3 itens novos

**Files:**
- Modify: `app/templates/motos_assai/base_motos_assai.html`

**Interfaces:**
- Consumes: endpoints `peca_lista`, `estoque_peca_lista`, `compra_peca_lista`.

- [ ] **Step 1: Add nav items** — logo após o link "Pendências" (`#menu-pendencias`):

```html
<a id="menu-pecas" class="motos-assai-nav-link" href="{{ url_for('motos_assai.peca_lista') }}"><i class="fas fa-gears"></i> Peças</a>
<a id="menu-estoque-pecas" class="motos-assai-nav-link" href="{{ url_for('motos_assai.estoque_peca_lista') }}"><i class="fas fa-boxes-stacked"></i> Estoque Peça</a>
<a id="menu-compras-pecas" class="motos-assai-nav-link" href="{{ url_for('motos_assai.compra_peca_lista') }}"><i class="fas fa-file-invoice-dollar"></i> Compras Peça</a>
```

- [ ] **Step 2: Verify** — qualquer tela do módulo renderiza (o `url_for` resolve os 3 endpoints; nome divergente → `BuildError`).

Run: `pytest tests/motos_assai/test_pecas_rotas.py::test_lista_pecas_200 -v`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add app/templates/motos_assai/base_motos_assai.html
git commit -m "feat(motos_assai): itens de menu Pecas/Estoque Peca/Compras Peca (Spec 2)"
```

---

## FASE 5 — Fechamento

### Task 16: Hint do schema + doc do módulo

**Files:**
- Modify: `.claude/skills/consultando-sql/schemas/tables/assai_pendencia.json`
- Modify: `app/motos_assai/CLAUDE.md`

**Interfaces:** nenhuma (docs).

- [ ] **Step 1: Refinar a hint do `assai_pendencia.json`** — a descrição de `afeta_estado_moto` deve citar que a ficha afeta o estado da moto quando `origem ∈ {GALPAO,TRANSPORTE,DEVOLUCAO}` OU `devolucao_item_id` OU `retorno_fisico=True` (hoje só cita pós-venda). Só texto de descrição; nenhuma coluna mudou (edição textual pontual — não precisa regenerar).

- [ ] **Step 2: Atualizar `app/motos_assai/CLAUDE.md`** — na seção "Estoque de Peças + Pendência categorizada": "Status de implementação" → **Spec 2 IMPLEMENTADO** (telas peça/estoque/compra, página de resolução por ficha + detalhe, pós-venda gera/acompanha, timeline no rastreamento, shim removido, follow-ups técnicos aplicados); acrescentar as rotas novas; registrar `resolucao_service` em "Services complementares"; mover os follow-ups resolvidos para "feito".

- [ ] **Step 3: Rodar o doc_audit + a suíte completa**

Run: `python scripts/audits/doc_audit.py --report-only --path app/motos_assai/CLAUDE.md`
Expected: OK.
Run: `pytest tests/motos_assai/ -q`
Expected: PASS (0 failed).

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/consultando-sql/schemas/tables/assai_pendencia.json app/motos_assai/CLAUDE.md
git commit -m "docs(motos_assai): CLAUDE.md Spec 2 implementado + hint assai_pendencia (Spec 2)"
```

---

## Deploy (após aval do dono — NÃO neste plano)

Sequência manual bundlada Spec 1 + Spec 2 (fora do `build.sh`): **migration 34** (já com a sequence) → **deploy do código** (push) → `python scripts/migrations/motos_assai_35_backfill_pendencias.py --confirmar` → `--check`. O `--check` falha se houver `PENDENTE` sem ficha (o shim foi removido; a resolução opera só por `pendencia_id`).

## Self-Review (executada na escrita)

- **Spec coverage:** Frentes A(4.1-4.7)→Tasks 3-9; B(§5)→Task 13; C(§6)→Task 10; D(§7)→Task 11; E(§8)→Task 12; F(§9)→Task 14; Menu(§10)→Task 15; follow-ups(§11)→Tasks 1,2,16; testes(§14)→cada task; deploy(§15)→seção final. Decisões S1-S8 cobertas (S1/S2→7,9; S3→13; S4/S7→9; S5→3; S6→4; S8→6,8,13,14).
- **Placeholder scan:** sem TBD/TODO; código real nos steps de lógica; templates com estrutura+molde+variáveis explícitas (o "teste" de template é o smoke de rota 200/302). Task 13 tem uma pré-leitura obrigatória explícita (nomes reais do `pos_venda_service`) por ser a de maior risco de divergência de assinatura.
- **Type consistency:** `resolver_com_tratativa` (Task 3) — assinatura idêntica consumida em Task 7. `detalhe_pendencia` (Task 5) — chaves `ficha/movimentos/custo_total/compras/filhas/pai` consumidas em Tasks 7,8. `pendencia_id` (Task 6) consumido nos templates/links das Tasks 7-9,13,14. `gerar_pendencia_de_ocorrencia` (Task 13) — nomes conferidos contra `pos_venda_service` na pré-leitura.
