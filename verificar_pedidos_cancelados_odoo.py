#!/usr/bin/env python3
"""
Script: Verificação e Exclusão de Pedidos Cancelados no Odoo
=============================================================

Busca todos os pedidos no sistema com qtd_saldo_produto_pedido > 0,
verifica no Odoo se estão cancelados, exibe resumo agrupado e
oferece opção de exclusão.

Uso:
    python verificar_pedidos_cancelados_odoo.py
    python verificar_pedidos_cancelados_odoo.py --auto-confirmar  # ⚠️ CUIDADO!

Autor: Sistema de Fretes
Data: 2025-10-14
"""

import sys
import os
import argparse
from datetime import datetime
from decimal import Decimal

# Adicionar path do projeto
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import create_app, db
from app.carteira.models import CarteiraPrincipal
from app.separacao.models import Separacao
from app.odoo.utils.connection import get_odoo_connection
from sqlalchemy import func
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def buscar_pedidos_com_saldo():
    """
    Busca todos os pedidos com saldo no sistema
    Agrupa por pedido para exibir totais
    """
    logger.info("🔍 Buscando pedidos com saldo no sistema...")

    pedidos = db.session.query(
        CarteiraPrincipal.num_pedido,
        CarteiraPrincipal.cnpj_cpf,
        CarteiraPrincipal.raz_social_red,
        CarteiraPrincipal.nome_cidade,
        CarteiraPrincipal.cod_uf,
        CarteiraPrincipal.status_pedido,
        func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido * CarteiraPrincipal.preco_produto_pedido).label('valor_total'),
        func.sum(CarteiraPrincipal.qtd_saldo_produto_pedido).label('qtd_total'),
        func.count(CarteiraPrincipal.id).label('num_itens')
    ).filter(
        CarteiraPrincipal.qtd_saldo_produto_pedido > 0,
        CarteiraPrincipal.status_pedido != 'Cancelado'  # Apenas não cancelados no sistema
    ).group_by(
        CarteiraPrincipal.num_pedido,
        CarteiraPrincipal.cnpj_cpf,
        CarteiraPrincipal.raz_social_red,
        CarteiraPrincipal.nome_cidade,
        CarteiraPrincipal.cod_uf,
        CarteiraPrincipal.status_pedido
    ).order_by(
        CarteiraPrincipal.num_pedido
    ).all()

    logger.info(f"✅ Encontrados {len(pedidos)} pedidos com saldo no sistema")

    return pedidos


def verificar_status_odoo(connection, pedidos):
    """
    Verifica no Odoo quais pedidos estão cancelados
    """
    logger.info("🔄 Verificando status no Odoo...")

    numeros_pedidos = [p.num_pedido for p in pedidos]

    # Buscar pedidos no Odoo
    try:
        pedidos_odoo = connection.search_read(
            'sale.order',
            [('name', 'in', numeros_pedidos)],
            ['name', 'state']
        )

        # Criar dicionário de status
        status_odoo = {p['name']: p['state'] for p in pedidos_odoo}

        logger.info(f"✅ {len(pedidos_odoo)} pedidos encontrados no Odoo")

        return status_odoo

    except Exception as e:
        logger.error(f"❌ Erro ao buscar pedidos no Odoo: {e}")
        return {}


