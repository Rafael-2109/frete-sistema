"""
Testes TDD para Task T1.1 — Lint de consistencia de roteamento.

Checks em check_consistencia() de prompt_size_audit.py:
  (a) skills citadas existem — 4 fontes:
      a.1 anti-gatilhos em descriptions de SKILL.md (check_anti_gatilhos)
      a.2 nomes listados no inventario do ROUTING_SKILLS.md
          (check_nomes_inventario_routing — nome em prosa parentetica e isento)
      a.3 chaves de SKILL_TO_CATEGORY do tool_skill_mapper.py (check_chaves_mapper
          — validas tambem via .claude/commands/*.md)
      a.4 skills declaradas no frontmatter de agents (check_skills_declaradas_agents
          — ERRO se o DIRETORIO nao existe; WARNING se so falta SKILL.md)
      (excecoes: '(planejada', SKILLS_EXTERNAS_ROUTING, SKILLS_SEM_SKILL_MD)
  (b) contagens declaradas no ROUTING_SKILLS.md = contagem real de skills
  (c) budget por subagente: soma descriptions declaradas em agents ≤ 8000c
      (WARNING por enquanto — BUDGET_SUBAGENTE_ENFORCE = False inicialmente)

Padrao: sem DB, sem Flask — puro filesystem (tmp_path) + importlib.
"""
import importlib.util
import textwrap
from pathlib import Path

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


def _escrever_mapper(path: Path, chaves: list[str]) -> None:
    """Cria um tool_skill_mapper.py minimo com SKILL_TO_CATEGORY."""
    corpo = "\n".join(f"    '{c}': 'Categoria X'," for c in chaves)
    path.write_text(
        f"SKILL_TO_CATEGORY = {{\n{corpo}\n}}\n",
        encoding="utf-8",
    )


# ================================================================ (a.1) anti-gatilhos

