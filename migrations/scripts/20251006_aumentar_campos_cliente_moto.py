"""
Migration: Aumentar limites de campos em ClienteMoto
Data: 2025-10-06
Descrição: Aumenta telefone_cliente (20→100) e cep_cliente (10→15)

COMO EXECUTAR:
--------------
python migrations/scripts/20251006_aumentar_campos_cliente_moto.py

OU via Flask shell:
-------------------
flask shell
>>> from migrations.scripts.20251006_aumentar_campos_cliente_moto import run_migration
>>> run_migration()

ROLLBACK:
---------
python migrations/scripts/20251006_aumentar_campos_cliente_moto.py rollback
"""

import sys
import os

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text
import logging

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def verificar_tamanho_atual():
    """Verifica o tamanho atual dos campos"""
    query = text("""
        SELECT
            column_name,
            character_maximum_length
        FROM information_schema.columns
        WHERE table_name = 'cliente_moto'
        AND column_name IN ('telefone_cliente', 'cep_cliente')
        ORDER BY column_name
    """)

    result = db.session.execute(query).fetchall()

    tamanhos = {}
    for row in result:
        tamanhos[row[0]] = row[1]

    logger.info("📏 Tamanhos atuais dos campos:")
    logger.info(f"   telefone_cliente: {tamanhos.get('telefone_cliente', 'N/A')}")
    logger.info(f"   cep_cliente: {tamanhos.get('cep_cliente', 'N/A')}")

    return tamanhos


