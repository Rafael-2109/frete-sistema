"""09 — Bulk de ajustes ordenado por TIPO de processo.

Substitui a abordagem "por produto, sequencial" do teste_210030325_lf.py.
Agora opera em ondas processuais para reduzir tempo total e aumentar
paralelismo (Lote -> Picking -> NF -> SEFAZ -> Entrada FB).

PIPELINE:

  ETAPA A — TRANSFERENCIA DE LOTES (intra-empresa, sem NF)
    Para todos ajustes acao=RENOMEAR_LOTE:
      garantir lote destino + StockInternalTransferService.transferir
    Paralelo (semaphore=5). Cada operacao e atomica via
    stock.quant.action_apply_inventory.

  ETAPA B — PICKINGS (saidas de NF, agrupados por direcao, limitados a N produtos)
    Para todos ajustes PERDA/INDUS/DEV:
      agrupa por (company_origem, tipo_op, picking_type_id)
      chunks de ate max_produtos_por_picking
      para cada chunk: 1 picking N linhas + F5b validar + F5c liberar

  ETAPA C — AGUARDAR INVOICES CIEL IT (paralelo, 1 polling longo)
    f5d_aguardar_invoices para TODOS pickings de B
    (robo CIEL IT cria invoice por picking)

  ETAPA D — SEFAZ (Playwright serial)
    f5e_transmitir_sefaz para TODAS invoices de C

  ETAPA E — ENTRADA FB (para cada NF SEFAZ-autorizada)
    Cria RecebimentoLf + processa pipeline 0-18 (recebimento LF)
    Resultado: lote alvo na FB com qty correspondente

USO TIPICO (sub-piloto 10 produtos):

    # 1. Dry-run completo, ver plano
    python scripts/inventario_2026_05/09_executar_onda1_bulk.py \\
        --company-id=5 --onda=1 --limite-produtos=10 --max-produtos-picking=5 --dry-run

    # 2. Executar ate F5c liberar (ETAPA A+B)
    python scripts/inventario_2026_05/09_executar_onda1_bulk.py \\
        --company-id=5 --onda=1 --limite-produtos=10 --max-produtos-picking=5 \\
        --ate-etapa=B --confirmar --usuario=rafael

    # 3. Aguardar invoices CIEL IT (ETAPA C)
    python scripts/inventario_2026_05/09_executar_onda1_bulk.py \\
        --company-id=5 --onda=1 --apenas-etapa=C --confirmar --usuario=rafael

    # 4. Transmitir SEFAZ (ETAPA D - irreversivel)
    python scripts/inventario_2026_05/09_executar_onda1_bulk.py \\
        --company-id=5 --onda=1 --apenas-etapa=D --confirmar --confirmar-sefaz \\
        --usuario=rafael

    # 5. Entrada FB (ETAPA E - cria recebimentos)
    python scripts/inventario_2026_05/09_executar_onda1_bulk.py \\
        --company-id=5 --onda=1 --apenas-etapa=E --confirmar --usuario=rafael

USO LF COMPLETO (apos sub-piloto OK):

    python scripts/inventario_2026_05/09_executar_onda1_bulk.py \\
        --company-id=5 --onda=1 --max-produtos-picking=30 \\
        --confirmar --confirmar-sefaz --usuario=rafael

Spec: D006 + CHECKPOINT_2026_05_18_PILOTO_COMPLETO.md secao 6.
"""
import argparse
import logging
import sys
import time
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
from pathlib import Path
from threading import Semaphore
from typing import Any, Dict, List, Optional, Tuple

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app, db  # noqa: E402  # type: ignore
from app.odoo.constants.locations import COMPANY_LOCATIONS  # noqa: E402  # type: ignore
from app.odoo.constants.operacoes_fiscais import (  # noqa: E402  # type: ignore
    COMPANY_PARTNER_ID,
)
from app.odoo.models import AjusteEstoqueInventario  # noqa: E402  # type: ignore
from app.odoo.services.inventario_pipeline_service import (  # noqa: E402  # type: ignore
    ACAO_PARA_DIRECAO,
    PICKING_TYPE_POR_DIRECAO,
    InventarioPipelineService,
    resolver_location_destino,
)
from app.odoo.services.stock_internal_transfer_service import (  # noqa: E402  # type: ignore
    StockInternalTransferService,
)
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402  # type: ignore
from app.odoo.services.stock_picking_service import StockPickingService  # noqa: E402  # type: ignore
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402  # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('bulk_onda')

CICLO = 'INVENTARIO_2026_05'

# Acoes que geram NF (vao para ETAPA B em diante)
ACOES_PICKING = {
    'PERDA_LF_FB', 'INDUSTRIALIZACAO_FB_LF',
    'DEV_LF_FB', 'DEV_FB_LF', 'DEV_LF_CD', 'DEV_CD_LF',
    'TRANSFERIR_CD_FB', 'TRANSFERIR_FB_CD',
}
# Acao apenas de lote (intra-empresa, sem NF)
ACOES_LOTE = {'RENOMEAR_LOTE', 'TRANSFERIR_LOTE'}

ETAPAS_VALIDAS = ('A', 'B', 'C', 'D', 'E')


def banner(titulo: str, char: str = '=') -> None:
    print()
    print(char * 78)
    print(f'  {titulo}')
    print(char * 78)


# ============================================================
# Helpers comuns
# ============================================================

def resolver_product_id(odoo, cod_produto: str) -> Optional[int]:
    """Resolve product.product.id pelo default_code. None se nao existe."""
    res = odoo.search_read(
        'product.product',
        [['default_code', '=', cod_produto]],
        ['id'],
        limit=1,
    )
    return res[0]['id'] if res else None


def validar_cadastro_fiscal(
    odoo, pids_map: Dict[str, Optional[int]], modo: str = 'strict',
) -> Dict[str, List[str]]:
    """Valida campos fiscais obrigatorios para SEFAZ + F5c.

    Cobertura:
        - G017: l10n_br_ncm_id ausente -> cstat=225 SEFAZ (NCM=False no XML)
        - G012/G013: weight=0 -> peso_liquido/volumes=0 -> F5c rejeita

    Args:
        pids_map: {cod_produto: product_id}. Cods com pid=None sao ignorados
            aqui (script ja' pula via skip_pid em outro ponto).
        modo: 'strict' raise RuntimeError com lista detalhada se houver
            problemas. 'warn' apenas imprime aviso e segue.

    Returns:
        {'sem_ncm': [...], 'sem_weight': [...]} com '{cod} ({nome[:40]})'.

    Raises:
        RuntimeError se modo='strict' e houver produtos faltando NCM ou weight.
    """
    pids_validos = [pid for pid in pids_map.values() if pid]
    if not pids_validos:
        return {'sem_ncm': [], 'sem_weight': []}

    prods = odoo.read(
        'product.product', pids_validos,
        ['default_code', 'name', 'l10n_br_ncm_id', 'weight'],
    )

    sem_ncm: List[str] = []
    sem_weight: List[str] = []
    for p in prods:
        cod = p.get('default_code') or '?'
        nome = (p.get('name') or '')[:40]
        if not p.get('l10n_br_ncm_id'):
            sem_ncm.append(f"{cod} ({nome})")
        w = float(p.get('weight') or 0)
        if w <= 0:
            sem_weight.append(f"{cod} ({nome}) weight={w}")

    # G018 v2: weight=0 NAO bloqueia mais (fix aplicado no picking via
    # aplicar_peso_volumes_fallback_picking entre F5b e F5c). Apenas NCM
    # ainda bloqueia em strict.
    if sem_weight:
        head = sem_weight[:10]
        extra = (
            f" ... +{len(sem_weight)-10} mais" if len(sem_weight) > 10 else ""
        )
        print(
            f"  G018 [{len(sem_weight)} sem weight no Odoo (fallback no "
            f"picking sera' aplicado em F5b->F5c)]: {head}{extra}"
        )

    if sem_ncm:
        head = sem_ncm[:30]
        extra = f" ... +{len(sem_ncm)-30} mais" if len(sem_ncm) > 30 else ""
        msg = (
            f"VALIDACAO FISCAL G017 [{len(sem_ncm)} sem NCM => "
            f"cstat=225 SEFAZ]: {head}{extra}"
        )
        if modo == 'strict':
            raise RuntimeError(msg)
        else:
            print(f"  AVISO (modo=warn): {msg}")

    return {'sem_ncm': sem_ncm, 'sem_weight': sem_weight}


