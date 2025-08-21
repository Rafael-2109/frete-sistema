#!/usr/bin/env python3
"""
Script para testar se os botões do portal estão funcionando
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.carteira.routes.separacoes_api import obter_separacoes_completas
from app.separacao.models import Separacao
import json

app = create_app()

def testar_api_separacoes():
    """Testa se a API está retornando o campo protocolo_portal"""
    with app.app_context():
        # Buscar uma separação qualquer
        separacao = db.session.query(Separacao).first()
        
        if not separacao:
            print("❌ Nenhuma separação encontrada no banco")
            return
        
        print(f"📦 Testando com pedido: {separacao.num_pedido}")
        print(f"📦 Lote de separação: {separacao.separacao_lote_id}")
        
        # Simular requisição para a API
        with app.test_request_context():
            try:
                # Importar e executar a função diretamente
                from flask import g
                from app.auth.models import Usuario
                
                # Simular usuário logado
                g.user = db.session.query(Usuario).first()
                
                # Chamar a função da API
                response = obter_separacoes_completas(separacao.num_pedido)
                
                # Converter resposta para dict
                if hasattr(response, 'get_json'):
                    data = response.get_json()
                else:
                    data = response[0].get_json()
                
                print("\n✅ Resposta da API recebida!")
                
                # Verificar se tem separações
                if data.get('success') and data.get('separacoes'):
                    for sep in data['separacoes']:
                        print(f"\n📋 Separação: {sep['separacao_lote_id']}")
                        print(f"   Status: {sep.get('status', 'N/A')}")
                        print(f"   Protocolo Portal: {sep.get('protocolo_portal', 'NÃO EXISTE NO RETORNO')}")
                        
                        # Verificar se o campo existe
                        if 'protocolo_portal' in sep:
                            print("   ✅ Campo protocolo_portal EXISTE no retorno da API")
                        else:
                            print("   ❌ Campo protocolo_portal NÃO EXISTE no retorno da API")
                else:
                    print("❌ Nenhuma separação retornada pela API")
                    
            except Exception as e:
                print(f"❌ Erro ao testar API: {e}")
                import traceback
                traceback.print_exc()

def verificar_tabelas_portal():
    """Verifica se as tabelas do portal existem"""
    with app.app_context():
        try:
            # Verificar se a tabela existe
            result = db.session.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'portal_integracoes'
                );
            """)
            exists = result.scalar()
            
            if exists:
                print("✅ Tabela portal_integracoes EXISTE no banco")
                
                # Contar registros
                count = db.session.execute("SELECT COUNT(*) FROM portal_integracoes").scalar()
                print(f"   Total de registros: {count}")
            else:
                print("❌ Tabela portal_integracoes NÃO EXISTE - Execute o script SQL!")
                print("   Comando: psql $DATABASE_URL < app/portal/sql/001_criar_tabelas_portal.sql")
                
        except Exception as e:
            print(f"❌ Erro ao verificar tabelas: {e}")

def verificar_import_portal():
    """Verifica se o módulo portal pode ser importado"""
    try:
        from app.portal.models import PortalIntegracao
        print("✅ Módulo portal.models importado com sucesso")
        print(f"   Classe PortalIntegracao disponível: {PortalIntegracao.__name__}")
    except ImportError as e:
        print(f"❌ Erro ao importar módulo portal: {e}")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("🔍 TESTE DE INTEGRAÇÃO DO PORTAL")
    print("=" * 60)
    
    print("\n1️⃣ Verificando import do módulo portal...")
    verificar_import_portal()
    
    print("\n2️⃣ Verificando tabelas do portal no banco...")
    verificar_tabelas_portal()
    
    print("\n3️⃣ Testando API de separações...")
    testar_api_separacoes()
    
    print("\n" + "=" * 60)
    print("📝 RESUMO:")
    print("Se os botões não aparecem, verifique:")
    print("1. Se o campo protocolo_portal está no retorno da API")
    print("2. Se as tabelas foram criadas no banco")
    print("3. Se o servidor foi reiniciado após as mudanças")
    print("4. Se o cache do navegador foi limpo (Ctrl+F5)")
    print("=" * 60)