"""
Migration: Adicionar campo agendamento_confirmado em EmbarqueItem
Data: 2025-01-06
Descrição: Adiciona campo boolean e popula com dados de Separacao

COMO EXECUTAR:
--------------
python migrations/scripts/20250106_adicionar_agendamento_confirmado.py

OU via Flask shell:
-------------------
flask shell
>>> from migrations.scripts.20250106_adicionar_agendamento_confirmado import run_migration
>>> run_migration()
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


def verificar_coluna_existe():
    """Verifica se a coluna agendamento_confirmado já existe"""
    query = text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name='embarque_itens'
        AND column_name='agendamento_confirmado'
    """)

    result = db.session.execute(query).fetchone()
    return result is not None


def adicionar_coluna():
    """Adiciona coluna agendamento_confirmado"""
    logger.info("📝 PASSO 1: Adicionando coluna agendamento_confirmado...")

    query = text("""
        ALTER TABLE embarque_itens
        ADD COLUMN agendamento_confirmado BOOLEAN DEFAULT false
    """)

    db.session.execute(query)
    db.session.commit()

    logger.info("✅ Coluna adicionada com sucesso!")


def popular_valores():
    """Popula valores baseado em Separacao"""
    logger.info("📝 PASSO 2: Populando valores baseado em Separacao...")

    query = text("""
        UPDATE embarque_itens ei
        SET agendamento_confirmado = COALESCE(
            (
                SELECT s.agendamento_confirmado
                FROM separacao s
                WHERE s.separacao_lote_id = ei.separacao_lote_id
                LIMIT 1
            ),
            false
        )
        WHERE ei.separacao_lote_id IS NOT NULL
    """)

    result = db.session.execute(query)
    db.session.commit()

    logger.info(f"✅ {result.rowcount} registros atualizados!")
    return result.rowcount


def verificar_resultado():
    """Verifica resultado da migration"""
    logger.info("📝 PASSO 3: Verificando resultado...")

    query = text("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN agendamento_confirmado = true THEN 1 ELSE 0 END) as confirmados,
            SUM(CASE WHEN agendamento_confirmado = false THEN 1 ELSE 0 END) as nao_confirmados
        FROM embarque_itens
    """)

    result = db.session.execute(query).fetchone()

    logger.info("=" * 60)
    logger.info("📊 RESULTADO DA MIGRATION:")
    logger.info(f"   Total de registros: {result[0]}")
    logger.info(f"   Confirmados: {result[1]}")
    logger.info(f"   Não confirmados: {result[2]}")
    logger.info("=" * 60)

    return {
        'total': result[0],
        'confirmados': result[1],
        'nao_confirmados': result[2]
    }


def run_migration():
    """
    Executa a migration completa

    Returns:
        dict: Resultado da migration
    """
    try:
        logger.info("=" * 60)
        logger.info("🚀 INICIANDO MIGRATION: agendamento_confirmado")
        logger.info("=" * 60)

        # Verificar se já existe
        if verificar_coluna_existe():
            logger.warning("⚠️  Coluna agendamento_confirmado já existe!")
            logger.warning("⚠️  Pulando criação da coluna...")

            # Apenas popular valores se já existe
            count = popular_valores()
            resultado = verificar_resultado()

            logger.info("=" * 60)
            logger.info("✅ MIGRATION CONCLUÍDA (coluna já existia)")
            logger.info("=" * 60)

            return {
                'success': True,
                'message': 'Migration concluída (coluna já existia)',
                'registros_atualizados': count,
                'resultado': resultado
            }

        # Criar coluna
        adicionar_coluna()

        # Popular valores
        count = popular_valores()

        # Verificar resultado
        resultado = verificar_resultado()

        logger.info("=" * 60)
        logger.info("✅ MIGRATION CONCLUÍDA COM SUCESSO!")
        logger.info("=" * 60)

        return {
            'success': True,
            'message': 'Migration concluída com sucesso',
            'registros_atualizados': count,
            'resultado': resultado
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
    Reverte a migration (remove a coluna)

    ⚠️ CUIDADO: Isso apaga todos os dados da coluna!
    """
    try:
        logger.warning("=" * 60)
        logger.warning("⚠️  REVERTENDO MIGRATION: agendamento_confirmado")
        logger.warning("⚠️  ISSO IRÁ APAGAR A COLUNA E SEUS DADOS!")
        logger.warning("=" * 60)

        # Confirmar
        confirmacao = input("Digite 'SIM' para confirmar rollback: ")
        if confirmacao != 'SIM':
            logger.info("❌ Rollback cancelado pelo usuário")
            return {'success': False, 'message': 'Rollback cancelado'}

        query = text("""
            ALTER TABLE embarque_itens
            DROP COLUMN agendamento_confirmado
        """)

        db.session.execute(query)
        db.session.commit()

        logger.info("✅ Rollback concluído - Coluna removida!")

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
            if 'registros_atualizados' in resultado:
                logger.info(f"   Registros atualizados: {resultado['registros_atualizados']}")
            sys.exit(0)
        else:
            logger.error("")
            logger.error("💥 FALHA!")
            logger.error(f"   {resultado['message']}")
            sys.exit(1)
