"""Migration HORA 04: expande hora_loja com campos da Receita + apelido."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


COLUNAS_NOVAS = [
    'apelido', 'razao_social', 'nome_fantasia',
    'logradouro', 'numero', 'complemento', 'bairro', 'cep',
    'telefone', 'email', 'inscricao_estadual',
    'situacao_cadastral', 'data_abertura', 'porte', 'natureza_juridica',
    'atividade_principal', 'receitaws_consultado_em',
]


def coluna_existe(col: str) -> bool:
    result = db.session.execute(
        db.text(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'hora_loja' AND column_name = :col
            """
        ),
        {'col': col},
    ).scalar()
    return result is not None


def verificar_antes():
    existentes = [c for c in COLUNAS_NOVAS if coluna_existe(c)]
    print(f"[BEFORE] colunas novas ja existentes: {len(existentes)}/{len(COLUNAS_NOVAS)}")


def executar_migration():
    sql_path = os.path.join(
        os.path.dirname(__file__),
        'hora_04_loja_campos_receita.sql',
    )
    with open(sql_path, 'r', encoding='utf-8') as f:
        sql = f.read()
    db.session.execute(db.text(sql))
    db.session.commit()
    print("[OK] SQL executado")


def verificar_depois():
    faltantes = [c for c in COLUNAS_NOVAS if not coluna_existe(c)]
    assert not faltantes, f"colunas faltando: {faltantes}"
    print(f"[AFTER] todas as {len(COLUNAS_NOVAS)} colunas novas existem")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_antes()
        executar_migration()
        verificar_depois()
        print("[DONE] Migration HORA 04 concluida")
