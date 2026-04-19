"""B3 (2026-04-18): Cancelamento em cascata de CarviaOperacao.

Quando operacao tem dependencias ativas (subs, CTe Comp, CE, Frete), o fluxo
atual exige N clicks manuais. Este service faz a operacao atomica:

  1. Snapshot de dependencias ativas (listar_dependencias_ativas)
  2. Operador confirma os que quer cancelar (UI modal)
  3. executar_cancelamento_cascata: cancela cada filho em ordem topologica
     + cancela a operacao, TUDO dentro da mesma transacao.

Bloqueios permanecem: fatura nao-CANCELADA, CarviaFrete CONFERIDO, CE PAGO.

Audit trail: cada cancelamento gera registro em CarviaAdminAudit (quando
disponivel) OU no log estruturado. Nao cria historico novo — reusa audit
existente.
"""

from __future__ import annotations

import logging
from typing import Dict, List

from app import db

logger = logging.getLogger(__name__)


def listar_dependencias_ativas(operacao_id: int) -> Dict:
    """Retorna inventario de dependencias ativas da operacao.

    Returns:
        dict com listas por tipo:
          - subcontratos: [{id, cte_numero, status, transportadora, bloqueado, motivo}]
          - ctes_complementares: [{id, numero_comp, cte_numero, status, bloqueado, motivo}]
          - custos_entrega: [{id, numero_custo, tipo_custo, status, bloqueado, motivo}]
          - carvia_fretes: [{id, status, bloqueado, motivo}]
    """
    from app.carvia.models import (
        CarviaOperacao, CarviaSubcontrato,
    )
    from app.carvia.models.cte_custos import (
        CarviaCteComplementar, CarviaCustoEntrega,
    )
    from app.carvia.models.frete import CarviaFrete

    op = db.session.get(CarviaOperacao, operacao_id)
    if not op:
        return {
            'operacao': None,
            'subcontratos': [],
            'ctes_complementares': [],
            'custos_entrega': [],
            'carvia_fretes': [],
        }

    subs = []
    for sub in op.subcontratos.filter(CarviaSubcontrato.status != 'CANCELADO').all():
        bloqueado = sub.status == 'FATURADO'
        motivo = (
            'Subcontrato FATURADO — desvincule da fatura primeiro'
            if bloqueado else None
        )
        subs.append({
            'id': sub.id,
            'cte_numero': sub.cte_numero,
            'status': sub.status,
            'transportadora_id': sub.transportadora_id,
            'bloqueado': bloqueado,
            'motivo': motivo,
        })

    comps = []
    for cc in op.ctes_complementares.filter(
        CarviaCteComplementar.status != 'CANCELADO'
    ).all():
        bloqueado = cc.status == 'FATURADO'
        motivo = (
            'CTe Complementar FATURADO — desvincule da fatura primeiro'
            if bloqueado else None
        )
        comps.append({
            'id': cc.id,
            'numero_comp': cc.numero_comp,
            'cte_numero': cc.cte_numero,
            'status': cc.status,
            'bloqueado': bloqueado,
            'motivo': motivo,
        })

    custos = []
    # Fallback gracioso se o model tem colunas nao aplicadas no DB
    # (divergencia model/schema — nao bloqueia outras dependencias).
    try:
        for ce in op.custos_entrega.filter(
            CarviaCustoEntrega.status != 'CANCELADO'
        ).all():
            bloqueado = ce.status == 'PAGO' or ce.fatura_transportadora_id is not None
            motivo = None
            if ce.status == 'PAGO':
                motivo = 'Custo Entrega PAGO — desconcilie FT primeiro'
            elif ce.fatura_transportadora_id is not None:
                motivo = 'Custo Entrega vinculado a FT — desvincule primeiro'
            custos.append({
                'id': ce.id,
                'numero_custo': ce.numero_custo,
                'tipo_custo': ce.tipo_custo,
                'status': ce.status,
                'bloqueado': bloqueado,
                'motivo': motivo,
            })
    except Exception as e_ce:
        logger.warning(
            'B3 listar: nao foi possivel carregar CustoEntrega para op=%s: %s',
            operacao_id, e_ce,
        )
        db.session.rollback()

    fretes = []
    try:
        for fr in CarviaFrete.query.filter(
            CarviaFrete.operacao_id == operacao_id,
            CarviaFrete.status != 'CANCELADO',
        ).all():
            status_conf = getattr(fr, 'status_conferencia', None)
            bloqueado = status_conf == 'CONFERIDO'
            motivo = (
                'CarviaFrete CONFERIDO — reabrir conferencia primeiro'
                if bloqueado else None
            )
            fretes.append({
                'id': fr.id,
                'status': fr.status,
                'status_conferencia': status_conf,
                'bloqueado': bloqueado,
                'motivo': motivo,
            })
    except Exception as e_fr:
        logger.warning(
            'B3 listar: nao foi possivel carregar CarviaFrete para op=%s: %s',
            operacao_id, e_fr,
        )
        db.session.rollback()

    return {
        'operacao': {
            'id': op.id,
            'cte_numero': op.cte_numero,
            'status': op.status,
            'fatura_cliente_id': op.fatura_cliente_id,
        },
        'subcontratos': subs,
        'ctes_complementares': comps,
        'custos_entrega': custos,
        'carvia_fretes': fretes,
    }


