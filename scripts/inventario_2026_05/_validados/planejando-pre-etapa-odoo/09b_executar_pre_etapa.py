"""F9b (D007) — Executor da Pre-etapa CD/FB (Onda 5/6).

⚠️ ARQUIVADO 2026-05-25 (sessao v9) — SUPERADO PELA SKILL 6.

Este script foi capinado para a Skill 6 `planejando-pre-etapa-odoo` modo
`executar-onda` (orchestrator C3 macro em
`app/odoo/estoque/orchestrators/pre_etapa_executor.py`).

USE A SKILL 6 modo `executar-onda` em vez deste script:
    SK=.claude/skills/planejando-pre-etapa-odoo/scripts/planejar_pre_etapa.py
    python "$SK" --modo executar-onda --company-id 4 --limite 1 --confirmar       # canary
    python "$SK" --modo executar-onda --company-id 4 --max-workers 5 --confirmar  # bulk paralelo
    python "$SK" --modo executar-onda --company-id 4 --cod-produto X --confirmar  # 1 produto especifico

Diferencas do capinado vs este script legacy:
- API v2 modernizada: `transferir_quantidade_para_lote` v1 -> v2 (guard
  delta_esperado propagado em ambos passos -origem/+destino — protege contra
  bug CICLAMATO 2026-05-23).
- POSITIVO_PURO refatorado: `odoo.create('stock.quant')` DIRETO -> Skill 1
  `ajustar_quant(criar_se_faltar=True, delta_esperado=qty)` — guard CICLAMATO.
- Output JSON estruturado (regra v7 "Log JSON e fonte de verdade") em vez de
  print/banner orientado a humano.
- Auditoria via OperacaoOdooAuditoria preservada.
- Paralelizacao via ThreadPoolExecutor preservada.

Este script permanece como REFERENCIA HISTORICA (museum vivo) — NAO executar.

============================================================
TEXTO ORIGINAL (referencia historica):
============================================================

Executa ajustes APROVADO de uma company:
- AJUSTE_{CID}_TRANSF_INTERNA_POS: transferir lote_origem → lote_destino
- AJUSTE_{CID}_TRANSF_INTERNA_NEG: transferir lote_origem → MIGRAÇÃO
- AJUSTE_{CID}_POSITIVO_PURO: inventory adjustment direto

Tudo via `StockInternalTransferService` (D006) ou `stock.quant.action_apply_inventory`.
NAO emite NF (operacoes 100% internas a company).

Pre-requisito: 04b_propor_pre_etapa_cd.py rodado + Onda 5 APROVADA via:
    python scripts/inventario_2026_05/04b_propor_pre_etapa_cd.py --listar-onda=5
    python scripts/inventario_2026_05/04b_propor_pre_etapa_cd.py \\
        --aprovar-onda=5 --hash=<sha> --usuario=rafael

Flags:
    --company-id={4,1}    OBRIGATORIO (4=CD, 1=FB futuro)
    --dry-run             (default) simula
    --confirmar           executa real
    --limite=N            executa N produtos primeiro (sub-piloto)
    --cod-produto=X       executa so 1 produto
    --usuario X           auditoria

Uso:
    # 1. Dry-run completo
    python scripts/inventario_2026_05/09b_executar_pre_etapa.py --company-id=4 --dry-run

    # 2. Sub-piloto: 10 produtos
    python scripts/inventario_2026_05/09b_executar_pre_etapa.py \\
        --company-id=4 --confirmar --limite=10 --usuario=rafael

    # 3. Bulk completo
    python scripts/inventario_2026_05/09b_executar_pre_etapa.py \\
        --company-id=4 --confirmar --usuario=rafael

CRITICO: rodar ANTES de Onda 2 (TRANSFERIR_FB_CD residual) — Onda 2
depende dos lotes alvo do CD existirem (criados aqui).

Spec: docs/inventario-2026-05/00-decisoes/D007-pre-etapa-cd-fb-minimizar-nf.md
"""
import argparse
import logging
import sys
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_THIS = Path(__file__).resolve()
# parents[4] porque o museum vivo esta em _validados/<skill>/ (4 niveis acima do root)
sys.path.insert(0, str(_THIS.parents[4]))

