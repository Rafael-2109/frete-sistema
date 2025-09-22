#!/usr/bin/env python3
"""
Script para Buscar NF Diretamente no Odoo e Importar
=====================================================

Busca uma NF específica no Odoo e tenta importar para o sistema.

Autor: Sistema de Fretes
Data: 21/09/2025
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from datetime import datetime, timedelta
from decimal import Decimal

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def buscar_e_importar_nf(numero_nf):
    """Busca NF no Odoo e importa para o sistema"""
    from app import create_app, db
    from app.faturamento.models import FaturamentoProduto
    from app.odoo.utils.safe_connection import get_safe_odoo_connection
    from app.odoo.utils.faturamento_mapper import FaturamentoMapper

    app = create_app()

    with app.app_context():
        try:
            logger.info("=" * 80)
            logger.info(f"🔍 BUSCANDO NF {numero_nf} DIRETAMENTE NO ODOO")
            logger.info("=" * 80)

            # Conectar ao Odoo
            odoo = get_safe_odoo_connection()
            mapper = FaturamentoMapper()

            # 1. Buscar a NF no Odoo usando diferentes estratégias
            logger.info("\n📊 ESTRATÉGIA 1: Buscar por nome exato")
            logger.info("-" * 60)

            # Tentar buscar account.move com nome exato
            domain = [
                ['name', '=', str(numero_nf)],
                ['move_type', 'in', ['out_invoice', 'out_refund']],
                ['state', 'in', ['posted', 'cancel']]
            ]

            logger.info(f"Domain: {domain}")

            invoices = odoo.search_read_safe(
                'account.move',
                domain,
                fields=['id', 'name', 'invoice_date', 'partner_id', 'amount_total', 'state', 'invoice_origin', 'write_date'],
                limit=10
            )

            if not invoices:
                # Tentar com ILIKE
                logger.info("\n📊 ESTRATÉGIA 2: Buscar com ILIKE")
                domain = [
                    ['name', 'ilike', str(numero_nf)],
                    ['move_type', 'in', ['out_invoice', 'out_refund']]
                ]
                invoices = odoo.search_read_safe(
                    'account.move',
                    domain,
                    fields=['id', 'name', 'invoice_date', 'partner_id', 'amount_total', 'state', 'invoice_origin', 'write_date'],
                    limit=10
                )

            if not invoices:
                # Tentar sem prefixo/sufixo
                logger.info("\n📊 ESTRATÉGIA 3: Buscar sem prefixo/sufixo")
                domain = [
                    ['name', 'ilike', f'%{numero_nf}%'],
                    ['move_type', 'in', ['out_invoice', 'out_refund']]
                ]
                invoices = odoo.search_read_safe(
                    'account.move',
                    domain,
                    fields=['id', 'name', 'invoice_date', 'partner_id', 'amount_total', 'state', 'invoice_origin', 'write_date'],
                    limit=10
                )

            if invoices:
                logger.info(f"✅ ENCONTRADA! {len(invoices)} fatura(s)")

                for inv in invoices:
                    logger.info(f"\n📋 Fatura: {inv.get('name')}")
                    logger.info(f"   ID Odoo: {inv.get('id')}")
                    logger.info(f"   Data: {inv.get('invoice_date')}")
                    logger.info(f"   Cliente: {inv.get('partner_id')}")
                    logger.info(f"   Valor: R$ {inv.get('amount_total', 0):,.2f}")
                    logger.info(f"   Estado: {inv.get('state')}")
                    logger.info(f"   Origem: {inv.get('invoice_origin')}")
                    logger.info(f"   Última modificação: {inv.get('write_date')}")

                    # Buscar linhas da invoice
                    invoice_id = inv['id']
                    logger.info(f"\n📦 Buscando produtos da NF {inv.get('name')}...")

                    lines_domain = [
                        ['move_id', '=', invoice_id],
                        ['product_id', '!=', False],
                        ['exclude_from_invoice_tab', '=', False]
                    ]

                    lines = odoo.search_read_safe(
                        'account.move.line',
                        lines_domain,
                        fields=['product_id', 'name', 'quantity', 'price_unit', 'price_subtotal']
                    )

                    if lines:
                        logger.info(f"   Encontrados {len(lines)} produtos")

                        # Verificar se já existe no banco
                        for line in lines[:5]:  # Mostrar até 5 produtos
                            produto_info = line.get('product_id')
                            if produto_info:
                                if isinstance(produto_info, (list, tuple)):
                                    cod_produto = str(produto_info[0])
                                    nome_produto = produto_info[1] if len(produto_info) > 1 else 'Desconhecido'
                                else:
                                    cod_produto = str(produto_info)
                                    nome_produto = 'Desconhecido'

                                logger.info(f"   - Produto {cod_produto}: {nome_produto}")
                                logger.info(f"     Qtd: {line.get('quantity', 0)}, Preço: R$ {line.get('price_unit', 0):,.2f}")

                                # Verificar se já existe
                                existe = FaturamentoProduto.query.filter_by(
                                    numero_nf=str(inv.get('name')),
                                    cod_produto=cod_produto
                                ).first()

                                if existe:
                                    logger.info(f"     ⚠️ Já existe no banco local!")
                                else:
                                    logger.info(f"     ✅ NÃO existe no banco - pode ser importado")

                        # Perguntar se deseja importar
                        if inv.get('state') == 'posted':
                            resposta = input(f"\n⚠️ Deseja importar a NF {inv.get('name')}? (s/N): ")
                            if resposta.strip().lower() in ['s', 'sim', 'y', 'yes']:
                                logger.info("\n🔄 Processando importação...")

                                # Mapear e importar
                                resultado_mapeamento = mapper.mapear_faturamento([inv])

                                if resultado_mapeamento['sucesso']:
                                    dados_mapeados = resultado_mapeamento['dados']
                                    logger.info(f"✅ {len(dados_mapeados)} itens mapeados")

                                    # Processar cada item
                                    novos = 0
                                    atualizados = 0

                                    for item in dados_mapeados:
                                        existe = FaturamentoProduto.query.filter_by(
                                            numero_nf=item['numero_nf'],
                                            cod_produto=item['cod_produto']
                                        ).first()

                                        if not existe:
                                            novo = FaturamentoProduto(**item)
                                            db.session.add(novo)
                                            novos += 1
                                        else:
                                            # Atualizar apenas status
                                            existe.status_nf = item.get('status_nf', 'Lançado')
                                            existe.updated_at = datetime.now()
                                            atualizados += 1

                                    db.session.commit()
                                    logger.info(f"✅ Importação concluída: {novos} novos, {atualizados} atualizados")
                                else:
                                    logger.error(f"❌ Erro no mapeamento: {resultado_mapeamento.get('erro')}")
                        else:
                            logger.warning(f"⚠️ NF com estado '{inv.get('state')}' - não será importada automaticamente")

            else:
                logger.warning(f"❌ NF {numero_nf} NÃO encontrada no Odoo")

                # Buscar algumas NFs recentes para debug
                logger.info("\n🔍 Buscando NFs recentes para referência...")

                recent_domain = [
                    ['invoice_date', '>=', '2025-09-01'],
                    ['invoice_date', '<=', '2025-09-21'],
                    ['move_type', 'in', ['out_invoice', 'out_refund']],
                    ['state', '=', 'posted']
                ]

                recent_invoices = odoo.search_read_safe(
                    'account.move',
                    recent_domain,
                    fields=['name', 'invoice_date', 'amount_total', 'state'],
                    limit=10
                )

                if recent_invoices:
                    logger.info(f"Exemplos de NFs recentes encontradas:")
                    for inv in recent_invoices[:5]:
                        logger.info(f"   - {inv.get('name')} ({inv.get('invoice_date')}) - R$ {inv.get('amount_total', 0):,.2f}")

            return True

        except Exception as e:
            logger.error(f"❌ Erro: {e}")
            import traceback
            traceback.print_exc()
            return False


def main():
    """Função principal"""

    # NF padrão ou receber como argumento
    numero_nf = sys.argv[1] if len(sys.argv) > 1 else "139191"

    buscar_e_importar_nf(numero_nf)

    return 0


if __name__ == '__main__':
    sys.exit(main())