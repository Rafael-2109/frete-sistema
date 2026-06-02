from __future__ import annotations
import re
from pathlib import Path

_FENCE = re.compile(r"^\s*```")


def resolve_ref(file_path: Path, target: str, root: Path) -> Path | None:
    """Resolve um link/ref markdown -> caminho absoluto, ou None se externo/vazio.
    Regra IDENTICA a C7 (checks_struct): './' '../' ou sem '/' = relativo ao dir do
    arquivo; senao root-relative. Fragmentos (#...) sao removidos."""
    t = target.split("#")[0].strip()
    if not t or t.startswith(("http://", "https://", "mailto:")):
        return None
    if t.startswith("./") or t.startswith("../") or "/" not in t:
        return (file_path.parent / t).resolve()
    return (root / t).resolve()

def fenced_lines(text: str) -> set[int]:
    """Numeros de linha (1-indexed) que estao DENTRO de um bloco ``` ... ``` (cerca de
    codigo). Checagens de CONTEUDO por linha (C7 link-rot, D3 acuracia, B5 markers,
    D4 termos) PULAM estas linhas: exemplos de codigo nao sao prosa nem afirmacoes do
    doc (um doc pode citar `[x](../nao_existe.md)` ou `Modelo.campo_exemplo` como
    ilustracao sem que isso seja um link morto ou um campo inexistente real)."""
    out: set[int] = set()
    in_fence = False
    for i, line in enumerate(text.splitlines(), 1):
        if _FENCE.match(line):
            in_fence = not in_fence
            continue  # a propria linha da cerca nao e conteudo
        if in_fence:
            out.add(i)
    return out
