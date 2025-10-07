#!/usr/bin/env python3
"""
Migration: Refatoração Financeira MotoCHEFE
Para: Ambiente Local (SQLite ou PostgreSQL)
Data: 2025-01-10

Uso:
    python app/motochefe/scripts/migration_refatoracao_financeira_local.py
"""

import sys
import os

# Adicionar caminho do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from sqlalchemy import text, inspect
from datetime import date
from decimal import Decimal

app = create_app()


def executar_migration():
    """Executa migration completa"""
    with app.app_context():
        print("=" * 80)
        print("MIGRATION: Refatoração Financeira MotoCHEFE")
        print("=" * 80)
        print()

        # Detectar tipo de banco
        engine_name = db.engine.name
        print(f"📊 Banco de dados detectado: {engine_name.upper()}")
        print()

        try:
            # 1. Alterar empresa_venda_moto
            print("1. Alterando tabela empresa_venda_moto...")
            alterar_empresa_venda_moto(engine_name)
            print("   ✅ Concluído")

            # 2. Alterar titulo_financeiro
            print("2. Alterando tabela titulo_financeiro...")
            alterar_titulo_financeiro(engine_name)
            print("   ✅ Concluído")

            # 3. Alterar comissao_vendedor
            print("3. Alterando tabela comissao_vendedor...")
            alterar_comissao_vendedor()
            print("   ✅ Concluído")

            # 4. Criar movimentacao_financeira
            print("4. Criando tabela movimentacao_financeira...")
            criar_movimentacao_financeira(engine_name)
            print("   ✅ Concluído")

            # 5. Criar titulo_a_pagar
            print("5. Criando tabela titulo_a_pagar...")
            criar_titulo_a_pagar(engine_name)
            print("   ✅ Concluído")

            # 6. Popular MargemSogima
            print("6. Criando empresa MargemSogima...")
            criar_margem_sogima()
            print("   ✅ Concluído")

            print()
            print("=" * 80)
            print("✅ MIGRATION EXECUTADA COM SUCESSO!")
            print("=" * 80)

        except Exception as e:
            db.session.rollback()
            print()
            print("=" * 80)
            print(f"❌ ERRO NA MIGRATION: {str(e)}")
            print("=" * 80)
            import traceback
            traceback.print_exc()
            raise


def coluna_existe(tabela, coluna):
    """Verifica se uma coluna existe na tabela"""
    inspector = inspect(db.engine)
    colunas = [col['name'] for col in inspector.get_columns(tabela)]
    return coluna in colunas


def alterar_empresa_venda_moto(engine_name):
    """Altera tabela empresa_venda_moto"""

    # IMPORTANTE: Alterar cnpj_empresa para nullable (para MargemSogima)
    if engine_name == 'postgresql':
        try:
            db.session.execute(text("""
                ALTER TABLE empresa_venda_moto ALTER COLUMN cnpj_empresa DROP NOT NULL;
            """))
            db.session.commit()
            print("   ✓ Campo 'cnpj_empresa' alterado para NULLABLE")
        except Exception as e:
            db.session.rollback()
            print(f"   ⚠️  cnpj_empresa: {e}")
    else:
        # SQLite não suporta ALTER COLUMN para mudar nullable
        # Por isso, cnpj_empresa continuará NOT NULL no schema SQLite,
        # mas MargemSogima será criada com cnpj_empresa vazio '' ao invés de NULL
        print("   ⚠️  SQLite: cnpj_empresa permanece NOT NULL (limitação)")

    # Adicionar novos campos
    colunas = [
        ('baixa_compra_auto', 'BOOLEAN DEFAULT 0' if engine_name == 'sqlite' else 'BOOLEAN DEFAULT FALSE'),
        ('saldo', 'DECIMAL(15, 2) DEFAULT 0'),
        ('tipo_conta', 'VARCHAR(20)'),
    ]

    for nome, tipo in colunas:
        if not coluna_existe('empresa_venda_moto', nome):
            try:
                db.session.execute(text(f"""
                    ALTER TABLE empresa_venda_moto ADD COLUMN {nome} {tipo};
                """))
                db.session.commit()
                print(f"   ✓ Coluna '{nome}' adicionada")
            except Exception as e:
                db.session.rollback()
                print(f"   ⚠️  Coluna '{nome}' já existe ou erro: {e}")
        else:
            print(f"   ⚠️  Coluna '{nome}' já existe")


