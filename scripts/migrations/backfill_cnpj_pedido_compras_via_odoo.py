#!/usr/bin/env python3
"""
Backfill: cnpj_fornecedor NULL em pedido_compras via Odoo
==========================================================

PROBLEMA:
O sync incremental (PedidoComprasServiceOtimizado.sincronizar_pedidos_incremental)
filtra purchase.order por create_date OR write_date dentro da janela (-90min).
Se um partner Odoo eh atualizado (CNPJ adicionado) APOS a criacao do PO, o
write_date do purchase.order nao muda, e o re-sync ignora o PO para sempre.

Resultado: POs ativos (status_odoo in purchase/to approve/draft) ficam com
cnpj_fornecedor=NULL. A validacao Fase 2 (NF x PO) filtra POs por CNPJ ANTES
de comparar preco/qtd — POs sem CNPJ sao descartados silenciosamente e a NF
cai em "sem_po" (bloqueio invisivel no modal de candidatos).

INVESTIGACAO ORIGINAL: agent_sessions.id=560 (Teams - Rafael, 11/05/2026 17:27)
NF 143343 da Novacki bloqueada por PO C2615916 com cnpj_fornecedor=NULL.

SOLUCAO:
Re-sincronizar via odoo_purchase_order_id (independente da janela temporal):
  1. Coletar POs locais ativos com cnpj_fornecedor IS NULL
  2. Batch read purchase.order -> partner_id
  3. Batch read res.partner -> l10n_br_cnpj
  4. UPDATE pedido_compras + snapshot HistoricoPedidoCompras

Idempotente: rodar 2x consecutivas = segunda nao faz nada.

USO:
    source .venv/bin/activate

    # Dry-run (default — apenas reporta contadores):
    python scripts/migrations/backfill_cnpj_pedido_compras_via_odoo.py

    # Executar batch limitado:
    python scripts/migrations/backfill_cnpj_pedido_compras_via_odoo.py --aplicar

    # Customizar tamanho do batch por chamada:
    python scripts/migrations/backfill_cnpj_pedido_compras_via_odoo.py --aplicar --batch 200

    # Limitar total maximo de POs por execucao (default: 500):
    python scripts/migrations/backfill_cnpj_pedido_compras_via_odoo.py --aplicar --max-pos 500

    # Status_odoo customizados (default: purchase,to approve,draft):
    python scripts/migrations/backfill_cnpj_pedido_compras_via_odoo.py --aplicar \
        --status "purchase,done,to approve,draft"

Data: 2026-05-11
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
import time

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db  # noqa: E402
from app.manufatura.models import PedidoCompras  # noqa: E402
from app.odoo.services.pedido_compras_service import PedidoComprasServiceOtimizado  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger('backfill_cnpj')


def _contar_pendentes(status_filter):
    """Conta POs ativos com cnpj_fornecedor NULL."""
    return (
        PedidoCompras.query
        .filter(
            PedidoCompras.cnpj_fornecedor.is_(None),
            PedidoCompras.status_odoo.in_(status_filter),
            PedidoCompras.odoo_purchase_order_id.isnot(None)
        )
        .count()
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        '--aplicar', action='store_true',
        help='Executa o backfill. Sem essa flag, apenas reporta contadores (dry-run).'
    )
    parser.add_argument(
        '--batch', type=int, default=100,
        help='POs Odoo distintos lidos por chamada (default: 100)'
    )
    parser.add_argument(
        '--max-pos', type=int, default=500,
        help='Maximo total de POs distintos por execucao (default: 500). Evita rodar infinito.'
    )
    parser.add_argument(
        '--status', type=str, default='purchase,to approve,draft',
        help='Status_odoo separados por virgula (default: "purchase,to approve,draft")'
    )
    args = parser.parse_args()

    status_filter = [s.strip() for s in args.status.split(',') if s.strip()]

    app = create_app()
    with app.app_context():
        pendentes_inicio = _contar_pendentes(status_filter)
        logger.info("=" * 72)
        logger.info(f"BACKFILL cnpj_fornecedor NULL — pedido_compras (via Odoo)")
        logger.info(f"  Status considerados: {status_filter}")
        logger.info(f"  POs pendentes (inicio): {pendentes_inicio}")
        logger.info(f"  Modo: {'APLICAR' if args.aplicar else 'DRY-RUN'}")
        logger.info(f"  Batch: {args.batch}  |  Max POs: {args.max_pos}")
        logger.info("=" * 72)

        if pendentes_inicio == 0:
            logger.info("✅ Nada a fazer. Saindo.")
            return 0

        if not args.aplicar:
            logger.info(
                "DRY-RUN: nenhum UPDATE sera executado. "
                "Rode com --aplicar para corrigir os registros."
            )
            return 0

        service = PedidoComprasServiceOtimizado()
        total_processados = 0
        total_linhas_corrigidas = 0
        total_partner_sem_cnpj = 0
        total_sem_partner = 0
        total_nao_encontrados = 0
        rodadas = 0
        inicio = time.time()

        while total_processados < args.max_pos:
            limite_rodada = min(args.batch, args.max_pos - total_processados)
            try:
                resultado = service.backfill_cnpj_via_odoo(
                    limit=limite_rodada,
                    status_filter=status_filter
                )
            except Exception as e:
                logger.error(f"❌ Erro na rodada {rodadas + 1}: {e}", exc_info=True)
                break

            processados = resultado.get('pos_distintos_processados', 0)
            corrigidos = resultado.get('linhas_corrigidas', 0)
            partner_sem_cnpj = resultado.get('pos_partner_sem_cnpj', 0)
            sem_partner = resultado.get('pos_sem_partner', 0)
            nao_encontrados = resultado.get('pos_nao_encontrados_odoo', 0)

            try:
                db.session.commit()
            except Exception as e:
                logger.error(f"❌ Erro no commit da rodada {rodadas + 1}: {e}", exc_info=True)
                db.session.rollback()
                break

            total_processados += processados
            total_linhas_corrigidas += corrigidos
            total_partner_sem_cnpj += partner_sem_cnpj
            total_sem_partner += sem_partner
            total_nao_encontrados += nao_encontrados
            rodadas += 1

            logger.info(
                f"  Rodada {rodadas}: processados={processados}  corrigidos={corrigidos}  "
                f"partner_sem_cnpj={partner_sem_cnpj}  sem_partner={sem_partner}  "
                f"nao_encontrados={nao_encontrados}"
            )

            # Se a rodada nao corrigiu NENHUMA linha, a proxima vai pegar os mesmos
            # POs anomalos (partner_sem_cnpj / excluidos do Odoo) e nao progredir.
            # Break unico que cobre todos os casos sem progresso (incluindo batch vazio).
            if corrigidos == 0:
                if processados == 0 and partner_sem_cnpj == 0 and sem_partner == 0 and nao_encontrados == 0:
                    logger.info("✅ Conjunto de NULLs esgotado.")
                else:
                    logger.info(
                        "⚠️  Rodada sem progresso "
                        f"(partner_sem_cnpj={partner_sem_cnpj}, sem_partner={sem_partner}, "
                        f"nao_encontrados={nao_encontrados}). "
                        "POs restantes precisam de correcao manual no Odoo."
                    )
                break

        pendentes_fim = _contar_pendentes(status_filter)
        duracao = time.time() - inicio

        logger.info("=" * 72)
        logger.info(f"FINALIZADO em {duracao:.1f}s ({rodadas} rodadas)")
        logger.info(f"  POs Odoo distintos processados: {total_processados}")
        logger.info(f"  Linhas pedido_compras corrigidas: {total_linhas_corrigidas}")
        logger.info(f"  Partner Odoo sem l10n_br_cnpj: {total_partner_sem_cnpj}")
        logger.info(f"  POs Odoo sem partner_id: {total_sem_partner}")
        logger.info(f"  POs nao encontrados no Odoo: {total_nao_encontrados}")
        logger.info(f"  Pendentes (inicio): {pendentes_inicio}")
        logger.info(f"  Pendentes (fim): {pendentes_fim}")
        logger.info(f"  Resolvidos nesta execucao: {pendentes_inicio - pendentes_fim}")
        logger.info("=" * 72)

        return 0


if __name__ == '__main__':
    sys.exit(main())
