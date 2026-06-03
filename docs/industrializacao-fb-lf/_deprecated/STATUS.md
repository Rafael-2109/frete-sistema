# STATUS — Industrialização FB↔LF

> **Última atualização**: 2026-05-29
> **Sprint atual**: Sprint 1 — Piloto (NF saída AUTORIZADA SEFAZ; caminho B Skill 7 paused por gap company na PO LF)
> **Próxima task pendente**: ⏸️ **A08 (NOVO)** — resolver gap company no `gerar_po_from_dfe`. PO 42676 LF criada em company FB (errada) e cancelada. DFe 43689 LF aguardando re-geração de PO. 4 hipóteses A/B/C/D em `ABERTOS.md#A08` e `testes/T23-caminho-B-skill7-resultado.md`.
> **Estado geral**: 🟡 NF saída 725676 RPI/2026/00242 AUTORIZADA SEFAZ (chave válida 44 dig — **NÃO cancelar**, D22). Caminho B Skill 7 cobriu DFe + escrituração + gerar_po, mas PO saiu em company errada. Bloqueio aguardando A08.

---

## Atores

- **Rafael** (operador): executa no Odoo UI, opera testes do piloto, toma decisões.
- **Claude** (assistente técnico): scripts, validação, documentação.
- **Fiscal** (validador final): valida apenas no S2.

---

## Resumo de progresso

| Sprint | Tasks | Done | In Progress | Pending | Failed | Blocked | Skipped |
|---|---:|---:|---:|---:|---:|---:|---:|
| S0 — Setup técnico | T01–T15 + T10b | 11 | 0 | 0 | 0 | 0 | 4 |
| S1 — Piloto | T21–T28 | 0 | 0 | 8 | 0 | 0 | 0 |
| S2 — Envio Fiscal | T29–T32 | 0 | 0 | 4 | 0 | 0 | 0 |
| S3 — Pós-piloto | T33–T35 | 1 | 0 | 2 | 0 | 0 | 0 |
| **Total** | **31** | **12** | **0** | **14** | **0** | **0** | **4** |

**S0 detalhe**:
- ✅ done (11): T01-T06, T10, T10b, T11, T12, **T33 antecipada via D18**
- ⛔ skipped (4): T07 (A05 decidida empiricamente em T21) · T08 (D16 caminho A — observar em T21) · T09 (rota 166 LF não subcontrata) · **T13 (D19 fundida com T21)**
- ⬜ pending (0): nenhuma — S0 está 100% pronto, S1 começa pelo T21

**S1 detalhe**:
- ⬜ pending (8): **T21 (próxima ação — Rafael cria PO)**, T22, T23, T24, T25, T26, T27, T28

> Tasks T16-T20 (treinamentos / CIEL IT separada) foram **removidas** do roadmap. Cenário Rafael+Claude não exige.

---

## Próxima task

### ⏸️ A08 — Resolver gap company na criação de PO LF via `gerar_po_from_dfe`

**Status**: blocked_human
**Bloqueia**: continuidade do piloto (T24-T28)
**Contexto**: caminho B Skill 7 (D21) chamou `gerar_po_from_dfe(dfe_id=43689)`. Robô CIEL IT criou PO 42676 mas em **company_id=1 (FB)** quando deveria ser 5 (LF). Causa: contexto do user de execução (Rafael uid=42 com company principal=FB). PO cancelada (state=cancel) nesta sessão. DFe 43689 está pronto (`purchase_id=False`).

**4 hipóteses** (detalhe em `testes/T23-caminho-B-skill7-resultado.md`):
- **A** — Re-executar com user company=LF (Edilane uid=78)
- **B** — Forçar context `allowed_company_ids=[5]` no execute_kw
- **C** — Cancelar PO e usar `preencher_po` da Skill 7 com `company_id=5`+demais campos
- **D** — Write XML-RPC direto na próxima PO

Decisão pendente: Rafael escolhe entre A/B/C/D na próxima sessão.

### Artefatos preservados que sobreviveram (estado real)

| Item | ID | Estado | Notas |
|---|---:|---|---|
| **NF saída 725676 RPI/2026/00242** | 725676 | posted, **autorizado SEFAZ** | **NÃO CANCELAR** (D22). Chave: 35260561724241000178550010000945901007256765 |
| Picking saída FB FB/SAI/IND/01606 | 322049 | done | 16 componentes em "Em Trânsito Industrialização" |
| PO 42659 (C2619775) FB | 42659 | purchase | Origem do fluxo |
| SO 73424 (VLF2600001) LF | 73424 | sale | Auto-criada via inter-company |
| MO LF 20154 LF/MO/03507 | 20154 | confirmed | dst=31093 LF/PA Terceiros, 8 raws waiting |
| Picking RECEB/FB/IND/00018 (entrada PA futura FB) | 322039 | assigned | pt=52 ✓ |
| DFe LF 43689 | 43689 | l10n_br_status='06' | tipo_pedido='serv-industrializacao', `purchase_id=False`, pronto para nova `gerar_po_from_dfe` |
| Locations 31092, 31093 | — | active | LF/Materiais Terceiros + LF/PA Terceiros |
| Picking type 98 LF/SAI/IND/RET | 98 | active | T07 done |

