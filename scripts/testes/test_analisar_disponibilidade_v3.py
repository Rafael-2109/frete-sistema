#!/usr/bin/env python3
"""
Teste do capability analisar_disponibilidade v3.0

Testa as novas funcionalidades:
- Consulta por DATA futura
- Filtros combinados
- Novas intenções
"""

import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app

app = create_app()


def test_pode_processar():
    """Testa se o método pode_processar captura os casos corretos."""
    from app.claude_ai_lite.capabilities.carteira.analisar_disponibilidade import AnalisarDisponibilidadeCapability

    cap = AnalisarDisponibilidadeCapability()

    casos_teste = [
        # (intencao, entidades, esperado, descricao)
        ("analisar_disponibilidade", {"raz_social_red": "ATACADAO"}, True, "Intenção direta com cliente"),
        ("disponibilidade_por_data", {"data": "2025-12-01"}, True, "Por data"),
        ("montar_carga", {"cliente": "ASSAI", "quantidade": 28}, True, "Montar carga com quantidade"),
        ("consultar_prazo", {}, False, "Sem entidades - deve falhar"),
        ("outro_qualquer", {"raz_social_red": "CARREFOUR"}, False, "Intenção desconhecida sem palavra-chave"),
        ("quando posso enviar 28 pallets pro atacadao", {"raz_social_red": "ATACADAO", "quantidade": 28}, True, "Consulta natural"),
        ("o que tem disponível pro rs", {"cod_uf": "RS"}, True, "Por UF"),
        ("quais produtos terão estoque no dia 01/12", {"data": "2025-12-01", "raz_social_red": "ATACADAO"}, True, "Por data futura"),
    ]

    print("\n" + "=" * 60)
    print("TESTE: pode_processar()")
    print("=" * 60)

    for intencao, entidades, esperado, descricao in casos_teste:
        resultado = cap.pode_processar(intencao, entidades)
        status = "✅" if resultado == esperado else "❌"
        print(f"{status} [{descricao}]")
        print(f"   Intenção: {intencao}")
        print(f"   Entidades: {entidades}")
        print(f"   Esperado: {esperado}, Obtido: {resultado}")
        print()


def test_extrair_data():
    """Testa extração de datas das entidades."""
    from app.claude_ai_lite.capabilities.carteira.analisar_disponibilidade import AnalisarDisponibilidadeCapability
    from datetime import date

    cap = AnalisarDisponibilidadeCapability()

    casos_teste = [
        ({"data": "2025-12-01"}, date(2025, 12, 1), "Formato ISO"),
        ({"data": "01/12/2025"}, date(2025, 12, 1), "Formato BR"),
        ({"data_disponibilidade": "2025-12-15"}, date(2025, 12, 15), "Campo data_disponibilidade"),
        ({"expedicao": "2025-11-30"}, date(2025, 11, 30), "Campo expedicao"),
        ({}, None, "Sem data"),
        ({"data": "invalido"}, None, "Data inválida"),
    ]

    print("\n" + "=" * 60)
    print("TESTE: _extrair_data()")
    print("=" * 60)

    for entidades, esperado, descricao in casos_teste:
        resultado = cap._extrair_data(entidades)
        status = "✅" if resultado == esperado else "❌"
        print(f"{status} [{descricao}]")
        print(f"   Entidades: {entidades}")
        print(f"   Esperado: {esperado}, Obtido: {resultado}")
        print()


def test_execucao_cliente():
    """Testa execução com cliente real (se houver dados)."""
    from app.claude_ai_lite.capabilities.carteira.analisar_disponibilidade import AnalisarDisponibilidadeCapability

    cap = AnalisarDisponibilidadeCapability()

    print("\n" + "=" * 60)
    print("TESTE: executar() - Análise por cliente")
    print("=" * 60)

    # Teste com cliente genérico
    entidades = {"raz_social_red": "ATACADAO"}
    contexto = {"consulta": "O que tem disponível do Atacadão?"}

    with app.app_context():
        resultado = cap.executar(entidades, contexto)

        print(f"Sucesso: {resultado.get('sucesso')}")
        print(f"Tipo consulta: {resultado.get('tipo_consulta')}")
        print(f"Total encontrado: {resultado.get('total_encontrado')}")

        if resultado.get('erro'):
            print(f"Erro: {resultado.get('erro')}")

        if resultado.get('analise'):
            print("\nAnálise:")
            for k, v in resultado['analise'].items():
                print(f"  {k}: {v}")


