# AUDITORIA — Plano original vs Realidade da sessão 2026-05-29

> Confronto MINUCIOSO entre IDs/estados previstos no plano (CONTEXTO + DECISOES + ROADMAP pré-sessão) e o que foi efetivamente realizado.

---

## 1. IDs previstos vs reais

### 1.1 Companies (CONTEXTO.md)
| Previsto | ID prev | Real usado | Status |
|---|---:|---:|---|
| NACOM GOYA - FB | 1 | 1 | ✅ |
| LA FAMIGLIA - LF | 5 | 5 | ✅ |
| SC | 3 (fora escopo) | não tocado | ✅ D07 |
| CD | 4 (fora escopo) | não tocado | ✅ D07 |

### 1.2 Partners (CONTEXTO.md)
| Previsto | ID prev | Real usado | Status |
|---|---:|---:|---|
| LF como partner em cmp=FB | 35 | 35 (PO 42659, supplierinfo 6319, picking) | ✅ |
| FB como partner em cmp=LF | (não listado no plano) | 1 (descoberto na sessão — `res.company.partner_id`) | 🆕 **achado faltante no CONTEXTO** |

### 1.3 Locations (CONTEXTO.md)
| Previsto | ID prev | Real | Status |
|---|---:|---:|---|
| FB/Estoque | 8 | 8 (picking saída src) | ✅ |
| LF/Estoque | 42 | 42 (não usado como dst da MO! Ver D23) | ⚠️ não foi destino |
| FB/Indisponivel | 31088 | 31088 (saldo de migração, não tocado) | ✅ |
| LF/Indisponivel | 31091 | 31091 (não tocado) | ✅ |
| Em Trânsito Industrialização | 26489 | 26489 (picking saída FB dst) | ✅ |
| Locais Fisicos/Local de subcontratação | 30713 | 30713 (substituído por 31092 — T04) | ✅ |
| **LF/Materiais Terceiros** (criada T02) | 31092 | 31092 | ✅ |
| **LF/PA de Terceiros** (criada T03) | 31093 | 31093 (dst MO LF 20154 — D23) | ✅ |

### 1.4 Picking Types (CONTEXTO.md)
| Previsto | ID prev | Real | Status |
|---|---:|---:|---|
| RECEB/FB (genérico) | 1 | 1 (NÃO USADO — correção pt=52) | ✅ evitado |
| FB/SAI/IND (saída ind) | 53 | 53 (picking saída FB 322049 ✓) | ✅ |
| RECEB/FB/IND (entrada retorno) | 52 | 52 (picking RECEB/FB/IND/00018 ✓) | ✅ |
| LF/RECEB/IND (entrada remessa LF) | 64 | 64 (esperado para entrada LF — caminho A não usado) | ⏸️ não testado |
| FB Subcontratação | 74 | 74 reativado T05, **não usado** | ✅ reativado, não chamado |
| RES Reposição p/ subcontratação | 75 | 75 (não disparado — D16 caminho A falhou) | ⚠️ |
| LF Subcontratação | 80 | 80 reativado T06, **não usado** | ✅ |
| LF Reposição p/ subcontratação | 81 | 81 não tocado | ✅ T09 skipped |
| **LF/SAI/IND/RET** (T07) | (a criar) | **98** (criado nesta sessão) | ✅ |

### 1.5 Routes (CONTEXTO.md)
| Previsto | ID prev | Real | Status |
|---|---:|---:|---|
| Fabricar (LF) | 134 | 134 (no produto, mas MO criada manual) | ⚠️ inerte |
| FB Reposição p/ subcontratação | 162 | 162 ativada (D18) mas 0 stock.rules criadas | ⚠️ caminho A do D16 falhou |
| LF Reposição p/ subcontratação | 166 | 166 inativa (T09 skipped) | ✅ |
| Subcontracting global | a verificar | NÃO usada (subcontract path não disparou) | ⚠️ |
| MTO global | (T11 adicionou id=1) | **1 ADICIONADA AO PRODUTO mas não funciona em LF** (rota 132 PSE LF seria correta) | ⚠️ DÍVIDA TÉCNICA |

