#!/usr/bin/env python3
"""
Script para listar todas as empresas cadastradas no Odoo
Data: 2025-01-25
"""

import sys
import os

# Adicionar o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.odoo.utils.connection import get_odoo_connection
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def listar_empresas():
    """
    Lista todas as empresas cadastradas no Odoo
    """
    try:
        # Conectar ao Odoo
        logger.info("🔌 Conectando ao Odoo...")
        odoo = get_odoo_connection()
        
        if not odoo:
            logger.error("❌ Não foi possível conectar ao Odoo")
            return None
        
        # Buscar todas as empresas
        logger.info("🏢 Buscando empresas cadastradas no Odoo...")
        empresas = odoo.search_read(
            'res.company',
            [],  # Sem filtros - buscar todas
            ['id', 'name', 'partner_id', 'currency_id', 'email', 'phone', 'website', 'vat', 'street', 'city', 'state_id', 'country_id']
        )
        
        logger.info(f"\n✅ Total de empresas encontradas: {len(empresas)}")
        logger.info("="*70)
        
        for i, emp in enumerate(empresas, 1):
            logger.info(f"\n🏢 EMPRESA {i}:")
            logger.info(f"   📋 Nome: {emp['name']}")
            logger.info(f"   🆔 ID: {emp['id']}")
            logger.info(f"   👤 Partner ID: {emp['partner_id'][0] if emp.get('partner_id') else 'N/A'}")
            logger.info(f"   💰 Moeda: {emp['currency_id'][1] if emp.get('currency_id') else 'N/A'}")
            logger.info(f"   📧 Email: {emp.get('email', 'N/A')}")
            logger.info(f"   📞 Telefone: {emp.get('phone', 'N/A')}")
            logger.info(f"   🌐 Website: {emp.get('website', 'N/A')}")
            logger.info(f"   📑 CNPJ/VAT: {emp.get('vat', 'N/A')}")
            logger.info(f"   📍 Endereço: {emp.get('street', 'N/A')}")
            logger.info(f"   🏙️ Cidade: {emp.get('city', 'N/A')}")
            logger.info(f"   🌍 Estado: {emp['state_id'][1] if emp.get('state_id') else 'N/A'}")
            logger.info(f"   🌎 País: {emp['country_id'][1] if emp.get('country_id') else 'N/A'}")
            logger.info("-"*70)
        
        # Procurar especificamente por NACOM ou GOYA
        logger.info("\n🔍 Procurando empresas NACOM/GOYA:")
        empresas_nacom = [emp for emp in empresas if 'NACOM' in emp['name'].upper() or 'GOYA' in emp['name'].upper()]
        
        if empresas_nacom:
            logger.info(f"✅ Encontradas {len(empresas_nacom)} empresa(s) NACOM/GOYA:")
            for emp in empresas_nacom:
                logger.info(f"   • {emp['name']} (ID: {emp['id']})")
        else:
            logger.info("❌ Nenhuma empresa NACOM ou GOYA encontrada")
        
        # Buscar também armazéns de cada empresa
        logger.info("\n🏭 ARMAZÉNS POR EMPRESA:")
        logger.info("="*70)
        
        for emp in empresas:
            armazens = odoo.search_read(
                'stock.warehouse',
                [('company_id', '=', emp['id'])],
                ['id', 'name', 'code']
            )
            
            if armazens:
                logger.info(f"\n🏢 {emp['name']} (ID: {emp['id']}):")
                for arm in armazens:
                    logger.info(f"   🏭 {arm['name']} - Código: {arm['code']} (ID: {arm['id']})")
            else:
                logger.info(f"\n🏢 {emp['name']} (ID: {emp['id']}): Sem armazéns cadastrados")
        
        return empresas
        
    except Exception as e:
        logger.error(f"❌ Erro ao listar empresas: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    logger.info("🚀 Iniciando listagem de empresas do Odoo...")
    logger.info("="*70)
    
    empresas = listar_empresas()
    
    if empresas:
        logger.info(f"\n✅ Listagem concluída! Total de {len(empresas)} empresa(s) encontrada(s)")
    else:
        logger.error("\n❌ Falha ao listar empresas")