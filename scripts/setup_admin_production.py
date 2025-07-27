#!/usr/bin/env python
"""
Script para configurar usuário admin em produção (Render)
Uso: python scripts/setup_admin_production.py [email]
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.auth.models import Usuario
from app.permissions.models import PerfilUsuario
from sqlalchemy import text

def setup_admin(email=None):
    """Configura usuário como admin"""
    app = create_app()
    
    with app.app_context():
        # Email padrão ou fornecido via argumento
        admin_email = email or os.getenv('ADMIN_EMAIL', 'rafael6250@gmail.com')
        
        print(f"🔧 Configurando admin para: {admin_email}")
        
        try:
            # 1. Verificar/criar perfil admin
            perfil_admin = PerfilUsuario.query.filter_by(nome='admin').first()
            if not perfil_admin:
                perfil_admin = PerfilUsuario(
                    nome='admin',
                    nome_exibicao='Administrador',
                    descricao='Acesso total ao sistema',
                    nivel=10,
                    ativo=True
                )
                db.session.add(perfil_admin)
                db.session.commit()
                print("✅ Perfil admin criado")
            
            # 2. Verificar se colunas existem
            result = db.session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'usuarios' 
                AND column_name IN ('perfil_id', 'perfil_nome')
            """))
            existing_cols = [row[0] for row in result]
            
            if 'perfil_id' not in existing_cols:
                db.session.execute(text(
                    "ALTER TABLE usuarios ADD COLUMN perfil_id INTEGER REFERENCES perfil_usuario(id)"
                ))
                db.session.commit()
                print("✅ Coluna perfil_id adicionada")
                
            if 'perfil_nome' not in existing_cols:
                db.session.execute(text(
                    "ALTER TABLE usuarios ADD COLUMN perfil_nome VARCHAR(50)"
                ))
                db.session.commit()
                print("✅ Coluna perfil_nome adicionada")
            
            # 3. Atualizar usuário
            usuario = Usuario.query.filter_by(email=admin_email).first()
            
            if usuario:
                usuario.perfil_id = perfil_admin.id
                usuario.perfil_nome = 'admin'
                db.session.commit()
                
                print(f"\n✅ Sucesso! {usuario.nome} agora é ADMINISTRADOR!")
                print(f"   Email: {usuario.email}")
                print(f"   Perfil: {perfil_admin.nome_exibicao}")
                return True
            else:
                print(f"\n❌ Usuário {admin_email} não encontrado!")
                print("   Certifique-se de criar a conta primeiro.")
                return False
                
        except Exception as e:
            print(f"\n❌ Erro: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    # Permitir email via linha de comando
    email = sys.argv[1] if len(sys.argv) > 1 else None
    setup_admin(email)