### 1.6 Produto piloto (CONTEXTO.md)
| Previsto | ID prev | Real | Status |
|---|---:|---:|---|
| product.product 4870112 | 27834 | 27834 ✓ | ✅ |
| product.template 4870112 | 42282 | 42282 ✓ | ✅ |
| BoM 14833 subcontract (será desativada T33) | 14833 | 14833 desativada antecipada (D18) | ✅ |
| BoM 3695 normal LF (Opção 2) | 3695 | 3695 + consumption=strict (T10) | ✅ |
| **BoM 3646 filha BATELADA** | (não no plano) | 3646 descoberta D17 + consumption=strict (T10b) | 🆕 **achado D17** |
| Semi BATELADA DE SHOYU | (não no plano) | id=29986 tmpl=44550 | 🆕 **achado D17** |
| Supplierinfo PA R$ 35,00 LF | 6319 | 6319 ✓ (usado pela PO 42659) | ✅ |

### 1.7 Contas contábeis FB (CONTEXTO.md)
| Previsto | ID prev | Real usado na NF 725676 | Status |
|---|---:|---|---|
| MATERIAL DE EMBALAGEM | 22289 (1150100002) | invoice line account: não verificado | ⏸️ A02 |
| PRODUTO-ACABADO | 22294 (1150100007) | a usar em T26 | ⏸️ |
| RECEBIMENTO FISICO FISCAL | 26842 (1150100011) | a usar em T26 | ⏸️ |
| MATERIAL EM TERCEIROS | (a buscar) (1150200001) | a usar em T22 lançamento | ⏸️ A02 ainda aberto |

### 1.8 IDs criados na sessão e ainda NÃO no CONTEXTO.md
🆕 **Falta documentar em CONTEXTO bloco "IDs descobertos no piloto"**:
| Tipo | ID | Nome | Função |
|---|---:|---|---|
| `l10n_br_ciel_it_account.operacao` | 1917 | Industrialização efetuada por outra empresa (ICMS 51) | PO FB → l10n_br_operacao_id na linha |
| `l10n_br_ciel_it_account.operacao` | 2686 | Remessa de mercadoria remetida p/ industrialização | PO LF entrada — `tipo_pedido_entrada='serv-industrializacao'` |
| `l10n_br_ciel_it_account.operacao` | 80 | Remessa p/ Industrialização | NF saída CFOP 5901 |
| `l10n_br_ciel_it_account.cfop` | 11 | 1124 - Industrialização efetuada por outra empresa | PO FB linha (intra-estadual SP→SP) |
| `l10n_br_ciel_it_account.cfop` | 101 | 1901 - Entrada p/ industrialização por encomenda | PO LF entrada linha |
| `l10n_br_ciel_it_account.cfop` | 307 | 5124 - Industrialização efetuada p/ outra empresa | NF retorno PA T25 |
| `l10n_br_ciel_it_account.cfop` | 391 | Remessa p/ industrialização por encomenda (5901) | NF saída atual |
| `account.fiscal.position` (FB) | 25 | REMESSA PARA INDUSTRIALIZAÇÃO | NF saída FB 725676 |
| `account.fiscal.position` (LF) | 131 | ENTRADA - REMESSA INDUSTRIALIZAÇÃO LF | PO LF (esperado) |
| `account.journal` (FB) | 17 | REMESSA PARA INDUSTRIALIZAÇÃO | NF saída 725676 |
| `account.incoterms` | 6 | CIF | obrigatório no picking saída |
| `delivery.carrier` | 996 | NACOM GOYA INDUSTRIA (transporte próprio) | obrigatório no picking saída |
| `stock.warehouse` (FB) | 1 | WH FB (default da company FB) | inter-company config (T01 gap) |
| `stock.warehouse` (LF) | 4 | WH LF (default da company LF) | inter-company config (T01 gap) |

---

