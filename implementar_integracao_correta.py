#!/usr/bin/env python3
"""
Script para implementar integração correta com Odoo
===================================================

Este script implementa a abordagem correta para acessar dados do Odoo
usando múltiplas consultas ao invés de campos com "/".

Execução:
    python implementar_integracao_correta.py

Autor: Sistema de Fretes - Integração Odoo
Data: 2025-07-14
"""

import json
import logging
import sys
import os
from typing import Dict, List, Any, Optional
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('integracao_correta.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def conectar_odoo():
    """
    Conecta ao Odoo usando as configurações do sistema
    """
    try:
        from app.odoo.utils.connection import OdooConnection
        from app.odoo.config.odoo_config import ODOO_CONFIG
        
        logger.info("Conectando ao Odoo...")
        connection = OdooConnection(ODOO_CONFIG)
        
        if connection.test_connection():
            logger.info("Conexão com Odoo estabelecida")
            return connection
        else:
            logger.error("Falha na conexão com Odoo")
            return None
            
    except Exception as e:
        logger.error(f"Erro ao conectar com Odoo: {e}")
        return None

def buscar_dados_linha_pedido(connection, limit: int = 50) -> List[Dict]:
    """
    Busca dados das linhas de pedido com campos diretos
    """
    logger.info(f"Buscando dados das linhas de pedido (limite: {limit})...")
    
    campos_linha = [
        'id',
        'order_id',
        'product_id',
        'product_uom_qty',
        'qty_to_invoice',
        'qty_saldo',
        'qty_cancelado',
        'qty_invoiced',
        'price_unit',
        'l10n_br_prod_valor',
        'l10n_br_total_nfe',
        'qty_delivered',
        'name',  # Descrição do produto na linha
        'sequence',  # Sequência da linha
        'state',  # Estado da linha
    ]
    
    try:
        dados_linha = connection.search_read(
            'sale.order.line',
            [],
            campos_linha,
            limit=limit
        )
        
        logger.info(f"Encontradas {len(dados_linha)} linhas de pedido")
        return dados_linha
        
    except Exception as e:
        logger.error(f"Erro ao buscar dados da linha: {e}")
        return []

def buscar_dados_pedido(connection, order_ids: List[int]) -> Dict[int, Dict]:
    """
    Busca dados dos pedidos baseado nos IDs
    """
    logger.info(f"Buscando dados de {len(order_ids)} pedidos...")
    
    campos_pedido = [
        'id',
        'name',
        'l10n_br_pedido_compra',
        'create_date',
        'date_order',
        'partner_id',
        'partner_shipping_id',
        'state',
        'user_id',
        'team_id',
        'payment_term_id',
        'incoterm',
        'carrier_id',
        'commitment_date',
        'picking_note',
    ]
    
    try:
        dados_pedido = connection.search_read(
            'sale.order',
            [('id', 'in', order_ids)],
            campos_pedido
        )
        
        # Indexar por ID para fácil acesso
        pedidos_map = {p['id']: p for p in dados_pedido}
        
        logger.info(f"Encontrados {len(pedidos_map)} pedidos")
        return pedidos_map
        
    except Exception as e:
        logger.error(f"Erro ao buscar dados do pedido: {e}")
        return {}

def buscar_dados_produto(connection, product_ids: List[int]) -> Dict[int, Dict]:
    """
    Busca dados dos produtos baseado nos IDs
    """
    logger.info(f"Buscando dados de {len(product_ids)} produtos...")
    
    campos_produto = [
        'id',
        'name',
        'default_code',
        'uom_id',
        'categ_id',
        'product_template_id',
        'barcode',
        'weight',
        'volume',
    ]
    
    try:
        dados_produto = connection.search_read(
            'product.product',
            [('id', 'in', product_ids)],
            campos_produto
        )
        
        # Indexar por ID para fácil acesso
        produtos_map = {p['id']: p for p in dados_produto}
        
        logger.info(f"Encontrados {len(produtos_map)} produtos")
        return produtos_map
        
    except Exception as e:
        logger.error(f"Erro ao buscar dados do produto: {e}")
        return {}

def buscar_dados_cliente(connection, partner_ids: List[int]) -> Dict[int, Dict]:
    """
    Busca dados dos clientes baseado nos IDs
    """
    logger.info(f"Buscando dados de {len(partner_ids)} clientes...")
    
    campos_cliente = [
        'id',
        'name',
        'l10n_br_cnpj',
        'l10n_br_razao_social',
        'l10n_br_municipio_id',
        'state_id',
        'street',
        'zip',
        'phone',
        'email',
        'l10n_br_endereco_numero',
        'l10n_br_endereco_bairro',
    ]
    
    try:
        dados_cliente = connection.search_read(
            'res.partner',
            [('id', 'in', partner_ids)],
            campos_cliente
        )
        
        # Indexar por ID para fácil acesso
        clientes_map = {c['id']: c for c in dados_cliente}
        
        logger.info(f"Encontrados {len(clientes_map)} clientes")
        return clientes_map
        
    except Exception as e:
        logger.error(f"Erro ao buscar dados do cliente: {e}")
        return {}

def integrar_dados_completos(connection, limit: int = 50) -> List[Dict]:
    """
    Integra todos os dados fazendo múltiplas consultas
    """
    logger.info("Iniciando integração completa dos dados...")
    
    # 1. Buscar dados das linhas de pedido
    linhas_pedido = buscar_dados_linha_pedido(connection, limit)
    
    if not linhas_pedido:
        logger.error("Nenhuma linha de pedido encontrada")
        return []
    
    # 2. Extrair IDs únicos para consultas relacionadas
    order_ids = list(set([linha['order_id'][0] for linha in linhas_pedido if linha['order_id']]))
    product_ids = list(set([linha['product_id'][0] for linha in linhas_pedido if linha['product_id']]))
    
    # 3. Buscar dados dos pedidos
    pedidos_map = buscar_dados_pedido(connection, order_ids)
    
    # 4. Buscar dados dos produtos
    produtos_map = buscar_dados_produto(connection, product_ids)
    
    # 5. Extrair IDs dos clientes dos pedidos
    partner_ids = []
    shipping_ids = []
    for pedido in pedidos_map.values():
        if pedido.get('partner_id'):
            partner_ids.append(pedido['partner_id'][0])
        if pedido.get('partner_shipping_id'):
            shipping_ids.append(pedido['partner_shipping_id'][0])
    
    all_client_ids = list(set(partner_ids + shipping_ids))
    
    # 6. Buscar dados dos clientes
    clientes_map = buscar_dados_cliente(connection, all_client_ids)
    
    # 7. Integrar todos os dados
    dados_integrados = []
    
    for linha in linhas_pedido:
        # Dados da linha
        dados_linha = {
            'linha_id': linha['id'],
            'linha_sequence': linha.get('sequence'),
            'linha_name': linha.get('name'),
            'linha_state': linha.get('state'),
            'product_uom_qty': linha.get('product_uom_qty'),
            'qty_to_invoice': linha.get('qty_to_invoice'),
            'qty_saldo': linha.get('qty_saldo'),
            'qty_cancelado': linha.get('qty_cancelado'),
            'qty_invoiced': linha.get('qty_invoiced'),
            'price_unit': linha.get('price_unit'),
            'l10n_br_prod_valor': linha.get('l10n_br_prod_valor'),
            'l10n_br_total_nfe': linha.get('l10n_br_total_nfe'),
            'qty_delivered': linha.get('qty_delivered'),
        }
        
        # Dados do pedido
        if linha['order_id']:
            order_id = linha['order_id'][0]
            pedido = pedidos_map.get(order_id, {})
            dados_linha.update({
                'pedido_id': order_id,
                'pedido_name': pedido.get('name'),
                'pedido_compra': pedido.get('l10n_br_pedido_compra'),
                'pedido_create_date': pedido.get('create_date'),
                'pedido_date_order': pedido.get('date_order'),
                'pedido_state': pedido.get('state'),
                'pedido_user_id': pedido.get('user_id'),
                'pedido_team_id': pedido.get('team_id'),
                'pedido_payment_term': pedido.get('payment_term_id'),
                'pedido_incoterm': pedido.get('incoterm'),
                'pedido_carrier': pedido.get('carrier_id'),
                'pedido_commitment_date': pedido.get('commitment_date'),
                'pedido_picking_note': pedido.get('picking_note'),
            })
            
            # Dados do cliente
            if pedido.get('partner_id'):
                partner_id = pedido['partner_id'][0]
                cliente = clientes_map.get(partner_id, {})
                dados_linha.update({
                    'cliente_id': partner_id,
                    'cliente_name': cliente.get('name'),
                    'cliente_cnpj': cliente.get('l10n_br_cnpj'),
                    'cliente_razao_social': cliente.get('l10n_br_razao_social'),
                    'cliente_municipio': cliente.get('l10n_br_municipio_id'),
                    'cliente_estado': cliente.get('state_id'),
                    'cliente_endereco': cliente.get('street'),
                    'cliente_cep': cliente.get('zip'),
                    'cliente_phone': cliente.get('phone'),
                    'cliente_email': cliente.get('email'),
                })
            
            # Dados do endereço de entrega
            if pedido.get('partner_shipping_id'):
                shipping_id = pedido['partner_shipping_id'][0]
                endereco = clientes_map.get(shipping_id, {})
                dados_linha.update({
                    'entrega_id': shipping_id,
                    'entrega_name': endereco.get('name'),
                    'entrega_cnpj': endereco.get('l10n_br_cnpj'),
                    'entrega_endereco': endereco.get('street'),
                    'entrega_numero': endereco.get('l10n_br_endereco_numero'),
                    'entrega_bairro': endereco.get('l10n_br_endereco_bairro'),
                    'entrega_cep': endereco.get('zip'),
                    'entrega_municipio': endereco.get('l10n_br_municipio_id'),
                    'entrega_estado': endereco.get('state_id'),
                    'entrega_phone': endereco.get('phone'),
                })
        
        # Dados do produto
        if linha['product_id']:
            product_id = linha['product_id'][0]
            produto = produtos_map.get(product_id, {})
            dados_linha.update({
                'produto_id': product_id,
                'produto_name': produto.get('name'),
                'produto_codigo': produto.get('default_code'),
                'produto_uom': produto.get('uom_id'),
                'produto_categoria': produto.get('categ_id'),
                'produto_template': produto.get('product_template_id'),
                'produto_barcode': produto.get('barcode'),
                'produto_peso': produto.get('weight'),
                'produto_volume': produto.get('volume'),
            })
        
        dados_integrados.append(dados_linha)
    
    logger.info(f"Integração completa finalizada: {len(dados_integrados)} registros")
    return dados_integrados

def main():
    """
    Função principal
    """
    logger.info("=== IMPLEMENTAÇÃO DE INTEGRAÇÃO CORRETA COM ODOO ===")
    
    # Conectar ao Odoo
    connection = conectar_odoo()
    if not connection:
        logger.error("Não foi possível conectar ao Odoo")
        return
    
    # Integrar dados completos
    dados_integrados = integrar_dados_completos(connection, limit=10)
    
    if not dados_integrados:
        logger.error("Nenhum dado foi integrado")
        return
    
    # Salvar resultados
    arquivo_resultado = 'integracao_odoo_correta.json'
    with open(arquivo_resultado, 'w', encoding='utf-8') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'total_registros': len(dados_integrados),
            'dados': dados_integrados
        }, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"Resultados salvos em: {arquivo_resultado}")
    
    # Resumo
    logger.info("\n" + "="*80)
    logger.info("RESUMO DA INTEGRAÇÃO")
    logger.info("="*80)
    logger.info(f"Total de registros integrados: {len(dados_integrados)}")
    logger.info(f"Campos por registro: {len(dados_integrados[0]) if dados_integrados else 0}")
    
    # Mostrar exemplo do primeiro registro
    if dados_integrados:
        logger.info("\nExemplo do primeiro registro:")
        primeiro = dados_integrados[0]
        for campo, valor in list(primeiro.items())[:10]:
            logger.info(f"  {campo}: {valor}")
        logger.info("  ... (mais campos)")
    
    logger.info("\nAbordagem utilizada:")
    logger.info("  1. Buscar dados de sale.order.line com campos diretos")
    logger.info("  2. Buscar dados de sale.order usando order_ids")
    logger.info("  3. Buscar dados de product.product usando product_ids")
    logger.info("  4. Buscar dados de res.partner usando partner_ids")
    logger.info("  5. Integrar todos os dados em uma estrutura unificada")
    
    logger.info("\nEsta abordagem resolve o problema dos campos com '/' que não funcionam no Odoo!")

if __name__ == "__main__":
    main() 