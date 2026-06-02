<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano de implementacao da Onda 0 do PAD-A (fundacao)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-01
-->

# PAD-A — Onda 0 (Fundacao) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Regras de execucao INVIOLAVEIS:** ver `docs/superpowers/specs/2026-06-01-arquitetura-de-artefatos-design.md` §8.5 (onda-a-onda c/ OK explicito, so a lista de arquivos, sem refatorar fora de escopo, parametrizar>criar, completude antes de fechar).

**Goal:** construir a fundacao determinística do PAD-A — os 2 lints (docs+scripts) pytest-cobertos, o scaffold, os 3 hooks, o pre-commit encadeado, a skill, a SOT do padrao e o GLOSSARIO — e rodar o baseline `--report-only` que vira o inventario de divida das Ondas 1-4.

**Architecture:** um pacote Python testavel `scripts/audits/artefato_lint/` (config + parser de header + zonas + checks) com 2 CLIs finas (`doc_audit.py`, `script_audit.py`) espelhando `ui_policy_lint.py` (argparse `--report-only/--enforce-new/--enforce-touched/--strict/--base-ref`, exit 0/1/2). Enforcement em 3 aneis: creation gate (PreToolUse block, itens 1-8 pre-escrita), commit lint (pre-commit encadeado, item 9 + tudo), Stop hook (advisory). LLM-judge/Voyage ficam como **interface stub** na Onda 0 (on-demand depois; memoria [[feedback_evals_llm_caros_preferir_pytest]] veta trigger automatico).

**Tech Stack:** Python 3.12 (stdlib: argparse, re, json, difflib, subprocess, pathlib, dataclasses), pytest, bash (hooks), git. Sem dependencia externa nova na Onda 0.

## Indice

- File Structure (decomposicao)
- Tasks 0-15 (1 secao por task): T0 hubs+skeleton · T1 config · T2 meta · T3 zones · T4 findings · T5 checks_struct · T6 checks_content · T7 checks_dup · T8 checks_script · T9 CLIs · T10 scaffold · T11 hooks+settings · T12 SOT+GLOSSARIO+D1 · T13 skill · T14 pre-commit · T15 baseline
- Ondas subsequentes + Self-Review

---

## File Structure (decomposicao)

```
scripts/audits/artefato_lint.config.json     # limiares/allowlists FIXADOS (spec §5.2)
scripts/audits/artefato_lint/
  __init__.py
  config.py        # carrega config.json + defaults; 1 responsabilidade: configuracao
  meta.py          # parse header doc:meta (HTML comment) / YAML frontmatter / header de script
  zones.py         # classifica path: managed_doc / operational_script / scratch / fora
  findings.py      # dataclass Finding + severidade + render tabela + exit codes
  gitdiff.py       # arquivos no escopo (--enforce-new/--enforce-touched/base-ref) — espelha ui_policy_lint
  checks_struct.py # C1 header, C2 sot_de, C3 hub-existe, C5 secoes-por-tipo, C6 TOC, C7 link-rot, hub-so-ponteiros
  checks_content.py# markers proibidos, glossario, citacao, frases banidas, acuracia-vs-schema
  checks_dup.py    # near-duplicate textual (difflib); semantic_stub() interface (no-op Onda 0)
  checks_script.py # script orfao (nao indexado), ID hardcoded, header de script
  registry.py      # cross-ref bidirecional hub<->artefato (item 9, usado no pre-commit)
scripts/audits/doc_audit.py        # CLI docs (thin)
scripts/audits/script_audit.py     # CLI scripts (thin)
scripts/docs/novo_artefato.py      # scaffold (Anel 1 — caminho facil ja conforme)
.claude/hooks/pad_creation_gate.py # PreToolUse Write|Edit -> itens 1-8 no conteudo proposto
.claude/hooks/pad_stop_completude.py # Stop -> lista pendencias (advisory, nunca bloqueia)
.claude/hooks/pad_sot_modulo.py    # PreToolUse Edit em app/<mod>/** (codigo) -> injeta SOT do modulo
scripts/hooks/pre-commit           # wrapper que encadeia ui + doc + script
scripts/hooks/pre-commit-doc-lint.sh
scripts/hooks/pre-commit-script-lint.sh
tests/audits/test_artefato_meta.py
tests/audits/test_artefato_zones.py
tests/audits/test_artefato_checks_struct.py
tests/audits/test_artefato_checks_content.py
tests/audits/test_artefato_checks_dup.py
tests/audits/test_artefato_checks_script.py
tests/audits/test_artefato_cli.py
.claude/references/ARQUITETURA_DE_ARTEFATOS.md  # SOT do padrao (dono vigente)
.claude/references/GLOSSARIO.md                 # terminologia unica (D1)
docs/superpowers/plans/INDEX.md                 # hub dos planos (corrige auto-orfao)
docs/superpowers/specs/INDEX.md                 # hub das specs (corrige auto-orfao da spec)
```

**Decisao de boundary:** checks separados por familia (struct/content/dup/script) em modulos focados; CLIs sao cascas. `config.json` isola TODO valor calibravel (zero "a criterio do agente").

---

## Task 0: Hubs de plans/specs (corrige auto-orfao) + skeleton do pacote

**Files:**
- Create: `docs/superpowers/plans/INDEX.md`
- Create: `docs/superpowers/specs/INDEX.md`
- Create: `scripts/audits/artefato_lint/__init__.py`

- [ ] **Step 1: criar `docs/superpowers/specs/INDEX.md`** (hub que a spec ja declara)

```markdown
<!-- doc:meta
tipo: index
camada: L1
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-01
-->
# Specs — indice
> **Papel:** mapa das specs de design. So ponteiros.

- [PAD-A — Arquitetura de Artefatos](2026-06-01-arquitetura-de-artefatos-design.md) — padrao deterministico docs+scripts
```

- [ ] **Step 2: criar `docs/superpowers/plans/INDEX.md`** (hub deste plano)

```markdown
<!-- doc:meta
tipo: index
camada: L1
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-01
-->
# Plans — indice
> **Papel:** mapa dos planos de implementacao. So ponteiros.

- [PAD-A Onda 0 — Fundacao](2026-06-01-pad-a-onda-0-fundacao.md) — lints+hooks+scaffold+skill+SOT
```

- [ ] **Step 3: criar pacote** `scripts/audits/artefato_lint/__init__.py`

```python
"""artefato_lint — engine deterministico do PAD-A (docs + scripts).

CLIs: scripts/audits/doc_audit.py e script_audit.py.
Config: scripts/audits/artefato_lint.config.json (limiares FIXADOS — spec §5.2).
"""
__all__ = ["config", "meta", "zones", "findings", "gitdiff"]
```

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/INDEX.md docs/superpowers/specs/INDEX.md scripts/audits/artefato_lint/__init__.py
git commit -m "feat(pad-a): hubs de plans/specs + skeleton artefato_lint (Onda 0 T0)"
```

---

## Task 1: Config FIXADA (spec §5.2)

**Files:**
- Create: `scripts/audits/artefato_lint.config.json`
- Create: `scripts/audits/artefato_lint/config.py`
- Test: `tests/audits/test_artefato_config.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/audits/test_artefato_config.py
from scripts.audits.artefato_lint import config

def test_config_carrega_limiares_fixados():
    c = config.load()
    assert c.dup_textual_block == 0.85
    assert c.dup_semantic_block == 0.92
    assert c.toc_min_lines == 100
    assert "docs/" in c.managed_doc_globs[0] or any("docs" in g for g in c.managed_doc_globs)
    assert "atualmente" in c.banned_time_sensitive
    assert "dezenas" in c.banned_hedge

