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
"""
import json
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

        # Aviso: skill declarada em agent sem diretorio correspondente
        skills_fs = {p.parent.name for p in (ROOT / ".claude/skills").glob("*/SKILL.md")}
        for agente, skills in sorted(_skills_declaradas_em_agents().items()):
            for skill in sorted(skills - skills_fs - SKILLS_SEM_SKILL_MD):
                avisos.append(
                    f"agente '{agente}' declara skill '{skill}' sem "
                    f".claude/skills/{skill}/SKILL.md"
                )
    except Exception as e:  # noqa: BLE001 — check nao pode derrubar o commit por bug proprio
        avisos.append(f"nao-orfandade da deny-list nao verificada (erro: {e})")

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
