#!/bin/bash

set -o errexit

echo "Iniciando build do Render..."

# Instalar depend�ncias Python
echo "Instalando depend�ncias Python..."
pip install -r requirements.txt

# Instalar modelo spaCy portugu�s
echo "Instalando modelo spaCy portugu�s..."
python -m spacy download pt_core_news_sm || echo "Falha ao instalar spaCy, continuando..."

# Instalar depend�ncias AI se existirem
if [ -f "requirements_ai.txt" ]; then
    echo "Instalando depend�ncias AI..."
    pip install -r requirements_ai.txt || echo "Falha ao instalar deps AI, continuando..."
fi

echo "Build conclu�do com sucesso!"