class TestCheckAntiGatilhos:
    """Check (a.1): referencias mortas em Anti:/NAO_USAR_PARA de descriptions."""

    def test_sem_anti_gatilho_ok(self, tmp_path):
        """Skill sem nenhum '->' na description nao gera erro."""
        skills_dir = tmp_path / ".claude/skills"
        _escrever_skill_md(skills_dir, "skill-a", "Faz A. Usar quando X.")
        erros, _ = mod.check_anti_gatilhos(
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
        erros, _ = mod.check_anti_gatilhos(
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
        erros, _ = mod.check_anti_gatilhos(
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
        erros, _ = mod.check_anti_gatilhos(
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
        erros, _ = mod.check_anti_gatilhos(
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
        erros, _ = mod.check_anti_gatilhos(
            skills_dir=skills_dir,
            agents_stems=set(),
            skills_externas=set(),
        )
        assert any("skill-morta" in e for e in erros)
        assert any("skill-a" in e for e in erros)

    def test_anti_gatilho_sem_skill_md_mas_diretorio_ok(self, tmp_path):
        """Skill em SKILLS_SEM_SKILL_MD (diretorio sem SKILL.md) e valida como destino."""
        skills_dir = tmp_path / ".claude/skills"
        # consultando-sql: diretorio sem SKILL.md
        (skills_dir / "consultando-sql").mkdir(parents=True)
        _escrever_skill_md(
            skills_dir, "skill-a",
            "Faz A. Nao analitico -> consultando-sql."
        )
        erros, _ = mod.check_anti_gatilhos(
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
        erros, _ = mod.check_anti_gatilhos(
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
        erros, _ = mod.check_anti_gatilhos(
            skills_dir=skills_dir,
            agents_stems=agents_stems,
            skills_externas=mod.SKILLS_EXTERNAS_ROUTING,
        )
        assert erros == [], f"Anti-gatilhos mortos no repo: {erros}"


# ============================================== (a.2) nomes do inventario ROUTING

class TestCheckNomesInventarioRouting:
    """Check (a.2): nomes listados COMO SKILL no inventario do ROUTING_SKILLS.md
    devem existir. Nomes em prosa parentetica (anotacao/deprecated) sao isentos."""

    def test_nomes_validos_ok(self, tmp_path):
        refs_dir = tmp_path / ".claude/references"
        refs_dir.mkdir(parents=True)
        skills_dir = tmp_path / ".claude/skills"
        _escrever_skill_md(skills_dir, "skill-a", "Faz A.")
        _escrever_skill_md(skills_dir, "skill-b", "Faz B.")
        _escrever_routing_skills(
            refs_dir, total=2,
            secoes={"Grupo A (2)": ["skill-a", "skill-b"]}
        )
        erros, _ = mod.check_nomes_inventario_routing(
            routing_path=refs_dir / "ROUTING_SKILLS.md",
            skills_dir=skills_dir,
            agents_stems=set(),
            skills_externas=set(),
        )
        assert erros == []

    def test_nome_morto_listado_gera_erro(self, tmp_path):
        """Nome morto listado COMO SKILL (fora de parenteses) -> ERRO."""
        refs_dir = tmp_path / ".claude/references"
        refs_dir.mkdir(parents=True)
        skills_dir = tmp_path / ".claude/skills"
        _escrever_skill_md(skills_dir, "skill-a", "Faz A.")
        linhas = [
            "## Skills — Inventario Completo (2 invocaveis em `.claude/skills/`)",
            "",
            "### Grupo A (2)",
            "`skill-a`, `skill-fantasma`",
            "",
        ]
        (refs_dir / "ROUTING_SKILLS.md").write_text("\n".join(linhas), encoding="utf-8")
        erros, _ = mod.check_nomes_inventario_routing(
            routing_path=refs_dir / "ROUTING_SKILLS.md",
            skills_dir=skills_dir,
            agents_stems=set(),
            skills_externas=set(),
        )
        assert any("skill-fantasma" in e for e in erros), f"erros={erros}"

    def test_nome_morto_em_prosa_parentetica_isento(self, tmp_path):
        """Nome morto DENTRO de parenteses (anotacao deprecated) -> sem erro."""
        refs_dir = tmp_path / ".claude/references"
        refs_dir.mkdir(parents=True)
        skills_dir = tmp_path / ".claude/skills"
        _escrever_skill_md(skills_dir, "skill-a", "Faz A.")
        linhas = [
            "## Skills — Inventario Completo (1 invocaveis em `.claude/skills/`)",
            "",
            "### Grupo A (1)",
            "`skill-a` (substitui `skill-velha` — deprecated)",
            "",
        ]
        (refs_dir / "ROUTING_SKILLS.md").write_text("\n".join(linhas), encoding="utf-8")
        erros, _ = mod.check_nomes_inventario_routing(
            routing_path=refs_dir / "ROUTING_SKILLS.md",
            skills_dir=skills_dir,
            agents_stems=set(),
            skills_externas=set(),
        )
        assert erros == [], f"prosa parentetica nao deve gerar erro: {erros}"

    def test_nome_agente_listado_valido(self, tmp_path):
        """Nome de agente citado depth-0 (ex.: no heading) e valido."""
        refs_dir = tmp_path / ".claude/references"
        refs_dir.mkdir(parents=True)
        skills_dir = tmp_path / ".claude/skills"
        _escrever_skill_md(skills_dir, "skill-a", "Faz A.")
        linhas = [
            "## Skills — Inventario Completo (1 invocaveis em `.claude/skills/`)",
            "",
            "### Grupo A (1) — USO EXCLUSIVO do subagent `agente-dono`",
            "`skill-a` desc",
            "",
        ]
        (refs_dir / "ROUTING_SKILLS.md").write_text("\n".join(linhas), encoding="utf-8")
        erros, _ = mod.check_nomes_inventario_routing(
            routing_path=refs_dir / "ROUTING_SKILLS.md",
            skills_dir=skills_dir,
            agents_stems={"agente-dono"},
            skills_externas=set(),
        )
        assert erros == []

    def test_nome_planejada_isento(self, tmp_path):
        """Nome listado seguido de '(planejada' e isento."""
        refs_dir = tmp_path / ".claude/references"
        refs_dir.mkdir(parents=True)
        skills_dir = tmp_path / ".claude/skills"
        _escrever_skill_md(skills_dir, "skill-a", "Faz A.")
        linhas = [
            "## Skills — Inventario Completo (1 invocaveis em `.claude/skills/`)",
            "",
            "### Grupo A (1)",
            "`skill-a` desc, `skill-futura` (planejada — ainda nao existe)",
            "",
        ]
        (refs_dir / "ROUTING_SKILLS.md").write_text("\n".join(linhas), encoding="utf-8")
        erros, _ = mod.check_nomes_inventario_routing(
            routing_path=refs_dir / "ROUTING_SKILLS.md",
            skills_dir=skills_dir,
            agents_stems=set(),
            skills_externas=set(),
        )
        assert erros == []

    def test_repo_real_inventario_sem_nomes_mortos(self):
        """Inventario do ROUTING_SKILLS.md real nao tem nomes mortos listados."""
        agents_stems = {p.stem for p in (ROOT / ".claude/agents").glob("*.md")}
        erros, _ = mod.check_nomes_inventario_routing(
            routing_path=ROOT / ".claude/references/ROUTING_SKILLS.md",
            skills_dir=ROOT / ".claude/skills",
            agents_stems=agents_stems,
            skills_externas=mod.SKILLS_EXTERNAS_ROUTING,
        )
        assert erros == [], f"Nomes mortos no inventario do ROUTING: {erros}"


# ============================================== (a.3) chaves do tool_skill_mapper

class TestCheckChavesMapper:
    """Check (a.3): chaves de SKILL_TO_CATEGORY devem existir como skill dir,
    command (.claude/commands/*.md), agent ou SKILLS_EXTERNAS_ROUTING."""

    def test_chave_skill_dir_ok(self, tmp_path):
        mapper = tmp_path / "mapper.py"
        _escrever_mapper(mapper, ["skill-a"])
        skills_dir = tmp_path / ".claude/skills"
        _escrever_skill_md(skills_dir, "skill-a", "Faz A.")
        erros, _ = mod.check_chaves_mapper(
            mapper_path=mapper,
            skills_dir=skills_dir,
            commands_dir=tmp_path / ".claude/commands",
            agents_stems=set(),
            skills_externas=set(),
        )
        assert erros == []

    def test_chave_command_ok(self, tmp_path):
        """Chave que vive em .claude/commands/*.md (ex.: analise-carteira) e valida."""
        mapper = tmp_path / "mapper.py"
        _escrever_mapper(mapper, ["comando-x"])
        commands_dir = tmp_path / ".claude/commands"
        commands_dir.mkdir(parents=True)
        (commands_dir / "comando-x.md").write_text("# comando-x\n", encoding="utf-8")
        erros, _ = mod.check_chaves_mapper(
            mapper_path=mapper,
            skills_dir=tmp_path / ".claude/skills",
            commands_dir=commands_dir,
            agents_stems=set(),
            skills_externas=set(),
        )
        assert erros == []

    def test_chave_externa_ok(self, tmp_path):
        mapper = tmp_path / "mapper.py"
        _escrever_mapper(mapper, ["integracao-odoo"])
        erros, _ = mod.check_chaves_mapper(
            mapper_path=mapper,
            skills_dir=tmp_path / ".claude/skills",
            commands_dir=tmp_path / ".claude/commands",
            agents_stems=set(),
            skills_externas={"integracao-odoo"},
        )
        assert erros == []

    def test_chave_morta_gera_erro(self, tmp_path):
        mapper = tmp_path / "mapper.py"
        _escrever_mapper(mapper, ["skill-zumbi"])
        erros, _ = mod.check_chaves_mapper(
            mapper_path=mapper,
            skills_dir=tmp_path / ".claude/skills",
            commands_dir=tmp_path / ".claude/commands",
            agents_stems=set(),
            skills_externas=set(),
        )
        assert any("skill-zumbi" in e for e in erros), f"erros={erros}"

    def test_mapper_ausente_retorna_aviso(self, tmp_path):
        erros, avisos = mod.check_chaves_mapper(
            mapper_path=tmp_path / "naoexiste.py",
            skills_dir=tmp_path / ".claude/skills",
            commands_dir=tmp_path / ".claude/commands",
            agents_stems=set(),
            skills_externas=set(),
        )
        assert erros == []
        assert len(avisos) == 1

    def test_repo_real_mapper_sem_chaves_mortas(self):
        """SKILL_TO_CATEGORY real nao tem chaves mortas."""
        agents_stems = {p.stem for p in (ROOT / ".claude/agents").glob("*.md")}
        erros, _ = mod.check_chaves_mapper(
            mapper_path=ROOT / "app/agente/services/tool_skill_mapper.py",
            skills_dir=ROOT / ".claude/skills",
            commands_dir=ROOT / ".claude/commands",
            agents_stems=agents_stems,
            skills_externas=mod.SKILLS_EXTERNAS_ROUTING,
        )
        assert erros == [], f"Chaves mortas no mapper: {erros}"


# ============================================== (a.4) skills declaradas em agents

class TestCheckSkillsDeclaradasAgents:
    """Check (a.4): skill declarada no frontmatter de agent — ERRO se o diretorio
    nao existe; WARNING se diretorio existe mas falta SKILL.md (fora de
    SKILLS_SEM_SKILL_MD)."""

    def test_skill_com_skill_md_ok(self, tmp_path):
        agents_dir = tmp_path / ".claude/agents"
        agents_dir.mkdir(parents=True)
        skills_dir = tmp_path / ".claude/skills"
        _escrever_skill_md(skills_dir, "skill-a", "Faz A.")
        _escrever_agent_md(agents_dir, "agente-a", ["skill-a"])
        erros, avisos = mod.check_skills_declaradas_agents(
            agents_dir=agents_dir,
            skills_dir=skills_dir,
            skills_sem_skill_md=set(),
        )
        assert erros == []
        assert avisos == []

    def test_skill_sem_diretorio_gera_erro(self, tmp_path):
        """Skill declarada cujo diretorio NAO existe -> ERRO."""
        agents_dir = tmp_path / ".claude/agents"
        agents_dir.mkdir(parents=True)
        skills_dir = tmp_path / ".claude/skills"
        skills_dir.mkdir(parents=True)
        _escrever_agent_md(agents_dir, "agente-b", ["skill-inexistente"])
        erros, _ = mod.check_skills_declaradas_agents(
            agents_dir=agents_dir,
            skills_dir=skills_dir,
            skills_sem_skill_md=set(),
        )
        assert any("skill-inexistente" in e for e in erros), f"erros={erros}"
        assert any("agente-b" in e for e in erros)

    def test_diretorio_sem_skill_md_gera_warning(self, tmp_path):
        """Diretorio existe mas sem SKILL.md (fora da excecao) -> WARNING."""
        agents_dir = tmp_path / ".claude/agents"
        agents_dir.mkdir(parents=True)
        skills_dir = tmp_path / ".claude/skills"
        (skills_dir / "skill-semdoc").mkdir(parents=True)
        _escrever_agent_md(agents_dir, "agente-c", ["skill-semdoc"])
        erros, avisos = mod.check_skills_declaradas_agents(
            agents_dir=agents_dir,
            skills_dir=skills_dir,
            skills_sem_skill_md=set(),
        )
        assert erros == []
        assert any("skill-semdoc" in a for a in avisos), f"avisos={avisos}"

    def test_skills_sem_skill_md_excecao_sem_warning(self, tmp_path):
        """Skill em SKILLS_SEM_SKILL_MD com diretorio -> nem erro nem warning."""
        agents_dir = tmp_path / ".claude/agents"
        agents_dir.mkdir(parents=True)
        skills_dir = tmp_path / ".claude/skills"
        (skills_dir / "consultando-sql").mkdir(parents=True)
        _escrever_agent_md(agents_dir, "agente-d", ["consultando-sql"])
        erros, avisos = mod.check_skills_declaradas_agents(
            agents_dir=agents_dir,
            skills_dir=skills_dir,
            skills_sem_skill_md={"consultando-sql"},
        )
        assert erros == []
        assert avisos == []

    def test_repo_real_agents_sem_skills_inexistentes(self):
        """Nenhum agent real declara skill cujo diretorio nao existe."""
        erros, _ = mod.check_skills_declaradas_agents(
            agents_dir=ROOT / ".claude/agents",
            skills_dir=ROOT / ".claude/skills",
            skills_sem_skill_md=mod.SKILLS_SEM_SKILL_MD,
        )
        assert erros == [], f"Agents com skills inexistentes: {erros}"


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
        erros, _ = mod.check_contagens_routing(
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
        erros, _ = mod.check_contagens_routing(
            routing_path=refs_dir / "ROUTING_SKILLS.md",
            skills_validas={"skill-a", "skill-b"},
        )
        assert any("total" in e.lower() or "invocaveis" in e for e in erros), f"erros={erros}"

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
        erros, _ = mod.check_contagens_routing(
            routing_path=refs_dir / "ROUTING_SKILLS.md",
            skills_validas={"skill-a", "skill-b"},
        )
        assert any("Grupo X" in e or "grupo x" in e.lower() for e in erros), f"erros={erros}"

    def test_nome_em_prosa_parentetica_nao_conta(self, tmp_path):
        """Nome valido citado em prosa parentetica NAO conta na subsecao."""
        refs_dir = tmp_path / ".claude/references"
        refs_dir.mkdir(parents=True)
        linhas = [
            "## Skills — Inventario Completo (2 invocaveis em `.claude/skills/`)",
            "",
            "### Grupo A (2)",
            "`skill-a` (compoe com `skill-b`), `skill-b`",
            "",
        ]
        (refs_dir / "ROUTING_SKILLS.md").write_text("\n".join(linhas), encoding="utf-8")
        erros, _ = mod.check_contagens_routing(
            routing_path=refs_dir / "ROUTING_SKILLS.md",
            skills_validas={"skill-a", "skill-b"},
        )
        # skill-b em prosa nao conta; lista real = [skill-a, skill-b] = 2 == declarado
        assert erros == [], f"erros={erros}"

    def test_routing_ausente_retorna_aviso(self, tmp_path):
        """Arquivo ROUTING_SKILLS.md ausente -> aviso (nao erro bloqueador)."""
        erros, avisos = mod.check_contagens_routing(
            routing_path=tmp_path / "naoexiste.md",
            skills_validas={"skill-a"},
        )
        assert erros == []
        assert len(avisos) == 1

    def test_heading_renomeado_emite_aviso(self, tmp_path):
        """Routing EXISTE mas heading/headline renomeados -> AVISO (lint nao
        pode se auto-desarmar em silencio)."""
        refs_dir = tmp_path / ".claude/references"
        refs_dir.mkdir(parents=True)
        # heading com hifen no lugar do em-dash + headline sem '(N invocaveis'
        linhas = [
            "## Skills - Inventario Completo (2 skills)",
            "",
            "### Grupo A (2)",
            "`skill-a` desc,",
            "`skill-b` desc,",
            "",
        ]
        (refs_dir / "ROUTING_SKILLS.md").write_text("\n".join(linhas), encoding="utf-8")
        erros, avisos = mod.check_contagens_routing(
            routing_path=refs_dir / "ROUTING_SKILLS.md",
            skills_validas={"skill-a", "skill-b"},
        )
        assert erros == []
        # headline nao encontrada + nenhuma subsecao parseada (heading do
        # inventario renomeado) = 2 avisos
        assert len(avisos) == 2, f"avisos={avisos}"
        assert any("headline" in a for a in avisos)
        assert any("subsecao" in a for a in avisos)

    def test_heading_renomeado_emite_aviso_nomes_inventario(self, tmp_path):
        """check_nomes_inventario_routing tambem avisa com heading renomeado."""
        refs_dir = tmp_path / ".claude/references"
        refs_dir.mkdir(parents=True)
        (refs_dir / "ROUTING_SKILLS.md").write_text(
            "## Skills - Inventario (renomeado)\n\n### Grupo A (1)\n`skill-x`\n",
            encoding="utf-8",
        )
        erros, avisos = mod.check_nomes_inventario_routing(
            routing_path=refs_dir / "ROUTING_SKILLS.md",
            skills_dir=tmp_path / ".claude/skills",
            agents_stems=set(),
            skills_externas=set(),
        )
        assert erros == []
        assert len(avisos) == 1, f"avisos={avisos}"
        assert "subsecao" in avisos[0]

    def test_repo_real_contagens_ok(self):
        """Verifica que o repositorio real tem contagens consistentes."""
        skills_dir = ROOT / ".claude/skills"
        skills_validas = {p.parent.name for p in skills_dir.glob("*/SKILL.md")}
        skills_validas |= mod.SKILLS_SEM_SKILL_MD
        erros, _ = mod.check_contagens_routing(
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
        erros, _ = mod.check_budget_subagentes(
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

    def test_repo_real_nenhum_subagente_acima_do_budget(self):
        """T1.2 (invertido): NENHUM subagente do repo real emite aviso/erro de budget.

        Antes da T1.2 este teste assertava a violacao de gestor-estoque-odoo
        (15391c > 8000c). Apos a reducao das descriptions (<=600c, matriz
        movida para o corpo das SKILL.md), o estado limpo e' o invariante.
        """
        erros, avisos = mod.check_budget_subagentes(
            agents_dir=ROOT / ".claude/agents",
            skills_dir=ROOT / ".claude/skills",
            limite=8000,
            enforce=mod.BUDGET_SUBAGENTE_ENFORCE,
        )
        assert erros == [], f"Nenhum erro de budget esperado. erros={erros}"
        assert avisos == [], f"Nenhum aviso de budget esperado. avisos={avisos}"

    def test_budget_subagente_enforce_flipado(self):
        """T1.2: BUDGET_SUBAGENTE_ENFORCE deve estar True (estado limpo atingido)."""
        assert mod.BUDGET_SUBAGENTE_ENFORCE is True

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
    """Testa que check_consistencia() invoca os novos checks e propaga resultados."""

    def test_check_consistencia_inclui_novos_checks(self):
        """check_consistencia() no repo real deve rodar sem erros nos checks novos."""
        erros, _ = mod.check_consistencia()
        # Checks (a) e (b) devem ser limpos
        # Verificar que nenhum erro menciona anti-gatilho ou contagem errada no routing
        erros_novos = [e for e in erros if "anti-gatilho" in e.lower()
                       or "routing_skills" in e.lower()
                       or "contagem" in e.lower()
                       or "mapper" in e.lower()
                       or "inexistente" in e.lower()]
        assert erros_novos == [], f"Erros novos inesperados: {erros_novos}"

    def test_check_consistencia_repo_real_sem_erros(self):
        """check_consistencia() completo deve passar limpo no repo atual."""
        erros, _ = mod.check_consistencia()
        assert erros == [], f"Erros inesperados: {erros}"

    def test_check_consistencia_sem_aviso_nem_erro_de_budget(self):
        """T1.2 (invertido): check_consistencia() sem aviso/erro de budget.

        Antes da T1.2 este teste assertava >=1 AVISO BUDGET (gestor-estoque-odoo
        em 15391c). Com descriptions <=600c e BUDGET_SUBAGENTE_ENFORCE=True,
        o estado limpo (sem avisos E sem erros de budget) e' o invariante.
        """
        erros, avisos = mod.check_consistencia()
        avisos_budget = [a for a in avisos if "BUDGET" in a.upper() or "budget" in a.lower()]
        erros_budget = [e for e in erros if "BUDGET" in e.upper() or "budget" in e.lower()]
        assert avisos_budget == [], (
            f"Nenhum aviso de budget esperado pos-T1.2. avisos={avisos_budget}"
        )
        assert erros_budget == [], (
            f"Nenhum erro de budget esperado pos-T1.2. erros={erros_budget}"
        )
