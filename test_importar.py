#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para testar o endpoint /separacao/importar
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from flask import url_for

def testar_importar():
    """Testa se o endpoint está registrado corretamente"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("TESTE DO ENDPOINT /separacao/importar")
        print("="*60)
        
        # Verificar se a rota está registrada
        print("\n🔍 Verificando rotas registradas...")
        
        with app.test_request_context():
            try:
                # Tentar gerar URL para a rota
                url = url_for('separacao.importar')
                print(f"✅ Rota encontrada: {url}")
            except Exception as e:
                print(f"❌ Erro ao encontrar rota: {e}")
                
        # Listar todas as rotas de separação
        print("\n📋 Todas as rotas do blueprint 'separacao':")
        for rule in app.url_map.iter_rules():
            if 'separacao' in rule.endpoint:
                print(f"   {rule.methods} {rule.rule} -> {rule.endpoint}")
        
        # Testar com cliente de teste
        print("\n🧪 Testando requisição GET...")
        client = app.test_client()
        
        try:
            response = client.get('/separacao/importar')
            print(f"   Status Code: {response.status_code}")
            
            if response.status_code == 200:
                print("   ✅ Endpoint acessível")
            elif response.status_code == 302:
                print(f"   ⚠️ Redirecionamento para: {response.location}")
            elif response.status_code == 401:
                print("   ⚠️ Requer autenticação")
            elif response.status_code == 404:
                print("   ❌ Rota não encontrada")
            else:
                print(f"   ❓ Status inesperado: {response.status_code}")
                
            # Verificar se há erros no response
            if response.data:
                data_str = response.data.decode('utf-8')
                if 'error' in data_str.lower() or 'exception' in data_str.lower():
                    print("\n⚠️ Possível erro no HTML:")
                    # Procurar por mensagens de erro
                    import re
                    errors = re.findall(r'<pre.*?>(.*?)</pre>', data_str, re.DOTALL)
                    for error in errors[:2]:  # Mostrar até 2 erros
                        print(f"   {error[:200]}...")
                        
        except Exception as e:
            print(f"❌ Erro ao testar endpoint: {e}")
            import traceback
            traceback.print_exc()
        
        print("\n" + "="*60)
        print("TESTE CONCLUÍDO")
        print("="*60 + "\n")

if __name__ == "__main__":
    testar_importar()