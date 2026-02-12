#!/usr/bin/env python3
"""
Hook PostToolUse: Lembrete de Migration Par (.py + .sql) + Padrao de Conexao

Detecta criacao/edicao de arquivos em scripts/migrations/ e:
1. Avisa se o par correspondente (.py <-> .sql) nao existe
2. Lembra do padrao CORRETO de conexao para migrations

Nao bloqueia (exit 0 sempre). Apenas imprime aviso em stderr.
"""

import json
import os
import sys


PADRAO_CONEXAO = """
  PADRAO OBRIGATORIO para scripts de migration:
  -----------------------------------------------
  USAR 3 blocos with SEPARADOS (NUNCA reusar conexao apos commit):

    with db.engine.connect() as conn:   # BEFORE (read-only)
        ...

    with db.engine.begin() as conn:     # EXECUTE (auto-commit ao sair)
        ...

    with db.engine.connect() as conn:   # AFTER (conexao NOVA)
        ...

  NUNCA FAZER:
    conn = db.session.connection()  # conexao FECHA apos commit
    db.session.commit()             # conn morta a partir daqui
    conn.execute(...)               # ResourceClosedError!
"""


def main():
    try:
        input_data = sys.stdin.read()
        if not input_data:
            return

        event = json.loads(input_data)

        tool_name = event.get("tool_name", "")
        tool_input = event.get("tool_input", {})

        if tool_name not in ("Write", "Edit"):
            return

        file_path = tool_input.get("file_path", "")

        # So interessa arquivos em scripts/migrations/
        if "scripts/migrations/" not in file_path:
            return

        base, ext = os.path.splitext(file_path)
        mensagens = []

        # Verificar par .py <-> .sql
        if ext == ".py":
            par = base + ".sql"
            tipo_faltante = "SQL"
        elif ext == ".sql":
            par = base + ".py"
            tipo_faltante = "Python"
        else:
            return

        if not os.path.exists(par):
            nome_base = os.path.basename(base)
            mensagens.append(
                f"  PAR {tipo_faltante} NAO ENCONTRADO\n"
                f"  Criado:   {os.path.basename(file_path)}\n"
                f"  Faltando: {nome_base}{'.sql' if ext == '.py' else '.py'}\n"
                f"  Regra: DDL requer DOIS artefatos (.py + .sql).\n"
                f"  Excecao: data fixes (UPDATE/INSERT) podem ser so .py."
            )

        # Sempre lembrar padrao de conexao para .py
        if ext == ".py":
            mensagens.append(PADRAO_CONEXAO)

        if mensagens:
            print(
                "\n"
                "================================================\n"
                "  MIGRATION: LEMBRETES\n"
                "================================================",
                file=sys.stderr,
            )
            for msg in mensagens:
                print(msg, file=sys.stderr)
            print(
                "================================================\n",
                file=sys.stderr,
            )

    except Exception:
        pass  # Hook nao deve bloquear nunca


if __name__ == "__main__":
    main()