def test_config_tem_secoes_por_tipo():
    c = config.load()
    assert set(["Fontes"]).issubset(set(c.required_sections["reference"]))
    assert set(["Rollback", "Verificacao"]).issubset(set(c.required_sections["runbook"]))
    assert set(["Status", "Contexto", "Decisao", "Consequencias"]).issubset(set(c.required_sections["adr"]))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/audits/test_artefato_config.py -v`
Expected: FAIL (ModuleNotFoundError / config.load nao existe)

- [ ] **Step 3: criar `scripts/audits/artefato_lint.config.json`**

```json
{
  "managed_doc_globs": ["docs/**/*.md", ".claude/references/**/*.md", ".claude/skills/**/*.md", "app/*/CLAUDE.md", "CLAUDE.md"],
  "operational_script_globs": ["scripts/inventario_2026_05/**/*.py", "app/odoo/estoque/scripts/**/*.py"],
  "ignore_globs": ["**/tests/fixtures/**", "**/_deprecated/**", "**/.venv/**", "**/__pycache__/**"],
  "toc_min_lines": 100,
  "hub_max_prose_lines": 3,
  "hub_warn_lines": 500,
  "dup_textual_block": 0.85,
  "dup_textual_report": 0.75,
  "dup_semantic_block": 0.92,
  "dup_semantic_report": 0.85,
  "id_hardcoded_regex": "\\d{5,}",
  "banned_hedge": ["dezenas", "varios", "varias", "alguns", "algumas", "muitos", "muitas", "aproximadamente"],
  "banned_time_sensitive": ["atualmente", "por enquanto", "recentemente", "hoje em dia"],
  "forbidden_markers_reference": ["~~", "TABELA REFUTADA", "\\u2714v\\d", "ACHADO 20\\d\\d-", "\\ud83d\\udd34"],
  "required_sections": {
    "reference": ["Papel", "Fontes"],
    "runbook": ["Papel", "Pre-condicoes", "Passos", "Rollback", "Verificacao"],
    "how-to": ["Papel"],
    "adr": ["Status", "Contexto", "Decisao", "Consequencias"],
    "explanation": ["Papel", "Contexto"],
    "state": ["Atualizado", "Estado atual", "Pendencias"],
    "index": [],
    "scratch": []
  },
  "valid_tipos": ["reference", "how-to", "runbook", "explanation", "adr", "state", "index", "scratch"],
  "valid_camadas": ["L1", "L2", "L3"],
  "schemas_tables_dir": ".claude/skills/consultando-sql/schemas/tables"
}
```

- [ ] **Step 4: criar `scripts/audits/artefato_lint/config.py`**

```python
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CONFIG_PATH = ROOT / "scripts" / "audits" / "artefato_lint.config.json"

@dataclass
class Config:
    raw: dict
    @property
    def managed_doc_globs(self): return self.raw["managed_doc_globs"]
    @property
    def operational_script_globs(self): return self.raw["operational_script_globs"]
    @property
    def ignore_globs(self): return self.raw["ignore_globs"]
    @property
    def toc_min_lines(self): return self.raw["toc_min_lines"]
    @property
    def hub_max_prose_lines(self): return self.raw["hub_max_prose_lines"]
    @property
    def dup_textual_block(self): return self.raw["dup_textual_block"]
    @property
    def dup_textual_report(self): return self.raw["dup_textual_report"]
    @property
    def dup_semantic_block(self): return self.raw["dup_semantic_block"]
    @property
    def banned_hedge(self): return self.raw["banned_hedge"]
    @property
    def banned_time_sensitive(self): return self.raw["banned_time_sensitive"]
    @property
    def forbidden_markers_reference(self): return self.raw["forbidden_markers_reference"]
    @property
    def required_sections(self): return self.raw["required_sections"]
    @property
    def valid_tipos(self): return self.raw["valid_tipos"]
    @property
    def valid_camadas(self): return self.raw["valid_camadas"]
    @property
    def id_hardcoded_regex(self): return self.raw["id_hardcoded_regex"]
    @property
    def schemas_tables_dir(self): return self.raw["schemas_tables_dir"]

def load(path: Path = CONFIG_PATH) -> "Config":
    return Config(json.loads(Path(path).read_text(encoding="utf-8")))
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m pytest tests/audits/test_artefato_config.py -v`
Expected: PASS (2 passed)

- [ ] **Step 6: Commit**

```bash
git add scripts/audits/artefato_lint.config.json scripts/audits/artefato_lint/config.py tests/audits/test_artefato_config.py
git commit -m "feat(pad-a): config FIXADA + loader (Onda 0 T1)"
```

---

## Task 2: Parser de header `doc:meta` (meta.py)

**Files:**
- Create: `scripts/audits/artefato_lint/meta.py`
- Test: `tests/audits/test_artefato_meta.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/audits/test_artefato_meta.py
from scripts.audits.artefato_lint import meta

DOC = """<!-- doc:meta
tipo: reference
camada: L2
sot_de: regras de frete
hub: .claude/references/INDEX.md
superseded_by: —
atualizado: 2026-06-01
-->
# Titulo
"""

def test_parse_header_html_comment():
    m = meta.parse_doc(DOC)
    assert m.found is True
    assert m.fields["tipo"] == "reference"
    assert m.fields["camada"] == "L2"
    assert m.fields["hub"] == ".claude/references/INDEX.md"

def test_parse_header_ausente():
    m = meta.parse_doc("# Sem header\n")
    assert m.found is False

def test_parse_script_header():
    s = '"""x"""\n# tipo: script\n# etapa: 15\n# doc-dono: docs/x.md\n# hub: scripts/INDEX.md\n'
    m = meta.parse_script(s)
    assert m.fields["etapa"] == "15"
    assert m.fields["doc-dono"] == "docs/x.md"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/audits/test_artefato_meta.py -v`
Expected: FAIL (meta.parse_doc nao existe)

- [ ] **Step 3: criar `scripts/audits/artefato_lint/meta.py`**

```python
from __future__ import annotations
import re
from dataclasses import dataclass, field

DOC_BLOCK = re.compile(r"<!--\s*doc:meta\s*(.*?)-->", re.DOTALL)
YAML_BLOCK = re.compile(r"\A---\s*\n(.*?)\n---", re.DOTALL)
KV = re.compile(r"^\s*([\w-]+)\s*:\s*(.*?)\s*$")
SCRIPT_KV = re.compile(r"^#\s*([\w-]+)\s*:\s*(.*?)\s*$")

@dataclass
class Meta:
    found: bool
    fields: dict = field(default_factory=dict)
    source: str = ""  # "html" | "yaml" | "script" | ""

def _kv_block(text: str, pattern) -> dict:
    out = {}
    for line in text.splitlines():
        m = pattern.match(line)
        if m:
            out[m.group(1)] = m.group(2)
    return out

def parse_doc(content: str) -> Meta:
    m = DOC_BLOCK.search(content)
    if m:
        return Meta(True, _kv_block(m.group(1), KV), "html")
    y = YAML_BLOCK.search(content)
    if y:
        f = _kv_block(y.group(1), KV)
        # skills/memoria usam frontmatter YAML; aceitamos como header valido
        if "tipo" in f or "name" in f:
            return Meta(True, f, "yaml")
    return Meta(False, {}, "")

def parse_script(content: str) -> Meta:
    f = _kv_block(content, SCRIPT_KV)
    return Meta(bool(f), f, "script") if f else Meta(False, {}, "")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/audits/test_artefato_meta.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/audits/artefato_lint/meta.py tests/audits/test_artefato_meta.py
git commit -m "feat(pad-a): parser de header doc:meta + script header (Onda 0 T2)"
```

---

## Task 3: Classificacao de zonas (zones.py)

**Files:**
- Create: `scripts/audits/artefato_lint/zones.py`
- Test: `tests/audits/test_artefato_zones.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/audits/test_artefato_zones.py
from scripts.audits.artefato_lint import zones, config

C = config.load()

def test_doc_gerenciado():
    assert zones.is_managed_doc("docs/x.md", C) is True
    assert zones.is_managed_doc(".claude/references/Y.md", C) is True
    assert zones.is_managed_doc("README.md", C) is False  # raiz nao-CLAUDE nao e gerenciado por glob

def test_script_operacional():
    assert zones.is_operational_script("scripts/inventario_2026_05/15_x.py", C) is True
    assert zones.is_operational_script("app/utils/foo.py", C) is False

def test_ignore_e_scratch():
    assert zones.is_ignored("app/tests/fixtures/x.md", C) is True
    assert zones.is_scratch("<!-- doc:meta\ntipo: scratch\n-->\n") is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/audits/test_artefato_zones.py -v`
Expected: FAIL

- [ ] **Step 3: criar `scripts/audits/artefato_lint/zones.py`**

```python
from __future__ import annotations
from pathlib import PurePath
from . import meta as meta_mod

def _match_any(path: str, globs) -> bool:
    p = PurePath(path)
    return any(p.match(g) for g in globs)

