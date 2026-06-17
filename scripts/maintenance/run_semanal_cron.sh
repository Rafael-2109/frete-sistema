#!/usr/bin/env bash
# Wrapper para executar a Manutencao Semanal (D1-D7) via systemd-timer.
#
# Espelha run_d8_cron.sh. Resolve os mesmos bugs cronicos de cron:
#   1. CRON_API_KEY vazia (cron/systemd nao source .profile por default)
#   2. PATH incompleto (claude CLI nao achado)
#   3. Working directory errado (paths relativos falham)
#   4. Log nao redirecionado consistentemente
#
# Usado por: ~/.config/systemd/user/claude-semanal.service
#   (OnCalendar=Mon *-*-* 10:00:00, Persistent=true -> catch-up)
# Antes vivia no crontab: 0 10 * * 1 ... claude -p prompt_manutencao.md
# (migrado em 2026-06-12 — cron WSL2 nao tem catch-up; systemd Persistent tem)

set -u  # falha se variavel nao definida (ajuda a detectar CRON_API_KEY vazia)

# 1. Source do .profile para pegar CRON_API_KEY e outras envs do usuario
if [ -f "$HOME/.profile" ]; then
    # shellcheck source=/dev/null
    source "$HOME/.profile"
fi

# Fallback: se .bashrc tambem define, extrair so a var (interactive guard impede source completo)
if [ -z "${CRON_API_KEY:-}" ] && [ -f "$HOME/.bashrc" ]; then
    # shellcheck disable=SC2046
    export CRON_API_KEY="$(grep '^export CRON_API_KEY=' "$HOME/.bashrc" | head -1 | sed -E 's/^export CRON_API_KEY="?([^"]*)"?/\1/')"
fi

# 2. PATH minimo (cron/systemd tem PATH reduzido); claude CLI fica em ~/.local/bin
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# 3. cd para o projeto (paths relativos funcionam)
PROJECT_DIR="/home/rafaelnascimento/projetos/frete_sistema"
cd "$PROJECT_DIR" || {
    echo "ERRO: nao foi possivel cd para $PROJECT_DIR" >&2
    exit 1
}

# 4. Log com data
DATA="$(date +%Y-%m-%d)"
LOG_FILE="/tmp/claude-cron-semanal-${DATA}.log"
# Prompt lido da ARVORE PRINCIPAL (canonico) — a execucao do claude ocorre na
# worktree dedicada (cd adiante). Assim editar o prompt vale na hora, sem push.
PROMPT_FILE="$PROJECT_DIR/.claude/atualizacoes/prompt_manutencao.md"

# 5. Validacoes antes de disparar o claude -p
{
    echo "========================================"
    echo "Manutencao Semanal (D1-D7) — ${DATA}"
    echo "Iniciado em: $(date -Iseconds)"
    echo "PWD: $PWD"
    echo "PATH: $PATH"
    echo "CRON_API_KEY: ${CRON_API_KEY:+SET (${#CRON_API_KEY} chars)}${CRON_API_KEY:-UNSET (persistencia no DB sera pulada)}"
    echo "claude CLI: $(command -v claude || echo 'NAO ENCONTRADO')"
    echo "========================================"
    echo ""
} > "$LOG_FILE" 2>&1

if [ ! -f "$PROMPT_FILE" ]; then
    echo "ERRO: prompt file $PROMPT_FILE nao encontrado em $PWD" >> "$LOG_FILE"
    exit 2
fi

if ! command -v claude > /dev/null 2>&1; then
    echo "ERRO: claude CLI nao esta no PATH" >> "$LOG_FILE"
    exit 3
fi

# 5.5 Lock exclusivo + worktree dedicada
# D8 e semanal compartilham a worktree de manutencao — flock impede execucao
# concorrente (corromperia o working tree / cruzaria commits).
LOCKFILE="/tmp/claude-manutencao-worktree.lock"
exec 9>"$LOCKFILE"
if ! flock -w 1800 9; then
    echo "ERRO: timeout (1800s) aguardando lock da worktree — outro fluxo de manutencao em execucao" >> "$LOG_FILE"
    exit 4
fi

# Preparar/sincronizar a worktree compartilhada (branch cron/manutencao, SEM push).
# shellcheck source=_setup_worktree.sh
source "$PROJECT_DIR/scripts/maintenance/_setup_worktree.sh"

if [ -z "${WORKTREE_DIR:-}" ] || [ ! -d "$WORKTREE_DIR" ]; then
    echo "ERRO: worktree de manutencao indisponivel — abortando" >> "$LOG_FILE"
    exit 5
fi

cd "$WORKTREE_DIR" || {
    echo "ERRO: nao foi possivel cd para worktree $WORKTREE_DIR" >> "$LOG_FILE"
    exit 6
}

{
    echo ""
    echo "Worktree de execucao: $PWD"
    echo "Branch: $(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
    echo ""
} >> "$LOG_FILE"

# 6. Executar a manutencao semanal com o prompt orquestrador (cwd = worktree)
claude -p "$(cat "$PROMPT_FILE")" \
    --model opus \
    --permission-mode bypassPermissions \
    >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

{
    echo ""
    echo "========================================"
    echo "Manutencao Semanal finalizada em: $(date -Iseconds)"
    echo "Exit code: $EXIT_CODE"
    echo "========================================"
} >> "$LOG_FILE"

exit $EXIT_CODE
