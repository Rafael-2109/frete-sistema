#!/usr/bin/env python3
"""
Comando para corrigir todos os saldos da CarteiraPrincipal
===========================================================

Este comando faz uma correção única em todos os registros da CarteiraPrincipal,
recalculando qtd_saldo_produto_pedido baseado no faturamento atual.

Uso:
    python app/commands/corrigir_saldos_carteira.py

Autor: Sistema de Fretes
Data: 2025-01-23
"""

import logging
import sys
import os
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app, db
from sqlalchemy import text

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def corrigir_todos_saldos_carteira():
    """
    Corrige todos os saldos da CarteiraPrincipal baseado no faturamento atual

    Fórmula: qtd_saldo_produto_pedido = qtd_produto_pedido - qtd_faturada

    Returns:
        int: Número de registros atualizados
    """
    try:
        logger.info("=" * 80)
        logger.info("🔧 CORREÇÃO DE SALDOS DA CARTEIRA PRINCIPAL")
        logger.info("=" * 80)
        logger.info(f"Início: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        # Query SQL otimizada para update em massa
        # Esta query atualiza TODOS os registros de uma vez
        sql_update = text("""
            UPDATE carteira_principal cp
            SET qtd_saldo_produto_pedido = cp.qtd_produto_pedido - COALESCE(
                (SELECT SUM(fp.qtd_produto_faturado)
                 FROM faturamento_produto fp
                 WHERE fp.origem = cp.num_pedido
                   AND fp.cod_produto = cp.cod_produto
                   AND fp.status_nf != 'Cancelado'), 0
            ),
            updated_at = NOW(),
            updated_by = 'CorrecaoSaldos'
            WHERE 1=1
        """)

        logger.info("📊 Executando correção em massa...")
        logger.info("   Isso pode levar alguns minutos dependendo do tamanho da base...")

        resultado = db.session.execute(sql_update)
        registros_atualizados = resultado.rowcount

        # Commit das mudanças
        db.session.commit()

        logger.info("=" * 80)
        logger.info(f"✅ CORREÇÃO CONCLUÍDA COM SUCESSO!")
        logger.info(f"   Total de registros atualizados: {registros_atualizados:,}")
        logger.info(f"Término: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("=" * 80)

        return registros_atualizados

    except Exception as e:
        logger.error(f"❌ Erro ao corrigir saldos: {e}")
        db.session.rollback()
        raise


def verificar_saldos_negativos():
    """
    Verifica se existem saldos negativos após a correção
    """
    try:
        sql_check = text("""
            SELECT
                COUNT(*) as total,
                COUNT(CASE WHEN qtd_saldo_produto_pedido < 0 THEN 1 END) as negativos
            FROM carteira_principal
            WHERE 1=1
        """)

        resultado = db.session.execute(sql_check).fetchone()
        total = resultado[0]
        negativos = resultado[1]

        if negativos > 0:
            logger.warning(f"⚠️  ATENÇÃO: Existem {negativos} registros com saldo negativo!")
            logger.warning("   Isso pode indicar:")
            logger.warning("   1. Faturamento maior que quantidade do pedido")
            logger.warning("   2. Múltiplas NFs para o mesmo pedido/produto")
            logger.warning("   3. Dados inconsistentes que precisam de análise manual")

            # Mostrar alguns exemplos
            sql_exemplos = text("""
                SELECT
                    num_pedido,
                    cod_produto,
                    qtd_produto_pedido,
                    qtd_saldo_produto_pedido
                FROM carteira_principal
                WHERE qtd_saldo_produto_pedido < 0
                LIMIT 5
            """)

            exemplos = db.session.execute(sql_exemplos).fetchall()
            if exemplos:
                logger.warning("\n   Exemplos de saldos negativos:")
                for ex in exemplos:
                    logger.warning(f"   - Pedido {ex[0]}, Produto {ex[1]}: "
                                 f"Qtd={ex[2]}, Saldo={ex[3]}")
        else:
            logger.info(f"✅ Todos os {total} registros têm saldo válido (>= 0)")

        return negativos

    except Exception as e:
        logger.error(f"❌ Erro ao verificar saldos: {e}")
        return -1


def main():
    """
    Função principal
    """
    app = create_app()

    with app.app_context():
        try:
            # 1. Executar correção
            registros = corrigir_todos_saldos_carteira()

            if registros > 0:
                # 2. Verificar saldos negativos
                logger.info("\n🔍 Verificando integridade dos dados...")
                verificar_saldos_negativos()

                # 3. Estatísticas finais
                logger.info("\n📊 RESUMO FINAL:")
                logger.info(f"   - Registros corrigidos: {registros:,}")
                logger.info("   - Processo: CONCLUÍDO")
                logger.info("   - Próximos passos: O scheduler manterá os saldos atualizados")

            else:
                logger.warning("⚠️ Nenhum registro foi atualizado")
                logger.warning("   Verifique se existem dados na CarteiraPrincipal")

        except Exception as e:
            logger.error(f"❌ ERRO FATAL: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()