def is_ignored(path: str, cfg) -> bool:
    return _match_any(path, cfg.ignore_globs)

def is_managed_doc(path: str, cfg) -> bool:
    if is_ignored(path, cfg):
        return False
    return _match_any(path, cfg.managed_doc_globs)

def is_operational_script(path: str, cfg) -> bool:
    if is_ignored(path, cfg):
        return False
    return _match_any(path, cfg.operational_script_globs)

def is_scratch(content: str) -> bool:
    m = meta_mod.parse_doc(content)
    return m.fields.get("tipo") == "scratch"
```

> Nota: `PurePath.match` casa `docs/**/*.md` em Python 3.13+? Em 3.12 `**` em `match` e limitado. **Verificacao na implementacao:** se `p.match("docs/**/*.md")` nao casar subpastas em 3.12, trocar por checagem com `fnmatch` sobre o path completo ou `path.startswith` por prefixo de glob. Cobrir com o teste `test_doc_gerenciado` (subpasta `docs/a/b/x.md`).

- [ ] **Step 4: Run test (incluir caso subpasta profunda) e ajustar matcher ate passar**

Run: `python -m pytest tests/audits/test_artefato_zones.py -v`
Expected: PASS (3 passed). Se falhar por `**`, aplicar fallback fnmatch e re-rodar.

- [ ] **Step 5: Commit**

```bash
git add scripts/audits/artefato_lint/zones.py tests/audits/test_artefato_zones.py
git commit -m "feat(pad-a): classificacao de zonas (managed/operational/ignore/scratch) (Onda 0 T3)"
```

---

## Task 4: Findings + exit codes (findings.py)

**Files:**
- Create: `scripts/audits/artefato_lint/findings.py`
- Test: `tests/audits/test_artefato_findings.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/audits/test_artefato_findings.py
from scripts.audits.artefato_lint.findings import Finding, exit_code, render

def test_exit_code_block():
    fs = [Finding("C1", "x.md", 1, "header faltando", "block")]
    assert exit_code(fs) == 1

def test_exit_code_ok_quando_so_report():
    fs = [Finding("D5", "x.md", 1, "near-dup 0.80", "report")]
    assert exit_code(fs) == 0

def test_render_inclui_codigo_e_path():
    out = render([Finding("C7", "docs/x.md", 12, "link morto ../y.md", "block")])
    assert "C7" in out and "docs/x.md" in out and "12" in out
```

- [ ] **Step 2: Run** `python -m pytest tests/audits/test_artefato_findings.py -v` → FAIL

- [ ] **Step 3: criar `scripts/audits/artefato_lint/findings.py`**

```python
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
```

- [ ] **Step 4: Run** → PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/audits/artefato_lint/findings.py tests/audits/test_artefato_findings.py
git commit -m "feat(pad-a): Finding + exit codes + render (Onda 0 T4)"
```

---

## Task 5: Checks estruturais (checks_struct.py)

Cobre: header valido (C1: tipo/camada/atualizado), sot_de presente (C2), hub existe (C3), secoes-por-tipo (C5), TOC>100 (C6), link-rot (C7), hub-so-ponteiros.

**Files:**
- Create: `scripts/audits/artefato_lint/checks_struct.py`
- Test: `tests/audits/test_artefato_checks_struct.py`

- [ ] **Step 1: Write the failing tests** (um por regra; código completo)

```python
# tests/audits/test_artefato_checks_struct.py
from pathlib import Path
from scripts.audits.artefato_lint import checks_struct as cs, config
C = config.load()

def _w(tmp, rel, txt):
    p = tmp / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(txt, encoding="utf-8"); return p

HEAD = ("<!-- doc:meta\ntipo: reference\ncamada: L2\nsot_de: x\n"
        "hub: docs/INDEX.md\nsuperseded_by: —\natualizado: 2026-06-01\n-->\n")

def test_c1_header_invalido_tipo(tmp_path):
    p = _w(tmp_path, "docs/a.md", "<!-- doc:meta\ntipo: bogus\ncamada: L2\nhub: docs/INDEX.md\natualizado: 2026-06-01\nsot_de: x\n-->\n# T\n## Fontes\n")
    fs = cs.check_file(p, tmp_path, C)
    assert any(f.code == "C1" for f in fs)

def test_c3_hub_inexistente(tmp_path):
    p = _w(tmp_path, "docs/a.md", HEAD + "# T\n## Fontes\n")
    fs = cs.check_file(p, tmp_path, C)
    assert any(f.code == "C3" for f in fs)  # docs/INDEX.md nao existe

def test_c5_reference_sem_fontes(tmp_path):
    _w(tmp_path, "docs/INDEX.md", "<!-- doc:meta\ntipo: index\ncamada: L1\nhub: docs/INDEX.md\natualizado: 2026-06-01\nsot_de: —\n-->\n# i\n")
    p = _w(tmp_path, "docs/a.md", HEAD + "# T\nconteudo sem secao fontes\n")
    fs = cs.check_file(p, tmp_path, C)
    assert any(f.code == "C5" for f in fs)

def test_c7_link_rot(tmp_path):
    _w(tmp_path, "docs/INDEX.md", "<!-- doc:meta\ntipo: index\ncamada: L1\nhub: docs/INDEX.md\natualizado: 2026-06-01\nsot_de: —\n-->\n# i\n")
    p = _w(tmp_path, "docs/a.md", HEAD + "# T\nveja [x](../nao_existe.md)\n## Fontes\n")
    fs = cs.check_file(p, tmp_path, C)
    assert any(f.code == "C7" for f in fs)

def test_ok_completo(tmp_path):
    _w(tmp_path, "docs/INDEX.md", "<!-- doc:meta\ntipo: index\ncamada: L1\nhub: docs/INDEX.md\natualizado: 2026-06-01\nsot_de: —\n-->\n# i\n")
    p = _w(tmp_path, "docs/a.md", HEAD + "# T\n## Fontes\nok\n")
    fs = cs.check_file(p, tmp_path, C)
    assert [f for f in fs if f.severity == "block"] == []
```

- [ ] **Step 2: Run** → FAIL

- [ ] **Step 3: criar `scripts/audits/artefato_lint/checks_struct.py`**

