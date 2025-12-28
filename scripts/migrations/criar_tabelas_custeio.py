"""
Script para criar tabelas do modulo de Custeio
Executar localmente: python scripts/migrations/criar_tabelas_custeio.py
"""
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text


def criar_tabelas_custeio():
    """Cria as tabelas custo_mensal e custo_considerado"""
    app = create_app()
    with app.app_context():
        try:
            print("=" * 60)
            print("CRIANDO TABELAS DO MODULO DE CUSTEIO")
            print("=" * 60)

            # ============================================
            # TABELA: custo_mensal
            # ============================================
            print("\n[1/2] Criando tabela custo_mensal...")

            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS custo_mensal (
                    id SERIAL PRIMARY KEY,

                    -- Periodo de referencia
                    mes INTEGER NOT NULL,
                    ano INTEGER NOT NULL,

                    -- Produto
                    cod_produto VARCHAR(50) NOT NULL,
                    nome_produto VARCHAR(255),
                    tipo_produto VARCHAR(20) NOT NULL,

                    -- Custos calculados
                    custo_liquido_medio NUMERIC(15, 6),
                    custo_medio_estoque NUMERIC(15, 6),
                    ultimo_custo NUMERIC(15, 6),
                    custo_bom NUMERIC(15, 6),

                    -- Estoque inicial
                    qtd_estoque_inicial NUMERIC(15, 3) DEFAULT 0,
                    custo_estoque_inicial NUMERIC(15, 2) DEFAULT 0,

                    -- Compras do mes
                    qtd_comprada NUMERIC(15, 3) DEFAULT 0,
                    valor_compras_bruto NUMERIC(15, 2) DEFAULT 0,
                    valor_icms NUMERIC(15, 2) DEFAULT 0,
                    valor_pis NUMERIC(15, 2) DEFAULT 0,
                    valor_cofins NUMERIC(15, 2) DEFAULT 0,
                    valor_compras_liquido NUMERIC(15, 2) DEFAULT 0,

                    -- Producao
                    qtd_produzida NUMERIC(15, 3) DEFAULT 0,
                    custo_producao NUMERIC(15, 2) DEFAULT 0,

                    -- Consumo/Vendas
                    qtd_consumida NUMERIC(15, 3) DEFAULT 0,
                    qtd_vendida NUMERIC(15, 3) DEFAULT 0,

                    -- Estoque final
                    qtd_estoque_final NUMERIC(15, 3) DEFAULT 0,
                    custo_estoque_final NUMERIC(15, 2) DEFAULT 0,

                    -- Controle
                    status VARCHAR(20) DEFAULT 'ABERTO' NOT NULL,
                    fechado_em TIMESTAMP,
                    fechado_por VARCHAR(100),

                    -- Auditoria
                    criado_em TIMESTAMP DEFAULT NOW() NOT NULL,
                    atualizado_em TIMESTAMP DEFAULT NOW(),

                    -- Constraint unica
                    CONSTRAINT uq_custo_mensal_periodo_produto
                        UNIQUE (mes, ano, cod_produto)
                );
            """))

            # Indices
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_custo_mensal_periodo
                    ON custo_mensal(ano, mes);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_custo_mensal_tipo
                    ON custo_mensal(tipo_produto);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_custo_mensal_produto
                    ON custo_mensal(cod_produto);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_custo_mensal_status
                    ON custo_mensal(status);
            """))

            print("   Tabela custo_mensal criada com sucesso!")

            # ============================================
            # TABELA: custo_considerado
            # ============================================
            print("\n[2/2] Criando tabela custo_considerado...")

            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS custo_considerado (
                    id SERIAL PRIMARY KEY,

                    -- Produto (unico)
                    cod_produto VARCHAR(50) NOT NULL UNIQUE,
                    nome_produto VARCHAR(255),
                    tipo_produto VARCHAR(20) NOT NULL,

                    -- Tipos de custo disponiveis
                    custo_medio_mes NUMERIC(15, 6),
                    ultimo_custo NUMERIC(15, 6),
                    custo_medio_estoque NUMERIC(15, 6),
                    custo_bom NUMERIC(15, 6),

                    -- Custo considerado (selecionado)
                    tipo_custo_selecionado VARCHAR(20) DEFAULT 'MEDIO_MES' NOT NULL,
                    custo_considerado NUMERIC(15, 6),

                    -- Posicao de estoque
                    qtd_estoque_inicial NUMERIC(15, 3) DEFAULT 0,
                    custo_estoque_inicial NUMERIC(15, 2) DEFAULT 0,
                    qtd_comprada_periodo NUMERIC(15, 3) DEFAULT 0,
                    custo_compras_periodo NUMERIC(15, 2) DEFAULT 0,
                    qtd_estoque_final NUMERIC(15, 3) DEFAULT 0,
                    custo_estoque_final NUMERIC(15, 2) DEFAULT 0,

                    -- Referencia ao ultimo fechamento
                    ultimo_mes_fechado INTEGER,
                    ultimo_ano_fechado INTEGER,

                    -- Auditoria
                    atualizado_em TIMESTAMP DEFAULT NOW(),
                    atualizado_por VARCHAR(100)
                );
            """))

            # Indices
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_custo_considerado_tipo
                    ON custo_considerado(tipo_produto);
            """))
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_custo_considerado_produto
                    ON custo_considerado(cod_produto);
            """))

            print("   Tabela custo_considerado criada com sucesso!")

            db.session.commit()

            print("\n" + "=" * 60)
            print("TABELAS CRIADAS COM SUCESSO!")
            print("=" * 60)

            # Verificar criacao
            result = db.session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_name IN ('custo_mensal', 'custo_considerado')
                ORDER BY table_name;
            """))
            tabelas = [row[0] for row in result.fetchall()]
            print(f"\nTabelas encontradas: {tabelas}")

        except Exception as e:
            print(f"\n[ERRO] Falha ao criar tabelas: {e}")
            db.session.rollback()
            raise


def verificar_tabelas():
    """Verifica se as tabelas existem e mostra sua estrutura"""
    app = create_app()
    with app.app_context():
        try:
            print("\n" + "=" * 60)
            print("VERIFICANDO ESTRUTURA DAS TABELAS")
            print("=" * 60)

            for tabela in ['custo_mensal', 'custo_considerado']:
                print(f"\n[{tabela}]")
                result = db.session.execute(text(f"""
                    SELECT column_name, data_type, is_nullable, column_default
                    FROM information_schema.columns
                    WHERE table_name = '{tabela}'
                    ORDER BY ordinal_position;
                """))
                for row in result.fetchall():
                    print(f"   {row[0]}: {row[1]} (nullable={row[2]})")

        except Exception as e:
            print(f"[ERRO] {e}")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Criar tabelas do modulo de Custeio')
    parser.add_argument('--verificar', action='store_true', help='Apenas verifica se as tabelas existem')

    args = parser.parse_args()

    if args.verificar:
        verificar_tabelas()
    else:
        criar_tabelas_custeio()
        verificar_tabelas()
