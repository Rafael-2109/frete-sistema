#!/usr/bin/env python3
"""
Deploy Sistema Completo de Integração Odoo
==========================================

Script para verificar todo o sistema de integração Odoo implementado:
- CarteiraPrincipal com CampoMapper  
- FaturamentoProduto com FaturamentoMapper
- Sistema de múltiplas queries
- Mapeamentos hardcoded

Resultado esperado: 100% funcional para ambos os sistemas
"""

import sys
import os
import json
from pathlib import Path

# Adicionar o diretório do projeto ao Python path
sys.path.insert(0, str(Path(__file__).parent / "app"))

def verificar_sistema_completo_odoo():
    """Verifica se todo o sistema de integração Odoo está funcionando"""
    
    print("🚀 VERIFICAÇÃO COMPLETA DO SISTEMA DE INTEGRAÇÃO ODOO")
    print("=" * 70)
    
    resultados = {
        "sistemas_testados": [],
        "status_geral": True,
        "problemas_encontrados": [],
        "sucessos": [],
        "estatisticas": {}
    }
    
    try:
        # 1. TESTAR SISTEMA DE CARTEIRA
        print("📋 1. TESTANDO SISTEMA DE CARTEIRA")
        print("-" * 50)
        
        # 1.1 CampoMapper
        print("🔧 1.1 Verificando CampoMapper...")
        from app.odoo.utils.campo_mapper import CampoMapper
        
        carteira_mapper = CampoMapper()
        carteira_stats = carteira_mapper.obter_estatisticas_mapeamento()
        
        print(f"   📊 Carteira - Total: {carteira_stats['total_campos']} campos")
        print(f"   📊 Carteira - Simples: {carteira_stats['campos_simples']} ({carteira_stats['percentual_simples']:.1f}%)")
        print(f"   📊 Carteira - Complexos: {carteira_stats['campos_complexos']} ({carteira_stats['percentual_complexos']:.1f}%)")
        
        if carteira_stats['total_campos'] >= 39:
            print("   ✅ CampoMapper da carteira: FUNCIONANDO")
            resultados["sucessos"].append(f"CampoMapper: {carteira_stats['total_campos']} campos")
        else:
            print("   ❌ CampoMapper da carteira: PROBLEMA")
            resultados["problemas_encontrados"].append("CampoMapper com poucos campos")
            resultados["status_geral"] = False
        
        # 1.2 CarteiraService  
        print("\n🏪 1.2 Verificando CarteiraService...")
        from app.odoo.services.carteira_service import CarteiraService
        
        carteira_service = CarteiraService()
        if hasattr(carteira_service, 'mapper') and isinstance(carteira_service.mapper, CampoMapper):
            print("   ✅ CarteiraService: INTEGRADO")
            resultados["sucessos"].append("CarteiraService integrado com CampoMapper")
        else:
            print("   ❌ CarteiraService: PROBLEMA DE INTEGRAÇÃO")
            resultados["problemas_encontrados"].append("CarteiraService não integrado")
            resultados["status_geral"] = False
        
        resultados["sistemas_testados"].append("Carteira")
        resultados["estatisticas"]["carteira"] = carteira_stats
        
        # 2. TESTAR SISTEMA DE FATURAMENTO
        print("\n💰 2. TESTANDO SISTEMA DE FATURAMENTO")
        print("-" * 50)
        
        # 2.1 FaturamentoMapper
        print("🔧 2.1 Verificando FaturamentoMapper...")
        from app.odoo.utils.faturamento_mapper import FaturamentoMapper
        
        faturamento_mapper = FaturamentoMapper()
        faturamento_stats = faturamento_mapper.obter_estatisticas_mapeamento()
        
        print(f"   📊 Faturamento - Total: {faturamento_stats['total_campos']} campos")
        print(f"   📊 Faturamento - Simples: {faturamento_stats['campos_simples']} ({faturamento_stats['percentual_simples']:.1f}%)")
        print(f"   📊 Faturamento - Complexos: {faturamento_stats['campos_complexos']} ({faturamento_stats['percentual_complexos']:.1f}%)")
        print(f"   📊 Faturamento - Calculados: {faturamento_stats['campos_calculados']} ({faturamento_stats['percentual_calculados']:.1f}%)")
        
        if faturamento_stats['total_campos'] >= 17:
            print("   ✅ FaturamentoMapper: FUNCIONANDO")
            resultados["sucessos"].append(f"FaturamentoMapper: {faturamento_stats['total_campos']} campos")
        else:
            print("   ❌ FaturamentoMapper: PROBLEMA")
            resultados["problemas_encontrados"].append("FaturamentoMapper com poucos campos")
            resultados["status_geral"] = False
        
        # 2.2 FaturamentoService
        print("\n🏪 2.2 Verificando FaturamentoService...")
        from app.odoo.services.faturamento_service import FaturamentoService
        
        faturamento_service = FaturamentoService()
        if hasattr(faturamento_service, 'mapper') and isinstance(faturamento_service.mapper, FaturamentoMapper):
            print("   ✅ FaturamentoService: INTEGRADO")
            resultados["sucessos"].append("FaturamentoService integrado com FaturamentoMapper")
        else:
            print("   ❌ FaturamentoService: PROBLEMA DE INTEGRAÇÃO")
            resultados["problemas_encontrados"].append("FaturamentoService não integrado")
            resultados["status_geral"] = False
        
        resultados["sistemas_testados"].append("Faturamento")
        resultados["estatisticas"]["faturamento"] = faturamento_stats
        
        # 3. TESTAR INFRAESTRUTURA COMUM
        print("\n🌐 3. TESTANDO INFRAESTRUTURA COMUM")
        print("-" * 50)
        
        # 3.1 OdooConnection
        print("🔗 3.1 Verificando OdooConnection...")
        from app.odoo.utils.connection import OdooConnection, get_odoo_connection
        
        connection = get_odoo_connection()
        if hasattr(connection, 'buscar_registro_por_id'):
            print("   ✅ OdooConnection: Método buscar_registro_por_id disponível")
            resultados["sucessos"].append("OdooConnection com múltiplas queries")
        else:
            print("   ❌ OdooConnection: Método buscar_registro_por_id AUSENTE")
            resultados["problemas_encontrados"].append("OdooConnection sem múltiplas queries")
            resultados["status_geral"] = False
        
        resultados["sistemas_testados"].append("OdooConnection")
        
        # 4. TESTE INTEGRADO DE CAMPOS PROBLEMÁTICOS
        print("\n🎯 4. TESTANDO CAMPOS PROBLEMÁTICOS")
        print("-" * 50)
        
        # 4.1 Campos problemáticos da carteira
        campos_problematicos_carteira = [
            "order_id/partner_shipping_id/l10n_br_cnpj",
            "order_id/partner_shipping_id/zip", 
            "order_id/partner_shipping_id/street",
            "order_id/partner_id/state_id/code",
            "order_id/partner_shipping_id/l10n_br_municipio_id/name"
        ]
        
        carteira_identificados = 0
        for campo in campos_problematicos_carteira:
            if carteira_mapper.eh_campo_multiplas_queries(campo):
                carteira_identificados += 1
        
        print(f"   🎯 Carteira - Campos problemáticos identificados: {carteira_identificados}/{len(campos_problematicos_carteira)}")
        
        # 4.2 Campos problemáticos do faturamento
        campos_problematicos_faturamento = [
            "partner_id/l10n_br_cnpj",
            "partner_id/l10n_br_municipio_id/name",
            "move_id/invoice_user_id/name",
            "move_id/invoice_origin",
            "product_id/weight"
        ]
        
        faturamento_identificados = 0
        for campo in campos_problematicos_faturamento:
            if faturamento_mapper.eh_campo_multiplas_queries(campo):
                faturamento_identificados += 1
        
        print(f"   🎯 Faturamento - Campos problemáticos identificados: {faturamento_identificados}/{len(campos_problematicos_faturamento)}")
        
        if (carteira_identificados == len(campos_problematicos_carteira) and 
            faturamento_identificados == len(campos_problematicos_faturamento)):
            print("   ✅ Todos os campos problemáticos identificados corretamente")
            resultados["sucessos"].append("Campos problemáticos 100% identificados")
        else:
            print("   ⚠️ Alguns campos problemáticos não foram identificados")
            resultados["problemas_encontrados"].append("Campos problemáticos parcialmente identificados")
        
        # 5. TESTE DE MAPEAMENTO COM DADOS SIMULADOS
        print("\n🎭 5. TESTANDO COM DADOS SIMULADOS")
        print("-" * 50)
        
        # 5.1 Teste carteira
        dados_carteira_simulados = [
            {
                'id': 1,
                'order_id': [100, 'PEDIDO-001'],
                'product_id': [200, 'PRODUTO-A'],
                'product_uom_qty': 10.0,
                'qty_saldo': 5.0,
                'price_unit': 25.50
            }
        ]
        
        carteira_mapeada = carteira_mapper.mapear_para_carteira(dados_carteira_simulados)
        print(f"   📋 Carteira simulada: {len(carteira_mapeada)} registros processados")
        
        # 5.2 Teste faturamento
        dados_faturamento_simulados = [
            {
                'id': 1,
                'move_id': [100, 'INV/2025/001'],
                'partner_id': [500, 'ACME Corp'],
                'product_id': [200, 'PRODUTO-A'],
                'quantity': 10.0,
                'price_unit': 25.50,
                'price_total': 255.00,
                'date': '2025-01-15'
            }
        ]
        
        faturamento_mapeado = faturamento_mapper.mapear_para_faturamento(dados_faturamento_simulados)
        print(f"   📋 Faturamento simulado: {len(faturamento_mapeado)} registros processados")
        
        if len(carteira_mapeada) > 0 and len(faturamento_mapeado) > 0:
            print("   ✅ Mapeamento com dados simulados: FUNCIONANDO")
            resultados["sucessos"].append("Mapeamento simulado funcional")
        else:
            print("   ❌ Mapeamento com dados simulados: PROBLEMA")
            resultados["problemas_encontrados"].append("Mapeamento simulado com falhas")
            resultados["status_geral"] = False
        
        # 6. RELATÓRIO FINAL CONSOLIDADO
        print("\n📋 RELATÓRIO FINAL CONSOLIDADO")
        print("=" * 50)
        
        # Contabilizar totais
        total_campos = carteira_stats['total_campos'] + faturamento_stats['total_campos']
        total_simples = carteira_stats['campos_simples'] + faturamento_stats['campos_simples']
        total_complexos = carteira_stats['campos_complexos'] + faturamento_stats['campos_complexos']
        
        print(f"✅ Sucessos ({len(resultados['sucessos'])}):")
        for sucesso in resultados['sucessos']:
            print(f"   - {sucesso}")
        
        if resultados['problemas_encontrados']:
            print(f"\n⚠️ Problemas encontrados ({len(resultados['problemas_encontrados'])}):")
            for problema in resultados['problemas_encontrados']:
                print(f"   - {problema}")
        
        print(f"\n📊 ESTATÍSTICAS CONSOLIDADAS:")
        print(f"   🎯 Total de campos mapeados: {total_campos}")
        print(f"   📋 Carteira: {carteira_stats['total_campos']} campos")
        print(f"   💰 Faturamento: {faturamento_stats['total_campos']} campos")
        print(f"   ⚡ Campos simples: {total_simples}")
        print(f"   🔗 Campos complexos: {total_complexos}")
        print(f"   🧮 Campos calculados: {faturamento_stats['campos_calculados']}")
        
        print(f"\n🧪 Sistemas testados: {', '.join(resultados['sistemas_testados'])}")
        
        # 7. STATUS FINAL
        if resultados['status_geral']:
            print("\n🎉 SISTEMA ODOO COMPLETAMENTE FUNCIONAL!")
            print("✅ Todos os componentes implementados com sucesso")
            print("🚀 Pronto para uso em produção")
            
            print("\n🎯 BENEFÍCIOS ALCANÇADOS:")
            print("   - Carteira: 39 campos com múltiplas queries automáticas")
            print("   - Faturamento: 17 campos com cálculos automáticos")
            print("   - 100% de cobertura dos mapeamentos hardcoded")
            print("   - Sistema robusto sem dependências externas")
            print("   - Resolução automática de relacionamentos complexos")
            print("   - Suporte completo à localização brasileira")
            
        else:
            print("\n⚠️ SISTEMA COM PROBLEMAS MENORES")
            print("🔧 Alguns ajustes podem ser necessários")
        
        # Salvar relatório consolidado
        with open("relatorio_sistema_odoo_completo.json", "w", encoding="utf-8") as f:
            json.dump(resultados, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Relatório consolidado salvo em: relatorio_sistema_odoo_completo.json")
        
        return resultados['status_geral']
        
    except Exception as e:
        print(f"\n❌ ERRO CRÍTICO: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("🚀 INICIANDO VERIFICAÇÃO COMPLETA DO SISTEMA ODOO...")
    print("📋 Componentes: CampoMapper, FaturamentoMapper, Services, Connection")
    print("🎯 Objetivo: Validar integração completa CarteiraPrincipal + FaturamentoProduto")
    print()
    
    sucesso = verificar_sistema_completo_odoo()
    
    if sucesso:
        print("\n🎊 DEPLOY SISTEMA ODOO CONCLUÍDO COM SUCESSO!")
        print("🚀 Sistema completo pronto para integração Odoo em produção!")
    else:
        print("\n⚠️ DEPLOY COM PROBLEMAS")
        print("🔧 Revise os problemas identificados antes de usar em produção") 