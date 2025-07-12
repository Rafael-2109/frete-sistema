#!/usr/bin/env python3
"""
🧪 TESTE SIMPLES DO LOOP INFINITO
=================================

Teste direto e simples para verificar se o loop foi corrigido.
"""

import asyncio
import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

async def teste_simples():
    """Teste simples e direto"""
    print("🧪 TESTE SIMPLES DO LOOP INFINITO")
    print("=" * 50)
    
    try:
        # Importar IntegrationManager
        from app.claude_ai_novo.integration.integration_manager import IntegrationManager
        
        # Criar instância
        print("1️⃣ Criando IntegrationManager...")
        manager = IntegrationManager()
        
        # Contador de tentativas
        max_tentativas = 3
        tentativa = 0
        
        # Testar consulta
        print("2️⃣ Testando consulta...")
        
        # Adicionar timeout para evitar travamento
        try:
            result = await asyncio.wait_for(
                manager.process_unified_query("Como estão as entregas do Atacadão?"),
                timeout=5.0  # 5 segundos de timeout
            )
            
            print("✅ Consulta processada com sucesso!")
            print(f"   Resultado: {result}")
            
            # Verificar se houve prevenção de loop
            if result.get('loop_prevented'):
                print("⚠️ Loop foi detectado e prevenido")
            
            return True
            
        except asyncio.TimeoutError:
            print("❌ TIMEOUT! A consulta travou (possível loop infinito)")
            return False
            
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Executa o teste"""
    sucesso = await teste_simples()
    
    print("\n" + "=" * 50)
    if sucesso:
        print("✅ RESULTADO: O loop infinito foi CORRIGIDO!")
    else:
        print("❌ RESULTADO: O loop infinito AINDA EXISTE!")
    print("=" * 50)

if __name__ == "__main__":
    # Para Windows
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main()) 