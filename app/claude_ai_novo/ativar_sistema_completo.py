#!/usr/bin/env python3
"""
🚀 ATIVADOR DO SISTEMA COMPLETO - Claude AI Novo
================================================

Este script ativa todas as capacidades reais do sistema:
- Dados reais do banco de dados
- Claude API real
- Todas as integrações
- Sistema de cache
- Monitoramento completo
"""

import os
import sys
import asyncio
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Adicionar o diretório raiz ao path
project_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(project_root))

class SistemaCompleto:
    """Ativador do sistema completo com todas as capacidades"""
    
    def __init__(self):
        self.config_applied = False
        self.components_activated = []
        self.errors = []
        
    def configurar_ambiente(self):
        """Configura todas as variáveis de ambiente necessárias"""
        logger.info("🔧 Configurando ambiente...")
        
        # 1. Ativar sistema novo
        os.environ['USE_NEW_CLAUDE_SYSTEM'] = 'true'
        logger.info("✅ Sistema novo ativado")
        
        # 2. Ativar dados reais
        os.environ['USE_REAL_DATA'] = 'true'
        logger.info("✅ Dados reais ativados")
        
        # 3. Ativar Claude real
        os.environ['USE_REAL_CLAUDE'] = 'true'
        
        # Verificar se API key está configurada
        if not os.getenv('ANTHROPIC_API_KEY'):
            logger.warning("⚠️ ANTHROPIC_API_KEY não configurada!")
            logger.info("💡 Configure com: export ANTHROPIC_API_KEY='sua-chave-aqui'")
        else:
            logger.info("✅ Claude API real ativada")
        
        # 4. Ativar cache Redis (se disponível)
        if os.getenv('REDIS_URL'):
            os.environ['USE_REDIS_CACHE'] = 'true'
            logger.info("✅ Cache Redis ativado")
        else:
            logger.info("💡 Redis não configurado - usando cache em memória")
        
        # 5. Configurar modo de produção
        os.environ['FLASK_ENV'] = 'production'
        os.environ['SYSTEM_MODE'] = 'production'
        logger.info("✅ Modo produção ativado")
        
        self.config_applied = True
    
    async def ativar_componentes(self):
        """Ativa todos os componentes do sistema"""
        logger.info("\n🚀 Ativando componentes do sistema...")
        
        try:
            # 1. Verificar banco de dados
            logger.info("\n📊 Verificando conexão com banco de dados...")
            from app import db
            from sqlalchemy import text
            
            with db.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                logger.info("✅ Banco de dados conectado")
                self.components_activated.append("database")
        except Exception as e:
            logger.error(f"❌ Erro no banco de dados: {e}")
            self.errors.append(f"Database: {e}")
        
        try:
            # 2. Verificar Claude API
            logger.info("\n🤖 Verificando Claude API...")
            from app.claude_ai_novo.integration.external_api_integration import ClaudeAPIClient
            
            if os.getenv('ANTHROPIC_API_KEY'):
                client = ClaudeAPIClient.from_environment()
                if client.validate_connection():
                    logger.info("✅ Claude API conectada e validada")
                    self.components_activated.append("claude_api")
                else:
                    logger.warning("⚠️ Claude API não validada")
            else:
                logger.warning("⚠️ ANTHROPIC_API_KEY não configurada")
                
        except Exception as e:
            logger.error(f"❌ Erro na Claude API: {e}")
            self.errors.append(f"Claude API: {e}")
        
        try:
            # 3. Ativar Integration Manager
            logger.info("\n🔗 Ativando Integration Manager...")
            from app.claude_ai_novo.integration.integration_manager import IntegrationManager
            
            integration = IntegrationManager()
            result = await integration.initialize_all_modules()
            
            if result.get('success'):
                logger.info(f"✅ Integration Manager ativo: {result['modules_active']}/{result['modules_loaded']} módulos")
                self.components_activated.append("integration_manager")
            else:
                logger.warning(f"⚠️ Integration Manager com problemas: {result}")
                
        except Exception as e:
            logger.error(f"❌ Erro no Integration Manager: {e}")
            self.errors.append(f"Integration Manager: {e}")
        
        try:
            # 4. Ativar Orchestrator Manager
            logger.info("\n🎭 Ativando Orchestrator Manager...")
            from app.claude_ai_novo.orchestrators.orchestrator_manager import get_orchestrator_manager
            
            orchestrator = get_orchestrator_manager()
            if orchestrator.health_check():
                logger.info("✅ Orchestrator Manager saudável")
                self.components_activated.append("orchestrator_manager")
            else:
                logger.warning("⚠️ Orchestrator Manager com problemas")
                
        except Exception as e:
            logger.error(f"❌ Erro no Orchestrator Manager: {e}")
            self.errors.append(f"Orchestrator Manager: {e}")
        
        try:
            # 5. Verificar dados reais
            logger.info("\n📈 Verificando acesso a dados reais...")
            from app.claude_ai_novo.utils.data_manager import DataManager
            
            data_manager = DataManager()
            await data_manager.initialize()
            
            # Testar carregamento de dados
            test_data = data_manager.provide_data('clientes')
            if 'error' not in test_data:
                logger.info("✅ Acesso a dados reais confirmado")
                self.components_activated.append("real_data")
            else:
                logger.warning(f"⚠️ Dados reais não acessíveis: {test_data}")
                
        except Exception as e:
            logger.error(f"❌ Erro nos dados reais: {e}")
            self.errors.append(f"Real Data: {e}")
    
    async def testar_sistema_completo(self):
        """Testa o sistema completo com uma query real"""
        logger.info("\n🧪 Testando sistema completo...")
        
        try:
            from app.claude_transition import get_transition_manager
            
            manager = get_transition_manager()
            
            # Queries de teste
            test_queries = [
                "Quantos pedidos temos hoje?",
                "Status das entregas do Atacadão",
                "Gerar relatório de fretes da semana"
            ]
            
            for query in test_queries:
                logger.info(f"\n📝 Testando: '{query}'")
                
                result = await manager.processar_consulta(query)
                
                if result and result != "{}" and len(str(result)) > 10:
                    logger.info(f"✅ Resposta válida: {str(result)[:100]}...")
                else:
                    logger.warning(f"⚠️ Resposta inválida: {result}")
                    
        except Exception as e:
            logger.error(f"❌ Erro no teste completo: {e}")
            self.errors.append(f"System Test: {e}")
    
    def gerar_relatorio(self):
        """Gera relatório final de ativação"""
        logger.info("\n" + "="*60)
        logger.info("📊 RELATÓRIO DE ATIVAÇÃO DO SISTEMA")
        logger.info("="*60)
        
        logger.info(f"\n✅ Componentes Ativados: {len(self.components_activated)}")
        for comp in self.components_activated:
            logger.info(f"   • {comp}")
        
        if self.errors:
            logger.info(f"\n❌ Erros Encontrados: {len(self.errors)}")
            for error in self.errors:
                logger.info(f"   • {error}")
        
        # Recomendações
        logger.info("\n💡 RECOMENDAÇÕES:")
        
        if 'claude_api' not in self.components_activated:
            logger.info("   1. Configure ANTHROPIC_API_KEY para ativar Claude real")
            
        if 'database' not in self.components_activated:
            logger.info("   2. Verifique DATABASE_URL para conectar ao banco real")
            
        if 'real_data' not in self.components_activated:
            logger.info("   3. Configure USE_REAL_DATA=true para usar dados reais")
        
        if not self.errors:
            logger.info("\n🎉 SISTEMA TOTALMENTE ATIVADO E FUNCIONAL!")
        else:
            logger.info("\n⚠️ Sistema parcialmente ativado - verifique os erros acima")
        
        logger.info("\n" + "="*60)

async def main():
    """Função principal"""
    ativador = SistemaCompleto()
    
    # 1. Configurar ambiente
    ativador.configurar_ambiente()
    
    # 2. Ativar componentes
    await ativador.ativar_componentes()
    
    # 3. Testar sistema
    await ativador.testar_sistema_completo()
    
    # 4. Gerar relatório
    ativador.gerar_relatorio()

if __name__ == "__main__":
    print("""
    🚀 ATIVADOR DO SISTEMA COMPLETO - Claude AI Novo
    ================================================
    
    Este script vai ativar todas as capacidades reais do sistema.
    
    IMPORTANTE: Certifique-se de ter configurado:
    - ANTHROPIC_API_KEY (para Claude real)
    - DATABASE_URL (para banco de dados real)
    - REDIS_URL (opcional, para cache)
    
    Pressione ENTER para continuar ou CTRL+C para cancelar...
    """)
    
    input()
    
    # Executar ativação
    asyncio.run(main()) 