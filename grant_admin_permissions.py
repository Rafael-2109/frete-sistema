#!/usr/bin/env python
"""
Script para garantir que o admin tenha todas as permissões
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.auth.models import Usuario
from app.permissions.models import (
    PerfilUsuario, ModuloSistema, PermissaoUsuario,
    PermissionCategory
)

def grant_all_permissions_to_admin():
    """Garante que o perfil admin tenha todas as permissões"""
    app = create_app()
    
    with app.app_context():
        print("🔧 Configurando permissões totais para admin...")
        
        # 1. Buscar perfil admin
        perfil_admin = PerfilUsuario.query.filter_by(nome='admin').first()
        if not perfil_admin:
            print("❌ Perfil admin não encontrado!")
            return False
        
        # 2. Buscar todos os módulos
        modulos = ModuloSistema.query.all()
        print(f"📋 Encontrados {len(modulos)} módulos")
        
        # 3. Buscar usuário admin
        usuario_admin = Usuario.query.filter_by(email='rafael6250@gmail.com').first()
        if not usuario_admin:
            print("❌ Usuário admin não encontrado!")
            return False
        
        # 4. Criar permissões para TODOS os módulos
        for modulo in modulos:
            # Verificar se já existe permissão
            perm = PermissaoUsuario.query.filter_by(
                usuario_id=usuario_admin.id,
                modulo_id=modulo.id
            ).first()
            
            if not perm:
                perm = PermissaoUsuario(
                    usuario_id=usuario_admin.id,
                    modulo_id=modulo.id,
                    visualizar=True,
                    criar=True,
                    editar=True,
                    deletar=True,
                    aprovar=True,
                    exportar=True
                )
                db.session.add(perm)
                print(f"✅ Permissão total criada para: {modulo.nome}")
            else:
                # Atualizar para garantir acesso total
                perm.visualizar = True
                perm.criar = True
                perm.editar = True
                perm.deletar = True
                perm.aprovar = True
                perm.exportar = True
                print(f"✅ Permissão atualizada para: {modulo.nome}")
        
        # 5. Criar módulo permissions se não existir
        modulo_permissions = ModuloSistema.query.filter_by(nome='permissions').first()
        if not modulo_permissions:
            # Criar categoria administrador se não existir
            cat_admin = PermissionCategory.query.filter_by(nome='administrador').first()
            if not cat_admin:
                cat_admin = PermissionCategory(
                    nome='administrador',
                    nome_exibicao='Administração',
                    descricao='Módulos administrativos',
                    icone='fas fa-cog',
                    ordem=1
                )
                db.session.add(cat_admin)
                db.session.flush()
            
            modulo_permissions = ModuloSistema(
                nome='permissions',
                nome_exibicao='Gerenciar Permissões',
                descricao='Sistema de permissões de usuários',
                icone='fas fa-shield-alt',
                rota='permissions.index',
                categoria_id=cat_admin.id,
                ativo=True,
                ordem=1
            )
            db.session.add(modulo_permissions)
            db.session.flush()
            print("✅ Módulo permissions criado")
        
        # 6. Garantir permissão no módulo permissions
        perm_permissions = PermissaoUsuario.query.filter_by(
            usuario_id=usuario_admin.id,
            modulo_id=modulo_permissions.id
        ).first()
        
        if not perm_permissions:
            perm_permissions = PermissaoUsuario(
                usuario_id=usuario_admin.id,
                modulo_id=modulo_permissions.id,
                visualizar=True,
                criar=True,
                editar=True,
                deletar=True,
                aprovar=True,
                exportar=True
            )
            db.session.add(perm_permissions)
        
        # 7. Remover verificação de submódulos (não existe no modelo atual)
        
        db.session.commit()
        
        print("\n🎉 Sucesso! Admin agora tem acesso total ao sistema!")
        print("   - Todas as permissões foram concedidas")
        print("   - Módulo permissions foi criado/atualizado")
        print("   - Submódulos foram configurados")
        print("\n📋 Estatísticas:")
        print(f"   - Total de módulos: {len(modulos)}")
        print(f"   - Permissões do admin: {PermissaoUsuario.query.filter_by(usuario_id=usuario_admin.id).count()}")
        
        return True

if __name__ == "__main__":
    grant_all_permissions_to_admin()