#!/usr/bin/env python3
"""
prompt_size_audit.py — mede o tamanho REAL do system prompt estatico do Agente Web
e instala o GATILHO DE PODA (FASE 5 — governanca do plano refactor-governanca-prompt).

Dono: Claude Code (refactor prompt, FASE 1 2026-06-04 / FASE 5 2026-06-06).
Motivo: a documentacao (app/agente/CLAUDE.md) afirmava ~2.7K tokens enquanto o real
era ~17.5K (defasagem ~6.5x). Numero hardcoded apodrece a cada edicao do prompt.
Este script e a FONTE auto-medida E o gatilho que impede a acrecao reativa de voltar.

Mede os 3 arquivos concatenados em `_build_full_system_prompt()` (client.py) quando
USE_CUSTOM_SYSTEM_PROMPT=true:
  1. app/agente/prompts/preset_operacional.md
  2. app/agente/prompts/system_prompt.md
  3. app/agente/config/empresa_briefing.md

Uso:
  python scripts/audits/prompt_size_audit.py                  # report legivel
  python scripts/audits/prompt_size_audit.py --json           # snapshot machine-readable
  python scripts/audits/prompt_size_audit.py --md             # bloco markdown
  python scripts/audits/prompt_size_audit.py --check N        # exit 1 se TOTAL de linhas > N (teto absoluto)
  python scripts/audits/prompt_size_audit.py --check-delta    # GATILHO: exit 1 se prompt CRESCEU vs baseline
  python scripts/audits/prompt_size_audit.py --check-consistency  # F1.3 PAD-CTX: subagentes nas 3 projecoes + deny-list sem orfas
  python scripts/audits/prompt_size_audit.py --update-baseline    # grava o estado atual como novo marco
  python scripts/audits/prompt_size_audit.py --update-claude-md   # reescreve o bloco de tamanho no CLAUDE.md

Nota: tokens sao ESTIMATIVA (bytes/3.5, calibrado p/ pt-BR + XML). A Anthropic nao
publica tokenizer offline; o objetivo aqui e detectar DEFASAGEM e CRESCIMENTO, nao
precisao absoluta. Trate como ordem de grandeza.

T1.1 (2026-06-11): novos checks em check_consistencia():
  (a) skills citadas existem — 4 fontes:
      a.1 check_anti_gatilhos: anti-gatilhos em descriptions de SKILL.md
      a.2 check_nomes_inventario_routing: nomes listados no inventario do
          ROUTING_SKILLS.md (prosa parentetica isenta)
      a.3 check_chaves_mapper: chaves de SKILL_TO_CATEGORY (tool_skill_mapper.py;
          validas tambem via .claude/commands/*.md)
      a.4 check_skills_declaradas_agents: frontmatter skills de agents
          (ERRO se diretorio inexistente; WARNING se so falta SKILL.md)
  (b) check_contagens_routing: contagens declaradas no ROUTING_SKILLS.md
  (c) check_budget_subagentes: budget de descriptions por subagente (WARNING ate T1.2)
"""
import json
import re
import sys
from pathlib import Path

# raiz do projeto = 2 niveis acima de scripts/audits/
ROOT = Path(__file__).resolve().parents[2]

ARQUIVOS = [
    ("preset_operacional.md", ROOT / "app/agente/prompts/preset_operacional.md"),
    ("system_prompt.md",      ROOT / "app/agente/prompts/system_prompt.md"),
    ("empresa_briefing.md",   ROOT / "app/agente/config/empresa_briefing.md"),
]

BYTES_POR_TOKEN = 3.5  # estimativa pt-BR + XML

BASELINE_PATH = ROOT / "scripts/audits/prompt_size_baseline.json"
CLAUDE_MD_PATH = ROOT / "app/agente/CLAUDE.md"

# Marcadores do bloco auto-medido no CLAUDE.md (T5.2). Conteudo entre eles e' gerado.
MARK_INI = "<!-- prompt-size:start (auto: scripts/audits/prompt_size_audit.py --update-claude-md) -->"
MARK_FIM = "<!-- prompt-size:end -->"

# Arquivo(s) cujo crescimento individual e' vigiado alem do total (o que inchou: 407->862).
CHAVES_CRITICAS = ("system_prompt.md",)


# --------------------------------------------------------------------- medicao

def snapshot(arquivos=None):
    """Mede os arquivos e retorna um dict serializavel:
    {"arquivos": {nome: {linhas, bytes, tokens[, ausente]}}, "total": {linhas, bytes, tokens}}
    Arquivo ausente NAO conta no total (registrado com ausente=True).
    """
    arquivos = arquivos if arquivos is not None else ARQUIVOS
    out = {"arquivos": {}, "total": {"linhas": 0, "bytes": 0, "tokens": 0}}
    for nome, p in arquivos:
        p = Path(p)
        if not p.exists():
            out["arquivos"][nome] = {"linhas": None, "bytes": None, "tokens": None, "ausente": True}
            continue
        txt = p.read_text(encoding="utf-8")
        linhas = len(txt.splitlines())
        nbytes = len(txt.encode("utf-8"))
        tok = int(nbytes / BYTES_POR_TOKEN)
        out["arquivos"][nome] = {"linhas": linhas, "bytes": nbytes, "tokens": tok}
        out["total"]["linhas"] += linhas
        out["total"]["bytes"] += nbytes
    out["total"]["tokens"] = int(out["total"]["bytes"] / BYTES_POR_TOKEN)
    return out


# --------------------------------------------------------------------- baseline

