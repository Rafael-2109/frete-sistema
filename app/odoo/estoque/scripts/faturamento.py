"""faturamento.py — Skill 8 ATOMICA L2 `faturando-odoo` (v24+ — AP6 refator).

5 atomos ABRANGENTES sobre `account.move` (NF de SAIDA inter-company),
espelhando o pattern da Skill 7 `escrituracao.py` ABRANGENTE v19+ (7 atomos).

Constituicao §6.5 AP6 (v24+ RESOLVIDO PARCIAL + v27+ S3 rename):
este modulo encapsula as 5 operacoes das ETAPAs C+D do orchestrator
`inventario_pipeline.py` (renomeado de `faturamento_pipeline.py` em
v27+ S3; stub alias compat preservado para retrocompatibilidade):

  1. validar_invoice_constants     — pre-cond fiscal_position/tipo_pedido/payment_term
  2. liberar_faturamento           — action_liberar_faturamento via Skill 5 LEGACY
  3. polling_invoice               — fire-and-poll aguardar_invoice_do_robo (Skill 5 LEGACY)
  4. validar_invoice_pos_robo      — aplica G029 + G007 + G034 via _invoice_helpers
  5. transmitir_sefaz              — Playwright SEFAZ IRREVERSIVEL

Cada atomo eh **dry-run-first** + **versatil** (qualquer direcao FB↔LF↔CD)
+ **auto-seguro** (gotchas codificados intra-atomo). Composicao via:

  - Orchestrator C3 `inventario_pipeline.py` (ETAPAS C+D compoem os 5 atomos)
  - FLUXO L3 1.1.x (saida pura) — pendente v25+ markdown
  - FLUXO L3 1.3 (transferencia completa = 1.1.x + 1.2.x) — pendente v25+ markdown

Gotchas codificados (invariantes intra-atomo):
  G016    : commit_resilient + SSL drop + dispose proativo
  G019/G020: validar state='done' antes de liberar_faturamento (codificado na Skill 5)
  G029    : payment_provider_id=38 (SEM_PAGAMENTO) — _invoice_helpers
  G007    : price_unit fallback std_price ou 0.01 — _invoice_helpers
  G034    : DEV_* fiscal_position+tipo_pedido — _invoice_helpers
  D5      : SNAPSHOT meta antes do polling (sessao pode expirar)
  D7      : HARD_FAIL_CONFIG_ERRORS aborta batch SEFAZ
  D8      : idempotencia TRIPLA (sem invoice_id / por invoice no batch / por persistencia)
  D9      : re-fetch via safe_session_get apos commits
  CRITICAL-1 v17: commit POS-Playwright falha NAO conta sucesso (DB nao persistido)
  MED C-1: registrar situacao_nf != 'autorizado' em erro_msg
  MED C-2: persistir cstat+xmotivo em falha SEFAZ

Spec:
  app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md §6+ (AP6 refator v24+)
  app/odoo/estoque/CLAUDE.md §6 Tabela 1 (Skill 8 ATOMICA L2)
  app/odoo/estoque/orchestrators/inventario_pipeline.py (v23+ ETAPAS C+D
    originais + v25+ S1 opt-in --usar-skill8-atomica-v25 delegando a este
    modulo; v27+ S3 renomeado de faturamento_pipeline.py com stub alias)
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any, Dict, FrozenSet, List, Optional

from app.odoo.estoque.scripts._commit_helpers import (
    commit_resilient,
    safe_session_get,
)
from app.odoo.estoque.scripts._invoice_helpers import (
    PERFIL_INVENTARIO_INTER_COMPANY,
    _validar_perfil,
    corrigir_price_zero_em_invoice,
    garantir_fiscal_setup,
    garantir_payment_provider,
)
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


# ============================================================
# Constants Skill 8 ATOMICA L2 (v24+)
# ============================================================

# Timeouts/Retry (defaults — caller pode sobrescrever)
F5D_POLLING_TIMEOUT_DEFAULT_S: int = 1800   # 30min polling invoice CIEL IT
F5D_POLL_INTERVAL_DEFAULT_S: int = 40       # 40s entre checks
F5E_PLAYWRIGHT_MAX_TENTATIVAS_DEFAULT: int = 15
F5E_PLAYWRIGHT_INTERVALO_RETRY_DEFAULT_S: int = 120

# D7: erros de config que ABORTAM batch SEFAZ inteiro (operador deve intervir)
HARD_FAIL_CONFIG_ERRORS: FrozenSet[str] = frozenset({
    'playwright_indisponivel',
    'odoo_password_ausente',
    'odoo_username_ausente',
})

# Campos de constants validados em validar_invoice_constants (pre-cond)
# Caller passa dict {campo: valor_esperado}; atomo le e compara.
CONSTANTS_CAMPOS_VALIDAVEIS: FrozenSet[str] = frozenset({
    'fiscal_position_id',
    'l10n_br_tipo_pedido',
    'payment_term_id',
    'journal_id',
    'partner_id',
    'company_id',
})


# ============================================================
# Helper privado de auditoria (contexto_origem='faturamento')
# ============================================================

def _registrar_auditoria(
    *,
    ajuste_id: Optional[int],
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
    executado_por: str = 'faturamento_svc',
) -> None:
    """Registra operacao em operacao_odoo_auditoria (contexto faturamento).

    Lazy import de OperacaoOdooAuditoria. Pattern espelhado de
    `escrituracao._registrar_auditoria` (contexto_origem='faturamento'
    distingue da Skill 7 'escrituracao_lf' e do orchestrator
    'inventario_pipeline').

    Falha de auditoria NAO derruba operacao real (pattern service legado L569).
    """
    try:
        from app.odoo.models import OperacaoOdooAuditoria  # lazy
        external_id_seg = (
            f'A{ajuste_id:06d}' if ajuste_id is not None else 'BATCH'
        )
        external_id = (
            f'FAT-{ciclo}-{external_id_seg}-{fase}-{uuid.uuid4().hex[:8]}'
        )
        OperacaoOdooAuditoria.registrar(
            external_id=external_id,
            tabela_origem='ajuste_estoque_inventario',
            registro_id=ajuste_id,
            acao=acao,
            modelo_odoo=modelo_odoo or 'account.move',
            etapa_descricao=f'{fase} {acao}',
            status=status,
            payload_json=payload,
            resposta_json=resposta,
            erro_msg=erro_msg,
            tempo_execucao_ms=tempo_ms,
            pipeline_etapa=fase,
            contexto_origem='faturamento',
            contexto_ref=ciclo,
            executado_por=executado_por,
            odoo_id=odoo_id,
        )
    except Exception as e:
        logger.error(
            f'auditoria faturamento fase={fase} falhou: {e}', exc_info=True,
        )


# ============================================================
# Service Principal — FaturamentoInvoiceService
# ============================================================

class FaturamentoInvoiceService:
    """Skill 8 ATOMICA L2 `faturando-odoo`: 5 atomos sobre account.move.

    Cada atomo eh dry-run-first (default seguro) + versatil + auto-seguro.
    Composicao via orchestrator C3 `inventario_pipeline` ou FLUXOS L3
    (1.1.x saida pura, 1.3 transferencia completa).

    Atomos publicos (ordem tipica de uso):

        validar_invoice_constants   pre-cond fiscal antes de liberar
        liberar_faturamento         dispara robo CIEL IT (action_liberar)
        polling_invoice             aguarda robo criar invoice
        validar_invoice_pos_robo    aplica G029+G007+G034 pos-criacao
        transmitir_sefaz            Playwright SEFAZ IRREVERSIVEL

    Uso (composicao manual em Python):

        from app.odoo.estoque.scripts.faturamento import (
            FaturamentoInvoiceService,
        )
        from app.odoo.estoque.scripts.picking import StockPickingService

        odoo = get_odoo_connection()
        picking_svc = StockPickingService(odoo=odoo)
        svc = FaturamentoInvoiceService(odoo=odoo, picking_svc=picking_svc)

        # 1. Liberar faturamento (dispara robo)
        r1 = svc.liberar_faturamento(
            picking_id=12345, ajuste_ids=[111, 112],
            ciclo='INVENTARIO_2026_05',
            dry_run=False, confirmar=True,
        )
        # 2. Polling invoice
        r2 = svc.polling_invoice(
            picking_id=12345, ajuste_ids=[111, 112],
            ciclo='INVENTARIO_2026_05',
            timeout_s=1800, dry_run=False,
        )
        invoice_id = r2['invoice_id']
        # 3. Validar pos-robo
        r3 = svc.validar_invoice_pos_robo(
            invoice_id=invoice_id, ajuste_id_primeiro=111,
            ciclo='INVENTARIO_2026_05',
            dry_run=False, confirmar=True,
        )
        # 4. Transmitir SEFAZ (IRREVERSIVEL — exige confirmar_sefaz)
        r4 = svc.transmitir_sefaz(
            invoice_id=invoice_id, ajuste_ids=[111, 112],
            ciclo='INVENTARIO_2026_05',
            dry_run=False, confirmar_sefaz=True,
        )
    """

    def __init__(
        self,
        *,
        odoo: Optional[Any] = None,
        picking_svc: Optional[Any] = None,
    ) -> None:
        """Inicializa o service.

        Args:
            odoo: conexao XML-RPC (default: get_odoo_connection()).
            picking_svc: instancia de StockPickingService (Skill 5 LEGACY)
                usada para delegar liberar_faturamento + aguardar_invoice.
                Default: lazy-init na primeira chamada que precisar.
        """
        self.odoo = odoo or get_odoo_connection()
        self._picking_svc = picking_svc

    @property
    def picking_svc(self) -> Any:
        """Lazy init de StockPickingService (Skill 5 LEGACY)."""
        if self._picking_svc is None:
            from app.odoo.estoque.scripts.picking import StockPickingService
            self._picking_svc = StockPickingService(odoo=self.odoo)
        return self._picking_svc

    # ============================================================
    # ATOMO 1 — validar_invoice_constants
    # ============================================================

    def validar_invoice_constants(
        self,
        *,
        invoice_id: int,
        constants_esperadas: Dict[str, Any],
        ajuste_id: Optional[int] = None,
        ciclo: str = '',
        dry_run: bool = True,
        usuario: str = 'faturamento_svc',
    ) -> Dict[str, Any]:
        """Pre-cond fiscal: valida que account.move tem constants esperadas.

        Le os campos especificados em `constants_esperadas` e compara com
        os valores do account.move atual. Util ANTES de liberar_faturamento
        para garantir que o robo CIEL IT vai criar invoice com fiscal_position
        + l10n_br_tipo_pedido + payment_term + journal corretos.

        Campos suportados (CONSTANTS_CAMPOS_VALIDAVEIS):
          - fiscal_position_id
          - l10n_br_tipo_pedido
          - payment_term_id
          - journal_id
          - partner_id
          - company_id

        Para campos relational (X2many de tipo (id, name)): compara o ID.

        Args:
            invoice_id: account.move.id a validar.
            constants_esperadas: dict {campo: valor_esperado}.
            ajuste_id: id do ajuste (auditoria; opcional).
            ciclo: identificador do ciclo (auditoria).
            dry_run: True (default) NAO escreve nada — sempre READ-only.
                Mantido para consistencia da API (todos atomos tem flag).
            usuario: identificador para auditoria.

        Returns:
            dict com:
              status: 'OK' (todos campos batem) | 'FALHA_DIVERGENCIA' |
                      'FALHA_INVOICE_NAO_EXISTE' | 'FALHA_CAMPO_INVALIDO'
              campos_validados: lista de campos checados
              divergencias: dict {campo: {'esperado': X, 'atual': Y}}
              tempo_ms: tempo total da operacao
        """
        t0 = time.time()
        out: Dict[str, Any] = {
            'atomo': 'validar_invoice_constants',
            'invoice_id': invoice_id,
            'ciclo': ciclo,
            'ajuste_id': ajuste_id,
            'dry_run': dry_run,
            'campos_validados': [],
            'divergencias': {},
        }

        # Validar campos suportados
        campos_invalidos = (
            set(constants_esperadas.keys()) - CONSTANTS_CAMPOS_VALIDAVEIS
        )
        if campos_invalidos:
            out['status'] = 'FALHA_CAMPO_INVALIDO'
            out['erro'] = (
                f'Campos nao validaveis: {sorted(campos_invalidos)}. '
                f'Suportados: {sorted(CONSTANTS_CAMPOS_VALIDAVEIS)}'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        campos_a_ler = sorted(constants_esperadas.keys())

        try:
            registros = self.odoo.read(
                'account.move', [invoice_id], campos_a_ler,
            )
        except Exception as e:
            out['status'] = 'FALHA_INVOICE_NAO_EXISTE'
            out['erro'] = f'read account.move {invoice_id}: {e}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if not registros:
            out['status'] = 'FALHA_INVOICE_NAO_EXISTE'
            out['erro'] = f'account.move id={invoice_id} nao encontrado'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        invoice_atual = registros[0]
        out['campos_validados'] = campos_a_ler

        # Comparar campos
        for campo, esperado in constants_esperadas.items():
            atual = invoice_atual.get(campo)
            # Odoo retorna campos relational como [id, name] ou False
            if isinstance(atual, list) and len(atual) >= 1:
                atual_id = atual[0]
            else:
                atual_id = atual
            if atual_id != esperado:
                out['divergencias'][campo] = {
                    'esperado': esperado,
                    'atual': atual_id,
                    'atual_raw': atual,
                }

        if out['divergencias']:
            out['status'] = 'FALHA_DIVERGENCIA'
        else:
            out['status'] = 'OK'

        out['tempo_ms'] = int((time.time() - t0) * 1000)

        _registrar_auditoria(
            ajuste_id=ajuste_id, ciclo=ciclo,
            fase='F5_VALIDAR_CONSTANTS', acao='validar_invoice_constants',
            status=out['status'],
            payload={'constants_esperadas': constants_esperadas},
            resposta={
                'campos_validados': out['campos_validados'],
                'divergencias': out['divergencias'],
            },
            odoo_id=invoice_id, modelo_odoo='account.move',
            tempo_ms=out['tempo_ms'], executado_por=usuario,
        )
        return out

    # ============================================================
    # ATOMO 2 — liberar_faturamento
    # ============================================================

    def liberar_faturamento(
        self,
        *,
        picking_id: int,
        ajuste_ids: Optional[List[int]] = None,
        ciclo: str = '',
        dry_run: bool = True,
        confirmar: bool = False,
        usuario: str = 'faturamento_svc',
    ) -> Dict[str, Any]:
        """Dispara action_liberar_faturamento (robo CIEL IT cria invoice).

        DELEGA `StockPickingService.liberar_faturamento` (Skill 5 LEGACY)
        que codifica G019/G020 (validar state='done' antes de chamar).

        Apos esta chamada, o robo CIEL IT cria automaticamente o
        account.move correspondente (pode levar ate 30 min). Use
        `polling_invoice` para fire-and-poll do resultado.

        Args:
            picking_id: stock.picking.id em state='done'.
            ajuste_ids: lista de ajustes associados (auditoria).
            ciclo: identificador do ciclo (auditoria).
            dry_run: True (default) NAO chama Odoo; reporta planejamento.
            confirmar: exigido com dry_run=False para chamar Odoo.
            usuario: identificador para auditoria.

        Returns:
            dict com:
              status: 'DRY_RUN_OK' | 'OK' | 'BLOQUEADO_SEM_CONFIRMAR' |
                      'FALHA_PICKING_NAO_DONE' | 'FALHA_PICKING_NAO_EXISTE' |
                      'FALHA'
              picking_id: input
              picking_state: state lido do Odoo
              tempo_ms: tempo total da operacao
        """
        t0 = time.time()
        ajuste_ids = ajuste_ids or []
        ajuste_id_primeiro = ajuste_ids[0] if ajuste_ids else None

        out: Dict[str, Any] = {
            'atomo': 'liberar_faturamento',
            'picking_id': picking_id,
            'ajuste_ids': ajuste_ids,
            'ciclo': ciclo,
            'dry_run': dry_run,
        }

        # Real-run exige confirmar explicito
        if not dry_run and not confirmar:
            out['status'] = 'BLOQUEADO_SEM_CONFIRMAR'
            out['erro'] = (
                'Real-run exige confirmar=True para chamar Odoo '
                '(action_liberar_faturamento dispara robo CIEL IT — '
                'cria invoice no Odoo, NAO REVERSIVEL via XML-RPC).'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Ler state ANTES (validacao + planejamento dry-run)
        try:
            p = self.odoo.read(
                'stock.picking', [picking_id], ['state', 'name'],
            )
        except Exception as e:
            out['status'] = 'FALHA_PICKING_NAO_EXISTE'
            out['erro'] = f'read stock.picking {picking_id}: {e}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if not p:
            out['status'] = 'FALHA_PICKING_NAO_EXISTE'
            out['erro'] = f'stock.picking id={picking_id} nao encontrado'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        out['picking_state'] = p[0]['state']
        out['picking_name'] = p[0]['name']

        if p[0]['state'] != 'done':
            out['status'] = 'FALHA_PICKING_NAO_DONE'
            out['erro'] = (
                f'Picking {picking_id} state={p[0]["state"]!r} '
                "(esperado 'done' para liberar_faturamento). "
                'F5b validar() pode ter tido false-positive (G019). '
                'Re-tentar validar antes de liberar.'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if dry_run:
            out['status'] = 'DRY_RUN_OK'
            out['observacao'] = (
                f'Real-run chamaria action_liberar_faturamento([{picking_id}]) '
                f'no Odoo. Robo CIEL IT criaria account.move em 3-30min.'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            _registrar_auditoria(
                ajuste_id=ajuste_id_primeiro, ciclo=ciclo,
                fase='F5c_LIBERADO', acao='liberar_faturamento',
                status='DRY_RUN_OK',
                payload={'picking_id': picking_id},
                odoo_id=picking_id, modelo_odoo='stock.picking',
                tempo_ms=out['tempo_ms'], executado_por=usuario,
            )
            return out

        # REAL-RUN: delegar para Skill 5 LEGACY
        try:
            self.picking_svc.liberar_faturamento(picking_id)
        except Exception as e:
            out['status'] = 'FALHA'
            out['erro'] = str(e)[:500]
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            _registrar_auditoria(
                ajuste_id=ajuste_id_primeiro, ciclo=ciclo,
                fase='F5c_LIBERADO', acao='liberar_faturamento',
                status='FALHA',
                erro_msg=str(e)[:500],
                odoo_id=picking_id, modelo_odoo='stock.picking',
                tempo_ms=out['tempo_ms'], executado_por=usuario,
            )
            return out

        out['status'] = 'OK'
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        _registrar_auditoria(
            ajuste_id=ajuste_id_primeiro, ciclo=ciclo,
            fase='F5c_LIBERADO', acao='liberar_faturamento',
            status='OK',
            payload={'picking_id': picking_id},
            odoo_id=picking_id, modelo_odoo='stock.picking',
            tempo_ms=out['tempo_ms'], executado_por=usuario,
        )
        return out

    # ============================================================
    # ATOMO 3 — polling_invoice
    # ============================================================

    def polling_invoice(
        self,
        *,
        picking_id: int,
        ajuste_ids: Optional[List[int]] = None,
        ciclo: str = '',
        timeout_s: int = F5D_POLLING_TIMEOUT_DEFAULT_S,
        poll_interval_s: int = F5D_POLL_INTERVAL_DEFAULT_S,
        dry_run: bool = True,
        usuario: str = 'faturamento_svc',
    ) -> Dict[str, Any]:
        """Fire-and-poll: aguarda robo CIEL IT criar invoice apos liberar.

        DELEGA `StockPickingService.aguardar_invoice_do_robo` (Skill 5 LEGACY)
        que faz busca por `account.move.ref=picking_name` (Metodo 1).

        Args:
            picking_id: stock.picking.id ja com liberar_faturamento disparado.
            ajuste_ids: lista de ajustes associados (auditoria).
            ciclo: identificador do ciclo (auditoria).
            timeout_s: segundos totais ate desistir (default 1800 = 30min).
            poll_interval_s: segundos entre tentativas (default 40).
            dry_run: True (default) NAO chama Odoo; reporta planejamento.
            usuario: identificador para auditoria.

        Returns:
            dict com:
              status: 'DRY_RUN_OK' | 'OK' | 'TIMEOUT' | 'FALHA'
              invoice_id: account.move.id (None se timeout ou falha)
              picking_id: input
              tempo_ms: tempo total da operacao (proximo de timeout em TIMEOUT)
        """
        t0 = time.time()
        ajuste_ids = ajuste_ids or []
        ajuste_id_primeiro = ajuste_ids[0] if ajuste_ids else None

        out: Dict[str, Any] = {
            'atomo': 'polling_invoice',
            'picking_id': picking_id,
            'ajuste_ids': ajuste_ids,
            'ciclo': ciclo,
            'timeout_s': timeout_s,
            'poll_interval_s': poll_interval_s,
            'dry_run': dry_run,
            'invoice_id': None,
        }

        if dry_run:
            out['status'] = 'DRY_RUN_OK'
            out['observacao'] = (
                f'Real-run faria fire-and-poll de ate {timeout_s}s '
                f'({poll_interval_s}s interval) por account.move '
                f'criada pelo robo CIEL IT a partir do picking {picking_id}.'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # REAL-RUN: delegar para Skill 5 LEGACY
        try:
            invoice_id = self.picking_svc.aguardar_invoice_do_robo(
                picking_id,
                timeout=timeout_s,
                poll_interval=poll_interval_s,
            )
        except Exception as e:
            out['status'] = 'FALHA'
            out['erro'] = str(e)[:500]
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            _registrar_auditoria(
                ajuste_id=ajuste_id_primeiro, ciclo=ciclo,
                fase='F5d_INVOICE_GERADA', acao='polling_invoice',
                status='FALHA',
                erro_msg=str(e)[:500],
                odoo_id=picking_id, modelo_odoo='stock.picking',
                tempo_ms=out['tempo_ms'], executado_por=usuario,
            )
            return out

        out['tempo_ms'] = int((time.time() - t0) * 1000)
        out['invoice_id'] = invoice_id

        if invoice_id:
            out['status'] = 'OK'
            _registrar_auditoria(
                ajuste_id=ajuste_id_primeiro, ciclo=ciclo,
                fase='F5d_INVOICE_GERADA', acao='polling_invoice',
                status='SUCESSO',
                resposta={'invoice_id': invoice_id, 'picking_id': picking_id},
                odoo_id=invoice_id, modelo_odoo='account.move',
                tempo_ms=out['tempo_ms'], executado_por=usuario,
            )
        else:
            out['status'] = 'TIMEOUT'
            out['erro'] = (
                f'Robo CIEL IT nao criou invoice no timeout {timeout_s}s '
                f'(picking {picking_id})'
            )
            _registrar_auditoria(
                ajuste_id=ajuste_id_primeiro, ciclo=ciclo,
                fase='F5d', acao='polling_invoice',
                status='TIMEOUT',
                erro_msg=out['erro'],
                odoo_id=picking_id, modelo_odoo='stock.picking',
                tempo_ms=out['tempo_ms'], executado_por=usuario,
            )
        return out

    # ============================================================
    # ATOMO 4 — validar_invoice_pos_robo
    # ============================================================

    def validar_invoice_pos_robo(
        self,
        *,
        invoice_id: int,
        ajuste_id_primeiro: int,
        perfil: str = PERFIL_INVENTARIO_INTER_COMPANY,
        ciclo: str = '',
        dry_run: bool = True,
        confirmar: bool = False,
        usuario: str = 'faturamento_svc',
    ) -> Dict[str, Any]:
        """Aplica sub-etapas G029 + G007 + G034 apos robo criar invoice.

        Delega `_invoice_helpers` (perfil 'inventario-inter-company'):
          - F5d.5 (G029): garantir_payment_provider — payment_provider_id=38
          - F5d.6 (G007): corrigir_price_zero_em_invoice — fallback std_price
          - F5d.7 (G034): garantir_fiscal_setup — DEV_* FP/tipo_pedido

        Helpers sao idempotentes (checam estado pre-existente).

        Args:
            invoice_id: account.move.id recem-criada pelo robo.
            ajuste_id_primeiro: id do primeiro ajuste (helpers leem acao_decidida).
            perfil: V1 = 'inventario-inter-company'.
                Outros perfis raise NotImplementedError nos helpers.
            ciclo: identificador do ciclo (auditoria).
            dry_run: True (default) NAO chama Odoo; reporta planejamento.
            confirmar: exigido com dry_run=False para escrever no Odoo.
            usuario: identificador para auditoria.

        Returns:
            dict com:
              status: 'DRY_RUN_OK' | 'OK' | 'OK_PARCIAL' |
                      'BLOQUEADO_SEM_CONFIRMAR' | 'FALHA_PERFIL_INVALIDO' |
                      'FALHA_AJUSTE_NAO_EXISTE' | 'FALHA'
              sub_etapas: dict com contadores f5d5_ok/falha, f5d6_corrigidas/falha,
                          f5d7_ok/skip/falha
              tempo_ms: tempo total da operacao
        """
        t0 = time.time()
        out: Dict[str, Any] = {
            'atomo': 'validar_invoice_pos_robo',
            'invoice_id': invoice_id,
            'ajuste_id_primeiro': ajuste_id_primeiro,
            'ciclo': ciclo,
            'perfil': perfil,
            'dry_run': dry_run,
            'sub_etapas': {
                'f5d5_payment_provider_ok': 0,
                'f5d5_payment_provider_falha': 0,
                'f5d6_price_zero_corrigidas': 0,
                'f5d6_price_zero_falha': 0,
                'f5d7_fiscal_setup_ok': 0,
                'f5d7_fiscal_setup_skip': 0,
                'f5d7_fiscal_setup_falha': 0,
            },
        }

        # Validar perfil ANTES (anti-poison se chamado em loop)
        try:
            _validar_perfil(perfil)
        except (NotImplementedError, ValueError) as e:
            out['status'] = 'FALHA_PERFIL_INVALIDO'
            out['erro'] = str(e)
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Real-run exige confirmar explicito (helpers escrevem no Odoo)
        if not dry_run and not confirmar:
            out['status'] = 'BLOQUEADO_SEM_CONFIRMAR'
            out['erro'] = (
                'Real-run exige confirmar=True para escrever no Odoo '
                '(G029 payment_provider + G007 price + G034 fiscal_setup '
                'modificam account.move).'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if dry_run:
            out['status'] = 'DRY_RUN_OK'
            out['observacao'] = (
                f'Real-run aplicaria G029 (payment_provider=38) + G007 '
                f'(corrige price_unit=0) + G034 (DEV_* fiscal_position) '
                f'na invoice {invoice_id} (perfil={perfil!r}).'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # REAL-RUN: aplicar sub-etapas (cada uma try/except individual — D6)
        # Re-fetch ajuste fresco
        from app.odoo.models import AjusteEstoqueInventario  # lazy
        primeiro = safe_session_get(AjusteEstoqueInventario, ajuste_id_primeiro)
        if primeiro is None:
            out['status'] = 'FALHA_AJUSTE_NAO_EXISTE'
            out['erro'] = (
                f'Ajuste id={ajuste_id_primeiro} nao encontrado no DB local '
                f'(re-fetch retornou None — pode ter sumido pos-commit).'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # F5d.5 — G029 payment_provider
        try:
            ok_f5d5 = garantir_payment_provider(
                self.odoo, invoice_id, primeiro,
                perfil=perfil, executado_por=usuario,
            )
            if ok_f5d5:
                out['sub_etapas']['f5d5_payment_provider_ok'] = 1
            else:
                out['sub_etapas']['f5d5_payment_provider_falha'] = 1
        except NotImplementedError:
            raise  # perfil errado — propaga
        except Exception as e:
            logger.warning(f'F5d.5 payment_provider invoice {invoice_id}: {e}')
            out['sub_etapas']['f5d5_payment_provider_falha'] = 1

        # F5d.6 — G007 price zero
        try:
            n_corrigidas = corrigir_price_zero_em_invoice(
                self.odoo, invoice_id, primeiro,
                perfil=perfil, executado_por=usuario,
            )
            out['sub_etapas']['f5d6_price_zero_corrigidas'] = int(
                n_corrigidas or 0
            )
        except NotImplementedError:
            raise
        except Exception as e:
            logger.warning(f'F5d.6 price_zero invoice {invoice_id}: {e}')
            out['sub_etapas']['f5d6_price_zero_falha'] = 1

        # F5d.7 — G034 fiscal_setup (apenas DEV_*)
        try:
            ok_f5d7 = garantir_fiscal_setup(
                self.odoo, invoice_id, primeiro,
                perfil=perfil, executado_por=usuario,
            )
            if ok_f5d7:
                # Helper retorna True tambem para acao nao-DEV (skip).
                # Heuristica: se acao NAO eh DEV_*, contar como skip; senao OK.
                if primeiro.acao_decidida and primeiro.acao_decidida.startswith('DEV_'):
                    out['sub_etapas']['f5d7_fiscal_setup_ok'] = 1
                else:
                    out['sub_etapas']['f5d7_fiscal_setup_skip'] = 1
            else:
                out['sub_etapas']['f5d7_fiscal_setup_falha'] = 1
        except NotImplementedError:
            raise
        except Exception as e:
            logger.warning(f'F5d.7 fiscal_setup invoice {invoice_id}: {e}')
            out['sub_etapas']['f5d7_fiscal_setup_falha'] = 1

        # commit sub-etapas — falha NAO derruba (D6)
        commit_resilient()

        # Status agregado
        falhas = (
            out['sub_etapas']['f5d5_payment_provider_falha']
            + out['sub_etapas']['f5d6_price_zero_falha']
            + out['sub_etapas']['f5d7_fiscal_setup_falha']
        )
        if falhas == 0:
            out['status'] = 'OK'
        else:
            out['status'] = 'OK_PARCIAL'

        out['tempo_ms'] = int((time.time() - t0) * 1000)
        _registrar_auditoria(
            ajuste_id=ajuste_id_primeiro, ciclo=ciclo,
            fase='F5d_INVOICE_GERADA', acao='validar_invoice_pos_robo',
            status=out['status'],
            payload={'perfil': perfil},
            resposta={'sub_etapas': out['sub_etapas']},
            odoo_id=invoice_id, modelo_odoo='account.move',
            tempo_ms=out['tempo_ms'], executado_por=usuario,
        )
        return out

    # ============================================================
    # ATOMO 5 — transmitir_sefaz (IRREVERSIVEL)
    # ============================================================

    def transmitir_sefaz(
        self,
        *,
        invoice_id: int,
        ajuste_ids: List[int],
        ciclo: str = '',
        max_tentativas: int = F5E_PLAYWRIGHT_MAX_TENTATIVAS_DEFAULT,
        intervalo_retry: int = F5E_PLAYWRIGHT_INTERVALO_RETRY_DEFAULT_S,
        dry_run: bool = True,
        confirmar_sefaz: bool = False,
        usuario: str = 'faturamento_svc',
    ) -> Dict[str, Any]:
        """Transmite NF-e via Playwright SEFAZ (IRREVERSIVEL).

        Patterns codificados (preservados do orchestrator v17 ETAPA D):
          - D7: HARD_FAIL_CONFIG_ERRORS aborta com status=FALHA_CONFIG
          - D8.3: idempotencia persistente — skip se QUALQUER ajuste ja
                  em FASE_F5e_OK ou status=EXECUTADO (cobre crash mid-loop)
          - D9: re-fetch ajustes via safe_session_get apos Playwright
          - F6 v15c: safe_session_get anti-DetachedInstanceError
          - MED C-1: registra situacao_nf != 'autorizado' em erro_msg
          - MED C-2: persiste cstat+xmotivo em falha
          - G016 (D14): commit_resilient antes E depois
          - CRITICAL-1 v17: commit POS-Playwright FALHA = NAO conta sucesso
                            (estado em memoria NAO persistido; SEFAZ JA
                            autorizada — operador investiga manualmente)

        D-OPS-2b §7.5.2 (NAO corrigido aqui): F5e propaga chave_nfe para
        TODOS ajustes do mesmo invoice. Fix definitivo (filtrar por
        account.move.line) eh TODO pos-canary.

        Args:
            invoice_id: account.move.id em F5d_INVOICE_GERADA.
            ajuste_ids: lista de ajustes da mesma invoice (>=1).
            ciclo: identificador do ciclo (auditoria).
            max_tentativas: tentativas Playwright/NF (default 15).
            intervalo_retry: segundos entre tentativas (default 120).
            dry_run: True (default) NAO chama Playwright.
            confirmar_sefaz: 2-nivel — exigido para real-run (irreversivel).
            usuario: identificador para auditoria.

        Returns:
            dict com:
              status: 'DRY_RUN_OK' | 'OK' | 'IDEMPOTENT_SKIP' |
                      'BLOQUEADO_SEM_CONFIRMAR_SEFAZ' | 'FALHA_CONFIG' |
                      'FALHA_AJUSTES_VAZIOS' | 'FALHA_COMMIT_PRE' |
                      'FALHA_COMMIT_POS_SEFAZ_OK' | 'FALHA'
              invoice_id: input
              chave_nfe: chave SEFAZ (em OK ou IDEMPOTENT_SKIP)
              situacao_nf: 'autorizado' | outro (registrar erro_msg se nao)
              tempo_ms: tempo total da operacao
        """
        t0 = time.time()

        out: Dict[str, Any] = {
            'atomo': 'transmitir_sefaz',
            'invoice_id': invoice_id,
            'ajuste_ids': ajuste_ids,
            'ciclo': ciclo,
            'dry_run': dry_run,
            'confirmar_sefaz': confirmar_sefaz,
            'chave_nfe': None,
            'situacao_nf': None,
        }

        if not ajuste_ids:
            out['status'] = 'FALHA_AJUSTES_VAZIOS'
            out['erro'] = (
                'ajuste_ids vazio — atomo precisa de >=1 ajuste para auditoria '
                'e propagacao de chave_nfe (D-OPS-2b).'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # D18: real-run exige --confirmar-sefaz (2 niveis — IRREVERSIVEL)
        if not dry_run and not confirmar_sefaz:
            out['status'] = 'BLOQUEADO_SEM_CONFIRMAR_SEFAZ'
            out['erro'] = (
                'transmitir_sefaz e IRREVERSIVEL. Real-run exige '
                'confirmar_sefaz=True (NF autorizada SEFAZ so cancela '
                'via processo formal 24h + sem uso + declaracao).'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if dry_run:
            out['status'] = 'DRY_RUN_OK'
            out['observacao'] = (
                f'Real-run chamaria transmitir_nfe_via_playwright(invoice='
                f'{invoice_id}, max_tentativas={max_tentativas}, '
                f'intervalo_retry={intervalo_retry}s). Tempo estimado: '
                f'5-10min/NF. {len(ajuste_ids)} ajustes seriam atualizados '
                f'(propagacao chave_nfe D-OPS-2b).'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # ============================================================
        # REAL-RUN: Playwright SEFAZ (IRREVERSIVEL)
        # ============================================================

        # Lazy import Playwright service (NAO MEXER — modulo externo)
        from app.recebimento.services.playwright_nfe_transmissao import (
            transmitir_nfe_via_playwright,
        )
        from app.odoo.models import AjusteEstoqueInventario  # lazy

        # G016 Opcao A: commit antes da NF longa (libera conexao DB)
        if not commit_resilient():
            logger.warning(
                f'F5e commit pre-Playwright invoice {invoice_id} falhou '
                f'(SSL). Continuando — risco de DB desincronizar.'
            )

        # F6 v15c: re-fetch ajustes
        ajustes_fresh: List = []
        for aid in ajuste_ids:
            af = safe_session_get(AjusteEstoqueInventario, aid)
            if af is not None:
                ajustes_fresh.append(af)

        if not ajustes_fresh:
            out['status'] = 'FALHA'
            out['erro'] = (
                f'Re-fetch ajustes vazio para invoice {invoice_id} '
                f'(todos sumiram?). Skipping Playwright.'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # D8.3 (persistencia): skip se QUALQUER ajuste ja em F5e_OK
        ja_processados = [
            a for a in ajustes_fresh
            if a.fase_pipeline == 'F5e_SEFAZ_OK' or a.status == 'EXECUTADO'
        ]
        if ja_processados:
            chave_existente = next(
                (a.chave_nfe for a in ja_processados if a.chave_nfe), None,
            )
            out['status'] = 'IDEMPOTENT_SKIP'
            out['chave_nfe'] = chave_existente
            out['observacao'] = (
                f'Idempotencia D8.3: invoice {invoice_id} ja transmitida '
                f'({len(ja_processados)}/{len(ajustes_fresh)} ajustes em '
                f'F5e_OK ou EXECUTADO).'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        inicio_inv = time.time()

        # Transmitir Playwright (5-10min/NF)
        try:
            resultado = transmitir_nfe_via_playwright(
                invoice_id, self.odoo, logger,
                max_tentativas=max_tentativas,
                intervalo_retry=intervalo_retry,
            )
        except Exception as e:
            tempo_ms_inv = int((time.time() - inicio_inv) * 1000)
            logger.error(
                f'F5e excecao invoice {invoice_id}: {e}', exc_info=True,
            )
            # F6 v15c: re-fetch pos-Playwright
            ajustes_post: List = []
            for aid in ajuste_ids:
                af = safe_session_get(AjusteEstoqueInventario, aid)
                if af is not None:
                    ajustes_post.append(af)
            for aj in ajustes_post:
                aj.fase_pipeline = 'F5e_FALHA'
                aj.erro_msg = (f'F5e excecao: {e}')[:500]
                _registrar_auditoria(
                    ajuste_id=aj.id, ciclo=ciclo, fase='F5e',
                    acao='transmitir_sefaz', modelo_odoo='account.move',
                    status='EXCECAO', odoo_id=invoice_id,
                    erro_msg=str(e)[:500], tempo_ms=tempo_ms_inv,
                    executado_por=usuario,
                )
            commit_resilient()
            out['status'] = 'FALHA'
            out['erro'] = f'excecao: {str(e)[:300]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        tempo_ms_inv = int((time.time() - inicio_inv) * 1000)

        # D7 (HARD_FAIL_CONFIG): batch abortado se erro de config
        if (
            not resultado.get('sucesso')
            and resultado.get('tentativas') == 0
            and resultado.get('erro') in HARD_FAIL_CONFIG_ERRORS
        ):
            erro = resultado['erro']
            ajustes_post: List = []
            for aid in ajuste_ids:
                af = safe_session_get(AjusteEstoqueInventario, aid)
                if af is not None:
                    ajustes_post.append(af)
            for aj in ajustes_post:
                aj.fase_pipeline = 'F5e_FALHA'
                aj.erro_msg = (f'Config invalida: {erro}')[:500]
                _registrar_auditoria(
                    ajuste_id=aj.id, ciclo=ciclo, fase='F5e',
                    acao='transmitir_sefaz', modelo_odoo='account.move',
                    status='FALHA_CONFIG', odoo_id=invoice_id,
                    erro_msg=erro, tempo_ms=tempo_ms_inv,
                    resposta=resultado, executado_por=usuario,
                )
            commit_resilient()
            out['status'] = 'FALHA_CONFIG'
            out['erro'] = erro
            out['erro_config'] = erro
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # D9: re-fetch ajustes apos Playwright (sessao pode ter expirado)
        ajustes_post: List = []
        for aid in ajuste_ids:
            af = safe_session_get(AjusteEstoqueInventario, aid)
            if af is not None:
                ajustes_post.append(af)
        if not ajustes_post:
            out['status'] = 'FALHA'
            out['erro'] = (
                f'Re-fetch pos-Playwright vazio para invoice {invoice_id} '
                f'— resultado NAO persistido (ajustes sumiram).'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if resultado.get('sucesso'):
            chave_nfe = resultado.get('chave_nf')
            situacao = resultado.get('situacao_nf')
            out['chave_nfe'] = chave_nfe
            out['situacao_nf'] = situacao

            # Marcar TODOS os ajustes da mesma invoice como F5e_SEFAZ_OK
            # NOTA D-OPS-2b §7.5.2: propaga chave para TODOS ajustes do invoice.
            for aj in ajustes_post:
                aj.fase_pipeline = 'F5e_SEFAZ_OK'
                aj.chave_nfe = chave_nfe
                aj.status = 'EXECUTADO'
                # MED C-1: registrar excecao_autorizado para audit
                if situacao and situacao != 'autorizado':
                    aj.erro_msg = (
                        f'{situacao} tentativa='
                        f'{resultado.get("tentativa", "?")}'
                    )[:500]
                _registrar_auditoria(
                    ajuste_id=aj.id, ciclo=ciclo, fase='F5e',
                    acao='transmitir_sefaz', modelo_odoo='account.move',
                    status='SUCESSO', odoo_id=invoice_id,
                    resposta=resultado, tempo_ms=tempo_ms_inv,
                    executado_por=usuario,
                )

            # CRITICAL-1 v17: commit POS-Playwright FALHA = NAO contar sucesso
            if not commit_resilient():
                logger.error(
                    f'F5e CRITICAL: commit POS-Playwright FALHOU para '
                    f'invoice {invoice_id} (SEFAZ AUTORIZADA com '
                    f'chave={chave_nfe}). Estado em memoria NAO persistido. '
                    f'Operador DEVE checar DB e marcar fase_pipeline='
                    f'F5e_SEFAZ_OK manualmente. NAO re-executar SEFAZ '
                    f'para esta invoice.'
                )
                out['status'] = 'FALHA_COMMIT_POS_SEFAZ_OK'
                out['erro'] = (
                    f'SEFAZ autorizou (chave={chave_nfe}) mas commit DB '
                    f'falhou. Operador investiga manualmente.'
                )
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out

            out['status'] = 'OK'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            logger.info(
                f'F5e invoice {invoice_id} -> SEFAZ OK '
                f'(chave={chave_nfe}, situacao={situacao}, '
                f'{len(ajustes_post)} ajustes)'
            )
            return out

        # Sucesso=False (mas nao HARD_FAIL_CONFIG)
        erro = resultado.get('erro', 'erro_desconhecido')
        ultimo = resultado.get('ultimo_estado') or {}
        # MED C-2: persistir cstat+xmotivo (campo acionavel)
        erro_msg_completo = (
            f"SEFAZ falhou: {erro} "
            f"(tentativas={resultado.get('tentativas', '?')}, "
            f"cstat={ultimo.get('cstat')}, "
            f"xmotivo={ultimo.get('xmotivo')})"
        )[:500]
        for aj in ajustes_post:
            aj.fase_pipeline = 'F5e_FALHA'
            aj.erro_msg = erro_msg_completo
            _registrar_auditoria(
                ajuste_id=aj.id, ciclo=ciclo, fase='F5e',
                acao='transmitir_sefaz', modelo_odoo='account.move',
                status='FALHA', odoo_id=invoice_id,
                resposta=resultado, erro_msg=erro_msg_completo,
                tempo_ms=tempo_ms_inv, executado_por=usuario,
            )
        commit_resilient()
        out['status'] = 'FALHA'
        out['erro'] = erro
        out['situacao_nf'] = ultimo.get('cstat')
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        logger.error(
            f'F5e invoice {invoice_id} falhou: {erro} '
            f'(cstat={ultimo.get("cstat")}, '
            f'xmotivo={ultimo.get("xmotivo")})'
        )
        return out
