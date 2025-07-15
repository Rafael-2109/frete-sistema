#!/usr/bin/env python3
"""
Teste do FaturamentoMapper
==========================

Testa se o sistema de múltiplas queries para faturamento está funcionando corretamente
para resolver campos complexos do mapeamento de faturamento.
"""

import sys
import os
from pathlib import Path

# Adicionar o diretório do projeto ao Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

def testar_faturamento_mapper():
    """Testa a implementação completa do FaturamentoMapper"""
    
    print("🧪 TESTE DO FATURAMENTO MAPPER")
    print("=" * 50)
    
    try:
        # 1. Testar importação do FaturamentoMapper
        print("📦 1. Testando importação do FaturamentoMapper...")
        from app.odoo.utils.faturamento_mapper import FaturamentoMapper
        print("   ✅ FaturamentoMapper importado com sucesso")
        
        # 2. Testar instanciação
        print("\n🛠️ 2. Testando instanciação do FaturamentoMapper...")
        mapper = FaturamentoMapper()
        print("   ✅ FaturamentoMapper instanciado com sucesso")
        
        # 3. Verificar mapeamento hardcoded
        print(f"\n📋 3. Verificando mapeamento hardcoded...")
        print(f"   📋 Mapeamento de faturamento: {len(mapper.mapeamento_faturamento)} campos")
        
        if len(mapper.mapeamento_faturamento) > 0:
            print("   ✅ Mapeamento hardcoded carregado com sucesso")
            
            # Mostrar alguns campos como exemplo
            print("   📝 Exemplos de mapeamento:")
            exemplos = list(mapper.mapeamento_faturamento.items())[:5]
            for campo_faturamento, campo_odoo in exemplos:
                print(f"      {campo_faturamento} -> {campo_odoo}")
        else:
            print("   ❌ Mapeamento hardcoded não foi carregado")
            return False
        
        # 4. Verificar campos de múltiplas queries
        print(f"\n🔗 4. Verificando campos de múltiplas queries...")
        print(f"   🔗 Campos múltiplas queries: {len(mapper.campos_multiplas_queries)} campos")
        
        if len(mapper.campos_multiplas_queries) > 0:
            print("   ✅ Campos de múltiplas queries identificados")
            
            # Mostrar exemplos
            print("   📝 Exemplos de campos complexos:")
            exemplos_complexos = list(mapper.campos_multiplas_queries.keys())[:3]
            for campo in exemplos_complexos:
                print(f"      {campo}")
        else:
            print("   ⚠️ Nenhum campo de múltiplas queries identificado")
        
        # 5. Testar métodos do mapper
        print("\n⚙️ 5. Testando métodos do FaturamentoMapper...")
        
        # Teste obter_estatisticas_mapeamento
        stats = mapper.obter_estatisticas_mapeamento()
        print(f"   📊 Estatísticas obtidas:")
        print(f"      Total de campos: {stats['total_campos']}")
        print(f"      Campos simples: {stats['campos_simples']} ({stats['percentual_simples']:.1f}%)")
        print(f"      Campos complexos: {stats['campos_complexos']} ({stats['percentual_complexos']:.1f}%)")
        print(f"      Campos calculados: {stats['campos_calculados']} ({stats['percentual_calculados']:.1f}%)")
        
        # Teste eh_campo_multiplas_queries
        campo_teste = "partner_id/l10n_br_cnpj"
        if mapper.eh_campo_multiplas_queries(campo_teste):
            print(f"   ✅ Campo {campo_teste} corretamente identificado como múltiplas queries")
        else:
            print(f"   ⚠️ Campo {campo_teste} não identificado como múltiplas queries")
        
        # 6. Testar FaturamentoService
        print("\n🏪 6. Testando FaturamentoService...")
        try:
            from app.odoo.services.faturamento_service import FaturamentoService
            service = FaturamentoService()
            print("   ✅ FaturamentoService instanciado com sucesso")
            
            # Verificar se tem o FaturamentoMapper integrado
            if hasattr(service, 'mapper') and isinstance(service.mapper, FaturamentoMapper):
                print("   ✅ FaturamentoMapper integrado ao FaturamentoService")
            else:
                print("   ❌ FaturamentoMapper não está integrado ao FaturamentoService")
                return False
            
        except Exception as e:
            print(f"   ❌ Erro ao testar FaturamentoService: {e}")
            return False
        
        # 7. Teste com dados simulados de faturamento
        print("\n🎭 7. Testando com dados simulados de faturamento...")
        
        # Simular dados do Odoo para account.move.line
        dados_simulados_faturamento = [
            {
                'id': 1,
                'move_id': [100, 'INV/2025/001'],
                'partner_id': [500, 'ACME Corp'],
                'product_id': [200, 'PRODUTO-A'],
                'quantity': 10.0,
                'price_unit': 25.50,
                'price_total': 255.00,
                'date': '2025-01-15'
            },
            {
                'id': 2,
                'move_id': [101, 'INV/2025/002'], 
                'partner_id': [501, 'Tech Solutions'],
                'product_id': [201, 'PRODUTO-B'],
                'quantity': 5.0,
                'price_unit': 100.00,
                'price_total': 500.00,
                'date': '2025-01-16'
            }
        ]
        
        # Testar mapeamento simples (sem conexão real)
        dados_mapeados_simples = mapper.mapear_para_faturamento(dados_simulados_faturamento)
        print(f"   📋 Mapeamento simples: {len(dados_mapeados_simples)} registros processados")
        
        if dados_mapeados_simples:
            primeiro_item = dados_mapeados_simples[0]
            campos_com_valor = sum(1 for v in primeiro_item.values() if v is not None and v != '')
            print(f"   📊 Campos com valor no primeiro item: {campos_com_valor}/{len(primeiro_item)}")
            
            # Mostrar alguns campos mapeados
            print("   📝 Exemplos de campos mapeados:")
            for campo, valor in list(primeiro_item.items())[:5]:
                print(f"      {campo}: {valor}")
            
            print("   ✅ Mapeamento simples de faturamento funcionando")
        else:
            print("   ❌ Mapeamento simples de faturamento falhou")
            return False
        
        # 8. Testar campos calculados
        print("\n🧮 8. Testando campos calculados...")
        
        # Simular item com dados para cálculo
        item_teste = {
            'peso_unitario_produto': 2.5,
            'qtd_produto_faturado': 10.0,
            'valor_produto_faturado': 250.0,
            'municipio': 'Fortaleza (CE)'
        }
        
        item_calculado = mapper._processar_campos_calculados(item_teste)
        
        peso_total_esperado = 2.5 * 10.0
        preco_unitario_esperado = 250.0 / 10.0
        
        if (item_calculado['peso_total'] == peso_total_esperado and 
            item_calculado['preco_produto_faturado'] == preco_unitario_esperado and
            item_calculado['municipio'] == 'Fortaleza' and
            item_calculado['estado'] == 'CE'):
            print("   ✅ Campos calculados funcionando corretamente")
            print(f"      peso_total: {item_calculado['peso_total']}")
            print(f"      preco_produto_faturado: {item_calculado['preco_produto_faturado']}")
            print(f"      municipio: {item_calculado['municipio']}")
            print(f"      estado: {item_calculado['estado']}")
        else:
            print("   ❌ Campos calculados com problemas")
            return False
        
        # 9. Resumo final
        print("\n📋 RESUMO DO TESTE")
        print("=" * 40)
        print("✅ Sistema de faturamento funcionando:")
        print("   - FaturamentoMapper carregado")
        print("   - Mapeamento hardcoded funcionando")
        print("   - Campos de múltiplas queries identificados")
        print("   - FaturamentoService integrado")
        print("   - Mapeamento simples testado")
        print("   - Campos calculados funcionando")
        
        print("\n🎯 CAMPOS MAPEADOS:")
        print("📄 Dados da NF: numero_nf, data_fatura, origem, status_nf")
        print("👥 Dados do Cliente: cnpj_cliente, nome_cliente, municipio, estado")
        print("🏢 Dados Comerciais: vendedor, incoterm")
        print("📦 Dados do Produto: cod_produto, nome_produto, peso_unitario")
        print("📊 Quantidades/Valores: qtd_faturado, valor_faturado, preco_faturado")
        print("🧮 Calculados: peso_total, preco_unitario")
        
        print("\n🎯 PRÓXIMO PASSO:")
        print("Testar com conexão real ao Odoo para verificar se as")
        print("múltiplas queries resolvem os campos de faturamento")
        
        return True
        
    except Exception as e:
        print(f"\n❌ ERRO NO TESTE: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    resultado = testar_faturamento_mapper()
    if resultado:
        print("\n🎉 FATURAMENTO MAPPER FUNCIONANDO!")
    else:
        print("\n💥 PROBLEMAS NO FATURAMENTO MAPPER ENCONTRADOS") 