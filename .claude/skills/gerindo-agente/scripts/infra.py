#!/usr/bin/env python3
"""
infra.py — observabilidade de infra/seguranca do Agente Web (READ, Onda 4 / P10).

Expoe o estado operacional do agente para INSPECAO. Custo $0 de tokens (SQL/Redis
puro). Subcomandos:

  flags          Flags de EVOLUCAO (blueprint Ondas 0-4 + loop corretivo) com:
                 declarada (valor NESTE processo), env var, default e — o ponto
                 central — `db_evidence`: o estado EFETIVO em PROD inferido do
                 rastro no BANCO (env-INDEPENDENTE), pois o banco aponta p/ PROD.
  gates          Gates de acesso runtime (permissions.py): WRITE gerindo (dev-only),
                 restricao de estoque + allow-list, debug-mode, reversibilidade,
                 hard-enforce. Cada um com enforcement + allow-list + o que bloqueia.
  worker-status  Filas RQ do agente (agent_judge/agent_eval/agent_validation/
                 agent_background/artifacts) + workers vivos. Degrada se Redis off.

HONESTIDADE DE AMBIENTE (gotcha que motivou o db_evidence): flags e Redis sao lidos
do AMBIENTE DO PROCESSO. Rodado pelo agente web em PROD -> reflete PROD (correto, e o
consumidor primario). Rodado por dev localmente -> reflete LOCAL. O BANCO e a UNICA
fonte PROD-verdadeira quando rodado local (DATABASE_URL aponta p/ PROD). Por isso o
`flags` cruza o declarado [this-process] com `db_evidence` [PROD via DB].

Tudo READ — nenhuma escrita. Ver docs/superpowers/plans/2026-06-03-evolucao-gerindo-agente.md (Onda 4 / P10).
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

from common import (
    format_table, run_handler, success_output, truncate,
)


SUBCOMMANDS = {
    'flags': {
        'help': 'Flags de evolucao (Ondas 0-4 + loop corretivo) + db_evidence (estado PROD via DB) — custo $0',
        'args': [
            {'name': '--days', 'type': int, 'default': 30,
             'help': 'Janela (dias) p/ a evidencia time-bound (agent_step/PlanState). Default 30.'},
        ],
    },
    'gates': {
        'help': 'Gates de acesso runtime (WRITE gerindo, estoque, debug, reversibilidade, hard-enforce) — custo $0',
        'args': [],
    },
    'worker-status': {
        'help': 'Filas RQ do agente + workers vivos (degrada se Redis off) — custo $0',
        'args': [],
    },
}


# =============================================================================
# Tabela das flags de EVOLUCAO. Fonte: secoes rotuladas "Onda 0..4" + flywheel +
# loop corretivo em app/agente/config/feature_flags.py. Cada tupla:
#   (attr_no_modulo, env_var, default, grupo, evidence_key, evidence_kind)
# evidence_key liga a flag a uma metrica de rastro no BANCO (env-independente).
#   evidence_key=None => sem rastro DB limpo (NAO inventamos proxy enganoso).
# evidence_kind distingue a SEMANTICA do rastro:
#   'activity'  => a atividade da flag ESCREVE a metrica (rastro>0 => flag EFETIVA em PROD).
#   'readiness' => atuador de INJECAO (sem rastro de injecao no DB); a metrica mede o
#                  CONTEUDO pronto p/ injetar, NAO o estado da flag (que so o env PROD sabe).
# =============================================================================
EVOLUTION_FLAGS = [
    ('USE_CAPABILITY_REGISTRY',     'AGENT_CAPABILITY_REGISTRY',   False, 'Onda 0',         None,                    None),
    # QUALITY_SPINE gateia o ENRIQUECIMENTO frustration_score (chat.py:1849), NAO a linha
    # agent_step (essa e Onda 0, incondicional). Rastro = steps com frustration_score (review HIGH-1).
    ('USE_AGENT_QUALITY_SPINE',     'AGENT_QUALITY_SPINE',         False, 'Onda 1',         'agent_step_frustration', 'activity'),
    ('USE_AGENT_STEP_JUDGE',        'AGENT_STEP_JUDGE',            False, 'Onda 1',         'agent_step_judged',     'activity'),
    ('USE_AGENT_ONTOLOGY',          'AGENT_ONTOLOGY',              False, 'Onda 1',         None,                    None),
    ('USE_AGENT_PLANNER',           'AGENT_PLANNER',               False, 'Onda 2',         'planstate_with_plan',   'activity'),
    ('USE_AGENT_VERIFY',            'AGENT_VERIFY',                False, 'Onda 2',         'agent_step_verified',   'activity'),
    ('AGENT_EVAL_GATE',             'AGENT_EVAL_GATE',             False, 'Onda 3',         'eval_scores',           'activity'),
    ('USE_AGENT_EVAL_CALIBRATION',  'AGENT_EVAL_CALIBRATION',      False, 'Onda 3',         'eval_cases',            'activity'),
    ('AGENT_DIRECTIVE_PROMOTION',   'AGENT_DIRECTIVE_PROMOTION',   False, 'Onda 3',         'directives_shadow',     'activity'),
    ('USE_AGENT_SKILL_RAG',         'AGENT_SKILL_RAG',             False, 'Onda 4',         None,                    None),
    ('USE_AGENT_WORLD_MODEL_INJECT', 'AGENT_WORLD_MODEL_INJECT',   False, 'Onda 4',         None,                    None),
    # readiness = CONTEUDO que o builder _build_operational_directives injeta = NULL/legado + 'ativa'
    # (importance>=threshold, nivel-5), NAO so 'ativa' (review MED-4).
    ('USE_OPERATIONAL_DIRECTIVES',  'AGENT_OPERATIONAL_DIRECTIVES', False, 'Atuador',       'directives_injetaveis', 'readiness'),
    # readiness = regras mandatory de QUALQUER path (filtro real de _build_user_rules), NAO so /corrections/ (review MED-3).
    ('USE_USER_RULES_CHANNEL',      'AGENT_USER_RULES_CHANNEL',    True,  'Loop corretivo', 'mandatory_rules_total', 'readiness'),
    ('USE_USER_RULES_TOP',          'AGENT_USER_RULES_TOP',        True,  'Loop corretivo', None,                    None),
    ('USE_RECURRENCE_SCORE',        'AGENT_RECURRENCE_SCORE',      False, 'Loop corretivo', None,                    None),
    ('AGENT_OUTCOME_TRACKING',      'AGENT_OUTCOME_TRACKING',      True,  'Loop corretivo', 'outcome_populated',     'activity'),
    ('AGENT_CORRECTION_PROMOTION',  'AGENT_CORRECTION_PROMOTION',  True,  'Loop corretivo', 'corrections_mandatory', 'activity'),
    ('AGENT_CORRECTION_DEMOTION',   'AGENT_CORRECTION_DEMOTION',   False, 'Loop corretivo', None,                    None),
    ('USE_MANDATORY_HARD_ENFORCE',  'AGENT_MANDATORY_HARD_ENFORCE', False, 'Loop corretivo', None,                   None),
]

# Filas RQ relevantes ao agente/flywheel (worker_render.py:143 lista a hardcoded).
AGENT_QUEUES = ['agent_judge', 'agent_eval', 'agent_validation', 'agent_background', 'artifacts']

# Subcomandos WRITE da skill que o gate _classify_gerindo_write NEGA ao agente web/Teams.
# Espelha o regex em permissions.py:424 (_GERINDO_WRITE_REGEX) — manter em sincronia se la mudar.
GERINDO_WRITE_BLOCKED = ['approve', 'reject', 'promote-batch', 'review', 'run', 'respond']


def _scope_info():
    """Rotula a procedencia de cada dimensao (honestidade de ambiente).

    O banco (DATABASE_URL) e a unica fonte PROD-verdadeira quando rodado local.
    Flags/Redis vem do ambiente DESTE processo. NUNCA imprime URL/senha.
    """
    db_url = os.environ.get('DATABASE_URL', '') or ''
    redis_url = os.environ.get('REDIS_URL', '') or ''
    # PROD = string EXTERNA do Render (dev local->PROD: '...oregon-postgres.render.com')
    # OU string INTERNA (agente web em PROD: host curto 'dpg-...'/'red-...' sem dominio)
    # OU marcador positivo de ambiente Render (RENDER=true / RENDER_SERVICE_ID).
    # Sem isso, o consumidor PRIMARIO (agente web em PROD) era rotulado 'local' (review MED-5).
    on_render = bool(os.environ.get('RENDER') or os.environ.get('RENDER_SERVICE_ID'))
    db_prod = on_render or any(t in db_url for t in ('.render.com', 'oregon-postgres', 'dpg-'))
    redis_prod = on_render or any(t in redis_url for t in ('.render.com', 'oregon-redis', 'red-'))
    return {
        'data_source': 'PROD' if db_prod else 'local/desconhecido',
        'flags_source': 'this-process (env do processo: local p/ dev, PROD p/ agente web)',
        'redis_target': 'PROD' if redis_prod else 'local/this-process',
    }


def _read_flag(attr, env_var, default):
    """Le a flag pelo modulo feature_flags (getattr) com fallback ao os.getenv.

    Tolerante: nunca levanta (contrato READ-first + degradacao graciosa).
    """
    try:
        from app.agente.config import feature_flags as ff
        if hasattr(ff, attr):
            return bool(getattr(ff, attr))
    except Exception:
        pass
    raw = os.environ.get(env_var)
    if raw is None:
        return bool(default)
    return raw.strip().lower() == 'true'


def _compute_evidence(days):
    """Coleta as metricas de rastro no BANCO (env-independente) UMA vez.

    Cada bloco e isolado (try/except + rollback) e degrada para None sem mascarar
    (a chave fica None + warning) — NUNCA emite status=query_error (o snapshot P12
    rejeitaria o shape de erro). Retorna (metrics, warnings, window_meta).
    """
    from app import db
    from datetime import timedelta
    from sqlalchemy import text, or_ as sql_or

    metrics = {
        'agent_step_frustration': None, 'agent_step_judged': None, 'agent_step_verified': None,
        'planstate_with_plan': None, 'planstate_total': None,
        'eval_scores': None, 'eval_cases': None,
        'directives_shadow': None, 'directives_injetaveis': None,
        'corrections_mandatory': None, 'mandatory_rules_total': None, 'outcome_populated': None,
    }
    warnings = []
    try:
        from app.utils.timezone import agora_utc_naive
        since = agora_utc_naive() - timedelta(days=days)
    except Exception:
        from datetime import datetime
        since = datetime(1970, 1, 1)

    # 1) agent_step (Onda 1) — time-bound. ATENCAO: a LINHA agent_step e Onda 0 (incondicional),
    # entao count total NAO prova flag. Contamos so o que CADA flag de fato escreve:
    # judge (STEP_JUDGE), verify (VERIFY), frustration_score (QUALITY_SPINE — chat.py:1849). Review HIGH-1.
    try:
        row = db.session.execute(text("""
            SELECT count(*) FILTER (WHERE outcome_signal::jsonb ? 'judge')  AS judged,
                   count(*) FILTER (WHERE outcome_signal::jsonb ? 'verify') AS verified,
                   count(*) FILTER (WHERE outcome_signal::jsonb ? 'frustration_score') AS frustration
            FROM agent_step
            WHERE created_at >= :since
        """), {'since': since}).fetchone()
        if row is not None:
            metrics['agent_step_judged'] = int(row.judged or 0)
            metrics['agent_step_verified'] = int(row.verified or 0)
            metrics['agent_step_frustration'] = int(row.frustration or 0)
    except Exception as e:
        db.session.rollback()
        warnings.append(f"evidencia agent_step indisponivel: {e}")

    # 2) PlanState (Onda 2: planner) — % de sessoes com data->'plan' na janela.
    try:
        row = db.session.execute(text("""
            SELECT count(*) AS total,
                   count(*) FILTER (WHERE data::jsonb ? 'plan') AS with_plan
            FROM agent_sessions
            WHERE created_at >= :since
        """), {'since': since}).fetchone()
        if row is not None:
            metrics['planstate_total'] = int(row.total or 0)
            metrics['planstate_with_plan'] = int(row.with_plan or 0)
    except Exception as e:
        db.session.rollback()
        warnings.append(f"evidencia PlanState indisponivel: {e}")

    # 3) eval (Onda 3: A3 gate + calibracao) — cumulativo.
    try:
        from app.agente.models import AgentEvalScore
        metrics['eval_scores'] = int(AgentEvalScore.query.count())
    except Exception as e:
        db.session.rollback()
        warnings.append(f"evidencia eval_scores indisponivel: {e}")
    try:
        from app.agente.models import AgentEvalCase
        metrics['eval_cases'] = int(AgentEvalCase.query.count())
    except Exception as e:
        db.session.rollback()
        warnings.append(f"evidencia eval_cases indisponivel: {e}")

    # 4) Diretrizes-empresa: shadow (A4 promocao, activity) + injetaveis (atuador readiness).
    # injetaveis espelha _build_operational_directives (memory_injection.py:462-475): directive_status
    # IN (NULL,'ativa') + importance>=threshold + non-cold — NULL/legado TAMBEM injeta (review MED-4).
    try:
        from app.agente.models import AgentMemory
        try:
            from app.agente.config.feature_flags import MANDATORY_IMPORTANCE_THRESHOLD as _imp_thr
            imp_thr = float(_imp_thr)
        except Exception:
            imp_thr = 0.7
        empresa_base = [
            AgentMemory.user_id == 0,
            AgentMemory.is_directory == False,  # noqa: E712
            sql_or(
                AgentMemory.path.like('/memories/empresa/heuristicas/%'),
                AgentMemory.path.like('/memories/empresa/protocolos/%'),
            ),
        ]
        metrics['directives_shadow'] = int(AgentMemory.query.filter(
            *empresa_base, AgentMemory.directive_status == 'shadow').count())
        metrics['directives_injetaveis'] = int(AgentMemory.query.filter(
            *empresa_base,
            AgentMemory.is_cold == False,  # noqa: E712
            AgentMemory.importance_score >= imp_thr,
            sql_or(AgentMemory.directive_status.is_(None), AgentMemory.directive_status == 'ativa'),
        ).count())
    except Exception as e:
        db.session.rollback()
        warnings.append(f"evidencia diretrizes indisponivel: {e}")

    # 5) corrections_mandatory = CORRECTION_PROMOTION (activity): correcoes /corrections/ promovidas
    # a mandatory. E o que o batch A4 ESCREVE (priority='mandatory' em /corrections/).
    try:
        from app.agente.models import AgentMemory
        metrics['corrections_mandatory'] = int(AgentMemory.query.filter(
            AgentMemory.is_directory == False,  # noqa: E712
            AgentMemory.path.like('/memories/corrections/%'),
            AgentMemory.priority == 'mandatory',
        ).count())
    except Exception as e:
        db.session.rollback()
        warnings.append(f"evidencia correcoes mandatory indisponivel: {e}")

    # 5b) mandatory_rules_total = USER_RULES_CHANNEL (readiness): TODA regra mandatory injetavel,
    # de QUALQUER path. Espelha o filtro REAL de _build_user_rules (memory_injection_rules.py:16-42):
    # priority='mandatory' + non-cold, SEM restringir a /corrections/ (review MED-3).
    try:
        from app.agente.models import AgentMemory
        metrics['mandatory_rules_total'] = int(AgentMemory.query.filter(
            AgentMemory.is_directory == False,  # noqa: E712
            AgentMemory.priority == 'mandatory',
            AgentMemory.is_cold == False,  # noqa: E712
        ).count())
    except Exception as e:
        db.session.rollback()
        warnings.append(f"evidencia mandatory_rules indisponivel: {e}")

    # 6) Outcome tracking populado (loop corretivo: harmful/helpful > 0) — cumulativo.
    try:
        from app.agente.models import AgentMemory
        metrics['outcome_populated'] = int(AgentMemory.query.filter(
            sql_or(AgentMemory.harmful_count > 0, AgentMemory.helpful_count > 0)
        ).count())
    except Exception as e:
        db.session.rollback()
        warnings.append(f"evidencia outcome indisponivel: {e}")

    window_meta = {'evidence_window_days': days, 'time_bound_keys': ['agent_step_frustration',
                   'agent_step_judged', 'agent_step_verified', 'planstate_with_plan', 'planstate_total']}
    return metrics, warnings, window_meta


def _evidence_for(evidence_key, evidence_kind, metrics):
    """Constroi o bloco db_evidence de UMA flag a partir das metricas coletadas.

    Retorna None se a flag nao tem rastro DB limpo (evidence_key=None) — honesto,
    sem proxy enganoso. Senao {metric, kind, value, signal}.

    kind='activity' (a atividade da flag escreve a metrica):
      active  -> rastro (>0): EFETIVAMENTE ON em PROD (independe do declarado).
      idle    -> rastro 0: inativa / no-op em PROD (ou janela vazia).
    kind='readiness' (atuador de injecao, sem rastro de injecao no DB):
      ready   -> ha CONTEUDO pronto (>0) p/ injetar (estado da flag NAO inferivel).
      empty   -> 0 conteudo: nada a injetar mesmo se a flag estiver ON.
    unknown -> a metrica falhou (None) em qualquer kind.
    """
    # Shape HOMOGENEO sempre (dict, nunca None) p/ o snapshot P12 nao colapsar o
    # campo polimorfico e mascarar regressao no sub-shape (review MED-7/LOW-9).
    if evidence_key is None:
        return {'metric': None, 'kind': None, 'value': None, 'signal': 'none'}
    val = metrics.get(evidence_key)
    if val is None:
        return {'metric': evidence_key, 'kind': evidence_kind, 'value': None, 'signal': 'unknown'}
    if evidence_kind == 'readiness':
        signal = 'ready' if val > 0 else 'empty'
    else:
        signal = 'active' if val > 0 else 'idle'
    return {'metric': evidence_key, 'kind': evidence_kind, 'value': int(val), 'signal': signal}


def _verdict(declared, evidence):
    """Frase curta cruzando declarado [this-process] x db_evidence [PROD/readiness]."""
    d = 'ON' if declared else 'OFF'
    sig = evidence['signal']
    val = evidence['value']
    if sig == 'none':
        return f"declarada {d} [this-process]; sem rastro DB (nao inferivel)"
    if sig == 'unknown':
        return f"declarada {d} [this-process]; evidencia DB indisponivel"
    if sig == 'active':
        return f"declarada {d} [this-process]; DB mostra {val} -> EFETIVA em PROD"
    if sig == 'idle':
        return f"declarada {d} [this-process]; DB sem rastro (0) -> inativa/no-op em PROD"
    if sig == 'ready':
        return (f"declarada {d} [this-process]; {val} prontos p/ injetar [readiness] — "
                f"estado da flag de injecao so no env PROD")
    # empty
    return f"declarada {d} [this-process]; 0 prontos [readiness] — nada a injetar mesmo se ON"


def handle_flags(args):
    """Estado das flags de evolucao: declarado [this-process] x db_evidence [PROD].

    O bloco `db_evidence` e env-INDEPENDENTE (le o banco, que aponta p/ PROD) e e o
    que fecha o blind spot: rodando local, o declarado e local, mas a evidencia DB
    revela o estado EFETIVO em PROD. Custo $0.
    """
    metrics, warnings, window_meta = _compute_evidence(args.days)
    scope = _scope_info()

    flags = []
    for attr, env_var, default, grupo, evidence_key, evidence_kind in EVOLUTION_FLAGS:
        declared = _read_flag(attr, env_var, default)
        evidence = _evidence_for(evidence_key, evidence_kind, metrics)
        flags.append({
            'attr': attr,
            'env_var': env_var,
            'grupo': grupo,
            'default': bool(default),
            'declared': bool(declared),
            'db_evidence': evidence,
            'verdict': _verdict(declared, evidence),
        })

    declarados_on = sum(1 for f in flags if f['declared'])
    efetivas_prod = sum(1 for f in flags if f['db_evidence']['signal'] == 'active')

    data = {
        'scope': scope,
        'total_flags': len(flags),
        'declarados_on': declarados_on,
        'efetivas_prod_por_evidencia': efetivas_prod,
        'evidence_window': window_meta,
        'flags': flags,
    }

    if args.json_mode:
        success_output('flags', data, json_mode=True, warnings=warnings)
        return

    print("Flags de evolucao do Agente Web (Ondas 0-4 + loop corretivo):\n")
    print(f"  Procedencia: dados={scope['data_source']} | flags={scope['flags_source']}")
    print(f"  Declaradas ON [this-process]: {declarados_on}/{len(flags)} | "
          f"com rastro DB (efetivas PROD): {efetivas_prod}\n")
    rows = []
    for f in flags:
        ev = f['db_evidence']
        if ev['signal'] == 'none':
            ev_str = '-'
        elif ev['signal'] == 'unknown':
            ev_str = '?'
        else:
            ev_str = f"{ev['metric']}={ev['value']}"
        rows.append([
            f['grupo'],
            f['env_var'],
            'ON' if f['declared'] else 'OFF',
            ev_str,
        ])
    print(format_table(['Grupo', 'Env var', 'Declar', 'Evidencia DB (PROD)'], rows))
    for w in warnings:
        print(f"  [!] {w}")


def handle_gates(args):
    """Estado dos gates de acesso runtime (permissions.py + flags de enforcement).

    Reporta os controles que GOVERNAM o que o agente web/Teams pode executar. Os
    valores de enforcement/flag sao [this-process] (env). allow-list vem das
    constantes de permissions.py. Custo $0.
    """
    scope = _scope_info()
    warnings = []

    # Constantes/flags de permissions.py + feature_flags (tolerante).
    estoque_enforce = _read_flag('USE_ESTOQUE_RESTRICAO_ENFORCEMENT', 'AGENT_ESTOQUE_RESTRICAO_ENFORCEMENT', True)
    estoque_allow = None
    try:
        # A constante mora em feature_flags (definida via _parse_allowed_user_ids_csv), NAO em
        # permissions (la e import LOCAL dentro de can_use_tool). Review HIGH-2.
        from app.agente.config.feature_flags import ESTOQUE_RESTRICAO_ALLOWED_USER_IDS
        estoque_allow = sorted(int(x) for x in ESTOQUE_RESTRICAO_ALLOWED_USER_IDS)
    except Exception as e:
        warnings.append(f"allow-list de estoque indisponivel: {e}")

    debug_flag = _read_flag('USE_DEBUG_MODE', 'AGENT_DEBUG_MODE', True)
    reversibility = _read_flag('USE_REVERSIBILITY_CHECK', 'AGENT_REVERSIBILITY_CHECK', True)
    hard_enforce = _read_flag('USE_MANDATORY_HARD_ENFORCE', 'AGENT_MANDATORY_HARD_ENFORCE', False)

    # Shape FIXO e homogeneo entre gates (snapshot-estavel): name/enforcement/
    # enabled/flag/allow_list/blocks/source.
    gates = [
        {
            'name': 'gerindo_write',
            'enforcement': 'always_deny',
            'enabled': True,
            'flag': None,
            'allow_list': None,
            'blocks': 'agente web/Teams executar via Bash os WRITE da skill: '
                      + ', '.join(GERINDO_WRITE_BLOCKED),
            'source': 'permissions._classify_gerindo_write',
        },
        {
            'name': 'estoque_restricao',
            'enforcement': 'flag_gated',
            'enabled': bool(estoque_enforce),
            'flag': 'AGENT_ESTOQUE_RESTRICAO_ENFORCEMENT',
            'allow_list': estoque_allow,
            'blocks': 'skills WRITE de ajuste/Indisponivel de estoque p/ user fora da allow-list '
                      '(ajustando-quant; transferindo-interno se Indisponivel; planejando-pre-etapa executar-onda)',
            'source': 'permissions._classify_estoque_restricao',
        },
        {
            'name': 'debug_mode',
            'enforcement': 'per_session',
            'enabled': None,  # ContextVar por sessao (admin) — nao estaticamente conhecivel
            'flag': 'AGENT_DEBUG_MODE',
            'allow_list': None,
            'blocks': 'acesso cross-user (target_user_id) e tabelas internas — liberado so a admin via toggle',
            'source': 'permissions.get_debug_mode (ContextVar)',
        },
        {
            'name': 'reversibility_check',
            'enforcement': 'flag_gated_warn',
            'enabled': bool(reversibility),
            'flag': 'AGENT_REVERSIBILITY_CHECK',
            'allow_list': None,
            'blocks': 'NAO bloqueia — emite destructive_action_warning (SSE) p/ confirmacao no frontend '
                      '(o deny efetivo fica a cargo do AskUserQuestion do SDK)',
            'source': 'permissions._classify_destructive_action',
        },
        {
            'name': 'mandatory_hard_enforce',
            'enforcement': 'flag_gated',
            'enabled': bool(hard_enforce),
            'flag': 'AGENT_MANDATORY_HARD_ENFORCE',
            'allow_list': None,
            'blocks': 'PreToolUse bloqueia tool cujo input contem token ENFORCE_DENY_SUBSTR de regra dura curada',
            'source': 'feature_flags.USE_MANDATORY_HARD_ENFORCE (hooks PreToolUse)',
        },
    ]
    # Flag debug (auxiliar) p/ contexto, ja que enabled fica null (per_session).
    debug_flag_value = bool(debug_flag)

    data = {
        'scope': scope,
        'debug_mode_flag': debug_flag_value,
        'gates': gates,
    }

    if args.json_mode:
        success_output('gates', data, json_mode=True, warnings=warnings)
        return

    print("Gates de acesso do Agente Web (runtime):\n")
    print(f"  (enforcement/flags = {scope['flags_source']})\n")
    rows = []
    for g in gates:
        if g['enabled'] is True:
            en = 'SIM'
        elif g['enabled'] is False:
            en = 'NAO'
        else:
            en = 'sessao'
        rows.append([
            g['name'],
            g['enforcement'],
            en,
            ','.join(str(x) for x in g['allow_list']) if g['allow_list'] else '-',
            truncate(g['blocks'], 52),
        ])
    print(format_table(['Gate', 'Enforcement', 'Ativo', 'Allow-list', 'Bloqueia'], rows))
    print(f"\n  USE_DEBUG_MODE (flag): {'ON' if debug_flag_value else 'OFF'}")
    for w in warnings:
        print(f"  [!] {w}")


def _redis_client():
    """Cliente Redis pelo mesmo padrao dos workers (REDIS_URL, default localhost)."""
    import redis
    redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    return redis.Redis.from_url(redis_url)


def handle_worker_status(args):
    """Filas RQ do agente + workers vivos. Degrada (reachable=False) se Redis off.

    SHAPE FIXO mesmo sem Redis (reachable/queues/workers sempre presentes) p/ o
    snapshot P12. NUNCA usa status=query_error. Le o Redis DESTE processo (local p/
    dev, PROD p/ agente web) — `scope.redis_target` rotula. Custo $0.
    """
    scope = _scope_info()
    warnings = []
    reachable = False
    queues = []
    workers = []

    try:
        r = _redis_client()
        r.ping()
        reachable = True
    except Exception as e:
        warnings.append(f"Redis inacessivel ({scope['redis_target']}): {e}")
        r = None

    if reachable:
        try:
            from rq import Queue, Worker
            from rq.registry import StartedJobRegistry, FailedJobRegistry
            for name in AGENT_QUEUES:
                try:
                    q = Queue(name, connection=r)
                    started = StartedJobRegistry(name, connection=r).count
                    failed = FailedJobRegistry(name, connection=r).count
                    queues.append({
                        'name': name,
                        'queued': int(q.count),
                        'started': int(started),
                        'failed': int(failed),
                    })
                except Exception as e:
                    queues.append({'name': name, 'queued': None, 'started': None, 'failed': None})
                    warnings.append(f"fila {name} indisponivel: {e}")
            try:
                for w in Worker.all(connection=r):
                    qn = []
                    try:
                        qn = list(w.queue_names())
                    except Exception:
                        qn = []
                    workers.append({
                        'name': w.name,
                        'state': getattr(w, 'state', None),
                        'queues': qn,
                    })
            except Exception as e:
                warnings.append(f"Worker.all indisponivel: {e}")
        except Exception as e:
            warnings.append(f"rq indisponivel: {e}")

    data = {
        'scope': scope,
        'reachable': bool(reachable),
        'workers_total': len(workers),
        'queues': queues,
        'workers': workers,
    }

    if args.json_mode:
        success_output('worker-status', data, json_mode=True, warnings=warnings)
        return

    print("Filas RQ do Agente Web + workers:\n")
    print(f"  Redis ({scope['redis_target']}): {'OK' if reachable else 'INACESSIVEL'}\n")
    if queues:
        rows = [[
            q['name'],
            '-' if q['queued'] is None else str(q['queued']),
            '-' if q['started'] is None else str(q['started']),
            '-' if q['failed'] is None else str(q['failed']),
        ] for q in queues]
        print(format_table(['Fila', 'Enfileirados', 'Em execucao', 'Falhos'], rows))
    if workers:
        print(f"\n  Workers vivos: {len(workers)}")
        for w in workers:
            print(f"    - {w['name']} [{w['state']}] filas={','.join(w['queues']) or '-'}")
    elif reachable:
        print("\n  (Nenhum worker vivo registrado neste Redis.)")
    for w in warnings:
        print(f"  [!] {w}")


HANDLERS = {
    'flags': handle_flags,
    'gates': handle_gates,
    'worker-status': handle_worker_status,
}


def main():
    run_handler('Observabilidade de infra/seguranca do Agente Web (READ)', SUBCOMMANDS, HANDLERS)


if __name__ == '__main__':
    main()
