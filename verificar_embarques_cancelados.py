#!/usr/bin/env python3
"""
Script de verificação de embarques cancelados
- Lista embarques cancelados e seus itens
- Mostra quais NFs seriam removidas
- Mostra quais pedidos seriam resetados
- NÃO faz alterações no banco (apenas consulta)
"""

import sys
import os
from datetime import datetime

# Adiciona o diretório raiz ao path para importar os módulos da aplicação
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.embarques.models import Embarque, EmbarqueItem
from app.pedidos.models import Pedido

def main():
    """Função principal do script"""
    app = create_app()
    
    with app.app_context():
        print("🔍 VERIFICAÇÃO DE EMBARQUES CANCELADOS")
        print("=" * 60)
        print(f"Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print("ℹ️  Este script apenas CONSULTA dados, não faz alterações.")
        print()
        
        # Busca embarques cancelados
        embarques_cancelados = Embarque.query.filter_by(status='CANCELADO').all()
        
        if not embarques_cancelados:
            print("✅ Nenhum embarque cancelado encontrado.")
            return
        
        print(f"📋 Encontrados {len(embarques_cancelados)} embarques cancelados:")
        print()
        
        total_itens = 0
        total_nfs_para_remover = 0
        total_pedidos_para_resetar = 0
        
        for i, embarque in enumerate(embarques_cancelados, 1):
            print(f"🚛 {i}. Embarque #{embarque.id}")
            print(f"   📅 Criado em: {embarque.criado_em.strftime('%d/%m/%Y %H:%M') if embarque.criado_em else 'N/A'}")
            print(f"   🚚 Transportadora: {embarque.transportadora.razao_social if embarque.transportadora else 'N/A'}")
            print(f"   📍 Tipo: {embarque.tipo_carga or 'N/A'}")
            print(f"   🏷️  Status: {embarque.status}")
            
            # Busca itens do embarque
            itens = EmbarqueItem.query.filter_by(embarque_id=embarque.id).all()
            
            if not itens:
                print("   ⚠️  Nenhum item encontrado")
                print()
                continue
            
            print(f"   📦 {len(itens)} itens:")
            
            # Analisa itens
            lotes_separacao = set()
            nfs_para_remover = []
            
            for item in itens:
                status_nf = "✅ COM NF" if item.nota_fiscal else "❌ SEM NF"
                print(f"      • Item {item.id}: {item.cliente} - {status_nf}")
                
                if item.nota_fiscal:
                    print(f"        📄 NF: {item.nota_fiscal} (SERÁ REMOVIDA)")
                    nfs_para_remover.append(item.nota_fiscal)
                    total_nfs_para_remover += 1
                
                if item.separacao_lote_id:
                    lotes_separacao.add(item.separacao_lote_id)
                    print(f"        📋 Lote: {item.separacao_lote_id}")
                
                total_itens += 1
            
            # Verifica pedidos que seriam resetados
            if lotes_separacao:
                print(f"   🔄 Pedidos que seriam resetados para 'Aberto':")
                
                for lote_id in lotes_separacao:
                    pedidos_lote = Pedido.query.filter_by(separacao_lote_id=lote_id).all()
                    
                    for pedido in pedidos_lote:
                        status_atual = "COM COTAÇÃO" if pedido.cotacao_id else "SEM COTAÇÃO"
                        transp_atual = f" - {pedido.transportadora}" if pedido.transportadora else ""
                        
                        print(f"      📋 Pedido {pedido.num_pedido} ({status_atual}{transp_atual})")
                        total_pedidos_para_resetar += 1
            
            print(f"   📊 Resumo do embarque:")
            print(f"      • NFs para remover: {len(nfs_para_remover)}")
            print(f"      • Lotes de separação: {len(lotes_separacao)}")
            print()
        
        # Resumo geral
        print("📊 RESUMO GERAL:")
        print(f"   • Total de embarques cancelados: {len(embarques_cancelados)}")
        print(f"   • Total de itens: {total_itens}")
        print(f"   • Total de NFs que seriam removidas: {total_nfs_para_remover}")
        print(f"   • Total de pedidos que seriam resetados: {total_pedidos_para_resetar}")
        
        if total_nfs_para_remover > 0 or total_pedidos_para_resetar > 0:
            print()
            print("⚠️  AÇÕES QUE SERIAM EXECUTADAS pelo script de limpeza:")
            if total_nfs_para_remover > 0:
                print(f"   🗑️  Remover {total_nfs_para_remover} NFs dos itens")
            if total_pedidos_para_resetar > 0:
                print(f"   🔄 Resetar {total_pedidos_para_resetar} pedidos para status 'Aberto'")
            print()
            print("💡 Para executar a limpeza, use o script: python limpar_embarques_cancelados.py")
        else:
            print()
            print("✅ Nenhuma ação seria necessária.")
        
        print(f"\n🏁 Verificação finalizada em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Script interrompido pelo usuário (Ctrl+C)")
    except Exception as e:
        print(f"\n❌ Erro inesperado: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n👋 Encerrando script...") 