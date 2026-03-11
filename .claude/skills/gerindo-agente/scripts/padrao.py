#!/usr/bin/env python3
"""
Dominio 3: Padroes & Aprendizado — patterns, pitfalls, analise e extracao.

Gerencia padroes aprendidos pelo agente via pattern_analyzer.

Subcomandos:
  patterns  Ver padroes aprendidos (patterns.xml)
  pitfalls  Ver pitfalls registrados (pitfalls.json)
  analyze   Executar analise de padroes (Sonnet)
  extract   Extrair conhecimento de uma sessao
  empresa   Ver memorias compartilhadas (escopo empresa)
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')))

from common import (
    error_exit, format_datetime, format_json,
    get_app_context, parse_args_with_subcommands, resolve_user, truncate,
)


SUBCOMMANDS = {
    'patterns': {
        'help': 'Ver padroes aprendidos (patterns.xml)',
        'args': [],
    },
    'pitfalls': {
        'help': 'Ver pitfalls registrados (pitfalls.json)',
        'args': [],
    },
    'analyze': {
        'help': 'Executar analise de padroes (chama Sonnet)',
        'args': [],
    },
    'extract': {
        'help': 'Extrair conhecimento de uma sessao',
        'args': [
            {'name': '--session-id', 'required': True, 'help': 'ID da sessao'},
        ],
    },
    'empresa': {
        'help': 'Ver memorias compartilhadas (escopo empresa)',
        'args': [],
    },
}


def handle_patterns(args):
    """Ver padroes aprendidos."""
    from app.agente.models import AgentMemory

    path = '/memories/learned/patterns.xml'
    mem = AgentMemory.get_by_path(args.user_id, path)

    if not mem:
        if args.json_mode:
            print(format_json({'exists': False, 'path': path}))
        else:
            print("Nenhum padrao aprendido encontrado.")
            print("Execute 'analyze' para gerar padroes a partir de sessoes anteriores.")
        return

    if args.json_mode:
        print(format_json({
            'exists': True,
            'path': path,
            'content': mem.content,
            'usage_count': mem.usage_count,
            'effective_count': mem.effective_count,
            'updated_at': format_datetime(mem.updated_at),
        }))
    else:
        print(f"Padroes Aprendidos (atualizado: {format_datetime(mem.updated_at)})")
        print(f"Uso: {mem.usage_count}x injetado | {mem.effective_count}x efetivo\n")
        print(mem.content)


def handle_pitfalls(args):
    """Ver pitfalls registrados."""
    import json
    from app.agente.models import AgentMemory

    path = '/memories/system/pitfalls.json'
    mem = AgentMemory.get_by_path(args.user_id, path)

    if not mem or not mem.content:
        if args.json_mode:
            print(format_json({'exists': False, 'pitfalls': []}))
        else:
            print("Nenhum pitfall registrado.")
        return

    try:
        pitfalls = json.loads(mem.content)
    except json.JSONDecodeError:
        error_exit("pitfalls.json corrompido.")

    if args.json_mode:
        print(format_json({'total': len(pitfalls), 'pitfalls': pitfalls}))
    else:
        print(f"Pitfalls do Sistema ({len(pitfalls)}):\n")
        # Agrupar por area
        by_area = {}
        for p in pitfalls:
            area = p.get('area', 'geral')
            by_area.setdefault(area, []).append(p)

        for area, items in sorted(by_area.items()):
            print(f"  [{area.upper()}]")
            for item in items:
                hits = item.get('hit_count', 1)
                desc = item.get('description', '?')
                print(f"    ({hits}x) {desc}")
            print()


def handle_analyze(args):
    """Executar analise de padroes."""
    from app.agente.services.pattern_analyzer import analyze_and_save

    app, _ = get_app_context()

    print("Executando analise de padroes via Sonnet...")
    try:
        result = analyze_and_save(app, args.user_id)
        if result:
            if args.json_mode:
                print(format_json({'sucesso': True, 'resultado': 'padroes atualizados'}))
            else:
                print("Padroes atualizados com sucesso.")
                print("Use 'patterns' para visualizar.")
        else:
            if args.json_mode:
                print(format_json({'sucesso': False, 'motivo': 'sem dados suficientes'}))
            else:
                print("Sem dados suficientes para analise (precisa de mais sessoes).")
    except Exception as e:
        error_exit(f"Erro na analise: {e}")


def handle_extract(args):
    """Extrair conhecimento de uma sessao."""
    from app.agente.models import AgentSession
    from app.agente.services.pattern_analyzer import extrair_conhecimento_sessao

    session = AgentSession.query.filter_by(
        session_id=args.session_id, user_id=args.user_id
    ).first()
    if not session:
        error_exit(f"Sessao nao encontrada: {args.session_id}")

    messages = session.get_messages()
    if len(messages) < 3:
        error_exit("Sessao tem menos de 3 mensagens. Nao ha conteudo suficiente.")

    app, _ = get_app_context()

    print("Extraindo conhecimento da sessao via Sonnet...")
    try:
        result = extrair_conhecimento_sessao(app, args.user_id, messages)
        if args.json_mode:
            print(format_json({'sucesso': True, 'resultado': result}))
        else:
            if result:
                print(f"Conhecimento extraido com sucesso: {result}")
            else:
                print("Nenhum conhecimento relevante extraido desta sessao.")
    except Exception as e:
        error_exit(f"Erro na extracao: {e}")


def handle_empresa(args):
    """Ver memorias compartilhadas (escopo empresa, user_id=0)."""
    from app.agente.models import AgentMemory

    # Memorias empresa pertencem a user_id=0
    memories = AgentMemory.query.filter(
        AgentMemory.user_id == 0,
        AgentMemory.escopo == 'empresa',
        AgentMemory.is_directory == False,  # noqa: E712
    ).order_by(AgentMemory.updated_at.desc()).limit(args.limit).all()

    if args.json_mode:
        data = [{
            'id': m.id,
            'path': m.path,
            'category': m.category,
            'importance_score': round(m.importance_score, 2),
            'content_preview': truncate(m.content, 200) if m.content else '',
            'created_by': m.created_by,
            'updated_at': format_datetime(m.updated_at),
        } for m in memories]
        print(format_json({'total': len(data), 'memorias_empresa': data}))
    else:
        if not memories:
            print("Nenhuma memoria empresa encontrada.")
            return

        print(f"Memorias Empresa ({len(memories)}):\n")
        for m in memories:
            print(f"  [{m.category}] {m.path}")
            print(f"    {truncate(m.content, 100) if m.content else '(vazio)'}")
            print(f"    Criado por user_id={m.created_by} | Atualizado: {format_datetime(m.updated_at)}")
            print()


HANDLERS = {
    'patterns': handle_patterns,
    'pitfalls': handle_pitfalls,
    'analyze': handle_analyze,
    'extract': handle_extract,
    'empresa': handle_empresa,
}


def main():
    args, subcommand = parse_args_with_subcommands(
        'Padroes e aprendizado do agente', SUBCOMMANDS
    )

    # analyze e extract criam seu proprio app context via service
    # mas precisamos do contexto para resolver_user e queries
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
