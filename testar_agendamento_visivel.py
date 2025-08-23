#!/usr/bin/env python3
"""
Script temporário para testar agendamento com navegador VISÍVEL
Permite visualizar o que o Playwright está fazendo
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.portal.atacadao.playwright_client import PlaywrightClient
import logging
from datetime import datetime, timedelta

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

def testar_com_navegador_visivel():
    """Executa teste de agendamento com navegador visível"""
    
    # IMPORTANTE: headless=False para ver o navegador
    logger.info("Iniciando teste com navegador VISÍVEL...")
    client = PlaywrightClient(headless=False)  # ← NAVEGADOR VISÍVEL!
    
    try:
        # Dados de teste
        pedido_cliente = "932955"  # Pedido de teste
        data_agendamento = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
        
        dados = {
            'pedido_cliente': pedido_cliente,
            'data_agendamento': data_agendamento,
            'data_agendamento_iso': data_agendamento,
            'peso_total': 10.25,
            'produtos': {
                '70848': 5  # Produto com quantidade
            }
        }
        
        logger.info(f"""
========================================
TESTE DE AGENDAMENTO - NAVEGADOR VISÍVEL
========================================
Pedido: {pedido_cliente}
Data: {data_agendamento}
Peso: {dados['peso_total']} kg

VOCÊ PODERÁ VER O NAVEGADOR FUNCIONANDO!
========================================
        """)
        
        # Fazer login se necessário
        if not client.verificar_login():
            logger.error("Sessão expirada. Execute primeiro: python configurar_sessao_atacadao.py")
            return
        
        logger.info("✅ Login verificado")
        
        # Executar agendamento
        logger.info("Iniciando processo de agendamento...")
        resultado = client.criar_agendamento(dados)
        
        # Mostrar resultado
        logger.info("\n" + "="*50)
        if resultado['success']:
            logger.info(f"✅✅✅ SUCESSO!")
            logger.info(f"Protocolo: {resultado.get('protocolo', 'N/A')}")
            logger.info(f"Mensagem: {resultado['message']}")
        else:
            logger.error(f"❌ FALHA!")
            logger.error(f"Mensagem: {resultado['message']}")
            if 'debug_info' in resultado:
                logger.error(f"Debug: {resultado['debug_info']}")
        
        logger.info("="*50)
        
        # Manter navegador aberto por 10 segundos para visualização
        if not resultado['success']:
            logger.info("\n⏸️ Mantendo navegador aberto por 30 segundos para análise...")
            logger.info("Você pode inspecionar o estado da página...")
            import time
            time.sleep(30)
        
    except Exception as e:
        logger.error(f"Erro durante teste: {e}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("Fechando navegador...")
        client.fechar()

if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║                TESTE COM NAVEGADOR VISÍVEL                 ║
║                                                            ║
║  Este teste abrirá o Chrome/Chromium para você visualizar ║
║  exatamente o que o sistema está fazendo.                 ║
║                                                            ║
║  Você verá:                                                ║
║  1. Busca do pedido                                       ║
║  2. Preenchimento do formulário                           ║
║  3. Tentativas de clicar no botão Salvar                  ║
║  4. Se o agendamento é criado ou não                      ║
║                                                            ║
║  Pressione ENTER para iniciar...                          ║
╚════════════════════════════════════════════════════════════╝
    """)
    input()
    
    testar_com_navegador_visivel()
    
    print("\n✅ Teste concluído!")