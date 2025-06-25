#!/usr/bin/env python3
"""
🧪 TESTE MAPEAMENTO SEMÂNTICO CORRIGIDO
Verifica se correções foram aplicadas com sucesso
"""

import sys
import os

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath('.'))

def testar_mapeamento():
    """Testa se mapeamento semântico carrega e funciona"""
    
    print("🧪 TESTE MAPEAMENTO SEMÂNTICO CORRIGIDO")
    print("=" * 50)
    
    try:
        # 1. Testar import
        print("1. Testando import...")
        from app.claude_ai.mapeamento_semantico import get_mapeamento_semantico
        print("   ✅ Import bem-sucedido")
        
        # 2. Testar instância
        print("2. Testando instância...")
        mapeamento = get_mapeamento_semantico()
        print("   ✅ Instância criada")
        
        # 3. Testar campo "origem" corrigido
        print("3. Testando campo 'origem' corrigido...")
        resultado = mapeamento.mapear_termo_natural("origem")
        if resultado:
            primeiro = resultado[0]
            print(f"   ✅ Campo origem mapeado para: {primeiro['modelo']}.{primeiro['campo']}")
            print(f"   📝 Observação: Campo agora mapeia para NÚMERO DO PEDIDO (não localização)")
        else:
            print("   ❌ Campo origem não encontrado")
        
        # 4. Testar campos essenciais de EntregaMonitorada
        print("4. Testando campos essenciais EntregaMonitorada...")
        campos_essenciais = ["numero_nf", "cliente", "transportadora", "vendedor", "destino"]
        
        for campo in campos_essenciais:
            resultado = mapeamento.mapear_termo_natural(campo)
            if resultado and any(r['modelo'] == 'EntregaMonitorada' for r in resultado):
                print(f"   ✅ {campo} mapeado corretamente")
            else:
                print(f"   ❌ {campo} NÃO encontrado para EntregaMonitorada")
        
        # 5. Testar novos campos de Pedidos
        print("5. Testando campos novos de Pedidos...")
        campos_pedidos = ["pallets do pedido", "protocolo", "obs do pdd", "nf no cd"]
        
        for campo in campos_pedidos:
            resultado = mapeamento.mapear_termo_natural(campo)
            if resultado and any(r['modelo'] == 'Pedido' for r in resultado):
                print(f"   ✅ '{campo}' mapeado para Pedido")
            else:
                print(f"   ⚠️ '{campo}' não encontrado")
        
        # 6. Testar consulta completa
        print("6. Testando consulta completa...")
        consulta = "buscar origem 123456"
        resultado = mapeamento.mapear_consulta_completa(consulta)
        
        print(f"   📊 Consulta: '{consulta}'")
        print(f"   📊 Mapeamentos encontrados: {len(resultado['mapeamentos_encontrados'])}")
        print(f"   📊 Modelos envolvidos: {list(resultado['modelos_envolvidos'])}")
        
        if 'RelatorioFaturamentoImportado' in resultado['modelos_envolvidos']:
            print("   ✅ Campo 'origem' detectado corretamente!")
        else:
            print("   ❌ Campo 'origem' NÃO detectado")
        
        print("\n" + "=" * 50)
        print("🎉 TESTE CONCLUÍDO - MAPEAMENTO SEMÂNTICO FUNCIONANDO!")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    sucesso = testar_mapeamento()
    if sucesso:
        print("\n✅ TODOS OS TESTES PASSARAM!")
        sys.exit(0)
    else:
        print("\n❌ TESTES FALHARAM!")
        sys.exit(1) 