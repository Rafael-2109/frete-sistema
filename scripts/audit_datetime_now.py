#!/usr/bin/env python3
"""
Auditoria e auto-fix de datetime.now() no codebase.

Modos de operacao:
  --report   Gera JSON com TODAS as ocorrencias categorizadas (default)
  --fix      Aplica substituicoes + adiciona imports ausentes
  --verify   Conta ocorrencias restantes e valida que sao apenas TIMING/SKIP
  --dry-run  Mostra o que --fix faria sem alterar arquivos

Uso:
  python scripts/audit_datetime_now.py --report
  python scripts/audit_datetime_now.py --fix
  python scripts/audit_datetime_now.py --verify
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

# Diretorio raiz do projeto
PROJECT_ROOT = Path(__file__).resolve().parent.parent

# =============================================================================
# CONFIGURACAO
# =============================================================================

# Arquivos/dirs a ignorar completamente
SKIP_PATHS = {
    "app/utils/timezone.py",
    "scripts/audit_datetime_now.py",
    ".claude/hooks/ban_datetime_now.py",
}

SKIP_DIRS = {
    "__pycache__",
    ".git",
    "node_modules",
    ".venv",
    "venv",
    "backups",
    ".claude/skills",
    ".claude/tests",
    "tests",
}

SKIP_EXTENSIONS = {".backup", ".bak", ".md", ".txt", ".sql", ".html", ".css", ".js"}

# Patterns de TIMING (medicao de duracao — timezone irrelevante)
TIMING_PATTERNS = [
    r"^\s*inicio\s*=\s*datetime\.now\(\)",
    r"^\s*fim\s*=\s*datetime\.now\(\)",
    r"^\s*start\s*=\s*datetime\.now\(\)",
    r"^\s*end\s*=\s*datetime\.now\(\)",
    r"^\s*t0\s*=\s*datetime\.now\(\)",
    r"^\s*t1\s*=\s*datetime\.now\(\)",
    r"^\s*inicio_\w+\s*=\s*datetime\.now\(\)",
    r"^\s*fim_\w+\s*=\s*datetime\.now\(\)",
    r"^\s*inicio_operacao\s*=\s*datetime\.now\(\)",
    r"^\s*fim_operacao\s*=\s*datetime\.now\(\)",
    r"^\s*tempo_inicio\s*=\s*datetime\.now\(\)",
    r"^\s*tempo_fim\s*=\s*datetime\.now\(\)",
    r"^\s*start_time\s*=\s*datetime\.now\(\)",
    r"^\s*end_time\s*=\s*datetime\.now\(\)",
    r"^\s*hora_inicio\s*=\s*datetime\.now\(\)",
    r"^\s*hora_fim\s*=\s*datetime\.now\(\)",
    r"\(datetime\.now\(\)\s*-\s*inicio",
    r"\(datetime\.now\(\)\s*-\s*start",
    r"\(datetime\.now\(\)\s*-\s*t0",
    r"\(datetime\.now\(\)\s*-\s*tempo_inicio",
    r"\(datetime\.now\(\)\s*-\s*hora_inicio",
    r"\(datetime\.now\(\)\s*-\s*inicio_",
    r"duracao\s*=.*datetime\.now\(\)",
    r"elapsed\s*=.*datetime\.now\(\)",
    r"tempo_decorrido\s*=.*datetime\.now\(\)",
    r"total_seconds\(\)",  # qualquer linha com total_seconds + datetime.now
]

# Patterns que indicam datetime.now() com argumentos (nao datetime.now() puro)
DATETIME_NOW_WITH_ARGS = re.compile(r"datetime\.now\([^)]+\)")


# =============================================================================
# CLASSIFICACAO
# =============================================================================

def classify_occurrence(filepath_rel: str, line: str, lineno: int) -> str:
    """
    Classifica uma ocorrencia de datetime.now().
    Retorna: SKIP | TIMING | ODOO_QUERY | GENERAL
    """
    # datetime.now() com argumentos — nao e nosso alvo
    # (ex: datetime.now(BRASIL_TZ), datetime.now(timezone.utc))
    if DATETIME_NOW_WITH_ARGS.search(line) and "datetime.now()" not in line:
        return "SKIP_WITH_ARGS"

    # Arquivo de timezone — onde as funcoes core vivem
    if filepath_rel in SKIP_PATHS:
        return "SKIP"

    # Checar patterns de TIMING
    for pattern in TIMING_PATTERNS:
        if re.search(pattern, line):
            return "TIMING"

    return "GENERAL"


def should_skip_file(filepath: Path) -> bool:
    """Verifica se o arquivo deve ser ignorado."""
    filepath_rel = str(filepath.relative_to(PROJECT_ROOT))

    # Skip por extensao
    if filepath.suffix in SKIP_EXTENSIONS:
        return True

    # Skip por diretorio
    for skip_dir in SKIP_DIRS:
        if skip_dir in filepath_rel.split(os.sep):
            return True
        if filepath_rel.startswith(skip_dir):
            return True

    # Skip por path exato
    if filepath_rel in SKIP_PATHS:
        return True

    return False


# =============================================================================
# SCANNING
# =============================================================================

def scan_file(filepath: Path) -> list:
    """Escaneia um arquivo e retorna lista de ocorrencias."""
    occurrences = []
    filepath_rel = str(filepath.relative_to(PROJECT_ROOT))

    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return occurrences

    for lineno, line in enumerate(content.splitlines(), 1):
        # Buscar datetime.now() — tanto puro quanto com args
        if "datetime.now()" not in line:
            continue

        category = classify_occurrence(filepath_rel, line, lineno)

        occurrence = {
            "arquivo": filepath_rel,
            "linha": lineno,
            "categoria": category,
            "original": line.rstrip(),
        }

        if category == "GENERAL":
            # Determinar substituicao
            replacement = line.replace("datetime.now()", "agora_utc_naive()")
            occurrence["substituicao"] = replacement.rstrip()
            occurrence["funcao"] = "agora_utc_naive"
        elif category in ("TIMING", "SKIP", "SKIP_WITH_ARGS"):
            occurrence["motivo"] = {
                "TIMING": "medicao de duracao — timezone irrelevante",
                "SKIP": "arquivo core de timezone",
                "SKIP_WITH_ARGS": "datetime.now() com argumentos de timezone",
            }.get(category, "skip")

        occurrences.append(occurrence)

    return occurrences


def scan_all() -> list:
    """Escaneia todo o projeto."""
    all_occurrences = []

    for filepath in sorted(PROJECT_ROOT.rglob("*.py")):
        if should_skip_file(filepath):
            continue
        occurrences = scan_file(filepath)
        all_occurrences.extend(occurrences)

    return all_occurrences


# =============================================================================
# REPORT
# =============================================================================

def report(occurrences: list):
    """Gera relatorio JSON."""
    por_categoria = {}
    acoes = []
    skip = []

    for occ in occurrences:
        cat = occ["categoria"]
        por_categoria[cat] = por_categoria.get(cat, 0) + 1

        if cat == "GENERAL":
            acoes.append(occ)
        else:
            skip.append(occ)

    result = {
        "total": len(occurrences),
        "por_categoria": por_categoria,
        "total_acoes": len(acoes),
        "total_skip": len(skip),
        "acoes": acoes,
        "skip": skip,
    }

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return result


# =============================================================================
# FIX
# =============================================================================

def fix_file(filepath: Path, file_occurrences: list, dry_run: bool = False) -> dict:
    """Aplica fixes em um arquivo."""
    filepath_rel = str(filepath.relative_to(PROJECT_ROOT))
    result = {"arquivo": filepath_rel, "fixes": 0, "import_added": False}

    # Filtrar apenas ocorrencias que precisam de fix
    actionable = [o for o in file_occurrences if o["categoria"] == "GENERAL"]
    if not actionable:
        return result

    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        result["erro"] = str(e)
        return result

    lines = content.splitlines(keepends=True)
    funcoes_necessarias = set()

    # Aplicar substituicoes linha a linha
    for occ in actionable:
        lineno = occ["linha"] - 1  # 0-indexed
        if lineno < len(lines):
            old_line = lines[lineno]
            if "datetime.now()" in old_line:
                funcao = occ.get("funcao", "agora_utc_naive")
                new_line = old_line.replace("datetime.now()", f"{funcao}()")
                lines[lineno] = new_line
                funcoes_necessarias.add(funcao)
                result["fixes"] += 1

    if result["fixes"] == 0:
        return result

    # Gerenciar imports
    new_content = "".join(lines)
    new_content, import_added = ensure_import(new_content, funcoes_necessarias)
    result["import_added"] = import_added

    if not dry_run:
        filepath.write_text(new_content, encoding="utf-8")
    else:
        result["dry_run"] = True

    return result


def ensure_import(content: str, funcoes: set) -> tuple:
    """
    Garante que o import de app.utils.timezone esta presente.
    Retorna (novo_conteudo, import_foi_adicionado).
    """
    import_added = False

    # Verificar se ja tem import de timezone
    existing_import = re.search(
        r"^from\s+app\.utils\.timezone\s+import\s+(.+)$",
        content,
        re.MULTILINE,
    )

    if existing_import:
        # Ja tem import — verificar se as funcoes necessarias estao la
        existing_funcs = {f.strip() for f in existing_import.group(1).split(",")}
        missing = funcoes - existing_funcs

        if missing:
            # Adicionar funcoes faltantes ao import existente
            all_funcs = sorted(existing_funcs | funcoes)
            new_import_line = f"from app.utils.timezone import {', '.join(all_funcs)}"
            content = content[: existing_import.start()] + new_import_line + content[existing_import.end() :]
            import_added = True
    else:
        # Nao tem import — adicionar
        funcs_sorted = sorted(funcoes)
        new_import = f"from app.utils.timezone import {', '.join(funcs_sorted)}\n"

        # Encontrar posicao para inserir (apos ultimo from/import do bloco de imports)
        lines = content.splitlines(keepends=True)
        insert_pos = find_import_insert_position(lines)

        lines.insert(insert_pos, new_import)
        content = "".join(lines)
        import_added = True

    return content, import_added


def find_import_insert_position(lines: list) -> int:
    """
    Encontra a melhor posicao para inserir um novo import.
    Insere apos o ultimo bloco de 'from app...' imports, ou apos imports stdlib.
    """
    last_app_import = -1
    last_any_import = -1
    in_docstring = False
    docstring_char = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Track docstrings
        if not in_docstring:
            if stripped.startswith('"""') or stripped.startswith("'''"):
                docstring_char = stripped[:3]
                if stripped.count(docstring_char) >= 2:
                    continue  # single-line docstring
                in_docstring = True
                continue
        else:
            if docstring_char and docstring_char in stripped:
                in_docstring = False
            continue

        # Ignorar imports indentados (lazy imports dentro de funcoes)
        if line[0:1] in (' ', '\t'):
            continue

        if stripped.startswith("from app.") or stripped.startswith("import app."):
            last_app_import = i + 1
        elif stripped.startswith("from ") or stripped.startswith("import "):
            last_any_import = i + 1

    if last_app_import > 0:
        return last_app_import
    if last_any_import > 0:
        return last_any_import
    return 0


