<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano de implementacao da Onda 1 do PAD-A (indice mestre / navegabilidade)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->

# PAD-A — Onda 1 (Indice mestre) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Regras de execucao INVIOLAVEIS:** ver `docs/superpowers/specs/2026-06-01-arquitetura-de-artefatos-design.md` §8.5 (onda-a-onda c/ OK explicito, so a lista de arquivos, sem refatorar fora de escopo, parametrizar>criar, completude antes de fechar).

**Goal:** entregar a navegabilidade do PAD-A (spec §8 Onda 1): um detector deterministico de alcancabilidade/bidirecionalidade (C8, advisory) + o esqueleto minimo de hubs que liga a arvore `docs/` ao `CLAUDE.md` e fecha as 2 violacoes bidir existentes — SEM migrar os 645 headers ausentes (isso e Onda 4+).

**Architecture:** o detector C8 e um modulo global `checks_reach.py` espelhando `checks_dup.py` (recebe o mapa de todos os docs apos o loop da CLI, retorna `Finding`s com severidade `report`). O modelo de aresta credita markdown-link **E** code-span/path-ref (porque o `CLAUDE.md` indexa via code-span), pulando linhas fenced; a reachability (BFS de `CLAUDE.md`) propaga apenas por **hubs** (`tipo:index`, `*INDEX.md`, `*README.md`, `*CLAUDE.md`). O esqueleto de hubs e criado conforme o padrao ja comprovado pelos 3 `INDEX.md` de superpowers (header `tipo:index`, `hub:<self>`, so-ponteiros).

**Tech Stack:** Python 3.12 (stdlib: re, json, collections, pathlib, dataclasses), pytest, git. Reusa o engine `scripts/audits/artefato_lint/`. Sem dependencia externa nova.

## Indice

