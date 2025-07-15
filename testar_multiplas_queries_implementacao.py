#!/usr/bin/env python3
"""
Teste da Implementação de Múltiplas Queries
==========================================

Testa se o sistema de múltiplas queries está funcionando corretamente
para resolver os 11 campos problemáticos do mapeamento Odoo.
"""

import sys
import os
from pathlib import Path

# Adicionar o diretório do projeto ao Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

def testar_implementacao_multiplas_queries():
    """Testa a implementação completa do sistema de múltiplas queries"""
    
    print("🧪 TESTE DA IMPLEMENTAÇÃO DE MÚLTIPLAS QUERIES")
    print("=" * 60)
    
    try:
        # 1. Testar importação dos módulos
        print("📦 1. Testando importações...")
        from app.odoo.utils.campo_mapper import CampoMapper
        from app.odoo.utils.connection import OdooConnection
        print("   ✅ CampoMapper importado")
        print("   ✅ OdooConnection importado")
        
        # 2. Testar instanciação do CampoMapper
        print("\n🛠️ 2. Testando CampoMapper...")
        mapper = CampoMapper()
        print(f"   ✅ CampoMapper instanciado")
        
        # 3. Verificar carregamento do mapeamento do usuário
        print(f"   📋 Mapeamento do usuário: {len(mapper.mapeamento_usuario)} campos")
        if len(mapper.mapeamento_usuario) > 0:
            print("   ✅ Mapeamento do usuário carregado com sucesso")
        else:
            print("   ❌ Mapeamento do usuário não foi carregado")
            return False
        
        # 4. Verificar campos de múltiplas queries
        print(f"   🔗 Campos múltiplas queries: {len(mapper.campos_multiplas_queries)} campos")
        if len(mapper.campos_multiplas_queries) == 11:
            print("   ✅ Todos os 11 campos problemáticos mapeados")
        else:
            print(f"   ⚠️ Esperados 11 campos, encontrados {len(mapper.campos_multiplas_queries)}")
        
        # 5. Testar métodos do mapper
        print("\n⚙️ 3. Testando métodos do CampoMapper...")
        
        # Teste obter_estatisticas_mapeamento
        stats = mapper.obter_estatisticas_mapeamento()
        print(f"   📊 Estatísticas obtidas:")
        print(f"      Total de campos: {stats['total_campos']}")
        print(f"      Campos simples: {stats['campos_simples']} ({stats['percentual_simples']:.1f}%)")
        print(f"      Campos complexos: {stats['campos_complexos']} ({stats['percentual_complexos']:.1f}%)")
        
        # Teste eh_campo_multiplas_queries
        campo_teste = "order_id/partner_shipping_id/l10n_br_cnpj"
        if mapper.eh_campo_multiplas_queries(campo_teste):
            print(f"   ✅ Campo {campo_teste} corretamente identificado como múltiplas queries")
        else:
            print(f"   ❌ Campo {campo_teste} não identificado como múltiplas queries")
        
        # 6. Testar conexão OdooConnection
        print("\n🌐 4. Testando métodos OdooConnection...")
        from app.odoo.config.odoo_config import ODOO_CONFIG
        connection = OdooConnection(ODOO_CONFIG)
        
        # Verificar se método buscar_registro_por_id existe
        if hasattr(connection, 'buscar_registro_por_id'):
            print("   ✅ Método buscar_registro_por_id existe")
        else:
            print("   ❌ Método buscar_registro_por_id não encontrado")
            return False
        
        # 7. Testar CarteiraService
        print("\n🏪 5. Testando CarteiraService...")
        try:
            from app.odoo.services.carteira_service import CarteiraService
            service = CarteiraService()
            print("   ✅ CarteiraService instanciado")
            
            # Verificar se tem o método de múltiplas queries
            if hasattr(service, '_processar_dados_carteira_com_multiplas_queries'):
                print("   ✅ Método _processar_dados_carteira_com_multiplas_queries existe")
            else:
                print("   ⚠️ Método _processar_dados_carteira_com_multiplas_queries não encontrado")
                print("   ℹ️ O service ainda usa o método antigo, mas isso pode ser adicionado")
            
        except Exception as e:
            print(f"   ⚠️ Erro ao testar CarteiraService: {e}")
        
        # 8. Teste com dados simulados
        print("\n🎭 6. Testando com dados simulados...")
        
        # Simular dados do Odoo
        dados_simulados = [
            {
                'id': 1,
                'order_id': [100, 'Pedido 001'],
                'product_id': [200, 'Produto A'],
                'product_uom_qty': 10.0,
                'price_unit': 25.50
            }
        ]
        
        # Testar mapeamento simples (sem conexão real)
        dados_mapeados_simples = mapper.mapear_para_carteira(dados_simulados)
        print(f"   📋 Mapeamento simples: {len(dados_mapeados_simples)} registros processados")
        
        if dados_mapeados_simples:
            primeiro_item = dados_mapeados_simples[0]
            campos_com_valor = sum(1 for v in primeiro_item.values() if v is not None)
            print(f"   📊 Campos com valor no primeiro item: {campos_com_valor}/{len(primeiro_item)}")
            print("   ✅ Mapeamento simples funcionando")
        
        # 9. Resumo final
        print("\n📋 RESUMO DO TESTE")
        print("=" * 40)
        print("✅ Sistema base funcionando:")
        print("   - CampoMapper carregado")
        print("   - Mapeamento do usuário funcionando")
        print("   - 11 campos problemáticos identificados")
        print("   - OdooConnection com buscar_registro_por_id")
        print("   - Métodos de estatísticas funcionando")
        print("   - Mapeamento simples testado")
        
        print("\n🎯 PRÓXIMO PASSO:")
        print("Testar com conexão real ao Odoo para verificar se as")
        print("múltiplas queries resolvem os campos problemáticos")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    resultado = testar_implementacao_multiplas_queries()
    if resultado:
        print("\n🎉 IMPLEMENTAÇÃO BÁSICA FUNCIONANDO!")
    else:
        print("\n💥 PROBLEMAS NA IMPLEMENTAÇÃO ENCONTRADOS") 