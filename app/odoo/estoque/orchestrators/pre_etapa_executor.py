"""pre_etapa_executor.py — Orchestrator C3 macro da Skill 6.

Executa ajustes APROVADO da pre-etapa (Onda 5 CD / Onda 6 FB) compondo
Skills 1+2:

- POS  (AJUSTE_{CID}_TRANSF_INTERNA_POS): Skill 2 transferir_quantidade_para_lote_v2
       — delta_esperado propagado, lote_origem→lote_destino.
- NEG  (AJUSTE_{CID}_TRANSF_INTERNA_NEG): Skill 2 transferir_quantidade_para_lote_v2
       — delta_esperado propagado, lote_origem→MIGRACAO (consolidador).
- PURO (AJUSTE_{CID}_POSITIVO_PURO):       Skill 1 ajustar_quant(criar_se_faltar=True,
       delta_esperado=qty) — guard CICLAMATO ativo.

Capina `09b_executar_pre_etapa.py` (746 LOC):
- API v1 legada -> v2 com guard delta_esperado propagado
- `odoo.create('stock.quant')` DIRETO -> ajustar_quant via Skill 1
- print banner -> dict estruturado (regra v7 "Log JSON e fonte de verdade")

Pre-requisito: Skill 6 modo `aprovar-onda` rodado (ajustes status='APROVADO').

Auditoria preservada via OperacaoOdooAuditoria.registrar (mesmo pattern do 09b).
Paralelizacao preservada via ThreadPoolExecutor (max_workers configuravel).

Spec D007: docs/inventario-2026-05/00-decisoes/D007-pre-etapa-cd-fb-minimizar-nf.md
"""
import logging
import time
import uuid
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple

from app.odoo.estoque.scripts.pre_etapa import (
    ACOES_INTERNAS_POR_CID,
    COMPANY_LOCATIONS_PRE_ETAPA,
    ONDA_NUM_POR_CID,
)
from app.odoo.estoque.scripts.quant import StockQuantAdjustmentService
from app.odoo.estoque.scripts.transfer import StockInternalTransferService
from app.odoo.services.stock_lot_service import StockLotService
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)

# ============================================================
# Constantes
# ============================================================

LOTE_MIGRACAO = 'MIGRAÇÃO'
LOTE_DEFAULT_SEM_NOME = 'P-15/05'
TOL_DELTA = 0.001  # mesma de transfer.py / quant.py

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

CICLO_DEFAULT = 'INVENTARIO_2026_05'


# ============================================================
# Helpers de leitura Odoo
# ============================================================

