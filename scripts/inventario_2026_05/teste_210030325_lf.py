# etapa: orquestrador
# doc-dono: scripts/inventario_2026_05/INDEX.md
"""Teste piloto end-to-end — produto 210030325 LF (INVENTARIO_2026_05).

Produto no Odoo: id=28239
    `[210030325] ROTULO - MOLHO DE ALHO PET 150 ML - CAMPO BELO`

Orquestra os 6 ajustes do caso piloto (ids 139003-139008):
- 4 TRANSFERIR_LOTE: consolidam 82.300 un no lote `26014` na LF
  (transferencia de quantidade entre lotes — D004 atualizada 2026-05-18)
- 2 PERDA_LF_FB: enviam 66.532 un para lote MIGRACAO na FB (CFOP 5903)

ABORDAGEM (apos correcao 2026-05-18 — NAO renomear lote):
    Cada ajuste "RENOMEAR_LOTE" no DB e' interpretado como TRANSFERIR_LOTE,
    via StockInternalTransferService.transferir_quantidade_para_lote() —
    preserva os lotes originais e movimenta apenas a quantidade especifica
    indicada (qtd_inventario do ajuste), sem afetar o restante.

Pipeline:
    [opcional canary F7.6] NF 13075 referencia historica vs payload proposto
    1. Pre-flight: resolve product_id, mapeia quants reais, detecta gaps
    2. Garantir lote 26014 na LF (criar_se_nao_existe)
    3. TRANSFERIR 4x via StockInternalTransferService (mesma location de
       cada quant — usa inventory adjustment standard do Odoo)
    4. F5a — criar 1 picking LF->FB com 2 linhas (lotes originais que
       restaram apos as transferencias)
    5. F5b — validar picking (confirm + assign + button_validate)
    6. F5c — liberar_faturamento
    7. F5d — aguardar invoice do robo CIEL IT (~3min)
    8. F5e — transmitir SEFAZ via Playwright [IRREVERSIVEL]

Flags:
    --dry-run             (default) simula tudo, nao toca Odoo
    --confirmar           executa transferencias + picking + F5b-F5d (sem SEFAZ)
    --confirmar-sefaz     ALEM de --confirmar, executa F5e Playwright
    --skip-transferencias pula etapas de transferir lote
    --pular-canary        pula canary F7.6
    --usuario X           usuario (auditoria)

Uso tipico:
    # 1. Dry-run: ver plano + pre-requisitos + canary
    python scripts/inventario_2026_05/teste_210030325_lf.py --dry-run

    # 2. Real (sem SEFAZ): executar ate aguardar invoice
    python scripts/inventario_2026_05/teste_210030325_lf.py --confirmar --usuario=rafael

    # 3. Real (com SEFAZ): completar transmissao
    python scripts/inventario_2026_05/teste_210030325_lf.py --confirmar --confirmar-sefaz --usuario=rafael

CRITERIOS DE SUCESSO (validar pos-execucao via 08_extrair_pos_execucao.py):
- LF: cod 210030325 lote '26014' com ~82.300 un consolidado
  (em ate 2 quants: LF/Estoque + LF/Pre-Producao, conforme distribuicao
   atual dos lotes origem)
- FB: cod 210030325 lote 'MIGRACAO' com +66.532 un
- 1 NF CFOP 5903 emitida (chave SEFAZ 44 digitos)
- operacao_odoo_auditoria com 6-10 rows do ciclo+ajuste

Spec: docs/inventario-2026-05/CHECKPOINT_2026_05_17_FIM_DIA.md
"""
import argparse
import json
import logging
import sys
from decimal import Decimal
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_THIS = Path(__file__).resolve()
sys.path.insert(0, str(_THIS.parents[2]))

from app import create_app, db  # noqa: E402 # type: ignore
from app.odoo.constants.locations import COMPANY_LOCATIONS  # noqa: E402 # type: ignore
from app.odoo.constants.operacoes_fiscais import (  # noqa: E402 # type: ignore
    COMPANY_PARTNER_ID,
    MATRIZ_INTERCOMPANY,
    resolver_fiscal_position,
)
from app.odoo.models import AjusteEstoqueInventario  # noqa: E402 # type: ignore
from app.odoo.services.inventario_pipeline_service import (  # noqa: E402 # type: ignore
    InventarioPipelineService,
    resolver_location_destino,
)
from app.odoo.services.stock_internal_transfer_service import (  # noqa: E402 # type: ignore
    StockInternalTransferService,
)
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402 # type: ignore
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402 # type: ignore

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-8s %(name)s | %(message)s',
)
logger = logging.getLogger('teste_piloto')

