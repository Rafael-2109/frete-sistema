"""escrituracao.py — Atomo C3 macro Skill 7 `escriturando-odoo` (v17.5).

Encapsula a logica de ESCRITURAR ENTRADA de NF SEFAZ-autorizada no destino
via `RecebimentoLf` + agregacao de lotes + invocacao do service externo
`RecebimentoLfOdooService` (37 etapas LF->FB).

Substitui logica inline anteriormente em
`app/odoo/estoque/orchestrators/faturamento_pipeline.executar_etapa_e` (v17 —
reverted em v17.5 por violar a constituicao §6: `faturando-odoo` = SO SAIDA,
`escriturando-odoo` = SO ENTRADA; quem une saida + entrada e' o FLUXO L3).

REGRA INVIOLAVEL 94 (v17.5 ARQ-2):
  `escriturando-odoo` (Skill 7) = SO ENTRADA. Encapsula tudo que era inline
  na ETAPA E do orchestrator pre-v17.5.

V1 STRICT (2026-05-26 v17.5):
  - SO suporta LF->FB (PERDA_LF_FB, DEV_LF_FB, TRANSFERIR_CD_FB) via
    RecebimentoLfOdooService externo (4562 LOC validados em PROD — NAO MEXER).
  - Outras direcoes (CD->LF, DEV_CD_LF) raise NotImplementedError ate' o
    service externo suportar (futuro Skill 7 v2).

Gotchas codificados (invariantes intra-atomo):
  G-RECLF-2  : aceita `transfer_status='erro'` como sucesso parcial OK
               (FB OK suficiente; FASE 6+7 FB->CD podem falhar sem derrubar FB)
  G-RECLF-3  : idempotencia via `RecebimentoLf.odoo_lf_invoice_id` (UK
               aplicada PROD em v17 — migration `add_uq_recebimento_lf_invoice_id`)
  HIGH-3 v17 : `status='processando'` RETOMA (anti-RecLf orfao por crash
               mid-process — service externo suporta resume via etapa_atual>0)
  HIGH-4 v17 : svc externo instanciado FRESH por invocacao (anti-vazamento
               estado interno via self._recebimento_id e caches Redis)
  HIGH-5 v17 : `produto_tracking` real via fetch batch product.tracking
               (anti-D-OPS-5 quebra `_step_10_preencher_lotes` p/ tracking='none')
  D17        : ACAO_PARA_CFOP_ENTRADA 5xxx->1xxx (RecebimentoLfLote.cfop —
               Odoo FB so' tem fiscal_position para CFOPs de entrada 1xxx)
  D9         : re-fetch ajustes via `safe_session_get` apos commits internos
               do svc externo (anti-DetachedInstanceError)

Reference:
  app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md §7.4 G-RECLF-1..11
  app/odoo/estoque/CLAUDE.md §6 (catalogo de atomos)
"""
from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.odoo.constants.operacoes_fiscais import ACAO_PARA_CFOP_ENTRADA
from app.odoo.estoque.scripts._commit_helpers import (
    commit_resilient,
    safe_session_get,
)
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


# Defaults V1 STRICT (LF -> FB)
CNPJ_LF_DEFAULT = '18.467.441/0001-63'
COMPANY_ID_FB_DEFAULT = 1
TOTAL_ETAPAS_RECLF = 37


