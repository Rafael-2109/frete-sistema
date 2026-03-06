"""
Migration: Adicionar categoria_id em ocorrencia_subcategoria e ocorrencia_responsavel
=====================================================================================

Vincula subcategorias e responsaveis como filhos de categoria.
Registros existentes sao vinculados a COMERCIAL (id=2).
Registros "Teste"/"teste" sao removidos (sem referencias).

Criado em: 06/03/2026 | Corrigido: 06/03/2026
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db

# Categoria default para registros existentes
CATEGORIA_COMERCIAL_ID = 2


def verificar_coluna_existe(conn, tabela, coluna):
    """Verifica se coluna ja existe na tabela"""
    result = conn.execute(db.text("""
        SELECT EXISTS (
            SELECT 1 FROM information_schema.columns
            WHERE table_name = :tabela AND column_name = :coluna
        )
    """), {'tabela': tabela, 'coluna': coluna})
    return result.scalar()


def verificar_indice_existe(conn, nome_indice):
    """Verifica se indice ja existe"""
    result = conn.execute(db.text("""
        SELECT EXISTS (
            SELECT 1 FROM pg_indexes
            WHERE indexname = :nome
        )
    """), {'nome': nome_indice})
    return result.scalar()


def limpar_registros_teste(conn):
    """Remove registros de teste sem referencias"""
    print("\n" + "=" * 60)
    print("PASSO 1: Limpar registros de teste")
    print("=" * 60)

    # Subcategoria 'teste' (id=1)
    r = conn.execute(db.text(
        "DELETE FROM ocorrencia_devolucao_subcategoria WHERE subcategoria_id = 1"
    ))
    print(f"  Juncoes subcategoria removidas: {r.rowcount}")

    r = conn.execute(db.text(
        "DELETE FROM ocorrencia_subcategoria WHERE id = 1 AND codigo = 'TESTE'"
    ))
    print(f"  Subcategoria 'teste' removida: {r.rowcount}")

    # Categoria 'Teste' (id=1)
    r = conn.execute(db.text(
        "DELETE FROM ocorrencia_devolucao_categoria WHERE categoria_id = 1"
    ))
    print(f"  Juncoes categoria removidas: {r.rowcount}")

    r = conn.execute(db.text(
        "DELETE FROM ocorrencia_categoria WHERE id = 1 AND codigo = 'TESTE'"
    ))
    print(f"  Categoria 'Teste' removida: {r.rowcount}")

    conn.commit()


def adicionar_categoria_id(conn, tabela, indice):
    """Adiciona coluna categoria_id: nullable -> update -> not null"""
    print(f"\n{'='*60}")
    print(f"Processando: {tabela}")
    print(f"{'='*60}")

    col_existe = verificar_coluna_existe(conn, tabela, 'categoria_id')
    idx_existe = verificar_indice_existe(conn, indice)

    print(f"  BEFORE:")
    print(f"    coluna categoria_id existe: {col_existe}")
    print(f"    indice {indice} existe: {idx_existe}")

    if col_existe:
        print(f"  -> Coluna ja existe. Pulando.")
        return

    count = conn.execute(db.text(f"SELECT COUNT(*) FROM {tabela}")).scalar() or 0
    print(f"  Registros na tabela: {count}")

    # Passo A: Adicionar como NULLABLE
    print(f"  Adicionando coluna categoria_id (nullable)...")
    conn.execute(db.text(f"""
        ALTER TABLE {tabela}
        ADD COLUMN categoria_id INTEGER REFERENCES ocorrencia_categoria(id)
    """))

    # Passo B: Vincular registros existentes a COMERCIAL
    if count > 0:
        print(f"  Vinculando {count} registros a COMERCIAL (id={CATEGORIA_COMERCIAL_ID})...")
        r = conn.execute(db.text(f"""
            UPDATE {tabela} SET categoria_id = :cat_id WHERE categoria_id IS NULL
        """), {'cat_id': CATEGORIA_COMERCIAL_ID})
        print(f"  Registros atualizados: {r.rowcount}")

    # Passo C: Aplicar NOT NULL
    print(f"  Aplicando constraint NOT NULL...")
    conn.execute(db.text(f"""
        ALTER TABLE {tabela} ALTER COLUMN categoria_id SET NOT NULL
    """))

    # Passo D: Criar indice
    print(f"  Criando indice {indice}...")
    conn.execute(db.text(f"""
        CREATE INDEX IF NOT EXISTS {indice} ON {tabela}(categoria_id)
    """))

    conn.commit()

    # AFTER: verificar
    col_existe = verificar_coluna_existe(conn, tabela, 'categoria_id')
    idx_existe = verificar_indice_existe(conn, indice)

    print(f"  AFTER:")
    print(f"    coluna categoria_id existe: {col_existe}")
    print(f"    indice {indice} existe: {idx_existe}")

    if col_existe and idx_existe:
        print(f"  OK: Migration aplicada com sucesso!")
    else:
        print(f"  ERRO: Verificacao pos-migration falhou!")


def main():
    app = create_app()

    with app.app_context():
        conn = db.engine.connect()

        # Passo 1: Limpar teste
        limpar_registros_teste(conn)

        # Passo 2-3: Adicionar categoria_id
        adicionar_categoria_id(conn, 'ocorrencia_subcategoria', 'idx_subcategoria_categoria_id')
        adicionar_categoria_id(conn, 'ocorrencia_responsavel', 'idx_responsavel_categoria_id')

        conn.close()
        print(f"\n{'='*60}")
        print("Migration concluida!")
        print(f"{'='*60}")


if __name__ == '__main__':
    main()
