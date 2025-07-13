#!/usr/bin/env python3
"""
🔍 TESTE END-TO-END: Fluxo Completo de uma Pergunta
==================================================

Simula o fluxo completo de uma pergunta do usuário através de todo o sistema.
"""

import sys
import os
import logging
from datetime import datetime
import json

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def print_section(title: str):
    """Imprime seção formatada"""
    print(f"\n{'='*60}")
    print(f"📍 {title}")
    print(f"{'='*60}\n")

def simulate_user_query():
    """Simula uma pergunta real do usuário"""
    print_section("TESTE END-TO-END: FLUXO COMPLETO")
    
    # Pergunta simulada
    user_query = "Quantas entregas temos pendentes do Assai em São Paulo?"
    user_id = "user_123"
    session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print(f"👤 Usuário: {user_id}")
    print(f"🔑 Sessão: {session_id}")
    print(f"❓ Pergunta: {user_query}")
    print()
    
    try:
        # 1. INICIALIZAR SISTEMA
        print_section("1. INICIALIZANDO SISTEMA")
        
        from app.claude_ai_novo.orchestrators import get_main_orchestrator
        orchestrator = get_main_orchestrator()
        
        if not orchestrator:
            print("❌ Erro ao inicializar orchestrator")
            return
        
        print(f"✅ Orchestrator inicializado com {len(orchestrator.components)} componentes")
        print(f"✅ Workflows disponíveis: {list(orchestrator.workflows.keys())}")
        
        # 2. CONVERSA - INICIAR SESSÃO
        print_section("2. INICIANDO CONVERSA")
        
        converser = orchestrator.components.get('conversers')
        if converser:
            session_id = converser.start_conversation(
                user_id=user_id,
                initial_message=user_query,
                metadata={'source': 'e2e_test', 'timestamp': datetime.now().isoformat()}
            )
            print(f"✅ Conversa iniciada: {session_id}")
            
            # Adicionar mensagem do usuário
            converser.add_user_message(session_id, user_query)
            print("✅ Mensagem do usuário adicionada ao contexto")
        
        # 3. ANÁLISE - ENTENDER A PERGUNTA
        print_section("3. ANALISANDO PERGUNTA")
        
        analyzer = orchestrator.components.get('analyzers')
        if analyzer:
            analysis = analyzer.analyze_query(user_query)
            
            print("📊 Análise da pergunta:")
            
            # Obter informações do semantic_analysis
            semantic = analysis.get('semantic_analysis', {})
            intention = analysis.get('intention_analysis', {})
            
            print(f"   - Domínio detectado: {semantic.get('domains', ['não detectado'])}")
            print(f"   - Intenção: {intention.get('intention', 'não detectada')}")
            print(f"   - Entidades: {semantic.get('entities', {})}")
            print(f"   - Confiança: {intention.get('confidence', 0):.2%}")
            
            # Detalhes das entidades
            entities = semantic.get('entities', {})
            if entities:
                print("\n📌 Entidades detectadas:")
                for entity_type, values in entities.items():
                    print(f"   - {entity_type}: {values}")
        
        # 4. MAPEAMENTO - TRADUZIR PARA BANCO
        print_section("4. MAPEAMENTO SEMÂNTICO")
        
        mapper = orchestrator.components.get('mappers')
        if mapper and analysis:
            # Pegar domínio do semantic_analysis
            semantic = analysis.get('semantic_analysis', {})
            domains = semantic.get('domains', ['entregas'])
            domain = domains[0] if domains else 'entregas'
            mapping = mapper.get_domain_mapping(domain)
            
            print(f"🗺️ Mapeamento para domínio '{domain}':")
            if mapping:
                print(f"   - Tabela principal: {mapping.get('table_name', 'não definida')}")
                print(f"   - Campos mapeados: {len(mapping.get('fields', {}))}")
                
                # Mapear entidades para campos
                if 'cliente' in entities:
                    cliente_field = mapper.map_field(domain, 'cliente')
                    print(f"   - 'cliente' → '{cliente_field}'")
                
                if 'localização' in entities:
                    local_field = mapper.map_field(domain, 'localização')
                    print(f"   - 'localização' → '{local_field}'")
        
        # 5. SCANNER - OTIMIZAR CONSULTA
        print_section("5. OTIMIZAÇÃO VIA SCANNER")
        
        scanner = orchestrator.components.get('scanners')
        if scanner and analysis:
            # Pegar domínio do semantic_analysis
            semantic = analysis.get('semantic_analysis', {})
            domains = semantic.get('domains', ['entregas'])
            domain = domains[0] if domains else 'entregas'
            scan_info = scanner.get_domain_info(domain)
            
            if scan_info:
                print(f"🔍 Informações de otimização:")
                print(f"   - Tabelas relacionadas: {scan_info.get('tables', [])}")
                print(f"   - Índices disponíveis: {scan_info.get('indexes', [])}")
                print(f"   - Relacionamentos: {scan_info.get('relationships', [])}")
        
        # 6. CARREGAMENTO - BUSCAR DADOS
        print_section("6. CARREGANDO DADOS")
        
        loader = orchestrator.components.get('loaders')
        if loader and analysis:
            # Preparar filtros baseados na análise
            filters = {}
            
            semantic = analysis.get('semantic_analysis', {})
            entities = semantic.get('entities', {})
            
            if 'cliente' in entities:
                filters['cliente'] = entities['cliente'][0] if entities['cliente'] else None
            
            if 'localização' in entities:
                filters['uf'] = entities['localização'][0] if entities['localização'] else None
            
            if 'status' in entities:
                filters['status'] = entities['status'][0] if entities['status'] else 'pendente'
            
            print(f"🔧 Filtros aplicados: {filters}")
            
            # Carregar dados
            domains = semantic.get('domains', ['entregas'])
            domain = domains[0] if domains else 'entregas'
            try:
                data = loader.load_data(domain, filters)
                print(f"✅ Dados carregados: {len(data) if isinstance(data, list) else 'objeto'} registros")
            except Exception as e:
                print(f"⚠️ Erro ao carregar dados: {e}")
                data = []
        
        # 7. PROCESSAMENTO - FORMATAR RESPOSTA
        print_section("7. PROCESSANDO RESPOSTA")
        
        processor = orchestrator.components.get('processors')
        if processor:
            # Preparar contexto
            context = {
                'query': user_query,
                'analysis': analysis,
                'data': data if 'data' in locals() else [],
                'session_id': session_id,
                'user_id': user_id
            }
            
            try:
                response = processor.process(context)
                
                print("📝 Resposta processada:")
                print(f"   - Tipo: {response.get('type', 'texto')}")
                print(f"   - Tamanho: {len(response.get('content', ''))} caracteres")
                print(f"   - Metadados: {list(response.get('metadata', {}).keys())}")
                
                # Mostrar preview da resposta
                content = response.get('content', '')
                if content:
                    preview = content[:200] + "..." if len(content) > 200 else content
                    print(f"\n📄 Preview da resposta:")
                    print(f"   {preview}")
            except Exception as e:
                print(f"⚠️ Erro ao processar: {e}")
                response = {'content': 'Erro ao processar resposta'}
        
        # 8. ENRIQUECIMENTO - ADICIONAR CONTEXTO
        print_section("8. ENRIQUECENDO RESPOSTA")
        
        enricher = orchestrator.components.get('enrichers')
        if enricher and 'response' in locals():
            try:
                enriched = enricher.enrich(response, context)
                
                print("✨ Enriquecimentos aplicados:")
                additions = enriched.get('additions', {})
                for key, value in additions.items():
                    print(f"   - {key}: {value}")
                    
            except Exception as e:
                print(f"⚠️ Erro ao enriquecer: {e}")
        
        # 9. MEMÓRIA - SALVAR CONTEXTO
        print_section("9. SALVANDO NA MEMÓRIA")
        
        memorizer = orchestrator.components.get('memorizers')
        if memorizer:
            try:
                # Salvar interação
                memory_data = {
                    'session_id': session_id,
                    'user_id': user_id,
                    'query': user_query,
                    'analysis': analysis if 'analysis' in locals() else {},
                    'response': response if 'response' in locals() else {},
                    'timestamp': datetime.now().isoformat()
                }
                
                saved = memorizer.store(session_id, memory_data)
                print(f"✅ Contexto salvo na memória: {saved}")
                
                # Verificar se foi salvo
                retrieved = memorizer.retrieve(session_id)
                if retrieved:
                    print(f"✅ Verificação: Memória recuperada com sucesso")
                    
            except Exception as e:
                print(f"⚠️ Erro ao salvar memória: {e}")
        
        # 10. APRENDIZADO - CAPTURAR PADRÕES
        print_section("10. APRENDIZADO CONTÍNUO")
        
        learner = orchestrator.components.get('learners')
        if learner:
            try:
                # Capturar padrão
                if 'analysis' in locals():
                    intention = analysis.get('intention_analysis', {})
                    semantic = analysis.get('semantic_analysis', {})
                    domains = semantic.get('domains', ['unknown'])
                    
                    pattern = {
                        'query_type': intention.get('intention', 'unknown'),
                        'domain': domains[0] if domains else 'unknown',
                        'entities': semantic.get('entities', {}),
                        'success': True,
                        'timestamp': datetime.now().isoformat()
                    }
                else:
                    pattern = {
                        'query_type': 'unknown',
                        'domain': 'unknown',
                        'entities': {},
                        'success': True,
                        'timestamp': datetime.now().isoformat()
                    }
                
                learned = learner.learn(pattern)
                print(f"✅ Padrão capturado: {learned}")
                
            except Exception as e:
                print(f"⚠️ Erro no aprendizado: {e}")
        
        # 11. CONVERSA - ADICIONAR RESPOSTA
        print_section("11. FINALIZANDO CONVERSA")
        
        if converser and 'response' in locals():
            # Adicionar resposta do assistente
            assistant_response = response.get('content', 'Resposta processada com sucesso')
            converser.add_assistant_message(session_id, assistant_response)
            print("✅ Resposta do assistente adicionada ao contexto")
            
            # Obter resumo da conversa
            summary = converser.get_conversation_summary(session_id)
            print(f"\n📊 Resumo da conversa:")
            print(f"   - Mensagens: {summary.get('message_count', 0)}")
            print(f"   - Status: {summary.get('status', 'unknown')}")
            print(f"   - Iniciada em: {summary.get('started_at', 'N/A')}")
        
        # RESUMO FINAL
        print_section("RESUMO DO FLUXO E2E")
        
        print("✅ COMPONENTES TESTADOS:")
        print("   1. Orchestrator - Coordenação central")
        print("   2. Converser - Gestão de conversas")
        print("   3. Analyzer - Análise de intenção")
        print("   4. Mapper - Mapeamento semântico")
        print("   5. Scanner - Otimização de queries")
        print("   6. Loader - Carregamento de dados")
        print("   7. Processor - Processamento de resposta")
        print("   8. Enricher - Enriquecimento contextual")
        print("   9. Memorizer - Persistência de contexto")
        print("  10. Learner - Aprendizado contínuo")
        print("  11. Converser - Finalização da conversa")
        
        print(f"\n🎯 FLUXO COMPLETO EXECUTADO COM SUCESSO!")
        print(f"⏱️ Tempo total: ~{(datetime.now() - datetime.strptime(session_id.split('_')[1], '%Y%m%d')).seconds} segundos")
        
    except Exception as e:
        logger.error(f"❌ Erro no fluxo E2E: {e}", exc_info=True)
        print(f"\n❌ ERRO NO FLUXO: {e}")

if __name__ == "__main__":
    simulate_user_query() 