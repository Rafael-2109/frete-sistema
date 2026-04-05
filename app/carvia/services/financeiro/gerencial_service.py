"""
GerencialService — Metricas analiticas do modulo CarVia
========================================================

Agrega valor por UF/mes, valor por unidade (moto), valor por kg cubado.
Usado pela tela gerencial (admin-only) e pelo card de faturamento no dashboard.
"""

import logging
from collections import defaultdict
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import func

from app import db

logger = logging.getLogger(__name__)

ZERO = Decimal('0')


def _build_nf_peso_subquery(alias='nf_peso'):
    """Subquery: peso bruto total das NFs por operacao (fallback para peso_cubado)."""
    from app.carvia.models import CarviaNf, CarviaOperacaoNf

    return (
        db.session.query(
            CarviaOperacaoNf.operacao_id,
            func.coalesce(
                func.sum(CarviaNf.peso_bruto), 0
            ).label('total_peso_bruto'),
        )
        .join(CarviaNf, CarviaNf.id == CarviaOperacaoNf.nf_id)
        .group_by(CarviaOperacaoNf.operacao_id)
        .subquery(alias)
    )


def _build_moto_count_subquery(alias='moto_count'):
    """Subquery: contagem de veiculos (motos) por operacao via CarviaNfVeiculo.

    Apenas operacoes cujas NFs tem registros em carvia_nf_veiculos (chassis)
    sao consideradas 'moto'. COUNT(veiculo.id) = numero real de motos.
    """
    from app.carvia.models import CarviaOperacaoNf, CarviaNfVeiculo

    return (
        db.session.query(
            CarviaOperacaoNf.operacao_id,
            func.count(CarviaNfVeiculo.id).label('qtd_veiculos'),
        )
        .join(CarviaNfVeiculo, CarviaNfVeiculo.nf_id == CarviaOperacaoNf.nf_id)
        .group_by(CarviaOperacaoNf.operacao_id)
        .subquery(alias)
    )


def _build_moto_count_per_nf_subquery(alias='moto_nf'):
    """Subquery: contagem de veiculos (motos) por NF via CarviaNfVeiculo."""
    from app.carvia.models import CarviaNfVeiculo

    return (
        db.session.query(
            CarviaNfVeiculo.nf_id,
            func.count(CarviaNfVeiculo.id).label('qtd_motos'),
        )
        .group_by(CarviaNfVeiculo.nf_id)
        .subquery(alias)
    )


def _calcular_metricas(valor_total_raw, qtd_motos_raw, peso_cubado_raw, peso_bruto_nfs_raw):
    """Calcula peso efetivo, valor/unidade e valor/kg cubado a partir dos totais.

    qtd_motos: contagem real de veiculos (chassis) — se 0, mostra N/A.
    """
    valor_total = Decimal(str(valor_total_raw)) if valor_total_raw else ZERO
    qtd_motos = int(qtd_motos_raw or 0)
    peso_cubado_total = Decimal(str(peso_cubado_raw)) if peso_cubado_raw else ZERO
    peso_bruto_nfs = Decimal(str(peso_bruto_nfs_raw)) if peso_bruto_nfs_raw else ZERO

    # Peso efetivo: cubado se > 0, senao peso bruto das NFs
    peso_efetivo = peso_cubado_total if peso_cubado_total > 0 else peso_bruto_nfs

    return {
        'valor_total': valor_total,
        'qtd_motos': qtd_motos,
        'peso_efetivo': peso_efetivo,
        'valor_por_unidade': (valor_total / qtd_motos) if qtd_motos > 0 else None,
        'valor_por_kg_cubado': (valor_total / peso_efetivo) if peso_efetivo > 0 else None,
    }


def _mes_label(dt):
    """Converte datetime truncado para label YYYY-MM."""
    if dt is None:
        return 'Sem data'
    return dt.strftime('%Y-%m')


