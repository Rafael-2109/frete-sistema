#!/usr/bin/env python3
"""
🔧 TESTE DAS CORREÇÕES DE NOMENCLATURA E FUNCIONALIDADES

Valida as 4 correções principais:
1. Knowledge Manager integrado
2. Domain vs Domínio (nomenclatura consistente)
3. Grupo Empresarial restaurado
4. UFs completas do utils/ufs.py
"""

import sys
import os
import asyncio
from typing import Dict, Any
from datetime import datetime

# Adicionar caminho
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

async def test_correcoes_nomenclatura():
    """Testa todas as correções aplicadas"""
    
    print("🔧 TESTE DAS CORREÇÕES DE NOMENCLATURA E FUNCIONALIDADES")
    print("="*65)
    
    # 1. TESTAR KNOWLEDGE MANAGER NO SMARTBASEAGENT
    print("\n📚 TESTE 1: Knowledge Manager Integration")
    
    try:
        from app.claude_ai_novo.multi_agent.agent_types import AgentType
        from app.claude_ai_novo.multi_agent.agents.smart_base_agent import SmartBaseAgent
        
        agent = SmartBaseAgent(AgentType.ENTREGAS)
        
        # Verificar se knowledge_manager foi carregado
        tem_knowledge = hasattr(agent, 'tem_knowledge_manager') and agent.tem_knowledge_manager
        
        if tem_knowledge:
            print("   ✅ Knowledge Manager integrado com sucesso")
            print(f"   📊 Tipo: {type(agent.knowledge_manager).__name__}")
        else:
            print("   ❌ Knowledge Manager não carregado")
            
    except Exception as e:
        print(f"   ❌ Erro ao testar Knowledge Manager: {e}")
        tem_knowledge = False
    
    # 2. TESTAR NOMENCLATURA DOMAIN vs DOMÍNIO
    print("\n🌐 TESTE 2: Nomenclatura Português (domínio)")
    
    try:
        # Verificar se os métodos usam nomenclatura em português
        conhecimento = agent._load_domain_knowledge()
        
        # Verificar se as chaves estão em português
        chaves_portugues = [
            'modelos_principais' in str(conhecimento),
            'campos_chave' in str(conhecimento),
            'foco' in str(conhecimento)
        ]
        
        nomenclatura_ok = all(chaves_portugues)
        
        if nomenclatura_ok:
            print("   ✅ Nomenclatura em português aplicada")
            print(f"   📝 Campos encontrados: modelos_principais, campos_chave, foco")
        else:
            print("   ❌ Ainda usa nomenclatura em inglês")
            print(f"   📝 Conhecimento: {list(conhecimento.keys())[:3]}")
            
    except Exception as e:
        print(f"   ❌ Erro ao testar nomenclatura: {e}")
        nomenclatura_ok = False
    
    # 3. TESTAR GRUPO EMPRESARIAL NO QUERY ANALYZER
    print("\n🏢 TESTE 3: Grupo Empresarial Restoration")
    
    try:
        from app.claude_ai_novo.analyzers.query_analyzer import get_query_analyzer
        
        query_analyzer = get_query_analyzer()
        
        # Testar detecção de grupo empresarial
        resultado = query_analyzer.analyze_query("Quantas entregas do Assai estão atrasadas?")
        entidades = resultado.get('entities', [])
        
        # Verificar se detectou grupo empresarial ou empresa
        grupo_detectado = any('grupo_empresarial:' in entity or 'empresa:' in entity for entity in entidades)
        
        if grupo_detectado:
            print("   ✅ Grupo Empresarial funcionando")
            print(f"   🏢 Entidades detectadas: {entidades}")
        else:
            print("   ❌ Grupo Empresarial não detectado")
            print(f"   📝 Entidades retornadas: {entidades}")
            
    except Exception as e:
        print(f"   ❌ Erro ao testar Grupo Empresarial: {e}")
        grupo_detectado = False
    
    # 4. TESTAR UFS COMPLETAS
    print("\n🗺️ TESTE 4: UFs Completas (utils/ufs.py)")
    
    try:
        # Testar detecção de diferentes estados
        estados_teste = [
            "Entregas em SP estão ok",
            "Problemas no RJ hoje", 
            "Status AC urgente",
            "Verificar TO amanhã"
        ]
        
        deteccoes_estados = []
        
        for consulta in estados_teste:
            resultado = query_analyzer.analyze_query(consulta)
            entidades = resultado.get('entities', [])
            
            estados_encontrados = [e for e in entidades if 'estado:' in e]
            deteccoes_estados.extend(estados_encontrados)
        
        # Verificar se detectou estados diversos (não só os 8 básicos)
        estados_detectados = len(set(deteccoes_estados))
        
        if estados_detectados >= 3:
            print("   ✅ UFs completas funcionando")
            print(f"   🗺️ Estados detectados: {deteccoes_estados}")
        else:
            print("   ⚠️ Poucos estados detectados")
            print(f"   📝 Estados: {deteccoes_estados}")
            
        # Verificar se está usando utils/ufs.py
        try:
            from app.utils.ufs import UF_LIST
            total_ufs = len(UF_LIST)
            print(f"   📊 Total UFs disponíveis: {total_ufs}")
            ufs_ok = total_ufs >= 27
        except:
            ufs_ok = False
            
    except Exception as e:
        print(f"   ❌ Erro ao testar UFs: {e}")
        ufs_ok = False
        estados_detectados = 0
    
    # 5. RELATÓRIO CONSOLIDADO
    print("\n📋 RELATÓRIO CONSOLIDADO")
    print("="*65)
    
    correcoes = {
        'Knowledge Manager': tem_knowledge,
        'Nomenclatura Português': nomenclatura_ok,
        'Grupo Empresarial': grupo_detectado,
        'UFs Completas': ufs_ok
    }
    
    sucesso_total = sum(correcoes.values())
    total_testes = len(correcoes)
    
    for nome, status in correcoes.items():
        icon = "✅" if status else "❌"
        print(f"   {icon} {nome}")
    
    print(f"\n   📊 Taxa de sucesso: {sucesso_total}/{total_testes} ({sucesso_total/total_testes*100:.1f}%)")
    
    if sucesso_total == total_testes:
        print("\n   🎉 TODAS AS CORREÇÕES APLICADAS COM SUCESSO!")
        print("   🚀 Sistema agora possui:")
        print("      • Knowledge Manager integrado")
        print("      • Nomenclatura consistente em português")
        print("      • Detecção inteligente de grupos empresariais")  
        print("      • Cobertura completa de UFs brasileiras")
    else:
        print(f"\n   ⚠️ {total_testes - sucesso_total} correção(ões) precisam de ajustes")
    
    return {
        'knowledge_manager': tem_knowledge,
        'nomenclatura_portugues': nomenclatura_ok,
        'grupo_empresarial': grupo_detectado,
        'ufs_completas': ufs_ok,
        'todas_correcoes_ok': sucesso_total == total_testes
    }

if __name__ == "__main__":
    result = asyncio.run(test_correcoes_nomenclatura())
    
    print(f"\n🎯 RESULTADO FINAL: {result}")
    
    if result['todas_correcoes_ok']:
        print("\n✅ SISTEMA COMPLETAMENTE CORRIGIDO E MELHORADO!")
    else:
        print("\n🔧 ALGUMAS CORREÇÕES NECESSITAM AJUSTES FINAIS") 