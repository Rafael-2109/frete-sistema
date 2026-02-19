# COMISSOES — 408

Documentacao detalhada dos scripts de comissao no SSW: criacao geral, geracao CSV por cidade e importacao.

---

- [criar_comissao_408.py](#criar_comissao_408py)
- [gerar_csv_comissao_408.py](#gerar_csv_comissao_408py)
- [importar_comissao_cidade_408.py](#importar_comissao_cidade_408py)

---

## criar_comissao_408.py

Cria comissao de unidade no SSW. Vincula unidade a transportadora com despachos.

```bash
python .claude/skills/operando-ssw/scripts/criar_comissao_408.py \
  --unidade VIX --cnpj 42769176000152 [--data-inicio 180226] \
  [--despacho-exp "1,00"] [--despacho-rec "1,00"] \
  [--defaults-file ssw_defaults.json] --dry-run
```

**FIELD_MAP** (5 campos):

| Parametro CLI | Campo SSW | Limite | Obrigatorio |
|---------------|-----------|--------|-------------|
| unidade | `2` (id) | 3 | Sim |
| cnpj | `3` (id) | 14 | Sim |
| data_inicio | `data_ini` | 6 | Nao (default: 180226) |
| despacho_exp | `exp_emit_despacho_pol` | 10 | Nao (default: 1,00) |
| despacho_rec | `rec_dest_despacho_pol` | 10 | Nao (default: 1,00) |

**Fluxo SSW**: Unidade → `ajaxEnvia('ENV', 1)` → preencher CNPJ + campos → `ajaxEnvia('ENV2', 0)`

**Deteccao de existencia**: `document.getElementById('acao')?.value` — `'A'` = ja existe, `'I'` = inclusao.

**Deteccao de sucesso**: Popup fecha automaticamente (TargetClosedError). Popup aberto = erro.

**Prerequisitos**: 478 finalizado (`inclusao` != 'S') + 485 cadastrado + 401 unidade existente.

| Mensagem SSW | Causa | Solucao |
|-------------|-------|---------|
| "CNPJ nao cadastrado como fornecedor" | 478 com `inclusao=S` | Corrigir 478 primeiro |
| "CNPJ nao cadastrado como fornecedor" | Fornecedor nao existe | Cadastrar na 478 |
| (popup nao fecha, sem mensagem) | Nao cadastrado na 485 | Cadastrar na 485 |

---

## gerar_csv_comissao_408.py

Gera CSVs de comissao **por cidade** para importacao em lote na 408. Python puro (pandas + csv), NAO usa Playwright.

```bash
python .claude/skills/operando-ssw/scripts/gerar_csv_comissao_408.py \
  --excel /tmp/backup_vinculos.xlsx \
  [--aba Sheet] [--output-dir /tmp/ssw_408_csvs/] \
  [--unidades BVH,CGR] [--template ../comissao_408_template.json] \
  [--dry-run]
```

| Parametro | Obrigatorio | Descricao |
|-----------|-------------|-----------|
| --excel | Sim | Excel com precos por cidade (backup_vinculos.xlsx) |
| --aba | Nao | Nome da aba (default: Sheet) |
| --output-dir | Nao | Diretorio de saida (default: /tmp/ssw_408_csvs/) |
| --unidades | Nao | Filtrar por IATA virgula-sep. Sem = todas |
| --template | Nao | Template JSON (default: ../comissao_408_template.json) |
| --dry-run | -- | Estatisticas sem gerar arquivos |

**CSV de saida**: 238 colunas, separador `;`, encoding ISO-8859-1, decimais com virgula. 2 linhas por cidade: E=expedicao, R=recepcao.

**Conversoes Excel → CSV**:

| Excel | CSV targets | Conversao |
|-------|-------------|-----------|
| Acr. Frete | EXP/REC_1_PERC_FRETE_* | x100 (decimal → %) |
| GRIS/ADV | EXP/REC_2_PERC_VLR_MERC_* | x100 (decimal → %) |
| DESPACHO/CTE/TAS | EXP/REC_3_DESPACHO_* | as-is (R$) |
| FRETE PESO | EXP/REC_3_APOS_ULT_FX_* | x1000 (R$/KG → R$/TON) |
| VALOR MINIMO | EXP/REC_4_MINIMO_R$_* | as-is (R$) |
| PEDAGIO | EXP/REC_5_PEDAGIO_FRACAO_100KG | as-is (R$) |

**POLO/REGIAO/INTERIOR**: Recebem o MESMO valor (comissao por cidade).

**CIDADE/UF**: `{CIDADE_UPPERCASE_SEM_ACENTO}/{UF}`. Apostrofos e hifens convertidos para espaco (SSW usa `D OESTE`, nao `D'OESTE`).

---

## importar_comissao_cidade_408.py

Importa CSVs de comissao por cidade na 408 do SSW via Playwright. Individual ou lote.

```bash
# Individual:
python .claude/skills/operando-ssw/scripts/importar_comissao_cidade_408.py \
  --csv /tmp/ssw_408_csvs/BVH_comissao_408.csv --unidade BVH --dry-run

# Lote:
python .claude/skills/operando-ssw/scripts/importar_comissao_cidade_408.py \
  --csv-dir /tmp/ssw_408_csvs/ [--unidades BVH,CGR,SSA] --dry-run
```

| Parametro | Obrigatorio | Descricao |
|-----------|-------------|-----------|
| --csv | Sim* | Caminho do CSV (modo individual) |
| --unidade | Nao | Sigla IATA (auto-detectado do nome se omitido) |
| --csv-dir | Sim* | Diretorio com CSVs `*_comissao_408.csv` (modo lote) |
| --unidades | Nao | Filtrar por IATA virgula-sep (sem = todas) |
| --dry-run | -- | Valida CSVs sem importar |

*Obrigatorio: `--csv` OU `--csv-dir` (um dos dois).

**Fluxo SSW por unidade**: Abrir 408 → preencher unidade → `CSV_CID` → popup upload → `IMP_CSV` → coleta resultado.

**AJAX actions**: `CSV_CID` (flag 1) abre popup importacao. `IMP_CSV` (flag 0) submete.

**Contadores SSW**: "Incluidas" = novas. "Alteradas" = valores diferentes (sobrescreve). "Nao inclusas" = valores identicos (nenhuma alteracao).

**Prerequisitos**: CSVs gerados por `gerar_csv_comissao_408.py` (238 cols, `;`, ISO-8859-1) + comissao geral ja existente.

**Pausa entre unidades**: 3 segundos entre imports.