def exibir_pedidos_cancelados(pedidos, status_odoo):
    """
    Exibe pedidos cancelados no Odoo mas ainda com saldo no sistema
    """
    cancelados = []

    print("\n" + "=" * 120)
    print("📋 PEDIDOS CANCELADOS NO ODOO COM SALDO NO SISTEMA")
    print("=" * 120)
    print()

    for pedido in pedidos:
        status = status_odoo.get(pedido.num_pedido, 'não encontrado')

        if status == 'cancel':
            cancelados.append(pedido)

            # Formatar valores
            valor_total = float(pedido.valor_total or 0)
            qtd_total = float(pedido.qtd_total or 0)

            print(f"🔴 Pedido: {pedido.num_pedido}")
            print(f"   Cliente: {pedido.raz_social_red or 'N/A'}")
            print(f"   CNPJ: {pedido.cnpj_cpf or 'N/A'}")
            print(f"   Cidade/UF: {pedido.nome_cidade or 'N/A'} / {pedido.cod_uf or 'N/A'}")
            print(f"   Status Sistema: {pedido.status_pedido}")
            print(f"   Status Odoo: CANCELADO")
            print(f"   Valor Total: R$ {valor_total:,.2f}")
            print(f"   Qtd Total: {qtd_total:,.2f}")
            print(f"   Itens: {pedido.num_itens}")
            print()

    print("=" * 120)
    print(f"Total de pedidos cancelados no Odoo: {len(cancelados)}")

    if cancelados:
        valor_total_cancelados = sum(float(p.valor_total or 0) for p in cancelados)
        print(f"Valor total dos cancelados: R$ {valor_total_cancelados:,.2f}")

    print("=" * 120)
    print()

    return cancelados


def excluir_pedidos_cancelados(pedidos_cancelados, auto_confirmar=False):
    """
    Exclui pedidos cancelados do sistema após confirmação

    Processo:
    1. Para cada separação vinculada a EmbarqueItem: cancela o EmbarqueItem
    2. Exclui todas as Separacao
    3. Exclui da CarteiraPrincipal
    4. Remove PreSeparacaoItem se existirem
    """
    if not pedidos_cancelados:
        logger.info("✅ Nenhum pedido cancelado para excluir")
        return

    print(f"\n⚠️  ATENÇÃO: {len(pedidos_cancelados)} pedidos serão EXCLUÍDOS do sistema!\n")

    # Listar pedidos que serão excluídos
    print("Pedidos que serão excluídos:")
    for i, pedido in enumerate(pedidos_cancelados, 1):
        print(f"  {i}. {pedido.num_pedido} - {pedido.raz_social_red}")

    print()

    # Confirmar exclusão
    if not auto_confirmar:
        confirmacao = input("Digite 'EXCLUIR' para confirmar a exclusão: ").strip()

        if confirmacao != 'EXCLUIR':
            logger.info("❌ Exclusão cancelada pelo usuário")
            return
    else:
        logger.warning("⚠️  Modo auto-confirmar ativado! Excluindo automaticamente...")

    # Executar exclusão
    logger.info("🔄 Iniciando exclusão...")

    numeros_pedidos = [p.num_pedido for p in pedidos_cancelados]

    try:
        from app.embarques.models import EmbarqueItem

        # 1. Cancelar EmbarqueItem vinculados às separações desses pedidos
        logger.info("   🔍 Verificando separações vinculadas a embarques...")

        separacoes = Separacao.query.filter(
            Separacao.num_pedido.in_(numeros_pedidos)
        ).all()

        embarques_cancelados = 0

        for separacao in separacoes:
            if separacao.separacao_lote_id:
                embarque_itens = EmbarqueItem.query.filter_by(
                    separacao_lote_id=separacao.separacao_lote_id
                ).all()

                for embarque_item in embarque_itens:
                    embarque_item.status = 'cancelado'
                    embarques_cancelados += 1

        if embarques_cancelados > 0:
            logger.info(f"   ✅ {embarques_cancelados} itens de embarque cancelados")

        # 2. Excluir todas as Separacao (incluindo faturadas)
        separacoes_excluidas = Separacao.query.filter(
            Separacao.num_pedido.in_(numeros_pedidos)
        ).delete(synchronize_session=False)

        logger.info(f"   ✅ {separacoes_excluidas} separações excluídas")

        # 3. Excluir da CarteiraPrincipal
        itens_excluidos = CarteiraPrincipal.query.filter(
            CarteiraPrincipal.num_pedido.in_(numeros_pedidos)
        ).delete(synchronize_session=False)

        logger.info(f"   ✅ {itens_excluidos} itens excluídos da CarteiraPrincipal")

        # 4. PreSeparacaoItem (se existir)
        try:
            from app.carteira.models import PreSeparacaoItem

            presep_excluidos = PreSeparacaoItem.query.filter(
                PreSeparacaoItem.num_pedido.in_(numeros_pedidos)
            ).delete(synchronize_session=False)

            if presep_excluidos > 0:
                logger.info(f"   ✅ {presep_excluidos} pré-separações excluídas")

        except Exception:
            pass  # Tabela pode não existir

        # Commit
        db.session.commit()

        logger.info(f"✅ Exclusão concluída com sucesso!")
        logger.info(f"   - EmbarqueItens cancelados: {embarques_cancelados}")
        logger.info(f"   - Separações excluídas: {separacoes_excluidas}")
        logger.info(f"   - Itens da carteira excluídos: {itens_excluidos}")
        logger.info(f"   - Total de pedidos excluídos: {len(numeros_pedidos)}")

    except Exception as e:
        logger.error(f"❌ Erro durante exclusão: {e}")
        db.session.rollback()
        raise


