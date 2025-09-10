#!/usr/bin/env python3
"""
Script de teste para validar as correções do upload Sendas
Implementa as 4 correções sugeridas pelo GPT5:
1. Sempre usar iframe para modal de upload
2. Verificador de erro ciente do iframe
3. Não fechar modal de upload
4. Aguardar sinal claro no iframe
"""

import asyncio
import sys
import os
import logging
from datetime import datetime

# Adicionar o caminho do projeto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from app.portal.sendas.consumir_agendas import ConsumirAgendasSendas

# Configurar logging detalhado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'/tmp/sendas_test_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """
    Testa o upload corrigido
    """
    # Arquivo de teste
    arquivo_teste = f'/tmp/sendas_multi_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    # Verificar se existe arquivo de teste recente
    import glob
    arquivos_recentes = sorted(glob.glob('/tmp/sendas_multi_*.xlsx'))
    if arquivos_recentes:
        arquivo_teste = arquivos_recentes[-1]
        logger.info(f"📁 Usando arquivo existente: {arquivo_teste}")
    else:
        logger.error("❌ Nenhum arquivo de teste encontrado em /tmp/sendas_multi_*.xlsx")
        logger.info("💡 Por favor, baixe uma planilha primeiro ou crie um arquivo de teste")
        return False
    
    logger.info("=" * 60)
    logger.info("TESTE DE UPLOAD CORRIGIDO - PORTAL SENDAS")
    logger.info("=" * 60)
    logger.info("Correções implementadas:")
    logger.info("✅ 1. Sempre usar iframe para modal de upload")
    logger.info("✅ 2. Verificador de erro ciente do iframe")
    logger.info("✅ 3. Não fechar modal de upload")
    logger.info("✅ 4. Aguardar sinal claro no iframe")
    logger.info("✅ 5. Removidos page.evaluate desnecessários")
    logger.info("=" * 60)
    
    try:
        # Criar instância do consumidor
        logger.info("🚀 Iniciando ConsumirAgendasSendas...")
        consumidor = ConsumirAgendasSendas()
        
        # Executar upload
        logger.info("🌐 Iniciando navegador...")
        await consumidor.portal.iniciar_navegador()
        
        logger.info("🔐 Fazendo login...")
        if not await consumidor.portal.fazer_login():
            logger.error("❌ Falha no login")
            return False
        
        logger.info("✅ Login bem-sucedido")
        
        logger.info("📋 Navegando para gestão de pedidos...")
        if not await consumidor.navegar_para_gestao_pedidos():
            logger.error("❌ Falha ao navegar")
            return False
        
        logger.info("✅ Navegação bem-sucedida")
        
        logger.info("📤 Iniciando upload da planilha...")
        resultado = await consumidor.fazer_upload_planilha(arquivo_teste)
        
        if resultado:
            logger.info("=" * 60)
            logger.info("✅ UPLOAD BEM-SUCEDIDO!")
            logger.info("=" * 60)
            logger.info("🎉 As correções funcionaram!")
            logger.info("✅ Modal foi encontrado no iframe")
            logger.info("✅ Input foi encontrado no modal")
            logger.info("✅ Botão foi encontrado no modal")
            logger.info("✅ Arquivo foi enviado corretamente")
            logger.info("✅ Servidor processou sem erro 500")
            logger.info("=" * 60)
            
            # Capturar screenshot de sucesso
            screenshot_path = f"/tmp/sendas_sucesso_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await consumidor.portal.page.screenshot(path=screenshot_path)
            logger.info(f"📸 Screenshot de sucesso: {screenshot_path}")
            
        else:
            logger.error("=" * 60)
            logger.error("❌ UPLOAD FALHOU")
            logger.error("=" * 60)
            logger.error("Verifique o log detalhado acima para identificar o problema")
            
            # Capturar screenshot de erro
            screenshot_path = f"/tmp/sendas_erro_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            await consumidor.portal.page.screenshot(path=screenshot_path)
            logger.error(f"📸 Screenshot de erro: {screenshot_path}")
        
        # Fechar navegador
        await consumidor.portal.fechar()
        logger.info("🔒 Navegador fechado")
        
        return resultado
        
    except Exception as e:
        logger.error(f"❌ Erro durante teste: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    # Executar teste
    sucesso = asyncio.run(main())
    
    if sucesso:
        logger.info("\n✅ TESTE CONCLUÍDO COM SUCESSO!")
        sys.exit(0)
    else:
        logger.error("\n❌ TESTE FALHOU")
        sys.exit(1)