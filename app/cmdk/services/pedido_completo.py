"""
Service que monta o contexto completo de um pedido para a tela rica de
raio-X (/cmdk/pedido/<num_pedido>).

Combina dados de:
  - CarteiraPrincipal (itens, totais)
  - Separacao (separacoes ativas + lotes em previsao)
  - FaturamentoProduto + EntregaMonitorada (NFs faturadas + status entrega)

Projecao de estoque (D0-D28) e estoque atual sao LAZY no client
(chamam /carteira/api/pedido/<num>/estoque e
/carteira/api/produto/<cod>/projecao-linha existentes).
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import func

from app import db
from app.carteira.models import CarteiraPrincipal
from app.carteira.utils.separacao_utils import calcular_peso_pallet_produto
from app.faturamento.models import FaturamentoProduto
from app.monitoramento.models import EntregaMonitorada
from app.separacao.models import Separacao


logger = logging.getLogger(__name__)


# Status de Separacao que representam separacao "ativa" (nao faturada)
STATUS_SEP_ATIVAS = ('ABERTO', 'PREVISAO', 'COTADO')


def montar_contexto(num_pedido: str) -> Optional[dict]:
    """
    Retorna contexto completo do pedido ou None se nao existir.

    Estrutura retornada (compativel com template cmdk/pedido_completo.html).
    """
    itens_orm = (
        db.session.query(CarteiraPrincipal)
        .filter(
            CarteiraPrincipal.num_pedido == num_pedido,
            CarteiraPrincipal.ativo.is_(True),
        )
        .order_by(CarteiraPrincipal.cod_produto)
        .all()
    )

    if not itens_orm:
        return None

    primeiro = itens_orm[0]

    # ----------------------------------------------------------- agregados (1 query cada)
    qtd_faturada_por_cod = _carregar_qtd_faturada_por_produto(num_pedido)
    qtd_separacao_por_cod = _carregar_qtd_em_separacao_por_produto(num_pedido)

    # ----------------------------------------------------------- itens & totais
    itens, totais = _montar_itens(
        itens_orm, qtd_faturada_por_cod, qtd_separacao_por_cod
    )

    # ----------------------------------------------------------- separacoes
    separacoes = _carregar_separacoes(num_pedido)

    # ----------------------------------------------------------- NFs faturadas
    nfs_faturadas = _carregar_nfs_faturadas(num_pedido)

    # ----------------------------------------------------------- contexto final
    return {
        'num_pedido': num_pedido,
        'cliente': {
            'cnpj_cpf': primeiro.cnpj_cpf,
            'razao_social': primeiro.raz_social,
            'razao_social_red': primeiro.raz_social_red,
            'municipio': primeiro.municipio,
            'estado': primeiro.estado,
            'vendedor': primeiro.vendedor,
            'equipe_vendas': primeiro.equipe_vendas,
        },
        'endereco_entrega': {
            'cnpj': primeiro.cnpj_endereco_ent,
            'empresa': primeiro.empresa_endereco_ent,
            'cep': primeiro.cep_endereco_ent,
            'cidade': primeiro.nome_cidade,
            'uf': primeiro.cod_uf,
            'bairro': primeiro.bairro_endereco_ent,
            'rua': primeiro.rua_endereco_ent,
            'numero': primeiro.endereco_ent,
            'telefone': primeiro.telefone_endereco_ent,
        },
        'pedido_cliente': primeiro.pedido_cliente,
        'data_pedido': _fmt_data(primeiro.data_pedido),
        'data_pedido_iso': primeiro.data_pedido.isoformat() if primeiro.data_pedido else None,
        'status_pedido': primeiro.status_pedido,
        'status_badge': _badge_status(primeiro.status_pedido),
        'observacoes': primeiro.observ_ped_1,
        'totais': totais,
        'itens': itens,
        'separacoes': separacoes,
        'has_separacoes': bool(separacoes),
        'nfs_faturadas': nfs_faturadas,
        'has_nfs_faturadas': bool(nfs_faturadas),
    }


# =============================================================================
# Helpers internos
# =============================================================================

def _montar_itens(
    itens_orm,
    qtd_faturada_por_cod: dict,
    qtd_separacao_por_cod: dict,
) -> tuple[list[dict], dict]:
    """
    Monta lista de itens com qtd_saldo_efetivo (deduz faturado + separacoes).

    qtd_saldo_efetivo = qtd_pedido - qtd_faturada - qtd_em_separacao_aberta

    Importante: o campo `qtd_saldo_produto_pedido` do banco ja deduz faturado,
    mas NAO deduz separacoes ativas (sincronizado_nf=False). Por isso
    recalculamos aqui para o display da tela rica.
    """
    itens: list[dict] = []
    total_valor = 0.0
    total_valor_saldo = 0.0
    total_peso = 0.0
    total_pallet = 0.0
    total_qtd_pedido = 0.0
    total_qtd_saldo = 0.0

    for item in itens_orm:
        cod = item.cod_produto
        qtd_pedido = float(item.qtd_produto_pedido or 0)
        qtd_faturada = float(qtd_faturada_por_cod.get(cod, 0) or 0)
        qtd_em_separacao = float(qtd_separacao_por_cod.get(cod, 0) or 0)
        qtd_saldo_banco = float(item.qtd_saldo_produto_pedido or 0)
        # qtd_saldo efetivo: garantido >=0 (caso somatorio passe de qtd_pedido)
        qtd_saldo_efetivo = max(0.0, qtd_pedido - qtd_faturada - qtd_em_separacao)

        preco = float(item.preco_produto_pedido or 0)
        valor_pedido = qtd_pedido * preco
        valor_saldo_efetivo = qtd_saldo_efetivo * preco

        try:
            peso, pallet = calcular_peso_pallet_produto(cod, qtd_saldo_efetivo)
        except Exception:
            peso, pallet = 0.0, 0.0

        # Coeficientes unitarios para JS recalcular ao editar qtd no modo
        # edicao de separacao. peso_unit = peso / qtd_saldo_efetivo (se qtd>0)
        peso_unit = (float(peso or 0) / qtd_saldo_efetivo) if qtd_saldo_efetivo else 0.0
        pallet_unit = (float(pallet or 0) / qtd_saldo_efetivo) if qtd_saldo_efetivo else 0.0

        itens.append({
            'cod_produto': cod,
            'nome_produto': item.nome_produto,
            'qtd_pedido': qtd_pedido,
            'qtd_faturada': qtd_faturada,
            'qtd_em_separacao': qtd_em_separacao,
            'qtd_saldo': qtd_saldo_efetivo,
            'qtd_saldo_banco': qtd_saldo_banco,  # referencia (debug)
            'preco_unitario': preco,
            'valor_pedido': valor_pedido,
            'valor_saldo': valor_saldo_efetivo,
            'peso_total': float(peso or 0),
            'pallet_total': float(pallet or 0),
            'peso_unit': peso_unit,           # usado por JS modo edicao
            'pallet_unit': pallet_unit,       # usado por JS modo edicao
            # Tooltip pre-formatado para template
            'tooltip_saldo': (
                f"Pedido: {qtd_pedido:.0f}  "
                f"−  Faturado: {qtd_faturada:.0f}  "
                f"−  Em separação: {qtd_em_separacao:.0f}  "
                f"=  Saldo: {qtd_saldo_efetivo:.0f}"
            ),
        })

        total_valor += valor_pedido
        total_valor_saldo += valor_saldo_efetivo
        total_peso += float(peso or 0)
        total_pallet += float(pallet or 0)
        total_qtd_pedido += qtd_pedido
        total_qtd_saldo += qtd_saldo_efetivo

    totais = {
        'qtd_itens': len(itens),
        'qtd_pedido_total': total_qtd_pedido,
        'qtd_saldo_total': total_qtd_saldo,
        'valor_pedido': total_valor,
        'valor_saldo': total_valor_saldo,
        'peso_total': total_peso,
        'pallet_total': total_pallet,
    }
    return itens, totais


def _carregar_qtd_faturada_por_produto(num_pedido: str) -> dict:
    """
    Retorna {cod_produto: qtd_faturada_total} para o pedido.
    Liga via FaturamentoProduto.origem == num_pedido.
    """
    rows = (
        db.session.query(
            FaturamentoProduto.cod_produto,
            func.sum(FaturamentoProduto.qtd_produto_faturado).label('qtd'),
        )
        .filter(FaturamentoProduto.origem == num_pedido)
        .group_by(FaturamentoProduto.cod_produto)
        .all()
    )
    return {r.cod_produto: float(r.qtd or 0) for r in rows}


def _carregar_qtd_em_separacao_por_produto(num_pedido: str) -> dict:
    """
    Retorna {cod_produto: qtd_total_em_separacoes_abertas} para o pedido.
    Conta apenas Separacao.sincronizado_nf=False (separacao ainda nao faturada).
    """
    rows = (
        db.session.query(
            Separacao.cod_produto,
            func.sum(Separacao.qtd_saldo).label('qtd'),
        )
        .filter(
            Separacao.num_pedido == num_pedido,
            Separacao.sincronizado_nf.is_(False),
        )
        .group_by(Separacao.cod_produto)
        .all()
    )
    return {r.cod_produto: float(r.qtd or 0) for r in rows}


def _carregar_separacoes(num_pedido: str) -> list[dict]:
    """
    Carrega separacoes ativas (nao faturadas) agregadas por separacao_lote_id.

    Cada lote inclui lista `items` com cada Separacao individual (id, cod_produto,
    nome_produto, qtd_saldo, valor_saldo, peso, pallet) — usado pela tela rica
    para permitir edicao de qtd item-a-item.

    Separacoes orfas (sem separacao_lote_id) sao agrupadas em chave fallback
    LOTE_ORFAO_<id> e logadas como warning.

    Retorna lista de lotes ordenada por expedicao.
    """
    seps = (
        db.session.query(Separacao)
        .filter(
            Separacao.num_pedido == num_pedido,
            Separacao.sincronizado_nf.is_(False),
        )
        .order_by(Separacao.expedicao.asc().nullslast())
        .all()
    )

    if not seps:
        return []

    lotes: dict = {}
    for sep in seps:
        lote_id = sep.separacao_lote_id
        if not lote_id:
            lote_id = f'LOTE_ORFAO_{sep.id}'
            logger.warning(
                f"[cmdk.pedido_completo] separacao orfa (sem lote_id): "
                f"num_pedido={num_pedido} sep_id={sep.id} cod_produto={sep.cod_produto}"
            )

        if lote_id not in lotes:
            lotes[lote_id] = {
                'lote_id': lote_id,
                'is_orfao': lote_id.startswith('LOTE_ORFAO_'),
                'tipo_envio': sep.tipo_envio or 'total',
                'expedicao': _fmt_data(sep.expedicao),
                'expedicao_iso': sep.expedicao.isoformat() if sep.expedicao else None,
                'agendamento': _fmt_data(sep.agendamento),
                'agendamento_iso': sep.agendamento.isoformat() if sep.agendamento else None,
                'agendamento_confirmado': bool(sep.agendamento_confirmado),
                'protocolo': sep.protocolo,
                'status': sep.status,
                'is_previsao': sep.status == 'PREVISAO',
                'qtd_itens': 0,
                'valor_total': 0.0,
                'peso_total': 0.0,
                'pallet_total': 0.0,
                'items': [],
            }
        lote = lotes[lote_id]
        lote['qtd_itens'] += 1

        qtd_item = float(sep.qtd_saldo or 0)
        valor_item = float(sep.valor_saldo or 0)
        peso_item = float(getattr(sep, 'peso', 0) or 0)
        pallet_item = float(getattr(sep, 'pallet', 0) or 0)

        lote['valor_total'] += valor_item
        lote['peso_total'] += peso_item
        lote['pallet_total'] += pallet_item

        lote['items'].append({
            'separacao_id': sep.id,
            'cod_produto': sep.cod_produto,
            'nome_produto': sep.nome_produto,
            'qtd_saldo': qtd_item,
            'valor_saldo': valor_item,
            'peso': peso_item,
            'pallet': pallet_item,
            'preco_unitario': (valor_item / qtd_item) if qtd_item else 0,
        })

    return sorted(
        lotes.values(),
        key=lambda x: (x.get('expedicao_iso') or '9999-12-31', x['lote_id']),
    )


def _carregar_nfs_faturadas(num_pedido: str) -> list[dict]:
    """
    Carrega NFs faturadas para o pedido, com status de entrega.

    Liga via FaturamentoProduto.origem == num_pedido (1 NF tem N produtos),
    agrega totais por numero_nf, faz LEFT JOIN com EntregaMonitorada
    (origem='NACOM') para enriquecer com status de entrega.

    Retorna lista ordenada por data_fatura desc.
    """
    rows = (
        db.session.query(
            FaturamentoProduto.numero_nf.label('numero_nf'),
            func.max(FaturamentoProduto.data_fatura).label('data_fatura'),
            func.sum(FaturamentoProduto.valor_produto_faturado).label('valor_total'),
            func.sum(FaturamentoProduto.peso_total).label('peso_total'),
            func.count(FaturamentoProduto.id).label('qtd_itens'),
            func.max(FaturamentoProduto.status_nf).label('status_nf'),
            func.bool_or(FaturamentoProduto.revertida).label('revertida'),
            func.max(EntregaMonitorada.transportadora).label('transportadora'),
            func.max(EntregaMonitorada.data_embarque).label('data_embarque'),
            func.max(EntregaMonitorada.data_entrega_prevista).label('data_entrega_prevista'),
            func.max(EntregaMonitorada.data_hora_entrega_realizada).label('data_entrega_realizada'),
            func.max(EntregaMonitorada.data_agenda).label('data_agenda'),
            func.bool_or(EntregaMonitorada.entregue).label('entregue'),
            func.bool_or(EntregaMonitorada.nf_cd).label('nf_cd'),
            func.max(EntregaMonitorada.lead_time).label('lead_time'),
        )
        .outerjoin(
            EntregaMonitorada,
            db.and_(
                EntregaMonitorada.numero_nf == FaturamentoProduto.numero_nf,
                EntregaMonitorada.origem == 'NACOM',
            ),
        )
        .filter(FaturamentoProduto.origem == num_pedido)
        .group_by(FaturamentoProduto.numero_nf)
        .order_by(func.max(FaturamentoProduto.data_fatura).desc().nullslast())
        .all()
    )

    out = []
    for row in rows:
        out.append({
            'numero_nf': row.numero_nf,
            'data_fatura': _fmt_data(row.data_fatura),
            'valor_total': float(row.valor_total or 0),
            'peso_total': float(row.peso_total or 0),
            'qtd_itens': int(row.qtd_itens or 0),
            'status_nf': row.status_nf,
            'revertida': bool(row.revertida),
            'transportadora': row.transportadora,
            'data_embarque': _fmt_data(row.data_embarque),
            'data_entrega_prevista': _fmt_data(row.data_entrega_prevista),
            'data_entrega_realizada': _fmt_data(row.data_entrega_realizada),
            'data_agenda': _fmt_data(row.data_agenda),
            'lead_time': row.lead_time,
            'entrega_badge': _badge_entrega(row),
            'url_monitoramento': f'/monitoramento/listar_entregas?numero_nf={row.numero_nf}',
        })
    return out


def _badge_entrega(row) -> Optional[dict]:
    """Mapeia status de EntregaMonitorada (do row) para badge {label, tone}."""
    if row.revertida:
        return {'label': 'Revertida', 'tone': 'danger'}
    if row.entregue:
        return {'label': 'Entregue', 'tone': 'success'}
    if row.nf_cd:
        return {'label': 'No CD', 'tone': 'warning'}
    if row.data_embarque:
        return {'label': 'Em trânsito', 'tone': 'info'}
    if row.data_fatura:
        return {'label': 'Faturada', 'tone': 'secondary'}
    return None


def _fmt_data(d) -> Optional[str]:
    """Formata date como dd/mm/aaaa."""
    if not d:
        return None
    try:
        return d.strftime('%d/%m/%Y')
    except (AttributeError, ValueError):
        return None


def _badge_status(status: Optional[str]) -> Optional[dict]:
    if not status:
        return None
    s = status.strip().lower()
    if 'cancel' in s:
        return {'label': 'Cancelado', 'tone': 'danger'}
    if 'cota' in s:
        return {'label': 'Cotação', 'tone': 'warning'}
    if 'venda' in s:
        return {'label': 'Pedido de venda', 'tone': 'success'}
    return {'label': status[:30], 'tone': 'secondary'}
