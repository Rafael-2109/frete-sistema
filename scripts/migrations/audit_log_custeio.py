"""
Migration: Audit log dedicado do modulo Custeio
Sprint 3 - C16 (auditoria 2026-05-10)
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from app import create_app, db


DDL = [
    """CREATE TABLE IF NOT EXISTS audit_log_custeio (
        id SERIAL PRIMARY KEY,
        timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
        usuario VARCHAR(100) NOT NULL,
        ip_address VARCHAR(45) NULL,
        session_id VARCHAR(100) NULL,
        entidade VARCHAR(50) NOT NULL,
        entidade_id INTEGER NULL,
        evento VARCHAR(20) NOT NULL,
        antes_json TEXT NULL,
        depois_json TEXT NULL,
        motivo TEXT NULL,
        contexto VARCHAR(255) NULL
    )""",
    "CREATE INDEX IF NOT EXISTS ix_audit_custeio_timestamp ON audit_log_custeio(timestamp)",
    "CREATE INDEX IF NOT EXISTS ix_audit_custeio_usuario ON audit_log_custeio(usuario)",
    "CREATE INDEX IF NOT EXISTS ix_audit_custeio_entidade ON audit_log_custeio(entidade)",
    "CREATE INDEX IF NOT EXISTS ix_audit_custeio_entidade_id ON audit_log_custeio(entidade_id)",
    "CREATE INDEX IF NOT EXISTS ix_audit_custeio_evento ON audit_log_custeio(evento)",
    "CREATE INDEX IF NOT EXISTS idx_audit_custeio_entidade_id ON audit_log_custeio(entidade, entidade_id)",
    "CREATE INDEX IF NOT EXISTS idx_audit_custeio_timestamp_evento ON audit_log_custeio(timestamp, evento)",
]


def run():
    app = create_app()
    with app.app_context():
        for ddl in DDL:
            db.session.execute(db.text(ddl))
        db.session.commit()
        print("Tabela audit_log_custeio criada com indices.")


if __name__ == '__main__':
    run()
