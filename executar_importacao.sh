#!/bin/bash

# Script de execução da importação histórica do Odoo - SEM FILTRO
# Autor: Sistema
# Data: 21/09/2025
# Versão: 2.0 - Usa script sem filtro

echo "======================================"
echo "🚀 IMPORTADOR HISTÓRICO DO ODOO"
echo "       (VERSÃO SEM FILTRO)"
echo "======================================"
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Verificar se Python está instalado
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python 3 não está instalado${NC}"
    exit 1
fi

# Informação importante
echo -e "${BLUE}ℹ️  Este script busca TODOS os pedidos do período${NC}"
echo -e "${BLUE}   (01/07/2025 a 21/09/2025) SEM filtrar por saldo${NC}"
echo ""

# Menu de opções
echo "Escolha o modo de execução:"
echo ""
echo "  1) 🔍 DRY RUN (Simulação - apenas analisa sem gravar)"
echo "  2) ⚡ PRODUÇÃO (Grava dados no banco)"
echo "  3) ❌ Cancelar"
echo ""

read -p "Digite sua opção (1-3): " opcao

case $opcao in
    1)
        echo -e "${GREEN}🔍 Executando em modo DRY RUN...${NC}"
        echo -e "${GREEN}   Analisando dados SEM FILTRO de saldo${NC}"
        echo ""
        python3 importar_historico_sem_filtro.py
        ;;
    2)
        echo -e "${YELLOW}⚠️  ATENÇÃO: Modo PRODUÇÃO selecionado!${NC}"
        echo -e "${YELLOW}Isso irá GRAVAR dados no banco de dados.${NC}"
        echo -e "${YELLOW}Serão importados TODOS os pedidos (incluindo saldo 0)${NC}"
        echo ""
        read -p "Tem certeza? Digite 'SIM' para confirmar: " confirmacao

        if [ "$confirmacao" = "SIM" ]; then
            echo -e "${GREEN}⚡ Executando em modo PRODUÇÃO...${NC}"
            echo -e "${GREEN}   Importando TODOS os pedidos SEM FILTRO${NC}"
            echo ""
            python3 importar_historico_sem_filtro.py --producao --confirmar
        else
            echo -e "${RED}❌ Operação cancelada${NC}"
            exit 1
        fi
        ;;
    3)
        echo -e "${RED}❌ Operação cancelada${NC}"
        exit 0
        ;;
    *)
        echo -e "${RED}❌ Opção inválida${NC}"
        exit 1
        ;;
esac

# Verificar código de saída
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}✅ Processo finalizado com sucesso!${NC}"
else
    echo ""
    echo -e "${RED}❌ Processo finalizado com erros. Verifique o log.${NC}"
fi