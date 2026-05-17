"""Testa DSL engine de validacao de campos contra Manual ECD."""
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent.parent / ".claude" / "skills" / \
    "auditando-sped-vs-manual" / "scripts"
sys.path.insert(0, str(SKILL_DIR))

from dsl_engine import (
    load_regras_yaml,
    validate_record,
    audit_registro_compliance,
    ComplianceFinding,
)


REGRAS_DIR = Path(__file__).parent.parent.parent / ".claude" / "skills" / \
    "auditando-sped-vs-manual" / "regras"


def test_load_regras_i050():
    """Carrega YAML de I050 com campos definidos."""
    regras = load_regras_yaml(REGRAS_DIR / "I050.yaml")
    assert regras["registro"] == "I050"
    assert len(regras["campos"]) > 0
    cod_nat = next(c for c in regras["campos"] if c["nome"] == "COD_NAT")
    assert cod_nat["tipo"] == "C"
    assert cod_nat["tamanho"] == 2
    assert "01" in cod_nat["valores"]


def test_validate_record_campo_obrigatorio_ausente():
    record = {"DT_ALT": "01012024", "COD_NAT": "01"}  # sem IND_CTA
    regras = {
        "registro": "I050",
        "campos": [
            {"pos": 2, "nome": "DT_ALT", "tipo": "N", "tamanho": 8, "obrigatorio": "S"},
            {"pos": 3, "nome": "COD_NAT", "tipo": "C", "tamanho": 2, "obrigatorio": "S"},
            {"pos": 4, "nome": "IND_CTA", "tipo": "C", "tamanho": 1, "obrigatorio": "S",
             "valores": ["S", "A"]},
        ],
    }
    findings = validate_record(record, regras)
    assert any(f.tipo == "campo_obrigatorio_ausente" and "IND_CTA" in f.descricao
               for f in findings)


def test_validate_record_valor_nao_listado():
    record = {"COD_NAT": "99"}
    regras = {
        "registro": "I050",
        "campos": [
            {"pos": 3, "nome": "COD_NAT", "tipo": "C", "tamanho": 2,
             "obrigatorio": "S", "valores": ["01", "02", "03"]},
        ],
    }
    findings = validate_record(record, regras)
    assert any(f.tipo == "valor_nao_listado" for f in findings)


def test_validate_record_tipo_invalido():
    record = {"VL_DC": "abc"}
    regras = {
        "registro": "I250",
        "campos": [
            {"pos": 4, "nome": "VL_DC", "tipo": "N", "tamanho": 19, "decimal": 2,
             "obrigatorio": "S"},
        ],
    }
    findings = validate_record(record, regras)
    assert any(f.tipo == "tipo_invalido" and "numerico" in f.descricao.lower()
               for f in findings)


def test_validate_record_tamanho_excedido():
    record = {"COD_NAT": "001"}  # tamanho 3 != 2
    regras = {
        "registro": "I050",
        "campos": [
            {"pos": 3, "nome": "COD_NAT", "tipo": "C", "tamanho": 2, "obrigatorio": "S"},
        ],
    }
    findings = validate_record(record, regras)
    assert any(f.tipo == "tamanho_invalido" for f in findings)


def test_audit_registro_compliance_full():
    """Auditoria de varios registros I050 num parsed SPED."""
    parsed = {
        "registros": {
            "I050": [
                {"DT_ALT": "01012024", "COD_NAT": "01", "IND_CTA": "S",
                 "NIVEL": "1", "COD_CTA": "1", "COD_CTA_SUP": "", "CTA": "ATIVO"},
                {"DT_ALT": "01012024", "COD_NAT": "99", "IND_CTA": "X",
                 "NIVEL": "1", "COD_CTA": "2", "COD_CTA_SUP": "", "CTA": "ERRO"},
            ],
        },
    }
    findings = audit_registro_compliance(parsed, REGRAS_DIR)
    assert len(findings) >= 2
    assert any("COD_NAT" in f.descricao for f in findings)
    assert any("IND_CTA" in f.descricao for f in findings)


def test_compliance_finding_to_dict():
    """ComplianceFinding.to_dict() retorna dict serializavel."""
    f = ComplianceFinding(
        tipo="campo_obrigatorio_ausente",
        registro="I050",
        campo="IND_CTA",
        severidade="BLOQUEANTE",
        descricao="teste",
    )
    d = f.to_dict()
    assert d["categoria"] == "compliance_manual"
    assert d["tipo"] == "campo_obrigatorio_ausente"
    assert isinstance(d, dict)


def test_load_todos_yamls_validos():
    """Smoke: todos os YAMLs em regras/ carregam sem erro e tem campos."""
    yamls = sorted(REGRAS_DIR.glob("*.yaml"))
    assert len(yamls) >= 5, (
        f"Esperado >=5 YAMLs (I050, I155, I250, J100, J150). "
        f"Encontrado {len(yamls)}: {[y.name for y in yamls]}"
    )
    for yaml_file in yamls:
        regras = load_regras_yaml(yaml_file)
        assert "registro" in regras, f"{yaml_file.name} sem campo 'registro'"
        assert "campos" in regras, f"{yaml_file.name} sem campo 'campos'"
        assert len(regras["campos"]) > 0, f"{yaml_file.name} com lista campos vazia"
        # REG sempre como campo 1 (sanity)
        reg_campo = next((c for c in regras["campos"] if c["nome"] == "REG"), None)
        assert reg_campo is not None, f"{yaml_file.name} sem campo REG"
        assert reg_campo["valores"] == [regras["registro"]], (
            f"{yaml_file.name}: REG.valores={reg_campo['valores']} != "
            f"['{regras['registro']}']"
        )


def test_parser_status_misaligned_pula_yaml(tmp_path):
    """Mecanismo de skip via parser_status continua funcional para YAMLs
    bloqueados — testa contra YAML sintetico (J100/J150 reais foram
    desbloqueados em 2026-05-17 apos fix do parser)."""
    yaml_blocked = tmp_path / "FAKE.yaml"
    yaml_blocked.write_text(
        "registro: FAKE\n"
        "descricao: registro fake para testar skip\n"
        "parser_status: misaligned_blocked\n"
        "parser_fix_required: \"path/to/fix\"\n"
        "campos:\n"
        "  - {pos: 1, nome: REG, tipo: C, tamanho: 4, obrigatorio: S, valores: [FAKE]}\n",
        encoding="utf-8",
    )
    parsed = {"registros": {"FAKE": [{"REG": "FAKE"}]}}
    findings = audit_registro_compliance(parsed, tmp_path)
    misaligned = [f for f in findings
                  if f.tipo == "yaml_skipped_parser_misaligned"]
    assert len(misaligned) == 1
    assert misaligned[0].registro == "FAKE"
    assert misaligned[0].severidade == "INFO"
    assert "path/to/fix" in misaligned[0].descricao
