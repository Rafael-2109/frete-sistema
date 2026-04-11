# -*- coding: utf-8 -*-
"""
Service de Cobertura CustoEntrega ↔ Subcontrato
================================================

Gerencia vinculo entre CarviaCustoEntrega e CarviaSubcontrato,
indicando que o custo sera pago pela FaturaTransportadora do subcontrato.

Regras de integridade:
- CE e Sub devem pertencer aa mesma operacao
- CE nao pode estar PAGO ou CANCELADO ao vincular
- CE nao pode estar conciliado diretamente ao vincular
- Ao desvincular: se CE foi PAGO via auto-propagacao, revert PENDENTE
"""

import logging

from app import db

logger = logging.getLogger(__name__)


class CustoEntregaCoberturaService:

    @staticmethod
    def vincular(ce_id, sub_id, usuario):
        """Vincula CustoEntrega ao Subcontrato que cobra este custo.

        Args:
            ce_id: ID do CarviaCustoEntrega
            sub_id: ID do CarviaSubcontrato
            usuario: email do usuario

        Returns:
            dict com sucesso e detalhes

        Raises:
            ValueError: se validacao falhar
        """
        from app.carvia.models import CarviaCustoEntrega, CarviaSubcontrato

        ce = db.session.get(CarviaCustoEntrega, ce_id)
        if not ce:
            raise ValueError(f'Custo de entrega {ce_id} nao encontrado')

        sub = db.session.get(CarviaSubcontrato, sub_id)
        if not sub:
            raise ValueError(f'Subcontrato {sub_id} nao encontrado')

        # Validacoes
        if ce.status == 'CANCELADO':
            raise ValueError('Custo de entrega cancelado nao pode ser vinculado')

        if ce.status == 'PAGO':
            raise ValueError(
                'Custo de entrega ja esta PAGO. '
                'Desfaca o pagamento antes de vincular ao subcontrato.'
            )

        if ce.conciliado:
            raise ValueError(
                'Custo de entrega ja esta conciliado diretamente. '
                'Desfaca a conciliacao antes de vincular ao subcontrato.'
            )

        if ce.operacao_id != sub.operacao_id:
            raise ValueError(
                f'Custo de entrega (operacao #{ce.operacao_id}) e '
                f'subcontrato (operacao #{sub.operacao_id}) pertencem '
                f'a operacoes diferentes.'
            )

        if sub.status == 'CANCELADO':
            raise ValueError('Subcontrato cancelado nao pode ser vinculado')

        if ce.subcontrato_id is not None:
            raise ValueError(
                f'Custo de entrega ja esta vinculado ao subcontrato #{ce.subcontrato_id}. '
                f'Desvincule antes de vincular a outro.'
            )

        # Vincular
        ce.subcontrato_id = sub_id

        # Se sub ja tem FT e FT ja esta PAGO → propagar PAGO ao CE imediatamente
        if sub.fatura_transportadora_id:
            from app.carvia.models import CarviaFaturaTransportadora
            ft = db.session.get(CarviaFaturaTransportadora, sub.fatura_transportadora_id)
            if ft and ft.status_pagamento == 'PAGO':
                from app.utils.timezone import agora_utc_naive
                ce.status = 'PAGO'
                ce.pago_em = agora_utc_naive()
                ce.pago_por = f'auto:{usuario}:via_ft_{ft.id}'
                # NAO setar ce.conciliado=True — conciliado reflete junction
                # CarviaConciliacao, nao cobertura via FT
                logger.info(
                    "CE %s auto-PAGO ao vincular (FT #%d ja PAGO) por %s",
                    ce.numero_custo, ft.id, usuario,
                )

        logger.info(
            "CE %s vinculado ao Sub #%d (%s) por %s",
            ce.numero_custo, sub.id, sub.cte_numero or '-', usuario,
        )

        return {
            'sucesso': True,
            'ce_numero': ce.numero_custo,
            'sub_cte_numero': sub.cte_numero or f'Sub #{sub.id}',
            'ft_numero': (
                sub.fatura_transportadora.numero_fatura
                if sub.fatura_transportadora_id and sub.fatura_transportadora
                else None
            ),
            'ce_status': ce.status,
        }

    @staticmethod
    def desvincular(ce_id, usuario):
        """Remove vinculo CustoEntrega ↔ Subcontrato.

        Se CE foi PAGO via auto-propagacao (pago_por startswith 'auto:'),
        reverte para PENDENTE (exceto se tiver FC).

        Args:
            ce_id: ID do CarviaCustoEntrega
            usuario: email do usuario

        Returns:
            dict com sucesso e detalhes
        """
        from app.carvia.models import CarviaCustoEntrega

        ce = db.session.get(CarviaCustoEntrega, ce_id)
        if not ce:
            raise ValueError(f'Custo de entrega {ce_id} nao encontrado')

        if ce.subcontrato_id is None:
            raise ValueError('Custo de entrega nao esta vinculado a nenhum subcontrato')

        old_sub_id = ce.subcontrato_id
        status_revertido = False

        # Desvincular
        ce.subcontrato_id = None

        # Se CE foi PAGO via auto-propagacao, reverter
        if ce.status == 'PAGO' and (ce.pago_por or '').startswith('auto:'):
            from app.carvia.services.financeiro.carvia_conciliacao_service import (
                CarviaConciliacaoService,
            )
            if not CarviaConciliacaoService._tem_movimentacao_fc('custo_entrega', ce.id):
                ce.status = 'PENDENTE'
                ce.pago_em = None
                ce.pago_por = None
                ce.conciliado = False
                status_revertido = True
                logger.info(
                    "CE %s revertido para PENDENTE ao desvincular Sub #%d por %s",
                    ce.numero_custo, old_sub_id, usuario,
                )

        logger.info(
            "CE %s desvinculado do Sub #%d por %s",
            ce.numero_custo, old_sub_id, usuario,
        )

        return {
            'sucesso': True,
            'ce_numero': ce.numero_custo,
            'status_revertido': status_revertido,
            'ce_status': ce.status,
        }

    @staticmethod
    def subcontratos_disponiveis(ce_id):
        """Retorna Subcontratos da mesma operacao disponiveis para vincular.

        Retorna subs que:
        - Pertencem aa mesma operacao do CE
        - Nao estao CANCELADOS
        - Ordenados por data emissao desc

        Args:
            ce_id: ID do CarviaCustoEntrega

        Returns:
            list[dict] com id, cte_numero, status, valor_final,
                        fatura_transportadora_id, fatura_numero
        """
        from app.carvia.models import CarviaCustoEntrega, CarviaSubcontrato

        ce = db.session.get(CarviaCustoEntrega, ce_id)
        if not ce:
            return []

        subs = CarviaSubcontrato.query.filter(
            CarviaSubcontrato.operacao_id == ce.operacao_id,
            CarviaSubcontrato.status != 'CANCELADO',
        ).order_by(CarviaSubcontrato.cte_data_emissao.desc()).all()

        resultado = []
        for s in subs:
            ft_numero = None
            if s.fatura_transportadora_id and s.fatura_transportadora:
                ft_numero = s.fatura_transportadora.numero_fatura
            resultado.append({
                'id': s.id,
                'cte_numero': s.cte_numero or f'Sub #{s.id}',
                'status': s.status,
                'valor_final': float(s.valor_final or 0) if hasattr(s, 'valor_final') else 0,
                'transportadora': (
                    s.transportadora.razao_social
                    if s.transportadora_id and s.transportadora
                    else '-'
                ),
                'fatura_transportadora_id': s.fatura_transportadora_id,
                'fatura_numero': ft_numero,
            })
        return resultado
