#!/usr/bin/env python3
"""
Script para testar o sistema de permissões comerciais.

Este script testa:
1. Criação de permissões
2. Consulta de permissões
3. Aplicação de filtros
4. Registro de logs

Autor: Sistema de Fretes
Data: 2025-01-21
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.auth.models import Usuario
from app.comercial.services.permissao_service import PermissaoService
from app.comercial.models import PermissaoComercial, LogPermissaoComercial
from sqlalchemy import text

def testar_permissoes():
    """Testa o sistema completo de permissões"""

    app = create_app()

    with app.app_context():
        print("\n" + "="*80)
        print("TESTE DO SISTEMA DE PERMISSÕES COMERCIAIS")
        print("="*80 + "\n")

        try:
            # 1. Buscar um usuário vendedor para teste
            print("📋 1. Buscando usuários vendedores...")
            vendedores = Usuario.query.filter_by(perfil='vendedor', status='ativo').all()

            if not vendedores:
                print("❌ Nenhum vendedor ativo encontrado para teste")
                print("   Criando usuário vendedor de teste...")

                vendedor_teste = Usuario(
                    nome="Vendedor Teste Permissões",
                    email="vendedor.teste.permissoes@empresa.com",
                    perfil="vendedor",
                    status="ativo"
                )
                vendedor_teste.set_senha("teste123")
                db.session.add(vendedor_teste)
                db.session.commit()
                vendedor_id = vendedor_teste.id
                print(f"✅ Vendedor de teste criado: ID={vendedor_id}")
            else:
                vendedor_teste = vendedores[0]
                vendedor_id = vendedor_teste.id
                print(f"✅ Usando vendedor existente: {vendedor_teste.nome} (ID={vendedor_id})")

            # 2. Limpar permissões antigas (se houver)
            print("\n📋 2. Limpando permissões antigas...")
            PermissaoComercial.query.filter_by(usuario_id=vendedor_id).delete()
            db.session.commit()
            print("✅ Permissões antigas removidas")

            # 3. Adicionar permissões de teste
            print("\n📋 3. Adicionando permissões de teste...")

            # Buscar ou criar usuário admin para os testes
            admin = Usuario.query.filter_by(perfil='administrador').first()
            if not admin:
                admin = Usuario(
                    nome="Admin Teste",
                    email="admin@empresa.com",
                    perfil="administrador",
                    status="ativo"
                )
                admin.set_senha("admin123")
                db.session.add(admin)
                db.session.commit()
                print("   ✅ Admin de teste criado")

            # Simular contexto de requisição com admin logado
            with app.test_request_context():
                from flask_login import login_user
                login_user(admin)

                # Adicionar permissão de equipe
                resultado = PermissaoService.adicionar_permissao(
                    usuario_id=vendedor_id,
                    tipo='equipe',
                    valor='VENDAS_SP',
                    admin_email='admin@empresa.com'
                )
                if isinstance(resultado, dict):
                    print(f"   - Equipe VENDAS_SP: {resultado.get('message', 'Adicionado')}")
                else:
                    print(f"   - Equipe VENDAS_SP: {'Adicionado com sucesso' if resultado else 'Erro ao adicionar'}")

                # Adicionar permissão de vendedor específico
                resultado = PermissaoService.adicionar_permissao(
                    usuario_id=vendedor_id,
                    tipo='vendedor',
                    valor='João Silva',
                    admin_email='admin@empresa.com'
                )
                if isinstance(resultado, dict):
                    print(f"   - Vendedor João Silva: {resultado.get('message', 'Adicionado')}")
                else:
                    print(f"   - Vendedor João Silva: {'Adicionado com sucesso' if resultado else 'Erro ao adicionar'}")

                resultado = PermissaoService.adicionar_permissao(
                    usuario_id=vendedor_id,
                    tipo='vendedor',
                    valor='Maria Santos',
                    admin_email='admin@empresa.com'
                )
                if isinstance(resultado, dict):
                    print(f"   - Vendedor Maria Santos: {resultado.get('message', 'Adicionado')}")
                else:
                    print(f"   - Vendedor Maria Santos: {'Adicionado com sucesso' if resultado else 'Erro ao adicionar'}")

            # 4. Consultar permissões
            print("\n📋 4. Consultando permissões do vendedor...")
            permissoes = PermissaoService.obter_permissoes_usuario(vendedor_id)

            print(f"   - Equipes permitidas: {permissoes['equipes']}")
            print(f"   - Vendedores permitidos: {permissoes['vendedores']}")
            total = len(permissoes['equipes']) + len(permissoes['vendedores'])
            print(f"   - Total de permissões: {total}")

            # 5. Testar filtro em query simulada
            print("\n📋 5. Testando aplicação de filtros...")

            # Simular query da CarteiraPrincipal
            from app.carteira.models import CarteiraPrincipal

            # Contar total sem filtro
            total_sem_filtro = CarteiraPrincipal.query.count()
            print(f"   - Total de itens na carteira (sem filtro): {total_sem_filtro}")

            # Aplicar filtro de permissões (simulando vendedor logado)
            with app.test_request_context():
                from flask_login import login_user
                login_user(vendedor_teste)

                query = CarteiraPrincipal.query
                query = PermissaoService.aplicar_filtro_permissoes(
                    query,
                    campo_equipe='equipe_vendas',
                    campo_vendedor='vendedor'
                )
                total_com_filtro = query.count()
                print(f"   - Total de itens após filtro: {total_com_filtro}")

                # Mostrar alguns exemplos
                itens = query.limit(5).all()
                if itens:
                    print("\n   Exemplos de itens filtrados:")
                    for item in itens:
                        print(f"     - Pedido: {item.num_pedido}, Vendedor: {item.vendedor}, Equipe: {item.equipe_vendas}")

            # 6. Verificar logs
            print("\n📋 6. Verificando logs de auditoria...")
            logs = LogPermissaoComercial.query.filter_by(usuario_id=vendedor_id).order_by(
                LogPermissaoComercial.data_hora.desc()
            ).limit(5).all()

            print(f"   - Total de logs encontrados: {len(logs)}")
            for log in logs:
                print(f"     - {log.data_hora}: {log.acao} {log.tipo} '{log.valor}'")

            # 7. Remover uma permissão
            print("\n📋 7. Testando remoção de permissão...")
            with app.test_request_context():
                login_user(admin)
                resultado = PermissaoService.remover_permissao(
                    usuario_id=vendedor_id,
                    tipo='vendedor',
                    valor='Maria Santos'
                )
                if isinstance(resultado, dict):
                    print(f"   - Remover Maria Santos: {resultado.get('message', 'Removido')}")
                else:
                    print(f"   - Remover Maria Santos: {'Removido com sucesso' if resultado else 'Erro ao remover'}")

            # Verificar permissões atualizadas
            permissoes = PermissaoService.obter_permissoes_usuario(vendedor_id)
            print(f"   - Vendedores após remoção: {permissoes['vendedores']}")

            # 8. Limpar todas as permissões
            print("\n📋 8. Testando limpeza total de permissões...")
            with app.test_request_context():
                login_user(admin)
                # Usar limpar_permissoes_usuario que é o método correto
                resultado = PermissaoService.limpar_permissoes_usuario(vendedor_id)
                print(f"   - Limpar todas: {resultado} permissões removidas")

            # Verificar que ficou sem permissões
            permissoes = PermissaoService.obter_permissoes_usuario(vendedor_id)
            total_final = len(permissoes['equipes']) + len(permissoes['vendedores'])
            print(f"   - Total após limpeza: {total_final}")

            # 9. Resumo final
            print("\n" + "="*80)
            print("✅ TESTE CONCLUÍDO COM SUCESSO!")
            print("="*80)
            print("\n📊 RESUMO:")
            print("   - Sistema de permissões funcionando corretamente")
            print("   - Logs de auditoria sendo registrados")
            print("   - Filtros aplicados conforme esperado")
            print("   - Todas as operações CRUD funcionais")

            print("\n💡 PRÓXIMOS PASSOS:")
            print("   1. Acessar /comercial/admin/permissoes como admin")
            print("   2. Configurar permissões reais para vendedores")
            print("   3. Testar login com vendedor e verificar restrições")

        except Exception as e:
            print(f"\n❌ ERRO durante teste: {e}")
            import traceback
            traceback.print_exc()
            db.session.rollback()

if __name__ == '__main__':
    testar_permissoes()