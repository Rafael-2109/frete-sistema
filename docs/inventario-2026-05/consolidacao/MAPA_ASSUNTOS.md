# MAPA GERAL — Operação de inventário 2026-05

> **NOTA (Onda 2 PAD-A):** o termo "gold-script" foi aposentado — a constituição vigente do orquestrador Odoo é `app/odoo/estoque/CLAUDE.md` (vocabulário: services/primitivas C1/C2 · orchestrators C3). Este doc é mineração transitória válida; a consolidação real dos scripts é a Onda 3.

**Criado:** 2026-05-20 (refeito com profundidade após pesquisa em 4 frentes: decisões, gotchas, estado, primitivas).
**Escopo:** `scripts/inventario_2026_05/` (**~100 scripts — volátil, operação viva**) + `docs/inventario-2026-05/` (decisões D*, premissas P*, gotchas G*, estado) + primitivas em `app/odoo/services/`.

> **Este é um ÍNDICE NAVEGÁVEL, não uma cópia.** Aponta para as fontes (`D###`, `G###`, `arquivo:linha`)
> em vez de repetir o conteúdo delas. Objetivo: entender o todo e guiar a consolidação em gold-scripts.
> Fontes: decisões em `00-decisoes/`, gotchas em `02-gotchas/`, premissas em `01-premissas/`,
> estado em `SOT.md` + `PENDENCIAS.md`. Convenção status: ✅ pronto · 🟡 existe/falta manual · 🔴 gap · 📖 read-only.
> **Como migrar** (estrutura-alvo `app/odoo/estoque/` + gatilhos por situação): [`PLANO_MIGRACAO.md`](PLANO_MIGRACAO.md).
> **Mineração** (cada um dos ~100 scripts → gold destino + o que preservar): [`MAPA_SCRIPTS.md`](MAPA_SCRIPTS.md).

---

## 1. As 3 gerações de mecanismo (por que existem ~90 scripts)

A operação evoluiu o mecanismo 3 vezes, cada uma reduzindo emissão de NF na SEFAZ. Isso explica a
estratificação dos scripts — muitos são de gerações anteriores, hoje superadas.

| Geração | Mecanismo | Decisões | Emite NF? | Onde vive |
|---------|-----------|----------|-----------|-----------|
| **G1** NF inter-company por diferença líquida | picking saída → robô CIEL IT → SEFAZ → entrada destino | D004, D005 | **Sim** (SEFAZ) | Ondas 1-2; `09`, `09c`, `teste_210030325`, `fat_lf_04/05`, `InventarioPipelineService` |
| **G2** Pré-etapa interna consolidando em MIGRAÇÃO | transferência interna + residual, sem NF | D006, **D007** | Não | Ondas 5-6; `03b/04b/09b`, `PreEtapaEstoqueService` |
| **G3** Inventory adjustment direto por planilha via locais "Indisponível" | `stock.quant` + `action_apply_inventory`, sem NF | D010, **D011**, D012, D013 | Não | **Atual**; `11-17`, `ajuste_*`, `mover_migracao`, `StockQuantAdjustmentService` |

> Cadeias de supersessão (FONTE: `sa1`): D002 substitui D001 (matriz IC); **D014 complementa/corrige D002**
> (entradas 1xxx + regra CFOP por tipo de produto + corrige vasilhame fp 64); D006 substitui renomeio de D004;
> D007 substitui abordagem fiscal de D004 + INDISPONIBILIZAR de D005 (p/ CD); D011 substitui virtual id=28
> e relocaliza MIGRAÇÃO; D012 é override de D011 só p/ LF. **D009 não existe** (gap na numeração).

---

## 2. Camadas de abstração (o esqueleto — corrige a mistura anterior)

| Camada | O que é | Membros |
|--------|---------|---------|
| **C0 — Constantes** | dados fixos (IDs, CFOP, lotes) | `app/odoo/constants/` (locations, operacoes_fiscais) |
| **C1 — Primitivas atômicas** | 1 operação Odoo atômica | `StockLotService`, `StockQuantAdjustmentService` |
| **C2 — Serviços compostos** | compõem primitivas | `StockInternalTransferService`, `StockPickingService`, `IndisponibilizacaoEstoqueService`, `PreEtapaEstoqueService` (planner) |
| **C3 — Orquestradores macro** | fluxo multi-etapa (NF/SEFAZ/batch) | `InventarioPipelineService`, `RecebimentoLfOdooService`; scripts `09`, `fat_lf_04/05`, `teste_210030325` |
| **R — Leitura/auditoria** | read-only | `monitor/*`, extração, diff/SOT |

