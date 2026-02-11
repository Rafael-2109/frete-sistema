"""
Service para processamento de Recebimento LF no Odoo (Worker RQ)
================================================================

Arquitetura: Checkpoint por Etapa + Fire and Poll
--------------------------------------------------
Cada etapa segue o ciclo:
  1. Guard: se etapa_atual >= N, pular
  2. Idempotencia: ler Odoo para ver se etapa ja foi executada
  3. Executar: gravar no Odoo (ou fire_and_poll para ops pesadas)
  4. Checkpoint: salvar etapa_atual=N + IDs no banco local

Operacoes pesadas (etapas 4, 7, 8, 12, 13, 16) usam padrao "fire and poll":
  1. Dispara acao no Odoo com timeout curto (60s)
  2. Se timeout, OK — acao continua no Odoo
  3. Polla a cada 10s ate resultado aparecer (max 30min)

Resiliencia:
  - Cada step re-busca recebimento fresco do DB (previne DetachedInstanceError)
  - Checkpoint apos cada etapa com commit_with_retry
  - Recovery: ao retomar, inspeciona Odoo para recuperar IDs nao salvos
  - Idempotencia: verifica estado no Odoo antes de executar operacoes destrutivas

Responsabilidades (18 etapas):
FASE 1 - Preparacao DFe:
    1. Buscar DFe no Odoo
    2. Avancar status do DFe (se necessario)
    3. Atualizar data_entrada e tipo_pedido

FASE 2 - Gerar e Configurar PO:
    4. action_gerar_po_dfe [fire_and_poll]
    5. Extrair PO do resultado
    6. Configurar PO (team, payment_term, picking_type)
    7. Confirmar PO (button_confirm) [fire_and_poll]
    8. Aprovar PO (button_approve, se necessario) [fire_and_poll]

FASE 3 - Picking / Recebimento:
    9. Buscar picking gerado
    10. Preencher lotes (CFOP!=1902: manual, CFOP=1902: auto)
    11. Aprovar quality checks
    12. Validar picking (button_validate) [fire_and_poll]

FASE 4 - Fatura:
    13. Criar invoice (action_create_invoice) [fire_and_poll]
    14. Extrair invoice_id
    15. Configurar invoice (situacao_nf, impostos)
    16. Confirmar invoice (action_post) [fire_and_poll]

FASE 5 - Finalizacao:
    17. Atualizar status local
    18. Criar MovimentacaoEstoque

IMPORTANTE: Este service e chamado pelo job RQ, NAO diretamente pela rota.
"""

import json
import logging
import os
import time
from datetime import date
from decimal import Decimal

from redis import Redis

from app import db
from app.recebimento.models import RecebimentoLf
from app.odoo.utils.connection import get_odoo_connection
from app.utils.database_retry import commit_with_retry
from app.utils.timezone import agora_utc_naive

logger = logging.getLogger(__name__)


