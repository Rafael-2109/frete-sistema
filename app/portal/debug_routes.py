"""
Script de diagnóstico para verificar status das rotas do portal
Execute este arquivo para verificar se o blueprint portal está registrado
"""

def verificar_rotas_portal():
    """Verifica o status das rotas do portal"""
    from flask import Flask
    from app import create_app
    import sys
    
    print("=" * 60)
    print("🔍 DIAGNÓSTICO DE ROTAS DO PORTAL")
    print("=" * 60)
    
    try:
        # Criar aplicação
        app = create_app()
        
        # Verificar se portal_bp foi registrado
        portal_registrado = False
        for blueprint_name in app.blueprints:
            if blueprint_name == 'portal':
                portal_registrado = True
                print(f"✅ Blueprint 'portal' está registrado")
                break
        
        if not portal_registrado:
            print("❌ Blueprint 'portal' NÃO está registrado!")
            
            # Tentar importar manualmente para ver o erro
            print("\n🔍 Tentando importar portal_bp manualmente...")
            try:
                from app.portal import portal_bp
                print("✅ Importação manual funcionou!")
                print("⚠️ O problema está no registro, não na importação")
            except Exception as e:
                print(f"❌ Erro na importação: {e}")
                import traceback
                traceback.print_exc()
        
        # Listar todas as rotas do portal se registrado
        if portal_registrado:
            print("\n📋 Rotas do portal registradas:")
            with app.app_context():
                rules = list(app.url_map.iter_rules())
                portal_routes = [r for r in rules if r.endpoint.startswith('portal.')]
                
                if portal_routes:
                    for rule in sorted(portal_routes, key=lambda x: str(x)):
                        print(f"  • {rule.rule} -> {rule.endpoint}")
                        
                    # Verificar especificamente central_portais
                    central_exists = any(r.endpoint == 'portal.central_portais' for r in portal_routes)
                    if central_exists:
                        print(f"\n✅ Rota 'portal.central_portais' EXISTE")
                    else:
                        print(f"\n❌ Rota 'portal.central_portais' NÃO EXISTE")
                else:
                    print("  ❌ Nenhuma rota do portal foi encontrada")
        
        # Verificar todos os blueprints registrados
        print("\n📦 Todos os blueprints registrados:")
        for bp_name in sorted(app.blueprints.keys()):
            bp = app.blueprints[bp_name]
            print(f"  • {bp_name} (prefix: {bp.url_prefix or '/'})")
        
        # Tentar importar cada parte do portal separadamente
        print("\n🔍 Testando imports do portal separadamente:")
        
        imports_to_test = [
            ("app.portal", "Módulo principal"),
            ("app.portal.routes", "Routes principal"),
            ("app.portal.routes_sessao", "Routes de sessão"),
            ("app.portal.routes_async", "Routes assíncronas"),
            ("app.portal.atacadao.routes_depara", "Atacadão De-Para"),
            ("app.portal.atacadao.routes_agendamento", "Atacadão Agendamento"),
            ("app.portal.atacadao.verificacao_protocolo", "Atacadão Verificação"),
            ("app.portal.tenda.routes_depara", "Tenda De-Para"),
            ("app.portal.tenda.routes_agendamento", "Tenda Agendamento"),
        ]
        
        for module_path, description in imports_to_test:
            try:
                __import__(module_path)
                print(f"  ✅ {description} ({module_path})")
            except ImportError as e:
                print(f"  ❌ {description} ({module_path}): {e}")
            except Exception as e:
                print(f"  ⚠️ {description} ({module_path}): {type(e).__name__}: {e}")
        
        return portal_registrado
        
    except Exception as e:
        print(f"❌ Erro ao criar aplicação: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    import sys
    success = verificar_rotas_portal()
    sys.exit(0 if success else 1)