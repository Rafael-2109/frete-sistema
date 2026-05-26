"""faturamento_pipeline.py — Orchestrator C3 macro Skill 8 `faturando-odoo` (v15b).

Executa pipeline completo A-F de faturamento inter-company de inventario:

- ETAPA A: transferencias internas pre-faturamento (DELEGADO Skill 2)
- ETAPA B: F5a criar pickings + F5b validar + F5c liberar (via Skill 5 v15a)
- ETAPA C: F5d aguardar invoices CIEL IT  (stub v16)
- ETAPA D: F5e transmitir SEFAZ Playwright (stub v17 — IRREVERSIVEL)
- ETAPA E: RecebimentoLf X->FB (stub v17)
- ETAPA F: picking entrada manual destino (DELEGADO Skill 5 v15a — stub v17)

v15b (esta versao): C6 (esqueleto) + C7 (F5a criar) + C8 (F5b validar) + F5c.
  ETAPAS C/D/E/F: stubs `NOT_IMPLEMENTED_v15b`.

REGRA INVIOLAVEL 0: ler `app/odoo/estoque/PLANEJAMENTO_SKILL8_FATURANDO.md`
INTEIRO antes de modificar este arquivo. SEFAZ irreversivel.

PRINCIPIO ARQUITETURAL v15a:
  Toda operacao em stock.picking passa por StockPickingService (Skill 5).
  Orchestrator NUNCA chama `odoo.create('stock.picking')` direto.

Pattern reuso: `app/odoo/estoque/orchestrators/pre_etapa_executor.py` (Skill 6 v9).

Decisoes aplicadas:
  D10: db.engine.dispose() profilatico antes/apos C+D (v16)
  D11: db.session.expire_all() + reload entre etapas
  D13: ETAPA A SEQUENCIAL (XML-RPC nao thread-safe Request-sent)
  D14: _commit_resilient versao MAIS FORTE (engine.dispose se SSL)
  D15: ETAPA A 100% DELEGAVEL para Skill 2 `transferindo-interno-odoo`
  D16: ETAPA B pipeline POR PICKING + sleep 5s entre chunks (G022)
  D18: dry_run=True default + --confirmar + --confirmar-sefaz (2 niveis)
  10.6: F5a/F5b/F5c via atomos Skill 5 (`criar_picking_inter_company`,
        `validar_picking_inter_company`, `liberar_faturamento`)
  10.5: PRE-FLIGHT via sub-skill C5 (subprocess `auditar_cadastro_inventario.py`)

Gotchas codificados:
  G016: SSL — `_commit_resilient` proativo + `expire_all()+carregar_ajustes()`
  G022: sleep 5s entre chunks ETAPA B
  G023: company_id forcado em moves (via atomo Skill 5)
  G-ETB-COMPENSATORIO: qty_restante > 0 em PERDA_LF_FB cria novo
        AjusteEstoqueInventario PROPOSTO para ondas futuras
  G-ETB-G014 (TODO v16): lote vencido on-the-fly via Skill 2

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
        OperacaoOdooAuditoria.registrar(
            external_id=external_id,
            tabela_origem='ajuste_estoque_inventario',
            registro_id=ajuste_id,
            acao=acao,
            modelo_odoo=modelo_odoo or 'stock.picking',
            etapa=fase,
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
        self, *, ciclo: str, confirmar_sefaz: bool = False, **_kw,
    ) -> Dict[str, Any]:
        """ETAPA D — F5e transmitir SEFAZ Playwright (stub v17 — IRREVERSIVEL).

        v17: implementar Playwright serial (1 browser) + idempotencia
        TRIPLA (D8) + commit_resilient antes/apos cada NF (D14) +
        re-fetch via db.session.get (D9). HARD_FAIL_CONFIG aborta batch.
        D18: exige --confirmar-sefaz ALEM de --confirmar.
        """
        if not confirmar_sefaz:
            return {
                'etapa': 'D',
                'ciclo': ciclo,
                'status': 'BLOQUEADO_SEM_CONFIRMAR_SEFAZ',
                'erro': (
                    'ETAPA D (SEFAZ) e IRREVERSIVEL. Exige '
                    '`--confirmar-sefaz` ALEM de `--confirmar`. '
                    'Em v15b, stub retorna sem executar.'
                ),
            }
        return {
            'etapa': 'D',
            'ciclo': ciclo,
            'status': 'NOT_IMPLEMENTED_v15b',
            'roadmap': 'C11 v17',
        }

    def executar_etapa_e(self, *, ciclo: str, **_kw) -> Dict[str, Any]:
        """ETAPA E — RecebimentoLf X->FB (stub v17).

        v17: invoca `RecebimentoLfOdooService.processar_recebimento(rec_id)`
        (modulo externo — NAO MEXER). 30-60min POR INVOICE (G-RECLF-1).
        Decidir paralelismo em v17 (decisao 10.7 PENDENTE).

        v17 ira utilizar (CR-F8 v15c — refs explicitas):
          - `ACOES_ENTRADA_FB` (filtro de acoes que disparam ETAPA E)
          - `ACAO_PARA_CFOP_ENTRADA` (mapa 5xxx -> 1xxx para
            RecebimentoLfLote.cfop — D17)
        """
        return {
            'etapa': 'E',
            'ciclo': ciclo,
            'status': 'NOT_IMPLEMENTED_v15b',
            'roadmap': 'C12 v17',
            'refs_v17': {
                'acoes_entrada_fb_count': len(ACOES_ENTRADA_FB),
                'cfop_entrada_count': len(ACAO_PARA_CFOP_ENTRADA),
            },
        }

    def executar_etapa_f(self, *, ciclo: str, **_kw) -> Dict[str, Any]:
        """ETAPA F — picking entrada manual destino FB->{LF,CD} (stub v17).

        v17: invoca `picking_svc.criar_picking_entrada_destino_manual`
        (atomo Skill 5 v15a) por invoice_id distinto. G023 codificado
        intra-atomo. Idempotencia via origin EXATO.

        v17 ira utilizar (CR-F10 v15c — refs explicitas das 4 constantes
        ETAPA F centralizadas em `picking_types.py` v15a):
          - `ACOES_ENTRADA_DESTINO_MANUAL` (filtro: so' INDUSTRIALIZACAO_FB_LF
            validado em PROD; DEV_FB_LF/TRANSFERIR_FB_CD a validar)
          - `PICKING_TYPE_ENTRADA_DESTINO_MANUAL` (LF=19; CD/FB a descobrir)
          - `COMPANY_LABEL_ENTRADA` (FB/CD/LF — usado em `origin`)
          - `LOCATION_ORIGEM_ENTRADA_INDUSTR` (alias 26489 Em Transito Industr)
        """
        return {
            'etapa': 'F',
            'ciclo': ciclo,
            'status': 'NOT_IMPLEMENTED_v15b',
            'roadmap': 'C13 v17',
            'refs_v17': {
                'acoes_entrada_destino_manual_count': len(
                    ACOES_ENTRADA_DESTINO_MANUAL
                ),
                'picking_type_entrada_destino_manual': dict(
                    PICKING_TYPE_ENTRADA_DESTINO_MANUAL
                ),
                'company_label_entrada': dict(COMPANY_LABEL_ENTRADA),
                'location_origem_entrada_industr': (
                    LOCATION_ORIGEM_ENTRADA_INDUSTR
                ),
            },
        }

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
        usuario: str = 'faturamento_pipeline',
        cod_produto: Optional[str] = None,
        limite: Optional[int] = None,
        pular_pre_flight: bool = False,
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
                    # v16: ETAPA C agora real-aware (timeout default 1800s).
                    res = self.executar_etapa_c(
                        ciclo=ciclo,
                        company_origem_id=company_origem_id,
                        dry_run=dry_run,
                        usuario=usuario,
                        cod_produto=cod_produto,
                    )
                elif etapa == 'D':
                    res = self.executar_etapa_d(
                        ciclo=ciclo,
                        confirmar_sefaz=confirmar_sefaz,
                    )
                elif etapa == 'E':
                    res = self.executar_etapa_e(ciclo=ciclo)
                elif etapa == 'F':
                    res = self.executar_etapa_f(ciclo=ciclo)
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
        STATUS_FALHA = (
            'EXCECAO_NAO_TRATADA',
            'BLOQUEADO_SEM_CONFIRMAR_SEFAZ',
            'BLOQUEADO_ETAPA_ANTERIOR_FALHOU',
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
# CLI (modo: bulk / pre-flight / etapa-X)
# ============================================================

def _build_argparser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog='faturar_pipeline',
        description=(
            'Skill 8 faturando-odoo orchestrator v15b — '
            'pipeline A->B->C->D->E->F inter-company.'
        ),
    )
    p.add_argument('--ciclo', default=CICLO_DEFAULT,
                   help=f'identificador do ciclo (default {CICLO_DEFAULT})')
    p.add_argument(
        '--modo', choices=['bulk', 'pre-flight'],
        default='bulk',
        help='bulk = pipeline A->F; pre-flight = so sub-skill C5',
    )
    p.add_argument(
        '--etapas', default=','.join(ETAPAS_VALIDAS),
        help=(
            f'etapas separadas por virgula (default {",".join(ETAPAS_VALIDAS)}); '
            f'use "A,B" para parar antes de C'
        ),
    )
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
    p.add_argument('--pular-pre-flight', action='store_true',
                   help='nao invoca sub-skill C5 (uso em pytest)')
    p.add_argument('--usuario', default='faturamento_pipeline_cli',
                   help='identificador para auditoria')
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

        # modo bulk
        result = executor.executar_pipeline_bulk(
            ciclo=args.ciclo,
            etapas=etapas_tuple,
            company_origem_id=args.company_origem_id,
            dry_run=dry_run,
            confirmar_sefaz=args.confirmar_sefaz,
            usuario=args.usuario,
            cod_produto=args.cod_produto,
            limite=args.limite,
            pular_pre_flight=args.pular_pre_flight,
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
