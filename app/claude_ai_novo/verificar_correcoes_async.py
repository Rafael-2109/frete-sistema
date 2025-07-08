#!/usr/bin/env python3
"""
🔧 VERIFICAÇÃO DAS CORREÇÕES ASYNC/AWAIT

Verifica se os problemas reportados pelo Pylance foram resolvidos:
1. integration_manager.py (linhas 180 e 242)
2. claude_transition.py (linha 48)
"""

import os
import sys

# Ajustar path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

def verificar_correcoes():
    """Verifica se as correções foram aplicadas"""
    
    print("🔧 VERIFICAÇÃO DAS CORREÇÕES ASYNC/AWAIT")
    print("=" * 50)
    
    resultados = []
    
    # 1. VERIFICAR INTEGRATION_MANAGER.PY
    print("\n1. 📊 VERIFICANDO integration_manager.py:")
    try:
        integration_file = os.path.join(current_dir, "integration", "integration_manager.py")
        
        if os.path.exists(integration_file):
            with open(integration_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Verificar se tem verificação de __await__
            if 'hasattr' in content and '__await__' in content:
                print("   ✅ Verificação async implementada")
                resultados.append("✅ Verificação async implementada")
            else:
                print("   ❌ Verificação async não encontrada")
                resultados.append("❌ Verificação async ausente")
                
            # Verificar se ainda tem await direto sem verificação
            lines = content.split('\n')
            await_direto_sem_verificacao = False
            
            for i, line in enumerate(lines):
                if 'await self.claude_integration.processar_consulta_real' in line:
                    # Verificar se há hasattr na mesma linha ou linhas anteriores próximas
                    verificacao_encontrada = False
                    
                    # Verificar linha atual
                    if 'hasattr' in line:
                        verificacao_encontrada = True
                    
                    # Verificar até 5 linhas anteriores
                    for j in range(max(0, i-5), i):
                        if 'hasattr' in lines[j] and '__await__' in lines[j]:
                            verificacao_encontrada = True
                            break
                    
                    if not verificacao_encontrada:
                        await_direto_sem_verificacao = True
                        break
            
            if not await_direto_sem_verificacao:
                print("   ✅ Não há await direto sem verificação")
                resultados.append("✅ Await condicionado")
            else:
                print("   ❌ Ainda há await direto sem verificação")
                resultados.append("❌ Await direto presente")
                
        else:
            print("   ❌ Arquivo não encontrado")
            resultados.append("❌ Arquivo não encontrado")
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append(f"❌ Erro: {str(e)[:50]}")
    
    # 2. VERIFICAR CLAUDE_TRANSITION.PY
    print("\n2. 🔄 VERIFICANDO claude_transition.py:")
    try:
        transition_file = os.path.join(project_root, "app", "claude_transition.py")
        
        if os.path.exists(transition_file):
            with open(transition_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Verificar se tem verificação de __await__
            if 'hasattr' in content and '__await__' in content:
                print("   ✅ Verificação async implementada")
                resultados.append("✅ Transition verificação async")
            else:
                print("   ❌ Verificação async não encontrada")
                resultados.append("❌ Transition sem verificação")
                
            # Verificar se linha 48 foi corrigida
            lines = content.split('\n')
            if len(lines) > 47:  # linha 48 (index 47)
                linha_48 = lines[47].strip()
                if 'hasattr' in linha_48 or 'await' not in linha_48:
                    print("   ✅ Linha 48 corrigida")
                    resultados.append("✅ Linha 48 corrigida")
                else:
                    print(f"   ❌ Linha 48 ainda problemática: {linha_48}")
                    resultados.append("❌ Linha 48 problemática")
            
        else:
            print("   ❌ Arquivo não encontrado")
            resultados.append("❌ Transition não encontrado")
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append(f"❌ Erro transition: {str(e)[:50]}")
    
    # 3. VERIFICAR IMPORTS ANTROPIC
    print("\n3. 🤖 VERIFICANDO claude_client.py:")
    try:
        client_file = os.path.join(current_dir, "integration", "claude", "claude_client.py")
        
        if os.path.exists(client_file):
            with open(client_file, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Verificar se tem tipagem correta para messages
            if 'MessageParam' in content or 'from typing' in content:
                print("   ✅ Arquivo existe e tem tipagem")
                resultados.append("✅ claude_client tipagem")
            else:
                print("   ⚠️ Pode precisar de ajuste de tipagem")
                resultados.append("⚠️ claude_client tipagem")
        else:
            print("   ❌ Arquivo não encontrado")
            resultados.append("❌ claude_client não encontrado")
            
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        resultados.append(f"❌ Erro client: {str(e)[:50]}")
    
    # RESUMO
    print("\n" + "=" * 50)
    print("📊 RESUMO DAS VERIFICAÇÕES:")
    print("=" * 50)
    
    sucessos = len([r for r in resultados if r.startswith("✅")])
    parciais = len([r for r in resultados if r.startswith("⚠️")])
    total = len(resultados)
    
    for resultado in resultados:
        print(f"   {resultado}")
    
    print(f"\n🎯 TAXA DE SUCESSO: {sucessos}/{total} ({sucessos/total*100:.1f}%)")
    if parciais > 0:
        print(f"⚠️ AJUSTES PARCIAIS: {parciais}")
    
    if sucessos >= 5:
        print("\n🎉 CORREÇÕES ASYNC/AWAIT APLICADAS COM SUCESSO!")
        print("✅ Problemas do Pylance devem estar resolvidos")
        print("✅ Sistema deve funcionar sem erros de coroutine")
        return True
    elif sucessos >= 3:
        print("\n⚠️ CORREÇÕES PARCIALMENTE APLICADAS")
        print("🔧 Alguns ajustes finais podem ser necessários")
        return True
    else:
        print("\n❌ CORREÇÕES PRECISAM DE MAIS TRABALHO")
        print("🔧 Problemas async/await ainda precisam ser resolvidos")
        return False

if __name__ == "__main__":
    verificar_correcoes() 