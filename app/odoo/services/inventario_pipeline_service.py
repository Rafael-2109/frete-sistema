"""InventarioPipelineService — orquestrador pipeline batch (5 metodos).

Cada metodo opera sobre uma colecao de ajustes/pickings/invoices em
paralelismo controlado por Semaphore (default max_concurrent=5):

    F5a  criar_pickings        — N pickings em paralelo
    F5b  validar_pickings      — confirmar + reservar + validar
    F5c  liberar_faturamento   — dispara robo CIEL IT
    F5d  aguardar_invoices     — 1 polling longo para todas
    F5e  transmitir_sefaz      — serial (1 browser Playwright)

Decisao arquitetural: docs/inventario-2026-05/00-decisoes/
D003-arquitetura-pipeline-batches.md
Spec: docs/superpowers/specs/2026-05-17-ajuste-inventario-nacom-lf-design.md
      §6.2 + §8.1.1
"""
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore
from typing import Dict, List, Optional

from app import db
from app.odoo.constants.locations import COMPANY_LOCATIONS
from app.odoo.constants.operacoes_fiscais import COMPANY_PARTNER_ID
from app.odoo.services.stock_picking_service import StockPickingService
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


# Mapeia acao_decidida (AjusteEstoqueInventario) -> (tipo_op, origem, destino)
ACAO_PARA_DIRECAO: Dict[str, tuple] = {
    'TRANSFERIR_CD_FB':       ('transf-filial',        4, 1),
    'TRANSFERIR_FB_CD':       ('transf-filial',        1, 4),
    'INDUSTRIALIZACAO_FB_LF': ('industrializacao',     1, 5),
    'PERDA_LF_FB':            ('perda',                5, 1),
    'DEV_FB_LF':              ('dev-industrializacao', 1, 5),
    'DEV_LF_FB':              ('dev-industrializacao', 5, 1),
    'DEV_CD_LF':              ('dev-industrializacao', 4, 5),
    'DEV_LF_CD':              ('dev-industrializacao', 5, 4),
}


# Mapping (company_origem, tipo_op) -> picking_type_id
# Hardcoded por enquanto. Auditoria 00e (F0) descobriu:
#   FB outgoing: 51 (entre filiais) | 53 (industrializacao) | 88 (copia)
#   CD outgoing: 55 (entre filiais) | 96 (retrabalho)
#   LF outgoing: 66 (industrializacao) | 94 (n. aplicado)
# G003 (SOT.md §3): mover este mapping para app/odoo/constants/picking_types.py
# se virar fonte de gotcha (Refinement futuro).
PICKING_TYPE_POR_DIRECAO: Dict[tuple, int] = {
    (1, 'transf-filial'):        51,  # FB: Expedicao Entre Filiais
    (4, 'transf-filial'):        55,  # CD: Expedicao Entre Filiais
    (1, 'industrializacao'):     53,  # FB: Expedicao Industrializacao
    (5, 'perda'):                94,  # LF: Expedicao N Aplicado
    (4, 'dev-industrializacao'): 96,  # CD: Retrabalho
    (5, 'dev-industrializacao'): 66,  # LF: Expedicao Industrializacao
    (1, 'dev-industrializacao'): 53,  # FB: idem industrializacao (P011 sem precedente)
}


