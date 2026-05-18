# QUICK START — Nova Sessão Inventário 2026-05

**Data do checkpoint:** 2026-05-17 (fim de dia)
**Branch:** `main` (tudo commitado e mergeado)

---

## 🎯 PROMPT PRONTO PARA COLAR NA NOVA SESSÃO

```
Continuo trabalho de Inventário 2026-05. Status checkpoint em
docs/inventario-2026-05/QUICK_START_NEXT_SESSION.md.

Próximo passo: rodar F7.1 (extrair estoque do Odoo prod via XML-RPC,
~2-5min, gera 3 Excels + /tmp/estoque_odoo_2026_05.json). Em seguida
F7.3 (confronto, gera diff JSON + 3 Excels com colunas lote_inferido +
validade_divergente) e F7.4 --propor (popular ajuste_estoque_inventario
status=PROPOSTO).

Antes de rodar:
1. git pull origin main
2. pytest tests/odoo/ -p no:randomly  (deve retornar 97 passed)
3. Verificar se /tmp/inventario_fisico_2026_05.json existe (483KB)
   — se sumiu (reboot WSL), re-rodar F7.2 com planilha:
   python scripts/inventario_2026_05/02_carregar_inventario_xlsx.py \
     --xlsx "/mnt/c/Users/rafael.nascimento/Downloads/COMPILADO INV. 16.05.2026.xlsx"
4. Ler docs/inventario-2026-05/SOT.md (estado atual)
5. Ler docs/inventario-2026-05/QUICK_START_NEXT_SESSION.md (este arquivo)

Autorizado a rodar F7.1 → F7.3 → F7.4 --propor em sequência. Pausar
APENAS quando F7.4 --propor estiver pronto, para revisar via --listar-onda
antes de aprovar.
```

---

## ✅ O que está PRONTO

### Services (97 tests/odoo passing)
- **F3** `StockPickingService` — criar/confirmar/validar/cancelar picking + liberar_faturamento + aguardar_invoice_do_robo (13 tests)
- **F4** `InventarioPipelineService` — 5 métodos batch f5a..f5e + auditoria granular via `OperacaoOdooAuditoria` (29 tests)
- **F5** `IndisponibilizacaoEstoqueService` — canary_lote/_local + indispor/reverter + auditoria (15 tests)

### Scripts F7.1-7.4 (preparação)
- `01_extrair_estoque_odoo.py` — extrai stock.quant FB/CD/LF
- `02_carregar_inventario_xlsx.py` — parser robusto (headers por nome, lote/validade tipos misturados, outliers)
- `03_confrontar_inv_vs_odoo.py` — diff com P6 (mais novo se inv sem lote) + cross-check validade
- `04_propor_ajustes.py` — popular `AjusteEstoqueInventario` (status=PROPOSTO) + listar/aprovar com hash da onda

### Planilha real já processada
- Path: `/mnt/c/Users/rafael.nascimento/Downloads/COMPILADO INV. 16.05.2026.xlsx`
- 2087 linhas válidas (FB:276 / CD:1373 / LF:438), 113 sem lote (5.4%), 1297 com validade (62%)
- JSON intermediário: `/tmp/inventario_fisico_2026_05.json` (483KB — **EFÊMERO**, pode sumir em reboot)

### Auditoria habilitada
- Tabela `ajuste_estoque_inventario` (negócio — fase_pipeline, chave_nfe)
- Tabela `operacao_odoo_auditoria` (técnica — 1 row por chamada Odoo lógica, payload/resposta/tempo_ms/erro)

---

## ⏸️ O que está PENDENTE

### F7.5-7.10 (canaries + execução + reconciliação)
- 7.5 `05_canary_estoque_staging.py` — testa indisponibilizar em staging
- 7.6 `06_canary_nfs_referencia.py` — testa fiscal_position correto
- 7.7-7.9 `07/08/09_executar_onda*.py` — wrappers que chamam `InventarioPipelineService`
- 7.10 `10_reconciliar_pos_ajuste.py` — re-extrai estoque + valida diff zerou

### F8 docs (2 playbooks)
- `OPERACOES_FISCAIS_NACOM_LF.md`
- `OPERACOES_LOTE_E_INDISPONIBILIZACAO.md`

### F9 execução operacional (bloqueada por F7.5-7.10)

