# Skill Improvement Roadmap

**Criado**: 2026-02-26
**Objetivo**: Passar cada skill pelo ciclo de melhoria do skill-creator
**Modo de uso**: Abrir 1 sessao por skill. Cada sessao le este arquivo, pega a proxima skill `PENDING`, muda para `IN_PROGRESS`, executa as etapas, e muda para `DONE`.

---

## Setup da Sessao

### Como iniciar (1 comando por aba):

```bash
claude --dangerously-skip-permissions -p "Leia .claude/skills/SKILL_IMPROVEMENT_ROADMAP.md. Pegue a proxima skill PENDING. IMEDIATAMENTE marque como IN_PROGRESS neste arquivo (Edit tool). Depois execute os 7 passos. Ao final marque DONE com data."
```

Ou interativamente: abrir `claude --dangerously-skip-permissions` e colar o prompt.

**NAO usar plan mode** — o roadmap JA E o plano. Ir direto para execucao.

Para rodar varias em paralelo, abra N abas e cole o prompt em cada uma.
Cada sessao pega a proxima PENDING automaticamente — sem conflito.

---

## Etapas por Skill (6 passos + limpeza)

### Passo 1 — Validacao Estrutural
```bash
source .venv/bin/activate && python .claude/skills/skill-creator/scripts/quick_validate.py .claude/skills/{SKILL_NAME}/
```
Corrigir problemas encontrados antes de prosseguir.

### Passo 2 — Criar Evals
Criar `.claude/skills/{SKILL_NAME}/evals/evals.json` com 3-5 test cases:
- Cobrir cada script/funcionalidade da skill
- Cada eval com `prompt`, `expected_output`, `expectations` (assertions)
- Incluir cenarios de sucesso E de borda (dados vazios, ambiguidade)

### Passo 3 — Executar Evals (with_skill vs without_skill)
Para cada eval, spawnar 2 agentes em paralelo:
- `with_skill`: Agente com SKILL.md + scripts disponiveis
- `without_skill`: Agente generico sem skill (baseline)
Salvar outputs em `{SKILL_NAME}-workspace/iteration-1/eval-{N}/`

### Passo 4 — Grading + Benchmark
- Grading de cada run seguindo `.claude/skills/skill-creator/agents/grader.md`
- Benchmark agregado via `scripts/aggregate_benchmark.py`
- Viewer HTML via `eval-viewer/generate_review.py`

### Passo 5 — Melhorar SKILL.md
Com base nos resultados:
- Instrucoes mais claras onde o agente errou
- Regras anti-alucinacao especificas da skill
- Cenarios compostos (multi-query) se aplicavel
- Tratamento de resultados vazios/erro
- Regra de fidelidade ao output dos scripts

### Passo 6 — Criar Trigger Eval Set + Otimizacao de Description
```bash
# Criar trigger_eval_set.json com 20 queries (10 true + 10 false)
source .venv/bin/activate && export $(grep ANTHROPIC_API_KEY .env) && \
cd .claude/skills/skill-creator && python -m scripts.run_loop \
  --eval-set ../../skills/{SKILL_NAME}/evals/trigger_eval_set.json \
  --skill-path ../../skills/{SKILL_NAME} \
  --model claude-sonnet-4-6 \
  --max-iterations 5 \
  --hide-real-skill \
  --verbose
```
**NOTA**: O `run_loop` tem recall baixo (~0-11%) para queries simples.
Limitacao conhecida do mecanismo `.claude/commands/`. O valor esta nas
descriptions alternativas geradas, nao no score absoluto.

### Passo 7 — Limpeza OBRIGATORIA

**MANTER** (commitar):
- `.claude/skills/{SKILL_NAME}/evals/` — test cases reutilizaveis
- `.claude/skills/{SKILL_NAME}/SKILL.md` — melhorias aplicadas
- Este roadmap (status atualizado)

**REMOVER** (antes de commitar):
- `.claude/skills/{SKILL_NAME}-workspace/` — artefatos de execucao
- Qualquer arquivo temporario em `/tmp/` gerado pelo viewer/report

