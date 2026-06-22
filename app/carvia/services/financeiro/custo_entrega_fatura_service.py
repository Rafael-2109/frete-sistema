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
- FT deve existir; vinculo PERMITIDO mesmo CONFERIDA/PAGA/conciliada
  (pode_anexar_item — decisao 2026-05-20). O vinculo NAO recalcula valor_total
  nem re-concilia; CE atrasado fica VINCULADO_FT (pagamento tratado a parte).
- Ao desvincular: reset campos `numero_documento='PENDENTE_FATURA'`,
  `tipo_documento='PENDENTE_DOCUMENTO'`, `data_vencimento=None` (xerox Nacom).
"""

import logging

from app import db

logger = logging.getLogger(__name__)


# Sentinelas (xerox DespesaExtra Nacom)
SENTINEL_NUMERO_DOCUMENTO = 'PENDENTE_FATURA'
SENTINEL_TIPO_DOCUMENTO = 'PENDENTE_DOCUMENTO'


class CustoEntregaFaturaService:
    """Servico para vincular/desvincular CE <-> FaturaTransportadora."""

    @staticmethod
    def vincular(ce_id, fatura_id, usuario, ajustes=None):
        """Vincula CarviaCustoEntrega a uma CarviaFaturaTransportadora.

        Args:
            ce_id: ID do CarviaCustoEntrega
            fatura_id: ID da CarviaFaturaTransportadora
            usuario: email/nome do usuario
            ajustes: dict opcional para atualizar campos do CE em transacao
                unica (xerox DespesaExtra Nacom). Chaves suportadas:
                - tipo_documento (str): tipo_documento_cobranca
                - valor (float): valor_cobranca
                - numero_documento (str): numero_cte_documento (vazio -> sentinela)
                - copiar_vencimento_fatura (bool): se True, copia
                  fatura.vencimento -> ce.data_vencimento

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

        # Validacao da fatura — pode_anexar_item() permite vincular mesmo
        # CONFERIDA/PAGA/conciliada (decisao 2026-05-20). Documentos atrasados
        # podem ser anexados; o vinculo NAO recalcula valor_total nem re-concilia.
        pode_anexar, razao = fatura.pode_anexar_item()
        if not pode_anexar:
            raise ValueError(
                f'Fatura {fatura.numero_fatura} nao pode receber novos vinculos: {razao}'
            )

        # Aplicar ajustes ANTES de setar FK/status — transacao unica.
        # Xerox de DespesaExtra Nacom (fretes/routes.py:4341-4348).
        if ajustes:
            tipo_documento = ajustes.get('tipo_documento')
            if tipo_documento:
                ce.tipo_documento = tipo_documento

            valor = ajustes.get('valor')
            if valor is not None:
                ce.valor = valor

            numero_documento = ajustes.get('numero_documento')
            if numero_documento is not None:
                # Vazio vira sentinela; preenchido vai direto.
                ce.numero_documento = (
                    numero_documento.strip()
                    if numero_documento and numero_documento.strip()
                    else SENTINEL_NUMERO_DOCUMENTO
                )

            if ajustes.get('copiar_vencimento_fatura') and fatura.vencimento:
                ce.data_vencimento = fatura.vencimento

        # Executar vinculo — a FK `fatura_transportadora_id` passa a indicar o
        # vinculo; o status PERMANECE PENDENTE (status VINCULADO_FT removido em
        # 2026-06-22). CE PENDENTE com FK = sera pago junto da FT.
        # NOTA (2026-05-20): a FT pode estar PAGA/conciliada (pode_anexar_item
        # permite). NAO auto-propagamos PAGO ao CE: o pagamento ja realizado nao
        # cobriu este item atrasado — seu pagamento e tratado a parte
        # (conciliacao direta ou nova rodada da FT).
        ce.fatura_transportadora_id = fatura_id
        ce.status = 'PENDENTE'

        logger.info(
            "CE %s vinculado a FT #%d (%s) por %s (ajustes=%s)",
            ce.numero_custo, fatura.id, fatura.numero_fatura, usuario,
            bool(ajustes),
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

        Reset de campos (xerox DespesaExtra Nacom em fretes/routes.py:4395-4396):
        - numero_documento -> 'PENDENTE_FATURA'
        - tipo_documento -> 'PENDENTE_DOCUMENTO'
        - data_vencimento -> None

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
        elif old_ft_id and ce.status == 'PENDENTE':
            # CE estava vinculado a FT (FK preenchida) e PENDENTE — ao desvincular
            # mantem PENDENTE mas reseta os campos de documento/vencimento
            # (xerox Nacom). Antes era o estado VINCULADO_FT.
            status_revertido = True

        # Reset de campos de documento e vencimento (xerox Nacom).
        # Aplicado SOMENTE quando status volta para PENDENTE — se CE permanece
        # PAGO (com FC propria), nao mexer em campos que o operador preencheu
        # manualmente.
        if status_revertido:
            ce.numero_documento = SENTINEL_NUMERO_DOCUMENTO
            ce.tipo_documento = SENTINEL_TIPO_DOCUMENTO
            ce.data_vencimento = None

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
    def faturas_disponiveis(ce_id, restrito_por_transportadora=True):
        """Retorna CarviaFaturaTransportadora disponiveis para vincular este CE.

        Filtros:
        - Todas as FTs sao elegiveis (CONFERIDA/PAGA/conciliada inclusive) —
          consistente com vincular() que usa pode_anexar_item (2026-05-20).
          O campo 'cabe_ce' do resultado sinaliza divergencia de soma para a UI.
        - Se restrito_por_transportadora=True (default) E CE tem frete_id,
          filtra por mesma transportadora via CarviaSubcontrato vinculado ao
          frete. Caso contrario, retorna todas elegiveis (paridade Nacom).

        Args:
            ce_id: ID do CarviaCustoEntrega
            restrito_por_transportadora: se True, restringe a FTs da mesma
                transportadora que opera o frete. Default True (compat).
                Passar False para alinhar com Nacom (qualquer FT pendente).

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
        if restrito_por_transportadora and ce.frete_id:
            frete = db.session.get(CarviaFrete, ce.frete_id)
            if frete:
                subs = CarviaSubcontrato.query.filter_by(frete_id=frete.id).all()
                transportadora_ids = {s.transportadora_id for s in subs if s.transportadora_id}

        # 2026-05-20: sem filtro de status — faturas CONFERIDAS/PAGAS/conciliadas
        # tambem podem receber despesas atrasadas (pode_anexar_item).
        query = CarviaFaturaTransportadora.query
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
        - FT deve permitir anexacao (pode_anexar_item — 2026-05-20: aceita
          CONFERIDA/PAGA/conciliada; despesas atrasadas podem ser vinculadas).

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

        pode_anexar, _ = fatura.pode_anexar_item()
        if not pode_anexar:
            return []

        if not fatura.transportadora_id:
            return []

        # Branch A — CEs com frete_id: JOIN CE -> CarviaSubcontrato (via frete_id)
        # para filtrar por transportadora_id, com distinct para evitar duplicatas.
        ces_com_frete = (
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
            .all()
        )

        # Branch B (fallback 2026-05-05) — CEs sem frete_id mas com operacao_id.
        # Cobre o cenario novo de CE criado direto no CTe (sem CarviaFrete).
        # Match deve ser deterministico — duas vias INDEPENDENTES (EXISTS evita
        # fan-out do OUTERJOIN+OR que poderia trazer CEs de outra transportadora):
        #
        #   (a) override explicito: CE.transportadora_id == FT.transportadora_id
        #   (b) inferido pela operacao: EXISTS CarviaSubcontrato com mesma operacao
        #       E mesma transportadora da FT
        sub_exists = (
            db.session.query(CarviaSubcontrato.id)
            .filter(
                CarviaSubcontrato.operacao_id == CarviaCustoEntrega.operacao_id,
                CarviaSubcontrato.transportadora_id == fatura.transportadora_id,
                CarviaSubcontrato.status != 'CANCELADO',
            )
            .exists()
        )
        ces_sem_frete = (
            db.session.query(CarviaCustoEntrega)
            .filter(
                CarviaCustoEntrega.status == 'PENDENTE',
                CarviaCustoEntrega.fatura_transportadora_id.is_(None),
                CarviaCustoEntrega.frete_id.is_(None),
                CarviaCustoEntrega.operacao_id.isnot(None),
                db.or_(
                    CarviaCustoEntrega.transportadora_id == fatura.transportadora_id,
                    sub_exists,
                ),
            )
            .all()
        )

        # Merge sem duplicatas (chave: ce.id) — preserva ordem por criado_em DESC
        ce_map = {ce.id: ce for ce in (ces_com_frete + ces_sem_frete)}
        ces = sorted(
            ce_map.values(), key=lambda c: c.criado_em or db.func.now(), reverse=True,
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
