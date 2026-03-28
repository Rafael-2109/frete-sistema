"""
GerencialService — Metricas analiticas do modulo CarVia
========================================================

Agrega valor por UF/mes, valor por unidade (moto), valor por kg cubado.
Usado pela tela gerencial (admin-only) e pelo card de faturamento no dashboard.
"""

import logging
from decimal import Decimal

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
        total_despesas = db.session.query(
            func.coalesce(func.sum(CarviaDespesa.valor), 0)
        ).filter(
            CarviaDespesa.status != 'CANCELADO',
            CarviaDespesa.data_despesa >= data_inicio,
            CarviaDespesa.data_despesa <= data_fim,
        ).scalar() or ZERO

        totais['total_despesas'] = Decimal(str(total_despesas))

        return totais

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
