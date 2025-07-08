#!/usr/bin/env python3
"""
🧪 TESTE SISTEMA SEM WARNINGS

Script para validar que o SmartBaseAgentRealista elimina todos os warnings
e mantém funcionalidade plena.
"""

import sys
import os
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Configurar logging para capturar warnings
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)8s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

class ContadorWarnings:
    """Conta warnings no sistema"""
    
    def __init__(self):
        self.warnings_count = 0
        self.warnings_list = []
        self.original_warning = logging.getLogger().warning
        
        # Interceptar warnings
        def custom_warning(message, *args, **kwargs):
            if "⚠️" in str(message) or "WARNING" in str(message):
                self.warnings_count += 1
                self.warnings_list.append(str(message))
            return self.original_warning(message, *args, **kwargs)
        
        # Aplicar interceptor a todos os loggers
        for name in logging.Logger.manager.loggerDict:
            logging.getLogger(name).warning = custom_warning
    
    def get_results(self):
        """Retorna resultado da contagem"""
        return {
            'total_warnings': self.warnings_count,
            'warnings_list': self.warnings_list
        }


async def testar_agente_realista():
    """Testa o agente realista sem warnings"""
    logger.info("🧪 INICIANDO TESTE - SmartBaseAgentRealista")
    
    # Inicializar contador de warnings
    contador = ContadorWarnings()
    
    try:
        # Importar e testar agente entregas
        from app.claude_ai_novo.multi_agent.agents.entregas_agent import EntregasAgent
        
        logger.info("📦 Criando EntregasAgent...")
        agente = EntregasAgent()
        
        logger.info("🔍 Testando capacidades do agente...")
        status = agente.get_agent_status()
        
        logger.info("📊 STATUS DO AGENTE REALISTA:")
        logger.info(f"   • Tipo: {status['agent_type']}")
        logger.info(f"   • Capacidades ativas: {len(status['capacidades_ativas'])}")
        logger.info(f"   • Performance class: {status['performance_class']}")
        logger.info(f"   • Warnings eliminados: {len(status['warnings_eliminados'])}")
        
        logger.info("📋 CAPACIDADES ATIVAS:")
        for cap in status['capacidades_ativas']:
            logger.info(f"   ✅ {cap}")
        
        logger.info("🚫 WARNINGS ELIMINADOS:")
        for warning in status['warnings_eliminados']:
            logger.info(f"   🚫 {warning}")
        
        # Testar análise básica
        logger.info("🔍 Testando análise de consulta...")
        
        test_query = "Como estão as entregas do Atacadão hoje?"
        test_context = {
            'username': 'Teste Sistema',
            'user_id': 'test_123',
            'timestamp': datetime.now().isoformat()
        }
        
        resultado = await agente.analyze(test_query, test_context)
        
        logger.info("📊 RESULTADO DA ANÁLISE:")
        logger.info(f"   • Relevância: {resultado.get('relevance', 0):.2f}")
        logger.info(f"   • Confiança: {resultado.get('confidence', 0):.2f}")
        logger.info(f"   • Agente: {resultado.get('agent_type', 'N/A')}")
        logger.info(f"   • Dados reais: {resultado.get('dados_reais', False)}")
        
        # Verificar capacidades especializadas
        caps_especializadas = agente.get_specialized_capabilities()
        logger.info(f"🎯 CAPACIDADES ESPECIALIZADAS: {len(caps_especializadas)}")
        for cap in caps_especializadas:
            logger.info(f"   🎯 {cap}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ ERRO NO TESTE: {e}")
        return False
    
    finally:
        # Verificar warnings gerados
        results = contador.get_results()
        
        logger.info("📊 RESULTADO FINAL DOS WARNINGS:")
        logger.info(f"   • Total warnings: {results['total_warnings']}")
        
        if results['total_warnings'] == 0:
            logger.info("   ✅ SUCESSO: Zero warnings detectados!")
        else:
            logger.warning(f"   ⚠️ ATENÇÃO: {results['total_warnings']} warnings detectados:")
            for warning in results['warnings_list']:
                logger.warning(f"      - {warning}")
        
        return results['total_warnings'] == 0