> **Gold-script ≠ orquestrador.** C1/C2 são os gold-scripts (versáteis). C3 são "mains" do inventário —
> NÃO reutilizáveis como bloco; devem ser remontados a partir de C1/C2 via guia.

---

## 3. Tabela mestra — assunto × gold-script × camada × fontes

| Assunto (ação) | Gold-script | Camada | Status | Decisões | Gotchas | Scripts ad-hoc que consolida |
|----------------|-------------|--------|--------|----------|---------|------------------------------|
| Ajuste de inventário de 1 quant | `StockQuantAdjustmentService.ajustar_quant` | C1 | ✅ + manual + 22 testes | D010, D012 | G028, G029 | 11, 12, 13, 14_v2, criar_saldo |
| Resolver/criar/renomear lote | `StockLotService` | C1 | 🟡 falta manual | D005, P1(lotes) | G009, G014, G036, **G002** (`=`→`in`) | (dependência geral); padronizar_migracao |
| Transferência entre lotes (mesmo local) | `StockInternalTransferService` (+ orquestrador `transferir_lote.py` net-zero **JÁ existe** — promover, não recriar) | C2 | 🟡 falta manual | D006, D010 | **G028**, G021, G022, G027, +`lot_id` empresa errada | 10, 13_transf, 15, 15r, substituir_lote, **transferir_lote**, recuperar_aumentos_falhos |
| Escrituração DFe entrada (FLUXO A — direção inversa do faturamento) | `escriturar_dfe_lf.py` (NÃO reusa RecebimentoLf) | C3 | 🔴 novo (assunto descoberto) | D004 | quirk DFe status 04 | escriturar_dfe_lf |
| MIGRAÇÃO ↔ Indisponível | (composição de `ajustar_quant` / transfer) | C2 | 🟡 padrão, sem service dedicado | **D011**, D012, D013 | G036 | mover_migracao, ajuste_fb_cd_indisponivel, transferir_indisp |
| Pré-etapa CD/FB (planejar) | `PreEtapaEstoqueService.planejar` (planner puro, não escreve) | C2 | 🟡 falta manual | **D007** | — | 03b, 04b (executor = 09b) |
| Indisponibilizar lote/local (canary) | `IndisponibilizacaoEstoqueService` | C2 | 🟡 falta manual | D005 | — | 09 onda3 |
| Picking inter-company (criar/validar) | `StockPickingService` (acoplado robô CIEL IT) | C2 | 🟡 falta manual | D002, G003 | **G011**, G023, G019, G020 | etapa B de 09, fat_lf_05; 16_cancelar_pickings |
| Faturamento inter-company (NF→SEFAZ→entrada) | `InventarioPipelineService` + `RecebimentoLfOdooService` | C3 | 🟡 macro, falta manual | D004, D002 | **~20 gotchas** (ver §4) | 09, 09c, fat_lf_04/05, teste_210030325, entrada_fb_piloto |
| **Cancelar MO (mrp.production)** | — | C1/C2 | 🔴 **GAP** (só script) | — | G024 | 14_cancelar_mos, cancelar_mos |
| **Cancelar reserva (move.line/unreserve)** | — | C1/C2 | 🔴 **GAP** (`resetar_reserva` não cancela picking) | — | G024, G025 | cancelar_reservas_migracao, remover_reservas_saida |
| Leitura: estoque/quants | `monitor/_comum` + helpers | R | 🟡 disperso | — | — | 01, extrair_estoque_locais_emp, monitor/1 |
| Leitura: movimentações | helpers | R | 🟡 disperso | — | — | rastrear_movs, monitor/2 |
| Leitura: diff/SOT/confronto | lógica repetida (9 variações) | R | 🟡 consolidar | D010 | — | comparar_sot_*, confronto_4_fontes, diff_*, relatorio_final_sot |
| Investigação F0 (discovery) | — | R | 📦 arquivar | — | — | 00-00e, auditoria/investiga_* |

---

## 4. Gotchas por assunto (o ouro — fonte: `02-gotchas/`, 31 gotchas)

> G005/G031/G032/G033 **não existem** (gaps). G019/G020 ainda **ABERTOS**.

