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

from sqlalchemy.exc import OperationalError

from app.odoo.constants.ids_diversos import (
    CARRIER_NACOM,
    INCOTERM_CIF,
)
from app.odoo.constants.locations import COMPANY_LOCATIONS
from app.odoo.constants.operacoes_fiscais import COMPANY_PARTNER_ID
from app.odoo.constants.picking_types import (
    LOCATION_DESTINO_POR_DIRECAO,
    get_picking_type,
)
from app.odoo.estoque.scripts.picking import StockPickingService
from app.odoo.utils.connection import get_odoo_connection

logger = logging.getLogger(__name__)


# ============================================================
# Constantes locais (v15b)
# ============================================================

CICLO_DEFAULT = 'INVENTARIO_2026_05'

# Mapeia acao_decidida -> (tipo_op, company_origem, company_destino).
# Mesma tabela do `inventario_pipeline_service.ACAO_PARA_DIRECAO` — copiada
# para evitar import cruzado service <-> orchestrator. Centralizar em
# `app/odoo/constants/operacoes_fiscais.py` em v17 (pendencia §9 do
# PLANEJAMENTO).
ACAO_PARA_DIRECAO: Dict[str, Tuple[str, int, int]] = {
    'TRANSFERIR_CD_FB':       ('transf-filial',        4, 1),
    'TRANSFERIR_FB_CD':       ('transf-filial',        1, 4),
    'INDUSTRIALIZACAO_FB_LF': ('industrializacao',     1, 5),
    'PERDA_LF_FB':            ('perda',                5, 1),
    'DEV_FB_LF':              ('dev-industrializacao', 1, 5),
    'DEV_LF_FB':              ('dev-industrializacao', 5, 1),
    'DEV_CD_LF':              ('dev-industrializacao', 4, 5),
    'DEV_LF_CD':              ('dev-industrializacao', 5, 4),
}

# Subset de acao_decidida que dispara ETAPA B (cria picking inter-company).
# Equivale a `ACAO_PARA_DIRECAO.keys()` — proxy semantico (filtro pipeline,
# NAO matriz fiscal). NAO entra em `operacoes_fiscais.py`.
ACOES_PICKING: frozenset = frozenset(ACAO_PARA_DIRECAO.keys())

# Limite de cods por picking (script 09 L1136). Reduz over-reservation em
# lotes velhos pos-renomeacao (G022).
MAX_CODS_POR_PICKING = 30

# Sleep entre chunks ETAPA B (D16, script 09 L1136-1138 — G022 mitigation).
SLEEP_ENTRE_CHUNKS = 5.0

# Etapas validas (ordem fixa A->B->C->D->E->F).
ETAPAS_VALIDAS: Tuple[str, ...] = ('A', 'B', 'C', 'D', 'E', 'F')

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


# ============================================================
# Helpers de auditoria + commit resiliente
# ============================================================