## 2. Estados previstos vs reais

### 2.1 Fluxo macro (CONTEXTO.md linhas 32-40 — "Solução adotada")

| Previsto no plano | Realidade |
|---|---|
| PO de compra FB→LF dispara SO espelhado em cmp=LF via `sale_purchase_inter_company_rules` (instalado) | ✅ PO 42659 → SO 73424 (origem corretamente referenciada em `client_order_ref`) |
| SO LF + MTO + BoM normal 3695 dispara MO em cmp=LF | ❌ MO NÃO disparada automaticamente (rota MTO 1 não tem rules em LF). MO criada **manualmente** (D20 caminho concorrente). |
| PCP LF aponta MO em cmp=LF normalmente (consumo, perda, produção) | ⏸️ MO 20154 criada mas state=confirmed (aguardando reserva — componentes ainda em "Em Trânsito Industrialização") |
| Componentes da FB tratados como "estoque de terceiros" via location dedicada em cmp=LF | ⏸️ Componentes saíram FB (T22 OK) mas ainda não entraram em LF/Materiais Terceiros — bloqueio A08 |
| NF de retorno LF→FB com 3 CFOPs por linha (5124 PA + 5902 consumo+perda + 5903 sobra) — Caminho C | ⬜ Ainda não testado (T25 não chegou) |
| Recebimento FB usa picking_type=52 (não 1 genérico) | ✅ Picking RECEB/FB/IND/00018 com pt=52 — **CORREÇÃO HISTÓRICA confirmada como prevenção (mas ainda não testada com DFe retorno real)** |

### 2.2 Decisões D01-D15 (originais) — status pós-sessão

| # | Decisão | Status |
|---|---|---|
| D01 | Caminho C (5902 cobre consumo+perda; 5903 só sobra) | ⏸️ não testado (NF retorno não emitida) |
| D02 | Apenas água é insumo próprio LF | ✅ refletido em D17 (água excluída da remessa CFOP 5901) |
| D03 | Valor R$ 35,00/cx via supplierinfo 6319 | ✅ usado na PO 42659 e na invoice 725676 (amount_untaxed = R$ 2.797,85 dos componentes; valor agregado vem na NF retorno) |
| D04 | CIEL IT mapeia CFOP por linha | ✅ confirmado (16 linhas com CFOP 5901 na invoice 725676) |
| D05 | Opção B strict | ✅ T10 + T10b (BoMs 3695 e 3646 ambas strict) |
| D06 | BoMs subcontract sem revisão | n/a (subcontract path não disparou) |
| D07 | Escopo só FB↔LF | ✅ |
| D08 | 1 PO piloto 10 cx | ✅ PO 42659 |
| D09 | Virada gradual após validação Fiscal | ⬜ não chegou |
| D10 | Opção 2 (inter-company / MO cmp=LF) | ✅ inter-company funcionou; ⚠️ MO manual (não automática como D10 inferiu) |
| D11 | 2 estoques novos LF/Materiais Terceiros + LF/PA Terceiros | ✅ T02 (31092) + T03 (31093) |
| D12 | Criar regras nas rotas 162 e 166 | ⛔ skipped (T08 caminho A D16 falhou; T09 LF não subcontrata) |
| D13 | BoM 14833 ativa pré-piloto | superseded: desativada antecipada (D18) |
| D14 | Remessa complementar via PO complementar | ⬜ não testado |
| D15 | PCP LF revisa BoMs no rollout | ⬜ aplicará no rollout |

### 2.3 Decisões D16-D23 (novas da sessão)

| # | Decisão | Origem |
|---|---|---|
| D16 | T08 caminho A (pular stock.rule cross-company) | sessão de 2026-05-28 |
| D17 | BATELADA é subprocesso interno LF (BoM hierárquica 3695→3646) | sessão de 2026-05-28 |
| D18 | Antecipar T33 + ativar rota 162 antes de T13 | sessão de 2026-05-28 |
| D19 | Fusão T13+T21 (piloto direto com 4870112) | sessão de 2026-05-29 |
| D20 | Caminho concorrente: MO LF manual | sessão de 2026-05-29 |
| D21 | Caminho B Skill 7 (DFe via XML autorizado) | sessão de 2026-05-29 |
| D22 | Manter NF 725676 autorizada SEFAZ | sessão de 2026-05-29 |
| D23 | A05 corrigida: PA → LF/PA Terceiros (31093), supersede D20 | sessão de 2026-05-29 |

