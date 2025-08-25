#!/usr/bin/env python3
"""
Verifica e cria/ajusta tabela grupo_empresarial
"""
from app import create_app, db
app = create_app()
from sqlalchemy import text

with app.app_context():
    try:
        # Verifica se tabela existe
        result = db.session.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'grupo_empresarial'
            ORDER BY ordinal_position
        """))
        
        columns = result.fetchall()
        
        if columns:
            print("📊 Tabela grupo_empresarial existe com as colunas:")
            for col in columns:
                print(f"  - {col[0]}: {col[1]}")
            
            # Verifica se tem a coluna prefixo_cnpj
            col_names = [col[0] for col in columns]
            
            if 'prefixo_cnpj' not in col_names:
                print("\n⚠️ Coluna prefixo_cnpj não existe. Adicionando...")
                
                # Adiciona coluna prefixo_cnpj
                db.session.execute(text("""
                    ALTER TABLE grupo_empresarial 
                    ADD COLUMN IF NOT EXISTS prefixo_cnpj VARCHAR(8)
                """))
                
                # Adiciona coluna descricao se não existir
                if 'descricao' not in col_names:
                    db.session.execute(text("""
                        ALTER TABLE grupo_empresarial 
                        ADD COLUMN IF NOT EXISTS descricao VARCHAR(255)
                    """))
                
                # Remove colunas antigas se existirem
                if 'info_grupo' in col_names:
                    db.session.execute(text("""
                        ALTER TABLE grupo_empresarial 
                        DROP COLUMN IF EXISTS info_grupo
                    """))
                
                if 'tipo_grupo' in col_names:
                    db.session.execute(text("""
                        ALTER TABLE grupo_empresarial 
                        DROP COLUMN IF EXISTS tipo_grupo
                    """))
                
                db.session.commit()
                print("✅ Tabela ajustada com sucesso!")
            else:
                print("✅ Tabela já está com a estrutura correta!")
        else:
            print("❌ Tabela não existe. Criando...")
            
            # Cria tabela
            db.session.execute(text("""
                CREATE TABLE grupo_empresarial (
                    id SERIAL PRIMARY KEY,
                    nome_grupo VARCHAR(100) NOT NULL,
                    prefixo_cnpj VARCHAR(8) NOT NULL,
                    descricao VARCHAR(255),
                    criado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    criado_por VARCHAR(100),
                    ativo BOOLEAN DEFAULT TRUE
                )
            """))
            
            # Cria índices
            db.session.execute(text("""
                CREATE UNIQUE INDEX IF NOT EXISTS uk_prefixo_cnpj 
                ON grupo_empresarial(prefixo_cnpj)
            """))
            
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_grupo_empresarial_nome 
                ON grupo_empresarial(nome_grupo)
            """))
            
            db.session.commit()
            print("✅ Tabela criada com sucesso!")
        
        # Insere dados de exemplo
        print("\n📦 Inserindo dados de exemplo...")
        
        grupos = [
            ('Atacadão', '75315333', 'Rede Atacadão'),
            ('Atacadão', '10776574', 'Rede Atacadão'),
            ('Carrefour', '45543915', 'Grupo Carrefour'),
            ('Pão de Açúcar', '06057223', 'Grupo Pão de Açúcar'),
        ]
        
        for nome, prefixo, desc in grupos:
            try:
                db.session.execute(text("""
                    INSERT INTO grupo_empresarial (nome_grupo, prefixo_cnpj, descricao, criado_por, ativo)
                    VALUES (:nome, :prefixo, :desc, 'Sistema', true)
                """), {'nome': nome, 'prefixo': prefixo, 'desc': desc})
                print(f"  ✅ {nome} - {prefixo}")
            except Exception as e:
                if 'duplicate' in str(e).lower():
                    print(f"  ⚠️ {nome} - {prefixo} (já existe)")
                else:
                    print(f"  ❌ {nome} - {prefixo}: {e}")
        
        db.session.commit()
        
        # Verifica dados inseridos
        result = db.session.execute(text("""
            SELECT nome_grupo, COUNT(*) as qtd 
            FROM grupo_empresarial 
            WHERE ativo = true
            GROUP BY nome_grupo 
            ORDER BY nome_grupo
        """))
        
        print("\n📊 Grupos cadastrados:")
        for row in result:
            print(f"  - {row[0]}: {row[1]} prefixo(s)")
            
    except Exception as e:
        print(f"❌ Erro: {e}")
        db.session.rollback()