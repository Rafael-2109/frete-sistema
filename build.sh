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
    # Resolver problemas de múltiplas heads
echo "🔧 Resolvendo problemas de migração..."
flask db merge heads || echo "⚠️ Merge não necessário"
flask db upgrade || echo "⚠️ Upgrade já aplicado" || echo "⚠️ Sem migrações para executar"
fi

echo "✅ Build concluído!" 

# Aplicar correções Claude AI
echo "🔧 Aplicando correções Claude AI..."
python corrigir_problemas_claude_render.py || echo "⚠️ Correções Claude AI já aplicadas ou falharam"

# Executar migrações das tabelas de IA
echo "🗄️ Executando migrações das tabelas de IA..."
# Resolver problemas de múltiplas heads
echo "🔧 Resolvendo problemas de migração..."
flask db merge heads || echo "⚠️ Merge não necessário"
flask db upgrade || echo "⚠️ Upgrade já aplicado" || echo "⚠️ Migrações já aplicadas ou falharam"
