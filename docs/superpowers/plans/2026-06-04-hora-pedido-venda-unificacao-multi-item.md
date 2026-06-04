<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-04
-->
# HORA — Pedido de Venda: unificação multi-item + submit único — Implementation Plan

> **Papel:** plano de implementação task-by-task (TDD) da unificação multi-item do Pedido de Venda das Lojas HORA — componente de lista de motos compartilhado pelas 2 telas (FU-2), N motos na criação (FU-3) e um único "Salvar Pedido" que reconcilia header+itens+pagamentos numa transação (FU-5).

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unificar a área de motos do Pedido de Venda HORA num componente de lista compartilhado pelas 2 telas (FU-2), permitir N motos na criação (FU-3) e reduzir os "Salvar X" granulares a um único "Salvar Pedido" que reconcilia header+itens+pagamentos numa transação (FU-5).

**Architecture:** `criar_venda_manual` passa a aceitar `itens=[...]` (retrocompatível). Novo `salvar_pedido_completo` reconcilia o estado submetido contra o banco compondo helpers flush-only (`_aplicar_header`/`_aplicar_itens`/`_aplicar_pagamentos`) com 1 commit. Front: `_lista_motos.html` (lista repetível) idêntico em criação e edição, com IDs por-linha e um botão "Salvar Pedido". Transições e peças inalteradas; 5 rotas granulares ficam deprecadas (só os forms saem).

**Tech Stack:** Flask 3 + SQLAlchemy 2 (services em `app/hora/services/venda_service.py`, rotas em `app/hora/routes/`), Jinja2 + vanilla JS (`_pedido_venda_scripts.html`), pytest (`tests/hora/`).

**Spec:** `docs/superpowers/specs/2026-06-04-hora-pedido-venda-unificacao-multi-item-design.md`.

## Indice

