#!/usr/bin/env python3
"""
Script para testar campos individuais do Odoo
==============================================

Este script testa cada campo individual do CSV para identificar
quais existem no Odoo e quais são inválidos.

Execução:
    python testar_campos_individuais.py

Autor: Sistema de Fretes - Integração Odoo
Data: 2025-07-14
"""

import csv
import json
import logging
from typing import Dict, List, Any

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[
        logging.FileHandler('testar_campos_individuais.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def carregar_campos_csv(arquivo_csv: str) -> List[str]:
    """
    Carrega campos do CSV
    """
    logger.info(f"Carregando campos do arquivo: {arquivo_csv}")
    
    try:
        with open(arquivo_csv, 'r', encoding='utf-8-sig') as f:
            reader = csv.reader(f, delimiter=';')
            
            # Linha 1: Nomes técnicos dos campos
            linha_tecnica = next(reader)
            
            # Remover BOM se presente
            if linha_tecnica and linha_tecnica[0].startswith('\ufeff'):
                linha_tecnica[0] = linha_tecnica[0][1:]
            
            return linha_tecnica
            
    except Exception as e:
        logger.error(f"Erro ao carregar CSV: {e}")
        raise

def testar_campo_individual(campo: str, connection) -> Dict[str, Any]:
    """
    Testa um campo individual no Odoo
    """
    try:
        logger.info(f"Testando campo: {campo}")
        
        # Tentar buscar um registro usando apenas esse campo
        dados = connection.search_read(
            model='sale.order.line',
            domain=[],
            fields=[campo],
            limit=1
        )
        
        if dados:
            exemplo = dados[0]
            valor = exemplo.get(campo)
            
            return {
                'campo': campo,
                'valido': True,
                'valor_exemplo': valor,
                'tipo_valor': type(valor).__name__,
                'erro': None
            }
        else:
            return {
                'campo': campo,
                'valido': False,
                'valor_exemplo': None,
                'tipo_valor': None,
                'erro': 'Nenhum registro encontrado'
            }
            
    except Exception as e:
        return {
            'campo': campo,
            'valido': False,
            'valor_exemplo': None,
            'tipo_valor': None,
            'erro': str(e)
        }

def main():
    """
    Função principal
    """
    logger.info("Iniciando teste de campos individuais...")
    
    # Carregar campos do CSV
    campos = carregar_campos_csv('projeto_carteira/Linha do pedido de venda (sale.order.line) (26).csv')
    logger.info(f"Carregados {len(campos)} campos para testar")
    
    # Conectar ao Odoo
    try:
        from app.odoo.utils.connection import get_odoo_connection
        connection = get_odoo_connection()
        
        # Testar conexão
        resultado_conexao = connection.test_connection()
        if not resultado_conexao['success']:
            logger.error(f"Falha na conexão: {resultado_conexao['message']}")
            return
        
        logger.info("Conexão com Odoo estabelecida com sucesso")
        
    except Exception as e:
        logger.error(f"Erro ao conectar com Odoo: {e}")
        return
    
    # Testar cada campo individual
    resultados = []
    campos_validos = []
    campos_invalidos = []
    
    for i, campo in enumerate(campos):
        logger.info(f"[{i+1}/{len(campos)}] Testando: {campo}")
        
        resultado = testar_campo_individual(campo, connection)
        resultados.append(resultado)
        
        if resultado['valido']:
            campos_validos.append(campo)
            logger.info(f"  ✓ VÁLIDO - Exemplo: {resultado['valor_exemplo']}")
        else:
            campos_invalidos.append(campo)
            logger.info(f"  ✗ INVÁLIDO - Erro: {resultado['erro']}")
    
    # Compilar resultados finais
    resultados_finais = {
        'total_campos': len(campos),
        'campos_validos': len(campos_validos),
        'campos_invalidos': len(campos_invalidos),
        'taxa_sucesso': len(campos_validos) / len(campos) * 100,
        'lista_campos_validos': campos_validos,
        'lista_campos_invalidos': campos_invalidos,
        'detalhes_completos': resultados
    }
    
    # Salvar resultados
    with open('resultados_teste_campos.json', 'w', encoding='utf-8') as f:
        json.dump(resultados_finais, f, indent=2, ensure_ascii=False)
    
    # Relatório final
    logger.info("\n" + "="*80)
    logger.info("RELATÓRIO FINAL - TESTE DE CAMPOS INDIVIDUAIS")
    logger.info("="*80)
    logger.info(f"Total de campos testados: {len(campos)}")
    logger.info(f"Campos válidos: {len(campos_validos)}")
    logger.info(f"Campos inválidos: {len(campos_invalidos)}")
    logger.info(f"Taxa de sucesso: {len(campos_validos)/len(campos)*100:.1f}%")
    
    logger.info("\nCAMPOS VÁLIDOS:")
    for i, campo in enumerate(campos_validos):
        logger.info(f"  {i+1}. {campo}")
    
    logger.info("\nCAMPOS INVÁLIDOS:")
    for i, campo in enumerate(campos_invalidos):
        logger.info(f"  {i+1}. {campo}")
    
    logger.info("\nTeste concluído! Verifique 'resultados_teste_campos.json' para detalhes.")

if __name__ == "__main__":
    main() 