### 2.4 Tasks do ROADMAP_TASKS.md — status pós-sessão

| Task | Plano original | Real |
|---|---|---|
| T01 | Validar inter-company FB↔LF | ✅ done (XML-RPC). ⚠️ Faltava `warehouse_id` na config (descoberto em T21) — `T01 gap`. |
| T02 | Criar LF/Materiais Terceiros | ✅ id=31092 |
| T03 | Criar LF/PA de Terceiros | ✅ id=31093 |
| T04 | property_stock_subcontractor da LF | ✅ aponta para 31092 |
| T05 | Reativar pt=74 | ✅ (não usado depois — subcontract path não disparou) |
| T06 | Reativar pt=80 | ✅ (não usado) |
| T07 | Criar LF/SAI/IND/RET | ✅ id=98 (esta sessão) |
| T08 | stock.rule rota 162 | ⛔ skipped (D16 caminho A) — confirmado em T21: ZERO stock.rules criadas em 162 |
| T09 | Rota 166 | ⛔ skipped (T09 análise) |
| T10 | BoM 3695 strict | ✅ |
| T10b | BoM 3646 strict | ✅ (derivada de D17) |
| T11 | Adicionar rota MTO 1 ao produto | ✅ mas DÍVIDA TÉCNICA (rota 132 PSE LF seria correta — MTO 1 só tem rules em FB) |
| T12 | Mapear journals | ✅ |
| T13 | Teste produto qualquer | ⛔ skipped (D19 fundido com T21) |
| T14 | Documentar lições T13 | n/a |
| T15 | Snapshot pré-piloto | n/a |
| T21 | Piloto E2E direto | 🟡 in_progress: PO+SO+picking saída+NF SEFAZ ✓ ; MO criada (D20+D23); A08 bloqueio |
| T22 | NF saída FB CFOP 5901 | ✅ AUTORIZADA SEFAZ (chave 35260...6765) — **mas com 16 linhas, não 17 como D17 previu** — investigar |
| T23 | DFe entra na LF | ⏸️ tentativa caminho B (D21) → bloqueio A08 |
| T24 | Apontar MO LF | ⬜ |
| T25 | NF retorno LF→FB | ⬜ |
| T26 | DFe FB + pt=52 | ⬜ |
| T27 | Validar fechamento | ⬜ |
| T28 | Pacote final | ⬜ |
| T33 | Desativar BoM 14833 (pós-piloto) | ✅ antecipada D18 |
| T34 | Rollout 29 PAs | ⬜ (dívida T11: corrigir rota 132 antes de rolar) |

---

## 3. Divergências factuais entre plano e realidade

### 3.1 ✅ D17 CORRIGIDA: 16 componentes (não 17) — RESOLVIDO 2026-05-29

D17 original (CONTEXTO.md linha 119): "Escopo total da remessa FB→LF: **17 componentes** = 7 embalagens (BoM 3695) + 9 químicos + 1 MP shoyu_tradicional (BoM 3646)".

**Validação empírica NF 725676**: **16 linhas product** confirmadas via XML-RPC:
- 7 embalagens (210030322 ROTULO, 210030110 TAMPA, 210030203 CAIXA, 207210014 ETIQUETA, 208000008 FILME, 208000010 FITA, 210030010 FRASCO)
- **8 químicos** (BENZOATO, CORANTE, SAL, SORBATO, ACIDO CITRICO, ANTIESPUMANTE, ACUCAR, AROMA) — NÃO 9 como D17 dizia
- 1 MP shoyu_tradicional (105000022)
- = **7 + 8 + 1 = 16**