class GerencialService:

    # ── Tela Gerencial ──────────────────────────────────────────────

    def obter_metricas_por_uf_mes(self, data_inicio, data_fim):
        """
        Retorna metricas agregadas por UF destino + mes.

        Cada item:
            uf_destino, mes_label (YYYY-MM), valor_total,
            qtd_motos, peso_efetivo,
            valor_por_unidade (ou None), valor_por_kg_cubado (ou None)

        Regras:
        - Exclui status CANCELADO e registros sem UF/data
        - qtd_motos = COUNT(CarviaNfVeiculo.id) — so operacoes com motos identificadas
        - peso_efetivo = peso_cubado_total se > 0, senao peso_bruto_nfs_total
        - Sem motos identificadas → valor_por_unidade = None (N/A)
        - Divisao por zero → None (template exibe N/A)
        """
        from app.carvia.models import CarviaOperacao

        nf_peso = _build_nf_peso_subquery('nf_peso')
        moto_count = _build_moto_count_subquery('moto_count')

        mes_trunc = func.date_trunc(
            'month', CarviaOperacao.cte_data_emissao
        ).label('mes')

        rows = (
            db.session.query(
                CarviaOperacao.uf_destino,
                mes_trunc,
                func.coalesce(func.sum(CarviaOperacao.cte_valor), 0).label('valor_total'),
                func.coalesce(func.sum(moto_count.c.qtd_veiculos), 0).label('qtd_motos'),
                func.coalesce(func.sum(CarviaOperacao.peso_cubado), 0).label('peso_cubado_total'),
                func.coalesce(func.sum(nf_peso.c.total_peso_bruto), 0).label('peso_bruto_nfs_total'),
            )
            .outerjoin(nf_peso, nf_peso.c.operacao_id == CarviaOperacao.id)
            .outerjoin(moto_count, moto_count.c.operacao_id == CarviaOperacao.id)
            .filter(
                CarviaOperacao.status != 'CANCELADO',
                CarviaOperacao.cte_data_emissao.isnot(None),
                CarviaOperacao.uf_destino.isnot(None),
                CarviaOperacao.cte_data_emissao >= data_inicio,
                CarviaOperacao.cte_data_emissao <= data_fim,
            )
            .group_by(CarviaOperacao.uf_destino, mes_trunc)
            .order_by(mes_trunc.desc(), CarviaOperacao.uf_destino)
            .all()
        )

        resultado = []
        for row in rows:
            metricas = _calcular_metricas(
                row.valor_total, row.qtd_motos,
                row.peso_cubado_total, row.peso_bruto_nfs_total,
            )
            metricas['uf_destino'] = row.uf_destino
            metricas['mes_label'] = _mes_label(row.mes)
            resultado.append(metricas)

        return resultado

    def obter_totais_periodo(self, data_inicio, data_fim):
        """
        Retorna totais agregados do periodo (sem breakdown por UF/mes).

        Returns:
            dict com valor_total, qtd_motos, peso_efetivo,
                 valor_por_unidade, valor_por_kg_cubado, total_despesas
        """
        from app.carvia.models import CarviaOperacao, CarviaDespesa

        nf_peso = _build_nf_peso_subquery('nf_peso_totais')
        moto_count = _build_moto_count_subquery('moto_count_totais')

        row = (
            db.session.query(
                func.coalesce(func.sum(CarviaOperacao.cte_valor), 0).label('valor_total'),
                func.coalesce(func.sum(moto_count.c.qtd_veiculos), 0).label('qtd_motos'),
                func.coalesce(func.sum(CarviaOperacao.peso_cubado), 0).label('peso_cubado_total'),
                func.coalesce(func.sum(nf_peso.c.total_peso_bruto), 0).label('peso_bruto_nfs_total'),
            )
            .outerjoin(nf_peso, nf_peso.c.operacao_id == CarviaOperacao.id)
            .outerjoin(moto_count, moto_count.c.operacao_id == CarviaOperacao.id)
            .filter(
                CarviaOperacao.status != 'CANCELADO',
                CarviaOperacao.cte_data_emissao.isnot(None),
                CarviaOperacao.cte_data_emissao >= data_inicio,
                CarviaOperacao.cte_data_emissao <= data_fim,
            )
            .one()
        )

        totais = _calcular_metricas(
            row.valor_total, row.qtd_motos,
            row.peso_cubado_total, row.peso_bruto_nfs_total,
        )

        # Despesas do periodo (sem FK para operacao — total geral)
        # Exclui categoria DESCONSIDERAR (nao entra no calculo gerencial)
        total_despesas = db.session.query(
            func.coalesce(func.sum(CarviaDespesa.valor), 0)
        ).filter(
            CarviaDespesa.status != 'CANCELADO',
            CarviaDespesa.tipo_despesa != 'DESCONSIDERAR',
            CarviaDespesa.data_despesa >= data_inicio,
            CarviaDespesa.data_despesa <= data_fim,
        ).scalar() or ZERO

        totais['total_despesas'] = Decimal(str(total_despesas))

        return totais

    # ── Aba Itens NF × CTe ───────────────────────────────────────────

    def obter_itens_nf_com_rateio(self, data_inicio, data_fim):
        """
        Retorna itens de NF com rateio do CTe distribuido ate nivel de item.

        Algoritmo em 2 etapas:
          1. NF-level: cascata [motos → peso → qtd_nfs] para distribuir cte_valor entre NFs
          2. Item-level: distribui share da NF entre itens por proporcao de quantidade

        Filtro: NFs ATIVAS vinculadas a CTes nao-cancelados no periodo.

        Returns:
            list[dict] com campos de item + NF + CTe + rateio_nf + rateio_item + criterio
        """
        from app.carvia.models import (
            CarviaNf, CarviaNfItem, CarviaOperacao, CarviaOperacaoNf,
            CarviaModeloMoto,
        )

        moto_nf = _build_moto_count_per_nf_subquery('moto_nf_itens')

        rows = (
            db.session.query(
                CarviaNfItem.id.label('item_id'),
                CarviaNfItem.codigo_produto,
                CarviaNfItem.descricao.label('descricao_item'),
                CarviaNfItem.quantidade,
                CarviaNfItem.valor_unitario,
                CarviaNfItem.valor_total_item,
                CarviaModeloMoto.nome.label('modelo_moto_nome'),
                CarviaModeloMoto.cubagem_minima.label('peso_cubado_modelo'),
                CarviaNf.id.label('nf_id'),
                CarviaNf.numero_nf,
                CarviaNf.serie_nf,
                CarviaNf.data_emissao.label('data_nf'),
                CarviaNf.nome_emitente,
                CarviaNf.cnpj_emitente,
                CarviaNf.nome_destinatario,
                CarviaNf.uf_destinatario,
                CarviaNf.cidade_destinatario,
                CarviaNf.peso_bruto,
                CarviaOperacao.id.label('operacao_id'),
                CarviaOperacao.cte_numero,
                CarviaOperacao.cte_valor,
                CarviaOperacao.cte_data_emissao.label('data_cte'),
                CarviaOperacao.status.label('status_operacao'),
                func.coalesce(moto_nf.c.qtd_motos, 0).label('qtd_motos_nf'),
            )
            .join(CarviaNf, CarviaNf.id == CarviaNfItem.nf_id)
            .join(CarviaOperacaoNf, CarviaOperacaoNf.nf_id == CarviaNf.id)
            .join(CarviaOperacao, CarviaOperacao.id == CarviaOperacaoNf.operacao_id)
            .outerjoin(CarviaModeloMoto, CarviaModeloMoto.id == CarviaNfItem.modelo_moto_id)
            .outerjoin(moto_nf, moto_nf.c.nf_id == CarviaNf.id)
            .filter(
                CarviaNf.status == 'ATIVA',
                CarviaOperacao.status != 'CANCELADO',
                CarviaOperacao.cte_data_emissao.isnot(None),
                CarviaOperacao.cte_data_emissao >= data_inicio,
                CarviaOperacao.cte_data_emissao <= data_fim,
            )
            .order_by(
                CarviaNf.data_emissao.desc().nullslast(),
                CarviaNf.numero_nf,
                CarviaNfItem.id,
            )
            .all()
        )

        return self._aplicar_rateio_itens(rows)

    def _aplicar_rateio_itens(self, rows):
        """Aplica rateio cascateado [motos → peso → qtd_nfs] ate nivel de item.

        Etapa 1: distribui cte_valor entre NFs do mesmo CTe.
        Etapa 2: distribui share da NF entre itens por proporcao de quantidade.
        """
        # Agrupar por operacao (CTe)
        by_op = defaultdict(list)
        for r in rows:
            by_op[r.operacao_id].append({
                'item_id': r.item_id,
                'codigo_produto': r.codigo_produto,
                'descricao_item': r.descricao_item,
                'quantidade': float(r.quantidade) if r.quantidade else 0,
                'valor_unitario': float(r.valor_unitario) if r.valor_unitario else None,
                'valor_total_item': float(r.valor_total_item) if r.valor_total_item else None,
                'modelo_moto_nome': r.modelo_moto_nome,
                'peso_cubado_modelo': float(r.peso_cubado_modelo) if r.peso_cubado_modelo else None,
                'nf_id': r.nf_id,
                'numero_nf': r.numero_nf,
                'serie_nf': r.serie_nf,
                'data_nf': r.data_nf,
                'nome_emitente': r.nome_emitente,
                'cnpj_emitente': r.cnpj_emitente,
                'nome_destinatario': r.nome_destinatario,
                'uf_destinatario': r.uf_destinatario,
                'cidade_destinatario': r.cidade_destinatario,
                'peso_bruto': float(r.peso_bruto) if r.peso_bruto else 0,
                'operacao_id': r.operacao_id,
                'cte_numero': r.cte_numero,
                'cte_valor': float(r.cte_valor) if r.cte_valor else 0,
                'data_cte': r.data_cte,
                'status_operacao': r.status_operacao,
                'qtd_motos_nf': int(r.qtd_motos_nf or 0),
            })

        resultado = []

        for op_id, items in by_op.items():
            cte_valor = Decimal(str(items[0]['cte_valor']))

            # --- Etapa 1: NF-level rateio ---
            # Agrupar itens por NF
            nfs = {}
            for item in items:
                nf_id = item['nf_id']
                if nf_id not in nfs:
                    nfs[nf_id] = {
                        'qtd_motos': item['qtd_motos_nf'],
                        'peso_bruto': Decimal(str(item['peso_bruto'])),
                        'items': [],
                    }
                nfs[nf_id]['items'].append(item)

            nf_list = list(nfs.values())
            total_motos = sum(n['qtd_motos'] for n in nf_list)
            total_peso = sum(n['peso_bruto'] for n in nf_list)

            # Determinar criterio e share por NF
            if len(nf_list) == 1:
                criterio = 'Direto (1:1)'
                nf_list[0]['nf_share'] = cte_valor
            elif total_motos > 0:
                criterio = 'Motos'
                for n in nf_list:
                    prop = Decimal(str(n['qtd_motos'])) / Decimal(str(total_motos))
                    n['nf_share'] = (cte_valor * prop).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP,
                    )
            elif total_peso > 0:
                criterio = 'Peso'
                for n in nf_list:
                    prop = n['peso_bruto'] / total_peso
                    n['nf_share'] = (cte_valor * prop).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP,
                    )
            else:
                criterio = 'Qtd NFs'
                valor_por_nf = cte_valor / len(nf_list)
                for n in nf_list:
                    n['nf_share'] = valor_por_nf.quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP,
                    )

            # Ajuste de centavos no nivel NF
            if len(nf_list) > 1:
                soma_nf = sum(n['nf_share'] for n in nf_list)
                diff_nf = cte_valor - soma_nf
                if diff_nf != 0:
                    nf_list[0]['nf_share'] += diff_nf

            # Calcular valor por unidade|kg do CTe
            if criterio in ('Motos', 'Direto (1:1)') and total_motos > 0:
                valor_por_unidade_kg = float(
                    (cte_valor / Decimal(str(total_motos))).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP,
                    )
                )
                unidade_label = 'R$/Unid'
            elif total_peso > 0:
                valor_por_unidade_kg = float(
                    (cte_valor / total_peso).quantize(
                        Decimal('0.01'), rounding=ROUND_HALF_UP,
                    )
                )
                unidade_label = 'R$/Kg'
            else:
                valor_por_unidade_kg = None
                unidade_label = None

            # --- Etapa 2: Item-level rateio dentro de cada NF ---
            for n in nf_list:
                nf_share = n['nf_share']
                nf_items = n['items']
                total_qty = sum(
                    Decimal(str(i['quantidade'])) for i in nf_items
                )

                if total_qty > 0:
                    for item in nf_items:
                        item_qty = Decimal(str(item['quantidade']))
                        prop = item_qty / total_qty
                        item['rateio_nf'] = float(nf_share)
                        item['rateio_item'] = float(
                            (nf_share * prop).quantize(
                                Decimal('0.01'), rounding=ROUND_HALF_UP,
                            )
                        )
                        item['criterio_rateio'] = criterio
                        item['valor_por_unidade_kg'] = valor_por_unidade_kg
                        item['unidade_label'] = unidade_label

                    # Ajuste de centavos no nivel item
                    soma_it = sum(
                        Decimal(str(i['rateio_item'])) for i in nf_items
                    )
                    diff_it = nf_share - soma_it
                    if diff_it != 0:
                        nf_items[0]['rateio_item'] = float(
                            Decimal(str(nf_items[0]['rateio_item'])) + diff_it
                        )
                else:
                    # Sem quantidade — divisao igual entre itens
                    share = float(nf_share / len(nf_items)) if nf_items else 0
                    for item in nf_items:
                        item['rateio_nf'] = float(nf_share)
                        item['rateio_item'] = share
                        item['criterio_rateio'] = criterio
                        item['valor_por_unidade_kg'] = valor_por_unidade_kg
                        item['unidade_label'] = unidade_label

                resultado.extend(nf_items)

        # Ordenar: data NF desc, numero NF asc, item_id asc
        resultado.sort(key=lambda r: (
            -(r['data_nf'].toordinal() if r.get('data_nf') else 0),
            r.get('numero_nf') or '',
            r.get('item_id') or 0,
        ))

        return resultado

    # ── Card Dashboard ──────────────────────────────────────────────

    def obter_faturamento_comparativo(self):
        """
        Retorna faturamento (SUM cte_valor) do mes atual vs mes anterior.

        Returns:
            dict com mes_atual, mes_anterior, variacao_pct (float|None)
        """
        from app.carvia.models import CarviaOperacao
        from app.utils.timezone import agora_brasil_naive

        hoje = agora_brasil_naive().date()
        primeiro_dia_mes_atual = hoje.replace(day=1)

        # Mes anterior: primeiro dia do mes anterior
        if primeiro_dia_mes_atual.month == 1:
            primeiro_dia_mes_anterior = primeiro_dia_mes_atual.replace(
                year=primeiro_dia_mes_atual.year - 1, month=12
            )
        else:
            primeiro_dia_mes_anterior = primeiro_dia_mes_atual.replace(
                month=primeiro_dia_mes_atual.month - 1
            )

        filtro_base = CarviaOperacao.status != 'CANCELADO'

        # Mes atual (com upper bound para excluir CTes com data futura)
        mes_atual = db.session.query(
            func.coalesce(func.sum(CarviaOperacao.cte_valor), 0)
        ).filter(
            filtro_base,
            CarviaOperacao.cte_data_emissao >= primeiro_dia_mes_atual,
            CarviaOperacao.cte_data_emissao <= hoje,
        ).scalar() or ZERO

        # Mes anterior
        mes_anterior = db.session.query(
            func.coalesce(func.sum(CarviaOperacao.cte_valor), 0)
        ).filter(
            filtro_base,
            CarviaOperacao.cte_data_emissao >= primeiro_dia_mes_anterior,
            CarviaOperacao.cte_data_emissao < primeiro_dia_mes_atual,
        ).scalar() or ZERO

        mes_atual = Decimal(str(mes_atual))
        mes_anterior = Decimal(str(mes_anterior))

        # Variacao percentual
        if mes_anterior > 0:
            variacao_pct = float(
                ((mes_atual - mes_anterior) / mes_anterior) * 100
            )
        else:
            variacao_pct = None

        return {
            'mes_atual': mes_atual,
            'mes_anterior': mes_anterior,
            'variacao_pct': variacao_pct,
        }