```python
from __future__ import annotations
import re
from pathlib import Path
from unicodedata import normalize
from .findings import Finding
from . import meta as meta_mod

MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
HEADING = re.compile(r"^#{1,6}\s+(.*)$", re.M)
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

def _norm(s: str) -> str:
    s = normalize("NFKD", s).encode("ascii", "ignore").decode().lower().strip()
    return re.sub(r"\s+", " ", s)

def check_file(path: Path, root: Path, cfg) -> list[Finding]:
    rel = str(Path(path).resolve().relative_to(Path(root).resolve()))
    text = Path(path).read_text(encoding="utf-8")
    out: list[Finding] = []
    m = meta_mod.parse_doc(text)
    # C1 header
    if not m.found:
        out.append(Finding("C1", rel, 1, "header doc:meta ausente", "block"))
        return out
    tipo = m.fields.get("tipo", "")
    if tipo not in cfg.valid_tipos:
        out.append(Finding("C1", rel, 1, f"tipo invalido: {tipo!r}", "block"))
    if m.fields.get("camada") not in cfg.valid_camadas and m.source != "yaml":
        out.append(Finding("C1", rel, 1, "camada ausente/invalida", "block"))
    if not DATE.match(m.fields.get("atualizado", "")) and m.source != "yaml":
        out.append(Finding("C1", rel, 1, "atualizado ausente/invalida (YYYY-MM-DD)", "block"))
    # C2 sot_de
    if "sot_de" not in m.fields and m.source != "yaml":
        out.append(Finding("C2", rel, 1, "sot_de ausente (tema ou '—')", "block"))
    # C3 hub existe
    hub = m.fields.get("hub", "")
    if hub and hub not in ("—", "-"):
        if not (Path(root) / hub).exists():
            out.append(Finding("C3", rel, 1, f"hub inexistente: {hub}", "block"))
    elif m.source != "yaml":
        out.append(Finding("C3", rel, 1, "hub ausente", "block"))
    # C5 secoes por tipo
    headings = {_norm(h) for h in HEADING.findall(text)}
    for req in cfg.required_sections.get(tipo, []):
        if _norm(req) not in headings and tipo == "reference":
            out.append(Finding("C5", rel, 1, f"secao obrigatoria ausente p/ {tipo}: {req}", "block"))
        elif _norm(req) not in headings:
            out.append(Finding("C5", rel, 1, f"secao obrigatoria ausente p/ {tipo}: {req}", "block"))
    # C6 TOC se >100 linhas
    nlines = text.count("\n") + 1
    if nlines > cfg.toc_min_lines and not re.search(r"(?im)^#{1,3}\s*(indice|table of contents|toc)\b", text):
        out.append(Finding("C6", rel, 1, f"arquivo {nlines} linhas sem TOC", "block"))
    # C7 link-rot (apenas links relativos a arquivos .md/.py/dir)
    for i, line in enumerate(text.splitlines(), 1):
        for target in MD_LINK.findall(line):
            t = target.split("#")[0].strip()
            if not t or t.startswith(("http://", "https://", "mailto:")):
                continue
            base = Path(path).parent if t.startswith((".", "/")) is False and "/" not in t else Path(root)
            cand = (Path(path).parent / t) if (t.startswith("./") or t.startswith("../") or "/" not in t) else (Path(root) / t)
            if not cand.exists():
                out.append(Finding("C7", rel, i, f"link morto: {t}", "block"))
    # hub so ponteiros
    if tipo == "index":
        prose = _prose_block_lines(text)
        if prose > cfg.hub_max_prose_lines:
            out.append(Finding("HUB", rel, 1, f"hub com {prose} linhas de prosa nao-ponteiro (>{cfg.hub_max_prose_lines})", "block"))
    return out

def _prose_block_lines(text: str) -> int:
    """Maior bloco contiguo de linhas que nao sejam ponteiro/heading/meta/branco."""
    best = cur = 0
    in_meta = False
    for line in text.splitlines():
        s = line.strip()
        if s.startswith("<!--"): in_meta = True
        if in_meta:
            if "-->" in s: in_meta = False
            continue
        is_pointer = s.startswith(("-", "*", "#", ">", "|")) or s == "" or bool(MD_LINK.search(s))
        cur = 0 if is_pointer else cur + 1
        best = max(best, cur)
    return best
```

> **Nota de implementacao (C7):** a resolucao de caminho relativo tem 2 casos (relativo ao arquivo via `./`/`../`, ou relativo a raiz). O teste `test_c7_link_rot` usa `../nao_existe.md`; adicionar tambem caso raiz `docs/y.md` inexistente. Ajustar `cand` ate ambos passarem. NAO simplificar removendo um caso (link-rot e o check de maior valor — spec FM7).

- [ ] **Step 4: Run** → PASS (5 passed). Adicionar caso link raiz e re-rodar.

- [ ] **Step 5: Commit**

```bash
git add scripts/audits/artefato_lint/checks_struct.py tests/audits/test_artefato_checks_struct.py
git commit -m "feat(pad-a): checks estruturais C1/C2/C3/C5/C6/C7/HUB (Onda 0 T5)"
```

---

## Task 6: Checks de conteudo (checks_content.py)

Cobre: markers proibidos em `reference` (B5), frases banidas/time-sensitive (D4), citacao em `reference` (D2), glossario (D1), acuracia-vs-schema (D3).

**Files:**
- Create: `scripts/audits/artefato_lint/checks_content.py`
- Test: `tests/audits/test_artefato_checks_content.py`

- [ ] **Step 1: Write the failing tests**

```python
# tests/audits/test_artefato_checks_content.py
from pathlib import Path
from scripts.audits.artefato_lint import checks_content as cc, config
C = config.load()

REF = ("<!-- doc:meta\ntipo: reference\ncamada: L2\nsot_de: x\nhub: docs/INDEX.md\n"
       "superseded_by: —\natualizado: 2026-06-01\n-->\n# T\n")

def _w(tmp, rel, txt):
    p = tmp / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(txt, encoding="utf-8"); return p

def test_marker_refutado(tmp_path):
    p = _w(tmp_path, "docs/a.md", REF + "tabela X 🔴 TABELA REFUTADA\n## Fontes\n")
    fs = cc.check_file(p, tmp_path, C)
    assert any(f.code == "B5" for f in fs)

def test_hedge_banido(tmp_path):
    p = _w(tmp_path, "docs/a.md", REF + "havia varios registros\n## Fontes\nFONTE: x\n")
    fs = cc.check_file(p, tmp_path, C)
    assert any(f.code == "D4" for f in fs)

def test_reference_sem_citacao(tmp_path):
    p = _w(tmp_path, "docs/a.md", REF + "afirmo um fato\n")  # sem ## Fontes nem FONTE:
    fs = cc.check_file(p, tmp_path, C)
    assert any(f.code == "D2" for f in fs)

def test_acuracia_campo_inexistente(tmp_path):
    # schema fake
    sd = tmp_path / ".claude/skills/consultando-sql/schemas/tables"; sd.mkdir(parents=True)
    (sd / "separacao.json").write_text('{"columns":[{"name":"qtd_saldo"}]}', encoding="utf-8")
    p = _w(tmp_path, "docs/a.md", REF + "use Separacao.campo_inexistente\n## Fontes\nFONTE: x\n")
    fs = cc.check_file(p, tmp_path, C)
    assert any(f.code == "D3" for f in fs)
```

- [ ] **Step 2: Run** → FAIL

- [ ] **Step 3: criar `scripts/audits/artefato_lint/checks_content.py`**

```python
from __future__ import annotations
import json, re
from pathlib import Path
from .findings import Finding
from . import meta as meta_mod

TABLE_FIELD = re.compile(r"\b([A-Z][a-zA-Z_]+)\.([a-z_][a-z0-9_]+)\b")  # Modelo.campo

def _body(text: str) -> str:
    return re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

def check_file(path: Path, root: Path, cfg) -> list[Finding]:
    rel = str(Path(path).resolve().relative_to(Path(root).resolve()))
    text = Path(path).read_text(encoding="utf-8")
    tipo = meta_mod.parse_doc(text).fields.get("tipo", "")
    body = _body(text)
    out: list[Finding] = []
    # B5 markers proibidos (so em reference)
    if tipo == "reference":
        for i, line in enumerate(body.splitlines(), 1):
            for pat in cfg.forbidden_markers_reference:
                if re.search(pat, line):
                    out.append(Finding("B5", rel, i, f"marker proibido em reference: /{pat}/", "block"))
    # D4 hedge/time-sensitive (so em reference)
    if tipo == "reference":
        low = body.lower()
        for i, line in enumerate(body.splitlines(), 1):
            ll = line.lower()
            for w in cfg.banned_hedge + cfg.banned_time_sensitive:
                if re.search(rf"\b{re.escape(w)}\b", ll):
                    out.append(Finding("D4", rel, i, f"termo vago/time-sensitive em reference: {w!r}", "block"))
    # D2 citacao em reference
    if tipo == "reference":
        if not re.search(r"(?im)^#{1,4}\s*fontes\b", text) and "FONTE:" not in text:
            out.append(Finding("D2", rel, 1, "reference sem '## Fontes' nem 'FONTE:'", "block"))
    # D3 acuracia de campos vs schema JSON
    sd = Path(root) / cfg.schemas_tables_dir
    if sd.exists():
        for i, line in enumerate(body.splitlines(), 1):
            for modelo, campo in TABLE_FIELD.findall(line):
                tbl = sd / f"{modelo.lower()}.json"
                if tbl.exists():
                    cols = {c.get("name") for c in json.loads(tbl.read_text()).get("columns", [])}
                    if campo not in cols:
                        out.append(Finding("D3", rel, i, f"{modelo}.{campo} nao existe no schema {tbl.name}", "block"))
    # D1 glossario fica em check separado (precisa do GLOSSARIO.md — Task 12); placeholder de interface:
    return out
```

> **Nota:** D1 (glossario) depende de `.claude/references/GLOSSARIO.md` (Task 12). Implementar `check_glossario(path, root, cfg, glossario)` quando o GLOSSARIO existir; adicionar teste entao. NAO inventar termos agora — o glossario nasce na Task 12 com os ofensores reais (company_id/partner_id, MIGRACAO/preprod, qtd_saldo).

