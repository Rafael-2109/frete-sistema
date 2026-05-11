"""
HISTORICO D8 — Correcoes 2026-05-11

Insere/atualiza 5 entradas no agent_improvement_dialogue documentando:

1. IMP-2026-05-11-002 v3 — CORRECAO: a deducao da v1 (D8 batch 04:01 BRT)
   estava errada. JSONLs de 6 linhas/turns=0 NAO eram padrao normal;
   eram fallback filesystem do CLI causado por bug no agent_loader.py
   (commit 8d2d28f1 corrigiu).

2. IMP-2026-05-11-004 v1 — max_turns=30 hardcoded no client.py cortava
   respostas longas. Removido em 2026-05-11.

3. IMP-2026-05-11-005 v1 — additionalProperties=true no schema do
   session_summarizer quebrava structured outputs (Sentry PYTHON-FLASK-A0,
   62 events). Trocado para false em 2026-05-11.

4. IMP-2026-05-11-006 v1 — text_to_sql_tool passava UUID para campos
   bigint (Sentry PYTHON-FLASK-M, 32 events). Adicionada deteccao
   pre-execucao em 2026-05-11.

5. IMP-2026-05-11-007 v1 — REQUEST_TIMEOUT=10s em render_logs_tool.py
   estourava com horas=24, agente reportava "nao tenho acesso ao MCP
   Render". Aumentado para 30s em 2026-05-11.

Idempotente: usa ON CONFLICT (suggestion_key, version) DO UPDATE.
Pode ser rodado multiplas vezes sem efeitos colaterais.

Uso local (banco local): python scripts/migrations/2026-05-11_historico_d8_correcoes.py
Uso producao (Render Shell): python scripts/migrations/2026-05-11_historico_d8_correcoes.py
"""

import os
import sys

# Garante path do projeto antes de importar app (regra CLAUDE.md/memory)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


def main() -> int:
    sql_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            '2026-05-11_historico_d8_correcoes.sql')

    if not os.path.exists(sql_path):
        print(f"[ERRO] SQL nao encontrado: {sql_path}")
        return 1

    with open(sql_path, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    app = create_app()
    with app.app_context():
        # Mostra a qual banco esta conectado (auditoria)
        url = db.engine.url
        host = url.host or "?"
        db_name = url.database or "?"
        print(f"[INFO] Conectado a: postgresql://***@{host}/{db_name}")

        # before: contagem das entradas alvo
        before = db.session.execute(text("""
            SELECT COUNT(*) FROM agent_improvement_dialogue
            WHERE suggestion_key IN (
                'IMP-2026-05-11-002', 'IMP-2026-05-11-004', 'IMP-2026-05-11-005',
                'IMP-2026-05-11-006', 'IMP-2026-05-11-007'
            )
        """)).scalar() or 0
        print(f"[BEFORE] Entradas alvo existentes: {before}")

        # Executa o SQL inteiro (transacao gerenciada pelo BEGIN/COMMIT no SQL)
        # Nota: SQLAlchemy auto-commit nao se aplica — exec_driver_sql roda raw.
        with db.engine.connect() as conn:
            for statement in _split_sql(sql_content):
                conn.exec_driver_sql(statement)
            conn.commit()

        # after: lista resultado final
        after_rows = db.session.execute(text("""
            SELECT suggestion_key, version, author, severity, LEFT(title, 80) AS titulo
            FROM agent_improvement_dialogue
            WHERE suggestion_key IN (
                'IMP-2026-05-11-002', 'IMP-2026-05-11-004', 'IMP-2026-05-11-005',
                'IMP-2026-05-11-006', 'IMP-2026-05-11-007'
            )
              AND (suggestion_key != 'IMP-2026-05-11-002' OR version = 3)
            ORDER BY suggestion_key, version
        """)).fetchall()

        print(f"[AFTER] {len(after_rows)} entradas alvo registradas:")
        for r in after_rows:
            d = r._mapping
            print(f"  - {d['suggestion_key']} v{d['version']:>2} "
                  f"| {d['author']:>11} | {d['severity']:>8} | {d['titulo']}")

        if len(after_rows) != 5:
            print("[ERRO] Esperado 5 entradas, obtido " + str(len(after_rows)))
            return 2

    print("[OK] Historico D8 atualizado com sucesso.")
    return 0


def _split_sql(sql: str) -> list:
    """Divide o SQL em statements separando por ';' simples no nivel raiz.

    Ignora ';' dentro de strings literais simples. Suficiente para este SQL.
    Remove statements vazios e comentarios isolados.
    """
    statements = []
    current = []
    in_string = False
    for ch in sql:
        if ch == "'" and (not current or current[-1] != '\\'):
            in_string = not in_string
        if ch == ';' and not in_string:
            stmt = ''.join(current).strip()
            if stmt and not _is_comment_only(stmt):
                statements.append(stmt)
            current = []
        else:
            current.append(ch)
    # Tail (sem ';' final)
    tail = ''.join(current).strip()
    if tail and not _is_comment_only(tail):
        statements.append(tail)
    return statements


def _is_comment_only(stmt: str) -> bool:
    """True se o statement so contem comentarios SQL (-- ... ou /* */)."""
    lines = [ln.strip() for ln in stmt.split('\n') if ln.strip()]
    return all(ln.startswith('--') or ln.startswith('/*') for ln in lines)


if __name__ == '__main__':
    sys.exit(main())