def apply_fixes(occurrences: list, dry_run: bool = False):
    """Aplica todos os fixes."""
    # Agrupar por arquivo
    by_file = {}
    for occ in occurrences:
        arquivo = occ["arquivo"]
        if arquivo not in by_file:
            by_file[arquivo] = []
        by_file[arquivo].append(occ)

    results = []
    total_fixes = 0
    total_imports = 0

    for filepath_rel, file_occs in sorted(by_file.items()):
        filepath = PROJECT_ROOT / filepath_rel
        if not filepath.exists():
            continue

        result = fix_file(filepath, file_occs, dry_run=dry_run)
        if result["fixes"] > 0:
            results.append(result)
            total_fixes += result["fixes"]
            if result["import_added"]:
                total_imports += 1

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Resultado:")
    print(f"  Arquivos modificados: {len(results)}")
    print(f"  Substituicoes aplicadas: {total_fixes}")
    print(f"  Imports adicionados/atualizados: {total_imports}")

    if results:
        print(f"\nDetalhes:")
        for r in results:
            status = f"  {r['arquivo']}: {r['fixes']} fix(es)"
            if r["import_added"]:
                status += " + import"
            if r.get("erro"):
                status += f" [ERRO: {r['erro']}]"
            print(status)

    return results


# =============================================================================
# VERIFY
# =============================================================================

