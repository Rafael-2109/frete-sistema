"""Cria ou completa um INDEX.md listando os leaves .md de uma subpasta.

Uso:
    python scripts/docs/completar_index.py --subdir docs/hora --create --write
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from scripts.docs import _doc_meta


def _referenced(name: str, text: str) -> bool:
    """True se o basename aparece como TOKEN no texto (nao mero substring).
    Evita falso-positivo de colisao: 'a.md' NAO conta como presente dentro de 'ba.md'."""
    return bool(re.search(rf"(?<![\w./-]){re.escape(name)}(?![\w-])", text))


def _title(path: Path) -> str:
    """Retorna o texto da 1a linha que começa com '# '; se não houver, retorna path.stem."""
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.startswith("# "):
                return line[2:].strip()
    except Exception:
        pass
    return path.stem


def run(
    scope_root,
    subdir: str,
    create: bool = False,
    write: bool = False,
    data: str = "2026-06-02",
) -> int:
    subdir_path = Path(scope_root) / subdir
    index_path = subdir_path / "INDEX.md"

    # leaves = .md diretos, excluindo INDEX.md e README.md
    leaves = sorted(
        p
        for p in subdir_path.glob("*.md")
        if p.name not in ("INDEX.md", "README.md")
    )

    if index_path.exists():
        current_text = index_path.read_text(encoding="utf-8")
        missing = [leaf for leaf in leaves if not _referenced(leaf.name, current_text)]

        if missing:
            print(f"Faltantes em {subdir}/INDEX.md ({len(missing)}):")
            for leaf in missing:
                print(f"  - {leaf.name}")
            if write:
                lines_to_add = "".join(
                    f"- [{_title(leaf)}]({leaf.name})\n" for leaf in missing
                )
                with index_path.open("a", encoding="utf-8") as fh:
                    fh.write(lines_to_add)
                print(f"  -> Adicionados {len(missing)} entradas em {index_path}")
        else:
            print(f"INDEX em {subdir} ja esta completo.")
    else:
        # INDEX ausente
        if not create:
            print(f"INDEX ausente em {subdir} (use --create)")
            return 0

        # montar conteudo
        hub = f"{subdir}/INDEX.md"
        header = _doc_meta.build_header("index", hub, data, camada="L1", sot_de="—")
        body_lines = "".join(
            f"- [{_title(leaf)}]({leaf.name})\n" for leaf in leaves
        )
        content = (
            header
            + f"# {subdir_path.name} — indice\n\n"
            + f"> **Papel:** indice de {subdir}. So ponteiros.\n\n"
            + body_lines
            + "\n"
        )

        if write:
            index_path.write_text(content, encoding="utf-8")
            print(f"INDEX criado: {index_path}")
        else:
            print(f"--- preview {index_path} ---")
            print(content)
            print("--- fim preview ---")

    return 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Cria/completa INDEX.md de uma subpasta.")
    parser.add_argument("--scope-root", default=".", help="Raiz do escopo (default: .)")
    parser.add_argument("--subdir", required=True, help="Subdiretório relativo a scope-root")
    parser.add_argument("--create", action="store_true", help="Criar INDEX se ausente")
    parser.add_argument("--write", action="store_true", help="Gravar alterações (sem: dry-run)")
    parser.add_argument("--data", default="2026-06-02", help="Data (YYYY-MM-DD)")
    args = parser.parse_args()

    raise SystemExit(
        run(
            scope_root=args.scope_root,
            subdir=args.subdir,
            create=args.create,
            write=args.write,
            data=args.data,
        )
    )


if __name__ == "__main__":
    main()
