#!/usr/bin/env python3
"""
Script de Teste - Processamento de Cancelamento de Pedidos
==========================================================

Testa a implementação de detecção e processamento de pedidos cancelados
no scheduler da CarteiraPrincipal.

Como usar:
1. python testar_cancelamento_pedido.py --modo dry-run
   (simula sem fazer alterações)

2. python testar_cancelamento_pedido.py --pedido VSC00123
   (testa com pedido específico)

3. python testar_cancelamento_pedido.py --incremental
   (testa modo incremental completo)

Autor: Sistema de Fretes
Data: 2025-10-14
"""

import sys
import os
import argparse
from datetime import datetime

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.odoo.services.carteira_service import CarteiraService
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def testar_processamento_cancelamento(num_pedido: str, dry_run: bool = True):
    """
    Testa o processamento de cancelamento de um pedido específico
    """
    logger.info("=" * 80)
    logger.info(f"🧪 TESTE: Processamento de Cancelamento - Pedido {num_pedido}")
    logger.info(f"   Modo: {'DRY-RUN (sem alterações)' if dry_run else 'REAL (com alterações)'}")
    logger.info("=" * 80)

    app = create_app()

    with app.app_context():
        # 1. Verificar estado atual
        logger.info(f"\n📊 Estado ANTES do processamento:")

        itens_carteira = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido).all()
        logger.info(f"   - Itens na carteira: {len(itens_carteira)}")

        if itens_carteira:
            for item in itens_carteira:
                logger.info(f"     • {item.cod_produto}: status={item.status_pedido}, "
                          f"qtd={item.qtd_produto_pedido}, saldo={item.qtd_saldo_produto_pedido}")

        separacoes = Separacao.query.filter_by(num_pedido=num_pedido).all()
        logger.info(f"   - Separações: {len(separacoes)}")

        if separacoes:
            for sep in separacoes:
                logger.info(f"     • {sep.cod_produto}: status={sep.status}, "
                          f"qtd={sep.qtd_saldo}, sincronizado_nf={sep.sincronizado_nf}")

        if not itens_carteira and not separacoes:
            logger.warning(f"⚠️ Pedido {num_pedido} não encontrado no sistema!")
            return

        # 2. Executar processamento
        if not dry_run:
            logger.info(f"\n🔄 Executando processamento de cancelamento...")

            service = CarteiraService()
            resultado = service._processar_cancelamento_pedido(num_pedido)

            if resultado:
                logger.info(f"✅ Processamento concluído com sucesso")
            else:
                logger.error(f"❌ Erro no processamento")
                return

            # 3. Verificar estado após processamento
            logger.info(f"\n📊 Estado DEPOIS do processamento:")

            itens_carteira = CarteiraPrincipal.query.filter_by(num_pedido=num_pedido).all()
            logger.info(f"   - Itens na carteira: {len(itens_carteira)}")

            if itens_carteira:
                for item in itens_carteira:
                    logger.info(f"     • {item.cod_produto}: status={item.status_pedido}, "
                              f"qtd={item.qtd_produto_pedido}, "
                              f"saldo={item.qtd_saldo_produto_pedido}, "
                              f"cancelada={item.qtd_cancelada_produto_pedido}")

            separacoes = Separacao.query.filter_by(num_pedido=num_pedido).all()
            logger.info(f"   - Separações: {len(separacoes)}")

            if separacoes:
                for sep in separacoes:
                    logger.info(f"     • {sep.cod_produto}: status={sep.status}, "
                              f"qtd={sep.qtd_saldo}, sincronizado_nf={sep.sincronizado_nf}")
        else:
            logger.info(f"\n⚠️ DRY-RUN: Processamento não executado")
            logger.info(f"   Alterações que seriam feitas:")
            logger.info(f"   - {len(itens_carteira)} itens marcados como Cancelado")
            logger.info(f"   - Saldos zerados")

            separacoes_nao_faturadas = [s for s in separacoes if not s.sincronizado_nf]
            logger.info(f"   - {len(separacoes_nao_faturadas)} separações não faturadas revertidas")

    logger.info("=" * 80)


