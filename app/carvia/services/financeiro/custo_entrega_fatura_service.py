# -*- coding: utf-8 -*-
"""
Service CustoEntrega ↔ FaturaTransportadora
===========================================

Gerencia o vinculo direto de CarviaCustoEntrega com CarviaFaturaTransportadora,
espelhando o padrao DespesaExtra.fatura_frete_id do modulo Nacom.

Substitui o CustoEntregaCoberturaService (obsoleto) que vinculava CE a
CarviaSubcontrato. Agora CE se relaciona diretamente com a fatura.

Regras de integridade:
- CE nao pode estar CANCELADO ou PAGO ao vincular
- CE nao pode estar conciliado diretamente ao vincular
- CE nao pode ja estar vinculado a outra FT
- FT deve existir e nao estar CONFERIDA (bloqueio via pode_editar())
- Ao vincular com FT ja PAGA: auto-propaga status PAGO
- Ao desvincular: se foi PAGO via auto-propagacao, reverte para PENDENTE
"""

import logging

from app import db

logger = logging.getLogger(__name__)


class CustoEntregaFaturaService:
    """Servico para vincular/desvincular CE <-> FaturaTransportadora."""

    @staticmethod
    def vincular(ce_id, fatura_id, usuario):
        """Vincula CarviaCustoEntrega a uma CarviaFaturaTransportadora.

        Args:
            ce_id: ID do CarviaCustoEntrega
            fatura_id: ID da CarviaFaturaTransportadora
            usuario: email/nome do usuario

        Returns:
            dict com sucesso e detalhes

        Raises:
            ValueError: se validacao falhar
        """
        from app.carvia.models import CarviaCustoEntrega, CarviaFaturaTransportadora

        ce = db.session.get(CarviaCustoEntrega, ce_id)
        if not ce:
            raise ValueError(f'Custo de entrega {ce_id} nao encontrado')

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            raise ValueError(f'Fatura transportadora {fatura_id} nao encontrada')

        # Validacoes do CE
        if ce.status == 'CANCELADO':
            raise ValueError('Custo de entrega cancelado nao pode ser vinculado')

        if ce.status == 'PAGO':
            raise ValueError(
                'Custo de entrega ja esta PAGO. '
                'Desfaca o pagamento antes de vincular a uma fatura.'
            )

        if ce.conciliado:
            raise ValueError(
                'Custo de entrega ja esta conciliado diretamente. '
                'Desfaca a conciliacao antes de vincular a uma fatura.'
            )

        if ce.fatura_transportadora_id is not None:
            if ce.fatura_transportadora_id == fatura_id:
                raise ValueError(
                    f'Custo de entrega ja esta vinculado a esta fatura #{fatura_id}.'
                )
            raise ValueError(
                f'Custo de entrega ja esta vinculado a fatura #{ce.fatura_transportadora_id}. '
                f'Desvincule antes de vincular a outra.'
            )

        # Validacao da fatura — pode_editar() ja bloqueia FT CONFERIDA ou PAGA.
        # Isso garante que CEs so sao vinculados enquanto a fatura esta em
        # construcao/conferencia. Alinhado com o filtro da `faturas_disponiveis()`.
        pode_editar, razao = fatura.pode_editar()
        if not pode_editar:
            raise ValueError(
                f'Fatura {fatura.numero_fatura} nao pode receber novos vinculos: {razao}'
            )

        # Executar vinculo — status vai para VINCULADO_FT.
        # Auto-propagacao para PAGO nao e necessaria aqui: se a FT pudesse estar
        # PAGA, `pode_editar()` teria falhado acima.
        ce.fatura_transportadora_id = fatura_id
        ce.status = 'VINCULADO_FT'

        logger.info(
            "CE %s vinculado a FT #%d (%s) por %s",
            ce.numero_custo, fatura.id, fatura.numero_fatura, usuario,
        )

        return {
            'sucesso': True,
            'ce_numero': ce.numero_custo,
            'ce_status': ce.status,
            'ft_id': fatura.id,
            'ft_numero': fatura.numero_fatura,
            'ft_status_pagamento': fatura.status_pagamento,
        }

    @staticmethod
    def desvincular(ce_id, usuario):
        """Remove vinculo CE <-> FaturaTransportadora.

        Se CE foi PAGO via auto-propagacao (pago_por startswith 'auto:'),
        reverte para PENDENTE — desde que nao tenha movimentacao FC propria.

        Bloqueios:
        - FT ja CONFERIDA (nao pode mais alterar itens)
        - CE tem movimentacao FC propria (pago manualmente por outro fluxo)

        Args:
            ce_id: ID do CarviaCustoEntrega
            usuario: email/nome do usuario

        Returns:
            dict com sucesso e detalhes
        """
        from app.carvia.models import CarviaCustoEntrega, CarviaFaturaTransportadora
        from app.carvia.services.financeiro.carvia_conciliacao_service import (
            CarviaConciliacaoService,
        )

        ce = db.session.get(CarviaCustoEntrega, ce_id)
        if not ce:
            raise ValueError(f'Custo de entrega {ce_id} nao encontrado')

        if ce.fatura_transportadora_id is None:
            raise ValueError('Custo de entrega nao esta vinculado a nenhuma fatura')

        fatura = db.session.get(CarviaFaturaTransportadora, ce.fatura_transportadora_id)
        if fatura and fatura.status_conferencia == 'CONFERIDO':
            raise ValueError(
                f'Fatura {fatura.numero_fatura} ja esta CONFERIDA. '
                f'Reabra a conferencia antes de desvincular.'
            )

        old_ft_id = ce.fatura_transportadora_id
        status_revertido = False

        # Desvincular
        ce.fatura_transportadora_id = None

        # Reverter status se foi PAGO via auto-propagacao
        if ce.status == 'PAGO' and (ce.pago_por or '').startswith('auto:'):
            if not CarviaConciliacaoService._tem_movimentacao_fc('custo_entrega', ce.id):
                ce.status = 'PENDENTE'
                ce.pago_em = None
                ce.pago_por = None
                ce.conciliado = False
                status_revertido = True
            else:
                # Tem FC propria — nao pode reverter, nao pode desvincular
                ce.fatura_transportadora_id = old_ft_id  # rollback do desvinculo
                raise ValueError(
                    f'Custo {ce.numero_custo} tem movimentacao de fluxo de caixa propria. '
                    f'Remova a movimentacao antes de desvincular.'
                )
        elif ce.status == 'VINCULADO_FT':
            # Status VINCULADO_FT volta para PENDENTE ao desvincular
            ce.status = 'PENDENTE'
            status_revertido = True

        logger.info(
            "CE %s desvinculado da FT #%d por %s (status_revertido=%s)",
            ce.numero_custo, old_ft_id, usuario, status_revertido,
        )

        return {
            'sucesso': True,
            'ce_numero': ce.numero_custo,
            'ce_status': ce.status,
            'status_revertido': status_revertido,
        }

    @staticmethod
    def faturas_disponiveis(ce_id):
        """Retorna CarviaFaturaTransportadora disponiveis para vincular este CE.

        Filtros:
        - FT nao CONFERIDA e nao PAGA (consistente com vincular() que usa pode_editar)
        - Se CE tem frete_id, filtra por mesma transportadora via
          CarviaSubcontrato vinculado ao frete. Caso contrario, retorna todas
          elegiveis (usuario decide).

        Args:
            ce_id: ID do CarviaCustoEntrega

        Returns:
            list[dict] com id, numero_fatura, transportadora_nome, valor_total,
                      vencimento, soma_subs, soma_ces, diferenca, cabe_ce
        """
        from sqlalchemy import func as sqlfunc
        from app.carvia.models import (
            CarviaCustoEntrega, CarviaFaturaTransportadora,
            CarviaFrete, CarviaSubcontrato,
        )

        ce = db.session.get(CarviaCustoEntrega, ce_id)
        if not ce:
            return []

        # Identificar transportadoras candidatas via frete_id (se disponivel)
        transportadora_ids = set()
        if ce.frete_id:
            frete = db.session.get(CarviaFrete, ce.frete_id)
            if frete:
                subs = CarviaSubcontrato.query.filter_by(frete_id=frete.id).all()
                transportadora_ids = {s.transportadora_id for s in subs if s.transportadora_id}

        query = CarviaFaturaTransportadora.query.filter(
            CarviaFaturaTransportadora.status_conferencia != 'CONFERIDO',
            CarviaFaturaTransportadora.status_pagamento != 'PAGO',
        )
        if transportadora_ids:
            query = query.filter(
                CarviaFaturaTransportadora.transportadora_id.in_(transportadora_ids)
            )
        faturas = query.order_by(
            CarviaFaturaTransportadora.data_emissao.desc()
        ).all()

        if not faturas:
            return []

        # Pre-agregar soma_subs e soma_ces por fatura_transportadora_id
        # em duas queries agregadas (evita N+1 — antes era 1 query por fatura).
        fatura_ids = [f.id for f in faturas]

        # Phase C (2026-04-14): valor_considerado migrou para CarviaFrete.
        # LEFT JOIN CarviaFrete via sub.frete_id para somar via frete.
        from app.carvia.models import CarviaFrete
        subs_agg = dict(
            db.session.query(
                CarviaSubcontrato.fatura_transportadora_id,
                sqlfunc.coalesce(sqlfunc.sum(CarviaFrete.valor_considerado), 0),
            ).outerjoin(
                CarviaFrete, CarviaSubcontrato.frete_id == CarviaFrete.id,
            ).filter(
                CarviaSubcontrato.fatura_transportadora_id.in_(fatura_ids),
                CarviaSubcontrato.status != 'CANCELADO',
            ).group_by(CarviaSubcontrato.fatura_transportadora_id).all()
        )

        ces_agg = dict(
            db.session.query(
                CarviaCustoEntrega.fatura_transportadora_id,
                sqlfunc.coalesce(sqlfunc.sum(CarviaCustoEntrega.valor), 0),
            ).filter(
                CarviaCustoEntrega.fatura_transportadora_id.in_(fatura_ids),
                CarviaCustoEntrega.status != 'CANCELADO',
            ).group_by(CarviaCustoEntrega.fatura_transportadora_id).all()
        )

        valor_ce = float(ce.valor or 0)
        resultado = []
        for f in faturas:
            soma_subs = float(subs_agg.get(f.id, 0) or 0)
            soma_ces = float(ces_agg.get(f.id, 0) or 0)
            total_itens = soma_subs + soma_ces
            valor_total_ft = float(f.valor_total or 0)
            diferenca = valor_total_ft - total_itens

            resultado.append({
                'id': f.id,
                'numero_fatura': f.numero_fatura,
                'transportadora_nome': (
                    f.transportadora.razao_social
                    if f.transportadora_id and f.transportadora
                    else '-'
                ),
                'valor_total': valor_total_ft,
                'vencimento': f.vencimento.strftime('%d/%m/%Y') if f.vencimento else '-',
                'data_emissao': f.data_emissao.strftime('%d/%m/%Y') if f.data_emissao else '-',
                'status_conferencia': f.status_conferencia,
                'status_pagamento': f.status_pagamento,
                'soma_subs': round(soma_subs, 2),
                'soma_ces': round(soma_ces, 2),
                'total_itens': round(total_itens, 2),
                'diferenca': round(diferenca, 2),
                'cabe_ce': diferenca >= valor_ce - 0.01,
            })
        return resultado

    @staticmethod
    def ces_disponiveis_para_fatura(fatura_id):
        """Retorna CarviaCustoEntrega elegiveis para vincular a esta FT.

        Inverso de `faturas_disponiveis(ce_id)` — usado pela tela de detalhe
        da FT para oferecer vinculacao reversa (padrao DespesaExtra do Nacom
        adaptado: Nacom so permite vincular pelo lado da despesa, CarVia
        permite pelos dois lados).

        Filtros:
        - CE com `status='PENDENTE'` e `fatura_transportadora_id IS NULL`
        - CE cujo `frete_id` aponta para um frete que tem subcontrato(s) da
          mesma transportadora da FT (navegacao ce.frete_id -> CarviaSubcontrato
          -> transportadora_id). CEs sem frete_id sao excluidos por seguranca
          (nao da para garantir que pertencem a essa transportadora).
        - FT deve estar editavel (senao retorna lista vazia — defesa em
          profundidade; a rota tambem valida `pode_editar()`).

        Args:
            fatura_id: ID da CarviaFaturaTransportadora

        Returns:
            list[dict] com id, numero_custo, tipo_custo, valor,
                      operacao_cte_numero, operacao_cliente, fornecedor_nome,
                      data_custo
        """
        from app.carvia.models import (
            CarviaCustoEntrega, CarviaFaturaTransportadora,
            CarviaSubcontrato, CarviaOperacao,
        )

        fatura = db.session.get(CarviaFaturaTransportadora, fatura_id)
        if not fatura:
            return []

        pode_editar, _ = fatura.pode_editar()
        if not pode_editar:
            return []

        if not fatura.transportadora_id:
            return []

        # Buscar CEs PENDENTE sem FT cujo frete_id aponta para um frete
        # que possui subcontrato da mesma transportadora da FT.
        # JOIN CE -> CarviaSubcontrato (via frete_id) para filtrar por
        # transportadora_id, com distinct para evitar duplicatas quando
        # o frete tem multiplos subs.
        ces = (
            db.session.query(CarviaCustoEntrega)
            .join(
                CarviaSubcontrato,
                CarviaSubcontrato.frete_id == CarviaCustoEntrega.frete_id,
            )
            .filter(
                CarviaCustoEntrega.status == 'PENDENTE',
                CarviaCustoEntrega.fatura_transportadora_id.is_(None),
                CarviaCustoEntrega.frete_id.isnot(None),
                CarviaSubcontrato.transportadora_id == fatura.transportadora_id,
            )
            .distinct()
            .order_by(CarviaCustoEntrega.criado_em.desc())
            .all()
        )

        if not ces:
            return []

        # Carregar operacoes em lote para evitar N+1
        op_ids = list({ce.operacao_id for ce in ces if ce.operacao_id})
        operacoes_map = {}
        if op_ids:
            ops = CarviaOperacao.query.filter(CarviaOperacao.id.in_(op_ids)).all()
            operacoes_map = {op.id: op for op in ops}

        resultado = []
        for ce in ces:
            op = operacoes_map.get(ce.operacao_id) if ce.operacao_id else None
            resultado.append({
                'id': ce.id,
                'numero_custo': ce.numero_custo,
                'tipo_custo': ce.tipo_custo,
                'valor': float(ce.valor or 0),
                'operacao_id': ce.operacao_id,
                'operacao_cte_numero': op.cte_numero if op else '-',
                'operacao_cliente': op.nome_cliente if op else '-',
                'operacao_destino': (
                    f'{op.cidade_destino}/{op.uf_destino}'
                    if op and op.cidade_destino else '-'
                ),
                'fornecedor_nome': ce.fornecedor_nome or '-',
                'data_custo': (
                    ce.data_custo.strftime('%d/%m/%Y') if ce.data_custo else '-'
                ),
            })
        return resultado
