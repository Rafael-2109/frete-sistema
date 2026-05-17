"""StockLotService — gerencia lotes (stock.lot) no Odoo.

Wrapper sobre helpers existentes em
`app/recebimento/services/recebimento_fisico_odoo_service.py`:
- `_resolver_lote` (linhas 324-378)
- `_criar_stock_lot_com_fallback` (linhas 416-482)

Inclui workaround do bug intermitente do operador `'='` em `stock.lot.search`
(GOTCHAS.md:111). Usar SEMPRE `'in'` ou `'=like'`.

Spec: docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md §6.2
"""
import logging
from typing import Optional
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


class StockLotService:
    """Gerencia stock.lot no Odoo de forma reutilizavel."""

    def __init__(self, odoo=None):
        self.odoo = odoo or get_odoo_connection()

    def buscar_por_nome(self, nome: str, product_id: int, company_id: int) -> Optional[int]:
        """Busca lote por nome usando operador 'in' (workaround do bug do '=').

        Estrategia em 2 passos:
        1. Primeiro tenta `['name', 'in', [nome]]` (resolve a maior parte dos casos).
        2. Fallback: `['name', '=like', nome]` se o primeiro nao encontrar.

        Returns:
            lot_id ou None.
        """
        if not nome:
            return None

        ids = self.odoo.search('stock.lot', [
            ['name', 'in', [nome]],
            ['product_id', '=', product_id],
            ['company_id', '=', company_id],
        ], limit=1)
        if ids:
            return ids[0]

        ids = self.odoo.search('stock.lot', [
            ['name', '=like', nome],
            ['product_id', '=', product_id],
            ['company_id', '=', company_id],
        ], limit=1)
        return ids[0] if ids else None

    def criar(self, nome: str, product_id: int, company_id: int,
              expiration_date: Optional[str] = None) -> int:
        """Cria stock.lot. Em caso de unique constraint, busca o existente e atualiza.

        Args:
            nome: nome do lote (obrigatorio).
            product_id: produto Odoo.
            company_id: empresa Odoo.
            expiration_date: validade no formato 'YYYY-MM-DD HH:MM:SS' ou None.

        Returns:
            lot_id (recem criado ou existente).

        Raises:
            ValueError: se `nome` vazio.
            Exception: para erros que nao sao unique constraint.
        """
        if not nome:
            raise ValueError('Nome do lote obrigatorio')

        payload = {
            'name': nome,
            'product_id': product_id,
            'company_id': company_id,
        }
        if expiration_date:
            payload['expiration_date'] = expiration_date

        try:
            return self.odoo.create('stock.lot', payload)
        except Exception as e:
            err = str(e).lower()
            if 'unique' in err or 'duplicate' in err:
                logger.warning(
                    f'Lote {nome!r} ja existe (unique constraint), buscando existente'
                )
                existente = self.buscar_por_nome(nome, product_id, company_id)
                if existente:
                    if expiration_date:
                        self.odoo.write(
                            'stock.lot', [existente],
                            {'expiration_date': expiration_date},
                        )
                    return existente
            raise

    def renomear(self, lot_id: int, novo_nome: str) -> bool:
        """Renomeia lote (regra P9 do spec — divergencia apenas de lote).

        Guard: bloqueia se ha `stock.move.line` em picking nao-done para
        este lote. Sem isso o rename pode corromper picking ativo.

        Raises:
            ValueError: se `novo_nome` vazio.
            RuntimeError: se ha move pendente.
        """
        if not novo_nome:
            raise ValueError('novo_nome obrigatorio')

        pendentes = self.odoo.search('stock.move.line', [
            ['lot_id', '=', lot_id],
            ['state', 'not in', ['done', 'cancel']],
        ], limit=1)
        if pendentes:
            raise RuntimeError(
                f'Lote {lot_id} tem stock.move.line em picking nao-done '
                f'(line_id={pendentes[0]}); rename bloqueado.'
            )

        self.odoo.write('stock.lot', [lot_id], {'name': novo_nome})
        return True

    def inativar(self, lot_id: int) -> bool:
        """Indisponibiliza lote (active=False).

        Usado por `indisponibilizacao_estoque_service` apos canary tecnico OK.
        """
        self.odoo.write('stock.lot', [lot_id], {'active': False})
        return True

    def reativar(self, lot_id: int) -> bool:
        """Reverte `inativar`."""
        self.odoo.write('stock.lot', [lot_id], {'active': True})
        return True

    def atualizar_validade(self, lot_id: int, expiration_date: str) -> bool:
        """Atualiza data de validade.

        Args:
            expiration_date: formato 'YYYY-MM-DD HH:MM:SS'.
        """
        self.odoo.write('stock.lot', [lot_id], {'expiration_date': expiration_date})
        return True
