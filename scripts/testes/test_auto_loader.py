"""
Teste do AutoLoader - Auto-geracao de loaders em tempo real.

Testa o fluxo completo:
1. Pergunta que nao tem capacidade
2. Sistema tenta auto-gerar loader
3. Executa e responde
4. Salva loader como pendente de revisao

Executar:
    python scripts/testes/test_auto_loader.py
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app


def test_auto_loader():
    """Testa o AutoLoader com pergunta real."""
    app = create_app()

    with app.app_context():
        print("=" * 70)
        print("TESTE DO AUTO-LOADER")
        print("=" * 70)
        print()

        # Simula uma intencao classificada
        intencao = {
            "dominio": "carteira",
            "intencao": "buscar_pedido_sem_agendamento",  # Intencao que nao existe
            "entidades": {
                "cliente": "Assai"
            },
            "confianca": 0.6
        }

        consulta = "Há pedidos do cliente Assai sem agendamento?"

        print(f"CONSULTA: {consulta}")
        print(f"INTENCAO DETECTADA: {intencao}")
        print()

        # Teste 1: Verifica elegibilidade
        print("1. VERIFICANDO ELEGIBILIDADE")
        print("-" * 50)
        from app.claude_ai_lite.ia_trainer.services.auto_loader import AutoLoaderService

        service = AutoLoaderService()
        elegivel = service._pergunta_elegivel(consulta, intencao)
        print(f"   Elegivel para auto-geracao: {elegivel}")
        print()

        if not elegivel:
            print("   Pergunta nao elegivel. Teste encerrado.")
            return

        # Teste 2: Gera decomposicao automatica
        print("2. GERANDO DECOMPOSICAO AUTOMATICA")
        print("-" * 50)
        decomposicao = service._gerar_decomposicao_automatica(consulta, intencao)
        for i, parte in enumerate(decomposicao, 1):
            print(f"   {i}. {parte.get('parte', '')[:50]}")
            print(f"      Tipo: {parte.get('tipo')} | Campo: {parte.get('campo')}")
        print()

        # Teste 3: Tenta responder automaticamente
        print("3. TENTANDO RESPONDER AUTOMATICAMENTE")
        print("-" * 50)
        print("   (Isso vai chamar a API Claude para gerar o loader...)")
        print()

        resultado = service.tentar_responder(
            consulta=consulta,
            intencao=intencao,
            usuario_id=1,
            usuario="teste_auto_loader"
        )

        print(f"   Sucesso: {resultado.get('sucesso')}")
        print(f"   Experimental: {resultado.get('experimental')}")
        print(f"   Loader ID: {resultado.get('loader_id')}")

        if resultado.get('erro'):
            print(f"   Erro: {resultado.get('erro')}")

        if resultado.get('resposta'):
            print()
            print("   RESPOSTA GERADA:")
            print("   " + "-" * 40)
            for linha in resultado['resposta'].split('\n')[:15]:
                print(f"   {linha}")
            if len(resultado['resposta'].split('\n')) > 15:
                print("   ...")

        print()
        print("=" * 70)

        # Teste 4: Verifica se loader foi salvo
        if resultado.get('loader_id'):
            print("4. VERIFICANDO LOADER SALVO")
            print("-" * 50)
            from app.claude_ai_lite.ia_trainer.models import CodigoSistemaGerado

            loader = CodigoSistemaGerado.query.get(resultado['loader_id'])
            if loader:
                print(f"   Nome: {loader.nome}")
                print(f"   Tipo: {loader.tipo_codigo}")
                print(f"   Ativo: {loader.ativo}")
                print(f"   Criado por: {loader.criado_por}")
                print(f"   Gatilhos: {loader.gatilhos}")
                print()
                print("   Definicao tecnica (primeiros 200 chars):")
                print(f"   {str(loader.definicao_tecnica)[:200]}...")

        print()
        print("=" * 70)
        print("TESTE CONCLUIDO")
        print("=" * 70)


def test_fluxo_orchestrator():
    """Testa o fluxo completo via Orchestrator."""
    app = create_app()

    with app.app_context():
        print()
        print("=" * 70)
        print("TESTE DO FLUXO COMPLETO VIA ORCHESTRATOR")
        print("=" * 70)
        print()

        from app.claude_ai_lite.core.orchestrator import processar_consulta

        consulta = "Quais pedidos do cliente Atacadao estao sem agendamento?"

        print(f"CONSULTA: {consulta}")
        print()
        print("Processando...")
        print()

        resposta = processar_consulta(
            consulta=consulta,
            usar_claude_resposta=False,  # Nao elabora com Claude, so retorna dados
            usuario="teste",
            usuario_id=1
        )

        print("RESPOSTA:")
        print("-" * 50)
        print(resposta[:1000] if len(resposta) > 1000 else resposta)

        print()
        print("=" * 70)
        print("TESTE CONCLUIDO")
        print("=" * 70)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--orchestrator', action='store_true', help='Testa via orchestrator')
    args = parser.parse_args()

    if args.orchestrator:
        test_fluxo_orchestrator()
    else:
        test_auto_loader()