- [Premissas e anchor](#premissas)
- [Decisoes de escopo (consolidadas)](#decisoes)
- [File Structure (decomposicao)](#file-structure)
- [Fase A — Detector C8 (TDD)](#fase-a): T1 resolve_ref · T2 checks_reach · T3 wiring CLI · T4 testes · T5 baseline-antes
- [Fase B — Esqueleto de hubs](#fase-b): T6 docs/INDEX · T7 superpowers/INDEX · T8 inventario/INDEX · T9 aresta CLAUDE.md · T10 fecha bidir · T11 ssw top-edge · T12 registro+verificacao
- [Divida declarada (defer explicito)](#divida)
- [Self-Review](#self-review)

---

## Premissas e anchor <a id="premissas"></a>

ANTES de iniciar qualquer task, ancorar em verdade (nao confiar nesta doc cega):

```bash
cd /home/rafaelnascimento/projetos/frete_sistema && source .venv/bin/activate
git rev-parse HEAD                 # deve == origin/main; conter merge 93af41d7b alcancavel
python3 -m pytest tests/audits/ -q # DEVE dar 46 passed
```

Se nao bater, re-investigar (NAO assumir). Ground-truth da exploracao em `/tmp/pad_a_reach/` (analyzer + report.json + SCOPE_FACTS.md). Numeros-chave: 706 docs gerenciados, 59 com header, 568 orfaos (modelo realista code-span), 2 violacoes bidir reais (`ARQUITETURA_DE_ARTEFATOS.md` e `GLOSSARIO.md` declaram `hub: .claude/references/INDEX.md` que nao os lista de volta), `CLAUDE.md -> docs/` = 0 arestas.

## Decisoes de escopo (consolidadas) <a id="decisoes"></a>

Validadas pela exploracao (workflow `wf_c98ae76d`, 6 agentes) + critica adversarial. **Onda 1 = SO navegabilidade**; NAO migrar headers, NAO mover/renomear arquivos, NAO converter o formato code-span do `CLAUDE.md`.

1. **Modelo de aresta C8 = link + code-span** (skip fenced). So markdown-link da `reached=1` (inutil ate `CLAUDE.md` ser convertido); code-span+link da `reached=138/orfaos=568` (util e acionavel).
2. **Propagacao do BFS = so por hubs** = `tipo:index` OU basename em `{INDEX.md, README.md, CLAUDE.md}`. Um doc de conteudo alcancado NAO propaga (evita "salvar" vizinho por mencao lateral). Inclui `README.md` (convencao de indice de-facto neste projeto) e `CLAUDE.md` de modulo (MOCs ricos) — senao C8 falsamente acusa orfandade de docs navegaveis por eles.
3. **Hubs NOVOS declaram `hub: <self>`** (padrao dos 3 superpowers) — NUNCA `hub: docs/INDEX.md` (criaria novas obrigacoes bidir). Index e topo de cadeia; quem aponta pra ele sao os filhos de conteudo (Onda 3-4). A aresta mestre->area-hub e por **link no corpo** (alimenta BFS), nao pelo campo `hub:`.
4. **NAO promover `docs/industrializacao-fb-lf/README.md` a `tipo:index`** (dispararia HUB-check de prosa>3 sobre corpo narrativo). Linka-lo do mestre por ponteiro de corpo; BFS nao exige header no alvo.
5. **C8 severidade = `report`** (advisory, espelha D1/`check_glossario`). `exit_code` so conta `block`, entao os 568 orfaos NAO travam commit. Promocao a `block` = pos Onda 3-4 + OK do Rafael.
6. **C8 so roda com grafo COMPLETO** (`--report-only`/`--strict`); SKIPADO sob scope parcial (`--enforce-*`/`--path`) — senao grafo incompleto = falsos orfaos.
7. **`.claude/skills/**` = reachable-by-tool** (descobertas pelo Skill tool via YAML, nao por hub). Classificadas via `tool_reachable_globs` no config — saem da contagem de orfaos (eram 77 = 13.6%).
8. **ssw entra so com aresta de topo** (tag `tipo:index` + 2 links no `ssw/INDEX.md`). Wiring filho-a-filho dos ~85 backticks de `comercial/`+`operacional/` = Onda 3-4.

## File Structure (decomposicao) <a id="file-structure"></a>

```
# Fase A — detector C8 (engine)
scripts/audits/artefato_lint/text_utils.py    # MODIFICAR: + resolve_ref(file_path, target, root) compartilhado
scripts/audits/artefato_lint/checks_struct.py # MODIFICAR: C7 passa a usar resolve_ref (zero mudanca de comportamento)
scripts/audits/artefato_lint/checks_reach.py  # CRIAR: check global C8 (espelha checks_dup)
scripts/audits/doc_audit.py                   # MODIFICAR: le text 1x no loop, acumula reach_docs, flag --skip-reach, chama C8
scripts/audits/artefato_lint.config.json      # MODIFICAR: + reach_roots, + tool_reachable_globs
tests/audits/test_artefato_checks_reach.py    # CRIAR: TDD (fixtures inline, espelha test_artefato_checks_dup)

# Fase B — esqueleto de hubs (navegabilidade)
docs/INDEX.md                                 # CRIAR: hub-mestre de docs/ (tipo:index, hub:self)
docs/superpowers/INDEX.md                     # CRIAR: liga plans/specs/reports ja-tagged
docs/inventario-2026-05/INDEX.md              # CRIAR: liga 8 docs-estado da raiz + subdir READMEs
CLAUDE.md                                      # MODIFICAR: +1 linha code-span -> docs/INDEX.md
.claude/references/INDEX.md                    # MODIFICAR: +2 linhas (ARQUITETURA + GLOSSARIO) — fecha bidir
.claude/references/ssw/INDEX.md                # MODIFICAR: + doc:meta tipo:index + 2 links (comercial/operacional)
docs/superpowers/plans/INDEX.md                # MODIFICAR: + ponteiro para este plano (item-9)
```

---

## Fase A — Detector C8 (TDD) <a id="fase-a"></a>

### Task 1: Extrair `resolve_ref` compartilhado (anti-drift C7/C8)

**Files:**
- Modify: `scripts/audits/artefato_lint/text_utils.py`
- Modify: `scripts/audits/artefato_lint/checks_struct.py:58-77` (C7 usa o helper)
- Test: `tests/audits/test_artefato_checks_struct.py` (suite C7 ja existente DEVE continuar verde)

- [ ] **Step 1: Adicionar `resolve_ref` em `text_utils.py`** (copia FIEL da regra C7; retorna caminho absoluto resolvido ou `None`):

```python
from pathlib import Path

def resolve_ref(file_path: Path, target: str, root: Path) -> Path | None:
    """Resolve um link/ref markdown -> caminho absoluto, ou None se externo/vazio.
    Regra IDENTICA a C7 (checks_struct): './' '../' ou sem '/' = relativo ao dir do
    arquivo; senao root-relative. Fragmentos (#...) sao removidos."""
    t = target.split("#")[0].strip()
    if not t or t.startswith(("http://", "https://", "mailto:")):
        return None
    if t.startswith("./") or t.startswith("../") or "/" not in t:
        return (file_path.parent / t).resolve()
    return (root / t).resolve()
```

- [ ] **Step 2: C7 em `checks_struct.py` passa a usar `resolve_ref`.** Substituir o bloco inline (linhas ~70-75) por:

```python
from .text_utils import fenced_lines, resolve_ref
# ... dentro do loop C7, no lugar do if/else de resolucao:
            cand = resolve_ref(Path(path), target, Path(root))
            if cand is None:
                continue
            if not cand.exists():
                out.append(Finding("C7", rel, i, f"link morto: {t}", "block"))
```

> Atencao: preservar o `t = target.split("#")[0].strip()` que ja existe para a mensagem `link morto: {t}`. `resolve_ref` faz o mesmo split internamente; manter o `t` local so para a mensagem.

- [ ] **Step 3: Rodar a suite C7 (zero regressao)**

Run: `python3 -m pytest tests/audits/test_artefato_checks_struct.py -q`
Expected: PASS (mesmos testes de antes; comportamento C7 inalterado).

- [ ] **Step 4: Rodar a suite inteira**

Run: `python3 -m pytest tests/audits/ -q`
Expected: `46 passed`.

- [ ] **Step 5: Commit**

```bash
git add scripts/audits/artefato_lint/text_utils.py scripts/audits/artefato_lint/checks_struct.py
git commit -m "refactor(pad-a): extrai resolve_ref compartilhado C7/C8 (Onda 1 T1)"
```

### Task 2: Modulo `checks_reach.py` (C8) — TDD

**Files:**
- Create: `scripts/audits/artefato_lint/checks_reach.py`
- Test: `tests/audits/test_artefato_checks_reach.py` (Task 4 escreve a suite; aqui a impl)

> Ordem TDD: escrever o esqueleto da impl com assinatura, depois Task 4 traz os testes; mas como os casos sao conhecidos, esta task entrega a impl COMPLETA e a Task 4 a cobre. (Se preferir TDD estrito, intercalar: cada teste da Task 4 antes do bloco correspondente aqui.)

- [ ] **Step 1: Criar `checks_reach.py`** com a impl completa (portada do prototipo `/tmp/pad_a_reach/analyze_hubs.py`, com saida `Finding`):

```python
from __future__ import annotations
import re
from collections import deque
from pathlib import Path
from .findings import Finding
from .text_utils import fenced_lines, resolve_ref

MD_LINK = re.compile(r"\[[^\]]*\]\(([^)]+)\)")
PATH_REF = re.compile(r"`?([\w./-]+\.md)`?")  # code-span ou path nu -> .md

def _is_hub(rel: str, tipo: str) -> bool:
    """Nos que PROPAGAM reachability: index declarado OU MOC de-facto por nome."""
    return tipo == "index" or Path(rel).name in ("INDEX.md", "README.md", "CLAUDE.md")

def _is_tool_reachable(rel: str, cfg) -> bool:
    from . import zones
    globs = cfg.raw.get("tool_reachable_globs", [])
    return zones._match_any(rel, globs)

def extract_refs(text: str, file_path: Path, root: Path, managed: set[str]) -> set[str]:
    """Refs de saida -> rel-paths gerenciados. Credita markdown-link E code-span/path,
    pulando linhas fenced (exemplos de codigo nao sao arestas reais)."""
    out: set[str] = set()
    fenced = fenced_lines(text)
    for i, line in enumerate(text.splitlines(), 1):
        if i in fenced:
            continue
        for target in MD_LINK.findall(line):
            cand = resolve_ref(file_path, target, root)
            if cand is not None:
                _add(out, cand, root, managed)
        for target in PATH_REF.findall(line):
            cand = resolve_ref(file_path, target, root)
            if cand is not None:
                _add(out, cand, root, managed)
    return out

def _add(out: set[str], cand: Path, root: Path, managed: set[str]) -> None:
    try:
        rel = str(cand.relative_to(root))
    except ValueError:
        return
    if rel in managed:
        out.add(rel)

def check_reachability(docs: dict[str, dict], cfg, root: Path) -> list[Finding]:
    """C8 global (advisory). docs: rel -> {'tipo': str, 'hub': str|None, 'text': str}.
    Emite C8-ORPHAN (nao alcancavel de CLAUDE.md via hubs), C8-BIDIR (item-9: doc
    declara hub que nao o lista de volta), C8-HUBFILE (hub declarado inexistente).
    Severidade 'report': mede a divida, nao trava commit. Promover a 'block' SO apos
    Ondas 3-4 reduzirem a divida + OK do usuario (spec §8.5)."""
    root = Path(root)
    managed = set(docs.keys())
    refs = {rel: extract_refs(d["text"], root / rel, root, managed) for rel, d in docs.items()}
    hubs = {rel for rel, d in docs.items() if _is_hub(rel, d.get("tipo", ""))}
    roots = {"CLAUDE.md"} & managed

    # BFS: a fronteira expande SO por hubs + roots
    reached: set[str] = set()
    q = deque(roots)
    while q:
        cur = q.popleft()
        if cur in reached:
            continue
        reached.add(cur)
        if cur in hubs or cur in roots:
            for nxt in refs.get(cur, ()):
                if nxt not in reached:
                    q.append(nxt)

    out: list[Finding] = []
    for rel, d in sorted(docs.items()):
        if rel in roots:
            continue
        if _is_tool_reachable(rel, cfg):
            continue  # reachable-by-tool (skills): fora do grafo de hubs por design
        # C8-ORPHAN
        if rel not in reached:
            out.append(Finding("C8", rel, 1, "orfao: nao alcancavel de CLAUDE.md via hubs", "report"))
        # C8-BIDIR / C8-HUBFILE (item-9) — so para docs que DECLARAM hub
        h = d.get("hub")
        if h and h not in ("—", "-") and rel not in hubs:
            if h not in managed:
                out.append(Finding("C8", rel, 1, f"hub declarado inexistente/nao-gerenciado: {h}", "report"))
            elif rel not in refs.get(h, set()):
                out.append(Finding("C8", rel, 1, f"hub {h} nao lista este doc de volta (item-9)", "report"))
    return out
```

- [ ] **Step 2: Smoke manual** (sem CLI ainda):

```bash
python3 -c "
import sys; sys.path.insert(0,'.')
from scripts.audits.artefato_lint import checks_reach, config
from pathlib import Path
docs={'CLAUDE.md':{'tipo':'','hub':None,'text':'ver \`docs/INDEX.md\`'},
      'docs/INDEX.md':{'tipo':'index','hub':'docs/INDEX.md','text':'- [a](a.md)'},
      'a.md':{'tipo':'reference','hub':'docs/INDEX.md','text':'x'}}
print([f.message for f in checks_reach.check_reachability(docs, config.load(), Path('.'))])
"
```
Expected: lista vazia para `a.md` orfandade (alcancado via hub); pode acusar `a.md` bidir se `docs/INDEX.md` nao lista `a.md` — neste fixture lista, entao `[]`.

- [ ] **Step 3: Commit** (apos Task 4 verde — ver Task 4 step de commit).

### Task 3: Wiring na CLI `doc_audit.py` + config

**Files:**
- Modify: `scripts/audits/doc_audit.py:14,39,49-64`
- Modify: `scripts/audits/artefato_lint.config.json`

- [ ] **Step 1: Config** — adicionar 2 chaves ao `artefato_lint.config.json`:

```json
  "reach_roots": ["CLAUDE.md"],
  "tool_reachable_globs": [".claude/skills/**/*.md"],
```

(inserir antes de `"id_hardcoded_regex"`; cuidar da virgula JSON.)

- [ ] **Step 2: Import** — `doc_audit.py:14` adicionar `checks_reach`:

```python
from scripts.audits.artefato_lint import checks_struct, checks_content, checks_dup, checks_reach
```

- [ ] **Step 3: Flag** — junto da `--skip-dup` (linha ~39):

```python
    ap.add_argument("--skip-reach", action="store_true", help="pula alcancabilidade C8 (global) — auto-skip sob scope parcial")
```

- [ ] **Step 4: Loop le `text` 1x + acumula `reach_docs`.** Substituir o corpo do `for p in iter_docs(...)` (linhas ~52-55) por:

```python
        reach_docs = {}
        for p in iter_docs(ROOT, cfg, scope, args.path):
            rel = str(p.relative_to(ROOT))
            text = p.read_text(encoding="utf-8")
            all_findings += checks_struct.check_file(p, ROOT, cfg)
            all_findings += checks_content.check_file(p, ROOT, cfg)
            blocks[rel] = checks_content._body(text)
            m = meta_mod.parse_doc(text)
            reach_docs[rel] = {"tipo": m.fields.get("tipo", ""),
                               "hub": (m.fields.get("hub") or "").strip() or None,
                               "text": text}
```

E adicionar o import de meta no topo: `from scripts.audits.artefato_lint import ... meta as meta_mod` (ja existe `meta` no engine; importar em `doc_audit.py`).

- [ ] **Step 5: Chamar C8 apos o loop** (logo apos o bloco `--skip-dup`, linha ~57). C8 so roda com grafo COMPLETO:

```python
        partial = (scope is not None) or bool(args.path)
        if not args.skip_reach and not partial:
            all_findings += checks_reach.check_reachability(reach_docs, cfg, ROOT)
```

- [ ] **Step 6: Verificar que a CLI roda** (baseline ainda nao avaliado, so nao quebra):

Run: `python3 scripts/audits/doc_audit.py --report-only --skip-dup | tail -5`
Expected: roda sem erro (exit 0); aparecem achados `C8 report` no output.

- [ ] **Step 7: Commit** (apos Task 4 verde).

### Task 4: Suite TDD `test_artefato_checks_reach.py`

**Files:**
- Create: `tests/audits/test_artefato_checks_reach.py` (fixtures inline, espelha `test_artefato_checks_dup.py`)

- [ ] **Step 1: Escrever os 8 casos:**

```python
from pathlib import Path
from scripts.audits.artefato_lint import checks_reach, config

CFG = config.load()
ROOT = Path(".")

def _run(docs):
    return checks_reach.check_reachability(docs, CFG, ROOT)

def _codes(fs, sub):
    return [f for f in fs if f.code == "C8" and sub in f.message]

def test_hub_lista_filho_reachable():
    docs = {"CLAUDE.md": {"tipo": "", "hub": None, "text": "`docs/INDEX.md`"},
            "docs/INDEX.md": {"tipo": "index", "hub": "docs/INDEX.md", "text": "- [a](a.md)"},
            "a.md": {"tipo": "reference", "hub": "docs/INDEX.md", "text": "x"}}
    fs = _run(docs)
    assert not [f for f in fs if f.path == "a.md" and "orfao" in f.message]

def test_doc_sem_hub_orfao():
    docs = {"CLAUDE.md": {"tipo": "", "hub": None, "text": "nada"},
            "b.md": {"tipo": "reference", "hub": None, "text": "x"}}
    fs = _run(docs)
    assert any(f.path == "b.md" and "orfao" in f.message and f.severity == "report" for f in fs)

def test_bidir_doc_declara_hub_mas_hub_nao_lista():
    docs = {"CLAUDE.md": {"tipo": "", "hub": None, "text": "`I.md`"},
            "I.md": {"tipo": "index", "hub": "I.md", "text": "sem ponteiros"},
            "a.md": {"tipo": "reference", "hub": "I.md", "text": "x"}}
    fs = _run(docs)
    assert _codes(fs, "item-9")  # I.md nao lista a.md

def test_codespan_credita_aresta():
    # hub referencia filho SO por code-span (path nu), nao [txt](path)
    docs = {"CLAUDE.md": {"tipo": "", "hub": None, "text": "`H.md`"},
            "H.md": {"tipo": "index", "hub": "H.md", "text": "ponteiro `c.md` aqui"},
            "c.md": {"tipo": "reference", "hub": "H.md", "text": "x"}}
    fs = _run(docs)
    assert not [f for f in fs if f.path == "c.md" and "orfao" in f.message]

def test_link_only_nao_propaga_por_doc_conteudo():
    # X (conteudo) e alcancado e menciona Y, mas nenhum hub menciona Y -> Y orfao
    docs = {"CLAUDE.md": {"tipo": "", "hub": None, "text": "`H.md`"},
            "H.md": {"tipo": "index", "hub": "H.md", "text": "- [x](X.md)"},
            "X.md": {"tipo": "reference", "hub": "H.md", "text": "- [y](Y.md)"},
            "Y.md": {"tipo": "reference", "hub": None, "text": "z"}}
    fs = _run(docs)
    assert any(f.path == "Y.md" and "orfao" in f.message for f in fs)

def test_claude_md_modulo_propaga():
    docs = {"CLAUDE.md": {"tipo": "", "hub": None, "text": "`app/x/CLAUDE.md`"},
            "app/x/CLAUDE.md": {"tipo": "", "hub": None, "text": "- [r](ROADMAP.md)"},
            "app/x/ROADMAP.md": {"tipo": "reference", "hub": None, "text": "x"}}
    fs = _run(docs)
    assert not [f for f in fs if f.path == "app/x/ROADMAP.md" and "orfao" in f.message]

def test_severidade_report_nao_altera_exit():
    from scripts.audits.artefato_lint import findings
    docs = {"CLAUDE.md": {"tipo": "", "hub": None, "text": "nada"},
            "o.md": {"tipo": "reference", "hub": None, "text": "x"}}
    fs = _run(docs)
    assert fs and findings.exit_code(fs) == 0

def test_hub_missing_file():
    docs = {"CLAUDE.md": {"tipo": "", "hub": None, "text": "`a.md`"},
            "a.md": {"tipo": "reference", "hub": "naoexiste/INDEX.md", "text": "x"}}
    fs = _run(docs)
    assert _codes(fs, "inexistente")
```

- [ ] **Step 2: Rodar a nova suite**

Run: `python3 -m pytest tests/audits/test_artefato_checks_reach.py -v`
Expected: `8 passed`.

- [ ] **Step 3: Rodar a suite inteira**

Run: `python3 -m pytest tests/audits/ -q`
Expected: `54 passed` (46 + 8).

- [ ] **Step 4: Commit Fase A**

```bash
git add scripts/audits/artefato_lint/checks_reach.py scripts/audits/doc_audit.py \
        scripts/audits/artefato_lint.config.json tests/audits/test_artefato_checks_reach.py
git commit -m "feat(pad-a): check C8 alcancabilidade/bidir (advisory) — Onda 1 Fase A"
```

### Task 5: Baseline-ANTES do C8 (metrica de divida)

**Files:** nenhum (so medicao).

- [ ] **Step 1: Capturar contagem de orfaos/bidir ANTES dos hubs**

Run:
```bash
python3 scripts/audits/doc_audit.py --report-only --skip-dup 2>/dev/null | grep -c "^C8.*orfao"
python3 scripts/audits/doc_audit.py --report-only --skip-dup 2>/dev/null | grep -c "item-9"
```
Expected: registrar os 2 numeros (orfaos-antes, bidir-antes=2). Guardar para comparar na Task 12.

---

## Fase B — Esqueleto de hubs <a id="fase-b"></a>

> Cada hub NOVO nasce via scaffold OU header manual `tipo:index`/`hub:<self>` e DEVE passar `python3 scripts/audits/doc_audit.py --enforce-touched` (gate Anel 1 valida o Write; Anel 2 valida no commit). So-ponteiros: prosa contigua >3 linhas = falha HUB.

### Task 6: `docs/INDEX.md` — hub-mestre de `docs/`

**Files:**
- Create: `docs/INDEX.md`

- [ ] **Step 1: Gerar o esqueleto conforme** (scaffold OU escrever direto). Header + corpo so-ponteiros listando as entradas top-level de `docs/` (agrupadas por area) e os sub-hubs:

```markdown
<!-- doc:meta
tipo: index
camada: L1
sot_de: —
hub: docs/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# docs/ — indice mestre
> **Papel:** ponto de entrada da documentacao tecnica do projeto (`docs/`). So ponteiros.

## Padrao e processo (PAD-A)
- [Planos de implementacao](superpowers/plans/INDEX.md) — ondas do PAD-A e outros planos
- [Specs / design](superpowers/specs/INDEX.md) — desenhos aprovados
- [Reports / baselines](superpowers/reports/INDEX.md) — inventarios e medicoes
- [Indice de superpowers](superpowers/INDEX.md) — hub das 3 categorias acima

## Operacoes Odoo / estoque
- [Inventario 2026-05](inventario-2026-05/INDEX.md) — ciclo de inventario NACOM/LF/CD/FB
- [Industrializacao FB-LF](industrializacao-fb-lf/README.md) — remessa industrializacao (indice no README)

## Agente
- [Blueprint do agente](blueprint-agente/BLUEPRINT_MESTRE.md) — eixos A-F + criticas

## Outros
- [Pallet](pallet/MAPEAMENTO_TELAS.md) — telas e ajustes do modulo pallet
- [Lojas HORA](hora/INVARIANTES.md) — invariantes + checklist go-live
- [Importador de pedidos redes (Sendas/Tenda)](planos/PLANO_IMPORTADOR_PEDIDOS_REDES.md) — cluster Sendas
```

> NOTA execucao: completar com TODOS os top-level reais de `docs/` (conferir `find docs -maxdepth 1`). Os 13 .md soltos da raiz de `docs/` podem entrar como ponteiros diretos numa secao "Avulsos" OU agrupados (cluster Sendas aponta os 6 docs Sendas). NAO mover arquivos. Manter cada linha como ponteiro (sem paragrafo de prosa >3 linhas).

- [ ] **Step 2: Validar conformidade**

Run: `python3 scripts/audits/doc_audit.py --enforce-touched --skip-dup 2>/dev/null | grep "docs/INDEX.md"`
Expected: nenhum achado `block` para `docs/INDEX.md` (C1/C3/C5/HUB ok). C8 `report` de orfandade do PROPRIO docs/INDEX.md so some apos a Task 9 (aresta no CLAUDE.md).

### Task 7: `docs/superpowers/INDEX.md` — liga os 3 sub-hubs

**Files:**
- Create: `docs/superpowers/INDEX.md`

- [ ] **Step 1: Criar** (so-ponteiros aos 3 INDEX ja-tagged):

```markdown
<!-- doc:meta
tipo: index
camada: L1
sot_de: —
hub: docs/superpowers/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# superpowers — indice
> **Papel:** hub das categorias de artefatos do fluxo superpowers. So ponteiros.

- [Plans](plans/INDEX.md) — planos de implementacao por onda
- [Specs](specs/INDEX.md) — desenhos/design aprovados
- [Reports](reports/INDEX.md) — baselines e inventarios
```

- [ ] **Step 2: Validar** — `python3 scripts/audits/doc_audit.py --enforce-touched --skip-dup 2>/dev/null | grep "superpowers/INDEX.md"` → sem `block`.

### Task 8: `docs/inventario-2026-05/INDEX.md` — maior subtree (88 docs)

**Files:**
- Create: `docs/inventario-2026-05/INDEX.md`

- [ ] **Step 1: Criar** so-ponteiros listando os 8 docs-estado da raiz + as subpastas (apontando os READMEs existentes onde houver):

```markdown
<!-- doc:meta
tipo: index
camada: L1
sot_de: —
hub: docs/inventario-2026-05/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Inventario 2026-05 — indice
> **Papel:** mapa do ciclo de inventario 2026-05 (NACOM/LF/CD/FB). So ponteiros.

## Estado
- [SOT](SOT.md) — fonte da verdade do ciclo
- [Pendencias](PENDENCIAS.md)
- [Pickings pendentes](PICKINGS_PENDENTES.md)

## Por categoria
- [Decisoes](00-decisoes/) — D0xx
- [Premissas](01-premissas/)
- [Gotchas](02-gotchas/) — Gxxx
- [Execucoes](08-execucoes/README.md)
- [Historia](99-historia/README.md)
- [Consolidacao](consolidacao/)
```

> NOTA: conferir nomes reais via `find docs/inventario-2026-05 -maxdepth 1`. Subdirs sem README (00-decisoes, 02-gotchas) ficam como ponteiro-de-diretorio na Onda 1; suas folhas individuais sao alcancadas via sub-READMEs na Onda 3-4 (divida declarada). Ponteiros de diretorio (`00-decisoes/`) sao linhas-ponteiro validas (nao prosa).

- [ ] **Step 2: Validar** — sem `block` para `inventario-2026-05/INDEX.md`.

### Task 9: Aresta `CLAUDE.md -> docs/` (a mais alavancada)

**Files:**
- Modify: `CLAUDE.md` (sub-tabela "Infraestrutura e Agente" do INDICE DE REFERENCIAS, apos a linha `Indice completo | .claude/references/INDEX.md`)

- [ ] **Step 1: Inserir 1 linha** no MESMO formato code-span da tabela:

```markdown
| Documentacao tecnica (docs/) | `docs/INDEX.md` |
```

> Sem esta linha, `docs/INDEX.md` nasce orfao (modelo code-span). Edicao inseparavel da Task 6. NAO converter o resto da tabela para markdown-link (fora de escopo).

- [ ] **Step 2: Verificar a aresta** — re-rodar o baseline C8:

Run: `python3 scripts/audits/doc_audit.py --report-only --skip-dup 2>/dev/null | grep -c "^C8.*orfao"`
Expected: contagem de orfaos MENOR que a da Task 5 (docs/ agora alcancavel a cascata via hubs criados).

### Task 10: Fechar as 2 violacoes bidir (`references/INDEX.md`)

**Files:**
- Modify: `.claude/references/INDEX.md` (secao "Consulta Rapida")

- [ ] **Step 1: Adicionar 2 linhas** em markdown-link relativo (formato dos vizinhos intra-tree):

```markdown
| **Arquitetura de Artefatos (padrao PAD-A)** | [ARQUITETURA_DE_ARTEFATOS.md](ARQUITETURA_DE_ARTEFATOS.md) |
| **Glossario — terminologia canonica** | [GLOSSARIO.md](GLOSSARIO.md) |
```

> Conferir o formato exato da secao "Consulta Rapida" antes de inserir (pode ser tabela 2-col ou lista). Manter consistente. Isso fecha as 2 unicas `bidir_violations` reais (`ARQUITETURA` + `GLOSSARIO` declaram `hub: .claude/references/INDEX.md`).

- [ ] **Step 2: Verificar bidir fechado**

Run: `python3 scripts/audits/doc_audit.py --report-only --skip-dup 2>/dev/null | grep -c "item-9"`
Expected: `0` (eram 2).

### Task 11: ssw — aresta de topo (tag + 2 links)

**Files:**
- Modify: `.claude/references/ssw/INDEX.md`

- [ ] **Step 1: Adicionar header `doc:meta tipo:index`** no topo do `ssw/INDEX.md` (sem tocar o corpo):

```markdown
<!-- doc:meta
tipo: index
camada: L1
sot_de: —
hub: .claude/references/ssw/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
```

> CUIDADO HUB-check: ao virar `tipo:index`, o corpo do `ssw/INDEX.md` passa a ser auditado por HUB (prosa contigua >3 linhas = falha). Conferir ANTES (`python3 scripts/audits/doc_audit.py --enforce-touched --skip-dup | grep ssw/INDEX`). Se falhar HUB, NAO reescrever o corpo nesta onda — reverter o header e deixar ssw como divida Onda 3-4 (registrar). So tag se passar limpo.

- [ ] **Step 2: Adicionar 2 markdown-links** para os sub-INDEX hoje desconectados (referenciados so como ``comercial/``/``operacional/`` de diretorio):

```markdown
- [Comercial (tabelas de frete)](comercial/INDEX.md)
- [Operacional (cadastros e coletas)](operacional/INDEX.md)
```

- [ ] **Step 3: Validar** — sem `block` novo para `ssw/INDEX.md`.

### Task 12: Registro (item-9) + verificacao de completude

**Files:**
- Modify: `docs/superpowers/plans/INDEX.md` (ponteiro para este plano)

- [ ] **Step 1: Registrar este plano no hub** (`docs/superpowers/plans/INDEX.md`):

```markdown
- [PAD-A Onda 1 — Indice mestre](2026-06-02-pad-a-onda-1-indice-mestre.md) — hubs + ligar docs/ ao CLAUDE.md + check C8
```

- [ ] **Step 2: Baseline-DEPOIS + delta** (Rule 7 completude, numeros exatos):

```bash
python3 scripts/audits/doc_audit.py --report-only --skip-dup 2>/dev/null | grep -c "^C8.*orfao"  # orfaos-depois
python3 scripts/audits/doc_audit.py --report-only --skip-dup 2>/dev/null | grep -c "item-9"        # bidir-depois (esperado 0)
```
Expected: orfaos-depois < orfaos-antes (Task 5); bidir-depois = 0.

- [ ] **Step 3: Suite verde + hubs conformes**

Run: `python3 -m pytest tests/audits/ -q`
Expected: `54 passed`.

Run: `python3 scripts/audits/doc_audit.py --enforce-touched --skip-dup 2>/dev/null | grep -E "block" | grep -E "docs/INDEX|superpowers/INDEX|inventario-2026-05/INDEX|ssw/INDEX"`
Expected: vazio (nenhum hub novo bloqueia).

- [ ] **Step 4: Commit Fase B**

```bash
git add docs/INDEX.md docs/superpowers/INDEX.md docs/inventario-2026-05/INDEX.md \
        CLAUDE.md .claude/references/INDEX.md .claude/references/ssw/INDEX.md \
        docs/superpowers/plans/INDEX.md docs/superpowers/plans/2026-06-02-pad-a-onda-1-indice-mestre.md
git commit -m "feat(pad-a): esqueleto de hubs + aresta docs/->CLAUDE.md + fecha bidir (Onda 1 Fase B)"
```

- [ ] **Step 5: Merge para main** — SO com OK explicito do Rafael (preferencia: nao push sem pedido; usar `[skip render]` se for so doc).

---

## Divida declarada (defer explicito) <a id="divida"></a>

NAO sao silencio — ficam escritos como divida consciente:

1. **645/693 headers `doc:meta` ausentes** -> Onda 3-4 (migracao em massa). C8 os reporta (`report`), mede mas nao paga.
2. **~85 folhas ssw em `comercial/`+`operacional/`** (backtick-sem-path nos sub-INDEX) -> Onda 3-4. Onda 1 so religa os 2 sub-INDEX ao topo.
3. **8 subdirs ssw sem INDEX** (financeiro/cadastros/contabilidade/edi/embarcador/fiscal/logistica/relatorios) -> Onda 3-4.
4. **77 arquivos `.claude/skills/**`** -> reachable-by-tool por design (classificados via `tool_reachable_globs`). NAO sao orfaos reais.
5. **Promocao C8 `report`->`block`** -> pos Onda 3-4 + OK Rafael (§8.5). Comentario-gate codificado no modulo.
6. **`CLAUDE.md` so usa code-span** -> Onda 1 NAO converte o formato. C8 obriga-se a creditar code-span (teste `test_codespan_credita_aresta` nao-negociavel).
7. **`docs/industrializacao-fb-lf/README.md` sem header** -> ligado por ponteiro de corpo no mestre; header fica p/ Onda 3-4.
8. **`app/*/CLAUDE.md` formalizados como `tipo:index`** -> Onda 3-4 (hoje propagam no C8 por nome, sem header formal).
9. **Defeito no `2026-06-02-pad-a-baseline.md`** (§Pendencias numera "Onda 1 = C1 headers", diverge do spec §8) -> corrigir na Onda 2 (conflitos) OU edicao pontual; registrar.

## Self-Review <a id="self-review"></a>

- **Cobertura spec §8 Onda 1:** "hubs faltantes (docs/INDEX.md, raiz, .claude raiz, scripts/)" -> docs/INDEX.md (T6) ✓; "raiz/.claude raiz/scripts" cobrem arquivos FORA da zona gerenciada (config: so docs/**, .claude/references/**, .claude/skills/**, app/*/CLAUDE.md, CLAUDE.md) -> nucleo in-zone = docs/ entregue; raiz/.claude/scripts = expansao de zona, DECISAO p/ Rafael (default: defer, fora da zona enforced). "ligar docs/ ao CLAUDE.md" -> T9 ✓. "check de alcancabilidade" -> C8 Fase A ✓.
- **Item-9 (spec §5/§5.1):** implementado como C8-BIDIR (pre-commit, mas `report` na Onda 1; promocao a `block` declarada como divida). As 2 violacoes reais fecham em T10. ✓
- **Placeholder scan:** impl de `checks_reach.py` completa (T2); testes completos (T4); conteudo dos hubs com header completo + nota de "completar top-level reais" (deterministico via `find`). Sem TODO/TBD.
- **Type consistency:** `check_reachability(docs, cfg, root)`, `extract_refs(text, file_path, root, managed)`, `resolve_ref(file_path, target, root)`, `_is_hub(rel, tipo)` — assinaturas consistentes entre T1/T2/T3/T4.
- **Regras §8.5:** so a lista de arquivos do File Structure; sem refatorar fora de escopo (resolve_ref e refator MINIMO necessario p/ anti-drift); parametrizar>criar (reach_roots/tool_reachable_globs no config); completude antes de fechar (T5 antes vs T12 depois com numeros).
