#!/usr/bin/env python3
"""
Teste da integração Odoo com contexto Flask
============================================

Este script testa a integração com Odoo usando contexto Flask
para resolver problemas de "Working outside of application context"
"""

import logging
import sys
import os
from datetime import datetime

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

def criar_app_context():
    """
    Cria contexto Flask para o teste
    """
    try:
        from app import create_app
        
        # Criar aplicação Flask
        app = create_app()
        
        # Retornar contexto da aplicação
        return app.app_context()
        
    except Exception as e:
        logger.error(f"Erro ao criar contexto Flask: {e}")
        return None

def testar_mapeamento_simples():
    """
    Testa o mapeamento de campos básico
    """
    try:
        logger.info("=== TESTE DE MAPEAMENTO SIMPLES ===")
        
        from app.odoo.utils.campo_mapper import CampoMapper
        from app.odoo.utils.connection import get_odoo_connection
        
        # Conectar ao Odoo
        connection = get_odoo_connection()
        if not connection:
            logger.error("Falha na conexao com Odoo")
            return False
        
        logger.info("Conexao com Odoo estabelecida")
        
        # Criar mapper
        mapper = CampoMapper()
        
        # Testar busca simples (poucos registros)
        logger.info("Testando busca de dados simples...")
        dados = mapper.buscar_dados_completos(connection, {}, limit=3)
        
        if dados:
            logger.info(f"Dados encontrados: {len(dados)} registros")
            
            # Mostrar estrutura do primeiro registro
            if dados:
                primeiro = dados[0]
                logger.info("Campos do primeiro registro:")
                for campo, valor in primeiro.items():
                    if valor is not None:
                        logger.info(f"  {campo}: {valor}")
                
                return True
        else:
            logger.warning("Nenhum dado encontrado")
            return False
        
    except Exception as e:
        logger.error(f"Erro no teste de mapeamento: {e}")
        return False

def testar_integracao_com_contexto():
    """
    Testa integração completa com contexto Flask
    """
    try:
        logger.info("=== TESTE DE INTEGRAÇÃO COM CONTEXTO ===")
        
        # Criar contexto Flask
        app_context = criar_app_context()
        if not app_context:
            logger.error("Falha ao criar contexto Flask")
            return False
        
        with app_context:
            # Dentro do contexto Flask
            from app.odoo.services.faturamento_service import FaturamentoService
            
            # Criar serviço
            service = FaturamentoService()
            
            # Filtros simples
            filtros = {
                'state': 'sale'
            }
            
            logger.info(f"Testando importação com filtros: {filtros}")
            
            # Executar importação (sem parâmetro limit)
            resultado = service.importar_faturamento_odoo(filtros)
            
            if resultado.get('success'):  # Chave correta é 'success'
                logger.info("Integração bem-sucedida!")
                logger.info(f"Total processado: {resultado.get('total_processado', 0)}")
                logger.info(f"Total importado: {resultado.get('total_importado', 0)}")
                return True
            else:
                logger.error(f"Falha na integração: {resultado.get('message', 'Erro desconhecido')}")
                return False
        
    except Exception as e:
        logger.error(f"Erro na integração com contexto: {e}")
        return False

def testar_conexao_basica():
    """
    Testa apenas a conexão básica
    """
    try:
        logger.info("=== TESTE DE CONEXÃO BÁSICA ===")
        
        from app.odoo.utils.connection import get_odoo_connection
        
        connection = get_odoo_connection()
        
        if connection:
            logger.info("Conexao com Odoo estabelecida")
            
            # Testar consulta simples
            try:
                dados = connection.search_read(
                    'sale.order.line',
                    [],
                    ['id', 'name'],
                    limit=1
                )
                
                if dados:
                    logger.info(f"Consulta simples: {len(dados)} registro(s) encontrado(s)")
                    logger.info(f"  Exemplo: {dados[0]}")
                    return True
                else:
                    logger.warning("Nenhum registro encontrado na consulta simples")
                    return True  # Ainda é sucesso se a conexão funciona
            except Exception as e:
                logger.error(f"Erro na consulta simples: {e}")
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
    logger.info("=== TESTE DE INTEGRAÇÃO ODOO COM CONTEXTO FLASK ===")
    logger.info(f"Iniciado em: {datetime.now()}")
    
    testes = [
        ("Conexão Básica", testar_conexao_basica),
        ("Mapeamento Simples", testar_mapeamento_simples),
        ("Integração com Contexto", testar_integracao_com_contexto)
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
        logger.info("TODOS OS TESTES PASSARAM!")
        return True
    else:
        logger.error("ALGUNS TESTES FALHARAM")
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