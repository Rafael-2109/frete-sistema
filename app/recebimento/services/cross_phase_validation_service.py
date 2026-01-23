"""
CrossPhaseValidationService - Validacao de Dependencias entre Fases
===================================================================

Verifica se as Fases 1, 2 e 3 do recebimento de materiais foram
concluidas antes de permitir a Fase 4 (Recebimento Fisico).

Pipeline obrigatorio:
    Fase 1 (Fiscal) → Fase 2 (Match NF×PO) → Fase 3 (Consolidacao) → Fase 4 (Recebimento)

Regras:
    - Fase 4 so pode executar se Fase 3 completou (status='consolidado' ou 'finalizado_odoo')
    - status='aprovado' NAO e pass-through! Requer consolidacao explicita.
    - Pickings antigos sem DFE no sistema sao liberados como 'legacy' (com warning).
    - Operador recebe diagnostico detalhado com contato para resolucao.
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
        self.tipo_liberacao = None  # 'full', 'finalizado_odoo', 'legacy'
        self.bloqueio_motivo = None
        self.contato_resolucao = None

        # Fase 1 (Validacao Fiscal)
        self.fase1_status = None
        self.fase1_numero_nf = None
        self.fase1_aprovado = False

        # Fase 2 (Match NF x PO)
        self.fase2_status = None
        self.fase2_validacao_id = None
        self.fase2_numero_nf = None
        self.fase2_percentual_match = None
        self.fase2_po_vinculado = None
        self.fase2_aprovado = False

        # Fase 3 (Consolidacao)
        self.fase3_status = None  # 'consolidado', 'finalizado_odoo', 'aguardando_consolidacao', 'pendente'
        self.fase3_po_consolidado = None
        self.fase3_aprovado = False

        # Diagnostico
        self.diagnostico = []

    def to_dict(self):
        """Serializa para enviar ao frontend."""
        return {
            'pode_receber': self.pode_receber,
            'tipo_liberacao': self.tipo_liberacao,
            'bloqueio_motivo': self.bloqueio_motivo,
            'contato_resolucao': self.contato_resolucao,
            'fases': {
                'fase1': {
                    'nome': 'Validacao Fiscal',
                    'status': self.fase1_status,
                    'aprovado': self.fase1_aprovado,
                    'numero_nf': self.fase1_numero_nf,
                    'icone': 'check-circle' if self.fase1_aprovado else ('times-circle' if self.fase1_status else 'question-circle'),
                    'cor': 'success' if self.fase1_aprovado else ('danger' if self.fase1_status else 'secondary'),
                },
                'fase2': {
                    'nome': 'Match NF x PO',
                    'status': self.fase2_status,
                    'aprovado': self.fase2_aprovado,
                    'percentual_match': self.fase2_percentual_match,
                    'po_vinculado': self.fase2_po_vinculado,
                    'icone': 'check-circle' if self.fase2_aprovado else ('times-circle' if self.fase2_status else 'question-circle'),
                    'cor': 'success' if self.fase2_aprovado else ('danger' if self.fase2_status else 'secondary'),
                },
                'fase3': {
                    'nome': 'Consolidacao PO',
                    'status': self.fase3_status,
                    'aprovado': self.fase3_aprovado,
                    'po_consolidado': self.fase3_po_consolidado,
                    'icone': 'check-circle' if self.fase3_aprovado else ('clock' if self.fase3_status == 'aguardando_consolidacao' else 'times-circle'),
                    'cor': 'success' if self.fase3_aprovado else ('warning' if self.fase3_status == 'aguardando_consolidacao' else 'danger'),
                },
            },
            'diagnostico': self.diagnostico,
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

    # Contatos por tipo de bloqueio
    CONTATOS = {
        'fase1_pendente': 'Sistema (validacao fiscal nao executada - aguardar scheduler)',
        'fase1_nao_executada': 'Sistema (validacao fiscal nao executada - aguardar scheduler)',
        'fase1_validando': 'Sistema (validacao fiscal em processamento - aguardar)',
        'fase1_bloqueado': 'Fiscal (divergencia fiscal pendente)',
        'fase1_primeira_compra': 'Fiscal (cadastro de primeira compra)',
        'fase1_erro': 'TI (erro na validacao fiscal)',
        'fase2_pendente': 'Sistema (validacao NF x PO nao executada - aguardar)',
        'fase2_validando': 'Sistema (validacao NF x PO em processamento - aguardar)',
        'fase2_bloqueado': 'Compras (divergencia NF x PO - match incompleto)',
        'fase2_erro': 'TI (erro na validacao NF x PO)',
        'fase3_pendente': 'Compras (consolidacao de PO pendente)',
        'fase3_aguardando_consolidacao': 'Compras (match 100% identificado - executar consolidacao na Central Fiscal)',
    }

    def validar_fases_picking(self, purchase_order_id, origin=None):
        """
        Valida todas as fases para um picking.

        Args:
            purchase_order_id: ID do PO no Odoo (de PickingRecebimento.odoo_purchase_order_id)
            origin: Campo origin do picking (pode conter numero da NF)

        Returns:
            PhaseStatus com veredicto e diagnostico
        """
        status = PhaseStatus()

        if not purchase_order_id:
            # Picking sem PO - caso raro, liberar como legacy
            status.pode_receber = True
            status.tipo_liberacao = 'legacy'
            status.diagnostico.append('Picking sem PO vinculado - liberado como legado.')
            return status

        try:
            # 1. Buscar ValidacaoNfPoDfe pelo PO do picking
            validacao = self._buscar_validacao_nf_po(purchase_order_id)

            if not validacao:
                # Sem DFE no sistema - pode ser picking antigo
                status.pode_receber = True
                status.tipo_liberacao = 'legacy'
                status.diagnostico.append(
                    'NF nao registrada no sistema de validacao. '
                    'Picking liberado como legado (anterior ao sistema).'
                )
                return status

            # 2. Preencher info Fase 2
            status.fase2_status = validacao.status
            status.fase2_validacao_id = validacao.id
            status.fase2_numero_nf = validacao.numero_nf
            status.fase2_percentual_match = validacao.percentual_match
            status.fase2_po_vinculado = validacao.odoo_po_vinculado_name
            status.fase2_aprovado = validacao.status in self.STATUSES_FASE2_OK

            # 3. Buscar ValidacaoFiscalDfe pela DFE
            fiscal = None
            if validacao.odoo_dfe_id:
                fiscal = ValidacaoFiscalDfe.query.filter_by(
                    odoo_dfe_id=validacao.odoo_dfe_id
                ).first()

            if fiscal:
                status.fase1_status = fiscal.status
                status.fase1_numero_nf = fiscal.numero_nf
                status.fase1_aprovado = (fiscal.status == 'aprovado')
            else:
                # DFE existe na Fase 2 mas Fase 1 nao rodou
                status.fase1_status = 'nao_executada'
                status.fase1_aprovado = False

            # 4. Avaliar Fase 3 (Consolidacao)
            # IMPORTANTE: 'aprovado' NAO e pass-through!
            # 'aprovado' = "pronto para consolidar" = Fase 3 PENDENTE
            # So 'consolidado' ou 'finalizado_odoo' significam Fase 3 completa
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
                # bloqueado, pendente, validando, erro
                status.fase3_status = 'pendente'
                status.fase3_aprovado = False

            # 5. Veredicto final (ordem de prioridade: Fase 1 → Fase 2 → Fase 3)
            self._definir_veredicto(status, fiscal)

            # 6. Construir diagnostico
            status.diagnostico = self._construir_diagnostico(status)

            return status

        except Exception as e:
            logger.error(f"Erro na validacao cross-phase para PO {purchase_order_id}: {e}")
            # Em caso de erro interno, liberar como legacy para nao bloquear operacao
            status.pode_receber = True
            status.tipo_liberacao = 'legacy'
            status.diagnostico.append(f'Erro na validacao de fases: {str(e)}. Liberado como legado.')
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
            # Todos sem PO - todos legacy
            return {p.odoo_picking_id: self._make_legacy_status('Picking sem PO') for p in pickings}

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

            # Montar resultado por picking
            results = {}
            for p in pickings:
                po_id = p.odoo_purchase_order_id
                if not po_id:
                    results[p.odoo_picking_id] = self._make_legacy_status('Picking sem PO')
                    continue

                validacao = po_to_validacao.get(po_id)
                if not validacao:
                    results[p.odoo_picking_id] = self._make_legacy_status(
                        'NF nao registrada no sistema de validacao'
                    )
                    continue

                fiscal = fiscais_by_dfe.get(validacao.odoo_dfe_id) if validacao.odoo_dfe_id else None
                results[p.odoo_picking_id] = self._build_phase_status(validacao, fiscal)

            return results

        except Exception as e:
            logger.error(f"Erro no batch de validacao cross-phase: {e}")
            # Em caso de erro, liberar todos como legacy
            return {p.odoo_picking_id: self._make_legacy_status(f'Erro: {e}') for p in pickings}

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

    def _definir_veredicto(self, status, fiscal):
        """Define pode_receber, bloqueio_motivo e contato_resolucao."""
        if not status.fase1_aprovado and fiscal:
            status.pode_receber = False
            status.bloqueio_motivo = f'Fase 1 (Fiscal) bloqueada: {status.fase1_status}'
            status.contato_resolucao = self.CONTATOS.get(
                f'fase1_{status.fase1_status}', 'Fiscal'
            )
        elif not status.fase1_aprovado and not fiscal:
            status.pode_receber = False
            status.bloqueio_motivo = 'Fase 1 (Fiscal) nao executada para esta NF'
            status.contato_resolucao = self.CONTATOS['fase1_nao_executada']
        elif not status.fase2_aprovado:
            status.pode_receber = False
            status.bloqueio_motivo = f'Fase 2 (Match NF x PO) bloqueada: {status.fase2_status}'
            status.contato_resolucao = self.CONTATOS.get(
                f'fase2_{status.fase2_status}', 'Compras'
            )
        elif not status.fase3_aprovado:
            if status.fase3_status == 'aguardando_consolidacao':
                status.pode_receber = False
                status.bloqueio_motivo = (
                    'Fase 3 (Consolidacao PO) nao executada. '
                    'Match 100% identificado, mas consolidacao precisa ser executada.'
                )
                status.contato_resolucao = self.CONTATOS['fase3_aguardando_consolidacao']
            else:
                status.pode_receber = False
                status.bloqueio_motivo = 'Fase 3 (Consolidacao PO) pendente'
                status.contato_resolucao = self.CONTATOS['fase3_pendente']
        else:
            status.pode_receber = True
            if status.fase3_status == 'finalizado_odoo':
                status.tipo_liberacao = 'finalizado_odoo'
            else:
                status.tipo_liberacao = 'full'

    def _construir_diagnostico(self, status):
        """Constroi lista de mensagens de diagnostico para o operador."""
        msgs = []

        # Fase 1
        if status.fase1_aprovado:
            nf_info = f' (NF {status.fase1_numero_nf})' if status.fase1_numero_nf else ''
            msgs.append(f'✅ Fase 1 - Validacao Fiscal: Aprovada{nf_info}')
        elif status.fase1_status == 'nao_executada':
            msgs.append('❌ Fase 1 - Validacao Fiscal: Nao executada (aguardar processamento automatico)')
        elif status.fase1_status:
            msgs.append(f'❌ Fase 1 - Validacao Fiscal: {status.fase1_status.replace("_", " ").title()}')

        # Fase 2
        if status.fase2_aprovado:
            match_info = f' ({status.fase2_percentual_match}% match)' if status.fase2_percentual_match else ''
            po_info = f' - PO: {status.fase2_po_vinculado}' if status.fase2_po_vinculado else ''
            msgs.append(f'✅ Fase 2 - Match NF x PO: {status.fase2_status.title()}{match_info}{po_info}')
        elif status.fase2_status:
            match_info = f' ({status.fase2_percentual_match}% match)' if status.fase2_percentual_match else ''
            msgs.append(f'❌ Fase 2 - Match NF x PO: {status.fase2_status.replace("_", " ").title()}{match_info}')

        # Fase 3
        if status.fase3_aprovado:
            po_info = f' - PO: {status.fase3_po_consolidado}' if status.fase3_po_consolidado else ''
            if status.fase3_status == 'finalizado_odoo':
                msgs.append(f'✅ Fase 3 - Consolidacao: PO vinculado pelo Odoo{po_info}')
            else:
                msgs.append(f'✅ Fase 3 - Consolidacao: Executada{po_info}')
        elif status.fase3_status == 'aguardando_consolidacao':
            msgs.append('⏳ Fase 3 - Consolidacao: Match 100% OK, aguardando execucao da consolidacao')
        elif status.fase3_status:
            msgs.append(f'❌ Fase 3 - Consolidacao: {status.fase3_status.replace("_", " ").title()}')

        return msgs

    def _build_phase_status(self, validacao, fiscal):
        """Constroi PhaseStatus a partir de validacao e fiscal encontrados."""
        status = PhaseStatus()

        # Fase 2
        status.fase2_status = validacao.status
        status.fase2_validacao_id = validacao.id
        status.fase2_numero_nf = validacao.numero_nf
        status.fase2_percentual_match = validacao.percentual_match
        status.fase2_po_vinculado = validacao.odoo_po_vinculado_name
        status.fase2_aprovado = validacao.status in self.STATUSES_FASE2_OK

        # Fase 1
        if fiscal:
            status.fase1_status = fiscal.status
            status.fase1_numero_nf = fiscal.numero_nf
            status.fase1_aprovado = (fiscal.status == 'aprovado')
        else:
            status.fase1_status = 'nao_executada'
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
        self._definir_veredicto(status, fiscal)

        # Diagnostico
        status.diagnostico = self._construir_diagnostico(status)

        return status

    def _make_legacy_status(self, motivo='Picking anterior ao sistema'):
        """Cria PhaseStatus para pickings legados (sem DFE no sistema)."""
        status = PhaseStatus()
        status.pode_receber = True
        status.tipo_liberacao = 'legacy'
        status.diagnostico.append(f'{motivo}. Liberado como legado.')
        return status

    def _prioridade(self, status_str):
        """Retorna prioridade numerica de um status (menor = melhor)."""
        return self.PRIORIDADE_STATUS.get(status_str, 99)
