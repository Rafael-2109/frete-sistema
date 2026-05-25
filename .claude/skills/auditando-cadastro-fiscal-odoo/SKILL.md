---
name: auditando-cadastro-fiscal-odoo
description: |
  Esta skill deve ser usada quando o usuario precisa fazer PRE-FLIGHT de auditoria
  de cadastro fiscal de produtos no Odoo ANTES de operacoes que tocam SEFAZ
  (faturamento inventario, transferencia inter-company, NF de inventario).
  Cobre G017 (NCM ausente), G018 (weight=0), G035 (barcode invalido GTIN),
  G014 (lote vencido com saldo) + D-OPS-2 (duplicacao em pipeline ativo) +
  D-OPS-3 (tracking='none' info). Perfil V1: 'inventario' (Skill 8 faturando-odoo).
  Roadmap perfis: 'venda-cliente' (V2), 'compras-importacao' (V3+).

  USAR QUANDO:
  - "audita cadastro fiscal do ciclo X"
  - "pre-flight para faturar onda Y"
  - "verifica NCM/barcode/weight dos cods Z"
  - "limpa barcodes invalidos antes de SEFAZ"
  - "tem duplicacao em pipeline ativo?"
  - Sub-skill delegada pela Skill 8 'faturando-odoo' (Skill 8 v15+ chama esta)

  NAO USAR QUANDO:
  - Apenas listar produtos por filtro generico -> usar consultando-sql
  - Operacoes WRITE de estoque (ajustar/transferir) -> Skills 1/2 estoque
  - Criar NF / lancamento Odoo -> Skill 8 faturando-odoo (v15+) ou
    integracao-odoo
  - Auditoria contabil/financeira -> auditor-financeiro
---

# auditando-cadastro-fiscal-odoo

## Contrato (skill C5 — perfil V1 'inventario')

- **objeto**: `product.product` + `l10n_br_ciel_it_account.ncm` +
              `stock.lot` (G014) + `AjusteEstoqueInventario` (D-OPS-2)
- **input**: 1 das 3 formas (mutuamente exclusivas):
  - `--produtos PID1,PID2,...` (ids do Odoo)
  - `--cods COD1,COD2,...` (default_code)
  - `--ciclo NOME_CICLO` (le AjusteEstoqueInventario do ciclo)
  - `--perfil inventario` (V1; futuro: `venda-cliente`)
  - `--auto-corrigir-barcode` (opcional — G035 fix automatico)
  - `--no-pipeline-check` (skip D-OPS-2)
  - `--no-lote-vencido-check` (skip G014)
- **output**: JSON estruturado em stdout (`status_global`, `pode_faturar`,
              `bloqueios`, `warnings`, `acoes_aplicadas`, `tempo_ms`)
- **pre-condicoes**: nenhuma; READ-only por default
- **pos-condicoes**: NENHUM ajuste de inventario tocado; opcional WRITE em
              `product.barcode` apenas com `--auto-corrigir-barcode` + `--confirmar`
- **gotchas-invariante (V1 inventario)**:
  - G017 (NCM)        — BLOQUEIO ('strict')
  - G018 (weight=0)   — WARN (fallback aplicado no picking F5b->F5c)
  - G035 (barcode)    — BLOQUEIO ou AUTO-FIX
  - G014 (lote venc.) — WARN (ETAPA B do faturamento resolve)
  - D-OPS-2 (duplicacao pipeline) — BLOQUEIO
  - D-OPS-3 (tracking='none') — INFO (apos fix Skill 2 v14b nao bloqueia)
- **modos**: `--dry-run` (default — NAO escreve) -> `--confirmar` (so'
              autoriza WRITE de barcode se `--auto-corrigir-barcode` flag set)

## Quando invocar

### Pelo agente web / Claude Code (auto-invocacao)

Trigger keywords:
- "audita cadastro fiscal"
- "pre-flight"
- "valida NCM"
- "limpa barcode invalido"
- "checa duplicacao pipeline"
- "tem lote vencido em..."

### Pela Skill 8 `faturando-odoo` (v15+ — subprocess)

Skill 8 chama esta antes de iniciar bulk. Se `pode_faturar=False`, aborta
com mensagem clara. Se `pode_faturar=True`, prossegue para etapa A.

## Receitas (CLI)

### 1. Auditar ciclo inteiro (uso Skill 8)
```bash
python .claude/skills/auditando-cadastro-fiscal-odoo/scripts/auditar_cadastro_inventario.py \
    --ciclo INVENTARIO_2026_05 \
    --perfil inventario
```

### 2. Auditar lista de cods + auto-fix barcode
```bash
python .claude/skills/auditando-cadastro-fiscal-odoo/scripts/auditar_cadastro_inventario.py \
    --cods "102020600,4829046,4879046" \
    --perfil inventario \
    --auto-corrigir-barcode \
    --confirmar
```

### 3. Auditar apenas G017/G018 (skip pipeline + lote)
```bash
python .claude/skills/auditando-cadastro-fiscal-odoo/scripts/auditar_cadastro_inventario.py \
    --cods "102020600" \
    --perfil inventario \
    --no-pipeline-check \
    --no-lote-vencido-check
```

## Exit codes

- `0` — `PRE_FLIGHT_OK` (sem bloqueios, sem warnings; pode_faturar=True)
- `1` — `PRE_FLIGHT_BLOQUEADO` (algum bloqueio detectado; pode_faturar=False)
- `2` — `PRE_FLIGHT_WARN` (so' warnings, sem bloqueio; pode_faturar=True)
- `3` — erro de uso (argparse / sem cods)

## Output (JSON)

```json
{
  "status_global": "PRE_FLIGHT_OK | PRE_FLIGHT_WARN | PRE_FLIGHT_BLOQUEADO",
  "pode_faturar": true,
  "auditados": 5,
  "erros_resolucao": [],
  "bloqueios": {
    "ncm_faltando": [],
    "barcode_invalido": [],
    "duplicacao_pipeline": []
  },
  "warnings": {
    "weight_zero": [],
    "lote_vencido": [],
    "tracking_none": []
  },
  "acoes_aplicadas": [
    {"tipo": "clear_barcode", "count": 2, "ids": [123, 456]}
  ],
  "tempo_ms": 320,
  "erro": null
}
```

## Trade-offs (V1 minima)

- **Perfis multiplos previstos** mas SO' V1 implementada (alinha com
  feedback `[[skills_demanda_driven]]` — V2 quando demanda real surgir).
- **READ-only por default** + WRITE so' G035 (autorizado explicitamente).
  Outras correcoes (cadastrar NCM, alterar weight) sao MANUAIS.
- **D-OPS-2 (duplicacao pipeline) precisa db_session** — sem `--ciclo` ou
  sem fornecer a sessao SQLAlchemy, o check eh' skipado.

## Cross-refs

- Skill 8 que invoca: `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md` §4
- Service: `app/odoo/estoque/scripts/cadastro_fiscal_audit.py`
- Gotchas docs: `docs/inventario-2026-05/02-gotchas/G017,G018,G035,G014-*.md`
- Memorias: `[[teste-real-6-cods-v14a-ops]]` (D-OPS-1..D-OPS-5 origem)
- Atomo dependente: `app/odoo/utils/gtin_validator.py` (G035)
- Skill 2 fix D-OPS-5: `[[skill2_distribuir_indisp_pattern]]` (v14b)
