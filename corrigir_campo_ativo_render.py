#!/usr/bin/env python3
"""
Script para corrigir o campo 'ativo' na tabela ai_grupos_empresariais
Execute no shell do Render: python corrigir_campo_ativo_render.py
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text

def corrigir_campo_ativo():
    """Corrige o tipo do campo ativo"""
    app = create_app()
    
    with app.app_context():
        print("\n🔧 CORRIGINDO TABELAS DE APRENDIZADO...")
        
        # 1. Fazer rollback de qualquer transação pendente
        try:
            db.session.rollback()
        except:
            pass
            
        # 2. Verificar se a tabela existe
        try:
            existe = db.session.execute(
                text("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = 'ai_grupos_empresariais'
                    )
                """)
            ).scalar()
            
            if not existe:
                print("❌ Tabela ai_grupos_empresariais não existe!")
                criar_tabelas_completas()
                return
                
        except Exception as e:
            print(f"❌ Erro ao verificar tabela: {e}")
            db.session.rollback()
        
        # 3. Verificar estrutura atual
        try:
            # Verificar colunas
            colunas = db.session.execute(
                text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = 'ai_grupos_empresariais'
                    ORDER BY ordinal_position
                """)
            ).fetchall()
            
            print("\n📊 Estrutura atual da tabela:")
            tem_arrays = False
            for col in colunas:
                print(f"  - {col.column_name}: {col.data_type}")
                if col.data_type == 'ARRAY':
                    tem_arrays = True
            
            # Se não tem arrays ou tem problemas, recriar
            if not tem_arrays or len(colunas) < 5:
                print("\n⚠️ Estrutura incompleta, recriando tabela...")
                db.session.execute(text("DROP TABLE IF EXISTS ai_grupos_empresariais CASCADE"))
                db.session.commit()
                criar_tabelas_completas()
                return
                
        except Exception as e:
            print(f"⚠️ Erro ao verificar estrutura: {e}")
            db.session.rollback()
            criar_tabelas_completas()
            return
        
        print("\n✅ Tabela já existe com estrutura correta!")
        verificar_resultado()

def criar_tabelas_completas():
    """Cria todas as tabelas de aprendizado com estrutura correta"""
    try:
        print("\n📦 CRIANDO TABELAS DE APRENDIZADO...")
        
        # Rollback de qualquer transação pendente
        try:
            db.session.rollback()
        except:
            pass
        
        # 1. ai_grupos_empresariais - COM arrays PostgreSQL
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_grupos_empresariais (
                id SERIAL PRIMARY KEY,
                nome_grupo VARCHAR(200) NOT NULL UNIQUE,
                tipo_negocio VARCHAR(100),
                cnpj_prefixos TEXT[],
                palavras_chave TEXT[],
                filtro_sql TEXT NOT NULL,
                regras_deteccao JSONB,
                estatisticas JSONB,
                ativo BOOLEAN DEFAULT TRUE,
                aprendido_automaticamente BOOLEAN DEFAULT FALSE,
                confirmado_por VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.session.commit()
        print("✅ Tabela ai_grupos_empresariais criada com arrays")
        
        # 2. ai_knowledge_patterns
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_knowledge_patterns (
                id SERIAL PRIMARY KEY,
                pattern_type VARCHAR(50) NOT NULL,
                pattern_text TEXT NOT NULL,
                interpretation JSONB NOT NULL,
                confidence FLOAT DEFAULT 0.5,
                usage_count INTEGER DEFAULT 1,
                success_rate FLOAT DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by VARCHAR(100),
                UNIQUE(pattern_type, pattern_text)
            )
        """))
        db.session.commit()
        print("✅ Tabela ai_knowledge_patterns criada")
        
        # 3. ai_semantic_mappings
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_semantic_mappings (
                id SERIAL PRIMARY KEY,
                termo_usuario TEXT NOT NULL,
                campo_sistema VARCHAR(100) NOT NULL,
                modelo VARCHAR(50) NOT NULL,
                contexto TEXT,
                frequencia INTEGER DEFAULT 1,
                ultima_uso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                validado BOOLEAN DEFAULT FALSE,
                validado_por VARCHAR(100),
                validado_em TIMESTAMP,
                UNIQUE(termo_usuario, campo_sistema, modelo)
            )
        """))
        db.session.commit()
        print("✅ Tabela ai_semantic_mappings criada")
        
        # 4. ai_learning_history
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_learning_history (
                id SERIAL PRIMARY KEY,
                consulta_original TEXT NOT NULL,
                interpretacao_inicial JSONB NOT NULL,
                resposta_inicial TEXT,
                feedback_usuario TEXT,
                interpretacao_corrigida JSONB,
                resposta_corrigida TEXT,
                tipo_correcao VARCHAR(50),
                aprendizado_extraido JSONB,
                usuario_id INTEGER,
                sessao_id VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.session.commit()
        print("✅ Tabela ai_learning_history criada")
        
        # 5. ai_learning_metrics
        db.session.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_learning_metrics (
                id SERIAL PRIMARY KEY,
                metrica_tipo VARCHAR(50) NOT NULL,
                metrica_valor FLOAT NOT NULL,
                contexto JSONB,
                periodo_inicio TIMESTAMP NOT NULL,
                periodo_fim TIMESTAMP NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db.session.commit()
        print("✅ Tabela ai_learning_metrics criada")
        
        # 6. Criar índices
        criar_indices()
        
        # 7. Inserir dados iniciais
        inserir_dados_iniciais()
        
    except Exception as e:
        print(f"❌ Erro ao criar tabelas: {e}")
        db.session.rollback()

def criar_indices():
    """Cria índices para melhor performance"""
    try:
        print("\n🔍 Criando índices...")
        
        indices = [
            "CREATE INDEX IF NOT EXISTS idx_grupos_ativo ON ai_grupos_empresariais(ativo) WHERE ativo = TRUE",
            "CREATE INDEX IF NOT EXISTS idx_grupos_cnpj ON ai_grupos_empresariais USING GIN(cnpj_prefixos)",
            "CREATE INDEX IF NOT EXISTS idx_grupos_palavras ON ai_grupos_empresariais USING GIN(palavras_chave)",
            "CREATE INDEX IF NOT EXISTS idx_patterns_type_text ON ai_knowledge_patterns(pattern_type, pattern_text)",
            "CREATE INDEX IF NOT EXISTS idx_semantic_termo ON ai_semantic_mappings(termo_usuario)",
            "CREATE INDEX IF NOT EXISTS idx_learning_created ON ai_learning_history(created_at DESC)"
        ]
        
        for idx in indices:
            try:
                db.session.execute(text(idx))
                print(f"  ✅ Índice criado")
            except Exception as e:
                print(f"  ⚠️ Índice já existe ou erro: {e}")
        
        db.session.commit()
        
    except Exception as e:
        print(f"❌ Erro ao criar índices: {e}")
        db.session.rollback()

def inserir_dados_iniciais():
    """Insere dados iniciais nas tabelas"""
    try:
        print("\n📝 INSERINDO DADOS INICIAIS...")
        
        # 1. Grupos empresariais com arrays
        grupos = [
            ('Assai', 'Atacarejo', ['06.057.223/'], ['assai', 'assaí'], "cliente ILIKE '%assai%'"),
            ('Atacadão', 'Atacarejo', ['75.315.333/', '00.063.960/', '93.209.765/'], ['atacadao', 'atacadão'], "cliente ILIKE '%atacadao%' OR cliente ILIKE '%atacadao%'"),
            ('Carrefour', 'Varejo', ['45.543.915/'], ['carrefour'], "cliente ILIKE '%carrefour%'"),
            ('Tenda', 'Atacado', ['01.157.555/'], ['tenda'], "cliente ILIKE '%tenda%'"),
            ('Fort', 'Atacado', [], ['fort'], "cliente ILIKE '%fort%'"),
            ('Mateus', 'Varejo', [], ['mateus'], "cliente ILIKE '%mateus%'"),
            ('Coco Bambu', 'Restaurante', [], ['coco bambu', 'cocobambu'], "cliente ILIKE '%coco%bambu%'"),
            ('Mercantil Rodrigues', 'Atacado', [], ['mercantil rodrigues', 'rodrigues'], "cliente ILIKE '%mercantil%rodrigues%'")
        ]
        
        for nome, tipo, cnpjs, palavras, filtro in grupos:
            try:
                db.session.execute(
                    text("""
                        INSERT INTO ai_grupos_empresariais 
                        (nome_grupo, tipo_negocio, cnpj_prefixos, palavras_chave, filtro_sql)
                        VALUES (:nome, :tipo, :cnpjs, :palavras, :filtro)
                        ON CONFLICT (nome_grupo) DO UPDATE SET
                            tipo_negocio = EXCLUDED.tipo_negocio,
                            cnpj_prefixos = EXCLUDED.cnpj_prefixos,
                            palavras_chave = EXCLUDED.palavras_chave,
                            filtro_sql = EXCLUDED.filtro_sql
                    """),
                    {'nome': nome, 'tipo': tipo, 'cnpjs': cnpjs, 'palavras': palavras, 'filtro': filtro}
                )
                print(f"  ✅ Grupo {nome} inserido")
            except Exception as e:
                print(f"  ❌ Erro ao inserir {nome}: {e}")
        
        db.session.commit()
        
        # 2. Padrões básicos
        padroes = [
            ('intencao', 'status', '{"acao": "verificar_status"}', 0.8),
            ('intencao', 'melhor', '{"acao": "status", "contexto": "melhoria"}', 0.7),
            ('intencao', 'entregas atrasadas', '{"acao": "listar", "filtro": "atrasadas", "dominio": "entregas"}', 0.9),
            ('periodo', 'hoje', '{"periodo_dias": 0, "tipo": "dia_atual"}', 0.9),
            ('periodo', 'ontem', '{"periodo_dias": 1, "tipo": "dia_anterior"}', 0.9),
            ('periodo', 'esta semana', '{"periodo_dias": 7, "tipo": "semana_atual"}', 0.8),
            ('periodo', 'este mês', '{"periodo_dias": 30, "tipo": "mes_atual"}', 0.8),
            ('dominio', 'entregas', '{"modelo": "EntregaMonitorada", "foco": "monitoramento"}', 0.8),
            ('dominio', 'pedidos', '{"modelo": "Pedido", "foco": "vendas"}', 0.8),
            ('dominio', 'fretes', '{"modelo": "Frete", "foco": "financeiro"}', 0.8),
            ('dominio', 'embarques', '{"modelo": "Embarque", "foco": "operacional"}', 0.8)
        ]
        
        for tipo, texto, interp, conf in padroes:
            try:
                db.session.execute(
                    text("""
                        INSERT INTO ai_knowledge_patterns 
                        (pattern_type, pattern_text, interpretation, confidence, created_by)
                        VALUES (:tipo, :texto, CAST(:interp AS jsonb), :conf, 'sistema')
                        ON CONFLICT (pattern_type, pattern_text) DO UPDATE SET
                            interpretation = EXCLUDED.interpretation,
                            confidence = EXCLUDED.confidence
                    """),
                    {'tipo': tipo, 'texto': texto, 'interp': interp, 'conf': conf}
                )
                print(f"  ✅ Padrão '{texto}' inserido")
            except Exception as e:
                print(f"  ❌ Erro ao inserir padrão: {e}")
        
        db.session.commit()
        print("\n✅ Dados iniciais inseridos com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao inserir dados: {e}")
        db.session.rollback()

def verificar_resultado():
    """Verifica o resultado final"""
    print("\n🔍 VERIFICANDO RESULTADO...")
    
    try:
        # Verificar grupos
        count = db.session.execute(
            text("SELECT COUNT(*) FROM ai_grupos_empresariais WHERE ativo = TRUE")
        ).scalar()
        print(f"✅ {count} grupos empresariais ativos")
        
        # Verificar padrões
        count = db.session.execute(
            text("SELECT COUNT(*) FROM ai_knowledge_patterns")
        ).scalar()
        print(f"✅ {count} padrões de aprendizado")
        
        # Testar queries com arrays
        print("\n🧪 Testando queries com arrays...")
        try:
            # Query 1: Buscar grupos com palavras-chave
            grupos = db.session.execute(
                text("""
                    SELECT nome_grupo, tipo_negocio, 
                           array_to_string(palavras_chave, ', ') as palavras,
                           array_to_string(cnpj_prefixos, ', ') as cnpjs
                    FROM ai_grupos_empresariais 
                    WHERE ativo = TRUE
                    AND cardinality(palavras_chave) > 0
                    LIMIT 5
                """)
            ).fetchall()
            
            print("✅ Query com arrays funcionando!")
            for grupo in grupos:
                print(f"  - {grupo.nome_grupo} ({grupo.tipo_negocio})")
                print(f"    Palavras: {grupo.palavras}")
                if grupo.cnpjs:
                    print(f"    CNPJs: {grupo.cnpjs}")
            
            # Query 2: Buscar por palavra específica
            print("\n🔍 Testando busca por palavra-chave...")
            resultado = db.session.execute(
                text("""
                    SELECT nome_grupo 
                    FROM ai_grupos_empresariais 
                    WHERE ativo = TRUE
                    AND 'assai' = ANY(palavras_chave)
                """)
            ).fetchone()
            
            if resultado:
                print(f"✅ Encontrado grupo: {resultado.nome_grupo}")
            
        except Exception as e:
            print(f"❌ Erro na query com arrays: {e}")
            
    except Exception as e:
        print(f"❌ Erro ao verificar: {e}")

if __name__ == "__main__":
    corrigir_campo_ativo()
    # verificar_resultado() já é chamado dentro de corrigir_campo_ativo() quando apropriado 