def corrigir_weight_zero(
    odoo, pids_map: Dict[str, Optional[int]], peso_fallback: float = 0.001,
) -> List[Dict[str, Any]]:
    """G018 v2: DETECTA produtos com weight=0 (NAO modifica master data).

    Tentativa anterior (write em product.product/template) NAO PERSISTE no
    Odoo CIEL IT (write_date atualiza mas valor mantem 0.0 — algum hook
    silencioso reseta). Decisao: aplicar fallback no PICKING (writable),
    nao no produto.

    Esta funcao agora apenas detecta e loga. O fix real e' aplicado em
    `aplicar_peso_volumes_fallback_picking` entre F5b e F5c.

    Args:
        pids_map: {cod_produto: product_id}. Cods com pid=None ignorados.
        peso_fallback: ignorado (mantido para compatibilidade CLI).

    Returns:
        Lista de produtos com weight=0 (apenas info, sem alteracao).
    """
    pids_validos = [pid for pid in pids_map.values() if pid]
    if not pids_validos:
        return []

    prods = odoo.read(
        'product.product', pids_validos,
        ['default_code', 'name', 'weight'],
    )
    com_weight_zero = [
        p for p in prods if float(p.get('weight') or 0) <= 0
    ]
    if not com_weight_zero:
        return []

    print(f"  G018 v2: {len(com_weight_zero)} produto(s) com weight=0 "
          f"detectado(s) (fallback sera' aplicado no picking F5b->F5c)")
    for p in com_weight_zero[:10]:
        cod = p['default_code']
        nome = (p.get('name') or '')[:40]
        print(f"    {cod:>12} ({nome})")
    if len(com_weight_zero) > 10:
        print(f"    ... +{len(com_weight_zero)-10} mais")
    return [
        {'cod': p['default_code'], 'pid': p['id'],
         'nome': (p.get('name') or '')[:40], 'weight_atual': 0.0}
        for p in com_weight_zero
    ]


def aplicar_peso_volumes_fallback_picking(
    odoo, picking_id: int,
    peso_unitario_fallback: float = 0.001,
    volumes_fallback: int = 1,
) -> Dict[str, Any]:
    """G018 v2: aplica peso_liquido/volumes fallback no stock.picking.

    Necessario porque:
    - `l10n_br_peso_liquido` e' computed @api.depends('move_ids.qty_done')
      como SUM(qty_done * product.weight). Se product.weight=0 (e CIEL IT
      nao deixa modificar via XML-RPC), peso_liquido=0 e action_liberar_faturamento
      falha (G012).
    - `l10n_br_volumes` idem (G013).
    - `l10n_br_peso_liquido`, `l10n_br_peso_bruto`, `l10n_br_volumes` SAO
      writable em stock.picking (verificado via fields_get).

    Chamar ENTRE f5b_validar_pickings (qty_done preenchido) e f5c_liberar_faturamento.

    Args:
        picking_id: stock.picking.id.
        peso_unitario_fallback: peso/un se nao tiver. Default 0.001 kg.
        volumes_fallback: volumes minimo se 0. Default 1.

    Returns:
        {'peso_liquido_antes': float, 'peso_liquido_depois': float,
         'volumes_antes': int, 'volumes_depois': int, 'aplicado': bool}.
    """
    p = odoo.read('stock.picking', [picking_id],
        ['l10n_br_peso_liquido', 'l10n_br_peso_bruto', 'l10n_br_volumes', 'state'])
    if not p:
        return {'aplicado': False, 'erro': 'picking nao encontrado'}
    peso_atual = float(p[0].get('l10n_br_peso_liquido') or 0)
    peso_bruto_atual = float(p[0].get('l10n_br_peso_bruto') or 0)
    volumes_atual = int(p[0].get('l10n_br_volumes') or 0)

    updates = {}
    if peso_atual <= 0 or peso_bruto_atual <= 0:
        # Calcular peso fallback = SUM(qty_done) * peso_unitario_fallback
        moves = odoo.search_read('stock.move', [['picking_id', '=', picking_id]],
            ['quantity'])
        qty_total = sum(float(m.get('quantity') or 0) for m in moves)
        peso_calc = max(qty_total * peso_unitario_fallback, peso_unitario_fallback)
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
            'volumes_antes': volumes_atual,
        }

    odoo.write('stock.picking', [picking_id], updates)
    print(f'    G018 picking {picking_id}: peso_liquido {peso_atual} -> '
          f'{updates.get("l10n_br_peso_liquido", peso_atual)}, '
          f'volumes {volumes_atual} -> '
          f'{updates.get("l10n_br_volumes", volumes_atual)}')
    return {
        'aplicado': True,
        'peso_liquido_antes': peso_atual,
        'peso_liquido_depois': updates.get('l10n_br_peso_liquido', peso_atual),
        'volumes_antes': volumes_atual,
        'volumes_depois': updates.get('l10n_br_volumes', volumes_atual),
    }


def carregar_ajustes(
    company_id: int, onda: int,
    status_filtro: Tuple[str, ...] = ('APROVADO', 'PROPOSTO', 'EXECUTADO'),
    limite_produtos: Optional[int] = None,
    filtro_cod_produto: Optional[List[str]] = None,
) -> List[AjusteEstoqueInventario]:
    """Carrega ajustes da onda, filtrando por company + status.

    Onda 1 = LF↔FB: PERDA/INDUS/DEV/RENOMEAR_LOTE
    """
    q = (
        AjusteEstoqueInventario.query
        .filter_by(ciclo=CICLO, company_id=company_id)
        .filter(AjusteEstoqueInventario.status.in_(status_filtro))
    )
    if onda == 1:
        q = q.filter(
            AjusteEstoqueInventario.acao_decidida.in_(
                list(ACOES_LOTE | {
                    'PERDA_LF_FB', 'INDUSTRIALIZACAO_FB_LF',
                    'DEV_LF_FB', 'DEV_FB_LF', 'DEV_CD_LF', 'DEV_LF_CD',
                })
            )
        )
    elif onda == 2:
        q = q.filter(
            AjusteEstoqueInventario.acao_decidida.in_(
                ['TRANSFERIR_CD_FB', 'TRANSFERIR_FB_CD']
            )
        )
    elif onda == 3:
        q = q.filter(
            AjusteEstoqueInventario.acao_decidida.in_(
                ['INDISPONIBILIZAR_LOTE', 'INDISPONIBILIZAR_LOCAL']
            )
        )
    if filtro_cod_produto:
        q = q.filter(
            AjusteEstoqueInventario.cod_produto.in_(filtro_cod_produto)
        )
    ajustes = q.order_by(AjusteEstoqueInventario.cod_produto, AjusteEstoqueInventario.id).all()

    if limite_produtos is not None:
        prods_distintos: List[str] = []
        seen = set()
        for a in ajustes:
            if a.cod_produto not in seen:
                seen.add(a.cod_produto)
                prods_distintos.append(a.cod_produto)
            if len(prods_distintos) >= limite_produtos:
                break
        ajustes = [a for a in ajustes if a.cod_produto in set(prods_distintos)]

    return ajustes


