"""
Testes TDD para Task T1.1 — Lint de consistencia de roteamento.

3 novos checks em check_consistencia() de prompt_size_audit.py:
  (a) anti-gatilhos em descriptions de SKILL.md citam skills/agents existentes
      (excecoes: planejada, SKILLS_EXTERNAS_ROUTING)
  (b) contagens declaradas no ROUTING_SKILLS.md = contagem real de skills
  (c) budget por subagente: soma descriptions declaradas em agents ≤ 8000c
      (WARNING por enquanto — BUDGET_SUBAGENTE_ENFORCE = False inicialmente)

Padrao: sem DB, sem Flask — puro filesystem (tmp_path) + importlib.
"""
import importlib.util
import textwrap
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/audits/prompt_size_audit.py"


def _carregar_modulo():
    spec = importlib.util.spec_from_file_location("prompt_size_audit_t11", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


mod = _carregar_modulo()


# ================================================================ helpers fixtures

def _escrever_skill_md(skills_dir: Path, nome: str, description: str) -> None:
    """Cria um diretorio com SKILL.md minimo para testes."""
    d = skills_dir / nome
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        textwrap.dedent(f"""\
        ---
        name: {nome}
        description: >-
          {description}
        allowed-tools: Read, Bash
        ---
        # {nome}
        """),
        encoding="utf-8",
    )


def _escrever_agent_md(agents_dir: Path, nome: str, skills: list[str]) -> None:
    """Cria .claude/agents/<nome>.md com frontmatter skills."""
    skills_yaml = "\n".join(f"  - {s}" for s in skills)
    (agents_dir / f"{nome}.md").write_text(
        textwrap.dedent(f"""\
        ---
        name: {nome}
        description: Agente de teste {nome}.
        tools: Read
        skills:
        {skills_yaml}
        ---
        # {nome}
        """),
        encoding="utf-8",
    )


def _escrever_routing_skills(refs_dir: Path, total: int, secoes: dict[str, list[str]]) -> None:
    """Cria ROUTING_SKILLS.md minimo com headline de contagem e subsecoes."""
    linhas = [
        f"## Skills — Inventario Completo ({total} invocaveis em `.claude/skills/`)",
        "",
        "Texto intro.",
        "",
    ]
    for grupo, skills in secoes.items():
        linhas.append(f"### {grupo} ({len(skills)})")
        for s in skills:
            linhas.append(f"`{s}` descricao aqui,")
        linhas.append("")
    (refs_dir / "ROUTING_SKILLS.md").write_text("\n".join(linhas), encoding="utf-8")


# ================================================================ (a) anti-gatilhos

