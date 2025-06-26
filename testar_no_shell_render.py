#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🚀 TESTE DIRETO NO SHELL DO RENDER
Execute este script no console do Render para testar funcionalidades
"""

import os
import sys
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configurar ambiente
os.environ['FLASK_APP'] = 'run.py'

# Importar aplicação
from app import create_app, db
from app.auth.models import Usuario
from app.claude_ai.intelligent_query_analyzer import get_intelligent_analyzer
from app.claude_ai.multi_agent_system import get_multi_agent_system
from app.claude_ai.human_in_loop_learning import HumanInLoopLearning
from app.utils.grupo_empresarial import GrupoEmpresarial
from sqlalchemy import text
import json

print("="*60)
print("🚀 TESTE DIRETO NO SHELL DO RENDER")
print("="*60)

def testar_sistema():
    """Testa e corrige o sistema de aprendizado"""
    app = create_app()
    
    with app.app_context():
        print("\n🔍 VERIFICANDO TABELAS DE APRENDIZADO...")
        
        # 1. Verificar se as tabelas existem
        tabelas = [
            'ai_knowledge_patterns',
            'ai_semantic_mappings', 
            'ai_learning_history',
            'ai_grupos_empresariais',
            'ai_business_contexts',
            'ai_response_templates',
            'ai_learning_metrics'
        ]
        
        for tabela in tabelas:
            try:
                result = db.session.execute(
                    text(f"SELECT COUNT(*) FROM {tabela}")
                ).scalar()
                print(f"✅ {tabela}: {result} registros")
            except Exception as e:
                print(f"❌ {tabela}: ERRO - {str(e)[:50]}...")
                db.session.rollback()
        
        # 2. Corrigir grupos empresariais
        print("\n🏢 VERIFICANDO GRUPOS EMPRESARIAIS...")
        try:
            # Verificar quantos grupos existem
            count = db.session.execute(
                text("SELECT COUNT(*) FROM ai_grupos_empresariais")
            ).scalar()
            
            print(f"Total de grupos: {count}")
            
            if count == 0:
                print("Inserindo grupos iniciais...")
                
                # Inserir grupos básicos
                grupos = [
                    ('Assai', 'Atacarejo', ['06.057.223/'], ['assai', 'assaí']),
                    ('Atacadão', 'Atacarejo', ['75.315.333/', '00.063.960/'], ['atacadao', 'atacadão']),
                    ('Carrefour', 'Varejo', ['45.543.915/'], ['carrefour'])
                ]
                
                for nome, tipo, cnpjs, palavras in grupos:
                    try:
                        db.session.execute(
                            text("""
                                INSERT INTO ai_grupos_empresariais 
                                (nome_grupo, tipo_negocio, cnpj_prefixos, palavras_chave, 
                                 filtro_sql, ativo)
                                VALUES (:nome, :tipo, :cnpjs, :palavras, :filtro, TRUE)
                                ON CONFLICT (nome_grupo) DO NOTHING
                            """),
                            {
                                'nome': nome,
                                'tipo': tipo,
                                'cnpjs': cnpjs,
                                'palavras': palavras,
                                'filtro': f"cliente ILIKE '%{nome.lower()}%'"
                            }
                        )
                        print(f"✅ Grupo {nome} inserido")
                    except Exception as e:
                        print(f"❌ Erro ao inserir {nome}: {e}")
                        db.session.rollback()
                
                db.session.commit()
                
            # Listar grupos ativos
            grupos = db.session.execute(
                text("""
                    SELECT nome_grupo, tipo_negocio, cnpj_prefixos, palavras_chave
                    FROM ai_grupos_empresariais
                    WHERE ativo IS TRUE
                """)
            ).fetchall()
            
            print("\nGrupos ativos:")
            for grupo in grupos:
                print(f"- {grupo.nome_grupo} ({grupo.tipo_negocio})")
                
        except Exception as e:
            print(f"❌ Erro ao verificar grupos: {e}")
            db.session.rollback()
        
        # 3. Adicionar padrões iniciais
        print("\n📚 VERIFICANDO PADRÕES DE APRENDIZADO...")
        try:
            count = db.session.execute(
                text("SELECT COUNT(*) FROM ai_knowledge_patterns")
            ).scalar()
            
            print(f"Total de padrões: {count}")
            
            if count < 5:
                print("Inserindo padrões básicos...")
                
                padroes = [
                    ('intencao', 'melhor', {'acao': 'status', 'contexto': 'melhoria'}),
                    ('periodo', 'hoje', {'periodo_dias': 0, 'tipo': 'dia_atual'}),
                    ('periodo', 'ontem', {'periodo_dias': 1, 'tipo': 'dia_anterior'}),
                    ('dominio', 'entregas', {'modelo': 'EntregaMonitorada', 'foco': 'monitoramento'}),
                    ('dominio', 'pedidos', {'modelo': 'Pedido', 'foco': 'vendas'})
                ]
                
                for tipo, texto, interp in padroes:
                    try:
                        db.session.execute(
                            text("""
                                INSERT INTO ai_knowledge_patterns 
                                (pattern_type, pattern_text, interpretation, 
                                 confidence, created_by)
                                VALUES (:tipo, :texto, :interp::jsonb, 0.7, 'sistema')
                                ON CONFLICT (pattern_type, pattern_text) DO NOTHING
                            """),
                            {
                                'tipo': tipo,
                                'texto': texto,
                                'interp': json.dumps(interp)
                            }
                        )
                        print(f"✅ Padrão '{texto}' inserido")
                    except Exception as e:
                        print(f"❌ Erro ao inserir padrão: {e}")
                        db.session.rollback()
                
                db.session.commit()
                
        except Exception as e:
            print(f"❌ Erro ao verificar padrões: {e}")
            db.session.rollback()
        
        # 4. Testar consulta problemática
        print("\n🧪 TESTANDO CONSULTA DE GRUPOS...")
        try:
            consulta = "Melhorou agora?"
            grupos = db.session.execute(
                text("""
                    SELECT nome_grupo, tipo_negocio, filtro_sql
                    FROM ai_grupos_empresariais
                    WHERE ativo IS TRUE
                    AND palavras_chave IS NOT NULL
                    AND array_length(palavras_chave, 1) > 0
                    AND EXISTS (
                        SELECT 1 FROM unnest(palavras_chave) AS palavra
                        WHERE LOWER(:consulta) LIKE '%' || LOWER(palavra) || '%'
                    )
                """),
                {"consulta": consulta}
            ).fetchall()
            
            print(f"✅ Query executada com sucesso! {len(grupos)} grupos encontrados")
            
        except Exception as e:
            print(f"❌ Erro na query: {e}")
            db.session.rollback()
        
        # 5. Verificar sistema de aprendizado
        print("\n🧠 TESTANDO SISTEMA DE APRENDIZADO...")
        try:
            from app.claude_ai.lifelong_learning import get_lifelong_learning
            
            ll = get_lifelong_learning()
            stats = ll.obter_estatisticas_aprendizado()
            
            print("Estatísticas do sistema:")
            for key, value in stats.items():
                print(f"  {key}: {value}")
                
        except Exception as e:
            print(f"❌ Erro ao testar aprendizado: {e}")
        
        print("\n✅ TESTE CONCLUÍDO!")

if __name__ == "__main__":
    testar_sistema()

print("\n🚀 Script finalizado!") 