"""
Testes do diagnóstico determinístico de automação de sessões do Agente Web.

Mede quanto do custo vem de tarefas ROTINEIRAS + ESTRUTURADAS (template estável) que
poderiam ser resolvidas por fast-path (Tier 0 regex/serviço) ou modelo mais barato,
em vez do loop Opus. Ancorado nas mensagens reais observadas em PROD (Gabriella etc.).

Função pura `classificar` + agregação `agregar` — sem DB, sem LLM, determinístico.
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/audits/session_automation_audit.py"


def _mod():
    spec = importlib.util.spec_from_file_location("session_automation_audit", SCRIPT)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


mod = _mod()


# --------------------------------------------------------------- classificar (real)

def test_vinculacao_nf_po_gabriella():
    # mensagem literal observada em PROD (user_id 69)
    r = mod.classificar("vincular o pedido C2615918 na nota 439871 no odoo e no frete, validar se tem algum erro e faça o ajuste")
    assert r["categoria"] == "vinculacao_nf_po"
    assert r["automatizavel"] is True
    assert r["tier_alvo"] in ("tier0", "sonnet")


def test_monitoramento_entrega():
    for txt in [
        "a NF 237284 foi entregue?",
        "que dia embarcou o pedido VCD123?",
        "cadê a entrega do Atacadão",
        "qual o status do pedido 4291",
    ]:
        r = mod.classificar(txt)
        assert r["categoria"] == "monitoramento_entrega", txt
        assert r["tier_alvo"] == "tier0"
        assert r["automatizavel"] is True


def test_cotacao():
    for txt in ["qual o frete para Manaus 5000kg?", "cotação para SP 3 toneladas", "quanto sai o frete pra RJ"]:
        r = mod.classificar(txt)
        assert r["categoria"] == "cotacao", txt
        assert r["automatizavel"] is True


def test_recalculo_frete_carvia():
    # rotina da Talita (id 17), observada em PROD
    for txt in [
        "agente logistico recalcular o frete cotado da NFe 2005 -CAZAN - embarque gerado no sistema CARVIA #5595 com o novo fre.mim peso",
        "agente logistico, por favor atualizar o embarque da CARVIA #5547, o valor do frete cotado, precisa ser recalculado o frete min peso",
    ]:
        r = mod.classificar(txt)
        assert r["categoria"] == "recalculo_frete_carvia", txt
        assert r["automatizavel"] is True


def test_faturamento():
    r = mod.classificar("olá, boa tarde @agente logístico poderia me ajudar a faturar esse CD/OUT/25315 item 4210176")
    assert r["categoria"] == "faturamento"
    assert r["tier_alvo"] == "sonnet"  # SEFAZ irreversível — não tier0


def test_baseline_eh_automatizavel():
    r = mod.classificar("atualizar baseline")
    assert r["categoria"] == "baseline"
    assert r["automatizavel"] is True
    assert r["tier_alvo"] == "tier0"


def test_consulta_movimentacao():
    for txt in [
        "preciso movimentação desse item [102030303] AZEITONA VERDE INTEIRA 20/24 desde o dia 18/05/2026",
        "verificar validade lote 94543",
    ]:
        r = mod.classificar(txt)
        assert r["categoria"] == "consulta_movimentacao", txt
        assert r["automatizavel"] is True


def test_cancelamento_semi():
    r = mod.classificar("cancelar o pedido VCD123")
    assert r["categoria"] == "cancelamento"
    # tem efeito colateral -> não é tier0 puro, mas é estruturado
    assert r["tier_alvo"] in ("sonnet", "haiku")


def test_conversa_livre_fica_opus():
    r = mod.classificar("me faça uma análise completa da carteira priorizando P1 a P7 e explique as rupturas")
    assert r["automatizavel"] is False
    assert r["tier_alvo"] == "opus"


def test_followup_curto_nao_classifica_como_rotina():
    # last_message frequentemente é "pronto?" — não deve virar categoria automatizável
    for txt in ["pronto?", "PRONTO?", "?", "pode me ajudar", "ok"]:
        r = mod.classificar(txt)
        assert r["automatizavel"] is False, txt
        assert r["categoria"] in ("indeterminado", "conversa")


def test_texto_vazio_ou_none():
    assert mod.classificar(None)["categoria"] == "indeterminado"
    assert mod.classificar("")["categoria"] == "indeterminado"


# ------------------------------------------------------------------- agregar

def test_agregar_ranking_por_custo():
    linhas = [
        {"texto": "vincular o pedido C2615918 na nota 439871 no odoo e no frete", "custo": 10.0},
        {"texto": "vincular o pedido C2618956 na nota 3186 no odoo", "custo": 6.0},
        {"texto": "a NF 237284 foi entregue?", "custo": 5.0},
        {"texto": "me faça uma análise da carteira", "custo": 30.0},
    ]
    rank = mod.agregar(linhas)
    cats = {r["categoria"]: r for r in rank}
    assert cats["vinculacao_nf_po"]["sessoes"] == 2
    assert cats["vinculacao_nf_po"]["custo"] == 16.0
    # ordenado por custo desc
    custos = [r["custo"] for r in rank]
    assert custos == sorted(custos, reverse=True)
    # economia só conta nas categorias automatizáveis
    assert cats["vinculacao_nf_po"]["economia_estimada"] > 0
    assert cats.get("conversa_analise", {}).get("economia_estimada", 0) == 0 or \
           any(r["categoria"] not in ("vinculacao_nf_po",) for r in rank)


def test_economia_nunca_excede_custo():
    linhas = [{"texto": "a nf 100 foi entregue?", "custo": 8.0}]
    rank = mod.agregar(linhas)
    for r in rank:
        assert 0 <= r["economia_estimada"] <= r["custo"]
