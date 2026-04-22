"""Matching entre pagamento de fatura (transacao CC) e fatura (PessoalImportacao).

Uma fatura de cartao de credito importada (PessoalImportacao com
tipo_arquivo='fatura_cartao' e situacao_fatura='PAGO') precisa ser vinculada
a transacao de CC que a pagou (eh_pagamento_cartao=True na CC).

Este servico oferece:
- sugerir_matches(): heuristica por valor + data + titular/membro
- vincular(): cria vinculo fatura.transacao_pagamento_id = tx.id
- desvincular(): remove vinculo
- backfill_historico(): processa todas as faturas PAGO sem vinculo

Heuristica de match:
    - Total da fatura (sum das compras) vs valor da transacao CC (tolerancia 1%)
    - Data da transacao CC no intervalo [periodo_fim, periodo_fim + 30 dias]
    - Mesmo membro (titular do cartao = titular da CC) OU qualquer CC do grupo
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import func

from app import db
from app.pessoal.models import (
    PessoalConta, PessoalImportacao, PessoalTransacao,
)

logger = logging.getLogger(__name__)


# =============================================================================
# HEURISTICAS
# =============================================================================
def _total_compras_fatura(importacao_id: int) -> float:
    """Soma do valor das transacoes (compras) da fatura."""
    total = db.session.query(
        func.coalesce(func.sum(PessoalTransacao.valor), 0)
    ).filter(
        PessoalTransacao.importacao_id == importacao_id,
    ).scalar() or 0
    return float(total)


def sugerir_matches(
    fatura_id: int,
    tolerancia_pct: float = 0.02,  # 2% (pagamento pode diferir por juros/correcao)
    janela_dias_min: int = 0,
    janela_dias_max: int = 40,
) -> list[dict]:
    """Sugere candidatos de transacao de pagamento para uma fatura.

    Retorna lista ordenada por score (menor diferenca de valor + menor dist dias).
    """
    fat = db.session.get(PessoalImportacao, fatura_id)
    if not fat:
        raise ValueError(f'Fatura id={fatura_id} nao encontrada')
    if fat.tipo_arquivo != 'fatura_cartao':
        raise ValueError(
            f'Importacao id={fatura_id} nao e fatura_cartao '
            f'(tipo={fat.tipo_arquivo})'
        )

    total_compras = _total_compras_fatura(fatura_id)
    if total_compras <= 0:
        logger.warning('fatura_id=%d sem compras, sem sugestoes', fatura_id)
        return []

    # Intervalo de busca: apos periodo_fim da fatura (quando fecha), geralmente
    # pagamento ocorre ate 30-40 dias depois.
    if not fat.periodo_fim:
        logger.warning('fatura_id=%d sem periodo_fim', fatura_id)
        return []

    data_min = fat.periodo_fim + timedelta(days=janela_dias_min)
    data_max = fat.periodo_fim + timedelta(days=janela_dias_max)

    # Titular do cartao (membro da PessoalConta da fatura)
    conta_cartao = db.session.get(PessoalConta, fat.conta_id)
    titular_id = conta_cartao.membro_id if conta_cartao else None

    # CCs do mesmo titular (ou todas CCs se nao sabemos titular)
    q_cc = db.session.query(PessoalConta.id).filter(
        PessoalConta.tipo == 'conta_corrente',
    )
    if titular_id:
        q_cc = q_cc.filter(
            (PessoalConta.membro_id == titular_id)
            | (PessoalConta.membro_id.is_(None))
        )
    cc_ids = [x[0] for x in q_cc.all()]
    if not cc_ids:
        return []

    # Candidatos: pagamentos de cartao em CC, no intervalo, valor proximo
    valor_min = total_compras * (1 - tolerancia_pct)
    valor_max_limit = total_compras * (1 + tolerancia_pct)

    candidatos = PessoalTransacao.query.filter(
        PessoalTransacao.eh_pagamento_cartao.is_(True),
        PessoalTransacao.tipo == 'debito',
        PessoalTransacao.conta_id.in_(cc_ids),
        PessoalTransacao.data >= data_min,
        PessoalTransacao.data <= data_max,
        PessoalTransacao.valor >= Decimal(str(valor_min)),
        PessoalTransacao.valor <= Decimal(str(valor_max_limit)),
    ).order_by(PessoalTransacao.data.asc()).all()

    # Exclui candidatos ja vinculados a OUTRAS faturas (bulk fetch em 1 query)
    if candidatos:
        ids_linked_outras = {
            row[0] for row in db.session.query(
                PessoalImportacao.transacao_pagamento_id,
            ).filter(
                PessoalImportacao.transacao_pagamento_id.in_(
                    [c.id for c in candidatos],
                ),
                PessoalImportacao.id != fatura_id,
            ).all()
        }
    else:
        ids_linked_outras = set()
    candidatos_livres = [c for c in candidatos if c.id not in ids_linked_outras]

    # Score: valor exato + menor distancia
    resultado = []
    for c in candidatos_livres:
        diff_valor = abs(float(c.valor) - total_compras)
        dist_dias = (c.data - fat.periodo_fim).days if fat.periodo_fim else 0
        # Menor diff + menor dist = maior score
        match_exato = 1000 if diff_valor < 0.01 else 0
        score = match_exato - diff_valor * 10 - dist_dias
        resultado.append({
            'transacao_id': c.id,
            'data': c.data.isoformat(),
            'data_br': c.data.strftime('%d/%m/%Y'),
            'historico': c.historico,
            'valor': float(c.valor),
            'conta_id': c.conta_id,
            'conta_nome': c.conta.nome if c.conta else None,
            'diff_valor': round(diff_valor, 2),
            'dist_dias': dist_dias,
            'score': round(score, 2),
            'match_exato': match_exato > 0,
        })

    resultado.sort(key=lambda x: x['score'], reverse=True)
    return resultado


# =============================================================================
# VINCULO
# =============================================================================
def vincular(
    fatura_id: int,
    transacao_pagamento_id: int,
    data_pagamento: Optional[date] = None,
) -> dict:
    """Vincula fatura a transacao de pagamento.

    - Seta fatura.transacao_pagamento_id = transacao_pagamento_id
    - Seta fatura.data_pagamento = data_pagamento ou transacao.data
    - Se a transacao nao tiver eh_pagamento_cartao=True, FORCA TRUE + excluir_relatorio=True
      (pois agora sabemos que e pagamento de fatura)
    """
    fat = db.session.get(PessoalImportacao, fatura_id)
    if not fat:
        raise ValueError(f'Fatura id={fatura_id} nao encontrada')
    if fat.tipo_arquivo != 'fatura_cartao':
        raise ValueError(f'Importacao id={fatura_id} nao e fatura_cartao')

    tx = db.session.get(PessoalTransacao, transacao_pagamento_id)
    if not tx:
        raise ValueError(f'Transacao id={transacao_pagamento_id} nao encontrada')
    if tx.tipo != 'debito':
        raise ValueError(
            f'Transacao id={transacao_pagamento_id} nao e debito (tipo={tx.tipo})'
        )

    # Verificar que a transacao ja nao esta vinculada a outra fatura
    outra = PessoalImportacao.query.filter(
        PessoalImportacao.transacao_pagamento_id == tx.id,
        PessoalImportacao.id != fatura_id,
    ).first()
    if outra:
        raise ValueError(
            f'Transacao id={tx.id} ja vinculada a fatura id={outra.id}. '
            'Desvincule antes.'
        )

    fat.transacao_pagamento_id = tx.id
    fat.data_pagamento = data_pagamento or tx.data
    fat.situacao_fatura = 'PAGO'

    # Forca marcas necessarias na transacao (se ainda nao marcado)
    alterou_tx = False
    if not tx.eh_pagamento_cartao:
        tx.eh_pagamento_cartao = True
        alterou_tx = True
    if not tx.excluir_relatorio:
        tx.excluir_relatorio = True
        alterou_tx = True

    db.session.commit()

    logger.info(
        'fatura_vinculada fatura_id=%d tx_id=%d data_pagamento=%s alterou_tx=%s',
        fatura_id, tx.id, fat.data_pagamento, alterou_tx,
    )

    return {
        'fatura_id': fatura_id,
        'transacao_pagamento_id': tx.id,
        'data_pagamento': fat.data_pagamento.isoformat() if fat.data_pagamento else None,
        'alterou_transacao': alterou_tx,
    }


def desvincular(fatura_id: int) -> dict:
    """Remove vinculo fatura -> transacao de pagamento.

    NAO reverte eh_pagamento_cartao na transacao (mantem independente).
    """
    fat = db.session.get(PessoalImportacao, fatura_id)
    if not fat:
        raise ValueError(f'Fatura id={fatura_id} nao encontrada')

    tx_id = fat.transacao_pagamento_id
    fat.transacao_pagamento_id = None
    fat.data_pagamento = None
    db.session.commit()

    logger.info('fatura_desvinculada fatura_id=%d tx_id=%s', fatura_id, tx_id or '-')
    return {'fatura_id': fatura_id, 'transacao_pagamento_id': tx_id}


# =============================================================================
# BACKFILL AUTOMATICO
# =============================================================================
def backfill_historico(
    apenas_match_exato: bool = True,
    max_candidatas: int = 1,
    dry_run: bool = True,
) -> dict:
    """Vincula automaticamente faturas PAGAS sem vinculo, quando houver
    candidata unica com match exato (valor + data dentro da janela).

    Args:
        apenas_match_exato: se True, so vincula quando diff_valor < 0.01
        max_candidatas: se 1, so vincula quando ha UMA unica candidata elegivel
        dry_run: se True, nao commita. Retorna o que faria.
    """
    faturas = PessoalImportacao.query.filter(
        PessoalImportacao.tipo_arquivo == 'fatura_cartao',
        PessoalImportacao.transacao_pagamento_id.is_(None),
    ).all()

    vinculadas = []
    ambiguas = []
    sem_match = []
    erros = []

    for fat in faturas:
        try:
            sugestoes = sugerir_matches(fat.id)
        except Exception as e:
            erros.append({'fatura_id': fat.id, 'erro': str(e)})
            continue

        # Filtra match exato se requerido
        if apenas_match_exato:
            sugestoes = [s for s in sugestoes if s['match_exato']]

        if not sugestoes:
            sem_match.append({
                'fatura_id': fat.id,
                'nome_arquivo': fat.nome_arquivo,
                'periodo_fim': fat.periodo_fim.isoformat() if fat.periodo_fim else None,
                'total_compras': _total_compras_fatura(fat.id),
            })
            continue

        if len(sugestoes) > max_candidatas:
            ambiguas.append({
                'fatura_id': fat.id,
                'n_candidatas': len(sugestoes),
                'top_3': sugestoes[:3],
            })
            continue

        # Vincula
        melhor = sugestoes[0]
        if not dry_run:
            try:
                vincular(fat.id, melhor['transacao_id'])
            except Exception as e:
                erros.append({'fatura_id': fat.id, 'erro': str(e)})
                continue
        vinculadas.append({
            'fatura_id': fat.id,
            'transacao_id': melhor['transacao_id'],
            'valor': melhor['valor'],
            'data': melhor['data'],
        })

    logger.info(
        'backfill_fatura dry=%s vinculadas=%d ambiguas=%d sem_match=%d erros=%d',
        dry_run, len(vinculadas), len(ambiguas), len(sem_match), len(erros),
    )

    return {
        'dry_run': dry_run,
        'total_faturas_sem_vinculo': len(faturas),
        'vinculadas': vinculadas,
        'ambiguas': ambiguas,
        'sem_match': sem_match,
        'erros': erros,
    }


# =============================================================================
# LISTAGEM (para tela de gerenciamento)
# =============================================================================
def listar_faturas_com_status(
    conta_id: Optional[int] = None,
    apenas_sem_vinculo: bool = False,
    limit: int = 100,
) -> list[dict]:
    """Lista faturas de cartao com status de vinculo ao pagamento."""
    q = PessoalImportacao.query.filter(
        PessoalImportacao.tipo_arquivo == 'fatura_cartao',
    )
    if conta_id:
        q = q.filter(PessoalImportacao.conta_id == conta_id)
    if apenas_sem_vinculo:
        q = q.filter(PessoalImportacao.transacao_pagamento_id.is_(None))

    faturas = q.order_by(
        PessoalImportacao.periodo_fim.desc().nullslast(),
    ).limit(limit).all()
    if not faturas:
        return []

    # Bulk: totais (SUM + COUNT) agregados por importacao_id em 1 query
    fatura_ids = [f.id for f in faturas]
    agregados = {
        row[0]: (int(row[1] or 0), float(row[2] or 0))
        for row in db.session.query(
            PessoalTransacao.importacao_id,
            func.count(PessoalTransacao.id),
            func.coalesce(func.sum(PessoalTransacao.valor), 0),
        ).filter(
            PessoalTransacao.importacao_id.in_(fatura_ids),
        ).group_by(PessoalTransacao.importacao_id).all()
    }

    # Bulk: transacoes de pagamento em 1 query
    pag_ids = [f.transacao_pagamento_id for f in faturas if f.transacao_pagamento_id]
    pagamentos = {
        t.id: t
        for t in PessoalTransacao.query.filter(
            PessoalTransacao.id.in_(pag_ids),
        ).all()
    } if pag_ids else {}

    out = []
    for fat in faturas:
        n_compras, total_compras = agregados.get(fat.id, (0, 0.0))
        tx_pag = pagamentos.get(fat.transacao_pagamento_id) if fat.transacao_pagamento_id else None
        out.append({
            'id': fat.id,
            'conta_id': fat.conta_id,
            'conta_nome': fat.conta.nome if fat.conta else None,
            'nome_arquivo': fat.nome_arquivo,
            'periodo_inicio': (
                fat.periodo_inicio.isoformat() if fat.periodo_inicio else None
            ),
            'periodo_fim': (
                fat.periodo_fim.isoformat() if fat.periodo_fim else None
            ),
            'situacao_fatura': fat.situacao_fatura,
            'total_compras': round(total_compras, 2),
            'data_pagamento': fat.data_pagamento.isoformat() if fat.data_pagamento else None,
            'transacao_pagamento_id': fat.transacao_pagamento_id,
            'pagamento': {
                'id': tx_pag.id,
                'data': tx_pag.data.isoformat() if tx_pag.data else None,
                'valor': float(tx_pag.valor),
                'historico': tx_pag.historico,
                'diff_valor': round(float(tx_pag.valor) - total_compras, 2),
            } if tx_pag else None,
            'n_compras': n_compras,
        })
    return out
