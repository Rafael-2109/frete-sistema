#!/usr/bin/env python3
"""
🧪 TESTE - Sistema Novo com Dados Reais
Valida se o sistema novo está executando consultas com dados reais do banco
"""

import sys
import os
sys.path.insert(0, os.path.abspath('.'))

from app import create_app
from app.claude_transition import get_claude_transition
# DataExecutor removido - funcionalidade redundante
import json

def teste_sistema_transicao():
    """Testa se o sistema de transição está funcionando"""
    print("🔧 TESTE 1: Sistema de Transição")
    
    try:
        with create_app().app_context():
            transition = get_claude_transition()
            print(f"✅ Sistema ativo: {transition.sistema_ativo}")
            print(f"✅ Usar sistema novo: {transition.usar_sistema_novo}")
            
            if transition.sistema_ativo == "novo":
                print("✅ Sistema NOVO está ativo!")
                return True
            else:
                print("❌ Sistema ANTIGO está ativo")
                return False
                
    except Exception as e:
        print(f"❌ Erro no teste de transição: {e}")
        return False

# def teste_data_executor():
#     """Testa se o DataExecutor está funcionando"""
#     # DataExecutor removido - funcionalidade redundante
#     print("\n🎯 TESTE 2: Data Executor (REMOVIDO)")
#     print("✅ DataExecutor foi removido - funcionalidade redundante")
#     return True

def teste_consulta_real():
    """Testa consulta real com dados do banco"""
    print("\n📊 TESTE 2: Consulta Real com Dados")
    
    try:
        with create_app().app_context():
            # Usar sistema de transição ao invés do data_executor
            transition = get_claude_transition()
            
            # Testar consulta sobre entregas
            consulta = "Quantas entregas tivemos hoje?"
            print(f"🔍 Executando consulta: '{consulta}'")
            
            resposta = transition.processar_consulta(consulta)
            
            print(f"✅ Resposta recebida:")
            print(f"   - Tamanho: {len(resposta)} caracteres")
            
            if 'erro' in resposta.lower():
                print(f"❌ Erro na resposta: {resposta[:100]}...")
                return False
            
            # Verificar se tem dados úteis
            if len(resposta) > 50:
                print(f"✅ Resposta com conteúdo adequado")
                return True
            else:
                print(f"❌ Resposta muito curta")
                return False
            
    except Exception as e:
        print(f"❌ Erro no teste de consulta real: {e}")
        return False

def teste_integracao_completa():
    """Testa integração completa do sistema novo"""
    print("\n🚀 TESTE 4: Integração Completa")
    
    try:
        with create_app().app_context():
            transition = get_claude_transition()
            
            # Testar processamento completo
            consulta = "Preciso saber sobre as entregas de hoje"
            print(f"💬 Processando consulta: '{consulta}'")
            
            resposta = transition.processar_consulta(consulta)
            
            print(f"✅ Resposta recebida:")
            print(f"   - Tamanho: {len(resposta)} caracteres")
            
            # Evitar backslash em f-string
            primeira_linha = resposta.split('\n')[0]
            print(f"   - Primeira linha: {primeira_linha}")
            
            # Verificar se não tem placeholders
            placeholders = ['[X]', '[Y]', '[Z]', '[W]', '[%]']
            tem_placeholders = any(p in resposta for p in placeholders)
            
            if tem_placeholders:
                print("❌ PROBLEMA: Resposta contém placeholders!")
                for p in placeholders:
                    if p in resposta:
                        print(f"   - Encontrado: {p}")
                return False
            else:
                print("✅ Resposta sem placeholders - usando dados reais!")
                return True
                
    except Exception as e:
        print(f"❌ Erro no teste de integração: {e}")
        return False

def main():
    """Executa todos os testes"""
    print("🧪 TESTE COMPLETO: Sistema Novo com Dados Reais")
    print("=" * 60)
    
    testes = [
        ("Sistema de Transição", teste_sistema_transicao),
        # ("Data Executor", teste_data_executor),  # Removido
        ("Consulta Real", teste_consulta_real),
        ("Integração Completa", teste_integracao_completa)
    ]
    
    resultados = []
    
    for nome, funcao in testes:
        resultado = funcao()
        resultados.append((nome, resultado))
        
        if resultado:
            print(f"✅ {nome}: PASSOU")
        else:
            print(f"❌ {nome}: FALHOU")
    
    print("\n" + "=" * 60)
    print("📊 RESUMO DOS TESTES:")
    
    passou = sum(1 for _, r in resultados if r)
    total = len(resultados)
    
    print(f"✅ Passou: {passou}/{total}")
    print(f"❌ Falhou: {total - passou}/{total}")
    print(f"🎯 Taxa de sucesso: {passou/total*100:.1f}%")
    
    if passou == total:
        print("\n🎉 TODOS OS TESTES PASSARAM!")
        print("✅ Sistema novo funcionando com dados reais!")
    else:
        print("\n⚠️ ALGUNS TESTES FALHARAM")
        print("❌ Sistema ainda não está funcionando completamente")

if __name__ == "__main__":
    main() 