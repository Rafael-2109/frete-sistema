# T23 — Caminho B Skill 7 (criar DFe em LF a partir do XML NF saída) — PARCIAL

**Status final**: 🟡 paused — PO cancelada por **gap não previsto** (PO criada em company FB em vez de LF)
**Executado em**: 2026-05-29
**Executor**: Claude via XML-RPC (Skill 7 ABRANGENTE v19+ átomos)

---

## Por que esse caminho

Rafael sugeriu **caminho B** (mais rápido que esperar DFe SEFAZ propagar):
- Já temos XML autorizado da NF 725676 (RPI/2026/00242) no campo `l10n_br_xml_aut_nfe`
- Skill 7 v19+ tem átomo `criar_dfe_a_partir_do_invoice_saida` que faz exatamente isso

Sequência dos átomos Skill 7 v19+ (todos chamados):

| # | Átomo | Resultado |
|---|---|---|
| 1 | `criar_dfe_a_partir_do_invoice_saida(invoice_id=725676, company_destino=5)` | ✅ DFe id=**43689** criado em LF + B-V23-1 fix aplicado (16 dfe.lines company_id→LF) |
| 2 | `escriturar_dfe(dfe_id=43689, l10n_br_tipo_pedido='serv-industrializacao')` | ✅ ESCRITURADO (data_entrada=2026-05-29) |
| 3 | `gerar_po_from_dfe(dfe_id=43689)` | ✅ CRIADO PO id=**42676** (C2619787, ~179s) |

---

## Gap descoberto na PO 42676

`action_gerar_po_dfe` do robô CIEL IT criou PO em **company errada** (FB em vez de LF):

| Campo | Plano (LF entrada CFOP 1901) | Real na PO 42676 |
|---|---|---|
| `company_id` | **5 (LF)** | ❌ 1 (FB) |
| `partner_id` | NACOM GOYA - FB (1) | ✓ 1 |
| `l10n_br_tipo_pedido` | `serv-industrializacao` | ✓ |
| `l10n_br_operacao_id` | **2686** (Remessa industrialização entrada LF) | ❌ False |
| `fiscal_position_id` | **131** (ENTRADA - REMESSA INDUSTRIALIZAÇÃO LF) | ❌ False |
| `picking_type_id` | **64** (LF/RECEB/IND) | ❌ 1 (FB) |
| Linha `l10n_br_cfop_id` | 101 (CFOP 1901) | ❌ False |
| Linha `account_id` | equivalente LF de 22611 | ❌ 22611 (FB) |

**Causa raiz suspeitada**: Rafael (uid=42) tem `company_id` principal = FB (1). O robô CIEL IT herda esse contexto ao executar `action_gerar_po_dfe`. Apesar do DFe estar em company=LF (5), a PO sai em FB.

Isso é variante do AP6 / D-V25-1 do projeto inventário — mas a correção F2/F3 v25+ é específica para **inventário INDUSTRIALIZACAO_FB_LF**, que tem semântica fiscal diferente da nossa industrialização real.

---

## Confronto F3 v25+ X plano industrialização REAL

| Aspecto | F3 v25+ (inventário INDUSTRIALIZACAO_FB_LF) | Plano industrialização real (operação 2686) |
|---|---|---|
| Caso real | Mascarar lacuna fiscal de inventário inter-company sem fluxo formal | NF de remessa para industrialização CFOP 5901 (formal SEFAZ) |
| Tipo do DFe | `'compra'` (destrava action_gerar_po_dfe no robô) | `'serv-industrializacao'` (l10n_br_tipo_pedido_entrada da op 2686) |
| Tipo do PO | `'serv-industrializacao'` | `'serv-industrializacao'` (mesmo) |
| Operação | (mapeada via CONSTANTS_FLUXO_L3 v20+) | **2686** (LF entrada com CFOP 1901) |
| fiscal_position | (varia por direção CD/FB/LF) | **131** ENTRADA REMESSA INDUSTRIALIZAÇÃO LF |

Inicialmente assumi F3 v25+ por estar na constituição do projeto inventário, mas Rafael apontou: **isso é INDUSTRIALIZAÇÃO REAL, não inventário**. O tipo correto vem da operação CIEL IT cadastrada (2686 → `serv-industrializacao`). Mesmo nome de string mas semântica fiscal diferente — `'compra'` foi descartado.

---

## Ação tomada

- ✅ **PO 42676 cancelada** (`button_cancel` → state=cancel)
- ✅ **DFe 43689** ficou com `l10n_br_status='06'` (PO cancelada), `purchase_id=False` — pronto para nova tentativa
- DFe não tem `action_cancel` (modelo Odoo); status atual é compatível com reaproveitamento

## Artefatos Odoo após cancelamento

| Item | ID | Estado | Observação |
|---|---:|---|---|
| NF saída 725676 RPI/2026/00242 | 725676 | posted, autorizado SEFAZ | **NÃO PODE CANCELAR** (processo formal 24h) |
| DFe LF 43689 | 43689 | status=06, sem PO | Pronto para nova tentativa `gerar_po_from_dfe` em próxima sessão |
| PO 42676 (cancelada) | 42676 | cancel | Cancelada |
| MO LF 20154 | 20154 | confirmed | Aguardando componentes |
| Picking saída FB/SAI/IND/01606 | 322049 | done | 16 componentes em Em Trânsito Industrialização |
| Picking RECEB/FB/IND/00018 (entrada PA futuro FB) | 322039 | assigned | Esperando retorno PA |
| SO 73424 (VLF2600001) LF | 73424 | sale | Confirmada (criada via inter-company) |
| PO 42659 (C2619775) FB | 42659 | purchase | Confirmada (ORIGEM do fluxo) |
| Locations 31092/31093 | 31092/31093 | active | LF/Materiais Terceiros + LF/PA Terceiros |
| picking_type 98 LF/SAI/IND/RET | 98 | active | T07 done |

---

## Próximo passo necessário (para próxima sessão)

Resolver o **issue da company** ao criar PO via `action_gerar_po_dfe`:

### Hipótese A — Switch de user
- Rodar `gerar_po_from_dfe` autenticado como user com company principal=LF
- Candidatos: Edilane (uid=78, PCP LF) — testar se tem grupo `purchase.group_purchase_manager`
- Alternativa: criar/configurar user dedicado

### Hipótese B — Forçar context via execute_kw
- `gerar_po_from_dfe` por dentro chama `action_gerar_po_dfe` sem contexto explícito
- Forçar `context={'allowed_company_ids': [5], 'force_company': 5}` no execute_kw

### Hipótese C — Skill 7 `preencher_po` post-hoc
- Após PO criada errada, usar `preencher_po` com TODOS os campos (operacao_id, fiscal_position_id, picking_type_id, company_id)
- Verificar se `preencher_po` aceita esses campos (provavelmente sim, pelo nome)

### Hipótese D — Write XML-RPC direto
- Write company_id=5, fiscal_position_id=131, operacao_id=2686, picking_type_id=64 na PO
- Write 16 linhas: account_id (LF) + l10n_br_cfop_id=101
- Risco: campos derivados que precisam recompute

Recomendação: **A** mais limpo (alinhado ao plano original Rafael+PCP LF executa). **C** segundo melhor (semântico).
