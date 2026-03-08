# Scripts — Skill Creator

Documentacao dos scripts de avaliacao e otimizacao de skills.

---

## Arquivos

| Script | Descricao |
|--------|-----------|
| `utils.py` | Utilitarios compartilhados: `parse_skill_md()` |
| `run_eval.py` | Avaliacao de trigger — testa se description ativa corretamente |
| `improve_description.py` | Melhoria de description via `claude -p` |
| `run_loop.py` | Loop eval + improve com live report HTML |
| `generate_report.py` | Gerador de relatorio HTML visual |
| `quick_validate.py` | Validacao rapida da estrutura de uma skill |
| `aggregate_benchmark.py` | Agregacao de benchmarks de variance |
| `package_skill.py` | Empacotamento de skill para distribuicao |
| `init_skill.py` | Scaffold de nova skill (adicao local) |
| `run_functional_eval.py` | Eval comportamental — testa decisoes do agente (adicao local) |

---

## `run_eval.py`

Avalia se uma description faz Claude triggerar (ler a skill) para um conjunto de queries.

**Mecanismo**: Cria command files temporarios em `.claude/commands/` com UUID unico. Detecta trigger via stream events (`content_block_start/delta/stop`) para early detection — nao espera resposta completa.

```bash
python -m scripts.run_eval \
    --eval-set evals/eval_set.json \
    --skill-path .claude/skills/minha-skill \
    --runs-per-query 3 \
    --trigger-threshold 0.5 \
    --num-workers 10 \
    --timeout 30 \
    --model claude-sonnet-4-6 \
    --hide-real-skill \
    --verbose
```

| Parametro | Default | Descricao |
|-----------|---------|-----------|
| `--eval-set` | (obrigatorio) | JSON com queries e `should_trigger` |
| `--skill-path` | (obrigatorio) | Diretorio com `SKILL.md` |
| `--description` | da SKILL.md | Override da description para testar |
| `--num-workers` | 10 | Workers paralelos |
| `--timeout` | 30 | Timeout por query (segundos) |
| `--runs-per-query` | 3 | Repeticoes por query |
| `--trigger-threshold` | 0.5 | Fracao minima de triggers para PASS |
| `--model` | configurado | Modelo para `claude -p` |
| `--hide-real-skill` | false | Esconde SKILL.md real durante eval |
| `--verbose` | false | Imprime progresso em stderr |

**Formato do eval set** (`eval_set.json`):
```json
[
  {"query": "crie uma skill para monitorar entregas", "should_trigger": true},
  {"query": "consulte o saldo do produto X", "should_trigger": false}
]
```

---

## `improve_description.py`

Gera uma description melhorada baseada nos resultados de eval.

**Mecanismo**: Chama `claude -p` como subprocess (sem necessidade de `ANTHROPIC_API_KEY` separada — usa auth da sessao Claude Code). Se a description gerada exceder 1024 chars, faz rewrite automatico em single-turn.

```bash
python -m scripts.improve_description \
    --eval-results results.json \
    --skill-path .claude/skills/minha-skill \
    --model claude-opus-4-6 \
    --history history.json \
    --verbose
```

| Parametro | Default | Descricao |
|-----------|---------|-----------|
| `--eval-results` | (obrigatorio) | JSON de `run_eval.py` |
| `--skill-path` | (obrigatorio) | Diretorio com `SKILL.md` |
| `--model` | (obrigatorio) | Modelo para improvement |
| `--history` | nenhum | JSON com tentativas anteriores |
| `--verbose` | false | Imprime description em stderr |

**API programatica** (usada por `run_loop.py`):
```python
from scripts.improve_description import improve_description

new_desc = improve_description(
    skill_name="minha-skill",
    skill_content="...",
    current_description="...",
    eval_results={...},
    history=[...],
    model="claude-opus-4-6",
    log_dir=Path("logs/"),     # Salva transcripts em JSON
    iteration=1,               # Numero da iteracao
    test_results={...},        # Resultados de test set (opcional)
)
```

---

## `run_loop.py`

Loop completo: eval → improve → eval → improve → ... ate convergir ou atingir max iteracoes.

**Features**:
- **Live report HTML**: Abre no browser com auto-refresh 5s
- **Train/test split**: Holdout estratificado por `should_trigger`
- **Blinded history**: Strips campos `test_*` antes de enviar ao modelo (previne data leakage)
- **Batch eval**: Train + test avaliados juntos em 1 batch (mais rapido)
- **Precision/recall/accuracy**: Metricas detalhadas no verbose

