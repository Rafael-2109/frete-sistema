#!/usr/bin/env python3
"""
Dominio 2: Sessoes — listagem, busca, visualizacao e sumarizacao.

Gerencia sessoes do agente (agent_sessions).

Subcomandos:
  list      Listar sessoes recentes
  search    Busca textual em sessoes (ILIKE)
  semantic  Busca semantica via embeddings
  view      Visualizar mensagens de uma sessao
  summary   Ver resumo estruturado de uma sessao
  users     Listar usuarios com sessoes (admin)
  delete    Deletar sessao (requer --confirm)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

from common import (
    error_exit, format_datetime, format_json, format_table,
    get_app_context, parse_args_with_subcommands, resolve_user, truncate,
)


SUBCOMMANDS = {
    'list': {
        'help': 'Listar sessoes recentes',
        'args': [
            {'name': '--channel', 'default': None, 'choices': ['teams', 'web'],
             'help': 'Filtrar por canal (teams/web)'},
        ],
    },
    'search': {
        'help': 'Busca textual em sessoes (ILIKE)',
        'args': [
            {'name': '--query', 'required': True, 'help': 'Termo de busca'},
            {'name': '--channel', 'default': None, 'choices': ['teams', 'web'],
             'help': 'Filtrar por canal'},
        ],
    },
    'semantic': {
        'help': 'Busca semantica via embeddings (fallback ILIKE)',
        'args': [
            {'name': '--query', 'required': True, 'help': 'Consulta semantica'},
        ],
    },
    'view': {
        'help': 'Visualizar mensagens de uma sessao',
        'args': [
            {'name': '--session-id', 'required': True, 'help': 'ID da sessao'},
        ],
    },
    'summary': {
        'help': 'Ver resumo estruturado de uma sessao',
        'args': [
            {'name': '--session-id', 'required': True, 'help': 'ID da sessao'},
        ],
    },
    'users': {
        'help': 'Listar usuarios com sessoes (admin)',
        'args': [],
    },
    'delete': {
        'help': 'Deletar sessao (requer --confirm)',
        'args': [
            {'name': '--session-id', 'required': True, 'help': 'ID da sessao'},
            {'name': '--confirm', 'action': 'store_true', 'help': 'Confirmar exclusao'},
        ],
    },
}


def handle_list(args):
    """Listar sessoes recentes."""
    from app.agente.models import AgentSession

    query = AgentSession.query.filter_by(user_id=args.user_id)

    if args.channel == 'teams':
        query = query.filter(AgentSession.session_id.like('teams_%'))
    elif args.channel == 'web':
        query = query.filter(~AgentSession.session_id.like('teams_%'))

    sessions = query.order_by(AgentSession.updated_at.desc()).limit(args.limit).all()

    if args.json_mode:
        data = [s.to_dict() for s in sessions]
        print(format_json({'total': len(data), 'sessoes': data}))
    else:
        if not sessions:
            print("Nenhuma sessao encontrada.")
            return

        print(f"Sessoes recentes ({len(sessions)}):\n")
        rows = []
        for s in sessions:
            canal = 'Teams' if s.session_id.startswith('teams_') else 'Web'
            has_summary = 'Sim' if s.summary else 'Nao'
            rows.append([
                s.session_id[:16] + '...',
                truncate(s.title or '(sem titulo)', 40),
                str(s.message_count or 0),
                f"${float(s.total_cost_usd or 0):.4f}",
                canal,
                s.model or '-',
                has_summary,
                format_datetime(s.updated_at),
            ])
        print(format_table(
            ['Session ID', 'Titulo', 'Msgs', 'Custo', 'Canal', 'Modelo', 'Summary', 'Atualizado'],
            rows
        ))


def handle_search(args):
    """Busca textual em sessoes."""
    from app import db
    from sqlalchemy import text

    user_id = args.user_id
    query_text = f"%{args.query}%"

    sql = """
        SELECT session_id, title, message_count, total_cost_usd, updated_at
        FROM agent_sessions
        WHERE user_id = :user_id
        AND CAST(data AS TEXT) ILIKE :query
    """
    params = {'user_id': user_id, 'query': query_text}

    if args.channel == 'teams':
        sql += " AND session_id LIKE :channel_pattern"
        params['channel_pattern'] = 'teams_%'
    elif args.channel == 'web':
        sql += " AND session_id NOT LIKE :channel_pattern"
        params['channel_pattern'] = 'teams_%'

    sql += " ORDER BY updated_at DESC LIMIT :lim"
    params['lim'] = args.limit

    results = db.session.execute(text(sql), params).fetchall()

    if args.json_mode:
        data = [{
            'session_id': r[0],
            'title': r[1],
            'message_count': r[2],
            'cost_usd': float(r[3] or 0),
            'updated_at': format_datetime(r[4]),
        } for r in results]
        print(format_json({'query': args.query, 'resultados': data}))
    else:
        if not results:
            print(f"Nenhuma sessao encontrada para: '{args.query}'")
            return

        print(f"Busca por '{args.query}' ({len(results)} resultados):\n")
        rows = []
        for r in results:
            rows.append([
                r[0][:16] + '...',
                truncate(r[1] or '(sem titulo)', 40),
                str(r[2] or 0),
                format_datetime(r[4]),
            ])
        print(format_table(['Session ID', 'Titulo', 'Msgs', 'Atualizado'], rows))


def handle_semantic(args):
    """Busca semantica via embeddings."""
    try:
        from app.embeddings.session_search import buscar_sessoes_semantica
        results = buscar_sessoes_semantica(
            user_id=args.user_id,
            query=args.query,
            limit=args.limit,
        )
    except ImportError:
        # Fallback para busca textual
        print("Embeddings nao disponiveis. Usando busca textual...\n")
        args.channel = None
        handle_search(args)
        return
    except Exception as e:
        # Fallback para busca textual
        print(f"Busca semantica falhou ({e}). Usando busca textual...\n")
        args.channel = None
        handle_search(args)
        return

    if args.json_mode:
        print(format_json({'query': args.query, 'metodo': 'semantico', 'resultados': results}))
    else:
        if not results:
            print(f"Nenhum resultado semantico para: '{args.query}'")
            return

        print(f"Busca semantica por '{args.query}' ({len(results)} resultados):\n")
        for r in results:
            score = r.get('similarity', r.get('score', 0))
            print(f"  [{score:.3f}] {r.get('session_id', '?')[:16]}...")
            print(f"    {truncate(r.get('title', r.get('content', '')), 80)}")
            print()


def handle_view(args):
    """Visualizar mensagens de uma sessao."""
    from app.agente.models import AgentSession

    session = AgentSession.query.filter_by(
        session_id=args.session_id, user_id=args.user_id
    ).first()
    if not session:
        error_exit(f"Sessao nao encontrada: {args.session_id}")

    messages = session.get_messages()

    if args.json_mode:
        print(format_json({
            'session_id': session.session_id,
            'title': session.title,
            'message_count': len(messages),
            'messages': messages,
        }))
    else:
        print(f"Sessao: {session.session_id}")
        print(f"Titulo: {session.title or '(sem titulo)'}")
        print(f"Modelo: {session.model or '(nao registrado)'}")
        print(f"Mensagens: {len(messages)}\n")
        print("=" * 60)

        for msg in messages:
            role = msg.get('role', '?').upper()
            content = msg.get('content', '')
            timestamp = msg.get('timestamp', '')
            tools = msg.get('tools_used', [])

            print(f"\n[{role}] {timestamp}")
            if tools:
                print(f"  Tools: {', '.join(tools)}")
            print(f"  {truncate(content, 500)}")

        print("\n" + "=" * 60)


def handle_summary(args):
    """Ver resumo estruturado de uma sessao."""
    from app.agente.models import AgentSession

    session = AgentSession.query.filter_by(
        session_id=args.session_id, user_id=args.user_id
    ).first()
    if not session:
        error_exit(f"Sessao nao encontrada: {args.session_id}")

    summary = session.get_summary()

    if args.json_mode:
        print(format_json({
            'session_id': session.session_id,
            'has_summary': bool(summary),
            'summary': summary,
            'summary_updated_at': format_datetime(session.summary_updated_at),
        }))
    else:
        if not summary:
            print(f"Sessao {args.session_id} nao tem resumo.")
            return

        print(f"Resumo da Sessao: {session.session_id}\n")
        print(f"  Resumo: {summary.get('resumo_geral', '-')}")

        acoes = summary.get('acoes_usuario', [])
        if acoes:
            print(f"\n  Acoes do usuario:")
            for a in acoes:
                print(f"    - {a}")

        perfil = summary.get('perfil_signals', {})
        if perfil and isinstance(perfil, dict):
            dominio = perfil.get('dominio_provavel', '')
            tipos = ', '.join(perfil.get('tipo_atividade', []))
            clientes = ', '.join(perfil.get('clientes_envolvidos', []))
            volume = perfil.get('volume', '')
            if dominio or tipos:
                print(f"\n  Perfil da sessao:")
                if dominio:
                    print(f"    Dominio: {dominio}")
                if tipos:
                    print(f"    Atividades: {tipos}")
                if clientes:
                    print(f"    Clientes: {clientes}")
                if volume:
                    print(f"    Volume: {volume}")

        pedidos = summary.get('pedidos_mencionados', [])
        if pedidos:
            print(f"\n  Pedidos mencionados:")
            for p in pedidos:
                print(f"    - {p.get('cliente', '?')}: {p.get('pedido', '?')} ({p.get('status', '')})")

        decisoes = summary.get('decisoes_tomadas', [])
        if decisoes:
            print(f"\n  Decisoes:")
            for d in decisoes:
                print(f"    - {d}")

        tarefas = summary.get('tarefas_pendentes', [])
        if tarefas:
            print(f"\n  Tarefas pendentes:")
            for t in tarefas:
                print(f"    - {t}")

        alertas = summary.get('alertas', [])
        if alertas:
            print(f"\n  Alertas:")
            for a in alertas:
                print(f"    - {a}")

        tools = summary.get('ferramentas_usadas', [])
        if tools:
            print(f"\n  Ferramentas: {', '.join(tools)}")

        topicos = summary.get('topicos_abordados', [])
        if topicos:
            print(f"  Topicos: {', '.join(topicos)}")

        print(f"\n  Atualizado: {format_datetime(session.summary_updated_at)}")


def handle_users(args):
    """Listar usuarios com sessoes (admin)."""
    from app import db
    from app.agente.models import AgentSession
    from sqlalchemy import func

    results = db.session.query(
        AgentSession.user_id,
        func.count(AgentSession.id).label('total_sessions'),
        func.sum(AgentSession.message_count).label('total_messages'),
        func.sum(AgentSession.total_cost_usd).label('total_cost'),
        func.max(AgentSession.updated_at).label('last_activity'),
    ).group_by(AgentSession.user_id).order_by(
        func.count(AgentSession.id).desc()
    ).limit(args.limit).all()

    # Buscar nomes
    user_ids = [r[0] for r in results if r[0]]
    user_names = {}
    if user_ids:
        from app.auth.models import Usuario
        users = Usuario.query.filter(Usuario.id.in_(user_ids)).all()
        user_names = {u.id: u.nome for u in users}

    if args.json_mode:
        data = [{
            'user_id': r[0],
            'nome': user_names.get(r[0], f'Usuario #{r[0]}'),
            'total_sessions': r[1],
            'total_messages': int(r[2] or 0),
            'total_cost_usd': float(r[3] or 0),
            'last_activity': format_datetime(r[4]),
        } for r in results]
        print(format_json({'usuarios': data}))
    else:
        if not results:
            print("Nenhum usuario com sessoes.")
            return

        print(f"Usuarios com sessoes ({len(results)}):\n")
        rows = []
        for r in results:
            rows.append([
                str(r[0]),
                user_names.get(r[0], f'Usuario #{r[0]}'),
                str(r[1]),
                str(int(r[2] or 0)),
                f"${float(r[3] or 0):.4f}",
                format_datetime(r[4]),
            ])
        print(format_table(
            ['ID', 'Nome', 'Sessoes', 'Msgs', 'Custo', 'Ultima Atividade'],
            rows
        ))


def handle_delete(args):
    """Deletar sessao."""
    from app import db
    from app.agente.models import AgentSession

    if not args.confirm:
        error_exit("Use --confirm para confirmar exclusao da sessao.")

    session = AgentSession.query.filter_by(
        session_id=args.session_id, user_id=args.user_id
    ).first()
    if not session:
        error_exit(f"Sessao nao encontrada: {args.session_id}")

    # Usar db.session.delete para disparar cascade
    db.session.delete(session)
    db.session.commit()

    if args.json_mode:
        print(format_json({'sucesso': True, 'session_id': args.session_id}))
    else:
        print(f"Sessao deletada: {args.session_id}")


HANDLERS = {
    'list': handle_list,
    'search': handle_search,
    'semantic': handle_semantic,
    'view': handle_view,
    'summary': handle_summary,
    'users': handle_users,
    'delete': handle_delete,
}


def main():
    args, subcommand = parse_args_with_subcommands(
        'Gerenciamento de sessoes do agente', SUBCOMMANDS
    )

    app, ctx = get_app_context()
    with ctx:
        # users nao requer user_id valido (admin)
        if subcommand != 'users':
            resolve_user(args.user_id)

        handler = HANDLERS.get(subcommand)
        if handler:
            handler(args)
        else:
            error_exit(f"Subcomando desconhecido: {subcommand}")


if __name__ == '__main__':
    main()
