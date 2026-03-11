#!/usr/bin/env python3
"""
Dominio 6: Manutencao — consolidacao, cold, reindexacao, sumarizacao e cleanup.

Subcomandos:
  consolidate       Consolidar memorias redundantes (via Sonnet)
  cold-move         Mover memorias ineficazes para tier frio
  summarize         Sumarizar uma sessao (via Sonnet)
  reindex-memories  Reindexar embeddings de memorias
  reindex-sessions  Reindexar embeddings de sessoes
  cleanup-orphans   Limpar entidades orfas do Knowledge Graph
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

from common import (
    error_exit, format_json,
    get_app_context, parse_args_with_subcommands, resolve_user,
)


SUBCOMMANDS = {
    'consolidate': {
        'help': 'Consolidar memorias redundantes (via Sonnet, ~$0.006)',
        'args': [],
    },
    'cold-move': {
        'help': 'Mover memorias ineficazes para tier frio',
        'args': [],
    },
    'summarize': {
        'help': 'Sumarizar uma sessao (via Sonnet, ~$0.003)',
        'args': [
            {'name': '--session-id', 'required': True, 'help': 'ID da sessao'},
        ],
    },
    'reindex-memories': {
        'help': 'Reindexar embeddings de memorias',
        'args': [
            {'name': '--reindex', 'action': 'store_true',
             'help': 'Forcar reindexacao (inclui ja indexados)'},
        ],
    },
    'reindex-sessions': {
        'help': 'Reindexar embeddings de sessoes',
        'args': [
            {'name': '--reindex', 'action': 'store_true',
             'help': 'Forcar reindexacao (inclui ja indexados)'},
        ],
    },
    'cleanup-orphans': {
        'help': 'Limpar entidades orfas do Knowledge Graph',
        'args': [],
    },
}


def handle_consolidate(args):
    """Consolidar memorias redundantes."""
    from app.agente.services.memory_consolidator import maybe_consolidate

    print("Verificando se consolidacao e necessaria...")
    result = maybe_consolidate(args.user_id)

    if args.json_mode:
        print(format_json({
            'sucesso': True,
            'resultado': result or 'nenhuma consolidacao necessaria',
        }))
    else:
        if result:
            print(f"Consolidacao realizada: {result}")
        else:
            print("Nenhuma consolidacao necessaria (abaixo dos thresholds).")


def handle_cold_move(args):
    """Mover memorias ineficazes para tier frio."""
    from app.agente.services.memory_consolidator import maybe_move_to_cold

    count = maybe_move_to_cold(args.user_id)

    if args.json_mode:
        print(format_json({'sucesso': True, 'movidas_para_cold': count}))
    else:
        if count > 0:
            print(f"{count} memoria(s) movida(s) para tier frio.")
        else:
            print("Nenhuma memoria para mover para tier frio.")


def handle_summarize(args):
    """Sumarizar uma sessao."""
    from app.agente.models import AgentSession
    from app.agente.services.session_summarizer import summarize_session

    session = AgentSession.query.filter_by(
        session_id=args.session_id, user_id=args.user_id
    ).first()
    if not session:
        error_exit(f"Sessao nao encontrada: {args.session_id}")

    if session.message_count and session.message_count < 3:
        error_exit("Sessao tem menos de 3 mensagens. Nao ha conteudo suficiente.")

    app, _ = get_app_context()

    print(f"Sumarizando sessao {args.session_id}...")
    try:
        result = summarize_session(app, args.session_id, args.user_id)
        if result:
            # Recarregar sessao para pegar summary atualizado
            from app import db
            db.session.refresh(session)
            summary = session.get_summary()

            if args.json_mode:
                print(format_json({'sucesso': True, 'summary': summary}))
            else:
                print("Sumarizacao concluida com sucesso.")
                if summary:
                    print(f"\n  Resumo: {summary.get('resumo_geral', '-')}")
                    topicos = summary.get('topicos_abordados', [])
                    if topicos:
                        print(f"  Topicos: {', '.join(topicos)}")
        else:
            if args.json_mode:
                print(format_json({'sucesso': False, 'motivo': 'sumarizacao retornou False'}))
            else:
                print("Sumarizacao nao produziu resultado (sessao pode ter poucos dados).")
    except Exception as e:
        error_exit(f"Erro na sumarizacao: {e}")


def handle_reindex_memories(args):
    """Reindexar embeddings de memorias."""
    try:
        from app.embeddings.indexers.memory_indexer import collect_memories, index_memories
    except ImportError:
        error_exit("Modulo de embeddings nao disponivel. Verifique se voyageai esta instalado.")

    print(f"Reindexando memorias do usuario {args.user_id}...")
    try:
        memories, stats = collect_memories(user_id=args.user_id)
        print(f"Coletadas {len(memories)} memorias. Indexando...")
        result = index_memories(memories, reindex=args.reindex)
        if args.json_mode:
            print(format_json({'sucesso': True, 'coletadas': len(memories), 'resultado': result}))
        else:
            print(f"Reindexacao concluida: {result}")
    except Exception as e:
        error_exit(f"Erro na reindexacao: {e}")


def handle_reindex_sessions(args):
    """Reindexar embeddings de sessoes."""
    try:
        from app.embeddings.indexers.session_turn_indexer import collect_turns, index_turns
    except ImportError:
        error_exit("Modulo de embeddings nao disponivel. Verifique se voyageai esta instalado.")

    print(f"Reindexando sessoes do usuario {args.user_id}...")
    try:
        turns, stats = collect_turns(user_id=args.user_id)
        print(f"Coletados {len(turns)} turns. Indexando...")
        result = index_turns(turns, reindex=args.reindex)
        if args.json_mode:
            print(format_json({'sucesso': True, 'coletados': len(turns), 'resultado': result}))
        else:
            print(f"Reindexacao concluida: {result}")
    except Exception as e:
        error_exit(f"Erro na reindexacao: {e}")


def handle_cleanup_orphans(args):
    """Limpar entidades orfas do Knowledge Graph."""
    from app.agente.services.knowledge_graph_service import cleanup_orphan_entities

    count = cleanup_orphan_entities(user_id=args.user_id)

    if args.json_mode:
        print(format_json({'sucesso': True, 'orfaos_removidos': count}))
    else:
        if count > 0:
            print(f"{count} entidade(s) orfa(s) removida(s) do Knowledge Graph.")
        else:
            print("Nenhuma entidade orfa encontrada.")


HANDLERS = {
    'consolidate': handle_consolidate,
    'cold-move': handle_cold_move,
    'summarize': handle_summarize,
    'reindex-memories': handle_reindex_memories,
    'reindex-sessions': handle_reindex_sessions,
    'cleanup-orphans': handle_cleanup_orphans,
}


def main():
    args, subcommand = parse_args_with_subcommands(
        'Manutencao do sistema de agente', SUBCOMMANDS
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
