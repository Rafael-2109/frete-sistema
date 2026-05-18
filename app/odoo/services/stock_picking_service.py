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
from typing import Any, Dict, List, Optional

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
    INCOTERM_CIF = 6     # account.incoterms code=CIF
    CARRIER_NACOM = 996  # delivery.carrier "(61.724.241/0001-78) NACOM GOYA ..."

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

        Reuso: recebimento_lf_odoo_service.py:2317-2334.
        """
        self.odoo.execute_kw('stock.picking', 'action_confirm', [[picking_id]])
        self.odoo.execute_kw('stock.picking', 'action_assign', [[picking_id]])
        logger.info(f'Picking {picking_id}: confirmado + reservado')

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

    def validar(self, picking_id: int) -> bool:
        """button_validate com context skip_backorder.

        Trata 'cannot marshal None' como sucesso (XML-RPC nao serializa
        None retornado por Odoo quando nao ha wizard intermediario).

        Context `skip_backorder=True` + `picking_ids_not_to_backorder`
        evita o wizard de backorder (que deixaria o picking em 'assigned'
        ao inves de 'done' quando ha diferenca entre qty_done e demand).
        Padrao usado em recebimento_lf_odoo_service.py:1548-1558.

        Raises:
            Exception: qualquer outra exceção (ex.: 'Quality checks
                pending') eh propagada — o caller decide retry ou abort.
        """
        try:
            self.odoo.execute_kw(
                'stock.picking', 'button_validate', [[picking_id]],
                {'context': {
                    'skip_backorder': True,
                    'picking_ids_not_to_backorder': [picking_id],
                }},
            )
            return True
        except Exception as e:
            if 'cannot marshal None' in str(e):
                logger.info(
                    f'Picking {picking_id}: button_validate retornou None (sucesso)'
                )
                return True
            raise

    def cancelar(self, picking_id: int, motivo: str = '') -> bool:
        """Cancela picking via action_cancel. Motivo apenas para log."""
        self.odoo.execute_kw('stock.picking', 'action_cancel', [[picking_id]])
        logger.info(
            f'Picking {picking_id} cancelado'
            + (f' (motivo: {motivo})' if motivo else '')
        )
        return True

    def liberar_faturamento(self, picking_id: int) -> None:
        """action_liberar_faturamento — sinaliza para o robo CIEL IT criar
        a invoice (account.move).

        Apos esta chamada, o robo da NACOM cria automaticamente o
        account.move correspondente (pode levar ate 30 min). Use
        `aguardar_invoice_do_robo()` para fire-and-poll do resultado.

        Pre-condicao: picking em state='done' e
        liberacao_para_faturamento configurada no picking_type.

        Reuso: recebimento_lf_odoo_service.py:2526-2531 (etapa 21,
        sem nome explicito).

        Raises:
            Exception: propaga qualquer erro de negocio (ex.: 'Picking
                nao validado') para o caller decidir.
        """
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
