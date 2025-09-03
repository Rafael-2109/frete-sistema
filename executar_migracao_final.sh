#!/bin/bash
# =====================================================
# SCRIPT DE MIGRAÇÃO FINAL: Pedido → VIEW
# Data: 2025-01-29
# 
# Ordem de execução:
# 1. Backup do banco
# 2. Adicionar campos em Separacao (incluindo cotacao_id)
# 3. Migrar dados de Pedido → Separacao
# 4. Criar VIEW pedidos com ID determinístico
# =====================================================

echo "=========================================="
echo "MIGRAÇÃO FINAL: Transformar Pedido em VIEW"
echo "=========================================="
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 1. VERIFICAR AMBIENTE
echo -e "${YELLOW}[1/7] Verificando ambiente...${NC}"

# Tentar carregar do .env se existir (ambiente local)
if [ -f ".env" ]; then
    echo "📁 Arquivo .env encontrado, carregando variáveis..."
    export $(cat .env | grep -v '^#' | xargs)
fi

# Verificar se DATABASE_URL está disponível
if [ -z "$DATABASE_URL" ]; then
    echo -e "${RED}❌ DATABASE_URL não encontrada${NC}"
    echo ""
    echo "📋 Opções:"
    echo "1. Se está no Render: DATABASE_URL já deveria estar configurada"
    echo "2. Se está local: Verifique o arquivo .env"
    echo "3. Ou execute: export DATABASE_URL='postgresql://...'"
    exit 1
fi

# Ocultar senha na exibição
DB_DISPLAY=$(echo $DATABASE_URL | sed 's/:\/\/[^:]*:[^@]*@/:\/\/***:***@/')
echo -e "${GREEN}✅ Ambiente configurado${NC}"
echo -e "   Banco: $DB_DISPLAY"
echo ""

# 2. BACKUP DO BANCO
echo -e "${YELLOW}[2/7] Criando backup do banco...${NC}"
BACKUP_FILE="backup_migracao_pedido_view_$(date +%Y%m%d_%H%M%S).sql"
pg_dump $DATABASE_URL > $BACKUP_FILE
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Backup criado: $BACKUP_FILE${NC}"
else
    echo -e "${RED}❌ Erro ao criar backup${NC}"
    exit 1
fi
echo ""

# 3. ADICIONAR CAMPOS EM SEPARACAO (sql_render_modular.sql)
echo -e "${YELLOW}[3/7] Adicionando campos básicos em Separacao...${NC}"
psql $DATABASE_URL < sql_render_modular.sql
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Campos básicos adicionados${NC}"
else
    echo -e "${RED}❌ Erro ao adicionar campos básicos${NC}"
    echo "Verifique o arquivo sql_render_modular.sql"
    exit 1
fi
echo ""

# 4. ADICIONAR COTACAO_ID EM SEPARACAO
echo -e "${YELLOW}[4/7] Adicionando cotacao_id em Separacao...${NC}"
psql $DATABASE_URL << 'EOF'
-- Adicionar campo cotacao_id
ALTER TABLE separacao 
ADD COLUMN IF NOT EXISTS cotacao_id INTEGER REFERENCES cotacoes(id);

-- Criar índice
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sep_cotacao_id 
ON separacao(cotacao_id)
WHERE cotacao_id IS NOT NULL;

-- Verificar
SELECT 
    COUNT(*) as total_campos_adicionados
FROM information_schema.columns
WHERE table_name = 'separacao'
AND column_name = 'cotacao_id';
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Campo cotacao_id adicionado${NC}"
else
    echo -e "${RED}❌ Erro ao adicionar cotacao_id${NC}"
    exit 1
fi
echo ""

# 5. MIGRAR DADOS DE PEDIDO PARA SEPARACAO
echo -e "${YELLOW}[5/7] Migrando dados de Pedido para Separacao...${NC}"

