#!/usr/bin/env python3
"""
Teste do Estado Estruturado v3 - PILAR 3 da IA Fina.

Valida:
1. CONSTRAINTS como objeto formal (não lista de frases)
2. ENTIDADES com metadados (valor + fonte)
3. OPCOES com esperado_do_usuario
4. CONSULTA com modelo SQL
5. DIALOGO com dominios_validos

Execução:
    python scripts/testes/test_structured_state_v3.py
"""

import sys
import os
import json

# Adiciona o path do projeto
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))


def testar_estrutura_basica():
    """Testa estrutura básica do estado."""
    from app.claude_ai_lite.core.structured_state import (
        EstadoManager, EstadoDialogo, FonteEntidade
    )

    print("=" * 70)
    print("TESTE 1: Estrutura Básica (estado IDLE)")
    print("=" * 70)

    # Limpa estado anterior
    EstadoManager.limpar_tudo(999)

    # Obtém estado vazio
    estado = EstadoManager.obter(999)
    json_str = estado.to_json_para_claude()
    json_obj = json.loads(json_str)

    print("\nJSON Gerado:")
    print(json_str)

    # Validações
    assert "DIALOGO" in json_obj, "Deve ter DIALOGO"
    assert "dominios_validos" in json_obj["DIALOGO"], "DIALOGO deve ter dominios_validos"
    assert "carteira" in json_obj["DIALOGO"]["dominios_validos"], "Deve incluir carteira"
    assert "CONSTRAINTS" in json_obj, "Deve ter CONSTRAINTS"
    assert "campos_validos" in json_obj["CONSTRAINTS"], "CONSTRAINTS deve ter campos_validos"
    assert json_obj["CONSTRAINTS"]["proibido_inventar"] == True, "proibido_inventar deve ser True"

    print("\n✅ Teste 1 PASSOU!")
    return True


def testar_entidades_com_metadados():
    """Testa entidades com metadados (valor + fonte)."""
    from app.claude_ai_lite.core.structured_state import (
        EstadoManager, FonteEntidade
    )

    print("\n" + "=" * 70)
    print("TESTE 2: Entidades com Metadados")
    print("=" * 70)

    # Limpa e configura
    EstadoManager.limpar_tudo(999)

    # Adiciona entidades com diferentes fontes
    EstadoManager.atualizar_entidade(999, "num_pedido", "VCD2564177", FonteEntidade.USUARIO.value)
    EstadoManager.atualizar_entidade(999, "cliente", "ATACADÃO", FonteEntidade.CONSULTA.value)
    EstadoManager.atualizar_entidade(999, "data_expedicao", "2025-11-27", FonteEntidade.EXTRATOR.value)

    estado = EstadoManager.obter(999)
    json_str = estado.to_json_para_claude()
    json_obj = json.loads(json_str)

    print("\nJSON Gerado:")
    print(json_str)

    # Validações
    entidades = json_obj.get("ENTIDADES", {})
    assert "num_pedido" in entidades, "Deve ter num_pedido"
    assert entidades["num_pedido"]["valor"] == "VCD2564177", "Valor deve ser VCD2564177"
    assert entidades["num_pedido"]["fonte"] == "usuario", "Fonte deve ser usuario"

    assert "cliente" in entidades, "Deve ter cliente"
    assert entidades["cliente"]["fonte"] == "consulta_anterior", "Fonte deve ser consulta_anterior"

    print("\n✅ Teste 2 PASSOU!")
    return True


def testar_constraints_formal():
    """Testa CONSTRAINTS como objeto formal."""
    from app.claude_ai_lite.core.structured_state import (
        EstadoManager, EstadoDialogo, FonteEntidade
    )

    print("\n" + "=" * 70)
    print("TESTE 3: CONSTRAINTS como Objeto Formal")
    print("=" * 70)

    # Limpa e configura separação ativa
    EstadoManager.limpar_tudo(999)
    EstadoManager.definir_separacao(999, {
        "num_pedido": "VCD2564177",
        "cliente": "CLIENTE TESTE",
        "data_expedicao": "2025-11-27",
        "modo": "total",
        "resumo": {"total": 5, "incluidos": 5}
    })

    estado = EstadoManager.obter(999)
    json_str = estado.to_json_para_claude()
    json_obj = json.loads(json_str)

    print("\nJSON Gerado:")
    print(json_str)

    # Validações
    constraints = json_obj.get("CONSTRAINTS", {})

    # Deve ser objeto, não lista!
    assert isinstance(constraints, dict), "CONSTRAINTS deve ser dict, não lista!"

    # Deve ter prioridade
    assert "prioridade" in constraints, "Deve ter prioridade"
    assert "num_pedido" in constraints["prioridade"], "Deve ter prioridade para num_pedido"
    assert "SEPARACAO.num_pedido" in constraints["prioridade"]["num_pedido"], "Prioridade deve incluir SEPARACAO"

    # Deve ter interpretação de data
    assert constraints["interpretacao_padrao_data"] == "aplicar_em_data_expedicao_do_rascunho"

    # Deve ter ação esperada
    assert constraints["acao_esperada"] == "modificacao_ou_confirmacao_do_rascunho"

    print("\n✅ Teste 3 PASSOU!")
    return True


