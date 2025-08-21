#!/bin/bash
# Script para aplicar migrations SQL

# Configurações do banco (AJUSTE CONFORME SEU AMBIENTE)
DB_HOST="localhost"
DB_PORT="5432"
DB_NAME="frete_sistema"
DB_USER="postgres"

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

echo "======================================"
echo "🔧 APLICANDO MIGRATIONS SQL"
echo "======================================"

# Verificar se o arquivo existe
if [ ! -f "migrations/add_sync_flags_separacao.sql" ]; then
    echo -e "${RED}❌ Arquivo migrations/add_sync_flags_separacao.sql não encontrado!${NC}"
    exit 1
fi

echo "📋 Banco: $DB_NAME"
echo "👤 Usuário: $DB_USER"
echo ""

# Pedir confirmação
read -p "Deseja aplicar as migrations? (s/n): " resposta

if [ "$resposta" != "s" ] && [ "$resposta" != "S" ]; then
    echo "Operação cancelada"
    exit 0
fi

# Executar migration
echo ""
echo "🚀 Aplicando migrations..."

psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f migrations/add_sync_flags_separacao.sql

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Migrations aplicadas com sucesso!${NC}"
    
    # Verificar se as colunas foram criadas
    echo ""
    echo "🔍 Verificando colunas criadas..."
    psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'separacao' AND column_name IN ('sincronizado_nf', 'numero_nf', 'data_sincronizacao', 'zerado_por_sync', 'data_zeragem');"
else
    echo -e "${RED}❌ Erro ao aplicar migrations${NC}"
    exit 1
fi