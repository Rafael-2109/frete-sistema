#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICAÇÃO COMPLETA DO MAPEAMENTO
=================================

Verifica TODOS os 38 campos do mapeamento_carteira.csv 
individualmente no Odoo, sem agrupamento por modelo.

Autor: Sistema
Data: 2025-07-15
"""

import logging
import sys
import os

# Adicionar ao path
sys.path.append(os.path.abspath('.'))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def carregar_mapeamento_completo():
    """Carrega TODOS os campos do mapeamento do usuário"""
    try:
        mapeamento = []
        with open('projeto_carteira/mapeamento_carteira.csv', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            for i, line in enumerate(lines):
                line = line.strip()
                if i == 0:  # Header
                    continue
                if not line or line.startswith('#'):
                    continue
                    
                parts = line.split(';')
                if len(parts) >= 4:
                    campo_modelo = parts[0].strip()
                    nome_excel = parts[1].strip()
                    campo_odoo = parts[2].strip()
                    significado = parts[3].strip()
                    
                    if campo_modelo and campo_odoo and not campo_modelo.startswith('#'):
                        mapeamento.append({
                            'campo_modelo': campo_modelo,
                            'nome_excel': nome_excel,
                            'campo_odoo': campo_odoo,
                            'significado': significado
                        })
        
        logger.info(f"✅ Mapeamento completo carregado: {len(mapeamento)} campos")
        return mapeamento
    except Exception as e:
        logger.error(f"❌ Erro ao carregar mapeamento: {e}")
        return []

def conectar_odoo():
    """Conecta ao Odoo"""
    try:
        from app.odoo.utils.connection import get_odoo_connection
        connection = get_odoo_connection()
        if connection:
            logger.info("✅ Conexão com Odoo estabelecida")
            return connection
        else:
            logger.error("❌ Falha na conexão com Odoo")
            return None
    except Exception as e:
        logger.error(f"❌ Erro ao conectar Odoo: {e}")
        return None

def extrair_modelo_e_campo(campo_odoo):
    """Extrai modelo base e campo base do campo Odoo"""
    # Mapear prefixos para modelos
    if campo_odoo.startswith('order_id/'):
        if 'partner_id/' in campo_odoo:
            if 'partner_shipping_id/' in campo_odoo:
                # order_id/partner_shipping_id/campo -> res.partner
                campo_base = campo_odoo.split('/')[-1]
                return 'res.partner', campo_base
            else:
                # order_id/partner_id/campo -> res.partner  
                campo_base = campo_odoo.replace('order_id/partner_id/', '')
                return 'res.partner', campo_base
        elif 'payment_term_id' in campo_odoo:
            return 'account.payment.term', 'name'
        elif 'payment_provider_id' in campo_odoo:
            return 'payment.provider', 'name'
        else:
            # order_id/campo -> sale.order
            campo_base = campo_odoo.replace('order_id/', '')
            return 'sale.order', campo_base
            
    elif campo_odoo.startswith('product_id/'):
        if 'categ_id/' in campo_odoo:
            # product_id/categ_id/campo -> product.category
            campo_base = campo_odoo.replace('product_id/categ_id/', '').replace('parent_id/', '')
            return 'product.category', campo_base
        elif 'uom_id' in campo_odoo:
            return 'uom.uom', 'name'
        else:
            # product_id/campo -> product.product
            campo_base = campo_odoo.replace('product_id/', '')
            return 'product.product', campo_base
            
    else:
        # Campo direto de sale.order.line
        return 'sale.order.line', campo_odoo

def verificar_campo_individual(connection, modelo, campo, campo_odoo_original):
    """Verifica se um campo específico existe no modelo"""
    try:
        # Buscar todos os campos do modelo
        fields_info = connection.execute_kw(
            modelo, 'fields_get', [], 
            {'attributes': ['string', 'type', 'relation']}
        )
        
        campos_existentes = set(fields_info.keys())
        
        # Verificar se o campo existe
        if campo in campos_existentes:
            field_info = fields_info[campo]
            return {
                'existe': True,
                'modelo': modelo,
                'campo': campo,
                'campo_odoo_original': campo_odoo_original,
                'tipo': field_info.get('type', 'N/A'),
                'descricao': field_info.get('string', 'N/A'),
                'relacao': field_info.get('relation', 'N/A')
            }
        else:
            return {
                'existe': False,
                'modelo': modelo,
                'campo': campo,
                'campo_odoo_original': campo_odoo_original,
                'erro': f"Campo '{campo}' não encontrado em '{modelo}'"
            }
        
    except Exception as e:
        return {
            'existe': False,
            'modelo': modelo,
            'campo': campo,
            'campo_odoo_original': campo_odoo_original,
            'erro': f"Erro ao verificar: {e}"
        }

def main():
    """Executa verificação campo por campo"""
    logger.info("=" * 70)
    logger.info("🔍 VERIFICAÇÃO COMPLETA DO MAPEAMENTO - CAMPO POR CAMPO")
    logger.info("=" * 70)
    
    # 1. Carregar mapeamento completo
    logger.info("\n📋 PASSO 1: Carregando mapeamento completo...")
    mapeamento = carregar_mapeamento_completo()
    if not mapeamento:
        logger.error("❌ Falha ao carregar mapeamento")
        return
    
    logger.info(f"📊 Total de campos no mapeamento: {len(mapeamento)}")
    
    # 2. Conectar Odoo
    logger.info("\n🔗 PASSO 2: Conectando ao Odoo...")
    connection = conectar_odoo()
    if not connection:
        logger.error("❌ Falha na conexão com Odoo")
        return
    
    # 3. Verificar campo por campo
    logger.info("\n🔍 PASSO 3: Verificando cada campo individualmente...")
    
    resultados = []
    campos_existentes = 0
    campos_faltando = 0
    
    for i, item in enumerate(mapeamento, 1):
        campo_modelo = item['campo_modelo']
        campo_odoo = item['campo_odoo']
        
        logger.info(f"\n📋 [{i:02d}/{len(mapeamento)}] {campo_modelo}")
        logger.info(f"    🔗 Campo Odoo: {campo_odoo}")
        
        # Extrair modelo e campo base
        modelo, campo_base = extrair_modelo_e_campo(campo_odoo)
        logger.info(f"    🏷️ Modelo: {modelo} | Campo: {campo_base}")
        
        # Verificar campo
        resultado = verificar_campo_individual(connection, modelo, campo_base, campo_odoo)
        resultados.append(resultado)
        
        if resultado['existe']:
            campos_existentes += 1
            logger.info(f"    ✅ EXISTE: {resultado['descricao']} ({resultado['tipo']})")
        else:
            campos_faltando += 1
            logger.error(f"    ❌ FALTANDO: {resultado['erro']}")
    
    # 4. Relatório final detalhado
    logger.info("\n" + "=" * 70)
    logger.info("📊 RELATÓRIO FINAL DETALHADO")
    logger.info("=" * 70)
    
    logger.info(f"\n🎯 RESULTADO GERAL:")
    logger.info(f"   ✅ Campos existentes: {campos_existentes}")
    logger.info(f"   ❌ Campos faltando: {campos_faltando}")
    logger.info(f"   📊 Total verificado: {len(mapeamento)}")
    
    taxa_sucesso = (campos_existentes / len(mapeamento) * 100) if mapeamento else 0
    logger.info(f"   📈 Taxa de sucesso: {taxa_sucesso:.1f}%")
    
    # Listar campos faltando (se houver)
    if campos_faltando > 0:
        logger.info(f"\n❌ CAMPOS FALTANDO ({campos_faltando}):")
        for resultado in resultados:
            if not resultado['existe']:
                logger.error(f"   • {resultado['campo_odoo_original']} → {resultado['erro']}")
    
    # Agrupamento por modelo
    logger.info(f"\n📋 AGRUPAMENTO POR MODELO:")
    modelos_count = {}
    for resultado in resultados:
        modelo = resultado['modelo']
        if modelo not in modelos_count:
            modelos_count[modelo] = {'existentes': 0, 'total': 0}
        modelos_count[modelo]['total'] += 1
        if resultado['existe']:
            modelos_count[modelo]['existentes'] += 1
    
    for modelo, counts in modelos_count.items():
        taxa = (counts['existentes'] / counts['total'] * 100) if counts['total'] > 0 else 0
        logger.info(f"   📋 {modelo}: {counts['existentes']}/{counts['total']} ({taxa:.1f}%)")
    
    # Conclusão final
    logger.info(f"\n🎯 CONCLUSÃO:")
    if campos_faltando == 0:
        logger.info("🎉 SUCESSO TOTAL! Todos os campos do mapeamento existem no Odoo")
        logger.info("✅ Mapeamento 100% válido para produção")
    elif taxa_sucesso >= 95:
        logger.info("✅ QUASE PERFEITO! Poucos campos faltando")
        logger.info("⚠️ Revisar campos faltando antes de usar em produção")
    else:
        logger.warning("⚠️ ATENÇÃO! Muitos campos faltando")
        logger.warning("❌ Mapeamento precisa ser corrigido antes da produção")
    
    logger.info("=" * 70)

if __name__ == "__main__":
    main() 