#!/usr/bin/env python3
"""
🧪 TESTE SIMPLES DA CORREÇÃO ASYNC
=================================

Testa se o erro "This event loop is already running" foi corrigido.
"""

import os
import sys
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

# Configurar variáveis de ambiente
os.environ['USE_NEW_CLAUDE_SYSTEM'] = 'true'

def testar_correcao():
    """Testa se a correção funcionou"""
    print("\n🧪 TESTANDO CORREÇÃO DO ERRO ASYNC\n")
    
    try:
        # Importar o módulo
        from app.claude_transition import processar_consulta_transicao
        
        print("1️⃣ Testando query simples...")
        
        # Testar uma query
        resultado = processar_consulta_transicao("Como estão as entregas do Atacadão?")
        
        # Verificar se retornou algo
        if resultado:
            print("✅ SUCESSO! Query processada sem erro de event loop")
            print(f"📝 Tipo de resultado: {type(resultado)}")
            
            # Mostrar parte do resultado
            if isinstance(resultado, str):
                print(f"📝 Resultado (primeiros 200 chars): {resultado[:200]}...")
            else:
                print(f"📝 Resultado: {resultado}")
                
            # Verificar se tem a resposta genérica
            if "Sistema operacional e processando entregas normalmente" in str(resultado):
                print("\n⚠️  AVISO: Ainda está retornando resposta genérica")
                print("   Mas pelo menos não está dando erro de event loop!")
            else:
                print("\n🎉 EXCELENTE! Não está mais retornando resposta genérica!")
                
        else:
            print("❌ Resultado vazio")
            
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        
        # Verificar se é o erro específico de event loop
        if "This event loop is already running" in str(e):
            print("\n❌ ERRO DE EVENT LOOP AINDA PRESENTE!")
        else:
            print("\n✅ Não é erro de event loop (é outro erro)")
    
    print("\n✅ TESTE COMPLETO!")

if __name__ == "__main__":
    testar_correcao() 