def alterar_titulo_financeiro(engine_name):
    """Altera tabela titulo_financeiro"""
    colunas = [
        ("numero_chassi", "VARCHAR(30)"),
        ("tipo_titulo", "VARCHAR(20)"),
        ("ordem_pagamento", "INTEGER"),
        ("empresa_recebedora_id", "INTEGER"),
        ("valor_original", "DECIMAL(15, 2)"),
        ("valor_saldo", "DECIMAL(15, 2)"),
        ("valor_pago_total", "DECIMAL(15, 2) DEFAULT 0"),
        ("data_emissao", "DATE"),
        ("data_ultimo_pagamento", "DATE"),
        ("titulo_pai_id", "INTEGER"),
        ("eh_titulo_dividido", "BOOLEAN DEFAULT 0" if engine_name == 'sqlite' else "BOOLEAN DEFAULT FALSE"),
        ("historico_divisao", "TEXT"),
        ("criado_por", "VARCHAR(100)"),
    ]

    for nome, tipo in colunas:
        if not coluna_existe('titulo_financeiro', nome):
            try:
                db.session.execute(text(f"""
                    ALTER TABLE titulo_financeiro ADD COLUMN {nome} {tipo};
                """))
                db.session.commit()
                print(f"   ✓ Coluna '{nome}' adicionada")
            except Exception as e:
                db.session.rollback()
                print(f"   ⚠️  Coluna '{nome}': {e}")
        else:
            print(f"   ⚠️  Coluna '{nome}' já existe")

    # Migrar dados antigos (somente se tipo_titulo for NULL)
    if engine_name == 'sqlite':
        # SQLite: usar date()
        db.session.execute(text("""
            UPDATE titulo_financeiro SET
                tipo_titulo = 'VENDA',
                ordem_pagamento = 4,
                valor_original = valor_parcela,
                valor_saldo = valor_parcela - COALESCE(valor_recebido, 0),
                valor_pago_total = COALESCE(valor_recebido, 0),
                data_emissao = date(criado_em)
            WHERE tipo_titulo IS NULL;
        """))
    else:
        # PostgreSQL: usar CAST ou ::date
        db.session.execute(text("""
            UPDATE titulo_financeiro SET
                tipo_titulo = 'VENDA',
                ordem_pagamento = 4,
                valor_original = valor_parcela,
                valor_saldo = valor_parcela - COALESCE(valor_recebido, 0),
                valor_pago_total = COALESCE(valor_recebido, 0),
                data_emissao = criado_em::date
            WHERE tipo_titulo IS NULL;
        """))
    db.session.commit()
    print("   ✓ Dados antigos migrados")


def alterar_comissao_vendedor():
    """Altera tabela comissao_vendedor"""
    if not coluna_existe('comissao_vendedor', 'numero_chassi'):
        try:
            db.session.execute(text("""
                ALTER TABLE comissao_vendedor ADD COLUMN numero_chassi VARCHAR(30);
            """))
            db.session.commit()
            print("   ✓ Coluna 'numero_chassi' adicionada")
        except Exception as e:
            db.session.rollback()
            print(f"   ⚠️  Erro: {e}")
    else:
        print("   ⚠️  Coluna 'numero_chassi' já existe")


