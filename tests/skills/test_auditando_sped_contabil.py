"""Testa auditoria contabil — equacionalidade saldo, hierarquia."""
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).parent.parent.parent / ".claude" / "skills" / \
    "auditando-sped-contabil" / "scripts"
sys.path.insert(0, str(SKILL_DIR))

from audit_balance import audit_balance_equations, BalanceFinding


def make_parsed_sped(i155_records: list[dict]) -> dict:
    """Helper para montar parsed SPED minimo com so I155."""
    return {
        "metadata": {"total_lines": len(i155_records)},
        "registros": {"I155": i155_records},
    }


def test_balance_equation_holds():
    """Caso valido: saldo_ini D 100 + deb 50 - cred 30 = saldo_fin D 120."""
    parsed = make_parsed_sped([
        {"COD_CTA": "11101", "COD_CCUS": "", "VL_SLD_INI": "100,00",
         "IND_DC_INI": "D", "VL_DEB": "50,00", "VL_CRED": "30,00",
         "VL_SLD_FIN": "120,00", "IND_DC_FIN": "D"},
    ])
    findings = audit_balance_equations(parsed)
    assert findings == [], f"unexpected findings: {findings}"


def test_balance_equation_broken():
    """Caso quebrado: 100 + 50 - 30 != 999."""
    parsed = make_parsed_sped([
        {"COD_CTA": "11101", "COD_CCUS": "", "VL_SLD_INI": "100,00",
         "IND_DC_INI": "D", "VL_DEB": "50,00", "VL_CRED": "30,00",
         "VL_SLD_FIN": "999,00", "IND_DC_FIN": "D"},
    ])
    findings = audit_balance_equations(parsed)
    assert len(findings) == 1
    f = findings[0]
    assert isinstance(f, BalanceFinding)
    assert f.cod_cta == "11101"
    assert f.severidade == "BLOQUEANTE"
    assert "999" in f.descricao or "120" in f.descricao


def test_balance_credora_to_devedora_inversion():
    """Saldo inicial C 100 + deb 200 - cred 50 = saldo fin D 50."""
    parsed = make_parsed_sped([
        {"COD_CTA": "21101", "COD_CCUS": "", "VL_SLD_INI": "100,00",
         "IND_DC_INI": "C", "VL_DEB": "200,00", "VL_CRED": "50,00",
         "VL_SLD_FIN": "50,00", "IND_DC_FIN": "D"},
    ])
    findings = audit_balance_equations(parsed)
    assert findings == [], f"Caso valido (inversao saldo) deve passar: {findings}"


def test_balance_tolerance():
    """Diferenca de 0,01 (arredondamento) NAO deve gerar finding."""
    parsed = make_parsed_sped([
        {"COD_CTA": "11101", "COD_CCUS": "", "VL_SLD_INI": "100,00",
         "IND_DC_INI": "D", "VL_DEB": "50,00", "VL_CRED": "30,00",
         "VL_SLD_FIN": "120,01", "IND_DC_FIN": "D"},
    ])
    findings = audit_balance_equations(parsed, tolerance=0.02)
    assert findings == []


def test_balance_multiple_accounts():
    """Auditoria por conta — uma quebra outra OK."""
    parsed = make_parsed_sped([
        {"COD_CTA": "11101", "COD_CCUS": "", "VL_SLD_INI": "100,00",
         "IND_DC_INI": "D", "VL_DEB": "50,00", "VL_CRED": "30,00",
         "VL_SLD_FIN": "120,00", "IND_DC_FIN": "D"},
        {"COD_CTA": "11102", "COD_CCUS": "", "VL_SLD_INI": "0,00",
         "IND_DC_INI": "D", "VL_DEB": "10,00", "VL_CRED": "0,00",
         "VL_SLD_FIN": "999,00", "IND_DC_FIN": "D"},
    ])
    findings = audit_balance_equations(parsed)
    assert len(findings) == 1
    assert findings[0].cod_cta == "11102"


def test_balance_malformed_record_missing_field():
    """Registro sem campo obrigatorio gera WARNING com malformed=True."""
    parsed = make_parsed_sped([
        {"COD_CTA": "11101", "COD_CCUS": "",
         # VL_SLD_INI faltando
         "IND_DC_INI": "D", "VL_DEB": "50,00", "VL_CRED": "30,00",
         "VL_SLD_FIN": "120,00", "IND_DC_FIN": "D"},
    ])
    findings = audit_balance_equations(parsed)
    assert len(findings) == 1
    f = findings[0]
    assert f.severidade == "WARNING"
    assert f.malformed is True
    assert "malformado" in f.descricao.lower()


def test_balance_malformed_record_invalid_decimal():
    """Valor decimal invalido gera WARNING com malformed=True."""
    parsed = make_parsed_sped([
        {"COD_CTA": "11101", "COD_CCUS": "", "VL_SLD_INI": "abc",
         "IND_DC_INI": "D", "VL_DEB": "50,00", "VL_CRED": "30,00",
         "VL_SLD_FIN": "120,00", "IND_DC_FIN": "D"},
    ])
    findings = audit_balance_equations(parsed)
    assert len(findings) == 1
    assert findings[0].malformed is True


def test_balance_tolerance_zero_strict_mode():
    """tolerance=0: equacao perfeita passa, diff de 0,01 quebra."""
    # Equacao perfeita: deve passar
    parsed_perfect = make_parsed_sped([
        {"COD_CTA": "11101", "COD_CCUS": "", "VL_SLD_INI": "100,00",
         "IND_DC_INI": "D", "VL_DEB": "50,00", "VL_CRED": "30,00",
         "VL_SLD_FIN": "120,00", "IND_DC_FIN": "D"},
    ])
    assert audit_balance_equations(parsed_perfect, tolerance=0) == []

    # Diff de 0,01 com tolerance=0: deve quebrar
    parsed_diff = make_parsed_sped([
        {"COD_CTA": "11101", "COD_CCUS": "", "VL_SLD_INI": "100,00",
         "IND_DC_INI": "D", "VL_DEB": "50,00", "VL_CRED": "30,00",
         "VL_SLD_FIN": "120,01", "IND_DC_FIN": "D"},
    ])
    findings = audit_balance_equations(parsed_diff, tolerance=0)
    assert len(findings) == 1
    assert findings[0].severidade == "BLOQUEANTE"
