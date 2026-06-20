# Hooks arquivados

Hooks sem wiring em **nenhum** settings (projeto `.claude/settings.json` **e** global
`~/.claude/settings.json`) — confirmado `grep` = 0 em ambos. Arquivados 2026-06-19.

| Hook | Por que arquivado |
|------|-------------------|
| `notificar-alteracao.py` | Auditava edição por keyword em diff (proxy textual fraco); duplica `audit-separacao`; sem consumidor. Docstring afirmava `settings.local.json` (wiring que nunca existiu). |
| `rodar-testes-pos-edicao.py` | Rodava `pytest` inteiro a cada edição `.py` — ROI negativo. Regressão já coberta por `lembrar-regenerar-schemas` + `ban_datetime_now` + lints de pre-commit. |

**Deletados a pedido do dev (2026-06-19 — não usados, "só poluíam"):** `audit-separacao.py`
(estava no global com gate `*separacao*`; removido do `~/.claude/settings.json` junto) e
`validar-pedido-critico.py` (já havia sido removido do global pelo dev). Não estão neste diretório;
recuperáveis via histórico git se necessário.

> ⚠️ **Nota de auditoria (evita confusão):** `lembrar-migration-par` **continua ativo** — wired no
> **`~/.claude/settings.json` (config pessoal/global do dev)**, gate `if` em `scripts/migrations/`.
> O `~/.claude/settings.json` usa entradas `if Edit(...)` + `if Write(...)` por hook (parece "2x" mas
> NÃO é duplicação — é config correta). **Antes de mover/deletar qualquer hook, checar AMBOS os
> settings (projeto `.claude/settings.json` + global `~/.claude/settings.json`).**

Reativar: mover de volta para `.claude/hooks/` **e** adicionar ao settings correto no mesmo commit.