CICLO = 'INVENTARIO_2026_05'
COD_PILOTO = '210030325'
COMPANY_LF = 5
COMPANY_FB = 1
LOTE_ALVO = '26014'
LOTE_FB_DESTINO = 'MIGRACAO'
PICKING_TYPE_LF_PERDA = 94  # LF Expedicao N Aplicado (audit 00e)
PARTNER_FB = COMPANY_PARTNER_ID[COMPANY_FB]
LOCATION_LF = COMPANY_LOCATIONS[COMPANY_LF]
LOCATION_DESTINO_PERDA = resolver_location_destino('perda', COMPANY_FB)

# Canary F7.6 (D004 — operacoes_fiscais.py)
NF_REFERENCIA_ID = MATRIZ_INTERCOMPANY['perda']['account_move_id_referencia']  # 588209
FISCAL_POSITION_ESPERADA = resolver_fiscal_position('perda', COMPANY_LF, COMPANY_FB)  # 91


# ============================================================
# Helpers
# ============================================================

def banner(titulo: str, char: str = '=') -> None:
    """Imprime banner visual."""
    print()
    print(char * 72)
    print(f'  {titulo}')
    print(char * 72)


def resolver_product_id(odoo, cod_produto: str) -> Tuple[int, str]:
    """Resolve product.product.id pelo default_code. Retorna (id, name)."""
    res = odoo.search_read(
        'product.product',
        [['default_code', '=', cod_produto]],
        ['id', 'name', 'default_code'],
        limit=1,
    )
    if not res:
        raise RuntimeError(
            f'product.default_code={cod_produto!r} nao encontrado no Odoo'
        )
    p = res[0]
    print(f'  product_id={p["id"]}  name={p["name"]!r}')
    return p['id'], p['name']


def buscar_ajustes_piloto() -> List[AjusteEstoqueInventario]:
    """Retorna os 6 ajustes do caso piloto, ordenados por id."""
    ajustes = (
        AjusteEstoqueInventario.query
        .filter_by(ciclo=CICLO, cod_produto=COD_PILOTO, company_id=COMPANY_LF)
        .order_by(AjusteEstoqueInventario.id)
        .all()
    )
    if not ajustes:
        raise RuntimeError(
            f'Nenhum ajuste encontrado para ciclo={CICLO} cod={COD_PILOTO} '
            f'company={COMPANY_LF}. Caso piloto nao foi proposto?'
        )
    return ajustes


def descrever_ajuste(a: AjusteEstoqueInventario) -> str:
    """Linha legivel de 1 ajuste."""
    return (
        f'  id={a.id:>6}  {a.acao_decidida:<22}  '
        f'lote_origem={(a.lote_origem or "(sem lote)"):<10}  '
        f'lote_destino={(a.lote_destino or "-"):<10}  '
        f'qty_ref={a.qtd_inventario:>10}  qty_ajuste={a.qtd_ajuste:>12}  '
        f'status={a.status}  fase={a.fase_pipeline or "-"}'
    )


# ============================================================
# Pre-flight + plano de transferencias
# ============================================================

def mapear_quants_por_lote(odoo, product_id: int) -> Dict:
    """Lista todos os quants do produto na LF (internal locations).

    Retorna dict {nome_lote_str: [{quant_id, lot_id, location_id, location_name, qty, reserved}]}.
    Quants sem lote ficam em chave '(sem lote)'.
    """
    quants = odoo.search_read(
        'stock.quant',
        [
            ['product_id', '=', product_id],
            ['company_id', '=', COMPANY_LF],
            ['location_id.usage', '=', 'internal'],
            ['quantity', '!=', 0],
        ],
        ['id', 'lot_id', 'location_id', 'quantity', 'reserved_quantity'],
    )
    por_lote: Dict[str, List[Dict]] = {}
    for q in quants:
        lname = q['lot_id'][1] if q.get('lot_id') else '(sem lote)'
        por_lote.setdefault(lname, []).append({
            'quant_id': q['id'],
            'lot_id': q['lot_id'][0] if q.get('lot_id') else None,
            'location_id': q['location_id'][0] if q.get('location_id') else None,
            'location_name': q['location_id'][1] if q.get('location_id') else None,
            'qty': float(q['quantity']),
            'reserved': float(q.get('reserved_quantity') or 0),
        })
    return por_lote