def testar_opcoes_com_esperado():
    """Testa OPCOES com esperado_do_usuario."""
    from app.claude_ai_lite.core.structured_state import (
        EstadoManager, EstadoDialogo
    )

    print("\n" + "=" * 70)
    print("TESTE 4: OPCOES com esperado_do_usuario")
    print("=" * 70)

    # Limpa e configura
    EstadoManager.limpar_tudo(999)
    EstadoManager.definir_opcoes(
        999,
        motivo="Escolha o modo de expedição",
        lista=[
            {"letra": "A", "descricao": "Expedir tudo disponível"},
            {"letra": "B", "descricao": "Expedir parcialmente"},
            {"letra": "C", "descricao": "Cancelar separação"}
        ],
        esperado_do_usuario="escolher A, B ou C para definir o modo"
    )

    estado = EstadoManager.obter(999)
    json_str = estado.to_json_para_claude()
    json_obj = json.loads(json_str)

    print("\nJSON Gerado:")
    print(json_str)

    # Validações
    assert "OPCOES" in json_obj, "Deve ter OPCOES"
    opcoes = json_obj["OPCOES"]
    assert "esperado_do_usuario" in opcoes, "Deve ter esperado_do_usuario"
    assert "escolher" in opcoes["esperado_do_usuario"], "Esperado deve mencionar escolher"

    # CONSTRAINTS deve indicar que espera escolha
    assert json_obj["CONSTRAINTS"]["acao_esperada"] == "usuario_escolhendo_opcao_A_B_C"

    print("\n✅ Teste 4 PASSOU!")
    return True


def testar_consulta_com_modelo():
    """Testa CONSULTA com modelo SQL."""
    from app.claude_ai_lite.core.structured_state import (
        EstadoManager
    )

    print("\n" + "=" * 70)
    print("TESTE 5: CONSULTA com Modelo SQL")
    print("=" * 70)

    # Limpa e configura
    EstadoManager.limpar_tudo(999)
    EstadoManager.definir_consulta(
        999,
        tipo="pedidos",
        total=3,
        itens=[
            {"num_pedido": "VCD001", "raz_social_red": "CLIENTE A"},
            {"num_pedido": "VCD002", "raz_social_red": "CLIENTE B"},
            {"num_pedido": "VCD003", "raz_social_red": "CLIENTE C"}
        ],
        modelo="CarteiraPrincipal"
    )

    estado = EstadoManager.obter(999)
    json_str = estado.to_json_para_claude()
    json_obj = json.loads(json_str)

    print("\nJSON Gerado:")
    print(json_str)

    # Validações
    assert "CONSULTA" in json_obj, "Deve ter CONSULTA"
    consulta = json_obj["CONSULTA"]
    assert "modelo" in consulta, "Deve ter modelo"
    assert consulta["modelo"] == "CarteiraPrincipal", "Modelo deve ser CarteiraPrincipal"
    assert consulta["total"] == 3, "Total deve ser 3"

    # Deve ter extraído entidades com fonte consulta
    entidades = json_obj.get("ENTIDADES", {})
    assert entidades["num_pedido"]["fonte"] == "consulta_anterior", "Fonte deve ser consulta_anterior"

    print("\n✅ Teste 5 PASSOU!")
    return True