def salvar_baseline(path, snap):
    Path(path).write_text(json.dumps(snap, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def carregar_baseline(path):
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def comparar_delta(atual, baseline, chaves_criticas=CHAVES_CRITICAS):
    """Retorna (ok, mensagens). ok=False se o total OU alguma chave critica CRESCEU
    em linhas vs o baseline. Reducao (poda) e' SEMPRE permitida (ok=True)."""
    msgs = []
    for chave in chaves_criticas:
        a = (atual.get("arquivos", {}).get(chave) or {}).get("linhas")
        b = (baseline.get("arquivos", {}).get(chave) or {}).get("linhas")
        if a is not None and b is not None and a > b:
            msgs.append(f"{chave} cresceu {b}->{a} linhas (+{a - b})")
    at = atual["total"]["linhas"]
    bt = baseline["total"]["linhas"]
    if at > bt:
        msgs.append(f"total estatico cresceu {bt}->{at} linhas (+{at - bt})")
    return (len(msgs) == 0, msgs)


# ----------------------------------------------- consistencia (F1.3 PAD-CTX)
# Subagentes existem em 3 projecoes: .claude/agents/*.md (fonte canonica — e' o
# que o SDK carrega), system_prompt <subagents> (politica de delegacao) e
# CLAUDE.md raiz tabela SUBAGENTES (mapa). Divergencia silenciosa = agente
# invisivel ao routing (caso real: gestor-estoque-odoo, bug N-6 do estudo
# 2026-06-09). Tambem vigia a NAO-ORFANDADE da deny-list de skills: skill
# excluida do listing do principal precisa de dono (subagente que a declara),
# senao fica inacessivel em TODAS as superficies (caso real: faturando-odoo).
# Padrao: .claude/references/ARQUITETURA_CONTEXTO_AGENTE.md (PAD-CTX).

AGENTS_DIR = ROOT / ".claude/agents"
CLAUDE_MD_RAIZ = ROOT / "CLAUDE.md"
WHITELIST_PRINCIPAL = ROOT / "app/agente/config/skills_whitelist.py"
WHITELIST_LOJAS = ROOT / "app/agente_lojas/config/skills_whitelist.py"

# Agentes intencionalmente FORA do <subagents> do system_prompt (motivo declarado).
EXCECOES_SYSTEM_PROMPT = {
    "desenvolvedor-integracao-odoo": "dev-only (Claude Code; CLAUDE.md o lista marcado dev-only)",
    "orientador-loja": "superficie isolada agente_lojas (/agente-lojas)",
    "auditor-sped-ecd": "fluxo dev SPED ECD (nao operacional do agente web)",
    "controlador-custo-frete": "fora do loader web por medicao T2.1 (0 invocacoes web/90d + dev/30d); disponivel via Task no CC dev",
    "gestor-devolucoes": "fora do loader web por medicao T2.1 (0 invocacoes web/90d + dev/30d); disponivel via Task no CC dev",
    "gestor-ssw": "fora do loader web por medicao T2.1 (0 invocacoes web/90d + dev/30d); disponivel via Task no CC dev",
}
# Agentes intencionalmente FORA da tabela SUBAGENTES do CLAUDE.md raiz.
EXCECOES_CLAUDE_MD = {
    "orientador-loja": "superficie isolada agente_lojas",
    "auditor-sped-ecd": "fluxo dev SPED ECD",
}
# Skills declaraveis em agents SEM SKILL.md proprio (design intencional).
SKILLS_SEM_SKILL_MD = {
    "consultando-sql",  # descoberta via filesystem (schemas/); decisao 2026 — nao criar SKILL.md
}

# Skills citaveis como anti-gatilho em descriptions de SKILL.md que NAO existem em
# .claude/skills/ porque sao skills do Claude Code global (fora do escopo do agente web).
# Adicionar aqui SOMENTE apos confirmar que o diretorio .claude/skills/<nome>/ nao existe.
# Confirmado em 2026-06-11 (T1.1): nenhum desses diretorios existe em .claude/skills/.
SKILLS_EXTERNAS_ROUTING = {
    "integracao-odoo",   # skill CC-global (dev-only); agente e' desenvolvedor-integracao-odoo
    "frontend-design",   # skill CC-global (dev-only, Jinja2/HTML)
    "skill-creator",     # skill CC-global (dev-only, criar/melhorar skills)
    "ralph-wiggum",      # skill CC-global (dev-only, loop autonomo)
    "prd-generator",     # skill CC-global (dev-only, spec antes de impl)
    "resolvendo-problemas",  # skill CC-global (dev-only, investigacao G/XG)
}

# Flag de controle do check (c) — budget por subagente.
# True = ERRO (exit 1) se algum subagente ultrapassar o limite. Flipada na T1.2
# (2026-06-11) apos a correcao de gestor-estoque-odoo (15391c -> ~6.3K chars):
# descriptions de SKILL.md ficaram <=600c e a matriz USAR/NAO-USAR completa
# foi movida para o corpo de cada SKILL.md.
BUDGET_SUBAGENTE_ENFORCE = True

# Limite de budget (chars) por subagente — igual ao budget do listing do CLI Agent SDK.
BUDGET_SUBAGENTE_LIMITE = 8000


# Regex para extrair referencias de anti-gatilho das descriptions de SKILL.md.
# Captura o nome apos "->", pulando fillers opcionais (usar, use, Subagente, etc.).
# Requer pelo menos um hifen no nome (todos os nomes de skill/agente tem hifen).
_RE_ANTI_GATILHO = re.compile(
    r"->\s*(?:\*\*)?(?:usar\s+|use\s+|Subagente\s+|subagente\s+|o\s+|a\s+)?([a-z][a-z0-9-]+[a-z0-9])(?:\*\*)?",
    re.IGNORECASE,
)


def _subsecoes_inventario_routing(txt):
    """Retorna [(grupo, conta_declarada, segmento)] das subsecoes '### Grupo (N)'
    do inventario do ROUTING_SKILLS.md (entre o heading do inventario e o
    changelog HTML; cada segmento termina no proximo '###' ou no footer
    '> Skills dev')."""
    partes = txt.split("## Skills — Inventario Completo", 1)
    if len(partes) < 2:
        return []
    corpo = partes[1].split("<!-- CHANGELOG", 1)[0]
    out = []
    for m in re.finditer(r"^### (.+?)\((\d+)\)", corpo, re.MULTILINE):
        grupo = m.group(1).strip()
        conta = int(m.group(2))
        inicio = m.end()
        fim_match = re.search(r"^### |^> Skills dev", corpo[inicio:], re.MULTILINE)
        fim = inicio + fim_match.start() if fim_match else len(corpo)
        out.append((grupo, conta, corpo[inicio:fim]))
    return out


def _nomes_listados_inventario(segmento):
    """Extrai [(nome, pos_fim)] dos backtick-names com hifen listados COMO SKILL
    num segmento de subsecao do inventario — ou seja, com profundidade de
    parenteses 0. Nomes DENTRO de parenteses sao prosa/anotacao (ex.:
    '(substitui `memoria-usuario` — deprecated)') e ficam de fora."""
    out = []
    for m in re.finditer(r"`([a-z][a-z0-9-]+[a-z0-9])`", segmento):
        nome = m.group(1)
        if "-" not in nome:
            continue
        antes = segmento[:m.start()]
        depth = antes.count("(") - antes.count(")")
        if depth > 0:
            continue  # prosa parentetica — nao e listagem de skill
        out.append((nome, m.end()))
    return out


def check_anti_gatilhos(skills_dir=None, agents_stems=None, skills_externas=None):
    """Check (a.1) — T1.1: verifica que toda referencia anti-gatilho ('->') nas
    descriptions de SKILL.md aponta para skill/agente que existe.

    Excecoes validas:
    - Nome seguido de '(planejada' na mesma linha (convencao T0.2).
    - Nome presente em skills_externas (skills CC-global fora de .claude/skills/).

    Retorna (erros, avisos).
    """
    if skills_dir is None:
        skills_dir = ROOT / ".claude/skills"
    if agents_stems is None:
        agents_stems = {p.stem for p in AGENTS_DIR.glob("*.md")}
    if skills_externas is None:
        skills_externas = SKILLS_EXTERNAS_ROUTING

    skills_dir = Path(skills_dir)
    # Skills validas: SKILL.md existente OU apenas diretorio (ex: consultando-sql)
    skills_validas = {p.parent.name for p in skills_dir.glob("*/SKILL.md")}
    # Adicionar diretorios sem SKILL.md que existam
    if skills_dir.exists():
        for d in skills_dir.iterdir():
            if d.is_dir():
                skills_validas.add(d.name)

    erros = []
    avisos = []

    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        skill_name = skill_md.parent.name
        try:
            txt = skill_md.read_text(encoding="utf-8")
            m = re.search(r"^---\s*\n(.*?)\n---\s*\n", txt, re.DOTALL)
            if not m:
                continue
            fm = m.group(1)

            for match in _RE_ANTI_GATILHO.finditer(fm):
                nome = match.group(1).strip()
                # Filtro: precisa ter pelo menos um hifen (nomes de skill/agente)
                if "-" not in nome or len(nome) <= 4:
                    continue

                # Ja' esta no filesystem ou nos agents?
                if nome in skills_validas or nome in agents_stems:
                    continue

                # E' skill CC-global declarada na lista de excecoes?
                if nome in skills_externas:
                    continue

                # E' seguida de '(planejada' no mesmo contexto?
                inicio = match.end()
                contexto_proximo = fm[inicio:inicio + 40]
                if re.search(r"\(planejada", contexto_proximo, re.IGNORECASE):
                    continue

                erros.append(
                    f"SKILL.md '{skill_name}': anti-gatilho morto -> '{nome}' "
                    f"(nao existe em .claude/skills/, .claude/agents/ nem "
                    f"SKILLS_EXTERNAS_ROUTING; se for skill planejada, adicione "
                    f"'(planejada' logo apos o nome)"
                )
        except Exception as e:  # noqa: BLE001
            avisos.append(f"check_anti_gatilhos: erro ao ler '{skill_name}': {e}")

    return erros, avisos


def check_contagens_routing(routing_path=None, skills_validas=None):
    """Check (b) — T1.1: verifica que as contagens declaradas no ROUTING_SKILLS.md
    correspondem ao numero real de skills no filesystem.

    Verifica:
    - Headline '## Skills — Inventario Completo (N invocaveis)' == total real
    - Cada subsecao '### Grupo (N)' == numero de backtick-names validos listados

    'Valido' = nome existe em skills_validas (inclui SKILLS_SEM_SKILL_MD).

    Retorna (erros, avisos).
    """
    if routing_path is None:
        routing_path = ROOT / ".claude/references/ROUTING_SKILLS.md"
    if skills_validas is None:
        skills_validas = {p.parent.name for p in (ROOT / ".claude/skills").glob("*/SKILL.md")}
        skills_validas |= SKILLS_SEM_SKILL_MD

    routing_path = Path(routing_path)
    if not routing_path.exists():
        return [], [f"ROUTING_SKILLS.md ausente em {routing_path} — contagens nao verificadas"]

    erros = []
    avisos = []
    txt = routing_path.read_text(encoding="utf-8")

    # 1. Verificar total na headline
    m_total = re.search(
        r"## Skills — Inventario Completo \((\d+) invocaveis", txt
    )
    if m_total:
        total_declarado = int(m_total.group(1))
        total_real = len(skills_validas)
        if total_declarado != total_real:
            erros.append(
                f"ROUTING_SKILLS.md headline declara {total_declarado} skills invocaveis "
                f"mas o filesystem tem {total_real} "
                f"(ajuste a contagem ou adicione/remova a skill correspondente)"
            )
    else:
        # Lint nao pode se auto-desarmar em silencio: heading renomeado/reformatado
        # (ex.: em-dash -> hifen) faria o check passar sem verificar nada.
        avisos.append(
            f"ROUTING_SKILLS.md existe mas a headline "
            f"'## Skills — Inventario Completo (N invocaveis' nao foi encontrada — "
            f"contagem total NAO verificada (heading renomeado? atualize o regex "
            f"em check_contagens_routing)"
        )

    # 2. Verificar subsecoes '### Grupo (N)' — mesma extracao depth-0 do check (a.2),
    # garantindo coerencia: nome listado ou conta (se valido) ou e' ERRO no (a.2).
    subsecoes = _subsecoes_inventario_routing(txt)
    if not subsecoes:
        avisos.append(
            f"ROUTING_SKILLS.md existe mas nenhuma subsecao '### Grupo (N)' foi "
            f"encontrada no inventario — contagens por grupo NAO verificadas "
            f"(heading do inventario renomeado? atualize _subsecoes_inventario_routing)"
        )
    for grupo, conta_declarada, segmento in subsecoes:
        nomes_listados = [n for n, _ in _nomes_listados_inventario(segmento)]
        nomes_validos = [n for n in nomes_listados if n in skills_validas]
        conta_real = len(nomes_validos)

        if conta_declarada != conta_real:
            erros.append(
                f"ROUTING_SKILLS.md secao '{grupo}' declara {conta_declarada} skills "
                f"mas {conta_real} existem no filesystem "
                f"(skills listadas: {nomes_validos})"
            )

    return erros, avisos


def check_nomes_inventario_routing(routing_path=None, skills_dir=None,
                                   agents_stems=None, skills_externas=None):
    """Check (a.2) — T1.1 fix: todo nome listado COMO SKILL nas subsecoes do
    inventario do ROUTING_SKILLS.md deve existir (diretorio em .claude/skills/,
    agent, SKILLS_EXTERNAS_ROUTING, ou sufixo '(planejada').

    Nomes em prosa parentetica (anotacoes/deprecated, ex.: '(substitui
    `memoria-usuario` — deprecated)') NAO sao listagem — isentos.

    Retorna (erros, avisos).
    """
    if routing_path is None:
        routing_path = ROOT / ".claude/references/ROUTING_SKILLS.md"
    if skills_dir is None:
        skills_dir = ROOT / ".claude/skills"
    if agents_stems is None:
        agents_stems = {p.stem for p in AGENTS_DIR.glob("*.md")}
    if skills_externas is None:
        skills_externas = SKILLS_EXTERNAS_ROUTING

    routing_path = Path(routing_path)
    skills_dir = Path(skills_dir)
    if not routing_path.exists():
        return [], [f"ROUTING_SKILLS.md ausente em {routing_path} — nomes nao verificados"]

    # Valido = qualquer diretorio em .claude/skills/ (com ou sem SKILL.md)
    skills_validas = set()
    if skills_dir.exists():
        skills_validas = {d.name for d in skills_dir.iterdir() if d.is_dir()}

    erros = []
    avisos = []
    txt = routing_path.read_text(encoding="utf-8")

    subsecoes = _subsecoes_inventario_routing(txt)
    if not subsecoes:
        # Lint nao pode se auto-desarmar em silencio (heading renomeado).
        avisos.append(
            f"ROUTING_SKILLS.md existe mas nenhuma subsecao '### Grupo (N)' foi "
            f"encontrada no inventario — nomes listados NAO verificados "
            f"(heading do inventario renomeado? atualize _subsecoes_inventario_routing)"
        )
    for grupo, _conta, segmento in subsecoes:
        for nome, pos_fim in _nomes_listados_inventario(segmento):
            if nome in skills_validas or nome in agents_stems or nome in skills_externas:
                continue
            if re.match(r"\s*\(planejada", segmento[pos_fim:pos_fim + 40], re.IGNORECASE):
                continue
            erros.append(
                f"ROUTING_SKILLS.md secao '{grupo}': nome morto listado como skill "
                f"-> '{nome}' (nao existe em .claude/skills/, .claude/agents/ nem "
                f"SKILLS_EXTERNAS_ROUTING; se for planejada, adicione '(planejada' "
                f"logo apos o nome; se for anotacao historica, mova para dentro de "
                f"parenteses)"
            )

    return erros, avisos


def check_chaves_mapper(mapper_path=None, skills_dir=None, commands_dir=None,
                        agents_stems=None, skills_externas=None):
    """Check (a.3) — T1.1 fix: toda chave de SKILL_TO_CATEGORY no
    tool_skill_mapper.py deve existir como diretorio em .claude/skills/, stem de
    .claude/commands/*.md (slash commands como 'analise-carteira'), stem de
    .claude/agents/*.md, ou SKILLS_EXTERNAS_ROUTING. Chave morta = ERRO.

    Retorna (erros, avisos).
    """
    if mapper_path is None:
        mapper_path = ROOT / "app/agente/services/tool_skill_mapper.py"
    if skills_dir is None:
        skills_dir = ROOT / ".claude/skills"
    if commands_dir is None:
        commands_dir = ROOT / ".claude/commands"
    if agents_stems is None:
        agents_stems = {p.stem for p in AGENTS_DIR.glob("*.md")}
    if skills_externas is None:
        skills_externas = SKILLS_EXTERNAS_ROUTING

    mapper_path = Path(mapper_path)
    skills_dir = Path(skills_dir)
    commands_dir = Path(commands_dir)
    if not mapper_path.exists():
        return [], [f"tool_skill_mapper.py ausente em {mapper_path} — chaves nao verificadas"]

    mod_mapper = _carregar_modulo_isolado(mapper_path)
    chaves = set(getattr(mod_mapper, "SKILL_TO_CATEGORY", {}))

    skills_dirs = {d.name for d in skills_dir.iterdir() if d.is_dir()} if skills_dir.exists() else set()
    commands = {p.stem for p in commands_dir.glob("*.md")} if commands_dir.exists() else set()

    erros = []
    for chave in sorted(chaves):
        if (chave in skills_dirs or chave in commands
                or chave in agents_stems or chave in skills_externas):
            continue
        erros.append(
            f"tool_skill_mapper.py SKILL_TO_CATEGORY: chave morta '{chave}' "
            f"(nao existe em .claude/skills/, .claude/commands/, .claude/agents/ "
            f"nem SKILLS_EXTERNAS_ROUTING — remova a chave ou crie a skill)"
        )

    return erros, []


def check_skills_declaradas_agents(agents_dir=None, skills_dir=None,
                                   skills_sem_skill_md=None):
    """Check (a.4) — T1.1 fix: skill declarada no frontmatter `skills:` de
    .claude/agents/*.md. ERRO se o DIRETORIO .claude/skills/<skill>/ nao existe
    (skill fantasma — o SDK nao tera o que carregar). WARNING se o diretorio
    existe mas falta SKILL.md (fora de SKILLS_SEM_SKILL_MD, que e' design
    intencional e nao gera nada).

    Retorna (erros, avisos).
    """
    if agents_dir is None:
        agents_dir = AGENTS_DIR
    if skills_dir is None:
        skills_dir = ROOT / ".claude/skills"
    if skills_sem_skill_md is None:
        skills_sem_skill_md = SKILLS_SEM_SKILL_MD

    agents_dir = Path(agents_dir)
    skills_dir = Path(skills_dir)

    skills_md_fs = {p.parent.name for p in skills_dir.glob("*/SKILL.md")}
    skills_dirs_fs = {d.name for d in skills_dir.iterdir() if d.is_dir()} if skills_dir.exists() else set()

    erros = []
    avisos = []
    for agent_md in sorted(agents_dir.glob("*.md")):
        agent_nome = agent_md.stem
        txt = agent_md.read_text(encoding="utf-8")
        m = re.search(r"^skills:\s*\n((?:\s+-\s+\S+\s*\n)+)", txt, re.MULTILINE)
        if not m:
            continue
        skills = {
            ln.strip().lstrip("-").strip()
            for ln in m.group(1).strip().splitlines()
        }
        for skill in sorted(skills - skills_md_fs - set(skills_sem_skill_md)):
            if skill not in skills_dirs_fs:
                erros.append(
                    f"agente '{agent_nome}' declara skill '{skill}' INEXISTENTE "
                    f"(.claude/skills/{skill}/ nao existe — remova do frontmatter "
                    f"ou crie a skill)"
                )
            else:
                avisos.append(
                    f"agente '{agent_nome}' declara skill '{skill}' sem "
                    f".claude/skills/{skill}/SKILL.md"
                )

    return erros, avisos


def check_budget_subagentes(agents_dir=None, skills_dir=None, limite=None, enforce=None):
    """Check (c) — T1.1: verifica que a soma das descriptions das skills declaradas
    em cada .claude/agents/*.md nao ultrapassa o limite de 8000 chars (budget CLI).

    Formula identica a skills_listing_audit.py: entry = len(nome) + 4 + len(desc);
    total = soma(entries) + (N-1) newlines.

    Com enforce=False (padrao ate T1.2): ultrapassar o limite gera AVISO (nao ERRO).
    Com enforce=True: gera ERRO (exit 1).

    Retorna (erros, avisos).
    """
    if agents_dir is None:
        agents_dir = AGENTS_DIR
    if skills_dir is None:
        skills_dir = ROOT / ".claude/skills"
    if limite is None:
        limite = BUDGET_SUBAGENTE_LIMITE
    if enforce is None:
        enforce = BUDGET_SUBAGENTE_ENFORCE

    agents_dir = Path(agents_dir)
    skills_dir = Path(skills_dir)

    # Import isolado de skills_listing_audit para reutilizar _extrair_description
    import importlib.util as _ilu
    _sla_path = Path(__file__).resolve().parent / "skills_listing_audit.py"
    _spec = _ilu.spec_from_file_location("_sla_budget", _sla_path)
    _sla = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_sla)

    erros = []
    avisos = []

    for agent_md in sorted(agents_dir.glob("*.md")):
        agent_nome = agent_md.stem
        txt = agent_md.read_text(encoding="utf-8")
        m = re.search(r"^skills:\s*\n((?:\s+-\s+\S+\s*\n)+)", txt, re.MULTILINE)
        if not m:
            continue  # agente sem skills declaradas — nao conta

        skills = [
            ln.strip().lstrip("-").strip()
            for ln in m.group(1).strip().splitlines()
        ]
        if not skills:
            continue

        total = 0
        n_com_desc = 0
        for skill_nome in skills:
            skill_md = skills_dir / skill_nome / "SKILL.md"
            if not skill_md.exists():
                continue  # skills sem SKILL.md (consultando-sql, etc.) nao contam
            desc = _sla._extrair_description(skill_md)
            total += len(skill_nome) + 4 + len(desc)
            n_com_desc += 1

        if n_com_desc > 1:
            total += n_com_desc - 1  # (N-1) newlines

        if total > limite:
            msg = (
                f"AVISO BUDGET: agente '{agent_nome}' tem {total}c de descriptions "
                f"declaradas (limite {limite}c) — o CLI pode truncar skills ao carregar "
                f"este subagente. Encurte descriptions ou remova skills do frontmatter."
            )
            if enforce:
                erros.append(msg)
            else:
                avisos.append(msg)

    return erros, avisos


def _carregar_modulo_isolado(path):
    """Carrega um .py SEM importar o pacote `app` (evita boot do Flask).
    So' serve para modulos auto-contidos como as skills_whitelist."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(Path(path).stem + "_isolado", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _agents_no_filesystem():
    return {p.stem: p for p in sorted(AGENTS_DIR.glob("*.md"))}


def _skills_declaradas_em_agents():
    """nome_agente -> set(skills) do frontmatter `skills:` de .claude/agents/*.md."""
    import re
    out = {}
    for nome, p in _agents_no_filesystem().items():
        txt = p.read_text(encoding="utf-8")
        skills = set()
        m = re.search(r"^skills:\s*\n((?:\s+-\s+\S+\s*\n)+)", txt, re.MULTILINE)
        if m:
            skills = {
                ln.strip().lstrip("-").strip()
                for ln in m.group(1).strip().splitlines()
            }
        out[nome] = skills
    return out


def _agents_no_system_prompt():
    import re
    txt = (ROOT / "app/agente/prompts/system_prompt.md").read_text(encoding="utf-8")
    return set(re.findall(r'<agent name="([^"]+)"', txt))


def _agents_no_claude_md():
    import re
    txt = CLAUDE_MD_RAIZ.read_text(encoding="utf-8")
    partes = txt.split("## SUBAGENTES", 1)
    if len(partes) < 2:
        return set()
    corpo = partes[1].split("\n## ", 1)[0]
    return set(re.findall(r"^\| `([a-z0-9-]+)` \|", corpo, re.MULTILINE))


def check_consistencia():
    """Retorna (erros, avisos). Erros = divergencias que quebram routing/acesso."""
    erros, avisos = [], []

    fs = set(_agents_no_filesystem())
    sp = _agents_no_system_prompt()
    cm = _agents_no_claude_md()

    # 1. Projecao cita agente inexistente no filesystem -> ERRO
    for nome in sorted(sp - fs):
        erros.append(
            f"system_prompt <subagents> cita '{nome}' sem .claude/agents/{nome}.md"
        )
    for nome in sorted(cm - fs):
        erros.append(
            f"CLAUDE.md SUBAGENTES cita '{nome}' sem .claude/agents/{nome}.md"
        )

    # 2. Agente do filesystem ausente das projecoes (sem excecao declarada) -> ERRO
    for nome in sorted(fs - sp):
        if nome not in EXCECOES_SYSTEM_PROMPT:
            erros.append(
                f"agente '{nome}' existe em .claude/agents/ mas FALTA no <subagents> "
                f"do system_prompt (adicione, ou declare em EXCECOES_SYSTEM_PROMPT com motivo)"
            )
    for nome in sorted(fs - cm):
        if nome not in EXCECOES_CLAUDE_MD:
            erros.append(
                f"agente '{nome}' existe em .claude/agents/ mas FALTA na tabela "
                f"SUBAGENTES do CLAUDE.md raiz (adicione, ou declare em EXCECOES_CLAUDE_MD)"
            )

    # 3. Nao-orfandade da deny-list: skill excluida do principal precisa de dono.
    try:
        wl = _carregar_modulo_isolado(WHITELIST_PRINCIPAL)
        declaradas = set()
        for skills in _skills_declaradas_em_agents().values():
            declaradas |= skills
        hora = set(getattr(wl, "SKILLS_DOMINIO_HORA", set()))
        dev_reserved = set(getattr(wl, "SKILLS_DEV_RESERVED", set()))
        lojas_permitidas = set()
        if WHITELIST_LOJAS.exists():
            lojas = _carregar_modulo_isolado(WHITELIST_LOJAS)
            lojas_permitidas = set(getattr(lojas, "SKILLS_PERMITIDAS", set()))

        for skill in sorted(wl.SKILLS_DELEGADAS_SUBAGENTE):
            if skill in dev_reserved:
                continue  # reservada a superficies dev/admin por design (PAD-CTX F2)
            if skill in hora:
                if skill not in lojas_permitidas:
                    erros.append(
                        f"skill '{skill}' (grupo HORA da deny-list) nao esta na "
                        f"allow-list do agente_lojas — orfa nas duas superficies"
                    )
                continue
            if skill not in declaradas:
                erros.append(
                    f"skill '{skill}' esta na deny-list (fora do listing do principal) "
                    f"mas NAO e' declarada em nenhum .claude/agents/*.md — orfa, sem dono"
                )

    except Exception as e:  # noqa: BLE001 — check nao pode derrubar o commit por bug proprio
        avisos.append(f"nao-orfandade da deny-list nao verificada (erro: {e})")

    # T1.1 check (a.1): referencias mortas em descriptions de SKILL.md
    try:
        agents_stems = {p.stem for p in AGENTS_DIR.glob("*.md")}
        e_anti, a_anti = check_anti_gatilhos(
            skills_dir=ROOT / ".claude/skills",
            agents_stems=agents_stems,
            skills_externas=SKILLS_EXTERNAS_ROUTING,
        )
        erros.extend(e_anti)
        avisos.extend(a_anti)
    except Exception as e:  # noqa: BLE001
        avisos.append(f"check_anti_gatilhos nao executado (erro: {e})")

    # T1.1 check (a.2): nomes mortos listados no inventario do ROUTING_SKILLS.md
    try:
        e_inv, a_inv = check_nomes_inventario_routing()
        erros.extend(e_inv)
        avisos.extend(a_inv)
    except Exception as e:  # noqa: BLE001
        avisos.append(f"check_nomes_inventario_routing nao executado (erro: {e})")

    # T1.1 check (a.3): chaves mortas em SKILL_TO_CATEGORY (tool_skill_mapper.py)
    try:
        e_map, a_map = check_chaves_mapper()
        erros.extend(e_map)
        avisos.extend(a_map)
    except Exception as e:  # noqa: BLE001
        avisos.append(f"check_chaves_mapper nao executado (erro: {e})")

    # T1.1 check (a.4): skills declaradas em agents — ERRO se diretorio inexistente,
    # WARNING se diretorio existe mas falta SKILL.md (substitui o aviso legado).
    try:
        e_decl, a_decl = check_skills_declaradas_agents()
        erros.extend(e_decl)
        avisos.extend(a_decl)
    except Exception as e:  # noqa: BLE001
        avisos.append(f"check_skills_declaradas_agents nao executado (erro: {e})")

    # T1.1 check (b): contagens declaradas no ROUTING_SKILLS.md
    try:
        skills_validas = {p.parent.name for p in (ROOT / ".claude/skills").glob("*/SKILL.md")}
        skills_validas |= SKILLS_SEM_SKILL_MD
        e_routing, a_routing = check_contagens_routing(
            routing_path=ROOT / ".claude/references/ROUTING_SKILLS.md",
            skills_validas=skills_validas,
        )
        erros.extend(e_routing)
        avisos.extend(a_routing)
    except Exception as e:  # noqa: BLE001
        avisos.append(f"check_contagens_routing nao executado (erro: {e})")

    # T1.1 check (c): budget por subagente (WARNING ate T1.2 quando BUDGET_SUBAGENTE_ENFORCE=True)
    try:
        e_budget, a_budget = check_budget_subagentes()
        erros.extend(e_budget)
        avisos.extend(a_budget)
    except Exception as e:  # noqa: BLE001
        avisos.append(f"check_budget_subagentes nao executado (erro: {e})")

    return erros, avisos


# --------------------------------------------------------------------- markdown

def fmt_tok(t):
    return f"~{t / 1000:.1f}K tok" if isinstance(t, (int, float)) else t


def bloco_md(snap):
    linhas = [
        "| Componente | Linhas | Bytes | Tokens (est.) |",
        "|------------|-------:|------:|--------------:|",
    ]
    for nome, d in snap["arquivos"].items():
        if d.get("ausente"):
            linhas.append(f"| `{nome}` | AUSENTE | — | — |")
        else:
            linhas.append(f"| `{nome}` | {d['linhas']} | {d['bytes']} | {fmt_tok(d['tokens'])} |")
    t = snap["total"]
    linhas.append(f"| **TOTAL estatico** | **{t['linhas']}** | **{t['bytes']}** | **{fmt_tok(t['tokens'])}** |")
    linhas.append("")
    linhas.append(
        f"> Medido por `scripts/audits/prompt_size_audit.py` "
        f"(tokens = bytes/{BYTES_POR_TOKEN}, estimativa pt-BR+XML). "
        f"NUNCA editar a mao — rode `--update-claude-md`."
    )
    return "\n".join(linhas)


def atualizar_bloco_marcado(texto, bloco, ini, fim):
    """Substitui o conteudo entre `ini` e `fim` por `bloco`, preservando o resto.
    Idempotente. Levanta ValueError se algum marcador estiver ausente."""
    if ini not in texto or fim not in texto:
        raise ValueError(f"marcadores ausentes no texto ({ini!r} / {fim!r})")
    pre = texto.split(ini)[0]
    pos = texto.split(fim, 1)[1]
    return f"{pre}{ini}\n{bloco}\n{fim}{pos}"


# --------------------------------------------------------------------- CLI

def _print_report(snap):
    print("=" * 64)
    print("SYSTEM PROMPT ESTATICO DO AGENTE WEB — tamanho real medido")
    print("=" * 64)
    print(f"{'Componente':<26}{'Linhas':>8}{'Bytes':>10}{'Tokens~':>12}")
    print("-" * 64)
    for nome, d in snap["arquivos"].items():
        if d.get("ausente"):
            print(f"{nome:<26}{'AUSENTE':>8}{'AUSENTE':>10}{'AUSENTE':>12}")
        else:
            print(f"{nome:<26}{d['linhas']:>8}{d['bytes']:>10}{fmt_tok(d['tokens']):>12}")
    t = snap["total"]
    print("-" * 64)
    print(f"{'TOTAL':<26}{t['linhas']:>8}{t['bytes']:>10}{fmt_tok(t['tokens']):>12}")
    print("\nFonte unica deste numero. Re-rode apos editar qualquer prompt.")


def main():
    argv = sys.argv

    if "--json" in argv:
        print(json.dumps(snapshot(), indent=2, ensure_ascii=False))
        return 0

    if "--update-baseline" in argv:
        snap = snapshot()
        salvar_baseline(BASELINE_PATH, snap)
        sp = snap["arquivos"]["system_prompt.md"]["linhas"]
        print(f"baseline atualizado: {BASELINE_PATH.relative_to(ROOT)} "
              f"(system_prompt={sp}L, total={snap['total']['linhas']}L)")
        return 0

    if "--update-claude-md" in argv:
        snap = snapshot()
        bloco = bloco_md(snap)
        texto = CLAUDE_MD_PATH.read_text(encoding="utf-8")
        try:
            novo = atualizar_bloco_marcado(texto, bloco, MARK_INI, MARK_FIM)
        except ValueError:
            print(f"ERRO: marcadores ausentes em {CLAUDE_MD_PATH.relative_to(ROOT)}.\n"
                  f"  Adicione onde o bloco deve viver:\n  {MARK_INI}\n  {MARK_FIM}",
                  file=sys.stderr)
            return 2
        if novo != texto:
            CLAUDE_MD_PATH.write_text(novo, encoding="utf-8")
            print(f"CLAUDE.md atualizado (bloco de tamanho): total={snap['total']['linhas']}L")
        else:
            print("CLAUDE.md ja' estava atualizado (sem mudanca).")
        return 0

    if "--check-delta" in argv:
        base = carregar_baseline(BASELINE_PATH)
        if base is None:
            print(f"baseline ausente ({BASELINE_PATH.relative_to(ROOT)}); "
                  f"rode --update-baseline para armar o gatilho. Sem bloqueio.",
                  file=sys.stderr)
            return 0  # no-op: nao bloqueia worktree sem baseline
        atual = snapshot()
        ok, msgs = comparar_delta(atual, base)
        sp = atual["arquivos"]["system_prompt.md"]["linhas"]
        if ok:
            print(f"OK: prompt nao cresceu vs baseline "
                  f"(system_prompt={sp}L, total={atual['total']['linhas']}L).")
            return 0
        print("GATILHO DE PODA (FASE 5): o prompt do Agente Web CRESCEU vs baseline:", file=sys.stderr)
        for m in msgs:
            print(f"  - {m}", file=sys.stderr)
        print("\nAntes de crescer, aplique a regua R-EXEC-5:", file=sys.stderr)
        print("  (a) e' PRINCIPIO (Camada 0=prompt) ou PROCEDIMENTO (Camada 1=skill/ref)?", file=sys.stderr)
        print("      procedimento hiper-especifico sai do prompt (progressive disclosure).", file=sys.stderr)
        print("  (b) remover esta linha causa erro mensuravel? se nao, corta.", file=sys.stderr)
        print("\nSe o crescimento e' consciente (com poda de altitude compensatoria), registre o marco:", file=sys.stderr)
        print("  python scripts/audits/prompt_size_audit.py --update-baseline && \\", file=sys.stderr)
        print("  python scripts/audits/prompt_size_audit.py --update-claude-md && \\", file=sys.stderr)
        print("  git add scripts/audits/prompt_size_baseline.json app/agente/CLAUDE.md", file=sys.stderr)
        print("\nBypass emergencial: git commit --no-verify", file=sys.stderr)
        return 1

    if "--check-consistency" in argv:
        erros, avisos = check_consistencia()
        for a in avisos:
            print(f"AVISO: {a}", file=sys.stderr)
        if erros:
            print("CONSISTENCIA DE SUBAGENTES/SKILLS (PAD-CTX) — violacoes:", file=sys.stderr)
            for e in erros:
                print(f"  - {e}", file=sys.stderr)
            print("\nFonte canonica = .claude/agents/*.md; system_prompt e CLAUDE.md sao "
                  "projecoes.\nPadrao: .claude/references/ARQUITETURA_CONTEXTO_AGENTE.md",
                  file=sys.stderr)
            return 1
        print(f"OK: subagentes consistentes nas 3 projecoes ({len(_agents_no_system_prompt())} "
              f"no system_prompt) e deny-list sem skills orfas.")
        return 0

    if "--check" in argv:
        try:
            limite = int(argv[argv.index("--check") + 1])
        except (ValueError, IndexError):
            print("uso: --check <N_linhas>", file=sys.stderr)
            return 2
        total = snapshot()["total"]["linhas"]
        print(f"system prompt estatico: {total} linhas (limite {limite})")
        if total > limite:
            print(f"FALHA: prompt cresceu acima do limite ({total} > {limite}). "
                  f"Pode/deve aplicar poda compensatoria (ver plano refactor-governanca).",
                  file=sys.stderr)
            return 1
        print("OK: dentro do limite.")
        return 0

    if "--md" in argv:
        print(bloco_md(snapshot()))
        return 0

    _print_report(snapshot())
    return 0


if __name__ == "__main__":
    sys.exit(main())
