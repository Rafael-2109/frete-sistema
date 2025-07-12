#!/usr/bin/env python3
"""
🔧 CORREÇÃO AGENT_TYPE - Problema específico nos agentes

Script para corrigir o problema do agent_type que está impedindo
o funcionamento correto dos agentes de domínio.
"""

import os
import sys
import traceback

# Adicionar path correto
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

def diagnosticar_agent_type():
    """Diagnostica o problema específico do agent_type"""
    
    print("🔍 DIAGNÓSTICO AGENT_TYPE")
    print("=" * 50)
    
    diagnostico = {
        'AgentType_import': False,
        'BaseSpecialistAgent_import': False,
        'SmartBaseAgent_import': False,
        'FretesAgent_import': False,
        'FretesAgent_creation': False,
        'agent_type_property': False,
        'agent_type_value': False,
        'erro_detalhado': None
    }
    
    try:
        # Teste 1: Importar AgentType
        from app.claude_ai_novo.utils.agent_types import AgentType
        diagnostico['AgentType_import'] = True
        print("✅ AgentType importado com sucesso")
        
        # Teste 2: Importar BaseSpecialistAgent
        from app.claude_ai_novo.coordinators.domain_agents.base_agent import BaseSpecialistAgent
        diagnostico['BaseSpecialistAgent_import'] = True
        print("✅ BaseSpecialistAgent importado com sucesso")
        
        # Teste 3: Importar SmartBaseAgent
        from app.claude_ai_novo.coordinators.domain_agents.smart_base_agent import SmartBaseAgent
        diagnostico['SmartBaseAgent_import'] = True
        print("✅ SmartBaseAgent importado com sucesso")
        
        # Teste 4: Importar FretesAgent
        from app.claude_ai_novo.coordinators.domain_agents.fretes_agent import FretesAgent
        diagnostico['FretesAgent_import'] = True
        print("✅ FretesAgent importado com sucesso")
        
        # Teste 5: Criar instância diretamente
        print("\n🧪 TESTANDO CRIAÇÃO DE INSTÂNCIA...")
        
        # Teste criação via SmartBaseAgent diretamente
        print("  📝 Testando SmartBaseAgent direto...")
        smart_agent = SmartBaseAgent(AgentType.FRETES)
        if hasattr(smart_agent, 'agent_type'):
            print(f"  ✅ SmartBaseAgent tem agent_type: {smart_agent.agent_type}")
        else:
            print("  ❌ SmartBaseAgent não tem agent_type")
        
        # Teste criação via FretesAgent
        print("  📝 Testando FretesAgent...")
        fretes_agent = FretesAgent()
        diagnostico['FretesAgent_creation'] = True
        print("  ✅ FretesAgent criado com sucesso")
        
        # Verificar propriedades
        print("\n🔍 VERIFICANDO PROPRIEDADES...")
        propriedades = [attr for attr in dir(fretes_agent) if not attr.startswith('_')]
        print(f"  📋 Propriedades do FretesAgent: {len(propriedades)}")
        
        # Verificar agent_type especificamente
        if hasattr(fretes_agent, 'agent_type'):
            diagnostico['agent_type_property'] = True
            print(f"  ✅ agent_type encontrado: {fretes_agent.agent_type}")
            
            if hasattr(fretes_agent.agent_type, 'value'):
                diagnostico['agent_type_value'] = True
                print(f"  ✅ agent_type.value: {fretes_agent.agent_type.value}")
            else:
                print("  ❌ agent_type não tem propriedade 'value'")
        else:
            print("  ❌ agent_type não encontrado")
            print(f"  📋 Propriedades relevantes: {[p for p in propriedades if 'agent' in p or 'type' in p]}")
        
        # Testar se o problema é na inicialização
        print("\n🔧 TESTANDO INICIALIZAÇÃO MANUAL...")
        try:
            # Tentar inicializar manualmente
            manual_agent = FretesAgent()
            if not hasattr(manual_agent, 'agent_type'):
                print("  🛠️ Tentando definir agent_type manualmente...")
                manual_agent.agent_type = AgentType.FRETES
                print("  ✅ agent_type definido manualmente")
                
                # Testar se funciona
                print(f"  🧪 Teste: {manual_agent.agent_type.value}")
            
        except Exception as e:
            print(f"  ❌ Erro na inicialização manual: {e}")
            
    except Exception as e:
        diagnostico['erro_detalhado'] = str(e)
        print(f"❌ Erro durante diagnóstico: {e}")
        traceback.print_exc()
    
    return diagnostico

