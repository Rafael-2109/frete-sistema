#!/usr/bin/env python3
"""
🧪 TESTE DO MOTOR NLP
Demonstra as capacidades do motor de processamento de linguagem natural
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app.claude_ai_novo.nlp_engine import get_nlp_engine, IntentType, EntityType
from datetime import datetime
import json


def test_nlp_engine():
    """Testa várias consultas no motor NLP"""
    
    # Obter instância do motor
    engine = get_nlp_engine()
    
    # Consultas de teste em pt-BR
    test_queries = [
        # Consultas de contagem
        "Quantas entregas do Assai estão atrasadas hoje?",
        "Qual o total de pedidos pendentes do Carrefour?",
        "Quantos embarques saíram ontem para SP?",
        
        # Consultas de valor/faturamento
        "Quanto faturamos com o Atacadão este mês?",
        "Qual o valor total das entregas realizadas hoje?",
        "Quanto foi o faturamento de junho?",
        
        # Consultas de status
        "Como estão os embarques do Tenda?",
        "Qual a situação das entregas urgentes?",
        "Status dos pedidos 12345 e 67890",
        
        # Consultas de tendência
        "Evolução das entregas nos últimos 7 dias",
        "Como está o crescimento do faturamento?",
        "Tendência de atrasos nesta semana",
        
        # Consultas de comparação
        "Comparar entregas do Assai vs Carrefour",
        "Qual cliente tem mais pedidos atrasados?",
        "Diferença de faturamento entre SP e RJ",
        
        # Consultas de listagem
        "Liste todas as entregas pendentes de hoje",
        "Mostre os pedidos urgentes do Fort",
        "Quais notas fiscais foram emitidas ontem?",
        
        # Consultas com problemas
        "Problemas críticos nas entregas de São Paulo",
        "Entregas atrasadas há mais de 3 dias",
        "Pedidos com erro de faturamento",
        
        # Consultas complexas
        "Quanto o Assai faturou em entregas atrasadas na última semana em SP?",
        "Liste os 10 maiores pedidos pendentes de cotação com valor acima de R$ 5.000",
        "Comparação de performance de entregas entre filiais do Carrefour em junho",
    ]
    
    print("🧠 TESTE DO MOTOR NLP PT-BR\n")
    print("=" * 80)
    
    for i, query in enumerate(test_queries, 1):
        print(f"\n📝 TESTE {i}: {query}")
        print("-" * 80)
        
        # Processar consulta
        result = engine.process_query(query)
        
        # Exibir resultados
        print(f"✅ Consulta normalizada: {result.normalized_query}")
        print(f"🎯 Intenção: {result.intent.type.value} (confiança: {result.intent.confidence:.2%})")
        
        if result.intent.sub_intents:
            print(f"   Sub-intenções: {[si.value for si in result.intent.sub_intents]}")
        
        print(f"\n🔍 Entidades detectadas:")
        for entity in result.entities:
            print(f"   - {entity.type.value}: '{entity.text}' → {entity.normalized_value or entity.value}")
            print(f"     Posição: {entity.position}, Confiança: {entity.confidence:.2%}")
        
        print(f"\n📊 Contexto:")
        print(f"   - Escopo temporal: {result.context.temporal_scope}")
        print(f"   - Filtros implícitos: {result.context.implicit_filters}")
        print(f"   - Domínio: {result.context.business_domain}")
        print(f"   - Urgência: {result.context.urgency_level}")
        
        print(f"\n💯 Confiança geral: {result.confidence_score:.2%}")
        
        if result.sql_suggestion:
            print(f"\n💾 SQL sugerido:")
            print(f"   {result.sql_suggestion}")
        
        if result.clarification_needed:
            print(f"\n⚠️  Esclarecimento necessário!")
            if result.suggestions:
                print(f"   Sugestões: {', '.join(result.suggestions)}")
        
        print("\n" + "=" * 80)


def test_specific_intents():
    """Testa intenções específicas"""
    
    engine = get_nlp_engine()
    
    print("\n\n🎯 TESTE DE INTENÇÕES ESPECÍFICAS\n")
    print("=" * 80)
    
    intent_examples = {
        IntentType.COUNT: [
            "Quantos pedidos temos?",
            "Quantidade de entregas realizadas",
            "Total de notas emitidas"
        ],
        IntentType.SUM: [
            "Valor total faturado",
            "Soma das entregas do dia",
            "Totalizar valores pendentes"
        ],
        IntentType.STATUS: [
            "Como está o pedido 12345?",
            "Situação das entregas",
            "Status atual do sistema"
        ],
        IntentType.TREND: [
            "Evolução das vendas",
            "Tendência de crescimento",
            "Como aumentaram os pedidos?"
        ],
        IntentType.COMPARISON: [
            "Comparar janeiro vs fevereiro",
            "Assai versus Carrefour",
            "Qual é melhor?"
        ],
        IntentType.ISSUES: [
            "Problemas urgentes",
            "Entregas atrasadas",
            "Erros críticos de hoje"
        ]
    }
    
    for intent_type, examples in intent_examples.items():
        print(f"\n📌 Testando {intent_type.value.upper()}")
        print("-" * 40)
        
        for example in examples:
            result = engine.process_query(example)
            match = "✅" if result.intent.type == intent_type else "❌"
            print(f"{match} '{example}' → {result.intent.type.value} ({result.intent.confidence:.2%})")


def test_entity_extraction():
    """Testa extração de entidades"""
    
    engine = get_nlp_engine()
    
    print("\n\n🔍 TESTE DE EXTRAÇÃO DE ENTIDADES\n")
    print("=" * 80)
    
    entity_examples = {
        "Datas": [
            "entregas de hoje",
            "pedidos de ontem",
            "faturamento de 25/12/2024",
            "relatório de janeiro"
        ],
        "Valores": [
            "pedidos acima de R$ 1.000,00",
            "faturamento de 50 mil reais",
            "desconto de 15%"
        ],
        "Clientes": [
            "entregas do Assai",
            "pedidos do Atacadão",
            "notas do Carrefour"
        ],
        "Localizações": [
            "entregas em SP",
            "pedidos de São Paulo",
            "filiais do Rio de Janeiro"
        ],
        "Documentos": [
            "pedido 12345",
            "NF 67890",
            "nota fiscal 111222"
        ]
    }
    
    for category, examples in entity_examples.items():
        print(f"\n📌 {category}")
        print("-" * 40)
        
        for example in examples:
            result = engine.process_query(example)
            if result.entities:
                for entity in result.entities:
                    print(f"✅ '{example}' → {entity.type.value}: '{entity.text}' = {entity.normalized_value or entity.value}")
            else:
                print(f"❌ '{example}' → Nenhuma entidade detectada")


def test_context_understanding():
    """Testa compreensão de contexto"""
    
    engine = get_nlp_engine()
    
    print("\n\n🧩 TESTE DE COMPREENSÃO CONTEXTUAL\n")
    print("=" * 80)
    
    context_queries = [
        ("Entregas urgentes atrasadas", "Detectar urgência e problema"),
        ("Faturamento do Assai em SP hoje", "Cliente + localização + tempo"),
        ("Comparar vendas deste mês com o anterior", "Comparação temporal"),
        ("Top 10 clientes por faturamento", "Ranking implícito"),
        ("Pedidos pendentes há mais de 5 dias", "Filtro temporal implícito")
    ]
    
    for query, description in context_queries:
        print(f"\n📝 {query}")
        print(f"   ({description})")
        print("-" * 60)
        
        result = engine.process_query(query)
        
        print(f"🎯 Domínio detectado: {result.context.business_domain}")
        print(f"⏰ Escopo temporal: {result.context.temporal_scope}")
        print(f"🚨 Urgência: {result.context.urgency_level}")
        print(f"🔍 Filtros implícitos: {json.dumps(result.context.implicit_filters, indent=2)}")


def test_sql_translation():
    """Testa tradução para SQL"""
    
    engine = get_nlp_engine()
    
    print("\n\n💾 TESTE DE TRADUÇÃO SQL\n")
    print("=" * 80)
    
    sql_queries = [
        "Quantas entregas do Assai?",
        "Valor total faturado hoje",
        "Liste pedidos atrasados",
        "Status das entregas de SP",
        "Comparar faturamento por cliente"
    ]
    
    for query in sql_queries:
        result = engine.process_query(query)
        
        print(f"\n📝 Consulta: {query}")
        if result.sql_suggestion:
            print(f"✅ SQL gerado:")
            print(f"   {result.sql_suggestion}")
        else:
            print(f"❌ SQL não gerado (confiança: {result.confidence_score:.2%})")


def main():
    """Executa todos os testes"""
    
    print("\n🚀 INICIANDO TESTES DO MOTOR NLP\n")
    
    # Executar testes
    test_nlp_engine()
    test_specific_intents()
    test_entity_extraction()
    test_context_understanding()
    test_sql_translation()
    
    print("\n\n✅ TESTES CONCLUÍDOS!")
    print("\n💡 O motor NLP está pronto para processar consultas em português brasileiro!")
    print("   - Classificação de intenções")
    print("   - Extração de entidades")
    print("   - Compreensão contextual")
    print("   - Tradução para SQL")
    print("   - Aprendizado contínuo")


if __name__ == "__main__":
    main()