- **Faturamento inter-company — ~20 gotchas (DE LONGE o mais perigoso):**
  `G004` (arquitetura real = picking→robô→Playwright, NÃO `account.move` direto),
  `G011` (qty_done entre assign e validate — raiz de G012/G013), `G016` (SSL crash em loops longos),
  `G019`/`G020` (`validar()` engole erro e marca done falso — ABERTOS),
  quarteto pré-flight fiscal `G035`/`G017`/`G007`/`G018` (barcode-GTIN / NCM / price_unit / weight → SEFAZ cstat 225).
- **Transferência/lote:** `G028` (over-reservation pós-renomeio, ratio até 459x — núcleo de `consolidar_move_lines`), `G021`/`G022`/`G027`.
- **Conexão Odoo/XML-RPC:** `G002`/`G036` (operador `=` em `stock.lot.name`/relacionais retorna vazio → usar `in`), `G016`, `G030`.
- **Cancelamento:** `G024`/`G025` (órfãos de move_line + recompute manual de `reserved_quantity`).

---

## 5. C0 — Constantes (estado de centralização)

| Constante | Onde está | Ação |
|-----------|-----------|------|
| `COMPANY_LOCATIONS` (FB=8, CD=32, LF=42) | ✅ `constants/locations.py` | SC=22 **NÃO adicionado** (decisão 2026-05-20: SC fora de escopo, D011:95) |
| `CODIGO_PARA_COMPANY_ID` / `COMPANY_PARTNER_ID` (FB=1, CD=34, LF=35) | ✅ `constants/operacoes_fiscais.py` | SC **NÃO adicionado** (mesma decisão) |
| `MATRIZ_INTERCOMPANY` (**6 ops**: 4 ajuste + 2 referência) — CFOP **saída** + campo **`entrada`** (1901/1903/1949/1151/1152/1124/1902 + `resolver_entrada()`); validado no Odoo 2026-05-21, **[D014](../00-decisoes/D014-cfop-entradas-e-operacoes-referencia.md)** | ✅ `operacoes_fiscais.py` | regra CFOP por tipo de produto: 5901 insumo · **5902 insumo utilizado (NUNCA produto acabado) ≠ 5903 não-aplicado** · 5124+5902 = venda-industrializacao (fp 111, ref) · **5921 = vasilhame (fp 64, ref)** · 5949 = retrabalho/ajuste tipo 4 (inventário). **SARET tipo 4 c/ 5902 = erro** |
| `LOCAIS_INDISPONIVEL` (FB 31088, SC 31089, CD 31090, LF 31091) | ✅ **FEITO (Onda 1)** em `locations.py` + `get_local_indisponivel()` + testes | migrar consumidores (gradual, QUANDO-SUPERADO) |
| `LOTES_MIGRACAO_POR_COMPANY` (FB id=30482, CD id=30856) | ✅ **FEITO (Onda 1)** em `locations.py` | migrar consumidores |
| `PICKING_TYPE_POR_DIRECAO` / `LOCATION_DESTINO_POR_DIRECAO` | ✅ **FEITO** em `constants/picking_types.py` (G003 resolvido); pipeline importa + re-exporta (compat scripts) | — |
| INCOTERM_CIF=6, CARRIER_NACOM=996, PAYMENT_PROVIDER_SEM_PAGAMENTO=38 | ✅ **FEITO** em `constants/ids_diversos.py`; pipeline/stock_picking importam | `app/pedidos/integracao_odoo` tem INCOTERM_CIF próprio (outro módulo, fora de escopo) |
| Sub-locais Pré-Produção FB/LF (4066/4067/4068/27458/53/30710) | ✅ **FEITO** em `locations.LOCAIS_PRE_PRODUCAO` (default canônico) | scripts 15/17 podem importar (são parametrizáveis) |

**Bugs latentes:** (1) **SC (company_id=3)** ausente dos dicts → orquestradores "todas empresas" o ignoram em silêncio.
(2) **`MIGRAÇÃO` (acento, canônico) vs `MIGRACAO`** coexistem (D005/D010 com acento; D011/D012 sem; ambos por D013) — hardcoded sem acento em `teste_210030325_lf.py:98`, `fat_lf_02_carregar.py:162`.

