# Plano de Atualizacao Automatizada

**Criado**: 27/03/2026
**Frequencia**: Semanal (segunda-feira, 08:00 BRT)
**Executor**: Claude Code Scheduled Task

---

## Visao Geral

Tarefa agendada que executa 4 dominios de manutencao do projeto de forma autonoma, gerando relatorios rastreaveis para cada execucao.

---

## Dominios

| # | Dominio | Pasta | Manual | O que faz |
|---|---------|-------|--------|-----------|
| 1 | **CLAUDE.md** | [`claude_md/`](claude_md/) | [`README.md`](claude_md/README.md) | Audita e atualiza os 9 arquivos CLAUDE.md contra o estado atual do codigo |
| 2 | **References** | [`references/`](references/) | [`README.md`](references/README.md) | Revisa 326 arquivos em `.claude/references/` para precisao e melhores praticas |
| 3 | **Memorias** | [`memorias/`](memorias/) | [`README.md`](memorias/README.md) | Avalia, reorganiza e limpa os 30 arquivos de memoria seguindo best practices Anthropic |
| 4 | **Sentry** | [`sentry/`](sentry/) | [`README.md`](sentry/README.md) | Avalia issues do Sentry, corrige bugs e gera relatorio do que foi feito |

---

## Estrutura de Pastas

```
.claude/atualizacoes/
  plano_atualizacao.md          ← ESTE ARQUIVO (ponteiro raiz)
  claude_md/
    README.md                   ← Manual: como atualizar CLAUDE.md
    historico.md                ← Indice de todas as atualizacoes
    atualizacao-YYYY-MM-DD-N.md ← Relatorios individuais
  references/
    README.md                   ← Manual: como atualizar references
    historico.md                ← Indice de todas as atualizacoes
    atualizacao-YYYY-MM-DD-N.md ← Relatorios individuais
  memorias/
    README.md                   ← Manual: como reorganizar memorias
    historico.md                ← Indice de todas as atualizacoes
    atualizacao-YYYY-MM-DD-N.md ← Relatorios individuais
  sentry/
    README.md                   ← Manual: como triar e corrigir Sentry
    historico.md                ← Indice de todas as atualizacoes
    atualizacao-YYYY-MM-DD-N.md ← Relatorios individuais
```

---

## Instrucoes Obrigatorias

1. **NUNCA modificar arquivos sem gerar relatorio** — toda alteracao deve ter `atualizacao-*.md` correspondente
2. **NUNCA deletar sem justificativa** — relatorio deve explicar por que foi removido
3. **Relatorios devem ser auto-contidos** — qualquer pessoa deve entender o que mudou lendo apenas o relatorio
4. **Historico.md atualizado a cada execucao** — entrada com data, numero sequencial e resumo (max 5 linhas)
5. **Commits atomicos por dominio** — 1 commit por dominio, mensagem descritiva

---

## Sequencia de Execucao

```
1. CLAUDE.md    → Auditar 9 arquivos contra codigo atual
2. References   → Revisar referencias desatualizadas
3. Memorias     → Avaliar, consolidar e limpar memorias
4. Sentry       → Triar issues, corrigir bugs, reportar
```

Cada dominio segue o ciclo: **Avaliar → Atualizar → Relatorio → Commit**

---

## Arquivos-Alvo por Dominio

### 1. CLAUDE.md (9 arquivos)
- `CLAUDE.md` (raiz)
- `app/agente/CLAUDE.md`
- `app/agente/services/CLAUDE.md`
- `app/carteira/CLAUDE.md`
- `app/carvia/CLAUDE.md`
- `app/financeiro/CLAUDE.md`
- `app/odoo/CLAUDE.md`
- `app/seguranca/CLAUDE.md`
- `app/teams/CLAUDE.md`

### 2. References (12 grupos, 326 arquivos)
- `.claude/references/` (12 root files)
- `.claude/references/design/` (2 files)
- `.claude/references/linx/` (1 file)
- `.claude/references/modelos/` (4 files)
- `.claude/references/negocio/` (6 files)
- `.claude/references/odoo/` (8 files)
- `.claude/references/ssw/` (298 files, 10 subdirs)

### 3. Memorias (30 arquivos)
- `/home/rafaelnascimento/.claude/projects/-home-rafaelnascimento-projetos-frete-sistema/memory/`

### 4. Sentry
- Organizacao: `nacom`
- Projeto: `python-flask`
- Escopo: issues nao resolvidas com prioridade alta
