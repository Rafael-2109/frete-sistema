"""
Modulo compartilhado para scripts da skill gerindo-agente.

Fornece setup de app context, formatacao, parsing de argumentos e helpers comuns.
Todos os scripts desta skill importam deste modulo.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


def sys_path_setup():
    """Configura sys.path para importar modulos do app."""
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), '..', '..', '..', '..')
    )
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


def get_app_context():
    """
    Cria Flask app e retorna (app, ctx) com app context ativo.

    Uso:
        app, ctx = get_app_context()
        with ctx:
            # operacoes com banco
    """
    sys_path_setup()
    from app import create_app
    app = create_app()
    ctx = app.app_context()
    return app, ctx


def add_common_args(parser: argparse.ArgumentParser) -> None:
    """Adiciona argumentos comuns a todos os scripts."""
    parser.add_argument(
        '--user-id', type=int, required=True,
        help='ID do usuario no banco de dados'
    )
    parser.add_argument(
        '--json', action='store_true', dest='json_mode',
        help='Saida em formato JSON'
    )
    parser.add_argument(
        '--limit', type=int, default=20,
        help='Limite de resultados (default: 20)'
    )


def format_table(headers: List[str], rows: List[List[str]], max_col_width: int = 50) -> str:
    """
    Formata dados como tabela plain-text alinhada.

    Args:
        headers: Nomes das colunas
        rows: Lista de linhas (cada linha e uma lista de strings)
        max_col_width: Largura maxima por coluna

    Returns:
        String formatada como tabela
    """
    if not rows:
        return "(vazio)"

    # Truncar valores e converter para string
    str_rows = []
    for row in rows:
        str_row = [truncate(str(cell), max_col_width) for cell in row]
        str_rows.append(str_row)

    # Calcular largura de cada coluna
    col_widths = []
    for i, header in enumerate(headers):
        max_width = len(header)
        for row in str_rows:
            if i < len(row):
                max_width = max(max_width, len(row[i]))
        col_widths.append(min(max_width, max_col_width))

    # Formatar header
    header_line = ' | '.join(h.ljust(col_widths[i]) for i, h in enumerate(headers))
    separator = '-+-'.join('-' * w for w in col_widths)

    # Formatar linhas
    lines = [header_line, separator]
    for row in str_rows:
        line = ' | '.join(
            (row[i] if i < len(row) else '').ljust(col_widths[i])
            for i in range(len(headers))
        )
        lines.append(line)

    return '\n'.join(lines)


def format_datetime(dt: Optional[datetime]) -> str:
    """Formata datetime como DD/MM/YYYY HH:MM (BR naive)."""
    if not dt:
        return '-'
    return dt.strftime('%d/%m/%Y %H:%M')


def format_json(data: Any) -> str:
    """Serializa para JSON formatado."""
    return json.dumps(data, indent=2, ensure_ascii=False, default=str)


def truncate(text: str, max_len: int = 80) -> str:
    """Trunca texto com '...' se exceder max_len."""
    if not text:
        return ''
    if len(text) <= max_len:
        return text
    return text[:max_len - 3] + '...'


def resolve_user(user_id: int) -> dict:
    """
    Valida que user_id existe no banco. Retorna dict com dados basicos.

    Raises:
        SystemExit: Se usuario nao encontrado
    """
    from app.auth.models import Usuario
    user = Usuario.query.get(user_id)
    if not user:
        error_exit(f"Usuario com ID={user_id} nao encontrado.")
    return {'id': user.id, 'nome': user.nome, 'email': user.email}


def success_output(data: Any, json_mode: bool = False) -> None:
    """Imprime resultado formatado (text ou JSON)."""
    if json_mode:
        if isinstance(data, str):
            print(data)
        else:
            print(format_json(data))
    else:
        if isinstance(data, str):
            print(data)
        elif isinstance(data, dict):
            for key, value in data.items():
                print(f"{key}: {value}")
        elif isinstance(data, list):
            for item in data:
                print(item)


def error_exit(msg: str, code: int = 1) -> None:
    """Imprime erro para stderr e encerra."""
    print(f"ERRO: {msg}", file=sys.stderr)
    sys.exit(code)


def parse_args_with_subcommands(
    description: str,
    subcommands: Dict[str, Dict[str, Any]],
) -> Tuple[argparse.Namespace, str]:
    """
    Cria parser com subcomandos e retorna (args, subcomando).

    Args:
        description: Descricao do script
        subcommands: Dict {nome: {help, args: [{name, **kwargs}]}}

    Returns:
        Tupla (args, nome_subcomando)
    """
    parser = argparse.ArgumentParser(description=description)
    subparsers = parser.add_subparsers(dest='subcommand', help='Subcomando')
    subparsers.required = True

    for name, config in subcommands.items():
        sub = subparsers.add_parser(name, help=config.get('help', ''))
        add_common_args(sub)

        for arg in config.get('args', []):
            arg_name = arg.pop('name')
            sub.add_argument(arg_name, **arg)
            # Restaurar 'name' para reutilizacao
            arg['name'] = arg_name

    args = parser.parse_args()
    return args, args.subcommand
