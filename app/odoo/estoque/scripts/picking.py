# etapa: C2
# doc-dono: app/odoo/estoque/CLAUDE.md §6
"""StockPickingService — gerencia stock.picking de transferencia.

Generaliza padroes em:
- app/pallet/services/emissao_nf_pallet.py:115-177 (criar_picking -> validar_picking)
- app/recebimento/services/recebimento_lf_odoo_service.py:2273-2611 (saida +
  liberar_faturamento + aguardar_invoice do robo CIEL IT)

Padrao: create -> action_confirm -> action_assign -> preencher qty_done ->
button_validate -> action_liberar_faturamento -> aguardar invoice do robo CIEL IT.

Spec: docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md §6.2

v15a (2026-05-25): adicionados 3 atomos inter-company para reuso na Skill 8
`faturando-odoo` (C6.5 — DECISAO 10.6 PLANEJAMENTO_SKILL8_FATURANDO):
  - `criar_picking_inter_company` (F5a — codifica fix D-OPS-3 tracking='none')
  - `validar_picking_inter_company` (F5b — fluxo F5b completo + G018 peso/volumes)
  - `criar_picking_entrada_destino_manual` (ETAPA F — G023 company_id forcado +
    idempotencia via origin)
"""
import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.odoo.constants import ids_diversos
from app.odoo.services.stock_lot_service import StockLotService
from app.odoo.utils.connection import get_odoo_connection, is_cannot_marshal_none

logger = logging.getLogger(__name__)


