#!/usr/bin/env python3
"""
Teste do Estado Estruturado v4 - PILAR 3 da IA Fina.

Valida os 6 novos pontos:
1. contexto_pergunta_atual no DIALOGO
2. Integração extrator → estado (atualizar_do_extrator)
3. REFERENCIA (this pointer) para "esse pedido"
4. prioridade_fonte em CONSTRAINTS
5. TEMP para variáveis temporárias
6. item_focado em SEPARACAO

Execução:
    python scripts/testes/test_structured_state_v4.py
"""

import sys
import os
import json

# Adiciona o path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


def testar_contexto_pergunta():
    """Testa contexto_pergunta_atual no DIALOGO."""
    from app.claude_ai_lite.core.structured_state import (
        EstadoManager, ContextoPergunta
    )

    print("=" * 70)
    print("TESTE 1: contexto_pergunta_atual no DIALOGO")
    print("=" * 70)

    EstadoManager.limpar_tudo(999)

    # Define opções (deve setar contexto = escolher_opcao)
    EstadoManager.definir_opcoes(
        999,
        motivo="Escolha a data",
        lista=[{"letra": "A", "descricao": "27/11"}]
    )

    estado = EstadoManager.obter(999)
    json_str = estado.to_json_para_claude()
    json_obj = json.loads(json_str)

    print("\nJSON Gerado:")
    print(json_str[:500])

    # Validações
    assert "DIALOGO" in json_obj
    assert json_obj["DIALOGO"]["contexto_pergunta_atual"] == "escolher_opcao"
    assert json_obj["CONSTRAINTS"]["acao_esperada"] == "usuario_escolhendo_opcao_A_B_C"

    print("\n✅ Teste 1 PASSOU!")
    return True


def testar_integracao_extrator():
    """Testa integração extrator → estado."""
    from app.claude_ai_lite.core.structured_state import (
        EstadoManager, FonteEntidade
    )

    print("\n" + "=" * 70)
    print("TESTE 2: Integração extrator → estado")
    print("=" * 70)

    EstadoManager.limpar_tudo(999)

    # Simula entidades extraídas pelo Claude
    entidades_extraidas = {
        "num_pedido": "VCD2564177",
        "expedicao": "2025-11-27",
        "raz_social_red": "ATACADÃO"
    }

    EstadoManager.atualizar_do_extrator(999, entidades_extraidas)

    estado = EstadoManager.obter(999)
    json_str = estado.to_json_para_claude()
    json_obj = json.loads(json_str)

    print("\nJSON Gerado:")
    print(json_str[:500])

    # Validações
    entidades = json_obj.get("ENTIDADES", {})
    assert entidades["num_pedido"]["fonte"] == "extrator"
    assert entidades["num_pedido"]["valor"] == "VCD2564177"

    # Deve ter atualizado referências
    assert json_obj["REFERENCIA"]["pedido"] == "VCD2564177"

    print("\n✅ Teste 2 PASSOU!")
    return True


def testar_referencia_this_pointer():
    """Testa REFERENCIA (this pointer)."""
    from app.claude_ai_lite.core.structured_state import EstadoManager

    print("\n" + "=" * 70)
    print("TESTE 3: REFERENCIA (this pointer)")
    print("=" * 70)

    EstadoManager.limpar_tudo(999)

    # Define referências
    EstadoManager.definir_referencia(
        999,
        pedido="VCD001",
        cliente="ATACADÃO",
        item_idx=2
    )

    estado = EstadoManager.obter(999)
    json_str = estado.to_json_para_claude()
    json_obj = json.loads(json_str)

    print("\nJSON Gerado:")
    print(json_str[:500])

    # Validações
    assert "REFERENCIA" in json_obj
    assert json_obj["REFERENCIA"]["pedido"] == "VCD001"
    assert json_obj["REFERENCIA"]["cliente"] == "ATACADÃO"
    assert json_obj["REFERENCIA"]["item_idx"] == 2

    # Prioridade deve incluir REFERENCIA
    assert "REFERENCIA.pedido" in json_obj["CONSTRAINTS"]["prioridade"]["num_pedido"]

    print("\n✅ Teste 3 PASSOU!")
    return True


