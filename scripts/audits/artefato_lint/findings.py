from __future__ import annotations
from dataclasses import dataclass

@dataclass
class Finding:
    code: str
    path: str
    line: int
    message: str
    severity: str  # "block" | "report"

def exit_code(findings) -> int:
    return 1 if any(f.severity == "block" for f in findings) else 0

def render(findings) -> str:
    if not findings:
        return "OK — nenhum achado."
    lines = ["", f"{'COD':<6} {'SEV':<6} {'LOCAL':<48} MSG", "-" * 90]
    for f in sorted(findings, key=lambda x: (x.severity != "block", x.path, x.line)):
        loc = f"{f.path}:{f.line}"
        lines.append(f"{f.code:<6} {f.severity:<6} {loc:<48} {f.message}")
    n_block = sum(1 for f in findings if f.severity == "block")
    lines += ["-" * 90, f"{len(findings)} achados ({n_block} bloqueantes)"]
    return "\n".join(lines)
