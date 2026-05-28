"""faturamento_pipeline.py — Orchestrator C3 macro Skill 8 `faturando-odoo` (v17).

Executa pipeline completo A-F de faturamento inter-company de inventario:

- ETAPA A: transferencias internas pre-faturamento (Skill 2 v2 — v16)
- ETAPA B: F5a criar pickings + F5b validar + F5c liberar (via Skill 5 v15a)
- ETAPA C: F5d aguardar invoices CIEL IT + sub-etapas .5/.6/.7 (v16)
- ETAPA D: F5e transmitir SEFAZ Playwright (v17 — IRREVERSIVEL)
- ETAPA E: RecebimentoLf X->FB (v17 — invoca RecebimentoLfOdooService externo)
- ETAPA F: picking entrada manual destino (DELEGADO Skill 5 v15a — v17)

v17 (esta versao): C11 (ETAPA D F5e SEFAZ) + C12 (ETAPA E RecLF) +
  C13 (ETAPA F atomo Skill 5). Todas etapas A-F implementadas.

REGRA INVIOLAVEL 0: ler `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md`
INTEIRO antes de modificar este arquivo. SEFAZ irreversivel.

PRINCIPIO ARQUITETURAL v15a:
  Toda operacao em stock.picking passa por StockPickingService (Skill 5).
  Orchestrator NUNCA chama `odoo.create('stock.picking')` direto.

Pattern reuso: `app/odoo/estoque/orchestrators/pre_etapa_executor.py` (Skill 6 v9).

Decisoes aplicadas:
  D5: SNAPSHOT meta antes de polling/Playwright (v16/v17)
  D7: HARD_FAIL_CONFIG_ERRORS aborta batch SEFAZ (v17)
  D8: idempotencia TRIPLA F5e (sem inv_id + batch + persistencia — v17)
  D9: re-fetch via safe_session_get apos Playwright (v17)
  D10: db.engine.dispose() profilatico antes/apos C+D (v16)
  D11: db.session.expire_all() + reload entre etapas
  D13: ETAPA A SEQUENCIAL (XML-RPC nao thread-safe Request-sent)
  D14: _commit_resilient versao MAIS FORTE (engine.dispose se SSL)
  D15: ETAPA A 100% DELEGAVEL para Skill 2 `transferindo-interno-odoo`
  D16: ETAPA B pipeline POR PICKING + sleep 5s entre chunks (G022)
  D17: ACAO_PARA_CFOP_ENTRADA 5xxx->1xxx (RecebimentoLfLote.cfop — v17)
  D18: dry_run=True default + --confirmar + --confirmar-sefaz (2 niveis)
  10.6: F5a/F5b/F5c via atomos Skill 5 (`criar_picking_inter_company`,
        `validar_picking_inter_company`, `liberar_faturamento`)
  10.5: PRE-FLIGHT via sub-skill C5 (subprocess `auditar_cadastro_inventario.py`)
  10.7 v17 (Rafael 2026-05-25): ETAPA E SEQUENCIAL + recovery --resume.
        Razao: RecebimentoLfOdoo NAO eh thread-safe (Redis state);
        G-RECLF-1 (50-100h/onda 100 invoices) aceito por idempotencia.

Gotchas codificados:
  G016: SSL — `_commit_resilient` proativo + `expire_all()+carregar_ajustes()`
  G022: sleep 5s entre chunks ETAPA B
  G023: company_id forcado em moves (via atomo Skill 5)
  G-ETB-COMPENSATORIO: qty_restante > 0 em PERDA_LF_FB cria novo
        AjusteEstoqueInventario PROPOSTO para ondas futuras
  G-ETB-G014: lote vencido on-the-fly via Skill 2 (v16)
  G-RECLF-2 (v17): aceita transfer_status='erro' como sucesso parcial
        (FB OK suficiente; FASE 6+7 podem falhar sem derrubar FB)
  G-RECLF-3: idempotencia via RecebimentoLf.odoo_lf_invoice_id (UK)
  G-RECLF-9 mitigado: Playwright SEFAZ NAO concorre (etapa-barreira macro
        garante D nao roda com E concorrente)

V1 STRICT ETAPA F (v17): APENAS INDUSTRIALIZACAO_FB_LF (LF=19 validado em
PROD via pickings 317306, 317316). DEV_FB_LF/TRANSFERIR_FB_CD: NotImplemented
ate' descoberta de PICKING_TYPE_ENTRADA_DESTINO_MANUAL para CD/FB.

Spec: app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import subprocess
import sys
import time
import uuid
from collections import defaultdict
from typing import Any, Dict, List, Optional, Tuple

from app.odoo.constants.ids_diversos import (
    CARRIER_NACOM,
    INCOTERM_CIF,
    PAYMENT_PROVIDER_SEM_PAGAMENTO,  # CR-F11 v15c: ref stub C (G029)
)
from app.odoo.constants.locations import COMPANY_LOCATIONS
from app.odoo.constants.operacoes_fiscais import (
    ACAO_PARA_CFOP_ENTRADA,  # CR-F8 v15c: ref stub E (D17)
    ACAO_PARA_DIRECAO,        # CR-F8 v15c: fonte unica de verdade
    ACOES_ENTRADA_FB,         # CR-F8 v15c: ref stub E
    ACOES_PICKING,            # CR-F8 v15c: derivada de ACAO_PARA_DIRECAO
    COMPANY_PARTNER_ID,
)
from app.odoo.constants.picking_types import (
    ACOES_ENTRADA_DESTINO_MANUAL,           # CR-F10 v15c: ref stub F
    COMPANY_LABEL_ENTRADA,                  # CR-F10 v15c: ref stub F
    LOCATION_DESTINO_POR_DIRECAO,
    LOCATION_ORIGEM_ENTRADA_INDUSTR,        # CR-F10 v15c: ref stub F (alias 26489)
    PICKING_TYPE_ENTRADA_DESTINO_MANUAL,    # CR-F10 v15c: ref stub F
    get_picking_type,
)
from app.odoo.estoque.scripts._commit_helpers import (
    commit_resilient as _commit_resilient_shared,  # CR-F9 v15c: helper consolidado
    safe_session_get,                              # CR-F6 v15c: re-fetch ORM
)
from app.odoo.estoque.scripts._invoice_helpers import (
    # CR-C10.1 v16 (Rafael 2026-05-25): helpers POS-invoice CIEL IT por PERFIL.
    # V1 cobre 'inventario-inter-company' apenas; perfis futuros raise.
    PERFIL_INVENTARIO_INTER_COMPANY,
    corrigir_price_zero_em_invoice,  # F5d.6 (G007)
    garantir_fiscal_setup,           # F5d.7 (G034 DEV_*)
    garantir_payment_provider,       # F5d.5 (G029)
)
from app.odoo.estoque.scripts.picking import StockPickingService
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


# ============================================================
# Constantes locais (v15b)
# ============================================================

CICLO_DEFAULT = 'INVENTARIO_2026_05'

# CR-F8 v15c CRITICAL: `ACAO_PARA_DIRECAO` e `ACOES_PICKING` agora vivem em
# `app/odoo/constants/operacoes_fiscais.py` (consolidado — Reviewer B conf 95).
# `inventario_pipeline_service.py` tambem importa daqui — fonte unica.
# Re-export aqui mantido por compat com testes que importam de orchestrator.
# (re-exports vem dos imports acima)

# Limite de cods por picking (script 09 L1136). Reduz over-reservation em
# lotes velhos pos-renomeacao (G022).
MAX_CODS_POR_PICKING = 30

# Sleep entre chunks ETAPA B (D16, script 09 L1136-1138 — G022 mitigation).
SLEEP_ENTRE_CHUNKS = 5.0

# Etapas validas (ordem fixa A->B->C->D->E->F).
ETAPAS_VALIDAS: Tuple[str, ...] = ('A', 'B', 'C', 'D', 'E', 'F')

# CR-C10.2 v16: ACOES_LOTE — acoes intra-empresa sem NF (ETAPA A).
# DISJUNTAS de ACOES_PICKING (ETAPA B) — ajustes RENOMEAR_LOTE/TRANSFERIR_LOTE
# NAO viram picking inter-company; transferem qty entre lotes intra-empresa
# via Skill 2 `transferir_quantidade_para_lote_v2`.
# Centralizar em `app/odoo/constants/operacoes_fiscais.py` em v17 (TODO).
ACOES_LOTE: frozenset = frozenset({'RENOMEAR_LOTE', 'TRANSFERIR_LOTE'})

# Sub-skill C5 PRE-FLIGHT — caminho do CLI do projeto.
# Resolvido relativo ao root via PROJECT_ROOT (cwd ou setado por env).
SUB_SKILL_C5_CLI = (
    '.claude/skills/auditando-cadastro-fiscal-odoo/scripts/'
    'auditar_cadastro_inventario.py'
)
SUB_SKILL_C5_TIMEOUT_S = 120  # 6 cods em v14b-ops levaram 987ms; bulk
#                              # ~150 cods estima <30s. Margem 4x.

# Estados de fase_pipeline finais por etapa.
FASE_F5a_OK = 'F5a_PICKING_OK'
FASE_F5b_OK = 'F5b_VALIDADO'
FASE_F5c_OK = 'F5c_LIBERADO'
FASE_F5a_FALHA = 'F5a_FALHA'
FASE_F5b_FALHA = 'F5b_FALHA'
FASE_F5c_FALHA = 'F5c_FALHA'

# v16 — ETAPA C F5d invoices
FASE_F5d_OK = 'F5d_INVOICE_GERADA'
FASE_F5d_TIMEOUT = 'F5d_TIMEOUT'

# Defaults polling ETAPA C (D5 pattern + service legado L948)
F5D_POLLING_TIMEOUT_S = 1800   # 30 min total
F5D_POLL_INTERVAL_S = 40       # entre check de cada picking pendente

# v17 — ETAPA D F5e SEFAZ Playwright
FASE_F5e_OK = 'F5e_SEFAZ_OK'
FASE_F5e_FALHA = 'F5e_FALHA'

# v17 — ETAPA F F5f entrada destino manual
FASE_F5f_OK = 'F5f_ENTRADA_OK'
FASE_F5f_FALHA = 'F5f_FALHA'

# v18 — Recovery `executar_pipeline_resume` defaults (substitui
# `fat_lf_resume.sh` 18 iters + `fat_lf_resume_entrada.sh` 30 iters E + 12 F).
RESUME_MAX_ITER_DEFAULT = 18
RESUME_TIMEOUT_ITER_S_DEFAULT = 900  # 15 min/iter (espelha shell)
RESUME_ETAPAS_VALIDAS: Tuple[str, ...] = ('B', 'C', 'D', 'E', 'F')

# v18 — fases terminais por etapa (ajuste sai do "pendente" da etapa quando
# alcanca uma fase >= terminal). Usado por `_contar_pendentes_por_etapa`.
# Ordem: nao-iniciado -> F5a_*/F5b_* (em B) -> F5c_LIBERADO (terminal B / pre C)
# -> F5d_INVOICE_GERADA (terminal C / pre D) -> F5e_SEFAZ_OK (terminal D / pre E,F)
# -> F5f_ENTRADA_OK (terminal F).
FASES_TERMINAIS_B: frozenset = frozenset({
    FASE_F5c_OK, FASE_F5d_OK, FASE_F5e_OK, FASE_F5f_OK,
})
FASES_PRE_B: frozenset = frozenset({
    None, 'TRANSF_OK', FASE_F5a_OK, FASE_F5a_FALHA, FASE_F5b_OK, FASE_F5b_FALHA, FASE_F5c_FALHA,
})

# v17 — HARD_FAIL_CONFIG_ERRORS (D7 do service legado L1110-1114).
# Estes erros + tentativas=0 ABORTAM o batch SEFAZ (operador deve intervir).
HARD_FAIL_CONFIG_ERRORS: frozenset = frozenset({
    'playwright_indisponivel',
    'odoo_password_ausente',
    'odoo_username_ausente',
})

# v17 — Playwright defaults (alinhados ao service legado L1101-1102 +
# RecebimentoLfOdooService PLAYWRIGHT_MAX_TENTATIVAS=15)
F5E_PLAYWRIGHT_MAX_TENTATIVAS = 15        # 15 tentativas x 120s = ~30min/NF
F5E_PLAYWRIGHT_INTERVALO_RETRY_S = 120    # 2 min entre tentativas


# ============================================================
# Helpers de auditoria + commit resiliente
# ============================================================

# CR-F9 v15c: `_commit_resilient` consolidado em
# `app/odoo/estoque/scripts/_commit_helpers.py:commit_resilient` (helper
# compartilhado entre orchestrators). Re-alias local mantido para compat
# com call sites existentes. Reviewer B+D conf 80-85 — match SSL tightened
# (lista especifica em vez de `'connection'` BROAD).
_commit_resilient = _commit_resilient_shared


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
    """Registra operacao em operacao_odoo_auditoria (contexto faturamento).

    Lazy import de OperacaoOdooAuditoria para evitar circular em testes
    unitarios que mockam o orchestrator sem app_context.

    Padrao copiado de `pre_etapa_executor._registrar_auditoria` + extras
    para pipeline F5* (campos `picking_id`/`invoice_id` ate v17).
    """
    try:
        from app.odoo.models import OperacaoOdooAuditoria  # lazy
        external_id = (
            f'INV-{ciclo}-A{ajuste_id:06d}-{fase}-{uuid.uuid4().hex[:8]}'
        )
        # G-AUDIT-1 (NOVO v21+ FIX 2026-05-27): NUNCA passar `etapa=fase`.
        # Coluna `etapa` é INTEGER no modelo (`OperacaoOdooAuditoria.etapa = db.Column(db.Integer)`)
        # mas fase é string ('F5a_PICKING_OK', etc.). Passar string em INTEGER causa
        # `psycopg2.errors.InvalidTextRepresentation` que faz rollback cascateado.
        # Fonte correta da informação semântica de fase é `pipeline_etapa` (string),
        # já passado abaixo. `etapa_descricao` (string) também já carrega fase.
        # Incidente: 2026-05-27 pipeline REAL v21+ crashou em F5a depois de criar
        # picking órfão 321600 — ver memory [[g_audit_1_etapa_int_vs_string]] (v22+).
        OperacaoOdooAuditoria.registrar(
            external_id=external_id,
            tabela_origem='ajuste_estoque_inventario',
            registro_id=ajuste_id,
            acao=acao,
            modelo_odoo=modelo_odoo or 'stock.picking',
            etapa_descricao=f'{fase} {acao}',
            status=status,
            payload_json=payload,
            resposta_json=resposta,
            erro_msg=erro_msg,
            tempo_execucao_ms=tempo_ms,
            pipeline_etapa=fase,
            contexto_origem='faturamento_pipeline',
            contexto_ref=ciclo,
            executado_por=executado_por,
            odoo_id=odoo_id,
        )
    except Exception as e:
        logger.error(f'auditoria fase={fase} falhou: {e}', exc_info=True)


def _project_root() -> str:
    """Retorna root do projeto (worktree).

    Convencao: usa env `FRETE_PROJECT_ROOT` ou faz fallback a CWD. O orchestrator
    e' chamado de Python (entry-point ou pytest) — em ambos os contextos o CWD
    e' o worktree.

    Util tambem para localizar a sub-skill C5 (que depende de `.claude/skills/`
    presente).
    """
    return os.environ.get('FRETE_PROJECT_ROOT', os.getcwd())


def _pre_flight_via_subskill_c5(
    *,
    ciclo: str,
    timeout_s: int = SUB_SKILL_C5_TIMEOUT_S,
) -> Dict[str, Any]:
    """Invoca sub-skill `auditando-cadastro-fiscal-odoo` perfil 'inventario'.

    Pattern (decisao 10.5): subprocess delegada. Skill 8 nao implementa
    pre-flight diretamente — apenas invoca + parsea JSON. Se a sub-skill
    retornar `pode_faturar=False` (status_global=BLOQUEADO), orchestrator
    aborta com mensagem clara.

    Tradeoffs aceitos (R22 mitigation):
      - usa `sys.executable` (NAO 'python' do PATH) — funciona em venv.
      - env=os.environ.copy() — preserva DATABASE_URL+ODOO_* do caller.
      - captura stdout/stderr separados; parsea so stdout (JSON unico).
      - timeout=120s — bulk ~150 cods estimado <30s; margem 4x.

    Args:
        ciclo: identificador do ciclo de inventario.
        timeout_s: timeout do subprocess (default 120).

    Returns:
        dict com:
          status_global: PRE_FLIGHT_OK | PRE_FLIGHT_WARN | PRE_FLIGHT_BLOQUEADO
          pode_faturar: bool
          bloqueios: dict por categoria
          warnings: dict por categoria
          auditados: int
          tempo_ms: int
          stdout_raw: str (debug)
          stderr_raw: str (debug)
          exit_code: int

    Raises:
        FileNotFoundError: sub-skill nao instalada.
        subprocess.TimeoutExpired: timeout estourou (operador deve investigar).
    """
    cli_path = os.path.join(_project_root(), SUB_SKILL_C5_CLI)
    if not os.path.exists(cli_path):
        raise FileNotFoundError(
            f'Sub-skill C5 CLI nao encontrada: {cli_path!r}. '
            f'Verifique se `.claude/skills/auditando-cadastro-fiscal-odoo/` '
            f'esta presente no worktree.'
        )

    cmd = [
        sys.executable,
        cli_path,
        '--ciclo', ciclo,
    ]
    logger.info(
        f'PRE-FLIGHT C5: invocando subprocess `auditar_cadastro_inventario.py '
        f'--ciclo {ciclo!r}` (timeout={timeout_s}s)'
    )
    t0 = time.time()
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            env=os.environ.copy(),
            cwd=_project_root(),
        )
    except subprocess.TimeoutExpired as e:
        logger.error(
            f'PRE-FLIGHT C5: TIMEOUT apos {timeout_s}s. '
            f'Sub-skill nao retornou. Verificar conexao Odoo + tamanho ciclo.'
        )
        raise

    elapsed_ms = int((time.time() - t0) * 1000)
    stdout = proc.stdout or ''
    stderr = proc.stderr or ''

    # Tentar parsear JSON do stdout. Sub-skill emite varios logs em stderr +
    # JSON unico no stdout (regra v7 / CR-Pattern do projeto).
    try:
        payload = json.loads(stdout)
    except json.JSONDecodeError as e:
        logger.error(
            f'PRE-FLIGHT C5: stdout nao e JSON valido. '
            f'exit={proc.returncode} '
            f'stdout[:500]={stdout[:500]!r} '
            f'stderr[:500]={stderr[:500]!r}'
        )
        return {
            'status_global': 'PRE_FLIGHT_ERRO_PARSE',
            'pode_faturar': False,
            'erro_parse': str(e),
            'exit_code': proc.returncode,
            'stdout_raw': stdout,
            'stderr_raw': stderr,
            'tempo_ms': elapsed_ms,
        }

    payload['exit_code'] = proc.returncode
    payload['tempo_ms'] = payload.get('tempo_ms') or elapsed_ms
    # CR-F6 (Skill 6 lessons): manter stderr p/ debug em falhas obscuras.
    payload['stderr_raw'] = stderr[:2000] if stderr else ''
    logger.info(
        f'PRE-FLIGHT C5: status={payload.get("status_global")} '
        f'pode_faturar={payload.get("pode_faturar")} '
        f'auditados={payload.get("auditados")} '
        f'tempo_ms={payload["tempo_ms"]}'
    )
    return payload


# ============================================================
# Helpers de resolucao (premissas de cada ajuste)
# ============================================================

def _resolver_picking_metadata(
    acao_decidida: str,
) -> Dict[str, Any]:
    """Resolve metadados de picking inter-company a partir de acao_decidida.

    Args:
        acao_decidida: AjusteEstoqueInventario.acao_decidida (ex.
            'PERDA_LF_FB', 'INDUSTRIALIZACAO_FB_LF', ...).

    Returns:
        dict com:
          tipo_op: str (transf-filial/industrializacao/perda/dev-industrializacao)
          company_origem_id: int
          company_destino_id: int
          picking_type_id: int
          partner_id: int (do destino — fiscal_position resolver)
          location_origem_id: int (estoque interno da origem)
          location_destino_id: int (location virtual de transito)

    Raises:
        ValueError: se acao_decidida nao mapeada em ACAO_PARA_DIRECAO.
    """
    if acao_decidida not in ACAO_PARA_DIRECAO:
        raise ValueError(
            f'acao_decidida={acao_decidida!r} nao mapeada em ACAO_PARA_DIRECAO. '
            f'Validas: {sorted(ACAO_PARA_DIRECAO.keys())}'
        )
    tipo_op, co, cd = ACAO_PARA_DIRECAO[acao_decidida]

    picking_type_id = get_picking_type(co, tipo_op)
    partner_id = COMPANY_PARTNER_ID[cd]
    location_origem_id = COMPANY_LOCATIONS[co]
    # location_destino_id segue LOCATION_DESTINO_POR_DIRECAO (virtuais).
    key = (co, tipo_op)
    if key not in LOCATION_DESTINO_POR_DIRECAO:
        raise ValueError(
            f'LOCATION_DESTINO_POR_DIRECAO sem entrada para (co={co}, '
            f'tipo_op={tipo_op!r}). Validas: '
            f'{sorted(LOCATION_DESTINO_POR_DIRECAO.keys())}'
        )
    location_destino_id = LOCATION_DESTINO_POR_DIRECAO[key]

    return {
        'tipo_op': tipo_op,
        'company_origem_id': co,
        'company_destino_id': cd,
        'picking_type_id': picking_type_id,
        'partner_id': partner_id,
        'location_origem_id': location_origem_id,
        'location_destino_id': location_destino_id,
    }


def _carregar_ajustes(
    *,
    ciclo: str,
    company_origem_id: Optional[int] = None,
    acoes: Optional[List[str]] = None,
    fases_pipeline: Optional[List[Optional[str]]] = None,
    status_filter: Optional[List[str]] = None,
    cod_produto: Optional[str] = None,
    limite: Optional[int] = None,
) -> List:
    """Carrega ajustes do DB local apos `expire_all()` (D11 — barreira entre etapas).

    Pattern script 09 `carregar_ajustes` (L416-469) — re-load da sessao apos
    cada etapa, garantindo `fase_pipeline` atualizada.

    Code-review v15b CR-C1 (CRITICAL): adicionado `status_filter` (default
    `['PROPOSTO', 'APROVADO']`) para excluir CANCELADO/EXECUTADO/FALHA de
    re-processamento. Ajustes CANCELADO entrariam no pipeline sem isso,
    gerando picking SEFAZ-irreversivel para registros invalidos.

    Args:
        ciclo: identificador do ciclo (ex 'INVENTARIO_2026_05').
        company_origem_id: filtro por company emissora.
        acoes: filtro por acao_decidida (default: ACOES_PICKING — 8 acoes).
        fases_pipeline: filtro por fase_pipeline (default: None = qualquer).
            Aceita None na lista para casar fase NULL (ainda nao iniciado).
        status_filter: filtro por status (default: ['PROPOSTO', 'APROVADO']).
            Pass `None` para nao filtrar (uso interno/admin).
        cod_produto: filtro por 1 produto especifico (smoke/canary).
        limite: limita N primeiros ajustes (sub-piloto).

    Returns:
        Lista de AjusteEstoqueInventario.
    """
    from app import db  # lazy
    from app.odoo.models import AjusteEstoqueInventario  # lazy

    db.session.expire_all()  # D11 — invalida ORM cache

    q = AjusteEstoqueInventario.query.filter_by(ciclo=ciclo)

    # CR-C1 v15b: filtro de status (default exclui CANCELADO/EXECUTADO/FALHA).
    if status_filter is None:
        status_filter = ['PROPOSTO', 'APROVADO']
    if status_filter:
        q = q.filter(AjusteEstoqueInventario.status.in_(status_filter))

    if company_origem_id is not None:
        # ACAO_PARA_DIRECAO[acao][1] == company_origem. Filtro por acoes da
        # company emissora.
        acoes_co = [
            a for a, (_, co, _) in ACAO_PARA_DIRECAO.items()
            if co == company_origem_id
        ]
        if acoes:
            # CR-M1 v15b: se intersecao vazia, retornar [] (NAO remover filtro).
            acoes = [a for a in acoes if a in acoes_co]
            if not acoes:
                return []
        else:
            acoes = acoes_co
    if acoes is None:
        acoes = sorted(ACOES_PICKING)
    if acoes:
        q = q.filter(AjusteEstoqueInventario.acao_decidida.in_(acoes))
    if fases_pipeline is not None:
        # Suporta None na lista (fase NULL = ainda nao iniciado).
        fases_concretas = [f for f in fases_pipeline if f is not None]
        casa_null = None in fases_pipeline
        if fases_concretas and casa_null:
            q = q.filter(
                (AjusteEstoqueInventario.fase_pipeline.in_(fases_concretas))
                | (AjusteEstoqueInventario.fase_pipeline.is_(None))
            )
        elif fases_concretas:
            q = q.filter(
                AjusteEstoqueInventario.fase_pipeline.in_(fases_concretas)
            )
        elif casa_null:
            q = q.filter(AjusteEstoqueInventario.fase_pipeline.is_(None))
    if cod_produto:
        q = q.filter_by(cod_produto=cod_produto)
    q = q.order_by(AjusteEstoqueInventario.id)
    if limite:
        q = q.limit(limite)
    return q.all()


def _agrupar_em_chunks(
    ajustes: List, max_cods: int = MAX_CODS_POR_PICKING,
) -> List[List]:
    """Divide lista de ajustes em chunks por unique cod_produto.

    Cada chunk contem ate `max_cods` cods distintos. Ajustes do mesmo cod
    ficam SEMPRE no mesmo chunk (1 produto = 1 linha no picking).

    Pattern script 09 L900-1100 — pickings de ate 30 cods por chunk
    reduzem over-reservation (G022).

    Args:
        ajustes: lista de AjusteEstoqueInventario.
        max_cods: limite de cods por chunk (default 30).

    Returns:
        Lista de chunks (cada chunk = lista de ajustes).
    """
    if not ajustes:
        return []
    # Agrupar por cod (mantem ordem de insercao no dict para reprodutibilidade)
    por_cod: Dict[str, List] = defaultdict(list)
    for a in ajustes:
        por_cod[a.cod_produto].append(a)
    cods_ordenados = list(por_cod.keys())

    chunks: List[List] = []
    for i in range(0, len(cods_ordenados), max_cods):
        cods_chunk = cods_ordenados[i:i + max_cods]
        ajustes_chunk: List = []
        for cod in cods_chunk:
            ajustes_chunk.extend(por_cod[cod])
        chunks.append(ajustes_chunk)
    return chunks


def _agrupar_por_direcao(ajustes: List) -> Dict[str, List]:
    """Agrupa ajustes por `acao_decidida` (chave full direction).

    CR-C2 v15b CRITICAL: era `(co, tipo_op)` — INCORRETO porque
    `DEV_LF_FB` (co=5, cd=1) e `DEV_LF_CD` (co=5, cd=4) compartilham
    `(5, 'dev-industrializacao')` mas tem `partner_id` distintos. Misturar
    no mesmo chunk geraria picking com partner errado (fiscalmente invalido
    — SEFAZ irreversivel).

    Cada `acao_decidida` mapeia para 1 tupla (tipo_op, co, cd) unica em
    `ACAO_PARA_DIRECAO` -> agrupamento por acao garante 1 chunk = 1
    `partner_id` + 1 `picking_type` + 1 `location_destino`.

    Pattern script 09 — cada grupo gera N pickings (1 por chunk de ate 30 cods).

    Returns:
        Dict {acao_decidida: [ajustes...]}.
    """
    out: Dict[str, List] = defaultdict(list)
    for a in ajustes:
        if a.acao_decidida not in ACAO_PARA_DIRECAO:
            logger.warning(
                f'_agrupar_por_direcao: ajuste {a.id} acao_decidida='
                f'{a.acao_decidida!r} sem entrada — pulando.'
            )
            continue
        out[a.acao_decidida].append(a)
    return dict(out)


# ============================================================
# Classe principal: FaturamentoPipelineExecutor
# ============================================================

class FaturamentoPipelineExecutor:
    """Orquestrador C3 macro de faturamento inter-company (Skill 8 v15b).

    Composicao:
      - StockPickingService (Skill 5 v15a) — 3 atomos inter-company:
          * criar_picking_inter_company (F5a)
          * validar_picking_inter_company (F5b)
          * liberar_faturamento (F5c — atomo legacy ja existente)
      - StockInternalTransferService (Skill 2) — ETAPA A (delegado)
      - Sub-skill `auditando-cadastro-fiscal-odoo` (C5 v14b) — PRE-FLIGHT
        invocada via subprocess

    Etapas v15b implementadas: A, B (F5a + F5b + F5c).
    Etapas v16+ (stubs): C (F5d), D (F5e), E (RecLF), F (entrada manual).
    """

    def __init__(
        self,
        odoo=None,
        picking_svc: Optional[StockPickingService] = None,
    ):
        """Construtor.

        Args:
            odoo: conexao XML-RPC. Default: get_odoo_connection().
            picking_svc: StockPickingService injetavel (test-friendly).
                Default: novo StockPickingService(odoo=self.odoo).
        """
        self.odoo = odoo or get_odoo_connection()
        self.picking_svc = picking_svc or StockPickingService(odoo=self.odoo)

    # ========================================================
    # PRE-FLIGHT (delega sub-skill C5)
    # ========================================================

    def pre_flight(
        self, ciclo: str, *, timeout_s: int = SUB_SKILL_C5_TIMEOUT_S,
    ) -> Dict[str, Any]:
        """Invoca sub-skill `auditando-cadastro-fiscal-odoo` --ciclo X.

        Wrapper publico para testes. Delega para helper de modulo.
        """
        return _pre_flight_via_subskill_c5(ciclo=ciclo, timeout_s=timeout_s)

    # ========================================================
    # ETAPA A (DELEGADO Skill 2)
    # ========================================================

    def executar_etapa_a(
        self,
        *,
        ciclo: str,
        company_origem_id: Optional[int] = None,
        dry_run: bool = True,
        usuario: str = 'faturamento_pipeline',
        cod_produto: Optional[str] = None,
        limite: Optional[int] = None,  # v16: aceita limite para smoke
        permitir_etapa_a_noop_real: bool = False,  # DEPRECATED v16 — compat
    ) -> Dict[str, Any]:
        """ETAPA A v16: transferencias intra-empresa SEM NF (RENOMEAR/TRANSFERIR_LOTE).

        Filtra ajustes com `acao_decidida in ACOES_LOTE` = {RENOMEAR_LOTE,
        TRANSFERIR_LOTE}. ESCOPO DISJUNTO de ACOES_PICKING (ETAPA B).

        Implementacao v16 (CR-C10.2 / CR-H3 v15b TODO):
          - Filtra ACOES_LOTE + fase NULL ou TRANSF_PENDENTE (idempotente)
          - Para cada ajuste: invoca Skill 2 v2 `transferir_quantidade_para_lote_v2`
          - SEQUENCIAL (D13 — XML-RPC nao thread-safe Request-sent)
          - Marca fase TRANSF_OK ou TRANSF_FALHA
          - external_id_operacao populado (F12 pattern v15c)
          - Auditoria por ajuste

        Substitui:
          - v15b NOOP guard que marcava TUDO como TRANSF_OK (perigoso —
            incluia ACOES_PICKING que NAO sao transferencias).
          - v15c `raise NotImplementedError` guard.

        Compat flag `permitir_etapa_a_noop_real=True`:
          - v16: ainda aceito mas emite DeprecationWarning. Marca apenas
            ajustes ACOES_LOTE como TRANSF_OK sem chamar Skill 2 (uso de
            operador convicto que lote ja' casa).
          - v17 (planejado): removido.

        Args:
            ciclo: identificador do ciclo.
            company_origem_id: filtro por company emissora.
            dry_run: True (default) simula; False executa real.
            usuario: identificador para auditoria.
            cod_produto: smoke/canary.
            permitir_etapa_a_noop_real: DEPRECATED v16 — marca TRANSF_OK
                sem chamar Skill 2. Sera removido em v17.

        Returns:
            dict com status + contadores (ajustes_total, ajustes_transferidos,
            ajustes_skip_pid, ajustes_falha, ...).
        """
        t0 = time.time()
        # CR-C10.2 v16: filtrar ACOES_LOTE (escopo disjunto de ACOES_PICKING).
        ajustes = _carregar_ajustes(
            ciclo=ciclo,
            company_origem_id=company_origem_id,
            acoes=sorted(ACOES_LOTE),  # so' RENOMEAR_LOTE + TRANSFERIR_LOTE
            fases_pipeline=[None, 'TRANSF_PENDENTE'],
            cod_produto=cod_produto,
            limite=limite,  # v16 smoke/canary
        )
        out: Dict[str, Any] = {
            'etapa': 'A',
            'ciclo': ciclo,
            'company_origem_id': company_origem_id,
            'dry_run': dry_run,
            'ajustes_total': len(ajustes),
            'ajustes_transferidos': 0,
            'ajustes_skip_ja_ok': 0,
            'ajustes_skip_pid_ausente': 0,
            'ajustes_skip_sem_lote_destino': 0,
            'ajustes_skip_qty_zero': 0,
            'ajustes_falha': [],
        }
        if not ajustes:
            out['status'] = 'SKIP_NENHUM_AJUSTE'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        if dry_run:
            # Em dry-run, NAO chama Skill 2. So' reporta planejamento.
            out['status'] = 'DRY_RUN_OK_ETAPA_A'
            out['observacao'] = (
                f'v16 dry-run: {len(ajustes)} ajustes ACOES_LOTE planejados '
                f'para transferencia intra-empresa via Skill 2 '
                f'`transferir_quantidade_para_lote_v2`. Real-run faria '
                f'1 RPC stock.lot resolver + 1 Skill 2 v2 por ajuste.'
            )
            out['ajustes_planejados'] = [
                {
                    'id': a.id,
                    'acao': a.acao_decidida,
                    'cod_produto': a.cod_produto,
                    'lote_origem': a.lote_origem,
                    'lote_destino': a.lote_destino,
                    'qtd_inventario': float(a.qtd_inventario or 0),
                    'company_id': a.company_id,
                }
                for a in ajustes[:10]  # primeiros 10 para preview
            ]
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # ============================================================
        # REAL-RUN: invoca Skill 2 v2 por ajuste (SEQUENCIAL D13)
        # ============================================================

        # Compat DEPRECATED v15c flag — manter por seguranca durante migracao.
        if permitir_etapa_a_noop_real:
            logger.warning(
                'permitir_etapa_a_noop_real=True DEPRECATED v16 — sera '
                'removido em v17. Marca TRANSF_OK sem chamar Skill 2 '
                '(uso de operador convicto que lote ja casa com quants).'
            )
            for a in ajustes:
                a.fase_pipeline = 'TRANSF_OK'
            if not _commit_resilient():
                out['status'] = 'FALHA_COMMIT_TRANSF_OK_NOOP'
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out
            out['status'] = 'EXECUTADO_ETAPA_A_NOOP_DEPRECATED'
            out['ajustes_atualizados'] = len(ajustes)
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # v16: implementacao real via Skill 2 v2.
        # Lazy import — evita circular em testes.
        from app.odoo.estoque.scripts.transfer import (  # noqa: PLC0415
            StockInternalTransferService,
        )
        from app.odoo.services.stock_lot_service import (  # noqa: PLC0415
            StockLotService,
        )

        transfer_svc = StockInternalTransferService(odoo=self.odoo)
        lot_svc = StockLotService(odoo=self.odoo)

        # Pre-snapshot dos ajustes (D1 pattern — anti-DetachedInstance).
        # Usa `ciclo` parametro (NAO a.ciclo) — consistente em todos snapshots
        # mesmo se DB retornar valor inconsistente.
        ajuste_index: Dict[int, Any] = {a.id: a for a in ajustes}
        snapshots = [
            {
                'id': a.id,
                'ciclo': ciclo,  # parametro, nao a.ciclo
                'cod_produto': a.cod_produto,
                'lote_origem': (a.lote_origem or '').strip() or None,
                'lote_destino': (a.lote_destino or '').strip(),
                'company_id': a.company_id,
                'qtd_inventario': float(a.qtd_inventario or 0),
                'fase_atual': a.fase_pipeline,
                'acao': a.acao_decidida,
            }
            for a in ajustes
        ]

        # Pre-resolver product_id por cod_produto (cache, 1 batch read)
        cods_distintos = sorted({s['cod_produto'] for s in snapshots})
        prod_cache = self._resolver_pids_em_batch(cods_distintos)

        # Iterar SEQUENCIAL (D13)
        for snap in snapshots:
            t_snap = time.time()
            # Idempotencia: skip ja em TRANSF_OK
            if snap['fase_atual'] == 'TRANSF_OK':
                out['ajustes_skip_ja_ok'] += 1
                continue

            pid = prod_cache.get(snap['cod_produto'])
            if not pid:
                out['ajustes_skip_pid_ausente'] += 1
                continue

            if not snap['lote_destino']:
                out['ajustes_skip_sem_lote_destino'] += 1
                # Marcar fase TRANSF_FALHA + erro_msg
                aj = ajuste_index[snap['id']]
                aj.fase_pipeline = 'TRANSF_FALHA'
                aj.erro_msg = 'ETAPA A: sem lote_destino no ajuste'
                _commit_resilient()
                continue

            qty = snap['qtd_inventario']
            if qty <= 0:
                out['ajustes_skip_qty_zero'] += 1
                continue

            # Resolver lot_id_origem (Skill 2 v2 aceita None se sem lote)
            lot_id_origem: Optional[int] = None
            if snap['lote_origem']:
                try:
                    lot_id_origem = lot_svc.buscar_por_nome(
                        snap['lote_origem'], pid, snap['company_id'],
                    )
                except Exception as e:
                    logger.warning(
                        f'ETAPA A ajuste {snap["id"]} buscar lote '
                        f'{snap["lote_origem"]!r} falhou: {e}. '
                        f'Tentando sem lote origem (Skill 2 v2 trata None).'
                    )
                    lot_id_origem = None

            # Invocar Skill 2 v2 `transferir_quantidade_para_lote_v2`
            try:
                result = transfer_svc.transferir_quantidade_para_lote_v2(
                    product_id=pid,
                    company_id=snap['company_id'],
                    location_id=COMPANY_LOCATIONS[snap['company_id']],
                    qty=qty,
                    lot_id_origem=lot_id_origem,
                    nome_lote_destino=snap['lote_destino'],
                    dry_run=False,
                )
                tempo_ms_snap = int((time.time() - t_snap) * 1000)

                # F12 v15c: external_id_operacao para rastreabilidade
                external_id_a = (
                    f'INV-{snap["ciclo"]}-A{snap["id"]:06d}-TRANSF_OK-'
                    f'{uuid.uuid4().hex[:8]}'
                )
                aj = ajuste_index[snap['id']]
                aj.fase_pipeline = 'TRANSF_OK'
                aj.external_id_operacao = external_id_a
                _registrar_auditoria(
                    ajuste_id=snap['id'], ciclo=snap['ciclo'],
                    fase='TRANSF_OK',
                    acao='transferir_quantidade_para_lote_v2',
                    modelo_odoo='stock.quant',
                    status='SUCESSO',
                    payload={
                        'product_id': pid,
                        'company_id': snap['company_id'],
                        'qty': qty,
                        'lot_id_origem': lot_id_origem,
                        'lote_destino': snap['lote_destino'],
                        'lote_origem': snap['lote_origem'],
                    },
                    resposta={
                        'lote_destino_nome': result.get('lote_destino_nome'),
                        'lote_destino_criado_agora': result.get(
                            'lote_destino_criado_agora'
                        ),
                    },
                    tempo_ms=tempo_ms_snap, executado_por=usuario,
                )
                _commit_resilient()
                out['ajustes_transferidos'] += 1

            except Exception as e:
                msg = str(e)[:500]
                logger.error(
                    f'ETAPA A ajuste {snap["id"]} Skill 2 falhou: {msg}',
                    exc_info=True,
                )
                aj = ajuste_index[snap['id']]
                aj.fase_pipeline = 'TRANSF_FALHA'
                aj.erro_msg = msg
                _registrar_auditoria(
                    ajuste_id=snap['id'], ciclo=snap['ciclo'],
                    fase='TRANSF_FALHA',
                    acao='transferir_quantidade_para_lote_v2',
                    modelo_odoo='stock.quant',
                    status='FALHA', erro_msg=msg,
                    executado_por=usuario,
                )
                _commit_resilient()
                out['ajustes_falha'].append({
                    'ajuste_id': snap['id'],
                    'cod_produto': snap['cod_produto'],
                    'erro': msg,
                })

        n_falhas = len(out['ajustes_falha'])
        n_ok = out['ajustes_transferidos']
        if n_falhas == 0:
            out['status'] = 'EXECUTADO_ETAPA_A'
        elif n_ok > 0:
            out['status'] = 'EXECUTADO_PARCIAL_ETAPA_A'
        else:
            out['status'] = 'FALHA_TOTAL_ETAPA_A'

        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    # ========================================================
    # ETAPA B (F5a + F5b + F5c via atomos Skill 5 v15a)
    # ========================================================

    def executar_etapa_b(
        self,
        *,
        ciclo: str,
        company_origem_id: Optional[int] = None,
        dry_run: bool = True,
        usuario: str = 'faturamento_pipeline',
        cod_produto: Optional[str] = None,
        limite: Optional[int] = None,
        sleep_entre_chunks: float = SLEEP_ENTRE_CHUNKS,
    ) -> Dict[str, Any]:
        """ETAPA B: F5a criar pickings + F5b validar + F5c liberar (chunk-serial).

        Pattern (D16 — sub-nuance MICRO):
          - Agrupa ajustes por (company_origem, tipo_op)
          - Para cada grupo: chunkar por ate `MAX_CODS_POR_PICKING` cods
          - Para cada chunk: F5a -> F5b -> F5c -> sleep 5s -> proximo
          - Resolve picking_type/partner/locations via _resolver_picking_metadata
          - Invoca atomos Skill 5 v15a (D-OPS-3 codificado intra-atomo)
          - G-ETB-COMPENSATORIO em PERDA_LF_FB quando qty_restante > 0 (v15b min)

        NAO implementado em v15b (TODO v16):
          - G-ETB-G014 lote vencido on-the-fly (Skill 2 chamada inline)
            -> assume ajustes com lote_origem valido (nao vencido)
          - Paralelizacao ajustes intra-picking (Semaphore=5)
            -> v15b roda intra-picking sequencial (codigo mais simples; perf
               OK ate ~30 cods/picking, ~5-10s/picking)

        Args:
            ciclo: identificador do ciclo.
            company_origem_id: filtro por company emissora.
            dry_run: True (default) simula; False executa real.
            usuario: identificador para auditoria.
            cod_produto: smoke/canary.
            limite: limita N primeiros ajustes (sub-piloto).
            sleep_entre_chunks: pausa entre criar/validar/liberar de pickings
                distintos (G022 — default 5s).

        Returns:
            dict com status + contadores + lista de pickings.
        """
        t0 = time.time()
        # Carrega ajustes pendentes de ETAPA B (fase NULL ou TRANSF_OK).
        ajustes = _carregar_ajustes(
            ciclo=ciclo,
            company_origem_id=company_origem_id,
            fases_pipeline=[None, 'TRANSF_OK'],
            cod_produto=cod_produto,
            limite=limite,
        )
        out: Dict[str, Any] = {
            'etapa': 'B',
            'ciclo': ciclo,
            'company_origem_id': company_origem_id,
            'dry_run': dry_run,
            'ajustes_total': len(ajustes),
            'pickings_planejados': [],
            'pickings_criados': [],
            'pickings_validados': [],
            'pickings_liberados': [],
            'compensatorios_criados': [],
            'falhas': [],
        }
        if not ajustes:
            out['status'] = 'SKIP_NENHUM_AJUSTE'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # CR-C2 v15b: agrupar por acao_decidida (full direction) — preserva
        # (co, cd) unico por chunk = picking com partner_id correto.
        por_acao = _agrupar_por_direcao(ajustes)
        out['grupos_direcao'] = {
            acao: len(ajs) for acao, ajs in por_acao.items()
        }

        # CR-H1 v15b: tracker global de chunks ja executados para sleep G022
        # cobrir tambem TRANSICOES entre grupos (no script 09 isso esta na
        # ETAPA B inteira; aqui replicamos com flag).
        chunk_executado = False

        # Para cada grupo: chunkar + iterar
        for acao_decidida, ajustes_grupo in por_acao.items():
            chunks = _agrupar_em_chunks(ajustes_grupo)
            logger.info(
                f'ETAPA B grupo acao={acao_decidida!r}: '
                f'{len(ajustes_grupo)} ajustes em {len(chunks)} chunks'
            )
            for idx_chunk, ajustes_chunk in enumerate(chunks, 1):
                # CR-H1 v15b: sleep antes de TODO chunk (exceto o primeiro
                # absoluto) — boundary entre grupos tambem dorme (G022).
                if chunk_executado and not dry_run and sleep_entre_chunks > 0:
                    logger.info(
                        f'G022 sleep {sleep_entre_chunks}s antes do chunk '
                        f'{idx_chunk}/{len(chunks)} (acao={acao_decidida!r})'
                    )
                    time.sleep(sleep_entre_chunks)

                resultado_chunk = self._processar_chunk_etapa_b(
                    ajustes_chunk=ajustes_chunk,
                    acao_decidida_referencia=acao_decidida,
                    dry_run=dry_run,
                    usuario=usuario,
                    ciclo=ciclo,
                )
                chunk_executado = True
                # Agregar resultados
                if resultado_chunk.get('picking_planejado'):
                    out['pickings_planejados'].append(
                        resultado_chunk['picking_planejado']
                    )
                if resultado_chunk.get('picking_id_criado'):
                    out['pickings_criados'].append(
                        resultado_chunk['picking_id_criado']
                    )
                if resultado_chunk.get('picking_id_validado'):
                    out['pickings_validados'].append(
                        resultado_chunk['picking_id_validado']
                    )
                if resultado_chunk.get('picking_id_liberado'):
                    out['pickings_liberados'].append(
                        resultado_chunk['picking_id_liberado']
                    )
                for comp in resultado_chunk.get('compensatorios', []):
                    out['compensatorios_criados'].append(comp)
                for falha in resultado_chunk.get('falhas', []):
                    out['falhas'].append(falha)

        # CR-F15 v15c (Reviewer A H2 conf 82): distincao EXECUTADO_AUTO_CORRIGIDO.
        # Skill 6 v9 pattern — quando compensatorio resolveu pendencia G021
        # E zero falhas reais, status agregado e' AUTO_CORRIGIDO (NAO falha).
        # Relevante para `--resume` v18 distinguir auto-corrigido vs falhou.
        n_falhas = len(out['falhas'])
        n_compensatorios = len(out['compensatorios_criados'])
        n_liberados = len(out['pickings_liberados'])
        n_planejados = len(out['pickings_planejados'])

        if n_falhas > 0:
            if n_liberados > 0 or len(out['pickings_criados']) > 0:
                out['status'] = (
                    'DRY_RUN_PARCIAL' if dry_run else 'EXECUTADO_PARCIAL'
                )
            else:
                out['status'] = 'FALHA_TOTAL'
        elif n_compensatorios > 0 and not dry_run:
            # CR-F15: compensatorio criado SEM falha = AUTO_CORRIGIDO
            out['status'] = 'EXECUTADO_AUTO_CORRIGIDO'
        elif dry_run:
            out['status'] = (
                'DRY_RUN_OK_ETAPA_B' if n_planejados > 0
                else 'DRY_RUN_OK_NENHUM_PICKING'
            )
        else:
            out['status'] = 'EXECUTADO_ETAPA_B'

        # CR-F14 v15c (Reviewer A H1 conf 85): contadores estruturados
        # (proxy do Skill 6 v9 `_novos_contadores`) — facilita observabilidade
        # em bulk + permite `--resume` v18 distinguir _dry de real.
        out['contadores'] = {
            'pickings_planejados': n_planejados,
            'pickings_criados': len(out['pickings_criados']),
            'pickings_validados': len(out['pickings_validados']),
            'pickings_liberados': n_liberados,
            'compensatorios_criados': n_compensatorios,
            'falhas': n_falhas,
            'modo': 'dry-run' if dry_run else 'real',
        }

        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    # ========================================================
    # ETAPA B — processamento POR CHUNK (1 chunk = 1 picking)
    # ========================================================

    def _processar_chunk_etapa_b(
        self,
        *,
        ajustes_chunk: List,
        acao_decidida_referencia: str,
        dry_run: bool,
        usuario: str,
        ciclo: str,
    ) -> Dict[str, Any]:
        """Processa 1 chunk de ate 30 cods em pipeline F5a -> F5b -> F5c.

        Cada chunk gera 1 picking. Sub-nuance D16:
          - F5a: criar_picking_inter_company (Skill 5 v15a) — idempotente
            via origin (CR-F1 v15c — anti-duplicacao SEFAZ)
          - F5b: validar_picking_inter_company (Skill 5 v15a)
          - F5c: liberar_faturamento (Skill 5 — atomo legacy)
          - Caller (executar_etapa_b) faz sleep 5s entre chunks (G022)

        **G-ETB-G014 WARNING (CR-F3 v15c — Reviewer C conf 95)**:
        Esta funcao ASSUME que `a.lote_origem` esta valido (lote nao
        vencido) no Odoo. Em PROD com lote em `expiration_date < HOJE`:
        - `action_assign` no Odoo rejeitara reserva silenciosamente.
        - F5b retornara erro de quant insuficiente.
        - PRE-FLIGHT C5 v14b detecta lotes vencidos como WARNING (nao
          BLOQUEIO) — operador deve revisar.
        Implementacao completa do G014 (migracao on-the-fly via Skill 2)
        e' TODO v16. Ate la, lotes vencidos disparam warning no log.

        Args:
            ajustes_chunk: lista de AjusteEstoqueInventario do mesmo
                `acao_decidida` (CR-C2 v15b — agrupados por acao full).
            acao_decidida_referencia: acao do primeiro ajuste — usada para
                resolver metadata.
            dry_run: simula vs executa.
            usuario: para auditoria.
            ciclo: para auditoria.

        Returns:
            dict com chave por sub-etapa (picking_planejado / picking_id_criado /
            picking_id_validado / picking_id_liberado / compensatorios / falhas
            / ajustes_lote_potencialmente_vencido).
        """
        out_chunk: Dict[str, Any] = {
            'ajustes_ids': [a.id for a in ajustes_chunk],
            'compensatorios': [],
            'falhas': [],
            # CR-F3 v15c: rastreabilidade de lotes potencialmente vencidos
            # (G014 TODO v16). Operador pode cross-checar com PRE-FLIGHT C5.
            'ajustes_lote_potencialmente_vencido': [],
        }

        # Resolver metadata da direcao (picking_type + partner + locations)
        try:
            meta = _resolver_picking_metadata(acao_decidida_referencia)
        except ValueError as e:
            out_chunk['falhas'].append({
                'sub_etapa': 'resolve_meta',
                'erro': str(e),
                'ajustes_ids': out_chunk['ajustes_ids'],
            })
            return out_chunk

        # Montar linhas — 1 linha por ajuste do chunk.
        # Pattern script L850-870: agrupar por cod (1 linha por cod com qty
        # total). Em v15b min, 1 linha por ajuste (caso simples 1 ajuste/cod).
        # G023: lote_origem do ajuste vai como lot_name na linha.
        linhas: List[Dict[str, Any]] = []
        # Mapear pid <- cod_produto via Odoo (1 read em batch).
        cods_distintos = sorted({a.cod_produto for a in ajustes_chunk})
        cods_para_pid = self._resolver_pids_em_batch(cods_distintos)

        # CR-C10.3 v16: G014 pre-check lotes vencidos on-the-fly.
        # Detecta cods com livre_validos < demand E livre_vencidos > 0;
        # migra qty para lote novo INV-{cod}-{YYYYMMDD} via Skill 2 v2.
        # Pattern script 09 L795-917 — codificado intra-chunk para evitar
        # action_assign falhar silenciosamente no F5a (Odoo CIEL IT rejeita
        # reserva de lote vencido).
        g014_resultado = self._g014_pre_check_lotes_vencidos(
            ajustes_chunk=ajustes_chunk,
            cods_para_pid=cods_para_pid,
            location_origem_id=meta['location_origem_id'],
            dry_run=dry_run,
        )
        out_chunk['g014'] = g014_resultado
        lote_novo_por_cod = g014_resultado.get('lote_novo_por_cod', {})
        if lote_novo_por_cod:
            logger.info(
                f'G014: {len(lote_novo_por_cod)} cods com lote vencido '
                f'migrados para lote novo (dry_run={dry_run})'
            )

        # CR-FIX R1F2 v16 (HIGH 88): G014 partial failure handling.
        # Cods que tentaram migrar mas falharam ficam em g014.erros[]. Se
        # criar picking com lote_origem vencido, action_assign falha
        # silenciosamente no Odoo CIEL IT — F5b retorna erro de qty
        # insuficiente, mas root cause (G014 falhou) fica obscuro.
        # Solucao: filtrar cods com erros de G014 — adicionar a falhas
        # explicitas e marcar para SKIP do picking (operador investiga).
        # Aplica APENAS em real-run (em dry-run, planejamento eh OK).
        cods_g014_falhou: set = set()
        if not dry_run and g014_resultado.get('erros'):
            cods_g014_falhou = {e['cod'] for e in g014_resultado['erros']}
            for cod_err in cods_g014_falhou:
                ajustes_afetados = [
                    a.id for a in ajustes_chunk if a.cod_produto == cod_err
                ]
                out_chunk['falhas'].append({
                    'sub_etapa': 'G014_pre_check',
                    'erro': (
                        f'G014 falhou em cod={cod_err} — picking NAO criado '
                        f'(lote vencido nao migrado para lote novo). '
                        f'Operador deve investigar saldos manualmente.'
                    ),
                    'cod_produto': cod_err,
                    'ajustes_ids': ajustes_afetados,
                })

        ajustes_sem_pid: List[int] = []
        for a in ajustes_chunk:
            # CR-FIX R1F2 v16 (HIGH 88): pular cods cujo G014 falhou.
            # Ja' adicionados a out_chunk['falhas'] acima.
            if a.cod_produto in cods_g014_falhou:
                continue
            pid = cods_para_pid.get(a.cod_produto)
            if not pid:
                ajustes_sem_pid.append(a.id)
                continue
            qty = float(a.qtd_ajuste or a.qtd_inventario or 0)
            if qty <= 0:
                # G021 — sera filtrado pelo atomo Skill 5, mas log explicito
                logger.warning(
                    f'_processar_chunk_etapa_b: ajuste {a.id} qty<=0 '
                    f'({qty}) — pulando.'
                )
                continue
            # CR-C10.3 v16: se G014 migrou lote vencido, usar lote novo na linha
            lot_name_efetivo = lote_novo_por_cod.get(
                a.cod_produto, a.lote_origem or None,
            )
            linhas.append({
                'product_id': pid,
                'quantity': qty,
                'lot_name': lot_name_efetivo,
                'name': f'INV {a.cod_produto} ajuste={a.id}',
            })

        if ajustes_sem_pid:
            out_chunk['falhas'].append({
                'sub_etapa': 'resolve_pids',
                'erro': (
                    f'{len(ajustes_sem_pid)} ajustes sem product_id '
                    f'no Odoo (cod_produto nao cadastrado ou archived)'
                ),
                'ajustes_ids': ajustes_sem_pid,
            })
            # Continuar com os que tem pid (parcial OK)

        if not linhas:
            out_chunk['falhas'].append({
                'sub_etapa': 'montar_linhas',
                'erro': 'todas as linhas foram filtradas (qty<=0 ou sem pid)',
                'ajustes_ids': out_chunk['ajustes_ids'],
            })
            return out_chunk

        # Origin idempotente (rastreabilidade). Caller pode re-executar e
        # picking ja existente sera detectado upstream via fase_pipeline.
        origin = (
            f'INV-{ciclo}-SAIDA-{meta["tipo_op"][:8].upper()}-'
            f'{ajustes_chunk[0].id:06d}'
        )

        # Planejamento (sempre — base dry-run vs real)
        plano = {
            'origin': origin,
            'tipo_op': meta['tipo_op'],
            'company_origem_id': meta['company_origem_id'],
            'company_destino_id': meta['company_destino_id'],
            'picking_type_id': meta['picking_type_id'],
            'partner_id': meta['partner_id'],
            'location_origem_id': meta['location_origem_id'],
            'location_destino_id': meta['location_destino_id'],
            'n_linhas': len(linhas),
            'qty_total': sum(l['quantity'] for l in linhas),
            'ajustes_ids': out_chunk['ajustes_ids'],
        }
        out_chunk['picking_planejado'] = plano

        if dry_run:
            logger.info(
                f'F5a DRY-RUN: picking planejado origin={origin!r} '
                f'{meta["tipo_op"]} co={meta["company_origem_id"]}->'
                f'cd={meta["company_destino_id"]} '
                f'n_linhas={len(linhas)} qty_total={plano["qty_total"]}'
            )
            return out_chunk

        # F5a — criar picking via atomo Skill 5 v15a
        try:
            t_f5a = time.time()
            f5a_result = self.picking_svc.criar_picking_inter_company(
                company_origem_id=meta['company_origem_id'],
                company_destino_id=meta['company_destino_id'],
                location_origem_id=meta['location_origem_id'],
                location_destino_id=meta['location_destino_id'],
                linhas=linhas,
                picking_type_id=meta['picking_type_id'],
                partner_id=meta['partner_id'],
                origin=origin,
                incoterm_id=INCOTERM_CIF,
                carrier_id=CARRIER_NACOM,
            )
            picking_id = f5a_result['picking_id']
            f5a_status = f5a_result.get('status', 'CRIADO')  # CR-F1 v15c
            out_chunk['picking_id_criado'] = picking_id
            out_chunk['f5a_status'] = f5a_status  # CRIADO|IDEMPOTENT_DONE|IDEMPOTENT_OTHER
            tempo_f5a = int((time.time() - t_f5a) * 1000)

            # CR-F1 v15c: se atomo retornou IDEMPOTENT_DONE, picking ja foi
            # processado anteriormente (F5b+F5c) — pular F5b/F5c e marcar
            # ajustes como ja' finalizados (anti-loop em re-execucao).
            if f5a_status == 'IDEMPOTENT_DONE':
                logger.info(
                    f'F5a IDEMPOTENT_DONE picking_id={picking_id} '
                    f'origin={origin!r} — pulando F5b/F5c'
                )
                for a in ajustes_chunk:
                    a.picking_id_odoo = picking_id
                    # Forca fase F5c_OK porque picking ja' esta done
                    a.fase_pipeline = FASE_F5c_OK
                _commit_resilient()
                out_chunk['picking_id_validado'] = picking_id
                out_chunk['picking_id_liberado'] = picking_id
                return out_chunk

            # Atualizar fase + picking_id + external_id em todos ajustes do chunk
            # CR-F12 v15c: setar external_id_operacao para rastreabilidade
            # (campo do model ate v15b nunca era populado — Reviewer B conf 82)
            external_id_f5a = (
                f'INV-{ciclo}-A{ajustes_chunk[0].id:06d}-{FASE_F5a_OK}-'
                f'{uuid.uuid4().hex[:8]}'
            )
            for a in ajustes_chunk:
                a.picking_id_odoo = picking_id
                a.fase_pipeline = FASE_F5a_OK
                a.external_id_operacao = external_id_f5a  # CR-F12 v15c
                _registrar_auditoria(
                    ajuste_id=a.id, ciclo=ciclo, fase=FASE_F5a_OK,
                    acao='criar_picking_inter_company',
                    modelo_odoo='stock.picking',
                    status='SUCESSO', odoo_id=picking_id,
                    payload={
                        'origin': origin,
                        'f5a_status': f5a_status,  # CR-F1 v15c
                        'linhas_planejadas': len(
                            f5a_result.get('linhas_planejadas', [])
                        ),
                        'tracking_none_pids': f5a_result.get(
                            'tracking_none_pids', []
                        ),
                    },
                    tempo_ms=tempo_f5a, executado_por=usuario,
                )
            if not _commit_resilient():
                # F2 v15c (CRITICAL Reviewer D R-OPS-3 conf 82): ABORT chunk
                # se commit falha apos F5a OK. Continuar para F5b com DB local
                # dessincronizado (picking_id_odoo NULO mas Odoo com picking)
                # cria caos: F5b valida picking no Odoo mas erro_msg/fase_pipeline
                # nao persistem. Re-run depende de F1 idempotencia para nao duplicar.
                logger.error(
                    f'F5a commit FAILED apos picking_id={picking_id} criado. '
                    f'ABORT chunk para evitar cascata. Re-run usara F1 '
                    f'idempotencia via origin={origin!r}.'
                )
                out_chunk['falhas'].append({
                    'sub_etapa': 'F5a_commit',
                    'erro': (
                        f'commit_resilient falhou apos F5a OK (picking_id='
                        f'{picking_id} criado no Odoo, fase nao persistida). '
                        f'Re-run com F1 idempotencia detectara picking existente.'
                    ),
                    'picking_id': picking_id,
                    'ajustes_ids': out_chunk['ajustes_ids'],
                })
                return out_chunk
        except Exception as e:
            msg = str(e)[:500]
            logger.error(
                f'F5a falhou origin={origin!r}: {msg}', exc_info=True
            )
            # CR-F6 v15c (Reviewer D R-OPS-5 conf 85): re-fetch ajustes
            # apos excecao para anti-DetachedInstanceError. commit_resilient
            # pode ter feito session.close() em falha anterior.
            from app.odoo.models import AjusteEstoqueInventario  # lazy
            ajuste_ids = [a.id for a in ajustes_chunk]
            ajustes_fresh = []
            for aid in ajuste_ids:
                af = safe_session_get(AjusteEstoqueInventario, aid)
                if af is not None:
                    ajustes_fresh.append(af)
            for a in ajustes_fresh:
                a.fase_pipeline = FASE_F5a_FALHA
                a.erro_msg = msg
                _registrar_auditoria(
                    ajuste_id=a.id, ciclo=ciclo, fase=FASE_F5a_FALHA,
                    acao='criar_picking_inter_company',
                    modelo_odoo='stock.picking',
                    status='FALHA', erro_msg=msg, executado_por=usuario,
                )
            _commit_resilient()
            out_chunk['falhas'].append({
                'sub_etapa': 'F5a',
                'erro': msg,
                'ajustes_ids': out_chunk['ajustes_ids'],
            })
            return out_chunk

        # F5b — validar picking via atomo Skill 5 v15a
        try:
            t_f5b = time.time()
            # G023: passa linhas_esperadas (mesma estrutura do F5a — sem lot_id
            # pois lot_name sera resolvido pelo atomo).
            linhas_esperadas = [
                {
                    'product_id': l['product_id'],
                    'quantity': l['quantity'],
                    'lot_name': l.get('lot_name'),
                }
                for l in linhas
            ]
            f5b_result = self.picking_svc.validar_picking_inter_company(
                picking_id=picking_id,
                linhas_esperadas=linhas_esperadas,
                aplicar_peso_volumes=True,
            )
            out_chunk['picking_id_validado'] = picking_id
            tempo_f5b = int((time.time() - t_f5b) * 1000)
            pendencias = f5b_result.get('mls_pendencias', [])

            for a in ajustes_chunk:
                a.fase_pipeline = FASE_F5b_OK
                _registrar_auditoria(
                    ajuste_id=a.id, ciclo=ciclo, fase=FASE_F5b_OK,
                    acao='validar_picking_inter_company',
                    modelo_odoo='stock.picking',
                    status='SUCESSO', odoo_id=picking_id,
                    resposta={
                        'state_apos_validate': f5b_result.get(
                            'state_apos_validate'
                        ),
                        'g023_aplicado': f5b_result.get('g023_aplicado'),
                        'peso_volumes_aplicado': f5b_result.get(
                            'peso_volumes', {}
                        ).get('aplicado'),
                        'n_pendencias': len(pendencias),
                    },
                    tempo_ms=tempo_f5b, executado_por=usuario,
                )
            _commit_resilient()

            # G-ETB-COMPENSATORIO: pendencias G021 em PERDA_LF_FB criam
            # AjusteEstoqueInventario PROPOSTO para ondas futuras.
            if pendencias and acao_decidida_referencia == 'PERDA_LF_FB':
                compensatorios = self._criar_compensatorios_g_etb(
                    ajustes_chunk=ajustes_chunk,
                    pendencias=pendencias,
                    ciclo=ciclo,
                    cods_para_pid=cods_para_pid,
                    usuario=usuario,
                )
                out_chunk['compensatorios'].extend(compensatorios)
        except Exception as e:
            msg = str(e)[:500]
            logger.error(
                f'F5b falhou picking_id={picking_id}: {msg}', exc_info=True
            )
            for a in ajustes_chunk:
                a.fase_pipeline = FASE_F5b_FALHA
                a.erro_msg = msg
                _registrar_auditoria(
                    ajuste_id=a.id, ciclo=ciclo, fase=FASE_F5b_FALHA,
                    acao='validar_picking_inter_company',
                    modelo_odoo='stock.picking',
                    status='FALHA', odoo_id=picking_id,
                    erro_msg=msg, executado_por=usuario,
                )
            _commit_resilient()
            out_chunk['falhas'].append({
                'sub_etapa': 'F5b',
                'erro': msg,
                'picking_id': picking_id,
                'ajustes_ids': out_chunk['ajustes_ids'],
            })
            return out_chunk

        # F5c — liberar faturamento (dispara robo CIEL IT).
        # Atomo Skill 5 legacy `liberar_faturamento` ja' existe + valida
        # pre-cond state='done' internamente (G019/G020 fechada v3).
        try:
            t_f5c = time.time()
            self.picking_svc.liberar_faturamento(picking_id)
            out_chunk['picking_id_liberado'] = picking_id
            tempo_f5c = int((time.time() - t_f5c) * 1000)
            for a in ajustes_chunk:
                a.fase_pipeline = FASE_F5c_OK
                _registrar_auditoria(
                    ajuste_id=a.id, ciclo=ciclo, fase=FASE_F5c_OK,
                    acao='liberar_faturamento',
                    modelo_odoo='stock.picking',
                    status='SUCESSO', odoo_id=picking_id,
                    tempo_ms=tempo_f5c, executado_por=usuario,
                )
            _commit_resilient()
            logger.info(
                f'F5c picking {picking_id} liberado '
                f'({len(ajustes_chunk)} ajustes)'
            )
        except Exception as e:
            msg = str(e)[:500]
            logger.error(
                f'F5c falhou picking_id={picking_id}: {msg}', exc_info=True
            )
            for a in ajustes_chunk:
                a.fase_pipeline = FASE_F5c_FALHA
                a.erro_msg = msg
                _registrar_auditoria(
                    ajuste_id=a.id, ciclo=ciclo, fase=FASE_F5c_FALHA,
                    acao='liberar_faturamento',
                    modelo_odoo='stock.picking',
                    status='FALHA', odoo_id=picking_id,
                    erro_msg=msg, executado_por=usuario,
                )
            _commit_resilient()
            out_chunk['falhas'].append({
                'sub_etapa': 'F5c',
                'erro': msg,
                'picking_id': picking_id,
                'ajustes_ids': out_chunk['ajustes_ids'],
            })

        return out_chunk

    def _g014_pre_check_lotes_vencidos(
        self,
        *,
        ajustes_chunk: List,
        cods_para_pid: Dict[str, int],
        location_origem_id: int,
        dry_run: bool,
    ) -> Dict[str, Any]:
        """G014 v16: pre-check de lotes vencidos com migracao on-the-fly.

        Pattern script 09 L795-917 — antes de criar picking inter-company,
        verifica se os lotes_origem dos ajustes estao vencidos
        (`expiration_date < HOJE`). Lote vencido bloqueia `action_assign`
        silenciosamente no Odoo (CIEL IT rejeita reserva).

        Logica (por cod):
          1. READ stock.quant (product+company+location_origem, qty>0)
          2. READ stock.lot.expiration_date para lotes encontrados
          3. Separar quants_validos vs quants_vencidos
          4. Se `livre_validos < demand` E `livre_vencidos > 0`:
               qty_a_migrar = min(demand - livre_validos, livre_vencidos)
               nome_lote_novo = 'INV-{cod}-{YYYYMMDD}'  (idempotente por dia)
               Para cada quant vencido (FIFO ordem): Skill 2 v2 migra
               `take = min(livre_qv, qty_restante)` para lote novo
          5. Retorna `lote_novo_por_cod` para caller substituir `lot_name`
             nas linhas do picking (evita reservar lote vencido).

        Idempotencia: Skill 2 v2 internamente usa `resolver_lote_destino`
        com `criar_se_faltar=True` que faz search ANTES de criar (mesmo nome
        + mesmo produto = retorna existente). Re-rodar G014 no mesmo dia
        para o mesmo cod NAO duplica lote.

        Args:
            ajustes_chunk: lista de AjusteEstoqueInventario do chunk.
            cods_para_pid: cache cod -> product.id.
            location_origem_id: location stock.location.id de origem.
            dry_run: se True, planeja sem chamar Skill 2.

        Returns:
            dict {
                'lote_novo_por_cod': {cod: nome_lote_novo},
                'cods_com_lote_vencido': [cods detectados],
                'transferencias_executadas': [dicts com detalhes],
                'transferencias_planejadas': [dicts em dry-run],
                'erros': [{cod, erro}],
            }
        """
        # CR-FIX R1F4 v16 (HIGH 82): substituir datetime.utcnow() (banida pelo
        # hook ban_datetime_now.py) por agora_utc_naive (padrao do projeto —
        # ver REGRAS_TIMEZONE.md).
        from datetime import datetime as _dt  # lazy — para _dt.strptime em _is_vencido
        from datetime import timedelta as _td  # lazy
        from app.utils.timezone import agora_utc_naive  # lazy

        HOJE = agora_utc_naive()  # naive datetime (UTC), compativel com projeto
        EXP_NOVO_LOTE = (HOJE + _td(days=365)).strftime('%Y-%m-%d %H:%M:%S')
        HOJE_STR = HOJE.strftime('%Y%m%d')

        out: Dict[str, Any] = {
            'lote_novo_por_cod': {},
            'cods_com_lote_vencido': [],
            'transferencias_executadas': [],
            'transferencias_planejadas': [],
            'erros': [],
        }

        if not ajustes_chunk:
            return out

        # Agrupar demand_total e company por cod
        demand_por_cod: Dict[str, float] = defaultdict(float)
        company_por_cod: Dict[str, int] = {}
        for a in ajustes_chunk:
            demand_por_cod[a.cod_produto] += float(
                a.qtd_ajuste or a.qtd_inventario or 0
            )
            company_por_cod[a.cod_produto] = a.company_id

        # Lazy import — evita circular em testes
        transfer_svc = None  # so' instancia se for real-run com transferencia

        for cod, demand in demand_por_cod.items():
            if demand <= 0:
                continue
            pid = cods_para_pid.get(cod)
            if not pid:
                continue
            company_id = company_por_cod[cod]

            # READ quants origem
            try:
                quants = self.odoo.search_read(
                    'stock.quant',
                    [
                        ['product_id', '=', pid],
                        ['company_id', '=', company_id],
                        ['location_id', '=', location_origem_id],
                        ['quantity', '>', 0],
                    ],
                    ['id', 'lot_id', 'quantity', 'reserved_quantity'],
                )
            except Exception as e:
                logger.warning(
                    f'G014 read quants cod={cod} pid={pid} falhou: {e}'
                )
                out['erros'].append({'cod': cod, 'erro': str(e)[:200]})
                continue
            if not quants:
                continue

            # READ expiration_date dos lotes
            lot_ids = [q['lot_id'][0] for q in quants if q.get('lot_id')]
            lot_exp_cache: Dict[int, Optional[str]] = {}
            if lot_ids:
                try:
                    lots_info = self.odoo.read(
                        'stock.lot', lot_ids, ['expiration_date'],
                    )
                    lot_exp_cache = {
                        l['id']: l.get('expiration_date')
                        for l in lots_info
                    }
                except Exception as e:
                    logger.warning(
                        f'G014 read stock.lot.expiration_date cod={cod} '
                        f'lot_ids={lot_ids} falhou: {e}'
                    )
                    out['erros'].append({'cod': cod, 'erro': str(e)[:200]})
                    continue

            def _is_vencido(q):
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

            quants_validos = [q for q in quants if not _is_vencido(q)]
            quants_vencidos = [q for q in quants if _is_vencido(q)]
            livre_validos = sum(
                float(q['quantity']) - float(q.get('reserved_quantity') or 0)
                for q in quants_validos
            )
            livre_vencidos = sum(
                float(q['quantity']) - float(q.get('reserved_quantity') or 0)
                for q in quants_vencidos
            )

            if livre_validos >= demand or livre_vencidos <= 0:
                # Saldo livre suficiente ou nao ha vencidos para migrar
                continue

            out['cods_com_lote_vencido'].append(cod)
            qty_a_migrar = min(demand - livre_validos, livre_vencidos)
            nome_lote_novo = f'INV-{cod}-{HOJE_STR}'

            if dry_run:
                out['transferencias_planejadas'].append({
                    'cod': cod,
                    'pid': pid,
                    'qty_a_migrar': qty_a_migrar,
                    'demand_total': demand,
                    'livre_validos': livre_validos,
                    'livre_vencidos': livre_vencidos,
                    'nome_lote_novo': nome_lote_novo,
                    'lotes_vencidos_origem': [
                        q['lot_id'][1] if q.get('lot_id') else 'sem-lote'
                        for q in quants_vencidos
                    ],
                })
                out['lote_novo_por_cod'][cod] = nome_lote_novo
                continue

            # REAL: Skill 2 v2 por quant vencido
            if transfer_svc is None:
                from app.odoo.estoque.scripts.transfer import (  # noqa: PLC0415
                    StockInternalTransferService,
                )
                transfer_svc = StockInternalTransferService(odoo=self.odoo)

            qty_restante = qty_a_migrar
            migrou_algo_pra_cod = False
            for qv in quants_vencidos:
                if qty_restante <= 0.001:
                    break
                livre_qv = (
                    float(qv['quantity'])
                    - float(qv.get('reserved_quantity') or 0)
                )
                if livre_qv <= 0:
                    continue
                take = min(livre_qv, qty_restante)
                lot_id_origem = qv['lot_id'][0] if qv.get('lot_id') else None
                lote_origem_nome = (
                    qv['lot_id'][1] if qv.get('lot_id') else 'sem-lote'
                )
                try:
                    transfer_svc.transferir_quantidade_para_lote_v2(
                        product_id=pid,
                        company_id=company_id,
                        location_id=location_origem_id,
                        qty=take,
                        lot_id_origem=lot_id_origem,
                        nome_lote_destino=nome_lote_novo,
                        expiration_date_destino=EXP_NOVO_LOTE,
                        dry_run=False,
                    )
                    out['transferencias_executadas'].append({
                        'cod': cod,
                        'qty_migrada': take,
                        'lote_origem_nome': lote_origem_nome,
                        'lot_id_origem': lot_id_origem,
                        'lote_destino': nome_lote_novo,
                    })
                    qty_restante -= take
                    migrou_algo_pra_cod = True
                except Exception as e:
                    logger.error(
                        f'G014 transferir cod={cod} take={take} '
                        f'lote_origem={lote_origem_nome!r} -> '
                        f'{nome_lote_novo!r} falhou: {e}',
                        exc_info=True,
                    )
                    out['erros'].append({
                        'cod': cod,
                        'erro': f'transferir {take}: {str(e)[:200]}',
                    })

            if migrou_algo_pra_cod:
                out['lote_novo_por_cod'][cod] = nome_lote_novo

        return out

    def _resolver_pids_em_batch(self, cods: List[str]) -> Dict[str, int]:
        """Resolve cod_produto -> product.id em 1 read batch.

        Args:
            cods: lista de default_code (cod_produto local).

        Returns:
            dict {cod_produto: product_id}. Cods nao encontrados omitidos.
        """
        if not cods:
            return {}
        produtos = self.odoo.search_read(
            'product.product',
            [['default_code', 'in', cods]],
            ['id', 'default_code'],
        )
        return {
            p['default_code']: p['id']
            for p in produtos
            if p.get('default_code')
        }

    def _criar_compensatorios_g_etb(
        self,
        *,
        ajustes_chunk: List,
        pendencias: List[Dict[str, Any]],
        ciclo: str,
        cods_para_pid: Dict[str, int],
        usuario: str,
    ) -> List[Dict[str, Any]]:
        """G-ETB-COMPENSATORIO (script L994-1031): cria AjusteEstoqueInventario
        PROPOSTO para ondas futuras quando qty_restante > 0 em PERDA_LF_FB.

        Apenas aplicavel quando `acao_decidida='PERDA_LF_FB'` (tipo_op='perda'
        + company_origem=5/LF). Para outras acoes, retorna lista vazia.

        Args:
            ajustes_chunk: ajustes do chunk processado (PERDA_LF_FB ja garantido).
            pendencias: lista de MLs com qty_done < qty_demand (G021).
            ciclo: identificador do ciclo (compartilhado).
            cods_para_pid: cache cod -> pid.
            usuario: para auditoria.

        Returns:
            lista de dicts com cada compensatorio criado.
        """
        from app import db  # lazy
        from app.odoo.models import AjusteEstoqueInventario  # lazy

        # Mapear pid -> ajuste_origem (multipla referencia em caso de >1 ajuste
        # por cod no chunk — pegar o primeiro)
        pid_to_ajuste_origem: Dict[int, Any] = {}
        for a in ajustes_chunk:
            pid = cods_para_pid.get(a.cod_produto)
            if pid and pid not in pid_to_ajuste_origem:
                pid_to_ajuste_origem[pid] = a

        compensatorios_criados: List[Dict[str, Any]] = []
        for pend in pendencias:
            # Estrutura tipica de pendencia (G021): {product_id, qty_demand,
            # qty_done, ...} — caller (validar_picking_inter_company) deve
            # retornar isso. Se nao tiver chave product_id, pular.
            pid = pend.get('product_id')
            qty_restante = float(
                (pend.get('qty_demand') or 0) - (pend.get('qty_done') or 0)
            )
            if not pid or qty_restante <= 0:
                continue
            ajuste_origem = pid_to_ajuste_origem.get(pid)
            if not ajuste_origem:
                logger.warning(
                    f'G-ETB-COMPENSATORIO: pid={pid} qty_restante={qty_restante} '
                    f'sem ajuste_origem mapeado — pulando.'
                )
                continue

            # CR-H2 v15b: PRESERVAR `acao_decidida` do origem (compensatorio
            # mantem a mesma operacao fiscal — ex: PERDA_LF_FB que nao
            # transferiu N un re-tenta como PERDA_LF_FB em onda futura;
            # script 09 L994-1031 forcava 'INDUSTRIALIZACAO_FB_LF' o que
            # poderia ser fiscalmente invalido quando origem era de outra
            # company/direcao).
            try:
                novo = AjusteEstoqueInventario(
                    ciclo=ciclo,
                    cod_produto=ajuste_origem.cod_produto,
                    tipo_produto=ajuste_origem.tipo_produto,
                    company_id=ajuste_origem.company_id,
                    lote_inventariado=ajuste_origem.lote_inventariado,
                    lote_odoo=ajuste_origem.lote_odoo,
                    lote_origem=ajuste_origem.lote_origem,
                    lote_destino='MIGRAÇÃO',  # G031 — consolidador
                    qtd_inventario=qty_restante,
                    qtd_odoo=0,
                    qtd_ajuste=qty_restante,
                    custo_medio=ajuste_origem.custo_medio,
                    acao_decidida=ajuste_origem.acao_decidida,  # CR-H2 v15b
                    status='PROPOSTO',
                    erro_msg=(
                        f'[COMPENSATORIO_FALTA_ESTOQUE] '
                        f'origem_ajuste={ajuste_origem.id} '
                        f'qty_restante={qty_restante}'
                    ),
                    criado_por=usuario,
                )
                db.session.add(novo)
                db.session.flush()  # garantir id sem commit ainda
                compensatorios_criados.append({
                    'novo_ajuste_id': novo.id,
                    'origem_ajuste_id': ajuste_origem.id,
                    'cod_produto': ajuste_origem.cod_produto,
                    'qty_restante': qty_restante,
                })
                logger.info(
                    f'G-ETB-COMPENSATORIO: criado ajuste {novo.id} '
                    f'(origem {ajuste_origem.id}) cod={ajuste_origem.cod_produto} '
                    f'qty={qty_restante}'
                )
            except Exception as e:
                logger.error(
                    f'G-ETB-COMPENSATORIO: falha ao criar para '
                    f'origem={ajuste_origem.id} pid={pid}: {e}',
                    exc_info=True,
                )

        if compensatorios_criados:
            _commit_resilient()
        return compensatorios_criados

    # ========================================================
    # ETAPAS C/D/E/F (STUBS v15b — implementar em v16/v17)
    # ========================================================

    def executar_etapa_c(
        self,
        *,
        ciclo: str,
        company_origem_id: Optional[int] = None,
        dry_run: bool = True,
        usuario: str = 'faturamento_pipeline',
        cod_produto: Optional[str] = None,
        timeout_polling: int = F5D_POLLING_TIMEOUT_S,
        poll_interval: int = F5D_POLL_INTERVAL_S,
        perfil_invoice_helpers: str = PERFIL_INVENTARIO_INTER_COMPANY,
    ) -> Dict[str, Any]:
        """ETAPA C v16 — F5d aguardar invoices CIEL IT + sub-etapas .5/.6/.7.

        Polling longo (default 1800s, intervalo 40s) sobre `picking_svc.
        aguardar_invoice_do_robo(pid)` (Skill 5 atomo legacy). Para cada
        invoice resolvida, aplica sub-etapas:
          - F5d.5 (G029): `garantir_payment_provider` — payment_provider_id=38
          - F5d.6 (G007): `corrigir_price_zero_em_invoice` — fallback std_price
          - F5d.7 (G034): `garantir_fiscal_setup` — DEV_* FP/tipo_pedido

        Sub-etapas via `_invoice_helpers.py` com `perfil='inventario-inter-company'`
        V1 (CR-C10.1 v16 — Rafael). Outros perfis (venda-cliente futuro)
        raise NotImplementedError nos helpers (logica diferente).

        Patterns codificados (do service legado L945-1102):
          - D2: agrupa por picking_id_odoo (1 picking -> 1 invoice)
          - D5: SNAPSHOT meta antes do polling (sessao pode expirar)
          - D6: sub-etapas .5/.6/.7 em try/except — falha individual NAO derruba
          - F6 v15c: safe_session_get apos commit_resilient (anti-DetachedInstance)
          - F7 v15c: db.engine.dispose() antes/apos JA codificado no macro
          - F12 v15c: external_id_operacao populado em CADA fase F5d
          - G016: commit_resilient antes/depois do polling

        Idempotencia:
          - Filtra `fase_pipeline='F5c_LIBERADO'` + `picking_id_odoo NOT NULL`
            (ajustes ja em F5d_INVOICE_GERADA tem invoice_id_odoo e sao pulados)
          - Sub-etapas .5/.6/.7 sao internamente idempotentes (helpers checam estado)

        Args:
            ciclo: identificador do ciclo.
            company_origem_id: filtro por company emissora.
            dry_run: True (default) — em dry-run, NAO faz polling
                (retorna apenas planejamento: quantos pickings pendentes).
            usuario: identificador para auditoria.
            cod_produto: smoke/canary.
            timeout_polling: segundos totais ate desistir (default 1800).
            poll_interval: segundos entre checks de cada picking (default 40).
            perfil_invoice_helpers: V1 = 'inventario-inter-company'.
                Outros raise NotImplementedError nos helpers.

        Returns:
            dict com:
              status: DRY_RUN_OK_ETAPA_C | EXECUTADO_ETAPA_C |
                      EXECUTADO_PARCIAL_TIMEOUT | SKIP_NENHUM_AJUSTE | FALHA_*
              pickings_pendentes: lista de picking_ids esperados
              pickings_resolvidos: dict {pid: invoice_id}
              pickings_timeout: lista de pids que nao tiveram invoice no timeout
              sub_etapas: contadores por sub-etapa
        """
        from app import db  # lazy
        from app.odoo.models import AjusteEstoqueInventario  # lazy

        t0 = time.time()

        # Carregar ajustes em F5c_LIBERADO com picking_id_odoo (idempotencia:
        # ja em F5d_INVOICE_GERADA tem invoice_id_odoo populado e sao pulados).
        ajustes = _carregar_ajustes(
            ciclo=ciclo,
            company_origem_id=company_origem_id,
            fases_pipeline=[FASE_F5c_OK],
            cod_produto=cod_produto,
        )
        # Defensivo: filtrar ajustes sem picking_id_odoo (anomalia).
        ajustes_validos: List = [a for a in ajustes if a.picking_id_odoo]
        ajustes_sem_picking: List = [a for a in ajustes if not a.picking_id_odoo]
        if ajustes_sem_picking:
            logger.warning(
                f'ETAPA C: {len(ajustes_sem_picking)} ajustes em '
                f'F5c_LIBERADO SEM picking_id_odoo (anomalia) — pulando: '
                f'{[a.id for a in ajustes_sem_picking[:5]]}'
            )

        out: Dict[str, Any] = {
            'etapa': 'C',
            'ciclo': ciclo,
            'company_origem_id': company_origem_id,
            'dry_run': dry_run,
            'perfil_invoice_helpers': perfil_invoice_helpers,
            'ajustes_total': len(ajustes_validos),
            'ajustes_sem_picking': len(ajustes_sem_picking),
            'pickings_pendentes': [],
            'pickings_resolvidos': {},
            'pickings_timeout': [],
            'sub_etapas': {
                'f5d5_payment_provider_ok': 0,
                'f5d5_payment_provider_falha': 0,
                'f5d6_price_zero_corrigidas': 0,
                'f5d6_price_zero_falha': 0,
                'f5d7_fiscal_setup_ok': 0,
                'f5d7_fiscal_setup_skip': 0,  # acao nao DEV ou ja' correto
                'f5d7_fiscal_setup_falha': 0,
            },
        }

        if not ajustes_validos:
            out['status'] = 'SKIP_NENHUM_AJUSTE'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # D2: agrupar por picking_id_odoo (1 picking gera 1 invoice CIEL IT)
        ajustes_por_pid: Dict[int, List] = defaultdict(list)
        for a in ajustes_validos:
            ajustes_por_pid[a.picking_id_odoo].append(a)
        pickings_pendentes = list(ajustes_por_pid.keys())
        out['pickings_pendentes'] = sorted(pickings_pendentes)

        if dry_run:
            # Em dry-run, NAO faz polling. So' reporta planejamento.
            out['status'] = 'DRY_RUN_OK_ETAPA_C'
            out['observacao'] = (
                f'v16 dry-run: {len(pickings_pendentes)} pickings em '
                f'F5c_LIBERADO esperando invoice CIEL IT. Real-run faria '
                f'polling de {timeout_polling}s ({poll_interval}s interval) '
                f'+ sub-etapas .5/.6/.7 por invoice. Perfil sub-etapas: '
                f'{perfil_invoice_helpers!r}.'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # ============================================================
        # REAL-RUN: polling + sub-etapas
        # ============================================================

        # CR-FIX R1F1 v16 (CRITICAL 95): validar perfil ANTES do polling
        # para anti-poison do session. Se perfil errado, NotImplementedError
        # de sub-etapa F5d.5 quebraria todo polling com primeira invoice
        # resolvida (pickings restantes ficam F5c_LIBERADO permanentemente).
        from app.odoo.estoque.scripts._invoice_helpers import (  # noqa: PLC0415
            _validar_perfil,
        )
        try:
            _validar_perfil(perfil_invoice_helpers)
        except (NotImplementedError, ValueError) as e:
            out['status'] = 'FALHA_PERFIL_INVALIDO'
            out['erro'] = str(e)
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # D5: SNAPSHOT meta antes do polling (sessao pode expirar em
        # SSL idle timeout durante esperas de 30 min).
        ajustes_meta_por_pid: Dict[int, List[Dict[str, Any]]] = {
            pid: [
                {
                    'id': a.id,
                    'ciclo': a.ciclo,
                    'acao_decidida': a.acao_decidida,
                }
                for a in lista
            ]
            for pid, lista in ajustes_por_pid.items()
        }

        # G016 Opcao A: commit antes do polling longo
        if not _commit_resilient():
            logger.error(
                'F5d commit_resilient falhou ANTES do polling — abortando ETAPA C.'
            )
            out['status'] = 'FALHA_COMMIT_PRE_POLLING'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        pendentes_set = set(pickings_pendentes)
        resolved: Dict[int, int] = {}
        inicio_por_pid = {pid: time.time() for pid in pendentes_set}

        start_polling = time.time()
        while pendentes_set and (time.time() - start_polling) < timeout_polling:
            for pid in list(pendentes_set):
                # picking_svc.aguardar_invoice_do_robo retorna invoice_id
                # ou None. Usar poll_interval curto p/ nao bloquear.
                try:
                    invoice_id = self.picking_svc.aguardar_invoice_do_robo(
                        pid,
                        timeout=poll_interval,
                        poll_interval=poll_interval,
                    )
                except Exception as e:
                    logger.error(
                        f'F5d aguardar_invoice_do_robo({pid}) raise: {e}',
                        exc_info=True,
                    )
                    # NAO remover do pendentes_set — tentar de novo no proximo loop
                    continue

                if not invoice_id:
                    continue

                # Invoice resolvida — marcar fase F5d_INVOICE_GERADA em todos
                # ajustes do mesmo picking.
                resolved[pid] = invoice_id
                pendentes_set.discard(pid)

                tempo_ms_pid = int(
                    (time.time() - inicio_por_pid[pid]) * 1000
                )

                # F6 v15c: re-fetch ajustes via safe_session_get apos polling longo
                metas = ajustes_meta_por_pid[pid]
                ajustes_fresh: List = []
                for meta in metas:
                    af = safe_session_get(AjusteEstoqueInventario, meta['id'])
                    if af is not None:
                        ajustes_fresh.append(af)
                if not ajustes_fresh:
                    logger.error(
                        f'F5d: re-fetch ajustes vazio para picking {pid} '
                        f'(todos sumiram?). Skipping invoice {invoice_id}.'
                    )
                    continue

                # F12 v15c: external_id_operacao para rastreabilidade
                external_id_f5d = (
                    f'INV-{ciclo}-A{ajustes_fresh[0].id:06d}-'
                    f'{FASE_F5d_OK}-{uuid.uuid4().hex[:8]}'
                )
                for aj in ajustes_fresh:
                    aj.fase_pipeline = FASE_F5d_OK
                    aj.invoice_id_odoo = invoice_id
                    aj.external_id_operacao = external_id_f5d
                    _registrar_auditoria(
                        ajuste_id=aj.id, ciclo=ciclo, fase=FASE_F5d_OK,
                        acao='aguardar_invoice', modelo_odoo='account.move',
                        status='SUCESSO', odoo_id=invoice_id,
                        resposta={'invoice_id': invoice_id, 'picking_id': pid},
                        tempo_ms=tempo_ms_pid, executado_por=usuario,
                    )
                # CR-FIX R1F3 v16 (HIGH 85): se commit falha, NAO continuar
                # para sub-etapas (session sujo -> Odoo writes orfaos do DB
                # local). Resume v18 reprocessara este picking — invoice_id
                # Odoo ja' existe e sera detectado.
                if not _commit_resilient():
                    logger.error(
                        f'F5d commit apos invoice {invoice_id} '
                        f'(picking {pid}) FALHOU. PULA sub-etapas .5/.6/.7 '
                        f'(session sujo). fase_pipeline pode estar dessincronizada '
                        f'— resume v18 retentara.'
                    )
                    continue  # proxima iteracao do for pid

                logger.info(
                    f'F5d picking {pid} -> invoice {invoice_id} '
                    f'({len(ajustes_fresh)} ajustes)'
                )

                # ========================================================
                # SUB-ETAPAS F5d.5 / .6 / .7 (D6 — try/except individual)
                # ========================================================
                # Re-fetch novamente apos commit_resilient (defensive — pode ter
                # feito session.close() em SSL drop).
                primeiro = safe_session_get(
                    AjusteEstoqueInventario, ajustes_fresh[0].id,
                )
                if primeiro is None:
                    logger.error(
                        f'F5d sub-etapas pulam invoice {invoice_id} '
                        f'(ajuste {ajustes_fresh[0].id} sumiu pos-commit).'
                    )
                    continue

                # F5d.5 — G029 payment_provider
                try:
                    ok_f5d5 = garantir_payment_provider(
                        self.odoo, invoice_id, primeiro,
                        perfil=perfil_invoice_helpers,
                        executado_por=usuario,
                    )
                    if ok_f5d5:
                        out['sub_etapas']['f5d5_payment_provider_ok'] += 1
                    else:
                        out['sub_etapas']['f5d5_payment_provider_falha'] += 1
                except NotImplementedError:
                    raise  # perfil errado — propaga
                except Exception as e:
                    logger.warning(
                        f'F5d.5 payment_provider invoice {invoice_id}: {e}'
                    )
                    out['sub_etapas']['f5d5_payment_provider_falha'] += 1

                # F5d.6 — G007 price zero
                try:
                    n_corrigidas = corrigir_price_zero_em_invoice(
                        self.odoo, invoice_id, primeiro,
                        perfil=perfil_invoice_helpers,
                        executado_por=usuario,
                    )
                    out['sub_etapas']['f5d6_price_zero_corrigidas'] += int(
                        n_corrigidas or 0
                    )
                except NotImplementedError:
                    raise  # perfil errado — propaga
                except Exception as e:
                    logger.warning(
                        f'F5d.6 price_zero invoice {invoice_id}: {e}'
                    )
                    out['sub_etapas']['f5d6_price_zero_falha'] += 1

                # F5d.7 — G034 fiscal_setup (apenas DEV_*)
                try:
                    ok_f5d7 = garantir_fiscal_setup(
                        self.odoo, invoice_id, primeiro,
                        perfil=perfil_invoice_helpers,
                        executado_por=usuario,
                    )
                    if ok_f5d7:
                        # garantir_fiscal_setup retorna True tambem para acao
                        # nao-DEV (skip). Heuristica: se acao_decidida NAO eh
                        # DEV_*, contar como skip; senao OK.
                        if primeiro.acao_decidida and primeiro.acao_decidida.startswith('DEV_'):
                            out['sub_etapas']['f5d7_fiscal_setup_ok'] += 1
                        else:
                            out['sub_etapas']['f5d7_fiscal_setup_skip'] += 1
                    else:
                        out['sub_etapas']['f5d7_fiscal_setup_falha'] += 1
                except NotImplementedError:
                    raise  # perfil errado — propaga
                except Exception as e:
                    logger.warning(
                        f'F5d.7 fiscal_setup invoice {invoice_id}: {e}'
                    )
                    out['sub_etapas']['f5d7_fiscal_setup_falha'] += 1

                # commit sub-etapas — falha NAO derruba (D6)
                _commit_resilient()

            # Se ainda ha pendentes, aguarda antes do proximo loop
            if pendentes_set:
                logger.info(
                    f'F5d aguardando {len(pendentes_set)} pickings ainda '
                    f'(elapsed={int(time.time() - start_polling)}s/'
                    f'{timeout_polling}s)'
                )
                time.sleep(poll_interval)

        # Timeout — registrar ajustes nao resolvidos
        if pendentes_set:
            logger.warning(
                f'F5d timeout {timeout_polling}s — {len(pendentes_set)} '
                f'pickings sem invoice: {sorted(pendentes_set)}'
            )
            for pid in pendentes_set:
                metas = ajustes_meta_por_pid[pid]
                ajustes_to_timeout: List = []
                for meta in metas:
                    af = safe_session_get(AjusteEstoqueInventario, meta['id'])
                    if af is not None:
                        ajustes_to_timeout.append(af)
                tempo_ms_pid = int(
                    (time.time() - inicio_por_pid[pid]) * 1000
                )
                for aj in ajustes_to_timeout:
                    # NAO mudar fase para FALHA (operador pode rodar resume)
                    # Apenas registra auditoria com status TIMEOUT.
                    _registrar_auditoria(
                        ajuste_id=aj.id, ciclo=ciclo, fase='F5d',
                        acao='aguardar_invoice', modelo_odoo='account.move',
                        status='TIMEOUT', executado_por=usuario,
                        erro_msg=(
                            f'timeout {timeout_polling}s — robo CIEL IT '
                            f'nao criou invoice (picking {pid})'
                        ),
                        tempo_ms=tempo_ms_pid,
                    )
                _commit_resilient()

        out['pickings_resolvidos'] = dict(resolved)
        out['pickings_timeout'] = sorted(pendentes_set)
        n_resolved = len(resolved)
        n_pendentes_inicial = len(pickings_pendentes)
        if n_resolved == n_pendentes_inicial:
            out['status'] = 'EXECUTADO_ETAPA_C'
        elif n_resolved > 0:
            out['status'] = 'EXECUTADO_PARCIAL_TIMEOUT'
        else:
            out['status'] = 'FALHA_TIMEOUT_TOTAL'

        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    def executar_etapa_d(
        self,
        *,
        ciclo: str,
        company_origem_id: Optional[int] = None,
        dry_run: bool = True,
        confirmar_sefaz: bool = False,
        usuario: str = 'faturamento_pipeline',
        cod_produto: Optional[str] = None,
        max_tentativas: int = F5E_PLAYWRIGHT_MAX_TENTATIVAS,
        intervalo_retry: int = F5E_PLAYWRIGHT_INTERVALO_RETRY_S,
    ) -> Dict[str, Any]:
        """ETAPA D v17 — F5e transmitir SEFAZ via Playwright (IRREVERSIVEL).

        Para cada `account.move` (invoice CIEL IT) com `fase_pipeline=
        F5d_INVOICE_GERADA`, transmite NF-e SEFAZ via Playwright UI Odoo
        (serial, 1 browser). Atualiza `fase_pipeline=F5e_SEFAZ_OK` + `chave_nfe`
        em TODOS ajustes da mesma invoice.

        Patterns codificados (do service legado L1116-1346 + v16 patterns):
          - D7 (HARD_FAIL_CONFIG_ERRORS): playwright_indisponivel +
            odoo_password_ausente + odoo_username_ausente + tentativas=0
            ABORTA batch (RuntimeError) — operador intervir.
          - D8 (idempotencia TRIPLA):
              1. Por ajuste: skip se sem invoice_id_odoo (anomalia F5d)
              2. Por invoice no batch: 1 invoice = 1 transmissao SEFAZ
              3. Por persistencia: skip se ja F5e_SEFAZ_OK ou status=EXECUTADO
          - D5 (SNAPSHOT meta antes do polling): sessao pode expirar em
            5-10min Playwright/NF.
          - D9 (re-fetch via safe_session_get apos Playwright): combinado
            com commit_resilient antes/depois.
          - F6 v15c (safe_session_get): anti-DetachedInstanceError pos-commit.
          - MED C-1 (situacao_nf != 'autorizado' mas sucesso=True): registra
            em erro_msg para audit fiscal (excecao_autorizado).
          - MED C-2 (cstat+xmotivo de ultimo_estado): persistir em falha.
          - G016 (D14): commit_resilient antes E depois de cada NF.

        D18: exige `--confirmar-sefaz` ALEM de `--confirmar` (2 niveis).

        Args:
            ciclo: identificador do ciclo.
            company_origem_id: filtro por company emissora (None = todas).
            dry_run: True (default) NAO chama Playwright; apenas reporta
                planejamento (quantas invoices seriam transmitidas).
            confirmar_sefaz: 2 nivel — exigido para real-run (irreversivel).
            usuario: identificador para auditoria.
            cod_produto: smoke/canary.
            max_tentativas: tentativas Playwright/NF (default 15).
            intervalo_retry: segundos entre tentativas (default 120).

        Returns:
            dict com:
              status: DRY_RUN_OK_ETAPA_D | EXECUTADO_ETAPA_D |
                      EXECUTADO_PARCIAL | SKIP_NENHUM_AJUSTE |
                      BLOQUEADO_SEM_CONFIRMAR_SEFAZ | FALHA_CONFIG |
                      FALHA_COMMIT_PRE
              invoices_pendentes: lista de invoice_ids esperados
              invoices_resolvidas: dict {invoice_id: chave_nfe}
              invoices_falha: dict {invoice_id: erro}
              invoices_skip: lista de invoice_ids ja em F5e_SEFAZ_OK
              contadores: {sucesso, falha, skip_idempotent}

        Em HARD_FAIL_CONFIG (D7), retorna early com `status='FALHA_CONFIG'`
        e `erro_config` populado. Caller deve verificar status (NAO via
        try/except — orchestrator nao lanca RuntimeError; alinhado a
        Reviewer 1 HIGH-2 v17).
        """
        from app import db  # lazy
        from app.odoo.models import AjusteEstoqueInventario  # lazy

        t0 = time.time()

        # D18: real-run exige --confirmar-sefaz (2 niveis)
        if not dry_run and not confirmar_sefaz:
            return {
                'etapa': 'D',
                'ciclo': ciclo,
                'status': 'BLOQUEADO_SEM_CONFIRMAR_SEFAZ',
                'erro': (
                    'ETAPA D (SEFAZ) e IRREVERSIVEL. Real-run exige '
                    '`--confirmar-sefaz` ALEM de `--confirmar`.'
                ),
                'tempo_ms': int((time.time() - t0) * 1000),
            }

        # Carregar ajustes em F5d_INVOICE_GERADA (idempotencia: ja em
        # F5e_SEFAZ_OK sao pulados via filtro de fase).
        ajustes = _carregar_ajustes(
            ciclo=ciclo,
            company_origem_id=company_origem_id,
            fases_pipeline=[FASE_F5d_OK],
            cod_produto=cod_produto,
        )

        # Defensivo D8.1: filtrar ajustes SEM invoice_id_odoo (anomalia F5d)
        ajustes_validos: List = [a for a in ajustes if a.invoice_id_odoo]
        ajustes_sem_invoice: List = [
            a for a in ajustes if not a.invoice_id_odoo
        ]
        if ajustes_sem_invoice:
            logger.warning(
                f'ETAPA D: {len(ajustes_sem_invoice)} ajustes em '
                f'F5d_INVOICE_GERADA SEM invoice_id_odoo (anomalia) — '
                f'pulando: {[a.id for a in ajustes_sem_invoice[:5]]}'
            )

        out: Dict[str, Any] = {
            'etapa': 'D',
            'ciclo': ciclo,
            'company_origem_id': company_origem_id,
            'dry_run': dry_run,
            'confirmar_sefaz': confirmar_sefaz,
            'ajustes_total': len(ajustes_validos),
            'ajustes_sem_invoice': len(ajustes_sem_invoice),
            'invoices_pendentes': [],
            'invoices_resolvidas': {},
            'invoices_falha': {},
            'invoices_skip': [],
            'contadores': {
                'sucesso': 0,
                'falha': 0,
                'skip_idempotent': 0,
            },
        }

        if not ajustes_validos:
            out['status'] = 'SKIP_NENHUM_AJUSTE'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # D8.2: agrupar por invoice_id (1 invoice = 1 transmissao SEFAZ)
        ajustes_por_invoice: Dict[int, List] = defaultdict(list)
        for a in ajustes_validos:
            ajustes_por_invoice[a.invoice_id_odoo].append(a)
        invoices_pendentes = list(ajustes_por_invoice.keys())
        out['invoices_pendentes'] = sorted(invoices_pendentes)

        if dry_run:
            out['status'] = 'DRY_RUN_OK_ETAPA_D'
            out['observacao'] = (
                f'v17 dry-run: {len(invoices_pendentes)} invoices em '
                f'F5d_INVOICE_GERADA esperando transmissao SEFAZ. '
                f'Real-run faria Playwright serial (~5-10min/NF; total '
                f'estimado={len(invoices_pendentes) * 5}-'
                f'{len(invoices_pendentes) * 10}min).'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # ============================================================
        # REAL-RUN: Playwright serial (IRREVERSIVEL — SEFAZ)
        # ============================================================

        # Lazy import Playwright service (NAO MEXER — modulo externo)
        from app.recebimento.services.playwright_nfe_transmissao import (  # noqa: PLC0415
            transmitir_nfe_via_playwright,
        )

        # D5: SNAPSHOT meta antes do loop (sessao pode expirar em
        # 5-10min Playwright/NF).
        ajustes_meta_por_invoice: Dict[int, List[Dict[str, Any]]] = {
            inv_id: [
                {
                    'id': a.id,
                    'ciclo': a.ciclo,
                    'acao_decidida': a.acao_decidida,
                }
                for a in lista
            ]
            for inv_id, lista in ajustes_por_invoice.items()
        }

        # G016 Opcao A: commit antes do loop longo
        if not _commit_resilient():
            logger.error(
                'F5e commit_resilient falhou ANTES do Playwright loop — '
                'abortando ETAPA D.'
            )
            out['status'] = 'FALHA_COMMIT_PRE'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # D8.3: idempotencia POR INVOICE no batch (1 invoice = 1 transmissao).
        # invoices_processadas[inv_id] = chave_nfe (sucesso) ou None (falha).
        invoices_processadas: Dict[int, Optional[str]] = {}

        for invoice_id in invoices_pendentes:
            metas = ajustes_meta_por_invoice[invoice_id]
            inicio_inv = time.time()

            # F6 v15c: re-fetch ajustes via safe_session_get
            ajustes_fresh: List = []
            for meta in metas:
                af = safe_session_get(AjusteEstoqueInventario, meta['id'])
                if af is not None:
                    ajustes_fresh.append(af)
            if not ajustes_fresh:
                logger.error(
                    f'F5e: re-fetch ajustes vazio para invoice {invoice_id} '
                    f'(todos sumiram?). Skipping.'
                )
                continue

            # D8.3 (persistencia): skip se QUALQUER ajuste do invoice ja F5e_OK
            # CRITICAL-2 v17 fix (Reviewer 1 conf 90): guard permissivo —
            # 1 ajuste em F5e_OK = invoice JA transmitida (chave SEFAZ unica).
            # Cenario coberto: crash mid-loop apos marcar a1=F5e_OK mas antes
            # de a2/a3 (commit atomico ausente por ajuste). Sem este fix,
            # re-run com a3 ainda em F5d invocaria Playwright DOBRADO.
            ja_processados = [
                a for a in ajustes_fresh
                if a.fase_pipeline == FASE_F5e_OK or a.status == 'EXECUTADO'
            ]
            # HIGH-1 v17 (Reviewer 1 conf 85): estado inconsistente
            # (status=EXECUTADO mas fase != F5e_OK) WARN — pode indicar
            # corrupcao de fase_pipeline em rodada anterior.
            inconsistentes = [
                a for a in ajustes_fresh
                if a.status == 'EXECUTADO' and a.fase_pipeline != FASE_F5e_OK
            ]
            if inconsistentes:
                logger.warning(
                    f'F5e invoice {invoice_id}: {len(inconsistentes)} ajustes '
                    f'com status=EXECUTADO mas fase != F5e_OK (estado '
                    f'inconsistente). Ids: {[a.id for a in inconsistentes[:3]]}. '
                    f'NAO transmitindo (precaucao SEFAZ).'
                )
            if ja_processados:
                chave_existente = next(
                    (a.chave_nfe for a in ja_processados if a.chave_nfe), None,
                )
                logger.info(
                    f'F5e SKIP invoice {invoice_id} ja transmitida '
                    f'(chave={chave_existente}, {len(ja_processados)}/'
                    f'{len(ajustes_fresh)} ajustes em F5e_OK) — '
                    f'idempotencia persistente'
                )
                out['invoices_skip'].append(invoice_id)
                out['contadores']['skip_idempotent'] += 1
                if chave_existente:
                    invoices_processadas[invoice_id] = chave_existente
                continue

            # G016 Opcao A: commit antes da NF longa (libera conexao DB)
            self_commit_pre = _commit_resilient()
            if not self_commit_pre:
                logger.warning(
                    f'F5e commit pre-Playwright invoice {invoice_id} '
                    f'falhou (SSL). Continuando — risco de DB desincronizar.'
                )

            # Transmitir Playwright (5-10min/NF)
            try:
                resultado = transmitir_nfe_via_playwright(
                    invoice_id, self.odoo, logger,
                    max_tentativas=max_tentativas,
                    intervalo_retry=intervalo_retry,
                )
            except Exception as e:
                # Excecao inesperada — NAO HARD_FAIL_CONFIG, registrar e seguir
                tempo_ms_inv = int((time.time() - inicio_inv) * 1000)
                logger.error(
                    f'F5e excecao invoice {invoice_id}: {e}', exc_info=True,
                )
                # F6 v15c: re-fetch pos-Playwright (sessao pode ter expirado)
                ajustes_post: List = []
                for meta in metas:
                    af = safe_session_get(AjusteEstoqueInventario, meta['id'])
                    if af is not None:
                        ajustes_post.append(af)
                for aj in ajustes_post:
                    aj.fase_pipeline = FASE_F5e_FALHA
                    aj.erro_msg = (f'F5e excecao: {e}')[:500]
                    _registrar_auditoria(
                        ajuste_id=aj.id, ciclo=ciclo, fase='F5e',
                        acao='transmitir_nfe', modelo_odoo='account.move',
                        status='EXCECAO', odoo_id=invoice_id,
                        erro_msg=str(e)[:500], tempo_ms=tempo_ms_inv,
                        executado_por=usuario,
                    )
                _commit_resilient()
                invoices_processadas[invoice_id] = None
                out['invoices_falha'][invoice_id] = (
                    f'excecao: {str(e)[:200]}'
                )
                out['contadores']['falha'] += 1
                continue

            tempo_ms_inv = int((time.time() - inicio_inv) * 1000)

            # D7 (HARD_FAIL_CONFIG): batch abortado se erro de config
            if (
                not resultado.get('sucesso')
                and resultado.get('tentativas') == 0
                and resultado.get('erro') in HARD_FAIL_CONFIG_ERRORS
            ):
                erro = resultado['erro']
                # F6 v15c: re-fetch + marcar falha
                ajustes_post: List = []
                for meta in metas:
                    af = safe_session_get(AjusteEstoqueInventario, meta['id'])
                    if af is not None:
                        ajustes_post.append(af)
                for aj in ajustes_post:
                    aj.fase_pipeline = FASE_F5e_FALHA
                    aj.erro_msg = (f'Config invalida: {erro}')[:500]
                    _registrar_auditoria(
                        ajuste_id=aj.id, ciclo=ciclo, fase='F5e',
                        acao='transmitir_nfe', modelo_odoo='account.move',
                        status='FALHA_CONFIG', odoo_id=invoice_id,
                        erro_msg=erro, tempo_ms=tempo_ms_inv,
                        resposta=resultado, executado_por=usuario,
                    )
                _commit_resilient()
                out['invoices_falha'][invoice_id] = erro
                out['contadores']['falha'] += 1
                # Abort batch
                logger.error(
                    f'F5e HARD_FAIL_CONFIG: {erro}. Batch abortado. '
                    f'{len(invoices_pendentes) - len(invoices_processadas) - 1} '
                    f'invoices nao processadas.'
                )
                out['status'] = 'FALHA_CONFIG'
                out['erro_config'] = erro
                out['invoices_resolvidas'] = {
                    k: v for k, v in invoices_processadas.items() if v
                }
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out

            # D9: re-fetch ajustes apos Playwright (sessao pode ter expirado)
            ajustes_post: List = []
            for meta in metas:
                af = safe_session_get(AjusteEstoqueInventario, meta['id'])
                if af is not None:
                    ajustes_post.append(af)
            if not ajustes_post:
                logger.error(
                    f'F5e re-fetch pos-Playwright vazio para invoice '
                    f'{invoice_id} — resultado NAO persistido. Sem '
                    f'recovery: ajuste sumiu do DB local.'
                )
                continue

            if resultado.get('sucesso'):
                chave_nfe = resultado.get('chave_nf')
                situacao = resultado.get('situacao_nf')
                # CRITICAL-1 v17: invoices_processadas atualizado apenas
                # apos commit_resilient OK (vide fix abaixo). Antes do fix,
                # marcacao prematura aqui podia confundir re-run em crash.
                # Marcar TODOS os ajustes da mesma invoice como F5e_SEFAZ_OK
                # NOTA D-OPS-2b §7.5.2: F5e do service legado propaga chave para
                # TODOS ajustes do invoice. Workaround documentado mas NAO
                # corrigido aqui (regra v14a-fix: NAO MEXER no service legado;
                # fix definitivo via Skill 8 deve filtrar por account.move.line
                # — TODO v18 ou pos-canary C20).
                for aj in ajustes_post:
                    aj.fase_pipeline = FASE_F5e_OK
                    aj.chave_nfe = chave_nfe
                    aj.status = 'EXECUTADO'
                    # MED C-1 v17: registrar excecao_autorizado para audit
                    if situacao and situacao != 'autorizado':
                        aj.erro_msg = (
                            f'{situacao} tentativa='
                            f'{resultado.get("tentativa", "?")}'
                        )[:500]
                    _registrar_auditoria(
                        ajuste_id=aj.id, ciclo=ciclo, fase='F5e',
                        acao='transmitir_nfe', modelo_odoo='account.move',
                        status='SUCESSO', odoo_id=invoice_id,
                        resposta=resultado, tempo_ms=tempo_ms_inv,
                        executado_por=usuario,
                    )
                # CRITICAL-1 v17 fix (Reviewer 1 conf 95): se commit
                # pos-Playwright FALHA, NAO contar como sucesso (estado em
                # memoria NAO persistido — re-run dobraria SEFAZ). Marcar
                # explicitamente como FALHA_COMMIT_POS_SEFAZ_OK p/ operador
                # investigar — SEFAZ ja autorizada com chave={chave_nfe}.
                if not _commit_resilient():
                    logger.error(
                        f'F5e CRITICAL: commit POS-Playwright FALHOU para '
                        f'invoice {invoice_id} (SEFAZ AUTORIZADA com '
                        f'chave={chave_nfe}). Estado em memoria NAO '
                        f'persistido. Operador DEVE checar DB e marcar '
                        f'fase_pipeline=F5e_SEFAZ_OK manualmente. '
                        f'NAO re-executar ETAPA D para esta invoice.'
                    )
                    invoices_processadas[invoice_id] = chave_nfe  # SEFAZ ok
                    out['invoices_falha'][invoice_id] = (
                        f'FALHA_COMMIT_POS_SEFAZ_OK (chave={chave_nfe} '
                        f'autorizada mas DB nao atualizado)'
                    )
                    out['contadores']['falha'] += 1
                    continue
                invoices_processadas[invoice_id] = chave_nfe
                out['invoices_resolvidas'][invoice_id] = chave_nfe
                out['contadores']['sucesso'] += 1
                logger.info(
                    f'F5e invoice {invoice_id} -> SEFAZ OK '
                    f'(chave={chave_nfe}, situacao={situacao}, '
                    f'{len(ajustes_post)} ajustes)'
                )
            else:
                erro = resultado.get('erro', 'erro_desconhecido')
                ultimo = resultado.get('ultimo_estado') or {}
                invoices_processadas[invoice_id] = None
                # MED C-2 v17: persistir cstat+xmotivo (campo acionavel)
                erro_msg_completo = (
                    f"SEFAZ falhou: {erro} "
                    f"(tentativas={resultado.get('tentativas', '?')}, "
                    f"cstat={ultimo.get('cstat')}, "
                    f"xmotivo={ultimo.get('xmotivo')})"
                )[:500]
                for aj in ajustes_post:
                    aj.fase_pipeline = FASE_F5e_FALHA
                    aj.erro_msg = erro_msg_completo
                    _registrar_auditoria(
                        ajuste_id=aj.id, ciclo=ciclo, fase='F5e',
                        acao='transmitir_nfe', modelo_odoo='account.move',
                        status='FALHA', odoo_id=invoice_id,
                        resposta=resultado, erro_msg=erro_msg_completo,
                        tempo_ms=tempo_ms_inv, executado_por=usuario,
                    )
                _commit_resilient()
                out['invoices_falha'][invoice_id] = erro
                out['contadores']['falha'] += 1
                logger.error(
                    f'F5e invoice {invoice_id} falhou: {erro} '
                    f'(cstat={ultimo.get("cstat")}, '
                    f'xmotivo={ultimo.get("xmotivo")})'
                )

        # Status agregado
        n_sucesso = out['contadores']['sucesso']
        n_falha = out['contadores']['falha']
        n_skip = out['contadores']['skip_idempotent']
        n_total = len(invoices_pendentes)
        if n_falha == 0:
            out['status'] = 'EXECUTADO_ETAPA_D'
        elif n_sucesso > 0 or n_skip > 0:
            out['status'] = 'EXECUTADO_PARCIAL'
        else:
            out['status'] = 'FALHA_ETAPA_D'

        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    # ========================================================
    # FLUXO L3 1.2.1 / 1.2.2 — v19+ ABRANGENTE
    # ========================================================
    # Composicao dos 7 atomos da Skill 7 ABRANGENTE (`escriturando-odoo` v19+)
    # + atomo S2 Skill 5 (`preencher_lotes_picking` v19+) seguindo a inteligencia
    # documentada em:
    #   - app/odoo/estoque/fluxos/1.2.1-escriturar-dfe-industrializacao.md
    #   - app/odoo/estoque/fluxos/1.2.2-criar-dfe-manual-transferencia.md
    #
    # AP2 RECLASSIFICADO (v19+): este metodo SUBSTITUI a logica das ETAPA E+F
    # atuais (que continuam funcionando como legacy ate v20+ ativar opt-in).
    # ETAPA E legacy: Skill 7 V1 STRICT `criar_recebimento_orchestrado` (AP1).
    # ETAPA F legacy: Skill 5 v15a `criar_picking_entrada_destino_manual` (AP2).
    # ========================================================

    def executar_fluxo_l3_1_2_x(
        self,
        *,
        invoice_id_saida: int,
        company_destino: int,
        l10n_br_tipo_pedido_dfe: str,
        l10n_br_tipo_pedido_po: str,
        team_id: int,
        payment_term_id: int,
        picking_type_id: int,
        payment_provider_id: int,
        lotes_data: Optional[List[Dict[str, Any]]] = None,
        lote_default: Optional[str] = None,
        poll_timeout_po_s: int = 1800,
        poll_timeout_invoice_s: int = 300,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """v19+ ABRANGENTE: executa FLUXO L3 1.2.1 (caminho A) ou 1.2.2 (caminho B).

        Decide via `buscar_dfe(chave_nfe_do_invoice_saida, company_destino)`:
          - encontrado=True  -> caminho A (DFe ja veio via SEFAZ)
          - encontrado=False -> caminho B (DFe upload via XML da SAIDA — NF nossa)

        Composicao sequencial dos atomos:
          1. Skill 7 buscar_dfe (READ — decide caminho)
          1.5 (F2a v25+) caminho A: corrigir dfe.line.company_id=destino
          2. SE caminho B: Skill 7 criar_dfe_a_partir_do_invoice_saida (upload XML)
          3. Skill 7 escriturar_dfe (l10n_br_tipo_pedido_dfe='compra' + data_entrada)
          4. Skill 7 gerar_po_from_dfe (fire_and_poll — robo CIEL IT cria PO)
          5. Skill 7 preencher_po (team + payment + picking_type + company +
                                   l10n_br_tipo_pedido_po='serv-industrializacao')
          6. Skill 7 confirmar_po (button_confirm + cond button_approve)
          6.5 (F2b v25+) G023 force company_id em picking + moves
          7. Skill 5 preencher_lotes_picking (lotes_data resolvido — F1 v25+)
          8. Skill 5 validar (button_validate — G019/G020)
          9. Skill 7 criar_invoice_from_po (action_create_invoice + poll;
             invoice herda l10n_br_tipo_pedido='serv-industrializacao' da PO)

        Posting da invoice (account.move.action_post) NAO faz parte deste metodo —
        fica para o caller (orchestrator pipeline_bulk v20+ ou outro caso).

        Args:
            invoice_id_saida: account.move da NF SAIDA (state=posted,
                situacao=autorizado, l10n_br_xml_aut_nfe nao-vazio).
            company_destino: 1=FB, 4=CD, 5=LF.
            l10n_br_tipo_pedido_dfe: tipo do pedido escrito no DFe no passo 3
                (ex.: 'compra' para INDUSTRIALIZACAO_FB_LF). F3a v25+ —
                separado de l10n_br_tipo_pedido_po porque DFe e PO precisam
                de tipos diferentes neste fluxo (DFe 'compra' destrava
                action_gerar_po_dfe; PO 'serv-industrializacao' fixa
                journal ENTIN + CFOP 1949).
            l10n_br_tipo_pedido_po: tipo do pedido escrito na PO no passo 5
                (ex.: 'serv-industrializacao' para INDUSTRIALIZACAO_FB_LF).
                Invoice herda da PO no passo 9.
            team_id: purchase.team.id (caller fornece via constants).
                Para LF (F4 v25+): FIXO 143 (Rafael) via CONSTANTS_FLUXO_L3.
            payment_term_id: account.payment.term.id.
            picking_type_id: stock.picking.type.id.
            payment_provider_id: payment.provider.id (G029).
            lotes_data: mapping por produto. F1 v25+: caller (orchestrator
                `_executar_etapa_f_via_fluxo_l3`) DEVE resolver via
                AjusteEstoqueInventario antes de chamar. Formato:
                [{'product_id': int, 'lote_nome': str, 'quantidade': float}].
            lote_default: fallback ML sem cobertura em lotes_data. F1b v25+:
                default mudado de 'MIGRAÇÃO' literal para None (forcar caller
                a fornecer lotes_data correto). Caller pode passar
                'INV-{cod}-{HOJE}' resolvido em batch se quiser fallback.
            poll_timeout_po_s: timeout do polling de gerar_po_from_dfe.
            poll_timeout_invoice_s: timeout do polling de criar_invoice_from_po.
            dry_run: True (default) NAO escreve em Odoo; cada atomo dispara
                em modo dry_run+true.

        Returns:
            dict com:
              status: 'DRY_RUN_OK' | 'FLUXO_OK' | 'FALHA_PASSO_<X>'
              caminho: 'A' | 'B' | 'INDEFINIDO'
              dfe_id: int | None
              po_id: int | None
              picking_id: int | None
              invoice_id: int | None
              passos: list[{'passo': str, 'status': str, 'tempo_ms': int}]
              tempo_ms: int
              erro: str | None
        """
        from app.odoo.estoque.scripts.escrituracao import (  # lazy
            EscrituracaoLfService,
        )

        t0 = time.time()
        out: Dict[str, Any] = {
            'status': 'FALHA_PASSO_1_BUSCAR_DFE',
            'caminho': 'INDEFINIDO',
            'dfe_id': None,
            'po_id': None,
            'picking_id': None,
            'invoice_id': None,
            'passos': [],
            'tempo_ms': 0,
            'erro': None,
        }

        escr_svc = EscrituracaoLfService(odoo=self.odoo)

        def _passo(nome: str, resultado: Dict[str, Any]) -> None:
            out['passos'].append({
                'passo': nome,
                'status': resultado.get('status'),
                'tempo_ms': resultado.get('tempo_ms'),
                'erro': resultado.get('erro'),
            })

        # ----- Passo 1: buscar_dfe (READ, decide caminho) -----
        # Precisa chave_nfe do invoice_saida — leitura previa
        try:
            inv_resp = self.odoo.read(
                'account.move', [invoice_id_saida],
                ['l10n_br_chave_nf', 'state'],
            )
        except Exception as e:
            out['erro'] = f'erro_ler_invoice_saida: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out
        if not inv_resp:
            out['erro'] = 'invoice_saida_sumiu'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out
        chave_nfe = (inv_resp[0].get('l10n_br_chave_nf') or '').strip()
        if not chave_nfe:
            out['erro'] = 'invoice_saida_sem_chave_nfe'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        r1 = escr_svc.buscar_dfe(
            chave_nfe=chave_nfe, company_id=company_destino,
        )
        _passo('1_buscar_dfe', r1)

        # ----- Passo 2: caminho A vs B -----
        # CR-v19+-HIGH-3: NAO retornar early quando status='processado'.
        # 'processado' significa apenas XML parseado pelo robo CIEL IT
        # (codes 04/05 em l10n_br_status); NAO garante que PO+picking+invoice
        # ja existem. Idempotencia real e' feita pelos atomos a jusante
        # (gerar_po_from_dfe via dfe.purchase_id, criar_invoice_from_po via
        # po.invoice_ids, etc) — deixar fluir.
        if r1.get('encontrado'):
            out['caminho'] = 'A'
            dfe_id = r1.get('dfe_id')

            # F2a v25+ (Rafael 2026-05-27): aplicar fix B-V23-1 tambem no
            # caminho A. Quando DFe vem via SEFAZ, as `dfe.line.company_id`
            # herdam company do EMITENTE (FB=1) em vez do DESTINATARIO
            # (LF=5). Sintoma: passo 9 `action_create_invoice` falha com
            # 'Rafael nao tem acesso leitura a dfe.line' (ir.rule id=353).
            # B-V23-1 estava codificado apenas em
            # `criar_dfe_a_partir_do_invoice_saida` (caminho B). F2a fecha o
            # gap para o caminho A — que e' o caminho mais comum em
            # INDUSTRIALIZACAO_FB_LF (4 de 4 DFes do canary v20+ vieram via
            # SEFAZ, ver fluxos/1.2.2-criar-dfe-manual-transferencia.md L24).
            if dfe_id and not dry_run:
                r1_5 = escr_svc.alinhar_dfe_lines_company(
                    dfe_id=dfe_id,
                    company_destino=company_destino,
                )
                _passo('1_5_alinhar_dfe_lines_company_a', r1_5)
        else:
            out['caminho'] = 'B'
            r2 = escr_svc.criar_dfe_a_partir_do_invoice_saida(
                invoice_id_saida=invoice_id_saida,
                company_destino=company_destino,
                dry_run=dry_run,
            )
            _passo('2_criar_dfe_a_partir_do_invoice_saida', r2)
            if r2.get('status') not in (
                'CRIADO', 'IDEMPOTENT_EXISTE', 'DRY_RUN_OK',
            ):
                out['status'] = 'FALHA_PASSO_2_CRIAR_DFE'
                out['erro'] = r2.get('erro')
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out
            dfe_id = r2.get('dfe_id')

        out['dfe_id'] = dfe_id

        # ----- Passo 3: escriturar_dfe (F3b v25+: tipo='compra' p/ DFe) -----
        r3 = escr_svc.escriturar_dfe(
            dfe_id=dfe_id or 0,  # type-hint friendly; atomo valida
            l10n_br_tipo_pedido=l10n_br_tipo_pedido_dfe,
            dry_run=dry_run,
        )
        _passo('3_escriturar_dfe', r3)
        # FIX v20+ (descoberto no canary REAL 2026-05-26): aceitar
        # IDEMPOTENT_ESCRITURADO novo status v20+ do atomo Skill 7 (FIX A
        # anti-sobrescrita fiscal). Sem este accept, DFe ja escriturado em
        # PROD (caso normal pos-ETAPA E legacy) caia em FALHA_PASSO_3.
        if r3.get('status') not in (
            'ESCRITURADO', 'DRY_RUN_OK', 'IDEMPOTENT_ESCRITURADO',
        ):
            out['status'] = 'FALHA_PASSO_3_ESCRITURAR'
            out['erro'] = r3.get('erro')
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # ----- Passo 4: gerar_po_from_dfe -----
        r4 = escr_svc.gerar_po_from_dfe(
            dfe_id=dfe_id or 0,
            poll_timeout_s=poll_timeout_po_s,
            dry_run=dry_run,
        )
        _passo('4_gerar_po_from_dfe', r4)
        if r4.get('status') not in (
            'CRIADO', 'IDEMPOTENT_EXISTE', 'DRY_RUN_OK',
        ):
            out['status'] = 'FALHA_PASSO_4_GERAR_PO'
            out['erro'] = r4.get('erro')
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out
        po_id = r4.get('po_id')
        out['po_id'] = po_id

        # Em dry-run nao temos po_id real — abortar gracioso com FLUXO_OK
        if dry_run:
            out['status'] = 'DRY_RUN_OK'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # ----- Passo 5: preencher_po (F3d v25+: tipo='serv-industrializacao') -----
        r5 = escr_svc.preencher_po(
            po_id=po_id or 0,
            team_id=team_id,
            payment_term_id=payment_term_id,
            picking_type_id=picking_type_id,
            company_id=company_destino,
            payment_provider_id=payment_provider_id,
            l10n_br_tipo_pedido=l10n_br_tipo_pedido_po,
            dry_run=False,
        )
        _passo('5_preencher_po', r5)
        if r5.get('status') not in ('PREENCHIDO',):
            out['status'] = 'FALHA_PASSO_5_PREENCHER_PO'
            out['erro'] = r5.get('erro')
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # ----- Passo 6: confirmar_po -----
        r6 = escr_svc.confirmar_po(
            po_id=po_id or 0, dry_run=False,
        )
        _passo('6_confirmar_po', r6)
        if r6.get('status') not in (
            'CONFIRMADO', 'IDEMPOTENT_CONFIRMADO',
        ):
            out['status'] = 'FALHA_PASSO_6_CONFIRMAR_PO'
            out['erro'] = r6.get('erro')
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # ----- Passo 7+8: preencher_lotes_picking + validar -----
        # picking foi gerado pelo Odoo apos confirmar_po. Buscar via
        # purchase.order.picking_ids
        # CR-v19+-HIGH-1: filtrar por state. PO pode ter multiplos
        # pickings (retorno + entrada) ou picking ja 'done' — escolher o
        # ativo (assigned/partially_available/confirmed) e fazer idempotencia
        # se ja done.
        try:
            po_data = self.odoo.read(
                'purchase.order', [po_id], ['picking_ids'],
            )
            picking_ids = (
                po_data[0].get('picking_ids', []) if po_data else []
            )
            if not picking_ids:
                out['status'] = 'FALHA_PASSO_7_SEM_PICKING'
                out['erro'] = 'po_sem_picking_pos_confirm'
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out
            pks = self.odoo.read(
                'stock.picking', picking_ids, ['id', 'state', 'name'],
            ) or []
        except Exception as e:
            out['status'] = 'FALHA_PASSO_7_SEM_PICKING'
            out['erro'] = f'erro_ler_picking_ids: {str(e)[:200]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Tentar achar picking 'done' (idempotente)
        done_pk = next(
            (p for p in pks if p.get('state') == 'done'), None,
        )
        if done_pk:
            # Idempotente: preencher_lotes + validar ja rodaram antes
            picking_id = done_pk['id']
            out['picking_id'] = picking_id
            _passo('7_preencher_lotes_picking', {
                'status': 'IDEMPOTENT_DONE',
                'tempo_ms': 0,
                'erro': None,
            })
            _passo('8_validar_picking', {
                'status': 'IDEMPOTENT_DONE',
                'tempo_ms': 0,
                'erro': None,
            })
        else:
            # Achar picking ativo p/ preencher + validar
            ativo_pk = next(
                (p for p in pks if p.get('state') in (
                    'assigned', 'partially_available', 'confirmed',
                )), None,
            )
            if not ativo_pk:
                out['status'] = 'FALHA_PASSO_7_PICKING_STATE_INVALIDO'
                out['erro'] = (
                    f'nenhum picking ativo (states: '
                    f'{[p.get("state") for p in pks]})'
                )
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out
            picking_id = ativo_pk['id']
            out['picking_id'] = picking_id

            # F2b v25+ (Rafael 2026-05-27): G023 force company_id em picking +
            # moves nativos (gerados via action_gerar_po_dfe). XML-RPC nao
            # herda company automaticamente em alguns cenarios (sintoma no
            # AVULSO_FRASCO: picking sairia de location_id=4 Parceiros/
            # Fornecedores). Espelha hardening do atomo legacy
            # `criar_picking_entrada_destino_manual` (picking.py L1391-1399).
            # Idempotente: write em company ja correta = no-op no Odoo.
            try:
                self.odoo.write(
                    'stock.picking', [picking_id],
                    {'company_id': company_destino},
                )
                moves_ids = self.odoo.search(
                    'stock.move', [('picking_id', '=', picking_id)],
                )
                if moves_ids:
                    self.odoo.write(
                        'stock.move', moves_ids,
                        {'company_id': company_destino},
                    )
                _passo('6_5_g023_force_company', {
                    'status': 'OK',
                    'picking_id': picking_id,
                    'moves_alinhados': len(moves_ids) if moves_ids else 0,
                    'tempo_ms': 0,
                    'erro': None,
                })
            except Exception as e:
                # NAO-fatal: caso company ja esteja correta ou Odoo
                # rejeitar write — segue fluxo e deixa o erro real
                # aparecer no passo 7/8/9 se houver.
                logger.warning(
                    f'F2b G023 force company falhou (non-fatal): '
                    f'{str(e)[:200]}'
                )
                _passo('6_5_g023_force_company', {
                    'status': 'FALHOU_NAO_FATAL',
                    'erro': f'{str(e)[:200]}',
                    'tempo_ms': 0,
                })

            r7 = self.picking_svc.preencher_lotes_picking(
                picking_id=picking_id,
                lotes_data=lotes_data or [],
                lote_default=lote_default,
                dry_run=False,
            )
            _passo('7_preencher_lotes_picking', r7)
            if r7.get('status') not in ('PREENCHIDO',):
                out['status'] = 'FALHA_PASSO_7_PREENCHER_LOTES'
                out['erro'] = r7.get('erro')
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out

            # ----- Passo 8: validar picking -----
            try:
                self.picking_svc.validar(picking_id)
                _passo('8_validar_picking', {
                    'status': 'VALIDADO',
                    'tempo_ms': 0,
                    'erro': None,
                })
            except Exception as e:
                out['status'] = 'FALHA_PASSO_8_VALIDAR'
                out['erro'] = f'validar_picking_falhou: {str(e)[:200]}'
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out

        # ----- Passo 9: criar_invoice_from_po -----
        r9 = escr_svc.criar_invoice_from_po(
            po_id=po_id or 0,
            poll_timeout_s=poll_timeout_invoice_s,
            dry_run=False,
        )
        _passo('9_criar_invoice_from_po', r9)
        if r9.get('status') not in ('CRIADO', 'IDEMPOTENT_EXISTE'):
            out['status'] = 'FALHA_PASSO_9_CRIAR_INVOICE'
            out['erro'] = r9.get('erro')
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out
        out['invoice_id'] = r9.get('invoice_id')

        out['status'] = 'FLUXO_OK'
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    # ============================================================
    # v20+ — Constants por company_destino para FLUXO L3 1.2.x
    # v27+ S4 EXPAND — entries FB=1 e CD=4 (descoberta XML-RPC + MATRIZ)
    # ============================================================
    # Pattern por destino:
    #   - team_id: STATIC para LF=143 (decisao F4 v25+ — operacional fixo);
    #     None para FB+CD (G039 dinamico via _resolver_constants_fluxo_l3
    #     resolve no run-time pelo user de execucao + criar purchase.team
    #     se necessario via Skill 7 atomo garantir_purchase_team).
    #     CANDIDATE: Rafael define STATIC vs G039 caso-a-caso apos canary
    #     primeira INDUSTRIALIZACAO_*_FB ou TRANSFERIR_*_CD natural.
    #   - payment_term_id=2791 'A VISTA' universal (validado LF; assume-se
    #     universal por nao ter pagamento real inter-company).
    #   - payment_provider_id=38 'SEM PAGAMENTO' universal (G029).
    #   - picking_type_id: default Recebimento da company (descoberto via
    #     XML-RPC discovery 2026-05-27 — `stock.picking.type` filter
    #     code='incoming' + active=True). Casos especiais (transf-filial
    #     vs industrializacao vs retorno) sao derivados pelo motor fiscal
    #     Odoo via fiscal_position + l10n_br_tipo_pedido no DFe/PO; CFOP
    #     correto vira automaticamente. NAO precisa mapear PT especifico
    #     por acao_decidida no minimo viavel.
    #
    # MINIMO VIAVEL v27+ S4: 3 entries (LF=5 + FB=1 + CD=4). LF=5 ja
    # validado canary REAL PROD 2026-05-26 (caso 627348). FB+CD ainda
    # CANDIDATE — primeira INDUSTRIALIZACAO_LF_FB / TRANSFERIR_FB_CD /
    # PERDA_LF_FB natural valida canary v28+.
    CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO: Dict[int, Dict[str, Any]] = {
        1: {  # FB — CANDIDATE v27+ S4 (pendente canary REAL)
            'team_id': None,         # G039 dinamico (Rafael decide STATIC pos-canary)
            'payment_term_id': 2791, # 'A VISTA' (assumido universal)
            'picking_type_id': 1,    # 'Recebimento (FB)' (discovery 2026-05-27)
            'payment_provider_id': 38,  # G029 'SEM PAGAMENTO'
        },
        4: {  # CD — CANDIDATE v27+ S4 (pendente canary REAL)
            'team_id': None,         # G039 dinamico
            'payment_term_id': 2791, # 'A VISTA'
            'picking_type_id': 13,   # 'Recebimento (CD)' (discovery 2026-05-27)
            'payment_provider_id': 38,
        },
        5: {  # LF (validado canary v20+ + F4 v25+ team fixo)
            # F4 v25+ (Rafael 2026-05-27): team_id FIXO 143 (Rafael) para LF,
            # NAO derivado do user de execucao via G039. Decisao explicita
            # apos cirurgia AVULSO_FRASCO mostrar que team=143 e' o padrao
            # operacional desta skill (todas as POs LF inter-company nascem
            # com 143). Veja `_resolver_constants_fluxo_l3` para o by-pass
            # do G039 override apenas no destino LF.
            'team_id': 143,          # purchase.team Rafael LF (fixo F4 v25+)
            'payment_term_id': 2791, # 'A VISTA'
            'picking_type_id': 19,   # 'LF: Recebimento (LF)'
            'payment_provider_id': 38,  # G029 'SEM PAGAMENTO'
        },
    }

    # F3a v25+ (Rafael 2026-05-27): tipos diferentes em DFe vs PO.
    # Evidencia empirica: cirurgia AVULSO_FRASCO confirmou que tipo='compra'
    # no DFe permite `action_gerar_po_dfe` rodar normalmente (sem derivar
    # picking_type=64 errado); e em seguida `preencher_po` escreve
    # 'serv-industrializacao' que e' o tipo correto para invoice/journal
    # ENTIN + CFOP 1949 retorno industrializacao. Atualmente: passo 3 do
    # FLUXO L3 escreve 'compra' no DFe; passo 5 escreve 'serv-industrializacao'
    # na PO; passo 9 invoice herda da PO automaticamente.
    #
    # v27+ S4 EXPAND: mapeamento para TODAS direcoes da MATRIZ_INTERCOMPANY.
    # Padrao identificado em mineracao do operacoes_fiscais.py +
    # MATRIZ_INTERCOMPANY[op]['entrada'][(co, cd)]['l10n_br_tipo_pedido_entrada']:
    #
    #   dfe='compra' UNIVERSAL — destrava action_gerar_po_dfe (validacao
    #     empirica AVULSO_FRASCO v24+; tipo 'compra' no DFe e' interpretado
    #     pelo robo CIEL IT como "DFe de fornecedor a receber"  -> gera PO
    #     normalmente sem derivar picking_type errado).
    #   po=<derivado da MATRIZ>['entrada'][(co_origem, co_destino)]
    #     ['l10n_br_tipo_pedido_entrada'] — tipo correto p/ invoice ENTIN
    #     + CFOP correto via fiscal_position_id da entrada.
    #
    # ACAO_PARA_DIRECAO mapping (acao_decidida -> (tipo_op, co_origem, co_destino)):
    #   INDUSTRIALIZACAO_FB_LF: (industrializacao, 1, 5) -> entrada serv-industrializacao
    #   PERDA_LF_FB: (perda, 5, 1)                       -> entrada retorno
    #   DEV_LF_FB:  (dev-industrializacao, 5, 1)         -> entrada outro
    #   DEV_CD_LF:  (dev-industrializacao, 4, 5)         -> entrada retorno
    #   DEV_LF_CD:  (dev-industrializacao, 5, 4)         -> entrada outro
    #   DEV_FB_LF:  (dev-industrializacao, 1, 5)         -> entrada retorno
    #   TRANSFERIR_FB_CD: (transf-filial, 1, 4)          -> entrada transf-filial
    #   TRANSFERIR_CD_FB: (transf-filial, 4, 1)          -> entrada transf-filial
    L10N_BR_TIPO_PEDIDO_POR_ACAO: Dict[str, Dict[str, str]] = {
        # Industrializacao FB→LF (validado canary v20+ + cirurgia v24+)
        'INDUSTRIALIZACAO_FB_LF': {
            'dfe': 'compra',
            'po': 'serv-industrializacao',
        },
        # Perda LF→FB (CANDIDATE v27+ S4 — pendente canary REAL)
        'PERDA_LF_FB': {
            'dfe': 'compra',
            'po': 'retorno',
        },
        # Devolucao industrializacao (4 direcoes — CANDIDATE v27+ S4)
        'DEV_LF_FB': {
            'dfe': 'compra',
            'po': 'outro',
        },
        'DEV_CD_LF': {
            'dfe': 'compra',
            'po': 'retorno',
        },
        'DEV_LF_CD': {
            'dfe': 'compra',
            'po': 'outro',
        },
        'DEV_FB_LF': {
            'dfe': 'compra',
            'po': 'retorno',
        },
        # Transferencia entre filiais (2 direcoes — CANDIDATE v27+ S4)
        'TRANSFERIR_FB_CD': {
            'dfe': 'compra',
            'po': 'transf-filial',
        },
        'TRANSFERIR_CD_FB': {
            'dfe': 'compra',
            'po': 'transf-filial',
            # CR-v27+-Finding2-S4 (88% conf — RESOLVIDO 2026-05-27 Rafael):
            # TRANSFERIR_CD_FB JÁ ESTÁ em ACOES_ENTRADA_FB
            # (operacoes_fiscais.py:422 — ETAPA E legacy). Hoje é processado
            # via `executar_etapa_e` legacy (RecebimentoLf X→FB via Skill 7
            # V1 STRICT). Esta entry mapeada aqui (v27+ S4) NÃO é dead code:
            # destrava o caminho FLUXO L3 1.2.x para esta direção quando
            # v28+ S7 implementar `_executar_etapa_e_via_fluxo_l3`
            # (espelhando helper de ETAPA F, mas filtrando ACOES_ENTRADA_FB).
            # Quando ativo via `--usar-fluxo-l3-v19=True`, TRANSFERIR_CD_FB
            # (junto com PERDA_LF_FB + DEV_LF_FB + DEV_CD_LF) usará o
            # caminho A (buscar DFe via SEFAZ) ou B (criar manual via
            # XML saída) — decisão automática via `buscar_dfe`. Decisão
            # operacional Rafael 2026-05-27: "robô CIEL IT tem mesmo
            # defeito de atraso em QUALQUER tipo — CD→FB tbm tem que
            # funcionar pelo mesmo pattern de pesquisa+criar manual".
        },
    }

    def _resolver_constants_fluxo_l3(
        self, *, acao_decidida: str, company_destino: int,
    ) -> Optional[Dict[str, Any]]:
        """v20+ S3: resolve constants para `executar_fluxo_l3_1_2_x`.

        Retorna None se direcao nao suportada (caller marca NAO_SUPORTADA_V20).
        Minimo viavel: apenas INDUSTRIALIZACAO_FB_LF (validado canary).

        v23+ G039 (NF inter-company): substitui `team_id` STATIC (default
        do dict CONSTANTS_FLUXO_L3) pelo team do user de execucao atual
        (`self.odoo._uid`). Garante que `button_confirm`/`button_approve`
        nao trave a PO em state='to approve' por falta de aprovador. Cache
        local em `self._g039_team_cache[(user_id, company_id)]` evita N
        round-trips por onda (1 garantir_purchase_team por (user,company)).
        Em caso de falha do hook G039 (Odoo down, etc.), preserva `team_id`
        STATIC + loga WARNING — fallback compativel com comportamento legacy.
        """
        cdest_constants = self.CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO.get(
            company_destino
        )
        l10n_tipo_map = self.L10N_BR_TIPO_PEDIDO_POR_ACAO.get(acao_decidida)
        if not cdest_constants or not l10n_tipo_map:
            return None

        # F3a v25+: dois tipos por acao (dfe vs po). Compat-friendly:
        # apos refator do mapping (Dict -> Dict[str,str] com keys 'dfe'/'po')
        # caller (executar_fluxo_l3_1_2_x) decide qual usar em cada passo.
        resolved: Dict[str, Any] = {
            'company_destino': company_destino,
            'l10n_br_tipo_pedido_dfe': l10n_tipo_map['dfe'],
            'l10n_br_tipo_pedido_po': l10n_tipo_map['po'],
            **cdest_constants,  # team_id STATIC ja FIXO 143 para LF (F4 v25+)
        }

        # F4 v25+ (Rafael 2026-05-27): G039 override DESABILITADO para LF=5.
        # CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO[5]['team_id']=143 e' a
        # verdade absoluta para esta direcao (decisao explicita Rafael).
        # Demais destinos (FB=1, CD=4) ainda nao mapeados; quando forem,
        # decidir caso-a-caso se G039 dinamico ou STATIC fixo aplica.
        if company_destino != 5:
            # v23+ G039 — override team_id pelo team do user de execucao
            team_g039_id, team_g039_status = self._resolver_team_g039(
                company_id=company_destino,
            )
            if team_g039_id is not None:
                resolved['team_id'] = team_g039_id
                resolved['_team_g039_status'] = team_g039_status
            # else: fallback silencioso para team_id STATIC ja em `resolved`

        return resolved

    def _resolver_team_g039(
        self, *, company_id: int,
    ) -> Tuple[Optional[int], Optional[str]]:
        """v23+ G039: resolve team_id do user de execucao para `company_id`.

        Cache local em `self._g039_team_cache[(user_id, company_id)]`.
        Lazy-init do cache (atributo ausente -> cria vazio).

        Returns:
            (team_id, status) onde:
              status: 'OK_EXISTENTE' | 'CRIADO' | 'CACHE' | None (falha)
              team_id: int | None (None = fallback static do caller)
        """
        if not hasattr(self, '_g039_team_cache'):
            self._g039_team_cache = {}

        # Lazy auth — necessario para descobrir uid de execucao
        try:
            if not self.odoo._uid:
                self.odoo.authenticate()
        except Exception as e:
            logger.warning(
                f'_resolver_team_g039: auth Odoo falhou: {str(e)[:200]}'
            )
            return None, None

        uid = self.odoo._uid
        if not isinstance(uid, int) or uid <= 0:
            logger.warning(
                f'_resolver_team_g039: uid invalido ({uid!r})'
            )
            return None, None

        key = (uid, company_id)
        if key in self._g039_team_cache:
            return self._g039_team_cache[key], 'CACHE'

        try:
            from app.odoo.estoque.scripts.escrituracao import (
                EscrituracaoLfService,
            )
            escr_svc = EscrituracaoLfService(odoo=self.odoo)
            r = escr_svc.garantir_purchase_team(
                user_id=uid,
                company_id=company_id,
                dry_run=False,  # idempotente; CREATE so se necessario
            )
        except Exception as e:
            logger.warning(
                f'_resolver_team_g039 erro garantir_purchase_team '
                f'(user_id={uid}, company_id={company_id}): {str(e)[:200]}'
            )
            return None, None

        status = r.get('status')
        if status in ('OK_EXISTENTE', 'CRIADO'):
            team_id = r.get('team_id')
            if isinstance(team_id, int) and team_id > 0:
                self._g039_team_cache[key] = team_id
                return team_id, status
        logger.warning(
            f'_resolver_team_g039: garantir_purchase_team retornou '
            f'status={status} erro={r.get("erro")} '
            f'(user_id={uid}, company_id={company_id}) — fallback STATIC'
        )
        return None, None

    def _executar_etapa_f_via_fluxo_l3(
        self,
        *,
        ciclo: str,
        company_origem_id: Optional[int] = None,
        dry_run: bool = True,
        usuario: str = 'faturamento_pipeline',
        cod_produto: Optional[str] = None,
        t0: float,
    ) -> Dict[str, Any]:
        """v20+ S3: ETAPA F substituida pelo FLUXO L3 1.2.x.

        Itera invoices em F5e_SEFAZ_OK ∩ ACOES_ENTRADA_DESTINO_MANUAL,
        resolve constants por company_destino, invoca
        `executar_fluxo_l3_1_2_x` por invoice. company_destino nao
        suportado (constants nao mapeadas) retorna NAO_SUPORTADA_V20 e
        segue para proximo invoice.

        Minimo viavel: company_destino=5 (LF) validado canary REAL PROD
        2026-05-26 caso 627348 INDUSTRIALIZACAO_FB_LF. CD=4 e FB=1
        pendentes v21+.

        Returns:
            dict similar a executar_etapa_f legacy:
              status: EXECUTADO_OK | EXECUTADO_PARCIAL | DRY_RUN_OK |
                      SKIP_NENHUM_AJUSTE
              invoices_pendentes, invoices_ok, invoices_falha,
              invoices_nao_suportadas_v20, contadores
        """
        from app.odoo.models import AjusteEstoqueInventario  # lazy
        del AjusteEstoqueInventario  # nao usado diretamente; ja' carregado por _carregar_ajustes
        from app.utils.timezone import agora_utc_naive  # lazy F1 v25+

        ajustes = _carregar_ajustes(
            ciclo=ciclo,
            company_origem_id=company_origem_id,
            fases_pipeline=[FASE_F5e_OK],
            cod_produto=cod_produto,
            status_filter=['PROPOSTO', 'APROVADO', 'EXECUTADO'],
        )

        elegiveis: List = [
            a for a in ajustes
            if a.invoice_id_odoo
            and a.acao_decidida in ACOES_ENTRADA_DESTINO_MANUAL
        ]

        out: Dict[str, Any] = {
            'etapa': 'F',
            'modo': 'fluxo_l3_v19',
            'ciclo': ciclo,
            'company_origem_id': company_origem_id,
            'dry_run': dry_run,
            'ajustes_total': len(elegiveis),
            'invoices_pendentes': [],
            'invoices_ok': {},
            'invoices_falha': {},
            'invoices_nao_suportadas_v20': {},
            'contadores': {
                'ok': 0, 'falha': 0, 'nao_suportada_v20': 0,
            },
        }

        if not elegiveis:
            out['status'] = 'SKIP_NENHUM_AJUSTE'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        ajustes_por_invoice: Dict[int, List] = defaultdict(list)
        for a in elegiveis:
            ajustes_por_invoice[a.invoice_id_odoo].append(a)
        invoices_pendentes = list(ajustes_por_invoice.keys())
        out['invoices_pendentes'] = sorted(invoices_pendentes)

        # F1 v25+ (Rafael 2026-05-27): resolver product_id em batch para
        # construcao de `lotes_data` por invoice. Bug AVULSO_FRASCO: caminho
        # novo L3 v19+ chamava `executar_fluxo_l3_1_2_x` SEM `lotes_data`,
        # entao `lote_default='MIGRAÇÃO'` literal era aplicado a TODOS MLs
        # (saldo final em LF/Estoque/MIGRAÇÃO em vez do lote real do XML
        # SEFAZ). Fix espelha `executar_etapa_f` legacy v17.5 linhas
        # 3998-4018 — le `AjusteEstoqueInventario.lote_destino` da planilha
        # (definido pelo operador) e transforma vazio/'MIGRAÇÃO' em
        # `INV-{cod}-{YYYYMMDD}` (consistente com PROD 317306, 317316).
        cods_global = sorted({a.cod_produto for a in elegiveis})
        prod_cache: Dict[str, int] = self._resolver_pids_em_batch(cods_global)
        HOJE_F1 = agora_utc_naive().strftime('%Y%m%d')

        for invoice_id in invoices_pendentes:
            ajs = ajustes_por_invoice[invoice_id]
            acao = ajs[0].acao_decidida
            _, _, company_destino = ACAO_PARA_DIRECAO[acao]

            constants = self._resolver_constants_fluxo_l3(
                acao_decidida=acao, company_destino=company_destino,
            )
            if not constants:
                out['invoices_nao_suportadas_v20'][invoice_id] = (
                    f'acao={acao} company_destino={company_destino}: '
                    f'constants nao mapeadas em '
                    f'CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO. Pendencia v21+.'
                )
                out['contadores']['nao_suportada_v20'] += 1
                continue

            # v24.1+ FIX (regression v23+ G039): `_resolver_constants_fluxo_l3`
            # adiciona meta-keys prefixadas '_' (ex: '_team_g039_status') no
            # dict resolved. Filtrar ANTES do splat porque
            # `executar_fluxo_l3_1_2_x` tem assinatura strict sem **kwargs.
            # Sem filtro: TypeError: unexpected keyword argument
            # '_team_g039_status'. Descoberto v24+ canary REAL PROD operacao
            # avulsa INDUSTRIALIZACAO_FB_LF 37688un cod 210030009 — NF SEFAZ
            # autorizada (chave 35260561724241000178550010000945741007183640)
            # ficou pendente escrituracao por bug ETAPA F.
            public_constants = {
                k: v for k, v in constants.items() if not k.startswith('_')
            }

            # F1 v25+: construir `lotes_data` desta invoice (1 entry por
            # (pid, lote_destino) com qty agregada). Espelha legacy linhas
            # 3998-4018. Lote vazio/'MIGRAÇÃO' -> 'INV-{cod}-{YYYYMMDD}'.
            agg_lotes: Dict[Tuple[int, str], float] = defaultdict(float)
            for a in ajs:
                pid = prod_cache.get(a.cod_produto)
                if not pid:
                    logger.warning(
                        f'  F invoice {invoice_id}: sem product_id para '
                        f'{a.cod_produto}, pulando ajuste {a.id}'
                    )
                    continue
                lote_dest_raw = (a.lote_destino or '').strip()
                if not lote_dest_raw or lote_dest_raw == 'MIGRAÇÃO':
                    lote_dest = f'INV-{a.cod_produto}-{HOJE_F1}'
                else:
                    lote_dest = lote_dest_raw
                agg_lotes[(pid, lote_dest)] += float(abs(a.qtd_ajuste or 0))

            lotes_data_inv: List[Dict[str, Any]] = [
                {'product_id': pid, 'lote_nome': lote_dest, 'quantidade': qty}
                for (pid, lote_dest), qty in agg_lotes.items()
                if qty > 0
            ]
            # F1b: `lote_default` apenas como ULTIMO recurso caso ML do
            # picking referencie produto fora do AjusteEstoque (ex:
            # subproduto auto-criado pelo Odoo). Caller normal NAO depende
            # disso — lotes_data ja cobre todos os pids esperados.
            lote_default_inv = f'INV-FALLBACK-{HOJE_F1}'

            try:
                r = self.executar_fluxo_l3_1_2_x(
                    invoice_id_saida=invoice_id,
                    lotes_data=lotes_data_inv,
                    lote_default=lote_default_inv,
                    dry_run=dry_run,
                    **public_constants,
                )
            except Exception as e:
                logger.error(
                    f'  F invoice {invoice_id} acao={acao}: '
                    f'executar_fluxo_l3_1_2_x raise: {e}', exc_info=True,
                )
                out['invoices_falha'][invoice_id] = (
                    f'fluxo_l3_excecao: {str(e)[:200]}'
                )
                out['contadores']['falha'] += 1
                continue

            status_fluxo = r.get('status')
            if status_fluxo in ('FLUXO_OK', 'DRY_RUN_OK'):
                out['invoices_ok'][invoice_id] = {
                    'caminho': r.get('caminho'),
                    'po_id': r.get('po_id'),
                    'picking_id': r.get('picking_id'),
                    'invoice_id_destino': r.get('invoice_id'),
                }
                out['contadores']['ok'] += 1
                logger.info(
                    f'  F invoice {invoice_id} acao={acao}: '
                    f'{status_fluxo} caminho={r.get("caminho")} '
                    f'tempo={r.get("tempo_ms")}ms'
                )
            else:
                out['invoices_falha'][invoice_id] = (
                    f'{status_fluxo}: {r.get("erro") or "sem_erro_detalhado"}'
                )
                out['contadores']['falha'] += 1
                logger.error(
                    f'  F invoice {invoice_id} acao={acao}: '
                    f'{status_fluxo} erro={r.get("erro")}'
                )

        n_ok = out['contadores']['ok']
        n_falha = out['contadores']['falha']
        n_nao_suportada = out['contadores']['nao_suportada_v20']

        # CR-v20+-HIGH-2 (review code-reviewer 2026-05-26): nao_suportada_v20
        # conta como sinal de parcial — onda mista LF (ok) + CD (nao_suportada)
        # deve reportar EXECUTADO_PARCIAL, nao EXECUTADO_OK. Operador precisa
        # saber que parte da onda nao foi processada e fica para v21+.
        if n_falha == 0 and n_nao_suportada == 0 and n_ok > 0:
            out['status'] = (
                'DRY_RUN_OK' if dry_run else 'EXECUTADO_OK'
            )
        elif n_ok > 0:
            # ha ok + (falha ou nao_suportada) — parcial alerta operador
            out['status'] = 'EXECUTADO_PARCIAL'
        elif n_falha > 0:
            out['status'] = 'FALHA_ETAPA_F'
        else:
            # n_ok==0 + n_falha==0 + (n_nao_suportada >= 0)
            out['status'] = 'SKIP_NAO_SUPORTADA_V20'

        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    # ========================================================
    # v25+ S1 — Skill 8 ATOMICA L2 opt-in helpers (AP6 refator)
    # ========================================================
    # Substituem ETAPAs C+D legacy quando flag `--usar-skill8-atomica-v25`
    # esta ativa. Delegam aos 5 atomos de
    # `app/odoo/estoque/scripts/faturamento.py` (FaturamentoInvoiceService).
    # Default OFF preserva legacy = zero risco regressao. Ortogonal a
    # `--usar-fluxo-l3-v19` (que substitui ETAPAs E+F).
    #
    # Composicao (paridade contadores com legacy executar_etapa_c/d):
    #   ETAPA C: polling_invoice + validar_invoice_pos_robo (atomos 3+4)
    #   ETAPA D: transmitir_sefaz (atomo 5)
    #
    # Atomo 1 (validar_invoice_constants) NAO entra: ETAPA C nao tem
    # pre-cond legacy equivalente (orchestrator legacy nao valida constants).
    # Atomo 2 (liberar_faturamento) NAO entra: ja' eh executado em ETAPA B
    # legacy (passo 3 de `executar_etapa_b`). Migracao da ETAPA B para
    # liberar via Skill 8 ATOMICA pendente refator v26+ (escopo maior).

    def _executar_etapa_c_via_skill8_atomica(
        self,
        *,
        ciclo: str,
        company_origem_id: Optional[int] = None,
        dry_run: bool = True,
        usuario: str = 'faturamento_pipeline',
        cod_produto: Optional[str] = None,
        t0: float,
        timeout_polling: int = F5D_POLLING_TIMEOUT_S,
        poll_interval: int = F5D_POLL_INTERVAL_S,
        perfil_invoice_helpers: str = PERFIL_INVENTARIO_INTER_COMPANY,
    ) -> Dict[str, Any]:
        """v25+ S1 opt-in: ETAPA C substituida pelos atomos 3+4 da Skill 8
        ATOMICA L2 (`polling_invoice` + `validar_invoice_pos_robo`).

        Itera ajustes em F5c_LIBERADO ∩ picking_id_odoo, agrupa por
        picking_id (D2: 1 picking -> 1 invoice CIEL IT). Para cada
        picking, invoca `polling_invoice` para aguardar o robo CIEL IT
        criar `account.move`, depois `validar_invoice_pos_robo` para
        aplicar G029 + G007 + G034 via `_invoice_helpers`. Atualiza
        `fase_pipeline=F5d_INVOICE_GERADA` + `invoice_id_odoo` +
        `external_id_operacao` em todos ajustes do mesmo picking.

        Patterns codificados (paridade legacy `executar_etapa_c`):
          - D2: 1 picking -> 1 invoice CIEL IT (agrupa por picking_id)
          - D5: snapshot meta intra-atomo (atomo 3 polling_invoice)
          - D6: sub-etapas .5/.6/.7 try/except (atomo 4 validar_invoice_pos_robo)
          - F6 v15c: safe_session_get para re-fetch pos-commit (atomo 4)
          - F12: external_id_operacao por picking ate v17
          - G016: commit_resilient pos-polling

        Args:
            ciclo, company_origem_id, dry_run, usuario, cod_produto, t0:
                args padrao (espelha executar_etapa_c legacy).
            timeout_polling: segundos totais ate desistir (default 1800).
            poll_interval: segundos entre checks de cada picking (default 40).
            perfil_invoice_helpers: V1 = 'inventario-inter-company'.
                Outros raise NotImplementedError nos helpers.

        Returns:
            dict com paridade ESTRUTURAL legacy `executar_etapa_c`:
              etapa: 'C'
              modo: 'skill8_atomica_v25' (sinalizador para auditoria)
              status: EXECUTADO_ETAPA_C | DRY_RUN_OK_ETAPA_C |
                      EXECUTADO_PARCIAL_TIMEOUT | FALHA_TIMEOUT_TOTAL |
                      FALHA_PERFIL_INVALIDO | FALHA_COMMIT_PRE_POLLING |
                      SKIP_NENHUM_AJUSTE
              ajustes_total, ajustes_sem_picking (campos paridade legacy)
              pickings_pendentes, pickings_resolvidos, pickings_timeout
              sub_etapas: dict com f5d5/f5d6/f5d7 contadores agregados
              tempo_ms
        """
        from app.odoo.estoque.scripts.faturamento import (  # noqa: PLC0415
            FaturamentoInvoiceService,
        )
        from app.odoo.estoque.scripts._invoice_helpers import (  # noqa: PLC0415
            _validar_perfil,
        )
        from app.odoo.models import AjusteEstoqueInventario  # noqa: PLC0415

        # Carregar ajustes em F5c_LIBERADO (idempotencia via filtro de fase)
        ajustes = _carregar_ajustes(
            ciclo=ciclo,
            company_origem_id=company_origem_id,
            fases_pipeline=[FASE_F5c_OK],
            cod_produto=cod_produto,
        )
        # Defensivo: filtrar ajustes sem picking_id_odoo (anomalia)
        ajustes_validos: List = [a for a in ajustes if a.picking_id_odoo]
        ajustes_sem_picking: List = [
            a for a in ajustes if not a.picking_id_odoo
        ]
        if ajustes_sem_picking:
            logger.warning(
                f'ETAPA C (s8 v25+): {len(ajustes_sem_picking)} ajustes em '
                f'F5c_LIBERADO SEM picking_id_odoo (anomalia) — pulando: '
                f'{[a.id for a in ajustes_sem_picking[:5]]}'
            )

        out: Dict[str, Any] = {
            'etapa': 'C',
            'modo': 'skill8_atomica_v25',
            'ciclo': ciclo,
            'company_origem_id': company_origem_id,
            'dry_run': dry_run,
            'perfil_invoice_helpers': perfil_invoice_helpers,
            'ajustes_total': len(ajustes_validos),
            'ajustes_sem_picking': len(ajustes_sem_picking),
            'pickings_pendentes': [],
            'pickings_resolvidos': {},
            # CR-v27+-H2 (83% conf): separar timeout genuino (robo ainda
            # processando — operador faz resume) de excecao/falha do atomo
            # (operador investiga). Antes (v25+ S1 inicial), pickings_timeout
            # misturava ambos os casos, dificultando diagnostico.
            'pickings_timeout': [],          # robo CIEL IT nao criou invoice no timeout
            'pickings_falha_excecao': [],    # atomo polling_invoice raise OU status != 'OK'/'TIMEOUT'
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

        if not ajustes_validos:
            out['status'] = 'SKIP_NENHUM_AJUSTE'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # D2: agrupar por picking_id (1 picking -> 1 invoice CIEL IT)
        ajustes_por_pid: Dict[int, List] = defaultdict(list)
        for a in ajustes_validos:
            ajustes_por_pid[a.picking_id_odoo].append(a)
        pickings_pendentes = sorted(ajustes_por_pid.keys())
        out['pickings_pendentes'] = pickings_pendentes

        if dry_run:
            out['status'] = 'DRY_RUN_OK_ETAPA_C'
            out['observacao'] = (
                f'v25+ S1 dry-run: {len(pickings_pendentes)} pickings em '
                f'F5c_LIBERADO esperando invoice CIEL IT. Real-run usaria '
                f'Skill 8 ATOMICA polling_invoice + validar_invoice_pos_robo '
                f'(perfil={perfil_invoice_helpers!r}).'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # ============================================================
        # REAL-RUN: instanciar Skill 8 ATOMICA + loop pickings
        # ============================================================

        # CR-FIX R1F1 v16 (paridade): validar perfil ANTES do polling.
        try:
            _validar_perfil(perfil_invoice_helpers)
        except (NotImplementedError, ValueError) as e:
            out['status'] = 'FALHA_PERFIL_INVALIDO'
            out['erro'] = str(e)
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # G016 Opcao A: commit antes do polling longo
        if not _commit_resilient():
            logger.error(
                'F5d (s8 v25+) commit_resilient falhou ANTES do polling — '
                'abortando ETAPA C.'
            )
            out['status'] = 'FALHA_COMMIT_PRE_POLLING'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Instanciar Skill 8 ATOMICA (reusa picking_svc do orchestrator
        # para preservar conexao Odoo + retry config).
        svc = FaturamentoInvoiceService(
            odoo=self.odoo, picking_svc=self.picking_svc,
        )

        # Loop por picking — polling_invoice + validar_invoice_pos_robo
        for pid in pickings_pendentes:
            ajs_picking = ajustes_por_pid[pid]
            ajuste_ids = [a.id for a in ajs_picking]
            ajuste_id_primeiro = ajs_picking[0].id

            # Atomo 3: polling_invoice (delega Skill 5 LEGACY)
            try:
                r_poll = svc.polling_invoice(
                    picking_id=pid,
                    ajuste_ids=ajuste_ids,
                    ciclo=ciclo,
                    timeout_s=timeout_polling,
                    poll_interval_s=poll_interval,
                    dry_run=False,
                    usuario=usuario,
                )
            except Exception as e:
                logger.error(
                    f'  C s8 picking {pid}: polling_invoice raise: {e}',
                    exc_info=True,
                )
                # CR-v27+-H2: excecao = falha do atomo, NAO timeout
                out['pickings_falha_excecao'].append(pid)
                continue

            status_poll = r_poll.get('status')
            if status_poll == 'TIMEOUT':
                # Timeout genuino: robo CIEL IT nao criou invoice no tempo
                out['pickings_timeout'].append(pid)
                continue
            if status_poll != 'OK':
                logger.error(
                    f'  C s8 picking {pid}: polling_invoice status='
                    f'{status_poll!r} erro={r_poll.get("erro")}'
                )
                # CR-v27+-H2: status nao-OK/nao-TIMEOUT = falha do atomo
                out['pickings_falha_excecao'].append(pid)
                continue

            invoice_id = r_poll.get('invoice_id')
            if not invoice_id:
                logger.error(
                    f'  C s8 picking {pid}: polling_invoice OK mas sem '
                    f'invoice_id (anomalia atomo).'
                )
                # CR-v27+-H2: anomalia atomo (OK sem invoice_id) = falha
                out['pickings_falha_excecao'].append(pid)
                continue

            out['pickings_resolvidos'][pid] = invoice_id

            # Re-fetch ajustes + marcar F5d_INVOICE_GERADA (paridade legacy
            # linhas 2145-2173)
            ajustes_fresh: List = []
            for aid in ajuste_ids:
                af = safe_session_get(AjusteEstoqueInventario, aid)
                if af is not None:
                    ajustes_fresh.append(af)
            if not ajustes_fresh:
                logger.warning(
                    f'  C s8 picking {pid}: re-fetch ajustes vazio '
                    f'pos-polling (todos sumiram?). Skipping validar.'
                )
                continue

            external_id_f5d = (
                f'INV-{ciclo}-A{ajustes_fresh[0].id:06d}-'
                f'{FASE_F5d_OK}-{uuid.uuid4().hex[:8]}'
            )
            for aj in ajustes_fresh:
                aj.fase_pipeline = FASE_F5d_OK
                aj.invoice_id_odoo = invoice_id
                aj.external_id_operacao = external_id_f5d

            # Commit pos-polling antes das sub-etapas (paridade R1F3 v16)
            if not _commit_resilient():
                logger.error(
                    f'  C s8 picking {pid} commit pos-polling FALHOU. '
                    f'PULA validar_invoice_pos_robo (session sujo). '
                    f'Resume v25+ retentara.'
                )
                continue

            logger.info(
                f'F5d (s8) picking {pid} -> invoice {invoice_id} '
                f'({len(ajustes_fresh)} ajustes)'
            )

            # Atomo 4: validar_invoice_pos_robo (G029 + G007 + G034)
            try:
                r_val = svc.validar_invoice_pos_robo(
                    invoice_id=invoice_id,
                    ajuste_id_primeiro=ajuste_id_primeiro,
                    perfil=perfil_invoice_helpers,
                    ciclo=ciclo,
                    dry_run=False,
                    confirmar=True,
                    usuario=usuario,
                )
            except NotImplementedError:
                # Perfil invalido — propaga (anti-poison loop)
                raise
            except Exception as e:
                logger.error(
                    f'  C s8 invoice {invoice_id} validar_pos_robo raise: '
                    f'{e}', exc_info=True,
                )
                continue

            # Agregar sub_etapas (FaturamentoInvoiceService usa mesmas chaves)
            sub_etapas_atom = r_val.get('sub_etapas', {})
            for k in out['sub_etapas']:
                out['sub_etapas'][k] += sub_etapas_atom.get(k, 0)

        # Status final (paridade legacy + H2 v27+)
        n_resolved = len(out['pickings_resolvidos'])
        n_timeout = len(out['pickings_timeout'])
        n_falha = len(out['pickings_falha_excecao'])
        n_pendentes_inicial = len(pickings_pendentes)
        if n_resolved == n_pendentes_inicial:
            out['status'] = 'EXECUTADO_ETAPA_C'
        elif n_resolved > 0:
            # CR-v27+-H2: distinguir parcial por timeout vs parcial por falha
            if n_timeout > 0 and n_falha == 0:
                out['status'] = 'EXECUTADO_PARCIAL_TIMEOUT'
            elif n_falha > 0 and n_timeout == 0:
                out['status'] = 'EXECUTADO_PARCIAL_FALHA'
            else:  # ambos
                out['status'] = 'EXECUTADO_PARCIAL_MISTO'
        else:
            # 0 resolvidos — apenas timeouts OU apenas falhas OU mistura
            if n_falha == 0:
                out['status'] = 'FALHA_TIMEOUT_TOTAL'
            elif n_timeout == 0:
                out['status'] = 'FALHA_EXCECAO_TOTAL'
            else:
                out['status'] = 'FALHA_MISTO_TOTAL'

        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    def _executar_etapa_d_via_skill8_atomica(
        self,
        *,
        ciclo: str,
        company_origem_id: Optional[int] = None,
        dry_run: bool = True,
        confirmar_sefaz: bool = False,
        usuario: str = 'faturamento_pipeline',
        cod_produto: Optional[str] = None,
        t0: float,
        max_tentativas: int = F5E_PLAYWRIGHT_MAX_TENTATIVAS,
        intervalo_retry: int = F5E_PLAYWRIGHT_INTERVALO_RETRY_S,
    ) -> Dict[str, Any]:
        """v25+ S1 opt-in: ETAPA D substituida pelo atomo 5 da Skill 8
        ATOMICA L2 (`transmitir_sefaz`).

        Itera ajustes em F5d_INVOICE_GERADA, agrupa por invoice_id
        (D8.2: 1 invoice -> 1 transmissao SEFAZ). Para cada invoice
        invoca `transmitir_sefaz` (Playwright IRREVERSIVEL) que ja
        codifica intra-atomo:
          - D7: HARD_FAIL_CONFIG_ERRORS aborta batch
          - D8.3: idempotencia persistente (F5e_SEFAZ_OK / status=EXECUTADO)
          - D9: re-fetch via safe_session_get pos-Playwright
          - CRITICAL-1: commit POS-Playwright FALHA = NAO conta sucesso
          - MED C-1: situacao_nf != 'autorizado' registrado em erro_msg
          - MED C-2: cstat+xmotivo persistido em falha
          - G016: commit_resilient antes E depois

        O atomo atualiza diretamente `fase_pipeline=F5e_SEFAZ_OK` +
        `chave_nfe` + `status='EXECUTADO'` em todos ajustes do mesmo
        invoice (D-OPS-2b §7.5.2: propaga para TODOS).

        Args:
            ciclo, company_origem_id, dry_run, confirmar_sefaz, usuario,
            cod_produto, t0: args padrao (espelha executar_etapa_d legacy).
            max_tentativas: tentativas Playwright/NF (default 15).
            intervalo_retry: segundos entre tentativas (default 120).

        Returns:
            dict com paridade ESTRUTURAL legacy `executar_etapa_d`:
              etapa: 'D'
              modo: 'skill8_atomica_v25'
              status: EXECUTADO_ETAPA_D | DRY_RUN_OK_ETAPA_D |
                      EXECUTADO_PARCIAL | BLOQUEADO_SEM_CONFIRMAR_SEFAZ |
                      FALHA_CONFIG | SKIP_NENHUM_AJUSTE | FALHA_ETAPA_D
              ajustes_total, ajustes_sem_invoice
              invoices_pendentes, invoices_resolvidas (chave_nfe por inv),
              invoices_falha, invoices_skip
              contadores: {sucesso, falha, skip_idempotent}
        """
        from app.odoo.estoque.scripts.faturamento import (  # noqa: PLC0415
            FaturamentoInvoiceService,
        )

        # D18: real-run exige --confirmar-sefaz (2 niveis)
        if not dry_run and not confirmar_sefaz:
            return {
                'etapa': 'D',
                'modo': 'skill8_atomica_v25',
                'ciclo': ciclo,
                'status': 'BLOQUEADO_SEM_CONFIRMAR_SEFAZ',
                'erro': (
                    'ETAPA D (SEFAZ) e IRREVERSIVEL. Real-run exige '
                    '`--confirmar-sefaz` ALEM de `--confirmar`.'
                ),
                'tempo_ms': int((time.time() - t0) * 1000),
            }

        # Carregar ajustes em F5d_INVOICE_GERADA (idempotencia via fase)
        ajustes = _carregar_ajustes(
            ciclo=ciclo,
            company_origem_id=company_origem_id,
            fases_pipeline=[FASE_F5d_OK],
            cod_produto=cod_produto,
        )
        ajustes_validos: List = [a for a in ajustes if a.invoice_id_odoo]
        ajustes_sem_invoice: List = [
            a for a in ajustes if not a.invoice_id_odoo
        ]
        if ajustes_sem_invoice:
            logger.warning(
                f'ETAPA D (s8 v25+): {len(ajustes_sem_invoice)} ajustes em '
                f'F5d_INVOICE_GERADA SEM invoice_id_odoo (anomalia) — '
                f'pulando: {[a.id for a in ajustes_sem_invoice[:5]]}'
            )

        out: Dict[str, Any] = {
            'etapa': 'D',
            'modo': 'skill8_atomica_v25',
            'ciclo': ciclo,
            'company_origem_id': company_origem_id,
            'dry_run': dry_run,
            'confirmar_sefaz': confirmar_sefaz,
            'ajustes_total': len(ajustes_validos),
            'ajustes_sem_invoice': len(ajustes_sem_invoice),
            'invoices_pendentes': [],
            'invoices_resolvidas': {},
            'invoices_falha': {},
            'invoices_skip': [],
            'contadores': {
                'sucesso': 0,
                'falha': 0,
                'skip_idempotent': 0,
            },
        }

        if not ajustes_validos:
            out['status'] = 'SKIP_NENHUM_AJUSTE'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # D8.2: agrupar por invoice_id (1 invoice -> 1 transmissao SEFAZ)
        ajustes_por_invoice: Dict[int, List] = defaultdict(list)
        for a in ajustes_validos:
            ajustes_por_invoice[a.invoice_id_odoo].append(a)
        invoices_pendentes = sorted(ajustes_por_invoice.keys())
        out['invoices_pendentes'] = invoices_pendentes

        if dry_run:
            out['status'] = 'DRY_RUN_OK_ETAPA_D'
            out['observacao'] = (
                f'v25+ S1 dry-run: {len(invoices_pendentes)} invoices em '
                f'F5d_INVOICE_GERADA esperando transmissao SEFAZ. '
                f'Real-run usaria Skill 8 ATOMICA transmitir_sefaz '
                f'(Playwright IRREVERSIVEL, ~5-10min/NF; total estimado='
                f'{len(invoices_pendentes) * 5}-'
                f'{len(invoices_pendentes) * 10}min).'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # ============================================================
        # REAL-RUN: Skill 8 ATOMICA transmitir_sefaz por invoice
        # ============================================================

        # Instanciar service (reusa picking_svc para conexao Odoo)
        svc = FaturamentoInvoiceService(
            odoo=self.odoo, picking_svc=self.picking_svc,
        )

        for invoice_id in invoices_pendentes:
            ajs_invoice = ajustes_por_invoice[invoice_id]
            ajuste_ids = [a.id for a in ajs_invoice]

            try:
                r_sefaz = svc.transmitir_sefaz(
                    invoice_id=invoice_id,
                    ajuste_ids=ajuste_ids,
                    ciclo=ciclo,
                    max_tentativas=max_tentativas,
                    intervalo_retry=intervalo_retry,
                    dry_run=False,
                    confirmar_sefaz=True,  # ja' validado em D18 acima
                    usuario=usuario,
                )
            except Exception as e:
                logger.error(
                    f'  D s8 invoice {invoice_id}: transmitir_sefaz raise: '
                    f'{e}', exc_info=True,
                )
                out['invoices_falha'][invoice_id] = (
                    f'excecao: {str(e)[:200]}'
                )
                out['contadores']['falha'] += 1
                continue

            status_atom = r_sefaz.get('status')

            # D7: HARD_FAIL_CONFIG aborta batch (operador deve intervir)
            if status_atom == 'FALHA_CONFIG':
                logger.error(
                    f'  D s8 invoice {invoice_id}: FALHA_CONFIG '
                    f'{r_sefaz.get("erro")} — ABORTA BATCH.'
                )
                out['invoices_falha'][invoice_id] = (
                    f'FALHA_CONFIG: {r_sefaz.get("erro")}'
                )
                out['contadores']['falha'] += 1
                out['status'] = 'FALHA_CONFIG'
                out['erro_config'] = r_sefaz.get('erro_config') or r_sefaz.get('erro')
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out

            # D8.3: idempotencia persistente — invoice ja transmitida
            if status_atom == 'IDEMPOTENT_SKIP':
                chave = r_sefaz.get('chave_nfe')
                out['invoices_skip'].append(invoice_id)
                if chave:
                    out['invoices_resolvidas'][invoice_id] = chave
                out['contadores']['skip_idempotent'] += 1
                logger.info(
                    f'  D s8 invoice {invoice_id}: IDEMPOTENT_SKIP '
                    f'(chave_existente={chave!r})'
                )
                continue

            if status_atom == 'OK':
                chave = r_sefaz.get('chave_nfe')
                out['invoices_resolvidas'][invoice_id] = chave
                out['contadores']['sucesso'] += 1
                logger.info(
                    f'  D s8 invoice {invoice_id} -> SEFAZ OK '
                    f'(chave={chave}, ajustes={len(ajuste_ids)})'
                )
                continue

            # Outros (FALHA, FALHA_COMMIT_POS_SEFAZ_OK, FALHA_AJUSTES_VAZIOS,
            # BLOQUEADO_SEM_CONFIRMAR_SEFAZ — improvavel ja' que confirmar=True)
            erro_msg = r_sefaz.get('erro') or 'sem_erro_detalhado'
            out['invoices_falha'][invoice_id] = (
                f'{status_atom}: {erro_msg}'
            )
            out['contadores']['falha'] += 1
            logger.error(
                f'  D s8 invoice {invoice_id}: {status_atom} {erro_msg}'
            )

        # Status final (paridade legacy)
        n_sucesso = out['contadores']['sucesso']
        n_falha = out['contadores']['falha']
        n_skip = out['contadores']['skip_idempotent']
        n_pendentes = len(invoices_pendentes)

        if n_falha == 0 and (n_sucesso + n_skip) == n_pendentes:
            out['status'] = 'EXECUTADO_ETAPA_D'
        elif n_sucesso > 0 or n_skip > 0:
            out['status'] = 'EXECUTADO_PARCIAL'
        else:
            out['status'] = 'FALHA_ETAPA_D'

        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    def executar_etapa_e(
        self,
        *,
        ciclo: str,
        company_origem_id: Optional[int] = None,
        dry_run: bool = True,
        usuario: str = 'faturamento_pipeline',
        cod_produto: Optional[str] = None,
        usar_fluxo_l3_v19: bool = False,
    ) -> Dict[str, Any]:
        """ETAPA E v17.5 — DELEGA atomo Skill 7 `escriturando-odoo` por invoice.

        Para cada invoice_id distinto com `fase_pipeline=F5e_SEFAZ_OK` e
        `acao_decidida in ACOES_ENTRADA_FB`, invoca atomo Skill 7
        `EscrituracaoLfService.criar_recebimento_orchestrado(invoice_id, ajustes)`
        que encapsula:
          - G-RECLF-3 idempotencia via UK odoo_lf_invoice_id
          - HIGH-3 status='processando' RETOMA
          - HIGH-4 svc externo instanciado fresh
          - HIGH-5 produto_tracking via fetch batch
          - G-RECLF-2 transfer_status='erro' = PARCIAL OK
          - D17 ACAO_PARA_CFOP_ENTRADA 5xxx->1xxx
          - D9 re-fetch ajustes via safe_session_get
          - commit_resilient antes/dentro

        REGRA INVIOLAVEL 94 (v17.5 ARQ-2): orchestrator NAO recompoe logica
        de criar RecebimentoLf inline. Skill 7 = SO ENTRADA.

        Decisao 10.7 v17 (Rafael 2026-05-25 — preservada): SEQUENCIAL.
        Razao: RecebimentoLfOdooService NAO eh thread-safe (Redis state).
        Idempotencia perfeita permite recovery via --resume.

        Args:
            ciclo: identificador do ciclo.
            company_origem_id: filtro por company emissora (None = todas).
            dry_run: True (default) NAO cria RecebimentoLf; reporta planejamento.
            usuario: identificador para auditoria + executado_por do service.
            cod_produto: smoke/canary.

        Returns:
            dict com:
              status: DRY_RUN_OK_ETAPA_E | EXECUTADO_ETAPA_E |
                      EXECUTADO_PARCIAL | SKIP_NENHUM_AJUSTE | FALHA_COMMIT_PRE
              invoices_pendentes: lista de invoice_ids esperados
              invoices_ok: dict {invoice_id: rec_id}
              invoices_falha: dict {invoice_id: erro}
              invoices_skip: lista de invoice_ids ja processados
              invoices_retomados: lista (HIGH-3 RETOMADO)
              contadores: {ok, falha, skip, retomado, parcial_fb_ok_transfer_erro}
        """
        # Lazy imports — Skill 7 service + helpers
        from app.odoo.estoque.scripts.escrituracao import (  # noqa: PLC0415
            EscrituracaoLfService,
        )

        t0 = time.time()

        # FIX v20+ S3: opt-in `--usar-fluxo-l3-v19` skip ETAPA E legacy.
        # ETAPA E LEGACY processa ACOES_ENTRADA_FB (LF/CD -> FB destino).
        # Minimo viavel S3: company_destino=FB(1) NAO esta em
        # CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO (so LF=5 validado canary).
        # ETAPA E via fluxo L3 fica pendente v21+ quando FB constants
        # forem mapeadas+validadas. Default flag=False preserva legacy.
        if usar_fluxo_l3_v19:
            return {
                'etapa': 'E',
                'ciclo': ciclo,
                'company_origem_id': company_origem_id,
                'dry_run': dry_run,
                'status': 'SKIP_NAO_SUPORTADA_V20_FLUXO_L3',
                'observacao': (
                    'ETAPA E (entrada FB via Skill 7 V1 STRICT) NAO substituida '
                    'pelo FLUXO L3 1.2.x em v20+. Constants para company_destino='
                    '1 (FB) nao mapeadas em CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO. '
                    'Pendencia v21+: validar canary + mapear constants FB.'
                ),
                'tempo_ms': int((time.time() - t0) * 1000),
            }

        # Carregar ajustes em F5e_SEFAZ_OK
        ajustes = _carregar_ajustes(
            ciclo=ciclo,
            company_origem_id=company_origem_id,
            fases_pipeline=[FASE_F5e_OK],
            cod_produto=cod_produto,
            # F5e marca status='EXECUTADO' (do service legado L1268), entao
            # incluir EXECUTADO no filtro de status (D-OPS-1b varchar(20))
            status_filter=['PROPOSTO', 'APROVADO', 'EXECUTADO'],
        )

        # L17: filtrar ACOES_ENTRADA_FB
        ajustes_entrada_fb: List = [
            a for a in ajustes
            if a.invoice_id_odoo and a.chave_nfe
            and a.acao_decidida in ACOES_ENTRADA_FB
        ]

        # Log dos descartados (sentido FB->X — entrada destino manual ETAPA F)
        descartados: List = [
            a for a in ajustes
            if a.invoice_id_odoo and a.chave_nfe
            and a.acao_decidida not in ACOES_ENTRADA_FB
        ]
        if descartados:
            cods_desc = sorted({a.cod_produto for a in descartados})
            logger.info(
                f'  [L17] {len(descartados)} ajustes pulados (sentido FB->X, '
                f'entrada destino e manual ETAPA F): {len(cods_desc)} '
                f'produtos, acoes={sorted({a.acao_decidida for a in descartados})}'
            )

        out: Dict[str, Any] = {
            'etapa': 'E',
            'ciclo': ciclo,
            'company_origem_id': company_origem_id,
            'dry_run': dry_run,
            'ajustes_total': len(ajustes_entrada_fb),
            'ajustes_descartados_fb_x': len(descartados),
            'invoices_pendentes': [],
            'invoices_ok': {},
            'invoices_falha': {},
            'invoices_skip': [],
            'invoices_retomados': [],
            'contadores': {
                'ok': 0,
                'falha': 0,
                'skip': 0,
                'retomado': 0,
                'parcial_fb_ok_transfer_erro': 0,
            },
        }

        if not ajustes_entrada_fb:
            out['status'] = 'SKIP_NENHUM_AJUSTE'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Agrupar por invoice_id (1 NF = 1 RecebimentoLf)
        ajustes_por_invoice: Dict[int, List] = defaultdict(list)
        for a in ajustes_entrada_fb:
            ajustes_por_invoice[a.invoice_id_odoo].append(a)
        invoices_pendentes = list(ajustes_por_invoice.keys())
        out['invoices_pendentes'] = sorted(invoices_pendentes)

        if dry_run:
            out['status'] = 'DRY_RUN_OK_ETAPA_E'
            out['observacao'] = (
                f'v17.5 dry-run: {len(invoices_pendentes)} RecebimentoLf '
                f'seriam criados via atomo Skill 7 '
                f'(EscrituracaoLfService.criar_recebimento_orchestrado). '
                f'Tempo estimado real: {len(invoices_pendentes) * 30}-'
                f'{len(invoices_pendentes) * 60}min (sequencial, '
                f'decisao 10.7). Recovery via --apenas-etapa=E.'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # ============================================================
        # REAL-RUN: SEQUENCIAL — DELEGA atomo Skill 7 por invoice
        # ============================================================

        # G016 commit antes do loop longo
        if not _commit_resilient():
            logger.error(
                'F-E commit_resilient falhou ANTES do loop — '
                'abortando ETAPA E.'
            )
            out['status'] = 'FALHA_COMMIT_PRE'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Instanciar atomo Skill 7 (uma vez para a ETAPA toda; svc externo
        # interno e' fresh por invocacao via HIGH-4 do proprio atomo).
        escrituracao_svc = EscrituracaoLfService(odoo=self.odoo)

        for invoice_id in invoices_pendentes:
            ajustes_inv = ajustes_por_invoice[invoice_id]

            try:
                resultado = escrituracao_svc.criar_recebimento_orchestrado(
                    invoice_id=invoice_id,
                    ajustes=ajustes_inv,
                    ciclo=ciclo,
                    usuario=usuario,
                    dry_run=False,
                )
            except Exception as e:
                logger.error(
                    f'  E invoice {invoice_id}: atomo Skill 7 raise: {e}',
                    exc_info=True,
                )
                out['invoices_falha'][invoice_id] = (
                    f'atomo_skill7_excecao: {str(e)[:200]}'
                )
                out['contadores']['falha'] += 1
                continue

            status_atomo = resultado.get('status')
            rec_id = resultado.get('rec_id')

            if status_atomo == 'CRIADO':
                out['invoices_ok'][invoice_id] = rec_id
                out['contadores']['ok'] += 1
                logger.info(
                    f'  E invoice {invoice_id}: CRIADO rec={rec_id} '
                    f'inv_fb={resultado.get("odoo_invoice_id_fb")} '
                    f'transfer={resultado.get("transfer_status")} '
                    f'tempo={resultado.get("tempo_ms")}ms'
                )
            elif status_atomo == 'RETOMADO':
                # HIGH-3: contado como sucesso (RecLf foi retomado e processado)
                out['invoices_ok'][invoice_id] = rec_id
                out['invoices_retomados'].append(invoice_id)
                out['contadores']['ok'] += 1
                out['contadores']['retomado'] += 1
                logger.info(
                    f'  E invoice {invoice_id}: RETOMADO rec={rec_id} '
                    f'(HIGH-3 recovery)'
                )
            elif status_atomo == 'IDEMPOTENT_PROCESSADO':
                out['invoices_skip'].append(invoice_id)
                out['contadores']['skip'] += 1
                logger.info(
                    f'  E invoice {invoice_id}: SKIP G-RECLF-3 '
                    f'rec={rec_id} ja processado'
                )
            elif status_atomo == 'PARCIAL':
                # G-RECLF-2: FB OK mas transfer FASE 6+7 erro
                out['invoices_ok'][invoice_id] = rec_id
                out['contadores']['ok'] += 1
                out['contadores']['parcial_fb_ok_transfer_erro'] += 1
                logger.warning(
                    f'  E invoice {invoice_id}: PARCIAL rec={rec_id} '
                    f'(G-RECLF-2 transfer_status=erro aceito)'
                )
            elif status_atomo == 'FALHA':
                out['invoices_falha'][invoice_id] = (
                    resultado.get('erro') or 'atomo_falha_sem_erro'
                )
                out['contadores']['falha'] += 1
                logger.error(
                    f'  E invoice {invoice_id}: FALHA atomo Skill 7 - '
                    f'erro={resultado.get("erro")}'
                )
            else:  # SKIP_AJUSTES_VAZIOS ou outro
                logger.warning(
                    f'  E invoice {invoice_id}: status atomo desconhecido='
                    f'{status_atomo!r}, contando como falha'
                )
                out['invoices_falha'][invoice_id] = (
                    f'atomo_status_desconhecido: {status_atomo}'
                )
                out['contadores']['falha'] += 1

        # Status agregado
        n_ok = out['contadores']['ok']
        n_falha = out['contadores']['falha']
        if n_falha == 0:
            out['status'] = 'EXECUTADO_ETAPA_E'
        elif n_ok > 0 or out['contadores']['skip'] > 0:
            out['status'] = 'EXECUTADO_PARCIAL'
        else:
            out['status'] = 'FALHA_ETAPA_E'

        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    def executar_etapa_f(
        self,
        *,
        ciclo: str,
        company_origem_id: Optional[int] = None,
        dry_run: bool = True,
        usuario: str = 'faturamento_pipeline',
        cod_produto: Optional[str] = None,
        auto_confirma_direcao_nova: bool = False,
        usar_fluxo_l3_v19: bool = False,
    ) -> Dict[str, Any]:
        """ETAPA F v17.5 — picking entrada manual destino FB->{LF,CD}.

        Para cada invoice_id distinto com `fase_pipeline=F5e_SEFAZ_OK` e
        `acao_decidida in ACOES_ENTRADA_DESTINO_MANUAL`, **DELEGA** para
        atomo Skill 5 v15a `picking_svc.criar_picking_entrada_destino_manual`
        que codifica G023 (company_id em moves) + G011 (lot_name/quantity)
        + G019/G020 (state check) + idempotencia via origin EXATO.

        Pattern arquitetural (decisao 10.6 v14a-fix — Rafael):
          Toda operacao em stock.picking passa por StockPickingService.
          Orchestrator NUNCA chama odoo.create('stock.picking') direto.

        EXPANSAO v17.5 (decisao Rafael Q1=C — 2026-05-26):
          - INDUSTRIALIZACAO_FB_LF: validado PROD (317306, 317316). LF=19.
            location_origem=26489 Em Transito Industrializacao.
            ✅ executa sempre (sem flag).
          - DEV_FB_LF: canary fiscal sem precedente PROD. LF=19 reusado;
            fp 86 assumido (sem precedente — pode precisar ajuste pos-canary).
            location_origem=26489 (assumido). 🟡 exige
            `auto_confirma_direcao_nova=True` em real-run.
          - TRANSFERIR_FB_CD: discovery Odoo 2026-05-26 — PT 50
            CD/IN/INTER (NACOM/CD/IN/INTER/0000N); src=6 Em Transito Filiais;
            dest=32 CD/Estoque; partner=NACOM GOYA - CD (34). 🟡 exige
            `auto_confirma_direcao_nova=True` em real-run.

        Patterns codificados (do script 09 L1428-1688):
          - L17 Filtra ACOES_ENTRADA_DESTINO_MANUAL (sentidos FB->X)
          - Agrupa por invoice_id (1 NF = 1 picking entrada)
          - Idempotencia via origin `INV-{ciclo}-ENTRADA-{label}-NF{invoice_id}`
          - Pre-check: `account.move.state='posted'` ANTES de criar picking
          - Lote `MIGRAÇÃO`/vazio -> `INV-{cod}-{YYYYMMDD}` (consistente com
            317306, 317316 validados em PROD)
          - F5f_ENTRADA_OK marca fase apos picking done

        Args:
            ciclo: identificador do ciclo.
            company_origem_id: filtro por company emissora (None = todas).
            dry_run: True (default) NAO cria picking; reporta planejamento.
            usuario: identificador para auditoria.
            cod_produto: smoke/canary.
            auto_confirma_direcao_nova: v17.5 (default False) — flag explicita
                para habilitar DEV_FB_LF + TRANSFERIR_FB_CD em real-run. Dry-run
                sempre planeja TODAS as direcoes (informacional). Em real-run,
                direcoes canary sem a flag retornam `direcao_canary_bloqueada`.

        Returns:
            dict com:
              status: DRY_RUN_OK_ETAPA_F | EXECUTADO_ETAPA_F |
                      EXECUTADO_PARCIAL | SKIP_NENHUM_AJUSTE
              invoices_pendentes: lista de invoice_ids esperados
              invoices_ok: dict {invoice_id: picking_id}
              invoices_skip: dict {invoice_id: 'IDEMPOTENT_DONE'|...}
              invoices_falha: dict {invoice_id: erro}
              invoices_canary_bloqueado: dict {invoice_id: motivo} — v17.5
              contadores: {ok, skip, falha, canary_bloqueado, not_implemented_direcao}
        """
        from app import db  # lazy
        from app.odoo.models import AjusteEstoqueInventario  # lazy
        from app.odoo.constants.picking_types import (  # lazy v17.5
            ACOES_ENTRADA_DESTINO_MANUAL_CANARY,
            LOCATION_ORIGEM_POR_DIRECAO,
        )
        from app.utils.timezone import agora_utc_naive  # lazy (banido datetime.utcnow)

        t0 = time.time()

        # FIX v20+ S3: opt-in `--usar-fluxo-l3-v19` substitui ETAPA F legacy
        # (Skill 5 atomo `criar_picking_entrada_destino_manual` tampao AP2)
        # pelo FLUXO L3 1.2.x via `executar_fluxo_l3_1_2_x`. Minimo viavel:
        # apenas company_destino=5 (LF) validado em canary REAL PROD
        # 2026-05-26 caso 627348 INDUSTRIALIZACAO_FB_LF; demais direcoes
        # (4=CD) retornam NAO_SUPORTADA_V20 e seguem para proximo invoice
        # (caller decide se aborta ou continua).
        # Default flag=False preserva 100% comportamento legacy.
        if usar_fluxo_l3_v19:
            return self._executar_etapa_f_via_fluxo_l3(
                ciclo=ciclo,
                company_origem_id=company_origem_id,
                dry_run=dry_run,
                usuario=usuario,
                cod_produto=cod_produto,
                t0=t0,
            )

        # Carregar ajustes em F5e_SEFAZ_OK
        ajustes = _carregar_ajustes(
            ciclo=ciclo,
            company_origem_id=company_origem_id,
            fases_pipeline=[FASE_F5e_OK],
            cod_produto=cod_produto,
            status_filter=['PROPOSTO', 'APROVADO', 'EXECUTADO'],
        )

        # Filtrar ACOES_ENTRADA_DESTINO_MANUAL (FB->X)
        elegiveis: List = [
            a for a in ajustes
            if a.invoice_id_odoo
            and a.acao_decidida in ACOES_ENTRADA_DESTINO_MANUAL
        ]

        out: Dict[str, Any] = {
            'etapa': 'F',
            'ciclo': ciclo,
            'company_origem_id': company_origem_id,
            'dry_run': dry_run,
            'auto_confirma_direcao_nova': auto_confirma_direcao_nova,
            'ajustes_total': len(elegiveis),
            'invoices_pendentes': [],
            'invoices_ok': {},
            'invoices_skip': {},
            'invoices_falha': {},
            'invoices_canary_bloqueado': {},
            'contadores': {
                'ok': 0,
                'skip': 0,
                'falha': 0,
                'canary_bloqueado': 0,
                'not_implemented_direcao': 0,
            },
        }

        if not elegiveis:
            out['status'] = 'SKIP_NENHUM_AJUSTE'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Agrupar por invoice_id (1 NF = 1 picking entrada)
        ajustes_por_invoice: Dict[int, List] = defaultdict(list)
        for a in elegiveis:
            ajustes_por_invoice[a.invoice_id_odoo].append(a)
        invoices_pendentes = list(ajustes_por_invoice.keys())
        out['invoices_pendentes'] = sorted(invoices_pendentes)

        if dry_run:
            # Reportar planejamento por invoice
            planejamento = []
            invoices_canary = 0
            for inv_id, ajs in ajustes_por_invoice.items():
                acao = ajs[0].acao_decidida
                _, _, co_dest = ACAO_PARA_DIRECAO[acao]
                label = COMPANY_LABEL_ENTRADA.get(co_dest, str(co_dest))
                cods = sorted({a.cod_produto for a in ajs})
                qty_total = sum(
                    float(abs(a.qtd_ajuste or 0)) for a in ajs
                )
                eh_canary = acao in ACOES_ENTRADA_DESTINO_MANUAL_CANARY
                if eh_canary:
                    invoices_canary += 1
                planejamento.append({
                    'invoice_id': inv_id,
                    'acao': acao,
                    'destino_label': label,
                    'company_destino_id': co_dest,
                    'cods': cods,
                    'qty_total': qty_total,
                    'canary_v175': eh_canary,
                })
            out['status'] = 'DRY_RUN_OK_ETAPA_F'
            out['planejamento'] = planejamento
            out['invoices_canary_count'] = invoices_canary
            out['observacao'] = (
                f'v17.5 dry-run: {len(invoices_pendentes)} pickings entrada '
                f'destino seriam criados (DELEGADO Skill 5 atomo). '
                f'{invoices_canary} sao direcoes canary (DEV_FB_LF / '
                f'TRANSFERIR_FB_CD) — exigem '
                f'`auto_confirma_direcao_nova=True` em real-run.'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # ============================================================
        # REAL-RUN: DELEGADO Skill 5 v15a
        # ============================================================

        # G016 commit antes do loop
        if not _commit_resilient():
            logger.error(
                'F-F commit_resilient falhou ANTES do loop — '
                'abortando ETAPA F.'
            )
            out['status'] = 'FALHA_COMMIT_PRE'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # HIGH-6 v17 (Reviewer 3 conf 80): HOJE deve ser calculado DENTRO
        # do loop. Runs longas (100+ invoices XML-RPC lento) podem cruzar
        # meia-noite; lote `INV-{cod}-{YYYYMMDD}` da invoice deve ter a
        # data do MOMENTO de criacao (idempotencia: re-run no dia seguinte
        # gera `INV-{cod}-{D+1}` para os ajustes recem-tocados; ja' criados
        # ficam consistentes com o lote do dia em que rodaram).
        for invoice_id in invoices_pendentes:
            inicio_inv = time.time()
            HOJE = agora_utc_naive().strftime('%Y%m%d')
            ajs = ajustes_por_invoice[invoice_id]
            acao = ajs[0].acao_decidida
            _, company_origem, company_destino = ACAO_PARA_DIRECAO[acao]

            # v17.5 CANARY GUARD: direcao nova exige --auto-confirma-direcao-nova
            if (acao in ACOES_ENTRADA_DESTINO_MANUAL_CANARY
                    and not auto_confirma_direcao_nova):
                logger.warning(
                    f'  F invoice {invoice_id} acao={acao}: '
                    f'direcao CANARY v17.5 sem precedente PROD. Bloqueada por '
                    f'falta de flag auto_confirma_direcao_nova=True. '
                    f'Use dry-run para planejamento; real-run exige flag.'
                )
                out['invoices_canary_bloqueado'][invoice_id] = (
                    f'direcao_canary_bloqueada: acao={acao} '
                    f'(usar auto_confirma_direcao_nova=True)'
                )
                out['contadores']['canary_bloqueado'] += 1
                continue

            # Validar direcao mapeada em PICKING_TYPE_ENTRADA_DESTINO_MANUAL
            # (v17.5 PT 50 CD adicionado p/ TRANSFERIR_FB_CD)
            picking_type_id = PICKING_TYPE_ENTRADA_DESTINO_MANUAL.get(
                company_destino
            )
            location_dest = COMPANY_LOCATIONS.get(company_destino)
            company_label = COMPANY_LABEL_ENTRADA.get(
                company_destino, str(company_destino)
            )

            if not picking_type_id or not location_dest:
                logger.warning(
                    f'  F invoice {invoice_id} acao={acao}: '
                    f'PICKING_TYPE_ENTRADA_DESTINO_MANUAL sem entrada '
                    f'para company_destino={company_destino}. '
                    f'Validas: {sorted(PICKING_TYPE_ENTRADA_DESTINO_MANUAL.keys())}'
                )
                out['invoices_falha'][invoice_id] = (
                    f'direcao_nao_implementada: acao={acao} '
                    f'company_destino={company_destino}'
                )
                out['contadores']['not_implemented_direcao'] += 1
                out['contadores']['falha'] += 1
                continue

            # v17.5: location_origem varia por direcao (antes era hardcode 26489)
            location_origem = LOCATION_ORIGEM_POR_DIRECAO.get(acao)
            if location_origem is None:
                logger.warning(
                    f'  F invoice {invoice_id} acao={acao}: '
                    f'LOCATION_ORIGEM_POR_DIRECAO sem entrada. '
                    f'Validas: {sorted(LOCATION_ORIGEM_POR_DIRECAO.keys())}'
                )
                out['invoices_falha'][invoice_id] = (
                    f'location_origem_nao_mapeada: acao={acao}'
                )
                out['contadores']['not_implemented_direcao'] += 1
                out['contadores']['falha'] += 1
                continue

            # Pre-check: invoice deve estar posted (SEFAZ-OK)
            try:
                inv_data = self.odoo.read(
                    'account.move', [invoice_id],
                    ['state', 'l10n_br_situacao_nf'],
                )
                if not inv_data:
                    logger.error(
                        f'  F invoice {invoice_id} sumiu do Odoo, pulando'
                    )
                    out['invoices_falha'][invoice_id] = 'invoice_sumiu_odoo'
                    out['contadores']['falha'] += 1
                    continue
                inv = inv_data[0]
                if inv['state'] != 'posted':
                    logger.warning(
                        f'  F invoice {invoice_id} state={inv["state"]} '
                        f'!= posted. Pulando.'
                    )
                    out['invoices_falha'][invoice_id] = (
                        f'invoice_nao_posted (state={inv["state"]})'
                    )
                    out['contadores']['falha'] += 1
                    continue
                # CRITICAL-4 v17 (Reviewer 3 conf 92): validar situacao_nf
                # SEFAZ. Sem este check, NF cancelada na SEFAZ (mas state
                # ainda 'posted' no Odoo ate proximo ciclo de sync) criaria
                # picking de entrada para NF invalidada -> saldo fantasma.
                situacao_nf = inv.get('l10n_br_situacao_nf')
                if situacao_nf and situacao_nf != 'autorizado':
                    logger.warning(
                        f'  F invoice {invoice_id} situacao_nf='
                        f'{situacao_nf!r} != autorizado. Pulando '
                        f'(picking entrada NAO criado).'
                    )
                    out['invoices_falha'][invoice_id] = (
                        f'invoice_nao_autorizado_sefaz '
                        f'(situacao_nf={situacao_nf!r})'
                    )
                    out['contadores']['falha'] += 1
                    continue
            except Exception as e:
                logger.error(
                    f'  F invoice {invoice_id}: erro ler state invoice: {e}'
                )
                out['invoices_falha'][invoice_id] = (
                    f'erro_ler_invoice: {str(e)[:100]}'
                )
                out['contadores']['falha'] += 1
                continue

            # Resolver product_id e agregar qty por (pid, lote_destino)
            cods = sorted({a.cod_produto for a in ajs})
            prod_cache = self._resolver_pids_em_batch(cods)

            agg: Dict[Tuple[int, str], float] = defaultdict(float)
            for a in ajs:
                pid = prod_cache.get(a.cod_produto)
                if not pid:
                    logger.warning(
                        f'    sem product_id para {a.cod_produto}, '
                        f'pulando ajuste {a.id}'
                    )
                    continue
                lote_dest_raw = (a.lote_destino or '').strip()
                # Lote MIGRAÇÃO/vazio vira INV-{cod}-{YYYYMMDD} consistente
                # com 317316 e G014 do v16
                if not lote_dest_raw or lote_dest_raw == 'MIGRAÇÃO':
                    lote_dest = f'INV-{a.cod_produto}-{HOJE}'
                else:
                    lote_dest = lote_dest_raw
                agg[(pid, lote_dest)] += float(abs(a.qtd_ajuste or 0))

            if not agg:
                logger.warning(
                    f'  F invoice {invoice_id}: agg vazio (0 produtos com '
                    f'pid+qty>0), pulando'
                )
                # HIGH-7 v17 (Reviewer 3 conf 82): registrar auditoria por
                # ajuste para nao silenciar bug sistematico de
                # _resolver_pids_em_batch. Sem auditoria, orchestrator
                # loopearia silenciosamente em re-runs sem rastro no DB.
                for a in ajs:
                    af = safe_session_get(AjusteEstoqueInventario, a.id)
                    if af is not None:
                        _registrar_auditoria(
                            ajuste_id=af.id, ciclo=ciclo, fase='F-F',
                            acao='entrada_destino_manual',
                            modelo_odoo='stock.picking',
                            status='SKIP_AGG_VAZIO',
                            erro_msg=(
                                f'agg vazio para invoice {invoice_id} '
                                f'(nenhum product_id resolvido)'
                            ),
                            executado_por=usuario,
                        )
                _commit_resilient()
                out['invoices_falha'][invoice_id] = 'agg_vazio'
                out['contadores']['falha'] += 1
                continue

            # Montar moves_data para o atomo (formato compativel com
            # criar_picking_entrada_destino_manual)
            moves_data = [
                {
                    'product_id': pid,
                    'quantity': qty,
                    'lot_dest_name': lote_dest,
                }
                for (pid, lote_dest), qty in agg.items()
                if qty > 0
            ]

            # Origin idempotente (consistente com 317306, 317316 do script 09)
            origin = (
                f'INV-{ciclo}-ENTRADA-{company_label}-NF{invoice_id}'
            )

            # DELEGA para atomo Skill 5 v15a
            # v17.5: location_origem varia por direcao (antes hardcode 26489)
            try:
                resultado = self.picking_svc.criar_picking_entrada_destino_manual(
                    company_destino_id=company_destino,
                    location_origem_id=location_origem,
                    location_destino_id=location_dest,
                    moves_data=moves_data,
                    picking_type_id=picking_type_id,
                    origin=origin,
                )
                tempo_ms_inv = int((time.time() - inicio_inv) * 1000)
                picking_id = resultado.get('picking_id')
                status_atom = resultado.get('status')
                state_atom = resultado.get('state')

                # F6 v15c: re-fetch ajustes pos-atomo (Odoo XML-RPC pode demorar)
                ajustes_post: List = []
                for a in ajs:
                    af = safe_session_get(AjusteEstoqueInventario, a.id)
                    if af is not None:
                        ajustes_post.append(af)

                if status_atom in ('CRIADO', 'IDEMPOTENT_DONE'):
                    # Sucesso: marcar F5f_ENTRADA_OK em todos ajustes
                    for aj in ajustes_post:
                        aj.fase_pipeline = FASE_F5f_OK
                        _registrar_auditoria(
                            ajuste_id=aj.id, ciclo=ciclo, fase=FASE_F5f_OK,
                            acao='entrada_destino_manual',
                            modelo_odoo='stock.picking',
                            status='SUCESSO' if status_atom == 'CRIADO' else 'SKIPPED_IDEMPOTENT',
                            odoo_id=picking_id,
                            resposta=resultado,
                            tempo_ms=tempo_ms_inv, executado_por=usuario,
                        )
                    _commit_resilient()
                    if status_atom == 'CRIADO':
                        out['invoices_ok'][invoice_id] = picking_id
                        out['contadores']['ok'] += 1
                        logger.info(
                            f'  F invoice {invoice_id}: picking '
                            f'{picking_id} criado state=done '
                            f'(company={company_destino}, {len(moves_data)} moves)'
                        )
                    else:  # IDEMPOTENT_DONE
                        out['invoices_skip'][invoice_id] = (
                            f'IDEMPOTENT_DONE picking_id={picking_id}'
                        )
                        out['contadores']['skip'] += 1
                        logger.info(
                            f'  F invoice {invoice_id}: picking '
                            f'{picking_id} ja done (skip)'
                        )
                elif status_atom == 'IDEMPOTENT_OTHER':
                    # Picking existe mas state != done — investigacao manual
                    logger.warning(
                        f'  F invoice {invoice_id}: picking {picking_id} '
                        f'IDEMPOTENT_OTHER state={state_atom}. '
                        f'Investigacao manual necessaria.'
                    )
                    out['invoices_falha'][invoice_id] = (
                        f'IDEMPOTENT_OTHER picking_id={picking_id} '
                        f'state={state_atom}'
                    )
                    out['contadores']['falha'] += 1
                    for aj in ajustes_post:
                        _registrar_auditoria(
                            ajuste_id=aj.id, ciclo=ciclo, fase='F-F',
                            acao='entrada_destino_manual',
                            modelo_odoo='stock.picking',
                            status='IDEMPOTENT_OTHER',
                            odoo_id=picking_id,
                            erro_msg=(
                                f'state={state_atom} — investigacao manual'
                            ),
                            tempo_ms=tempo_ms_inv, executado_por=usuario,
                        )
                    _commit_resilient()
                else:
                    logger.error(
                        f'  F invoice {invoice_id}: atomo retornou status '
                        f'desconhecido={status_atom!r}'
                    )
                    out['invoices_falha'][invoice_id] = (
                        f'atomo_status_desconhecido: {status_atom}'
                    )
                    out['contadores']['falha'] += 1
            except Exception as e:
                tempo_ms_inv = int((time.time() - inicio_inv) * 1000)
                logger.error(
                    f'  F invoice {invoice_id}: atomo falhou: {e}',
                    exc_info=True,
                )
                # F6 v15c re-fetch + auditoria
                ajustes_post: List = []
                for a in ajs:
                    af = safe_session_get(AjusteEstoqueInventario, a.id)
                    if af is not None:
                        ajustes_post.append(af)
                for aj in ajustes_post:
                    aj.erro_msg = (f'F entrada destino falhou: {e}')[:500]
                    _registrar_auditoria(
                        ajuste_id=aj.id, ciclo=ciclo, fase='F-F',
                        acao='entrada_destino_manual',
                        modelo_odoo='stock.picking',
                        status='EXCECAO', erro_msg=str(e)[:500],
                        tempo_ms=tempo_ms_inv, executado_por=usuario,
                    )
                _commit_resilient()
                out['invoices_falha'][invoice_id] = (
                    f'atomo_excecao: {str(e)[:200]}'
                )
                out['contadores']['falha'] += 1

        # Status agregado (v17.5: canary_bloqueado conta como sucesso parcial
        # se houver outras ok; isolado vira EXECUTADO_PARCIAL — operador roda
        # de novo com --auto-confirma-direcao-nova para processar canary)
        n_ok = out['contadores']['ok']
        n_falha = out['contadores']['falha']
        n_canary = out['contadores']['canary_bloqueado']
        if n_falha == 0 and n_canary == 0:
            out['status'] = 'EXECUTADO_ETAPA_F'
        elif n_ok > 0 or out['contadores']['skip'] > 0 or n_canary > 0:
            # Tem alguma operacao ok/skip OU canary aguardando confirmacao
            out['status'] = 'EXECUTADO_PARCIAL'
        else:
            out['status'] = 'FALHA_ETAPA_F'

        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    # ========================================================
    # Entry-point macro: executar_pipeline_bulk (A->B->C->D->E->F)
    # ========================================================

    def executar_pipeline_bulk(
        self,
        *,
        ciclo: str,
        etapas: Tuple[str, ...] = ETAPAS_VALIDAS,
        company_origem_id: Optional[int] = None,
        dry_run: bool = True,
        confirmar_sefaz: bool = False,
        auto_confirma_direcao_nova: bool = False,
        usuario: str = 'faturamento_pipeline',
        cod_produto: Optional[str] = None,
        limite: Optional[int] = None,
        pular_pre_flight: bool = False,
        usar_fluxo_l3_v19: bool = False,
        usar_skill8_atomica_v25: bool = False,
    ) -> Dict[str, Any]:
        """Entry-point publico: executa pipeline A->B->C->D->E->F como
        SEQUENCIA de barreiras (D11) com sub-skill C5 PRE-FLIGHT no inicio.

        Pattern macro (decisao 10.3 — etapa = barreira):
          PRE-FLIGHT C5 (se nao pular) -> bloqueia se !pode_faturar
          A -> expire_all+reload -> B -> expire_all+reload -> C -> ...

        Args:
            ciclo: identificador do ciclo.
            etapas: subset de ETAPAS_VALIDAS (ordem fixa). Default: todas.
            company_origem_id: filtro por company emissora (None = todas).
            dry_run: True (default) simula; False executa real.
            confirmar_sefaz: 2 nivel — exigido para ETAPA D (irreversivel).
            usuario: identificador para auditoria.
            cod_produto: smoke/canary.
            limite: limita N primeiros ajustes (sub-piloto).
            pular_pre_flight: True pula sub-skill C5 (uso em pytest).

        Returns:
            dict consolidado com resultado de cada etapa.
        """
        t0 = time.time()
        out: Dict[str, Any] = {
            'ciclo': ciclo,
            'etapas_solicitadas': list(etapas),
            'company_origem_id': company_origem_id,
            'dry_run': dry_run,
            'confirmar_sefaz': confirmar_sefaz,
            'limite': limite,
            'cod_produto': cod_produto,
            'pre_flight': None,
            'etapas_executadas': {},
        }

        # Validar etapas + ordem
        invalidas = [e for e in etapas if e not in ETAPAS_VALIDAS]
        if invalidas:
            out['status'] = 'FALHA_USO'
            out['erro'] = (
                f'etapas invalidas: {invalidas}. Validas: {ETAPAS_VALIDAS}'
            )
            return out

        # PRE-FLIGHT C5
        if not pular_pre_flight:
            try:
                pre_flight_result = self.pre_flight(ciclo)
            except FileNotFoundError as e:
                out['status'] = 'FALHA_PRE_FLIGHT_CLI_AUSENTE'
                out['erro'] = str(e)
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out
            except subprocess.TimeoutExpired:
                out['status'] = 'FALHA_PRE_FLIGHT_TIMEOUT'
                out['erro'] = (
                    f'sub-skill C5 timeout apos {SUB_SKILL_C5_TIMEOUT_S}s'
                )
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out

            out['pre_flight'] = pre_flight_result
            if not pre_flight_result.get('pode_faturar', False):
                out['status'] = 'BLOQUEADO_PRE_FLIGHT'
                out['erro'] = (
                    f'PRE-FLIGHT C5 retornou pode_faturar=False '
                    f'(status_global={pre_flight_result.get("status_global")}). '
                    f'Bloqueios: {pre_flight_result.get("bloqueios")}. '
                    f'Corrigir cadastro antes de re-executar.'
                )
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out

        # CR-H4 v15b: guard architectural para v17 — abortar antes de ETAPA D
        # se ETAPA B (anterior critica) teve falhas. Em v15b stubs C/D/E/F
        # nao escrevem SEFAZ, mas a constante explicita o invariante para
        # quando v17 implementar.
        ETAPAS_ABORT_SE_ANTERIOR_FALHOU: Tuple[str, ...] = ('D',)

        # CR-F7 v15c (Reviewer A C2 + C HIGH conf 90): ETAPAS_DISPOSE_ENVOLVEM
        # listam etapas que exigem `db.engine.dispose()` profilatico ANTES e
        # APOS (D10 — G016 SSL drop em loops longos). Em v15b C/D sao stubs;
        # ativar dispose efetivo em v16/v17 quando essas etapas operarem.
        ETAPAS_DISPOSE_ENVOLVEM: Tuple[str, ...] = ('C', 'D')

        # CR-F4 v15c: importar db aqui para barreira MACRO explicita entre
        # etapas (D11 — Reviewer A C1 CRITICAL conf 95). expire_all() entre
        # etapas garante ORM cache invalidado mesmo se `executar_etapa_X`
        # nao recarregar (defensive).
        from app import db  # lazy

        # Executar etapas na ordem fixa
        ultima_etapa_executada: Optional[str] = None
        for etapa in ETAPAS_VALIDAS:
            if etapa not in etapas:
                continue
            # CR-H4: bloquear D se B falhou
            if etapa in ETAPAS_ABORT_SE_ANTERIOR_FALHOU:
                if 'B' in out['etapas_executadas']:
                    status_b = out['etapas_executadas']['B'].get('status', '')
                    if (
                        status_b.startswith('FALHA')
                        or status_b == 'EXCECAO_NAO_TRATADA'
                        or 'PARCIAL' in status_b
                    ):
                        out['etapas_executadas'][etapa] = {
                            'etapa': etapa,
                            'status': 'BLOQUEADO_ETAPA_ANTERIOR_FALHOU',
                            'erro': (
                                f'ETAPA {etapa} (SEFAZ) bloqueada porque '
                                f'ETAPA B status={status_b!r}. Resolver B '
                                f'antes de re-executar D.'
                            ),
                        }
                        continue

            # CR-F4 v15c: BARREIRA MACRO explicita (D11) entre etapas — Reviewer A C1.
            # expire_all() invalida ORM cache; cada `executar_etapa_X` re-loadara
            # ajustes frescos com `fase_pipeline` da etapa anterior.
            if ultima_etapa_executada is not None:
                try:
                    db.session.expire_all()
                    logger.debug(
                        f'BARREIRA MACRO (D11): expire_all() apos '
                        f'{ultima_etapa_executada} -> antes de {etapa}'
                    )
                except Exception as e:
                    logger.warning(f'D11 expire_all falhou (continuando): {e}')

            # CR-F7 v15c: db.engine.dispose() PROFILATICO antes de etapas
            # com ops longas (C polling 1800s, D Playwright 5-10min/NF).
            # ATIVO ate v15b (stubs leves); custo trivial mesmo em stub.
            if etapa in ETAPAS_DISPOSE_ENVOLVEM:
                try:
                    db.engine.dispose()
                    logger.debug(
                        f'D10 db.engine.dispose() PROFILATICO antes de ETAPA {etapa}'
                    )
                except Exception as e:
                    logger.warning(
                        f'D10 engine.dispose antes de {etapa} falhou: {e}'
                    )

            try:
                if etapa == 'A':
                    res = self.executar_etapa_a(
                        ciclo=ciclo,
                        company_origem_id=company_origem_id,
                        dry_run=dry_run,
                        usuario=usuario,
                        cod_produto=cod_produto,
                        limite=limite,  # v16: propagar smoke/canary
                    )
                elif etapa == 'B':
                    res = self.executar_etapa_b(
                        ciclo=ciclo,
                        company_origem_id=company_origem_id,
                        dry_run=dry_run,
                        usuario=usuario,
                        cod_produto=cod_produto,
                        limite=limite,
                    )
                elif etapa == 'C':
                    # v16: ETAPA C real-aware (timeout default 1800s).
                    # v25+ S1: opt-in usar_skill8_atomica_v25 substitui legacy
                    # pelos atomos 3+4 da Skill 8 ATOMICA L2 (polling_invoice +
                    # validar_invoice_pos_robo). Default OFF preserva legacy =
                    # zero risco regressao. Ortogonal a usar_fluxo_l3_v19.
                    if usar_skill8_atomica_v25:
                        res = self._executar_etapa_c_via_skill8_atomica(
                            ciclo=ciclo,
                            company_origem_id=company_origem_id,
                            dry_run=dry_run,
                            usuario=usuario,
                            cod_produto=cod_produto,
                            t0=time.time(),
                        )
                    else:
                        res = self.executar_etapa_c(
                            ciclo=ciclo,
                            company_origem_id=company_origem_id,
                            dry_run=dry_run,
                            usuario=usuario,
                            cod_produto=cod_produto,
                        )
                elif etapa == 'D':
                    # v17: ETAPA D real-aware (Playwright SEFAZ).
                    # confirmar_sefaz e' 2 nivel — exigido para real-run.
                    # v25+ S1: opt-in usar_skill8_atomica_v25 substitui legacy
                    # pelo atomo 5 da Skill 8 ATOMICA L2 (transmitir_sefaz).
                    if usar_skill8_atomica_v25:
                        res = self._executar_etapa_d_via_skill8_atomica(
                            ciclo=ciclo,
                            company_origem_id=company_origem_id,
                            dry_run=dry_run,
                            confirmar_sefaz=confirmar_sefaz,
                            usuario=usuario,
                            cod_produto=cod_produto,
                            t0=time.time(),
                        )
                    else:
                        res = self.executar_etapa_d(
                            ciclo=ciclo,
                            company_origem_id=company_origem_id,
                            dry_run=dry_run,
                            confirmar_sefaz=confirmar_sefaz,
                            usuario=usuario,
                            cod_produto=cod_produto,
                        )
                elif etapa == 'E':
                    # v17: ETAPA E real-aware (RecebimentoLf X->FB SEQUENCIAL).
                    # v20+ S3: opt-in usar_fluxo_l3_v19 propagado (skip se True).
                    res = self.executar_etapa_e(
                        ciclo=ciclo,
                        company_origem_id=company_origem_id,
                        dry_run=dry_run,
                        usuario=usuario,
                        cod_produto=cod_produto,
                        usar_fluxo_l3_v19=usar_fluxo_l3_v19,
                    )
                elif etapa == 'F':
                    # v17.5: ETAPA F real-aware (DELEGA Skill 5 atomo).
                    # Flag auto_confirma_direcao_nova passa adiante para
                    # liberar canary DEV_FB_LF + TRANSFERIR_FB_CD.
                    # v20+ S3: opt-in usar_fluxo_l3_v19 substitui ETAPA F
                    # legacy pelo FLUXO L3 1.2.x quando flag=True (LF
                    # destino validado canary; CD destino NAO_SUPORTADA_V20).
                    res = self.executar_etapa_f(
                        ciclo=ciclo,
                        company_origem_id=company_origem_id,
                        dry_run=dry_run,
                        usuario=usuario,
                        cod_produto=cod_produto,
                        auto_confirma_direcao_nova=auto_confirma_direcao_nova,
                        usar_fluxo_l3_v19=usar_fluxo_l3_v19,
                    )
                else:
                    res = {'status': 'FALHA_USO_ETAPA_DESCONHECIDA'}
                out['etapas_executadas'][etapa] = res
                ultima_etapa_executada = etapa  # CR-F4 v15c: rastrear p/ barreira
            except Exception as e:
                logger.error(
                    f'ETAPA {etapa} falhou: {e}', exc_info=True,
                )
                out['etapas_executadas'][etapa] = {
                    'etapa': etapa,
                    'status': 'EXCECAO_NAO_TRATADA',
                    'erro': str(e)[:500],
                }
                ultima_etapa_executada = etapa  # mesmo em falha, etapa rodou
                # Em v15b: nao abortar — continuar outras etapas (operador
                # decide). Em v17 (SEFAZ): abortar em D se falhar para
                # nao continuar com state distribuido inconsistente.

            # CR-F7 v15c: db.engine.dispose() PROFILATICO APOS etapas longas
            # (D10 — alem do dispose antes).
            if etapa in ETAPAS_DISPOSE_ENVOLVEM:
                try:
                    db.engine.dispose()
                    logger.debug(
                        f'D10 db.engine.dispose() PROFILATICO apos ETAPA {etapa}'
                    )
                except Exception as e:
                    logger.warning(
                        f'D10 engine.dispose apos {etapa} falhou: {e}'
                    )

        # Status agregado.
        # CR-M3 v15b: 'BLOQUEADO_SEM_CONFIRMAR_SEFAZ' e
        # 'BLOQUEADO_ETAPA_ANTERIOR_FALHOU' contam como falha — pipeline
        # nao retorna OK quando ETAPA D foi bloqueada.
        # CR-v20+-CRITICAL-1 (review code-reviewer 2026-05-26):
        # 'SKIP_NAO_SUPORTADA_V20_FLUXO_L3' (retornado por ETAPA E quando
        # `usar_fluxo_l3_v19=True` mas company_destino=1 FB ainda nao
        # mapeada em CONSTANTS_FLUXO_L3_POR_COMPANY_DESTINO) DEVE contar
        # como falha. Sem este check, operador rodando
        # `--usar-fluxo-l3-v19 --etapas E,F` receberia EXECUTADO_OK mesmo
        # com ETAPA E silenciosamente skipada — silent correctness gap.
        STATUS_FALHA = (
            'EXCECAO_NAO_TRATADA',
            'BLOQUEADO_SEM_CONFIRMAR_SEFAZ',
            'BLOQUEADO_ETAPA_ANTERIOR_FALHOU',
            'SKIP_NAO_SUPORTADA_V20_FLUXO_L3',  # v20+ CRITICAL-1
            'SKIP_NAO_SUPORTADA_V20',           # v20+ ETAPA F via fluxo L3 sem invoices suportados
        )
        status_etapas = [
            r.get('status', '') for r in out['etapas_executadas'].values()
        ]
        if any(
            s.startswith('FALHA') or s in STATUS_FALHA
            for s in status_etapas
        ):
            out['status'] = (
                'EXECUTADO_PARCIAL' if not dry_run else 'DRY_RUN_PARCIAL'
            )
        elif dry_run:
            out['status'] = 'DRY_RUN_OK'
        else:
            out['status'] = 'EXECUTADO_OK'

        out['tempo_ms'] = int((time.time() - t0) * 1000)
        return out

    # ============================================================
    # v18 — Recovery `executar_pipeline_resume` (C14)
    # ============================================================

    def _contar_pendentes_por_etapa(
        self,
        *,
        etapa: str,
        ciclo: str,
        company_origem_id: Optional[int] = None,
        cod_produto: Optional[str] = None,
    ) -> int:
        """Conta ajustes ainda pendentes para a etapa indicada.

        Define "pendente" por etapa (espelha filtros usados em
        `executar_etapa_X` + scripts `fat_lf_resume*.sh`):

          - B: acao in ACOES_PICKING + fase nao-terminal de B
               (fase NOT IN {F5c, F5d, F5e, F5f}). Inclui F5a_FALHA / F5b_FALHA /
               F5c_FALHA naturalmente (NAO terminais).
          - C: acao in ACOES_PICKING + fase IN (F5c_LIBERADO, F5d_TIMEOUT).
               F5d_TIMEOUT incluida (CR v18 F1): re-rodar C tenta polling
               novamente; pode pegar invoice agora pronta no CIEL IT.
          - D: acao in ACOES_PICKING + fase IN (F5d_INVOICE_GERADA, F5e_FALHA).
               F5e_FALHA incluida (CR v18 F1): operador pode tentar retry —
               se executar_etapa_d nao re-processar F5e_FALHA, vira STAGNATION
               alertando operador (intervencao manual: revert fase_pipeline OU
               investigar SEFAZ rejeicao cstat).
          - E: acao in ACOES_ENTRADA_FB + fase == F5e_SEFAZ_OK MINUS invoices
               com RecebimentoLf status='processado'. Espelha contador de
               `fat_lf_resume_entrada.sh:contar_e`. RecLf em outros status
               (pendente/processando/erro) ainda conta como pendente — recovery
               re-invoca Skill 7 que aplica HIGH-3 retoma.
          - F: acao in ACOES_ENTRADA_DESTINO_MANUAL + fase IN (F5e_SEFAZ_OK,
               F5f_FALHA). F5f_FALHA incluida (CR v18 F1 CRITICAL): retry
               idempotente — Skill 5 atomo `criar_picking_entrada_destino_manual`
               eh idempotente via origin exato. Se F5f_FALHA persistir, vira
               STAGNATION alertando operador.

        Pre-cond: app_context ativo (db.session disponivel).

        Args:
            etapa: 'B' | 'C' | 'D' | 'E' | 'F'.
            ciclo: identificador do ciclo.
            company_origem_id: filtro opcional (so ETAPA B-D filtram por
                acoes da company origem; E/F sao por acao_decidida).
            cod_produto: smoke/canary (1 produto).

        Returns:
            int >= 0.

        Raises:
            ValueError: etapa invalida.
        """
        if etapa not in RESUME_ETAPAS_VALIDAS:
            raise ValueError(
                f'_contar_pendentes_por_etapa: etapa={etapa!r} invalida. '
                f'Validas: {RESUME_ETAPAS_VALIDAS}'
            )

        from app import db  # lazy
        from app.odoo.models import AjusteEstoqueInventario  # lazy

        db.session.expire_all()  # D11 — invalida ORM cache

        q = AjusteEstoqueInventario.query.filter_by(ciclo=ciclo)
        # CR v23+ S2: ETAPA F aceita 'EXECUTADO' porque ajustes ja' progrediram
        # apos ETAPA D OK (status muda PROPOSTO->APROVADO->EXECUTADO em F5e_SEFAZ_OK).
        # Sem este filtro ampliado, contador F retornaria 0 para ajustes
        # pos-SEFAZ pendentes de criar invoice de ENTRADA (passo 9 do FLUXO L3
        # 1.2.x). Workaround manual `UPDATE status='APROVADO'` era necessario
        # antes do retry resume F. v23+ codifica fix raiz. Demais etapas
        # mantem PROPOSTO/APROVADO (status nao deveria ser EXECUTADO antes do
        # SEFAZ-OK).
        status_validos: List[str] = ['PROPOSTO', 'APROVADO']
        if etapa == 'F':
            status_validos.append('EXECUTADO')
        q = q.filter(
            AjusteEstoqueInventario.status.in_(status_validos)
        )
        if cod_produto:
            q = q.filter(AjusteEstoqueInventario.cod_produto == cod_produto)

        if etapa in ('B', 'C', 'D'):
            # Filtra acoes da company emissora se informada.
            if company_origem_id is not None:
                acoes_co = [
                    a for a, (_, co, _) in ACAO_PARA_DIRECAO.items()
                    if co == company_origem_id and a in ACOES_PICKING
                ]
                if not acoes_co:
                    return 0
                q = q.filter(
                    AjusteEstoqueInventario.acao_decidida.in_(acoes_co)
                )
            else:
                q = q.filter(
                    AjusteEstoqueInventario.acao_decidida.in_(
                        list(ACOES_PICKING)
                    )
                )

            if etapa == 'B':
                # Pendentes: fase IS NULL OR fase NOT IN terminais de B.
                q = q.filter(
                    (
                        AjusteEstoqueInventario.fase_pipeline.is_(None)
                    ) | (
                        AjusteEstoqueInventario.fase_pipeline.notin_(
                            list(FASES_TERMINAIS_B)
                        )
                    )
                )
            elif etapa == 'C':
                # CR v18 F1: incluir F5d_TIMEOUT (retry polling pode pegar
                # invoice agora pronta).
                q = q.filter(
                    AjusteEstoqueInventario.fase_pipeline.in_(
                        [FASE_F5c_OK, FASE_F5d_TIMEOUT]
                    )
                )
            elif etapa == 'D':
                # CR v18 F1: incluir F5e_FALHA (alerta operador via
                # STAGNATION para investigar SEFAZ rejeicao OU revert manual).
                q = q.filter(
                    AjusteEstoqueInventario.fase_pipeline.in_(
                        [FASE_F5d_OK, FASE_F5e_FALHA]
                    )
                )
            return int(q.count())

        if etapa == 'E':
            # Pendentes: acoes_entrada_fb em F5e_SEFAZ_OK; remover invoices
            # com RecebimentoLf 'processado' (G-RECLF-3).
            from app.recebimento.models import RecebimentoLf  # lazy
            q = q.filter(
                AjusteEstoqueInventario.acao_decidida.in_(
                    list(ACOES_ENTRADA_FB)
                )
            )
            q = q.filter(
                AjusteEstoqueInventario.fase_pipeline == FASE_F5e_OK
            )
            ajustes = q.all()
            invs = {
                a.invoice_id_odoo for a in ajustes if a.invoice_id_odoo
            }
            if not invs:
                return 0
            feitos = {
                r.odoo_lf_invoice_id
                for r in (
                    RecebimentoLf.query
                    .filter(
                        RecebimentoLf.odoo_lf_invoice_id.in_(list(invs))
                    )
                    .filter(RecebimentoLf.status == 'processado')
                    .all()
                )
            }
            return len(invs - feitos)

        # etapa == 'F'
        # CR v18 F1 CRITICAL: incluir F5f_FALHA — retry idempotente da Skill 5
        # atomo via origin exato. Persistencia em F5f_FALHA gera STAGNATION
        # alertando operador a investigar (cause real do retry-falha).
        q = q.filter(
            AjusteEstoqueInventario.acao_decidida.in_(
                list(ACOES_ENTRADA_DESTINO_MANUAL)
            )
        )
        q = q.filter(
            AjusteEstoqueInventario.fase_pipeline.in_(
                [FASE_F5e_OK, FASE_F5f_FALHA]
            )
        )
        return int(q.count())

    def executar_pipeline_resume(
        self,
        *,
        ciclo: str,
        apenas_etapa: str,
        max_iter: int = RESUME_MAX_ITER_DEFAULT,
        timeout_iter_s: int = RESUME_TIMEOUT_ITER_S_DEFAULT,
        detector_stagnation: bool = True,
        company_origem_id: Optional[int] = None,
        dry_run: bool = True,
        confirmar_sefaz: bool = False,
        auto_confirma_direcao_nova: bool = False,
        usuario: str = 'faturamento_pipeline_resume',
        cod_produto: Optional[str] = None,
        limite: Optional[int] = None,
        usar_fluxo_l3_v19: bool = False,
        usar_skill8_atomica_v25: bool = False,
    ) -> Dict[str, Any]:
        """Loop de recovery: invoca `executar_pipeline_bulk(etapas=(apenas_etapa,))`
        repetidamente ate' (a) pendentes==0 OU (b) detector_stagnation OU
        (c) max_iter atingido.

        Substitui scripts shell `fat_lf_resume.sh` (B->D) + `fat_lf_resume_entrada.sh`
        (E + F). Reusa toda a infraestrutura de `executar_pipeline_bulk`
        (barreira MACRO D11 + D10 dispose + CR-H4 guard + auditoria).

        Pattern (espelha shell `fat_lf_resume.sh:18-39`):
          1. Contar pendentes iniciais. Se 0 -> TUDO_OK_INICIAL.
          2. Para iter in 1..max_iter:
             a. executar_pipeline_bulk(etapas=(apenas_etapa,), pular_pre_flight=True)
             b. recontar pendentes.
             c. se pendentes == 0 -> TUDO_OK.
             d. se detector_stagnation AND pendentes == prev_pendentes -> STAGNATION.
             e. prev_pendentes = pendentes.
          3. Se loop completar sem retorno -> MAX_ITER.

        Args:
            ciclo: identificador do ciclo.
            apenas_etapa: 'B' | 'C' | 'D' | 'E' | 'F' (A nao precisa recovery
                iterativo — Skill 2 ja' tem retomada propria).
            max_iter: limite de iteracoes (default 18, espelha shell).
            timeout_iter_s: timeout do bulk por iter (default 900s).
                **CR v18 F3 — NAO ENFORCADO em v18**: serve apenas de
                orientacao operacional (informa o operador qual eh o tempo
                esperado por iter para ETAPA C polling = 1800s, D Playwright =
                5-10min/NF, E RecLf = 30-60min/invoice). NAO eh propagado
                para `executar_pipeline_bulk` (que NAO tem parametro de
                timeout em v18). Enforcement via ThreadPoolExecutor.submit().result(timeout=)
                pendente refator v19+. Operador pode usar `timeout` do shell
                Linux: `timeout 900 python -m ... --modo resume ...`.
            detector_stagnation: True (default) para parada antecipada se
                pendentes nao diminuir. Util em ETAPA D (operador deve checar
                rejeicao SEFAZ se travar).
            company_origem_id: filtro de company emissora (1/4/5).
            dry_run: True default — simula. False executa real.
            confirmar_sefaz: 2 nivel obrigatorio em ETAPA D.
            auto_confirma_direcao_nova: ETAPA F canary v17.5.
            usuario: auditoria.
            cod_produto: smoke/canary 1 produto.
            limite: limita N primeiros ajustes por iter.

        Returns:
            dict com:
              modo: 'resume'
              ciclo, apenas_etapa, max_iter
              iteracoes_executadas: int
              restantes_iniciais: int
              restantes_por_iter: List[{iter, restantes, status_bulk}]
              motivo_parada: 'TUDO_OK_INICIAL' | 'TUDO_OK' | 'STAGNATION' |
                             'MAX_ITER' | 'EXCECAO' | 'FALHA_USO'
              ultima_invocacao_bulk: dict (resultado do bulk da ultima iter)
              status: 'EXECUTADO_OK' | 'EXECUTADO_PARCIAL' | 'DRY_RUN_OK' |
                      'DRY_RUN_PARCIAL' | 'FALHA_USO'
              tempo_ms: int
              erro: str (se EXCECAO ou FALHA_USO)

        Raises:
            ValueError: apenas_etapa nao em RESUME_ETAPAS_VALIDAS.
        """
        t0 = time.time()
        out: Dict[str, Any] = {
            'modo': 'resume',
            'ciclo': ciclo,
            'apenas_etapa': apenas_etapa,
            'max_iter': max_iter,
            'detector_stagnation': detector_stagnation,
            'dry_run': dry_run,
            'iteracoes_executadas': 0,
            'restantes_iniciais': None,
            'restantes_por_iter': [],
            'motivo_parada': None,
            'ultima_invocacao_bulk': None,
        }

        # Validar apenas_etapa.
        if apenas_etapa not in RESUME_ETAPAS_VALIDAS:
            out['status'] = 'FALHA_USO'
            out['motivo_parada'] = 'FALHA_USO'
            out['erro'] = (
                f'apenas_etapa={apenas_etapa!r} invalida para resume. '
                f'Validas: {RESUME_ETAPAS_VALIDAS} '
                f'(A nao precisa recovery iterativo).'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Guard CR-H4: D exige confirmar_sefaz em real-run.
        if apenas_etapa == 'D' and not dry_run and not confirmar_sefaz:
            out['status'] = 'FALHA_USO'
            out['motivo_parada'] = 'FALHA_USO'
            out['erro'] = (
                'ETAPA D em real-run exige --confirmar-sefaz (IRREVERSIVEL).'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Contar pendentes iniciais.
        try:
            restantes_iniciais = self._contar_pendentes_por_etapa(
                etapa=apenas_etapa,
                ciclo=ciclo,
                company_origem_id=company_origem_id,
                cod_produto=cod_produto,
            )
        except Exception as e:
            logger.error(
                f'resume: contagem inicial falhou: {e}', exc_info=True,
            )
            out['status'] = 'EXECUTADO_PARCIAL' if not dry_run else 'DRY_RUN_PARCIAL'
            out['motivo_parada'] = 'EXCECAO'
            out['erro'] = f'contagem_inicial: {str(e)[:300]}'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        out['restantes_iniciais'] = restantes_iniciais
        if restantes_iniciais == 0:
            out['motivo_parada'] = 'TUDO_OK_INICIAL'
            out['status'] = 'DRY_RUN_OK' if dry_run else 'EXECUTADO_OK'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            logger.info(
                f'resume ciclo={ciclo} etapa={apenas_etapa}: '
                f'TUDO_OK_INICIAL (0 pendentes).'
            )
            return out

        # Loop principal.
        prev_restantes = restantes_iniciais
        for i in range(1, max_iter + 1):
            iter_t0 = time.time()
            logger.info(
                f'resume ITER {i}/{max_iter} ciclo={ciclo} '
                f'etapa={apenas_etapa} prev_restantes={prev_restantes}'
            )

            # Invocar bulk com 1 etapa.
            try:
                bulk_result = self.executar_pipeline_bulk(
                    ciclo=ciclo,
                    etapas=(apenas_etapa,),
                    company_origem_id=company_origem_id,
                    dry_run=dry_run,
                    confirmar_sefaz=confirmar_sefaz,
                    auto_confirma_direcao_nova=auto_confirma_direcao_nova,
                    usuario=usuario,
                    cod_produto=cod_produto,
                    limite=limite,
                    # Recovery NAO re-roda pre-flight (custoso, ja' rodou
                    # no canary inicial; ETAPAS B-F nao escrevem cadastro).
                    pular_pre_flight=True,
                    # v20+ S3: propagar opt-in para recovery resume
                    usar_fluxo_l3_v19=usar_fluxo_l3_v19,
                    # v25+ S1: propagar opt-in Skill 8 ATOMICA L2
                    usar_skill8_atomica_v25=usar_skill8_atomica_v25,
                )
            except Exception as e:
                logger.error(
                    f'resume ITER {i}: bulk falhou: {e}', exc_info=True,
                )
                out['iteracoes_executadas'] = i
                out['motivo_parada'] = 'EXCECAO'
                out['ultima_invocacao_bulk'] = {'erro': str(e)[:300]}
                out['status'] = (
                    'EXECUTADO_PARCIAL' if not dry_run else 'DRY_RUN_PARCIAL'
                )
                out['erro'] = f'iter {i} bulk: {str(e)[:300]}'
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out

            out['ultima_invocacao_bulk'] = bulk_result

            # Re-contar pendentes pos-iter.
            try:
                restantes = self._contar_pendentes_por_etapa(
                    etapa=apenas_etapa,
                    ciclo=ciclo,
                    company_origem_id=company_origem_id,
                    cod_produto=cod_produto,
                )
            except Exception as e:
                logger.error(
                    f'resume ITER {i}: contagem pos falhou: {e}',
                    exc_info=True,
                )
                out['iteracoes_executadas'] = i
                out['motivo_parada'] = 'EXCECAO'
                out['status'] = (
                    'EXECUTADO_PARCIAL' if not dry_run else 'DRY_RUN_PARCIAL'
                )
                out['erro'] = f'iter {i} contagem: {str(e)[:300]}'
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                return out

            iter_ms = int((time.time() - iter_t0) * 1000)
            out['restantes_por_iter'].append({
                'iter': i,
                'restantes': restantes,
                'status_bulk': bulk_result.get('status'),
                'tempo_ms': iter_ms,
            })

            # TUDO_OK ?
            if restantes == 0:
                out['iteracoes_executadas'] = i
                out['motivo_parada'] = 'TUDO_OK'
                out['status'] = 'DRY_RUN_OK' if dry_run else 'EXECUTADO_OK'
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                logger.info(
                    f'resume ciclo={ciclo} etapa={apenas_etapa}: '
                    f'TUDO_OK apos {i} iter (de {restantes_iniciais} -> 0).'
                )
                return out

            # STAGNATION ?
            if detector_stagnation and restantes == prev_restantes:
                out['iteracoes_executadas'] = i
                out['motivo_parada'] = 'STAGNATION'
                out['status'] = (
                    'EXECUTADO_PARCIAL' if not dry_run else 'DRY_RUN_PARCIAL'
                )
                out['tempo_ms'] = int((time.time() - t0) * 1000)
                logger.warning(
                    f'resume ciclo={ciclo} etapa={apenas_etapa}: STAGNATION '
                    f'apos {i} iter (restantes={restantes} sem progresso). '
                    f'Operador deve investigar (ex.: SEFAZ rejeicao, robo CIEL IT travado, '
                    f'cadastro fiscal pendente).'
                )
                return out

            # Em dry-run, fase_pipeline nao avanca — `restantes` ficara igual.
            # Detector_stagnation evita loop infinito; sem detector, max_iter
            # ainda fecha. Documentado em pytest dry-run para evitar surpresa.
            prev_restantes = restantes

        # MAX_ITER atingido.
        out['iteracoes_executadas'] = max_iter
        out['motivo_parada'] = 'MAX_ITER'
        out['status'] = (
            'EXECUTADO_PARCIAL' if not dry_run else 'DRY_RUN_PARCIAL'
        )
        out['tempo_ms'] = int((time.time() - t0) * 1000)
        logger.warning(
            f'resume ciclo={ciclo} etapa={apenas_etapa}: MAX_ITER '
            f'apos {max_iter} iter (restantes={prev_restantes}).'
        )
        return out


# ============================================================
# CLI (modo: bulk / pre-flight / resume)
# ============================================================

def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='faturar_pipeline',
        description=(
            'Skill 8 faturando-odoo orchestrator v18 — '
            'pipeline A->B->C->D->E->F + recovery resume.'
        ),
    )
    p.add_argument('--ciclo', default=CICLO_DEFAULT,
                   help=f'identificador do ciclo (default {CICLO_DEFAULT})')
    p.add_argument(
        '--modo', choices=['bulk', 'pre-flight', 'resume'],
        default='bulk',
        help=(
            'bulk = pipeline A->F; pre-flight = so sub-skill C5; '
            'resume = loop iterativo so de --apenas-etapa (v18)'
        ),
    )
    p.add_argument(
        '--etapas', default=','.join(ETAPAS_VALIDAS),
        help=(
            f'etapas separadas por virgula (default {",".join(ETAPAS_VALIDAS)}); '
            f'use "A,B" para parar antes de C. Ignorado em --modo resume.'
        ),
    )
    p.add_argument('--apenas-etapa', default=None, choices=list(RESUME_ETAPAS_VALIDAS),
                   help=(
                       'v18 — etapa unica para --modo resume '
                       f'(validas: {",".join(RESUME_ETAPAS_VALIDAS)}).'
                   ))
    p.add_argument('--max-iter', type=int, default=RESUME_MAX_ITER_DEFAULT,
                   help=(
                       f'v18 — max iteracoes do loop resume '
                       f'(default {RESUME_MAX_ITER_DEFAULT}, espelha shell).'
                   ))
    p.add_argument('--timeout-iter', type=int, default=RESUME_TIMEOUT_ITER_S_DEFAULT,
                   help=(
                       f'v18 — orientacao operacional (default {RESUME_TIMEOUT_ITER_S_DEFAULT}s); '
                       'NAO ENFORCADO em v18 (CR v18 F3): serve apenas de '
                       'sinalizacao. Operador pode usar `timeout NNN python -m ...` '
                       'do shell para enforcement real.'
                   ))
    p.add_argument('--sem-stagnation', action='store_true',
                   help='v18 — desabilita detector_stagnation (default True).')
    p.add_argument('--company-origem-id', type=int, default=None,
                   help='filtro por company emissora (1/4/5)')
    p.add_argument('--cod-produto', default=None,
                   help='smoke/canary — 1 produto especifico')
    p.add_argument('--limite', type=int, default=None,
                   help='limita N primeiros ajustes (sub-piloto)')
    p.add_argument('--confirmar', action='store_true',
                   help='executa real (sem --confirmar = dry-run)')
    p.add_argument('--confirmar-sefaz', action='store_true',
                   help='2 nivel — exigido para ETAPA D (IRREVERSIVEL)')
    p.add_argument('--auto-confirma-direcao-nova', action='store_true',
                   help='v17.5 — habilita ETAPA F canary direcoes '
                        'DEV_FB_LF + TRANSFERIR_FB_CD (sem precedente PROD)')
    p.add_argument('--pular-pre-flight', action='store_true',
                   help='nao invoca sub-skill C5 (uso em pytest)')
    p.add_argument('--usuario', default='faturamento_pipeline_cli',
                   help='identificador para auditoria')
    p.add_argument(
        '--usar-fluxo-l3-v19', action='store_true',
        help=(
            'v20+ S3 opt-in: substitui ETAPAS E+F legacy pelo FLUXO L3 1.2.x '
            'via executar_fluxo_l3_1_2_x. Default OFF preserva 100%% '
            'comportamento legacy. ETAPA E (entrada FB destino) retorna '
            'SKIP_NAO_SUPORTADA_V20_FLUXO_L3 (pendencia v28+); ETAPA F '
            'todos destinos (LF=5 validado canary 2026-05-26 caso 627348; '
            'FB=1 e CD=4 CANDIDATE v27+ S4 expand constants + L10N_BR_TIPO_PEDIDO '
            'mapeado para 8 acoes da MATRIZ_INTERCOMPANY — pendente canary REAL).'
        ),
    )
    p.add_argument(
        '--usar-skill8-atomica-v25', action='store_true',
        help=(
            'v25+ S1 opt-in: substitui ETAPAs C+D legacy pelos atomos 3, 4 '
            'e 5 da Skill 8 ATOMICA L2 em app/odoo/estoque/scripts/'
            'faturamento.py. ETAPA C usa polling_invoice + '
            'validar_invoice_pos_robo (G029+G007+G034); ETAPA D usa '
            'transmitir_sefaz (Playwright IRREVERSIVEL). Default OFF '
            'preserva 100%% comportamento legacy. Ortogonal a '
            '--usar-fluxo-l3-v19 (ambas podem coexistir; --usar-skill8 '
            'substitui C+D, --usar-fluxo-l3 substitui E+F).'
        ),
    )
    return p


def main(argv: Optional[List[str]] = None) -> int:
    """Entry-point CLI.

    Cria Flask app_context obrigatorio (D11 — `db.session.expire_all()` precisa).
    Pattern espelha `setup_cli_completo` da Skill 6 — versao minima inline.

    Exit codes (alinhados Skill 6 v9):
      0 = OK (real ou dry-run completo)
      1 = falha negocial (pre-flight bloqueado, ETAPA D sem sefaz, etc)
      2 = uso (argparse, etapa invalida)
      4 = DRY_RUN_OK (sucesso simulado)
    """
    parser = _build_argparser()
    args = parser.parse_args(argv)

    # Parse etapas
    etapas_tuple = tuple(e.strip().upper() for e in args.etapas.split(','))
    invalidas = [e for e in etapas_tuple if e not in ETAPAS_VALIDAS]
    if invalidas:
        sys.stderr.write(
            f'ERRO USO: etapas invalidas {invalidas}. '
            f'Validas: {ETAPAS_VALIDAS}\n'
        )
        return 2

    # App context obrigatorio — db.session.expire_all() em _carregar_ajustes
    # exige Flask context. Pattern espelha Skill 6 setup_cli_completo.
    from app import create_app  # lazy
    app = create_app()
    with app.app_context():
        executor = FaturamentoPipelineExecutor()
        dry_run = not args.confirmar

        if args.modo == 'pre-flight':
            try:
                result = executor.pre_flight(args.ciclo)
            except FileNotFoundError as e:
                sys.stderr.write(f'ERRO: {e}\n')
                return 1
            print(json.dumps(result, indent=2, default=str))
            if result.get('status_global') == 'PRE_FLIGHT_OK':
                return 0
            if result.get('status_global') == 'PRE_FLIGHT_WARN':
                return 0  # warn nao bloqueia
            return 1

        if args.modo == 'resume':
            if not args.apenas_etapa:
                sys.stderr.write(
                    'ERRO USO: --modo resume exige --apenas-etapa '
                    f'(validas: {",".join(RESUME_ETAPAS_VALIDAS)}).\n'
                )
                return 2
            result = executor.executar_pipeline_resume(
                ciclo=args.ciclo,
                apenas_etapa=args.apenas_etapa,
                max_iter=args.max_iter,
                timeout_iter_s=args.timeout_iter,
                detector_stagnation=not args.sem_stagnation,
                company_origem_id=args.company_origem_id,
                dry_run=dry_run,
                confirmar_sefaz=args.confirmar_sefaz,
                auto_confirma_direcao_nova=args.auto_confirma_direcao_nova,
                usuario=args.usuario,
                cod_produto=args.cod_produto,
                limite=args.limite,
                usar_fluxo_l3_v19=args.usar_fluxo_l3_v19,
                usar_skill8_atomica_v25=args.usar_skill8_atomica_v25,
            )
            print(json.dumps(result, indent=2, default=str))
            status = result.get('status', '')
            if status == 'EXECUTADO_OK':
                return 0
            if status == 'DRY_RUN_OK':
                return 4
            if status in ('DRY_RUN_PARCIAL', 'EXECUTADO_PARCIAL'):
                return 1
            if status == 'FALHA_USO':
                return 2
            return 1

        # modo bulk
        result = executor.executar_pipeline_bulk(
            ciclo=args.ciclo,
            etapas=etapas_tuple,
            company_origem_id=args.company_origem_id,
            dry_run=dry_run,
            confirmar_sefaz=args.confirmar_sefaz,
            auto_confirma_direcao_nova=args.auto_confirma_direcao_nova,
            usuario=args.usuario,
            cod_produto=args.cod_produto,
            limite=args.limite,
            pular_pre_flight=args.pular_pre_flight,
            usar_fluxo_l3_v19=args.usar_fluxo_l3_v19,
            usar_skill8_atomica_v25=args.usar_skill8_atomica_v25,
        )
        print(json.dumps(result, indent=2, default=str))

        status = result.get('status', '')
        if status == 'EXECUTADO_OK':
            return 0
        if status == 'DRY_RUN_OK':
            return 4
        if status in ('DRY_RUN_PARCIAL', 'EXECUTADO_PARCIAL'):
            return 1
        if status == 'FALHA_USO':
            return 2
        return 1


if __name__ == '__main__':
    sys.exit(main())
