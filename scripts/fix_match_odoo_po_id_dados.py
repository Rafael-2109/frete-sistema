"""
Script de Correcao: Preencher odoo_po_id correto em MatchNfPoItem e MatchAlocacao
=================================================================================

Este script corrige os registros existentes onde odoo_po_id armazena o ID da
LINHA (purchase.order.line) em vez do ID do HEADER (purchase.order).

FLUXO:
1. Buscar todos os MatchNfPoItem/MatchAlocacao com odoo_po_id preenchido
2. Buscar o PedidoCompras correspondente pelo num_pedido
3. Usar o odoo_purchase_order_id (header) do PedidoCompras
4. Atualizar o campo odoo_po_id para o valor correto

ATENCAO: Execute APOS o fix_odoo_purchase_order_id_dados.py

USO:
    source .venv/bin/activate
    python scripts/fix_match_odoo_po_id_dados.py

    # Modo dry-run (simula sem salvar)
    python scripts/fix_match_odoo_po_id_dados.py --dry-run

    # Processar apenas N registros
    python scripts/fix_match_odoo_po_id_dados.py --limit 100

Autor: Sistema de Fretes
Data: 2026-01-26
"""

import sys
import os
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.manufatura.models import PedidoCompras
from app.recebimento.models import MatchNfPoItem, MatchAlocacao


def processar(dry_run: bool = False, limit: int = None):
    """
    Corrige o campo odoo_po_id para usar o ID do header (purchase.order).

    Args:
        dry_run: Se True, apenas simula sem salvar
        limit: Limite de registros a processar (None = todos)
    """
    app = create_app()
    with app.app_context():
        try:
            print("=" * 70)
            print("CORRECAO: Atualizar odoo_po_id em MatchNfPoItem e MatchAlocacao")
            print(f"Modo: {'DRY-RUN (simulacao)' if dry_run else 'PRODUCAO (salvando)'}")
            if limit:
                print(f"Limite: {limit} registros")
            print("=" * 70)

            # ============================================================
            # PARTE 1: MatchNfPoItem
            # ============================================================
            print("\n[1/2] Processando MatchNfPoItem...")

            query_match = MatchNfPoItem.query.filter(
                MatchNfPoItem.odoo_po_id.isnot(None),
                MatchNfPoItem.odoo_po_name.isnot(None)
            )

            if limit:
                query_match = query_match.limit(limit)

            matches = query_match.all()
            print(f"  Encontrados {len(matches)} registros")

            # Criar cache de PO header IDs por num_pedido
            po_names = list(set([m.odoo_po_name for m in matches if m.odoo_po_name]))
            print(f"  PO names unicos: {len(po_names)}")

            # Buscar mapeamento num_pedido -> odoo_purchase_order_id
            po_name_to_header = {}
            pedidos = PedidoCompras.query.filter(
                PedidoCompras.num_pedido.in_(po_names),
                PedidoCompras.odoo_purchase_order_id.isnot(None)
            ).all()

            for p in pedidos:
                if p.num_pedido and p.odoo_purchase_order_id:
                    # Pode haver multiplos registros por num_pedido (produtos diferentes)
                    # Todos devem ter o mesmo odoo_purchase_order_id
                    if p.num_pedido not in po_name_to_header:
                        po_name_to_header[p.num_pedido] = int(p.odoo_purchase_order_id)

            print(f"  Mapeamento PO name -> header ID: {len(po_name_to_header)} entradas")

            # Corrigir matches
            match_atualizados = 0
            match_nao_encontrados = 0

            for m in matches:
                header_id = po_name_to_header.get(m.odoo_po_name)

                if not header_id:
                    match_nao_encontrados += 1
                    continue

                # Verificar se ja esta correto
                if m.odoo_po_id == header_id:
                    continue

                if not dry_run:
                    m.odoo_po_id = header_id
                    match_atualizados += 1
                else:
                    print(f"  [DRY-RUN] Match {m.id}: {m.odoo_po_id} -> {header_id}")
                    match_atualizados += 1

            print(f"  Atualizados: {match_atualizados}")
            print(f"  Sem mapeamento: {match_nao_encontrados}")

            # ============================================================
            # PARTE 2: MatchAlocacao
            # ============================================================
            print("\n[2/2] Processando MatchAlocacao...")

            query_aloc = MatchAlocacao.query.filter(
                MatchAlocacao.odoo_po_id.isnot(None),
                MatchAlocacao.odoo_po_name.isnot(None)
            )

            if limit:
                query_aloc = query_aloc.limit(limit)

            alocacoes = query_aloc.all()
            print(f"  Encontrados {len(alocacoes)} registros")

            # Corrigir alocacoes
            aloc_atualizados = 0
            aloc_nao_encontrados = 0

            for a in alocacoes:
                header_id = po_name_to_header.get(a.odoo_po_name)

                if not header_id:
                    aloc_nao_encontrados += 1
                    continue

                # Verificar se ja esta correto
                if a.odoo_po_id == header_id:
                    continue

                if not dry_run:
                    a.odoo_po_id = header_id
                    aloc_atualizados += 1
                else:
                    print(f"  [DRY-RUN] Aloc {a.id}: {a.odoo_po_id} -> {header_id}")
                    aloc_atualizados += 1

            print(f"  Atualizados: {aloc_atualizados}")
            print(f"  Sem mapeamento: {aloc_nao_encontrados}")

            # Commit
            if not dry_run:
                db.session.commit()
                print(f"\nCommit realizado!")

            print("-" * 70)
            print("RESULTADO TOTAL:")
            print(f"  MatchNfPoItem atualizados: {match_atualizados}")
            print(f"  MatchAlocacao atualizados: {aloc_atualizados}")
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
        description='Corrige odoo_po_id em MatchNfPoItem e MatchAlocacao'
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
