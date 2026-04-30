"""Migration HORA 23: Emprestimo de moto entre nossa loja e loja externa."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402

SQL_PATH = os.path.join(os.path.dirname(__file__), 'hora_23_emprestimo_moto.sql')


def tabela_existe(nome: str) -> bool:
    return bool(db.session.execute(
        db.text("SELECT 1 FROM information_schema.tables WHERE table_name=:n"),
        {'n': nome},
    ).scalar())


def main() -> None:
    app = create_app()
    with app.app_context():
        antes = tabela_existe('hora_emprestimo_moto')
        print(f'ANTES: hora_emprestimo_moto existe = {antes}')

        with open(SQL_PATH, 'r', encoding='utf-8') as f:
            sql = f.read()
        db.session.execute(db.text(sql))
        db.session.commit()

        depois = tabela_existe('hora_emprestimo_moto')
        print(f'DEPOIS: hora_emprestimo_moto existe = {depois}')
        if depois:
            count = db.session.execute(
                db.text('SELECT COUNT(*) FROM hora_emprestimo_moto')
            ).scalar()
            print(f'Linhas na tabela: {count}')
        if not depois:
            sys.exit(1)


if __name__ == '__main__':
    main()
