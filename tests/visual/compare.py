#!/usr/bin/env python3
"""
Visual Snapshot Compare — diff baseline vs current usando Pillow.

Compara snapshots/baseline/<X>.png contra snapshots/current/<X>.png.
Falha (exit 1) se qualquer pagina exceder o threshold de diff (% de pixels).
Gera report HTML em snapshots/reports/<timestamp>/ para inspecao visual.

Pre-requisito:
  - Rodar capture.py --target baseline (uma vez, define a verdade)
  - Rodar capture.py --target current (antes de cada validacao)

Uso:
  python tests/visual/compare.py
  python tests/visual/compare.py --threshold 0.5    # mais rigoroso
  python tests/visual/compare.py --pages hora_pedidos_lista,hora_estoque_lista
  python tests/visual/compare.py --update-baseline  # promove current para baseline

Saida:
  exit 0  → todas paginas OK (diff < threshold)
  exit 1  → uma ou mais excederam threshold
  exit 2  → erro de execucao (baseline nao existe, etc)
"""

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

import yaml
from PIL import Image, ImageChops

ROOT = Path(__file__).resolve().parents[2]
VISUAL_DIR = ROOT / "tests" / "visual"
SNAPSHOTS_DIR = VISUAL_DIR / "snapshots"
PAGES_YML = VISUAL_DIR / "pages.yml"


def diff_pct(img_a: Image.Image, img_b: Image.Image) -> tuple[float, Image.Image]:
    """
    Retorna (pct_pixels_diferentes, diff_image).
    Imagens sao redimensionadas para o menor tamanho comum se diferem.
    """
    if img_a.size != img_b.size:
        # Resize para o min comum (full-page screenshots podem variar em altura)
        w = min(img_a.size[0], img_b.size[0])
        h = min(img_a.size[1], img_b.size[1])
        img_a = img_a.resize((w, h), Image.Resampling.LANCZOS)
        img_b = img_b.resize((w, h), Image.Resampling.LANCZOS)

    if img_a.mode != "RGB":
        img_a = img_a.convert("RGB")
    if img_b.mode != "RGB":
        img_b = img_b.convert("RGB")

    diff = ImageChops.difference(img_a, img_b)
    bbox = diff.getbbox()
    if bbox is None:
        # Identicas
        return 0.0, diff

    # Conta pixels nao-zero (diferentes em qualquer canal)
    total_pixels = img_a.size[0] * img_a.size[1]
    diff_data = diff.getdata()
    diff_pixels = sum(1 for px in diff_data if px != (0, 0, 0))
    pct = (diff_pixels / total_pixels) * 100.0
    return pct, diff


