#!/usr/bin/env python3
"""
Teste do módulo de Clarificação Enriquecida (v6.0).

Testa o novo fluxo que:
1. Detecta O QUE está faltando (cliente, pedido, produto, data)
2. Busca sugestões REAIS do sistema
3. Oferece opções clicáveis/numeradas ao usuário

Uso:
    python scripts/testes/test_clarification_enricher.py

Criado em: 28/11/2025
"""

import sys
import os

# Adiciona o diretório raiz ao path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from app import create_app


def test_detectar_tipo_faltante():
    """Testa a detecção do tipo de informação faltante."""
    from app.claude_ai_lite.core.clarification_enricher import detectar_tipo_faltante

    print("\n" + "="*60)
    print("TESTE 1: Detecção do tipo de informação faltante")
    print("="*60)

    casos = [
        # Caso, Ambiguidade, Esperado
        ("Cliente informado pelo Claude", {"tipo_faltante": "cliente"}, "cliente"),
        ("Pedido informado pelo Claude", {"tipo_faltante": "pedido"}, "pedido"),
        ("Produto informado pelo Claude", {"tipo_faltante": "produto"}, "produto"),
        ("Data informada pelo Claude", {"tipo_faltante": "data"}, "data"),

        # Detecção por análise de texto
        ("Pergunta sobre cliente", {"pergunta": "Qual cliente você quer consultar?"}, "cliente"),
        ("Pergunta sobre pedido", {"pergunta": "Qual o número do pedido?"}, "pedido"),
        ("Pergunta sobre produto", {"pergunta": "Qual produto você procura?"}, "produto"),
        ("Pergunta sobre data", {"pergunta": "Para quando você quer programar?"}, "data"),

        # Fallback para genérico
        ("Sem contexto", {"pergunta": "Poderia esclarecer?"}, "generico"),
    ]

    for nome, ambiguidade, esperado in casos:
        resultado = detectar_tipo_faltante(ambiguidade, {})
        status = "✅" if resultado == esperado else "❌"
        print(f"{status} {nome}: esperado='{esperado}', obtido='{resultado}'")


def test_enriquecer_cliente():
    """Testa o enriquecimento quando falta CLIENTE."""
    from app.claude_ai_lite.core.clarification_enricher import enriquecer_clarificacao

    print("\n" + "="*60)
    print("TESTE 2: Enriquecimento de clarificação (cliente)")
    print("="*60)

    resultado = enriquecer_clarificacao(
        tipo_faltante='cliente',
        entidades={},
        usuario_id=1,
        contexto_conversa=None
    )

    print(f"\nTipo sugestão: {resultado.get('tipo_sugestao')}")
    print(f"Sugestões: {resultado.get('sugestoes', [])}")
    print(f"Mensagem: {resultado.get('mensagem_enriquecida')}")
    print(f"Contexto adicional: {resultado.get('contexto_adicional')}")


def test_enriquecer_pedido():
    """Testa o enriquecimento quando falta PEDIDO."""
    from app.claude_ai_lite.core.clarification_enricher import enriquecer_clarificacao

    print("\n" + "="*60)
    print("TESTE 3: Enriquecimento de clarificação (pedido)")
    print("="*60)

    # Sem cliente
    resultado1 = enriquecer_clarificacao(
        tipo_faltante='pedido',
        entidades={},
        usuario_id=1,
        contexto_conversa=None
    )
    print(f"\nSem cliente:")
    print(f"  Sugestões: {resultado1.get('sugestoes', [])}")

    # Com cliente
    resultado2 = enriquecer_clarificacao(
        tipo_faltante='pedido',
        entidades={'raz_social_red': 'ASSAI'},
        usuario_id=1,
        contexto_conversa=None
    )
    print(f"\nCom cliente ASSAI:")
    print(f"  Sugestões: {resultado2.get('sugestoes', [])}")
    print(f"  Contexto: {resultado2.get('contexto_adicional')}")


def test_enriquecer_data():
    """Testa o enriquecimento quando falta DATA."""
    from app.claude_ai_lite.core.clarification_enricher import enriquecer_clarificacao

    print("\n" + "="*60)
    print("TESTE 4: Enriquecimento de clarificação (data)")
    print("="*60)

    resultado = enriquecer_clarificacao(
        tipo_faltante='data',
        entidades={'num_pedido': 'VCD2564177'},
        usuario_id=1,
        contexto_conversa=None
    )

    print(f"\nSugestões de data: {resultado.get('sugestoes', [])}")
    print(f"Contexto adicional: {resultado.get('contexto_adicional')}")


def test_gerar_resposta_enriquecida():
    """Testa a geração de resposta completa enriquecida."""
    from app.claude_ai_lite.core.clarification_enricher import gerar_resposta_clarificacao_enriquecida

    print("\n" + "="*60)
    print("TESTE 5: Resposta de clarificação enriquecida completa")
    print("="*60)

    ambiguidade = {
        "existe": True,
        "tipo_faltante": "cliente",
        "pergunta": "Qual cliente você quer consultar?",
        "motivo": "Não foi especificado o cliente"
    }

    resposta = gerar_resposta_clarificacao_enriquecida(
        ambiguidade=ambiguidade,
        entidades={'cod_uf': 'SP'},
        usuario_id=1,
        contexto_conversa=None
    )

    print(f"\n{resposta}")


def test_buscar_clientes_pendencias():
    """Testa a busca de clientes com pendências."""
    from app.claude_ai_lite.core.clarification_enricher import _buscar_clientes_com_pendencias

    print("\n" + "="*60)
    print("TESTE 6: Buscar clientes com pendências")
    print("="*60)

    clientes = _buscar_clientes_com_pendencias(limite=10)

    print(f"\nTop 10 clientes com mais pendências:")
    for i, cliente in enumerate(clientes, 1):
        print(f"  {i}. {cliente}")


def main():
    """Executa todos os testes."""
    app = create_app()

    with app.app_context():
        print("\n" + "="*60)
        print("TESTES DO MÓDULO CLARIFICATION_ENRICHER v6.0")
        print("="*60)

        # Teste 1: Detecção do tipo
        test_detectar_tipo_faltante()

        # Teste 2: Enriquecimento cliente
        test_enriquecer_cliente()

        # Teste 3: Enriquecimento pedido
        test_enriquecer_pedido()

        # Teste 4: Enriquecimento data
        test_enriquecer_data()

        # Teste 5: Resposta completa
        test_gerar_resposta_enriquecida()

        # Teste 6: Busca de clientes
        test_buscar_clientes_pendencias()

        print("\n" + "="*60)
        print("TESTES CONCLUÍDOS!")
        print("="*60)


if __name__ == '__main__':
    main()