from app import create_app, db  # noqa: E402
from app.odoo.constants.locations import COMPANY_LOCATIONS  # noqa: E402
from app.odoo.models import (  # noqa: E402
    AjusteEstoqueInventario, OperacaoOdooAuditoria,
)
from app.odoo.services.stock_internal_transfer_service import (  # noqa: E402
    StockInternalTransferService,
)
from app.odoo.services.stock_lot_service import StockLotService  # noqa: E402
from app.odoo.utils.connection import get_odoo_connection  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)-7s %(name)s | %(message)s',
)
logger = logging.getLogger('09b_executar')

CICLO = 'INVENTARIO_2026_05'
LOTE_MIGRACAO = 'MIGRAÇÃO'

# Acoes da Onda 5 por company
ACOES_INTERNAS_POR_CID: Dict[int, Dict[str, str]] = {
    4: {  # CD
        'POS': 'AJUSTE_CD_TRANSF_INTERNA_POS',
        'NEG': 'AJUSTE_CD_TRANSF_INTERNA_NEG',
        'PURO': 'AJUSTE_CD_POSITIVO_PURO',
    },
    1: {  # FB (Onda 6 futura)
        'POS': 'AJUSTE_FB_TRANSF_INTERNA_POS',
        'NEG': 'AJUSTE_FB_TRANSF_INTERNA_NEG',
        'PURO': 'AJUSTE_FB_POSITIVO_PURO',
    },
}

# Mapeamento para auditoria: VARCHAR(20) constraint em operacao_odoo_auditoria.acao
# (nomes completos sao usados em acao_decidida do ajuste — sem limite de coluna).
ACAO_AUDIT_CURTA: Dict[str, str] = {
    'AJUSTE_CD_TRANSF_INTERNA_POS': 'cd_pre_pos',
    'AJUSTE_CD_TRANSF_INTERNA_NEG': 'cd_pre_neg',
    'AJUSTE_CD_POSITIVO_PURO': 'cd_pos_puro',
    'AJUSTE_FB_TRANSF_INTERNA_POS': 'fb_pre_pos',
    'AJUSTE_FB_TRANSF_INTERNA_NEG': 'fb_pre_neg',
    'AJUSTE_FB_POSITIVO_PURO': 'fb_pos_puro',
}


def banner(titulo: str, char: str = '=') -> None:
    print()
    print(char * 78)
    print(f'  {titulo}')
    print(char * 78)


def resolver_product_id(odoo, cod_produto: str) -> Optional[Tuple[int, str]]:
    """Resolve product.id pelo default_code (apenas active=True).

    Decisao usuario 2026-05-18: produtos arquivados (active=False) NAO
    sao processados pela pre-etapa. Ficam como FALHA com mensagem para
    revisao humana — reativar manualmente OU tratamento fora deste fluxo.
    """
    res = odoo.search_read(
        'product.product',
        [['default_code', '=', cod_produto]],
        ['id', 'name'],
        limit=1,
    )
    if not res:
        return None
    return res[0]['id'], res[0]['name']


def buscar_quants_produto_cid(
    odoo, product_id: int, company_id: int,
) -> List[Dict]:
    """Lista todos quants do produto na company, com lote nome + location."""
    quants = odoo.search_read(
        'stock.quant',
        [
            ['product_id', '=', product_id],
            ['company_id', '=', company_id],
            ['location_id.usage', '=', 'internal'],
        ],
        ['id', 'lot_id', 'location_id', 'quantity', 'reserved_quantity'],
    )
    out = []
    for q in quants:
        out.append({
            'quant_id': q['id'],
            'lot_id': q['lot_id'][0] if q.get('lot_id') else None,
            'lote_nome': q['lot_id'][1] if q.get('lot_id') else '',
            'location_id': q['location_id'][0] if q.get('location_id') else None,
            'location_nome': q['location_id'][1] if q.get('location_id') else '',
            'quantity': float(q['quantity']),
            'reserved': float(q.get('reserved_quantity', 0) or 0),
        })
    return out


