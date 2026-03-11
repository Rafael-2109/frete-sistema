#!/usr/bin/env python3
"""
Dominio 4: Knowledge Graph — query, entidades, links e relacoes.

Gerencia o grafo de conhecimento do agente (agent_memory_entities,
agent_memory_entity_links, agent_memory_entity_relations).

Subcomandos:
  query      Query multi-hop no grafo (prompt em linguagem natural)
  entities   Listar entidades do grafo
  links      Ver links de uma entidade com memorias
  relations  Ver relacoes entre entidades
  stats      Estatisticas do grafo
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

from common import (
    error_exit, format_datetime, format_json, format_table,
    get_app_context, parse_args_with_subcommands, resolve_user, truncate,
)


SUBCOMMANDS = {
    'query': {
        'help': 'Query multi-hop no grafo (prompt em linguagem natural)',
        'args': [
            {'name': '--prompt', 'required': True, 'help': 'Consulta em linguagem natural'},
        ],
    },
    'entities': {
        'help': 'Listar entidades do grafo',
        'args': [
            {'name': '--type', 'default': None, 'dest': 'entity_type',
             'help': 'Filtrar por tipo (uf, pedido, cnpj, transportadora, produto, cliente, fornecedor, regra)'},
        ],
    },
    'links': {
        'help': 'Ver links de uma entidade com memorias',
        'args': [
            {'name': '--entity-id', 'type': int, 'required': True, 'help': 'ID da entidade'},
        ],
    },
    'relations': {
        'help': 'Ver relacoes entre entidades',
        'args': [
            {'name': '--entity-name', 'default': None, 'help': 'Filtrar por nome de entidade'},
        ],
    },
    'stats': {
        'help': 'Estatisticas do grafo',
        'args': [],
    },
}


def handle_query(args):
    """Query multi-hop no grafo."""
    from app.agente.services.knowledge_graph_service import query_graph_memories
    from app.agente.models import AgentMemory

    results = query_graph_memories(
        user_id=args.user_id,
        prompt=args.prompt,
        limit=args.limit,
    )

    if not results:
        if args.json_mode:
            print(format_json({'prompt': args.prompt, 'total': 0, 'resultados': []}))
        else:
            print(f"Nenhum resultado no grafo para: '{args.prompt}'")
        return

    # Enriquecer resultados com path/content do banco
    memory_ids = [r.get('memory_id') for r in results if r.get('memory_id')]
    memories_by_id = {}
    if memory_ids:
        mems = AgentMemory.query.filter(AgentMemory.id.in_(memory_ids)).all()
        memories_by_id = {m.id: m for m in mems}

    enriched = []
    for r in results:
        mem = memories_by_id.get(r.get('memory_id'))
        enriched.append({
            'memory_id': r.get('memory_id'),
            'similarity': r.get('similarity', 0),
            'source': r.get('source', '?'),
            'path': mem.path if mem else '?',
            'content': mem.content if mem else '',
        })

    if args.json_mode:
        print(format_json({
            'prompt': args.prompt,
            'total': len(enriched),
            'resultados': enriched,
        }))
    else:
        print(f"Query no Knowledge Graph: '{args.prompt}' ({len(enriched)} resultados):\n")
        for r in enriched:
            print(f"  [{r['similarity']:.3f}] {r['path']} (via {r['source']})")
            print(f"    {truncate(r['content'], 100)}")
            print()


def handle_entities(args):
    """Listar entidades do grafo."""
    from app.agente.models import AgentMemoryEntity

    query = AgentMemoryEntity.query.filter(
        AgentMemoryEntity.user_id == args.user_id
    )

    if args.entity_type:
        query = query.filter(AgentMemoryEntity.entity_type == args.entity_type)

    entities = query.order_by(
        AgentMemoryEntity.mention_count.desc()
    ).limit(args.limit).all()

    if args.json_mode:
        data = [{
            'id': e.id,
            'type': e.entity_type,
            'name': e.entity_name,
            'key': e.entity_key,
            'mention_count': e.mention_count,
            'first_seen': format_datetime(e.first_seen_at),
            'last_seen': format_datetime(e.last_seen_at),
        } for e in entities]
        print(format_json({'total': len(data), 'entidades': data}))
    else:
        if not entities:
            print("Nenhuma entidade encontrada no grafo.")
            return

        print(f"Entidades do Knowledge Graph ({len(entities)}):\n")
        rows = []
        for e in entities:
            rows.append([
                str(e.id),
                e.entity_type,
                truncate(e.entity_name, 30),
                e.entity_key or '-',
                str(e.mention_count),
                format_datetime(e.last_seen_at),
            ])
        print(format_table(
            ['ID', 'Tipo', 'Nome', 'Key', 'Mencoes', 'Ultimo'],
            rows
        ))


def handle_links(args):
    """Ver links de uma entidade com memorias."""
    from app.agente.models import AgentMemoryEntity, AgentMemoryEntityLink, AgentMemory

    entity = AgentMemoryEntity.query.get(args.entity_id)
    if not entity:
        error_exit(f"Entidade nao encontrada: ID={args.entity_id}")

    # Verificar que pertence ao usuario
    if entity.user_id != args.user_id:
        error_exit(f"Entidade ID={args.entity_id} nao pertence ao usuario {args.user_id}.")

    links = AgentMemoryEntityLink.query.filter_by(
        entity_id=entity.id
    ).all()

    # Buscar memorias associadas
    memory_ids = [l.memory_id for l in links]
    memories = {}
    if memory_ids:
        mems = AgentMemory.query.filter(AgentMemory.id.in_(memory_ids)).all()
        memories = {m.id: m for m in mems}

    if args.json_mode:
        data = []
        for l in links:
            mem = memories.get(l.memory_id)
            data.append({
                'link_id': l.id,
                'relation_type': l.relation_type,
                'memory_id': l.memory_id,
                'memory_path': mem.path if mem else '(deletada)',
                'memory_preview': truncate(mem.content, 200) if mem and mem.content else '',
                'created_at': format_datetime(l.created_at),
            })
        print(format_json({
            'entity': {
                'id': entity.id,
                'type': entity.entity_type,
                'name': entity.entity_name,
                'key': entity.entity_key,
            },
            'total_links': len(data),
            'links': data,
        }))
    else:
        print(f"Entidade: [{entity.entity_type}] {entity.entity_name}")
        if entity.entity_key:
            print(f"Key: {entity.entity_key}")
        print(f"Mencoes: {entity.mention_count}\n")

        if not links:
            print("Nenhum link com memorias.")
            return

        print(f"Links ({len(links)}):\n")
        for l in links:
            mem = memories.get(l.memory_id)
            rel = l.relation_type
            path = mem.path if mem else '(deletada)'
            preview = truncate(mem.content, 80) if mem and mem.content else ''
            print(f"  [{rel}] {path}")
            if preview:
                print(f"    {preview}")
            print()


def handle_relations(args):
    """Ver relacoes entre entidades."""
    from app.agente.models import AgentMemoryEntity, AgentMemoryEntityRelation

    query = AgentMemoryEntityRelation.query

    if args.entity_name:
        # Buscar entidade pelo nome
        name_upper = args.entity_name.upper()
        entities = AgentMemoryEntity.query.filter(
            AgentMemoryEntity.user_id == args.user_id,
            AgentMemoryEntity.entity_name.ilike(f'%{name_upper}%'),
        ).all()

        if not entities:
            error_exit(f"Entidade nao encontrada: {args.entity_name}")

        entity_ids = [e.id for e in entities]
        from sqlalchemy import or_
        query = query.filter(
            or_(
                AgentMemoryEntityRelation.source_entity_id.in_(entity_ids),
                AgentMemoryEntityRelation.target_entity_id.in_(entity_ids),
            )
        )
    else:
        # Filtrar por user_id via join
        entity_ids_subquery = AgentMemoryEntity.query.filter(
            AgentMemoryEntity.user_id == args.user_id
        ).with_entities(AgentMemoryEntity.id).subquery()

        query = query.filter(
            AgentMemoryEntityRelation.source_entity_id.in_(
                entity_ids_subquery.select()
            )
        )

    relations = query.order_by(
        AgentMemoryEntityRelation.weight.desc()
    ).limit(args.limit).all()

    # Buscar nomes das entidades
    all_entity_ids = set()
    for r in relations:
        all_entity_ids.add(r.source_entity_id)
        all_entity_ids.add(r.target_entity_id)

    entities_map = {}
    if all_entity_ids:
        ents = AgentMemoryEntity.query.filter(
            AgentMemoryEntity.id.in_(list(all_entity_ids))
        ).all()
        entities_map = {e.id: e for e in ents}

    if args.json_mode:
        data = [{
            'source': {
                'id': r.source_entity_id,
                'name': entities_map.get(r.source_entity_id, None) and entities_map[r.source_entity_id].entity_name,
                'type': entities_map.get(r.source_entity_id, None) and entities_map[r.source_entity_id].entity_type,
            },
            'relation': r.relation_type,
            'target': {
                'id': r.target_entity_id,
                'name': entities_map.get(r.target_entity_id, None) and entities_map[r.target_entity_id].entity_name,
                'type': entities_map.get(r.target_entity_id, None) and entities_map[r.target_entity_id].entity_type,
            },
            'weight': round(r.weight, 3),
        } for r in relations]
        print(format_json({'total': len(data), 'relacoes': data}))
    else:
        if not relations:
            print("Nenhuma relacao encontrada.")
            return

        print(f"Relacoes ({len(relations)}):\n")
        rows = []
        for r in relations:
            src = entities_map.get(r.source_entity_id)
            tgt = entities_map.get(r.target_entity_id)
            src_name = f"{src.entity_name}" if src else f"ID={r.source_entity_id}"
            tgt_name = f"{tgt.entity_name}" if tgt else f"ID={r.target_entity_id}"
            rows.append([
                truncate(src_name, 25),
                r.relation_type,
                truncate(tgt_name, 25),
                str(round(r.weight, 3)),
            ])
        print(format_table(['Origem', 'Relacao', 'Destino', 'Peso'], rows))


def handle_stats(args):
    """Estatisticas do grafo."""
    from app.agente.services.knowledge_graph_service import get_graph_stats

    stats = get_graph_stats(user_id=args.user_id)

    if args.json_mode:
        print(format_json(stats))
    else:
        print(f"Knowledge Graph Stats (user_id={args.user_id}):\n")
        print(f"  Entidades: {stats.get('total_entities', 0)}")
        print(f"  Links: {stats.get('total_links', 0)}")
        print(f"  Relacoes: {stats.get('total_relations', 0)}")

        by_type = stats.get('entities_by_type', {})
        if by_type:
            print(f"\n  Por tipo:")
            for entity_type, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
                print(f"    {entity_type}: {count}")

        top = stats.get('top_entities', [])
        if top:
            print(f"\n  Top entidades:")
            for e in top[:10]:
                print(f"    {e.get('name', '?')} ({e.get('type', '?')}) — {e.get('mention_count', 0)} mencoes")


HANDLERS = {
    'query': handle_query,
    'entities': handle_entities,
    'links': handle_links,
    'relations': handle_relations,
    'stats': handle_stats,
}


def main():
    args, subcommand = parse_args_with_subcommands(
        'Knowledge Graph do agente', SUBCOMMANDS
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
