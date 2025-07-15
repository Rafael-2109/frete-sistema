#!/usr/bin/env python3
"""
Script para descobrir campos corretos no Odoo baseado no CSV
============================================================

Este script analisa o CSV fornecido e tenta buscar os campos corretos no Odoo
para garantir que extraímos as informações corretas.

Execução:
    python descobrir_campos_odoo.py

Autor: Sistema de Fretes - Integração Odoo
Data: 2025-07-14
"""

import csv
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('descobrir_campos_odoo.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def carregar_campos_csv(arquivo_csv: str) -> Dict[str, Any]:
    """
    Carrega campos do CSV e extrai informações estruturadas
    """
    logger.info(f"Carregando campos do arquivo: {arquivo_csv}")
    
    try:
        with open(arquivo_csv, 'r', encoding='utf-8-sig') as f:  # utf-8-sig remove BOM automaticamente
            reader = csv.reader(f, delimiter=';')
            
            # Linha 1: Nomes técnicos dos campos
            linha_tecnica = next(reader)
            
            # Linha 2: Nomes descritivos dos campos  
            linha_descritiva = next(reader)
            
            # Resto: Dados de exemplo
            dados_exemplo = []
            for i, linha in enumerate(reader):
                if i >= 80:  # Limitar a 80 registros
                    break
                dados_exemplo.append(linha)
            
            # Remover BOM do primeiro campo se presente
            if linha_tecnica and linha_tecnica[0].startswith('\ufeff'):
                linha_tecnica[0] = linha_tecnica[0][1:]
                logger.info("BOM removido do primeiro campo")
            
            logger.info(f"Carregados {len(linha_tecnica)} campos e {len(dados_exemplo)} registros de exemplo")
            
            return {
                'campos_tecnicos': linha_tecnica,
                'campos_descritivos': linha_descritiva,
                'dados_exemplo': dados_exemplo,
                'total_campos': len(linha_tecnica),
                'total_registros_exemplo': len(dados_exemplo)
            }
            
    except Exception as e:
        logger.error(f"Erro ao carregar CSV: {e}")
        raise

def analisar_campos_odoo(campos_tecnicos: List[str]) -> Dict[str, Any]:
    """
    Analisa os campos técnicos para entender a estrutura do Odoo
    """
    logger.info("🔍 Analisando estrutura dos campos do Odoo...")
    
    # Categorizar campos por tipo
    campos_diretos = []
    campos_relacionados = []
    campos_hierarquicos = []
    
    for campo in campos_tecnicos:
        if '/' not in campo:
            campos_diretos.append(campo)
        elif campo.count('/') == 1:
            campos_relacionados.append(campo)
        else:
            campos_hierarquicos.append(campo)
    
    # Identificar modelos relacionados
    modelos_relacionados = set()
    for campo in campos_relacionados + campos_hierarquicos:
        if '/' in campo:
            modelo = campo.split('/')[0]
            modelos_relacionados.add(modelo)
    
    logger.info(f"📊 Análise concluída:")
    logger.info(f"   • Campos diretos: {len(campos_diretos)}")
    logger.info(f"   • Campos relacionados: {len(campos_relacionados)}")
    logger.info(f"   • Campos hierárquicos: {len(campos_hierarquicos)}")
    logger.info(f"   • Modelos relacionados: {list(modelos_relacionados)}")
    
    return {
        'campos_diretos': campos_diretos,
        'campos_relacionados': campos_relacionados,
        'campos_hierarquicos': campos_hierarquicos,
        'modelos_relacionados': list(modelos_relacionados),
        'total_campos': len(campos_tecnicos)
    }

def testar_conexao_odoo() -> bool:
    """
    Testa conexão com o Odoo
    """
    logger.info("🔗 Testando conexão com Odoo...")
    
    try:
        from app.odoo.utils.connection import get_odoo_connection
        
        connection = get_odoo_connection()
        resultado = connection.test_connection()
        
        if resultado['success']:
            logger.info("✅ Conexão com Odoo estabelecida com sucesso")
            logger.info(f"   • Versão: {resultado['data']['version']}")
            logger.info(f"   • Database: {resultado['data']['database']}")
            logger.info(f"   • Usuário: {resultado['data']['user']['name']}")
            return True
        else:
            logger.error(f"❌ Falha na conexão: {resultado['message']}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Erro na conexão: {e}")
        return False

def buscar_dados_odoo(campos: List[str], limite: int = 80) -> Dict[str, Any]:
    """
    Busca dados no Odoo usando os campos identificados
    """
    logger.info(f"🔍 Buscando dados no Odoo com {len(campos)} campos...")
    
    try:
        from app.odoo.utils.connection import get_odoo_connection
        
        connection = get_odoo_connection()
        
        # Domínio para buscar registros com saldo (carteira pendente)
        domain = [['qty_saldo', '>', 0]]
        
        logger.info(f"📋 Campos a buscar: {campos[:10]}...")  # Mostrar primeiros 10
        
        # Buscar dados do Odoo
        dados = connection.search_read(
            model='sale.order.line',
            domain=domain,
            fields=campos,
            limit=limite
        )
        
        logger.info(f"✅ Encontrados {len(dados)} registros no Odoo")
        
        return {
            'sucesso': True,
            'dados': dados,
            'total_registros': len(dados),
            'campos_usados': campos
        }
        
    except Exception as e:
        logger.error(f"❌ Erro ao buscar dados: {e}")
        return {
            'sucesso': False,
            'erro': str(e),
            'dados': [],
            'total_registros': 0
        }

def comparar_dados(dados_csv: List[List[str]], dados_odoo: List[Dict], 
                   campos_tecnicos: List[str]) -> Dict[str, Any]:
    """
    Compara dados do CSV com dados do Odoo para validar campos
    """
    logger.info("🔍 Comparando dados CSV vs Odoo...")
    
    resultados = {
        'campos_validados': [],
        'campos_problematicos': [],
        'amostras_comparacao': []
    }
    
    # Comparar primeiro registro como amostra
    if dados_csv and dados_odoo:
        registro_csv = dados_csv[0]
        registro_odoo = dados_odoo[0]
        
        logger.info("📊 Amostra de comparação:")
        logger.info(f"   • CSV: {len(registro_csv)} campos")
        logger.info(f"   • Odoo: {len(registro_odoo)} campos")
        
        # Comparar campo por campo
        for i, campo in enumerate(campos_tecnicos):
            if i < len(registro_csv):
                valor_csv = registro_csv[i]
                valor_odoo = registro_odoo.get(campo, 'CAMPO_NAO_ENCONTRADO')
                
                comparacao = {
                    'campo': campo,
                    'posicao': i,
                    'valor_csv': valor_csv,
                    'valor_odoo': valor_odoo,
                    'tipo_odoo': type(valor_odoo).__name__,
                    'compativel': valor_odoo != 'CAMPO_NAO_ENCONTRADO'
                }
                
                resultados['amostras_comparacao'].append(comparacao)
                
                if comparacao['compativel']:
                    resultados['campos_validados'].append(campo)
                else:
                    resultados['campos_problematicos'].append(campo)
                
                # Log detalhado para primeiros 10 campos
                if i < 10:
                    logger.info(f"   🔸 {campo}: CSV='{valor_csv}' | Odoo={valor_odoo} ({type(valor_odoo).__name__})")
    
    logger.info(f"✅ Validação concluída:")
    logger.info(f"   • Campos validados: {len(resultados['campos_validados'])}")
    logger.info(f"   • Campos problemáticos: {len(resultados['campos_problematicos'])}")
    
    return resultados

def salvar_resultados(resultados: Dict[str, Any], arquivo_saida: str = 'resultados_descoberta_odoo.json'):
    """
    Salva resultados em arquivo JSON
    """
    logger.info(f"💾 Salvando resultados em: {arquivo_saida}")
    
    try:
        # Converter datetime para string
        resultados_serializaveis = {
            'timestamp': datetime.now().isoformat(),
            'resultados': resultados
        }
        
        with open(arquivo_saida, 'w', encoding='utf-8') as f:
            json.dump(resultados_serializaveis, f, indent=2, ensure_ascii=False)
        
        logger.info("✅ Resultados salvos com sucesso")
        
    except Exception as e:
        logger.error(f"❌ Erro ao salvar resultados: {e}")

def main():
    """
    Função principal do script
    """
    logger.info("🚀 Iniciando descoberta de campos Odoo...")
    
    # Arquivo CSV com dados de exemplo
    arquivo_csv = 'projeto_carteira/Linha do pedido de venda (sale.order.line) (26).csv'
    
    try:
        # 1. Carregar campos do CSV
        dados_csv = carregar_campos_csv(arquivo_csv)
        
        # 2. Analisar estrutura dos campos
        analise_campos = analisar_campos_odoo(dados_csv['campos_tecnicos'])
        
        # 3. Testar conexão com Odoo
        if not testar_conexao_odoo():
            logger.error("❌ Sem conexão com Odoo. Abortando...")
            return
        
        # 4. Buscar dados no Odoo
        resultado_busca = buscar_dados_odoo(dados_csv['campos_tecnicos'], 80)
        
        # 5. Comparar dados
        if resultado_busca['sucesso']:
            comparacao = comparar_dados(
                dados_csv['dados_exemplo'],
                resultado_busca['dados'],
                dados_csv['campos_tecnicos']
            )
        else:
            comparacao = {'erro': resultado_busca['erro']}
        
        # 6. Compilar resultados finais
        resultados_finais = {
            'csv_info': {
                'total_campos': dados_csv['total_campos'],
                'total_registros_exemplo': dados_csv['total_registros_exemplo']
            },
            'analise_campos': analise_campos,
            'busca_odoo': resultado_busca,
            'comparacao': comparacao
        }
        
        # 7. Salvar resultados
        salvar_resultados(resultados_finais)
        
        # 8. Relatório final
        logger.info("\n" + "="*80)
        logger.info("📊 RELATÓRIO FINAL - DESCOBERTA DE CAMPOS ODOO")
        logger.info("="*80)
        logger.info(f"📂 Arquivo CSV: {arquivo_csv}")
        logger.info(f"📋 Total de campos: {dados_csv['total_campos']}")
        logger.info(f"📊 Registros de exemplo: {dados_csv['total_registros_exemplo']}")
        
        if resultado_busca['sucesso']:
            logger.info(f"✅ Registros encontrados no Odoo: {resultado_busca['total_registros']}")
            
            if 'campos_validados' in comparacao:
                logger.info(f"✅ Campos validados: {len(comparacao['campos_validados'])}")
                logger.info(f"⚠️ Campos problemáticos: {len(comparacao['campos_problematicos'])}")
                
                # Mostrar campos problemáticos
                if comparacao['campos_problematicos']:
                    logger.info("\n🔸 Campos problemáticos:")
                    for campo in comparacao['campos_problematicos'][:10]:  # Primeiros 10
                        logger.info(f"   • {campo}")
        else:
            logger.error(f"❌ Falha na busca: {resultado_busca['erro']}")
        
        logger.info("="*80)
        logger.info("🎯 Descoberta concluída! Verifique 'resultados_descoberta_odoo.json' para detalhes.")
        
    except Exception as e:
        logger.error(f"❌ Erro no processo principal: {e}")
        raise

if __name__ == "__main__":
    main()
