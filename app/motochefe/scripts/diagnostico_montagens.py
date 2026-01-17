"""
Script de diagnóstico para investigar problema com montagens
Verifica estado de PedidoVendaMotoItem e TituloAPagar
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db # noqa: E402
from app.motochefe.models import PedidoVendaMotoItem # noqa: E402
from app.motochefe.models.financeiro import TituloAPagar # noqa: E402

def diagnosticar_montagens():
    app = create_app()

    with app.app_context():
        print("=" * 80)
        print("DIAGNÓSTICO DE MONTAGENS")
        print("=" * 80)

        # 1. Verificar item ID 26 especificamente
        print("\n1. INVESTIGANDO ITEM ID 26:")
        print("-" * 80)
        item_26 = db.session.get(PedidoVendaMotoItem,26) if 26 else None
        if item_26:
            print(f"✅ Item encontrado:")
            print(f"   - ID: {item_26.id}")
            print(f"   - Pedido ID: {item_26.pedido_id}")
            print(f"   - Chassi: {item_26.numero_chassi}")
            print(f"   - Montagem Contratada: {item_26.montagem_contratada}")
            print(f"   - Montagem Paga: {item_26.montagem_paga}")
            print(f"   - Valor Montagem: R$ {item_26.valor_montagem}")
            print(f"   - Fornecedor Montagem: {item_26.fornecedor_montagem}")

            # Buscar TituloAPagar correspondente
            titulo_pagar = db.session.query(TituloAPagar).filter_by(
                pedido_id=item_26.pedido_id,
                numero_chassi=item_26.numero_chassi,
                tipo='MONTAGEM'
            ).first()

            if titulo_pagar:
                print(f"\n   📋 TituloAPagar correspondente:")
                print(f"      - ID: {titulo_pagar.id}")
                print(f"      - Status: {titulo_pagar.status}")
                print(f"      - Valor Original: R$ {titulo_pagar.valor_original}")
                print(f"      - Valor Pago: R$ {titulo_pagar.valor_pago}")
                print(f"      - Valor Saldo: R$ {titulo_pagar.valor_saldo}")
                print(f"      - Data Criação: {titulo_pagar.data_criacao}")
                print(f"      - Data Liberação: {titulo_pagar.data_liberacao}")
                print(f"      - Data Pagamento: {titulo_pagar.data_pagamento}")

                print(f"\n   🔍 DIAGNÓSTICO:")
                if item_26.montagem_paga and titulo_pagar.status in ['ABERTO', 'PARCIAL']:
                    print(f"      ⚠️  DESSINCRONIA DETECTADA!")
                    print(f"      - Item.montagem_paga = True")
                    print(f"      - TituloAPagar.status = {titulo_pagar.status}")
                    print(f"      - CAUSA: Tabelas desincronizadas")
                elif not item_26.montagem_paga and titulo_pagar.status == 'PAGO':
                    print(f"      ⚠️  DESSINCRONIA DETECTADA!")
                    print(f"      - Item.montagem_paga = False")
                    print(f"      - TituloAPagar.status = PAGO")
                    print(f"      - CAUSA: Tabelas desincronizadas")
                else:
                    print(f"      ✅ Sincronizado corretamente")
            else:
                print(f"\n   ❌ TituloAPagar NÃO encontrado para este item!")
                print(f"      - CAUSA: Título não foi criado ou foi deletado")
        else:
            print(f"❌ Item ID 26 NÃO encontrado")

        # 2. Verificar TODOS os itens com dessincronia
        print("\n\n2. BUSCANDO DESSINCRONIAS EM TODAS AS MONTAGENS:")
        print("-" * 80)

        # Buscar todos os itens com montagem contratada
        itens_com_montagem = db.session.query(PedidoVendaMotoItem).filter_by(
            montagem_contratada=True
        ).all()

        dessincronias = []

        for item in itens_com_montagem:
            titulo = db.session.query(TituloAPagar).filter_by(
                pedido_id=item.pedido_id,
                numero_chassi=item.numero_chassi,
                tipo='MONTAGEM'
            ).first()

            if not titulo:
                dessincronias.append({
                    'item_id': item.id,
                    'problema': 'SEM_TITULO',
                    'item_paga': item.montagem_paga,
                    'titulo_status': None
                })
            elif item.montagem_paga and titulo.status in ['ABERTO', 'PARCIAL']:
                dessincronias.append({
                    'item_id': item.id,
                    'problema': 'ITEM_PAGO_TITULO_ABERTO',
                    'item_paga': True,
                    'titulo_status': titulo.status,
                    'titulo_id': titulo.id
                })
            elif not item.montagem_paga and titulo.status == 'PAGO':
                dessincronias.append({
                    'item_id': item.id,
                    'problema': 'ITEM_NAO_PAGO_TITULO_PAGO',
                    'item_paga': False,
                    'titulo_status': 'PAGO',
                    'titulo_id': titulo.id
                })

        if dessincronias:
            print(f"⚠️  Encontradas {len(dessincronias)} dessincronia(s):\n")
            for d in dessincronias:
                print(f"   - Item ID {d['item_id']}:")
                print(f"     Problema: {d['problema']}")
                print(f"     Item.montagem_paga: {d['item_paga']}")
                print(f"     TituloAPagar.status: {d['titulo_status']}")
                if 'titulo_id' in d:
                    print(f"     TituloAPagar.id: {d['titulo_id']}")
                print()
        else:
            print("✅ Nenhuma dessincronia encontrada!")

        # 3. Listar TituloAPagar que aparecem em Contas a Pagar
        print("\n3. TÍTULOS A PAGAR EXIBIDOS EM CONTAS A PAGAR:")
        print("-" * 80)

        titulos_visiveis = db.session.query(TituloAPagar).filter(
            TituloAPagar.tipo == 'MONTAGEM',
            TituloAPagar.status.in_(['ABERTO', 'PARCIAL'])
        ).all()

        print(f"Total de títulos visíveis: {len(titulos_visiveis)}\n")

        for titulo in titulos_visiveis[:10]:  # Mostrar apenas 10 primeiros
            item = db.session.query(PedidoVendaMotoItem).filter_by(
                pedido_id=titulo.pedido_id,
                numero_chassi=titulo.numero_chassi
            ).first()

            status_item = "✅" if item and not item.montagem_paga else "⚠️"

            print(f"{status_item} Título ID {titulo.id}:")
            print(f"   - Status: {titulo.status}")
            print(f"   - Saldo: R$ {titulo.valor_saldo}")
            print(f"   - Item ID: {item.id if item else 'N/A'}")
            print(f"   - Item.montagem_paga: {item.montagem_paga if item else 'N/A'}")
            print()

        print("\n" + "=" * 80)
        print("FIM DO DIAGNÓSTICO")
        print("=" * 80)

if __name__ == '__main__':
    diagnosticar_montagens()
