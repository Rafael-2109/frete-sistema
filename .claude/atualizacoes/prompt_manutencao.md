Voce e o ORQUESTRADOR de manutencao semanal do projeto Sistema de Fretes.
Seu papel e coordenar 6 dominios de manutencao em 3 estagios, usando agentes paralelos.

REGRAS INVIOLAVEIS:
- NUNCA executar dominios sequencialmente quando podem ser paralelos
- SEMPRE verificar status.json de cada dominio antes de prosseguir
- NUNCA abortar tudo por falha de um dominio — os demais continuam
- SEMPRE gerar relatorio consolidado, mesmo se todos falharem

---

## SETUP

```bash
DATA=$(date +%Y-%m-%d)
mkdir -p /tmp/manutencao-$DATA
```

Ler os 6 arquivos de dominio:
- `.claude/atualizacoes/dominios/dominio-1-claude-md.md`
- `.claude/atualizacoes/dominios/dominio-2-references.md`
- `.claude/atualizacoes/dominios/dominio-3-memorias.md`
- `.claude/atualizacoes/dominios/dominio-4-sentry.md`
- `.claude/atualizacoes/dominios/dominio-5-tests.md`
- `.claude/atualizacoes/dominios/dominio-6-memory-eval.md`

---

## ESTAGIO 1 — Lancar 4 agentes EM PARALELO

CRITICO: Lancar os 4 agentes SIMULTANEAMENTE em uma unica mensagem com 4 Agent tool calls.
NAO lancar um, esperar, e lancar o proximo. Todos ao mesmo tempo.

### Agent D1 — CLAUDE.md Audit
- Prompt: conteudo COMPLETO de `dominio-1-claude-md.md`
- Mode: bypassPermissions
- Espera: escrever `/tmp/manutencao-{DATA}/dominio-1-status.json`

### Agent D2 — References Audit
- Prompt: conteudo COMPLETO de `dominio-2-references.md`
- Mode: bypassPermissions
- Espera: escrever `/tmp/manutencao-{DATA}/dominio-2-status.json`

### Agent D3 — Memorias Cleanup
- Prompt: conteudo COMPLETO de `dominio-3-memorias.md`
- Mode: bypassPermissions
- Espera: escrever `/tmp/manutencao-{DATA}/dominio-3-status.json`

### Agent D4 — Sentry Triage
- Prompt: conteudo COMPLETO de `dominio-4-sentry.md`
- Mode: bypassPermissions
- Espera: escrever `/tmp/manutencao-{DATA}/dominio-4-status.json`

### Verificacao pos-Estagio 1

Apos TODOS os 4 agentes retornarem, verificar:
```bash
for i in 1 2 3 4; do
  if [ -f /tmp/manutencao-$DATA/dominio-$i-status.json ]; then
    echo "D$i: $(cat /tmp/manutencao-$DATA/dominio-$i-status.json | python3 -c 'import sys,json; d=json.load(sys.stdin); print(d["status"], "-", d["resumo"])')"
  else
    echo "D$i: AUSENTE (agente falhou sem escrever status)"
  fi
done
```

Se TODOS os 4 status estiverem FAILED ou ausentes, PULAR Estagio 2 e ir direto para ESTAGIO 3 (consolidacao).

---

## ESTAGIO 2 — Lancar 2 agentes EM PARALELO

CRITICO: Lancar os 2 agentes SIMULTANEAMENTE.

### Agent D5 — Test Runner
- Prompt: conteudo COMPLETO de `dominio-5-tests.md`
- Mode: bypassPermissions
- Espera: escrever `/tmp/manutencao-{DATA}/dominio-5-status.json`

### Agent D6 — Memory Eval (Render Postgres)
- Prompt: conteudo COMPLETO de `dominio-6-memory-eval.md`
- Mode: bypassPermissions
- Espera: escrever `/tmp/manutencao-{DATA}/dominio-6-status.json`

### Verificacao pos-Estagio 2

Mesma logica do Estagio 1 — verificar `dominio-5-status.json` e `dominio-6-status.json`.

---

## ESTAGIO 3 — Consolidacao (voce executa diretamente, sem agentes)

### 3.1 Coletar resultados

Ler TODOS os 6 status.json existentes em `/tmp/manutencao-{DATA}/`.
Para cada dominio:
- Se status.json existe: extrair status, resumo, metricas
- Se status.json nao existe: marcar como FAILED (agente nao completou)

### 3.2 Git operations (apenas se algum dominio produziu mudancas)

Verificar se ha mudancas com `git status`. Se sim:

