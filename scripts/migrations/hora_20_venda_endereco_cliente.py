"""Migration HORA 20: campos de endereco do cliente em hora_venda.

Adiciona 7 colunas de endereco (cep, logradouro, numero, complemento, bairro,
cidade, uf) e origem_criacao em hora_venda. Suporta novo fluxo "Pedido de
Vendas" no menu Faturamento, que cria HoraVenda manual com dados completos
para emissao de NFe via TagPlus.

Idempotente: ADD COLUMN IF NOT EXISTS em tudo. Vendas existentes (DANFE)
ficam com endereco NULL; sao retro-compativeis.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


COLUNAS_NOVAS = (
    'cep',
    'endereco_logradouro',
    'endereco_numero',
    'endereco_complemento',
    'endereco_bairro',
    'endereco_cidade',
    'endereco_uf',
    'origem_criacao',
)


def coluna_existe(tabela: str, coluna: str) -> bool:
    return bool(db.session.execute(
        db.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {'t': tabela, 'c': coluna},
    ).scalar())


def coluna_default(tabela: str, coluna: str):
    return db.session.execute(
        db.text(
            "SELECT column_default FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {'t': tabela, 'c': coluna},
    ).scalar()


def verificar(label: str):
    print(f"[{label}]")
    print("  hora_venda - novas colunas:")
    for c in COLUNAS_NOVAS:
        existe = coluna_existe('hora_venda', c)
        print(f"    {c}: {'OK' if existe else 'NAO existe'}")
    print(f"  hora_venda.origem_criacao default: "
          f"{coluna_default('hora_venda', 'origem_criacao')!r}")
    qtd_total = db.session.execute(db.text(
        'SELECT COUNT(*) FROM hora_venda'
    )).scalar()
    qtd_origem = db.session.execute(db.text(
        "SELECT COUNT(*) FROM hora_venda WHERE origem_criacao IS NOT NULL"
    )).scalar() if coluna_existe('hora_venda', 'origem_criacao') else 0
    print(f"  hora_venda total={qtd_total} com origem_criacao={qtd_origem}")


def executar_ddl():
    path = os.path.join(
        os.path.dirname(__file__), 'hora_20_venda_endereco_cliente.sql'
    )
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
