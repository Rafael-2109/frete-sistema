#!/usr/bin/env python3
"""
🚀 TESTE DE INTEGRAÇÃO - AUTO COMMAND PROCESSOR NO CHAT PRINCIPAL
Testa se os comandos automáticos funcionam no chat Claude AI
"""

import os
import sys
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('teste_integracao_autonomia.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)

# Adicionar path do projeto
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def teste_comandos_chat():
    """Testa comandos automáticos via chat principal"""
    
    logger.info("🚀 INICIANDO TESTE DE INTEGRAÇÃO - AUTONOMIA NO CHAT")
    
    try:
        # Configurar ambiente local para teste
        os.environ['DATABASE_URL'] = 'sqlite:///instance/sistema_fretes.db'
        os.environ['FLASK_ENV'] = 'development'
        
        # Criar app Flask
        from app import create_app
        app = create_app()
        
        sucessos = 0
        total_testes = 0
        
        with app.app_context():
            logger.info("✅ Contexto Flask criado com sucesso")
            
            # Importar sistema principal
            from app.claude_ai.claude_real_integration import processar_com_claude_real
            
            # Contexto de usuário para teste
            user_context = {
                'user_id': 999,
                'username': 'teste_autonomia',
                'perfil': 'admin',
                'vendedor_codigo': None
            }
            
            # TESTE 1: Comando de descobrir projeto
            total_testes += 1
            logger.info(f"[{total_testes}/6] Testando: Comando 'descobrir projeto'...")
            
            try:
                resposta = processar_com_claude_real("descobrir projeto", user_context)
                
                if ("CLAUDE AI - AUTONOMIA TOTAL" in resposta and 
                    "descobrir_projeto" in resposta and
                    "Auto Command Processor" in resposta):
                    logger.info("   ✅ PASSOU: Comando descobrir projeto executado automaticamente!")
                    sucessos += 1
                else:
                    logger.warning("   ❌ FALHOU: Comando não foi detectado como automático")
                    logger.debug(f"   Resposta recebida: {resposta[:200]}...")
                    
            except Exception as e:
                logger.error(f"   ❌ ERRO: {e}")
            
            # TESTE 2: Comando de ler arquivo
            total_testes += 1
            logger.info(f"[{total_testes}/6] Testando: Comando 'ler arquivo'...")
            
            try:
                resposta = processar_com_claude_real("lê o arquivo carteira/models.py", user_context)
                
                if ("CLAUDE AI - AUTONOMIA TOTAL" in resposta and 
                    "ler_arquivo" in resposta):
                    logger.info("   ✅ PASSOU: Comando ler arquivo detectado!")
                    sucessos += 1
                else:
                    logger.warning("   ❌ FALHOU: Comando não foi detectado")
                    
            except Exception as e:
                logger.error(f"   ❌ ERRO: {e}")
            
            # TESTE 3: Comando de criar módulo
            total_testes += 1
            logger.info(f"[{total_testes}/6] Testando: Comando 'criar módulo'...")
            
            try:
                resposta = processar_com_claude_real("cria um módulo teste com campos nome, ativo", user_context)
                
                if ("CLAUDE AI - AUTONOMIA TOTAL" in resposta and 
                    "criar_modulo" in resposta):
                    logger.info("   ✅ PASSOU: Comando criar módulo detectado!")
                    sucessos += 1
                else:
                    logger.warning("   ❌ FALHOU: Comando não foi detectado")
                    
            except Exception as e:
                logger.error(f"   ❌ ERRO: {e}")
            
            # TESTE 4: Comando de inspecionar banco  
            total_testes += 1
            logger.info(f"[{total_testes}/6] Testando: Comando 'inspecionar banco'...")
            
            try:
                resposta = processar_com_claude_real("inspeciona o banco", user_context)
                
                if ("CLAUDE AI - AUTONOMIA TOTAL" in resposta and 
                    "inspecionar_banco" in resposta):
                    logger.info("   ✅ PASSOU: Comando inspecionar banco detectado!")
                    sucessos += 1
                else:
                    logger.warning("   ❌ FALHOU: Comando não foi detectado")
                    
            except Exception as e:
                logger.error(f"   ❌ ERRO: {e}")
            
            # TESTE 5: Comando de listar diretório
            total_testes += 1
            logger.info(f"[{total_testes}/6] Testando: Comando 'listar diretório'...")
            
            try:
                resposta = processar_com_claude_real("lista o diretório embarques", user_context)
                
                if ("CLAUDE AI - AUTONOMIA TOTAL" in resposta and 
                    "listar_diretorio" in resposta):
                    logger.info("   ✅ PASSOU: Comando listar diretório detectado!")
                    sucessos += 1
                else:
                    logger.warning("   ❌ FALHOU: Comando não foi detectado")
                    
            except Exception as e:
                logger.error(f"   ❌ ERRO: {e}")
            
            # TESTE 6: Consulta normal (não deve ser comando)
            total_testes += 1
            logger.info(f"[{total_testes}/6] Testando: Consulta normal...")
            
            try:
                resposta = processar_com_claude_real("quantas entregas do Assai", user_context)
                
                if ("CLAUDE AI - AUTONOMIA TOTAL" not in resposta):
                    logger.info("   ✅ PASSOU: Consulta normal não foi tratada como comando")
                    sucessos += 1
                else:
                    logger.warning("   ❌ FALHOU: Consulta normal foi tratada como comando automático")
                    
            except Exception as e:
                logger.error(f"   ❌ ERRO: {e}")
        
        # Resultado final
        percentual = (sucessos / total_testes * 100) if total_testes > 0 else 0
        
        logger.info("=" * 60)
        logger.info("   RESULTADO FINAL DA INTEGRAÇÃO")
        logger.info("=" * 60)
        logger.info(f"📊 RESULTADOS:")
        logger.info(f"   ✅ Sucessos: {sucessos}/{total_testes} ({percentual:.1f}%)")
        
        if percentual >= 80:
            logger.info("🎉 INTEGRAÇÃO FUNCIONANDO PERFEITAMENTE!")
            logger.info("   Claude AI agora tem AUTONOMIA TOTAL no chat!")
        elif percentual >= 60:
            logger.info("⚠️ INTEGRAÇÃO PARCIALMENTE FUNCIONAL")
            logger.info("   Algumas funcionalidades precisam de ajuste")
        else:
            logger.info("❌ INTEGRAÇÃO COM PROBLEMAS")
            logger.info("   Necessário verificar implementação")
        
        logger.info("📋 LOG DETALHADO: teste_integracao_autonomia.log")
        logger.info("=" * 60)
        
        return sucessos == total_testes
        
    except Exception as e:
        logger.error(f"❌ ERRO CRÍTICO no teste: {e}", exc_info=True)
        return False

if __name__ == '__main__':
    print("🚀 TESTE DE INTEGRAÇÃO - AUTONOMIA DO CLAUDE AI")
    print("=" * 60)
    
    sucesso = teste_comandos_chat()
    
    if sucesso:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("Claude AI agora tem autonomia total no chat!")
    else:
        print("\n⚠️ Alguns testes falharam")
        print("Verifique os logs para mais detalhes")
    
    print("=" * 60) 