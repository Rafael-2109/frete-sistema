"""Migration: CTe Complementar.motivo + NF.modalidade_frete + drop FaturaCliente.tipo_frete.

Consolida 3 mudancas que juntas removem assuncao FOB/CIF como "tomador substituto":
- BACKUP + BACKFILL: preserva tipo_frete historico + popula cte_tomador das operacoes
  antes do drop (FOB→DESTINATARIO, CIF→REMETENTE — semantica correta de incoterm).
- Adiciona motivo generico no CTe Complementar (extraido de ObsCont xTexto iniciando com "MOTIVO:")
- Adiciona modalidade_frete na NF (campo SEFAZ <transp>/<modFrete>)
- Remove tipo_frete da FaturaCliente (obsoleto; SOT do tomador e o CTe)

Idempotente (IF NOT EXISTS / IF EXISTS / verificacoes por existencia).
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db  # noqa: E402


def _coluna_existe(tabela: str, coluna: str) -> bool:
    row = db.session.execute(db.text(
        """
        SELECT 1 FROM information_schema.columns
         WHERE table_name = :t AND column_name = :c
        """
    ), {'t': tabela, 'c': coluna}).fetchone()
    return row is not None


def _tabela_existe(tabela: str) -> bool:
    row = db.session.execute(db.text(
        """
        SELECT 1 FROM information_schema.tables
         WHERE table_name = :t
        """
    ), {'t': tabela}).fetchone()
    return row is not None


def verificar_antes():
    print('=' * 70)
    print('[BEFORE]')
    print(f"  carvia_cte_complementares.motivo existe?            {_coluna_existe('carvia_cte_complementares', 'motivo')}")
    print(f"  carvia_nfs.modalidade_frete existe?                 {_coluna_existe('carvia_nfs', 'modalidade_frete')}")
    print(f"  carvia_faturas_cliente.tipo_frete existe?           {_coluna_existe('carvia_faturas_cliente', 'tipo_frete')}")
    print(f"  carvia_faturas_cliente_tipo_frete_backup existe?    {_tabela_existe('carvia_faturas_cliente_tipo_frete_backup')}")


def backup_e_backfill():
    """Preserva tipo_frete + popula cte_tomador das operacoes antes do drop.

    Regra R19: FOB=DESTINATARIO, CIF=REMETENTE. So atualiza cte_tomador NULL
    (nao sobrescreve SOT do XML).
    """
    if not _coluna_existe('carvia_faturas_cliente', 'tipo_frete'):
        print("  [=] tipo_frete ja removido — backup/backfill skip")
        return

    # Backup schema
    db.session.execute(db.text("""
        CREATE TABLE IF NOT EXISTS carvia_faturas_cliente_tipo_frete_backup (
            id INTEGER,
            numero_fatura VARCHAR(50),
            cnpj_cliente VARCHAR(20),
            tipo_frete VARCHAR(10),
            status VARCHAR(20),
            backup_em TIMESTAMP
        )
    """))

    # Backup dados (so novos — idempotente)
    result = db.session.execute(db.text("""
        INSERT INTO carvia_faturas_cliente_tipo_frete_backup
            (id, numero_fatura, cnpj_cliente, tipo_frete, status, backup_em)
        SELECT f.id, f.numero_fatura, f.cnpj_cliente, f.tipo_frete, f.status, NOW()
          FROM carvia_faturas_cliente f
         WHERE f.tipo_frete IS NOT NULL
           AND NOT EXISTS (
               SELECT 1 FROM carvia_faturas_cliente_tipo_frete_backup b
                WHERE b.id = f.id
           )
    """))
    print(f"  [BACKUP] {result.rowcount} faturas com tipo_frete salvas em backup")

    # Backfill cte_tomador (so operacoes com cte_tomador NULL)
    result = db.session.execute(db.text("""
        UPDATE carvia_operacoes op
           SET cte_tomador = CASE f.tipo_frete
                                 WHEN 'FOB' THEN 'DESTINATARIO'
                                 WHEN 'CIF' THEN 'REMETENTE'
                             END
          FROM carvia_faturas_cliente f
         WHERE op.fatura_cliente_id = f.id
           AND op.cte_tomador IS NULL
           AND f.tipo_frete IN ('FOB', 'CIF')
    """))
    print(f"  [BACKFILL] cte_tomador populado em {result.rowcount} operacoes")


def executar():
    # 0. Backup + Backfill (so se tipo_frete ainda existe)
    backup_e_backfill()

    # 1. CTe Complementar motivo
    if not _coluna_existe('carvia_cte_complementares', 'motivo'):
        db.session.execute(db.text(
            "ALTER TABLE carvia_cte_complementares ADD COLUMN motivo VARCHAR(500)"
        ))
        print("  [+] carvia_cte_complementares.motivo adicionado")
    else:
        print("  [=] carvia_cte_complementares.motivo ja existe — skip")

    # 2. NF modalidade_frete
    if not _coluna_existe('carvia_nfs', 'modalidade_frete'):
        db.session.execute(db.text(
            "ALTER TABLE carvia_nfs ADD COLUMN modalidade_frete VARCHAR(1)"
        ))
        print("  [+] carvia_nfs.modalidade_frete adicionado")
    else:
        print("  [=] carvia_nfs.modalidade_frete ja existe — skip")

    # 3. Fatura Cliente drop tipo_frete (apos backup + backfill)
    if _coluna_existe('carvia_faturas_cliente', 'tipo_frete'):
        db.session.execute(db.text(
            "ALTER TABLE carvia_faturas_cliente DROP COLUMN tipo_frete"
        ))
        print("  [-] carvia_faturas_cliente.tipo_frete removido")
    else:
        print("  [=] carvia_faturas_cliente.tipo_frete ja removido — skip")

    db.session.commit()


def verificar_depois():
    print('-' * 70)
    print('[AFTER]')
    print(f"  carvia_cte_complementares.motivo existe?            {_coluna_existe('carvia_cte_complementares', 'motivo')}")
    print(f"  carvia_nfs.modalidade_frete existe?                 {_coluna_existe('carvia_nfs', 'modalidade_frete')}")
    print(f"  carvia_faturas_cliente.tipo_frete existe?           {_coluna_existe('carvia_faturas_cliente', 'tipo_frete')}")
    print(f"  carvia_faturas_cliente_tipo_frete_backup existe?    {_tabela_existe('carvia_faturas_cliente_tipo_frete_backup')}")

    if _tabela_existe('carvia_faturas_cliente_tipo_frete_backup'):
        cnt = db.session.execute(db.text(
            "SELECT COUNT(*) FROM carvia_faturas_cliente_tipo_frete_backup"
        )).scalar()
        print(f"  [BACKUP] {cnt} faturas preservadas em backup")

    op_tomador = db.session.execute(db.text(
        "SELECT COUNT(*) FROM carvia_operacoes WHERE cte_tomador IS NOT NULL"
    )).scalar()
    print(f"  [OPERACOES] {op_tomador} operacoes com cte_tomador populado")

    assert _coluna_existe('carvia_cte_complementares', 'motivo'), 'motivo nao foi criado'
    assert _coluna_existe('carvia_nfs', 'modalidade_frete'), 'modalidade_frete nao foi criado'
    assert not _coluna_existe('carvia_faturas_cliente', 'tipo_frete'), 'tipo_frete ainda existe'
    print("[OK] Todas as mudancas aplicadas com sucesso")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        verificar_antes()
        executar()
        verificar_depois()
