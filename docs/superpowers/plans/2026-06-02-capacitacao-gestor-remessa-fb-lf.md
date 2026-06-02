<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano de implementacao da capacitacao do gestor-estoque-odoo p/ remessa avulsa FB->LF
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->

# Capacitação do gestor-estoque-odoo p/ remessa FB→LF — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Papel deste doc:** plano executável (tarefas TDD) que implementa o spec `docs/superpowers/specs/2026-06-02-capacitacao-gestor-remessa-fb-lf-design.md`. **Não** repete o "porquê" (está no spec) — só o "como", passo a passo.
> **Abra quando:** for executar/retomar a implementação das correções C1–C5 + canary.

**Goal:** Tornar o `gestor-estoque-odoo` capaz de executar autonomamente a remessa inter-company FB→LF de insumo (avulsa), corrigindo as 3 camadas (skills genéricas / fluxo / prompt).

**Architecture:** Correções cirúrgicas nos átomos L2 (idempotência intra-Odoo na Skill 8; qualificação de DFe-resumo na Skill 7; company do lote na Skill 5) + nova folha L3 1.3.1 (entry-point avulso) + fix de drift no prompt L4. Cada átomo permanece genérico/dry-run-first; compatibilidade retroativa preservada.

**Tech Stack:** Python 3.12, pytest (mock XML-RPC), Odoo XML-RPC, Flask app context. Sem evals LLM (preferência do usuário).

## TOC

