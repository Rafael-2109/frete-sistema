#!/usr/bin/env python3
"""Cleanup do pedido placeholder BACKFILL-2026-05-17 — NF 7 fica orfa.

Contexto: o backfill v2.1 criou o pedido placeholder `BACKFILL-2026-05-17`
(id=2) para a NF 7 (numero=1737, loja 11 ARICANDUVA) porque a Q.P.A. nao
emitiu pedido VOE para essa loja com os valores anomalos da NF
(R$ 3.300/chassi vs R$ 5.800-7.100 do pedido 1).

Rafael decidiu (2026-05-17): remover o placeholder e deixar a NF orfa
ate ele identificar/criar o pedido VOE real. Cancela a sep sintetica,
NF volta para NAO_RECONCILIADO.

NAO RODA EM BUILD.SH — execucao manual unica via Render Shell:
    cd /opt/render/project/src
    source .venv/bin/activate
    python scripts/migrations/cleanup_placeholder_nf7_orfa.py --dry-run
    python scripts/migrations/cleanup_placeholder_nf7_orfa.py --apply

Idempotente: re-rodar apos sucesso e no-op (verifica precondicoes).

PRECONDICOES (verificadas antes de tocar em qualquer coisa):
  - AssaiPedidoVenda(id=2, numero='BACKFILL-2026-05-17') existe
  - AssaiSeparacao(id=10, loja_id=11, status=FATURADA) existe E pedido_id=2
  - AssaiNfQpa(id=7, numero='1737') existe E separacao_id=10

ACOES (em ordem, dentro de UMA transacao):
  1. NF 7: separacao_id=NULL, status_match='NAO_RECONCILIADO'
  2. AssaiNfQpaItem(nf_id=7): separacao_item_id=NULL,
     tipo_divergencia='CHASSI_SEM_SEPARACAO'
  3. Para cada chassi da sep 10: emitir EVENTO_DISPONIVEL com motivo
     'cleanup_placeholder_2026_05_17' (chassis voltam de FATURADA -> DISPONIVEL)
  4. DELETE assai_separacao_item WHERE separacao_id=10 (cascade da sep)
  5. DELETE assai_separacao WHERE id=10
  6. DELETE assai_pedido_venda_loja WHERE id=4148 (loja_id=11 pedido_id=2)
  7. DELETE assai_pedido_venda WHERE id=2

ESTADO FINAL:
  - NF 7 = NAO_RECONCILIADO com 3 items CHASSI_SEM_SEPARACAO
  - 3 chassis = DISPONIVEL (status_efetivo)
  - 0 referencias ao placeholder BACKFILL-2026-05-17 no banco
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


logger = logging.getLogger('cleanup_placeholder_nf7')

# IDs especificos descobertos via auditoria 2026-05-17 (estado atual em PROD).
# Se algum nao bater, abort — alguma outra mudanca aconteceu desde a auditoria.
PEDIDO_PLACEHOLDER_ID = 2
PEDIDO_PLACEHOLDER_NUMERO = 'BACKFILL-2026-05-17'
PVL_PLACEHOLDER_ID = 4148
SEP_PLACEHOLDER_ID = 10
SEP_LOJA_ID = 11
NF_ORFA_ID = 7
NF_NUMERO_ESPERADO = '1737'

MOTIVO_DISPONIVEL = 'cleanup_placeholder_2026_05_17'


def _validar_precondicoes() -> dict:
    """Retorna dict com 'ok' bool + 'detalhes' lista. Side-effect-free."""
    from app.motos_assai.models import (
        AssaiPedidoVenda, AssaiPedidoVendaLoja, AssaiSeparacao,
        AssaiSeparacaoItem, AssaiNfQpa, AssaiNfQpaItem,
        SEPARACAO_STATUS_FATURADA,
    )

    detalhes: list[str] = []
    ok = True

    pedido = AssaiPedidoVenda.query.get(PEDIDO_PLACEHOLDER_ID)
    if not pedido:
        detalhes.append(f'pedido id={PEDIDO_PLACEHOLDER_ID} NAO existe — '
                        'cleanup ja rodou (NO-OP)')
        return {'ok': False, 'noop': True, 'detalhes': detalhes}

    if pedido.numero != PEDIDO_PLACEHOLDER_NUMERO:
        detalhes.append(f'pedido id={PEDIDO_PLACEHOLDER_ID} tem numero '
                        f'{pedido.numero!r}, esperado {PEDIDO_PLACEHOLDER_NUMERO!r} — ABORT')
        ok = False

    pvl = AssaiPedidoVendaLoja.query.get(PVL_PLACEHOLDER_ID)
    if not pvl or pvl.pedido_id != PEDIDO_PLACEHOLDER_ID or pvl.loja_id != SEP_LOJA_ID:
        detalhes.append(f'PVL id={PVL_PLACEHOLDER_ID} inconsistente — ABORT')
        ok = False

    sep = AssaiSeparacao.query.get(SEP_PLACEHOLDER_ID)
    if not sep or sep.pedido_id != PEDIDO_PLACEHOLDER_ID or sep.loja_id != SEP_LOJA_ID:
        detalhes.append(f'sep id={SEP_PLACEHOLDER_ID} inconsistente — ABORT')
        ok = False
    elif sep.status != SEPARACAO_STATUS_FATURADA:
        detalhes.append(f'sep id={SEP_PLACEHOLDER_ID} status={sep.status} '
                        f'(esperado FATURADA) — pode ter sido alterada manualmente, ABORT')
        ok = False

    nf = AssaiNfQpa.query.get(NF_ORFA_ID)
    if not nf or nf.numero != NF_NUMERO_ESPERADO or nf.separacao_id != SEP_PLACEHOLDER_ID:
        detalhes.append(f'NF id={NF_ORFA_ID} inconsistente — ABORT')
        ok = False

    # Sep nao pode ter OUTRA NF apontando (so a NF 7)
    outras = (
        AssaiNfQpa.query
        .filter(AssaiNfQpa.separacao_id == SEP_PLACEHOLDER_ID,
                AssaiNfQpa.id != NF_ORFA_ID)
        .all()
    )
    if outras:
        detalhes.append(
            f'sep {SEP_PLACEHOLDER_ID} tem {len(outras)} OUTRA(S) NF(s) '
            f'apontando ({[n.id for n in outras]}) — ABORT'
        )
        ok = False

    # Sep nao pode ter mais que 3 itens (esperado: 3 chassis)
    n_items = AssaiSeparacaoItem.query.filter_by(
        separacao_id=SEP_PLACEHOLDER_ID
    ).count()
    if n_items != 3:
        detalhes.append(f'sep {SEP_PLACEHOLDER_ID} tem {n_items} items '
                        '(esperado 3) — ABORT')
        ok = False

    # NF nao pode ter mais que 3 items
    n_nf_items = AssaiNfQpaItem.query.filter_by(nf_id=NF_ORFA_ID).count()
    if n_nf_items != 3:
        detalhes.append(f'NF {NF_ORFA_ID} tem {n_nf_items} items '
                        '(esperado 3) — ABORT')
        ok = False

    detalhes.append(f'pedido={pedido.id}/{pedido.numero}, PVL={pvl.id}, '
                    f'sep={sep.id}/{sep.status}, NF={nf.id}/{nf.numero}/'
                    f'{nf.status_match}, items_sep={n_items}, items_nf={n_nf_items}')
    return {'ok': ok, 'noop': False, 'detalhes': detalhes}


def _aplicar_cleanup(dry_run: bool) -> dict:
    """Executa as 7 acoes em ordem. Se dry_run=True, NAO commita."""
    from app.motos_assai.models import (
        AssaiPedidoVenda, AssaiPedidoVendaLoja, AssaiSeparacao,
        AssaiSeparacaoItem, AssaiNfQpa, AssaiNfQpaItem,
        NF_STATUS_NAO_RECONCILIADO, EVENTO_DISPONIVEL,
        DIVERGENCIA_TIPO_CHASSI_SEM_SEPARACAO,
    )
    from app.motos_assai.services.moto_evento_service import emitir_evento

    result = {'acoes': [], 'dry_run': dry_run}

    # 1. NF: separacao_id=NULL + status_match=NAO_RECONCILIADO
    nf = AssaiNfQpa.query.get(NF_ORFA_ID)
    nf.separacao_id = None
    nf.status_match = NF_STATUS_NAO_RECONCILIADO
    result['acoes'].append(f'NF {NF_ORFA_ID}: separacao_id=NULL, status=NAO_RECONCILIADO')

    # 2. Items da NF: separacao_item_id=NULL + tipo_divergencia=CHASSI_SEM_SEPARACAO
    items_nf = AssaiNfQpaItem.query.filter_by(nf_id=NF_ORFA_ID).all()
    for it in items_nf:
        it.separacao_item_id = None
        it.tipo_divergencia = DIVERGENCIA_TIPO_CHASSI_SEM_SEPARACAO
    result['acoes'].append(
        f'{len(items_nf)} items_nf: separacao_item_id=NULL, tipo=CHASSI_SEM_SEPARACAO'
    )

    # 3. Eventos DISPONIVEL para cada chassi da sep (revertendo FATURADA)
    items_sep = AssaiSeparacaoItem.query.filter_by(
        separacao_id=SEP_PLACEHOLDER_ID,
    ).all()
    chassis = [it.chassi for it in items_sep]
    operador_id = _get_admin_id()
    for chassi in chassis:
        emitir_evento(
            chassi, EVENTO_DISPONIVEL,
            operador_id=operador_id,
            observacao=MOTIVO_DISPONIVEL,
            dados_extras={
                'origem': MOTIVO_DISPONIVEL,
                'sep_removida_id': SEP_PLACEHOLDER_ID,
                'pedido_placeholder_removido': PEDIDO_PLACEHOLDER_ID,
                'nf_orfa_id': NF_ORFA_ID,
            },
        )
    result['acoes'].append(
        f'{len(chassis)} EVENTO_DISPONIVEL emitidos (chassis: {chassis})'
    )

    # 4 + 5. DELETE itens + DELETE sep (cascade via relationship)
    sep = AssaiSeparacao.query.get(SEP_PLACEHOLDER_ID)
    db.session.delete(sep)
    db.session.flush()
    result['acoes'].append(
        f'DELETE sep id={SEP_PLACEHOLDER_ID} (cascade {len(items_sep)} items)'
    )

    # 6. DELETE PVL
    pvl = AssaiPedidoVendaLoja.query.get(PVL_PLACEHOLDER_ID)
    db.session.delete(pvl)
    db.session.flush()
    result['acoes'].append(f'DELETE PVL id={PVL_PLACEHOLDER_ID}')

    # 7. DELETE pedido placeholder
    pedido = AssaiPedidoVenda.query.get(PEDIDO_PLACEHOLDER_ID)
    db.session.delete(pedido)
    db.session.flush()
    result['acoes'].append(
        f'DELETE pedido id={PEDIDO_PLACEHOLDER_ID} ({PEDIDO_PLACEHOLDER_NUMERO})'
    )

    if dry_run:
        db.session.rollback()
        result['acoes'].append('--dry-run: ROLLBACK (nenhuma mudanca aplicada)')
    else:
        db.session.commit()
        result['acoes'].append('COMMIT — cleanup aplicado em PROD')

    return result


def _get_admin_id() -> int:
    """Retorna id=1 (Rafael) como fallback. Eventos sao auditaveis por dados_extras."""
    from app.auth.models import Usuario
    admin = Usuario.query.filter_by(perfil='administrador').first()
    return admin.id if admin else 1


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--dry-run', action='store_true',
                       help='Simula sem commit (RECOMENDADO 1a execucao)')
    group.add_argument('--apply', action='store_true',
                       help='Aplica em PROD (commit real)')
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    )

    app = create_app()
    with app.app_context():
        logger.info('=== cleanup_placeholder_nf7_orfa ===')

        precond = _validar_precondicoes()
        for d in precond['detalhes']:
            logger.info('[precond] %s', d)

        if precond.get('noop'):
            logger.info('NO-OP: cleanup ja foi aplicado anteriormente.')
            return 0

        if not precond['ok']:
            logger.error(
                'Precondicoes NAO atendidas — abortando para evitar mudanca '
                'em estado diferente do esperado. Investigue antes de re-rodar.'
            )
            return 1

        result = _aplicar_cleanup(dry_run=args.dry_run)
        for acao in result['acoes']:
            logger.info('[acao] %s', acao)

        if args.dry_run:
            logger.info('DRY-RUN concluido. Para aplicar: --apply')
        else:
            logger.info('CLEANUP APLICADO. Estado final:')
            logger.info('  - NF 7 = NAO_RECONCILIADO (orfa, aguardando pedido VOE real)')
            logger.info('  - 3 chassis = DISPONIVEL (status_efetivo)')
            logger.info('  - placeholder BACKFILL-2026-05-17 REMOVIDO')

        return 0


if __name__ == '__main__':
    sys.exit(main())
