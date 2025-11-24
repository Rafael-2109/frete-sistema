"""
Teste do fluxo completo do Orchestrator com AutoLoader.

Simula uma consulta que NAO tem capacidade e deve:
1. Tentar loaders aprendidos (nenhum)
2. Tentar auto-gerar loader
3. Retornar resposta experimental

Roda: python scripts/testes/test_orchestrator_autoloader.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

import logging

# Configura logging detalhado
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s - %(name)s - %(message)s'
)

# Reduz ruido de outros modulos
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('anthropic').setLevel(logging.WARNING)

from app import create_app

app = create_app()


def testar_orchestrator():
    print("=" * 70)
    print("TESTE DO ORCHESTRATOR COM AUTO-LOADER")
    print("=" * 70)
    print()

    with app.app_context():
        from app.claude_ai_lite.core.orchestrator import processar_consulta
        from app.claude_ai_lite.core.classifier import get_classifier
        from app.claude_ai_lite.capabilities import find_capability

        consulta = "Há pedidos do cliente Assai sem agendamento?"

        print(f"CONSULTA: {consulta}")
        print()

        # 1. Verifica classificacao
        print("1. CLASSIFICAÇÃO DA INTENÇÃO")
        print("-" * 50)
        classifier = get_classifier()
        intencao = classifier.classificar(consulta, None)
        print(f"   Dominio: {intencao.get('dominio')}")
        print(f"   Intencao: {intencao.get('intencao')}")
        print(f"   Entidades: {intencao.get('entidades')}")
        print(f"   Confianca: {intencao.get('confianca')}")
        print()

        # 2. Verifica se tem capacidade
        print("2. BUSCA DE CAPACIDADE")
        print("-" * 50)
        intencao_tipo = intencao.get('intencao', '')
        entidades = intencao.get('entidades', {})
        capacidade = find_capability(intencao_tipo, entidades)

        if capacidade:
            print(f"   ENCONTRADA: {capacidade.NOME}")
            print(f"   Dominio: {capacidade.DOMINIO}")
            print(f"   Isso NAO deveria acontecer - a pergunta deveria ir para o auto-loader")
        else:
            print("   Nenhuma capacidade encontrada")
            print("   OK! Deveria ir para _tratar_sem_capacidade")
        print()

        # 3. Testa _tratar_sem_capacidade diretamente
        print("3. TESTANDO _tratar_sem_capacidade DIRETAMENTE")
        print("-" * 50)
        from app.claude_ai_lite.core.orchestrator import _tratar_sem_capacidade

        try:
            resposta_sem_cap = _tratar_sem_capacidade(
                consulta=consulta,
                intencao=intencao,
                usuario_id=1,
                usuario="teste"
            )
            print(f"   Resposta obtida ({len(resposta_sem_cap)} chars):")
            print()
            # Mostra primeiros 500 chars
            preview = resposta_sem_cap[:500]
            for linha in preview.split('\n'):
                print(f"   {linha}")
            if len(resposta_sem_cap) > 500:
                print(f"   ... ({len(resposta_sem_cap) - 500} chars restantes)")
        except Exception as e:
            print(f"   ERRO: {e}")
            import traceback
            traceback.print_exc()
        print()

        # 4. Testa processar_consulta completo
        print("4. TESTANDO processar_consulta COMPLETO")
        print("-" * 50)

        try:
            resposta_completa = processar_consulta(
                consulta=consulta,
                usar_claude_resposta=True,
                usuario="teste",
                usuario_id=1
            )
            print(f"   Resposta obtida ({len(resposta_completa)} chars):")
            print()
            # Mostra resposta completa se nao for muito grande
            if len(resposta_completa) < 2000:
                for linha in resposta_completa.split('\n'):
                    print(f"   {linha}")
            else:
                preview = resposta_completa[:1000]
                for linha in preview.split('\n'):
                    print(f"   {linha}")
                print(f"   ... ({len(resposta_completa) - 1000} chars restantes)")

            # Verifica se eh experimental
            if "[Resposta experimental" in resposta_completa:
                print()
                print("   >>> SUCESSO: Resposta veio do AUTO-LOADER <<<")
            elif "Desculpe" in resposta_completa or "ainda não consigo" in resposta_completa:
                print()
                print("   >>> FALHA: Resposta foi sugestao (auto-loader nao funcionou) <<<")
            elif "Não consegui" in resposta_completa:
                print()
                print("   >>> FALHA: Resposta foi fallback (sem criterio) <<<")

        except Exception as e:
            print(f"   ERRO: {e}")
            import traceback
            traceback.print_exc()

        print()
        print("=" * 70)
        print("TESTE CONCLUIDO")
        print("=" * 70)


if __name__ == '__main__':
    testar_orchestrator()
