"""
Migration: Novos campos em carvia_faturas_cliente + tabela carvia_fatura_cliente_itens
======================================================================================

Adiciona 14 novos campos em carvia_faturas_cliente (tipo_frete, dados pagador, etc.)
e cria tabela carvia_fatura_cliente_itens para itens de detalhe por CTe.

Contexto: Parser de faturas SSW calibrado para formato multi-pagina com campos adicionais.

Execucao:
    source .venv/bin/activate
    python scripts/migrations/adicionar_campos_fatura_cliente_v2.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text


NOVOS_CAMPOS = [
    ('tipo_frete', 'VARCHAR(10)'),
    ('quantidade_documentos', 'INTEGER'),
    ('valor_mercadoria', 'NUMERIC(15,2)'),
    ('valor_icms', 'NUMERIC(15,2)'),
    ('aliquota_icms', 'VARCHAR(20)'),
    ('valor_pedagio', 'NUMERIC(15,2)'),
    ('vencimento_original', 'DATE'),
    ('cancelada', 'BOOLEAN DEFAULT FALSE'),
    ('pagador_endereco', 'VARCHAR(500)'),
    ('pagador_cep', 'VARCHAR(10)'),
    ('pagador_cidade', 'VARCHAR(100)'),
    ('pagador_uf', 'VARCHAR(2)'),
    ('pagador_ie', 'VARCHAR(20)'),
    ('pagador_telefone', 'VARCHAR(30)'),
]


def verificar_antes():
    """Verifica estado antes da migration"""
    # Verificar se algum campo novo ja existe
    result = db.session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'carvia_faturas_cliente'
          AND column_name = 'tipo_frete'
    """)).fetchone()

    if result:
        print("[INFO] Campo tipo_frete ja existe em carvia_faturas_cliente.")
        campos_existentes = True
    else:
        print("[INFO] Campos novos NAO existem em carvia_faturas_cliente. Serao criados.")
        campos_existentes = False

    # Verificar tabela de itens
    result_tabela = db.session.execute(text("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_name = 'carvia_fatura_cliente_itens'
    """)).fetchone()

    if result_tabela:
        print("[INFO] Tabela carvia_fatura_cliente_itens ja existe.")
        tabela_existe = True
    else:
        print("[INFO] Tabela carvia_fatura_cliente_itens NAO existe. Sera criada.")
        tabela_existe = False

    return not (campos_existentes and tabela_existe)


def executar_migration():
    """Executa a migration"""
    # 1. Adicionar colunas em carvia_faturas_cliente
    print("[1/3] Adicionando colunas em carvia_faturas_cliente...")
    for campo, tipo in NOVOS_CAMPOS:
        db.session.execute(text(f"""
            ALTER TABLE carvia_faturas_cliente
            ADD COLUMN IF NOT EXISTS {campo} {tipo}
        """))
        print(f"  + {campo} ({tipo})")

    # 2. Criar tabela carvia_fatura_cliente_itens
    print("[2/3] Criando tabela carvia_fatura_cliente_itens...")
    db.session.execute(text("""
        CREATE TABLE IF NOT EXISTS carvia_fatura_cliente_itens (
            id SERIAL PRIMARY KEY,
            fatura_cliente_id INTEGER NOT NULL REFERENCES carvia_faturas_cliente(id) ON DELETE CASCADE,
            cte_numero VARCHAR(20),
            cte_data_emissao DATE,
            contraparte_cnpj VARCHAR(20),
            contraparte_nome VARCHAR(255),
            nf_numero VARCHAR(20),
            valor_mercadoria NUMERIC(15,2),
            peso_kg NUMERIC(15,3),
            base_calculo NUMERIC(15,2),
            icms NUMERIC(15,2),
            iss NUMERIC(15,2),
            st NUMERIC(15,2),
            frete NUMERIC(15,2),
            criado_em TIMESTAMP DEFAULT NOW()
        )
    """))

    # 3. Criar indice
    print("[3/3] Criando indice em carvia_fatura_cliente_itens...")
    db.session.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_fatura_cliente_itens_fatura
        ON carvia_fatura_cliente_itens(fatura_cliente_id)
    """))

    db.session.commit()
    print("[OK] Migration concluida com sucesso.")


def verificar_depois():
    """Verifica estado apos a migration"""
    # Verificar campos novos
    result = db.session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'carvia_faturas_cliente'
          AND column_name IN ('tipo_frete', 'cancelada', 'pagador_endereco', 'pagador_uf')
        ORDER BY column_name
    """)).fetchall()

    campos = [r[0] for r in result]
    print(f"[INFO] Campos novos encontrados em carvia_faturas_cliente: {campos}")
    if len(campos) < 4:
        print("[ERRO] Nem todos os campos foram criados!")
        return False

    # Verificar tabela de itens
    result_tabela = db.session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'carvia_fatura_cliente_itens'
        ORDER BY ordinal_position
    """)).fetchall()

    if result_tabela:
        colunas = [r[0] for r in result_tabela]
        print(f"[OK] Tabela carvia_fatura_cliente_itens criada com {len(colunas)} colunas: {colunas}")
    else:
        print("[ERRO] Tabela carvia_fatura_cliente_itens NAO foi criada!")
        return False

    return True


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        if not verificar_antes():
            print("[INFO] Migration ja aplicada. Nada a fazer.")
            sys.exit(0)

        executar_migration()
        verificar_depois()
