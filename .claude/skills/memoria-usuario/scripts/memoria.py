#!/usr/bin/env python3
"""
Script para gerenciar memórias persistentes do usuário.

Implementa a interface da Memory Tool da Anthropic usando banco de dados.
Referência: https://platform.claude.com/docs/pt-BR/agents-and-tools/tool-use/memory-tool

Uso:
    python memoria.py view --user-id 1
    python memoria.py view --user-id 1 --path /memories/preferences.xml
    python memoria.py save --user-id 1 --path /memories/preferences.xml --content "<xml>...</xml>"
    python memoria.py update --user-id 1 --path /memories/preferences.xml --old "texto" --new "novo"
    python memoria.py delete --user-id 1 --path /memories/preferences.xml
    python memoria.py clear --user-id 1
"""

import sys
import os
import argparse
import json

# Adiciona raiz do projeto ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from app import create_app, db
from app.agente.models import AgentMemory


def view_memory(user_id: int, path: str = None):
    """
    Visualiza memórias do usuário.

    Se path não especificado, lista o diretório raiz /memories.
    Se path é diretório, lista conteúdo.
    Se path é arquivo, mostra conteúdo.
    """
    app = create_app()

    with app.app_context():
        if not path:
            path = '/memories'

        # Caso especial: /memories (raiz)
        if path == '/memories':
            items = AgentMemory.list_directory(user_id, path)

            if not items:
                # Cria diretório raiz virtual se não existir
                print(f"Directory: {path}")
                print("(empty - nenhuma memoria salva)")
                return

            print(f"Directory: {path}")
            for item in sorted(items, key=lambda x: x.path):
                name = item.path.split('/')[-1]
                suffix = '/' if item.is_directory else ''
                print(f"- {name}{suffix}")
            return

        # Busca path específico
        memory = AgentMemory.get_by_path(user_id, path)

        if not memory:
            print(f"ERRO: Path nao encontrado: {path}")
            sys.exit(1)

        # Se for diretório, lista conteúdo
        if memory.is_directory:
            items = AgentMemory.list_directory(user_id, path)

            print(f"Directory: {path}")
            if not items:
                print("(empty)")
            else:
                for item in sorted(items, key=lambda x: x.path):
                    name = item.path.split('/')[-1]
                    suffix = '/' if item.is_directory else ''
                    print(f"- {name}{suffix}")
            return

        # É arquivo, mostra conteúdo com números de linha
        content = memory.content or ""
        lines = content.splitlines()

        for i, line in enumerate(lines, 1):
            print(f"{i:4d}: {line}")


def save_memory(user_id: int, path: str, content: str):
    """Salva/cria memória."""
    app = create_app()

    with app.app_context():
        if not path.startswith('/memories'):
            print(f"ERRO: Path deve comecar com /memories")
            sys.exit(1)

        existing = AgentMemory.get_by_path(user_id, path)

        if existing:
            # Atualiza existente
            existing.content = content
            existing.is_directory = False
            action = "Atualizado"
        else:
            # Cria novo
            AgentMemory.create_file(user_id, path, content)
            action = "Criado"

        db.session.commit()
        print(f"{action}: {path}")


def update_memory(user_id: int, path: str, old_str: str, new_str: str):
    """Substitui texto em memória existente."""
    app = create_app()

    with app.app_context():
        memory = AgentMemory.get_by_path(user_id, path)

        if not memory:
            print(f"ERRO: Arquivo nao encontrado: {path}")
            sys.exit(1)

        if memory.is_directory:
            print(f"ERRO: Nao eh possivel editar um diretorio")
            sys.exit(1)

        content = memory.content or ""
        count = content.count(old_str)

        if count == 0:
            print(f"ERRO: Texto nao encontrado em {path}")
            sys.exit(1)
        elif count > 1:
            print(f"ERRO: Texto aparece {count} vezes. Deve ser unico.")
            sys.exit(1)

        memory.content = content.replace(old_str, new_str)
        db.session.commit()

        print(f"Atualizado: {path}")


def delete_memory(user_id: int, path: str):
    """Deleta memória (arquivo ou diretório)."""
    app = create_app()

    with app.app_context():
        if path == '/memories':
            print("ERRO: Nao eh possivel deletar o diretorio raiz /memories")
            sys.exit(1)

        memory = AgentMemory.get_by_path(user_id, path)

        if not memory:
            print(f"ERRO: Path nao encontrado: {path}")
            sys.exit(1)

        tipo = "Diretorio" if memory.is_directory else "Arquivo"
        count = AgentMemory.delete_by_path(user_id, path)

        db.session.commit()

        print(f"{tipo} deletado: {path}" + (f" ({count} itens)" if count > 1 else ""))


def clear_all_memory(user_id: int):
    """Limpa todas as memórias do usuário."""
    app = create_app()

    with app.app_context():
        count = AgentMemory.clear_all_for_user(user_id)
        db.session.commit()

        print(f"Todas as memorias limpas ({count} itens removidos)")


def main():
    parser = argparse.ArgumentParser(
        description='Gerencia memorias persistentes do usuario'
    )

    subparsers = parser.add_subparsers(dest='command', help='Comandos disponiveis')

    # view
    view_parser = subparsers.add_parser('view', help='Visualiza memorias')
    view_parser.add_argument('--user-id', type=int, required=True, help='ID do usuario')
    view_parser.add_argument('--path', type=str, help='Path da memoria (default: /memories)')

    # save
    save_parser = subparsers.add_parser('save', help='Salva memoria')
    save_parser.add_argument('--user-id', type=int, required=True, help='ID do usuario')
    save_parser.add_argument('--path', type=str, required=True, help='Path da memoria')
    save_parser.add_argument('--content', type=str, required=True, help='Conteudo a salvar')

    # update
    update_parser = subparsers.add_parser('update', help='Atualiza memoria (str_replace)')
    update_parser.add_argument('--user-id', type=int, required=True, help='ID do usuario')
    update_parser.add_argument('--path', type=str, required=True, help='Path da memoria')
    update_parser.add_argument('--old', type=str, required=True, help='Texto a substituir')
    update_parser.add_argument('--new', type=str, required=True, help='Novo texto')

    # delete
    delete_parser = subparsers.add_parser('delete', help='Deleta memoria')
    delete_parser.add_argument('--user-id', type=int, required=True, help='ID do usuario')
    delete_parser.add_argument('--path', type=str, required=True, help='Path da memoria')

    # clear
    clear_parser = subparsers.add_parser('clear', help='Limpa todas as memorias')
    clear_parser.add_argument('--user-id', type=int, required=True, help='ID do usuario')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == 'view':
        view_memory(args.user_id, args.path)
    elif args.command == 'save':
        save_memory(args.user_id, args.path, args.content)
    elif args.command == 'update':
        update_memory(args.user_id, args.path, args.old, args.new)
    elif args.command == 'delete':
        delete_memory(args.user_id, args.path)
    elif args.command == 'clear':
        clear_all_memory(args.user_id)


if __name__ == '__main__':
    main()
