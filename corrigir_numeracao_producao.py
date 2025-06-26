#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 CORRETOR DE NUMERAÇÃO - PRODUÇÃO
Resolve o problema específico: Embarque #254 tem ID 278 (diferença de 24)

EXECUTE ESTE SCRIPT NO SERVIDOR DE PRODUÇÃO
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def opcao_1_avancar_numeros_simples():
    """
    OPÇÃO 1: Modifica a função para próximos embarques terem número = ID
    Mais simples e segura
    """
    print("🚀 CORREÇÃO RÁPIDA: Sincronizar números com IDs")
    print("=" * 60)
    
    # Fazer backup da função atual
    try:
        with open('app/utils/embarque_numero.py', 'r', encoding='utf-8') as f:
            conteudo_original = f.read()
            
        # Salvar backup
        with open('app/utils/embarque_numero.py.backup', 'w', encoding='utf-8') as f:
            f.write(conteudo_original)
        
        print("✅ Backup criado: app/utils/embarque_numero.py.backup")
        
        # Nova função que sincroniza com IDs
        nova_funcao = '''#!/usr/bin/env python3

"""
Utilitário centralizado para geração de números de embarque.
Evita duplicações e problemas de concorrência.
MODIFICADO: Sincroniza números com IDs para resolver dessincronização
"""

from app import db
from app.embarques.models import Embarque
import threading

# Lock para operações thread-safe
_lock = threading.Lock()

def obter_proximo_numero_embarque():
    """
    Obtém o próximo número de embarque de forma thread-safe.
    
    VERSÃO CORRIGIDA: Sincroniza com IDs quando necessário
    
    Returns:
        int: Próximo número de embarque disponível
    """
    with _lock:
        try:
            # Query otimizada para obter o maior número atual
            ultimo_numero = db.session.query(
                db.func.coalesce(db.func.max(Embarque.numero), 0)
            ).scalar()
            
            # 🔧 CORREÇÃO: Sincronizar com IDs se necessário
            ultimo_id = db.session.query(
                db.func.coalesce(db.func.max(Embarque.id), 0)
            ).scalar()
            
            # Se ID está à frente, usar ID como base
            if ultimo_id > ultimo_numero:
                ultimo_numero = ultimo_id
            
            proximo_numero = ultimo_numero + 1
            
            # Verifica se já existe um embarque com este número (safety check)
            while Embarque.query.filter_by(numero=proximo_numero).first():
                proximo_numero += 1
            
            return proximo_numero
            
        except Exception as e:
            # Fallback: se der erro, conta todos os embarques + 1
            total_embarques = Embarque.query.count()
            return total_embarques + 1
'''
        
        # Salvar nova versão
        with open('app/utils/embarque_numero.py', 'w', encoding='utf-8') as f:
            f.write(nova_funcao)
        
        print("✅ Função modificada com sucesso!")
        print()
        print("🎯 RESULTADO:")
        print("   • Próximos embarques terão número = ID")
        print("   • Por exemplo: se próximo ID for 279, embarque será #279")
        print("   • Isso resolve a dessincronização daqui pra frente")
        print("   • Embarques antigos mantêm numeração original")
        print()
        print("🔄 REINICIE O SERVIDOR RENDER para aplicar as mudanças")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False

def opcao_2_reset_postgresql():
    """
    OPÇÃO 2: Comando SQL para resetar sequência PostgreSQL
    Mais complexa, mas "mais limpa"
    """
    print("🔄 RESET DA SEQUÊNCIA POSTGRESQL")
    print("=" * 60)
    
    print("⚠️ Esta opção requer execução manual no PostgreSQL")
    print()
    print("📋 PASSOS PARA EXECUTAR:")
    print("1️⃣ Conecte no PostgreSQL do Render:")
    print("   → Render Dashboard → Database → Connect")
    print()
    print("2️⃣ Execute esta consulta para ver situação atual:")
    print("   SELECT MAX(id) as ultimo_id, MAX(numero) as ultimo_numero FROM embarques;")
    print()
    print("3️⃣ Se último número for 254 e último ID for 278, execute:")
    print("   SELECT setval('embarques_id_seq', 254, true);")
    print()
    print("4️⃣ Verifique o resultado:")
    print("   SELECT nextval('embarques_id_seq');")
    print("   (deve retornar 255)")
    print()
    print("5️⃣ Reverta o teste:")
    print("   SELECT setval('embarques_id_seq', 254, true);")
    print()
    print("💡 Após isso, próximo embarque será #255 com ID 255")
    
    return True

def reverter_opcao_1():
    """Reverte a Opção 1 usando o backup"""
    print("↩️ REVERTER CORREÇÃO")
    print("=" * 30)
    
    try:
        if not os.path.exists('app/utils/embarque_numero.py.backup'):
            print("❌ Backup não encontrado!")
            return False
        
        # Restaurar backup
        with open('app/utils/embarque_numero.py.backup', 'r', encoding='utf-8') as f:
            backup_content = f.read()
        
        with open('app/utils/embarque_numero.py', 'w', encoding='utf-8') as f:
            f.write(backup_content)
        
        print("✅ Função original restaurada!")
        print("🔄 REINICIE O SERVIDOR para aplicar")
        
        return True
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        return False

def main():
    """Menu principal simplificado"""
    print("🔧 CORRETOR DE NUMERAÇÃO - EMBARQUES")
    print("=" * 50)
    print("Problema: Embarque #254 tem ID 278 (diferença de 24)")
    print()
    
    print("💡 ESCOLHA UMA OPÇÃO:")
    print()
    print("1️⃣ AVANÇAR NÚMEROS (Recomendado)")
    print("   ✅ Simples e seguro")
    print("   ✅ Próximos embarques: número = ID")
    print("   ✅ Ex: Próximo será #279 com ID 279")
    print("   ⚠️ 'Pula' números 255-278")
    print()
    print("2️⃣ REBOBINAR IDs (Avançado)")  
    print("   ✅ Mantém sequência natural")
    print("   ✅ Próximo será #255 com ID 255")
    print("   ⚠️ Requer comando SQL manual")
    print()
    print("3️⃣ REVERTER (se já aplicou Opção 1)")
    print("   ↩️ Volta ao estado original")
    print()
    print("0️⃣ SAIR")
    print()
    
    opcao = input("Escolha (1/2/3/0): ").strip()
    
    if opcao == '1':
        print()
        confirmacao = input("⚠️ Confirma aplicar OPÇÃO 1? (s/N): ").lower()
        if confirmacao == 's':
            sucesso = opcao_1_avancar_numeros_simples()
            if sucesso:
                print("\n🎉 OPÇÃO 1 APLICADA COM SUCESSO!")
                print("🔄 Reinicie o servidor Render para ativar")
            else:
                print("\n❌ Falha na aplicação")
        else:
            print("❌ Operação cancelada")
    
    elif opcao == '2':
        print()
        opcao_2_reset_postgresql()
    
    elif opcao == '3':
        print()
        confirmacao = input("⚠️ Confirma REVERTER? (s/N): ").lower()
        if confirmacao == 's':
            sucesso = reverter_opcao_1()
            if sucesso:
                print("\n✅ REVERTIDO COM SUCESSO!")
            else:
                print("\n❌ Falha na reversão")
        else:
            print("❌ Operação cancelada")
    
    elif opcao == '0':
        print("👋 Saindo...")
    
    else:
        print("❌ Opção inválida")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n⏹️ Interrompido pelo usuário")
    except Exception as e:
        print(f"\n❌ ERRO: {e}") 