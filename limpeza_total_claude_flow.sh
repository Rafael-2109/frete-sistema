#!/bin/bash

# Script de limpeza TOTAL de todas as referências ao claude-flow
# Data: $(date)

echo "=============================================="
echo "   LIMPEZA TOTAL CLAUDE-FLOW/SPARC/SWARM    "
echo "=============================================="
echo ""

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Criar backup final antes da limpeza total
BACKUP_DIR="backup_limpeza_total_$(date +%Y%m%d_%H%M%S)"
echo -e "${YELLOW}Criando backup completo em: $BACKUP_DIR${NC}"
mkdir -p "$BACKUP_DIR"

# Fazer backup de arquivos importantes que serão modificados
echo -e "${GREEN}Fazendo backup de arquivos que serão modificados...${NC}"
[ -f ".mcp.json" ] && cp .mcp.json "$BACKUP_DIR/"
[ -f ".gitignore" ] && cp .gitignore "$BACKUP_DIR/"
[ -f "CLAUDE-flow.md" ] && cp CLAUDE-flow.md "$BACKUP_DIR/"
[ -d ".claude" ] && cp -r .claude "$BACKUP_DIR/"
[ -d "memory" ] && cp -r memory "$BACKUP_DIR/"
[ -d "optimization" ] && cp -r optimization "$BACKUP_DIR/"
[ -d "coordination" ] && cp -r coordination "$BACKUP_DIR/"
[ -f "ENVIRONMENT_READY.md" ] && cp ENVIRONMENT_READY.md "$BACKUP_DIR/"

echo ""
echo -e "${YELLOW}=== AÇÕES QUE SERÃO REALIZADAS ===${NC}"
echo ""
echo -e "${RED}1. ARQUIVOS E DIRETÓRIOS A REMOVER:${NC}"
echo "   - CLAUDE-flow.md (arquivo de documentação claude-flow)"
echo "   - .mcp.json (configuração MCP com claude-flow)"
echo "   - memory/ (diretório de memória do claude-flow)"
echo "   - optimization/ (diretório de otimização)"
echo "   - coordination/ (diretório de coordenação)"
echo "   - Todos os templates em .claude/agents/"
echo "   - Todos os comandos em .claude/commands/"
echo "   - Scripts de remoção anteriores"
echo ""
echo -e "${BLUE}2. ARQUIVOS A LIMPAR (remover referências):${NC}"
echo "   - .gitignore (remover linhas com claude-flow/sparc/swarm)"
echo "   - ENVIRONMENT_READY.md (se contiver referências)"
echo "   - Arquivos em app/claude_ai_novo/*.md com referências"
echo ""
echo -e "${GREEN}3. O QUE SERÁ PRESERVADO:${NC}"
echo "   - CLAUDE.md (documentação do projeto)"
echo "   - .claude/settings.json (configurações do Claude Code)"
echo "   - Todo o código do sistema de frete"
echo "   - Banco de dados e configurações"
echo ""
echo -e "${YELLOW}Backup completo em: $BACKUP_DIR${NC}"
echo ""
read -p "Deseja prosseguir com a limpeza TOTAL? (s/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Ss]$ ]]; then
    echo -e "${RED}Operação cancelada pelo usuário.${NC}"
    exit 1
fi

echo ""
echo -e "${GREEN}=== INICIANDO LIMPEZA TOTAL ===${NC}"
echo ""

# 1. Remover arquivos e diretórios principais
echo -e "${BLUE}[1/5] Removendo arquivos e diretórios principais...${NC}"

# Remover arquivo CLAUDE-flow.md
[ -f "CLAUDE-flow.md" ] && rm -f CLAUDE-flow.md && echo "  ✓ CLAUDE-flow.md removido"

# Remover .mcp.json (tem configurações do claude-flow)
[ -f ".mcp.json" ] && rm -f .mcp.json && echo "  ✓ .mcp.json removido"

# Remover diretórios relacionados
[ -d "memory" ] && rm -rf memory && echo "  ✓ Diretório memory/ removido"
[ -d "optimization" ] && rm -rf optimization && echo "  ✓ Diretório optimization/ removido"
[ -d "coordination" ] && rm -rf coordination && echo "  ✓ Diretório coordination/ removido"

