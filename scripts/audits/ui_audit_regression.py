#!/usr/bin/env python3
"""
UI Audit Regression Check — compara audit atual vs baseline commitado.

Falha (exit 1) se qualquer codigo de violacao AUMENTOU em relacao ao baseline.
Usado em pre-commit hook (local) ou CI (PR) para prevenir regressao.

Uso:
  python scripts/audits/ui_audit_regression.py
  python scripts/audits/ui_audit_regression.py --update-baseline  # apos cleanup intencional

Saida:
  exit 0  → OK (igual ou melhor que baseline)
  exit 1  → REGRESSAO detectada (uma ou mais categorias aumentaram)

Baseline: relatorios/ui_audit_baseline.json (commitado).
Atualizado quando alguma fase de cleanup termina e queremos travar o novo piso.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASELINE = ROOT / "relatorios" / "ui_audit_baseline.json"
TMP_AUDIT = ROOT / "relatorios" / "ui_audit_tmp.json"


def load_totals(path: Path) -> dict:
    with path.open() as f:
        data = json.load(f)
    return data.get("totals_by_violation", {})


def run_audit() -> dict:
    """Roda audit em tmp e retorna totals_by_violation."""
    audit_script = ROOT / "scripts" / "audits" / "ui_audit.py"
    result = subprocess.run(
        [sys.executable, str(audit_script), "--json-only"],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
    )
    if result.returncode != 0:
        print(f"[regression] ERRO ao rodar audit:\n{result.stderr}", file=sys.stderr)
        sys.exit(2)
    # audit gera ui_audit_<data>.json no diretorio relatorios. Pegamos o mais recente.
    reports_dir = ROOT / "relatorios"
    candidates = sorted(reports_dir.glob("ui_audit_2*.json"), reverse=True)
    if not candidates:
        print("[regression] ERRO: nenhum ui_audit_<data>.json gerado", file=sys.stderr)
        sys.exit(2)
    return load_totals(candidates[0])


def compare(baseline: dict, current: dict) -> tuple[list, list]:
    """Retorna (regressoes, melhorias) — listas de tuples (code, baseline_val, current_val, delta)."""
    all_codes = set(baseline) | set(current)
    regressoes = []
    melhorias = []
    for code in sorted(all_codes):
        b = baseline.get(code, 0)
        c = current.get(code, 0)
        if c > b:
            regressoes.append((code, b, c, c - b))
        elif c < b:
            melhorias.append((code, b, c, b - c))
    return regressoes, melhorias


def main():
    parser = argparse.ArgumentParser(description="UI Audit regression check")
    parser.add_argument("--update-baseline", action="store_true",
                        help="Atualiza baseline para o estado atual (apos cleanup intencional)")
    args = parser.parse_args()

    if not BASELINE.exists():
        print(f"[regression] ERRO: baseline nao existe em {BASELINE}", file=sys.stderr)
        print("[regression] Para criar: python scripts/audits/ui_audit.py --json-only && "
              "cp relatorios/ui_audit_<data>.json relatorios/ui_audit_baseline.json")
        sys.exit(2)

    print(f"[regression] Baseline: {BASELINE.name}")
    print(f"[regression] Rodando audit atual...")
    current = run_audit()
    baseline = load_totals(BASELINE)

    regressoes, melhorias = compare(baseline, current)

    if melhorias:
        print(f"\n[regression] Melhorias ({len(melhorias)}):")
        for code, b, c, delta in melhorias:
            print(f"  {code:35} {b:>5} -> {c:<5} (-{delta})")

    if regressoes:
        print(f"\n[regression] REGRESSOES detectadas ({len(regressoes)}):")
        for code, b, c, delta in regressoes:
            print(f"  {code:35} {b:>5} -> {c:<5} (+{delta})")

    total_b = sum(baseline.values())
    total_c = sum(current.values())
    print(f"\n[regression] Total: {total_b} -> {total_c} ({'+' if total_c >= total_b else ''}{total_c - total_b})")

    if args.update_baseline:
        # encontra o JSON mais recente e copia
        reports_dir = ROOT / "relatorios"
        latest = sorted(reports_dir.glob("ui_audit_2*.json"), reverse=True)[0]
        shutil.copy(latest, BASELINE)
        print(f"\n[regression] Baseline atualizado para o estado atual (de {latest.name})")
        sys.exit(0)

    if regressoes:
        print("\n[regression] FALHA — uma ou mais categorias aumentaram em relacao ao baseline.")
        print("[regression] Corrija ou rode com --update-baseline se a regressao for intencional.")
        sys.exit(1)

    print("\n[regression] OK — nenhuma regressao detectada.")
    sys.exit(0)


if __name__ == "__main__":
    main()
