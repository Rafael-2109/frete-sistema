---
name: consultando-quant-odoo
description: >-
  Skill READ-only (3 átomos versáteis em 3 modos CLI) para CONSULTAR stock.quant
  + cross-ref reverso ML→quant + pickings reservando quants no Odoo AO VIVO
  (não no DB local sincronizado). MODOS: `--modo quants` (default, clássico),
  `--modo move-lines` (NOVO v7, cross-ref reverso via tupla — G030),
  `--modo pickings` (NOVO v7, agrupa MLs por picking com metadados — pré-cond
  inviolável de Skill 2 transferência). Usar quando o pedido é "qual o saldo
  restante do produto X em empresa Y?", "tem saldo em loc !=Indisponivel?",
  "quais quants em lote MIGRACAO?", "saldo total por produto+empresa",
  "auditoria pós-ajuste de inventário", "snapshot ao vivo do estoque",
  ou (NOVO v7) "quais pickings estão reservando o quant X?" (fluxo 2.6),
  "quais MLs apontam para esse quant?".
  NÃO USAR PARA:
  - consulta no DB local (sincronizado) -> consultando-sql
  - rastrear NF/PO/SO específico -> rastreando-odoo
  - explorar modelo Odoo desconhecido -> descobrindo-odoo-estrutura
  - análise agregada de ruptura/projeção -> Subagente gestor-estoque-producao
  - operar (WRITE) quants -> ajustando-quant-odoo
  - operar reservas (WRITE) -> operando-reservas-odoo
  - localizar MLs órfãs específicas (qty=0) -> Skill 2.4 `--find-orphan`
allowed-tools: Read, Bash, Glob, Grep
---

# consultando-quant-odoo (READ-only — 3 átomos de consulta ao vivo)

Skill **mínimo viável** (C1 mineração parcial · C2-C5 implementado para 3 átomos · C6-C10 conforme uso). Construída em 2026-05-23, estendida em 2026-05-24 v7 com 2 modos cross-ref reverso.

Constituição: `app/odoo/estoque/CLAUDE.md`. Service: `app/odoo/estoque/scripts/consulta_quant.py`.

---

## Contrato — átomo 1: listar_quants (modo `quants`, default)

```
objeto:        stock.quant (READ-only, sem escrita)
input:         filtros versáteis (cods, empresas, locations_excluir,
                                  com_lote, only_principal, agregar)
output (JSON): {total_quants, quants:[...], agregado:{(cod,empresa):{...}}}
pré-condições: pids OU cods (resolvidos auto); empresas ⊆ {FB,CD,LF}
pós-condições: nenhuma (read-only)
gotchas-invariante: filtra qty!=0 por default; trata company_id multi-empresa;
                    enriquece com cod/produto/lote/location names
modos:         READ apenas (sem --dry-run/--confirmar)
status:        sempre OK (read não falha — pode retornar vazio)
```

## Contrato — átomo 2: listar_move_lines_por_quant (modo `move-lines`, NOVO v7)

```
objeto:        stock.move.line (READ-only, cross-ref reverso a partir de quants)
input:         --quant-ids <Q1,Q2,...> [--states <csv>] [--incluir-move]
                 (states default = assigned,partially_available;
                  --states todos = sem filtro)
output (JSON): {total_mls, mls:[{id, quant_id (resolvido via tupla), pid,
                                 product_name, lot_id, lot_name,
                                 location_id, location_name,
                                 location_dest_id, location_dest_name,
                                 picking_id, picking_name, picking_state,
                                 move_id, production_id, production_name,
                                 quantity, state, company_id, empresa}]}
pré-condições: quant_ids não-vazio.
pós-condições: nenhuma (read-only).
gotchas-invariante: G030 — `quant_id` em stock.move.line é COMPUTED store:False;
                    filtro `quant_id in [...]` é IGNORADO pelo Odoo. Cross-ref
                    é via TUPLA (product_id, lot_id, location_id, company_id).
                    G024: usar `quantity`, não `reserved_uom_qty`.
modos:         READ apenas
status:        sempre OK
```

## Contrato — átomo 3: listar_pickings_por_quant (modo `pickings`, NOVO v7)

```
objeto:        stock.picking (READ-only, agrupa MLs por picking)
input:         --quant-ids <Q1,Q2,...> [--states <csv>]
output (JSON): {total_pickings, total_mls,
                pickings:[{id, name, state, origin, partner_id, partner_name,
                           picking_type_id, picking_type_name,
                           scheduled_date, create_date, company_id, empresa,
                           n_mls, qty_total, lotes_envolvidos,
                           produtos_envolvidos, mls:[...]}],
                mls_sem_picking:[...]}
pré-condições: quant_ids não-vazio.
pós-condições: nenhuma (read-only).
gotchas-invariante: ordena por state-priority (assigned > partial > confirmed
                    > waiting > done > cancel) + create_date. Reaproveita
                    listar_move_lines_por_quant internamente. Inclui
                    metadados ricos para caller classificar caminho A-E
                    do fluxo 2.6 sem RPCs extras.
modos:         READ apenas
status:        sempre OK
```

## Constantes (importadas do `_utils.py`)

| Símbolo | Valor | Significado |
|---|---|---|
| `INDISP` | `{1: 31088, 3: 31089, 4: 31090, 5: 31091}` | location_id Indisponivel por company |
| `PRINCIPAL` | `{1: 8, 4: 32, 5: 42}` | location_id principal por company |
| `EMP_TO_CID` | `{'FB': 1, 'CD': 4, 'LF': 5}` | mapeamento empresa → company_id |

## Receitas (caso real -> args)