- [Fase 1 — Backend: criação multi-item](#fase-1--backend-criação-multi-item)
- [Fase 2 — Frontend: componente de lista + criação multi-item](#fase-2--frontend-componente-de-lista--criação-multi-item)
- [Fase 3 — Backend+Front: edição reconciliadora](#fase-3--backendfront-edição-reconciliadora)
- [Fase 4 — Cleanup + regressão](#fase-4--cleanup--regressão)
- [Self-Review (cobertura da spec)](#self-review-cobertura-da-spec)

**Pré-requisitos de execução (gotchas):**
- Rodar pytest da raiz do worktree com `.env`+venv da raiz: `set -a; source <raiz>/.env; set +a; source <raiz>/.venv/bin/activate; python -m pytest ...` (sem `.env` cai em SQLite; `gotcha_testes_hora_residuo`).
- Commits: o pre-commit UI lint chama `python` — manter o venv ativado no shell do commit.
- Testes HORA: usar CNPJ único `uuid.int[:14]` para loja (`_loja_unica` em `tests/hora/test_autocomplete_chassi_disponivel.py`); services HORA fazem flush, commit na rota/orquestrador.

---

## Fase 1 — Backend: criação multi-item

### Task 1: `criar_venda_manual` aceita `itens=[...]` (retrocompatível)

**Files:**
- Modify: `app/hora/services/venda_service.py:635-916` (`criar_venda_manual`)
- Test: `tests/hora/test_criar_venda_multi_item.py` (criar)

- [ ] **Step 1: Write the failing test**

```python
# tests/hora/test_criar_venda_multi_item.py
"""Fase 1 (FU-3): criar_venda_manual aceita lista de itens (N motos)."""
from __future__ import annotations

import uuid
from decimal import Decimal

from app import db as _db
from app.hora.models import HoraLoja, HoraModelo, HoraVenda
from app.hora.services import venda_service
from app.hora.services.moto_service import get_or_create_moto, registrar_evento


def _loja(modelo_nome=None):
    from app.utils.timezone import agora_utc_naive
    cnpj = str(uuid.uuid4().int)[:14].ljust(14, '0')
    loja = HoraLoja(cnpj=cnpj, apelido='MI-' + cnpj[:6], nome='Loja MI ' + cnpj[:6],
                    razao_social='Loja MI LTDA', nome_fantasia='Loja MI', ativa=True,
                    atualizado_em=agora_utc_naive())
    _db.session.add(loja); _db.session.flush()
    return loja


def _modelo():
    m = HoraModelo(nome_modelo='MOD-MI-' + uuid.uuid4().hex[:8].upper(), ativo=True,
                   preco_a_vista=Decimal('1000.00'))
    _db.session.add(m); _db.session.flush()
    return m


def _chassi_estoque(modelo_nome, loja_id, cor='PRETA'):
    chassi = ('MI' + uuid.uuid4().hex).upper()[:25]
    get_or_create_moto(numero_chassi=chassi, modelo_nome=modelo_nome, cor=cor, criado_por='t')
    registrar_evento(numero_chassi=chassi, tipo='RECEBIDA', loja_id=loja_id, operador='t')
    registrar_evento(numero_chassi=chassi, tipo='CONFERIDA', loja_id=loja_id, operador='t')
    _db.session.flush()
    return chassi


def _endereco():
    return dict(cep='01001000', endereco_logradouro='Rua A', endereco_numero='1',
                endereco_complemento='', endereco_bairro='Centro', endereco_cidade='SP',
                endereco_uf='SP')


def test_criar_venda_com_dois_itens(db):
    loja = _loja(); modelo = _modelo()
    c1 = _chassi_estoque(modelo.nome_modelo, loja.id)
    c2 = _chassi_estoque(modelo.nome_modelo, loja.id)
    venda = venda_service.criar_venda_manual(
        cpf_cliente='12345678909', nome_cliente='Cliente Dois',
        itens=[{'numero_chassi': c1, 'valor_final': Decimal('1000.00')},
               {'numero_chassi': c2, 'valor_final': Decimal('900.00')}],
        pagamentos=[{'forma_pagamento_hora': 'DINHEIRO', 'valor': Decimal('1900.00'),
                     'numero_parcelas': 1, 'aut_id': None}],
        loja_id_override=loja.id, criado_por='t', **_endereco(),
    )
    assert {it.numero_chassi for it in venda.itens} == {c1, c2}
    assert venda.valor_total == Decimal('1900.00')


def test_criar_venda_legado_chassi_singular_ainda_funciona(db):
    """Retrocompat: numero_chassi/valor_final (sem itens) cria 1 item."""
    loja = _loja(); modelo = _modelo()
    c1 = _chassi_estoque(modelo.nome_modelo, loja.id)
    venda = venda_service.criar_venda_manual(
        cpf_cliente='12345678909', nome_cliente='Cliente Um',
        numero_chassi=c1, valor_final=Decimal('1000.00'),
        pagamentos=[{'forma_pagamento_hora': 'DINHEIRO', 'valor': Decimal('1000.00'),
                     'numero_parcelas': 1, 'aut_id': None}],
        loja_id_override=loja.id, criado_por='t', **_endereco(),
    )
    assert len(venda.itens) == 1 and venda.itens[0].numero_chassi == c1
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/hora/test_criar_venda_multi_item.py -q`
Expected: FAIL — `test_criar_venda_com_dois_itens` erra (kwarg `itens` inesperado / só cria 1).

- [ ] **Step 3: Refactor `criar_venda_manual` signature + normalização**

Em `venda_service.py`, no início de `criar_venda_manual` (~`:635`), trocar os parâmetros singulares por `itens` opcional retrocompatível e normalizar para lista interna. Substituir a assinatura para incluir `itens: Optional[List[dict]] = None` (manter `numero_chassi=None`, `valor_final=None` para legado) e, antes das validações, inserir:

```python
    # Normaliza para lista de itens (FU-3). Legado: numero_chassi/valor_final
    # singulares -> 1 item. Novo: itens=[{numero_chassi, valor_final}, ...].
    if itens is None:
        if numero_chassi is None or valor_final is None:
            raise ValueError('Informe itens=[...] ou numero_chassi/valor_final.')
        itens = [{'numero_chassi': numero_chassi, 'valor_final': valor_final}]
    itens_norm = []
    vistos = set()
    for it in itens:
        ch = (it.get('numero_chassi') or '').strip()
        if not ch:
            raise ValueError('Item sem chassi.')
        if ch in vistos:
            raise ValueError(f'Chassi repetido no pedido: {ch}')
        vistos.add(ch)
        itens_norm.append({'numero_chassi': ch, 'valor_final': it.get('valor_final')})
    if not itens_norm:
        raise ValueError('Pedido precisa de ao menos 1 item.')
```

- [ ] **Step 4: Trocar o trecho de criação de 1 item por loop sobre `itens_norm`**

Onde hoje (~`:762-858`) há o lock de 1 chassi + criação de 1 `HoraVendaItem` + 1 `RESERVADA`, substituir por loop que acumula `valor_total`. Antes de `add(venda)`/`flush`, o `valor_total` precisa ser a soma — então mover o cálculo para depois do loop de itens (criar a `HoraVenda` com `valor_total=0`, flush para obter `venda.id`, depois iterar itens). Estrutura:

```python
    # venda criada com valor_total=0; itens somam abaixo.
    db.session.add(venda)
    db.session.flush()  # venda.id

    valor_total = Decimal('0')
    for it in itens_norm:
        ch = it['numero_chassi']
        _lock_chassi_e_validar_disponivel(ch)
        preco_ref, desc_rs, desc_pct, tabela_id, _div = _resolver_preco_tabela(
            modelo_id=_modelo_id_do_chassi(ch), na_data=venda.data_venda,
            valor_final=it['valor_final'],
        )
        item = HoraVendaItem(
            venda_id=venda.id, numero_chassi=ch, tabela_preco_id=tabela_id,
            preco_tabela_referencia=preco_ref, desconto_aplicado=desc_rs,
            desconto_percentual=desc_pct, preco_final=it['valor_final'],
        )
        db.session.add(item)
        db.session.flush()
        registrar_evento(numero_chassi=ch, tipo='RESERVADA', loja_id=venda.loja_id,
                         operador=criado_por or 'sistema')
        valor_total += Decimal(str(it['valor_final']))
    venda.valor_total = valor_total
    db.session.flush()
```

> Nota: extrair `_modelo_id_do_chassi(chassi)` se ainda não existir (helper que faz `HoraMoto.query.get(chassi).modelo_id`), ou reusar o caminho atual de resolução de modelo dentro do antigo bloco de 1 item. O cálculo de `status` (`_avaliar_status_pagamento`) deve rodar **após** `valor_total` estar somado.

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest tests/hora/test_criar_venda_multi_item.py tests/hora/test_pedido_workflow.py -q`
Expected: PASS (novos + 15 de workflow continuam verdes — retrocompat).

- [ ] **Step 6: Commit**

```bash
git add app/hora/services/venda_service.py tests/hora/test_criar_venda_multi_item.py
git commit -m "feat(hora): criar_venda_manual aceita itens=[...] (N motos, retrocompat) [Fase 1]"
```

### Task 2: Rota de criação lê arrays `chassi[]`/`valor[]`

**Files:**
- Modify: `app/hora/routes/tagplus_routes.py:1034-1198` (`tagplus_pedido_venda_criar`)
- Test: `tests/hora/test_pedido_venda_criar_route_arrays.py` (criar)

- [ ] **Step 1: Write the failing test** (usa `client` + login bypass do conftest)

```python
# tests/hora/test_pedido_venda_criar_route_arrays.py
"""Fase 1 (FU-3): rota de criacao monta lista de itens a partir de chassi[]/valor[]."""
from __future__ import annotations
import uuid
from decimal import Decimal

from app import db as _db
from app.hora.models import HoraLoja, HoraModelo, HoraVenda
from app.hora.services.moto_service import get_or_create_moto, registrar_evento


def _loja():
    from app.utils.timezone import agora_utc_naive
    cnpj = str(uuid.uuid4().int)[:14].ljust(14, '0')
    loja = HoraLoja(cnpj=cnpj, apelido='RT-' + cnpj[:6], nome='Loja RT', razao_social='RT LTDA',
                    nome_fantasia='RT', ativa=True, atualizado_em=agora_utc_naive())
    _db.session.add(loja); _db.session.flush(); return loja


def _chassi(loja_id):
    m = HoraModelo(nome_modelo='MOD-RT-' + uuid.uuid4().hex[:8].upper(), ativo=True,
                   preco_a_vista=Decimal('1000'))
    _db.session.add(m); _db.session.flush()
    ch = ('RT' + uuid.uuid4().hex).upper()[:25]
    get_or_create_moto(numero_chassi=ch, modelo_nome=m.nome_modelo, cor='PRETA', criado_por='t')
    registrar_evento(numero_chassi=ch, tipo='RECEBIDA', loja_id=loja_id, operador='t')
    registrar_evento(numero_chassi=ch, tipo='CONFERIDA', loja_id=loja_id, operador='t')
    _db.session.flush(); return ch


def test_post_criar_com_dois_chassis(client, db):
    loja = _loja(); c1 = _chassi(loja.id); c2 = _chassi(loja.id)
    resp = client.post('/hora/tagplus/pedido-venda', data={
        'cpf': '12345678909', 'nome': 'Cliente', 'cep': '01001000',
        'logradouro': 'Rua A', 'numero_endereco': '1', 'bairro': 'Centro',
        'cidade': 'SP', 'uf': 'SP', 'loja_id': str(loja.id), 'vendedor': 'Fulano',
        'chassi': [c1, c2], 'valor': ['1.000,00', '900,00'],
        'pagamento_forma': ['DINHEIRO'], 'pagamento_valor': ['1.900,00'],
        'pagamento_parcelas': ['1'], 'pagamento_aut_id': [''],
        'modalidade_frete': '1',
    }, follow_redirects=False)
    assert resp.status_code in (302, 303)
    venda = HoraVenda.query.filter(HoraVenda.itens.any()).order_by(HoraVenda.id.desc()).first()
    assert venda is not None
    assert {it.numero_chassi for it in venda.itens} == {c1, c2}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/hora/test_pedido_venda_criar_route_arrays.py -q`
Expected: FAIL — a rota lê `chassi` singular; cria 1 item (ou erra).

- [ ] **Step 3: Modify the route to read arrays**

Em `tagplus_pedido_venda_criar`, trocar a leitura singular de `chassi`/`valor` por arrays e montar `itens`:

```python
    chassis = request.form.getlist('chassi')
    valores = request.form.getlist('valor')
    itens = []
    for i, ch in enumerate(chassis):
        ch = (ch or '').strip()
        if not ch:
            continue
        v_raw = valores[i] if i < len(valores) else ''
        v_str = (v_raw or '').strip().replace('.', '').replace(',', '.') if ',' in (v_raw or '') else (v_raw or '').strip()
        try:
            v = Decimal(v_str) if v_str else None
        except (InvalidOperation, ValueError):
            v = None
        itens.append({'numero_chassi': ch, 'valor_final': v})
    # ... chamar criar_venda_manual(itens=itens, ...) em vez de numero_chassi/valor_final
```

E na chamada a `criar_venda_manual`, substituir `numero_chassi=...`/`valor_final=...` por `itens=itens`.

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/hora/test_pedido_venda_criar_route_arrays.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/hora/routes/tagplus_routes.py tests/hora/test_pedido_venda_criar_route_arrays.py
git commit -m "feat(hora): rota de criacao le chassi[]/valor[] (N motos) [Fase 1]"
```

---

## Fase 2 — Frontend: componente de lista + criação multi-item

### Task 3: Componente `_lista_motos.html` (lista repetível)

**Files:**
- Create: `app/templates/hora/tagplus/_lista_motos.html`
- Reference: `app/templates/hora/tagplus/_componente_moto_desconto.html` (markup de 1 linha)

- [ ] **Step 1: Criar o partial com 1 linha-template + container**

Estrutura (cada linha = o conteúdo do `_componente_moto_desconto.html` com IDs sufixados por `data-row` e classes `.js-*`, + hidden `item_id` + botão remover). O loop renderiza linhas existentes (`itens` no modo edição) ou 1 linha vazia (criação). Inclui `<template id="tpl-linha-moto">` para clonar.

```jinja
{# _lista_motos.html — lista repetivel de motos. Compartilhado criacao+edicao.
   Contexto: `itens` (lista de HoraVendaItem ou vazio), `modelos`, `somente_leitura` (bool). #}
<div id="motos-container" data-somente-leitura="{{ '1' if somente_leitura else '0' }}">
  {% set linhas = itens if itens else [None] %}
  {% for it in linhas %}
    {% include 'hora/tagplus/_linha_moto.html' with context %}
  {% endfor %}
</div>
{% if not somente_leitura %}
<button type="button" class="btn btn-outline-secondary btn-sm mt-2" id="btn-add-moto-linha">
  <i class="fas fa-plus"></i> Adicionar moto
</button>
<template id="tpl-linha-moto">
  {% set it = None %}
  {% include 'hora/tagplus/_linha_moto.html' with context %}
</template>
{% endif %}
```

- [ ] **Step 2: Criar `_linha_moto.html`** (uma linha — extrai o markup do `_componente_moto_desconto.html`, IDs sufixados `-{{ loop_idx }}`/`item.id`, classes `.js-modelo/.js-cor/.js-chassi/.js-preco-tabela/.js-desconto-pct/.js-desconto-rs/.js-valor`, hidden `item_id`, botão `.js-remover-linha`). O chassi mantém `data-hora-autocomplete="chassi" data-hora-open-on-focus="1" data-hora-extra-params="disponivel=1"`. Em `somente_leitura`, campos viram `readonly`/`disabled` e o botão remover some.

> O conteúdo é o `_componente_moto_desconto.html` atual com: (a) `id="f-modelo"` → `class="form-select js-modelo"` + `data-row` único; idem cor/chassi/preço/desconto/valor; (b) `<input type="hidden" name="item_id" value="{{ it.id if it else '' }}" class="js-item-id">`; (c) `name="chassi"` continua (array `chassi[]`); `name="valor"` continua (array `valor[]`).

- [ ] **Step 3: Validar render (Jinja compila) via smoke**

Run (da raiz do worktree, venv+env): `python -c "from app import create_app; app=create_app(); app.jinja_env.get_template('hora/tagplus/_lista_motos.html'); app.jinja_env.get_template('hora/tagplus/_linha_moto.html'); print('OK')"`
Expected: `OK`.

- [ ] **Step 4: Commit**

```bash
git add app/templates/hora/tagplus/_lista_motos.html app/templates/hora/tagplus/_linha_moto.html
git commit -m "feat(hora): componente _lista_motos (lista repetivel de motos) [Fase 2]"
```

### Task 4: JS — add/remove linha + cascata e desconto por-linha

**Files:**
- Modify: `app/templates/hora/tagplus/_pedido_venda_scripts.html`

- [ ] **Step 1: Reescrever a cascata para escopo de linha**

Adicionar função `wireLinhaMoto(rowEl)` que: (a) liga `wireDescontoSync(rowEl, preco)` (já existe, por-escopo); (b) `carregarCores`/`atualizarFiltroChassi`/`preencherDadosDoChassi`/`atualizarPrecoTabela` operam via `rowEl.querySelector('.js-modelo'|'.js-cor'|'.js-chassi'|...)` (não `getElementById`). Inicializar `document.querySelectorAll('#motos-container [data-row]').forEach(wireLinhaMoto)`.

```javascript
function wireLinhaMoto(row) {
  const elModelo = row.querySelector('.js-modelo');
  const elCor    = row.querySelector('.js-cor');
  const elChassi = row.querySelector('.js-chassi');
  // atualizarFiltroChassi por-linha
  function atualizarFiltro() {
    if (!elChassi) return;
    const p = ['disponivel=1'];
    if (elModelo && elModelo.value) p.push('modelo_id=' + encodeURIComponent(elModelo.value));
    if (elCor && elCor.value) p.push('cor=' + encodeURIComponent(elCor.value));
    elChassi.dataset.horaExtraParams = p.join('&');
  }
  if (elModelo) elModelo.addEventListener('change', () => { atualizarFiltro(); /* carregarCores(row); atualizarPrecoTabela(row); */ });
  if (elCor) elCor.addEventListener('change', () => { atualizarFiltro(); if (elChassi) elChassi.value=''; });
  atualizarFiltro();
  const preco = parseBR((row.querySelector('.js-preco-tabela')||{}).value);
  wireDescontoSync(row, isNaN(preco) ? null : preco);
  const btnRemover = row.querySelector('.js-remover-linha');
  if (btnRemover) btnRemover.addEventListener('click', () => {
    if (document.querySelectorAll('#motos-container [data-row]').length > 1) row.remove();
  });
}
```

- [ ] **Step 2: Add-linha clonando o `<template>`**

```javascript
const btnAddLinha = document.getElementById('btn-add-moto-linha');
const tplLinha = document.getElementById('tpl-linha-moto');
const motosContainer = document.getElementById('motos-container');
if (btnAddLinha && tplLinha && motosContainer) {
  btnAddLinha.addEventListener('click', () => {
    const frag = tplLinha.content.cloneNode(true);
    const row = frag.querySelector('[data-row]');
    motosContainer.appendChild(frag);
    if (window.HoraAutocomplete) window.HoraAutocomplete.init(row);  // ativa autocomplete do chassi novo
    wireLinhaMoto(row);
  });
}
```

> Migrar a cascata global existente (`elModelo`/`elCor`/`elChassi` por `getElementById`) para o caminho por-linha; manter `wireDescontoSync` (não mexer) e o bloco Enter=Próximo (Frente B) e o painel de pagamentos.

- [ ] **Step 3: Validar JS renderizado**

Run: `python -c "from app import create_app; app=create_app(); app.test_client().get('/hora/tagplus/pedido-venda/novo')"` — então `node --check` no JS extraído (ou validar via Playwright na Task 9). Mínimo: garantir que `_pedido_venda_scripts.html` ainda compila como Jinja e o `<script>` é JS válido (`node --check` num dump do template renderizado).

- [ ] **Step 4: Commit**

```bash
git add app/templates/hora/tagplus/_pedido_venda_scripts.html
git commit -m "feat(hora): cascata+desconto por-linha + add/remove linha de moto [Fase 2]"
```

### Task 5: Tela de criação usa `_lista_motos.html` + 1 botão "Salvar Pedido"

**Files:**
- Modify: `app/templates/hora/tagplus/pedido_venda_novo.html` (branch `{% else %}` — criação, ~L878-1008)

- [ ] **Step 1: Trocar o include único por `_lista_motos.html`**

No bloco de criação, substituir `{% include 'hora/tagplus/_componente_moto_desconto.html' %}` por `{% include 'hora/tagplus/_lista_motos.html' %}` (com `somente_leitura = false`, `itens = []`). Garantir um único `<button type="submit">Salvar Pedido</button>` ao fim do form `#form-pedido-venda`.

- [ ] **Step 2: Smoke render**

Run: `python -c "from app import create_app; app=create_app(); print(app.test_client().get('/hora/tagplus/pedido-venda/novo').status_code)"`
Expected: `200`.

- [ ] **Step 3: Commit**

```bash
git add app/templates/hora/tagplus/pedido_venda_novo.html
git commit -m "feat(hora): criacao usa _lista_motos + botao unico Salvar Pedido [Fase 2]"
```

---

## Fase 3 — Backend+Front: edição reconciliadora

### Task 6: Extrair helpers flush-only

**Files:**
- Modify: `app/hora/services/venda_service.py` (`editar_venda`, `editar_pagamentos`, `adicionar_item_pedido`, `remover_item_pedido`, `editar_item_pedido`)
- Test: `tests/hora/test_helpers_flush_only.py` (criar)

- [ ] **Step 1: Write the failing test** (helpers não comitam; orquestrador comita)

```python
# tests/hora/test_helpers_flush_only.py
"""Fase 3: helpers _aplicar_* fazem flush, nao commit (1 commit no orquestrador)."""
from app.hora.services import venda_service


def test_helpers_existem_e_nao_comitam(db):
    # Os helpers devem existir e ser flush-only (sem db.session.commit dentro).
    import inspect
    for nome in ('_aplicar_header', '_aplicar_itens', '_aplicar_pagamentos'):
        fn = getattr(venda_service, nome, None)
        assert fn is not None, f'helper {nome} ausente'
        src = inspect.getsource(fn)
        assert 'commit()' not in src, f'{nome} nao pode comitar (flush-only)'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/hora/test_helpers_flush_only.py -q`
Expected: FAIL — helpers não existem.

- [ ] **Step 3: Extrair a lógica em helpers flush-only**

Criar em `venda_service.py`:
- `_aplicar_header(venda, dados: dict, usuario)` — corpo atual de `editar_venda` SEM o `commit` (valida campos via matriz + setattr + auditoria, só `flush`).
- `_aplicar_pagamentos(venda, pagamentos: list[dict], usuario)` — corpo de `editar_pagamentos` sem commit.
- `_aplicar_itens(venda, itens: list[dict], usuario)` — reconcilia: para cada `it` com `item_id` existente → atualiza valor (lógica de `editar_item_pedido` sem troca de chassi); item existente ausente da lista → remove (lógica de `remover_item_pedido`); `it` sem `item_id` com chassi → adiciona (lógica de `adicionar_item_pedido`). Sem commit; respeita "não remove último".

As funções públicas viram wrappers: `editar_venda(...) = _aplicar_header(...) ; db.session.commit()`; idem `editar_pagamentos`, `adicionar_item_pedido`, `remover_item_pedido`, `editar_item_pedido` (cada uma chama o helper específico + `commit`). Preserva os testes de `test_pedido_workflow.py`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/hora/test_helpers_flush_only.py tests/hora/test_pedido_workflow.py tests/hora/test_pedido_venda_editar_item.py -q`
Expected: PASS (helpers existem + workflow intacto).

- [ ] **Step 5: Commit**

```bash
git add app/hora/services/venda_service.py tests/hora/test_helpers_flush_only.py
git commit -m "refactor(hora): extrai helpers flush-only _aplicar_header/itens/pagamentos [Fase 3]"
```

### Task 7: `salvar_pedido_completo` (orquestrador, 1 commit)

**Files:**
- Modify: `app/hora/services/venda_service.py` (nova função)
- Test: `tests/hora/test_salvar_pedido_completo.py` (criar)

- [ ] **Step 1: Write the failing test**

```python
# tests/hora/test_salvar_pedido_completo.py
"""Fase 3 (FU-5): salvar_pedido_completo reconcilia header+itens+pagamentos numa transacao."""
from __future__ import annotations
import uuid
from decimal import Decimal

from app import db as _db
from app.hora.models import HoraLoja, HoraModelo, HoraVenda
from app.hora.services import venda_service
from app.hora.services.moto_service import get_or_create_moto, registrar_evento


def _setup_pedido_2_itens():
    from app.utils.timezone import agora_utc_naive
    cnpj = str(uuid.uuid4().int)[:14].ljust(14, '0')
    loja = HoraLoja(cnpj=cnpj, apelido='SP-' + cnpj[:6], nome='Loja SP', razao_social='SP LTDA',
                    nome_fantasia='SP', ativa=True, atualizado_em=agora_utc_naive())
    _db.session.add(loja); _db.session.flush()
    m = HoraModelo(nome_modelo='MOD-SP-' + uuid.uuid4().hex[:8].upper(), ativo=True,
                   preco_a_vista=Decimal('1000'))
    _db.session.add(m); _db.session.flush()
    def chassi():
        ch = ('SP' + uuid.uuid4().hex).upper()[:25]
        get_or_create_moto(numero_chassi=ch, modelo_nome=m.nome_modelo, cor='PRETA', criado_por='t')
        registrar_evento(numero_chassi=ch, tipo='RECEBIDA', loja_id=loja.id, operador='t')
        registrar_evento(numero_chassi=ch, tipo='CONFERIDA', loja_id=loja.id, operador='t')
        _db.session.flush(); return ch
    c1, c2, c3 = chassi(), chassi(), chassi()
    venda = venda_service.criar_venda_manual(
        cpf_cliente='12345678909', nome_cliente='C', cep='01001000',
        endereco_logradouro='R', endereco_numero='1', endereco_complemento='',
        endereco_bairro='B', endereco_cidade='SP', endereco_uf='SP',
        itens=[{'numero_chassi': c1, 'valor_final': Decimal('1000')},
               {'numero_chassi': c2, 'valor_final': Decimal('1000')}],
        pagamentos=[{'forma_pagamento_hora': 'DINHEIRO', 'valor': Decimal('2000'),
                     'numero_parcelas': 1, 'aut_id': None}],
        loja_id_override=loja.id, criado_por='t')
    return venda, c1, c2, c3


def test_reconcilia_remove_adiciona_atualiza(db):
    venda, c1, c2, c3 = _setup_pedido_2_itens()
    item_c1 = next(it for it in venda.itens if it.numero_chassi == c1)
    # mantem c1 (novo valor 900), remove c2 (ausente), adiciona c3
    venda_service.salvar_pedido_completo(
        venda_id=venda.id,
        header={},
        itens=[{'item_id': item_c1.id, 'numero_chassi': c1, 'valor_final': Decimal('900')},
               {'item_id': None, 'numero_chassi': c3, 'valor_final': Decimal('800')}],
        pagamentos=[{'forma_pagamento_hora': 'DINHEIRO', 'valor': Decimal('1700'),
                     'numero_parcelas': 1, 'aut_id': None}],
        usuario='t')
    _db.session.refresh(venda)
    chassis = {it.numero_chassi for it in venda.itens}
    assert chassis == {c1, c3}
    assert venda.valor_total == Decimal('1700')
    assert venda.status == 'COTACAO'  # soma pagamentos == total -> nao INCOMPLETO
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/hora/test_salvar_pedido_completo.py -q`
Expected: FAIL — `salvar_pedido_completo` não existe.

- [ ] **Step 3: Implementar `salvar_pedido_completo`**

```python
def salvar_pedido_completo(venda_id, header, itens, pagamentos, usuario=None):
    venda = HoraVenda.query.get(venda_id)
    if venda is None:
        raise ValueError('Venda nao encontrada.')
    _aplicar_header(venda, header or {}, usuario)
    if venda.status == VENDA_STATUS_COTACAO:   # itens so em COTACAO
        _aplicar_itens(venda, itens or [], usuario)
    if venda.status in (VENDA_STATUS_INCOMPLETO, VENDA_STATUS_COTACAO):
        _aplicar_pagamentos(venda, pagamentos or [], usuario)
    # recalcula total + status numa passada
    venda.valor_total = sum((it.preco_final for it in venda.itens), Decimal('0'))
    venda.status = _avaliar_status_pagamento(venda)
    db.session.commit()
    return venda
```

> Ajustar imports de `VENDA_STATUS_*` e `Decimal`. `_avaliar_status_pagamento` deve aceitar a venda já com itens/pagamentos no session (flush implícito). Auditoria já é emitida pelos helpers.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/hora/test_salvar_pedido_completo.py tests/hora/test_pedido_workflow.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/hora/services/venda_service.py tests/hora/test_salvar_pedido_completo.py
git commit -m "feat(hora): salvar_pedido_completo reconcilia pedido numa transacao [Fase 3]"
```

### Task 8: Rota `vendas_salvar_pedido` + edição usa `_lista_motos.html`

**Files:**
- Modify: `app/hora/routes/vendas.py` (nova rota)
- Modify: `app/templates/hora/tagplus/pedido_venda_novo.html` (branch `{% if venda %}` — edição)
- Test: `tests/hora/test_vendas_salvar_pedido_route.py` (criar)

- [ ] **Step 1: Write the failing test** (POST único)

```python
# tests/hora/test_vendas_salvar_pedido_route.py
"""Fase 3 (FU-5): POST /vendas/<id>/salvar reconcilia tudo de uma vez."""
# (reusa o setup de test_salvar_pedido_completo via helper local ou copia _setup)
# Monta data com arrays: item_id[], item_chassi[], item_valor[], pagamento_*[] + header.
# Assert resp 302 e estado reconciliado no banco.
```

> Espelhar o setup do Task 7 (loja/modelo/chassis + criar pedido 2 itens), depois `client.post(f'/hora/vendas/{venda.id}/salvar', data={...arrays...})` e checar itens/valor_total/status.

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/hora/test_vendas_salvar_pedido_route.py -q`
Expected: FAIL — rota inexistente (404/BuildError).

- [ ] **Step 3: Implementar a rota**

```python
@hora_bp.route('/vendas/<int:venda_id>/salvar', methods=['POST'])
@require_hora_perm('vendas', 'editar')
def vendas_salvar_pedido(venda_id: int):
    venda = HoraVenda.query.get_or_404(venda_id)
    # ... mesmos guards de acesso/loja das outras rotas ...
    header = {k: request.form.get(k) for k in (
        'vendedor', 'forma_pagamento', 'telefone_cliente', 'email_cliente',
        'observacoes', 'nome_cliente', 'cpf_cliente', 'cep',
        'endereco_logradouro', 'endereco_numero', 'endereco_complemento',
        'endereco_bairro', 'endereco_cidade', 'endereco_uf', 'modalidade_frete',
        'numero_parcelas', 'intervalo_parcelas_dias', 'valor_frete', 'tipo_frete_calc')}
    ids = request.form.getlist('item_id')
    chs = request.form.getlist('item_chassi')
    vals = request.form.getlist('item_valor')
    itens = []
    for i, ch in enumerate(chs):
        ch = (ch or '').strip()
        if not ch:
            continue
        item_id = ids[i] if i < len(ids) and (ids[i] or '').strip().isdigit() else None
        itens.append({'item_id': int(item_id) if item_id else None,
                      'numero_chassi': ch,
                      'valor_final': _parse_decimal_form(vals[i]) if i < len(vals) and vals[i] else None})
    # pagamentos: reusar o parser de vendas_pagamentos_editar
    pagamentos = _parse_pagamentos_form(request.form)
    try:
        venda_service.salvar_pedido_completo(venda_id=venda.id, header=header,
                                             itens=itens, pagamentos=pagamentos,
                                             usuario=_operador_atual())
        flash('Pedido salvo.', 'success')
    except (ValueError, venda_service.TransicaoInvalidaError,
            venda_service.ChassiIndisponivelError) as exc:
        flash(f'Erro: {exc}', 'danger')
    return redirect(url_for('hora.vendas_detalhe', venda_id=venda.id))
```

> Extrair `_parse_pagamentos_form(form)` do corpo de `vendas_pagamentos_editar` (DRY).

- [ ] **Step 4: Editar a tela de edição** (`{% if venda %}`): trocar a tabela de itens + form "adicionar moto" + forms granulares (`#form-pedido-venda` header, pagamentos, collapses de item) por **1 form** `#form-salvar-pedido` (action `vendas_salvar_pedido`) contendo: header + `{% include 'hora/tagplus/_lista_motos.html' %}` (com `itens = venda.itens`, `somente_leitura = ro_oper`) + pagamentos + **1 botão "Salvar Pedido"**. Os forms granulares saem (rotas ficam deprecadas — Task 8.5 não as remove). Transições/peças/definir-loja permanecem como estão.

- [ ] **Step 5: Run tests + smoke render dos status**

Run: `python -m pytest tests/hora/test_vendas_salvar_pedido_route.py -q` e smoke de render (Task 10).
Expected: PASS / 200.

- [ ] **Step 6: Commit**

```bash
git add app/hora/routes/vendas.py app/templates/hora/tagplus/pedido_venda_novo.html tests/hora/test_vendas_salvar_pedido_route.py
git commit -m "feat(hora): rota+tela edicao com Salvar Pedido unico (reconciliador) [Fase 3]"
```

---

## Fase 4 — Cleanup + regressão

### Task 9: Validação visual (Playwright)

**Files:**
- Test: validação manual via Playwright (login bot `claude-visual@bot.nacom.com.br`).

- [ ] **Step 1:** Criar pedido com 2 motos (adicionar linha, escolher chassi via autocomplete clicável, valores) → salvar → conferir 2 itens.
- [ ] **Step 2:** Editar o pedido (COTAÇÃO): remover 1 moto, adicionar outra, mudar valor, mudar pagamentos → 1 clique "Salvar Pedido" → conferir reconciliação e status.
- [ ] **Step 3:** Abrir pedido CONFIRMADO/FATURADO → lista e pagamentos read-only; "Salvar Pedido" só altera campos permitidos. Zero erros de console.

### Task 10: Smoke de render dos 5 status + regressão

**Files:**
- Test: `tests/hora/test_pedido_venda_render_status.py` (criar)

- [ ] **Step 1: Write smoke tests** — para cada status (INCOMPLETO/COTACAO/CONFIRMADO/FATURADO/CANCELADO) criar venda no status e `client.get(f'/hora/vendas/{id}')` → 200, sem 500, contendo `Salvar Pedido` (ou ausência quando CANCELADO).
- [ ] **Step 2: Run** `python -m pytest tests/hora/test_pedido_venda_render_status.py -q` → PASS.
- [ ] **Step 3: Commit** `git commit -m "test(hora): smoke render dos 5 status do Pedido de Venda [Fase 4]"`.

### Task 11: Documentação (CLAUDE.md §21 + INDEX já feitos)

**Files:**
- Modify: `app/hora/CLAUDE.md` (nova seção §21 descrevendo a unificação multi-item + submit único; nota de deprecação das 5 rotas; FU-1 já entregue).

- [ ] **Step 1:** Escrever §21 (espelha §20). **Step 2:** Commit `docs(hora): §21 unificacao multi-item + submit unico [Fase 4]`.

---

## Self-Review (cobertura da spec)

- FU-2 (área igual): Task 3 (`_lista_motos.html`), Task 5 (criação usa), Task 8 (edição usa). ✓
- FU-3 (N motos criação): Task 1 (`itens=`), Task 2 (rota arrays), Task 5 (UI). ✓
- FU-5 (Salvar único): Task 7 (`salvar_pedido_completo`), Task 8 (rota+tela). ✓
- Gap itens↔pagamentos: Task 7 (recalcula status numa passada). ✓
- Retrocompat dos testes: Task 1 (`itens` opcional), Task 6 (wrappers helper+commit). ✓
- Decisões #3 (peças inline) e #4 (rotas deprecadas, só forms saem): Task 8 não remove rotas. ✓
- Read-only por status: Task 3 (`somente_leitura`), Task 8 (passa `ro_oper`), Task 10 (smoke). ✓
