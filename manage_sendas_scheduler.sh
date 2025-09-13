#!/bin/bash

# Script para gerenciar o scheduler da fila Sendas

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/sendas_scheduler.pid"
LOG_FILE="$SCRIPT_DIR/logs/sendas_scheduler.log"

# Criar diretório de logs se não existir
mkdir -p "$SCRIPT_DIR/logs"

start_scheduler() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "❌ Scheduler já está rodando com PID $PID"
            exit 1
        fi
    fi
    
    echo "🚀 Iniciando Scheduler da Fila Sendas..."
    
    # Carregar variáveis de ambiente
    if [ -f "$SCRIPT_DIR/.env" ]; then
        export $(cat "$SCRIPT_DIR/.env" | grep -v '^#' | xargs)
    fi
    
    # Iniciar scheduler em background
    nohup python3 "$SCRIPT_DIR/start_sendas_scheduler.py" > "$LOG_FILE" 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"
    
    echo "✅ Scheduler iniciado com PID $PID"
    echo "📋 Logs em: $LOG_FILE"
    echo ""
    echo "Comandos disponíveis:"
    echo "  ./manage_sendas_scheduler.sh status  - Ver status"
    echo "  ./manage_sendas_scheduler.sh stop    - Parar scheduler"
    echo "  ./manage_sendas_scheduler.sh logs    - Ver logs"
}

stop_scheduler() {
    if [ ! -f "$PID_FILE" ]; then
        echo "⚠️ PID file não encontrado. Scheduler não está rodando?"
        exit 1
    fi
    
    PID=$(cat "$PID_FILE")
    
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "🛑 Parando Scheduler (PID $PID)..."
        kill "$PID"
        rm -f "$PID_FILE"
        echo "✅ Scheduler parado"
    else
        echo "⚠️ Processo $PID não encontrado"
        rm -f "$PID_FILE"
    fi
}

status_scheduler() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            echo "✅ Scheduler está rodando com PID $PID"
            echo ""
            echo "Informações do processo:"
            ps -fp "$PID"
            echo ""
            echo "Últimas linhas do log:"
            tail -n 10 "$LOG_FILE"
        else
            echo "❌ Scheduler não está rodando (PID $PID não encontrado)"
            rm -f "$PID_FILE"
        fi
    else
        echo "❌ Scheduler não está rodando (sem PID file)"
    fi
}

view_logs() {
    if [ -f "$LOG_FILE" ]; then
        echo "📋 Mostrando logs do Scheduler Sendas:"
        echo "----------------------------------------"
        tail -f "$LOG_FILE"
    else
        echo "⚠️ Arquivo de log não encontrado: $LOG_FILE"
    fi
}

case "$1" in
    start)
        start_scheduler
        ;;
    stop)
        stop_scheduler
        ;;
    restart)
        stop_scheduler
        sleep 2
        start_scheduler
        ;;
    status)
        status_scheduler
        ;;
    logs)
        view_logs
        ;;
    *)
        echo "Uso: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "Comandos:"
        echo "  start   - Iniciar o scheduler"
        echo "  stop    - Parar o scheduler"
        echo "  restart - Reiniciar o scheduler"
        echo "  status  - Ver status do scheduler"
        echo "  logs    - Ver logs em tempo real"
        exit 1
        ;;
esac