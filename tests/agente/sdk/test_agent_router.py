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


# ─── Precisão da heurística (alinhada à disciplina do model_router) ──────────

def test_terceira_pessoa_pergunta_diagnostica_nao_entra():
    """'concilia/consolida' (3a pessoa, pergunta) NAO deve casar — só o infinitivo
    completo (conciliar/consolidar) é comando de recebimento. Bug que o
    model_router já pagou (2026-05-11)."""
    for msg in ("o sistema concilia a nota com o pedido automaticamente?",
                "como o odoo consolida a nota com o pedido?"):
        role, reason = select_specialist(msg)
        assert role == "principal", msg
        assert reason == "default", msg


def test_coocorrencia_sem_verbo_nao_entra():
    """Mera co-ocorrência de 'nota N' + 'pedido' SEM verbo de vínculo é conversa
    de cobrança/financeiro, não match NF×PO — fica no principal."""
    for msg in ("o pedido do cliente atrasou, mandei nota 5 vezes ao financeiro",
                "a nota 100 ja foi paga pelo pedido recorrente do cliente"):
        role, reason = select_specialist(msg)
        assert role == "principal", msg


def test_plural_pedidos_entra_no_especialista():
    """'\\bpedido\\b' não casava 'pedidos' (o 's' quebra a fronteira) — turno real
    de recebimento ia para o principal. Plural deve casar."""
    role, reason = select_specialist("vincular os pedidos nas notas pelo odoo")
    assert role == "gestor-recebimento"
    assert reason == "padrao_recebimento"


def test_infinitivo_conciliar_consolidar_ainda_entra():
    """Garante que o aperto (infinitivo) NÃO derruba os comandos legítimos."""
    for msg in ("conciliar a nota 12345 com o pedido C99",
                "consolidar as POs da nota 48862"):
        role, reason = select_specialist(msg)
        assert role == "gestor-recebimento", msg
        assert reason == "padrao_recebimento", msg