def localizar_doador(
    quants: List[Dict], lote_nome_origem: str, qty_pedida: float,
) -> Optional[Dict]:
    """Encontra quant que pode doar qty_pedida do lote_nome_origem.

    Estrategia:
        1. Quant com lote_nome igual e qty >= pedida (match exato ou parcial)
        2. Quant com qty maior (parcial)
        3. Soma de N quants do mesmo lote (split entre quants)
            — nao implementado nesta versao, retorna o primeiro disponivel
    """
    candidatos = [
        q for q in quants
        if (q['lote_nome'] or '') == (lote_nome_origem or '')
        and q['quantity'] >= qty_pedida - 0.001
    ]
    if candidatos:
        # Preferir o quant com menor sobra (parcial menor)
        return sorted(candidatos, key=lambda q: q['quantity'])[0]
    # Fallback: qualquer quant do mesmo lote (pode ter qty insuficiente)
    fallback = [q for q in quants if (q['lote_nome'] or '') == (lote_nome_origem or '')]
    return fallback[0] if fallback else None


def registrar_auditoria(
    *, ajuste_id: int, acao: str, status: str,
    payload: Optional[Dict] = None, resposta: Optional[Dict] = None,
    erro_msg: Optional[str] = None, tempo_ms: Optional[int] = None,
    executado_por: str = 'sistema',
) -> None:
    """Registra operacao em operacao_odoo_auditoria (contexto pre_etapa)."""
    try:
        OperacaoOdooAuditoria.registrar(
            external_id=f'PREETAPA-{acao}-{ajuste_id}-{uuid.uuid4().hex[:8]}',
            tabela_origem='ajuste_estoque_inventario',
            registro_id=ajuste_id,
            acao=acao,
            modelo_odoo='stock.quant',
            etapa=None,
            etapa_descricao=f'{acao} pre-etapa',
            status=status,
            payload_json=payload,
            resposta_json=resposta,
            erro_msg=erro_msg,
            tempo_execucao_ms=tempo_ms,
            pipeline_etapa='ONDA_5_PRE_ETAPA',
            contexto_origem='pre_etapa',
            contexto_ref=CICLO,
            executado_por=executado_por,
        )
    except Exception as e:
        logger.error(f'auditoria falhou: {e}', exc_info=True)