def testar_prioridade_fonte():
    """Testa prioridade_fonte em CONSTRAINTS."""
    from app.claude_ai_lite.core.structured_state import (
        EstadoManager, FonteEntidade, PRIORIDADE_FONTES
    )

    print("\n" + "=" * 70)
    print("TESTE 4: prioridade_fonte em CONSTRAINTS")
    print("=" * 70)

    EstadoManager.limpar_tudo(999)

    estado = EstadoManager.obter(999)
    json_str = estado.to_json_para_claude()
    json_obj = json.loads(json_str)

    print("\nJSON Gerado:")
    print(json_str[:500])

    # Validações
    assert "prioridade_fonte" in json_obj["CONSTRAINTS"]
    assert json_obj["CONSTRAINTS"]["prioridade_fonte"] == PRIORIDADE_FONTES
    assert json_obj["CONSTRAINTS"]["prioridade_fonte"][0] == "usuario"
    assert json_obj["CONSTRAINTS"]["prioridade_fonte"][1] == "rascunho"

    print("\n✅ Teste 4 PASSOU!")
    return True


def testar_prioridade_fonte_respeita_usuario():
    """Testa que fonte do usuário não é sobrescrita."""
    from app.claude_ai_lite.core.structured_state import (
        EstadoManager, FonteEntidade
    )

    print("\n" + "=" * 70)
    print("TESTE 5: Prioridade de fonte (usuário não sobrescrito)")
    print("=" * 70)

    EstadoManager.limpar_tudo(999)

    # Usuário define pedido
    EstadoManager.atualizar_entidade(
        999, "num_pedido", "VCD_USUARIO", FonteEntidade.USUARIO.value
    )

    # Extrator tenta sobrescrever
    EstadoManager.atualizar_do_extrator(999, {"num_pedido": "VCD_EXTRATOR"})

    estado = EstadoManager.obter(999)
    json_str = estado.to_json_para_claude()
    json_obj = json.loads(json_str)

    print("\nJSON Gerado:")
    print(json_str[:500])

    # Validações - usuário deve prevalecer!
    assert json_obj["ENTIDADES"]["num_pedido"]["valor"] == "VCD_USUARIO"
    assert json_obj["ENTIDADES"]["num_pedido"]["fonte"] == "usuario"

    print("\n✅ Teste 5 PASSOU!")
    return True


def testar_temp():
    """Testa TEMP para variáveis temporárias."""
    from app.claude_ai_lite.core.structured_state import EstadoManager

    print("\n" + "=" * 70)
    print("TESTE 6: TEMP (variáveis temporárias)")
    print("=" * 70)

    EstadoManager.limpar_tudo(999)

    # Define variáveis temporárias
    EstadoManager.definir_temp(
        999,
        ultimo_numero=5,
        ultimo_item_mencionado="Azeitona Verde"
    )

    estado = EstadoManager.obter(999)
    json_str = estado.to_json_para_claude()
    json_obj = json.loads(json_str)

    print("\nJSON Gerado:")
    print(json_str[:500])

    # Validações
    assert "TEMP" in json_obj
    assert json_obj["TEMP"]["ultimo_numero"] == 5
    assert json_obj["TEMP"]["ultimo_item_mencionado"] == "Azeitona Verde"

    print("\n✅ Teste 6 PASSOU!")
    return True


def testar_item_focado():
    """Testa item_focado em SEPARACAO."""
    from app.claude_ai_lite.core.structured_state import EstadoManager

    print("\n" + "=" * 70)
    print("TESTE 7: item_focado em SEPARACAO")
    print("=" * 70)

    EstadoManager.limpar_tudo(999)

    # Define separação
    EstadoManager.definir_separacao(999, {
        "num_pedido": "VCD001",
        "cliente": "CLIENTE TESTE",
        "itens": [
            {"cod_produto": "P001", "nome_produto": "Azeitona", "quantidade": 100},
            {"cod_produto": "P002", "nome_produto": "Azeite", "quantidade": 50}
        ]
    })

    # Define item focado
    EstadoManager.definir_item_focado(999, {
        "idx": 1,
        "cod_produto": "P001",
        "nome_produto": "Azeitona",
        "quantidade": 100
    })

    estado = EstadoManager.obter(999)
    json_str = estado.to_json_para_claude()
    json_obj = json.loads(json_str)

    print("\nJSON Gerado:")
    print(json_str)

    # Validações
    assert "item_focado" in json_obj["SEPARACAO"]
    assert json_obj["SEPARACAO"]["item_focado"]["cod_produto"] == "P001"
    assert json_obj["SEPARACAO"]["item_focado"]["nome_produto"] == "Azeitona"

    # Prioridade deve incluir item_focado
    assert "SEPARACAO.item_focado" in json_obj["CONSTRAINTS"]["prioridade"]["item"]

    print("\n✅ Teste 7 PASSOU!")
    return True


