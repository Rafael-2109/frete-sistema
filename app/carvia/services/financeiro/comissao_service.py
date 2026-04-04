"""
Comissao CarVia — Service
==========================

Logica de negocio para fechamento de comissao:
- Criar fechamento por periodo (cte_data_emissao)
- Editar fechamento (percentual, vendedor, observacoes)
- Incluir/excluir CTes de um fechamento (individual ou batch)
- Gerar despesa vinculada para conciliacao bancaria
- Registrar pagamento (manual ou via conciliacao)
- Recalcular totais apos alteracoes
"""

import logging
from decimal import Decimal

from app import db
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


class ComissaoService:
    """Gerencia fechamentos de comissao CarVia."""

    # ------------------------------------------------------------------
    # Percentual global
    # ------------------------------------------------------------------

    @staticmethod
    def get_percentual_config():
        """Le percentual de comissao do CarviaConfig.

        Returns:
            Decimal — percentual como fracao (ex: 0.05 = 5%)

        Raises:
            ValueError se nao configurado ou invalido.
        """
        from app.carvia.services.pricing.config_service import CarviaConfigService

        valor = CarviaConfigService.get('COMISSAO_PERCENTUAL')
        if not valor:
            raise ValueError(
                'Parametro COMISSAO_PERCENTUAL nao configurado. '
                'Acesse Configuracoes > Parametros Globais.'
            )
        try:
            pct = Decimal(str(valor).replace(',', '.').replace('%', '').strip())
            # Se o usuario digitou 5 (pensando 5%), converter para 0.05
            if pct > 1:
                pct = pct / Decimal('100')
            if pct <= 0 or pct > 1:
                raise ValueError(f'Percentual invalido: {valor}')
            return pct
        except Exception as e:
            raise ValueError(f'Valor de COMISSAO_PERCENTUAL invalido: {valor} — {e}')

    # ------------------------------------------------------------------
    # Despesa vinculada (integracao financeira)
    # ------------------------------------------------------------------

    @staticmethod
    def _criar_despesa_vinculada(fechamento, criado_por):
        """Cria despesa tipo COMISSAO vinculada ao fechamento.

        Chamado internamente por criar_fechamento().
        A despesa permite que a comissao participe do fluxo de conciliacao bancaria.
        """
        from app.carvia.models import CarviaDespesa

        descricao = f'Comissao {fechamento.numero_fechamento} — {fechamento.vendedor_nome}'
        despesa = CarviaDespesa(
            tipo_despesa='COMISSAO',
            descricao=descricao,
            valor=fechamento.total_comissao,
            data_despesa=fechamento.data_fim,
            data_vencimento=fechamento.data_fim,
            status='PENDENTE',
            criado_por=criado_por,
        )
        db.session.add(despesa)
        db.session.flush()
        fechamento.despesa_id = despesa.id
        logger.info(
            "Despesa #%d (COMISSAO) criada para fechamento %s — R$ %s",
            despesa.id, fechamento.numero_fechamento, fechamento.total_comissao,
        )
        return despesa

    @staticmethod
    def _sincronizar_despesa(fechamento):
        """Sincroniza valor e descricao da despesa vinculada com o fechamento.

        Chamado apos qualquer operacao que altere total_comissao
        (editar percentual, incluir/excluir CTe).
        """
        if not fechamento.despesa_id:
            return
        from app.carvia.models import CarviaDespesa
        despesa = db.session.get(CarviaDespesa, fechamento.despesa_id)
        if not despesa:
            return
        if despesa.status != 'PENDENTE':
            logger.warning(
                "Despesa #%d nao esta PENDENTE (%s) — skip sincronizacao valor",
                despesa.id, despesa.status,
            )
            return
        despesa.valor = fechamento.total_comissao
        despesa.descricao = f'Comissao {fechamento.numero_fechamento} — {fechamento.vendedor_nome}'
        despesa.data_despesa = fechamento.data_fim
        despesa.data_vencimento = fechamento.data_fim

    # ------------------------------------------------------------------
    # CTes elegiveis
    # ------------------------------------------------------------------

    @staticmethod
    def buscar_ctes_elegiveis(data_inicio, data_fim, excluir_ja_comissionados=True):
        """Retorna CTes CarVia elegiveis para comissao no periodo.

        Criterios:
        - cte_data_emissao BETWEEN data_inicio AND data_fim
        - status != 'CANCELADO'
        - cte_valor IS NOT NULL AND cte_valor > 0
        - (opcional) Nao incluso em outro fechamento ativo

        Args:
            data_inicio: date
            data_fim: date
            excluir_ja_comissionados: se True, exclui CTes ja em fechamentos nao-cancelados

        Returns:
            list[CarviaOperacao] ordenado por cte_data_emissao ASC
        """
        from app.carvia.models import CarviaOperacao
        from app.carvia.models.comissao import (
            CarviaComissaoFechamento, CarviaComissaoFechamentoCte,
        )

        query = db.session.query(CarviaOperacao).filter(
            CarviaOperacao.cte_data_emissao.between(data_inicio, data_fim),
            CarviaOperacao.status != 'CANCELADO',
            CarviaOperacao.cte_valor.isnot(None),
            CarviaOperacao.cte_valor > 0,
        )

        if excluir_ja_comissionados:
            # Subquery: operacao_ids ja em fechamentos ativos (nao excluidos)
            ja_comissionados = db.session.query(
                CarviaComissaoFechamentoCte.operacao_id
            ).join(
                CarviaComissaoFechamento,
                CarviaComissaoFechamentoCte.fechamento_id == CarviaComissaoFechamento.id,
            ).filter(
                CarviaComissaoFechamento.status != 'CANCELADO',
                CarviaComissaoFechamentoCte.excluido.is_(False),
            ).subquery()

            query = query.filter(
                CarviaOperacao.id.notin_(ja_comissionados)
            )

        return query.order_by(CarviaOperacao.cte_data_emissao.asc()).all()

    # ------------------------------------------------------------------
    # Criar fechamento
    # ------------------------------------------------------------------

    @staticmethod
    def criar_fechamento(
        vendedor_nome,
        vendedor_email,
        data_inicio,
        data_fim,
        operacao_ids,
        criado_por,
        percentual=None,
        observacoes=None,
    ):
        """Cria fechamento de comissao com CTes selecionados.

        Args:
            vendedor_nome: str — nome do vendedor
            vendedor_email: str or None
            data_inicio: date
            data_fim: date
            operacao_ids: list[int] — IDs de CarviaOperacao
            criado_por: str — email do usuario
            percentual: Decimal or None — se None, usa CarviaConfig
            observacoes: str or None

        Returns:
            CarviaComissaoFechamento

        Raises:
            ValueError para validacoes de negocio.
        """
        from app.carvia.models import CarviaOperacao
        from app.carvia.models.comissao import (
            CarviaComissaoFechamento, CarviaComissaoFechamentoCte,
        )

        if not vendedor_nome or not vendedor_nome.strip():
            raise ValueError('Nome do vendedor e obrigatorio.')

        if not operacao_ids:
            raise ValueError('Selecione ao menos um CTe.')

        if data_inicio > data_fim:
            raise ValueError('Data inicio deve ser anterior ou igual a data fim.')

        # Percentual: usar override ou config
        if percentual is not None:
            pct = Decimal(str(percentual))
            if pct > 1:
                pct = pct / Decimal('100')
        else:
            pct = ComissaoService.get_percentual_config()

        # Validar operacoes
        operacoes = CarviaOperacao.query.filter(
            CarviaOperacao.id.in_(operacao_ids),
        ).all()

        if len(operacoes) != len(operacao_ids):
            encontrados = {o.id for o in operacoes}
            faltando = set(operacao_ids) - encontrados
            raise ValueError(f'CTes nao encontrados: {faltando}')

        # Validar: nenhum cancelado, todos com cte_valor e cte_data_emissao
        for op in operacoes:
            if op.status == 'CANCELADO':
                raise ValueError(f'{op.cte_numero}: CTe cancelado.')
            if not op.cte_valor or op.cte_valor <= 0:
                raise ValueError(f'{op.cte_numero}: sem valor de CTe.')
            if not op.cte_data_emissao:
                raise ValueError(f'{op.cte_numero}: sem data de emissao do CTe.')

        # Criar fechamento
        fechamento = CarviaComissaoFechamento(
            numero_fechamento=CarviaComissaoFechamento.gerar_numero_fechamento(),
            vendedor_nome=vendedor_nome.strip(),
            vendedor_email=(vendedor_email or '').strip() or None,
            data_inicio=data_inicio,
            data_fim=data_fim,
            percentual=pct,
            status='PENDENTE',
            observacoes=(observacoes or '').strip() or None,
            criado_por=criado_por,
        )
        db.session.add(fechamento)
        db.session.flush()  # Gera fechamento.id

        # Criar junctions com snapshots
        for op in operacoes:
            valor_cte = Decimal(str(op.cte_valor))
            valor_comissao = (valor_cte * pct).quantize(Decimal('0.01'))

            cte_junction = CarviaComissaoFechamentoCte(
                fechamento_id=fechamento.id,
                operacao_id=op.id,
                cte_numero=op.cte_numero or f'OP-{op.id}',
                cte_data_emissao=op.cte_data_emissao,
                valor_cte_snapshot=valor_cte,
                percentual_snapshot=pct,
                valor_comissao=valor_comissao,
                incluido_por=criado_por,
            )
            db.session.add(cte_junction)

        # Recalcular totais
        db.session.flush()
        fechamento.recalcular_totais()

        # Criar despesa vinculada para conciliacao bancaria
        ComissaoService._criar_despesa_vinculada(fechamento, criado_por)

        db.session.commit()

        logger.info(
            "Comissao %s criada: %d CTes, R$ %s bruto, R$ %s comissao (%.2f%%) por %s",
            fechamento.numero_fechamento, fechamento.qtd_ctes,
            fechamento.total_bruto, fechamento.total_comissao,
            float(pct * 100), criado_por,
        )
        return fechamento

    # ------------------------------------------------------------------
    # Incluir / Excluir CTe
    # ------------------------------------------------------------------

    @staticmethod
    def incluir_cte(fechamento_id, operacao_id, incluido_por):
        """Inclui CTe em um fechamento PENDENTE.

        Se o CTe ja foi excluido do mesmo fechamento, reativa.

        Returns:
            CarviaComissaoFechamentoCte

        Raises:
            ValueError para erros de validacao.
        """
        from app.carvia.models import CarviaOperacao
        from app.carvia.models.comissao import (
            CarviaComissaoFechamento, CarviaComissaoFechamentoCte,
        )

        fechamento = db.session.get(CarviaComissaoFechamento, fechamento_id)
        if not fechamento:
            raise ValueError('Fechamento nao encontrado.')
        if fechamento.status != 'PENDENTE':
            raise ValueError(f'Fechamento {fechamento.status} — so pode alterar PENDENTE.')

        operacao = db.session.get(CarviaOperacao, operacao_id)
        if not operacao:
            raise ValueError('CTe nao encontrado.')
        if operacao.status == 'CANCELADO':
            raise ValueError(f'{operacao.cte_numero}: CTe cancelado.')
        if not operacao.cte_valor or operacao.cte_valor <= 0:
            raise ValueError(f'{operacao.cte_numero}: sem valor de CTe.')
        if not operacao.cte_data_emissao:
            raise ValueError(f'{operacao.cte_numero}: sem data de emissao do CTe.')

        # Verificar se ja existe (possivelmente excluido)
        existente = CarviaComissaoFechamentoCte.query.filter_by(
            fechamento_id=fechamento_id,
            operacao_id=operacao_id,
        ).first()

        pct = Decimal(str(fechamento.percentual))
        valor_cte = Decimal(str(operacao.cte_valor))
        valor_comissao = (valor_cte * pct).quantize(Decimal('0.01'))

        if existente:
            if not existente.excluido:
                raise ValueError(f'{operacao.cte_numero} ja esta no fechamento.')
            # Reativar
            existente.excluido = False
            existente.excluido_em = None
            existente.excluido_por = None
            existente.valor_cte_snapshot = valor_cte
            existente.percentual_snapshot = pct
            existente.valor_comissao = valor_comissao
            existente.incluido_por = incluido_por
            existente.incluido_em = agora_utc_naive()
            junction = existente
        else:
            junction = CarviaComissaoFechamentoCte(
                fechamento_id=fechamento_id,
                operacao_id=operacao_id,
                cte_numero=operacao.cte_numero or f'OP-{operacao.id}',
                cte_data_emissao=operacao.cte_data_emissao,
                valor_cte_snapshot=valor_cte,
                percentual_snapshot=pct,
                valor_comissao=valor_comissao,
                incluido_por=incluido_por,
            )
            db.session.add(junction)

        db.session.flush()
        fechamento.recalcular_totais()
        ComissaoService._sincronizar_despesa(fechamento)
        db.session.commit()

        logger.info(
            "CTe %s incluido em %s por %s",
            operacao.cte_numero, fechamento.numero_fechamento, incluido_por,
        )
        return junction

    @staticmethod
    def excluir_cte(fechamento_id, operacao_id, excluido_por):
        """Exclui (soft) CTe de um fechamento PENDENTE.

        Raises:
            ValueError para erros de validacao.
        """
        from app.carvia.models.comissao import (
            CarviaComissaoFechamento, CarviaComissaoFechamentoCte,
        )
        fechamento = db.session.get(CarviaComissaoFechamento, fechamento_id)
        if not fechamento:
            raise ValueError('Fechamento nao encontrado.')
        if fechamento.status != 'PENDENTE':
            raise ValueError(f'Fechamento {fechamento.status} — so pode alterar PENDENTE.')

        junction = CarviaComissaoFechamentoCte.query.filter_by(
            fechamento_id=fechamento_id,
            operacao_id=operacao_id,
            excluido=False,
        ).first()

        if not junction:
            raise ValueError('CTe nao encontrado no fechamento.')

        junction.excluido = True
        junction.excluido_em = agora_utc_naive()
        junction.excluido_por = excluido_por

        db.session.flush()
        fechamento.recalcular_totais()
        ComissaoService._sincronizar_despesa(fechamento)
        db.session.commit()

        logger.info(
            "CTe op_id=%d excluido de %s por %s",
            operacao_id, fechamento.numero_fechamento, excluido_por,
        )

    # ------------------------------------------------------------------
    # Editar fechamento
    # ------------------------------------------------------------------

    @staticmethod
    def editar_fechamento(fechamento_id, dados, editado_por):
        """Edita campos de um fechamento PENDENTE.

        Se percentual mudar, recalcula valor_comissao de todos os CTes ativos.
        Sincroniza despesa vinculada automaticamente.

        Args:
            fechamento_id: int
            dados: dict com chaves opcionais:
                - vendedor_nome: str
                - vendedor_email: str
                - percentual: Decimal (como fracao, ex: 0.05)
                - observacoes: str
            editado_por: str — email

        Returns:
            CarviaComissaoFechamento

        Raises:
            ValueError para erros de validacao.
        """
        from app.carvia.models.comissao import (
            CarviaComissaoFechamento, CarviaComissaoFechamentoCte,
        )

        fechamento = db.session.get(CarviaComissaoFechamento, fechamento_id)
        if not fechamento:
            raise ValueError('Fechamento nao encontrado.')
        if fechamento.status != 'PENDENTE':
            raise ValueError(
                f'Nao e possivel editar fechamento com status {fechamento.status}.'
            )

        # Campos simples
        if 'vendedor_nome' in dados:
            nome = (dados['vendedor_nome'] or '').strip()
            if not nome:
                raise ValueError('Nome do vendedor e obrigatorio.')
            fechamento.vendedor_nome = nome

        if 'vendedor_email' in dados:
            fechamento.vendedor_email = (dados['vendedor_email'] or '').strip() or None

        if 'observacoes' in dados:
            fechamento.observacoes = (dados['observacoes'] or '').strip() or None

        # Percentual — recalcula todos os CTes
        percentual_mudou = False
        if 'percentual' in dados and dados['percentual'] is not None:
            novo_pct = Decimal(str(dados['percentual']))
            if novo_pct > 1:
                novo_pct = novo_pct / Decimal('100')
            if novo_pct <= 0 or novo_pct > 1:
                raise ValueError(f'Percentual invalido: {dados["percentual"]}')

            if novo_pct != fechamento.percentual:
                percentual_mudou = True
                fechamento.percentual = novo_pct

                # Recalcular todos os CTes ativos
                ctes_ativos = CarviaComissaoFechamentoCte.query.filter_by(
                    fechamento_id=fechamento_id,
                    excluido=False,
                ).all()

                for cte in ctes_ativos:
                    cte.percentual_snapshot = novo_pct
                    cte.valor_comissao = (
                        Decimal(str(cte.valor_cte_snapshot)) * novo_pct
                    ).quantize(Decimal('0.01'))

                db.session.flush()
                fechamento.recalcular_totais()

                logger.info(
                    "Percentual de %s alterado para %.4f por %s — %d CTes recalculados",
                    fechamento.numero_fechamento, float(novo_pct),
                    editado_por, len(ctes_ativos),
                )

        # Sincronizar despesa vinculada (se percentual ou vendedor mudou)
        ComissaoService._sincronizar_despesa(fechamento)

        db.session.commit()

        logger.info(
            "Comissao %s editada por %s (percentual_mudou=%s)",
            fechamento.numero_fechamento, editado_por, percentual_mudou,
        )
        return fechamento

    # ------------------------------------------------------------------
    # Incluir CTes em batch (para modal visual)
    # ------------------------------------------------------------------

    @staticmethod
    def incluir_ctes_batch(fechamento_id, operacao_ids, incluido_por):
        """Inclui multiplos CTes em um fechamento PENDENTE.

        Reutiliza logica de incluir_cte individual mas com commit unico.

        Args:
            fechamento_id: int
            operacao_ids: list[int]
            incluido_por: str

        Returns:
            int — quantidade de CTes incluidos

        Raises:
            ValueError para erros de validacao.
        """
        from app.carvia.models import CarviaOperacao
        from app.carvia.models.comissao import (
            CarviaComissaoFechamento, CarviaComissaoFechamentoCte,
        )

        fechamento = db.session.get(CarviaComissaoFechamento, fechamento_id)
        if not fechamento:
            raise ValueError('Fechamento nao encontrado.')
        if fechamento.status != 'PENDENTE':
            raise ValueError(f'Fechamento {fechamento.status} — so pode alterar PENDENTE.')
        if not operacao_ids:
            raise ValueError('Selecione ao menos um CTe.')

        pct = Decimal(str(fechamento.percentual))
        incluidos = 0

        for operacao_id in operacao_ids:
            operacao = db.session.get(CarviaOperacao, operacao_id)
            if not operacao:
                logger.warning("CTe op_id=%d nao encontrado — skip", operacao_id)
                continue
            if operacao.status == 'CANCELADO':
                logger.warning("CTe %s cancelado — skip", operacao.cte_numero)
                continue
            if not operacao.cte_valor or operacao.cte_valor <= 0:
                logger.warning("CTe %s sem valor — skip", operacao.cte_numero)
                continue
            if not operacao.cte_data_emissao:
                logger.warning("CTe %s sem data emissao — skip", operacao.cte_numero)
                continue

            # Verificar duplicata
            existente = CarviaComissaoFechamentoCte.query.filter_by(
                fechamento_id=fechamento_id,
                operacao_id=operacao_id,
            ).first()

            valor_cte = Decimal(str(operacao.cte_valor))
            valor_comissao = (valor_cte * pct).quantize(Decimal('0.01'))

            if existente:
                if not existente.excluido:
                    logger.warning("CTe %s ja no fechamento — skip", operacao.cte_numero)
                    continue
                # Reativar
                existente.excluido = False
                existente.excluido_em = None
                existente.excluido_por = None
                existente.valor_cte_snapshot = valor_cte
                existente.percentual_snapshot = pct
                existente.valor_comissao = valor_comissao
                existente.incluido_por = incluido_por
                existente.incluido_em = agora_utc_naive()
            else:
                junction = CarviaComissaoFechamentoCte(
                    fechamento_id=fechamento_id,
                    operacao_id=operacao_id,
                    cte_numero=operacao.cte_numero or f'OP-{operacao.id}',
                    cte_data_emissao=operacao.cte_data_emissao,
                    valor_cte_snapshot=valor_cte,
                    percentual_snapshot=pct,
                    valor_comissao=valor_comissao,
                    incluido_por=incluido_por,
                )
                db.session.add(junction)

            incluidos += 1

        if incluidos == 0:
            raise ValueError('Nenhum CTe valido para incluir.')

        db.session.flush()
        fechamento.recalcular_totais()
        ComissaoService._sincronizar_despesa(fechamento)
        db.session.commit()

        logger.info(
            "%d CTes incluidos em %s por %s",
            incluidos, fechamento.numero_fechamento, incluido_por,
        )
        return incluidos

    # ------------------------------------------------------------------
    # Transicoes de status
    # ------------------------------------------------------------------

    @staticmethod
    def marcar_pago(fechamento_id, data_pagamento, pago_por):
        """Transiciona PENDENTE -> PAGO.

        Args:
            fechamento_id: int
            data_pagamento: date
            pago_por: str — email

        Raises:
            ValueError se transicao invalida.
        """
        from app.carvia.models.comissao import CarviaComissaoFechamento

        fechamento = db.session.get(CarviaComissaoFechamento, fechamento_id)
        if not fechamento:
            raise ValueError('Fechamento nao encontrado.')
        if fechamento.status != 'PENDENTE':
            raise ValueError(
                f'Nao e possivel pagar fechamento com status {fechamento.status}.'
            )
        if fechamento.qtd_ctes == 0:
            raise ValueError('Fechamento sem CTes — nao pode ser pago.')

        fechamento.status = 'PAGO'
        fechamento.data_pagamento = data_pagamento
        fechamento.pago_em = agora_utc_naive()
        fechamento.pago_por = pago_por
        db.session.commit()

        logger.info(
            "Comissao %s marcada como PAGO em %s por %s",
            fechamento.numero_fechamento, data_pagamento, pago_por,
        )

    @staticmethod
    def cancelar(fechamento_id, cancelado_por):
        """Transiciona PENDENTE -> CANCELADO.

        Se houver despesa vinculada PENDENTE, cancela junto.
        Se despesa ja PAGO (conciliada), nao cancela a despesa.

        Raises:
            ValueError se transicao invalida.
        """
        from app.carvia.models.comissao import CarviaComissaoFechamento
        from app.carvia.models import CarviaDespesa

        fechamento = db.session.get(CarviaComissaoFechamento, fechamento_id)
        if not fechamento:
            raise ValueError('Fechamento nao encontrado.')
        if fechamento.status == 'PAGO':
            raise ValueError('Nao e possivel cancelar fechamento ja pago.')
        if fechamento.status == 'CANCELADO':
            raise ValueError('Fechamento ja esta cancelado.')

        fechamento.status = 'CANCELADO'

        # Cancelar despesa vinculada (se PENDENTE)
        if fechamento.despesa_id:
            despesa = db.session.get(CarviaDespesa, fechamento.despesa_id)
            if despesa and despesa.status == 'PENDENTE':
                despesa.status = 'CANCELADO'
                logger.info(
                    "Despesa #%d cancelada junto com comissao %s",
                    despesa.id, fechamento.numero_fechamento,
                )
            elif despesa and despesa.status != 'PENDENTE':
                logger.warning(
                    "Despesa #%d nao cancelada (status=%s) — comissao %s cancelada sem propagar",
                    despesa.id, despesa.status, fechamento.numero_fechamento,
                )

        db.session.commit()

        logger.info(
            "Comissao %s cancelada por %s",
            fechamento.numero_fechamento, cancelado_por,
        )
