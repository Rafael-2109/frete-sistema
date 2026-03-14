"""
Migration: Criar tabelas de CTE Complementar e Custo Entrega (CarVia)
=====================================================================

Cria 3 tabelas:
1. carvia_cte_complementares — CTe complementares emitidos por operacao
2. carvia_custos_entrega — Custos adicionais de entrega vinculados a operacao
3. carvia_custo_entrega_anexos — Anexos dos custos de entrega (comprovantes, etc.)

Dependencias: carvia_operacoes, carvia_faturas_cliente (ja devem existir)

Executar: python scripts/migrations/criar_tabelas_custo_entrega_cte_complementar.py
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from app import create_app, db
from sqlalchemy import text, inspect


def verificar_tabela_existe(inspector, tabela):
    """Verifica se uma tabela ja existe no banco"""
    return tabela in inspector.get_table_names()


def criar_tabelas():
    app = create_app()
    with app.app_context():
        inspector = inspect(db.engine)

        tabelas_antes = set(inspector.get_table_names())
        tabelas_novas = [
            'carvia_cte_complementares',
            'carvia_custos_entrega',
            'carvia_custo_entrega_anexos',
        ]

        # Verificar dependencias
        dependencias = ['carvia_operacoes', 'carvia_faturas_cliente']
        faltando = [t for t in dependencias if t not in tabelas_antes]
        if faltando:
            print(f"ERRO: Tabelas de dependencia nao encontradas: {faltando}")
            print("Execute primeiro: python scripts/migrations/criar_tabelas_carvia.py")
            return

        existentes = [t for t in tabelas_novas if t in tabelas_antes]
        if existentes:
            print(f"Tabelas ja existentes: {existentes}")
            print("Migration ja foi executada anteriormente.")
            return

        print("Criando tabelas CTE Complementar + Custo Entrega...")

        try:
            # 1. carvia_cte_complementares (referenciada por custos_entrega)
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS carvia_cte_complementares (
                    id SERIAL PRIMARY KEY,
                    numero_comp VARCHAR(20) NOT NULL,
                    operacao_id INTEGER NOT NULL REFERENCES carvia_operacoes(id),
                    fatura_cliente_id INTEGER REFERENCES carvia_faturas_cliente(id),
                    cte_numero VARCHAR(20),
                    cte_chave_acesso VARCHAR(44) UNIQUE,
                    cte_valor NUMERIC(15,2) NOT NULL,
                    cte_xml_path VARCHAR(500),
                    cte_xml_nome_arquivo VARCHAR(255),
                    cte_data_emissao DATE,
                    cnpj_cliente VARCHAR(20),
                    nome_cliente VARCHAR(255),
                    status VARCHAR(20) NOT NULL DEFAULT 'RASCUNHO',
                    observacoes TEXT,
                    criado_por VARCHAR(100) NOT NULL,
                    criado_em TIMESTAMP DEFAULT NOW(),
                    atualizado_em TIMESTAMP DEFAULT NOW()
                );
            """))
            print("  [1/3] carvia_cte_complementares criada")

            # 2. carvia_custos_entrega
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS carvia_custos_entrega (
                    id SERIAL PRIMARY KEY,
                    numero_custo VARCHAR(20) NOT NULL,
                    operacao_id INTEGER NOT NULL REFERENCES carvia_operacoes(id),
                    cte_complementar_id INTEGER REFERENCES carvia_cte_complementares(id),
                    tipo_custo VARCHAR(50) NOT NULL,
                    descricao VARCHAR(500),
                    valor NUMERIC(15,2) NOT NULL,
                    data_custo DATE NOT NULL,
                    data_vencimento DATE,
                    fornecedor_nome VARCHAR(255),
                    fornecedor_cnpj VARCHAR(20),
                    status VARCHAR(20) NOT NULL DEFAULT 'PENDENTE',
                    pago_por VARCHAR(100),
                    pago_em TIMESTAMP,
                    total_conciliado NUMERIC(15,2) NOT NULL DEFAULT 0,
                    conciliado BOOLEAN NOT NULL DEFAULT FALSE,
                    observacoes TEXT,
                    criado_por VARCHAR(100) NOT NULL,
                    criado_em TIMESTAMP DEFAULT NOW(),
                    atualizado_em TIMESTAMP DEFAULT NOW()
                );
            """))
            print("  [2/3] carvia_custos_entrega criada")

            # 3. carvia_custo_entrega_anexos
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS carvia_custo_entrega_anexos (
                    id SERIAL PRIMARY KEY,
                    custo_entrega_id INTEGER NOT NULL REFERENCES carvia_custos_entrega(id) ON DELETE CASCADE,
                    nome_original VARCHAR(255) NOT NULL,
                    nome_arquivo VARCHAR(255) NOT NULL,
                    caminho_s3 VARCHAR(500) NOT NULL,
                    tamanho_bytes INTEGER,
                    content_type VARCHAR(100),
                    descricao TEXT,
                    criado_em TIMESTAMP NOT NULL DEFAULT NOW(),
                    criado_por VARCHAR(100) NOT NULL,
                    ativo BOOLEAN NOT NULL DEFAULT TRUE
                );
            """))
            print("  [3/3] carvia_custo_entrega_anexos criada")

            # Indices
            print("\nCriando indices...")
            indices = [
                # carvia_cte_complementares
                "CREATE INDEX IF NOT EXISTS ix_carvia_cte_comp_numero_comp ON carvia_cte_complementares(numero_comp);",
                "CREATE INDEX IF NOT EXISTS ix_carvia_cte_comp_operacao_id ON carvia_cte_complementares(operacao_id);",
                "CREATE INDEX IF NOT EXISTS ix_carvia_cte_comp_fatura_cliente_id ON carvia_cte_complementares(fatura_cliente_id);",
                "CREATE INDEX IF NOT EXISTS ix_carvia_cte_comp_cte_numero ON carvia_cte_complementares(cte_numero);",
                "CREATE INDEX IF NOT EXISTS ix_carvia_cte_comp_cnpj_cliente ON carvia_cte_complementares(cnpj_cliente);",
                "CREATE INDEX IF NOT EXISTS ix_carvia_cte_comp_status ON carvia_cte_complementares(status);",
                # carvia_custos_entrega
                "CREATE INDEX IF NOT EXISTS ix_carvia_custo_entrega_numero_custo ON carvia_custos_entrega(numero_custo);",
                "CREATE INDEX IF NOT EXISTS ix_carvia_custo_entrega_operacao_id ON carvia_custos_entrega(operacao_id);",
                "CREATE INDEX IF NOT EXISTS ix_carvia_custo_entrega_cte_comp_id ON carvia_custos_entrega(cte_complementar_id);",
                "CREATE INDEX IF NOT EXISTS ix_carvia_custo_entrega_tipo_custo ON carvia_custos_entrega(tipo_custo);",
                "CREATE INDEX IF NOT EXISTS ix_carvia_custo_entrega_status ON carvia_custos_entrega(status);",
                # carvia_custo_entrega_anexos
                "CREATE INDEX IF NOT EXISTS ix_carvia_custo_entrega_anexo_custo_id ON carvia_custo_entrega_anexos(custo_entrega_id);",
                "CREATE INDEX IF NOT EXISTS ix_carvia_custo_entrega_anexo_ativo ON carvia_custo_entrega_anexos(ativo);",
            ]
            for idx_sql in indices:
                db.session.execute(text(idx_sql))
            print(f"  {len(indices)} indices criados")

            db.session.commit()

            # Verificacao
            inspector = inspect(db.engine)
            tabelas_depois = set(inspector.get_table_names())
            novas = tabelas_depois - tabelas_antes
            print(f"\nTabelas criadas: {sorted(novas)}")
            print("Migration concluida com sucesso!")

        except Exception as e:
            db.session.rollback()
            print(f"\nERRO na migration: {e}")
            raise


if __name__ == '__main__':
    criar_tabelas()
