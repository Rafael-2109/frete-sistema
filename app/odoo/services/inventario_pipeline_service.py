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
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Semaphore
from typing import Any, Dict, List, Optional

from app import db
from app.odoo.constants.locations import COMPANY_LOCATIONS
from app.odoo.constants.operacoes_fiscais import COMPANY_PARTNER_ID
from app.odoo.models import OperacaoOdooAuditoria
from app.odoo.services.stock_picking_service import StockPickingService
from app.odoo.utils.connection import get_odoo_connection
from app.recebimento.services.playwright_nfe_transmissao import (
    transmitir_nfe_via_playwright,
)

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


# Location destino virtual "Parceiros/Clientes" (id=5), descoberto em
# audit 00e como destino real do tipo_op='perda' (LF perde estoque
# emitindo NF para parceiro virtual). Para outros tipo_op, o destino
# eh a location interna da company destino.
LOCATION_DESTINO_VIRTUAL_PARCEIROS = 5


def resolver_location_destino(tipo_op: str, company_destino: int) -> int:
    """Resolve stock.location.id destino do picking conforme tipo_op.

    - 'perda': location virtual "Parceiros/Clientes" (id=5). Audit 00e
      confirmou que LF emite NF de perda contra location virtual.
    - Demais (transf-filial / industrializacao / dev-industrializacao):
      location interna principal da company_destino (COMPANY_LOCATIONS).

    Args:
        tipo_op: chave de MATRIZ_INTERCOMPANY.
        company_destino: company_id destino.

    Returns:
        stock.location.id.

    Raises:
        ValueError: se company_destino sem entrada em COMPANY_LOCATIONS.
    """
    if tipo_op == 'perda':
        return LOCATION_DESTINO_VIRTUAL_PARCEIROS
    loc = COMPANY_LOCATIONS.get(company_destino)
    if loc is None:
        raise ValueError(
            f'COMPANY_LOCATIONS sem entrada para company_destino='
            f'{company_destino}; tipo_op={tipo_op!r}'
        )
    return loc


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

    def _registrar_op(
        self,
        *,
        ciclo: str,
        ajuste_id: int,
        fase: str,
        acao: str,
        modelo_odoo: str,
        status: str,
        executado_por: str,
        odoo_id: Optional[int] = None,
        payload: Optional[Dict[str, Any]] = None,
        resposta: Optional[Dict[str, Any]] = None,
        erro_msg: Optional[str] = None,
        tempo_ms: Optional[int] = None,
        screenshot_s3_key: Optional[str] = None,
    ) -> None:
        """Registra 1 row em operacao_odoo_auditoria para auditoria granular.

        external_id: f'INV-{ciclo}-A{ajuste_id:06d}-{fase}-{uuid8}' (unique).
        Caller decide commit (helper apenas flush).
        """
        try:
            OperacaoOdooAuditoria.registrar(
                external_id=(
                    f'INV-{ciclo}-A{ajuste_id:06d}-{fase}-'
                    f'{uuid.uuid4().hex[:8]}'
                ),
                tabela_origem='ajuste_estoque_inventario',
                registro_id=ajuste_id,
                acao=acao,
                modelo_odoo=modelo_odoo,
                odoo_id=odoo_id,
                etapa=5,  # F5 (pipeline batch)
                etapa_descricao=f'{fase} — {acao} {modelo_odoo}',
                status=status,
                payload_json=payload,
                resposta_json=resposta,
                erro_msg=erro_msg,
                tempo_execucao_ms=tempo_ms,
                pipeline_etapa=fase,
                screenshot_s3_key=screenshot_s3_key,
                contexto_origem='inventario',
                contexto_ref=ciclo,
                executado_por=executado_por,
            )
        except Exception as e:
            # Falha de auditoria nao deve quebrar o pipeline real
            logger.error(
                f'_registrar_op falhou (ajuste={ajuste_id}, fase={fase}): '
                f'{e}',
                exc_info=True,
            )

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
            """Trabalho Odoo I/O paralelo, SEM tocar DB local.

            Retorna dict com keys: ajuste_id, picking_id, skipped,
            payload, tempo_ms (para auditoria no main thread).
            """
            inicio = time.time()
            with self.semaphore:
                if snap['picking_id_existente']:
                    logger.info(
                        f"F5a skip ajuste {snap['id']} (picking_id_odoo"
                        f"={snap['picking_id_existente']} ja existe)"
                    )
                    return {
                        'ajuste_id': snap['id'],
                        'picking_id': snap['picking_id_existente'],
                        'skipped': True,
                        'payload': None,
                        'tempo_ms': int((time.time() - inicio) * 1000),
                    }

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
                location_destino = resolver_location_destino(tipo_op, destino)
                partner_id = COMPANY_PARTNER_ID[destino]

                linhas = [{
                    'product_id': product_id,
                    'quantity': float(abs(snap['qtd_ajuste'])),
                    'lot_name': (
                        snap['lote_inventariado'] or snap['lote_odoo']
                    ),
                }]

                payload = {
                    'company_origem_id': origem,
                    'company_destino_id': destino,
                    'location_origem_id': location_origem,
                    'location_destino_id': location_destino,
                    'picking_type_id': picking_type_id,
                    'partner_id': partner_id,
                    'linhas': linhas,
                    'origin': f"INV-{snap['ciclo']}-A{snap['id']:06d}",
                    'acao_decidida': acao,
                }

                picking_id = self.picking_svc.criar_transferencia(
                    company_origem_id=origem,
                    company_destino_id=destino,
                    location_origem_id=location_origem,
                    location_destino_id=location_destino,
                    linhas=linhas,
                    picking_type_id=picking_type_id,
                    partner_id=partner_id,
                    origin=payload['origin'],
                )
                return {
                    'ajuste_id': snap['id'],
                    'picking_id': picking_id,
                    'skipped': False,
                    'payload': payload,
                    'tempo_ms': int((time.time() - inicio) * 1000),
                }

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_odoo_io, s): s for s in snapshots}
            for fut in as_completed(futures):
                snap = futures[fut]
                ajuste = ajuste_index[snap['id']]
                try:
                    res = fut.result()
                    result[res['ajuste_id']] = res['picking_id']
                    if not res['skipped']:
                        ajuste.picking_id_odoo = res['picking_id']
                        ajuste.fase_pipeline = 'F5a_PICKING_CRIADO'
                        self._registrar_op(
                            ciclo=snap['ciclo'],
                            ajuste_id=res['ajuste_id'],
                            fase='F5a',
                            acao='create',
                            modelo_odoo='stock.picking',
                            status='SUCESSO',
                            executado_por=executado_por,
                            odoo_id=res['picking_id'],
                            payload=res['payload'],
                            resposta={'picking_id': res['picking_id']},
                            tempo_ms=res['tempo_ms'],
                        )
                        db.session.commit()
                        logger.info(
                            f'F5a ajuste {res["ajuste_id"]} '
                            f'({snap["acao_decidida"]}) '
                            f'→ picking {res["picking_id"]} '
                            f'(por {executado_por})'
                        )
                except Exception as e:
                    ajuste.fase_pipeline = 'F5a_FALHA'
                    ajuste.erro_msg = str(e)
                    self._registrar_op(
                        ciclo=snap['ciclo'],
                        ajuste_id=snap['id'],
                        fase='F5a',
                        acao='create',
                        modelo_odoo='stock.picking',
                        status='FALHA',
                        executado_por=executado_por,
                        erro_msg=str(e),
                    )
                    db.session.commit()
                    logger.error(
                        f'F5a falhou para ajuste {snap["id"]}: {e}'
                    )
        return result

    # ============================================================
    # F5b — validar_pickings
    # ============================================================

    def f5b_validar_pickings(
        self, ajustes: List, executado_por: str = 'sistema'
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
        # Pre-indexar ajustes por picking_id + WARNING em skip silencioso
        ajuste_por_pid: Dict[int, object] = {}
        for a in ajustes:
            if a.picking_id_odoo:
                ajuste_por_pid[a.picking_id_odoo] = a
            else:
                logger.warning(
                    f'F5b skip ajuste {a.id} sem picking_id_odoo '
                    f'(fase={a.fase_pipeline}) — provavelmente falha em F5a'
                )
        picking_ids = list(ajuste_por_pid.keys())

        def _io(pid):
            inicio = time.time()
            with self.semaphore:
                self.picking_svc.confirmar_e_reservar(pid)
                # Nota: nao chamamos preencher_qty_done aqui — Odoo ja
                # preenche via action_assign. Caso preciso de override
                # (ex.: lote especifico), expandir em iteracao futura.
                self.picking_svc.validar(pid)
                return pid, int((time.time() - inicio) * 1000)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_io, pid): pid for pid in picking_ids}
            for fut in as_completed(futures):
                pid = futures[fut]
                aj = ajuste_por_pid[pid]
                try:
                    pid_ret, tempo_ms = fut.result()
                    result[pid] = True
                    aj.fase_pipeline = 'F5b_VALIDADO'
                    self._registrar_op(
                        ciclo=aj.ciclo,
                        ajuste_id=aj.id,
                        fase='F5b',
                        acao='button_validate',
                        modelo_odoo='stock.picking',
                        status='SUCESSO',
                        executado_por=executado_por,
                        odoo_id=pid,
                        tempo_ms=tempo_ms,
                    )
                    db.session.commit()
                    logger.info(
                        f'F5b picking {pid} validado (ajuste {aj.id})'
                    )
                except Exception as e:
                    result[pid] = False
                    aj.fase_pipeline = 'F5b_FALHA'
                    aj.erro_msg = str(e)
                    self._registrar_op(
                        ciclo=aj.ciclo,
                        ajuste_id=aj.id,
                        fase='F5b',
                        acao='button_validate',
                        modelo_odoo='stock.picking',
                        status='FALHA',
                        executado_por=executado_por,
                        odoo_id=pid,
                        erro_msg=str(e),
                    )
                    db.session.commit()
                    logger.error(f'F5b picking {pid} falhou: {e}')
        return result

    # ============================================================
    # F5c — liberar_faturamento
    # ============================================================

    def f5c_liberar_faturamento(
        self, ajustes: List, executado_por: str = 'sistema'
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
        ajuste_por_pid: Dict[int, object] = {}
        for a in ajustes:
            if a.picking_id_odoo:
                ajuste_por_pid[a.picking_id_odoo] = a
            else:
                logger.warning(
                    f'F5c skip ajuste {a.id} sem picking_id_odoo '
                    f'(fase={a.fase_pipeline}) — provavelmente falha anterior'
                )
        picking_ids = list(ajuste_por_pid.keys())

        def _io(pid):
            inicio = time.time()
            with self.semaphore:
                self.picking_svc.liberar_faturamento(pid)
                return pid, int((time.time() - inicio) * 1000)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_io, pid): pid for pid in picking_ids}
            for fut in as_completed(futures):
                pid = futures[fut]
                aj = ajuste_por_pid[pid]
                try:
                    pid_ret, tempo_ms = fut.result()
                    result[pid] = True
                    aj.fase_pipeline = 'F5c_LIBERADO'
                    self._registrar_op(
                        ciclo=aj.ciclo,
                        ajuste_id=aj.id,
                        fase='F5c',
                        acao='liberar_faturamento',
                        modelo_odoo='stock.picking',
                        status='SUCESSO',
                        executado_por=executado_por,
                        odoo_id=pid,
                        tempo_ms=tempo_ms,
                    )
                    db.session.commit()
                    logger.info(
                        f'F5c picking {pid} liberado (ajuste {aj.id})'
                    )
                except Exception as e:
                    result[pid] = False
                    aj.fase_pipeline = 'F5c_FALHA'
                    aj.erro_msg = str(e)
                    self._registrar_op(
                        ciclo=aj.ciclo,
                        ajuste_id=aj.id,
                        fase='F5c',
                        acao='liberar_faturamento',
                        modelo_odoo='stock.picking',
                        status='FALHA',
                        executado_por=executado_por,
                        odoo_id=pid,
                        erro_msg=str(e),
                    )
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
        executado_por: str = 'sistema',
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
        ajuste_por_pid: Dict[int, object] = {}
        for a in ajustes:
            if a.picking_id_odoo:
                ajuste_por_pid[a.picking_id_odoo] = a
            else:
                logger.warning(
                    f'F5d skip ajuste {a.id} sem picking_id_odoo '
                    f'(fase={a.fase_pipeline}) — provavelmente falha anterior'
                )
        pendentes = set(ajuste_por_pid.keys())
        resolved: Dict[int, Optional[int]] = {
            pid: None for pid in ajuste_por_pid
        }

        start = time.time()
        # Tempos de inicio de cada picking (para registrar tempo_ms ao
        # achar a invoice)
        inicio_por_pid = {pid: time.time() for pid in pendentes}
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
                    tempo_ms = int(
                        (time.time() - inicio_por_pid[pid]) * 1000
                    )
                    self._registrar_op(
                        ciclo=aj.ciclo,
                        ajuste_id=aj.id,
                        fase='F5d',
                        acao='aguardar_invoice',
                        modelo_odoo='account.move',
                        status='SUCESSO',
                        executado_por=executado_por,
                        odoo_id=invoice_id,
                        resposta={
                            'invoice_id': invoice_id, 'picking_id': pid,
                        },
                        tempo_ms=tempo_ms,
                    )
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
            # Registrar timeout para auditoria
            for pid in pendentes:
                aj = ajuste_por_pid[pid]
                tempo_ms = int(
                    (time.time() - inicio_por_pid[pid]) * 1000
                )
                self._registrar_op(
                    ciclo=aj.ciclo,
                    ajuste_id=aj.id,
                    fase='F5d',
                    acao='aguardar_invoice',
                    modelo_odoo='account.move',
                    status='TIMEOUT',
                    executado_por=executado_por,
                    erro_msg=f'timeout {timeout}s — robo CIEL IT nao criou invoice',
                    tempo_ms=tempo_ms,
                )
                db.session.commit()
        return resolved

    # ============================================================
    # F5e — transmitir_sefaz (serial via Playwright)
    # ============================================================

    # Erros de configuracao que devem abortar o batch inteiro
    # (nao adianta tentar a proxima invoice — o ambiente esta quebrado)
    HARD_FAIL_CONFIG_ERRORS = {
        'playwright_indisponivel',
        'odoo_password_ausente',
        'odoo_username_ausente',
    }

    def f5e_transmitir_sefaz(
        self, ajustes: List, executado_por: str = 'sistema'
    ) -> Dict[int, Optional[str]]:
        """Transmite NF-e para SEFAZ via Playwright (serial, 1 browser).

        Reusa app/recebimento/services/playwright_nfe_transmissao
        .transmitir_nfe_via_playwright(invoice_id, odoo, logger) que
        retorna dict (vide assinatura completa naquele modulo).

        Idempotente: skip se ajuste ja em F5e_SEFAZ_OK ou
        status=EXECUTADO (NF-e ja transmitida — reprocessar abre
        Playwright sem necessidade).

        Iteracao serial — uma NF-e por vez (1 browser Playwright).
        Worst case: 100 ajustes × 15 tentativas × 120s = ~45h.

        Abort batch: se Playwright/Odoo indisponivel (config errors
        com tentativas=0), lanca RuntimeError para sinalizar ao
        operador que o ambiente esta quebrado.

        Args:
            ajustes: lista de AjusteEstoqueInventario com
                invoice_id_odoo populado (fase_pipeline >= F5d_INVOICE_GERADA).

        Returns:
            {invoice_id: chave_nf (sucesso) | None (falha)}.

        Raises:
            RuntimeError: se erro de config detectado (abort batch).
        """
        result: Dict[int, Optional[str]] = {}

        for aj in ajustes:
            inv_id = aj.invoice_id_odoo

            # MED B-2: skip silencioso virou WARNING (sinal de F5d timeout)
            if not inv_id:
                logger.warning(
                    f'F5e skip ajuste {aj.id} sem invoice_id_odoo '
                    f'(fase={aj.fase_pipeline}). Provavelmente timeout '
                    'em F5d.'
                )
                self._registrar_op(
                    ciclo=aj.ciclo, ajuste_id=aj.id, fase='F5e',
                    acao='transmitir_nfe', modelo_odoo='account.move',
                    status='SKIPPED', executado_por=executado_por,
                    erro_msg='sem invoice_id_odoo (provavelmente F5d timeout)',
                )
                db.session.commit()
                continue

            # BUG-2: idempotency guard — NF-e ja transmitida nao precisa Playwright
            if aj.fase_pipeline == 'F5e_SEFAZ_OK' or aj.status == 'EXECUTADO':
                logger.info(
                    f'F5e skip ajuste {aj.id} (ja SEFAZ_OK, '
                    f'chave={aj.chave_nfe})'
                )
                if aj.chave_nfe:
                    result[inv_id] = aj.chave_nfe
                self._registrar_op(
                    ciclo=aj.ciclo, ajuste_id=aj.id, fase='F5e',
                    acao='transmitir_nfe', modelo_odoo='account.move',
                    status='SKIPPED_IDEMPOTENT', executado_por=executado_por,
                    odoo_id=inv_id,
                    resposta={'chave_nfe': aj.chave_nfe},
                )
                db.session.commit()
                continue

            inicio = time.time()
            try:
                resultado = transmitir_nfe_via_playwright(
                    inv_id, self.odoo, logger
                )
                tempo_ms = int((time.time() - inicio) * 1000)

                # BUG-3: detectar erros de config e abortar batch
                if (
                    not resultado.get('sucesso')
                    and resultado.get('tentativas') == 0
                    and resultado.get('erro') in self.HARD_FAIL_CONFIG_ERRORS
                ):
                    erro = resultado['erro']
                    aj.fase_pipeline = 'F5e_FALHA'
                    aj.erro_msg = f'Config invalida: {erro}'
                    self._registrar_op(
                        ciclo=aj.ciclo, ajuste_id=aj.id, fase='F5e',
                        acao='transmitir_nfe', modelo_odoo='account.move',
                        status='FALHA_CONFIG', executado_por=executado_por,
                        odoo_id=inv_id, resposta=resultado, erro_msg=erro,
                        tempo_ms=tempo_ms,
                    )
                    db.session.commit()
                    raise RuntimeError(
                        f'F5e abortado: configuracao invalida — {erro}. '
                        f'{len(ajustes) - len(result) - 1} ajustes nao '
                        'processados.'
                    )

                if resultado.get('sucesso'):
                    chave_nfe = resultado.get('chave_nf')
                    result[inv_id] = chave_nfe
                    aj.fase_pipeline = 'F5e_SEFAZ_OK'
                    aj.chave_nfe = chave_nfe
                    aj.status = 'EXECUTADO'
                    # MED C-1: registrar excecao_autorizado para audit fiscal
                    situacao = resultado.get('situacao_nf')
                    if situacao and situacao != 'autorizado':
                        aj.erro_msg = (
                            f'{situacao} tentativa='
                            f'{resultado.get("tentativa", "?")}'
                        )
                    self._registrar_op(
                        ciclo=aj.ciclo, ajuste_id=aj.id, fase='F5e',
                        acao='transmitir_nfe', modelo_odoo='account.move',
                        status='SUCESSO', executado_por=executado_por,
                        odoo_id=inv_id, resposta=resultado,
                        tempo_ms=tempo_ms,
                    )
                    db.session.commit()
                    logger.info(
                        f'F5e invoice {inv_id} → SEFAZ OK '
                        f'(chave={chave_nfe}, situacao={situacao}, '
                        f'ajuste {aj.id})'
                    )
                else:
                    erro = resultado.get('erro', 'erro_desconhecido')
                    result[inv_id] = None
                    aj.fase_pipeline = 'F5e_FALHA'
                    # MED C-2: persistir cstat/xmotivo de ultimo_estado
                    # (rejeicao SEFAZ — campo mais acionavel)
                    ultimo = resultado.get('ultimo_estado') or {}
                    aj.erro_msg = (
                        f"SEFAZ falhou: {erro} "
                        f"(tentativas={resultado.get('tentativas', '?')}, "
                        f"cstat={ultimo.get('cstat')}, "
                        f"xmotivo={ultimo.get('xmotivo')})"
                    )
                    self._registrar_op(
                        ciclo=aj.ciclo, ajuste_id=aj.id, fase='F5e',
                        acao='transmitir_nfe', modelo_odoo='account.move',
                        status='FALHA', executado_por=executado_por,
                        odoo_id=inv_id, resposta=resultado,
                        erro_msg=aj.erro_msg, tempo_ms=tempo_ms,
                    )
                    db.session.commit()
                    logger.error(
                        f'F5e invoice {inv_id} falhou: {erro} '
                        f'(cstat={ultimo.get("cstat")}, '
                        f'xmotivo={ultimo.get("xmotivo")})'
                    )
            except RuntimeError:
                # Re-raise para o caller decidir (abort batch acima)
                raise
            except Exception as e:
                tempo_ms = int((time.time() - inicio) * 1000)
                result[inv_id] = None
                aj.fase_pipeline = 'F5e_FALHA'
                aj.erro_msg = str(e)
                self._registrar_op(
                    ciclo=aj.ciclo, ajuste_id=aj.id, fase='F5e',
                    acao='transmitir_nfe', modelo_odoo='account.move',
                    status='EXCECAO', executado_por=executado_por,
                    odoo_id=inv_id, erro_msg=str(e), tempo_ms=tempo_ms,
                )
                db.session.commit()
                logger.error(
                    f'F5e excecao na invoice {inv_id}: {e}',
                    exc_info=True,
                )
        return result