def montar_plano_transferencia(
    ajuste: AjusteEstoqueInventario, quants_por_lote: Dict,
) -> Optional[Dict]:
    """Para 1 ajuste RENOMEAR/TRANSFERIR, define qual quant origem usar.

    Estrategia: combina lote_origem com qtd_inventario (qty exata pedida)
    para resolver ambiguidade quando ha multiplos quants do mesmo lote.

    Retorna None se nao for possivel resolver (warning sera emitido).
    """
    chave = (ajuste.lote_origem or '').strip() or '(sem lote)'
    quants = quants_por_lote.get(chave, [])
    if not quants:
        return None

    qty_pedida = float(ajuste.qtd_inventario or 0)
    # Priorizacao:
    # 1. Quant com qty == qty_pedida (match exato)
    # 2. Quant com qty > qty_pedida (transferencia parcial)
    # 3. Fallback: primeiro disponivel
    exatos = [q for q in quants if q['qty'] == qty_pedida]
    if exatos:
        escolhido = exatos[0]
        modo = 'EXATO'
    else:
        maiores = [q for q in quants if q['qty'] >= qty_pedida]
        if maiores:
            # Pega o quant com menor qty (parcial menor sobra)
            escolhido = sorted(maiores, key=lambda q: q['qty'])[0]
            modo = 'PARCIAL'
        else:
            escolhido = quants[0]
            modo = 'FALLBACK_INSUFICIENTE'

    return {
        'ajuste_id': ajuste.id,
        'quant_origem_id': escolhido['quant_id'],
        'lot_id_origem': escolhido['lot_id'],
        'lote_origem_nome': chave,
        'location_id': escolhido['location_id'],
        'location_name': escolhido['location_name'],
        'qty_no_quant': escolhido['qty'],
        'qty_a_transferir': qty_pedida,
        'lote_destino_nome': ajuste.lote_destino or LOTE_ALVO,
        'modo': modo,
    }


