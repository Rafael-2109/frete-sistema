# -*- coding: utf-8 -*-
"""
Backfill: Resolver favorecidos para itens de extrato existentes
================================================================

Duas fases:
1. Re-buscar partner_id/partner_name do Odoo para itens existentes
2. Executar pipeline FavorecidoResolverService em todos os lotes de saída

Uso:
    source .venv/bin/activate
    python scripts/migrations/backfill_favorecido_extrato_item.py

Flags:
    --fase1-only    Só re-buscar dados do Odoo (sem resolver)
    --fase2-only    Só executar pipeline (assume dados Odoo já presentes)
    --lote=ID       Processar apenas um lote específico
    --dry-run       Mostrar o que seria feito, sem commit
"""

import sys
import os
import argparse
import logging
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _odoo_search_read_with_retry(conn, model, domain, fields, max_retries=2):
    """search_read com retry e re-autenticação."""
    for attempt in range(max_retries):
        try:
            return conn.search_read(model, domain, fields=fields)
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"Erro Odoo (tentativa {attempt + 1}): {e}")
                try:
                    conn.authenticate()
                except Exception:
                    pass
                time.sleep(1)
            else:
                raise


def fase1_rebuscar_partner_data(conn, dry_run=False):
    """
    Fase 1: Re-buscar partner_id e partner_name do Odoo para itens existentes.

    Faz batch search_read nos statement_line_ids para preencher
    odoo_partner_id e odoo_partner_name. Commit por batch para não perder
    progresso em caso de SSL drop.
    """
    from app import db
    from app.financeiro.models import ExtratoItem, ExtratoLote
    from app.utils.database_retry import commit_with_retry
    from app.utils.database_helpers import ensure_connection

    # Buscar itens de lotes de saída que não têm odoo_partner_id
    itens = ExtratoItem.query.join(ExtratoLote).filter(
        ExtratoLote.tipo_transacao == 'saida',
        ExtratoItem.odoo_partner_id.is_(None),
        ExtratoItem.statement_line_id.isnot(None)
    ).all()

    logger.info(f"Fase 1: {len(itens)} itens sem odoo_partner_id")

    if not itens:
        return 0

    # Buscar dados do Odoo em batches de 100
    statement_line_ids = [i.statement_line_id for i in itens]
    item_por_stl = {i.statement_line_id: i for i in itens}

    atualizados = 0
    batch_size = 100
    total_batches = (len(statement_line_ids) + batch_size - 1) // batch_size

    for i in range(0, len(statement_line_ids), batch_size):
        batch_ids = statement_line_ids[i:i + batch_size]
        batch_num = (i // batch_size) + 1

        ensure_connection()

        try:
            linhas = _odoo_search_read_with_retry(
                conn, 'account.bank.statement.line',
                [['id', 'in', batch_ids]],
                ['id', 'partner_id', 'partner_name']
            ) or []

            for linha in linhas:
                stl_id = linha['id']
                item = item_por_stl.get(stl_id)
                if not item:
                    continue

                partner_id = linha.get('partner_id')
                partner_name = linha.get('partner_name')

                if partner_id:
                    if isinstance(partner_id, (list, tuple)):
                        item.odoo_partner_id = partner_id[0]
                        item.odoo_partner_name = partner_id[1] if len(partner_id) > 1 else None
                    elif isinstance(partner_id, int):
                        item.odoo_partner_id = partner_id

                if partner_name and not item.odoo_partner_name:
                    item.odoo_partner_name = partner_name

                if item.odoo_partner_id:
                    atualizados += 1

            if not dry_run:
                commit_with_retry(db.session)

            logger.info(f"  Batch {batch_num}/{total_batches}: processado ({atualizados} atualizados)")

        except Exception as e:
            logger.error(f"  Erro no batch {batch_num}/{total_batches}: {e}")
            try:
                db.session.rollback()
            except Exception:
                pass

    if dry_run:
        db.session.rollback()
        logger.info(f"Fase 1 (DRY-RUN): {atualizados} itens seriam atualizados")
    else:
        logger.info(f"Fase 1 concluída: {atualizados} itens atualizados com partner_id")

    return atualizados


def fase2_executar_pipeline(conn, lote_id=None, dry_run=False):
    """
    Fase 2: Executar FavorecidoResolverService em lotes de saída.
    Commit por lote + retry em SSL drop.
    """
    from app import db
    from app.financeiro.models import ExtratoLote
    from app.financeiro.services.favorecido_resolver_service import FavorecidoResolverService
    from app.utils.database_retry import commit_with_retry
    from app.utils.database_helpers import ensure_connection
    from sqlalchemy.exc import OperationalError, DBAPIError

    # Buscar lotes de saída
    query = ExtratoLote.query.filter_by(tipo_transacao='saida')
    if lote_id:
        query = query.filter_by(id=lote_id)

    lotes = query.all()

    logger.info(f"Fase 2: {len(lotes)} lotes de saída para processar")

    resolver = FavorecidoResolverService(connection=conn)
    stats_total = {'total': 0, 'resolvidos': 0, 'metodos': {}}

    for idx, lote in enumerate(lotes, 1):
        ensure_connection()

        try:
            logger.info(f"\n--- Lote {lote.id}: {lote.nome} ({lote.total_linhas} linhas) [{idx}/{len(lotes)}] ---")
            stats = resolver.resolver_lote(lote.id)

            stats_total['total'] += stats['total']
            stats_total['resolvidos'] += stats['resolvidos']
            for metodo, count in stats['metodos'].items():
                stats_total['metodos'][metodo] = stats_total['metodos'].get(metodo, 0) + count

            if not dry_run:
                commit_with_retry(db.session)

        except (OperationalError, DBAPIError) as e:
            error_msg = str(e).lower()
            is_ssl = any(err in error_msg for err in [
                'ssl', 'decryption', 'bad record', 'eof detected',
                'connection reset', 'server closed'
            ])

            if is_ssl:
                logger.warning(f"  SSL drop no lote {lote.id}, tentando retry...")
                try:
                    db.session.rollback()
                    db.session.close()
                    db.engine.dispose()
                except Exception:
                    pass
                time.sleep(1)

                # Retry uma vez
                try:
                    ensure_connection()
                    stats = resolver.resolver_lote(lote.id)
                    stats_total['total'] += stats['total']
                    stats_total['resolvidos'] += stats['resolvidos']
                    for metodo, count in stats['metodos'].items():
                        stats_total['metodos'][metodo] = stats_total['metodos'].get(metodo, 0) + count

                    if not dry_run:
                        commit_with_retry(db.session)

                    logger.info(f"  Retry do lote {lote.id} bem-sucedido")
                except Exception as retry_e:
                    logger.error(f"  Erro no retry do lote {lote.id}: {retry_e}")

        except Exception as e:
            logger.error(f"  Erro no lote {lote.id}: {e}")

    if dry_run:
        db.session.rollback()
        logger.info(f"\nFase 2 (DRY-RUN): {stats_total}")
    else:
        logger.info(f"\nFase 2 concluída: {stats_total}")

    return stats_total


def executar():
    parser = argparse.ArgumentParser(description='Backfill de favorecido em extrato_item')
    parser.add_argument('--fase1-only', action='store_true', help='Só fase 1')
    parser.add_argument('--fase2-only', action='store_true', help='Só fase 2')
    parser.add_argument('--lote', type=int, default=None, help='Lote específico')
    parser.add_argument('--dry-run', action='store_true', help='Não commitar')
    args = parser.parse_args()

    from app import create_app
    from app.odoo.utils.connection import get_odoo_connection

    app = create_app()
    with app.app_context():
        conn = get_odoo_connection()
        if not conn.authenticate():
            logger.error("Falha na autenticação com Odoo")
            sys.exit(1)

        print("=" * 60)
        print("BACKFILL: Favorecido em extrato_item")
        print("=" * 60)

        if not args.fase2_only:
            fase1_rebuscar_partner_data(conn, dry_run=args.dry_run)

        if not args.fase1_only:
            fase2_executar_pipeline(conn, lote_id=args.lote, dry_run=args.dry_run)

        print("\nBackfill concluído!")


if __name__ == '__main__':
    executar()
