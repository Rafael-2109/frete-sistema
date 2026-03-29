#!/usr/bin/env python3
"""
Migration: Indexes de performance para entregas_monitoradas
============================================================

Adiciona indexes em colunas frequentemente filtradas que nao tinham indice:
- status_finalizacao, data_embarque, data_agenda, data_faturamento, transportadora
- Partial indexes para booleans: entregue=false, nf_cd=true, reagendar=true

Data: 2026-03-29
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db
from sqlalchemy import text


INDEXES = [
    ("idx_em_status_finalizacao", "CREATE INDEX IF NOT EXISTS idx_em_status_finalizacao ON entregas_monitoradas (status_finalizacao)"),
    ("idx_em_data_embarque", "CREATE INDEX IF NOT EXISTS idx_em_data_embarque ON entregas_monitoradas (data_embarque)"),
    ("idx_em_data_agenda", "CREATE INDEX IF NOT EXISTS idx_em_data_agenda ON entregas_monitoradas (data_agenda)"),
    ("idx_em_data_faturamento", "CREATE INDEX IF NOT EXISTS idx_em_data_faturamento ON entregas_monitoradas (data_faturamento)"),
    ("idx_em_transportadora", "CREATE INDEX IF NOT EXISTS idx_em_transportadora ON entregas_monitoradas (transportadora)"),
    ("idx_em_entregue", "CREATE INDEX IF NOT EXISTS idx_em_entregue ON entregas_monitoradas (entregue) WHERE entregue = false"),
    ("idx_em_nf_cd", "CREATE INDEX IF NOT EXISTS idx_em_nf_cd ON entregas_monitoradas (nf_cd) WHERE nf_cd = true"),
    ("idx_em_reagendar", "CREATE INDEX IF NOT EXISTS idx_em_reagendar ON entregas_monitoradas (reagendar) WHERE reagendar = true"),
]


def run():
    app = create_app()
    with app.app_context():
        # Verificar indexes existentes antes
        result = db.session.execute(text("""
            SELECT indexname FROM pg_indexes WHERE tablename = 'entregas_monitoradas'
        """))
        existing = {row[0] for row in result}
        print(f"Indexes existentes: {len(existing)}")
        for idx_name in sorted(existing):
            print(f"  - {idx_name}")

        # Criar indexes
        created = 0
        for idx_name, ddl in INDEXES:
            if idx_name in existing:
                print(f"  [SKIP] {idx_name} ja existe")
            else:
                print(f"  [CREATE] {idx_name}...")
                db.session.execute(text(ddl))
                created += 1

        # ANALYZE para atualizar estatisticas
        db.session.execute(text("ANALYZE entregas_monitoradas"))
        db.session.commit()

        # Verificar apos
        result = db.session.execute(text("""
            SELECT indexname FROM pg_indexes WHERE tablename = 'entregas_monitoradas'
        """))
        after = {row[0] for row in result}
        print(f"\nIndexes apos migration: {len(after)} ({created} criados)")
        for idx_name in sorted(after):
            print(f"  - {idx_name}")


if __name__ == "__main__":
    run()
