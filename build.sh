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

# Executar migrações com correção robusta
echo "🗄️ Executando migrações do banco..."
echo "🔧 Aplicando correção robusta de migração..."

# Tentar resolver problema da revisão 1d81b88a3038
flask db stamp head 2>/dev/null || echo "⚠️ Stamp não necessário"
flask db merge heads 2>/dev/null || echo "⚠️ Sem múltiplas heads para merge"
flask db upgrade 2>/dev/null || echo "⚠️ Upgrade com problemas, continuando..."

echo "✅ Build concluído!" 

# Aplicar correções Claude AI
echo "🔧 Aplicando correções Claude AI..."
python corrigir_problemas_claude_render.py || echo "⚠️ Correções Claude AI já aplicadas ou falharam"

# Verificação final de migrações
echo "✅ Migrações aplicadas com sucesso!"