class TestCheckAntiGatilhos:
    """Check (a): referencias mortas em Anti:/NAO_USAR_PARA de descriptions."""

    def test_sem_anti_gatilho_ok(self, tmp_path):
        """Skill sem nenhum '->' na description nao gera erro."""
        skills_dir = tmp_path / ".claude/skills"
        _escrever_skill_md(skills_dir, "skill-a", "Faz A. Usar quando X.")
        erros, avisos = mod.check_anti_gatilhos(
            skills_dir=skills_dir,
            agents_stems=set(),
            skills_externas=set(),
        )
        assert erros == []

    def test_anti_gatilho_skill_existente_ok(self, tmp_path):
        """'->' apontando para skill que existe no fs nao gera erro."""
        skills_dir = tmp_path / ".claude/skills"
        _escrever_skill_md(skills_dir, "skill-a", "Faz A. Anti: nao x -> skill-b.")
        _escrever_skill_md(skills_dir, "skill-b", "Faz B.")
        erros, avisos = mod.check_anti_gatilhos(
            skills_dir=skills_dir,
            agents_stems=set(),
            skills_externas=set(),
        )
        assert erros == []

    def test_anti_gatilho_agente_existente_ok(self, tmp_path):
        """'->' apontando para nome de agente existente nao gera erro."""
        skills_dir = tmp_path / ".claude/skills"
        _escrever_skill_md(skills_dir, "skill-a",
                           "Faz A. Anti: complexo -> meu-agente-teste.")
        erros, avisos = mod.check_anti_gatilhos(
            skills_dir=skills_dir,
            agents_stems={"meu-agente-teste"},
            skills_externas=set(),
        )
        assert erros == []

    def test_anti_gatilho_externa_ok(self, tmp_path):
        """'->' apontando para skill em SKILLS_EXTERNAS_ROUTING nao gera erro."""
        skills_dir = tmp_path / ".claude/skills"
        _escrever_skill_md(skills_dir, "skill-a",
                           "Faz A. Criar integracao -> integracao-odoo.")
        erros, avisos = mod.check_anti_gatilhos(
            skills_dir=skills_dir,
            agents_stems=set(),
            skills_externas={"integracao-odoo"},
        )
        assert erros == []

    def test_anti_gatilho_planejada_ok(self, tmp_path):
        """'->' para skill nao existente MAS marcada (planejada) nao gera erro."""
        skills_dir = tmp_path / ".claude/skills"
        _escrever_skill_md(
            skills_dir, "skill-a",
            "Faz A. Nao: -> skill-futura (planejada — ainda nao existe)."
        )
        erros, avisos = mod.check_anti_gatilhos(
            skills_dir=skills_dir,
            agents_stems=set(),
            skills_externas=set(),
        )
        assert erros == []

    def test_anti_gatilho_morto_gera_erro(self, tmp_path):
        """'->' para skill que nao existe e nao e planejada nem externa -> ERRO."""
        skills_dir = tmp_path / ".claude/skills"
        _escrever_skill_md(
            skills_dir, "skill-a",
            "Faz A. Anti: fazer X -> skill-morta."
        )
        erros, avisos = mod.check_anti_gatilhos(
            skills_dir=skills_dir,
            agents_stems=set(),
            skills_externas=set(),
        )
        assert any("skill-morta" in e for e in erros)
        assert any("skill-a" in e for e in erros)

    def test_anti_gatilho_sem_skill_md_mas_diretorio_ok(self, tmp_path):
        """Skill em SKILLS_SEM_SKILL_MD (diretorio sem SKILL.md) e valida como destino."""
        skills_dir = tmp_path / ".claude/skills"
        # consultar-sql: diretorio sem SKILL.md
        (skills_dir / "consultando-sql").mkdir(parents=True)
        _escrever_skill_md(
            skills_dir, "skill-a",
            "Faz A. Nao analitico -> consultando-sql."
        )
        erros, avisos = mod.check_anti_gatilhos(
            skills_dir=skills_dir,
            agents_stems=set(),
            skills_externas=set(),
        )
        # consultando-sql existe como diretorio -> valido
        assert not any("consultando-sql" in e for e in erros)

    def test_skill_sem_hifen_nao_capturada(self, tmp_path):
        """Palavras sem hifen apos '->' nao devem ser tratadas como nome de skill."""
        skills_dir = tmp_path / ".claude/skills"
        _escrever_skill_md(
            skills_dir, "skill-a",
            "Faz A. Nao usar para escrita -> usar outra abordagem."
        )
        erros, avisos = mod.check_anti_gatilhos(
            skills_dir=skills_dir,
            agents_stems=set(),
            skills_externas=set(),
        )
        # "outra" e "abordagem" nao tem hifen -> nao devem gerar erro
        assert erros == []

    def test_repo_real_nao_tem_anti_gatilhos_mortos(self):
        """Verifica que o repositorio atual nao tem referencias mortas apos excecoes."""
        # Este teste usa o repo real — deve passar apos a implementacao das constantes
        skills_dir = ROOT / ".claude/skills"
        agents_dir = ROOT / ".claude/agents"
        agents_stems = {p.stem for p in agents_dir.glob("*.md")}
        erros, avisos = mod.check_anti_gatilhos(
            skills_dir=skills_dir,
            agents_stems=agents_stems,
            skills_externas=mod.SKILLS_EXTERNAS_ROUTING,
        )
        assert erros == [], f"Anti-gatilhos mortos no repo: {erros}"


# ================================================================ (b) contagens ROUTING