- [ ] **Step 4: Run** → PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/audits/artefato_lint/checks_content.py tests/audits/test_artefato_checks_content.py
git commit -m "feat(pad-a): checks de conteudo B5/D2/D3/D4 (Onda 0 T6)"
```

---

## Task 7: Near-duplicate textual + interface semantica (checks_dup.py)

**Files:**
- Create: `scripts/audits/artefato_lint/checks_dup.py`
- Test: `tests/audits/test_artefato_checks_dup.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/audits/test_artefato_checks_dup.py
from scripts.audits.artefato_lint import checks_dup as cd, config
C = config.load()

def test_near_dup_textual_bloqueia():
    a = "A regra de fila RQ exige editar tres arquivos no worker e no start."
    b = "A regra de fila RQ exige editar tres arquivos no worker e no start de novo."
    fs = cd.compare_blocks({"docs/a.md": a, "docs/b.md": b}, C)
    assert any(f.code == "D5" and f.severity == "block" for f in fs)

def test_textos_distintos_nao_disparam():
    fs = cd.compare_blocks({"docs/a.md": "frete para manaus", "docs/b.md": "balanco contabil sped"}, C)
    assert fs == []

def test_semantic_stub_noop():
    # Onda 0: semantic e no-op (sem Voyage); so garante interface
    assert cd.semantic_compare({"docs/a.md": "x"}, C) == []
```

- [ ] **Step 2: Run** → FAIL

- [ ] **Step 3: criar `scripts/audits/artefato_lint/checks_dup.py`**

```python
from __future__ import annotations
from difflib import SequenceMatcher
from itertools import combinations
from .findings import Finding

def compare_blocks(blocks: dict[str, str], cfg) -> list[Finding]:
    out: list[Finding] = []
    items = list(blocks.items())
    for (pa, ta), (pb, tb) in combinations(items, 2):
        ratio = SequenceMatcher(None, ta, tb).ratio()
        if ratio >= cfg.dup_textual_block:
            out.append(Finding("D5", pa, 1, f"near-duplicate textual {ratio:.2f} vs {pb} (use --override+justificativa)", "block"))
        elif ratio >= cfg.dup_textual_report:
            out.append(Finding("D5", pa, 1, f"near-duplicate textual {ratio:.2f} vs {pb}", "report"))
    return out

def semantic_compare(blocks: dict[str, str], cfg) -> list[Finding]:
    """Interface da faixa semantica (Voyage/pgvector). Onda 0: no-op.

    Ativacao on-demand (memoria feedback_evals_llm_caros_preferir_pytest:
    NUNCA trigger automatico). Implementacao real em onda posterior usa
    embeddings ja existentes (~$0.90/mes) com cosseno >= cfg.dup_semantic_block.
    """
    return []
```

- [ ] **Step 4: Run** → PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/audits/artefato_lint/checks_dup.py tests/audits/test_artefato_checks_dup.py
git commit -m "feat(pad-a): near-duplicate textual + stub semantico (Onda 0 T7)"
```

---

## Task 8: Checks de script (checks_script.py)

Cobre: ID hardcoded no nome (C3-script), header de script ausente, script orfao (nao indexado em nenhum INDEX/MAPA da zona).

**Files:**
- Create: `scripts/audits/artefato_lint/checks_script.py`
- Test: `tests/audits/test_artefato_checks_script.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/audits/test_artefato_checks_script.py
from scripts.audits.artefato_lint import checks_script as csr, config
C = config.load()

def _w(tmp, rel, txt):
    p = tmp / rel; p.parent.mkdir(parents=True, exist_ok=True); p.write_text(txt, encoding="utf-8"); return p

def test_id_hardcoded(tmp_path):
    p = _w(tmp_path, "scripts/inventario_2026_05/consolidar_lote_104000015.py", "x=1\n")
    fs = csr.check_file(p, tmp_path, C, index_basenames=set())
    assert any(f.code == "SC-ID" for f in fs)

def test_script_orfao(tmp_path):
    p = _w(tmp_path, "scripts/inventario_2026_05/foo.py", "# tipo: script\n# etapa: 1\n# doc-dono: x\n# hub: y\n")
    fs = csr.check_file(p, tmp_path, C, index_basenames=set())
    assert any(f.code == "SC-ORFAO" for f in fs)

def test_script_indexado_ok(tmp_path):
    p = _w(tmp_path, "scripts/inventario_2026_05/foo.py", "# tipo: script\n# etapa: 1\n# doc-dono: x\n# hub: y\n")
    fs = csr.check_file(p, tmp_path, C, index_basenames={"foo.py"})
    assert [f for f in fs if f.code == "SC-ORFAO"] == []
```

- [ ] **Step 2: Run** → FAIL

- [ ] **Step 3: criar `scripts/audits/artefato_lint/checks_script.py`**

```python
from __future__ import annotations
import re
from pathlib import Path
from .findings import Finding
from . import meta as meta_mod

def check_file(path: Path, root: Path, cfg, index_basenames: set[str]) -> list[Finding]:
    rel = str(Path(path).resolve().relative_to(Path(root).resolve()))
    name = Path(path).name
    out: list[Finding] = []
    if re.search(cfg.id_hardcoded_regex, name):
        out.append(Finding("SC-ID", rel, 1, f"ID de objeto no nome do script: {name}", "block"))
    text = Path(path).read_text(encoding="utf-8")
    m = meta_mod.parse_script(text)
    if not ({"etapa", "doc-dono"} <= set(m.fields)):
        out.append(Finding("SC-HEADER", rel, 1, "header de script ausente (# etapa / # doc-dono / # hub)", "block"))
    if name not in index_basenames:
        out.append(Finding("SC-ORFAO", rel, 1, "script nao indexado em nenhum INDEX/MAPA da zona", "block"))
    return out

def collect_index_basenames(root: Path, cfg) -> set[str]:
    """Coleta basenames .py citados em qualquer INDEX.md/MAPA_SCRIPTS.md das zonas operacionais."""
    names: set[str] = set()
    for g in cfg.operational_script_globs:
        base = Path(root) / g.split("**")[0]
        for idx in list(base.rglob("INDEX.md")) + list(base.rglob("MAPA_SCRIPTS.md")):
            for mref in re.findall(r"[\w./-]+\.py", idx.read_text(encoding="utf-8")):
                names.add(Path(mref).name)
    return names
```

- [ ] **Step 4: Run** → PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/audits/artefato_lint/checks_script.py tests/audits/test_artefato_checks_script.py
git commit -m "feat(pad-a): checks de script (ID hardcoded, header, orfao) (Onda 0 T8)"
```

---

## Task 9: gitdiff (escopo) + CLIs doc_audit/script_audit

**Files:**
- Create: `scripts/audits/artefato_lint/gitdiff.py`
- Create: `scripts/audits/doc_audit.py`
- Create: `scripts/audits/script_audit.py`
- Test: `tests/audits/test_artefato_cli.py`

- [ ] **Step 1: Write the failing test** (smoke do CLI em diretorio temporario git)

```python
# tests/audits/test_artefato_cli.py
import subprocess, sys, os
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]

