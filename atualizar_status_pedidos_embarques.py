#!/usr/bin/env python3
"""
Script para atualizar status dos pedidos que estão em embarques ativos
- Busca todos os pedidos que estão em embarques com status 'ativo'
- Atualiza o status desses pedidos para 'COTADO'
- Usado uma única vez para corrigir dados históricos
"""

import sys
import os
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.pedidos.models import Pedido
from app.embarques.models import Embarque, EmbarqueItem

def atualizar_status_pedidos_embarques():
    """Atualiza status dos pedidos que estão em embarques ativos"""
    app = create_app()
    
    with app.app_context():
        print(f"🔧 ATUALIZAÇÃO DE STATUS - PEDIDOS EM EMBARQUES ATIVOS")
        print("=" * 60)
        print(f"Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print()
        
        try:
            # Busca todos os embarques ativos
            embarques_ativos = Embarque.query.filter_by(status='ativo').all()
            
            if not embarques_ativos:
                print("❌ Nenhum embarque ativo encontrado!")
                return False
            
            print(f"📦 Encontrados {len(embarques_ativos)} embarques ativos")
            print()
            
            pedidos_atualizados = 0
            pedidos_ja_corretos = 0
            pedidos_nao_encontrados = 0
            
            # Para cada embarque ativo
            for embarque in embarques_ativos:
                print(f"🚛 Processando Embarque #{embarque.numero} (ID: {embarque.id})")
                print(f"   Transportadora: {embarque.transportadora.razao_social if embarque.transportadora else 'N/A'}")
                print(f"   Tipo: {embarque.tipo_carga or 'N/A'}")
                print(f"   Itens: {len(embarque.itens)}")
                
                # Para cada item do embarque
                for item in embarque.itens:
                    if item.status != 'ativo':
                        continue
                    
                    # Busca o pedido correspondente pelo separacao_lote_id
                    pedido = Pedido.query.filter_by(
                        separacao_lote_id=item.separacao_lote_id
                    ).first()
                    
                    if not pedido:
                        print(f"   ⚠️  Pedido não encontrado para lote {item.separacao_lote_id} (Item: {item.pedido})")
                        pedidos_nao_encontrados += 1
                        continue
                    
                    # Verifica status atual
                    status_atual = pedido.status_calculado
                    
                    if status_atual == 'COTADO':
                        pedidos_ja_corretos += 1
                        continue
                    
                    # Atualiza para COTADO
                    # Para FOB, não precisa de cotacao_id
                    if embarque.tipo_carga == 'FOB':
                        # FOB não tem cotação, mas deve estar como COTADO
                        pedido.nf_cd = False  # Reseta flag NF no CD
                        # O status será calculado automaticamente como COTADO pelo trigger
                    else:
                        # Para outros tipos, define cotacao_id se existir
                        if embarque.cotacao_id:
                            pedido.cotacao_id = embarque.cotacao_id
                        
                        # Define transportadora
                        if embarque.transportadora:
                            pedido.transportadora = embarque.transportadora.razao_social
                        
                        # Reseta flag NF no CD
                        pedido.nf_cd = False
                    
                    print(f"   ✅ Pedido {pedido.num_pedido}: {status_atual} → COTADO")
                    pedidos_atualizados += 1
                
                print()
            
            # Commit das alterações
            if pedidos_atualizados > 0:
                db.session.commit()
                print(f"💾 Alterações salvas no banco de dados!")
            
            # Relatório final
            print("📊 RELATÓRIO FINAL:")
            print(f"   • Embarques processados: {len(embarques_ativos)}")
            print(f"   • Pedidos atualizados: {pedidos_atualizados}")
            print(f"   • Pedidos já corretos: {pedidos_ja_corretos}")
            print(f"   • Pedidos não encontrados: {pedidos_nao_encontrados}")
            print()
            
            if pedidos_atualizados > 0:
                print("✅ Atualização concluída com sucesso!")
            else:
                print("ℹ️  Nenhuma atualização necessária - todos os pedidos já estão corretos!")
            
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Erro durante a atualização: {str(e)}")
            return False

def main():
    """Função principal"""
    print("🚀 INICIANDO ATUALIZAÇÃO DE STATUS DOS PEDIDOS EM EMBARQUES")
    print()
    
    # Confirmação do usuário
    resposta = input("⚠️  Este script irá atualizar o status dos pedidos em embarques ativos.\n"
                    "   Deseja continuar? (s/N): ").strip().lower()
    
    if resposta not in ['s', 'sim', 'y', 'yes']:
        print("❌ Operação cancelada pelo usuário.")
        return
    
    print()
    
    # Executa a atualização
    sucesso = atualizar_status_pedidos_embarques()
    
    if sucesso:
        print("\n🎉 Script executado com sucesso!")
    else:
        print("\n💥 Script finalizado com erros!")

if __name__ == "__main__":
    main() 