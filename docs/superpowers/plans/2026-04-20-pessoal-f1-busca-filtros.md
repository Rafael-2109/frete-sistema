# Pessoal F1 — Busca Global e Filtros Avançados

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Permitir busca combinada em transações pessoais via querystring shareable, com filtros de valor, categoria presente/ausente, e índice GIN trigram acelerando ILIKE.

**Architecture:** Extende `/pessoal/transacoes` (rota `listar()`) aceitando novos query params. UI ganha segunda linha de filtros colapsável e botão "Salvar busca" (localStorage). Extensão `pg_trgm` do PostgreSQL acelera ILIKE em `historico_completo` quando a tabela cresce.

**Tech Stack:** Flask, SQLAlchemy, PostgreSQL + pg_trgm, Jinja2, pytest (PostgreSQL real via conftest), Bootstrap 5, jQuery, localStorage.

**Spec:** `docs/superpowers/specs/2026-04-20-pessoal-evolucao-fases-design.md` (seção "Fase 1").

---

## File Structure

| Arquivo | Responsabilidade | Criar/Modificar |
|---|---|---|
| `tests/pessoal/__init__.py` | Marca package | **Criar** |
| `tests/pessoal/conftest.py` | Fixtures: membro, categoria, conta, transacao, client logado | **Criar** |
| `tests/pessoal/test_transacoes_filtros.py` | Testes unit + integration dos novos filtros | **Criar** |
| `scripts/migrations/pessoal_transacoes_trgm.sql` | Extensão pg_trgm + índice GIN idempotente | **Criar** |
| `scripts/migrations/pessoal_transacoes_trgm.py` | Runner com verificação before/after | **Criar** |
| `app/pessoal/routes/transacoes.py` | Adicionar filtros `valor_min`, `valor_max`, `tem_categoria` na `listar()` | **Modificar** `listar()` |
| `app/templates/pessoal/transacoes.html` | Nova linha de filtros + toggle colapsável + salvar busca localStorage | **Modificar** topo do template |

---

## Task 1: Infraestrutura de testes do módulo pessoal

**Files:**
- Create: `tests/pessoal/__init__.py`
- Create: `tests/pessoal/conftest.py`

- [ ] **Step 1: Criar o package**

```bash
touch tests/pessoal/__init__.py
```

- [ ] **Step 2: Criar conftest com fixtures reutilizáveis**

Arquivo: `tests/pessoal/conftest.py`

```python
"""Fixtures compartilhadas para tests do módulo pessoal."""
from datetime import date
from decimal import Decimal

import pytest

from app import db as _db
from app.pessoal.models import (
    PessoalMembro, PessoalConta, PessoalCategoria,
    PessoalImportacao, PessoalTransacao,
)


@pytest.fixture
def membro(db):
    m = PessoalMembro(nome='Teste', ativo=True)
    _db.session.add(m)
    _db.session.commit()
    return m


@pytest.fixture
def categoria_alimentacao(db):
    c = PessoalCategoria(nome='Mercado', grupo='Alimentacao', ativa=True)
    _db.session.add(c)
    _db.session.commit()
    return c


@pytest.fixture
def categoria_transporte(db):
    c = PessoalCategoria(nome='Uber', grupo='Transporte', ativa=True)
    _db.session.add(c)
    _db.session.commit()
    return c


@pytest.fixture
def conta(db, membro):
    c = PessoalConta(
        nome='CC Bradesco Teste',
        tipo='conta_corrente',
        banco='bradesco',
        membro_id=membro.id,
        ativa=True,
    )
    _db.session.add(c)
    _db.session.commit()
    return c


@pytest.fixture
def importacao(db, conta):
    imp = PessoalImportacao(
        conta_id=conta.id,
        nome_arquivo='teste.csv',
        tipo_arquivo='extrato_cc',
        total_linhas=0,
        linhas_importadas=0,
        status='IMPORTADO',
    )
    _db.session.add(imp)
    _db.session.commit()
    return imp


def _transacao_factory(db, importacao, conta, **kwargs):
    """Cria transação com defaults razoáveis."""
    defaults = {
        'importacao_id': importacao.id,
        'conta_id': conta.id,
        'data': date(2026, 4, 1),
        'historico': 'TESTE PADRAO',
        'descricao': None,
        'historico_completo': 'TESTE PADRAO',
        'valor': Decimal('100.00'),
        'tipo': 'debito',
        'status': 'PENDENTE',
        'excluir_relatorio': False,
        'hash_transacao': f'hash_{id(defaults)}',
    }
    defaults.update(kwargs)
    # Garantir hash único se não informado
    if 'hash_transacao' not in kwargs:
        defaults['hash_transacao'] = (
            f"hash_{defaults['data']}_{defaults['historico']}_{defaults['valor']}"
        )
    t = PessoalTransacao(**defaults)
    _db.session.add(t)
    _db.session.commit()
    return t


@pytest.fixture
def make_transacao(db, importacao, conta):
    """Factory para criar transações customizadas no teste."""
    def _factory(**kwargs):
        return _transacao_factory(_db, importacao, conta, **kwargs)
    return _factory


@pytest.fixture
def client_autorizado(app, client, monkeypatch):
    """Client com pode_acessar_pessoal=True (bypass da lista de IDs)."""
    from app.pessoal import pode_acessar_pessoal  # noqa

    monkeypatch.setattr(
        'app.pessoal.routes.transacoes.pode_acessar_pessoal',
        lambda user: True,
    )
    return client
```

