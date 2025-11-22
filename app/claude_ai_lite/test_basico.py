"""
Teste da estrutura modular Claude AI Lite.
Execute: python -m app.claude_ai_lite.test_basico
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))


def testar_dominios():
    """Verifica dominios registrados."""
    from app.claude_ai_lite.domains import listar_dominios

    print("=== DOMINIOS REGISTRADOS ===")
    dominios = listar_dominios()
    print(f"Disponiveis: {dominios}")
    assert "carteira" in dominios, "Dominio carteira nao registrado!"
    print("OK\n")


def testar_loader_carteira():
    """Testa loader do dominio carteira."""
    from app.claude_ai_lite.domains import get_loader

    print("=== LOADER CARTEIRA ===")
    loader_class = get_loader("carteira")
    assert loader_class is not None, "Loader carteira nao encontrado!"

    loader = loader_class()
    print(f"Dominio: {loader.DOMINIO}")
    print(f"Campos: {loader.CAMPOS_BUSCA}")

    # Testa busca
    resultado = loader.buscar("VCD2509030", "num_pedido")
    print(f"Busca VCD2509030: {resultado['total_encontrado']} encontrado(s)")
    assert resultado["sucesso"], f"Erro: {resultado.get('erro')}"
    print("OK\n")


def testar_consulta_completa():
    """Testa fluxo completo."""
    from app.claude_ai_lite import processar_consulta

    print("=== CONSULTA COMPLETA ===")
    resposta = processar_consulta("Pedido VCD2509030 tem separacao?")
    print(f"Resposta ({len(resposta)} chars):")
    print(resposta[:300] + "..." if len(resposta) > 300 else resposta)
    assert len(resposta) > 50, "Resposta muito curta!"
    print("OK\n")


def testar_consulta_sem_claude():
    """Testa consulta sem usar Claude na resposta."""
    from app.claude_ai_lite.core import processar_consulta

    print("=== CONSULTA SEM CLAUDE (RAPIDO) ===")
    resposta = processar_consulta("Pedido VCD2509030?", usar_claude_resposta=False)
    print(resposta[:200] + "...")
    print("OK\n")


if __name__ == '__main__':
    from app import create_app

    print("=" * 60)
    print("TESTE CLAUDE AI LITE - ESTRUTURA MODULAR")
    print("=" * 60 + "\n")

    app = create_app()
    with app.app_context():
        testar_dominios()
        testar_loader_carteira()
        testar_consulta_sem_claude()
        testar_consulta_completa()

    print("=" * 60)
    print("TODOS OS TESTES PASSARAM!")
    print("=" * 60)
