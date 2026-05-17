"""DSL engine de validacao de campos por registro contra Manual ECD.

Regras carregadas de .claude/skills/auditando-sped-vs-manual/regras/*.yaml.
Cada YAML define: registro, campos (pos, nome, tipo, tamanho, obrigatorio,
valores, decimal), regras_extras (referencia ou descricao).

Engine valida campo por campo: presenca, tipo (C/N), tamanho, lista de valores.
Regras "negocio" complexas (REGRA_HIERARQUIA_COD_SUP) ja estao em
audit_hierarchy.py — DSL nao duplica.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ComplianceFinding:
    tipo: str
    registro: str
    campo: str
    severidade: str = "BLOQUEANTE"
    descricao: str = ""
    contexto: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "categoria": "compliance_manual",
            "tipo": self.tipo,
            "registro": self.registro,
            "campo": self.campo,
            "severidade": self.severidade,
            "descricao": self.descricao,
            "contexto": self.contexto,
        }


def load_regras_yaml(yaml_path: Path) -> dict[str, Any]:
    """Carrega YAML de regras de um registro."""
    with open(yaml_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _is_numeric(value: str) -> bool:
    """Verifica se valor e numerico (aceita separadores BR e ponto decimal)."""
    if value == "":
        return True
    cleaned = value.replace(".", "").replace(",", ".")
    try:
        Decimal(cleaned)
        return True
    except InvalidOperation:
        return False


def validate_record(
    record: dict[str, str],
    regras: dict[str, Any],
) -> list[ComplianceFinding]:
    """Valida um registro contra YAML de regras.

    Para cada campo definido no YAML, verifica:
    1. Obrigatoriedade (campo ausente ou vazio quando obrigatorio=S)
    2. Tipo (N = deve ser numerico)
    3. Tamanho (C = nao exceder ou diferir do tamanho definido)
    4. Valores validos (lista fechada quando campo 'valores' definido)
    """
    findings: list[ComplianceFinding] = []
    registro = regras["registro"]

    for campo_def in regras.get("campos", []):
        nome = campo_def["nome"]
        if nome == "REG":
            continue  # REG eh chave estrutural, sempre presente

        valor = record.get(nome, "")
        obrigatorio = campo_def.get("obrigatorio", "N") == "S"
        tipo = campo_def.get("tipo", "C")
        tamanho = campo_def.get("tamanho")
        valores_validos = campo_def.get("valores")

        # 1. Obrigatoriedade
        if obrigatorio and not valor:
            findings.append(ComplianceFinding(
                tipo="campo_obrigatorio_ausente",
                registro=registro,
                campo=nome,
                severidade="BLOQUEANTE",
                descricao=(
                    f"{registro}.{nome} eh obrigatorio (Manual ECD) mas esta vazio"
                ),
                contexto={"campo_def": campo_def},
            ))
            continue  # sem valor, nao adianta checar tipo/tamanho

        if not valor:
            continue  # campo opcional e vazio = OK

        # 2. Tipo
        if tipo == "N" and not _is_numeric(valor):
            findings.append(ComplianceFinding(
                tipo="tipo_invalido",
                registro=registro,
                campo=nome,
                severidade="BLOQUEANTE",
                descricao=(
                    f"{registro}.{nome} deveria ser numerico, encontrado '{valor}'"
                ),
                contexto={"valor": valor, "tipo_esperado": "N"},
            ))

        # 3. Tamanho (apenas se for inteiro finito; "-" ou None = sem limite)
        if isinstance(tamanho, int) and tamanho > 0 and tipo == "C":
            if len(valor) > tamanho:
                findings.append(ComplianceFinding(
                    tipo="tamanho_invalido",
                    registro=registro,
                    campo=nome,
                    severidade="BLOQUEANTE",
                    descricao=(
                        f"{registro}.{nome} tamanho={len(valor)} excede limite {tamanho}"
                    ),
                    contexto={"valor": valor, "tamanho_max": tamanho},
                ))

        # 4. Valores validos
        if valores_validos and valor not in valores_validos:
            findings.append(ComplianceFinding(
                tipo="valor_nao_listado",
                registro=registro,
                campo=nome,
                severidade="BLOQUEANTE",
                descricao=(
                    f"{registro}.{nome}='{valor}' nao esta na lista de valores "
                    f"validos: {valores_validos}"
                ),
                contexto={"valor": valor, "valores_validos": valores_validos},
            ))

    return findings


def audit_registro_compliance(
    parsed_sped: dict[str, Any],
    regras_dir: Path,
) -> list[ComplianceFinding]:
    """Para cada YAML em regras_dir/, valida registros correspondentes no parsed.

    Itera todos os *.yaml na pasta de regras, carrega o schema de cada
    registro e valida cada ocorrencia encontrada no parsed SPED.
    Adicionar suporte a novo registro = criar novo YAML, zero codigo Python.

    YAMLs com `parser_status: misaligned_blocked` sao PULADOS e geram
    finding informativo (parser local diverge do Manual; rodar DSL contra
    parser bugado produz falso positivo massivo). Ver `parser_fix_required`
    no YAML para localizacao do fix.
    """
    findings: list[ComplianceFinding] = []

    if not regras_dir.is_dir():
        return findings

    for yaml_file in sorted(regras_dir.glob("*.yaml")):
        regras = load_regras_yaml(yaml_file)
        registro = regras["registro"]

        if regras.get("parser_status") == "misaligned_blocked":
            findings.append(ComplianceFinding(
                tipo="yaml_skipped_parser_misaligned",
                registro=registro,
                campo="(YAML inteiro)",
                severidade="INFO",
                descricao=(
                    f"YAML {registro} pulado: parser local diverge do Manual. "
                    f"Fix: {regras.get('parser_fix_required', '(nao informado)')}"
                ),
                contexto={"yaml_file": yaml_file.name},
            ))
            continue

        records = parsed_sped.get("registros", {}).get(registro, [])

        for record in records:
            findings.extend(validate_record(record, regras))

    return findings


if __name__ == "__main__":
    import json
    import sys

    if len(sys.argv) != 2:
        print("Uso: python dsl_engine.py <parsed_sped.json>", file=sys.stderr)
        sys.exit(2)

    with open(sys.argv[1], encoding="utf-8") as f:
        parsed = json.load(f)

    regras_dir = Path(__file__).parent.parent / "regras"
    findings = audit_registro_compliance(parsed, regras_dir)
    print(json.dumps({
        "regras_yaml_aplicadas": [p.stem for p in sorted(regras_dir.glob("*.yaml"))],
        "findings_count": len(findings),
        "findings": [f.to_dict() for f in findings],
    }, ensure_ascii=False, indent=2))
