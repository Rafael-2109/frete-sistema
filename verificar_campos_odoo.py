#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
VERIFICAÇÃO DE CAMPOS ODOO
=========================

Verifica se os campos mapeados em mapeamento_carteira.csv realmente 
existem no Odoo e se retornam dados válidos.

Autor: Sistema
Data: 2025-07-15
"""

import logging
import sys
import os
import csv

# Adicionar ao path
sys.path.append(os.path.abspath('.'))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def carregar_mapeamento():
    """Carrega o mapeamento do usuário"""
    try:
        mapeamento = {}
        with open('projeto_carteira/mapeamento_carteira.csv', 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
            for i, line in enumerate(lines):
                line = line.strip()
                if i == 0:  # Header
                    continue
                if not line or line.startswith('#'):
                    continue
                    
                parts = line.split(';')
                if len(parts) >= 3:
                    campo_modelo = parts[0].strip()
                    campo_odoo = parts[2].strip()
                    
                    if campo_modelo and campo_odoo and not campo_modelo.startswith('#'):
                        mapeamento[campo_modelo] = campo_odoo
        
        logger.info(f"✅ Mapeamento carregado: {len(mapeamento)} campos")
        return mapeamento
    except Exception as e:
        logger.error(f"❌ Erro ao carregar mapeamento: {e}")
        return {}

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

def verificar_modelo_fields(connection, modelo, campos_necessarios):
    """Verifica se os campos existem no modelo Odoo"""
    try:
        # Buscar todos os campos do modelo usando interface correta
        fields_info = connection.execute_kw(
            modelo, 'fields_get', [], 
            {'attributes': ['string', 'type', 'relation']}
        )
        
        campos_existentes = set(fields_info.keys())
        campos_verificados = []
        campos_faltando = []
        
        for campo in campos_necessarios:
            # Extrair o campo base (sem relacionamentos)
            campo_base = campo.split('/')[0] if '/' in campo else campo
            
            if campo_base in campos_existentes:
                campos_verificados.append(campo)
                logger.info(f"   ✅ {campo} → {fields_info[campo_base].get('string', 'N/A')}")
            else:
                campos_faltando.append(campo)
                logger.warning(f"   ❌ {campo} → NÃO ENCONTRADO")
        
        return {
            'modelo': modelo,
            'total_campos': len(campos_necessarios),
            'campos_existentes': len(campos_verificados),
            'campos_faltando': len(campos_faltando),
            'lista_faltando': campos_faltando,
            'taxa_sucesso': f"{(len(campos_verificados)/len(campos_necessarios)*100):.1f}%"
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao verificar modelo {modelo}: {e}")
        return None

def organizar_campos_por_modelo(mapeamento):
    """Organiza campos por modelo Odoo"""
    modelos = {
        'sale.order.line': [],  # Linhas de pedido (modelo principal)
        'sale.order': [],       # Pedidos
        'res.partner': [],      # Clientes
        'product.product': [],  # Produtos
        'product.category': [], # Categorias
        'uom.uom': [],          # Unidades de medida
        'account.payment.term': [], # Condições pagamento
    }
    
    for campo_modelo, campo_odoo in mapeamento.items():
        # Analisar campo Odoo para determinar modelo
        if campo_odoo.startswith('order_id/'):
            if 'partner_id/' in campo_odoo:
                # Campo de cliente via pedido
                campo_limpo = campo_odoo.replace('order_id/partner_id/', '')
                modelos['res.partner'].append(campo_limpo)
            elif 'payment_term_id' in campo_odoo:
                modelos['account.payment.term'].append('name')
            else:
                # Campo direto do pedido
                campo_limpo = campo_odoo.replace('order_id/', '')
                modelos['sale.order'].append(campo_limpo)
                
        elif campo_odoo.startswith('product_id/'):
            if 'categ_id/' in campo_odoo:
                # Campo de categoria via produto
                campo_limpo = campo_odoo.replace('product_id/categ_id/', '').replace('parent_id/', '')
                modelos['product.category'].append(campo_limpo)
            elif 'uom_id' in campo_odoo:
                modelos['uom.uom'].append('name')
            else:
                # Campo direto do produto
                campo_limpo = campo_odoo.replace('product_id/', '')
                modelos['product.product'].append(campo_limpo)
                
        else:
            # Campo direto de sale.order.line
            modelos['sale.order.line'].append(campo_odoo)
    
    # Remover duplicatas
    for modelo in modelos:
        modelos[modelo] = list(set(modelos[modelo]))
        if modelos[modelo]:
            logger.info(f"📋 {modelo}: {len(modelos[modelo])} campos únicos")
    
    return modelos

def testar_busca_dados(connection, modelo, campos, limite=5):
    """Testa se consegue buscar dados reais usando os campos"""
    try:
        logger.info(f"🔍 Testando busca em {modelo} com {len(campos)} campos...")
        
        # Buscar poucos registros para teste usando interface correta
        registros = connection.search_read(
            modelo, [], campos, limit=limite
        )
        
        if registros:
            logger.info(f"   ✅ {len(registros)} registros encontrados")
            
            # Mostrar exemplo do primeiro registro
            primeiro = registros[0]
            logger.info("   📄 Exemplo de dados:")
            for campo in campos[:3]:  # Primeiros 3 campos
                valor = primeiro.get(campo, 'N/A')
                if isinstance(valor, list) and len(valor) > 1:
                    valor = f"[{valor[0]}, '{valor[1]}']"
                logger.info(f"      {campo}: {valor}")
                
            return True
        else:
            logger.warning(f"   ⚠️ Nenhum registro encontrado em {modelo}")
            return False
            
    except Exception as e:
        logger.error(f"   ❌ Erro ao buscar dados em {modelo}: {e}")
        return False

def testar_campos_relacionais(connection):
    """Testa especificamente os campos relacionais do mapeamento"""
    logger.info("\n🔗 TESTE ESPECIAL: Campos relacionais")
    
    try:
        # Testar busca com campos relacionais específicos do mapeamento
        campos_teste = [
            'order_id',      # Relacionamento com sale.order
            'product_id',    # Relacionamento com product.product
            'qty_saldo',     # Campo específico brasileiro
            'product_uom_qty', # Quantidade
            'price_unit'     # Preço unitário
        ]
        
        logger.info("🔍 Testando sale.order.line com campos relacionais...")
        registros = connection.search_read(
            'sale.order.line', 
            [('qty_saldo', '>', 0)],  # Filtro carteira pendente
            campos_teste, 
            limit=3
        )
        
        if registros:
            logger.info(f"   ✅ {len(registros)} registros com qty_saldo > 0")
            
            # Verificar estrutura dos dados relacionais
            for i, registro in enumerate(registros[:2]):
                logger.info(f"   📄 Registro {i+1}:")
                
                # Verificar order_id (deve ser [id, "nome"])
                order_id = registro.get('order_id')
                if isinstance(order_id, list) and len(order_id) >= 2:
                    logger.info(f"      ✅ order_id: [{order_id[0]}, '{order_id[1]}']")
                else:
                    logger.warning(f"      ⚠️ order_id formato inesperado: {order_id}")
                
                # Verificar product_id (deve ser [id, "nome"])
                product_id = registro.get('product_id')
                if isinstance(product_id, list) and len(product_id) >= 2:
                    logger.info(f"      ✅ product_id: [{product_id[0]}, '{product_id[1]}']")
                else:
                    logger.warning(f"      ⚠️ product_id formato inesperado: {product_id}")
                    
                # Verificar qty_saldo
                qty_saldo = registro.get('qty_saldo')
                logger.info(f"      📊 qty_saldo: {qty_saldo}")
                
            return True
        else:
            logger.warning("   ⚠️ Nenhum registro com qty_saldo > 0 encontrado")
            return False
            
    except Exception as e:
        logger.error(f"   ❌ Erro no teste de campos relacionais: {e}")
        return False

def main():
    """Executa verificação completa"""
    logger.info("=" * 60)
    logger.info("🔍 VERIFICAÇÃO DE CAMPOS ODOO")
    logger.info("=" * 60)
    
    # 1. Carregar mapeamento
    logger.info("\n📋 PASSO 1: Carregando mapeamento...")
    mapeamento = carregar_mapeamento()
    if not mapeamento:
        logger.error("❌ Falha ao carregar mapeamento")
        return
    
    # 2. Conectar Odoo
    logger.info("\n🔗 PASSO 2: Conectando ao Odoo...")
    connection = conectar_odoo()
    if not connection:
        logger.error("❌ Falha na conexão com Odoo")
        return
    
    # 3. Organizar campos por modelo
    logger.info("\n📊 PASSO 3: Organizando campos por modelo...")
    modelos_campos = organizar_campos_por_modelo(mapeamento)
    
    # 4. Verificar cada modelo
    logger.info("\n🔍 PASSO 4: Verificando existência dos campos...")
    resultados = []
    
    for modelo, campos in modelos_campos.items():
        if not campos:
            continue
            
        logger.info(f"\n🏷️ Verificando modelo: {modelo}")
        resultado = verificar_modelo_fields(connection, modelo, campos)
        if resultado:
            resultados.append(resultado)
    
    # 5. Testar busca de dados
    logger.info("\n🧪 PASSO 5: Testando busca de dados reais...")
    
    # Testar sale.order.line (modelo principal)
    campos_teste = ['qty_saldo', 'product_uom_qty', 'price_unit']
    testar_busca_dados(connection, 'sale.order.line', campos_teste)
    
    # 6. Testar campos relacionais
    testar_campos_relacionais(connection)

    # 7. Relatório final
    logger.info("\n" + "=" * 60)
    logger.info("📊 RELATÓRIO FINAL")
    logger.info("=" * 60)
    
    total_campos = 0
    total_existentes = 0
    
    for resultado in resultados:
        total_campos += resultado['total_campos']
        total_existentes += resultado['campos_existentes']
        
        logger.info(f"📋 {resultado['modelo']}")
        logger.info(f"   ✅ Existentes: {resultado['campos_existentes']}/{resultado['total_campos']} ({resultado['taxa_sucesso']})")
        
        if resultado['campos_faltando'] > 0:
            logger.warning(f"   ❌ Faltando: {resultado['lista_faltando'][:3]}...")
    
    taxa_geral = f"{(total_existentes/total_campos*100):.1f}%" if total_campos > 0 else "0%"
    logger.info(f"\n🎯 RESULTADO GERAL: {total_existentes}/{total_campos} campos ({taxa_geral})")
    
    if total_existentes == total_campos:
        logger.info("🎉 SUCESSO! Todos os campos existem no Odoo")
    elif total_existentes / total_campos > 0.8:
        logger.info("✅ BOM! Maioria dos campos existe no Odoo")
    else:
        logger.warning("⚠️ ATENÇÃO! Muitos campos faltando no Odoo")
    
    logger.info("=" * 60)

if __name__ == "__main__":
    main() 