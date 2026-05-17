"""Diff estrutural SPED nosso vs SPED contadora (ground truth aprovado RFB).

Tres dimensoes:
1. diff_registros_presentes: que registros existem em um mas nao no outro.
2. diff_campos_preenchidos: dado um registro presente em ambos, que campos
   estao vazios no nosso mas preenchidos no ground.
3. diff_estrutural_completo: combinacao.

Nao compara VALORES (datas, montantes) pois nosso periodo eh diferente.
Compara STRUTURA (presenca de registros, campos preenchidos).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class DiffFinding:
    tipo: str  # 'registro_ausente_nosso', 'registro_extra_nosso',
               # 'campo_vazio_nosso', 'campo_extra_nosso'
    registro: str
    severidade: str  # 'BLOQUEANTE' | 'WARNING' | 'INFO'
    descricao: str
    contexto: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "categoria": "diff_ground_truth",
            "tipo": self.tipo,
            "registro": self.registro,
            "severidade": self.severidade,
            "descricao": self.descricao,
            "contexto": self.contexto,
        }


# Severidade default por registro — registros obrigatorios sao BLOQUEANTES,
# opcionais sao WARNINGs. Fonte: app/relatorios_fiscais/manual_ecd/INDEX.md
REGISTROS_OBRIGATORIOS = frozenset({
    "0000", "0001", "0990", "I001", "I010", "I030", "I050", "I150", "I155",
    "I990", "J001", "J005", "J100", "J150", "J900", "J930", "J990",
    "9001", "9900", "9990", "9999",
})

REGISTROS_CONDICIONAIS: dict[str, str] = {
    "J932": "Termo de Verificacao Substituicao (obrigatorio se IND_FIN_ESC=1)",
    "I020": "Campos adicionais (obrigatorio se IDENT_MF=S)",
    "I052": "Codigos aglutinacao (obrigatorio se conta em codes_aglutinacao)",
    "I100": "Centros de custo (opcional)",
    "0150": "Cadastro participantes (obrigatorio se ha relacionamento societario)",
    "0180": "Relacionamento participantes (obrigatorio se ha 0150)",
}


def _severidade_para_registro_ausente(reg: str) -> tuple[str, str]:
    """Retorna (severidade, descr_complemento) para registro ausente."""
    if reg in REGISTROS_OBRIGATORIOS:
        return "BLOQUEANTE", "Registro OBRIGATORIO"
    elif reg in REGISTROS_CONDICIONAIS:
        return "WARNING", f"Condicional: {REGISTROS_CONDICIONAIS[reg]}"
    else:
        return "INFO", "Registro opcional"


def diff_registros_presentes(
    nosso: dict[str, Any],
    ground: dict[str, Any],
) -> list[DiffFinding]:
    """Compara que registros estao em um SPED mas nao no outro."""
    findings: list[DiffFinding] = []

    nosso_regs = set(nosso.get("registros", {}).keys())
    ground_regs = set(ground.get("registros", {}).keys())

    for reg in sorted(ground_regs - nosso_regs):
        severidade, descr_extra = _severidade_para_registro_ausente(reg)
        ground_count = len(ground["registros"][reg])
        findings.append(DiffFinding(
            tipo="registro_ausente_nosso",
            registro=reg,
            severidade=severidade,
            descricao=(
                f"Registro {reg} presente no SPED contadora ({ground_count} "
                f"ocorrencias) mas ausente no nosso. {descr_extra}."
            ),
            contexto={"ground_count": ground_count},
        ))

    for reg in sorted(nosso_regs - ground_regs):
        nosso_count = len(nosso["registros"][reg])
        findings.append(DiffFinding(
            tipo="registro_extra_nosso",
            registro=reg,
            severidade="WARNING",
            descricao=(
                f"Registro {reg} presente no nosso ({nosso_count} "
                f"ocorrencias) mas ausente no SPED contadora. Verificar se eh necessario."
            ),
            contexto={"nosso_count": nosso_count},
        ))

    return findings


def diff_campos_preenchidos(
    nosso: dict[str, Any],
    ground: dict[str, Any],
    registro: str,
) -> list[DiffFinding]:
    """Para um registro presente em ambos, verifica campos vazios no nosso
    que estao preenchidos no ground."""
    findings: list[DiffFinding] = []

    nosso_recs = nosso.get("registros", {}).get(registro, [])
    ground_recs = ground.get("registros", {}).get(registro, [])

    if not nosso_recs or not ground_recs:
        return findings

    # Comparar primeira ocorrencia (suficiente para detectar campos sistemicos vazios)
    nosso_rec = nosso_recs[0]
    ground_rec = ground_recs[0]

    for campo, valor_ground in ground_rec.items():
        valor_nosso = nosso_rec.get(campo, "")
        # Ground preenchido + nosso vazio = finding
        # Checagem explicita: falsy-but-valid (0, False) nao deve ser ignorado
        ground_vazio = valor_ground is None or valor_ground == ""
        nosso_vazio = valor_nosso is None or valor_nosso == ""
        if not ground_vazio and nosso_vazio:
            raw = str(valor_ground)
            preview = (raw[:40] + "...") if len(raw) > 40 else raw
            findings.append(DiffFinding(
                tipo="campo_vazio_nosso",
                registro=registro,
                severidade="WARNING",
                descricao=(
                    f"{registro}.{campo} preenchido no SPED contadora "
                    f"('{preview}') mas vazio no nosso. "
                    f"Verificar mapeamento Odoo."
                ),
                contexto={
                    "campo": campo,
                    "valor_ground": valor_ground,
                    "valor_nosso": valor_nosso,
                },
            ))

    return findings


def diff_estrutural_completo(
    nosso: dict[str, Any],
    ground: dict[str, Any],
) -> list[DiffFinding]:
    """Combinacao das outras funcoes — varre todos os registros comuns."""
    findings = diff_registros_presentes(nosso, ground)

    nosso_regs = set(nosso.get("registros", {}).keys())
    ground_regs = set(ground.get("registros", {}).keys())
    common = nosso_regs & ground_regs

    for reg in sorted(common):
        findings.extend(diff_campos_preenchidos(nosso, ground, reg))

    return findings


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) != 3:
        print("Uso: python diff_truth.py <nosso.json> <ground_truth.json>",
              file=sys.stderr)
        sys.exit(2)

    with open(sys.argv[1], encoding="utf-8") as f:
        nosso = json.load(f)
    with open(sys.argv[2], encoding="utf-8") as f:
        ground = json.load(f)

    findings = diff_estrutural_completo(nosso, ground)
    print(json.dumps({
        "findings_count": len(findings),
        "por_severidade": {
            sev: sum(1 for f in findings if f.severidade == sev)
            for sev in ["BLOQUEANTE", "WARNING", "INFO"]
        },
        "findings": [f.to_dict() for f in findings],
    }, ensure_ascii=False, indent=2))