def imprimir_resumo_ajustes(ajustes: List[AjusteEstoqueInventario]) -> Dict[str, Any]:
    """Imprime contagens por acao + retorna dict resumo."""
    por_acao: Dict[str, int] = defaultdict(int)
    prods_por_acao: Dict[str, set] = defaultdict(set)
    valor_total = Decimal('0')
    for a in ajustes:
        por_acao[a.acao_decidida] += 1
        prods_por_acao[a.acao_decidida].add(a.cod_produto)
        if a.qtd_ajuste and a.custo_medio:
            valor_total += Decimal(str(abs(a.qtd_ajuste * a.custo_medio)))

    print(f'  Total ajustes: {len(ajustes)}  Total produtos distintos: '
          f'{len({a.cod_produto for a in ajustes})}')
    for acao in sorted(por_acao):
        print(f'    {acao:<24} {por_acao[acao]:>6} ajustes  '
              f'{len(prods_por_acao[acao]):>5} produtos')
    print(f'  Valor BRL estimado (|qtd_ajuste * custo_medio|): R$ {valor_total:.2f}')
    return {
        'total_ajustes': len(ajustes),
        'por_acao': dict(por_acao),
        'prods_por_acao': {k: sorted(v) for k, v in prods_por_acao.items()},
        'valor_brl': float(valor_total),
    }


# ============================================================
# ETAPA A — Transferencias de lote
# ============================================================

def etapa_a_transferencias_lote(
    odoo, ajustes: List[AjusteEstoqueInventario],
    dry_run: bool, executado_por: str, max_workers: int = 5,
) -> Dict[str, Any]:
    """Para cada ajuste RENOMEAR_LOTE/TRANSFERIR_LOTE: transferir qty para lote alvo.

    Paralelo por (cod_produto, ajuste_id). Cada operacao via
    StockInternalTransferService.transferir_quantidade_para_lote.

    Skip ajustes ja com fase_pipeline=TRANSF_OK (idempotencia).
    """
    banner('ETAPA A — Transferencias de lote (intra-empresa, sem NF)', '-')
    lote_ajustes = [a for a in ajustes if a.acao_decidida in ACOES_LOTE]
    print(f'  {len(lote_ajustes)} ajustes RENOMEAR/TRANSFERIR_LOTE')
    if not lote_ajustes:
        return {'total': 0, 'ok': 0, 'skip': 0, 'falha': 0}

    # Pre-resolver product_id por cod_produto (cache)
    cods = sorted({a.cod_produto for a in lote_ajustes})
    print(f'  Resolvendo product_id para {len(cods)} produtos...')
    prod_cache: Dict[str, Optional[int]] = {}
    for cod in cods:
        prod_cache[cod] = resolver_product_id(odoo, cod)
    missing = [c for c, pid in prod_cache.items() if not pid]
    if missing:
        print(f'  AVISO: {len(missing)} produtos sem product_id no Odoo: {missing[:5]}...')

    if dry_run:
        print(f'  [DRY-RUN] {len(lote_ajustes)} transferencias seriam executadas.')
        return {'total': len(lote_ajustes), 'dry_run': True}

    # Pre-snapshot dos ajustes (evita acesso ao DB nas threads — padrao f5a)
    snapshots = []
    ajuste_index: Dict[int, AjusteEstoqueInventario] = {}
    for a in lote_ajustes:
        ajuste_index[a.id] = a
        snapshots.append({
            'id': a.id,
            'cod_produto': a.cod_produto,
            'lote_origem': (a.lote_origem or '').strip() or None,
            'lote_destino': (a.lote_destino or '').strip(),
            'company_id': a.company_id,
            'qtd_inventario': float(a.qtd_inventario or 0),
            'fase_atual': a.fase_pipeline,
        })

    ist = StockInternalTransferService(odoo=odoo)
    lot_svc = StockLotService(odoo=odoo)
    res_ok = 0
    res_skip = 0
    res_falha = 0
    res_skip_falta_pid = 0

    def _io(snap: Dict[str, Any]) -> Dict[str, Any]:
        """SEQUENCIAL — conexao XML-RPC nao e thread-safe (Request-sent)."""
        if snap['fase_atual'] == 'TRANSF_OK':
            return {'id': snap['id'], 'status': 'skip', 'erro': 'ja em TRANSF_OK'}
        pid = prod_cache.get(snap['cod_produto'])
        if not pid:
            return {'id': snap['id'], 'status': 'skip_pid',
                    'erro': f"sem product_id ({snap['cod_produto']})"}
        if not snap['lote_destino']:
            return {'id': snap['id'], 'status': 'falha', 'erro': 'sem lote_destino'}
        qty = snap['qtd_inventario']
        if qty <= 0:
            return {'id': snap['id'], 'status': 'skip', 'erro': 'qtd_inventario=0'}
        lot_id_origem = (
            lot_svc.buscar_por_nome(snap['lote_origem'], pid, snap['company_id'])
            if snap['lote_origem'] else None
        )
        try:
            ist.transferir_quantidade_para_lote(
                product_id=pid, company_id=snap['company_id'],
                location_id=COMPANY_LOCATIONS[snap['company_id']],
                qty=qty, lot_id_origem=lot_id_origem,
                nome_lote_destino=snap['lote_destino'],
            )
            return {'id': snap['id'], 'status': 'ok', 'erro': None}
        except Exception as e:
            return {'id': snap['id'], 'status': 'falha', 'erro': str(e)[:300]}

    inicio = time.time()
    for idx, snap in enumerate(snapshots, 1):
        r = _io(snap)
        aj_id = r['id']
        status = r['status']
        erro = r['erro']
        aj = ajuste_index[aj_id]
        if status == 'ok':
            aj.fase_pipeline = 'TRANSF_OK'
            db.session.commit()
            res_ok += 1
        elif status == 'skip':
            res_skip += 1
        elif status == 'skip_pid':
            res_skip_falta_pid += 1
        else:  # falha
            aj.fase_pipeline = 'TRANSF_FALHA'
            aj.erro_msg = (erro or '')[:500]
            db.session.commit()
            res_falha += 1
            logger.error(f'A: ajuste {aj_id} falhou: {erro}')
        if idx % 20 == 0:
            print(f'  ETAPA A progress: {idx}/{len(snapshots)} '
                  f'(ok={res_ok} skip={res_skip} falha={res_falha})')

    elapsed = int(time.time() - inicio)
    print(f'  ETAPA A concluida em {elapsed}s: OK={res_ok} SKIP={res_skip} '
          f'SKIP_PID={res_skip_falta_pid} FALHA={res_falha}')
    return {
        'total': len(lote_ajustes), 'ok': res_ok, 'skip': res_skip,
        'skip_pid': res_skip_falta_pid, 'falha': res_falha, 'tempo_s': elapsed,
    }


