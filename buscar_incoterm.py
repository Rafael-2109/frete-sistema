#!/usr/bin/env python3
"""
Script para buscar Incoterms disponíveis no Odoo
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.odoo.utils.connection import get_odoo_connection
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Conectar
logger.info("Conectando ao Odoo...")
odoo = get_odoo_connection()

# Buscar Incoterms
logger.info("\n🚢 BUSCANDO INCOTERMS...")
incoterms = odoo.search_read(
    'account.incoterms',
    [],
    ['id', 'name', 'code']
)

if incoterms:
    logger.info(f"\n✅ {len(incoterms)} Incoterms encontrados:")
    for inc in incoterms:
        logger.info(f"   • ID: {inc['id']:3} | Código: {inc['code']:10} | Nome: {inc['name']}")
        if 'CIF' in inc['code'].upper():
            logger.info(f"     ⭐ CIF ENCONTRADO! ID = {inc['id']}")
else:
    logger.info("❌ Nenhum Incoterm encontrado")