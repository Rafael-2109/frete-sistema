<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-23
-->
# CarVia — Propagação de Endereço + Carta de Correção (CCe) — Implementation Plan

> **Papel:** plano de implementação bite-sized (TDD, commits frequentes) das duas frentes CarVia pedidas em 2026-06-23 — propagação de endereço destino + Carta de Correção (CCe). Derivado do spec `docs/superpowers/specs/2026-06-23-carvia-propagacao-endereco-cce-design.md` (aprovado).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

## Indice

- [Contexto](#contexto)
- [Global Constraints](#global-constraints)
- [FASE A — Propagação de cidade/UF](#fase-a--propagacao-de-cidadeuf)
  - [Task A1: Helper R1-safe](#task-a1-helper-r1-safe-de-propagacao-para-embarqueentrega)
  - [Task A2: Service de propagação](#task-a2-service-de-propagacao-resolve-cotacaonfoperacao-carvia)
  - [Task A3: Hook + API](#task-a3-hook-no-atualizar_endereco--contagem-na-resposta-da-api)
- [FASE B — Modelo CCe + anexo](#fase-b--modelo-cce-cadeia-compartilhada--anexo)
  - [Task B1: Extrair cadeia](#task-b1-extrair-logica-de-cadeia-para-modulo-compartilhado)
  - [Task B2: Models + migration](#task-b2-models-carviacartacorrecao--vinculo--migration--registro)
  - [Task B3: Service CCe](#task-b3-service-carviacartacorrecaoservice)
  - [Task B4: Rotas CCe](#task-b4-rotas-de-cce--registro-no-blueprint)
  - [Task B5: Card UI + cotação/NF](#task-b5-card-ui--js--insercao-no-detalhe-da-cotacao-e-da-nf)
- [FASE C — Impressão](#fase-c--impressao-pdfimagem-embutida)
  - [Task C1: Render PDF→imagem](#task-c1-helper-de-render-pdfimagem--base64)
  - [Task C2: Rota de impressão](#task-c2-rota-unica-de-impressao-de-cce--template)
  - [Task C3: Botão na NF](#task-c3-botao-imprimir-cce-no-detalhe-da-nf)
  - [Task C4: CCe no PDF do embarque](#task-c4-cce-no-pdf-do-embarque-capa--completo)
  - [Task C5: CCe no monitoramento](#task-c5-cce-no-monitoramento-exibir--imprimir)
- [Fechamento](#fechamento-parte-do-pronto)
- [Self-Review do plano](#self-review-do-plano)

## Contexto

Plano derivado do spec aprovado. Implementa, em 3 fases TDD independentes dentro do módulo CarVia (isolado — R1), o fluxo fiscal de correção de endereço: (A) ao editar o endereço destino de um cliente CarVia, propagar cidade/UF para NF/cotação/operação/embarque/monitoramento em aberto; (B) anexar uma Carta de Correção (CCe) por NF com cadeia compartilhada cotação↔NF (espelhando o padrão Comprovante existente); (C) imprimir a CCe junto no PDF do embarque, no detalhe da NF e no monitoramento (PDF→imagem via `pypdfium2`). Toda a base de código foi mapeada com `file_path:line_number` no spec; este plano traz o código real a escrever em cada passo.

**Goal:** Ao corrigir o endereço destino de um cliente CarVia, propagar cidade/UF para NF/cotação/operação/embarque/monitoramento em aberto; e permitir anexar uma Carta de Correção (CCe) por NF (com cadeia compartilhada cotação↔NF), imprimi-la junto no PDF do embarque, no detalhe da NF e no monitoramento.

**Architecture:** Três fases independentes dentro de `app/carvia/` (módulo isolado — R1). Fase A: service de propagação + helper R1-safe em `app/utils/`. Fase B: par de models espelhando o padrão Comprovante (N:N polimórfico + `sincronizar_cadeia`), com extração da lógica de cadeia para um módulo compartilhado. Fase C: render PDF→imagem (`pypdfium2`) embutido nos templates de impressão (HTML + `window.print()`).

**Tech Stack:** Flask 3.1 · SQLAlchemy 2.0 · Flask-Migrate · pypdfium2 5.4 · Pillow 12.1 · pytest · Jinja2 · Bootstrap 5.

## Global Constraints

- **R1 (isolamento CarVia):** `app/carvia/` NÃO importa `app/embarques`, `app/monitoramento`, `app/fretes`, `app/carteira` em module-level. Cruzamentos via **lazy import** ou helper R1-safe em `app/utils/` (espelha `app/utils/propagacao_local_cd.py`).
- **R2 (lazy imports):** imports de services/models de outros sub-pacotes ficam DENTRO das funções.
- **GAP-20:** nunca deletar registro fiscal — soft-delete via `ativo`.
- **Transação:** métodos de service fazem `db.session.add` + `flush`, **NÃO commitam** — o caller (rota) commita. Espelha `CarviaComprovanteService`.
- **Migration = par DDL + Python** (Flask-Migrate); `downgrade()` reverte na ordem inversa.
- **Storage S3:** sempre via `from app.utils.file_storage import get_file_storage`; `save_file(file, folder=...)`, `download_file(path)->bytes`, `get_download_url(path, filename)`.
- **Timezone:** datas naive via `from app.utils.timezone import agora_utc_naive`.
- **Permissão das rotas:** `if not getattr(current_user, 'sistema_carvia', False): return jsonify({'erro': 'Acesso negado.'}), 403`.
- **Testes:** pytest com a fixture `db` do `tests/conftest.py` (`def test_x(db):` — já abre app_context). Helpers criam objetos com `from app import db as _db`.
- **CCe model = ENXUTO:** apenas arquivo + `descricao`. SEM campos fiscais (protocolo/sequência/texto) — decisão C do brainstorming.
- **Não tocar** `CarviaEnderecoCorrecao` nem a flag `CARVIA_FEATURE_EDITAR_ENDERECO_CCE` (infra pré-existente de audit textual do CTe, fora de escopo; complementar à CCe-anexo).

---

## FASE A — Propagação de cidade/UF

### Task A1: Helper R1-safe de propagação para Embarque/Entrega

**Files:**
- Create: `app/utils/propagacao_endereco_carvia.py`
- Test: `tests/carvia/test_propagacao_endereco.py`

**Interfaces:**
- Produces: `propagar_cidade_uf_carvia(numeros_nf: list[str], cot_ids: list[int], cidade: str|None, uf: str|None) -> dict` retornando `{'embarque_itens': int, 'entregas': int}`.

- [ ] **Step 1: Write the failing test**

```python
# tests/carvia/test_propagacao_endereco.py
from app import db as _db
from app.utils.propagacao_endereco_carvia import propagar_cidade_uf_carvia


def _embarque_item_carvia(numero_nf, cidade, uf, lote='CARVIA-NF-1', status='ativo'):
    from app.embarques.models import Embarque, EmbarqueItem
    from app.utils.timezone import agora_utc_naive
    emb = Embarque(numero=None, status=status, criado_em=agora_utc_naive())
    _db.session.add(emb); _db.session.flush()
    item = EmbarqueItem(
        embarque_id=emb.id, separacao_lote_id=lote, nota_fiscal=numero_nf,
        cliente='C', pedido='P', cidade_destino=cidade, uf_destino=uf, status=status,
    )
    _db.session.add(item); _db.session.flush()
    return item


def _entrega_carvia(numero_nf, cidade, uf, entregue=False):
    from app.monitoramento.models import EntregaMonitorada
    e = EntregaMonitorada(numero_nf=numero_nf, cliente='C', municipio=cidade, uf=uf,
                          origem='CARVIA', entregue=entregue)
    _db.session.add(e); _db.session.flush()
    return e


def test_propaga_cidade_uf_para_embarque_item_carvia_aberto(db):
    item = _embarque_item_carvia('555', 'Cidade Velha', 'RJ')
    res = propagar_cidade_uf_carvia(['555'], [], 'Cidade Nova', 'SP')
    db.session.refresh(item)
    assert item.cidade_destino == 'Cidade Nova'
    assert item.uf_destino == 'SP'
    assert res['embarque_itens'] == 1


def test_nao_toca_entrega_ja_entregue(db):
    e = _entrega_carvia('556', 'Cidade Velha', 'RJ', entregue=True)
    res = propagar_cidade_uf_carvia(['556'], [], 'Cidade Nova', 'SP')
    db.session.refresh(e)
    assert e.municipio == 'Cidade Velha'  # intacta
    assert res['entregas'] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/carvia/test_propagacao_endereco.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'app.utils.propagacao_endereco_carvia'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/utils/propagacao_endereco_carvia.py
"""Propaga cidade/UF do cadastro de endereço CarVia para os destinos EXTERNOS
ao CarVia: `embarque_itens` (item CarVia) e `entregas_monitoradas` (origem CARVIA).

Mora em app/utils (zona neutra) porque o CarVia não pode importar app/embarques
nem app/monitoramento (R1). Espelha app/utils/propagacao_local_cd.py:
- Idempotente; UPDATE filtra status/entregue.
- Sem commit (UPDATE em massa synchronize_session=False); o caller commita.
- EmbarqueItem: separacao_lote_id LIKE 'CARVIA-%' E (nota_fiscal IN numeros_nf
  OU carvia_cotacao_id IN cot_ids), status 'ativo'. NUNCA toca itens Nacom.
- EntregaMonitorada: numero_nf IN numeros_nf, origem='CARVIA', entregue=False.
"""


def propagar_cidade_uf_carvia(numeros_nf, cot_ids, cidade, uf):
    numeros_nf = [n for n in (numeros_nf or []) if n]
    cot_ids = [c for c in (cot_ids or []) if c]
    if (not numeros_nf and not cot_ids) or (cidade is None and uf is None):
        return {'embarque_itens': 0, 'entregas': 0}

    from app import db
    from app.embarques.models import EmbarqueItem
    from app.monitoramento.models import EntregaMonitorada

    valores = {}
    if cidade is not None:
        valores['cidade_destino'] = cidade
    if uf is not None:
        valores['uf_destino'] = uf

    cond_match = []
    if numeros_nf:
        cond_match.append(EmbarqueItem.nota_fiscal.in_(numeros_nf))
    if cot_ids:
        cond_match.append(EmbarqueItem.carvia_cotacao_id.in_(cot_ids))

    n_itens = (
        EmbarqueItem.query
        .filter(
            EmbarqueItem.separacao_lote_id.ilike('CARVIA-%'),
            db.or_(*cond_match),
            EmbarqueItem.status == 'ativo',
        )
        .update(valores, synchronize_session=False)
    )

    n_entregas = 0
    if numeros_nf:
        valores_e = {}
        if cidade is not None:
            valores_e['municipio'] = cidade
        if uf is not None:
            valores_e['uf'] = uf
        n_entregas = (
            EntregaMonitorada.query
            .filter(
                EntregaMonitorada.numero_nf.in_(numeros_nf),
                EntregaMonitorada.origem == 'CARVIA',
                EntregaMonitorada.entregue.is_(False),
            )
            .update(valores_e, synchronize_session=False)
        )

    return {'embarque_itens': n_itens, 'entregas': n_entregas}
```

> Nota ao implementador: confirme os nomes de coluna `EmbarqueItem.status`/`cliente`/`pedido` no model `app/embarques/models.py:400` ao montar o helper de teste; ajuste apenas o helper de teste se algum campo NOT NULL exigir valor. O corpo do helper só usa `nota_fiscal`, `separacao_lote_id`, `carvia_cotacao_id`, `status`, `cidade_destino`, `uf_destino` (confirmados em `app/embarques/models.py:439-476`).

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/carvia/test_propagacao_endereco.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add app/utils/propagacao_endereco_carvia.py tests/carvia/test_propagacao_endereco.py
git commit -m "feat(carvia): helper R1-safe propaga cidade/UF p/ embarque+entrega"
```

---

### Task A2: Service de propagação (resolve cotação/NF/operação CarVia)

**Files:**
- Create: `app/carvia/services/clientes/propagacao_endereco_service.py`
- Test: `tests/carvia/test_propagacao_endereco.py` (adiciona casos)

**Interfaces:**
- Consumes: `propagar_cidade_uf_carvia(...)` da Task A1.
- Produces: `CarviaPropagacaoEnderecoService.propagar(endereco_id: int) -> dict` retornando `{'cotacoes', 'nfs', 'operacoes', 'embarque_itens', 'entregas'}` (ints). NÃO commita.

- [ ] **Step 1: Write the failing test**

```python
# acrescentar em tests/carvia/test_propagacao_endereco.py
def _endereco_destino(cnpj='98765432000155', cidade='Cidade Velha', uf='RJ'):
    from app.carvia.models.clientes import CarviaCliente, CarviaClienteEndereco
    cli = CarviaCliente(nome_comercial='CLI', ativo=True, criado_por='t')
    _db.session.add(cli); _db.session.flush()
    end = CarviaClienteEndereco(
        cliente_id=cli.id, cnpj=cnpj, tipo='DESTINO',
        fisico_cidade=cidade, fisico_uf=uf, criado_por='t',
    )
    _db.session.add(end); _db.session.flush()
    return end


def test_propaga_nf_ativa_por_cnpj(db):
    from app.carvia.models.documentos import CarviaNf
    from app.carvia.services.clientes.propagacao_endereco_service import (
        CarviaPropagacaoEnderecoService,
    )
    end = _endereco_destino(cnpj='11222333000144')
    nf = CarviaNf(numero_nf='900', cnpj_emitente='1', nome_emitente='E',
                  cnpj_destinatario='11222333000144', nome_destinatario='D',
                  cidade_destinatario='Cidade Velha', uf_destinatario='RJ',
                  valor_total=1, tipo_fonte='MANUAL', status='ATIVA', criado_por='t')
    _db.session.add(nf); _db.session.flush()
    end.fisico_cidade = 'Cidade Nova'; end.fisico_uf = 'SP'; _db.session.flush()

    res = CarviaPropagacaoEnderecoService.propagar(end.id)
    db.session.refresh(nf)
    assert nf.cidade_destinatario == 'Cidade Nova'
    assert nf.uf_destinatario == 'SP'
    assert res['nfs'] == 1


def test_endereco_origem_nao_propaga(db):
    from app.carvia.services.clientes.propagacao_endereco_service import (
        CarviaPropagacaoEnderecoService,
    )
    end = _endereco_destino()
    end.tipo = 'ORIGEM'; _db.session.flush()
    res = CarviaPropagacaoEnderecoService.propagar(end.id)
    assert res == {'cotacoes': 0, 'nfs': 0, 'operacoes': 0, 'embarque_itens': 0, 'entregas': 0}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/carvia/test_propagacao_endereco.py -v`
Expected: FAIL com `ModuleNotFoundError: ...propagacao_endereco_service`

- [ ] **Step 3: Write minimal implementation**

```python
# app/carvia/services/clientes/propagacao_endereco_service.py
"""Propaga cidade/UF de um CarviaClienteEndereco (tipo DESTINO) para os
registros CarVia EM ABERTO vinculados, mais EmbarqueItem/EntregaMonitorada
(via helper R1-safe). Disparado ao editar o endereço (cliente_service).

Vínculos (ver docs/superpowers/specs/2026-06-23-carvia-propagacao-endereco-cce-design.md):
- CarviaCotacao: FK endereco_destino_id; atualiza override entrega_cidade/uf
  SÓ se já preenchidos (senão a FK já reflete o endereço novo).
- CarviaNf / CarviaOperacao: match por CNPJ (sem FK), status ATIVA / RASCUNHO.
- EmbarqueItem / EntregaMonitorada: via helper app/utils (R1).

NÃO commita (caller commita). Só escreve onde o valor difere.
"""
import logging

from app import db

logger = logging.getLogger(__name__)


class CarviaPropagacaoEnderecoService:

    @staticmethod
    def propagar(endereco_id):
        from app.carvia.models import (
            CarviaClienteEndereco, CarviaCotacao, CarviaNf, CarviaOperacao,
        )
        res = {'cotacoes': 0, 'nfs': 0, 'operacoes': 0,
               'embarque_itens': 0, 'entregas': 0}

        end = db.session.get(CarviaClienteEndereco, endereco_id)
        if not end or end.tipo != 'DESTINO':
            return res

        cidade = end.fisico_cidade
        uf = end.fisico_uf
        cnpj = end.cnpj

        # 1. Cotações (FK precisa) — override entrega_* só se já preenchido
        cot_ids = []
        cotacoes = CarviaCotacao.query.filter(
            CarviaCotacao.endereco_destino_id == endereco_id,
            CarviaCotacao.status.notin_(['RECUSADO', 'CANCELADO']),
        ).all()
        for cot in cotacoes:
            cot_ids.append(cot.id)
            mudou = False
            if cot.entrega_cidade and cot.entrega_cidade != cidade:
                cot.entrega_cidade = cidade
                mudou = True
            if cot.entrega_uf and cot.entrega_uf != uf:
                cot.entrega_uf = uf
                mudou = True
            if mudou:
                res['cotacoes'] += 1

        numeros_nf = []
        if cnpj:
            # 2. NFs ATIVAS do CNPJ
            for nf in CarviaNf.query.filter(
                CarviaNf.cnpj_destinatario == cnpj,
                CarviaNf.status == 'ATIVA',
            ).all():
                if nf.numero_nf:
                    numeros_nf.append(nf.numero_nf)
                mudou = False
                if nf.cidade_destinatario != cidade:
                    nf.cidade_destinatario = cidade
                    mudou = True
                if nf.uf_destinatario != uf:
                    nf.uf_destinatario = uf
                    mudou = True
                if mudou:
                    res['nfs'] += 1

            # 3. Operações (CTe) RASCUNHO do CNPJ
            for op in CarviaOperacao.query.filter(
                CarviaOperacao.cnpj_cliente == cnpj,
                CarviaOperacao.status == 'RASCUNHO',
            ).all():
                mudou = False
                if op.cidade_destino != cidade:
                    op.cidade_destino = cidade
                    mudou = True
                if op.uf_destino != uf:
                    op.uf_destino = uf
                    mudou = True
                if mudou:
                    res['operacoes'] += 1

        # 4/5. EmbarqueItem + EntregaMonitorada (helper R1-safe, lazy import)
        from app.utils.propagacao_endereco_carvia import propagar_cidade_uf_carvia
        externos = propagar_cidade_uf_carvia(numeros_nf, cot_ids, cidade, uf)
        res['embarque_itens'] = externos['embarque_itens']
        res['entregas'] = externos['entregas']

        db.session.flush()
        logger.info("Propagacao endereco #%s: %s", endereco_id, res)
        return res
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/carvia/test_propagacao_endereco.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add app/carvia/services/clientes/propagacao_endereco_service.py tests/carvia/test_propagacao_endereco.py
git commit -m "feat(carvia): service propaga cidade/UF do endereco p/ cotacao/NF/operacao em aberto"
```

---

### Task A3: Hook no atualizar_endereco + contagem na resposta da API

**Files:**
- Modify: `app/carvia/services/clientes/cliente_service.py:546-660` (`atualizar_endereco`)
- Modify: `app/carvia/routes/cliente_routes.py:237-270` (`api_atualizar_endereco`)
- Test: `tests/carvia/test_propagacao_endereco.py` (caso de integração via service)

**Interfaces:**
- Consumes: `CarviaPropagacaoEnderecoService.propagar` (Task A2).
- Produces: `atualizar_endereco` retorna `(True, None, {'propagacao': {...}})` quando cidade/UF mudaram; a rota inclui `propagacao` no JSON.

- [ ] **Step 1: Write the failing test**

```python
# acrescentar em tests/carvia/test_propagacao_endereco.py
def test_atualizar_endereco_dispara_propagacao(db):
    from app.carvia.models.documentos import CarviaNf
    from app.carvia.services.clientes.cliente_service import CarviaClienteService
    end = _endereco_destino(cnpj='55666777000188', cidade='Velha', uf='RJ')
    nf = CarviaNf(numero_nf='950', cnpj_emitente='1', nome_emitente='E',
                  cnpj_destinatario='55666777000188', nome_destinatario='D',
                  cidade_destinatario='Velha', uf_destinatario='RJ',
                  valor_total=1, tipo_fonte='MANUAL', status='ATIVA', criado_por='t')
    _db.session.add(nf); _db.session.flush()

    ok, erro, ctx = CarviaClienteService.atualizar_endereco(
        end.id, {'fisico_cidade': 'Nova', 'fisico_uf': 'SP'})
    assert ok and erro is None
    assert ctx and ctx.get('propagacao', {}).get('nfs') == 1
    db.session.refresh(nf)
    assert nf.cidade_destinatario == 'Nova'


def test_atualizar_endereco_sem_mudar_cidade_uf_nao_propaga(db):
    from app.carvia.services.clientes.cliente_service import CarviaClienteService
    end = _endereco_destino(cnpj='10101010000110', cidade='Velha', uf='RJ')
    ok, erro, ctx = CarviaClienteService.atualizar_endereco(
        end.id, {'razao_social': 'Outra Razao'})
    assert ok
    assert (ctx or {}).get('propagacao') is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/carvia/test_propagacao_endereco.py -v`
Expected: FAIL — `ctx` é `None` (hoje retorna `(True, None, None)`).

- [ ] **Step 3: Modify `atualizar_endereco`**

No início do método (após `endereco = db.session.get(...)` e o guard de não-encontrado, ~linha 570), capture o valor antigo:

```python
        cidade_uf_antes = (endereco.fisico_cidade, endereco.fisico_uf)
```

Substitua o `return` final (linhas 659-660):

```python
        db.session.flush()
        return True, None, None
```

por:

```python
        db.session.flush()

        # Propaga cidade/UF para os registros em aberto, se mudaram (DESTINO).
        contexto_saida = None
        cidade_uf_depois = (endereco.fisico_cidade, endereco.fisico_uf)
        if endereco.tipo == 'DESTINO' and cidade_uf_depois != cidade_uf_antes:
            from app.carvia.services.clientes.propagacao_endereco_service import (
                CarviaPropagacaoEnderecoService,
            )
            propagacao = CarviaPropagacaoEnderecoService.propagar(endereco.id)
            if any(propagacao.values()):
                contexto_saida = {'propagacao': propagacao}
        return True, None, contexto_saida
```

- [ ] **Step 4: Modify a rota `api_atualizar_endereco`**

Em `cliente_routes.py`, troque o bloco de sucesso (linhas 269-270):

```python
            db.session.commit()
            return jsonify({'sucesso': True, 'mensagem': 'Endereco atualizado.'})
```

por:

```python
            db.session.commit()
            resposta = {'sucesso': True, 'mensagem': 'Endereco atualizado.'}
            if contexto and contexto.get('propagacao'):
                p = contexto['propagacao']
                resposta['propagacao'] = p
                resposta['mensagem'] = (
                    'Endereco atualizado. Propagado para '
                    f"{p['nfs']} NF(s), {p['operacoes']} CTe(s), "
                    f"{p['cotacoes']} cotacao(oes), {p['embarque_itens']} embarque(s), "
                    f"{p['entregas']} entrega(s)."
                )
            return jsonify(resposta)
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/carvia/test_propagacao_endereco.py -v`
Expected: PASS (6 passed)

- [ ] **Step 6: Commit**

```bash
git add app/carvia/services/clientes/cliente_service.py app/carvia/routes/cliente_routes.py tests/carvia/test_propagacao_endereco.py
git commit -m "feat(carvia): editar endereco propaga cidade/UF + retorna contagem na API"
```

---

## FASE B — Modelo CCe (cadeia compartilhada) + anexo

### Task B1: Extrair lógica de cadeia para módulo compartilhado

**Files:**
- Create: `app/carvia/services/documentos/_cadeia_nf.py`
- Modify: `app/carvia/services/documentos/comprovante_service.py:116-195` (passa a delegar)
- Test: `tests/carvia/test_cadeia_nf.py`

**Interfaces:**
- Produces: `resolver_cadeia_nf(entidade_tipo: str, entidade_id: int) -> set[tuple[str, int]]` — fecho da cadeia (cotacao/nf/operacao/fatura_cliente). Lógica idêntica à de `CarviaComprovanteService._entidades_relacionadas`.

- [ ] **Step 1: Write the failing test (regressão = mesma saída do comprovante)**

```python
# tests/carvia/test_cadeia_nf.py
from app import db as _db
from app.carvia.services.documentos._cadeia_nf import resolver_cadeia_nf
from app.carvia.services.documentos.comprovante_service import CarviaComprovanteService


def test_cadeia_de_nf_inclui_ela_mesma(db):
    from app.carvia.models.documentos import CarviaNf
    nf = CarviaNf(numero_nf='700', cnpj_emitente='1', nome_emitente='E',
                  cnpj_destinatario='2', nome_destinatario='D',
                  cidade_destinatario='C', uf_destinatario='SP',
                  valor_total=1, tipo_fonte='MANUAL', status='ATIVA', criado_por='t')
    _db.session.add(nf); _db.session.flush()
    fecho = resolver_cadeia_nf('nf', nf.id)
    assert ('nf', nf.id) in fecho


def test_extracao_identica_ao_metodo_antigo(db):
    from app.carvia.models.documentos import CarviaNf
    nf = CarviaNf(numero_nf='701', cnpj_emitente='1', nome_emitente='E',
                  cnpj_destinatario='2', nome_destinatario='D',
                  cidade_destinatario='C', uf_destinatario='SP',
                  valor_total=1, tipo_fonte='MANUAL', status='ATIVA', criado_por='t')
    _db.session.add(nf); _db.session.flush()
    assert (resolver_cadeia_nf('nf', nf.id)
            == CarviaComprovanteService._entidades_relacionadas('nf', nf.id))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/carvia/test_cadeia_nf.py -v`
Expected: FAIL com `ModuleNotFoundError: ..._cadeia_nf`

- [ ] **Step 3: Create `_cadeia_nf.py`** (copie o corpo de `_entidades_relacionadas`, `comprovante_service.py:116-195`)

```python
# app/carvia/services/documentos/_cadeia_nf.py
"""Fecho da cadeia documental CarVia a partir de uma entidade.

Eixo = NFs. De NFs deriva operações (CarviaOperacaoNf), faturas
(operacao.fatura_cliente_id) e cotações (CarviaPedidoItem.numero_nf, elo
textual). SOT único — consumido por comprovante_service e carta_correcao_service
(evita duplicar a lógica de cadeia em dois lugares).
"""
from app import db


def resolver_cadeia_nf(entidade_tipo, entidade_id):
    """Conjunto de (tipo, id) no fecho da cadeia ligado a esta entidade.
    Inclui a própria entidade de origem."""
    from app.carvia.models import (
        CarviaNf, CarviaOperacao, CarviaOperacaoNf,
        CarviaPedido, CarviaPedidoItem,
    )
    rel = {(entidade_tipo, entidade_id)}

    nf_ids = set()
    if entidade_tipo == 'nf':
        nf_ids.add(entidade_id)
    elif entidade_tipo == 'operacao':
        nf_ids.update(
            r.nf_id for r in
            CarviaOperacaoNf.query.filter_by(operacao_id=entidade_id).all()
        )
    elif entidade_tipo == 'fatura_cliente':
        op_ids = [
            o.id for o in
            CarviaOperacao.query.filter_by(fatura_cliente_id=entidade_id).all()
        ]
        if op_ids:
            nf_ids.update(
                r.nf_id for r in CarviaOperacaoNf.query.filter(
                    CarviaOperacaoNf.operacao_id.in_(op_ids)
                ).all()
            )
    elif entidade_tipo == 'cotacao':
        numeros = [
            i.numero_nf
            for p in CarviaPedido.query.filter_by(cotacao_id=entidade_id).all()
            for i in p.itens if i.numero_nf
        ]
        if numeros:
            nf_ids.update(
                nf.id for nf in
                CarviaNf.query.filter(CarviaNf.numero_nf.in_(numeros)).all()
            )

    if not nf_ids:
        return rel

    numeros_nf = set()
    for nf in CarviaNf.query.filter(CarviaNf.id.in_(nf_ids)).all():
        rel.add(('nf', nf.id))
        if nf.numero_nf:
            numeros_nf.add(nf.numero_nf)

    op_ids = set()
    for r in CarviaOperacaoNf.query.filter(CarviaOperacaoNf.nf_id.in_(nf_ids)).all():
        rel.add(('operacao', r.operacao_id))
        op_ids.add(r.operacao_id)

    if op_ids:
        for op in CarviaOperacao.query.filter(CarviaOperacao.id.in_(op_ids)).all():
            if op.fatura_cliente_id:
                rel.add(('fatura_cliente', op.fatura_cliente_id))

    if numeros_nf:
        rows = db.session.query(CarviaPedido.cotacao_id).join(
            CarviaPedidoItem, CarviaPedidoItem.pedido_id == CarviaPedido.id
        ).filter(
            CarviaPedidoItem.numero_nf.in_(list(numeros_nf))
        ).distinct().all()
        for (cot_id,) in rows:
            if cot_id:
                rel.add(('cotacao', cot_id))

    return rel
```

- [ ] **Step 4: Delegate from `comprovante_service.py`**

Substitua todo o corpo de `_entidades_relacionadas` (linhas 117-195) por delegação:

```python
    @staticmethod
    def _entidades_relacionadas(entidade_tipo, entidade_id):
        """Fecho da cadeia (delegado ao SOT compartilhado)."""
        from app.carvia.services.documentos._cadeia_nf import resolver_cadeia_nf
        return resolver_cadeia_nf(entidade_tipo, entidade_id)
```

- [ ] **Step 5: Run tests (novo + regressão do comprovante)**

Run: `pytest tests/carvia/test_cadeia_nf.py -v && pytest tests/carvia/ -k comprovante -v`
Expected: PASS — incluindo os testes de comprovante existentes (regressão verde).

- [ ] **Step 6: Commit**

```bash
git add app/carvia/services/documentos/_cadeia_nf.py app/carvia/services/documentos/comprovante_service.py tests/carvia/test_cadeia_nf.py
git commit -m "refactor(carvia): extrai resolver_cadeia_nf p/ SOT compartilhado (comprovante delega)"
```

---

### Task B2: Models CarviaCartaCorrecao + Vinculo + migration + registro

**Files:**
- Create: `app/carvia/models/carta_correcao.py`
- Modify: `app/carvia/models/__init__.py` (registrar import + `__all__`)
- Create: `migrations/versions/<rev>_carvia_cce.py`
- Test: `tests/carvia/test_carta_correcao_model.py`

**Interfaces:**
- Produces: `CarviaCartaCorrecao` (tabela `carvia_cartas_correcao`) + `CarviaCartaCorrecaoVinculo` (tabela `carvia_carta_correcao_vinculos`, `ENTIDADES_VALIDAS = {'cotacao', 'nf'}`, `ORIGEM_MANUAL`/`ORIGEM_PROPAGADO`).

- [ ] **Step 1: Write the failing test**

```python
# tests/carvia/test_carta_correcao_model.py
from app import db as _db


def test_cria_carta_e_vinculo(db):
    from app.carvia.models import CarviaCartaCorrecao, CarviaCartaCorrecaoVinculo
    carta = CarviaCartaCorrecao(
        nome_original='cce.pdf', nome_arquivo='abc_cce.pdf',
        caminho_s3='carvia/cartas_correcao/abc_cce.pdf',
        content_type='application/pdf', criado_por='t')
    _db.session.add(carta); _db.session.flush()
    v = CarviaCartaCorrecaoVinculo(
        carta_id=carta.id, entidade_tipo='nf', entidade_id=10,
        origem=CarviaCartaCorrecaoVinculo.ORIGEM_MANUAL, criado_por='t')
    _db.session.add(v); _db.session.flush()
    assert carta.id and v.id
    assert 'nf' in CarviaCartaCorrecaoVinculo.ENTIDADES_VALIDAS
    assert 'cotacao' in CarviaCartaCorrecaoVinculo.ENTIDADES_VALIDAS
    assert carta.ativo is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/carvia/test_carta_correcao_model.py -v`
Expected: FAIL com `ImportError: cannot import name 'CarviaCartaCorrecao'`

- [ ] **Step 3: Create the models**

```python
# app/carvia/models/carta_correcao.py
"""Carta de Correção (CCe) CarVia — anexo de documento (PDF/imagem).

Espelha o padrão Comprovante (N:N polimórfico): o arquivo vive UMA vez no S3;
os vínculos o tornam visível na cadeia cotacao <-> nf. Anexar na NF propaga
para a cotação vinculada e vice-versa (sincronizar_cadeia, eixo = NFs).

Model ENXUTO (decisão de design): arquivo + descrição. SEM campos fiscais —
o audit textual de campos do CTe já vive em CarviaEnderecoCorrecao (separado).
Soft-delete via `ativo` (GAP-20).
"""
from app import db
from app.utils.timezone import agora_utc_naive


class CarviaCartaCorrecao(db.Model):
    """Carta de Correção (arquivo S3) — N:N com cotacao/nf via vínculo."""
    __tablename__ = 'carvia_cartas_correcao'

    id = db.Column(db.Integer, primary_key=True)
    nome_original = db.Column(db.String(255), nullable=False)
    nome_arquivo = db.Column(db.String(255), nullable=False)
    caminho_s3 = db.Column(db.String(500), nullable=False)
    tamanho_bytes = db.Column(db.Integer, nullable=True)
    content_type = db.Column(db.String(100), nullable=True)
    descricao = db.Column(db.Text, nullable=True)

    ativo = db.Column(db.Boolean, nullable=False, default=True, index=True)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    vinculos = db.relationship(
        'CarviaCartaCorrecaoVinculo',
        back_populates='carta',
        cascade='all, delete-orphan',
    )

    def __repr__(self):
        return f'<CarviaCartaCorrecao {self.id} {self.nome_original} ativo={self.ativo}>'


class CarviaCartaCorrecaoVinculo(db.Model):
    """Vínculo N:N polimórfico entre CCe e documento (cotacao/nf)."""
    __tablename__ = 'carvia_carta_correcao_vinculos'

    ENTIDADE_COTACAO = 'cotacao'
    ENTIDADE_NF = 'nf'
    ENTIDADES_VALIDAS = frozenset({ENTIDADE_COTACAO, ENTIDADE_NF})

    ORIGEM_MANUAL = 'MANUAL'
    ORIGEM_PROPAGADO = 'PROPAGADO'

    id = db.Column(db.Integer, primary_key=True)
    carta_id = db.Column(
        db.Integer,
        db.ForeignKey('carvia_cartas_correcao.id', ondelete='CASCADE'),
        nullable=False, index=True,
    )
    entidade_tipo = db.Column(db.String(30), nullable=False)
    entidade_id = db.Column(db.Integer, nullable=False)
    origem = db.Column(db.String(20), nullable=False, default=ORIGEM_MANUAL)
    criado_em = db.Column(db.DateTime, nullable=False, default=agora_utc_naive)
    criado_por = db.Column(db.String(100), nullable=False)

    carta = db.relationship('CarviaCartaCorrecao', back_populates='vinculos')

    __table_args__ = (
        db.UniqueConstraint(
            'carta_id', 'entidade_tipo', 'entidade_id',
            name='uq_carvia_cce_vinculo',
        ),
        db.Index(
            'ix_carvia_cce_vinculo_entidade', 'entidade_tipo', 'entidade_id',
        ),
    )

    def __repr__(self):
        return (f'<CarviaCartaCorrecaoVinculo {self.id} carta#{self.carta_id} '
                f'{self.entidade_tipo}#{self.entidade_id} {self.origem}>')
```

- [ ] **Step 4: Register in `models/__init__.py`**

Após o bloco de Comprovantes (linha 88), adicione:

```python
# Carta de Correção (CCe) — N:N com cotacao / NF
from app.carvia.models.carta_correcao import (  # noqa: F401
    CarviaCartaCorrecao, CarviaCartaCorrecaoVinculo,
)
```

E em `__all__` (após `'CarviaComprovanteVinculo',`):

```python
    # Carta de Correção (CCe)
    'CarviaCartaCorrecao', 'CarviaCartaCorrecaoVinculo',
```

- [ ] **Step 5: Generate the migration**

Run: `flask db migrate -m "carvia cce: cartas_correcao + vinculos"`
Then OPEN the generated file and verify `upgrade()` creates both tables (FK CASCADE, UNIQUE `uq_carvia_cce_vinculo`, index `ix_carvia_cce_vinculo_entidade`) and `downgrade()` drops `carvia_carta_correcao_vinculos` BEFORE `carvia_cartas_correcao`. Edit if autogenerate missed the index/constraint names.

- [ ] **Step 6: Apply migration + run tests**

Run: `flask db upgrade && pytest tests/carvia/test_carta_correcao_model.py -v`
Expected: PASS (1 passed)

- [ ] **Step 7: Commit**

```bash
git add app/carvia/models/carta_correcao.py app/carvia/models/__init__.py migrations/versions/*carvia_cce*.py tests/carvia/test_carta_correcao_model.py
git commit -m "feat(carvia): models CarviaCartaCorrecao + Vinculo (CCe) + migration"
```

---

### Task B3: Service CarviaCartaCorrecaoService

**Files:**
- Create: `app/carvia/services/documentos/carta_correcao_service.py`
- Modify: `app/carvia/utils/upload_policies.py` (adiciona `ALLOWED_EXT_CCE`)
- Test: `tests/carvia/test_carta_correcao_service.py`

**Interfaces:**
- Consumes: `resolver_cadeia_nf` (B1); models (B2); `get_file_storage`; `ALLOWED_EXT_CCE`/`MAX_BYTES_ANEXO`/`UPLOAD_MAX_MB_ANEXO` (upload_policies).
- Produces: `CarviaCartaCorrecaoService` com `validar_entidade`, `sincronizar_cadeia`, `criar`, `listar`, `tem_cce_batch`, `soft_delete`, `download_url`.

- [ ] **Step 1: Add `ALLOWED_EXT_CCE` to upload_policies**

Em `app/carvia/utils/upload_policies.py`, após `ALLOWED_EXT_ANEXO` (linha 31):

```python
# Carta de Correção (CCe) — PDF ou imagem (renderizável p/ impressão)
ALLOWED_EXT_CCE: frozenset[str] = frozenset({'pdf', 'jpg', 'jpeg', 'png'})
```

- [ ] **Step 2: Write the failing test**

```python
# tests/carvia/test_carta_correcao_service.py
import io
import pytest
from app import db as _db
from werkzeug.datastructures import FileStorage
from app.carvia.services.documentos.carta_correcao_service import CarviaCartaCorrecaoService


def _fake_pdf():
    return FileStorage(stream=io.BytesIO(b'%PDF-1.4 fake'),
                       filename='cce.pdf', content_type='application/pdf')


def _nf(numero='800'):
    from app.carvia.models.documentos import CarviaNf
    nf = CarviaNf(numero_nf=numero, cnpj_emitente='1', nome_emitente='E',
                  cnpj_destinatario='2', nome_destinatario='D',
                  cidade_destinatario='C', uf_destinatario='SP',
                  valor_total=1, tipo_fonte='MANUAL', status='ATIVA', criado_por='t')
    _db.session.add(nf); _db.session.flush()
    return nf


def test_criar_e_listar_cce_na_nf(db):
    nf = _nf()
    carta = CarviaCartaCorrecaoService.criar('nf', nf.id, _fake_pdf(), 'user@bot',
                                             descricao='corrige endereco')
    _db.session.commit()
    assert carta.id
    pares = CarviaCartaCorrecaoService.listar('nf', nf.id)
    assert len(pares) == 1
    assert pares[0][0].descricao == 'corrige endereco'


def test_entidade_invalida_levanta(db):
    with pytest.raises(ValueError):
        CarviaCartaCorrecaoService.criar('operacao', 1, _fake_pdf(), 'u')


def test_soft_delete(db):
    nf = _nf('801')
    carta = CarviaCartaCorrecaoService.criar('nf', nf.id, _fake_pdf(), 'u')
    _db.session.commit()
    CarviaCartaCorrecaoService.soft_delete(carta.id)
    _db.session.commit()
    assert CarviaCartaCorrecaoService.listar('nf', nf.id) == []
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest tests/carvia/test_carta_correcao_service.py -v`
Expected: FAIL com `ModuleNotFoundError: ...carta_correcao_service`

- [ ] **Step 4: Write the service**

```python
# app/carvia/services/documentos/carta_correcao_service.py
"""Service de Carta de Correção (CCe) CarVia.

Upload/listagem/exclusão/download + propagação pela cadeia cotacao <-> nf.
Espelha CarviaComprovanteService, porém ENXUTO (sem campos financeiros) e
restrito às entidades {cotacao, nf}. Métodos de escrita fazem flush, NÃO commitam.
"""
import logging
import os

from app import db
from app.carvia.utils.upload_policies import (
    ALLOWED_EXT_CCE, MAX_BYTES_ANEXO, UPLOAD_MAX_MB_ANEXO,
    is_extensao_permitida, mensagem_erro_extensao, mensagem_erro_tamanho,
)

logger = logging.getLogger(__name__)


def _resolver_modelo(entidade_tipo):
    if entidade_tipo == 'cotacao':
        from app.carvia.models import CarviaCotacao
        return CarviaCotacao
    if entidade_tipo == 'nf':
        from app.carvia.models import CarviaNf
        return CarviaNf
    return None


class CarviaCartaCorrecaoService:

    @staticmethod
    def validar_entidade(entidade_tipo, entidade_id):
        from app.carvia.models import CarviaCartaCorrecaoVinculo
        if entidade_tipo not in CarviaCartaCorrecaoVinculo.ENTIDADES_VALIDAS:
            raise ValueError(
                f"Tipo de entidade invalido: '{entidade_tipo}'. "
                f"Validos: {', '.join(sorted(CarviaCartaCorrecaoVinculo.ENTIDADES_VALIDAS))}."
            )
        modelo = _resolver_modelo(entidade_tipo)
        obj = db.session.get(modelo, entidade_id)
        if not obj:
            raise ValueError(f"{entidade_tipo} #{entidade_id} nao encontrado.")
        return obj

    @staticmethod
    def sincronizar_cadeia(entidade_tipo, entidade_id, criado_por='sistema'):
        """Vincula toda CCe ativa do fecho da cadeia a TODAS as entidades
        cotacao/nf do fecho. Idempotente. NÃO commita. Retorna nº de vínculos criados."""
        from app.carvia.models import CarviaCartaCorrecao, CarviaCartaCorrecaoVinculo
        from app.carvia.services.documentos._cadeia_nf import resolver_cadeia_nf

        rel = resolver_cadeia_nf(entidade_tipo, entidade_id)
        pairs = [(t, i) for (t, i) in rel if t in ('cotacao', 'nf')]
        if not pairs:
            return 0

        cond = db.or_(*[
            db.and_(
                CarviaCartaCorrecaoVinculo.entidade_tipo == t,
                CarviaCartaCorrecaoVinculo.entidade_id == i,
            ) for (t, i) in pairs
        ])
        existentes = CarviaCartaCorrecaoVinculo.query.filter(cond).all()
        existentes_set = {(v.carta_id, v.entidade_tipo, v.entidade_id) for v in existentes}
        carta_ids = {v.carta_id for v in existentes}
        if not carta_ids:
            return 0

        ativos = {
            c.id for c in CarviaCartaCorrecao.query.filter(
                CarviaCartaCorrecao.id.in_(carta_ids),
                CarviaCartaCorrecao.ativo.is_(True),
            ).all()
        }
        criados = 0
        for carta_id in ativos:
            for (t, i) in pairs:
                if (carta_id, t, i) not in existentes_set:
                    db.session.add(CarviaCartaCorrecaoVinculo(
                        carta_id=carta_id, entidade_tipo=t, entidade_id=i,
                        origem=CarviaCartaCorrecaoVinculo.ORIGEM_PROPAGADO,
                        criado_por=criado_por,
                    ))
                    criados += 1
        if criados:
            db.session.flush()
        return criados

    @staticmethod
    def criar(entidade_tipo, entidade_id, file, usuario, descricao=None):
        from app.carvia.models import CarviaCartaCorrecao, CarviaCartaCorrecaoVinculo

        CarviaCartaCorrecaoService.validar_entidade(entidade_tipo, entidade_id)

        if not file or not file.filename:
            raise ValueError('Nenhum arquivo enviado.')
        if not is_extensao_permitida(file.filename, ALLOWED_EXT_CCE):
            raise ValueError(mensagem_erro_extensao(ALLOWED_EXT_CCE))

        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > MAX_BYTES_ANEXO:
            raise ValueError(mensagem_erro_tamanho(UPLOAD_MAX_MB_ANEXO))

        from app.utils.file_storage import get_file_storage
        storage = get_file_storage()
        caminho = storage.save_file(file, folder='carvia/cartas_correcao')
        if not caminho:
            raise ValueError('Falha ao salvar arquivo no storage.')

        carta = CarviaCartaCorrecao(
            nome_original=file.filename,
            nome_arquivo=os.path.basename(caminho),
            caminho_s3=caminho,
            tamanho_bytes=size,
            content_type=file.content_type,
            descricao=(descricao or '').strip() or None,
            criado_por=usuario,
        )
        db.session.add(carta)
        db.session.flush()

        db.session.add(CarviaCartaCorrecaoVinculo(
            carta_id=carta.id, entidade_tipo=entidade_tipo, entidade_id=entidade_id,
            origem=CarviaCartaCorrecaoVinculo.ORIGEM_MANUAL, criado_por=usuario,
        ))
        db.session.flush()

        CarviaCartaCorrecaoService.sincronizar_cadeia(
            entidade_tipo, entidade_id, criado_por=usuario)
        logger.info("CarviaCartaCorrecao #%s criada para %s#%s por %s",
                    carta.id, entidade_tipo, entidade_id, usuario)
        return carta

    @staticmethod
    def listar(entidade_tipo, entidade_id):
        from app.carvia.models import CarviaCartaCorrecao, CarviaCartaCorrecaoVinculo
        return db.session.query(
            CarviaCartaCorrecao, CarviaCartaCorrecaoVinculo,
        ).join(
            CarviaCartaCorrecaoVinculo,
            CarviaCartaCorrecaoVinculo.carta_id == CarviaCartaCorrecao.id,
        ).filter(
            CarviaCartaCorrecaoVinculo.entidade_tipo == entidade_tipo,
            CarviaCartaCorrecaoVinculo.entidade_id == entidade_id,
            CarviaCartaCorrecao.ativo.is_(True),
        ).order_by(CarviaCartaCorrecao.criado_em.desc()).all()

    @staticmethod
    def tem_cce_batch(entidade_tipo, entidade_ids):
        from app.carvia.models import CarviaCartaCorrecao, CarviaCartaCorrecaoVinculo
        ids = [i for i in (entidade_ids or []) if i is not None]
        if not ids:
            return {}
        rows = db.session.query(CarviaCartaCorrecaoVinculo.entidade_id).join(
            CarviaCartaCorrecao,
            CarviaCartaCorrecao.id == CarviaCartaCorrecaoVinculo.carta_id,
        ).filter(
            CarviaCartaCorrecaoVinculo.entidade_tipo == entidade_tipo,
            CarviaCartaCorrecaoVinculo.entidade_id.in_(ids),
            CarviaCartaCorrecao.ativo.is_(True),
        ).distinct().all()
        com = {r[0] for r in rows}
        return {i: (i in com) for i in ids}

    @staticmethod
    def soft_delete(carta_id):
        from app.carvia.models import CarviaCartaCorrecao
        carta = db.session.get(CarviaCartaCorrecao, carta_id)
        if not carta:
            return None
        carta.ativo = False
        db.session.flush()
        return carta

    @staticmethod
    def download_url(carta):
        from app.utils.file_storage import get_file_storage
        storage = get_file_storage()
        return (storage.get_download_url(carta.caminho_s3, carta.nome_original)
                or storage.get_file_url(carta.caminho_s3))
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/carvia/test_carta_correcao_service.py -v`
Expected: PASS (3 passed)

- [ ] **Step 6: Commit**

```bash
git add app/carvia/services/documentos/carta_correcao_service.py app/carvia/utils/upload_policies.py tests/carvia/test_carta_correcao_service.py
git commit -m "feat(carvia): CarviaCartaCorrecaoService (CCe N:N cotacao<->nf, cadeia)"
```

---

### Task B4: Rotas de CCe + registro no blueprint

**Files:**
- Create: `app/carvia/routes/carta_correcao_routes.py`
- Modify: `app/carvia/routes/__init__.py:39-76` (import + register)
- Test: `tests/carvia/test_carta_correcao_routes.py`

**Interfaces:**
- Produces: rotas `POST /carvia/api/carta-correcao/<entidade_tipo>/<int:entidade_id>/upload`, `POST /carvia/api/carta-correcao/<int:carta_id>/excluir`, `GET /carvia/api/carta-correcao/<int:carta_id>/download`. Endpoints `carvia.upload_carta_correcao`, `carvia.excluir_carta_correcao`, `carvia.download_carta_correcao`.

- [ ] **Step 1: Write the failing test**

```python
# tests/carvia/test_carta_correcao_routes.py
import io
from app import db as _db


def _login_carvia(client, app):
    """Loga um usuário com sistema_carvia=True. Se o conftest já tiver fixture/
    helper de auth (procure 'login' em tests/conftest.py), prefira-o."""
    from app.auth.models import Usuario  # ajuste o caminho real do model Usuario
    u = Usuario.query.filter_by(email='cce@bot').first()
    if not u:
        u = Usuario(nome='CCe Bot', email='cce@bot', sistema_carvia=True, status='ativo')
        if hasattr(u, 'set_senha'):
            u.set_senha('x')
        _db.session.add(u); _db.session.commit()
    with client.session_transaction() as s:
        s['_user_id'] = str(u.id)
    return u


def test_upload_carta_correcao_na_nf(client, app):
    from app.carvia.models.documentos import CarviaNf
    _login_carvia(client, app)
    nf = CarviaNf(numero_nf='8800', cnpj_emitente='1', nome_emitente='E',
                  cnpj_destinatario='2', nome_destinatario='D',
                  cidade_destinatario='C', uf_destinatario='SP',
                  valor_total=1, tipo_fonte='MANUAL', status='ATIVA', criado_por='t')
    _db.session.add(nf); _db.session.commit()
    data = {'arquivo': (io.BytesIO(b'%PDF-1.4 x'), 'cce.pdf'), 'descricao': 'corr'}
    resp = client.post(f'/carvia/api/carta-correcao/nf/{nf.id}/upload',
                       data=data, content_type='multipart/form-data')
    assert resp.status_code == 200
    assert resp.get_json()['sucesso'] is True
```

> Antes de implementar, procure em `tests/conftest.py` por uma fixture/helper de login (ex.: `auth_client`) e use-o em vez de `_login_carvia` se existir. Confirme o caminho real do model `Usuario`.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/carvia/test_carta_correcao_routes.py -v`
Expected: FAIL — 404 (rota não existe).

- [ ] **Step 3: Write the routes** (espelha `comprovante_routes.py`, sem `marcar-pago`)

```python
# app/carvia/routes/carta_correcao_routes.py
"""Rotas de Carta de Correção (CCe) CarVia (AJAX). Delega ao
CarviaCartaCorrecaoService. Imports do service são LAZY (R2). Upload propaga
pela cadeia cotacao<->nf automaticamente."""
import logging

from flask import request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user

from app import db

logger = logging.getLogger(__name__)


def register_carta_correcao_routes(bp):

    @bp.route('/api/carta-correcao/<entidade_tipo>/<int:entidade_id>/upload',
              methods=['POST'])  # type: ignore
    @login_required
    def upload_carta_correcao(entidade_tipo, entidade_id):  # type: ignore
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403
        from app.carvia.services.documentos.carta_correcao_service import (
            CarviaCartaCorrecaoService,
        )
        file = request.files.get('arquivo')
        try:
            carta = CarviaCartaCorrecaoService.criar(
                entidade_tipo=entidade_tipo, entidade_id=entidade_id,
                file=file, usuario=current_user.email,
                descricao=request.form.get('descricao', ''),
            )
            db.session.commit()
            return jsonify({'sucesso': True, 'carta': {
                'id': carta.id, 'nome_original': carta.nome_original,
                'tamanho_bytes': carta.tamanho_bytes,
                'criado_em': carta.criado_em.isoformat() if carta.criado_em else None,
            }})
        except ValueError as ve:
            db.session.rollback()
            return jsonify({'erro': str(ve)}), 400
        except Exception as e:  # noqa: BLE001
            db.session.rollback()
            logger.error("Erro upload CCe %s#%s: %s", entidade_tipo, entidade_id, e)
            return jsonify({'erro': f'Erro ao salvar arquivo: {e}'}), 500

    @bp.route('/api/carta-correcao/<int:carta_id>/excluir', methods=['POST'])  # type: ignore
    @login_required
    def excluir_carta_correcao(carta_id):  # type: ignore
        if not getattr(current_user, 'sistema_carvia', False):
            return jsonify({'erro': 'Acesso negado.'}), 403
        from app.carvia.services.documentos.carta_correcao_service import (
            CarviaCartaCorrecaoService,
        )
        try:
            carta = CarviaCartaCorrecaoService.soft_delete(carta_id)
            if not carta:
                return jsonify({'erro': 'Carta de correcao nao encontrada.'}), 404
            db.session.commit()
            return jsonify({'sucesso': True})
        except Exception as e:  # noqa: BLE001
            db.session.rollback()
            logger.error("Erro excluir CCe %s: %s", carta_id, e)
            return jsonify({'erro': f'Erro: {e}'}), 500

    @bp.route('/api/carta-correcao/<int:carta_id>/download')  # type: ignore
    @login_required
    def download_carta_correcao(carta_id):  # type: ignore
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('carvia.dashboard'))
        from app.carvia.models import CarviaCartaCorrecao
        from app.carvia.services.documentos.carta_correcao_service import (
            CarviaCartaCorrecaoService,
        )
        carta = db.session.get(CarviaCartaCorrecao, carta_id)
        if not carta or not carta.ativo:
            flash('Carta de correcao nao encontrada.', 'warning')
            return redirect(url_for('carvia.dashboard'))
        try:
            url = CarviaCartaCorrecaoService.download_url(carta)
            if url:
                return redirect(url)
            flash('Nao foi possivel gerar URL de download.', 'warning')
        except Exception as e:  # noqa: BLE001
            logger.error("Erro download CCe %s: %s", carta_id, e)
            flash(f'Erro: {e}', 'danger')
        return redirect(url_for('carvia.dashboard'))
```

- [ ] **Step 4: Register in `routes/__init__.py`**

Após a linha 40 (`from app.carvia.routes.comprovante_routes import register_comprovante_routes`):

```python
    from app.carvia.routes.carta_correcao_routes import register_carta_correcao_routes
```

Após a linha 76 (`register_comprovante_routes(bp)`):

```python
    register_carta_correcao_routes(bp)
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/carvia/test_carta_correcao_routes.py -v`
Expected: PASS (1 passed)

- [ ] **Step 6: Commit**

```bash
git add app/carvia/routes/carta_correcao_routes.py app/carvia/routes/__init__.py tests/carvia/test_carta_correcao_routes.py
git commit -m "feat(carvia): rotas upload/excluir/download da CCe + registro blueprint"
```

---

### Task B5: Card UI + JS + inserção no detalhe da cotação e da NF

**Files:**
- Create: `app/templates/carvia/_cartas_correcao_card.html`
- Create: `app/static/carvia/js/cartas_correcao_widget.js`
- Modify: `app/templates/carvia/cotacoes/detalhe.html` (import macro + render + script)
- Modify: `app/templates/carvia/nfs/detalhe.html` (idem)
- Modify: `app/carvia/routes/cotacao_v2_routes.py` (`detalhe_cotacao_v2`, ~linha 1392): monta `cces_cotacao`
- Modify: `app/carvia/routes/nf_routes.py` (`detalhe_nf`, ~linha 659): monta `cces_nf`

**Interfaces:**
- Consumes: `CarviaCartaCorrecaoService.listar` (B3); rotas (B4).

- [ ] **Step 1: Create the macro** (espelha `_comprovantes_card.html`, sem valor/data/cnpj)

```jinja
{# app/templates/carvia/_cartas_correcao_card.html
   Widget reutilizavel de Cartas de Correcao (CCe) CarVia (N:N cotacao<->nf).
   Uso (topo do template):
     {% from 'carvia/_cartas_correcao_card.html' import cartas_correcao_card with context %}
   Render (cces = lista de pares (carta, vinculo) de CarviaCartaCorrecaoService.listar):
     {{ cartas_correcao_card('Cartas de Correcao (CCe)', cces_nf,
          url_for('carvia.upload_carta_correcao', entidade_tipo='nf', entidade_id=nf.id),
          pode_editar=True) }}
   Requer 1x na pagina:
     <script src="{{ url_for('static', filename='carvia/js/cartas_correcao_widget.js') }}"></script>
#}
{% macro cartas_correcao_card(titulo, cces, upload_url, pode_editar=True) %}
<div class="card mt-3">
    <div class="card-header d-flex justify-content-between align-items-center">
        <h5 class="mb-0"><i class="fas fa-file-signature"></i> {{ titulo }} ({{ cces|length }})</h5>
    </div>
    <div class="card-body">
        {% if cces %}
        <div class="table-responsive">
            <table class="table table-sm table-hover align-middle mb-0">
                <thead><tr>
                    <th>Arquivo</th><th>Origem</th><th class="col-nowrap">Enviado</th>
                    <th class="text-end">Acoes</th>
                </tr></thead>
                <tbody>
                    {% for carta, vinc in cces %}
                    <tr>
                        <td>
                            <strong>{{ carta.nome_original }}</strong>
                            {% if carta.descricao %}<div class="small text-muted">{{ carta.descricao }}</div>{% endif %}
                        </td>
                        <td>
                            {% if vinc.origem == 'PROPAGADO' %}
                            <span class="badge bg-secondary" title="Herdado da cadeia">Propagado</span>
                            {% else %}
                            <span class="badge bg-primary" title="Anexado neste documento">Manual</span>
                            {% endif %}
                        </td>
                        <td class="col-nowrap"><small>{{ carta.criado_em.strftime('%d/%m/%Y %H:%M') if carta.criado_em else '-' }}<br>{{ carta.criado_por or '' }}</small></td>
                        <td class="text-end col-nowrap">
                            <a href="{{ url_for('carvia.download_carta_correcao', carta_id=carta.id) }}"
                               class="btn btn-sm btn-outline-primary" title="Baixar CCe"><i class="fas fa-download"></i></a>
                            {% if pode_editar %}
                            <button type="button" class="btn btn-sm btn-outline-danger carvia-cce-excluir"
                                    data-carta-id="{{ carta.id }}" title="Excluir CCe"><i class="fas fa-trash"></i></button>
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {% else %}
        <p class="text-muted text-center mb-3">Nenhuma carta de correcao.</p>
        {% endif %}

        {% if pode_editar %}
        <hr>
        <form class="carvia-cce-form" enctype="multipart/form-data" data-upload-url="{{ upload_url }}">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <div class="row g-2 align-items-end">
                <div class="col-md-5">
                    <label class="form-label">Carta de Correcao <span class="text-danger">*</span></label>
                    <input type="file" class="form-control form-control-sm" name="arquivo" accept=".pdf,.jpg,.jpeg,.png" required>
                </div>
                <div class="col-md-5">
                    <label class="form-label">Descricao</label>
                    <input type="text" class="form-control form-control-sm" name="descricao" placeholder="Opcional">
                </div>
                <div class="col-md-2">
                    <button type="submit" class="btn btn-sm btn-outline-success w-100" title="Enviar CCe"><i class="fas fa-upload"></i></button>
                </div>
            </div>
            <small class="text-muted">pdf, jpg, jpeg, png (max 10MB). Propaga entre a cotacao e a NF da cadeia.</small>
        </form>
        {% endif %}
    </div>
</div>
{% endmacro %}
```

- [ ] **Step 2: Create the JS widget** (espelha `comprovantes_widget.js`, classes `carvia-cce-*`)

```javascript
/* app/static/carvia/js/cartas_correcao_widget.js
 * Widget de Cartas de Correcao (CCe) CarVia. Delegacao de eventos no document.
 * HTML esperado (carvia/_cartas_correcao_card.html):
 *  - <form class="carvia-cce-form" data-upload-url="..."> com input[name=arquivo]
 *  - <button class="carvia-cce-excluir" data-carta-id="...">
 */
(function () {
    'use strict';
    function getCsrfToken(form) {
        if (form) {
            var input = form.querySelector('input[name="csrf_token"]');
            if (input && input.value) return input.value;
        }
        var meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute('content') : '';
    }

    document.addEventListener('submit', function (e) {
        var form = e.target;
        if (!form || !form.classList || !form.classList.contains('carvia-cce-form')) return;
        e.preventDefault();
        var url = form.getAttribute('data-upload-url');
        if (!url) { alert('URL de upload nao configurada.'); return; }
        var btn = form.querySelector('button[type="submit"]');
        var btnHtml = btn ? btn.innerHTML : '';
        if (btn) { btn.disabled = true; btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i>'; }
        fetch(url, { method: 'POST', body: new FormData(form), headers: { 'X-CSRFToken': getCsrfToken(form) } })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data && data.sucesso) { location.reload(); }
                else { alert((data && data.erro) || 'Erro ao enviar CCe'); if (btn) { btn.disabled = false; btn.innerHTML = btnHtml; } }
            })
            .catch(function () { alert('Erro de conexao ao enviar CCe'); if (btn) { btn.disabled = false; btn.innerHTML = btnHtml; } });
    });

    document.addEventListener('click', function (e) {
        var btn = e.target.closest ? e.target.closest('.carvia-cce-excluir') : null;
        if (!btn) return;
        e.preventDefault();
        var cartaId = btn.getAttribute('data-carta-id');
        if (!cartaId) return;
        if (!confirm('Excluir esta carta de correcao? (sera removida da cotacao e da NF da cadeia)')) return;
        btn.disabled = true;
        fetch('/carvia/api/carta-correcao/' + cartaId + '/excluir', {
            method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': getCsrfToken(null) }
        })
            .then(function (r) { return r.json(); })
            .then(function (data) {
                if (data && data.sucesso) { location.reload(); }
                else { alert((data && data.erro) || 'Erro ao excluir CCe'); btn.disabled = false; }
            })
            .catch(function () { alert('Erro de conexao ao excluir CCe'); btn.disabled = false; });
    });
})();
```

- [ ] **Step 3: Wire into the NF detail route + template**

Em `nf_routes.py`, função `detalhe_nf` (~linha 659), antes do `render_template` (lazy import R2):

```python
        from app.carvia.services.documentos.carta_correcao_service import (
            CarviaCartaCorrecaoService,
        )
        cces_nf = CarviaCartaCorrecaoService.listar('nf', nf.id)
```

e adicione `cces_nf=cces_nf` ao contexto do `render_template`.

Em `app/templates/carvia/nfs/detalhe.html`: no topo (junto à linha 7 do import do comprovante):

```jinja
{% from 'carvia/_cartas_correcao_card.html' import cartas_correcao_card with context %}
```

logo após o bloco do card de comprovantes (~linha 1085):

```jinja
{{ cartas_correcao_card('Cartas de Correcao (CCe)', cces_nf,
     url_for('carvia.upload_carta_correcao', entidade_tipo='nf', entidade_id=nf.id),
     pode_editar=True) }}
```

e no bloco de scripts (junto à linha 1089):

```jinja
<script src="{{ url_for('static', filename='carvia/js/cartas_correcao_widget.js') }}"></script>
```

- [ ] **Step 4: Wire into the cotação detail route + template**

Em `cotacao_v2_routes.py`, função `detalhe_cotacao_v2` (~linha 1392), antes do `render_template`:

```python
        from app.carvia.services.documentos.carta_correcao_service import (
            CarviaCartaCorrecaoService,
        )
        cces_cotacao = CarviaCartaCorrecaoService.listar('cotacao', cotacao.id)
```

e adicione `cces_cotacao=cces_cotacao` ao contexto.

Em `app/templates/carvia/cotacoes/detalhe.html`: import (junto à linha 9):

```jinja
{% from 'carvia/_cartas_correcao_card.html' import cartas_correcao_card with context %}
```

após o card de comprovantes (~linha 848):

```jinja
{{ cartas_correcao_card('Cartas de Correcao (CCe)', cces_cotacao,
     url_for('carvia.upload_carta_correcao', entidade_tipo='cotacao', entidade_id=cotacao.id),
     pode_editar=True) }}
```

e o script (junto à linha 853):

```jinja
<script src="{{ url_for('static', filename='carvia/js/cartas_correcao_widget.js') }}"></script>
```

- [ ] **Step 5: Manual smoke test**

Run: `python run.py` e abra um detalhe de NF e de cotação CarVia; faça upload de um PDF na NF e confirme que aparece também na cotação vinculada (cadeia). Exclua e confirme remoção.
Expected: card "Cartas de Correcao (CCe)" renderiza; upload/download/exclusão funcionam; CCe da NF aparece na cotação da mesma cadeia.

- [ ] **Step 6: Commit**

```bash
git add app/templates/carvia/_cartas_correcao_card.html app/static/carvia/js/cartas_correcao_widget.js app/templates/carvia/nfs/detalhe.html app/templates/carvia/cotacoes/detalhe.html app/carvia/routes/nf_routes.py app/carvia/routes/cotacao_v2_routes.py
git commit -m "feat(carvia): card de CCe (anexo) no detalhe da NF e da cotacao"
```

---

## FASE C — Impressão (PDF→imagem embutida)

### Task C1: Helper de render PDF/imagem → base64

**Files:**
- Create: `app/carvia/services/documentos/cce_render.py`
- Test: `tests/carvia/test_cce_render.py`

**Interfaces:**
- Consumes: `get_file_storage().download_file`; pypdfium2; Pillow.
- Produces: `render_cces_para_impressao(cces) -> list[dict]` onde `cces` é a lista de pares `(carta, vinculo)` (saída de `listar`); cada item: `{'carta_id': int, 'descricao': str|None, 'paginas': list[str]}` (PNG base64, sem prefixo data:). Também expõe `_baixar_bytes(caminho_s3)` (mockável em teste).

- [ ] **Step 1: Write the failing test**

```python
# tests/carvia/test_cce_render.py
import base64


def test_render_imagem_embute_direto(db, monkeypatch):
    from app.carvia.services.documentos import cce_render

    class _Carta:
        id = 1; descricao = 'x'; content_type = 'image/png'
        nome_original = 'cce.png'; caminho_s3 = 'carvia/cartas_correcao/cce.png'

    png_1px = base64.b64decode(
        'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==')
    monkeypatch.setattr(cce_render, '_baixar_bytes', lambda p: png_1px)

    out = cce_render.render_cces_para_impressao([(_Carta(), None)])
    assert len(out) == 1
    assert out[0]['carta_id'] == 1
    assert len(out[0]['paginas']) == 1
    base64.b64decode(out[0]['paginas'][0])  # base64 valido


def test_render_lista_vazia(db):
    from app.carvia.services.documentos import cce_render
    assert cce_render.render_cces_para_impressao([]) == []
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/carvia/test_cce_render.py -v`
Expected: FAIL com `ModuleNotFoundError: ...cce_render`

- [ ] **Step 3: Write the helper**

```python
# app/carvia/services/documentos/cce_render.py
"""Render de Cartas de Correção (CCe) para impressão embutida.

Converte cada CCe (PDF -> imagem por página via pypdfium2; imagem -> embute
direto) em PNG base64, para sair como página(s) no HTML que window.print()
imprime (capa do embarque, detalhe da NF, monitoramento). Padrão pypdfium2
espelha app/financeiro/leitor_comprovantes_sicoob.py:244.
"""
import base64
import io
import logging

logger = logging.getLogger(__name__)

_ESCALA_PDF = 2.5  # nitidez razoavel sem estourar memoria


def _baixar_bytes(caminho_s3):
    from app.utils.file_storage import get_file_storage
    return get_file_storage().download_file(caminho_s3)


def _png_base64(pil_image):
    buf = io.BytesIO()
    pil_image.convert('RGB').save(buf, format='PNG')
    return base64.b64encode(buf.getvalue()).decode('ascii')


def _paginas_de_pdf(pdf_bytes):
    import pypdfium2 as pdfium
    paginas = []
    pdf = pdfium.PdfDocument(pdf_bytes)
    try:
        for i in range(len(pdf)):
            bitmap = pdf[i].render(scale=_ESCALA_PDF)
            paginas.append(_png_base64(bitmap.to_pil()))
    finally:
        pdf.close()
    return paginas


def render_cces_para_impressao(cces):
    """cces = lista de pares (carta, vinculo) (saida de listar). Retorna
    list[{'carta_id', 'descricao', 'paginas': [png_base64,...]}]."""
    from PIL import Image

    resultado = []
    for carta, _vinc in (cces or []):
        try:
            dados = _baixar_bytes(carta.caminho_s3)
            if not dados:
                logger.warning("CCe #%s sem bytes no storage (%s)", carta.id, carta.caminho_s3)
                continue
            ct = (carta.content_type or '').lower()
            nome = (carta.nome_original or '').lower()
            eh_pdf = 'pdf' in ct or nome.endswith('.pdf')
            if eh_pdf:
                paginas = _paginas_de_pdf(dados)
            else:
                paginas = [_png_base64(Image.open(io.BytesIO(dados)))]
            if paginas:
                resultado.append({
                    'carta_id': carta.id,
                    'descricao': carta.descricao,
                    'paginas': paginas,
                })
        except Exception as e:  # noqa: BLE001
            logger.error("Falha ao renderizar CCe #%s: %s", getattr(carta, 'id', '?'), e)
    return resultado
```

- [ ] **Step 4: Run tests**

Run: `pytest tests/carvia/test_cce_render.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add app/carvia/services/documentos/cce_render.py tests/carvia/test_cce_render.py
git commit -m "feat(carvia): render CCe (PDF->imagem via pypdfium2) p/ impressao embutida"
```

---

### Task C2: Rota única de impressão de CCe + template

**Files:**
- Create: `app/templates/carvia/nfs/imprimir_cce.html`
- Modify: `app/carvia/routes/carta_correcao_routes.py` (adiciona rota de impressão)
- Test: `tests/carvia/test_carta_correcao_routes.py` (adiciona caso)

**Interfaces:**
- Consumes: `CarviaCartaCorrecaoService.listar`; `render_cces_para_impressao` (C1).
- Produces: `GET /carvia/cartas-correcao/imprimir?nf_id=<id>` (endpoint `carvia.imprimir_cce`). Retorna HTML que auto-imprime.

- [ ] **Step 1: Write the failing test**

```python
# acrescentar em tests/carvia/test_carta_correcao_routes.py
def test_imprimir_cce_da_nf_retorna_html(client, app):
    from app.carvia.models.documentos import CarviaNf
    _login_carvia(client, app)
    nf = CarviaNf(numero_nf='8801', cnpj_emitente='1', nome_emitente='E',
                  cnpj_destinatario='2', nome_destinatario='D',
                  cidade_destinatario='C', uf_destinatario='SP',
                  valor_total=1, tipo_fonte='MANUAL', status='ATIVA', criado_por='t')
    _db.session.add(nf); _db.session.commit()
    resp = client.get(f'/carvia/cartas-correcao/imprimir?nf_id={nf.id}')
    assert resp.status_code == 200
    assert b'window.print' in resp.data  # sem CCe ainda: pagina vazia mas valida
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/carvia/test_carta_correcao_routes.py::test_imprimir_cce_da_nf_retorna_html -v`
Expected: FAIL — 404.

- [ ] **Step 3: Add the print route** (em `carta_correcao_routes.py`, dentro de `register_carta_correcao_routes`)

```python
    @bp.route('/cartas-correcao/imprimir')  # type: ignore
    @login_required
    def imprimir_cce():  # type: ignore
        """Imprime as CCe de uma NF (?nf_id=) como folhas (window.print)."""
        from flask import render_template, request as _req
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('carvia.dashboard'))
        nf_id = _req.args.get('nf_id', type=int)
        from app.carvia.services.documentos.carta_correcao_service import (
            CarviaCartaCorrecaoService,
        )
        from app.carvia.services.documentos.cce_render import render_cces_para_impressao
        cces = CarviaCartaCorrecaoService.listar('nf', nf_id) if nf_id else []
        paginas = render_cces_para_impressao(cces)
        return render_template('carvia/nfs/imprimir_cce.html',
                               cces=paginas, nf_id=nf_id)
```

- [ ] **Step 4: Create the print template**

```jinja
{# app/templates/carvia/nfs/imprimir_cce.html #}
<!DOCTYPE html>
<html lang="pt-br"><head><meta charset="utf-8"><title>Cartas de Correcao</title>
<style>
  @page { margin: 8mm; }
  body { margin: 0; font-family: Arial, sans-serif; }
  .cce-page { page-break-after: always; text-align: center; }
  .cce-page:last-child { page-break-after: auto; }
  .cce-page img { max-width: 100%; height: auto; }
  .cce-desc { font-size: 12px; color: #444; margin: 4px 0; }
  .cce-vazio { padding: 40px; color: #888; text-align: center; }
</style></head><body>
{% if cces %}
  {% for cce in cces %}
    {% for pag in cce.paginas %}
    <div class="cce-page">
      {% if cce.descricao and loop.first %}<div class="cce-desc">{{ cce.descricao }}</div>{% endif %}
      <img src="data:image/png;base64,{{ pag }}" alt="Carta de Correcao">
    </div>
    {% endfor %}
  {% endfor %}
{% else %}
  <div class="cce-vazio">Nenhuma carta de correcao para esta NF.</div>
{% endif %}
<script>window.onload = function () { window.print(); };</script>
</body></html>
```

- [ ] **Step 5: Run tests**

Run: `pytest tests/carvia/test_carta_correcao_routes.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/carvia/routes/carta_correcao_routes.py app/templates/carvia/nfs/imprimir_cce.html tests/carvia/test_carta_correcao_routes.py
git commit -m "feat(carvia): rota+template unica de impressao de CCe (PDF->imagem, window.print)"
```

---

### Task C3: Botão "Imprimir CCe" no detalhe da NF

**Files:**
- Modify: `app/templates/carvia/nfs/detalhe.html` (botão na barra de ações, ~linha 64-67)

**Interfaces:**
- Consumes: rota `carvia.imprimir_cce` (C2); `cces_nf` já no contexto (B5).

- [ ] **Step 1: Add the button** (junto aos botões "Baixar PDF/XML", ~linha 64)

```jinja
{% if cces_nf %}
<a href="{{ url_for('carvia.imprimir_cce', nf_id=nf.id) }}" target="_blank"
   class="btn btn-outline-secondary btn-sm" title="Imprimir Cartas de Correcao">
  <i class="fas fa-print"></i> Imprimir CCe ({{ cces_nf|length }})
</a>
{% endif %}
```

- [ ] **Step 2: Manual smoke test**

Run: `python run.py`; abra um detalhe de NF com CCe anexada; clique "Imprimir CCe".
Expected: nova aba abre com a CCe renderizada e o diálogo de impressão.

- [ ] **Step 3: Commit**

```bash
git add app/templates/carvia/nfs/detalhe.html
git commit -m "feat(carvia): botao Imprimir CCe no detalhe da NF"
```

---

### Task C4: CCe no PDF do embarque (capa + completo)

**Files:**
- Modify: `app/embarques/routes.py` (topo: import de `render_cces_para_impressao`; `imprimir_embarque` ~1440 e `imprimir_embarque_completo` ~1494)
- Modify: `app/templates/embarques/imprimir_completo.html` (após loop CarVia, ~linha 567)
- Modify: `app/templates/embarques/imprimir_embarque.html` (antes do rodapé/script ~349)
- Test: `tests/carvia/test_cce_embarque.py`

**Interfaces:**
- Consumes: `CarviaCartaCorrecaoService.listar`, `render_cces_para_impressao` (C1). `app/embarques` PODE importar CarVia (R1 restringe só o que CarVia importa). Importe `render_cces_para_impressao` no topo de `routes.py` (não cria ciclo — `cce_render` não importa embarques) para o monkeypatch do teste funcionar.
- Produces: `_coletar_cces_embarque(numeros_nf) -> list[dict]` (forma de `render_cces_para_impressao`); contexto `cces_embarque` nos 2 templates.

- [ ] **Step 1: Write the failing test**

```python
# tests/carvia/test_cce_embarque.py
import io
from app import db as _db
from werkzeug.datastructures import FileStorage


def test_coletar_cces_do_embarque_por_nf(db, monkeypatch):
    from app.embarques import routes as emb_routes
    from app.carvia.models.documentos import CarviaNf
    from app.carvia.services.documentos.carta_correcao_service import CarviaCartaCorrecaoService
    nf = CarviaNf(numero_nf='9001', cnpj_emitente='1', nome_emitente='E',
                  cnpj_destinatario='2', nome_destinatario='D',
                  cidade_destinatario='C', uf_destinatario='SP',
                  valor_total=1, tipo_fonte='MANUAL', status='ATIVA', criado_por='t')
    _db.session.add(nf); _db.session.flush()
    CarviaCartaCorrecaoService.criar('nf', nf.id,
        FileStorage(stream=io.BytesIO(b'%PDF-1.4 x'), filename='c.pdf', content_type='application/pdf'), 'u')
    _db.session.commit()
    # evita render real: substitui no namespace de routes (import no topo do modulo)
    monkeypatch.setattr(emb_routes, 'render_cces_para_impressao',
                        lambda cces: [{'carta_id': c.id, 'descricao': None, 'paginas': ['AAA']} for c, _ in cces])
    out = emb_routes._coletar_cces_embarque(['9001'])
    assert len(out) == 1 and out[0]['paginas'] == ['AAA']
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/carvia/test_cce_embarque.py -v`
Expected: FAIL — `_coletar_cces_embarque` não existe.

- [ ] **Step 3: Import + collector + wire both routes** (em `app/embarques/routes.py`)

No topo do arquivo (com os demais imports):

```python
from app.carvia.services.documentos.cce_render import render_cces_para_impressao
```

Defina a função coletora (nível de módulo):

```python
def _coletar_cces_embarque(numeros_nf):
    """Renderiza as CCe (PDF->imagem base64) das NFs CarVia do embarque, p/ impressao."""
    numeros = [n for n in (numeros_nf or []) if n]
    if not numeros:
        return []
    from app.carvia.models.documentos import CarviaNf
    from app.carvia.services.documentos.carta_correcao_service import (
        CarviaCartaCorrecaoService,
    )
    nf_ids = [nf.id for nf in CarviaNf.query.filter(
        CarviaNf.numero_nf.in_(numeros), CarviaNf.status == 'ATIVA').all()]
    pares = []
    vistos = set()
    for nf_id in nf_ids:
        for carta, vinc in CarviaCartaCorrecaoService.listar('nf', nf_id):
            if carta.id not in vistos:
                vistos.add(carta.id)
                pares.append((carta, vinc))
    return render_cces_para_impressao(pares)
```

> Se o import no topo de `app/embarques/routes.py` causar import circular no startup, mova-o para dentro de `_coletar_cces_embarque` e ajuste o monkeypatch do teste para `monkeypatch.setattr('app.carvia.services.documentos.cce_render.render_cces_para_impressao', ...)`. Verifique `python -c "import app"` após editar.

Em `imprimir_embarque_completo` (~linha 1616, após montar `carvia_separacoes_data`) e em `imprimir_embarque` (após montar a lista de itens), antes dos respectivos `render_template`:

```python
        numeros_nf_carvia = [
            it.nota_fiscal for it in embarque.itens_ativos
            if it.nota_fiscal and (it.separacao_lote_id or '').startswith('CARVIA-')
        ]
        cces_embarque = _coletar_cces_embarque(numeros_nf_carvia)
```

e passe `cces_embarque=cces_embarque` aos dois `render_template`.

- [ ] **Step 4: Inject pages in both templates**

Em `imprimir_completo.html`, após o `{% endfor %}` do loop CarVia (~linha 567) e antes do rodapé (~linha 570):

```jinja
{% if cces_embarque %}
  {% for cce in cces_embarque %}
    {% for pag in cce.paginas %}
    <div class="page-break" style="text-align:center;">
      <img src="data:image/png;base64,{{ pag }}" style="max-width:100%;height:auto;" alt="Carta de Correcao">
    </div>
    {% endfor %}
  {% endfor %}
{% endif %}
```

Em `imprimir_embarque.html`, imediatamente antes do `<script>window.print()...` (~linha 349), insira o mesmo bloco `{% if cces_embarque %}...{% endif %}`.

- [ ] **Step 5: Run tests + import check**

Run: `python -c "import app" && pytest tests/carvia/test_cce_embarque.py -v`
Expected: import OK; PASS.

- [ ] **Step 6: Manual smoke test**

Run: `python run.py`; imprima um embarque (capa e completo) que contenha NF CarVia com CCe.
Expected: as folhas da CCe saem ao final do mesmo PDF/impressão.

- [ ] **Step 7: Commit**

```bash
git add app/embarques/routes.py app/templates/embarques/imprimir_completo.html app/templates/embarques/imprimir_embarque.html tests/carvia/test_cce_embarque.py
git commit -m "feat(embarques): CCe das NFs CarVia sai no PDF do embarque (capa+completo)"
```

---

### Task C5: CCe no monitoramento (exibir + imprimir)

**Files:**
- Modify: `app/monitoramento/routes.py` (`visualizar_entrega` ~linha 197)
- Modify: `app/templates/monitoramento/visualizar_entrega.html` (seção + botão)
- Test: `tests/carvia/test_cce_monitoramento.py`

**Interfaces:**
- Consumes: `CarviaCartaCorrecaoService.listar`; `CarviaNf` (lazy); rota `carvia.imprimir_cce` (C2).
- Produces: `_cces_da_entrega(entrega) -> tuple[list, int|None]` retornando `(pares, nf_id)`; contexto `cces_entrega` + `cce_nf_id`.

- [ ] **Step 1: Write the failing test**

```python
# tests/carvia/test_cce_monitoramento.py
import io
from app import db as _db
from werkzeug.datastructures import FileStorage


def test_resolver_cces_da_entrega_carvia(db):
    from app.monitoramento import routes as mon_routes
    from app.carvia.models.documentos import CarviaNf
    from app.carvia.services.documentos.carta_correcao_service import CarviaCartaCorrecaoService
    nf = CarviaNf(numero_nf='9100', cnpj_emitente='1', nome_emitente='E',
                  cnpj_destinatario='2', nome_destinatario='D',
                  cidade_destinatario='C', uf_destinatario='SP',
                  valor_total=1, tipo_fonte='MANUAL', status='ATIVA', criado_por='t')
    _db.session.add(nf); _db.session.flush()
    CarviaCartaCorrecaoService.criar('nf', nf.id,
        FileStorage(stream=io.BytesIO(b'%PDF-1.4 x'), filename='c.pdf', content_type='application/pdf'), 'u')
    _db.session.commit()

    class _E:
        numero_nf = '9100'; origem = 'CARVIA'
    pares, nf_id = mon_routes._cces_da_entrega(_E())
    assert len(pares) == 1
    assert nf_id == nf.id


def test_resolver_cces_entrega_nacom_vazio(db):
    from app.monitoramento import routes as mon_routes
    class _E:
        numero_nf = '9100'; origem = 'NACOM'
    pares, nf_id = mon_routes._cces_da_entrega(_E())
    assert pares == [] and nf_id is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/carvia/test_cce_monitoramento.py -v`
Expected: FAIL — `_cces_da_entrega` não existe.

- [ ] **Step 3: Add helper + wire route** (em `app/monitoramento/routes.py`)

```python
def _cces_da_entrega(entrega):
    """CCe da entrega CarVia (numero_nf -> CarviaNf ATIVA -> CCe).
    Retorna (pares, nf_id). Lazy import (R1-safe). ([] , None) se nao-CarVia."""
    if not entrega or getattr(entrega, 'origem', None) != 'CARVIA' or not entrega.numero_nf:
        return [], None
    from app.carvia.models.documentos import CarviaNf
    from app.carvia.services.documentos.carta_correcao_service import (
        CarviaCartaCorrecaoService,
    )
    nf = CarviaNf.query.filter_by(numero_nf=entrega.numero_nf, status='ATIVA').first()
    if not nf:
        return [], None
    return CarviaCartaCorrecaoService.listar('nf', nf.id), nf.id
```

Em `visualizar_entrega` (~linha 197), antes do `render_template`:

```python
    cces_entrega, cce_nf_id = _cces_da_entrega(entrega)
```

e adicione `cces_entrega=cces_entrega, cce_nf_id=cce_nf_id` ao contexto.

- [ ] **Step 4: Add the section to the template**

Em `app/templates/monitoramento/visualizar_entrega.html`, numa seção visível do detalhe:

```jinja
{% if cces_entrega %}
<div class="card mt-3">
  <div class="card-header d-flex justify-content-between align-items-center">
    <span><i class="fas fa-file-signature"></i> Cartas de Correcao (CCe) ({{ cces_entrega|length }})</span>
    {% if cce_nf_id %}
    <a href="{{ url_for('carvia.imprimir_cce', nf_id=cce_nf_id) }}" target="_blank"
       class="btn btn-sm btn-outline-secondary"><i class="fas fa-print"></i> Imprimir CCe</a>
    {% endif %}
  </div>
  <div class="card-body p-2">
    <ul class="list-unstyled mb-0">
      {% for carta, vinc in cces_entrega %}
      <li>
        <a href="{{ url_for('carvia.download_carta_correcao', carta_id=carta.id) }}">
          <i class="fas fa-download"></i> {{ carta.nome_original }}</a>
        {% if carta.descricao %}<small class="text-muted">— {{ carta.descricao }}</small>{% endif %}
      </li>
      {% endfor %}
    </ul>
  </div>
</div>
{% endif %}
```

- [ ] **Step 5: Run tests + manual smoke**

Run: `pytest tests/carvia/test_cce_monitoramento.py -v`
Expected: PASS (2 passed). Smoke: abra uma EntregaMonitorada CarVia com CCe; veja a seção e o botão imprimir.

- [ ] **Step 6: Commit**

```bash
git add app/monitoramento/routes.py app/templates/monitoramento/visualizar_entrega.html tests/carvia/test_cce_monitoramento.py
git commit -m "feat(monitoramento): exibe e imprime CCe da entrega CarVia"
```

---

## Fechamento (parte do "pronto")

- [ ] Rodar a suíte CarVia completa: `pytest tests/carvia/ -q` (sem regressões).
- [ ] Atualizar `app/carvia/CLAUDE.md`: nova seção documentando (a) propagação de cidade/UF do endereço (gatilho `atualizar_endereco`, helper R1-safe, vínculos) e (b) CCe-anexo (cadeia cotacao↔nf, rotas, impressão embarque/NF/monitoramento) — distinguindo do `CarviaEnderecoCorrecao` (audit textual do CTe).
- [ ] Indexar este plano e o spec em `docs/superpowers/plans/INDEX.md` / `specs/INDEX.md` (skill padronizando-docs).
- [ ] Verificar geração de schemas JSON de `carvia_cartas_correcao` / `carvia_carta_correcao_vinculos` em `.claude/skills/consultando-sql/schemas/tables/` (se houver pipeline de geração).

## Self-Review do plano

- **Cobertura do spec:** Fase A (propagação NF/cotação/operação/embarque/monitoramento) = A1-A3. Fase B (model+anexo cadeia cotação/NF) = B1-B5. Fase C (impressão embarque capa+completo, NF, monitoramento, rota única) = C1-C5. Migration = B2. Sem requisito do spec sem task.
- **Riscos do spec:** R-A (CNPJ/`tipo='DESTINO'`) coberto em A2; R-B (regressão comprovante) coberto em B1 Step 5; R-C (override cotação só-se-preenchido) em A2; R-D (custo render) mitigado por `scale=2.5` + só CCe das NFs do embarque em C4; R-E (sobrescrita NF ATIVA) em A2.
- **Consistência de tipos:** `render_cces_para_impressao(cces)` consome pares `(carta, vinculo)` em C1/C2/C4; `listar()` retorna esses pares (B3). `propagar()` retorna dict com 5 chaves usado em A3. `_coletar_cces_embarque` retorna lista de dicts renderizados; `_cces_da_entrega` retorna `(pares, nf_id)` — consistente com o consumo nos templates.
- **Placeholders conhecidos:** o `<rev>` da migration (gerado pelo Flask-Migrate); fixture de login em B4 (usar a do conftest se existir) e o possível import lazy em C4 — ambos com a correção explícita inline.