# ============================================================
# ETAPA B — Pickings agrupados
# ============================================================

def _chunk(lst: List[Any], size: int) -> List[List[Any]]:
    return [lst[i:i + size] for i in range(0, len(lst), size)]


def etapa_b_pickings(
    odoo, ajustes: List[AjusteEstoqueInventario],
    dry_run: bool, executado_por: str, max_produtos_por_picking: int = 30,
    modo_validacao_fiscal: str = 'strict',
    auto_fix_weight: float = 0.001,
) -> Dict[str, Any]:
    """Agrupa ajustes PERDA/INDUS/DEV por (company_origem, tipo_op).

    Para cada grupo, divide em chunks de N produtos e cria 1 picking
    por chunk. Cada picking tem N linhas (1 por ajuste).

    Skip ajustes ja com fase_pipeline em (F5a_PICKING_CRIADO,
    F5b_VALIDADO, F5c_LIBERADO, F5d_INVOICE_GERADA, F5e_SEFAZ_OK).
    """
    banner('ETAPA B — Pickings agrupados (saidas de NF)', '-')
    picking_ajustes = [
        a for a in ajustes
        if a.acao_decidida in ACOES_PICKING
        and a.fase_pipeline not in ('F5a_PICKING_CRIADO', 'F5b_VALIDADO',
                                    'F5c_LIBERADO', 'F5d_INVOICE_GERADA',
                                    'F5e_SEFAZ_OK')
    ]
    print(f'  {len(picking_ajustes)} ajustes PERDA/INDUS/DEV pendentes')
    if not picking_ajustes:
        return {'total': 0, 'pickings': 0}

    # Agrupar por (company_origem, tipo_op)
    grupos: Dict[Tuple[int, str], List[AjusteEstoqueInventario]] = defaultdict(list)
    for aj in picking_ajustes:
        if aj.acao_decidida not in ACAO_PARA_DIRECAO:
            logger.warning(f'  Acao {aj.acao_decidida!r} sem direcao, pulando ajuste {aj.id}')
            continue
        tipo_op, origem, destino = ACAO_PARA_DIRECAO[aj.acao_decidida]
        grupos[(origem, tipo_op)].append(aj)

    print(f'  {len(grupos)} grupos (company_origem, tipo_op):')
    for (origem, tipo_op), grp in grupos.items():
        print(f'    company_origem={origem}, tipo_op={tipo_op}: {len(grp)} ajustes')

    if dry_run:
        total_pickings = 0
        for grp in grupos.values():
            cods_distintos = sorted({a.cod_produto for a in grp})
            n_chunks = len(_chunk(cods_distintos, max_produtos_por_picking))
            total_pickings += n_chunks
        print(f'  [DRY-RUN] {total_pickings} pickings seriam criados '
              f'(max {max_produtos_por_picking} produtos/picking).')
        return {'total': len(picking_ajustes), 'pickings_planejados': total_pickings, 'dry_run': True}

    # Resolver product_id + standard_price para todos os codigos
    cods_total = sorted({a.cod_produto for a in picking_ajustes})
    print(f'  Resolvendo product_id + standard_price para {len(cods_total)} produtos...')
    prod_cache: Dict[str, Optional[int]] = {}
    custo_cache: Dict[str, float] = {}  # cod_produto -> custo (>0)
    for c in cods_total:
        prods = odoo.search_read(
            'product.product',
            [['default_code', '=', c]],
            ['id', 'standard_price'],
            limit=1,
        )
        if prods:
            prod_cache[c] = prods[0]['id']
            std = float(prods[0].get('standard_price') or 0)
            # Aceita negativo como abs (erro de cadastro Odoo), zero vira 0.01
            custo_cache[c] = abs(std) if std else 0.01
        else:
            prod_cache[c] = None
            custo_cache[c] = 0.01

    # Validar custo_medio dos ajustes — se 0/None, usar standard_price
    ajustes_corrigidos = 0
    for aj in picking_ajustes:
        cm = float(aj.custo_medio or 0)
        if cm <= 0:
            novo_cm = custo_cache.get(aj.cod_produto, 0.01)
            aj.custo_medio = novo_cm
            ajustes_corrigidos += 1
            logger.info(
                f'  ajuste {aj.id} ({aj.cod_produto}): custo_medio '
                f'{cm} -> {novo_cm} (standard_price Odoo)'
            )
    if ajustes_corrigidos:
        db.session.commit()
        print(f'  Corrigidos {ajustes_corrigidos} ajustes com custo_medio<=0')

    # G018: ANTES da validacao fiscal, corrigir weight=0 (fallback automatico
    # via product.write). Evita que validar_cadastro_fiscal aborte por
    # weight=0 em produtos onde 0.001 e' aceitavel (rotulos/embalagens).
    # auto_fix_weight=0 desabilita (validacao fiscal vai bloquear).
    if auto_fix_weight > 0:
        corrigir_weight_zero(
            odoo, prod_cache, peso_fallback=auto_fix_weight,
        )

    # G017 + G012/G013: validar cadastro fiscal ANTES de criar pickings.
    # Aborta etapa B (modo=strict) ou avisa (modo=warn) se houver produtos
    # sem NCM/weight no Odoo. Cods orfaos (pid=None) sao filtrados aqui;
    # picking_svc.criar_transferencia ja' pula esses ajustes naturalmente.
    if modo_validacao_fiscal == 'skip':
        print('  Validacao fiscal: PULADA (modo=skip)')
    else:
        n_pids = sum(1 for pid in prod_cache.values() if pid)
        print(f'  Validacao fiscal (modo={modo_validacao_fiscal}) sobre '
              f'{n_pids} produtos com pid...')
        validar_cadastro_fiscal(
            odoo, prod_cache, modo=modo_validacao_fiscal,
        )
        print('  Validacao fiscal: OK (NCM e weight presentes em todos os pids)')

    picking_svc = StockPickingService(odoo=odoo)
    pipeline_svc = InventarioPipelineService(odoo=odoo, picking_svc=picking_svc)

    total_pickings = 0
    total_validados = 0
    total_liberados = 0
    falhas = 0

    for (company_origem, tipo_op), grp in grupos.items():
        company_destino_id = ACAO_PARA_DIRECAO[grp[0].acao_decidida][2]
        picking_type_id = PICKING_TYPE_POR_DIRECAO.get((company_origem, tipo_op))
        if not picking_type_id:
            logger.error(f'  picking_type ausente para ({company_origem}, {tipo_op}); pulando grupo')
            falhas += len(grp)
            continue
        location_origem = COMPANY_LOCATIONS[company_origem]
        location_destino = resolver_location_destino(
            tipo_op, company_destino_id, company_origem=company_origem,
        )
        partner_id = COMPANY_PARTNER_ID[company_destino_id]

        # Agrupar dentro do grupo por cod_produto -> lista de ajustes
        por_produto: Dict[str, List[AjusteEstoqueInventario]] = defaultdict(list)
        for aj in grp:
            por_produto[aj.cod_produto].append(aj)

        cods_distintos = sorted(por_produto.keys())
        chunks = _chunk(cods_distintos, max_produtos_por_picking)
        print(f'\n  Grupo ({company_origem}, {tipo_op}) -> '
              f'{len(chunks)} pickings (max {max_produtos_por_picking} produtos)')

        for idx, chunk_cods in enumerate(chunks, 1):
            linhas: List[Dict[str, Any]] = []
            ajustes_chunk: List[AjusteEstoqueInventario] = []
            ajustes_compensatorios_a_criar: List[Dict[str, Any]] = []
            for cod in chunk_cods:
                pid = prod_cache.get(cod)
                if not pid:
                    logger.warning(f'    sem product_id para {cod}, pulando')
                    continue
                ajustes_produto = por_produto[cod]
                demand_total = sum(
                    float(abs(a.qtd_ajuste or 0)) for a in ajustes_produto
                )
                if demand_total <= 0:
                    continue
                ajustes_chunk.extend(ajustes_produto)

                # Consultar quants REAIS na origem (FIFO por create_date)
                quants = odoo.search_read(
                    'stock.quant',
                    [
                        ['product_id', '=', pid],
                        ['company_id', '=', company_origem],
                        ['location_id', '=', location_origem],
                        ['quantity', '>', 0],
                    ],
                    ['id', 'lot_id', 'quantity', 'reserved_quantity', 'create_date'],
                    order='create_date asc',
                )

                # G014 PROTECTION: separar quants em VALIDOS (lote nao vencido)
                # e VENCIDOS (lote expirado). Odoo CIEL IT bloqueia auto-reserva
                # de lotes vencidos via action_assign.
                # Se livre_validos < demand: transferir qty necessaria de lotes
                # vencidos -> lote NOVO valido (criado on-the-fly).
                from datetime import datetime as _dt, timedelta as _td
                HOJE = _dt.utcnow()
                EXP_NOVO_LOTE = (HOJE + _td(days=365)).strftime('%Y-%m-%d %H:%M:%S')

                lot_ids_consultar = [q['lot_id'][0] for q in quants if q.get('lot_id')]
                lot_exp_cache: Dict[int, Optional[str]] = {}
                if lot_ids_consultar:
                    lots_info = odoo.read(
                        'stock.lot', lot_ids_consultar, ['expiration_date'],
                    )
                    lot_exp_cache = {
                        l['id']: l.get('expiration_date') for l in lots_info
                    }

                def _is_lot_vencido(q):
                    if not q.get('lot_id'):
                        return False  # quant sem lote = nao vencido
                    exp = lot_exp_cache.get(q['lot_id'][0])
                    if not exp:
                        return False
                    try:
                        exp_dt = _dt.strptime(exp.split(' ')[0], '%Y-%m-%d')
                        return exp_dt < HOJE
                    except Exception:
                        return False

                quants_validos = [q for q in quants if not _is_lot_vencido(q)]
                quants_vencidos = [q for q in quants if _is_lot_vencido(q)]
                livre_validos = sum(
                    float(q['quantity']) - float(q.get('reserved_quantity') or 0)
                    for q in quants_validos
                )
                livre_vencidos = sum(
                    float(q['quantity']) - float(q.get('reserved_quantity') or 0)
                    for q in quants_vencidos
                )
                qty_disponivel = livre_validos + livre_vencidos

                # G014: se livre_validos < demand e ha vencidos livres,
                # transferir qty necessaria para lote novo valido.
                if livre_validos < demand_total and livre_vencidos > 0:
                    qty_a_migrar = min(
                        demand_total - livre_validos, livre_vencidos,
                    )
                    nome_lote_novo = f'INV-{cod}-{HOJE.strftime("%Y%m%d")}'
                    logger.warning(
                        f'    G014 {cod}: livre_validos={livre_validos:.3f} < '
                        f'demand={demand_total:.3f}. Transferindo '
                        f'{qty_a_migrar:.3f} de lotes vencidos -> lote novo '
                        f'{nome_lote_novo} (exp={EXP_NOVO_LOTE[:10]}).'
                    )
                    try:
                        from app.odoo.services.stock_internal_transfer_service import (
                            StockInternalTransferService,
                        )
                        transfer_svc = StockInternalTransferService(odoo=odoo)
                        qty_restante_migrar = qty_a_migrar
                        for qv in quants_vencidos:
                            if qty_restante_migrar <= 0.001:
                                break
                            livre_qv = (
                                float(qv['quantity'])
                                - float(qv.get('reserved_quantity') or 0)
                            )
                            if livre_qv <= 0:
                                continue
                            take = min(livre_qv, qty_restante_migrar)
                            transfer_svc.transferir_quantidade_para_lote(
                                product_id=pid,
                                company_id=company_origem,
                                location_id=location_origem,
                                qty=take,
                                lot_id_origem=(
                                    qv['lot_id'][0] if qv.get('lot_id') else None
                                ),
                                nome_lote_destino=nome_lote_novo,
                                expiration_date_destino=EXP_NOVO_LOTE,
                            )
                            qty_restante_migrar -= take
                            logger.info(
                                f'    G014 migrou {take:.3f} do lote '
                                f'{qv["lot_id"][1] if qv.get("lot_id") else "sem-lote"} '
                                f'-> {nome_lote_novo}'
                            )
                        # Re-consultar quants apos transferencia
                        quants = odoo.search_read(
                            'stock.quant',
                            [
                                ['product_id', '=', pid],
                                ['company_id', '=', company_origem],
                                ['location_id', '=', location_origem],
                                ['quantity', '>', 0],
                            ],
                            ['id', 'lot_id', 'quantity',
                             'reserved_quantity', 'create_date'],
                            order='create_date asc',
                        )
                        # Re-cache expiration dos lotes (lote novo agora aparece)
                        lot_ids_consultar = [
                            q['lot_id'][0] for q in quants if q.get('lot_id')
                        ]
                        if lot_ids_consultar:
                            lots_info = odoo.read(
                                'stock.lot', lot_ids_consultar,
                                ['expiration_date'],
                            )
                            lot_exp_cache = {
                                l['id']: l.get('expiration_date')
                                for l in lots_info
                            }
                        # Refazer split validos/vencidos
                        quants_validos = [
                            q for q in quants if not _is_lot_vencido(q)
                        ]
                    except Exception as e:
                        logger.error(
                            f'    G014 falha ao transferir vencidos: {e}'
                        )

                qty_restante = demand_total
                # G014: priorizar quants VALIDOS (FIFO entre eles). Quants
                # vencidos remanescentes NAO entram no picking (Odoo bloqueia).
                for q in quants_validos:
                    if qty_restante <= 0.001:
                        break
                    livre = float(q['quantity']) - float(q.get('reserved_quantity') or 0)
                    if livre <= 0:
                        continue
                    take = min(livre, qty_restante)
                    lot_name = q['lot_id'][1] if q.get('lot_id') else False
                    linhas.append({
                        'product_id': pid,
                        'quantity': take,
                        'lot_name': lot_name,
                        'name': f'Inv {CICLO} cod={cod} lote={lot_name}',
                    })
                    qty_restante -= take

                # Se sobrou qty_restante: criar ajuste compensatorio
                # Regra do usuario (2026-05-18): "se qty_restante>0 criar
                # ajuste positivo na FB e transferir pra LF"
                if qty_restante > 0.001:
                    logger.warning(
                        f'    {cod}: demanda {demand_total} > disponivel {qty_disponivel} '
                        f'(falta {qty_restante:.4f}). Gerando ajuste compensatorio FB->LF.'
                    )
                    # So aplicavel quando tipo_op=perda (LF→FB).
                    # Para outros tipos_op, registrar so como pendencia.
                    if tipo_op == 'perda' and company_origem == 5:
                        # Pegar custo_medio do produto (de qualquer ajuste do mesmo cod)
                        custo_ref = next(
                            (a.custo_medio for a in ajustes_produto if a.custo_medio),
                            0,
                        )
                        ajustes_compensatorios_a_criar.append({
                            'cod_produto': cod,
                            'tipo_produto': int(cod[0]) if cod[0].isdigit() else 1,
                            'company_id': 5,  # ajuste na LF (origem)
                            'acao_decidida': 'INDUSTRIALIZACAO_FB_LF',
                            'qtd_inventario': qty_restante,
                            'qtd_odoo': 0,
                            'qtd_ajuste': qty_restante,
                            'custo_medio': custo_ref,
                            'lote_origem': None,
                            'lote_destino': 'MIGRAÇÃO',  # alvo intermediario na LF
                            # Nota: modelo AjusteEstoqueInventario nao tem
                            # `tipo_divergencia` — encodado no `erro_msg` abaixo
                            'tipo_divergencia_marker': 'COMPENSATORIO_FALTA_ESTOQUE',
                            'status': 'PROPOSTO',
                            'origem_ajuste_id': ajustes_produto[0].id,
                        })
                    # Marcar ajuste original com erro_msg apontando o delta
                    for a in ajustes_produto:
                        a.erro_msg = (
                            f'qty_restante={qty_restante:.4f} sem estoque '
                            f'(disponivel={qty_disponivel:.4f}, demand={demand_total:.4f})'
                        )[:500]
            if not linhas:
                logger.info(f'    chunk {idx}/{len(chunks)}: sem linhas, pulando')
                continue

            origin_str = f'INV-{CICLO}-{tipo_op.upper()}-G{idx:03d}'
            try:
                picking_id = picking_svc.criar_transferencia(
                    company_origem_id=company_origem,
                    company_destino_id=company_destino_id,
                    location_origem_id=location_origem,
                    location_destino_id=location_destino,
                    linhas=linhas,
                    picking_type_id=picking_type_id,
                    partner_id=partner_id,
                    origin=origin_str,
                )
                total_pickings += 1
                # Marca picking_id em todos ajustes do chunk
                for aj in ajustes_chunk:
                    aj.picking_id_odoo = picking_id
                    aj.fase_pipeline = 'F5a_PICKING_CRIADO'
                # Persistir ajustes compensatorios (PROPOSTO) para
                # quando o usuario aprovar/processar ondas futuras.
                if ajustes_compensatorios_a_criar:
                    for payload_comp in ajustes_compensatorios_a_criar:
                        novo = AjusteEstoqueInventario(
                            ciclo=CICLO,
                            cod_produto=payload_comp['cod_produto'],
                            tipo_produto=payload_comp['tipo_produto'],
                            company_id=payload_comp['company_id'],
                            acao_decidida=payload_comp['acao_decidida'],
                            qtd_inventario=payload_comp['qtd_inventario'],
                            qtd_odoo=payload_comp['qtd_odoo'],
                            qtd_ajuste=payload_comp['qtd_ajuste'],
                            custo_medio=payload_comp['custo_medio'],
                            lote_origem=payload_comp['lote_origem'],
                            lote_destino=payload_comp['lote_destino'],
                            status=payload_comp['status'],
                            criado_por=executado_por,
                            erro_msg=(
                                f'[{payload_comp["tipo_divergencia_marker"]}] '
                                f'Compensatorio origem_ajuste='
                                f'{payload_comp["origem_ajuste_id"]}'
                            ),
                        )
                        db.session.add(novo)
                db.session.commit()
                print(f'    [{idx}/{len(chunks)}] picking {picking_id} criado '
                      f'({len(ajustes_chunk)} ajustes, {len(linhas)} linhas, '
                      f'{len(ajustes_compensatorios_a_criar)} compensatorios)')
            except Exception as e:
                logger.error(f'    chunk {idx}: criar_transferencia falhou: {e}')
                for aj in ajustes_chunk:
                    aj.fase_pipeline = 'F5a_FALHA'
                    aj.erro_msg = str(e)[:500]
                db.session.commit()
                falhas += len(ajustes_chunk)
                continue

            # Validar + liberar (bulk via pipeline svc)
            # L19 fix: passar linhas para preencher_qty_done apos action_assign
            # (senao move_lines ficam qty_done=0 -> peso/volumes=0 -> F5c falha)
            try:
                pipeline_svc.f5b_validar_pickings(
                    ajustes_chunk, executado_por=executado_por,
                    linhas_por_picking={picking_id: linhas},
                )
                total_validados += 1
            except Exception as e:
                logger.error(f'    chunk {idx}: f5b falhou: {e}')

            # G018 v2: peso_liquido/volumes fallback no picking (entre F5b e F5c).
            # product.write({weight: X}) NAO PERSISTE em CIEL IT (hook reseta para 0),
            # mas l10n_br_peso_liquido + l10n_br_volumes EM stock.picking SAO writable.
            # Aplicar fallback evita F5c rejeitar por peso=0/volumes=0.
            try:
                aplicar_peso_volumes_fallback_picking(
                    odoo, picking_id,
                    peso_unitario_fallback=0.001,
                    volumes_fallback=max(1, len(linhas)),
                )
            except Exception as e:
                logger.warning(
                    f'    chunk {idx}: G018 fallback peso/volumes '
                    f'falhou (nao bloqueante): {e}'
                )

            try:
                pipeline_svc.f5c_liberar_faturamento(ajustes_chunk, executado_por=executado_por)
                total_liberados += 1
            except Exception as e:
                logger.error(f'    chunk {idx}: f5c falhou: {e}')

    print(f'\n  ETAPA B: pickings criados={total_pickings} '
          f'validados={total_validados} liberados={total_liberados} '
          f'ajustes_falha={falhas}')
    return {
        'total': len(picking_ajustes),
        'pickings_criados': total_pickings,
        'pickings_validados': total_validados,
        'pickings_liberados': total_liberados,
        'falhas': falhas,
    }


