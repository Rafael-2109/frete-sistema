"""StockReservaService — atomos para operar reservas no Odoo.

Skill: `operando-reservas-odoo` (C1 fechado, C2-C5 minimo viavel).
Constituicao: `app/odoo/estoque/CLAUDE.md`.

Atomos implementados (uso imediato):
  - cancelar_moves_orfaos(picking_id, move_ids, ml_ids)
        Cirurgia: unlink MLs orfaos + zera product_uom_qty dos moves parent.
        Outras MLs do picking permanecem intactas. Picking nao e cancelado.
  - cancelar_picking_inteiro(picking_id)
        stock.picking.action_cancel — cancela picking + moves filhos.

Atomos previstos (catalogo, sem implementacao ainda — adicionar conforme demanda):
  - unreserve_picking(picking_id) → stock.picking.do_unreserve (libera tudo)
  - unreserve_mo(mo_id, reassign=False) → mrp.production.do_unreserve [+ action_assign]
  - zerar_reserved_residual(quant_ids) → stock.quant.write({reserved_quantity: 0})
  - find_orphan_mls(quant_ids) → identificar MLs apontando para quants zerados

Gotchas-invariante (codificados ou previstos):
  - G024: `reserved_uom_qty` NAO existe em Odoo 16/17 — usar `quantity` (ML) ou
    `qty_done` (legado). Os scripts validados usam `quantity`.
  - G025: Odoo CIEL IT pode ter metodo com nome variando. CONFIRMADO para 17:
    stock.picking.action_cancel ✅, stock.picking.do_unreserve ✅,
    stock.move._action_cancel PRIVADO (nao chamavel via XML-RPC).
  - G026: MO em `to_close/done` tem `picked=True` (consumo realizado) — NAO mexer.
  - G027: `reserved_quantity` interno SEMPRE vem de saida — zerar residual stale
    e seguro APOS unreserve.
  - G028: batch 50 com fallback individual (timeouts XML-RPC).
  - G029: MLs sem picking (de MOs) → unlink direto; com picking → preferir
    do_unreserve (fluxo Odoo). Cirurgia em picking-com-MLs-OK exige unlink direto
    porque do_unreserve afeta TODAS as MLs.

Probes (validados 2026-05-23 contra odoo-17-ee-nacomgoya-prd):
  - stock.move._action_cancel → '<Fault 4: Private methods cannot be called>'
  - stock.move.action_cancel/button_cancel/do_unreserve → NAO EXISTEM
  - Workaround para cancelar move individual: unlink MLs + write(product_uom_qty=0).
"""
import logging
import time
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# Statuses possiveis do atomo
STATUS_OK_CIRURGIA = 'CIRURGIA_OK'
STATUS_OK_CANCEL = 'PICKING_CANCELADO'
STATUS_DRY_RUN = 'DRY_RUN_OK'
STATUS_NOOP = 'NOOP'
STATUS_FALHA_PICKING = 'FALHA_PICKING_NAO_EXISTE'
STATUS_FALHA_STATE = 'FALHA_PICKING_STATE_INVALIDO'
STATUS_FALHA_ODOO = 'FALHA_ODOO'


