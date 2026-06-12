<!-- doc:meta
tipo: state
camada: L3
sot_de: —
hub: docs/inventario-2026-05/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# SOT — Inventário 2026-05 NACOM/LF

> **Papel:** SOT — Inventário 2026-05 NACOM/LF.

## Indice

- [1. O QUE É ESTE TRABALHO](#1-o-que-é-este-trabalho)
- [2. DOCUMENTOS-CHAVE (SOT em ordem de leitura)](#2-documentos-chave-sot-em-ordem-de-leitura)
- [3. ESTADO POR FASE](#3-estado-por-fase)
  - [Foundation (concluída)](#foundation-concluída)
  - [Implementação (pendente)](#implementação-pendente)
  - [§6.1 — Justificativa do cancelamento de F6](#61-justificativa-do-cancelamento-de-f6)
  - [§7.2 — Ajustes em F7.2/F7.3 após inspeção da planilha real (2026-05-17)](#72-ajustes-em-f72f73-após-inspeção-da-planilha-real-2026-05-17)
  - [§7.4.2 — Piloto 210030325 LF EXECUTADO + 5 fixes generalizados (2026-05-18 fim do dia)](#742-piloto-210030325-lf-executado-5-fixes-generalizados-2026-05-18-fim-do-dia)
  - [§7.4.3 — D004 GENERALIZADA para FB+CD (2026-05-18 fim do dia)](#743-d004-generalizada-para-fbcd-2026-05-18-fim-do-dia)
  - [§7.4.1 — REFINAMENTO 2026-05-18: TRANSFERIR quantidade entre lotes (sem renomear)](#741-refinamento-2026-05-18-transferir-quantidade-entre-lotes-sem-renomear)
  - [§7.4 — Refator F7.3/F7.4: rename + diferença líquida + lote MIGRACAO (2026-05-17 final do dia)](#74-refator-f73f74-rename-diferença-líquida-lote-migracao-2026-05-17-final-do-dia)
  - [§7.5 — Teste piloto end-to-end: produto `210030325` LF (definido pelo usuário 2026-05-17 fim do dia)](#75-teste-piloto-end-to-end-produto-210030325-lf-definido-pelo-usuário-2026-05-17-fim-do-dia)
  - [§7.3 — Auditoria habilitada em F4/F5 (decisão usuário 2026-05-17)](#73-auditoria-habilitada-em-f4f5-decisão-usuário-2026-05-17)
  - [Tarefas técnicas pendentes ao final (G003 sugestão de refator)](#tarefas-técnicas-pendentes-ao-final-g003-sugestão-de-refator)
- [4. PRÓXIMA SESSÃO — COMO RETOMAR](#4-próxima-sessão-como-retomar)
  - [Opção A: Subagent-driven (recomendado para Fases 3 e 4)](#opção-a-subagent-driven-recomendado-para-fases-3-e-4)
  - [Opção B: Sessão direta sequencial](#opção-b-sessão-direta-sequencial)
  - [Opção C: Híbrido (Recomendado por mim)](#opção-c-híbrido-recomendado-por-mim)
- [5. CHECKLIST PARA NOVA SESSÃO](#5-checklist-para-nova-sessão)
- [6. PROMPT INICIAL (status: ainda válido como referência)](#6-prompt-inicial-status-ainda-válido-como-referência)
- [7. RISCOS CONHECIDOS](#7-riscos-conhecidos)
  - [Desvios do plano aplicados em F4 (necessários, não opcionais)](#desvios-do-plano-aplicados-em-f4-necessários-não-opcionais)
  - [Bugs encontrados em code-review pós-F4 e corrigidos (3 reviewers paralelos)](#bugs-encontrados-em-code-review-pós-f4-e-corrigidos-3-reviewers-paralelos)
  - [Bugs MEDIUM não corrigidos (acceptable risks)](#bugs-medium-não-corrigidos-acceptable-risks)
- [8. ARTEFATOS PERSISTIDOS](#8-artefatos-persistidos)
  - [Em `main` (origin sincronizado)](#em-main-origin-sincronizado)
  - [Pendente de criar](#pendente-de-criar)
- [9. COMO ATUALIZAR ESTE SOT](#9-como-atualizar-este-sot)
- [Atualizado](#atualizado)
- [Estado atual](#estado-atual)
- [Pendencias](#pendencias)

**Source of Truth macro do trabalho.** Lido por nova sessão Claude Code (ou subagentes) para retomar de onde parou.

**Última atualização:** 2026-05-20 madrugada (**D013** — ajuste FB+CD por planilha De→Para Estoque↔Indisponível; 98/101 CD + 2154/2259 FB EXECUTADO, 108 exceções P13; `FB/Estoque`/`CD/*` como origem = **wildcard** sub-locations). Anterior: 2026-05-20 (D012 — ajuste LF por planilha direta) · 2026-05-19 tarde (D011 — locais `{emp}/Indisponivel`; FB=31088, SC=31089, CD=31090, LF=31091) · 2026-05-19 ~08:00 (D010 — direção MIGRAÇÃO por sinal de diff_qtd; ~11.762 transferências via scripts 15+15r)
**Status global:** Foundation + F3 + F4 + F5 completas + PILOTO END-TO-END + D006/D007 + **Pre-etapa CD CONCLUIDA** (6920 EXECUTADO, 97,98%) + **Onda 2 FB→CD operacionalizada via D009** (20 ajustes + 20 splits EXECUTADO em 3 batches / 3 NFs SEFAZ SDTRA/2026/0867-0869). Batch 3a (18 ajustes) travado por robô CIEL IT (ver G032). Restam 17 PROPOSTO insolúveis (saldo FB físico < pedido) + 10 FALHA Cat1 (admin Odoo) + 1 APROVADO drift pendente. **D010 (2026-05-19)**: regra inviolável `diff_qtd>0 → lote→MIGRAÇÃO`, `diff_qtd<0 → MIGRAÇÃO→lote` para qualquer planilha gerada pelo pipeline `monitor/`. Restam ~5.281 linhas na aba 5_Diff_Por_Lote do MONITOR_DIFF 2026-05-19_07-58 ainda divergentes.

---

## 1. O QUE É ESTE TRABALHO

Conduzir os ajustes de estoque decorrentes do inventário físico realizado em 16/05/2026 nas empresas:

- **NACOM GOYA** filiais FB (`company_id=1`) e CD (`company_id=4`)
- **LA FAMIGLIA** (`company_id=5`, prestadora de industrialização)
- SC (`company_id=3`) **fora de escopo nesta fase**

Os ajustes saem por NF entre empresas (CFOPs 5901/5903/5949/5152/5151) seguindo o padrão NACOM real: **picking → robô CIEL IT → Playwright SEFAZ** (não `account.move` direto).

**Filosofia:** infraestrutura reutilizável para operações diárias (transferências, devoluções, industrialização) — inventário é o primeiro consumidor, não o caso especial.

---

## 2. DOCUMENTOS-CHAVE (SOT em ordem de leitura)

| Documento | Conteúdo | Lido por |
|-----------|----------|----------|
| **`CHECKPOINT_2026_05_18_PILOTO_COMPLETO.md`** | **Snapshot apos piloto OK — estado atual completo** | **PRIMEIRO em sessao nova** |
| **`QUICK_START_NEXT_SESSION.md`** | **Prompt pronto + tarefas para bulk onda 1** | **PRIMEIRO em sessao nova** |
| `CHECKPOINT_2026_05_17_FIM_DIA.md` | Snapshot pre-piloto (historico) | Apenas referencia |
| `00-decisoes/D006-...md` | TRANSFERIR vs RENOMEAR + 5 licoes aprendidas piloto | Antes de codar bulk |
| Este arquivo (`docs/inventario-2026-05/SOT.md`) | Estado macro, próximos passos | TODOS (humanos, Claude, subagentes) |
| `docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md` | Spec v3 (pipeline batches) | Antes de qualquer codificação |
| `docs/superpowers/plans/2026-05-17-ajuste-inventario-nacom-lf.md` | Plano detalhado com código por task | Durante implementação (5164 linhas) |
| `app/agente/prompts/prompt_inventario.md` | Prompt inicial do usuário (intenção/regras de negócio) | Para entender o "porquê" |
| `docs/inventario-2026-05/00-decisoes/D000-D005.md` | Decisões formais com fontes (D004/D005 = rename + MIGRACAO) | Quando dúvida sobre estrutura |
| **`docs/inventario-2026-05/00-decisoes/D010-direcao-transferencia-migracao-por-sinal-diff_qtd.md`** | **REGRA INVIOLÁVEL: direção MIGRAÇÃO depende do sinal de diff_qtd** (`>0` lote→MIGRAÇÃO, `<0` MIGRAÇÃO→lote) | **OBRIGATÓRIO antes de qualquer script de transferência MIGRAÇÃO** |
| **`docs/inventario-2026-05/00-decisoes/D011-locais-indisponivel-por-empresa.md`** | **Locais `{emp}/Indisponivel` (FB=31088 / SC=31089 / CD=31090 / LF=31091) como contraparte de ajustes CD/FB** (negativo → Indisponivel/MIGRACAO; positivo → Indisponivel→Estoque/lote_real) | **OBRIGATÓRIO antes de qualquer NOVO script de ajuste CD/FB pós-2026-05-19** |
| **`docs/inventario-2026-05/00-decisoes/D012-ajuste-estoque-lf-via-planilha-direta.md`** | **Ajuste LF por planilha via inventory adjustment PURO** (criar saldo Pasta16 / realocação net-zero Pasta17). `P-15/05` muda de sentido por planilha; redução multi-local 42→53→(39/38); net-zero atômico | **OBRIGATÓRIO antes de ajuste LF por planilha direta (2026-05-20+)** |
| **`docs/inventario-2026-05/00-decisoes/D013-ajuste-fb-cd-indisponivel-via-planilha-de-para.md`** | **Ajuste FB+CD por planilha De-Local/De-Lote → Para-Local/Para-Lote** (Estoque↔Indisponível, inventory adjustment 2 passos). Origem `FB/Estoque`/`CD/Estoque`/`CD/*` = **wildcard** sub-locations; De-Lote vazio = `P-15/05`; `MIGRAÇÃO` = variante com saldo na loc (G036). Script `ajuste_fb_cd_indisponivel.py` | **OBRIGATÓRIO antes de ajuste FB/CD por planilha De→Para (2026-05-20+)** |
| **`docs/inventario-2026-05/00-decisoes/D014-cfop-entradas-e-operacoes-referencia.md`** | **CFOP de ENTRADA + regra por tipo de produto** (5901/5124/5902/5903/5949/5921) + entradas confirmadas (1901/1903/1949/1151/1152/1124/1902) + operações de referência `venda-industrializacao` (5124+5902) e `vasilhame` (5921). **5902 NUNCA é produto acabado**; SARET tipo 4 com 5902 = erro. Corrige D002 (vasilhame fp 64) | **Antes de emitir/auditar NF intercompany LF↔FB/CD** |
| `docs/inventario-2026-05/01-premissas/P001-P011.md` | Premissas confirmadas com origem | Quando dúvida sobre regra |
| `docs/inventario-2026-05/02-gotchas/G001-G004.md` | Armadilhas descobertas + solução | Antes de codar área afetada |
| **`docs/inventario-2026-05/02-gotchas/G036-lote-virgula-literal-e-duplicado-operador-igual.md`** | **Lote com vírgula = literal real (não split); lotes duplicados + bug operador `=` → resolver lot_id via `in`** | Antes de qualquer busca de saldo por nome de lote |

---

## 3. ESTADO POR FASE

Leitura: `✅ feito` / `⏳ pendente` / `⚠️ parcial` / `🚫 bloqueado` / `📝 documentado mas não codado`

### Foundation (concluída)

| Fase | Status | Artefato | Tests |
|------|--------|----------|-------|
| **F0** Audit Run | ✅ | 5 scripts em `scripts/inventario_2026_05/00*.py` + D000, D001, D002, D003 + G001, G002, G003, G004 | — (read-only) |
| **F1.1** Constants | ✅ | `app/odoo/constants/operacoes_fiscais.py` + `locations.py` | 17 ✅ |
| **F1.2** Migration `operacao_odoo_auditoria` | ✅ | `scripts/migrations/2026_05_18_operacao_odoo_auditoria.{py,sql}` + `app/odoo/models/operacao_odoo_auditoria.py` | 4 ✅ |
| **F1.3** Migration `ajuste_estoque_inventario` | ✅ | `scripts/migrations/2026_05_18_ajuste_estoque_inventario.{py,sql}` + `app/odoo/models/ajuste_estoque_inventario.py` | 4 ✅ |
| **F1.x** ALTER pipeline | ✅ | `scripts/migrations/2026_05_19_add_fase_pipeline.{py,sql}` (D003) | — (verificação no script) |
| **F1.x** ALTER lote_origem/destino | ✅ | `scripts/migrations/2026_05_17_add_lote_destino_ajuste.{py,sql}` (D004/D005) — 2 colunas VARCHAR(60) | — (verificação no script) |
| **F1.x** `build.sh` | ✅ | Items 19/20/21 adicionados (commit `6737d907`). **TODO**: adicionar item 22 com a nova migration | bash -n OK |
| **F2** `stock_lot_service.py` | ✅ | `app/odoo/services/stock_lot_service.py` (criar/renomear/inativar/reativar/atualizar_validade/buscar_por_nome) | 15 ✅ |
| **F3** `stock_picking_service.py` | ✅ | `app/odoo/services/stock_picking_service.py` (criar_transferencia/confirmar_e_reservar/preencher_qty_done/validar/cancelar/liberar_faturamento/aguardar_invoice_do_robo) | 13 ✅ |
| **F4** `inventario_pipeline_service.py` | ✅ | `app/odoo/services/inventario_pipeline_service.py` (f5a..f5e + helper resolver_location_destino + helper _registrar_op) — auditoria granular via OperacaoOdooAuditoria | 29 ✅ |
| **F5** `indisponibilizacao_estoque_service.py` | ✅ | `app/odoo/services/indisponibilizacao_estoque_service.py` (canary_lote/_local + indispor/reverter_lote/_local + helper _registrar_op) — auditoria granular | 15 ✅ |

### Implementação (pendente)

| Fase | Status | Próximo passo | Bloqueio? |
|------|--------|---------------|-----------|
| **F6** Hooks determinísticos | 🚫 **CANCELADA** | — | Decisão usuário 2026-05-17 — ver §6.1 |
| **F7** Scripts datados (10 scripts) | ⚠️ 7/10 (preparacao 4 + piloto 3 + bulk 0/3) | F7.5-7.10 bulk completo. PILOTO 210030325 LF EXECUTADO ✅ (2026-05-18). | Liberado |
| **F8** Documentação (2 playbooks + estrutura) | ⏳ 4 tasks | Task 8.1 (estrutura pastas — JÁ PARCIAL) | Não |
| **F9** Execução operacional | ⚠️ piloto OK, bulk pendente | Construir 09_executar_onda1_bulk.py | Bloqueio: bulk wrapper |

### §6.1 — Justificativa do cancelamento de F6

**4 dos 5 hooks são redundantes** — proteção já está nos services:

| Hook proposto | Equivalente existente |
|---------------|----------------------|
| `pre_execute_nf` regras 1-2 (status=APROVADO, aprovado_em) | Caller filtra `AjusteEstoqueInventario.query.filter_by(status='APROVADO')` antes de chamar f5a |
| `pre_lote_rename` | `StockLotService.renomear()` (F2) — mesma regra idêntica |
| `pre_execute_indisponibilizacao` | `IndisponibilizacaoEstoqueService.indisponibilizar_lote/local` raise se `canary_passou=False` |
| `pos_execute_nf` → `db.session.commit()` | F4 já commita em cada fase do pipeline |

**`pos_execute_nf` → gera `.md` em `04-movimentacoes/`**: não funciona em Render (filesystem efêmero, deploys reescrevem). Auditoria real já tem 2 caminhos: tabela `OperacaoOdooAuditoria` (polimórfica) + `AjusteEstoqueInventario.fase_pipeline/erro_msg/chave_nfe/picking_id_odoo/invoice_id_odoo` (granular).

**`pre_commit_docs.sh`**: só faria sentido se houvesse os `.md` (cancelados acima).

**Únicas 2 regras NÃO cobertas em código**:
- Divergência custo médio inv vs Odoo > 20% (sinal de produto errado)
- Teto financeiro da onda (limite de exposição por execução)

Decisão: operador valida custo/teto on-the-fly em F7 (inline no script de execução, não como hook separado).

### §7.2 — Ajustes em F7.2/F7.3 após inspeção da planilha real (2026-05-17)

Planilha `COMPILADO INV. 16.05.2026.xlsx` (84KB, 3 abas FB/CD/LF, 2091 linhas) revelou que:

| Achado | Aba afetada | Decisão |
|--------|-------------|---------|
| Headers **divergem por aba** (CD: 4 cols `CODIGO\|LOTE\|VALIDADE\|QTD`; FB: 7 cols `CODIGO\|DESCRIÇÃO\|VALIDADE\|LOTE \|QTD\|MEDIDA\|LOCAL` com `LOTE ` espaço; LF: 5 cols `CODIGO\|PRODUTO\|QTD\|LOTE\|VALIDADE`) | Todas | F7.2 detecta colunas por nome (case-insensitive), não posição. HEADER_ALIASES |
| Lote misturado int (271)/str (91) | LF principalmente | F7.2 converte sempre para str via `str(lote).strip()` |
| Lote vazio: 113 linhas (5.4%) — 2 FB, 31 CD, **80 LF** (18%) | Todas, LF dominante | F7.3 P6.regra3 ganha parametro `usar_mais_novo=False` default; True quando inv sem lote. Nova `tipo_divergencia='QUANTIDADE_LOTE_INFERIDO'` com `lote_inferido=True` + `linhas_inv_origem` (rastreabilidade) |
| Validade: 1297 linhas com data (62%) + 19 `'S/INF'/'S/ INF'` + 772 vazias | Todas | F7.2 parser: datetime→ISO, S/INF→None, string→tenta parse (ISO/BR DD/MM/YYYY). Novo campo `validade_inv` no JSON |
| Outliers cod em CD: 2 começando com letra (`'C'`, `'S'`) | CD | F7.2 skip silencioso com count (decisão usuário) |
| Cross-check validade inv vs Odoo `stock.lot.expiration_date` | F7.3 | Flag `validade_divergente=True` + `validade_msg` no diff. Log AVISO durante execução, não bloqueia ajuste (decisão usuário) |
| Tipos de produto: 1, 2, 4 (sem tipo 3) | — | Esperado |

**Pipeline atualizado (após estes ajustes):**
1. `python 01_extrair_estoque_odoo.py` → `/tmp/estoque_odoo_2026_05.json`
2. `python 02_carregar_inventario_xlsx.py --xlsx 'COMPILADO INV. 16.05.2026.xlsx'` → `/tmp/inventario_fisico_2026_05.json` ✅ **rodado, 2087 linhas válidas**
3. `python 03_confrontar_inv_vs_odoo.py` → `/tmp/diff_inventario_2026_05.json` + 3 Excels diff (com colunas `lote_inferido`, `validade_divergente`, `validade_msg`)
4. `python 04_propor_ajustes.py --propor` → `AjusteEstoqueInventario` (status=PROPOSTO)

### §7.4.2 — Piloto 210030325 LF EXECUTADO + 5 fixes generalizados (2026-05-18 fim do dia)

**Resultado**: piloto end-to-end EXECUTADO em PROD com sucesso. NF-e
SEFAZ autorizada (chave `35260518467441000163550010000131491006086070`,
cstat=100). Commit `a8e0d0bb`.

**Estado fisico no Odoo**:
- LF: lote `26014` consolidado com **82.300 un** (2 quants: loc 42 com
  74.404 + loc 53 com 7.896 — bate inventario fisico)
- 5 quants antigos zerados (sem lote, 24715×2, 3009/24, MIGRAÇÃO)
- Picking 317290 (LF→Parceiros/Clientes virtual, state=done)
- Invoice 608607 RETNA/2026/00029 (posted, SEFAZ autorizado)
- 6 ajustes DB: status=EXECUTADO

**5 fixes descobertos durante o piloto, generalizados no codigo** — ver
`00-decisoes/D006-...md` secao "Licoes aprendidas":

| # | Fix | Onde |
|---|---|---|
| L1 | `StockPickingService` defaults `incoterm=6 (CIF)` + `carrier_id=996 (NACOM)` | `stock_picking_service.py` |
| L2 | `_resolver_cids_e_menu(company_id)` — LF=5/217, NACOM=1-3-4/124 | `playwright_nfe_transmissao.py` |
| L3 | `_fechar_modais_tecnicos()` antes de cada click | `playwright_nfe_transmissao.py` |
| L4 | `_tratar_wizard_confirmacao()` apos Transmitir NF-e | `playwright_nfe_transmissao.py` |
| L5 | `_garantir_payment_provider()` em F5d (`PAYMENT_PROVIDER_SEM_PAGAMENTO=38`, fallback reset_to_draft+post) | `inventario_pipeline_service.py` |

**Testes**: 117 passing (97 baseline + 20 novos — `criar_se_nao_existe`,
`StockInternalTransferService`, defaults incoterm/carrier).

**Extrator pos-execucao**: corrigido apos piloto. Bugs originais:
- `RENOMEAR_LOTE`: validava nome do lote ao inves de qty no lote_destino
- `PERDA_LF_FB`: comparava com FB destino (mas FB nao recebe estoque)
- `stock.lot.active`: campo nao existe nesta versao (read+search falham)

Fix: validar qty no `qty_no_lote_alvo_origem` para TRANSFERIR; para
PERDA_LF_FB validar apenas pipeline completo (picking done + invoice
posted + chave_nfe).

**Proximo bloqueio**: construir `09_executar_onda1_bulk.py` que itera
por (cod_produto, company_id) para os 1.065 ajustes restantes. Padrao
estabelecido pelo `teste_210030325_lf.py`.

### §7.4.3 — D004 GENERALIZADA para FB+CD (2026-05-18 fim do dia)

Apos piloto LF OK, a logica D004 (rename+diferenca liquida) foi
generalizada para TODAS as 3 companies em escopo:

**Mudanca no script 03 `confrontar_inv_vs_odoo.py`**:
- Removido filtro `if cid == 5` no bloco D004 (~linha 295).
- Logica de agregacao + transferencia de lotes + diferenca liquida
  aplicada a LF (cid=5), FB (cid=1) e CD (cid=4).

**Mudanca no script 04 `propor_ajustes.py:cmd_propor()`**:
- `lote_destino` agora e' RECALCULADO baseado em `acao_decidida`
  (mais autoritativo que default 'MIGRACAO' do script 03).
- Tabela de defaults por acao (ver D004 secao "Generalizacao
  2026-05-18").

**Impacto pratico**:
- Ondas 2 (FB↔CD transferencia, 2.558 ajustes) e 3 (sem ajuste fiscal,
  19.366 ajustes) ainda foram geradas com fluxo antigo "1 diff por
  quant Odoo" (pre-D004). Decisao usuario: regerar ou manter?
- Onda 1 (LF, 1.071 ajustes) ja tinha D004 aplicada — sem impacto.

**Comando para regerar** (idempotente — so insere novos):
```bash
python scripts/inventario_2026_05/03_confrontar_inv_vs_odoo.py
python scripts/inventario_2026_05/04_propor_ajustes.py --propor
# Comparar contadores antes/depois para decidir
```

Ver D004 e D006 para detalhes.

### §7.4.1 — REFINAMENTO 2026-05-18: TRANSFERIR quantidade entre lotes (sem renomear)

Apos analise no dry-run do caso piloto 210030325 LF — ver `00-decisoes/D006-transferir-quantidade-entre-lotes-nao-renomear.md`.

**Mudanca**: o item 1 de D004 ("Renomear lotes Odoo") foi substituido por **TRANSFERIR quantidades especificas entre lotes** via inventory adjustment (`stock.quant.action_apply_inventory`). Motivos:

1. Quant sem lote (`lot_id=False`) nao pode ser renomeado (caso 32677 sem lote, 39.216 un).
2. Renomeio afeta lote inteiro — nao suporta split parcial (caso MIGRAÇÃO 67.220 = 35.188 renomear + 32.032 perda).
3. Multiplos lotes origem → mesmo lote destino viola unique constraint (4 lotes → 26014).

**Servicos novos** (atomicos, reutilizaveis):
- `StockLotService.criar_se_nao_existe(nome, product_id, company_id) → (lot_id, criado)`
- `StockInternalTransferService.transferir_entre_lotes(...)` e `transferir_quantidade_para_lote(...)`
- 18 testes novos (4 criar_se_nao_existe + 14 internal_transfer)
- Total tests: 97 → 115

**Acao no DB**: `acao_decidida='RENOMEAR_LOTE'` permanece como nome (compatibilidade com 644 ajustes ja propostos), mas o EXECUTOR (teste_210030325_lf.py + futuros) interpreta como "transferir qty entre lotes".

### §7.4 — Refator F7.3/F7.4: rename + diferença líquida + lote MIGRACAO (2026-05-17 final do dia)

**Fonte**: instrução usuário após análise do caso `210030325` LF — ver `00-decisoes/D004-rename-lote-diferenca-liquida.md` e `00-decisoes/D005-lote-migracao-consolidador-fantasmas.md`.

**Problema (versão anterior)**:
Para um cod_produto com saldo nos dois lados (Odoo e inventário) mas com lotes disjuntos, F7.3 gerava 1 diff por quant Odoo + 1 diff por linha inv sem match. Caso `210030325` LF (Embalagem):
- Odoo: 5 quants em 4 nomes de lote (`'', 24715×2, 3009/24, MIGRAÇÃO`) totalizando 148.832 un
- Inv: 1 lote (`26014`) com 82.300 un (lote não existe no Odoo)
- Resultado errado: 5 NFs PERDA (LF→FB total -148.832) + 1 NF INDUSTRIALIZACAO (FB→LF +82.300). Implica devolver 148k e remeter 82k — fiscalmente absurdo (82.300 un existem fisicamente, só estão em "lote errado").

**Decisão (D004/D005)**:
1. **Renomear lotes Odoo** (FIFO por `quant_id`) até cobrir o saldo inv → ações `RENOMEAR_LOTE` com `qty_ajuste=0`, `lote_origem=<lote Odoo>`, `lote_destino=<lote inv>`
2. **Diferença líquida apenas** vira 1 NF:
   - Sobra (Odoo > Inv): PERDA_LF_FB com `lote_destino='MIGRACAO'` na FB
   - Falta (Inv > Odoo): INDUSTRIALIZACAO_FB_LF com `lote_destino=<lote inv>` na LF
3. **Custo unitário**: quando lote alvo não tem custo no Odoo (lote novo), usar média ponderada `Σ value / Σ quantity` dos outros quants do cod (`_custo_medio_cod()` em F7.3)
4. **Lote `MIGRACAO`** na FB consolida TODOS os fantasmas (PERDA_LF_FB + TRANSFERIR_CD_FB). Após onda 1+2, lote MIGRACAO da FB será indisponibilizado (Ordem 3 opção 1 do prompt original — validação manual no Odoo UI conforme D005)

**Mudanças de schema**:
- `ajuste_estoque_inventario` ganha `lote_origem VARCHAR(60)` + `lote_destino VARCHAR(60)`
- Model atualizado em `app/odoo/models/ajuste_estoque_inventario.py`
- Migration: `scripts/migrations/2026_05_17_add_lote_destino_ajuste.{py,sql}` (idempotente via `ADD COLUMN IF NOT EXISTS`)
- Aplicada em PROD/local 2026-05-17 22:58. **Pendente**: incluir no `build.sh` (item 22) para deploy Render

**Mudanças de código**:
- `scripts/inventario_2026_05/03_confrontar_inv_vs_odoo.py`:
  - Novo helper `_custo_medio_cod(quants)` (linha ~85)
  - Novo bloco "D004: LF com saldo nos DOIS lados e lotes disjuntos" no `confrontar_company` — gera RENOMEAR_LOTE_PARCIAL + diff de diferença líquida com 1 ajuste por lote residual (preserva rastreio fiscal + respeita VARCHAR(60))
  - Excel diff ganha colunas `lote_origem` + `lote_destino`
  - Aplica **apenas** para `cid=5` (LF) por enquanto — generalização para FB↔CD pendente
- `scripts/inventario_2026_05/04_propor_ajustes.py`:
  - `RENOMEAR_LOTE_PARCIAL` → `RENOMEAR_LOTE` em `calcular_acao_decidida`
  - Insert preenche `lote_origem`/`lote_destino` (do diff OU default por ação: PERDA_LF_FB e TRANSFERIR_CD_FB → MIGRACAO; INDUSTRIALIZACAO_FB_LF/DEV_* → lote_inventariado)

**Validação caso `210030325` LF (após refator)**:
- 4 RENOMEAR_LOTE (vazio + 24715 + 3009/24 + MIGRAÇÃO parcial) totalizando 82.300 un para lote 26014, `qty_ajuste=0`
- 2 PERDA_LF_FB (MIGRAÇÃO residual 32.032 + 24715 segundo quant 34.500) totalizando -66.532 un para lote MIGRACAO na FB, custo R$ 0,6434, valor R$ 42.806,69
- Net: 1 NF de saída (vs 5 anteriores). Sem NF de entrada (vs 1 anterior).

**Estado atual** (23639 PROPOSTO):
- Onda 1 (LF↔FB NF): 1.071 ajustes / R$ 12.776.851
- Onda 2 (FB↔CD transf): 2.558 ajustes / R$ 887.291.961
- Onda 3 (INDISPONIBILIZAR_*): 19.366 ajustes / R$ 4.564.628.280
- Onda 4 (RENOMEAR_LOTE): **644 ajustes** (vs 17 antes) / R$ 0

**Pendências**:
- Generalizar D004 para FB↔CD (atualmente só LF)
- F7.9 ainda pendente — após onda 1+2 executadas, deve gerar 1 INDISPONIBILIZAR_LOTE por cod consolidado no lote MIGRACAO da FB (validação Ordem 3 opção 1 — canary manual no Odoo UI)
- Atualizar `build.sh` com migration 2026_05_17_add_lote_destino_ajuste para deploy Render

### §7.5 — Teste piloto end-to-end: produto `210030325` LF (definido pelo usuário 2026-05-17 fim do dia)

**Decisão**: antes de aprovar/executar onda 1 inteira (1.071 ajustes LF), rodar **UM caso piloto completo** e extrair validação. Critério de sucesso virá: aplicar regra para resto da onda 1 ou ajustar antes.

**Caso escolhido**: produto `210030325` (Embalagem, FRASCO INCOLOR 1,01 L - MOLHO) na LF (cid=5). Já tem 6 ajustes PROPOSTO (ids 139003-139008): 4 RENOMEAR_LOTE (consolidam 82.300 un em lote 26014) + 2 PERDA_LF_FB (66.532 un → MIGRACAO na FB, R$ 42.806,69).

**A construir na próxima sessão** (não construir nesta):
1. `scripts/inventario_2026_05/teste_210030325_lf.py` — wrapper específico, encadeia F2 (4 renames) + F3 (criar picking) + F4 (f5b-e: validar, liberar, aguardar invoice CIEL IT ~3min, transmitir SEFAZ via Playwright). Flag `--dry-run` obrigatória na primeira execução.
2. `scripts/inventario_2026_05/08_extrair_pos_execucao.py` — extrator **replicável por filial** (`--company-id=N`): para cada ajuste EXECUTADO consulta Odoo (lote renomeado? quant atual? invoice emitida? chave SEFAZ?) e gera Excel comparando proposto vs realizado.
3. Canary F7.6 conceitual: comparar NF 13075 (referência histórica PERDA LF→FB CFOP 5903) vs NF que seria gerada — validar fiscal_position_id, l10n_br_tipo_pedido, CFOP.

**Irreversibilidade conhecida**: transmissão SEFAZ via Playwright é irreversível após autorização (workflow item 10 do prompt — operações sem rollback exigem aprovação explícita). **PAUSAR para confirmação do usuário antes da etapa de transmissão**, mesmo após dry-run OK.

**Sucesso = critérios**:
- 4 `stock.lot.name` renomeados na LF para `26014`
- LF cod 210030325: 1 lote `26014` com 82.300 un (consolidado)
- FB cod 210030325 lote `MIGRACAO`: +66.532 un
- 1 NF CFOP 5903 emitida (chave SEFAZ 44 dígitos capturada)
- `operacao_odoo_auditoria` ~12 rows do ciclo desse cod
- Extrator gera Excel comparativo proposto vs realizado (alinhado)

**Bloqueantes**:
- Build de scripts 1+2 acima
- Aprovação da onda 1 (`--aprovar-onda=1 --hash=<sha> --usuario=rafael`)
- Verificar pré-requisitos manuais (Playwright Chromium, credenciais Odoo, certificado SEFAZ válido)

### §7.3 — Auditoria habilitada em F4/F5 (decisão usuário 2026-05-17)

**Gap original**: `operacao_odoo_auditoria` foi criada em F1.2 com helper `.registrar()` mas nenhum service F3/F4/F5 a usava. Ficaria vazia em prod.

**Correção**: helper `_registrar_op()` em ambos services F4 e F5, chamado após cada operação Odoo (granularidade "1 operação lógica = 1 row").

**O que cada tabela contém após ajuste executado:**

| Tabela | Granularidade | Conteúdo |
|--------|---------------|----------|
| `ajuste_estoque_inventario` | 1 row por divergência | Ciclo de vida do ponto de vista de negócio: PROPOSTO → APROVADO → fase_pipeline F5a→F5e → EXECUTADO/FALHA. Campos: qtd_inventario, qtd_odoo, qtd_ajuste, custo_medio, acao_decidida, picking_id_odoo, invoice_id_odoo, **chave_nfe** (44 dígitos SEFAZ), erro_msg |
| `operacao_odoo_auditoria` | 1 row por chamada Odoo lógica | Trilha técnica: payload, resposta_json, tempo_execucao_ms, modelo_odoo, acao (create/button_validate/liberar_faturamento/aguardar_invoice/transmitir_nfe/canary_lote/etc.), status (SUCESSO/FALHA/SKIPPED/TIMEOUT/EXCECAO/PASSOU/NAO_PASSOU), pipeline_etapa (F5a..F5e), executado_por, contexto_origem ('inventario' ou 'indisponibilizacao'), contexto_ref (ciclo ou ajuste_id) |

**Exemplo: 1 ajuste executado com sucesso deixa:**

```
ajuste_estoque_inventario:
  id=42, ciclo='INVENTARIO_2026_05', cod_produto='4320147',
  qtd_ajuste=-5, status='EXECUTADO',
  picking_id_odoo=99999, invoice_id_odoo=200000,
  chave_nfe='35260112345...', fase_pipeline='F5e_SEFAZ_OK'

operacao_odoo_auditoria (5 rows com registro_id=42, contexto_ref='INVENTARIO_2026_05'):
  - pipeline_etapa='F5a' acao='create' modelo_odoo='stock.picking'
    status='SUCESSO' odoo_id=99999 tempo_ms=2300
  - pipeline_etapa='F5b' acao='button_validate' modelo_odoo='stock.picking'
    status='SUCESSO' odoo_id=99999 tempo_ms=4500
  - pipeline_etapa='F5c' acao='liberar_faturamento' modelo_odoo='stock.picking'
    status='SUCESSO' odoo_id=99999 tempo_ms=1200
  - pipeline_etapa='F5d' acao='aguardar_invoice' modelo_odoo='account.move'
    status='SUCESSO' odoo_id=200000 tempo_ms=180000  (3min — robo CIEL IT)
  - pipeline_etapa='F5e' acao='transmitir_nfe' modelo_odoo='account.move'
    status='SUCESSO' odoo_id=200000 tempo_ms=45000   (45s — Playwright + SEFAZ)
```

**Query forensics típica** (algum ajuste falhou):
```sql
SELECT pipeline_etapa, status, erro_msg, tempo_execucao_ms
FROM operacao_odoo_auditoria
WHERE registro_id = <ajuste_id> AND contexto_origem = 'inventario'
ORDER BY id;
```

**Falha de auditoria NÃO bloqueia pipeline** (try/except + logger.error em `_registrar_op`).

### Tarefas técnicas pendentes ao final (G003 sugestão de refator)

- [ ] G005: medir tempo robô CIEL IT em paralelo (5 pickings simultâneos) antes de bulk grande — sem isso, F5d (`f5d_aguardar_invoices`) pode levar 25h em vez de 30min
- [ ] G006: validar `action_liberar_faturamento` em outros picking types além de `Expedição Entre Filiais (FB)` (id=51)
- [ ] Mover `_resolver_picking_type` (hardcoded no plano Task 4.1) para `app/odoo/constants/picking_types.py` se virar fonte de gotcha

---

## 4. PRÓXIMA SESSÃO — COMO RETOMAR

### Opção A: Subagent-driven (recomendado para Fases 3 e 4)

Cada task do plano (`docs/superpowers/plans/...`) tem código completo e tests embutidos. Subagente fresco lê plano, executa task isolada, retorna. Vantagens:

- Tasks 3.1 → 3.4 podem rodar **em paralelo limitado** (cuidado: 3.2 depende de 3.1; 3.3 e 3.4 podem rodar em paralelo)
- F5 independente de F3 — pode rodar em paralelo total
- Cada subagente "redescobre" mínimo (lê plano, executa, sai)
- Reduz risco de context window estourar

**Como invocar:** `superpowers:subagent-driven-development` apontando para o plano.

### Opção B: Sessão direta sequencial

Continuar conversação interativa com Claude Code, uma fase por vez. Vantagens:

- Mais simples (zero overhead)
- Decisões intermediárias podem ser tomadas durante (ex: G005 canary do robô)
- Você acompanha em tempo real

**Como invocar:** Nova sessão → "Continue Fase 3 do plano `docs/superpowers/plans/2026-05-17-ajuste-inventario-nacom-lf.md`"

### Opção C: Híbrido (Recomendado por mim)

- **F3 + F5 em sessão direta** (decisões pontuais ainda podem aparecer — ex: confirmar picking_type por direção)
- **F4 (pipeline service)** via subagent-driven já que tem 5 sub-tasks bem definidas
- **F6 + F7 + F8** em sessão direta (operação real próxima)

---

## 5. CHECKLIST PARA NOVA SESSÃO

Ao começar, faça:

1. [ ] `git pull origin main` para garantir sincronia
2. [ ] `git log --oneline -5` para ver últimos commits (incluindo merge da branch foundation)
3. [ ] Leia este arquivo (`docs/inventario-2026-05/SOT.md`) inteiro
4. [ ] Leia o spec (`docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md`) — focar em §6.2 (arquitetura services) e §8 (pipeline)
5. [ ] Identifique fase a executar e abra plano na seção correspondente
6. [ ] Verifique se há novos GOTCHAS ou ajustes em `02-gotchas/` antes de codar
7. [ ] Rode `pytest tests/odoo/ -v` para confirmar baseline (40 testes devem passar)
8. [ ] Implementar task → testar → commit → próxima task

---

## 6. PROMPT INICIAL (status: ainda válido como referência)

`app/agente/prompts/prompt_inventario.md` (v2 do prompt) continua válido como descrição da **intenção do dono do projeto**. **NÃO é mais SOT operacional** — quem opera deve ler spec/plano/SOT.

O prompt resta útil porque:
- Documenta as **regras de negócio originais** (ordem 1, 2, 3)
- Lista as **NFs de referência** que orientaram o audit (94457, 13075, 147772, 94410)
- Define **filosofia de documentação atômica e regras invioláveis**

O prompt foi **revisado e aprimorado** durante a sessão (v2 inclui ajustes feitos pelo usuário em L1-L8 do brainstorming). Próximas revisões devem ir para o spec (não voltar ao prompt).

---

## 7. RISCOS CONHECIDOS

| Risco | Mitigação |
|-------|-----------|
| Robô CIEL IT serial → F5d toma 25h | Canary G005 antes de bulk grande |
| `action_liberar_faturamento` não existe em todos picking types | Validar via G006 antes de implementar Task 4.3 |
| NF emitida = irreversível após janela SEFAZ | Hooks `pre_execute_nf` bloqueia execução sem aprovação humana |
| `dev-industrializacao FB↔LF` sem precedente histórico | P011 assume fiscal_position por simetria com CD↔LF (74 e 89); validar com canary fiscal antes de bulk |
| `nfe_infnfe_*` stale via XML-RPC → SEFAZ 225 | Playwright UI obrigatório em F5e (já documentado e existe em `playwright_nfe_transmissao.py`) |

### Desvios do plano aplicados em F4 (necessários, não opcionais)

| Desvio | Onde | Motivo |
|--------|------|--------|
| Fixture `app_ctx` → `db` | tests F4 | `app_ctx` não existe em `tests/conftest.py`; `db` fornece `app_context+begin_nested+rollback` |
| `f5b/f5c/f5d/f5e` recebem `List[Ajuste]` (plano: `List[int]`) | service F4 | Plano fazia `AjusteEstoqueInventario.query.filter_by(picking_id_odoo=pid)` — `db.session.commit()` no service vaza dados do savepoint do test para o DB persistente; colisões por `picking_id_odoo` em re-runs |
| F5a refactor: Odoo I/O paralelo + DB write serial no main thread (plano: thread filha commita) | service F4 | `ThreadPoolExecutor` cria threads sem Flask `app_context`; `db.session.commit()` em thread filha falha (`Working outside of application context`); pool de conexão diferente do savepoint |
| `transmitir_nfe_via_playwright(invoice_id, odoo, logger)` retorna `dict` (plano: `transmitir_nfe_playwright(invoice_id)` retorna string) | service F4 / Task 4.5 | Plano alertou: *"investigar antes de implementar 4.5"* — função real tem 3 args e retorna `dict` |
| `PICKING_TYPE_POR_DIRECAO` módulo-level dict (plano: hardcoded em método) | service F4 | Facilita futuro refactor G003 (mover para `constants/picking_types.py`) |

### Bugs encontrados em code-review pós-F4 e corrigidos (3 reviewers paralelos)

| Bug | Severity | Confidence | Status | Onde |
|-----|----------|------------|--------|------|
| **BUG-1**: `location_destino=5` hardcoded — correto apenas para `'perda'`, errado para `TRANSFERIR_*`, `INDUSTRIALIZACAO_*`, `DEV_*` (picking destino errado no Odoo) | HIGH | 95 | ✅ FIX commit `b385dabb` — helper `resolver_location_destino(tipo_op, destino)` + 7 tests novos | service F4 (originou do plano linha 2451) |
| **BUG-2**: `f5e_transmitir_sefaz` sem idempotency guard — re-execução abre Playwright em NF-e já transmitida | HIGH | 95+88 | ✅ FIX commit `5ee53f50` — skip se `fase_pipeline=F5e_SEFAZ_OK` ou `status=EXECUTADO` | service F4 |
| **BUG-3**: Erros de config (`playwright_indisponivel`, env vars ausentes) tratados como falha por-NF — 100 ajustes em batch sem alarme | HIGH | 82 | ✅ FIX commit `5ee53f50` — abort batch via `RuntimeError` quando `tentativas=0 + erro in HARD_FAIL_CONFIG_ERRORS` | service F4 |
| **MED C-2**: `cstat/xmotivo` do `ultimo_estado` (rejeição SEFAZ) não persistido em `erro_msg` | MED | 75 | ✅ FIX commit `5ee53f50` — `erro_msg` agora inclui `cstat=NNN, xmotivo='...'` | service F4 |
| **MED C-1**: `situacao_nf=excecao_autorizado` descartado (relevante audit fiscal) | MED | 76 | ✅ FIX commit `5ee53f50` — registrado em `erro_msg` mesmo em sucesso quando situacao != autorizado | service F4 |
| **MED B-2**: skip silencioso de ajustes sem `picking_id_odoo` em F5b/F5c/F5d (sinal de F5a falho) | MED | 81 | ✅ FIX commit `5ee53f50` — `logger.warning` nos 3 métodos | service F4 |

### Bugs MEDIUM não corrigidos (acceptable risks)

| Bug | Severity | Mitigação |
|-----|----------|-----------|
| **A-MED-1**: `expire_on_commit=True` faz objetos expirarem após commits — refresh implícito em F5b/F5c | MED | Funciona via SELECT implícito; sem regressão observada. Refactor opcional: replicar padrão F5a (pre-index + `db.session.get`) |
| **A-MED-2**: Semaphore compartilhado pode ficar com count reduzido se thread crash sem `__exit__` | MED | `__exit__` no `with self.semaphore:` é garantido em fim normal; crash de thread é raro e affecting apenas instância vigente — re-instanciar service resolve |
| **A-HIGH-3**: Se Odoo cria picking mas `db.session.commit()` falha, próximo F5a re-cria duplicate | HIGH (low likelihood) | Guard `if ajuste.picking_id_odoo: skip` JÁ existe — só protege se commit foi bem-sucedido em pass anterior. Fence token (idempotency_key no Odoo) é melhoria futura |
| **B-MED-1**: Plano F4/F7 ainda mostra `List[int]` no texto | MED | Documentado aqui no SOT como desvio. Plano text não é fonte de verdade — SOT + código são |
| **C-MED-3**: Worst-case duração serial F5e (~45h/100 NFs) não no docstring | LOW | Docstring atualizada em commit `5ee53f50` menciona "Worst case: 100 ajustes × 15 × 120s = ~45h" |

---

## 8. ARTEFATOS PERSISTIDOS

### Em `main` (origin sincronizado)

```
app/odoo/
  constants/
    __init__.py
    locations.py
    operacoes_fiscais.py    # MATRIZ_INTERCOMPANY + helpers
  models/
    __init__.py
    operacao_odoo_auditoria.py
    ajuste_estoque_inventario.py
  services/
    stock_lot_service.py    # F2 (15 + 4 criar_se_nao_existe = 19 tests) — D006
    stock_internal_transfer_service.py # D006 (14 tests) — transferir entre lotes via inventory adjustment
    stock_picking_service.py # F3 (13 tests)
    inventario_pipeline_service.py # F4 (25 tests) — f5a..f5e orquestrador batch (recebe List[Ajuste], DESVIO do plano: plano usava List[int] + lookup por picking_id_odoo, refatorado por bug de pool de conexao em tests). Bugs HIGH post-review (BUG-1 location_destino, BUG-2 idempotency F5e, BUG-3 abort config) e MEDIUMs corrigidos (cstat/xmotivo persistido, situacao_nf audit, WARNING em skip silencioso).
    indisponibilizacao_estoque_service.py # F5 (12 tests) — canary_lote/canary_local com try/finally (SEMPRE reverte) + indisponibilizar_lote/local com canary_passou guard + reverter_lote/local. OPORTUNIDADE refactor: usar StockLotService.inativar/reativar (F2) em vez de odoo.write direto.

scripts/
  migrations/
    2026_05_18_operacao_odoo_auditoria.{py,sql}
    2026_05_18_ajuste_estoque_inventario.{py,sql}
    2026_05_19_add_fase_pipeline.{py,sql}
    2026_05_17_add_lote_destino_ajuste.{py,sql}  # D004/D005 lote_origem + lote_destino
  inventario_2026_05/
    README.md
    00_audit_odoo_realidade.py
    00b_investigar_gotchas.py
    00c_investigar_g003.py
    00d_investigar_variacoes.py
    00e_investigar_pickings.py
    01_extrair_estoque_odoo.py        # F7.1 — stock.quant → Excel + JSON
    02_carregar_inventario_xlsx.py    # F7.2 — planilha → JSON validado
    03_confrontar_inv_vs_odoo.py      # F7.3 — diff com P6/P9
    04_propor_ajustes.py              # F7.4 — propor/listar/aprovar com hash da onda
    hooks/                  # placeholder vazio (F6 CANCELADA — ver §6.1)

tests/odoo/                 # 97 tests passing
  __init__.py
  constants/__init__.py
  constants/test_operacoes_fiscais.py  # 17 tests
  models/__init__.py
  models/test_operacao_odoo_auditoria.py  # 4 tests
  models/test_ajuste_estoque_inventario.py  # 4 tests
  services/__init__.py
  services/test_stock_lot_service.py  # 15 tests
  services/test_stock_picking_service.py  # 13 tests (F3)
  services/test_inventario_pipeline_service.py  # 29 tests (F4 + post-review fixes + auditoria)
  services/test_indisponibilizacao_estoque_service.py  # 15 tests (F5 + auditoria)

docs/
  inventario-2026-05/
    SOT.md                  # ESTE ARQUIVO
    README.md
    00-decisoes/
      D000-audit-odoo-realidade.md
      D001-escolhas-pos-audit.md
      D002-matriz-intercompany-final.md
      D003-arquitetura-pipeline-batches.md
      D004-rename-lote-diferenca-liquida.md       # 2026-05-17
      D005-lote-migracao-consolidador-fantasmas.md  # 2026-05-17
    01-premissas/
      P001-P010-placeholder.md  # placeholders — preencher se virarem ativos
      P011-dev-industrializacao-fb-lf-sem-precedente.md
    02-gotchas/
      G001-nfs-referencia-sao-entradas-nao-saidas.md
      INV-002-picking-type-LF-divergente.md
      G003-cfop-real-divergente-do-prompt.md
      G004-padrao-real-eh-picking-robo-CIEL-IT.md
    03-canary/              # vazio (F4 pendente)
    04-movimentacoes/       # vazio (F5 pendente)
    05-rollback/            # vazio
    06-aprovacoes/          # vazio
    07-relatorios/          # vazio (F1 scripts pendentes)
  superpowers/
    specs/2026-05-17-ajuste-inventario-nacom-lf-design.md
    plans/2026-05-17-ajuste-inventario-nacom-lf.md

build.sh    # items 19/20/21 adicionados

.claude/references/odoo/
  IDS_FIXOS.md              # CORRIGIDO (LF picking_type=19, não 16)
```

### Pendente de criar

```
scripts/inventario_2026_05/
  # 01-04 ja em main (preparacao — F7.1-7.4)
  05_canary_estoque_staging.py
  06_canary_nfs_referencia.py
  07_executar_onda1_lf_fb.py          # incluir validacao inline: custo >20%, teto onda
  08_executar_onda2_cd_fb.py
  09_executar_onda3_indisponibilizacao.py
  10_reconciliar_pos_ajuste.py
  # F6 hooks/ CANCELADA — ver §6.1

.claude/references/odoo/
  OPERACOES_FISCAIS_NACOM_LF.md       # F8 playbook
  OPERACOES_LOTE_E_INDISPONIBILIZACAO.md  # F8 playbook
```

---

## 9. COMO ATUALIZAR ESTE SOT

Sempre que uma fase mudar de status, atualizar §3 (Estado por fase). Sempre que descobrir novo GOTCHA, atualizar §7 (Riscos). Sempre que criar novo artefato, atualizar §8 (Artefatos).

**Este SOT é a única página que precisa estar sempre atual.** Spec e plano podem ficar desatualizados se decisões mudarem — quando isso acontecer, registrar em `00-decisoes/D00X.md` nova e referenciar aqui.

## Atualizado

Ver datas no corpo do documento (registro historico).

## Estado atual

Ver secoes do corpo acima (estado registrado na epoca).

## Pendencias

Ver itens listados no corpo acima.
