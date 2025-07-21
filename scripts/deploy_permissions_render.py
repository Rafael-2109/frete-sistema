#!/usr/bin/env python3
"""
Script para Deploy do Sistema de Permissões Avançadas no Render
===============================================================

Este script facilita o deploy das mudanças de permissões no ambiente de produção.

MUDANÇAS INCLUÍDAS:
1. Campo 'equipe_vendas' adicionado em:
   - relatoriofaturamentoimportado
   - faturamentoproduto

2. Sistema completo de permissões com 7 tabelas:
   - perfil_usuario
   - modulo_sistema  
   - funcao_modulo
   - permissao_usuario
   - usuario_vendedor
   - usuario_equipe_vendas
   - log_permissao

3. Índices otimizados para performance

USO:
    python scripts/deploy_permissions_render.py
"""

import os
import sys

def verificar_ambiente():
    """Verifica se estamos no ambiente correto"""
    if not os.path.exists('app'):
        print("❌ Execute este script na raiz do projeto!")
        return False
    
    if not os.path.exists('migrations/versions/add_permissions_equipe_vendas.py'):
        print("❌ Migração não encontrada!")
        return False
    
    return True

def main():
    print("🚀 DEPLOY SISTEMA DE PERMISSÕES - RENDER")
    print("=" * 50)
    
    if not verificar_ambiente():
        sys.exit(1)
    
    print("✅ Ambiente verificado")
    print()
    
    print("📋 INSTRUÇÕES PARA DEPLOY NO RENDER:")
    print()
    print("1️⃣  FAZER COMMIT E PUSH:")
    print("    git add .")
    print("    git commit -m 'Sistema permissões avançadas + equipe_vendas'")
    print("    git push origin main")
    print()
    
    print("2️⃣  NO RENDER.COM:")
    print("    a) Acesse o dashboard do projeto")
    print("    b) Vá em 'Environment' > 'Shell'") 
    print("    c) Execute os comandos:")
    print()
    print("       export FLASK_APP=run.py")
    print("       flask db upgrade")
    print()
    
    print("3️⃣  INICIALIZAR DADOS PADRÃO:")
    print("    python3 -c \"")
    print("    from app import create_app")
    print("    from app.permissions.models import inicializar_dados_padrao")
    print("    app = create_app()")
    print("    with app.app_context():")
    print("        inicializar_dados_padrao()")
    print("    print('✅ Dados padrão inicializados')")
    print("    \"")
    print()
    
    print("4️⃣  REGISTRAR BLUEPRINT (NO CÓDIGO):")
    print("    Adicionar em app/__init__.py:")
    print("    from app.permissions import permissions_bp")
    print("    app.register_blueprint(permissions_bp)")
    print()
    
    print("5️⃣  VERIFICAR FUNCIONAMENTO:")
    print("    - Acesse /admin/permissions")
    print("    - Confirme que as tabelas foram criadas")
    print("    - Teste permissões básicas")
    print()
    
    print("🔍 VERIFICAÇÕES PÓS-DEPLOY:")
    print("=" * 30)
    print("✅ Campo equipe_vendas em relatoriofaturamentoimportado")
    print("✅ Campo equipe_vendas em faturamentoproduto") 
    print("✅ 7 novas tabelas de permissões criadas")
    print("✅ Índices de performance aplicados")
    print("✅ Interface /admin/permissions acessível")
    print()
    
    print("⚠️  ROLLBACK (SE NECESSÁRIO):")
    print("    flask db downgrade add_permissions_equipe_vendas")
    print()
    
    print("✅ Deploy preparado! Siga as instruções acima.")

if __name__ == "__main__":
    main() 