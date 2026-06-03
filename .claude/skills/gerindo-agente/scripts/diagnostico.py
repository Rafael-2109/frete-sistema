#!/usr/bin/env python3
"""
Dominio 5: Diagnosticos — insights, metricas, saude, efetividade, conflitos, friccao e briefing.

Subcomandos:
  insights           Insights completos do agente (custos, resolucao, tendencias)
  memory-metrics     Metricas de qualidade do sistema de memoria
  health             Health score composto (0-100)
  effectiveness      Memorias mais/menos efetivas
  cold-candidates    Memorias candidatas a tier frio
  conflicts          Memorias com conflito potencial
  embedding-coverage Cobertura de embeddings (memorias e sessoes)
  friction           Analise detalhada de friccao (5 sinais)
  briefing           Visualizar briefing intersessao atual

  -- Camada de evolucao/qualidade (Onda 1, dado em agent_step + insights $0) --
  step-quality       Qualidade por-turno: judge score/label, vies sem-tool, adversarial refutou
  step-coverage      Cobertura de sinal por canal (web/teams) + gargalo PlanState
  rule-adhesion      Adesao de regras / loop corretivo (reincidencia por error_signature) — $0
  routing            Metricas de roteamento (ambiguidade, struggling, skills) — $0
  recommendations    Recomendacoes acionaveis completas (rule-based, ate 5) — $0

Escopo: subcomandos da camada de evolucao aceitam --all (sistema inteiro).
Sem --all, usam --user-id. Distinguem 'empty'/'query_error' de zero silencioso.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

from common import (
    error_exit, format_datetime, format_json, format_table,
    get_app_context, parse_args_with_subcommands, resolve_user,
    success_output, truncate,
)


SUBCOMMANDS = {
    'insights': {
        'help': 'Insights completos do agente',
        'args': [
            {'name': '--days', 'type': int, 'default': 30, 'help': 'Periodo em dias (default: 30)'},
        ],
    },
    'memory-metrics': {
        'help': 'Metricas de qualidade do sistema de memoria',
        'args': [
            {'name': '--days', 'type': int, 'default': 30, 'help': 'Periodo em dias (default: 30)'},
        ],
    },
    'health': {
        'help': 'Health score composto (0-100)',
        'args': [
            {'name': '--days', 'type': int, 'default': 30, 'help': 'Periodo em dias (default: 30)'},
        ],
    },
    'effectiveness': {
        'help': 'Memorias mais/menos efetivas',
        'args': [],
    },
    'cold-candidates': {
        'help': 'Memorias candidatas a tier frio',
        'args': [],
    },
    'conflicts': {
        'help': 'Memorias com conflito potencial',
        'args': [],
    },
    'embedding-coverage': {
        'help': 'Cobertura de embeddings (memorias e sessoes)',
        'args': [],
    },
    'friction': {
        'help': 'Analise detalhada de friccao (5 sinais)',
        'args': [
            {'name': '--days', 'type': int, 'default': 30, 'help': 'Periodo em dias (default: 30)'},
        ],
    },
    'briefing': {
        'help': 'Visualizar briefing intersessao atual',
        'args': [],
    },
    'step-quality': {
        'help': 'Qualidade por-turno (judge/verify) de agent_step',
        'args': [
            {'name': '--days', 'type': int, 'default': 30, 'help': 'Periodo em dias (default: 30)'},
            {'name': '--all', 'action': 'store_true', 'dest': 'all_users', 'help': 'Sistema inteiro (todos os usuarios)'},
        ],
    },
    'step-coverage': {
        'help': 'Cobertura de sinal por canal + gargalo PlanState',
        'args': [
            {'name': '--days', 'type': int, 'default': 30, 'help': 'Periodo em dias (default: 30)'},
            {'name': '--all', 'action': 'store_true', 'dest': 'all_users', 'help': 'Sistema inteiro (todos os usuarios)'},
        ],
    },
    'rule-adhesion': {
        'help': 'Adesao de regras / loop corretivo (custo $0)',
        'args': [
            {'name': '--days', 'type': int, 'default': 30, 'help': 'Periodo em dias (default: 30)'},
            {'name': '--all', 'action': 'store_true', 'dest': 'all_users', 'help': 'Sistema inteiro (todos os usuarios)'},
        ],
    },
    'routing': {
        'help': 'Metricas de roteamento (custo $0)',
        'args': [
            {'name': '--days', 'type': int, 'default': 30, 'help': 'Periodo em dias (default: 30)'},
            {'name': '--all', 'action': 'store_true', 'dest': 'all_users', 'help': 'Sistema inteiro (todos os usuarios)'},
        ],
    },
    'recommendations': {
        'help': 'Recomendacoes acionaveis completas (custo $0)',
        'args': [
            {'name': '--days', 'type': int, 'default': 30, 'help': 'Periodo em dias (default: 30)'},
            {'name': '--all', 'action': 'store_true', 'dest': 'all_users', 'help': 'Sistema inteiro (todos os usuarios)'},
        ],
    },
    'status': {
        'help': 'Status canonico consolidado (agregador unico, 1x get_insights_data)',
        'args': [
            {'name': '--days', 'type': int, 'default': 30, 'help': 'Periodo em dias (default: 30)'},
            {'name': '--all', 'action': 'store_true', 'dest': 'all_users', 'help': 'Sistema inteiro (todos os usuarios)'},
        ],
    },
}


def handle_insights(args):
    """Insights completos do agente."""
    from app.agente.services.insights_service import get_insights_data

    data = get_insights_data(days=args.days, user_id=args.user_id, compare=True)

    if args.json_mode:
        print(format_json(data))
    else:
        overview = data.get('overview', {})
        print(f"Insights do Agente ({args.days} dias):\n")
        print(f"  Sessoes: {overview.get('total_sessions', 0)}")
        print(f"  Mensagens: {overview.get('total_messages', 0)}")
        print(f"  Custo total: ${overview.get('total_cost_usd', 0):.4f}")
        print(f"  Custo/sessao: ${overview.get('avg_cost_per_session', 0):.4f}")
        print(f"  Usuarios unicos: {overview.get('unique_users', 0)}")

        print(f"\n  Resolucao: {data.get('resolution_rate', 0):.1f}%")
        print(f"  Custo/resolucao: ${data.get('cost_per_resolution', 0):.4f}")
        print(f"  Health Score: {data.get('health_score', 0):.1f}/100")
        print(f"  Adocao: {data.get('adoption_rate', 0):.1f}%")

        friction = data.get('friction', {})
        print(f"  Friccao: {friction.get('friction_score', 0)}")

        deltas = data.get('deltas', {})
        if any(v is not None for v in deltas.values()):
            print(f"\n  Deltas vs periodo anterior:")
            for key, val in deltas.items():
                if val is not None:
                    sinal = '+' if val > 0 else ''
                    print(f"    {key}: {sinal}{val:.1f}%")

        # Top tools
        tools = data.get('tools', {}).get('most_used', [])[:5]
        if tools:
            print(f"\n  Top 5 tools:")
            for t in tools:
                print(f"    {t['tool']}: {t['count']}x")

        # Topicos
        topics = data.get('topics', [])[:5]
        if topics:
            print(f"\n  Top topicos:")
            for t in topics:
                print(f"    {t['topic']}: {t['count']}x")

        recommendations = data.get('recommendations', [])
        if recommendations:
            print(f"\n  Recomendacoes:")
            for r in recommendations[:3]:
                if isinstance(r, dict):
                    print(f"    - {r.get('text', r.get('message', str(r)))}")
                else:
                    print(f"    - {r}")


def handle_memory_metrics(args):
    """Metricas de qualidade do sistema de memoria."""
    from app.agente.services.insights_service import get_memory_metrics

    data = get_memory_metrics(days=args.days, user_id=args.user_id)

    if args.json_mode:
        print(format_json(data))
    else:
        print(f"Metricas de Memoria ({args.days} dias):\n")
        print(f"  Total memorias: {data.get('total_memories', 0)}")
        print(f"  Utilizacao: {data.get('utilization_rate', 0):.1f}%")
        print(f"  Acessadas no periodo: {data.get('accessed_in_period', 0)}")
        print(f"  Correcoes no periodo: {data.get('corrections_count', 0)}")
        print(f"  Importance medio: {data.get('avg_importance_score', 0):.3f}")
        print(f"  Embeddings orfaos: {data.get('orphan_embeddings', 0)}")

        corr_stats = data.get('correction_count_stats', {})
        if corr_stats:
            print(f"\n  Correcoes (campo correction_count):")
            print(f"    Memorias com correcoes: {corr_stats.get('memories_with_corrections', 0)}")
            print(f"    Total correcoes: {corr_stats.get('total_corrections', 0)}")
            print(f"    Media/memoria: {corr_stats.get('avg_per_memory', 0):.2f}")

        decay = data.get('decay_distribution', {})
        if decay:
            print(f"\n  Distribuicao de idade:")
            for bucket, count in decay.items():
                print(f"    {bucket}: {count}")

        cats = data.get('categories', {})
        if cats:
            print(f"\n  Por categoria de path:")
            for cat, count in sorted(cats.items(), key=lambda x: x[1], reverse=True):
                print(f"    {cat}: {count}")

        kg = data.get('knowledge_graph', {})
        if kg:
            print(f"\n  Knowledge Graph:")
            print(f"    Entidades: {kg.get('total_entities', 0)}")
            print(f"    Links: {kg.get('total_links', 0)}")
            print(f"    Relacoes: {kg.get('total_relations', 0)}")

        most_corrected = data.get('most_corrected_memories', [])
        if most_corrected:
            print(f"\n  Top 5 mais corrigidas:")
            for m in most_corrected:
                print(f"    {m['path']} ({m['correction_count']}x corrigida, {m['usage_count']}x usada)")


def handle_health(args):
    """Health score composto."""
    from app.agente.services.insights_service import get_insights_data

    data = get_insights_data(days=args.days, user_id=args.user_id, compare=True)

    health = data.get('health_score', 0)
    resolution = data.get('resolution_rate', 0)
    friction = data.get('friction', {}).get('friction_score', 0)
    adoption = data.get('adoption_rate', 0)

    if args.json_mode:
        print(format_json({
            'health_score': health,
            'resolution_rate': resolution,
            'friction_score': friction,
            'adoption_rate': adoption,
            'period_days': args.days,
        }))
    else:
        # Classificacao
        if health >= 80:
            status = 'EXCELENTE'
        elif health >= 60:
            status = 'BOM'
        elif health >= 40:
            status = 'REGULAR'
        else:
            status = 'CRITICO'

        print(f"Health Score: {health:.1f}/100 ({status})\n")
        print(f"  Resolucao: {resolution:.1f}% (peso 35%)")
        print(f"  Friccao: {friction} (peso 25%, invertido)")
        print(f"  Adocao: {adoption:.1f}% (peso 20%)")
        print(f"  Estabilidade custo: peso 20%")
        print(f"\n  Periodo: {args.days} dias")


def handle_effectiveness(args):
    """Memorias mais/menos efetivas."""
    from app.agente.models import AgentMemory

    # Mais efetivas (usage > 0, ordenar por effective/usage ratio)
    effective = AgentMemory.query.filter(
        AgentMemory.user_id == args.user_id,
        AgentMemory.is_directory == False,  # noqa: E712
        AgentMemory.usage_count > 0,
    ).order_by(
        (AgentMemory.effective_count * 1.0 / AgentMemory.usage_count).desc()
    ).limit(args.limit).all()

    if args.json_mode:
        data = [{
            'path': m.path,
            'usage_count': m.usage_count,
            'effective_count': m.effective_count,
            'ratio': round(m.effective_count / m.usage_count, 3) if m.usage_count > 0 else 0,
            'category': m.category,
            'is_cold': m.is_cold,
        } for m in effective]
        print(format_json({'total': len(data), 'memorias': data}))
    else:
        if not effective:
            print("Nenhuma memoria com dados de uso.")
            return

        print(f"Efetividade de Memorias ({len(effective)}):\n")
        rows = []
        for m in effective:
            ratio = round(m.effective_count / m.usage_count, 3) if m.usage_count > 0 else 0
            rows.append([
                truncate(m.path, 40),
                str(m.usage_count),
                str(m.effective_count),
                f"{ratio:.1%}",
                m.category,
                'COLD' if m.is_cold else '-',
            ])
        print(format_table(
            ['Path', 'Uso', 'Efetivo', 'Ratio', 'Cat.', 'Status'],
            rows
        ))


def handle_cold_candidates(args):
    """Memorias candidatas a tier frio."""
    from app.agente.models import AgentMemory

    candidates = AgentMemory.query.filter(
        AgentMemory.user_id == args.user_id,
        AgentMemory.is_directory == False,  # noqa: E712
        AgentMemory.usage_count >= 20,
        AgentMemory.effective_count == 0,
        AgentMemory.is_cold == False,  # noqa: E712
    ).order_by(AgentMemory.usage_count.desc()).limit(args.limit).all()

    if args.json_mode:
        data = [{
            'path': m.path,
            'usage_count': m.usage_count,
            'category': m.category,
            'importance_score': round(m.importance_score, 2),
            'updated_at': format_datetime(m.updated_at),
        } for m in candidates]
        print(format_json({'total': len(data), 'candidatos': data}))
    else:
        if not candidates:
            print("Nenhuma memoria candidata a tier frio.")
            return

        print(f"Candidatas a Tier Frio ({len(candidates)}):")
        print("(Criterio: uso >= 20x, efetividade = 0)\n")
        rows = []
        for m in candidates:
            rows.append([
                truncate(m.path, 40),
                str(m.usage_count),
                m.category,
                str(round(m.importance_score, 2)),
                format_datetime(m.updated_at),
            ])
        print(format_table(['Path', 'Uso', 'Cat.', 'Imp.', 'Atualizado'], rows))


def handle_conflicts(args):
    """Memorias com conflito potencial."""
    from app.agente.models import AgentMemory

    conflicts = AgentMemory.query.filter(
        AgentMemory.user_id == args.user_id,
        AgentMemory.is_directory == False,  # noqa: E712
        AgentMemory.has_potential_conflict == True,  # noqa: E712
    ).order_by(AgentMemory.updated_at.desc()).limit(args.limit).all()

    if args.json_mode:
        data = [{
            'id': m.id,
            'path': m.path,
            'category': m.category,
            'content_preview': truncate(m.content, 200) if m.content else '',
            'usage_count': m.usage_count,
            'correction_count': m.correction_count,
            'updated_at': format_datetime(m.updated_at),
        } for m in conflicts]
        print(format_json({'total': len(data), 'conflitos': data}))
    else:
        if not conflicts:
            print("Nenhuma memoria com conflito potencial.")
            return

        print(f"Memorias com Conflito Potencial ({len(conflicts)}):\n")
        for m in conflicts:
            print(f"  [{m.category}] {m.path}")
            print(f"    Uso: {m.usage_count}x | Correcoes: {m.correction_count}x")
            print(f"    {truncate(m.content, 100) if m.content else '(vazio)'}")
            print()


def handle_embedding_coverage(args):
    """Cobertura de embeddings."""
    from app import db
    from app.agente.models import AgentMemory
    from sqlalchemy import text

    user_id = args.user_id

    # Total memorias (arquivos)
    total_memories = AgentMemory.query.filter(
        AgentMemory.user_id == user_id,
        AgentMemory.is_directory == False,  # noqa: E712
    ).count()

    # Memorias com embedding
    mem_with_embed = 0
    try:
        result = db.session.execute(text("""
            SELECT COUNT(DISTINCT memory_id)
            FROM agent_memory_embeddings
            WHERE user_id = :uid
        """), {'uid': user_id})
        mem_with_embed = result.scalar() or 0
    except Exception:
        db.session.rollback()

    # Sessoes totais
    from app.agente.models import AgentSession
    total_sessions = AgentSession.query.filter_by(user_id=user_id).count()

    # Sessoes com embedding (session turns)
    sess_with_embed = 0
    try:
        result = db.session.execute(text("""
            SELECT COUNT(DISTINCT session_id)
            FROM session_turn_embeddings
            WHERE user_id = :uid
        """), {'uid': user_id})
        sess_with_embed = result.scalar() or 0
    except Exception:
        db.session.rollback()

    data = {
        'memorias': {
            'total': total_memories,
            'com_embedding': mem_with_embed,
            'cobertura': round(mem_with_embed / total_memories * 100, 1) if total_memories > 0 else 0,
        },
        'sessoes': {
            'total': total_sessions,
            'com_embedding': sess_with_embed,
            'cobertura': round(sess_with_embed / total_sessions * 100, 1) if total_sessions > 0 else 0,
        },
    }

    if args.json_mode:
        print(format_json(data))
    else:
        print(f"Cobertura de Embeddings (user_id={user_id}):\n")
        mem = data['memorias']
        print(f"  Memorias: {mem['com_embedding']}/{mem['total']} ({mem['cobertura']:.1f}%)")
        sess = data['sessoes']
        print(f"  Sessoes:  {sess['com_embedding']}/{sess['total']} ({sess['cobertura']:.1f}%)")


def handle_friction(args):
    """Analise detalhada de friccao."""
    from app.agente.services.friction_analyzer import analyze_friction

    data = analyze_friction(days=args.days, user_id=args.user_id)

    if args.json_mode:
        print(format_json(data))
    else:
        score = data.get('friction_score', 0)
        total = data.get('total_sessions_analyzed', 0)

        if total == 0:
            print("Sem dados suficientes para analise de friccao.")
            return

        # Classificacao
        if score < 20:
            status = 'BAIXA'
        elif score < 50:
            status = 'MODERADA'
        else:
            status = 'ALTA'

        print(f"Analise de Friccao ({args.days} dias, {total} sessoes):\n")
        print(f"  Score: {score}/100 ({status})\n")

        # Sinal 1: Queries repetidas
        repeated = data.get('repeated_queries', [])
        print(f"  1. Queries repetidas: {len(repeated)} cluster(s)")
        for r in repeated[:5]:
            print(f"     - \"{truncate(r.get('query', ''), 60)}\" ({r.get('count', 0)}x em {r.get('sessions', 0)} sessoes)")

        # Sinal 2: Sessoes abandonadas
        abandoned = data.get('abandoned_sessions', [])
        print(f"\n  2. Sessoes abandonadas: {len(abandoned)}")
        for a in abandoned[:5]:
            print(f"     - {a.get('session_id', '?')[:16]}... ({a.get('message_count', 0)} msgs)")

        # Sinal 3: Sinais de frustracao
        frustration = data.get('frustration_signals', [])
        print(f"\n  3. Sinais de frustracao: {len(frustration)} sessoes")
        for f in frustration[:5]:
            signals = f.get('signals', [])
            markers = [s.get('marker', '') for s in signals[:2]]
            print(f"     - {f.get('session_id', '?')[:16]}... ({f.get('signal_count', 0)} sinais: {', '.join(markers)})")

        # Sinal 4: Sessoes sem tools
        no_tools = data.get('no_tool_sessions', [])
        print(f"\n  4. Sessoes sem tools: {len(no_tools)}")
        for n in no_tools[:5]:
            print(f"     - {n.get('session_id', '?')[:16]}... ({n.get('message_count', 0)} msgs, ${n.get('cost_usd', 0):.4f})")

        # Resumo
        summary = data.get('summary', '')
        if summary:
            print(f"\n  Resumo: {summary}")


def handle_briefing(args):
    """Visualizar briefing intersessao atual."""
    from app.agente.services.intersession_briefing import build_intersession_briefing

    xml = build_intersession_briefing(user_id=args.user_id)

    if args.json_mode:
        print(format_json({
            'user_id': args.user_id,
            'has_briefing': xml is not None,
            'briefing_xml': xml,
        }))
    else:
        if not xml:
            print("Nenhum briefing disponivel (sem eventos relevantes desde a ultima sessao).")
            return

        print(f"Briefing Intersessao (user_id={args.user_id}):\n")
        print(xml)


# ─────────────────────────────────────────────────────────────────────────
# Camada de evolucao/qualidade (Onda 1) — agent_step + insights $0.
# Escopo: --all => sistema inteiro (user_id=None); senao --user-id.
# Distinguem 'empty'/'query_error'/'feature_disabled' de zero silencioso.
# ─────────────────────────────────────────────────────────────────────────

def _scope_uid(args):
    """Resolve escopo: None (sistema inteiro) se --all, senao o --user-id."""
    return None if getattr(args, 'all_users', False) else args.user_id


def _scope_label(args):
    return 'TODOS os usuarios' if _scope_uid(args) is None else f'user_id={args.user_id}'


def _classify_health(score):
    """Classificacao textual do health score (0-100)."""
    if score >= 80:
        return 'EXCELENTE'
    if score >= 60:
        return 'BOM'
    if score >= 40:
        return 'REGULAR'
    return 'CRITICO'


def _embedding_coverage(uid):
    """Cobertura de embeddings (memorias + sessoes), --all-safe (uid=None => sistema).

    Replica handle_embedding_coverage mas com filtro `(:uid IS NULL OR ...)` para
    suportar escopo de sistema inteiro. Tabelas podem nao existir (try/except).
    """
    from app import db
    from app.agente.models import AgentMemory, AgentSession
    from sqlalchemy import text

    mq = AgentMemory.query.filter(AgentMemory.is_directory == False)  # noqa: E712
    if uid is not None:
        mq = mq.filter(AgentMemory.user_id == uid)
    total_memories = mq.count()

    mem_embed = 0
    try:
        mem_embed = db.session.execute(text(
            "SELECT COUNT(DISTINCT memory_id) FROM agent_memory_embeddings "
            "WHERE (:uid IS NULL OR user_id = :uid)"
        ), {'uid': uid}).scalar() or 0
    except Exception:
        db.session.rollback()

    sq = AgentSession.query
    if uid is not None:
        sq = sq.filter_by(user_id=uid)
    total_sessions = sq.count()

    sess_embed = 0
    try:
        sess_embed = db.session.execute(text(
            "SELECT COUNT(DISTINCT session_id) FROM session_turn_embeddings "
            "WHERE (:uid IS NULL OR user_id = :uid)"
        ), {'uid': uid}).scalar() or 0
    except Exception:
        db.session.rollback()

    return {
        'memorias': {
            'total': total_memories,
            'com_embedding': mem_embed,
            'cobertura': round(mem_embed / total_memories * 100, 1) if total_memories else 0,
        },
        'sessoes': {
            'total': total_sessions,
            'com_embedding': sess_embed,
            'cobertura': round(sess_embed / total_sessions * 100, 1) if total_sessions else 0,
        },
    }


def _loop_health(days, uid):
    """PlanState / loop-health (--all-safe). Replica a plan_sql de step-coverage.

    Sinaliza o gargalo B1 (PlanState ~0 -> promocao A4 vira no-op). Inclui
    'status': 'query_error' se a consulta falhar (degradacao graciosa).
    """
    from app import db
    from app.utils.timezone import agora_utc_naive
    from datetime import timedelta
    from sqlalchemy import text

    since = agora_utc_naive() - timedelta(days=days)
    try:
        row = db.session.execute(text("""
            SELECT count(*) AS total,
                   count(*) FILTER (WHERE data::jsonb ? 'plan') AS with_plan,
                   count(*) FILTER (WHERE session_id LIKE 'teams_%') AS teams_sessions
            FROM agent_sessions
            WHERE created_at >= :since AND (:uid IS NULL OR user_id = :uid)
        """), {'since': since, 'uid': uid}).fetchone()
    except Exception as e:
        db.session.rollback()
        return {'status': 'query_error', 'error': str(e)}

    total = (row.total or 0) if row else 0
    with_plan = (row.with_plan or 0) if row else 0
    teams = (row.teams_sessions or 0) if row else 0
    pct = round(100.0 * with_plan / total, 1) if total else 0.0
    return {
        'status': 'ok',
        'sessions_total': total,
        'with_plan': with_plan,
        'with_plan_pct': pct,
        'teams_sessions': teams,
        'gargalo_b1': bool(total > 0 and pct < 5),
    }


def _memoria_stats(uid):
    """Agregado leve de memorias (espelha memoria.stats), --all-safe (uid=None => sistema).

    Fecha o item 'stats' do agregador status com escalares distintos de memory-metrics:
    total de caracteres, media de uso/efetividade, conflitos e distribuicao por escopo.
    """
    from app import db
    from app.agente.models import AgentMemory
    from sqlalchemy import func

    base = [AgentMemory.is_directory == False]  # noqa: E712
    if uid is not None:
        base.append(AgentMemory.user_id == uid)

    total_chars = db.session.query(func.sum(func.length(AgentMemory.content))).filter(*base).scalar() or 0
    conflitos = AgentMemory.query.filter(*base, AgentMemory.has_potential_conflict == True).count()  # noqa: E712
    avg_usage = db.session.query(func.avg(AgentMemory.usage_count)).filter(*base).scalar() or 0
    avg_effective = db.session.query(func.avg(AgentMemory.effective_count)).filter(*base).scalar() or 0
    escopo_counts = db.session.query(
        AgentMemory.escopo, func.count(AgentMemory.id)
    ).filter(*base).group_by(AgentMemory.escopo).all()

    return {
        'total_caracteres': int(total_chars),
        'conflitos': conflitos,
        'media_uso': round(float(avg_usage), 1),
        'media_efetividade': round(float(avg_effective), 1),
        'por_escopo': {esc: count for esc, count in escopo_counts},
    }


def handle_step_quality(args):
    """Qualidade por-turno: judge score/label, vies sem-tool, adversarial refutou.

    Fonte: agent_step.outcome_signal (gravado por workers/step_judge.py + plan_verifier.py).
    Surface o sinal de ACERTO real (substitui as proxies de eco). O contraste
    'judge=success MAS adversarial refutou' expoe o vies sem-tool do judge.
    """
    from app import db
    from app.utils.timezone import agora_utc_naive
    from datetime import timedelta
    from sqlalchemy import text

    uid = _scope_uid(args)
    since = agora_utc_naive() - timedelta(days=args.days)
    params = {'since': since, 'uid': uid}

    agg_sql = text("""
        SELECT
          count(*) AS total,
          count(*) FILTER (WHERE outcome_signal::jsonb ? 'judge') AS judged,
          avg((outcome_signal::jsonb->'judge'->>'score')::numeric)
             FILTER (WHERE (outcome_signal::jsonb->'judge'->>'score') ~ '^[0-9]+$') AS avg_score,
          count(*) FILTER (WHERE outcome_signal::jsonb->'judge'->>'label' = 'success') AS judge_success,
          count(*) FILTER (WHERE outcome_signal::jsonb->'judge'->>'label' = 'failure') AS judge_failure,
          count(*) FILTER (WHERE (outcome_signal::jsonb->'judge'->>'componente_culpado') IS NOT NULL
                            AND (outcome_signal::jsonb->'judge'->>'componente_culpado') <> 'null') AS with_culpado,
          count(*) FILTER (WHERE (outcome_signal::jsonb->'verify'->'adversarial'->>'refuted') = 'true') AS adversarial_refuted,
          count(*) FILTER (WHERE outcome_signal::jsonb->'judge'->>'label' = 'success'
                            AND (outcome_signal::jsonb->'verify'->'adversarial'->>'refuted') = 'true') AS success_but_refuted,
          count(*) FILTER (WHERE (outcome_signal::jsonb->>'frustration_score') ~ '^[0-9]+$'
                            AND (outcome_signal::jsonb->>'frustration_score')::int >= 3) AS high_frustration
        FROM agent_step
        WHERE created_at >= :since AND (:uid IS NULL OR user_id = :uid)
    """)
    label_sql = text("""
        SELECT COALESCE(outcome_signal::jsonb->'judge'->>'label', '(sem label)') AS label, count(*) AS n
        FROM agent_step
        WHERE created_at >= :since AND (:uid IS NULL OR user_id = :uid)
          AND outcome_signal::jsonb ? 'judge'
        GROUP BY 1 ORDER BY n DESC
    """)
    culpado_sql = text("""
        SELECT outcome_signal::jsonb->'judge'->>'componente_culpado' AS comp, count(*) AS n
        FROM agent_step
        WHERE created_at >= :since AND (:uid IS NULL OR user_id = :uid)
          AND (outcome_signal::jsonb->'judge'->>'componente_culpado') IS NOT NULL
          AND (outcome_signal::jsonb->'judge'->>'componente_culpado') <> 'null'
        GROUP BY 1 ORDER BY n DESC LIMIT 10
    """)
    try:
        row = db.session.execute(agg_sql, params).fetchone()
        labels = db.session.execute(label_sql, params).fetchall()
        culpados = db.session.execute(culpado_sql, params).fetchall()
    except Exception as e:
        db.session.rollback()
        err = {'status': 'query_error', 'error': str(e)}
        print(format_json(err) if args.json_mode else f"Erro ao consultar agent_step: {e}")
        return

    total = (row.total if row else 0) or 0
    data = {
        'status': 'ok' if total > 0 else 'empty',
        'period_days': args.days,
        'scope': _scope_label(args),
        'total_steps': total,
        'judged': (row.judged or 0) if row else 0,
        'avg_judge_score': round(float(row.avg_score), 1) if row and row.avg_score is not None else None,
        'judge_success': (row.judge_success or 0) if row else 0,
        'judge_failure': (row.judge_failure or 0) if row else 0,
        'with_componente_culpado': (row.with_culpado or 0) if row else 0,
        'adversarial_refuted': (row.adversarial_refuted or 0) if row else 0,
        'success_but_refuted': (row.success_but_refuted or 0) if row else 0,
        'high_frustration': (row.high_frustration or 0) if row else 0,
        'label_distribution': [{'label': r.label, 'count': r.n} for r in labels],
        'top_componente_culpado': [{'componente': r.comp, 'count': r.n} for r in culpados],
    }

    if args.json_mode:
        print(format_json(data))
        return

    if total == 0:
        print(f"Qualidade Step-level ({args.days} dias, {data['scope']}): SEM DADOS.")
        print("(agent_step comecou 2026-05-30. Verifique a flag AGENT_STEP_JUDGE e o canal —")
        print(" Teams pode nao estar instrumentado em agent_step.)")
        return

    print(f"Qualidade Step-level ({args.days} dias, {data['scope']}):\n")
    print(f"  Steps: {total} | com judge: {data['judged']}")
    if data['avg_judge_score'] is not None:
        print(f"  Score medio do judge: {data['avg_judge_score']}/100")
    print(f"  Judge success: {data['judge_success']} | failure: {data['judge_failure']}")
    print(f"  Com componente_culpado: {data['with_componente_culpado']}")
    print(f"  Adversarial refutou: {data['adversarial_refuted']}")
    print(f"  [VIES sem-tool] judge=success MAS adversarial refutou: {data['success_but_refuted']}")
    print(f"  Alta frustracao (score >= 3): {data['high_frustration']}")
    if data['label_distribution']:
        print("\n  Distribuicao de label do judge:")
        for d in data['label_distribution']:
            print(f"    {d['label']}: {d['count']}")
    if data['top_componente_culpado']:
        print("\n  Top componentes culpados:")
        for d in data['top_componente_culpado']:
            print(f"    {d['componente']}: {d['count']}")


def handle_step_coverage(args):
    """Cobertura de sinal por canal (web/teams) + gargalo PlanState.

    Revela lacunas estruturais: canal Teams nao instrumentado em agent_step,
    e o gargalo B1 (PlanState ~0 -> promocao A4 vira no-op).
    """
    from app import db
    from app.utils.timezone import agora_utc_naive
    from datetime import timedelta
    from sqlalchemy import text

    uid = _scope_uid(args)
    since = agora_utc_naive() - timedelta(days=args.days)
    params = {'since': since, 'uid': uid}

    cov_sql = text("""
        SELECT COALESCE(channel, '(null)') AS channel,
               count(*) AS total,
               count(*) FILTER (WHERE outcome_signal::jsonb ? 'judge') AS judged,
               count(*) FILTER (WHERE outcome_signal::jsonb ? 'verify') AS verified,
               count(*) FILTER (WHERE outcome_signal::jsonb ? 'triage') AS triaged,
               max(created_at) AS last_step
        FROM agent_step
        WHERE created_at >= :since AND (:uid IS NULL OR user_id = :uid)
        GROUP BY channel
        ORDER BY count(*) DESC
    """)
    plan_sql = text("""
        SELECT count(*) AS total,
               count(*) FILTER (WHERE data::jsonb ? 'plan') AS with_plan,
               count(*) FILTER (WHERE session_id LIKE 'teams_%') AS teams_sessions
        FROM agent_sessions
        WHERE created_at >= :since AND (:uid IS NULL OR user_id = :uid)
    """)
    try:
        cov = db.session.execute(cov_sql, params).fetchall()
        plan = db.session.execute(plan_sql, params).fetchone()
    except Exception as e:
        db.session.rollback()
        err = {'status': 'query_error', 'error': str(e)}
        print(format_json(err) if args.json_mode else f"Erro ao consultar cobertura: {e}")
        return

    by_channel = [{
        'channel': r.channel,
        'total': r.total,
        'judged': r.judged,
        'verified': r.verified,
        'triaged': r.triaged,
        'last_step': format_datetime(r.last_step),
    } for r in cov]
    total_steps = sum(c['total'] for c in by_channel)
    sess_total = (plan.total or 0) if plan else 0
    with_plan = (plan.with_plan or 0) if plan else 0
    teams_sessions = (plan.teams_sessions or 0) if plan else 0

    data = {
        'status': 'ok' if total_steps > 0 or sess_total > 0 else 'empty',
        'period_days': args.days,
        'scope': _scope_label(args),
        'steps_total': total_steps,
        'by_channel': by_channel,
        'plan_state': {
            'sessions_total': sess_total,
            'with_plan': with_plan,
            'with_plan_pct': round(100.0 * with_plan / sess_total, 1) if sess_total else 0.0,
            'teams_sessions': teams_sessions,
        },
    }

    if args.json_mode:
        print(format_json(data))
        return

    print(f"Cobertura de Sinal ({args.days} dias, {data['scope']}):\n")
    if not by_channel:
        print("  Nenhum step registrado no periodo (agent_step vazio).")
    else:
        rows = []
        for c in by_channel:
            rows.append([
                c['channel'], str(c['total']), str(c['judged']),
                str(c['verified']), str(c['triaged']), c['last_step'],
            ])
        print(format_table(['Canal', 'Steps', 'Judge', 'Verify', 'Triage', 'Ultimo'], rows))

    ps = data['plan_state']
    print(f"\n  PlanState (sessoes com plano super-loop): {ps['with_plan']}/{ps['sessions_total']} ({ps['with_plan_pct']}%)")
    if ps['sessions_total'] > 0 and ps['with_plan_pct'] < 5:
        print("  [GARGALO B1] PlanState ~0 -> promocao A4 (Distill->Deploy) vira no-op.")
    if ps['teams_sessions'] > 0 and not any(c['channel'] == 'teams' for c in by_channel):
        print(f"  [LACUNA] {ps['teams_sessions']} sessoes Teams no periodo, mas 0 steps Teams em agent_step (canal nao instrumentado).")


def handle_rule_adhesion(args):
    """Painel de adesao de regras / loop corretivo pessoal (sintoma Marcus). Custo $0.

    Mede reincidencia por error_signature ANTES (correction_count) vs DEPOIS
    (harmful_count) da promocao a regra dura ('mandatory').
    """
    from app.agente.services.insights_service import get_rule_adhesion_panel

    data = get_rule_adhesion_panel(days=args.days, user_id=_scope_uid(args))

    if args.json_mode:
        print(format_json(data))
        return

    print(f"Adesao de Regras ({args.days} dias, {_scope_label(args)}):\n")
    print(f"  Correcoes (em /memories/corrections/): {data.get('total_corrections', 0)}")
    print(f"  Promovidas a regra dura (mandatory): {data.get('mandatory_count', 0)} ({data.get('mandatory_pct', 0)}%)")

    outcome = data.get('outcome', {})
    if not outcome.get('available', False):
        print("\n  [!] Metricas de reincidencia indisponiveis (colunas Fase 3.1 ausentes no banco).")
    else:
        print(f"\n  Outcome com regra dura: reincidencias DEPOIS={outcome.get('harmful_total', 0)}, "
              f"injecoes uteis={outcome.get('helpful_total', 0)}")

    top = data.get('top_by_signature', [])
    if top:
        print("\n  Top assinaturas de erro (reincidencia antes -> depois da promocao):")
        rows = []
        for t in top:
            rows.append([
                truncate(str(t.get('error_signature', '')), 36),
                str(t.get('ocorrencias', 0)),
                str(t.get('reincidencia_total', 0)),
                str(t.get('reincidencia_pos_promocao', 0)),
                'Sim' if t.get('promovida') else 'Nao',
            ])
        print(format_table(['Assinatura', 'Ocorr', 'Antes', 'Depois', 'Regra dura'], rows))
    else:
        print("\n  (Sem assinaturas de erro registradas no periodo.)")


def handle_routing(args):
    """Metricas de roteamento (ambiguidade, struggling, distribuicao de skills). Custo $0."""
    from app.agente.services.insights_service import get_routing_metrics

    data = get_routing_metrics(days=args.days, user_id=_scope_uid(args))

    if args.json_mode:
        print(format_json(data))
        return

    total = data.get('total_sessions', 0)
    if total == 0:
        print(f"Roteamento ({args.days} dias, {_scope_label(args)}): sem sessoes no periodo.")
        return

    amb = data.get('ambiguidade', {})
    instr = data.get('instrumentacao', {})
    struggling = data.get('struggling', [])

    print(f"Metricas de Roteamento ({args.days} dias, {_scope_label(args)}):\n")
    print(f"  Sessoes: {total} (com summary: {data.get('sessions_com_summary', 0)})")
    print(f"  Health (routing): {data.get('health_score', 0)}")
    print(f"  Taxa AskUser (ambiguidade): {amb.get('taxa_askuser_pct', 0)}% ({amb.get('sessions_askuser', 0)} sessoes)")
    print(f"  Taxa com Skill: {amb.get('taxa_skill_pct', 0)}% ({amb.get('sessions_com_skill', 0)} sessoes)")
    print(f"  Sessoes struggling (>=15 msgs, <=2 tools): {len(struggling)}")
    if instr:
        ativos = [k for k, v in instr.items() if v]
        print(f"  Instrumentacao ativa: {', '.join(ativos) if ativos else '(nenhuma)'}")
    print("\n  (Distribuicao de skills/topicos completa via --json.)")


def handle_recommendations(args):
    """Recomendacoes acionaveis completas (rule-based, ate 5). Custo $0.

    Diferente de 'insights' (que trunca a 3), aqui mostramos a lista completa
    do recommendations_engine sobre as metricas ja computadas pelo insights_service.
    """
    from app.agente.services.insights_service import get_insights_data
    from app.agente.services.recommendations_engine import generate_recommendations

    metrics = get_insights_data(days=args.days, user_id=_scope_uid(args), compare=True)
    recs = generate_recommendations(metrics)

    if args.json_mode:
        print(format_json({'total': len(recs), 'period_days': args.days,
                           'scope': _scope_label(args), 'recommendations': recs}))
        return

    if not recs:
        print(f"Recomendacoes ({args.days} dias, {_scope_label(args)}): nenhuma "
              "(sem dados suficientes ou agente saudavel).")
        return

    print(f"Recomendacoes ({args.days} dias, {_scope_label(args)}) — {len(recs)}:\n")
    for r in recs:
        sev = str(r.get('severity', '?')).upper()
        print(f"  [{sev}] {r.get('title', '')}")
        desc = r.get('description', '')
        if desc:
            print(f"    {desc}")
        action = r.get('action')
        if isinstance(action, dict) and action.get('label'):
            print(f"    -> Acao sugerida: {action['label']}")
        print()


def handle_status(args):
    """Status canonico consolidado do agente (agregador unico, custo $0 de tokens).

    Chama get_insights_data UMA UNICA vez e fatia health/friction/resolution/adoption/
    overview/deltas/recommendations/rule_adhesion — eliminando as 3 chamadas
    redundantes de insights/health/recommendations. Soma memory-metrics (+grafo stats
    via knowledge_graph), embedding-coverage e loop-health/PlanState. Emite o envelope
    canonico em --json. Suporta --all (sistema inteiro).
    """
    from app.agente.services.insights_service import get_insights_data, get_memory_metrics

    uid = _scope_uid(args)
    warnings = []

    # 1) UMA chamada a get_insights_data (compare=True, igual aos handlers que substitui).
    insights = get_insights_data(days=args.days, user_id=uid, compare=True)
    friction = insights.get('friction', {}) or {}
    rule = insights.get('rule_adhesion', {}) or {}
    if not rule:
        warnings.append("rule_adhesion vazio (flag AGENT_CORRECTION_PROMOTION OFF ou sem correcoes)")

    # 2) memory-metrics (inclui knowledge_graph = grafo stats numa so chamada).
    mem = get_memory_metrics(days=args.days, user_id=uid)
    if mem.get('error'):
        warnings.append(f"memory-metrics degradado: {mem['error']}")
    kg = mem.get('knowledge_graph', {}) or {}

    # 3) complementos (queries diretas, --all-safe).
    mstats = _memoria_stats(uid)
    embeddings = _embedding_coverage(uid)
    loop = _loop_health(args.days, uid)
    if loop.get('status') == 'query_error':
        warnings.append(f"loop-health indisponivel: {loop.get('error')}")
    if loop.get('gargalo_b1'):
        warnings.append("[GARGALO B1] PlanState ~0 (<5%) -> promocao A4 (Distill->Deploy) vira no-op")

    health = insights.get('health_score', 0)
    data = {
        'period_days': args.days,
        'scope': _scope_label(args),
        'health': {
            'health_score': health,
            'classification': _classify_health(health),
            'resolution_rate': insights.get('resolution_rate', 0),
            'adoption_rate': insights.get('adoption_rate', 0),
            'friction_score': friction.get('friction_score', 0),
        },
        'overview': insights.get('overview', {}),
        'deltas': insights.get('deltas', {}),
        'memory': {
            'total_memories': mem.get('total_memories', 0),
            'utilization_rate': mem.get('utilization_rate', 0),
            'accessed_in_period': mem.get('accessed_in_period', 0),
            'corrections_count': mem.get('corrections_count', 0),
            'orphan_embeddings': mem.get('orphan_embeddings', 0),
            'cold_tier': mem.get('cold_tier', {}),
            # 'stats' do roadmap (memoria.stats): escalares distintos de memory-metrics.
            'total_caracteres': mstats['total_caracteres'],
            'media_uso': mstats['media_uso'],
            'media_efetividade': mstats['media_efetividade'],
            'conflitos': mstats['conflitos'],
            'por_escopo': mstats['por_escopo'],
        },
        'graph': {
            'total_entities': kg.get('total_entities', 0),
            'total_links': kg.get('total_links', 0),
            'total_relations': kg.get('total_relations', 0),
        },
        'embeddings': embeddings,
        'loop_health': loop,
        'rule_adhesion': {
            'total_corrections': rule.get('total_corrections', 0),
            'mandatory_count': rule.get('mandatory_count', 0),
            'outcome_available': bool((rule.get('outcome', {}) or {}).get('available', False)),
        },
        'recommendations': [
            {'severity': r.get('severity'), 'title': r.get('title')}
            for r in (insights.get('recommendations', []) or [])[:5]
            if isinstance(r, dict)
        ],
    }

    if args.json_mode:
        success_output('status', data, json_mode=True, warnings=warnings)
        return

    h = data['health']
    print(f"STATUS do Agente ({args.days} dias, {data['scope']}):\n")
    print(f"  Saude: {h['health_score']:.1f}/100 ({h['classification']})")
    print(f"    Resolucao {h['resolution_rate']:.1f}% | Adocao {h['adoption_rate']:.1f}% | Friccao {h['friction_score']}")
    ov = data['overview']
    print(f"  Sessoes: {ov.get('total_sessions', 0)} | Mensagens: {ov.get('total_messages', 0)} | Custo ${ov.get('total_cost_usd', 0):.4f}")
    m = data['memory']
    print(f"  Memoria: {m['total_memories']} memorias | utilizacao {m['utilization_rate']:.1f}% | "
          f"{m['corrections_count']} correcoes | orfaos {m['orphan_embeddings']}")
    print(f"    media uso {m['media_uso']}x | efetividade {m['media_efetividade']}x | "
          f"conflitos {m['conflitos']} | {m['total_caracteres']} chars")
    g = data['graph']
    print(f"  Grafo: {g['total_entities']} entidades, {g['total_links']} links, {g['total_relations']} relacoes")
    em = data['embeddings']
    print(f"  Embeddings: memorias {em['memorias']['cobertura']:.1f}% | sessoes {em['sessoes']['cobertura']:.1f}%")
    if loop.get('status') != 'query_error':
        gargalo = " [GARGALO B1]" if loop.get('gargalo_b1') else ""
        print(f"  Loop/PlanState: {loop['with_plan']}/{loop['sessions_total']} sessoes c/ plano ({loop['with_plan_pct']}%){gargalo}")
    ra = data['rule_adhesion']
    extra = "" if ra['outcome_available'] else " (outcome de reincidencia indisponivel)"
    print(f"  Adesao de regras: {ra['total_corrections']} correcoes, {ra['mandatory_count']} regras duras{extra}")
    if data['recommendations']:
        print("\n  Recomendacoes:")
        for r in data['recommendations']:
            print(f"    [{str(r.get('severity', '?')).upper()}] {r.get('title', '')}")
    if warnings:
        print("\n  Avisos:")
        for w in warnings:
            print(f"    - {w}")


HANDLERS = {
    'insights': handle_insights,
    'memory-metrics': handle_memory_metrics,
    'health': handle_health,
    'effectiveness': handle_effectiveness,
    'cold-candidates': handle_cold_candidates,
    'conflicts': handle_conflicts,
    'embedding-coverage': handle_embedding_coverage,
    'friction': handle_friction,
    'briefing': handle_briefing,
    'step-quality': handle_step_quality,
    'step-coverage': handle_step_coverage,
    'rule-adhesion': handle_rule_adhesion,
    'routing': handle_routing,
    'recommendations': handle_recommendations,
    'status': handle_status,
}


def main():
    args, subcommand = parse_args_with_subcommands(
        'Diagnosticos do agente', SUBCOMMANDS
    )

    app, ctx = get_app_context()
    with ctx:
        resolve_user(args.user_id)
        handler = HANDLERS.get(subcommand)
        if handler:
            handler(args)
        else:
            error_exit(f"Subcomando desconhecido: {subcommand}")


if __name__ == '__main__':
    main()
