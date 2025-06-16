#!/usr/bin/env python3
"""
Script simples para verificar o estado atual de um pedido
"""

import sys
import os
from datetime import datetime

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.pedidos.models import Pedido
from app.embarques.models import EmbarqueItem, Embarque

def verificar_pedido(numero_pedido):
    """Verifica o estado atual de um pedido"""
    app = create_app()
    
    with app.app_context():
        print(f"🔍 VERIFICAÇÃO DO PEDIDO {numero_pedido}")
        print("=" * 50)
        print(f"Executado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        print()
        
        # Busca o pedido
        pedido = Pedido.query.filter_by(num_pedido=str(numero_pedido)).first()
        
        if not pedido:
            print(f"❌ Pedido {numero_pedido} não encontrado!")
            return False
        
        print(f"📋 DADOS DO PEDIDO:")
        print(f"   • Número: {pedido.num_pedido}")
        print(f"   • Cliente: {pedido.raz_social_red}")
        print(f"   • CNPJ: {pedido.cnpj_cpf}")
        print(f"   • Lote de separação: {pedido.separacao_lote_id}")
        print(f"   • NF: '{pedido.nf or 'SEM NF'}'")
        print(f"   • Status: '{pedido.status_calculado}'")
        print(f"   • Cotação ID: {pedido.cotacao_id or 'N/A'}")
        print(f"   • Transportadora: {pedido.transportadora or 'N/A'}")
        print(f"   • Data embarque: {pedido.data_embarque or 'N/A'}")
        print(f"   • NF no CD: {pedido.nf_cd}")
        print()
        
        # Busca embarques que contêm este pedido
        embarques = []
        if pedido.separacao_lote_id:
            embarques = db.session.query(EmbarqueItem, Embarque).join(Embarque).filter(
                EmbarqueItem.separacao_lote_id == pedido.separacao_lote_id
            ).all()
        
        if not embarques:
            # Fallback: busca por número do pedido
            embarques = db.session.query(EmbarqueItem, Embarque).join(Embarque).filter(
                EmbarqueItem.pedido == pedido.num_pedido
            ).all()
        
        print(f"🚚 EMBARQUES QUE CONTÊM ESTE PEDIDO:")
        if embarques:
            for item_embarque, embarque in embarques:
                print(f"   • Embarque #{embarque.numero}")
                print(f"     - Status do embarque: {embarque.status}")
                print(f"     - Status do item: {item_embarque.status}")
                print(f"     - NF no item: '{item_embarque.nota_fiscal or 'SEM NF'}'")
                print(f"     - Transportadora: {embarque.transportadora.razao_social if embarque.transportadora else 'N/A'}")
        else:
            print(f"   • Nenhum embarque encontrado")
        print()
        
        # Análise do status
        print(f"🔍 ANÁLISE DO STATUS:")
        if pedido.nf_cd:
            print(f"   ✅ Status 'NF no CD' está correto (nf_cd = True)")
        elif pedido.nf and pedido.nf.strip():
            print(f"   ✅ Status 'FATURADO' está correto (tem NF: {pedido.nf})")
        elif pedido.data_embarque:
            print(f"   ✅ Status 'EMBARCADO' está correto (data embarque: {pedido.data_embarque})")
        elif pedido.cotacao_id:
            print(f"   ✅ Status 'COTADO' está correto (cotação ID: {pedido.cotacao_id})")
        else:
            print(f"   ✅ Status 'ABERTO' está correto (sem cotação, sem NF, sem embarque)")
        
        return True

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Uso: python verificar_pedido_nf.py <numero_pedido>")
        print("Exemplo: python verificar_pedido_nf.py 12345")
        sys.exit(1)
    
    numero_pedido = sys.argv[1]
    verificar_pedido(numero_pedido) 