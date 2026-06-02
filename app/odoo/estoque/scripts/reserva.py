# etapa: C1-C2
# doc-dono: app/odoo/estoque/CLAUDE.md §6
"""StockReservaService — atomos para operar reservas no Odoo.

Skill: `operando-reservas-odoo` (C1 fechado, C2-C5 minimo viavel).
Constituicao: `app/odoo/estoque/CLAUDE.md`.

Atomos implementados (uso imediato):
  - cancelar_moves_orfaos(picking_id, move_ids, ml_ids)
        Cirurgia: unlink MLs orfaos + zera product_uom_qty dos moves parent.
        Outras MLs do picking permanecem intactas. Picking nao e cancelado.
  - cancelar_picking_inteiro(picking_id)
        stock.picking.action_cancel — cancela picking + moves filhos.
  - unreserve_picking(picking_id) — NOVO 2026-05-24 v7
        stock.picking.do_unreserve — libera reservas SEM cancelar picking.
        Picking volta a confirmed/waiting (MLs apagadas; reserved_quantity dos
        quants recalculado). Para fluxo 2.6 caminho C (desreservar mantendo
        picking). AVISO operacional: picking pode TRAVAR em assigned se Odoo
        nao re-confirmar (usuario 2026-05-24 §2).
  - find_orphan_mls(quant_ids) — NOVO 2026-05-24 v7
        Identifica MLs apontando para quants com qty=0 (orfas pos-cirurgia
        sem residual cleanup). Usa cross-ref via tupla (G030) sob a Skill 9.
  - zerar_reserved_residual(quant_ids)
        Zera reserved_quantity de quants com residual stale (positivo OU
        negativo). Caller responsavel por garantir sem MLs ativas.

Atomos previstos (catalogo, sem implementacao ainda — adicionar conforme demanda):
  - unreserve_mo(mo_id, reassign=False) → mrp.production.do_unreserve [+ action_assign]

Gotchas-invariante (codificados ou previstos):
  - G024: `reserved_uom_qty` NAO existe em Odoo 16/17 — usar `quantity` (ML) ou
    `qty_done` (legado). Os scripts validados usam `quantity`.
  - G025: Odoo CIEL IT pode ter metodo com nome variando. CONFIRMADO para 17:
    stock.picking.action_cancel ✅, stock.picking.do_unreserve ✅,
    stock.picking._action_unreserve NAO EXISTE,
    stock.move._action_cancel PRIVADO (nao chamavel via XML-RPC).
  - G026: MO em `to_close/done` tem `picked=True` (consumo realizado) — NAO mexer.
  - G027: `reserved_quantity` interno SEMPRE vem de saida — zerar residual stale
    e seguro APOS unreserve.
  - G028: batch 50 com fallback individual (timeouts XML-RPC).
  - G029: MLs sem picking (de MOs) → unlink direto; com picking → preferir
    do_unreserve (fluxo Odoo). Cirurgia em picking-com-MLs-OK exige unlink direto
    porque do_unreserve afeta TODAS as MLs.
  - G030: stock.move.line.quant_id e' computed `store: False` — NAO usar como
    filtro. Cross-ref ML→quant via tupla (product, lot, location, company).
    Detalhes em `docs/inventario-2026-05/02-gotchas/G030-quant-id-em-stock-move-line-eh-computed.md`.
  - G_UNRESERVE_TRAVA: do_unreserve pode deixar picking em state=assigned
    mesmo apos MLs serem apagadas (aviso usuario 2026-05-24 §2). Caller
    deve verificar state pos e considerar action_confirm / action_assign
    se quiser re-reservar. Para liberar saldo sem manter picking: usar
    cancelar_picking_inteiro (caminho A do fluxo 2.6).

Probes (validados 2026-05-23 contra odoo-17-ee-nacomgoya-prd):
  - stock.move._action_cancel → '<Fault 4: Private methods cannot be called>'
  - stock.move.action_cancel/button_cancel/do_unreserve → NAO EXISTEM
  - Workaround para cancelar move individual: unlink MLs + write(product_uom_qty=0).
Probes (validados 2026-05-24 v7):
  - stock.picking.do_unreserve em state=cancel → retorna None (NOOP seguro).
  - stock.picking._action_unreserve → NAO EXISTE (Fault method does not exist).
"""
import logging
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Statuses possiveis do atomo
STATUS_OK_CIRURGIA = 'CIRURGIA_OK'
STATUS_OK_CANCEL = 'PICKING_CANCELADO'
STATUS_OK_UNRESERVE = 'PICKING_UNRESERVED'
STATUS_OK_ZERAR_RESIDUAL = 'ZERAR_RESIDUAL_OK'  # CR1-M2 v7-fix
STATUS_DRY_RUN = 'DRY_RUN_OK'
STATUS_NOOP = 'NOOP'
STATUS_FALHA_PICKING = 'FALHA_PICKING_NAO_EXISTE'
STATUS_FALHA_STATE = 'FALHA_PICKING_STATE_INVALIDO'
STATUS_FALHA_ODOO = 'FALHA_ODOO'
STATUS_OK_FIND_ORPHAN = 'ORPHAN_MLS_LISTED'


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
    # ATOMO 4 — Unreserve picking (NOVO 2026-05-24 v7)
    # ------------------------------------------------------------------
    def unreserve_picking(
        self,
        picking_id: int,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Libera reservas do picking SEM cancelar (do_unreserve nativo).

        Wrapper sobre `stock.picking.do_unreserve` (XML-RPC publico,
        validado AO VIVO 2026-05-24 v7). Diferenca essencial vs
        cancelar_picking_inteiro:
          - cancelar_picking: picking vira CANCEL, MLs apagadas, moves cancel
          - unreserve_picking: picking volta para CONFIRMED/WAITING/AVAILABLE,
            MLs apagadas mas moves ATIVOS (podem ser re-reservados depois)

        Caminho C do fluxo 2.6 (tratar reserva ativa pre-transferencia).

        Pre-condicoes:
          - picking existe e state in (assigned, partially_available,
            confirmed, waiting) — NAO done/cancel/draft.

        Pos-condicoes:
          - MLs do picking: APAGADAS (todas as quantity_done viram 0).
          - reserved_quantity dos quants relacionados: RECALCULADO pelo Odoo.
          - picking.state: depende do Odoo (geralmente confirmed/waiting/
            partially_available). AVISO: pode TRAVAR em assigned se Odoo
            re-reservar automaticamente (depende do trigger e disponibilidade).

        Args:
            picking_id: ID do picking.
            dry_run: se True, so calcula e mostra plano. Default True.

        Output: {status, picking_id, picking_name, picking_state_antes,
                 picking_state_depois, n_mls_antes, n_mls_depois,
                 tempo_ms, erro}
        """
        t0 = time.time()
        out: Dict[str, Any] = {'picking_id': picking_id}

        picking = self.odoo.search_read(
            'stock.picking', [('id', '=', picking_id)],
            ['id', 'name', 'state', 'move_line_ids'], limit=1,
        )
        if not picking:
            out['status'] = STATUS_FALHA_PICKING
            out['erro'] = f'picking_id={picking_id} nao encontrado'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out
        picking = picking[0]
        out['picking_name'] = picking['name']
        out['picking_state_antes'] = picking['state']
        out['n_mls_antes'] = len(picking.get('move_line_ids', []))

        # Pre-cond: NAO done/cancel/draft (CR1-H1 v7-fix: adicionado 'draft')
        if picking['state'] in ('done', 'cancel', 'draft'):
            out['status'] = STATUS_FALHA_STATE
            out['erro'] = (
                f'picking {picking["name"]} state={picking["state"]} — '
                f'do_unreserve so opera em assigned/partially_available/'
                f'confirmed/waiting'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Se nao tem MLs reservadas, NOOP
        if out['n_mls_antes'] == 0:
            out['status'] = STATUS_NOOP
            out['erro'] = (
                f'picking {picking["name"]} state={picking["state"]} '
                f'ja sem MLs reservadas — NOOP'
            )
            out['picking_state_depois'] = picking['state']
            out['n_mls_depois'] = 0
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if dry_run:
            out['status'] = STATUS_DRY_RUN
            out['acao'] = (
                f'stock.picking.do_unreserve([{picking_id}]) — '
                f'apaga {out["n_mls_antes"]} MLs, picking volta a '
                f'confirmed/waiting; reserved_quantity dos quants recalculado'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        try:
            self.odoo.execute_kw(
                'stock.picking', 'do_unreserve', [[picking_id]],
            )
            picking_pos = self.odoo.search_read(
                'stock.picking', [('id', '=', picking_id)],
                ['state', 'move_line_ids'], limit=1,
            )
            out['picking_state_depois'] = (
                picking_pos[0]['state'] if picking_pos else '?'
            )
            out['n_mls_depois'] = (
                len(picking_pos[0].get('move_line_ids', [])) if picking_pos else -1
            )
            out['status'] = STATUS_OK_UNRESERVE
            # Aviso explicito se state pos == assigned (G_UNRESERVE_TRAVA)
            if out['picking_state_depois'] == 'assigned':
                out['aviso'] = (
                    'picking continua em state=assigned pos do_unreserve '
                    '(G_UNRESERVE_TRAVA). Odoo pode ter re-reservado '
                    'automaticamente. Verificar se MLs foram realmente apagadas.'
                )
        except Exception as exc:
            out['status'] = STATUS_FALHA_ODOO
            out['erro'] = str(exc)[:500]
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    # ------------------------------------------------------------------
    # ATOMO 5 — Find orphan MLs (NOVO 2026-05-24 v7)
    # ------------------------------------------------------------------
    def find_orphan_mls(
        self,
        quant_ids: List[int],
        states: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Lista MLs orfaos: apontando para quants com qty=0 (sem cleanup residual).

        Diferenca vs Skill 9 listar_move_lines_por_quant:
          - Skill 9: lista TODAS as MLs reservando os quants (ativas).
          - find_orphan_mls: filtra apenas as ORFAS (quant qty=0 mas ML
            ainda apontando para ele).

        Use case: pos-cirurgia (cancelar_moves_orfaos da Skill 2.4) ou
        pos-ajuste-quant-para-zero (Skill 1) pode deixar MLs/quants em
        estado inconsistente — quant zerado mas ML ainda referenciando-o.

        Reaproveita Skill 9 internamente (cross-ref via tupla G030).

        Args:
            quant_ids: IDs de quants a verificar.
            states: states das MLs a considerar. Default = ['assigned',
                'partially_available'] (MLs ativas).

        Pre-condicoes (READ-only):
          - quant_ids nao-vazio.

        Pos-condicoes (READ-only): sem mutacao Odoo.

        Output: {status, total_orfaos, mls_orfas, quants_zerados_com_mls,
                 quants_com_saldo, tempo_ms}
        """
        t0 = time.time()
        out: Dict[str, Any] = {'quant_ids': quant_ids}

        if not quant_ids:
            out['status'] = STATUS_OK_FIND_ORPHAN
            out['total_orfaos'] = 0
            out['mls_orfas'] = []
            out['quants_zerados_com_mls'] = []
            out['quants_com_saldo'] = []
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # 1) Buscar estado atual dos quants
        quants = self.odoo.read(
            'stock.quant', list(quant_ids),
            ['id', 'product_id', 'lot_id', 'location_id', 'quantity',
             'reserved_quantity', 'company_id'],
        )
        quant_qty_map: Dict[int, float] = {
            q['id']: q.get('quantity') or 0 for q in quants
        }

        # 2) Buscar MLs via Skill 9 (cross-ref via tupla G030)
        # Import lazy para evitar circular
        from app.odoo.estoque.scripts.consulta_quant import StockQuantQueryService
        query_svc = StockQuantQueryService(odoo=self.odoo)
        mls_res = query_svc.listar_move_lines_por_quant(
            quant_ids=quant_ids, states=states,
            incluir_picking=True, incluir_move=True,
        )

        # 3) Classificar: ML orfa = quant qty=0 (TOL 1e-4)
        TOL = 0.0001
        mls_orfas = []
        quants_zerados_com_mls = set()
        for ml in mls_res['mls']:
            quant_id = ml.get('quant_id')
            if quant_id is None:
                continue
            qty_quant = quant_qty_map.get(quant_id, 0)
            if abs(qty_quant) < TOL:
                mls_orfas.append(ml)
                quants_zerados_com_mls.add(quant_id)

        # Quants com saldo (NAO orfaos — MLs sao legitimas)
        quants_com_saldo = [
            q['id'] for q in quants
            if abs(q.get('quantity') or 0) >= TOL
        ]

        out['status'] = STATUS_OK_FIND_ORPHAN
        out['total_orfaos'] = len(mls_orfas)
        out['mls_orfas'] = mls_orfas
        out['quants_zerados_com_mls'] = sorted(quants_zerados_com_mls)
        out['quants_com_saldo'] = quants_com_saldo
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    # ------------------------------------------------------------------
    # ATOMOS PREVISTOS (catalogo, sem implementacao ainda)
    # ------------------------------------------------------------------
    def unreserve_mo(
        self, mo_id: int, reassign: bool = False, dry_run: bool = True,
    ) -> Dict[str, Any]:
        """[PREVISTO] mrp.production.do_unreserve [+ action_assign].
        Implementar quando houver demanda."""
        _ = (mo_id, reassign, dry_run)  # silencia pyright
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
            out['status'] = STATUS_OK_ZERAR_RESIDUAL  # CR1-M2 v7-fix (era CIRURGIA_OK)
        except Exception as exc:
            out['status'] = STATUS_FALHA_ODOO
            out['erro'] = str(exc)[:500]
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out
