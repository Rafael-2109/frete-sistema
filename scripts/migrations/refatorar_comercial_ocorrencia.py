"""
Migration: Refatorar SELECTs da Area Comercial - Ocorrencias
=============================================================

Cria 5 tabelas lookup, 2 tabelas de juncao e 3 FK columns em ocorrencia_devolucao.
Migra dados existentes dos campos varchar para as novas tabelas.

Criado em: 21/02/2026
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


def verificar_antes(conn):
    """Verificacao pre-migration"""
    print("\n=== VERIFICACAO PRE-MIGRATION ===")

    # Verificar se tabelas lookup ja existem
    tabelas = ['ocorrencia_categoria', 'ocorrencia_subcategoria', 'ocorrencia_responsavel',
                'ocorrencia_origem', 'ocorrencia_autorizado_por',
                'ocorrencia_devolucao_categoria', 'ocorrencia_devolucao_subcategoria']

    for tabela in tabelas:
        result = conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :t)"
        ), {'t': tabela}).scalar()
        print(f"  Tabela {tabela}: {'JA EXISTE' if result else 'nao existe'}")

    # Verificar se FK columns ja existem
    for col in ['responsavel_id', 'origem_id', 'autorizado_por_id']:
        result = conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.columns "
            "WHERE table_name = 'ocorrencia_devolucao' AND column_name = :c)"
        ), {'c': col}).scalar()
        print(f"  Coluna ocorrencia_devolucao.{col}: {'JA EXISTE' if result else 'nao existe'}")

    # Contar ocorrencias existentes
    total = conn.execute(text("SELECT COUNT(*) FROM ocorrencia_devolucao")).scalar()
    print(f"  Total de ocorrencias: {total}")

    # Contar valores distintos para cada campo
    for campo in ['categoria', 'subcategoria', 'responsavel', 'origem', 'autorizado_por']:
        distintos = conn.execute(text(
            f"SELECT COUNT(DISTINCT {campo}) FROM ocorrencia_devolucao WHERE {campo} IS NOT NULL AND {campo} != ''"
        )).scalar()
        print(f"  Valores distintos em {campo}: {distintos}")


def criar_tabelas_lookup(conn):
    """Cria as 5 tabelas lookup"""
    print("\n=== CRIANDO TABELAS LOOKUP ===")

    tabelas_lookup = [
        'ocorrencia_categoria',
        'ocorrencia_subcategoria',
        'ocorrencia_responsavel',
        'ocorrencia_origem',
        'ocorrencia_autorizado_por',
    ]

    for tabela in tabelas_lookup:
        existe = conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :t)"
        ), {'t': tabela}).scalar()

        if existe:
            print(f"  {tabela}: JA EXISTE, pulando")
            continue

        conn.execute(text(f"""
            CREATE TABLE {tabela} (
                id SERIAL PRIMARY KEY,
                codigo VARCHAR(50) NOT NULL UNIQUE,
                descricao VARCHAR(255) NOT NULL,
                ativo BOOLEAN NOT NULL DEFAULT TRUE,
                criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                criado_por VARCHAR(100) DEFAULT 'migration',
                atualizado_em TIMESTAMP DEFAULT NOW(),
                atualizado_por VARCHAR(100)
            )
        """))
        print(f"  {tabela}: CRIADA")


def criar_tabelas_juncao(conn):
    """Cria as 2 tabelas de juncao (N:M)"""
    print("\n=== CRIANDO TABELAS DE JUNCAO ===")

    # ocorrencia_devolucao_categoria
    existe = conn.execute(text(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ocorrencia_devolucao_categoria')"
    )).scalar()

    if not existe:
        conn.execute(text("""
            CREATE TABLE ocorrencia_devolucao_categoria (
                id SERIAL PRIMARY KEY,
                ocorrencia_devolucao_id INTEGER NOT NULL REFERENCES ocorrencia_devolucao(id) ON DELETE CASCADE,
                categoria_id INTEGER NOT NULL REFERENCES ocorrencia_categoria(id) ON DELETE CASCADE,
                UNIQUE(ocorrencia_devolucao_id, categoria_id)
            )
        """))
        conn.execute(text(
            "CREATE INDEX idx_odc_ocorrencia ON ocorrencia_devolucao_categoria(ocorrencia_devolucao_id)"
        ))
        conn.execute(text(
            "CREATE INDEX idx_odc_categoria ON ocorrencia_devolucao_categoria(categoria_id)"
        ))
        print("  ocorrencia_devolucao_categoria: CRIADA")
    else:
        print("  ocorrencia_devolucao_categoria: JA EXISTE")

    # ocorrencia_devolucao_subcategoria
    existe = conn.execute(text(
        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'ocorrencia_devolucao_subcategoria')"
    )).scalar()

    if not existe:
        conn.execute(text("""
            CREATE TABLE ocorrencia_devolucao_subcategoria (
                id SERIAL PRIMARY KEY,
                ocorrencia_devolucao_id INTEGER NOT NULL REFERENCES ocorrencia_devolucao(id) ON DELETE CASCADE,
                subcategoria_id INTEGER NOT NULL REFERENCES ocorrencia_subcategoria(id) ON DELETE CASCADE,
                UNIQUE(ocorrencia_devolucao_id, subcategoria_id)
            )
        """))
        conn.execute(text(
            "CREATE INDEX idx_ods_ocorrencia ON ocorrencia_devolucao_subcategoria(ocorrencia_devolucao_id)"
        ))
        conn.execute(text(
            "CREATE INDEX idx_ods_subcategoria ON ocorrencia_devolucao_subcategoria(subcategoria_id)"
        ))
        print("  ocorrencia_devolucao_subcategoria: CRIADA")
    else:
        print("  ocorrencia_devolucao_subcategoria: JA EXISTE")


def adicionar_fk_columns(conn):
    """Adiciona 3 FK columns em ocorrencia_devolucao"""
    print("\n=== ADICIONANDO FK COLUMNS ===")

    fks = [
        ('responsavel_id', 'ocorrencia_responsavel'),
        ('origem_id', 'ocorrencia_origem'),
        ('autorizado_por_id', 'ocorrencia_autorizado_por'),
    ]

    for col, ref_table in fks:
        existe = conn.execute(text(
            "SELECT EXISTS (SELECT FROM information_schema.columns "
            "WHERE table_name = 'ocorrencia_devolucao' AND column_name = :c)"
        ), {'c': col}).scalar()

        if existe:
            print(f"  {col}: JA EXISTE")
            continue

        conn.execute(text(f"""
            ALTER TABLE ocorrencia_devolucao
            ADD COLUMN {col} INTEGER REFERENCES {ref_table}(id)
        """))
        conn.execute(text(f"""
            CREATE INDEX idx_ocorrencia_{col} ON ocorrencia_devolucao({col})
        """))
        print(f"  {col}: ADICIONADA com FK para {ref_table}")


def migrar_dados_categoria(conn):
    """Migra varchar categoria -> junction ocorrencia_devolucao_categoria"""
    print("\n=== MIGRANDO CATEGORIAS (varchar -> junction) ===")

    # Buscar ocorrencias com categoria preenchida
    ocorrencias = conn.execute(text(
        "SELECT id, categoria FROM ocorrencia_devolucao "
        "WHERE categoria IS NOT NULL AND TRIM(categoria) != ''"
    )).fetchall()

    migrados = 0
    for oc_id, categoria in ocorrencias:
        # Verificar se ja foi migrado
        ja_existe = conn.execute(text(
            "SELECT 1 FROM ocorrencia_devolucao_categoria odc "
            "JOIN ocorrencia_categoria oc ON odc.categoria_id = oc.id "
            "WHERE odc.ocorrencia_devolucao_id = :oid AND oc.codigo = :c"
        ), {'oid': oc_id, 'c': categoria}).first()

        if ja_existe:
            continue

        # Buscar id da categoria
        cat = conn.execute(text(
            "SELECT id FROM ocorrencia_categoria WHERE codigo = :c"
        ), {'c': categoria}).first()

        if cat:
            conn.execute(text(
                "INSERT INTO ocorrencia_devolucao_categoria (ocorrencia_devolucao_id, categoria_id) "
                "VALUES (:oid, :cid) ON CONFLICT DO NOTHING"
            ), {'oid': oc_id, 'cid': cat[0]})
            migrados += 1

    print(f"  {migrados} vinculos categoria criados")


def migrar_dados_subcategoria(conn):
    """Migra varchar subcategoria -> junction ocorrencia_devolucao_subcategoria"""
    print("\n=== MIGRANDO SUBCATEGORIAS (varchar -> junction) ===")

    ocorrencias = conn.execute(text(
        "SELECT id, subcategoria FROM ocorrencia_devolucao "
        "WHERE subcategoria IS NOT NULL AND TRIM(subcategoria) != ''"
    )).fetchall()

    migrados = 0
    for oc_id, subcategoria in ocorrencias:
        ja_existe = conn.execute(text(
            "SELECT 1 FROM ocorrencia_devolucao_subcategoria ods "
            "JOIN ocorrencia_subcategoria os ON ods.subcategoria_id = os.id "
            "WHERE ods.ocorrencia_devolucao_id = :oid AND os.codigo = :c"
        ), {'oid': oc_id, 'c': subcategoria}).first()

        if ja_existe:
            continue

        sub = conn.execute(text(
            "SELECT id FROM ocorrencia_subcategoria WHERE codigo = :c"
        ), {'c': subcategoria}).first()

        if sub:
            conn.execute(text(
                "INSERT INTO ocorrencia_devolucao_subcategoria (ocorrencia_devolucao_id, subcategoria_id) "
                "VALUES (:oid, :sid) ON CONFLICT DO NOTHING"
            ), {'oid': oc_id, 'sid': sub[0]})
            migrados += 1

    print(f"  {migrados} vinculos subcategoria criados")


def migrar_dados_fk(conn):
    """Migra varchar responsavel/origem/autorizado_por -> FK ids"""
    print("\n=== MIGRANDO FKs (varchar -> id) ===")

    # Responsavel
    migrados = conn.execute(text("""
        UPDATE ocorrencia_devolucao od
        SET responsavel_id = or2.id
        FROM ocorrencia_responsavel or2
        WHERE od.responsavel = or2.codigo
        AND od.responsavel_id IS NULL
        AND od.responsavel IS NOT NULL AND TRIM(od.responsavel) != ''
    """)).rowcount
    print(f"  responsavel_id: {migrados} atualizados")

    # Origem
    migrados = conn.execute(text("""
        UPDATE ocorrencia_devolucao od
        SET origem_id = oo.id
        FROM ocorrencia_origem oo
        WHERE od.origem = oo.codigo
        AND od.origem_id IS NULL
        AND od.origem IS NOT NULL AND TRIM(od.origem) != ''
    """)).rowcount
    print(f"  origem_id: {migrados} atualizados")

    # Autorizado por (match por descricao, case insensitive)
    migrados = conn.execute(text("""
        UPDATE ocorrencia_devolucao od
        SET autorizado_por_id = oap.id
        FROM ocorrencia_autorizado_por oap
        WHERE LOWER(TRIM(od.autorizado_por)) = LOWER(oap.descricao)
        AND od.autorizado_por_id IS NULL
        AND od.autorizado_por IS NOT NULL AND TRIM(od.autorizado_por) != ''
    """)).rowcount
    print(f"  autorizado_por_id: {migrados} atualizados")


def verificar_depois(conn):
    """Verificacao pos-migration"""
    print("\n=== VERIFICACAO POS-MIGRATION ===")

    # Contar registros em cada tabela lookup
    for tabela in ['ocorrencia_categoria', 'ocorrencia_subcategoria', 'ocorrencia_responsavel',
                    'ocorrencia_origem', 'ocorrencia_autorizado_por']:
        total = conn.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar()
        print(f"  {tabela}: {total} registros")

    # Contar registros nas tabelas de juncao
    for tabela in ['ocorrencia_devolucao_categoria', 'ocorrencia_devolucao_subcategoria']:
        total = conn.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar()
        print(f"  {tabela}: {total} vinculos")

    # Contar FKs preenchidas
    for col in ['responsavel_id', 'origem_id', 'autorizado_por_id']:
        preenchidos = conn.execute(text(
            f"SELECT COUNT(*) FROM ocorrencia_devolucao WHERE {col} IS NOT NULL"
        )).scalar()
        total = conn.execute(text("SELECT COUNT(*) FROM ocorrencia_devolucao")).scalar()
        print(f"  {col}: {preenchidos}/{total} preenchidos")

    # Verificar orfaos (varchar preenchido mas FK nula)
    for campo, fk_col in [('responsavel', 'responsavel_id'), ('origem', 'origem_id'), ('autorizado_por', 'autorizado_por_id')]:
        orfaos = conn.execute(text(
            f"SELECT COUNT(*) FROM ocorrencia_devolucao "
            f"WHERE {campo} IS NOT NULL AND TRIM({campo}) != '' AND {fk_col} IS NULL"
        )).scalar()
        if orfaos > 0:
            print(f"  AVISO: {orfaos} orfaos em {campo} (varchar sem FK correspondente)")


def main():
    app = create_app()

    with app.app_context():
        with db.engine.begin() as conn:
            verificar_antes(conn)

            # 1. Criar tabelas lookup
            criar_tabelas_lookup(conn)

            # 2. Criar tabelas de juncao
            criar_tabelas_juncao(conn)

            # 3. Adicionar FK columns
            adicionar_fk_columns(conn)

            # 4. Migrar dados existentes
            migrar_dados_categoria(conn)
            migrar_dados_subcategoria(conn)
            migrar_dados_fk(conn)

            # 5. Verificacao pos-migration
            verificar_depois(conn)

    print("\n=== MIGRATION CONCLUIDA COM SUCESSO ===")


if __name__ == '__main__':
    main()
