#!/bin/bash
# =====================================================
# SCRIPT DE MIGRAÇÃO COMPLETA: Pedido → Separacao
# Data: 2025-01-29
# =====================================================

echo "=========================================="
echo "MIGRAÇÃO: Transformar Pedido em VIEW"
echo "=========================================="
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. VERIFICAR AMBIENTE
echo -e "${YELLOW}[1/6] Verificando ambiente...${NC}"
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}❌ DATABASE_URL não configurada${NC}"
    echo "Configure a variável de ambiente DATABASE_URL antes de continuar"
    exit 1
fi
echo -e "${GREEN}✅ Ambiente configurado${NC}"
echo ""

# 2. BACKUP DO BANCO
echo -e "${YELLOW}[2/6] Criando backup do banco...${NC}"
BACKUP_FILE="backup_antes_migracao_$(date +%Y%m%d_%H%M%S).sql"
pg_dump $DATABASE_URL > $BACKUP_FILE
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Backup criado: $BACKUP_FILE${NC}"
else
    echo -e "${RED}❌ Erro ao criar backup${NC}"
    exit 1
fi
echo ""

# 3. ADICIONAR CAMPOS EM SEPARACAO
echo -e "${YELLOW}[3/6] Adicionando campos em Separacao...${NC}"
psql $DATABASE_URL < sql_render_modular.sql
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Campos adicionados em Separacao${NC}"
else
    echo -e "${RED}❌ Erro ao adicionar campos${NC}"
    echo "Verifique o arquivo sql_render_modular.sql"
    exit 1
fi
echo ""

# 4. MIGRAR DADOS DE PEDIDO PARA SEPARACAO
echo -e "${YELLOW}[4/6] Migrando dados de Pedido para Separacao...${NC}"
python3 migrar_dados_pedido_para_separacao.py
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Dados migrados com sucesso${NC}"
else
    echo -e "${RED}❌ Erro na migração de dados${NC}"
    exit 1
fi
echo ""

# 5. CRIAR VIEW PEDIDOS
echo -e "${YELLOW}[5/6] Criando VIEW pedidos...${NC}"
psql $DATABASE_URL < sql_criar_view_pedidos_v3.sql
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ VIEW pedidos criada${NC}"
else
    echo -e "${RED}❌ Erro ao criar VIEW${NC}"
    exit 1
fi
echo ""

# 6. ATUALIZAR CÓDIGO PYTHON
echo -e "${YELLOW}[6/6] Atualizando código Python...${NC}"
# Fazer backup do modelo original
cp app/pedidos/models.py app/pedidos/models_original.py
# Substituir pelo adapter
cp app/pedidos/models_adapter.py app/pedidos/models.py
echo -e "${GREEN}✅ Modelo Pedido atualizado para usar VIEW${NC}"
echo ""

# RESUMO FINAL
echo "=========================================="
echo -e "${GREEN}MIGRAÇÃO CONCLUÍDA COM SUCESSO!${NC}"
echo "=========================================="
echo ""
echo "✅ Campos adicionados em Separacao"
echo "✅ Dados migrados de Pedido → Separacao"
echo "✅ VIEW pedidos criada"
echo "✅ Modelo Python atualizado"
echo ""
echo -e "${YELLOW}PRÓXIMOS PASSOS:${NC}"
echo "1. Testar a aplicação completamente"
echo "2. Verificar se todas as funcionalidades estão OK"
echo "3. Remover tabela pedidos_backup após validação"
echo "4. Remover tabela pre_separacao_item"
echo ""
echo -e "${YELLOW}ROLLBACK (se necessário):${NC}"
echo "1. psql \$DATABASE_URL < $BACKUP_FILE"
echo "2. cp app/pedidos/models_original.py app/pedidos/models.py"
echo ""