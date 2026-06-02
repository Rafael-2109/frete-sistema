"""escrituracao.py — Atomo C3 macro Skill 7 `escriturando-odoo` (v17.5).

Encapsula a logica de ESCRITURAR ENTRADA de NF SEFAZ-autorizada no destino
via `RecebimentoLf` + agregacao de lotes + invocacao do service externo
`RecebimentoLfOdooService` (37 etapas LF->FB).

Substitui logica inline anteriormente em
`app/odoo/estoque/orchestrators/inventario_pipeline.executar_etapa_e`
(antigo `faturamento_pipeline.py` — renomeado v27+ S3; v17 reverted em
v17.5 por violar a constituicao §6: `faturando-odoo` = SO SAIDA,
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
from datetime import date
from typing import Any, Callable, Dict, List, Optional, Tuple

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

# ============================================================
# Defaults v19+ ABRANGENTE (7 atomos: buscar_dfe, criar_dfe_*, escriturar_dfe,
# gerar_po_from_dfe, preencher_po, confirmar_po, criar_invoice_from_po).
# ============================================================
FIRE_TIMEOUT_DEFAULT_S = 120      # action_X dispara: Odoo retorna timeout normal
POLL_TIMEOUT_PO_DEFAULT_S = 1800  # robo CIEL IT materializa PO em 3-5min/madrugada a >30min/pico
POLL_TIMEOUT_INVOICE_DEFAULT_S = 300  # invoice draft via action_create_invoice
POLL_TIMEOUT_DFE_PROC_DEFAULT_S = 120  # action_processar_arquivo_manual parsea XML
POLL_INTERVAL_S = 2  # gap entre polls

# l10n_br_status CIEL IT do DFe quando a SEFAZ entregou apenas o RESUMO
# (sem XML completo / 0 linhas). DFe nesse estado NAO serve para gerar PO
# (caminho A geraria PO vazia — gotcha G-ENT-2). Ver buscar_dfe (C2).
DFE_STATUS_RESUMO_SEFAZ = '06'

CNPJS_NACOM: frozenset = frozenset({
    '18.467.441/0001-63',  # LF
    '61.724.241/0001-69',  # FB (CNPJ historicamente referido)
    '06.057.223/0001-09',  # CD (placeholder — validar via res.company.vat)
})


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
    `inventario_pipeline._registrar_auditoria` (contexto_origem='escrituracao_lf'
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
            # G-AUDIT-1/N21 (3a cópia, canary P6 2026-05-29): NÃO passar
            # `etapa=fase` — coluna `operacao_odoo_auditoria.etapa` é Integer
            # (string de fase estoura InvalidTextRepresentation). A fase vai em
            # `pipeline_etapa` (String) + `etapa_descricao`.
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

        .. deprecated:: v20+
            Wrapper V1 STRICT mantido para preservar ETAPA E legacy do
            orchestrator (`inventario_pipeline.executar_etapa_e`). Sera
            removido em v21+ ou v22+ apos canary REAL PROD do FLUXO L3
            1.2.x validar substituicao via `executar_fluxo_l3_1_2_x`
            (compoe os 7 atomos ABRANGENTES `buscar_dfe`, `criar_dfe_a_partir_do_invoice_saida`,
            `escriturar_dfe`, `gerar_po_from_dfe`, `preencher_po`,
            `confirmar_po`, `criar_invoice_from_po`).
            Migracao: usar `executar_fluxo_l3_1_2_x` no orchestrator
            (S3 v20+ adiciona flag opt-in `--usar-fluxo-l3-v19`).
            Constituicao: `app/odoo/estoque/CLAUDE.md` §6.5 AP1 (resolvido v19+).
        """
        import warnings as _warnings  # lazy
        _warnings.warn(
            'EscrituracaoLfService.criar_recebimento_orchestrado eh '
            'WRAPPER V1 STRICT deprecado v20+ (mantido para preservar '
            'ETAPA E legacy do orchestrator). Sera removido em v21+ ou '
            'v22+ apos canary REAL PROD do FLUXO L3 1.2.x validar '
            'substituicao via executar_fluxo_l3_1_2_x. Ver CLAUDE.md '
            'estoque §6.5 AP1.',
            DeprecationWarning,
            stacklevel=2,
        )

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

    # ============================================================
    # v19+ ABRANGENTE — 7 atomos para compor via FLUXOS L3 1.2.1 / 1.2.2.
    # Pattern minerado de RecebimentoLfOdooService (4562 LOC NAO MEXER).
    # Cada atomo: 1 operacao versatil + dry-run-first (corrige AP4) +
    # idempotencia via campos Odoo (sem assumir DB local).
    # ============================================================

    def _fire_and_poll(
        self,
        *,
        fire_fn: Callable[[], Any],
        poll_fn: Callable[[], Optional[Any]],
        label: str,
        poll_timeout_s: int = POLL_TIMEOUT_PO_DEFAULT_S,
        poll_interval_s: int = POLL_INTERVAL_S,
    ) -> Any:
        """Helper SSL-resilient: dispara action longa + polling ate' resultado.

        Pattern espelhado de `RecebimentoLfOdooService._fire_and_poll`.
        - `fire_fn`: callable que dispara a action (espera timeout — o callable
          deve internamente passar `timeout_override`+`expected_timeout=True`
          para `odoo.execute_kw` se aplicavel).
        - `poll_fn`: callable que verifica se resultado materializou
          (retorna o resultado se sim, None se ainda nao).

        Levanta `TimeoutError` se poll_timeout_s esgota sem materializar.
        """
        # Dispara (timeout esperado — action longa retorna antes de concluir).
        try:
            fire_fn()
        except Exception as e:
            # `expected_timeout=True` cobre timeout normal; outras exc propagam
            err_low = str(e).lower()
            if 'timeout' not in err_low and 'expected' not in err_low:
                logger.warning(
                    f'_fire_and_poll({label}): fire raised non-timeout: '
                    f'{str(e)[:200]}'
                )
                raise

        # Poll loop
        elapsed = 0
        while elapsed < poll_timeout_s:
            try:
                resultado = poll_fn()
                # CR-v19+-CRIT-1: usar `is not None` para nao confundir
                # po_id=0 (falsy) com "ainda nao materializou". Pattern do
                # service externo RecebimentoLfOdooService preserved.
                if resultado is not None:
                    return resultado
            except Exception as e:
                logger.warning(
                    f'_fire_and_poll({label}) poll attempt erro '
                    f'(continuando): {str(e)[:200]}'
                )
            time.sleep(poll_interval_s)
            elapsed += poll_interval_s

        raise TimeoutError(
            f'_fire_and_poll({label}): poll_timeout_s={poll_timeout_s} '
            f'esgotado sem materializar resultado'
        )

    # ============================================================
    # v23+ G039 — Invariante purchase.team (NF inter-company LF/CD/FB)
    # ============================================================
    # PO criada via FLUXO L3 1.2.x (caminho A ou B) cai em `team_id` default
    # (ex.: 41 'Aprovacao LF - JOSEFA' user_id=78 Edilane). Se PO precisa
    # aprovacao dupla por valor/regra CIEL IT custom, `button_confirm`
    # retorna True mas state fica 'to approve' permanente; `button_approve`
    # via XML-RPC nao destrava quando o user de execucao (ex.: Rafael uid=42)
    # nao e' o user do team. Resultado: FALHA_PASSO_7_SEM_PICKING.
    #
    # SOLUCAO v23+ (codifica workaround manual v22+): garantir purchase.team
    # com user_id=<user_de_execucao> + company_id=<destino>. Se nao existe,
    # CREATE. Caller (orchestrator) substitui team_id static por este team
    # ANTES de preencher_po.
    #
    # Doc: PROTECAO_PROXIMA_SESSAO.md N24 + CLAUDE.md §14 D-V22-3.
    _COMPANY_SIGLA_DEFAULT: Dict[int, str] = {1: 'FB', 4: 'CD', 5: 'LF'}

    def garantir_purchase_team(
        self,
        *,
        user_id: int,
        company_id: int,
        nome_template: str = 'Aprovação {sigla} - {primeiro_nome}',
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Atomo Skill 7 G039: garante purchase.team com (user_id, company_id) ativo.

        Idempotencia: busca `purchase.team` com domain
        `[('user_id','=',user_id),('company_id','=',company_id),('active','=',True)]`.
        Se ja existe -> retorna team_id existente (status='OK_EXISTENTE').
        Se nao existe -> CREATE com nome derivado de `nome_template`
        (status='CRIADO'). Dry-run nao escreve, retorna 'DRY_RUN_OK' + plano.

        Args:
            user_id: res.users.id do user de execucao do pipeline (ex.: Rafael=42).
            company_id: res.company.id da PO (ex.: LF=5).
            nome_template: template do nome do team novo. Placeholders:
                `{sigla}` -> sigla da company (FB/CD/LF; fallback `company_id={id}`)
                `{primeiro_nome}` -> primeiro nome do user (UPPER; fallback 'USER{id}')
            dry_run: True (default) NAO escreve.

        Returns:
            dict com:
              status: 'OK_EXISTENTE' | 'CRIADO' | 'DRY_RUN_OK' | 'FALHA'
              team_id: int | None
              team_data: dict | None (id+name+user_id+company_id+active)
              criado: bool (True se houve CREATE)
              tempo_ms: int
              erro: str | None
        """
        t0 = time.time()
        out: Dict[str, Any] = {
            'status': 'FALHA',
            'team_id': None,
            'team_data': None,
            'criado': False,
            'tempo_ms': 0,
            'erro': None,
        }

        # Pre-cond LEVES (sintaticas)
        if not isinstance(user_id, int) or user_id <= 0:
            out['erro'] = f'user_id_invalido: {user_id!r}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out
        if not isinstance(company_id, int) or company_id <= 0:
            out['erro'] = f'company_id_invalido: {company_id!r}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Busca team existente
        try:
            teams_existentes = self.odoo.execute_kw(
                'purchase.team', 'search_read',
                [[
                    ('user_id', '=', user_id),
                    ('company_id', '=', company_id),
                    ('active', '=', True),
                ]],
                {'fields': ['id', 'name', 'user_id', 'company_id', 'active']},
            )
        except Exception as e:
            out['erro'] = f'erro_search_purchase_team: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if teams_existentes:
            team = teams_existentes[0]
            out['status'] = 'OK_EXISTENTE'
            out['team_id'] = team['id']
            out['team_data'] = team
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Nao existe — preparar CREATE
        sigla = self._COMPANY_SIGLA_DEFAULT.get(company_id, f'company_id={company_id}')

        # Resolve primeiro nome do user (best-effort)
        try:
            user_data = self.odoo.read(
                'res.users', [user_id], ['name', 'login'],
            )
            user_nome_completo = (user_data[0].get('name') if user_data else None) or f'USER{user_id}'
            primeiro_nome = user_nome_completo.split()[0].upper() if user_nome_completo else f'USER{user_id}'
        except Exception as e:
            logger.warning(f'garantir_purchase_team: falha ler res.users {user_id}: {str(e)[:200]}')
            primeiro_nome = f'USER{user_id}'

        nome_novo = nome_template.format(sigla=sigla, primeiro_nome=primeiro_nome)
        values_novo = {
            'name': nome_novo,
            'user_id': user_id,
            'company_id': company_id,
        }

        if dry_run:
            out['status'] = 'DRY_RUN_OK'
            out['plano'] = {
                'create_model': 'purchase.team',
                'values': values_novo,
            }
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # REAL-RUN: CREATE
        try:
            team_id_novo = self.odoo.execute_kw(
                'purchase.team', 'create', [values_novo],
            )
        except Exception as e:
            out['erro'] = f'erro_create_purchase_team: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if not isinstance(team_id_novo, int) or team_id_novo <= 0:
            out['erro'] = f'create_retornou_invalido: {team_id_novo!r}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Confirma via read
        try:
            team_data = self.odoo.read(
                'purchase.team', [team_id_novo],
                ['id', 'name', 'user_id', 'company_id', 'active'],
            )
            out['team_data'] = team_data[0] if team_data else None
        except Exception:
            out['team_data'] = {'id': team_id_novo, 'name': nome_novo, **values_novo}

        out['status'] = 'CRIADO'
        out['team_id'] = team_id_novo
        out['criado'] = True
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    # ============================================================
    # F2a v25+ — Helper publico para alinhar dfe.line.company_id
    # ============================================================
    def alinhar_dfe_lines_company(
        self,
        *,
        dfe_id: int,
        company_destino: int,
    ) -> Dict[str, Any]:
        """Atomo Skill 7 F2a (B-V23-1 generalizado): alinha dfe.line.company_id
        com `company_destino` em batch (idempotente).

        Extracao da logica codificada inline em
        `criar_dfe_a_partir_do_invoice_saida` linhas 1066-1131 (B-V23-1 fix
        raiz v23.5+). F2a v25+ generaliza para uso tambem no caminho A
        (DFe via SEFAZ) — onde nao passamos por
        `criar_dfe_a_partir_do_invoice_saida` mas as lines podem ter
        herdado company do EMITENTE.

        Pre-condicao: DFe ja existe e foi processado (lines criadas).

        Args:
            dfe_id: id do l10n_br_ciel_it_account.dfe.
            company_destino: res.company.id que deve aparecer em todas as
                lines (geralmente 5=LF para entrada industrializacao).

        Returns:
            dict com:
              status: 'OK' | 'IDEMPOTENT_OK' | 'FALHA_NAO_FATAL'
              dfe_id: int
              lines_total: int
              lines_corrigidas: List[int] (ids escritos; vazio se idempotente)
              tempo_ms: int
              erro: str | None (NAO bloqueia caller — fix nao-fatal)
        """
        t0 = time.time()
        out: Dict[str, Any] = {
            'status': 'FALHA_NAO_FATAL',
            'dfe_id': dfe_id,
            'lines_total': 0,
            'lines_corrigidas': [],
            'tempo_ms': 0,
            'erro': None,
        }
        if not isinstance(dfe_id, int) or dfe_id <= 0:
            out['erro'] = f'dfe_id_invalido: {dfe_id!r}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out
        if not isinstance(company_destino, int) or company_destino <= 0:
            out['erro'] = f'company_destino_invalido: {company_destino!r}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        try:
            line_ids = self.odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe.line', 'search',
                [[('dfe_id', '=', dfe_id)]],
            )
        except Exception as e:
            out['erro'] = f'erro_search_dfe_lines: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        out['lines_total'] = len(line_ids) if line_ids else 0
        if not line_ids:
            out['status'] = 'IDEMPOTENT_OK'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        try:
            lines_atuais = self.odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe.line', 'read',
                [line_ids], {'fields': ['id', 'company_id']},
            )
        except Exception as e:
            out['erro'] = f'erro_read_dfe_lines: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        ids_para_corrigir: List[int] = []
        for ln in lines_atuais:
            company_atual = ln.get('company_id')
            company_atual_id = (
                company_atual[0]
                if isinstance(company_atual, list)
                else company_atual
            )
            if company_atual_id != company_destino:
                ids_para_corrigir.append(ln['id'])

        if not ids_para_corrigir:
            out['status'] = 'IDEMPOTENT_OK'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        try:
            self.odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe.line', 'write',
                [ids_para_corrigir, {'company_id': company_destino}],
            )
        except Exception as e:
            out['erro'] = f'erro_write_dfe_lines: {str(e)[:200]}'
            out['lines_corrigidas'] = []
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        logger.info(
            f'alinhar_dfe_lines_company: dfe={dfe_id} F2a aplicado em '
            f'{len(ids_para_corrigir)} dfe.lines '
            f'(company_id -> {company_destino})'
        )
        out['status'] = 'OK'
        out['lines_corrigidas'] = ids_para_corrigir
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    def buscar_dfe(
        self,
        *,
        chave_nfe: str,
        company_id: int,
    ) -> Dict[str, Any]:
        """READ-only: busca DFe por chave_nfe + company_id e QUALIFICA estado.

        Retorna estado canonico para decisao do FLUXO L3 (1.2.1 vs 1.2.2).
        NAO escreve — sem dry_run. Sempre seguro chamar.

        QUALIFICACAO (C2 / G-ENT-2): um DFe pode existir mas estar VAZIO
        (DFe-resumo SEFAZ: `l10n_br_status='06'` e/ou 0 linhas
        `l10n_br_ciel_it_account.dfe.line`, sem XML completo). Esse DFe NAO
        serve para gerar PO (caminho A geraria PO vazia). buscar_dfe conta as
        linhas e reporta `populado` + `n_linhas`. Quando vazio, `status` vira
        'resumo_vazio' para o orchestrator forcar caminho B (criar/popular via
        XML da NF de SAIDA). A DECISAO de caminho (A vs B) vive no orchestrator
        `executar_fluxo_l3_1_2_x` (constituicao §6) — este atomo so REPORTA.

        Args:
            chave_nfe: chave NF-e 44 digitos (`protnfe_infnfe_chnfe` no DFe).
            company_id: company onde o DFe seria recebido.

        Returns:
            dict com:
              encontrado: bool
              dfe_id: int | None
              status: str ('pendente' | 'a_processar' | 'processado'
                           | 'resumo_vazio' | 'ausente')
              populado: bool — True se ha >0 dfe.line (XML completo parseado)
              n_linhas: int — qtd de l10n_br_ciel_it_account.dfe.line do DFe
              raw: dict — campos lidos do DFe (vazio se nao encontrado)
              tempo_ms: int
              erro: str | None
        """
        t0 = time.time()
        out: Dict[str, Any] = {
            'encontrado': False,
            'dfe_id': None,
            'status': 'ausente',
            'populado': False,
            'n_linhas': 0,
            'raw': {},
            'tempo_ms': 0,
            'erro': None,
        }
        # Pre-cond simples (READ — nao raise antes de tentar)
        if not chave_nfe or len(chave_nfe.strip()) < 40:
            out['erro'] = 'chave_nfe_invalida'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        try:
            resp = self.odoo.search_read(
                'l10n_br_ciel_it_account.dfe',
                [
                    ('protnfe_infnfe_chnfe', '=', chave_nfe.strip()),
                    ('company_id', '=', company_id),
                ],
                ['id', 'l10n_br_status', 'l10n_br_situacao_dfe',
                 'nfe_infnfe_ide_nnf', 'protnfe_infnfe_chnfe',
                 'purchase_id'],
            )
        except Exception as e:
            out['erro'] = f'odoo_search_falhou: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if not resp:
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        dfe = resp[0]
        # QUALIFICACAO C2 (G-ENT-2): contar linhas do DFe. DFe-resumo SEFAZ
        # (status '06' e/ou 0 linhas) NAO esta populado — geraria PO vazia
        # se tratado como caminho A. Contamos via search_count em
        # l10n_br_ciel_it_account.dfe.line (FK dfe_id).
        try:
            n_linhas = self.odoo.search_count(
                'l10n_br_ciel_it_account.dfe.line',
                [('dfe_id', '=', dfe['id'])],
            )
        except Exception as e:
            out['erro'] = f'odoo_search_count_dfe_line_falhou: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out
        populado = n_linhas > 0

        # Mapeamento status: l10n_br_status CIEL IT
        # '03' = pendente, '04'/'05' = processado, default = a_processar.
        # DFE_STATUS_RESUMO_SEFAZ ('06', DFe-resumo) OU sem linhas ->
        # 'resumo_vazio' (forca caminho B).
        st_raw = (dfe.get('l10n_br_status') or '').strip()
        if st_raw == DFE_STATUS_RESUMO_SEFAZ or not populado:
            status = 'resumo_vazio'
        elif st_raw in ('04', '05'):
            status = 'processado'
        elif st_raw == '03':
            status = 'pendente'
        else:
            status = 'a_processar'

        out['encontrado'] = True
        out['dfe_id'] = dfe['id']
        out['status'] = status
        out['populado'] = populado
        out['n_linhas'] = n_linhas
        out['raw'] = dfe
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    def criar_dfe_a_partir_do_invoice_saida(
        self,
        *,
        invoice_id_saida: int,
        company_destino: int,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Cria DFe no destino a partir do XML autorizado de account.move SAIDA.

        Pattern minerado de `_step_00_criar_dfe_fb` (L838-977) +
        `_step_25_upload_dfe_cd` (L2834-3037) do svc externo. Lê
        `account.move.l10n_br_xml_aut_nfe` (base64) + cria DFe no destino +
        dispara `action_processar_arquivo_manual` (fire-and-poll para Odoo
        parsear o XML).

        Args:
            invoice_id_saida: account.move da NF SAIDA (state=posted,
                situacao=autorizado, l10n_br_xml_aut_nfe nao-vazio).
            company_destino: company onde DFe sera criado (1=FB, 4=CD, 5=LF).
            dry_run: True (default) NAO escreve; reporta planejamento.

        Idempotencia (C2 / G-ENT-2): se ja existe DFe na company destino,
        distingue dois casos via `buscar_dfe(...)['populado']`:
          - populado (>0 dfe.line)   -> IDEMPOTENT_EXISTE (nada a fazer).
          - NAO populado (DFe-resumo SEFAZ status='06'/0 linhas) -> POPULA o
            DFe existente fazendo write do XML da SAIDA + reprocessando
            (action_processar_arquivo_manual). Retorna status 'POPULADO'.
        Sem este split, um DFe-resumo levaria o orchestrator a gerar PO vazia.

        Returns:
            dict com:
              status: 'DRY_RUN_OK' | 'CRIADO' | 'POPULADO'
                      | 'IDEMPOTENT_EXISTE' | 'FALHA'
              dfe_id: int | None
              chave_nfe: str | None
              tempo_ms: int
              erro: str | None
        """
        t0 = time.time()
        out: Dict[str, Any] = {
            'status': 'FALHA',
            'dfe_id': None,
            'chave_nfe': None,
            'tempo_ms': 0,
            'erro': None,
        }

        # Pre-cond LEVES (nao raise antes de dry_run check — AP4)
        if not isinstance(invoice_id_saida, int) or invoice_id_saida <= 0:
            out['erro'] = 'invoice_id_saida_invalido'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out
        if company_destino not in (1, 4, 5):
            out['erro'] = f'company_destino_invalida: {company_destino}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Ler XML do invoice SAIDA (sempre — necessario p/ chave_nfe no plano)
        try:
            inv_resp = self.odoo.read(
                'account.move', [invoice_id_saida],
                ['l10n_br_xml_aut_nfe', 'l10n_br_chave_nf',
                 'l10n_br_numero_nota_fiscal', 'company_id', 'state'],
            )
        except Exception as e:
            out['erro'] = f'erro_ler_invoice_saida: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if not inv_resp:
            out['erro'] = 'invoice_saida_sumiu'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        inv = inv_resp[0]
        chave = (inv.get('l10n_br_chave_nf') or '').strip()
        xml_b64 = inv.get('l10n_br_xml_aut_nfe')
        out['chave_nfe'] = chave

        if not chave:
            out['erro'] = 'chave_nfe_vazia'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out
        if not xml_b64:
            out['erro'] = 'xml_aut_nfe_vazio'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Idempotencia C2 (G-ENT-2): DFe ja existe? Distinguir populado vs
        # DFe-resumo vazio. So' e' IDEMPOTENT_EXISTE quando JA esta populado
        # (>0 dfe.line). Se existe mas e' resumo vazio, POPULAR via write do
        # XML da SAIDA + reprocessar (em vez de criar duplicado).
        ja = self.buscar_dfe(chave_nfe=chave, company_id=company_destino)
        dfe_existente_id = ja.get('dfe_id') if ja.get('encontrado') else None
        existe_populado = bool(ja.get('encontrado')) and bool(ja.get('populado'))
        if existe_populado:
            out['status'] = 'IDEMPOTENT_EXISTE'
            out['dfe_id'] = ja['dfe_id']
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        modo = 'popular_existente' if dfe_existente_id else 'criar_novo'

        # Dry-run: reporta plano sem write
        if dry_run:
            out['status'] = 'DRY_RUN_OK'
            out['modo'] = modo
            out['dfe_id'] = dfe_existente_id  # None se criar_novo
            out['plano'] = {
                'modo': modo,
                'create_model': 'l10n_br_ciel_it_account.dfe',
                'write_values': {
                    'company_id': company_destino,
                    'l10n_br_xml_dfe': '<base64 size=%d>' % len(xml_b64 or ''),
                },
                'after_write': 'action_processar_arquivo_manual fire_and_poll',
            }
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # REAL-RUN: (a) popular DFe-resumo existente via write OU
        #           (b) criar DFe novo. Ambos disparam processar abaixo.
        if dfe_existente_id:
            try:
                self.odoo.write(
                    'l10n_br_ciel_it_account.dfe',
                    [dfe_existente_id],
                    {
                        'company_id': company_destino,
                        'l10n_br_xml_dfe': xml_b64,
                    },
                )
                dfe_id = dfe_existente_id
                logger.info(
                    f'criar_dfe_a_partir_do_invoice_saida: DFe-resumo '
                    f'{dfe_id} POPULADO via XML da SAIDA '
                    f'(company={company_destino}, chave={chave[:20]}...)'
                )
            except Exception as e:
                out['erro'] = f'write_dfe_resumo_falhou: {str(e)[:200]}'
                out['dfe_id'] = dfe_existente_id
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out
        else:
            try:
                dfe_id = self.odoo.create(
                    'l10n_br_ciel_it_account.dfe',
                    {
                        'company_id': company_destino,
                        'l10n_br_xml_dfe': xml_b64,
                    },
                )
                logger.info(
                    f'criar_dfe_a_partir_do_invoice_saida: DFe {dfe_id} criado '
                    f'(company={company_destino}, chave={chave[:20]}...)'
                )
            except Exception as e:
                out['erro'] = f'create_dfe_falhou: {str(e)[:200]}'
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out

        # Fire-and-poll: action_processar_arquivo_manual
        def fire_processar():
            return self.odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe',
                'action_processar_arquivo_manual',
                [[dfe_id]],
                {},
            )

        def poll_processar():
            d = self.odoo.read(
                'l10n_br_ciel_it_account.dfe', [dfe_id],
                ['l10n_br_status', 'l10n_br_situacao_dfe'],
            )
            if d and (d[0].get('l10n_br_status') or '').strip() in (
                '03', '04', '05'
            ):
                return d[0]
            return None

        try:
            self._fire_and_poll(
                fire_fn=fire_processar,
                poll_fn=poll_processar,
                label='processar_dfe',
                poll_timeout_s=POLL_TIMEOUT_DFE_PROC_DEFAULT_S,
            )
        except TimeoutError as e:
            out['status'] = 'FALHA'
            out['dfe_id'] = dfe_id
            out['erro'] = f'processar_timeout: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out
        except Exception as e:
            out['status'] = 'FALHA'
            out['dfe_id'] = dfe_id
            out['erro'] = f'processar_falhou: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # v23.5+ B-V23-1 FIX RAIZ: alinhar dfe.line.company_id com pai DFe.
        # ----
        # Quando XML da SAIDA cross-company (ex: FB->LF) eh parseado pelo
        # Odoo CIEL IT, o pai `l10n_br_ciel_it_account.dfe` recebe
        # `company_id = company_destino` (LF=5) mas as filhas
        # `l10n_br_ciel_it_account.dfe.line` HERDAM `company_id` da company
        # da SAIDA original (FB=1). Sintoma: passo 9 `action_create_invoice`
        # falha com `<Fault 4: 'Rafael nao tem acesso leitura' a dfe.line>`
        # porque o metodo CIEL IT faz `with_company(dfe.company_id=5)` que
        # reduz `allowed_company_ids=[5]`; dfe.lines company=1 nao passam
        # pela `ir.rule id=353 'dfe_line multi-company'` (domain
        # [('company_id', 'in', company_ids)]) nesse contexto reduzido.
        #
        # FIX: apos `action_processar_arquivo_manual` parsear o XML e criar
        # as lines, ler todas as lines do DFe e fazer batch write
        # `company_id=company_destino` se houver inconsistencia.
        # Idempotencia: se todas ja estao corretas, skip write.
        #
        # Validado v23+ workaround manual em PROD (dfe 43533 lines
        # 129585/86 FB->LF) + codificado v23.5+ como fix raiz.
        # Doc: PROTECAO N25 + VALIDACAO B-V23-1.
        lines_atualizadas: list = []
        try:
            line_ids = self.odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe.line', 'search',
                [[('dfe_id', '=', dfe_id)]],
            )
            if line_ids:
                lines_atuais = self.odoo.execute_kw(
                    'l10n_br_ciel_it_account.dfe.line', 'read',
                    [line_ids], {'fields': ['id', 'company_id']},
                )
                ids_para_corrigir = []
                for ln in lines_atuais:
                    company_atual = ln.get('company_id')
                    company_atual_id = (
                        company_atual[0]
                        if isinstance(company_atual, list)
                        else company_atual
                    )
                    if company_atual_id != company_destino:
                        ids_para_corrigir.append(ln['id'])
                if ids_para_corrigir:
                    self.odoo.execute_kw(
                        'l10n_br_ciel_it_account.dfe.line', 'write',
                        [ids_para_corrigir, {'company_id': company_destino}],
                    )
                    lines_atualizadas = ids_para_corrigir
                    logger.info(
                        f'criar_dfe_a_partir_do_invoice_saida: B-V23-1 fix '
                        f'aplicado em {len(ids_para_corrigir)} dfe.lines '
                        f'(company_id -> {company_destino}). lines={ids_para_corrigir}'
                    )
                else:
                    logger.debug(
                        f'criar_dfe_a_partir_do_invoice_saida: B-V23-1 '
                        f'idempotent — todas {len(line_ids)} dfe.lines ja '
                        f'em company_id={company_destino}'
                    )
        except Exception as e:
            # NAO-fatal: lines com company errada caem no passo 9 com erro
            # claro 'leitura dfe.line'. Logamos warning para diagnostico.
            logger.warning(
                f'criar_dfe_a_partir_do_invoice_saida: B-V23-1 fix falhou '
                f'(non-fatal): {str(e)[:200]}'
            )

        out['status'] = 'POPULADO' if dfe_existente_id else 'CRIADO'
        out['dfe_id'] = dfe_id
        if lines_atualizadas:
            out['dfe_lines_corrigidas_b_v23_1'] = lines_atualizadas
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    def escriturar_dfe(
        self,
        *,
        dfe_id: int,
        l10n_br_tipo_pedido: str,
        data_entrada: Optional[str] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Configura DFe (l10n_br_tipo_pedido + l10n_br_data_entrada).

        Pattern minerado de `_step_03_configurar_dfe` (L1054-1090) +
        `_step_26_configurar_dfe_cd` (L3039-3088). write em
        `l10n_br_ciel_it_account.dfe` para informar tipo de pedido que
        permitira `action_gerar_po_dfe` derivar PO + fiscal_position
        correta no proximo passo.

        Args:
            dfe_id: id do DFe (criado via caminho A ou B).
            l10n_br_tipo_pedido: 'serv-industrializacao' | 'transf-filial'
                | 'retorno' | 'outro'. Olhar `MATRIZ_INTERCOMPANY[acao]
                ['entrada'][(co, cd)]['l10n_br_tipo_pedido_entrada']`.
            data_entrada: 'YYYY-MM-DD' (default hoje).
            dry_run: True (default) NAO escreve.

        Returns:
            dict com:
              status: 'DRY_RUN_OK' | 'ESCRITURADO' | 'FALHA'
              dfe_id: int
              l10n_br_tipo_pedido: str
              data_entrada: str
              tempo_ms: int
              erro: str | None
        """
        t0 = time.time()
        out: Dict[str, Any] = {
            'status': 'FALHA',
            'dfe_id': dfe_id,
            'l10n_br_tipo_pedido': l10n_br_tipo_pedido,
            'data_entrada': data_entrada or date.today().strftime('%Y-%m-%d'),
            'tempo_ms': 0,
            'erro': None,
        }
        if not isinstance(dfe_id, int) or dfe_id <= 0:
            out['erro'] = 'dfe_id_invalido'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out
        if l10n_br_tipo_pedido not in (
            'serv-industrializacao', 'transf-filial',
            'retorno', 'outro', 'industrializacao',
            'perda', 'dev-industrializacao',
        ):
            out['erro'] = f'tipo_pedido_invalido: {l10n_br_tipo_pedido!r}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        values = {
            'l10n_br_data_entrada': out['data_entrada'],
            'l10n_br_tipo_pedido': l10n_br_tipo_pedido,
        }

        # FIX A v20+ (MEDIO critico fiscal): idempotencia pre-write +
        # preservacao de l10n_br_data_entrada ja populada.
        #
        # Caso descoberto em PROD 2026-05-26 (subagente audit Fase A):
        # 4 DFes INDUSTRIALIZACAO_FB_LF tem l10n_br_data_entrada ja setada
        # (18-20/05); sem este check, real-run reescreveria para date.today()
        # (26/05) alterando data fiscal de invoice posted. Risco SPED/contabil.
        #
        # Regras:
        #   - Se ambos campos ja iguais ao proposto -> IDEMPOTENT_ESCRITURADO
        #     (no-op sem write)
        #   - Se l10n_br_data_entrada ja populada (truthy) E caller usou default
        #     -> PRESERVAR data atual (sobrescrever proposto)
        #   - Re-check apos preservacao: se ambos iguais -> IDEMPOTENT
        try:
            pre_check = self.odoo.read(
                'l10n_br_ciel_it_account.dfe', [dfe_id],
                ['l10n_br_tipo_pedido', 'l10n_br_data_entrada'],
            )
        except Exception as e:
            out['erro'] = f'erro_pre_read_dfe: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if not pre_check:
            out['erro'] = 'pre_read_dfe_nao_encontrou'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        pre = pre_check[0]
        atual_tipo = pre.get('l10n_br_tipo_pedido')
        atual_data_raw = pre.get('l10n_br_data_entrada')

        # CR-v20+-HIGH-1 (review code-reviewer 2026-05-26): normalizar
        # data para 'YYYY-MM-DD' antes de comparar. Odoo 17 XML-RPC
        # retorna fields.Date como string 'YYYY-MM-DD' OU False; mas se
        # CIEL IT customizar para fields.Datetime, retorna 'YYYY-MM-DD HH:MM:SS'
        # e comparacao silenciosamente falharia, forcando write em invoice
        # posted (exatamente o risco que FIX A foi desenhado para evitar).
        # `str(x)[:10]` defensivamente extrai apenas a parte de data.
        atual_data = str(atual_data_raw)[:10] if atual_data_raw else None

        # Caso 1: ambos campos ja iguais ao proposto -> no-op
        if atual_tipo == l10n_br_tipo_pedido and atual_data == out['data_entrada']:
            out['status'] = 'IDEMPOTENT_ESCRITURADO'
            out['idempotent_via'] = 'campos_ja_iguais'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Caso 2: data_entrada ja populada (truthy) E caller usou default
        # (data_entrada=None original que virou date.today()) -> PRESERVAR
        # atual. Operador que passa data_entrada explicito sobrepoe esta logica.
        # Detecta default via comparacao com date.today() atual.
        if atual_data and data_entrada is None:
            out['data_entrada'] = atual_data
            values['l10n_br_data_entrada'] = atual_data
            # Re-check apos preservacao
            if atual_tipo == l10n_br_tipo_pedido:
                out['status'] = 'IDEMPOTENT_ESCRITURADO'
                out['idempotent_via'] = 'data_preservada_tipo_igual'
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out

        if dry_run:
            out['status'] = 'DRY_RUN_OK'
            out['plano'] = {
                'write_model': 'l10n_br_ciel_it_account.dfe',
                'write_ids': [dfe_id],
                'write_values': values,
            }
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        try:
            self.odoo.write(
                'l10n_br_ciel_it_account.dfe', [dfe_id], values,
            )
            # CR-v19+-MED-1: verify AMBOS os campos (CIEL IT pode descartar
            # silenciosamente um write parcial via hook de recalculo —
            # `memory/ciel_it_quirks.md` G018-similar pattern).
            check = self.odoo.read(
                'l10n_br_ciel_it_account.dfe', [dfe_id],
                ['l10n_br_tipo_pedido', 'l10n_br_data_entrada'],
            )
            if not check:
                out['erro'] = 'write_nao_persistiu_dfe_sumiu'
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out
            chk = check[0]
            if chk.get('l10n_br_tipo_pedido') != l10n_br_tipo_pedido:
                out['erro'] = 'write_nao_persistiu_tipo_pedido'
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out
            # CR-v20+-HIGH-1: normalizar data antes de comparar (idem
            # FIX A pre-read — defesa contra fields.Datetime customizacao).
            chk_data_raw = chk.get('l10n_br_data_entrada')
            chk_data = str(chk_data_raw)[:10] if chk_data_raw else None
            if chk_data != out['data_entrada']:
                out['erro'] = 'write_nao_persistiu_data_entrada'
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out
        except Exception as e:
            out['erro'] = f'write_dfe_falhou: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        out['status'] = 'ESCRITURADO'
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    # ============================================================
    # v23.5+ B-V23-2 — Helper resolver_account_id_por_company
    # ============================================================
    # `action_gerar_po_dfe` cria PO.lines no destino (company=LF=5) mas
    # `account_id` e resolvido para `account.account` da company FONTE
    # (FB id=22611 '3202010001 CUSTOS') em vez do equivalente DESTINO
    # (LF id=26459). Cada code de conta existe em todas 4 companies.
    # Sintoma: passo 9 `action_create_invoice` falha com `"Empresas
    # incompativeis: PO line LF vs Account FB"`.
    #
    # Helper resolve o account.account equivalente no destino por
    # (code, company_id). Hook em `gerar_po_from_dfe` apos status=CRIADO
    # itera PO.lines + corrige account_id divergente em batch.
    # Doc: PROTECAO N26 + VALIDACAO B-V23-2.

    def resolver_account_id_por_company(
        self,
        *,
        account_id_fonte: int,
        company_destino: int,
    ) -> Dict[str, Any]:
        """Helper Skill 7 B-V23-2: resolve account.account equivalente em outra company.

        Le `code` do account_id_fonte + search `(code, company_id=destino)`.
        Retorna id do account na company destino, ou None se nao existir
        (caller decide fallback ou erro).

        Args:
            account_id_fonte: id atual do account.account (qualquer company).
            company_destino: company alvo (1=FB, 4=CD, 5=LF).

        Returns:
            dict com:
              status: 'OK_EXISTE' | 'JA_NA_DESTINO' | 'NAO_EXISTE_DESTINO' | 'FALHA'
              account_id_destino: int | None
              code: str | None
              tempo_ms: int
              erro: str | None
        """
        t0 = time.time()
        out: Dict[str, Any] = {
            'status': 'FALHA',
            'account_id_destino': None,
            'code': None,
            'tempo_ms': 0,
            'erro': None,
        }

        if not isinstance(account_id_fonte, int) or account_id_fonte <= 0:
            out['erro'] = f'account_id_fonte_invalido: {account_id_fonte!r}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out
        if not isinstance(company_destino, int) or company_destino <= 0:
            out['erro'] = f'company_destino_invalida: {company_destino!r}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Le account fonte (code + company_id)
        try:
            ac_fonte = self.odoo.read(
                'account.account', [account_id_fonte],
                ['id', 'code', 'name', 'company_id'],
            )
        except Exception as e:
            out['erro'] = f'erro_ler_account_fonte: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if not ac_fonte:
            out['erro'] = 'account_fonte_nao_existe'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        ac = ac_fonte[0]
        code = (ac.get('code') or '').strip()
        company_fonte = ac.get('company_id')
        company_fonte_id = (
            company_fonte[0] if isinstance(company_fonte, list)
            else company_fonte
        )
        out['code'] = code

        if not code:
            out['erro'] = 'account_fonte_sem_code'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Ja esta na company correta?
        if company_fonte_id == company_destino:
            out['status'] = 'JA_NA_DESTINO'
            out['account_id_destino'] = account_id_fonte
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Search account equivalente na company destino
        try:
            ac_destino = self.odoo.execute_kw(
                'account.account', 'search_read',
                [[('code', '=', code), ('company_id', '=', company_destino)]],
                {'fields': ['id', 'code', 'name', 'company_id'], 'limit': 1},
            )
        except Exception as e:
            out['erro'] = f'erro_search_account_destino: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if not ac_destino:
            out['status'] = 'NAO_EXISTE_DESTINO'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        out['status'] = 'OK_EXISTE'
        out['account_id_destino'] = ac_destino[0]['id']
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    def gerar_po_from_dfe(
        self,
        *,
        dfe_id: int,
        fire_timeout_s: int = FIRE_TIMEOUT_DEFAULT_S,
        poll_timeout_s: int = POLL_TIMEOUT_PO_DEFAULT_S,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Dispara action_gerar_po_dfe + poll ate' purchase.order materializar.

        Pattern minerado de `_step_04_gerar_po` (L1096-1165). Idempotencia
        via `dfe.purchase_id` antes de disparar — se ja existe PO, retorna
        sem fire.

        Args:
            dfe_id: id do DFe ja escriturado (l10n_br_tipo_pedido set).
            fire_timeout_s: timeout do disparo da action (default 120s).
            poll_timeout_s: timeout total do polling (default 1800s).
            dry_run: True (default) NAO dispara.

        Returns:
            dict com:
              status: 'DRY_RUN_OK' | 'CRIADO' | 'IDEMPOTENT_EXISTE' |
                      'FALHA' | 'TIMEOUT'
              po_id: int | None
              tempo_ms: int
              erro: str | None
        """
        t0 = time.time()
        out: Dict[str, Any] = {
            'status': 'FALHA',
            'po_id': None,
            'tempo_ms': 0,
            'erro': None,
        }
        if not isinstance(dfe_id, int) or dfe_id <= 0:
            out['erro'] = 'dfe_id_invalido'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # FIX B v20+ (CRITICO): idempotencia via TRES CAMINHOS de vinculo
        # DFe<->PO no CIEL IT. Pattern minerado de `validacao_nf_po_service.py`
        # L530-534+L575-609 (service de match NF x PO validado em PROD):
        #   1. DFE.purchase_id (~14.6% — many2one direto, excepcional)
        #   2. DFE.purchase_fiscal_id (~75% dos concluidos — escrituracao)
        #   3. PO.dfe_id reverso (~85.4% — caminho primario em status=04)
        #
        # Caso descoberto em PROD 2026-05-26 (subagente audit Fase A):
        # 4 DFes do ciclo INVENTARIO_2026_05 INDUSTRIALIZACAO_FB_LF
        # (42868/42930/42931/42882) tem `purchase_id=False` mas pipeline
        # completo no Odoo (PO+picking+invoice existem). Rafael confirmou
        # que sem cobrir os 3 caminhos, `_fire_and_poll` dispara action e
        # DUPLICA PO+picking+invoice.
        # Doc: `/tmp/subagent-findings/audit_idempotencia_v20_1779815000.md`.
        try:
            dfe_check = self.odoo.read(
                'l10n_br_ciel_it_account.dfe', [dfe_id],
                ['purchase_id', 'purchase_fiscal_id'],
            )
        except Exception as e:
            out['erro'] = f'erro_ler_dfe: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if dfe_check:
            chk = dfe_check[0]
            # Caminho 1: purchase_id direto (14.6%)
            purchase_id = chk.get('purchase_id')
            if purchase_id:
                po_id_ex = (
                    purchase_id[0]
                    if isinstance(purchase_id, (list, tuple))
                    else purchase_id
                )
                out['status'] = 'IDEMPOTENT_EXISTE'
                out['po_id'] = po_id_ex
                out['idempotent_via'] = 'dfe_purchase_id_direto'
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out

            # Caminho 2: purchase_fiscal_id (75% dos concluidos — escrituracao)
            purchase_fiscal_id = chk.get('purchase_fiscal_id')
            if purchase_fiscal_id:
                po_id_ex = (
                    purchase_fiscal_id[0]
                    if isinstance(purchase_fiscal_id, (list, tuple))
                    else purchase_fiscal_id
                )
                out['status'] = 'IDEMPOTENT_EXISTE'
                out['po_id'] = po_id_ex
                out['idempotent_via'] = 'dfe_purchase_fiscal_id'
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out

        # Caminho 3 (85.4%): fallback search reverso po.dfe_id
        try:
            po_reverso = self.odoo.search_read(
                'purchase.order',
                [('dfe_id', '=', dfe_id), ('state', '!=', 'cancel')],
                ['id'],
                limit=1, order='id desc',
            )
        except Exception as e:
            out['erro'] = f'erro_search_po_reverso: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if po_reverso:
            out['status'] = 'IDEMPOTENT_EXISTE'
            out['po_id'] = po_reverso[0]['id']
            out['idempotent_via'] = 'po_dfe_id_reverso'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if dry_run:
            out['status'] = 'DRY_RUN_OK'
            out['plano'] = {
                'action': 'l10n_br_ciel_it_account.dfe.action_gerar_po_dfe',
                'dfe_ids': [dfe_id],
                'context': {'validate_analytic': True},
                'fire_timeout_s': fire_timeout_s,
                'poll_timeout_s': poll_timeout_s,
            }
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # REAL-RUN: fire + poll
        def fire_gerar_po():
            return self.odoo.execute_kw(
                'l10n_br_ciel_it_account.dfe',
                'action_gerar_po_dfe',
                [[dfe_id]],
                {'context': {'validate_analytic': True}},
                timeout_override=fire_timeout_s,
                expected_timeout=True,
            )

        def poll_gerar_po():
            # poll via dfe.purchase_id (primario) + fallback search
            d = self.odoo.read(
                'l10n_br_ciel_it_account.dfe', [dfe_id],
                ['purchase_id'],
            )
            if d and d[0].get('purchase_id'):
                p = d[0]['purchase_id']
                return p[0] if isinstance(p, (list, tuple)) else p
            search = self.odoo.search_read(
                'purchase.order',
                [('dfe_id', '=', dfe_id), ('state', '!=', 'cancel')],
                ['id'],
                limit=1, order='id desc',
            )
            if search:
                return search[0]['id']
            return None

        try:
            po_id = self._fire_and_poll(
                fire_fn=fire_gerar_po,
                poll_fn=poll_gerar_po,
                label='gerar_po',
                poll_timeout_s=poll_timeout_s,
            )
        except TimeoutError as e:
            out['status'] = 'TIMEOUT'
            out['erro'] = str(e)[:200]
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out
        except Exception as e:
            out['status'] = 'FALHA'
            out['erro'] = f'fire_falhou: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        out['status'] = 'CRIADO'
        # CR-v19+-HIGH-2: simplificar coercion (segundo branch era morto)
        out['po_id'] = int(po_id) if po_id is not None else None

        # v23.5+ B-V23-2 FIX RAIZ: alinhar PO.line.account_id com company da line.
        # ----
        # `action_gerar_po_dfe` cria PO no DESTINO (LF=5) mas as PO.lines
        # recebem `account_id` apontando para account.account da company
        # FONTE (FB id=22611) em vez do equivalente DESTINO (LF id=26459).
        # Sintoma cascateado pos-fix B-V23-1: passo 9 `action_create_invoice`
        # falha com `"Empresas incompativeis: PO line LF vs Account FB"`.
        #
        # FIX: ler PO.lines + para cada line: ler account_id atual + resolver
        # account.account equivalente em line.company_id via
        # `resolver_account_id_por_company` + batch write apenas se diferente.
        # Idempotencia: se accounts ja estao alinhados, skip write.
        #
        # NOTA: hook so' roda em status=CRIADO (PO recem-criada pelo robo).
        # Para status=IDEMPOTENT_EXISTE (PO ja existia antes do disparo),
        # NAO tocamos — operador pode estar em estado avancado (invoice ja
        # criada, etc). Hook nao-fatal: log warning se algo der errado.
        # Doc: PROTECAO N26 + VALIDACAO B-V23-2.
        po_lines_corrigidas: list = []
        try:
            po_data = self.odoo.read(
                'purchase.order', [out['po_id']],
                ['order_line'],
            )
            if po_data and po_data[0].get('order_line'):
                line_ids = po_data[0]['order_line']
                lines_atuais = self.odoo.execute_kw(
                    'purchase.order.line', 'read',
                    [line_ids], {'fields': ['id', 'company_id', 'account_id']},
                )
                # Agrupar IDs novos por (company_destino, account_id_destino)
                # para batch writes (1 write por (company,account_destino_id))
                writes_por_account: Dict[int, list] = {}
                for ln in lines_atuais:
                    line_company = ln.get('company_id')
                    line_company_id = (
                        line_company[0] if isinstance(line_company, list)
                        else line_company
                    )
                    line_account = ln.get('account_id')
                    line_account_id = (
                        line_account[0] if isinstance(line_account, list)
                        else line_account
                    )
                    if not line_account_id or not line_company_id:
                        continue
                    resolver_out = self.resolver_account_id_por_company(
                        account_id_fonte=line_account_id,
                        company_destino=line_company_id,
                    )
                    rstatus = resolver_out.get('status')
                    if rstatus == 'JA_NA_DESTINO':
                        # idempotente — account ja' esta na company da line
                        continue
                    if rstatus == 'OK_EXISTE':
                        novo_id = resolver_out['account_id_destino']
                        writes_por_account.setdefault(novo_id, []).append(
                            ln['id']
                        )
                    elif rstatus == 'NAO_EXISTE_DESTINO':
                        # Operador precisa criar account equivalente — log
                        # warning + segue. Caller (orchestrator passo 9)
                        # detectara erro 'Empresas incompativeis' com
                        # diagnostico claro.
                        logger.warning(
                            f'gerar_po_from_dfe: B-V23-2 account code='
                            f'{resolver_out.get("code")!r} NAO existe em '
                            f'company={line_company_id}. PO line '
                            f'{ln["id"]} continuara com account divergente.'
                        )
                # Aplica writes em batch
                for novo_account_id, ids_linhas in writes_por_account.items():
                    self.odoo.execute_kw(
                        'purchase.order.line', 'write',
                        [ids_linhas, {'account_id': novo_account_id}],
                    )
                    po_lines_corrigidas.extend(ids_linhas)
                    logger.info(
                        f'gerar_po_from_dfe: B-V23-2 fix aplicado em '
                        f'{len(ids_linhas)} PO.lines (account_id -> '
                        f'{novo_account_id}). lines={ids_linhas}'
                    )
                if not po_lines_corrigidas:
                    logger.debug(
                        f'gerar_po_from_dfe: B-V23-2 idempotent — todas '
                        f'{len(lines_atuais)} PO.lines ja alinhadas'
                    )
        except Exception as e:
            # NAO-fatal: caller detectara erro 'Empresas incompativeis' no
            # passo 9 se account ficar divergente.
            logger.warning(
                f'gerar_po_from_dfe: B-V23-2 fix falhou (non-fatal): '
                f'{str(e)[:200]}'
            )

        if po_lines_corrigidas:
            out['po_lines_corrigidas_b_v23_2'] = po_lines_corrigidas
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    def preencher_po(
        self,
        *,
        po_id: int,
        team_id: int,
        payment_term_id: int,
        picking_type_id: int,
        company_id: int,
        payment_provider_id: int,
        l10n_br_tipo_pedido: Optional[str] = None,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Preenche purchase.order com campos obrigatorios pos-DFe.

        Pattern minerado de `_step_06_configurar_po` (L1193-1236). Write
        em campos derivados de MATRIZ_INTERCOMPANY + constants
        (TEAM_ID, PAYMENT_PROVIDER, PAYMENT_TERM, PICKING_TYPE, COMPANY).
        Caller (fluxo L3) decide os valores; atomo apenas executa write.

        Args:
            po_id: id purchase.order ja criada via gerar_po_from_dfe.
            team_id: sale.team.id.
            payment_term_id: account.payment.term.id.
            picking_type_id: stock.picking.type.id.
            company_id: res.company.id (deve casar com DFe).
            payment_provider_id: payment.provider.id (G029).
            l10n_br_tipo_pedido: F3c v25+ — quando fornecido, sobrescreve o
                tipo herdado do DFe (ex: 'compra' no DFe -> 'serv-
                industrializacao' na PO para INDUSTRIALIZACAO_FB_LF).
                Se None: nao toca, PO mantem o que herdou.
                Valores aceitos: 'serv-industrializacao' | 'transf-filial' |
                'retorno' | 'outro' | 'compra' | 'industrializacao' |
                'perda' | 'dev-industrializacao' (mesma whitelist do DFe).
            dry_run: True (default) NAO escreve.

        Returns:
            dict com:
              status: 'DRY_RUN_OK' | 'PREENCHIDO' | 'FALHA'
              po_id: int
              tempo_ms: int
              erro: str | None
        """
        t0 = time.time()
        out: Dict[str, Any] = {
            'status': 'FALHA',
            'po_id': po_id,
            'tempo_ms': 0,
            'erro': None,
        }
        # Pre-cond LEVES
        if not isinstance(po_id, int) or po_id <= 0:
            out['erro'] = 'po_id_invalido'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out
        for nome, val in (
            ('team_id', team_id), ('payment_term_id', payment_term_id),
            ('picking_type_id', picking_type_id), ('company_id', company_id),
            ('payment_provider_id', payment_provider_id),
        ):
            if not isinstance(val, int) or val <= 0:
                out['erro'] = f'{nome}_invalido: {val!r}'
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out

        # F3c v25+: validacao do tipo do pedido (whitelist espelhada de
        # `escriturar_dfe` linha 1186-1193).
        if l10n_br_tipo_pedido is not None and l10n_br_tipo_pedido not in (
            'serv-industrializacao', 'transf-filial',
            'retorno', 'outro', 'industrializacao',
            'perda', 'dev-industrializacao', 'compra',
        ):
            out['erro'] = (
                f'l10n_br_tipo_pedido_invalido: {l10n_br_tipo_pedido!r}'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        values = {
            'team_id': team_id,
            'payment_provider_id': payment_provider_id,
            'payment_term_id': payment_term_id,
            'company_id': company_id,
            'picking_type_id': picking_type_id,
        }
        if l10n_br_tipo_pedido is not None:
            values['l10n_br_tipo_pedido'] = l10n_br_tipo_pedido

        if dry_run:
            out['status'] = 'DRY_RUN_OK'
            out['plano'] = {
                'write_model': 'purchase.order',
                'write_ids': [po_id],
                'write_values': values,
            }
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        try:
            self.odoo.write('purchase.order', [po_id], values)
            check = self.odoo.read(
                'purchase.order', [po_id],
                ['team_id', 'picking_type_id'],
            )
            if not check:
                out['erro'] = 'po_sumiu_pos_write'
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out
        except Exception as e:
            out['erro'] = f'write_po_falhou: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        out['status'] = 'PREENCHIDO'
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    def confirmar_po(
        self,
        *,
        po_id: int,
        auto_approve: bool = True,
        fire_timeout_s: int = FIRE_TIMEOUT_DEFAULT_S,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """button_confirm + (cond) button_approve em purchase.order.

        Pattern minerado de `_step_07_confirmar_po` + `_step_08_aprovar_po`
        (L1300-1391). State sai de 'draft' -> 'purchase' (ou 'to approve'
        -> 'purchase' via button_approve).

        Args:
            po_id: id purchase.order ja preenchida via preencher_po.
            auto_approve: True (default) chama button_approve se state
                ficar 'to approve' apos confirm (non-fatal se falhar).
            fire_timeout_s: timeout do disparo (default 120s).
            dry_run: True (default) NAO confirma.

        Returns:
            dict com:
              status: 'DRY_RUN_OK' | 'CONFIRMADO' | 'IDEMPOTENT_CONFIRMADO' |
                      'FALHA'
              po_id: int
              state_final: str
              tempo_ms: int
              erro: str | None
        """
        t0 = time.time()
        out: Dict[str, Any] = {
            'status': 'FALHA',
            'po_id': po_id,
            'state_final': None,
            'tempo_ms': 0,
            'erro': None,
        }
        if not isinstance(po_id, int) or po_id <= 0:
            out['erro'] = 'po_id_invalido'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Idempotencia: ja confirmado?
        try:
            check = self.odoo.read(
                'purchase.order', [po_id], ['state'],
            )
        except Exception as e:
            out['erro'] = f'erro_ler_po: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if not check:
            out['erro'] = 'po_sumiu'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        state_atual = check[0].get('state')
        if state_atual in ('purchase', 'done'):
            out['status'] = 'IDEMPOTENT_CONFIRMADO'
            out['state_final'] = state_atual
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if dry_run:
            out['status'] = 'DRY_RUN_OK'
            out['plano'] = {
                'action': 'purchase.order.button_confirm',
                'po_ids': [po_id],
                'state_atual': state_atual,
                'auto_approve': auto_approve,
            }
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # REAL-RUN: button_confirm
        try:
            self.odoo.execute_kw(
                'purchase.order', 'button_confirm', [[po_id]],
                {'context': {'validate_analytic': True}},
                timeout_override=fire_timeout_s,
                expected_timeout=True,
            )
        except Exception as e:
            err_low = str(e).lower()
            if 'timeout' not in err_low and 'expected' not in err_low:
                out['erro'] = f'button_confirm_falhou: {str(e)[:200]}'
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out

        # Poll: state != 'draft'
        elapsed = 0
        state_final = state_atual
        while elapsed < fire_timeout_s:
            try:
                c = self.odoo.read('purchase.order', [po_id], ['state'])
                if c:
                    state_final = c[0].get('state')
                    if state_final != 'draft':
                        break
            except Exception:
                pass
            time.sleep(POLL_INTERVAL_S)
            elapsed += POLL_INTERVAL_S

        if state_final == 'draft':
            out['erro'] = 'po_state_draft_apos_confirm'
            out['state_final'] = state_final
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Auto-approve (non-fatal)
        if auto_approve and state_final == 'to approve':
            try:
                self.odoo.execute_kw(
                    'purchase.order', 'button_approve', [[po_id]],
                )
                c = self.odoo.read('purchase.order', [po_id], ['state'])
                if c:
                    state_final = c[0].get('state')
            except Exception as e:
                logger.warning(
                    f'confirmar_po button_approve falhou (non-fatal): '
                    f'{str(e)[:200]}'
                )

        out['status'] = 'CONFIRMADO'
        out['state_final'] = state_final
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    def criar_invoice_from_po(
        self,
        *,
        po_id: int,
        fire_timeout_s: int = FIRE_TIMEOUT_DEFAULT_S,
        poll_timeout_s: int = POLL_TIMEOUT_INVOICE_DEFAULT_S,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """Dispara action_create_invoice + poll ate' invoice draft aparecer.

        Pattern minerado de `_step_13_criar_invoice` (L1578-1629).
        Idempotencia: se po.invoice_ids ja contem algum invoice, retorna
        ultimo sem disparar.

        Args:
            po_id: id purchase.order confirmada (state='purchase').
            fire_timeout_s: timeout do disparo (default 120s).
            poll_timeout_s: timeout do polling (default 300s).
            dry_run: True (default) NAO dispara.

        Returns:
            dict com:
              status: 'DRY_RUN_OK' | 'CRIADO' | 'IDEMPOTENT_EXISTE' |
                      'TIMEOUT' | 'FALHA'
              invoice_id: int | None
              tempo_ms: int
              erro: str | None
        """
        t0 = time.time()
        out: Dict[str, Any] = {
            'status': 'FALHA',
            'invoice_id': None,
            'tempo_ms': 0,
            'erro': None,
        }
        if not isinstance(po_id, int) or po_id <= 0:
            out['erro'] = 'po_id_invalido'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Idempotencia
        try:
            po_data = self.odoo.read(
                'purchase.order', [po_id], ['invoice_ids', 'state'],
            )
        except Exception as e:
            out['erro'] = f'erro_ler_po: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if not po_data:
            out['erro'] = 'po_sumiu'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        inv_ids_existentes = po_data[0].get('invoice_ids', []) or []
        if inv_ids_existentes:
            out['status'] = 'IDEMPOTENT_EXISTE'
            out['invoice_id'] = inv_ids_existentes[-1]
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if dry_run:
            out['status'] = 'DRY_RUN_OK'
            out['plano'] = {
                'action': 'purchase.order.action_create_invoice',
                'po_ids': [po_id],
                'fire_timeout_s': fire_timeout_s,
                'poll_timeout_s': poll_timeout_s,
            }
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # REAL-RUN: fire + poll
        def fire_criar():
            return self.odoo.execute_kw(
                'purchase.order', 'action_create_invoice', [[po_id]],
                {},
                timeout_override=fire_timeout_s,
                expected_timeout=True,
            )

        def poll_criar():
            p = self.odoo.read(
                'purchase.order', [po_id], ['invoice_ids'],
            )
            if p and p[0].get('invoice_ids'):
                return p[0]['invoice_ids'][-1]
            return None

        try:
            invoice_id = self._fire_and_poll(
                fire_fn=fire_criar,
                poll_fn=poll_criar,
                label='criar_invoice',
                poll_timeout_s=poll_timeout_s,
            )
        except TimeoutError as e:
            out['status'] = 'TIMEOUT'
            out['erro'] = str(e)[:200]
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out
        except Exception as e:
            out['status'] = 'FALHA'
            out['erro'] = f'fire_falhou: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        out['status'] = 'CRIADO'
        out['invoice_id'] = int(invoice_id) if isinstance(
            invoice_id, (int, float)
        ) else None
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out
