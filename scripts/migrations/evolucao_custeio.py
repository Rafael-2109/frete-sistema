#!/usr/bin/env python3
"""
MIGRACAO: Sistema de Custeio - Evolucao Completa
Data: 2025-12-26

Executa:
- Adiciona versionamento ao CustoConsiderado
- Cria tabelas CustoFrete e ParametroCusteio
- Adiciona campos de snapshot/margem na CarteiraPrincipal

Uso:
    cd /home/rafaelnascimento/projetos/frete_sistema
    source .venv/bin/activate
    python scripts/migrations/evolucao_custeio.py
"""

import sys
import os

# Adicionar raiz do projeto ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def executar_migracao():
    """Executa migracao completa do sistema de custeio"""
    app = create_app()

    with app.app_context():
        try:
            logger.info("=" * 70)
            logger.info("MIGRACAO: Sistema de Custeio - Evolucao Completa")
            logger.info("=" * 70)

            # ============================================================
            # PARTE 1: Versionamento em custo_considerado
            # ============================================================
            logger.info("\n[1/4] Adicionando campos de versionamento em custo_considerado...")

            sql_versionamento = """
                ALTER TABLE custo_considerado ADD COLUMN IF NOT EXISTS versao INTEGER DEFAULT 1;
                ALTER TABLE custo_considerado ADD COLUMN IF NOT EXISTS custo_atual BOOLEAN DEFAULT TRUE;
                ALTER TABLE custo_considerado ADD COLUMN IF NOT EXISTS vigencia_inicio TIMESTAMP DEFAULT NOW();
                ALTER TABLE custo_considerado ADD COLUMN IF NOT EXISTS vigencia_fim TIMESTAMP NULL;
                ALTER TABLE custo_considerado ADD COLUMN IF NOT EXISTS custo_producao NUMERIC(15,6) NULL;
                ALTER TABLE custo_considerado ADD COLUMN IF NOT EXISTS motivo_alteracao TEXT NULL;
            """
            db.session.execute(text(sql_versionamento))
            logger.info("  -> Campos de versionamento adicionados")

            # Atualizar registros existentes
            sql_update = """
                UPDATE custo_considerado
                SET versao = 1,
                    custo_atual = TRUE,
                    vigencia_inicio = COALESCE(atualizado_em, NOW())
                WHERE versao IS NULL;
            """
            result = db.session.execute(text(sql_update))
            logger.info(f"  -> {result.rowcount} registros atualizados com versao=1")

            # Remover constraint antiga (se existir)
            try:
                db.session.execute(text("""
                    ALTER TABLE custo_considerado
                    DROP CONSTRAINT IF EXISTS custo_considerado_cod_produto_key;
                """))
                logger.info("  -> Constraint antiga removida (se existia)")
            except Exception as e:
                logger.warning(f"  -> Constraint nao existia ou ja foi removida: {e}")

            # Criar nova constraint e indice
            try:
                db.session.execute(text("""
                    CREATE UNIQUE INDEX IF NOT EXISTS uq_custo_considerado_versao
                    ON custo_considerado(cod_produto, versao);
                """))
                db.session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_custo_considerado_atual
                    ON custo_considerado(cod_produto, custo_atual);
                """))
                logger.info("  -> Indices criados")
            except Exception as e:
                logger.warning(f"  -> Indices ja existem: {e}")

            db.session.commit()
            logger.info("  -> PARTE 1 CONCLUIDA")

            # ============================================================
            # PARTE 2: Tabela custo_frete
            # ============================================================
            logger.info("\n[2/4] Criando tabela custo_frete...")

            sql_custo_frete = """
                CREATE TABLE IF NOT EXISTS custo_frete (
                    id SERIAL PRIMARY KEY,
                    incoterm VARCHAR(20) NOT NULL,
                    cod_uf VARCHAR(2) NOT NULL,
                    percentual_frete NUMERIC(5,2) NOT NULL,
                    vigencia_inicio DATE NOT NULL,
                    vigencia_fim DATE NULL,
                    criado_em TIMESTAMP DEFAULT NOW(),
                    criado_por VARCHAR(100),
                    UNIQUE(incoterm, cod_uf, vigencia_inicio)
                );

                CREATE INDEX IF NOT EXISTS idx_custo_frete_vigencia
                ON custo_frete(incoterm, cod_uf, vigencia_inicio);
            """
            db.session.execute(text(sql_custo_frete))
            db.session.commit()
            logger.info("  -> Tabela custo_frete criada")
            logger.info("  -> PARTE 2 CONCLUIDA")

            # ============================================================
            # PARTE 3: Tabela parametro_custeio
            # ============================================================
            logger.info("\n[3/4] Criando tabela parametro_custeio...")

            sql_parametro = """
                CREATE TABLE IF NOT EXISTS parametro_custeio (
                    id SERIAL PRIMARY KEY,
                    chave VARCHAR(50) UNIQUE NOT NULL,
                    valor NUMERIC(15,6) NOT NULL,
                    descricao TEXT,
                    atualizado_em TIMESTAMP DEFAULT NOW(),
                    atualizado_por VARCHAR(100)
                );
            """
            db.session.execute(text(sql_parametro))

            # Inserir parametro inicial
            sql_insert_param = """
                INSERT INTO parametro_custeio (chave, valor, descricao)
                VALUES ('CUSTO_OPERACAO_PERCENTUAL', 0, 'Custo operacional percentual global aplicado a todos os produtos')
                ON CONFLICT (chave) DO NOTHING;
            """
            db.session.execute(text(sql_insert_param))
            db.session.commit()
            logger.info("  -> Tabela parametro_custeio criada")
            logger.info("  -> Parametro CUSTO_OPERACAO_PERCENTUAL inserido")
            logger.info("  -> PARTE 3 CONCLUIDA")

            # ============================================================
            # PARTE 4: Campos de snapshot e margem em carteira_principal
            # ============================================================
            logger.info("\n[4/4] Adicionando campos de snapshot e margem em carteira_principal...")

            sql_carteira = """
                -- Campos de snapshot de custo
                ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS custo_unitario_snapshot NUMERIC(15,6);
                ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS custo_tipo_snapshot VARCHAR(20);
                ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS custo_vigencia_snapshot TIMESTAMP;
                ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS custo_producao_snapshot NUMERIC(15,6);

                -- Campos de margem calculada
                ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS margem_bruta NUMERIC(15,2);
                ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS margem_bruta_percentual NUMERIC(5,2);
                ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS margem_liquida NUMERIC(15,2);
                ALTER TABLE carteira_principal ADD COLUMN IF NOT EXISTS margem_liquida_percentual NUMERIC(5,2);
            """
            db.session.execute(text(sql_carteira))
            db.session.commit()
            logger.info("  -> Campos de snapshot e margem adicionados")
            logger.info("  -> PARTE 4 CONCLUIDA")

            # ============================================================
            # VERIFICACAO FINAL
            # ============================================================
            logger.info("\n" + "=" * 70)
            logger.info("VERIFICACAO FINAL")
            logger.info("=" * 70)

            # Verificar custo_considerado
            result = db.session.execute(text("""
                SELECT COUNT(*) as total,
                       COUNT(CASE WHEN custo_atual = TRUE THEN 1 END) as atuais,
                       COUNT(CASE WHEN versao IS NOT NULL THEN 1 END) as com_versao
                FROM custo_considerado
            """))
            row = result.fetchone()
            logger.info(f"custo_considerado: {row[0]} registros, {row[1]} atuais, {row[2]} com versao")

            # Verificar tabelas novas
            for tabela in ['custo_frete', 'parametro_custeio']:
                result = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela}"))
                count = result.scalar()
                logger.info(f"{tabela}: {count} registros")

            # Verificar campos na carteira_principal
            result = db.session.execute(text("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'carteira_principal'
                AND column_name IN (
                    'custo_unitario_snapshot', 'custo_tipo_snapshot',
                    'custo_vigencia_snapshot', 'custo_producao_snapshot',
                    'margem_bruta', 'margem_bruta_percentual',
                    'margem_liquida', 'margem_liquida_percentual'
                )
                ORDER BY column_name
            """))
            campos = [row[0] for row in result.fetchall()]
            logger.info(f"carteira_principal: {len(campos)} campos de custo/margem adicionados")
            for campo in campos:
                logger.info(f"  - {campo}")

            logger.info("\n" + "=" * 70)
            logger.info("MIGRACAO CONCLUIDA COM SUCESSO!")
            logger.info("=" * 70)

            return True

        except Exception as e:
            db.session.rollback()
            logger.error(f"\nERRO na migracao: {e}")
            logger.exception("Detalhes do erro:")
            return False


