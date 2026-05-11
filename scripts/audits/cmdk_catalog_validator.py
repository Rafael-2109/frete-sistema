#!/usr/bin/env python3
"""
Validador de sincronia entre o catalogo Ctrl+K e a sidebar.

Compara:
  - Endpoints url_for(...) usados em app/templates/_sidebar.html
  - Catalogo COMANDOS em app/cmdk/services/comandos.py

Detecta:
  - Endpoints na sidebar AUSENTES no catalogo (precisa adicionar item Ctrl+K)
  - Endpoints no catalogo AUSENTES na sidebar (catalogo desatualizado)

Uso:
  python scripts/audits/cmdk_catalog_validator.py            # falha se houver gap
  python scripts/audits/cmdk_catalog_validator.py --report-only  # nunca falha (CI/audit)
  python scripts/audits/cmdk_catalog_validator.py --json     # output JSON

Exit codes:
  0 = OK ou modo --report-only
  1 = Sincronia quebrada (modo default)
  2 = Erro de execucao (arquivo nao encontrado, parse falhou)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Permitir rodar de qualquer diretorio (sys.path)
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

SIDEBAR_FILE = ROOT / 'app' / 'templates' / '_sidebar.html'
COMANDOS_FILE = ROOT / 'app' / 'cmdk' / 'services' / 'comandos.py'

# Endpoints da sidebar que sao deliberadamente excluidos do Ctrl+K
# (ex: dashboards de logo, links externos, callbacks de submenu)
ENDPOINTS_IGNORADOS = {
    'main.dashboard',                # logo Nacom — ja eh entry point
    'motochefe.dashboard_motochefe', # logo MotoChefe — entry point
    'auth.logout',                   # acao destrutiva, nao deve ser comando navegavel
    'static',                        # built-in Flask (logos, assets) — nao eh navegavel
}


# =============================================================================
# Parsers
# =============================================================================

# Casa: url_for('blueprint.func') ou url_for('blueprint.func', kwarg=...)
RE_URL_FOR = re.compile(r"url_for\(\s*['\"]([\w.]+)['\"]")


def extrair_endpoints_sidebar(path: Path) -> set[str]:
    """Extrai todos os endpoints url_for(...) do _sidebar.html."""
    if not path.exists():
        raise FileNotFoundError(f"Sidebar nao encontrada: {path}")
    text = path.read_text(encoding='utf-8')
    endpoints = set(RE_URL_FOR.findall(text))
    return endpoints - ENDPOINTS_IGNORADOS


def extrair_endpoints_comandos(path: Path) -> set[str]:
    """Importa COMANDOS e extrai endpoint de cada item."""
    if not path.exists():
        raise FileNotFoundError(f"Catalogo nao encontrado: {path}")
    # Import dinamico
    from app.cmdk.services.comandos import COMANDOS
    return {cmd.endpoint for cmd in COMANDOS}


# =============================================================================
# Diff
# =============================================================================

def comparar(sidebar: set[str], catalogo: set[str]) -> dict:
    """Retorna dict com diferencas categorizadas."""
    return {
        'na_sidebar_faltando_no_catalogo': sorted(sidebar - catalogo),
        'no_catalogo_faltando_na_sidebar': sorted(catalogo - sidebar),
        'em_ambos': sorted(sidebar & catalogo),
        'total_sidebar': len(sidebar),
        'total_catalogo': len(catalogo),
    }


# =============================================================================
# Output
# =============================================================================

def imprimir_relatorio(diff: dict) -> None:
    print()
    print("=" * 70)
    print("VALIDADOR Ctrl+K — Sincronia catalogo vs _sidebar.html")
    print("=" * 70)
    print(f"  Endpoints na sidebar:  {diff['total_sidebar']}")
    print(f"  Endpoints no catalogo: {diff['total_catalogo']}")
    print(f"  Em ambos:              {len(diff['em_ambos'])}")
    print()

    falta_cat = diff['na_sidebar_faltando_no_catalogo']
    falta_sid = diff['no_catalogo_faltando_na_sidebar']

    if not falta_cat and not falta_sid:
        print("  ✓ TUDO SINCRONIZADO — catalogo cobre 100% da sidebar.")
        print()
        return

    if falta_cat:
        print(f"  ✗ FALTAM no catalogo Ctrl+K ({len(falta_cat)}):")
        print("    (Endpoints aparecem em _sidebar.html mas nao em comandos.py)")
        for ep in falta_cat:
            print(f"       - {ep}")
        print()
        print("    -> Adicione Comando(...) em app/cmdk/services/comandos.py")
        print("       seguindo as condicoes de permissao da sidebar.")
        print()

    if falta_sid:
        print(f"  ⚠ EXTRAS no catalogo (nao estao na sidebar) ({len(falta_sid)}):")
        print("    (Endpoints aparecem em comandos.py mas nao em _sidebar.html)")
        for ep in falta_sid:
            print(f"       - {ep}")
        print()
        print("    -> Verifique se esses endpoints ainda existem na UI.")
        print("       Se foram removidos, remover tambem do catalogo.")
        print()


# =============================================================================
# Main
# =============================================================================

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--report-only', action='store_true',
        help='Nunca falha (exit 0) — uso em CI sem bloquear.'
    )
    parser.add_argument(
        '--json', action='store_true',
        help='Output em JSON (machine-readable).'
    )
    parser.add_argument(
        '--strict-extras', action='store_true',
        help='Falha tambem se houver extras no catalogo (default: so falha por faltantes).'
    )
    args = parser.parse_args()

    try:
        sidebar = extrair_endpoints_sidebar(SIDEBAR_FILE)
        catalogo = extrair_endpoints_comandos(COMANDOS_FILE)
    except FileNotFoundError as e:
        print(f"ERRO: {e}", file=sys.stderr)
        return 2
    except Exception as e:
        print(f"ERRO inesperado: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 2

    diff = comparar(sidebar, catalogo)

    if args.json:
        print(json.dumps(diff, indent=2, ensure_ascii=False))
    else:
        imprimir_relatorio(diff)

    if args.report_only:
        return 0

    falhou = bool(diff['na_sidebar_faltando_no_catalogo'])
    if args.strict_extras:
        falhou = falhou or bool(diff['no_catalogo_faltando_na_sidebar'])

    return 1 if falhou else 0


if __name__ == '__main__':
    sys.exit(main())
