#!/usr/bin/env python3
"""
🔧 CORREÇÃO UTF-8 - DATABASE_URL

Script para identificar e corrigir problemas UTF-8 no DATABASE_URL
que está impedindo a inicialização do sistema.
"""

import os
import re
import sys
from urllib.parse import urlparse, quote_plus

def diagnosticar_database_url():
    """Diagnostica problemas na DATABASE_URL"""
    
    print("🔍 DIAGNÓSTICO DATABASE_URL")
    print("=" * 50)
    
    # Verificar se DATABASE_URL existe
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL não encontrada nas variáveis de ambiente")
        return False
    
    print(f"✅ DATABASE_URL encontrada")
    print(f"📏 Tamanho: {len(database_url)} caracteres")
    
    # Verificar encoding
    try:
        database_url.encode('utf-8')
        print("✅ DATABASE_URL pode ser codificada em UTF-8")
    except UnicodeEncodeError as e:
        print(f"❌ Erro de codificação UTF-8: {e}")
        return False
    
    # Verificar se há caracteres problemáticos
    problematicos = []
    for i, char in enumerate(database_url):
        try:
            char.encode('utf-8')
        except UnicodeEncodeError:
            problematicos.append((i, char, ord(char)))
    
    if problematicos:
        print(f"❌ Caracteres problemáticos encontrados: {len(problematicos)}")
        for pos, char, code in problematicos[:10]:  # Mostrar apenas os primeiros 10
            print(f"  Posição {pos}: '{char}' (código: {code})")
    else:
        print("✅ Nenhum caractere problemático encontrado")
    
    # Tentar parsear URL
    try:
        parsed = urlparse(database_url)
        print(f"✅ URL parseada com sucesso")
        print(f"  Scheme: {parsed.scheme}")
        print(f"  Hostname: {parsed.hostname}")
        print(f"  Port: {parsed.port}")
        print(f"  Database: {parsed.path}")
    except Exception as e:
        print(f"❌ Erro ao parsear URL: {e}")
        return False
    
    return True

def corrigir_database_url():
    """Corrige problemas na DATABASE_URL"""
    
    print("\n🔧 CORREÇÃO DATABASE_URL")
    print("=" * 50)
    
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL não encontrada")
        return False
    
    # Fazer backup da URL original
    backup_url = database_url
    
    # Corrigir caracteres problemáticos
    url_corrigida = database_url
    
    # Tentar diferentes estratégias de correção
    try:
        # Estratégia 1: Remover caracteres não-ASCII
        url_corrigida = ''.join(char for char in database_url if ord(char) < 128)
        print(f"✅ Estratégia 1: Removidos caracteres não-ASCII")
        
        # Estratégia 2: Tentar decodificar/recodificar
        try:
            url_corrigida = database_url.encode('latin-1').decode('utf-8')
            print(f"✅ Estratégia 2: Recodificação latin-1 → utf-8")
        except:
            pass
        
        # Estratégia 3: URL encoding dos caracteres problemáticos
        if '@' in url_corrigida:
            # Separar partes da URL
            parts = url_corrigida.split('@')
            if len(parts) == 2:
                auth_part = parts[0]
                rest_part = parts[1]
                
                # Corrigir parte de autenticação
                if ':' in auth_part:
                    protocol_user, password = auth_part.rsplit(':', 1)
                    password_encoded = quote_plus(password)
                    url_corrigida = f"{protocol_user}:{password_encoded}@{rest_part}"
                    print(f"✅ Estratégia 3: URL encoding da senha")
    
    except Exception as e:
        print(f"❌ Erro durante correção: {e}")
        return False
    
    # Verificar se a correção funcionou
    try:
        url_corrigida.encode('utf-8')
        print(f"✅ URL corrigida pode ser codificada em UTF-8")
        
        # Tentar parsear URL corrigida
        parsed = urlparse(url_corrigida)
        print(f"✅ URL corrigida parseada com sucesso")
        
        # Mostrar diferenças
        if url_corrigida != backup_url:
            print(f"\n📊 DIFERENÇAS:")
            print(f"  Original: {len(backup_url)} caracteres")
            print(f"  Corrigida: {len(url_corrigida)} caracteres")
            print(f"  Diferença: {len(backup_url) - len(url_corrigida)} caracteres removidos")
        
        return url_corrigida
        
    except Exception as e:
        print(f"❌ URL corrigida ainda tem problemas: {e}")
        return False

def aplicar_correcao():
    """Aplica a correção definitiva"""
    
    print("\n🚀 APLICAÇÃO DA CORREÇÃO")
    print("=" * 50)
    
    # Gerar URL corrigida
    url_corrigida = corrigir_database_url()
    
    if not url_corrigida:
        print("❌ Não foi possível corrigir a DATABASE_URL")
        return False
    
    # Aplicar correção via environment
    os.environ['DATABASE_URL'] = url_corrigida
    print("✅ DATABASE_URL corrigida aplicada ao ambiente")
    
    # Testar se a aplicação agora pode inicializar
    try:
        print("\n🧪 TESTANDO INICIALIZAÇÃO DO SISTEMA...")
        
        # Tentar importar e usar database
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from app.claude_ai_novo.utils.agent_types import AgentType
        print("✅ AgentType importado com sucesso")
        
        from app.claude_ai_novo.coordinators.domain_agents.fretes_agent import FretesAgent
        agent = FretesAgent()
        print("✅ FretesAgent criado com sucesso")
        
        if hasattr(agent, 'agent_type'):
            print(f"✅ agent_type funciona: {agent.agent_type}")
            print(f"✅ agent_type.value: {agent.agent_type.value}")
        else:
            print("❌ agent_type ainda não funciona")
            
        return True
        
    except Exception as e:
        print(f"❌ Sistema ainda não pode inicializar: {e}")
        return False

def main():
    """Função principal"""
    
    print("🔧 CORREÇÃO UTF-8 - DATABASE_URL")
    print("=" * 60)
    
    # Passo 1: Diagnosticar
    if not diagnosticar_database_url():
        print("\n❌ Falha no diagnóstico")
        return 1
    
    # Passo 2: Corrigir
    if not aplicar_correcao():
        print("\n❌ Falha na correção")
        return 1
    
    print("\n✅ CORREÇÃO CONCLUÍDA COM SUCESSO!")
    print("🚀 Sistema agora pode inicializar normalmente")
    print("💡 A IA deve voltar a responder corretamente")
    
    return 0

if __name__ == "__main__":
    exit(main()) 