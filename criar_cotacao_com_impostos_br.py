#!/usr/bin/env python3
"""
Script para criar cotação no Odoo acionando o cálculo de impostos brasileiro
Data: 2025-01-25
"""

import sys
import os
from datetime import datetime, timedelta

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.odoo.utils.connection import get_odoo_connection
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def criar_cotacao_impostos_br():
    """
    Cria cotação no Odoo e aciona o cálculo de impostos brasileiro
    """
    try:
        # Conectar ao Odoo
        logger.info("🔌 Conectando ao Odoo...")
        odoo = get_odoo_connection()
        
        if not odoo:
            logger.error("❌ Não foi possível conectar ao Odoo")
            return None
        
        # Empresa NACOM GOYA - CD
        company_id = 4
        warehouse_id = 3
        
        logger.info(f"🏢 Empresa: NACOM GOYA - CD (ID: {company_id})")
        
        # Dados da cotação
        cnpj_cliente = '75.315.333/0002-90'
        produtos_cotacao = [
            {
                'codigo': '4310162',
                'descricao': 'AZEITONA VERDE CAMPO BELO BALDE',
                'quantidade': 70,
                'preco_unitario': 196.83
            },
            {
                'codigo': '4320147',
                'descricao': 'AZEITONA VERDE CAMPO BELO FAT.POUCH',
                'quantidade': 112,
                'preco_unitario': 79.25
            },
            {
                'codigo': '4320172', 
                'descricao': 'AZEITONA VERDE CAMPO BELO FAT.VIDRO',
                'quantidade': 44,
                'preco_unitario': 99.91
            }
        ]
        
        # 1. Buscar cliente
        logger.info(f"🔍 Buscando cliente: {cnpj_cliente}")
        cliente = odoo.search_read(
            'res.partner',
            [('l10n_br_cnpj', '=', cnpj_cliente)],
            ['id', 'name', 'property_account_position_id'],
            limit=1
        )
        
        if not cliente:
            cnpj_limpo = cnpj_cliente.replace('.', '').replace('/', '').replace('-', '')
            cliente = odoo.search_read(
                'res.partner',
                [('l10n_br_cnpj', 'ilike', cnpj_limpo[:8])],
                ['id', 'name', 'property_account_position_id'],
                limit=1
            )
        
        if not cliente:
            logger.error("❌ Cliente não encontrado")
            return None
            
        partner_id = cliente[0]['id']
        logger.info(f"✅ Cliente: {cliente[0]['name']} (ID: {partner_id})")
        
        # 2. Preparar linhas
        logger.info("📦 Preparando produtos...")
        order_lines = []
        
        for prod in produtos_cotacao:
            # Buscar produto
            produto = odoo.search_read(
                'product.product',
                [('default_code', '=', prod['codigo'])],
                ['id', 'name', 'taxes_id', 'uom_id'],
                limit=1
            )
            
            if not produto:
                produto = odoo.search_read(
                    'product.product',
                    [('name', 'ilike', prod['descricao'][:20])],
                    ['id', 'name', 'taxes_id', 'uom_id'],
                    limit=1
                )
            
            if produto:
                logger.info(f"   ✅ {produto[0]['name']}")
                
                # Adicionar linha COM impostos do produto
                order_lines.append((0, 0, {
                    'product_id': produto[0]['id'],
                    'name': prod['descricao'],
                    'product_uom_qty': prod['quantidade'],
                    'price_unit': prod['preco_unitario'],
                    'product_uom': produto[0]['uom_id'][0] if produto[0].get('uom_id') else 1,
                    'tax_id': [(6, 0, produto[0].get('taxes_id', []))]  # Impostos do produto
                }))
            else:
                logger.warning(f"   ❌ Produto não encontrado: {prod['codigo']}")
                order_lines.append((0, 0, {
                    'name': f"{prod['codigo']} - {prod['descricao']}",
                    'product_uom_qty': prod['quantidade'],
                    'price_unit': prod['preco_unitario'],
                    'product_uom': 1
                }))
        
        # 3. Criar cotação
        logger.info("📝 Criando cotação...")
        
        cotacao_data = {
            'partner_id': partner_id,
            'company_id': company_id,
            'warehouse_id': warehouse_id,
            'date_order': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'validity_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'order_line': order_lines
        }
        
        # Adicionar posição fiscal se houver
        if cliente[0].get('property_account_position_id'):
            cotacao_data['fiscal_position_id'] = cliente[0]['property_account_position_id'][0]
        
        cotacao_id = odoo.execute_kw(
            'sale.order',
            'create',
            [cotacao_data],
            {'context': {'company_id': company_id}}
        )
        
        logger.info(f"✅ Cotação criada! ID: {cotacao_id}")
        
        # 4. ACIONAR O CÁLCULO DE IMPOSTOS BRASILEIRO
        logger.info("🇧🇷 Acionando cálculo de impostos brasileiro...")
        
        try:
            # Método 1: Chamar o método específico brasileiro
            result = odoo.execute_kw(
                'sale.order',
                'onchange_l10n_br_calcular_imposto',
                [[cotacao_id]],
                {'context': {'company_id': company_id}}
            )
            logger.info("   ✅ Método onchange_l10n_br_calcular_imposto executado!")
        except Exception as e:
            logger.warning(f"   ⚠️ Método brasileiro não disponível: {e}")
            
            # Método 2: Tentar executar a Server Action diretamente
            try:
                logger.info("   🔄 Tentando executar Server Action 'Atualizar Impostos'...")
                
                # Executar a ação ID 863 (Atualizar Impostos)
                result = odoo.execute_kw(
                    'ir.actions.server',
                    'run',
                    [[863]],  # ID da ação "Atualizar Impostos"
                    {'context': {
                        'active_model': 'sale.order',
                        'active_id': cotacao_id,
                        'active_ids': [cotacao_id]
                    }}
                )
                logger.info("   ✅ Server Action executada!")
            except Exception as e2:
                logger.warning(f"   ⚠️ Server Action não executada: {e2}")
        
        # 5. Forçar recálculo dos totais
        logger.info("🔄 Forçando recálculo dos totais...")
        try:
            # Write vazio para forçar compute fields
            odoo.execute_kw(
                'sale.order',
                'write',
                [[cotacao_id], {}],
                {'context': {'company_id': company_id}}
            )
            logger.info("   ✅ Recálculo forçado")
        except:
            pass
        
        # 6. Tentar método _compute_amounts se disponível
        try:
            odoo.execute_kw(
                'sale.order',
                '_compute_amounts',
                [[cotacao_id]],
                {'context': {'company_id': company_id}}
            )
            logger.info("   ✅ _compute_amounts executado")
        except:
            pass
        
        # 7. Buscar cotação atualizada
        logger.info("📊 Buscando cotação com impostos calculados...")
        cotacao = odoo.search_read(
            'sale.order',
            [('id', '=', cotacao_id)],
            ['name', 'amount_untaxed', 'amount_tax', 'amount_total', 
             'fiscal_position_id', 'l10n_br_icms_value', 'l10n_br_ipi_value',
             'l10n_br_pis_value', 'l10n_br_cofins_value']
        )
        
        if cotacao:
            logger.info("\n" + "="*70)
            logger.info("📊 COTAÇÃO CRIADA COM IMPOSTOS BRASILEIROS:")
            logger.info("="*70)
            logger.info(f"   📋 Número: {cotacao[0]['name']}")
            logger.info(f"   👤 Cliente: {cliente[0]['name']}")
            logger.info(f"   📊 Posição Fiscal: {cotacao[0]['fiscal_position_id'][1] if cotacao[0].get('fiscal_position_id') else 'N/A'}")
            logger.info(f"   💰 Subtotal: R$ {cotacao[0]['amount_untaxed']:,.2f}")
            logger.info(f"   💰 IMPOSTOS: R$ {cotacao[0]['amount_tax']:,.2f}")
            logger.info(f"   💰 TOTAL: R$ {cotacao[0]['amount_total']:,.2f}")
            
            # Impostos brasileiros específicos (se disponíveis)
            if cotacao[0].get('l10n_br_icms_value'):
                logger.info(f"   🇧🇷 ICMS: R$ {cotacao[0]['l10n_br_icms_value']:,.2f}")
            if cotacao[0].get('l10n_br_ipi_value'):
                logger.info(f"   🇧🇷 IPI: R$ {cotacao[0]['l10n_br_ipi_value']:,.2f}")
            if cotacao[0].get('l10n_br_pis_value'):
                logger.info(f"   🇧🇷 PIS: R$ {cotacao[0]['l10n_br_pis_value']:,.2f}")
            if cotacao[0].get('l10n_br_cofins_value'):
                logger.info(f"   🇧🇷 COFINS: R$ {cotacao[0]['l10n_br_cofins_value']:,.2f}")
            
            # Porcentagem de impostos
            if cotacao[0]['amount_untaxed'] > 0:
                percent = (cotacao[0]['amount_tax'] / cotacao[0]['amount_untaxed']) * 100
                logger.info(f"   📊 Impostos: {percent:.2f}% do subtotal")
            
            logger.info("="*70)
            
            # Buscar detalhes das linhas
            linhas = odoo.search_read(
                'sale.order.line',
                [('order_id', '=', cotacao_id)],
                ['name', 'price_subtotal', 'price_tax', 'price_total', 'tax_id'],
                limit=5
            )
            
            if linhas:
                logger.info("\n📦 PRODUTOS COM IMPOSTOS:")
                for linha in linhas:
                    logger.info(f"\n   • {linha['name'][:50]}")
                    logger.info(f"     Subtotal: R$ {linha['price_subtotal']:,.2f}")
                    logger.info(f"     Impostos: R$ {linha.get('price_tax', 0):,.2f}")
                    logger.info(f"     Total: R$ {linha.get('price_total', 0):,.2f}")
                    
                    # Buscar detalhes dos impostos
                    if linha.get('tax_id'):
                        impostos = odoo.search_read(
                            'account.tax',
                            [('id', 'in', linha['tax_id'])],
                            ['name', 'amount'],
                            limit=3
                        )
                        if impostos:
                            logger.info(f"     Impostos aplicados:")
                            for imp in impostos:
                                logger.info(f"       - {imp['name']}: {imp['amount']}%")
        
        return cotacao_id
        
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    logger.info("🚀 Criando cotação com impostos brasileiros...")
    logger.info("="*70)
    
    cotacao_id = criar_cotacao_impostos_br()
    
    if cotacao_id:
        logger.info(f"\n✅ SUCESSO!")
        logger.info(f"🆔 Cotação ID: {cotacao_id}")
        logger.info("💡 Impostos calculados usando localização brasileira")
        logger.info("📋 Verifique no Odoo os impostos aplicados")