### Etapas executadas nesta sessão (sequência completa)

```
1. ✅ T-AJUSTE-ESTOQUE: 3 ajustes positivos + 2 residuais (TAMPA, ANTIESPUMANTE, AROMA)
2. ✅ PO 42659 (C2619775) FB criada e confirmada
   - Descobertas: warehouse_id=False em FB+LF (T01 gap), incoterm, carrier, operacao linha, cfop linha
3. ✅ SO 73424 (VLF2600001) LF auto-criada via inter-company + confirmada
4. ✅ Picking LF/OUT/00020 cancelado (rota delivery normal, errada)
5. ✅ T07 — pt=98 LF/SAI/IND/RET criado
6. ✅ MO LF 20154 LF/MO/03507 criada (dst=31093 LF/PA Terceiros forçado)
7. ✅ Picking saída FB FB/SAI/IND/01606 criado manual + 16 stock.moves + validado
8. ✅ action_liberar_faturamento → robô CIEL IT criou invoice 725676
9. ✅ Playwright SEFAZ AUTORIZOU NF na 1ª tentativa (chave 44 dígitos válida)
10. ✅ Skill 7 caminho B passo 1: DFe 43689 criado em LF via XML autorizado + B-V23-1 fix aplicado
11. ✅ Skill 7 caminho B passo 2: DFe escriturado (tipo='serv-industrializacao')
12. ⚠️ Skill 7 caminho B passo 3: PO 42676 criada em company errada (FB) — CANCELADA
```

### T21b — Criar MO LF manualmente (caminho concorrente D20)

**Status**: ⬜ pending
**Executor**: Claude via XML-RPC (recomendado, mantém automação) OU Rafael/PCP LF via UI Odoo (pattern histórico)
**Spec**:
```
product_id     = 27834 ([4870112] MOLHO SHOYU - PET 12X1,01 L)
product_qty    = 10
bom_id         = 3695 (LF normal hierárquica, consumption=strict)
company_id     = 5 (LF)
origin         = "C2619775 / VLF2600001"  # rastreabilidade até PO/SO
```

Após MO done → 10 cx PA entram em LF/Estoque → picking LF/OUT/00020 reserva e fica `assigned`.

### Estado atual do piloto (T21 em andamento)

| Etapa | Status |
|---|---|
| PO 42659 (C2619775) FB confirmed | ✅ |
| Picking RECEB/FB/IND/00018 (pt=52 ✓) FB | ✅ assigned |
| SO 73424 (VLF2600001) LF confirmed | ✅ |
| Picking LF/OUT/00020 LF | ⏸️ confirmed esperando MO |
| **MO LF** | **⬜ a criar (T21b)** |
| Validar picking_out LF | ⬜ pós-MO |
| Validar move 10 cx LF/Estoque → Cliente | ⬜ pós-picking |

### Tasks subsequentes (sequência do piloto)

| Task | Quem | O que |
|---|---|---|
| T22 | Rafael (CIEL IT) | Emitir NF saída FB CFOP 5901 (17 componentes — D17) |
| T23 | Rafael (Odoo) + Claude | DFe entra na LF; validar picking pt=64 |
| T24 | Rafael (Odoo) | Apontar MO LF (consumo + 10 cx produção) |
| T25 | Rafael (CIEL IT) | Emitir NF retorno LF→FB (1×5124 + 17×5902 + N×5903) |
| T26 | Rafael (Odoo) + Claude | DFe entra na FB; validar picking pt=52 |
| T27 | Claude | Validar fechamento de PO/SO/MO/picking |
| T28 | Claude | Pacote final (`testes/SPRINT1-piloto-resultado.md`) |

---

## Histórico recente

