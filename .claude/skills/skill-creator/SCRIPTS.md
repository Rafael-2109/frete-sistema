# Scripts — Skill Creator (Detalhes)

Referencia detalhada de parametros, retornos e modos de operacao.

---

## Ambiente Virtual

Nao requer ambiente virtual do projeto Flask.
Excecoes: `quick_validate.py` requer `pyyaml`; `improve_description.py` requer `anthropic`.

---

## 1. utils.py

**Proposito:** Utilitarios compartilhados. Parser de SKILL.md com suporte a YAML multiline (`>`, `|`, `>-`, `|-`).

**Funcoes:**
- `parse_skill_md(skill_path: Path) -> tuple[str, str, str]` — Retorna `(name, description, full_content)`.

**Usado por:** `run_eval.py`, `improve_description.py`, `run_loop.py`.

---

## 2. quick_validate.py

**Proposito:** Valida estrutura de uma skill (SKILL.md + frontmatter YAML). Verifica existencia do arquivo, formato do frontmatter, campos obrigatorios e convencoes de nomes.

```bash
python .claude/skills/skill-creator/scripts/quick_validate.py <skill_directory>
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `<skill_directory>` | Caminho do diretorio da skill (OBRIGATORIO, posicional) | `.claude/skills/minha-skill` |

**Validacoes realizadas:**

| Validacao | Descricao |
|-----------|-----------|
| SKILL.md existe | Verifica presenca do arquivo |
| Frontmatter YAML | Verifica `---` delimitadores e YAML valido |
| Campos obrigatorios | `name` e `description` devem existir |
| Propriedades permitidas | name, description, license, allowed-tools, metadata, compatibility |
| Nome kebab-case | Letras minusculas, digitos e hifens. Max 64 caracteres |
| Descricao limpa | Sem angle brackets (`<>`). Max 1024 caracteres |
| Compatibility | String opcional, max 500 caracteres |

**Output:** Mensagem de texto. Exit code 0 = valido, 1 = invalido.

**Dependencia:** `pyyaml`.

---

## 3. package_skill.py

**Proposito:** Empacota uma skill em arquivo `.skill` (formato ZIP) para distribuicao. Executa validacao automatica antes de empacotar. Exclui `__pycache__/`, `*.pyc`, `.DS_Store`, `node_modules/`, e `evals/` (na raiz).

```bash
python .claude/skills/skill-creator/scripts/package_skill.py <path/to/skill-folder> [output-directory]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `<path/to/skill-folder>` | Caminho do diretorio da skill (OBRIGATORIO) | `.claude/skills/my-skill` |
| `[output-directory]` | Diretorio de saida (opcional, default: CWD) | `./dist` |

**Output:** Texto livre com lista de arquivos adicionados/skipped. Exit code 0 = sucesso, 1 = erro.

---

## 4. init_skill.py (recurso adicional)

**Proposito:** Cria uma nova skill a partir de template. Gera diretorio com SKILL.md, scripts/, references/ e assets/ com arquivos de exemplo.

> **Nota:** Este script NAO existe na versao oficial Anthropic. Mantido como recurso adicional do projeto.

```bash
python .claude/skills/skill-creator/scripts/init_skill.py <skill-name> --path <path>
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `<skill-name>` | Nome da skill em kebab-case (OBRIGATORIO) | `data-analyzer` |
| `--path` | Diretorio onde criar a skill (OBRIGATORIO) | `--path .claude/skills` |

**Regras de nome:** Apenas letras minusculas, digitos e hifens. Max 40 caracteres.

**Output:** Texto livre com status de criacao. Exit code 0 = sucesso, 1 = erro.

---

## 5. improve_description.py

**Proposito:** Otimiza a description de uma skill usando a API Anthropic com extended thinking. Analisa resultados de eval para gerar descriptions melhoradas que triggeram corretamente.

```bash
python -m scripts.improve_description \
  --eval-results <path/to/eval-results.json> \
  --skill-path <path/to/skill> \
  --model <model-id> \
  [--history <path/to/history.json>] \
  [--verbose]
```

| Parametro | Descricao |
|-----------|-----------|
| `--eval-results` | JSON com resultados do `run_eval.py` (OBRIGATORIO) |
| `--skill-path` | Diretorio da skill (OBRIGATORIO) |
| `--model` | Modelo Anthropic para improvement (OBRIGATORIO) |
| `--history` | JSON com tentativas anteriores (opcional) |
| `--verbose` | Imprime thinking no stderr |

**Funcionalidade:**
- Recebe eval results e gera nova description via Claude com thinking
- Se description > 1024 chars, automaticamente pede rewrite mais curto
- Loga transcripts em JSON para auditoria

**Output:** JSON com `description` (nova) e `history` (acumulado). Exit code 0 = sucesso.

**Dependencia:** `anthropic` (requer `ANTHROPIC_API_KEY` no ambiente).

---

## 6. run_eval.py

**Proposito:** Testa se uma description faz Claude triggerar a skill corretamente. Cria command file temporario em `.claude/commands/`, roda `claude -p` com `--output-format stream-json`, e detecta triggering via stream events.

```bash
python -m scripts.run_eval \
  --eval-set <path/to/eval-set.json> \
  --skill-path <path/to/skill> \
  [--description "override description"] \
  [--num-workers 10] \
  [--timeout 30] \
  [--runs-per-query 3] \
  [--trigger-threshold 0.5] \
  [--model <model-id>] \
  [--verbose]
