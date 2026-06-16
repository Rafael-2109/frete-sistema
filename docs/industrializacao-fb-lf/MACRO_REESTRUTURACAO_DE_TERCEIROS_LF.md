<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/industrializacao-fb-lf/INDEX.md
superseded_by: —
atualizado: 2026-06-15
-->
# MACRO — Reestruturação do estoque LF para "De Terceiros" (industrialização por encomenda)

> **Papel:** macro/esboço (Sessão 1) da reestruturação do estoque LF para "De Terceiros" (31092/31093) — As-Is/To-Be + plano de sessões com DoD/gate. **Abra quando:** for entender o panorama da frente ou acompanhar o faseamento S1→S4. Desenho detalhado da S2: `DESENHO_S2_REESTRUTURACAO_DE_TERCEIROS_LF.md`.

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
6. **Automação G1/G2:** validar consistência com 31092 (provada nos canários 0-3 **com o piloto que forçava 31092**). **⚠️ Pré-condição p/ ligar o cron G1 (descoberta 2026-06-16):** a descoberta usa `31092` **exato** (genealogia + entrada) → **janela de transição** (lotes pré-migração em 42) + **poluição do voto** pelo picking de migração — endurecer antes do cron: `DESENHO_S2 §7.1-D4`.

## Plano de sessões — DoD + GATE (decidido com Rafael; SEGUIR NA ORDEM)

> **🔒 Regra de faseamento (garantia de que as sessões sejam seguidas):** cada sessão só começa quando a anterior cumpriu sua **DoD** E foi **aprovada por Rafael** (4-mãos). **NÃO pular fases** — em especial, **NÃO implementar (S3) sem o desenho da S2 aprovado**, e **NÃO ligar SA (S4) sem a reestruturação (S3) concluída**. Cada sessão TERMINA atualizando: (1) a coluna Status desta tabela, (2) o banner + gatilho do `PROMPT_PROXIMA_SESSAO.md`.

| Sessão | Status | Foco | Definition of Done (DoD) | Gate p/ avançar |
|---|---|---|---|---|
| **S1** | ✅ | Macro | As-Is/To-Be mapeado + plano + reservas LF/Estoque limpas (este doc) | feito |
| **S2** | ✅ | Desenho + investigação ampla | Plano wired completo em **`DESENHO_S2_REESTRUTURACAO_DE_TERCEIROS_LF.md`** (investigação ao vivo `s72`–`s79`); decisões GATE tomadas (D1 terceiros contábil/L1 · D2 reparent 31092/31093 sob 42 · D3 açúcar depois) | **Rafael aprovou (GATE 15/06)** |
| **S3** | ✅ **FÍSICO** (A5 pend.) | Implementação Odoo | **A1 reparent ✅** + **A4 migração ✅** (439 quants, 0 SVL, saldo conservado, `s83`=gates OK) + **A2/A3 put-away ✅** (rules 3,4). Mecânica resolvida (codificar move.line manual + anti-dup at_confirm + wizard expiry via `finalizar_picking`). **Falta A5 repoint L1 (Contador)** + exceções (açúcar D3 / 3 sem-lote / 2 resíduos). | **A5 = go + Contador** |
| **S4** | ⬜ | Automação (SA) | **Pré-condição (D4): endurecer a descoberta G1** (genealogia+entrada `child_of 42` + exigir SVL no voto/preço — `DESENHO_S2 §7.1`) **antes** de ligar o cron + canary READ/oráculo. Depois: crons G1/G2 ligados (domain data-de-corte "daqui pra frente") + G2 SEFAZ piloto, sobre o estado reestruturado (= **estágio 4** do RUNBOOK `fluxos/1.1.4`) | **go duplo** (SEFAZ irreversível) |

## Checklist de investigação da Sessão 2 — ✅ RESOLVIDO em `DESENHO_S2_REESTRUTURACAO_DE_TERCEIROS_LF.md` (scripts `s72`–`s79`)
- [x] **PO/entrada:** pt19 compra (heterogêneo MP+EMB+PA, 16 já→31092), pt64 industrializ. (src real Clientes→42, gera SVL), ajustes 38→42, Model B Vendors→31092 — `s73`/`s75`/`s76`.
- [x] **Todas as rotas/rules** que tocam 42: 15 rules / 7 rotas mapeadas (src e dst) — `s73 §1.3`.
- [x] **Histórico de stock.move em 42** (365d): entradas/saídas por pt e por origem/destino; nenhum fluxo de subcontratação real — `s74 §1.5`.
- [x] **Contábil:** valoração é por `product.category` (não location; campos da location vazios); migração interna = **0 SVL** (2000 moves) — `s72`/`s75`/`s76 §1.7`. ⇒ premissa do MACRO refutada (§ DESENHO_S2 §2).
- [x] **Mecanismo de migração:** 443 quants em 42 direto (442 livres + 1 açúcar); picking interno único pt23, por categoria — `s72`/§4.
- [x] **Exceções:** açúcar = picking `321794`; lotes P-15/05 (82) e MIGRAÇÃO (5) migram normal — `s72`/`s75`.
- [x] **Subcontratação:** pt48/63 OFF, 0 moves reais — `s73`/`s74` (sem ação).
- [x] **Impacto entregas/retorno:** pt20/66/94/97 (conteúdo PA vs material) + pt98 já em 31093 — `s73`/`s77`.
- [x] **MOs/reservas ativas:** só MO 20797 (ketchup, em 53); única reserva = açúcar — `s75`.

## Estado preparado nesta sessão (não refazer)
- Reservas em LF/Estoque limpas: MO **03507 cancelada** (liberou 4 quants), picking **`LF/PC/03497` unreserved** (liberou 7 quants, da MO 03575 — batelada de ketchup mantida em Pré-Produção). Resta só o açúcar (1 quant, saída FB — fora da migração).
- Diagnóstico de saldo/origem/roteamento (As-Is) completo (este doc).
- Planilha de conferência: `/tmp/conferencia_LF_terceiros_2026-06-15.xlsx` (todos FB; sem exceções reais).
- **Automação (canary G1) — SAs já PROVISIONADAS no Odoo (inertes):** `ir.actions.server` **G1 `sa_id=2029`** + **G2 `sa_id=2030`** criadas (code = body versionado; `verificar` OK). **Crons NÃO ligados** (gated). A genealogia G1 explode de **31092** — por isso a reestruturação é pré-requisito de ligar a automação em produção real. Ligar crons + SEFAZ = Sessão 4 (estágio 4 do RUNBOOK `fluxos/1.1.4`).

## Contexto

Documento — industrializacao por encomenda FB<->LF. Tema: MACRO da reestruturação do estoque LF para "De Terceiros" (31092/31093). Rascunho da Sessão 1 (de 4); SOT do desenho detalhado será produzido na Sessão 2. Relacionado: `SOT_OPERACOES.md §"OBJETIVO FINAL"` (critério #4) + `ACHADOS_TECNICOS.md` + `app/odoo/estoque/fluxos/1.1.4`.
