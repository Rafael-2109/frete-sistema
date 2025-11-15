#!/bin/bash
# Script para buscar logs de webhooks TagPlus usando Render CLI
# A API REST do Render não disponibiliza endpoint público de logs
# Use a CLI oficial: https://render.com/docs/cli

# Cores para output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

SERVICE_NAME="sistema-fretes"

# Verificar se Render CLI está instalado
if ! command -v render &> /dev/null; then
    echo -e "${RED}❌ Render CLI não encontrado${NC}"
    echo ""
    echo "Instale com:"
    echo "  npm install -g @render-com/cli"
    echo ""
    echo "Ou use npx (sem instalar):"
    echo "  npx @render-com/cli logs $SERVICE_NAME"
    exit 1
fi

# Função para mostrar ajuda
show_help() {
    echo "🔍 Busca de Logs de Webhooks TagPlus"
    echo ""
    echo "Uso: $0 [opção]"
    echo ""
    echo "Opções:"
    echo "  webhooks          Todos os webhooks recebidos"
    echo "  nfe               Apenas webhooks de NFe"
    echo "  cliente           Apenas webhooks de cliente"
    echo "  rejeitados        Apenas webhooks rejeitados"
    echo "  validados         Apenas webhooks validados"
    echo "  erro              Erros no processamento"
    echo "  nfe:<numero>      Buscar NFe específica (ex: nfe:12345)"
    echo "  tempo:<horas>     Últimas N horas (ex: tempo:24)"
    echo "  live              Monitorar em tempo real"
    echo ""
    echo "Exemplos:"
    echo "  $0 webhooks"
    echo "  $0 nfe"
    echo "  $0 rejeitados"
    echo "  $0 nfe:12345"
    echo "  $0 tempo:48"
    echo ""
}

# Função para buscar webhooks
buscar_webhooks() {
    local filtro="$1"
    local tempo="${2:-1h}"

    echo -e "${BLUE}🔍 Buscando logs (últimas $tempo)...${NC}"
    echo ""

    render logs "$SERVICE_NAME" --since "$tempo" | grep --color=always -E "$filtro" || echo -e "${YELLOW}⚠️  Nenhum log encontrado${NC}"
}

# Processar argumentos
case "${1:-help}" in
    webhooks|webhook)
        echo -e "${GREEN}📦 Todos os webhooks recebidos${NC}"
        buscar_webhooks "WEBHOOK RECEBIDO|WEBHOOK NFE|WEBHOOK CLIENTE" "${2:-1h}"
        ;;

    nfe)
        echo -e "${GREEN}📄 Webhooks de NFe${NC}"
        buscar_webhooks "WEBHOOK NFE|/webhook/tagplus/nfe" "${2:-1h}"
        ;;

    cliente)
        echo -e "${GREEN}👤 Webhooks de Cliente${NC}"
        buscar_webhooks "WEBHOOK CLIENTE|/webhook/tagplus/cliente" "${2:-1h}"
        ;;

    rejeitados|rejeitado)
        echo -e "${RED}🚫 Webhooks rejeitados${NC}"
        buscar_webhooks "WEBHOOK REJEITADO" "${2:-1h}"
        ;;

    validados|validado)
        echo -e "${GREEN}✅ Webhooks validados${NC}"
        buscar_webhooks "WEBHOOK VALIDADO" "${2:-1h}"
        ;;

    erro|erros)
        echo -e "${RED}❌ Erros no processamento${NC}"
        buscar_webhooks "Erro no webhook" "${2:-1h}"
        ;;

    nfe:*)
        nfe_num="${1#nfe:}"
        echo -e "${BLUE}🔍 Buscando NFe ${nfe_num}${NC}"
        buscar_webhooks "NFe.*${nfe_num}|NF ${nfe_num}" "${2:-24h}"
        ;;

    tempo:*)
        horas="${1#tempo:}"
        echo -e "${BLUE}📊 Últimas ${horas} horas${NC}"
        buscar_webhooks "WEBHOOK" "${horas}h"
        ;;

    live|monitor)
        echo -e "${GREEN}📡 Monitorando webhooks em tempo real... (Ctrl+C para sair)${NC}"
        echo ""
        render logs "$SERVICE_NAME" --tail | grep --line-buffered --color=always "WEBHOOK"
        ;;

    stats|estatisticas)
        echo -e "${BLUE}📊 Estatísticas de webhooks (últimas 24h)${NC}"
        echo ""

        logs=$(render logs "$SERVICE_NAME" --since 24h)

        total=$(echo "$logs" | grep -c "WEBHOOK RECEBIDO" || echo "0")
        nfes=$(echo "$logs" | grep -c "WEBHOOK NFE" || echo "0")
        clientes=$(echo "$logs" | grep -c "WEBHOOK CLIENTE" || echo "0")
        validados=$(echo "$logs" | grep -c "WEBHOOK VALIDADO" || echo "0")
        rejeitados=$(echo "$logs" | grep -c "WEBHOOK REJEITADO" || echo "0")
        processados=$(echo "$logs" | grep -c "processada via webhook" || echo "0")
        erros=$(echo "$logs" | grep -c "Erro no webhook" || echo "0")

        echo -e "Total recebidos:    ${GREEN}${total}${NC}"
        echo -e "  └─ NFes:          ${BLUE}${nfes}${NC}"
        echo -e "  └─ Clientes:      ${BLUE}${clientes}${NC}"
        echo ""
        echo -e "Validados:          ${GREEN}${validados}${NC}"
        echo -e "Rejeitados:         ${RED}${rejeitados}${NC}"
        echo ""
        echo -e "NFes processadas:   ${GREEN}${processados}${NC}"
        echo -e "Erros:              ${RED}${erros}${NC}"
        ;;

    help|--help|-h)
        show_help
        ;;

    *)
        echo -e "${RED}❌ Opção inválida: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