```

| Parametro | Descricao | Default |
|-----------|-----------|---------|
| `--eval-set` | JSON com queries e should_trigger (OBRIGATORIO) | — |
| `--skill-path` | Diretorio da skill (OBRIGATORIO) | — |
| `--description` | Override da description a testar | SKILL.md |
| `--num-workers` | Workers paralelos (ProcessPoolExecutor) | 10 |
| `--timeout` | Timeout por query em segundos | 30 |
| `--runs-per-query` | Repeticoes por query | 3 |
| `--trigger-threshold` | Threshold de trigger rate | 0.5 |
| `--model` | Modelo para `claude -p` | configurado |

**Output:** JSON com results, summary (passed/failed/total). Exit code 0 = sucesso.

**Dependencia:** `claude` CLI acessivel no PATH.

---

## 7. run_loop.py

**Proposito:** Loop completo: eval -> improve -> eval -> improve. Train/test split (60/40 default) para evitar overfitting. Gera HTML report com auto-refresh.

```bash
python -m scripts.run_loop \
  --eval-set <path/to/eval-set.json> \
  --skill-path <path/to/skill> \
  --model <model-id> \
  [--max-iterations 5] \
  [--holdout 0.4] \
  [--num-workers 10] \
  [--report auto|none|<path>] \
  [--results-dir <path>] \
  [--verbose]
```

| Parametro | Descricao | Default |
|-----------|-----------|---------|
| `--eval-set` | JSON com queries (OBRIGATORIO) | — |
| `--skill-path` | Diretorio da skill (OBRIGATORIO) | — |
| `--model` | Modelo para improvement (OBRIGATORIO) | — |
| `--max-iterations` | Max iteracoes de melhoria | 5 |
| `--holdout` | Fracao held-out para test (0 = desabilita) | 0.4 |
| `--report` | `auto` (temp file), `none`, ou path | auto |
| `--results-dir` | Dir para salvar results.json + report.html | — |

**Output:** JSON com best_description, history, scores train/test. Abre browser automaticamente.

**Dependencia:** `claude` CLI, `anthropic`.

---

## 8. aggregate_benchmark.py

**Proposito:** Le grading.json de run directories e calcula mean, stddev, min, max para pass_rate, time, tokens. Gera `benchmark.json` + `benchmark.md`.

```bash
python -m scripts.aggregate_benchmark <benchmark_dir> \
  [--skill-name <name>] \
  [--skill-path <path>] \
  [--output <path/to/benchmark.json>]
```

| Parametro | Descricao | Default |
|-----------|-----------|---------|
| `<benchmark_dir>` | Diretorio com eval dirs (OBRIGATORIO) | — |
| `--skill-name` | Nome da skill | — |
| `--skill-path` | Path da skill | — |
| `--output` | Path de saida para benchmark.json | `<dir>/benchmark.json` |

**Layouts suportados:**
- Workspace: `<dir>/eval-N/{with_skill,without_skill}/run-N/grading.json`
- Legacy: `<dir>/runs/eval-N/{with_skill,without_skill}/run-N/grading.json`

**Output:** benchmark.json + benchmark.md. Exit code 0 = sucesso.

---

## 9. generate_report.py

**Proposito:** Gera HTML report visual para output do `run_loop.py`. Mostra cada iteracao com check/x por query, distingue train vs test.

```bash
python -m scripts.generate_report <input.json> [-o <output.html>] [--skill-name <name>]
```

| Parametro | Descricao |
|-----------|-----------|
| `<input>` | JSON do `run_loop.py` (ou `-` para stdin) |
| `-o` | Arquivo HTML de saida (default: stdout) |
| `--skill-name` | Nome da skill para titulo |

**Output:** HTML completo com tabela de iteracoes, scores train/test, legenda visual.

---

## Arquivos Nao-Script

### agents/

| Arquivo | Proposito |
|---------|-----------|
| `grader.md` | Instrucoes para agente de avaliacao de assertions (8 steps, output: grading.json) |
| `comparator.md` | Instrucoes para comparacao cega A/B (7 steps, output: comparison.json) |
| `analyzer.md` | Post-hoc analysis + benchmark analysis (output: analysis.json ou notes array) |

### references/

| Arquivo | Proposito |
|---------|-----------|
| `schemas.md` | JSON schemas completos: evals.json, history.json, grading.json, metrics.json, timing.json, benchmark.json, comparison.json, analysis.json |

### assets/

| Arquivo | Proposito |
|---------|-----------|
| `eval_review.html` | Template HTML para review de eval set (description optimization). Placeholders: `__EVAL_DATA_PLACEHOLDER__`, `__SKILL_NAME_PLACEHOLDER__`, `__SKILL_DESCRIPTION_PLACEHOLDER__` |

### eval-viewer/

| Arquivo | Proposito |
|---------|-----------|
| `generate_review.py` | HTTP server + gerador HTML para review de eval results. Suporta `--static`, `--previous-workspace`, `--benchmark` |
| `viewer.html` | Frontend completo: tabs Outputs/Benchmark, navegacao, feedback textarea, grading display, xlsx inline |
