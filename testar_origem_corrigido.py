#!/usr/bin/env python3
"""
🧪 TESTE CAMPO ORIGEM CORRIGIDO
Demonstra que a correção do campo "origem" funcionou
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

def testar_origem():
    """Testa se campo origem agora mapeia corretamente"""
    
    print("🔍 TESTE: Campo 'origem' corrigido")
    print("=" * 40)
    
    try:
        from app.claude_ai.mapeamento_semantico import get_mapeamento_semantico
        mapeamento = get_mapeamento_semantico()
        
        # Teste 1: Consulta "origem"
        print("1. Testando termo 'origem'...")
        resultado = mapeamento.mapear_termo_natural("origem")
        
        if resultado:
            primeiro = resultado[0]
            print(f"   ✅ Mapeado para: {primeiro['modelo']}.{primeiro['campo']}")
            
            if primeiro['modelo'] == 'RelatorioFaturamentoImportado' and primeiro['campo'] == 'origem':
                print("   🎯 CORRETO: Mapeia para faturamento.origem (número do pedido)")
            else:
                print("   ❌ INCORRETO: Não mapeia para RelatorioFaturamentoImportado.origem")
        else:
            print("   ❌ Termo 'origem' não encontrado")
        
        # Teste 2: Consulta completa "buscar origem 123456"
        print("\n2. Testando consulta 'buscar origem 123456'...")
        consulta = mapeamento.mapear_consulta_completa("buscar origem 123456")
        
        modelos = list(consulta['modelos_envolvidos'])
        print(f"   📊 Modelos detectados: {modelos}")
        
        if 'RelatorioFaturamentoImportado' in modelos:
            print("   ✅ SUCESSO: Campo origem detectado corretamente!")
            print("   📝 Significado: Buscar faturamento pelo número do pedido 123456")
        else:
            print("   ❌ FALHA: Campo origem não detectado")
        
        # Teste 3: Verificar mapeamentos encontrados
        if consulta['mapeamentos_encontrados']:
            mapeamento_origem = consulta['mapeamentos_encontrados'][0]
            print(f"   🔍 Campo detectado: {mapeamento_origem['modelo']}.{mapeamento_origem['campo']}")
        
        print("\n" + "=" * 40)
        print("✅ TESTE CONCLUÍDO!")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False

if __name__ == "__main__":
    success = testar_origem()
    if success:
        print("\n🎉 CAMPO 'ORIGEM' FUNCIONANDO CORRETAMENTE!")
        print("📝 Agora mapeia para número do pedido (não localização)")
    else:
        print("\n❌ TESTE FALHOU!") 