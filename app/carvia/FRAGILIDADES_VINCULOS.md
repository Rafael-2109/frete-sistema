<!-- doc:meta
tipo: state
camada: L2
sot_de: fragilidades-vinculos-carvia
hub: app/carvia/CLAUDE.md
superseded_by: —
atualizado: 2026-06-22
-->
# Fragilidades de vínculo — CarVia

> **Papel:** índice consolidado das 11 fragilidades estruturais de INTEGRIDADE DE VÍNCULO do módulo CarVia (auditoria 2026-06-22), com status e evidência file:line, referenciando os donos (`REVISAO_ARQUITETURA_2026.md`, `REVISAO_GAPS.md`) em vez de duplicar. **Abra quando:** for mexer em vínculo frete↔operação↔subcontrato↔custo, match de NF, ou avaliar dívida estrutural do módulo.

## Atualizado

2026-06-22 — auditoria do link Frete↔CTe (pedido do Rafael). #1 CORRIGIDO + backfill aplicado em prod (107 fretes). Demais ABERTAS.

## Estado atual

**Padrão-raiz comum** (liga #1, #2, #3, #4, #5, #6, #11): vínculos modelados como **FK singular (ou string CSV) populados num único momento (a criação da entidade dona), sem reconciliação quando a contraparte chega depois** — e com uma fonte-de-verdade alternativa (a junction `carvia_operacao_nfs`) que a UI ignora. Não são 11 bugs independentes; é o mesmo defeito em camadas diferentes.

| # | Fragilidade | Sev. | Status | Evidência (file:line) | Dono / já documentado |
|---|---|---|---|---|---|
| 1 | `frete.operacao_id` só populado na CRIAÇÃO; CTe importado depois nunca re-vincula o frete (110/114 fretes "falso sem-CTe" em prod) | CRÍTICO | **CORRIGIDO 2026-06-22** | `carvia_frete_service.py:431,815-889`; `importacao_service.py` (`_revincular_fretes_da_operacao`); `frete_routes.py:43-45` | Era parcial em REVISAO_ARQUITETURA V1/R5; fix em CLAUDE.md R10-R13 + MIGRATIONS.md |
| 2 | Subcontrato (CTe de custo) importado nasce com `frete_id=NULL` → `frete.subcontratos` vazio, margem real não fecha | ALTO | ABERTO | `importacao_service.py:2294-2319`; `frete.py:138-144`; populador automático só no botão manual `frete_routes.py:1056-1064` | REVISAO_ARQUITETURA_2026.md V1 + falha estrutural A |
| 3 | Match de NF por `numeros_nfs` CSV + NF não-única (reemissão CANCELADA+ATIVA); ILIKE sem âncora de vírgula em vários callers | ALTO | ABERTO | `frete.py:49`; `frete_routes.py:761`, `custo_entrega_routes.py:1023`, `pedido_routes.py:535,703`; CLAUDE.md R1 | REVISAO_ARQUITETURA V3/FK4; **REVISAO_GAPS Refator 2.5** (junction `CarviaFreteNf`, PENDENTE) |
| 4 | FK singular DEPRECATED `CarviaFrete.subcontrato_id` (1:1) escrita em paralelo com `frete_id` (1:N) → divergência/stale | ALTO | ABERTO | `frete.py:80-91`; dupla escrita `frete_routes.py:896,1060`; `cte_custos.py:201-209` | REVISAO_ARQUITETURA FK5; **REVISAO_GAPS Refator 2.4** (PENDENTE) |
| 5 | Auto-link CE↔frete best-effort SILENCIOSO com fallback fraco por `(transportadora, cnpj)` `.first()` por data → pode vincular CE ao frete errado e propagar `operacao_id` | MÉDIO | ABERTO | `custo_entrega_autolink_service.py:91-104,106-113,116-117` | **NÃO documentado** como gap próprio |
| 6 | `cte_complementar.frete_id` no import resolve por `.first()` sobre `operacao_id` (1:N) → pode pendurar no frete errado | MÉDIO | ABERTO | `importacao_service.py:1009-1014` | REVISAO_ARQUITETURA V2 |
| 7 | `CteComplementar.custos_entrega` 1:N com `delete-orphan` no ORM mas fluxo é 1:1; FK sem `ondelete` no DB | MÉDIO | ABERTO | `cte_custos.py:81-86,151-156` (mitigado por R14) | REVISAO_ARQUITETURA FK7 |
| 8 | Conciliação/Movimentação financeira polimórficas (`tipo_documento`,`documento_id`) SEM FK ao documento; idem `CarviaAnexo` (S3 órfão) | MÉDIO | ABERTO | `financeiro.py:100-102,281-283`; `anexos.py:33-37`; limpeza só via `admin_service.py:233,329` | REVISAO_ARQUITETURA FK2/V6/FK3 |
| 9 | Status irreversível (R4) + conferência assimétrica → vínculo nascido errado e faturado/conferido sem rota limpa de reversão | MÉDIO | ABERTO | CLAUDE.md R4/R14.1 (cascade atrás de flag default False); `admin_service.py:215-216` | **REVISAO_GAPS GAP-23** (P1/ALTO) |
| 10 | Numeração sequencial por `MAX()+1` sem lock/sequence → colisão sob import concorrente/lote | MÉDIO | ABERTO | `cte_custos.py:88-103,301-316`; `importacao_service.py:2288-2298`; CLAUDE.md R7/R8 | REVISAO_ARQUITETURA FK6; **REVISAO_GAPS GAP-28** |
| 11 | Margem por frete = `valor_venda − valor_cotado` (cotação, não CTe real); agravada quando o lado-custo (sub) nem é vinculado | MÉDIO | ABERTO | `frete.py:185-197`; `valor_cte`/`valor_considerado` só no vínculo manual `frete_routes.py:1063-1064` | REVISAO_ARQUITETURA M1 + falha estrutural A |

## Pendencias

- **#1 (corrigido)** — frete 185 resolvido (era duplicata: op 239 RASCUNHO/CAR-235-6 cancelada pelo Rafael 2026-06-22 → backfill vinculou à op 238 FATURADO). Restam **3 "ambíguos"** (fretes 111, 202, 323) que NÃO são ambiguidade real: cada um é **1 frete = 2 NFs, cada NF com seu próprio CTe FATURADO** — a FK singular `operacao_id` não comporta 2 CTes, então ficam NULL até a junction N:N `CarviaFreteNf` (Refator 2.5). Decisão Rafael: tratar depois.
- **Estruturais de maior ROI (atacam o padrão-raiz)**: Refator 2.5 (junction `CarviaFreteNf` como SOT, mata #3 e parte de #1/#2) e Refator 2.4 (aposentar `subcontrato_id`, mata #4) — ambos PENDENTES em `REVISAO_GAPS.md`. Match por `chave_acesso_nf` (44 díg.) em vez de `numero_nf` fecharia #3 na raiz.
- **#2** (subcontrato `frete_id=NULL` no import) é o espelho de #1 no lado-custo — mesma solução (re-link no import), ainda não feito.
- **#5** é o único sem dono documentado — registrar em `REVISAO_ARQUITETURA_2026.md` ao priorizar.

> Detalhe arquitetural completo (com fluxogramas e classificação epistêmica): [REVISAO_ARQUITETURA_2026.md](REVISAO_ARQUITETURA_2026.md). Gaps numerados e refatores pendentes: [REVISAO_GAPS.md](REVISAO_GAPS.md).