def verificar_estado_atual():
    """Verifica estado atual do banco antes da migracao"""
    app = create_app()

    with app.app_context():
        logger.info("\n" + "=" * 70)
        logger.info("VERIFICACAO DE ESTADO ATUAL")
        logger.info("=" * 70)

        # Verificar se custo_considerado existe
        result = db.session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'custo_considerado'
            ORDER BY ordinal_position
        """))
        colunas = [row[0] for row in result.fetchall()]

        if 'versao' in colunas:
            logger.info("custo_considerado: JA TEM campos de versionamento")
        else:
            logger.info("custo_considerado: PRECISA de campos de versionamento")

        # Verificar tabelas auxiliares
        for tabela in ['custo_frete', 'parametro_custeio']:
            result = db.session.execute(text(f"""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = '{tabela}'
                )
            """))
            existe = result.scalar()
            status = "JA EXISTE" if existe else "NAO EXISTE (sera criada)"
            logger.info(f"{tabela}: {status}")

        # Verificar campos em carteira_principal
        result = db.session.execute(text("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'carteira_principal'
            AND column_name LIKE '%snapshot%' OR column_name LIKE 'margem%'
        """))
        campos = [row[0] for row in result.fetchall()]

        if campos:
            logger.info(f"carteira_principal: JA TEM {len(campos)} campos de custo/margem")
        else:
            logger.info("carteira_principal: PRECISA de campos de custo/margem")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Migracao do Sistema de Custeio')
    parser.add_argument('--verificar', action='store_true', help='Apenas verificar estado atual')
    parser.add_argument('--executar', action='store_true', help='Executar migracao')

    args = parser.parse_args()

    if args.verificar:
        verificar_estado_atual()
    elif args.executar:
        sucesso = executar_migracao()
        sys.exit(0 if sucesso else 1)
    else:
        print("Uso:")
        print("  --verificar  Verificar estado atual do banco")
        print("  --executar   Executar migracao")
        print("\nExemplo:")
        print("  python scripts/migrations/evolucao_custeio.py --verificar")
        print("  python scripts/migrations/evolucao_custeio.py --executar")