- [ ] **Step 3: Rodar um smoke test — importar fixtures sem erro**

Arquivo temporário para validar (deletar depois): `tests/pessoal/test_fixtures_smoke.py`

```python
def test_fixtures_carregam(membro, categoria_alimentacao, conta, importacao, make_transacao):
    t = make_transacao()
    assert t.id is not None
    assert t.valor == 100
```

Run: `source .venv/bin/activate && pytest tests/pessoal/test_fixtures_smoke.py -v`
Expected: 1 passed

- [ ] **Step 4: Remover arquivo de smoke e commitar**

```bash
rm tests/pessoal/test_fixtures_smoke.py
git add tests/pessoal/__init__.py tests/pessoal/conftest.py
git commit -m "test(pessoal): infra de testes do modulo pessoal

Adiciona package tests/pessoal/ com fixtures reutilizaveis: membro,
conta, categoria, importacao, make_transacao factory, client autorizado.
Prepara terreno para testes dos filtros de F1 e proximas fases.
"
```

---

## Task 2: Migration — índice GIN pg_trgm

**Files:**
- Create: `scripts/migrations/pessoal_transacoes_trgm.sql`
- Create: `scripts/migrations/pessoal_transacoes_trgm.py`

- [ ] **Step 1: Criar SQL idempotente**

Arquivo: `scripts/migrations/pessoal_transacoes_trgm.sql`

```sql
-- Migration: indice GIN trigram para busca por substring rapida em
-- pessoal_transacoes.historico_completo.

CREATE EXTENSION IF NOT EXISTS pg_trgm;

CREATE INDEX IF NOT EXISTS idx_pessoal_transacoes_hist_completo_trgm
    ON pessoal_transacoes
    USING gin (historico_completo gin_trgm_ops);
```

- [ ] **Step 2: Criar runner Python com verificação**

Arquivo: `scripts/migrations/pessoal_transacoes_trgm.py`

```python
"""
Migration: extensao pg_trgm + indice GIN em pessoal_transacoes.historico_completo.

Acelera buscas ILIKE '%texto%' na tabela de transacoes pessoais.

Executar: python scripts/migrations/pessoal_transacoes_trgm.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text, inspect


INDICE_NOME = 'idx_pessoal_transacoes_hist_completo_trgm'


def _indice_existe():
    rows = db.session.execute(text("""
        SELECT 1
          FROM pg_indexes
         WHERE schemaname = 'public'
           AND tablename = 'pessoal_transacoes'
           AND indexname = :nome
    """), {'nome': INDICE_NOME}).fetchall()
    return bool(rows)


def _extensao_existe():
    rows = db.session.execute(text("""
        SELECT 1 FROM pg_extension WHERE extname = 'pg_trgm'
    """)).fetchall()
    return bool(rows)


def migrar():
    app = create_app()
    with app.app_context():
        print("=" * 60)
        print("MIGRATION: pessoal_transacoes pg_trgm")
        print("=" * 60)

        ext_antes = _extensao_existe()
        idx_antes = _indice_existe()
        print(f"\n[BEFORE] extensao pg_trgm: {ext_antes}")
        print(f"[BEFORE] indice {INDICE_NOME}: {idx_antes}")

        if not ext_antes:
            print("\n[1/2] Criando extensao pg_trgm...")
            db.session.execute(text("CREATE EXTENSION IF NOT EXISTS pg_trgm;"))
        else:
            print("\n[1/2] Extensao pg_trgm ja existe.")

        if not idx_antes:
            print("\n[2/2] Criando indice GIN trigram...")
            db.session.execute(text(f"""
                CREATE INDEX IF NOT EXISTS {INDICE_NOME}
                  ON pessoal_transacoes
                  USING gin (historico_completo gin_trgm_ops);
            """))
        else:
            print("\n[2/2] Indice ja existe.")

        db.session.commit()

        print("\n" + "=" * 60)
        print(f"[AFTER] extensao pg_trgm: {_extensao_existe()}")
        print(f"[AFTER] indice {INDICE_NOME}: {_indice_existe()}")
        print("=" * 60)
        print("\nMigration concluida!")


if __name__ == '__main__':
    migrar()
```

