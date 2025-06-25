#!/usr/bin/env python3
"""
🧠 CRIAR TABELAS DE APRENDIZADO VITALÍCIO
Script simplificado para criar as tabelas
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    print("🧠 Criando tabelas de aprendizado vitalício...")
    
    # Criar cada tabela individualmente
    tabelas = [
        """
        CREATE TABLE IF NOT EXISTS ai_knowledge_patterns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pattern_type VARCHAR(50) NOT NULL,
            pattern_text TEXT NOT NULL,
            interpretation TEXT NOT NULL,
            confidence FLOAT DEFAULT 0.5,
            usage_count INTEGER DEFAULT 1,
            success_rate FLOAT DEFAULT 0.5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(100),
            UNIQUE(pattern_type, pattern_text)
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS ai_semantic_mappings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            termo_usuario TEXT NOT NULL,
            campo_sistema VARCHAR(100) NOT NULL,
            modelo VARCHAR(50) NOT NULL,
            contexto TEXT,
            frequencia INTEGER DEFAULT 1,
            ultima_uso TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            validado INTEGER DEFAULT 0,
            validado_por VARCHAR(100),
            validado_em TIMESTAMP,
            UNIQUE(termo_usuario, campo_sistema, modelo)
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS ai_learning_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            consulta_original TEXT NOT NULL,
            interpretacao_inicial TEXT NOT NULL,
            resposta_inicial TEXT,
            feedback_usuario TEXT,
            interpretacao_corrigida TEXT,
            resposta_corrigida TEXT,
            tipo_correcao VARCHAR(50),
            aprendizado_extraido TEXT,
            usuario_id INTEGER,
            sessao_id VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS ai_grupos_empresariais (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_grupo VARCHAR(200) NOT NULL UNIQUE,
            tipo_negocio VARCHAR(100),
            cnpj_prefixos TEXT,
            palavras_chave TEXT,
            filtro_sql TEXT NOT NULL,
            regras_deteccao TEXT,
            estatisticas TEXT,
            ativo INTEGER DEFAULT 1,
            aprendido_automaticamente INTEGER DEFAULT 0,
            confirmado_por VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS ai_business_contexts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contexto_nome VARCHAR(100) NOT NULL UNIQUE,
            descricao TEXT,
            regras TEXT NOT NULL,
            exemplos TEXT,
            restricoes TEXT,
            prioridade INTEGER DEFAULT 50,
            ativo INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS ai_response_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tipo_consulta VARCHAR(100) NOT NULL,
            contexto VARCHAR(100),
            template_resposta TEXT NOT NULL,
            variaveis_necessarias TEXT,
            exemplo_uso TEXT,
            taxa_satisfacao FLOAT DEFAULT 0.5,
            uso_count INTEGER DEFAULT 0,
            ativo INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """,
        
        """
        CREATE TABLE IF NOT EXISTS ai_learning_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            metrica_tipo VARCHAR(50) NOT NULL,
            metrica_valor FLOAT NOT NULL,
            contexto TEXT,
            periodo_inicio TIMESTAMP NOT NULL,
            periodo_fim TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    ]
    
    # Executar cada CREATE TABLE
    for i, sql in enumerate(tabelas, 1):
        try:
            db.session.execute(text(sql))
            db.session.commit()
            print(f"✅ Tabela {i}/7 criada")
        except Exception as e:
            print(f"❌ Erro na tabela {i}: {e}")
            db.session.rollback()
    
    # Inserir grupos empresariais iniciais
    print("\n📝 Inserindo grupos empresariais...")
    
    grupos = [
        ('Assai', 'Atacarejo', '["06.057.223/"]', '["assai", "assaí"]', '%assai%'),
        ('Atacadão', 'Atacarejo', '["75.315.333/", "00.063.960/", "93.209.765/"]', '["atacadao", "atacadão"]', '%atacad%'),
        ('Carrefour', 'Varejo', '["45.543.915/"]', '["carrefour"]', '%carrefour%'),
        ('Tenda', 'Atacarejo', '["01.157.555/"]', '["tenda"]', '%tenda%'),
        ('Mateus', 'Varejo Regional', '["12.545.228/", "58.217.678/", "23.583.231/"]', '["mateus", "grupo mateus"]', '%mateus%'),
        ('Fort', 'Atacarejo', '["13.481.309/"]', '["fort", "fort atacadista"]', '%fort%'),
        ('Coco Bambu', 'Restaurante', '["09.335.736/"]', '["coco bambu", "cocobambu"]', '%coco%bambu%'),
        ('Mercantil Rodrigues', 'Atacarejo', '["83.373.845/"]', '["mercantil rodrigues", "mercantil"]', '%mercantil%rodrigues%')
    ]
    
    for nome, tipo, cnpjs, palavras, filtro in grupos:
        try:
            # Verificar se já existe
            existe = db.session.execute(
                text("SELECT COUNT(*) FROM ai_grupos_empresariais WHERE nome_grupo = :nome"),
                {"nome": nome}
            ).scalar()
            
            if existe == 0:
                db.session.execute(
                    text("""
                        INSERT INTO ai_grupos_empresariais 
                        (nome_grupo, tipo_negocio, cnpj_prefixos, palavras_chave, filtro_sql)
                        VALUES (:nome, :tipo, :cnpjs, :palavras, :filtro)
                    """),
                    {"nome": nome, "tipo": tipo, "cnpjs": cnpjs, "palavras": palavras, "filtro": filtro}
                )
                print(f"   ✅ {nome}")
        except Exception as e:
            print(f"   ❌ Erro ao inserir {nome}: {e}")
    
    db.session.commit()
    
    # Verificar resultado
    print("\n📊 Verificando tabelas criadas...")
    
    tabelas_verificar = [
        'ai_knowledge_patterns',
        'ai_semantic_mappings', 
        'ai_learning_history',
        'ai_grupos_empresariais',
        'ai_business_contexts',
        'ai_response_templates',
        'ai_learning_metrics'
    ]
    
    for tabela in tabelas_verificar:
        try:
            count = db.session.execute(text(f"SELECT COUNT(*) FROM {tabela}")).scalar()
            print(f"   ✅ {tabela}: {count} registros")
        except:
            print(f"   ❌ {tabela}: Não encontrada")
    
    print("\n✅ CONCLUÍDO!") 