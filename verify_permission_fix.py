#!/usr/bin/env python3
"""
Script simples para verificar se as correções foram aplicadas
"""

import os

def verify_fixes():
    """Verifica se todas as correções foram aplicadas"""
    
    print("🔍 Verificando correções de permissão...\n")
    
    all_ok = True
    
    # 1. Verificar PermissionCategory no models.py
    print("=== 1. Verificando models.py ===")
    models_file = 'app/permissions/models.py'
    with open(models_file, 'r') as f:
        content = f.read()
    
    # Verificar colunas em português
    checks = [
        ('nome = db.Column(db.String(50)', 'Coluna "nome" em português'),
        ('nome_exibicao = db.Column(db.String(100)', 'Coluna "nome_exibicao" em português'),
        ('descricao = db.Column(db.String(255)', 'Coluna "descricao" em português'),
        ('icone = db.Column(db.String(50)', 'Coluna "icone" em português'),
        ('cor = db.Column(db.String(7)', 'Coluna "cor" em português'),
        ('ordem = db.Column(db.Integer', 'Coluna "ordem" em português'),
        ('ativo = db.Column(db.Boolean', 'Coluna "ativo" em português'),
        ('criado_em = db.Column(db.DateTime', 'Coluna "criado_em" em português'),
        ('return f\'<PermissionCategory {self.nome}>\'', '__repr__ usa self.nome')
    ]
    
    for check, desc in checks:
        if check in content:
            print(f"✅ {desc}")
        else:
            print(f"❌ {desc} - NÃO ENCONTRADO")
            all_ok = False
    
    # 2. Verificar decorators_patch.py
    print("\n=== 2. Verificando decorators_patch.py ===")
    decorator_file = 'app/permissions/decorators_patch.py'
    with open(decorator_file, 'r') as f:
        content = f.read()
    
    checks = [
        ("perfil.lower() in ['admin', 'administrador', 'administrator']", 'Verifica múltiplas variações de admin'),
        ("perfil = getattr(current_user, 'perfil_nome', None) or getattr(current_user, 'perfil', None)", 'Obtém perfil de forma segura'),
        ('Admin bypass ativado para {current_user.email} (perfil: {perfil})', 'Log mostra o perfil'),
    ]
    
    for check, desc in checks:
        if check in content:
            print(f"✅ {desc}")
        else:
            print(f"❌ {desc} - NÃO ENCONTRADO")
            all_ok = False
    
    # 3. Verificar routes_hierarchical.py
    print("\n=== 3. Verificando routes_hierarchical.py ===")
    routes_file = 'app/permissions/routes_hierarchical.py'
    with open(routes_file, 'r') as f:
        content = f.read()
    
    if 'from app.permissions.decorators_patch import require_permission' in content:
        print("✅ Import correto do decorators_patch")
    else:
        print("❌ Import incorreto - deve usar decorators_patch")
        all_ok = False
    
    # Resumo
    print("\n=== RESUMO ===")
    if all_ok:
        print("✅ TODAS as correções foram aplicadas com sucesso!")
        print("\n📋 Correções aplicadas:")
        print("   1. PermissionCategory usa colunas em português (nome, nome_exibicao, etc)")
        print("   2. Decorador permite admin/administrador/administrator")
        print("   3. Routes importa decorators_patch corretamente")
        print("\n🎉 O erro 403 deve estar resolvido para rafael6250@gmail.com")
    else:
        print("❌ Algumas correções estão faltando!")
    
    return all_ok

if __name__ == '__main__':
    verify_fixes()