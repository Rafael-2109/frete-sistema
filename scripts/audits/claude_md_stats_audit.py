#!/usr/bin/env python3
"""
claude_md_stats_audit.py — mede as stats REAIS (LOC / arquivos .py / templates) de cada
modulo que tem CLAUDE.md proprio e arma o GATILHO DE DRIFT contra defasagem das stats
declaradas nos cabecalhos dos CLAUDE.md.

Dono: Claude Code (auditoria CLAUDE.md, 2026-06-06).
Motivo: as stats "~XXK LOC, NN arquivos" nos cabecalhos dos CLAUDE.md sao atualizadas a
mao e apodrecem. Auditoria de 2026-06-06 achou defasagens de ate ~4x (motos_assai 5.1K->
19.8K; agente 35.8K->51K; odoo 18.6K->42.5K; services 8.7K->12.8K). Numero hardcoded sem
gatilho sempre volta a defasar. Este script e a FONTE auto-medida + o gatilho de poda.

Espelha o padrao de `prompt_size_audit.py` (baseline JSON + --check-delta).

Uso:
  python scripts/audits/claude_md_stats_audit.py                 # report legivel (real medido)
  python scripts/audits/claude_md_stats_audit.py --json          # snapshot machine-readable
  python scripts/audits/claude_md_stats_audit.py --md            # bloco markdown
  python scripts/audits/claude_md_stats_audit.py --update-baseline   # grava o estado atual como marco
  python scripts/audits/claude_md_stats_audit.py --check-drift       # GATILHO: exit 1 se algum modulo driftou vs baseline
  python scripts/audits/claude_md_stats_audit.py --check-drift --staged   # idem, MAS so' nos modulos tocados pelo commit (uso no pre-commit)

Drift = um modulo cujo tamanho REAL afastou-se do baseline alem do limite (LOC +-15% OU
arquivos .py +-LIMITE_PY OU templates +-LIMITE_TPL). Quando dispara, significa que o
codigo cresceu/encolheu desde a ultima vez que as stats do CLAUDE.md foram conferidas —
hora de atualizar o cabecalho do CLAUDE.md afetado e re-armar o baseline.

Nota: LOC = linhas fisicas de .py (splitlines), nao SLOC. O objetivo e detectar
DEFASAGEM/CRESCIMENTO, nao precisao absoluta. Trate como ordem de grandeza.
"""
import json
import subprocess
import sys
from pathlib import Path

# raiz do projeto = 2 niveis acima de scripts/audits/
ROOT = Path(__file__).resolve().parents[2]

BASELINE_PATH = ROOT / "scripts/audits/claude_md_stats_baseline.json"

# Limites de drift (alem do baseline) que disparam o gatilho.
LIMITE_LOC_PCT = 0.15   # +-15% em linhas .py
LIMITE_PY = 5           # +-5 arquivos .py
LIMITE_TPL = 5          # +-5 templates .html

# (label, py_dir relativo a ROOT, tpl_dir relativo a ROOT ou None)
# label = caminho do CLAUDE.md correspondente, para facilitar localizar o cabecalho a corrigir.
MODULOS = [
    ("app/agente",              "app/agente",             "app/templates/agente"),
    ("app/agente/services",     "app/agente/services",    None),
    ("app/agente_lojas",        "app/agente_lojas",       "app/templates/agente_lojas"),
    ("app/carteira",            "app/carteira",           "app/templates/carteira"),
    ("app/carvia",              "app/carvia",             "app/templates/carvia"),
    ("app/chat",                "app/chat",               "app/templates/chat"),
    ("app/devolucao",           "app/devolucao",          "app/templates/devolucao"),
    ("app/financeiro",          "app/financeiro",         "app/templates/financeiro"),
    ("app/fretes",              "app/fretes",             "app/templates/fretes"),
    ("app/hora",                "app/hora",               "app/templates/hora"),
    ("app/motos_assai",         "app/motos_assai",        "app/templates/motos_assai"),
    ("app/odoo",                "app/odoo",               "app/templates/odoo"),
    ("app/odoo/estoque",        "app/odoo/estoque",       None),
    ("app/relatorios_fiscais",  "app/relatorios_fiscais", "app/templates/relatorios_fiscais"),
    ("app/seguranca",           "app/seguranca",          "app/templates/seguranca"),
    ("app/teams",               "app/teams",              "app/templates/teams"),
    ("app/whatsapp",            "app/whatsapp",           "app/templates/whatsapp"),
]


