#!/usr/bin/env python3
"""
🧪 TESTE DA INTERFACE DE TRANSIÇÃO
Valida se a interface de transição está funcionando
"""

import sys
from pathlib import Path

# Adicionar path do projeto
projeto_root = Path(__file__).parent
sys.path.insert(0, str(projeto_root))

def testar_interface_transicao():
    """Testa a interface de transição"""
    print("🧪 TESTANDO INTERFACE DE TRANSIÇÃO")
    print("="*50)
    
    try:
        # Teste 1: Import da interface
        print("\n1. 📦 Testando import da interface...")
        from app.claude_transition import get_claude_transition, processar_consulta_transicao
        print("✅ Interface importada com sucesso")
        
        # Teste 2: Inicialização
        print("\n2. 🚀 Testando inicialização...")
        transition = get_claude_transition()
        print(f"✅ Interface inicializada - Sistema ativo: {transition.sistema_ativo}")
        
        # Teste 3: Processamento básico
        print("\n3. 🎯 Testando processamento...")
        resultado = processar_consulta_transicao("teste de funcionamento")
        print(f"✅ Processamento funcionando")
        print(f"📄 Resultado: {resultado[:80]}...")
        
        # Teste 4: Alternância de sistema
        print("\n4. 🔄 Testando alternância...")
        sistema_anterior = transition.sistema_ativo
        mensagem_alternancia = transition.alternar_sistema()
        print(f"✅ {mensagem_alternancia}")
        print(f"🔄 Sistema mudou de '{sistema_anterior}' para '{transition.sistema_ativo}'")
        
        # Voltar ao sistema original
        transition.alternar_sistema()
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

def mostrar_instrucoes_uso():
    """Mostra instruções de uso da interface"""
    print("\n" + "🚀" * 50)
    print("COMO USAR A INTERFACE DE TRANSIÇÃO")
    print("🚀" * 50)
    
    print("""
📋 OPÇÃO 1 - USO DIRETO:
   from app.claude_transition import processar_consulta_transicao
   resultado = processar_consulta_transicao("sua consulta aqui")

📋 OPÇÃO 2 - CONTROLE MANUAL:
   from app.claude_transition import get_claude_transition
   
   transition = get_claude_transition()
   print(f"Sistema ativo: {transition.sistema_ativo}")
   
   # Processar consulta
   resultado = transition.processar_consulta("sua consulta")
   
   # Alternar sistema
   transition.alternar_sistema()

📋 OPÇÃO 3 - VARIÁVEL DE AMBIENTE:
   # No terminal ou .env:
   export USE_NEW_CLAUDE_SYSTEM=true    # Usar sistema novo
   export USE_NEW_CLAUDE_SYSTEM=false   # Usar sistema antigo
   
   # Reiniciar aplicação para aplicar a mudança

💡 VANTAGENS:
   ✅ Fallback automático se sistema novo falhar
   ✅ Zero risco de quebrar funcionalidades
   ✅ Transição transparente
   ✅ Controle total sobre qual sistema usar
""")

def main():
    """Executa testes da interface de transição"""
    print("🔄 TESTE COMPLETO DA INTERFACE DE TRANSIÇÃO")
    print("="*60)
    
    if testar_interface_transicao():
        print("\n🎉 INTERFACE DE TRANSIÇÃO FUNCIONANDO PERFEITAMENTE!")
        mostrar_instrucoes_uso()
        
        print("\n🎯 PRÓXIMOS PASSOS RECOMENDADOS:")
        print("1. ✅ Começar usando processar_consulta_transicao() nas suas rotas")
        print("2. ✅ Configurar USE_NEW_CLAUDE_SYSTEM=true quando confortável")
        print("3. ✅ Monitorar logs para verificar funcionamento")
        print("4. ✅ Migrar progressivamente para o sistema novo")
        
    else:
        print("\n❌ PROBLEMAS ENCONTRADOS NA INTERFACE")
        print("🔧 Verifique se todos os módulos estão instalados corretamente")

if __name__ == "__main__":
    main() 