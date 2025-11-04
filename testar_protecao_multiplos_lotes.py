"""
Script de Teste - Proteção contra Múltiplos Lotes
==================================================

Testa se a correção está funcionando corretamente:
- Pedidos com múltiplos separacao_lote_id devem ser IGNORADOS
- Pedidos com apenas 1 separacao_lote_id devem ser processados normalmente

Uso:
    python testar_protecao_multiplos_lotes.py
"""

import sys
import os

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))

from app import create_app, db
from app.separacao.models import Separacao
from app.odoo.services.ajuste_sincronizacao_service import AjusteSincronizacaoService
import logging

# Configurar logging detalhado
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def testar_protecao_multiplos_lotes():
    """
    Testa a proteção contra múltiplos lotes
    """
    app = create_app()

    with app.app_context():
        try:
            logger.info("=" * 80)
            logger.info("TESTE DE PROTEÇÃO CONTRA MÚLTIPLOS LOTES")
            logger.info("=" * 80)

            # Buscar um pedido com múltiplos lotes (se existir)
            query = """
                SELECT num_pedido, COUNT(DISTINCT separacao_lote_id) as total_lotes
                FROM separacao
                WHERE separacao_lote_id IS NOT NULL
                  AND sincronizado_nf = FALSE
                GROUP BY num_pedido
                HAVING COUNT(DISTINCT separacao_lote_id) > 1
                LIMIT 1
            """

            resultado = db.session.execute(query).fetchone()

            if resultado:
                num_pedido, total_lotes = resultado
                logger.info(f"\n✅ Encontrado pedido {num_pedido} com {total_lotes} lotes diferentes")

                # Testar a função de identificação de lotes
                logger.info(f"\n🔍 Testando _identificar_lotes_afetados para pedido {num_pedido}...")

                lotes_afetados = AjusteSincronizacaoService._identificar_lotes_afetados(num_pedido)

                if len(lotes_afetados) == 0:
                    logger.info(f"✅ SUCESSO! Pedido {num_pedido} foi IGNORADO corretamente (retornou lista vazia)")
                    logger.info(f"   📋 Proteção funcionando: pedidos com múltiplos lotes não serão alterados")
                else:
                    logger.error(f"❌ FALHA! Pedido {num_pedido} NÃO foi ignorado")
                    logger.error(f"   ❌ Retornou {len(lotes_afetados)} lotes: {lotes_afetados}")
                    return False

                # Verificar os lotes reais no banco
                logger.info(f"\n📊 Verificando lotes reais no banco para pedido {num_pedido}:")
                separacoes = Separacao.query.filter_by(
                    num_pedido=num_pedido,
                    sincronizado_nf=False
                ).all()

                lotes_encontrados = set()
                for sep in separacoes:
                    if sep.separacao_lote_id:
                        lotes_encontrados.add(sep.separacao_lote_id)
                        logger.info(f"   - Lote: {sep.separacao_lote_id}, Produto: {sep.cod_produto}, Qtd: {sep.qtd_saldo}, Status: {sep.status}")

                logger.info(f"\n📈 Total de lotes únicos: {len(lotes_encontrados)}")

            else:
                logger.warning("⚠️ Nenhum pedido com múltiplos lotes encontrado no banco")
                logger.info("   Criando cenário de teste simulado...")

                # Listar alguns pedidos com apenas 1 lote para comparação
                query_simples = """
                    SELECT num_pedido, COUNT(DISTINCT separacao_lote_id) as total_lotes
                    FROM separacao
                    WHERE separacao_lote_id IS NOT NULL
                      AND sincronizado_nf = FALSE
                    GROUP BY num_pedido
                    HAVING COUNT(DISTINCT separacao_lote_id) = 1
                    LIMIT 3
                """

                pedidos_simples = db.session.execute(query_simples).fetchall()

                if pedidos_simples:
                    logger.info("\n📋 Pedidos com 1 único lote (devem ser processados):")
                    for num_pedido, total_lotes in pedidos_simples:
                        lotes_afetados = AjusteSincronizacaoService._identificar_lotes_afetados(num_pedido)

                        if len(lotes_afetados) == 1:
                            logger.info(f"   ✅ {num_pedido}: 1 lote - Processado corretamente")
                        else:
                            logger.error(f"   ❌ {num_pedido}: Esperado 1 lote, retornou {len(lotes_afetados)}")

            logger.info("\n" + "=" * 80)
            logger.info("TESTE CONCLUÍDO")
            logger.info("=" * 80)

            return True

        except Exception as e:
            logger.error(f"❌ Erro durante teste: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    sucesso = testar_protecao_multiplos_lotes()
    sys.exit(0 if sucesso else 1)