# --------------------------------------------------------------------- medicao

def _medir_py(py_dir: Path):
    """Retorna (n_arquivos, loc) de .py sob py_dir, ignorando __pycache__."""
    n = 0
    loc = 0
    if not py_dir.exists():
        return 0, 0
    for p in py_dir.rglob("*.py"):
        if "__pycache__" in p.parts:
            continue
        n += 1
        try:
            loc += len(p.read_text(encoding="utf-8", errors="replace").splitlines())
        except OSError:
            pass
    return n, loc


def _medir_tpl(tpl_dir):
    if not tpl_dir:
        return 0
    d = Path(tpl_dir)
    if not d.exists():
        return 0
    return sum(1 for p in d.rglob("*.html") if "__pycache__" not in p.parts)


def snapshot(modulos=None):
    """Mede todos os modulos. Retorna {label: {py, loc, tpl}}."""
    modulos = modulos if modulos is not None else MODULOS
    out = {}
    for label, py_rel, tpl_rel in modulos:
        n, loc = _medir_py(ROOT / py_rel)
        tpl = _medir_tpl(ROOT / tpl_rel) if tpl_rel else 0
        out[label] = {"py": n, "loc": loc, "tpl": tpl}
    return out


# --------------------------------------------------------------------- staged

def _arquivos_staged():
    """Lista de paths .py staged no commit (relativos a ROOT). [] se git indisponivel."""
    try:
        out = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout
    except (subprocess.CalledProcessError, OSError):
        return []
    return [ln for ln in out.splitlines() if ln.endswith(".py")]


def labels_tocados(arquivos_py, modulos=None):
    """Labels de MODULOS cujo py_dir contem algum arquivo .py staged.
    app/odoo/estoque/x.py -> {'app/odoo', 'app/odoo/estoque'} (ambos os niveis)."""
    modulos = modulos if modulos is not None else MODULOS
    tocados = set()
    for f in arquivos_py:
        for label, py_rel, _ in modulos:
            if f == py_rel or f.startswith(py_rel.rstrip("/") + "/"):
                tocados.add(label)
    return tocados


# --------------------------------------------------------------------- baseline

