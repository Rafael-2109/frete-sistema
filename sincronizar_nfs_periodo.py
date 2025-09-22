#!/usr/bin/env python3
"""
Script SIMPLES para Sincronizar NFs de um Período
=================================================

Usa o FaturamentoService.sincronizar_faturamento_incremental()
com janela de tempo customizada.

Período: 01/07/2025 até 21/09/2025

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

    # Período desejado
    DATA_INICIO = date(2025, 7, 1)   # 01/07/2025
    DATA_FIM = date(2025, 9, 21)      # 21/09/2025

    # Calcular janela em minutos
    dias = (DATA_FIM - DATA_INICIO).days + 1
    horas = dias * 24
    minutos = horas * 60

    logger.info("="*60)
    logger.info("🔄 SINCRONIZAÇÃO DE NFs HISTÓRICAS")
    logger.info("="*60)
    logger.info(f"📅 Período: {DATA_INICIO.strftime('%d/%m/%Y')} até {DATA_FIM.strftime('%d/%m/%Y')}")
    logger.info(f"⏱️ Janela: {dias} dias = {minutos} minutos")
    logger.info("")

    app = create_app()

    with app.app_context():
        try:
            # Confirmar
            resposta = input(f"⚠️ Sincronizar {dias} dias de NFs? (s/N): ")
            if resposta.strip().lower() not in ['s', 'sim', 'y', 'yes']:
                logger.info("❌ Cancelado")
                return 0

            logger.info("✅ Iniciando sincronização...")

            # Criar serviço
            service = FaturamentoService()

            # Chamar sincronização com janela customizada
            # O método vai buscar NFs dos últimos X minutos
            resultado = service.sincronizar_faturamento_incremental(
                minutos_janela=minutos,
                primeira_execucao=True  # Para não aplicar filtros adicionais
            )

            if resultado.get('sucesso'):
                logger.info("\n✅ SINCRONIZAÇÃO CONCLUÍDA!")
                logger.info(f"   Registros novos: {resultado.get('registros_novos', 0)}")
                logger.info(f"   Registros atualizados: {resultado.get('registros_atualizados', 0)}")
                logger.info(f"   Tempo: {resultado.get('tempo_execucao', 0):.2f}s")

                # Mostrar detalhes se houver
                sinc = resultado.get('sincronizacoes', {})
                if sinc:
                    logger.info(f"   Entregas: {sinc.get('entregas_sincronizadas', 0)}")
                    logger.info(f"   Fretes: {sinc.get('fretes_lancados', 0)}")
            else:
                logger.error(f"❌ Erro: {resultado.get('erro')}")
                return 1

            # Verificar resultados
            from app.separacao.models import Separacao
            from app.carteira.models import CarteiraPrincipal

            sincronizadas = Separacao.query.filter_by(sincronizado_nf=True).count()
            nao_sincronizadas = Separacao.query.filter_by(sincronizado_nf=False).count()
            com_saldo = CarteiraPrincipal.query.filter(
                CarteiraPrincipal.qtd_saldo_produto_pedido > 0
            ).count()

            logger.info(f"\n📊 ESTADO FINAL:")
            logger.info(f"   Separações sincronizadas: {sincronizadas}")
            logger.info(f"   Separações não sincronizadas: {nao_sincronizadas}")
            logger.info(f"   Itens com saldo > 0: {com_saldo}")

            return 0

        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
            return 1


if __name__ == '__main__':
    sys.exit(main())