class RecebimentoLfOdooService:
    """Processa Recebimento LF completo no Odoo (18 etapas com checkpoint)."""

    # IDs fixos (conforme IDS_FIXOS.md)
    COMPANY_FB = 1
    COMPANY_LF = 5
    PICKING_TYPE_FB = 1
    TEAM_ID = 119
    PAYMENT_PROVIDER_ID = 92  # Transferencia Bancaria FB (company_id=1)
    PAYMENT_TERM_A_VISTA = 2791

    # Fire and Poll — parametros
    FIRE_TIMEOUT = 60       # Timeout curto para disparar acao (60s)
    POLL_INTERVAL = 10      # Intervalo entre polls (10s)
    MAX_POLL_TIME = 1800    # Tempo maximo de polling (30 min)

    # =================================================================
    # Metodo principal
    # =================================================================

    def processar_recebimento(self, recebimento_id, usuario_nome=None):  # noqa: ARG002
        """
        Processa um Recebimento LF completo no Odoo (18 etapas com checkpoint).

        Suporta retomada: se etapa_atual > 0, pula etapas ja concluidas.
        Cada etapa re-busca o registro do banco (previne DetachedInstanceError).

        Args:
            recebimento_id: ID do RecebimentoLf local
            usuario_nome: Nome do usuario (para log)

        Returns:
            Dict com resultado do processamento

        Raises:
            Exception se erro irrecuperavel
        """
        self._recebimento_id = recebimento_id

        self._safe_update(status='processando', tentativas_increment=True)

        try:
            odoo = get_odoo_connection()

            # Recovery: se etapa_atual > 0, tentar recuperar IDs do Odoo
            rec = self._get_recebimento()
            if rec.etapa_atual > 0:
                logger.info(
                    f"[RecLF {recebimento_id}] RETOMADA: etapa_atual={rec.etapa_atual}, "
                    f"recuperando estado do Odoo..."
                )
                self._recover_state_from_odoo(odoo)

            # Dispatch sequencial — cada step re-busca recebimento internamente
            self._step_01_buscar_dfe(odoo)
            self._step_02_avancar_status_dfe(odoo)
            self._step_03_configurar_dfe(odoo)
            self._step_04_gerar_po(odoo)
            self._step_05_extrair_po(odoo)
            self._step_06_configurar_po(odoo)
            self._step_07_confirmar_po(odoo)
            self._step_08_aprovar_po(odoo)
            self._step_09_buscar_picking(odoo)
            self._step_10_preencher_lotes(odoo)
            self._step_11_aprovar_quality_checks(odoo)
            self._step_12_validar_picking(odoo)
            self._step_13_criar_invoice(odoo)
            self._step_14_extrair_invoice(odoo)
            self._step_15_configurar_invoice(odoo)
            self._step_16_confirmar_invoice(odoo)
            self._step_17_atualizar_status(odoo)
            self._step_18_criar_movimentacoes(odoo)

            # Sucesso!
            self._safe_update(
                status='processado',
                processado_em=agora_utc_naive(),
                erro_mensagem=None,
                fase_atual=5,
            )

            rec = self._get_recebimento()
            logger.info(
                f"[RecLF {recebimento_id}] SUCESSO! "
                f"DFe={rec.odoo_dfe_id} PO={rec.odoo_po_name} "
                f"Picking={rec.odoo_picking_name} "
                f"Invoice={rec.odoo_invoice_name}"
            )

            return {
                'status': 'processado',
                'recebimento_id': recebimento_id,
                'odoo_po_id': rec.odoo_po_id,
                'odoo_po_name': rec.odoo_po_name,
                'odoo_picking_id': rec.odoo_picking_id,
                'odoo_picking_name': rec.odoo_picking_name,
                'odoo_invoice_id': rec.odoo_invoice_id,
                'odoo_invoice_name': rec.odoo_invoice_name,
            }

        except Exception as e:
            logger.error(
                f"[RecLF {recebimento_id}] ERRO na etapa "
                f"{self._get_recebimento_safe_attr('etapa_atual', '?')}: {e}"
            )
            try:
                self._safe_update(status='erro', erro_mensagem=str(e)[:500])
            except Exception:
                logger.error(f"[RecLF {recebimento_id}] Falha ao salvar status de erro")
            raise

    # =================================================================
    # Helpers de estado
    # =================================================================

    def _get_recebimento(self):
        """Re-busca recebimento fresco do banco. Previne DetachedInstanceError."""
        try:
            rec = db.session.get(RecebimentoLf, self._recebimento_id)
        except Exception:
            # Sessao pode estar em estado invalido apos SSL error
            try:
                db.session.rollback()
            except Exception:
                pass
            rec = db.session.get(RecebimentoLf, self._recebimento_id)
        if not rec:
            raise ValueError(f"Recebimento {self._recebimento_id} nao encontrado")
        return rec

    def _safe_update(self, tentativas_increment=False, **fields):
        """
        Atualiza campos do recebimento com resiliencia a SSL errors.

        Re-busca registro, aplica campos, e commita com retry completo
        (re-fetch + re-set + re-commit) em caso de erro de sessao.

        Args:
            tentativas_increment: Se True, incrementa tentativas
            **fields: Campos para setar (ex: status='processando')
        """
        max_retries = 3
        for attempt in range(max_retries):
            try:
                rec = self._get_recebimento()
                for field, value in fields.items():
                    if hasattr(rec, field):
                        setattr(rec, field, value)
                if tentativas_increment:
                    rec.tentativas = (rec.tentativas or 0) + 1
                db.session.commit()
                return
            except Exception as e:
                error_str = str(e).lower()
                is_recoverable = any(err in error_str for err in [
                    'ssl', 'decryption', 'bad record', 'not bound to a session',
                    'detachedinstanceerror',
                ])
                if is_recoverable and attempt < max_retries - 1:
                    logger.warning(
                        f"  [safe_update] Erro recuperavel tentativa "
                        f"{attempt + 1}/{max_retries}: {type(e).__name__}"
                    )
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
                    try:
                        db.session.close()
                    except Exception:
                        pass
                    time.sleep(0.5 * (attempt + 1))
                else:
                    raise

    def _get_recebimento_safe_attr(self, attr, default=None):
        """Busca atributo do recebimento sem levantar excecao."""
        try:
            rec = self._get_recebimento()
            return getattr(rec, attr, default)
        except Exception:
            return default

    def _checkpoint(self, etapa, fase=None, msg='', **extra_fields):
        """
        Salva checkpoint: etapa_atual + campos extras + commit.

        Resiliente a SSL errors: se commit falhar por SSL, a sessao e
        reconstruida e o checkpoint e reaplicado do zero (re-fetch + re-set + re-commit).

        Args:
            etapa: Numero da etapa concluida (1-18)
            fase: Numero da fase (opcional, calculado automaticamente)
            msg: Mensagem de progresso para Redis
            **extra_fields: Campos extras para salvar (ex: odoo_po_id=123)

        Returns:
            RecebimentoLf fresco apos commit
        """
        # Calcular fase
        if fase is not None:
            computed_fase = fase
        elif etapa <= 3:
            computed_fase = 1
        elif etapa <= 8:
            computed_fase = 2
        elif etapa <= 12:
            computed_fase = 3
        elif etapa <= 16:
            computed_fase = 4
        else:
            computed_fase = 5

        max_retries = 3
        for attempt in range(max_retries):
            try:
                rec = self._get_recebimento()
                rec.etapa_atual = etapa
                rec.fase_atual = computed_fase
                rec.ultimo_checkpoint_em = agora_utc_naive()

                for field, value in extra_fields.items():
                    if hasattr(rec, field):
                        setattr(rec, field, value)

                db.session.commit()
                break  # Sucesso

            except Exception as e:
                error_str = str(e).lower()
                is_ssl = any(err in error_str for err in [
                    'ssl', 'decryption', 'bad record', 'not bound to a session',
                    'detachedinstanceerror',
                ])

                if is_ssl and attempt < max_retries - 1:
                    logger.warning(
                        f"  [Checkpoint] SSL/sessao error tentativa {attempt + 1}/{max_retries}, "
                        f"reconstruindo sessao..."
                    )
                    try:
                        db.session.rollback()
                    except Exception:
                        pass
                    try:
                        db.session.close()
                    except Exception:
                        pass
                    time.sleep(0.5 * (attempt + 1))
                    # Loop continua: re-fetch + re-set + re-commit
                else:
                    raise

        # Atualizar Redis para polling da tela de status
        self._atualizar_redis(
            self._recebimento_id, computed_fase, etapa,
            18, msg  # total_etapas hardcoded para evitar acesso a rec
        )

        logger.debug(
            f"  [Checkpoint] etapa={etapa} fase={computed_fase} "
            f"{', '.join(f'{k}={v}' for k, v in extra_fields.items())}"
        )

        # Re-buscar fresco apos commit
        return self._get_recebimento()

    def _write_and_verify(self, odoo, model, record_id, values, step_name, critical_fields=None):
        """
        Executa write no Odoo e verifica lendo de volta.

        Args:
            odoo: Conexao Odoo
            model: Nome do modelo Odoo
            record_id: ID do registro (int ou [int])
            values: Dict com valores a escrever
            step_name: Nome do passo (para log)
            critical_fields: Lista de campos que DEVEM bater (raise se divergir)

        Raises:
            ValueError: Se campo critico divergiu
        """
        # Normalizar record_id para lista
        ids = record_id if isinstance(record_id, list) else [record_id]
        single_id = ids[0]

        # Write
        odoo.write(model, ids, values)

        # Read-back
        fields_to_check = list(values.keys())
        read_data = odoo.execute_kw(
            model, 'read',
            [ids],
            {'fields': fields_to_check}
        )

        if not read_data:
            logger.warning(f"  [{step_name}] Read-back vazio para {model} {single_id}")
            return

        actual = read_data[0]
        critical_fields = critical_fields or []

        for field in fields_to_check:
            expected = values[field]
            got = actual.get(field)

            # Normalizar Odoo False -> None para campos vazios (many2one)
            if got is False:
                got = None
            if expected is False:
                expected = None

            # Normalizar many2one [id, 'name'] -> id
            if isinstance(got, (list, tuple)) and len(got) >= 1:
                got = got[0]

            if got != expected:
                if field in critical_fields:
                    raise ValueError(
                        f"[{step_name}] Campo critico {model}.{field} diverge: "
                        f"esperado={expected}, obtido={got}"
                    )
                else:
                    logger.warning(
                        f"  [{step_name}] {model}.{field}: esperado={expected}, obtido={got}"
                    )

    def _recover_state_from_odoo(self, odoo):
        """
        Recupera estado do Odoo ao retomar processamento interrompido.

        Executado APENAS quando etapa_atual > 0 (resume).
        Busca IDs que podem ter sido criados no Odoo mas nao salvos localmente.
        Ajusta etapa_atual baseado no estado real do Odoo.
        """
        rec = self._get_recebimento()
        dfe_id = rec.odoo_dfe_id
        mudou = False

        # Recuperar PO se nao temos localmente
        if not rec.odoo_po_id and dfe_id:
            dfe_data = odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe', 'read',
                [[dfe_id]],
                {'fields': ['purchase_id']}
            )
            if dfe_data and dfe_data[0].get('purchase_id'):
                purchase_ref = dfe_data[0]['purchase_id']
                po_id = purchase_ref[0] if isinstance(purchase_ref, (list, tuple)) else purchase_ref
                rec.odoo_po_id = po_id
                # Buscar nome
                po_data = odoo.execute_kw(
                    'purchase.order', 'read', [[po_id]], {'fields': ['name']}
                )
                if po_data:
                    rec.odoo_po_name = po_data[0].get('name')
                logger.info(f"  [Recovery] PO encontrado no Odoo: {rec.odoo_po_name} (ID={po_id})")
                mudou = True

        # Recuperar Picking se temos PO mas nao picking
        if rec.odoo_po_id and not rec.odoo_picking_id:
            pickings = odoo.execute_kw(
                'stock.picking', 'search_read',
                [[
                    ['purchase_id', '=', rec.odoo_po_id],
                    ['picking_type_code', '=', 'incoming'],
                ]],
                {'fields': ['id', 'name', 'state'], 'limit': 1, 'order': 'id desc'}
            )
            if pickings:
                rec.odoo_picking_id = pickings[0]['id']
                rec.odoo_picking_name = pickings[0]['name']
                logger.info(
                    f"  [Recovery] Picking encontrado no Odoo: {rec.odoo_picking_name} "
                    f"(ID={rec.odoo_picking_id}, state={pickings[0]['state']})"
                )
                mudou = True

        # Recuperar Invoice se temos PO mas nao invoice
        if rec.odoo_po_id and not rec.odoo_invoice_id:
            po_data = odoo.execute_kw(
                'purchase.order', 'read',
                [[rec.odoo_po_id]],
                {'fields': ['invoice_ids']}
            )
            invoice_ids = po_data[0].get('invoice_ids', []) if po_data else []
            if invoice_ids:
                inv_id = invoice_ids[-1]
                rec.odoo_invoice_id = inv_id
                inv_data = odoo.execute_kw(
                    'account.move', 'read', [[inv_id]], {'fields': ['name']}
                )
                if inv_data:
                    rec.odoo_invoice_name = inv_data[0].get('name')
                logger.info(
                    f"  [Recovery] Invoice encontrada no Odoo: {rec.odoo_invoice_name} "
                    f"(ID={inv_id})"
                )
                mudou = True

        # Ajustar etapa_atual baseado no estado real no Odoo
        if rec.odoo_po_id:
            po_data = odoo.execute_kw(
                'purchase.order', 'read',
                [[rec.odoo_po_id]],
                {'fields': ['state']}
            )
            if po_data:
                po_state = po_data[0].get('state')
                if po_state in ('purchase', 'done') and rec.etapa_atual < 8:
                    logger.info(f"  [Recovery] PO state={po_state}, ajustando etapa para 8")
                    rec.etapa_atual = 8
                    mudou = True
                elif po_state == 'to approve' and rec.etapa_atual < 7:
                    logger.info(f"  [Recovery] PO state=to approve, ajustando etapa para 7")
                    rec.etapa_atual = 7
                    mudou = True
                elif po_state in ('draft', 'sent') and rec.etapa_atual < 4:
                    logger.info(f"  [Recovery] PO state={po_state} (PO existe), ajustando etapa para 4")
                    rec.etapa_atual = 4
                    mudou = True

        if rec.odoo_picking_id:
            picking_data = odoo.execute_kw(
                'stock.picking', 'read',
                [[rec.odoo_picking_id]],
                {'fields': ['state']}
            )
            if picking_data:
                picking_state = picking_data[0].get('state')
                if picking_state == 'done' and rec.etapa_atual < 12:
                    logger.info(f"  [Recovery] Picking state=done, ajustando etapa para 12")
                    rec.etapa_atual = 12
                    mudou = True
                elif picking_state in ('assigned', 'confirmed', 'waiting') and rec.etapa_atual < 9:
                    logger.info(f"  [Recovery] Picking state={picking_state}, ajustando etapa para 9")
                    rec.etapa_atual = 9
                    mudou = True

        if rec.odoo_invoice_id:
            inv_data = odoo.execute_kw(
                'account.move', 'read',
                [[rec.odoo_invoice_id]],
                {'fields': ['state']}
            )
            if inv_data:
                inv_state = inv_data[0].get('state')
                if inv_state == 'posted' and rec.etapa_atual < 16:
                    logger.info(f"  [Recovery] Invoice state=posted, ajustando etapa para 16")
                    rec.etapa_atual = 16
                    mudou = True
                elif inv_state == 'draft' and rec.etapa_atual < 13:
                    logger.info(f"  [Recovery] Invoice state=draft, ajustando etapa para 13")
                    rec.etapa_atual = 13
                    mudou = True

        if mudou:
            commit_with_retry(db.session)
            logger.info(
                f"  [Recovery] Estado recuperado: etapa_atual={rec.etapa_atual}, "
                f"PO={rec.odoo_po_id}, Picking={rec.odoo_picking_id}, "
                f"Invoice={rec.odoo_invoice_id}"
            )

    # =================================================================
    # FASE 1: Preparacao DFe (etapas 1-3)
    # =================================================================

    def _step_01_buscar_dfe(self, odoo):
        """Etapa 1: Buscar DFe no Odoo e validar existencia."""
        rec = self._get_recebimento()
        if rec.etapa_atual >= 1:
            return

        dfe_id = rec.odoo_dfe_id
        logger.info(f"  Etapa 1/18: Buscando DFe {dfe_id}")
        self._atualizar_redis(rec.id, 1, 1, rec.total_etapas, 'Buscando DFe...')

        dfe = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe', 'search_read',
            [[['id', '=', dfe_id]]],
            {
                'fields': ['id', 'l10n_br_status', 'l10n_br_situacao_dfe',
                           'nfe_infnfe_ide_nnf', 'protnfe_infnfe_chnfe',
                           'purchase_id'],
                'limit': 1,
            }
        )

        if not dfe:
            raise ValueError(f"DFe {dfe_id} nao encontrado no Odoo")

        self._checkpoint(etapa=1, msg='DFe encontrado')

    def _step_02_avancar_status_dfe(self, odoo):
        """Etapa 2: Avancar status do DFe se necessario (01 -> 03)."""
        rec = self._get_recebimento()
        if rec.etapa_atual >= 2:
            return

        dfe_id = rec.odoo_dfe_id
        logger.info(f"  Etapa 2/18: Avancando status DFe {dfe_id}")
        self._atualizar_redis(rec.id, 1, 2, rec.total_etapas, 'Avancando status DFe...')

        # Ler status atual (idempotencia)
        dfe_data = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe', 'read',
            [[dfe_id]],
            {'fields': ['l10n_br_status']}
        )
        status_atual = dfe_data[0].get('l10n_br_status', '01') if dfe_data else '01'

        if status_atual in ('01', '02'):
            # Tentar dar ciencia
            try:
                odoo.execute_kw(
                    'l10n_br_ciel_it_account.dfe',
                    'action_ciencia_dfe',
                    [[dfe_id]]
                )
                logger.info(f"  DFe {dfe_id}: ciencia executada")
            except Exception as e:
                if 'cannot marshal None' not in str(e):
                    logger.warning(f"  DFe {dfe_id}: action_ciencia_dfe falhou: {e}")
                    # Tentar write direto do status
                    try:
                        odoo.write('l10n_br_ciel_it_account.dfe', [dfe_id], {
                            'l10n_br_status': '03',
                        })
                    except Exception as e2:
                        logger.warning(f"  DFe {dfe_id}: write status 03 falhou: {e2}")

        # Re-buscar status final
        dfe_atualizado = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe', 'read',
            [[dfe_id]],
            {'fields': ['l10n_br_status']}
        )
        status_final = dfe_atualizado[0]['l10n_br_status'] if dfe_atualizado else status_atual
        logger.info(f"  DFe {dfe_id}: status final = '{status_final}'")

        self._checkpoint(etapa=2, msg=f'Status DFe: {status_final}')

    def _step_03_configurar_dfe(self, odoo):
        """Etapa 3: Atualizar data_entrada e tipo_pedido no DFe."""
        rec = self._get_recebimento()
        if rec.etapa_atual >= 3:
            return

        dfe_id = rec.odoo_dfe_id
        logger.info(f"  Etapa 3/18: Configurando DFe (data_entrada + tipo_pedido)")
        self._atualizar_redis(rec.id, 1, 3, rec.total_etapas, 'Configurando DFe...')

        # Idempotencia: verificar se ja configurado
        dfe_data = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe', 'read',
            [[dfe_id]],
            {'fields': ['l10n_br_data_entrada', 'l10n_br_tipo_pedido']}
        )
        if dfe_data:
            data_entrada = dfe_data[0].get('l10n_br_data_entrada')
            tipo_pedido = dfe_data[0].get('l10n_br_tipo_pedido')
            if data_entrada and tipo_pedido == 'serv-industrializacao':
                logger.info(f"  DFe {dfe_id}: ja configurado (data={data_entrada}, tipo={tipo_pedido})")
                self._checkpoint(etapa=3, msg='DFe ja configurado')
                return

        hoje = date.today().strftime('%Y-%m-%d')
        values = {
            'l10n_br_data_entrada': hoje,
            'l10n_br_tipo_pedido': 'serv-industrializacao',
        }

        self._write_and_verify(
            odoo, 'l10n_br_ciel_it_account.dfe', [dfe_id], values,
            'Configurar DFe', critical_fields=['l10n_br_tipo_pedido']
        )

        logger.info(f"  DFe {dfe_id} configurado: data_entrada={hoje}, tipo=serv-industrializacao")
        self._checkpoint(etapa=3, msg='DFe configurado')

    # =================================================================
    # FASE 2: Gerar e Configurar PO (etapas 4-8)
    # =================================================================

    def _step_04_gerar_po(self, odoo):
        """Etapa 4: Gerar PO a partir do DFe via fire_and_poll."""
        rec = self._get_recebimento()
        if rec.etapa_atual >= 4:
            return

        dfe_id = rec.odoo_dfe_id
        logger.info(f"  Etapa 4/18: Gerando PO (fire_and_poll, fire_timeout={self.FIRE_TIMEOUT}s)")
        self._atualizar_redis(rec.id, 2, 4, rec.total_etapas, 'Gerando PO no Odoo (pode demorar)...')

        # Idempotencia: verificar se DFe ja tem purchase_id
        dfe_data = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe', 'read',
            [[dfe_id]],
            {'fields': ['purchase_id']}
        )
        if dfe_data and dfe_data[0].get('purchase_id'):
            po_ref = dfe_data[0]['purchase_id']
            po_id = po_ref[0] if isinstance(po_ref, (list, tuple)) else po_ref
            logger.info(f"  DFe {dfe_id} ja tem PO (ID={po_id}), pulando geracao")
            self._checkpoint(etapa=4, odoo_po_id=po_id, msg='PO ja existia')
            return

        def fire_gerar_po():
            return odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe',
                'action_gerar_po_dfe',
                [[dfe_id]],
                {'context': {'validate_analytic': True}},
                timeout_override=self.FIRE_TIMEOUT
            )

        def poll_gerar_po():
            dfe_check = odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe', 'read',
                [[dfe_id]],
                {'fields': ['purchase_id']}
            )
            if dfe_check and dfe_check[0].get('purchase_id'):
                return dfe_check[0]['purchase_id']  # [id, 'name']
            # Buscar tambem por dfe_id no purchase.order (excluir canceladas)
            po_search = odoo.execute_kw(
                'purchase.order', 'search_read',
                [[
                    ['dfe_id', '=', dfe_id],
                    ['state', '!=', 'cancel'],
                ]],
                {'fields': ['id', 'name', 'state'], 'limit': 1,
                 'order': 'id desc'}
            )
            if po_search:
                return po_search[0]
            return None

        po_ref = self._fire_and_poll(odoo, fire_gerar_po, poll_gerar_po, 'Gerar PO')

        # Extrair po_id do resultado
        po_id = None
        if isinstance(po_ref, (list, tuple)):
            po_id = po_ref[0]
        elif isinstance(po_ref, dict):
            po_id = po_ref.get('res_id') or po_ref.get('id')
        elif isinstance(po_ref, int):
            po_id = po_ref

        if not po_id:
            raise ValueError("Purchase Order nao foi criado apos action_gerar_po_dfe")

        self._checkpoint(etapa=4, odoo_po_id=po_id, msg='PO gerado')

    def _step_05_extrair_po(self, odoo):
        """Etapa 5: Extrair e confirmar dados do PO criado."""
        rec = self._get_recebimento()
        if rec.etapa_atual >= 5:
            return

        po_id = rec.odoo_po_id
        if not po_id:
            raise ValueError("odoo_po_id nao encontrado — etapa 4 nao executou corretamente")

        logger.info(f"  Etapa 5/18: Extraindo dados PO {po_id}")
        self._atualizar_redis(rec.id, 2, 5, rec.total_etapas, 'Localizando PO...')

        po_data = odoo.execute_kw(
            'purchase.order', 'read',
            [[po_id]],
            {'fields': ['name', 'state']}
        )
        if not po_data:
            raise ValueError(f"PO {po_id} nao encontrado no Odoo")

        po_name = po_data[0]['name']
        logger.info(f"  PO encontrado: {po_name} (ID={po_id}, state={po_data[0]['state']})")

        self._checkpoint(etapa=5, odoo_po_name=po_name, msg=f'PO {po_name} encontrado')

    def _step_06_configurar_po(self, odoo):
        """Etapa 6: Configurar PO (team, payment_term, picking_type, company) + corrigir precos."""
        rec = self._get_recebimento()
        if rec.etapa_atual >= 6:
            return

        po_id = rec.odoo_po_id
        logger.info(f"  Etapa 6/18: Configurando PO {po_id}")
        self._atualizar_redis(rec.id, 2, 6, rec.total_etapas, f'Configurando PO...')

        # Idempotencia: verificar se team ja configurado
        po_data = odoo.execute_kw(
            'purchase.order', 'read',
            [[po_id]],
            {'fields': ['team_id', 'payment_term_id', 'picking_type_id', 'company_id']}
        )
        team_configured = False
        if po_data:
            po = po_data[0]
            team_id = po['team_id'][0] if isinstance(po.get('team_id'), (list, tuple)) else po.get('team_id')
            team_configured = (team_id == self.TEAM_ID)

        # Configurar team/payment_term se necessario
        if not team_configured:
            values = {
                'team_id': self.TEAM_ID,
                'payment_provider_id': self.PAYMENT_PROVIDER_ID,
                'payment_term_id': self.PAYMENT_TERM_A_VISTA,
                'company_id': self.COMPANY_FB,
                'picking_type_id': self.PICKING_TYPE_FB,
            }

            self._write_and_verify(
                odoo, 'purchase.order', [po_id], values,
                'Configurar PO',
                critical_fields=['team_id', 'payment_term_id', 'picking_type_id', 'company_id', 'payment_provider_id']
            )
        else:
            logger.info(f"  PO {po_id}: team ja configurado (team_id={self.TEAM_ID})")

        # Corrigir precos das PO lines a partir do DFe (fonte de verdade)
        self._corrigir_precos_po_dfe(odoo, po_id, rec.odoo_dfe_id)

        self._checkpoint(etapa=6, msg='PO configurado')

    def _corrigir_precos_po_dfe(self, odoo, po_id, dfe_id):
        """
        Corrige price_unit das PO lines para bater com vUnCom do DFe.

        O action_gerar_po_dfe do Odoo redistribui arredondamentos internamente,
        gerando price_unit divergente do vUnCom da NF-e em algumas linhas.
        Este metodo corrige para que PO lines (e consequentemente stock.move)
        reflitam o preco unitario real da NF-e.

        Args:
            odoo: Conexao Odoo ativa
            po_id: ID do purchase.order
            dfe_id: ID do DFe (fonte de verdade dos precos)
        """
        if not dfe_id:
            logger.warning("  _corrigir_precos_po_dfe: dfe_id ausente, pulando")
            return

        # 1. Ler DFe lines (fonte de verdade)
        dfe_lines = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe.line', 'search_read',
            [[['dfe_id', '=', dfe_id]]],
            {'fields': ['id', 'product_id', 'det_prod_vuncom']}
        )

        # Indexar por product_id
        dfe_price_by_pid = {}
        for dl in dfe_lines:
            if dl.get('product_id') and dl.get('det_prod_vuncom'):
                pid = dl['product_id'][0] if isinstance(dl['product_id'], (list, tuple)) else dl['product_id']
                dfe_price_by_pid[pid] = float(dl['det_prod_vuncom'])

        if not dfe_price_by_pid:
            logger.info("  Precos DFe: nenhum preco encontrado nas DFe lines")
            return

        # 2. Ler PO lines
        po_lines = odoo.execute_kw(
            'purchase.order.line', 'search_read',
            [[['order_id', '=', po_id]]],
            {'fields': ['id', 'product_id', 'price_unit']}
        )

        # 3. Corrigir divergencias
        corrigidos = 0
        for pl in po_lines:
            pid = pl['product_id'][0] if isinstance(pl.get('product_id'), (list, tuple)) else None
            if pid and pid in dfe_price_by_pid:
                dfe_price = dfe_price_by_pid[pid]
                po_price = pl.get('price_unit', 0)
                if abs(dfe_price - po_price) > 0.0001:
                    odoo.write('purchase.order.line', pl['id'], {'price_unit': dfe_price})
                    logger.info(
                        f"    PO line {pl['id']}: price_unit {po_price} -> {dfe_price}"
                    )
                    corrigidos += 1

        if corrigidos:
            logger.info(f"  Precos corrigidos: {corrigidos} PO lines")
        else:
            logger.info(f"  Precos ja corretos (0 divergencias)")

    def _step_07_confirmar_po(self, odoo):
        """Etapa 7: Confirmar PO (button_confirm) via fire_and_poll."""
        rec = self._get_recebimento()
        if rec.etapa_atual >= 7:
            return

        po_id = rec.odoo_po_id
        logger.info(f"  Etapa 7/18: Confirmando PO (fire_and_poll)")
        self._atualizar_redis(rec.id, 2, 7, rec.total_etapas, 'Confirmando PO...')

        # Idempotencia: verificar state
        po_data = odoo.execute_kw(
            'purchase.order', 'read',
            [[po_id]],
            {'fields': ['state']}
        )
        if po_data and po_data[0].get('state') != 'draft':
            logger.info(f"  PO {po_id}: state={po_data[0]['state']}, ja confirmado")
            self._checkpoint(etapa=7, msg=f"PO state={po_data[0]['state']}")
            return

        def fire_confirmar_po():
            return odoo.execute_kw(
                'purchase.order', 'button_confirm',
                [[po_id]],
                {'context': {'validate_analytic': True}},
                timeout_override=self.FIRE_TIMEOUT
            )

        def poll_confirmar_po():
            po = odoo.execute_kw(
                'purchase.order', 'read',
                [[po_id]],
                {'fields': ['state']}
            )
            if po and po[0].get('state') != 'draft':
                return po[0]['state']
            return None

        self._fire_and_poll(odoo, fire_confirmar_po, poll_confirmar_po, 'Confirmar PO')
        self._checkpoint(etapa=7, msg='PO confirmado')

    def _step_08_aprovar_po(self, odoo):
        """Etapa 8: Aprovar PO (button_approve) via fire_and_poll, se necessario."""
        rec = self._get_recebimento()
        if rec.etapa_atual >= 8:
            return

        po_id = rec.odoo_po_id
        logger.info(f"  Etapa 8/18: Verificando aprovacao PO")
        self._atualizar_redis(rec.id, 2, 8, rec.total_etapas, 'Aprovando PO...')

        # Idempotencia: verificar state
        po_data = odoo.execute_kw(
            'purchase.order', 'read',
            [[po_id]],
            {'fields': ['state']}
        )

        if not po_data or po_data[0].get('state') != 'to approve':
            state = po_data[0].get('state') if po_data else 'unknown'
            logger.info(f"  PO {po_id}: state={state}, aprovacao nao necessaria")
            self._checkpoint(etapa=8, msg=f'PO state={state}')
            return

        def fire_aprovar_po():
            return odoo.execute_kw(
                'purchase.order', 'button_approve',
                [[po_id]],
                timeout_override=self.FIRE_TIMEOUT
            )

        def poll_aprovar_po():
            po = odoo.execute_kw(
                'purchase.order', 'read',
                [[po_id]],
                {'fields': ['state']}
            )
            if po and po[0].get('state') != 'to approve':
                return po[0]['state']
            return None

        try:
            self._fire_and_poll(odoo, fire_aprovar_po, poll_aprovar_po, 'Aprovar PO')
            logger.info(f"  PO {po_id} aprovado")
        except Exception as e:
            logger.warning(f"  Erro ao aprovar PO {po_id}: {e}")
            # Nao levantar exception — continuar mesmo sem aprovacao

        self._checkpoint(etapa=8, msg='PO aprovado')

    # =================================================================
    # FASE 3: Picking / Recebimento (etapas 9-12)
    # =================================================================

    def _step_09_buscar_picking(self, odoo):
        """Etapa 9: Buscar picking gerado pelo PO."""
        rec = self._get_recebimento()
        if rec.etapa_atual >= 9:
            return

        po_id = rec.odoo_po_id
        logger.info(f"  Etapa 9/18: Buscando picking do PO {po_id}")
        self._atualizar_redis(rec.id, 3, 9, rec.total_etapas, 'Buscando picking...')

        # Tentar ate 5 vezes com espera de 8s
        picking = None
        max_tentativas = 5
        espera = 8
        for tentativa in range(max_tentativas):
            pickings = odoo.execute_kw(
                'stock.picking', 'search_read',
                [[
                    ['purchase_id', '=', po_id],
                    ['picking_type_code', '=', 'incoming'],
                ]],
                {
                    'fields': ['id', 'name', 'state', 'move_line_ids', 'move_ids',
                               'location_id', 'location_dest_id'],
                    'limit': 1,
                    'order': 'id desc',
                }
            )
            if pickings:
                picking = pickings[0]
                break
            if tentativa < max_tentativas - 1:
                logger.info(
                    f"  Picking nao encontrado, tentativa {tentativa + 1}/{max_tentativas}, "
                    f"aguardando {espera}s..."
                )
                time.sleep(espera)

        if not picking:
            raise ValueError(f"Picking nao encontrado para PO {po_id}")

        picking_id = picking['id']
        picking_name = picking['name']
        logger.info(f"  Picking encontrado: {picking_name} (ID={picking_id}, state={picking['state']})")

        # Se picking nao esta assigned, tentar forcar
        if picking['state'] not in ('assigned', 'done'):
            try:
                odoo.execute_kw(
                    'stock.picking', 'action_assign',
                    [[picking_id]],
                    timeout_override=90
                )
                logger.info(f"  action_assign executado em {picking_name}")
            except Exception as e:
                if 'cannot marshal None' not in str(e):
                    logger.warning(f"  action_assign falhou: {e}")

        self._checkpoint(
            etapa=9,
            odoo_picking_id=picking_id,
            odoo_picking_name=picking_name,
            msg=f'Picking {picking_name} encontrado'
        )

    def _step_10_preencher_lotes(self, odoo):
        """Etapa 10: Preencher lotes no picking (com commit por lote)."""
        rec = self._get_recebimento()
        if rec.etapa_atual >= 10:
            return

        picking_id = rec.odoo_picking_id
        if not picking_id:
            raise ValueError("odoo_picking_id nao encontrado — etapa 9 nao executou")

        logger.info(f"  Etapa 10/18: Preenchendo lotes no picking {picking_id}")
        self._atualizar_redis(rec.id, 3, 10, rec.total_etapas, 'Preenchendo lotes...')

        # Verificar state do picking — se done, pular
        picking_data = odoo.execute_kw(
            'stock.picking', 'read',
            [[picking_id]],
            {'fields': ['state', 'move_line_ids', 'move_ids', 'location_id', 'location_dest_id']}
        )
        if picking_data and picking_data[0].get('state') == 'done':
            logger.warning(f"  Picking {picking_id} ja validado (state=done), pulando lotes")
            self._checkpoint(etapa=10, msg='Picking ja done')
            return

        # Filtrar apenas lotes pendentes
        lotes_pendentes = rec.lotes.filter_by(processado=False).all()
        if not lotes_pendentes:
            logger.info(f"  Todos os lotes ja processados")
            self._checkpoint(etapa=10, msg='Lotes ja processados')
            return

        self._preencher_lotes_picking(odoo, rec, picking_data[0] if picking_data else {'id': picking_id})
        self._checkpoint(etapa=10, msg='Lotes preenchidos')

    def _step_11_aprovar_quality_checks(self, odoo):
        """Etapa 11: Aprovar todos os quality checks do picking."""
        rec = self._get_recebimento()
        if rec.etapa_atual >= 11:
            return

        picking_id = rec.odoo_picking_id
        logger.info(f"  Etapa 11/18: Aprovando quality checks")
        self._atualizar_redis(rec.id, 3, 11, rec.total_etapas, 'Aprovando quality checks...')

        # Verificar state do picking — se done, pular
        picking_data = odoo.execute_kw(
            'stock.picking', 'read',
            [[picking_id]],
            {'fields': ['state']}
        )
        if picking_data and picking_data[0].get('state') == 'done':
            logger.info(f"  Picking {picking_id} ja validado, pulando quality checks")
            self._checkpoint(etapa=11, msg='Picking ja done')
            return

        self._aprovar_quality_checks(odoo, picking_id)
        self._checkpoint(etapa=11, msg='Quality checks aprovados')

    def _step_12_validar_picking(self, odoo):
        """Etapa 12: Validar picking (button_validate) via fire_and_poll."""
        rec = self._get_recebimento()
        if rec.etapa_atual >= 12:
            return

        picking_id = rec.odoo_picking_id
        logger.info(f"  Etapa 12/18: Validando picking (fire_and_poll)")
        self._atualizar_redis(rec.id, 3, 12, rec.total_etapas, 'Validando picking...')

        # Idempotencia: verificar state
        picking_data = odoo.execute_kw(
            'stock.picking', 'read',
            [[picking_id]],
            {'fields': ['state']}
        )
        if picking_data and picking_data[0].get('state') == 'done':
            logger.info(f"  Picking {picking_id}: ja validado (state=done)")
            self._checkpoint(etapa=12, msg='Picking ja validado')
            return

        # Verificar se assigned
        if picking_data and picking_data[0].get('state') != 'assigned':
            state = picking_data[0].get('state')
            raise ValueError(
                f"Picking {picking_id} nao esta 'assigned' (state={state})"
            )

        def fire_validar():
            return odoo.execute_kw(
                'stock.picking', 'button_validate',
                [[picking_id]],
                {'context': {
                    'skip_backorder': True,
                    'picking_ids_not_to_backorder': [picking_id],
                }},
                timeout_override=self.FIRE_TIMEOUT
            )

        def poll_validar():
            p = odoo.execute_kw(
                'stock.picking', 'read',
                [[picking_id]],
                {'fields': ['state']}
            )
            if p and p[0].get('state') == 'done':
                return 'done'
            return None

        self._fire_and_poll(odoo, fire_validar, poll_validar, 'Validar Picking')
        logger.info(f"  Picking {picking_id} validado (state=done)")
        self._checkpoint(etapa=12, msg='Picking validado')

    # =================================================================
    # FASE 4: Fatura (etapas 13-16)
    # =================================================================

    def _step_13_criar_invoice(self, odoo):
        """Etapa 13: Criar invoice a partir do PO via fire_and_poll."""
        rec = self._get_recebimento()
        if rec.etapa_atual >= 13:
            return

        po_id = rec.odoo_po_id
        logger.info(f"  Etapa 13/18: Criando invoice (fire_and_poll)")
        self._atualizar_redis(rec.id, 4, 13, rec.total_etapas, 'Criando fatura...')

        # Idempotencia: verificar se PO ja tem invoice
        po_data = odoo.execute_kw(
            'purchase.order', 'read',
            [[po_id]],
            {'fields': ['invoice_ids']}
        )
        existing_ids = po_data[0].get('invoice_ids', []) if po_data else []
        if existing_ids:
            invoice_id = existing_ids[-1]
            logger.info(f"  PO {po_id} ja tem invoice (ID={invoice_id}), pulando criacao")
            self._checkpoint(etapa=13, odoo_invoice_id=invoice_id, msg='Invoice ja existia')
            return

        def fire_criar():
            return odoo.execute_kw(
                'purchase.order', 'action_create_invoice',
                [[po_id]],
                timeout_override=self.FIRE_TIMEOUT
            )

        def poll_criar():
            po = odoo.execute_kw(
                'purchase.order', 'read',
                [[po_id]],
                {'fields': ['invoice_ids']}
            )
            ids = po[0].get('invoice_ids', []) if po else []
            if ids:
                return ids[-1]
            return None

        invoice_id = self._fire_and_poll(odoo, fire_criar, poll_criar, 'Criar Invoice')

        # Se poll retornou dict, extrair id
        if isinstance(invoice_id, dict):
            invoice_id = invoice_id.get('res_id') or invoice_id.get('id')

        if not invoice_id:
            raise ValueError(f"Invoice nao foi criada para PO {po_id}")

        self._checkpoint(etapa=13, odoo_invoice_id=invoice_id, msg='Invoice criada')

    def _step_14_extrair_invoice(self, odoo):
        """Etapa 14: Extrair e confirmar dados da invoice criada."""
        rec = self._get_recebimento()
        if rec.etapa_atual >= 14:
            return

        invoice_id = rec.odoo_invoice_id
        if not invoice_id:
            raise ValueError("odoo_invoice_id nao encontrado — etapa 13 nao executou")

        logger.info(f"  Etapa 14/18: Extraindo dados invoice {invoice_id}")
        self._atualizar_redis(rec.id, 4, 14, rec.total_etapas, 'Localizando fatura...')

        invoice_data = odoo.execute_kw(
            'account.move', 'read',
            [[invoice_id]],
            {'fields': ['name', 'state']}
        )
        if not invoice_data:
            raise ValueError(f"Invoice {invoice_id} nao encontrada no Odoo")

        invoice_name = invoice_data[0]['name']
        logger.info(f"  Invoice encontrada: {invoice_name} (ID={invoice_id}, state={invoice_data[0]['state']})")

        self._checkpoint(etapa=14, odoo_invoice_name=invoice_name, msg=f'Invoice {invoice_name}')

    def _step_15_configurar_invoice(self, odoo):
        """Etapa 15: Configurar invoice (situacao_nf, impostos)."""
        rec = self._get_recebimento()
        if rec.etapa_atual >= 15:
            return

        invoice_id = rec.odoo_invoice_id
        logger.info(f"  Etapa 15/18: Configurando invoice {invoice_id}")
        self._atualizar_redis(rec.id, 4, 15, rec.total_etapas, 'Configurando fatura...')

        # Idempotencia: verificar se ja configurada
        inv_data = odoo.execute_kw(
            'account.move', 'read',
            [[invoice_id]],
            {'fields': ['l10n_br_situacao_nf', 'state']}
        )
        if inv_data:
            situacao = inv_data[0].get('l10n_br_situacao_nf')
            state = inv_data[0].get('state')
            if situacao == 'autorizado' or state == 'posted':
                logger.info(f"  Invoice {invoice_id}: ja configurada (situacao={situacao}, state={state})")
                self._checkpoint(etapa=15, msg='Invoice ja configurada')
                return

        # Setar situacao NF-e como autorizado
        self._write_and_verify(
            odoo, 'account.move', [invoice_id],
            {'l10n_br_situacao_nf': 'autorizado'},
            'Configurar Invoice',
            critical_fields=['l10n_br_situacao_nf']
        )

        # Recalcular impostos — pre-calculo (opcional)
        try:
            odoo.execute_kw(
                'account.move',
                'onchange_l10n_br_calcular_imposto',
                [[invoice_id]]
            )
            logger.info(f"  Impostos recalculados (onchange) na invoice {invoice_id}")
        except Exception as e:
            logger.warning(f"  Recalculo onchange falhou (nao critico): {e}")

        # Ler write_date ANTES para detectar conclusao no poll
        inv_pre = odoo.execute_kw(
            'account.move', 'read', [[invoice_id]],
            {'fields': ['write_date']}
        )
        write_date_antes = inv_pre[0]['write_date'] if inv_pre else None

        # Atualizar Impostos (btn) — OBRIGATORIO, ~2 min, usar fire_and_poll
        logger.info(f"  Atualizar Impostos (fire_and_poll, ~2min)...")

        def fire_impostos():
            return odoo.execute_kw(
                'account.move',
                'onchange_l10n_br_calcular_imposto_btn',
                [[invoice_id]],
                timeout_override=self.FIRE_TIMEOUT
            )

        def poll_impostos():
            inv = odoo.execute_kw(
                'account.move', 'read', [[invoice_id]],
                {'fields': ['write_date']}
            )
            if inv and inv[0]['write_date'] != write_date_antes:
                return True  # Invoice foi modificada — impostos recalculados
            return None

        self._fire_and_poll(odoo, fire_impostos, poll_impostos, 'Atualizar Impostos')
        logger.info(f"  Atualizar Impostos concluido na invoice {invoice_id}")

        # Verificar total apos recalculo (log informativo)
        inv_check = odoo.execute_kw(
            'account.move', 'read',
            [[invoice_id]],
            {'fields': ['amount_total', 'amount_untaxed']}
        )
        if inv_check:
            total = inv_check[0].get('amount_total', 0)
            untaxed = inv_check[0].get('amount_untaxed', 0)
            logger.info(f"  Invoice {invoice_id}: total={total}, base={untaxed}")

        self._checkpoint(etapa=15, msg='Invoice configurada')

    def _step_16_confirmar_invoice(self, odoo):
        """Etapa 16: Confirmar invoice (action_post) via fire_and_poll."""
        rec = self._get_recebimento()
        if rec.etapa_atual >= 16:
            return

        invoice_id = rec.odoo_invoice_id
        logger.info(f"  Etapa 16/18: Confirmando invoice (fire_and_poll)")
        self._atualizar_redis(rec.id, 4, 16, rec.total_etapas, 'Confirmando fatura...')

        # Idempotencia: verificar state
        inv_data = odoo.execute_kw(
            'account.move', 'read',
            [[invoice_id]],
            {'fields': ['state']}
        )
        if inv_data and inv_data[0].get('state') == 'posted':
            logger.info(f"  Invoice {invoice_id}: ja confirmada (state=posted)")
            self._checkpoint(etapa=16, msg='Invoice ja confirmada')
            return

        def fire_confirmar():
            return odoo.execute_kw(
                'account.move', 'action_post',
                [[invoice_id]],
                {'context': {'validate_analytic': True}},
                timeout_override=self.FIRE_TIMEOUT
            )

        def poll_confirmar():
            inv = odoo.execute_kw(
                'account.move', 'read',
                [[invoice_id]],
                {'fields': ['state']}
            )
            if inv and inv[0].get('state') == 'posted':
                return 'posted'
            return None

        self._fire_and_poll(odoo, fire_confirmar, poll_confirmar, 'Confirmar Invoice')
        logger.info(f"  Invoice {invoice_id} confirmada (state=posted)")
        self._checkpoint(etapa=16, msg='Invoice confirmada')

    # =================================================================
    # FASE 5: Finalizacao (etapas 17-18)
    # =================================================================

    def _step_17_atualizar_status(self, _odoo):
        """Etapa 17: Atualizar status local."""
        rec = self._get_recebimento()
        if rec.etapa_atual >= 17:
            return

        logger.info(f"  Etapa 17/18: Atualizando status local")
        self._atualizar_redis(rec.id, 5, 17, rec.total_etapas, 'Atualizando status...')
        self._checkpoint(etapa=17, msg='Status atualizado')

    def _step_18_criar_movimentacoes(self, odoo):
        """Etapa 18: Criar MovimentacaoEstoque."""
        rec = self._get_recebimento()
        if rec.etapa_atual >= 18:
            return

        logger.info(f"  Etapa 18/18: Criando MovimentacaoEstoque")
        self._atualizar_redis(rec.id, 5, 18, rec.total_etapas, 'Registrando movimentacoes...')

        try:
            self._criar_movimentacoes_estoque(odoo)
            logger.info(f"  MovimentacaoEstoque criadas com sucesso")
        except Exception as e:
            # Nao falhar o recebimento por erro na movimentacao
            logger.warning(
                f"  Erro ao criar MovimentacaoEstoque (nao critico): {e}"
            )

        self._checkpoint(etapa=18, msg='Movimentacoes registradas')

    # =================================================================
    # Sub-rotinas reutilizadas
    # =================================================================

    def _preencher_lotes_picking(self, odoo, recebimento, picking):
        """
        Preenche stock.move.line com lote + quantidade para cada produto.

        - Agrupa lotes por product_id
        - Primeira entrada: atualiza line existente
        - Entradas adicionais: cria novas lines
        - Lotes com validade: cria stock.lot manualmente
        - Commit apos CADA lote para granularidade de retomada
        """
        # Filtrar apenas lotes pendentes
        lotes = recebimento.lotes.filter_by(processado=False).all()
        if not lotes:
            logger.info(f"  Nenhum lote pendente para processar")
            return

        picking_id = picking['id']

        # Agrupar lotes por product_id
        lotes_por_produto = {}
        for lote in lotes:
            pid = lote.odoo_product_id
            if pid not in lotes_por_produto:
                lotes_por_produto[pid] = []
            lotes_por_produto[pid].append(lote)

        # Buscar move_lines atuais do picking
        move_lines = odoo.execute_kw(
            'stock.move.line', 'search_read',
            [[['picking_id', '=', picking_id]]],
            {
                'fields': [
                    'id', 'product_id', 'move_id', 'qty_done',
                    'quantity', 'product_uom_id', 'location_id', 'location_dest_id',
                ],
            }
        )

        # Buscar demands dos moves para ajuste de arredondamento
        move_ids = list({
            ml['move_id'][0]
            for ml in move_lines
            if ml.get('move_id')
        })
        move_demands = {}
        if move_ids:
            moves = odoo.execute_kw(
                'stock.move', 'read',
                [move_ids],
                {'fields': ['id', 'product_id', 'product_uom_qty']}
            )
            for m in moves:
                pid = m['product_id'][0] if m.get('product_id') else None
                move_demands[pid] = m['product_uom_qty']

        # Indexar move_lines por product_id
        lines_por_produto = {}
        for ml in move_lines:
            pid = ml['product_id'][0] if ml.get('product_id') else None
            if pid not in lines_por_produto:
                lines_por_produto[pid] = []
            lines_por_produto[pid].append(ml)

        for product_id, lotes_produto in lotes_por_produto.items():
            existing_lines = lines_por_produto.get(product_id, [])

            # Quantidade efetiva: usar demand do move se diferenca < 0.01
            # Evita partially_available por arredondamento decimal
            move_demand = move_demands.get(product_id)

            for i, lote in enumerate(lotes_produto):
                # Skip se ja processado (check extra por seguranca)
                if lote.processado:
                    continue

                # Resolver lote (criar stock.lot se tem data_validade)
                lot_data = self._resolver_lote(
                    odoo, lote, product_id, recebimento.company_id
                )

                # Ajustar quantidade: usar demand do move se diferenca < 0.01
                qty = lote.quantidade  # Decimal do DB (Numeric)
                if (move_demand is not None
                        and len(lotes_produto) == 1
                        and abs(float(qty) - move_demand) < 0.01):
                    qty = Decimal(str(move_demand))

                if i == 0 and existing_lines:
                    # Primeira entrada: atualizar line existente
                    line = existing_lines[0]
                    write_data = {
                        'quantity': float(qty),
                    }
                    write_data.update(lot_data)

                    odoo.write('stock.move.line', line['id'], write_data)
                    lote.processado = True
                    lote.odoo_move_line_id = line['id']
                    logger.debug(
                        f"    Lote '{lote.lote_nome}' (qtd={lote.quantidade} -> {qty}) "
                        f"atualizado na line {line['id']}"
                    )
                else:
                    # Entradas adicionais: criar nova line
                    ref_line = existing_lines[0] if existing_lines else None
                    if not ref_line:
                        logger.warning(
                            f"    Sem line de referencia para produto {product_id}, "
                            f"pulando lote '{lote.lote_nome}'"
                        )
                        continue

                    nova_line_data = {
                        'move_id': ref_line['move_id'][0] if ref_line['move_id'] else None,
                        'picking_id': picking_id,
                        'product_id': product_id,
                        'product_uom_id': ref_line['product_uom_id'][0] if ref_line['product_uom_id'] else None,
                        'quantity': float(qty),
                        'location_id': ref_line['location_id'][0] if ref_line['location_id'] else None,
                        'location_dest_id': ref_line['location_dest_id'][0] if ref_line['location_dest_id'] else None,
                    }
                    nova_line_data.update(lot_data)

                    nova_line_id = odoo.create('stock.move.line', nova_line_data)
                    lote.processado = True
                    lote.odoo_move_line_id = nova_line_id
                    logger.debug(
                        f"    Lote '{lote.lote_nome}' (qtd={lote.quantidade}) "
                        f"criado como nova line {nova_line_id}"
                    )

                # Commit apos CADA lote para granularidade de retomada
                commit_with_retry(db.session)

    def _resolver_lote(self, odoo, lote, product_id, company_id):
        """
        Resolve como identificar o lote na stock.move.line.

        - Se produto usa expiration_date E informou data_validade:
          cria/atualiza stock.lot manualmente -> retorna {lot_id: X}
        - Senao: retorna {lot_name: 'LOTE-XXX'} (Odoo cria auto ao validar)

        Returns:
            Dict com 'lot_id' ou 'lot_name'
        """
        if (lote.data_validade and
                lote.produto_tracking in ('lot', 'serial') and
                lote.lote_nome):

            # Formatar expiration_date para Odoo (YYYY-MM-DD HH:MM:SS)
            if hasattr(lote.data_validade, 'strftime'):
                exp_date_str = lote.data_validade.strftime('%Y-%m-%d') + ' 00:00:00'
            else:
                exp_date_str = str(lote.data_validade) + ' 00:00:00'

            # Verificar se lote ja existe no Odoo
            lote_existente = odoo.search('stock.lot', [
                ['name', '=', lote.lote_nome],
                ['product_id', '=', product_id],
                ['company_id', '=', company_id],
            ])

            if lote_existente:
                lot_id = lote_existente[0]
                odoo.write('stock.lot', lot_id, {
                    'expiration_date': exp_date_str,
                })
                logger.debug(f"    stock.lot {lot_id} atualizado com validade={exp_date_str}")
            else:
                lot_id = odoo.create('stock.lot', {
                    'name': lote.lote_nome,
                    'product_id': product_id,
                    'company_id': company_id,
                    'expiration_date': exp_date_str,
                })
                logger.debug(f"    stock.lot {lot_id} criado: '{lote.lote_nome}' validade={exp_date_str}")

            lote.odoo_lot_id = lot_id
            return {'lot_id': lot_id}

        elif lote.lote_nome:
            return {'lot_name': lote.lote_nome}
        else:
            # Sem lote (tracking=none)
            return {}

    def _aprovar_quality_checks(self, odoo, picking_id):
        """
        Busca TODOS quality checks do picking e aprova como 'pass'.
        Inclui checks zerados — aprovamos tudo automaticamente para LF.
        """
        checks = odoo.execute_kw(
            'quality.check', 'search_read',
            [[
                ['picking_id', '=', picking_id],
                ['quality_state', '=', 'none'],
            ]],
            {'fields': ['id', 'test_type', 'quality_state']}
        )

        if not checks:
            logger.info(f"    Nenhum quality check pendente para picking {picking_id}")
            return

        logger.info(f"    Aprovando {len(checks)} quality checks")

        for check in checks:
            check_id = check['id']
            test_type = check.get('test_type', 'passfail')

            try:
                if test_type == 'measure':
                    odoo.write('quality.check', check_id, {'measure': 0})
                    try:
                        odoo.execute_kw('quality.check', 'do_measure', [[check_id]])
                    except Exception as e:
                        if 'cannot marshal None' not in str(e):
                            raise
                else:
                    try:
                        odoo.execute_kw('quality.check', 'do_pass', [[check_id]])
                    except Exception as e:
                        if 'cannot marshal None' not in str(e):
                            raise

                logger.debug(f"    QC {check_id} ({test_type}): aprovado")

            except Exception as e:
                logger.error(f"    Erro no quality check {check_id}: {e}")
                raise

    def _criar_movimentacoes_estoque(self, odoo):
        """
        Cria MovimentacaoEstoque a partir dos lotes processados.
        """
        from app.estoque.models import MovimentacaoEstoque
        from app.producao.models import CadastroPalletizacao

        rec = self._get_recebimento()
        lotes_processados = rec.lotes.filter_by(processado=True).all()
        if not lotes_processados:
            logger.warning(f"  Nenhum lote processado para MovimentacaoEstoque")
            return

        # Coletar product_ids e move_line_ids para busca batch
        product_ids = list(set(lt.odoo_product_id for lt in lotes_processados if lt.odoo_product_id))
        move_line_ids = list(set(lt.odoo_move_line_id for lt in lotes_processados if lt.odoo_move_line_id))

        # Buscar codigos de produto
        codigos = {}
        if product_ids:
            try:
                produtos = odoo.execute_kw(
                    'product.product', 'read',
                    [product_ids],
                    {'fields': ['id', 'default_code']}
                )
                codigos = {p['id']: p.get('default_code') for p in produtos if p.get('default_code')}
            except Exception as e:
                logger.error(f"  Erro ao buscar codigos produto: {e}")

        # Buscar move_ids das move_lines
        move_ids = {}
        if move_line_ids:
            try:
                mls = odoo.execute_kw(
                    'stock.move.line', 'read',
                    [move_line_ids],
                    {'fields': ['id', 'move_id']}
                )
                for ml in mls:
                    mid = ml.get('move_id')
                    if mid:
                        move_ids[ml['id']] = mid[0] if isinstance(mid, (list, tuple)) else mid
            except Exception as e:
                logger.error(f"  Erro ao buscar move_ids: {e}")

        criadas = 0
        for lote in lotes_processados:
            try:
                cod_produto = codigos.get(lote.odoo_product_id)
                if not cod_produto:
                    continue

                move_id = move_ids.get(lote.odoo_move_line_id)
                if not move_id:
                    continue

                # Verificar se produto e comprado
                cadastro = CadastroPalletizacao.query.filter_by(
                    cod_produto=str(cod_produto), produto_comprado=True
                ).first()
                if not cadastro:
                    continue

                # Verificar duplicacao
                existente = MovimentacaoEstoque.query.filter_by(
                    odoo_move_id=str(move_id)
                ).first()
                if existente:
                    existente.lote_nome = lote.lote_nome
                    existente.data_validade = lote.data_validade
                    existente.atualizado_em = agora_utc_naive()
                    continue

                entrada = MovimentacaoEstoque(
                    cod_produto=str(cod_produto),
                    nome_produto=lote.odoo_product_name or cadastro.nome_produto,
                    data_movimentacao=agora_utc_naive().date(),
                    tipo_movimentacao='ENTRADA',
                    local_movimentacao='COMPRA',
                    qtd_movimentacao=lote.quantidade,
                    odoo_picking_id=str(rec.odoo_picking_id),
                    odoo_move_id=str(move_id),
                    tipo_origem='ODOO',
                    lote_nome=lote.lote_nome,
                    data_validade=lote.data_validade,
                    num_pedido=rec.odoo_po_name,
                    observacao=f"Recebimento LF {rec.odoo_picking_name} - Lote: {lote.lote_nome}",
                    criado_por=rec.usuario or 'Sistema Recebimento LF',
                    ativo=True
                )
                db.session.add(entrada)
                criadas += 1

            except Exception as e:
                logger.error(f"  Erro ao criar MovimentacaoEstoque para lote {lote.lote_nome}: {e}")

        commit_with_retry(db.session)
        logger.info(f"  MovimentacaoEstoque: {criadas} criadas")

    # =================================================================
    # Helpers de infraestrutura
    # =================================================================

    def _fire_and_poll(self, odoo, fire_fn, poll_fn, step_name,
                       fire_timeout=None, poll_interval=None, max_poll_time=None):
        """
        Padrao Fire and Poll: dispara acao no Odoo com timeout curto e polla ate resultado.

        1. fire_fn() com timeout curto (60s) — se timeout, OK (acao continua no Odoo)
        2. poll_fn() a cada poll_interval ate retornar truthy
        3. Se max_poll_time excedido, raise TimeoutError

        NOTA sobre reconexao: as closures fire_fn/poll_fn capturam `odoo` do escopo
        da funcao chamadora. O OdooConnection tem Circuit Breaker com retry e
        reconexao automatica (via _models=None). Erros de conexao durante poll
        sao logados e o polling continua — a proxima chamada reconecta automaticamente.

        Args:
            odoo: Conexao Odoo (para referencia)
            fire_fn: callable que dispara a acao Odoo (pode dar timeout)
            poll_fn: callable que retorna resultado ou None/False
            step_name: nome do passo (para log)
            fire_timeout: timeout do fire (default FIRE_TIMEOUT=60s)
            poll_interval: intervalo entre polls (default POLL_INTERVAL=10s)
            max_poll_time: tempo maximo de polling (default MAX_POLL_TIME=1800s)

        Returns:
            Resultado retornado por fire_fn (se nao deu timeout) ou poll_fn (se deu timeout)

        Raises:
            TimeoutError: se max_poll_time excedido sem resultado no poll
            Exception: erros nao relacionados a timeout
        """
        fire_timeout = fire_timeout or self.FIRE_TIMEOUT
        poll_interval = poll_interval or self.POLL_INTERVAL
        max_poll_time = max_poll_time or self.MAX_POLL_TIME

        # 1. FIRE — dispara acao com timeout curto
        fire_result = None
        needs_polling = False

        try:
            fire_result = fire_fn()
            logger.info(f"  [{step_name}] Acao completou dentro do timeout ({fire_timeout}s)")
        except Exception as e:
            error_str = str(e)
            if 'Timeout' in error_str or 'timeout' in error_str or 'timed out' in error_str:
                logger.info(
                    f"  [{step_name}] Timeout ao disparar ({fire_timeout}s) — "
                    f"esperado, iniciando polling..."
                )
                needs_polling = True
            elif 'cannot marshal None' in error_str:
                logger.info(f"  [{step_name}] Acao completou (retorno None)")
                fire_result = None
            else:
                raise

        # Se fire completou, verificar se resultado ja e valido
        if not needs_polling:
            try:
                poll_result = poll_fn()
                if poll_result:
                    return poll_result
            except Exception:
                pass
            if fire_result:
                return fire_result

        # 2. POLL — verificar resultado periodicamente
        elapsed = 0
        poll_count = 0
        while elapsed < max_poll_time:
            time.sleep(poll_interval)
            elapsed += poll_interval
            poll_count += 1

            # Atualizar Redis com tempo de espera
            rec = self._get_recebimento()
            self._atualizar_redis(
                rec.id,
                rec.fase_atual or 1,
                rec.etapa_atual or 1,
                rec.total_etapas,
                f'Aguardando {step_name}... {elapsed}s'
            )

            try:
                poll_result = poll_fn()
                if poll_result:
                    logger.info(
                        f"  [{step_name}] Poll #{poll_count} ({elapsed}s): resultado encontrado"
                    )
                    return poll_result
                else:
                    logger.debug(
                        f"  [{step_name}] Poll #{poll_count} ({elapsed}s): aguardando..."
                    )
            except Exception as e:
                error_str = str(e)
                if ('Timeout' in error_str or 'timeout' in error_str or
                        'timed out' in error_str or 'Connection' in error_str or
                        'SSL' in error_str or 'socket' in error_str):
                    logger.warning(
                        f"  [{step_name}] Erro de conexao no poll #{poll_count}, "
                        f"reconectando Odoo..."
                    )
                else:
                    logger.warning(
                        f"  [{step_name}] Erro no poll #{poll_count}: {e}"
                    )

        # 3. Timeout de polling — erro
        raise TimeoutError(
            f"[{step_name}] Polling expirou apos {max_poll_time}s "
            f"({poll_count} tentativas) sem resultado"
        )

    def _atualizar_redis(self, recebimento_id, fase, etapa, total_etapas, msg=''):
        """Atualiza progresso no Redis para polling da tela de status."""
        try:
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            redis_conn = Redis.from_url(redis_url)
            progresso = {
                'recebimento_id': recebimento_id,
                'fase': fase,
                'etapa': etapa,
                'total_etapas': total_etapas,
                'percentual': int((etapa / total_etapas) * 100) if total_etapas else 0,
                'mensagem': msg,
            }
            redis_conn.setex(
                f'recebimento_lf_progresso:{recebimento_id}',
                3600,  # TTL 1 hora
                json.dumps(progresso)
            )
        except Exception:
            pass  # Redis opcional para progresso