async def testar_sistema_multi_agente():
    """Testa sistema multi-agente completo"""
    logger.info("🤖 TESTANDO SISTEMA MULTI-AGENTE...")
    
    try:
        from app.claude_ai_novo.multi_agent.multi_agent_orchestrator import MultiAgentOrchestrator
        from app.claude_ai_novo.multi_agent.agents.entregas_agent import get_entregas_agent
        from app.claude_ai_novo.multi_agent.agents.fretes_agent import get_fretes_agent
        
        # Criar agentes
        agentes = {
            'entregas': get_entregas_agent(),
            'fretes': get_fretes_agent()
        }
        
        logger.info(f"✅ Criados {len(agentes)} agentes especializados")
        
        # Testar capacidades de cada agente
        for nome, agente in agentes.items():
            status = agente.get_agent_status()
            logger.info(f"📊 Agente {nome}:")
            logger.info(f"   • Capacidades: {len(status['capacidades_ativas'])}")
            logger.info(f"   • Performance: {status['performance_class']}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ ERRO NO TESTE MULTI-AGENTE: {e}")
        return False


async def testar_compatibilidade():
    """Testa compatibilidade com sistema existente"""
    logger.info("🔗 TESTANDO COMPATIBILIDADE COM SISTEMA EXISTENTE...")
    
    try:
        # Testar se os imports ainda funcionam
        from app.claude_ai_novo.multi_agent.specialist_agents import get_specialist_agents
        
        agentes = get_specialist_agents()
        logger.info(f"✅ Sistema de agentes especialistas: {len(agentes)} agentes")
        
        # Testar cada agente
        for agent_type, agente in agentes.items():
            if hasattr(agente, 'get_agent_status'):
                status = agente.get_agent_status()
                logger.info(f"📊 {agent_type}: {status.get('performance_class', 'N/A')}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ ERRO DE COMPATIBILIDADE: {e}")
        return False


async def benchmark_performance():
    """Benchmark de performance sem warnings"""
    logger.info("⚡ BENCHMARK DE PERFORMANCE...")
    
    try:
        from app.claude_ai_novo.multi_agent.agents.entregas_agent import EntregasAgent
        
        agente = EntregasAgent()
        
        # Testar múltiplas consultas
        consultas_teste = [
            "Entregas do Assai hoje",
            "Status entregas atrasadas", 
            "Performance transportadoras",
            "Agendamentos pendentes",
            "Entregas finalizadas ontem"
        ]
        
        tempos = []
        
        for consulta in consultas_teste:
            start_time = datetime.now()
            
            resultado = await agente.analyze(consulta, {'user_id': 'benchmark'})
            
            end_time = datetime.now()
            tempo = (end_time - start_time).total_seconds()
            tempos.append(tempo)
            
            logger.info(f"⚡ '{consulta[:20]}...': {tempo:.3f}s")
        
        tempo_medio = sum(tempos) / len(tempos) if tempos else 0
        logger.info(f"📊 PERFORMANCE MÉDIA: {tempo_medio:.3f}s por consulta")
        
        return tempo_medio < 1.0  # Esperamos < 1 segundo por consulta
        
    except Exception as e:
        logger.error(f"❌ ERRO NO BENCHMARK: {e}")
        return False


async def main():
    """Função principal de teste"""
    logger.info("🚀 INICIANDO TESTE COMPLETO DO SISTEMA SEM WARNINGS")
    logger.info("=" * 80)
    
    resultados = {}
    
    # Teste 1: Agente Realista
    logger.info("\n📋 TESTE 1: SmartBaseAgentRealista")
    resultados['agente_realista'] = await testar_agente_realista()
    
    # Teste 2: Sistema Multi-Agente
    logger.info("\n📋 TESTE 2: Sistema Multi-Agente")
    resultados['multi_agente'] = await testar_sistema_multi_agente()
    
    # Teste 3: Compatibilidade
    logger.info("\n📋 TESTE 3: Compatibilidade")
    resultados['compatibilidade'] = await testar_compatibilidade()
    
    # Teste 4: Performance
    logger.info("\n📋 TESTE 4: Performance")
    resultados['performance'] = await benchmark_performance()
    
    # Resultado final
    logger.info("\n" + "=" * 80)
    logger.info("📊 RESULTADO FINAL DOS TESTES:")
    
    sucessos = sum(1 for sucesso in resultados.values() if sucesso)
    total = len(resultados)
    
    for teste, sucesso in resultados.items():
        status = "✅ PASSOU" if sucesso else "❌ FALHOU"
        logger.info(f"   {teste}: {status}")
    
    logger.info(f"\n🎯 TAXA DE SUCESSO: {sucessos}/{total} ({(sucessos/total)*100:.1f}%)")
    
    if sucessos == total:
        logger.info("🎉 TODOS OS TESTES PASSARAM! Sistema sem warnings operacional.")
        return True
    else:
        logger.error("⚠️ ALGUNS TESTES FALHARAM. Revisar implementação.")
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("❌ Teste interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Erro fatal no teste: {e}")
        sys.exit(1) 