### F6 hooks (🚫 CANCELADA — redundante. Ver SOT §6.1)

---

## 🔧 PIPELINE OPERACIONAL — Comandos para rodar (em ordem)

```bash
# 1. Extrair estoque do Odoo prod (XML-RPC, ~2-5min)
python scripts/inventario_2026_05/01_extrair_estoque_odoo.py
# → docs/inventario-2026-05/07-relatorios/estoque-odoo-{FB,CD,LF}.xlsx
# → /tmp/estoque_odoo_2026_05.json

# 2. (Se /tmp sumiu) re-carregar planilha do inventário
python scripts/inventario_2026_05/02_carregar_inventario_xlsx.py \
    --xlsx "/mnt/c/Users/rafael.nascimento/Downloads/COMPILADO INV. 16.05.2026.xlsx"
# → /tmp/inventario_fisico_2026_05.json

# 3. Confrontar (gera diff JSON + 3 Excels com lote_inferido + validade_divergente)
python scripts/inventario_2026_05/03_confrontar_inv_vs_odoo.py
# → docs/inventario-2026-05/07-relatorios/diff-inv-vs-odoo-{FB,CD,LF}.xlsx
# → /tmp/diff_inventario_2026_05.json

# === PAUSAR AQUI — REVISAR Excels diff antes de popular DB ===

# 4. Propor ajustes (popular ajuste_estoque_inventario com status=PROPOSTO)
python scripts/inventario_2026_05/04_propor_ajustes.py --propor

# 5. Listar onda + ver hash
python scripts/inventario_2026_05/04_propor_ajustes.py --listar-onda=1
# (anotar hash impresso)

# 6. Aprovar onda travando conjunto via hash
python scripts/inventario_2026_05/04_propor_ajustes.py \
    --aprovar-onda=1 --hash=<sha> --usuario=rafael
# → status='APROVADO', aprovado_em=now, aprovado_por=rafael
```

**Ondas:**
- 1: industrializacao/perda/dev (LF↔FB e LF↔CD)
- 2: transferencias filiais (CD↔FB)
- 3: indisponibilização (requer F7.9 — pendente)
- 4: renomear lote

---

## 📋 DECISÕES IMPORTANTES DESTA SESSÃO

| Decisão | Justificativa |
|---------|---------------|
| F6 CANCELADA | 4 dos 5 hooks redundantes com services já implementados; .md efêmero em prod Render |
| F7 escopo: 7.1-7.4 só | Preparação (sem WRITE Odoo). 7.5-7.10 quando planilha for ser executada de fato |
| P6 regra 3 = "mais novo" para inv sem lote | Apenas no caminho específico (inv vazio); preserva regra original para outros usos |
| VALIDADE_DIVERGENTE: log + aviso | Não bloqueia ajuste, operador decide caso a caso |
| Outliers cod nao-digito ('C','S' em CD): skip | Erros de digitação da planilha |
| Auditoria F4+F5 instrumentada | Gap original — tabela `operacao_odoo_auditoria` ficaria vazia sem isso |
| Lote string sempre | Planilha LF tem 271 lotes como int — converter |
| `"S/INF"/"S/ INF"` = validade vazia | Casos LF — não tentar parsear como data |

---

## 🐛 GOTCHAS para SEMPRE LEMBRAR (já em memória persistente)

- **[`gotcha_query_mapper_init_test.md`]**: em tests, `Model.query.filter_by()` pode disparar `configure_mappers()` que falha por `Mapper[Embarque]`. Usar SQL bruto via `db.session.execute(text(SQL))` em tests novos.
- **[`gotcha_commit_service_vaza_savepoint.md`]**: `db.session.commit()` em service vaza dados do savepoint do fixture `db` para o DB persistente. Usar `flush()` em service; caller commita. OU receber objetos direto, não buscar por query interna.
- **Campo `acao` em `OperacaoOdooAuditoria` é `String(20)`**: abreviar (`liberar_faturamento`, não `action_liberar_faturamento`).
- **Falha de auditoria NÃO deve quebrar pipeline real**: `_registrar_op` envolve em `try/except + logger.error` (non-blocking).
- **Padrão F4 "Odoo I/O paralelo + DB serial main thread"**: `ThreadPoolExecutor` sem `app_context` falha em `db.session.commit()` na thread filha. Workers retornam dict; DB writes ficam no main thread.