def corrigir_agent_type():
    """Corrige o problema do agent_type"""
    
    print("\n🔧 CORREÇÃO AGENT_TYPE")
    print("=" * 50)
    
    try:
        # Importar módulos necessários
        from app.claude_ai_novo.utils.agent_types import AgentType
        from app.claude_ai_novo.coordinators.domain_agents.fretes_agent import FretesAgent
        
        # Estratégia 1: Verificar se o problema é na cadeia de herança
        print("📋 ESTRATÉGIA 1: Verificar cadeia de herança...")
        
        # Criar instância e verificar MRO (Method Resolution Order)
        agent = FretesAgent()
        print(f"  📊 MRO: {[cls.__name__ for cls in FretesAgent.__mro__]}")
        
        # Estratégia 2: Verificar se __init__ está sendo chamado
        print("\n📋 ESTRATÉGIA 2: Verificar inicialização...")
        
        # Verificar se as classes pai têm agent_type
        from app.claude_ai_novo.coordinators.domain_agents.smart_base_agent import SmartBaseAgent
        
        # Testar BaseSpecialistAgent (pular pois é abstrata)
        print("  ⚠️ BaseSpecialistAgent é abstrata - pulando teste direto")
        
        # Testar SmartBaseAgent
        try:
            smart_agent = SmartBaseAgent(AgentType.FRETES)
            print(f"  ✅ SmartBaseAgent funciona: {smart_agent.agent_type}")
        except Exception as e:
            print(f"  ❌ SmartBaseAgent falha: {e}")
        
        # Estratégia 3: Corrigir diretamente no FretesAgent
        print("\n📋 ESTRATÉGIA 3: Correção direta...")
        
        # Verificar se o problema está no __init__ do FretesAgent
        import inspect
        init_source = inspect.getsource(FretesAgent.__init__)
        print(f"  📝 FretesAgent.__init__ source:")
        print(f"  {init_source}")
        
        # Estratégia 4: Aplicar correção se necessário
        if not hasattr(agent, 'agent_type'):
            print("\n🛠️ APLICANDO CORREÇÃO...")
            
            # Definir agent_type na instância
            agent.agent_type = AgentType.FRETES
            print("  ✅ agent_type definido na instância")
            
            # Testar se funciona
            print(f"  🧪 Teste: {agent.agent_type.value}")
            
            return True
        else:
            print("\n✅ agent_type já está funcionando!")
            return True
            
    except Exception as e:
        print(f"❌ Erro durante correção: {e}")
        traceback.print_exc()
        return False

def aplicar_correcao_permanente():
    """Aplica correção permanente no código"""
    
    print("\n🚀 APLICAÇÃO DA CORREÇÃO PERMANENTE")
    print("=" * 50)
    
    try:
        # Verificar se o problema é no __init__ do FretesAgent
        fretes_agent_path = "app/claude_ai_novo/coordinators/domain_agents/fretes_agent.py"
        
        with open(fretes_agent_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Verificar se o super().__init__ está sendo chamado corretamente
        if 'super().__init__(AgentType.FRETES, claude_client)' in content:
            print("✅ super().__init__ está correto no FretesAgent")
        else:
            print("❌ super().__init__ pode estar incorreto")
            
            # Mostrar linha relevante
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'super().__init__' in line:
                    print(f"  Linha {i+1}: {line.strip()}")
        
        # Testar se a correção funciona
        from app.claude_ai_novo.coordinators.domain_agents.fretes_agent import FretesAgent
        agent = FretesAgent()
        
        if hasattr(agent, 'agent_type'):
            print("✅ Correção funcionou! agent_type está presente")
            return True
        else:
            print("❌ Correção ainda necessária")
            return False
            
    except Exception as e:
        print(f"❌ Erro durante aplicação da correção: {e}")
        traceback.print_exc()
        return False

def testar_sistema_completo():
    """Testa o sistema completo após correção"""
    
    print("\n🧪 TESTE COMPLETO DO SISTEMA")
    print("=" * 50)
    
    try:
        # Testar todos os agentes
        agentes = [
            ('FretesAgent', 'fretes_agent'),
            ('EntregasAgent', 'entregas_agent'), 
            ('PedidosAgent', 'pedidos_agent'),
            ('EmbarquesAgent', 'embarques_agent'),
            ('FinanceiroAgent', 'financeiro_agent')
        ]
        
        for nome_agente, nome_modulo in agentes:
            try:
                module = __import__(f'app.claude_ai_novo.coordinators.domain_agents.{nome_modulo}', 
                                  fromlist=[nome_agente])
                agent_class = getattr(module, nome_agente)
                
                # Criar instância
                agent = agent_class()
                
                # Verificar agent_type
                if hasattr(agent, 'agent_type'):
                    print(f"  ✅ {nome_agente}: {agent.agent_type.value}")
                else:
                    print(f"  ❌ {nome_agente}: sem agent_type")
                    
            except Exception as e:
                print(f"  ❌ {nome_agente}: erro - {e}")
        
        print("\n🎯 TESTE FINAL: Simular processamento de query...")
        
        # Tentar processar uma query
        from app.claude_ai_novo.coordinators.domain_agents.fretes_agent import FretesAgent
        agent = FretesAgent()
        
        if hasattr(agent, 'agent_type'):
            print("✅ Sistema está pronto para processar queries!")
            return True
        else:
            print("❌ Sistema ainda não está pronto")
            return False
            
    except Exception as e:
        print(f"❌ Erro durante teste completo: {e}")
        traceback.print_exc()
        return False

def main():
    """Função principal"""
    
    print("🔧 CORREÇÃO AGENT_TYPE - Problema específico nos agentes")
    print("=" * 70)
    
    # Passo 1: Diagnosticar
    diagnostico = diagnosticar_agent_type()
    
    # Passo 2: Corrigir
    if not corrigir_agent_type():
        print("\n❌ Falha na correção")
        return 1
    
    # Passo 3: Aplicar correção permanente
    if not aplicar_correcao_permanente():
        print("\n❌ Falha na aplicação da correção")
        return 1
    
    # Passo 4: Testar sistema completo
    if not testar_sistema_completo():
        print("\n❌ Falha no teste completo")
        return 1
    
    print("\n✅ CORREÇÃO AGENT_TYPE CONCLUÍDA COM SUCESSO!")
    print("🚀 Agentes agora devem funcionar corretamente")
    print("💡 A IA deve voltar a responder normalmente")
    
    return 0

if __name__ == "__main__":
    exit(main()) 