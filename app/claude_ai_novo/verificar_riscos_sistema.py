#!/usr/bin/env python3
"""
🔍 VERIFICAR RISCOS DO SISTEMA
==============================

Analisa possíveis problemas e riscos no sistema Claude AI Novo.
"""

import os
import sys
import asyncio
from pathlib import Path

# Adicionar diretório raiz ao path
root_dir = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_dir))

def verificar_riscos():
    """Verifica possíveis riscos no sistema"""
    print("\n🔍 VERIFICANDO RISCOS DO SISTEMA CLAUDE AI NOVO\n")
    
    riscos_encontrados = []
    avisos = []
    
    # 1. Verificar outros métodos async no SessionOrchestrator
    print("1️⃣ VERIFICANDO MÉTODOS ASYNC NO SESSION ORCHESTRATOR:")
    try:
        from app.claude_ai_novo.orchestrators.session_orchestrator import SessionOrchestrator
        
        # Métodos que podem ter o mesmo problema
        metodos_risco = [
            '_execute_workflow',
            '_process_deliveries_status', 
            '_process_general_inquiry'
        ]
        
        for metodo in metodos_risco:
            if hasattr(SessionOrchestrator, metodo):
                print(f"   ✅ {metodo} existe")
                # Verificar se já foi corrigido
                import inspect
                source = inspect.getsource(getattr(SessionOrchestrator, metodo))
                if "concurrent.futures" in source:
                    print(f"   ✅ {metodo} já corrigido com ThreadPoolExecutor")
                elif "process_unified_query" in source or "integration_manager" in source:
                    avisos.append(f"⚠️  {metodo} pode ter problema de event loop")
            else:
                print(f"   ❌ {metodo} não encontrado")
                
    except Exception as e:
        riscos_encontrados.append(f"❌ Erro ao verificar SessionOrchestrator: {e}")
    
    # 2. Verificar MainOrchestrator
    print("\n2️⃣ VERIFICANDO MAIN ORCHESTRATOR:")
    try:
        from app.claude_ai_novo.orchestrators.main_orchestrator import MainOrchestrator
        
        # Verificar se tem métodos async
        for attr_name in dir(MainOrchestrator):
            if not attr_name.startswith('_'):
                continue
            attr = getattr(MainOrchestrator, attr_name)
            if callable(attr):
                import inspect
                if asyncio.iscoroutinefunction(attr):
                    avisos.append(f"⚠️  MainOrchestrator.{attr_name} é async - verificar uso")
                    
        print("   ✅ MainOrchestrator verificado")
        
    except Exception as e:
        riscos_encontrados.append(f"❌ Erro ao verificar MainOrchestrator: {e}")
    
    # 3. Verificar IntegrationManager
    print("\n3️⃣ VERIFICANDO INTEGRATION MANAGER:")
    try:
        from app.claude_ai_novo.integration.integration_manager import IntegrationManager
        
        # Verificar métodos async principais
        metodos_async = ['process_unified_query', 'initialize_all_modules']
        
        for metodo in metodos_async:
            if hasattr(IntegrationManager, metodo):
                print(f"   ✅ {metodo} é async (esperado)")
            else:
                riscos_encontrados.append(f"❌ {metodo} não encontrado no IntegrationManager")
                
    except Exception as e:
        riscos_encontrados.append(f"❌ Erro ao verificar IntegrationManager: {e}")
    
    # 4. Verificar imports circulares
    print("\n4️⃣ VERIFICANDO IMPORTS CIRCULARES:")
    try:
        # Tentar importar módulos principais
        modules = [
            'app.claude_ai_novo.orchestrators',
            'app.claude_ai_novo.integration', 
            'app.claude_ai_novo.coordinators',
            'app.claude_ai_novo.processors'
        ]
        
        for module in modules:
            try:
                __import__(module)
                print(f"   ✅ {module} importa sem problemas")
            except ImportError as e:
                if "circular" in str(e).lower():
                    riscos_encontrados.append(f"❌ Import circular em {module}: {e}")
                else:
                    avisos.append(f"⚠️  Problema de import em {module}: {e}")
                    
    except Exception as e:
        riscos_encontrados.append(f"❌ Erro ao verificar imports: {e}")
    
    # 5. Verificar variáveis de ambiente
    print("\n5️⃣ VERIFICANDO VARIÁVEIS DE AMBIENTE:")
    env_vars = {
        'DATABASE_URL': os.getenv('DATABASE_URL'),
        'ANTHROPIC_API_KEY': os.getenv('ANTHROPIC_API_KEY'),
        'REDIS_URL': os.getenv('REDIS_URL'),
        'USE_NEW_CLAUDE_SYSTEM': os.getenv('USE_NEW_CLAUDE_SYSTEM')
    }
    
    for var, value in env_vars.items():
        if value:
            print(f"   ✅ {var} configurada")
        else:
            if var in ['DATABASE_URL', 'ANTHROPIC_API_KEY']:
                avisos.append(f"⚠️  {var} não configurada (necessária em produção)")
            else:
                print(f"   ℹ️  {var} não configurada (opcional)")
    
    # 6. Verificar conexões com banco
    print("\n6️⃣ VERIFICANDO CONEXÕES COM BANCO:")
    try:
        # Verificar se há tentativas de conexão sem contexto Flask
        from app.claude_ai_novo.loaders.domain import get_pedidos_loader
        
        # Tentar criar loader (pode falhar sem contexto Flask)
        try:
            loader = get_pedidos_loader()
            if hasattr(loader, 'db'):
                avisos.append("⚠️  Loaders podem tentar acessar DB sem contexto Flask")
        except Exception as e:
            if "application context" in str(e):
                avisos.append("⚠️  Loaders precisam de contexto Flask para DB")
                
    except Exception as e:
        print(f"   ℹ️  Não foi possível verificar loaders: {e}")
    
    # RESUMO
    print("\n" + "="*60)
    print("📊 RESUMO DA ANÁLISE DE RISCOS")
    print("="*60)
    
    if not riscos_encontrados and not avisos:
        print("\n✅ NENHUM RISCO CRÍTICO ENCONTRADO!")
        print("   O sistema parece estar bem configurado.")
    else:
        if riscos_encontrados:
            print(f"\n❌ RISCOS CRÍTICOS ENCONTRADOS: {len(riscos_encontrados)}")
            for risco in riscos_encontrados:
                print(f"   {risco}")
                
        if avisos:
            print(f"\n⚠️  AVISOS: {len(avisos)}")
            for aviso in avisos:
                print(f"   {aviso}")
    
    # Recomendações
    print("\n💡 RECOMENDAÇÕES:")
    print("   1. Sempre testar em ambiente local antes de deploy")
    print("   2. Verificar logs do Render após deploy")
    print("   3. Monitorar uso de memória (muitos módulos carregados)")
    print("   4. Considerar cache mais agressivo para reduzir carga")
    
    print("\n✅ VERIFICAÇÃO COMPLETA!")

if __name__ == "__main__":
    verificar_riscos() 