def test_execucao_data_futura():
    """Testa consulta por data futura."""
    from app.claude_ai_lite.capabilities.carteira.analisar_disponibilidade import AnalisarDisponibilidadeCapability
    from datetime import date, timedelta

    cap = AnalisarDisponibilidadeCapability()

    print("\n" + "=" * 60)
    print("TESTE: executar() - Disponibilidade por data futura")
    print("=" * 60)

    # Data 3 dias no futuro
    data_futura = (date.today() + timedelta(days=3)).strftime("%Y-%m-%d")

    entidades = {
        "raz_social_red": "ATACADAO",
        "data": data_futura
    }
    contexto = {"consulta": f"Quais produtos do Atacadão terão estoque no dia {data_futura}?"}

    with app.app_context():
        resultado = cap.executar(entidades, contexto)

        print(f"Sucesso: {resultado.get('sucesso')}")
        print(f"Tipo consulta: {resultado.get('tipo_consulta')}")
        print(f"Total encontrado: {resultado.get('total_encontrado')}")
        print(f"Data alvo: {resultado.get('data_alvo')}")

        if resultado.get('erro'):
            print(f"Erro: {resultado.get('erro')}")

        if resultado.get('analise'):
            print("\nAnálise:")
            for k, v in resultado['analise'].items():
                print(f"  {k}: {v}")


def test_execucao_uf():
    """Testa consulta por UF."""
    from app.claude_ai_lite.capabilities.carteira.analisar_disponibilidade import AnalisarDisponibilidadeCapability

    cap = AnalisarDisponibilidadeCapability()

    print("\n" + "=" * 60)
    print("TESTE: executar() - Disponibilidade por UF")
    print("=" * 60)

    entidades = {"cod_uf": "SP"}
    contexto = {"consulta": "O que tem pra mandar pro SP?"}

    with app.app_context():
        resultado = cap.executar(entidades, contexto)

        print(f"Sucesso: {resultado.get('sucesso')}")
        print(f"Tipo consulta: {resultado.get('tipo_consulta')}")
        print(f"Total encontrado: {resultado.get('total_encontrado')}")
        print(f"UF: {resultado.get('uf')}")

        if resultado.get('erro'):
            print(f"Erro: {resultado.get('erro')}")

        if resultado.get('analise'):
            print("\nAnálise:")
            for k, v in resultado['analise'].items():
                print(f"  {k}: {v}")


def test_formatacao():
    """Testa formatação do contexto."""
    from app.claude_ai_lite.capabilities.carteira.analisar_disponibilidade import AnalisarDisponibilidadeCapability

    cap = AnalisarDisponibilidadeCapability()

    print("\n" + "=" * 60)
    print("TESTE: formatar_contexto()")
    print("=" * 60)

    # Mock de resultado
    resultado = {
        "sucesso": True,
        "tipo_consulta": "disponibilidade_por_data",
        "total_encontrado": 3,
        "cliente": "ATACADAO 183",
        "data_alvo": "01/12/2025",
        "dados": [
            {"nome_produto": "AZEITONA VERDE", "num_pedido": "VCD123", "saldo_real": 100, "pallets": 2.5, "valor": 5000, "status": "disponivel_hoje"},
            {"nome_produto": "KETCHUP", "num_pedido": "VCD124", "saldo_real": 50, "pallets": 1.2, "valor": 2500, "status": "disponivel_na_data", "data_disponivel": "30/11/2025"},
        ],
        "analise": {
            "cliente": "ATACADAO 183",
            "data_alvo": "01/12/2025",
            "dias_ate_data": 3,
            "total_itens": 2,
            "disponiveis_hoje": 1,
            "disponiveis_na_data": 1,
            "sem_previsao": 0,
            "valor_disponivel_hoje": 5000,
            "valor_disponivel_na_data": 7500,
            "pallets_disponiveis_hoje": 2.5,
            "pallets_disponiveis_na_data": 3.7,
        }
    }

    formatado = cap.formatar_contexto(resultado)
    print(formatado)


def test_integracao_completa():
    """Teste de integração com o orchestrator."""
    print("\n" + "=" * 60)
    print("TESTE: Integração com Orchestrator")
    print("=" * 60)

    with app.app_context():
        from app.claude_ai_lite.core.orchestrator import processar_consulta

        consultas = [
            "Quais produtos do Atacadão 183 terão estoque semana que vem?",
            "O que tem disponível do Assaí?",
            "O que tem pra mandar pro RS?",
        ]

        for consulta in consultas:
            print(f"\n📝 Consulta: {consulta}")
            print("-" * 50)
            try:
                resposta = processar_consulta(consulta, usuario_id=1)
                # Mostra só as primeiras 500 caracteres
                print(resposta[:500] + "..." if len(resposta) > 500 else resposta)
            except Exception as e:
                print(f"❌ Erro: {e}")


if __name__ == "__main__":
    print("\n" + "=" * 70)
    print("  TESTES DO CAPABILITY analisar_disponibilidade v3.0")
    print("=" * 70)

    # Testes unitários
    test_pode_processar()
    test_extrair_data()
    test_formatacao()

    # Testes com banco (requer app context)
    test_execucao_cliente()
    test_execucao_data_futura()
    test_execucao_uf()

    # Teste de integração
    test_integracao_completa()

    print("\n" + "=" * 70)
    print("  TESTES CONCLUÍDOS")
    print("=" * 70)
