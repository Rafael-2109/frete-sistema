#!/usr/bin/env python3
"""
Instala o modelo português do spaCy de forma robusta
"""

import subprocess
import sys

def install_spacy_model():
    """Instala o modelo pt_core_news_sm do spaCy"""
    print("🧠 Instalando modelo spaCy português...")
    
    try:
        # Tentar método 1: via CLI do spaCy
        print("   📌 Tentando via spacy download...")
        result = subprocess.run(
            [sys.executable, '-m', 'spacy', 'download', 'pt_core_news_sm'],
            capture_output=True,
            text=True
        )
        
        if result.returncode == 0:
            print("   ✅ Modelo instalado com sucesso!")
            return True
        else:
            print(f"   ⚠️ Falha no método 1: {result.stderr}")
            
    except Exception as e:
        print(f"   ⚠️ Erro no método 1: {e}")
    
    # Tentar método 2: via código Python
    try:
        print("   📌 Tentando via código Python...")
        import spacy
        spacy.cli.download("pt_core_news_sm")
        print("   ✅ Modelo instalado com sucesso!")
        return True
    except Exception as e:
        print(f"   ⚠️ Erro no método 2: {e}")
    
    # Tentar método 3: verificar se já está instalado
    try:
        print("   📌 Verificando se já está instalado...")
        import spacy
        nlp = spacy.load("pt_core_news_sm")
        print("   ✅ Modelo já estava instalado!")
        return True
    except Exception as e:
        print(f"   ⚠️ Modelo não está instalado: {e}")
    
    print("   ❌ Não foi possível instalar o modelo spaCy")
    print("   💡 O sistema funcionará sem ele, mas com funcionalidades limitadas de NLP")
    return False

if __name__ == "__main__":
    success = install_spacy_model()
    # Sempre retornar 0 para não interromper o deploy
    sys.exit(0) 