def _registrar_auditoria(
    *,
    ajuste_id: int,
    ciclo: str,
    fase: str,
    acao: str,
    status: str,
    payload: Optional[Dict[str, Any]] = None,
    resposta: Optional[Dict[str, Any]] = None,
    erro_msg: Optional[str] = None,
    odoo_id: Optional[int] = None,
    modelo_odoo: Optional[str] = None,
    tempo_ms: Optional[int] = None,
    executado_por: str = 'sistema',
) -> None:
    """Registra operacao em operacao_odoo_auditoria (contexto escrituracao).

    Lazy import de OperacaoOdooAuditoria. Pattern espelhado de
    `faturamento_pipeline._registrar_auditoria` (contexto_origem='escrituracao_lf'
    distingue da Skill 8). TODO v18: consolidar helper compartilhado em
    `app/odoo/estoque/scripts/_auditoria.py` se um 3o callsite surgir.
    """
    try:
        from app.odoo.models import OperacaoOdooAuditoria  # lazy
        external_id = (
            f'INV-{ciclo}-A{ajuste_id:06d}-{fase}-{uuid.uuid4().hex[:8]}'
        )
        OperacaoOdooAuditoria.registrar(
            external_id=external_id,
            tabela_origem='ajuste_estoque_inventario',
            registro_id=ajuste_id,
            acao=acao,
            modelo_odoo=modelo_odoo or 'recebimento_lf',
            etapa=fase,
            etapa_descricao=f'{fase} {acao}',
            status=status,
            payload_json=payload,
            resposta_json=resposta,
            erro_msg=erro_msg,
            tempo_execucao_ms=tempo_ms,
            pipeline_etapa=fase,
            contexto_origem='escrituracao_lf',
            contexto_ref=ciclo,
            executado_por=executado_por,
            odoo_id=odoo_id,
        )
    except Exception as e:
        logger.error(f'auditoria escrituracao fase={fase} falhou: {e}', exc_info=True)