def testar_prioridade_fontes():
    """Testa que fontes de usuário/rascunho não são sobrescritas por consulta."""
    from app.claude_ai_lite.core.structured_state import (
        EstadoManager, FonteEntidade
    )

    print("\n" + "=" * 70)
    print("TESTE 6: Prioridade de Fontes")
    print("=" * 70)

    # Limpa e configura
    EstadoManager.limpar_tudo(999)

    # Usuário define num_pedido explicitamente
    EstadoManager.atualizar_entidade(999, "num_pedido", "VCD_USUARIO", FonteEntidade.USUARIO.value)

    # Depois vem uma consulta com outro pedido
    EstadoManager.definir_consulta(
        999,
        tipo="pedidos",
        total=1,
        itens=[{"num_pedido": "VCD_CONSULTA", "raz_social_red": "OUTRO CLIENTE"}],
        modelo="CarteiraPrincipal"
    )

    estado = EstadoManager.obter(999)
    json_str = estado.to_json_para_claude()
    json_obj = json.loads(json_str)

    print("\nJSON Gerado:")
    print(json_str)

    # Validações - a fonte do usuário deve prevalecer!
    entidades = json_obj.get("ENTIDADES", {})
    assert entidades["num_pedido"]["valor"] == "VCD_USUARIO", "Valor do usuário deve prevalecer"
    assert entidades["num_pedido"]["fonte"] == "usuario", "Fonte deve continuar como usuario"

    print("\n✅ Teste 6 PASSOU!")
    return True


def testar_cenario_completo():
    """Testa cenário completo: consulta → separação → opções."""
    from app.claude_ai_lite.core.structured_state import (
        EstadoManager, FonteEntidade
    )

    print("\n" + "=" * 70)
    print("TESTE 7: Cenário Completo (Fluxo Real)")
    print("=" * 70)

    # Limpa
    EstadoManager.limpar_tudo(999)

    print("\n--- Etapa 1: Usuário menciona pedido ---")
    EstadoManager.atualizar_entidade(999, "num_pedido", "VCD2564177", FonteEntidade.USUARIO.value)

    print("\n--- Etapa 2: Sistema faz consulta ---")
    EstadoManager.definir_consulta(
        999,
        tipo="pedidos",
        total=1,
        itens=[{
            "num_pedido": "VCD2564177",
            "raz_social_red": "ATACADÃO SP",
            "cod_uf": "SP"
        }],
        modelo="CarteiraPrincipal"
    )

    print("\n--- Etapa 3: Cria rascunho de separação ---")
    EstadoManager.definir_separacao(999, {
        "num_pedido": "VCD2564177",
        "cliente": "ATACADÃO SP",
        "data_expedicao": None,  # Ainda não definida
        "modo": "total",
        "itens": [
            {"cod_produto": "001", "nome_produto": "Azeitona Verde", "quantidade": 100},
            {"cod_produto": "002", "nome_produto": "Azeite Premium", "quantidade": 50}
        ],
        "resumo": {"total": 2, "incluidos": 2, "valor": 5000.00}
    })

    print("\n--- Etapa 4: Sistema oferece opções de data ---")
    EstadoManager.definir_opcoes(
        999,
        motivo="Escolha a data de expedição",
        lista=[
            {"letra": "A", "descricao": "27/11 - Segunda-feira"},
            {"letra": "B", "descricao": "28/11 - Terça-feira"},
            {"letra": "C", "descricao": "Outra data"}
        ],
        esperado_do_usuario="escolher A, B ou C, ou informar outra data"
    )

    estado = EstadoManager.obter(999)
    json_str = estado.to_json_para_claude()
    json_obj = json.loads(json_str)

    print("\nJSON Final:")
    print(json_str)

    # Validações finais
    assert "DIALOGO" in json_obj
    assert json_obj["DIALOGO"]["estado"] == "aguardando_escolha"
    assert "ENTIDADES" in json_obj
    assert "SEPARACAO" in json_obj
    assert json_obj["SEPARACAO"]["ativo"] == True
    assert "CONSULTA" in json_obj
    assert "OPCOES" in json_obj
    assert "esperado_do_usuario" in json_obj["OPCOES"]
    assert "CONSTRAINTS" in json_obj
    assert isinstance(json_obj["CONSTRAINTS"], dict)  # Não lista!
    assert json_obj["CONSTRAINTS"]["acao_esperada"] == "usuario_escolhendo_opcao_A_B_C"

    print("\n✅ Teste 7 PASSOU!")
    return True


def main():
    """Executa todos os testes."""
    print("\n" + "=" * 70)
    print("TESTES DO ESTADO ESTRUTURADO v3 - PILAR 3")
    print("=" * 70)

    testes = [
        ("Estrutura Básica", testar_estrutura_basica),
        ("Entidades com Metadados", testar_entidades_com_metadados),
        ("CONSTRAINTS Formal", testar_constraints_formal),
        ("OPCOES com esperado", testar_opcoes_com_esperado),
        ("CONSULTA com modelo", testar_consulta_com_modelo),
        ("Prioridade de Fontes", testar_prioridade_fontes),
        ("Cenário Completo", testar_cenario_completo),
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