- [ ] **Step 3: Executar localmente**

Run: `source .venv/bin/activate && python scripts/migrations/pessoal_transacoes_trgm.py`
Expected: saída "[AFTER] extensao pg_trgm: True" e "[AFTER] indice ... True"

- [ ] **Step 4: Commitar**

```bash
git add scripts/migrations/pessoal_transacoes_trgm.sql scripts/migrations/pessoal_transacoes_trgm.py
git commit -m "feat(pessoal): indice GIN pg_trgm em historico_completo

Acelera ILIKE '%texto%' na busca global F1. Migration idempotente
SQL + Python com verificacao before/after."
```

---

## Task 3: Filtro `valor_min` e `valor_max` — teste primeiro

**Files:**
- Modify: `app/pessoal/routes/transacoes.py` (função `listar()`)
- Test: `tests/pessoal/test_transacoes_filtros.py`

- [ ] **Step 1: Criar teste que falha**

Arquivo: `tests/pessoal/test_transacoes_filtros.py`

```python
"""Testes dos filtros de F1 (busca global e filtros avançados) em /pessoal/transacoes."""
from datetime import date
from decimal import Decimal

import pytest


@pytest.mark.integration
def test_filtro_valor_min_retorna_apenas_acima(
    client_autorizado, make_transacao, categoria_alimentacao,
):
    make_transacao(historico='COMPRA PEQUENA', valor=Decimal('50.00'),
                   hash_transacao='h1')
    make_transacao(historico='COMPRA MEDIA', valor=Decimal('300.00'),
                   hash_transacao='h2')
    make_transacao(historico='COMPRA GRANDE', valor=Decimal('1200.00'),
                   hash_transacao='h3')

    resp = client_autorizado.get('/pessoal/transacoes?valor_min=200')

    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'COMPRA MEDIA' in body
    assert 'COMPRA GRANDE' in body
    assert 'COMPRA PEQUENA' not in body


@pytest.mark.integration
def test_filtro_valor_max_retorna_apenas_abaixo(client_autorizado, make_transacao):
    make_transacao(historico='BARATO', valor=Decimal('50.00'), hash_transacao='a1')
    make_transacao(historico='CARO', valor=Decimal('999.00'), hash_transacao='a2')

    resp = client_autorizado.get('/pessoal/transacoes?valor_max=100')

    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'BARATO' in body
    assert 'CARO' not in body


@pytest.mark.integration
def test_filtro_valor_min_e_max_range(client_autorizado, make_transacao):
    make_transacao(historico='MIN', valor=Decimal('10.00'), hash_transacao='r1')
    make_transacao(historico='MEIO', valor=Decimal('500.00'), hash_transacao='r2')
    make_transacao(historico='MAX', valor=Decimal('2000.00'), hash_transacao='r3')

    resp = client_autorizado.get('/pessoal/transacoes?valor_min=100&valor_max=1000')

    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'MEIO' in body
    assert 'MIN' not in body
    assert 'MAX' not in body
```

- [ ] **Step 2: Rodar testes — devem falhar**

Run: `source .venv/bin/activate && pytest tests/pessoal/test_transacoes_filtros.py -v`
Expected: 3 FAILED — rota ainda não implementa `valor_min`/`valor_max`.

- [ ] **Step 3: Implementar filtro na rota**

Arquivo: `app/pessoal/routes/transacoes.py`, dentro de `listar()`, logo após a leitura do `busca`:

Adicionar (antes do bloco `query = PessoalTransacao.query`):

```python
    valor_min = request.args.get('valor_min', type=float)
    valor_max = request.args.get('valor_max', type=float)
```

E no bloco de aplicação de filtros (após `if busca:`), adicionar:

