"""Migration HORA 25: enriquecimento de venda via GET /pedidos/{id} TagPlus.

Aplica hora_25_tagplus_pedido_enrichment.sql idempotentemente e reporta
existencia das novas colunas + tabela.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


TABELAS = ('hora_tagplus_departamento_map',)
COLUNAS_NOVAS = (
    ('hora_tagplus_token', 'scope_efetivo'),
    ('hora_tagplus_nfe_emissao', 'tagplus_pedido_id'),
    ('hora_venda', 'tagplus_pedido_id'),
    ('hora_venda', 'tagplus_pedido_payload'),
    ('hora_venda', 'tagplus_departamento'),
    ('hora_tagplus_backfill_job', 'tipo'),
)
INDICES = (
    'ix_hora_tagplus_nfe_emissao_tagplus_pedido_id',
    'ix_hora_venda_tagplus_pedido_id',
    'ix_hora_venda_tagplus_departamento',
    'ix_hora_tagplus_departamento_map_loja_id',
    'ix_hora_tagplus_backfill_job_tipo',
)


def tabela_existe(nome: str) -> bool:
    return bool(db.session.execute(
        db.text("SELECT 1 FROM information_schema.tables WHERE table_name = :t"),
        {'t': nome},
    ).scalar())


def coluna_existe(tabela: str, coluna: str) -> bool:
    return bool(db.session.execute(
        db.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :t AND column_name = :c"
        ),
        {'t': tabela, 'c': coluna},
    ).scalar())


def indice_existe(nome: str) -> bool:
    return bool(db.session.execute(
        db.text("SELECT 1 FROM pg_indexes WHERE indexname = :n"),
        {'n': nome},
    ).scalar())


def verificar(label: str):
    print(f"[{label}]")
    for t in TABELAS:
        print(f"  tabela {t}: {'existe' if tabela_existe(t) else 'NAO existe'}")
    for tabela, coluna in COLUNAS_NOVAS:
        existe = coluna_existe(tabela, coluna)
        print(f"  coluna {tabela}.{coluna}: {'existe' if existe else 'NAO existe'}")
    for idx in INDICES:
        print(f"  indice {idx}: {'existe' if indice_existe(idx) else 'NAO existe'}")


def executar_ddl():
    path = os.path.join(
        os.path.dirname(__file__), 'hora_25_tagplus_pedido_enrichment.sql'
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
