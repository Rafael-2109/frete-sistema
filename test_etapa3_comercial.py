#!/usr/bin/env python3
"""
Script de teste para a 3ª etapa do módulo comercial
Testa a funcionalidade de documentos (NFs, Separações e Saldo)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.comercial.services.documento_service import DocumentoService
from datetime import datetime, date
from decimal import Decimal

def test_documento_service():
    """Testa o DocumentoService com dados de exemplo"""

    app = create_app()

    with app.app_context():
        print("\n" + "="*80)
        print("TESTE DA 3ª ETAPA - MÓDULO COMERCIAL")
        print("="*80)

        # Buscar um pedido de exemplo para testar
        from app.carteira.models import CarteiraPrincipal

        # Buscar um pedido de exemplo
        pedido_exemplo = db.session.query(CarteiraPrincipal.num_pedido, CarteiraPrincipal.cnpj_cpf)\
            .filter(CarteiraPrincipal.num_pedido.isnot(None))\
            .first()

        if not pedido_exemplo:
            print("❌ Nenhum pedido encontrado na CarteiraPrincipal para testar")
            return

        num_pedido = pedido_exemplo.num_pedido
        cnpj_cliente = pedido_exemplo.cnpj_cpf

        print(f"\n📋 Testando com pedido: {num_pedido}")
        print(f"👤 Cliente (CNPJ): {cnpj_cliente}")

        # Testar o serviço de documentos
        print("\n" + "-"*40)
        print("Testando DocumentoService.obter_documentos_pedido()")
        print("-"*40)

        try:
            resultado = DocumentoService.obter_documentos_pedido(
                num_pedido=num_pedido,
                cnpj_cliente=cnpj_cliente
            )

            print(f"\n✅ Documentos obtidos com sucesso!")
            print(f"   Cliente precisa agendamento: {resultado['cliente_precisa_agendamento']}")
            print(f"   Total de documentos: {len(resultado['documentos'])}")

            # Mostrar totais
            print(f"\n💰 Totais:")
            print(f"   Valor Total do Pedido: R$ {resultado['totais']['valor_total_pedido']:.2f}")
            print(f"   Valor Total Faturado: R$ {resultado['totais']['valor_total_faturado']:.2f}")
            print(f"   Valor Total Separações: R$ {resultado['totais']['valor_total_separacoes']:.2f}")
            print(f"   Saldo: R$ {resultado['totais']['saldo']:.2f}")

            # Mostrar documentos
            if resultado['documentos']:
                print(f"\n📄 Documentos encontrados:")
                for i, doc in enumerate(resultado['documentos'], 1):
                    print(f"\n   {i}. Tipo: {doc['tipo']}")

                    if doc['tipo'] == 'NF':
                        print(f"      Número NF: {doc.get('numero_nf', '-')}")
                        print(f"      Data Faturamento: {doc.get('data_faturamento', '-')}")
                        print(f"      Transportadora: {doc.get('transportadora', '-')}")
                        print(f"      Valor: R$ {doc.get('valor', 0):.2f}")

                    elif doc['tipo'] == 'Separação':
                        print(f"      Data Expedição: {doc.get('data_embarque', '-')}")
                        print(f"      Data Agendamento: {doc.get('data_agendamento', '-')}")
                        print(f"      Protocolo: {doc.get('protocolo_agendamento', '-')}")
                        print(f"      Status: {doc.get('status_agendamento', '-')}")
                        print(f"      Valor: R$ {doc.get('valor', 0):.2f}")

                    elif doc['tipo'] == 'Saldo':
                        print(f"      Valor: R$ {doc.get('valor', 0):.2f}")

        except Exception as e:
            print(f"❌ Erro ao obter documentos: {e}")
            import traceback
            traceback.print_exc()

        # Testar métodos privados individualmente
        print("\n" + "-"*40)
        print("Testando métodos auxiliares")
        print("-"*40)

        # Teste 1: Cliente precisa agendamento
        print(f"\n1. Verificando se cliente precisa agendamento:")
        try:
            precisa_agend = DocumentoService._cliente_precisa_agendamento(cnpj_cliente)
            print(f"   Cliente precisa agendamento: {precisa_agend}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")

        # Teste 2: Valor total do pedido
        print(f"\n2. Calculando valor total do pedido:")
        try:
            valor_total = DocumentoService._calcular_valor_total_pedido(num_pedido)
            print(f"   Valor total: R$ {float(valor_total):.2f}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")

        # Teste 3: Notas fiscais
        print(f"\n3. Buscando notas fiscais:")
        try:
            nfs = DocumentoService._obter_notas_fiscais_pedido(num_pedido)
            print(f"   Total de NFs: {len(nfs)}")
            for nf in nfs[:3]:  # Mostrar até 3
                print(f"   - NF {nf.get('numero_nf', '-')}: R$ {nf.get('valor', 0):.2f}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")

        # Teste 4: Separações
        print(f"\n4. Buscando separações:")
        try:
            seps = DocumentoService._obter_separacoes_pedido(num_pedido)
            print(f"   Total de Separações: {len(seps)}")
            for sep in seps[:3]:  # Mostrar até 3
                print(f"   - Lote {sep.get('separacao_lote_id', '-')}: R$ {sep.get('valor', 0):.2f}")
        except Exception as e:
            print(f"   ❌ Erro: {e}")

        print("\n" + "="*80)
        print("TESTE CONCLUÍDO")
        print("="*80)

if __name__ == '__main__':
    test_documento_service()