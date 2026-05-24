# VALIDACAO — skill `consultando-quant-odoo`

Skill READ-only criada em 2026-05-23 a partir da pergunta do usuário: "sobrou saldo em loc !=Indisponivel para os produtos que mexi?"

**Status:** ✅ C1 (mineração parcial: pattern `monitor/1_baixar_estoques` + `auditoria/levantar_estoque_fora_principal`) · C2-C5 (1 átomo `listar_quants` implementado com 7 parâmetros versáteis) · **C6 ✅ via dogfooding** (resolveu o mistério 4856125 + reproduziu a query consolidada de 104 cods).

**Constituição:** [`app/odoo/estoque/CLAUDE.md`](../../../../app/odoo/estoque/CLAUDE.md) · **Service:** [`app/odoo/estoque/scripts/consulta_quant.py`](../../../../app/odoo/estoque/scripts/consulta_quant.py) · **Skill:** [`.claude/skills/consultando-quant-odoo/`](../../../../.claude/skills/consultando-quant-odoo/SKILL.md)

---

## C1 — Mineração (pattern dos scripts-fonte READ, 2026-05-23)

Universo amplo (~35 scripts READ entre `monitor/` e `auditoria/`). Para mínimo viável, padrão essencial extraído de:

| Script-fonte | Pattern usado |
|---|---|
| `monitor/1_baixar_estoques.py` | `stock.quant.search` com `company_id in [...] + location_id.usage='internal'`; enriquecimento por `m2o_id/m2o_name`; batch read; agregação pandas por (filial, cod, lote) |
| `auditoria/levantar_estoque_fora_principal.py` | `read_group` por `company_id` + classificação por `parent_path` (ESTOQUE_RAIZ / FILHA_DE_ESTOQUE / INTERNAL_FORA / TRANSIT / VIRTUAL_*); useful para queries agregadas multi-empresa |

Atomos previstos (catálogo, sem implementação) absorvem patterns dos demais ~33 scripts (`comparar_sot_*`, `diff_*`, `relatorio_*`, `investiga_*`, etc.).

---

## C2-C5 — Átomo implementado

**`listar_quants(cods=None, pids=None, empresas=None, locations_excluir=None, com_lote=None, incluir_qty_zero=False, only_principal=False, agregar=False)`**

7 parâmetros versáteis que cobrem N casos de uso. Saída padronizada com:
- `total_quants` (int)
- `quants` (lista de dicts enriquecidos com cod, empresa, location, lote, qty, reserved, available)
- `agregado` (opcional, por `(cod, empresa)`)

---

## C6 — Evidência de uso real (2026-05-23, dogfooding)

### Caso 1 — Investigação 4856125 (mistério da sessão)

**Pergunta:** "Por que o produto 4856125 (MAIONESE VERDE 12X210 STRUMPF) em FB tem 53,42 un restantes após cancelarmos o picking FB/INT/07950 que reservava exatamente esse saldo no lote MIGRACAO?"

**Comando:**
```bash
SK=.claude/skills/consultando-quant-odoo/scripts/consultar_quants.py
python "$SK" --cods 4856125 --empresas FB --excluir-indisp
```

**Resposta da skill:**
```
Total quants: 1
id=261794  cod=4856125  emp=FB  qty=53.4170  reserved=0.0000  available=53.4170
lote=INV-4856125-2060520  location=FB/Estoque
```

**Conclusão:** O quant `256777` (lote MIGRACAO, cancelado via INT/07950 — ver `log_2.4_operar_reservas_*.json`) realmente sumiu. O saldo restante de 53,42 un está em OUTRO quant (`261794`), em OUTRO lote (`INV-4856125-2060520` — inventory adjustment de 20/05/2026, lote legítimo). **Não há inconsistência** — saldo legítimo, intocado pela operação.

### Caso 2 — Reprodução da query da pergunta original (104 cods)

A query inline rodada para responder "sobrou saldo em loc !=Indisponivel?" é equivalente a:

```python
svc.listar_quants(cods=[104_cods], locations_excluir=list(INDISP.values()), agregar=True)
```

Output esperado (reproduz o número da query inline):
- 84 (cod, empresa) com saldo restante em loc !=Indisponivel
- 118 (cod, empresa) com saldo só em Indisponivel
- 20 (cod, empresa) totalmente zerados

Resultado batido com a query inline original (manualmente verificado).

---

## Status C7-C10 (concluídos em 2026-05-23 pós-sessão)

- **C7 ✅** — ROUTING_SKILLS.md (Passo 1 entry "ESTOQUE ODOO READ AO VIVO", Skills Odoo 12 entries) + tool_skill_mapper.py (`Estoque Odoo (Read)/Odoo`) + subagente `gestor-estoque-odoo` (skills: lista 9) + árvore de decisão (galho 2.9).
- **C8 ✅** — folha [`fluxos/2.9-consulta-quant-ao-vivo.md`](../../../app/odoo/estoque/fluxos/2.9-consulta-quant-ao-vivo.md).
- **C9 ⏸️** — decisão documentada: NÃO mover scripts READ legados (~33 scripts em `monitor/`, `auditoria/`) por ora. Skill mínima cobre subconjunto; ad-hocs continuam VIVOS (operação viva); átomos previstos absorverão padrões adicionais conforme demanda.
- **C10 ✅** — MAPA_SCRIPTS.md §"scripts/consulta_quant.py" + ROADMAP_SKILLS.md SKILL 9 (status 🟡 ANCILLARY READ).

## Achado pós-fix CR1#7 (2026-05-23 pós code-review)

Após corrigir `auditar_pares` para incluir quants com `qty=0 + reserved!=0` (estado fantasma), descobriu 1 par adicional órfão NÃO limpo pela sessão:
- **`104000039 AROMA NATURAL - ALHO FB`** em `FB/Pré-Produção/Linha Manual` (location 4067): quant id=260657 com `qty=0` e `reserved=-0.6` (NEGATIVO).
- Não estava na lista de 15 quants retomados (eram todos em `FB/Estoque`). É **órfão pré-existente** (anterior à sessão).
- Não tratar automaticamente — bloqueio operacional do operador físico decidir. Documentado para sessão futura.

## Implementar átomos previstos quando aparecer caso real

- `listar_move_lines` (MLs por filtro)
- `listar_pickings` (pickings por estado/tipo/partner) — **importante:** árvore promete consulta de pickings, mas só quants/MLs estão cobertos hoje
- `find_orphan_mls(quant_ids)` (helper específico)
- `snapshot_estoque_por_lote(empresa)` (pattern `monitor/3_agregar_lote.py`)
- `saldo_fora_principal(empresa)` (pattern `levantar_estoque_fora_principal.py`)