def verify():
    """Verifica que nao restam violacoes."""
    occurrences = scan_all()

    timing = [o for o in occurrences if o["categoria"] == "TIMING"]
    skip = [o for o in occurrences if o["categoria"] in ("SKIP", "SKIP_WITH_ARGS")]
    violations = [o for o in occurrences if o["categoria"] == "GENERAL"]

    print("=" * 60)
    print("VERIFICACAO datetime.now()")
    print("=" * 60)
    print(f"  TIMING (permitido):        {len(timing)}")
    print(f"  SKIP (timezone.py/args):   {len(skip)}")
    print(f"  VIOLACOES:                 {len(violations)}")
    print("=" * 60)

    if violations:
        print("\nVIOLACOES ENCONTRADAS:")
        for v in violations:
            print(f"  {v['arquivo']}:{v['linha']}")
            print(f"    {v['original'].strip()}")
        print(f"\nTotal: {len(violations)} violacoes que precisam ser corrigidas.")
        return False
    else:
        print("\nSUCESSO: Nenhuma violacao encontrada!")
        return True


# =============================================================================
# MAIN
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="Auditoria datetime.now()")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--report", action="store_true", help="Gera relatorio JSON (default)")
    group.add_argument("--fix", action="store_true", help="Aplica substituicoes")
    group.add_argument("--verify", action="store_true", help="Verifica violacoes restantes")
    group.add_argument("--dry-run", action="store_true", help="Mostra o que --fix faria")
    args = parser.parse_args()

    if args.fix:
        occurrences = scan_all()
        report_data = report(occurrences)
        print(f"\n--- Aplicando {report_data['total_acoes']} fixes ---")
        apply_fixes(occurrences, dry_run=False)
    elif args.dry_run:
        occurrences = scan_all()
        report_data = report(occurrences)
        print(f"\n--- DRY RUN: {report_data['total_acoes']} fixes ---")
        apply_fixes(occurrences, dry_run=True)
    elif args.verify:
        success = verify()
        sys.exit(0 if success else 1)
    else:
        # Default: report
        occurrences = scan_all()
        report(occurrences)


if __name__ == "__main__":
    main()
