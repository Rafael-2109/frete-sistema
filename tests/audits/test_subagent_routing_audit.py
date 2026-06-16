"""Testes do tripwire de roteamento de subagentes (PAD-CTX).

Invariante: quando o conjunto de skills de um subagente muda (frontmatter
`skills:` de .claude/agents/*.md) mas o `<delegate_when>`/`<capabilities>` dele
no system_prompt NAO e' revisado, o principal pode nunca aprender a delegar para
a nova capacidade — foi exatamente o bug do #164 (auditando-reclassificacao-odoo:
skill no subagente, gatilho de delegacao desatualizado -> agente improvisava Bash).

`--check-routing` torna isso DETERMINISTICO: bloqueia o commit nesse caso.
Funcoes puras, sem DB/app — padrao do projeto (importlib).
"""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/audits/prompt_size_audit.py"


def _carregar_modulo():
    spec = importlib.util.spec_from_file_location("prompt_size_audit", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _carregar_modulo()


# ----------------------------------------------------------- _routing_hash
def test_routing_hash_ignora_whitespace():
    h1 = mod._routing_hash("a b c", "x y")
    h2 = mod._routing_hash("a   b\n c", "  x  y ")
    assert h1 == h2  # normaliza whitespace


def test_routing_hash_muda_com_conteudo():
    h1 = mod._routing_hash("reconciliacao extrato", "5 fluxos")
    h2 = mod._routing_hash("reconciliacao extrato; reclassificacao", "5 fluxos")
    assert h1 != h2  # conteudo diferente -> hash diferente


# ----------------------------------------------------------- _routing_por_agent
def test_routing_por_agent_extrai_blocos():
    txt = """
    <subagents>
    <agent name="auditor-financeiro" specialty="reconciliacao">
      <delegate_when>Auditoria Local vs Odoo, SEM_MATCH</delegate_when>
      <capabilities>5 fluxos reconciliacao</capabilities>
    </agent>
    <agent name="gestor-recebimento" specialty="pipeline">
      <delegate_when>DFEs bloqueados</delegate_when>
      <capabilities>4 fases</capabilities>
    </agent>
    </subagents>
    """
    r = mod._routing_por_agent(txt)
    assert set(r) == {"auditor-financeiro", "gestor-recebimento"}
    assert "SEM_MATCH" in r["auditor-financeiro"]["delegate_when"]
    assert r["gestor-recebimento"]["capabilities"] == "4 fases"


# ----------------------------------------------------------- comparar_routing
def _snap(skills, dw="x", cap="y"):
    return {"skills": sorted(skills), "routing_hash": mod._routing_hash(dw, cap)}


def test_comparar_routing_ok_quando_igual():
    base = {"auditor-financeiro": _snap(["a", "b"])}
    atual = {"auditor-financeiro": _snap(["a", "b"])}
    perigosos, drifts = mod.comparar_routing(atual, base)
    assert perigosos == [] and drifts == []


def test_comparar_routing_BLOQUEIA_skill_nova_sem_revisar_delegate_when():
    # O caso #164: skill adicionada, mas delegate_when/capabilities INALTERADOS.
    base = {"auditor-financeiro": _snap(["a", "b"], dw="recon", cap="5 fluxos")}
    atual = {"auditor-financeiro": _snap(["a", "b", "auditando-reclassificacao-odoo"],
                                         dw="recon", cap="5 fluxos")}
    perigosos, drifts = mod.comparar_routing(atual, base)
    assert len(perigosos) == 1
    assert "auditor-financeiro" in perigosos[0]
    assert "auditando-reclassificacao-odoo" in perigosos[0]


def test_comparar_routing_skill_nova_COM_revisao_nao_e_perigoso():
    # skill nova E delegate_when revisado juntos -> nao bloqueia (so drift, exige update).
    base = {"auditor-financeiro": _snap(["a", "b"], dw="recon", cap="5 fluxos")}
    atual = {"auditor-financeiro": _snap(["a", "b", "c"], dw="recon; reclassificacao", cap="6 fluxos")}
    perigosos, drifts = mod.comparar_routing(atual, base)
    assert perigosos == []
    assert len(drifts) == 1


def test_comparar_routing_delegate_when_mudou_sozinho_e_drift():
    base = {"auditor-financeiro": _snap(["a", "b"], dw="recon", cap="5 fluxos")}
    atual = {"auditor-financeiro": _snap(["a", "b"], dw="recon; reclassificacao", cap="5 fluxos")}
    perigosos, drifts = mod.comparar_routing(atual, base)
    assert perigosos == [] and len(drifts) == 1


def test_comparar_routing_agente_novo_e_drift():
    base = {}
    atual = {"novo-agente": _snap(["a"])}
    perigosos, drifts = mod.comparar_routing(atual, base)
    assert perigosos == [] and len(drifts) == 1
    assert "novo-agente" in drifts[0]


def test_comparar_routing_agente_removido_e_drift():
    base = {"sumiu": _snap(["a"])}
    atual = {}
    perigosos, drifts = mod.comparar_routing(atual, base)
    assert perigosos == [] and len(drifts) == 1


# ----------------------------------------------------------- integracao real
def test_snapshot_routing_estado_real_bate_com_baseline():
    """O estado real do repo deve estar consistente com o baseline versionado
    (se este teste falhar, rode --update-routing-baseline conscientemente)."""
    base = mod.carregar_baseline(mod.ROUTING_BASELINE_PATH)
    assert base is not None, "baseline de roteamento ausente — rode --update-routing-baseline"
    atual = mod.snapshot_routing()
    perigosos, drifts = mod.comparar_routing(atual, base)
    assert perigosos == [], f"gatilho de delegacao desatualizado: {perigosos}"
    assert drifts == [], f"baseline desatualizado: {drifts}"