def preflight(
    odoo, ajustes: List[AjusteEstoqueInventario], product_id: int,
) -> Dict:
    """Verifica pre-requisitos e monta plano de transferencias."""
    banner('PRE-FLIGHT — quants atuais e plano de transferencia', '-')
    warnings: List[str] = []

    # Listar todos os quants do produto na LF
    quants_por_lote = mapear_quants_por_lote(odoo, product_id)
    print(f'  Quants encontrados na LF (cid={COMPANY_LF}):')
    soma_lf = Decimal('0')
    for lname, lista in quants_por_lote.items():
        for q in lista:
            soma_lf += Decimal(str(q['qty']))
            print(
                f"    quant {q['quant_id']:>6}  loc=[{q['location_id']}] "
                f"{q['location_name']:<32}  lote={lname:<14}  qty={q['qty']:>10}  reserv={q['reserved']}"
            )
    print(f'  TOTAL LF: {soma_lf} un')

    # Verificar saldo Odoo vs ajustes
    soma_ajustes_qtd_odoo = sum(
        Decimal(str(a.qtd_odoo or 0)) for a in ajustes
    )
    print(f'  TOTAL qtd_odoo dos ajustes: {soma_ajustes_qtd_odoo} un')
    if soma_lf != soma_ajustes_qtd_odoo:
        warnings.append(
            f'Divergencia saldo Odoo atual ({soma_lf}) vs ajustes '
            f'({soma_ajustes_qtd_odoo}). Estado pode ter mudado desde script 03.'
        )

    # Verificar se ja existe lote alvo (26014) na LF
    lot_svc = StockLotService(odoo=odoo)
    lot_id_alvo_existente = lot_svc.buscar_por_nome(
        LOTE_ALVO, product_id, COMPANY_LF,
    )
    if lot_id_alvo_existente:
        print(f'  Lote alvo {LOTE_ALVO!r} JA existe na LF: lot_id={lot_id_alvo_existente}')
    else:
        print(f'  Lote alvo {LOTE_ALVO!r} NAO existe na LF — sera criado na etapa 1.')

    # Montar plano de transferencia para cada ajuste RENOMEAR/TRANSFERIR
    rename_ajustes = [
        a for a in ajustes
        if a.acao_decidida in ('RENOMEAR_LOTE', 'TRANSFERIR_LOTE')
    ]
    perda_ajustes = [a for a in ajustes if a.acao_decidida == 'PERDA_LF_FB']

    plano_transferencia: List[Dict] = []
    for a in rename_ajustes:
        plano = montar_plano_transferencia(a, quants_por_lote)
        if plano is None:
            warnings.append(
                f'Ajuste {a.id} ({a.acao_decidida}): nao foi possivel encontrar '
                f'quant para lote_origem={a.lote_origem!r}'
            )
            continue
        plano_transferencia.append(plano)
        if plano['modo'] == 'FALLBACK_INSUFICIENTE':
            warnings.append(
                f'Ajuste {a.id}: quant origem {plano["quant_origem_id"]} tem '
                f'{plano["qty_no_quant"]} un, mas ajuste pede transferir '
                f'{plano["qty_a_transferir"]} un. Insuficiente.'
            )

    # Montar linhas do picking PERDA (a partir dos ajustes PERDA, usando
    # os quants restantes apos as transferencias)
    perda_linhas: List[Dict] = []
    # Pegar primeiro location LF/Estoque (id=42) como destino do picking
    # (porque os quants de perda no caso piloto estao em location 42).
    location_origem_picking = LOCATION_LF
    for a in perda_ajustes:
        qty = abs(float(a.qtd_ajuste))
        lote_origem = (a.lote_origem or a.lote_odoo or '').strip()
        if not lote_origem:
            warnings.append(
                f'Ajuste PERDA {a.id} sem lote definido (origem={a.lote_origem!r} '
                f'odoo={a.lote_odoo!r}).'
            )
        # Garante que sobra o lote origem com qty suficiente apos transferencias
        sobra_apos_transf = Decimal('0')
        for q in quants_por_lote.get(lote_origem, []):
            if q['location_id'] == location_origem_picking:
                sobra_apos_transf += Decimal(str(q['qty']))
        # Descontar o que foi transferido desse lote/location
        for plano in plano_transferencia:
            if (
                plano['lote_origem_nome'] == lote_origem
                and plano['location_id'] == location_origem_picking
            ):
                sobra_apos_transf -= Decimal(str(plano['qty_a_transferir']))
        sobra_apos_transf = float(sobra_apos_transf)
        if sobra_apos_transf < qty - 0.01:
            warnings.append(
                f'Ajuste PERDA {a.id} ({lote_origem}, loc={location_origem_picking}): '
                f'sobra apos transferencias {sobra_apos_transf} un < '
                f'qty necessaria {qty} un.'
            )
        perda_linhas.append({
            'ajuste_id': a.id,
            'lote_origem_nome': lote_origem,
            'qty': qty,
            'sobra_esperada_pre_picking': sobra_apos_transf,
        })

    print()
    print(f'  Plano de transferencia: {len(plano_transferencia)} operacoes')
    for p in plano_transferencia:
        print(
            f"    ajuste {p['ajuste_id']}: transferir {p['qty_a_transferir']} un "
            f"do quant {p['quant_origem_id']} (lote={p['lote_origem_nome']!r}, "
            f"loc=[{p['location_id']}] {p['location_name']}) → lote "
            f"{p['lote_destino_nome']!r}  modo={p['modo']}"
        )
    print(f'  Linhas do picking PERDA: {len(perda_linhas)}')
    for ln in perda_linhas:
        print(
            f"    ajuste {ln['ajuste_id']}: {ln['qty']} un do lote "
            f"{ln['lote_origem_nome']!r}  (sobra esperada: {ln['sobra_esperada_pre_picking']} un)"
        )

    if warnings:
        print(f'\n  WARNINGS: {len(warnings)}')
        for w in warnings:
            print(f'    [!] {w}')
    else:
        print('\n  Sem warnings detectados.')

    return {
        'quants_por_lote': quants_por_lote,
        'lot_id_alvo_existente': lot_id_alvo_existente,
        'plano_transferencia': plano_transferencia,
        'perda_linhas': perda_linhas,
        'warnings': warnings,
        'location_origem_picking': location_origem_picking,
    }


# ============================================================
# Canary F7.6 — comparar com NF historica 13075
# ============================================================

