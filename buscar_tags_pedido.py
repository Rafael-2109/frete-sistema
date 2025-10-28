"""
Script para buscar marcadores (tag_ids) de um pedido no Odoo
=============================================================

Busca os tags (marcadores) do pedido VCD2563875 usando as credenciais
do carteira_service.py

Autor: Sistema de Fretes
Data: 2025-10-27
"""

import xmlrpc.client
import ssl
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Configuração do Odoo (mesma usada em odoo_config.py)
ODOO_CONFIG = {
    'url': 'https://odoo.nacomgoya.com.br',
    'database': 'odoo-17-ee-nacomgoya-prd',
    'username': 'rafael@conservascampobelo.com.br',
    'api_key': '67705b0986ff5c052e657f1c0ffd96ceb191af69',
    'timeout': 120
}


def conectar_odoo():
    """Estabelece conexão com Odoo e retorna common, models e uid"""
    try:
        # Configurar SSL
        ssl_context = ssl.create_default_context()

        # Conexão common
        common = xmlrpc.client.ServerProxy(
            f"{ODOO_CONFIG['url']}/xmlrpc/2/common",
            context=ssl_context
        )

        # Conexão models
        models = xmlrpc.client.ServerProxy(
            f"{ODOO_CONFIG['url']}/xmlrpc/2/object",
            context=ssl_context
        )

        # Autenticar
        uid = common.authenticate(
            ODOO_CONFIG['database'],
            ODOO_CONFIG['username'],
            ODOO_CONFIG['api_key'],
            {}
        )

        if not uid:
            logger.error("❌ Falha na autenticação")
            return None, None, None

        logger.info(f"✅ Autenticado com UID: {uid}")
        return common, models, uid

    except Exception as e:
        logger.error(f"❌ Erro ao conectar: {e}")
        return None, None, None


def buscar_tags_pedido(nome_pedido: str):
    """
    Busca os marcadores (tag_ids) de um pedido no Odoo

    Args:
        nome_pedido: Número do pedido (ex: VCD2563875)
    """
    try:
        logger.info(f"🔍 Iniciando busca de tags para o pedido: {nome_pedido}")

        # Conecta ao Odoo
        common, models, uid = conectar_odoo()

        if not uid:
            return None

        # Busca o pedido no sale.order
        logger.info(f"🔎 Buscando pedido {nome_pedido} no sale.order...")

        pedidos = models.execute_kw(
            ODOO_CONFIG['database'],
            uid,
            ODOO_CONFIG['api_key'],
            'sale.order',
            'search_read',
            [[('name', '=', nome_pedido)]],
            {
                'fields': ['id', 'name', 'tag_ids', 'state', 'partner_id', 'date_order'],
                'limit': 1
            }
        )

        if not pedidos:
            logger.warning(f"⚠️ Pedido {nome_pedido} não encontrado no Odoo")
            return None

        pedido = pedidos[0]
        logger.info(f"✅ Pedido encontrado!")
        logger.info(f"   📋 ID: {pedido.get('id')}")
        logger.info(f"   📋 Nome: {pedido.get('name')}")
        logger.info(f"   📋 Estado: {pedido.get('state')}")
        logger.info(f"   📋 Cliente ID: {pedido.get('partner_id')}")
        logger.info(f"   📋 Data: {pedido.get('date_order')}")

        # Busca os tag_ids
        tag_ids = pedido.get('tag_ids', [])
        logger.info(f"   🏷️  Tag IDs: {tag_ids}")

        if not tag_ids:
            logger.info("   ℹ️  Este pedido não possui tags/marcadores")
            return []

        # Busca detalhes dos tags em crm.tag
        logger.info(f"\n🔎 Buscando detalhes dos {len(tag_ids)} tags...")

        tags = models.execute_kw(
            ODOO_CONFIG['database'],
            uid,
            ODOO_CONFIG['api_key'],
            'crm.tag',
            'read',
            [tag_ids],
            {'fields': ['id', 'name', 'color']}
        )

        logger.info(f"\n{'='*70}")
        logger.info(f"📊 MARCADORES DO PEDIDO {nome_pedido}")
        logger.info(f"{'='*70}")

        for tag in tags:
            tag_id = tag.get('id')
            tag_name = tag.get('name')
            tag_color = tag.get('color', 0)

            logger.info(f"🏷️  ID: {tag_id:3d} | Nome: {tag_name:40s} | Cor: {tag_color}")

        logger.info(f"{'='*70}\n")

        return tags

    except Exception as e:
        logger.error(f"❌ Erro ao buscar tags do pedido: {e}", exc_info=True)
        return None


if __name__ == '__main__':
    # Pedido a ser consultado
    PEDIDO = 'VCD2563875'

    logger.info(f"🚀 Iniciando busca de marcadores do pedido {PEDIDO}")
    logger.info(f"{'='*70}\n")

    # Busca os tags
    tags = buscar_tags_pedido(PEDIDO)

    if tags:
        logger.info(f"\n✅ Busca concluída com sucesso!")
        logger.info(f"   Total de marcadores encontrados: {len(tags)}")
    else:
        logger.warning(f"\n⚠️ Nenhum marcador encontrado ou erro na busca")
