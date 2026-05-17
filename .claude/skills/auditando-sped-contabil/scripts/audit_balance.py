"""Auditoria contabil: equacionalidade saldo inicial + debitos - creditos = saldo final.

Para cada I155 (saldo mensal por conta), valida que:
    signed(saldo_fin) = signed(saldo_ini) + VL_DEB - VL_CRED

Onde signed(saldo) = +saldo se IND_DC=D, -saldo se IND_DC=C.

Tolerancia default 0.01 para arredondamento.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


@dataclass
class BalanceFinding:
    cod_cta: str
    cod_ccus: str
    saldo_ini_signed: Decimal
    deb: Decimal
    cred: Decimal
    saldo_fin_signed: Decimal
    saldo_fin_esperado: Decimal
    diff: Decimal
    severidade: str  # 'BLOQUEANTE' | 'WARNING'
    descricao: str
    malformed: bool = False  # True quando equacao nao pode ser computada (parse error)

    def to_dict(self) -> dict[str, Any]:
        return {
            "categoria": "batimento_contabil",
            "tipo": "equacionalidade_saldo" if not self.malformed else "registro_malformado",
            "cod_cta": self.cod_cta,
            "cod_ccus": self.cod_ccus,
            "saldo_ini_signed": str(self.saldo_ini_signed),
            "deb": str(self.deb),
            "cred": str(self.cred),
            "saldo_fin_signed": str(self.saldo_fin_signed),
            "saldo_fin_esperado": str(self.saldo_fin_esperado),
            "diff": str(self.diff),
            "severidade": self.severidade,
            "descricao": self.descricao,
            "malformed": self.malformed,
        }


def _parse_decimal_brl(value: str) -> Decimal:
    """Converte '1.234,56' ou '1234,56' para Decimal."""
    if not value or value == "":
        return Decimal("0")
    cleaned = value.replace(".", "").replace(",", ".")
    try:
        return Decimal(cleaned)
    except InvalidOperation as e:
        raise ValueError(f"Valor invalido '{value}': {e}")


def _signed(saldo: Decimal, ind_dc: str) -> Decimal:
    """Aplica sinal conforme IND_DC. D = positivo, C = negativo."""
    if ind_dc == "D":
        return saldo
    elif ind_dc == "C":
        return -saldo
    else:
        raise ValueError(f"IND_DC invalido: '{ind_dc}' (esperado D ou C)")


def audit_balance_equations(
    parsed_sped: dict[str, Any],
    tolerance: float = 0.01,
) -> list[BalanceFinding]:
    """Auditoria de equacionalidade contabil em I155.

    Args:
        parsed_sped: output de parseando-sped-ecd.
        tolerance: diferenca tolerada em R$ (default 0.01).

    Returns:
        Lista de BalanceFinding para contas que quebram a equacao.
    """
    i155 = parsed_sped.get("registros", {}).get("I155", [])
    findings: list[BalanceFinding] = []
    tol = Decimal(str(tolerance))

    for record in i155:
        try:
            cod_cta = record["COD_CTA"]
            cod_ccus = record.get("COD_CCUS", "")
            saldo_ini = _parse_decimal_brl(record["VL_SLD_INI"])
            deb = _parse_decimal_brl(record["VL_DEB"])
            cred = _parse_decimal_brl(record["VL_CRED"])
            saldo_fin = _parse_decimal_brl(record["VL_SLD_FIN"])
            ind_dc_ini = record["IND_DC_INI"]
            ind_dc_fin = record["IND_DC_FIN"]

            saldo_ini_s = _signed(saldo_ini, ind_dc_ini)
            saldo_fin_s = _signed(saldo_fin, ind_dc_fin)
            saldo_fin_esperado = saldo_ini_s + deb - cred
            diff = (saldo_fin_s - saldo_fin_esperado).copy_abs()

            if diff > tol:
                findings.append(BalanceFinding(
                    cod_cta=cod_cta,
                    cod_ccus=cod_ccus,
                    saldo_ini_signed=saldo_ini_s,
                    deb=deb,
                    cred=cred,
                    saldo_fin_signed=saldo_fin_s,
                    saldo_fin_esperado=saldo_fin_esperado,
                    diff=diff,
                    severidade="BLOQUEANTE",
                    descricao=(
                        f"Conta {cod_cta} CCUS {cod_ccus or '-'}: "
                        f"saldo_ini_signed={saldo_ini_s} + deb {deb} - cred {cred} = "
                        f"esperado {saldo_fin_esperado}, encontrado {saldo_fin_s} "
                        f"(diff {diff})"
                    ),
                ))
        except (KeyError, ValueError) as e:
            findings.append(BalanceFinding(
                cod_cta=record.get("COD_CTA", "?"),
                cod_ccus=record.get("COD_CCUS", "?"),
                saldo_ini_signed=Decimal("0"),
                deb=Decimal("0"),
                cred=Decimal("0"),
                saldo_fin_signed=Decimal("0"),
                saldo_fin_esperado=Decimal("0"),
                diff=Decimal("0"),
                severidade="WARNING",
                descricao=f"I155 malformado: {e}",
                malformed=True,
            ))

    return findings


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) != 2:
        print("Uso: python audit_balance.py <parsed_sped.json>", file=sys.stderr)
        sys.exit(2)

    with open(sys.argv[1], encoding="utf-8") as f:
        parsed = json.load(f)

    findings = audit_balance_equations(parsed)
    print(json.dumps({
        "total_i155": len(parsed.get("registros", {}).get("I155", [])),
        "findings_count": len(findings),
        "findings": [f.to_dict() for f in findings],
    }, ensure_ascii=False, indent=2, default=str))