**Causa do erro original em D17**: contagem incorreta dos químicos da BoM 3646. A BoM 3646 tem 10 linhas total = 8 químicos + 1 ÁGUA + 1 MP. O bloco "9 químicos + 1 MP" estava errado (incluía a ÁGUA como químico, então deveria ser "9 químicos+água + 1 MP — exclui água" = 8 + 1).

**D17 corrigida** em DECISOES.md nesta sessão (2026-05-29) com a contagem certa (16 componentes).

### 3.2 ⚠️ T01 estava considerado completo mas faltava `warehouse_id`

T01-resultado.md fechou com `rule_type='sale_purchase'` + intercompany_user OK. Mas o piloto travou na hora do button_confirm da PO com "Configure armazém para LF". Não foi previsto.

### 3.3 ⚠️ T11 fez algo SEM EFEITO real (rota 1 vs 132)

T11 adicionou rota MTO global id=1 ao produto. Plano: "para que SO LF (vinda de PO FB via inter-company) dispare MO automaticamente". Realidade: rota 1 tem 46 rules todas em cmp=FB; em LF não faz nada. A rota correta seria 132 PSE LF, que NENHUM dos 19 PAs LF amostrados usa.

### 3.4 ⚠️ D10 inferia procurement automático mas histórico LF é manual

D10 ("Opção 2 inter-company / MO cmp=LF"): "PCP LF aponta MO em cmp=LF normalmente". Plano implícito: SO LF dispara MO via MTO. Realidade: MOs em LF historicamente são CRIADAS MANUALMENTE por Edilane (PCP LF). D20 oficializou esse caminho concorrente.

### 3.5 ✅ A02 (contas contábeis) — VALIDADA EMPIRICAMENTE NF saída

A02 estava bloqueando T29. Validação empírica via XML-RPC nas 16 linhas da invoice 725676 mostrou:

**Account_id único usado em TODAS as 16 linhas**: `account.account` id=**26846** code=**1150100012** name="FATURAMENTO FISICO FISCAL" (cmp=FB).

Contas previstas no plano original NÃO foram usadas na NF saída:
- ❌ 1150100002 MATERIAL EMBALAGEM (não usada)
- ❌ 1150100007 PRODUTO-ACABADO (não usada — NF retorno T25)
- ❌ 1150100011 RECEBIMENTO FISICO FISCAL (transitória — não usada)
- ❌ 1150200001 MATERIAL EM TERCEIROS (não usada — pode aparecer T25)

**Pendente**: contas usadas em NF retorno T25 (5124 PA + 5902 componentes + 5903 sobras) — verificar quando emitida.

A02 marcado **parcialmente resolved** em ABERTOS.md (NF saída fechada; restante para T25).

### 3.6 ❌ D16 caminho A FALHOU silenciosamente (esperado)

D16 caminho A previa: "Ao primeiro PO inter-company que disparar fluxo subcontract, o módulo vai consultar essa rota — agora ativa, e CRIAR stock.rules automaticamente". Realidade: ZERO stock.rules foram criadas na rota 162 após confirm da PO 42659. T08 NÃO pode mais ser deixado pendente para T13 — precisa decidir caminhos B/C/D/E. Mas como o fluxo continuou via MO manual (D20), T08 deixou de ser bloqueante para o piloto. **Permanece bloqueante para o rollout futuro**.

### 3.7 🆕 Caminho B Skill 7 (não previsto no plano original)

T23 do plano original previa esperar DFe chegar via SEFAZ (caminho A). Sessão usou caminho B Skill 7 — atalho operacional. Esse caminho não estava roadmapeado, foi decisão D21 da sessão.

### 3.8 🆕 BoM 3646 filha (não no CONTEXTO original)

CONTEXTO original tinha só BoM 3695. D17 descobriu hierarquia 3695 → 3646 com BATELADA semi-acabado. CONTEXTO foi atualizado (linhas 88+) e foi adicionada T10b (consumption=strict na BoM filha).

