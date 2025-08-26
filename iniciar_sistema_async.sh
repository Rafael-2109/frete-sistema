#!/bin/bash
# Script para iniciar o sistema com suporte assíncrono
# Uso: ./iniciar_sistema_async.sh

echo "=========================================="
echo "🚀 INICIANDO SISTEMA DE FRETES COM REDIS"
echo "=========================================="
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. Verificar Redis
echo "1️⃣ Verificando Redis..."
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✅ Redis está rodando${NC}"
else
    echo -e "${YELLOW}⚠️ Redis não encontrado. Tentando iniciar...${NC}"
    
    # Tentar iniciar Redis
    if command -v systemctl &> /dev/null; then
        sudo systemctl start redis-server
    elif command -v brew &> /dev/null; then
        brew services start redis
    else
        echo -e "${RED}❌ Não foi possível iniciar Redis automaticamente${NC}"
        echo "Por favor, inicie o Redis manualmente e tente novamente"
        exit 1
    fi
    
    sleep 2
    
    if redis-cli ping > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Redis iniciado com sucesso${NC}"
    else
        echo -e "${RED}❌ Falha ao iniciar Redis${NC}"
        exit 1
    fi
fi

# 2. Instalar dependências (se necessário)
echo ""
echo "2️⃣ Verificando dependências Python..."
if ! python -c "import rq" 2>/dev/null; then
    echo -e "${YELLOW}⚠️ Instalando Redis Queue...${NC}"
    pip install rq==1.16.1 rq-dashboard==0.6.1
    echo -e "${GREEN}✅ Dependências instaladas${NC}"
else
    echo -e "${GREEN}✅ Dependências já instaladas${NC}"
fi

# 3. Aplicar migração do banco (se necessário)
echo ""
echo "3️⃣ Verificando migração do banco..."
if [ -f "migrations/add_job_id_to_portal_integracoes.sql" ]; then
    echo -e "${YELLOW}ℹ️  Migração SQL disponível em: migrations/add_job_id_to_portal_integracoes.sql${NC}"
    echo "Execute manualmente se ainda não aplicada"
fi

# 4. Iniciar Worker em background
echo ""
echo "4️⃣ Iniciando Worker do Atacadão..."

# Verificar se já está rodando
if pgrep -f "worker_atacadao.py" > /dev/null; then
    echo -e "${YELLOW}⚠️ Worker já está rodando${NC}"
    echo "PIDs encontrados:"
    pgrep -f "worker_atacadao.py"
else
    # Iniciar worker em background
    nohup python worker_atacadao.py > logs/worker_atacadao.log 2>&1 &
    WORKER_PID=$!
    echo -e "${GREEN}✅ Worker iniciado (PID: $WORKER_PID)${NC}"
    echo "Logs em: logs/worker_atacadao.log"
fi

# 5. Verificar status das filas
echo ""
echo "5️⃣ Status das filas:"
python worker_atacadao.py --status

# 6. Iniciar Dashboard (opcional)
echo ""
echo "6️⃣ Dashboard do RQ (opcional):"
echo -e "${YELLOW}Para visualizar o dashboard, execute em outro terminal:${NC}"
echo "   rq-dashboard"
echo "   Acesse: http://localhost:9181"

# 7. Iniciar aplicação Flask
echo ""
echo "7️⃣ Iniciando aplicação Flask..."
echo -e "${GREEN}Execute em outro terminal:${NC}"
echo "   python app.py"
echo "   ou"
echo "   flask run"

echo ""
echo "=========================================="
echo -e "${GREEN}✅ SISTEMA PRONTO!${NC}"
echo "=========================================="
echo ""
echo "📋 Comandos úteis:"
echo "   • Ver logs do worker: tail -f logs/worker_atacadao.log"
echo "   • Parar worker: pkill -f worker_atacadao.py"
echo "   • Status das filas: python worker_atacadao.py --status"
echo "   • Dashboard web: rq-dashboard"
echo ""
echo "🔗 Endpoints assíncronos disponíveis:"
echo "   • POST /portal/api/solicitar-agendamento-async"
echo "   • GET  /portal/api/status-job/{job_id}"
echo "   • GET  /portal/api/status-filas"
echo "   • POST /portal/api/reprocessar-integracao/{id}"
echo ""
echo "📚 Documentação completa: REDIS_QUEUE_GUIA.md"
echo ""