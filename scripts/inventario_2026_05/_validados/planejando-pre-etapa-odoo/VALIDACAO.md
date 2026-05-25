# Validacao Skill 6 — `planejando-pre-etapa-odoo`

Arquivados em 2026-05-24 v6 apos capinagem da Skill 6 (planner D007 da pre-etapa CD/FB).

**Skill canonica**: [`.claude/skills/planejando-pre-etapa-odoo/SKILL.md`](../../../.claude/skills/planejando-pre-etapa-odoo/SKILL.md)
**Service capinado**: [`app/odoo/estoque/scripts/pre_etapa.py`](../../../app/odoo/estoque/scripts/pre_etapa.py) (`PreEtapaEstoqueService` + 4 helpers I/O top-level)
**Shim legacy**: [`app/odoo/services/pre_etapa_estoque_service.py`](../../../app/odoo/services/pre_etapa_estoque_service.py) (re-exporta tudo de `estoque/scripts/`)
**Spec D007**: [`docs/inventario-2026-05/00-decisoes/D007-pre-etapa-cd-fb-minimizar-nf.md`](../../../docs/inventario-2026-05/00-decisoes/D007-pre-etapa-cd-fb-minimizar-nf.md)

---

## Scripts SUPERADOS

| Script (arquivado aqui) | Mapeamento na Skill 6 | Validacao |
|---|---|---|
| `03b_planejar_pre_etapa_cd.py` | Modo `planejar` (READ Odoo + grava JSON+Excel) — helper `planejar_pre_etapa_batch_company` + `enriquecer_quants_para_planejar` + `gerar_excel_plano_pre_etapa` + `_serializar_plano_em_dicts` | Service `PreEtapaEstoqueService.planejar()` (13 testes pytest originais preservados via shim) + 6 testes pytest novos cobrindo helpers I/O (enriquecer basic+vazio, batch outliers+cods_filter, hash determinismo+sensibilidade). Smoke CLI: `--modo planejar` com inputs vazios sintéticos retorna `DRY_RUN_OK_PLANEJADO exit 4` em 15ms. Sem inputs: `FALHA_INPUT_AUSENTE exit 1`. |
| `04b_propor_pre_etapa_cd.py` | Modos `propor`/`listar-onda`/`aprovar-onda` (WRITE+READ banco local com hash sha256) — helpers `propor_ajustes_pre_etapa` + `listar_onda_pre_etapa` + `aprovar_onda_pre_etapa` + `_calcular_hash_onda` + `_fazer_backup_pg_dump` (opcional) | `_calcular_hash_onda` testado via pytest (determinismo + sensibilidade a campos críticos). `aprovar-onda` sem --hash retorna `FALHA_USO exit 2` (smoke CLI). Workflow propor/listar/aprovar em PG local requer tabela migrada — coberto em sessao futura quando demanda surgir. |

## Scripts NÃO arquivados (permanecem VIVOS — operação viva)

| Script | Razao | Caminho |
|---|---|---|
| `09b_executar_pre_etapa.py` | Executor C3 macro — composição de Skills 1 (POSITIVO_PURO) + 2 (TRANSF_INTERNA_POS/NEG). NÃO é átomo da Skill 6. Capinagem para `app/odoo/estoque/orchestrators/pre_etapa_executor.py` em sessão futura quando demanda. | [`scripts/inventario_2026_05/09b_executar_pre_etapa.py`](../09b_executar_pre_etapa.py) |
| `04_propor_ajustes.py` | Cobre Ondas 1-4 (fora do escopo D007). Skill 6 cobre apenas Onda 5 (CD) + Onda 6 (FB futura). | [`scripts/inventario_2026_05/04_propor_ajustes.py`](../04_propor_ajustes.py) |

---

## Mudanças aplicadas nos arquivados

1. **sys.path corrigido** `parents[2]` → `parents[4]` (museum vivo em `_validados/<skill>/` em vez de `inventario_2026_05/`).
2. **Header de ARQUIVADO** adicionado no docstring com aviso + receita Skill 6 + ponteiros para spec.

## Smoke test museum vivo (validacao C9)

```bash
python -c "
import importlib.util
for path in [
    'scripts/inventario_2026_05/_validados/planejando-pre-etapa-odoo/03b_planejar_pre_etapa_cd.py',
    'scripts/inventario_2026_05/_validados/planejando-pre-etapa-odoo/04b_propor_pre_etapa_cd.py',
]:
    spec = importlib.util.spec_from_file_location('arq', path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    print(f'OK {path}')
"
# → OK museum 03b imports
# → OK museum 04b imports
```

---

## Status checkpoints C7-C10

- **C7 ✅**: subagente `gestor-estoque-odoo` (description + skills lista + header v5→v6 + árvore galho 4 NOVO), ROUTING_SKILLS (47→48 invocaveis + 15→16 Skills Odoo + galho 6 ESTOQUE WRITE), tool_skill_mapper (`'planejando-pre-etapa-odoo': 'Estoque Odoo (Write)'`), CLAUDE.md módulo §6 catálogo + header status.
- **C8 ✅**: [fluxo 4.1](../../../app/odoo/estoque/fluxos/4.1-pre-etapa-cd-d007.md) com 4 sub-casos a/b/c/d cobrindo preview, re-aprovar, Onda 6 FB futura, subset cods.
- **C9 ✅**: 03b + 04b arquivados aqui; 09b permanece VIVO.
- **C10 ✅**: MAPA_SCRIPTS atualizado seção `pre_etapa.py` + ROADMAP_SKILLS §SKILL 6 → 🟡 mín viável.

## Cobertura de testes

| Tipo | Count | Localizacao |
|---|---|---|
| Pytest originais (algoritmo planejar 1-produto) preservados via shim | 13 | `tests/odoo/services/test_pre_etapa_estoque_service.py` (testes 1-13) |
| Pytest novos (helpers I/O — enriquecer/batch_company/hash) | 6 | `tests/odoo/services/test_pre_etapa_estoque_service.py` (testes 14-19) |
| Smokes CLI (3 cenários) | 3 | `/tmp/log_skill6_C6_validacao_dry_run.json` |
| **TOTAL** | **22** | (19 pytest + 3 CLI smokes) |