```python
    if valor_min is not None:
        query = query.filter(PessoalTransacao.valor >= valor_min)
    if valor_max is not None:
        query = query.filter(PessoalTransacao.valor <= valor_max)
```

E no dict `filtros` passado ao template, incluir:

```python
            'valor_min': valor_min,
            'valor_max': valor_max,
```

- [ ] **Step 4: Rodar testes — devem passar**

Run: `source .venv/bin/activate && pytest tests/pessoal/test_transacoes_filtros.py -v`
Expected: 3 passed

- [ ] **Step 5: Commitar**

```bash
git add app/pessoal/routes/transacoes.py tests/pessoal/test_transacoes_filtros.py
git commit -m "feat(pessoal): filtros valor_min e valor_max em /transacoes

Permite restringir listagem por faixa de valor. Filtro inclusivo em
ambas as pontas. Com testes integration (pytest PostgreSQL real)."
```

---

## Task 4: Filtro `tem_categoria` — teste primeiro

**Files:**
- Modify: `app/pessoal/routes/transacoes.py`
- Test: `tests/pessoal/test_transacoes_filtros.py`

- [ ] **Step 1: Adicionar testes**

Append em `tests/pessoal/test_transacoes_filtros.py`:

```python
@pytest.mark.integration
def test_filtro_tem_categoria_sim_exclui_sem_categoria(
    client_autorizado, make_transacao, categoria_alimentacao,
):
    make_transacao(historico='CATEGORIZADA', categoria_id=categoria_alimentacao.id,
                   hash_transacao='c1')
    make_transacao(historico='SEM CATEGORIA', hash_transacao='c2')

    resp = client_autorizado.get('/pessoal/transacoes?tem_categoria=sim')

    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'CATEGORIZADA' in body
    assert 'SEM CATEGORIA' not in body


@pytest.mark.integration
def test_filtro_tem_categoria_nao_mostra_apenas_sem_categoria(
    client_autorizado, make_transacao, categoria_alimentacao,
):
    make_transacao(historico='CATEGORIZADA2', categoria_id=categoria_alimentacao.id,
                   hash_transacao='c3')
    make_transacao(historico='PENDENTE CAT', hash_transacao='c4')

    resp = client_autorizado.get('/pessoal/transacoes?tem_categoria=nao')

    assert resp.status_code == 200
    body = resp.get_data(as_text=True)
    assert 'PENDENTE CAT' in body
    assert 'CATEGORIZADA2' not in body
```

- [ ] **Step 2: Rodar testes — devem falhar**

Run: `source .venv/bin/activate && pytest tests/pessoal/test_transacoes_filtros.py -k tem_categoria -v`
Expected: 2 FAILED

- [ ] **Step 3: Implementar filtro na rota**

Arquivo: `app/pessoal/routes/transacoes.py`, após o bloco `valor_min`/`valor_max` do Task 3:

```python
    tem_categoria = request.args.get('tem_categoria')  # 'sim' | 'nao' | None
```

E no bloco de aplicação de filtros, adicionar:

```python
    if tem_categoria == 'sim':
        query = query.filter(PessoalTransacao.categoria_id.isnot(None))
    elif tem_categoria == 'nao':
        query = query.filter(PessoalTransacao.categoria_id.is_(None))
```

E no dict `filtros`:

```python
            'tem_categoria': tem_categoria,
```

- [ ] **Step 4: Rodar testes — devem passar**

Run: `source .venv/bin/activate && pytest tests/pessoal/test_transacoes_filtros.py -v`
Expected: 5 passed

- [ ] **Step 5: Commitar**

```bash
git add app/pessoal/routes/transacoes.py tests/pessoal/test_transacoes_filtros.py
git commit -m "feat(pessoal): filtro tem_categoria (sim/nao) em /transacoes

Permite listar so transacoes categorizadas ou so pendentes de
categorizacao, independente do status. Com testes integration."
```

---

## Task 5: UI — segunda linha de filtros colapsável

**Files:**
- Modify: `app/templates/pessoal/transacoes.html`

Localize no template a `<form>` de filtros existente (próximo da linha 35-90). A estrutura atual tem `data_inicio`, `data_fim`, `conta_id`, `categoria_id`, `status`, `busca`. Vamos expandir.

- [ ] **Step 1: Encontrar o form atual**

Run: `grep -n 'name="busca"\|form.*get\|data_inicio' app/templates/pessoal/transacoes.html | head -10`
Expected: mostra o form e a linha do campo busca.

