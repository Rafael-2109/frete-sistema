"""Migration HORA 43: criterio de listagem de pedidos por usuario + criador do pedido.

Mudancas:
  1. usuarios       -> +criterio_pedidos_hora VARCHAR(10) NOT NULL DEFAULT 'loja'
  2. hora_venda     -> +criado_por_id INTEGER (sem FK; padrao do modulo) + indice
  3. backfill criado_por_id via hora_venda_auditoria (acao='CRIOU', match por nome)

Idempotente — pode rodar 2x (IF NOT EXISTS + backfill so onde criado_por_id IS NULL).

Uso:
    python scripts/migrations/hora_43_criterio_pedidos_e_criador.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    "ALTER TABLE usuarios "
    "ADD COLUMN IF NOT EXISTS criterio_pedidos_hora VARCHAR(10) NOT NULL DEFAULT 'loja';",
    "ALTER TABLE hora_venda "
    "ADD COLUMN IF NOT EXISTS criado_por_id INTEGER;",
    "CREATE INDEX IF NOT EXISTS idx_hora_venda_criado_por_id "
    "ON hora_venda (criado_por_id);",
]

SQL_BACKFILL = """
-- Deterministico: agrega por venda e usa MIN(u.id) — evita resultado arbitrario
-- quando ha usuarios homonimos (usuarios.nome nao e UNIQUE).
UPDATE hora_venda v
   SET criado_por_id = sub.user_id
  FROM (
      SELECT a.venda_id, MIN(u.id) AS user_id
        FROM hora_venda_auditoria a
        JOIN usuarios u ON u.nome = a.usuario
       WHERE a.acao = 'CRIOU'
       GROUP BY a.venda_id
  ) sub
 WHERE sub.venda_id = v.id
   AND v.criado_por_id IS NULL;
"""


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        cols_user = {c['name'] for c in inspector.get_columns('usuarios')}
        cols_venda = {c['name'] for c in inspector.get_columns('hora_venda')}
        print('Estado antes:')
        print(f'  usuarios.criterio_pedidos_hora? {"criterio_pedidos_hora" in cols_user}')
        print(f'  hora_venda.criado_por_id? {"criado_por_id" in cols_venda}')

        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))
            res = conn.execute(text(SQL_BACKFILL))
            backfilled = res.rowcount if res.rowcount is not None else -1

        inspector = inspect(db.engine)
        cols_user = {c['name'] for c in inspector.get_columns('usuarios')}
        cols_venda = {c['name'] for c in inspector.get_columns('hora_venda')}
        print('\nEstado depois:')
        print(f'  usuarios.criterio_pedidos_hora? {"criterio_pedidos_hora" in cols_user}')
        print(f'  hora_venda.criado_por_id? {"criado_por_id" in cols_venda}')
        print(f'  criado_por_id backfilled (linhas): {backfilled}')

        if 'criterio_pedidos_hora' not in cols_user or 'criado_por_id' not in cols_venda:
            print('\nERRO: colunas nao criadas.')
            sys.exit(1)

        with db.engine.begin() as conn:
            sem_criador = conn.execute(text(
                'SELECT COUNT(*) FROM hora_venda WHERE criado_por_id IS NULL'
            )).scalar() or 0
        print(f'  vendas ainda sem criado_por_id (legado sem match): {sem_criador}')
        print('\nMigration HORA 43 concluida com sucesso.')


if __name__ == '__main__':
    main()