def executar_transferencia_interna(
    transfer_svc: StockInternalTransferService,
    lot_svc: StockLotService,
    ajuste: AjusteEstoqueInventario,
    product_id: int,
    quants_atuais: List[Dict],
    location_principal: int,
    dry_run: bool,
    executado_por: str,
) -> Dict:
    """Executa 1 transferencia POS ou NEG.

    Returns: dict {sucesso, erro, transferido_qty}
    """
    qty = float(ajuste.qtd_inventario if ajuste.qtd_inventario else ajuste.qtd_odoo)
    if qty <= 0:
        return {'sucesso': False, 'erro': 'qty<=0'}
    lote_origem = ajuste.lote_origem or ''
    lote_destino = ajuste.lote_destino or LOTE_MIGRACAO
    cid = ajuste.company_id

    doador = localizar_doador(quants_atuais, lote_origem, qty)
    if not doador:
        return {
            'sucesso': False,
            'erro': f'quant origem nao encontrado para lote={lote_origem!r}',
        }

    if doador['quantity'] < qty - 0.001:
        return {
            'sucesso': False,
            'erro': (
                f'quant origem {doador["quant_id"]} tem '
                f'{doador["quantity"]} un, ajuste pede {qty}'
            ),
        }

    if dry_run:
        print(
            f'    [DRY] ajuste {ajuste.id} {ajuste.acao_decidida}: '
            f'transferir {qty} un do quant {doador["quant_id"]} '
            f'(lote={lote_origem!r}, loc=[{doador["location_id"]}] '
            f'{doador["location_nome"]}) → lote {lote_destino!r}'
        )
        return {'sucesso': None, 'erro': None}

    inicio = time.time()
    try:
        res = transfer_svc.transferir_quantidade_para_lote(
            product_id=product_id,
            company_id=cid,
            location_id=doador['location_id'],
            qty=qty,
            lot_id_origem=doador['lot_id'],
            nome_lote_destino=lote_destino,
        )
        tempo_ms = int((time.time() - inicio) * 1000)
        registrar_auditoria(
            ajuste_id=ajuste.id,
            acao=ACAO_AUDIT_CURTA.get(ajuste.acao_decidida, ajuste.acao_decidida[:20]),
            status='SUCESSO',
            payload={
                'product_id': product_id, 'qty': qty,
                'lot_id_origem': doador['lot_id'],
                'lote_destino': lote_destino,
                'location_id': doador['location_id'],
            },
            resposta=res, tempo_ms=tempo_ms,
            executado_por=executado_por,
        )
        ajuste.status = 'EXECUTADO'
        ajuste.fase_pipeline = 'INTERNO_OK'
        db.session.commit()
        # Atualizar quants_atuais (subtrair qty do doador)
        doador['quantity'] -= qty
        return {'sucesso': True, 'transferido_qty': qty, 'tempo_ms': tempo_ms}
    except Exception as e:
        tempo_ms = int((time.time() - inicio) * 1000)
        msg = str(e)
        logger.error(f'ajuste {ajuste.id} FALHA: {msg}')
        registrar_auditoria(
            ajuste_id=ajuste.id,
            acao=ACAO_AUDIT_CURTA.get(ajuste.acao_decidida, ajuste.acao_decidida[:20]),
            status='FALHA', erro_msg=msg,
            tempo_ms=tempo_ms, executado_por=executado_por,
        )
        ajuste.status = 'FALHA'
        ajuste.fase_pipeline = 'INTERNO_FALHA'
        ajuste.erro_msg = msg
        db.session.commit()
        return {'sucesso': False, 'erro': msg, 'tempo_ms': tempo_ms}