def criar_movimentacao_financeira(engine_name):
    """Cria tabela movimentacao_financeira"""
    # Verificar se tabela já existe
    inspector = inspect(db.engine)
    if 'movimentacao_financeira' in inspector.get_table_names():
        print("   ⚠️  Tabela 'movimentacao_financeira' já existe")
        return

    if engine_name == 'sqlite':
        sql = """
        CREATE TABLE movimentacao_financeira (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo VARCHAR(20) NOT NULL,
            categoria VARCHAR(50) NOT NULL,
            valor DECIMAL(15, 2) NOT NULL,
            data_movimentacao DATE NOT NULL,

            empresa_origem_id INTEGER,
            origem_tipo VARCHAR(50),
            origem_identificacao VARCHAR(255),

            empresa_destino_id INTEGER,
            destino_tipo VARCHAR(50),
            destino_identificacao VARCHAR(255),

            pedido_id INTEGER,
            numero_chassi VARCHAR(30),
            titulo_financeiro_id INTEGER,
            comissao_vendedor_id INTEGER,
            embarque_moto_id INTEGER,
            despesa_mensal_id INTEGER,

            descricao TEXT,
            numero_nf VARCHAR(20),
            numero_documento VARCHAR(50),
            observacoes TEXT,

            eh_baixa_automatica BOOLEAN DEFAULT 0,
            movimentacao_origem_id INTEGER,

            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            criado_por VARCHAR(100),

            FOREIGN KEY (empresa_origem_id) REFERENCES empresa_venda_moto(id),
            FOREIGN KEY (empresa_destino_id) REFERENCES empresa_venda_moto(id),
            FOREIGN KEY (pedido_id) REFERENCES pedido_venda_moto(id),
            FOREIGN KEY (numero_chassi) REFERENCES moto(numero_chassi),
            FOREIGN KEY (titulo_financeiro_id) REFERENCES titulo_financeiro(id),
            FOREIGN KEY (comissao_vendedor_id) REFERENCES comissao_vendedor(id),
            FOREIGN KEY (embarque_moto_id) REFERENCES embarque_moto(id),
            FOREIGN KEY (despesa_mensal_id) REFERENCES despesa_mensal(id),
            FOREIGN KEY (movimentacao_origem_id) REFERENCES movimentacao_financeira(id)
        );
        """
    else:
        # PostgreSQL
        sql = """
        CREATE TABLE movimentacao_financeira (
            id SERIAL PRIMARY KEY,
            tipo VARCHAR(20) NOT NULL,
            categoria VARCHAR(50) NOT NULL,
            valor DECIMAL(15, 2) NOT NULL,
            data_movimentacao DATE NOT NULL,

            empresa_origem_id INTEGER,
            origem_tipo VARCHAR(50),
            origem_identificacao VARCHAR(255),

            empresa_destino_id INTEGER,
            destino_tipo VARCHAR(50),
            destino_identificacao VARCHAR(255),

            pedido_id INTEGER,
            numero_chassi VARCHAR(30),
            titulo_financeiro_id INTEGER,
            comissao_vendedor_id INTEGER,
            embarque_moto_id INTEGER,
            despesa_mensal_id INTEGER,

            descricao TEXT,
            numero_nf VARCHAR(20),
            numero_documento VARCHAR(50),
            observacoes TEXT,

            eh_baixa_automatica BOOLEAN DEFAULT FALSE,
            movimentacao_origem_id INTEGER,

            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            criado_por VARCHAR(100),

            FOREIGN KEY (empresa_origem_id) REFERENCES empresa_venda_moto(id),
            FOREIGN KEY (empresa_destino_id) REFERENCES empresa_venda_moto(id),
            FOREIGN KEY (pedido_id) REFERENCES pedido_venda_moto(id),
            FOREIGN KEY (numero_chassi) REFERENCES moto(numero_chassi),
            FOREIGN KEY (titulo_financeiro_id) REFERENCES titulo_financeiro(id),
            FOREIGN KEY (comissao_vendedor_id) REFERENCES comissao_vendedor(id),
            FOREIGN KEY (embarque_moto_id) REFERENCES embarque_moto(id),
            FOREIGN KEY (despesa_mensal_id) REFERENCES despesa_mensal(id),
            FOREIGN KEY (movimentacao_origem_id) REFERENCES movimentacao_financeira(id)
        );
        """

    db.session.execute(text(sql))
    db.session.commit()
    print("   ✓ Tabela criada")

    # Criar índices
    indices = [
        "CREATE INDEX IF NOT EXISTS idx_movfin_tipo ON movimentacao_financeira(tipo);",
        "CREATE INDEX IF NOT EXISTS idx_movfin_categoria ON movimentacao_financeira(categoria);",
        "CREATE INDEX IF NOT EXISTS idx_movfin_data ON movimentacao_financeira(data_movimentacao);",
        "CREATE INDEX IF NOT EXISTS idx_movfin_emp_origem ON movimentacao_financeira(empresa_origem_id);",
        "CREATE INDEX IF NOT EXISTS idx_movfin_emp_destino ON movimentacao_financeira(empresa_destino_id);",
    ]

    for idx in indices:
        db.session.execute(text(idx))
    db.session.commit()
    print("   ✓ Índices criados")


