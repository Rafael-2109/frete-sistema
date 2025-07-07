#!/usr/bin/env python3
"""
🔍 VERIFICAR SE KNOWLEDGE BASE ESTÁ IMPLEMENTADO NO RENDER
Script para verificar se as tabelas de aprendizado estão presentes no banco de dados
"""

import os
import sys
from datetime import datetime

# Adicionar o diretório raiz ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text
from config import Config

def verificar_knowledge_base():
    """Verifica se o banco de conhecimento está implementado"""
    print("\n" + "="*80)
    print("🔍 VERIFICANDO STATUS DO BANCO DE CONHECIMENTO")
    print("="*80 + "\n")
    
    app = create_app()
    
    # Detectar tipo de banco
    is_postgresql = 'postgresql' in Config.SQLALCHEMY_DATABASE_URI.lower()
    is_production = os.getenv('RENDER', 'false').lower() == 'true' or is_postgresql
    
    print(f"🗄️ Banco de dados: {'PostgreSQL (Produção)' if is_postgresql else 'SQLite (Local)'}")
    print(f"🌍 Ambiente: {'Produção (Render)' if is_production else 'Desenvolvimento'}")
    
    with app.app_context():
        try:
            # Tabelas que devem existir
            tabelas_esperadas = [
                'ai_knowledge_patterns',
                'ai_semantic_mappings',
                'ai_learning_history',
                'ai_grupos_empresariais',
                'ai_business_contexts',
                'ai_response_templates',
                'ai_learning_metrics'
            ]
            
            print("\n📊 VERIFICANDO TABELAS...")
            
            tabelas_existentes = []
            tabelas_nao_existentes = []
            
            for tabela in tabelas_esperadas:
                try:
                    # Tentar fazer SELECT na tabela
                    count = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar()
                    tabelas_existentes.append({
                        'nome': tabela,
                        'registros': count
                    })
                    print(f"   ✅ {tabela}: {count} registros")
                except Exception as e:
                    tabelas_nao_existentes.append({
                        'nome': tabela,
                        'erro': str(e)
                    })
                    print(f"   ❌ {tabela}: Não encontrada")
            
            # Verificar índices importantes
            print("\n📈 VERIFICANDO ÍNDICES...")
            
            indices_verificar = [
                'idx_patterns_type',
                'idx_semantic_termo',
                'idx_learning_created',
                'idx_grupos_nome'
            ]
            
            indices_existentes = 0
            
            for indice in indices_verificar:
                try:
                    if is_postgresql:
                        result = db.session.execute(text("""
                            SELECT COUNT(*) FROM pg_indexes 
                            WHERE indexname = :nome
                        """), {"nome": indice}).scalar()
                    else:
                        result = db.session.execute(text("""
                            SELECT COUNT(*) FROM sqlite_master 
                            WHERE type = 'index' AND name = :nome
                        """), {"nome": indice}).scalar()
                    
                    if result and result > 0:
                        indices_existentes += 1
                        print(f"   ✅ {indice}: OK")
                    else:
                        print(f"   ❌ {indice}: Não encontrado")
                except Exception as e:
                    print(f"   ⚠️ {indice}: Erro ao verificar")
            
            # Verificar dados específicos
            print("\n📝 VERIFICANDO DADOS INICIAIS...")
            
            if 'ai_grupos_empresariais' in [t['nome'] for t in tabelas_existentes]:
                try:
                    grupos = db.session.execute(text("""
                        SELECT nome_grupo, tipo_negocio, ativo 
                        FROM ai_grupos_empresariais 
                        ORDER BY nome_grupo
                    """)).fetchall()
                    
                    print(f"   📊 Grupos empresariais cadastrados: {len(grupos)}")
                    for grupo in grupos:
                        status = "✅ Ativo" if grupo[2] else "❌ Inativo"
                        print(f"      • {grupo[0]} ({grupo[1]}) - {status}")
                        
                except Exception as e:
                    print(f"   ⚠️ Erro ao verificar grupos: {e}")
            
            # Verificar sistema de aprendizado
            print("\n🧠 VERIFICANDO SISTEMA DE APRENDIZADO...")
            
            try:
                # Verificar se há padrões aprendidos
                if 'ai_knowledge_patterns' in [t['nome'] for t in tabelas_existentes]:
                    padroes = db.session.execute(text("""
                        SELECT pattern_type, COUNT(*) as total
                        FROM ai_knowledge_patterns
                        GROUP BY pattern_type
                    """)).fetchall()
                    
                    if padroes:
                        print(f"   📊 Padrões aprendidos:")
                        for padrao in padroes:
                            print(f"      • {padrao[0]}: {padrao[1]} padrões")
                    else:
                        print("   ℹ️ Nenhum padrão aprendido ainda")
                
                # Verificar histórico de aprendizado
                if 'ai_learning_history' in [t['nome'] for t in tabelas_existentes]:
                    historico = db.session.execute(text("""
                        SELECT COUNT(*) as total
                        FROM ai_learning_history
                        WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
                    """ if is_postgresql else """
                        SELECT COUNT(*) as total
                        FROM ai_learning_history
                        WHERE created_at >= datetime('now', '-7 days')
                    """)).scalar()
                    
                    print(f"   📊 Aprendizado dos últimos 7 dias: {historico} interações")
                    
            except Exception as e:
                print(f"   ⚠️ Erro ao verificar aprendizado: {e}")
            
            # Resumo final
            print("\n" + "="*80)
            print("📊 RESUMO DO STATUS")
            print("="*80)
            
            total_tabelas = len(tabelas_esperadas)
            tabelas_ok = len(tabelas_existentes)
            
            print(f"🗄️ Tabelas: {tabelas_ok}/{total_tabelas} ({(tabelas_ok/total_tabelas)*100:.1f}%)")
            print(f"📈 Índices: {indices_existentes}/{len(indices_verificar)} ({(indices_existentes/len(indices_verificar))*100:.1f}%)")
            
            if tabelas_ok == total_tabelas:
                print("✅ STATUS: COMPLETAMENTE IMPLEMENTADO!")
                print("🎉 O sistema de aprendizado está pronto para uso!")
                
                # Mostrar como usar
                print("\n💡 COMO USAR:")
                print("1. Configure ANTHROPIC_API_KEY nas variáveis de ambiente")
                print("2. O sistema aprende automaticamente com as interações")
                print("3. Monitore os logs para acompanhar o aprendizado")
                
            elif tabelas_ok > 0:
                print("⚠️ STATUS: PARCIALMENTE IMPLEMENTADO")
                print(f"🔧 Faltam {total_tabelas - tabelas_ok} tabelas:")
                for tabela in tabelas_nao_existentes:
                    print(f"   • {tabela['nome']}")
                
                print("\n🚀 PARA COMPLETAR:")
                print("1. Execute: python aplicar_knowledge_base.py")
                print("2. Ou se estiver no Render: python aplicar_tabelas_ai_render.py")
                
            else:
                print("❌ STATUS: NÃO IMPLEMENTADO")
                print("🚀 PARA IMPLEMENTAR:")
                print("1. Execute: python aplicar_knowledge_base.py")
                print("2. Ou se estiver no Render: python aplicar_tabelas_ai_render.py")
            
            print("\n📍 ARQUIVOS RELACIONADOS:")
            print("   • knowledge_base.sql: Definição das tabelas")
            print("   • aplicar_knowledge_base.py: Script para aplicar localmente")
            print("   • aplicar_tabelas_ai_render.py: Script para aplicar no Render")
            
            return tabelas_ok == total_tabelas
            
        except Exception as e:
            print(f"\n❌ ERRO GERAL: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    print(f"🕐 Início: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    implementado = verificar_knowledge_base()
    
    print(f"\n🕐 Fim: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    
    if implementado:
        print("\n🎯 TUDO PRONTO! O sistema de aprendizado está funcionando.")
    else:
        print("\n🔧 AÇÃO NECESSÁRIA: Execute os scripts de aplicação.")
    
    print("\n" + "="*80) 