def executar_positivo_puro(
    odoo, lot_svc: StockLotService,
    transfer_svc: StockInternalTransferService,
    ajuste: AjusteEstoqueInventario,
    product_id: int,
    location_principal: int,
    dry_run: bool,
    executado_por: str,
) -> Dict:
    """Cria lote alvo (se nao existe) + inventory adjustment positivo."""
    qty = float(ajuste.qtd_ajuste)
    if qty <= 0:
        return {'sucesso': False, 'erro': 'qty_ajuste<=0'}
    lote_destino = ajuste.lote_destino or 'P-15/05'
    cid = ajuste.company_id

    if dry_run:
        print(
            f'    [DRY] ajuste {ajuste.id} POSITIVO_PURO: criar/atualizar '
            f'lote {lote_destino!r} com +{qty} un em loc {location_principal}'
        )
        return {'sucesso': None, 'erro': None}

    inicio = time.time()
    try:
        # 1. Garantir lote
        lot_id_destino, criado_agora = lot_svc.criar_se_nao_existe(
            lote_destino, product_id, cid,
        )

        # 2. Verificar se ja existe quant para esse lote/location
        quant_existente = transfer_svc.buscar_quant(
            product_id, cid, location_principal, lot_id_destino,
        )

        if quant_existente:
            nova_qty = float(quant_existente['quantity']) + qty
            odoo.write(
                'stock.quant', [quant_existente['id']],
                {'inventory_quantity': nova_qty},
            )
            odoo.execute_kw(
                'stock.quant', 'action_apply_inventory',
                [[quant_existente['id']]],
            )
            quant_id = quant_existente['id']
            antes = quant_existente['quantity']
        else:
            quant_id = odoo.create('stock.quant', {
                'product_id': product_id,
                'company_id': cid,
                'location_id': location_principal,
                'lot_id': lot_id_destino,
                'inventory_quantity': qty,
            })
            odoo.execute_kw(
                'stock.quant', 'action_apply_inventory', [[quant_id]],
            )
            antes = 0
            nova_qty = qty

        tempo_ms = int((time.time() - inicio) * 1000)
        registrar_auditoria(
            ajuste_id=ajuste.id,
            acao=ACAO_AUDIT_CURTA.get(ajuste.acao_decidida, ajuste.acao_decidida[:20]),
            status='SUCESSO',
            payload={
                'product_id': product_id, 'lote_destino': lote_destino,
                'qty': qty, 'location_id': location_principal,
            },
            resposta={
                'quant_id': quant_id, 'qty_antes': antes,
                'qty_apos': nova_qty, 'lote_criado': criado_agora,
            },
            tempo_ms=tempo_ms, executado_por=executado_por,
        )
        ajuste.status = 'EXECUTADO'
        ajuste.fase_pipeline = 'POSITIVO_PURO_OK'
        db.session.commit()
        return {'sucesso': True, 'quant_id': quant_id, 'tempo_ms': tempo_ms}
    except Exception as e:
        tempo_ms = int((time.time() - inicio) * 1000)
        msg = str(e)
        logger.error(f'ajuste {ajuste.id} POSITIVO_PURO FALHA: {msg}')
        registrar_auditoria(
            ajuste_id=ajuste.id,
            acao=ACAO_AUDIT_CURTA.get(ajuste.acao_decidida, ajuste.acao_decidida[:20]),
            status='FALHA', erro_msg=msg,
            tempo_ms=tempo_ms, executado_por=executado_por,
        )
        ajuste.status = 'FALHA'
        ajuste.fase_pipeline = 'POSITIVO_PURO_FALHA'
        ajuste.erro_msg = msg
        db.session.commit()
        return {'sucesso': False, 'erro': msg, 'tempo_ms': tempo_ms}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--company-id', type=int, required=True, choices=[4, 1],
        help='OBRIGATORIO (4=CD, 1=FB)',
    )
    parser.add_argument('--dry-run', action='store_true', default=True)
    parser.add_argument('--confirmar', action='store_true')
    parser.add_argument('--limite', type=int, default=None,
                        help='executa N produtos primeiro (sub-piloto)')
    parser.add_argument('--cod-produto', default=None,
                        help='executa so 1 produto especifico')
    parser.add_argument('--usuario', default='09b_pre_etapa')
    parser.add_argument('--max-workers', type=int, default=1,
                        help='paralelizacao por produto (default=1 serial; '
                             'usar 5 para bulk acelerado ~5x)')
    args = parser.parse_args()

    dry_run = not args.confirmar
    cid = args.company_id
    location_principal = COMPANY_LOCATIONS[cid]
    acoes = ACOES_INTERNAS_POR_CID[cid]

    app = create_app()
    with app.app_context():
        odoo = get_odoo_connection()
        banner(
            f'EXECUTOR PRE-ETAPA (cid={cid}, modo={"DRY-RUN" if dry_run else "REAL"})'
        )
        print(f'  Location principal: {location_principal}')
        print(f'  Acoes: {acoes}')

        # 1. Buscar ajustes APROVADO
        q = (
            AjusteEstoqueInventario.query
            .filter_by(ciclo=CICLO, status='APROVADO', company_id=cid)
            .filter(AjusteEstoqueInventario.acao_decidida.in_(list(acoes.values())))
        )
        if args.cod_produto:
            q = q.filter_by(cod_produto=args.cod_produto)
        ajustes = q.all()
        if not ajustes:
            print('\nNenhum ajuste APROVADO encontrado. Aprove a Onda 5 via 04b primeiro.')
            sys.exit(0)

        # 2. Agrupar por cod_produto
        por_cod: Dict[str, List[AjusteEstoqueInventario]] = defaultdict(list)
        for a in ajustes:
            por_cod[a.cod_produto].append(a)

        cods_ordenados = sorted(por_cod.keys())
        if args.limite:
            cods_ordenados = cods_ordenados[:args.limite]
            print(f'  Limite ativo: {args.limite} primeiros produtos')
        print(f'\n{len(cods_ordenados)} produtos a processar / {len(ajustes)} ajustes totais\n')

        transfer_svc = StockInternalTransferService(odoo=odoo)
        lot_svc = StockLotService(odoo=odoo)

        stats = {
            'produtos_ok': 0, 'produtos_parcial': 0, 'produtos_falha': 0,
            'pos_ok': 0, 'pos_falha': 0,
            'neg_ok': 0, 'neg_falha': 0,
            'puro_ok': 0, 'puro_falha': 0,
        }

        # Capturar IDs (objetos ORM expirem entre threads)
        cod_to_ajuste_ids = {cod: [a.id for a in por_cod[cod]] for cod in cods_ordenados}
        db.session.expire_all()  # desligar objetos do contexto principal

        if args.max_workers > 1:
            print(f'  Paralelizacao ativa: max_workers={args.max_workers}\n')
            _executar_paralelo(
                app, cods_ordenados, cod_to_ajuste_ids, cid, acoes,
                location_principal, dry_run, args.usuario,
                args.max_workers, stats,
            )
            _imprimir_resumo(stats, dry_run)
            return

        # Modo serial (default ou max_workers=1)
        for i, cod in enumerate(cods_ordenados, 1):
            ajs_produto = por_cod[cod]
            pos = [a for a in ajs_produto if a.acao_decidida == acoes['POS']]
            neg = [a for a in ajs_produto if a.acao_decidida == acoes['NEG']]
            puro = [a for a in ajs_produto if a.acao_decidida == acoes['PURO']]
            print(f'[{i}/{len(cods_ordenados)}] cod={cod} | POS={len(pos)} NEG={len(neg)} PURO={len(puro)}')

            # Resolver product_id (apenas active=True por decisao usuario)
            resolve = resolver_product_id(odoo, cod)
            if not resolve:
                print(f'  ERRO: product nao encontrado (inativo OU sem cadastro)')
                stats['produtos_falha'] += 1
                # Persistir FALHA apenas em modo real — dry-run nao altera estado
                if not dry_run:
                    for a in ajs_produto:
                        a.status = 'FALHA'
                        a.erro_msg = (
                            'product_id nao resolvido — produto arquivado '
                            'ou nao cadastrado no Odoo'
                        )
                        db.session.commit()
                continue
            product_id, product_name = resolve

            # Mapear quants atuais
            quants_atuais = buscar_quants_produto_cid(odoo, product_id, cid)

            # Garantir lotes alvo + MIGRAÇÃO existem (se nao em dry-run)
            if not dry_run:
                lotes_a_criar = {a.lote_destino for a in pos + puro if a.lote_destino}
                if neg:
                    lotes_a_criar.add(LOTE_MIGRACAO)
                for lote_nome in lotes_a_criar:
                    lot_svc.criar_se_nao_existe(lote_nome, product_id, cid)

            sucessos_produto = 0
            falhas_produto = 0

            # POS primeiro (preencher alvos)
            for a in pos:
                r = executar_transferencia_interna(
                    transfer_svc, lot_svc, a, product_id,
                    quants_atuais, location_principal, dry_run, args.usuario,
                )
                if r['sucesso'] is True:
                    stats['pos_ok'] += 1
                    sucessos_produto += 1
                elif r['sucesso'] is False:
                    stats['pos_falha'] += 1
                    falhas_produto += 1
            # NEG (sobras → MIGRAÇÃO)
            for a in neg:
                r = executar_transferencia_interna(
                    transfer_svc, lot_svc, a, product_id,
                    quants_atuais, location_principal, dry_run, args.usuario,
                )
                if r['sucesso'] is True:
                    stats['neg_ok'] += 1
                    sucessos_produto += 1
                elif r['sucesso'] is False:
                    stats['neg_falha'] += 1
                    falhas_produto += 1
            # POSITIVO_PURO
            for a in puro:
                r = executar_positivo_puro(
                    odoo, lot_svc, transfer_svc, a, product_id,
                    location_principal, dry_run, args.usuario,
                )
                if r['sucesso'] is True:
                    stats['puro_ok'] += 1
                    sucessos_produto += 1
                elif r['sucesso'] is False:
                    stats['puro_falha'] += 1
                    falhas_produto += 1

            if falhas_produto == 0:
                stats['produtos_ok'] += 1
            elif sucessos_produto == 0:
                stats['produtos_falha'] += 1
            else:
                stats['produtos_parcial'] += 1

        # 3. Resumo
        banner('RESUMO', '=')
        print(f'  Produtos OK:          {stats["produtos_ok"]}')
        print(f'  Produtos parcial:     {stats["produtos_parcial"]}')
        print(f'  Produtos falha:       {stats["produtos_falha"]}')
        print(f'  POS  OK / FALHA:      {stats["pos_ok"]} / {stats["pos_falha"]}')
        print(f'  NEG  OK / FALHA:      {stats["neg_ok"]} / {stats["neg_falha"]}')
        print(f'  PURO OK / FALHA:      {stats["puro_ok"]} / {stats["puro_falha"]}')
        if dry_run:
            print('\n  Modo DRY-RUN — nada foi executado no Odoo.')