def canary_f76(odoo) -> Dict:
    """Compara campos fiscais da NF 13075 (referencia historica) com
    payload que sera enviado.
    """
    banner('CANARY F7.6 — NF 13075 (historica) vs proposta', '-')
    referencia = odoo.read(
        'account.move', [NF_REFERENCIA_ID],
        [
            'name', 'state', 'move_type', 'fiscal_position_id',
            'l10n_br_tipo_pedido', 'partner_id', 'company_id', 'amount_total',
            'invoice_line_ids',
        ],
    )
    if not referencia:
        print(f'  NF referencia id={NF_REFERENCIA_ID} nao encontrada no Odoo.')
        return {'ok': False, 'divergencias': ['referencia_nao_encontrada'],
                'referencia': None, 'proposta': None}
    ref = referencia[0]
    line_ids = ref.get('invoice_line_ids') or []
    cfops = []
    if line_ids:
        line_data = odoo.read(
            'account.move.line', line_ids[:5], ['l10n_br_cfop_id', 'name'],
        )
        cfops = [
            ld['l10n_br_cfop_id'][1] if ld.get('l10n_br_cfop_id') else None
            for ld in line_data
        ]
    proposta = {
        'fiscal_position_id': FISCAL_POSITION_ESPERADA,
        'l10n_br_tipo_pedido': 'perda',
        'partner_id': PARTNER_FB,
        'company_origem': COMPANY_LF,
        'company_destino': COMPANY_FB,
        'cfop_esperado': MATRIZ_INTERCOMPANY['perda']['cfop_esperado'][(5, 1)],
    }
    ref_fp_id = ref['fiscal_position_id'][0] if ref.get('fiscal_position_id') else None
    ref_tipo = ref.get('l10n_br_tipo_pedido')
    ref_partner_id = ref['partner_id'][0] if ref.get('partner_id') else None
    ref_company_id = ref['company_id'][0] if ref.get('company_id') else None

    print(f'  Referencia NF {ref.get("name")} (move_id={NF_REFERENCIA_ID}):')
    print(f'    state                = {ref.get("state")}')
    print(f'    fiscal_position_id   = {ref_fp_id}')
    print(f'    l10n_br_tipo_pedido  = {ref_tipo}')
    print(f'    partner_id           = {ref_partner_id}')
    print(f'    company_id           = {ref_company_id}')
    print(f'    cfops (linhas)       = {cfops}')
    print()
    print('  Proposta (caso piloto 210030325):')
    for k, v in proposta.items():
        print(f'    {k:<22} = {v}')

    divergencias = []
    if ref_fp_id != FISCAL_POSITION_ESPERADA:
        divergencias.append(
            f'fiscal_position_id divergente: ref={ref_fp_id} vs '
            f'proposta={FISCAL_POSITION_ESPERADA}'
        )
    if ref_tipo and ref_tipo != 'perda':
        divergencias.append(
            f'l10n_br_tipo_pedido divergente: ref={ref_tipo} vs proposta=perda'
        )
    if ref_partner_id != PARTNER_FB:
        divergencias.append(
            f'partner_id divergente: ref={ref_partner_id} vs proposta={PARTNER_FB}'
        )
    if divergencias:
        print(f'\n  DIVERGENCIAS ({len(divergencias)}):')
        for d in divergencias:
            print(f'    [!] {d}')
    else:
        print('\n  Canary OK — campos fiscais convergem.')
    return {
        'ok': not divergencias, 'divergencias': divergencias,
        'referencia': {
            'fiscal_position_id': ref_fp_id, 'tipo': ref_tipo,
            'partner_id': ref_partner_id, 'cfops': cfops,
        },
        'proposta': proposta,
    }


# ============================================================
# Etapa 1 — garantir lote alvo
# ============================================================

def garantir_lote_alvo(
    odoo, product_id: int, dry_run: bool,
) -> Optional[int]:
    """Cria lote 26014 na LF se nao existir. Retorna lot_id."""
    banner(f'ETAPA 1 — garantir lote {LOTE_ALVO!r} existe na LF', '-')
    lot_svc = StockLotService(odoo=odoo)
    existente = lot_svc.buscar_por_nome(LOTE_ALVO, product_id, COMPANY_LF)
    if existente:
        print(f'  Lote {LOTE_ALVO!r} ja existe na LF: lot_id={existente}')
        return existente
    if dry_run:
        print(f'  [DRY-RUN] criaria lote {LOTE_ALVO!r} na LF (product_id={product_id}).')
        return None
    novo, criado = lot_svc.criar_se_nao_existe(LOTE_ALVO, product_id, COMPANY_LF)
    print(f'  Lote {LOTE_ALVO!r} criado: lot_id={novo}  (criado_agora={criado})')
    return novo


# ============================================================
# Etapa 3 — picking LF→FB (perda)
# ============================================================

