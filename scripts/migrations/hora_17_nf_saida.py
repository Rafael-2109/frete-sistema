"""Migration HORA 17: NF de Saida (venda) + divergencias.

Executa o DDL de hora_17_nf_saida.sql idempotentemente e reporta estado
antes/depois: colunas novas em hora_venda e existencia de hora_venda_divergencia.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


COLUNAS_NOVAS_HORA_VENDA = (
    'arquivo_pdf_s3_key',
    'parser_usado',
    'parseada_em',
    'cnpj_emitente',
)

TABELAS_NOVAS = (
    'hora_venda_divergencia',
)


def coluna_existe(tabela: str, coluna: str) -> bool:
    return bool(db.session.execute(
        db.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {'t': tabela, 'c': coluna},
    ).scalar())


def coluna_nullable(tabela: str, coluna: str) -> bool:
    row = db.session.execute(
        db.text(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {'t': tabela, 'c': coluna},
    ).scalar()
    return row == 'YES'


def coluna_default(tabela: str, coluna: str):
    return db.session.execute(
        db.text(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {'t': tabela, 'c': coluna},
    ).scalar()


def tabela_existe(nome: str) -> bool:
    return bool(db.session.execute(
        db.text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"),
        {'t': nome},
    ).scalar())


def verificar(label: str):
    print(f"[{label}]")
    print("  hora_venda — novas colunas:")
    for c in COLUNAS_NOVAS_HORA_VENDA:
        existe = coluna_existe('hora_venda', c)
        print(f"    {c}: {'OK' if existe else 'NAO existe'}")
    print("  hora_venda.loja_id nullable:")
    print(f"    {'SIM (OK)' if coluna_nullable('hora_venda', 'loja_id') else 'NAO (esperado SIM)'}")
    print("  hora_venda.forma_pagamento default:")
    print(f"    {coluna_default('hora_venda', 'forma_pagamento')!r}")
    print("  tabelas novas:")
    for t in TABELAS_NOVAS:
        print(f"    {t}: {'existe' if tabela_existe(t) else 'NAO existe'}")


def executar_ddl():
    path = os.path.join(os.path.dirname(__file__), 'hora_17_nf_saida.sql')
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