class InventarioPipelineService:
    """Orquestrador batch do pipeline de ajuste de inventario."""

    def __init__(
        self,
        odoo=None,
        picking_svc=None,
        max_concurrent: int = 5,
        max_workers: int = 10,
    ):
        self.odoo = odoo or get_odoo_connection()
        self.picking_svc = picking_svc or StockPickingService(odoo=self.odoo)
        self.semaphore = Semaphore(max_concurrent)
        self.max_workers = max_workers

    # ============================================================
    # Helpers
    # ============================================================

    def _resolver_picking_type(self, company_origem: int, tipo_op: str) -> int:
        """Retorna picking_type_id Odoo para uma direcao.

        Raises:
            ValueError: se (company_origem, tipo_op) sem mapeamento.
        """
        key = (company_origem, tipo_op)
        pt = PICKING_TYPE_POR_DIRECAO.get(key)
        if pt is None:
            raise ValueError(
                f'picking_type sem mapeamento para {key}. '
                f'Validos: {sorted(PICKING_TYPE_POR_DIRECAO.keys())}'
            )
        return pt

    # ============================================================
    # F5a — criar_pickings
    # ============================================================

    def f5a_criar_pickings(
        self, ajustes: List, executado_por: str
    ) -> Dict[int, int]:
        """Cria pickings em paralelo (1 por ajuste).

        Idempotente: ajuste com picking_id_odoo ja preenchido eh skip.
        Paralelismo: ThreadPoolExecutor + Semaphore (max_concurrent).

        Args:
            ajustes: lista de AjusteEstoqueInventario.
            executado_por: usuario que disparou (auditoria).

        Returns:
            {ajuste_id: picking_id_odoo} — apenas dos casos com sucesso.
            Falhas marcam ajuste.fase_pipeline='F5a_FALHA' +
            ajuste.erro_msg.
        """
        result: Dict[int, int] = {}
        # Snapshot dos campos relevantes ANTES das threads. Threads
        # so fazem Odoo I/O (custo dominante); DB writes ficam na
        # thread principal para evitar problemas de pool de conexao /
        # savepoint isolado em tests.
        ajuste_index: Dict[int, object] = {a.id: a for a in ajustes}
        snapshots = [
            {
                'id': a.id,
                'acao_decidida': a.acao_decidida,
                'cod_produto': a.cod_produto,
                'qtd_ajuste': a.qtd_ajuste,
                'lote_inventariado': a.lote_inventariado,
                'lote_odoo': a.lote_odoo,
                'ciclo': a.ciclo,
                'picking_id_existente': a.picking_id_odoo,
            }
            for a in ajustes
        ]

        def _odoo_io(snap):
            """Trabalho Odoo I/O paralelo, SEM tocar DB local."""
            with self.semaphore:
                if snap['picking_id_existente']:
                    logger.info(
                        f"F5a skip ajuste {snap['id']} (picking_id_odoo"
                        f"={snap['picking_id_existente']} ja existe)"
                    )
                    return snap['id'], snap['picking_id_existente'], True

                acao = snap['acao_decidida']
                if acao not in ACAO_PARA_DIRECAO:
                    raise ValueError(
                        f'acao_decidida={acao!r} sem direcao mapeada '
                        'em ACAO_PARA_DIRECAO'
                    )
                tipo_op, origem, destino = ACAO_PARA_DIRECAO[acao]

                # Resolver product_id no Odoo via default_code
                products = self.odoo.search_read(
                    'product.product',
                    [['default_code', '=', snap['cod_produto']]],
                    ['id'],
                    limit=1,
                )
                if not products:
                    raise RuntimeError(
                        f"product.default_code={snap['cod_produto']!r} "
                        'nao encontrado no Odoo'
                    )
                product_id = products[0]['id']

                picking_type_id = self._resolver_picking_type(origem, tipo_op)
                location_origem = COMPANY_LOCATIONS[origem]
                # Location virtual "Parceiros/Clientes" descoberto audit 00e
                location_destino = 5
                partner_id = COMPANY_PARTNER_ID[destino]

                linhas = [{
                    'product_id': product_id,
                    'quantity': float(abs(snap['qtd_ajuste'])),
                    'lot_name': (
                        snap['lote_inventariado'] or snap['lote_odoo']
                    ),
                }]

                picking_id = self.picking_svc.criar_transferencia(
                    company_origem_id=origem,
                    company_destino_id=destino,
                    location_origem_id=location_origem,
                    location_destino_id=location_destino,
                    linhas=linhas,
                    picking_type_id=picking_type_id,
                    partner_id=partner_id,
                    origin=f"INV-{snap['ciclo']}-A{snap['id']:06d}",
                )
                return snap['id'], picking_id, False

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_odoo_io, s): s for s in snapshots}
            for fut in as_completed(futures):
                snap = futures[fut]
                ajuste = ajuste_index[snap['id']]
                try:
                    ajuste_id, picking_id, skipped = fut.result()
                    result[ajuste_id] = picking_id
                    if not skipped:
                        ajuste.picking_id_odoo = picking_id
                        ajuste.fase_pipeline = 'F5a_PICKING_CRIADO'
                        db.session.commit()
                        logger.info(
                            f'F5a ajuste {ajuste_id} ({snap["acao_decidida"]}) '
                            f'→ picking {picking_id} (por {executado_por})'
                        )
                except Exception as e:
                    ajuste.fase_pipeline = 'F5a_FALHA'
                    ajuste.erro_msg = str(e)
                    db.session.commit()
                    logger.error(
                        f'F5a falhou para ajuste {snap["id"]}: {e}'
                    )
        return result

    # ============================================================
    # F5b — validar_pickings
    # ============================================================

    def f5b_validar_pickings(
        self, ajustes: List
    ) -> Dict[int, bool]:
        """Para cada picking de cada ajuste: confirmar_e_reservar + validar.

        Recebe AjusteEstoqueInventario (com picking_id_odoo populado em
        F5a) em vez de picking_ids puros. Evita lookup por
        picking_id_odoo (que pode colidir em multiplos ciclos / re-runs).

        Odoo I/O paralelo, DB writes serial no main thread.

        Args:
            ajustes: lista de AjusteEstoqueInventario com picking_id_odoo
                populado (fase_pipeline >= F5a_PICKING_CRIADO).

        Returns:
            {picking_id: True (sucesso) | False (falha)}.
        """
        result: Dict[int, bool] = {}
        # Pre-indexar ajustes por picking_id e snapshot picking_ids
        ajuste_por_pid: Dict[int, object] = {
            a.picking_id_odoo: a for a in ajustes if a.picking_id_odoo
        }
        picking_ids = list(ajuste_por_pid.keys())

        def _io(pid):
            with self.semaphore:
                self.picking_svc.confirmar_e_reservar(pid)
                # Nota: nao chamamos preencher_qty_done aqui — Odoo ja
                # preenche via action_assign. Caso preciso de override
                # (ex.: lote especifico), expandir em iteracao futura.
                self.picking_svc.validar(pid)
                return pid

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_io, pid): pid for pid in picking_ids}
            for fut in as_completed(futures):
                pid = futures[fut]
                aj = ajuste_por_pid[pid]
                try:
                    fut.result()
                    result[pid] = True
                    aj.fase_pipeline = 'F5b_VALIDADO'
                    db.session.commit()
                    logger.info(
                        f'F5b picking {pid} validado (ajuste {aj.id})'
                    )
                except Exception as e:
                    result[pid] = False
                    aj.fase_pipeline = 'F5b_FALHA'
                    aj.erro_msg = str(e)
                    db.session.commit()
                    logger.error(f'F5b picking {pid} falhou: {e}')
        return result

    # ============================================================
    # F5c — liberar_faturamento
    # ============================================================

    def f5c_liberar_faturamento(
        self, ajustes: List
    ) -> Dict[int, bool]:
        """Dispara action_liberar_faturamento em todos pickings (paralelo).

        Apos esta etapa, robo CIEL IT comeca a criar invoices (F5d aguarda).

        Args:
            ajustes: lista de AjusteEstoqueInventario com picking_id_odoo
                populado (fase_pipeline >= F5b_VALIDADO).

        Returns:
            {picking_id: True | False}.
        """
        result: Dict[int, bool] = {}
        ajuste_por_pid: Dict[int, object] = {
            a.picking_id_odoo: a for a in ajustes if a.picking_id_odoo
        }
        picking_ids = list(ajuste_por_pid.keys())

        def _io(pid):
            with self.semaphore:
                self.picking_svc.liberar_faturamento(pid)
                return pid

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_io, pid): pid for pid in picking_ids}
            for fut in as_completed(futures):
                pid = futures[fut]
                aj = ajuste_por_pid[pid]
                try:
                    fut.result()
                    result[pid] = True
                    aj.fase_pipeline = 'F5c_LIBERADO'
                    db.session.commit()
                    logger.info(
                        f'F5c picking {pid} liberado (ajuste {aj.id})'
                    )
                except Exception as e:
                    result[pid] = False
                    aj.fase_pipeline = 'F5c_FALHA'
                    aj.erro_msg = str(e)
                    db.session.commit()
                    logger.error(f'F5c picking {pid} falhou: {e}')
        return result

    # ============================================================
    # F5d — aguardar_invoices (1 polling longo)
    # ============================================================

    def f5d_aguardar_invoices(
        self,
        ajustes: List,
        timeout: int = 1800,
        poll_interval: int = 40,
    ) -> Dict[int, Optional[int]]:
        """Aguarda robo CIEL IT criar invoices apos F5c.

        Estrategia: 1 polling longo (mais eficiente que N pollings
        independentes). Em cada iteracao, para cada picking ainda sem
        invoice, faz uma busca via aguardar_invoice_do_robo() com
        timeout curto (=poll_interval). Pickings ja resolvidos saem
        do conjunto de pendentes.

        Args:
            ajustes: lista de AjusteEstoqueInventario com
                picking_id_odoo populado (fase_pipeline >= F5c_LIBERADO).
            timeout: segundos totais ate desistir (default 30 min).
            poll_interval: segundos entre iteracoes (default 40s).

        Returns:
            {picking_id: invoice_id ou None se timeout}.
        """
        ajuste_por_pid: Dict[int, object] = {
            a.picking_id_odoo: a for a in ajustes if a.picking_id_odoo
        }
        pendentes = set(ajuste_por_pid.keys())
        resolved: Dict[int, Optional[int]] = {
            pid: None for pid in ajuste_por_pid
        }

        start = time.time()
        while pendentes and time.time() - start < timeout:
            for pid in list(pendentes):
                invoice_id = self.picking_svc.aguardar_invoice_do_robo(
                    pid, timeout=poll_interval, poll_interval=poll_interval
                )
                if invoice_id:
                    resolved[pid] = invoice_id
                    pendentes.discard(pid)
                    aj = ajuste_por_pid[pid]
                    aj.fase_pipeline = 'F5d_INVOICE_GERADA'
                    aj.invoice_id_odoo = invoice_id
                    db.session.commit()
                    logger.info(
                        f'F5d picking {pid} → invoice {invoice_id} '
                        f'(ajuste {aj.id})'
                    )
            if pendentes:
                logger.info(
                    f'F5d aguardando {len(pendentes)} pickings ainda '
                    f'(elapsed={int(time.time() - start)}s/{timeout}s)'
                )
                time.sleep(poll_interval)

        if pendentes:
            logger.warning(
                f'F5d timeout {timeout}s — {len(pendentes)} pickings '
                f'sem invoice: {sorted(pendentes)}'
            )
        return resolved
