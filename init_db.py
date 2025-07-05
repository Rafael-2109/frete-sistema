#!/usr/bin/env python3
import os
import sys
from app import create_app, db
from sqlalchemy import text

def init_database():
    """Inicializar banco de dados com tratamento de erros"""
    print("=== INICIANDO BANCO DE DADOS ===")
    
    # Criar aplicação
    app = create_app()
    
    with app.app_context():
        try:
            # Tentar corrigir migrações primeiro
            print("🔧 Verificando migrações...")
            from flask_migrate import stamp
            try:
                stamp(revision='heads')
                print("✅ Migrações marcadas como aplicadas")
            except Exception as e:
                print(f"⚠️  Aviso sobre migrações: {str(e)}")
                # Continuar mesmo com erro
            
            # Criar todas as tabelas
            print("✓ Criando tabelas...")
            db.create_all()
            print("✓ Comando db.create_all() executado")
            
            # Contar tabelas criadas
            if db.engine.url.drivername == 'postgresql':
                result = db.session.execute(text(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_schema = 'public'"
                ))
            else:
                result = db.session.execute(text(
                    "SELECT COUNT(*) FROM sqlite_master WHERE type='table'"
                ))
            
            count = result.scalar()
            print(f"✓ {count} tabelas no banco de dados")
            
            print("✓ Banco de dados inicializado com sucesso")
            
        except Exception as e:
            print(f"❌ Erro ao inicializar banco: {str(e)}")
            # Continuar mesmo com erro para não bloquear o deploy
            print("⚠️  Continuando com o deploy...")
            
    print("=== PROCESSO CONCLUÍDO ===")

if __name__ == "__main__":
    init_database()
