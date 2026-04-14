# Plano de Atualizacao Automatizada

**Criado**: 27/03/2026
**Atualizado**: 31/03/2026 (v4 — D8 + crontab local)
**Frequencia**: D1-D7 semanal (seg 10:00) + D8 diario (11:03)
**Executor**: Crontab local (WSL2) → Claude Code CLI (Opus)

---

## Visao Geral

Tarefas agendadas que executam **8 dominios** de manutencao, gerando relatorios rastreaveis.

**Scheduler**: Crontab local (`sudo crontab -u rafaelnascimento -l`).
RemoteTrigger cloud desabilitado — nao tem acesso a MCP servers locais (Render, Sentry, Playwright).

---

## Dominios

| # | Dominio | Pasta | Manual/Prompt | O que faz |
|---|---------|-------|---------------|-----------|
| 1 | **CLAUDE.md** | [`claude_md/`](claude_md/) | [`dominios/dominio-1-claude-md.md`](dominios/dominio-1-claude-md.md) | Audita e atualiza os 9 arquivos CLAUDE.md contra o estado atual do codigo |
| 2 | **References** | [`references/`](references/) | [`dominios/dominio-2-references.md`](dominios/dominio-2-references.md) | Revisa arquivos em `.claude/references/` para precisao e melhores praticas |
| 3 | **Memorias** | [`memorias/`](memorias/) | [`dominios/dominio-3-memorias.md`](dominios/dominio-3-memorias.md) | Avalia, reorganiza e limpa arquivos de memoria seguindo best practices Anthropic |
| 4 | **Sentry** | [`sentry/`](sentry/) | [`dominios/dominio-4-sentry.md`](dominios/dominio-4-sentry.md) | Tria issues do Sentry, corrige bugs tecnicos simples, gera relatorio |
| 5 | **Tests** | [`tests/`](tests/) | [`dominios/dominio-5-tests.md`](dominios/dominio-5-tests.md) | Executa suite pytest e reporta resultados com correlacao D4 |
| 6 | **Memory Eval** | [`memory-eval/`](memory-eval/) | [`dominios/dominio-6-memory-eval.md`](dominios/dominio-6-memory-eval.md) | Avalia saude do sistema de memorias em producao (Render Postgres) |
| 7 | **Agent Intelligence Report** | [`agent-reports/`](agent-reports/) | [`dominios/dominio-7-agent-report.md`](dominios/dominio-7-agent-report.md) | Analisa sessoes, tools, friccao e gera recomendacoes prescritivas (Bridge Agent SDK <-> Claude Code) |
| 8 | **Improvement Dialogue** | [`improvement-dialogue/`](improvement-dialogue/) | [`dominios/dominio-8-improvement-dialogue.md`](dominios/dominio-8-improvement-dialogue.md) | Dialogo versionado Agent SDK <-> Claude Code: avalia sugestoes, implementa via feature-dev (cron diario separado) |

---

## Arquitetura

```
OpenClaw cron (seg 10:00)
  └── claude -p "$(cat prompt_manutencao.md)" --model opus --permission-mode bypassPermissions
        │
        ├── SETUP: mkdir /tmp/manutencao-{DATA}/, ler 6 domain prompts
        │
        ├── ESTAGIO 1 — 4 Agent calls em PARALELO:
        │   ├── D1: CLAUDE.md Audit
        │   ├── D2: References Audit
        │   ├── D3: Memorias Cleanup
        │   └── D4: Sentry Triage + Fixes
        │
        ├── ESTAGIO 2 — 3 Agent calls em PARALELO:
        │   ├── D5: Test Runner (apos D4 completar)
        │   ├── D6: Memory Eval (Render Postgres)
        │   └── D7: Agent Intelligence Report (Render Postgres + API POST)
        │
        └── ESTAGIO 3 — Consolidacao:
            ├── Commits atomicos por dominio
            ├── Relatorio consolidado
            └── git push + gh pr create
```

### Coordenacao

- Cada subagente escreve `/tmp/manutencao-{DATA}/dominio-N-status.json`
- Orquestrador verifica presenca e status de cada JSON
- Dominio falha isoladamente — demais continuam

---

## Estrutura de Pastas

