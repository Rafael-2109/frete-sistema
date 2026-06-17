#!/usr/bin/env bash
# Helper compartilhado: prepara a worktree dedicada da manutencao (D8 + semanal).
#
# SOURCED por run_d8_cron.sh e run_semanal_cron.sh APOS PROJECT_DIR e LOG_FILE
# estarem definidos. NAO executar diretamente.
#
# Objetivo: isolar os crons de manutencao da arvore de trabalho principal do dev.
# Os crons rodam numa worktree compartilhada, na branch `cron/manutencao`, e
# NAO fazem push — os commits acumulam ali para o Rafael revisar e integrar
# manualmente (fluxo 4-maos). Detalhe: .claude/atualizacoes/plano_atualizacao.md.
#
# Contrato:
#   Entrada: PROJECT_DIR (arvore principal), LOG_FILE (opcional, p/ logar)
#   Saida:   exporta WORKTREE_DIR (cwd alvo do claude -p); vazio se falhar
#   Efeito:  cria/sincroniza a worktree idempotentemente; symlink .venv + copia .env
#
# Best-effort: nunca derruba o wrapper por falha de sync (so loga e segue no
# estado atual). A unica falha fatal e a worktree nao existir apos o setup.

WORKTREE_DIR="/home/rafaelnascimento/projetos/frete_sistema_manutencao"
WORKTREE_BRANCH="cron/manutencao"

# Log local (usa LOG_FILE se definido, senao stderr)
_wt_log() {
    if [ -n "${LOG_FILE:-}" ]; then
        echo "[setup_worktree] $*" >> "$LOG_FILE"
    else
        echo "[setup_worktree] $*" >&2
    fi
}

# 1. Trazer refs atualizadas do remoto (a partir da arvore principal)
if git -C "$PROJECT_DIR" fetch origin main --quiet; then
    _wt_log "fetch origin main OK"
else
    _wt_log "WARN: fetch origin main falhou (seguindo offline)"
fi

# 2. Criar a worktree se nao existir (idempotente)
if [ ! -d "$WORKTREE_DIR" ]; then
    if git -C "$PROJECT_DIR" show-ref --verify --quiet "refs/heads/$WORKTREE_BRANCH"; then
        # Branch ja existe (worktree foi removida mas a branch persistiu)
        if git -C "$PROJECT_DIR" worktree add "$WORKTREE_DIR" "$WORKTREE_BRANCH"; then
            _wt_log "worktree recriada na branch existente $WORKTREE_BRANCH"
        else
            _wt_log "ERRO: falha ao recriar worktree na branch $WORKTREE_BRANCH"
        fi
    else
        if git -C "$PROJECT_DIR" worktree add "$WORKTREE_DIR" -b "$WORKTREE_BRANCH" origin/main; then
            _wt_log "worktree criada (nova branch $WORKTREE_BRANCH de origin/main)"
        else
            _wt_log "ERRO: falha ao criar worktree+branch $WORKTREE_BRANCH"
        fi
    fi
else
    _wt_log "worktree ja existe em $WORKTREE_DIR"
fi

# Guard: sem worktree, o claude rodaria na arvore errada — abortar.
if [ ! -d "$WORKTREE_DIR" ]; then
    _wt_log "ERRO FATAL: WORKTREE_DIR inexistente apos setup"
    export WORKTREE_DIR=""
    return 1 2>/dev/null || exit 1
fi

# 3. Sincronizar com origin/main preservando commits acumulados (rebase best-effort).
#    Pula se a working tree estiver suja (resto de run morto) — nao arriscar perder
#    trabalho nem entrar em rebase conflitante automatico.
if [ -n "$(git -C "$WORKTREE_DIR" status --porcelain)" ]; then
    _wt_log "WARN: working tree suja na worktree — pulando sync (rebase)"
else
    if git -C "$WORKTREE_DIR" rebase origin/main --quiet; then
        _wt_log "rebase em origin/main OK"
    else
        _wt_log "WARN: rebase em origin/main conflitou — abortando, seguindo no estado atual"
        git -C "$WORKTREE_DIR" rebase --abort 2>/dev/null || true
    fi
fi

# 4. Ambiente Python: symlink .venv (path absoluto da raiz) + copia .env (gitignored).
#    Sem isso, create_app cai em SQLite e o D5 (testes) roda no banco errado.
if [ -d "$PROJECT_DIR/.venv" ]; then
    if ln -sfn "$PROJECT_DIR/.venv" "$WORKTREE_DIR/.venv"; then
        _wt_log ".venv symlinkada"
    else
        _wt_log "WARN: falha ao symlinkar .venv"
    fi
fi
if [ -f "$PROJECT_DIR/.env" ]; then
    if cp -f "$PROJECT_DIR/.env" "$WORKTREE_DIR/.env"; then
        _wt_log ".env copiado"
    else
        _wt_log "WARN: falha ao copiar .env"
    fi
fi

export WORKTREE_DIR
_wt_log "pronto — WORKTREE_DIR=$WORKTREE_DIR branch=$WORKTREE_BRANCH"
