#!/usr/bin/env python3
"""Cleanup: remove pedido placeholder BACKFILL e desvincula NF 1737.

Contexto (Rafael 2026-05-18):
  O script motos_assai_backfill_match_nfs_2026_05_17.py criou o pedido
  placeholder 'BACKFILL-2026-05-17' (id=3) com 1 separacao (sep 48
  FATURADA, loja 11 Aricanduva) vinculada a NF 1737 (id=7, BATEU).
  Como nao existe pedido REAL para a loja 11, o placeholder ficou
  no banco. A solucao definitiva e:

      1. Cancelar sep 48 e reverter 3 chassis para DISPONIVEL.
    2. Desvincular NF 1737 (separacao_id=NULL, status_match=NAO_RECONCILIADO,
       items com separacao_item_id=NULL e tipo_divergencia=NULL).
    3. Deletar AssaiPedidoVendaLoja(id=4605) + AssaiPedidoVenda(id=3).

  Nota: os 3 chassis EXISTEM em recibos Motochefe concluidos (recibo 8 e 9),
  entao quando o pedido REAL for cadastrado e a NF for vinculada manualmente
  via "Vincular NF", `_calcular_match` vai bater novamente sem divergencia.

  IMPORTANTE: este script roda APENAS UMA VEZ. NAO incluir no build.sh.
  Tambem precisa REMOVER motos_assai_backfill_match_nfs_2026_05_17.py do
  build.sh, senao a cada deploy o backfill RECRIA o pedido placeholder.

Idempotente:
  - Skip se pedido BACKFILL nao existe mais (ja rodou).
  - Skip se sep 48 ja CANCELADA.
  - Skip se NF 1737 ja desvinculada.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys

# sys.path para imports app.* funcionarem em Render Shell e CLI local
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)

from app import create_app, db  # noqa: E402
from app.utils.timezone import agora_brasil_naive  # noqa: E402


PEDIDO_PLACEHOLDER_NUMERO = 'BACKFILL-2026-05-17'
NF_ALVO_NUMERO = '1737'
MOTIVO = 'CLEANUP_PEDIDO_BACKFILL_2026_05_18'

logger = logging.getLogger('cleanup_backfill_nf_1737')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Mostra o plano sem mutar dados.',
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    )

    app = create_app()
    with app.app_context():
        from app.motos_assai.models import (
            AssaiPedidoVenda, AssaiPedidoVendaLoja,
            AssaiSeparacao, AssaiSeparacaoItem,
            AssaiNfQpa, AssaiNfQpaItem,
            SEPARACAO_STATUS_CANCELADA,
            NF_STATUS_NAO_RECONCILIADO,
            EVENTO_DISPONIVEL,
        )
        from app.motos_assai.services.moto_evento_service import emitir_evento
        from app.auth.models import Usuario

        admin = Usuario.query.filter_by(perfil='administrador').first()
        operador_id = admin.id if admin else 1

        # ─── 1. Localizar pedido placeholder ─────────────────────────────────
        pedido = AssaiPedidoVenda.query.filter_by(
            numero=PEDIDO_PLACEHOLDER_NUMERO,
        ).first()
        if not pedido:
            logger.info('[no-op] Pedido %r nao existe — cleanup ja foi feito.',
                        PEDIDO_PLACEHOLDER_NUMERO)
            return

        logger.info('Pedido placeholder encontrado: id=%s numero=%r status=%s',
                    pedido.id, pedido.numero, pedido.status)

        # ─── 2. Listar separacoes do pedido ──────────────────────────────────
        seps = AssaiSeparacao.query.filter_by(pedido_id=pedido.id).all()
        logger.info('%d separacao(oes) vinculadas ao pedido', len(seps))

        for sep in seps:
            if sep.status == SEPARACAO_STATUS_CANCELADA:
                logger.info('[skip] sep %s ja CANCELADA', sep.id)
                continue

            chassis_da_sep = [
                it.chassi for it in
                AssaiSeparacaoItem.query.filter_by(separacao_id=sep.id).all()
            ]
            logger.info('sep %s status=%s chassis=%s',
                        sep.id, sep.status, chassis_da_sep)

            # NFs vinculadas a essa sep
            nfs_vinculadas = AssaiNfQpa.query.filter_by(
                separacao_id=sep.id,
            ).all()
            logger.info('  -> %d NF(s) vinculadas: %s',
                        len(nfs_vinculadas),
                        [(n.id, n.numero, n.status_match) for n in nfs_vinculadas])

            if args.dry_run:
                logger.info('[DRY-RUN] cancelaria sep %s + reverteria %d chassis + desvincularia %d NFs',
                            sep.id, len(chassis_da_sep), len(nfs_vinculadas))
                continue

            # 2a. Desvincular NFs (separacao_id=NULL, status=NAO_RECONCILIADO)
            #     Items: separacao_item_id=NULL + tipo_divergencia=NULL.
            #     Os chassis EXISTEM em recibos Motochefe — quando operador
            #     vincular a NF a um pedido real via "Vincular NF", o
            #     `_calcular_match` recalcula sem erros (todas as condicoes
            #     ficam BATEU: chassi em assai_moto, em recibo conferido,
            #     loja resolvida via CNPJ).
            for nf in nfs_vinculadas:
                logger.info('  desvinculando NF %s (numero=%r): separacao_id NULL, status %s -> NAO_RECONCILIADO',
                            nf.id, nf.numero, nf.status_match)
                nf.separacao_id = None
                nf.status_match = NF_STATUS_NAO_RECONCILIADO
                for it_nf in AssaiNfQpaItem.query.filter_by(nf_id=nf.id).all():
                    it_nf.separacao_item_id = None
                    it_nf.tipo_divergencia = None

            # 2b. Cancelar separacao
            sep.status = SEPARACAO_STATUS_CANCELADA
            sep.motivo_cancelamento = (
                f'{MOTIVO}: pedido placeholder removido. '
                'NFs voltaram a NAO_RECONCILIADO para vinculacao manual quando '
                'pedido real for cadastrado.'
            )
            sep.fechada_em = agora_brasil_naive()

            # 2c. Reverter eventos: chassis voltam para DISPONIVEL
            for chassi in chassis_da_sep:
                emitir_evento(
                    chassi, EVENTO_DISPONIVEL,
                    operador_id=operador_id,
                    observacao=f'{MOTIVO} sep {sep.id} cancelada',
                    dados_extras={
                        'origem': MOTIVO,
                        'sep_cancelada': sep.id,
                    },
                )
                logger.info('  chassi %s -> evento DISPONIVEL', chassi)

        # ─── 3. Apagar AssaiPedidoVendaLoja do pedido ────────────────────────
        pvls = AssaiPedidoVendaLoja.query.filter_by(pedido_id=pedido.id).all()
        for pvl in pvls:
            logger.info('  deletando AssaiPedidoVendaLoja id=%s loja=%s',
                        pvl.id, pvl.loja_id)
            if not args.dry_run:
                db.session.delete(pvl)

        # ─── 4. Apagar o proprio pedido ──────────────────────────────────────
        logger.info('  deletando AssaiPedidoVenda id=%s numero=%r',
                    pedido.id, pedido.numero)
        if not args.dry_run:
            db.session.delete(pedido)
            db.session.commit()
            logger.info('=== cleanup COMMITADO ===')
        else:
            db.session.rollback()
            logger.info('=== DRY-RUN: nenhuma mudanca aplicada ===')


if __name__ == '__main__':
    main()
