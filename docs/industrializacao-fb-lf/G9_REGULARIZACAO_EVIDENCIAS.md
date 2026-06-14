<!-- doc:meta
tipo: reference
camada: L3
sot_de: regularizacao historica (G9) da industrializacao FB<->LF
hub: docs/industrializacao-fb-lf/INDEX.md
superseded_by: —
atualizado: 2026-06-14
-->
# G9 — Regularização histórica da industrialização FB↔LF (evidências + dimensionamento)

> **Papel:** evidências medidas ao vivo (Odoo PROD, READ-only, uid 42, 2026-06-14) para planejar a **correção retroativa** das contabilizações de industrialização que inflam o estoque/ativo da FB. É a **Pergunta 4 da Contadora** / **GOALS G9** ("como regularizar os saldos históricos já abertos — item separado, sem prazo"). O fluxo **prospectivo** (emitir retorno em 2 NFs) está no `SOT_OPERACOES.md`; **este doc é só o retroativo.**
> Scripts-fonte (READ-only, versionados): `scripts/g9_01_escopo_universo.py`, `scripts/g9_02_caso_abril2026.py`, `scripts/g9_03_transitorias_e_stock.py`.

## Indice

- [1. Item A — contabilização CORRETA × EM USO](#1-item-a--contabilização-correta--em-uso-nf--estoque)
  - [1.1 LF — SAÍDA / Retorno (j847)](#11-lf--saída--retorno-journal-j847)
  - [1.2 FB — ENTRADA / Recebe retorno (j1001)](#12-fb--entrada--recebe-retorno-journal-j1001-entsi)
- [2. Dimensionamento — saldos acumulados](#2-dimensionamento--saldos-acumulados-medido-2026-06-14)
  - [2.1 Universo de casos por período (j847)](#21-universo-de-casos-por-período-nfs-de-retorno-j847)
- [3. Restrição decisiva — LOCK DATES contábeis](#3--restrição-decisiva--lock-dates-contábeis-medido)
- [4. Item B — opções de método de correção](#4-item-b--opções-de-método-de-correção-proposta--exige-decisão-contadora)
- [5. Decisões pendentes (Rafael / Contadora)](#5-decisões-pendentes-para-rafael--contadora)
- [6. Caso-piloto APLICADO E VALIDADO (item C)](#6--caso-piloto-aplicado-e-validado-item-c-2026-06-14)
- [7. Levantamento completo do universo](#7-levantamento-completo-do-universo-item-2--g9_universo_desde_2025csv)
- [8. Plano de rollout](#8-plano-de-rollout-item-b--refinado-pós-teste)
- [Fontes](#fontes)
- [Contexto](#contexto)

---

## 1. Item A — contabilização CORRETA × EM USO (NF + estoque)

Evidência: caso real **NF LF `VND/2026/00234`** (id 562158, 2026-04-08, MOLHO SHOYU, R$ 2.798,95) ↔ entrada FB **`ENTSI/2026/04/0025`** (id 564486). Insumos da NF = **R$ 1.927,44** (16 linhas 5902); serviço = R$ 831,30.

### 1.1 LF — SAÍDA / Retorno (journal j847)

| Linha | EM USO (medido) | CORRETO (SOT §2 Et.4) |
|---|---|---|
| Serviço 5124 (op 2702) | `C 3101030001 SERVIÇOS / D 1120100001 CLIENTES` | ✅ igual (mantém) |
| Insumos 5902 (op 2864) | `C 1150100012 (transitória) / D CLIENTES` (embutido no recebível) | `D 5101020001 (PASSIVA) / C 1150100012` |
| **Efeito** | 🔴 **PASSIVA `5101020001` NÃO baixa** — insumos inflam o recebível e ficam pendurados em 1150100012 | PASSIVA baixa a cada retorno |

### 1.2 FB — ENTRADA / Recebe retorno (journal j1001 ENTSI)

| Linha | EM USO (medido) | CORRETO (SOT §2 Et.5) |
|---|---|---|
| Serviço 1124 (op 1917) | `D 1150100011 / C 2120100001 FORNECEDORES` | ✅ igual (a pagar serviço) |
| Insumos 1902 (op **2027**, `mov_estoque=True`) | `D 1150100011` **+** `C 1150100011` espelho (autocancela) **+ gera stock.move → entra estoque** | `D 1150100007 PA (incorpora custo) / C 5101010001 (baixa ATIVA)`, op **3252** (`mov_estoque=False`) **→ sem stock.move** |
| **Efeito** | 🔴 **ATIVA `5101010001` NÃO baixa** + 🔴 **insumos RE-ENTRAM no estoque físico FB (double-count)** | ATIVA baixa; PA valorado por Ic+S; estoque não infla |

> **Causa-raiz do "inflar o estoque da FB" (dois efeitos somados):**
> 1. **Contábil**: a conta de controle `5101010001` (ATIVA) é debitada na remessa e **nunca creditada** no retorno → acumula.
> 2. **Físico/valoração**: a op **2027** tem `l10n_br_movimento_estoque=True` → o retorno simbólico dos insumos **gera entrada de estoque**, re-inflando MP/embalagens que já haviam saído na remessa. A op **3252** (`mov_estoque=False`, criada no piloto) é a correta.

---

## 2. Dimensionamento — saldos acumulados (medido 2026-06-14)

| Conta (id Odoo) | Empresa | Saldo | Observação |
|---|---|---:|---|
| `5101010001` REMESSA IND. **ATIVA** (22800) | FB | **+R$ 61.930.965,26** | D 62,1M / C 0,21M — quase nada baixou |
| `5101020001` REMESSA IND. **PASSIVA** (26667) | LF | **−R$ 37.749.509,88** | C 37,75M |
| `5101010001` **ATIVA** (26652) | LF | **+R$ 8.674.765,50** | 🔴 LF debitando ATIVA via PERDAS (errado); 8,17M só em 2026 |
| `5101020001` **PASSIVA** (22815) | FB | **−R$ 13.298.623,42** | C 13,3M (a investigar — FB não deveria ter PASSIVA relevante) |
| Insumos 5902 sem baixa (j847, op 2864/2710) | LF | **R$ 43,1M** (2024-26) | 2024: 10,8M · 2025: 22,9M · 2026: 9,4M |

> ⚠️ **Assimetria a entender antes de regularizar:** ATIVA FB (61,9M) ≠ PASSIVA LF (37,7M) — não são espelhos perfeitos. A ATIVA FB é alimentada ~100% pelas **remessas** (j17/cfop 5901); a PASSIVA LF pela **entrada** (ENTIN). Diferença = timing remessa↔retorno + valores + a perna LF-PERDAS que vaza para a ATIVA LF.

### 2.1 Universo de casos por período (NFs de retorno, j847)

- **Range real**: `2024-08-12` → `2026-06-14`. **Total 1.580 NFs.**
- **Desde 01/2025 (pedido do Rafael): ≈ 1.152 NFs** (787 em 2025 + 365 em 2026).
- 100% partner = NACOM GOYA FB (j847 dedicado ao regime; zero venda a terceiros).
- Anomalia: **maio/2025 = só 2 NFs** (vs ~50-100/mês) — investigar (parada/troca de numeração).

---

## 3. 🔴 Restrição decisiva — LOCK DATES contábeis (medido)

| Empresa | fiscalyear / period / tax lock | Período ABERTO (corrigível na data original) |
|---|---|---|
| **FB** (company 1) | **2025-04-30** | a partir de **maio/2025** |
| **LF** (company 5) | **2025-12-31** | a partir de **janeiro/2026** |

**Consequência:** a maior parte do histórico está em **período fechado** (FB: 2024 + jan-abr/2025; LF: todo 2024-2025). Não dá para lançar/alterar na data original sem reabrir período (decisão da direção/Contadora — afeta SPED/balanços já entregues). ⇒ a regularização do grosso terá de ser **lançamento de ajuste em período ABERTO** (data corrente), referenciando o histórico.
**Abril/2026 (caso-piloto do item C) está ABERTO nos dois lados** → corrigível por lançamento direto.

---

## 4. Item B — opções de método de correção (PROPOSTA — exige decisão Contadora)

> A baixa das contas de controle precisa de **contrapartida**, que é **decisão contábil** (não inventar). No fluxo prospectivo a contrapartida é o PA (Ativo→Ativo); no **retroativo o PA já foi vendido/movido** → a contrapartida tem de ser definida (resultado de exercícios anteriores? ajuste de estoque? conta de equalização?).

| Modo | Como | Prós | Contras |
|---|---|---|---|
| **A — ajuste agregado por conta/período** | 1 lançamento de diário (account.move tipo `entry`) por empresa em período aberto: `D 5101020001 / C 5101010001` (+ contrapartida do double-count de estoque) pelos saldos acumulados | rápido; 2-4 lançamentos; reversível | menos rastreável NF-a-NF; precisa parear ATIVA×PASSIVA (assimetria) |
| **B — correção por documento (1 lançamento por NF)** | para cada uma das ~1.152 NFs, gerar a baixa que faltou | rastreável; é o que o item C testa | 1.152 escritas; maioria em período fechado (inviável na data original) |
| **C — híbrido** | per-documento só nos períodos ABERTOS (FB ≥ mai/2025; LF ≥ jan/2026); agregado para o fechado | rastreável onde dá; viável no fechado | dois mecanismos |

> **Double-count de estoque**: além da baixa contábil, há o estoque físico re-inflado (op 2027). Corrigir o ativo de estoque exige **ajuste de inventário/SVL** — decidir se entra na regularização ou é tratado à parte (Skill 1 / ajuste de quant).

---

## 5. Decisões pendentes (para Rafael / Contadora)
1. **Contrapartida da baixa retroativa** (a ATIVA/PASSIVA contra o quê, já que o PA foi consumido)? — decisão Contadora.
2. **Período fechado**: lançar ajuste agregado em data aberta, ou reabrir períodos? — direção/Contadora.
3. **Granularidade**: per-documento (Modo B/C) ou agregado (Modo A)?
4. **Double-count de estoque físico**: regularizar junto (ajuste de inventário) ou separado?
5. **Escrita do caso-piloto (item C, abril/2026)**: autorizar após dry-run + método definido.

---

---

## 6. ✅ Caso-piloto APLICADO E VALIDADO (item C, 2026-06-14)

Provada a viabilidade da **reversão pura per-documento** na NF `VND/2026/00234` (insumos R$ 1.927,44), via 2 lançamentos de ajuste reversíveis (`account.move` tipo `entry`, journal DIVERSOS), datas em período aberto. Script: `scripts/g9_05_corrigir_caso.py` (dry-run default + `--confirmar`).

| Lançamento | Débito | Crédito | Efeito medido |
|---|---|---|---|
| **LF** `DIV/2026/04/0003` (791839) | `5101020001` PASSIVA 1.927,44 | `1120100001` CLIENTES 1.927,44 | PASSIVA baixou +1.927,44; recebível **2.798,95 → 871,51** (= pagável FB; `payment_state=partial`) |
| **FB** `DIV/2026/04/0016` (791841) | `3201000001` CPV 1.927,44 | `5101010001` ATIVA 1.927,44 | ATIVA FB **61.930.965,26 → 61.929.037,82** (−1.927,44); custo reconhecido no resultado |

**Self-audit:** deltas exatos (±1.927,44), ambos balanceados, conciliação parcial OK, **reversível** (estornar os 2 entries desfaz). ✅

## 7. Levantamento completo do universo (item 2) — `g9_universo_desde_2025.csv`

**1.152 NFs de retorno desde 01/2025 · R$ 32.314.729,70 de insumos a regularizar** (script `scripts/g9_07_levantamento_universo.py`).

| Ano | NFs | Insumos 5902 |
|---|---:|---:|
| 2025 | 787 | R$ 22.935.502,79 |
| 2026 | 365 | R$ 9.379.226,91 |

**Por status de período (define o mecanismo de correção por perna):**

| Perna | ABERTO (per-documento direto) | FECHADO (ajuste agregado / reabrir período) |
|---|---|---|
| **LF — baixa PASSIVA** | 365 NFs · R$ 9,38M (2026) | 787 NFs · R$ 22,94M (2025) |
| **FB — baixa ATIVA** | 898 NFs · R$ 24,35M (≥mai/2025) | 254 NFs · R$ 7,96M (jan-abr/2025) |

> NFs sem entrada FB localizada pela chave: **6/1.152** (0,5% — investigar à parte). CSV tem 1 linha por NF: `lf_move_id, lf_nome, data, valor_insumos_5902, chave, fb_move_id, fb_nome, fb_periodo, lf_periodo`.

## 8. Plano de rollout (item B — refinado pós-teste)

1. **Períodos ABERTOS** (LF: 2026 · FB: ≥mai/2025): **per-documento** via `g9_05` parametrizado (loop sobre o CSV) — mecânica já provada. Dry-run em lote → amostra → go → execução em lote idempotente (REF por NF).
2. **Períodos FECHADOS** (LF: 2025 · FB: jan-abr/2025): **lançamento de ajuste AGREGADO** por conta/empresa em data corrente (somando os valores do CSV) — pois não dá para lançar na data original sem reabrir período.
3. **🔴 Aval da Contadora OBRIGATÓRIO antes do rollout**: a perna FB joga o custo em **resultado (CPV)** — no agregado (~R$32M+ desde 01/2025; R$62M incluindo 2024) há **impacto fiscal material** (IRPJ/CSLL / SPED já entregue). O teste prova a técnica; a Contadora decide método para o fechado + impacto fiscal (Pergunta 4 dela).
4. **Double-count físico de estoque**: tratar à parte (não materializou no caso testado; medir incidência real nos demais via SVL antes de incluir).
5. **A partir de já**: ligar o fluxo prospectivo correto (2 NFs / op 3252) para **parar de gerar novos casos** — senão o passivo continua crescendo (~R$1,5-2M/mês).

---

## Fontes

- **Odoo PROD** (READ-only, uid 42, 2026-06-14) — saldos de contas de controle, NFs de retorno (j847), lock dates, recebíveis, quants/SVL.
- `scripts/g9_03_transitorias_e_stock.py`, `scripts/g9_04_caso_detalhe_correcao.py` — leituras de saldo das transitórias + double-count físico.
- `scripts/g9_07_levantamento_universo.py` → `g9_universo_desde_2025.csv` — universo de 1.152 NFs desde 01/2025.
- `scripts/g9_05_corrigir_caso.py` (caso-piloto) e `scripts/g9_09_rollout_abril2026.py` (rollout abr/2026) — correção WRITE (dry-run default, `--confirmar`).
- `SOT_OPERACOES.md` — fluxo prospectivo (contas/operações corretas) referenciado nas tabelas EM USO × CORRETO.

## Contexto
Documento — industrialização por encomenda FB↔LF. Tema: regularização histórica (G9) — evidências e dimensionamento.
