"""Migration HORA 15: transferencia entre filiais + avaria em estoque.

Executa o DDL de hora_15_transferencia_e_avaria.sql idempotentemente e reporta
existencia das 5 tabelas antes/depois.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


TABELAS = (
    'hora_transferencia',
    'hora_transferencia_item',
    'hora_transferencia_auditoria',
    'hora_avaria',
    'hora_avaria_foto',
)


def tabela_existe(nome: str) -> bool:
    return bool(db.session.execute(
        db.text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"),
        {'t': nome},
    ).scalar())


def verificar(label: str):
    print(f"[{label}]")
    for t in TABELAS:
        print(f"  {t}: {'existe' if tabela_existe(t) else 'NAO existe'}")


def executar_ddl():
    path = os.path.join(os.path.dirname(__file__), 'hora_15_transferencia_e_avaria.sql')
    with open(path, encoding='utf-8') as f:
        sql = f.read()
    db.session.execute(db.text(sql))
    db.session.commit()


def main():
    app = create_app()
    with app.app_context():
        verificar('BEFORE')
        print("\n[APLICANDO DDL...]")
        executar_ddl()
        print("OK.\n")
        verificar('AFTER')


if __name__ == '__main__':
    main()