**COMMITAR** ao final:
```bash
git add .claude/skills/{SKILL_NAME}/SKILL.md .claude/skills/{SKILL_NAME}/evals/ .claude/skills/SKILL_IMPROVEMENT_ROADMAP.md
git commit -m "improve(skill): {SKILL_NAME} — evals + SKILL.md melhorado

- Validacao estrutural OK
- N evals criados cobrindo scripts/funcionalidades
- SKILL.md melhorado com [resumo das melhorias]
- Trigger eval set com 20 queries
- Workspace limpo

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Roadmap de Skills

### Legenda
- `DONE` — Ciclo completo executado e commitado
- `IN_PROGRESS` — Sessao ativa trabalhando (NAO pegar esta skill)
- `PENDING` — Aguardando sessao
- `SKIP` — Nao aplicavel

### P1 — Alta Complexidade (>100KB, muitos scripts)

| # | Skill | Scripts | Size | Status | Data |
|---|-------|---------|------|--------|------|
| 1 | `cotando-frete` | 4 | 124KB | DONE | 2026-02-26 |
| 2 | `gerindo-expedicao` | 8 | 504KB | DONE | 2026-02-26 |
| 3 | `rastreando-odoo` | 8 | 572KB | IN_PROGRESS | 2026-02-26 |
| 4 | `operando-ssw` | 16 | 532KB | DONE | 2026-02-26 |
| 5 | `consultando-sql` | 2 | 928KB | DONE | 2026-02-26 |
| 6 | `resolvendo-entidades` | 7 | 116KB | DONE | 2026-02-26 |

### P2 — Media Complexidade (scripts + references)

| # | Skill | Scripts | Size | Status | Data |
|---|-------|---------|------|--------|------|
| 7 | `gerindo-carvia` | 3 | 100KB | DONE | 2026-02-26 |
| 8 | `monitorando-entregas` | 3 | 88KB | DONE | 2026-02-26 |
| 9 | `integracao-odoo` | 4 | 76KB | DONE | 2026-02-26 |
| 10 | `visao-produto` | 2 | 48KB | DONE | 2026-02-26 |
| 11 | `acessando-ssw` | 2 | 44KB | IN_PROGRESS | 2026-02-26 |
| 12 | `diagnosticando-banco` | 1 | 44KB | DONE | 2026-02-26 |

### P3 — Simples (1 script)

| # | Skill | Scripts | Size | Status | Data |
|---|-------|---------|------|--------|------|
| 13 | `exportando-arquivos` | 1 | 36KB | DONE | 2026-02-26 |
| 14 | `lendo-arquivos` | 1 | 32KB | DONE | 2026-02-26 |
| 15 | `memoria-usuario` | 1 | 32KB | DONE | 2026-02-26 |
| 16 | `descobrindo-odoo-estrutura` | 1 | 32KB | DONE | 2026-02-26 |
| 17 | `buscando-rotas` | 1 | 16KB | IN_PROGRESS | 2026-02-26 |

### P4 — Reference-Only (sem scripts proprios)

| # | Skill | Refs | Size | Status | Data |
|---|-------|------|------|--------|------|
| 18 | `executando-odoo-financeiro` | 3 | 64KB | DONE | 2026-02-26 |
| 19 | `conciliando-odoo-po` | 3 | 56KB | DONE | 2026-02-26 |
| 20 | `validacao-nf-po` | 2 | 48KB | IN_PROGRESS | 2026-02-26 |
| 21 | `recebimento-fisico-odoo` | 2 | 44KB | DONE | 2026-02-26 |
| 22 | `frontend-design` | 2 | 44KB | IN_PROGRESS | 2026-02-26 |
| 23 | `razao-geral-odoo` | 0 | 16KB | DONE | 2026-02-26 |

### SKIP — Meta-skills

| # | Skill | Motivo | Status |
|---|-------|--------|--------|
| 24 | `skill-creator` | Meta-skill (ferramenta de melhoria) | SKIP |
| 25 | `ralph-wiggum` | Meta-skill (loop autonomo) | SKIP |
| 26 | `prd-generator` | Meta-skill (geracao de specs) | SKIP |

---

## Referencia Rapida

### Licoes da cotando-frete
1. **Workspace descartavel** — artefatos de execucao (~1MB+) nao ficam no repo
2. **Evals permanentes** — `evals.json` e `trigger_eval_set.json` sao reutilizaveis
3. **run_loop recall baixo** — esperado para queries simples, foco nas descriptions geradas
4. **ANTHROPIC_API_KEY** — precisa de `export $(grep ANTHROPIC_API_KEY .env)` antes do run_loop
5. **Modelo correto** — usar `claude-sonnet-4-6` (sem sufixo de data)
6. **Melhorias mais valiosas** — cenarios compostos, anti-alucinacao, fidelidade ao output

### Tempo Estimado
- P1 (alta): ~2-3h por skill
- P2 (media): ~1-2h por skill
- P3 (simples): ~30min-1h por skill
- P4 (reference-only): ~30min por skill
