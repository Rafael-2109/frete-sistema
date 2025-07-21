#!/usr/bin/env python3
"""
Script para verificar o sistema de permissões
"""

from app import create_app, db
from app.permissions.models import PerfilUsuario, ModuloSistema, FuncaoModulo
import sys

def main():
    print("🔍 Verificando sistema de permissões...")
    
    app = create_app()
    with app.app_context():
        try:
            # Verificar perfis
            perfis = PerfilUsuario.query.count()
            print(f"📋 Perfis encontrados: {perfis}")
            
            if perfis == 0:
                print("   Criando perfis padrão...")
                PerfilUsuario.get_or_create_default_profiles()
                perfis = PerfilUsuario.query.count()
                print(f"✅ Perfis criados: {perfis}")
            
            # Verificar módulos
            modulos = ModuloSistema.query.count()
            print(f"📦 Módulos encontrados: {modulos}")
            
            if modulos == 0:
                print("   Criando módulos padrão...")
                ModuloSistema.get_or_create_default_modules()
                modulos = ModuloSistema.query.count()
                print(f"✅ Módulos criados: {modulos}")
            
            # Verificar funções
            funcoes = FuncaoModulo.query.count()
            print(f"⚙️ Funções encontradas: {funcoes}")
            
            if funcoes == 0:
                print("   Criando funções básicas...")
                # Criar funções básicas para cada módulo
                for modulo in ModuloSistema.query.all():
                    # Função visualizar
                    funcao_ver = FuncaoModulo(
                        modulo_id=modulo.id,
                        nome='visualizar',
                        nome_exibicao=f'Visualizar {modulo.nome_exibicao}',
                        descricao=f'Permite visualizar dados do módulo {modulo.nome_exibicao}',
                        nivel_critico='NORMAL'
                    )
                    db.session.add(funcao_ver)
                    
                    # Função editar
                    funcao_edit = FuncaoModulo(
                        modulo_id=modulo.id,
                        nome='editar',
                        nome_exibicao=f'Editar {modulo.nome_exibicao}',
                        descricao=f'Permite editar dados do módulo {modulo.nome_exibicao}',
                        nivel_critico='ALTO'
                    )
                    db.session.add(funcao_edit)
                
                db.session.commit()
                funcoes = FuncaoModulo.query.count()
                print(f"✅ Funções criadas: {funcoes}")
            
            print(f"\n✅ SISTEMA DE PERMISSÕES VERIFICADO:")
            print(f"   - {perfis} perfis")
            print(f"   - {modulos} módulos")
            print(f"   - {funcoes} funções")
            
            return True
            
        except Exception as e:
            print(f"❌ ERRO: {e}")
            return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)