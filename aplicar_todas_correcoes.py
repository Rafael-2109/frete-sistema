#!/usr/bin/env python3
"""
Script MASTER para aplicar todas as correções dos sistemas Claude AI
"""

import os
import sys
import logging
import subprocess
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('aplicar_correcoes.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

def executar_comando(comando, descricao):
    """Executa comando e retorna sucesso/falha"""
    
    logger.info(f"🔧 {descricao}...")
    
    try:
        result = subprocess.run(
            comando,
            shell=True,
            capture_output=True,
            text=True,
            encoding='utf-8'
        )
        
        if result.returncode == 0:
            logger.info(f"✅ {descricao} - SUCESSO")
            if result.stdout:
                logger.info(f"📝 Output: {result.stdout[:200]}...")
            return True
        else:
            logger.error(f"❌ {descricao} - FALHOU")
            if result.stderr:
                logger.error(f"📝 Erro: {result.stderr[:200]}...")
            return False
            
    except Exception as e:
        logger.error(f"❌ {descricao} - ERRO: {e}")
        return False

def main():
    """Função principal"""
    
    logger.info("🚀 INICIANDO CORREÇÃO COMPLETA DOS SISTEMAS CLAUDE AI")
    logger.info("="*80)
    
    inicio = datetime.now()
    
    # Lista de correções a aplicar
    correcoes = [
        {
            'nome': 'Criar arquivos e diretórios necessários',
            'comando': 'python criar_arquivos_necessarios.py',
            'critico': True
        },
        {
            'nome': 'Corrigir encoding UTF-8 PostgreSQL',
            'comando': 'python corrigir_encoding_postgresql.py',
            'critico': True
        },
        {
            'nome': 'Diagnosticar Multi-Agent System',
            'comando': 'python diagnostico_multi_agent.py',
            'critico': False
        },
        {
            'nome': 'Testar sistemas específicos',
            'comando': 'python teste_sistemas_especificos.py',
            'critico': False
        },
        {
            'nome': 'Testar Multi-Agent corrigido',
            'comando': 'python teste_multi_agent_corrigido.py',
            'critico': False
        }
    ]
    
    # Executar correções
    sucessos = 0
    falhas = 0
    
    for i, correcao in enumerate(correcoes, 1):
        logger.info(f"\n[{i}/{len(correcoes)}] {correcao['nome']}")
        logger.info("-" * 60)
        
        if executar_comando(correcao['comando'], correcao['nome']):
            sucessos += 1
        else:
            falhas += 1
            
            # Se é crítico e falhou, abortar
            if correcao['critico']:
                logger.error(f"❌ CORREÇÃO CRÍTICA FALHOU: {correcao['nome']}")
                logger.error("⚠️ Abortando processo...")
                break
    
    # Relatório final
    duracao = datetime.now() - inicio
    
    logger.info("\n" + "="*80)
    logger.info("📊 RELATÓRIO FINAL DE CORREÇÕES")
    logger.info("="*80)
    
    logger.info(f"⏱️ Duração: {duracao.total_seconds():.1f} segundos")
    logger.info(f"✅ Sucessos: {sucessos}")
    logger.info(f"❌ Falhas: {falhas}")
    logger.info(f"📈 Taxa de sucesso: {sucessos/(sucessos+falhas)*100:.1f}%")
    
    if falhas == 0:
        logger.info("🎉 TODAS AS CORREÇÕES APLICADAS COM SUCESSO!")
        logger.info("🔥 Sistemas Claude AI devem estar funcionando agora")
        
        # Próximos passos
        logger.info("\n🎯 PRÓXIMOS PASSOS:")
        logger.info("1. Reiniciar o sistema Flask")
        logger.info("2. Executar teste final: python teste_claude_ai_final_funcional.py")
        logger.info("3. Verificar logs em: aplicar_correcoes.log")
        
    else:
        logger.warning(f"⚠️ {falhas} correções falharam")
        logger.info("📋 Verifique o log para detalhes específicos")
    
    logger.info(f"📄 Log completo salvo em: aplicar_correcoes.log")

if __name__ == "__main__":
    main() 