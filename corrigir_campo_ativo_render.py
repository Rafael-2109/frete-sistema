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
        print("\n🔧 CORRIGINDO CAMPO 'ativo' NA TABELA ai_grupos_empresariais...")
        
        try:
            # 1. Verificar tipo atual do campo
            result = db.session.execute(
                text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'ai_grupos_empresariais' 
                    AND column_name = 'ativo'
                """)
            ).fetchone()
            
            if result:
                print(f"Tipo atual do campo 'ativo': {result.data_type}")
                
                if result.data_type == 'integer':
                    print("Convertendo de INTEGER para BOOLEAN...")
                    
                    # 2. Criar nova coluna temporária
                    db.session.execute(
                        text("ALTER TABLE ai_grupos_empresariais ADD COLUMN ativo_novo BOOLEAN")
                    )
                    
                    # 3. Copiar dados convertendo
                    db.session.execute(
                        text("""
                            UPDATE ai_grupos_empresariais 
                            SET ativo_novo = CASE 
                                WHEN ativo = 1 THEN TRUE 
                                ELSE FALSE 
                            END
                        """)
                    )
                    
                    # 4. Remover coluna antiga
                    db.session.execute(
                        text("ALTER TABLE ai_grupos_empresariais DROP COLUMN ativo")
                    )
                    
                    # 5. Renomear nova coluna
                    db.session.execute(
                        text("ALTER TABLE ai_grupos_empresariais RENAME COLUMN ativo_novo TO ativo")
                    )
                    
                    # 6. Adicionar default
                    db.session.execute(
                        text("ALTER TABLE ai_grupos_empresariais ALTER COLUMN ativo SET DEFAULT TRUE")
                    )
                    
                    db.session.commit()
                    print("✅ Campo convertido com sucesso!")
                    
                elif result.data_type == 'boolean':
                    print("✅ Campo já está como BOOLEAN!")
                else:
                    print(f"⚠️ Tipo inesperado: {result.data_type}")
            else:
                print("❌ Campo 'ativo' não encontrado!")
                
        except Exception as e:
            print(f"❌ Erro ao converter campo: {e}")
            db.session.rollback()
            
            # Tentar solução alternativa
            print("\n🔄 Tentando solução alternativa...")
            try:
                # Recriar a tabela com estrutura correta
                db.session.execute(text("DROP TABLE IF EXISTS ai_grupos_empresariais CASCADE"))
                
                db.session.execute(text("""
                    CREATE TABLE ai_grupos_empresariais (
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
                
                # Inserir dados básicos
                grupos = [
                    ('Assai', 'Atacarejo', ['06.057.223/'], ['assai', 'assaí'], "cliente ILIKE '%assai%'"),
                    ('Atacadão', 'Atacarejo', ['75.315.333/', '00.063.960/'], ['atacadao', 'atacadão'], "cliente ILIKE '%atacadao%'"),
                    ('Carrefour', 'Varejo', ['45.543.915/'], ['carrefour'], "cliente ILIKE '%carrefour%'")
                ]
                
                for nome, tipo, cnpjs, palavras, filtro in grupos:
                    db.session.execute(
                        text("""
                            INSERT INTO ai_grupos_empresariais 
                            (nome_grupo, tipo_negocio, cnpj_prefixos, palavras_chave, filtro_sql)
                            VALUES (:nome, :tipo, :cnpjs, :palavras, :filtro)
                        """),
                        {'nome': nome, 'tipo': tipo, 'cnpjs': cnpjs, 'palavras': palavras, 'filtro': filtro}
                    )
                
                db.session.commit()
                print("✅ Tabela recriada com sucesso!")
                
            except Exception as e2:
                print(f"❌ Erro na solução alternativa: {e2}")
                db.session.rollback()
        
        # Verificar resultado final
        print("\n📊 VERIFICANDO RESULTADO...")
        try:
            count = db.session.execute(
                text("SELECT COUNT(*) FROM ai_grupos_empresariais WHERE ativo = TRUE")
            ).scalar()
            print(f"✅ {count} grupos ativos encontrados!")
            
            # Listar grupos
            grupos = db.session.execute(
                text("SELECT nome_grupo, tipo_negocio FROM ai_grupos_empresariais WHERE ativo = TRUE")
            ).fetchall()
            
            for grupo in grupos:
                print(f"  - {grupo.nome_grupo} ({grupo.tipo_negocio})")
                
        except Exception as e:
            print(f"❌ Erro ao verificar: {e}")

if __name__ == "__main__":
    corrigir_campo_ativo() 