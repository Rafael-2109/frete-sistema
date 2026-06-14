# tests/audits/test_route_template_audit.py
"""Testes do B2 — wiring rota->template.

Um template "existe" se houver, em QUALQUER pasta de template do projeto
(app/templates/ + os template_folder proprios de blueprints), um arquivo cujo
caminho case com o nome referenciado (exato ou por sufixo). Isso evita
falso-positivo (que levaria a `--no-verify`), ao custo de raro falso-negativo.
"""
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.audits.route_template_audit import (
    audit_source, extract_calls, template_exists, load_baseline, finding_key, _audit_paths,
)


# ---- extract_calls (parser) -------------------------------------------------

def test_extract_ignora_dinamico():
    assert extract_calls("render_template(tpl)") == []


def test_extract_literal_com_lineno():
    assert extract_calls("# l1\n# l2\nx = render_template('z.html')") == [("z.html", 3)]


def test_extract_ignora_comentario():
    # string dentro de comentario nao e' chamada real
    assert extract_calls('    # render_template("path/to/exemplo.html", ...)') == []


def test_extract_aspas_duplas():
    assert extract_calls('render_template("d.html")') == [("d.html", 1)]


def test_extract_multilinha():
    assert extract_calls("render_template(\n    'm.html',\n    x=1)") == [("m.html", 1)]


# ---- template_exists (resolucao tolerante a template_folder) ----------------

def test_exists_match_exato():
    assert template_exists("recebimento/x.html", {"templates/recebimento/x.html"})


def test_exists_blueprint_template_folder():
    # arquivo em app/agente/templates/agente/chat.html ; render usa 'agente/chat.html'
    assert template_exists("agente/chat.html", {"agente/templates/agente/chat.html"})


def test_exists_sem_prefixo_resolve_por_sufixo():
    # blueprint com template_folder=app/templates/recebimento ; render('divergencias.html')
    assert template_exists("divergencias.html", {"templates/recebimento/divergencias.html"})


def test_nao_exists():
    assert not template_exists("naoexiste.html", {"templates/agente/chat.html"})


# ---- audit_source (regra) ---------------------------------------------------

def test_audit_inexistente_bloqueia():
    fs = audit_source("return render_template('nope.html')", {"templates/agente/chat.html"})
    assert len(fs) == 1
    assert fs[0].severity == "block"
    assert "nope.html" in fs[0].message


def test_audit_existente_ok():
    assert audit_source("render_template('agente/chat.html')", {"templates/agente/chat.html"}) == []


def test_audit_dinamico_ignorado():
    assert audit_source("render_template(var)", {"templates/a.html"}) == []


def test_audit_comentario_ignorado():
    assert audit_source('# render_template("nope.html")', set()) == []


# ---- baseline (nao travar legado) -------------------------------------------

def test_baseline_filtra_achado_conhecido():
    fs = audit_source("render_template('nope.html')", set(), "app/x.py",
                      baseline={"app/x.py::nope.html"})
    assert fs == []


def test_baseline_nao_filtra_novo():
    fs = audit_source("render_template('novo.html')", set(), "app/x.py",
                      baseline={"app/x.py::nope.html"})
    assert len(fs) == 1
    assert "novo.html" in fs[0].message


def test_load_baseline_ausente_retorna_vazio(tmp_path):
    assert load_baseline(tmp_path / "naoexiste.json") == set()


def test_finding_key_formato_estavel():
    fs = audit_source("render_template('z.html')", set(), "app/y.py")
    assert finding_key(fs[0]) == "app/y.py::z.html"


# ---- escopo: so audita rotas Flask (app/) ----------------------------------

def test_audit_paths_so_app():
    # tests/ e scripts/ contem render_template('...') em strings/docstrings que
    # NAO sao rotas reais -> nao podem ser auditados (auto-bloqueio do proprio gate).
    paths = ["app/x/routes.py", "tests/audits/test_x.py", "scripts/audits/y.py",
             "app/z.py", "foo.txt", "migrations/versions/a.py"]
    assert _audit_paths(paths) == ["app/x/routes.py", "app/z.py"]


# ---- CLI (smoke) ------------------------------------------------------------

def test_cli_tem_help_staged():
    r = subprocess.run(
        [sys.executable, "scripts/audits/route_template_audit.py", "--help"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert "--staged" in r.stdout


def test_cli_all_report_only_roda_no_codigo_real():
    # report-only nunca bloqueia (exit 0); valida que roda contra o codigo real
    r = subprocess.run(
        [sys.executable, "scripts/audits/route_template_audit.py", "--all", "--report-only"],
        cwd=REPO, capture_output=True, text=True,
    )
    assert r.returncode == 0
