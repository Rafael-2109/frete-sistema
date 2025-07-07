#!/usr/bin/env python3
"""
Teste do NLP Enhanced Analyzer
"""

import sys
import os
from pathlib import Path

# Adicionar path correto
projeto_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(projeto_root))

def test_nlp_analyzer():
    """Testa NLP Enhanced Analyzer"""
    print("🧪 TESTANDO NLP ENHANCED ANALYZER")
    print("=" * 50)
    
    try:
        # Testar import
        from app.claude_ai_novo.analyzers.nlp_enhanced_analyzer import get_nlp_enhanced_analyzer
        print("✅ Import funcionando")
        
        # Testar instância
        analyzer = get_nlp_enhanced_analyzer()
        print(f"✅ Instância criada: {type(analyzer).__name__}")
        
        # Testar análise básica
        texto_teste = "mostrar entregas atrasadas do cliente Assai"
        resultado = analyzer.analisar_com_nlp(texto_teste)
        
        print(f"✅ Análise NLP:")
        print(f"   • Tokens: {len(resultado.tokens_limpos)}")
        print(f"   • Palavras-chave: {resultado.palavras_chave}")
        print(f"   • Sentimento: {resultado.sentimento}")
        print(f"   • Tempo verbal: {resultado.tempo_verbal}")
        
        if resultado.correcoes_sugeridas:
            print(f"   • Correções: {resultado.correcoes_sugeridas}")
        
        print("\n🎯 NLP ENHANCED ANALYZER VALIDADO!")
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_nlp_analyzer()
    exit(0 if success else 1)
