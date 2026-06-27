"""Migration HORA 56: coluna whatsapp_grupo_jid em hora_loja.

Adiciona `whatsapp_grupo_jid VARCHAR(60)` (nullable) à loja para o requisito
"1 grupo por loja": a loja do pedido/NF indica para qual grupo WhatsApp a
notificação é enviada (JID Baileys "...@g.us"). Antes havia um único grupo
global (env HORA_TAGPLUS_NOTIFY_GROUP_JID); agora é por loja, configurado na
tela da loja (dropdown ao vivo dos grupos da Evolution). Decisão 2026-06-27.

Idempotente — ADD COLUMN IF NOT EXISTS.

Uso:
    python scripts/migrations/hora_56_loja_whatsapp_grupo.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    "ALTER TABLE hora_loja ADD COLUMN IF NOT EXISTS whatsapp_grupo_jid VARCHAR(60)",
]


def _colunas() -> list:
    return [c['name'] for c in inspect(db.engine).get_columns('hora_loja')]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        print('Estado antes:')
        print(f'  hora_loja.whatsapp_grupo_jid existe? {"whatsapp_grupo_jid" in _colunas()}')

        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))

        existe = 'whatsapp_grupo_jid' in _colunas()
        print('\nEstado depois:')
        print(f'  hora_loja.whatsapp_grupo_jid existe? {existe}')

        if not existe:
            print('\nERRO: coluna nao foi criada.')
            sys.exit(1)

        print('\nMigration HORA 56 concluida com sucesso.')


if __name__ == '__main__':
    main()
