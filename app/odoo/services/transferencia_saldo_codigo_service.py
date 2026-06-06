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

    def transferir_v2(
        self, *,
        company_id: int,
        cod_origem, location_id_origem: int, lote_nome_origem,
        cod_destino, location_id_destino: int, lote_nome_destino,
        qty, usuario, dry_run: bool = False,
    ) -> Dict[str, Any]:
        """Transferência genérica de saldo entre códigos (qualquer empresa/local/lote).

        Generaliza transferir() (CD-only): parametriza company_id + locations +
        lotes origem/destino. A trava de par vira AVISO (r['aviso_par']) — NÃO
        bloqueia. dry_run=True simula (não cria lote, não grava espelho local).
        Reduz origem → cria/aumenta destino (compensa se o aumento falhar).
        """
        cod_origem, cod_destino = str(cod_origem).strip(), str(cod_destino).strip()
        qty = round(float(qty), CASAS)
        r: Dict[str, Any] = {
            'cod_origem': cod_origem, 'cod_destino': cod_destino,
            'company_id': company_id,
            'location_id_origem': location_id_origem,
            'location_id_destino': location_id_destino,
            'lote_nome_origem': lote_nome_origem,
            'lote_nome_destino': lote_nome_destino,
            'qty': qty, 'usuario': usuario, 'dry_run': dry_run,
            'lote_criado': False, 'aviso_par': False, 'status': None,
        }
        if qty <= 0:
            raise ValueError(f'qty deve ser > 0 (recebido {qty})')

        # 1. aviso de par (NÃO bloqueia — D2)
        destinos = {d['codigo'] for d in self.descobrir_destinos(cod_origem)}
        r['aviso_par'] = cod_destino not in destinos

        # 2. resolver produtos
        origem = self.resolver_produto(cod_origem)
        destino = self.resolver_produto(cod_destino)
        pid_o, pid_d = origem['product_id'], destino['product_id']

        # 3. resolver lote origem + validade (para herdar no destino)
        lot_id_origem: Optional[int] = None
        validade: Optional[str] = None
        if lote_nome_origem:
            lot_id_origem = self.lot_svc.buscar_por_nome(lote_nome_origem, pid_o, company_id)
            if not lot_id_origem:
                raise ValueError(
                    f'lote {lote_nome_origem!r} nao encontrado no produto '
                    f'{cod_origem} (company {company_id})')
            lots = self.odoo.read('stock.lot', [lot_id_origem], ['expiration_date'])
            validade = (lots[0].get('expiration_date') or None) if lots else None

        # 4. reduzir origem
        r_red = self.adjustment_svc.ajustar_quant(
            product_id=pid_o, company_id=company_id, location_id=location_id_origem,
            lot_id=lot_id_origem, delta=-qty, delta_esperado=-qty, tolerancia_delta=0.001,
            validar_nao_negativar=True, validar_nao_abaixo_reserva=True, dry_run=dry_run)
        r['reducao'] = r_red
        if r_red['status'] not in ('EXECUTADO', 'DRY_RUN_OK', 'EXECUTADO_AUTO_CORRIGIDO'):
            r['status'] = 'FALHA_REDUCAO'
            r['erro'] = r_red.get('erro')
            return r
        r['origem_antes'], r['origem_apos'] = r_red.get('qty_antes'), r_red.get('qty_apos')

        # 5. resolver/garantir lote destino no produto destino
        lot_id_destino: Optional[int] = None
        if lote_nome_destino:
            exp = validade if destino['use_expiration_date'] else None
            if dry_run:
                lot_id_destino = self.lot_svc.buscar_por_nome(lote_nome_destino, pid_d, company_id)
                r['lote_criado'] = lot_id_destino is None
            else:
                lot_id_destino, criado = self.lot_svc.criar_se_nao_existe(
                    lote_nome_destino, pid_d, company_id, expiration_date=exp)
                r['lote_criado'] = criado

        # 6. aumentar destino
        if dry_run and lote_nome_destino and lot_id_destino is None:
            # lote será criado no executar; quant nova começa em 0 → preview manual
            r['destino_antes'], r['destino_apos'] = 0.0, qty
            r['aumento'] = {'status': 'DRY_RUN_OK', 'qty_antes': 0.0,
                            'qty_apos': qty, 'acao': 'created'}
            r['status'] = 'DRY_RUN_OK'
            return r

        r_aum = self.adjustment_svc.ajustar_quant(
            product_id=pid_d, company_id=company_id, location_id=location_id_destino,
            lot_id=lot_id_destino, delta=qty, delta_esperado=qty, tolerancia_delta=0.001,
            criar_se_faltar=True, validar_nao_negativar=True,
            validar_nao_abaixo_reserva=True, dry_run=dry_run)
        r['aumento'] = r_aum
        if r_aum['status'] not in ('EXECUTADO', 'DRY_RUN_OK', 'EXECUTADO_AUTO_CORRIGIDO'):
            if not dry_run:
                comp = self.adjustment_svc.ajustar_quant(
                    product_id=pid_o, company_id=company_id, location_id=location_id_origem,
                    lot_id=lot_id_origem, delta=qty,
                    validar_nao_negativar=False, validar_nao_abaixo_reserva=False)
                r['compensacao'] = comp
            r['status'] = 'FALHA_AUMENTO_COMPENSADO'
            r['erro'] = r_aum.get('erro')
            return r
        r['destino_antes'], r['destino_apos'] = r_aum.get('qty_antes'), r_aum.get('qty_apos')

        # 7. espelho local (somente executar real — D8)
        if not dry_run:
            self._registrar_movimentacao_local(
                cod_origem, origem['name'], cod_destino, destino['name'],
                lote_nome_destino or lote_nome_origem, qty, usuario)
        r['status'] = 'DRY_RUN_OK' if dry_run else 'EXECUTADO'
        return r

    def transferir(self, cod_origem, cod_destino, lote_nome, qty,
                   usuario) -> Dict[str, Any]:
        """LEGADO (CD/Estoque, par obrigatório). Delega a transferir_v2.

        Mantém o contrato histórico: BLOQUEIA se cod_destino não é par em
        UnificacaoCodigos; usa CD/Estoque (company 4, loc 32) e o mesmo lote
        na origem e no destino. Callers: app/estoque/routes.py (tela legada).
        """
        cod_origem, cod_destino = str(cod_origem).strip(), str(cod_destino).strip()
        if round(float(qty), CASAS) <= 0:
            raise ValueError(f'qty deve ser > 0 (recebido {qty})')
        # trava dura legada: bloqueia par não-cadastrado
        destinos = {d['codigo'] for d in self.descobrir_destinos(cod_origem)}
        if cod_destino not in destinos:
            raise ValueError(
                f'{cod_destino} nao e par de {cod_origem} em UnificacaoCodigos ativa')
        return self.transferir_v2(
            company_id=self.CD_COMPANY_ID, cod_origem=cod_origem,
            location_id_origem=self.CD_ESTOQUE_LOC, lote_nome_origem=lote_nome,
            cod_destino=cod_destino, location_id_destino=self.CD_ESTOQUE_LOC,
            lote_nome_destino=lote_nome, qty=qty, usuario=usuario, dry_run=False)

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
