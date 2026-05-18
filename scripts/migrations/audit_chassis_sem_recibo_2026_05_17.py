#!/usr/bin/env python3
"""Auditoria retroativa: chassis em assai_moto SEM AssaiReciboItem conferido.

Aplica a nova regra de `_calcular_match` (CHASSI_FATURADO_SEM_RECIBO)
RETROATIVAMENTE: identifica chassis hoje em assai_moto que nunca passaram
por recibo Motochefe conferido + tem NF apontando, e DISPARA
reprocessar_match_nf para cada NF afetada.

O reprocessamento aplica a nova validacao -> NFs viram DIVERGENTE com
tipo CHASSI_FATURADO_SEM_RECIBO. Operador resolve via CCe (NF errada)
ou substituir_chassi (recibo errado).

CONTEXTO 2026-05-17: 13 chassis DOT (LA2026SA0100xxxxx) foram cadastrados
pela parte5 v2.1 do backfill via regex (sem recibo Motochefe — a Motochefe
ainda nao declarou compra deles). Este script flaga essas NFs.

NAO RODA EM BUILD.SH — execucao MANUAL via Render Shell:
    cd /opt/render/project/src
    source .venv/bin/activate
    python scripts/migrations/audit_chassis_sem_recibo_2026_05_17.py --dry-run
    python scripts/migrations/audit_chassis_sem_recibo_2026_05_17.py --apply

Idempotente: re-rodar nao gera divergencias duplicadas — o reprocessamento
em `reprocessar_match_nf` faz reset+re-roda match. Se NF ja tem divergencia
aberta com mesmo tipo, e o estado correto.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)

from app import create_app, db  # noqa: E402


logger = logging.getLogger('audit_chassis_sem_recibo')
MOTIVO = 'AUDIT_CHASSIS_SEM_RECIBO_2026_05_17'


def identificar_nfs_afetadas() -> list[int]:
    """Retorna IDs de NFs cujos chassis estao em assai_moto MAS sem
    AssaiReciboItem(conferido=True, ativo=True).
    """
    from app.motos_assai.models import (
        AssaiNfQpa, AssaiNfQpaItem, AssaiMoto, AssaiReciboItem,
        NF_STATUS_CANCELADA,
    )

    # Subquery: chassis em assai_moto SEM recibo conferido
    chassis_sem_recibo_sq = (
        db.session.query(AssaiMoto.chassi)
        .filter(
            ~db.session.query(AssaiReciboItem.id)
            .filter(
                AssaiReciboItem.chassi == AssaiMoto.chassi,
                AssaiReciboItem.conferido.is_(True),
                AssaiReciboItem.ativo.is_(True),
            )
            .exists()
        )
        .subquery()
    )

    # NFs ativas cujos chassis caem nesta subquery
    nfs = (
        db.session.query(AssaiNfQpa.id)
        .join(AssaiNfQpaItem, AssaiNfQpaItem.nf_id == AssaiNfQpa.id)
        .filter(
            AssaiNfQpaItem.chassi.in_(db.session.query(chassis_sem_recibo_sq.c.chassi)),
            AssaiNfQpa.status_match != NF_STATUS_CANCELADA,
        )
        .distinct()
        .all()
    )
    return sorted({n[0] for n in nfs})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dry-run', action='store_true',
                       help='Lista NFs afetadas sem reprocessar')
    group.add_argument('--apply', action='store_true',
                       help='Reprocessa NFs (cria divergencias CHASSI_FATURADO_SEM_RECIBO)')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    )

    app = create_app()
    with app.app_context():
        logger.info('=== audit_chassis_sem_recibo ===')

        nf_ids = identificar_nfs_afetadas()
        logger.info('Encontradas %d NF(s) afetadas: %s', len(nf_ids), nf_ids)

        if not nf_ids:
            logger.info('NO-OP: nenhuma NF com chassi sem recibo.')
            return 0

        # Detalhamento
        from app.motos_assai.models import (
            AssaiNfQpa, AssaiMoto, AssaiReciboItem,
        )
        for nf_id in nf_ids:
            nf = AssaiNfQpa.query.get(nf_id)
            items_orfaos = [
                it for it in nf.itens
                if AssaiMoto.query.filter_by(chassi=it.chassi).first()
                and not AssaiReciboItem.query.filter_by(
                    chassi=it.chassi, conferido=True, ativo=True,
                ).first()
            ]
            logger.info(
                '  NF %s (numero=%s loja=%s status=%s): %d/%d chassis sem recibo',
                nf.id, nf.numero, nf.loja_id, nf.status_match,
                len(items_orfaos), len(nf.itens),
            )

        if args.dry_run:
            logger.info('DRY-RUN. Para reprocessar: --apply')
            return 0

        # Reprocessar
        from app.motos_assai.services.reprocessar_match_service import (
            reprocessar_match_nfs,
        )
        from app.auth.models import Usuario
        admin = Usuario.query.filter_by(perfil='administrador').first()
        operador_id = admin.id if admin else 1

        stats = reprocessar_match_nfs(
            nf_ids, motivo=MOTIVO, operador_id=operador_id,
        )
        logger.info('reprocessar_match_nfs stats: total=%d ok=%d mudou=%d skipped=%d erro=%d',
                    stats['total'], stats['ok'], stats['mudou_status'],
                    stats['skipped'], stats['erro'])
        for det in stats['detalhes']:
            if det.get('status_anterior') != det.get('status_novo'):
                logger.info('  NF %s: %s -> %s',
                            det.get('nf_id'), det.get('status_anterior'),
                            det.get('status_novo'))

        logger.info('CONCLUIDO. Divergencias CHASSI_FATURADO_SEM_RECIBO criadas.')
        return 0


if __name__ == '__main__':
    sys.exit(main())
