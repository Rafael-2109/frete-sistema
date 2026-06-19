<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-19
-->
# CarVia — Viabilidade no Mapa/Embarque + Cidade no Export NF + Resultado por Frete — Implementation Plan

> **Papel:** plano de implementacao (task-by-task, TDD) das 3 entregas CarVia da spec de 2026-06-19.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Dar visibilidade da viabilidade CarVia (receita vs custo) no mapa de roteirizacao e no embarque (admin-only), incluir a cidade destino no export de NF, e criar a tela+Excel "Resultado por Frete" com rateio coerente por moto.

**Architecture:** 3 entregas independentes (commits isolados, ordem 1→2→3). O calculo de receita/rateio CarVia vive DENTRO de `app/carvia` (services); carteira e embarque consomem via LAZY import (isolamento R1). O rateio reaproveita as subqueries de contagem de motos e a cascata `motos→peso→nº NFs` ja existentes em `gerencial_service.py`.

**Tech Stack:** Flask 3.1 + SQLAlchemy 2.0, openpyxl (helper `excel_export_helper`), Jinja2 + Bootstrap + jQuery (mapa standalone), pytest (fixtures `app`/`db`/`client` em `tests/conftest.py`).

## Indice

- [Contexto](#contexto)
- [Global Constraints](#global-constraints)
- [File Structure](#file-structure)
- [Task 1 — Cidade destino no export de NF](#task-1-cidade-destino-no-export-de-nf)
- [Task 2 — viabilidade_service (receita CarVia por lotes/embarque)](#task-2-viabilidade_service-receita-carvia-por-lotesembarque)
- [Task 3 — Viabilidade no Ver no Mapa](#task-3-viabilidade-no-ver-no-mapa)
- [Task 4 — Receita CarVia no Embarque (admin-only)](#task-4-receita-carvia-no-embarque-admin-only)
- [Task 5 — resultado_frete_service (rateio por NF)](#task-5-resultado_frete_service-rateio-por-nf)
- [Task 6 — Tela /carvia/resultado-frete](#task-6-tela-carviaresultado-frete)
- [Task 7 — Export Excel Resultado por Frete (2 abas)](#task-7-export-excel-resultado-por-frete-2-abas)
- [Self-Review](#self-review)

## Contexto

Implementa a spec `docs/superpowers/specs/2026-06-19-carvia-viabilidade-rateio-frete-design.md` (aprovada). O nucleo das 3 entregas e a regra de rateio coerente por NF: receita (`CarviaOperacao.cte_valor`), custo subcontrato (`Σ CarviaSubcontrato` por operacao) e custo coleta (`CarviaColeta.valor_coleta`) sao todos rateados pela mesma base de motos/NF, com cascata de fallback. Validado contra producao (MCP Render): rateio por moto confere, prejuizos reais existem, `motos=0` ocorre (exige fallback), 1 operacao pode ter N subcontratos.

## Global Constraints

- **Isolamento CarVia (R1):** `app/carvia` NAO importa `app/carteira`/`app/embarques`/`app/fretes`. Carteira e embarque consomem CarVia via **lazy import** (dentro da funcao). Copiar verbatim este padrao.
- **Timezone:** datas/timestamps via `app.utils.timezone` (`agora_brasil_naive`, `agora_utc_naive`). NUNCA `datetime.now()`.
- **Campos de tabela:** usar exatamente os nomes confirmados nos schemas (`CarviaNf.cidade_destinatario`, `CarviaOperacao.cte_valor`, `CarviaSubcontrato.{cte_valor,valor_acertado,valor_cotado}`, `CarviaColeta.valor_coleta`, `CarviaColetaNf.{carvia_nf_id,qtd_motos,coleta_id}`, `CarviaCotacao.valor_final_aprovado`).
- **Guard de tela CarVia:** `@login_required` + `if not getattr(current_user, 'sistema_carvia', False): flash(...); return redirect(url_for('main.dashboard'))`. Telas admin-only adicionam `@require_admin` (de `app/utils/auth_decorators.py`) OU checam `current_user.perfil == 'administrador'`.
- **CSRF:** POST AJAX do mapa ja usa `headers: { 'X-CSRFToken': getCSRFToken() }`. Manter.
- **Numerico BR:** filtro Jinja `valor_br` (`app/utils/template_filters.py:40`).
- **Rateio canonico:** cascata `Direto(1:1) → Motos → Peso → Qtd NFs`, `quantize(Decimal('0.01'), ROUND_HALF_UP)`, ajuste de centavos na 1ª NF. Espelha `gerencial_service._aplicar_rateio_itens` (L504-535).
- **NAO tocar** `app/carteira/main_routes.py` (regra R2 carteira).
- **Commits isolados por entrega** (Task 1 = 1 commit; Tasks 2-4 = entrega 2; Tasks 5-7 = entrega 3).

## File Structure

| Arquivo | Acao | Responsabilidade |
|---------|------|------------------|
| `app/carvia/routes/exportacao_routes.py` | Modify | +coluna `Cidade Dest` em `exportar_nfs`/`exportar_operacoes` |
| `app/carvia/services/financeiro/viabilidade_service.py` | Create | Receita CarVia somada por lotes (mapa) e por embarque |
| `app/carteira/routes/mapa_routes.py` | Modify | `rota_otimizar` retorna receita CarVia + viabilidade |
| `app/templates/carteira/mapa_pedidos.html` | Modify | Cards "CarVia (receita)" + "Viabilidade" + wiring JS |
| `app/embarques/models.py` | Modify | Metodo `Embarque.receita_carvia()` (lazy) |
| `app/templates/embarques/visualizar_embarque.html` | Modify | Badge admin-only de receita CarVia |
| `app/carvia/services/financeiro/resultado_frete_service.py` | Create | Rateio por NF (receita/custo) + resumo por eixo |
| `app/carvia/routes/resultado_frete_routes.py` | Create | Tela `/carvia/resultado-frete` + rota de export |
| `app/carvia/routes/__init__.py` | Modify | Registrar `resultado_frete_routes` |
| `app/templates/carvia/resultado_frete/index.html` | Create | Tela: filtros + resumo + detalhe |
| `tests/carvia/test_export_nf_cidade.py` | Create | Teste Task 1 |
| `tests/carvia/test_viabilidade_service.py` | Create | Teste Task 2 |
| `tests/carvia/test_resultado_frete_service.py` | Create | Testes Task 5 |
| `tests/carvia/test_resultado_frete_routes.py` | Create | Teste Tasks 6/7 |

Helpers de teste reusados em todos os testes novos (copiar de `tests/carvia/test_a1_a2_linking.py`):
`_gerar_chave_44()`, `_criar_operacao(db, cte_numero, cte_valor)`, `_criar_nf(db, numero_nf, ...)`, `_criar_junction(db, operacao_id, nf_id)`. Login mock de `tests/carvia/test_coleta_routes.py`: `patch('flask_login.utils._get_user', return_value=_user())` com `_user().sistema_carvia=True`, `.perfil='administrador'`.

---

## Task 1 — Cidade destino no export de NF

**Files:**
- Modify: `app/carvia/routes/exportacao_routes.py` (`exportar_nfs` ~L390/L446; `exportar_operacoes` ~L611/L657)
- Test: `tests/carvia/test_export_nf_cidade.py`

**Interfaces:**
- Consumes: `CarviaNf.cidade_destinatario` (varchar 100). Helper `Campo`/`ColunaGrupo`/`gerar_excel_duplo_cabecalho` (ja importados no arquivo).
- Produces: coluna `Cidade Dest` no grupo `NF` dos dois exports, posicionada ANTES de `UF`.

- [ ] **Step 1: Write the failing test**

```python
# tests/carvia/test_export_nf_cidade.py
from io import BytesIO
from datetime import datetime
from decimal import Decimal
from unittest.mock import MagicMock, patch

from openpyxl import load_workbook


def _user():
    u = MagicMock()
    u.is_authenticated = True
    u.sistema_carvia = True
    u.perfil = 'administrador'
    u.email = 'test@bot'
    return u


def _criar_nf_simples(db, numero, cidade, uf):
    from app.carvia.models import CarviaNf
    nf = CarviaNf(
        numero_nf=numero,
        cnpj_emitente='11111111000111',
        nome_emitente='EMIT T',
        cnpj_destinatario='22222222000122',
        nome_destinatario='DEST T',
        uf_destinatario=uf,
        cidade_destinatario=cidade,
        data_emissao=datetime(2026, 1, 10).date(),
        valor_total=Decimal('500.00'),
        peso_bruto=Decimal('100.000'),
        status='ATIVA',
        tipo_fonte='MANUAL',
        criado_por='test',
    )
    db.session.add(nf)
    db.session.flush()
    return nf


def test_export_nfs_inclui_cidade_destino(db, client):
    _criar_nf_simples(db, '99001', 'RIBEIRAO PRETO', 'SP')
    with patch('flask_login.utils._get_user', return_value=_user()):
        r = client.get('/carvia/api/exportar/nfs')
    assert r.status_code == 200
    wb = load_workbook(BytesIO(r.data))
    ws = wb.active
    headers = [c.value for c in ws[2]]  # linha 2 = campos
    assert 'Cidade Dest' in headers
    valores = [c.value for row in ws.iter_rows(min_row=3) for c in row]
    assert 'RIBEIRAO PRETO' in valores
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/carvia/test_export_nf_cidade.py -v`
Expected: FAIL — `assert 'Cidade Dest' in headers` (coluna ainda nao existe).

- [ ] **Step 3: Implement — `exportar_nfs`**

Em `app/carvia/routes/exportacao_routes.py`, no dict de dados de `exportar_nfs` (apos `'nf_uf_dest': nf.uf_destinatario or '',` ~L390) adicionar:

```python
                    'nf_cidade_dest': nf.cidade_destinatario or '',
```

E na lista `colunas` do grupo `NF`, inserir o Campo ANTES de `Campo('nf_uf_dest', 'UF')` (~L446):

```python
                Campo('nf_cidade_dest', 'Cidade Dest'),
                Campo('nf_uf_dest', 'UF'),
```

- [ ] **Step 4: Implement — `exportar_operacoes`**

No dict de dados de `exportar_operacoes` (apos `'nf_uf_dest': (nf.uf_destinatario if nf else op.uf_destino or '') or '',` ~L611):

```python
                    'nf_cidade_dest': (nf.cidade_destinatario if nf else op.cidade_destino or '') or '',
```

E no grupo `NF` de `colunas` (~L657), antes de `Campo('nf_uf_dest', 'UF')`:

```python
                Campo('nf_cidade_dest', 'Cidade Dest'),
                Campo('nf_uf_dest', 'UF'),
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/carvia/test_export_nf_cidade.py -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add app/carvia/routes/exportacao_routes.py tests/carvia/test_export_nf_cidade.py
git commit -m "feat(carvia): cidade destino no export Excel de NFs e Operacoes"
```

---

## Task 2 — viabilidade_service (receita CarVia por lotes/embarque)

**Files:**
- Create: `app/carvia/services/financeiro/viabilidade_service.py`
- Test: `tests/carvia/test_viabilidade_service.py`

**Interfaces:**
- Produces:
  - `receita_carvia_por_lotes(lotes: list[str]) -> dict` → `{'total': float, 'por_lote': {lote: {'valor': float, 'fonte': 'CTE'|'COTACAO'|'SEM'}}}`
  - `receita_carvia_por_embarque(embarque_id: int) -> dict` → `{'total': float, 'tem_cte': bool}`
- Lotes aceitos: `CARVIA-PED-{id}`, `CARVIA-{cot_id}`, `CARVIA-NF-{id}`; qualquer outro → `'SEM'`, 0.

- [ ] **Step 1: Write the failing test**

```python
# tests/carvia/test_viabilidade_service.py
from datetime import datetime
from decimal import Decimal


def _criar_operacao(db, cte_numero, cte_valor):
    from app.carvia.models import CarviaOperacao
    op = CarviaOperacao(
        cte_numero=cte_numero, cte_valor=Decimal(str(cte_valor)),
        cte_data_emissao=datetime(2026, 1, 5).date(),
        cnpj_cliente='12345678000100', nome_cliente='C',
        uf_origem='SP', cidade_origem='SAO PAULO',
        uf_destino='RJ', cidade_destino='RIO DE JANEIRO',
        status='RASCUNHO', tipo_entrada='IMPORTADO', criado_por='test',
    )
    db.session.add(op); db.session.flush()
    return op


def _criar_nf(db, numero):
    from app.carvia.models import CarviaNf
    nf = CarviaNf(
        numero_nf=numero, cnpj_emitente='11111111000111', nome_emitente='E',
        cnpj_destinatario='22222222000122', nome_destinatario='D',
        data_emissao=datetime(2026, 1, 5).date(), valor_total=Decimal('500'),
        status='ATIVA', tipo_fonte='MANUAL', criado_por='test',
    )
    db.session.add(nf); db.session.flush()
    return nf


def test_receita_por_lote_nf_usa_cte(db):
    from app.carvia.models import CarviaOperacaoNf
    from app.carvia.services.financeiro.viabilidade_service import receita_carvia_por_lotes
    op = _criar_operacao(db, 'CTe-V1', 1200.0)
    nf = _criar_nf(db, '70001')
    db.session.add(CarviaOperacaoNf(operacao_id=op.id, nf_id=nf.id)); db.session.flush()

    res = receita_carvia_por_lotes([f'CARVIA-NF-{nf.id}'])
    assert res['total'] == 1200.0
    assert res['por_lote'][f'CARVIA-NF-{nf.id}']['fonte'] == 'CTE'


def test_lote_nacom_e_zero(db):
    from app.carvia.services.financeiro.viabilidade_service import receita_carvia_por_lotes
    res = receita_carvia_por_lotes(['LOTE_NACOM_123'])
    assert res['total'] == 0.0
    assert res['por_lote']['LOTE_NACOM_123']['fonte'] == 'SEM'
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/carvia/test_viabilidade_service.py -v`
Expected: FAIL — `ModuleNotFoundError: viabilidade_service`.

- [ ] **Step 3: Implement the service**

```python
# app/carvia/services/financeiro/viabilidade_service.py
"""Receita CarVia agregada para a tela de viabilidade (mapa + embarque).

Receita = CTe (CarviaOperacao.cte_valor) quando ja existe; senao o valor cotado
do frete (CarviaCotacao.valor_final_aprovado). NAO faz rateio — soma bruta.
"""
from app import db


def _receita_lote(lote):
    """(valor: float, fonte: 'CTE'|'COTACAO'|'SEM') para um separacao_lote_id."""
    from app.carvia.models import CarviaNf, CarviaOperacao, CarviaOperacaoNf
    from app.carvia.models.cotacao import CarviaCotacao, CarviaPedido

    if lote.startswith('CARVIA-PED-'):
        ped = CarviaPedido.query.get(int(lote.replace('CARVIA-PED-', '')))
        if not ped:
            return 0.0, 'SEM'
        ops = [o for o in ped.operacoes_ctes if o.cte_valor]
        if ops:
            return float(sum(o.cte_valor for o in ops)), 'CTE'
        cot = CarviaCotacao.query.get(ped.cotacao_id) if ped.cotacao_id else None
        if cot and cot.valor_final_aprovado:
            return float(cot.valor_final_aprovado), 'COTACAO'
        return 0.0, 'SEM'

    if lote.startswith('CARVIA-NF-'):
        nf = CarviaNf.query.get(int(lote.replace('CARVIA-NF-', '')))
        if not nf:
            return 0.0, 'SEM'
        op = (
            db.session.query(CarviaOperacao)
            .join(CarviaOperacaoNf, CarviaOperacaoNf.operacao_id == CarviaOperacao.id)
            .filter(CarviaOperacaoNf.nf_id == nf.id, CarviaOperacao.status != 'CANCELADO')
            .first()
        )
        if op and op.cte_valor:
            return float(op.cte_valor), 'CTE'
        return 0.0, 'SEM'

    if lote.startswith('CARVIA-'):  # CARVIA-{cot_id}
        try:
            cot_id = int(lote.replace('CARVIA-', ''))
        except ValueError:
            return 0.0, 'SEM'
        cot = CarviaCotacao.query.get(cot_id)
        if cot:
            valor = cot.valor_final_aprovado or cot.valor_manual or cot.valor_tabela
            if valor:
                return float(valor), 'COTACAO'
        return 0.0, 'SEM'

    return 0.0, 'SEM'  # lote NACOM


def receita_carvia_por_lotes(lotes):
    por_lote = {}
    total = 0.0
    for lote in (lotes or []):
        valor, fonte = _receita_lote(lote)
        por_lote[lote] = {'valor': round(valor, 2), 'fonte': fonte}
        total += valor
    return {'total': round(total, 2), 'por_lote': por_lote}


def receita_carvia_por_embarque(embarque_id):
    """Soma cte_valor das operacoes vinculadas ao embarque via CarviaFrete."""
    from app.carvia.models import CarviaFrete, CarviaOperacao
    if not embarque_id:
        return {'total': 0.0, 'tem_cte': False}
    op_ids = {
        fid for (fid,) in db.session.query(CarviaFrete.operacao_id)
        .filter(CarviaFrete.embarque_id == embarque_id, CarviaFrete.operacao_id.isnot(None))
        .distinct().all()
    }
    if not op_ids:
        return {'total': 0.0, 'tem_cte': False}
    ops = (
        db.session.query(CarviaOperacao)
        .filter(CarviaOperacao.id.in_(op_ids), CarviaOperacao.status != 'CANCELADO')
        .all()
    )
    total = float(sum(o.cte_valor for o in ops if o.cte_valor))
    return {'total': round(total, 2), 'tem_cte': any(o.cte_valor for o in ops)}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/carvia/test_viabilidade_service.py -v`
Expected: PASS (2 testes).

- [ ] **Step 5: Commit**

```bash
git add app/carvia/services/financeiro/viabilidade_service.py tests/carvia/test_viabilidade_service.py
git commit -m "feat(carvia): viabilidade_service — receita CarVia por lotes e por embarque"
```

---

## Task 3 — Viabilidade no Ver no Mapa

**Files:**
- Modify: `app/carteira/routes/mapa_routes.py` (`rota_otimizar`, L521-595)
- Modify: `app/templates/carteira/mapa_pedidos.html` (`#custoRotaRow` L153-161; `recalcularRota` L1114; `preencherCardCusto` L1165)

**Interfaces:**
- Consumes: `receita_carvia_por_lotes(lotes)` (Task 2). `data.get('lotes')` enviado pelo front.
- Produces: resposta JSON de `/carteira/mapa/api/rota/otimizar` ganha `carvia_receita_total: float`, `carvia_por_lote: dict`, `viabilidade: float`.

- [ ] **Step 1: Write the failing test (backend contract)**

```python
# tests/carvia/test_viabilidade_service.py  (acrescentar)
def test_receita_por_lotes_soma_multiplos(db):
    from app.carvia.models import CarviaOperacaoNf
    from app.carvia.services.financeiro.viabilidade_service import receita_carvia_por_lotes
    op1 = _criar_operacao(db, 'CTe-V2', 300.0); nf1 = _criar_nf(db, '70010')
    op2 = _criar_operacao(db, 'CTe-V3', 700.0); nf2 = _criar_nf(db, '70011')
    db.session.add(CarviaOperacaoNf(operacao_id=op1.id, nf_id=nf1.id))
    db.session.add(CarviaOperacaoNf(operacao_id=op2.id, nf_id=nf2.id))
    db.session.flush()
    res = receita_carvia_por_lotes([f'CARVIA-NF-{nf1.id}', f'CARVIA-NF-{nf2.id}', 'LOTE_X'])
    assert res['total'] == 1000.0
```

- [ ] **Step 2: Run test to verify it passes (service ja existe)**

Run: `pytest tests/carvia/test_viabilidade_service.py::test_receita_por_lotes_soma_multiplos -v`
Expected: PASS (o service da Task 2 ja trata lista de lotes). Se FAIL, corrigir Task 2 antes.

- [ ] **Step 3: Backend — `rota_otimizar`**

Em `app/carteira/routes/mapa_routes.py`, dentro de `rota_otimizar`, apos `total = round(custo.get('custo_operacional', 0) + valor_pedagio, 2)` (~L571), adicionar:

```python
        # Receita CarVia dos lotes selecionados (viabilidade pre-embarque)
        from app.carvia.services.financeiro.viabilidade_service import receita_carvia_por_lotes
        carvia = receita_carvia_por_lotes(data.get('lotes') or [])
```

No dict do `return jsonify({...})`, adicionar 3 chaves (apos `'pedagio': ...`):

```python
            'carvia_receita_total': carvia['total'],
            'carvia_por_lote': carvia['por_lote'],
            'viabilidade': round(carvia['total'] - total, 2),
```

- [ ] **Step 4: Frontend — payload com lotes**

Em `app/templates/carteira/mapa_pedidos.html`, dentro de `recalcularRota` (~L1134, apos `if (veiculoId) payload.veiculo_id = ...`):

```javascript
            payload.lotes = _lotesSelecionados();
```

- [ ] **Step 5: Frontend — nova row de viabilidade**

Apos o fechamento de `#custoRotaRow` (`</div>` da L161), inserir:

```html
        <!-- Viabilidade CarVia (receita CTe/cotacao vs custo da rota) -->
        <div class="row mb-3" id="viabilidadeRow" style="display: none;">
            <div class="col-md-3"><div class="stats-card bg-primary text-white"><div class="stat-value" id="carviaReceita">R$ 0</div><div class="stat-label">CarVia (receita)</div></div></div>
            <div class="col-md-3"><div class="stats-card text-white" id="viabilidadeCard"><div class="stat-value" id="viabilidadeValor">R$ 0</div><div class="stat-label">Viabilidade (receita − custo)</div></div></div>
        </div>
```

- [ ] **Step 6: Frontend — preencher cards**

Em `preencherCardCusto` (~L1184, antes de `$('#custoRotaRow').show();`):

```javascript
            if (resp.carvia_receita_total !== undefined && resp.carvia_receita_total > 0) {
                $('#carviaReceita').text(fmt(resp.carvia_receita_total));
                const viab = resp.viabilidade || 0;
                $('#viabilidadeValor').text(fmt(viab));
                $('#viabilidadeCard').removeClass('bg-success bg-danger')
                    .addClass(viab >= 0 ? 'bg-success' : 'bg-danger');
                $('#viabilidadeRow').show();
            } else {
                $('#viabilidadeRow').hide();
            }
```

- [ ] **Step 7: Run service test + manual smoke**

Run: `pytest tests/carvia/test_viabilidade_service.py -v` → PASS.
Manual: abrir `/carteira/mapa/visualizar` com lotes CarVia selecionados, recalcular rota, confirmar visualmente a row "CarVia (receita)" + "Viabilidade" (verde/vermelho). (Use a skill `run` para subir o app se desejar.)

- [ ] **Step 8: Commit**

```bash
git add app/carteira/routes/mapa_routes.py app/templates/carteira/mapa_pedidos.html tests/carvia/test_viabilidade_service.py
git commit -m "feat(carteira): viabilidade CarVia (receita vs custo) no Ver no Mapa"
```

---

## Task 4 — Receita CarVia no Embarque (admin-only)

**Files:**
- Modify: `app/embarques/models.py` (classe `Embarque`, apos `total_valor_pedidos` ~L139)
- Modify: `app/templates/embarques/visualizar_embarque.html` (card-header ~L130-141)

**Interfaces:**
- Consumes: `receita_carvia_por_embarque(embarque_id)` (Task 2).
- Produces: `Embarque.receita_carvia() -> dict` (`{'total': float, 'tem_cte': bool}`).

- [ ] **Step 1: Write the failing test**

```python
# tests/carvia/test_viabilidade_service.py  (acrescentar)
def test_embarque_receita_carvia_metodo(db):
    from app.embarques.models import Embarque
    from app.transportadoras.models import Transportadora
    from app.carvia.models import CarviaFrete

    op = _criar_operacao(db, 'CTe-EMB', 2500.0)
    emb = Embarque(numero=990001, status='ativo')
    db.session.add(emb); db.session.flush()
    transp = Transportadora(razao_social='T CARVIA', cnpj='33333333000133')
    db.session.add(transp); db.session.flush()
    cf = CarviaFrete(
        transportadora_id=transp.id, embarque_id=emb.id,
        cnpj_emitente='11111111000111', cnpj_destino='22222222000122',
        nome_destino='D', uf_destino='RJ', cidade_destino='RIO DE JANEIRO',
        tipo_carga='DIRETA', operacao_id=op.id, criado_por='test',
    )
    db.session.add(cf); db.session.flush()

    res = emb.receita_carvia()
    assert res['total'] == 2500.0
    assert res['tem_cte'] is True
```

> Se `Transportadora`/`Embarque`/`CarviaFrete` exigirem campos obrigatorios extras (NOT NULL), confirmar no schema e completar antes de rodar — o teste deve criar registros validos.

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/carvia/test_viabilidade_service.py::test_embarque_receita_carvia_metodo -v`
Expected: FAIL — `AttributeError: 'Embarque' object has no attribute 'receita_carvia'`.

- [ ] **Step 3: Implement — metodo no modelo Embarque**

Em `app/embarques/models.py`, na classe `Embarque`, apos `total_valor_pedidos`:

```python
    def receita_carvia(self):
        """Receita CarVia (CTe/cotacao) das operacoes deste embarque.

        Lazy import: o modulo Embarque NAO depende de CarVia em import-time (R1).
        Retorna {'total': float, 'tem_cte': bool}.
        """
        from app.carvia.services.financeiro.viabilidade_service import (
            receita_carvia_por_embarque,
        )
        return receita_carvia_por_embarque(self.id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/carvia/test_viabilidade_service.py::test_embarque_receita_carvia_metodo -v`
Expected: PASS.

- [ ] **Step 5: Template — badge admin-only**

Em `app/templates/embarques/visualizar_embarque.html`, dentro do `<div class="d-flex align-items-center gap-2">` (apos o `{% endif %}` do bloco `sistema_carvia`, ~L137), inserir:

```html
        {% if current_user.perfil == 'administrador' %}
          {% set _rc = embarque.receita_carvia() %}
          {% if _rc and _rc.total %}
          <span class="badge bg-info text-dark fs-6"
                title="Receita CarVia (CTe/cotacao) das operacoes deste embarque">
            <i class="fas fa-coins me-1"></i> CarVia: R$ {{ _rc.total|valor_br }}
          </span>
          {% endif %}
        {% endif %}
```

- [ ] **Step 6: Run suite + manual smoke**

Run: `pytest tests/carvia/test_viabilidade_service.py -v` → PASS.
Manual: abrir um embarque com frete CarVia como `perfil='administrador'` → badge "CarVia: R$ ..." visivel; como nao-admin → ausente.

- [ ] **Step 7: Commit**

```bash
git add app/embarques/models.py app/templates/embarques/visualizar_embarque.html tests/carvia/test_viabilidade_service.py
git commit -m "feat(embarques): receita CarVia admin-only no cabecalho do embarque"
```

---

## Task 5 — resultado_frete_service (rateio por NF)

**Files:**
- Create: `app/carvia/services/financeiro/resultado_frete_service.py`
- Test: `tests/carvia/test_resultado_frete_service.py`

**Interfaces:**
- Consumes: `gerencial_service._build_moto_count_per_nf_subquery`. Models `CarviaNf`, `CarviaOperacao`, `CarviaOperacaoNf`, `CarviaSubcontrato`, `CarviaColeta`, `CarviaColetaNf`, `CarviaFrete`.
- Produces:
  - `ResultadoFreteService().detalhe_por_nf(data_inicio, data_fim, uf=None) -> list[dict]`
    com keys: `nf_id, numero_nf, cidade, uf, operacao_id, cte_numero, data_cte, embarque_id, motos, receita, custo_sub, custo_sub_flag, custo_coleta, resultado, resultado_moto`.
  - `ResultadoFreteService().resumo(eixo, data_inicio, data_fim, uf=None) -> list[dict]`
    com `eixo ∈ {'cte','embarque','uf_mes'}`; keys: `label, receita, custo_sub, custo_coleta, custo_total, resultado, motos, receita_moto, custo_moto, resultado_moto, margem_pct`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/carvia/test_resultado_frete_service.py
from datetime import date
from decimal import Decimal


def _op(db, cte_numero, cte_valor):
    from app.carvia.models import CarviaOperacao
    o = CarviaOperacao(
        cte_numero=cte_numero, cte_valor=Decimal(str(cte_valor)),
        cte_data_emissao=date(2026, 1, 10),
        cnpj_cliente='12345678000100', nome_cliente='C',
        uf_origem='SP', cidade_origem='SAO PAULO',
        uf_destino='SP', cidade_destino='PIRACICABA',
        status='RASCUNHO', tipo_entrada='IMPORTADO', criado_por='test',
    )
    db.session.add(o); db.session.flush()
    return o


def _nf_motos(db, numero, motos, cidade='PIRACICABA', uf='SP', peso='100.000'):
    """NF + `motos` veiculos (chassi) -> contagem GREATEST = motos."""
    from app.carvia.models import CarviaNf, CarviaNfVeiculo
    nf = CarviaNf(
        numero_nf=numero, cnpj_emitente='11111111000111', nome_emitente='E',
        cnpj_destinatario='22222222000122', nome_destinatario='D',
        uf_destinatario=uf, cidade_destinatario=cidade,
        data_emissao=date(2026, 1, 10), valor_total=Decimal('500'),
        peso_bruto=Decimal(peso), status='ATIVA', tipo_fonte='MANUAL', criado_por='test',
    )
    db.session.add(nf); db.session.flush()
    for i in range(motos):
        db.session.add(CarviaNfVeiculo(nf_id=nf.id, chassi=f'CH{numero}{i:03d}'))
    db.session.flush()
    return nf


def _link(db, op_id, nf_id):
    from app.carvia.models import CarviaOperacaoNf
    db.session.add(CarviaOperacaoNf(operacao_id=op_id, nf_id=nf_id)); db.session.flush()


def test_receita_rateada_por_motos(db):
    from app.carvia.services.financeiro.resultado_frete_service import ResultadoFreteService
    op = _op(db, 'CTe-R1', 1440.0)
    for n in range(3):
        nf = _nf_motos(db, f'8000{n}', 2)
        _link(db, op.id, nf.id)
    det = ResultadoFreteService().detalhe_por_nf(date(2026, 1, 1), date(2026, 12, 31))
    assert len(det) == 3
    for d in det:
        assert d['motos'] == 2
        assert round(d['receita'], 2) == 480.0
        assert round(d['resultado'], 2) == 480.0
        assert round(d['resultado_moto'], 2) == 240.0


def test_custo_subcontrato_gera_prejuizo(db):
    from app.carvia.models import CarviaSubcontrato
    from app.transportadoras.models import Transportadora
    from app.carvia.services.financeiro.resultado_frete_service import ResultadoFreteService
    op = _op(db, 'CTe-R2', 4000.0)
    nf = _nf_motos(db, '81000', 16)
    _link(db, op.id, nf.id)
    transp = Transportadora(razao_social='T2', cnpj='44444444000144')
    db.session.add(transp); db.session.flush()
    db.session.add(CarviaSubcontrato(
        operacao_id=op.id, transportadora_id=transp.id,
        cte_valor=Decimal('4309.39'), status='CONFIRMADO', criado_por='test',
    )); db.session.flush()
    det = ResultadoFreteService().detalhe_por_nf(date(2026, 1, 1), date(2026, 12, 31))
    assert len(det) == 1
    d = det[0]
    assert round(d['custo_sub'], 2) == 4309.39
    assert d['custo_sub_flag'] == 'REAL'
    assert round(d['resultado'], 2) == round(4000.0 - 4309.39, 2)  # prejuizo


def test_resumo_por_cte_agrega(db):
    from app.carvia.services.financeiro.resultado_frete_service import ResultadoFreteService
    op = _op(db, 'CTe-R3', 1000.0)
    nf = _nf_motos(db, '82000', 4)
    _link(db, op.id, nf.id)
    res = ResultadoFreteService().resumo('cte', date(2026, 1, 1), date(2026, 12, 31))
    assert len(res) == 1
    assert round(res[0]['receita'], 2) == 1000.0
    assert res[0]['motos'] == 4
    assert round(res[0]['receita_moto'], 2) == 250.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/carvia/test_resultado_frete_service.py -v`
Expected: FAIL — `ModuleNotFoundError: resultado_frete_service`.

- [ ] **Step 3: Implement the service**

```python
# app/carvia/services/financeiro/resultado_frete_service.py
"""ResultadoFreteService — resultado (receita − custo) por frete, rateado por moto.

Receita = CarviaOperacao.cte_valor; custo = Σ subcontratos da operacao + coleta.
Receita e custo descem a NF pela MESMA base (cascata motos→peso→nº NFs) — por
construcao a soma fecha em qualquer eixo de resumo (CTe/embarque/UF-mes).
"""
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func

from app import db
from app.carvia.services.financeiro.gerencial_service import (
    _build_moto_count_per_nf_subquery,
)

ZERO = Decimal('0')
CENT = Decimal('0.01')


def _ratear(valor_total, nfs, key):
    """Distribui valor_total entre nfs (list de dict com 'motos','peso') -> nf[key].

    Cascata: 1 NF=direto; senao Motos; senao Peso; senao Qtd NFs. Ajuste de
    centavos na 1a NF. Espelha gerencial_service._aplicar_rateio_itens (NF-level).
    """
    if not nfs:
        return
    total_motos = sum(n['motos'] for n in nfs)
    total_peso = sum(n['peso'] for n in nfs)
    if len(nfs) == 1:
        nfs[0][key] = valor_total
        return
    if total_motos > 0:
        for n in nfs:
            prop = Decimal(n['motos']) / Decimal(total_motos)
            n[key] = (valor_total * prop).quantize(CENT, ROUND_HALF_UP)
    elif total_peso > 0:
        for n in nfs:
            prop = n['peso'] / total_peso
            n[key] = (valor_total * prop).quantize(CENT, ROUND_HALF_UP)
    else:
        v = (valor_total / len(nfs)).quantize(CENT, ROUND_HALF_UP)
        for n in nfs:
            n[key] = v
    soma = sum(n[key] for n in nfs)
    diff = valor_total - soma
    if diff != 0:
        nfs[0][key] += diff


class ResultadoFreteService:

    def detalhe_por_nf(self, data_inicio, data_fim, uf=None):
        from app.carvia.models import (
            CarviaNf, CarviaOperacao, CarviaOperacaoNf, CarviaSubcontrato,
            CarviaColeta, CarviaColetaNf, CarviaFrete,
        )
        moto_nf = _build_moto_count_per_nf_subquery('moto_nf_rf')

        q = (
            db.session.query(
                CarviaNf.id.label('nf_id'),
                CarviaNf.numero_nf,
                CarviaNf.cidade_destinatario,
                CarviaNf.uf_destinatario,
                CarviaNf.peso_bruto,
                CarviaOperacao.id.label('operacao_id'),
                CarviaOperacao.cte_numero,
                CarviaOperacao.cte_valor,
                CarviaOperacao.cte_data_emissao,
                func.coalesce(moto_nf.c.qtd_motos, 0).label('qtd_motos_nf'),
            )
            .join(CarviaOperacaoNf, CarviaOperacaoNf.nf_id == CarviaNf.id)
            .join(CarviaOperacao, CarviaOperacao.id == CarviaOperacaoNf.operacao_id)
            .outerjoin(moto_nf, moto_nf.c.nf_id == CarviaNf.id)
            .filter(
                CarviaNf.status == 'ATIVA',
                CarviaOperacao.status != 'CANCELADO',
                CarviaOperacao.cte_data_emissao.isnot(None),
                CarviaOperacao.cte_data_emissao >= data_inicio,
                CarviaOperacao.cte_data_emissao <= data_fim,
            )
        )
        if uf:
            q = q.filter(CarviaNf.uf_destinatario == uf)
        rows = q.all()
        if not rows:
            return []

        op_ids = {r.operacao_id for r in rows}
        nf_ids = {r.nf_id for r in rows}

        # custo subcontrato por operacao (SUM; flag REAL se houver cte_valor)
        sub_por_op = {}
        for s in (db.session.query(CarviaSubcontrato)
                  .filter(CarviaSubcontrato.operacao_id.in_(op_ids)).all()):
            valor = s.cte_valor if s.cte_valor is not None else (
                s.valor_acertado if s.valor_acertado is not None else s.valor_cotado)
            acc, real = sub_por_op.get(s.operacao_id, (ZERO, False))
            sub_por_op[s.operacao_id] = (
                acc + (Decimal(str(valor)) if valor else ZERO),
                real or (s.cte_valor is not None),
            )

        # embarque por operacao (eixo)
        emb_por_op = {}
        for op_id, emb_id in (db.session.query(CarviaFrete.operacao_id, CarviaFrete.embarque_id)
                              .filter(CarviaFrete.operacao_id.in_(op_ids),
                                      CarviaFrete.embarque_id.isnot(None)).all()):
            emb_por_op.setdefault(op_id, emb_id)

        # coleta: rateio do valor_coleta pela qtd_motos das linhas (papel de pao)
        coleta_de_nf = {}
        for ln in (db.session.query(CarviaColetaNf)
                   .filter(CarviaColetaNf.carvia_nf_id.in_(nf_ids)).all()):
            coleta_de_nf[ln.carvia_nf_id] = ln.coleta_id
        coleta_ids = set(coleta_de_nf.values())
        coleta_valor, coleta_total_motos, linha_motos = {}, defaultdict(int), {}
        if coleta_ids:
            for c in (db.session.query(CarviaColeta)
                      .filter(CarviaColeta.id.in_(coleta_ids)).all()):
                coleta_valor[c.id] = Decimal(str(c.valor_coleta)) if c.valor_coleta else ZERO
            for ln in (db.session.query(CarviaColetaNf)
                       .filter(CarviaColetaNf.coleta_id.in_(coleta_ids)).all()):
                coleta_total_motos[ln.coleta_id] += (ln.qtd_motos or 0)
                if ln.carvia_nf_id:
                    linha_motos[ln.carvia_nf_id] = ln.qtd_motos or 0

        # agrupar por operacao e ratear receita + custo subcontrato
        by_op = defaultdict(list)
        for r in rows:
            by_op[r.operacao_id].append(r)

        detalhe = []
        for op_id, op_rows in by_op.items():
            cte_valor = Decimal(str(op_rows[0].cte_valor or 0))
            sub_total, sub_real = sub_por_op.get(op_id, (ZERO, False))
            nfs = [{'r': r, 'motos': int(r.qtd_motos_nf or 0),
                    'peso': Decimal(str(r.peso_bruto or 0))} for r in op_rows]
            _ratear(cte_valor, nfs, 'receita')
            _ratear(sub_total, nfs, 'sub')
            for n in nfs:
                r = n['r']
                custo_coleta = ZERO
                cid = coleta_de_nf.get(r.nf_id)
                if cid and coleta_total_motos.get(cid):
                    custo_coleta = (
                        coleta_valor.get(cid, ZERO)
                        * Decimal(linha_motos.get(r.nf_id, 0))
                        / Decimal(coleta_total_motos[cid])
                    ).quantize(CENT, ROUND_HALF_UP)
                receita, custo_sub = n['receita'], n['sub']
                resultado = receita - custo_sub - custo_coleta
                motos = n['motos']
                detalhe.append({
                    'nf_id': r.nf_id, 'numero_nf': r.numero_nf,
                    'cidade': r.cidade_destinatario, 'uf': r.uf_destinatario,
                    'operacao_id': op_id, 'cte_numero': r.cte_numero,
                    'data_cte': r.cte_data_emissao,
                    'embarque_id': emb_por_op.get(op_id),
                    'motos': motos,
                    'receita': float(receita),
                    'custo_sub': float(custo_sub),
                    'custo_sub_flag': 'REAL' if sub_real else ('ESTIMADO' if sub_total > 0 else '—'),
                    'custo_coleta': float(custo_coleta),
                    'resultado': float(resultado),
                    'resultado_moto': float((resultado / motos).quantize(CENT, ROUND_HALF_UP)) if motos > 0 else None,
                })
        detalhe.sort(key=lambda d: d['resultado'])  # piores primeiro
        return detalhe

    def resumo(self, eixo, data_inicio, data_fim, uf=None):
        det = self.detalhe_por_nf(data_inicio, data_fim, uf)
        grupos = {}
        for d in det:
            if eixo == 'embarque':
                chave = d['embarque_id'] or 'sem'
                label = f"Embarque #{d['embarque_id']}" if d['embarque_id'] else 'Sem embarque'
            elif eixo == 'uf_mes':
                mes = d['data_cte'].strftime('%Y-%m') if d['data_cte'] else 'sem-data'
                chave = (d['uf'], mes)
                label = f"{d['uf'] or '—'} / {mes}"
            else:  # cte
                chave = d['operacao_id']
                label = d['cte_numero'] or f"op {d['operacao_id']}"
            g = grupos.setdefault(chave, {
                'label': label, 'receita': 0.0, 'custo_sub': 0.0,
                'custo_coleta': 0.0, 'resultado': 0.0, 'motos': 0,
            })
            g['receita'] += d['receita']
            g['custo_sub'] += d['custo_sub']
            g['custo_coleta'] += d['custo_coleta']
            g['resultado'] += d['resultado']
            g['motos'] += d['motos']
        out = []
        for g in grupos.values():
            motos = g['motos']
            custo_total = g['custo_sub'] + g['custo_coleta']
            out.append({
                **g,
                'custo_total': round(custo_total, 2),
                'receita_moto': round(g['receita'] / motos, 2) if motos else None,
                'custo_moto': round(custo_total / motos, 2) if motos else None,
                'resultado_moto': round(g['resultado'] / motos, 2) if motos else None,
                'margem_pct': round(g['resultado'] / g['receita'] * 100, 1) if g['receita'] else None,
            })
        out.sort(key=lambda x: x['resultado'])
        return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/carvia/test_resultado_frete_service.py -v`
Expected: PASS (3 testes).

- [ ] **Step 5: Commit**

```bash
git add app/carvia/services/financeiro/resultado_frete_service.py tests/carvia/test_resultado_frete_service.py
git commit -m "feat(carvia): resultado_frete_service — rateio coerente receita/custo por moto"
```

---

## Task 6 — Tela /carvia/resultado-frete

**Files:**
- Create: `app/carvia/routes/resultado_frete_routes.py`
- Modify: `app/carvia/routes/__init__.py` (registrar)
- Create: `app/templates/carvia/resultado_frete/index.html`
- Test: `tests/carvia/test_resultado_frete_routes.py`

**Interfaces:**
- Consumes: `ResultadoFreteService().resumo(...)` e `.detalhe_por_nf(...)` (Task 5).
- Produces: rota GET `carvia.resultado_frete` (`/carvia/resultado-frete`) + rota GET `carvia.exportar_resultado_frete` (Task 7).

- [ ] **Step 1: Write the failing test**

```python
# tests/carvia/test_resultado_frete_routes.py
from unittest.mock import MagicMock, patch


def _user(carvia=True, admin=True):
    u = MagicMock()
    u.is_authenticated = True
    u.sistema_carvia = carvia
    u.perfil = 'administrador' if admin else 'vendedor'
    u.email = 'test@bot'
    return u


def test_tela_resultado_frete_render(db, client):
    with patch('flask_login.utils._get_user', return_value=_user()):
        r = client.get('/carvia/resultado-frete')
    assert r.status_code == 200
    assert b'Resultado por Frete' in r.data


def test_tela_guard_sem_carvia(db, client):
    with patch('flask_login.utils._get_user', return_value=_user(carvia=False)):
        r = client.get('/carvia/resultado-frete')
    assert r.status_code in (301, 302)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/carvia/test_resultado_frete_routes.py -v`
Expected: FAIL — 404 (rota inexistente).

- [ ] **Step 3: Create route module**

```python
# app/carvia/routes/resultado_frete_routes.py
from datetime import datetime, timedelta

from flask import render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user

from app.utils.auth_decorators import require_admin


def _parse_date(arg, default):
    v = request.args.get(arg)
    if not v:
        return default
    try:
        return datetime.strptime(v, '%Y-%m-%d').date()
    except ValueError:
        return default


def register_resultado_frete_routes(bp):

    @bp.route('/resultado-frete')  # type: ignore
    @login_required
    @require_admin
    def resultado_frete():  # type: ignore
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado. Voce nao tem permissao para o sistema CarVia.', 'danger')
            return redirect(url_for('main.dashboard'))

        from app.carvia.services.financeiro.resultado_frete_service import ResultadoFreteService
        from app.utils.timezone import agora_brasil_naive

        hoje = agora_brasil_naive().date()
        data_inicio = _parse_date('data_inicio', hoje - timedelta(days=30))
        data_fim = _parse_date('data_fim', hoje)
        uf = request.args.get('uf') or None
        eixo = request.args.get('eixo') or 'cte'
        if eixo not in ('cte', 'embarque', 'uf_mes'):
            eixo = 'cte'

        svc = ResultadoFreteService()
        resumo = svc.resumo(eixo, data_inicio, data_fim, uf)
        detalhe = svc.detalhe_por_nf(data_inicio, data_fim, uf)

        return render_template(
            'carvia/resultado_frete/index.html',
            resumo=resumo, detalhe=detalhe, eixo=eixo,
            data_inicio=data_inicio.isoformat(), data_fim=data_fim.isoformat(),
            uf=uf or '',
        )
```

- [ ] **Step 4: Register the route module**

Em `app/carvia/routes/__init__.py`, dentro de `register_routes(bp)`, adicionar (junto aos demais `register_*`):

```python
    from app.carvia.routes.resultado_frete_routes import register_resultado_frete_routes
    register_resultado_frete_routes(bp)
```

- [ ] **Step 5: Create template**

```html
{# app/templates/carvia/resultado_frete/index.html #}
{% extends "base.html" %}

{% block content %}
<div class="container-fluid py-4">
    <div class="d-flex justify-content-between align-items-center mb-4">
        <div>
            <h2><i class="fas fa-scale-balanced"></i> CarVia — Resultado por Frete</h2>
            <p class="text-muted mb-0">Receita (CTe) vs custo (subcontrato + coleta), rateado por moto</p>
        </div>
        <a href="{{ url_for('carvia.exportar_resultado_frete', data_inicio=data_inicio, data_fim=data_fim, uf=uf, eixo=eixo) }}"
           class="btn btn-outline-success" title="Exportar Excel">
            <i class="fas fa-file-excel"></i> Exportar
        </a>
    </div>

    <div class="card mb-3">
        <div class="card-body py-2">
            <form method="get" class="row g-2 align-items-end">
                <div class="col-auto">
                    <label class="form-label small mb-0">Data Inicio</label>
                    <input type="date" class="form-control form-control-sm" name="data_inicio" value="{{ data_inicio }}">
                </div>
                <div class="col-auto">
                    <label class="form-label small mb-0">Data Fim</label>
                    <input type="date" class="form-control form-control-sm" name="data_fim" value="{{ data_fim }}">
                </div>
                <div class="col-auto">
                    <label class="form-label small mb-0">UF</label>
                    <input type="text" maxlength="2" class="form-control form-control-sm" name="uf" value="{{ uf }}" style="width:70px">
                </div>
                <div class="col-auto">
                    <label class="form-label small mb-0">Resumo por</label>
                    <select name="eixo" class="form-select form-select-sm">
                        <option value="cte" {% if eixo=='cte' %}selected{% endif %}>CTe CarVia</option>
                        <option value="embarque" {% if eixo=='embarque' %}selected{% endif %}>Embarque</option>
                        <option value="uf_mes" {% if eixo=='uf_mes' %}selected{% endif %}>UF / Mes</option>
                    </select>
                </div>
                <div class="col-auto">
                    <button type="submit" class="btn btn-primary btn-sm"><i class="fas fa-filter"></i> Filtrar</button>
                </div>
            </form>
        </div>
    </div>

    <h5 class="mt-3">Resumo ({{ eixo }})</h5>
    <div class="table-responsive">
        <table class="table table-sm carvia-table mb-4">
            <thead><tr class="table-thead-theme">
                <th>{{ 'CTe' if eixo=='cte' else ('Embarque' if eixo=='embarque' else 'UF/Mes') }}</th>
                <th class="text-end">Receita</th><th class="text-end">Custo Sub</th>
                <th class="text-end">Custo Coleta</th><th class="text-end">Resultado</th>
                <th class="text-end">Motos</th><th class="text-end">R$/Moto</th><th class="text-end">Margem %</th>
            </tr></thead>
            <tbody>
            {% for g in resumo %}
                <tr>
                    <td>{{ g.label }}</td>
                    <td class="text-end">{{ g.receita|valor_br }}</td>
                    <td class="text-end">{{ g.custo_sub|valor_br }}</td>
                    <td class="text-end">{{ g.custo_coleta|valor_br }}</td>
                    <td class="text-end {% if g.resultado < 0 %}text-danger fw-bold{% else %}text-success{% endif %}">{{ g.resultado|valor_br }}</td>
                    <td class="text-end">{{ g.motos }}</td>
                    <td class="text-end">{{ g.resultado_moto|valor_br if g.resultado_moto is not none else '—' }}</td>
                    <td class="text-end">{{ g.margem_pct ~ '%' if g.margem_pct is not none else '—' }}</td>
                </tr>
            {% else %}
                <tr><td colspan="8" class="text-center text-muted py-3">Nenhum dado no periodo</td></tr>
            {% endfor %}
            </tbody>
        </table>
    </div>

    <h5>Detalhe por NF</h5>
    <div class="table-responsive">
        <table class="table table-sm carvia-table mb-0">
            <thead><tr class="table-thead-theme">
                <th>NF</th><th>Cidade/UF</th><th>CTe</th><th class="text-end">Motos</th>
                <th class="text-end">Receita</th><th class="text-end">Custo Sub</th><th>Custo</th>
                <th class="text-end">Custo Coleta</th><th class="text-end">Resultado</th><th class="text-end">R$/Moto</th>
            </tr></thead>
            <tbody>
            {% for d in detalhe %}
                <tr>
                    <td>{{ d.numero_nf }}</td>
                    <td>{{ d.cidade or '' }}/{{ d.uf or '' }}</td>
                    <td>{{ d.cte_numero or '—' }}</td>
                    <td class="text-end">{{ d.motos }}</td>
                    <td class="text-end">{{ d.receita|valor_br }}</td>
                    <td class="text-end">{{ d.custo_sub|valor_br }}</td>
                    <td><span class="badge bg-{{ 'success' if d.custo_sub_flag=='REAL' else ('warning text-dark' if d.custo_sub_flag=='ESTIMADO' else 'secondary') }}">{{ d.custo_sub_flag }}</span></td>
                    <td class="text-end">{{ d.custo_coleta|valor_br }}</td>
                    <td class="text-end {% if d.resultado < 0 %}text-danger fw-bold{% else %}text-success{% endif %}">{{ d.resultado|valor_br }}</td>
                    <td class="text-end">{{ d.resultado_moto|valor_br if d.resultado_moto is not none else '—' }}</td>
                </tr>
            {% else %}
                <tr><td colspan="10" class="text-center text-muted py-3">Nenhuma NF no periodo</td></tr>
            {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
```

> A rota `carvia.exportar_resultado_frete` referenciada no `url_for` do botao e criada na Task 7. Implementar a Task 7 Step 3 ANTES de carregar a tela no browser (senao `url_for` lanca BuildError). O teste de render desta task nao falha por isso apenas se a Task 7 ja estiver no lugar — para manter a ordem TDD, rodar o teste de render so apos a Task 7 Step 3, OU registrar a rota de export como stub vazio aqui e completa-la na Task 7.

- [ ] **Step 6: Run test to verify it passes**

Run: `pytest tests/carvia/test_resultado_frete_routes.py::test_tela_resultado_frete_render -v`
Expected: PASS apos Task 7 Step 3 registrar `exportar_resultado_frete`. Se rodar isolado antes, implementar a rota de export (Task 7 Step 3) primeiro.

- [ ] **Step 7: Commit**

```bash
git add app/carvia/routes/resultado_frete_routes.py app/carvia/routes/__init__.py app/templates/carvia/resultado_frete/index.html tests/carvia/test_resultado_frete_routes.py
git commit -m "feat(carvia): tela Resultado por Frete (resumo por eixo + detalhe por NF)"
```

---

## Task 7 — Export Excel Resultado por Frete (2 abas)

**Files:**
- Modify: `app/carvia/routes/resultado_frete_routes.py` (+rota `exportar_resultado_frete`)
- Test: `tests/carvia/test_resultado_frete_routes.py` (+1 teste)

**Interfaces:**
- Consumes: `ResultadoFreteService`. Como `gerar_excel_duplo_cabecalho` gera 1 aba por chamada, este export monta o workbook diretamente com `openpyxl` (2 sheets).
- Produces: rota GET `carvia.exportar_resultado_frete` → xlsx 2 abas (`Resumo` + `Detalhe NF`).

- [ ] **Step 1: Write the failing test**

```python
# tests/carvia/test_resultado_frete_routes.py  (acrescentar)
from io import BytesIO
from openpyxl import load_workbook


def test_export_resultado_frete_duas_abas(db, client):
    with patch('flask_login.utils._get_user', return_value=_user()):
        r = client.get('/carvia/api/exportar/resultado-frete?data_inicio=2026-01-01&data_fim=2026-12-31')
    assert r.status_code == 200
    wb = load_workbook(BytesIO(r.data))
    assert 'Resumo' in wb.sheetnames
    assert 'Detalhe NF' in wb.sheetnames
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/carvia/test_resultado_frete_routes.py::test_export_resultado_frete_duas_abas -v`
Expected: FAIL — 404.

- [ ] **Step 3: Implement export route**

Adicionar em `app/carvia/routes/resultado_frete_routes.py`, dentro de `register_resultado_frete_routes(bp)`:

```python
    @bp.route('/api/exportar/resultado-frete')  # type: ignore
    @login_required
    @require_admin
    def exportar_resultado_frete():  # type: ignore
        if not getattr(current_user, 'sistema_carvia', False):
            flash('Acesso negado.', 'danger')
            return redirect(url_for('main.dashboard'))

        from io import BytesIO
        from flask import send_file
        from openpyxl import Workbook
        from openpyxl.styles import Font, PatternFill, Alignment
        from app.carvia.services.financeiro.resultado_frete_service import ResultadoFreteService
        from app.utils.timezone import agora_brasil_naive, agora_utc_naive

        hoje = agora_brasil_naive().date()
        data_inicio = _parse_date('data_inicio', hoje - timedelta(days=30))
        data_fim = _parse_date('data_fim', hoje)
        uf = request.args.get('uf') or None
        eixo = request.args.get('eixo') or 'cte'
        if eixo not in ('cte', 'embarque', 'uf_mes'):
            eixo = 'cte'

        svc = ResultadoFreteService()
        resumo = svc.resumo(eixo, data_inicio, data_fim, uf)
        detalhe = svc.detalhe_por_nf(data_inicio, data_fim, uf)

        hdr_fill = PatternFill(start_color='2E75B6', end_color='2E75B6', fill_type='solid')
        hdr_font = Font(bold=True, color='FFFFFF')
        center = Alignment(horizontal='center', vertical='center')

        def _write_sheet(ws, headers, rows):
            for c, h in enumerate(headers, start=1):
                cell = ws.cell(row=1, column=c, value=h)
                cell.fill = hdr_fill; cell.font = hdr_font; cell.alignment = center
            for ridx, row in enumerate(rows, start=2):
                for c, val in enumerate(row, start=1):
                    ws.cell(row=ridx, column=c, value=val)
            ws.freeze_panes = 'A2'

        wb = Workbook()
        ws1 = wb.active
        ws1.title = 'Resumo'
        _write_sheet(ws1,
            [eixo.upper(), 'Receita', 'Custo Sub', 'Custo Coleta', 'Custo Total',
             'Resultado', 'Motos', 'R$/Moto Receita', 'R$/Moto Custo', 'R$/Moto Result', 'Margem %'],
            [[g['label'], g['receita'], g['custo_sub'], g['custo_coleta'], g['custo_total'],
              g['resultado'], g['motos'], g['receita_moto'], g['custo_moto'],
              g['resultado_moto'], g['margem_pct']] for g in resumo],
        )
        ws2 = wb.create_sheet('Detalhe NF')
        _write_sheet(ws2,
            ['NF', 'Cidade', 'UF', 'CTe', 'Embarque', 'Motos', 'Receita',
             'Custo Sub', 'Flag Custo', 'Custo Coleta', 'Resultado', 'R$/Moto'],
            [[d['numero_nf'], d['cidade'], d['uf'], d['cte_numero'], d['embarque_id'],
              d['motos'], d['receita'], d['custo_sub'], d['custo_sub_flag'],
              d['custo_coleta'], d['resultado'], d['resultado_moto']] for d in detalhe],
        )

        output = BytesIO()
        wb.save(output)
        output.seek(0)
        ts = agora_utc_naive().strftime('%Y%m%d_%H%M')
        return send_file(
            output,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            as_attachment=True,
            download_name=f'carvia_resultado_frete_{ts}.xlsx',
        )
```

> `_parse_date` e `timedelta` ja estao importados no topo do modulo (Task 6 Step 3). Garantir o import `from datetime import datetime, timedelta` no topo.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/carvia/test_resultado_frete_routes.py -v`
Expected: PASS (3 testes — incluindo os 2 da Task 6).

- [ ] **Step 5: Run full carvia suite (regression)**

Run: `pytest tests/carvia/ -q`
Expected: todos os testes novos passam; nenhum existente quebra.

- [ ] **Step 6: Update docs (parte do "pronto")**

- `app/carvia/CLAUDE.md`: nova linha descrevendo `ResultadoFreteService` (rateio coerente por NF) e a tela `/carvia/resultado-frete`.
- `app/carteira/CLAUDE.md` (R11): mencionar a row de viabilidade CarVia no mapa.
Seguir a skill `padronizando-docs` (header doc:meta ja existe; manter indice/secoes; passar no doc_audit).

- [ ] **Step 7: Commit**

```bash
git add app/carvia/routes/resultado_frete_routes.py tests/carvia/test_resultado_frete_routes.py app/carvia/CLAUDE.md app/carteira/CLAUDE.md
git commit -m "feat(carvia): export Excel Resultado por Frete (Resumo + Detalhe NF)"
```

---

## Self-Review

**Spec coverage:**
- Entrega 1 (cidade no export) → Task 1 ✓ (nfs + operacoes).
- Entrega 2 mapa (CTe quando houver, senao cotacao) → Task 2 (`_receita_lote`) + Task 3 ✓.
- Entrega 2 embarque (admin-only) → Task 4 (`perfil == 'administrador'`) ✓.
- Entrega 3 nucleo de rateio coerente (cascata, COALESCE custo, coleta) → Task 5 ✓.
- Entrega 3 resumo por CTe/Embarque/UF-mes → Task 5 `resumo(eixo)` + Task 6 seletor ✓.
- Entrega 3 tela + Excel 2 abas → Tasks 6/7 ✓.
- Flag REAL/ESTIMADO do custo → Task 5 + coluna na tela/Excel ✓.
- Edge cases (motos=0 → peso/qtd; multi-subcontrato → SUM; coleta rateada) → `_ratear` + `sub_por_op` + rateio coleta ✓.

**Placeholder scan:** sem TBD/TODO. Os `~Lxxx` sao ancoras de localizacao, nao placeholders de codigo. A nota do teste Task 4 (campos NOT NULL de Embarque/Transportadora/CarviaFrete) pede confirmacao no schema — completar antes de rodar.

**Type consistency:** keys do dict de `detalhe_por_nf` (`receita, custo_sub, custo_sub_flag, custo_coleta, resultado, resultado_moto, embarque_id, cte_numero, data_cte, motos, cidade, uf, numero_nf`) sao consumidas identicas em `resumo`, no template (Task 6) e no Excel (Task 7). `receita_carvia_por_lotes`/`receita_carvia_por_embarque` retornam dicts com as chaves usadas em Task 3 (`total`, `por_lote`; `viabilidade` derivada na rota) e Task 4 (`total`, `tem_cte`). Consistente.

**Dependencia entre tasks:** Task 6 usa `url_for('carvia.exportar_resultado_frete')` (Task 7) — nota explicita para implementar Task 7 Step 3 antes de carregar a tela; teste de render roda apos esse registro.