def criar_titulo_a_pagar(engine_name):
    """Cria tabela titulo_a_pagar"""
    # Verificar se tabela já existe
    inspector = inspect(db.engine)
    if 'titulo_a_pagar' in inspector.get_table_names():
        print("   ⚠️  Tabela 'titulo_a_pagar' já existe")
        return

    if engine_name == 'sqlite':
        sql = """
        CREATE TABLE titulo_a_pagar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo VARCHAR(20) NOT NULL,

            titulo_financeiro_id INTEGER NOT NULL,
            pedido_id INTEGER NOT NULL,
            numero_chassi VARCHAR(30) NOT NULL,

            empresa_destino_id INTEGER,
            fornecedor_montagem VARCHAR(100),

            valor_original DECIMAL(15, 2) NOT NULL,
            valor_pago DECIMAL(15, 2) DEFAULT 0,
            valor_saldo DECIMAL(15, 2) NOT NULL,

            data_criacao DATE NOT NULL,
            data_liberacao DATE,
            data_vencimento DATE,
            data_pagamento DATE,

            status VARCHAR(20) DEFAULT 'PENDENTE' NOT NULL,
            observacoes TEXT,

            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            criado_por VARCHAR(100) DEFAULT 'SISTEMA',
            atualizado_em TIMESTAMP,
            atualizado_por VARCHAR(100),

            FOREIGN KEY (titulo_financeiro_id) REFERENCES titulo_financeiro(id),
            FOREIGN KEY (pedido_id) REFERENCES pedido_venda_moto(id),
            FOREIGN KEY (numero_chassi) REFERENCES moto(numero_chassi),
            FOREIGN KEY (empresa_destino_id) REFERENCES empresa_venda_moto(id)
        );
        """
    else:
        # PostgreSQL
        sql = """
        CREATE TABLE titulo_a_pagar (
            id SERIAL PRIMARY KEY,
            tipo VARCHAR(20) NOT NULL,

            titulo_financeiro_id INTEGER NOT NULL,
            pedido_id INTEGER NOT NULL,
            numero_chassi VARCHAR(30) NOT NULL,

            empresa_destino_id INTEGER,
            fornecedor_montagem VARCHAR(100),

            valor_original DECIMAL(15, 2) NOT NULL,
            valor_pago DECIMAL(15, 2) DEFAULT 0,
            valor_saldo DECIMAL(15, 2) NOT NULL,

            data_criacao DATE NOT NULL,
            data_liberacao DATE,
            data_vencimento DATE,
            data_pagamento DATE,

            status VARCHAR(20) DEFAULT 'PENDENTE' NOT NULL,
            observacoes TEXT,

            criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
            criado_por VARCHAR(100) DEFAULT 'SISTEMA',
            atualizado_em TIMESTAMP,
            atualizado_por VARCHAR(100),

            FOREIGN KEY (titulo_financeiro_id) REFERENCES titulo_financeiro(id),
            FOREIGN KEY (pedido_id) REFERENCES pedido_venda_moto(id),
            FOREIGN KEY (numero_chassi) REFERENCES moto(numero_chassi),
            FOREIGN KEY (empresa_destino_id) REFERENCES empresa_venda_moto(id)
        );
        """

    db.session.execute(text(sql))
    db.session.commit()
    print("   ✓ Tabela criada")

    # Criar índices
    indices = [
        "CREATE INDEX IF NOT EXISTS idx_titpagar_tipo ON titulo_a_pagar(tipo);",
        "CREATE INDEX IF NOT EXISTS idx_titpagar_status ON titulo_a_pagar(status);",
        "CREATE INDEX IF NOT EXISTS idx_titpagar_titulo ON titulo_a_pagar(titulo_financeiro_id);",
    ]

    for idx in indices:
        db.session.execute(text(idx))
    db.session.commit()
    print("   ✓ Índices criados")


def criar_margem_sogima():
    """Cria empresa MargemSogima se não existir"""
    from app.motochefe.services.empresa_service import garantir_margem_sogima
    margem = garantir_margem_sogima()
    print(f"   📌 MargemSogima criada/verificada: ID {margem.id}")


if __name__ == '__main__':
    print()
    resposta = input("⚠️  Executar migration? Esta operação altera o banco de dados. (s/N): ")

    if resposta.lower() == 's':
        executar_migration()
    else:
        print("❌ Migration cancelada pelo usuário")
