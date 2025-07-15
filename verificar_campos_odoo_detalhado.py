#!/usr/bin/env python3
"""
Script para verificar campos disponíveis em modelos do Odoo
===========================================================

Identifica quais campos realmente existem nos modelos
para corrigir os erros de validação.
"""

import logging
import sys
import os

# Adicionar path do projeto
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Configurar logging sem emojis
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def verificar_campos_modelo(connection, model_name, campos_teste):
    """
    Verifica quais campos existem em um modelo específico
    """
    logger.info(f"Verificando campos do modelo: {model_name}")
    
    campos_validos = []
    campos_invalidos = []
    
    for campo in campos_teste:
        try:
            # Tenta fazer uma consulta simples com o campo
            resultado = connection.search_read(
                model_name,
                [],
                [campo],
                limit=1
            )
            campos_validos.append(campo)
            logger.info(f"  ✓ {campo} - VÁLIDO")
        except Exception as e:
            campos_invalidos.append(campo)
            if "Invalid field" in str(e):
                logger.error(f"  ✗ {campo} - INVÁLIDO")
            else:
                logger.warning(f"  ? {campo} - ERRO: {str(e)[:100]}")
    
    return campos_validos, campos_invalidos

def verificar_todos_modelos(connection):
    """
    Verifica campos em todos os modelos problemáticos
    """
    modelos_teste = {
        'product.product': [
            'id', 'name', 'default_code', 'list_price', 
            'standard_price', 'categ_id', 'warranty',
            'type', 'uom_id', 'description', 'active'
        ],
        'res.partner': [
            'id', 'name', 'vat', 'street', 'city', 'state_id',
            'country_id', 'phone', 'email', 'l10n_br_isuf',
            'l10n_br_cnpj_cpf', 'customer_rank', 'supplier_rank'
        ],
        'delivery.carrier': [
            'id', 'name', 'partner_id', 'product_id',
            'delivery_type', 'fixed_price', 'active'
        ],
        'sale.order': [
            'id', 'name', 'partner_id', 'date_order', 'state',
            'amount_total', 'currency_id', 'user_id'
        ],
        'sale.order.line': [
            'id', 'name', 'product_id', 'product_uom_qty',
            'price_unit', 'order_id', 'state'
        ]
    }
    
    resultados = {}
    
    for modelo, campos in modelos_teste.items():
        logger.info(f"\n=== VERIFICANDO MODELO: {modelo} ===")
        validos, invalidos = verificar_campos_modelo(connection, modelo, campos)
        
        resultados[modelo] = {
            'validos': validos,
            'invalidos': invalidos,
            'total_testados': len(campos),
            'percentual_valido': (len(validos) / len(campos)) * 100
        }
        
        logger.info(f"Resultado: {len(validos)}/{len(campos)} campos válidos "
                   f"({resultados[modelo]['percentual_valido']:.1f}%)")
    
    return resultados

def gerar_mapeamento_corrigido(resultados):
    """
    Gera mapeamento corrigido baseado nos campos válidos
    """
    logger.info("\n=== GERANDO MAPEAMENTO CORRIGIDO ===")
    
    mapeamento = {
        'sale.order.line': {
            'obrigatorios': ['id', 'product_id', 'order_id'],
            'opcionais': []
        },
        'product.product': {
            'obrigatorios': ['id', 'name'],
            'opcionais': []
        },
        'res.partner': {
            'obrigatorios': ['id', 'name'],
            'opcionais': []
        },
        'delivery.carrier': {
            'obrigatorios': ['id', 'name'],
            'opcionais': []
        }
    }
    
    # Preencher com campos válidos
    for modelo, dados in resultados.items():
        if modelo in mapeamento:
            for campo in dados['validos']:
                if campo not in mapeamento[modelo]['obrigatorios']:
                    mapeamento[modelo]['opcionais'].append(campo)
    
    # Salvar arquivo
    with open('mapeamento_corrigido.py', 'w', encoding='utf-8') as f:
        f.write('# Mapeamento corrigido baseado em verificação real\n')
        f.write('# Gerado automaticamente em 2025-07-15\n\n')
        f.write('CAMPOS_VALIDOS = {\n')
        
        for modelo, dados in mapeamento.items():
            f.write(f'    "{modelo}": {{\n')
            f.write(f'        "obrigatorios": {dados["obrigatorios"]},\n')
            f.write(f'        "opcionais": {dados["opcionais"]}\n')
            f.write('    },\n')
        
        f.write('}\n')
    
    logger.info("Arquivo mapeamento_corrigido.py criado com sucesso!")
    return mapeamento

def main():
    """
    Função principal
    """
    try:
        logger.info("=== VERIFICAÇÃO DETALHADA DE CAMPOS ODOO ===")
        
        # Importar conexão
        from app.odoo.utils.connection import get_odoo_connection
        
        # Conectar
        connection = get_odoo_connection()
        if not connection:
            logger.error("Falha na conexão com Odoo")
            return False
        
        logger.info("Conexão com Odoo estabelecida")
        
        # Verificar todos os modelos
        resultados = verificar_todos_modelos(connection)
        
        # Gerar mapeamento corrigido
        mapeamento = gerar_mapeamento_corrigido(resultados)
        
        # Resumo final
        logger.info("\n=== RESUMO FINAL ===")
        for modelo, dados in resultados.items():
            logger.info(f"{modelo}: {dados['percentual_valido']:.1f}% campos válidos")
            if dados['invalidos']:
                logger.info(f"  Campos inválidos: {', '.join(dados['invalidos'])}")
        
        logger.info("\nVerificação concluída com sucesso!")
        logger.info("Use o arquivo mapeamento_corrigido.py para atualizar o código.")
        
        return True
        
    except Exception as e:
        logger.error(f"Erro na verificação: {e}")
        return False

if __name__ == "__main__":
    main() 