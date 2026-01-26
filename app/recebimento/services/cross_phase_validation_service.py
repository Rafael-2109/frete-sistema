"""
CrossPhaseValidationService - Validacao de Dependencias entre Fases
===================================================================

Verifica se as Fases 1, 2 e 3 do recebimento de materiais foram
concluidas antes de permitir a Fase 4 (Recebimento Fisico).

Pipeline obrigatorio:
    Fase 0 (NF no sistema) → Fase 1 (Fiscal) → Fase 2 (Match NF×PO) → Fase 3 (Consolidacao) → Fase 4 (Recebimento)

Regras:
    - TODO picking deve ter PO vinculado a uma NF no sistema para prosseguir.
    - Pickings sem PO ou sem NF no sistema = BLOQUEADO (fase_bloqueio=0).
    - status='aprovado' NAO e pass-through! Requer consolidacao explicita.
    - Operador recebe mensagem curta e direta com contato para resolucao.
"""

import logging
from datetime import datetime

from app import db
from app.recebimento.models import ValidacaoFiscalDfe, ValidacaoNfPoDfe

logger = logging.getLogger(__name__)


class PhaseStatus:
    """Resultado da validacao de fases para um picking."""

    def __init__(self):
        # Veredicto
        self.pode_receber = False
        self.tipo_liberacao = None    # 'full', 'finalizado_odoo'
        self.bloqueio_motivo = None   # Mensagem curta para operador
        self.contato_resolucao = None

        # NF vinculada (extraida do DFe via PO)
        self.numero_nf = None         # Numero da NF para exibicao
        self.tem_nf = False           # Se tem NF vinculada no sistema

        # Fases (simplificado)
        self.fase1_aprovado = False
        self.fase2_aprovado = False
        self.fase3_aprovado = False
        self.fase_bloqueio = None     # 0, 1, 2 ou 3 (qual fase bloqueia)

        # Info para modal (detalhes)
        self.fase2_validacao_id = None
        self.fase3_status = None
        self.fase3_po_consolidado = None

    def to_dict(self):
        """Serializa para enviar ao frontend."""
        return {
            'pode_receber': self.pode_receber,
            'tipo_liberacao': self.tipo_liberacao,
            'bloqueio_motivo': self.bloqueio_motivo,
            'contato_resolucao': self.contato_resolucao,
            'numero_nf': self.numero_nf,
            'tem_nf': self.tem_nf,
            'fase_bloqueio': self.fase_bloqueio,
            'fase1_aprovado': self.fase1_aprovado,
            'fase2_aprovado': self.fase2_aprovado,
            'fase3_aprovado': self.fase3_aprovado,
            'fase2_validacao_id': self.fase2_validacao_id,
            'fase3_status': self.fase3_status,
            'fase3_po_consolidado': self.fase3_po_consolidado,
        }


