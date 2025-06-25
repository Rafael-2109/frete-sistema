#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
🚀 TESTE DIRETO NO SHELL DO RENDER
Execute este script no console do Render para testar funcionalidades
"""

import os
import sys
from datetime import datetime

# Configurar ambiente
os.environ['FLASK_APP'] = 'run.py'

# Importar aplicação
from app import create_app, db
from app.auth.models import Usuario
from app.claude_ai.intelligent_query_analyzer import get_intelligent_analyzer
from app.claude_ai.multi_agent_system import get_multi_agent_system
from app.claude_ai.human_in_loop_learning import HumanInLoopLearning
from app.utils.grupo_empresarial import GrupoEmpresarial

print("="*60)
print("🚀 TESTE DIRETO NO SHELL DO RENDER")
print("="*60)

# Criar contexto da aplicação
app = create_app()

with app.app_context():
    print("\n📊 TESTE 1: Conexão com Banco de Dados")
    try:
        # Contar usuários
        user_count = Usuario.query.count()
        print(f"✅ Banco conectado! Usuários cadastrados: {user_count}")
    except Exception as e:
        print(f"❌ Erro no banco: {e}")
    
    print("\n🧠 TESTE 2: Análise Inteligente de Consultas")
    try:
        analyzer = get_intelligent_analyzer()
        result = analyzer.analisar_consulta_inteligente("Quantas entregas do Assai estão atrasadas?")
        print(f"✅ Análise funcionando!")
        print(f"   Intenção: {result.intencao_principal}")
        print(f"   Confiança: {result.confianca_interpretacao:.1%}")
        if result.entidades_detectadas.get('grupos_empresariais'):
            print(f"   Grupo detectado: {result.entidades_detectadas['grupos_empresariais'][0]['nome']}")
    except Exception as e:
        print(f"❌ Erro na análise: {e}")
    
    print("\n🏢 TESTE 3: Sistema de Grupos Empresariais")
    try:
        detector = GrupoEmpresarial()
        
        # Testar detecção
        testes = [
            ("06.057.223/0001-00", "Assai"),
            ("75.315.333/0001-00", "Atacadão"),
            ("45.543.915/0001-00", "Carrefour")
        ]
        
        for cnpj, esperado in testes:
            grupo = detector.detectar_grupo(cnpj=cnpj)
            if grupo:
                print(f"✅ {esperado}: {grupo['nome']} - {grupo['metodo_deteccao']}")
            else:
                print(f"❌ {esperado}: Não detectado")
                
    except Exception as e:
        print(f"❌ Erro nos grupos: {e}")
    
    print("\n🤖 TESTE 4: Multi-Agent System")
    try:
        system = get_multi_agent_system()
        print(f"✅ Multi-Agent inicializado com {len(system.agents)} agents")
        for agent_name in system.agents.keys():
            print(f"   • {agent_name}")
    except Exception as e:
        print(f"❌ Erro no Multi-Agent: {e}")
    
    print("\n🔄 TESTE 5: Human-in-the-Loop")
    try:
        hil = HumanInLoopLearning()
        
        # Simular feedback
        feedback = hil.capture_user_feedback(
            query="Teste shell Render",
            response="Resposta teste",
            feedback="Funcionando perfeitamente!",
            feedback_type="positive",
            severity=5,
            context={"source": "shell_test"}
        )
        
        if feedback:
            print("✅ Human-in-the-Loop funcionando!")
            print(f"   Feedback ID: {feedback.get('feedback_id')}")
        else:
            print("⚠️ Human-in-the-Loop sem resposta")
            
    except Exception as e:
        print(f"❌ Erro no Human-in-the-Loop: {e}")
    
    print("\n🔍 TESTE 6: Variáveis de Ambiente")
    env_vars = {
        "DATABASE_URL": "✅" if os.environ.get("DATABASE_URL") else "❌",
        "ANTHROPIC_API_KEY": "✅" if os.environ.get("ANTHROPIC_API_KEY") else "❌",
        "REDIS_URL": "✅" if os.environ.get("REDIS_URL") else "⚠️ (opcional)",
        "SECRET_KEY": "✅" if os.environ.get("SECRET_KEY") else "❌"
    }
    
    for var, status in env_vars.items():
        print(f"{status} {var}")
    
    print("\n📈 TESTE 7: Consulta Rápida de Dados")
    try:
        from app.pedidos.models import Pedido
        from app.monitoramento.models import EntregaMonitorada
        from app.fretes.models import Frete
        
        pedidos = Pedido.query.count()
        entregas = EntregaMonitorada.query.count()
        fretes = Frete.query.count()
        
        print(f"✅ Dados no sistema:")
        print(f"   Pedidos: {pedidos:,}")
        print(f"   Entregas: {entregas:,}")
        print(f"   Fretes: {fretes:,}")
        
    except Exception as e:
        print(f"❌ Erro ao consultar dados: {e}")
    
    print("\n🎯 RESUMO:")
    print("="*60)
    print("✅ Testes concluídos!")
    print(f"📅 Data/Hora: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("\n💡 Dica: Para testar funcionalidades web, use o navegador:")
    print(f"   https://sistema-fretes.onrender.com/claude-ai/real")

print("\n🚀 Script finalizado!") 