def testar_cenario_completo_v4():
    """Testa cenário completo com todas as features v4."""
    from app.claude_ai_lite.core.structured_state import (
        EstadoManager, FonteEntidade, ContextoPergunta
    )

    print("\n" + "=" * 70)
    print("TESTE 8: Cenário Completo v4")
    print("=" * 70)

    EstadoManager.limpar_tudo(999)

    print("\n--- Etapa 1: Extrator encontra pedido ---")
    EstadoManager.atualizar_do_extrator(999, {"num_pedido": "VCD2564177"})

    print("\n--- Etapa 2: Consulta retorna dados ---")
    EstadoManager.definir_consulta(
        999, "pedidos", 1,
        [{"num_pedido": "VCD2564177", "raz_social_red": "ATACADÃO"}]
    )

    print("\n--- Etapa 3: Cria rascunho ---")
    EstadoManager.definir_separacao(999, {
        "num_pedido": "VCD2564177",
        "cliente": "ATACADÃO",
        "itens": [
            {"cod_produto": "001", "nome_produto": "Azeitona", "quantidade": 100}
        ]
    })

    print("\n--- Etapa 4: Foca no item ---")
    EstadoManager.definir_item_focado(999, {
        "idx": 1,
        "cod_produto": "001",
        "nome_produto": "Azeitona",
        "quantidade": 100
    })

    print("\n--- Etapa 5: Define temp ---")
    EstadoManager.definir_temp(999, ultimo_numero=50)

    print("\n--- Etapa 6: Oferece opções ---")
    EstadoManager.definir_opcoes(
        999,
        motivo="Escolha a data",
        lista=[{"letra": "A", "descricao": "27/11"}],
        esperado_do_usuario="escolher A ou informar outra data"
    )

    estado = EstadoManager.obter(999)
    json_str = estado.to_json_para_claude()
    json_obj = json.loads(json_str)

    print("\nJSON Final:")
    print(json_str)

    # Validações completas
    assert json_obj["DIALOGO"]["contexto_pergunta_atual"] == "escolher_opcao"
    assert "ENTIDADES" in json_obj
    assert "REFERENCIA" in json_obj
    assert json_obj["REFERENCIA"]["pedido"] == "VCD2564177"
    assert "SEPARACAO" in json_obj
    assert "item_focado" in json_obj["SEPARACAO"]
    assert "CONSULTA" in json_obj
    assert "OPCOES" in json_obj
    assert "esperado_do_usuario" in json_obj["OPCOES"]
    assert "TEMP" in json_obj
    assert json_obj["TEMP"]["ultimo_numero"] == 50
    assert "prioridade_fonte" in json_obj["CONSTRAINTS"]
    assert json_obj["CONSTRAINTS"]["acao_esperada"] == "usuario_escolhendo_opcao_A_B_C"

    print("\n✅ Teste 8 PASSOU!")
    return True


def main():
    """Executa todos os testes."""
    print("\n" + "=" * 70)
    print("TESTES DO ESTADO ESTRUTURADO v4 - 6 NOVOS PONTOS")
    print("=" * 70)

    testes = [
        ("contexto_pergunta_atual", testar_contexto_pergunta),
        ("Integração extrator", testar_integracao_extrator),
        ("REFERENCIA (this pointer)", testar_referencia_this_pointer),
        ("prioridade_fonte", testar_prioridade_fonte),
        ("Prioridade respeita usuário", testar_prioridade_fonte_respeita_usuario),
        ("TEMP", testar_temp),
        ("item_focado", testar_item_focado),
        ("Cenário Completo v4", testar_cenario_completo_v4),
    ]

    resultados = {"sucesso": 0, "falha": 0}

    for nome, func in testes:
        try:
            if func():
                resultados["sucesso"] += 1
            else:
                resultados["falha"] += 1
                print(f"\n❌ {nome} FALHOU!")
        except Exception as e:
            resultados["falha"] += 1
            print(f"\n❌ {nome} ERRO: {e}")
            import traceback
            traceback.print_exc()

    # Resumo
    print("\n" + "=" * 70)
    print(f"RESUMO: {resultados['sucesso']} sucesso, {resultados['falha']} falha")
    print("=" * 70)

    return resultados["falha"] == 0


if __name__ == "__main__":
    sucesso = main()
    sys.exit(0 if sucesso else 1)
