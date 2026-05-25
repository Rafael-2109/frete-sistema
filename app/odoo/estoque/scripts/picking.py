"""StockPickingService — gerencia stock.picking de transferencia.

Generaliza padroes em:
- app/pallet/services/emissao_nf_pallet.py:115-177 (criar_picking -> validar_picking)
- app/recebimento/services/recebimento_lf_odoo_service.py:2273-2611 (saida +
  liberar_faturamento + aguardar_invoice do robo CIEL IT)

Padrao: create -> action_confirm -> action_assign -> preencher qty_done ->
button_validate -> action_liberar_faturamento -> aguardar invoice do robo CIEL IT.

Spec: docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md §6.2
"""
import logging
import time
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.odoo.constants import ids_diversos
from app.odoo.utils.connection import get_odoo_connection

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
            if 'cannot marshal None' in str(e):
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

        Idempotencia: se ja existe picking com `origin ilike "Devolução
        de {name}"`, retorna esse id sem criar duplicado.

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
        ja = self.odoo.search_read(
            'stock.picking',
            [['origin', 'ilike', f'Devolução de {pk[0]["name"]}']],
            ['id'], limit=1,
        )
        if ja:
            logger.info(
                f'Picking {picking_id} ({pk[0]["name"]}): devolucao ja '
                f'existe (id={ja[0]["id"]}). Retornando sem criar.'
            )
            return ja[0]['id']

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