def _commit_resilient(
    *, max_attempts: int = 3, backoff_base: float = 2.0,
) -> bool:
    """Commit resiliente a SSL drop (D14 — versao MAIS FORTE que `_commit_with_retry`).

    Combina (a) rollback+close+retry com (b) `db.engine.dispose()` proativo
    quando detecta substring 'SSL' no erro. Backoff exponencial entre
    tentativas (2s, 4s, 8s).

    Espelha script 09 L158-210 (`_commit_resilient`) — versao consolidada
    aqui ate criacao do helper compartilhado em
    `app/odoo/estoque/scripts/_commit_helpers.py` (pendencia §9 v16).

    Args:
        max_attempts: numero maximo de tentativas (default 3).
        backoff_base: base do backoff exponencial em segundos (default 2).

    Returns:
        True se commit OK (em alguma tentativa), False se esgotou.
    """
    from app import db  # lazy (evita circular em tests)

    last_err: Optional[Exception] = None
    for attempt in range(1, max_attempts + 1):
        try:
            db.session.commit()
            if attempt > 1:
                logger.info(f'G016 _commit_resilient OK na tentativa {attempt}')
            return True
        except OperationalError as e:
            last_err = e
            err_str = str(e)[:200]
            err_low = err_str.lower()
            is_ssl = 'ssl' in err_low or 'connection' in err_low
            logger.warning(
                f'G016 _commit_resilient attempt {attempt}/{max_attempts} '
                f'OperationalError (ssl={is_ssl}): {err_str}'
            )
            try:
                db.session.rollback()
            except Exception as e_rb:
                logger.warning(f'G016 rollback falhou (continuando): {e_rb}')
            try:
                db.session.close()
            except Exception as e_cl:
                logger.warning(f'G016 close falhou (continuando): {e_cl}')
            if is_ssl:
                # D14: dispose proativo do engine se SSL drop detectado.
                try:
                    db.engine.dispose()
                    logger.info('G016 db.engine.dispose() executado (SSL drop)')
                except Exception as e_disp:
                    logger.warning(f'G016 engine.dispose falhou: {e_disp}')
            if attempt < max_attempts:
                sleep_s = backoff_base ** (attempt - 1)
                time.sleep(sleep_s)
    logger.error(
        f'G016 _commit_resilient FAILED apos {max_attempts} tentativas. '
        f'Ultimo erro: {last_err}'
    )
    return False


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
    ) -> Dict[str, Any]:
        """ETAPA A: transferencias internas pre-faturamento.

        DELEGADO 100% para Skill 2 `transferindo-interno-odoo` (D15).
        Esta funcao apenas:
          1. Carrega ajustes do ciclo+company com fases ('TRANSF_PENDENTE'|None)
             e acao_decidida em ACOES_PICKING.
          2. SEQUENCIAL (D13 — XML-RPC nao thread-safe Request-sent):
             para cada ajuste, invoca Skill 2 via service direto.
          3. Atualiza `fase_pipeline = 'TRANSF_OK'` em sucesso.

        v15b: implementacao SIMPLES — invoca apenas se o ajuste tem
        `lote_origem` distinto do quant atual (caller responsavel por
        decidir se precisa transferir). Em v16, expandir com analise
        de quants automatica.

        Args:
            ciclo: identificador do ciclo.
            company_origem_id: filtro por company emissora.
            dry_run: True (default) simula; False executa real.
            usuario: identificador para auditoria.
            cod_produto: smoke/canary.

        Returns:
            dict com status + contadores.
        """
        t0 = time.time()
        ajustes = _carregar_ajustes(
            ciclo=ciclo,
            company_origem_id=company_origem_id,
            fases_pipeline=[None, 'TRANSF_PENDENTE'],
            cod_produto=cod_produto,
        )
        out: Dict[str, Any] = {
            'etapa': 'A',
            'ciclo': ciclo,
            'company_origem_id': company_origem_id,
            'dry_run': dry_run,
            'ajustes_total': len(ajustes),
        }
        if not ajustes:
            out['status'] = 'SKIP_NENHUM_AJUSTE'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # v15b min: marca todos como 'TRANSF_OK' (sem analise de quants).
        # Em v16, integrar com Skill 2 quando descobrirmos casos reais que
        # exigem transf interna antes da ETAPA B. Caso geral (script 09
        # L501-613): a maioria dos ajustes NAO precisa de ETAPA A — apenas
        # quando o lote_origem requer renomeacao.
        # CR-BUG-1 v9 (Skill 6 lessons): se houver incerteza, retornar
        # status especifico em vez de simular.
        if dry_run:
            out['status'] = 'DRY_RUN_OK_ETAPA_A_NOOP'
            out['observacao'] = (
                f'v15b: ETAPA A simplificada — assume que ajustes ja '
                f'tem `lote_origem` correto no Odoo. Em v16, integrar '
                f'analise de quants + invocacao Skill 2 se necessario. '
                f'Por ora retorna NOOP para nao bloquear pipeline A+B+C+D+E+F.'
            )
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        # Real run: marcar como TRANSF_OK sem operar (v15b stub seguro).
        # Em v16, invocar Skill 2 aqui se houver lote_origem != quant atual.
        for a in ajustes:
            a.fase_pipeline = 'TRANSF_OK'
        if not _commit_resilient():
            out['status'] = 'FALHA_COMMIT_TRANSF_OK'
            out['tempo_ms'] = int((time.time() - t0) * 1000)
            return out

        out['status'] = 'EXECUTADO_ETAPA_A_NOOP'
        out['ajustes_atualizados'] = len(ajustes)
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

        # Status agregado
        if out['falhas']:
            if out['pickings_liberados'] or out['pickings_criados']:
                out['status'] = (
                    'DRY_RUN_OK_PARCIAL' if dry_run else 'EXECUTADO_PARCIAL'
                )
            else:
                out['status'] = 'FALHA_TOTAL'
        elif dry_run:
            out['status'] = 'DRY_RUN_OK_ETAPA_B'
        else:
            out['status'] = 'EXECUTADO_ETAPA_B'

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
          - F5a: criar_picking_inter_company (Skill 5 v15a)
          - F5b: validar_picking_inter_company (Skill 5 v15a)
          - F5c: liberar_faturamento (Skill 5 — atomo legacy)
          - Caller (executar_etapa_b) faz sleep 5s entre chunks (G022)

        Args:
            ajustes_chunk: lista de AjusteEstoqueInventario do mesmo
                (company_origem, tipo_op). Todos com `acao_decidida`
                compativel (ja agrupados upstream).
            acao_decidida_referencia: acao do primeiro ajuste — usada para
                resolver metadata.
            dry_run: simula vs executa.
            usuario: para auditoria.
            ciclo: para auditoria.

        Returns:
            dict com chave por sub-etapa (picking_planejado / picking_id_criado /
            picking_id_validado / picking_id_liberado / compensatorios / falhas).
        """
        out_chunk: Dict[str, Any] = {
            'ajustes_ids': [a.id for a in ajustes_chunk],
            'compensatorios': [],
            'falhas': [],
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

        ajustes_sem_pid: List[int] = []
        for a in ajustes_chunk:
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
            linhas.append({
                'product_id': pid,
                'quantity': qty,
                'lot_name': a.lote_origem or None,
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
            out_chunk['picking_id_criado'] = picking_id
            tempo_f5a = int((time.time() - t_f5a) * 1000)

            # Atualizar fase + picking_id em todos ajustes do chunk
            for a in ajustes_chunk:
                a.picking_id_odoo = picking_id
                a.fase_pipeline = FASE_F5a_OK
                _registrar_auditoria(
                    ajuste_id=a.id, ciclo=ciclo, fase=FASE_F5a_OK,
                    acao='criar_picking_inter_company',
                    modelo_odoo='stock.picking',
                    status='SUCESSO', odoo_id=picking_id,
                    payload={
                        'origin': origin,
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
                logger.error(
                    f'F5a commit FAILED apos picking_id={picking_id} criado'
                )
                # Continuar — picking ja existe no Odoo (idempotente via origin)
        except Exception as e:
            msg = str(e)[:500]
            logger.error(
                f'F5a falhou origin={origin!r}: {msg}', exc_info=True
            )
            for a in ajustes_chunk:
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

    def executar_etapa_c(self, *, ciclo: str, **_kw) -> Dict[str, Any]:
        """ETAPA C — F5d aguardar invoices CIEL IT (stub v16).

        v16: implementar polling de account.move + sub-etapas F5d.5 (G029
        payment_provider) + F5d.6 (G007 price zero) + F5d.7 (G034 fiscal
        setup DEV_*). D10: db.engine.dispose() antes/apos.
        """
        return {
            'etapa': 'C',
            'ciclo': ciclo,
            'status': 'NOT_IMPLEMENTED_v15b',
            'roadmap': 'C9/C10 v16',
        }

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
        """
        return {
            'etapa': 'E',
            'ciclo': ciclo,
            'status': 'NOT_IMPLEMENTED_v15b',
            'roadmap': 'C12 v17',
        }

    def executar_etapa_f(self, *, ciclo: str, **_kw) -> Dict[str, Any]:
        """ETAPA F — picking entrada manual destino FB->{LF,CD} (stub v17).

        v17: invoca `picking_svc.criar_picking_entrada_destino_manual`
        (atomo Skill 5 v15a) por invoice_id distinto. G023 codificado
        intra-atomo. Idempotencia via origin EXATO.
        """
        return {
            'etapa': 'F',
            'ciclo': ciclo,
            'status': 'NOT_IMPLEMENTED_v15b',
            'roadmap': 'C13 v17',
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

        # Executar etapas na ordem fixa
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
            try:
                if etapa == 'A':
                    res = self.executar_etapa_a(
                        ciclo=ciclo,
                        company_origem_id=company_origem_id,
                        dry_run=dry_run,
                        usuario=usuario,
                        cod_produto=cod_produto,
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
                    res = self.executar_etapa_c(ciclo=ciclo)
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
            except Exception as e:
                logger.error(
                    f'ETAPA {etapa} falhou: {e}', exc_info=True,
                )
                out['etapas_executadas'][etapa] = {
                    'etapa': etapa,
                    'status': 'EXCECAO_NAO_TRATADA',
                    'erro': str(e)[:500],
                }
                # Em v15b: nao abortar — continuar outras etapas (operador
                # decide). Em v17 (SEFAZ): abortar em D se falhar para
                # nao continuar com state distribuido inconsistente.

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
