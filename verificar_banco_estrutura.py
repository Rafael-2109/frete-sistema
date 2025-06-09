#!/usr/bin/env python3
import os
import sqlite3
from app import create_app, db
from app.auth.models import Usuario

def verificar_estrutura_banco():
    """Verifica e corrige a estrutura do banco de dados"""
    
    # Cria o contexto da aplicação
    app = create_app()
    
    with app.app_context():
        try:
            # Verifica se consegue acessar a tabela usuarios
            print("🔍 Verificando estrutura da tabela usuarios...")
            
            # Tenta fazer uma consulta simples
            resultado = db.session.execute(db.text("SELECT name FROM sqlite_master WHERE type='table' AND name='usuarios'")).fetchone()
            
            if not resultado:
                print("❌ Tabela usuarios não existe. Criando...")
                db.create_all()
                print("✅ Tabelas criadas com sucesso!")
            else:
                print("✅ Tabela usuarios existe.")
                
                # Verifica se a coluna status existe
                try:
                    resultado = db.session.execute(db.text("PRAGMA table_info(usuarios)")).fetchall()
                    colunas = [row[1] for row in resultado]
                    
                    print(f"📋 Colunas encontradas: {colunas}")
                    
                    if 'status' not in colunas:
                        print("❌ Coluna 'status' não encontrada. Adicionando...")
                        db.session.execute(db.text("ALTER TABLE usuarios ADD COLUMN status VARCHAR(20) DEFAULT 'ativo'"))
                        db.session.commit()
                        print("✅ Coluna 'status' adicionada!")
                    else:
                        print("✅ Coluna 'status' já existe.")
                        
                except Exception as e:
                    print(f"❌ Erro ao verificar colunas: {e}")
                    print("🔄 Recriando tabelas...")
                    db.drop_all()
                    db.create_all()
                    print("✅ Tabelas recriadas com sucesso!")
            
            # Verifica se existe pelo menos um usuário
            usuarios = Usuario.query.all()
            print(f"👥 Usuários encontrados: {len(usuarios)}")
            
            if len(usuarios) == 0:
                print("👤 Criando usuário administrador...")
                admin = Usuario(
                    nome='Rafael Nascimento',
                    email='rafael@nacomgoya.com.br',
                    perfil='administrador',
                    status='ativo',
                    empresa='Nacom Goya',
                    cargo='Administrador'
                )
                admin.set_senha('Rafa2109')
                db.session.add(admin)
                db.session.commit()
                print("✅ Usuário administrador criado!")
            
            print("\n🎉 Verificação concluída com sucesso!")
            
        except Exception as e:
            print(f"❌ Erro durante verificação: {e}")
            db.session.rollback()

if __name__ == '__main__':
    verificar_estrutura_banco() 