class TestCheckContagensRouting:
    """Check (b): contagens declaradas no ROUTING_SKILLS.md == real."""

    def test_contagens_corretas_ok(self, tmp_path):
        """Contagens declaradas iguais ao real -> sem erros."""
        skills_dir = tmp_path / ".claude/skills"
        refs_dir = tmp_path / ".claude/references"
        refs_dir.mkdir(parents=True)
        _escrever_skill_md(skills_dir, "skill-a", "Faz A.")
        _escrever_skill_md(skills_dir, "skill-b", "Faz B.")
        _escrever_routing_skills(
            refs_dir, total=2,
            secoes={"Grupo A (2)": ["skill-a", "skill-b"]}
        )
        erros, avisos = mod.check_contagens_routing(
            routing_path=refs_dir / "ROUTING_SKILLS.md",
            skills_validas={"skill-a", "skill-b"},
        )
        assert erros == []

    def test_total_errado_gera_erro(self, tmp_path):
        """Total declarado != real -> ERRO."""
        skills_dir = tmp_path / ".claude/skills"
        refs_dir = tmp_path / ".claude/references"
        refs_dir.mkdir(parents=True)
        _escrever_skill_md(skills_dir, "skill-a", "Faz A.")
        _escrever_skill_md(skills_dir, "skill-b", "Faz B.")
        # declara 3 mas só 2 existem
        _escrever_routing_skills(
            refs_dir, total=3,
            secoes={"Grupo A (2)": ["skill-a", "skill-b"]}
        )
        erros, avisos = mod.check_contagens_routing(
            routing_path=refs_dir / "ROUTING_SKILLS.md",
            skills_validas={"skill-a", "skill-b"},
        )
        assert any("53" in e or "total" in e.lower() or "invocaveis" in e for e in erros), f"erros={erros}"

    def test_subsecao_errada_gera_erro(self, tmp_path):
        """Subsecao com contagem errada -> ERRO."""
        refs_dir = tmp_path / ".claude/references"
        refs_dir.mkdir(parents=True)
        # declara subsecao com 3 mas lista apenas 2
        linhas = [
            "## Skills — Inventario Completo (2 invocaveis em `.claude/skills/`)",
            "",
            "### Grupo X (3)",
            "`skill-a` desc,",
            "`skill-b` desc,",
            "",
        ]
        (refs_dir / "ROUTING_SKILLS.md").write_text("\n".join(linhas), encoding="utf-8")
        erros, avisos = mod.check_contagens_routing(
            routing_path=refs_dir / "ROUTING_SKILLS.md",
            skills_validas={"skill-a", "skill-b"},
        )
        assert any("Grupo X" in e or "grupo x" in e.lower() for e in erros), f"erros={erros}"

    def test_routing_ausente_retorna_aviso(self, tmp_path):
        """Arquivo ROUTING_SKILLS.md ausente -> aviso (nao erro bloqueador)."""
        erros, avisos = mod.check_contagens_routing(
            routing_path=tmp_path / "naoexiste.md",
            skills_validas={"skill-a"},
        )
        assert erros == []
        assert len(avisos) == 1

    def test_repo_real_contagens_ok(self):
        """Verifica que o repositorio real tem contagens consistentes."""
        skills_dir = ROOT / ".claude/skills"
        skills_validas = {p.parent.name for p in skills_dir.glob("*/SKILL.md")}
        skills_validas |= mod.SKILLS_SEM_SKILL_MD
        erros, avisos = mod.check_contagens_routing(
            routing_path=ROOT / ".claude/references/ROUTING_SKILLS.md",
            skills_validas=skills_validas,
        )
        assert erros == [], f"Contagens erradas no repo: {erros}"


# ================================================================ (c) budget subagente

