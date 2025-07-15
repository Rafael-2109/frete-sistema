#!/usr/bin/env python3
"""
Teste Simplificado de Integração Odoo
=====================================

Teste apenas de busca e mapeamento de dados, sem salvar no banco.
"""

import logging
import sys
import os
from datetime import datetime

# Adicionar path do projeto
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def testar_mapeamento_completo():
    """
    Testa mapeamento completo sem salvar no banco
    """
    try:
        logger.info("=== TESTE DE MAPEAMENTO COMPLETO ===")
        
        from app.odoo.utils.campo_mapper import CampoMapper
        from app.odoo.utils.connection import get_odoo_connection
        
        # Conectar ao Odoo
        connection = get_odoo_connection()
        if not connection:
            logger.error("Falha na conexão com Odoo")
            return False
        
        logger.info("Conexão com Odoo estabelecida")
        
        # Criar mapper
        mapper = CampoMapper()
        
        # Filtros de teste
        filtros = {
            'state': 'sale'
        }
        
        # Buscar dados completos
        logger.info(f"Buscando dados com filtros: {filtros}")
        dados_integrados = mapper.buscar_dados_completos(connection, filtros, limit=10)
        
        if dados_integrados:
            logger.info(f"✓ Dados integrados: {len(dados_integrados)} registros")
            
            # Mapear para faturamento
            dados_faturamento = mapper.mapear_para_faturamento(dados_integrados)
            logger.info(f"✓ Mapeamento faturamento: {len(dados_faturamento)} registros")
            
            # Mapear para carteira
            dados_carteira = mapper.mapear_para_carteira(dados_integrados)
            logger.info(f"✓ Mapeamento carteira: {len(dados_carteira)} registros")
            
            # Mostrar exemplo de dados
            if dados_faturamento:
                logger.info("=== EXEMPLO DE FATURAMENTO ===")
                exemplo = dados_faturamento[0]
                for campo, valor in exemplo.items():
                    if valor is not None:
                        logger.info(f"  {campo}: {valor}")
            
            if dados_carteira:
                logger.info("=== EXEMPLO DE CARTEIRA ===")
                exemplo = dados_carteira[0]
                for campo, valor in exemplo.items():
                    if valor is not None:
                        logger.info(f"  {campo}: {valor}")
            
            return True
        else:
            logger.warning("Nenhum dado encontrado")
            return False
        
    except Exception as e:
        logger.error(f"Erro no teste de mapeamento: {e}")
        return False

def testar_conectividade():
    """
    Testa conectividade básica com Odoo
    """
    try:
        logger.info("=== TESTE DE CONECTIVIDADE ===")
        
        from app.odoo.utils.connection import get_odoo_connection
        
        connection = get_odoo_connection()
        if not connection:
            logger.error("Falha na conexão")
            return False
        
        # Testar autenticação
        result = connection.test_connection()
        
        if result.get('success'):
            logger.info(f"✓ Conexão OK - Versão: {result.get('version', 'N/A')}")
            logger.info(f"✓ Usuário: {result.get('username', 'N/A')}")
            logger.info(f"✓ Banco: {result.get('database', 'N/A')}")
            return True
        else:
            logger.error(f"✗ Falha na conexão: {result.get('error', 'Erro desconhecido')}")
            return False
        
    except Exception as e:
        logger.error(f"Erro no teste de conectividade: {e}")
        return False

def main():
    """
    Função principal
    """
    logger.info("=== TESTE SIMPLIFICADO DE INTEGRAÇÃO ODOO ===")
    logger.info(f"Iniciado em: {datetime.now()}")
    
    testes = [
        ("Conectividade", testar_conectividade),
        ("Mapeamento Completo", testar_mapeamento_completo)
    ]
    
    resultados = []
    
    for nome, teste in testes:
        logger.info(f"\n--- EXECUTANDO: {nome} ---")
        try:
            resultado = teste()
            resultados.append((nome, resultado))
            
            if resultado:
                logger.info(f"✓ {nome}: SUCESSO")
            else:
                logger.error(f"✗ {nome}: FALHA")
                
        except Exception as e:
            logger.error(f"✗ {nome}: ERRO - {e}")
            resultados.append((nome, False))
    
    # Resumo final
    logger.info("\n=== RESUMO FINAL ===")
    sucessos = sum(1 for _, resultado in resultados if resultado)
    total = len(resultados)
    
    for nome, resultado in resultados:
        status = "✓ SUCESSO" if resultado else "✗ FALHA"
        logger.info(f"  {nome}: {status}")
    
    logger.info(f"\nTotal: {sucessos}/{total} testes bem-sucedidos")
    
    if sucessos == total:
        logger.info("🎉 TODOS OS TESTES PASSARAM!")
        logger.info("🚀 Integração Odoo está funcionando corretamente!")
        return True
    else:
        logger.error("❌ ALGUNS TESTES FALHARAM")
        return False

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\nTeste interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Erro fatal: {e}")
        sys.exit(1) 