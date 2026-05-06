#!/usr/bin/env python3
"""
Visual Snapshot Capture — Playwright

Captura screenshot full-page de paginas-chave em DARK e LIGHT mode.
Salva em tests/visual/snapshots/<target>/<page>_<theme>.png.

Pre-requisitos:
  - App Flask rodando (default http://localhost:5000)
  - Credenciais em UI_VISUAL_EMAIL e UI_VISUAL_PASSWORD env vars
  - Playwright instalado (ja esta no projeto)
  - Browser instalado: python -m playwright install chromium

Uso:
  # captura em snapshots/current/ (para comparar com baseline)
  python tests/visual/capture.py

  # captura em snapshots/baseline/ (define a verdade)
  python tests/visual/capture.py --target baseline

  # paginas especificas
  python tests/visual/capture.py --pages hora_pedidos_lista,hora_estoque_lista

  # URL diferente (CI, staging, etc)
  python tests/visual/capture.py --base-url http://staging.example.com

Saida:
  exit 0  → todos snapshots OK
  exit 1  → falhou em algum (ex: pagina retornou erro)
"""

import argparse
import os
import sys
import time
from pathlib import Path

import yaml
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeoutError

ROOT = Path(__file__).resolve().parents[2]
VISUAL_DIR = ROOT / "tests" / "visual"
SNAPSHOTS_DIR = VISUAL_DIR / "snapshots"
PAGES_YML = VISUAL_DIR / "pages.yml"


def login(page, base_url: str, email: str, password: str) -> bool:
    """Faz login via formulario. Retorna True se sucesso."""
    page.goto(f"{base_url}/auth/login", wait_until="networkidle")
    try:
        page.fill('input[name="email"]', email)
        page.fill('input[name="senha"]', password)
        page.click('button[type="submit"]')
        page.wait_for_load_state("networkidle", timeout=10000)
    except PWTimeoutError:
        print("[capture] ERRO: timeout no login", file=sys.stderr)
        return False

    # Login bem-sucedido = nao ficou em /auth/login
    if "/auth/login" in page.url or "/auth/" in page.url:
        print(f"[capture] ERRO: login falhou (ainda em {page.url})", file=sys.stderr)
        return False
    return True


def set_theme(page, theme: str) -> None:
    """Define tema via localStorage e reload."""
    # Theme handler: base.html lê localStorage 'nacom-theme' antes de render
    page.evaluate(f"() => localStorage.setItem('nacom-theme', '{theme}')")


