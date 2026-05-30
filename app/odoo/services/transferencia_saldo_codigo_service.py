"""TransferenciaSaldoCodigoService — transfere saldo entre CÓDIGOS mantendo lote.

Em CD/Estoque (company 4, loc 32). É uma TROCA DE CÓDIGO: mesmo nome de lote em
produtos diferentes (origem→destino). Diferente de StockInternalTransferService
(mesmo produto, lotes diferentes). Orquestra 2 ajustes atômicos:
  1. reduzir quant origem (lote X)
  2. garantir lote X no produto destino (criar com validade do origem) + aumentar

Desacoplado da UI (sem flask/request/current_user): `usuario` entra por parâmetro.
Tela web e futura skill do gestor-estoque-odoo consomem o mesmo service.

Spec: docs/superpowers/specs/2026-05-22-transferencia-saldo-codigos-odoo-design.md
"""
import logging
from typing import Any, Dict, List, Optional

from app.odoo.constants.locations import COMPANY_LOCATIONS
from app.odoo.services.stock_lot_service import StockLotService
from app.odoo.services.stock_quant_adjustment_service import (
    StockQuantAdjustmentService,
)
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)

CASAS = 6


def _get_db_session():
    """Acesso lazy à sessão SQLAlchemy (evita import circular app.odoo→app)."""
    from app import db
    return db.session


