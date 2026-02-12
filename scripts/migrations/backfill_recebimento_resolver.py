# -*- coding: utf-8 -*-
"""
Backfill: Resolver pagadores para itens de extrato de ENTRADA existentes
========================================================================

Executa o RecebimentoResolverService para todos os lotes de entrada
que possuem itens sem favorecido resolvido.

Uso:
    python scripts/migrations/backfill_recebimento_resolver.py [--dry-run]

Flags:
    --dry-run   Mostra estatísticas sem persistir no banco
"""

import sys
import os
import argparse
import logging
import time

# Setup path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from app.financeiro.models import ExtratoItem, ExtratoLote

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description='Backfill resolver de pagadores (entrada)')
    parser.add_argument('--dry-run', action='store_true', help='Preview sem persistir')
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        from app.utils.database_retry import commit_with_retry
        from app.utils.database_helpers import ensure_connection
        from sqlalchemy.exc import OperationalError, DBAPIError

        # Buscar lotes de entrada com itens pendentes
        lotes_pendentes = db.session.query(ExtratoLote.id, ExtratoLote.statement_name).filter(
            ExtratoLote.tipo_transacao == 'entrada'
        ).join(
            ExtratoItem, ExtratoItem.lote_id == ExtratoLote.id
        ).filter(
            ExtratoItem.favorecido_metodo.is_(None)
        ).distinct().all()

        if not lotes_pendentes:
            logger.info("Nenhum lote de entrada com itens pendentes encontrado.")
            return

        logger.info(f"Lotes de entrada com itens pendentes: {len(lotes_pendentes)}")

        # Importar resolver (lazy para evitar conexão Odoo em dry-run)
        from app.financeiro.services.recebimento_resolver_service import RecebimentoResolverService

        stats_global = {
            'total_lotes': len(lotes_pendentes),
            'total_itens': 0,
            'total_resolvidos': 0,
            'metodos': {},
            'erros_lote': 0,
        }

        resolver = RecebimentoResolverService()

        for idx, (lote_id, statement_name) in enumerate(lotes_pendentes, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"Processando lote {lote_id}: {statement_name} [{idx}/{len(lotes_pendentes)}]")
            logger.info(f"{'='*60}")

            ensure_connection()

            try:
                if args.dry_run:
                    # Em dry-run, contar itens pendentes sem resolver
                    count = ExtratoItem.query.filter(
                        ExtratoItem.lote_id == lote_id,
                        ExtratoItem.favorecido_metodo.is_(None)
                    ).count()
                    logger.info(f"  [DRY-RUN] {count} itens seriam processados")
                    stats_global['total_itens'] += count
                else:
                    stats = resolver.resolver_lote(lote_id)
                    stats_global['total_itens'] += stats['total']
                    stats_global['total_resolvidos'] += stats['resolvidos']

                    for metodo, count in stats['metodos'].items():
                        stats_global['metodos'][metodo] = stats_global['metodos'].get(metodo, 0) + count

                    logger.info(f"  Resultado: {stats['resolvidos']}/{stats['total']} resolvidos")
                    logger.info(f"  Métodos: {stats['metodos']}")

                    commit_with_retry(db.session)

            except (OperationalError, DBAPIError) as e:
                error_msg = str(e).lower()
                is_ssl = any(err in error_msg for err in [
                    'ssl', 'decryption', 'bad record', 'eof detected',
                    'connection reset', 'server closed'
                ])

                if is_ssl:
                    logger.warning(f"  SSL drop no lote {lote_id}, tentando retry...")
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
                        stats = resolver.resolver_lote(lote_id)
                        stats_global['total_itens'] += stats['total']
                        stats_global['total_resolvidos'] += stats['resolvidos']

                        for metodo, count in stats['metodos'].items():
                            stats_global['metodos'][metodo] = stats_global['metodos'].get(metodo, 0) + count

                        commit_with_retry(db.session)
                        logger.info(f"  Retry do lote {lote_id} bem-sucedido")
                    except Exception as retry_e:
                        logger.error(f"  Erro no retry do lote {lote_id}: {retry_e}")
                        stats_global['erros_lote'] += 1
                else:
                    logger.error(f"  ERRO no lote {lote_id}: {e}")
                    stats_global['erros_lote'] += 1

            except Exception as e:
                logger.error(f"  ERRO no lote {lote_id}: {e}")
                stats_global['erros_lote'] += 1

        # Resumo final
        logger.info(f"\n{'='*60}")
        logger.info("RESUMO FINAL")
        logger.info(f"{'='*60}")
        logger.info(f"Lotes processados: {stats_global['total_lotes']}")
        logger.info(f"Total itens: {stats_global['total_itens']}")

        if not args.dry_run:
            logger.info(f"Resolvidos: {stats_global['total_resolvidos']}")
            logger.info(f"Métodos: {stats_global['metodos']}")
            logger.info(f"Erros de lote: {stats_global['erros_lote']}")

            taxa = (
                stats_global['total_resolvidos'] / stats_global['total_itens'] * 100
                if stats_global['total_itens'] > 0 else 0
            )
            logger.info(f"Taxa de resolução: {taxa:.1f}%")
        else:
            logger.info("[DRY-RUN] Nenhuma alteração persistida.")


if __name__ == '__main__':
    main()
