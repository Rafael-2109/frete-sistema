#!/usr/bin/env python3
"""
Script para Limpar Duplicatas e Re-sincronizar NFs Históricas
==============================================================

1. Verifica e remove duplicatas existentes
2. Recalcula saldos da carteira
3. Executa sincronização histórica com correção aplicada

Autor: Sistema de Fretes
Data: 21/09/2025
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from datetime import date
from decimal import Decimal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def remover_duplicatas():
    """Remove duplicatas do FaturamentoProduto"""
    from app import create_app, db
    from app.faturamento.models import FaturamentoProduto
    from sqlalchemy import func, desc

    app = create_app()

    with app.app_context():
        logger.info("=" * 80)
        logger.info("🧹 FASE 1: REMOVENDO DUPLICATAS")
        logger.info("=" * 80)

        # Verificar duplicatas
        duplicatas = db.session.query(
            FaturamentoProduto.numero_nf,
            FaturamentoProduto.cod_produto,
            func.count().label('quantidade')
        ).group_by(
            FaturamentoProduto.numero_nf,
            FaturamentoProduto.cod_produto
        ).having(func.count() > 1).all()

        if not duplicatas:
            logger.info("✅ Nenhuma duplicata encontrada!")
            return True

        logger.info(f"⚠️ Encontradas {len(duplicatas)} combinações duplicadas")

        # Mostrar algumas amostras
        for dup in duplicatas[:5]:
            logger.info(f"   NF {dup.numero_nf}, Produto {dup.cod_produto}: {dup.quantidade} registros")

        # Confirmar remoção
        resposta = input("\n⚠️ Deseja remover as duplicatas? (s/N): ")
        if resposta.strip().lower() not in ['s', 'sim', 'y', 'yes']:
            logger.info("❌ Cancelado pelo usuário")
            return False

        # Remover duplicatas
        total_removidas = 0
        for dup in duplicatas:
            registros = FaturamentoProduto.query.filter_by(
                numero_nf=dup.numero_nf,
                cod_produto=dup.cod_produto
            ).order_by(desc(FaturamentoProduto.id)).all()

            # Remover todos exceto o primeiro (mais recente)
            if len(registros) > 1:
                for registro in registros[1:]:
                    db.session.delete(registro)
                    total_removidas += 1

        db.session.commit()
        logger.info(f"✅ {total_removidas} registros duplicados removidos")

        return True


def recalcular_saldos():
    """Recalcula os saldos da carteira"""
    from app import create_app, db
    from app.carteira.models import CarteiraPrincipal
    from app.faturamento.models import FaturamentoProduto
    from sqlalchemy import func

    app = create_app()

    with app.app_context():
        logger.info("\n" + "=" * 80)
        logger.info("📊 FASE 2: RECALCULANDO SALDOS")
        logger.info("=" * 80)

        itens_carteira = CarteiraPrincipal.query.all()
        logger.info(f"Processando {len(itens_carteira)} itens...")

        contador_atualizados = 0
        contador_negativos = 0

        for i, item in enumerate(itens_carteira):
            if i % 500 == 0:
                logger.info(f"   Processando item {i}/{len(itens_carteira)}...")

            # Buscar total faturado
            total_faturado = db.session.query(
                func.sum(FaturamentoProduto.qtd_produto_faturado)
            ).filter(
                FaturamentoProduto.origem == item.num_pedido,
                FaturamentoProduto.cod_produto == item.cod_produto,
                FaturamentoProduto.status_nf != 'Cancelado'
            ).scalar() or Decimal('0')

            # Calcular novo saldo
            novo_saldo = item.qtd_produto_pedido - total_faturado

            if item.qtd_saldo_produto_pedido != novo_saldo:
                item.qtd_saldo_produto_pedido = novo_saldo
                contador_atualizados += 1

                if novo_saldo < 0:
                    contador_negativos += 1

        db.session.commit()

        logger.info(f"✅ {contador_atualizados} saldos atualizados")
        if contador_negativos > 0:
            logger.info(f"⚠️ {contador_negativos} itens com saldo negativo (faturado > pedido)")

        # Estatística final
        valor_total = db.session.query(
            func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido)
        ).filter(
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).scalar() or Decimal('0')

        logger.info(f"💰 Valor total da carteira (saldo > 0): R$ {valor_total:,.2f}")

        return True


def sincronizar_historico():
    """Executa sincronização histórica com correção aplicada"""
    from app import create_app
    from app.odoo.services.faturamento_service import FaturamentoService
    from app.separacao.models import Separacao
    from app.carteira.models import CarteiraPrincipal

    # Período desejado
    DATA_INICIO = date(2025, 7, 1)   # 01/07/2025
    DATA_FIM = date(2025, 9, 21)      # 21/09/2025

    # Calcular janelas em minutos
    dias = (DATA_FIM - DATA_INICIO).days + 1
    minutos_totais = dias * 24 * 60  # Converter dias para minutos

    logger.info("\n" + "=" * 80)
    logger.info("🔄 FASE 3: SINCRONIZAÇÃO HISTÓRICA")
    logger.info("=" * 80)
    logger.info(f"📅 Período: {DATA_INICIO.strftime('%d/%m/%Y')} até {DATA_FIM.strftime('%d/%m/%Y')}")
    logger.info(f"⏱️ Janela: {dias} dias = {minutos_totais:,} minutos")
    logger.info("")

    app = create_app()

    with app.app_context():
        # Estatísticas antes
        logger.info("📊 Estado ANTES da sincronização:")
        sincronizadas_antes = Separacao.query.filter_by(sincronizado_nf=True).count()
        nao_sincronizadas_antes = Separacao.query.filter_by(sincronizado_nf=False).count()
        com_saldo_antes = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).count()

        logger.info(f"   Separações sincronizadas: {sincronizadas_antes}")
        logger.info(f"   Separações não sincronizadas: {nao_sincronizadas_antes}")
        logger.info(f"   Itens com saldo > 0: {com_saldo_antes}")

        # Confirmar
        resposta = input(f"\n⚠️ Sincronizar {dias} dias de NFs? (s/N): ")
        if resposta.strip().lower() not in ['s', 'sim', 'y', 'yes']:
            logger.info("❌ Cancelado pelo usuário")
            return False

        logger.info("\n✅ Iniciando sincronização...")

        # Criar serviço
        service = FaturamentoService()

        # Chamar sincronização com parâmetros específicos
        logger.info(f"\n🔄 Chamando sincronização com:")
        logger.info(f"   minutos_janela: {minutos_totais:,}")
        logger.info(f"   minutos_status: {minutos_totais:,}")
        logger.info(f"   primeira_execucao: False")
        logger.info(f"   🔴 Com correção aplicada: verificará NFs dos últimos {int(minutos_totais * 1.1)} minutos")

        resultado = service.sincronizar_faturamento_incremental(
            minutos_janela=minutos_totais,  # Período completo para buscar dados
            primeira_execucao=False,  # NÃO sobrescrever minutos_janela
            minutos_status=minutos_totais  # Período completo para buscar status
        )

        if resultado.get('sucesso'):
            logger.info("\n✅ SINCRONIZAÇÃO CONCLUÍDA!")
            logger.info(f"   Registros novos: {resultado.get('registros_novos', 0)}")
            logger.info(f"   Registros atualizados: {resultado.get('registros_atualizados', 0)}")
            logger.info(f"   Tempo: {resultado.get('tempo_execucao', 0):.2f}s")

            # Detalhes adicionais
            sinc = resultado.get('sincronizacoes', {})
            if sinc:
                logger.info("\n📊 Detalhes da sincronização:")
                logger.info(f"   Entregas: {sinc.get('entregas_sincronizadas', 0)}")
                logger.info(f"   Fretes: {sinc.get('fretes_lancados', 0)}")
                logger.info(f"   Relatórios: {sinc.get('relatorios_consolidados', 0)}")
        else:
            logger.error(f"❌ Erro: {resultado.get('erro')}")
            return False

        # Estatísticas depois
        logger.info("\n📊 Estado DEPOIS da sincronização:")
        sincronizadas_depois = Separacao.query.filter_by(sincronizado_nf=True).count()
        nao_sincronizadas_depois = Separacao.query.filter_by(sincronizado_nf=False).count()
        com_saldo_depois = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.qtd_saldo_produto_pedido > 0
        ).count()
        sem_saldo_depois = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.qtd_saldo_produto_pedido == 0
        ).count()

        logger.info(f"   Separações sincronizadas: {sincronizadas_depois} (+ {sincronizadas_depois - sincronizadas_antes})")
        logger.info(f"   Separações não sincronizadas: {nao_sincronizadas_depois} (- {nao_sincronizadas_antes - nao_sincronizadas_depois})")
        logger.info(f"   Itens com saldo > 0: {com_saldo_depois} (- {com_saldo_antes - com_saldo_depois})")
        logger.info(f"   Itens com saldo = 0: {sem_saldo_depois}")

        return True


def main():
    """Função principal"""
    logger.info("=" * 80)
    logger.info("🚀 LIMPEZA E SINCRONIZAÇÃO COMPLETA")
    logger.info("=" * 80)

    # PASSO 1: Remover duplicatas
    if not remover_duplicatas():
        logger.error("❌ Falha ao remover duplicatas")
        return 1

    # PASSO 2: Recalcular saldos
    if not recalcular_saldos():
        logger.error("❌ Falha ao recalcular saldos")
        return 1

    # PASSO 3: Sincronizar histórico
    if not sincronizar_historico():
        logger.error("❌ Falha na sincronização")
        return 1

    logger.info("\n" + "=" * 80)
    logger.info("✅ PROCESSO CONCLUÍDO COM SUCESSO!")
    logger.info("=" * 80)
    logger.info("\n📌 Resumo:")
    logger.info("   1. Duplicatas removidas")
    logger.info("   2. Saldos recalculados")
    logger.info("   3. NFs históricas sincronizadas SEM duplicatas")
    logger.info("\n🔴 IMPORTANTE: A correção no faturamento_service.py garante que:")
    logger.info("   - Importações históricas verificam NFs do período completo")
    logger.info("   - Scheduler continua otimizado verificando apenas 2 dias")
    logger.info("   - NÃO haverá mais duplicatas em importações futuras")

    return 0


if __name__ == '__main__':
    sys.exit(main())