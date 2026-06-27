"""Migration HORA 55: perfis de permissao das Lojas HORA.

Cria `hora_perfil` (definicao do perfil) e `hora_perfil_permissao` (esqueleto de
permissoes por perfil x modulo). O DDL vive no .sql irmao (lido do disco); este
.py instancia o app, executa o SQL e valida idempotencia.

Slug do perfil HORA usa prefixo 'hora_' e nunca colide com os 6 slugs reservados
do sistema — ver cabecalho do .sql para o racional completo.

Uso:
    python scripts/migrations/hora_55_perfis.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_PATH = os.path.join(os.path.dirname(__file__), 'hora_55_perfis.sql')

SQL_TABELAS_EXISTEM = """
SELECT COUNT(*) FROM information_schema.tables
WHERE table_schema = 'public' AND table_name IN ('hora_perfil', 'hora_perfil_permissao')
"""


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        with open(SQL_PATH, encoding='utf-8') as f:
            sql = f.read()

        with db.engine.begin() as conn:
            antes = conn.execute(text(SQL_TABELAS_EXISTEM)).scalar()
            print(f'Tabelas hora_perfil* existentes antes: {antes}/2')

            conn.execute(text(sql))

            depois = conn.execute(text(SQL_TABELAS_EXISTEM)).scalar()
            print(f'Tabelas hora_perfil* existentes depois: {depois}/2')

        print('\nMigration HORA 55 concluida com sucesso.')


if __name__ == '__main__':
    main()