def executar_picking_perda(
    odoo, perda_linhas: List[Dict], product_id: int, dry_run: bool,
    executado_por: str, ajuste_index: Dict[int, AjusteEstoqueInventario],
) -> Optional[int]:
    """Cria 1 picking LF→FB com N linhas via StockPickingService."""
    banner('ETAPA 3 — CRIAR PICKING LF→FB (PERDA, CFOP 5903)', '-')
    print(f'  Executado por: {executado_por}')
    if not perda_linhas:
        print('  Nada para fazer (sem linhas de perda).')
        return None
    linhas_payload = [
        {
            'product_id': product_id,
            'quantity': ln['qty'],
            'lot_name': ln['lote_origem_nome'],
            'name': (
                f"Perda inv 2026-05 cod={COD_PILOTO} lote={ln['lote_origem_nome']}"
            ),
        }
        for ln in perda_linhas
    ]
    payload = {
        'company_origem_id': COMPANY_LF,
        'company_destino_id': COMPANY_FB,
        'location_origem_id': LOCATION_LF,
        'location_destino_id': LOCATION_DESTINO_PERDA,
        'picking_type_id': PICKING_TYPE_LF_PERDA,
        'partner_id': PARTNER_FB,
        'linhas': linhas_payload,
        'origin': f'INV-{CICLO}-PILOTO-{COD_PILOTO}',
    }
    print('  Payload do picking:')
    for k, v in payload.items():
        if k != 'linhas':
            print(f'    {k} = {v}')
    print('    linhas:')
    for linha in linhas_payload:
        print(f'      - {linha}')
    if dry_run:
        print('  [DRY-RUN] picking NAO criado.')
        return None
    from app.odoo.services.stock_picking_service import StockPickingService # type: ignore
    picking_svc = StockPickingService(odoo=odoo)
    picking_id = picking_svc.criar_transferencia(
        company_origem_id=COMPANY_LF,
        company_destino_id=COMPANY_FB,
        location_origem_id=LOCATION_LF,
        location_destino_id=LOCATION_DESTINO_PERDA,
        linhas=linhas_payload,
        picking_type_id=PICKING_TYPE_LF_PERDA,
        partner_id=PARTNER_FB,
        origin=payload['origin'],
    )
    print(f'  OK — picking_id = {picking_id}')
    for ln in perda_linhas:
        aj = ajuste_index.get(ln['ajuste_id'])
        if aj:
            aj.picking_id_odoo = picking_id
            aj.fase_pipeline = 'F5a_PICKING_CRIADO'
            db.session.commit()
    return picking_id


# ============================================================
# Etapas F5b..F5e via InventarioPipelineService
# ============================================================

def executar_pos_picking(
    odoo, ajustes_perda: List[AjusteEstoqueInventario],
    dry_run: bool, executado_por: str, transmitir_sefaz: bool,
) -> None:
    if dry_run:
        banner('ETAPAS 4-7 — pipeline pos-picking (DRY-RUN)', '-')
        print('  [DRY-RUN] f5b (validar) → f5c (liberar) → f5d (aguardar invoice) '
              '→ f5e (SEFAZ) — nao executados.')
        return
    svc = InventarioPipelineService(odoo=odoo)
    banner('ETAPA 4 — F5b validar picking', '-')
    svc.f5b_validar_pickings(ajustes_perda, executado_por=executado_por)
    banner('ETAPA 5 — F5c liberar faturamento (dispara robo CIEL IT)', '-')
    svc.f5c_liberar_faturamento(ajustes_perda, executado_por=executado_por)
    banner('ETAPA 6 — F5d aguardar invoice do robo CIEL IT (~3 min)', '-')
    svc.f5d_aguardar_invoices(
        ajustes_perda, timeout=1800, poll_interval=40,
        executado_por=executado_por,
    )
    if transmitir_sefaz:
        banner('ETAPA 7 — F5e transmitir SEFAZ (Playwright — IRREVERSIVEL)', '!')
        svc.f5e_transmitir_sefaz(ajustes_perda, executado_por=executado_por)
    else:
        print()
        print('  F5e (SEFAZ) NAO executado (faltou --confirmar-sefaz).')
        print('  Para finalizar: rode novamente com --confirmar --confirmar-sefaz')


