# CIRURGIA AVULSO_2026_05_27_FRASCO — Root cause de 5 falhas no pipeline INDUSTRIALIZACAO_FB_LF

**Data**: 2026-05-27
**Operação**: transferir 37688un FRASCO 210030009 de FB/Indisponivel/MIGRAÇÃO → LF/Estoque/AJ-27-05
**Status final**: ✅ DESTRAVADA — invoice ENTIN/2026/05/0056 posted + LF/Estoque/AJ-27-05=37688un
**Sessão**: v24+/v24.1+ (commits ab37e3b8 + 42c097d5)

---

## Linha do tempo

1. **Operação inicial via pipeline** (subagente background com `--usar-fluxo-l3-v19`):
   - SAÍDA SEFAZ autorizada (NF 718364 chave `...164482`) ✅
   - ETAPA F crashou em 47ms — bug `_team_g039_status` não filtrado no splat (regression v23+ G039)
2. **Hotfix v24.1+** aplicado (commit 42c097d5): filtra `_*` meta-keys antes do splat
3. **Re-tentativa pós-hotfix**: avançou 6/8 passos do FLUXO L3 1.2.2 mas PO 42515 ficou sem picking (motor Odoo não disparou stock_rule)
4. **Cirurgia manual 9 passos** (subagente background com autorização Rafael):
   - Reverteu lote + devolveu picking + voltou DFe a draft + tipo='compra' + reprocessou DFe
   - Múltiplas tentativas (POs 42526/42540/42541 falharam) — chegou em PO 42543 perfeita
5. **PO 42543 confirmada via UI Rafael** (alterado tipo manual de 'compra' para 'serv-industrializacao')
6. **Resultado final**: invoice ENTIN/2026/05/0056 posted + 37688un em LF/Estoque/AJ-27-05

---

## 5 falhas distintas identificadas (análise root cause subagente)

### FALHA #1 — Pipeline marcou EXECUTADO sem rodar ETAPA F (P0)

**Descrição**: Pipeline marcou ajuste 177465 como `status='EXECUTADO'` em `fase_pipeline='F5e_SEFAZ_OK'` mas ETAPAS E+F (criar entrada LF) não rodaram automaticamente.

**Causa**: `executar_pipeline_bulk` modo legacy v17 NÃO chama `executar_fluxo_l3_1_2_x` para `INDUSTRIALIZACAO_FB_LF` (FB→LF). Depende da flag `--usar-fluxo-l3-v19` opt-in que não foi acionada na primeira execução.

**Fix proposto**: Tornar L3 v19+ default (remover opt-in) para todas as ações inter-company com destino LF/FB/CD. Deprecar v17 STRICT (LF→FB only).

**Arquivo**: `app/odoo/estoque/orchestrators/faturamento_pipeline.py executar_pipeline_bulk`

### FALHA #2 — PO criada com tipo='rem-industrializacao' (P1)

**Descrição**: Quando job/operador reprocessou DFe 43564, gerou PO 42525 com `tipo='rem-industrializacao'` (herança do XML da NF saída FB).

**Causa**: Skill 7 `escriturar_dfe` não força o tipo correto para o destinatário LF. Default vem do XML.

**Fix proposto**: Em `executar_fluxo_l3_1_2_x` passo 3 `escriturar_dfe(l10n_br_tipo_pedido='serv-industrializacao')` já está mapeado em `L10N_BR_TIPO_PEDIDO_POR_ACAO[INDUSTRIALIZACAO_FB_LF]`. **CONFIRMAR** que passo 3 efetivamente sobrescreve ANTES do passo 4 `gerar_po_from_dfe`.

**Arquivo**: `app/odoo/estoque/scripts/escrituracao.py escriturar_dfe` + orchestrator passo 3

### FALHA #3 — Lote default MIGRAÇÃO silencioso (P0 — BUG ARQUITETURAL MAIS CRÍTICO)

**Descrição**: Picking 321817 foi preenchido com `lote=MIGRAÇÃO` em vez do `AJ-27-05` do XML SEFAZ. Saldo criado em LF/Estoque/MIGRAÇÃO incorretamente.

**Causa arquitetural**: `_executar_etapa_f_via_fluxo_l3` chama `executar_fluxo_l3_1_2_x` SEM passar `lotes_data`. Resultado: o átomo Skill 5 `preencher_lotes_picking` usa `lote_default='MIGRAÇÃO'` para TODOS os MLs.

**Evidência código**:
- `faturamento_pipeline.py:3352-3356` — kwargs `**public_constants` não inclui `lotes_data`
- `escrituracao.py:2800` — `lote_default='MIGRAÇÃO'` como default

**Impacto**: CADA inter-company gera saldo em LOTE ERRADO silenciosamente. Saldo final fica em MIGRAÇÃO em vez do lote do XML SEFAZ.