class CrossPhaseValidationService:
    """
    Valida dependencias entre fases do recebimento de materiais.

    Lookup:
        PickingRecebimento.odoo_purchase_order_id
            → ValidacaoNfPoDfe.odoo_po_vinculado_id OU po_consolidado_id
            → ValidacaoFiscalDfe.odoo_dfe_id (via ValidacaoNfPoDfe.odoo_dfe_id)
    """

    # Statuses que significam "fase 2 passou" (match identificado)
    STATUSES_FASE2_OK = {'aprovado', 'consolidado', 'finalizado_odoo'}

    # Statuses que significam "fase 3 completou" (consolidacao feita OU nao necessaria)
    STATUSES_FASE3_OK = {'consolidado', 'finalizado_odoo'}

    # Prioridade de status (menor = melhor)
    PRIORIDADE_STATUS = {
        'consolidado': 1,
        'finalizado_odoo': 2,
        'aprovado': 3,
        'bloqueado': 4,
        'validando': 5,
        'pendente': 6,
        'erro': 7,
    }

    def validar_fases_picking(self, purchase_order_id, origin=None):
        """
        Valida todas as fases para um picking.

        Args:
            purchase_order_id: ID do PO no Odoo (de PickingRecebimento.odoo_purchase_order_id)
            origin: Campo origin do picking (nao utilizado atualmente)

        Returns:
            PhaseStatus com veredicto e mensagem simplificada
        """
        status = PhaseStatus()

        if not purchase_order_id:
            # Picking sem PO = BLOQUEADO (sem NF vinculada)
            status.pode_receber = False
            status.tem_nf = False
            status.fase_bloqueio = 0
            status.bloqueio_motivo = 'Picking sem NF vinculada'
            return status

        try:
            # 1. Buscar ValidacaoNfPoDfe pelo PO do picking
            validacao = self._buscar_validacao_nf_po(purchase_order_id)

            if not validacao:
                # PO existe mas sem DFe no sistema = BLOQUEADO
                status.pode_receber = False
                status.tem_nf = False
                status.fase_bloqueio = 0
                status.bloqueio_motivo = 'NF nao encontrada no sistema'
                return status

            # NF encontrada no sistema
            status.tem_nf = True
            status.numero_nf = validacao.numero_nf

            # 2. Preencher info Fase 2
            status.fase2_validacao_id = validacao.id
            status.fase2_aprovado = validacao.status in self.STATUSES_FASE2_OK

            # 3. Buscar ValidacaoFiscalDfe pela DFE (Fase 1)
            fiscal = None
            if validacao.odoo_dfe_id:
                fiscal = ValidacaoFiscalDfe.query.filter_by(
                    odoo_dfe_id=validacao.odoo_dfe_id
                ).first()

            if fiscal:
                status.fase1_aprovado = (fiscal.status == 'aprovado')
            else:
                status.fase1_aprovado = False

            # 4. Avaliar Fase 3 (Consolidacao)
            if validacao.status == 'consolidado':
                status.fase3_status = 'consolidado'
                status.fase3_po_consolidado = validacao.po_consolidado_name
                status.fase3_aprovado = True
            elif validacao.status == 'finalizado_odoo':
                status.fase3_status = 'finalizado_odoo'
                status.fase3_po_consolidado = validacao.odoo_po_vinculado_name
                status.fase3_aprovado = True
            elif validacao.status == 'aprovado':
                # Match 100% mas consolidacao NAO foi executada ainda!
                status.fase3_status = 'aguardando_consolidacao'
                status.fase3_aprovado = False
            else:
                status.fase3_status = 'pendente'
                status.fase3_aprovado = False

            # 5. Veredicto final (ordem de prioridade: Fase 1 → Fase 2 → Fase 3)
            self._definir_veredicto(status, fiscal, validacao)

            return status

        except Exception as e:
            logger.error(f"Erro na validacao cross-phase para PO {purchase_order_id}: {e}")
            # Em caso de erro interno, BLOQUEAR (nao liberar)
            status.pode_receber = False
            status.tem_nf = False
            status.fase_bloqueio = 0
            status.bloqueio_motivo = 'Erro no sistema - Falar com Logistica'
            status.contato_resolucao = 'Logistica'
            return status

    def validar_fases_batch(self, pickings):
        """
        Valida fases para multiplos pickings em 2 queries (sem N+1).

        Args:
            pickings: Lista de objetos PickingRecebimento

        Returns:
            Dict: {odoo_picking_id: PhaseStatus}
        """
        po_ids = [p.odoo_purchase_order_id for p in pickings if p.odoo_purchase_order_id]

        if not po_ids:
            # Todos sem PO = BLOQUEADOS
            return {p.odoo_picking_id: self._make_blocked_status(
                'Picking sem NF vinculada', fase=0
            ) for p in pickings}

        try:
            # Query 1: Todas as ValidacaoNfPoDfe que matcham algum PO
            validacoes = ValidacaoNfPoDfe.query.filter(
                db.or_(
                    ValidacaoNfPoDfe.odoo_po_vinculado_id.in_(po_ids),
                    ValidacaoNfPoDfe.po_consolidado_id.in_(po_ids),
                )
            ).all()

            # Cache: po_id -> validacao (priorizar por status mais avancado)
            po_to_validacao = {}
            for v in validacoes:
                for po_id in [v.odoo_po_vinculado_id, v.po_consolidado_id]:
                    if po_id and po_id in po_ids:
                        existing = po_to_validacao.get(po_id)
                        if not existing or self._prioridade(v.status) < self._prioridade(existing.status):
                            po_to_validacao[po_id] = v

            # Query 2: Todas as ValidacaoFiscalDfe para DFEs encontradas
            dfe_ids = [v.odoo_dfe_id for v in validacoes if v.odoo_dfe_id]
            fiscais_by_dfe = {}
            if dfe_ids:
                fiscais = ValidacaoFiscalDfe.query.filter(
                    ValidacaoFiscalDfe.odoo_dfe_id.in_(dfe_ids)
                ).all()
                fiscais_by_dfe = {f.odoo_dfe_id: f for f in fiscais}

            # Identificar POs que não têm ValidacaoNfPoDfe para buscar fallback
            po_ids_sem_validacao = []
            for p in pickings:
                po_id = p.odoo_purchase_order_id
                if po_id and po_id not in po_to_validacao:
                    po_ids_sem_validacao.append(po_id)

            # Buscar NFs via PO.dfe_id (fallback) para POs sem validação local
            nfs_fallback = {}
            if po_ids_sem_validacao:
                nfs_fallback = self._buscar_nfs_via_po_dfe_batch(po_ids_sem_validacao)

            # Montar resultado por picking
            results = {}
            for p in pickings:
                po_id = p.odoo_purchase_order_id
                if not po_id:
                    results[p.odoo_picking_id] = self._make_blocked_status(
                        'Picking sem NF vinculada', fase=0
                    )
                    continue

                validacao = po_to_validacao.get(po_id)
                if not validacao:
                    # Tentar fallback via PO.dfe_id
                    nf_fallback = nfs_fallback.get(po_id)
                    if nf_fallback:
                        # Tem NF via PO.dfe_id mas sem validação local
                        # Criar status bloqueado mas com NF exibida
                        status = PhaseStatus()
                        status.pode_receber = False
                        status.tem_nf = True
                        status.numero_nf = nf_fallback
                        status.fase_bloqueio = 2
                        status.bloqueio_motivo = 'Validacao Compras - Falar com Compras'
                        status.contato_resolucao = 'Compras'
                        results[p.odoo_picking_id] = status
                    else:
                        results[p.odoo_picking_id] = self._make_blocked_status(
                            'NF nao encontrada no sistema', fase=0
                        )
                    continue

                fiscal = fiscais_by_dfe.get(validacao.odoo_dfe_id) if validacao.odoo_dfe_id else None
                results[p.odoo_picking_id] = self._build_phase_status(validacao, fiscal)

            return results

        except Exception as e:
            logger.error(f"Erro no batch de validacao cross-phase: {e}")
            # Em caso de erro, BLOQUEAR todos
            return {p.odoo_picking_id: self._make_blocked_status(
                'Erro no sistema - Falar com Logistica', fase=0, contato='Logistica'
            ) for p in pickings}

    # ===== Metodos Privados =====

    def _buscar_validacao_nf_po(self, purchase_order_id):
        """Busca ValidacaoNfPoDfe pelo PO, priorizando status mais avancado."""
        return ValidacaoNfPoDfe.query.filter(
            db.or_(
                ValidacaoNfPoDfe.odoo_po_vinculado_id == purchase_order_id,
                ValidacaoNfPoDfe.po_consolidado_id == purchase_order_id,
            )
        ).order_by(
            db.case(
                (ValidacaoNfPoDfe.status == 'consolidado', 1),
                (ValidacaoNfPoDfe.status == 'finalizado_odoo', 2),
                (ValidacaoNfPoDfe.status == 'aprovado', 3),
                else_=4,
            ),
            ValidacaoNfPoDfe.validado_em.desc()
        ).first()

    def _definir_veredicto(self, status, fiscal, validacao):
        """Define pode_receber, bloqueio_motivo e contato_resolucao."""

        # Fase 1 nao aprovada
        if not status.fase1_aprovado:
            status.pode_receber = False
            if fiscal:
                fase1_status = fiscal.status
                if fase1_status == 'primeira_compra':
                    status.bloqueio_motivo = 'Aguardando Fiscal cadastrar - Falar com Fiscal'
                    status.contato_resolucao = 'Fiscal'
                elif fase1_status in ('bloqueado', 'divergencia'):
                    status.bloqueio_motivo = 'Divergencia fiscal - Falar com Fiscal'
                    status.contato_resolucao = 'Fiscal'
                elif fase1_status == 'erro':
                    status.bloqueio_motivo = 'Erro no sistema - Falar com Logistica'
                    status.contato_resolucao = 'Logistica'
                else:
                    # pendente, validando, nao_executada
                    status.bloqueio_motivo = 'Aguardando validacao fiscal'
                    status.contato_resolucao = None
            else:
                status.bloqueio_motivo = 'Aguardando validacao fiscal'
                status.contato_resolucao = None
            status.fase_bloqueio = 1
            return

        # Fase 2 nao aprovada
        if not status.fase2_aprovado:
            status.pode_receber = False
            validacao_status = validacao.status if validacao else 'pendente'
            if validacao_status in ('bloqueado', 'divergencia'):
                status.bloqueio_motivo = 'Divergencia na NF c/ Pedido - Falar com Compras'
                status.contato_resolucao = 'Compras'
            elif validacao_status == 'erro':
                status.bloqueio_motivo = 'Erro no sistema - Falar com Logistica'
                status.contato_resolucao = 'Logistica'
            else:
                # pendente, validando
                status.bloqueio_motivo = 'Validacao Compras - Falar com Compras'
                status.contato_resolucao = 'Compras'
            status.fase_bloqueio = 2
            return

        # Fase 3 nao aprovada
        if not status.fase3_aprovado:
            status.pode_receber = False
            status.bloqueio_motivo = 'Falta arrumar o Pedido - Falar com Compras'
            status.contato_resolucao = 'Compras'
            status.fase_bloqueio = 3
            return

        # Todas as fases OK
        status.pode_receber = True
        status.fase_bloqueio = None
        if status.fase3_status == 'finalizado_odoo':
            status.tipo_liberacao = 'finalizado_odoo'
        else:
            status.tipo_liberacao = 'full'

    def _build_phase_status(self, validacao, fiscal):
        """Constroi PhaseStatus a partir de validacao e fiscal encontrados."""
        status = PhaseStatus()

        # NF
        status.tem_nf = True
        status.numero_nf = validacao.numero_nf

        # Fase 2
        status.fase2_validacao_id = validacao.id
        status.fase2_aprovado = validacao.status in self.STATUSES_FASE2_OK

        # Fase 1
        if fiscal:
            status.fase1_aprovado = (fiscal.status == 'aprovado')
        else:
            status.fase1_aprovado = False

        # Fase 3
        if validacao.status == 'consolidado':
            status.fase3_status = 'consolidado'
            status.fase3_po_consolidado = validacao.po_consolidado_name
            status.fase3_aprovado = True
        elif validacao.status == 'finalizado_odoo':
            status.fase3_status = 'finalizado_odoo'
            status.fase3_po_consolidado = validacao.odoo_po_vinculado_name
            status.fase3_aprovado = True
        elif validacao.status == 'aprovado':
            status.fase3_status = 'aguardando_consolidacao'
            status.fase3_aprovado = False
        else:
            status.fase3_status = 'pendente'
            status.fase3_aprovado = False

        # Veredicto
        self._definir_veredicto(status, fiscal, validacao)

        return status

    def _make_blocked_status(self, motivo, fase=0, contato=None):
        """Cria PhaseStatus bloqueado (sem NF ou sem PO)."""
        status = PhaseStatus()
        status.pode_receber = False
        status.tem_nf = False
        status.fase_bloqueio = fase
        status.bloqueio_motivo = motivo
        status.contato_resolucao = contato
        return status

    def _prioridade(self, status_str):
        """Retorna prioridade numerica de um status (menor = melhor)."""
        return self.PRIORIDADE_STATUS.get(status_str, 99)

    def _buscar_nf_via_po_dfe(self, purchase_order_id: int):
        """
        Busca número da NF diretamente no Odoo via PO.dfe_id.
        Fallback quando não há ValidacaoNfPoDfe.

        Campos Odoo:
        - purchase.order.dfe_id → many2one para l10n_br_ciel_it_account.dfe
        - l10n_br_ciel_it_account.dfe.nfe_infnfe_ide_nnf → número da NF

        Args:
            purchase_order_id: ID do PO no Odoo

        Returns:
            str: Número da NF ou None se não encontrado
        """
        try:
            from app.odoo.utils.connection import get_odoo_connection

            odoo = get_odoo_connection()
            if not odoo.authenticate():
                logger.warning("Falha na autenticacao com Odoo para buscar NF via PO.dfe_id")
                return None

            # Buscar PO com dfe_id
            pos = odoo.execute_kw(
                'purchase.order', 'search_read',
                [[['id', '=', purchase_order_id]]],
                {'fields': ['dfe_id'], 'limit': 1}
            )

            if not pos or not pos[0].get('dfe_id'):
                return None

            # dfe_id é many2one: [id, name] ou id
            dfe_id_data = pos[0]['dfe_id']
            dfe_id = dfe_id_data[0] if isinstance(dfe_id_data, (list, tuple)) else dfe_id_data

            if not dfe_id:
                return None

            # Buscar DFe para obter número da NF
            dfes = odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe', 'search_read',
                [[['id', '=', dfe_id]]],
                {'fields': ['nfe_infnfe_ide_nnf'], 'limit': 1}
            )

            if dfes and dfes[0].get('nfe_infnfe_ide_nnf'):
                return str(dfes[0]['nfe_infnfe_ide_nnf'])

            return None

        except Exception as e:
            logger.warning(f"Erro ao buscar NF via PO.dfe_id para PO {purchase_order_id}: {e}")
            return None

    def _buscar_nfs_via_po_dfe_batch(self, po_ids: list) -> dict:
        """
        Busca números de NF via PO.dfe_id em batch para múltiplos POs.
        Otimização para evitar N+1 queries.

        Args:
            po_ids: Lista de IDs de POs no Odoo

        Returns:
            Dict: {po_id: numero_nf} para POs que têm dfe_id
        """
        if not po_ids:
            return {}

        try:
            from app.odoo.utils.connection import get_odoo_connection

            odoo = get_odoo_connection()
            if not odoo.authenticate():
                logger.warning("Falha na autenticacao com Odoo para buscar NFs via PO.dfe_id batch")
                return {}

            # Buscar todos os POs com seus dfe_id
            pos = odoo.execute_kw(
                'purchase.order', 'search_read',
                [[['id', 'in', list(po_ids)]]],
                {'fields': ['id', 'dfe_id']}
            )

            if not pos:
                return {}

            # Mapear PO -> dfe_id
            po_to_dfe = {}
            dfe_ids = set()
            for po in pos:
                dfe_id_data = po.get('dfe_id')
                if dfe_id_data:
                    dfe_id = dfe_id_data[0] if isinstance(dfe_id_data, (list, tuple)) else dfe_id_data
                    if dfe_id:
                        po_to_dfe[po['id']] = dfe_id
                        dfe_ids.add(dfe_id)

            if not dfe_ids:
                return {}

            # Buscar DFes para obter números das NFs
            dfes = odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe', 'search_read',
                [[['id', 'in', list(dfe_ids)]]],
                {'fields': ['id', 'nfe_infnfe_ide_nnf']}
            )

            # Mapear dfe_id -> numero_nf
            dfe_to_nf = {}
            for dfe in dfes:
                if dfe.get('nfe_infnfe_ide_nnf'):
                    dfe_to_nf[dfe['id']] = str(dfe['nfe_infnfe_ide_nnf'])

            # Montar resultado: po_id -> numero_nf
            resultado = {}
            for po_id, dfe_id in po_to_dfe.items():
                nf = dfe_to_nf.get(dfe_id)
                if nf:
                    resultado[po_id] = nf

            logger.info(f"   Batch NF via PO.dfe_id: {len(resultado)} NFs encontradas de {len(po_ids)} POs")
            return resultado

        except Exception as e:
            logger.warning(f"Erro ao buscar NFs via PO.dfe_id batch: {e}")
            return {}