# ============================================================
# Main
# ============================================================

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--company-id', type=int, required=True,
        choices=[1, 4, 5],
        help='Empresa onde rodar o piloto (1=FB, 4=CD, 5=LF). '
             'OBRIGATORIO — regra do usuario: scripts sempre tem --company-id.',
    )
    parser.add_argument('--cod-produto', default=COD_PILOTO,
                        help=f'cod_produto (default: {COD_PILOTO})')
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--confirmar', action='store_true',
                        help='executa transferencias + picking + F5b-F5d (sem SEFAZ)')
    parser.add_argument('--confirmar-sefaz', action='store_true',
                        help='executa tambem F5e SEFAZ Playwright (irreversivel)')
    parser.add_argument('--skip-transferencias', action='store_true',
                        help='pula etapas 1-2 (assumir transferencias ja feitas)')
    parser.add_argument('--pular-canary', action='store_true')
    parser.add_argument('--usuario', default='teste_piloto')
    parser.add_argument('--json-out', default=None)
    args = parser.parse_args()

    dry_run = not args.confirmar
    if args.confirmar_sefaz and not args.confirmar:
        print('ERRO: --confirmar-sefaz exige --confirmar')
        sys.exit(2)

    # Validacao: este script foi instrumentado para LF (cid=5).
    # Outros valores exigem refatoracao de constantes (picking_type,
    # location, fiscal_position). Bloqueamos por seguranca.
    if args.company_id != COMPANY_LF:
        print(
            f'ERRO: --company-id={args.company_id} ainda nao suportado. '
            f'Este wrapper esta calibrado para LF (cid={COMPANY_LF}). '
            f'Outras empresas exigem ajustar PICKING_TYPE_*, LOCATION_*, '
            f'fiscal_position antes — ver MATRIZ_INTERCOMPANY.'
        )
        sys.exit(6)

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        banner(f'TESTE PILOTO {args.cod_produto} (modo={"DRY-RUN" if dry_run else "REAL"})')
        print(f'  Ciclo: {CICLO}')
        print(f'  Cod produto: {args.cod_produto}  Company origem={args.company_id}  destino FB={COMPANY_FB}')
        print(f'  Lote alvo (origem): {LOTE_ALVO}')
        print(f'  Lote destino (FB): {LOTE_FB_DESTINO}')
        print(f'  Picking type LF perda: {PICKING_TYPE_LF_PERDA}')
        print(f'  Usuario: {args.usuario}')

        ajustes = buscar_ajustes_piloto()
        ajuste_index = {a.id: a for a in ajustes}
        banner(f'AJUSTES DO CASO PILOTO ({len(ajustes)} encontrados)', '-')
        for a in ajustes:
            print(descrever_ajuste(a))

        status_set = {a.status for a in ajustes}
        if 'APROVADO' not in status_set and not dry_run:
            print()
            print('  [!] Nenhum ajuste APROVADO. Pipeline real exige aprovacao.')
            print('  Rode: 04_propor_ajustes.py --listar-onda=1, capture hash,')
            print(f'         depois --aprovar-onda=1 --hash=<sha> --usuario={args.usuario}')
            sys.exit(3)

        banner('PRODUCT.PRODUCT lookup', '-')
        product_id, product_name = resolver_product_id(odoo, COD_PILOTO)

        canary = None
        if not args.pular_canary:
            canary = canary_f76(odoo)
            if canary['divergencias'] and not dry_run:
                print('\n  [!] Canary F7.6 reportou divergencias. ABORTANDO modo --confirmar.')
                sys.exit(4)

        pre = preflight(odoo, ajustes, product_id)
        if pre['warnings'] and not dry_run:
            print('\n  [!] Pre-flight reportou warnings. Use --skip-transferencias se ja foi tratado.')
            if not args.skip_transferencias:
                sys.exit(5)

        # ETAPA 1: garantir lote alvo
        lot_id_alvo = None
        if not args.skip_transferencias:
            lot_id_alvo = garantir_lote_alvo(odoo, product_id, dry_run)

        # ETAPA 2: transferencias
        transferencias_resultados: List[Dict] = []
        if args.skip_transferencias:
            banner('ETAPA 2 — TRANSFERENCIAS (SKIP, --skip-transferencias ativo)', '-')
        else:
            transferencias_resultados = _executar_transferencias_inline(
                odoo, pre['plano_transferencia'], product_id,
                lot_id_alvo, dry_run, args.usuario, ajuste_index,
            )

        # ETAPA 3: picking
        picking_id = executar_picking_perda(
            odoo, pre['perda_linhas'], product_id, dry_run, args.usuario, ajuste_index,
        )

        # ETAPAS 4-7
        ajustes_perda = [a for a in ajustes if a.acao_decidida == 'PERDA_LF_FB']
        if not dry_run and picking_id:
            db.session.expire_all()
            ajustes_perda = [
                a for a in buscar_ajustes_piloto()
                if a.acao_decidida == 'PERDA_LF_FB'
            ]
        executar_pos_picking(
            odoo, ajustes_perda, dry_run, args.usuario, args.confirmar_sefaz,
        )

        # Resumo final
        banner('RESUMO', '=')
        ajustes_final = buscar_ajustes_piloto()
        for a in ajustes_final:
            print(descrever_ajuste(a))
        if dry_run:
            print()
            print('  Modo DRY-RUN — nada foi executado no Odoo.')
            print('  Proximos passos (apos revisar plano acima):')
            print('    1. Aprovar onda 1 via 04_propor_ajustes.py --aprovar-onda=1 --hash=<sha>')
            print('    2. Rodar este script com --confirmar --usuario=rafael')
            print('    3. Apos invoice criada: --confirmar --confirmar-sefaz')

        if args.json_out:
            payload = {
                'ciclo': CICLO, 'cod_produto': COD_PILOTO,
                'product_id': product_id, 'product_name': product_name,
                'modo': 'dry-run' if dry_run else 'real',
                'usuario': args.usuario,
                'canary': canary,
                'preflight': {
                    'warnings': pre['warnings'],
                    'plano_transferencia': pre['plano_transferencia'],
                    'perda_linhas': pre['perda_linhas'],
                    'quants_por_lote_antes': pre['quants_por_lote'],
                    'lot_id_alvo_existente': pre['lot_id_alvo_existente'],
                },
                'lot_id_alvo': lot_id_alvo,
                'transferencias': transferencias_resultados,
                'picking_id': picking_id,
                'ajustes_pos_execucao': [
                    {
                        'id': a.id, 'acao': a.acao_decidida, 'status': a.status,
                        'fase_pipeline': a.fase_pipeline,
                        'picking_id_odoo': a.picking_id_odoo,
                        'invoice_id_odoo': a.invoice_id_odoo,
                        'chave_nfe': a.chave_nfe, 'erro_msg': a.erro_msg,
                    }
                    for a in ajustes_final
                ],
            }
            with open(args.json_out, 'w') as f:
                json.dump(payload, f, indent=2, default=str)
            print(f'\n  Resumo JSON: {args.json_out}')


