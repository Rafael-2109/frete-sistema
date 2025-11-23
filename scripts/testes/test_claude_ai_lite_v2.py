"""
Teste da nova arquitetura do Claude AI Lite v2.0

Executa dentro do contexto Flask para testar:
1. Carregamento de capacidades
2. Registry automático
3. Classificador
4. Orchestrator
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app

app = create_app()

with app.app_context():
    print("=" * 60)
    print("TESTE: Claude AI Lite v2.0 - Nova Arquitetura")
    print("=" * 60)
    print()

    # 1. Testa imports básicos
    print("1. Testando imports básicos...")
    try:
        from app.claude_ai_lite import processar_consulta, get_all_capabilities, find_capability
        print("   OK: imports funcionando")
    except Exception as e:
        print(f"   ERRO: {e}")
        sys.exit(1)

    # 2. Testa carregamento de capacidades
    print("\n2. Testando carregamento de capacidades...")
    try:
        caps = get_all_capabilities()
        print(f"   OK: {len(caps)} capacidades carregadas")
        for cap in caps:
            print(f"      - {cap.NOME} ({cap.DOMINIO}) [{cap.TIPO}]")
            print(f"        Intenções: {', '.join(cap.INTENCOES[:3])}")
    except Exception as e:
        print(f"   ERRO: {e}")
        import traceback
        traceback.print_exc()

    # 3. Testa find_capability
    print("\n3. Testando find_capability...")
    try:
        cap = find_capability('consultar_status', {'num_pedido': 'VCD123'})
        if cap:
            print(f"   OK: consultar_status -> {cap.NOME}")
        else:
            print("   AVISO: Nenhuma capacidade encontrada para consultar_status")

        cap2 = find_capability('analisar_disponibilidade', {'num_pedido': 'VCD456'})
        if cap2:
            print(f"   OK: analisar_disponibilidade -> {cap2.NOME}")
        else:
            print("   AVISO: Nenhuma capacidade encontrada para analisar_disponibilidade")

        cap3 = find_capability('consultar_estoque', {'produto': 'azeitona'})
        if cap3:
            print(f"   OK: consultar_estoque -> {cap3.NOME}")
        else:
            print("   AVISO: Nenhuma capacidade encontrada para consultar_estoque")
    except Exception as e:
        print(f"   ERRO: {e}")
        import traceback
        traceback.print_exc()

    # 4. Testa prompts
    print("\n4. Testando geração de prompts...")
    try:
        from app.claude_ai_lite.prompts import gerar_prompt_classificacao
        prompt = gerar_prompt_classificacao()
        print(f"   OK: Prompt gerado ({len(prompt)} caracteres)")
        print(f"   Primeiras 200 chars: {prompt[:200]}...")
    except Exception as e:
        print(f"   ERRO: {e}")
        import traceback
        traceback.print_exc()

    # 5. Testa classifier (sem chamar API)
    print("\n5. Testando estrutura do classifier...")
    try:
        from app.claude_ai_lite.core.classifier import IntentClassifier
        print("   OK: IntentClassifier importado")
    except Exception as e:
        print(f"   ERRO: {e}")
        import traceback
        traceback.print_exc()

    # 6. Testa orchestrator
    print("\n6. Testando estrutura do orchestrator...")
    try:
        from app.claude_ai_lite.core.orchestrator import processar_consulta as proc
        print("   OK: orchestrator importado")
    except Exception as e:
        print(f"   ERRO: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("TESTE CONCLUÍDO!")
    print("=" * 60)