class StockReservaService:
    """Atomos C1/C2 para operar reservas no Odoo (skill 2.4)."""

    def __init__(self, odoo):
        self.odoo = odoo

    # ------------------------------------------------------------------
    # ATOMO 1 — Cirurgia: cancelar moves orfaos preservando o picking
    # ------------------------------------------------------------------
    def cancelar_moves_orfaos(
        self,
        picking_id: int,
        ml_ids: List[int],
        moves_writes: Dict[int, float],
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Cirurgia: unlink MLs orfaos + ajusta product_uom_qty dos moves parent.

        Args:
            picking_id: ID do picking que contem os moves orfaos (so para validar).
            ml_ids: IDs das stock.move.line a remover (unlink).
            moves_writes: dict {move_id: novo_product_uom_qty}. Usar 0 para zerar
                (move com 1 ML orfa); usar soma das MLs OK restantes para moves
                com multi-ML mistas (1 orfa + N OK).
            dry_run: se True, so calcula. Default True.

        Pre-condicoes:
          - picking existe e nao esta em ['done', 'cancel'].
          - moves_writes.keys() pertencem ao picking_id.
          - ml_ids pertencem a moves do picking_id.

        Pos-condicoes:
          - MLs com id em ml_ids removidas.
          - Moves com id em moves_writes: product_uom_qty := valor especificado.
          - Picking permanece com state inalterado (pode virar partially_available
            no proximo trigger do Odoo).

        Output: {status, picking_id, ml_ids_unlinked, moves_ajustados,
                 picking_state_antes, picking_state_depois, moves_estado, tempo_ms, erro}
        """
        t0 = time.time()
        out: Dict[str, Any] = {
            'picking_id': picking_id,
            'ml_ids_alvo': ml_ids,
            'moves_writes_alvo': moves_writes,
        }

        picking = self.odoo.search_read(
            'stock.picking', [('id', '=', picking_id)],
            ['id', 'name', 'state'], limit=1,
        )
        if not picking:
            out['status'] = STATUS_FALHA_PICKING
            out['erro'] = f'picking_id={picking_id} nao encontrado'
            return out
        picking = picking[0]
        out['picking_name'] = picking['name']
        out['picking_state_antes'] = picking['state']

        if picking['state'] in ('done', 'cancel'):
            out['status'] = STATUS_FALHA_STATE
            out['erro'] = f'picking {picking["name"]} state={picking["state"]} — nao alteravel'
            return out

        if dry_run:
            out['status'] = STATUS_DRY_RUN
            out['acao'] = (
                f'unlink {len(ml_ids)} stock.move.line + '
                f'write product_uom_qty em {len(moves_writes)} stock.move '
                f'(valores: {moves_writes})'
            )
            return out

        try:
            # 1) Unlink MLs orfaos
            if ml_ids:
                self.odoo.execute_kw('stock.move.line', 'unlink', [ml_ids])
                out['ml_ids_unlinked'] = ml_ids
            # 2) Ajustar product_uom_qty dos moves (1 write por valor unico)
            #    Agrupa por valor para minimizar RPC calls.
            ajustes_por_valor: Dict[float, List[int]] = {}
            for mid, novo_qty in moves_writes.items():
                ajustes_por_valor.setdefault(novo_qty, []).append(mid)
            moves_ajustados = []
            for novo_qty, mids in ajustes_por_valor.items():
                self.odoo.execute_kw(
                    'stock.move', 'write', [mids, {'product_uom_qty': novo_qty}],
                )
                moves_ajustados.extend([(mid, novo_qty) for mid in mids])
            out['moves_ajustados'] = moves_ajustados
            # 3) Re-ler estado pos
            picking_pos = self.odoo.read('stock.picking', [picking_id], ['state'])
            out['picking_state_depois'] = picking_pos[0]['state']
            moves_pos = self.odoo.read(
                'stock.move', list(moves_writes.keys()),
                ['id', 'state', 'product_uom_qty', 'quantity'],
            ) if moves_writes else []
            out['moves_estado'] = moves_pos
            out['status'] = STATUS_OK_CIRURGIA
        except Exception as exc:
            out['status'] = STATUS_FALHA_ODOO
            out['erro'] = str(exc)[:500]
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    # ------------------------------------------------------------------
    # ATOMO 2 — Cancelar picking inteiro
    # ------------------------------------------------------------------
    def cancelar_picking_inteiro(
        self,
        picking_id: int,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Cancela picking via stock.picking.action_cancel — cascateia para moves.

        Pre-condicoes:
          - picking existe e nao esta em ['done', 'cancel'].

        Pos-condicoes:
          - picking.state = 'cancel'.
          - stock.move filhas: state = 'cancel' (cascade do Odoo).
          - stock.move.line filhas: removidas ou state=cancel.
          - stock.quant.reserved_quantity das MLs filhas: recalculado pelo Odoo.

        Output: {status, picking_id, picking_state_antes, picking_state_depois,
                 moves_cancelados_count, tempo_ms, erro}
        """
        t0 = time.time()
        out: Dict[str, Any] = {'picking_id': picking_id}

        picking = self.odoo.search_read(
            'stock.picking', [('id', '=', picking_id)],
            ['id', 'name', 'state', 'move_ids'], limit=1,
        )
        if not picking:
            out['status'] = STATUS_FALHA_PICKING
            out['erro'] = f'picking_id={picking_id} nao encontrado'
            return out
        picking = picking[0]
        out['picking_name'] = picking['name']
        out['picking_state_antes'] = picking['state']
        out['moves_count_antes'] = len(picking.get('move_ids', []))

        if picking['state'] in ('done', 'cancel'):
            if picking['state'] == 'cancel':
                out['status'] = STATUS_NOOP
                out['erro'] = f'picking ja estava em state=cancel'
            else:
                out['status'] = STATUS_FALHA_STATE
                out['erro'] = f'picking state={picking["state"]} — nao cancelavel (done)'
            return out

        if dry_run:
            out['status'] = STATUS_DRY_RUN
            out['acao'] = f'stock.picking.action_cancel([{picking_id}])'
            return out

        try:
            self.odoo.execute_kw('stock.picking', 'action_cancel', [[picking_id]])
            picking_pos = self.odoo.read('stock.picking', [picking_id], ['state'])
            out['picking_state_depois'] = picking_pos[0]['state']
            out['status'] = STATUS_OK_CANCEL
        except Exception as exc:
            out['status'] = STATUS_FALHA_ODOO
            out['erro'] = str(exc)[:500]
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    # ------------------------------------------------------------------
    # ATOMOS PREVISTOS (catalogo, sem implementacao ainda)
    # ------------------------------------------------------------------
    def unreserve_picking(self, picking_id: int, dry_run: bool = True) -> Dict[str, Any]:
        """[PREVISTO] stock.picking.do_unreserve — libera todas reservas do picking.
        Implementar quando houver demanda."""
        raise NotImplementedError(
            'unreserve_picking ainda nao implementado. Use cancelar_picking_inteiro '
            'OU cancelar_moves_orfaos. Adicionar implementacao quando precisar.'
        )

    def unreserve_mo(
        self, mo_id: int, reassign: bool = False, dry_run: bool = True,
    ) -> Dict[str, Any]:
        """[PREVISTO] mrp.production.do_unreserve [+ action_assign].
        Implementar quando houver demanda."""
        raise NotImplementedError(
            'unreserve_mo ainda nao implementado. Adicionar quando precisar.'
        )

    def zerar_reserved_residual(
        self, quant_ids: List[int], dry_run: bool = True,
        batch_size: int = 200,
    ) -> Dict[str, Any]:
        """Zera reserved_quantity de quants com residual stale (positivo OU negativo).

        Implementado 2026-05-23 para resolver efeito colateral do unlink de MLs:
        quando se faz unlink de uma stock.move.line apontando para um quant,
        o Odoo recalcula reserved_quantity = reserved_atual - ml.quantity. Se o
        quant ja estava com reserved=0 (apos --resetar-reserva da skill 1), o
        resultado fica NEGATIVO (estado fantasma).

        Pre-condicoes (responsabilidade do caller):
          - Nao deve haver MLs ativas (state in assigned/partially_available) que
            esperem esse reserved_quantity. Verificar antes de chamar.
          - Se houver MLs ativas legitimas, usar unreserve_picking/unreserve_mo
            primeiro.

        Pos-condicoes:
          - quants com id em quant_ids: reserved_quantity=0.

        Output: {status, quant_ids, valores_antes, valores_depois, tempo_ms, erro}
        """
        t0 = time.time()
        out: Dict[str, Any] = {'quant_ids': quant_ids}

        # 1) Snapshot antes
        quants_antes = self.odoo.read(
            'stock.quant', quant_ids, ['id', 'quantity', 'reserved_quantity'],
        )
        out['valores_antes'] = {q['id']: {
            'qty': q['quantity'], 'reserved': q['reserved_quantity'],
        } for q in quants_antes}

        if dry_run:
            out['status'] = STATUS_DRY_RUN
            out['acao'] = (
                f'write reserved_quantity=0 em {len(quant_ids)} quants '
                f'(batch={batch_size})'
            )
            return out

        try:
            zerados = 0
            for i in range(0, len(quant_ids), batch_size):
                batch = quant_ids[i:i + batch_size]
                self.odoo.execute_kw(
                    'stock.quant', 'write', [batch, {'reserved_quantity': 0}],
                )
                zerados += len(batch)
            # Snapshot depois
            quants_depois = self.odoo.read(
                'stock.quant', quant_ids, ['id', 'quantity', 'reserved_quantity'],
            )
            out['valores_depois'] = {q['id']: {
                'qty': q['quantity'], 'reserved': q['reserved_quantity'],
            } for q in quants_depois}
            out['quants_processados'] = zerados
            out['status'] = STATUS_OK_CIRURGIA  # reuso do status
        except Exception as exc:
            out['status'] = STATUS_FALHA_ODOO
            out['erro'] = str(exc)[:500]
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out