```bash
# Criar branch (ou usar existente se re-run no mesmo dia)
git checkout -b manutencao/semanal-$DATA 2>/dev/null || git checkout manutencao/semanal-$DATA

# Commits atomicos por dominio
# D1 (CLAUDE.md)
git add CLAUDE.md app/*/CLAUDE.md app/agente/services/CLAUDE.md .claude/atualizacoes/claude_md/
git commit -m "maint(claude-md): auditoria semanal $DATA" || true

# D2 (References)
git add .claude/references/ .claude/atualizacoes/references/
git commit -m "maint(references): revisao semanal $DATA" || true

# D3 (Memorias) — arquivos de memoria sao fora do repo, mas o relatorio fica dentro
git add .claude/atualizacoes/memorias/
git commit -m "maint(memorias): reorganizacao semanal $DATA" || true

# D4 (Sentry) — adicionar APENAS arquivos listados em dominio-4-status.json:arquivos_modificados
# Ler a lista de arquivos modificados do status.json do D4
if [ -f /tmp/manutencao-$DATA/dominio-4-status.json ]; then
  SENTRY_FILES=$(python3 -c 'import sys,json; d=json.load(open("/tmp/manutencao-'$DATA'/dominio-4-status.json")); [print(f) for f in d.get("arquivos_modificados",[])]' 2>/dev/null)
  if [ -n "$SENTRY_FILES" ]; then
    echo "$SENTRY_FILES" | xargs git add
  fi
fi
git add .claude/atualizacoes/sentry/
git commit -m "fix(sentry): correcoes automaticas $DATA" || true

# D5 (Tests) — apenas relatorio
git add .claude/atualizacoes/tests/
git commit -m "maint(tests): relatorio de testes $DATA" || true

# D6 (Memory Eval) — apenas relatorio
git add .claude/atualizacoes/memory-eval/
git commit -m "maint(memory-eval): avaliacao de saude $DATA" || true
```

NOTA: `|| true` garante que commit vazio (sem mudancas) nao aborta o script.

### 3.3 Relatorio consolidado

Gerar `.claude/atualizacoes/atualizacao-{DATA}-consolidado.md`:

```markdown
# Manutencao Semanal Consolidada — {DATA}

**Data**: {DATA}
**Dominios executados**: 6
**Dominios OK**: X | **PARCIAL**: Y | **FAILED**: Z

## Resumo por Dominio

| # | Dominio | Status | Resumo |
|---|---------|--------|--------|
| 1 | CLAUDE.md Audit | OK/PARCIAL/FAILED | ... |
| 2 | References Audit | OK/PARCIAL/FAILED | ... |
| 3 | Memorias Cleanup | OK/PARCIAL/FAILED | ... |
| 4 | Sentry Triage | OK/PARCIAL/FAILED | ... |
| 5 | Test Runner | OK/PARCIAL/FAILED | ... |
| 6 | Memory Eval | OK/PARCIAL/FAILED | ... |

## Metricas

### CLAUDE.md
- Arquivos auditados: X/9, modificados: Y

### References
- Arquivos revisados: X, corrigidos: Y

### Memorias
- Auditadas: X, removidas: Y, consolidadas: Z

### Sentry
- Issues avaliadas: X, corrigidas: Y, ignoradas: Z

### Tests
- Total: X, passed: Y, failed: Z, taxa: W%

### Memory Eval (Producao)
- Health score: X/100
- Total memorias: X, cold: Y, stale 60d: Z
- Recomendacoes: N

## Erros e Falhas
(Listar erros de cada dominio que falhou)
```

### 3.4 Commitar consolidado

```bash
git add .claude/atualizacoes/atualizacao-$DATA-consolidado.md
git commit -m "maint: relatorio consolidado semanal $DATA" || true
```

### 3.5 Push e PR

```bash
git push origin manutencao/semanal-$DATA
```

Criar PR:
```bash
gh pr create \
  --title "maint: manutencao semanal $DATA" \
  --body "## Manutencao Semanal Automatizada

Relatorio consolidado: \`.claude/atualizacoes/atualizacao-$DATA-consolidado.md\`

### Dominios Executados
- D1: CLAUDE.md Audit
- D2: References Audit
- D3: Memorias Cleanup
- D4: Sentry Triage + Fixes
- D5: Test Runner
- D6: Memory Eval (Producao)

Gerado automaticamente pelo Orquestrador de Manutencao." \
  --base main
```

Se `git push` ou `gh pr create` falhar, registrar no log e continuar (commits ficam locais).

### 3.6 Finalizar

Informar resultado final:
- Quantos dominios OK/PARCIAL/FAILED
- URL do PR (se criado)
- Caminho do relatorio consolidado
- Caminho do log em /tmp/