def verificar_dados_afetados():
    """Verifica quantos registros seriam afetados"""
    query = text("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN LENGTH(telefone_cliente) > 20 THEN 1 ELSE 0 END) as telefone_longos,
            SUM(CASE WHEN LENGTH(cep_cliente) > 10 THEN 1 ELSE 0 END) as cep_longos
        FROM cliente_moto
        WHERE telefone_cliente IS NOT NULL OR cep_cliente IS NOT NULL
    """)

    result = db.session.execute(query).fetchone()

    logger.info("=" * 60)
    logger.info("📊 ANÁLISE DOS DADOS EXISTENTES:")
    logger.info(f"   Total de clientes com dados: {result[0]}")
    logger.info(f"   Telefones > 20 caracteres: {result[1]}")
    logger.info(f"   CEPs > 10 caracteres: {result[2]}")
    logger.info("=" * 60)

    return {
        'total': result[0],
        'telefone_longos': result[1],
        'cep_longos': result[2]
    }


def alterar_campos():
    """Altera o tamanho dos campos"""
    logger.info("📝 PASSO 1: Aumentando campo telefone_cliente (20 → 100)...")

    query_telefone = text("""
        ALTER TABLE cliente_moto
        ALTER COLUMN telefone_cliente TYPE VARCHAR(100)
    """)

    db.session.execute(query_telefone)
    db.session.commit()

    logger.info("✅ Campo telefone_cliente alterado com sucesso!")

    logger.info("📝 PASSO 2: Aumentando campo cep_cliente (10 → 15)...")

    query_cep = text("""
        ALTER TABLE cliente_moto
        ALTER COLUMN cep_cliente TYPE VARCHAR(15)
    """)

    db.session.execute(query_cep)
    db.session.commit()

    logger.info("✅ Campo cep_cliente alterado com sucesso!")


def verificar_resultado():
    """Verifica resultado da migration"""
    logger.info("📝 PASSO 3: Verificando resultado...")

    tamanhos = verificar_tamanho_atual()

    logger.info("=" * 60)
    logger.info("✅ RESULTADO DA MIGRATION:")
    logger.info(f"   telefone_cliente: {tamanhos.get('telefone_cliente', 'N/A')} caracteres")
    logger.info(f"   cep_cliente: {tamanhos.get('cep_cliente', 'N/A')} caracteres")
    logger.info("=" * 60)

    return tamanhos


def run_migration():
    """
    Executa a migration completa

    Returns:
        dict: Resultado da migration
    """
    try:
        logger.info("=" * 60)
        logger.info("🚀 INICIANDO MIGRATION: Aumentar campos ClienteMoto")
        logger.info("=" * 60)

        # Verificar tamanho atual
        tamanhos_antes = verificar_tamanho_atual()

        # Verificar se já está com os novos tamanhos
        if tamanhos_antes.get('telefone_cliente') == 100 and tamanhos_antes.get('cep_cliente') == 15:
            logger.warning("⚠️  Campos já estão com os novos tamanhos!")
            logger.info("=" * 60)
            logger.info("✅ MIGRATION JÁ FOI APLICADA")
            logger.info("=" * 60)

            return {
                'success': True,
                'message': 'Migration já foi aplicada anteriormente',
                'tamanhos': tamanhos_antes
            }

        # Verificar dados que seriam afetados
        dados = verificar_dados_afetados()

        # Alterar campos
        alterar_campos()

        # Verificar resultado
        tamanhos_depois = verificar_resultado()

        logger.info("=" * 60)
        logger.info("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
        logger.info("=" * 60)

        return {
            'success': True,
            'message': 'Migration concluída com sucesso',
            'tamanhos_antes': tamanhos_antes,
            'tamanhos_depois': tamanhos_depois,
            'dados_afetados': dados
        }

    except Exception as e:
        logger.error("=" * 60)
        logger.error(f"❌ ERRO NA MIGRATION: {str(e)}")
        logger.error("=" * 60)
        db.session.rollback()

        return {
            'success': False,
            'message': f'Erro na migration: {str(e)}',
            'error': str(e)
        }


def rollback_migration():
    """
    Reverte a migration (volta aos tamanhos originais)

    ⚠️ CUIDADO: Dados que excederem os limites originais serão TRUNCADOS!
    """
    try:
        logger.warning("=" * 60)
        logger.warning("⚠️  REVERTENDO MIGRATION: Campos ClienteMoto")
        logger.warning("⚠️  Telefones > 20 e CEPs > 10 serão TRUNCADOS!")
        logger.warning("=" * 60)

        # Verificar dados que seriam truncados
        dados = verificar_dados_afetados()

        if dados['telefone_longos'] > 0 or dados['cep_longos'] > 0:
            logger.warning("")
            logger.warning(f"⚠️  {dados['telefone_longos']} telefones serão truncados!")
            logger.warning(f"⚠️  {dados['cep_longos']} CEPs serão truncados!")
            logger.warning("")

        # Confirmar
        confirmacao = input("Digite 'SIM' para confirmar rollback: ")
        if confirmacao != 'SIM':
            logger.info("❌ Rollback cancelado pelo usuário")
            return {'success': False, 'message': 'Rollback cancelado'}

        logger.info("📝 Revertendo campo telefone_cliente (100 → 20)...")

        query_telefone = text("""
            ALTER TABLE cliente_moto
            ALTER COLUMN telefone_cliente TYPE VARCHAR(20)
        """)

        db.session.execute(query_telefone)
        db.session.commit()

        logger.info("✅ Campo telefone_cliente revertido!")

        logger.info("📝 Revertendo campo cep_cliente (15 → 10)...")

        query_cep = text("""
            ALTER TABLE cliente_moto
            ALTER COLUMN cep_cliente TYPE VARCHAR(10)
        """)

        db.session.execute(query_cep)
        db.session.commit()

        logger.info("✅ Campo cep_cliente revertido!")

        verificar_resultado()

        logger.info("=" * 60)
        logger.info("✅ Rollback concluído!")
        logger.info("=" * 60)

        return {
            'success': True,
            'message': 'Rollback concluído com sucesso'
        }

    except Exception as e:
        logger.error(f"❌ ERRO NO ROLLBACK: {str(e)}")
        db.session.rollback()

        return {
            'success': False,
            'message': f'Erro no rollback: {str(e)}',
            'error': str(e)
        }


if __name__ == '__main__':
    """
    Execução direta do script
    """
    # Criar app Flask
    app = create_app()

    with app.app_context():
        # Verificar argumentos
        if len(sys.argv) > 1 and sys.argv[1] == 'rollback':
            resultado = rollback_migration()
        else:
            resultado = run_migration()

        # Exibir resultado final
        if resultado['success']:
            logger.info("")
            logger.info("🎉 SUCESSO!")
            logger.info(f"   {resultado['message']}")
            sys.exit(0)
        else:
            logger.error("")
            logger.error("💥 FALHA!")
            logger.error(f"   {resultado['message']}")
            sys.exit(1)