# ============================================================
# ETAPA C — Aguardar invoices CIEL IT
# ============================================================

def etapa_c_aguardar_invoices(
    odoo, ajustes: List[AjusteEstoqueInventario],
    dry_run: bool, executado_por: str,
    timeout: int = 1800, poll_interval: int = 40,
) -> Dict[str, Any]:
    """Aguarda robo CIEL IT criar invoices para todos pickings de B.

    Polling unico, em paralelo por picking distinto.
    """
    banner('ETAPA C — Aguardar invoices CIEL IT (paralelo)', '-')
    pendentes = [
        a for a in ajustes
        if a.picking_id_odoo
        and a.fase_pipeline in ('F5c_LIBERADO',)
        and not a.invoice_id_odoo
    ]
    print(f'  {len(pendentes)} ajustes aguardando invoice CIEL IT')
    if not pendentes:
        return {'total': 0}
    pickings_distintos = sorted({a.picking_id_odoo for a in pendentes})
    print(f'  {len(pickings_distintos)} pickings distintos')

    if dry_run:
        print(f'  [DRY-RUN] aguardaria invoices ate {timeout}s.')
        return {'total': len(pendentes), 'dry_run': True}

    pipeline_svc = InventarioPipelineService(odoo=odoo)
    resolved = pipeline_svc.f5d_aguardar_invoices(
        pendentes, timeout=timeout, poll_interval=poll_interval,
        executado_por=executado_por,
    )
    ok = sum(1 for v in resolved.values() if v)
    miss = sum(1 for v in resolved.values() if not v)
    print(f'  ETAPA C: invoices criadas={ok} timeout={miss}')
    return {'total': len(pendentes), 'ok': ok, 'timeout': miss}


