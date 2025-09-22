#!/usr/bin/env python3
"""
Script para Verificar NF Específica no Sistema e no Odoo
========================================================

Verifica se uma NF específica existe no banco local e busca no Odoo.

Autor: Sistema de Fretes
Data: 21/09/2025
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import logging
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def verificar_nf_local(numero_nf):
    """Verifica se NF existe no banco local"""
    from app import create_app, db
    from app.faturamento.models import FaturamentoProduto, RelatorioFaturamentoImportado
    from app.separacao.models import Separacao

    app = create_app()

    with app.app_context():
        logger.info("=" * 80)
        logger.info(f"🔍 VERIFICANDO NF {numero_nf} NO BANCO LOCAL")
        logger.info("=" * 80)

        # Verificar em FaturamentoProduto
        logger.info("\n📊 1. VERIFICANDO EM FaturamentoProduto:")
        logger.info("-" * 60)

        produtos_nf = FaturamentoProduto.query.filter_by(numero_nf=str(numero_nf)).all()

        if produtos_nf:
            logger.info(f"✅ ENCONTRADA! {len(produtos_nf)} produto(s) na NF {numero_nf}")
            for prod in produtos_nf:
                logger.info(f"   Produto: {prod.cod_produto} - {prod.nome_produto}")
                logger.info(f"   Quantidade: {prod.qtd_produto_faturado}")
                logger.info(f"   Origem (pedido): {prod.origem}")
                logger.info(f"   Status: {prod.status_nf}")
                logger.info(f"   Data fatura: {prod.data_fatura}")
                logger.info(f"   Criado em: {prod.created_at}")
                logger.info("-" * 40)
        else:
            logger.warning(f"❌ NF {numero_nf} NÃO encontrada em FaturamentoProduto")

        # Verificar em RelatorioFaturamentoImportado
        logger.info("\n📊 2. VERIFICANDO EM RelatorioFaturamentoImportado:")
        logger.info("-" * 60)

        relatorio = RelatorioFaturamentoImportado.query.filter_by(numero_nf=str(numero_nf)).first()

        if relatorio:
            logger.info(f"✅ ENCONTRADA em RelatorioFaturamentoImportado!")
            logger.info(f"   Cliente: {relatorio.nome_cliente}")
            logger.info(f"   Data: {relatorio.data_fatura}")
            logger.info(f"   Valor: R$ {relatorio.valor_total:,.2f}")
            logger.info(f"   Origem: {relatorio.origem}")
            logger.info(f"   Ativo: {relatorio.ativo}")
        else:
            logger.warning(f"❌ NF {numero_nf} NÃO encontrada em RelatorioFaturamentoImportado")

        # Verificar em Separacao
        logger.info("\n📊 3. VERIFICANDO EM Separacao:")
        logger.info("-" * 60)

        separacoes = Separacao.query.filter_by(numero_nf=str(numero_nf)).all()

        if separacoes:
            logger.info(f"✅ ENCONTRADA em {len(separacoes)} separação(ões)!")
            for sep in separacoes[:5]:  # Mostrar até 5
                logger.info(f"   Pedido: {sep.num_pedido}")
                logger.info(f"   Produto: {sep.cod_produto}")
                logger.info(f"   Sincronizado NF: {sep.sincronizado_nf}")
                logger.info("-" * 40)
        else:
            logger.warning(f"❌ NF {numero_nf} NÃO encontrada em Separacao")

        return bool(produtos_nf)


def buscar_nf_odoo(numero_nf):
    """Busca NF diretamente no Odoo"""
    from app import create_app
    from app.odoo.services.faturamento_service import FaturamentoService
    import xmlrpc.client

    app = create_app()

    with app.app_context():
        logger.info("\n" + "=" * 80)
        logger.info(f"🔍 BUSCANDO NF {numero_nf} NO ODOO")
        logger.info("=" * 80)

        try:
            # Configurar conexão Odoo
            service = FaturamentoService()

            # Buscar configurações
            odoo_url = os.getenv('ODOO_URL', 'https://erp.semprefruta.com.br')
            odoo_db = os.getenv('ODOO_DB', 'erp')
            odoo_username = os.getenv('ODOO_USERNAME')
            odoo_password = os.getenv('ODOO_PASSWORD')

            if not all([odoo_username, odoo_password]):
                logger.error("❌ Credenciais Odoo não configuradas")
                return None

            # Conectar ao Odoo
            common = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/common')
            uid = common.authenticate(odoo_db, odoo_username, odoo_password, {})

            if not uid:
                logger.error("❌ Falha na autenticação Odoo")
                return None

            models = xmlrpc.client.ServerProxy(f'{odoo_url}/xmlrpc/2/object')

            # Buscar invoice pelo número
            logger.info(f"Buscando invoice com number = {numero_nf}...")

            # Primeiro tentar account.move (Odoo 13+)
            invoice_ids = models.execute_kw(
                odoo_db, uid, odoo_password,
                'account.move', 'search',
                [[
                    ['name', '=', str(numero_nf)],
                    ['move_type', 'in', ['out_invoice', 'out_refund']]
                ]],
                {'limit': 10}
            )

            if not invoice_ids:
                # Tentar buscar com LIKE
                invoice_ids = models.execute_kw(
                    odoo_db, uid, odoo_password,
                    'account.move', 'search',
                    [[
                        ['name', 'ilike', str(numero_nf)],
                        ['move_type', 'in', ['out_invoice', 'out_refund']]
                    ]],
                    {'limit': 10}
                )

            if invoice_ids:
                logger.info(f"✅ ENCONTRADA no Odoo! IDs: {invoice_ids}")

                # Buscar detalhes
                invoices = models.execute_kw(
                    odoo_db, uid, odoo_password,
                    'account.move', 'read',
                    [invoice_ids],
                    {'fields': ['name', 'invoice_date', 'partner_id', 'amount_total', 'state', 'invoice_origin']}
                )

                for inv in invoices:
                    logger.info("\n📋 Detalhes da NF no Odoo:")
                    logger.info(f"   Número: {inv.get('name')}")
                    logger.info(f"   Data: {inv.get('invoice_date')}")
                    logger.info(f"   Cliente: {inv.get('partner_id')}")
                    logger.info(f"   Valor: R$ {inv.get('amount_total', 0):,.2f}")
                    logger.info(f"   Status: {inv.get('state')}")
                    logger.info(f"   Origem: {inv.get('invoice_origin')}")

                # Buscar linhas da invoice
                logger.info("\n📦 Buscando produtos da NF...")

                lines = models.execute_kw(
                    odoo_db, uid, odoo_password,
                    'account.move.line', 'search_read',
                    [[['move_id', 'in', invoice_ids], ['product_id', '!=', False]]],
                    {'fields': ['product_id', 'name', 'quantity', 'price_unit']}
                )

                if lines:
                    logger.info(f"Encontrados {len(lines)} produtos:")
                    for line in lines:
                        logger.info(f"   - {line.get('product_id')[1] if line.get('product_id') else 'N/A'}")
                        logger.info(f"     Qtd: {line.get('quantity')}, Preço: R$ {line.get('price_unit', 0):,.2f}")

                return True
            else:
                logger.warning(f"❌ NF {numero_nf} NÃO encontrada no Odoo")

                # Tentar buscar em período específico
                logger.info("\n🔍 Tentando buscar NFs no período de 01/07 a 21/09...")

                invoice_ids = models.execute_kw(
                    odoo_db, uid, odoo_password,
                    'account.move', 'search',
                    [[
                        ['invoice_date', '>=', '2025-07-01'],
                        ['invoice_date', '<=', '2025-09-21'],
                        ['move_type', 'in', ['out_invoice', 'out_refund']],
                        ['state', 'in', ['posted', 'cancel']]
                    ]],
                    {'limit': 5}
                )

                if invoice_ids:
                    invoices = models.execute_kw(
                        odoo_db, uid, odoo_password,
                        'account.move', 'read',
                        [invoice_ids[:5]],
                        {'fields': ['name', 'invoice_date', 'state']}
                    )

                    logger.info(f"Exemplos de NFs encontradas no período:")
                    for inv in invoices:
                        logger.info(f"   - {inv.get('name')} ({inv.get('invoice_date')}) - {inv.get('state')}")

                return False

        except Exception as e:
            logger.error(f"❌ Erro ao buscar no Odoo: {e}")
            import traceback
            traceback.print_exc()
            return None


def main():
    """Função principal"""

    # NF padrão ou receber como argumento
    numero_nf = sys.argv[1] if len(sys.argv) > 1 else "139191"

    logger.info("=" * 80)
    logger.info(f"🔍 VERIFICAÇÃO COMPLETA DA NF {numero_nf}")
    logger.info("=" * 80)

    # Verificar localmente
    existe_local = verificar_nf_local(numero_nf)

    # Buscar no Odoo
    existe_odoo = buscar_nf_odoo(numero_nf)

    # Resumo
    logger.info("\n" + "=" * 80)
    logger.info("📊 RESUMO DA VERIFICAÇÃO")
    logger.info("=" * 80)
    logger.info(f"NF {numero_nf}:")
    logger.info(f"   Banco Local: {'✅ EXISTE' if existe_local else '❌ NÃO EXISTE'}")
    logger.info(f"   Odoo: {'✅ EXISTE' if existe_odoo else '❌ NÃO EXISTE' if existe_odoo is False else '⚠️ ERRO NA BUSCA'}")

    if existe_odoo and not existe_local:
        logger.warning("\n⚠️ NF existe no Odoo mas NÃO foi importada!")
        logger.warning("Possíveis causas:")
        logger.warning("1. NF fora do período de sincronização")
        logger.warning("2. NF com status que não é importado")
        logger.warning("3. Erro durante importação")
        logger.warning("4. Filtro de data ou status impedindo importação")

    return 0


if __name__ == '__main__':
    sys.exit(main())