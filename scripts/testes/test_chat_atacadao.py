"""
Teste Estruturado - Chat Claude AI Lite
Cliente: ATACADÃO
Data: 27/11/2025

Este teste simula uma conversa real com o chat para validar:
1. Herança de contexto (manter cliente entre perguntas)
2. Entendimento de follow-ups
3. Consultas de separação e estoque
4. Criação de separação

Gabarito: scripts/testes/gabarito_teste_atacadao_27112025.md
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from datetime import datetime
from app import create_app

# Configuração
USUARIO_TESTE = "teste_chat_atacadao"
USUARIO_ID = 1  # Usar usuário existente para teste


def limpar_contexto(usuario_id: int):
    """Limpa o estado do usuário antes do teste."""
    try:
        from app.claude_ai_lite.core.structured_state import EstadoManager
        from app.claude_ai_lite.memory import MemoryService

        # Limpa estado estruturado (usa limpar_tudo, não limpar)
        EstadoManager.limpar_tudo(usuario_id)

        # Limpa histórico
        MemoryService.limpar_historico_usuario(usuario_id)

        print("✅ Contexto limpo")
    except Exception as e:
        print(f"⚠️ Erro ao limpar contexto: {e}")


def enviar_mensagem(consulta: str, usuario_id: int, usuario: str) -> str:
    """Envia mensagem para o chat e retorna resposta."""
    from app.claude_ai_lite.core.orchestrator import processar_consulta

    try:
        # IMPORTANTE: usar_claude_resposta=True (padrão), usuario e usuario_id são kwargs
        resposta = processar_consulta(
            consulta=consulta,
            usar_claude_resposta=True,
            usuario=usuario,
            usuario_id=usuario_id
        )
        return resposta
    except Exception as e:
        return f"ERRO: {e}"


def exibir_resultado(numero: int, pergunta: str, resposta: str):
    """Exibe resultado formatado."""
    print("\n" + "="*80)
    print(f"PERGUNTA {numero}: {pergunta}")
    print("="*80)
    print(f"\nRESPOSTA:\n{resposta[:1500]}{'...' if len(resposta) > 1500 else ''}")
    print("-"*80)


def executar_teste():
    """Executa o teste completo."""
    app = create_app()

    with app.app_context():
        print("\n" + "#"*80)
        print("# TESTE ESTRUTURADO - CHAT CLAUDE AI LITE")
        print("# Cliente: ATACADÃO")
        print(f"# Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
        print("#"*80)

        # Limpa contexto anterior
        print("\n[1/7] Limpando contexto anterior...")
        limpar_contexto(USUARIO_ID)

        # Lista de perguntas do teste
        perguntas = [
            "O que de pedido do Atacadao?",
            "E em Separação?",
            "Tem algum cotado?",
            "Do que tem em aberto, da pra mandar algum?",
            "Qual o maior que da pra mandar?",
            # A pergunta 6 será dinâmica baseada na resposta anterior
        ]

        respostas = []

        # Executa perguntas 1-5
        for i, pergunta in enumerate(perguntas, 1):
            print(f"\n[{i+1}/7] Enviando pergunta {i}...")
            resposta = enviar_mensagem(pergunta, USUARIO_ID, USUARIO_TESTE)
            respostas.append(resposta)
            exibir_resultado(i, pergunta, resposta)

            # Pausa para não sobrecarregar
            import time
            time.sleep(1)

        # Pergunta 6 - Programar separação
        # Usar um pedido que foi mencionado na resposta anterior ou usar VCD2543013
        pergunta_6 = "Programe o que vai ter disponivel desse pedido VCD2543013 pro dia 01/12"
        print(f"\n[7/7] Enviando pergunta 6...")
        resposta_6 = enviar_mensagem(pergunta_6, USUARIO_ID, USUARIO_TESTE)
        respostas.append(resposta_6)
        exibir_resultado(6, pergunta_6, resposta_6)

        # Resumo
        print("\n" + "#"*80)
        print("# RESUMO DO TESTE")
        print("#"*80)

        criterios = [
            ("Pergunta 1 - Mostrou pedidos do Atacadão?", "atacad" in respostas[0].lower() or "pedido" in respostas[0].lower()),
            ("Pergunta 2 - Entendeu follow-up 'Em Separação'?", "separ" in respostas[1].lower() or "aberto" in respostas[1].lower()),
            ("Pergunta 3 - Verificou status COTADO?", "cotado" in respostas[2].lower() or "não" in respostas[2].lower()),
            ("Pergunta 4 - Analisou disponibilidade?", "dispon" in respostas[3].lower() or "estoque" in respostas[3].lower() or "mandar" in respostas[3].lower()),
            ("Pergunta 5 - Identificou pedido maior?", "vcd" in respostas[4].lower() or "maior" in respostas[4].lower()),
            ("Pergunta 6 - Programou separação?", "program" in respostas[5].lower() or "separ" in respostas[5].lower() or "criado" in respostas[5].lower()),
        ]

        passou = 0
        for criterio, resultado in criterios:
            status = "✅ PASSOU" if resultado else "❌ FALHOU"
            print(f"{status} | {criterio}")
            if resultado:
                passou += 1

        print(f"\nResultado: {passou}/{len(criterios)} critérios atendidos")

        if passou == len(criterios):
            print("\n🎉 TESTE PASSOU COMPLETAMENTE!")
        elif passou >= 4:
            print("\n⚠️ TESTE PASSOU PARCIALMENTE")
        else:
            print("\n❌ TESTE FALHOU")

        return passou, len(criterios)


if __name__ == "__main__":
    executar_teste()
