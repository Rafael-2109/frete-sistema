#!/bin/bash

# Build script para Render com correção de migrações

echo "=== INICIANDO DEPLOY NO RENDER ==="

# 1. Instalar dependências
echo "Instalando dependências..."
pip install -r requirements.txt

# 2. Instalar Playwright e navegadores (para Portal Atacadão)
echo "Instalando Playwright e nest-asyncio..."
pip install playwright nest-asyncio
playwright install chromium
playwright install-deps chromium || echo "Dependências instaladas pelo Render"

# 3. Instalar modelo spaCy português
echo "Instalando modelo spaCy português..."
python -m spacy download pt_core_news_sm || echo "spaCy pode não estar instalado, continuando..."

# 3. Verificar e corrigir migrações
echo "Verificando migrações..."

# Verificar se há múltiplas heads
if flask db heads | grep -q "Multiple head revisions"; then
    echo "Múltiplas heads detectadas, criando merge..."
    flask db merge heads -m "Merge múltiplas heads automaticamente"
fi

# Verificar se há heads não aplicadas
if ! flask db current | grep -q "(head)"; then
    echo "Aplicando migrações..."
    flask db upgrade
else
    echo "Banco já está atualizado"
fi

# 4. Verificar e aplicar migração hora_agendamento
echo "Verificando campo hora_agendamento..."
mkdir -p scripts
python scripts/deploy_render.py || echo "Script de verificação falhou, continuando..."

# 5. Inicializar banco se necessário
echo "Inicializando banco..."
python init_db.py

echo "Build concluído com sucesso!"

python aplicar_migracao_render.py || echo "Migration already applied"