def salvar_baseline(path, snap):
    Path(path).write_text(json.dumps(snap, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def carregar_baseline(path):
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def comparar_drift(atual, baseline):
    """Retorna (ok, mensagens). ok=False se algum modulo afastou-se do baseline alem do
    limite (cresceu OU encolheu — stats defasadas em qualquer direcao)."""
    msgs = []
    for label, a in atual.items():
        b = baseline.get(label)
        if b is None:
            msgs.append(f"{label}: NOVO modulo sem baseline (py={a['py']}, loc={a['loc']})")
            continue
        # LOC: drift percentual
        if b["loc"] > 0:
            pct = abs(a["loc"] - b["loc"]) / b["loc"]
            if pct > LIMITE_LOC_PCT:
                msgs.append(f"{label}/CLAUDE.md: LOC {b['loc']}->{a['loc']} ({pct*100:.0f}% drift)")
        elif a["loc"] > 0:
            msgs.append(f"{label}/CLAUDE.md: LOC 0->{a['loc']}")
        # arquivos .py
        if abs(a["py"] - b["py"]) >= LIMITE_PY:
            msgs.append(f"{label}/CLAUDE.md: arquivos .py {b['py']}->{a['py']} (+-{abs(a['py']-b['py'])})")
        # templates
        if abs(a["tpl"] - b["tpl"]) >= LIMITE_TPL:
            msgs.append(f"{label}/CLAUDE.md: templates {b['tpl']}->{a['tpl']} (+-{abs(a['tpl']-b['tpl'])})")
    # modulos removidos do snapshot mas presentes no baseline
    for label in baseline:
        if label not in atual:
            msgs.append(f"{label}: presente no baseline mas nao medido (removido?)")
    return (len(msgs) == 0, msgs)


# --------------------------------------------------------------------- markdown

def _fmt_loc(loc):
    return f"~{loc/1000:.1f}K" if loc >= 1000 else str(loc)


def bloco_md(snap):
    linhas = [
        "| Modulo (CLAUDE.md) | Arquivos .py | LOC | Templates |",
        "|--------------------|-------------:|----:|----------:|",
    ]
    for label, d in snap.items():
        linhas.append(f"| `{label}/CLAUDE.md` | {d['py']} | {_fmt_loc(d['loc'])} | {d['tpl']} |")
    linhas.append("")
    linhas.append(
        "> Medido por `scripts/audits/claude_md_stats_audit.py`. "
        "NUNCA editar a mao — rode o script e atualize os cabecalhos dos CLAUDE.md."
    )
    return "\n".join(linhas)


# --------------------------------------------------------------------- CLI

def _print_report(snap, baseline=None):
    print("=" * 78)
    print("STATS REAIS DOS MODULOS COM CLAUDE.md PROPRIO")
    print("=" * 78)
    print(f"{'Modulo':<28}{'.py':>6}{'LOC':>10}{'tpl':>6}   vs baseline")
    print("-" * 78)
    for label, d in snap.items():
        delta = ""
        if baseline and label in baseline:
            b = baseline[label]
            dl = d["loc"] - b["loc"]
            if dl:
                delta = f"LOC {dl:+d}"
        print(f"{label:<28}{d['py']:>6}{d['loc']:>10}{d['tpl']:>6}   {delta}")
    print("-" * 78)
    print("Fonte unica destes numeros. Re-rode apos crescer um modulo; "
          "atualize o cabecalho do CLAUDE.md afetado + --update-baseline.")


def main():
    argv = sys.argv

    if "--json" in argv:
        print(json.dumps(snapshot(), indent=2, ensure_ascii=False))
        return 0

    if "--md" in argv:
        print(bloco_md(snapshot()))
        return 0

    if "--update-baseline" in argv:
        snap = snapshot()
        salvar_baseline(BASELINE_PATH, snap)
        print(f"baseline atualizado: {BASELINE_PATH.relative_to(ROOT)} ({len(snap)} modulos)")
        return 0

    if "--check-drift" in argv:
        base = carregar_baseline(BASELINE_PATH)
        if base is None:
            print(f"baseline ausente ({BASELINE_PATH.relative_to(ROOT)}); "
                  f"rode --update-baseline para armar o gatilho. Sem bloqueio.",
                  file=sys.stderr)
            return 0  # no-op: nao bloqueia sem baseline
        atual = snapshot()
        if "--staged" in argv:
            tocados = labels_tocados(_arquivos_staged())
            if not tocados:
                return 0  # commit nao toca .py de modulo com CLAUDE.md -> nada a checar
            atual = {k: v for k, v in atual.items() if k in tocados}
            base = {k: v for k, v in base.items() if k in tocados}
        ok, msgs = comparar_drift(atual, base)
        if ok:
            print(f"OK: stats dos CLAUDE.md dentro do limite vs baseline ({len(atual)} modulos).")
            return 0
        print("GATILHO DE DRIFT: stats reais afastaram-se do baseline — "
              "cabecalhos de CLAUDE.md provavelmente defasados:", file=sys.stderr)
        for m in msgs:
            print(f"  - {m}", file=sys.stderr)
        print("\nAcao: atualize o cabecalho (~XK LOC / N arquivos) do(s) CLAUDE.md acima e re-arme:", file=sys.stderr)
        print("  python scripts/audits/claude_md_stats_audit.py --update-baseline && \\", file=sys.stderr)
        print("  git add scripts/audits/claude_md_stats_baseline.json app/**/CLAUDE.md", file=sys.stderr)
        print("\nBypass emergencial: git commit --no-verify", file=sys.stderr)
        return 1

    base = carregar_baseline(BASELINE_PATH)
    _print_report(snapshot(), base)
    return 0


if __name__ == "__main__":
    sys.exit(main())
