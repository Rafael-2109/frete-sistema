#!/bin/bash

set -o errexit

echo "Iniciando build do Render..."

# Instalar dependências Python
echo "Instalando dependências Python..."
pip install -r requirements.txt

# Instalar modelo spaCy português
echo "Instalando modelo spaCy português..."
python -m spacy download pt_core_news_sm || echo "Falha ao instalar spaCy, continuando..."

# Instalar dependências AI se existirem
if [ -f "requirements_ai.txt" ]; then
    echo "Instalando dependências AI..."
    pip install -r requirements_ai.txt || echo "Falha ao instalar deps AI, continuando..."
fi

echo "Build concluído com sucesso!"
