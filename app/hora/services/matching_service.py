"""Matching NF x Pedido — sugere pedidos candidatos por chassis e aplica
correções 1-1 entre itens da NF e do Pedido.

Regra crítica: filtro é por `loja_destino_id`, NUNCA por CNPJ. Todas as NFs
e pedidos da HORA usam o CNPJ da matriz; a loja é o discriminante real.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import List, Optional

from app import db
from app.hora.models import (
    HoraNfEntrada,
    HoraNfEntradaItem,
    HoraPedido,
    HoraPedidoItem,
)
from app.hora.services.moto_service import get_or_create_moto
from app.hora.services.pedido_service import atualizar_status_pedido_por_faturamento


STATUS_CANDIDATOS = ('ABERTO', 'PARCIALMENTE_FATURADO')


# ------------------------------------------------------------------------
# Score
# ------------------------------------------------------------------------

@dataclass
class ScoreCandidato:
    """Contagem de chassis para um par (NF, Pedido) candidato."""
    pedido_id: int
    numero_pedido: str
    data_pedido_iso: str
    status: str
    total_pedido: int          # chassis no pedido (com chassi preenchido)
    total_pedido_pendente: int  # chassis NULL no pedido (ainda sem atribuicao)
    match: int                 # chassis da NF que casam com pedido
    sem_nf: int                # chassis do pedido (com chassi) ainda nao faturados em qualquer NF

    def to_dict(self) -> dict:
        return asdict(self)


def _chassis_nf(nf: HoraNfEntrada) -> set:
    return {i.numero_chassi for i in nf.itens if i.numero_chassi}


def _chassis_pedido_preenchidos(pedido: HoraPedido) -> set:
    return {i.numero_chassi for i in pedido.itens if i.numero_chassi}


def _chassis_pedido_pendentes(pedido: HoraPedido) -> int:
    return sum(1 for i in pedido.itens if not i.numero_chassi)


def _chassis_ja_faturados_no_pedido(pedido_id: int) -> set:
    """Chassis do pedido que aparecem em NFs vinculadas a este pedido."""
    rows = (
        db.session.query(HoraNfEntradaItem.numero_chassi)
        .join(HoraNfEntrada, HoraNfEntradaItem.nf_id == HoraNfEntrada.id)
        .filter(HoraNfEntrada.pedido_id == pedido_id)
        .all()
    )
    return {r.numero_chassi for r in rows}


def calcular_score(nf: HoraNfEntrada, pedido: HoraPedido) -> ScoreCandidato:
    chassis_nf = _chassis_nf(nf)
    chassis_ped = _chassis_pedido_preenchidos(pedido)
    faturados = _chassis_ja_faturados_no_pedido(pedido.id)

    match = len(chassis_ped & chassis_nf)
    sem_nf = len(chassis_ped - faturados)

    return ScoreCandidato(
        pedido_id=pedido.id,
        numero_pedido=pedido.numero_pedido,
        data_pedido_iso=pedido.data_pedido.isoformat() if pedido.data_pedido else '',
        status=pedido.status,
        total_pedido=len(chassis_ped),
        total_pedido_pendente=_chassis_pedido_pendentes(pedido),
        match=match,
        sem_nf=sem_nf,
    )


# ------------------------------------------------------------------------
# Candidatos
# ------------------------------------------------------------------------

def candidatos_pedidos_para_nf(nf_id: int) -> List[ScoreCandidato]:
    """Retorna pedidos candidatos da MESMA loja da NF, ordenados por match desc.

    Pre-requisito: NF precisa ter `loja_destino_id` preenchida.
    Filtro: `loja_destino_id == nf.loja_destino_id` AND status em ABERTO/PARCIAL.
    Ordenacao: match DESC, depois total_pedido_pendente DESC (pedidos mais "pre-NF"
    aparecem antes em caso de empate), depois data_pedido DESC.
    """
    nf = HoraNfEntrada.query.get(nf_id)
    if not nf:
        raise ValueError(f'NF {nf_id} nao encontrada')
    if not nf.loja_destino_id:
        raise ValueError(
            'NF ainda nao tem loja_destino_id. Preencha a loja antes de '
            'buscar pedidos candidatos.'
        )

    pedidos = (
        HoraPedido.query
        .filter(
            HoraPedido.loja_destino_id == nf.loja_destino_id,
            HoraPedido.status.in_(STATUS_CANDIDATOS),
        )
        .order_by(HoraPedido.data_pedido.desc(), HoraPedido.id.desc())
        .all()
    )

    scores = [calcular_score(nf, p) for p in pedidos]
    scores.sort(
        key=lambda s: (s.match, s.total_pedido_pendente, s.data_pedido_iso),
        reverse=True,
    )
    return scores


def score_um_pedido(nf_id: int, pedido_id: int) -> ScoreCandidato:
    nf = HoraNfEntrada.query.get(nf_id)
    if not nf:
        raise ValueError(f'NF {nf_id} nao encontrada')
    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        raise ValueError(f'Pedido {pedido_id} nao encontrado')
    if nf.loja_destino_id and pedido.loja_destino_id and nf.loja_destino_id != pedido.loja_destino_id:
        raise ValueError(
            f'Loja da NF ({nf.loja_destino_id}) difere da loja do pedido ({pedido.loja_destino_id}).'
        )
    return calcular_score(nf, pedido)


# ------------------------------------------------------------------------
# Preview de match (para pintar linhas)
# ------------------------------------------------------------------------

def preview_match(nf_id: int, pedido_id: int) -> dict:
    """Retorna estrutura para pintar linhas NF x Pedido.

    {
      nf_itens: [{chassi, modelo, cor, match: bool}, ...],
      pedido_itens: [{id, chassi, modelo, cor, match: bool, pendente: bool}, ...],
      totais: {
        total_nf,
        total_pedido,
        total_pedido_pendente,
        match,
        pct_match,  # match / total_nf * 100
      }
    }
    """
    nf = HoraNfEntrada.query.get(nf_id)
    if not nf:
        raise ValueError(f'NF {nf_id} nao encontrada')
    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        raise ValueError(f'Pedido {pedido_id} nao encontrado')

    chassis_nf = _chassis_nf(nf)
    chassis_ped = _chassis_pedido_preenchidos(pedido)
    intersecao = chassis_nf & chassis_ped

    nf_itens = [
        {
            'id': i.id,
            'chassi': i.numero_chassi,
            'modelo': i.modelo_texto_original or '',
            'cor': i.cor_texto_original or '',
            'match': i.numero_chassi in intersecao,
        }
        for i in nf.itens
    ]

    pedido_itens = [
        {
            'id': i.id,
            'chassi': i.numero_chassi,
            'modelo': i.modelo.nome_modelo if i.modelo else '',
            'cor': i.cor or '',
            'pendente': i.numero_chassi is None,
            'match': bool(i.numero_chassi and i.numero_chassi in intersecao),
        }
        for i in pedido.itens
    ]

    total_nf = len(nf.itens)
    total_pedido = len(pedido.itens)
    match = len(intersecao)
    pct_match = (match / total_nf * 100) if total_nf else 0.0

    return {
        'nf_itens': nf_itens,
        'pedido_itens': pedido_itens,
        'totais': {
            'total_nf': total_nf,
            'total_pedido': total_pedido,
            'total_pedido_pendente': _chassis_pedido_pendentes(pedido),
            'match': match,
            'pct_match': round(pct_match, 1),
        },
    }


# ------------------------------------------------------------------------
# Correcoes 1-1
# ------------------------------------------------------------------------

def _validar_mesma_loja(nf: HoraNfEntrada, pedido: HoraPedido) -> None:
    if not nf.loja_destino_id:
        raise ValueError('NF sem loja_destino_id. Defina a loja antes de corrigir.')
    if not pedido.loja_destino_id:
        raise ValueError('Pedido sem loja_destino_id.')
    if nf.loja_destino_id != pedido.loja_destino_id:
        raise ValueError(
            f'Loja da NF ({nf.loja_destino_id}) difere do pedido ({pedido.loja_destino_id}).'
        )


def aplicar_correcao_pedido_item(
    nf_id: int,
    pedido_id: int,
    pedido_item_id: int,
    nf_item_id: int,
    operador: Optional[str] = None,
) -> dict:
    """Copia chassi da NF para o item do pedido (Corrigir Pedido).

    Cenarios:
    - item.numero_chassi IS NULL: preenche com o chassi da NF (+ ajusta modelo_id).
    - item.numero_chassi != chassi NF: substitui (supoe que Motochefe trocou chassi
      na hora de faturar). Em ambos, respeita invariante insert-once de HoraMoto.

    Validacoes:
    - nf_item e pedido_item pertencem a nf_id / pedido_id.
    - loja de nf == loja de pedido.
    - chassi-alvo nao pode ja estar em outro item do mesmo pedido.
    """
    nf = HoraNfEntrada.query.get(nf_id)
    if not nf:
        raise ValueError(f'NF {nf_id} nao encontrada')
    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        raise ValueError(f'Pedido {pedido_id} nao encontrado')
    _validar_mesma_loja(nf, pedido)

    nf_item = HoraNfEntradaItem.query.get(nf_item_id)
    if not nf_item or nf_item.nf_id != nf.id:
        raise ValueError(f'Item {nf_item_id} nao pertence a NF {nf_id}')

    pedido_item = HoraPedidoItem.query.get(pedido_item_id)
    if not pedido_item or pedido_item.pedido_id != pedido.id:
        raise ValueError(f'Item {pedido_item_id} nao pertence ao pedido {pedido_id}')

    novo_chassi = nf_item.numero_chassi
    if not novo_chassi:
        raise ValueError('Item da NF sem chassi.')

    # Unicidade no mesmo pedido
    duplicado = (
        HoraPedidoItem.query
        .filter(
            HoraPedidoItem.pedido_id == pedido.id,
            HoraPedidoItem.numero_chassi == novo_chassi,
            HoraPedidoItem.id != pedido_item.id,
        )
        .first()
    )
    if duplicado:
        raise ValueError(
            f'Chassi {novo_chassi} ja esta em outro item (#{duplicado.id}) do pedido.'
        )

    # Garante HoraMoto (insert-once)
    moto = get_or_create_moto(
        numero_chassi=novo_chassi,
        modelo_nome=nf_item.modelo_texto_original,
        cor=nf_item.cor_texto_original or 'NAO_INFORMADA',
        numero_motor=nf_item.numero_motor_texto_original,
        criado_por=operador,
    )

    pedido_item.numero_chassi = moto.numero_chassi
    pedido_item.modelo_id = moto.modelo_id
    if nf_item.cor_texto_original and not pedido_item.cor:
        pedido_item.cor = nf_item.cor_texto_original

    db.session.commit()

    # Se a NF ja esta vinculada a este pedido, atualiza status
    if nf.pedido_id == pedido.id:
        atualizar_status_pedido_por_faturamento(pedido.id)

    return {
        'ok': True,
        'pedido_item_id': pedido_item.id,
        'numero_chassi': pedido_item.numero_chassi,
    }


def aplicar_correcao_nf_item(
    nf_id: int,
    pedido_id: int,
    nf_item_id: int,
    pedido_item_id: int,
    operador: Optional[str] = None,
) -> dict:
    """Copia chassi do pedido para o item da NF (Corrigir NF).

    Supoe que o item do pedido tem o chassi correto (Motochefe errou ao faturar).
    Valida unicidade por (nf_id, chassi).
    """
    nf = HoraNfEntrada.query.get(nf_id)
    if not nf:
        raise ValueError(f'NF {nf_id} nao encontrada')
    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        raise ValueError(f'Pedido {pedido_id} nao encontrado')
    _validar_mesma_loja(nf, pedido)

    nf_item = HoraNfEntradaItem.query.get(nf_item_id)
    if not nf_item or nf_item.nf_id != nf.id:
        raise ValueError(f'Item {nf_item_id} nao pertence a NF {nf_id}')

    pedido_item = HoraPedidoItem.query.get(pedido_item_id)
    if not pedido_item or pedido_item.pedido_id != pedido.id:
        raise ValueError(f'Item {pedido_item_id} nao pertence ao pedido {pedido_id}')

    novo_chassi = pedido_item.numero_chassi
    if not novo_chassi:
        raise ValueError(
            'Item do pedido sem chassi. Use "Corrigir Pedido" para preencher o '
            'chassi do pedido a partir da NF.'
        )

    # Unicidade na mesma NF
    duplicado = (
        HoraNfEntradaItem.query
        .filter(
            HoraNfEntradaItem.nf_id == nf.id,
            HoraNfEntradaItem.numero_chassi == novo_chassi,
            HoraNfEntradaItem.id != nf_item.id,
        )
        .first()
    )
    if duplicado:
        raise ValueError(
            f'Chassi {novo_chassi} ja esta em outro item (#{duplicado.id}) da NF.'
        )

    # Garante HoraMoto do chassi novo
    get_or_create_moto(
        numero_chassi=novo_chassi,
        modelo_nome=(pedido_item.modelo.nome_modelo if pedido_item.modelo else None),
        cor=pedido_item.cor or 'NAO_INFORMADA',
        criado_por=operador,
    )

    nf_item.numero_chassi = novo_chassi
    db.session.commit()

    if nf.pedido_id == pedido.id:
        atualizar_status_pedido_por_faturamento(pedido.id)

    return {
        'ok': True,
        'nf_item_id': nf_item.id,
        'numero_chassi': nf_item.numero_chassi,
    }


# ------------------------------------------------------------------------
# Completar chassis (Gap 2)
# ------------------------------------------------------------------------

def aplicar_pares_completar_chassis(
    pedido_id: int,
    pares: List[dict],
    operador: Optional[str] = None,
) -> dict:
    """Aplica N pares 1-1 para preencher chassis pendentes do pedido.

    pares: [{'pedido_item_id': int, 'nf_item_id': int}, ...]

    - Cada pedido_item precisa estar com chassi NULL.
    - Cada nf_item tem que ser da loja do pedido e ter chassi preenchido.
    - Chassis dentro do mesmo pedido nao se repetem.
    """
    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        raise ValueError(f'Pedido {pedido_id} nao encontrado')
    if not pedido.loja_destino_id:
        raise ValueError('Pedido sem loja_destino_id.')

    aplicados = []
    chassis_aplicados_no_lote = set()

    for par in pares:
        pi_id = par.get('pedido_item_id')
        ni_id = par.get('nf_item_id')
        if not pi_id or not ni_id:
            raise ValueError(f'Par invalido: {par}')

        pi = HoraPedidoItem.query.get(int(pi_id))
        if not pi or pi.pedido_id != pedido.id:
            raise ValueError(f'Item pedido {pi_id} nao pertence ao pedido.')
        if pi.numero_chassi:
            raise ValueError(
                f'Item pedido #{pi_id} ja possui chassi ({pi.numero_chassi}). '
                f'Use a tela de edicao manual.'
            )

        ni = HoraNfEntradaItem.query.get(int(ni_id))
        if not ni or not ni.numero_chassi:
            raise ValueError(f'Item NF {ni_id} invalido ou sem chassi.')
        # Valida que a NF e da mesma loja
        nf = HoraNfEntrada.query.get(ni.nf_id)
        if not nf or nf.loja_destino_id != pedido.loja_destino_id:
            raise ValueError(
                f'Item NF {ni_id} e de loja diferente do pedido.'
            )

        chassi = ni.numero_chassi
        if chassi in chassis_aplicados_no_lote:
            raise ValueError(f'Chassi {chassi} repetido no lote.')
        # Unicidade no pedido
        dup = (
            HoraPedidoItem.query
            .filter(
                HoraPedidoItem.pedido_id == pedido.id,
                HoraPedidoItem.numero_chassi == chassi,
                HoraPedidoItem.id != pi.id,
            )
            .first()
        )
        if dup:
            raise ValueError(
                f'Chassi {chassi} ja esta em outro item (#{dup.id}) do pedido.'
            )
        chassis_aplicados_no_lote.add(chassi)

        moto = get_or_create_moto(
            numero_chassi=chassi,
            modelo_nome=ni.modelo_texto_original,
            cor=ni.cor_texto_original or 'NAO_INFORMADA',
            numero_motor=ni.numero_motor_texto_original,
            criado_por=operador,
        )
        pi.numero_chassi = moto.numero_chassi
        pi.modelo_id = moto.modelo_id
        if ni.cor_texto_original and not pi.cor:
            pi.cor = ni.cor_texto_original

        aplicados.append({
            'pedido_item_id': pi.id,
            'nf_item_id': ni.id,
            'numero_chassi': pi.numero_chassi,
        })

    db.session.commit()
    # Recalcula status de todas as NFs vinculadas a este pedido
    atualizar_status_pedido_por_faturamento(pedido.id)

    return {'ok': True, 'aplicados': aplicados, 'total': len(aplicados)}


def chassis_nf_disponiveis_para_pedido(pedido_id: int) -> List[dict]:
    """Retorna chassis de NFs da mesma loja que NAO estao em nenhum pedido_item.

    Prioriza NFs ja vinculadas ao pedido; depois NFs sem vinculo da mesma loja.
    """
    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        raise ValueError(f'Pedido {pedido_id} nao encontrado')
    if not pedido.loja_destino_id:
        raise ValueError('Pedido sem loja_destino_id.')

    # Chassis ja usados em QUALQUER item do pedido
    chassis_em_uso_pedido = {
        i.numero_chassi for i in pedido.itens if i.numero_chassi
    }

    # Base: itens de NFs da mesma loja
    q = (
        db.session.query(HoraNfEntradaItem, HoraNfEntrada)
        .join(HoraNfEntrada, HoraNfEntradaItem.nf_id == HoraNfEntrada.id)
        .filter(HoraNfEntrada.loja_destino_id == pedido.loja_destino_id)
    )
    linhas = q.all()

    # Ordena: NF vinculada ao pedido primeiro, depois sem vinculo, depois outras
    def prioridade(row):
        _, nf = row
        if nf.pedido_id == pedido.id:
            return (0, -nf.data_emissao.toordinal() if nf.data_emissao else 0)
        if nf.pedido_id is None:
            return (1, -nf.data_emissao.toordinal() if nf.data_emissao else 0)
        return (2, -nf.data_emissao.toordinal() if nf.data_emissao else 0)

    linhas.sort(key=prioridade)

    resultado = []
    for ni, nf in linhas:
        if not ni.numero_chassi:
            continue
        if ni.numero_chassi in chassis_em_uso_pedido:
            continue
        resultado.append({
            'nf_item_id': ni.id,
            'nf_id': nf.id,
            'nf_numero': nf.numero_nf,
            'nf_pedido_id': nf.pedido_id,
            'vinculada_a_este_pedido': nf.pedido_id == pedido.id,
            'chassi': ni.numero_chassi,
            'modelo': ni.modelo_texto_original or '',
            'cor': ni.cor_texto_original or '',
            'preco_real': float(ni.preco_real) if ni.preco_real is not None else None,
        })
    return resultado


def editar_pedido_item_manual(
    pedido_id: int,
    pedido_item_id: int,
    numero_chassi: Optional[str] = None,
    modelo_nome: Optional[str] = None,
    cor: Optional[str] = None,
    operador: Optional[str] = None,
) -> dict:
    """Edicao manual (excecao da excecao): permite ajustar chassi/modelo/cor
    de um item do pedido. Valida unicidade do chassi no mesmo pedido."""
    pedido = HoraPedido.query.get(pedido_id)
    if not pedido:
        raise ValueError(f'Pedido {pedido_id} nao encontrado')
    pi = HoraPedidoItem.query.get(pedido_item_id)
    if not pi or pi.pedido_id != pedido.id:
        raise ValueError(f'Item {pedido_item_id} nao pertence ao pedido.')

    chassi_norm = (numero_chassi or '').strip().upper() or None
    if chassi_norm:
        if len(chassi_norm) > 30:
            raise ValueError('chassi excede 30 caracteres.')
        dup = (
            HoraPedidoItem.query
            .filter(
                HoraPedidoItem.pedido_id == pedido.id,
                HoraPedidoItem.numero_chassi == chassi_norm,
                HoraPedidoItem.id != pi.id,
            )
            .first()
        )
        if dup:
            raise ValueError(
                f'Chassi {chassi_norm} ja esta em outro item (#{dup.id}) do pedido.'
            )
        moto = get_or_create_moto(
            numero_chassi=chassi_norm,
            modelo_nome=modelo_nome,
            cor=(cor or 'NAO_INFORMADA'),
            criado_por=operador,
        )
        pi.numero_chassi = moto.numero_chassi
        pi.modelo_id = moto.modelo_id
    else:
        pi.numero_chassi = None
        if modelo_nome:
            from app.hora.services.cadastro_service import buscar_ou_criar_modelo
            pi.modelo_id = buscar_ou_criar_modelo(modelo_nome).id

    if cor is not None:
        pi.cor = cor.strip().upper() or None

    db.session.commit()
    atualizar_status_pedido_por_faturamento(pedido.id)
    return {
        'ok': True,
        'pedido_item_id': pi.id,
        'numero_chassi': pi.numero_chassi,
    }


# ------------------------------------------------------------------------
# Vinculos por chassi (para UI de detalhe com granularidade por moto)
# ------------------------------------------------------------------------

def vinculos_por_chassi_pedido(pedido_id: int) -> dict:
    """Para cada chassi do pedido, retorna a NF (+item) que o faturou.

    Retorna: {chassi: {'nf': HoraNfEntrada, 'nf_item': HoraNfEntradaItem}}

    Considera apenas NFs com pedido_id == este pedido. Chassi do pedido
    ausente do dict significa: ainda nao faturado.
    """
    rows = (
        db.session.query(HoraNfEntradaItem, HoraNfEntrada)
        .join(HoraNfEntrada, HoraNfEntradaItem.nf_id == HoraNfEntrada.id)
        .filter(HoraNfEntrada.pedido_id == pedido_id)
        .all()
    )
    resultado = {}
    for nf_item, nf in rows:
        if nf_item.numero_chassi:
            resultado[nf_item.numero_chassi] = {'nf': nf, 'nf_item': nf_item}
    return resultado


def vinculo_por_chassi_nf(nf_id: int) -> dict:
    """Para cada chassi da NF, retorna o pedido (+item) que o contem.

    Busca entre todos os pedidos que usam o chassi (prioriza pedido vinculado
    a esta NF; se nao achar la, busca em qualquer pedido com o mesmo chassi).

    Retorna: {chassi: {'pedido': HoraPedido, 'pedido_item': HoraPedidoItem,
                        'vinculado_a_nf': bool}}
    Chassi ausente do dict = chassi da NF nao casa com nenhum pedido (extra).
    """
    nf = HoraNfEntrada.query.get(nf_id)
    if not nf:
        return {}

    chassis_nf = [i.numero_chassi for i in nf.itens if i.numero_chassi]
    if not chassis_nf:
        return {}

    # 1) pedido diretamente vinculado a esta NF (prioridade)
    resultado = {}
    if nf.pedido_id:
        pedido = HoraPedido.query.get(nf.pedido_id)
        if pedido:
            for pi in pedido.itens:
                if pi.numero_chassi and pi.numero_chassi in chassis_nf:
                    resultado[pi.numero_chassi] = {
                        'pedido': pedido,
                        'pedido_item': pi,
                        'vinculado_a_nf': True,
                    }

    # 2) chassis ainda nao resolvidos: busca em qualquer pedido
    chassis_pendentes = [c for c in chassis_nf if c not in resultado]
    if chassis_pendentes:
        itens_extras = (
            db.session.query(HoraPedidoItem, HoraPedido)
            .join(HoraPedido, HoraPedidoItem.pedido_id == HoraPedido.id)
            .filter(HoraPedidoItem.numero_chassi.in_(chassis_pendentes))
            .all()
        )
        for pi, pedido in itens_extras:
            if pi.numero_chassi not in resultado:
                resultado[pi.numero_chassi] = {
                    'pedido': pedido,
                    'pedido_item': pi,
                    'vinculado_a_nf': False,
                }
    return resultado


def resumo_faturamento_pedido(
    pedido: HoraPedido,
    chassis_faturados_por_pedido: Optional[dict] = None,
) -> dict:
    """Agregado para lista/dashboard: {total, faturados, pendentes_chassi, pct}.

    `chassis_faturados_por_pedido` (opcional): dict {pedido_id: set(chassis)}
    pre-carregado em batch para evitar N+1. Se None, consulta individual.

    pct e calculado sobre base conhecida (chassis com chassi preenchido).
    Chassis pendentes nao entram na base do percentual (nao ha como faturar
    um item sem chassi); aparecem em `pendentes_chassi` separadamente.
    """
    total = len(pedido.itens)
    chassis_pedido = {i.numero_chassi for i in pedido.itens if i.numero_chassi}
    pendentes_chassi = total - len(chassis_pedido)
    if chassis_faturados_por_pedido is not None:
        fat_set = chassis_faturados_por_pedido.get(pedido.id, set())
    else:
        fat_set = _chassis_ja_faturados_no_pedido(pedido.id)
    faturados = len(fat_set & chassis_pedido)
    base = len(chassis_pedido)
    return {
        'total': total,
        'faturados': faturados,
        'pendentes_chassi': pendentes_chassi,
        'pct': int((faturados * 100) / base) if base else 0,
    }


def chassis_faturados_por_pedido_batch(pedido_ids: list) -> dict:
    """Bulk load: {pedido_id: set(chassis_faturados)} em 1 query."""
    if not pedido_ids:
        return {}
    rows = (
        db.session.query(
            HoraNfEntrada.pedido_id,
            HoraNfEntradaItem.numero_chassi,
        )
        .join(HoraNfEntradaItem, HoraNfEntradaItem.nf_id == HoraNfEntrada.id)
        .filter(HoraNfEntrada.pedido_id.in_(pedido_ids))
        .all()
    )
    out: dict = {pid: set() for pid in pedido_ids}
    for pid, chassi in rows:
        if chassi:
            out.setdefault(pid, set()).add(chassi)
    return out


def resumo_vinculo_nf(
    nf: HoraNfEntrada,
    chassis_por_pedido: Optional[dict] = None,
) -> dict:
    """Agregado para lista de NFs. `chassis_por_pedido` (opcional):
    {pedido_id: set(chassis_do_pedido)} pre-carregado para evitar N+1.
    """
    total_nf = len(nf.itens)
    if not nf.pedido_id:
        return {'total_nf': total_nf, 'match': 0, 'sem_pedido': True}
    chassis_nf = {i.numero_chassi for i in nf.itens if i.numero_chassi}
    if chassis_por_pedido is not None:
        chassis_ped = chassis_por_pedido.get(nf.pedido_id, set())
    else:
        pedido = HoraPedido.query.get(nf.pedido_id)
        if not pedido:
            return {'total_nf': total_nf, 'match': 0, 'sem_pedido': True}
        chassis_ped = {i.numero_chassi for i in pedido.itens if i.numero_chassi}
    match = len(chassis_nf & chassis_ped)
    return {
        'total_nf': total_nf,
        'match': match,
        'sem_pedido': False,
    }


def chassis_pedido_batch(pedido_ids: list) -> dict:
    """Bulk load: {pedido_id: set(chassis_preenchidos)} em 1 query."""
    if not pedido_ids:
        return {}
    rows = (
        db.session.query(HoraPedidoItem.pedido_id, HoraPedidoItem.numero_chassi)
        .filter(HoraPedidoItem.pedido_id.in_(pedido_ids))
        .filter(HoraPedidoItem.numero_chassi.isnot(None))
        .all()
    )
    out: dict = {pid: set() for pid in pedido_ids}
    for pid, chassi in rows:
        out.setdefault(pid, set()).add(chassi)
    return out