# Primeiro, migrar dados via SQL direto (mais eficiente)
psql $DATABASE_URL << 'EOF'
-- Migrar dados de pedidos para separacao
UPDATE separacao s
SET 
    -- Status e controles
    status = COALESCE(p.status, 'ABERTO'),
    nf_cd = COALESCE(p.nf_cd, FALSE),
    data_embarque = p.data_embarque,
    
    -- Normalização
    cidade_normalizada = p.cidade_normalizada,
    uf_normalizada = p.uf_normalizada,
    codigo_ibge = p.codigo_ibge,
    
    -- Impressão
    separacao_impressa = COALESCE(p.separacao_impressa, FALSE),
    separacao_impressa_em = p.separacao_impressa_em,
    separacao_impressa_por = p.separacao_impressa_por,
    
    -- Cotação
    cotacao_id = p.cotacao_id
    
FROM pedidos p
WHERE s.separacao_lote_id = p.separacao_lote_id
AND s.separacao_lote_id IS NOT NULL;

-- Verificar resultado
SELECT 
    COUNT(*) as registros_atualizados,
    COUNT(DISTINCT separacao_lote_id) as lotes_atualizados,
    COUNT(cotacao_id) as com_cotacao
FROM separacao
WHERE separacao_lote_id IS NOT NULL;
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Dados migrados com sucesso${NC}"
else
    echo -e "${RED}❌ Erro na migração de dados${NC}"
    exit 1
fi
echo ""

# 6. CRIAR VIEW PEDIDOS
echo -e "${YELLOW}[6/7] Criando VIEW pedidos com ID determinístico...${NC}"

# Renomear tabela original e criar VIEW
psql $DATABASE_URL < sql_criar_view_pedidos_final.sql
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ VIEW pedidos criada com sucesso${NC}"
else
    echo -e "${RED}❌ Erro ao criar VIEW${NC}"
    echo "Verifique o arquivo sql_criar_view_pedidos_final.sql"
    exit 1
fi
echo ""

# 7. ATUALIZAR MODELO PYTHON
echo -e "${YELLOW}[7/7] Atualizando modelo Python...${NC}"

# Fazer backup do modelo original
if [ -f "app/pedidos/models.py" ]; then
    cp app/pedidos/models.py app/pedidos/models_backup_$(date +%Y%m%d_%H%M%S).py
    echo -e "${GREEN}✅ Backup do modelo criado${NC}"
fi

# Substituir pelo adapter (se existir)
if [ -f "app/pedidos/models_adapter.py" ]; then
    cp app/pedidos/models_adapter.py app/pedidos/models.py
    echo -e "${GREEN}✅ Modelo Pedido atualizado para usar VIEW${NC}"
else
    echo -e "${YELLOW}⚠️ Arquivo models_adapter.py não encontrado${NC}"
    echo "Você precisará atualizar o modelo manualmente"
fi
echo ""

# VALIDAÇÃO FINAL
echo -e "${YELLOW}Executando validações...${NC}"
psql $DATABASE_URL << 'EOF'
-- Comparar totais
SELECT 
    'pedidos_backup' as fonte,
    COUNT(*) as total
FROM pedidos_backup
UNION ALL
SELECT 
    'pedidos VIEW' as fonte,
    COUNT(*) as total
FROM pedidos;

-- Testar ID determinístico
SELECT 
    'IDs únicos' as teste,
    CASE 
        WHEN COUNT(DISTINCT id) = COUNT(DISTINCT separacao_lote_id) 
        THEN 'OK' 
        ELSE 'ERRO' 
    END as resultado
FROM pedidos;
EOF

# RESUMO FINAL
echo ""
echo "=========================================="
echo -e "${GREEN}MIGRAÇÃO CONCLUÍDA!${NC}"
echo "=========================================="
echo ""
echo "✅ Backup criado: $BACKUP_FILE"
echo "✅ Campos adicionados em Separacao (incluindo cotacao_id)"
echo "✅ Dados migrados de Pedido → Separacao"
echo "✅ VIEW pedidos criada com ID determinístico"
echo ""
echo -e "${YELLOW}PRÓXIMOS PASSOS:${NC}"
echo "1. Testar a aplicação completamente"
echo "2. Verificar que Pedido.query.get(id) funciona"
echo "3. Verificar que cotações funcionam corretamente"
echo "4. Após validação, executar:"
echo "   - DROP TABLE pedidos_backup;"
echo "   - DROP TABLE pre_separacao_item;"
echo ""
echo -e "${YELLOW}ROLLBACK (se necessário):${NC}"
echo "psql \$DATABASE_URL < $BACKUP_FILE"
echo "