class StockPickingService:
    """Gerencia stock.picking no Odoo de forma reutilizavel."""

    def __init__(self, odoo=None):
        self.odoo = odoo or get_odoo_connection()

    # Defaults inter-company NACOM (G004 / aprendizado caso piloto 2026-05-18):
    # picking outgoing exige 'incoterm' + 'carrier_id' para action_liberar_faturamento
    # disparar. Sem isso: 'Voce deve informar o Tipo de Frete para liberar
    # o faturamento.'.
    INCOTERM_CIF = ids_diversos.INCOTERM_CIF      # central: app/odoo/constants/ids_diversos.py
    CARRIER_NACOM = ids_diversos.CARRIER_NACOM    # delivery.carrier NACOM GOYA

    def criar_transferencia(
        self,
        company_origem_id: int,
        company_destino_id: int,
        location_origem_id: int,
        location_destino_id: int,
        linhas: List[Dict[str, Any]],
        picking_type_id: int,
        partner_id: Optional[int] = None,
        scheduled_date: Optional[str] = None,
        origin: Optional[str] = None,
        incoterm_id: Optional[int] = INCOTERM_CIF,
        carrier_id: Optional[int] = CARRIER_NACOM,
    ) -> int:
        """Cria picking de transferencia (saida).

        Args:
            company_origem_id: company emissora.
            company_destino_id: company destino (documental, nao vai no payload
                — apenas log).
            location_origem_id: stock.location origem.
            location_destino_id: stock.location destino.
            linhas: [{'product_id': int, 'quantity': float,
                      'lot_name': str|None, 'lot_id': int|None,
                      'uom_id': int|None, 'name': str|None}, ...]
            picking_type_id: stock.picking.type id (saida da company origem).
            partner_id: parceiro destino (opcional, mas obrigatorio para
                operacoes fiscais).
            scheduled_date: 'YYYY-MM-DD HH:MM:SS' (Odoo espera UTC).
            origin: campo origin do picking (rastreabilidade).
            incoterm_id: campo `incoterm` no stock.picking ("Tipo de Frete").
                Default `INCOTERM_CIF` (id 6 — CIF). G004: NACOM exige
                preenchido para `action_liberar_faturamento`. Passe None
                para nao setar.
            carrier_id: delivery.carrier ("Carrier"). Default `CARRIER_NACOM`
                (996 — NACOM GOYA transportadora propria). Passe None
                para nao setar.

        Returns:
            picking_id (int).

        Raises:
            ValueError: se linhas vazias.
        """
        if not linhas:
            raise ValueError('linhas vazias — picking exige ao menos 1 produto')

        move_ids = []
        for linha in linhas:
            product_id = linha['product_id']
            qty = float(linha['quantity'])
            move_payload = {
                'name': linha.get('name', f'Transf produto {product_id}'),
                'product_id': product_id,
                'product_uom_qty': qty,
                'location_id': location_origem_id,
                'location_dest_id': location_destino_id,
                'company_id': company_origem_id,
            }
            if linha.get('uom_id'):
                move_payload['product_uom'] = linha['uom_id']
            move_ids.append((0, 0, move_payload))

        picking_payload = {
            'location_id': location_origem_id,
            'location_dest_id': location_destino_id,
            'picking_type_id': picking_type_id,
            'company_id': company_origem_id,
            'move_ids': move_ids,
        }
        if partner_id:
            picking_payload['partner_id'] = partner_id
        if scheduled_date:
            picking_payload['scheduled_date'] = scheduled_date
        if origin:
            picking_payload['origin'] = origin
        if incoterm_id is not None:
            picking_payload['incoterm'] = incoterm_id
        if carrier_id is not None:
            picking_payload['carrier_id'] = carrier_id

        picking_id = self.odoo.create('stock.picking', picking_payload)
        logger.info(
            f'Picking criado: id={picking_id} origem_company={company_origem_id} '
            f'destino_company={company_destino_id} linhas={len(linhas)} '
            f'incoterm={incoterm_id} carrier={carrier_id}'
        )
        return picking_id

    def confirmar_e_reservar(self, picking_id: int) -> None:
        """Confirma o picking e tenta reservar estoque.

        Sequencia padrao:
            1. action_confirm (draft -> confirmed)
            2. action_assign (reserva estoque + cria stock.move.line)

        G023 nota: consolidar_move_lines NAO eh chamado aqui (cache
        stale logo apos action_assign). Eh chamado em validar() — la
        os campos computed ja' foram refrescados pelos writes de
        preencher_qty_done + ajustar_qty_done_pelo_disponivel.

        Reuso: recebimento_lf_odoo_service.py:2317-2334.
        """
        self.odoo.execute_kw('stock.picking', 'action_confirm', [[picking_id]])
        self.odoo.execute_kw('stock.picking', 'action_assign', [[picking_id]])
        logger.info(f'Picking {picking_id}: confirmado + reservado')

    def consolidar_move_lines(
        self, picking_id: int,
        linhas_esperadas: Optional[List[Dict[str, Any]]] = None,
    ) -> int:
        """G023: corrige over-reservation apos action_assign forcando os
        lotes/qtds EXATOS solicitados pelo caller.

        Problema: quando ETAPA A renomeia lote (action_apply_inventory),
        reservas no lote velho podem permanecer orfas. O action_assign
        subsequente em ETAPA B reserva tanto no lote velho QUANTO no lote
        novo, causando over-reservation (caso real: 2x a 459x).

        Solucao: ao inves de FIFO automatico, usar `linhas_esperadas`
        (passadas pelo caller, ja' com `lot_name` + `quantity` exata
        derivada dos AjusteEstoqueInventario). Para cada (produto, lote)
        esperado: encontrar move_line correspondente e setar
        quantity+qty_done exatos; ZERAR todas as outras move_lines do
        mesmo produto (incluindo as auto-criadas pelo action_assign em
        lotes errados).

        Args:
            picking_id: stock.picking.id
            linhas_esperadas: [{'product_id': int, 'lot_name': str,
                'quantity': float, ...}, ...]. Mesma estrutura passada
                ao `preencher_qty_done`. Se None, NAO faz nada (no-op).

        Returns:
            int — produtos cuja alocacao foi ajustada
        """
        if not linhas_esperadas:
            return 0

        # Agrupar linhas esperadas por (product_id, lot_name)
        # — cada chave -> sum(quantity) (caso mesmo produto+lote repita)
        esperado: Dict[Tuple[int, str], float] = defaultdict(float)
        produtos_esperados: set = set()
        for ln in linhas_esperadas:
            pid = ln['product_id']
            lot_name = (ln.get('lot_name') or '').strip()
            qty = float(ln.get('quantity') or 0)
            if qty <= 0:
                continue
            esperado[(pid, lot_name)] += qty
            produtos_esperados.add(pid)

        if not esperado:
            return 0

        # Ler todas as move_lines do picking, agrupar por (product_id, lot_name)
        mls = self.odoo.search_read(
            'stock.move.line',
            [['picking_id', '=', picking_id]],
            ['id', 'product_id', 'quantity', 'qty_done', 'lot_id', 'lot_name'],
        )

        # Para cada move_line: identificar product_id e lot_name efetivo
        mls_por_chave: Dict[Tuple[int, str], List[Dict]] = defaultdict(list)
        mls_por_produto: Dict[int, List[Dict]] = defaultdict(list)
        for ml in mls:
            pid = ml['product_id'][0] if ml.get('product_id') else None
            if not pid:
                continue
            lot_name = ''
            if ml.get('lot_id'):
                lot_name = ml['lot_id'][1] or ''
            elif ml.get('lot_name'):
                lot_name = ml['lot_name'] or ''
            lot_name = lot_name.strip()
            mls_por_chave[(pid, lot_name)].append(ml)
            mls_por_produto[pid].append(ml)

        ajustes = 0
        mls_processadas: set = set()

        # Etapa 1: para cada linha esperada, encontrar move_line do mesmo
        # (produto, lote) e setar quantity+qty_done = qty esperada
        for (pid, lot_name), qty_esperada in esperado.items():
            mls_match = mls_por_chave.get((pid, lot_name), [])
            if not mls_match:
                logger.warning(
                    f'  G023 picking {picking_id}: produto={pid} '
                    f'lote={lot_name!r} esperado={qty_esperada:.4f} '
                    f'mas NAO encontrou move_line correspondente. '
                    f'(action_assign nao reservou nesse lote)'
                )
                continue
            ml = mls_match[0]
            mls_processadas.add(ml['id'])
            old_qty = float(ml.get('quantity') or 0)
            if abs(old_qty - qty_esperada) > 0.0001:
                self.odoo.write(
                    'stock.move.line', [ml['id']],
                    {'quantity': qty_esperada, 'qty_done': qty_esperada},
                )
                logger.debug(
                    f'  G023 picking {picking_id}: ml {ml["id"]} '
                    f'prod={pid} lote={lot_name!r} '
                    f'qty {old_qty:.4f} -> {qty_esperada:.4f}'
                )
            # Lidar com duplicatas (mais de uma ml com mesma chave)
            for ml_dup in mls_match[1:]:
                mls_processadas.add(ml_dup['id'])
                if float(ml_dup.get('quantity') or 0) > 0 or \
                   float(ml_dup.get('qty_done') or 0) > 0:
                    self.odoo.write(
                        'stock.move.line', [ml_dup['id']],
                        {'quantity': 0, 'qty_done': 0},
                    )
                    logger.debug(
                        f'  G023 picking {picking_id}: ml duplicada '
                        f'{ml_dup["id"]} zerada (prod={pid} lote={lot_name!r})'
                    )

        # Etapa 2: para cada produto esperado, zerar TODAS as move_lines
        # que nao foram processadas (= reservas em lotes "errados" criados
        # pelo action_assign)
        for pid in produtos_esperados:
            for ml in mls_por_produto.get(pid, []):
                if ml['id'] in mls_processadas:
                    continue
                old_qty = float(ml.get('quantity') or 0)
                if old_qty > 0 or float(ml.get('qty_done') or 0) > 0:
                    lot_efetivo = ml.get('lot_id') or ml.get('lot_name') or '(sem)'
                    self.odoo.write(
                        'stock.move.line', [ml['id']],
                        {'quantity': 0, 'qty_done': 0},
                    )
                    logger.warning(
                        f'  G023 picking {picking_id}: ml {ml["id"]} '
                        f'prod={pid} lote={lot_efetivo} '
                        f'qty {old_qty:.4f} -> 0 (lote nao esperado)'
                    )

        # Contar produtos cuja soma final difere de soma original
        for pid in produtos_esperados:
            soma_old = sum(
                float(ml.get('quantity') or 0)
                for ml in mls_por_produto.get(pid, [])
            )
            soma_esperada = sum(
                qty for (p, _), qty in esperado.items() if p == pid
            )
            if abs(soma_old - soma_esperada) > 0.0001:
                ajustes += 1
                logger.warning(
                    f'  G023 picking {picking_id} produto {pid}: '
                    f'sum(ml.quantity) {soma_old:.4f} -> {soma_esperada:.4f}'
                )

        return ajustes

    def preencher_qty_done(
        self, picking_id: int, linhas: List[Dict[str, Any]]
    ) -> None:
        """Preenche qty_done nas move_lines do picking.

        Match por product_id (primeira move_line por produto). Cada linha
        pode informar lot_id OU lot_name (mutuamente exclusivos — lot_id
        prevalece se ambos vierem).

        Args:
            picking_id: stock.picking.id.
            linhas: [{'product_id': int, 'quantity': float,
                      'lot_id': int|None, 'lot_name': str|None}, ...]

        Raises:
            RuntimeError: se algum product_id da entrada nao tem move_line
                no picking (estoque insuficiente ou produto errado).
        """
        move_lines = self.odoo.search_read(
            'stock.move.line',
            [['picking_id', '=', picking_id]],
            ['id', 'product_id'],
        )

        produto_para_line: Dict[int, int] = {}
        for ml in move_lines:
            pid = ml['product_id'][0] if ml.get('product_id') else None
            if pid and pid not in produto_para_line:
                produto_para_line[pid] = ml['id']

        for linha in linhas:
            pid = linha['product_id']
            if pid not in produto_para_line:
                raise RuntimeError(
                    f'product_id={pid} sem move_line no picking={picking_id}'
                )
            line_id = produto_para_line[pid]
            update: Dict[str, Any] = {'qty_done': float(linha['quantity'])}
            if linha.get('lot_id'):
                update['lot_id'] = linha['lot_id']
            elif linha.get('lot_name'):
                update['lot_name'] = linha['lot_name']
            self.odoo.write('stock.move.line', [line_id], update)

    def ajustar_qty_done_pelo_disponivel(self, picking_id: int) -> Dict[str, Any]:
        """Ajusta product_uom_qty (demand) = sum(qty_done) das move_lines.

        Estrategia segura: NUNCA infla qty_done alem do disponivel no
        lote. Em vez disso, REDUZ a demanda da move para igualar ao que
        action_assign efetivamente reservou nos lotes. Isso permite
        button_validate sem backorder e sem saldo negativo.

        A diferenca (demand original - qty_done) e' reportada para o
        caller decidir gerar ajuste complementar.

        Returns:
            dict com:
                ajustadas: int — moves cuja demand foi reduzida
                pendencias: list — [{move_id, product_id, demand_orig, qty_done, falta}]
        """
        moves = self.odoo.search_read(
            'stock.move', [['picking_id', '=', picking_id]],
            ['id', 'product_id', 'product_uom_qty', 'state', 'move_line_ids'],
        )
        ajustadas = 0
        pendencias = []
        for mv in moves:
            if mv.get('state') == 'cancel':
                continue
            demand = float(mv.get('product_uom_qty') or 0)
            ml_ids = mv.get('move_line_ids') or []
            if not ml_ids or demand <= 0:
                continue
            mls = self.odoo.read(
                'stock.move.line', ml_ids,
                ['id', 'qty_done', 'quantity'],
            )
            soma_qty_done = sum(float(ml.get('qty_done') or 0) for ml in mls)
            # Caso 1: qty_done bate demanda — nada a fazer
            if abs(soma_qty_done - demand) < 0.001:
                continue
            # Caso 2: qty_done < demand — REDUZIR demand (nao inflar qty_done)
            if soma_qty_done < demand:
                falta = demand - soma_qty_done
                pendencias.append({
                    'move_id': mv['id'],
                    'product_id': mv['product_id'][0] if mv.get('product_id') else None,
                    'product_name': mv['product_id'][1] if mv.get('product_id') else None,
                    'demand_orig': demand,
                    'qty_done': soma_qty_done,
                    'falta': falta,
                })
                # Reduzir a demanda do move para igualar ao que esta disponivel
                self.odoo.write(
                    'stock.move', [mv['id']],
                    {'product_uom_qty': soma_qty_done},
                )
                ajustadas += 1
                logger.warning(
                    f"Picking {picking_id} move {mv['id']}: demand "
                    f'{demand} reduzida para {soma_qty_done} '
                    f'(falta {falta}). Gerar ajuste complementar.'
                )
            # Caso 3: qty_done > demand (raro) — manter qty_done
            else:
                self.odoo.write(
                    'stock.move', [mv['id']],
                    {'product_uom_qty': soma_qty_done},
                )
                ajustadas += 1
        return {'ajustadas': ajustadas, 'pendencias': pendencias}

    def validar(
        self, picking_id: int,
        linhas_esperadas: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """button_validate com context skip_backorder.

        G019 FIX: SEMPRE checa state=done apos chamada. Antes engolia
        'cannot marshal None' como sucesso, mas Odoo pode retornar wizard
        de estoque negativo (ou outro) que deixa picking em assigned —
        false-positive cascateia em G020 e robo CIEL IT nunca cria invoice.

        Context `skip_backorder=True` + `picking_ids_not_to_backorder`
        evita o wizard de backorder (que deixaria o picking em 'assigned'
        ao inves de 'done' quando ha diferenca entre qty_done e demand).
        Padrao usado em recebimento_lf_odoo_service.py:1548-1558.

        Raises:
            RuntimeError: picking apos button_validate NAO ficou em state=done
                (provavelmente estoque negativo, wizard pendente, etc).
            Exception: qualquer outra exceção (ex.: 'Quality checks
                pending') eh propagada — o caller decide retry ou abort.
        """
        # G023: consolidar move_lines ANTES de button_validate.
        # Usa `linhas_esperadas` (lote_origem + qtd_ajuste exatos vindos
        # dos AjusteEstoqueInventario) para forcar move_lines a refletirem
        # EXATAMENTE o que foi planejado, descartando reservas em lotes
        # nao previstos (criadas por action_assign apos renomeacao de lote).
        if linhas_esperadas:
            try:
                ajustes_g023 = self.consolidar_move_lines(
                    picking_id, linhas_esperadas=linhas_esperadas,
                )
                if ajustes_g023 > 0:
                    logger.warning(
                        f'Picking {picking_id}: G023 corrigiu over-reservation '
                        f'em {ajustes_g023} produtos antes de button_validate'
                    )
            except Exception as e:
                logger.warning(
                    f'Picking {picking_id}: G023 consolidar_move_lines falhou '
                    f'(nao bloqueante): {e}'
                )

        marshal_none = False
        try:
            self.odoo.execute_kw(
                'stock.picking', 'button_validate', [[picking_id]],
                {'context': {
                    'skip_backorder': True,
                    'picking_ids_not_to_backorder': [picking_id],
                }},
            )
        except Exception as e:
            if is_cannot_marshal_none(e):  # 'cannot marshal None' = sucesso (O6) — ver odoo/GOTCHAS.md
                marshal_none = True
            else:
                raise

        # G019 FIX: SEMPRE verificar state real apos button_validate
        p = self.odoo.read('stock.picking', [picking_id], ['state'])
        state = p[0]['state'] if p else None
        if state == 'done':
            if marshal_none:
                logger.info(
                    f'Picking {picking_id}: button_validate retornou None '
                    '(state=done verificado — sucesso)'
                )
            return True
        # state != 'done' — false-positive G019
        raise RuntimeError(
            f'Picking {picking_id} state={state!r} apos button_validate '
            f'(esperado "done"). Provavelmente: estoque negativo, wizard '
            f'pendente, ou outro impedimento. '
            f'{"button_validate retornou marshal None mas state nao=done." if marshal_none else ""}'
        )

    def cancelar(self, picking_id: int, motivo: str = '') -> bool:
        """Cancela picking via action_cancel. Motivo apenas para log."""
        self.odoo.execute_kw('stock.picking', 'action_cancel', [[picking_id]])
        logger.info(
            f'Picking {picking_id} cancelado'
            + (f' (motivo: {motivo})' if motivo else '')
        )
        return True

    def devolver(self, picking_id: int) -> int:
        """Cria stock.return.picking + valida — restaura estoque.

        Wrapper sobre o wizard `stock.return.picking` do Odoo: cria o
        wizard, popula `product_return_moves` via `default_get` (write
        vazio com contexto), executa `create_returns`, seta `qty_done`
        nas move_lines do novo picking e valida.

        Idempotencia: se ja existe picking VIVO com `origin ilike "Devolução
        de {name}"`, retorna esse id sem criar duplicado. Devolucoes em
        state=cancel sao IGNORADAS (G-AUDIT-3/N23) — move qty=0 nao restaura
        saldo; se so existem canceladas, cria uma nova.

        G019 pattern: re-le state do novo picking apos button_validate;
        raise se != 'done'.

        Padrao derivado de fat_lf_cleanup.reverter_picking (PROD
        2026-05-20).

        Args:
            picking_id: stock.picking.id em state=done.

        Returns:
            picking_id da DEVOLUCAO (novo stock.picking).

        Raises:
            RuntimeError: picking nao existe, nao esta em state=done,
                ou devolucao apos button_validate nao ficou em state=done.
        """
        pk = self.odoo.read('stock.picking', [picking_id], ['name', 'state'])
        if not pk:
            raise RuntimeError(f'Picking {picking_id} nao existe no Odoo')
        if pk[0]['state'] != 'done':
            raise RuntimeError(
                f'Picking {picking_id} state={pk[0]["state"]!r} '
                '(esperado "done" para devolver)'
            )

        # Idempotencia: ja existe devolucao?
        # G-AUDIT-3 (N23): NUNCA reaproveitar devolucao em state=cancel — o
        # move da devolucao cancelada tem qty=0 e NAO restaura saldo. Estados
        # validos para reaproveitar: draft/confirmed/assigned/done. Se TODAS
        # as devolucoes existentes (por origin) sao cancel, prossegue para
        # criar uma NOVA funcional; se ha mistura, prefere a viva. Espelha o
        # fix de `criar_picking_inter_company` (mesma licao atemporal:
        # idempotencia por chave externa SEMPRE filtra registro morto).
        existentes = self.odoo.search_read(
            'stock.picking',
            [['origin', 'ilike', f'Devolução de {pk[0]["name"]}']],
            ['id', 'state'],
        )
        vivas = [p for p in existentes if (p.get('state') or '') != 'cancel']
        if vivas:
            canceladas = [
                p for p in existentes if (p.get('state') or '') == 'cancel'
            ]
            logger.info(
                f'Picking {picking_id} ({pk[0]["name"]}): devolucao ja '
                f'existe (id={vivas[0]["id"]}, state={vivas[0].get("state")!r}). '
                'Retornando sem criar.'
                + (
                    f' (G-AUDIT-3: ignorando {len(canceladas)} devolucao(oes) '
                    f'cancelada(s) ids={[p["id"] for p in canceladas]}.)'
                    if canceladas else ''
                )
            )
            return vivas[0]['id']
        # G-AUDIT-3: nenhuma devolucao viva (todas cancel ou inexistente) —
        # prossegue para criar uma NOVA.

        # Criar wizard stock.return.picking
        ctx = {
            'active_id': picking_id,
            'active_model': 'stock.picking',
            'active_ids': [picking_id],
        }
        wid = self.odoo.execute_kw(
            'stock.return.picking', 'create',
            [{'picking_id': picking_id}], {'context': ctx},
        )
        # Popular product_return_moves via default_get (write vazio com ctx)
        self.odoo.execute_kw(
            'stock.return.picking', 'write',
            [[wid], {}], {'context': ctx},
        )
        res = self.odoo.execute_kw(
            'stock.return.picking', 'create_returns',
            [[wid]], {'context': ctx},
        )
        # CR1#1 (2026-05-24 v3): aceitar 3 shapes de retorno do create_returns:
        # dict {'res_id': N} (mais comum) | int N | [N] (lista 1 id em
        # algumas versoes Odoo CIEL IT). Guard contra bool (subclasse de int).
        if isinstance(res, dict):
            new_pid = res.get('res_id')
        elif isinstance(res, list) and len(res) == 1 and isinstance(res[0], int):
            new_pid = res[0]
        elif isinstance(res, bool):
            new_pid = None
        else:
            new_pid = res
        if not isinstance(new_pid, int) or isinstance(new_pid, bool) or new_pid <= 0:
            raise RuntimeError(
                f'Picking {picking_id}: create_returns retornou '
                f'inesperado: res={res!r} (esperava int > 0, dict com '
                f'res_id, ou [int] de 1 elemento).'
            )

        # Setar qty_done = quantity em todas as MLs do novo picking
        mls = self.odoo.search_read(
            'stock.move.line',
            [['picking_id', '=', new_pid]],
            ['id', 'quantity', 'qty_done'],
        )
        for ml in mls:
            q = float(ml.get('quantity') or 0)
            if q > 0 and float(ml.get('qty_done') or 0) != q:
                self.odoo.write(
                    'stock.move.line', [ml['id']],
                    {'qty_done': q},
                )

        # button_validate com skip_backorder
        self.odoo.execute_kw(
            'stock.picking', 'button_validate', [[new_pid]],
            {'context': {
                'skip_backorder': True,
                'picking_ids_not_to_backorder': [new_pid],
            }},
        )

        # G019 pattern: verificar state real apos button_validate
        p = self.odoo.read('stock.picking', [new_pid], ['state'])
        state = p[0]['state'] if p else None
        if state != 'done':
            raise RuntimeError(
                f'Devolucao {new_pid} (do picking {picking_id}) '
                f'state={state!r} apos button_validate (esperado "done"). '
                f'Provavelmente: estoque negativo, wizard pendente, ou '
                f'outro impedimento.'
            )

        logger.info(
            f'Picking {picking_id} ({pk[0]["name"]}): devolucao {new_pid} '
            'criada e validada (state=done)'
        )
        return new_pid

    def liberar_faturamento(self, picking_id: int) -> None:
        """action_liberar_faturamento — sinaliza para o robo CIEL IT criar
        a invoice (account.move).

        Apos esta chamada, o robo da NACOM cria automaticamente o
        account.move correspondente (pode levar ate 30 min). Use
        `aguardar_invoice_do_robo()` para fire-and-poll do resultado.

        G020 FIX: agora valida pre-condicao state=done em runtime.
        Antes Odoo aceitava chamada em picking-nao-done sem erro mas robo
        CIEL IT NUNCA criava invoice — gerando rabo silencioso.

        Reuso: recebimento_lf_odoo_service.py:2526-2531 (etapa 21,
        sem nome explicito).

        Raises:
            RuntimeError: picking nao esta em state=done (pre-cond falhou).
            Exception: propaga qualquer erro de negocio (ex.: 'Picking
                nao validado') para o caller decidir.
        """
        # G020 FIX: validar pre-condicao state=done
        p = self.odoo.read('stock.picking', [picking_id], ['state'])
        if not p:
            raise RuntimeError(f'Picking {picking_id} nao existe no Odoo')
        if p[0]['state'] != 'done':
            raise RuntimeError(
                f'Picking {picking_id} state={p[0]["state"]!r} '
                '(esperado "done" para liberar_faturamento). '
                'F5b validar() pode ter tido false-positive (G019) — '
                're-tentar validar antes de liberar.'
            )
        self.odoo.execute_kw(
            'stock.picking', 'action_liberar_faturamento', [[picking_id]]
        )
        logger.info(
            f'Picking {picking_id}: action_liberar_faturamento disparado '
            '(aguardando robo CIEL IT criar invoice)'
        )

    def aguardar_invoice_do_robo(
        self,
        picking_id: int,
        timeout: int = 1800,
        poll_interval: int = 40,
    ) -> Optional[int]:
        """Fire-and-poll: aguarda robo CIEL IT criar invoice apos
        liberar_faturamento().

        O robo CIEL IT cria account.move com `ref=picking_name` (Metodo
        1). Como fallback (versoes futuras), tenta tambem
        `invoice_origin ilike picking_name` (Metodo 2).

        Args:
            picking_id: stock.picking.id ja com liberar_faturamento()
                disparado.
            timeout: segundos totais ate desistir (default 30 min).
            poll_interval: segundos entre tentativas (default 40s).

        Returns:
            invoice_id (account.move.id) ou None se nao encontrar dentro
            do timeout.

        Raises:
            ValueError: se picking_id nao existe (read vazio).

        Reuso: recebimento_lf_odoo_service.py:2560-2611
        """
        picking = self.odoo.read(
            'stock.picking', [picking_id], ['name', 'company_id']
        )
        if not picking:
            raise ValueError(f'Picking {picking_id} nao encontrado')

        picking_name = picking[0]['name']
        company_id = picking[0]['company_id'][0]

        start = time.time()
        while time.time() - start < timeout:
            # Metodo 1: ref = picking_name (padrao robo CIEL IT atual)
            invoices = self.odoo.search_read(
                'account.move',
                [
                    ['company_id', '=', company_id],
                    ['ref', '=', picking_name],
                    ['state', '!=', 'cancel'],
                ],
                ['id'],
                limit=1,
            )
            if invoices:
                logger.info(
                    f'Picking {picking_id} ({picking_name}): invoice '
                    f'encontrada via ref → id={invoices[0]["id"]}'
                )
                return invoices[0]['id']

            # Metodo 2: invoice_origin ilike (fallback)
            invoices = self.odoo.search_read(
                'account.move',
                [
                    ['company_id', '=', company_id],
                    ['invoice_origin', 'ilike', picking_name],
                    ['state', '!=', 'cancel'],
                ],
                ['id'],
                limit=1,
            )
            if invoices:
                logger.info(
                    f'Picking {picking_id} ({picking_name}): invoice '
                    f'encontrada via invoice_origin → id={invoices[0]["id"]}'
                )
                return invoices[0]['id']

            time.sleep(poll_interval)

        logger.warning(
            f'Picking {picking_id} ({picking_name}): timeout {timeout}s '
            'sem invoice do robo CIEL IT'
        )
        return None

    # ========================================================================
    # ATOMOS v15a — INTER-COMPANY (C6.5 — Skill 8 faturando-odoo decision 10.6)
    # ========================================================================

    def aplicar_peso_volumes_fallback(
        self, picking_id: int,
        peso_unitario_fallback: float = 0.001,
        volumes_fallback: int = 1,
    ) -> Dict[str, Any]:
        """G018 v2: fallback peso_liquido / peso_bruto / volumes em picking.

        `product.write({weight: X})` NAO PERSISTE em CIEL IT (hook reseta para 0),
        mas `l10n_br_peso_liquido`, `l10n_br_peso_bruto` e `l10n_br_volumes` em
        `stock.picking` SAO writable (verificado via fields_get). Aplicar este
        fallback entre F5b (validar) e F5c (liberar_faturamento) evita que
        `action_liberar_faturamento` rejeite por peso=0/volumes=0 silenciosamente.

        Quando aplicar:
            - Apos `validar()` (qty_done preenchido + button_validate OK).
            - Antes de `liberar_faturamento()` (F5c).

        Args:
            picking_id: stock.picking.id.
            peso_unitario_fallback: peso por unidade quando product.weight=0.
                Default 0.001 kg (1g — minimo aceito por SEFAZ).
            volumes_fallback: volumes minimo. Default 1.

        Returns:
            {'aplicado': bool, 'peso_liquido_antes': float,
             'peso_liquido_depois': float, 'volumes_antes': int,
             'volumes_depois': int}

        Fonte: scripts/inventario_2026_05/09_executar_onda1_bulk.py:346-413
            (funcao `aplicar_peso_volumes_fallback_picking`).
        """
        p = self.odoo.read(
            'stock.picking', [picking_id],
            ['l10n_br_peso_liquido', 'l10n_br_peso_bruto',
             'l10n_br_volumes', 'state'],
        )
        if not p:
            return {'aplicado': False, 'erro': 'picking nao encontrado'}
        peso_atual = float(p[0].get('l10n_br_peso_liquido') or 0)
        peso_bruto_atual = float(p[0].get('l10n_br_peso_bruto') or 0)
        volumes_atual = int(p[0].get('l10n_br_volumes') or 0)

        updates: Dict[str, Any] = {}
        if peso_atual <= 0 or peso_bruto_atual <= 0:
            # Calcular peso fallback = SUM(qty_done) * peso_unitario
            moves = self.odoo.search_read(
                'stock.move', [['picking_id', '=', picking_id]],
                ['quantity'],
            )
            qty_total = sum(float(m.get('quantity') or 0) for m in moves)
            peso_calc = max(
                qty_total * peso_unitario_fallback,
                peso_unitario_fallback,
            )
            if peso_atual <= 0:
                updates['l10n_br_peso_liquido'] = peso_calc
            if peso_bruto_atual <= 0:
                updates['l10n_br_peso_bruto'] = peso_calc
        if volumes_atual <= 0:
            updates['l10n_br_volumes'] = volumes_fallback

        if not updates:
            return {
                'aplicado': False,
                'peso_liquido_antes': peso_atual,
                'peso_liquido_depois': peso_atual,
                'volumes_antes': volumes_atual,
                'volumes_depois': volumes_atual,
            }

        self.odoo.write('stock.picking', [picking_id], updates)
        logger.info(
            f'Picking {picking_id}: G018 fallback aplicado — peso '
            f'{peso_atual} -> {updates.get("l10n_br_peso_liquido", peso_atual)}, '
            f'volumes {volumes_atual} -> '
            f'{updates.get("l10n_br_volumes", volumes_atual)}'
        )
        return {
            'aplicado': True,
            'peso_liquido_antes': peso_atual,
            'peso_liquido_depois': updates.get('l10n_br_peso_liquido', peso_atual),
            'volumes_antes': volumes_atual,
            'volumes_depois': updates.get('l10n_br_volumes', volumes_atual),
        }

    def criar_picking_inter_company(
        self,
        company_origem_id: int,
        company_destino_id: int,
        location_origem_id: int,
        location_destino_id: int,
        linhas: List[Dict[str, Any]],
        picking_type_id: int,
        partner_id: int,
        origin: Optional[str] = None,
        scheduled_date: Optional[str] = None,
        incoterm_id: Optional[int] = INCOTERM_CIF,
        carrier_id: Optional[int] = CARRIER_NACOM,
        tracking_por_pid: Optional[Dict[int, str]] = None,
    ) -> Dict[str, Any]:
        """ATOMO ETAPA B (Skill 8 F5a): cria stock.picking de SAIDA inter-company.

        Encapsula `criar_transferencia` com:
            - Pre-flight D-OPS-3: produtos `tracking='none'` tem `lot_name`/
              `lot_id` removidos das linhas (Odoo CIEL IT nao aceita lote em
              produto sem rastreio — falha silenciosa em XML-RPC).
            - Pre-cond: linhas nao vazia + `company_origem != company_destino`
              + partner_id OBRIGATORIO (fiscal_position resolver).
            - G004: incoterm + carrier defaults (passe None p/ omitir).

        Gotchas codificados:
            G004: NACOM exige `incoterm` + `carrier_id` para
                `action_liberar_faturamento` disparar (sem isso: "Voce deve
                informar o Tipo de Frete para liberar o faturamento.").
            G021: linhas com qty<=0 sao filtradas (caller pode passar mistura).
            D-OPS-3: produtos `tracking='none'` (sem rastreio) tem lot_name/
                lot_id stripeados antes do create. Evita o bug L965 do script
                09 que pula esses quants (fix v14b Skill 2 + agora codificado
                aqui para Skill 8 v15+).
            G022: caller eh responsavel por `sleep` entre pickings (orchestrator
                Skill 8 v15b ira preservar pattern script L1136-1138).

        NAO encapsula (caller faz):
            - Resolucao de lote+qty per ajuste (G023 lote_origem) — caller
              monta `linhas` com lot_name corretos.
            - Lote vencido on-the-fly (G014) — caller usa Skill 2 transferir
              ANTES de chamar este atomo.
            - Compensatorio (G-ETB-COMPENSATORIO) — caller analisa
              `qty_restante` e decide.

        Args:
            company_origem_id: company emissora (FB=1, CD=4, LF=5).
            company_destino_id: company destino — usado para validacao + logging
                (NAO vai no payload do picking — apenas log).
            location_origem_id: stock.location de saida (estoque da company origem).
            location_destino_id: stock.location virtual de transito (ex.
                LOCATION_DESTINO_TRANSITO_INDUSTR=26489 para industrializacao).
            linhas: [{'product_id': int, 'quantity': float,
                      'lot_name': str|None, 'lot_id': int|None,
                      'uom_id': int|None, 'name': str|None}, ...]
            picking_type_id: stock.picking.type.id (SAIDA da company origem;
                usar `picking_types.get_picking_type(company_origem, tipo_op)`).
            partner_id: res.partner.id destino — OBRIGATORIO em inter-company.
            origin: campo `origin` do picking (rastreabilidade idempotente).
            scheduled_date: 'YYYY-MM-DD HH:MM:SS' (UTC).
            incoterm_id: G004 — Tipo de Frete (default INCOTERM_CIF=6). None omite.
            carrier_id: G004 — Carrier (default CARRIER_NACOM=996). None omite.
            tracking_por_pid: pre-fetched {pid: tracking}. Se None, lemos do Odoo
                em batch (1 read). Aceita p/ otimizar em bulk.

        Returns:
            Dict com:
              picking_id: int — id do stock.picking (novo ou idempotente)
              status: str — CRIADO | IDEMPOTENT_DONE | IDEMPOTENT_OTHER
              state: str (so quando IDEMPOTENT_*) — state do picking existente
              tracking_none_pids: list[int] — pids tracking='none' detectados
                (informativo; lot_name foi removido das linhas correspondentes;
                vazio se IDEMPOTENT_*)
              linhas_planejadas: list — linhas APOS normalizacao tracking='none'
                (vazio se IDEMPOTENT_*)
              tempo_ms: int

        Raises:
            ValueError: pre-cond falhou (linhas vazias, company iguais, partner_id
                ausente, origin ausente).
            Exception: erros XML-RPC do Odoo (propaga para caller decidir retry).

        v15c F1 (CRITICAL): idempotencia via `origin` EXATO antes de create.
            Sem isso, SSL drop apos create + commit local falha permite
            re-execucao a criar DUPLICATA -> 2 invoices CIEL IT -> 2 NFs
            SEFAZ irreversiveis (catastrofe fiscal). Pattern espelha
            `criar_picking_entrada_destino_manual` v15a. Reviewer D
            R-OPS-1 conf 95.

        G-AUDIT-3 v22+ (2026-05-27): idempotencia NUNCA reaproveita picking
            state=cancel. Estados validos para reaproveitar: draft, confirmed,
            assigned, done. State=cancel representa retry pos-falha (cleanup) e
            reaproveitar provoca `action_assign` "Nada para verificar a
            disponibilidade" em F5b. Se TODOS pickings com origin EXATO sao
            cancel, prossegue para create (cria NOVO). Se ha mistura, retorna
            o primeiro nao-cancelado (idempotencia saudavel). Caso raro mas
            possivel se pipeline foi cancelado N vezes e re-executado.
        """
        inicio = time.time()

        # Pre-cond
        if not linhas:
            raise ValueError(
                'linhas vazias — picking exige ao menos 1 produto'
            )
        if company_origem_id == company_destino_id:
            raise ValueError(
                f'company_origem ({company_origem_id}) == company_destino '
                f'({company_destino_id}) — use Skill 2 transferindo-interno-odoo '
                'para intra-company.'
            )
        if not partner_id:
            raise ValueError(
                'partner_id OBRIGATORIO para inter-company '
                '(fiscal_position precisa resolver). '
                'Usar `operacoes_fiscais.COMPANY_PARTNER_ID[company_destino_id]`.'
            )
        # v15c F1: origin agora e' OBRIGATORIO para idempotencia.
        # Sem origin, fluxo perde a chave de recuperacao apos SSL drop.
        if not origin:
            raise ValueError(
                'origin OBRIGATORIO para idempotencia (v15c F1). '
                'Caller deve montar string controlada (ex: '
                'INV-{ciclo}-SAIDA-{tipo_op}-{ajuste_id:06d}).'
            )

        # v15c F1 (CRITICAL): IDEMPOTENCIA via origin EXATO antes de create.
        # Sem isso, re-execucao apos SSL drop cria DUPLICATA -> 2 NFs SEFAZ.
        # Pattern espelha `criar_picking_entrada_destino_manual` v15a.
        # G-AUDIT-3 v22+: NUNCA reaproveitar state=cancel (retry pos-falha).
        existentes = self.odoo.search_read(
            'stock.picking',
            [['origin', '=', origin]],
            ['id', 'state'],
        )
        if existentes:
            cancelados = [
                p for p in existentes
                if (p.get('state') or '') == 'cancel'
            ]
            reaproveitaveis = [
                p for p in existentes
                if (p.get('state') or '') != 'cancel'
            ]
            if reaproveitaveis:
                # Idempotencia saudavel: pega o primeiro nao-cancelado.
                # Se ha mistura (canceladas + reaproveitavel), prefere o vivo.
                picking_id_existente = reaproveitaveis[0]['id']
                state_existente = (
                    reaproveitaveis[0].get('state') or 'unknown'
                )
                status_idem = (
                    'IDEMPOTENT_DONE' if state_existente == 'done'
                    else 'IDEMPOTENT_OTHER'
                )
                logger.info(
                    f'criar_picking_inter_company: IDEMPOTENT — picking '
                    f'{picking_id_existente} ja existe com origin={origin!r} '
                    f'(state={state_existente!r}, status={status_idem}). '
                    f'Skipping create (F1 v15c — anti-duplicacao SEFAZ).'
                    + (
                        f' (G-AUDIT-3 v22+: ignorando '
                        f'{len(cancelados)} pickings cancelados '
                        f'ids={[p["id"] for p in cancelados]}.)'
                        if cancelados else ''
                    )
                )
                return {
                    'picking_id': picking_id_existente,
                    'status': status_idem,
                    'state': state_existente,
                    'tracking_none_pids': [],
                    'linhas_planejadas': [],
                    'tempo_ms': int((time.time() - inicio) * 1000),
                }
            # G-AUDIT-3 v22+: TODOS sao cancel — criar NOVO.
            # Reaproveitar cancel faz action_assign falhar ("Nada para
            # verificar a disponibilidade"). Codificado como invariante
            # apos retry pipeline v21+ INVENTARIO_2026_05 (picking 321600
            # cancel impedia F5b). Estados validos para reaproveitar:
            # draft/confirmed/assigned/done.
            logger.info(
                f'criar_picking_inter_company: G-AUDIT-3 v22+ — '
                f'encontrados {len(cancelados)} pickings cancelados com '
                f'origin={origin!r} (ids={[p["id"] for p in cancelados]}). '
                f'NAO reaproveitar (criar NOVO picking).'
            )

        # G021: filtrar qty<=0
        linhas_filtradas = [
            l for l in linhas
            if float(l.get('quantity') or 0) > 0
        ]
        if not linhas_filtradas:
            raise ValueError(
                'linhas filtradas (qty > 0) vazias — todas as qty <= 0'
            )

        # D-OPS-3 pre-flight: detectar produtos tracking='none' em batch.
        pids_distintos = sorted({l['product_id'] for l in linhas_filtradas})
        if tracking_por_pid is None:
            prod_tracking = self.odoo.read(
                'product.product', pids_distintos, ['tracking'],
            )
            tracking_por_pid = {
                p['id']: (p.get('tracking') or 'lot')
                for p in prod_tracking
            }

        tracking_none_pids: List[int] = sorted([
            pid for pid in pids_distintos
            if tracking_por_pid.get(pid) == 'none'
        ])

        # Normalizar linhas: produtos tracking='none' nao podem ter lot_name/lot_id
        linhas_normalizadas: List[Dict[str, Any]] = []
        for linha in linhas_filtradas:
            linha_norm = dict(linha)  # copia rasa
            pid = linha_norm['product_id']
            if tracking_por_pid.get(pid) == 'none':
                # D-OPS-3 FIX: produto sem rastreio NAO aceita lote
                if linha_norm.get('lot_name') or linha_norm.get('lot_id'):
                    logger.info(
                        f'  criar_picking_inter_company: D-OPS-3 fix — '
                        f'produto {pid} tracking=none, removendo '
                        f'lot_name={linha_norm.get("lot_name")!r} / '
                        f'lot_id={linha_norm.get("lot_id")}'
                    )
                linha_norm.pop('lot_name', None)
                linha_norm.pop('lot_id', None)
            linhas_normalizadas.append(linha_norm)

        # WRITE — delega para criar_transferencia (incoterm/carrier ja codificado)
        picking_id = self.criar_transferencia(
            company_origem_id=company_origem_id,
            company_destino_id=company_destino_id,
            location_origem_id=location_origem_id,
            location_destino_id=location_destino_id,
            linhas=linhas_normalizadas,
            picking_type_id=picking_type_id,
            partner_id=partner_id,
            scheduled_date=scheduled_date,
            origin=origin,
            incoterm_id=incoterm_id,
            carrier_id=carrier_id,
        )

        logger.info(
            f'criar_picking_inter_company: picking {picking_id} '
            f'origem={company_origem_id} destino={company_destino_id} '
            f'linhas={len(linhas_normalizadas)} '
            f'tracking_none_pids={len(tracking_none_pids)} '
            f'origin={origin!r}'
        )
        return {
            'picking_id': picking_id,
            'status': 'CRIADO',  # v15c F1: distingue de IDEMPOTENT_*
            'tracking_none_pids': tracking_none_pids,
            'linhas_planejadas': linhas_normalizadas,
            'tempo_ms': int((time.time() - inicio) * 1000),
        }

    def validar_picking_inter_company(
        self,
        picking_id: int,
        linhas_esperadas: List[Dict[str, Any]],
        aplicar_peso_volumes: bool = True,
        peso_unitario_fallback: float = 0.001,
        volumes_fallback: int = 1,
    ) -> Dict[str, Any]:
        """ATOMO ETAPA B (Skill 8 F5b): valida picking inter-company.

        Sequencia (D3 v14a — codificada inviolavel):
            1. `confirmar_e_reservar` (action_confirm + action_assign)
            2. `preencher_qty_done` (com lot_name/lot_id de linhas_esperadas)
            3. `ajustar_qty_done_pelo_disponivel` (G021 — reduz demand se < disp)
            4. `validar(linhas_esperadas=)` (G023 consolidar + button_validate +
               G019 re-le state)
            5. (opcional) `aplicar_peso_volumes_fallback` (G018 v2 — preparacao
               para F5c liberar_faturamento; chamado APOS validate quando
               qty_done ja' foi consolidado)

        Substitui o fluxo F5b distribuido em
        `inventario_pipeline_service.f5b_validar_pickings` + script 09
        L1110-1124 (aplicar_peso_volumes_fallback_picking).

        Gotchas codificados:
            G019: `validar()` re-le state apos button_validate; raise se
                != 'done'. Evita false-positive 'cannot marshal None'.
            G023: `validar(linhas_esperadas=)` consolida MLs ANTES de
                button_validate (descarta reservas em lotes nao esperados).
            G021: `ajustar_qty_done_pelo_disponivel` reduz demand se < qty_done
                (evita over-reserva). Pendencias retornadas no output.
            G018 v2: peso/volumes via stock.picking write (product.weight nao
                persiste em CIEL IT).

        NAO faz `liberar_faturamento` (F5c) — fica na Skill 8 orchestrator.
        NAO faz `aguardar_invoice_do_robo` (parte de F5d) — idem.

        Args:
            picking_id: stock.picking.id em state=draft/confirmed/assigned.
            linhas_esperadas: [{'product_id': int, 'quantity': float,
                                'lot_name': str|None, 'lot_id': int|None}, ...]
                vindas dos ajustes do inventario (lote_origem + qtd_ajuste).
                Lista vazia/None desliga G021/G023 (NAO recomendado).
            aplicar_peso_volumes: ativa G018 v2 (default True).
            peso_unitario_fallback: peso/un quando product.weight=0 (default 0.001).
            volumes_fallback: volumes minimo (default 1).

        Returns:
            Dict com:
              picking_id: int
              state_apos_validate: str ('done' se G019 OK)
              mls_pendencias: list — moves cuja demand foi reduzida (G021)
              g023_aplicado: bool — true se linhas_esperadas nao-vazia
              peso_volumes: dict — resultado de aplicar_peso_volumes_fallback
                  (vazio se aplicar_peso_volumes=False)
              tempo_ms: int

        Raises:
            RuntimeError: G019 false-positive (state != 'done' apos validate).
            RuntimeError: produto sem move_line (estoque insuficiente).
            Exception: outros erros Odoo (Quality checks, etc).
        """
        inicio = time.time()

        # 1. Confirmar + reservar
        self.confirmar_e_reservar(picking_id)

        # 2. Preencher qty_done com lotes do ajuste
        if linhas_esperadas:
            self.preencher_qty_done(picking_id, linhas_esperadas)

        # 3. Ajustar demand pelo disponivel (G021)
        ajuste_qty = self.ajustar_qty_done_pelo_disponivel(picking_id)
        pendencias = ajuste_qty.get('pendencias', []) if ajuste_qty else []

        # 4. Validar (G023 + G019 — re-le state)
        # Contrato de validar(): retorna True se state=='done' OU raise
        # RuntimeError. Se chegou aqui sem raise, state == 'done' garantido.
        # CR v15a Issue 3 fix: NAO refaz read extra (validar() ja garante).
        self.validar(picking_id, linhas_esperadas=linhas_esperadas)
        state_final = 'done'

        # 5. G018 v2: peso/volumes (preparacao p/ F5c). Apos validate, qty_done
        # ja foi consolidado e moves estao em state='done'.
        peso_volumes_resultado: Dict[str, Any] = {}
        if aplicar_peso_volumes:
            try:
                peso_volumes_resultado = self.aplicar_peso_volumes_fallback(
                    picking_id,
                    peso_unitario_fallback=peso_unitario_fallback,
                    volumes_fallback=volumes_fallback,
                )
            except Exception as e:
                logger.warning(
                    f'Picking {picking_id}: G018 fallback peso/volumes '
                    f'falhou (nao bloqueante): {e}'
                )
                peso_volumes_resultado = {
                    'aplicado': False,
                    'erro': str(e)[:200],
                }

        logger.info(
            f'validar_picking_inter_company: picking {picking_id} '
            f'state={state_final} pendencias_g021={len(pendencias)} '
            f'g023={bool(linhas_esperadas)} '
            f'peso_volumes_aplicado={peso_volumes_resultado.get("aplicado")}'
        )
        return {
            'picking_id': picking_id,
            'state_apos_validate': state_final,
            'mls_pendencias': pendencias,
            'g023_aplicado': bool(linhas_esperadas),
            'peso_volumes': peso_volumes_resultado,
            'tempo_ms': int((time.time() - inicio) * 1000),
        }

    def criar_picking_entrada_destino_manual(
        self,
        company_destino_id: int,
        location_origem_id: int,
        location_destino_id: int,
        moves_data: List[Dict[str, Any]],
        picking_type_id: int,
        origin: str,
        partner_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """⚠️ REABILITADO C9 (2026-06-02) p/ INDUSTRIALIZACAO_FB_LF avulsa.

        ATUALIZACAO C9: o canary real INDUSTRIALIZACAO_FB_LF (2026-06-02) refutou
        a premissa da deprecacao abaixo ("motor Odoo gera picking via DFe→PO").
        Para DFe-resumo (status 06 — caso de INDUSTRIALIZACAO_FB_LF), a PO
        confirma SEM disparar procurement (move_ids vazio) mesmo com
        route/account/picking_type/team corretos. Logo, o picking de entrada
        manual VOLTA a ser o caminho padrao (folha 1.3.1 PASSO 8), e NAO sera
        removido em v20+. Estendido com 'purchase_line_id' por move (vincula a
        PO p/ qty_received + criar_invoice_from_po).

        --- contexto historico da deprecacao (preservado) ---
        ex-DEPRECATED v19+ — tampão arquitetural AP2 (CLAUDE.md §6.5).

        **Pattern correto v19+**: ETAPA F do orchestrator NÃO deve criar
        picking de ENTRADA (Skill 8 = SAÍDA, fronteira fiscal Skill 7 ENTRADA).
        Caminho correto: criar DFe via `EscrituracaoLfService
        .criar_dfe_a_partir_do_invoice_saida(invoice_id_saida, company_destino)`
        — motor Odoo gera picking automaticamente via DFe→PO→picking nativo.

        Esta função permanece como **museum vivo**:
          - Validada em PROD pickings 317306/317316 (caminho B paliativo v17.5)
          - Útil como fallback durante transição v19→v20 se FLUXO L3 falhar
          - Pytest existente preservado para regressão se for necessário rollback
          - Será REMOVIDA em v20+ após canary real do FLUXO L3 1.2.x

        Usar:
          `FaturamentoPipelineExecutor.executar_fluxo_l3_1_2_x(...)` (v19+ NOVO,
          em app/odoo/estoque/orchestrators/inventario_pipeline.py;
          renomeado de faturamento_pipeline.py em v27+ S3 — stub compat)
          que internamente compõe Skill 7 ABRANGENTE (7 átomos) + Skill 5
          `preencher_lotes_picking` + Skill 5 `validar`.

        ATOMO ETAPA F LEGADO (Skill 8 G023): cria + valida picking de ENTRADA
        manual em destino (FB → {LF, CD}).

        Padrao L17: NFs sentido FB→{LF, CD} de industrializacao interna precisam
        de picking de entrada criado MANUALMENTE no destino. O robo CIEL IT NAO
        cria entrada automatica (nao ha DFe no sentido reverso).

        Validado em PROD com pickings 317306 (LF/IN/01733) e 317316 (LF/IN/01734).

        Sequencia inviolavel:
            1. Idempotencia via `origin`: se ja existe picking com mesmo origin:
                - state='done': retorna esse id (status='IDEMPOTENT_DONE')
                - outro state: retorna esse id mas status='IDEMPOTENT_OTHER'
                  (operador deve investigar; nao recria).
            2. `odoo.create('stock.picking', payload)` com moves_data.
            3. **G023 CRITICO**: `write('stock.move', moves, {'company_id':
               company_destino_id})` apos create — XML-RPC NAO herda company
               do picking para os moves.
            4. `action_confirm` + `action_assign`.
            5. G011: para cada move_line — re-escrever `quantity` (auto-vazio
               apos action_assign) + setar `lot_name` (de moves_data) se a
               ML nao tem lot_id/lot_name.
            6. `button_validate`.
            7. G019/G020: re-le state e raise se != 'done'.

        Gotchas codificados:
            G023 (L17 script L1637-1640): company_id em moves DEVE ser escrito
                apos create — XML-RPC nao herda.
            G011 (script L1646-1665): re-escrever quantity em MLs e setar
                lot_name se faltando.
            G019/G020: re-le state apos button_validate; raise se != 'done'.
            Idempotencia (script L1552-1578): busca por `origin = X` exato
                — se done, skip; se outro state, retorna p/ investigacao.

        Args:
            company_destino_id: company onde a entrada eh criada (LF=5, CD=4).
            location_origem_id: stock.location virtual de transito (ex.
                LOCATION_ORIGEM_ENTRADA_INDUSTR=26489 Em Transito Industrializacao).
            location_destino_id: stock.location de estoque interno do destino
                (ex. COMPANY_LOCATIONS[5]=42 para LF/Estoque).
            moves_data: [{'product_id': int, 'quantity': float,
                          'lot_dest_name': str, 'name': str (opcional),
                          'purchase_line_id': int (opcional — C9)}, ...]
                NB: usa 'lot_dest_name' (nome padronizado p/ entrada manual,
                ex. INV-{cod}-{YYYYMMDD}), distinto do 'lot_name' de SAIDA.
                'purchase_line_id' (C9 2026-06-02): vincula o move a PO.line
                (atualiza qty_received + habilita criar_invoice_from_po).
                Necessario p/ INDUSTRIALIZACAO_FB_LF avulsa (DFe-resumo nao gera
                picking nativo). Callsites legados da ETAPA F nao passam (opt).
            picking_type_id: stock.picking.type.id de ENTRADA do destino
                (ex. PICKING_TYPE_ENTRADA_DESTINO_MANUAL[5]=19 para LF).
            origin: rastreabilidade + idempotencia. Caller monta string como
                `f'INV-{ciclo}-ENTRADA-{label}-NF{invoice_id}'` (formato
                consistente com script 09 L1547-1549).
            partner_id: (C9.1 2026-06-02) emitente da NF (ex. FB=1). Setado no
                picking p/ replicar o picking nativo — sem ele o button_validate
                falha 'Source Location not set'. Opcional (callsites legados
                omitem). NB: `warehouse_id` e' DERIVADO do picking_type
                automaticamente (C9.1) e setado nos moves pelo mesmo motivo.

        Returns:
            Dict com:
              picking_id: int — id do picking (novo ou idempotente)
              status: str — CRIADO | IDEMPOTENT_DONE | IDEMPOTENT_OTHER
              state: str — state final do picking
              n_moves: int — numero de moves criados (0 se idempotente)
              tempo_ms: int

        Raises:
            ValueError: pre-cond falhou (moves_data vazio, origin vazio).
            RuntimeError: G019/G020 — state != 'done' apos button_validate.
            Exception: outros erros XML-RPC (propaga).
        """
        inicio = time.time()

        # Pre-cond
        if not moves_data:
            raise ValueError(
                'moves_data vazio — picking entrada exige ao menos 1 produto'
            )
        if not origin:
            raise ValueError(
                'origin vazio — picking entrada manual exige origin '
                "(idempotencia via 'origin' exato)"
            )

        # Filter qty<=0
        moves_filtrados = [
            m for m in moves_data
            if float(m.get('quantity') or 0) > 0
        ]
        if not moves_filtrados:
            raise ValueError(
                'moves_data filtrados (qty > 0) vazios — todas qty <= 0'
            )

        # 1. Idempotencia: ja existe picking com este origin?
        existentes = self.odoo.search_read(
            'stock.picking',
            [['origin', '=', origin]],
            ['id', 'name', 'state'],
        )
        if existentes:
            ex = existentes[0]
            if ex['state'] == 'done':
                logger.info(
                    f'criar_picking_entrada_destino_manual: origin={origin!r} '
                    f'ja existe done (picking {ex["id"]} {ex["name"]}) — skip'
                )
                return {
                    'picking_id': ex['id'],
                    'status': 'IDEMPOTENT_DONE',
                    'state': 'done',
                    'n_moves': 0,
                    'tempo_ms': int((time.time() - inicio) * 1000),
                }
            else:
                logger.warning(
                    f'criar_picking_entrada_destino_manual: origin={origin!r} '
                    f'ja existe picking {ex["id"]} {ex["name"]} state='
                    f'{ex["state"]} != done. Nao recria — investigacao manual.'
                )
                return {
                    'picking_id': ex['id'],
                    'status': 'IDEMPOTENT_OTHER',
                    'state': ex['state'],
                    'n_moves': 0,
                    'tempo_ms': int((time.time() - inicio) * 1000),
                }

        # C9.1 (2026-06-02): derivar warehouse_id do picking_type. O picking
        # NATIVO (gold standard) carrega warehouse_id; o manual sem ele faz o
        # button_validate falhar 'Source Location not set' na cadeia do motor
        # (canary FB->LF 2026-06-02). Determinístico — não é improviso.
        _pt = self.odoo.read(
            'stock.picking.type', [picking_type_id], ['warehouse_id'],
        )
        _wh = _pt[0].get('warehouse_id') if _pt else None
        warehouse_id = (
            _wh[0] if isinstance(_wh, (list, tuple)) and _wh
            else (_wh if isinstance(_wh, int) else None)
        )

        # 2. Criar stock.picking com moves
        moves_payload = []
        for m in moves_filtrados:
            move_dict = {
                'product_id': m['product_id'],
                'product_uom_qty': float(m['quantity']),
                'name': m.get('name', f'{origin} - prod={m["product_id"]}'),
                'location_id': location_origem_id,
                'location_dest_id': location_destino_id,
            }
            # C9 (2026-06-02): vincular a PO.line quando fornecido. Necessario
            # p/ INDUSTRIALIZACAO_FB_LF avulsa: o DFe-resumo (status 06) NAO
            # gera picking nativo no confirm da PO, entao o fallback manual
            # (folha 1.3.1 PASSO 8) precisa ligar o move a PO.line p/ atualizar
            # qty_received e permitir criar_invoice_from_po (Skill 7) gerar a
            # in_invoice de entrada (CFOP 1901). Opcional/retrocompativel.
            if m.get('purchase_line_id'):
                move_dict['purchase_line_id'] = m['purchase_line_id']
            # C9.1: warehouse_id (do picking_type) replica o picking nativo.
            if warehouse_id:
                move_dict['warehouse_id'] = warehouse_id
            moves_payload.append((0, 0, move_dict))

        picking_data = {
            'picking_type_id': picking_type_id,
            'location_id': location_origem_id,
            'location_dest_id': location_destino_id,
            'company_id': company_destino_id,
            'origin': origin,
            'move_ids_without_package': moves_payload,
        }
        # C9.1: partner_id (emitente da NF) replica o picking nativo — sem ele
        # o button_validate falha 'Source Location not set'. Opcional/retrocompat.
        if partner_id:
            picking_data['partner_id'] = partner_id
        picking_id = self.odoo.create('stock.picking', picking_data)
        logger.info(
            f'criar_picking_entrada_destino_manual: picking {picking_id} '
            f'criado (company_destino={company_destino_id}, '
            f'{len(moves_payload)} moves, origin={origin!r})'
        )

        # 3. G023 CRITICO: forcar company_id nos moves (XML-RPC nao herda)
        moves_ids = self.odoo.search(
            'stock.move', [['picking_id', '=', picking_id]],
        )
        if moves_ids:
            self.odoo.write(
                'stock.move', moves_ids,
                {'company_id': company_destino_id},
            )
            logger.debug(
                f'  G023: company_id={company_destino_id} forcado em '
                f'{len(moves_ids)} moves'
            )

        # 4. action_confirm + action_assign
        self.odoo.execute_kw(
            'stock.picking', 'action_confirm', [[picking_id]],
        )
        self.odoo.execute_kw(
            'stock.picking', 'action_assign', [[picking_id]],
        )

        # 5. G011: preencher lot_name + re-escrever quantity E qty_done em MLs
        # Mapear pid -> lot_dest_name
        lote_por_pid: Dict[int, str] = {}
        for m in moves_filtrados:
            pid = m['product_id']
            lote_dest = m.get('lot_dest_name', '').strip()
            if lote_dest:
                lote_por_pid[pid] = lote_dest

        mls = self.odoo.search_read(
            'stock.move.line',
            [['picking_id', '=', picking_id]],
            ['id', 'product_id', 'quantity', 'lot_id', 'lot_name'],
        )
        for ml in mls:
            pid_ml = ml['product_id'][0] if ml.get('product_id') else None
            if not pid_ml:
                continue
            # G011 (CR v15a Issue 2 fix): re-escrever quantity COMO REFORCO
            # (auto-vazio apos assign em algumas versoes CIEL IT) E setar
            # qty_done explicitamente — button_validate consulta qty_done
            # (nao quantity) para decidir o quanto efetivamente transferir.
            # Atomo eh mais DEFENSIVO que o script L1660-1665 (que tambem
            # validou em PROD 317306/317316 — provavelmente porque CIEL IT
            # trata ETAPA F como immediate_transfer e auto-seta qty_done;
            # mesmo assim setamos explicito para alinhar pattern Skill 5
            # `preencher_qty_done` + reduzir risco de regressao versao Odoo).
            qty_ml = float(ml.get('quantity') or 0)
            updates: Dict[str, Any] = {
                'quantity': qty_ml,
                'qty_done': qty_ml,
            }
            # Setar lot_name se ML nao tem lot_id NEM lot_name AND tem destino
            if not ml.get('lot_id') and not ml.get('lot_name'):
                lote_dest = lote_por_pid.get(pid_ml)
                if lote_dest:
                    updates['lot_name'] = lote_dest
            self.odoo.write('stock.move.line', [ml['id']], updates)

        # 6. button_validate com skip_backorder (CR v15a Issue 1 fix)
        # Alinha pattern dos outros atomos Skill 5 (`validar()`, `devolver()`):
        # `skip_backorder=True` + `picking_ids_not_to_backorder` evita o
        # wizard de backorder (que deixaria state='assigned' em vez de 'done'
        # quando ha diferenca entre qty_done e demand). Se isso acontecer
        # sem o context, G019 raise (falha alta, mas evitavel — Issue 1 v15a CR).
        self.odoo.execute_kw(
            'stock.picking', 'button_validate', [[picking_id]],
            {'context': {
                'skip_backorder': True,
                'picking_ids_not_to_backorder': [picking_id],
            }},
        )

        # 7. G019/G020: re-le state e raise se != 'done'
        p_after = self.odoo.read(
            'stock.picking', [picking_id], ['state'],
        )
        state_final = p_after[0]['state'] if p_after else None
        if state_final != 'done':
            raise RuntimeError(
                f'criar_picking_entrada_destino_manual: picking '
                f'{picking_id} state={state_final!r} apos button_validate '
                f'(esperado "done"). Provavelmente estoque negativo, wizard '
                f'pendente, ou outro impedimento. G019/G020 false-positive.'
            )

        logger.info(
            f'criar_picking_entrada_destino_manual: picking {picking_id} '
            f'state=done (origin={origin!r})'
        )
        return {
            'picking_id': picking_id,
            'status': 'CRIADO',
            'state': 'done',
            'n_moves': len(moves_filtrados),
            'tempo_ms': int((time.time() - inicio) * 1000),
        }

    def preencher_lotes_picking(
        self,
        *,
        picking_id: int,
        lotes_data: Optional[List[Dict[str, Any]]] = None,
        lote_default: Optional[str] = None,
        company_destino: Optional[int] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """ATOMO v19+ S2 (Skill 5): atribui lote+qty em stock.move.line.

        Pattern minerado de `RecebimentoLfOdooService._preencher_lotes_picking`
        (L3982-4100+). Util para pickings NATIVOS gerados via DFe->PO confirmada
        (caminho A/B do FLUXO L3 1.2.1/1.2.2) que precisam ter seus move.lines
        preenchidos com (lote, quantidade) antes do `button_validate`.

        Estrategia:
          - Agrupa lotes_data por product_id
          - Para cada produto: 1a entrada atualiza move.line existente,
            entradas adicionais criam novas move.lines (referenciando a 1a)
          - Resolve/cria o stock.lot EXPLICITAMENTE na company DESTINO
            (C3/G-ENT-6) e seta `lot_id` no write/create — NAO depende do
            Odoo reaproveitar o lote por `lot_name` (que em multi-company puxa
            o lote da empresa ORIGEM e trava o button_validate com 'Empresas
            incompativeis'). Respeita G031 (stock.lot e POR PRODUTO no CIEL IT:
            sempre nome+product_id+company_id).
          - Quando lotes_data nao cobre algum product_id: aplicar lote_default
            se fornecido, senao FALHA (NAO escreve nada — operacao atomica)

        Args:
            picking_id: id stock.picking (state='assigned' ou similar).
            lotes_data: lista [{'product_id': int, 'lote_nome': str,
                                'quantidade': float}, ...]. Mapping por produto.
                                Multiplos entries para o mesmo product_id criam
                                multiplas move.lines (1 por lote).
            lote_default: nome de lote usado quando lotes_data nao cobre algum
                product_id encontrado nas move.lines do picking (ex: 'MIGRAÇÃO'
                para inventario). None = falha se sobrar ML sem mapping.
            company_destino: company_id Odoo onde o lote DEVE existir (C3/G-ENT-6).
                Default None -> deriva de `picking.company_id` (read). Quando
                resolvido para um int valido, o atomo resolve/cria o stock.lot
                nesta company e fixa `lot_id` na move.line. Quando NAO resolvivel
                (ex: testes mockados), cai no comportamento legado (so lot_name).
            dry_run: True (default) NAO escreve; reporta plano.

        Returns:
            dict com:
              status: 'DRY_RUN_OK' | 'PREENCHIDO' | 'FALHA'
              picking_id: int
              company_destino: int | None — company usada na resolucao dos lotes
              mls_atualizadas: int — move.lines existentes que receberam write
              mls_criadas: int — novas move.lines criadas (entradas adicionais)
              mls_pendentes: list[int] — product_ids no picking sem cobertura
                                          (apenas em FALHA, quando lote_default
                                          nao fornecido)
              tempo_ms: int
              erro: str | None — inclui 'FALHA_LOTE_COMPANY_DIVERGENTE' (G-ENT-6)
                                 se o lote resolvido pertence a outra company
        """
        inicio = time.time()
        out: Dict[str, Any] = {
            'status': 'FALHA',
            'picking_id': picking_id,
            'company_destino': company_destino,
            'mls_atualizadas': 0,
            'mls_criadas': 0,
            'mls_pendentes': [],
            'tempo_ms': 0,
            'erro': None,
        }
        # Pre-cond LEVES (NAO raise antes de dry_run — AP4)
        if not isinstance(picking_id, int) or picking_id <= 0:
            out['erro'] = 'picking_id_invalido'
            out['tempo_ms'] = int((time.time() - inicio) * 1000)
            return out
        if lotes_data is None:
            lotes_data = []

        # C3/G-ENT-6: resolver company DESTINO do lote.
        # Default None -> derivar de picking.company_id (read).
        if company_destino is None:
            try:
                pk = self.odoo.read(
                    'stock.picking', [picking_id], ['company_id']
                )
                if pk and isinstance(pk, list) and pk[0].get('company_id'):
                    cid = pk[0]['company_id']
                    # Odoo many2one vem como [id, name]
                    cand = cid[0] if isinstance(cid, (list, tuple)) else cid
                    if isinstance(cand, int):
                        company_destino = cand
            except Exception as e:
                # Nao bloqueia: cai no comportamento legado (so lot_name).
                logger.warning(
                    f'preencher_lotes_picking: nao derivou company_destino '
                    f'do picking {picking_id} ({str(e)[:120]}); '
                    f'usando fallback lot_name'
                )
                company_destino = None
        # So habilita resolucao explicita de lot_id se company_destino e int
        # valido (>0). Caso contrario, preserva comportamento legado (lot_name).
        resolver_lote_por_company = (
            isinstance(company_destino, int) and company_destino > 0
        )
        out['company_destino'] = company_destino if resolver_lote_por_company else None

        # Ler move.lines atuais do picking
        try:
            move_lines = self.odoo.search_read(
                'stock.move.line',
                [('picking_id', '=', picking_id)],
                ['id', 'product_id', 'move_id', 'qty_done', 'quantity',
                 'product_uom_id', 'location_id', 'location_dest_id',
                 'lot_id', 'lot_name'],
            )
        except Exception as e:
            out['erro'] = f'erro_ler_mls: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - inicio) * 1000)
            return out

        if not move_lines:
            out['erro'] = 'picking_sem_move_lines'
            out['tempo_ms'] = int((time.time() - inicio) * 1000)
            return out

        # Indexar MLs por product_id
        lines_por_produto: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for ml in move_lines:
            pid = ml['product_id'][0] if ml.get('product_id') else None
            if pid:
                lines_por_produto[pid].append(ml)

        # Agrupar lotes_data por product_id (preservar ordem)
        lotes_por_produto: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
        for ld in lotes_data:
            pid_ld = ld.get('product_id')
            if isinstance(pid_ld, int) and pid_ld > 0:
                lotes_por_produto[pid_ld].append(ld)

        # Detectar produtos do picking sem cobertura em lotes_data
        produtos_sem_cobertura = [
            pid for pid in lines_por_produto.keys()
            if pid not in lotes_por_produto
        ]
        if produtos_sem_cobertura and not lote_default:
            out['mls_pendentes'] = produtos_sem_cobertura
            out['erro'] = (
                f'produtos_sem_cobertura: {produtos_sem_cobertura} '
                f'(forneca lote_default ou estenda lotes_data)'
            )
            out['tempo_ms'] = int((time.time() - inicio) * 1000)
            return out

        # Aplicar lote_default p/ produtos sem cobertura
        if lote_default and produtos_sem_cobertura:
            for pid in produtos_sem_cobertura:
                mls_pid = lines_por_produto[pid]
                qty_demand_total = sum(
                    float(ml.get('quantity') or 0) for ml in mls_pid
                )
                lotes_por_produto[pid].append({
                    'product_id': pid,
                    'lote_nome': lote_default,
                    'quantidade': qty_demand_total,
                })

        # Montar plano (writes + creates).
        # Cada entrada carrega metadados internos '_pid'/'_lote_nome' (usados
        # apenas no real-run para resolver lot_id na company destino — C3/G-ENT-6;
        # sao removidos antes de enviar ao Odoo).
        writes: List[Tuple[int, Dict[str, Any]]] = []  # (ml_id, write_data)
        creates: List[Dict[str, Any]] = []
        for pid, lotes_produto in lotes_por_produto.items():
            existing_lines = lines_por_produto.get(pid, [])
            if not existing_lines:
                # produto nao esta no picking — skip
                continue
            for i, ld in enumerate(lotes_produto):
                lote_nome = (ld.get('lote_nome') or '').strip()
                qty = float(ld.get('quantidade') or 0)
                if qty <= 0:
                    continue
                if i == 0:
                    line = existing_lines[0]
                    write_data: Dict[str, Any] = {
                        'qty_done': qty,
                        'quantity': qty,
                    }
                    if lote_nome:
                        write_data['lot_name'] = lote_nome
                        write_data['_pid'] = pid
                        write_data['_lote_nome'] = lote_nome
                    writes.append((line['id'], write_data))
                else:
                    ref_line = existing_lines[0]
                    nova_line: Dict[str, Any] = {
                        'move_id': (
                            ref_line['move_id'][0]
                            if ref_line.get('move_id') else None
                        ),
                        'picking_id': picking_id,
                        'product_id': pid,
                        'product_uom_id': (
                            ref_line['product_uom_id'][0]
                            if ref_line.get('product_uom_id') else None
                        ),
                        'qty_done': qty,
                        'quantity': qty,
                        'location_id': (
                            ref_line['location_id'][0]
                            if ref_line.get('location_id') else None
                        ),
                        'location_dest_id': (
                            ref_line['location_dest_id'][0]
                            if ref_line.get('location_dest_id') else None
                        ),
                    }
                    if lote_nome:
                        nova_line['lot_name'] = lote_nome
                        nova_line['_pid'] = pid
                        nova_line['_lote_nome'] = lote_nome
                    creates.append(nova_line)

        if dry_run:
            out['status'] = 'DRY_RUN_OK'
            out['resolver_lote_por_company'] = resolver_lote_por_company
            out['plano'] = {
                'writes_count': len(writes),
                'creates_count': len(creates),
                'writes_sample': [
                    (mid, {k: v for k, v in wd.items()
                           if not k.startswith('_')})
                    for mid, wd in writes[:3]
                ],
                'creates_sample': [
                    {k: v for k, v in cd.items() if not k.startswith('_')}
                    for cd in creates[:3]
                ],
            }
            out['mls_atualizadas'] = len(writes)
            out['mls_criadas'] = len(creates)
            out['tempo_ms'] = int((time.time() - inicio) * 1000)
            return out

        # C3/G-ENT-6: resolver lot_id na company DESTINO (so quando habilitado).
        # Resolve uma vez por (pid, lote_nome) — cache local.
        lot_cache: Dict[Tuple[int, str], int] = {}
        if resolver_lote_por_company:
            lot_svc = StockLotService(odoo=self.odoo)
            entradas = [(w[1], 'write') for w in writes] + \
                       [(c, 'create') for c in creates]
            for data, _tipo in entradas:
                lote_nome = data.get('_lote_nome')
                pid = data.get('_pid')
                if not lote_nome or not isinstance(pid, int):
                    continue
                chave = (pid, lote_nome)
                if chave not in lot_cache:
                    try:
                        lot_id, _criado = lot_svc.criar_se_nao_existe(
                            lote_nome, pid, company_destino,
                        )
                    except Exception as e:
                        out['erro'] = (
                            f'erro_resolver_lote {lote_nome!r} pid={pid} '
                            f'company={company_destino}: {str(e)[:160]}'
                        )
                        out['tempo_ms'] = int((time.time() - inicio) * 1000)
                        return out
                    # Guard pos-condicao G-ENT-6: lote DEVE pertencer a
                    # company destino (company de lote com saldo e imutavel).
                    try:
                        lot_rec = self.odoo.read(
                            'stock.lot', [lot_id], ['company_id']
                        )
                    except Exception as e:
                        out['erro'] = (
                            f'erro_ler_lote_guard lot_id={lot_id}: '
                            f'{str(e)[:160]}'
                        )
                        out['tempo_ms'] = int((time.time() - inicio) * 1000)
                        return out
                    lot_cid = None
                    if lot_rec and isinstance(lot_rec, list):
                        raw = lot_rec[0].get('company_id')
                        lot_cid = (
                            raw[0] if isinstance(raw, (list, tuple)) else raw
                        )
                    if lot_cid != company_destino:
                        out['erro'] = 'FALHA_LOTE_COMPANY_DIVERGENTE'
                        out['lote_divergente'] = {
                            'lot_id': lot_id,
                            'lote_nome': lote_nome,
                            'product_id': pid,
                            'company_lote': lot_cid,
                            'company_destino': company_destino,
                        }
                        out['tempo_ms'] = int((time.time() - inicio) * 1000)
                        # NAO escreve nada — operacao atomica (G-ENT-6)
                        return out
                    lot_cache[chave] = lot_id
                data['lot_id'] = lot_cache[chave]

        # Limpar metadados internos antes de enviar ao Odoo
        for _ml_id, wd in writes:
            wd.pop('_pid', None)
            wd.pop('_lote_nome', None)
        for cd in creates:
            cd.pop('_pid', None)
            cd.pop('_lote_nome', None)

        # REAL-RUN: writes + creates
        try:
            for ml_id, wdata in writes:
                self.odoo.write('stock.move.line', [ml_id], wdata)
            for cdata in creates:
                self.odoo.create('stock.move.line', cdata)
        except Exception as e:
            out['erro'] = f'write_mls_falhou: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - inicio) * 1000)
            return out

        out['status'] = 'PREENCHIDO'
        out['mls_atualizadas'] = len(writes)
        out['mls_criadas'] = len(creates)
        out['tempo_ms'] = int((time.time() - inicio) * 1000)
        logger.info(
            f'preencher_lotes_picking: picking={picking_id} '
            f'atualizadas={len(writes)} criadas={len(creates)}'
        )
        return out
