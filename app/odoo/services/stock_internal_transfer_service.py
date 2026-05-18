"""StockInternalTransferService — transferencia entre lotes / locations internas.

Servico ATOMICO e REUTILIZAVEL para ajustar quantidades entre:
- Lotes diferentes (mesmo product+company+location)
- Quant sem lote (lot_id=False) -> lote especifico
- Locations diferentes da mesma company (opcional, futuro)

Implementa o padrao oficial do Odoo 16+ via INVENTORY ADJUSTMENT
(stock.quant.action_apply_inventory). Movimenta quantidades sem
renomear lotes — preserva rastreabilidade fiscal e historico.

Por que NAO renomear lote (`stock.lot.write({'name': ...})`)?
- Renomear afeta TODO o lote (todos os quants) — nao permite split parcial
- Viola unique constraint (name, product_id, company_id) se 2 origens
  apontam para o mesmo destino
- Quant sem lot_id (lot_id=False) nao tem nome para renomear

A operacao gera 1 stock.move automatico (via inventory adjustment)
visivel em Inventory > Reporting > Stock Moves com origem
'Physical Inventory'. E auditavel.

Spec: D004/D005 (refator 2026-05-18) — inventario 2026-05.

Reutilizavel para:
- Consolidacao de lotes apos inventario (cenario INVENTARIO_2026_05)
- Correcao de cadastro errado de lote
- Atribuicao de lote a quant sem lote (lot_id=False)
- Split de lote para fracionamento fiscal
"""
import logging
import time
from typing import Any, Dict, List, Optional

from app.odoo.services.stock_lot_service import StockLotService
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


