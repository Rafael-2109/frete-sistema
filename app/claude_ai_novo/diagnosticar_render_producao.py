"""
🔍 DIAGNÓSTICO DO PROBLEMA NO RENDER
===================================

Script para identificar por que não funciona no Render.
"""

import os
import sys
from pathlib import Path

# Adicionar caminho ao sistema
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

print("🔍 DIAGNÓSTICO DO RENDER\n")

# 1. Verificar ambiente
print("1️⃣ AMBIENTE:")
print(f"   - Sistema: {sys.platform}")
print(f"   - Python: {sys.version}")
print(f"   - DATABASE_URL existe: {'DATABASE_URL' in os.environ}")
print(f"   - FLASK_ENV: {os.environ.get('FLASK_ENV', 'não definido')}")
print(f"   - Rodando no Render: {'RENDER' in os.environ}")

# 2. Verificar Flask
print("\n2️⃣ CONTEXTO FLASK:")
try:
    from flask import current_app, has_app_context
    print(f"   - Flask importado: ✅")
    print(f"   - Tem contexto ativo: {has_app_context()}")
except Exception as e:
    print(f"   - Erro ao importar Flask: {e}")

# 3. Verificar aplicação
print("\n3️⃣ APLICAÇÃO:")
try:
    from app import create_app
    print(f"   - create_app disponível: ✅")
    
    # Tentar criar app
    app = create_app()
    print(f"   - App criada: ✅")
    
    # Verificar contexto
    with app.app_context():
        print(f"   - Contexto criado: ✅")
        
        # Tentar acessar banco
        try:
            from app import db
            from sqlalchemy import text
            
            # Teste simples
            result = db.session.execute(text("SELECT 1")).scalar()
            print(f"   - Banco acessível: ✅ (resultado: {result})")
            
        except Exception as db_error:
            print(f"   - Erro no banco: {db_error}")
            
except Exception as app_error:
    print(f"   - Erro na aplicação: {app_error}")

# 4. Testar loaders
print("\n4️⃣ LOADERS:")
try:
    from app.claude_ai_novo.loaders import get_loader_manager
    from app.claude_ai_novo.loaders.domain.entregas_loader import EntregasLoader
    
    print(f"   - Imports OK: ✅")
    
    # Testar criação
    loader_manager = get_loader_manager()
    print(f"   - LoaderManager criado: ✅")
    
    # Testar loader específico
    entregas_loader = EntregasLoader()
    print(f"   - EntregasLoader criado: ✅")
    
    # Testar com contexto
    if 'app' in locals():
        with app.app_context():
            try:
                data = entregas_loader.load_data({'cliente': 'teste'})
                print(f"   - load_data executou: ✅")
                print(f"   - Registros: {data.get('total_registros', 0)}")
            except Exception as load_error:
                print(f"   - Erro no load_data: {load_error}")
                import traceback
                traceback.print_exc()
    else:
        print(f"   - Sem app para testar load_data")
        
except Exception as loader_error:
    print(f"   - Erro nos loaders: {loader_error}")
    import traceback
    traceback.print_exc()

# 5. Verificar rota
print("\n5️⃣ ROTAS FLASK:")
try:
    if 'app' in locals():
        with app.app_context():
            # Listar rotas relacionadas ao Claude
            for rule in app.url_map.iter_rules():
                if 'claude' in str(rule):
                    print(f"   - {rule}")
except Exception as route_error:
    print(f"   - Erro nas rotas: {route_error}")

# 6. Testar fluxo completo
print("\n6️⃣ FLUXO COMPLETO:")
try:
    if 'app' in locals():
        with app.app_context():
            from app.claude_ai_novo import get_claude_ai_instance
            
            # Obter instância
            claude = get_claude_ai_instance()
            print(f"   - Claude AI criado: ✅")
            
            # Testar query
            result = claude.process_query_sync(
                "Quantas entregas do Atacadão nos últimos 30 dias?",
                {"user_id": "teste"}
            )
            
            print(f"   - Query processada: ✅")
            print(f"   - Tem resposta: {'agent_response' in result}")
            
            if 'agent_response' in result:
                response = result['agent_response']
                if isinstance(response, dict):
                    response_text = response.get('response', '')
                else:
                    response_text = str(response)
                
                print(f"   - Tamanho resposta: {len(response_text)} chars")
                print(f"   - Primeiros 200 chars: {response_text[:200]}...")
                
except Exception as flow_error:
    print(f"   - Erro no fluxo: {flow_error}")
    import traceback
    traceback.print_exc()

print("\n" + "="*60)
print("📋 RESUMO DO DIAGNÓSTICO")
print("="*60)

# Conclusões
if 'RENDER' in os.environ:
    print("✅ Rodando no Render")
else:
    print("⚠️  NÃO está no Render (teste local)")

if 'has_app_context' in locals() and has_app_context():
    print("✅ Tem contexto Flask ativo")
else:
    print("❌ SEM contexto Flask - esse é o problema!")

print("\n💡 SOLUÇÕES:")
print("1. Se não tem contexto Flask, criar com app.app_context()")
print("2. Verificar se a rota está criando contexto corretamente")
print("3. Verificar logs do Render para erros de inicialização") 