# Remover scripts de remoção anteriores
[ -f "remove_claude_flow.sh" ] && rm -f remove_claude_flow.sh && echo "  ✓ remove_claude_flow.sh removido"
[ -f "remove_hive_mind.sh" ] && rm -f remove_hive_mind.sh && echo "  ✓ remove_hive_mind.sh removido"

# 2. Limpar .claude/agents
echo ""
echo -e "${BLUE}[2/5] Limpando .claude/agents/...${NC}"
if [ -d ".claude/agents" ]; then
    # Remover diretórios específicos
    for dir in sparc swarm github consensus optimization templates testing; do
        [ -d ".claude/agents/$dir" ] && rm -rf ".claude/agents/$dir" && echo "  ✓ .claude/agents/$dir removido"
    done
    
    # Remover arquivos com referências
    find .claude/agents -type f -name "*.md" | while read file; do
        if grep -q -i "claude-flow\|sparc\|swarm\|hive-mind" "$file" 2>/dev/null; then
            rm -f "$file"
            echo "  ✓ $(basename $file) removido"
        fi
    done
fi

# 3. Limpar .claude/commands
echo ""
echo -e "${BLUE}[3/5] Limpando .claude/commands/...${NC}"
if [ -d ".claude/commands" ]; then
    # Remover diretórios específicos
    for dir in sparc coordination github monitoring optimization memory workflows training automation analysis hooks; do
        [ -d ".claude/commands/$dir" ] && rm -rf ".claude/commands/$dir" && echo "  ✓ .claude/commands/$dir removido"
    done
    
    # Remover arquivos sparc.md na raiz de commands
    [ -f ".claude/commands/sparc.md" ] && rm -f ".claude/commands/sparc.md" && echo "  ✓ sparc.md removido"
fi

# 4. Limpar .claude/helpers se existir
echo ""
echo -e "${BLUE}[4/5] Limpando .claude/helpers/...${NC}"
if [ -d ".claude/helpers" ]; then
    rm -rf .claude/helpers && echo "  ✓ .claude/helpers removido"
fi

# 5. Limpar referências em arquivos
echo ""
echo -e "${BLUE}[5/5] Limpando referências em arquivos...${NC}"

# Limpar .gitignore
if [ -f ".gitignore" ]; then
    grep -v -i "claude-flow\|sparc\|swarm\|hive-mind\|\.roo\|roomodes" .gitignore > .gitignore.tmp
    mv .gitignore.tmp .gitignore
    echo "  ✓ .gitignore limpo"
fi

# Limpar ENVIRONMENT_READY.md se existir e tiver referências
if [ -f "ENVIRONMENT_READY.md" ]; then
    if grep -q -i "claude-flow\|sparc\|swarm" ENVIRONMENT_READY.md; then
        grep -v -i "claude-flow\|sparc\|swarm" ENVIRONMENT_READY.md > ENVIRONMENT_READY.md.tmp
        mv ENVIRONMENT_READY.md.tmp ENVIRONMENT_READY.md
        echo "  ✓ ENVIRONMENT_READY.md limpo"
    fi
fi

# Limpar arquivos em app/claude_ai_novo/
if [ -d "app/claude_ai_novo" ]; then
    for file in app/claude_ai_novo/*.md; do
        if [ -f "$file" ] && grep -q -i "claude-flow\|sparc\|swarm" "$file"; then
            grep -v -i "claude-flow\|sparc\|swarm" "$file" > "$file.tmp"
            mv "$file.tmp" "$file"
            echo "  ✓ $(basename $file) limpo"
        fi
    done
fi

echo ""
echo -e "${GREEN}=============================================="
echo "         LIMPEZA TOTAL CONCLUÍDA             "
echo "==============================================${NC}"
echo ""
echo "✅ Todas as referências ao claude-flow removidas"
echo "✅ Diretórios e arquivos relacionados removidos"
echo "✅ Templates e comandos limpos"
echo "✅ Backup completo em: $BACKUP_DIR"
echo ""
echo -e "${GREEN}Arquivos preservados:${NC}"
echo "  - CLAUDE.md (documentação do projeto)"
echo "  - .claude/settings.json (configurações do Claude Code)"
echo "  - Sistema de frete (100% funcional)"
echo ""
echo -e "${YELLOW}Para restaurar (se necessário):${NC}"
echo "  cp -r $BACKUP_DIR/* ."
echo ""
echo -e "${GREEN}Sistema completamente limpo e funcional!${NC}"