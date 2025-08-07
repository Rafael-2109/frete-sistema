#!/usr/bin/env python3
"""
Script Simplificado para Render Shell
Execute diretamente no Render Shell
"""

print("=" * 60)
print("🚀 CRIANDO SISTEMA HÍBRIDO DE ESTOQUE NO RENDER")
print("=" * 60)

try:
    # Importar o necessário
    from app import create_app, db
    from sqlalchemy import text
    
    app = create_app()
    
    with app.app_context():
        print("\n📊 Criando tabelas...")
        
        # Criar tabela estoque_atual
        with db.engine.connect() as conn:
            # Criar estoque_atual
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS estoque_atual (
                    cod_produto VARCHAR(50) PRIMARY KEY,
                    nome_produto VARCHAR(200),
                    estoque NUMERIC(15,3) NOT NULL DEFAULT 0,
                    ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    versao INTEGER DEFAULT 1
                )
            """))
            conn.commit()
            print("✅ Tabela estoque_atual criada")
            
            # Criar estoque_projecao_cache
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS estoque_projecao_cache (
                    cod_produto VARCHAR(50) PRIMARY KEY,
                    projecao_json JSON,
                    menor_estoque_7d NUMERIC(15,3),
                    status_ruptura VARCHAR(20),
                    data_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    tempo_calculo_ms INTEGER,
                    versao INTEGER DEFAULT 1
                )
            """))
            conn.commit()
            print("✅ Tabela estoque_projecao_cache criada")
            
            # Criar índices
            indices = [
                "CREATE INDEX IF NOT EXISTS idx_estoque_atual_produto ON estoque_atual(cod_produto)",
                "CREATE INDEX IF NOT EXISTS idx_estoque_atual_atualizacao ON estoque_atual(ultima_atualizacao)",
                "CREATE INDEX IF NOT EXISTS idx_projecao_cache_produto ON estoque_projecao_cache(cod_produto)",
                "CREATE INDEX IF NOT EXISTS idx_projecao_cache_ruptura ON estoque_projecao_cache(status_ruptura)",
                "CREATE INDEX IF NOT EXISTS idx_projecao_cache_menor_estoque ON estoque_projecao_cache(menor_estoque_7d)",
                "CREATE INDEX IF NOT EXISTS idx_projecao_cache_calculo ON estoque_projecao_cache(data_calculo)"
            ]
            
            print("\n🔍 Criando índices...")
            for idx in indices:
                try:
                    conn.execute(text(idx))
                    conn.commit()
                    print(f"✅ Índice criado: {idx.split('idx_')[1].split(' ')[0]}")
                except Exception as e:
                    if "already exists" not in str(e).lower():
                        print(f"⚠️ Erro no índice: {e}")
            
            # Verificar tabelas criadas
            print("\n🔍 Verificando estrutura criada...")
            
            # Verificar estoque_atual
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'estoque_atual'
                ORDER BY ordinal_position
            """))
            print("\n📊 Estrutura estoque_atual:")
            for row in result:
                print(f"  - {row[0]}: {row[1]}")
            
            # Verificar estoque_projecao_cache
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'estoque_projecao_cache'
                ORDER BY ordinal_position
            """))
            print("\n📊 Estrutura estoque_projecao_cache:")
            for row in result:
                print(f"  - {row[0]}: {row[1]}")
            
            # Contar registros (opcional)
            result = conn.execute(text("SELECT COUNT(*) FROM estoque_atual"))
            count_atual = result.scalar()
            
            result = conn.execute(text("SELECT COUNT(*) FROM estoque_projecao_cache"))
            count_cache = result.scalar()
            
            print(f"\n📈 Status:")
            print(f"  - estoque_atual: {count_atual} registros")
            print(f"  - estoque_projecao_cache: {count_cache} registros")
        
        print("\n" + "=" * 60)
        print("✅ SISTEMA HÍBRIDO CRIADO COM SUCESSO!")
        print("=" * 60)
        print("\n🎯 Próximos passos:")
        print("1. Reinicie o serviço no Render Dashboard")
        print("2. Verifique: /estoque/api/hibrido/saude")
        print("3. Monitor logs para confirmar ausência do erro PG 1082")
        print("=" * 60)
        
except Exception as e:
    print(f"\n❌ ERRO: {e}")
    print("\nTente executar os comandos SQL diretamente:")
    print("-" * 60)
    print("""
-- Copie e execute no PostgreSQL:

CREATE TABLE IF NOT EXISTS estoque_atual (
    cod_produto VARCHAR(50) PRIMARY KEY,
    nome_produto VARCHAR(200),
    estoque NUMERIC(15,3) NOT NULL DEFAULT 0,
    ultima_atualizacao TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    versao INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS estoque_projecao_cache (
    cod_produto VARCHAR(50) PRIMARY KEY,
    projecao_json JSON,
    menor_estoque_7d NUMERIC(15,3),
    status_ruptura VARCHAR(20),
    data_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    tempo_calculo_ms INTEGER,
    versao INTEGER DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_estoque_atual_produto ON estoque_atual(cod_produto);
CREATE INDEX IF NOT EXISTS idx_estoque_atual_atualizacao ON estoque_atual(ultima_atualizacao);
CREATE INDEX IF NOT EXISTS idx_projecao_cache_produto ON estoque_projecao_cache(cod_produto);
CREATE INDEX IF NOT EXISTS idx_projecao_cache_ruptura ON estoque_projecao_cache(status_ruptura);
CREATE INDEX IF NOT EXISTS idx_projecao_cache_menor_estoque ON estoque_projecao_cache(menor_estoque_7d);
CREATE INDEX IF NOT EXISTS idx_projecao_cache_calculo ON estoque_projecao_cache(data_calculo);
    """)
    print("-" * 60)