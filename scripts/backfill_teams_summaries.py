"""
Backfill de summaries para sessões Teams sem sumarização.

Contexto: O post-session processing do Teams não gerava summaries automaticamente
antes do commit f4fae4db (2026-03-13). Este script sumariza retroativamente
as sessões que ficaram sem summary.

Uso:
    # Dry-run (default): lista sessões candidatas sem alterar
    python scripts/backfill_teams_summaries.py

    # Executar backfill
    python scripts/backfill_teams_summaries.py --execute

    # Filtrar por user_id
    python scripts/backfill_teams_summaries.py --execute --user-id 69

    # Limitar quantidade (para testar)
    python scripts/backfill_teams_summaries.py --execute --limit 5

Custo estimado: ~$0.003 por sessão (Sonnet, ~2K tokens input, ~500 output).
"""

import argparse
import logging
import sys
import os
import time

# Setup path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger('backfill_summaries')


def main():
    parser = argparse.ArgumentParser(description='Backfill summaries para sessões Teams')
    parser.add_argument('--execute', action='store_true', help='Executar backfill (sem = dry-run)')
    parser.add_argument('--user-id', type=int, help='Filtrar por user_id específico')
    parser.add_argument('--limit', type=int, default=100, help='Máximo de sessões (default: 100)')
    parser.add_argument(
        '--min-messages', type=int, default=5,
        help='Mínimo de mensagens para sumarizar (default: 5)',
    )
    args = parser.parse_args()

    from app import create_app
    app = create_app()

    with app.app_context():
        from app.agente.models import AgentSession

        # Buscar sessões Teams sem summary, com mensagens suficientes
        query = AgentSession.query.filter(
            AgentSession.session_id.like('teams_%'),
            AgentSession.summary.is_(None),
            AgentSession.message_count >= args.min_messages,
        )

        if args.user_id:
            query = query.filter(AgentSession.user_id == args.user_id)

        query = query.order_by(AgentSession.message_count.desc())
        sessions = query.limit(args.limit).all()

        if not sessions:
            logger.info("Nenhuma sessão Teams sem summary encontrada.")
            return

        # Agrupar por user_id para relatório
        by_user = {}
        for s in sessions:
            uid = s.user_id or 0
            by_user.setdefault(uid, []).append(s)

        logger.info(f"=== {'DRY-RUN' if not args.execute else 'EXECUTANDO'} ===")
        logger.info(f"Sessões candidatas: {len(sessions)}")
        for uid, user_sessions in sorted(by_user.items()):
            user_name = user_sessions[0].user.nome if user_sessions[0].user else f'user_{uid}'
            total_msgs = sum(s.message_count or 0 for s in user_sessions)
            logger.info(
                f"  user_id={uid} ({user_name}): "
                f"{len(user_sessions)} sessões, {total_msgs} msgs total"
            )

        if not args.execute:
            logger.info("\nAdicione --execute para processar.")
            logger.info(f"Custo estimado: ~${len(sessions) * 0.003:.2f}")
            return

        # Executar backfill
        from app.agente.services.session_summarizer import summarize_and_save

        success = 0
        failed = 0
        skipped = 0

        for i, session in enumerate(sessions, 1):
            session_id = session.session_id
            user_id = session.user_id or 0
            msg_count = session.message_count or 0

            logger.info(
                f"[{i}/{len(sessions)}] Sumarizando {session_id[:20]}... "
                f"(user={user_id}, msgs={msg_count})"
            )

            try:
                result = summarize_and_save(
                    app=app,
                    session_id=session_id,
                    user_id=user_id,
                )
                if result:
                    success += 1
                    logger.info(f"  ✓ Summary salvo")
                else:
                    skipped += 1
                    logger.info(f"  - Pulado (sem mensagens suficientes ou erro)")

                # Rate limiting: ~1 req/s para não estourar API
                time.sleep(1.2)

            except Exception as e:
                failed += 1
                logger.error(f"  ✗ Erro: {e}")

        logger.info(f"\n=== RESULTADO ===")
        logger.info(f"Sucesso: {success}")
        logger.info(f"Pulados: {skipped}")
        logger.info(f"Falhas:  {failed}")
        logger.info(f"Custo estimado: ~${success * 0.003:.3f}")


if __name__ == '__main__':
    main()
