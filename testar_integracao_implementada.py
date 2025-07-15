#!/usr/bin/env python3
"""
Script para testar a integração implementada
===========================================

Este script testa a integração correta implementada no serviço de faturamento.

Execução:
    python testar_integracao_implementada.py

Autor: Sistema de Fretes - Integração Odoo
Data: 2025-07-14
"""

import logging
import sys
import os
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('teste_integracao.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def testar_integracao():
    """
    Testa a integração de faturamento implementada
    """
    try:
        logger.info("=== TESTE DA INTEGRAÇÃO IMPLEMENTADA ===")
        
        # Importar depois para evitar conflitos
        from app.odoo.services.faturamento_service import FaturamentoService
        
        # Criar instância do serviço
        service = FaturamentoService()
        
        # Testar com filtros específicos
        filtros = {
            'state': 'sale',
            'data_inicio': '2025-07-01'
        }
        
        logger.info(f"Testando importação com filtros: {filtros}")
        
        # Executar importação
        resultado = service.importar_faturamento_odoo(filtros)
        
        logger.info("Resultado da importação:")
        logger.info(f"  - Sucesso: {resultado['success']}")
        logger.info(f"  - Mensagem: {resultado['message']}")
        logger.info(f"  - Total importado: {resultado['total_importado']}")
        logger.info(f"  - Total processado: {resultado['total_processado']}")
        
        if resultado['success']:
            logger.info("✅ Integração funcionou corretamente!")
        else:
            logger.error("❌ Falha na integração")
        
        return resultado
        
    except Exception as e:
        logger.error(f"❌ Erro no teste: {e}")
        return {'success': False, 'error': str(e)}

def testar_mapeamento():
    """
    Testa o mapeamento de campos
    """
    try:
        logger.info("=== TESTE DO MAPEAMENTO DE CAMPOS ===")
        
        from app.odoo.utils.campo_mapper import CampoMapper
        from app.odoo.utils.connection import get_odoo_connection
        
        # Conectar ao Odoo
        connection = get_odoo_connection()
        if not connection:
            logger.error("Falha na conexao com Odoo")
            return False
        
        # Criar mapper
        mapper = CampoMapper()
        
        # Testar busca de dados
        logger.info("Testando busca de dados completos...")
        dados = mapper.buscar_dados_completos(connection, {}, limit=5)
        
        if dados:
            logger.info(f"Dados encontrados: {len(dados)} registros")
            
            # Testar mapeamento para faturamento
            logger.info("Testando mapeamento para faturamento...")
            dados_faturamento = mapper.mapear_para_faturamento(dados)
            
            if dados_faturamento:
                logger.info(f"Mapeamento para faturamento: {len(dados_faturamento)} registros")
                
                # Mostrar exemplo do primeiro registro
                if dados_faturamento:
                    primeiro = dados_faturamento[0]
                    logger.info("Exemplo de registro mapeado:")
                    campos_exemplo = [
                        'nome_pedido', 'codigo_produto', 'nome_produto', 
                        'nome_cliente', 'cnpj_cliente', 'quantidade_produto',
                        'preco_unitario', 'status_pedido'
                    ]
                    for campo in campos_exemplo:
                        valor = primeiro.get(campo)
                        logger.info(f"  {campo}: {valor}")
                    
                    logger.info("Mapeamento funcionou corretamente!")
                    return True
            else:
                logger.error("Falha no mapeamento para faturamento")
                return False
        else:
            logger.error("Nenhum dado encontrado")
            return False
        
    except Exception as e:
        logger.error(f"Erro no teste de mapeamento: {e}")
        return False

def testar_conexao():
    """
    Testa a conexão com o Odoo
    """
    try:
        logger.info("=== TESTE DA CONEXAO COM ODOO ===")
        
        from app.odoo.utils.connection import get_odoo_connection
        
        connection = get_odoo_connection()
        
        if connection:
            logger.info("Conexao com Odoo estabelecida")
            
            # Testar operação simples
            try:
                # Buscar um registro simples
                dados = connection.search_read(
                    'sale.order.line',
                    [],
                    ['id', 'name', 'state'],
                    limit=1
                )
                
                if dados:
                    logger.info(f"Teste de consulta: {len(dados)} registro(s) encontrado(s)")
                    logger.info(f"  Exemplo: {dados[0]}")
                    return True
                else:
                    logger.warning("Nenhum registro encontrado, mas conexao funcionou")
                    return True
            except Exception as e:
                logger.error(f"Erro na consulta: {e}")
                return False
        else:
            logger.error("Falha na conexao com Odoo")
            return False
            
    except Exception as e:
        logger.error(f"Erro no teste de conexao: {e}")
        return False

def main():
    """
    Função principal
    """
    logger.info("Iniciando testes da integração implementada...")
    
    # Teste 1: Conexão
    if not testar_conexao():
        logger.error("❌ Falha no teste de conexão - abortando")
        return
    
    # Teste 2: Mapeamento
    if not testar_mapeamento():
        logger.error("❌ Falha no teste de mapeamento - abortando")
        return
    
    # Teste 3: Integração completa
    resultado = testar_integracao()
    
    if resultado['success']:
        logger.info("\n" + "="*60)
        logger.info("🎉 TODOS OS TESTES PASSARAM COM SUCESSO!")
        logger.info("="*60)
        logger.info("A integração está funcionando corretamente e pronta para uso.")
    else:
        logger.error("\n" + "="*60)
        logger.error("❌ ALGUM TESTE FALHOU")
        logger.error("="*60)
        logger.error("Verifique os logs acima para mais detalhes.")

if __name__ == "__main__":
    main() 