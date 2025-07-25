#!/bin/bash

# Script para sincronizar o repositório do Windows para o Linux

# Diretórios
WINDOWS_DIR="/mnt/c/Users/rafael.nascimento/Desktop/Sistema Online/frete_sistema"
LINUX_DIR="/home/rafaelnascimento/projetos/frete_sistema"

echo "=== Sincronizando repositório do Windows para Linux ==="
echo "De: $WINDOWS_DIR"
echo "Para: $LINUX_DIR"
echo ""

# Verificar se o diretório Linux existe
if [ ! -d "$LINUX_DIR" ]; then
    echo "Erro: Diretório Linux não encontrado: $LINUX_DIR"
    exit 1
fi

# Navegar para o diretório Windows
cd "$WINDOWS_DIR" || exit 1

# Obter o branch atual
CURRENT_BRANCH=$(git branch --show-current)
echo "Branch atual: $CURRENT_BRANCH"

# Criar um bundle com todos os commits
echo "Criando bundle com os commits..."
git bundle create /tmp/frete_sistema.bundle --all

# Navegar para o diretório Linux e aplicar o bundle
echo "Aplicando bundle no repositório Linux..."
cd "$LINUX_DIR" || exit 1

# Fazer backup do estado atual
echo "Fazendo backup do estado atual..."
git stash push -m "Backup antes da sincronização $(date +%Y%m%d_%H%M%S)"

# Buscar e aplicar os commits do bundle
echo "Aplicando commits..."
git fetch /tmp/frete_sistema.bundle "$CURRENT_BRANCH:refs/remotes/sync/$CURRENT_BRANCH"

# Fazer merge dos commits
echo "Fazendo merge dos commits..."
git merge "sync/$CURRENT_BRANCH" --no-edit

# Limpar
rm /tmp/frete_sistema.bundle

echo ""
echo "=== Sincronização concluída! ==="
echo "Último commit no Linux:"
git log --oneline -1