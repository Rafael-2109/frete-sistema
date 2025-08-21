#!/bin/bash
# Script de Recuperação de Separações Perdidas
# Reconstrói Separações que foram deletadas incorretamente

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}🔧 RECUPERAÇÃO DE SEPARAÇÕES PERDIDAS${NC}"
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
    echo "Uso: ./recuperar_separacoes.sh [opções]"
    echo ""
    echo "Opções:"
    echo "  --verificar    Apenas verifica quantos pedidos órfãos existem"
    echo "  --dry-run      Modo simulação (não salva alterações)"
    echo "  --pedido ID    Verifica/recupera pedido específico"
    echo "  --help         Mostra esta ajuda"
    echo ""
    echo "Exemplos:"
    echo "  ./recuperar_separacoes.sh --verificar        # Conta pedidos órfãos"
    echo "  ./recuperar_separacoes.sh --dry-run          # Simula recuperação"
    echo "  ./recuperar_separacoes.sh                     # Executa recuperação"
    echo "  ./recuperar_separacoes.sh --pedido P001      # Verifica pedido específico"
    echo ""
    echo -e "${YELLOW}⚠️  ATENÇÃO:${NC}"
    echo "Este script reconstrói Separações que foram deletadas mas cujos"
    echo "Pedidos ainda têm o separacao_lote_id e NF associada."
    exit 0
fi

# Mensagem de aviso
echo -e "${YELLOW}⚠️  IMPORTANTE:${NC}"
echo "Este script vai reconstruir Separações perdidas usando dados de NFs."
echo "Situação: Pedido tem separacao_lote_id mas Separacao foi deletada."
echo ""

# Se for verificação
if [ "$1" == "--verificar" ]; then
    echo -e "${BLUE}🔍 Verificando pedidos órfãos...${NC}"
    python executar_recuperacao_separacoes.py --verificar
    exit $?
fi

# Se for dry-run
if [ "$1" == "--dry-run" ]; then
    echo -e "${YELLOW}🔄 Executando em modo SIMULAÇÃO...${NC}"
    python executar_recuperacao_separacoes.py --dry-run
    exit $?
fi

# Se for pedido específico
if [ "$1" == "--pedido" ] && [ -n "$2" ]; then
    echo -e "${BLUE}🔍 Verificando pedido $2...${NC}"
    python executar_recuperacao_separacoes.py --pedido "$2"
    exit $?
fi

# Execução normal - pedir confirmação
echo -e "${RED}⚠️  ATENÇÃO: Esta operação irá CRIAR novas Separações!${NC}"
echo ""
read -p "Deseja continuar? (s/n): " resposta

if [ "$resposta" != "s" ] && [ "$resposta" != "S" ]; then
    echo -e "${YELLOW}Operação cancelada pelo usuário${NC}"
    exit 0
fi

# Executar recuperação
echo ""
echo -e "${GREEN}🚀 Iniciando recuperação...${NC}"
python executar_recuperacao_separacoes.py

# Verificar resultado
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Recuperação concluída!${NC}"
    echo "Verifique o arquivo de log em logs/ para detalhes completos"
else
    echo -e "${RED}❌ Erro durante a recuperação. Verifique os logs.${NC}"
    exit 1
fi