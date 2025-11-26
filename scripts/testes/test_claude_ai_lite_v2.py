"""
Teste da nova arquitetura do Claude AI Lite v3.5.2+

Executa dentro do contexto Flask para testar:
1. Carregamento de capacidades
2. Registry automático com consulta_generica
3. Entity Mapper
4. Capacidade Genérica
5. Fluxo completo (opcional)

Execute: python scripts/testes/test_claude_ai_lite_v2.py [--completo]
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app

app = create_app()

with app.app_context():
    print("=" * 60)
    print("TESTE: Claude AI Lite v3.5.2+ - Consulta Genérica")
    print("=" * 60)
    print()

    # 1. Testa imports básicos
    print("1. Testando imports básicos...")
    try:
        from app.claude_ai_lite import processar_consulta, get_all_capabilities, find_capability
        print("   ✅ imports funcionando")
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        sys.exit(1)

    # 2. Testa carregamento de capacidades
    print("\n2. Testando carregamento de capacidades...")
    try:
        caps = get_all_capabilities()
        print(f"   ✅ {len(caps)} capacidades carregadas")
        for cap in caps:
            print(f"      - {cap.NOME} ({cap.DOMINIO}) [{cap.TIPO}]")
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        import traceback
        traceback.print_exc()

    # 3. Verifica se consulta_generica foi carregada
    print("\n3. Verificando capacidade consulta_generica...")
    try:
        from app.claude_ai_lite.capabilities import get_capability
        cap_gen = get_capability('consulta_generica')
        if cap_gen:
            print(f"   ✅ consulta_generica encontrada: {cap_gen.DESCRICAO}")
        else:
            print("   ❌ consulta_generica NÃO encontrada!")
    except Exception as e:
        print(f"   ❌ ERRO: {e}")

    # 4. Testa entity_mapper com consulta genérica
    print("\n4. Testando entity_mapper com tipo 'consulta_generica'...")
    try:
        from app.claude_ai_lite.core.entity_mapper import mapear_extracao

        extracao_simulada = {
            'intencao': 'consultar_pedidos_novos',
            'tipo': 'consulta_generica',
            'entidades': {
                'tabela': 'CarteiraPrincipal',
                'campo_filtro': 'data_pedido',
                'data_inicio': '2025-11-24',
                'data_fim': '2025-11-25'
            },
            'confianca': 0.9
        }

        resultado = mapear_extracao(extracao_simulada)
        print(f"   Domínio: {resultado.get('dominio')}")
        print(f"   Intenção: {resultado.get('intencao')}")

        if resultado.get('dominio') == 'carteira' and resultado.get('intencao') == 'consulta_generica':
            print("   ✅ Mapeamento correto!")
        else:
            print("   ❌ Mapeamento incorreto!")
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        import traceback
        traceback.print_exc()

    # 5. Testa find_capability com consulta genérica
    print("\n5. Testando find_capability para consulta genérica...")
    try:
        entidades_gen = {
            'tabela': 'CarteiraPrincipal',
            'data_inicio': 'ontem',
            'data_fim': 'hoje'
        }

        cap_encontrada = find_capability('consulta_generica', entidades_gen)
        if cap_encontrada:
            print(f"   ✅ Capacidade encontrada: {cap_encontrada.NOME}")
        else:
            print("   ❌ Capacidade NÃO encontrada como fallback!")
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        import traceback
        traceback.print_exc()

    # 6. Testa execução da capacidade genérica
    print("\n6. Testando execução da capacidade genérica...")
    try:
        from app.claude_ai_lite.capabilities.carteira.consulta_generica import ConsultaGenericaCapability

        cap = ConsultaGenericaCapability()
        entidades = {
            'tabela': 'CarteiraPrincipal',
            'campo_filtro': 'data_pedido',
            'data_inicio': 'ontem',
            'data_fim': 'hoje'
        }

        resultado = cap.executar(entidades, {})
        print(f"   Sucesso: {resultado.get('sucesso')}")
        print(f"   Total: {resultado.get('total', 0)}")

        if resultado.get('sucesso'):
            print("   ✅ Execução bem sucedida!")
            if resultado.get('dados'):
                print(f"   Primeiros resultados:")
                for item in resultado.get('dados', [])[:3]:
                    print(f"      - {item}")
        else:
            print(f"   ⚠️ Erro: {resultado.get('erro')}")
    except Exception as e:
        print(f"   ❌ ERRO: {e}")
        import traceback
        traceback.print_exc()

    # 7. Testa fluxo completo (se --completo passado)
    if '--completo' in sys.argv:
        print("\n7. Testando fluxo COMPLETO (com API Claude)...")
        try:
            from app.claude_ai_lite.core.orchestrator import processar_consulta as proc

            consultas = [
                "O que entrou de pedido ontem e hoje?",
                "Pedidos novos",
            ]

            for consulta in consultas:
                print(f"\n   📝 Consulta: {consulta}")
                resposta = proc(
                    consulta=consulta,
                    usar_claude_resposta=True,
                    usuario="Teste",
                    usuario_id=1
                )
                print(f"   🤖 Resposta:")
                print("-" * 40)
                # Mostra primeiras 500 chars da resposta
                print(resposta[:500] if len(resposta) > 500 else resposta)
                print("-" * 40)

        except Exception as e:
            print(f"   ❌ ERRO: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n7. Teste de fluxo completo PULADO (use --completo para executar)")

    print("\n" + "=" * 60)
    print("TESTE CONCLUÍDO!")
    print("=" * 60)
    print("\nPara testar fluxo completo com API Claude:")
    print("  python scripts/testes/test_claude_ai_lite_v2.py --completo")