def _executar_transferencias_inline(
    odoo, plano: List[Dict], product_id: int, lot_id_alvo: Optional[int],
    dry_run: bool, executado_por: str,
    ajuste_index: Dict[int, AjusteEstoqueInventario],
) -> List[Dict]:
    """Variante inline (com product_id real) que executa todas as
    transferencias do plano via StockInternalTransferService.

    `lot_id_alvo` e' passado apenas para informar no log; nao e' necessario
    nas chamadas porque cada transferencia passa nome_lote_destino e o
    service resolve via criar_se_nao_existe.
    """
    banner('ETAPA 2 — TRANSFERIR quantidades para lote alvo', '-')
    print(f'  Executado por: {executado_por}  lot_id_alvo(se ja existia)={lot_id_alvo}')
    if dry_run:
        print(f'  [DRY-RUN] {len(plano)} transferencias seriam executadas.')
    svc = StockInternalTransferService(odoo=odoo)
    resultados: List[Dict] = []
    for p in plano:
        aj_id = p['ajuste_id']
        prefixo = '[DRY-RUN] ' if dry_run else ''
        print(
            f"  {prefixo}Ajuste {aj_id}: transferir {p['qty_a_transferir']} un "
            f"do quant {p['quant_origem_id']} (lote {p['lote_origem_nome']!r}, "
            f"loc=[{p['location_id']}] {p['location_name']}) → lote "
            f"{p['lote_destino_nome']!r}  modo={p['modo']}"
        )
        if p['modo'] == 'FALLBACK_INSUFICIENTE':
            print(f'    [!] SKIP — qty insuficiente')
            resultados.append({'ajuste_id': aj_id, 'sucesso': False,
                               'erro': 'insuficiente', 'modo': p['modo']})
            if not dry_run:
                aj = ajuste_index.get(aj_id)
                if aj:
                    aj.fase_pipeline = 'TRANSF_SKIP'
                    aj.erro_msg = 'qty no quant origem insuficiente'
                    db.session.commit()
            continue
        if dry_run:
            resultados.append({'ajuste_id': aj_id, 'sucesso': None,
                               'erro': None, 'modo': p['modo']})
            continue
        try:
            res = svc.transferir_quantidade_para_lote(
                product_id=product_id, company_id=COMPANY_LF,
                location_id=p['location_id'],
                qty=p['qty_a_transferir'],
                lot_id_origem=p['lot_id_origem'],
                nome_lote_destino=p['lote_destino_nome'],
            )
            resultados.append({'ajuste_id': aj_id, 'sucesso': True,
                               'erro': None, 'resultado': res,
                               'modo': p['modo']})
            aj = ajuste_index.get(aj_id)
            if aj:
                aj.fase_pipeline = 'TRANSF_OK'
                db.session.commit()
            print(
                f"    OK  quant_destino={res['quant_destino_id']}  "
                f"qty_destino_apos={res['quant_destino_qty_apos']}"
            )
        except Exception as e:
            msg = str(e)
            print(f'    FALHA: {msg}')
            resultados.append({'ajuste_id': aj_id, 'sucesso': False,
                               'erro': msg, 'modo': p['modo']})
            aj = ajuste_index.get(aj_id)
            if aj:
                aj.fase_pipeline = 'TRANSF_FALHA'
                aj.erro_msg = msg
                db.session.commit()
    return resultados


if __name__ == '__main__':
    main()
