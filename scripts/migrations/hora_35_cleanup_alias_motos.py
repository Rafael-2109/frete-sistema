"""HORA 35: limpa motos vinculadas a modelos absorvidos (aliases).

Atualiza `hora_moto.modelo_id` para o canonico quando a moto aponta para um
modelo com `merged_em_id IS NOT NULL`. Resolve a inconsistencia em que motos
criadas APOS um merge ficaram apontando para o alias absorvido (ex.: chassi
LYDAE3930T1204206 vinculado a MOTO ELETRICA TIPO SCOOTER JETMAX, alias
mergido em JET MAX).

Idempotente: 2x executa sem efeito apos a primeira corrida.

Uso:
    python scripts/migrations/hora_35_cleanup_alias_motos.py
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402


def main() -> int:
    app = create_app()
    with app.app_context():
        # 1. Diagnostico antes
        rows_before = db.session.execute(text(
            """
            SELECT mt.numero_chassi, mt.modelo_id, m.nome_modelo,
                   m.merged_em_id, c.nome_modelo AS canonico_nome
            FROM hora_moto mt
            JOIN hora_modelo m ON m.id = mt.modelo_id
            JOIN hora_modelo c ON c.id = m.merged_em_id
            WHERE m.merged_em_id IS NOT NULL
            ORDER BY mt.numero_chassi
            """
        )).fetchall()
        print(f'[BEFORE] motos vinculadas a alias mergido: {len(rows_before)}')
        for r in rows_before[:20]:
            print(
                f'  - chassi={r.numero_chassi} modelo_id={r.modelo_id} '
                f'({r.nome_modelo!r}) -> canonico={r.merged_em_id} '
                f'({r.canonico_nome!r})'
            )

        if not rows_before:
            print('[OK] Nada a fazer — todas as motos ja apontam para canonicos.')
            return 0

        # 2. UPDATE: para cada moto, modelo_id = canonico (m.merged_em_id).
        result = db.session.execute(text(
            """
            UPDATE hora_moto AS mt
            SET modelo_id = m.merged_em_id
            FROM hora_modelo AS m
            WHERE mt.modelo_id = m.id
              AND m.merged_em_id IS NOT NULL
            """
        ))
        n_atualizadas = result.rowcount
        db.session.commit()
        print(f'[UPDATE] {n_atualizadas} moto(s) atualizada(s).')

        # 3. Diagnostico depois — deve ser 0
        rows_after = db.session.execute(text(
            """
            SELECT COUNT(*) AS total
            FROM hora_moto mt
            JOIN hora_modelo m ON m.id = mt.modelo_id
            WHERE m.merged_em_id IS NOT NULL
            """
        )).fetchone()
        total_after = rows_after.total if rows_after else 0
        print(f'[AFTER] motos ainda vinculadas a alias: {total_after}')

        if total_after > 0:
            print('[ERRO] Ainda ha motos pendentes — investigar.')
            return 1

        print('[OK] Cleanup concluido com sucesso.')
        return 0


if __name__ == '__main__':
    sys.exit(main())
