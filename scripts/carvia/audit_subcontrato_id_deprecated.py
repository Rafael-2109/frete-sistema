#!/usr/bin/env python3
"""R2.4 (2026-04-19): Auditoria read-only de CarviaFrete.subcontrato_id
(FK deprecated — ver comentario no modelo frete.py).

Objetivo de integridade: detectar divergencias entre o caminho antigo
(CarviaFrete.subcontrato_id singular) e o caminho canonical
(CarviaSubcontrato.frete_id reverso 1:N).

Cenarios flagados:
  1. CarviaFrete com subcontrato_id mas o sub nao tem frete_id apontando
     de volta (orfao no path novo).
  2. CarviaFrete sem subcontrato_id mas tem subs vinculados via frete_id
     (path novo OK, antigo vazio — esperado apos transicao).
  3. CarviaFrete.subcontrato_id apontando para sub que ja foi CANCELADO.

READ-ONLY. Nao modifica dados. Use antes de refatorar call sites.

Uso local:
    source .venv/bin/activate
    python scripts/carvia/audit_subcontrato_id_deprecated.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app, db  # noqa: E402
from sqlalchemy import text  # noqa: E402


def main():
    app = create_app()
    with app.app_context():
        print('=' * 60)
        print('R2.4 — Auditoria CarviaFrete.subcontrato_id (DEPRECATED)')
        print('=' * 60)

        # Usa SQL direto para evitar drift model/schema local (ver CLAUDE.md)
        total_fretes = db.session.execute(text(
            'SELECT COUNT(*) FROM carvia_fretes'
        )).scalar()
        fretes_com_sub_dep = db.session.execute(text(
            'SELECT COUNT(*) FROM carvia_fretes WHERE subcontrato_id IS NOT NULL'
        )).scalar()
        print(f'Total CarviaFrete:                      {total_fretes}')
        print(f'Com subcontrato_id (deprecated) setado: {fretes_com_sub_dep}')
        print()

        # Cenario 1: CarviaFrete.subcontrato_id mas sub.frete_id != frete.id
        try:
            divergentes = db.session.execute(text("""
                SELECT f.id AS frete_id, f.subcontrato_id,
                       s.frete_id AS sub_frete_id, s.status AS sub_status
                FROM carvia_fretes f
                JOIN carvia_subcontratos s ON s.id = f.subcontrato_id
                WHERE f.subcontrato_id IS NOT NULL
                  AND (s.frete_id IS NULL OR s.frete_id != f.id)
                ORDER BY f.id DESC
                LIMIT 50
            """)).fetchall()
            print(f'Cenario 1 — divergencia frete.subcontrato_id vs '
                  f'sub.frete_id reverso:')
            print(f'  {len(divergentes)} divergencia(s) (mostrando ate 50)')
            for row in divergentes[:5]:
                print(f'    frete={row.frete_id} sub={row.subcontrato_id} '
                      f'sub.frete_id={row.sub_frete_id} '
                      f'(sub_status={row.sub_status})')
        except Exception as e:
            print(f'  erro: {e}')
            db.session.rollback()
        print()

        # Cenario 2: frete sem subcontrato_id mas com subs via frete_id
        try:
            ok_path_novo = db.session.execute(text("""
                SELECT COUNT(DISTINCT f.id) AS total
                FROM carvia_fretes f
                JOIN carvia_subcontratos s ON s.frete_id = f.id
                WHERE f.subcontrato_id IS NULL
                  AND s.status != 'CANCELADO'
            """)).scalar()
            print(f'Cenario 2 — fretes usando APENAS path novo '
                  f'(sub.frete_id): {ok_path_novo}')
        except Exception as e:
            print(f'  erro: {e}')
            db.session.rollback()
        print()

        # Cenario 3: subcontrato_id aponta para sub CANCELADO
        try:
            cancelados = db.session.execute(text("""
                SELECT f.id, f.subcontrato_id, s.status
                FROM carvia_fretes f
                JOIN carvia_subcontratos s ON s.id = f.subcontrato_id
                WHERE f.subcontrato_id IS NOT NULL
                  AND s.status = 'CANCELADO'
                ORDER BY f.id DESC
                LIMIT 20
            """)).fetchall()
            print(f'Cenario 3 — frete.subcontrato_id aponta para sub '
                  f'CANCELADO: {len(cancelados)}')
            for row in cancelados[:5]:
                print(f'    frete={row.id} -> sub={row.subcontrato_id} '
                      f'({row.status})')
        except Exception as e:
            print(f'  erro: {e}')
            db.session.rollback()

        print()
        print('=' * 60)
        print('Resultado: este script e read-only. Para cada divergencia')
        print('detectada, planejar migracao do callsite correspondente')
        print('(lista em scripts/carvia/refactor_2_4_callers.md — TODO).')
        print('=' * 60)


if __name__ == '__main__':
    main()
