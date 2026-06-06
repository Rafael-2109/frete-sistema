"""Migration HORA 45: tabela de dedupe/auditoria de notificações WhatsApp.

Cria a tabela `hora_tagplus_notificacao_whatsapp` usada para:
  - Garantir idempotência (UNIQUE tipo + ref_id): uma notificação por evento.
  - Rastrear status de envio para grupo e vendedor individualmente.
  - Auditar tentativas, erros e horário de envio.

Eventos cobertos:
  - tipo='NFE'    -> HoraTagPlusNfeEmissao.id  (NFe aprovada)
  - tipo='PEDIDO' -> HoraVenda.id              (pedido confirmado)

Idempotente — pode rodar 2x sem erro (CREATE IF NOT EXISTS + índices IF NOT EXISTS).

Uso:
    python scripts/migrations/hora_45_tagplus_notificacao_whatsapp.py
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
    CREATE TABLE IF NOT EXISTS hora_tagplus_notificacao_whatsapp (
        id               SERIAL PRIMARY KEY,
        tipo             VARCHAR(10)  NOT NULL,
        ref_id           INTEGER      NOT NULL,
        numero           VARCHAR(30),
        cliente_nome     VARCHAR(255),
        vendedor_nome    VARCHAR(120),
        loja_nome        VARCHAR(120),
        valor            NUMERIC(15,2),
        enviado_grupo    BOOLEAN      NOT NULL DEFAULT FALSE,
        enviado_vendedor BOOLEAN,
        status           VARCHAR(15)  NOT NULL DEFAULT 'PENDENTE',
        erro             TEXT,
        tentativas       INTEGER      NOT NULL DEFAULT 0,
        anexou_pdf       BOOLEAN      NOT NULL DEFAULT FALSE,
        enviado_em       TIMESTAMP,
        criado_em        TIMESTAMP    NOT NULL DEFAULT NOW()
    )
    """,
    """
    CREATE UNIQUE INDEX IF NOT EXISTS uq_hora_tagplus_notif_tipo_ref
        ON hora_tagplus_notificacao_whatsapp (tipo, ref_id)
    """,
    """
    CREATE INDEX IF NOT EXISTS idx_hora_tagplus_notif_status
        ON hora_tagplus_notificacao_whatsapp (status)
    """,
]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        tabelas = inspector.get_table_names()
        tabela_existe = 'hora_tagplus_notificacao_whatsapp' in tabelas

        print('Estado antes:')
        print(f'  hora_tagplus_notificacao_whatsapp existe? {tabela_existe}')
        if tabela_existe:
            colunas = [c['name'] for c in inspector.get_columns('hora_tagplus_notificacao_whatsapp')]
            print(f'  colunas: {colunas}')

        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))

        inspector = inspect(db.engine)
        tabelas = inspector.get_table_names()
        tabela_existe = 'hora_tagplus_notificacao_whatsapp' in tabelas

        print('\nEstado depois:')
        print(f'  hora_tagplus_notificacao_whatsapp existe? {tabela_existe}')
        if tabela_existe:
            colunas = [c['name'] for c in inspector.get_columns('hora_tagplus_notificacao_whatsapp')]
            print(f'  colunas: {colunas}')

        if not tabela_existe:
            print('\nERRO: tabela não foi criada.')
            sys.exit(1)

        print('\nMigration HORA 45 concluída com sucesso.')


if __name__ == '__main__':
    main()
