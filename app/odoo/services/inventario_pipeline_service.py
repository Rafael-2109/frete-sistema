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


# Locations virtuais usadas como destino de pickings inter-company.
# Pickings outgoing exigem location_dest_id com company_id=False (shared).
# Descobertos em audit dos picking_types.default_location_dest_id (2026-05-18):
#   pt 53 FB Expedicao Industrializacao: dest=26489 (Em Transito Industrializacao)
#   pt 51 FB Expedicao Entre Filiais:    dest=6     (Em Transito Filiais)
#   pt 55 CD Expedicao Entre Filiais:    dest=6     (Em Transito Filiais)
#   pt 66 LF Expedicao Industrializacao: dest=5     (Parceiros/Clientes)
#   pt 94 LF Expedicao N Aplicado:       dest=5     (Parceiros/Clientes)
#   pt 96 CD Retrabalho:                 dest=26489 (Em Transito Industrializacao)
LOCATION_DESTINO_VIRTUAL_PARCEIROS = 5   # Parceiros/Clientes (perda LF→FB)
LOCATION_DESTINO_TRANSITO_FILIAIS = 6    # Em Transito (Filiais) — TRANSF_FILIAL
LOCATION_DESTINO_TRANSITO_INDUSTR = 26489  # Em Transito (Industrializacao)

# Mapeamento canonico por (company_origem, tipo_op) -> location virtual
# de destino. Validado contra default_location_dest_id de cada picking_type.
LOCATION_DESTINO_POR_DIRECAO = {
    (5, 'perda'):                5,      # LF→FB perda
    (1, 'industrializacao'):     26489,  # FB→LF industrializacao
    (5, 'industrializacao'):     5,      # LF retorno (pt 66 LF Exp Industr)
    (1, 'transf-filial'):        6,      # FB→CD
    (4, 'transf-filial'):        6,      # CD→FB
    (5, 'dev-industrializacao'): 5,      # LF retorna industr (pt 66)
    (4, 'dev-industrializacao'): 26489,  # CD retrabalho (pt 96)
    (1, 'dev-industrializacao'): 26489,  # FB dev industr (pt 53)
}


