"""
Script de Backfill: Preencher Campos Faltantes de Pedidos de Compras

Busca no Odoo dados para pedidos que estão com campos faltantes:
- cnpj_fornecedor (via res.partner)
- icms_produto_pedido, pis_produto_pedido, cofins_produto_pedido (da linha)

Uso:
    python scripts/backfill_campos_pedidos_compras.py [--dry-run] [--limit N]

Exemplos:
    # Testar sem alterar dados (recomendado primeiro)
    python scripts/backfill_campos_pedidos_compras.py --dry-run --limit 10

    # Executar em lote pequeno
    python scripts/backfill_campos_pedidos_compras.py --limit 100

    # Executar todos
    python scripts/backfill_campos_pedidos_compras.py
"""

import sys
import os
import argparse
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app, db
from app.manufatura.models import PedidoCompras
from app.odoo.utils.connection import get_odoo_connection


def buscar_dados_batch_odoo(connection, odoo_line_ids: list) -> dict:
    """
    Busca dados em batch para múltiplas linhas de PO.

    Args:
        connection: Conexão com Odoo
        odoo_line_ids: Lista de IDs de linhas de purchase.order.line

    Retorna: {
        odoo_line_id: {
            'cnpj': str ou None,
            'icms': Decimal,
            'pis': Decimal,
            'cofins': Decimal
        }
    }
    """
    if not odoo_line_ids:
        return {}

    # Passo 1: Buscar linhas com impostos e order_id
    linhas = connection.search_read(
        'purchase.order.line',
        [('id', 'in', odoo_line_ids)],
        fields=[
            'id', 'order_id',
            'l10n_br_icms_valor', 'l10n_br_pis_valor', 'l10n_br_cofins_valor'
        ]
    )

    # Mapear linha → dados da linha + order_id
    linha_dados = {}
    order_ids = set()
    for l in linhas:
        if l.get('order_id'):
            linha_dados[l['id']] = {
                'order_id': l['order_id'][0],
                'icms': Decimal(str(l.get('l10n_br_icms_valor') or 0)),
                'pis': Decimal(str(l.get('l10n_br_pis_valor') or 0)),
                'cofins': Decimal(str(l.get('l10n_br_cofins_valor') or 0))
            }
            order_ids.add(l['order_id'][0])

    if not order_ids:
        return {}

    # Passo 2: Buscar pedidos e seus partner_ids
    pedidos = connection.read(
        'purchase.order',
        list(order_ids),
        fields=['id', 'partner_id']
    )

    # Mapear order_id → partner_id
    order_para_partner = {}
    partner_ids = set()
    for p in pedidos:
        if p.get('partner_id'):
            partner_id = p['partner_id'][0] if isinstance(p['partner_id'], list) else p['partner_id']
            order_para_partner[p['id']] = partner_id
            partner_ids.add(partner_id)

    if not partner_ids:
        # Retornar apenas impostos se não tem partner
        resultado = {}
        for linha_id, dados in linha_dados.items():
            resultado[linha_id] = {
                'cnpj': None,
                'icms': dados['icms'],
                'pis': dados['pis'],
                'cofins': dados['cofins']
            }
        return resultado

    # Passo 3: Buscar fornecedores com CNPJ
    partners = connection.read(
        'res.partner',
        list(partner_ids),
        fields=['id', 'name', 'l10n_br_cnpj']
    )

    # Mapear partner_id → dados
    partner_map = {p['id']: p for p in partners}

    # Passo 4: Montar resultado final
    resultado = {}
    for linha_id, dados in linha_dados.items():
        order_id = dados['order_id']
        partner_id = order_para_partner.get(order_id)

        cnpj = None
        if partner_id:
            partner = partner_map.get(partner_id, {})
            cnpj_raw = partner.get('l10n_br_cnpj')
            # Sanitizar: Odoo retorna False para campos vazios
            if cnpj_raw and cnpj_raw is not False:
                cnpj = cnpj_raw

        resultado[linha_id] = {
            'cnpj': cnpj,
            'icms': dados['icms'],
            'pis': dados['pis'],
            'cofins': dados['cofins']
        }

    return resultado


