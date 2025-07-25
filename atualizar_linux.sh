#!/bin/bash
# Script para atualizar o repositório Linux com os commits do Windows

# Criar bundle no diretório Windows atual
git bundle create /tmp/frete_sistema.bundle --all

echo "Bundle criado. Agora execute os seguintes comandos:"
echo ""
echo "cd /home/rafaelnascimento/projetos/frete_sistema"
echo "git fetch /tmp/frete_sistema.bundle main:sync/main"
echo "git merge sync/main"
echo "rm /tmp/frete_sistema.bundle"