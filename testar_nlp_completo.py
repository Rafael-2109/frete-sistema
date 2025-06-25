#!/usr/bin/env python3
"""
🧠 TESTE COMPLETO DO NLP AVANÇADO
Verifica se todas as bibliotecas NLP estão funcionando corretamente
"""

import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def testar_nlp():
    """Testa todas as funcionalidades NLP"""
    
    print("🧠 TESTE COMPLETO DO SISTEMA NLP")
    print("=" * 50)
    
    # 1. Testar FuzzyWuzzy
    print("\n1️⃣ Testando FuzzyWuzzy (correção ortográfica)...")
    try:
        from fuzzywuzzy import fuzz, process
        
        # Teste de correção
        clientes = ["Assai", "Atacadão", "Carrefour", "Tenda"]
        
        testes = [
            ("asai", "Assai"),
            ("atacadao", "Atacadão"),
            ("carrefur", "Carrefour"),
            ("tneda", "Tenda")
        ]
        
        for erro, esperado in testes:
            melhor_match = process.extractOne(erro, clientes)
            print(f"   '{erro}' → '{melhor_match[0]}' (confiança: {melhor_match[1]}%)")
            assert melhor_match[0] == esperado, f"Esperava {esperado}, mas obteve {melhor_match[0]}"
        
        print("   ✅ FuzzyWuzzy funcionando perfeitamente!")
        
    except ImportError:
        print("   ❌ FuzzyWuzzy não instalado")
        return False
    except Exception as e:
        print(f"   ❌ Erro no FuzzyWuzzy: {e}")
        return False
    
    # 2. Testar SpaCy
    print("\n2️⃣ Testando SpaCy (análise sintática)...")
    try:
        import spacy
        
        # Carregar modelo português
        nlp = spacy.load("pt_core_news_sm")
        
        # Teste de análise
        texto = "Quais entregas do Assai estão atrasadas em São Paulo?"
        doc = nlp(texto)
        
        print(f"   Texto: '{texto}'")
        print(f"   Tokens: {[token.text for token in doc]}")
        print(f"   Entidades: {[(ent.text, ent.label_) for ent in doc.ents]}")
        print(f"   POS Tags: {[(token.text, token.pos_) for token in doc[:5]]}")
        
        print("   ✅ SpaCy funcionando com modelo português!")
        
    except ImportError:
        print("   ❌ SpaCy não instalado")
        return False
    except OSError:
        print("   ⚠️ SpaCy instalado mas modelo português não baixado")
        print("      Execute: python -m spacy download pt_core_news_sm")
        return False
    except Exception as e:
        print(f"   ❌ Erro no SpaCy: {e}")
        return False
    
    # 3. Testar NLTK
    print("\n3️⃣ Testando NLTK (stopwords e tokenização)...")
    try:
        import nltk
        from nltk.corpus import stopwords
        from nltk.tokenize import word_tokenize
        
        # Teste de stopwords
        stops = stopwords.words('portuguese')
        print(f"   Stopwords português: {stops[:10]}...")
        
        # Teste de tokenização
        texto = "O sistema de entregas está funcionando perfeitamente!"
        tokens = word_tokenize(texto.lower())
        tokens_limpos = [t for t in tokens if t not in stops and t.isalnum()]
        
        print(f"   Texto original: '{texto}'")
        print(f"   Tokens limpos: {tokens_limpos}")
        
        print("   ✅ NLTK funcionando com recursos português!")
        
    except ImportError:
        print("   ❌ NLTK não instalado")
        return False
    except LookupError:
        print("   ⚠️ NLTK instalado mas recursos não baixados")
        print("      Execute: python install_nlp_models.py")
        return False
    except Exception as e:
        print(f"   ❌ Erro no NLTK: {e}")
        return False
    
    # 4. Testar integração com o sistema
    print("\n4️⃣ Testando integração com intelligent_query_analyzer...")
    try:
        from app.claude_ai.intelligent_query_analyzer import IntelligentQueryAnalyzer
        from app.claude_ai.nlp_enhanced_analyzer import get_nlp_analyzer
        
        # Teste de análise inteligente
        analyzer = IntelligentQueryAnalyzer()
        nlp_analyzer = get_nlp_analyzer()
        
        consultas_teste = [
            "quais entregass do asai atrazadas",
            "mostre os pedids do atacadao",
            "relatoru excel do carrefur"
        ]
        
        for consulta in consultas_teste:
            # Análise NLP
            analise_nlp = nlp_analyzer.analisar_com_nlp(consulta)
            
            # Análise inteligente
            interpretacao = analyzer.analisar_consulta_inteligente(consulta)
            
            print(f"\n   Consulta: '{consulta}'")
            print(f"   Correções NLP: {analise_nlp.correcoes_sugeridas}")
            print(f"   Intenção: {interpretacao.intencao_principal.value}")
            print(f"   Confiança: {interpretacao.confianca_interpretacao:.2%}")
        
        print("\n   ✅ Integração funcionando perfeitamente!")
        
    except ImportError as e:
        print(f"   ❌ Erro ao importar módulos do sistema: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Erro na integração: {e}")
        return False
    
    # Resultado final
    print("\n" + "=" * 50)
    print("✨ TODOS OS TESTES PASSARAM! NLP 100% FUNCIONAL!")
    print("=" * 50)
    
    return True

def main():
    """Função principal"""
    success = testar_nlp()
    
    if not success:
        print("\n⚠️ Alguns testes falharam. Execute os seguintes comandos:")
        print("1. pip install -r requirements.txt")
        print("2. python install_nlp_models.py")
        sys.exit(1)
    
    print("\n🚀 Sistema pronto para usar NLP avançado!")
    print("   - Correção ortográfica automática ✅")
    print("   - Análise sintática em português ✅")
    print("   - Detecção de entidades ✅")
    print("   - Fuzzy matching inteligente ✅")

if __name__ == "__main__":
    main() 