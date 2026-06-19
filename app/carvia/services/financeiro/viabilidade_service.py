"""Receita CarVia agregada para a tela de viabilidade (mapa + embarque).

Receita = CTe (CarviaOperacao.cte_valor) quando ja existe; senao o valor cotado
do frete (CarviaCotacao.valor_final_aprovado). NAO faz rateio — soma bruta.
"""
from app import db


def _receita_lote(lote):
    """(valor: float, fonte: 'CTE'|'COTACAO'|'SEM') para um separacao_lote_id."""
    from app.carvia.models import CarviaNf, CarviaOperacao, CarviaOperacaoNf
    from app.carvia.models.cotacao import CarviaCotacao, CarviaPedido

    if lote.startswith('CARVIA-PED-'):
        ped = CarviaPedido.query.get(int(lote.replace('CARVIA-PED-', '')))
        if not ped:
            return 0.0, 'SEM'
        ops = [o for o in ped.operacoes_ctes if o.cte_valor]
        if ops:
            return float(sum(o.cte_valor for o in ops)), 'CTE'
        cot = CarviaCotacao.query.get(ped.cotacao_id) if ped.cotacao_id else None
        if cot and cot.valor_final_aprovado:
            return float(cot.valor_final_aprovado), 'COTACAO'
        return 0.0, 'SEM'

    if lote.startswith('CARVIA-NF-'):
        nf = CarviaNf.query.get(int(lote.replace('CARVIA-NF-', '')))
        if not nf:
            return 0.0, 'SEM'
        op = (
            db.session.query(CarviaOperacao)
            .join(CarviaOperacaoNf, CarviaOperacaoNf.operacao_id == CarviaOperacao.id)
            .filter(CarviaOperacaoNf.nf_id == nf.id, CarviaOperacao.status != 'CANCELADO')
            .first()
        )
        if op and op.cte_valor:
            return float(op.cte_valor), 'CTE'
        return 0.0, 'SEM'

    if lote.startswith('CARVIA-'):  # CARVIA-{cot_id}
        try:
            cot_id = int(lote.replace('CARVIA-', ''))
        except ValueError:
            return 0.0, 'SEM'
        cot = CarviaCotacao.query.get(cot_id)
        if cot:
            valor = cot.valor_final_aprovado or cot.valor_manual or cot.valor_tabela
            if valor:
                return float(valor), 'COTACAO'
        return 0.0, 'SEM'

    return 0.0, 'SEM'  # lote NACOM


def receita_carvia_por_lotes(lotes):
    por_lote = {}
    total = 0.0
    for lote in (lotes or []):
        valor, fonte = _receita_lote(lote)
        por_lote[lote] = {'valor': round(valor, 2), 'fonte': fonte}
        total += valor
    return {'total': round(total, 2), 'por_lote': por_lote}


def receita_carvia_por_embarque(embarque_id):
    """Soma cte_valor das operacoes vinculadas ao embarque via CarviaFrete."""
    from app.carvia.models import CarviaFrete, CarviaOperacao
    if not embarque_id:
        return {'total': 0.0, 'tem_cte': False}
    op_ids = {
        fid for (fid,) in db.session.query(CarviaFrete.operacao_id)
        .filter(CarviaFrete.embarque_id == embarque_id, CarviaFrete.operacao_id.isnot(None))
        .distinct().all()
    }
    if not op_ids:
        return {'total': 0.0, 'tem_cte': False}
    ops = (
        db.session.query(CarviaOperacao)
        .filter(CarviaOperacao.id.in_(op_ids), CarviaOperacao.status != 'CANCELADO')
        .all()
    )
    total = float(sum(o.cte_valor for o in ops if o.cte_valor))
    return {'total': round(total, 2), 'tem_cte': any(o.cte_valor for o in ops)}
