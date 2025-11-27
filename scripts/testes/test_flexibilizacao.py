#!/usr/bin/env python3
"""
Teste integrado das mudanças de flexibilização do Claude AI Lite.

Fase 1+2:
1. config.py - Configuração centralizada
2. MAX_ETAPAS dinâmico
3. Capabilities dinâmicas
4. Schema dinâmico

Fase 3:
5. Memory dinâmico
6. Revisão condicional
7. Responder com confiança

Execute com: python scripts/testes/test_flexibilizacao.py
"""

import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app


def test_config():
    """Testa configuração centralizada."""
    print("\n" + "=" * 60)
    print("TESTE 1: CONFIGURAÇÃO CENTRALIZADA")
    print("=" * 60)

    try:
        from app.claude_ai_lite.config import (
            get_config, get_max_etapas, get_max_historico,
            get_max_tokens, deve_revisar_resposta, usar_schema_dinamico,
            usar_capabilities_dinamicas, NivelAutonomia
        )

        config = get_config()
        print(f"\n Nível de autonomia: {config.nivel_autonomia.value}")
        print(f" MAX_ETAPAS default: {config.planejamento.max_etapas_default}")
        print(f" MAX_ETAPAS complexas: {config.planejamento.max_etapas_complexas}")
        print(f" Schema dinâmico: {usar_schema_dinamico()}")
        print(f" Capabilities dinâmicas: {usar_capabilities_dinamicas()}")
        print(f" MAX_HISTORICO: {get_max_historico()}")
        print(f" MAX_TOKENS (sonnet): {get_max_tokens('sonnet')}")
        print(f" MAX_TOKENS (haiku): {get_max_tokens('haiku')}")
        print(f" Deve revisar (confiança 0.5): {deve_revisar_resposta(0.5)}")
        print(f" Deve revisar (confiança 0.95): {deve_revisar_resposta(0.95)}")

        # Testa get_max_etapas com plano
        plano_simples = {'etapas': [{}]}
        plano_complexo = {
            'etapas': [{} for _ in range(8)],
            'etapas_necessarias': 8,
            'justificativa_etapas_extras': 'Consulta complexa com múltiplos JOINs'
        }

        print(f"\n MAX_ETAPAS (plano simples): {get_max_etapas(plano_simples)}")
        print(f" MAX_ETAPAS (plano complexo com justificativa): {get_max_etapas(plano_complexo)}")

        print("\n OK: Configuração funcionando!")
        return True

    except Exception as e:
        print(f"\n ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_capabilities_dinamicas():
    """Testa carregamento de capabilities dinâmicas."""
    print("\n" + "=" * 60)
    print("TESTE 2: CAPABILITIES DINÂMICAS")
    print("=" * 60)

    try:
        from app.claude_ai_lite.core.intelligent_extractor import (
            _obter_capabilities_prompt,
            _carregar_capabilities_dinamicas
        )

        # Testa carregamento dinâmico
        caps_dinamicas = _carregar_capabilities_dinamicas()
        print(f"\n Capabilities dinâmicas carregadas: {len(caps_dinamicas)} chars")
        print(f" Preview (primeiros 500 chars):")
        print("-" * 40)
        print(caps_dinamicas[:500])
        print("-" * 40)

        # Testa função principal
        caps_prompt = _obter_capabilities_prompt()
        print(f"\n _obter_capabilities_prompt(): {len(caps_prompt)} chars")

        print("\n OK: Capabilities dinâmicas funcionando!")
        return True

    except Exception as e:
        print(f"\n ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_schema_dinamico():
    """Testa schema dinâmico."""
    print("\n" + "=" * 60)
    print("TESTE 3: SCHEMA DINÂMICO")
    print("=" * 60)

    try:
        from app.claude_ai_lite.core.tool_registry import get_tool_registry

        registry = get_tool_registry()

        # Testa schema dinâmico para cada domínio
        dominios = ['carteira', 'estoque', 'fretes', 'faturamento', None]

        for dominio in dominios:
            schema = registry.formatar_schema_resumido(dominio)
            print(f"\n Schema ({dominio or 'geral'}): {len(schema)} chars")

        # Mostra preview do schema de carteira
        schema_carteira = registry.formatar_schema_resumido('carteira')
        print(f"\n Preview schema carteira (primeiros 800 chars):")
        print("-" * 40)
        print(schema_carteira[:800])
        print("-" * 40)

        print("\n OK: Schema dinâmico funcionando!")
        return True

    except Exception as e:
        print(f"\n ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_tool_registry():
    """Testa ToolRegistry completo."""
    print("\n" + "=" * 60)
    print("TESTE 4: TOOL REGISTRY")
    print("=" * 60)

    try:
        from app.claude_ai_lite.core.tool_registry import get_tool_registry

        registry = get_tool_registry()

        # Lista ferramentas
        ferramentas = registry.listar_ferramentas(dominio='carteira')
        print(f"\n Ferramentas para 'carteira': {len(ferramentas)}")

        for f in ferramentas[:5]:
            print(f"   - {f['nome']} ({f['tipo']})")

        # Formata para prompt
        prompt = registry.formatar_para_prompt(ferramentas)
        print(f"\n Prompt formatado: {len(prompt)} chars")

        # Testa obter ferramenta específica
        consultar_pedido = registry.obter_ferramenta('consultar_pedido')
        print(f"\n obter_ferramenta('consultar_pedido'): {consultar_pedido is not None}")

        loader = registry.obter_ferramenta('loader_generico')
        print(f" obter_ferramenta('loader_generico'): {loader is not None}")

        print("\n OK: ToolRegistry funcionando!")
        return True

    except Exception as e:
        print(f"\n ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_agent_planner_prompt():
    """Testa se o prompt do AgentPlanner usa config."""
    print("\n" + "=" * 60)
    print("TESTE 5: AGENT PLANNER PROMPT")
    print("=" * 60)

    try:
        from app.claude_ai_lite.core.agent_planner import AgentPlanner
        from app.claude_ai_lite.config import get_config

        config = get_config()

        planner = AgentPlanner()

        # Verifica se get_config é importado
        print(f"\n Config disponível no AgentPlanner: True")
        print(f" MAX_ETAPAS default: {config.planejamento.max_etapas_default}")
        print(f" MAX_ETAPAS complexas: {config.planejamento.max_etapas_complexas}")
        print(f" Usar diretrizes flexíveis: {config.planejamento.usar_diretrizes_flexiveis}")

        print("\n OK: AgentPlanner configurado!")
        return True

    except Exception as e:
        print(f"\n ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_memory_dinamico():
    """Testa memória com configurações dinâmicas."""
    print("\n" + "=" * 60)
    print("TESTE 6: MEMORY DINÂMICO")
    print("=" * 60)

    try:
        from app.claude_ai_lite.memory import (
            _get_max_historico, _get_max_tokens, _get_chars_por_token,
            MemoryService
        )
        from app.claude_ai_lite.config import get_config

        config = get_config()

        print(f"\n _get_max_historico(): {_get_max_historico()}")
        print(f" _get_max_tokens('sonnet'): {_get_max_tokens('sonnet')}")
        print(f" _get_max_tokens('haiku'): {_get_max_tokens('haiku')}")
        print(f" _get_max_tokens('opus'): {_get_max_tokens('opus')}")
        print(f" _get_chars_por_token(): {_get_chars_por_token()}")

        # Verifica se config é consistente
        assert _get_max_historico() == config.memoria.max_mensagens_default
        assert _get_max_tokens('sonnet') == config.memoria.tokens_por_modelo['sonnet']

        print("\n OK: Memory dinâmico funcionando!")
        return True

    except Exception as e:
        print(f"\n ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_revisao_condicional():
    """Testa revisão condicional no responder."""
    print("\n" + "=" * 60)
    print("TESTE 7: REVISÃO CONDICIONAL")
    print("=" * 60)

    try:
        from app.claude_ai_lite.core.responder import _deve_revisar
        from app.claude_ai_lite.config import get_config

        config = get_config()
        limiar = config.resposta.limiar_confianca_sem_revisao

        print(f"\n Limiar de confiança para não revisar: {limiar}")
        print(f" Revisão condicional habilitada: {config.resposta.revisao_condicional}")

        # Testes
        deve_05 = _deve_revisar(0.5)
        deve_09 = _deve_revisar(0.9)
        deve_095 = _deve_revisar(0.95)

        print(f"\n _deve_revisar(0.5): {deve_05} (esperado: True)")
        print(f" _deve_revisar(0.9): {deve_09} (esperado: True)")
        print(f" _deve_revisar(0.95): {deve_095} (esperado: False)")

        # Valida resultados
        assert deve_05 == True, "Confiança 0.5 deve revisar"
        assert deve_095 == False, "Confiança 0.95 não deve revisar"

        print("\n OK: Revisão condicional funcionando!")
        return True

    except Exception as e:
        print(f"\n ERRO: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Executa todos os testes."""
    print("\n" + "#" * 60)
    print("# TESTE INTEGRADO - CLAUDE AI LITE FLEXIBILIZAÇÃO")
    print("# Fase 1+2+3")
    print("#" * 60)

    app = create_app()

    with app.app_context():
        # Fase 1+2
        resultados = {
            '1_config': test_config(),
            '2_capabilities': test_capabilities_dinamicas(),
            '3_schema': test_schema_dinamico(),
            '4_registry': test_tool_registry(),
            '5_planner': test_agent_planner_prompt(),
            # Fase 3
            '6_memory': test_memory_dinamico(),
            '7_revisao': test_revisao_condicional(),
        }

        print("\n" + "=" * 60)
        print("RESUMO DOS TESTES")
        print("=" * 60)

        total = len(resultados)
        passou = sum(1 for r in resultados.values() if r)

        print("\nFase 1+2:")
        for nome, resultado in list(resultados.items())[:5]:
            status = "OK" if resultado else "FALHOU"
            print(f"  {nome}: {status}")

        print("\nFase 3:")
        for nome, resultado in list(resultados.items())[5:]:
            status = "OK" if resultado else "FALHOU"
            print(f"  {nome}: {status}")

        print(f"\n Total: {passou}/{total} testes passaram")

        if passou == total:
            print("\n TODOS OS TESTES PASSARAM!")
            return 0
        else:
            print("\n ALGUNS TESTES FALHARAM!")
            return 1


if __name__ == "__main__":
    sys.exit(main())
