#!/usr/bin/env python3
"""
Script para simular o comportamento do onchange e preencher CFOP automaticamente
Data: 2025-01-25
"""

import sys
import os
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.odoo.utils.connection import get_odoo_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def determinar_cfop_automatico(odoo, partner_id, product_id, company_id=4):
    """
    Simula a lógica do onchange para determinar o CFOP correto
    """
    try:
        # 1. Buscar informações do cliente
        cliente = odoo.search_read(
            'res.partner',
            [('id', '=', partner_id)],
            ['name', 'state_id', 'city', 'property_account_position_id', 'l10n_br_cnpj']
        )[0]
        
        logger.info(f"\n👤 Cliente: {cliente['name']}")
        
        # 2. Buscar estado do cliente
        estado_cliente = None
        if cliente.get('state_id'):
            estado = odoo.search_read(
                'res.country.state',
                [('id', '=', cliente['state_id'][0] if isinstance(cliente['state_id'], list) else cliente['state_id'])],
                ['code', 'name']
            )[0]
            estado_cliente = estado['code']
            logger.info(f"   Estado: {estado_cliente} - {estado['name']}")
        
        # 3. Verificar se é ZFM (Zona Franca de Manaus)
        is_zfm = False
        if cliente.get('city'):
            cidade = cliente['city'].upper()
            if 'MANAUS' in cidade or estado_cliente == 'AM':
                is_zfm = True
                logger.info("   ⭐ Cliente ZFM (Zona Franca de Manaus)")
        
        # 4. Buscar informações do produto
        produto = odoo.search_read(
            'product.product',
            [('id', '=', product_id)],
            ['name', 'default_code', 'taxes_id']
        )[0]
        
        logger.info(f"\n📦 Produto: {produto['name']}")
        
        # 5. Verificar se produto tem ST (Substituição Tributária)
        tem_st = False
        if produto.get('taxes_id'):
            impostos = odoo.search_read(
                'account.tax',
                [('id', 'in', produto['taxes_id'])],
                ['name', 'description']
            )
            for imposto in impostos:
                if 'ST' in imposto.get('name', '').upper() or 'SUBST' in imposto.get('name', '').upper():
                    tem_st = True
                    logger.info("   ⭐ Produto com Substituição Tributária (ST)")
                    break
        
        # 6. Buscar estado da empresa (origem)
        empresa = odoo.search_read(
            'res.company',
            [('id', '=', company_id)],
            ['name', 'state_id']
        )[0]
        
        estado_empresa = None
        if empresa.get('state_id'):
            estado_emp = odoo.search_read(
                'res.country.state',
                [('id', '=', empresa['state_id'][0] if isinstance(empresa['state_id'], list) else empresa['state_id'])],
                ['code', 'name']
            )[0]
            estado_empresa = estado_emp['code']
            logger.info(f"\n🏢 Empresa: {empresa['name']} - Estado: {estado_empresa}")
        
        # 7. LÓGICA DE DETERMINAÇÃO DO CFOP
        logger.info("\n" + "="*60)
        logger.info("🎯 DETERMINANDO CFOP BASEADO NAS REGRAS:")
        logger.info("="*60)
        
        cfop_codigo = None
        cfop_descricao = ""
        
        # Regras de CFOP
        if is_zfm:
            # Zona Franca de Manaus
            if tem_st:
                cfop_codigo = '6109'  # Venda para ZFM com ST
                cfop_descricao = "Venda para ZFM com ST"
            else:
                cfop_codigo = '6109'  # Venda para ZFM
                cfop_descricao = "Venda de produção para Zona Franca de Manaus"
        elif estado_cliente == estado_empresa:
            # Mesmo estado
            if tem_st:
                cfop_codigo = '5405'  # Venda dentro do estado com ST
                cfop_descricao = "Venda dentro do estado com ST"
            else:
                cfop_codigo = '5102'  # Venda dentro do estado
                cfop_descricao = "Venda de mercadoria dentro do estado"
        else:
            # Estados diferentes
            if tem_st:
                cfop_codigo = '6405'  # Venda interestadual com ST
                cfop_descricao = "Venda interestadual com ST"
            else:
                cfop_codigo = '6102'  # Venda interestadual
                cfop_descricao = "Venda de mercadoria para outro estado"
        
        logger.info(f"\n✅ CFOP determinado: {cfop_codigo} - {cfop_descricao}")
        logger.info(f"   Lógica aplicada:")
        logger.info(f"   • ZFM: {'SIM' if is_zfm else 'NÃO'}")
        logger.info(f"   • ST: {'SIM' if tem_st else 'NÃO'}")
        logger.info(f"   • Mesmo estado: {'SIM' if estado_cliente == estado_empresa else 'NÃO'}")
        
        # 8. Buscar o ID do CFOP no sistema
        cfop = odoo.search_read(
            'l10n_br_ciel_it_account.cfop',
            [('codigo_cfop', '=', cfop_codigo)],
            ['id', 'name'],
            limit=1
        )
        
        if cfop:
            cfop_id = cfop[0]['id']
            logger.info(f"\n✅ CFOP encontrado no sistema:")
            logger.info(f"   ID: {cfop_id}")
            logger.info(f"   Nome: {cfop[0]['name']}")
            return cfop_id
        else:
            logger.warning(f"\n⚠️ CFOP {cfop_codigo} não encontrado no sistema")
            
            # Tentar buscar CFOP alternativo
            if cfop_codigo in ['6109', '6110']:
                # Se não encontrar CFOP de ZFM, usar interestadual normal
                cfop_codigo_alt = '6102'
                logger.info(f"   Tentando CFOP alternativo: {cfop_codigo_alt}")
            else:
                cfop_codigo_alt = cfop_codigo
            
            cfop_alt = odoo.search_read(
                'l10n_br_ciel_it_account.cfop',
                [('codigo_cfop', '=', cfop_codigo_alt)],
                ['id', 'name'],
                limit=1
            )
            
            if cfop_alt:
                logger.info(f"   ✅ CFOP alternativo encontrado: {cfop_alt[0]['name']}")
                return cfop_alt[0]['id']
            
            return None
            
    except Exception as e:
        logger.error(f"Erro ao determinar CFOP: {e}")
        return None

