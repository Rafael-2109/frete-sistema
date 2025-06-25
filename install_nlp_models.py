#!/usr/bin/env python3
"""
🧠 INSTALADOR DE MODELOS NLP
Baixa automaticamente os modelos necessários para processamento em português
"""

import subprocess
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def instalar_modelos_nlp():
    """Instala todos os modelos necessários para NLP em português"""
    
    print("🧠 Instalando modelos de NLP para português...")
    
    # 1. Instalar modelo português do spaCy
    try:
        logger.info("📦 Baixando modelo pt_core_news_sm do spaCy...")
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "pt_core_news_sm"])
        logger.info("✅ Modelo spaCy português instalado com sucesso!")
    except subprocess.CalledProcessError as e:
        logger.warning(f"⚠️ Erro ao instalar modelo spaCy: {e}")
        logger.info("Tentando alternativa...")
        try:
            import spacy
            spacy.cli.download("pt_core_news_sm")
            logger.info("✅ Modelo instalado via spacy.cli!")
        except Exception as e2:
            logger.error(f"❌ Falha ao instalar modelo spaCy: {e2}")
    
    # 2. Baixar recursos do NLTK
    try:
        logger.info("📦 Baixando recursos NLTK...")
        import nltk
        
        # Recursos essenciais para português
        recursos = [
            'stopwords',        # Palavras comuns (de, a, o, que, etc)
            'punkt',           # Tokenização de sentenças
            'averaged_perceptron_tagger',  # POS tagging
            'rslp'             # Stemmer português
        ]
        
        for recurso in recursos:
            try:
                nltk.download(recurso, quiet=True)
                logger.info(f"  ✓ {recurso} baixado")
            except Exception as e:
                logger.warning(f"  ✗ Erro ao baixar {recurso}: {e}")
        
        logger.info("✅ Recursos NLTK instalados!")
        
    except ImportError:
        logger.warning("⚠️ NLTK não está instalado")
    except Exception as e:
        logger.error(f"❌ Erro ao instalar recursos NLTK: {e}")
    
    # 3. Verificar instalações
    print("\n📋 Verificando instalações...")
    
    # Testar spaCy
    try:
        import spacy
        nlp = spacy.load("pt_core_news_sm")
        doc = nlp("Teste de processamento em português")
        logger.info(f"✅ SpaCy funcionando! Tokens: {[token.text for token in doc]}")
    except Exception as e:
        logger.error(f"❌ SpaCy não está funcionando: {e}")
    
    # Testar NLTK
    try:
        import nltk
        from nltk.corpus import stopwords
        stops = stopwords.words('portuguese')[:5]
        logger.info(f"✅ NLTK funcionando! Stopwords: {stops}")
    except Exception as e:
        logger.error(f"❌ NLTK não está funcionando: {e}")
    
    print("\n✨ Instalação de modelos NLP concluída!")

if __name__ == "__main__":
    instalar_modelos_nlp() 