def gerar_relatorio(pedidos, status_odoo):
    """
    Gera relatório completo de status
    """
    print("\n" + "=" * 120)
    print("📊 RELATÓRIO COMPLETO")
    print("=" * 120)
    print()

    # Contar por status
    cancelados = sum(1 for p in pedidos if status_odoo.get(p.num_pedido) == 'cancel')
    ativos = sum(1 for p in pedidos if status_odoo.get(p.num_pedido) in ['draft', 'sent', 'sale', 'done'])
    nao_encontrados = sum(1 for p in pedidos if p.num_pedido not in status_odoo)

    print(f"Total de pedidos no sistema com saldo: {len(pedidos)}")
    print()
    print(f"Status no Odoo:")
    print(f"  - Cancelados: {cancelados} 🔴")
    print(f"  - Ativos: {ativos} 🟢")
    print(f"  - Não encontrados: {nao_encontrados} ⚠️")
    print()

    # Valores
    valor_total_sistema = sum(float(p.valor_total or 0) for p in pedidos)
    valor_cancelados = sum(float(p.valor_total or 0) for p in pedidos if status_odoo.get(p.num_pedido) == 'cancel')

    print(f"Valores:")
    print(f"  - Total no sistema: R$ {valor_total_sistema:,.2f}")
    print(f"  - Cancelados no Odoo: R$ {valor_cancelados:,.2f}")
    print()

    print("=" * 120)
    print()


def main():
    parser = argparse.ArgumentParser(
        description='Verifica e exclui pedidos cancelados no Odoo'
    )

    parser.add_argument(
        '--auto-confirmar',
        action='store_true',
        help='⚠️ CUIDADO: Exclui automaticamente sem pedir confirmação'
    )

    parser.add_argument(
        '--apenas-listar',
        action='store_true',
        help='Apenas lista os pedidos cancelados sem oferecer exclusão'
    )

    args = parser.parse_args()

    app = create_app()

    with app.app_context():
        try:
            # 1. Buscar pedidos com saldo no sistema
            pedidos = buscar_pedidos_com_saldo()

            if not pedidos:
                logger.info("✅ Nenhum pedido com saldo encontrado no sistema")
                return

            # 2. Conectar ao Odoo
            logger.info("🔌 Conectando ao Odoo...")
            connection = get_odoo_connection()

            if not connection:
                logger.error("❌ Não foi possível conectar ao Odoo")
                return

            # 3. Verificar status no Odoo
            status_odoo = verificar_status_odoo(connection, pedidos)

            # 4. Gerar relatório
            gerar_relatorio(pedidos, status_odoo)

            # 5. Exibir pedidos cancelados
            pedidos_cancelados = exibir_pedidos_cancelados(pedidos, status_odoo)

            # 6. Oferecer exclusão (se não for apenas listar)
            if not args.apenas_listar and pedidos_cancelados:
                print()
                excluir_pedidos_cancelados(pedidos_cancelados, auto_confirmar=args.auto_confirmar)
            elif args.apenas_listar:
                logger.info("ℹ️  Modo apenas listar - exclusão não oferecida")

        except KeyboardInterrupt:
            print("\n\n👋 Operação cancelada pelo usuário")
            sys.exit(0)

        except Exception as e:
            logger.error(f"\n❌ Erro: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