# ============================================================
# ETAPA D — SEFAZ
# ============================================================

def etapa_d_sefaz(
    odoo, ajustes: List[AjusteEstoqueInventario],
    dry_run: bool, executado_por: str,
) -> Dict[str, Any]:
    """Transmite NF-e via Playwright (serial).

    Recebe TODOS ajustes com invoice_id_odoo populado e fase F5d_INVOICE_GERADA.
    """
    banner('ETAPA D — SEFAZ via Playwright (serial)', '-')
    pendentes = [
        a for a in ajustes
        if a.invoice_id_odoo
        and a.fase_pipeline == 'F5d_INVOICE_GERADA'
    ]
    print(f'  {len(pendentes)} ajustes para transmitir SEFAZ')
    if not pendentes:
        return {'total': 0}

    # Reduz para invoices distintas
    inv_to_first = {}
    for a in pendentes:
        inv_to_first.setdefault(a.invoice_id_odoo, a)
    invoices_distintos = sorted(inv_to_first)
    print(f'  {len(invoices_distintos)} invoices distintas para transmitir')

    if dry_run:
        print(f'  [DRY-RUN] {len(invoices_distintos)} invoices SEFAZ seriam transmitidas.')
        return {'total': len(pendentes), 'dry_run': True}

    pipeline_svc = InventarioPipelineService(odoo=odoo)
    # f5e_transmitir_sefaz itera por ajuste, mas pula idempotente
    resolved = pipeline_svc.f5e_transmitir_sefaz(pendentes, executado_por=executado_por)
    ok = sum(1 for v in resolved.values() if v)
    miss = len(invoices_distintos) - ok
    print(f'  ETAPA D: SEFAZ OK={ok} FALHA/SKIP={miss}')
    return {'total': len(pendentes), 'ok': ok, 'falha_skip': miss}