- [ ] **Step 2: Adicionar linha colapsável "Filtros avançados"**

Imediatamente APÓS o botão submit do form de filtros atual (procurar `<button type="submit"`), **antes** de fechar o `</form>`, adicionar:

```html
<!-- Toggle filtros avançados -->
<div class="col-12 mt-2">
  <button class="btn btn-sm btn-link p-0" type="button"
          data-bs-toggle="collapse" data-bs-target="#filtrosAvancados"
          aria-expanded="false">
    <i class="fas fa-sliders-h"></i> Filtros avançados
  </button>
  <button class="btn btn-sm btn-outline-success ms-2" type="button" id="btnSalvarBusca">
    <i class="fas fa-bookmark"></i> Salvar busca
  </button>
  <button class="btn btn-sm btn-outline-secondary ms-1" type="button" id="btnPresets" data-bs-toggle="dropdown">
    <i class="fas fa-list"></i> Presets
  </button>
  <ul class="dropdown-menu" id="presetsMenu"></ul>
</div>

<div class="collapse col-12" id="filtrosAvancados">
  <div class="row g-2 mt-1">
    <div class="col-md-2">
      <label class="form-label small mb-0">Valor min</label>
      <input type="number" step="0.01" min="0" name="valor_min"
             class="form-control form-control-sm"
             value="{{ filtros.valor_min or '' }}">
    </div>
    <div class="col-md-2">
      <label class="form-label small mb-0">Valor max</label>
      <input type="number" step="0.01" min="0" name="valor_max"
             class="form-control form-control-sm"
             value="{{ filtros.valor_max or '' }}">
    </div>
    <div class="col-md-2">
      <label class="form-label small mb-0">Tipo</label>
      <select name="tipo" class="form-select form-select-sm">
        <option value="">Todos</option>
        <option value="debito" {{ 'selected' if filtros.tipo == 'debito' }}>Debito</option>
        <option value="credito" {{ 'selected' if filtros.tipo == 'credito' }}>Credito</option>
      </select>
    </div>
    <div class="col-md-2">
      <label class="form-label small mb-0">Membro</label>
      <select name="membro_id" class="form-select form-select-sm">
        <option value="">Todos</option>
        {% for m in membros %}
        <option value="{{ m.id }}" {{ 'selected' if filtros.membro_id == m.id }}>{{ m.nome }}</option>
        {% endfor %}
      </select>
    </div>
    <div class="col-md-2">
      <label class="form-label small mb-0">Categoria</label>
      <select name="tem_categoria" class="form-select form-select-sm">
        <option value="">Qualquer</option>
        <option value="sim" {{ 'selected' if filtros.tem_categoria == 'sim' }}>Categorizada</option>
        <option value="nao" {{ 'selected' if filtros.tem_categoria == 'nao' }}>Sem categoria</option>
      </select>
    </div>
    <div class="col-md-2">
      <label class="form-label small mb-0">&nbsp;</label>
      <a href="{{ url_for('pessoal.pessoal_transacoes.listar') }}"
         class="btn btn-sm btn-outline-secondary w-100">
        <i class="fas fa-eraser"></i> Limpar filtros
      </a>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Validar render**

Run (manual, começando o servidor):
```bash
source .venv/bin/activate && python run.py
# abrir http://localhost:5000/pessoal/transacoes, clicar em "Filtros avançados"
# testar cada filtro visualmente
```
Expected: segunda linha expande; valores persistem na URL após submit.

- [ ] **Step 4: Commitar**

```bash
git add app/templates/pessoal/transacoes.html
git commit -m "feat(pessoal): UI de filtros avancados em /transacoes

