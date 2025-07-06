#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🧪 TESTE DAS CORREÇÕES DO CLAUDE AI
Verifica se as alterações feitas resolvem os problemas
"""

import sys
import os

# Adicionar diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

print("=== TESTE DAS CORREÇÕES DO CLAUDE AI ===\n")

# 1. Testar se NLP Analyzer foi corrigido
print("1. Testando correção do NLP Analyzer...")
try:
    from app.claude_ai.nlp_enhanced_analyzer import NLPEnhancedAnalyzer
    analyzer = NLPEnhancedAnalyzer()
    
    # Testar método correto
    result = analyzer.analisar_com_nlp("Qual o status das entregas do Assai?")
    
    if result and hasattr(result, 'palavras_chave'):
        print(f"   ✅ NLP funcionando! Palavras-chave: {result.palavras_chave}")
    else:
        print(f"   ❌ NLP retornou resultado inesperado: {result}")
        
except Exception as e:
    print(f"   ❌ Erro ao testar NLP: {e}")

# 2. Testar se campo_ligacao está tratado
print("\n2. Testando tratamento de campo_ligacao...")
try:
    from app.claude_ai.advanced_integration import SemanticLoopProcessor
    
    processor = SemanticLoopProcessor()
    
    # Simular análise semântica
    import asyncio
    async def test_semantic():
        result = await processor._analyze_semantics("Teste de análise semântica")
        return result
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        semantic_result = loop.run_until_complete(test_semantic())
        print(f"   ✅ Análise semântica OK: confiança={semantic_result.get('confidence', 0)}")
    finally:
        loop.close()
    
except Exception as e:
    print(f"   ❌ Erro na análise semântica: {e}")

# 3. Verificar mensagens de erro melhoradas
print("\n3. Verificando mensagens de erro melhoradas...")
try:
    # Verificar se as strings foram alteradas
    with open('app/claude_ai/multi_agent_system.py', 'r', encoding='utf-8') as f:
        content = f.read()
        
    if 'Desculpe, encontrei um problema ao processar sua consulta' in content:
        print("   ✅ Mensagens de erro melhoradas implementadas")
    else:
        print("   ❌ Mensagens de erro antigas ainda presentes")
        
except Exception as e:
    print(f"   ❌ Erro ao verificar arquivo: {e}")

# 4. Testar integração completa
print("\n4. Testando integração completa...")
try:
    from app.claude_ai.claude_real_integration import ClaudeRealIntegration
    
    # Criar instância
    claude = ClaudeRealIntegration()
    
    # Verificar se tem os componentes
    components = {
        'nlp_analyzer': hasattr(claude, 'nlp_analyzer'),
        'advanced_ai_system': hasattr(claude, 'advanced_ai_system'),
        'multi_agent_system': hasattr(claude, 'multi_agent_system')
    }
    
    print(f"   Componentes disponíveis:")
    for comp, available in components.items():
        status = "✅" if available else "❌"
        print(f"     {status} {comp}")
    
    # Testar análise de consulta
    analise = claude._analisar_consulta("Quantas entregas estão atrasadas?")
    print(f"\n   Análise de consulta:")
    print(f"     - Domínio: {analise.get('dominio', 'N/A')}")
    print(f"     - Tipo: {analise.get('tipo_consulta', 'N/A')}")
    
except Exception as e:
    print(f"   ❌ Erro na integração: {e}")
    import traceback
    traceback.print_exc()

print("\n✅ TESTE CONCLUÍDO!")
print("\n📝 RESUMO DAS CORREÇÕES:")
print("1. NLP Analyzer: método analyze_advanced_query → analisar_com_nlp")
print("2. Advanced Integration: tratamento de erro campo_ligacao")
print("3. Multi Agent: mensagens de erro melhoradas")
print("4. Claude Real: logs de debug adicionais")

print("\n💡 PRÓXIMOS PASSOS:")
print("1. Fazer commit das alterações")
print("2. Push para GitHub: git push")
print("3. Aguardar deploy no Render")
print("4. Testar no sistema de produção") 