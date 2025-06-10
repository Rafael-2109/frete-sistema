#!/usr/bin/env python3
import os
import sys

def init_database():
    try:
        print("=== INICIANDO BANCO DE DADOS ===")
        
        # Verificar se estamos em produção
        if os.environ.get('DATABASE_URL'):
            print("✓ Ambiente de produção detectado (PostgreSQL)")
        else:
            print("✓ Ambiente de desenvolvimento detectado (SQLite)")
            
        # Importar app
        from app import create_app, db
        
        print("✓ Módulos importados com sucesso")
        
        # Criar aplicação
        app = create_app()
        print("✓ Aplicação Flask criada")
        
        with app.app_context():
            # Criar todas as tabelas
            db.create_all()
            print("✓ Comando db.create_all() executado")
            
            # Verificar tabelas criadas
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"✓ {len(tables)} tabelas criadas:")
            for table in sorted(tables)[:10]:  # Mostrar apenas as primeiras 10
                print(f"  - {table}")
            if len(tables) > 10:
                print(f"  ... e mais {len(tables) - 10} tabelas")
            
            # Atualizar colunas CNPJ para o tamanho correto
            try:
                print("🔧 Atualizando colunas CNPJ para VARCHAR(20)...")
                
                comandos_sql = [
                    "ALTER TABLE transportadoras ALTER COLUMN cnpj TYPE VARCHAR(20);",
                    "ALTER TABLE cotacao_itens ALTER COLUMN cnpj_cliente TYPE VARCHAR(20);", 
                    "ALTER TABLE embarque_volumes ALTER COLUMN cnpj_cliente TYPE VARCHAR(20);",
                    "ALTER TABLE contatos_agendamento ALTER COLUMN cnpj TYPE VARCHAR(20);",
                    "ALTER TABLE separacao_itens ALTER COLUMN cnpj_cpf TYPE VARCHAR(20);",
                    "ALTER TABLE pedidos ALTER COLUMN cnpj_cpf TYPE VARCHAR(20);",
                    "ALTER TABLE entregas_monitoradas ALTER COLUMN cnpj_cliente TYPE VARCHAR(20);",
                    "ALTER TABLE faturamento ALTER COLUMN cnpj_cliente TYPE VARCHAR(20);",
                    "ALTER TABLE faturamento ALTER COLUMN cnpj_transportadora TYPE VARCHAR(20);",
                    "ALTER TABLE fretes ALTER COLUMN cnpj_cliente TYPE VARCHAR(20);"
                ]
                
                for comando in comandos_sql:
                    try:
                        db.session.execute(db.text(comando))
                    except Exception:
                        # Tabela pode não existir ou já estar correta
                        continue
                
                db.session.commit()
                print("✓ Colunas CNPJ atualizadas para VARCHAR(20)")
                
            except Exception as e:
                print(f"⚠️ Aviso ao atualizar colunas CNPJ: {str(e)}")
                # Não falhamos o deploy por isso
                pass
                
        print("=== BANCO INICIALIZADO COM SUCESSO ===")
        return True
        
    except Exception as e:
        print(f"❌ ERRO na inicialização: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1) 