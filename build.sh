#!/usr/bin/env bash
# Script de build para Render.com

echo "🚀 Iniciando build do Sistema de Fretes..."

# Instalar dependências Python
echo "📦 Instalando dependências..."
pip install -r requirements.txt

# Baixar modelos de NLP
echo "🧠 Baixando modelos de linguagem natural..."

# Modelo português do spaCy
python -m spacy download pt_core_news_sm || echo "⚠️ Falha ao baixar modelo spaCy"

# Recursos NLTK
python -c "
import nltk
nltk.download('stopwords', quiet=True)
nltk.download('punkt', quiet=True)
nltk.download('rslp', quiet=True)
print('✅ Recursos NLTK baixados')
" || echo "⚠️ Falha ao baixar recursos NLTK"

# Executar migrações se existirem
if [ -f "flask" ]; then
    echo "🗄️ Executando migrações do banco..."
    flask db upgrade || echo "⚠️ Sem migrações para executar"
fi

echo "✅ Build concluído!" 

# Aplicar correções Claude AI (executar uma vez)
echo "🔧 Aplicando correções Claude AI..."
python migracao_ai_render.py || echo "⚠️ Migração AI já aplicada ou falhou"
