# CADASTROS — 401, 402, 478, 485

Documentacao detalhada dos scripts de cadastro no SSW: unidades, cidades, fornecedores e transportadoras.

---

- [cadastrar_unidade_401.py](#cadastrar_unidade_401py)
- [cadastrar_cidades_402.py](#cadastrar_cidades_402py)
- [exportar_cidades_402.py](#exportar_cidades_402py)
- [importar_cidades_402.py](#importar_cidades_402py)
- [cadastrar_fornecedor_478.py](#cadastrar_fornecedor_478py)
- [cadastrar_transportadora_485.py](#cadastrar_transportadora_485py)

---

## cadastrar_unidade_401.py

Cadastra nova unidade operacional. 31 campos com defaults do ssw_defaults.json.

```bash
python .claude/skills/operando-ssw/scripts/cadastrar_unidade_401.py \
  --sigla CGR --tipo T --razao-social "ALEMAR - CAMPO GRANDE/MS" \
  --nome-fantasia "ALEMAR CGR" [--ie "ISENTO"] [--cnpj 62312605000175] \
  [--defaults-file .claude/skills/operando-ssw/ssw_defaults.json] --dry-run
```

| Parametro | Obrigatorio | Descricao |
|-----------|-------------|-----------|
| --sigla | Sim | Codigo IATA 3 chars (ex: CGR, CWB, POA) |
| --tipo | Nao | T=Terceiro, F=Filial, M=Matriz (default: T) |
| --razao-social | Sim | Max 45 chars. Padrao: "[Parceiro] - [Cidade]/[UF]" |
| --nome-fantasia | Nao | Max 30 chars (default: razao social truncada) |
| --cnpj | Nao | 14 digitos (default: CNPJ CarVia do ssw_defaults.json) |
| --ie | Nao | Inscricao Estadual (vazio se isento) |
| --dry-run | -- | Preview sem submeter |

**Regra tipo T**: Usa CNPJ, IE, banco e dados fiscais da CarVia (nao do parceiro). Veja POP-A02.

---

## cadastrar_cidades_402.py

Cadastra cidades individualmente na grid da 402. **SOMENTE para 1-3 cidades no viewport.**

```bash
python .claude/skills/operando-ssw/scripts/cadastrar_cidades_402.py \
  --uf MS --unidade CGR \
  --cidades '[{"cidade":"CAMPO GRANDE","polo":"P","prazo":2}]' --dry-run
```

| Parametro | Obrigatorio | Descricao |
|-----------|-------------|-----------|
| --uf | Sim | UF para filtrar cidades (ex: MS, SP) |
| --unidade | Sim | Sigla da unidade responsavel (ex: CGR) |
| --cidades | Sim | JSON array com objetos {cidade, polo, prazo, ...} |
| --dry-run | -- | Preview sem submeter |

Campos obrigatorios por cidade: `cidade`, `polo` (P/R/I). `prazo` recomendado. Demais usam defaults do ssw_defaults.json.

**LIMITACAO CRITICA**: SSW 402 usa **virtual scroll** — apenas ~90 cidades existem no DOM por vez (de 400+ por UF). Cidades fora do viewport NAO podem ser alteradas via ATU. **Para >3 cidades ou fora do viewport, USAR `importar_cidades_402.py`**.

---

## exportar_cidades_402.py

Exporta CSV completo de cidades atendidas de uma UF na 402. Passo 1 do workflow CSV.

```bash
python .claude/skills/operando-ssw/scripts/exportar_cidades_402.py \
  --uf BA [--output /tmp/ba_402_export.csv] [--dry-run]
```

| Parametro | Obrigatorio | Descricao |
|-----------|-------------|-----------|
| --uf | Sim | UF para exportar (ex: BA, SP, MS) |
| --output | Nao | Caminho do CSV (default: /tmp/{uf}_402_export.csv) |
| --dry-run | -- | Mostra o que seria exportado sem executar |

**CRITICO**: `_MOD_CSV` so funciona na tela INICIAL da 402. Apos VIS_UF o botao desaparece.

**CSV exportado**: 45 colunas, separador `;`, encoding ISO-8859-1. Preserva formato exato do SSW (feriados `00/00`, sabado ` `, trailing `;`).

---

## importar_cidades_402.py

Importa cidades via CSV na 402. **Metodo PREFERIDO para alteracao bulk.**

```bash
python .claude/skills/operando-ssw/scripts/importar_cidades_402.py \
  --csv /tmp/cidades_cgr.csv --dry-run

python .claude/skills/operando-ssw/scripts/importar_cidades_402.py \
  --csv /tmp/cidades_cgr.csv --timeout 30
```

| Parametro | Obrigatorio | Descricao |
|-----------|-------------|-----------|
| --csv | Sim | Caminho do CSV (formato 402, separador `;`, ISO-8859-1) |
| --dry-run | -- | Valida CSV sem importar |
| --timeout | -- | Timeout apos IMPORTA2 (default: 20s). Aumentar para CSVs grandes |

**CRITICO — PRACA_COMERCIAL**: Para INCLUIR cidades novas (sem UNIDADE existente), o CSV DEVE ter PRACA_COMERCIAL (indice 15) = UNIDADE + POLO (ex: "SSAI", "JPAI"). Sem este campo, cidades sem UNIDADE sao silenciosamente ignoradas.

**Contadores SSW**: Inclusoes = cidades novas. Alteracoes = atualizadas. Nao inclusas = valores IDENTICOS ao SSW (NAO significa "nao sobrescreve").

### Workflow Exportar → Modificar → Importar

1. **Exportar**: `exportar_cidades_402.py --uf XX` — preserva todos 45 campos
2. **Modificar**: Python (ISO-8859-1, separador `;`) — alterar somente campos necessarios
3. **Importar**: `importar_cidades_402.py --csv /tmp/modificado.csv`

**IMPORTANTE**: Gerar CSV do zero (sem exportar primeiro) e fragil — formatos de feriado (`00/00`), sabado (espaco) e trailing `;` causam 0 matches.

---

## cadastrar_fornecedor_478.py

Cadastra fornecedor no SSW. **Prerequisito** para 485 e 408.

```bash
python .claude/skills/operando-ssw/scripts/cadastrar_fornecedor_478.py \
  --cnpj 42769176000152 --nome "UNI BRASIL TRANSPORTES" \
  --especialidade TRANSPORTADORA [--ie ISENTO] [--contribuinte N] \
  [--ddd 11] [--telefone 30001234] [--cep 06460040] \
  [--logradouro "RUA JOSE SOARES"] [--numero 100] [--bairro JAGUARE] \
  [--fg-cc N] [--defaults-file ssw_defaults.json] --dry-run
```

**FIELD_MAP** (12 campos):

| Parametro CLI | Campo SSW | Limite | Obrigatorio |
|---------------|-----------|--------|-------------|
| cnpj | `2` (id) | 14 | Sim |
| nome | `nome` | 45 | Sim |
| inscr_estadual | `inscr_estadual` | 20 | Nao (default: ISENTO) |
| contribuinte | `contribuinte` | 1 | Nao (default: N) |
| especialidade | `especialidade` | — | Nao (default: TRANSPORTADORA) |
| ddd | `ddd_principal` | 2 | Nao |
| telefone | `fone_principal` | 8 | Nao |
| cep | `cep_end` | 8 | Nao |
| logradouro | `logradouro` | 40 | Nao |
| numero | `numero_end` | 10 | Nao |
| bairro | `bairro_end` | 30 | Nao |
| fg_cc | `fg_cc` | 1 | Nao (default: N) |

**Validacoes**: CNPJ 14 digitos. DDD: rejeita '00', '01'. Telefone: rejeita '00000000', '99999999', min 8 digitos.

**Fluxo SSW**: CNPJ → `ajaxEnvia('PES', 0)` → preencher → `ajaxEnvia('GRA', 0)`

**GOTCHA CRITICO — `inclusao=S`**: Campo hidden. `S` = registro NAO finalizado → 408 rejeita CNPJ com "CNPJ nao cadastrado como fornecedor". Solucao: preencher TODOS os campos obrigatorios e re-executar GRA.

**`fg_cc` (CCF)**: `N` = padrao seguro. `S` requer campo `evento` (ex: 5224). CCF NAO e prerequisito para 408.

| Mensagem SSW | Causa | Solucao |
|-------------|-------|---------|
| "Informe a especialidade do fornecedor" | `especialidade` vazio | Preencher 'TRANSPORTADORA' |
| "DDD do telefone invalido" | DDD '01' ou '00' | Usar DDD real (ex: '11') |
| "Telefone invalido" | '00000000' ou '99999999' | Formato valido: '30001234' |
| "Informar ISENTO ou codigo em Inscricao Estadual" | `inscr_estadual` vazio | Preencher 'ISENTO' |
| "Se o fornecedor possui conta corrente..." | `fg_cc='S'` sem `evento` | Salvar com `fg_cc='N'` |

---

## cadastrar_transportadora_485.py

Cadastra transportadora no SSW. Mais simples que 478.

```bash
python .claude/skills/operando-ssw/scripts/cadastrar_transportadora_485.py \
  --cnpj 42769176000152 --nome "UNI BRASIL TRANSPORTES" [--ativo S] --dry-run
```

**FIELD_MAP** (3 campos):

| Parametro CLI | Campo SSW | Limite | Obrigatorio |
|---------------|-----------|--------|-------------|
| cnpj | `2` (id) | 14 | Sim |
| nome | `nome` | 45 | Sim |
| ativo | `fg_ativo` | 1 | Nao (default: S) |

**Fluxo SSW**: CNPJ → `ajaxEnvia('PES', 0)` → preencher → `ajaxEnvia('INC', 0)`

**Deteccao de existencia**: Apos PES, `nome` preenchido no DOM = ja existe.

**LIMITACAO**: CNPJ raiz com multiplas filiais → PES retorna **lista** em vez do formulario. Script da timeout. Verificar screenshot para confirmar existencia.
