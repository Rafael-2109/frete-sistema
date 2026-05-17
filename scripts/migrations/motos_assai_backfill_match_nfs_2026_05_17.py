#!/usr/bin/env python3
"""Backfill match NFs Q.P.A. — motos_assai (2026-05-17).

Resolve as 189+ divergencias acumuladas em 44 NFs Q.P.A. importadas em
2026-05-12..2026-05-17 com 3 causas raiz:

  1. loja_id=NULL nas 14 NFs de 17/05 — regex "LJ\\d+" falhou porque o
     destinatario_nome veio como "SENDAS DISTRIBUIDORA S/A" (sem o numero
     da loja). Corrigido em PROD pelo commit 848b992a (match por CNPJ).
     Este script aplica o mesmo match retroativamente.

  2. Separacoes Q.P.A. originais eram apenas de teste. Backfill cria
     1 AssaiSeparacao sintetica por NF (espelho 1:1), com status FATURADA
     direto, vincula NF e emite eventos SEPARADA+FATURADA por chassi.

  3. Chassis aguardando conferencia em Recibo 4 (X11-MINI, parado em
     2026-05-09 com 5/107 conferidos) ou ainda nao declarados pela
     Motochefe (13 DOT-2026). Script SKIPa NF cujos chassis ainda nao
     viraram AssaiMoto — proximo deploy retoma quando Rafael finalizar
     conferencias / Motochefe declarar compra.

PARTES (idempotentes, sempre rodam):
  parte1 — UPDATE retroativo de loja_id via CNPJ destinatario
  parte2 — DELETE de 2 AssaiMoto de teste com chassi de 4 digitos
           (id=1 chassi='2622', id=5 chassi='2465'). Soft-delete (ativo=False)
           dos AssaiReciboItem correspondentes para retira-los do fluxo de
           conferencia (mantem audit trail).
  parte3 — Cria separacao sintetica FATURADA por NF, espelho 1:1,
           quando TODOS os chassis ja existem em assai_moto.
  parte4 — Finaliza recibos pendentes (status EM_CONFERENCIA ou
           RECEBIDO_AGUARDANDO_CONFERENCIA). Para cada item nao conferido:
           valida regex_chassi contra modelo, cria AssaiMoto, emite
           EVENTO_ESTOQUE, marca conferido=True. Apos processar todos,
           se zero pendentes, recibo vai para CONCLUIDO. Resolve o Recibo 4
           (X11-MINI, parado em 2026-05-09 com 5/107 conferidos).

Idempotencia:
  - parte1: query filtra loja_id IS NULL — re-rodar e no-op.
  - parte2: filter_by(id=X, chassi=Y) — registro especifico, re-rodar e no-op.
  - parte3: SKIP NFs com status_match='BATEU' — re-rodar processa apenas
    NFs que mudaram (chassi novo cadastrado, etc).
  - parte4: filtra items com conferido=False ativo=True — re-rodar e no-op
    apos primeira execucao bem-sucedida.

Auto-cicatrizante:
  Conforme operadores finalizam recibos Motochefe pendentes, mais chassis
  ficam disponiveis. Proximo deploy o script processa as NFs aptas.

Roda em build.sh — proxima linha apos Migration 29.

Uso manual:
    python scripts/migrations/motos_assai_backfill_match_nfs_2026_05_17.py
    python scripts/migrations/motos_assai_backfill_match_nfs_2026_05_17.py --dry-run
    python scripts/migrations/motos_assai_backfill_match_nfs_2026_05_17.py --nf-id 38
    python scripts/migrations/motos_assai_backfill_match_nfs_2026_05_17.py --skip-parte2
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from decimal import Decimal

# sys.path para imports app.* funcionarem em Render Shell e CLI local
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)

from app import create_app, db  # noqa: E402
from app.utils.cnpj_utils import normalizar_cnpj  # noqa: E402
from app.utils.timezone import agora_brasil_naive  # noqa: E402


SCRIPT_VERSION = '2026-05-17-v1.1'
MOTIVO = 'BACKFILL_2026_05_17'
PEDIDO_PLACEHOLDER_NUMERO = 'BACKFILL-2026-05-17'

CHASSIS_LIXO_PARA_REMOVER = [
    (1, '2622'),
    (5, '2465'),
]


logger = logging.getLogger('backfill_match_nfs')


# ─── parte1 — UPDATE retroativo de loja_id ────────────────────────────────────

def parte1_update_loja_id() -> int:
    """Resolve loja_id via CNPJ destinatario para NFs antigas com loja_id NULL."""
    from app.motos_assai.models import AssaiNfQpa, AssaiLoja

    nfs_sem_loja = (
        AssaiNfQpa.query
        .filter(
            AssaiNfQpa.loja_id.is_(None),
            AssaiNfQpa.destinatario_cnpj.isnot(None),
        )
        .all()
    )

    if not nfs_sem_loja:
        logger.info('[parte1] no-op — nenhuma NF com loja_id NULL e CNPJ presente.')
        return 0

    todas_lojas = AssaiLoja.query.filter_by(ativo=True).all()
    cnpj_to_loja: dict[str, list] = {}
    for ll in todas_lojas:
        cnpj_norm = normalizar_cnpj(ll.cnpj)
        if cnpj_norm:
            cnpj_to_loja.setdefault(cnpj_norm, []).append(ll)

    atualizadas = 0
    ambiguas = 0
    sem_match = 0
    for nf in nfs_sem_loja:
        cnpj_norm = normalizar_cnpj(nf.destinatario_cnpj or '')
        if not cnpj_norm:
            sem_match += 1
            continue
        candidatas = cnpj_to_loja.get(cnpj_norm, [])
        if len(candidatas) == 1:
            nf.loja_id = candidatas[0].id
            atualizadas += 1
            logger.info(
                '[parte1] NF %s (chave=%s...) → loja_id=%s',
                nf.id, nf.chave_44[:8], candidatas[0].id,
            )
        elif len(candidatas) > 1:
            ambiguas += 1
            logger.warning(
                '[parte1] NF %s CNPJ %s ambiguo (%d lojas: %s) — SKIP',
                nf.id, nf.destinatario_cnpj, len(candidatas),
                [ll.id for ll in candidatas],
            )
        else:
            sem_match += 1

    if atualizadas:
        db.session.commit()
        logger.info(
            '[parte1] commit: %d atualizadas, %d ambiguas, %d sem match',
            atualizadas, ambiguas, sem_match,
        )

    return atualizadas


# ─── parte2 — DELETE chassis lixo ─────────────────────────────────────────────

def parte2_delete_chassis_lixo() -> int:
    """Remove 2 AssaiMoto de teste com chassi de 4 digitos + soft-delete recibo items."""
    from app.motos_assai.models import (
        AssaiMoto, AssaiMotoEvento, AssaiReciboItem,
    )

    removidos = 0
    for moto_id, chassi_esperado in CHASSIS_LIXO_PARA_REMOVER:
        moto = AssaiMoto.query.filter_by(
            id=moto_id, chassi=chassi_esperado,
        ).first()
        if not moto:
            logger.info(
                '[parte2] no-op — AssaiMoto id=%s chassi=%r ja removida.',
                moto_id, chassi_esperado,
            )
            continue

        eventos_apagados = AssaiMotoEvento.query.filter_by(
            chassi=chassi_esperado,
        ).delete(synchronize_session=False)

        # Soft-delete dos AssaiReciboItem desse chassi (mantem audit trail).
        # Sem isso, parte4 tentaria re-conferir um chassi invalido (4 digitos)
        # que nao bate regex algum -> ficaria em loop pendente.
        # tipo_divergencia eh VARCHAR(30) — string precisa caber.
        recibo_items_soft = AssaiReciboItem.query.filter_by(
            chassi=chassi_esperado,
        ).update(
            {
                'ativo': False,
                'tipo_divergencia': 'LIMPO_BACKFILL_2026_05_17',  # 25 chars
            },
            synchronize_session=False,
        )

        db.session.delete(moto)
        removidos += 1
        logger.info(
            '[parte2] removida AssaiMoto id=%s chassi=%r '
            '(%d eventos apagados, %d recibo_items soft-deleted)',
            moto_id, chassi_esperado, eventos_apagados, recibo_items_soft,
        )

    if removidos:
        db.session.commit()
        logger.info('[parte2] commit: %d AssaiMoto removidas', removidos)

    return removidos


# ─── parte4 — finalizar recibos pendentes ─────────────────────────────────────

def parte4_finalizar_recibos_pendentes() -> dict:
    """Conclui conferencia de recibos abandonados (Recibo 4 principalmente).

    Para cada AssaiReciboItem em recibo status EM_CONFERENCIA ou
    RECEBIDO_AGUARDANDO_CONFERENCIA, com conferido=False ativo=True:
      - Valida chassi contra regex do modelo_id do item
      - Se OK: cria AssaiMoto (se nao existir), emite EVENTO_ESTOQUE,
              marca conferido=True
      - Se falha regex: log warning + SKIP (mantem ativo=True)

    Apos processar todos os items de cada recibo, se zero pendentes,
    atualiza status para CONCLUIDO.
    """
    from app.motos_assai.models import (
        AssaiReciboMotochefe, AssaiReciboItem, AssaiMoto,
        RECIBO_STATUS_AGUARDANDO, RECIBO_STATUS_EM_CONFERENCIA,
        RECIBO_STATUS_CONCLUIDO, RECIBO_STATUS_COM_DIVERGENCIA,
        EVENTO_ESTOQUE,
    )
    from app.motos_assai.services.chassi_validator import validar_chassi
    from app.motos_assai.services.moto_evento_service import emitir_evento

    operador_id = _get_admin_id()
    stats = {
        'recibos_processados': 0,
        'items_conferidos': 0,
        'items_skip_regex': 0,
        'items_skip_sem_modelo': 0,
        'recibos_concluidos': 0,
        'erro': 0,
    }

    recibos_pendentes = (
        AssaiReciboMotochefe.query
        .filter(AssaiReciboMotochefe.status.in_([
            RECIBO_STATUS_AGUARDANDO,
            RECIBO_STATUS_EM_CONFERENCIA,
        ]))
        .order_by(AssaiReciboMotochefe.id.asc())
        .all()
    )

    if not recibos_pendentes:
        logger.info('[parte4] no-op — nenhum recibo pendente de conferencia.')
        return stats

    logger.info(
        '[parte4] %d recibo(s) pendentes: %s',
        len(recibos_pendentes), [r.id for r in recibos_pendentes],
    )

    for recibo in recibos_pendentes:
        try:
            items_pendentes = (
                AssaiReciboItem.query
                .filter_by(recibo_id=recibo.id, conferido=False, ativo=True)
                .order_by(AssaiReciboItem.id.asc())
                .all()
            )

            if not items_pendentes:
                logger.info(
                    '[parte4] recibo %s ja sem items pendentes — verificando status final',
                    recibo.id,
                )
            else:
                logger.info(
                    '[parte4] recibo %s: %d items pendentes para processar',
                    recibo.id, len(items_pendentes),
                )

            conferidos_neste_recibo = 0
            for item in items_pendentes:
                if not item.modelo_id:
                    logger.warning(
                        '[parte4] SKIP item %s (recibo %s) chassi=%r — modelo_id NULL',
                        item.id, recibo.id, item.chassi,
                    )
                    stats['items_skip_sem_modelo'] += 1
                    continue

                resultado = validar_chassi(item.chassi, item.modelo_id)
                if not resultado['ok']:
                    logger.warning(
                        '[parte4] SKIP item %s (recibo %s) chassi=%r — %s',
                        item.id, recibo.id, item.chassi, resultado['mensagem'],
                    )
                    stats['items_skip_regex'] += 1
                    continue

                moto_existente = AssaiMoto.query.filter_by(
                    chassi=item.chassi,
                ).first()
                if not moto_existente:
                    nova_moto = AssaiMoto(
                        chassi=item.chassi,
                        modelo_id=item.modelo_id,
                        cor=item.cor_texto,
                        motor=item.motor,
                    )
                    db.session.add(nova_moto)
                    db.session.flush()

                emitir_evento(
                    item.chassi, EVENTO_ESTOQUE,
                    operador_id=operador_id,
                    observacao=f'{MOTIVO} recibo {recibo.id}',
                    dados_extras={
                        'origem': MOTIVO,
                        'recibo_id': recibo.id,
                        'item_id': item.id,
                        'script_version': SCRIPT_VERSION,
                    },
                )

                item.conferido = True
                conferidos_neste_recibo += 1

            if conferidos_neste_recibo:
                stats['items_conferidos'] += conferidos_neste_recibo
                logger.info(
                    '[parte4] recibo %s: %d items conferidos via backfill',
                    recibo.id, conferidos_neste_recibo,
                )

            ainda_pendentes = (
                AssaiReciboItem.query
                .filter_by(recibo_id=recibo.id, conferido=False, ativo=True)
                .count()
            )
            if ainda_pendentes == 0:
                com_divergencia = (
                    AssaiReciboItem.query
                    .filter_by(recibo_id=recibo.id, ativo=True)
                    .filter(AssaiReciboItem.tipo_divergencia.isnot(None))
                    .count()
                )
                recibo.status = (
                    RECIBO_STATUS_COM_DIVERGENCIA
                    if com_divergencia else RECIBO_STATUS_CONCLUIDO
                )
                stats['recibos_concluidos'] += 1
                logger.info(
                    '[parte4] recibo %s → %s (zero pendentes, %d com divergencia)',
                    recibo.id, recibo.status, com_divergencia,
                )
            else:
                logger.info(
                    '[parte4] recibo %s mantem EM_CONFERENCIA — %d items ainda pendentes (regex falhou)',
                    recibo.id, ainda_pendentes,
                )

            db.session.commit()
            stats['recibos_processados'] += 1

        except Exception as e:
            db.session.rollback()
            logger.error(
                '[parte4] ERRO recibo %s: %s %s',
                recibo.id, type(e).__name__, e,
            )
            stats['erro'] += 1

    return stats


# ─── parte3 — separacoes sinteticas ───────────────────────────────────────────

def parte3_criar_separacoes_sinteticas(
    dry_run: bool = False, nf_id: int | None = None,
) -> dict:
    """Cria separacao sintetica FATURADA por NF (espelho 1:1)."""
    from app.motos_assai.models import (
        AssaiNfQpa, AssaiMoto, AssaiSeparacao, AssaiSeparacaoItem,
        NF_STATUS_BATEU, SEPARACAO_STATUS_FATURADA, SEPARACAO_STATUS_CANCELADA,
        EVENTO_SEPARADA, EVENTO_FATURADA,
    )
    from app.motos_assai.services.moto_evento_service import emitir_evento

    stats = {
        'ok': 0,
        'skip_loja_null': 0,
        'skip_sem_itens': 0,
        'skip_chassi_faltante': 0,
        'skip_chassi_em_outra_sep': 0,
        'erro': 0,
    }

    operador_id = _get_admin_id()

    q = AssaiNfQpa.query.filter(AssaiNfQpa.status_match != NF_STATUS_BATEU)
    if nf_id:
        q = q.filter(AssaiNfQpa.id == nf_id)

    nfs = q.order_by(
        AssaiNfQpa.data_emissao.asc(), AssaiNfQpa.id.asc(),
    ).all()

    if not nfs:
        logger.info('[parte3] no-op — nenhuma NF com status != BATEU.')
        return stats

    logger.info('[parte3] processando %d NF(s)%s', len(nfs),
                ' (DRY-RUN)' if dry_run else '')

    for nf in nfs:
        try:
            if not nf.loja_id:
                logger.info(
                    '[parte3] SKIP_LOJA_NULL: NF %s sem loja_id (CNPJ %s)',
                    nf.id, nf.destinatario_cnpj,
                )
                stats['skip_loja_null'] += 1
                continue

            chassis = [it.chassi for it in nf.itens]
            if not chassis:
                logger.warning(
                    '[parte3] SKIP_SEM_ITENS: NF %s sem itens (artefato de teste/rollback?)',
                    nf.id,
                )
                stats['skip_sem_itens'] += 1
                continue

            existentes = {
                m.chassi for m in
                AssaiMoto.query.filter(AssaiMoto.chassi.in_(chassis)).all()
            }
            faltantes = [c for c in chassis if c not in existentes]
            if faltantes:
                logger.info(
                    '[parte3] SKIP_CHASSI_FALTANTE: NF %s tem %d/%d chassis '
                    'fora de assai_moto (ex: %s)',
                    nf.id, len(faltantes), len(chassis), faltantes[:3],
                )
                stats['skip_chassi_faltante'] += 1
                continue

            conflitos = (
                AssaiSeparacaoItem.query
                .filter(AssaiSeparacaoItem.chassi.in_(chassis))
                .join(AssaiSeparacao,
                      AssaiSeparacao.id == AssaiSeparacaoItem.separacao_id)
                .filter(AssaiSeparacao.status.notin_([
                    SEPARACAO_STATUS_CANCELADA,
                ]))
                .all()
            )
            if conflitos:
                chassis_conflito = [c.chassi for c in conflitos]
                logger.warning(
                    '[parte3] SKIP_CHASSI_EM_OUTRA_SEP: NF %s tem %d chassi(s) '
                    'ja em outra sep nao-CANCELADA (ex: %s) — operador resolve manualmente',
                    nf.id, len(chassis_conflito), chassis_conflito[:3],
                )
                stats['skip_chassi_em_outra_sep'] += 1
                continue

            if dry_run:
                logger.info(
                    '[parte3 DRY-RUN] NF %s → sep sintetica, %d chassis, loja=%s',
                    nf.id, len(chassis), nf.loja_id,
                )
                stats['ok'] += 1
                continue

            pedido_id = _resolver_pedido_para_loja(nf.loja_id, operador_id)

            sep = AssaiSeparacao(
                pedido_id=pedido_id,
                loja_id=nf.loja_id,
                status=SEPARACAO_STATUS_FATURADA,
                fechada_por_id=operador_id,
                fechada_em=agora_brasil_naive(),
            )
            db.session.add(sep)
            db.session.flush()

            moto_por_chassi = {
                m.chassi: m for m in
                AssaiMoto.query.filter(AssaiMoto.chassi.in_(chassis)).all()
            }
            for it_nf in nf.itens:
                moto = moto_por_chassi.get(it_nf.chassi)
                if not moto:
                    raise RuntimeError(
                        f'inconsistencia: chassi {it_nf.chassi!r} sumiu '
                        'entre validacao e criacao'
                    )
                sep_item = AssaiSeparacaoItem(
                    separacao_id=sep.id,
                    chassi=it_nf.chassi,
                    modelo_id=moto.modelo_id,
                    valor_unitario_qpa=(it_nf.valor_extraido or Decimal('0')),
                    registrada_por_id=operador_id,
                )
                db.session.add(sep_item)
                db.session.flush()

                it_nf.separacao_item_id = sep_item.id
                it_nf.tipo_divergencia = None

                _dados = {
                    'origem': MOTIVO,
                    'nf_id': nf.id,
                    'sep_id': sep.id,
                    'script_version': SCRIPT_VERSION,
                }
                emitir_evento(it_nf.chassi, EVENTO_SEPARADA, operador_id,
                              observacao=f'{MOTIVO} NF {nf.id}',
                              dados_extras=_dados)
                emitir_evento(it_nf.chassi, EVENTO_FATURADA, operador_id,
                              observacao=f'{MOTIVO} NF {nf.id}',
                              dados_extras=_dados)

            nf.separacao_id = sep.id
            nf.status_match = NF_STATUS_BATEU

            divs_resolvidas = _resolver_divergencias_da_nf(nf.id, operador_id)

            db.session.commit()
            logger.info(
                '[parte3] OK: NF %s → sep %s FATURADA, %d chassis, %d divergencias resolvidas',
                nf.id, sep.id, len(chassis), divs_resolvidas,
            )
            stats['ok'] += 1

        except Exception as e:
            db.session.rollback()
            logger.error(
                '[parte3] ERRO NF %s: %s %s',
                nf.id, type(e).__name__, e,
            )
            stats['erro'] += 1

    return stats


# ─── helpers ──────────────────────────────────────────────────────────────────

def _resolver_pedido_para_loja(loja_id: int, operador_id: int) -> int:
    """Pedido REAL onde existir AssaiPedidoVendaLoja(loja_id), placeholder se nao."""
    from app.motos_assai.models import (
        AssaiPedidoVenda, AssaiPedidoVendaLoja, PEDIDO_STATUS_ABERTO,
    )

    pvl = (
        AssaiPedidoVendaLoja.query
        .filter_by(loja_id=loja_id)
        .order_by(AssaiPedidoVendaLoja.id.desc())
        .first()
    )
    if pvl:
        return pvl.pedido_id

    placeholder = AssaiPedidoVenda.query.filter_by(
        numero=PEDIDO_PLACEHOLDER_NUMERO,
    ).first()
    if not placeholder:
        placeholder = AssaiPedidoVenda(
            numero=PEDIDO_PLACEHOLDER_NUMERO,
            status=PEDIDO_STATUS_ABERTO,
            criado_por_id=operador_id,
        )
        db.session.add(placeholder)
        db.session.flush()
        logger.info('[helper] pedido placeholder criado id=%s', placeholder.id)

    pvl_placeholder = AssaiPedidoVendaLoja.query.filter_by(
        pedido_id=placeholder.id, loja_id=loja_id,
    ).first()
    if not pvl_placeholder:
        pvl_placeholder = AssaiPedidoVendaLoja(
            pedido_id=placeholder.id,
            loja_id=loja_id,
        )
        db.session.add(pvl_placeholder)
        db.session.flush()

    return placeholder.id


def _resolver_divergencias_da_nf(nf_id: int, operador_id: int) -> int:
    """Marca divergencias abertas da NF como resolvidas via backfill."""
    try:
        from app.motos_assai.models import (
            AssaiDivergencia, DIVERGENCIA_RESOLUCAO_IGNORAR,
        )
    except ImportError:
        return 0

    divergencias = (
        AssaiDivergencia.query
        .filter_by(nf_id=nf_id)
        .filter(AssaiDivergencia.resolvida_em.is_(None))
        .all()
    )
    if not divergencias:
        return 0

    for div in divergencias:
        div.resolvida_em = agora_brasil_naive()
        div.resolvida_por_id = operador_id
        div.tipo_resolucao = DIVERGENCIA_RESOLUCAO_IGNORAR
        div.observacao_resolucao = (
            f'{MOTIVO}: separacao sintetica criada via backfill '
            f'(script {SCRIPT_VERSION})'
        )

    return len(divergencias)


def _get_admin_id() -> int:
    """Primeiro Usuario com perfil=administrador, fallback id=1."""
    from app.auth.models import Usuario
    admin = Usuario.query.filter_by(perfil='administrador').first()
    return admin.id if admin else 1


# ─── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--dry-run', action='store_true',
        help='Simula sem commit (parte3 apenas — parte1/parte2 sao no-op se ja rodou).',
    )
    parser.add_argument(
        '--nf-id', type=int,
        help='Processa apenas uma NF especifica (debug).',
    )
    parser.add_argument(
        '--skip-parte1', action='store_true',
        help='Pula UPDATE retroativo de loja_id.',
    )
    parser.add_argument(
        '--skip-parte2', action='store_true',
        help='Pula DELETE de chassis lixo.',
    )
    parser.add_argument(
        '--skip-parte3', action='store_true',
        help='Pula criar separacoes sinteticas.',
    )
    parser.add_argument(
        '--skip-parte4', action='store_true',
        help='Pula finalizar recibos pendentes.',
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s %(levelname)s [%(name)s] %(message)s',
    )

    app = create_app()
    with app.app_context():
        logger.info('=== motos_assai backfill match NFs (%s) ===', SCRIPT_VERSION)

        # Isolamento por parte (2026-05-17 v1.1 fix): cada parte tem try/except
        # proprio para que falha em uma NAO interrompa as demais. O auto-deploy
        # do Render captura erro do script inteiro com `|| echo ...` no build.sh,
        # mas isso e granularidade boa demais — perdemos parte3/4 se parte2
        # explode. Isolamento aqui garante que cada parte tenta independente.
        if not args.skip_parte1:
            try:
                parte1_update_loja_id()
            except Exception:
                logger.exception('parte1 falhou — seguindo para proximas partes')
                db.session.rollback()

        if not args.skip_parte2:
            try:
                parte2_delete_chassis_lixo()
            except Exception:
                logger.exception('parte2 falhou — seguindo para proximas partes')
                db.session.rollback()

        # parte4 ANTES de parte3: finaliza recibos -> cadastra AssaiMoto
        # -> chassis das NFs ficam disponiveis para sep sintetica.
        if not args.skip_parte4 and not args.dry_run:
            try:
                stats_p4 = parte4_finalizar_recibos_pendentes()
                logger.info('[parte4 stats] %s', json.dumps(stats_p4))
            except Exception:
                logger.exception('parte4 falhou — seguindo para parte3')
                db.session.rollback()
        elif args.dry_run and not args.skip_parte4:
            logger.info('[parte4] SKIP em --dry-run (parte4 nao tem modo dry).')

        if not args.skip_parte3:
            try:
                stats = parte3_criar_separacoes_sinteticas(
                    dry_run=args.dry_run, nf_id=args.nf_id,
                )
                logger.info('[parte3 stats] %s', json.dumps(stats))
            except Exception:
                logger.exception('parte3 falhou')
                db.session.rollback()

        logger.info('=== backfill concluido ===')


if __name__ == '__main__':
    main()
