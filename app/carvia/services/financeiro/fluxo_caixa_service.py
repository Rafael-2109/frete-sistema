"""
Fluxo de Caixa CarVia — Service
================================

Consolida fontes de dados financeiros em visao diaria:
- A Receber: carvia_faturas_cliente (status != CANCELADA) + carvia_receitas (status != CANCELADO)
- A Pagar: carvia_faturas_transportadora (todas) + carvia_despesas (status != CANCELADO)

Agrupamento por data de vencimento com saldo acumulado progressivo.

Saldo de conta: calculado por SUM de carvia_conta_movimentacoes (sem cache).
"""

import logging
from collections import defaultdict
from decimal import Decimal

from sqlalchemy import func, case

from app import db

logger = logging.getLogger(__name__)

# Mapeamento dia da semana (Python weekday) -> portugues
DIAS_SEMANA = {
    0: 'Seg',
    1: 'Ter',
    2: 'Qua',
    3: 'Qui',
    4: 'Sex',
    5: 'Sab',
    6: 'Dom',
}


class FluxoCaixaService:
    """Consolida fluxo de caixa de todas as fontes CarVia."""

    def obter_fluxo(self, data_inicio, data_fim, filtro_status='total'):
        """
        Retorna fluxo de caixa agrupado por dia.

        Args:
            data_inicio: date - inicio do periodo
            data_fim: date - fim do periodo
            filtro_status: 'total' | 'pendente' | 'pago'

        Returns:
            dict com 'dias' (lista ordenada) e 'totais'
        """
        from app.carvia.models import (
            CarviaFaturaCliente,
            CarviaFaturaTransportadora,
            CarviaDespesa,
            CarviaCustoEntrega,
            CarviaReceita,
        )

        # Coletar lancamentos de cada fonte
        lancamentos_receber = self._buscar_faturas_cliente(
            CarviaFaturaCliente, data_inicio, data_fim, filtro_status
        )
        lancamentos_receber_receitas = self._buscar_receitas(
            CarviaReceita, data_inicio, data_fim, filtro_status
        )
        lancamentos_pagar_transp = self._buscar_faturas_transportadora(
            CarviaFaturaTransportadora, data_inicio, data_fim, filtro_status
        )
        lancamentos_pagar_desp = self._buscar_despesas(
            CarviaDespesa, data_inicio, data_fim, filtro_status
        )
        lancamentos_pagar_custos = self._buscar_custos_entrega(
            CarviaCustoEntrega, data_inicio, data_fim, filtro_status
        )

        # Agrupar por data de vencimento
        dias_receber = defaultdict(list)
        dias_pagar = defaultdict(list)

        for lanc in lancamentos_receber + lancamentos_receber_receitas:
            dias_receber[lanc['vencimento']].append(lanc)

        for lanc in lancamentos_pagar_transp + lancamentos_pagar_desp + lancamentos_pagar_custos:
            dias_pagar[lanc['vencimento']].append(lanc)

        # Coletar todas as datas com lancamentos
        todas_datas = sorted(
            set(dias_receber.keys()) | set(dias_pagar.keys())
        )

        # Montar resultado por dia com saldo acumulado
        resultado_dias = []
        saldo_acumulado = 0.0
        total_receber = 0.0
        total_pagar = 0.0

        for dt in todas_datas:
            receber_dia = dias_receber.get(dt, [])
            pagar_dia = dias_pagar.get(dt, [])

            soma_receber = sum(l['valor'] for l in receber_dia)
            soma_pagar = sum(l['valor'] for l in pagar_dia)
            saldo_dia = soma_receber - soma_pagar
            saldo_acumulado += saldo_dia

            total_receber += soma_receber
            total_pagar += soma_pagar

            resultado_dias.append({
                'data': dt,
                'data_str': dt.strftime('%d/%m/%Y'),
                'dia_semana': DIAS_SEMANA.get(dt.weekday(), ''),
                'a_receber': soma_receber,
                'a_pagar': soma_pagar,
                'saldo_dia': saldo_dia,
                'saldo_acumulado': saldo_acumulado,
                'lancamentos_receber': receber_dia,
                'lancamentos_pagar': pagar_dia,
            })

        return {
            'dias': resultado_dias,
            'totais': {
                'a_receber': total_receber,
                'a_pagar': total_pagar,
                'saldo_liquido': total_receber - total_pagar,
                'total_dias': len(resultado_dias),
            },
        }

    def _buscar_faturas_cliente(self, model, data_inicio, data_fim, filtro_status):
        """Busca faturas cliente (a receber) no periodo."""
        query = db.session.query(model).filter(
            model.vencimento >= data_inicio,
            model.vencimento <= data_fim,
            model.status != 'CANCELADA',
        )

        if filtro_status == 'pago':
            query = query.filter(model.status == 'PAGA')
        elif filtro_status == 'pendente':
            query = query.filter(model.status != 'PAGA')

        faturas = query.order_by(model.vencimento, model.id).all()

        resultado = []
        for f in faturas:
            resultado.append({
                'tipo_doc': 'fatura_cliente',
                'tipo_label': 'Fatura CarVia',
                'id': f.id,
                'vencimento': f.vencimento,
                'emissao': f.data_emissao,
                'fornecedor': f.nome_cliente or f.cnpj_cliente or '-',
                'documento': f.numero_fatura,
                'valor': float(f.valor_total or 0),
                'pago': f.status == 'PAGA',
                'status': f.status,
                'url_detalhe': f'/carvia/faturas-cliente/{f.id}',
            })

        return resultado

    def _buscar_faturas_transportadora(self, model, data_inicio, data_fim, filtro_status):
        """Busca faturas transportadora (a pagar) no periodo."""
        query = db.session.query(model).filter(
            model.vencimento >= data_inicio,
            model.vencimento <= data_fim,
        )

        if filtro_status == 'pago':
            query = query.filter(model.status_pagamento == 'PAGO')
        elif filtro_status == 'pendente':
            query = query.filter(model.status_pagamento == 'PENDENTE')

        # transportadora ja usa lazy='joined' no model (models.py:550)
        faturas = query.order_by(model.vencimento, model.id).all()

        resultado = []
        for f in faturas:
            nome_transp = '-'
            if f.transportadora:
                nome_transp = f.transportadora.razao_social or '-'

            resultado.append({
                'tipo_doc': 'fatura_transportadora',
                'tipo_label': 'Fatura Subcontrato',
                'id': f.id,
                'vencimento': f.vencimento,
                'emissao': f.data_emissao,
                'fornecedor': nome_transp,
                'documento': f.numero_fatura,
                'valor': float(f.valor_total or 0),
                'pago': f.status_pagamento == 'PAGO',
                'status': f.status_pagamento,
                'url_detalhe': f'/carvia/faturas-transportadora/{f.id}',
            })

        return resultado

    def _buscar_despesas(self, model, data_inicio, data_fim, filtro_status):
        """Busca despesas (a pagar) no periodo."""
        query = db.session.query(model).filter(
            model.data_vencimento >= data_inicio,
            model.data_vencimento <= data_fim,
            model.status != 'CANCELADO',
        )

        if filtro_status == 'pago':
            query = query.filter(model.status == 'PAGO')
        elif filtro_status == 'pendente':
            query = query.filter(model.status == 'PENDENTE')

        despesas = query.order_by(model.data_vencimento, model.id).all()

        resultado = []
        for d in despesas:
            resultado.append({
                'tipo_doc': 'despesa',
                'tipo_label': d.tipo_despesa or 'Despesa',
                'id': d.id,
                'vencimento': d.data_vencimento,
                'emissao': d.data_despesa,
                'fornecedor': d.descricao or '-',
                'documento': str(d.id),
                'valor': float(d.valor or 0),
                'pago': d.status == 'PAGO',
                'status': d.status,
                'url_detalhe': f'/carvia/despesas/{d.id}',
            })

        return resultado

    def _buscar_receitas(self, model, data_inicio, data_fim, filtro_status):
        """Busca receitas (a receber) no periodo."""
        query = db.session.query(model).filter(
            model.data_vencimento >= data_inicio,
            model.data_vencimento <= data_fim,
            model.status != 'CANCELADO',
        )

        if filtro_status == 'pago':
            query = query.filter(model.status == 'RECEBIDO')
        elif filtro_status == 'pendente':
            query = query.filter(model.status == 'PENDENTE')

        receitas = query.order_by(model.data_vencimento, model.id).all()

        resultado = []
        for r in receitas:
            resultado.append({
                'tipo_doc': 'receita',
                'tipo_label': r.tipo_receita or 'Receita',
                'id': r.id,
                'vencimento': r.data_vencimento,
                'emissao': r.data_receita,
                'fornecedor': r.descricao or '-',
                'documento': str(r.id),
                'valor': float(r.valor or 0),
                'pago': r.status == 'RECEBIDO',
                'status': r.status,
                'url_detalhe': f'/carvia/receitas/{r.id}',
            })

        return resultado

    def _buscar_custos_entrega(self, model, data_inicio, data_fim, filtro_status):
        """Busca custos de entrega (a pagar) no periodo."""
        query = db.session.query(model).filter(
            model.data_vencimento >= data_inicio,
            model.data_vencimento <= data_fim,
            model.status != 'CANCELADO',
        )

        if filtro_status == 'pago':
            query = query.filter(model.status == 'PAGO')
        elif filtro_status == 'pendente':
            query = query.filter(model.status == 'PENDENTE')

        custos = query.order_by(model.data_vencimento, model.id).all()

        resultado = []
        for c in custos:
            resultado.append({
                'tipo_doc': 'custo_entrega',
                'tipo_label': c.tipo_custo or 'Custo Entrega',
                'id': c.id,
                'vencimento': c.data_vencimento,
                'emissao': c.data_custo,
                'fornecedor': c.fornecedor_nome or c.descricao or '-',
                'documento': c.numero_custo,
                'valor': float(c.valor or 0),
                'pago': c.status == 'PAGO',
                'status': c.status,
                'url_detalhe': f'/carvia/custos-entrega/{c.id}',
            })

        return resultado

    def obter_lista_corrida(self, data_inicio, data_fim, filtro_status='total', filtro_direcao='todos'):
        """
        Retorna lista plana de lancamentos ordenados por vencimento.

        Args:
            data_inicio: date
            data_fim: date
            filtro_status: 'total' | 'pendente' | 'pago'
            filtro_direcao: 'todos' | 'receber' | 'pagar'

        Returns:
            dict com 'lancamentos' (lista plana) e 'totais'
        """
        from app.carvia.models import (
            CarviaFaturaCliente,
            CarviaFaturaTransportadora,
            CarviaDespesa,
            CarviaCustoEntrega,
            CarviaReceita,
        )

        lancamentos = []
        total_receber = 0.0
        total_pagar = 0.0

        # A Receber
        if filtro_direcao in ('todos', 'receber'):
            receber = self._buscar_faturas_cliente(
                CarviaFaturaCliente, data_inicio, data_fim, filtro_status
            )
            receber_receitas = self._buscar_receitas(
                CarviaReceita, data_inicio, data_fim, filtro_status
            )
            for l in receber + receber_receitas:
                l['direcao'] = 'A Receber'
                lancamentos.append(l)
                total_receber += l['valor']

        # A Pagar
        if filtro_direcao in ('todos', 'pagar'):
            pagar_transp = self._buscar_faturas_transportadora(
                CarviaFaturaTransportadora, data_inicio, data_fim, filtro_status
            )
            pagar_desp = self._buscar_despesas(
                CarviaDespesa, data_inicio, data_fim, filtro_status
            )
            pagar_custos = self._buscar_custos_entrega(
                CarviaCustoEntrega, data_inicio, data_fim, filtro_status
            )
            for l in pagar_transp + pagar_desp + pagar_custos:
                l['direcao'] = 'A Pagar'
                lancamentos.append(l)
                total_pagar += l['valor']

        # Ordenar por vencimento, depois por id
        lancamentos.sort(key=lambda x: (x['vencimento'], x['id']))

        return {
            'lancamentos': lancamentos,
            'totais': {
                'a_receber': total_receber,
                'a_pagar': total_pagar,
                'saldo_liquido': total_receber - total_pagar,
                'total_dias': len(set(l['vencimento'] for l in lancamentos)),
            },
        }

    # ===================================================================
    # Saldo de Conta
    # ===================================================================

    def obter_saldo_conta(self):
        """
        Calcula saldo atual da conta por SUM de movimentacoes.

        Returns:
            float — saldo (positivo = credito liquido)
        """
        from app.carvia.models import CarviaContaMovimentacao

        resultado = db.session.query(
            func.coalesce(
                func.sum(
                    case(
                        (CarviaContaMovimentacao.tipo_movimento == 'CREDITO',
                         CarviaContaMovimentacao.valor),
                        else_=-CarviaContaMovimentacao.valor,
                    )
                ),
                Decimal('0'),
            )
        ).scalar()

        return float(resultado)

    def obter_extrato(self, data_inicio, data_fim):
        """
        Monta extrato da conta com saldo acumulado progressivo.

        Args:
            data_inicio: date — inicio do periodo
            data_fim: date — fim do periodo (inclusive)

        Returns:
            dict com saldo_anterior, movimentacoes, saldo_final,
            total_creditos, total_debitos
        """
        from app.carvia.models import CarviaContaMovimentacao

        # Converter date → datetime para comparacao com TIMESTAMP
        from datetime import datetime, time

        dt_inicio = datetime.combine(data_inicio, time.min)
        dt_fim = datetime.combine(data_fim, time(23, 59, 59))

        # Saldo anterior (tudo antes de data_inicio)
        saldo_anterior_result = db.session.query(
            func.coalesce(
                func.sum(
                    case(
                        (CarviaContaMovimentacao.tipo_movimento == 'CREDITO',
                         CarviaContaMovimentacao.valor),
                        else_=-CarviaContaMovimentacao.valor,
                    )
                ),
                Decimal('0'),
            )
        ).filter(
            CarviaContaMovimentacao.criado_em < dt_inicio,
        ).scalar()

        saldo_anterior = float(saldo_anterior_result)

        # Movimentacoes no periodo
        movs = db.session.query(CarviaContaMovimentacao).filter(
            CarviaContaMovimentacao.criado_em >= dt_inicio,
            CarviaContaMovimentacao.criado_em <= dt_fim,
        ).order_by(
            CarviaContaMovimentacao.criado_em.asc(),
            CarviaContaMovimentacao.id.asc(),
        ).all()

        # Calcular saldo acumulado progressivo
        saldo_acumulado = saldo_anterior
        total_creditos = 0.0
        total_debitos = 0.0
        movimentacoes = []

        for mov in movs:
            valor = float(mov.valor)
            if mov.tipo_movimento == 'CREDITO':
                saldo_acumulado += valor
                total_creditos += valor
            else:
                saldo_acumulado -= valor
                total_debitos += valor

            movimentacoes.append({
                'id': mov.id,
                'criado_em': mov.criado_em,
                'tipo_doc': mov.tipo_doc,
                'doc_id': mov.doc_id,
                'tipo_movimento': mov.tipo_movimento,
                'valor': valor,
                'descricao': mov.descricao or '',
                'criado_por': mov.criado_por,
                'saldo_acumulado': saldo_acumulado,
            })

        return {
            'saldo_anterior': saldo_anterior,
            'movimentacoes': movimentacoes,
            'saldo_final': saldo_acumulado,
            'total_creditos': total_creditos,
            'total_debitos': total_debitos,
        }
