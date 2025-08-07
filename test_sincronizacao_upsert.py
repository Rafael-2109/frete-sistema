#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de teste para verificar a correção do erro de chave duplicada
na sincronização da carteira Odoo usando estratégia UPSERT.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Importar configurações do sistema
from app import create_app, db
from app.odoo.services.carteira_service import CarteiraService
from app.carteira.models import CarteiraPrincipal

def testar_sincronizacao():
    """Testa a sincronização com a estratégia UPSERT"""
    app = create_app()
    
    with app.app_context():
        print("\n" + "="*60)
        print("TESTE DE SINCRONIZAÇÃO COM UPSERT")
        print("="*60)
        
        # Verificar registros atuais
        total_antes = CarteiraPrincipal.query.count()
        odoo_antes = CarteiraPrincipal.query.filter(
            db.or_(
                CarteiraPrincipal.num_pedido.like('VSC%'),
                CarteiraPrincipal.num_pedido.like('VCD%'),
                CarteiraPrincipal.num_pedido.like('VFB%')
            )
        ).count()
        nao_odoo_antes = total_antes - odoo_antes
        
        print(f"\n📊 Estado ANTES da sincronização:")
        print(f"   Total de registros: {total_antes}")
        print(f"   Registros Odoo: {odoo_antes}")
        print(f"   Registros não-Odoo: {nao_odoo_antes}")
        
        # Verificar se há o registro específico que causou erro
        registro_problema = CarteiraPrincipal.query.filter_by(
            num_pedido='VCD2521074',
            cod_produto='4360177'
        ).first()
        
        if registro_problema:
            print(f"\n⚠️ Registro problemático EXISTE: VCD2521074/4360177")
            print(f"   ID: {registro_problema.id}")
            print(f"   Nome: {registro_problema.nome_produto}")
        else:
            print(f"\n✅ Registro problemático NÃO existe: VCD2521074/4360177")
        
        # Executar sincronização
        print("\n🔄 Executando sincronização com estratégia UPSERT...")
        print("-" * 60)
        
        try:
            service = CarteiraService()
            resultado = service.sincronizar_carteira_odoo_com_gestao_quantidades()
            
            if resultado['sucesso']:
                print("\n✅ SINCRONIZAÇÃO CONCLUÍDA COM SUCESSO!")
                print("\n📈 Estatísticas:")
                stats = resultado.get('estatisticas', {})
                print(f"   Novos registros inseridos: {stats.get('registros_inseridos', 0)}")
                print(f"   Registros atualizados: {stats.get('registros_atualizados', 0)}")
                print(f"   Registros removidos: {stats.get('registros_removidos', 0)}")
                print(f"   Registros não-Odoo preservados: {stats.get('registros_nao_odoo_preservados', 0)}")
                print(f"   Taxa de sucesso: {stats.get('taxa_sucesso', 'N/A')}")
                print(f"   Erros de processamento: {stats.get('erros_processamento', 0)}")
                print(f"   Tempo de execução: {stats.get('tempo_execucao_segundos', 0):.2f}s")
                
                if resultado.get('erros'):
                    print(f"\n⚠️ Erros encontrados:")
                    for erro in resultado['erros'][:5]:  # Mostrar apenas os 5 primeiros
                        print(f"   - {erro}")
                    if len(resultado['erros']) > 5:
                        print(f"   ... e mais {len(resultado['erros']) - 5} erros")
            else:
                print("\n❌ ERRO NA SINCRONIZAÇÃO:")
                print(f"   {resultado.get('erro', 'Erro desconhecido')}")
                
        except Exception as e:
            print(f"\n❌ EXCEÇÃO DURANTE SINCRONIZAÇÃO:")
            print(f"   {str(e)}")
            import traceback
            traceback.print_exc()
        
        # Verificar estado final
        print("\n" + "-" * 60)
        total_depois = CarteiraPrincipal.query.count()
        odoo_depois = CarteiraPrincipal.query.filter(
            db.or_(
                CarteiraPrincipal.num_pedido.like('VSC%'),
                CarteiraPrincipal.num_pedido.like('VCD%'),
                CarteiraPrincipal.num_pedido.like('VFB%')
            )
        ).count()
        nao_odoo_depois = total_depois - odoo_depois
        
        print(f"\n📊 Estado DEPOIS da sincronização:")
        print(f"   Total de registros: {total_depois}")
        print(f"   Registros Odoo: {odoo_depois}")
        print(f"   Registros não-Odoo: {nao_odoo_depois}")
        
        # Verificar se o registro problemático foi tratado corretamente
        registro_depois = CarteiraPrincipal.query.filter_by(
            num_pedido='VCD2521074',
            cod_produto='4360177'
        ).first()
        
        if registro_depois:
            print(f"\n✅ Registro VCD2521074/4360177 presente após sincronização")
            print(f"   ID: {registro_depois.id}")
            print(f"   Última atualização: {registro_depois.updated_at}")
        else:
            print(f"\n⚠️ Registro VCD2521074/4360177 NÃO encontrado após sincronização")
        
        print("\n" + "="*60)
        print("TESTE CONCLUÍDO")
        print("="*60 + "\n")

if __name__ == "__main__":
    testar_sincronizacao()