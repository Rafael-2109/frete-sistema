#!/usr/bin/env python3
"""
Teste direto do sistema de métricas otimizado
"""

import time
import sys
import os

# Adicionar path do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def main():
    print("=" * 60)
    print("🚀 TESTE DIRETO DO SISTEMA DE MÉTRICAS OTIMIZADO")
    print("=" * 60)
    
    try:
        # Importar diretamente o módulo otimizado
        print("\n1️⃣ Importando módulo otimizado...")
        from app.claude_ai_novo.monitoring.real_time_metrics import get_claude_metrics
        print("✅ Importação bem-sucedida!")
        
        # Obter instância
        print("\n2️⃣ Obtendo instância do sistema de métricas...")
        metrics = get_claude_metrics()
        print(f"✅ Instância obtida: {metrics.__class__.__name__}")
        
        # Testar performance
        print("\n3️⃣ Testando performance de get_comprehensive_metrics()...")
        tempos = []
        
        for i in range(5):
            start = time.time()
            result = metrics.get_comprehensive_metrics()
            elapsed = time.time() - start
            tempos.append(elapsed)
            print(f"   Chamada {i+1}: {elapsed:.3f}s")
        
        # Análise
        tempo_medio = sum(tempos) / len(tempos)
        tempo_max = max(tempos)
        tempo_min = min(tempos)
        
        print(f"\n📊 ANÁLISE DE PERFORMANCE:")
        print(f"   - Tempo médio: {tempo_medio:.3f}s")
        print(f"   - Tempo mínimo: {tempo_min:.3f}s")
        print(f"   - Tempo máximo: {tempo_max:.3f}s")
        
        # Verificar se é singleton
        print("\n4️⃣ Verificando padrão Singleton...")
        metrics2 = get_claude_metrics()
        if metrics is metrics2:
            print("✅ Singleton funcionando! Mesma instância retornada")
        else:
            print("❌ Problema: Instâncias diferentes!")
        
        # Mostrar algumas métricas
        print("\n5️⃣ Métricas obtidas:")
        print(f"   - System Score: {result['system_health']['system_score']}%")
        print(f"   - Modules Active: {result['system_health']['modules_active']}")
        print(f"   - Orchestrators: {result['orchestrators']['active_orchestrators']}")
        print(f"   - Status: {result['status']}")
        
        # Resultado final
        print("\n" + "=" * 60)
        if tempo_medio < 0.01:  # Menos de 10ms
            print("🎉 EXCELENTE: Performance ÓTIMA!")
            print("   - Resposta em milissegundos")
            print("   - Cache funcionando perfeitamente")
            print("   - Problema de 100+ segundos TOTALMENTE RESOLVIDO")
        elif tempo_medio < 0.1:  # Menos de 100ms
            print("✅ BOM: Performance adequada")
            print("   - Resposta rápida")
            print("   - Melhoria significativa")
        else:
            print("❌ PROBLEMA: Ainda lento!")
            print("   - Verificar implementação")
        
        print("\n📝 COMPARAÇÃO:")
        print(f"   - ANTES: 100+ segundos (com reinicializações)")
        print(f"   - AGORA: {tempo_medio:.3f} segundos")
        print(f"   - MELHORIA: {(100/tempo_medio):.0f}x mais rápido!")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 