def _resolver_product_id(odoo, cod_produto: str) -> Optional[Tuple[int, str]]:
    """Resolve product.id pelo default_code (apenas active=True).

    Decisao usuario 2026-05-18: produtos arquivados (active=False) NAO
    sao processados pela pre-etapa. Ficam como FALHA com mensagem para
    revisao humana.
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


def _buscar_quants_produto_cid(
    odoo, product_id: int, company_id: int,
) -> List[Dict[str, Any]]:
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


def _localizar_doador(
    quants: List[Dict[str, Any]],
    lote_nome_origem: str,
    qty_pedida: float,
) -> Optional[Dict[str, Any]]:
    """Encontra quant que pode doar qty_pedida do lote_nome_origem.

    Estrategia (igual 09b — pattern validado em PROD):
        1. Quant com lote_nome igual e qty >= pedida (match exato ou parcial)
        2. Prefere o de menor sobra (parcial menor)
        3. Fallback: qualquer quant do mesmo lote (mesmo se qty < pedida)
           — caller deve checar e bloquear se insuficiente.
    """
    candidatos = [
        q for q in quants
        if (q['lote_nome'] or '') == (lote_nome_origem or '')
        and q['quantity'] >= qty_pedida - TOL_DELTA
    ]
    if candidatos:
        return sorted(candidatos, key=lambda q: q['quantity'])[0]
    fallback = [
        q for q in quants
        if (q['lote_nome'] or '') == (lote_nome_origem or '')
    ]
    return fallback[0] if fallback else None


# ============================================================
# Auditoria (lazy import — evita circular em testes)
# ============================================================

def _registrar_auditoria(
    *,
    ajuste_id: int,
    acao: str,
    status: str,
    payload: Optional[Dict[str, Any]] = None,
    resposta: Optional[Dict[str, Any]] = None,
    erro_msg: Optional[str] = None,
    tempo_ms: Optional[int] = None,
    executado_por: str = 'sistema',
) -> None:
    """Registra operacao em operacao_odoo_auditoria (contexto pre_etapa).

    Lazy import de OperacaoOdooAuditoria para evitar circular em testes
    unitarios que mockam o orchestrator sem app_context.
    """
    try:
        from app.odoo.models import OperacaoOdooAuditoria  # lazy
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
            contexto_ref=CICLO_DEFAULT,
            executado_por=executado_por,
        )
    except Exception as e:
        logger.error(f'auditoria falhou: {e}', exc_info=True)


# ============================================================
# Execucao de 1 ajuste — POS/NEG via Skill 2 (transferir_quantidade_para_lote_v2)
# ============================================================

def _executar_transferencia_interna(
    transfer_svc: StockInternalTransferService,
    ajuste,
    product_id: int,
    quants_atuais: List[Dict[str, Any]],
    dry_run: bool,
    executado_por: str,
) -> Dict[str, Any]:
    """Executa 1 transferencia POS ou NEG via Skill 2 (v2 com delta_esperado).

    Refatorado de 09b._executar_transferencia_interna:
    - 09b usava `transferir_quantidade_para_lote` (v1, sem guard)
    - Agora usa `transferir_quantidade_para_lote_v2` que delega a
      `ajustar_quant`x2 com `delta_esperado=qty` propagado.

    A location e' a do quant doador (mesma origem/destino — transferencia
    intra-localizacao entre lotes). location_principal NAO e' usada aqui.

    Returns: dict {sucesso, erro, transferido_qty, tempo_ms}
    """
    from app import db  # lazy (evita circular em tests sem app)
    qty = float(ajuste.qtd_inventario if ajuste.qtd_inventario else ajuste.qtd_odoo)
    if qty <= 0:
        return {'sucesso': False, 'erro': 'qty<=0', 'transferido_qty': 0}
    lote_origem = ajuste.lote_origem or ''
    lote_destino = ajuste.lote_destino or LOTE_MIGRACAO
    cid = ajuste.company_id

    doador = _localizar_doador(quants_atuais, lote_origem, qty)
    if not doador:
        return {
            'sucesso': False,
            'erro': f'quant origem nao encontrado para lote={lote_origem!r}',
            'transferido_qty': 0,
        }
    if doador['quantity'] < qty - TOL_DELTA:
        return {
            'sucesso': False,
            'erro': (
                f'quant origem {doador["quant_id"]} tem '
                f'{doador["quantity"]} un, ajuste pede {qty}'
            ),
            'transferido_qty': 0,
        }

    inicio = time.time()
    try:
        res = transfer_svc.transferir_quantidade_para_lote_v2(
            product_id=product_id,
            company_id=cid,
            location_id=doador['location_id'],
            qty=qty,
            lot_id_origem=doador['lot_id'],
            nome_lote_destino=lote_destino,
            tolerancia_delta=TOL_DELTA,
            dry_run=dry_run,
        )
        tempo_ms = int((time.time() - inicio) * 1000)
        # Skill 2 v2 retorna status em 'reducao'/'aumento' ou status agregado.
        # Verificar sucesso via reducao + aumento OK (ambos EXECUTADO/DRY_RUN_OK).
        sucesso = _avaliar_sucesso_v2(res, dry_run)
        if dry_run:
            return {
                'sucesso': None,  # dry-run nao confirma sucesso
                'plano': res,
                'tempo_ms': tempo_ms,
            }
        if not sucesso:
            erro = (
                res.get('erro')
                or res.get('reducao_origem', {}).get('erro')
                or res.get('aumento_destino', {}).get('erro')
                or 'transfer v2 falhou'
            )
            _registrar_auditoria(
                ajuste_id=ajuste.id,
                acao=ACAO_AUDIT_CURTA.get(
                    ajuste.acao_decidida, ajuste.acao_decidida[:20],
                ),
                status='FALHA', erro_msg=str(erro),
                tempo_ms=tempo_ms, executado_por=executado_por,
            )
            ajuste.status = 'FALHA'
            ajuste.fase_pipeline = 'INTERNO_FALHA'
            ajuste.erro_msg = str(erro)
            db.session.commit()
            return {
                'sucesso': False, 'erro': str(erro), 'tempo_ms': tempo_ms,
                'transferido_qty': 0, 'detalhes_v2': res,
            }
        _registrar_auditoria(
            ajuste_id=ajuste.id,
            acao=ACAO_AUDIT_CURTA.get(
                ajuste.acao_decidida, ajuste.acao_decidida[:20],
            ),
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
        # Atualiza quants_atuais (subtrai qty do doador) — caso reaproveite no batch
        doador['quantity'] -= qty
        return {
            'sucesso': True, 'transferido_qty': qty, 'tempo_ms': tempo_ms,
            'detalhes_v2': res,
        }
    except Exception as e:
        tempo_ms = int((time.time() - inicio) * 1000)
        msg = str(e)
        logger.error(f'ajuste {ajuste.id} FALHA: {msg}')
        if not dry_run:
            _registrar_auditoria(
                ajuste_id=ajuste.id,
                acao=ACAO_AUDIT_CURTA.get(
                    ajuste.acao_decidida, ajuste.acao_decidida[:20],
                ),
                status='FALHA', erro_msg=msg,
                tempo_ms=tempo_ms, executado_por=executado_por,
            )
            try:
                ajuste.status = 'FALHA'
                ajuste.fase_pipeline = 'INTERNO_FALHA'
                ajuste.erro_msg = msg
                db.session.commit()
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass
        return {
            'sucesso': False, 'erro': msg, 'tempo_ms': tempo_ms,
            'transferido_qty': 0,
        }


def _avaliar_sucesso_v2(res: Dict[str, Any], dry_run: bool) -> bool:
    """Decide se composicao v2 (transferir_entre_lotes_v2) foi sucesso.

    Skill 2 v2 retorna `status` flat: 'EXECUTADO' | 'DRY_RUN_OK' |
    'FALHA_REDUCAO' | 'FALHA_AUMENTO' (linha 542 de transfer.py).
    Sucesso = status terminal positivo.
    """
    status = res.get('status', '')
    if dry_run:
        return status in {'DRY_RUN_OK', 'EXECUTADO', 'EXECUTADO_AUTO_CORRIGIDO'}
    return status in {'EXECUTADO', 'EXECUTADO_AUTO_CORRIGIDO'}


# ============================================================
# Execucao de 1 ajuste — PURO via Skill 1 (ajustar_quant com guard delta_esperado)
# ============================================================

def _executar_positivo_puro(
    quant_svc: StockQuantAdjustmentService,
    transfer_svc: StockInternalTransferService,
    ajuste,
    product_id: int,
    location_principal: int,
    dry_run: bool,
    executado_por: str,
) -> Dict[str, Any]:
    """Cria/aumenta quant alvo via Skill 1 ajustar_quant (com guard delta_esperado).

    Refatorado de 09b._executar_positivo_puro:
    - 09b usava `odoo.create('stock.quant', ...)` + `action_apply_inventory`
      DIRETO (sem guard delta_esperado — risco CICLAMATO).
    - Agora usa `quant_svc.ajustar_quant(delta=+qty, criar_se_faltar=True,
      delta_esperado=qty)` que ativa o guard CICLAMATO.

    Returns: dict {sucesso, erro, quant_id, tempo_ms}
    """
    from app import db  # lazy
    qty = float(ajuste.qtd_ajuste)
    if qty <= 0:
        return {'sucesso': False, 'erro': 'qty_ajuste<=0'}
    lote_destino_nome = ajuste.lote_destino or LOTE_DEFAULT_SEM_NOME
    cid = ajuste.company_id

    inicio = time.time()
    try:
        # 1. Resolver lot_id_destino (cria se nao existe via Skill 2 helper).
        #    Para lote_destino == 'P-15/05'/None, resolve para (None, ...)
        #    e ajustar_quant aceita lot_id=None (quant sem lote).
        lot_id_destino, nome_canonico, lote_criado = (
            transfer_svc.resolver_lote_destino(
                nome_lote=lote_destino_nome,
                product_id=product_id,
                company_id=cid,
                location_id=location_principal,
                criar_se_faltar=not dry_run,
            )
        )

        # 2. Ajuste via Skill 1 — guard delta_esperado=qty ativo.
        res = quant_svc.ajustar_quant(
            product_id=product_id,
            company_id=cid,
            location_id=location_principal,
            lot_id=lot_id_destino,
            delta=qty,
            criar_se_faltar=True,
            delta_esperado=qty,
            tolerancia_delta=TOL_DELTA,
            dry_run=dry_run,
        )

        tempo_ms = int((time.time() - inicio) * 1000)
        status_skill1 = res.get('status', '')

        if dry_run:
            return {
                'sucesso': None,
                'plano': res,
                'lote_destino_nome': nome_canonico,
                'lote_destino_criado_agora': lote_criado,
                'tempo_ms': tempo_ms,
            }

        oks_real = {'EXECUTADO', 'EXECUTADO_AUTO_CORRIGIDO', 'NOOP'}
        if status_skill1 not in oks_real:
            erro = res.get('erro') or f'ajustar_quant status={status_skill1}'
            _registrar_auditoria(
                ajuste_id=ajuste.id,
                acao=ACAO_AUDIT_CURTA.get(
                    ajuste.acao_decidida, ajuste.acao_decidida[:20],
                ),
                status='FALHA', erro_msg=str(erro),
                tempo_ms=tempo_ms, executado_por=executado_por,
            )
            ajuste.status = 'FALHA'
            ajuste.fase_pipeline = 'POSITIVO_PURO_FALHA'
            ajuste.erro_msg = str(erro)
            db.session.commit()
            return {
                'sucesso': False, 'erro': str(erro),
                'tempo_ms': tempo_ms, 'detalhes_skill1': res,
            }

        _registrar_auditoria(
            ajuste_id=ajuste.id,
            acao=ACAO_AUDIT_CURTA.get(
                ajuste.acao_decidida, ajuste.acao_decidida[:20],
            ),
            status='SUCESSO',
            payload={
                'product_id': product_id, 'lote_destino': lote_destino_nome,
                'qty': qty, 'location_id': location_principal,
            },
            resposta={
                'quant_id': res.get('quant_id'),
                'qty_antes': res.get('qty_antes'),
                'qty_apos': res.get('qty_apos'),
                'lote_criado': lote_criado,
                'status_skill1': status_skill1,
            },
            tempo_ms=tempo_ms, executado_por=executado_por,
        )
        ajuste.status = 'EXECUTADO'
        ajuste.fase_pipeline = 'POSITIVO_PURO_OK'
        db.session.commit()
        return {
            'sucesso': True, 'quant_id': res.get('quant_id'),
            'tempo_ms': tempo_ms, 'detalhes_skill1': res,
        }
    except Exception as e:
        tempo_ms = int((time.time() - inicio) * 1000)
        msg = str(e)
        logger.error(f'ajuste {ajuste.id} POSITIVO_PURO FALHA: {msg}')
        if not dry_run:
            _registrar_auditoria(
                ajuste_id=ajuste.id,
                acao=ACAO_AUDIT_CURTA.get(
                    ajuste.acao_decidida, ajuste.acao_decidida[:20],
                ),
                status='FALHA', erro_msg=msg,
                tempo_ms=tempo_ms, executado_por=executado_por,
            )
            try:
                ajuste.status = 'FALHA'
                ajuste.fase_pipeline = 'POSITIVO_PURO_FALHA'
                ajuste.erro_msg = msg
                db.session.commit()
            except Exception:
                try:
                    db.session.rollback()
                except Exception:
                    pass
        return {'sucesso': False, 'erro': msg, 'tempo_ms': tempo_ms}


# ============================================================
# Processamento de 1 produto (compor POS + NEG + PURO)
# ============================================================

def _processar_produto(
    odoo,
    quant_svc: StockQuantAdjustmentService,
    transfer_svc: StockInternalTransferService,
    cod: str,
    ajustes_produto: List,
    cid: int,
    acoes: Dict[str, str],
    location_principal: int,
    dry_run: bool,
    usuario: str,
    contadores: Dict[str, int],
) -> Dict[str, Any]:
    """Processa todos os ajustes APROVADOS de 1 produto.

    Atualiza contadores in-place. Retorna dict com detalhes do produto.
    lot_svc nao e necessario aqui (transfer_svc/quant_svc ja recebem
    via construtor).
    """
    from app import db  # lazy
    pos = [a for a in ajustes_produto if a.acao_decidida == acoes['POS']]
    neg = [a for a in ajustes_produto if a.acao_decidida == acoes['NEG']]
    puro = [a for a in ajustes_produto if a.acao_decidida == acoes['PURO']]

    produto_out: Dict[str, Any] = {
        'cod': cod,
        'pos_total': len(pos), 'neg_total': len(neg), 'puro_total': len(puro),
        'pos_results': [], 'neg_results': [], 'puro_results': [],
        'sucessos': 0, 'falhas': 0,
        'product_id': None, 'product_name': None,
    }

    resolve = _resolver_product_id(odoo, cod)
    if not resolve:
        msg = (
            'product_id nao resolvido — produto arquivado '
            'ou nao cadastrado no Odoo'
        )
        produto_out['erro'] = msg
        contadores['produtos_falha'] += 1
        if not dry_run:
            for a in ajustes_produto:
                a.status = 'FALHA'
                a.erro_msg = msg
            db.session.commit()
        return produto_out
    product_id, product_name = resolve
    produto_out['product_id'] = product_id
    produto_out['product_name'] = product_name

    quants_atuais = _buscar_quants_produto_cid(odoo, product_id, cid)

    # POS primeiro (preencher alvos)
    for a in pos:
        r = _executar_transferencia_interna(
            transfer_svc, a, product_id, quants_atuais,
            dry_run, usuario,
        )
        produto_out['pos_results'].append({'ajuste_id': a.id, 'resultado': r})
        if r['sucesso'] is True:
            contadores['pos_ok'] += 1
            produto_out['sucessos'] += 1
        elif r['sucesso'] is False:
            contadores['pos_falha'] += 1
            produto_out['falhas'] += 1
    # NEG (sobras -> MIGRACAO)
    for a in neg:
        r = _executar_transferencia_interna(
            transfer_svc, a, product_id, quants_atuais,
            dry_run, usuario,
        )
        produto_out['neg_results'].append({'ajuste_id': a.id, 'resultado': r})
        if r['sucesso'] is True:
            contadores['neg_ok'] += 1
            produto_out['sucessos'] += 1
        elif r['sucesso'] is False:
            contadores['neg_falha'] += 1
            produto_out['falhas'] += 1
    # POSITIVO_PURO
    for a in puro:
        r = _executar_positivo_puro(
            quant_svc, transfer_svc, a, product_id,
            location_principal, dry_run, usuario,
        )
        produto_out['puro_results'].append({'ajuste_id': a.id, 'resultado': r})
        if r['sucesso'] is True:
            contadores['puro_ok'] += 1
            produto_out['sucessos'] += 1
        elif r['sucesso'] is False:
            contadores['puro_falha'] += 1
            produto_out['falhas'] += 1

    if produto_out['falhas'] == 0 and produto_out['sucessos'] > 0:
        contadores['produtos_ok'] += 1
    elif produto_out['sucessos'] == 0 and produto_out['falhas'] > 0:
        contadores['produtos_falha'] += 1
    elif produto_out['falhas'] > 0 and produto_out['sucessos'] > 0:
        contadores['produtos_parcial'] += 1
    else:
        # dry-run ou tudo NOOP — considera produto ok
        contadores['produtos_ok'] += 1
    return produto_out


# ============================================================
# Paralelizacao (ThreadPoolExecutor)
# ============================================================

def _processar_produto_thread(
    app, cod: str, ajuste_ids: List[int], cid: int,
    acoes: Dict[str, str], location_principal: int,
    dry_run: bool, usuario: str,
) -> Tuple[Dict[str, int], Dict[str, Any]]:
    """Wrapper de _processar_produto para thread isolada.

    Cada thread cria proprio app_context + conexao Odoo + session db scoped.
    Returns: (contadores_locais, produto_out).
    """
    from app import db  # lazy
    from app.odoo.models import AjusteEstoqueInventario  # lazy
    contadores_locais = {
        'produtos_ok': 0, 'produtos_parcial': 0, 'produtos_falha': 0,
        'pos_ok': 0, 'pos_falha': 0,
        'neg_ok': 0, 'neg_falha': 0,
        'puro_ok': 0, 'puro_falha': 0,
    }
    produto_out: Dict[str, Any] = {'cod': cod}
    with app.app_context():
        try:
            ajustes = (
                AjusteEstoqueInventario.query
                .filter(AjusteEstoqueInventario.id.in_(ajuste_ids))
                .all()
            )
            if not ajustes:
                return contadores_locais, produto_out

            odoo = get_odoo_connection()
            lot_svc = StockLotService(odoo=odoo)
            quant_svc = StockQuantAdjustmentService(odoo=odoo, lot_svc=lot_svc)
            transfer_svc = StockInternalTransferService(odoo=odoo, lot_svc=lot_svc)

            produto_out = _processar_produto(
                odoo, quant_svc, transfer_svc,
                cod, ajustes, cid, acoes, location_principal,
                dry_run, usuario, contadores_locais,
            )
        except Exception as e:
            logger.error(f'cod={cod}: excecao na thread: {e}', exc_info=True)
            produto_out['erro_thread'] = str(e)
            try:
                db.session.rollback()
            except Exception:
                pass
            contadores_locais['produtos_falha'] += 1
        finally:
            try:
                db.session.remove()
            except Exception:
                pass
    return contadores_locais, produto_out


def _executar_paralelo(
    app, cods_ordenados: List[str],
    cod_to_ajuste_ids: Dict[str, List[int]],
    cid: int, acoes: Dict[str, str], location_principal: int,
    dry_run: bool, usuario: str, max_workers: int,
) -> Tuple[Dict[str, int], List[Dict[str, Any]]]:
    """Submete uma thread por produto via ThreadPoolExecutor.

    Returns: (contadores_agregados, lista de produto_outs).
    """
    contadores = {
        'produtos_ok': 0, 'produtos_parcial': 0, 'produtos_falha': 0,
        'pos_ok': 0, 'pos_falha': 0,
        'neg_ok': 0, 'neg_falha': 0,
        'puro_ok': 0, 'puro_falha': 0,
    }
    produtos: List[Dict[str, Any]] = []
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
            try:
                local, prod_out = future.result()
                for k, v in local.items():
                    contadores[k] += v
                produtos.append(prod_out)
            except Exception as e:
                logger.error(f'future cod={cod} falhou: {e}', exc_info=True)
                contadores['produtos_falha'] += 1
                produtos.append({'cod': cod, 'erro_future': str(e)})
    return contadores, produtos


# ============================================================
# Entry-point publico
# ============================================================

def executar_onda_pre_etapa(
    *,
    ciclo: str = CICLO_DEFAULT,
    company_id: int,
    onda_num: Optional[int] = None,
    usuario: str = 'pre_etapa_executor',
    max_workers: int = 1,
    limite: Optional[int] = None,
    cod_produto: Optional[str] = None,
    dry_run: bool = True,
) -> Dict[str, Any]:
    """Executa todos os ajustes APROVADO da Onda da company.

    Compoe Skills 1+2:
    - POS/NEG: Skill 2 transferir_quantidade_para_lote_v2 (delta_esperado propagado)
    - PURO: Skill 1 ajustar_quant (criar_se_faltar=True, delta_esperado=qty)

    Args:
        ciclo: identificador (default INVENTARIO_2026_05).
        company_id: 4 (CD Onda 5) ou 1 (FB Onda 6).
        onda_num: default inferido de company_id (4->5, 1->6).
        usuario: para auditoria.
        max_workers: paralelizacao por produto (default 1 serial; 5 para bulk ~5x).
        limite: executa N primeiros produtos (sub-piloto).
        cod_produto: filtra para 1 produto especifico.
        dry_run: True (default) simula; False executa real.

    Returns:
        dict {
            status,                # DRY_RUN_OK_EXECUTADO | EXECUTADO_ONDA | FALHA_*
            ciclo, company_id, onda_num,
            ajustes_total, produtos_total,
            contadores: {produtos_ok, produtos_parcial, produtos_falha,
                         pos_ok, pos_falha, neg_ok, neg_falha,
                         puro_ok, puro_falha},
            produtos: [{cod, product_id, sucessos, falhas, pos/neg/puro_results}],
            tempo_ms,
        }
    """
    from app import db  # lazy
    from app.odoo.models import AjusteEstoqueInventario  # lazy
    t0 = time.time()
    out: Dict[str, Any] = {
        'modo': 'executar-onda',
        'ciclo': ciclo,
        'company_id': company_id,
        'onda_num': onda_num or ONDA_NUM_POR_CID.get(company_id),
        'dry_run': dry_run,
        'max_workers': max_workers,
        'limite': limite,
        'cod_produto_filter': cod_produto,
    }

    if company_id not in ACOES_INTERNAS_POR_CID:
        out['status'] = 'FALHA_USO'
        out['erro'] = f'company_id={company_id} nao suportado (use 4 ou 1)'
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    acoes = ACOES_INTERNAS_POR_CID[company_id]
    location_principal = COMPANY_LOCATIONS_PRE_ETAPA[company_id]

    # 1. Buscar ajustes APROVADO
    q = (
        AjusteEstoqueInventario.query
        .filter_by(ciclo=ciclo, status='APROVADO', company_id=company_id)
        .filter(AjusteEstoqueInventario.acao_decidida.in_(list(acoes.values())))
    )
    if cod_produto:
        q = q.filter_by(cod_produto=cod_produto)
    ajustes = q.all()
    if not ajustes:
        out['status'] = 'FALHA_NENHUM_APROVADO'
        out['erro'] = (
            f'Nenhum ajuste APROVADO encontrado para ciclo={ciclo!r} '
            f'company_id={company_id} acoes={list(acoes.values())}. '
            f'Rode --modo aprovar-onda da Skill 6 primeiro.'
        )
        out['ajustes_total'] = 0
        out['produtos_total'] = 0
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    # 2. Agrupar por cod_produto
    por_cod: Dict[str, List] = defaultdict(list)
    for a in ajustes:
        por_cod[a.cod_produto].append(a)
    cods_ordenados = sorted(por_cod.keys())
    if limite:
        cods_ordenados = cods_ordenados[:limite]

    out['ajustes_total'] = len(ajustes)
    out['produtos_total'] = len(cods_ordenados)

    # 3. Paralelizar OU serial (default)
    if max_workers > 1:
        from flask import current_app
        app = current_app._get_current_object()  # type: ignore
        cod_to_ajuste_ids = {cod: [a.id for a in por_cod[cod]] for cod in cods_ordenados}
        db.session.expire_all()  # objetos ORM fora do contexto principal
        contadores, produtos = _executar_paralelo(
            app, cods_ordenados, cod_to_ajuste_ids, company_id,
            acoes, location_principal, dry_run, usuario, max_workers,
        )
    else:
        # Serial — usa conexao + svcs unicos
        odoo = get_odoo_connection()
        lot_svc = StockLotService(odoo=odoo)
        quant_svc = StockQuantAdjustmentService(odoo=odoo, lot_svc=lot_svc)
        transfer_svc = StockInternalTransferService(odoo=odoo, lot_svc=lot_svc)
        contadores = {
            'produtos_ok': 0, 'produtos_parcial': 0, 'produtos_falha': 0,
            'pos_ok': 0, 'pos_falha': 0,
            'neg_ok': 0, 'neg_falha': 0,
            'puro_ok': 0, 'puro_falha': 0,
        }
        produtos = []
        for cod in cods_ordenados:
            prod_out = _processar_produto(
                odoo, quant_svc, transfer_svc,
                cod, por_cod[cod], company_id, acoes,
                location_principal, dry_run, usuario, contadores,
            )
            produtos.append(prod_out)

    out['contadores'] = contadores
    out['produtos'] = produtos
    out['tempo_ms'] = int((time.time() - t0) * 1000)
    out['status'] = (
        'DRY_RUN_OK_EXECUTADO' if dry_run else 'EXECUTADO_ONDA'
    )
    return out
