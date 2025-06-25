#!/usr/bin/env python3
"""
Script para verificar status do Sistema Avançado de IA no Render
"""

import psycopg2
import requests
from datetime import datetime

def verificar_tabelas_render():
    """Verifica tabelas AI no PostgreSQL do Render"""
    print("🔍 VERIFICANDO TABELAS NO RENDER...")
    
    try:
        # Conectar ao PostgreSQL do Render
        conn = psycopg2.connect(
            host='dpg-d13m38vfte5s738t6p50-a.oregon-postgres.render.com',
            port=5432,
            database='sistema_fretes',
            user='sistema_user',
            password='R80cswDpRJGsmpTdA73XxvV2xqEfzYm9'
        )
        
        cursor = conn.cursor()
        
        # Verificar tabelas AI
        cursor.execute("""
            SELECT table_name, 
                   (SELECT count(*) FROM information_schema.columns WHERE table_name = t.table_name) as colunas
            FROM information_schema.tables t
            WHERE table_name LIKE 'ai_%' AND table_schema = 'public'
            ORDER BY table_name
        """)
        
        tabelas = cursor.fetchall()
        
        print(f"\n📊 TABELAS DE IA ENCONTRADAS: {len(tabelas)}")
        for tabela, colunas in tabelas:
            print(f"  ✅ {tabela} ({colunas} colunas)")
        
        # Verificar configurações
        cursor.execute("SELECT config_key, description FROM ai_system_config ORDER BY config_key")
        configs = cursor.fetchall()
        
        print(f"\n⚙️ CONFIGURAÇÕES SISTEMA: {len(configs)}")
        for config, desc in configs:
            print(f"  ✅ {config}: {desc}")
        
        # Verificar índices
        cursor.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename LIKE 'ai_%' 
            ORDER BY indexname
        """)
        indices = cursor.fetchall()
        
        print(f"\n📈 ÍNDICES CRIADOS: {len(indices)}")
        for idx in indices[:5]:  # Mostrar apenas os primeiros 5
            print(f"  ✅ {idx[0]}")
        if len(indices) > 5:
            print(f"  ... e mais {len(indices) - 5} índices")
        
        cursor.close()
        conn.close()
        
        return len(tabelas) == 6  # Esperamos 6 tabelas
        
    except Exception as e:
        print(f"❌ Erro ao verificar tabelas: {e}")
        return False

def testar_rotas_avancadas():
    """Testa as rotas avançadas do sistema"""
    print("\n🚀 TESTANDO ROTAS AVANÇADAS...")
    
    base_url = "https://sistema-fretes.onrender.com"
    
    rotas_testar = [
        "/claude-ai/advanced-dashboard",
        "/claude-ai/advanced-feedback-interface",
        "/api/advanced-analytics",
    ]
    
    resultados = {}
    
    for rota in rotas_testar:
        try:
            response = requests.get(f"{base_url}{rota}", timeout=10)
            status = "✅ OK" if response.status_code == 200 else f"⚠️ {response.status_code}"
            resultados[rota] = status
            print(f"  {status} {rota}")
        except Exception as e:
            resultados[rota] = f"❌ ERRO"
            print(f"  ❌ ERRO {rota}: {str(e)[:50]}...")
    
    return resultados

def testar_api_health():
    """Testa API de health check avançado"""
    print("\n🏥 TESTANDO HEALTH CHECK AVANÇADO...")
    
    try:
        response = requests.get(
            "https://sistema-fretes.onrender.com/claude-ai/api/system-health-advanced",
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                health = data.get('health_status', {})
                overall = health.get('overall_status', 'unknown')
                components = health.get('components', {})
                
                print(f"  ✅ Status Geral: {overall.upper()}")
                print(f"  🔧 Componentes: {len(components)}")
                
                for comp_name, comp_data in components.items():
                    status_icon = "✅" if comp_data.get('status') == 'healthy' else "⚠️"
                    print(f"    {status_icon} {comp_data.get('label', comp_name)}: {comp_data.get('status')}")
                
                return overall == 'healthy'
            else:
                print(f"  ❌ Health check falhou: {data.get('error', 'Erro desconhecido')}")
                return False
        else:
            print(f"  ❌ HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Erro no health check: {e}")
        return False

def testar_consulta_simples():
    """Testa uma consulta simples via API"""
    print("\n🤖 TESTANDO CONSULTA SIMPLES...")
    
    try:
        response = requests.post(
            "https://sistema-fretes.onrender.com/claude-ai/api/advanced-query",
            json={
                "query": "Status geral do sistema hoje",
                "test_mode": True
            },
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("  ✅ Consulta processada com sucesso")
                print(f"  🆔 Session ID: {data.get('session_id', 'N/A')}")
                
                metadata = data.get('metadata', {})
                features = data.get('advanced_features', {})
                
                print(f"  🧠 Multi-Agent: {'✅' if features.get('multi_agent_used') else '❌'}")
                print(f"  🔄 Loop Semântico: {'✅' if features.get('semantic_loop_applied') else '❌'}")
                print(f"  📊 Confiança: {metadata.get('confidence_score', 'N/A')}")
                
                return True
            else:
                print(f"  ❌ Consulta falhou: {data.get('error', 'Erro desconhecido')}")
                return False
        else:
            print(f"  ❌ HTTP {response.status_code}")
            return False
            
    except Exception as e:
        print(f"  ❌ Erro na consulta: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("🧪 VERIFICAÇÃO COMPLETA DO SISTEMA AVANÇADO DE IA")
    print("=" * 60)
    print(f"📅 Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    # Testes
    resultados = {
        'tabelas_ok': verificar_tabelas_render(),
        'rotas_ok': len([r for r in testar_rotas_avancadas().values() if 'OK' in r]) > 0,
        'health_ok': testar_api_health(),
        'consulta_ok': testar_consulta_simples()
    }
    
    # Resumo
    print("\n" + "=" * 60)
    print("📋 RESUMO DOS TESTES")
    print("=" * 60)
    
    testes_passaram = 0
    total_testes = len(resultados)
    
    for teste, resultado in resultados.items():
        status = "✅ PASSOU" if resultado else "❌ FALHOU"
        print(f"{status} {teste.replace('_', ' ').title()}")
        if resultado:
            testes_passaram += 1
    
    print(f"\n🎯 RESULTADO FINAL: {testes_passaram}/{total_testes} testes passaram")
    
    if testes_passaram == total_testes:
        print("🎉 SISTEMA AVANÇADO 100% OPERACIONAL!")
        print("\n🚀 PRÓXIMOS PASSOS:")
        print("1. Acesse /claude-ai/advanced-dashboard para dashboard executivo")
        print("2. Teste consultas complexas no Claude AI")
        print("3. Use /claude-ai/advanced-feedback-interface para feedback")
        print("4. Sistema pronto para Semana 5-6 do roadmap (FAISS + Produção)")
    else:
        print("⚠️ Alguns testes falharam - verificar logs acima")
        print("\n🔧 AÇÕES NECESSÁRIAS:")
        if not resultados['tabelas_ok']:
            print("- Executar novamente aplicar_tabelas_avancadas.py")
        if not resultados['health_ok']:
            print("- Verificar logs do sistema no Render")
        if not resultados['consulta_ok']:
            print("- Verificar configuração da ANTHROPIC_API_KEY")

if __name__ == "__main__":
    main() 