def main():
    parser = argparse.ArgumentParser(
        description='Backfill campos de Pedidos de Compras',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemplos:
  %(prog)s --dry-run --limit 10    # Testar sem alterar dados
  %(prog)s --limit 100             # Executar em lote pequeno
  %(prog)s                         # Executar todos
        """
    )
    parser.add_argument('--dry-run', action='store_true',
                        help='Apenas simula, não atualiza o banco')
    parser.add_argument('--limit', type=int, default=0,
                        help='Limitar quantidade de registros (0 = todos)')
    parser.add_argument('--batch-size', type=int, default=100,
                        help='Tamanho do batch para consultas no Odoo')
    args = parser.parse_args()

    print("=" * 60)
    print("BACKFILL DE CAMPOS DE PEDIDOS DE COMPRAS")
    print("=" * 60)

    if args.dry_run:
        print("⚠️  MODO DRY-RUN: Nenhuma alteração será feita no banco")

    print()

    app = create_app()
    with app.app_context():
        # Buscar pedidos sem CNPJ (indica que são antigos e podem ter outros campos faltando)
        query = PedidoCompras.query.filter(
            PedidoCompras.cnpj_fornecedor.is_(None),
            PedidoCompras.odoo_id.isnot(None)
        )

        if args.limit > 0:
            query = query.limit(args.limit)

        pedidos_sem_dados = query.all()
        total = len(pedidos_sem_dados)

        print(f"[INFO] Encontrados {total} pedidos para verificar")

        if total == 0:
            print("[INFO] Nenhum pedido para atualizar")
            return

        # Conectar ao Odoo
        print("[INFO] Conectando ao Odoo...")
        connection = get_odoo_connection()
        print("[INFO] Conexão estabelecida ✓")
        print()

        stats = {
            'cnpj_atualizado': 0,
            'icms_atualizado': 0,
            'pis_atualizado': 0,
            'cofins_atualizado': 0,
            'sem_cnpj_odoo': 0,
            'linha_nao_encontrada': 0,
            'erros': 0
        }

        # Processar em batches
        total_batches = (total + args.batch_size - 1) // args.batch_size

        for i in range(0, total, args.batch_size):
            batch = pedidos_sem_dados[i:i + args.batch_size]
            odoo_line_ids = [int(p.odoo_id) for p in batch if p.odoo_id]
            batch_num = i // args.batch_size + 1

            print(f"[INFO] Processando batch {batch_num}/{total_batches}: {len(odoo_line_ids)} linhas")

            try:
                dados_odoo = buscar_dados_batch_odoo(connection, odoo_line_ids)

                for pedido in batch:
                    if not pedido.odoo_id:
                        continue

                    odoo_id = int(pedido.odoo_id)
                    dados = dados_odoo.get(odoo_id)

                    if not dados:
                        stats['linha_nao_encontrada'] += 1
                        continue

                    alteracoes = []

                    # CNPJ
                    if dados.get('cnpj'):
                        if args.dry_run:
                            alteracoes.append(f"CNPJ={dados['cnpj']}")
                        else:
                            pedido.cnpj_fornecedor = dados['cnpj']
                        stats['cnpj_atualizado'] += 1
                    else:
                        stats['sem_cnpj_odoo'] += 1

                    # ICMS (atualizar se atual é NULL ou 0)
                    if dados['icms'] > 0 and not pedido.icms_produto_pedido:
                        if args.dry_run:
                            alteracoes.append(f"ICMS={dados['icms']}")
                        else:
                            pedido.icms_produto_pedido = dados['icms']
                        stats['icms_atualizado'] += 1

                    # PIS (atualizar se atual é NULL ou 0)
                    if dados['pis'] > 0 and not pedido.pis_produto_pedido:
                        if args.dry_run:
                            alteracoes.append(f"PIS={dados['pis']}")
                        else:
                            pedido.pis_produto_pedido = dados['pis']
                        stats['pis_atualizado'] += 1

                    # COFINS (atualizar se atual é NULL ou 0)
                    if dados['cofins'] > 0 and not pedido.cofins_produto_pedido:
                        if args.dry_run:
                            alteracoes.append(f"COFINS={dados['cofins']}")
                        else:
                            pedido.cofins_produto_pedido = dados['cofins']
                        stats['cofins_atualizado'] += 1

                    if alteracoes:
                        if args.dry_run:
                            print(f"  [DRY-RUN] {pedido.num_pedido}: {', '.join(alteracoes)}")
                        else:
                            pedido.atualizado_em = datetime.utcnow()

                if not args.dry_run:
                    db.session.commit()
                    print(f"  ✓ Batch {batch_num} commitado")

            except Exception as e:
                print(f"[ERRO] Batch {batch_num}: {e}")
                stats['erros'] += 1
                if not args.dry_run:
                    db.session.rollback()

        # Resultado final
        print()
        print("=" * 60)
        print("RESULTADO")
        print("=" * 60)
        print(f"  Total processado:        {total}")
        print(f"  CNPJ atualizado:         {stats['cnpj_atualizado']}")
        print(f"  ICMS atualizado:         {stats['icms_atualizado']}")
        print(f"  PIS atualizado:          {stats['pis_atualizado']}")
        print(f"  COFINS atualizado:       {stats['cofins_atualizado']}")
        print(f"  Sem CNPJ no Odoo:        {stats['sem_cnpj_odoo']}")
        print(f"  Linha não encontrada:    {stats['linha_nao_encontrada']}")
        print(f"  Erros:                   {stats['erros']}")
        print("=" * 60)

        if args.dry_run:
            print("\n⚠️  MODO DRY-RUN: Nenhuma alteração foi feita.")
            print("   Execute sem --dry-run para aplicar as mudanças.")


if __name__ == '__main__':
    main()
