#!/usr/bin/env python3
"""
prompt_size_audit.py — mede o tamanho REAL do system prompt estatico do Agente Web.

Dono: Claude Code (refactor prompt, FASE 1 — 2026-06-04).
Motivo: a documentacao (app/agente/CLAUDE.md) afirmava ~2.7K tokens enquanto o real
era ~17.5K (defasagem ~6.5x). Numero hardcoded apodrece a cada edicao do prompt.
Este script e a FONTE auto-medida — re-rode apos qualquer edicao dos prompts.

Mede os 3 arquivos concatenados em `_build_full_system_prompt()` (client.py) quando
USE_CUSTOM_SYSTEM_PROMPT=true:
  1. app/agente/prompts/preset_operacional.md
  2. app/agente/prompts/system_prompt.md
  3. app/agente/config/empresa_briefing.md

Uso:
  python scripts/audits/prompt_size_audit.py            # report
  python scripts/audits/prompt_size_audit.py --md       # bloco markdown p/ colar no CLAUDE.md
  python scripts/audits/prompt_size_audit.py --check N   # exit 1 se total de linhas > N (gatilho FASE 5)

Nota: tokens sao ESTIMATIVA (bytes/3.5, calibrado p/ pt-BR + XML). A Anthropic nao
publica tokenizer offline; o objetivo aqui e detectar DEFASAGEM e CRESCIMENTO, nao
precisao absoluta. Trate como ordem de grandeza.
"""
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


def medir():
    linhas_t = bytes_t = 0
    rows = []
    for nome, p in ARQUIVOS:
        if not p.exists():
            rows.append((nome, "AUSENTE", "AUSENTE", "AUSENTE"))
            continue
        txt = p.read_text(encoding="utf-8")
        linhas = len(txt.splitlines())
        nbytes = len(txt.encode("utf-8"))
        tok = int(nbytes / BYTES_POR_TOKEN)
        linhas_t += linhas
        bytes_t += nbytes
        rows.append((nome, linhas, nbytes, tok))
    tok_t = int(bytes_t / BYTES_POR_TOKEN)
    return rows, linhas_t, bytes_t, tok_t


def fmt_tok(t):
    return f"~{t/1000:.1f}K tok" if isinstance(t, int) else t


def main():
    rows, linhas_t, bytes_t, tok_t = medir()

    if "--check" in sys.argv:
        try:
            limite = int(sys.argv[sys.argv.index("--check") + 1])
        except (ValueError, IndexError):
            print("uso: --check <N_linhas>", file=sys.stderr)
            return 2
        print(f"system prompt estatico: {linhas_t} linhas (limite {limite})")
        if linhas_t > limite:
            print(f"FALHA: prompt cresceu acima do limite ({linhas_t} > {limite}). "
                  f"Pode/deve aplicar poda compensatoria (ver plano refactor-governanca).",
                  file=sys.stderr)
            return 1
        print("OK: dentro do limite.")
        return 0

    if "--md" in sys.argv:
        print("| Componente | Linhas | Bytes | Tokens (est.) |")
        print("|------------|-------:|------:|--------------:|")
        for nome, l, b, t in rows:
            print(f"| `{nome}` | {l} | {b} | {fmt_tok(t)} |")
        print(f"| **TOTAL estatico** | **{linhas_t}** | **{bytes_t}** | **{fmt_tok(tok_t)}** |")
        print(f"\n> Medido por `scripts/audits/prompt_size_audit.py` (tokens = bytes/{BYTES_POR_TOKEN}, estimativa pt-BR+XML).")
        return 0

    # report default
    print("=" * 64)
    print("SYSTEM PROMPT ESTATICO DO AGENTE WEB — tamanho real medido")
    print("=" * 64)
    print(f"{'Componente':<26}{'Linhas':>8}{'Bytes':>10}{'Tokens~':>12}")
    print("-" * 64)
    for nome, l, b, t in rows:
        print(f"{nome:<26}{str(l):>8}{str(b):>10}{fmt_tok(t):>12}")
    print("-" * 64)
    print(f"{'TOTAL':<26}{str(linhas_t):>8}{str(bytes_t):>10}{fmt_tok(tok_t):>12}")
    print(f"\nFonte unica deste numero. Re-rode apos editar qualquer prompt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