**Fix P0-A**: `_executar_etapa_f_via_fluxo_l3` deve construir `lotes_data=[{product_id, lote_destino, quantity}]` a partir dos `AjusteEstoqueInventario` agrupados por `invoice_id` e passar ao `executar_fluxo_l3_1_2_x`.

**Fix P0-B**: Em `executar_fluxo_l3_1_2_x`, trocar `lote_default='MIGRAÇÃO'` por `None` + raise em `preencher_lotes_picking` se sobrar ML sem lote (falha rápida vs saldo errado silencioso).

**Arquivos**:
- `app/odoo/estoque/orchestrators/faturamento_pipeline.py _executar_etapa_f_via_fluxo_l3`
- `app/odoo/estoque/scripts/escrituracao.py executar_fluxo_l3_1_2_x`
- `app/odoo/estoque/scripts/picking.py preencher_lotes_picking`

### FALHA #4 — picking_type=64 consumindo Em Trânsito Industrialização (P1)

**Descrição**: `tipo='rem-industrializacao'` → `picking_type=64` → `default_location_src_id=26489` (Em Trânsito Industrialização). Picking 321817 foi validado com lote MIGRAÇÃO que NÃO existe em Em Trânsito, então saldo veio de Parceiros/Fornecedores (location_id=4) virtual.

**Causa**: Cascateia da FALHA #2 — tipo errado gera picking_type errado. Combinado com lote errado (FALHA #3), criou saldo inválido.

**Fix**: Combinado com FALHA #2 + #3. Verificar que `preencher_po` (passo 5 do `executar_fluxo_l3`) escreve `picking_type_id=19` ANTES de `confirmar_po`. Atualmente linha 2982 (preencher_po) antes da linha 2999 (confirmar_po) — order OK.

**Arquivo**: `escrituracao.py preencher_po` (validar ordem já correta)

### FALHA #5 — qty_received=0 na OL (NÃO É BUG)

**Descrição**: OL 128678 da PO 42525 tem `qty_received=0` apesar do picking 321817 ter sido done.

**Causa**: NÃO é bug — é consequência da MINHA cirurgia (passo 2 devolveu picking 321817 via picking 321833). Net saldo = 0 = qty_received correto.

---

## Hipóteses descartadas (importante para não desperdiçar esforço futuro)

- ❌ **G039 purchase team gatekeeper**: NÃO foi causa do processo original. PO 42525 já nasceu com `team_id=143` Rafael correto.
- ❌ **G-PERM-1 ir.rule dfe.line**: Só surgiu DEPOIS, na cirurgia tentando reprocessar DFe com `purchase_fiscal_id` stale.

---

## 4 novos gotchas descobertos pela cirurgia

### G-DFE-PURCHASE-FISCAL-ID-STALE
`dfe.purchase_fiscal_id` apontando para PO cancelada bloqueia `action_processar_arquivo_manual` via ir.rule indireta. Limpar (`write {'purchase_fiscal_id': False}`) ANTES de reprocessar DFe.

### G-DFE-LINE-COMPANY-EMITENTE
`dfe.line.company_id` é criada com company do EMITENTE (FB) por default, mesmo que DFe seja `company_id=destinatário` (LF). Sintoma: PO criada vazia ou com line.company errada. Solução: `write` em todas `dfe.line.company_id=company_destinatário` ANTES de `action_gerar_po_dfe`. Codificado em Skill 7 v23.5+ B-V23-1 fix.

### G-INDUSTR-LF-PADRAO
PO LF entrada industrialização SEMPRE usa `l10n_br_tipo_pedido='serv-industrializacao'` (label confuso "Serviço de Industrialização") — mesmo que selection do Odoo sugira `rem-industrializacao` ('Remessa p/ Industrialização'). Tipo `'serv-industrializacao'` resolve invoice via journal **1047 ENTIN** existente; outros tipos não têm journal LF cadastrado. Padrão confirmado em 89+ POs LF históricas.

### G-PO-NATIVA-SEM-PICKING
Quando `purchase.order.button_confirm` é chamado MAS produto não tem `l10n_br_tipo_produto` cadastrado (ou outros campos fiscais ausentes), motor Odoo confirma PO mas NÃO dispara `_create_picking` (stock.rule não roda). Resultado: PO state=purchase, picking_ids=[], move_ids=[]. Write retroativo dos campos NÃO regenera moves. **Sub-skill C5 v24+ check `tipo_produto_ausente` JÁ detecta isso** (commit ab37e3b8) — operação foi rodada com `--pular-pre-flight`.

---

## Ordem de implementação dos fixes (priorização v25+)