def executar_cancelamento_cascata(
    operacao_id: int,
    ids_a_cancelar: Dict[str, List[int]],
    usuario: str,
    motivo: str | None = None,
) -> Dict:
    """Cancela filhos selecionados + a operacao em UMA transacao.

    ids_a_cancelar: dict com chaves:
      - 'subcontratos': [ids]
      - 'ctes_complementares': [ids]
      - 'custos_entrega': [ids]
      - 'carvia_fretes': [ids]
      - 'cancelar_operacao': bool (se True, tenta cancelar a operacao ao final)

    Ordem topologica (filhos -> pai):
      1. CarviaFrete
      2. CarviaCustoEntrega
      3. CarviaCteComplementar
      4. CarviaSubcontrato
      5. CarviaOperacao (se cancelar_operacao=True)

    Returns:
        dict com status, cancelados, erros.
    """
    from app.carvia.models import (
        CarviaOperacao, CarviaSubcontrato,
    )
    from app.carvia.models.cte_custos import (
        CarviaCteComplementar, CarviaCustoEntrega,
    )
    from app.carvia.models.frete import CarviaFrete
    from app.utils.timezone import agora_utc_naive

    resultado = {
        'status': 'OK',
        'cancelados': {
            'subcontratos': [],
            'ctes_complementares': [],
            'custos_entrega': [],
            'carvia_fretes': [],
            'operacao': None,
        },
        'erros': [],
    }
    agora = agora_utc_naive()

    try:
        # Reserva a operacao com lock pessimista para evitar race
        op = (
            db.session.query(CarviaOperacao)
            .filter(CarviaOperacao.id == operacao_id)
            .with_for_update()
            .first()
        )
        if not op:
            return {
                'status': 'ERRO',
                'erros': ['operacao_nao_encontrada'],
                'cancelados': resultado['cancelados'],
            }

        # 1. CarviaFrete
        for fr_id in ids_a_cancelar.get('carvia_fretes') or []:
            fr = db.session.get(CarviaFrete, fr_id)
            if not fr or fr.operacao_id != operacao_id:
                resultado['erros'].append(f'frete_{fr_id}_nao_pertence_operacao')
                continue
            if fr.status == 'CANCELADO':
                continue
            if getattr(fr, 'status_conferencia', None) == 'CONFERIDO':
                resultado['erros'].append(
                    f'frete_{fr_id}_CONFERIDO_reabrir_primeiro'
                )
                continue
            fr.status = 'CANCELADO'
            if hasattr(fr, 'cancelado_em'):
                fr.cancelado_em = agora
            if hasattr(fr, 'cancelado_por'):
                fr.cancelado_por = usuario
            resultado['cancelados']['carvia_fretes'].append(fr_id)

        # 2. CarviaCustoEntrega
        for ce_id in ids_a_cancelar.get('custos_entrega') or []:
            ce = db.session.get(CarviaCustoEntrega, ce_id)
            if not ce or ce.operacao_id != operacao_id:
                resultado['erros'].append(f'ce_{ce_id}_nao_pertence_operacao')
                continue
            if ce.status == 'CANCELADO':
                continue
            if ce.status == 'PAGO':
                resultado['erros'].append(f'ce_{ce_id}_PAGO_desconciliar_primeiro')
                continue
            if ce.fatura_transportadora_id is not None:
                resultado['erros'].append(
                    f'ce_{ce_id}_vinculado_FT_desvincular_primeiro'
                )
                continue
            ce.status = 'CANCELADO'
            resultado['cancelados']['custos_entrega'].append(ce_id)

        # 3. CarviaCteComplementar
        for cc_id in ids_a_cancelar.get('ctes_complementares') or []:
            cc = db.session.get(CarviaCteComplementar, cc_id)
            if not cc or cc.operacao_id != operacao_id:
                resultado['erros'].append(f'cc_{cc_id}_nao_pertence_operacao')
                continue
            if cc.status == 'CANCELADO':
                continue
            if cc.status == 'FATURADO':
                resultado['erros'].append(
                    f'cc_{cc_id}_FATURADO_desvincular_primeiro'
                )
                continue
            cc.status = 'CANCELADO'
            resultado['cancelados']['ctes_complementares'].append(cc_id)

        # 4. CarviaSubcontrato
        for sub_id in ids_a_cancelar.get('subcontratos') or []:
            sub = db.session.get(CarviaSubcontrato, sub_id)
            if not sub or sub.operacao_id != operacao_id:
                resultado['erros'].append(f'sub_{sub_id}_nao_pertence_operacao')
                continue
            if sub.status == 'CANCELADO':
                continue
            if sub.status == 'FATURADO':
                resultado['erros'].append(
                    f'sub_{sub_id}_FATURADO_desvincular_primeiro'
                )
                continue
            sub.status = 'CANCELADO'
            if hasattr(sub, 'cancelado_em'):
                sub.cancelado_em = agora
            if hasattr(sub, 'cancelado_por'):
                sub.cancelado_por = usuario
            resultado['cancelados']['subcontratos'].append(sub_id)

        # 5. Operacao
        if ids_a_cancelar.get('cancelar_operacao'):
            pode, razao = op.pode_cancelar()
            if not pode:
                resultado['erros'].append(f'operacao_bloqueada: {razao}')
            else:
                op.status = 'CANCELADO'
                resultado['cancelados']['operacao'] = operacao_id

        # Commit atomico. Se nenhum item foi cancelado, status=NADA_CANCELADO
        # mas NAO faz rollback (pode haver mutacoes nao-cancel que o caller
        # quer preservar — ex: updates de status feitos antes).
        nenhum_cancelado = (
            not any(
                resultado['cancelados'][k]
                for k in resultado['cancelados']
                if k != 'operacao'
            )
            and resultado['cancelados']['operacao'] is None
        )
        if nenhum_cancelado and resultado['erros']:
            resultado['status'] = 'NADA_CANCELADO'
        else:
            resultado['status'] = 'OK' if not resultado['erros'] else 'PARCIAL'
        # Sempre commit — deixa eventuais mutacoes de status (ja aplicadas
        # acima) persistirem. Se apply_fn levantou excecao, ja caiu no
        # except externo com rollback.
        db.session.commit()

        logger.info(
            'B3 cascade op=%s usuario=%s motivo=%r cancelados=%s erros=%s',
            operacao_id, usuario, motivo,
            {k: len(v) if isinstance(v, list) else v
             for k, v in resultado['cancelados'].items()},
            resultado['erros'],
        )

        return resultado

    except Exception as e:
        db.session.rollback()
        logger.exception(
            'B3 cascade: erro inesperado op=%s: %s', operacao_id, e
        )
        return {
            'status': 'ERRO',
            'erros': [str(e)],
            'cancelados': resultado.get('cancelados', {}),
        }
