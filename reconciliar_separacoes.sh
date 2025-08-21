#!/bin/bash
# Script de Reconciliação de Separações com NFs
# Executa o job de reconciliação com facilidade

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}🔄 RECONCILIAÇÃO SEPARAÇÃO x NF${NC}"
echo -e "${GREEN}================================================${NC}"

# Verificar se Python está disponível
if ! command -v python &> /dev/null; then
    echo -e "${RED}❌ Python não encontrado!${NC}"
    exit 1
fi

# Ativar ambiente virtual se existir
if [ -f "venv/bin/activate" ]; then
    echo -e "${YELLOW}🐍 Ativando ambiente virtual...${NC}"
    source venv/bin/activate
elif [ -f ".venv/bin/activate" ]; then
    echo -e "${YELLOW}🐍 Ativando ambiente virtual...${NC}"
    source .venv/bin/activate
fi

# Criar diretório de logs se não existir
mkdir -p logs

# Verificar argumentos
if [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "Uso: ./reconciliar_separacoes.sh [opções]"
    echo ""
    echo "Opções:"
    echo "  --dias N       Número de dias retroativos (padrão: 30)"
    echo "  --lote ID      Verificar lote específico"
    echo "  --dry-run      Modo simulação (não salva alterações)"
    echo "  --help         Mostra esta ajuda"
    echo ""
    echo "Exemplos:"
    echo "  ./reconciliar_separacoes.sh                    # Últimos 30 dias"
    echo "  ./reconciliar_separacoes.sh --dias 7           # Últimos 7 dias"
    echo "  ./reconciliar_separacoes.sh --lote SEP001      # Verificar lote específico"
    echo "  ./reconciliar_separacoes.sh --dry-run          # Modo simulação"
    exit 0
fi

# Executar reconciliação
echo -e "${YELLOW}🚀 Iniciando reconciliação...${NC}"
python executar_reconciliacao.py "$@"

# Verificar resultado
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Reconciliação concluída com sucesso!${NC}"
else
    echo -e "${RED}❌ Erro durante a reconciliação. Verifique os logs.${NC}"
    exit 1
fi