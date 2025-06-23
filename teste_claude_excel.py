#!/usr/bin/env python3
"""
Teste do Claude Real com comando Excel
"""

import os
import sys

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.claude_ai.claude_real_integration import processar_com_claude_real

def testar_claude_excel():
    """Testa se o Claude Real detecta e processa comandos Excel"""
    print("🧪 Testando Claude Real com comando Excel...")
    
    # Criar contexto Flask
    app = create_app()
    
    with app.app_context():
        try:
            consulta = "Gere um relatório em excel das entregas pendentes com os agendamentos e protocolos"
            
            print(f"📝 Comando: {consulta}")
            print("🤖 Processando com Claude Real...")
            
            resultado = processar_com_claude_real(consulta, {
                'user_id': 1,
                'username': 'teste',
                'perfil': 'admin'
            })
            
            print("=" * 80)
            print("📋 RESULTADO DO CLAUDE REAL:")
            print("=" * 80)
            print(resultado)
            print("=" * 80)
            
            # Verificar se contém indicações de Excel
            if 'excel' in resultado.lower():
                print("✅ Claude detectou comando Excel")
            else:
                print("❌ Claude NÃO detectou comando Excel")
                
            if '/static/reports/' in resultado:
                print("✅ Link de download encontrado")
            else:
                print("❌ Link de download NÃO encontrado")
                
            if 'entregas_pendentes_' in resultado:
                print("✅ Arquivo de entregas pendentes mencionado")
            else:
                print("❌ Arquivo de entregas pendentes NÃO mencionado")
                
        except Exception as e:
            print(f"❌ Erro crítico: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    testar_claude_excel() 