**Auditoria de constantes (code-review 2026-05-21):** **SKILLS essencialmente LIMPAS** — matches em `.claude/skills/` são nomes de campo Odoo (strings em search_read/SQL), não IDs de domínio. Único caso menor: `gerando-baseline-conciliacao/scripts/gerar_baseline.py:46` (`COMPANY_ID_FB=1` local). `app/odoo/constants/` é fonte única correta; maioria dos scripts importa certo. **Duplicações — ✅ CORRIGIDO 2026-05-21:** `02_carregar` (CODIGO_PARA_COMPANY_ID) + 8 scripts de Indisponível (mover_migracao/auditar_migracao/ajuste_fb_cd/transferir_fluxo_c/executar_fluxo_b/relotar/pasta22/transferir_indisp) + skill `gerar_baseline` agora importam do central (derivando subset `{c for c in (1,4,5)}` p/ preservar escopo — SC fica fora). Pendente: `00d_investigar_variacoes.py` (script JÁ-MORTO de investigação F0 — não tocado, será arquivado).

---

## 6. Gaps e sobreposições (fonte: `sa4`)

- **GAPS** (operação sem gold-script dedicado): cancelar MO; cancelar reserva isolada (`action_unreserve` — `resetar_reserva` NÃO cancela picking); criar/postar invoice (sempre vem do robô CIEL IT); transmissão SEFAZ (vive em `app/recebimento/services/playwright_nfe_transmissao`, não em `app/odoo/services`).
- **SOBREPOSIÇÃO:** `buscar_quant` duplicado em `StockQuantAdjustmentService` e `StockInternalTransferService` (assinaturas quase iguais); padrão `_registrar_op` + "caller commits" repetido em Indisponibilizacao e Pipeline.

---

## 7. As 3 semânticas de planilha (armadilha de design — fonte: `sa1`)

Qualquer gold-script/orquestrador de planilha DEVE deixar a semântica EXPLÍCITA (nunca inferir):
1. **Sinal de `diff_qtd`** (D010): `diff>0 → lote→MIGRAÇÃO`; `diff<0 → MIGRAÇÃO→lote`.
2. **Delta com sinal** (D012): QTD>0 aumenta, QTD<0 reduz (net-zero por produto).
3. **Magnitude positiva + campos De/Para** (D013): De-Local/De-Lote → Para-Local/Para-Lote + qtd.

---

## 8. Estado atual (fonte: `SOT.md` + `PENDENCIAS.md` — VIVOS; checkpoints em `99-historia/` = obsoletos)

- **CD (4):** ~concluído (98,4% pré-etapa D007 + D013).
- **FB (1):** consolidado via D013 (95,4%, ~28,6M un → Indisponível); sem "Onda 6" formal.
- **LF (5):** 2 rastros — pipeline-NF (114 EXEC/1617 PROPOSTO, piloto SEFAZ-OK) + planilha D012 (Pasta16 25/25, Pasta17 138/147).
- **SC (3):** fora de escopo.
- **Pendências:** P1-P13 (P7 resolvido). **P1 (padronização lotes `MI ###-###/AA`) bloqueia fechamento.**
- **Restrição ativa:** NÃO rodar `03c_netting_cross_company.py` até LF/CD finalizados.

---

## 9. Roadmap de consolidação (bottom-up, revisado)

| Ordem | Passo | Entregável |
|-------|-------|-----------|
| 1 | C0 Constantes (LOCAIS_INDISPONIVEL + SC + lotes + picking_type) | desbloqueia tudo; corrige bugs latentes |
| 2 | C1 Primitivas — manuais (lot, quant✅) + de-duplicar `buscar_quant` | gold-scripts atômicos documentados |
| 3 | C2 Serviços compostos — manuais (transfer, picking, indispon, pre_etapa) | gold-scripts compostos documentados |
| 4 | Gaps — criar gold-scripts: cancelar MO, cancelar reserva | cobre operações órfãs |
| 5 | C3 + R — manuais do macro (pipeline/faturamento) e consolidar leitura/diff | |
| 6 | `GUIA_CRIAR_ORQUESTRADOR.md` | guia + `ajuste_inventario.py` como exemplo |

---

## 10. Manuais (1 por gold-script — `consolidacao/manuais/`)

- ✅ `stock_quant_adjustment_service.md` (template)
- ⬜ stock_lot, internal_transfer, picking, indisponibilizacao, pre_etapa, pipeline (macro)

> Evidência desta análise (rascunho, efêmero): `/tmp/subagent-findings/20260520-183839-adc073fc/phase1/sa1-4`.
