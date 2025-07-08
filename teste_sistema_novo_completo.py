#!/usr/bin/env python3
"""
🧪 TESTE SISTEMA NOVO COMPLETO - Validação de Integração
Verifica se o claude_ai_novo está realmente funcionando e integrado
"""

import os
import sys
import asyncio
import traceback
from datetime import datetime

# Adicionar path do projeto
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

class TesteSistemaNovoCompleto:
    """Testa todas as funcionalidades do sistema novo"""
    
    def __init__(self):
        self.resultados = {
            'testes_executados': 0,
            'testes_passou': 0,
            'testes_falhou': 0,
            'detalhes': []
        }
    
    async def executar_todos_testes(self):
        """Executa todos os testes de integração"""
        print("🧪 INICIANDO TESTES COMPLETOS DO SISTEMA NOVO")
        print("=" * 60)
        
        # Lista de testes
        testes = [
            ("🔧 Imports Básicos", self.teste_imports_basicos),
            ("🏗️ ClaudeAINovo", self.teste_claude_ai_novo),
            ("🔗 IntegrationManager", self.teste_integration_manager),
            ("🤖 Multi-Agent System", self.teste_multi_agent_system),
            ("🧠 Intelligence System", self.teste_intelligence_system),
            ("🔍 Semantic System", self.teste_semantic_system),
            ("📊 Database Readers", self.teste_database_readers),
            ("🎯 Suggestion Engine", self.teste_suggestion_engine),
            ("🔄 Sistema de Transição", self.teste_sistema_transicao),
            ("⚙️ Advanced Integration", self.teste_advanced_integration)
        ]
        
        # Executar testes
        for nome, funcao_teste in testes:
            print(f"\n{nome}...")
            try:
                resultado = await funcao_teste()
                self._registrar_resultado(nome, True, resultado)
                print(f"✅ {nome} - PASSOU")
            except Exception as e:
                self._registrar_resultado(nome, False, str(e))
                print(f"❌ {nome} - FALHOU: {e}")
        
        # Relatório final
        self._imprimir_relatorio_final()
    
    def _registrar_resultado(self, nome: str, passou: bool, detalhes: str):
        """Registra resultado do teste"""
        self.resultados['testes_executados'] += 1
        if passou:
            self.resultados['testes_passou'] += 1
        else:
            self.resultados['testes_falhou'] += 1
        
        self.resultados['detalhes'].append({
            'nome': nome,
            'passou': passou,
            'detalhes': detalhes,
            'timestamp': datetime.now().isoformat()
        })
    
    async def teste_imports_basicos(self) -> str:
        """Testa se consegue importar módulos básicos"""
        try:
            # Import principal
            from app.claude_ai_novo import ClaudeAINovo, create_claude_ai_novo
            
            # Import do integration manager
            from app.claude_ai_novo.integration_manager import IntegrationManager
            
            # Import de alguns módulos específicos
            from app.claude_ai_novo.multi_agent.system import MultiAgentSystem
            from app.claude_ai_novo.intelligence.intelligence_manager import IntelligenceManager
            
            return "Todos os imports básicos funcionaram"
            
        except ImportError as e:
            raise Exception(f"Erro de import: {e}")
    
    async def teste_claude_ai_novo(self) -> str:
        """Testa se ClaudeAINovo pode ser instanciado"""
        try:
            from app.claude_ai_novo import ClaudeAINovo
            
            # Tentar instanciar
            claude_ai = ClaudeAINovo()
            
            # Verificar atributos básicos
            assert hasattr(claude_ai, 'integration_manager')
            assert hasattr(claude_ai, 'system_ready')
            assert hasattr(claude_ai, 'initialization_result')
            
            # Verificar métodos principais
            assert hasattr(claude_ai, 'initialize_system')
            assert hasattr(claude_ai, 'process_query')
            assert hasattr(claude_ai, 'get_system_status')
            
            return "ClaudeAINovo instanciado com sucesso"
            
        except Exception as e:
            raise Exception(f"Erro ao instanciar ClaudeAINovo: {e}")
    
    async def teste_integration_manager(self) -> str:
        """Testa IntegrationManager"""
        try:
            from app.claude_ai_novo.integration_manager import IntegrationManager
            
            # Instanciar
            manager = IntegrationManager()
            
            # Verificar métodos principais
            assert hasattr(manager, 'initialize_all_modules')
            assert hasattr(manager, 'process_unified_query')
            assert hasattr(manager, 'get_system_status')
            assert hasattr(manager, 'get_module')
            
            # Verificar estruturas internas
            assert hasattr(manager, 'modules')
            assert hasattr(manager, 'module_status')
            assert hasattr(manager, 'system_metrics')
            
            return "IntegrationManager funcional"
            
        except Exception as e:
            raise Exception(f"Erro no IntegrationManager: {e}")
    
    async def teste_multi_agent_system(self) -> str:
        """Testa sistema multi-agente"""
        try:
            # Imports do sistema multi-agente
            from app.claude_ai_novo.multi_agent.system import MultiAgentSystem
            from app.claude_ai_novo.multi_agent.multi_agent_orchestrator import MultiAgentOrchestrator
            from app.claude_ai_novo.multi_agent.agents.base_agent import BaseSpecialistAgent
            
            # Verificar agentes específicos
            from app.claude_ai_novo.multi_agent.agents.entregas_agent import EntregasAgent
            from app.claude_ai_novo.multi_agent.agents.fretes_agent import FretesAgent
            from app.claude_ai_novo.multi_agent.agents.pedidos_agent import PedidosAgent
            
            return "Sistema Multi-Agent importado com sucesso"
            
        except Exception as e:
            raise Exception(f"Erro no Multi-Agent System: {e}")
    
    async def teste_intelligence_system(self) -> str:
        """Testa sistema de inteligência"""
        try:
            # Intelligence core
            from app.claude_ai_novo.intelligence.intelligence_manager import IntelligenceManager
            from app.claude_ai_novo.intelligence.learning.learning_core import LearningCore
            from app.claude_ai_novo.intelligence.learning.pattern_learner import PatternLearner
            from app.claude_ai_novo.intelligence.learning.feedback_processor import FeedbackProcessor
            
            # Conversation
            from app.claude_ai_novo.intelligence.conversation.conversation_context import ConversationContext
            
            return "Sistema de Intelligence importado com sucesso"
            
        except Exception as e:
            raise Exception(f"Erro no Intelligence System: {e}")
    
    async def teste_semantic_system(self) -> str:
        """Testa sistema semântico"""
        try:
            # Semantic core
            from app.claude_ai_novo.semantic.semantic_manager import SemanticManager
            from app.claude_ai_novo.semantic.semantic_enricher import SemanticEnricher
            from app.claude_ai_novo.semantic.semantic_orchestrator import SemanticOrchestrator
            
            # Readers
            from app.claude_ai_novo.semantic.readers.database_reader import DatabaseReader
            
            # Mappers
            from app.claude_ai_novo.semantic.mappers.base_mapper import BaseMapper
            from app.claude_ai_novo.semantic.mappers.faturamento_mapper import FaturamentoMapper
            
            return "Sistema Semantic importado com sucesso"
            
        except Exception as e:
            raise Exception(f"Erro no Semantic System: {e}")
    
    async def teste_database_readers(self) -> str:
        """Testa database readers"""
        try:
            # Database readers específicos
            from app.claude_ai_novo.semantic.readers.database.database_connection import DatabaseConnection
            from app.claude_ai_novo.semantic.readers.database.metadata_reader import MetadataReader
            from app.claude_ai_novo.semantic.readers.database.data_analyzer import DataAnalyzer
            from app.claude_ai_novo.semantic.readers.database.field_searcher import FieldSearcher
            from app.claude_ai_novo.semantic.readers.database.auto_mapper import AutoMapper
            
            return "Database Readers importados com sucesso"
            
        except Exception as e:
            raise Exception(f"Erro nos Database Readers: {e}")
    
    async def teste_suggestion_engine(self) -> str:
        """Testa motor de sugestões"""
        try:
            from app.claude_ai_novo.suggestions.engine import SuggestionEngine
            
            # Tentar instanciar
            engine = SuggestionEngine()
            
            # Verificar métodos básicos
            assert hasattr(engine, 'generate_suggestions')
            
            return "Suggestion Engine funcional"
            
        except Exception as e:
            raise Exception(f"Erro no Suggestion Engine: {e}")
    
    async def teste_sistema_transicao(self) -> str:
        """Testa sistema de transição"""
        try:
            from app.claude_transition import ClaudeTransition, get_claude_transition, processar_consulta_transicao
            
            # Tentar usar função de transição
            resultado = processar_consulta_transicao("teste", {"user_id": "test"})
            
            return f"Sistema de transição funcional - Resposta: {resultado[:100]}..."
            
        except Exception as e:
            raise Exception(f"Erro no sistema de transição: {e}")
    
    async def teste_advanced_integration(self) -> str:
        """Testa Advanced Integration"""
        try:
            from app.claude_ai_novo.integration.advanced.advanced_integration import AdvancedAIIntegration, get_advanced_ai_integration
            
            # Tentar obter instância
            advanced_ai = get_advanced_ai_integration()
            
            if advanced_ai:
                assert hasattr(advanced_ai, 'process_advanced_query')
                return "Advanced Integration disponível e funcional"
            else:
                return "Advanced Integration configurado mas não inicializado"
            
        except Exception as e:
            raise Exception(f"Erro no Advanced Integration: {e}")
    
    def _imprimir_relatorio_final(self):
        """Imprime relatório final dos testes"""
        print("\n" + "="*80)
        print("🧪 RELATÓRIO FINAL DOS TESTES")
        print("="*80)
        
        total = self.resultados['testes_executados']
        passou = self.resultados['testes_passou']
        falhou = self.resultados['testes_falhou']
        taxa_sucesso = (passou / total * 100) if total > 0 else 0
        
        print(f"\n📊 RESUMO:")
        print(f"   ✅ Testes que passaram: {passou}")
        print(f"   ❌ Testes que falharam: {falhou}")
        print(f"   📊 Taxa de sucesso: {taxa_sucesso:.1f}%")
        
        print(f"\n📋 DETALHES:")
        for resultado in self.resultados['detalhes']:
            status = "✅" if resultado['passou'] else "❌"
            print(f"   {status} {resultado['nome']}")
            if not resultado['passou']:
                print(f"      🔍 Erro: {resultado['detalhes']}")
        
        # Conclusão
        print(f"\n🎯 CONCLUSÃO:")
        if taxa_sucesso >= 90:
            print("   🎉 SISTEMA NOVO COMPLETAMENTE FUNCIONAL!")
        elif taxa_sucesso >= 70:
            print("   ✅ SISTEMA NOVO MAJORITARIAMENTE FUNCIONAL")
        elif taxa_sucesso >= 50:
            print("   ⚠️ SISTEMA NOVO PARCIALMENTE FUNCIONAL")
        else:
            print("   ❌ SISTEMA NOVO COM PROBLEMAS CRÍTICOS")
        
        print(f"\n💡 PRÓXIMOS PASSOS:")
        if falhou == 0:
            print("   🚀 Sistema pronto para integração completa no routes.py")
            print("   🔧 Implementar ativação direta do sistema novo")
        else:
            print("   🔧 Corrigir problemas identificados nos testes")
            print("   🔍 Verificar dependências e configurações")


async def main():
    """Executa testes completos"""
    teste = TesteSistemaNovoCompleto()
    await teste.executar_todos_testes()


if __name__ == "__main__":
    asyncio.run(main()) 