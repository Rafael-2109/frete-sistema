"""Migration HORA 13: cria hora_user_permissao.

Permissoes granulares por usuario x modulo do HORA (Ver/Criar/Editar/Apagar).
Default = bloqueado. Admin sempre passa nas checagens (logica no service).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


def tabela_existe(nome: str) -> bool:
    return bool(db.session.execute(
        db.text(
            "SELECT 1 FROM information_schema.tables WHERE table_name = :t"
        ),
        {'t': nome},
    ).scalar())


def coluna_existe(tabela: str, coluna: str) -> bool:
    return bool(db.session.execute(
        db.text(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :t AND column_name = :c
            """
        ),
        {'t': tabela, 'c': coluna},
    ).scalar())


def verificar_antes():
    print("[BEFORE]")
    print(f"  hora_user_permissao existe? {tabela_existe('hora_user_permissao')}")


def executar_migration():
    sql_path = os.path.join(
        os.path.dirname(__file__),
        'hora_13_user_permissao.sql',
    )
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    db.session.execute(db.text(sql))
    db.session.commit()
    print("[OK] SQL executado")


def verificar_depois():
    assert tabela_existe('hora_user_permissao')
    for col in ('user_id', 'modulo', 'pode_ver', 'pode_criar',
                'pode_editar', 'pode_apagar', 'pode_aprovar',
                'atualizado_em', 'atualizado_por_id'):
        assert coluna_existe('hora_user_permissao', col), f'coluna {col} ausente'
    print("[AFTER] hora_user_permissao + 9 colunas presentes")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("[DONE] Migration HORA 13 concluida")
