from __future__ import annotations
import re

_FENCE = re.compile(r"^\s*```")

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
