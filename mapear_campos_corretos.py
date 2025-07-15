#!/usr/bin/env python3
"""
Script para mapear campos corretos do Odoo
==========================================

Este script explora os campos disponíveis no Odoo e mapeia corretamente
os campos necessários para a integração.

Execução:
    python mapear_campos_corretos.py

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
        logging.FileHandler('mapear_campos_corretos.log'),
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

def descobrir_campos_modelo(connection, modelo: str) -> tuple[List[str], Dict[str, Any]]:
    """
    Descobre todos os campos disponíveis em um modelo
    """
    try:
        logger.info(f"Descobrindo campos do modelo: {modelo}")
        
        # Método 1: Usar fields_get
        campos_info = connection.execute_kw(
            modelo, 
            'fields_get',
            [],
            {'attributes': ['string', 'type', 'relation']}
        )
        
        campos = list(campos_info.keys())
        logger.info(f"Encontrados {len(campos)} campos no modelo {modelo}")
        
        return campos, campos_info
        
    except Exception as e:
        logger.error(f"❌ Erro ao descobrir campos: {e}")
        return [], {}

def testar_campos_relacionados(connection, modelo: str, campo_base: str, campos_relacionados: List[str]) -> Dict[str, Any]:
    """
    Testa campos relacionados para ver quais funcionam
    """
    resultados = {}
    
    for campo in campos_relacionados:
        try:
            # Tentar buscar apenas o campo relacionado
            dados = connection.search_read(
                modelo,
                [],
                [campo_base, campo],
                limit=1
            )
            
            if dados:
                resultados[campo] = {
                    'status': 'válido',
                    'valor_exemplo': dados[0].get(campo, 'N/A')
                }
                logger.info(f"  ✓ {campo} - VÁLIDO")
            else:
                resultados[campo] = {
                    'status': 'sem_dados',
                    'valor_exemplo': None
                }
                logger.info(f"  ✓ {campo} - SEM DADOS")
                
        except Exception as e:
            resultados[campo] = {
                'status': 'inválido',
                'erro': str(e)
            }
            logger.info(f"  ✗ {campo} - INVÁLIDO")
    
    return resultados

def mapear_campos_necessarios(connection):
    """
    Mapeia os campos necessários para a integração
    """
    logger.info("Iniciando mapeamento de campos necessários...")
    
    # Campos base que sabemos que funcionam
    campos_base_validos = [
        'product_uom_qty',
        'qty_to_invoice', 
        'qty_saldo',
        'qty_cancelado',
        'qty_invoiced',
        'price_unit',
        'l10n_br_prod_valor',
        'l10n_br_total_nfe',
        'qty_delivered'
    ]
    
    # Descobrir todos os campos disponíveis
    campos_disponiveis, campos_info = descobrir_campos_modelo(connection, 'sale.order.line')
    
    # Campos relacionados que precisamos testar
    campos_relacionados_order = [
        'order_id',  # Campo base para pedido
    ]
    
    campos_relacionados_product = [
        'product_id',  # Campo base para produto
    ]
    
    # Testar campos relacionados
    logger.info("Testando campos relacionados de pedido...")
    resultados_order = testar_campos_relacionados(
        connection, 
        'sale.order.line', 
        'order_id', 
        campos_relacionados_order
    )
    
    logger.info("Testando campos relacionados de produto...")
    resultados_product = testar_campos_relacionados(
        connection, 
        'sale.order.line', 
        'product_id', 
        campos_relacionados_product
    )
    
    # Obter dados de exemplo para análise
    logger.info("Obtendo dados de exemplo...")
    dados_exemplo = connection.search_read(
        'sale.order.line',
        [],
        campos_base_validos + ['order_id', 'product_id'],
        limit=5
    )
    
    # Estruturar resultados
    mapeamento = {
        'timestamp': datetime.now().isoformat(),
        'modelo': 'sale.order.line',
        'campos_base_validos': campos_base_validos,
        'total_campos_disponiveis': len(campos_disponiveis),
        'campos_disponiveis': campos_disponiveis,
        'campos_info': campos_info,
        'resultados_order': resultados_order,
        'resultados_product': resultados_product,
        'dados_exemplo': dados_exemplo,
        'recomendacoes': {
            'campos_diretos_usar': campos_base_validos,
            'campos_relacionados_investigar': ['order_id', 'product_id'],
            'proximos_passos': [
                'Investigar estrutura dos campos order_id e product_id',
                'Testar acesso aos campos através de consultas separadas',
                'Mapear campos necessários através de múltiplas consultas'
            ]
        }
    }
    
    return mapeamento

def investigar_estrutura_relacionamentos(connection):
    """
    Investiga a estrutura dos relacionamentos order_id e product_id
    """
    logger.info("Investigando estrutura dos relacionamentos...")
    
    # Testar order_id
    try:
        logger.info("Testando estrutura do order_id...")
        dados_order = connection.search_read(
            'sale.order.line',
            [],
            ['order_id'],
            limit=3
        )
        
        if dados_order:
            order_ids = [d['order_id'][0] for d in dados_order if d['order_id']]
            logger.info(f"Order IDs encontrados: {order_ids}")
            
            # Buscar dados do pedido
            dados_pedido = connection.search_read(
                'sale.order',
                [('id', 'in', order_ids)],
                ['name', 'l10n_br_pedido_compra', 'create_date', 'date_order', 'partner_id'],
                limit=3
            )
            
            logger.info("Dados do pedido encontrados:")
            for pedido in dados_pedido:
                logger.info(f"  - {pedido}")
                
    except Exception as e:
        logger.error(f"Erro ao investigar order_id: {e}")
    
    # Testar product_id
    try:
        logger.info("Testando estrutura do product_id...")
        dados_product = connection.search_read(
            'sale.order.line',
            [],
            ['product_id'],
            limit=3
        )
        
        if dados_product:
            product_ids = [d['product_id'][0] for d in dados_product if d['product_id']]
            logger.info(f"Product IDs encontrados: {product_ids}")
            
            # Buscar dados do produto
            dados_produto = connection.search_read(
                'product.product',
                [('id', 'in', product_ids)],
                ['name', 'default_code', 'uom_id', 'categ_id'],
                limit=3
            )
            
            logger.info("Dados do produto encontrados:")
            for produto in dados_produto:
                logger.info(f"  - {produto}")
                
    except Exception as e:
        logger.error(f"Erro ao investigar product_id: {e}")

def main():
    """
    Função principal
    """
    logger.info("=== MAPEAMENTO DE CAMPOS CORRETOS DO ODOO ===")
    
    # Conectar ao Odoo
    connection = conectar_odoo()
    if not connection:
        logger.error("❌ Não foi possível conectar ao Odoo")
        return
    
    # Mapear campos necessários
    mapeamento = mapear_campos_necessarios(connection)
    
    # Investigar estrutura dos relacionamentos
    investigar_estrutura_relacionamentos(connection)
    
    # Salvar resultados
    arquivo_resultado = 'mapeamento_campos_corretos.json'
    with open(arquivo_resultado, 'w', encoding='utf-8') as f:
        json.dump(mapeamento, f, indent=2, ensure_ascii=False, default=str)
    
    logger.info(f"✅ Resultados salvos em: {arquivo_resultado}")
    
    # Resumo
    logger.info("\n" + "="*80)
    logger.info("RESUMO DO MAPEAMENTO")
    logger.info("="*80)
    logger.info(f"Total de campos disponíveis: {mapeamento['total_campos_disponiveis']}")
    logger.info(f"Campos base válidos: {len(mapeamento['campos_base_validos'])}")
    logger.info(f"Campos base: {', '.join(mapeamento['campos_base_validos'])}")
    logger.info("\nPróximos passos:")
    for i, passo in enumerate(mapeamento['recomendacoes']['proximos_passos'], 1):
        logger.info(f"  {i}. {passo}")

if __name__ == "__main__":
    main() 