- [Contexto](#contexto)
- [File structure](#file-structure)
- [Task 0 — C5 prompt drift](#task-0--c5-corrigir-drift-da-árvore-no-prompt-l4)
- [Task 1 — C1 Skill 8 idempotência intra-Odoo](#task-1--c1-skill-8-faturando-odoo-idempotência-intra-odoo--ajuste_ids-opcional)
- [Task 2 — C2 buscar_dfe qualifica resumo](#task-2--c2-buscar_dfe-qualifica-dfe-resumo-vazio--decisão-de-caminho)
- [Task 3 — C3 lote na company destino](#task-3--c3-preencher_lotes_picking-fixa-company-do-lote)
- [Task 4 — C4 folha 1.3.1](#task-4--c4-folha-l3-131-remessa-avulsa--no-na-árvore)
- [Task 5 — Canary](#task-5--canary-real-2-produtos)

## Contexto

Diagnóstico de raiz aprovado (ver spec §3): o gestor não executa a remessa avulsa por 3 furos — Skill 8 acoplada ao `AjusteEstoqueInventario` (idempotência), `buscar_dfe` não qualifica DFe-resumo, `preencher_lotes_picking` não fixa company do lote; + folha 1.3 sem entry-point avulso; + prompt com drift de status. Este plano corrige cada um sem mexer na operação.

Baseline de testes do estoque: `pytest tests/odoo/ -q` (rodar da raiz `/home/rafaelnascimento/projetos/frete_sistema` OU passar `DATABASE_URL` no worktree). Cada task deve manter a suite verde (zero regressão).

> **Nota de ambiente (worktree):** rodar pytest do worktree exige env. Use:
> `cd /home/rafaelnascimento/projetos/frete_sistema_remessa_fb_lf && source .venv/bin/activate && DATABASE_URL="$(grep -m1 '^DATABASE_URL' .env | cut -d= -f2-)" pytest tests/odoo/... -q`
> (ou rode da raiz, já que o código é o mesmo até o merge).

---

## File structure

| Arquivo | Responsabilidade | Ação |
|---|---|---|
| `.claude/agents/gestor-estoque-odoo.md` | Prompt L4 (árvore de decisão) | Modificar (C5) |
| `app/odoo/estoque/scripts/faturamento.py` | Skill 8 (`account.move`) | Modificar (C1) |
| `tests/odoo/services/test_faturamento_invoice_service.py` | testes Skill 8 | Modificar (C1) |
| `app/odoo/estoque/scripts/escrituracao.py` | Skill 7 (`DFe`) | Modificar (C2) |
| `app/odoo/estoque/orchestrators/inventario_pipeline.py` | decisão caminho A/B em `executar_fluxo_l3_1_2_x` | Modificar (C2) |
| `tests/odoo/services/test_escrituracao*.py` (arquivo de teste da Skill 7) | testes `buscar_dfe` | Modificar (C2) |
| `app/odoo/estoque/scripts/picking.py` | Skill 5 (`stock.picking`) | Modificar (C3) |
| `tests/odoo/services/test_stock_picking_service.py` | testes `preencher_lotes_picking` | Modificar (C3) |
| `app/odoo/estoque/fluxos/1.3.1-remessa-avulsa-insumo.md` | Fluxo L3 (entry-point avulso) | Criar (C4) |

---

## Task 0 — C5: corrigir drift da árvore no prompt L4

**Files:**
- Modify: `.claude/agents/gestor-estoque-odoo.md:93` (+ nota do galho 1 ~linha 111)

- [ ] **Step 1: Ler o trecho atual da árvore (linhas 84-111)** para confirmar o texto exato antes de editar.

- [ ] **Step 2: Substituir o status do galho 1.3**

Trocar (linha ~93):
```
   1.3  transferência completa (saída+entrada) → fluxos/1.3 (compõe Skill 8 ATÔMICA L2 + folha 1.2.x) ⬜ pendente v20+ (depende refator AP6)
```
Por (status real — folha escrita v27+ S5, entrada validada PROD 627348 + AVULSO_FRASCO):
```
   1.3  transferência completa (saída+entrada) → [folha 1.3](app/odoo/estoque/fluxos/1.3-transferencia-completa.md) ✅ v27+ S5 — compõe 1.1.1 (saída) + 1.2.x (entrada). Caminho com-ciclo.
        1.3.1 remessa AVULSA de insumo (sem ciclo de inventário) → folha `app/odoo/estoque/fluxos/1.3.1-remessa-avulsa-insumo.md` ✅ — origina os átomos diretamente (Skill 5 picking → Skill 8 SEFAZ → Skill 7 entrada), sem AjusteEstoqueInventario obrigatório.
```

- [ ] **Step 3: Validar que não há mais "1.3 ... pendente" no prompt**

Run: `grep -n "1.3" .claude/agents/gestor-estoque-odoo.md`
Expected: nenhuma linha do galho 1.3 contém "⬜ pendente".

- [ ] **Step 4: Commit**

```bash
git add .claude/agents/gestor-estoque-odoo.md
git commit -m "fix(gestor-estoque): corrige drift da arvore 1.3 (pendente -> disponivel) + no 1.3.1 avulso"
```

> Nota: a folha 1.3.1 referenciada é criada na Task 4. Ordem real de execução: Task 0 e Task 4 podem ser commitadas juntas, ou a referência 1.3.1 fica como forward-pointer até a Task 4 (link relativo a arquivo .md → C7 link-rot só bloqueia em arquivos novos/linhas tocadas; criar 1.3.1 antes de commitar o prompt evita o bloqueio). **Recomendado: executar Task 4 antes da Task 0**, ou commitar ambas juntas.

---

## Task 1 — C1: Skill 8 `faturando-odoo` idempotência intra-Odoo + `ajuste_ids` opcional

**Objetivo:** `transmitir_sefaz` deixa de exigir `ajuste_ids`; idempotência primária passa a ler o próprio `account.move` (`situacao_nf`/`l10n_br_status`); a camada de ajuste (D8.3 + propagação de chave) vira opcional (só quando `ajuste_ids` fornecido). Compat retroativa total.

**Files:**
- Modify: `app/odoo/estoque/scripts/faturamento.py:806-1000+` (`transmitir_sefaz`)
- Test: `tests/odoo/services/test_faturamento_invoice_service.py`

- [ ] **Step 1: Ler `transmitir_sefaz` inteiro (806-1010)** para mapear todos os usos de `ajuste_ids` (early-return 871-878; re-fetch 920-934; D8.3 936-953; propagação pós-Playwright; bloco de exceção 969-985).

- [ ] **Step 2: Escrever teste — transmitir_sefaz dry-run SEM ajuste_ids não falha mais**

Em `test_faturamento_invoice_service.py`, seguindo o padrão de mock já usado no arquivo (mock de `OdooConnection` com `read`/`search_read`):
```python
def test_transmitir_sefaz_dry_run_sem_ajustes_ok(svc_e_odoo):
    svc, odoo = svc_e_odoo
    # invoice em rascunho (situacao_nf != autorizado)
    odoo.read.return_value = [{'id': 999, 'situacao_nf': 'rascunho',
                               'l10n_br_status': False, 'chave_nfe': False,
                               'state': 'posted'}]
    r = svc.transmitir_sefaz(invoice_id=999, ajuste_ids=None, dry_run=True)
    assert r['status'] == 'DRY_RUN_OK'   # NAO mais FALHA_AJUSTES_VAZIOS
```

- [ ] **Step 3: Escrever teste — idempotência intra-Odoo (invoice já autorizado) sem ajustes**

```python
def test_transmitir_sefaz_idempotente_por_account_move(svc_e_odoo):
    svc, odoo = svc_e_odoo
    odoo.read.return_value = [{'id': 999, 'situacao_nf': 'autorizado',
                               'l10n_br_status': '100', 'chave_nfe': '3526...44dig',
                               'state': 'posted'}]
    r = svc.transmitir_sefaz(invoice_id=999, ajuste_ids=None,
                             dry_run=False, confirmar_sefaz=True)
    assert r['status'] == 'IDEMPOTENT_SKIP'
    assert r['chave_nfe'] == '3526...44dig'
    # Playwright NAO foi chamado (mock transmitir_nfe_via_playwright não invocado)
```

- [ ] **Step 4: Escrever teste — compat: com ajuste_ids mantém D8.3**

```python
def test_transmitir_sefaz_com_ajustes_preserva_d83(svc_e_odoo, ajuste_em_f5e_ok):
    # invoice rascunho mas ajuste ja em F5e_SEFAZ_OK -> IDEMPOTENT_SKIP via D8.3
    ...
    r = svc.transmitir_sefaz(invoice_id=999, ajuste_ids=[ajuste_em_f5e_ok.id],
                             dry_run=False, confirmar_sefaz=True)
    assert r['status'] == 'IDEMPOTENT_SKIP'
```

- [ ] **Step 5: Run tests — verificar que falham** (`transmitir_sefaz` ainda exige ajustes)

Run: `pytest tests/odoo/services/test_faturamento_invoice_service.py -k transmitir_sefaz -v`
Expected: os 2 testes novos sem-ajuste FALHAM (FALHA_AJUSTES_VAZIOS).

- [ ] **Step 6: Implementar — assinatura + idempotência intra-Odoo**

Em `faturamento.py`:
1. Assinatura: `ajuste_ids: Optional[List[int]] = None` (era `List[int]`).
2. Remover o early-return `FALHA_AJUSTES_VAZIOS` (linhas 871-878).
3. Após o bloco dry-run-confirm (após 889) e ANTES do bloco que depende de ajustes, inserir **idempotência intra-Odoo** (vale para dry-run e real):
```python
# Idempotencia PRIMARIA (intra-Odoo) — independe de ajuste-ancora.
inv = self.odoo.read('account.move', [invoice_id],
                     ['situacao_nf', 'l10n_br_status', 'chave_nfe', 'state'])
inv = inv[0] if inv else {}
ja_autorizada = (
    (inv.get('situacao_nf') or '').lower() == 'autorizado'
    or bool(inv.get('chave_nfe'))
)
if ja_autorizada:
    out['status'] = 'IDEMPOTENT_SKIP'
    out['chave_nfe'] = inv.get('chave_nfe') or None
    out['situacao_nf'] = inv.get('situacao_nf')
    out['observacao'] = 'Idempotencia intra-Odoo: account.move ja autorizado.'
    out['tempo_ms'] = int((time.time() - t0) * 1000)
    return out
```
4. Tornar o bloco de ajustes (re-fetch 920-934, D8.3 936-953, propagação pós-Playwright, bloco exceção) **condicional a `if ajuste_ids:`**. Sem ajustes: pular re-fetch/D8.3 (idempotência já garantida intra-Odoo acima) e a propagação de chave (não há ajuste para gravar) — mas ainda transmitir e persistir o resultado no `account.move`.
5. No dry-run, ajustar a `observacao` para `len(ajuste_ids or [])`.

> **CUIDADO SEFAZ:** a idempotência intra-Odoo é a guarda anti-dupla-transmissão quando não há ajuste. Garantir que `situacao_nf=='autorizado'` é lido corretamente (confirmar o campo via `descobrindo-odoo-estrutura` se o mock não refletir produção).

- [ ] **Step 7: Run tests — verificar que passam**

Run: `pytest tests/odoo/services/test_faturamento_invoice_service.py -v`
Expected: PASS (os 3 novos + os 28 existentes verdes).

- [ ] **Step 8: Run suite completa do estoque — zero regressão**

Run (da raiz): `pytest tests/odoo/ -q`
Expected: baseline anterior + 3 novos, todos verdes.

- [ ] **Step 9: Commit**

```bash
git add app/odoo/estoque/scripts/faturamento.py tests/odoo/services/test_faturamento_invoice_service.py
git commit -m "feat(faturando-odoo): idempotencia intra-Odoo no transmitir_sefaz + ajuste_ids opcional (C1)"
```

---

## Task 2 — C2: `buscar_dfe` qualifica DFe-resumo vazio + decisão de caminho

**Objetivo:** `buscar_dfe` distingue DFe populado de DFe-resumo (status '06' / 0 linhas / sem XML) → novo status `resumo_vazio`. A decisão A/B em `executar_fluxo_l3_1_2_x` trata `resumo_vazio` como **caminho B** (popular via XML da saída).

**Files:**
- Modify: `app/odoo/estoque/scripts/escrituracao.py:950-1025` (`buscar_dfe`)
- Modify: `app/odoo/estoque/orchestrators/inventario_pipeline.py:~2948` (decisão A vs B em `executar_fluxo_l3_1_2_x`)
- Test: arquivo de teste da Skill 7 (descobrir: `ls tests/odoo/ | grep -i escritur`)

- [ ] **Step 1: Localizar o arquivo de teste da Skill 7** — `grep -rl "buscar_dfe" tests/` e ler 1 teste existente para o padrão de mock.

- [ ] **Step 2: Escrever teste — buscar_dfe com DFe populado**

```python
def test_buscar_dfe_populado(svc_e_odoo):
    svc, odoo = svc_e_odoo
    odoo.search_read.side_effect = [
        [{'id': 10, 'l10n_br_status': '03', 'purchase_id': False,
          'protnfe_infnfe_chnfe': 'C'*44, 'nfe_infnfe_ide_nnf': '1'}],  # dfe
    ]
    odoo.search_count.return_value = 5   # 5 dfe.line -> populado
    r = svc.buscar_dfe(chave_nfe='C'*44, company_id=5)
    assert r['encontrado'] is True and r['status'] == 'pendente'
    assert r.get('populado') is True
```

- [ ] **Step 3: Escrever teste — buscar_dfe com resumo vazio (status 06, 0 linhas)**

```python
def test_buscar_dfe_resumo_vazio(svc_e_odoo):
    svc, odoo = svc_e_odoo
    odoo.search_read.return_value = [{'id': 11, 'l10n_br_status': '06',
        'purchase_id': False, 'protnfe_infnfe_chnfe': 'C'*44,
        'nfe_infnfe_ide_nnf': False}]
    odoo.search_count.return_value = 0   # 0 dfe.line
    r = svc.buscar_dfe(chave_nfe='C'*44, company_id=5)
    assert r['encontrado'] is True
    assert r['status'] == 'resumo_vazio'
    assert r.get('populado') is False
```

- [ ] **Step 4: Run — verificar falha**

Run: `pytest <arquivo_teste_skill7> -k buscar_dfe -v`
Expected: FAIL (status `resumo_vazio` ainda não existe; `populado` ausente).

- [ ] **Step 5: Implementar em `buscar_dfe`**

Após obter `dfe = resp[0]` (linha 1009), contar linhas e qualificar:
```python
n_linhas = self.odoo.search_count(
    'l10n_br_ciel_it_account.dfe.line', [('dfe_id', '=', dfe['id'])],
)
populado = n_linhas > 0
# status atual continua (processado/pendente/a_processar), mas:
if st_raw == '06' or not populado:
    status = 'resumo_vazio'
out['populado'] = populado
out['n_linhas'] = n_linhas
```
Adicionar `'populado'`/`'n_linhas'` ao dict `out` inicial (default `False`/`0`). Atualizar docstring (status canônico inclui `resumo_vazio`).

- [ ] **Step 6: Implementar decisão de caminho no orchestrator**

Em `executar_fluxo_l3_1_2_x` (linha ~2948), onde decide A vs B via `r1.get('encontrado')`: tratar `resumo_vazio` como **caminho B**:
```python
r1 = self._skill7.buscar_dfe(chave_nfe=chave, company_id=company_destino)
caminho_b = (not r1.get('encontrado')) or r1.get('status') == 'resumo_vazio'
if caminho_b:
    # caminho B: criar/POPULAR DFe via XML da saida
    ...
else:
    # caminho A
    ...
```
E em `criar_dfe_a_partir_do_invoice_saida`: ao achar DFe-resumo existente, **popular** em vez de `IDEMPOTENT_EXISTE` (ler trecho ~1100-1110 e ajustar a condição de idempotência para `populado is True`).

- [ ] **Step 7: Run testes da Skill 7 + orchestrator** — PASS. Run suite `pytest tests/odoo/ -q` — zero regressão.

- [ ] **Step 8: Commit**

```bash
git add app/odoo/estoque/scripts/escrituracao.py app/odoo/estoque/orchestrators/inventario_pipeline.py tests/...
git commit -m "feat(escriturando-odoo): buscar_dfe qualifica DFe-resumo vazio + forca caminho B (C2/G-ENT-2)"
```

---

## Task 3 — C3: `preencher_lotes_picking` fixa company do lote

**Objetivo:** o lote do destino (ex. P-02/06) é resolvido/criado na **company destino** (não arrasta o lote FB). Resolve G-ENT-6 (Model B automatizado).

**Files:**
- Modify: `app/odoo/estoque/scripts/picking.py:1492-1699` (`preencher_lotes_picking`; foco `write_data`/`nova_line` 1632-1665)
- Test: `tests/odoo/services/test_stock_picking_service.py`

- [ ] **Step 1: Ler `preencher_lotes_picking` inteiro (1492-1699)** + a assinatura de `StockLotService.buscar_por_nome` (`app/odoo/services/stock_lot_service.py`).

- [ ] **Step 2: Escrever teste — lote resolvido na company destino**

```python
def test_preencher_lotes_resolve_lote_na_company_destino(svc_e_odoo):
    svc, odoo = svc_e_odoo
    # picking company_id=5 (LF); StockLot resolvido deve ter company 5
    ...
    r = svc.preencher_lotes_picking(
        picking_id=123,
        lotes_data=[{'product_id': 27914, 'lote_nome': 'P-02/06', 'quantidade': 30.56}],
        company_destino=5, dry_run=False)
    assert r['status'] in ('PREENCHIDO', 'DRY_RUN_OK')
    # assert que o lot_id usado pertence a company 5 (mock de buscar_por_nome
    # chamado com company_id=5)
```

- [ ] **Step 3: Run — verificar falha** (parâmetro `company_destino` ainda não existe).

- [ ] **Step 4: Implementar**

1. Assinatura: adicionar `company_destino: Optional[int] = None`. Se None, derivar de `picking.company_id` (read).
2. Antes de criar/atualizar a move.line por `lot_name`, resolver o `stock.lot` explicitamente na company destino:
```python
from app.odoo.services.stock_lot_service import StockLotService
lot_svc = StockLotService(odoo=self.odoo)
lot_id = lot_svc.buscar_por_nome(lote_nome, product_id, company_id=company_destino)
if not lot_id:
    lot_id = lot_svc.criar(lote_nome, product_id, company_id=company_destino)  # confirmar assinatura real
```
3. Passar `lot_id` explícito (não só `lot_name`) no `write_data`/`nova_line` (1632-1665), incluindo `company_id` quando o create de move.line aceitar.
4. Pós-condição (guard): após resolver, validar `lot.company_id == company_destino` (read) e abortar com status claro se divergir (G-ENT-6).

> Respeitar G031 (`stock.lot` é por produto): sempre `buscar_por_nome(nome, product_id, company_id)`.

- [ ] **Step 5: Run testes picking + suite** — PASS, zero regressão.

- [ ] **Step 6: Commit**

```bash
git add app/odoo/estoque/scripts/picking.py tests/odoo/services/test_stock_picking_service.py
git commit -m "feat(operando-picking): preencher_lotes_picking fixa company do lote destino (C3/G-ENT-6)"
```

---

## Task 4 — C4: folha L3 1.3.1 remessa avulsa + nó na árvore

**Files:**
- Create: `app/odoo/estoque/fluxos/1.3.1-remessa-avulsa-insumo.md`

- [ ] **Step 1: Ler `fluxos/README.md`** (convenção/formato de folha) + a folha `1.3-transferencia-completa.md` (modelo).

- [ ] **Step 2: Escrever a folha 1.3.1** seguindo o formato das folhas existentes, com (mínimo):
  - **Quando usar:** remessa inter-company de **insumo direto** (sem BoM) **fora de ciclo de inventário**; ex. INDUSTRIALIZACAO_FB_LF avulsa.
  - **Pré-condições:** saldo já em `{origem}/Estoque/{lote}` (ETAPA 0 = fluxo 2.2); pré-flight C5 `pode_faturar=True`.
  - **Sequência (compõe átomos):**
    1. Skill 5 `criar_picking_inter_company` (linhas diretas: produto+qty+lote; `partner_id` destino; `picking_type` saída; loc origem→trânsito) → `validar_picking_inter_company`.
    2. **G-ENT-1:** Skill 5 `cancelar` o picking-companheiro "TERCEIROS" (server action 1899), em **contexto da company origem** (`allowed_company_ids=[origem]`).
    3. Skill 8 `liberar_faturamento` (ajuste_ids opcional — C1) → `polling_invoice` → `validar_invoice_pos_robo` → `transmitir_sefaz` (**SEFAZ irreversível — confirmação do usuário**).
    4. Skill 7 entrada via `executar_fluxo_l3_1_2_x` (`company_destino`, `lotes_data` com o lote destino — C3 fixa company; **caminho B** forçado p/ INDUSTRIALIZACAO_FB_LF — C2) → `action_post`.
    5. **G-ENT-5:** se PO confirmada sem picking (`FALHA_PASSO_7_SEM_PICKING`) → diagnóstico claro; fallback só se seguro; senão parar.
    6. Auditoria: `consultando-quant-odoo` confirma saldo `{destino}/Estoque/{lote_destino}`.
  - **Gotchas:** linkar G-ENT-1/2/5/6 + nota "âncora `AjusteEstoqueInventario` é OPCIONAL aqui (auditoria), não pré-requisito (C1)".
  - **Como o gestor executa:** compõe os átomos em dry-run → plano → confirmação → real; entrada via runner Python que chama `executar_fluxo_l3_1_2_x` (documentar o snippet, espelhando a "Composição Python direto" da folha 1.3).

- [ ] **Step 3: Validar lint do doc**

Run: `git add app/odoo/estoque/fluxos/1.3.1-remessa-avulsa-insumo.md && git commit -m "docs(fluxos): folha 1.3.1 remessa avulsa FB->LF (entry-point avulso C4)"`
Expected: pre-commit lint verde (header doc:meta + seções conforme tipo). Ajustar header se bloquear.

- [ ] **Step 4: Executar Task 0 (prompt) agora** (se ainda não), para o link 1.3.1 resolver.

---

## Task 5 — Canary real (2 produtos)

**Pré-cond:** C1–C5 commitadas + suite verde. Saldo já em `FB/Estoque/MIGRAÇÃO` (quants 267862=30,56 / 267863=5,36); cadastro fiscal OK (Fase 1).

- [ ] **Step 1: Dispatch ao `gestor-estoque-odoo`** (Task tool) com o pedido real: "remessa FB→LF dos produtos 105000002 (30,56kg) e 105000044 (5,36kg), lote destino P-02/06 na LF". O gestor deve ROTEAR sozinho para a folha 1.3.1 (validar que o drift sumiu) e montar o **dry-run** completo.
- [ ] **Step 2: Revisar o plano dry-run do gestor** (picking saída, NF draft CFOP 5901/fp 25, lote destino P-02/06 company LF).
- [ ] **Step 3: Confirmar execução real** até a NF draft; **apresentar a NF ao usuário antes do SEFAZ**.
- [ ] **Step 4: SEFAZ** (confirmação explícita do usuário) → entrada LF → `action_post`.
- [ ] **Step 5: Auditoria final** — `consultando-quant-odoo` confirma `LF/Estoque/P-02/06` = 30,56 + 5,36; baixa correspondente no trânsito.
- [ ] **Step 6: Registrar resultado** no spec/VALIDACAO + memória do projeto (canary REAL OK).

---

## Self-review (coverage do spec)

- spec §4 C1 → Task 1 ✅ · C2 → Task 2 ✅ · C3 → Task 3 ✅ · C4 → Task 4 ✅ · C5 → Task 0 ✅
- spec §5 testes determinísticos → Tasks 1/2/3 com pytest ✅
- spec §6 canary → Task 5 ✅
- spec §3.2 G-ENT-1/2/5/6 → G-ENT-2 (Task 2), G-ENT-6 (Task 3), G-ENT-1/G-ENT-5 (Task 4 folha) ✅
- Ambiguidade conhecida: assinaturas reais de `StockLotService.criar`/`buscar_por_nome` e o campo exato de "autorizado" (`situacao_nf` vs `l10n_br_status`) devem ser confirmadas ao ler o código no início das Tasks 1/3 (steps de leitura incluídos).