---

## 📚 ARQUIVOS DE REFERÊNCIA (em ordem de leitura)

1. **Este arquivo** — kickstart
2. `app/agente/prompts/prompt_inventario.md` — **INTENÇÃO ORIGINAL** do Rafael (regras de negócio, ordem das operações, workflow, regras invioláveis). Não é SOT operacional mas é o "porquê" de tudo
3. `docs/inventario-2026-05/SOT.md` — estado completo + decisões
4. `docs/superpowers/plans/2026-05-17-ajuste-inventario-nacom-lf.md` — plano detalhado por task
5. `docs/inventario-2026-05/00-decisoes/D000-D003.md` + `01-premissas/` + `02-gotchas/` — contexto fiscal/técnico
6. `memory/inventario_2026_05.md` — memória persistente (auto-carregada via `MEMORY.md`)

### Cobertura prompt original × implementação atual

| Item do prompt | Status |
|---|---|
| `<regra inviolável>` linha 135: renomear lote (estoque L1, inv L2) | ✅ P9 + `RENOMEAR_LOTE` em F7.3+F7.4 |
| `<estado_desejado>` linha 144: indisponibilização contábil (opção 1 lote, opção 2 local) | ✅ F5 `IndisponibilizacaoEstoqueService` |
| `<workflow>` linha 119: relatório/sequenciamento movimentações | ✅ F7.3 Excel + F7.4 hash da onda |
| `<workflow>` linha 120: aprovação humana das movimentações | ✅ F7.4 `--aprovar-onda --hash=<sha>` |
| `<workflow>` linha 121: 1 NF referência por tipo de movimentação | ⚠️ MATRIZ_INTERCOMPANY tem NFs ref (94457/13075/147772/94410) mas **F7.6 canary fiscal ainda pendente** |
| `<workflow>` linha 122: verificar campos NF emissão × NF ref | ⚠️ pendente F7.6 |
| `<workflow>` linha 123: 1 movimentação pequena (canary) antes do bulk | ⚠️ pendente F7.7 (precisa canary fiscal por CFOP antes do bulk) |
| `<workflow>` linha 124: operações sem rollback exigem aprovação | ✅ F4 idempotency + abort em config + audit granular |
| `<regras inviolaveis>` linha 132: hooks determinísticos | 🚫 CANCELADA (decisão usuário — services já protegem) |

---

## 🚨 SE ALGO DER ERRADO

### `/tmp/inventario_fisico_2026_05.json` sumiu (reboot WSL)
```bash
python scripts/inventario_2026_05/02_carregar_inventario_xlsx.py \
    --xlsx "/mnt/c/Users/rafael.nascimento/Downloads/COMPILADO INV. 16.05.2026.xlsx"
```

### Tests falhando após mudanças em service (poluição de DB)
```bash
python -c "
import os; os.environ['TESTING']='true'
from app import create_app, db
with create_app().app_context():
    db.session.execute(db.text(\"DELETE FROM ajuste_estoque_inventario WHERE ciclo LIKE 'TEST_%'\"))
    db.session.execute(db.text(\"DELETE FROM operacao_odoo_auditoria WHERE contexto_ref LIKE 'TEST_%' OR external_id LIKE '%TEST%'\"))
    db.session.commit()
"
```

### Odoo XML-RPC timeout no F7.1
- F7.1 lê stock.quant com paginação (limit=500). Para 3 companies pode levar 2-5min em prod.
- Se passar de 10min: investigar conectividade Odoo + circuit breaker (`app/odoo/utils/circuit_breaker.py`)

### Diff F7.3 tem QUANTIDADE_LOTE_INFERIDO em produto inesperado
- Significa que inventário não trouxe lote para esse produto + Odoo tem múltiplos lotes
- F7.3 escolheu o mais novo (P6.regra3 com `usar_mais_novo=True`)
- Revisar manualmente no Excel diff: coluna `lote_inferido=SIM` + `lote_odoo=<o que foi escolhido>`
- Se errado, corrigir planilha (informar lote correto) e re-rodar F7.2 + F7.3

### Validade divergente em massa
- Coluna `validade_divergente=SIM` no Excel diff
- Não bloqueia ajuste (decisão usuário 2026-05-17)
- Investigar caso a caso: pode ser data errada no inventário OU lote diferente fisicamente
