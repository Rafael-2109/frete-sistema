import psycopg2

def criar_tabelas_ai():
    # Conexao PostgreSQL Render
    conn = psycopg2.connect(
        host='dpg-d13m38vfte5s738t6p50-a.oregon-postgres.render.com',
        port=5432,
        database='sistema_fretes',
        user='sistema_user',
        password='R80cswDpRJGsmpTdA73XxvV2xqEfzYm9'
    )
    
    cursor = conn.cursor()
    print("Conectado! Criando sistema avancado...")
    
    try:
        # 1. Tabela principal de sessoes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_advanced_sessions (
                session_id VARCHAR(50) PRIMARY KEY,
                user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb
            )
        """)
        print("1/6 ai_advanced_sessions OK")
        
        # 2. Tabela de feedback
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_feedback_history (
                feedback_id VARCHAR(50) PRIMARY KEY,
                session_id VARCHAR(50),
                user_id INTEGER,
                query_original TEXT NOT NULL,
                response_original TEXT NOT NULL,
                feedback_text TEXT NOT NULL,
                feedback_type VARCHAR(20) NOT NULL,
                severity VARCHAR(20) DEFAULT 'medium',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                processed BOOLEAN DEFAULT FALSE,
                applied BOOLEAN DEFAULT FALSE,
                context_jsonb JSONB DEFAULT '{}'::jsonb
            )
        """)
        print("2/6 ai_feedback_history OK")
        
        # 3. Tabela de padroes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_learning_patterns (
                pattern_id VARCHAR(50) PRIMARY KEY,
                pattern_type VARCHAR(50) NOT NULL,
                description TEXT NOT NULL,
                frequency INTEGER DEFAULT 1,
                confidence_score DECIMAL(3,2) DEFAULT 0.5,
                improvement_suggestion TEXT,
                examples_jsonb JSONB DEFAULT '[]'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT TRUE
            )
        """)
        print("3/6 ai_learning_patterns OK")
        
        # 4. Tabela de metricas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_performance_metrics (
                metric_id SERIAL PRIMARY KEY,
                metric_date DATE DEFAULT CURRENT_DATE,
                metric_type VARCHAR(50) NOT NULL,
                metric_value DECIMAL(10,4) NOT NULL,
                metadata_jsonb JSONB DEFAULT '{}'::jsonb,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("4/6 ai_performance_metrics OK")
        
        # 5. Tabela de embeddings
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_semantic_embeddings (
                embedding_id SERIAL PRIMARY KEY,
                content_hash VARCHAR(64) UNIQUE NOT NULL,
                content_text TEXT NOT NULL,
                content_type VARCHAR(50) NOT NULL,
                embedding_vector JSONB,
                model_version VARCHAR(20) DEFAULT 'v1.0',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("5/6 ai_semantic_embeddings OK")
        
        # 6. Tabela de configuracao
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS ai_system_config (
                config_key VARCHAR(100) PRIMARY KEY,
                config_value JSONB NOT NULL,
                description TEXT,
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("6/6 ai_system_config OK")
        
        # Inserir configuracoes
        cursor.execute("""
            INSERT INTO ai_system_config (config_key, config_value, description) VALUES
            ('multi_agent_enabled', 'true'::jsonb, 'Sistema multi-agente'),
            ('human_learning_enabled', 'true'::jsonb, 'Aprendizado humano'),
            ('semantic_loop_max_iterations', '3'::jsonb, 'Max iteracoes'),
            ('metacognitive_threshold', '0.7'::jsonb, 'Threshold metacognitiva'),
            ('auto_tagging_enabled', 'true'::jsonb, 'Auto-tagging'),
            ('advanced_analytics_retention_days', '90'::jsonb, 'Retencao analytics')
            ON CONFLICT (config_key) DO NOTHING
        """)
        print("Configuracoes inseridas")
        
        # Indices principais
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_sessions_metadata ON ai_advanced_sessions USING gin(metadata_jsonb)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_ai_sessions_user ON ai_advanced_sessions(user_id, created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_feedback_user ON ai_feedback_history(user_id, created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_patterns_type ON ai_learning_patterns(pattern_type, confidence_score)")
        print("Indices criados")
        
        # Commit
        conn.commit()
        
        # Verificar resultado
        cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'ai_%' AND table_schema = 'public' ORDER BY table_name")
        tabelas = [row[0] for row in cursor.fetchall()]
        
        cursor.execute("SELECT COUNT(*) FROM ai_system_config")
        configs = cursor.fetchone()[0]
        
        print(f"\nSUCESSO! {len(tabelas)} tabelas criadas:")
        for t in tabelas:
            print(f"  - {t}")
        print(f"{configs} configuracoes inseridas")
        print("Sistema avancado de IA configurado!")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"Erro: {e}")
        cursor.close()
        conn.close()
        return False

if __name__ == "__main__":
    criar_tabelas_ai() 