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


# =====================================================================
# audit_hierarchy tests
# =====================================================================

from audit_hierarchy import audit_i050_hierarchy, HierarchyFinding


def make_parsed_i050(i050_records: list[dict], i250_records: list[dict] | None = None) -> dict:
    return {
        "metadata": {"total_lines": len(i050_records)},
        "registros": {
            "I050": i050_records,
            "I250": i250_records or [],
        },
    }


def test_hierarchy_valid():
    """Plano sintetica raiz 1 -> analitica 11 -> 111 valido."""
    parsed = make_parsed_i050([
        {"COD_CTA": "1", "COD_CTA_SUP": "", "NIVEL": "1", "COD_NAT": "01", "IND_CTA": "S", "CTA": "ATIVO"},
        {"COD_CTA": "11", "COD_CTA_SUP": "1", "NIVEL": "2", "COD_NAT": "01", "IND_CTA": "S", "CTA": "CIRCULANTE"},
        {"COD_CTA": "111", "COD_CTA_SUP": "11", "NIVEL": "3", "COD_NAT": "01", "IND_CTA": "A", "CTA": "CAIXA"},
    ])
    findings = audit_i050_hierarchy(parsed)
    assert findings == [], f"unexpected: {findings}"


def test_hierarchy_orphan_cod_sup():
    """COD_CTA_SUP=99 nao existe — orfao."""
    parsed = make_parsed_i050([
        {"COD_CTA": "111", "COD_CTA_SUP": "99", "NIVEL": "3", "COD_NAT": "01", "IND_CTA": "A", "CTA": "CAIXA"},
    ])
    findings = audit_i050_hierarchy(parsed)
    orfaos = [f for f in findings if f.tipo == "orfao_cod_sup"]
    assert len(orfaos) == 1
    assert isinstance(orfaos[0], HierarchyFinding)  # usa o import
    assert orfaos[0].severidade == "BLOQUEANTE"


def test_hierarchy_cod_nat_inconsistent():
    """Filha tem COD_NAT diferente do pai — inconsistencia."""
    parsed = make_parsed_i050([
        {"COD_CTA": "1", "COD_CTA_SUP": "", "NIVEL": "1", "COD_NAT": "01", "IND_CTA": "S", "CTA": "ATIVO"},
        {"COD_CTA": "11", "COD_CTA_SUP": "1", "NIVEL": "2", "COD_NAT": "02", "IND_CTA": "A", "CTA": "ERRO"},
    ])
    findings = audit_i050_hierarchy(parsed)
    assert any(f.tipo == "cod_nat_divergente" for f in findings)


def test_hierarchy_i250_account_not_in_i050():
    """Conta movimentada em I250 mas nao declarada em I050."""
    parsed = make_parsed_i050(
        i050_records=[
            {"COD_CTA": "111", "COD_CTA_SUP": "", "NIVEL": "1", "COD_NAT": "01", "IND_CTA": "A", "CTA": "CAIXA"},
        ],
        i250_records=[
            {"COD_CTA": "FANTASMA", "VL_DC": "100,00", "IND_DC": "D"},
        ],
    )
    findings = audit_i050_hierarchy(parsed)
    assert any(f.tipo == "i250_conta_inexistente" for f in findings)


def test_hierarchy_i250_synthetic_account():
    """Lancamento I250 em conta SINTETICA — erro (so analiticas movimentam)."""
    parsed = make_parsed_i050(
        i050_records=[
            {"COD_CTA": "1", "COD_CTA_SUP": "", "NIVEL": "1", "COD_NAT": "01", "IND_CTA": "S", "CTA": "ATIVO"},
        ],
        i250_records=[
            {"COD_CTA": "1", "VL_DC": "100,00", "IND_DC": "D"},
        ],
    )
    findings = audit_i050_hierarchy(parsed)
    assert any(f.tipo == "i250_conta_sintetica" for f in findings)


def test_hierarchy_no_cycles_detected():
    """Sem ciclos quando hierarquia eh acyclica."""
    parsed = make_parsed_i050([
        {"COD_CTA": "1", "COD_CTA_SUP": "", "NIVEL": "1", "COD_NAT": "01", "IND_CTA": "S", "CTA": "ATIVO"},
        {"COD_CTA": "11", "COD_CTA_SUP": "1", "NIVEL": "2", "COD_NAT": "01", "IND_CTA": "S", "CTA": "X"},
    ])
    findings = audit_i050_hierarchy(parsed)
    cycle_findings = [f for f in findings if f.tipo == "ciclo_hierarquia"]
    assert not cycle_findings


def test_hierarchy_cycle_detected_dedup():
    """Ciclo A->B->A detectado EXATAMENTE 1 vez (testa fix do dedup)."""
    parsed = make_parsed_i050([
        {"COD_CTA": "A", "COD_CTA_SUP": "B", "NIVEL": "1", "COD_NAT": "01", "IND_CTA": "S", "CTA": "X"},
        {"COD_CTA": "B", "COD_CTA_SUP": "A", "NIVEL": "2", "COD_NAT": "01", "IND_CTA": "S", "CTA": "Y"},
    ])
    findings = audit_i050_hierarchy(parsed)
    cycle_findings = [f for f in findings if f.tipo == "ciclo_hierarquia"]
    assert len(cycle_findings) == 1, (
        f"Ciclo deve ser reportado 1 vez (nao {len(cycle_findings)}). "
        f"Findings: {[f.descricao for f in cycle_findings]}"
    )
    assert "A" in cycle_findings[0].descricao
    assert "B" in cycle_findings[0].descricao