def capture_page(page, name: str, url: str, theme: str, target_dir: Path,
                 wait_for: str, timeout_ms: int, full_page: bool) -> bool:
    """Captura uma pagina em um tema especifico. Retorna True se sucesso."""
    out_path = target_dir / f"{name}_{theme}.png"

    # Set theme antes de navegar
    set_theme(page, theme)

    try:
        page.goto(url, wait_until=wait_for, timeout=timeout_ms)
    except PWTimeoutError:
        print(f"[capture] timeout em {url} (theme={theme})", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[capture] ERRO em {url} (theme={theme}): {e}", file=sys.stderr)
        return False

    # Validar que tema foi aplicado
    actual_theme = page.evaluate("() => document.documentElement.getAttribute('data-bs-theme')")
    if actual_theme != theme:
        # Force re-apply via JS (caso pagina sobrescreva)
        page.evaluate(
            f"() => {{ document.documentElement.setAttribute('data-bs-theme', '{theme}'); "
            f"document.documentElement.setAttribute('data-theme', '{theme}'); }}"
        )
        time.sleep(0.3)

    # Pequena pausa para fonts/animacoes estabilizarem
    time.sleep(0.5)

    page.screenshot(path=str(out_path), full_page=full_page)
    print(f"[capture] OK  {name}_{theme}.png  ({out_path.stat().st_size // 1024} KB)")
    return True


def load_config():
    with PAGES_YML.open() as f:
        return yaml.safe_load(f)


def main():
    parser = argparse.ArgumentParser(description="Visual snapshot capture (Playwright)")
    parser.add_argument("--target", choices=["baseline", "current"], default="current",
                        help="Onde salvar os snapshots (default: current)")
    parser.add_argument("--base-url", default=os.getenv("UI_VISUAL_BASE_URL", "http://localhost:5000"),
                        help="URL base do app (default: http://localhost:5000 ou env UI_VISUAL_BASE_URL)")
    parser.add_argument("--pages", default="",
                        help="Lista comma-separated de page names (default: todas)")
    parser.add_argument("--themes", default="dark,light",
                        help="Temas comma-separated (default: dark,light)")
    parser.add_argument("--headed", action="store_true",
                        help="Roda com browser visible (debug)")
    args = parser.parse_args()

    email = os.getenv("UI_VISUAL_EMAIL", "")
    password = os.getenv("UI_VISUAL_PASSWORD", "")
    if not email or not password:
        print("[capture] ERRO: defina UI_VISUAL_EMAIL e UI_VISUAL_PASSWORD env vars", file=sys.stderr)
        sys.exit(2)

    cfg = load_config()
    pages = cfg["pages"]
    config = cfg.get("config", {})

    viewport_w = config.get("viewport", {}).get("width", 1440)
    viewport_h = config.get("viewport", {}).get("height", 900)
    wait_for = config.get("wait_for", "networkidle")
    timeout_ms = config.get("timeout_ms", 15000)
    full_page = config.get("full_page", True)

    selected_pages = set(p.strip() for p in args.pages.split(",") if p.strip())
    selected_themes = [t.strip() for t in args.themes.split(",") if t.strip()]

    if selected_pages:
        pages = [p for p in pages if p["name"] in selected_pages]
        if not pages:
            print(f"[capture] ERRO: nenhuma pagina match para --pages={args.pages}", file=sys.stderr)
            sys.exit(2)

    target_dir = SNAPSHOTS_DIR / args.target
    target_dir.mkdir(parents=True, exist_ok=True)

    # Skip pages com placeholder {id} se SAMPLE_IDS nao tem
    sample_ids = {}
    if os.getenv("SAMPLE_IDS"):
        import json
        try:
            sample_ids = json.loads(os.getenv("SAMPLE_IDS"))
        except json.JSONDecodeError:
            print(f"[capture] AVISO: SAMPLE_IDS nao e JSON valido, ignorando", file=sys.stderr)

    print(f"[capture] Target:    {target_dir}")
    print(f"[capture] Base URL:  {args.base_url}")
    print(f"[capture] Pages:     {len(pages)}")
    print(f"[capture] Themes:    {selected_themes}")
    print(f"[capture] Viewport:  {viewport_w}x{viewport_h}")

    failures = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        context = browser.new_context(
            viewport={"width": viewport_w, "height": viewport_h},
            ignore_https_errors=True,
        )
        page = context.new_page()

        if not login(page, args.base_url, email, password):
            browser.close()
            sys.exit(1)
        print(f"[capture] Login OK")

        for p_cfg in pages:
            name = p_cfg["name"]
            url_path = p_cfg["url"]

            # Substituir {id} se necessario
            if "{id}" in url_path:
                key = name.replace("_detalhe", "").replace("_lista", "")
                if key not in sample_ids:
                    print(f"[capture] SKIP {name}: SAMPLE_IDS['{key}'] nao definido")
                    continue
                url_path = url_path.replace("{id}", str(sample_ids[key]))

            full_url = args.base_url.rstrip("/") + url_path

            for theme in selected_themes:
                ok = capture_page(
                    page, name, full_url, theme, target_dir,
                    viewport_w, viewport_h, wait_for, timeout_ms, full_page,
                )
                if not ok:
                    failures.append((name, theme))

        browser.close()

    if failures:
        print(f"\n[capture] FALHAS ({len(failures)}):")
        for name, theme in failures:
            print(f"  - {name} ({theme})")
        sys.exit(1)

    print(f"\n[capture] OK — {len(pages)} paginas x {len(selected_themes)} temas em {target_dir}")
    sys.exit(0)


if __name__ == "__main__":
    main()