```bash
python -m scripts.run_loop \
    --eval-set evals/eval_set.json \
    --skill-path .claude/skills/minha-skill \
    --model claude-opus-4-6 \
    --max-iterations 5 \
    --holdout 0.4 \
    --report auto \
    --results-dir results/ \
    --hide-real-skill \
    --verbose
```

| Parametro | Default | Descricao |
|-----------|---------|-----------|
| `--eval-set` | (obrigatorio) | JSON com queries |
| `--skill-path` | (obrigatorio) | Diretorio com `SKILL.md` |
| `--model` | (obrigatorio) | Modelo para improvement |
| `--max-iterations` | 5 | Maximo de iteracoes |
| `--holdout` | 0.4 | Fracao de test set (0 = sem split) |
| `--report` | `auto` | Caminho do HTML report (`none` desabilita) |
| `--results-dir` | nenhum | Diretorio para salvar results.json + report.html |
| `--hide-real-skill` | false | Esconde SKILL.md real durante eval |
| `--verbose` | false | Metricas detalhadas em stderr |
| `--num-workers` | 10 | Workers paralelos |
| `--timeout` | 30 | Timeout por query |
| `--runs-per-query` | 3 | Repeticoes por query |
| `--trigger-threshold` | 0.5 | Threshold de trigger |

---

## `generate_report.py`

Gera relatorio HTML visual a partir do output de `run_loop.py`.

```bash
# De arquivo
python -m scripts.generate_report results.json -o report.html --skill-name minha-skill

# De stdin
cat results.json | python -m scripts.generate_report - -o report.html
```

**Visual**: Google Fonts (Poppins + Lora), score badges color-coded (verde 80%+, laranja 50-79%, vermelho <50%), legenda com swatches train/test/positive/negative, highlight da melhor iteracao.

---

## `run_functional_eval.py` (adicao local)

Avaliacao comportamental — testa se o agente toma decisoes corretas (script certo, argumentos corretos, tratamento de erro) ao longo de uma interacao completa.

Diferente de `run_eval.py` (que testa apenas trigger), este roda o agente por ate 10 turns e avalia via grader (Anthropic API).

```bash
python -m scripts.run_functional_eval \
    --evals-json evals/evals.json \
    --skill-path .claude/skills/minha-skill \
    --workspace workspace/iteration-1 \
    --executor-model claude-sonnet-4-6 \
    --grader-model claude-sonnet-4-6 \
    --timeout 180 \
    --max-workers 3 \
    --configs with_skill,without_skill \
    --verbose
```

| Parametro | Default | Descricao |
|-----------|---------|-----------|
| `--evals-json` | (obrigatorio) | JSON com test cases e expectations |
| `--skill-path` | (obrigatorio) | Diretorio com `SKILL.md` |
| `--workspace` | (obrigatorio) | Diretorio para outputs |
| `--executor-model` | configurado | Modelo para executar agent |
| `--grader-model` | `claude-sonnet-4-6` | Modelo para grading |
| `--timeout` | 180 | Timeout por run (segundos) |
| `--max-workers` | 3 | Workers paralelos (so `with_skill`) |
| `--eval-ids` | todos | IDs especificos para rodar |
| `--configs` | `with_skill,without_skill` | Configs para comparar |

**Formato do evals.json**:
```json
{
  "skill_name": "minha-skill",
  "evals": [
    {
      "id": 1,
      "prompt": "faca X",
      "expectations": [
        "Usou o script correto",
        "Passou argumentos corretos"
      ]
    }
  ]
}
```

**Nota**: `without_skill` roda sequencialmente (hide/restore do SKILL.md). `with_skill` roda em paralelo.

---

## `init_skill.py` (adicao local)

Scaffold para criar nova skill com estrutura padrao.

```bash
python -m scripts.init_skill --name minha-skill --path .claude/skills/
```

---

## Dependencias

| Script | Dependencia externa |
|--------|---------------------|
| `run_eval.py` | `claude` CLI |
| `improve_description.py` | `claude` CLI |
| `run_loop.py` | `claude` CLI |
| `run_functional_eval.py` | `claude` CLI + `anthropic` SDK (para grading) |
| Demais | Nenhuma |