| Data | Evento | Detalhe |
|---|---|---|
| 2026-05-28 | Plano aprovado | Decisões 1–15 confirmadas |
| 2026-05-28 | Estrutura criada em `docs/industrializacao-fb-lf/` | CONTEXTO + STATUS + ROADMAP_TASKS + DECISOES + ABERTOS + scripts |
| 2026-05-28 | Script T01 executado | Todos checks técnicos passam |
| 2026-05-28 | Cenário simplificado | Removidas tasks T16-T20 (treinamentos). Executor: Rafael+Claude. |
| 2026-05-28 | **T02 ✅ done** | Location LF/Materiais de Terceiros criada (id=31092). Destrava T04. Ver `testes/T02-resultado.md` |
| 2026-05-28 | **T03 ✅ done** | Location LF/PA de Terceiros criada (id=31093). Destrava T07. Ver `testes/T03-resultado.md` |
| 2026-05-28 | **T04 ✅ done** | `res.partner` LF (35) `property_stock_subcontractor` → 31092. Destrava T13. Ver `testes/T04-resultado.md` |
| 2026-05-28 | **T11 ❌ failed_dry_run** | Filtro do script busca `'Make to Order'`, mas rota se chama `'MTO'`. Sem alteração no Odoo. Ver `testes/T11-falha-2026-05-28.md` |
| 2026-05-28 | **T10 ✅ done** | BoM 3695 `consumption='warning'` → `'strict'`. Implementa D05. Ver `testes/T10-resultado.md` |
| 2026-05-28 | **T11 ✅ done** | Após fix do filtro (`'MTO'` ou `'Make to Order'`), rota MTO id=1 adicionada ao template 42282. Destrava T13. Ver `testes/T11-resultado.md` |
| 2026-05-28 | **T01 ✅ done** | `res.company.rule_type` setado `'sale_purchase'` em FB (1) e LF (5) via XML-RPC (equivalente flag UI "Auto Generate Sales Orders"). Rollback documentado. Destrava T05/T06/T08/T12/T13. Ver `testes/T01-resultado.md` |
| 2026-05-28 | **T05 ✅ done** | picking_type 74 (FB Subcontratação) reativado. Fix do wrapper (`execute_kw` para passar `context`). Ver `testes/T05-resultado.md` |
| 2026-05-28 | **T06 ✅ done** | picking_type 80 (LF Subcontratação) reativado. Idêntico T05. Ver `testes/T06-resultado.md` |
| 2026-05-28 | **T08 ⏸️ blocked_human** | Odoo bloqueia stock.rule cross-company. 5 caminhos propostos, recomendação caminho A. Ver `testes/T08-falha-2026-05-28.md` |
| 2026-05-28 | **T09 ⛔ skipped** | Rota 166 (LF Reposição p/ subcontratação) não tem caso de uso na Opção 2. Ver `testes/T09-resultado.md` |
| 2026-05-28 | **T12 ✅ done** | Journals SALE+PURCHASE de FB e LF mapeados para referência em T22/T25. Informativo. Ver `testes/T12-resultado.md` |
| 2026-05-28 | **D16 + T08 ⛔ skipped** | Decisão Rafael: caminho A. T08 fica skipped; T13 valida se módulo cria stock.rules automaticamente. Plano B/C/D/E reservado se T13 indicar necessidade. |
| 2026-05-28 | **D17 + A01 ⛔ resolved + T10b derivada** | Estrutura BoM real do piloto = hierárquica (3695 PA + 3646 BATELADA filha). BATELADA é subprocesso interno LF. Remessa FB→LF = 17 componentes (7 emb + 9 quim + 1 MP shoyu). Ver `DECISOES.md#D17`. |
| 2026-05-28 | **T10b ✅ done** | BoM 3646 BATELADA `consumption='warning' → 'strict'`. Replica D05 na BoM filha. Ver `testes/T10b-resultado.md`. |
| 2026-05-28 | **D18 + T33 antecipada + rota 162 ativada** | Pré-validação confirmou: 0 MOs ativas + 0 done recentes + 0 pickings em pt=74 usando BoM 14833. Desativação 100% segura. Rota 162 ativada (referenciada pelo WH FB). BoMs ativas do produto piloto agora = apenas 3695+3646. Ver `testes/T33-antecipada-resultado.md` + `DECISOES.md#D18`. |
| 2026-05-28 | **Diagnóstico prep T13 completo** | 11 categorias validadas (picking types, routes, locations, companies, partner, produto, BoMs, supplierinfo, fiscal, estoque, conflitos). 2 alertas menores (weight=0 ACIDO CITRICO e ÁGUA; 3 componentes reservados em FB/Estoque mas com saldo em LF/Estoque/FB/Indisponivel) não bloqueiam T13. Ver `testes/T13-prep-cadastros.md`. |
| 2026-05-29 | **D19 + T13 ⛔ skipped + AJUSTE-ESTOQUE done** | Rafael decidiu usar produto piloto 4870112 direto. T13 (com produto qualquer) fundida com T21. Estoque dos 3 componentes ajustado (+120 un TAMPA, +0.0256 kg ANTIESPUMANTE, +0.5845 kg AROMA) via skill `ajustando-quant-odoo` em lotes ativos. Ver `testes/T-AJUSTE-ESTOQUE-resultado.md`. |
| 2026-05-29 | **T21 PO+SO criadas (inter-company DISPAROU)** | PO 42659 (C2619775) em FB confirmed + picking RECEB/FB/IND/00018 pt=52 ✓ correção histórica. SO 73424 (VLF2600001) em LF auto-criada via inter-company + confirmed. Picking LF/OUT confirmed aguardando saldo. Detalhe `testes/T21-piloto-resultado.md`. |
| 2026-05-29 | **Config inter-company FB/LF warehouse_id setado** | T01 não cobria — descoberto durante T21. `res.company.warehouse_id` setado FB=WH FB (1), LF=WH LF (4). Sem isso button_confirm da PO falhava com "Configure o armazém correto para LA FAMIGLIA - LF". |
| 2026-05-29 | **D20 + A05 ⛔ resolved + T21b derivada** | Investigação profunda: rota MTO global (1) não dispara em LF (zero rules em cmp=5). Rota PSE LF (132) faria, mas 0/19 PAs LF usam. Histórico: MOs LF sempre manuais (Edilane). D20 mantém pattern: PCP LF cria MO manualmente para o piloto. PA cai em LF/Estoque por padrão (rule 135). |
| 2026-05-29 | **A05 ↩ REABERTA + corrigida**: PA → LF/PA de Terceiros (31093) | Rafael relembrou a spec. D20 estava errado em fechar com LF/Estoque. MO LF criada com `location_dest_id=31093` forçado. Picking LF/OUT (errado) cancelado. T07 executado (pt=98 LF/SAI/IND/RET). |
| 2026-05-29 | **T07 ✅ done** | pt=98 LF/SAI/IND/RET criado (src=31093 LF/PA Terceiros, dst=26489 Em Trânsito Industrialização, return_type=64). Será usado em T25 (NF retorno LF→FB). |
| 2026-05-29 | **MO LF 20154 criada** | LF/MO/03507, state=confirmed, qty=10, dst=LF/PA Terceiros (31093). 8 raw waiting (BATELADA + 7 embalagens). Aguardando componentes chegarem em LF via T22+T23. |
| 2026-05-29 | **Picking saída FB 322049 (FB/SAI/IND/01606) ✅ DONE** | 16 componentes saíram FB/Estoque → Em Trânsito Industrialização. Incoterm=CIF, carrier=NACOM GOYA. Ajustes residuais de estoque feitos (+0.0001 ANTIESPUMANTE, +0.0052 AROMA) para 100% reserva. |
| 2026-05-29 | **NF saída CFOP 5901 AUTORIZADA SEFAZ** ✅ | account.move 725676 RPI/2026/00242, posted, situacao_nf='autorizado'. **Chave NF-e: 35260561724241000178550010000945901007256765**. amount_untaxed=R$ 2.797,85 (16 linhas CFOP 5901). Transmissão Playwright autorizada em 1ª tentativa, ~56s. Ver `testes/T22-NF-saida-resultado.md`. |

