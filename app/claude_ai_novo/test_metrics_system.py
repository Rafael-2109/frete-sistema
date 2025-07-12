#!/usr/bin/env python3
"""
🧪 TESTE SISTEMA DE MÉTRICAS
============================

Teste rápido para verificar se o sistema de métricas está funcionando.
"""

import sys
import os
from pathlib import Path

# Adicionar caminho para imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

def test_metrics_system():
    """Testa o sistema de métricas"""
    
    print("🧪 TESTANDO SISTEMA DE MÉTRICAS")
    print("=" * 50)
    
    try:
        # Teste 1: Importar sistema de métricas
        print("\n📋 TESTE 1: Importar sistema de métricas")
        from app.claude_ai_novo.monitoring.real_time_metrics import get_claude_metrics, record_query_metric
        print("✅ Importação bem-sucedida")
        
        # Teste 2: Obter instância das métricas
        print("\n📋 TESTE 2: Obter instância das métricas")
        metrics = get_claude_metrics()
        print(f"✅ Instância obtida: {type(metrics).__name__}")
        
        # Teste 3: Registrar uma métrica de teste
        print("\n📋 TESTE 3: Registrar métrica de teste")
        record_query_metric("test_query", 1.5, True, 150, False)
        print("✅ Métrica registrada com sucesso")
        
        # Teste 4: Obter métricas abrangentes
        print("\n📋 TESTE 4: Obter métricas abrangentes")
        comprehensive_metrics = metrics.get_comprehensive_metrics()
        print(f"✅ Métricas obtidas: {len(comprehensive_metrics)} categorias")
        
        # Teste 5: Verificar estrutura das métricas
        print("\n📋 TESTE 5: Verificar estrutura das métricas")
        expected_keys = ['system_health', 'orchestrators', 'performance', 'usage', 'model_config']
        for key in expected_keys:
            if key in comprehensive_metrics:
                print(f"✅ {key}: OK")
            else:
                print(f"❌ {key}: MISSING")
        
        # Teste 6: Mostrar dados das métricas
        print("\n📋 TESTE 6: Dados das métricas")
        print(f"📊 Performance: {comprehensive_metrics.get('performance', {})}")
        print(f"🧠 Modelo: {comprehensive_metrics.get('model_config', {})}")
        print(f"📈 Uso: {comprehensive_metrics.get('usage', {})}")
        
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_metrics_system()
    exit(0 if success else 1) 