class EscrituracaoLfService:
    """Skill 7 escriturando-odoo: atomo C3 macro para escriturar ENTRADA
    de NF SEFAZ-autorizada no destino.

    V1 STRICT (2026-05-26 v17.5): SO LF->FB via RecebimentoLfOdooService externo.

    Uso pelo orchestrator Skill 8 (ETAPA E pos-v17.5):

        from app.odoo.estoque.scripts.escrituracao import EscrituracaoLfService
        svc = EscrituracaoLfService(odoo=self.odoo)
        for invoice_id, ajustes in ajustes_por_invoice.items():
            resultado = svc.criar_recebimento_orchestrado(
                invoice_id=invoice_id,
                ajustes=ajustes,
                ciclo=ciclo,
                usuario=usuario,
                dry_run=False,
            )
            # status: CRIADO | RETOMADO | IDEMPOTENT_PROCESSADO |
            #         PARCIAL | FALHA | DRY_RUN_OK | SKIP_AJUSTES_VAZIOS
    """

    def __init__(self, odoo=None):
        self.odoo = odoo or get_odoo_connection()

    def criar_recebimento_orchestrado(
        self,
        *,
        invoice_id: int,
        ajustes: List[Any],
        ciclo: str,
        usuario: str,
        dry_run: bool = True,
        cnpj_emitente: str = CNPJ_LF_DEFAULT,
        company_id_recebedor: int = COMPANY_ID_FB_DEFAULT,
    ) -> Dict[str, Any]:
        """Atomo Skill 7: orquestra RecebimentoLf + agg lotes + svc externo.

        Encapsula:
          - Validacao V1 STRICT pre-cond (LF->FB only — V2 expandira)
          - Dry-run: planejamento sem escrever
          - Real-run:
            * Idempotencia G-RECLF-3 (RecLf processado -> IDEMPOTENT_PROCESSADO)
            * HIGH-3: status='processando' RETOMA (no-op se nao existe)
            * D9: re-fetch ajustes via safe_session_get (anti-Detached)
            * Fetch invoice data Odoo (chave + numero NF)
            * Resolve product_ids batch
            * HIGH-5: fetch tracking real batch (D-OPS-5 fix)
            * Cria RecebimentoLf + Lotes (se nao retomando):
              - agg (pid, lote_dest, cfop) -> qty
              - D17: ACAO_PARA_CFOP_ENTRADA 5xxx->1xxx
              - commit_resilient antes do svc externo
            * HIGH-4: svc instanciado fresh
            * Invoca svc_externo.processar_recebimento(rec.id) SINCRONO (30-60min)
            * G-RECLF-2: aceita transfer_status='erro' como PARCIAL OK
            * Re-fetch ajustes pos-svc + auditoria + commit

        Args:
            invoice_id: id account.move SEFAZ-OK (state='posted',
                situacao_nf='autorizado'). Caller (Skill 8 ETAPA E) ja' filtrou.
            ajustes: lista AjusteEstoqueInventario pre-carregada. Caller filtra
                por ACOES_ENTRADA_FB + chave_nfe + invoice_id_odoo == invoice_id.
                Atomo NAO re-filtra.
            ciclo: identificador do ciclo de inventario (auditoria + external_id).
            usuario: identificador para executado_por do svc externo + auditoria.
            dry_run: True (default) NAO escreve; reporta planejamento.
            cnpj_emitente: CNPJ emitente da NF. V1: default LF '18.467...'.
                Outros valores raise NotImplementedError.
            company_id_recebedor: company_id que recebe. V1: default FB=1.
                Outros valores raise NotImplementedError.

        Returns:
            dict com:
              status: str — 'CRIADO' | 'RETOMADO' | 'IDEMPOTENT_PROCESSADO' |
                            'PARCIAL' | 'FALHA' | 'DRY_RUN_OK' |
                            'SKIP_AJUSTES_VAZIOS'
              rec_id: int | None — id do RecebimentoLf (criado, retomado ou
                                   existente IDEMPOTENT)
              odoo_invoice_id_fb: int | None — invoice_id FB criado pelo
                                              svc externo (None em DRY_RUN/IDEMPOTENT)
              transfer_status: str | None — 'concluido' | 'erro' | None
                              (None em DRY_RUN/IDEMPOTENT)
              tempo_ms: int
              erro: str | None — preenchido se status='FALHA'
              [demais campos quando dry_run]: invoice_id, ajustes_count, observacao

        Raises:
            NotImplementedError: cnpj_emitente ou company_id_recebedor fora V1.
        """
        t0 = time.time()

        # Pre-cond V1 STRICT
        if cnpj_emitente != CNPJ_LF_DEFAULT or company_id_recebedor != COMPANY_ID_FB_DEFAULT:
            raise NotImplementedError(
                f'Skill 7 V1 STRICT: so suporta LF->FB '
                f'(cnpj={CNPJ_LF_DEFAULT!r}, '
                f'company_recebedor={COMPANY_ID_FB_DEFAULT}). '
                f'Recebeu cnpj={cnpj_emitente!r}, '
                f'company_recebedor={company_id_recebedor}. '
                f'Expansao quando RecebimentoLfOdooService suportar '
                f'outras direcoes (futuro v18+).'
            )

        if not ajustes:
            return {
                'status': 'SKIP_AJUSTES_VAZIOS',
                'rec_id': None,
                'odoo_invoice_id_fb': None,
                'transfer_status': None,
                'tempo_ms': int((time.time() - t0) * 1000),
                'erro': None,
            }

        # Dry-run
        if dry_run:
            cods_distintos = sorted({a.cod_produto for a in ajustes})
            return {
                'status': 'DRY_RUN_OK',
                'rec_id': None,
                'odoo_invoice_id_fb': None,
                'transfer_status': None,
                'invoice_id': invoice_id,
                'ajustes_count': len(ajustes),
                'cods_distintos': cods_distintos,
                'observacao': (
                    f'dry-run: 1 RecebimentoLf seria criado para invoice '
                    f'{invoice_id} com {len(ajustes)} ajustes '
                    f'({len(cods_distintos)} cods). Tempo estimado real: '
                    f'30-60min via service externo.'
                ),
                'tempo_ms': int((time.time() - t0) * 1000),
                'erro': None,
            }

        # ============================================================
        # REAL-RUN
        # ============================================================
        from app import db  # lazy
        from app.odoo.models import AjusteEstoqueInventario  # lazy
        from app.recebimento.models import (  # lazy
            RecebimentoLf,
            RecebimentoLfLote,
        )
        from app.recebimento.services.recebimento_lf_odoo_service import (  # lazy
            RecebimentoLfOdooService,
        )

        # G-RECLF-3 idempotencia: existe RecLf processado?
        existente = RecebimentoLf.query.filter_by(
            odoo_lf_invoice_id=invoice_id,
        ).order_by(RecebimentoLf.id.desc()).first()

        if existente and existente.status == 'processado':
            logger.info(
                f'Skill 7 invoice {invoice_id}: RecebimentoLf '
                f'{existente.id} ja processado (G-RECLF-3 skip)'
            )
            return {
                'status': 'IDEMPOTENT_PROCESSADO',
                'rec_id': existente.id,
                'odoo_invoice_id_fb': None,
                'transfer_status': None,
                'tempo_ms': int((time.time() - t0) * 1000),
                'erro': None,
            }

        # HIGH-3 v17 + F1 v17.5 (Reviewer 1 conf 85): status != 'processado'
        # RETOMAR via svc externo (broadened — antes era so 'processando').
        # Cobertura: 'processando' (crash mid-process), 'erro' (svc falhou
        # mid-etapa), 'pendente' (criado mas svc nao iniciou).
        # Service externo decide entre "comecar do zero" e "retomar" pelo
        # campo etapa_atual (0 = comecar; >0 = retomar). NAO criamos novos
        # RecebimentoLfLote — assumimos que foram criados na invocacao
        # anterior (idempotencia via UK; UNIQUE viola se tentar 2o INSERT).
        retomando = False
        if existente:
            # status='processado' ja' foi tratado acima (IDEMPOTENT_PROCESSADO).
            # Aqui sao todos os demais status: 'processando', 'erro', 'pendente'.
            logger.warning(
                f'Skill 7 invoice {invoice_id}: RecebimentoLf '
                f'{existente.id} em status={existente.status!r}. '
                f'RETOMANDO via processar_recebimento (service externo '
                f'suporta resume via etapa_atual>0). NAO recriando lotes '
                f'(idempotencia G-RECLF-3 UK).'
            )
            retomando = True

        # D9: re-fetch ajustes (anti-DetachedInstance pos-commits svc)
        ajustes_fresh: List = []
        for a in ajustes:
            ajuste_id = a.id if hasattr(a, 'id') else a['id']
            af = safe_session_get(AjusteEstoqueInventario, ajuste_id)
            if af is not None:
                ajustes_fresh.append(af)
        if not ajustes_fresh:
            return {
                'status': 'FALHA',
                'rec_id': None,
                'odoo_invoice_id_fb': None,
                'transfer_status': None,
                'tempo_ms': int((time.time() - t0) * 1000),
                'erro': 'ajustes_refetch_vazio',
            }

        # Fetch invoice Odoo (chave + numero NF)
        try:
            inv_data = self.odoo.read(
                'account.move', [invoice_id],
                ['name', 'l10n_br_chave_nf',
                 'l10n_br_numero_nota_fiscal', 'company_id'],
            )
            if not inv_data:
                return {
                    'status': 'FALHA',
                    'rec_id': None,
                    'odoo_invoice_id_fb': None,
                    'transfer_status': None,
                    'tempo_ms': int((time.time() - t0) * 1000),
                    'erro': 'invoice_sumiu_odoo',
                }
            inv = inv_data[0]
            chave = (
                inv.get('l10n_br_chave_nf') or ajustes_fresh[0].chave_nfe
            )
            numero_nf = str(
                inv.get('l10n_br_numero_nota_fiscal', '') or ''
            )
        except Exception as e:
            logger.error(
                f'Skill 7 invoice {invoice_id}: erro ler invoice: {e}'
            )
            return {
                'status': 'FALHA',
                'rec_id': None,
                'odoo_invoice_id_fb': None,
                'transfer_status': None,
                'tempo_ms': int((time.time() - t0) * 1000),
                'erro': f'erro_ler_invoice: {str(e)[:100]}',
            }

        # Resolver product_ids batch
        cods = sorted({a.cod_produto for a in ajustes_fresh})
        prod_cache = self._resolver_pids_em_batch(cods)

        # HIGH-5 v17: produto_tracking via fetch batch (anti-D-OPS-5)
        tracking_por_pid: Dict[int, str] = {}
        pids_validos = [pid for pid in prod_cache.values() if pid]
        if pids_validos:
            try:
                prods_data = self.odoo.read(
                    'product.product', pids_validos,
                    ['id', 'tracking'],
                )
                tracking_por_pid = {
                    p['id']: p.get('tracking', 'lot')
                    for p in prods_data
                }
            except Exception as e:
                logger.warning(
                    f'Skill 7 invoice {invoice_id}: erro fetch tracking '
                    f'(usando default "lot"): {e}'
                )

        # Criar ou retomar RecebimentoLf + Lotes
        if existente:
            rec = existente
            logger.info(
                f'Skill 7 invoice {invoice_id}: retomando RecebimentoLf '
                f'{rec.id} (status={existente.status}, '
                f'etapa_atual={getattr(existente, "etapa_atual", 0)})'
            )
        else:
            rec = RecebimentoLf(
                odoo_lf_invoice_id=invoice_id,
                numero_nf=numero_nf,
                chave_nfe=chave,
                cnpj_emitente=cnpj_emitente,
                company_id=company_id_recebedor,
                status='pendente',
                usuario=usuario,
                total_etapas=TOTAL_ETAPAS_RECLF,
            )
            db.session.add(rec)
            db.session.flush()

            # Agg (pid, lote_dest, cfop) -> qty
            agg: Dict[Tuple[int, str, str], float] = defaultdict(float)
            for a in ajustes_fresh:
                pid = prod_cache.get(a.cod_produto)
                if not pid:
                    logger.warning(
                        f'Skill 7 invoice {invoice_id}: sem product_id para '
                        f'{a.cod_produto}, pulando ajuste {a.id}'
                    )
                    continue
                lote_dest = (a.lote_destino or 'MIGRAÇÃO').strip()
                # D17: CFOP saida 5xxx -> entrada 1xxx (FB fiscal_position)
                cfop = ACAO_PARA_CFOP_ENTRADA.get(
                    a.acao_decidida, '1903'
                )
                agg[(pid, lote_dest, cfop)] += float(
                    abs(a.qtd_ajuste or 0)
                )

            for (pid, lote_dest, cfop), qty in agg.items():
                if qty <= 0:
                    continue
                # HIGH-5 v17: produto_tracking real
                produto_tracking = tracking_por_pid.get(pid, 'lot')
                db.session.add(RecebimentoLfLote(
                    recebimento_lf_id=rec.id,
                    odoo_product_id=pid,
                    tipo='auto',
                    lote_nome=lote_dest,
                    quantidade=qty,
                    cfop=cfop,
                    produto_tracking=produto_tracking,
                    processado=False,
                ))

            if not commit_resilient():
                logger.error(
                    f'Skill 7 invoice {invoice_id}: commit RecebimentoLf '
                    f'{rec.id} falhou (SSL). FALHA.'
                )
                return {
                    'status': 'FALHA',
                    'rec_id': rec.id,
                    'odoo_invoice_id_fb': None,
                    'transfer_status': None,
                    'tempo_ms': int((time.time() - t0) * 1000),
                    'erro': 'commit_recebimento_falhou',
                }
            logger.info(
                f'Skill 7 invoice {invoice_id}: RecebimentoLf {rec.id} '
                f'criado ({len(agg)} lotes)'
            )

        # HIGH-4 v17: svc externo instanciado fresh
        svc_externo = RecebimentoLfOdooService()

        # Processar SINCRONO (G-RECLF-1: 30-60min/invoice)
        try:
            resultado = svc_externo.processar_recebimento(
                rec.id, usuario_nome=usuario,
            )
        except Exception as e:
            tempo_ms_falha = int((time.time() - t0) * 1000)
            logger.error(
                f'Skill 7 invoice {invoice_id}: processar_recebimento '
                f'falhou: {e}',
                exc_info=True,
            )
            # Re-fetch + auditoria por ajuste
            for a in ajustes_fresh:
                af = safe_session_get(AjusteEstoqueInventario, a.id)
                if af is not None:
                    _registrar_auditoria(
                        ajuste_id=af.id, ciclo=ciclo, fase='F-E',
                        acao='recebimento_lf',
                        modelo_odoo='recebimento_lf',
                        status='FALHA',
                        odoo_id=getattr(rec, 'id', None),
                        erro_msg=str(e)[:500],
                        tempo_ms=tempo_ms_falha,
                        executado_por=usuario,
                    )
            commit_resilient()
            return {
                'status': 'FALHA',
                'rec_id': rec.id,
                'odoo_invoice_id_fb': None,
                'transfer_status': None,
                'tempo_ms': tempo_ms_falha,
                'erro': f'processar_recebimento: {str(e)[:200]}',
            }

        tempo_ms_final = int((time.time() - t0) * 1000)
        transfer_status = resultado.get('transfer_status')
        odoo_invoice_id_fb = resultado.get('odoo_invoice_id')

        # G-RECLF-2: aceita transfer_status='erro' como PARCIAL OK
        is_parcial = (transfer_status == 'erro')

        # Re-fetch ajustes pos-svc (D9 anti-DetachedInstance)
        ajustes_post: List = []
        for a in ajustes_fresh:
            af = safe_session_get(AjusteEstoqueInventario, a.id)
            if af is not None:
                ajustes_post.append(af)

        # Auditoria por ajuste
        status_auditoria = 'PARCIAL' if is_parcial else 'SUCESSO'
        for aj in ajustes_post:
            _registrar_auditoria(
                ajuste_id=aj.id, ciclo=ciclo, fase='F-E',
                acao='recebimento_lf',
                modelo_odoo='recebimento_lf',
                status=status_auditoria,
                odoo_id=odoo_invoice_id_fb,
                resposta=resultado,
                tempo_ms=tempo_ms_final,
                executado_por=usuario,
            )
        commit_resilient()

        # Status final
        if is_parcial:
            status_final = 'PARCIAL'  # G-RECLF-2: FB OK mas FASE 6+7 erro
            logger.warning(
                f'Skill 7 invoice {invoice_id}: FB OK mas transfer FASE 6+7 '
                f'ERRO (rec={rec.id}). G-RECLF-2 aceitando como parcial.'
            )
        elif retomando:
            status_final = 'RETOMADO'
        else:
            status_final = 'CRIADO'

        logger.info(
            f'Skill 7 invoice {invoice_id}: {status_final} '
            f'rec={rec.id} inv_fb={odoo_invoice_id_fb} '
            f'transfer={transfer_status} tempo={tempo_ms_final}ms'
        )

        return {
            'status': status_final,
            'rec_id': rec.id,
            'odoo_invoice_id_fb': odoo_invoice_id_fb,
            'transfer_status': transfer_status,
            'tempo_ms': tempo_ms_final,
            'erro': None,
        }

    def _resolver_pids_em_batch(self, cods: List[str]) -> Dict[str, int]:
        """Helper: cod_produto -> product_id em batch via product.product.

        Pattern espelhado de `FaturamentoPipelineExecutor._resolver_pids_em_batch`.
        Codigos nao encontrados ficam ausentes do dict (caller trata).
        """
        if not cods:
            return {}
        try:
            resp = self.odoo.search_read(
                'product.product',
                [('default_code', 'in', list(cods))],
                ['id', 'default_code'],
            )
            return {r['default_code']: r['id'] for r in resp}
        except Exception as e:
            logger.warning(
                f'_resolver_pids_em_batch falhou para {len(cods)} cods: {e}'
            )
            return {}
