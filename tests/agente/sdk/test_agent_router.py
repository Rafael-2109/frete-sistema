from app.agente.sdk.agent_router import select_specialist


def test_frase_de_recebimento_entra_no_especialista():
    role, reason = select_specialist("vincular o pedido C2615437 na nota 48862 pelo odoo")
    assert role == "gestor-recebimento"
    assert reason == "padrao_recebimento"

def test_continuacao_curta_mantem_especialista():
    role, reason = select_specialist("e a 48863?", current_active="gestor-recebimento")
    assert role == "gestor-recebimento"
    assert reason == "continuacao"

def test_sinal_de_outro_dominio_reverte_ao_principal():
    role, reason = select_specialist(
        "qual a margem de custeio do palmito?", current_active="gestor-recebimento")
    assert role == "principal"
    assert reason == "reversao_outro_dominio"

def test_default_principal_quando_nao_ha_sinal():
    role, reason = select_specialist("bom dia, tudo bem?")
    assert role == "principal"
    assert reason == "default"

def test_prompt_complexo_longo_fica_no_principal_mesmo_com_keyword():
    msg = ("preciso entender a politica de vinculacao de nota com pedido, comparar "
           "tolerancias, revisar premissas fiscais e decidir a estrategia geral aqui")
    role, reason = select_specialist(msg)
    assert role == "principal"
    assert reason == "prompt_complexo"
