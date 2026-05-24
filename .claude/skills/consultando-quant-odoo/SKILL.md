---
name: consultando-quant-odoo
description: >-
  Skill READ-only (átomo) para CONSULTAR stock.quant no Odoo AO VIVO (não no DB
  local sincronizado). Usar quando o pedido é "qual o saldo restante do produto
  X em empresa Y?", "tem saldo em loc !=Indisponivel?", "quais quants em lote
  MIGRACAO?", "saldo total por produto+empresa", "auditoria pós-ajuste de
  inventário", "snapshot ao vivo do estoque".
  NÃO USAR PARA:
  - consulta no DB local (sincronizado) -> consultando-sql
  - rastrear NF/PO/SO específico -> rastreando-odoo
  - explorar modelo Odoo desconhecido -> descobrindo-odoo-estrutura
  - análise agregada de ruptura/projeção -> Subagente gestor-estoque-producao
  - operar (WRITE) quants -> ajustando-quant-odoo
  - operar reservas -> operando-reservas-odoo
allowed-tools: Read, Bash, Glob, Grep
---

# consultando-quant-odoo (READ-only — átomo de consulta ao vivo)

Skill **mínimo viável** (C1 mineração parcial · C2-C5 implementado para 1 átomo · C6-C10 conforme uso). Construída em 2026-05-23 a partir da demanda "auditoria pós-ajuste: sobrou saldo em loc !=Indisponivel para os produtos que mexi?".

Constituição: `app/odoo/estoque/CLAUDE.md`. Service: `app/odoo/estoque/scripts/consulta_quant.py`.

---

## Contrato

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
| Saldos em lote MIGRACAO em FB+CD | `--com-lote MIGRA --empresas FB,CD` | Identifica estoque fantasma (memória `estoque-fantasma-migracao-indisponivel`) |
| Saldo só na location principal (sem sub-locais) | `--cods c1,c2 --only-principal` | Útil para conferir saldo "principal" de cada quant |
| Snapshot agregado por (cod, empresa) | `--cods c1,c2,... --agregar` | Soma todos quants, lista lotes/locais |

## Exemplos

```bash
SK=.claude/skills/consultando-quant-odoo/scripts/consultar_quants.py

# 1) Sobrou saldo dos 5 produtos em loc !=Indisponivel?
python "$SK" --cods 4856125,105000025,104000037 --excluir-indisp --agregar

# 2) Quants em lote MIGRACAO em FB
python "$SK" --com-lote MIGRA --empresas FB

# 3) Saldo só na principal (FB/Estoque, CD/Estoque, LF/Estoque)
python "$SK" --cods 4856125 --only-principal
```

## Catálogo de átomos

| Átomo | Status | Quando implementar |
|---|---|---|
| `listar_quants(cods, empresas, locations_excluir, com_lote, agregar, ...)` | ✅ implementado | — |
| `listar_move_lines(quant_ids, picking_ids, mo_ids, states)` | ⬜ previsto | quando precisar consultar MLs por filtro |
| `listar_pickings(states, picking_type_ids, partner_ids)` | ⬜ previsto | quando precisar listar pickings por estado |
| `find_orphan_mls(quant_ids)` | ⬜ previsto | helper específico: MLs apontando para quants qty=0 |
| `snapshot_estoque_por_lote(empresa)` | ⬜ previsto | relatório agregado por lote (segue `monitor/3_agregar_lote.py`) |
| `saldo_fora_principal(empresa)` | ⬜ previsto | classifica INTERNAL_FORA vs ESTOQUE_RAIZ (segue `auditoria/levantar_estoque_fora_principal.py`) |

## Composição em FLUXOS

- **Pós-WRITE da skill 1 ou 2.4**: auditoria "sobrou saldo?" ou "MLs órfãs ainda existem?"
- **Pré-WRITE da skill 1**: validar saldo atual antes de ajustar (skill 1 já faz isso internamente, mas o usuário pode querer ver antes de invocar)
- **Diagnóstico cross-empresa**: "onde está o saldo total de X?" (com_lote, agregar)

## Armadilhas

- **Não confundir com `consultando-sql`**: aquela é DB LOCAL sincronizado (pode estar desatualizado por minutos/horas). Esta é Odoo AO VIVO via XML-RPC (latência ~1-2s mas estado real).
- **Custo de N+1**: ao agregar muitos cods + empresas + listar todos quants, custo de XML-RPC cresce. Para milhares de cods, prefira `monitor/1_baixar_estoques.py` (batch CSV).
- **Filtro `incluir_qty_zero=False`**: default exclui quants vazios. Para auditar quants com `quantity=0` mas `reserved!=0` (MLs órfãs), passar `incluir_qty_zero=True`.

## Validação

Construída e validada em 2026-05-23 ao responder a pergunta "para os 104 produtos ajustados hoje, sobrou saldo em loc !=Indisponivel?" — retornou 84 (cod, empresa) com saldo restante + 118 em Indisponivel + 20 totalmente zerados. Ver `_validados/consultando-quant-odoo/VALIDACAO.md` (a criar).