class TestCheckBudgetSubagente:
    """Check (c): soma das descriptions de skills declaradas em agents <= 8000c."""

    def test_agente_sem_skills_ok(self, tmp_path):
        """Agente sem frontmatter skills nao gera aviso."""
        agents_dir = tmp_path / ".claude/agents"
        agents_dir.mkdir(parents=True)
        skills_dir = tmp_path / ".claude/skills"
        (agents_dir / "agente-x.md").write_text(
            "---\nname: agente-x\ndescription: Agente X.\ntools: Read\n---\n# agente-x\n",
            encoding="utf-8",
        )
        erros, avisos = mod.check_budget_subagentes(
            agents_dir=agents_dir,
            skills_dir=skills_dir,
            limite=8000,
        )
        assert erros == []
        assert avisos == []

    def test_agente_dentro_do_budget_ok(self, tmp_path):
        """Agente com skills cujas descriptions somam < limite -> sem aviso."""
        agents_dir = tmp_path / ".claude/agents"
        agents_dir.mkdir(parents=True)
        skills_dir = tmp_path / ".claude/skills"
        # Desc curta: ~30 chars
        _escrever_skill_md(skills_dir, "skill-x", "Faz X curto aqui mesmo.")
        _escrever_agent_md(agents_dir, "agente-a", ["skill-x"])
        erros, avisos = mod.check_budget_subagentes(
            agents_dir=agents_dir,
            skills_dir=skills_dir,
            limite=8000,
        )
        assert erros == []
        assert avisos == []

    def test_agente_acima_do_budget_gera_aviso(self, tmp_path):
        """Agente com skills que somam > limite -> AVISO (nao erro quando ENFORCE=False)."""
        agents_dir = tmp_path / ".claude/agents"
        agents_dir.mkdir(parents=True)
        skills_dir = tmp_path / ".claude/skills"
        # Criar uma description longa o suficiente para ultrapassar o limite
        desc_longa = "X " * 4100  # ~8200 chars de description
        _escrever_skill_md(skills_dir, "skill-grande", desc_longa.strip())
        _escrever_agent_md(agents_dir, "agente-gordo", ["skill-grande"])
        erros, avisos = mod.check_budget_subagentes(
            agents_dir=agents_dir,
            skills_dir=skills_dir,
            limite=8000,
            enforce=False,
        )
        assert erros == []
        assert any("agente-gordo" in a for a in avisos)
        assert any("BUDGET" in a.upper() for a in avisos)

    def test_agente_acima_do_budget_enforce_gera_erro(self, tmp_path):
        """Com enforce=True, budget excedido vira ERRO (para T1.2)."""
        agents_dir = tmp_path / ".claude/agents"
        agents_dir.mkdir(parents=True)
        skills_dir = tmp_path / ".claude/skills"
        desc_longa = "Y " * 4100
        _escrever_skill_md(skills_dir, "skill-pesada", desc_longa.strip())
        _escrever_agent_md(agents_dir, "agente-pesado", ["skill-pesada"])
        erros, avisos = mod.check_budget_subagentes(
            agents_dir=agents_dir,
            skills_dir=skills_dir,
            limite=8000,
            enforce=True,
        )
        assert any("agente-pesado" in e for e in erros)

    def test_skill_sem_skill_md_ignorada_no_budget(self, tmp_path):
        """Skill declarada sem SKILL.md (como consultando-sql) nao conta no budget."""
        agents_dir = tmp_path / ".claude/agents"
        agents_dir.mkdir(parents=True)
        skills_dir = tmp_path / ".claude/skills"
        # consultando-sql: diretorio sem SKILL.md
        (skills_dir / "consultando-sql").mkdir(parents=True)
        _escrever_agent_md(agents_dir, "agente-sql", ["consultando-sql"])
        erros, avisos = mod.check_budget_subagentes(
            agents_dir=agents_dir,
            skills_dir=skills_dir,
            limite=8000,
        )
        assert erros == []
        assert avisos == []

    def test_repo_real_gestor_estoque_odoo_emite_aviso(self):
        """gestor-estoque-odoo no repo real deve emitir AVISO BUDGET (> 8000c)."""
        erros, avisos = mod.check_budget_subagentes(
            agents_dir=ROOT / ".claude/agents",
            skills_dir=ROOT / ".claude/skills",
            limite=8000,
            enforce=False,
        )
        # gestor-estoque-odoo esta acima do limite
        assert any("gestor-estoque-odoo" in a for a in avisos), (
            f"Esperava aviso para gestor-estoque-odoo. avisos={avisos}"
        )

    def test_repo_real_enforce_false_nao_gera_erros_de_budget(self):
        """Com enforce=False, nenhum agente deve gerar ERRO (so avisos)."""
        erros, _ = mod.check_budget_subagentes(
            agents_dir=ROOT / ".claude/agents",
            skills_dir=ROOT / ".claude/skills",
            limite=8000,
            enforce=False,
        )
        assert erros == [], f"Nenhum erro de budget esperado com enforce=False. erros={erros}"


# ================================================================ integracao: check_consistencia()

class TestCheckConsistenciaIntegrado:
    """Testa que check_consistencia() invoca os 3 novos checks e propaga resultados."""

    def test_check_consistencia_inclui_novos_checks(self):
        """check_consistencia() no repo real deve rodar sem erros nos checks novos."""
        erros, avisos = mod.check_consistencia()
        # Checks (a) e (b) devem ser limpos
        # Verificar que nenhum erro menciona anti-gatilho ou contagem errada no routing
        erros_novos = [e for e in erros if "anti-gatilho" in e.lower()
                       or "routing_skills" in e.lower()
                       or "contagem" in e.lower()]
        assert erros_novos == [], f"Erros novos inesperados: {erros_novos}"

    def test_check_consistencia_aviso_budget_propagado(self):
        """AVISO BUDGET deve aparecer nos avisos de check_consistencia()."""
        erros, avisos = mod.check_consistencia()
        # Com BUDGET_SUBAGENTE_ENFORCE=False, deve ter pelo menos 1 aviso de budget
        avisos_budget = [a for a in avisos if "BUDGET" in a.upper() or "budget" in a.lower()]
        assert len(avisos_budget) >= 1, (
            f"Esperava ao menos 1 aviso de budget. avisos={avisos}"
        )
