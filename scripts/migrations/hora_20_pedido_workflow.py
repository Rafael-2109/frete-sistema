"""Migration HORA 20: workflow completo de pedido de venda.

Aplica hora_20_pedido_workflow.sql idempotentemente e reporta:
  - existencia da tabela hora_venda_auditoria
  - presenca dos novos campos em hora_venda
  - distribuicao de status apos UPDATE de migracao.
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


TABELAS = ('hora_venda_auditoria',)
COLUNAS_NOVAS = (
    ('hora_venda', 'confirmado_em'),
    ('hora_venda', 'confirmado_por'),
    ('hora_venda', 'cancelado_em'),
    ('hora_venda', 'cancelado_por'),
    ('hora_venda', 'cancelamento_motivo'),
    ('hora_venda', 'faturado_em'),
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


def distribuicao_status() -> dict:
    if not tabela_existe('hora_venda'):
        return {}
    rows = db.session.execute(db.text(
        "SELECT status, COUNT(*) FROM hora_venda GROUP BY status ORDER BY status"
    )).all()
    return {r[0]: r[1] for r in rows}


def verificar(label: str):
    print(f"[{label}]")
    for t in TABELAS:
        print(f"  tabela {t}: {'existe' if tabela_existe(t) else 'NAO existe'}")
    for tabela, coluna in COLUNAS_NOVAS:
        existe = coluna_existe(tabela, coluna)
        print(f"  coluna {tabela}.{coluna}: {'existe' if existe else 'NAO existe'}")
    print(f"  distribuicao status hora_venda: {distribuicao_status()}")


def executar_ddl():
    path = os.path.join(os.path.dirname(__file__), 'hora_20_pedido_workflow.sql')
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
