#!/usr/bin/env python3
"""
Script de uso único para limpeza de embarques cancelados
- Remove NFs dos itens de embarques cancelados
- Volta pedidos para status "Aberto"
- Executa apenas uma vez para correção de dados
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
        print("🔧 SCRIPT DE LIMPEZA DE EMBARQUES CANCELADOS")
        print("=" * 60)
        print(f"Iniciado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print()
        
        # Confirma execução
        resposta = input("⚠️  ATENÇÃO: Este script irá:\n"
                        "   - Remover NFs de todos os itens de embarques CANCELADOS\n"
                        "   - Voltar pedidos desses embarques para status 'Aberto'\n"
                        "   - Esta operação NÃO pode ser desfeita!\n\n"
                        "Deseja continuar? (digite 'SIM' para confirmar): ")
        
        if resposta.upper() != 'SIM':
            print("❌ Operação cancelada pelo usuário.")
            return
        
        print("\n🔍 Buscando embarques cancelados...")
        
        # Busca embarques cancelados
        embarques_cancelados = Embarque.query.filter_by(status='CANCELADO').all()
        
        if not embarques_cancelados:
            print("✅ Nenhum embarque cancelado encontrado.")
            return
        
        print(f"📋 Encontrados {len(embarques_cancelados)} embarques cancelados:")
        
        total_itens_processados = 0
        total_pedidos_atualizados = 0
        total_nfs_removidas = 0
        
        for embarque in embarques_cancelados:
            print(f"\n🚛 Processando Embarque #{embarque.id} - {embarque.transportadora.razao_social if embarque.transportadora else 'N/A'}")
            
            # Busca itens do embarque
            itens = EmbarqueItem.query.filter_by(embarque_id=embarque.id).all()
            
            if not itens:
                print("   ⚠️  Nenhum item encontrado neste embarque")
                continue
            
            print(f"   📦 {len(itens)} itens encontrados")
            
            # Coleta lotes de separação únicos para resetar pedidos
            lotes_separacao = set()
            itens_com_nf = 0
            
            for item in itens:
                # Remove NF se existir
                if item.nota_fiscal:
                    print(f"   🗑️  Removendo NF {item.nota_fiscal} do item {item.id}")
                    item.nota_fiscal = ''
                    total_nfs_removidas += 1
                    itens_com_nf += 1
                
                # Coleta lote de separação
                if item.separacao_lote_id:
                    lotes_separacao.add(item.separacao_lote_id)
                
                total_itens_processados += 1
            
            print(f"   ✅ {itens_com_nf} NFs removidas dos itens")
            
            # Reseta pedidos dos lotes de separação para "Aberto"
            if lotes_separacao:
                print(f"   🔄 Resetando pedidos de {len(lotes_separacao)} lotes de separação...")
                
                for lote_id in lotes_separacao:
                    # Busca pedidos do lote (lote_id pode ser string ou int)
                    pedidos_lote = Pedido.query.filter_by(separacao_lote_id=str(lote_id)).all()
                    
                    for pedido in pedidos_lote:
                        # Remove vinculação com cotação (volta ao estado inicial)
                        pedido.cotacao_id = None
                        pedido.transportadora = None
                        total_pedidos_atualizados += 1
                        print(f"     📋 Pedido {pedido.num_pedido} resetado para 'Aberto'")
            
            print(f"   ✅ Embarque #{embarque.id} processado com sucesso")
        
        # Confirma as alterações
        print(f"\n📊 RESUMO DA OPERAÇÃO:")
        print(f"   • Embarques cancelados processados: {len(embarques_cancelados)}")
        print(f"   • Itens processados: {total_itens_processados}")
        print(f"   • NFs removidas: {total_nfs_removidas}")
        print(f"   • Pedidos resetados para 'Aberto': {total_pedidos_atualizados}")
        
        confirma_commit = input(f"\n💾 Confirma a gravação das alterações no banco? (digite 'CONFIRMAR'): ")
        
        if confirma_commit.upper() == 'CONFIRMAR':
            try:
                db.session.commit()
                print("✅ Alterações salvas com sucesso no banco de dados!")
                
                # Log da operação
                log_msg = (f"LIMPEZA EMBARQUES CANCELADOS - {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n"
                          f"Embarques processados: {len(embarques_cancelados)}\n"
                          f"Itens processados: {total_itens_processados}\n"
                          f"NFs removidas: {total_nfs_removidas}\n"
                          f"Pedidos resetados: {total_pedidos_atualizados}\n")
                
                with open('log_limpeza_embarques.txt', 'a', encoding='utf-8') as f:
                    f.write(log_msg + "\n" + "="*50 + "\n")
                
                print("📝 Log da operação salvo em 'log_limpeza_embarques.txt'")
                
            except Exception as e:
                db.session.rollback()
                print(f"❌ Erro ao salvar alterações: {str(e)}")
                print("🔄 Todas as alterações foram revertidas.")
        else:
            db.session.rollback()
            print("❌ Operação cancelada. Nenhuma alteração foi salva.")
        
        print(f"\n🏁 Script finalizado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")

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