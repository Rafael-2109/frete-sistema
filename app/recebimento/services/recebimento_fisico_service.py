"""
Service para Recebimento Fisico (Fase 4)
=========================================

Responsabilidades:
- Listar pickings disponiveis do CACHE LOCAL (tabelas picking_recebimento_*)
- Buscar detalhes de um picking (refresh do Odoo + leitura do cache)
- Salvar recebimento local + enqueue job RQ (fire-and-forget)
- Validar que soma dos lotes = qtd esperada por produto
- Listar recebimentos com status
- Consultar status real no Odoo
- Retry de recebimentos com erro
"""

import logging
from datetime import datetime
from decimal import Decimal

from sqlalchemy import func

from app import db
from app.recebimento.models import (
    RecebimentoFisico,
    RecebimentoLote,
    RecebimentoQualityCheck,
    PickingRecebimento,
    PickingRecebimentoProduto,
    PickingRecebimentoMoveLine,
    PickingRecebimentoQualityCheck,
)
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


class RecebimentoFisicoService:
    """Service para operacoes de recebimento fisico."""

    # Company IDs conhecidos
    COMPANIES = {
        1: 'NACOM GOYA - FB',
        3: 'NACOM GOYA - SC',
        4: 'NACOM GOYA - CD',
        5: 'LA FAMIGLIA - LF',
    }

    # CNPJs de empresas do grupo (prefixos) a serem excluídos do recebimento
    # Pickings de fornecedores com esses prefixos são transferências internas
    CNPJS_GRUPO_INTERNO = ['61724241', '18467441']

    def buscar_pickings_disponiveis(self, company_id, filtro_nf=None, filtro_fornecedor=None,
                                     apenas_com_nf=False, pagina=1, por_pagina=50):
        """
        Busca pickings disponiveis do CACHE LOCAL (tabelas picking_recebimento_*).
        Dedup por purchase_order_id: mostra apenas o picking mais recente (write_date).
        Suporta paginacao server-side e filtro por NF vinculada.

        Args:
            company_id: ID da empresa no Odoo
            filtro_nf: Filtrar por numero de NF (origin do picking)
            filtro_fornecedor: Filtrar por nome do fornecedor
            apenas_com_nf: Se True, retorna apenas pickings com ValidacaoNfPoDfe
            pagina: Pagina atual (1-indexed)
            por_pagina: Itens por pagina (padrao 50)

        Returns:
            Dict com lista de pickings paginada + metadados de paginacao
        """
        try:
            from app.recebimento.models import ValidacaoNfPoDfe

            # Subquery: para cada PO, pegar o picking com maior write_date
            subq = db.session.query(
                PickingRecebimento.odoo_purchase_order_id,
                func.max(PickingRecebimento.write_date).label('max_write_date')
            ).filter(
                PickingRecebimento.company_id == company_id,
                PickingRecebimento.state == 'assigned',
            ).group_by(
                PickingRecebimento.odoo_purchase_order_id
            ).subquery()

            # Query principal: JOIN para pegar apenas o picking mais recente por PO
            query = PickingRecebimento.query.join(
                subq,
                db.and_(
                    PickingRecebimento.odoo_purchase_order_id == subq.c.odoo_purchase_order_id,
                    PickingRecebimento.write_date == subq.c.max_write_date,
                )
            ).filter(
                PickingRecebimento.company_id == company_id,
                PickingRecebimento.state == 'assigned',
            )

            # Aplicar filtros opcionais
            if filtro_nf:
                query = query.filter(PickingRecebimento.origin.ilike(f'%{filtro_nf}%'))

            if filtro_fornecedor:
                query = query.filter(PickingRecebimento.odoo_partner_name.ilike(f'%{filtro_fornecedor}%'))

            # Filtro apenas_com_nf: subquery para PO IDs que tem ValidacaoNfPoDfe
            if apenas_com_nf:
                po_ids_com_nf = db.session.query(
                    ValidacaoNfPoDfe.odoo_po_vinculado_id
                ).filter(
                    ValidacaoNfPoDfe.odoo_po_vinculado_id.isnot(None)
                ).union(
                    db.session.query(
                        ValidacaoNfPoDfe.po_consolidado_id
                    ).filter(
                        ValidacaoNfPoDfe.po_consolidado_id.isnot(None)
                    )
                ).subquery()

                query = query.filter(
                    PickingRecebimento.odoo_purchase_order_id.in_(
                        db.session.query(po_ids_com_nf)
                    )
                )

            # Excluir fornecedores do grupo interno (transferências entre empresas)
            # Pickings onde odoo_partner_cnpj inicia com prefixos do grupo são filtrados
            for cnpj_prefixo in self.CNPJS_GRUPO_INTERNO:
                query = query.filter(
                    db.or_(
                        PickingRecebimento.odoo_partner_cnpj.is_(None),
                        PickingRecebimento.odoo_partner_cnpj == '',
                        ~PickingRecebimento.odoo_partner_cnpj.like(f'{cnpj_prefixo}%')
                    )
                )

            # Ordenar
            query = query.order_by(PickingRecebimento.scheduled_date.desc())

            # Contar total ANTES de paginar
            total = query.count()

            # Paginar
            offset = (pagina - 1) * por_pagina
            pickings = query.offset(offset).limit(por_pagina).all()

            # Verificar quais ja tem recebimento local pendente/processando
            picking_ids = [p.odoo_picking_id for p in pickings]
            recebimentos_existentes = {}
            if picking_ids:
                existentes = RecebimentoFisico.query.filter(
                    RecebimentoFisico.odoo_picking_id.in_(picking_ids),
                    RecebimentoFisico.status.in_(['pendente', 'processando', 'processado'])
                ).all()
                for r in existentes:
                    recebimentos_existentes[r.odoo_picking_id] = r.status

            # Buscar ultima sincronizacao
            ultima_sync = db.session.query(
                func.max(PickingRecebimento.sincronizado_em)
            ).filter(
                PickingRecebimento.company_id == company_id
            ).scalar()

            resultado = []
            for p in pickings:
                # Contar produtos deste picking
                qtd_produtos = PickingRecebimentoProduto.query.filter_by(
                    picking_recebimento_id=p.id
                ).count()

                status_local = recebimentos_existentes.get(p.odoo_picking_id)
                resultado.append({
                    'id': p.odoo_picking_id,
                    'name': p.odoo_picking_name,
                    'partner_id': p.odoo_partner_id,
                    'partner_name': p.odoo_partner_name or 'Sem fornecedor',
                    'origin': p.origin or '',
                    'purchase_order_id': p.odoo_purchase_order_id,
                    'purchase_order_name': p.odoo_purchase_order_name or '',
                    'scheduled_date': p.scheduled_date.strftime('%Y-%m-%d %H:%M:%S') if p.scheduled_date else None,
                    'qtd_produtos': qtd_produtos,
                    'status_local': status_local,
                })

            # Validacao cross-phase: verificar fases 1→2→3 para cada picking
            from app.recebimento.services.cross_phase_validation_service import CrossPhaseValidationService
            validation_service = CrossPhaseValidationService()
            phase_statuses = validation_service.validar_fases_batch(pickings)

            for item in resultado:
                picking_id = item['id']
                phase = phase_statuses.get(picking_id)
                item['fase_validacao'] = {
                    'pode_receber': phase.pode_receber if phase else False,
                    'tem_nf': phase.tem_nf if phase else False,
                    'numero_nf': phase.numero_nf if phase else None,
                    'bloqueio_motivo': phase.bloqueio_motivo if phase else 'Erro no sistema',
                    'fase_bloqueio': phase.fase_bloqueio if phase else 0,
                    'tipo_liberacao': phase.tipo_liberacao if phase else None,
                }

            total_paginas = (total + por_pagina - 1) // por_pagina
            logger.info(
                f"Pickings company_id={company_id}: pagina {pagina}/{total_paginas} "
                f"({len(resultado)} de {total} total)"
            )
            return {
                'pickings': resultado,
                'total': total,
                'pagina': pagina,
                'por_pagina': por_pagina,
                'total_paginas': total_paginas,
                'ultima_sincronizacao': ultima_sync.strftime('%d/%m/%Y %H:%M') if ultima_sync else None,
            }

        except Exception as e:
            logger.error(f"Erro ao buscar pickings do cache: {e}")
            raise

    def buscar_detalhes_picking(self, picking_id):
        """
        Busca detalhes completos de um picking para preenchimento.
        1. Faz refresh do Odoo (busca dados frescos e atualiza cache local)
        2. Le dados do cache local atualizado

        Retorna:
        - Dados do picking (fornecedor, PO, data)
        - Produtos com quantidades esperadas e tracking
        - Quality checks configurados (passfail e measure)
        """
        try:
            # 1. Refresh: buscar dados frescos do Odoo e atualizar cache
            from app.recebimento.services.picking_recebimento_sync_service import PickingRecebimentoSyncService
            sync_service = PickingRecebimentoSyncService()
            sync_service.refresh_picking(picking_id)

            # 2. Ler do cache atualizado
            picking_local = PickingRecebimento.query.filter_by(
                odoo_picking_id=picking_id
            ).first()

            if not picking_local:
                raise ValueError(f"Picking {picking_id} nao encontrado no cache local")

            if picking_local.state != 'assigned':
                raise ValueError(
                    f"Picking {picking_local.odoo_picking_name} nao esta pronto para recebimento "
                    f"(state={picking_local.state}, esperado=assigned)"
                )

            # 3. Montar lista de produtos do cache
            produtos_local = PickingRecebimentoProduto.query.filter_by(
                picking_recebimento_id=picking_local.id
            ).all()

            produtos_resultado = []
            for prod in produtos_local:
                # Buscar move_lines deste produto
                lines = PickingRecebimentoMoveLine.query.filter_by(
                    produto_id=prod.id
                ).all()

                produtos_resultado.append({
                    'move_id': prod.odoo_move_id,
                    'product_id': prod.odoo_product_id,
                    'product_name': prod.odoo_product_name or 'Sem produto',
                    'qtd_esperada': float(prod.product_uom_qty) if prod.product_uom_qty else 0,
                    'product_uom': prod.product_uom or 'UN',
                    'tracking': prod.tracking or 'none',
                    'use_expiration_date': prod.use_expiration_date or False,
                    'move_lines': [{
                        'id': ml.odoo_move_line_id,
                        'lot_id': ml.lot_id,
                        'lot_name': ml.lot_name or '',
                        'quantity': float(ml.quantity) if ml.quantity else 0,
                        'reserved_qty': float(ml.reserved_uom_qty) if ml.reserved_uom_qty else 0,
                        'location_id': ml.location_id,
                        'location_dest_id': ml.location_dest_id,
                    } for ml in lines],
                })

            # 4. Buscar quality checks do cache
            checks_local = PickingRecebimentoQualityCheck.query.filter_by(
                picking_recebimento_id=picking_local.id
            ).all()

            checks_resultado = []
            for qc in checks_local:
                checks_resultado.append({
                    'id': qc.odoo_check_id,
                    'name': qc.title or '',
                    'title': qc.title or '',
                    'product_id': qc.odoo_product_id,
                    'product_name': qc.odoo_product_name or 'Operacao',
                    'point_id': qc.odoo_point_id,
                    'quality_state': qc.quality_state or 'none',
                    'test_type': qc.test_type or 'passfail',
                    'norm_unit': qc.norm_unit or '',
                    'tolerance_min': float(qc.tolerance_min) if qc.tolerance_min else 0,
                    'tolerance_max': float(qc.tolerance_max) if qc.tolerance_max else 0,
                })

            # Validacao cross-phase: diagnostico completo para o operador
            from app.recebimento.services.cross_phase_validation_service import CrossPhaseValidationService
            validation_service = CrossPhaseValidationService()
            phase_status = validation_service.validar_fases_picking(
                picking_local.odoo_purchase_order_id,
                picking_local.origin,
            )

            # Se encontrou validacao_id, incluir para auto-preenchimento
            validacao_id_auto = phase_status.fase2_validacao_id if phase_status else None

            return {
                'picking': {
                    'id': picking_local.odoo_picking_id,
                    'name': picking_local.odoo_picking_name,
                    'partner_id': picking_local.odoo_partner_id,
                    'partner_name': picking_local.odoo_partner_name or '',
                    'origin': picking_local.origin or '',
                    'purchase_order_id': picking_local.odoo_purchase_order_id,
                    'purchase_order_name': picking_local.odoo_purchase_order_name or '',
                    'scheduled_date': picking_local.scheduled_date.strftime('%Y-%m-%d %H:%M:%S') if picking_local.scheduled_date else None,
                    'company_id': picking_local.company_id,
                    'location_id': picking_local.location_id,
                    'location_dest_id': picking_local.location_dest_id,
                    'numero_nf_vinculada': phase_status.numero_nf if phase_status else None,
                },
                'produtos': produtos_resultado,
                'quality_checks': checks_resultado,
                'validacao_fases': phase_status.to_dict() if phase_status else None,
                'validacao_id_sugerido': validacao_id_auto,
            }

        except Exception as e:
            logger.error(f"Erro ao buscar detalhes do picking {picking_id}: {e}")
            raise

    def validar_lotes(self, produtos_lotes):
        """
        Valida que a soma dos lotes = quantidade esperada para cada produto.

        Args:
            produtos_lotes: Lista de {product_id, qtd_esperada, lotes: [{nome, qtd}]}

        Returns:
            (valido: bool, erros: list)
        """
        erros = []

        for produto in produtos_lotes:
            qtd_esperada = Decimal(str(produto['qtd_esperada']))
            soma_lotes = sum(
                Decimal(str(l['quantidade']))
                for l in produto['lotes']
            )

            if soma_lotes != qtd_esperada:
                erros.append({
                    'product_id': produto['product_id'],
                    'product_name': produto.get('product_name', ''),
                    'qtd_esperada': float(qtd_esperada),
                    'soma_lotes': float(soma_lotes),
                    'diferenca': float(qtd_esperada - soma_lotes),
                })

            # Validar que cada lote tem nome
            for lote in produto['lotes']:
                if not lote.get('nome', '').strip():
                    erros.append({
                        'product_id': produto['product_id'],
                        'product_name': produto.get('product_name', ''),
                        'erro': 'Lote sem nome',
                    })

        return len(erros) == 0, erros

    def salvar_recebimento(self, dados, usuario=None):
        """
        Salva recebimento localmente e enfileira job RQ.

        Args:
            dados: {
                picking_id, picking_name, purchase_order_id, purchase_order_name,
                partner_id, partner_name, company_id, numero_nf, validacao_id,
                lotes: [{product_id, product_name, move_line_id, move_id,
                         lote_nome, quantidade, data_validade, tracking}],
                quality_checks: [{check_id, point_id, product_id, test_type,
                                  titulo, resultado, valor_medido, unidade,
                                  tolerancia_min, tolerancia_max}],
            }
            usuario: Nome do usuario

        Returns:
            RecebimentoFisico criado
        """
        try:
            # Verificar se ja existe recebimento pendente/processando para este picking
            existente = RecebimentoFisico.query.filter_by(
                odoo_picking_id=dados['picking_id'],
            ).filter(
                RecebimentoFisico.status.in_(['pendente', 'processando'])
            ).first()

            if existente:
                raise ValueError(
                    f"Ja existe recebimento {existente.status} para picking "
                    f"{dados.get('picking_name', dados['picking_id'])} (ID local: {existente.id})"
                )

            # VALIDACAO CROSS-PHASE (BLOQUEANTE)
            # Verifica se Fases 1→2→3 foram concluidas antes de permitir Fase 4
            if dados.get('purchase_order_id'):
                from app.recebimento.services.cross_phase_validation_service import CrossPhaseValidationService
                validation_service = CrossPhaseValidationService()
                phase_status = validation_service.validar_fases_picking(
                    dados['purchase_order_id'],
                    dados.get('origin'),
                )

                if not phase_status.pode_receber:
                    raise ValueError(
                        f"Recebimento bloqueado - {phase_status.bloqueio_motivo}. "
                        f"Contato para resolver: {phase_status.contato_resolucao}"
                    )

                # Auto-preencher validacao_id se encontrou e nao foi informado
                if phase_status.fase2_validacao_id and not dados.get('validacao_id'):
                    dados['validacao_id'] = phase_status.fase2_validacao_id

            # Criar recebimento
            recebimento = RecebimentoFisico(
                odoo_picking_id=dados['picking_id'],
                odoo_picking_name=dados.get('picking_name'),
                odoo_purchase_order_id=dados.get('purchase_order_id'),
                odoo_purchase_order_name=dados.get('purchase_order_name'),
                odoo_partner_id=dados.get('partner_id'),
                odoo_partner_name=dados.get('partner_name'),
                company_id=dados['company_id'],
                validacao_id=dados.get('validacao_id'),
                numero_nf=dados.get('numero_nf'),
                status='pendente',
                usuario=usuario,
            )
            db.session.add(recebimento)
            db.session.flush()  # Obter ID

            # Criar lotes
            for lote_data in dados.get('lotes', []):
                lote = RecebimentoLote(
                    recebimento_id=recebimento.id,
                    odoo_product_id=lote_data['product_id'],
                    odoo_product_name=lote_data.get('product_name'),
                    odoo_move_line_id=lote_data.get('move_line_id'),
                    odoo_move_id=lote_data.get('move_id'),
                    lote_nome=lote_data['lote_nome'],
                    quantidade=lote_data['quantidade'],
                    data_validade=lote_data.get('data_validade'),
                    produto_tracking=lote_data.get('tracking', 'lot'),
                )
                db.session.add(lote)

            # Criar quality checks
            for qc_data in dados.get('quality_checks', []):
                qc = RecebimentoQualityCheck(
                    recebimento_id=recebimento.id,
                    odoo_check_id=qc_data['check_id'],
                    odoo_point_id=qc_data.get('point_id'),
                    odoo_product_id=qc_data.get('product_id'),
                    test_type=qc_data['test_type'],
                    titulo=qc_data.get('titulo'),
                    resultado=qc_data['resultado'],
                    valor_medido=qc_data.get('valor_medido'),
                    unidade=qc_data.get('unidade'),
                    tolerancia_min=qc_data.get('tolerancia_min'),
                    tolerancia_max=qc_data.get('tolerancia_max'),
                )
                db.session.add(qc)

            db.session.commit()

            # Enfileirar job RQ (fire-and-forget) com retry automatico
            try:
                from app.recebimento.workers.recebimento_fisico_jobs import processar_recebimento_job
                from app.portal.workers import enqueue_job
                from rq import Retry

                # Retry com backoff exponencial: 30s, 2min, 8min
                # Resolve problemas temporarios de timeout/indisponibilidade do Odoo
                retry_config = Retry(max=3, interval=[30, 120, 480])

                job = enqueue_job(
                    processar_recebimento_job,
                    recebimento.id,
                    usuario,
                    queue_name='recebimento',
                    timeout='15m',  # Aumentado para dar margem a operacoes lentas
                    retry=retry_config,
                )
                recebimento.job_id = job.id
                db.session.commit()
                logger.info(f"Job RQ enfileirado: {job.id} para recebimento {recebimento.id}")
            except Exception as e_job:
                logger.warning(f"Nao foi possivel enfileirar job RQ: {e_job}. "
                               f"Recebimento {recebimento.id} fica 'pendente' para retry manual.")

            logger.info(
                f"Recebimento {recebimento.id} salvo para picking {recebimento.odoo_picking_name} "
                f"({len(dados.get('lotes', []))} lotes, "
                f"{len(dados.get('quality_checks', []))} quality checks)"
            )

            return recebimento

        except ValueError:
            raise
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao salvar recebimento: {e}")
            raise

    def listar_recebimentos(self, company_id=None, status=None, limit=50):
        """
        Lista recebimentos locais com filtros.

        Args:
            company_id: Filtrar por empresa
            status: Filtrar por status (pendente, processando, processado, erro)
            limit: Limite de resultados

        Returns:
            Lista de recebimentos serializados
        """
        query = RecebimentoFisico.query

        if company_id:
            query = query.filter_by(company_id=company_id)

        if status:
            query = query.filter_by(status=status)

        recebimentos = query.order_by(
            RecebimentoFisico.criado_em.desc()
        ).limit(limit).all()

        return [r.to_dict() for r in recebimentos]

    def consultar_status_odoo(self, recebimento_id):
        """
        Consulta estado real do picking no Odoo para verificar processamento.

        Returns:
            Dict com estado atual do picking no Odoo
        """
        try:
            recebimento = RecebimentoFisico.query.get(recebimento_id)
            if not recebimento:
                raise ValueError(f"Recebimento {recebimento_id} nao encontrado")

            odoo = get_odoo_connection()
            picking = odoo.execute_kw(
                'stock.picking', 'search_read',
                [[['id', '=', recebimento.odoo_picking_id]]],
                {
                    'fields': ['id', 'name', 'state', 'date_done'],
                    'limit': 1,
                }
            )

            if not picking:
                return {
                    'recebimento_id': recebimento_id,
                    'odoo_state': 'nao_encontrado',
                    'message': f'Picking {recebimento.odoo_picking_id} nao encontrado no Odoo',
                }

            p = picking[0]
            return {
                'recebimento_id': recebimento_id,
                'odoo_picking_id': p['id'],
                'odoo_picking_name': p['name'],
                'odoo_state': p['state'],
                'date_done': p.get('date_done'),
                'status_local': recebimento.status,
            }

        except Exception as e:
            logger.error(f"Erro ao consultar status Odoo para recebimento {recebimento_id}: {e}")
            raise

    def retry_recebimento(self, recebimento_id):
        """
        Reseta status para 'pendente' e re-enfileira job RQ.

        Returns:
            RecebimentoFisico atualizado
        """
        try:
            recebimento = RecebimentoFisico.query.get(recebimento_id)
            if not recebimento:
                raise ValueError(f"Recebimento {recebimento_id} nao encontrado")

            if recebimento.status not in ('erro', 'cancelado'):
                raise ValueError(
                    f"Recebimento {recebimento_id} nao pode ser retentado "
                    f"(status atual: {recebimento.status})"
                )

            if recebimento.tentativas >= recebimento.max_tentativas:
                raise ValueError(
                    f"Recebimento {recebimento_id} excedeu max tentativas "
                    f"({recebimento.tentativas}/{recebimento.max_tentativas})"
                )

            # Resetar status
            recebimento.status = 'pendente'
            recebimento.erro_mensagem = None

            # Resetar processamento dos lotes e checks
            for lote in recebimento.lotes.all():
                lote.processado = False
            for qc in recebimento.quality_checks.all():
                qc.processado = False

            db.session.commit()

            # Re-enfileirar job com retry automatico
            try:
                from app.recebimento.workers.recebimento_fisico_jobs import processar_recebimento_job
                from app.portal.workers import enqueue_job
                from rq import Retry

                # Retry com backoff exponencial: 30s, 2min, 8min
                retry_config = Retry(max=3, interval=[30, 120, 480])

                job = enqueue_job(
                    processar_recebimento_job,
                    recebimento.id,
                    recebimento.usuario,
                    queue_name='recebimento',
                    timeout='15m',
                    retry=retry_config,
                )
                recebimento.job_id = job.id
                db.session.commit()
                logger.info(f"Retry: Job RQ {job.id} enfileirado para recebimento {recebimento.id}")
            except Exception as e_job:
                logger.warning(f"Nao foi possivel re-enfileirar job: {e_job}")

            return recebimento

        except ValueError:
            raise
        except Exception as e:
            db.session.rollback()
            logger.error(f"Erro ao retentar recebimento {recebimento_id}: {e}")
            raise