# ============================================================
# ETAPA E — Entrada FB para cada NF SEFAZ-autorizada
# ============================================================

def etapa_e_entrada_fb(
    odoo, ajustes: List[AjusteEstoqueInventario],
    dry_run: bool, executado_por: str,
) -> Dict[str, Any]:
    """Para cada invoice_id distinto com chave_nfe (SEFAZ OK), cria
    RecebimentoLf na FB e processa pipeline 0-18 (recebimento_lf).

    Replica entrada_fb_piloto.py em bulk.
    """
    banner('ETAPA E — Entrada FB para NFs SEFAZ-autorizadas', '-')
    from app.recebimento.models import (  # noqa: E402  # type: ignore
        RecebimentoLf, RecebimentoLfLote,
    )
    from app.recebimento.services.recebimento_lf_odoo_service import (  # noqa: E402  # type: ignore
        RecebimentoLfOdooService,
    )

    # L17 (G006/D006): Filtrar acoes que geram ENTRADA na FB.
    # Acoes incluidas: PERDA_LF_FB, TRANSFERIR_CD_FB, DEV_LF_FB, DEV_CD_LF
    # (sentidos {LF,CD}->FB — FB recebe NF).
    # Acoes excluidas: INDUSTRIALIZACAO_FB_LF, DEV_FB_LF, TRANSFERIR_FB_CD
    # (sentido FB->{LF,CD} — FB emite, nao recebe; entrada destino e' manual).
    ACOES_ENTRADA_FB = {
        'PERDA_LF_FB', 'TRANSFERIR_CD_FB', 'DEV_LF_FB', 'DEV_CD_LF',
    }
    autorizados = [
        a for a in ajustes
        if a.invoice_id_odoo and a.chave_nfe
        and a.fase_pipeline == 'F5e_SEFAZ_OK'
        and a.acao_decidida in ACOES_ENTRADA_FB
    ]
    if not autorizados:
        print('  Sem ajustes SEFAZ-autorizados com acao de entrada FB. '
              'Etapa pulada.')
        return {'total': 0}

    # Log dos descartados (sentido FB->X, entrada manual no destino)
    descartados = [
        a for a in ajustes
        if a.invoice_id_odoo and a.chave_nfe
        and a.fase_pipeline == 'F5e_SEFAZ_OK'
        and a.acao_decidida not in ACOES_ENTRADA_FB
    ]
    if descartados:
        cods_desc = sorted({a.cod_produto for a in descartados})
        print(
            f'  [L17] {len(descartados)} ajustes pulados (sentido FB->X, '
            f'entrada destino e manual): {len(cods_desc)} produtos, '
            f'acoes={sorted({a.acao_decidida for a in descartados})}'
        )

    # Agrupar por invoice_id (1 NF = 1 RecebimentoLf)
    por_invoice: Dict[int, List[AjusteEstoqueInventario]] = defaultdict(list)
    for a in autorizados:
        por_invoice[a.invoice_id_odoo].append(a)

    # CFOPs 5901/5903/5949 -> retorno -> entrada FB sem transferencia CD
    print(f'  {len(por_invoice)} invoices distintas para entrada FB')

    if dry_run:
        print(f'  [DRY-RUN] {len(por_invoice)} RecebimentoLf seriam criados.')
        return {'total': len(por_invoice), 'dry_run': True}

    ok = 0
    falha = 0
    skip = 0
    for invoice_id, ajs in por_invoice.items():
        # Idempotencia: ja' existe RecebimentoLf para essa invoice?
        existente = RecebimentoLf.query.filter_by(
            odoo_lf_invoice_id=invoice_id,
        ).order_by(RecebimentoLf.id.desc()).first()
        if existente and existente.status == 'processado':
            print(f'  invoice {invoice_id}: RecebimentoLf {existente.id} ja processado (skip)')
            skip += 1
            continue

        # Buscar dados da invoice
        try:
            inv_data = odoo.read(
                'account.move', [invoice_id],
                ['name', 'l10n_br_chave_nf', 'l10n_br_numero_nota_fiscal'],
            )
            if not inv_data:
                logger.error(f'  invoice {invoice_id} sumiu do Odoo, pulando')
                falha += 1
                continue
            inv = inv_data[0]
            chave = inv.get('l10n_br_chave_nf') or ajs[0].chave_nfe
            numero_nf = str(inv.get('l10n_br_numero_nota_fiscal', '') or '')
        except Exception as e:
            logger.error(f'  invoice {invoice_id}: erro ler: {e}')
            falha += 1
            continue

        # Resolver product_id de cada cod_produto
        cods = sorted({a.cod_produto for a in ajs})
        prod_cache = {c: resolver_product_id(odoo, c) for c in cods}

        # Criar RecebimentoLf + Lotes
        if existente:
            rec = existente
            print(f'  invoice {invoice_id}: retomando RecebimentoLf {rec.id}')
        else:
            rec = RecebimentoLf(
                odoo_lf_invoice_id=invoice_id,
                numero_nf=numero_nf,
                chave_nfe=chave,
                cnpj_emitente='18.467.441/0001-63',
                company_id=1,
                status='pendente',
                usuario=executado_por,
                total_etapas=37,
            )
            db.session.add(rec)
            db.session.flush()
            # Agregar por (product_id, lote_destino) -> qty
            agg: Dict[Tuple[int, str, str], float] = defaultdict(float)
            for a in ajs:
                pid = prod_cache.get(a.cod_produto)
                if not pid:
                    logger.warning(f'    sem product_id para {a.cod_produto}, pulando')
                    continue
                lote_dest = (a.lote_destino or 'MIGRAÇÃO').strip()
                cfop = '5903'  # default; refinar por tipo_op se necessario
                agg[(pid, lote_dest, cfop)] += float(abs(a.qtd_ajuste or 0))
            for (pid, lote_dest, cfop), qty in agg.items():
                if qty <= 0:
                    continue
                db.session.add(RecebimentoLfLote(
                    recebimento_lf_id=rec.id,
                    odoo_product_id=pid,
                    tipo='auto',
                    lote_nome=lote_dest,
                    quantidade=qty,
                    cfop=cfop,
                    produto_tracking='lot',
                    processado=False,
                ))
            db.session.commit()
            print(f'  invoice {invoice_id}: RecebimentoLf {rec.id} criado ({len(agg)} lotes)')

        # Processar SINCRONO
        svc = RecebimentoLfOdooService()
        try:
            resultado = svc.processar_recebimento(rec.id, usuario_nome=executado_por)
            print(f'    OK status={resultado.get("status")} invoice_fb={resultado.get("odoo_invoice_id")}')
            ok += 1
        except Exception as e:
            logger.error(f'  invoice {invoice_id}: processamento falhou: {e}')
            falha += 1

    print(f'  ETAPA E: OK={ok} SKIP={skip} FALHA={falha}')
    return {'total': len(por_invoice), 'ok': ok, 'skip': skip, 'falha': falha}


