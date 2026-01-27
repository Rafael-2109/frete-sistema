"""
Script de Correcao: Preencher odoo_purchase_order_id para dados existentes
==========================================================================

Este script busca o ID do header (purchase.order) a partir do ID da linha
(purchase.order.line) que ja esta armazenado no campo odoo_id.

FLUXO:
1. Buscar todos os PedidoCompras com odoo_id preenchido mas sem odoo_purchase_order_id
2. Agrupar por odoo_id (linha)
3. Buscar order_id da linha no Odoo (em batch de 500)
4. Atualizar o campo odoo_purchase_order_id localmente

USO:
    source .venv/bin/activate
    python scripts/fix_odoo_purchase_order_id_dados.py

    # Modo dry-run (simula sem salvar)
    python scripts/fix_odoo_purchase_order_id_dados.py --dry-run

    # Processar apenas N registros
    python scripts/fix_odoo_purchase_order_id_dados.py --limit 100

Autor: Sistema de Fretes
Data: 2026-01-26
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.manufatura.models import PedidoCompras
from app.odoo.utils.connection import get_odoo_connection


def processar(dry_run: bool = False, limit: int = None):
    """
    Preenche o campo odoo_purchase_order_id para registros existentes.

    Args:
        dry_run: Se True, apenas simula sem salvar
        limit: Limite de registros a processar (None = todos)
    """
    app = create_app()
    with app.app_context():
        try:
            print("=" * 70)
            print("CORRECAO: Preencher odoo_purchase_order_id")
            print(f"Modo: {'DRY-RUN (simulacao)' if dry_run else 'PRODUCAO (salvando)'}")
            if limit:
                print(f"Limite: {limit} registros")
            print("=" * 70)

            # Buscar registros que precisam de correcao
            query = PedidoCompras.query.filter(
                PedidoCompras.odoo_id.isnot(None),
                db.or_(
                    PedidoCompras.odoo_purchase_order_id.is_(None),
                    PedidoCompras.odoo_purchase_order_id == ''
                )
            )

            if limit:
                query = query.limit(limit)

            pedidos = query.all()

            if not pedidos:
                print("Nenhum registro precisa de correcao. Todos ja tem odoo_purchase_order_id.")
                return

            print(f"Encontrados {len(pedidos)} registros para corrigir")

            # Coletar IDs unicos das linhas (odoo_id)
            line_ids = list(set([
                int(p.odoo_id) for p in pedidos
                if p.odoo_id and p.odoo_id.isdigit()
            ]))

            if not line_ids:
                print("Nenhum odoo_id valido encontrado")
                return

            print(f"IDs de linhas unicos: {len(line_ids)}")

            # Conectar ao Odoo
            print("\nConectando ao Odoo...")
            odoo = get_odoo_connection()
            if not odoo.authenticate():
                raise Exception("Falha na autenticacao com Odoo")
            print("Autenticado com sucesso")

            # Buscar order_id das linhas em batches
            BATCH_SIZE = 500
            line_to_order = {}  # {line_id: order_id}

            print(f"\nBuscando order_id de {len(line_ids)} linhas em batches de {BATCH_SIZE}...")

            for i in range(0, len(line_ids), BATCH_SIZE):
                batch = line_ids[i:i+BATCH_SIZE]
                print(f"  Batch {i//BATCH_SIZE + 1}: {len(batch)} linhas...")

                try:
                    linhas = odoo.read(
                        'purchase.order.line',
                        batch,
                        ['id', 'order_id']
                    )

                    for linha in linhas:
                        if linha.get('order_id'):
                            # order_id vem como [id, name]
                            order_id = linha['order_id'][0] if isinstance(linha['order_id'], list) else linha['order_id']
                            line_to_order[linha['id']] = order_id

                    print(f"    Encontrados {len(linhas)} com order_id")

                except Exception as e:
                    print(f"    ERRO no batch: {e}")
                    continue

            print(f"\nMapeamento line->order: {len(line_to_order)} relacoes")

            # Atualizar registros locais
            atualizados = 0
            nao_encontrados = 0
            erros = 0

            print("\nAtualizando registros locais...")

            for pedido in pedidos:
                try:
                    line_id = int(pedido.odoo_id) if pedido.odoo_id and pedido.odoo_id.isdigit() else None

                    if not line_id:
                        nao_encontrados += 1
                        continue

                    order_id = line_to_order.get(line_id)

                    if not order_id:
                        nao_encontrados += 1
                        continue

                    if not dry_run:
                        pedido.odoo_purchase_order_id = str(order_id)
                        atualizados += 1
                    else:
                        print(f"  [DRY-RUN] {pedido.num_pedido} | line_id={line_id} -> order_id={order_id}")
                        atualizados += 1

                except Exception as e:
                    print(f"  ERRO ao processar {pedido.id}: {e}")
                    erros += 1

            if not dry_run:
                db.session.commit()
                print(f"\nCommit realizado!")

            print("-" * 70)
            print("RESULTADO:")
            print(f"  Atualizados: {atualizados}")
            print(f"  Nao encontrados no Odoo: {nao_encontrados}")
            print(f"  Erros: {erros}")
            print("=" * 70)

            if dry_run:
                print("\n[DRY-RUN] Nenhuma alteracao foi salva. Execute sem --dry-run para aplicar.")

        except Exception as e:
            print(f"ERRO: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            raise


def main():
    parser = argparse.ArgumentParser(
        description='Preenche odoo_purchase_order_id para registros existentes'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simula sem salvar'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=None,
        help='Limite de registros a processar'
    )

    args = parser.parse_args()
    processar(dry_run=args.dry_run, limit=args.limit)


if __name__ == "__main__":
    main()
