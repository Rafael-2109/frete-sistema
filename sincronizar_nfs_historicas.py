#!/usr/bin/env python3
"""
Script para Sincronizar NFs Históricas
======================================

Usa o FaturamentoService com parâmetros corretos para buscar e processar
NFs do período de 01/07/2025 até 21/09/2025.

Autor: Sistema de Fretes
Data: 21/09/2025
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from datetime import date

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
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

    logger.info("="*60)
    logger.info("🔄 SINCRONIZAÇÃO DE NFs HISTÓRICAS")
    logger.info("="*60)
    logger.info(f"📅 Período: {DATA_INICIO.strftime('%d/%m/%Y')} até {DATA_FIM.strftime('%d/%m/%Y')}")
    logger.info(f"⏱️ Janela: {dias} dias = {minutos_totais:,} minutos")
    logger.info("")

    app = create_app()

    with app.app_context():
        try:
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
                return 0

            logger.info("\n✅ Iniciando sincronização...")

            # Criar serviço
            service = FaturamentoService()

            # Chamar sincronização com parâmetros específicos
            logger.info(f"\n🔄 Chamando sincronização com:")
            logger.info(f"   minutos_janela: {minutos_totais:,}")
            logger.info(f"   minutos_status: {minutos_totais:,}")
            logger.info(f"   primeira_execucao: False")

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

                # Movimentações
                mov = resultado.get('movimentacoes_estoque', {})
                if mov:
                    logger.info(f"   Movimentações criadas: {mov.get('movimentacoes_criadas', 0)}")

            else:
                logger.error(f"❌ Erro: {resultado.get('erro')}")
                return 1

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

            logger.info("\n" + "="*60)
            logger.info("✅ PROCESSO CONCLUÍDO COM SUCESSO!")
            logger.info("="*60)
            logger.info("\n📌 Os saldos foram ajustados automaticamente:")
            logger.info("   - NFs processadas marcaram separações como sincronizadas")
            logger.info("   - Itens com separações sincronizadas não aparecem mais na carteira")

            return 0

        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == '__main__':
    sys.exit(main())