def resolver_location_destino(
    tipo_op: str, company_destino: int,
    company_origem: Optional[int] = None,
) -> int:
    """Resolve stock.location.id destino do picking conforme (tipo_op, origem).

    Para pickings inter-company, location_dest_id DEVE ser uma location
    virtual com company_id=False (Em Transito ou Parceiros), nunca a
    location interna da empresa destino — senao Odoo recusa com
    "Empresas incompativeis nos registros".

    Args:
        tipo_op: chave de MATRIZ_INTERCOMPANY.
        company_destino: company_id destino (mantido por backward compat).
        company_origem: company_id origem. Se nao informado, tenta inferir
            pelo tipo_op (fallback: 'perda'→5).

    Returns:
        stock.location.id (virtual em transito ou parceiros).

    Raises:
        ValueError: se (origem, tipo_op) sem mapeamento.
    """
    if company_origem is not None:
        key = (company_origem, tipo_op)
        if key in LOCATION_DESTINO_POR_DIRECAO:
            return LOCATION_DESTINO_POR_DIRECAO[key]
    # Backward compat (sem company_origem)
    if tipo_op == 'perda':
        return LOCATION_DESTINO_VIRTUAL_PARCEIROS
    if tipo_op == 'transf-filial':
        return LOCATION_DESTINO_TRANSITO_FILIAIS
    if tipo_op in ('industrializacao', 'dev-industrializacao'):
        return LOCATION_DESTINO_TRANSITO_INDUSTR
    raise ValueError(
        f'tipo_op={tipo_op!r} sem mapeamento de location destino. '
        f'company_origem={company_origem} company_destino={company_destino}'
    )


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

    # Lessons learned 2026-05-18 piloto 210030325 LF:
    # - Robo CIEL IT cria invoice sem payment_provider_id (Forma Pagamento)
    # - Sem isso, SEFAZ falha "Meio de pagamento nao configurado"
    # - NF historica 588209 usa payment_provider_id=38 (SEM PAGAMENTO)
    PAYMENT_PROVIDER_SEM_PAGAMENTO = 38

    # ============================================================
    # Helpers
    # ============================================================

    def _garantir_payment_provider(
        self, invoice_id: int, aj, executado_por: str,
    ) -> bool:
        """Garante que invoice tem payment_provider_id populado (idempotente).

        Setado para PAYMENT_PROVIDER_SEM_PAGAMENTO=38 ('SEM PAGAMENTO') —
        valor compativel com NFs de transferencia/perda inter-company
        (sem cobranca financeira). Necessario para SEFAZ Playwright.

        Args:
            invoice_id: account.move.id criada pelo robo CIEL IT
            aj: AjusteEstoqueInventario (para auditoria)
            executado_por: usuario

        Returns:
            True se setou (ou ja estava setado), False se falhou.
        """
        # Idempotencia: se ja tem payment_provider, skip
        try:
            current = self.odoo.read(
                'account.move', [invoice_id], ['payment_provider_id'],
            )
            if current and current[0].get('payment_provider_id'):
                logger.info(
                    f'payment_provider_id ja setado em invoice {invoice_id}: '
                    f'{current[0]["payment_provider_id"]} — skip.'
                )
                return True
        except Exception as e:
            logger.warning(f'check payment_provider_id falhou: {e}')

        # Setar via write (mesmo em state=posted — testado no piloto)
        try:
            self.odoo.write(
                'account.move', [invoice_id],
                {'payment_provider_id': self.PAYMENT_PROVIDER_SEM_PAGAMENTO},
            )
            logger.info(
                f'payment_provider_id={self.PAYMENT_PROVIDER_SEM_PAGAMENTO} '
                f'setado em invoice {invoice_id}'
            )
            self._registrar_op(
                ciclo=aj.ciclo, ajuste_id=aj.id, fase='F5d.5',
                acao='set_payment_provider', modelo_odoo='account.move',
                status='SUCESSO', executado_por=executado_por,
                odoo_id=invoice_id,
                payload={'payment_provider_id': self.PAYMENT_PROVIDER_SEM_PAGAMENTO},
            )
            return True
        except Exception as e:
            logger.error(
                f'write payment_provider_id em posted falhou: {e}. '
                'Tentando reset_to_draft + write + post...'
            )
            try:
                self.odoo.execute_kw(
                    'account.move', 'button_draft', [[invoice_id]],
                )
                self.odoo.write(
                    'account.move', [invoice_id],
                    {'payment_provider_id': self.PAYMENT_PROVIDER_SEM_PAGAMENTO},
                )
                self.odoo.execute_kw(
                    'account.move', 'action_post', [[invoice_id]],
                )
                logger.info(
                    f'payment_provider_id setado via reset_to_draft+post '
                    f'em invoice {invoice_id}'
                )
                self._registrar_op(
                    ciclo=aj.ciclo, ajuste_id=aj.id, fase='F5d.5',
                    acao='set_payment_provider', modelo_odoo='account.move',
                    status='SUCESSO', executado_por=executado_por,
                    odoo_id=invoice_id,
                    payload={
                        'payment_provider_id': self.PAYMENT_PROVIDER_SEM_PAGAMENTO,
                        'metodo': 'reset_to_draft+write+post',
                    },
                )
                return True
            except Exception as e2:
                self._registrar_op(
                    ciclo=aj.ciclo, ajuste_id=aj.id, fase='F5d.5',
                    acao='set_payment_provider', modelo_odoo='account.move',
                    status='FALHA', executado_por=executado_por,
                    odoo_id=invoice_id, erro_msg=str(e2),
                )
                return False

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
                location_destino = resolver_location_destino(
                    tipo_op, destino, company_origem=origem,
                )
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

    @staticmethod
    def _agrupar_por_picking(ajustes: List) -> Dict[int, List]:
        """Agrupa lista de ajustes por picking_id_odoo (suporta N ajustes/picking)."""
        grupo: Dict[int, List] = {}
        for a in ajustes:
            if a.picking_id_odoo:
                grupo.setdefault(a.picking_id_odoo, []).append(a)
            else:
                logger.warning(
                    f'  Skip ajuste {a.id} sem picking_id_odoo '
                    f'(fase={a.fase_pipeline})'
                )
        return grupo

    def f5b_validar_pickings(
        self, ajustes: List, executado_por: str = 'sistema'
    ) -> Dict[int, bool]:
        """Para cada picking distinto: confirmar_e_reservar + validar.

        Suporta multiplos ajustes por picking (1 picking com N produtos).
        Marca fase em TODOS os ajustes do mesmo picking.

        Args:
            ajustes: lista de AjusteEstoqueInventario com picking_id_odoo
                populado (fase_pipeline >= F5a_PICKING_CRIADO).

        Returns:
            {picking_id: True (sucesso) | False (falha)}.
        """
        result: Dict[int, bool] = {}
        ajustes_por_pid = self._agrupar_por_picking(ajustes)
        picking_ids = list(ajustes_por_pid.keys())

        def _io(pid):
            inicio = time.time()
            with self.semaphore:
                self.picking_svc.confirmar_e_reservar(pid)
                # Ajusta demand=qty_done quando ha divergencia (NAO infla
                # qty_done — apenas reduz demand). Pendencias retornadas
                # serao usadas pelo caller para gerar ajustes complementares.
                try:
                    result_ajuste = self.picking_svc.ajustar_qty_done_pelo_disponivel(pid)
                    if result_ajuste.get('pendencias'):
                        logger.warning(
                            f'Picking {pid}: {len(result_ajuste["pendencias"])} '
                            'moves com falta — gerar ajuste complementar.'
                        )
                except Exception as e:
                    logger.warning(
                        f'ajustar_qty_done falhou para picking {pid}: {e}. '
                        'Tentando validar mesmo assim.'
                    )
                self.picking_svc.validar(pid)
                return pid, int((time.time() - inicio) * 1000)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_io, pid): pid for pid in picking_ids}
            for fut in as_completed(futures):
                pid = futures[fut]
                ajustes_grupo = ajustes_por_pid[pid]
                try:
                    _pid_ret, tempo_ms = fut.result()
                    result[pid] = True
                    for aj in ajustes_grupo:
                        aj.fase_pipeline = 'F5b_VALIDADO'
                        self._registrar_op(
                            ciclo=aj.ciclo, ajuste_id=aj.id, fase='F5b',
                            acao='button_validate', modelo_odoo='stock.picking',
                            status='SUCESSO', executado_por=executado_por,
                            odoo_id=pid, tempo_ms=tempo_ms,
                        )
                    db.session.commit()
                    logger.info(
                        f'F5b picking {pid} validado ({len(ajustes_grupo)} ajustes)'
                    )
                except Exception as e:
                    result[pid] = False
                    for aj in ajustes_grupo:
                        aj.fase_pipeline = 'F5b_FALHA'
                        aj.erro_msg = str(e)[:500]
                        self._registrar_op(
                            ciclo=aj.ciclo, ajuste_id=aj.id, fase='F5b',
                            acao='button_validate', modelo_odoo='stock.picking',
                            status='FALHA', executado_por=executado_por,
                            odoo_id=pid, erro_msg=str(e),
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

        Suporta multiplos ajustes por picking. Marca fase em TODOS.

        Args:
            ajustes: lista de AjusteEstoqueInventario com picking_id_odoo
                populado (fase_pipeline >= F5b_VALIDADO).

        Returns:
            {picking_id: True | False}.
        """
        result: Dict[int, bool] = {}
        ajustes_por_pid = self._agrupar_por_picking(ajustes)
        picking_ids = list(ajustes_por_pid.keys())

        def _io(pid):
            inicio = time.time()
            with self.semaphore:
                self.picking_svc.liberar_faturamento(pid)
                return pid, int((time.time() - inicio) * 1000)

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {executor.submit(_io, pid): pid for pid in picking_ids}
            for fut in as_completed(futures):
                pid = futures[fut]
                ajustes_grupo = ajustes_por_pid[pid]
                try:
                    _pid_ret, tempo_ms = fut.result()
                    result[pid] = True
                    for aj in ajustes_grupo:
                        aj.fase_pipeline = 'F5c_LIBERADO'
                        self._registrar_op(
                            ciclo=aj.ciclo, ajuste_id=aj.id, fase='F5c',
                            acao='liberar_faturamento', modelo_odoo='stock.picking',
                            status='SUCESSO', executado_por=executado_por,
                            odoo_id=pid, tempo_ms=tempo_ms,
                        )
                    db.session.commit()
                    logger.info(
                        f'F5c picking {pid} liberado ({len(ajustes_grupo)} ajustes)'
                    )
                except Exception as e:
                    result[pid] = False
                    for aj in ajustes_grupo:
                        aj.fase_pipeline = 'F5c_FALHA'
                        aj.erro_msg = str(e)[:500]
                        self._registrar_op(
                            ciclo=aj.ciclo, ajuste_id=aj.id, fase='F5c',
                            acao='liberar_faturamento', modelo_odoo='stock.picking',
                            status='FALHA', executado_por=executado_por,
                            odoo_id=pid, erro_msg=str(e),
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
        ajustes_por_pid = self._agrupar_por_picking(ajustes)
        pendentes = set(ajustes_por_pid.keys())
        resolved: Dict[int, Optional[int]] = {
            pid: None for pid in ajustes_por_pid
        }

        start = time.time()
        inicio_por_pid = {pid: time.time() for pid in pendentes}
        while pendentes and time.time() - start < timeout:
            for pid in list(pendentes):
                invoice_id = self.picking_svc.aguardar_invoice_do_robo(
                    pid, timeout=poll_interval, poll_interval=poll_interval
                )
                if invoice_id:
                    resolved[pid] = invoice_id
                    pendentes.discard(pid)
                    ajustes_grupo = ajustes_por_pid[pid]
                    tempo_ms = int(
                        (time.time() - inicio_por_pid[pid]) * 1000
                    )
                    # Marca TODOS os ajustes do mesmo picking
                    for aj in ajustes_grupo:
                        aj.fase_pipeline = 'F5d_INVOICE_GERADA'
                        aj.invoice_id_odoo = invoice_id
                        self._registrar_op(
                            ciclo=aj.ciclo, ajuste_id=aj.id, fase='F5d',
                            acao='aguardar_invoice', modelo_odoo='account.move',
                            status='SUCESSO', executado_por=executado_por,
                            odoo_id=invoice_id,
                            resposta={'invoice_id': invoice_id, 'picking_id': pid},
                            tempo_ms=tempo_ms,
                        )
                    db.session.commit()
                    logger.info(
                        f'F5d picking {pid} → invoice {invoice_id} '
                        f'({len(ajustes_grupo)} ajustes)'
                    )
                    # F5d.5: garantir payment_provider_id na invoice
                    try:
                        self._garantir_payment_provider(
                            invoice_id, ajustes_grupo[0], executado_por,
                        )
                    except Exception as e:
                        logger.warning(
                            f'F5d.5 payment_provider write falhou para '
                            f'invoice {invoice_id}: {e}'
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
            for pid in pendentes:
                ajustes_grupo = ajustes_por_pid[pid]
                tempo_ms = int(
                    (time.time() - inicio_por_pid[pid]) * 1000
                )
                for aj in ajustes_grupo:
                    self._registrar_op(
                        ciclo=aj.ciclo, ajuste_id=aj.id, fase='F5d',
                        acao='aguardar_invoice', modelo_odoo='account.move',
                        status='TIMEOUT', executado_por=executado_por,
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
        # Idempotencia POR INVOICE (nao por ajuste): apos transmitir 1 NF,
        # todos os ajustes da mesma invoice sao pulados sem chamar Playwright
        # (1 invoice = 1 transmissao SEFAZ).
        invoices_processadas: Dict[int, Optional[str]] = {}

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

            # Se a invoice ja foi processada NESTE batch, replicar resultado
            # no ajuste atual (sem re-transmitir Playwright)
            if inv_id in invoices_processadas:
                chave_existente = invoices_processadas[inv_id]
                if chave_existente:
                    aj.fase_pipeline = 'F5e_SEFAZ_OK'
                    aj.chave_nfe = chave_existente
                    aj.status = 'EXECUTADO'
                else:
                    aj.fase_pipeline = 'F5e_FALHA'
                self._registrar_op(
                    ciclo=aj.ciclo, ajuste_id=aj.id, fase='F5e',
                    acao='transmitir_nfe', modelo_odoo='account.move',
                    status='SKIP_INV_PROC',  # max 20 chars (col VARCHAR 20)
                    executado_por=executado_por, odoo_id=inv_id,
                    resposta={'chave_nfe': chave_existente},
                )
                db.session.commit()
                logger.info(
                    f'F5e ajuste {aj.id} replicado de invoice {inv_id} '
                    f'(chave={chave_existente})'
                )
                continue

            # BUG-2: idempotency guard — NF-e ja transmitida (DB persistente)
            if aj.fase_pipeline == 'F5e_SEFAZ_OK' or aj.status == 'EXECUTADO':
                logger.info(
                    f'F5e skip ajuste {aj.id} (ja SEFAZ_OK, '
                    f'chave={aj.chave_nfe})'
                )
                if aj.chave_nfe:
                    result[inv_id] = aj.chave_nfe
                    invoices_processadas[inv_id] = aj.chave_nfe
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
                    invoices_processadas[inv_id] = chave_nfe  # idempotencia por invoice
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
                    invoices_processadas[inv_id] = None  # marca falha p/ proximos do mesmo invoice
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
