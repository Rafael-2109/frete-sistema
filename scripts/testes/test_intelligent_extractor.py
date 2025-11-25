#!/usr/bin/env python3
"""
Teste do Extrator Inteligente v3.5

Valida que o novo sistema delega corretamente ao Claude
e extrai entidades de forma flexível.

Casos de teste:
1. Datas em diferentes formatos
2. Referências contextuais
3. Modificações
4. Ações complexas
"""

import sys
import os

# Adiciona o path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

os.environ['FLASK_APP'] = 'app'
os.environ['FLASK_ENV'] = 'development'


def testar_extracao():
    """Testa o extrator inteligente com vários casos."""
    from app import create_app
    from app.claude_ai_lite.core.intelligent_extractor import extrair_inteligente
    from app.claude_ai_lite.core.entity_mapper import mapear_extracao

    app = create_app()

    # Casos de teste com expectativas
    # NOTA: Usamos 'expedicao' como campo destino (após mapeamento)
    # O Claude pode extrair como data_expedicao, data_nova, etc, mas o mapper converte
    casos = [
        # DATAS
        {
            "texto": "Pode criar a separação, mas crie pro dia 27/11",
            "esperado": {
                "tipo": "acao",
                "deve_ter_algum": ["expedicao", "data_expedicao", "data_separacao", "data"],
                "data_esperada": "2025-11-27"
            }
        },
        {
            "texto": "Quero pro dia 28/11 e não pro dia 25/11",
            "esperado": {
                "tipo": ["acao", "modificacao"],
                "deve_ter_algum": ["expedicao", "data_expedicao", "data_nova"],
                "data_esperada": "2025-11-28"
            }
        },
        {
            "texto": "Alterar a data de expedição para 30/11",
            "esperado": {
                "tipo": ["acao", "modificacao"],
                "deve_ter_algum": ["expedicao", "data_expedicao"]
            }
        },
        {
            "texto": "Criar separação do pedido VCD2564177 para semana que vem",
            "esperado": {
                "tipo": "acao",
                "deve_ter": ["num_pedido"],
                # Claude pode usar vários termos para "semana que vem"
                "deve_ter_algum": ["expedicao", "data_separacao", "periodo", "referencia_temporal", "data_expedicao"],
                "pedido_esperado": "VCD2564177"
            }
        },

        # CONTEXTO
        {
            "texto": "Pode criar a separação",
            "contexto": "Último pedido discutido: VCD2564177",
            "esperado": {
                "tipo": "acao",
                "deve_usar_contexto": True
            }
        },

        # CONFIRMAÇÕES
        {
            "texto": "Sim, pode confirmar",
            "esperado": {
                "tipo": "confirmacao"
            }
        },
        {
            "texto": "Confirmo a separação",
            "esperado": {
                "tipo": ["confirmacao", "acao"]
            }
        },

        # OPÇÕES - Claude PODE pedir clarificação quando há ambiguidade
        # Isso é o comportamento CORRETO - perguntar ao invés de assumir
        {
            "texto": "Opção A",
            "esperado": {
                # clarificacao é aceito quando não há contexto suficiente
                "tipo": ["acao", "confirmacao", "clarificacao"],
                "deve_ter": ["opcao"]
            }
        },
        {
            "texto": "Quero a opção B para o dia 29/11",
            "esperado": {
                # Claude PODE pedir clarificação: é data de expedição ou agendamento?
                "tipo": ["acao", "modificacao", "clarificacao"],
                "deve_ter": ["opcao"],
                "deve_ter_algum": ["expedicao", "data", "data_expedicao", "agendamento", "data_mencionada"]
            }
        },

        # CANCELAMENTO
        {
            "texto": "Cancela essa separação",
            "esperado": {
                # Claude pode interpretar como acao de cancelar
                "tipo": ["cancelamento", "acao"]
            }
        },
    ]

    with app.app_context():
        print("=" * 70)
        print("TESTE DO EXTRATOR INTELIGENTE v3.5")
        print("=" * 70)
        print()

        resultados = {"sucesso": 0, "falha": 0}

        for i, caso in enumerate(casos, 1):
            texto = caso["texto"]
            contexto = caso.get("contexto")
            esperado = caso["esperado"]

            print(f"[TESTE {i}] {texto}")
            if contexto:
                print(f"  Contexto: {contexto[:50]}...")

            try:
                # Extrai com Claude
                extracao = extrair_inteligente(texto, contexto)
                # Mapeia para sistema
                resultado = mapear_extracao(extracao)

                tipo = extracao.get("tipo", "")
                entidades = resultado.get("entidades", {})

                # Valida tipo
                tipos_esperados = esperado.get("tipo", [])
                if isinstance(tipos_esperados, str):
                    tipos_esperados = [tipos_esperados]

                tipo_ok = tipo in tipos_esperados if tipos_esperados else True

                # Valida entidades obrigatórias
                deve_ter = esperado.get("deve_ter", [])
                entidades_ok = all(
                    k in entidades or k in extracao.get("entidades", {})
                    for k in deve_ter
                )

                # Valida "deve ter algum" (pelo menos um da lista)
                deve_ter_algum = esperado.get("deve_ter_algum", [])
                algum_ok = True
                if deve_ter_algum:
                    todas_entidades = set(entidades.keys()) | set(extracao.get("entidades", {}).keys())
                    algum_ok = any(k in todas_entidades for k in deve_ter_algum)

                # Valida data específica (verifica em múltiplos campos possíveis)
                data_esperada = esperado.get("data_esperada")
                data_ok = True
                data_extraida = None
                if data_esperada:
                    # O Claude pode retornar em vários campos, verificamos todos
                    campos_data = ['expedicao', 'data_expedicao', 'data_nova', 'data_separacao', 'data']
                    for campo in campos_data:
                        valor = entidades.get(campo) or extracao.get("entidades", {}).get(campo)
                        if valor:
                            data_extraida = valor
                            break
                    data_ok = data_extraida == data_esperada

                # Valida pedido
                pedido_esperado = esperado.get("pedido_esperado")
                pedido_ok = True
                if pedido_esperado:
                    pedido_extraido = (
                        entidades.get("num_pedido") or
                        extracao.get("entidades", {}).get("num_pedido")
                    )
                    pedido_ok = pedido_extraido == pedido_esperado

                # Resultado do teste
                if tipo_ok and entidades_ok and algum_ok and data_ok and pedido_ok:
                    print(f"  ✅ SUCESSO")
                    print(f"     Tipo: {tipo}")
                    print(f"     Entidades: {list(entidades.keys())}")
                    if data_esperada:
                        print(f"     Data extraída: {data_extraida} (esperado: {data_esperada})")
                    if pedido_esperado:
                        print(f"     Pedido: {pedido_extraido}")
                    resultados["sucesso"] += 1
                else:
                    print(f"  ❌ FALHA")
                    print(f"     Tipo: {tipo} (esperado: {tipos_esperados})")
                    print(f"     Entidades: {list(entidades.keys())}")
                    if deve_ter:
                        print(f"     Deve ter: {deve_ter} - OK: {entidades_ok}")
                    if deve_ter_algum:
                        print(f"     Deve ter algum: {deve_ter_algum} - OK: {algum_ok}")
                    if data_esperada:
                        print(f"     Data: {data_extraida} (esperado: {data_esperada}) - OK: {data_ok}")
                    resultados["falha"] += 1

            except Exception as e:
                print(f"  ❌ ERRO: {e}")
                import traceback
                traceback.print_exc()
                resultados["falha"] += 1

            print()

        # Resumo
        print("=" * 70)
        print(f"RESUMO: {resultados['sucesso']} sucesso, {resultados['falha']} falha")
        print("=" * 70)

        return resultados["falha"] == 0


if __name__ == "__main__":
    sucesso = testar_extracao()
    sys.exit(0 if sucesso else 1)
