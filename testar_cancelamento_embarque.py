#!/usr/bin/env python3
"""
Script para testar o cancelamento de embarque e verificar se as NFs são removidas dos pedidos
"""

import sys
import os
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.embarques.models import Embarque, EmbarqueItem
from app.pedidos.models import Pedido
from app.embarques.routes import sincronizar_nf_embarque_pedido_completa

def testar_cancelamento_embarque(embarque_numero):
    """Testa o cancelamento de um embarque específico"""
    app = create_app()
    
    with app.app_context():
        print(f"🧪 TESTE DE CANCELAMENTO - EMBARQUE #{embarque_numero}")
        print("=" * 60)
        print(f"Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print()
        
        # Busca o embarque
        embarque = Embarque.query.filter_by(numero=embarque_numero).first()
        
        if not embarque:
            print(f"❌ Embarque #{embarque_numero} não encontrado!")
            return False
        
        print(f"📋 EMBARQUE ENCONTRADO:")
        print(f"   • Número: {embarque.numero}")
        print(f"   • Status: {embarque.status}")
        print(f"   • Transportadora: {embarque.transportadora.razao_social if embarque.transportadora else 'N/A'}")
        print(f"   • Total de itens: {len(embarque.itens)}")
        print()
        
        # Mostra estado ANTES do cancelamento
        print(f"🔍 ESTADO DOS PEDIDOS ANTES DO CANCELAMENTO:")
        pedidos_antes = {}
        
        for i, item in enumerate(embarque.itens):
            print(f"   📦 Item {i+1}: Pedido {item.pedido}")
            print(f"      • Lote: {item.separacao_lote_id}")
            print(f"      • NF no item: '{item.nota_fiscal or 'SEM NF'}'")
            print(f"      • Status do item: {item.status}")
            
            # Busca o pedido correspondente
            pedido = None
            if item.separacao_lote_id:
                pedido = Pedido.query.filter_by(separacao_lote_id=item.separacao_lote_id).first()
            elif item.pedido:
                pedido = Pedido.query.filter_by(num_pedido=item.pedido).first()
            
            if pedido:
                print(f"      • NF no pedido: '{pedido.nf or 'SEM NF'}'")
                print(f"      • Status do pedido: '{pedido.status_calculado}'")
                print(f"      • Cotação ID: {pedido.cotacao_id or 'N/A'}")
                
                pedidos_antes[item.pedido] = {
                    'nf': pedido.nf,
                    'status': pedido.status_calculado,
                    'cotacao_id': pedido.cotacao_id
                }
            else:
                print(f"      • ❌ PEDIDO NÃO ENCONTRADO!")
            print()
        
        # Simula o cancelamento
        print(f"🔧 SIMULANDO CANCELAMENTO...")
        print(f"   1. Removendo NFs dos itens...")
        
        nfs_removidas = 0
        for item in embarque.itens:
            if item.nota_fiscal and item.nota_fiscal.strip():
                print(f"      - Removendo NF '{item.nota_fiscal}' do item {item.pedido}")
                item.nota_fiscal = None
                nfs_removidas += 1
        
        print(f"   2. Cancelando todos os itens...")
        for item in embarque.itens:
            item.status = 'cancelado'
        
        print(f"   3. Executando sincronização...")
        sucesso, resultado = sincronizar_nf_embarque_pedido_completa(embarque.id)
        
        print(f"   ✅ Sincronização: {sucesso} - {resultado}")
        print()
        
        # Mostra estado DEPOIS do cancelamento
        print(f"🔍 ESTADO DOS PEDIDOS DEPOIS DO CANCELAMENTO:")
        
        for i, item in enumerate(embarque.itens):
            print(f"   📦 Item {i+1}: Pedido {item.pedido}")
            
            # Recarrega o pedido do banco
            pedido = None
            if item.separacao_lote_id:
                pedido = Pedido.query.filter_by(separacao_lote_id=item.separacao_lote_id).first()
            elif item.pedido:
                pedido = Pedido.query.filter_by(num_pedido=item.pedido).first()
            
            if pedido:
                estado_antes = pedidos_antes.get(item.pedido, {})
                
                print(f"      • NF: '{estado_antes.get('nf', 'N/A')}' → '{pedido.nf or 'SEM NF'}'")
                print(f"      • Status: '{estado_antes.get('status', 'N/A')}' → '{pedido.status_calculado}'")
                print(f"      • Cotação: '{estado_antes.get('cotacao_id', 'N/A')}' → '{pedido.cotacao_id or 'N/A'}'")
                
                # Verifica se mudou
                if estado_antes.get('nf') != pedido.nf:
                    print(f"      ✅ NF alterada corretamente")
                else:
                    print(f"      ❌ NF NÃO foi alterada!")
                
                if pedido.status_calculado == 'ABERTO':
                    print(f"      ✅ Status voltou para 'ABERTO'")
                else:
                    print(f"      ⚠️ Status não voltou para 'ABERTO': {pedido.status_calculado}")
            print()
        
        # Faz rollback para não alterar dados reais
        print(f"🔄 Fazendo rollback (não alterando dados reais)...")
        db.session.rollback()
        
        return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python testar_cancelamento_embarque.py <numero_embarque>")
        print("Exemplo: python testar_cancelamento_embarque.py 12345")
        sys.exit(1)
    
    numero_embarque = sys.argv[1]
    try:
        numero_embarque = int(numero_embarque)
        testar_cancelamento_embarque(numero_embarque)
    except ValueError:
        print("❌ Número do embarque deve ser um número inteiro!")
        sys.exit(1) 