class TransferenciaSaldoCodigoService:
    """Transfere saldo entre códigos mantendo o lote, em CD/Estoque."""

    CD_COMPANY_ID = 4
    CD_ESTOQUE_LOC = COMPANY_LOCATIONS[4]  # 32

    def __init__(self, odoo=None, adjustment_svc=None, lot_svc=None):
        self.odoo = odoo or get_odoo_connection()
        self.lot_svc = lot_svc or StockLotService(odoo=self.odoo)
        self.adjustment_svc = adjustment_svc or StockQuantAdjustmentService(
            odoo=self.odoo, lot_svc=self.lot_svc)

    def resolver_produto(self, cod) -> Dict[str, Any]:
        """default_code -> dados do produto. Erro se 0 ou >1 ativo."""
        cod = str(cod).strip()
        res = self.odoo.search_read(
            'product.product', [['default_code', '=', cod]],
            ['id', 'default_code', 'name', 'active', 'tracking',
             'uom_id', 'use_expiration_date'], limit=0)
        ativos = [p for p in res if p.get('active')]
        candidatos = ativos or res
        if not candidatos:
            raise ValueError(f'Produto {cod} nao encontrado no Odoo')
        if len(candidatos) > 1:
            raise ValueError(
                f'Produto {cod} ambiguo: {len(candidatos)} produtos')
        p = candidatos[0]
        return {
            'product_id': p['id'], 'cod': p['default_code'], 'name': p.get('name'),
            'tracking': p.get('tracking'),
            'uom': p['uom_id'][1] if p.get('uom_id') else None,
            'use_expiration_date': bool(p.get('use_expiration_date')),
        }

    def listar_lotes_cd_estoque(self, cod) -> List[Dict[str, Any]]:
        """Lotes do código em CD/Estoque com qtd/reservado/disponível/migração."""
        info = self.resolver_produto(cod)
        quants = self.odoo.search_read(
            'stock.quant',
            [['product_id', '=', info['product_id']],
             ['company_id', '=', self.CD_COMPANY_ID],
             ['location_id', '=', self.CD_ESTOQUE_LOC]],
            ['id', 'lot_id', 'quantity', 'reserved_quantity'], limit=0)
        out: List[Dict[str, Any]] = []
        for q in quants:
            lot = q.get('lot_id')
            lote_nome = lot[1] if lot else None
            qty = round(float(q['quantity']), CASAS)
            rsv = round(float(q.get('reserved_quantity') or 0), CASAS)
            out.append({
                'lote_nome': lote_nome,
                'lot_id': lot[0] if lot else None,
                'quantidade': qty, 'reservado': rsv,
                'disponivel': round(qty - rsv, CASAS),
                'is_migracao': bool(lote_nome and 'MIGRA' in lote_nome.upper()),
            })
        return out

    def descobrir_destinos(self, cod) -> List[Dict[str, Any]]:
        """Pares ativos relacionados (bidirecional), excluindo o próprio código."""
        from app.estoque.models import UnificacaoCodigos
        cod = str(cod).strip()
        relacionados = UnificacaoCodigos.get_todos_codigos_relacionados(cod)
        out: List[Dict[str, Any]] = []
        for c in relacionados:
            if str(c) == cod:
                continue
            try:
                info = self.resolver_produto(c)
                nome = info['name']
            except ValueError:
                nome = None
            out.append({'codigo': str(c), 'nome': nome})
        return out

    def transferir(self, cod_origem, cod_destino, lote_nome, qty,
                   usuario) -> Dict[str, Any]:
        """Transfere `qty` de cod_origem→cod_destino mantendo `lote_nome` em
        CD/Estoque. Reduz origem → cria/aumenta destino (compensa se falhar).
        Espelha em MovimentacaoEstoque. `lote_nome=None` => quant sem lote.
        """
        cod_origem, cod_destino = str(cod_origem).strip(), str(cod_destino).strip()
        qty = round(float(qty), CASAS)
        r: Dict[str, Any] = {
            'cod_origem': cod_origem, 'cod_destino': cod_destino,
            'lote_nome': lote_nome, 'qty': qty, 'usuario': usuario,
            'lote_criado': False, 'status': None}
        if qty <= 0:
            raise ValueError(f'qty deve ser > 0 (recebido {qty})')

        # 1. validar par bidirecional
        destinos = {d['codigo'] for d in self.descobrir_destinos(cod_origem)}
        if cod_destino not in destinos:
            raise ValueError(
                f'{cod_destino} nao e par de {cod_origem} em UnificacaoCodigos ativa')

        # 2. resolver produtos
        origem = self.resolver_produto(cod_origem)
        destino = self.resolver_produto(cod_destino)
        for info in (origem, destino):
            if info['tracking'] != 'lot':
                raise ValueError(
                    f"produto {info['cod']} tracking={info['tracking']} (esperado lot)")
        pid_o, pid_d = origem['product_id'], destino['product_id']

        # 3. resolver lote origem + validade (replicar no destino)
        lot_id_origem: Optional[int] = None
        validade: Optional[str] = None
        if lote_nome:
            lot_id_origem = self.lot_svc.buscar_por_nome(
                lote_nome, pid_o, self.CD_COMPANY_ID)
            if not lot_id_origem:
                raise ValueError(
                    f'lote {lote_nome!r} nao encontrado no produto {cod_origem} (CD)')
            lots = self.odoo.read('stock.lot', [lot_id_origem], ['expiration_date'])
            validade = (lots[0].get('expiration_date') or None) if lots else None

        # 4. reduzir origem
        r_red = self.adjustment_svc.ajustar_quant(
            product_id=pid_o, company_id=self.CD_COMPANY_ID,
            location_id=self.CD_ESTOQUE_LOC, lot_id=lot_id_origem, delta=-qty,
            validar_nao_negativar=True, validar_nao_abaixo_reserva=True)
        r['reducao'] = r_red
        if r_red['status'] != 'EXECUTADO':
            r['status'] = 'FALHA_REDUCAO'
            r['erro'] = r_red.get('erro')
            return r
        r['origem_antes'], r['origem_apos'] = r_red.get('qty_antes'), r_red.get('qty_apos')

        # 5. garantir lote destino (validade do origem se produto usa validade)
        lot_id_destino: Optional[int] = None
        if lote_nome:
            exp = validade if destino['use_expiration_date'] else None
            lot_id_destino, criado = self.lot_svc.criar_se_nao_existe(
                lote_nome, pid_d, self.CD_COMPANY_ID, expiration_date=exp)
            r['lote_criado'] = criado

        # 6. aumentar destino (compensar se falhar)
        r_aum = self.adjustment_svc.ajustar_quant(
            product_id=pid_d, company_id=self.CD_COMPANY_ID,
            location_id=self.CD_ESTOQUE_LOC, lot_id=lot_id_destino, delta=qty,
            criar_se_faltar=True, validar_nao_negativar=True,
            validar_nao_abaixo_reserva=True)
        r['aumento'] = r_aum
        if r_aum['status'] != 'EXECUTADO':
            comp = self.adjustment_svc.ajustar_quant(
                product_id=pid_o, company_id=self.CD_COMPANY_ID,
                location_id=self.CD_ESTOQUE_LOC, lot_id=lot_id_origem, delta=qty,
                validar_nao_negativar=False, validar_nao_abaixo_reserva=False)
            r['compensacao'] = comp
            r['status'] = 'FALHA_AUMENTO_COMPENSADO'
            r['erro'] = r_aum.get('erro')
            logger.error(
                f'Aumento falhou ({cod_origem}->{cod_destino} lote {lote_nome} '
                f'qty {qty}): {r_aum.get("erro")}; compensacao={comp.get("status")}')
            return r
        r['destino_antes'], r['destino_apos'] = r_aum.get('qty_antes'), r_aum.get('qty_apos')

        # 7. espelho local
        self._registrar_movimentacao_local(
            cod_origem, origem['name'], cod_destino, destino['name'],
            lote_nome, qty, usuario)
        r['status'] = 'EXECUTADO'
        return r

    def _registrar_movimentacao_local(
        self, cod_origem, nome_origem, cod_destino, nome_destino,
        lote_nome, qty, usuario) -> None:
        """Espelha a troca no estoque local: SAIDA(origem, -qty) + ENTRADA(destino, +qty).

        Convenção do sistema: saldo = SUM(qtd_movimentacao) puro (sinal embutido no
        valor), então SAIDA grava NEGATIVO — igual a processar_faturamento.py
        (-abs(qtd)) e consumo_producao_service.py. Sem o sinal, o saldo local do
        código de ORIGEM inflaria em vez de reduzir.

        AJUSTE/MANUAL — não duplica com o sync (entrada_material_service só
        importa picking_type_code='incoming'; inventory adjustment não gera).
        """
        from app.estoque.models import MovimentacaoEstoque
        from app.utils.timezone import agora_utc_naive
        hoje = agora_utc_naive().date()
        obs = (f'Transferencia saldo {cod_origem}->{cod_destino} '
               f'lote {lote_nome or "(sem lote)"} qtd {qty} (CD/Estoque Odoo)')
        session = _get_db_session()
        for cod, nome, tipo, qtd_sinalizada in (
            (cod_origem, nome_origem, 'SAIDA', -qty),
            (cod_destino, nome_destino, 'ENTRADA', qty),
        ):
            mov = MovimentacaoEstoque()
            mov.cod_produto = cod
            mov.nome_produto = nome
            mov.tipo_movimentacao = tipo
            mov.local_movimentacao = 'AJUSTE'
            mov.qtd_movimentacao = qtd_sinalizada
            mov.data_movimentacao = hoje
            mov.lote_nome = lote_nome
            mov.tipo_origem = 'MANUAL'
            mov.observacao = obs
            mov.criado_por = usuario
            session.add(mov)
        session.commit()
