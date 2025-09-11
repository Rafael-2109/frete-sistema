#!/bin/bash
# Claude-Flow IDE Integration Script
# Uso: ./scripts/claude-flow-ide.sh [comando]

set -e

PROJECT_ROOT=$(pwd)
export CLAUDE_WORKING_DIR="$PROJECT_ROOT"

# Cores para output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${BLUE}🌊 Claude-Flow IDE Integration${NC}"
echo -e "Projeto: ${GREEN}Sistema de Fretes${NC}"
echo ""

case "${1:-help}" in
  "analyze")
    echo -e "${YELLOW}📊 Analisando código Flask...${NC}"
    claude-flow swarm "analisar estrutura do projeto Flask"
    ;;
  
  "debug")
    echo -e "${YELLOW}🐛 Iniciando debugger...${NC}"
    claude-flow agent spawn debugger
    ;;
    
  "models")
    echo -e "${YELLOW}📋 Analisando modelos...${NC}"
    claude-flow swarm "revisar modelos SQLAlchemy"
    ;;
    
  "start")
    echo -e "${YELLOW}🚀 Iniciando sistema...${NC}"
    claude-flow start --ui
    ;;
    
  "status")
    claude-flow status
    ;;
    
  *)
    echo -e "${GREEN}Comandos:${NC} analyze debug models start status"
    ;;
esac
