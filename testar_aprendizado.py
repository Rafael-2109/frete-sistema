#!/usr/bin/env python3
"""
🧪 TESTE RÁPIDO DO SISTEMA DE APRENDIZADO
Verifica se está tudo funcionando
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text

def testar_aprendizado():
    """Testa se o sistema de aprendizado está funcionando"""
    app = create_app()
    
    with app.app_context():
        print("\n🧪 TESTANDO SISTEMA DE APRENDIZADO")
        print("=" * 50)
        
        try:
            # 1. Verificar se as tabelas existem
            tabelas = [
                'ai_knowledge_patterns',
                'ai_semantic_mappings', 
                'ai_grupos_empresariais',
                'ai_learning_history'
            ]
            
            print("\n📊 Verificando tabelas:")
            todas_ok = True
            
            for tabela in tabelas:
                try:
                    count = db.session.execute(
                        text(f"SELECT COUNT(*) FROM {tabela}")
                    ).scalar()
                    print(f"  ✅ {tabela}: {count} registros")
                except Exception as e:
                    print(f"  ❌ {tabela}: NÃO EXISTE")
                    todas_ok = False
            
            if todas_ok:
                print("\n✅ SISTEMA DE APRENDIZADO ESTÁ ATIVO!")
                print("\n🎯 Próximos passos:")
                print("1. Use o Claude AI normalmente")
                print("2. O sistema aprenderá automaticamente")
                print("3. Corrija quando errar para melhorar")
                
                # 2. Simular um aprendizado
                print("\n🧠 Testando aprendizado...")
                from app.claude_ai.lifelong_learning import get_lifelong_learning
                ll = get_lifelong_learning()
                
                # Simular uma interação
                resultado = ll.aprender_com_interacao(
                    consulta="Teste de aprendizado",
                    interpretacao={"teste": True},
                    resposta="Teste realizado com sucesso"
                )
                
                print("✅ Aprendizado funcionando!")
                print(f"   Padrões detectados: {len(resultado.get('padroes_detectados', []))}")
                
            else:
                print("\n⚠️  TABELAS AINDA NÃO CRIADAS")
                print("\n💡 Soluções:")
                print("1. Aguarde o deploy terminar no Render")
                print("2. Ou execute: python aplicar_tabelas_ai_render.py")
                
        except Exception as e:
            print(f"\n❌ Erro: {e}")
            print("\n💡 Possível solução:")
            print("1. Verifique se o deploy terminou")
            print("2. Execute no Render: python aplicar_tabelas_ai_render.py")

if __name__ == "__main__":
    testar_aprendizado() 