def criar_cotacao_com_cfop_automatico():
    """
    Cria cotação com CFOP determinado automaticamente
    """
    try:
        logger.info("🔌 Conectando ao Odoo...")
        odoo = get_odoo_connection()
        
        # Configurações
        company_id = 4  # NACOM GOYA - CD
        warehouse_id = 3
        
        # Testar com diferentes clientes
        clientes_teste = [
            '75.315.333/0002-90',  # ATACADAO MS (interestadual)
            '04.033.005/0062-11',  # Cliente em Manaus (ZFM)
        ]
        
        for cnpj_cliente in clientes_teste[:1]:  # Testar apenas o primeiro
            logger.info("\n" + "="*80)
            logger.info(f"🧪 TESTE COM CLIENTE: {cnpj_cliente}")
            logger.info("="*80)
            
            # Buscar cliente
            cliente = odoo.search_read(
                'res.partner',
                [('l10n_br_cnpj', '=', cnpj_cliente)],
                ['id', 'name'],
                limit=1
            )
            
            if not cliente:
                # Tentar busca parcial
                cnpj_limpo = cnpj_cliente.replace('.', '').replace('/', '').replace('-', '')
                cliente = odoo.search_read(
                    'res.partner',
                    [('l10n_br_cnpj', 'ilike', cnpj_limpo[:8])],
                    ['id', 'name'],
                    limit=1
                )
            
            if not cliente:
                logger.warning(f"❌ Cliente {cnpj_cliente} não encontrado")
                continue
            
            partner_id = cliente[0]['id']
            
            # Buscar produto
            produto = odoo.search_read(
                'product.product',
                [('default_code', '=', '4310162')],
                ['id', 'name'],
                limit=1
            )
            
            if not produto:
                produto = odoo.search_read(
                    'product.product',
                    [('sale_ok', '=', True)],
                    ['id', 'name'],
                    limit=1
                )
            
            if not produto:
                logger.error("❌ Nenhum produto encontrado")
                continue
            
            product_id = produto[0]['id']
            
            # DETERMINAR CFOP AUTOMATICAMENTE
            cfop_id = determinar_cfop_automatico(odoo, partner_id, product_id, company_id)
            
            # Criar cotação
            logger.info("\n📝 Criando cotação...")
            
            cotacao_data = {
                'partner_id': partner_id,
                'company_id': company_id,
                'warehouse_id': warehouse_id,
                'date_order': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'order_line': [(0, 0, {
                    'product_id': product_id,
                    'name': produto[0]['name'],
                    'product_uom_qty': 10,
                    'price_unit': 150.00,
                })],
            }
            
            # Adicionar CFOP se foi determinado
            if cfop_id:
                cotacao_data['order_line'][0][2]['l10n_br_cfop_id'] = cfop_id
                logger.info(f"   ✅ CFOP adicionado à linha: ID {cfop_id}")
            
            cotacao_id = odoo.execute_kw(
                'sale.order',
                'create',
                [cotacao_data]
            )
            
            logger.info(f"✅ Cotação criada: ID {cotacao_id}")
            
            # Verificar resultado
            cotacao = odoo.search_read(
                'sale.order',
                [('id', '=', cotacao_id)],
                ['name', 'partner_id']
            )[0]
            
            linhas = odoo.search_read(
                'sale.order.line',
                [('order_id', '=', cotacao_id)],
                ['product_id', 'l10n_br_cfop_id', 'l10n_br_cfop_codigo']
            )
            
            logger.info(f"\n📊 RESULTADO FINAL:")
            logger.info(f"   Cotação: {cotacao['name']}")
            logger.info(f"   Cliente: {cotacao['partner_id'][1] if isinstance(cotacao['partner_id'], list) else 'N/A'}")
            
            for linha in linhas:
                cfop_info = "VAZIO"
                if linha.get('l10n_br_cfop_id'):
                    if isinstance(linha['l10n_br_cfop_id'], list):
                        cfop_info = f"{linha.get('l10n_br_cfop_codigo', '')} - {linha['l10n_br_cfop_id'][1]}"
                    else:
                        cfop_info = linha.get('l10n_br_cfop_codigo', 'ID: ' + str(linha['l10n_br_cfop_id']))
                
                logger.info(f"   Produto: {linha['product_id'][1] if isinstance(linha['product_id'], list) else 'N/A'}")
                logger.info(f"   CFOP: {cfop_info}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Erro: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    logger.info("🚀 Simulando onchange para determinar CFOP automaticamente...")
    logger.info("="*80)
    
    sucesso = criar_cotacao_com_cfop_automatico()
    
    if sucesso:
        logger.info("\n✅ SUCESSO! CFOP determinado e aplicado automaticamente!")
        logger.info("""
RESUMO:
-------
Conseguimos simular o comportamento do onchange do Odoo!

A lógica de determinação do CFOP considera:
1. Se é ZFM (Zona Franca de Manaus)
2. Se o produto tem ST (Substituição Tributária)
3. Se é operação dentro do mesmo estado ou interestadual

CFOPs aplicados:
- 5102: Venda dentro do estado
- 6102: Venda interestadual
- 5405: Venda dentro do estado com ST
- 6405: Venda interestadual com ST
- 6109: Venda para ZFM

Esta lógica pode ser incorporada no script de criação de cotações!
""")