# Plano de Atualizacao Automatizada

**Criado**: 27/03/2026
**Atualizado**: 28/03/2026 (v2 — Orquestrador Paralelo)
**Frequencia**: Semanal (segunda-feira, 10:00 BRT)
**Executor**: OpenClaw Cron → Claude Code (Opus)

---

## Visao Geral

Tarefa agendada que executa **6 dominios** de manutencao em **3 estagios paralelos**, gerando relatorios rastreaveis para cada execucao e um relatorio consolidado.

**Scheduler unico**: OpenClaw (local). RemoteTrigger desabilitado em 28/03/2026.

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
        ├── ESTAGIO 2 — 2 Agent calls em PARALELO:
        │   ├── D5: Test Runner (apos D4 completar)
        │   └── D6: Memory Eval (Render Postgres)
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
  D5 Tests      ─┬─ Esperar ambos
  D6 Memory Eval─┘

ESTAGIO 3 (sequencial):
  Consolidar → Commit → Push → PR
```

Cada dominio segue o ciclo: **Avaliar → Atualizar → Relatorio → Status JSON**

---

## Configuracao OpenClaw

| Campo | Valor |
|-------|-------|
| ID | `04c21701-6c01-44ac-b7ac-592f15f541f7` |
| Nome | `Manutencao Semanal - Orquestrador Paralelo` |
| Schedule | `0 10 * * 1` (segundas 10:00) |
| Model | `anthropic/claude-opus-4-6` |
| Timeout | 2400s (40 min) |
| Session | isolated |
| Budget | sem limite |

---

## Historico de Versoes

| Data | Versao | O que mudou |
|------|--------|-------------|
| 27/03/2026 | v1 | Criacao — 3 dominios sequenciais + RemoteTrigger |
| 28/03/2026 | v2 | Orquestrador Paralelo — 6 dominios, 3 estagios, RemoteTrigger desabilitado |
