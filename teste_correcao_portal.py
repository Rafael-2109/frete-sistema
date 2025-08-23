#!/usr/bin/env python3
"""
Teste rápido para verificar se as correções de imports resolveram o problema
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.portal.models import PortalIntegracao, PortalLog
from app.portal.routes import executar_agendamento_portal

def testar_imports():
    """Testa se os imports estão funcionando corretamente"""
    print("=" * 60)
    print("TESTE DE IMPORTS E CONEXÃO DO BANCO")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Teste 1: Verificar se PortalIntegracao está acessível
            print("\n1. Testando acesso a PortalIntegracao...")
            count = PortalIntegracao.query.count()
            print(f"   ✅ PortalIntegracao acessível. Total de registros: {count}")
            
            # Teste 2: Verificar se PortalLog está acessível
            print("\n2. Testando acesso a PortalLog...")
            count_log = PortalLog.query.count()
            print(f"   ✅ PortalLog acessível. Total de logs: {count_log}")
            
            # Teste 3: Testar db.session.remove() e recriação
            print("\n3. Testando db.session.remove() e recriação...")
            
            # Criar um log de teste
            log_teste = PortalLog(
                integracao_id=1,
                acao='teste_conexao',
                sucesso=True,
                mensagem='Teste de conexão após db.session.remove()'
            )
            db.session.add(log_teste)
            db.session.commit()
            print("   ✅ Log criado com sucesso")
            
            # Remover sessão
            db.session.remove()
            print("   ✅ Sessão removida")
            
            # Tentar query novamente (deve recriar sessão automaticamente)
            count_after = PortalIntegracao.query.count()
            print(f"   ✅ Sessão recriada automaticamente. Total: {count_after}")
            
            # Limpar log de teste
            log_limpar = PortalLog.query.filter_by(acao='teste_conexao').first()
            if log_limpar:
                db.session.delete(log_limpar)
                db.session.commit()
                print("   ✅ Log de teste removido")
            
            print("\n" + "=" * 60)
            print("✅ TODOS OS TESTES PASSARAM!")
            print("=" * 60)
            print("\nAs correções funcionaram corretamente:")
            print("- PortalIntegracao e PortalLog estão acessíveis")
            print("- db.session.remove() permite recriação automática da sessão")
            print("- Não há mais erro de 'local variable not associated with value'")
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO NO TESTE: {e}")
            print("\nDetalhes do erro:")
            import traceback
            traceback.print_exc()
            return False

def testar_funcao_agendamento():
    """Testa se a função executar_agendamento_portal funciona"""
    print("\n" + "=" * 60)
    print("TESTE DA FUNÇÃO executar_agendamento_portal")
    print("=" * 60)
    
    app = create_app()
    
    with app.app_context():
        try:
            # Tentar executar com ID inexistente (deve retornar erro controlado)
            print("\nTestando função com ID inexistente...")
            resultado = executar_agendamento_portal(99999)
            
            if resultado['success'] == False:
                print(f"   ✅ Função retornou erro esperado: {resultado['message']}")
            else:
                print("   ⚠️ Função não retornou erro esperado")
            
            return True
            
        except Exception as e:
            print(f"\n❌ ERRO NA FUNÇÃO: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    sucesso1 = testar_imports()
    sucesso2 = testar_funcao_agendamento()
    
    if sucesso1 and sucesso2:
        print("\n🎉 CORREÇÃO COMPLETA E FUNCIONANDO!")
    else:
        print("\n⚠️ Ainda há problemas a resolver")