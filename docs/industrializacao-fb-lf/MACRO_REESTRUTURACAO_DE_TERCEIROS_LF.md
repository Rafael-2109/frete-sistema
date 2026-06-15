<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/industrializacao-fb-lf/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# MACRO — Reestruturação do estoque LF para "De Terceiros" (industrialização por encomenda)

> **RASCUNHO MACRO (Sessão 1 de 4).** Decisão Rafael 2026-06-15: **Opção A — processo completo**. Material e PA da LF passam a viver fisicamente em **De Terceiros**. Esta é a etapa de macro/esboço; o desenho detalhado costurando todas as pontas (PO, processos, movimentos, histórico) é a **Sessão 2**. NÃO implementar a partir deste doc — ele lista o que investigar.

## Decisão e porquê
- **Alvo:** `LF/Materiais de Terceiros (31092)` para insumos/embalagens · `LF/PA de Terceiros (31093)` para o produto acabado.
- **Porquê:** a LF é **industrializadora por encomenda** — todo o material é da FB (terceiros; confirmado: 311 produtos / 5,66M un, FB compra 10,1bi vs LF 47M; saldo pré-Odoo carregado por ajuste). Hoje gira em `LF/Estoque (42)` como se fosse estoque próprio. Segregar em "De Terceiros" reflete a propriedade (físico + contábil) **e** torna a operação consistente com a **automação da NF de retorno** (a genealogia do G1 já explode de `31092`).

## As-Is (estado atual — mapeado nesta sessão)
**Hub = `LF/Estoque (42)`. `31092`/`31093` vazios, fora do fluxo.**

Locations-chave: `42` LF/Estoque · `53` LF/Pré-Produção · `31092` Mat. Terceiros · `31093` PA Terceiros · LF/Pós-Produção · "Em Transito (Industrialização)" · Subcontratação.

| Bloco | Como é hoje (ancorado em 42) |
|---|---|
| **Entrada industrialização** | picking_type **"Recebimentos Industrialização (LF)"**: Em Transito (Ind.) → **42** ⛔ (deveria ser 31092) |
| Entrada compras / recebimento / devoluções | rota "Comprar - LF" (act=buy) → 42 · "Recebimento (LF)" → 42 · "Devoluções (LF)" → 42 |
| **Abastecimento produção** | 2 rules "Escolha os Componentes": **42 → Pré-Produção** (são os pickings `LF/PC/*`) |
| Produção | Pré-Produção → MO → consome (move_raw src = Pré-Produção) |
| **Armazenagem PA** | 3 rules Pós-Produção → **42** + picking_type "Armazenar Produto Acabado (LF)" → 42 |
| Entrega / retorno | 2 rules **42 → Clientes** · 2 rules **42 → Subcontratação** |
| Automação G1 | genealogia explode de **31092** → **inconsistente** com a operação real (42) |

## To-Be (estado-alvo)
| Bloco | Alvo |
|---|---|
| Entrada industrialização | Em Transito (Ind.) → **31092** |
| Abastecimento produção | **31092 → Pré-Produção** |
| Produção | (igual; origem agora é terceiros) |
| Armazenagem PA | Pós-Produção → **31093** |
| Retorno industrialização | **31093 → FB** (NF retorno, automação G1/G2) |
| Contábil | conta de estoque de `31092`/`31093` = **estoque de terceiros** (não próprio) |
| Automação G1 | `31092` consistente com a operação real |

## Macro etapas da transição
1. **Saldo:** migrar `42 → 31092` (EMB+MP, 301 prod) / `31093` (PA, 10 prod). 444 quants livres (reservas já limpas — ver abaixo). Tratar exceções: açúcar (saída FB pendente), lote MIGRAÇÃO/P-15/05.
2. **Roteamento entrada:** picking_type "Recebimentos Industrialização" (+ avaliar compras/recebimento) dst `42 → 31092`.
3. **Roteamento produção:** rules "Escolha os Componentes" src `42 → 31092`; rules Pós-Produção→Estoque + picking_type "Armazenar PA" dst `42 → 31093`.
4. **Roteamento saída:** rules de entrega/retorno src `42 → 31093` (PA) / `31092`.
5. **Contábil:** definir conta de valoração de 31092/31093 (terceiros) vs a de 42.
6. **Automação G1/G2:** validar consistência com 31092 (já provada nos canários 0-3).

## Plano de sessões — DoD + GATE (decidido com Rafael; SEGUIR NA ORDEM)