| # | Prioridade | Fix | Arquivo | Impacto |
|---|---|---|---|---|
| P0-A | CRÍTICO | Passar `lotes_data` resolvido ao `executar_fluxo_l3_1_2_x` | `faturamento_pipeline.py:_executar_etapa_f_via_fluxo_l3` linhas 3322-3356 | Evita lote errado em CADA inter-company |
| P0-B | CRÍTICO | Trocar `lote_default='MIGRAÇÃO'` por `None` + raise | `escrituracao.py:executar_fluxo_l3_1_2_x` linha 2800 + `picking.py:preencher_lotes_picking` | Falha rápida vs saldo errado silencioso |
| P0-C | CRÍTICO | L3 v19+ DEFAULT para todas inter-company | `pipeline_bulk` | Pipeline automático completo |
| P1-D | MÉDIO | Confirmar `escriturar_dfe` força `tipo='serv-industrializacao'` antes de `gerar_po_from_dfe` | `escrituracao.py:escriturar_dfe` + linha 2940 | PO nasce com tipo correto |
| P1-E | MÉDIO | Validar ordem `preencher_po` → `confirmar_po` (parece OK) | `executar_fluxo_l3_1_2_x` linhas 2982-2999 | picking_type correto |
| P2 | MÉDIO | Guard `EXECUTADO_PARCIAL` em pipeline_bulk quando ETAPA F skipped | `pipeline_bulk` | Evita falso-positivo `status=EXECUTADO` |
| P3-G | BAIXO | Codificar G-PO-DFE-LOCK (limpar `purchase_fiscal_id`) | `escrituracao.py` novo método | Antimedida para cirurgias futuras |
| P3-H | BAIXO | Codificar G-DFE-LINE-COMPANY (write `dfe.line.company_id`) | `escrituracao.py:gerar_po_from_dfe` pre-hook | Antimedida para PO vazia (já parcialmente codificado v23.5+ B-V23-1) |

---

## Implementação v25+ (commit pendente — 2026-05-27)

Após validação Rafael, aplicados 4 fixes que mapeiam aos 5 problemas reais
identificados. Hipóteses descartadas (G-PO-NATIVA-SEM-PICKING / G-DFE-LOCK)
NÃO foram implementadas — Rafael confirmou que não foram necessárias.

| Fix | Mapeamento | O que mudou |
|---|---|---|
| **F1** | LOTE obrigatório copiar da saída de acordo com a qtd | `_executar_etapa_f_via_fluxo_l3` agora resolve `prod_cache` em batch + monta `lotes_data` por invoice agregando `(product_id, lote_destino)` com `abs(qtd_ajuste)`. Espelha legacy v17.5 linhas 3998-4018. Lote vazio/'MIGRAÇÃO' → `INV-{cod}-{YYYYMMDD}`. |
| **F1b** | (consequência de F1) | `executar_fluxo_l3_1_2_x` default `lote_default='MIGRAÇÃO'` → `None`. Caller F1 passa `lotes_data` resolvido + `lote_default='INV-FALLBACK-{HOJE}'` (apenas backup). |
| **F2a** | empresa obrigatório setar (caminho A) | Novo átomo público `alinhar_dfe_lines_company(dfe_id, company_destino)` em `escrituracao.py`. Generaliza fix B-V23-1 que estava inline em `criar_dfe_a_partir_do_invoice_saida` (caminho B). `executar_fluxo_l3_1_2_x` invoca após `buscar_dfe` retornar `encontrado=True` (caminho A). Passo `1_5_alinhar_dfe_lines_company_a` registrado em `passos`. |
| **F2b** | empresa obrigatório setar (picking nativo) | `executar_fluxo_l3_1_2_x` força `stock.picking.company_id` + `stock.move.company_id` = `company_destino` após localizar picking ativo no passo 7 (espelha G023 do átomo legacy `criar_picking_entrada_destino_manual`). Não-fatal: erro vira log warning. Passo `6_5_g023_force_company` registrado. |
| **F3a** | tipo do pedido: compra no DFe; serv-industrializacao no PO | `L10N_BR_TIPO_PEDIDO_POR_ACAO` refatorado de `Dict[str, str]` para `Dict[str, Dict[str, str]]` com keys `'dfe'` e `'po'`. `INDUSTRIALIZACAO_FB_LF → {'dfe': 'compra', 'po': 'serv-industrializacao'}`. |
| **F3b** | tipo='compra' no DFe (passo 3) | `executar_fluxo_l3_1_2_x` passo 3 chama `escriturar_dfe(l10n_br_tipo_pedido=l10n_br_tipo_pedido_dfe)` (parâmetro renomeado de `l10n_br_tipo_pedido` para `l10n_br_tipo_pedido_dfe`). |
| **F3c** | preencher_po aceita `l10n_br_tipo_pedido` | Novo parâmetro opcional `l10n_br_tipo_pedido: Optional[str] = None` em `EscrituracaoLfService.preencher_po`. Quando fornecido, escreve no write da PO (entre os valores). Whitelist espelha `escriturar_dfe`. |
| **F3d** | tipo='serv-industrializacao' no PO (passo 5) | `executar_fluxo_l3_1_2_x` passo 5 chama `preencher_po(l10n_br_tipo_pedido=l10n_br_tipo_pedido_po)`. Fatura herda da PO no passo 9 sem intervenção adicional. |
| **F4** | Purchase team id=143 fixo | `CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO[5]['team_id']` 41 → **143** (STATIC FIXO). `_resolver_constants_fluxo_l3` desliga override G039 dinâmico para `company_destino=5` (LF). Demais destinos (FB=1, CD=4) mantêm G039 quando forem mapeados. |

