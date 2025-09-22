#!/usr/bin/env python3
"""
Script para Remover Duplicatas e Recalcular Saldos
==================================================

1. Remove duplicatas do FaturamentoProduto (mantém apenas 1 por numero_nf + cod_produto)
2. Recalcula saldos da CarteiraPrincipal usando a fórmula correta
3. NÃO remove nenhum registro, apenas corrige valores

Autor: Sistema de Fretes
Data: 21/09/2025
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from decimal import Decimal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    from app import create_app, db
    from app.carteira.models import CarteiraPrincipal
    from app.faturamento.models import FaturamentoProduto
    from sqlalchemy import func, desc

    logger.info("="*80)
    logger.info("🔧 CORREÇÃO: REMOVER DUPLICATAS E RECALCULAR SALDOS")
    logger.info("="*80)

    app = create_app()

    with app.app_context():
        try:
            # FASE 1: REMOVER DUPLICATAS DO FATURAMENTO
            logger.info("\n📊 FASE 1: REMOVENDO DUPLICATAS DO FATURAMENTO")
            logger.info("-"*60)

            # Identificar todas as combinações duplicadas
            duplicatas = db.session.query(
                FaturamentoProduto.numero_nf,
                FaturamentoProduto.cod_produto,
                func.count().label('quantidade')
            ).group_by(
                FaturamentoProduto.numero_nf,
                FaturamentoProduto.cod_produto
            ).having(func.count() > 1).all()

            logger.info(f"   Encontradas {len(duplicatas)} combinações duplicadas")

            total_registros_antes = FaturamentoProduto.query.count()

            if duplicatas:
                total_removidas = 0

                for dup in duplicatas:
                    # Buscar todos os registros dessa combinação
                    registros = FaturamentoProduto.query.filter_by(
                        numero_nf=dup.numero_nf,
                        cod_produto=dup.cod_produto
                    ).order_by(desc(FaturamentoProduto.id)).all()

                    # Manter apenas o primeiro (mais recente por ID)
                    if len(registros) > 1:
                        logger.debug(f"      NF {dup.numero_nf}, Produto {dup.cod_produto}: {len(registros)} registros, removendo {len(registros)-1}")
                        for registro in registros[1:]:  # Remove todos exceto o primeiro
                            db.session.delete(registro)
                            total_removidas += 1

                db.session.commit()

                total_registros_depois = FaturamentoProduto.query.count()

                logger.info(f"   ✅ {total_removidas} registros duplicados removidos")
                logger.info(f"   Total antes: {total_registros_antes}, Total depois: {total_registros_depois}")

            # FASE 2: RECALCULAR SALDOS DA CARTEIRA
            logger.info("\n📊 FASE 2: RECALCULANDO SALDOS DA CARTEIRA")
            logger.info("-"*60)

            # Buscar todos os itens da carteira
            itens_carteira = CarteiraPrincipal.query.all()
            logger.info(f"   Processando {len(itens_carteira)} itens...")

            contador_atualizados = 0
            contador_zerados = 0
            contador_negativos = 0
            exemplos_negativos = []

            for i, item in enumerate(itens_carteira):
                if i % 500 == 0:
                    logger.info(f"   Processando item {i}/{len(itens_carteira)}...")

                # Buscar total faturado para este item
                # Usar origem (que é o num_pedido) e cod_produto
                total_faturado = db.session.query(
                    func.sum(FaturamentoProduto.qtd_produto_faturado)
                ).filter(
                    FaturamentoProduto.origem == item.num_pedido,
                    FaturamentoProduto.cod_produto == item.cod_produto,
                    FaturamentoProduto.status_nf != 'Cancelado'  # Não contar NFs canceladas
                ).scalar() or Decimal('0')

                # Calcular novo saldo: qtd_pedido - qtd_faturado
                novo_saldo = item.qtd_produto_pedido - total_faturado

                # Atualizar se mudou
                if item.qtd_saldo_produto_pedido != novo_saldo:
                    saldo_anterior = item.qtd_saldo_produto_pedido
                    item.qtd_saldo_produto_pedido = novo_saldo
                    contador_atualizados += 1

                    if novo_saldo == 0:
                        contador_zerados += 1
                    elif novo_saldo < 0:
                        contador_negativos += 1
                        if len(exemplos_negativos) < 5:  # Guardar alguns exemplos
                            exemplos_negativos.append({
                                'pedido': item.num_pedido,
                                'produto': item.cod_produto,
                                'qtd_pedido': item.qtd_produto_pedido,
                                'qtd_faturado': total_faturado,
                                'saldo': novo_saldo
                            })

            db.session.commit()

            logger.info(f"\n   ✅ {contador_atualizados} saldos atualizados")
            logger.info(f"      - {contador_zerados} ficaram com saldo = 0 (100% faturados)")
            logger.info(f"      - {contador_negativos} ficaram com saldo negativo")

            if exemplos_negativos:
                logger.info("\n   ⚠️ Exemplos de saldos negativos (faturado > pedido):")
                for ex in exemplos_negativos:
                    logger.info(f"      Pedido {ex['pedido']}, Produto {ex['produto']}:")
                    logger.info(f"         Qtd pedido: {ex['qtd_pedido']}, Faturado: {ex['qtd_faturado']}, Saldo: {ex['saldo']}")

            # FASE 3: ESTATÍSTICAS FINAIS
            logger.info("\n📊 FASE 3: ESTATÍSTICAS FINAIS")
            logger.info("-"*60)

            # Contar situação final
            total_carteira = CarteiraPrincipal.query.count()
            com_saldo_positivo = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0
            ).count()
            com_saldo_zero = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.qtd_saldo_produto_pedido == 0
            ).count()
            com_saldo_negativo = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.qtd_saldo_produto_pedido < 0
            ).count()

            # Valor total (apenas saldo positivo)
            valor_total = db.session.query(
                func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido)
            ).filter(
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0
            ).scalar() or Decimal('0')

            logger.info(f"   Total de itens na carteira: {total_carteira}")
            logger.info(f"   Com saldo > 0: {com_saldo_positivo} itens")
            logger.info(f"   Com saldo = 0: {com_saldo_zero} itens")
            logger.info(f"   Com saldo < 0: {com_saldo_negativo} itens")
            logger.info(f"\n   💰 Valor total (saldo > 0): R$ {valor_total:,.2f}")

            # Verificar duplicatas restantes
            logger.info("\n📊 VERIFICAÇÃO FINAL DE DUPLICATAS:")
            logger.info("-"*60)

            duplicatas_restantes = db.session.query(
                FaturamentoProduto.numero_nf,
                FaturamentoProduto.cod_produto,
                func.count().label('quantidade')
            ).group_by(
                FaturamentoProduto.numero_nf,
                FaturamentoProduto.cod_produto
            ).having(func.count() > 1).count()

            logger.info(f"   Duplicatas restantes no FaturamentoProduto: {duplicatas_restantes}")

            if duplicatas_restantes > 0:
                logger.warning("   ⚠️ Ainda existem duplicatas! Pode ser necessário rodar novamente.")
            else:
                logger.info("   ✅ Nenhuma duplicata restante!")

            logger.info("\n" + "="*80)
            logger.info("✅ PROCESSO CONCLUÍDO!")
            logger.info("="*80)
            logger.info("\n📌 RESUMO:")
            logger.info(f"   - Duplicatas removidas: {total_removidas if duplicatas else 0}")
            logger.info(f"   - Saldos recalculados: {contador_atualizados}")
            logger.info(f"   - Valor total da carteira (saldo > 0): R$ {valor_total:,.2f}")

            if com_saldo_negativo > 0:
                logger.warning(f"\n⚠️ ATENÇÃO: {com_saldo_negativo} itens com saldo negativo")
                logger.warning("   Isso indica que foi faturado MAIS do que foi pedido!")

            return 0

        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()
            return 1


if __name__ == '__main__':
    sys.exit(main())