#!/usr/bin/env bash
# Wrapper para executar o D8 Improvement Dialogue via crontab local.
#
# Objetivo: resolver os bugs cronicos do cron D8:
#   1. CRON_API_KEY vazia (cron nao source .profile por default)
#   2. PATH incompleto (claude CLI nao achado)
#   3. Working directory errado (paths relativos falham)
#   4. Log nao redirecionado consistentemente
#
# Uso no crontab:
#   3 11 * * * /home/rafaelnascimento/projetos/frete_sistema/scripts/maintenance/run_d8_cron.sh
#
# Este wrapper deve ser usado APENAS para D8 (diario). O semanal (D1-D7) tem
# fluxo proprio via prompt_manutencao.md.

set -u  # falha se variavel nao definida (ajuda a detectar CRON_API_KEY vazia)

# -----------------------------------------------------------------------------
# 1. Source do .profile para pegar CRON_API_KEY e outras envs do usuario
# -----------------------------------------------------------------------------
# cron roda com ambiente minimo — source explicito do .profile garante que
# CRON_API_KEY fique disponivel para o claude -p (e para o proprio prompt
# que le via `echo $CRON_API_KEY` no PASSO RENDER API CONFIG).
if [ -f "$HOME/.profile" ]; then
    # shellcheck source=/dev/null
    source "$HOME/.profile"
fi

# Fallback: se .bashrc tambem define, tentar source (alguns setups tem la)
if [ -z "${CRON_API_KEY:-}" ] && [ -f "$HOME/.bashrc" ]; then
    # .bashrc pode ter early-return para non-interactive — usar eval para extrair so a var
    # shellcheck disable=SC2046
    export CRON_API_KEY="$(grep '^export CRON_API_KEY=' "$HOME/.bashrc" | head -1 | sed -E 's/^export CRON_API_KEY="?([^"]*)"?/\1/')"
fi

# -----------------------------------------------------------------------------
# 2. Definir PATH minimo necessario (cron tem PATH muito reduzido por default)
# -----------------------------------------------------------------------------
# claude CLI fica tipicamente em ~/.local/bin ou /usr/local/bin
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin:$PATH"

# -----------------------------------------------------------------------------
# 3. cd para o projeto (paths relativos funcionam)
# -----------------------------------------------------------------------------
PROJECT_DIR="/home/rafaelnascimento/projetos/frete_sistema"
cd "$PROJECT_DIR" || {
    echo "ERRO: nao foi possivel cd para $PROJECT_DIR" >&2
    exit 1
}

# -----------------------------------------------------------------------------
# 4. Log com data
# -----------------------------------------------------------------------------
DATA="$(date +%Y-%m-%d)"
LOG_FILE="/tmp/claude-cron-d8-${DATA}.log"
PROMPT_FILE=".claude/atualizacoes/dominios/dominio-8-improvement-dialogue.md"

# -----------------------------------------------------------------------------
# 5. Validacoes antes de disparar o claude -p
# -----------------------------------------------------------------------------
{
    echo "========================================"
    echo "D8 Improvement Dialogue — ${DATA}"
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

# -----------------------------------------------------------------------------
# 6. Executar D8 com o prompt completo
# -----------------------------------------------------------------------------
claude -p "$(cat "$PROMPT_FILE")" \
    --model opus \
    --permission-mode bypassPermissions \
    >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

{
    echo ""
    echo "========================================"
    echo "D8 finalizado em: $(date -Iseconds)"
    echo "Exit code: $EXIT_CODE"
    echo "========================================"
} >> "$LOG_FILE"

exit $EXIT_CODE
