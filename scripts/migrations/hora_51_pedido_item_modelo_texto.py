"""Migration HORA 51: coluna modelo_texto_original em hora_pedido_item.

Espelha hora_nf_entrada_item.modelo_texto_original — guarda o nome do modelo
exatamente como veio na origem (XLSX/imagem) para que a retroatividade
(propagar_resolucao) corrija o modelo do item de pedido quando a pendencia e
resolvida, sem o operador editar manualmente. Idempotente.

Uso:
    python scripts/migrations/hora_51_pedido_item_modelo_texto.py
"""
import logging
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from sqlalchemy import inspect, text  # noqa: E402

from app import create_app, db  # noqa: E402

logger = logging.getLogger(__name__)

SQL_DDL = [
    "ALTER TABLE hora_pedido_item "
    "ADD COLUMN IF NOT EXISTS modelo_texto_original VARCHAR(255);",
]


def _tem_coluna(inspector, tabela: str, coluna: str) -> bool:
    return any(c['name'] == coluna for c in inspector.get_columns(tabela))


def main() -> None:
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)
        print('Estado antes:')
        print(f'  hora_pedido_item.modelo_texto_original? '
              f'{_tem_coluna(inspector, "hora_pedido_item", "modelo_texto_original")}')
        with db.engine.begin() as conn:
            for sql in SQL_DDL:
                conn.execute(text(sql))
        inspector = inspect(db.engine)
        existe = _tem_coluna(inspector, 'hora_pedido_item', 'modelo_texto_original')
        print('\nEstado depois:')
        print(f'  hora_pedido_item.modelo_texto_original? {existe}')
        if not existe:
            print('\nERRO: coluna nao criada.')
            sys.exit(1)
        print('\nMigration HORA 51 concluida com sucesso.')


if __name__ == '__main__':
    main()
