#!/usr/bin/env python3
"""
skills_listing_audit.py — vigia o ORCAMENTO do listing de skills do Agente Web
(F2.5 do plano PAD-CTX — docs/superpowers/plans/2026-06-09-arquitetura-contexto-boot-agente.md).

Dono: Claude Code (curadoria de skills, FASE 2 PAD-CTX 2026-06-09).
Motivo: o CLI do Agent SDK monta a meta-tool `Skill` concatenando as descriptions de
TODAS as skills do listing; acima do budget ele TRUNCA proporcionalmente —
descartando as clausulas finais de desambiguacao (anti-gatilhos), que sao exatamente o
que protege o roteamento. Antes da F2 o listing tinha ~25,6K chars (28 skills) e rodava
truncado em silencio. Este audit impede a regressao.

FORMULA REAL DO CLI (extraida do binario 2.1.170 em 2026-06-09, apos warning
"Skill listing over budget: 21 skills, 8448 chars > 8000" com o audit antigo
dando falso-OK em 7.946 — ele somava SO as descriptions):
  - entrada por skill: `- {name}: {description}` -> len(name) + 4 + len(desc)
    (se houver `whenToUse` no frontmatter, o CLI concatena "desc - whenToUse";
    nenhuma skill do projeto usa o campo — guard abaixo avisa se surgir)
  - total: soma das entradas + (N-1) newlines
  - budget: context_window(200K default) x 4 bytes/token x fraction(0.01) = 8000;
    overrides: env SLASH_COMMAND_TOOL_CHAR_BUDGET (absoluto) ou setting
    skillListingBudgetFraction — usar so como ESCAPE consciente, o padrao
    PAD-CTX e CABER no budget default.

Mede: skills VISIVEIS ao agente principal = diretorios .claude/skills/*/SKILL.md
MENOS a deny-list SKILLS_DELEGADAS_SUBAGENTE (app/agente/config/skills_whitelist.py).

Uso:
  python scripts/audits/skills_listing_audit.py            # report legivel
  python scripts/audits/skills_listing_audit.py --check    # exit 1 se total > LIMITE_TOTAL
  python scripts/audits/skills_listing_audit.py --json     # snapshot machine-readable

Limiares (PAD-CTX, secao "Skills — template de description e curadoria"):
  LIMITE_TOTAL = 8000 chars (budget efetivo do CLI, na FORMULA REAL acima)
  ALVO_POR_SKILL = 500 chars de ENTRADA (name + 4 + description; estourar gera
  AVISO, nao bloqueia — excecoes pontuais toleradas enquanto o TOTAL couber)
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / ".claude/skills"
WHITELIST_PRINCIPAL = ROOT / "app/agente/config/skills_whitelist.py"

LIMITE_TOTAL = 8000
ALVO_POR_SKILL = 500
ENTRY_OVERHEAD = 4  # "- " + ": " no formato `- {name}: {description}` do CLI


def _carregar_modulo_isolado(path):
    """Carrega skills_whitelist.py SEM importar o pacote `app` (sem boot Flask)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(Path(path).stem + "_isolado", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _extrair_description(skill_md: Path) -> str:
    """Extrai o texto da description do frontmatter YAML (sem dependencia de pyyaml).

    Suporta os 2 formatos em uso: bloco escalar (`description: >-` / `>` / `|`)
    e linha unica (`description: texto`).
    """
    txt = skill_md.read_text(encoding="utf-8")
    m = re.search(r"^---\s*\n(.*?)\n---\s*\n", txt, re.DOTALL)
    if not m:
        return ""
    fm = m.group(1)
    linhas = fm.split("\n")
    desc_partes = []
    capturando = False
    for ln in linhas:
        if capturando:
            if ln.startswith((" ", "\t")) or ln.strip() == "":
                desc_partes.append(ln.strip())
                continue
            break  # proxima chave do frontmatter
        m2 = re.match(r"^description:\s*(.*)$", ln)
        if m2:
            resto = m2.group(1).strip()
            if resto in (">-", ">", "|", "|-"):
                capturando = True
            else:
                return resto
    return " ".join(p for p in desc_partes if p).strip()


def _tem_when_to_use(skill_md: Path) -> bool:
    """Guard: o CLI concatena `whenToUse` na description — se o campo surgir num
    SKILL.md, a medicao abaixo subestima. Avisar para incluir na formula."""
    txt = skill_md.read_text(encoding="utf-8")
    m = re.search(r"^---\s*\n(.*?)\n---\s*\n", txt, re.DOTALL)
    return bool(m and re.search(r"^when[_-]?to[_-]?use\s*:", m.group(1),
                                re.MULTILINE | re.IGNORECASE))


def snapshot():
    wl = _carregar_modulo_isolado(WHITELIST_PRINCIPAL)
    excluidas = set(wl.SKILLS_DELEGADAS_SUBAGENTE)
    out = {"skills": {}, "total_chars": 0, "n_skills": 0,
           "excluidas": sorted(excluidas), "when_to_use_detectado": []}
    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        nome = skill_md.parent.name
        if nome in excluidas:
            continue
        desc = _extrair_description(skill_md)
        # Formula real do CLI: entrada = `- {name}: {description}`
        entry_len = len(nome) + ENTRY_OVERHEAD + len(desc)
        out["skills"][nome] = entry_len
        out["total_chars"] += entry_len
        out["n_skills"] += 1
        if _tem_when_to_use(skill_md):
            out["when_to_use_detectado"].append(nome)
    # (N-1) newlines entre as entradas (join do CLI)
    out["total_chars"] += max(0, out["n_skills"] - 1)
    return out


def main():
    argv = sys.argv
    snap = snapshot()

    if "--json" in argv:
        print(json.dumps(snap, indent=2, ensure_ascii=False))
        return 0

    acima_do_alvo = {n: c for n, c in snap["skills"].items() if c > ALVO_POR_SKILL}

    print("=" * 64)
    print("LISTING DE SKILLS DO AGENTE WEB — orcamento (formula real do CLI:")
    print("entrada = len(name)+4+len(description); total += N-1 newlines)")
    print("=" * 64)
    for nome, chars in sorted(snap["skills"].items(), key=lambda kv: -kv[1]):
        flag = "  <-- acima do alvo 500c" if chars > ALVO_POR_SKILL else ""
        print(f"  {nome:<40}{chars:>6}c{flag}")
    print("-" * 64)
    print(f"  TOTAL: {snap['n_skills']} skills, {snap['total_chars']} chars "
          f"(limite {LIMITE_TOTAL})")

    if "--check" in argv:
        for nome in snap.get("when_to_use_detectado", []):
            print(f"AVISO: '{nome}' usa campo whenToUse no frontmatter — o CLI "
                  f"concatena na description e este audit NAO esta contando; "
                  f"incluir na formula.", file=sys.stderr)
        for nome, chars in sorted(acima_do_alvo.items()):
            print(f"AVISO: '{nome}' com {chars}c (alvo {ALVO_POR_SKILL}c — "
                  f"template PAD-CTX)", file=sys.stderr)
        if snap["total_chars"] > LIMITE_TOTAL:
            print(f"\nFALHA: listing com {snap['total_chars']} chars > {LIMITE_TOTAL} — "
                  f"o CLI vai TRUNCAR descriptions (roteamento degrada em silencio).\n"
                  f"Encolha descriptions (template ≤{ALVO_POR_SKILL}c) ou mova a skill "
                  f"para a deny-list se for de dominio/subagente.\n"
                  f"Padrao: .claude/references/ARQUITETURA_CONTEXTO_AGENTE.md",
                  file=sys.stderr)
            return 1
        print("OK: listing dentro do orcamento do CLI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
