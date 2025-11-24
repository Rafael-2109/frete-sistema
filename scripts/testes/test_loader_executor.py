"""
Teste do LoaderExecutor estruturado.

Testa a pergunta original: "Ha pedidos do cliente Assai sem agendamento?"

Executar:
    python scripts/testes/test_loader_executor.py
"""

import sys
import os

# Adiciona o diretorio raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app


def test_loader_executor():
    """Testa o LoaderExecutor com a pergunta original."""
    app = create_app()

    with app.app_context():
        from app.claude_ai_lite.ia_trainer.services.loader_executor import (
            LoaderExecutor,
            validar_definicao,
            executar_loader
        )

        print("=" * 60)
        print("TESTE DO LOADER EXECUTOR ESTRUTURADO")
        print("=" * 60)
        print()

        # Definicao para a pergunta: "Ha pedidos do cliente Assai sem agendamento?"
        definicao = {
            "modelo_base": "Separacao",
            "filtros": [
                {"campo": "raz_social_red", "operador": "ilike", "valor": "%Assai%"},
                {"campo": "agendamento", "operador": "is_null"},
                {"campo": "sincronizado_nf", "operador": "==", "valor": False}
            ],
            "campos_retorno": [
                "num_pedido",
                "raz_social_red",
                "nome_cidade",
                "cod_uf",
                "qtd_saldo",
                "expedicao",
                "agendamento",
                "status"
            ],
            "ordenar": [{"campo": "num_pedido", "direcao": "asc"}],
            "limite": 50
        }

        print("1. VALIDANDO DEFINICAO")
        print("-" * 40)
        validacao = validar_definicao(definicao)
        print(f"   Valido: {validacao['valido']}")
        if validacao.get('erros'):
            print(f"   Erros: {validacao['erros']}")
        if validacao.get('avisos'):
            print(f"   Avisos: {validacao['avisos']}")
        print()

        print("2. EXECUTANDO LOADER")
        print("-" * 40)
        resultado = executar_loader(definicao)
        print(f"   Sucesso: {resultado['sucesso']}")
        print(f"   Total encontrado: {resultado['total']}")
        if resultado.get('erro'):
            print(f"   Erro: {resultado['erro']}")
        print()

        if resultado['sucesso'] and resultado['dados']:
            print("3. RESULTADOS (primeiros 5)")
            print("-" * 40)
            for i, item in enumerate(resultado['dados'][:5], 1):
                print(f"   {i}. Pedido: {item.get('num_pedido')}")
                print(f"      Cliente: {item.get('raz_social_red')}")
                print(f"      Cidade: {item.get('nome_cidade')}/{item.get('cod_uf')}")
                print(f"      Qtd: {item.get('qtd_saldo')}")
                print(f"      Expedicao: {item.get('expedicao')}")
                print(f"      Agendamento: {item.get('agendamento')}")
                print()

        # Teste 2: Com parametro dinamico
        print("=" * 60)
        print("TESTE 2: COM PARAMETRO DINAMICO")
        print("=" * 60)
        print()

        definicao_parametrizada = {
            "modelo_base": "Separacao",
            "filtros": [
                {"campo": "raz_social_red", "operador": "ilike", "valor": "%$cliente%"},
                {"campo": "agendamento", "operador": "is_null"},
                {"campo": "sincronizado_nf", "operador": "==", "valor": False}
            ],
            "campos_retorno": ["num_pedido", "raz_social_red", "qtd_saldo"],
            "limite": 10
        }

        resultado2 = executar_loader(definicao_parametrizada, {"cliente": "Assai"})
        print(f"   Sucesso: {resultado2['sucesso']}")
        print(f"   Total: {resultado2['total']}")
        print()

        # Teste 3: Com agregacao
        print("=" * 60)
        print("TESTE 3: COM AGREGACAO (soma por cliente)")
        print("=" * 60)
        print()

        definicao_agregada = {
            "modelo_base": "Separacao",
            "filtros": [
                {"campo": "sincronizado_nf", "operador": "==", "valor": False},
                {"campo": "agendamento", "operador": "is_null"}
            ],
            "agregacao": {
                "tipo": "agrupar",
                "por": ["raz_social_red"],
                "funcoes": [
                    {"func": "count", "campo": "id", "alias": "total_itens"},
                    {"func": "sum", "campo": "qtd_saldo", "alias": "total_qtd"}
                ]
            },
            "limite": 10
        }

        resultado3 = executar_loader(definicao_agregada)
        print(f"   Sucesso: {resultado3['sucesso']}")
        print(f"   Total grupos: {resultado3['total']}")
        if resultado3.get('erro'):
            print(f"   Erro: {resultado3['erro']}")
        print()

        if resultado3['sucesso'] and resultado3['dados']:
            print("   Primeiros clientes sem agendamento:")
            for i, item in enumerate(resultado3['dados'][:5], 1):
                print(f"   {i}. {item}")

        # Teste 4: Com OR (cliente Assai OU Atacadao)
        print("=" * 60)
        print("TESTE 4: COM OR (Assai OU Atacadao)")
        print("=" * 60)
        print()

        definicao_or = {
            "modelo_base": "Separacao",
            "filtros": {
                "and": [
                    {"campo": "sincronizado_nf", "operador": "==", "valor": False},
                    {"campo": "agendamento", "operador": "is_null"},
                    {
                        "or": [
                            {"campo": "raz_social_red", "operador": "ilike", "valor": "%Assai%"},
                            {"campo": "raz_social_red", "operador": "ilike", "valor": "%Atacadao%"}
                        ]
                    }
                ]
            },
            "campos_retorno": ["num_pedido", "raz_social_red", "qtd_saldo"],
            "limite": 20
        }

        resultado4 = executar_loader(definicao_or)
        print(f"   Sucesso: {resultado4['sucesso']}")
        print(f"   Total: {resultado4['total']}")
        if resultado4.get('erro'):
            print(f"   Erro: {resultado4['erro']}")
        elif resultado4['dados']:
            print("   Primeiros 5 resultados:")
            for i, item in enumerate(resultado4['dados'][:5], 1):
                print(f"   {i}. {item.get('raz_social_red')} - {item.get('num_pedido')}")

        print()
        print("=" * 60)
        print("TESTES CONCLUIDOS")
        print("=" * 60)


if __name__ == '__main__':
    test_loader_executor()