def write_report(timestamp_dir: Path, results: list) -> None:
    """Escreve report HTML simples com tabela de resultados."""
    timestamp_dir.mkdir(parents=True, exist_ok=True)
    html_path = timestamp_dir / "report.html"

    rows = []
    for r in results:
        status_color = "#198754" if r["status"] == "OK" else "#dc3545"
        if r["status"] == "MISSING":
            status_color = "#fd7e14"
        rows.append(f"""
        <tr>
            <td>{r['name']}</td>
            <td>{r['theme']}</td>
            <td style="color:{status_color}">{r['status']}</td>
            <td>{r['diff_pct']:.3f}%</td>
            <td>{r.get('note', '')}</td>
        </tr>
        """)

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Visual Diff Report</title>
<style>
  body {{ font-family: system-ui; margin: 2rem; background: #1a1a1a; color: #e0e0e0; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ padding: 0.5rem 0.75rem; border-bottom: 1px solid #333; text-align: left; }}
  th {{ background: #2a2a2a; }}
  h1 {{ color: #ffd426; }}
</style></head>
<body>
<h1>Visual Diff Report — {datetime.now().isoformat(timespec='seconds')}</h1>
<table>
<thead>
<tr><th>Pagina</th><th>Tema</th><th>Status</th><th>Diff %</th><th>Nota</th></tr>
</thead>
<tbody>
{''.join(rows)}
</tbody>
</table>
</body></html>"""
    html_path.write_text(html, encoding="utf-8")


def load_pages():
    with PAGES_YML.open() as f:
        cfg = yaml.safe_load(f)
    return cfg["pages"], cfg.get("config", {})


def main():
    parser = argparse.ArgumentParser(description="Visual snapshot comparison")
    parser.add_argument("--threshold", type=float, default=None,
                        help="Diff threshold em %% (default: do pages.yml ou 1.0)")
    parser.add_argument("--pages", default="",
                        help="Lista comma-separated (default: todas)")
    parser.add_argument("--themes", default="dark,light",
                        help="Temas (default: dark,light)")
    parser.add_argument("--update-baseline", action="store_true",
                        help="Promove current para baseline (apos cleanup intencional)")
    args = parser.parse_args()

    pages, config = load_pages()
    threshold = args.threshold if args.threshold is not None else config.get("diff_threshold_pct", 1.0)

    selected_pages = set(p.strip() for p in args.pages.split(",") if p.strip())
    selected_themes = [t.strip() for t in args.themes.split(",") if t.strip()]
    if selected_pages:
        pages = [p for p in pages if p["name"] in selected_pages]

    baseline_dir = SNAPSHOTS_DIR / "baseline"
    current_dir = SNAPSHOTS_DIR / "current"

    if not baseline_dir.exists() or not list(baseline_dir.glob("*.png")):
        print(f"[compare] ERRO: nenhum baseline em {baseline_dir}", file=sys.stderr)
        print(f"[compare] Rode: python tests/visual/capture.py --target baseline", file=sys.stderr)
        sys.exit(2)

    if args.update_baseline:
        if not current_dir.exists() or not list(current_dir.glob("*.png")):
            print(f"[compare] ERRO: nenhum current para promover em {current_dir}", file=sys.stderr)
            sys.exit(2)
        # backup do baseline antigo
        backup_dir = SNAPSHOTS_DIR / f"baseline_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if any(baseline_dir.iterdir()):
            shutil.copytree(baseline_dir, backup_dir)
            print(f"[compare] Backup do baseline antigo em {backup_dir.name}/")
        # copiar current → baseline
        for png in current_dir.glob("*.png"):
            shutil.copy(png, baseline_dir / png.name)
        print(f"[compare] Baseline atualizado de current/")
        sys.exit(0)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    report_dir = SNAPSHOTS_DIR / "reports" / timestamp

    results = []
    failures = []

    print(f"[compare] Threshold: {threshold}%")
    print(f"[compare] Baseline:  {baseline_dir}")
    print(f"[compare] Current:   {current_dir}")
    print()

    for p_cfg in pages:
        name = p_cfg["name"]
        for theme in selected_themes:
            fname = f"{name}_{theme}.png"
            base = baseline_dir / fname
            curr = current_dir / fname

            if not base.exists():
                results.append({
                    "name": name, "theme": theme, "status": "MISSING",
                    "diff_pct": 0.0, "note": "baseline ausente",
                })
                print(f"  MISSING  {fname}  (no baseline)")
                continue
            if not curr.exists():
                results.append({
                    "name": name, "theme": theme, "status": "MISSING",
                    "diff_pct": 0.0, "note": "current ausente",
                })
                print(f"  MISSING  {fname}  (no current)")
                continue

            try:
                img_a = Image.open(base)
                img_b = Image.open(curr)
                pct, diff_img = diff_pct(img_a, img_b)
            except Exception as e:
                results.append({
                    "name": name, "theme": theme, "status": "ERROR",
                    "diff_pct": 0.0, "note": str(e)[:80],
                })
                failures.append(fname)
                print(f"  ERROR    {fname}  ({e})")
                continue

            status = "OK" if pct < threshold else "FAIL"
            results.append({
                "name": name, "theme": theme, "status": status,
                "diff_pct": pct, "note": "",
            })
            mark = "OK    " if status == "OK" else "FAIL  "
            print(f"  {mark} {fname}  diff={pct:.3f}%")

            # Salvar diff image para FAILs (visual debugging)
            if status == "FAIL":
                report_dir.mkdir(parents=True, exist_ok=True)
                diff_img.save(report_dir / f"diff_{fname}")
                shutil.copy(base, report_dir / f"baseline_{fname}")
                shutil.copy(curr, report_dir / f"current_{fname}")
                failures.append(fname)

    if results:
        report_dir.mkdir(parents=True, exist_ok=True)
        write_report(report_dir, results)
        print(f"\n[compare] Report em: {report_dir}/report.html")

    if failures:
        print(f"\n[compare] FALHAS ({len(failures)}):")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)

    print(f"\n[compare] OK — {len(results)} comparacoes < {threshold}%")
    sys.exit(0)


if __name__ == "__main__":
    main()