class StockInternalTransferService:
    """Transferencia atomica de quantidade entre lotes no mesmo location."""

    def __init__(self, odoo=None, lot_svc=None):
        self.odoo = odoo or get_odoo_connection()
        self.lot_svc = lot_svc or StockLotService(odoo=self.odoo)

    # ============================================================
    # Helper: buscar quant especifico
    # ============================================================

    def buscar_quant(
        self,
        product_id: int,
        company_id: int,
        location_id: int,
        lot_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """Busca 1 quant por (product, company, location, lot_id).

        lot_id=None busca quant sem lote (lot_id=False no Odoo).
        Se ha multiplos quants compativeis (mesmo lote em sub-locations
        agregadas), retorna o primeiro — caller deve refinar location_id.

        Returns:
            dict {id, quantity, value, lot_id} ou None se nao existe.
        """
        domain: List = [
            ['product_id', '=', product_id],
            ['company_id', '=', company_id],
            ['location_id', '=', location_id],
        ]
        if lot_id is None:
            domain.append(['lot_id', '=', False])
        else:
            domain.append(['lot_id', '=', lot_id])
        quants = self.odoo.search_read(
            'stock.quant', domain,
            ['id', 'quantity', 'value', 'lot_id', 'reserved_quantity'],
            limit=1,
        )
        return quants[0] if quants else None

    def listar_quants(
        self, product_id: int, company_id: int, location_id: int,
    ) -> List[Dict[str, Any]]:
        """Lista todos os quants do produto/company/location.

        Util para auditoria pos-transferencia.
        """
        return self.odoo.search_read(
            'stock.quant',
            [
                ['product_id', '=', product_id],
                ['company_id', '=', company_id],
                ['location_id', '=', location_id],
            ],
            ['id', 'quantity', 'value', 'lot_id', 'reserved_quantity'],
        )

    # ============================================================
    # Operacao atomica: transferir quantidade entre lotes
    # ============================================================

    def transferir_entre_lotes(
        self,
        product_id: int,
        company_id: int,
        location_id: int,
        qty: float,
        lot_id_origem: Optional[int],
        lot_id_destino: int,
    ) -> Dict[str, Any]:
        """Transfere `qty` do `lot_id_origem` para `lot_id_destino` no
        mesmo product/company/location, via inventory adjustment.

        Operacao atomica em 2 passos (cada um e um inventory adjustment
        com action_apply_inventory no Odoo):
            1. Reduzir quant origem em `qty`
            2. Aumentar (ou criar) quant destino em `qty`

        Args:
            product_id: product.product.id.
            company_id: company_id (res.company.id).
            location_id: stock.location.id (origem == destino).
            qty: quantidade a transferir (positiva).
            lot_id_origem: stock.lot.id do lote de origem.
                Use `None` para "quant sem lote" (lot_id=False no Odoo).
            lot_id_destino: stock.lot.id do lote de destino
                (use StockLotService.criar_se_nao_existe para garantir).

        Returns:
            dict com:
                quant_origem_id, quant_origem_qty_antes, quant_origem_qty_apos,
                quant_destino_id, quant_destino_qty_antes, quant_destino_qty_apos,
                qty_transferida, tempo_ms.

        Raises:
            ValueError: qty<=0, lot_ids iguais, falta quant origem.
            RuntimeError: quant origem tem qty < qty solicitada,
                ou reserva impede transferencia.
        """
        if qty <= 0:
            raise ValueError(f'qty deve ser > 0 (recebido {qty})')
        if lot_id_origem == lot_id_destino:
            raise ValueError(
                f'lot_id_origem == lot_id_destino ({lot_id_origem}) — '
                'nao ha o que transferir'
            )

        inicio = time.time()

        # 1. Localizar quant origem
        quant_origem = self.buscar_quant(
            product_id, company_id, location_id, lot_id_origem,
        )
        if not quant_origem:
            raise ValueError(
                f'Quant origem nao encontrado: product_id={product_id} '
                f'company_id={company_id} location_id={location_id} '
                f'lot_id={lot_id_origem}'
            )
        qty_origem_antes = float(quant_origem['quantity'])
        reservada = float(quant_origem.get('reserved_quantity', 0) or 0)

        if qty_origem_antes < qty:
            raise RuntimeError(
                f'Quant origem {quant_origem["id"]} tem {qty_origem_antes} un '
                f'mas pedido transferir {qty} un'
            )
        # Bloquear se ha reserva que ultrapassaria saldo restante.
        # Saldo apos = qty_origem_antes - qty; deve ser >= reservada.
        if (qty_origem_antes - qty) < reservada:
            raise RuntimeError(
                f'Quant origem {quant_origem["id"]} tem {reservada} un reservadas '
                f'em pickings ativos. Saldo apos transferencia '
                f'({qty_origem_antes - qty}) ficaria < reserva. Cancelar '
                f'pickings ou reduzir qty solicitada.'
            )

        # 2. Localizar (ou preparar criacao de) quant destino
        quant_destino = self.buscar_quant(
            product_id, company_id, location_id, lot_id_destino,
        )
        qty_destino_antes = (
            float(quant_destino['quantity']) if quant_destino else 0.0
        )

        # 3. Reduzir quant origem via inventory adjustment
        nova_qty_origem = qty_origem_antes - qty
        self.odoo.write(
            'stock.quant', [quant_origem['id']],
            {'inventory_quantity': nova_qty_origem},
        )
        self.odoo.execute_kw(
            'stock.quant', 'action_apply_inventory', [[quant_origem['id']]],
        )
        logger.info(
            f'Transferencia: quant_origem {quant_origem["id"]} '
            f'(lot_id={lot_id_origem}) {qty_origem_antes} → '
            f'{nova_qty_origem} (-{qty})'
        )

        # 4. Aumentar (ou criar) quant destino
        nova_qty_destino = qty_destino_antes + qty
        if quant_destino:
            self.odoo.write(
                'stock.quant', [quant_destino['id']],
                {'inventory_quantity': nova_qty_destino},
            )
            self.odoo.execute_kw(
                'stock.quant', 'action_apply_inventory',
                [[quant_destino['id']]],
            )
            quant_destino_id = quant_destino['id']
        else:
            # Criar quant novo. Em Odoo 16, criar com 'inventory_quantity'
            # e depois apply_inventory gera o movimento de entrada.
            quant_destino_id = self.odoo.create('stock.quant', {
                'product_id': product_id,
                'company_id': company_id,
                'location_id': location_id,
                'lot_id': lot_id_destino,
                'inventory_quantity': nova_qty_destino,
            })
            self.odoo.execute_kw(
                'stock.quant', 'action_apply_inventory',
                [[quant_destino_id]],
            )
        logger.info(
            f'Transferencia: quant_destino {quant_destino_id} '
            f'(lot_id={lot_id_destino}) {qty_destino_antes} → '
            f'{nova_qty_destino} (+{qty})'
        )

        return {
            'quant_origem_id': quant_origem['id'],
            'quant_origem_qty_antes': qty_origem_antes,
            'quant_origem_qty_apos': nova_qty_origem,
            'quant_destino_id': quant_destino_id,
            'quant_destino_qty_antes': qty_destino_antes,
            'quant_destino_qty_apos': nova_qty_destino,
            'qty_transferida': qty,
            'lot_id_origem': lot_id_origem,
            'lot_id_destino': lot_id_destino,
            'tempo_ms': int((time.time() - inicio) * 1000),
        }

    # ============================================================
    # Wrapper de alto nivel: garantir lote destino + transferir
    # ============================================================

    def transferir_quantidade_para_lote(
        self,
        product_id: int,
        company_id: int,
        location_id: int,
        qty: float,
        lot_id_origem: Optional[int],
        nome_lote_destino: str,
        expiration_date_destino: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Garante lote destino existe e transfere qty.

        Wrapper conveniente: 1 chamada faz criar_se_nao_existe + transferir.

        Args:
            product_id, company_id, location_id, qty, lot_id_origem:
                como em transferir_entre_lotes.
            nome_lote_destino: nome do lote alvo (ex: '26014'). Criado
                se nao existir.
            expiration_date_destino: validade (opcional) do lote alvo.

        Returns:
            dict como transferir_entre_lotes + chaves extras:
                lote_destino_nome, lote_destino_criado_agora.
        """
        lot_id_destino, criado = self.lot_svc.criar_se_nao_existe(
            nome_lote_destino, product_id, company_id,
            expiration_date=expiration_date_destino,
        )
        res = self.transferir_entre_lotes(
            product_id=product_id,
            company_id=company_id,
            location_id=location_id,
            qty=qty,
            lot_id_origem=lot_id_origem,
            lot_id_destino=lot_id_destino,
        )
        res['lote_destino_nome'] = nome_lote_destino
        res['lote_destino_criado_agora'] = criado
        return res
