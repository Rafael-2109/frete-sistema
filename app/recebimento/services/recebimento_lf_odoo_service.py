"""
Service para processamento de Recebimento LF no Odoo (Worker RQ)
================================================================

Responsabilidades (5 fases, 18 passos):
FASE 1 - Preparacao DFe:
    1. Buscar DFe no Odoo
    2. Avancar status do DFe (se necessario)
    3. Atualizar data_entrada e tipo_pedido

FASE 2 - Gerar e Configurar PO:
    4. action_gerar_po_dfe (timeout=180s)
    5. Buscar PO gerado
    6. Configurar PO (team, payment_term, picking_type)
    7. Confirmar PO (button_confirm)
    8. Aprovar PO (button_approve, se necessario)

FASE 3 - Picking / Recebimento:
    9. Buscar picking gerado
    10. Preencher lotes (CFOP!=1902: manual, CFOP=1902: auto)
    11. Aprovar quality checks
    12. Validar picking (button_validate)

FASE 4 - Fatura:
    13. Criar invoice (action_create_invoice)
    14. Buscar invoice gerada
    15. Configurar invoice (situacao_nf, impostos)
    16. Confirmar invoice (action_post)

FASE 5 - Finalizacao:
    17. Atualizar status local
    18. Criar MovimentacaoEstoque

IMPORTANTE: Este service e chamado pelo job RQ, NAO diretamente pela rota.
"""

import json
import logging
import os
import time
from datetime import datetime, date
from app.utils.timezone import agora_utc_naive

from redis import Redis

from app import db
from app.recebimento.models import RecebimentoLf
from app.odoo.utils.connection import get_odoo_connection
from app.utils.database_retry import commit_with_retry

logger = logging.getLogger(__name__)


