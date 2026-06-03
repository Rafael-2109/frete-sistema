<!-- doc:meta
tipo: reference
camada: L3
sot_de: —
hub: docs/inventario-2026-05/consolidacao/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# Mineração Skill 2 — `transferindo-interno-odoo` (2026-05-24)

> **Papel:** Mineração Skill 2 — `transferindo-interno-odoo` (2026-05-24).

## Indice

- [Scripts lidos por Claude Code (9 — leitura integral)](#scripts-lidos-por-claude-code-9-leitura-integral)
  - [Service existente + base genérica + caso novo do main](#service-existente-base-genérica-caso-novo-do-main)
  - [Padrões de transferência (4)](#padrões-de-transferência-4)
  - [Casos especiais (4)](#casos-especiais-4)
  - [Operação massiva (1)](#operação-massiva-1)
- [Scripts minerados por subagente Explore (7 — síntese)](#scripts-minerados-por-subagente-explore-7-síntese)
  - [1. `15_transferir_preprod_para_estoque_fb.py`](#1-15_transferir_preprod_para_estoque_fbpy)
  - [2. `17_transferir_preprod_lf_para_estoque.py`](#2-17_transferir_preprod_lf_para_estoquepy)
  - [3. `substituir_lote_205030410_fb.py`](#3-substituir_lote_205030410_fbpy)
  - [4. `relotar_migracao_para_lotes_fb.py`](#4-relotar_migracao_para_lotes_fbpy)
  - [5. `transferir_fluxo_c.py`](#5-transferir_fluxo_cpy)
  - [6. `transferir_indisp_para_estoque_p15_cd.py`](#6-transferir_indisp_para_estoque_p15_cdpy)
  - [7. `executar_fluxo_b_vivas.py`](#7-executar_fluxo_b_vivaspy)
- [Síntese cross-arquivo (16 scripts agregados)](#síntese-cross-arquivo-16-scripts-agregados)
  - [Padrões repetidos (convergem em 14+/18 scripts)](#padrões-repetidos-convergem-em-1418-scripts)
  - [Bugs convergentes (G-TRANSFER-01)](#bugs-convergentes-g-transfer-01)
  - [Átomos finais (Skill 2)](#átomos-finais-skill-2)
  - [O que NÃO é coberto pela Skill 2 atomica (vira fluxo composto futuro)](#o-que-não-é-coberto-pela-skill-2-atomica-vira-fluxo-composto-futuro)

> Registro consolidado da mineração C1 realizada em 2026-05-24 v2 (Skill 2 maturando). 9 scripts lidos integral por Claude Code + 7 scripts minerados por subagente Explore (sonnet, ~120s) + 2 do main. Total: 18 scripts.

**Por que esse arquivo existe**: a resposta do subagente Explore só existe no transcript da sessão original. Ao limpar o contexto, perde-se. Este arquivo persiste os findings críticos para futuras consultas (próximas sessões, fluxos compostos D010/D012/D013).

---

## Scripts lidos por Claude Code (9 — leitura integral)

### Service existente + base genérica + caso novo do main

| Script | Função | Decisão arquitetural derivada |
|---|---|---|
| `app/odoo/services/stock_internal_transfer_service.py` (303 L) | service v1 com `transferir_entre_lotes`/`transferir_quantidade_para_lote`/`buscar_quant`/`listar_quants` | preservar v1 (12 testes existentes); adicionar v2 ao lado |
| `scripts/inventario_2026_05/transferir_lote.py` (522 L) | orquestrador NET-ZERO multi-empresa (LF/FB/CD), planilha `diff_qtd`, USA `ajustar_quant` da Skill 1 | confirma tese arquitetural: composição de `ajustar_quant`×2 |
| `scripts/inventario_2026_05/consolidar_lote_104000015_sal_fb.py` (220 L) | hardcoded 2 grafias '027-098/26' / 'MI 027-098/26' + Op3 inter-local FB/Estoque → Linha Salmoura | mostrou padrão MODO B (loc→loc mesmo lote) + caso multi-grafia |

### Padrões de transferência (4)

| Script | Pattern | Status |
|---|---|---|
| `10_executar_emergenciais_fb.py` (269 L) | A — 10 casos hardcoded MIGRAÇÃO→canônico, FB/Estoque | EVAL — **SUPERADO 2026-05-24** |
| `13_transferencia_migracao_fb.py` (394 L) | A — planilha 446 linhas MIGRAÇÃO→canônico, FB only, saldo cumulativo no run | EVAL (orquestrador VIVO) |
| `15_transferencia_para_migracao.py` (677 L) | A inversa — planilha 4.888 linhas FB+CD, D010 sinal, retry+sharding+clamp_parcial | EVAL (orquestrador VIVO) |
| `15r_transferencia_reversa.py` (581 L) | A — MIGRAÇÃO→lote (D010 inversa), `--criar-lote-migracao` com saldo negativo permitido | EVAL (orquestrador VIVO) |

### Casos especiais (4)

| Script | Pattern | Status |
|---|---|---|
| `padronizar_migracao.py` (242 L) | A — 1 caso hardcoded; 2 lot_ids específicos (56534 → 30400) + UPDATEs DB local | EVAL — **SUPERADO 2026-05-24** (com limitação `--lot-id` documentada) |
| `recuperar_aumentos_falhos.py` (175 L) | só aumento de log de falha; **gotcha G021 lot_id empresa errada** | EVAL — pertence à Skill 1, não Skill 2 |
| `transferir_local_pasta22.py` (375 L) | A wildcard D013 De-Local+Lote→Para-Local+Lote; **3 premissas: qty BRUTA (reset reserva), P-15/05 = literal+sem-lote, todos locais internos** | EVAL (orquestrador VIVO) |
| `ajuste_fb_cd_indisponivel.py` (554 L) | A wildcard D013 + checkpoint incremental (cada 100 linhas) + retry; **MIGRAÇÃO consolidador G022 maior saldo na loc** | EVAL (orquestrador VIVO) |

### Operação massiva (1)

| Script | Pattern | Status |
|---|---|---|
| `mover_migracao_para_indisponivel.py` (509 L) | 3 filiais: FB/CD = B (loc→loc) + LF = A; **CSV separado de pulados** (quants com reserved>0) | EVAL (orquestrador VIVO) |

---

## Scripts minerados por subagente Explore (7 — síntese)

> Subagente Explore (sonnet) leu os 7 scripts em paralelo (~120s). Síntese consolidada abaixo. Findings detalhados estavam só na resposta do subagente — NÃO foram salvos em `/tmp/` (limitação do subagente READ-only).

### 1. `15_transferir_preprod_para_estoque_fb.py`

- **Tipo**: B (loc→loc mesmo lote — sub-locais Pré-Produção → FB/Estoque, single-empresa parametrizável)
- **Mecânica**: `odoo.write({'inventory_quantity': X})` + `action_apply_inventory` em 2 passos. NÃO usa StockInternalTransferService.
- **Lógica única**: opera saldo LIVRE = `quantity - reserved_quantity`; nunca toca reserva; destino criado se não existe.
- **Status**: EVAL — generalizado 2026-05-20; gera log JSON.

### 2. `17_transferir_preprod_lf_para_estoque.py`

- **Tipo**: B (clone do 15 para LF)
- **Diferença**: filtra por `--xlsx` (coluna `cod`) em vez de `--lot-source-log` do 15
- **Conclusão crítica**: 15+17 devem ser fundidos em átomo único com `--company`/`--estoque`/`--locs` + escolha de filtro (lot-log vs xlsx vs nenhum) — confirma decisão de criar `transferir_entre_locations`.

### 3. `substituir_lote_205030410_fb.py`

- **Tipo**: A + pre/post Skill 2.4 (unreserve → transfer → reassign)
- **Mecânica**: usa `StockInternalTransferService.transferir_entre_lotes`; chama `_do_unreserve` (privado) ANTES e `_action_assign` DEPOIS via `execute_kw`
- **Lógica única**: **3 etapas obrigatórias** (1) `_do_unreserve` em moves reservados → verificar reserva zerou → (2) transfer → (3) `_action_assign` no novo lote
- **Gotcha**: lote destino prefix canônico diferente (`'ME '` em vez de `'MI '`) — documentado explicitamente
- **Status**: EVAL — ensina padrão composto cross-skill

### 4. `relotar_migracao_para_lotes_fb.py`

- **Tipo**: A + B em 2 etapas SEQUENCIAIS (`--etapa relotar` → `--etapa enviar-estoque`)
- **Gotcha-1**: `LOTE_MIGRACAO_VARIANTES = ['MIGRAÇÃO', 'MIGRACAO', 'MIGRAÇAO']` wildcard das 3 grafias → confirmou G022
- **Gotcha-2**: NÃO é idempotente (`--etapa` separadas + ITENS hardcoded)
- **`_clamp()` com TOL=0.001**: qty acima do livre por menos que TOL = clamp silencioso; acima de TOL = SEM_SALDO
- **Status**: EVAL

### 5. `transferir_fluxo_c.py`

- **Tipo**: A multi-quant origem; lê move_lines de 2 pickings de devolução; transfere FB/Estoque → FB/Indisponível/MIGRAÇÃO
- **🚨 BUG (G-TRANSFER-01)**: `lot_dest = lot_svc.buscar_por_nome(...) or lot_svc.criar_se_nao_existe(...)` — `criar_se_nao_existe` retorna `(id, bool)` tuple, mas `dq` query usa `lot_dest` como int → bug
- **Outros gotchas**: clamp simples `mov = min(qty, livre)`; multi-quant loop até consumir restante; sem log JSON (risco em produção)
- **Status**: **COM-BUG** — a Skill 2 faz o CERTO (divergência = melhoria, não falha)

### 6. `transferir_indisp_para_estoque_p15_cd.py`

- **Tipo**: B inter-local (CD/Indisponível MIGRAÇÃO → CD/Estoque P-15/05) + criar lote P-15/05
- **Lógica única**: guard de sanidade verifica `quant_origem_id` esperado bate com atual (warning); hard-fail em saldo insuficiente (NÃO clamp, diferente do relotar); documenta explicitamente "Picking interno NÃO usado" (escolha intencional)
- **Status**: EVAL — padrão mais robusto (log JSON, guard de ID, hard-fail)

### 7. `executar_fluxo_b_vivas.py`

- **Tipo**: A passo 3 (passos 1+2 = outras skills); fluxo COMPOSTO 3-passos por NF: (1) cancelar invoice + (2) devolver picking + (3) transferir
- **`--so-passo {1,2,3}`**: permite execução parcial (checkpoint de fluxo composto)
- **Idempotência parcial**: devolução verificada antes de criar, mas transfer não
- **🚨 BUG (G-TRANSFER-01)**: mesmo bug do fluxo_c em `lot_svc.criar_se_nao_existe()` retornando tuple
- **`LOTE_VAZIO = 'P-15/05'`**: proxy explícito para "sem lote" (G_proxy_vazio confirmado)
- **`sleep(1)`** entre NFs em modo real
- **Trata `cannot marshal None`** como exceção aceitável (bug Odoo CIEL IT em `button_validate`)
- **Status**: **COM-BUG** — passo 3 vira átomo da Skill 2; passos 1+2 pertencem a `operando-picking-odoo` + `faturando-odoo`

---

## Síntese cross-arquivo (16 scripts agregados)

### Padrões repetidos (convergem em 14+/18 scripts)

1. **Mecânica única**: TODOS usam `write({inventory_quantity: X})` + `action_apply_inventory` em 2 passos por quant (reduz origem, aumenta/cria destino). Nenhum usa picking interno.
2. **Saldo livre**: TODOS operam `livre = quantity - reserved_quantity`; nunca tocam reserva (default).
3. **Create-or-update destino**: TODOS têm a mesma lógica `buscar_quant → update se existe, create+apply se não`.
4. **`--dry-run`/`--confirmar`**: 100% dos 18 scripts.
5. **Variantes MIGRAÇÃO**: 7/18 scripts lidam com lote MIGRAÇÃO em múltiplas grafias → confirma G022.

### Bugs convergentes (G-TRANSFER-01)

`criar_se_nao_existe` retorna `(id, bool)` mas `transferir_fluxo_c` e `executar_fluxo_b_vivas` usam como `id` puro → **bug em 2/18 scripts**. A Skill 2 nunca replica esse bug — `resolver_lote_destino` desempacota corretamente.

### Átomos finais (Skill 2)

Cobertura via `transferir_entre_lotes_v2` (lote→lote) + `transferir_entre_locations` (loc→loc) + composição cross-skill com 2.4 (unreserve→transfer→reassign):

| Átomo | Cobre scripts |
|-------|--------------|
| `transferir_entre_lotes_v2` (A) | 10, 13, 15, 15r, transferir_lote (orq), padronizar (com limitação), 15_preprod, 17_preprod, transferir_indisp_p15_cd (parte) |
| `transferir_entre_locations` (B) | mover_migracao (FB/CD), consolidar_lote_104k15 (Op3), transferir_indisp_p15_cd (parte), preprod scripts |
| Composição cross-skill (2.4 + 2 + 2.4) | substituir_lote_205030410 |
| Multi-quant origem (loop A) | fluxo_c, fluxo_b (passo 3), 15/15r wildcard |
| Recuperação pós-falha (só aumento) | recuperar_aumentos_falhos (pertence à Skill 1) |

### O que NÃO é coberto pela Skill 2 atomica (vira fluxo composto futuro)

- **Orquestração de planilha** (lê XLSX, normaliza schema, retry, sharding, checkpoint incremental, multi-quant origem com clamp parcial, semânticas D010/D012/D013, wildcard locations)
- **Fluxos compostos cross-skill** (`substituir_lote`: 2.4 unreserve → 2 transfer → 2.4 reassign; `executar_fluxo_b_vivas`: cancel invoice + return picking + transfer)
- **CSV de pulados** (`mover_migracao` separa quants com reserved>0 em CSV separado para tratamento posterior)
- **Sleep+retry específicos** (`fluxo_b_vivas` sleep 1s entre NFs em modo real)

Esses orquestradores permanecem **VIVOS** em `scripts/inventario_2026_05/` até cada padrão se repetir com 2+ casos reais (regra `feedback-skills-demanda-driven`).