---

## Decisões em aberto que bloqueiam

| Decisão | Bloqueia Task | Quem decide |
|---|---|---|
| ~~A01~~ | ⛔ resolved | D17 (BATELADA = subprocesso interno LF) |
| ~~A03~~ | ⛔ resolved | D19 (piloto direto com 4870112) |
| ~~A05~~ | ⛔ resolved | D20 (PA → LF/Estoque) |
| A02 — Contas por categoria (MP/semi) | T29 | Rafael (descobrir via consulta) |

---

## Riscos ativos

| Risco | Severidade | Próxima ação |
|---|---|---|
| Inter-company não dispara SO em LF após PO FB | Alta | T13 valida com produto qualquer |
| BoM tem componente inválido (X105000022) | Média | A01 — Rafael decide |
| CIEL IT não mapeia CFOPs corretamente | Média | T13 descobre + ajusta |
| OdooBot sem permissão suficiente | Baixa | Se aparecer no T13, criar usuário dedicado |

---

## Estimativa restante

- Sessões Claude até final piloto S1: **5–6**
- Sessões Claude até rollout 30 PAs concluído: **7–10**
- Tempo calendário até final piloto: **1–2 semanas**
- Tempo calendário até rollout completo: **5–7 semanas**

---

## Convenções

- Status: ⬜ pending, 🟡 in_progress, ✅ done, ❌ failed, ⏸️ blocked_human, ⛔ skipped
- IDs constantes: ver `CONTEXTO.md`
- Execução: dry-run primeiro, depois execute
- Resultado: `testes/T{NN}-resultado.md`
