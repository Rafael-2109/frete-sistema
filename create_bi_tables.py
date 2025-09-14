#!/usr/bin/env python3
"""
Script para criar as tabelas do módulo BI usando SQLAlchemy
"""
import os
import sys

# Adiciona o diretório do projeto ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.bi.models import (
    BiFreteAgregado, 
    BiDespesaDetalhada,
    BiPerformanceTransportadora,
    BiAnaliseRegional,
    BiIndicadorMensal
)

def criar_tabelas_bi():
    """Cria todas as tabelas do módulo BI"""
    app = create_app()
    
    with app.app_context():
        print("🚀 Iniciando criação das tabelas do BI...")
        
        try:
            # Cria todas as tabelas do módulo BI
            # Usa create_all() mas apenas para as tabelas do BI
            for model in [BiFreteAgregado, BiDespesaDetalhada, 
                         BiPerformanceTransportadora, BiAnaliseRegional, 
                         BiIndicadorMensal]:
                tablename = model.__tablename__
                
                # Verifica se a tabela já existe
                if not db.inspect(db.engine).has_table(tablename):
                    print(f"✅ Criando tabela: {tablename}")
                    model.__table__.create(db.engine)
                else:
                    print(f"⚠️ Tabela já existe: {tablename}")
            
            # Cria a função get_regiao_by_uf se não existir
            print("📦 Criando função auxiliar get_regiao_by_uf...")
            
            # Verifica se a função já existe
            check_function = """
                SELECT EXISTS (
                    SELECT 1 
                    FROM pg_proc 
                    WHERE proname = 'get_regiao_by_uf'
                );
            """
            result = db.session.execute(db.text(check_function)).scalar()
            
            if not result:
                create_function = """
                CREATE OR REPLACE FUNCTION get_regiao_by_uf(uf VARCHAR(2))
                RETURNS VARCHAR(20) AS $$
                BEGIN
                    CASE uf
                        WHEN 'AC', 'AP', 'AM', 'PA', 'RO', 'RR', 'TO' THEN
                            RETURN 'Norte';
                        WHEN 'AL', 'BA', 'CE', 'MA', 'PB', 'PE', 'PI', 'RN', 'SE' THEN
                            RETURN 'Nordeste';
                        WHEN 'DF', 'GO', 'MT', 'MS' THEN
                            RETURN 'Centro-Oeste';
                        WHEN 'ES', 'MG', 'RJ', 'SP' THEN
                            RETURN 'Sudeste';
                        WHEN 'PR', 'RS', 'SC' THEN
                            RETURN 'Sul';
                        ELSE
                            RETURN 'Indefinido';
                    END CASE;
                END;
                $$ LANGUAGE plpgsql;
                """
                db.session.execute(db.text(create_function))
                db.session.commit()
                print("✅ Função get_regiao_by_uf criada com sucesso!")
            else:
                print("⚠️ Função get_regiao_by_uf já existe")
            
            print("\n🎉 Todas as tabelas do BI foram criadas com sucesso!")
            print("\n📝 Próximos passos:")
            print("1. Execute 'python run_bi_etl.py' para carregar os dados")
            print("2. Acesse http://localhost:5000/bi/dashboard para visualizar")
            
            return True
            
        except Exception as e:
            print(f"\n❌ Erro ao criar tabelas: {str(e)}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    sucesso = criar_tabelas_bi()
    sys.exit(0 if sucesso else 1)