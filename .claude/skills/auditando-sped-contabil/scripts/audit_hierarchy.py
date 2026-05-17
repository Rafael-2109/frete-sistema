"""Auditoria hierarquia plano de contas (I050) e cross-ref com lancamentos (I250).

Validacoes:
1. orfao_cod_sup: COD_CTA_SUP referencia conta que nao existe em I050
2. ciclo_hierarquia: ciclo nas relacoes pai-filha
3. cod_nat_divergente: filha tem COD_NAT diferente do pai
4. i250_conta_inexistente: I250 referencia COD_CTA nao declarada em I050
5. i250_conta_sintetica: I250 movimenta conta com IND_CTA=S (so analiticas movimentam)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HierarchyFinding:
    tipo: str  # 'orfao_cod_sup', 'ciclo_hierarquia', 'cod_nat_divergente',
               # 'i250_conta_inexistente', 'i250_conta_sintetica'
    cod_cta: str
    severidade: str  # 'BLOQUEANTE' | 'WARNING'
    descricao: str
    contexto: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "categoria": "hierarquia_plano",
            "tipo": self.tipo,
            "cod_cta": self.cod_cta,
            "severidade": self.severidade,
            "descricao": self.descricao,
            "contexto": self.contexto,
        }


def audit_i050_hierarchy(parsed_sped: dict[str, Any]) -> list[HierarchyFinding]:
    """Auditoria completa de hierarquia I050 + cross-ref I250."""
    i050 = parsed_sped.get("registros", {}).get("I050", [])
    i250 = parsed_sped.get("registros", {}).get("I250", [])

    findings: list[HierarchyFinding] = []
    contas_map: dict[str, dict] = {c["COD_CTA"]: c for c in i050}

    # 1. orfao_cod_sup
    for conta in i050:
        cod_sup = conta.get("COD_CTA_SUP", "").strip()
        if cod_sup and cod_sup not in contas_map:
            findings.append(HierarchyFinding(
                tipo="orfao_cod_sup",
                cod_cta=conta["COD_CTA"],
                severidade="BLOQUEANTE",
                descricao=(
                    f"Conta {conta['COD_CTA']} ({conta.get('CTA', '?')}) tem "
                    f"COD_CTA_SUP={cod_sup} que nao existe em I050"
                ),
                contexto={"cod_cta_sup": cod_sup},
            ))

    # 2. ciclo_hierarquia (DFS com deteccao de ciclo)
    def detect_cycle_from(start: str) -> list[str] | None:
        visited: set[str] = set()
        path: list[str] = []
        node = start
        while node:
            if node in path:
                return path[path.index(node):] + [node]
            if node in visited:
                return None
            visited.add(node)
            path.append(node)
            conta = contas_map.get(node)
            if not conta:
                return None
            node = conta.get("COD_CTA_SUP", "").strip()
        return None

    seen_cycles: set[tuple[str, ...]] = set()
    for conta in i050:
        cycle = detect_cycle_from(conta["COD_CTA"])
        if cycle:
            key = tuple(sorted(cycle))
            if key not in seen_cycles:
                seen_cycles.add(key)
                findings.append(HierarchyFinding(
                    tipo="ciclo_hierarquia",
                    cod_cta=cycle[0],
                    severidade="BLOQUEANTE",
                    descricao=f"Ciclo na hierarquia I050: {' -> '.join(cycle)}",
                    contexto={"ciclo": list(cycle)},
                ))

    # 3. cod_nat_divergente
    for conta in i050:
        cod_sup = conta.get("COD_CTA_SUP", "").strip()
        if cod_sup and cod_sup in contas_map:
            pai = contas_map[cod_sup]
            if pai.get("COD_NAT") and conta.get("COD_NAT") and \
                    pai["COD_NAT"] != conta["COD_NAT"]:
                findings.append(HierarchyFinding(
                    tipo="cod_nat_divergente",
                    cod_cta=conta["COD_CTA"],
                    severidade="BLOQUEANTE",
                    descricao=(
                        f"Conta {conta['COD_CTA']} COD_NAT={conta['COD_NAT']} "
                        f"divergente do pai {cod_sup} COD_NAT={pai['COD_NAT']}"
                    ),
                    contexto={
                        "filha_cod_nat": conta["COD_NAT"],
                        "pai_cod_cta": cod_sup,
                        "pai_cod_nat": pai["COD_NAT"],
                    },
                ))

    # 4 + 5. cross-ref I250 -> I050
    for lcto in i250:
        cod_cta = lcto.get("COD_CTA", "").strip()
        if not cod_cta:
            continue
        if cod_cta not in contas_map:
            findings.append(HierarchyFinding(
                tipo="i250_conta_inexistente",
                cod_cta=cod_cta,
                severidade="BLOQUEANTE",
                descricao=(
                    f"I250 lancamento em COD_CTA={cod_cta} mas conta nao "
                    f"declarada em I050"
                ),
                contexto={"vl_dc": lcto.get("VL_DC", ""), "ind_dc": lcto.get("IND_DC", "")},
            ))
        else:
            conta = contas_map[cod_cta]
            if conta.get("IND_CTA") == "S":
                findings.append(HierarchyFinding(
                    tipo="i250_conta_sintetica",
                    cod_cta=cod_cta,
                    severidade="BLOQUEANTE",
                    descricao=(
                        f"I250 movimenta {cod_cta} com IND_CTA=S (sintetica). "
                        f"So contas analiticas (IND_CTA=A) podem ter lancamentos."
                    ),
                    contexto={"cta": conta.get("CTA", "?")},
                ))

    return findings


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) != 2:
        print("Uso: python audit_hierarchy.py <parsed_sped.json>", file=sys.stderr)
        sys.exit(2)

    with open(sys.argv[1], encoding="utf-8") as f:
        parsed = json.load(f)

    findings = audit_i050_hierarchy(parsed)
    print(json.dumps({
        "total_i050": len(parsed.get("registros", {}).get("I050", [])),
        "total_i250": len(parsed.get("registros", {}).get("I250", [])),
        "findings_count": len(findings),
        "findings_por_tipo": {
            tipo: sum(1 for f in findings if f.tipo == tipo)
            for tipo in ["orfao_cod_sup", "ciclo_hierarquia", "cod_nat_divergente",
                         "i250_conta_inexistente", "i250_conta_sintetica"]
        },
        "findings": [f.to_dict() for f in findings],
    }, ensure_ascii=False, indent=2))
