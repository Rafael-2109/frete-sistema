"""
Service para processamento de recebimento fisico no Odoo (Worker RQ)
====================================================================

Responsabilidades (7 passos):
1. Conectar ao Odoo e verificar picking (state=assigned)
2. Preencher stock.move.line (lote + quantidade)
3. Preencher quality checks (passfail: do_pass/do_fail)
4. Preencher quality checks (measure: write + do_measure)
5. Validar picking (button_validate)
6. Verificar resultado (state=done)
7. Atualizar status local

IMPORTANTE: Este service e chamado pelo job RQ, NAO diretamente pela rota.
"""

import logging
from datetime import datetime

from app import db
from app.recebimento.models import (
    RecebimentoFisico,
    RecebimentoLote,
    RecebimentoQualityCheck,
)
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


class RecebimentoFisicoOdooService:
    """Processa recebimentos fisicos no Odoo."""

    def processar_recebimento(self, recebimento_id, usuario_nome=None):
        """
        Processa um recebimento completo no Odoo (7 passos).

        Args:
            recebimento_id: ID do RecebimentoFisico local
            usuario_nome: Nome do usuario (para log)

        Returns:
            Dict com resultado do processamento

        Raises:
            Exception se erro irrecuperavel
        """
        recebimento = RecebimentoFisico.query.get(recebimento_id)
        if not recebimento:
            raise ValueError(f"Recebimento {recebimento_id} nao encontrado")

        # Marcar como processando
        recebimento.status = 'processando'
        recebimento.tentativas += 1
        db.session.commit()

        try:
            odoo = get_odoo_connection()

            # =====================================================
            # PASSO 1: Verificar picking
            # =====================================================
            logger.info(
                f"[Recebimento {recebimento_id}] Passo 1/7: Verificando picking "
                f"{recebimento.odoo_picking_name} (ID={recebimento.odoo_picking_id})"
            )

            picking = odoo.execute_kw(
                'stock.picking', 'search_read',
                [[['id', '=', recebimento.odoo_picking_id]]],
                {
                    'fields': ['id', 'name', 'state', 'move_line_ids', 'move_ids',
                               'location_id', 'location_dest_id'],
                    'limit': 1,
                }
            )

            if not picking:
                raise ValueError(
                    f"Picking {recebimento.odoo_picking_id} nao encontrado no Odoo"
                )

            picking = picking[0]

            if picking['state'] != 'assigned':
                if picking['state'] == 'done':
                    # Picking ja validado por outro meio
                    logger.warning(
                        f"[Recebimento {recebimento_id}] Picking ja esta 'done'. "
                        "Marcando como processado."
                    )
                    recebimento.status = 'processado'
                    recebimento.processado_em = datetime.utcnow()
                    db.session.commit()
                    return {'status': 'ja_processado', 'picking_state': 'done'}
                else:
                    raise ValueError(
                        f"Picking state={picking['state']} (esperado: assigned)"
                    )

            # =====================================================
            # PASSO 2: Preencher lotes + quantidades
            # =====================================================
            logger.info(
                f"[Recebimento {recebimento_id}] Passo 2/7: Preenchendo lotes"
            )
            self._preencher_lotes(odoo, recebimento, picking)

            # =====================================================
            # PASSO 3: Quality checks passfail
            # =====================================================
            checks_passfail = recebimento.quality_checks.filter_by(
                test_type='passfail'
            ).all()

            if checks_passfail:
                logger.info(
                    f"[Recebimento {recebimento_id}] Passo 3/7: "
                    f"Preenchendo {len(checks_passfail)} quality checks (passfail)"
                )
                self._preencher_quality_checks_passfail(odoo, checks_passfail)

            # =====================================================
            # PASSO 4: Quality checks measure
            # =====================================================
            checks_measure = recebimento.quality_checks.filter_by(
                test_type='measure'
            ).all()

            if checks_measure:
                logger.info(
                    f"[Recebimento {recebimento_id}] Passo 4/7: "
                    f"Preenchendo {len(checks_measure)} quality checks (measure)"
                )
                self._preencher_quality_checks_measure(odoo, checks_measure)

            # =====================================================
            # PASSO 5: Validar picking
            # =====================================================
            logger.info(
                f"[Recebimento {recebimento_id}] Passo 5/7: Validando picking"
            )
            self._validar_picking(odoo, recebimento.odoo_picking_id)

            # =====================================================
            # PASSO 6: Verificar resultado
            # =====================================================
            logger.info(
                f"[Recebimento {recebimento_id}] Passo 6/7: Verificando resultado"
            )
            picking_final = odoo.execute_kw(
                'stock.picking', 'search_read',
                [[['id', '=', recebimento.odoo_picking_id]]],
                {
                    'fields': ['id', 'state', 'date_done'],
                    'limit': 1,
                }
            )

            if picking_final and picking_final[0]['state'] == 'done':
                resultado = 'processado'
            else:
                state_final = picking_final[0]['state'] if picking_final else 'desconhecido'
                raise ValueError(
                    f"Picking nao ficou 'done' apos button_validate (state={state_final})"
                )

            # =====================================================
            # PASSO 7: Atualizar status local
            # =====================================================
            logger.info(
                f"[Recebimento {recebimento_id}] Passo 7/7: Atualizando status local"
            )
            recebimento.status = 'processado'
            recebimento.processado_em = datetime.utcnow()
            recebimento.erro_mensagem = None
            db.session.commit()

            logger.info(
                f"[Recebimento {recebimento_id}] SUCESSO: Picking "
                f"{recebimento.odoo_picking_name} validado no Odoo!"
            )

            return {
                'status': 'processado',
                'picking_state': 'done',
                'recebimento_id': recebimento_id,
            }

        except Exception as e:
            logger.error(
                f"[Recebimento {recebimento_id}] ERRO no processamento: {e}"
            )
            recebimento.status = 'erro'
            recebimento.erro_mensagem = str(e)[:500]
            db.session.commit()
            raise

    def _preencher_lotes(self, odoo, recebimento, picking):
        """
        Preenche stock.move.line com lote + quantidade para cada produto.

        Logica:
        - Para cada produto, agrupa os lotes do recebimento
        - Se produto usa expiration_date E operador informou data_validade:
          cria stock.lot manualmente COM expiration_date, usa lot_id na line
        - Senao: usa lot_name na line (Odoo cria lote auto ao validar)
        - Primeira entrada: atualiza a stock.move.line existente
        - Entradas adicionais: cria novas stock.move.line
        """
        lotes = recebimento.lotes.all()

        # Agrupar lotes por product_id
        lotes_por_produto = {}
        for lote in lotes:
            if lote.odoo_product_id not in lotes_por_produto:
                lotes_por_produto[lote.odoo_product_id] = []
            lotes_por_produto[lote.odoo_product_id].append(lote)

        # Buscar move_lines atuais do picking
        move_lines = odoo.execute_kw(
            'stock.move.line', 'search_read',
            [[['picking_id', '=', recebimento.odoo_picking_id]]],
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
            product_id = ml['product_id'][0] if ml['product_id'] else None
            if product_id not in lines_por_produto:
                lines_por_produto[product_id] = []
            lines_por_produto[product_id].append(ml)

        for product_id, lotes_produto in lotes_por_produto.items():
            existing_lines = lines_por_produto.get(product_id, [])

            for i, lote in enumerate(lotes_produto):
                # Determinar se deve criar stock.lot manualmente (com expiration_date)
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
                    lote.odoo_move_line_criado_id = line['id']
                    logger.debug(
                        f"  Lote '{lote.lote_nome}' (qtd={lote.quantidade}) "
                        f"atualizado na line {line['id']}"
                    )
                else:
                    # Entradas adicionais: criar nova line
                    ref_line = existing_lines[0] if existing_lines else None
                    if not ref_line:
                        logger.warning(
                            f"  Sem line de referencia para produto {product_id}, "
                            f"pulando lote '{lote.lote_nome}'"
                        )
                        continue

                    nova_line_data = {
                        'move_id': ref_line['move_id'][0] if ref_line['move_id'] else None,
                        'picking_id': recebimento.odoo_picking_id,
                        'product_id': product_id,
                        'product_uom_id': ref_line['product_uom_id'][0] if ref_line['product_uom_id'] else None,
                        'quantity': float(lote.quantidade),
                        'location_id': ref_line['location_id'][0] if ref_line['location_id'] else None,
                        'location_dest_id': ref_line['location_dest_id'][0] if ref_line['location_dest_id'] else None,
                    }
                    nova_line_data.update(lot_data)

                    nova_line_id = odoo.create('stock.move.line', nova_line_data)
                    lote.processado = True
                    lote.odoo_move_line_criado_id = nova_line_id
                    logger.debug(
                        f"  Lote '{lote.lote_nome}' (qtd={lote.quantidade}) "
                        f"criado como nova line {nova_line_id}"
                    )

        db.session.commit()

    def _resolver_lote(self, odoo, lote, product_id, company_id):
        """
        Resolve como identificar o lote na stock.move.line:
        - Se produto usa expiration_date E operador informou data_validade:
          cria/atualiza stock.lot manualmente COM expiration_date → retorna {lot_id: X}
        - Senao: retorna {lot_name: 'LOTE-XXX'} (Odoo cria auto ao validar)

        Returns:
            Dict com 'lot_id' ou 'lot_name' para merge no write/create da line
        """
        # Verificar se deve criar lote manualmente (com validade)
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
                # Atualizar expiration_date
                odoo.write('stock.lot', lot_id, {
                    'expiration_date': exp_date_str,
                })
                logger.debug(
                    f"  stock.lot {lot_id} atualizado com expiration_date={exp_date_str}"
                )
            else:
                # Criar stock.lot manualmente COM expiration_date
                lot_id = odoo.create('stock.lot', {
                    'name': lote.lote_nome,
                    'product_id': product_id,
                    'company_id': company_id,
                    'expiration_date': exp_date_str,
                })
                logger.debug(
                    f"  stock.lot {lot_id} criado: '{lote.lote_nome}' "
                    f"expiration_date={exp_date_str}"
                )

            lote.odoo_lot_id = lot_id
            return {'lot_id': lot_id}

        else:
            # Sem validade: usar lot_name (Odoo cria auto ao validar)
            return {'lot_name': lote.lote_nome}

    def _preencher_quality_checks_passfail(self, odoo, checks):
        """Executa do_pass ou do_fail para cada check passfail."""
        for check in checks:
            try:
                if check.resultado == 'pass':
                    try:
                        odoo.execute_kw(
                            'quality.check', 'do_pass',
                            [[check.odoo_check_id]]
                        )
                    except Exception as e:
                        if 'cannot marshal None' not in str(e):
                            raise
                else:
                    try:
                        odoo.execute_kw(
                            'quality.check', 'do_fail',
                            [[check.odoo_check_id]]
                        )
                    except Exception as e:
                        if 'cannot marshal None' not in str(e):
                            raise

                check.processado = True
                logger.debug(
                    f"  Quality check {check.odoo_check_id}: {check.resultado}"
                )

            except Exception as e:
                logger.error(
                    f"  Erro no quality check {check.odoo_check_id}: {e}"
                )
                raise

        db.session.commit()

    def _preencher_quality_checks_measure(self, odoo, checks):
        """Preenche valor medido e chama do_measure para validacao automatica."""
        for check in checks:
            try:
                # 1. Preencher valor medido
                odoo.write(
                    'quality.check',
                    check.odoo_check_id,
                    {'measure': float(check.valor_medido) if check.valor_medido else 0}
                )

                # 2. Executar do_measure (Odoo valida contra tolerancias)
                try:
                    odoo.execute_kw(
                        'quality.check', 'do_measure',
                        [[check.odoo_check_id]]
                    )
                except Exception as e:
                    if 'cannot marshal None' not in str(e):
                        raise

                check.processado = True
                logger.debug(
                    f"  Quality check measure {check.odoo_check_id}: "
                    f"valor={check.valor_medido}"
                )

            except Exception as e:
                logger.error(
                    f"  Erro no quality check measure {check.odoo_check_id}: {e}"
                )
                raise

        db.session.commit()

    def _validar_picking(self, odoo, picking_id):
        """
        Chama button_validate no picking para finalizar recebimento.

        IMPORTANTE: 'cannot marshal None' e retorno normal do Odoo = sucesso.
        """
        try:
            odoo.execute_kw(
                'stock.picking', 'button_validate',
                [[picking_id]]
            )
        except Exception as e:
            if 'cannot marshal None' not in str(e):
                raise
            # Sucesso (padrao Odoo - retorna None que causa marshal error)
            logger.debug(f"  button_validate retornou None (sucesso) para picking {picking_id}")