Adiciona linha colapsavel com valor min/max, tipo, membro e
tem_categoria. Botoes 'Salvar busca' e 'Presets' preparados para
Task 6 (localStorage)."
```

---

## Task 6: Salvar busca em localStorage

**Files:**
- Modify: `app/templates/pessoal/transacoes.html` (bloco `<script>` no final)

- [ ] **Step 1: Encontrar o bloco `<script>` final do template**

Run: `grep -n '<script>\|</script>' app/templates/pessoal/transacoes.html | head -10`
Expected: mostra onde inserir.

- [ ] **Step 2: Adicionar JS de presets antes de `})();` do IIFE existente**

No final do IIFE existente (antes do último `})();`), adicionar:

```javascript
  // ===== Presets de busca em localStorage =====
  const PRESETS_KEY = 'pessoal_transacoes_presets';

  function carregarPresets() {
    try { return JSON.parse(localStorage.getItem(PRESETS_KEY) || '[]'); }
    catch (e) { return []; }
  }
  function salvarPresets(lista) {
    localStorage.setItem(PRESETS_KEY, JSON.stringify(lista));
  }
  function urlAtualComoQuery() {
    // Ignora filtros internos de paginacao/sort pra preset limpo
    const p = new URLSearchParams(window.location.search);
    p.delete('page');
    return p.toString();
  }
  function renderMenuPresets() {
    const menu = document.getElementById('presetsMenu');
    const lista = carregarPresets();
    menu.innerHTML = '';
    if (!lista.length) {
      const li = document.createElement('li');
      li.innerHTML = '<span class="dropdown-item-text small text-muted">Nenhum preset salvo.</span>';
      menu.appendChild(li);
      return;
    }
    lista.forEach((p, idx) => {
      const li = document.createElement('li');
      li.className = 'd-flex align-items-center ps-2 pe-2';
      const link = document.createElement('a');
      link.className = 'dropdown-item flex-grow-1 small';
      link.href = '?' + p.query;
      link.textContent = p.nome;
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'btn btn-sm btn-link text-danger p-0 ms-1';
      btn.innerHTML = '<i class="fas fa-times"></i>';
      btn.onclick = function(e) {
        e.preventDefault();
        const atual = carregarPresets();
        atual.splice(idx, 1);
        salvarPresets(atual);
        renderMenuPresets();
      };
      li.appendChild(link);
      li.appendChild(btn);
      menu.appendChild(li);
    });
  }
  document.getElementById('btnSalvarBusca').addEventListener('click', function() {
    const nome = prompt('Nome do preset:');
    if (!nome) return;
    const lista = carregarPresets();
    lista.push({ nome: nome.trim(), query: urlAtualComoQuery() });
    salvarPresets(lista);
    renderMenuPresets();
    alert('Preset salvo.');
  });
  renderMenuPresets();
```

- [ ] **Step 3: Testar manualmente**

Run: `source .venv/bin/activate && python run.py`
- Abrir `/pessoal/transacoes?valor_min=100&tipo=debito`
- Clicar "Salvar busca", nomear "Débitos acima de 100"
- Recarregar. Clicar "Presets" → item aparece e navega pro mesmo URL.
- Clicar no X ao lado do preset → remove.

Expected: funcional.

- [ ] **Step 4: Commitar**

```bash
git add app/templates/pessoal/transacoes.html
git commit -m "feat(pessoal): presets de busca em localStorage

Usuario salva/nomeia buscas frequentes sem persistir no banco. Menu
dropdown lista presets com link pro URL e botao de remover."
```

---

## Task 7: Validar cobertura e rodar suite

- [ ] **Step 1: Rodar toda a suite de pessoal**

Run: `source .venv/bin/activate && pytest tests/pessoal/ -v`
Expected: 5 passed.

- [ ] **Step 2: Rodar smoke test manual do fluxo completo**

Passos no browser:
1. Acessar `/pessoal/transacoes` → lista carrega, filtros visíveis
2. Submeter busca texto → URL reflete
3. Abrir "Filtros avançados" → segunda linha aparece
4. Preencher `valor_min=200`, `tem_categoria=sim`, submit → filtro aplica, URL tem params
5. Clicar "Salvar busca" → prompt aceita, nome salvo
6. Clicar "Presets" → preset aparece
7. Navegar pelo preset → URL idêntica ao salvo
8. Clicar "Limpar filtros" → volta pra `/pessoal/transacoes` limpo

- [ ] **Step 3: Criar um summary commit (opcional)**

Se algum step precisou ajuste, consolida com:
```bash
git log --oneline -10
```
para confirmar histórico limpo.

---

## Notas finais

**Índice pg_trgm em produção:** rodar `python scripts/migrations/pessoal_transacoes_trgm.py` no Render Shell (ou aplicar o SQL diretamente). Extensão `pg_trgm` está disponível em todos os planos PostgreSQL da Render.

**Backward compat:** nenhum filtro existente foi alterado; apenas novos foram adicionados. URLs antigas continuam funcionando.

**Dependências para próximas fases:**
- F3 (hierarquia) vai expandir o filtro `categoria_id` para incluir descendentes via `categorias_descendentes_ids()` helper — não altera esta F1.
- F2 (alertas) não depende desta fase.