class RecebimentoLfOdooService:
    """Processa Recebimento LF completo no Odoo (5 fases)."""

    # IDs fixos (conforme IDS_FIXOS.md)
    COMPANY_FB = 1
    COMPANY_LF = 5
    PICKING_TYPE_FB = 1
    TEAM_ID = 119
    PAYMENT_PROVIDER_ID = 30
    PAYMENT_TERM_A_VISTA = 2791

    # Timeouts
    TIMEOUT_GERAR_PO = 180  # 3 minutos (operacao pesada)
    TIMEOUT_PADRAO = 60

    def processar_recebimento(self, recebimento_id, usuario_nome=None):
        """
        Processa um Recebimento LF completo no Odoo (5 fases, 18 passos).

        Suporta retomada: se fase_atual > 0, pula fases ja concluidas.

        Args:
            recebimento_id: ID do RecebimentoLf local
            usuario_nome: Nome do usuario (para log)

        Returns:
            Dict com resultado do processamento

        Raises:
            Exception se erro irrecuperavel
        """
        recebimento = RecebimentoLf.query.get(recebimento_id)
        if not recebimento:
            raise ValueError(f"Recebimento LF {recebimento_id} nao encontrado")

        # Marcar como processando
        recebimento.status = 'processando'
        recebimento.tentativas += 1
        commit_with_retry(db.session)

        try:
            odoo = get_odoo_connection()

            dfe_id = recebimento.odoo_dfe_id
            po_id = recebimento.odoo_po_id
            picking_id = recebimento.odoo_picking_id
            invoice_id = recebimento.odoo_invoice_id

            # =========================================================
            # FASE 1: Preparacao DFe (passos 1-3)
            # =========================================================
            if recebimento.fase_atual < 1:
                logger.info(
                    f"[RecLF {recebimento_id}] FASE 1: Preparacao DFe {dfe_id}"
                )
                self._atualizar_progresso(recebimento, fase=1, etapa=1, msg='Preparando DFe...')
                dfe_id = self._fase1_preparar_dfe(odoo, recebimento)
                recebimento.fase_atual = 1
                commit_with_retry(db.session)

            # =========================================================
            # FASE 2: Gerar e Configurar PO (passos 4-8)
            # =========================================================
            if recebimento.fase_atual < 2:
                logger.info(
                    f"[RecLF {recebimento_id}] FASE 2: Gerar e configurar PO"
                )
                self._atualizar_progresso(recebimento, fase=2, etapa=4, msg='Gerando PO...')

                # COMMIT antes de operacao longa (Gerar PO demora ~2min)
                db.session.commit()

                po_id = self._fase2_gerar_configurar_po(odoo, recebimento, dfe_id)
                recebimento.odoo_po_id = po_id
                recebimento.fase_atual = 2
                commit_with_retry(db.session)

            # =========================================================
            # FASE 3: Picking / Recebimento (passos 9-12)
            # =========================================================
            if recebimento.fase_atual < 3:
                logger.info(
                    f"[RecLF {recebimento_id}] FASE 3: Processar picking"
                )
                self._atualizar_progresso(recebimento, fase=3, etapa=9, msg='Processando picking...')

                # COMMIT antes de operacao longa (picking + lotes + QC pode demorar)
                db.session.commit()

                po_id = recebimento.odoo_po_id
                picking_id = self._fase3_processar_picking(odoo, recebimento, po_id)
                recebimento.odoo_picking_id = picking_id
                recebimento.fase_atual = 3
                commit_with_retry(db.session)

            # =========================================================
            # FASE 4: Fatura (passos 13-16)
            # =========================================================
            if recebimento.fase_atual < 4:
                logger.info(
                    f"[RecLF {recebimento_id}] FASE 4: Criar e confirmar fatura"
                )
                self._atualizar_progresso(recebimento, fase=4, etapa=13, msg='Criando fatura...')

                # COMMIT antes de operacao longa
                db.session.commit()

                po_id = recebimento.odoo_po_id
                invoice_id = self._fase4_criar_fatura(odoo, recebimento, po_id)
                recebimento.odoo_invoice_id = invoice_id
                recebimento.fase_atual = 4
                commit_with_retry(db.session)

            # =========================================================
            # FASE 5: Finalizacao (passos 17-18)
            # =========================================================
            if recebimento.fase_atual < 5:
                logger.info(
                    f"[RecLF {recebimento_id}] FASE 5: Finalizacao"
                )
                self._atualizar_progresso(recebimento, fase=5, etapa=17, msg='Finalizando...')
                self._fase5_finalizar(odoo, recebimento)
                recebimento.fase_atual = 5

            # Sucesso!
            recebimento.status = 'processado'
            recebimento.processado_em = agora_utc_naive()
            recebimento.erro_mensagem = None
            commit_with_retry(db.session)

            logger.info(
                f"[RecLF {recebimento_id}] SUCESSO! "
                f"DFe={dfe_id} PO={recebimento.odoo_po_name} "
                f"Picking={recebimento.odoo_picking_name} "
                f"Invoice={recebimento.odoo_invoice_name}"
            )

            return {
                'status': 'processado',
                'recebimento_id': recebimento_id,
                'odoo_po_id': recebimento.odoo_po_id,
                'odoo_po_name': recebimento.odoo_po_name,
                'odoo_picking_id': recebimento.odoo_picking_id,
                'odoo_picking_name': recebimento.odoo_picking_name,
                'odoo_invoice_id': recebimento.odoo_invoice_id,
                'odoo_invoice_name': recebimento.odoo_invoice_name,
            }

        except Exception as e:
            logger.error(
                f"[RecLF {recebimento_id}] ERRO na fase {recebimento.fase_atual}: {e}"
            )
            recebimento.status = 'erro'
            recebimento.erro_mensagem = str(e)[:500]
            commit_with_retry(db.session)
            raise

    # =================================================================
    # FASE 1: Preparacao DFe
    # =================================================================

    def _fase1_preparar_dfe(self, odoo, recebimento):
        """
        Prepara o DFe no Odoo:
        1. Buscar DFe e validar existencia
        2. Avancar status se necessario (01 -> 02 -> 03 -> 04)
        3. Atualizar data_entrada e tipo_pedido

        Returns:
            dfe_id confirmado
        """
        dfe_id = recebimento.odoo_dfe_id

        # Passo 1: Buscar DFe
        logger.info(f"  Passo 1/18: Buscando DFe {dfe_id}")
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

        dfe = dfe[0]
        status_atual = dfe.get('l10n_br_status', '01')

        # Passo 2: Avancar status se necessario
        logger.info(f"  Passo 2/18: Status DFe = '{status_atual}', avancando se necessario")
        self._atualizar_progresso(recebimento, fase=1, etapa=2, msg=f'Status DFe: {status_atual}')

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

        # Re-buscar status
        dfe_atualizado = odoo.execute_kw(
            'l10n_br_ciel_it_account.dfe', 'search_read',
            [[['id', '=', dfe_id]]],
            {'fields': ['l10n_br_status'], 'limit': 1}
        )
        status_final = dfe_atualizado[0]['l10n_br_status'] if dfe_atualizado else status_atual

        # Passo 3: Atualizar data_entrada e tipo_pedido
        logger.info(f"  Passo 3/18: Atualizando DFe (data_entrada + tipo_pedido)")
        self._atualizar_progresso(recebimento, fase=1, etapa=3, msg='Configurando DFe...')

        hoje = date.today().strftime('%Y-%m-%d')
        odoo.write('l10n_br_ciel_it_account.dfe', [dfe_id], {
            'l10n_br_data_entrada': hoje,
            'l10n_br_tipo_pedido': 'serv-industrializacao',
        })

        logger.info(
            f"  DFe {dfe_id} preparado: status={status_final}, "
            f"data_entrada={hoje}, tipo=serv-industrializacao"
        )

        return dfe_id

    # =================================================================
    # FASE 2: Gerar e Configurar PO
    # =================================================================

    def _fase2_gerar_configurar_po(self, odoo, recebimento, dfe_id):
        """
        Gera PO a partir do DFe e configura campos.

        Returns:
            po_id do Purchase Order criado
        """
        # Passo 4: Gerar PO (operacao pesada ~2min)
        logger.info(f"  Passo 4/18: Gerando PO (timeout={self.TIMEOUT_GERAR_PO}s)")
        self._atualizar_progresso(recebimento, fase=2, etapa=4, msg='Gerando PO no Odoo (pode demorar)...')

        try:
            po_result = odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe',
                'action_gerar_po_dfe',
                [[dfe_id]],
                {'context': {'validate_analytic': True}},
                timeout_override=self.TIMEOUT_GERAR_PO
            )
        except Exception as e:
            if 'cannot marshal None' not in str(e):
                raise
            po_result = None

        # Passo 5: Buscar PO gerado
        logger.info(f"  Passo 5/18: Buscando PO gerado")
        self._atualizar_progresso(recebimento, fase=2, etapa=5, msg='Localizando PO...')

        po_id = None

        # Tentar extrair do resultado
        if po_result and isinstance(po_result, dict):
            po_id = po_result.get('res_id')

        # Buscar pelo DFe
        if not po_id:
            po_search = odoo.execute_kw(
                'purchase.order', 'search_read',
                [[['dfe_id', '=', dfe_id]]],
                {'fields': ['id', 'name', 'state'], 'limit': 1}
            )
            if po_search:
                po_id = po_search[0]['id']

        # Buscar pelo purchase_id do DFe (many2one → [id, 'name'] ou False)
        if not po_id:
            dfe_data = odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe', 'read',
                [[dfe_id]],
                {'fields': ['purchase_id']}
            )
            if dfe_data:
                purchase_ref = dfe_data[0].get('purchase_id')
                if purchase_ref:
                    po_id = purchase_ref[0]  # many2one: [id, 'name']

        if not po_id:
            raise ValueError("Purchase Order nao foi criado apos action_gerar_po_dfe")

        # Buscar nome do PO
        po_data = odoo.execute_kw(
            'purchase.order', 'read',
            [[po_id]],
            {'fields': ['name', 'state']}
        )
        po_name = po_data[0]['name'] if po_data else f'PO-{po_id}'
        recebimento.odoo_po_name = po_name

        logger.info(f"  PO encontrado: {po_name} (ID={po_id})")

        # Passo 6: Configurar PO
        logger.info(f"  Passo 6/18: Configurando PO")
        self._atualizar_progresso(recebimento, fase=2, etapa=6, msg=f'Configurando {po_name}...')

        odoo.write('purchase.order', [po_id], {
            'team_id': self.TEAM_ID,
            'payment_provider_id': self.PAYMENT_PROVIDER_ID,
            'payment_term_id': self.PAYMENT_TERM_A_VISTA,
            'company_id': self.COMPANY_FB,
            'picking_type_id': self.PICKING_TYPE_FB,
        })

        # Passo 7: Confirmar PO
        logger.info(f"  Passo 7/18: Confirmando PO")
        self._atualizar_progresso(recebimento, fase=2, etapa=7, msg=f'Confirmando {po_name}...')

        try:
            odoo.execute_kw(
                'purchase.order', 'button_confirm',
                [[po_id]],
                {'context': {'validate_analytic': True}}
            )
        except Exception as e:
            if 'cannot marshal None' not in str(e):
                raise

        # Passo 8: Aprovar PO (se necessario)
        logger.info(f"  Passo 8/18: Verificando aprovacao PO")
        self._atualizar_progresso(recebimento, fase=2, etapa=8, msg='Aprovando PO...')

        po_state = odoo.execute_kw(
            'purchase.order', 'read',
            [[po_id]],
            {'fields': ['state']}
        )

        if po_state and po_state[0].get('state') == 'to approve':
            try:
                odoo.execute_kw(
                    'purchase.order', 'button_approve',
                    [[po_id]]
                )
                logger.info(f"  PO {po_name} aprovado")
            except Exception as e:
                if 'cannot marshal None' not in str(e):
                    logger.warning(f"  Erro ao aprovar PO {po_name}: {e}")
                    # Nao levantar exception — continuar mesmo sem aprovacao
        elif po_state:
            logger.info(f"  PO {po_name}: state={po_state[0].get('state')}, aprovacao nao necessaria")

        return po_id

    # =================================================================
    # FASE 3: Picking / Recebimento
    # =================================================================

    def _fase3_processar_picking(self, odoo, recebimento, po_id):
        """
        Busca picking, preenche lotes, aprova quality checks, valida.

        Returns:
            picking_id validado
        """
        # Passo 9: Buscar picking
        logger.info(f"  Passo 9/18: Buscando picking do PO {po_id}")
        self._atualizar_progresso(recebimento, fase=3, etapa=9, msg='Buscando picking...')

        # Pode demorar pois o Odoo precisa processar o "Receber Produtos"
        # Tentar ate 3 vezes com espera
        picking = None
        for tentativa in range(3):
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

            if tentativa < 2:
                logger.info(f"  Picking nao encontrado, tentativa {tentativa + 1}/3, aguardando 5s...")
                time.sleep(5)

        if not picking:
            raise ValueError(f"Picking nao encontrado para PO {po_id}")

        picking_id = picking['id']
        picking_name = picking['name']
        recebimento.odoo_picking_name = picking_name

        logger.info(f"  Picking encontrado: {picking_name} (ID={picking_id}, state={picking['state']})")

        # Se picking nao esta assigned, pode estar em waiting/confirmed
        if picking['state'] not in ('assigned', 'done'):
            # Tentar forcar assign
            try:
                odoo.execute_kw(
                    'stock.picking', 'action_assign',
                    [[picking_id]]
                )
                logger.info(f"  action_assign executado em {picking_name}")
            except Exception as e:
                if 'cannot marshal None' not in str(e):
                    logger.warning(f"  action_assign falhou: {e}")

            # Re-verificar state
            picking = odoo.execute_kw(
                'stock.picking', 'search_read',
                [[['id', '=', picking_id]]],
                {
                    'fields': ['id', 'name', 'state', 'move_line_ids', 'move_ids',
                               'location_id', 'location_dest_id'],
                    'limit': 1,
                }
            )[0]

        if picking['state'] == 'done':
            logger.warning(f"  Picking {picking_name} ja validado")
            return picking_id

        if picking['state'] != 'assigned':
            raise ValueError(
                f"Picking {picking_name} nao esta 'assigned' (state={picking['state']})"
            )

        # Passo 10: Preencher lotes
        logger.info(f"  Passo 10/18: Preenchendo lotes no picking")
        self._atualizar_progresso(recebimento, fase=3, etapa=10, msg='Preenchendo lotes...')
        self._preencher_lotes_picking(odoo, recebimento, picking)

        # Passo 11: Quality checks — aprovar TODOS como 'pass'
        logger.info(f"  Passo 11/18: Aprovando quality checks")
        self._atualizar_progresso(recebimento, fase=3, etapa=11, msg='Aprovando quality checks...')
        self._aprovar_quality_checks(odoo, picking_id)

        # Passo 12: Validar picking
        logger.info(f"  Passo 12/18: Validando picking")
        self._atualizar_progresso(recebimento, fase=3, etapa=12, msg='Validando picking...')
        self._validar_picking(odoo, picking_id)

        # Verificar resultado
        picking_final = odoo.execute_kw(
            'stock.picking', 'search_read',
            [[['id', '=', picking_id]]],
            {'fields': ['state'], 'limit': 1}
        )

        if picking_final and picking_final[0]['state'] == 'done':
            logger.info(f"  Picking {picking_name} validado com sucesso (state=done)")
        else:
            state_final = picking_final[0]['state'] if picking_final else 'desconhecido'
            raise ValueError(
                f"Picking {picking_name} nao ficou 'done' apos button_validate "
                f"(state={state_final})"
            )

        return picking_id

    def _preencher_lotes_picking(self, odoo, recebimento, picking):
        """
        Preenche stock.move.line com lote + quantidade para cada produto.

        Reutiliza logica do RecebimentoFisicoOdooService:
        - Agrupa lotes por product_id
        - Primeira entrada: atualiza line existente
        - Entradas adicionais: cria novas lines
        - Lotes com validade: cria stock.lot manualmente
        """
        lotes = recebimento.lotes.all()
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

        # Indexar move_lines por product_id
        lines_por_produto = {}
        for ml in move_lines:
            pid = ml['product_id'][0] if ml.get('product_id') else None
            if pid not in lines_por_produto:
                lines_por_produto[pid] = []
            lines_por_produto[pid].append(ml)

        for product_id, lotes_produto in lotes_por_produto.items():
            existing_lines = lines_por_produto.get(product_id, [])

            for i, lote in enumerate(lotes_produto):
                # Resolver lote (criar stock.lot se tem data_validade)
                lot_data = self._resolver_lote(
                    odoo, lote, product_id, recebimento.company_id
                )

                if i == 0 and existing_lines:
                    # Primeira entrada: atualizar line existente
                    line = existing_lines[0]
                    write_data = {
                        'quantity': float(lote.quantidade),
                    }
                    write_data.update(lot_data)

                    odoo.write('stock.move.line', line['id'], write_data)
                    lote.processado = True
                    lote.odoo_move_line_id = line['id']
                    logger.debug(
                        f"    Lote '{lote.lote_nome}' (qtd={lote.quantidade}) "
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
                        'quantity': float(lote.quantidade),
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
                    # Para measure: setar valor 0 e chamar do_measure
                    odoo.write('quality.check', check_id, {'measure': 0})
                    try:
                        odoo.execute_kw('quality.check', 'do_measure', [[check_id]])
                    except Exception as e:
                        if 'cannot marshal None' not in str(e):
                            raise
                else:
                    # Para passfail: aprovar direto
                    try:
                        odoo.execute_kw('quality.check', 'do_pass', [[check_id]])
                    except Exception as e:
                        if 'cannot marshal None' not in str(e):
                            raise

                logger.debug(f"    QC {check_id} ({test_type}): aprovado")

            except Exception as e:
                logger.error(f"    Erro no quality check {check_id}: {e}")
                raise

    def _validar_picking(self, odoo, picking_id):
        """
        Chama button_validate no picking.
        'cannot marshal None' e retorno normal do Odoo = sucesso.
        """
        try:
            odoo.execute_kw(
                'stock.picking', 'button_validate',
                [[picking_id]],
                timeout_override=self.TIMEOUT_GERAR_PO  # 180s — validacao com QC pode demorar
            )
        except Exception as e:
            if 'cannot marshal None' not in str(e):
                raise
            logger.debug(f"    button_validate retornou None (sucesso) para picking {picking_id}")

    # =================================================================
    # FASE 4: Fatura
    # =================================================================

    def _fase4_criar_fatura(self, odoo, recebimento, po_id):
        """
        Cria, configura e confirma fatura a partir do PO.

        Returns:
            invoice_id da fatura criada
        """
        # Passo 13: Criar invoice
        logger.info(f"  Passo 13/18: Criando invoice")
        self._atualizar_progresso(recebimento, fase=4, etapa=13, msg='Criando fatura...')

        try:
            invoice_result = odoo.execute_kw(
                'purchase.order', 'action_create_invoice',
                [[po_id]],
                timeout_override=self.TIMEOUT_GERAR_PO  # 180s — invoice pode demorar
            )
        except Exception as e:
            if 'cannot marshal None' not in str(e):
                raise
            invoice_result = None

        # Passo 14: Buscar invoice gerada
        logger.info(f"  Passo 14/18: Buscando invoice gerada")
        self._atualizar_progresso(recebimento, fase=4, etapa=14, msg='Localizando fatura...')

        invoice_id = None

        # Tentar extrair do resultado
        if invoice_result and isinstance(invoice_result, dict):
            invoice_id = invoice_result.get('res_id')

        # Buscar pelo PO (invoice_ids)
        if not invoice_id:
            po_updated = odoo.execute_kw(
                'purchase.order', 'read',
                [[po_id]],
                {'fields': ['invoice_ids']}
            )
            if po_updated:
                invoice_ids = po_updated[0].get('invoice_ids', [])
                if invoice_ids:
                    invoice_id = invoice_ids[-1]  # Ultima invoice

        if not invoice_id:
            raise ValueError(f"Invoice nao foi criada para PO {po_id}")

        # Buscar nome da invoice
        invoice_data = odoo.execute_kw(
            'account.move', 'read',
            [[invoice_id]],
            {'fields': ['name', 'state']}
        )
        invoice_name = invoice_data[0]['name'] if invoice_data else f'INV-{invoice_id}'
        recebimento.odoo_invoice_name = invoice_name

        logger.info(f"  Invoice encontrada: {invoice_name} (ID={invoice_id})")

        # Passo 15: Configurar invoice
        logger.info(f"  Passo 15/18: Configurando invoice")
        self._atualizar_progresso(recebimento, fase=4, etapa=15, msg=f'Configurando {invoice_name}...')

        # Setar situacao NF-e como autorizado
        odoo.write('account.move', [invoice_id], {
            'l10n_br_situacao_nf': 'autorizado',
        })

        # Recalcular impostos (OPCIONAL — nao falhar se der erro)
        try:
            odoo.execute_kw(
                'account.move',
                'onchange_l10n_br_calcular_imposto',
                [[invoice_id]]
            )
            logger.info(f"  Impostos recalculados na invoice {invoice_name}")
        except Exception as e:
            logger.warning(f"  Recalculo de impostos falhou (nao critico): {e}")

        # Segundo recalculo (btn)
        try:
            odoo.execute_kw(
                'account.move',
                'onchange_l10n_br_calcular_imposto_btn',
                [[invoice_id]]
            )
        except Exception as e:
            logger.warning(f"  Recalculo impostos btn falhou (nao critico): {e}")

        # Passo 16: Confirmar invoice
        logger.info(f"  Passo 16/18: Confirmando invoice")
        self._atualizar_progresso(recebimento, fase=4, etapa=16, msg=f'Confirmando {invoice_name}...')

        try:
            odoo.execute_kw(
                'account.move', 'action_post',
                [[invoice_id]],
                {'context': {'validate_analytic': True}}
            )
        except Exception as e:
            if 'cannot marshal None' not in str(e):
                raise

        # Verificar estado
        invoice_final = odoo.execute_kw(
            'account.move', 'read',
            [[invoice_id]],
            {'fields': ['state']}
        )
        state_final = invoice_final[0]['state'] if invoice_final else 'desconhecido'
        logger.info(f"  Invoice {invoice_name} confirmada (state={state_final})")

        return invoice_id

    # =================================================================
    # FASE 5: Finalizacao
    # =================================================================

    def _fase5_finalizar(self, odoo, recebimento):
        """
        Passo 17: Atualizar status local
        Passo 18: Criar MovimentacaoEstoque
        """
        # Passo 17: Status ja atualizado no processar_recebimento()
        logger.info(f"  Passo 17/18: Status local atualizado")
        self._atualizar_progresso(recebimento, fase=5, etapa=17, msg='Atualizando status...')

        # Passo 18: Criar MovimentacaoEstoque
        logger.info(f"  Passo 18/18: Criando MovimentacaoEstoque")
        self._atualizar_progresso(recebimento, fase=5, etapa=18, msg='Registrando movimentacoes...')

        try:
            self._criar_movimentacoes_estoque(odoo, recebimento)
            logger.info(f"  MovimentacaoEstoque criadas com sucesso")
        except Exception as e:
            # Nao falhar o recebimento por erro na movimentacao
            logger.warning(
                f"  Erro ao criar MovimentacaoEstoque (nao critico): {e}"
            )

    def _criar_movimentacoes_estoque(self, odoo, recebimento):
        """
        Cria MovimentacaoEstoque a partir dos lotes processados.
        Reutiliza logica do RecebimentoFisicoOdooService.
        """
        from app.estoque.models import MovimentacaoEstoque
        from app.producao.models import CadastroPalletizacao

        lotes_processados = recebimento.lotes.filter_by(processado=True).all()
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
                    odoo_picking_id=str(recebimento.odoo_picking_id),
                    odoo_move_id=str(move_id),
                    tipo_origem='ODOO',
                    lote_nome=lote.lote_nome,
                    data_validade=lote.data_validade,
                    num_pedido=recebimento.odoo_po_name,
                    observacao=f"Recebimento LF {recebimento.odoo_picking_name} - Lote: {lote.lote_nome}",
                    criado_por=recebimento.usuario or 'Sistema Recebimento LF',
                    ativo=True
                )
                db.session.add(entrada)
                criadas += 1

            except Exception as e:
                logger.error(f"  Erro ao criar MovimentacaoEstoque para lote {lote.lote_nome}: {e}")

        commit_with_retry(db.session)
        logger.info(f"  MovimentacaoEstoque: {criadas} criadas")

    # =================================================================
    # Helpers
    # =================================================================

    def _atualizar_progresso(self, recebimento, fase, etapa, msg=''):
        """Atualiza progresso no banco e Redis."""
        recebimento.fase_atual = fase
        recebimento.etapa_atual = etapa

        # Atualizar Redis para polling da tela de status
        try:
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
            redis_conn = Redis.from_url(redis_url)
            progresso = {
                'recebimento_id': recebimento.id,
                'fase': fase,
                'etapa': etapa,
                'total_etapas': recebimento.total_etapas,
                'percentual': int((etapa / recebimento.total_etapas) * 100),
                'mensagem': msg,
            }
            redis_conn.setex(
                f'recebimento_lf_progresso:{recebimento.id}',
                3600,  # TTL 1 hora
                json.dumps(progresso)
            )
        except Exception:
            pass  # Redis opcional para progresso