---

## 4. Achados de PROCESSO não documentados como reprodutíveis

(Para o rollout T34 dos 29 PAs, esses passos vão precisar ser executados de novo)

| Operação | Como foi feito nesta sessão | Reprodutibilidade |
|---|---|---|
| Ajuste estoque (5 writes) | Skill `ajustando-quant-odoo` via CLI | ✅ skill versionada |
| PO FB com l10n_br_operacao_id na LINHA (não header) | Write XML-RPC manual após onchange falhar | ⚠️ não há script versionado |
| PO FB com l10n_br_cfop_id na linha | Write XML-RPC manual | ⚠️ não há script versionado |
| warehouse_id em FB+LF | Write XML-RPC direto | ⚠️ não há script versionado |
| Picking saída FB com 16 stock.moves | Loop create XML-RPC + button_validate | ⚠️ não há script versionado |
| MO LF com dst forçado | mrp.production.create + action_confirm via XML-RPC | ⚠️ não há script versionado |
| incoterm CIF + carrier NACOM no picking | Write XML-RPC após erro de action_liberar_faturamento | ⚠️ não há script versionado |
| action_liberar_faturamento | execute_kw direto | ✅ caminho oficial da Skill 8 — só falta encapsular |
| transmitir_nfe_via_playwright | Service direto (Skill 8 bloqueia por ajuste_ids vazios) | ⚠️ Skill 8 precisa aceitar ajuste_ids vazios para piloto |
| Skill 7 caminho B (criar DFe via XML autorizado) | 3 átomos Skill 7 v19+ chamados em sequência | ✅ átomos existem em escrituracao.py |

---

## 5. Conclusões da auditoria

### 5.1 Plano X realidade — convergência

- IDs constantes (companies, locations, pt) bateram 100%
- Decisões D01-D15 ainda válidas (D10, D12 com nuances explicadas em D16/D20/D23)
- Fluxo macro está no esperado APESAR dos workarounds (gap company A08 vai resolver)

### 5.2 Plano X realidade — divergências importantes

1. **D17 (17 vs 16 componentes)** — recontar e atualizar D17 ou T22
2. **T01 incompleta** — faltou `warehouse_id` (T01-resultado precisa nota de adendo)
3. **T11 ineficaz** — rota MTO 1 não funciona em LF (dívida técnica)
4. **D16 caminho A confirmado falhou** — D12 D14 D14 todos invalidados pra subcontract (mas piloto continua via Opção 2)
5. **D20 superseded por D23** (já corrigido em DECISOES.md)
6. **Caminho B Skill 7 (D21)** — não estava no plano original, é atalho operacional

### 5.3 Reprodutibilidade

7 operações manuais (PO line writes, picking saída FB, MO LF, etc) não estão como scripts versionados. Risco para rollout T34 dos 29 PAs. **Recomendação**: criar `scripts/T22a_criar_picking_saida_fb.py` e `scripts/T21b_criar_mo_lf.py` antes do rollout.

### 5.4 A02 retroativamente fechável

Account_ids usados nas 16 linhas da invoice 725676 já estão no Odoo. Bastam 2 queries XML-RPC para fechar A02 sem esperar T29.

---

## Síntese final

| Categoria | Total previsto | Real conforme | Divergente | Não testado |
|---|---:|---:|---:|---:|
| IDs | 24 | 24 | 0 | — |
| Decisões D01-D15 | 15 | 8 | 4 (D10/D12/D13/D14 nuances) | 3 (D01/D09/D14) |
| Tasks T01-T15 | 15 | 11 | 0 | 4 |
| Tasks S1 piloto | 8 | 1 (T21 parcial) | 0 | 7 |
| Estados macro fluxo | 5 | 3 | 1 (MO manual vs MTO auto) | 1 (T25 retorno) |

**Maior gap descoberto na auditoria**: D17 dizia 17 componentes mas eu documentei 16 em T22 — precisa recontagem. Não é erro do plano, é divergência do meu documento.
