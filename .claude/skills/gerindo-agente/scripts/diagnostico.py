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
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

from common import (
    error_exit, format_datetime, format_json, format_table,
    get_app_context, parse_args_with_subcommands, resolve_user, truncate,
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