# ============================================================
# Paralelizacao por produto (max_workers > 1)
# ============================================================

def _imprimir_resumo(stats: Dict[str, int], dry_run: bool) -> None:
    banner('RESUMO', '=')
    print(f'  Produtos OK:          {stats["produtos_ok"]}')
    print(f'  Produtos parcial:     {stats["produtos_parcial"]}')
    print(f'  Produtos falha:       {stats["produtos_falha"]}')
    print(f'  POS  OK / FALHA:      {stats["pos_ok"]} / {stats["pos_falha"]}')
    print(f'  NEG  OK / FALHA:      {stats["neg_ok"]} / {stats["neg_falha"]}')
    print(f'  PURO OK / FALHA:      {stats["puro_ok"]} / {stats["puro_falha"]}')
    if dry_run:
        print('\n  Modo DRY-RUN — nada foi executado no Odoo.')


def _processar_produto_thread(
    app, cod: str, ajuste_ids: List[int], cid: int,
    acoes: Dict[str, str], location_principal: int,
    dry_run: bool, usuario: str,
) -> Dict[str, int]:
    """Executa pre-etapa de 1 produto em thread isolada.

    Cada thread tem seu Flask app_context proprio + conexao Odoo nova
    + session db scoped por thread (Flask-SQLAlchemy).

    Returns dict com contadores: produtos_*, pos_*, neg_*, puro_*.
    """
    local_stats = {
        'produtos_ok': 0, 'produtos_parcial': 0, 'produtos_falha': 0,
        'pos_ok': 0, 'pos_falha': 0,
        'neg_ok': 0, 'neg_falha': 0,
        'puro_ok': 0, 'puro_falha': 0,
    }
    with app.app_context():
        try:
            # Re-fetch ajustes na sessao desta thread
            ajustes = (
                AjusteEstoqueInventario.query
                .filter(AjusteEstoqueInventario.id.in_(ajuste_ids))
                .all()
            )
            if not ajustes:
                return local_stats

            odoo = get_odoo_connection()
            transfer_svc = StockInternalTransferService(odoo=odoo)
            lot_svc = StockLotService(odoo=odoo)

            pos = [a for a in ajustes if a.acao_decidida == acoes['POS']]
            neg = [a for a in ajustes if a.acao_decidida == acoes['NEG']]
            puro = [a for a in ajustes if a.acao_decidida == acoes['PURO']]

            resolve = resolver_product_id(odoo, cod)
            if not resolve:
                logger.warning(
                    f'cod={cod}: product nao encontrado (inativo/sem cadastro)'
                )
                local_stats['produtos_falha'] += 1
                if not dry_run:
                    for a in ajustes:
                        a.status = 'FALHA'
                        a.erro_msg = (
                            'product_id nao resolvido — produto arquivado '
                            'ou nao cadastrado no Odoo'
                        )
                    db.session.commit()
                return local_stats
            product_id, _ = resolve

            quants_atuais = buscar_quants_produto_cid(odoo, product_id, cid)

            if not dry_run:
                lotes_a_criar = {a.lote_destino for a in pos + puro if a.lote_destino}
                if neg:
                    lotes_a_criar.add(LOTE_MIGRACAO)
                for lote_nome in lotes_a_criar:
                    lot_svc.criar_se_nao_existe(lote_nome, product_id, cid)

            sucessos_produto = 0
            falhas_produto = 0
            for a in pos:
                r = executar_transferencia_interna(
                    transfer_svc, lot_svc, a, product_id,
                    quants_atuais, location_principal, dry_run, usuario,
                )
                if r['sucesso'] is True:
                    local_stats['pos_ok'] += 1
                    sucessos_produto += 1
                elif r['sucesso'] is False:
                    local_stats['pos_falha'] += 1
                    falhas_produto += 1
            for a in neg:
                r = executar_transferencia_interna(
                    transfer_svc, lot_svc, a, product_id,
                    quants_atuais, location_principal, dry_run, usuario,
                )
                if r['sucesso'] is True:
                    local_stats['neg_ok'] += 1
                    sucessos_produto += 1
                elif r['sucesso'] is False:
                    local_stats['neg_falha'] += 1
                    falhas_produto += 1
            for a in puro:
                r = executar_positivo_puro(
                    odoo, lot_svc, transfer_svc, a, product_id,
                    location_principal, dry_run, usuario,
                )
                if r['sucesso'] is True:
                    local_stats['puro_ok'] += 1
                    sucessos_produto += 1
                elif r['sucesso'] is False:
                    local_stats['puro_falha'] += 1
                    falhas_produto += 1

            if falhas_produto == 0:
                local_stats['produtos_ok'] += 1
            elif sucessos_produto == 0:
                local_stats['produtos_falha'] += 1
            else:
                local_stats['produtos_parcial'] += 1
        except Exception as e:
            logger.error(f'cod={cod}: excecao na thread: {e}', exc_info=True)
            try:
                db.session.rollback()
            except Exception:
                pass
            local_stats['produtos_falha'] += 1
        finally:
            try:
                db.session.remove()
            except Exception:
                pass
    return local_stats


def _executar_paralelo(
    app, cods_ordenados: List[str],
    cod_to_ajuste_ids: Dict[str, List[int]],
    cid: int, acoes: Dict[str, str], location_principal: int,
    dry_run: bool, usuario: str, max_workers: int,
    stats: Dict[str, int],
) -> None:
    """Submete uma thread por produto via ThreadPoolExecutor."""
    total = len(cods_ordenados)
    completos = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = {
            executor.submit(
                _processar_produto_thread,
                app, cod, cod_to_ajuste_ids[cod], cid, acoes,
                location_principal, dry_run, usuario,
            ): cod
            for cod in cods_ordenados
        }
        for future in as_completed(futures):
            cod = futures[future]
            completos += 1
            try:
                local = future.result()
                for k, v in local.items():
                    stats[k] += v
            except Exception as e:
                logger.error(f'future cod={cod} falhou: {e}', exc_info=True)
                stats['produtos_falha'] += 1
            if completos % 10 == 0 or completos == total:
                print(
                    f'  ... {completos}/{total} produtos processados '
                    f'(ok={stats["produtos_ok"]}, '
                    f'parcial={stats["produtos_parcial"]}, '
                    f'falha={stats["produtos_falha"]})'
                )


if __name__ == '__main__':
    main()