def test_doc_audit_report_only_roda():
    r = subprocess.run([sys.executable, "scripts/audits/doc_audit.py", "--report-only", "--path", "docs/superpowers/specs"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode in (0, 1)  # roda; report-only nunca 2
    assert "achados" in r.stdout.lower() or "OK" in r.stdout

def test_doc_audit_enforce_new_exit0_quando_sem_diff():
    r = subprocess.run([sys.executable, "scripts/audits/doc_audit.py", "--enforce-new", "--base-ref", "HEAD"],
                       cwd=REPO, capture_output=True, text=True)
    assert r.returncode in (0, 1)
```

- [ ] **Step 2: Run** → FAIL

- [ ] **Step 3: criar `gitdiff.py`** (espelha logica do ui_policy_lint)

```python
from __future__ import annotations
import subprocess
from pathlib import Path

def changed_files(root: Path, base_ref: str | None) -> set[str]:
    """Arquivos novos/modificados vs base_ref + untracked. Espelha ui_policy_lint --enforce-new."""
    files: set[str] = set()
    if base_ref:
        d = subprocess.run(["git", "diff", "--name-only", base_ref], cwd=root, capture_output=True, text=True)
        files |= {l for l in d.stdout.splitlines() if l.strip()}
    u = subprocess.run(["git", "ls-files", "--others", "--exclude-standard"], cwd=root, capture_output=True, text=True)
    files |= {l for l in u.stdout.splitlines() if l.strip()}
    return files

def touched_files(root: Path) -> set[str]:
    """--enforce-touched: working tree (staged+unstaged+untracked)."""
    out: set[str] = set()
    for args in (["git", "diff", "--name-only"], ["git", "diff", "--name-only", "--cached"],
                 ["git", "ls-files", "--others", "--exclude-standard"]):
        r = subprocess.run(args, cwd=root, capture_output=True, text=True)
        out |= {l for l in r.stdout.splitlines() if l.strip()}
    return out
```

- [ ] **Step 4: criar `scripts/audits/doc_audit.py`** (CLI fina, argparse igual ui_policy_lint)

```python
#!/usr/bin/env python3
"""doc_audit — lint deterministico de DOCUMENTOS do PAD-A.

Modos: --report-only (auditoria), --enforce-new (so novos/diff), --enforce-touched
(working tree), --strict (tudo). Exit 0 OK / 1 bloqueado / 2 erro.
"""
from __future__ import annotations
import argparse, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.audits.artefato_lint import config, zones, findings, gitdiff
from scripts.audits.artefato_lint import checks_struct, checks_content, checks_dup

def iter_docs(root: Path, cfg, scope: set[str] | None, path_filter: str | None):
    for p in root.rglob("*.md"):
        rel = str(p.relative_to(root))
        if not zones.is_managed_doc(rel, cfg):
            continue
        if path_filter and not rel.startswith(path_filter):
            continue
        if scope is not None and rel not in scope:
            continue
        if zones.is_scratch(p.read_text(encoding="utf-8")):
            continue
        yield p

def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--report-only", action="store_true")
    g.add_argument("--enforce-new", action="store_true")
    g.add_argument("--enforce-touched", action="store_true")
    g.add_argument("--strict", action="store_true")
    ap.add_argument("--base-ref", default="HEAD")
    ap.add_argument("--path", default=None, help="prefixo de path p/ filtrar (auditoria parcial)")
    args = ap.parse_args()
    cfg = config.load()
    scope = None
    if args.enforce_new:
        scope = gitdiff.changed_files(ROOT, args.base_ref)
    elif args.enforce_touched:
        scope = gitdiff.touched_files(ROOT)
    all_findings = []
    blocks = {}
    try:
        for p in iter_docs(ROOT, cfg, scope, args.path):
            all_findings += checks_struct.check_file(p, ROOT, cfg)
            all_findings += checks_content.check_file(p, ROOT, cfg)
            blocks[str(p.relative_to(ROOT))] = checks_content._body(p.read_text(encoding="utf-8"))
        all_findings += checks_dup.compare_blocks(blocks, cfg)
    except Exception as e:  # exit 2 = erro de execucao
        print(f"erro: {e}", file=sys.stderr)
        return 2
    print(findings.render(all_findings))
    if args.report_only:
        return 0
    return findings.exit_code(all_findings)

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: criar `scripts/audits/script_audit.py`** (analogo, usa checks_script + collect_index_basenames; itera operational_script_globs)

```python
#!/usr/bin/env python3
"""script_audit — lint deterministico de SCRIPTS do PAD-A."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.audits.artefato_lint import config, zones, findings, gitdiff, checks_script

def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--report-only", action="store_true")
    g.add_argument("--enforce-new", action="store_true")
    g.add_argument("--enforce-touched", action="store_true")
    g.add_argument("--strict", action="store_true")
    ap.add_argument("--base-ref", default="HEAD")
    args = ap.parse_args()
    cfg = config.load()
    scope = gitdiff.changed_files(ROOT, args.base_ref) if args.enforce_new else (
            gitdiff.touched_files(ROOT) if args.enforce_touched else None)
    idx = checks_script.collect_index_basenames(ROOT, cfg)
    fs = []
    try:
        for p in ROOT.rglob("*.py"):
            rel = str(p.relative_to(ROOT))
            if not zones.is_operational_script(rel, cfg):
                continue
            if scope is not None and rel not in scope:
                continue
            fs += checks_script.check_file(p, ROOT, cfg, idx)
    except Exception as e:
        print(f"erro: {e}", file=sys.stderr); return 2
    print(findings.render(fs))
    return 0 if args.report_only else findings.exit_code(fs)

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Run** → PASS (2 passed)

- [ ] **Step 7: Commit**

```bash
git add scripts/audits/artefato_lint/gitdiff.py scripts/audits/doc_audit.py scripts/audits/script_audit.py tests/audits/test_artefato_cli.py
git commit -m "feat(pad-a): gitdiff + CLIs doc_audit/script_audit espelhando ui_policy_lint (Onda 0 T9)"
```

---

## Task 10: Scaffold (novo_artefato.py)

**Files:**
- Create: `scripts/docs/novo_artefato.py`
- Test: `tests/audits/test_scaffold.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/audits/test_scaffold.py
import subprocess, sys
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]

def test_scaffold_reference_emite_secoes(tmp_path):
    out = tmp_path / "x.md"
    subprocess.run([sys.executable, "scripts/docs/novo_artefato.py", "--tipo", "reference",
                    "--tema", "frete", "--hub", "docs/INDEX.md", "--out", str(out)], cwd=REPO, check=True)
    txt = out.read_text(encoding="utf-8")
    assert "doc:meta" in txt and "tipo: reference" in txt
    assert "## Fontes" in txt and "**Papel:**" in txt
```

- [ ] **Step 2: Run** → FAIL

- [ ] **Step 3: criar `scripts/docs/novo_artefato.py`** (le required_sections do config e carimba)

```python
#!/usr/bin/env python3
"""Scaffold de artefato conforme PAD-A: nasce com header + secoes obrigatorias do tipo."""
from __future__ import annotations
import argparse, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.audits.artefato_lint import config

def build(tipo, tema, hub, data) -> str:
    cfg = config.load()
    secoes = cfg.required_sections.get(tipo, [])
    header = (f"<!-- doc:meta\ntipo: {tipo}\ncamada: L2\nsot_de: {tema}\n"
              f"hub: {hub}\nsuperseded_by: —\natualizado: {data}\n-->\n")
    body = [f"# {tema}", "", "> **Papel:** <1 linha>.  **Abra quando:** <...>", ""]
    for s in secoes:
        if s == "Papel":
            continue
        body += [f"## {s}", "", "<...>", ""]
    return header + "\n".join(body) + "\n"

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tipo", required=True)
    ap.add_argument("--tema", required=True)
    ap.add_argument("--hub", required=True)
    ap.add_argument("--data", default="2026-06-01")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(build(a.tipo, a.tema, a.hub, a.data), encoding="utf-8")
    print(f"criado: {a.out}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

> **Nota:** `--data` default fixo "2026-06-01" porque scripts do projeto NAO podem usar `datetime.now()` sem passar pela regra de timezone (hook ban_datetime_now). Quem chama informa a data (ou o gate injeta). Ver `.claude/references/REGRAS_TIMEZONE.md`.

- [ ] **Step 4: Run** → PASS

- [ ] **Step 5: Commit**

```bash
git add scripts/docs/novo_artefato.py tests/audits/test_scaffold.py
git commit -m "feat(pad-a): scaffold novo_artefato (Onda 0 T10)"
```

---

## Task 11: Hooks (creation gate, stop, sot-modulo) + settings.json

> **GOTCHA (do diagnostico):** `.claude/settings.json` JA tem hooks (`SessionStart`, `PreToolUse` matcher `Agent`, `PostToolUse` matcher `Agent`). **ESTENDER, nao sobrescrever.** Hooks vivem em `.claude/hooks/` (permissao de Write ja concedida no settings).
> **GOTCHA worktree:** `.git/hooks/` e compartilhado entre worktrees; `settings.json` e por-checkout. O creation gate so ativa quando Claude Code roda com cwd cujo settings.json o tem. Durante o dev (cwd=main), NAO ativa — proposital (nao quero gate meio-pronto bloqueando meu proprio build). Vai a serio no merge para main + restart.

**Files:**
- Create: `.claude/hooks/pad_creation_gate.py`
- Create: `.claude/hooks/pad_stop_completude.py`
- Create: `.claude/hooks/pad_sot_modulo.py`
- Modify: `.claude/settings.json` (estender hooks)
- Test: `tests/audits/test_creation_gate.py`

- [ ] **Step 1: Write the failing test** (gate recebe JSON via stdin, decide)

```python
# tests/audits/test_creation_gate.py
import subprocess, sys, json
from pathlib import Path
REPO = Path(__file__).resolve().parents[2]

def _run(payload):
    return subprocess.run([sys.executable, ".claude/hooks/pad_creation_gate.py"],
                          cwd=REPO, input=json.dumps(payload), capture_output=True, text=True)

def test_gate_bloqueia_doc_sem_header():
    payload = {"tool_name": "Write", "tool_input": {"file_path": str(REPO/"docs/zz.md"), "content": "# sem header\n"}}
    r = _run(payload)
    out = json.loads(r.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] == "deny"

def test_gate_permite_fora_de_zona():
    payload = {"tool_name": "Write", "tool_input": {"file_path": "/tmp/x.md", "content": "qualquer"}}
    r = _run(payload)
    out = json.loads(r.stdout)
    assert out["hookSpecificOutput"]["permissionDecision"] in ("allow", "ask", "")  # nao bloqueia fora de zona
```

- [ ] **Step 2: Run** → FAIL

- [ ] **Step 3: criar `.claude/hooks/pad_creation_gate.py`** (itens 1-8 sobre conteudo proposto; advisory-safe)

```python
#!/usr/bin/env python3
"""PAD-A creation gate (PreToolUse Write|Edit). Valida itens 1-8 do checklist
sobre o CONTEUDO PROPOSTO, antes do arquivo existir. So bloqueia em zona gerenciada.
Item 9 (registro no hub) NAO roda aqui (cross-file -> pre-commit). Saida = JSON
permissionDecision (deny|allow). E5: valida FORMA, nunca forca criar."""
from __future__ import annotations
import json, sys, tempfile
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

def _decision(decision, reason=""):
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": decision, "permissionDecisionReason": reason}}))
    return 0

def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return _decision("allow")
    tin = payload.get("tool_input", {})
    fpath = tin.get("file_path", "")
    content = tin.get("content") or tin.get("new_string") or ""
    if not fpath.endswith(".md") and not fpath.endswith(".py"):
        return _decision("allow")
    try:
        from scripts.audits.artefato_lint import config, zones, checks_struct, checks_content
        cfg = config.load()
        rel = fpath
        try: rel = str(Path(fpath).resolve().relative_to(ROOT))
        except Exception: pass
        if fpath.endswith(".md"):
            if not zones.is_managed_doc(rel, cfg) or zones.is_scratch(content):
                return _decision("allow")
            # escreve em tmp p/ reaproveitar checks (que leem arquivo)
            tf = Path(tempfile.mkstemp(suffix=".md")[1]); tf.write_text(content, encoding="utf-8")
            fs = checks_struct.check_file(tf, ROOT, cfg) + checks_content.check_file(tf, ROOT, cfg)
            tf.unlink(missing_ok=True)
            blockers = [f for f in fs if f.severity == "block"]
            if blockers:
                msg = "PAD-A gate bloqueou. Corrija:\n" + "\n".join(f"  [{b.code}] {b.message}" for b in blockers)
                return _decision("deny", msg)
        return _decision("allow")
    except Exception as e:
        # nunca travar o agente por erro do gate -> advisory-safe
        return _decision("allow", f"(gate ignorado: {e})")

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: criar `.claude/hooks/pad_stop_completude.py`** (Stop, advisory — lista pendencias dos arquivos tocados)

```python
#!/usr/bin/env python3
"""PAD-A Stop hook (advisory). Roda doc_audit/script_audit --enforce-touched e
LISTA pendencias. NUNCA bloqueia (exit 0 sempre). Memoria: nao trava fim de sessao."""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def main() -> int:
    try: json.load(sys.stdin)
    except Exception: pass
    for cli in ("doc_audit.py", "script_audit.py"):
        r = subprocess.run([sys.executable, f"scripts/audits/{cli}", "--enforce-touched"],
                           cwd=ROOT, capture_output=True, text=True)
        if r.returncode == 1:
            print(f"\n[PAD-A] pendencias em arquivos tocados ({cli}):\n{r.stdout}", file=sys.stderr)
    return 0  # advisory

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 5: criar `.claude/hooks/pad_sot_modulo.py`** (PreToolUse Edit em app/<mod>/** codigo -> injeta SOT)

```python
#!/usr/bin/env python3
"""PreToolUse advisory: ao editar codigo em app/<mod>/, injeta additionalContext
apontando a SOT do modulo (app/<mod>/CLAUDE.md), se existir. Nunca bloqueia."""
from __future__ import annotations
import json, sys, re
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]

def main() -> int:
    try: payload = json.load(sys.stdin)
    except Exception: return 0
    fp = payload.get("tool_input", {}).get("file_path", "")
    m = re.search(r"app/([^/]+)/", fp)
    ctx = ""
    if m and fp.endswith(".py"):
        sot = ROOT / "app" / m.group(1) / "CLAUDE.md"
        if sot.exists():
            ctx = f"SOT do modulo {m.group(1)}: app/{m.group(1)}/CLAUDE.md — consulte antes de alterar."
    if ctx:
        print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "additionalContext": ctx}}))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 6: Estender `.claude/settings.json`** — adicionar ao array `PreToolUse` (sem tocar no matcher `Agent`) + criar `Stop`:

```jsonc
// dentro de "hooks":
"PreToolUse": [
  { "matcher": "Agent", "hooks": [ { "type": "command", "command": "python3 .claude/hooks/enriquecer-feature-dev.py" } ] },
  { "matcher": "Write|Edit", "hooks": [ { "type": "command", "command": "python3 .claude/hooks/pad_creation_gate.py" } ] },
  { "matcher": "Edit", "hooks": [ { "type": "command", "command": "python3 .claude/hooks/pad_sot_modulo.py" } ] }
],
"Stop": [
  { "hooks": [ { "type": "command", "command": "python3 .claude/hooks/pad_stop_completude.py" } ] }
]
```

- [ ] **Step 7: Run** `python -m pytest tests/audits/test_creation_gate.py -v` → PASS (2 passed)

- [ ] **Step 8: Commit**

```bash
git add .claude/hooks/pad_creation_gate.py .claude/hooks/pad_stop_completude.py .claude/hooks/pad_sot_modulo.py .claude/settings.json tests/audits/test_creation_gate.py
git commit -m "feat(pad-a): 3 hooks (creation gate / stop / sot-modulo) + settings estendido (Onda 0 T11)"
```

---

## Task 12: SOT do padrao + GLOSSARIO (conteudo)

**Files:**
- Create: `.claude/references/ARQUITETURA_DE_ARTEFATOS.md`
- Create: `.claude/references/GLOSSARIO.md`
- Modify: `scripts/audits/artefato_lint/checks_content.py` (ligar D1 glossario)
- Test: `tests/audits/test_glossario.py`

- [ ] **Step 1:** criar `.claude/references/ARQUITETURA_DE_ARTEFATOS.md` — **dono vigente** do padrao (condensado da spec; tipo `reference`; com `## Fontes` apontando a spec). DEVE passar no proprio `doc_audit.py` (dogfooding).

- [ ] **Step 2:** criar `.claude/references/GLOSSARIO.md` (`tipo: reference`) com os ofensores reais do diagnostico:

```markdown
| Conceito | Termo canonico | Banidos (sinonimos) |
|---|---|---|
| empresa Odoo | company_id | (nao confundir com partner_id) |
| identificador de parceiro | partner_id | — |
| lote de consolidacao | MIGRACAO | preprod, pre-prod (quando for o lote) |
| saldo da Separacao | qtd_saldo | (Carteira usa qtd_saldo_produto_pedido) |
```

- [ ] **Step 3:** test `test_glossario.py`: doc com "partner_id" descrito como "empresa" dispara D1; implementar `checks_content.check_glossario(...)` lendo GLOSSARIO.md (tabela). Run → FAIL → implementar → PASS.

- [ ] **Step 4:** rodar `python scripts/audits/doc_audit.py --report-only --path .claude/references/ARQUITETURA_DE_ARTEFATOS.md` → **deve dar 0 bloqueante** (a SOT cumpre o proprio padrao). Corrigir ate verde.

- [ ] **Step 5: Commit**

```bash
git add .claude/references/ARQUITETURA_DE_ARTEFATOS.md .claude/references/GLOSSARIO.md scripts/audits/artefato_lint/checks_content.py tests/audits/test_glossario.py
git commit -m "feat(pad-a): SOT ARQUITETURA_DE_ARTEFATOS + GLOSSARIO + D1 glossario (Onda 0 T12)"
```

---

## Task 13: Skill padronizando-docs

**Files:**
- Create: `.claude/skills/padronizando-docs/SKILL.md`

- [ ] **Step 1:** criar SKILL.md (frontmatter YAML com `name`, `description` triggers de criar/editar doc/script; corpo = arvore de decisao: "fato novo? -> achar dono via doc_audit/grep -> atualiza dono; decisao? -> ADR; estado? -> ESTADO.md; achado? -> aterrissa + linka 1 hub" + comando do scaffold + checklist 9 itens + ponteiro p/ ARQUITETURA_DE_ARTEFATOS.md). Corpo <500 linhas; referencias 1 nivel.

- [ ] **Step 2:** verificar a skill com `doc_audit.py` (skills sao zona gerenciada): `python scripts/audits/doc_audit.py --report-only --path .claude/skills/padronizando-docs` → tratar findings (frontmatter YAML e header valido via meta.parse_doc source=yaml).

- [ ] **Step 3:** atualizar `ROUTING_SKILLS` se aplicavel (memoria [[feedback_skill_padrao_completo]]: ao mexer em skill, atualizar ROUTING + cross-refs). **Confirmar escopo antes** (regra §8.5.3 — nao criar artefato fora da lista sem OK).

- [ ] **Step 4: Commit**

```bash
git add .claude/skills/padronizando-docs/SKILL.md
git commit -m "feat(pad-a): skill padronizando-docs (Onda 0 T13)"
```

---

## Task 14: Pre-commit encadeado + link no CLAUDE.md

> **GOTCHA:** `.git/hooks/pre-commit` atual = copia de `pre-commit-ui-lint.sh`, **compartilhado entre worktrees**. Encadear afeta TODAS as worktrees. **EXIGE OK explicito do Rafael antes de instalar** (regra §8.5 + harness: nao alterar infra compartilhada sem confirmar).

**Files:**
- Create: `scripts/hooks/pre-commit` (wrapper)
- Create: `scripts/hooks/pre-commit-doc-lint.sh`
- Create: `scripts/hooks/pre-commit-script-lint.sh`
- Modify: `CLAUDE.md` (link L1 para o padrao)

- [ ] **Step 1:** criar `scripts/hooks/pre-commit-doc-lint.sh` e `pre-commit-script-lint.sh` (espelho do ui-lint, chamando `doc_audit.py --enforce-new --base-ref HEAD` e `script_audit.py ...`).

- [ ] **Step 2:** criar `scripts/hooks/pre-commit` (wrapper):

```bash
#!/usr/bin/env bash
set -e
ROOT="$(git rev-parse --show-toplevel)"; cd "$ROOT"
[ -f .venv/bin/activate ] && source .venv/bin/activate
bash scripts/hooks/pre-commit-ui-lint.sh
bash scripts/hooks/pre-commit-doc-lint.sh
bash scripts/hooks/pre-commit-script-lint.sh
exit 0
```

- [ ] **Step 3:** (so apos OK do Rafael) instalar: `ln -sf ../../scripts/hooks/pre-commit .git/hooks/pre-commit && chmod +x .git/hooks/pre-commit`. **Verificar** que ui-lint continua disparando (commit de teste com violacao UI conhecida).

- [ ] **Step 4:** adicionar ao `CLAUDE.md` (secao MODELOS CRITICOS / INDICE) 1 linha L1: `ANTES de criar/editar doc ou script: LER .claude/references/ARQUITETURA_DE_ARTEFATOS.md (padrao PAD-A) ou usar skill padronizando-docs`. **Poda:** so 1 linha (criterio A4: aplica-se amplamente + ausencia causa erro).

- [ ] **Step 5: Commit**

```bash
git add scripts/hooks/pre-commit scripts/hooks/pre-commit-doc-lint.sh scripts/hooks/pre-commit-script-lint.sh CLAUDE.md
git commit -m "feat(pad-a): pre-commit encadeado (ui+doc+script) + link CLAUDE.md (Onda 0 T14)"
```

---

## Task 15: Baseline `--report-only` (inventario de divida -> Ondas 1-4)

**Files:**
- Create: `docs/superpowers/reports/2026-06-01-pad-a-baseline.md` (`tipo: state`)

- [ ] **Step 1:** rodar full audit do legado:

```bash
python scripts/audits/doc_audit.py --report-only > /tmp/pad_doc_baseline.txt
python scripts/audits/script_audit.py --report-only > /tmp/pad_script_baseline.txt
```

- [ ] **Step 2:** consolidar em `docs/superpowers/reports/2026-06-01-pad-a-baseline.md` (`tipo: state`, hub = um reports/INDEX.md a criar): contagem por codigo (C1/C3/C7/D2/D3/SC-ORFAO...), por cluster, lista priorizada. Este relatorio E o input das Ondas 1-4.

- [ ] **Step 3:** rodar `pytest tests/audits/ -v` (suite completa Onda 0) → **tudo verde**.

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/reports/2026-06-01-pad-a-baseline.md docs/superpowers/reports/INDEX.md
git commit -m "feat(pad-a): baseline report-only (inventario de divida p/ Ondas 1-4) (Onda 0 T15)"
```

---

## Ondas subsequentes (planos proprios, gated por baseline verde)

Cada uma vira `docs/superpowers/plans/2026-XX-XX-pad-a-onda-N-*.md` quando a anterior fechar (regra §8.5.2). NAO detalhar agora (sao data-driven pelo baseline da Task 15):
- **Onda 1 — Indice mestre:** criar hubs faltantes + ligar `docs/` ao CLAUDE.md (resolve P3).
- **Onda 2 — Conflitos:** 6 conflitos de memoria + worker-RQ/company_id + aposentar gold-script + unificar constituicao orquestrador-Odoo + consertar MEMORY.md.
- **Onda 3 — Piloto inventario/estoque:** consolidar 163 scripts (indice + aposentar 59 orfaos + parametrizar 9 clusters) + SOT unica + estado em 1 lugar.
- **Onda 4+ — Varredura por cluster** guiada pelo baseline.

---

## Self-Review

**1. Spec coverage (Onda 0):** A1/A2 (header) → T2,T5; A3 SSOT/near-dup → T7; A4 camada/TOC → T5; A5 links → T5(C7); B1 schema-por-tipo → T5(C5); B5 markers → T6; C1-C3 scripts → T8; D1 glossario → T12; D2 citacao → T6; D3 acuracia → T6; D4 banidas → T6; D5 textual+stub semantico → T7; E1 gate → T11; E2 lint+pre-commit → T9,T14; E3 stop → T11; E4 sot-modulo → T11; E5 advisory-safe → T11(gate nunca trava). Scaffold → T10. SOT+GLOSSARIO → T12. Skill → T13. Baseline → T15. **Gaps conhecidos (explicitos):** faixa semantica real (Voyage) e LLM-judge ficam para onda on-demand (memoria veto-trigger); D1 depende do GLOSSARIO (T12, ordem correta).
**2. Placeholder scan:** sem "TBD/implement later". As "Notas de implementacao" marcam pontos de verificacao real (ex.: `**` glob no 3.12, 2 casos de C7) — sao instrucoes concretas, nao placeholders.
**3. Type consistency:** `Finding(code,path,line,message,severity)` usado igual em todos os checks; `check_file(path, root, cfg[, ...])` assinatura consistente (script recebe `index_basenames` a mais); `config.load()` retorna `Config` em todos; CLIs usam `findings.exit_code/render`.

**Riscos reais a vigiar na execucao:** (a) `PurePath.match` com `**` no 3.12 (T3 nota); (b) resolucao de link relativo C7 (T5 nota); (c) instalacao do pre-commit compartilhado entre worktrees (T14 — OK explicito); (d) settings.json estendido sem quebrar matchers `Agent` (T11).