```
.claude/atualizacoes/
  plano_atualizacao.md          ← ESTE ARQUIVO
  prompt_manutencao.md          ← Prompt do orquestrador (3 estagios)
  dominios/                     ← Prompts individuais por dominio
    dominio-1-claude-md.md
    dominio-2-references.md
    dominio-3-memorias.md
    dominio-4-sentry.md
    dominio-5-tests.md
    dominio-6-memory-eval.md
    dominio-7-agent-report.md
  claude_md/
    README.md                   ← Manual: como atualizar CLAUDE.md
    historico.md                ← Indice de todas as atualizacoes
    atualizacao-YYYY-MM-DD-N.md ← Relatorios individuais
  references/
    README.md
    historico.md
    atualizacao-YYYY-MM-DD-N.md
  memorias/
    README.md
    historico.md
    atualizacao-YYYY-MM-DD-N.md
  sentry/
    README.md
    historico.md
    atualizacao-YYYY-MM-DD-N.md
  tests/
    historico.md
    atualizacao-YYYY-MM-DD-N.md
  memory-eval/
    historico.md
    atualizacao-YYYY-MM-DD-N.md
  agent-reports/
    README.md                   ← Manual do D7
    historico.md                ← Indice de relatorios
    report-YYYY-MM-DD.md        ← Relatorios semanais (bridge Agent <-> Claude Code)
  atualizacao-YYYY-MM-DD-consolidado.md  ← Relatorio consolidado por execucao
```

---

## Instrucoes Obrigatorias

1. **NUNCA modificar arquivos sem gerar relatorio** — toda alteracao deve ter `atualizacao-*.md` correspondente
2. **NUNCA deletar sem justificativa** — relatorio deve explicar por que foi removido
3. **Relatorios devem ser auto-contidos** — qualquer pessoa deve entender o que mudou lendo apenas o relatorio
4. **Historico.md atualizado a cada execucao** — entrada com data, numero sequencial e resumo (max 5 linhas)
5. **Commits atomicos por dominio** — 1 commit por dominio, mensagem descritiva
6. **Status JSON obrigatorio** — cada dominio DEVE escrever status.json em `/tmp/`

---

## Sequencia de Execucao

```
ESTAGIO 1 (paralelo):
  D1 CLAUDE.md  ─┬─ Esperar todos
  D2 References  │
  D3 Memorias    │
  D4 Sentry     ─┘

ESTAGIO 2 (paralelo):
  D5 Tests           ─┬─ Esperar todos
  D6 Memory Eval      │
  D7 Agent Report    ─┘

ESTAGIO 3 (sequencial):
  Consolidar → Commit → Push → PR
```

Cada dominio segue o ciclo: **Avaliar → Atualizar → Relatorio → Status JSON**

---

## Configuracao Crontab

Gerenciado via `sudo crontab -u rafaelnascimento -l`. Logs em `/tmp/claude-cron-*.log`.

### D1-D7: Manutencao Semanal

| Campo | Valor |
|-------|-------|
| Cron | `0 10 * * 1` (segundas 10:00 BRT) |
| Comando | `claude -p "$(cat .claude/atualizacoes/prompt_manutencao.md)" --model opus --permission-mode bypassPermissions` |
| Log | `/tmp/claude-cron-semanal-YYYY-MM-DD.log` |

### D8: Improvement Dialogue (diario)

| Campo | Valor |
|-------|-------|
| Cron | `3 11 * * *` (diario 11:03 BRT) |
| Comando | `/home/rafaelnascimento/projetos/frete_sistema/scripts/maintenance/run_d8_cron.sh` |
| Wrapper | `scripts/maintenance/run_d8_cron.sh` — source `.profile` (CRON_API_KEY), cd no projeto, valida CLI, log em `/tmp/claude-cron-d8-YYYY-MM-DD.log` |
| Log | `/tmp/claude-cron-d8-YYYY-MM-DD.log` (auto pelo wrapper) |
| Workflow | `feature-dev` para implementacoes |
| Branch | `main` (commit direto, sem branch dedicada — preferencia usuario 2026-04-14) |

### RemoteTriggers (DESABILITADOS)

Migrados para crontab local em 31/03/2026. Sem acesso a MCP servers locais.

| ID | Nome | Status |
|----|------|--------|
| `trig_016x6pEVKZPrnKCpmpmDKDum` | Manutencao Semanal (v1, apenas D1-D2) | Desabilitado |
| `trig_01MCebVrnEgw7JWivdyjUria` | D8 Improvement Dialogue | Desabilitado |

Gerenciar: https://claude.ai/code/scheduled

---

## Historico de Versoes

| Data | Versao | O que mudou |
|------|--------|-------------|
| 27/03/2026 | v1 | Criacao — 3 dominios sequenciais + RemoteTrigger |
| 28/03/2026 | v2 | Orquestrador Paralelo — 6 dominios, 3 estagios, RemoteTrigger desabilitado |
| 28/03/2026 | v3 | Agent Intelligence Report — D7 adicionado (bridge Agent SDK <-> Claude Code), Estagio 2 de 2→3 agentes |
| 31/03/2026 | v4 | Improvement Dialogue — D8 adicionado + migracao de OpenClaw/RemoteTrigger para crontab local (WSL2) |
| 14/04/2026 | v5 | D8 fix cronico — wrapper `run_d8_cron.sh` (CRON_API_KEY via .profile), commit D8 direto em main (sem branch dedicada), PASSO 5 reordenado (relatorio antes de commit), push automatico |
