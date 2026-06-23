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


def _cotacao_id_do_lote(lote):
    """Resolve o cotacao_id de um separacao_lote_id CarVia quando o EmbarqueItem nao tem
    carvia_cotacao_id setado (fallback). A ordem importa: testar PED-/NF- ANTES do CARVIA-
    cru (que e a cotacao)."""
    from app.carvia.models import CarviaNf
    from app.carvia.models.cotacao import CarviaPedido, CarviaPedidoItem
    if not lote:
        return None
    if lote.startswith('CARVIA-PED-'):
        try:
            ped = CarviaPedido.query.get(int(lote.replace('CARVIA-PED-', '')))
        except ValueError:
            return None
        return ped.cotacao_id if ped else None
    if lote.startswith('CARVIA-NF-'):
        try:
            nf = CarviaNf.query.get(int(lote.replace('CARVIA-NF-', '')))
        except ValueError:
            return None
        if not nf:
            return None
        item = CarviaPedidoItem.query.filter_by(numero_nf=nf.numero_nf).first()
        if not item:
            return None
        ped = CarviaPedido.query.get(item.pedido_id)
        return ped.cotacao_id if ped else None
    if lote.startswith('CARVIA-'):
        try:
            return int(lote.replace('CARVIA-', ''))
        except ValueError:
            return None
    return None


def receita_carvia_por_embarque(embarque_id, itens_carvia=None):
    """Receita CarVia do embarque, agregada por COTACAO (CTe se houver, senao valor cotado).

    `itens_carvia`: lista de (separacao_lote_id, carvia_cotacao_id) dos EmbarqueItem CarVia
    ATIVOS, fornecida pela property `Embarque.receita_carvia` — mantem R1 (este service NAO
    importa app/embarques). Agrupar por cotacao evita dobrar quando o embarque tem >1 item da
    MESMA cotacao (split SP/RJ, ou provisorio CARVIA-PED-* + real CARVIA-NF-*).

    Antes este calculo somava SO o cte_valor via CarviaFrete: ficava R$ 0 ate a saida da
    portaria (quando o CarviaFrete/CTe nasce) e nao atualizava ao adicionar um pedido. Agora
    reflete a receita cotada dos pedidos ja no momento em que entram no embarque.
    """
    from app.carvia.models.cotacao import CarviaCotacao, CarviaPedido
    if not embarque_id or not itens_carvia:
        return {'total': 0.0, 'tem_cte': False}

    cot_ids = set()
    for lote, cot_id in itens_carvia:
        cid = cot_id or _cotacao_id_do_lote(lote)
        if cid:
            cot_ids.add(cid)

    total = 0.0
    tem_cte = False
    for cid in cot_ids:
        cot = CarviaCotacao.query.get(cid)
        if not cot or cot.status == 'CANCELADO':
            continue
        peds = (
            CarviaPedido.query
            .filter(CarviaPedido.cotacao_id == cid, CarviaPedido.status != 'CANCELADO')
            .all()
        )
        # operacoes_ctes (property do pedido) ja exclui operacoes CANCELADO
        ctes = [float(o.cte_valor) for p in peds for o in p.operacoes_ctes if o.cte_valor]
        if ctes:
            total += sum(ctes)
            tem_cte = True
        else:
            valor = cot.valor_final_aprovado or cot.valor_manual or cot.valor_tabela
            if valor:
                total += float(valor)

    return {'total': round(total, 2), 'tem_cte': tem_cte}
