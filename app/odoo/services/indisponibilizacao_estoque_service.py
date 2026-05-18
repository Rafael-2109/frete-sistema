"""IndisponibilizacaoEstoqueService — bloqueio de lote/local para faturamento.

Encapsula a operacao de "tirar do estoque" sem emitir NF — usada para
estoque deteriorado/perdido/em-quarentena que NAO deve aparecer em
disponivel-para-venda no Odoo.

Mecanismo: `active=False` em `stock.lot` ou `stock.location`. Odoo
deixa de considerar estes registros em reservas/picking auto-create.

CANARY OBRIGATORIO: hipotese deve ser validada em ambiente seguro
ANTES de aplicar em prod, via `canary_lote()` ou `canary_local()`,
que executam o teste e SEMPRE revertem (try/finally). Apos canary
OK, o caller chama `indisponibilizar_*` passando `canary_passou=True`.

Spec: docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md
      §6.2 + §10.1
"""
import logging
import time
import uuid
from typing import Any, Dict, Optional

from app.odoo.models import OperacaoOdooAuditoria
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


class IndisponibilizacaoEstoqueService:
    """Indisponibiliza lote/location no Odoo apos canary validado."""

    def __init__(self, odoo=None):
        self.odoo = odoo or get_odoo_connection()

    # ============================================================
    # Auditoria
    # ============================================================

    def _registrar_op(
        self,
        *,
        tabela_origem: str,
        registro_id: int,
        acao: str,
        modelo_odoo: str,
        status: str,
        executado_por: str,
        ajuste_id: Optional[int] = None,
        odoo_id: Optional[int] = None,
        payload: Optional[Dict[str, Any]] = None,
        resposta: Optional[Dict[str, Any]] = None,
        erro_msg: Optional[str] = None,
        tempo_ms: Optional[int] = None,
        contexto_ref: Optional[str] = None,
    ) -> None:
        """Registra 1 row em operacao_odoo_auditoria.

        F5 (indisponibilizacao/canary) chama Odoo direto, sem
        contexto de inventario obrigatorio. ajuste_id eh opcional;
        se informado, vai como contexto_ref tambem.
        """
        try:
            OperacaoOdooAuditoria.registrar(
                external_id=f'INDISPO-{acao}-{registro_id}-{uuid.uuid4().hex[:8]}',
                tabela_origem=tabela_origem,
                registro_id=registro_id,
                acao=acao,
                modelo_odoo=modelo_odoo,
                odoo_id=odoo_id,
                etapa=None,
                etapa_descricao=f'{acao} {modelo_odoo}',
                status=status,
                payload_json=payload,
                resposta_json=resposta,
                erro_msg=erro_msg,
                tempo_execucao_ms=tempo_ms,
                pipeline_etapa=None,
                contexto_origem='indisponibilizacao',
                contexto_ref=(
                    contexto_ref
                    if contexto_ref is not None
                    else (f'ajuste={ajuste_id}' if ajuste_id else None)
                ),
                executado_por=executado_por,
            )
            # Flush apenas — caller decide commit (consistente com F4).
            # OperacaoOdooAuditoria.registrar() ja chama flush().
        except Exception as e:
            logger.error(
                f'_registrar_op falhou ({acao} {modelo_odoo}={registro_id}): {e}',
                exc_info=True,
            )

    # ============================================================
    # Canaries (testes de hipotese — SEMPRE revertem)
    # ============================================================

    def canary_lote(
        self,
        lot_id: int,
        product_id: int,
        partner_id: int,
        executado_por: str = 'sistema',
        ajuste_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """C1: testa se `stock.lot.active=False` bloqueia faturamento.

        Procedimento:
            1. Le stock.quant antes para confirmar saldo positivo do lote
               (sem saldo nao tem como testar)
            2. Inativa o lote (active=False)
            3. Cria sale.order rascunho com o produto + confirma
            4. Verifica se o lote aparece em move_line_ids candidatos
            5. Cancela a SO (cleanup)
            6. SEMPRE reverte (active=True) — try/finally

        Returns:
            {'passou': bool, 'detalhes': str, 'sale_order_id': int|None}

        IMPORTANTE: este canary cria registros reais no Odoo (SO
        rascunho). Usar APENAS em ambiente de staging ou ciclo
        controlado — em prod polui historico.
        """
        inicio = time.time()
        # 1. Saldo antes
        quants_antes = self.odoo.search_read(
            'stock.quant',
            [['lot_id', '=', lot_id], ['quantity', '>', 0]],
            ['id', 'quantity', 'location_id'],
        )
        if not quants_antes:
            res = {
                'passou': False,
                'detalhes': (
                    f'Lote {lot_id} sem saldo positivo — escolha outro '
                    'para testar canary'
                ),
                'sale_order_id': None,
            }
            self._registrar_op(
                tabela_origem='stock.lot', registro_id=lot_id,
                acao='canary_lote', modelo_odoo='stock.lot',
                status='SKIPPED', executado_por=executado_por,
                ajuste_id=ajuste_id, odoo_id=lot_id, resposta=res,
                erro_msg='sem saldo positivo',
                tempo_ms=int((time.time() - inicio) * 1000),
            )
            return res

        so_id = None
        try:
            # 2. Inativar
            self.odoo.write('stock.lot', [lot_id], {'active': False})
            logger.info(f'canary_lote {lot_id}: active=False (teste)')

            # 3. Criar SO rascunho
            so_id = self.odoo.create('sale.order', {
                'partner_id': partner_id,
                'order_line': [(0, 0, {
                    'product_id': product_id,
                    'product_uom_qty': 1.0,
                })],
            })
            self.odoo.execute_kw(
                'sale.order', 'action_confirm', [[so_id]]
            )

            # 4. Buscar move_lines do picking gerado
            pickings = self.odoo.search_read(
                'stock.picking',
                [['sale_id', '=', so_id]],
                ['id', 'move_line_ids'],
            )
            move_line_ids_total = []
            for p in pickings:
                move_line_ids_total.extend(p.get('move_line_ids') or [])

            if move_line_ids_total:
                mls = self.odoo.read(
                    'stock.move.line',
                    move_line_ids_total,
                    ['id', 'lot_id'],
                )
                lotes_atribuidos = {
                    ml['lot_id'][0]
                    for ml in mls
                    if ml.get('lot_id')
                }
                passou = lot_id not in lotes_atribuidos
            else:
                # Sem move_line — Odoo nao reservou (sem estoque
                # candidato). Sinal positivo: lote esta fora.
                passou = True

            # 5. Cleanup: cancel SO
            try:
                self.odoo.execute_kw(
                    'sale.order', 'action_cancel', [[so_id]]
                )
            except Exception as cleanup_e:
                logger.warning(
                    f'canary_lote {lot_id}: cleanup SO {so_id} falhou: '
                    f'{cleanup_e}'
                )

            res = {
                'passou': passou,
                'detalhes': (
                    f'SO={so_id} move_lines={move_line_ids_total} '
                    f'lote_atribuido={not passou}'
                ),
                'sale_order_id': so_id,
            }
            self._registrar_op(
                tabela_origem='stock.lot', registro_id=lot_id,
                acao='canary_lote', modelo_odoo='stock.lot',
                status='PASSOU' if passou else 'NAO_PASSOU',
                executado_por=executado_por,
                ajuste_id=ajuste_id, odoo_id=lot_id, resposta=res,
                tempo_ms=int((time.time() - inicio) * 1000),
            )
            return res
        except Exception as e:
            self._registrar_op(
                tabela_origem='stock.lot', registro_id=lot_id,
                acao='canary_lote', modelo_odoo='stock.lot',
                status='EXCECAO', executado_por=executado_por,
                ajuste_id=ajuste_id, odoo_id=lot_id, erro_msg=str(e),
                tempo_ms=int((time.time() - inicio) * 1000),
            )
            raise
        finally:
            # 6. SEMPRE reverter (canary nao pode deixar lote inativo)
            try:
                self.odoo.write('stock.lot', [lot_id], {'active': True})
                logger.info(
                    f'canary_lote {lot_id}: revertido para active=True'
                )
            except Exception as e:
                logger.error(
                    f'FALHA AO REVERTER lote {lot_id}: {e}. '
                    'INTERVENCAO MANUAL OBRIGATORIA.',
                    exc_info=True,
                )

    def canary_local(
        self,
        location_id: int,
        product_id: int,
        partner_id: int,
        executado_por: str = 'sistema',
        ajuste_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """C2: testa se `stock.location.active=False` bloqueia faturamento.

        Mesma estrutura de `canary_lote`. Returns dict {'passou': bool,
        'sale_order_id': int|None}.
        """
        inicio = time.time()
        so_id = None
        try:
            self.odoo.write(
                'stock.location', [location_id], {'active': False}
            )
            logger.info(
                f'canary_local {location_id}: active=False (teste)'
            )

            so_id = self.odoo.create('sale.order', {
                'partner_id': partner_id,
                'order_line': [(0, 0, {
                    'product_id': product_id,
                    'product_uom_qty': 1.0,
                })],
            })
            self.odoo.execute_kw(
                'sale.order', 'action_confirm', [[so_id]]
            )

            pickings = self.odoo.search_read(
                'stock.picking',
                [['sale_id', '=', so_id]],
                ['id', 'move_line_ids'],
            )
            move_line_ids = []
            for p in pickings:
                move_line_ids.extend(p.get('move_line_ids') or [])

            if move_line_ids:
                mls = self.odoo.read(
                    'stock.move.line',
                    move_line_ids,
                    ['id', 'location_id'],
                )
                locais = {
                    ml['location_id'][0]
                    for ml in mls
                    if ml.get('location_id')
                }
                passou = location_id not in locais
            else:
                passou = True

            try:
                self.odoo.execute_kw(
                    'sale.order', 'action_cancel', [[so_id]]
                )
            except Exception as cleanup_e:
                logger.warning(
                    f'canary_local {location_id}: cleanup SO {so_id} '
                    f'falhou: {cleanup_e}'
                )

            res = {'passou': passou, 'sale_order_id': so_id}
            self._registrar_op(
                tabela_origem='stock.location', registro_id=location_id,
                acao='canary_local', modelo_odoo='stock.location',
                status='PASSOU' if passou else 'NAO_PASSOU',
                executado_por=executado_por,
                ajuste_id=ajuste_id, odoo_id=location_id, resposta=res,
                tempo_ms=int((time.time() - inicio) * 1000),
            )
            return res
        except Exception as e:
            self._registrar_op(
                tabela_origem='stock.location', registro_id=location_id,
                acao='canary_local', modelo_odoo='stock.location',
                status='EXCECAO', executado_por=executado_por,
                ajuste_id=ajuste_id, odoo_id=location_id, erro_msg=str(e),
                tempo_ms=int((time.time() - inicio) * 1000),
            )
            raise
        finally:
            try:
                self.odoo.write(
                    'stock.location', [location_id], {'active': True}
                )
                logger.info(
                    f'canary_local {location_id}: revertido para '
                    'active=True'
                )
            except Exception as e:
                logger.error(
                    f'FALHA AO REVERTER local {location_id}: {e}. '
                    'INTERVENCAO MANUAL OBRIGATORIA.',
                    exc_info=True,
                )

    # ============================================================
    # Indisponibilizar / Reverter (operacao real, requer canary OK)
    # ============================================================

    def indisponibilizar_lote(
        self,
        lot_id: int,
        canary_passou: bool,
        executado_por: str = 'sistema',
        ajuste_id: Optional[int] = None,
    ) -> bool:
        """Inativa lote no Odoo. EXIGE canary previamente validado.

        Raises:
            RuntimeError: se canary_passou=False.

        Nota: operacao naturalmente idempotente — chamar 2x equivale
        a 1x. Caller pode passar `canary_passou=True` apenas apos
        sucesso em `canary_lote(lot_id, ...)` no mesmo ambiente
        (staging ou pre-prod).
        """
        if not canary_passou:
            raise RuntimeError(
                'canary_lote nao foi validado (canary_passou=False). '
                'Execute canary_lote() em staging primeiro.'
            )
        inicio = time.time()
        self.odoo.write('stock.lot', [lot_id], {'active': False})
        self._registrar_op(
            tabela_origem='stock.lot', registro_id=lot_id,
            acao='indispor_lote', modelo_odoo='stock.lot',
            status='SUCESSO', executado_por=executado_por,
            ajuste_id=ajuste_id, odoo_id=lot_id,
            payload={'active': False},
            tempo_ms=int((time.time() - inicio) * 1000),
        )
        logger.info(f'indisponibilizar_lote {lot_id}: active=False')
        return True

    def reverter_lote(
        self,
        lot_id: int,
        executado_por: str = 'sistema',
        ajuste_id: Optional[int] = None,
    ) -> bool:
        """Reativa lote (rollback de `indisponibilizar_lote`)."""
        inicio = time.time()
        self.odoo.write('stock.lot', [lot_id], {'active': True})
        self._registrar_op(
            tabela_origem='stock.lot', registro_id=lot_id,
            acao='reverter_lote', modelo_odoo='stock.lot',
            status='SUCESSO', executado_por=executado_por,
            ajuste_id=ajuste_id, odoo_id=lot_id,
            payload={'active': True},
            tempo_ms=int((time.time() - inicio) * 1000),
        )
        logger.info(f'reverter_lote {lot_id}: active=True')
        return True

    def indisponibilizar_local(
        self,
        location_id: int,
        canary_passou: bool,
        executado_por: str = 'sistema',
        ajuste_id: Optional[int] = None,
    ) -> bool:
        """Inativa stock.location. EXIGE canary previamente validado.

        Raises:
            RuntimeError: se canary_passou=False.
        """
        if not canary_passou:
            raise RuntimeError(
                'canary_local nao foi validado '
                '(canary_passou=False). Execute canary_local() em '
                'staging primeiro.'
            )
        inicio = time.time()
        self.odoo.write(
            'stock.location', [location_id], {'active': False}
        )
        self._registrar_op(
            tabela_origem='stock.location', registro_id=location_id,
            acao='indispor_local', modelo_odoo='stock.location',
            status='SUCESSO', executado_por=executado_por,
            ajuste_id=ajuste_id, odoo_id=location_id,
            payload={'active': False},
            tempo_ms=int((time.time() - inicio) * 1000),
        )
        logger.info(
            f'indisponibilizar_local {location_id}: active=False'
        )
        return True

    def reverter_local(
        self,
        location_id: int,
        executado_por: str = 'sistema',
        ajuste_id: Optional[int] = None,
    ) -> bool:
        """Reativa location (rollback de `indisponibilizar_local`)."""
        inicio = time.time()
        self.odoo.write(
            'stock.location', [location_id], {'active': True}
        )
        self._registrar_op(
            tabela_origem='stock.location', registro_id=location_id,
            acao='reverter_local', modelo_odoo='stock.location',
            status='SUCESSO', executado_por=executado_por,
            ajuste_id=ajuste_id, odoo_id=location_id,
            payload={'active': True},
            tempo_ms=int((time.time() - inicio) * 1000),
        )
        logger.info(f'reverter_local {location_id}: active=True')
        return True
