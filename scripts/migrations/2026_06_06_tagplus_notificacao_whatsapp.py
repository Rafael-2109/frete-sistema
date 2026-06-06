# scripts/migrations/2026_06_06_tagplus_notificacao_whatsapp.py
"""Migration: cria tabela tagplus_notificacao_whatsapp (notificações WhatsApp TagPlus).

Idempotente — usa CREATE TABLE/INDEX IF NOT EXISTS.

Uso:
    python scripts/migrations/2026_06_06_tagplus_notificacao_whatsapp.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    """
    CREATE TABLE IF NOT EXISTS tagplus_notificacao_whatsapp (
        id               SERIAL PRIMARY KEY,
        tipo             VARCHAR(10)  NOT NULL,
        event_type       VARCHAR(30)  NOT NULL,
        tagplus_id       VARCHAR(30)  NOT NULL,
        numero           VARCHAR(30),
        cliente_nome     VARCHAR(255),
        valor            NUMERIC(15,2),
        vendedor_nome    VARCHAR(120),
        vendedor_user_id INTEGER,
        enviado_grupo    BOOLEAN      NOT NULL DEFAULT FALSE,
        enviado_vendedor BOOLEAN,
        status           VARCHAR(15)  NOT NULL DEFAULT 'PENDENTE',
        erro             TEXT,
        tentativas       INTEGER      NOT NULL DEFAULT 0,
        anexou_pdf       BOOLEAN      NOT NULL DEFAULT FALSE,
        enviado_em       TIMESTAMP,
        criado_em        TIMESTAMP    NOT NULL DEFAULT NOW()
    );
    """,
    "CREATE UNIQUE INDEX IF NOT EXISTS uq_tagplus_notif_tipo_id_event "
    "ON tagplus_notificacao_whatsapp (tipo, tagplus_id, event_type);",
    "CREATE INDEX IF NOT EXISTS idx_tagplus_notif_status "
    "ON tagplus_notificacao_whatsapp (status);",
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        existe_antes = 'tagplus_notificacao_whatsapp' in inspector.get_table_names()
        print(f'Estado antes: tabela existe? {existe_antes}')
        for ddl in SQL_DDL:
            db.session.execute(text(ddl))
        db.session.commit()
        inspector = inspect(db.engine)
        existe_depois = 'tagplus_notificacao_whatsapp' in inspector.get_table_names()
        cols = {c['name'] for c in inspector.get_columns('tagplus_notificacao_whatsapp')}
        print(f'Estado depois: tabela existe? {existe_depois}')
        print(f'Colunas: {sorted(cols)}')


if __name__ == '__main__':
    main()