> **🔒 Regra de faseamento (garantia de que as sessões sejam seguidas):** cada sessão só começa quando a anterior cumpriu sua **DoD** E foi **aprovada por Rafael** (4-mãos). **NÃO pular fases** — em especial, **NÃO implementar (S3) sem o desenho da S2 aprovado**, e **NÃO ligar SA (S4) sem a reestruturação (S3) concluída**. Cada sessão TERMINA atualizando: (1) a coluna Status desta tabela, (2) o banner + gatilho do `PROMPT_PROXIMA_SESSAO.md`.

| Sessão | Status | Foco | Definition of Done (DoD) | Gate p/ avançar |
|---|---|---|---|---|
| **S1** | ✅ | Macro | As-Is/To-Be mapeado + plano + reservas LF/Estoque limpas (este doc) | feito |
| **S2** | ⏭️ **PRÓXIMA** | Desenho + investigação ampla | Plano de execução **wired completo**, costurado ponta a ponta: PO/entrada · todas rotas/rules (src e dst=42) · histórico de `stock.move` em 42 · contábil · mecanismo de migração · exceções (ver checklist abaixo) | **Rafael aprova o plano** |
| **S3** | ⬜ | Implementação Odoo | Saldo migrado 42→31092/31093 + rules/picking_types reescritos + contábil ajustado; **validado** (saldo, reserva, produção, entrega não quebram) | **Rafael aprova** + go por escrita |
| **S4** | ⬜ | Automação (SA) | Crons G1/G2 ligados (domain data-de-corte "daqui pra frente") + G2 SEFAZ piloto, sobre o estado reestruturado (= **estágio 4** do RUNBOOK `fluxos/1.1.4`) | **go duplo** (SEFAZ irreversível) |

## Checklist de investigação para a Sessão 2 (não deixar passar nada)
- [ ] **PO/entrada:** como cada material entra — remessa de industrialização (FB) vs compra LF vs ajuste pré-Odoo. Mapear o roteamento de entrada completo e o alvo por tipo de entrada.
- [ ] **Todas as rotas/rules** que tocam 42 (as 7 src=42 + 4 dst=42 já listadas) + rotas completas (`stock.route`) e seus `rule_ids`.
- [ ] **Histórico de stock.move em 42** (janela ampla) para mapear TODOS os fluxos reais (entrada, consumo, PA, entrega, retorno, transferência, subcontratação) — garantir que nenhum fluxo fica órfão pós-mudança.
- [ ] **Contábil:** `property_stock_valuation_account_id` de 42 vs 31092/31093; impacto de SVL ao reclassificar; alinhamento com a conta de "estoque de terceiros".
- [ ] **Mecanismo de migração em massa** dos 444 quants: picking interno único (rastreável + reversível por estorno) vs skill `transferindo-interno-odoo` em loop (444 docs). Preservar lote (442/445 têm lote).
- [ ] **Exceções:** açúcar (saída FB `LF/LF/SAI/RNA/00103`), lotes MIGRAÇÃO/P-15/05, 4 produtos sem PO.
- [ ] **Subcontratação:** papel do "Local de subcontratação" no fluxo (rota subcontract).
- [ ] **Impacto entregas/retorno:** Ordens de Entrega (LF) e o retorno de industrialização (origem 42 hoje).
- [ ] **MOs/reservas ativas** no momento da migração (re-checar — hoje só restava o açúcar).

## Estado preparado nesta sessão (não refazer)
- Reservas em LF/Estoque limpas: MO **03507 cancelada** (liberou 4 quants), picking **`LF/PC/03497` unreserved** (liberou 7 quants, da MO 03575 — batelada de ketchup mantida em Pré-Produção). Resta só o açúcar (1 quant, saída FB — fora da migração).
- Diagnóstico de saldo/origem/roteamento (As-Is) completo (este doc).
- Planilha de conferência: `/tmp/conferencia_LF_terceiros_2026-06-15.xlsx` (todos FB; sem exceções reais).
- **Automação (canary G1) — SAs já PROVISIONADAS no Odoo (inertes):** `ir.actions.server` **G1 `sa_id=2029`** + **G2 `sa_id=2030`** criadas (code = body versionado; `verificar` OK). **Crons NÃO ligados** (gated). A genealogia G1 explode de **31092** — por isso a reestruturação é pré-requisito de ligar a automação em produção real. Ligar crons + SEFAZ = Sessão 4 (estágio 4 do RUNBOOK `fluxos/1.1.4`).

## Contexto

Documento — industrializacao por encomenda FB<->LF. Tema: MACRO da reestruturação do estoque LF para "De Terceiros" (31092/31093). Rascunho da Sessão 1 (de 4); SOT do desenho detalhado será produzido na Sessão 2. Relacionado: `SOT_OPERACOES.md §"OBJETIVO FINAL"` (critério #4) + `ACHADOS_TECNICOS.md` + `app/odoo/estoque/fluxos/1.1.4`.