| Preciso de... | Args | Comentário |
|---------------|------|------------|
| Saldo restante de N produtos em loc !=Indisponivel | `--cods c1,c2,... --excluir-indisp --agregar` | A pergunta original que motivou a skill |
| Onde estão saldos do produto X em FB? | `--cods X --empresas FB` | Lista quants ativos |
| Saldos em lote MIGRACAO em FB+CD | `--com-lote MIGRA --empresas FB,CD` | Identifica estoque fantasma |
| Saldo só na location principal | `--cods c1,c2 --only-principal` | Conferência "principal" |
| Snapshot agregado por (cod, empresa) | `--cods c1,c2,... --agregar` | Soma quants + lista lotes/locais |
| **Quais pickings reservam quants X,Y,Z?** (NOVO v7) | `--modo pickings --quant-ids X,Y,Z` | Pré-cond inviolável Skill 2 (fluxo 2.6) |
| **Quais MLs apontam para quants alvo?** (NOVO v7) | `--modo move-lines --quant-ids X,Y,Z` | Detalhe ML por ML antes de agrupar |
| MLs done historico apontando para quants | `--modo move-lines --quant-ids X --states done` | Auditoria histórica |

## Exemplos

```bash
SK=.claude/skills/consultando-quant-odoo/scripts/consultar_quants.py

# 1) Sobrou saldo dos 5 produtos em loc !=Indisponivel?
python "$SK" --cods 4856125,105000025,104000037 --excluir-indisp --agregar

# 2) Quants em lote MIGRACAO em FB
python "$SK" --com-lote MIGRA --empresas FB

# 3) Saldo só na principal (FB/Estoque, CD/Estoque, LF/Estoque)
python "$SK" --cods 4856125 --only-principal

# 4) NOVO v7: quais pickings estão reservando 3 quants do lote 13206?
python "$SK" --modo pickings --quant-ids 261590,261594,261598
# → 1 picking FB/INT/08022 (Transferências Internas), 3 MLs, 1035.083 un total

# 5) NOVO v7: detalhe ML por ML (sem agrupamento)
python "$SK" --modo move-lines --quant-ids 261590,261594,261598

# 6) NOVO v7: histórico done (auditoria)
python "$SK" --modo move-lines --quant-ids 229937 --states done
```

## Catálogo de átomos

| Átomo | Status | Notas |
|---|---|---|
| `listar_quants(cods, empresas, locations_excluir, com_lote, agregar, ...)` | ✅ | Modo `quants` (default) |
| `auditar_pares(pares_cod_empresa, ...)` | ✅ | Compõe 2x listar_quants (principais + indisp); helper Python |
| `listar_move_lines_por_quant(quant_ids, states, incluir_picking, incluir_move)` | ✅ **NOVO v7** | Modo `move-lines`. Cross-ref reverso via tupla G030 |
| `listar_pickings_por_quant(quant_ids, states)` | ✅ **NOVO v7** | Modo `pickings`. Reaproveita atomo 3, agrupa + metadados |
| `listar_pickings(states, picking_type_ids, partner_ids)` | ⬜ previsto | filtro INDEPENDENTE de quant_ids (sem demanda atual) |
| `snapshot_estoque_por_lote(empresa)` | ⬜ previsto | relatório agregado por lote |
| `saldo_fora_principal(empresa)` | ⬜ previsto | classifica INTERNAL_FORA vs ESTOQUE_RAIZ |

## Composição em FLUXOS

- **Pós-WRITE da skill 1 ou 2.4**: auditoria "sobrou saldo?" ou "MLs órfãs ainda existem?"
- **Pré-WRITE da skill 1**: validar saldo atual antes de ajustar (skill 1 já faz isso internamente, mas o usuário pode querer ver antes de invocar)
- **Diagnóstico cross-empresa**: "onde está o saldo total de X?" (com_lote, agregar)
- **Fluxo 2.6 — tratar reserva ATIVA pré-Skill 2** (NOVO v7, INVIOLÁVEL): antes de QUALQUER transferência (Skill 2 modo A/B/C), verificar `reserved > 0` via modo quants → se sim, identificar pickings via modo pickings → escolher caminho A-E (cancel/devolver/unreserve/outro_lote/cirurgia) → executar tratamento → re-checar → SOMENTE ENTÃO chamar Skill 2.

## Armadilhas

- **Não confundir com `consultando-sql`**: aquela é DB LOCAL sincronizado (pode estar desatualizado por minutos/horas). Esta é Odoo AO VIVO via XML-RPC (latência ~1-2s mas estado real).
- **Custo de N+1**: ao agregar muitos cods + empresas + listar todos quants, custo de XML-RPC cresce. Para milhares de cods, prefira `monitor/1_baixar_estoques.py` (batch CSV).
- **Filtro `incluir_qty_zero=False`**: default exclui quants vazios. Para auditar quants com `quantity=0` mas `reserved!=0` (MLs órfãs), passar `incluir_qty_zero=True`.
- **G030 — quant_id é UI-only** (NOVO v7): `stock.move.line.quant_id` é computed `store: False`. Filtros diretos via `('quant_id', 'in', [...])` são IGNORADOS pelo Odoo. Modos move-lines/pickings resolvem via tupla (product+lot+location+company) AUTOMATICAMENTE. Não tentar fazer query direta — usar a CLI.

## Validação

Construída e validada em 2026-05-23 ao responder a pergunta "para os 104 produtos ajustados hoje, sobrou saldo em loc !=Indisponivel?" — retornou 84 (cod, empresa) com saldo restante + 118 em Indisponivel + 20 totalmente zerados. **Estendida em v7 com 2 atomos cross-ref reverso** (validados em PROD via caso 71 cods). Ver [`_validados/consultando-quant-odoo/VALIDACAO.md`](../../../scripts/inventario_2026_05/_validados/consultando-quant-odoo/VALIDACAO.md) (CR2-L1 v7-fix).
