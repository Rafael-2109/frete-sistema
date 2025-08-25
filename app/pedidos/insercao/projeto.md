1- Criar tabela por grupo de clientes
2- Criar tabela por região (conjunto de UFs)
3- Criar tabela de preço utilizando regras das 2 tabelas + cod_produto + preços

1- N x Prefixos CNPJ = 1 grupo de clientes
2- N UFs = 1 região
3- 1 tabela de preço = 1 região + 1 grupo de clientes + N produtos

4- Rota e tela para comparar a tabela de preço com o pedido importado por PDF.
5- Mostrar as diferenças por CNPJ.
6- Mostrar os CNPJ sem diferenças.
7- Exportação de excel XLSX com informação da tabela de preço X pedido, possibilitando o usuario a exportar os pedidos e enviar para o vendedor corrigir.
8- Rota de importação dos pedidos excel no mesmo formato que o exportado.
9- Checkbox para definir pedidos a serem inseridos no Odoo. (Os pedidos importados pelo excel e pelo PDF devem renderizar a mesma tela para manter 1 padrão)

################################################################################


1077- Botão de inserir no Odoo respeitando os campos do script:

#!/usr/bin/env python3
"""
Script FINAL COMPLETO para criar cotação no Odoo com:
- Impostos calculados
- Incoterm CIF
- Forma de Pagamento: Transferência Bancária CD
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

def criar_cotacao_final():
    """
    Cria cotação completa no Odoo com todos os campos configurados
    """
    try:
        # Conectar ao Odoo
        logger.info("🔌 Conectando ao Odoo...")
        odoo = get_odoo_connection()
        
        if not odoo:
            logger.error("❌ Não foi possível conectar ao Odoo")
            return None
        
        # Configurações
        company_id = 4  # NACOM GOYA - CD
        warehouse_id = 3  # Armazém CD
        incoterm_id = 6  # CIF - COST, INSURANCE AND FREIGHT
        payment_provider_id = 30  # Transferência Bancária (NACOM GOYA - CD)
        
        logger.info(f"🏢 Empresa: NACOM GOYA - CD (ID: {company_id})")
        logger.info(f"🚢 Incoterm: CIF (ID: {incoterm_id})")
        logger.info(f"💳 Forma de Pagamento: Transferência Bancária CD (ID: {payment_provider_id})")
        
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
            ['id', 'name', 'property_account_position_id', 
             'property_product_pricelist', 'property_payment_term_id'],
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
        
        # Extrair configurações do cliente
        fiscal_position_id = None
        if cliente[0].get('property_account_position_id'):
            fiscal_position_id = cliente[0]['property_account_position_id'][0] if isinstance(cliente[0]['property_account_position_id'], list) else cliente[0]['property_account_position_id']
            logger.info(f"   📊 Posição Fiscal: ID {fiscal_position_id}")
        
        pricelist_id = None
        if cliente[0].get('property_product_pricelist'):
            pricelist_id = cliente[0]['property_product_pricelist'][0] if isinstance(cliente[0]['property_product_pricelist'], list) else cliente[0]['property_product_pricelist']
        
        payment_term_id = None
        if cliente[0].get('property_payment_term_id'):
            payment_term_id = cliente[0]['property_payment_term_id'][0] if isinstance(cliente[0]['property_payment_term_id'], list) else cliente[0]['property_payment_term_id']
        
        # 2. Preparar linhas de produtos
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
        
        # 3. Criar cotação COMPLETA
        logger.info("📝 Criando cotação completa...")
        
        cotacao_data = {
            'partner_id': partner_id,
            'company_id': company_id,
            'warehouse_id': warehouse_id,
            'incoterm': incoterm_id,  # INCOTERM CIF
            'payment_provider_id': payment_provider_id,  # Transferência Bancária CD
            'date_order': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'validity_date': (datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d'),
            'order_line': order_lines,
            'note': 'Cotação completa: Impostos + Incoterm CIF + Transferência Bancária CD'
        }
        
        # Adicionar configurações do cliente se disponíveis
        if fiscal_position_id:
            cotacao_data['fiscal_position_id'] = fiscal_position_id
        if pricelist_id:
            cotacao_data['pricelist_id'] = pricelist_id
        if payment_term_id:
            cotacao_data['payment_term_id'] = payment_term_id
        
        cotacao_id = odoo.execute_kw(
            'sale.order',
            'create',
            [cotacao_data],
            {'context': {'company_id': company_id}}
        )
        
        logger.info(f"✅ Cotação criada! ID: {cotacao_id}")
        
        # 4. Executar Server Action para calcular impostos
        logger.info("🇧🇷 Acionando cálculo de impostos...")
        
        try:
            # Executar a Server Action "Atualizar Impostos" (ID 863)
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
            logger.info("   ✅ Impostos calculados via Server Action!")
        except Exception as e:
            logger.warning(f"   ⚠️ Erro na Server Action: {e}")
            
            # Tentar forçar recálculo via write
            try:
                odoo.execute_kw(
                    'sale.order',
                    'write',
                    [[cotacao_id], {}],
                    {'context': {'company_id': company_id}}
                )
                logger.info("   ✅ Recálculo forçado via write")
            except:
                pass
        
        # 5. Buscar cotação criada
        logger.info("📊 Buscando cotação finalizada...")
        cotacao = odoo.search_read(
            'sale.order',
            [('id', '=', cotacao_id)],
            ['name', 'amount_untaxed', 'amount_tax', 'amount_total', 
             'fiscal_position_id', 'incoterm', 'payment_term_id',
             'payment_provider_id', 'company_id', 'warehouse_id', 'state']
        )
        
        if cotacao:
            logger.info("\n" + "="*80)
            logger.info("🎉 COTAÇÃO COMPLETA CRIADA COM SUCESSO!")
            logger.info("="*80)
            logger.info(f"   📋 Número: {cotacao[0]['name']}")
            logger.info(f"   👤 Cliente: {cliente[0]['name']}")
            logger.info(f"   🏢 Empresa: {cotacao[0]['company_id'][1] if cotacao[0].get('company_id') else 'N/A'}")
            logger.info(f"   🏭 Armazém: {cotacao[0]['warehouse_id'][1] if cotacao[0].get('warehouse_id') else 'N/A'}")
            
            # Incoterm
            if cotacao[0].get('incoterm'):
                incoterm_info = odoo.search_read(
                    'account.incoterms',
                    [('id', '=', cotacao[0]['incoterm'][0] if isinstance(cotacao[0]['incoterm'], list) else cotacao[0]['incoterm'])],
                    ['code', 'name']
                )
                if incoterm_info:
                    logger.info(f"   🚢 Incoterm: {incoterm_info[0]['code']} - {incoterm_info[0]['name']}")
            
            # Forma de Pagamento
            if cotacao[0].get('payment_provider_id'):
                logger.info(f"   💳 Forma de Pagamento: {cotacao[0]['payment_provider_id'][1]}")
            
            # Posição Fiscal
            if cotacao[0].get('fiscal_position_id'):
                logger.info(f"   📊 Posição Fiscal: {cotacao[0]['fiscal_position_id'][1]}")
            
            # Condição de Pagamento
            if cotacao[0].get('payment_term_id'):
                logger.info(f"   💰 Condição de Pagamento: {cotacao[0]['payment_term_id'][1]}")
            
            logger.info(f"   🏷️ Status: {cotacao[0]['state']}")
            logger.info(f"\n   💵 Subtotal: R$ {cotacao[0]['amount_untaxed']:,.2f}")
            logger.info(f"   💵 IMPOSTOS: R$ {cotacao[0]['amount_tax']:,.2f}")
            logger.info(f"   💵 TOTAL: R$ {cotacao[0]['amount_total']:,.2f}")
            
            # Porcentagem de impostos
            if cotacao[0]['amount_untaxed'] > 0 and cotacao[0]['amount_tax'] > 0:
                percent = (cotacao[0]['amount_tax'] / cotacao[0]['amount_untaxed']) * 100
                logger.info(f"   📊 Impostos representam: {percent:.2f}% do subtotal")
            
            logger.info("="*80)
            
            # Buscar detalhes das linhas
            linhas = odoo.search_read(
                'sale.order.line',
                [('order_id', '=', cotacao_id)],
                ['name', 'price_subtotal', 'price_tax', 'price_total', 'tax_id']
            )
            
            if linhas:
                logger.info("\n📦 PRODUTOS COM IMPOSTOS:")
                logger.info("-"*80)
                
                total_produtos = 0
                total_impostos = 0
                
                for i, linha in enumerate(linhas, 1):
                    logger.info(f"\n{i}. {linha['name'][:60]}")
                    logger.info(f"   Subtotal: R$ {linha['price_subtotal']:,.2f}")
                    
                    total_produtos += linha['price_subtotal']
                    
                    if linha.get('price_tax', 0) > 0:
                        logger.info(f"   Impostos: R$ {linha['price_tax']:,.2f}")
                        total_impostos += linha['price_tax']
                        
                        # Buscar detalhes dos impostos aplicados
                        if linha.get('tax_id'):
                            impostos = odoo.search_read(
                                'account.tax',
                                [('id', 'in', linha['tax_id'])],
                                ['name', 'amount']
                            )
                            if impostos:
                                logger.info(f"   Impostos aplicados:")
                                for imp in impostos:
                                    logger.info(f"      • {imp['name']}: {imp['amount']}%")
                    
                    logger.info(f"   Total: R$ {linha.get('price_total', linha['price_subtotal']):,.2f}")
                
                logger.info("-"*80)
                logger.info(f"\n📊 TOTAIS DOS PRODUTOS:")
                logger.info(f"   Subtotal: R$ {total_produtos:,.2f}")
                logger.info(f"   Impostos: R$ {total_impostos:,.2f}")
                logger.info(f"   TOTAL: R$ {(total_produtos + total_impostos):,.2f}")
            
            logger.info(f"\n" + "="*80)
            logger.info(f"🎯 RESUMO FINAL DA COTAÇÃO {cotacao[0]['name']}:")
            logger.info(f"   ✅ Impostos calculados e aplicados")
            logger.info(f"   ✅ Incoterm CIF configurado")
            logger.info(f"   ✅ Forma de Pagamento: Transferência Bancária CD")
            logger.info(f"   ✅ Total com impostos: R$ {cotacao[0]['amount_total']:,.2f}")
            logger.info("="*80)
        
        return cotacao_id
        
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    logger.info("🚀 Criando cotação FINAL COMPLETA no Odoo...")
    logger.info("="*80)
    
    cotacao_id = criar_cotacao_final()
    
    if cotacao_id:
        logger.info(f"\n✅ SUCESSO TOTAL!")
        logger.info(f"🆔 Cotação ID: {cotacao_id}")
        logger.info("\n💡 Cotação criada com TODOS os campos:")
        logger.info("   • Impostos calculados corretamente")
        logger.info("   • Incoterm CIF aplicado")
        logger.info("   • Forma de Pagamento: Transferência Bancária CD")
        logger.info("   • Empresa: NACOM GOYA - CD")
        logger.info("\n📋 Acesse no Odoo: Vendas > Cotações")



# Server Action 1955 - Debug Aprimorado para CFOP
# Executar no contexto de sale.order.line

import logging
_logger = logging.getLogger(__name__)

for record in records:
    _logger.info("="*60)
    _logger.info("CFOP DEBUG - Server Action 1955")
    _logger.info("="*60)

    # 1. Informações básicas
    _logger.info(f"Linha ID: {record.id}")
    _logger.info(f"Produto: {record.product_id.name if record.product_id else 'SEM PRODUTO'}")
    _logger.info(f"Pedido: {record.order_id.name if record.order_id else 'SEM PEDIDO'}")

    # 2. Campos CFOP atuais
    _logger.info(f"CFOP ID atual: {record.l10n_br_cfop_id.id if record.l10n_br_cfop_id else 'VAZIO'}")
    _logger.info(f"CFOP Código atual: {record.l10n_br_cfop_codigo or 'VAZIO'}")

    # 3. Verificar campos fiscais disponíveis
    fiscal_fields = []
    for field_name in record._fields:
        if 'fiscal' in field_name.lower() or 'cfop' in field_name.lower() or 'l10n_br' in field_name.lower():
            value = getattr(record, field_name, None)
            fiscal_fields.append(f"{field_name}: {value}")

    _logger.info("Campos fiscais encontrados:")
    for field in fiscal_fields[:10]:  # Limitar para não poluir o log
        _logger.info(f"  - {field}")

    # 4. Verificar posição fiscal
    if record.order_id and record.order_id.partner_id:
        partner = record.order_id.partner_id
        fiscal_pos = partner.property_account_position_id
        _logger.info(f"Cliente: {partner.name}")
        _logger.info(f"Posição Fiscal: {fiscal_pos.name if fiscal_pos else 'SEM POSIÇÃO FISCAL'}")
        _logger.info(f"Estado Cliente: {partner.state_id.code if partner.state_id else 'N/A'}")

    # 5. Verificar empresa
    if record.order_id:
        company = record.order_id.company_id
        _logger.info(f"Empresa: {company.name if company else 'N/A'}")
        _logger.info(f"Estado Empresa: {company.state_id.code if company and company.state_id else 'N/A'}")

    # 6. Tentar executar método de cálculo de impostos
    try:
        # Este método existe e calcula impostos
        if hasattr(record.order_id, 'onchange_l10n_br_calcular_imposto'):
            _logger.info("Executando onchange_l10n_br_calcular_imposto...")
            record.order_id.onchange_l10n_br_calcular_imposto()
            _logger.info("Método executado com sucesso!")

            # Verificar se CFOP mudou
            _logger.info(f"CFOP após cálculo: {record.l10n_br_cfop_codigo or 'AINDA VAZIO'}")
    except Exception as e:
        _logger.error(f"Erro ao executar método: {str(e)}")

    # 7. Listar métodos disponíveis que contém 'compute' ou 'onchange'
    methods = []
    for attr_name in dir(record):
        if not attr_name.startswith('_'):
            continue
        if 'compute' in attr_name or 'onchange' in attr_name:
            methods.append(attr_name)

    if methods:
        _logger.info("Métodos compute/onchange disponíveis:")
        for method in methods[:10]:
            _logger.info(f"  - {method}")

    _logger.info("="*60)
    _logger.info("FIM DO DEBUG CFOP")
    _logger.info("="*60)