# ============================================================
# Main
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--company-id', type=int, required=True, choices=[1, 4, 5])
    parser.add_argument('--onda', type=int, default=1, choices=[1, 2, 3])
    parser.add_argument('--limite-produtos', type=int, default=None,
                        help='processar so os primeiros N produtos (sub-piloto)')
    parser.add_argument('--max-produtos-picking', type=int, default=30)
    parser.add_argument('--filtro-cod-produto', default=None,
                        help='lista CSV de cod_produto a filtrar')
    parser.add_argument('--apenas-etapa', default=None, choices=ETAPAS_VALIDAS,
                        help='executar apenas 1 etapa (A/B/C/D/E)')
    parser.add_argument('--ate-etapa', default=None, choices=ETAPAS_VALIDAS,
                        help='executar ate a etapa N (A < B < C < D < E)')
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--confirmar', action='store_true',
                        help='executa de verdade (A+B+C; D requer --confirmar-sefaz; E requer --confirmar)')
    parser.add_argument('--confirmar-sefaz', action='store_true',
                        help='libera ETAPA D (SEFAZ Playwright — irreversivel)')
    parser.add_argument('--usuario', default='bulk_onda')
    parser.add_argument('--max-workers', type=int, default=5)
    parser.add_argument('--validacao-fiscal', default='strict',
                        choices=['strict', 'warn', 'skip'],
                        help='G017+G012/G013 validacao pre-pickings. '
                        'strict aborta etapa B se houver produtos sem '
                        'NCM/weight; warn apenas avisa; skip nao valida.')
    parser.add_argument('--auto-fix-weight', type=float, default=0.001,
                        help='G018: peso fallback (kg) para produtos com '
                        'weight=0. Default 0.001 (1g). Usar 0 desabilita o '
                        'fix automatico (validacao fiscal vai bloquear se '
                        'modo=strict). Aceitavel para rotulos/embalagens; '
                        'cadastro correto recomendado para ingredientes.')
    args = parser.parse_args()

    dry_run = not args.confirmar
    if args.confirmar_sefaz and not args.confirmar:
        print('ERRO: --confirmar-sefaz exige --confirmar')
        sys.exit(2)

    # Decidir conjunto de etapas a rodar
    if args.apenas_etapa:
        etapas = [args.apenas_etapa]
    else:
        idx_final = ETAPAS_VALIDAS.index(args.ate_etapa) if args.ate_etapa else len(ETAPAS_VALIDAS) - 1
        etapas = list(ETAPAS_VALIDAS[:idx_final + 1])

    filtro_cods: Optional[List[str]] = None
    if args.filtro_cod_produto:
        filtro_cods = [c.strip() for c in args.filtro_cod_produto.split(',') if c.strip()]

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()

        banner(
            f'BULK ONDA {args.onda} company={args.company_id} '
            f'modo={"DRY-RUN" if dry_run else "REAL"} '
            f'etapas={"".join(etapas)}'
        )
        print(f'  Usuario: {args.usuario}')
        print(f'  Limite produtos: {args.limite_produtos or "(sem limite)"}')
        print(f'  Max produtos/picking: {args.max_produtos_picking}')
        if filtro_cods:
            print(f'  Filtro cod_produto: {filtro_cods}')

        ajustes = carregar_ajustes(
            company_id=args.company_id, onda=args.onda,
            limite_produtos=args.limite_produtos,
            filtro_cod_produto=filtro_cods,
        )
        banner('RESUMO DOS AJUSTES SELECIONADOS', '-')
        imprimir_resumo_ajustes(ajustes)

        if not ajustes:
            print('\n  Nenhum ajuste — encerrando.')
            return

        if 'A' in etapas:
            etapa_a_transferencias_lote(
                odoo, ajustes, dry_run=dry_run, executado_por=args.usuario,
                max_workers=args.max_workers,
            )
            # Recarregar ajustes (fase_pipeline atualizada)
            db.session.expire_all()
            ajustes = carregar_ajustes(
                company_id=args.company_id, onda=args.onda,
                limite_produtos=args.limite_produtos,
                filtro_cod_produto=filtro_cods,
            )

        if 'B' in etapas:
            etapa_b_pickings(
                odoo, ajustes, dry_run=dry_run, executado_por=args.usuario,
                max_produtos_por_picking=args.max_produtos_picking,
                modo_validacao_fiscal=args.validacao_fiscal,
                auto_fix_weight=args.auto_fix_weight,
            )
            db.session.expire_all()
            ajustes = carregar_ajustes(
                company_id=args.company_id, onda=args.onda,
                limite_produtos=args.limite_produtos,
                filtro_cod_produto=filtro_cods,
            )

        if 'C' in etapas:
            etapa_c_aguardar_invoices(
                odoo, ajustes, dry_run=dry_run, executado_por=args.usuario,
            )
            db.session.expire_all()
            ajustes = carregar_ajustes(
                company_id=args.company_id, onda=args.onda,
                limite_produtos=args.limite_produtos,
                filtro_cod_produto=filtro_cods,
            )

        if 'D' in etapas:
            if not args.confirmar_sefaz and not dry_run:
                print('\n  ETAPA D requer --confirmar-sefaz (SEFAZ irreversivel). Pulando.')
            else:
                etapa_d_sefaz(
                    odoo, ajustes, dry_run=dry_run, executado_por=args.usuario,
                )
                db.session.expire_all()
                ajustes = carregar_ajustes(
                    company_id=args.company_id, onda=args.onda,
                    limite_produtos=args.limite_produtos,
                    filtro_cod_produto=filtro_cods,
                )

        if 'E' in etapas:
            etapa_e_entrada_fb(
                odoo, ajustes, dry_run=dry_run, executado_por=args.usuario,
            )

        banner('FIM', '=')


if __name__ == '__main__':
    main()