def testar_sincronizacao_incremental(minutos: int = 60, dry_run: bool = True):
    """
    Testa a sincronização incremental com detecção de cancelamentos
    """
    logger.info("=" * 80)
    logger.info(f"🧪 TESTE: Sincronização Incremental com Detecção de Cancelamentos")
    logger.info(f"   Janela: {minutos} minutos")
    logger.info(f"   Modo: {'DRY-RUN (sem alterações)' if dry_run else 'REAL (com alterações)'}")
    logger.info("=" * 80)

    app = create_app()

    with app.app_context():
        service = CarteiraService()

        # Contar estado antes
        total_carteira_antes = CarteiraPrincipal.query.count()
        cancelados_antes = CarteiraPrincipal.query.filter_by(status_pedido='Cancelado').count()

        logger.info(f"\n📊 Estado ANTES:")
        logger.info(f"   - Total na carteira: {total_carteira_antes}")
        logger.info(f"   - Cancelados: {cancelados_antes}")

        if not dry_run:
            logger.info(f"\n🔄 Executando sincronização incremental...")

            resultado = service.sincronizar_carteira_odoo_com_gestao_quantidades(
                usar_filtro_pendente=False,
                modo_incremental=True,
                minutos_janela=minutos,
                primeira_execucao=False
            )

            if resultado.get('sucesso'):
                logger.info(f"✅ Sincronização concluída com sucesso")

                # Estatísticas
                stats = resultado.get('estatisticas', {})
                logger.info(f"\n📊 Estatísticas:")
                logger.info(f"   - Novos: {stats.get('novos', 0)}")
                logger.info(f"   - Atualizados: {stats.get('atualizados', 0)}")
                logger.info(f"   - Cancelados: {stats.get('cancelamentos', 0)}")

                # Estado depois
                total_carteira_depois = CarteiraPrincipal.query.count()
                cancelados_depois = CarteiraPrincipal.query.filter_by(status_pedido='Cancelado').count()

                logger.info(f"\n📊 Estado DEPOIS:")
                logger.info(f"   - Total na carteira: {total_carteira_depois}")
                logger.info(f"   - Cancelados: {cancelados_depois}")
                logger.info(f"   - Novos cancelamentos: {cancelados_depois - cancelados_antes}")

            else:
                logger.error(f"❌ Erro na sincronização: {resultado.get('erro')}")
        else:
            logger.info(f"\n⚠️ DRY-RUN: Sincronização não executada")
            logger.info(f"   A sincronização buscaria pedidos alterados nos últimos {minutos} minutos")
            logger.info(f"   Incluindo pedidos com state='cancel' no Odoo")

    logger.info("=" * 80)


def listar_pedidos_cancelados():
    """
    Lista todos os pedidos cancelados no sistema
    """
    logger.info("=" * 80)
    logger.info("📋 PEDIDOS CANCELADOS NO SISTEMA")
    logger.info("=" * 80)

    app = create_app()

    with app.app_context():
        pedidos_cancelados = db.session.query(
            CarteiraPrincipal.num_pedido,
            db.func.count(CarteiraPrincipal.id).label('itens'),
            db.func.sum(CarteiraPrincipal.qtd_cancelada_produto_pedido).label('qtd_cancelada')
        ).filter(
            CarteiraPrincipal.status_pedido == 'Cancelado'
        ).group_by(
            CarteiraPrincipal.num_pedido
        ).all()

        logger.info(f"\n   Total de pedidos cancelados: {len(pedidos_cancelados)}\n")

        for pedido in pedidos_cancelados[:10]:  # Mostrar apenas os 10 primeiros
            logger.info(f"   • {pedido.num_pedido}: {pedido.itens} itens, "
                      f"qtd cancelada: {pedido.qtd_cancelada}")

        if len(pedidos_cancelados) > 10:
            logger.info(f"\n   ... e mais {len(pedidos_cancelados) - 10} pedidos")

    logger.info("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description='Testa processamento de cancelamento de pedidos'
    )

    parser.add_argument(
        '--pedido',
        type=str,
        help='Número do pedido para testar cancelamento'
    )

    parser.add_argument(
        '--incremental',
        action='store_true',
        help='Testar sincronização incremental completa'
    )

    parser.add_argument(
        '--minutos',
        type=int,
        default=60,
        help='Janela de minutos para sincronização incremental (padrão: 60)'
    )

    parser.add_argument(
        '--listar',
        action='store_true',
        help='Listar pedidos cancelados no sistema'
    )

    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simular sem fazer alterações (recomendado para primeiro teste)'
    )

    args = parser.parse_args()

    try:
        if args.listar:
            listar_pedidos_cancelados()

        elif args.pedido:
            testar_processamento_cancelamento(args.pedido, dry_run=args.dry_run)

        elif args.incremental:
            testar_sincronizacao_incremental(args.minutos, dry_run=args.dry_run)

        else:
            parser.print_help()
            print("\n💡 Exemplos de uso:")
            print("   python testar_cancelamento_pedido.py --listar")
            print("   python testar_cancelamento_pedido.py --pedido VSC00123 --dry-run")
            print("   python testar_cancelamento_pedido.py --incremental --minutos 120 --dry-run")

    except KeyboardInterrupt:
        logger.info("\n👋 Teste interrompido pelo usuário")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n❌ Erro durante o teste: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