**Pytest baseline**: 655 → 662 verdes (+7 net = +8 testes F2a/F3c novos − 1 teste removido por reescrita F4). Suíte total tests/odoo em 17s.

**Arquivos tocados (4)**:
- `app/odoo/estoque/orchestrators/faturamento_pipeline.py` (5 hunks — constants F3a+F4, _resolver_constants F4, executar_fluxo_l3_1_2_x assinatura+passos, _executar_etapa_f_via_fluxo_l3 lotes_data F1)
- `app/odoo/estoque/scripts/escrituracao.py` (2 hunks — novo átomo `alinhar_dfe_lines_company` F2a, `preencher_po` aceita `l10n_br_tipo_pedido` F3c)
- `tests/odoo/services/test_escrituracao_lf_service_v19.py` (+8 testes novos)
- `tests/odoo/services/test_faturamento_pipeline_fluxo_l3.py` (4 callsites adaptados para `_dfe`+`_po`)
- `tests/odoo/services/test_faturamento_pipeline_orchestrator.py` (5 testes ETAPA F + 2 testes G039 reescritos para refletir F4)

---

## Pattern cirúrgico completo (referência para futuras cirurgias)

1. Reverter transferência de lote (Skill 2 reverso) se houve transfer pós-criação errada
2. Devolver picking errado (Skill 5 `devolver`)
3. Cancelar PO antiga (`button_cancel`) — pode falhar se já tem recebimentos done; tudo bem, `dfe.purchase_id` ainda vira False
4. Voltar DFe a draft (`action_set_to_draft`)
5. Limpar `dfe.purchase_fiscal_id=False` se aponta para PO cancelada (G-DFE-PURCHASE-FISCAL-ID-STALE)
6. Write `dfe.l10n_br_tipo_pedido` correto + reprocessar XML (`action_processar_arquivo_manual`)
7. Write `dfe.line.company_id=destinatário` em todas lines (G-DFE-LINE-COMPANY-EMITENTE)
8. `action_gerar_po_dfe` com `context={'allowed_company_ids': [destinatário], 'force_company': destinatário}` para evitar PO em FB
9. Verificar PO criada na company correta + write tipo correto se necessário (G-INDUSTR-LF-PADRAO)
10. Se picking não gerou: criar `stock.picking` + `stock.move` manuais (G-PO-NATIVA-SEM-PICKING)
11. Preencher picking com lote do XML SEFAZ (NÃO 'MIGRAÇÃO' default — extrair `<rastro><nLote>` do `account.move.l10n_br_xml_aut_nfe`)
12. Validar picking + criar invoice via Skill 7 `criar_invoice_from_po`

---

## Permissão G-PERM-1 (workaround documentado)

`dfe.line` tem `ir.rule` record-level que bloqueia Rafael uid=42 ler. Workaround documentado: rodar com Edilane uid=78 ou outro user com acesso fiscal LF. Ver `[[g_perm_1_ir_rule_dfe_line]]`.

---

## Estado final PROD (preservado para futuro reference)

| Recurso | Estado | Observação |
|---|---|---|
| Invoice ENTIN/2026/05/0056 (719071) | posted | journal 1047 ENTIN, R$ 7.796,58 |
| NF SAÍDA 718364 | SEFAZ autorizada | chave `35260561724241000178550010000945741007183640` |
| PO 42543 (C2602695) | purchase | LF, tipo=serv-industrializacao, fp=131, team=143 Rafael |
| Picking 321834 (LF/IN/01780) | done | lote AJ-27-05 correto |
| Quant 265199 LF/Estoque/AJ-27-05 | 37688 un | ✅ saldo correto |
| Quant 265091 Em Trânsito Industrialização AJ-27-05 | 37688 órfão | padrão observado em outras NFs paradigma |
| PO 42525 (antiga) | purchase | preservada, pickings done+devolução, saldo líquido zero |
| POs 42526/42540/42541 | cancelled/unlinked | tentativas falhas durante cirurgia |
