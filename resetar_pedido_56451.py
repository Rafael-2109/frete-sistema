#!/usr/bin/env python3
"""
Script específico para resetar o pedido 56451 para status "Aberto"
- Script direto e simples
- Remove cotacao_id e transportadora
"""

import sys
import os
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.pedidos.models import Pedido

def main():
    app = create_app()
    
    with app.app_context():
        print("🔧 RESETAR PEDIDO 56451 PARA STATUS 'ABERTO'")
        print("=" * 50)
        print(f"Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print()
        
        # Busca o pedido 56451 (converte para string pois num_pedido é VARCHAR)
        pedido = Pedido.query.filter_by(num_pedido='56451').first()
        
        if not pedido:
            print("❌ Pedido 56451 não encontrado!")
            return
        
        print("📋 Dados do pedido:")
        print(f"   • Número: {pedido.num_pedido}")
        print(f"   • Cliente: {pedido.raz_social_red}")
        print(f"   • CNPJ: {pedido.cnpj_cpf}")
        print(f"   • Valor: R$ {pedido.valor_saldo_total:,.2f}")
        print(f"   • Peso: {pedido.peso_total} kg")
        
        # Status atual
        print(f"\n📊 Status atual:")
        print(f"   • Cotação ID: {pedido.cotacao_id}")
        print(f"   • Transportadora: {pedido.transportadora}")
        print(f"   • Lote Separação: {pedido.separacao_lote_id}")
        
        # Verifica se já está aberto
        if not pedido.cotacao_id and not pedido.transportadora:
            print("\n✅ Pedido 56451 já está com status 'Aberto'!")
            return
        
        # Confirma operação
        print(f"\n⚠️  AÇÃO: Resetar pedido 56451 para status 'Aberto'")
        resposta = input("Digite 'SIM' para confirmar: ")
        
        if resposta.upper() != 'SIM':
            print("❌ Operação cancelada.")
            return
        
        # Salva valores antigos
        cotacao_antiga = pedido.cotacao_id
        transportadora_antiga = pedido.transportadora
        
        # Executa reset
        print("\n🔄 Executando reset...")
        pedido.cotacao_id = None
        pedido.transportadora = None
        
        print(f"   ✅ Removido cotacao_id: {cotacao_antiga}")
        print(f"   ✅ Removido transportadora: {transportadora_antiga}")
        
        # Salva no banco
        try:
            db.session.commit()
            print(f"\n✅ SUCESSO! Pedido 56451 resetado para status 'Aberto'")
            
            # Log simples
            log_msg = f"{datetime.now().strftime('%d/%m/%Y %H:%M:%S')} - Pedido 56451 resetado para ABERTO (cotacao_id: {cotacao_antiga} → None, transportadora: {transportadora_antiga} → None)\n"
            
            with open('log_reset_pedidos.txt', 'a', encoding='utf-8') as f:
                f.write(log_msg)
            
            print("📝 Log salvo em 'log_reset_pedidos.txt'")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ ERRO ao salvar: {str(e)}")
            print("🔄 Alterações revertidas.")

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        print(f"❌ Erro: {str(e)}")
        import traceback
        traceback.print_exc() 