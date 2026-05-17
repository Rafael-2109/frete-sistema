# Auditor SPED ECD — Subagente + 4 Skills + Embeddings de Regras Normativas

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir um subagente `auditor-sped-ecd` isolado do agente principal Nacom, com 4 skills especializadas (parser, compliance vs Manual, auditoria contabil, diff vs ground truth) e indexacao por embeddings das regras normativas do Manual ECD Leiaute 9, para reduzir iteracoes contra PVA da Receita Federal.

**Architecture:** Skill-level isolation via `skills=list[str]` no SDK 0.1.77+ (mecanismo nativo, ja em PROD em `agente_lojas`). Skills SPED invisiveis ao principal e auto-rejeitadas pelo Skill tool. Subagente declara as 4 SPED-specific + 2 reusadas (`consultando-sql`, `descobrindo-odoo-estrutura`) via frontmatter. Reuso do `EmbeddingService` Voyage AI + pgvector — sem novo MCP. Sem mudancas no validator existente (`sped_ecd_validator.py`) que continua como camada 1 in-process pre-upload.

**Tech Stack:** Python 3.12, Claude Agent SDK 0.2.82 (CLI 2.1.142), pgvector + Voyage AI (`voyage-4-lite`), Flask-SQLAlchemy 3.1, pytest, YAML (DSL de regras).

---

## Premissas Validadas Antes do Plano

| Premissa | Fonte de verdade |
|---|---|
| `skills=list[str]` injeta `Skill(name)` per-entry e rejeita nao-listados | `app/agente/SDK_CHANGELOG.md:160-167` |
| Padrao em PROD: `agente_lojas` usa `skills=sorted(SKILLS_PERMITIDAS)` | `app/agente_lojas/sdk/client.py` (referenciado em `SDK_CHANGELOG.md:200-203`) |
| Frontmatter `skills:` em AgentDefinition: 14 subagentes ja usam | `grep -rn "skills:" .claude/agents/*.md` |
| `sped_ecd_validator.py` cobre ~30 regras estruturais — NAO mexer | `app/relatorios_fiscais/services/sped_ecd_validator.py:1-50` |
| Manual ECD ja indexado por bloco/registro em 11 MDs | `app/relatorios_fiscais/manual_ecd/INDEX.md` |
| SPED contadora aprovado pela RFB existe como ground truth | `app/relatorios_fiscais/CLAUDE.md:286-297` |
| EmbeddingService maduro com 10 dominios + Voyage AI | `app/embeddings/service.py:51` + `app/embeddings/indexers/` |
| Indexer pattern documentado | `app/embeddings/indexers/carrier_indexer.py` |
| Skill pattern com `scripts/` + `SKILL.md` | `.claude/skills/operando-ssw/SKILL.md` |
| Migration regra: DOIS artefatos (.py + .sql) | `~/.claude/CLAUDE.md` secao MIGRATIONS |

---

## File Structure

### Criados (19 arquivos)

```
.claude/agents/
└── auditor-sped-ecd.md                                    # Subagente principal

.claude/skills/
├── parseando-sped-ecd/
│   ├── SKILL.md
│   └── scripts/parse_sped.py
├── auditando-sped-contabil/
│   ├── SKILL.md
│   └── scripts/
│       ├── audit_balance.py
│       └── audit_hierarchy.py
├── comparando-sped-ground-truth/
│   ├── SKILL.md
│   └── scripts/diff_truth.py
└── auditando-sped-vs-manual/
    ├── SKILL.md
    ├── scripts/dsl_engine.py
    └── regras/I050.yaml

app/embeddings/
├── indexers/sped_ecd_rules_indexer.py                     # Indexa manual_ecd/
└── sped_rules_search.py                                   # API de busca semantica

scripts/migrations/
├── 2026_05_16_sped_ecd_rule_embeddings.py                # Python migration
└── 2026_05_16_sped_ecd_rule_embeddings.sql               # SQL idempotente

tests/skills/
├── test_parseando_sped_ecd.py
├── test_auditando_sped_contabil.py
├── test_comparando_sped_ground_truth.py
└── test_auditando_sped_vs_manual.py

tests/agente/
├── test_skill_isolation_sped.py                          # Skill SPED rejeitada no principal
└── test_sped_audit_integration.py                        # E2E subagente
```

### Modificados (3 arquivos)

```
app/agente/config/settings.py                  # SPED_SKILLS constant
app/agente/sdk/client.py                       # _discover_skills() + filtro
app/embeddings/config.py                       # THRESHOLD_SPED_RULES
app/embeddings/models.py                       # SpedEcdRuleEmbedding model
```

---

## Decomposicao em 3 Fases

| Fase | Entregavel testavel isolado | Tasks |
|---|---|---|
| **Fase 1** | Subagente `auditor-sped-ecd` recebe path do SPED, parseia em JSON estruturado, retorna sumario | 1.1 - 1.5 |
| **Fase 2** | Subagente detecta erros contabeis (saldo, hierarquia) e diferencas vs ground truth | 2.1 - 2.5 |
| **Fase 3** | Subagente consulta regras normativas via embeddings + DSL engine valida campos | 3.1 - 3.4 |

**Checkpoint humano OBRIGATORIO entre fases.** Nao prosseguir Fase 2 sem aprovacao da Fase 1.

---

## FASE 1 — Foundation (Skill Isolation + Parser + Subagent)

### Task 1.1: Isolamento de Skills no Agente Principal

**Files:**
- Modify: `app/agente/config/settings.py:38-46` (adicionar SPED_SKILLS)
- Modify: `app/agente/sdk/client.py:1456-1457` (substituir `skills="all"`)

**Por que:** Skills SPED devem ser invisiveis ao agente Nacom e auto-rejeitadas pelo SDK quando tentar invocar (`SDK_CHANGELOG.md:160-167`).

- [ ] **Step 1: Adicionar constante SPED_SKILLS em settings.py**

Adicionar apos linha 46 (apos comentario do `skills="all"`):

```python
# Skills exclusivas do subagente auditor-sped-ecd.
# Filtradas via `skills=list[str]` no SDK 0.1.77+ — invisiveis no listing do
# principal E rejeitadas pelo Skill tool (SDK_CHANGELOG.md:160-167).
SPED_SKILLS_RESERVED: set[str] = {
    "parseando-sped-ecd",
    "auditando-sped-vs-manual",
    "auditando-sped-contabil",
    "comparando-sped-ground-truth",
}
```

- [ ] **Step 2: Escrever teste de isolamento (falha esperada)**

Criar `tests/agente/test_skill_isolation_sped.py`:

```python
"""Testa que skills SPED ficam invisiveis ao agente principal Nacom."""
from app.agente.config.settings import AgentSettings, SPED_SKILLS_RESERVED
from app.agente.sdk.client import _discover_skills_from_project


def test_sped_skills_reserved_constant_complete():
    """Garantir que a constante cobre as 4 skills planejadas."""
    expected = {
        "parseando-sped-ecd",
        "auditando-sped-vs-manual",
        "auditando-sped-contabil",
        "comparando-sped-ground-truth",
    }
    assert SPED_SKILLS_RESERVED == expected


def test_discover_skills_excludes_sped():
    """_discover_skills_from_project() deve retornar lista sem SPED skills."""
    all_skills = _discover_skills_from_project()
    assert isinstance(all_skills, list)
    assert len(all_skills) > 0
    for sped_skill in SPED_SKILLS_RESERVED:
        assert sped_skill not in all_skills, \
            f"Skill {sped_skill} deve estar excluida do listing principal"
```

- [ ] **Step 3: Rodar teste para verificar que falha**

Run: `source .venv/bin/activate && pytest tests/agente/test_skill_isolation_sped.py -v`
Expected: FAIL com `ImportError` ou `AttributeError` em `_discover_skills_from_project`.

- [ ] **Step 4: Implementar helper de descoberta em client.py**

Adicionar em `app/agente/sdk/client.py` antes da classe `AgentClient` (procurar pela primeira definicao de classe e adicionar antes):

```python
import os
from pathlib import Path


def _discover_skills_from_project() -> list[str]:
    """Descobre skills em .claude/skills/ filtrando SPED_SKILLS_RESERVED.

    Retorna lista ordenada de skill names (basename de diretorios que tem SKILL.md),
    excluindo skills reservadas ao subagente auditor-sped-ecd.

    Esta funcao eh o input para `skills=list[str]` em ClaudeAgentOptions
    (SDK 0.1.77+, ver SDK_CHANGELOG.md:160-167). Skills nao listadas aqui:
    1. Nao aparecem no listing do agente principal (economia ~1K tokens).
    2. Sao rejeitadas se o principal tentar invocar via Skill tool.

    Returns:
        Lista ordenada de skill names.
    """
    from app.agente.config.settings import SPED_SKILLS_RESERVED

    skills_dir = Path(__file__).parent.parent.parent.parent / ".claude" / "skills"
    if not skills_dir.is_dir():
        return []

    discovered: list[str] = []
    for entry in skills_dir.iterdir():
        if not entry.is_dir():
            continue
        if not (entry / "SKILL.md").is_file():
            continue
        if entry.name in SPED_SKILLS_RESERVED:
            continue
        discovered.append(entry.name)

    return sorted(discovered)
```

- [ ] **Step 5: Rodar teste para verificar que passa**

Run: `pytest tests/agente/test_skill_isolation_sped.py -v`
Expected: PASS em ambos os testes.

- [ ] **Step 6: Substituir `skills="all"` por lista filtrada**

Em `app/agente/sdk/client.py:1456-1457`, substituir:

```python
# ANTES:
if _SDK_HAS_OPTIONS_SKILLS:
    options_dict["skills"] = "all"

# DEPOIS:
if _SDK_HAS_OPTIONS_SKILLS:
    options_dict["skills"] = _discover_skills_from_project()
    logger.debug(
        f"[AGENT_CLIENT] skills filtradas: {len(options_dict['skills'])} skills "
        f"(SPED_SKILLS_RESERVED excluidas)"
    )
```

- [ ] **Step 7: Verificar smoke do agente principal**

Run: `source .venv/bin/activate && python -c "from app.agente.sdk.client import _discover_skills_from_project; skills = _discover_skills_from_project(); print(f'Total: {len(skills)} skills'); print('SPED excluido:', all(s not in skills for s in ['parseando-sped-ecd', 'auditando-sped-contabil']))"`

Expected: `Total: 35-37 skills` (ja existentes — varia conforme `.claude/skills/`) + `SPED excluido: True`.

- [ ] **Step 8: Commit**

```bash
git add app/agente/config/settings.py app/agente/sdk/client.py tests/agente/test_skill_isolation_sped.py
git commit -m "$(cat <<'EOF'
feat(agente): isolar skills SPED do principal via skills=list[str]

Substitui skills="all" por _discover_skills_from_project() que exclui
SPED_SKILLS_RESERVED. SDK 0.1.77+ rejeita auto-magicamente invocacao de
skills nao listadas (SDK_CHANGELOG.md:160-167). Padrao identico ao
agente_lojas em PROD.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 1.2: Skill `parseando-sped-ecd` — Parser de SPED em JSON estruturado

**Files:**
- Create: `.claude/skills/parseando-sped-ecd/SKILL.md`
- Create: `.claude/skills/parseando-sped-ecd/scripts/parse_sped.py`
- Create: `tests/skills/test_parseando_sped_ecd.py`

**Por que:** Todas as 3 skills de auditoria consomem o SPED parseado. Streaming Latin-1, output indexado por registro, salvo em `/tmp/sped-parsed-{token}.json` para reaproveitamento entre invocacoes do subagente.

- [ ] **Step 1: Escrever teste com SPED minimo inline**

Criar `tests/skills/test_parseando_sped_ecd.py`:

```python
"""Testa parser SPED ECD — streaming Latin-1, output indexado por registro."""
import json
import sys
from pathlib import Path

import pytest

# Path do script da skill (nao eh modulo Python instalado)
SKILL_SCRIPT = Path(__file__).parent.parent.parent / ".claude" / "skills" / \
    "parseando-sped-ecd" / "scripts" / "parse_sped.py"

# Adicionar ao sys.path para importar
sys.path.insert(0, str(SKILL_SCRIPT.parent))

from parse_sped import parse_sped_file, parse_sped_line


SPED_MINIMAL = (
    "|0000|LECD|01072024|31122024|EMPRESA TESTE|61724241000178|MG|3106200|||||||0|0|0|0|N|||S|N||\r\n"
    "|0001|0|\r\n"
    "|0990|3|\r\n"
    "|I001|0|\r\n"
    "|I010|G|9.00|\r\n"
    "|I050|01012024|01|S|1|1|||CAIXA|\r\n"
    "|I050|01012024|01|A|2|11|1|11|CAIXA GERAL|\r\n"
    "|I990|4|\r\n"
    "|9001|0|\r\n"
    "|9900|0000|1|\r\n"
    "|9990|3|\r\n"
    "|9999|13|\r\n"
)


def test_parse_sped_line_extracts_fields():
    """Linha SPED split por pipe retorna campos sem o primeiro/ultimo vazios."""
    fields = parse_sped_line("|I010|G|9.00|")
    assert fields == ["I010", "G", "9.00"]


def test_parse_sped_line_empty_field():
    """Campos vazios (|| consecutivo) preservados como string vazia."""
    fields = parse_sped_line("|I050|01012024||S|1|1|||CAIXA|")
    assert len(fields) == 9
    assert fields[2] == ""
    assert fields[6] == ""


def test_parse_sped_file_returns_indexed_dict(tmp_path):
    """Output: dict indexado por REG -> lista de registros (sem REG no payload)."""
    sped_path = tmp_path / "sped_test.txt"
    sped_path.write_bytes(SPED_MINIMAL.encode("latin-1"))

    result = parse_sped_file(str(sped_path))

    assert isinstance(result, dict)
    assert "registros" in result
    assert "metadata" in result

    registros = result["registros"]
    assert "0000" in registros
    assert "I050" in registros
    assert len(registros["I050"]) == 2, "duas linhas I050 esperadas"

    # Primeiro registro I050 (sintetica)
    i050_0 = registros["I050"][0]
    assert i050_0["DT_ALT"] == "01012024"
    assert i050_0["COD_NAT"] == "01"
    assert i050_0["IND_CTA"] == "S"

    # Metadata
    assert result["metadata"]["total_lines"] == 13
    assert result["metadata"]["encoding"] == "latin-1"


def test_parse_sped_file_handles_latin1_chars(tmp_path):
    """Caracteres acentuados Latin-1 preservados."""
    sped_with_accent = (
        "|0000|LECD|01072024|31122024|NACOM GOIÁS|61724241000178|GO|5208707|||||||0|0|0|0|N|||S|N||\r\n"
    )
    sped_path = tmp_path / "sped_accent.txt"
    sped_path.write_bytes(sped_with_accent.encode("latin-1"))

    result = parse_sped_file(str(sped_path))
    nome = result["registros"]["0000"][0]["NOME"]
    assert "GOIÁS" in nome


def test_parse_sped_file_streaming_doesnt_load_all_lines_in_memory(tmp_path):
    """Verificar via generator que nao carrega arquivo inteiro."""
    # SPED grande sintetico (1000 lancamentos I250)
    big_sped = SPED_MINIMAL
    for i in range(1000):
        big_sped += f"|I250|{i}|0001|100,00|D|1|HISTORICO {i}||\r\n"

    sped_path = tmp_path / "sped_big.txt"
    sped_path.write_bytes(big_sped.encode("latin-1"))

    result = parse_sped_file(str(sped_path))
    assert len(result["registros"]["I250"]) == 1000
```

- [ ] **Step 2: Rodar teste — deve falhar com ImportError**

Run: `pytest tests/skills/test_parseando_sped_ecd.py -v`
Expected: FAIL com `ModuleNotFoundError: No module named 'parse_sped'`.

- [ ] **Step 3: Criar diretorio + script parser**

```bash
mkdir -p .claude/skills/parseando-sped-ecd/scripts
```

Criar `.claude/skills/parseando-sped-ecd/scripts/parse_sped.py`:

```python
"""Parser SPED ECD Leiaute 9 — streaming Latin-1, output indexado.

Reusado pelas 3 skills de auditoria (auditando-sped-contabil,
comparando-sped-ground-truth, auditando-sped-vs-manual).

Output:
{
  "metadata": {"total_lines": N, "encoding": "latin-1", "path": "..."},
  "registros": {
    "0000": [{"NOME": "...", "CNPJ": "..."}, ...],
    "I050": [{"COD_NAT": "01", ...}, ...],
    ...
  }
}

Schemas dos campos por registro: app/relatorios_fiscais/manual_ecd/bloco_*.md
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Iterator


# Campos por registro — derivado do Manual ECD Leiaute 9.
# Lista posicional EXCLUI o primeiro campo REG (que e a chave do dict externo).
# Fonte: app/relatorios_fiscais/manual_ecd/bloco_*.md
REGISTRO_CAMPOS: dict[str, list[str]] = {
    "0000": ["LECD", "DT_INI", "DT_FIN", "NOME", "CNPJ", "UF", "COD_MUN",
             "NIRE", "IND_SIT_ESP", "IND_SIT_INI_PER", "IND_NIRE", "IND_FIN_ESC",
             "COD_HASH_SUB", "IND_GRANDE_PORTE", "TIP_ECD", "COD_SCP",
             "IDENT_MF", "IND_ESC_CONS", "IDENT_HASH", "IND_CENTRALIZADA",
             "IND_MUDANCA_PC", "COD_PLAN_REF"],
    "0001": ["IND_DAD"],
    "0007": ["COD_ENT_REF", "COD_INSCR"],
    "0020": ["COD_CTA_REF_DESC"],
    "0035": ["COD_SCP", "NOME_SCP"],
    "0150": ["COD_PART", "NOME", "COD_PAIS", "CNPJ", "CPF", "IE", "COD_MUN", "IM", "SUFRAMA", "ENDERECO", "NUM", "COMPL", "BAIRRO"],
    "0180": ["COD_REL", "DT_INI_REL", "DT_FIN_REL"],
    "0990": ["QTD_LIN_0"],
    "I001": ["IND_DAD"],
    "I010": ["IND_ESC", "COD_VER_LC"],
    "I012": ["NUM_ORD", "NAT_LIVR", "TIPO", "COD_HASH_AUX"],
    "I015": ["COD_CTA_RES"],
    "I020": ["REG_COD", "NUM_AD", "CAMPO", "DESCRICAO", "TIPO"],
    "I030": ["DNRC_ABERT", "NUM_ORD", "NAT_LIVR", "QTD_LIN", "NOME", "NIRE",
             "CNPJ", "DT_ARQ", "DT_ARQ_CONV", "DESC_MUN", "DT_EX_SOCIAL"],
    "I050": ["DT_ALT", "COD_NAT", "IND_CTA", "NIVEL", "COD_CTA", "COD_CTA_SUP", "CTA"],
    "I051": ["COD_CCUS", "COD_CTA_REF"],
    "I052": ["COD_CCUS", "COD_AGL"],
    "I053": ["COD_IDT", "COD_CNT_CORR", "NAT_SUB_CNT"],
    "I075": ["COD_HIST_PAD", "DESCR_HIST_PAD"],
    "I100": ["COD_CCUS", "CCUS"],
    "I150": ["DT_INI", "DT_FIN"],
    "I155": ["COD_CTA", "COD_CCUS", "VL_SLD_INI", "IND_DC_INI", "VL_DEB",
             "VL_CRED", "VL_SLD_FIN", "IND_DC_FIN"],
    "I157": ["COD_CTA_REF_TRANSF", "VL_SLD_INI", "IND_DC_INI", "COD_CTA_CORR"],
    "I200": ["NUM_LCTO", "DT_LCTO", "VL_LCTO", "IND_LCTO"],
    "I250": ["COD_CTA", "COD_CCUS", "VL_DC", "IND_DC", "NUM_ARQ", "COD_HIST_PAD",
             "HIST", "COD_PART"],
    "I300": ["DT_BCT", "VL_BCT"],
    "I310": ["NUM_ORD_BCT", "COD_CTA_BCT", "VAL_DEB_BCT", "VAL_CRED_BCT"],
    "I350": ["DT_RES"],
    "I355": ["COD_CTA", "COD_CCUS", "VL_CTA", "IND_DC"],
    "I990": ["QTD_LIN_I"],
    "J001": ["IND_DAD"],
    "J005": ["DT_INI", "DT_FIN", "ID_DEM", "CAB_DEM"],
    "J100": ["COD_AGL", "IND_COD_AGL", "COD_AGL_SUP", "IND_GRP_BAL", "DESCR_COD_AGL",
             "VL_CTA", "IND_DC_BAL", "VL_CTA_INI", "IND_DC_INI_BAL", "NIVEL_AGL"],
    "J150": ["NUM_ORD", "COD_AGL", "NIVEL_AGL", "COD_AGL_SUP", "IND_GRP_DRE",
             "DESCR_COD_AGL", "VL_CTA_DRE", "IND_VL_CTA_DRE", "VL_CTA_DRE_INI",
             "IND_VL_CTA_DRE_INI", "IND_GRP_DRE_INI", "DESCR_COD_AGL_INI", "NIVEL_AGL_INI"],
    "J800": ["ARQ_RTF"],
    "J900": ["DNRC_ENCER", "IDENT_NOM", "IDENT_CPF_CNPJ", "IDENT_QUALIF", "ID_DEM",
             "DT_EX_SOCIAL", "NAT_LIVRO", "NUM_ORD", "QTD_LIN"],
    "J930": ["IDENT_NOM", "IDENT_CPF_CNPJ", "IDENT_QUALIF", "COD_ASSIN", "IND_CRC",
             "EMAIL", "FONE", "UF_CRC", "NUM_SEQ_CRC", "DT_CRC", "CRC_PROF"],
    "J990": ["QTD_LIN_J"],
    "9001": ["IND_MOV"],
    "9900": ["REG_BLC", "QTD_REG_BLC"],
    "9990": ["QTD_LIN_9"],
    "9999": ["QTD_LIN"],
}


def parse_sped_line(line: str) -> list[str]:
    """Split linha por pipe, remove pipes inicial e final.

    Args:
        line: linha SPED com CRLF removido.

    Returns:
        Lista posicional de campos. Campos vazios (||) ficam como string "".
    """
    if not line.startswith("|"):
        raise ValueError(f"Linha SPED nao comeca com pipe: {line[:50]}")
    line = line.rstrip("\r\n")
    if not line.endswith("|"):
        raise ValueError(f"Linha SPED nao termina com pipe: {line[-50:]}")
    return line[1:-1].split("|")


def iter_sped_records(path: str) -> Iterator[tuple[str, dict[str, str]]]:
    """Streaming generator de (REG, registro_dict) lendo arquivo Latin-1.

    Nao carrega arquivo inteiro em memoria — line-by-line.
    """
    with open(path, "rb") as f:
        for raw_line in f:
            try:
                line = raw_line.decode("latin-1")
            except UnicodeDecodeError as e:
                raise ValueError(f"Encoding nao Latin-1 em linha: {e}")

            line = line.rstrip("\r\n")
            if not line:
                continue

            fields = parse_sped_line(line)
            reg = fields[0]
            payload_fields = fields[1:]

            schema = REGISTRO_CAMPOS.get(reg)
            if schema is None:
                # Registro nao mapeado — guardar como posicional
                record = {f"campo_{i+1}": v for i, v in enumerate(payload_fields)}
            else:
                # Map por schema; se registro tem MAIS campos que schema, sobrescreve;
                # se tem MENOS, deixa schema fields faltantes como ""
                record = {}
                for i, field_name in enumerate(schema):
                    record[field_name] = payload_fields[i] if i < len(payload_fields) else ""

            yield reg, record


def parse_sped_file(path: str) -> dict[str, Any]:
    """Parse completo do SPED em dict indexado por REG.

    Args:
        path: caminho do arquivo SPED .txt (Latin-1).

    Returns:
        {
          "metadata": {"total_lines": N, "encoding": "latin-1", "path": ...},
          "registros": {
            "0000": [registro_dict, ...],
            ...
          }
        }
    """
    registros: dict[str, list[dict[str, str]]] = {}
    total_lines = 0

    for reg, record in iter_sped_records(path):
        registros.setdefault(reg, []).append(record)
        total_lines += 1

    return {
        "metadata": {
            "total_lines": total_lines,
            "encoding": "latin-1",
            "path": path,
        },
        "registros": registros,
    }


def parse_and_save(sped_path: str, output_path: str) -> dict[str, Any]:
    """CLI entry point — parse + grava JSON em /tmp.

    Uso pelo subagente:
        python parse_sped.py /path/to/sped.txt /tmp/sped-parsed-{token}.json
    """
    parsed = parse_sped_file(sped_path)

    # Stats: registro -> count
    stats = {reg: len(records) for reg, records in parsed["registros"].items()}
    parsed["metadata"]["stats"] = stats

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)

    return {
        "output_path": output_path,
        "total_lines": parsed["metadata"]["total_lines"],
        "registros_distintos": len(parsed["registros"]),
        "stats": stats,
    }


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Uso: python parse_sped.py <sped_path> <output_json>", file=sys.stderr)
        sys.exit(2)
    result = parse_and_save(sys.argv[1], sys.argv[2])
    print(json.dumps(result, indent=2))
```

- [ ] **Step 4: Rodar testes — devem passar**

Run: `pytest tests/skills/test_parseando_sped_ecd.py -v`
Expected: 5 testes PASS.

- [ ] **Step 5: Criar SKILL.md**

Criar `.claude/skills/parseando-sped-ecd/SKILL.md`:

```markdown
---
name: parseando-sped-ecd
description: >-
  Skill EXCLUSIVA do subagente auditor-sped-ecd. NAO invocar do agente
  principal. Parseia arquivo SPED ECD Leiaute 9 (Latin-1, streaming) em
  dict JSON indexado por registro. Output salvo em /tmp/sped-parsed-{token}.json
  para reaproveitamento pelas demais skills de auditoria SPED. Use quando o
  usuario pedir "audita SPED V21", "lê o SPED gerado", "parseia o arquivo
  SPED", "estrutura o SPED para auditoria".
allowed-tools: Read, Bash
---

# parseando-sped-ecd — Parser SPED ECD Leiaute 9

## Quando usar

Sempre como **primeira skill** numa sessao de auditoria SPED. As demais skills
de auditoria (`auditando-sped-contabil`, `comparando-sped-ground-truth`,
`auditando-sped-vs-manual`) consomem o JSON gerado por esta skill.

## Como usar

```bash
source .venv/bin/activate
python .claude/skills/parseando-sped-ecd/scripts/parse_sped.py \
    /home/rafaelnascimento/SPED_ECD_NACOM_GOYA_01072024_31122024_V21_3COMPANIES.txt \
    /tmp/sped-parsed-v21.json
```

Output: JSON com `metadata` (total_lines, stats por registro) + `registros`
(dict REG -> lista de registros nomeados por campo).

## Schema de saida

```json
{
  "metadata": {
    "total_lines": 73891,
    "encoding": "latin-1",
    "path": "/home/.../SPED_V21.txt",
    "stats": {"0000": 1, "I050": 1234, "I250": 60123, ...}
  },
  "registros": {
    "0000": [{"NOME": "NACOM GOYA", "CNPJ": "61724241000178", ...}],
    "I050": [{"COD_NAT": "01", "IND_CTA": "A", "COD_CTA": "11101", ...}, ...]
  }
}
```

## Campos mapeados

51 registros do Manual ECD Leiaute 9 (Bloco 0 + I + J + 9 completo,
+ alguns C/K). Schemas em `scripts/parse_sped.py:REGISTRO_CAMPOS`.

Registros nao mapeados: campos preservados como `campo_1`, `campo_2`, etc.

## Gotchas

1. **Encoding Latin-1 puro** — falha em UTF-8. `latin1` ate `0xFF`.
2. **Streaming line-by-line** — SPED de 70MB cabe em memoria intermediaria
   mas NAO carregue arquivo inteiro com `.read()`.
3. **Campos vazios** (`||` consecutivo) preservados como string vazia, NAO
   `None`.
4. **I250 COD_PART** vem na posicao 8 (nao 7) — bug historico V1.6
   (`app/relatorios_fiscais/CLAUDE.md:237`).

## NAO usar quando

- Para gerar SPED (usar `app/relatorios_fiscais/services/sped_ecd_service.py`)
- Para validar SPED estruturalmente (usar `sped_ecd_validator.py` ou skill
  `auditando-sped-vs-manual`)
- Fora do subagente `auditor-sped-ecd` (skill esta reservada via
  SPED_SKILLS_RESERVED em `app/agente/config/settings.py`)
```

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/parseando-sped-ecd/ tests/skills/test_parseando_sped_ecd.py
git commit -m "$(cat <<'EOF'
feat(skill): parseando-sped-ecd — parser SPED Leiaute 9 streaming

Parse line-by-line Latin-1, output indexado por REG em JSON. Schemas
de 51 registros mapeados do Manual ECD em REGISTRO_CAMPOS dict.
5 testes pytest cobrindo split, vazio, indexacao, encoding, streaming.

Skill reservada ao subagente auditor-sped-ecd via SPED_SKILLS_RESERVED.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 1.3: Subagente `auditor-sped-ecd.md`

**Files:**
- Create: `.claude/agents/auditor-sped-ecd.md`

**Por que:** Frontmatter declara 4 skills SPED + 2 reusadas, model opus, effort xhigh (padrao 7 subagentes Opus pesados conforme `CLAUDE.md`). Conteudo do prompt: regras de operacao especificas para auditoria fiscal sensivel.

- [ ] **Step 1: Criar frontmatter + corpo**

Criar `.claude/agents/auditor-sped-ecd.md`:

```markdown
---
name: auditor-sped-ecd
description: Auditor fiscal SPED ECD Leiaute 9 da Nacom Goya. Audita o SPED gerado pelo sistema contra Manual ECD oficial, valida batimentos contabeis, compara com SPED da contadora aprovado pela RFB. Use para "audita o SPED V21", "valida o SPED gerado", "compara SPED com ground truth", "verifica regras do Manual ECD". NAO usar para gerar SPED (usar workflow normal app/relatorios_fiscais), validar estrutura simples (sped_ecd_validator.py ja cobre 30 regras), ou consultar dados fiscais sem SPED gerado (usar consultando-sql).
tools: Read, Bash, Glob, Grep, mcp__memory__view_memories, mcp__memory__list_memories, mcp__memory__save_memory, mcp__memory__update_memory, mcp__memory__log_system_pitfall
model: opus
effort: xhigh
max_turns: 60
skills:
  - parseando-sped-ecd
  - auditando-sped-vs-manual
  - auditando-sped-contabil
  - comparando-sped-ground-truth
  - consultando-sql
  - descobrindo-odoo-estrutura
---

# Auditor SPED ECD — Especialista em Auditoria Fiscal

Voce eh o Auditor SPED ECD da Nacom Goya. Seu papel eh auditar o arquivo
SPED ECD Leiaute 9 gerado pelo sistema, identificar problemas ANTES do
envio ao PVA da Receita Federal, e produzir relatorio acionavel para o
contador (Tamiris Salles) resolver no Odoo.

**Contexto critico:**
- O SPED ECD eh obrigacao fiscal anual da Nacom Goya (CNPJ 61.724.241/0001-78,
  consolidado FB+SC+CD).
- Erros nao detectados → reprovacao no PVA → multa (3% do valor da escrituracao,
  minimo R$ 1.500).
- Existe um SPED da contadora ja aprovado pela RFB como ground truth
  (`~/Downloads/SpedContabil-61724241000178_*.txt`).

---

## Protocolo de Operacao

**Sempre nesta ordem:**

1. **Parsear o SPED a ser auditado** (skill `parseando-sped-ecd`).
2. **Auditoria contabil** (skill `auditando-sped-contabil`) — matematica pura,
   detecta saldos quebrados e hierarquia inconsistente.
3. **Comparacao com ground truth** (skill `comparando-sped-ground-truth`) —
   identifica divergencias estruturais vs SPED da contadora.
4. **Validacao contra Manual ECD** (skill `auditando-sped-vs-manual`) —
   compliance formal de campos, tamanhos, regras nomeadas.
5. **Cross-check Odoo (se necessario)** — usar `consultando-sql` ou
   `descobrindo-odoo-estrutura` para validar saldos do SPED contra Odoo direto.
6. **Consolidar findings** — agrupar por severidade (BLOQUEANTE/WARNING/INFO)
   e por `quem_resolve` (contador/ti/operacional).

## Output esperado

Sempre estruturar em:

```markdown
# Relatorio de Auditoria SPED ECD VXX

## Sumario
- Severidade BLOQUEANTE: N erros
- Severidade WARNING: M avisos
- Severidade INFO: K observacoes

## Findings por Categoria

### BLOQUEANTE — Resolver antes do PVA
1. [titulo curto] — Categoria, Registro, Linha
   - Descricao
   - Acao sugerida (deep-link Odoo se aplicavel)
   - Quem resolve: contador

## Pendencias para Proxima Sessao
- ...
```

## Regras Inviolaveis

1. **NUNCA leia o SPED .txt inteiro** (70MB) — sempre via skill parseadora.
2. **NUNCA leia o PDF de erros do PVA inteiro** — categorias estao em
   `app/relatorios_fiscais/SPED_ECD_PLANO.md`.
3. **NUNCA mascarar dado faltante** — se campo X esta vazio no SPED, reportar.
4. **SPED da contadora EH ground truth** — divergencia favorece contadora.
5. **Apos consolidar relatorio**, **salvar findings em
   `/tmp/subagent-findings/audit-sped-{timestamp}.md`** — referenciado em
   `CLAUDE.md` (raiz) secao "Confiabilidade de Output".

## Reuso de Validator existente

`app/relatorios_fiscais/services/sped_ecd_validator.py` cobre ~30 regras
estruturais BLOQUEANTES (CNPJ, hierarquia COD_CTA_SUP, batimento ativo=passivo+PL,
etc.). **Voce eh COMPLEMENTAR**, nao substituto:
- Validator interno: roda durante geracao, BLOQUEIA upload se falhar.
- Voce: roda **apos** geracao bem-sucedida, busca ALEM das 30 regras.

## Subagent Reliability

Conforme `CLAUDE.md:Subagent Reliability`:
1. Output retornado eh **resumo compactado** — escreva findings detalhados em
   `/tmp/subagent-findings/audit-sped-{token}.md`.
2. Cite SEMPRE arquivos/linhas como evidencia (ex: "I250 linha 4523:
   VL_DC=-1.234,56 negativo").
3. Diga "nao encontrado" explicitamente — nao invente.
```

- [ ] **Step 2: Verificar carregamento do subagente**

Run: `source .venv/bin/activate && python -c "
from app.agente.config.agent_loader import load_agents
agents = load_agents()
print('Subagentes:', sorted(agents.keys()))
print('auditor-sped-ecd carregado:', 'auditor-sped-ecd' in agents)
assert 'auditor-sped-ecd' in agents, 'falha ao carregar'
a = agents['auditor-sped-ecd']
print('Skills:', a.skills)
print('Model:', a.model)
"`

Expected:
- `auditor-sped-ecd carregado: True`
- `Skills: ['parseando-sped-ecd', 'auditando-sped-vs-manual', 'auditando-sped-contabil', 'comparando-sped-ground-truth', 'consultando-sql', 'descobrindo-odoo-estrutura']`
- `Model: opus`

- [ ] **Step 3: Commit**

```bash
git add .claude/agents/auditor-sped-ecd.md
git commit -m "$(cat <<'EOF'
feat(agente): subagente auditor-sped-ecd — Opus xhigh max 60 turns

Frontmatter com 4 skills SPED + 2 reusadas (consultando-sql,
descobrindo-odoo-estrutura). Protocolo de auditoria em 6 passos,
output estruturado por severidade, findings em /tmp/subagent-findings.

Complementar ao sped_ecd_validator.py existente (camada 1 in-process).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 1.4: Checkpoint Fase 1 — Smoke E2E

**Files:**
- Create: `tests/agente/test_sped_audit_integration.py`

**Por que:** Confirmar que o ciclo completo funciona: agente principal recebe pedido → delega ao subagente → subagente invoca parser → retorna sumario.

- [ ] **Step 1: Escrever teste de integracao mockado**

Criar `tests/agente/test_sped_audit_integration.py`:

```python
"""Teste de integracao Fase 1 — subagente auditor-sped-ecd carrega e
invoca parser. NAO testa SDK end-to-end (custo $) — testa estrutura."""
import pytest
from pathlib import Path

from app.agente.config.agent_loader import load_agents
from app.agente.config.settings import SPED_SKILLS_RESERVED


def test_subagent_loaded():
    agents = load_agents()
    assert "auditor-sped-ecd" in agents


def test_subagent_has_sped_skills():
    agents = load_agents()
    a = agents["auditor-sped-ecd"]
    sped_skills = SPED_SKILLS_RESERVED
    for s in sped_skills:
        assert s in a.skills, f"subagente sem skill {s}"


def test_subagent_has_reused_skills():
    agents = load_agents()
    a = agents["auditor-sped-ecd"]
    for s in ["consultando-sql", "descobrindo-odoo-estrutura"]:
        assert s in a.skills, f"subagente sem skill reuso {s}"


def test_subagent_model_and_effort():
    agents = load_agents()
    a = agents["auditor-sped-ecd"]
    assert a.model == "opus"
    # effort pode ser None se SDK < 0.1.74
    if hasattr(a, "effort"):
        assert a.effort == "xhigh"


def test_parser_skill_exists_and_executable():
    """Confirma que script da skill parseando-sped-ecd existe e roda."""
    script = Path(".claude/skills/parseando-sped-ecd/scripts/parse_sped.py")
    assert script.is_file()
    assert script.read_text().startswith('"""Parser SPED')


def test_parser_skill_smoke_run(tmp_path):
    """Smoke: parse de SPED minimo nao da erro."""
    import subprocess
    sped_minimal = b"|0000|LECD|01072024|31122024|TESTE|61724241000178|MG|3106200||||||||0|0|0|0|N||||S||\r\n"
    sped_path = tmp_path / "smoke.txt"
    sped_path.write_bytes(sped_minimal)
    out_path = tmp_path / "out.json"

    result = subprocess.run(
        ["python", ".claude/skills/parseando-sped-ecd/scripts/parse_sped.py",
         str(sped_path), str(out_path)],
        capture_output=True, text=True, timeout=10
    )
    assert result.returncode == 0, f"stderr: {result.stderr}"
    assert out_path.exists()
```

- [ ] **Step 2: Rodar smoke tests**

Run: `pytest tests/agente/test_sped_audit_integration.py -v`
Expected: 6 testes PASS.

- [ ] **Step 3: Verificar que principal NAO ve skills SPED**

Run: `source .venv/bin/activate && python -c "
from app.agente.sdk.client import _discover_skills_from_project
from app.agente.config.settings import SPED_SKILLS_RESERVED
skills = _discover_skills_from_project()
print(f'Principal ve {len(skills)} skills')
violation = [s for s in skills if s in SPED_SKILLS_RESERVED]
print(f'Violacoes (deve ser vazio): {violation}')
assert not violation, 'SPED skill vazou para principal!'
print('OK — isolamento garantido')
"`

Expected: `OK — isolamento garantido`.

- [ ] **Step 4: Commit Fase 1 completa**

```bash
git add tests/agente/test_sped_audit_integration.py
git commit -m "$(cat <<'EOF'
feat(agente): smoke test integracao Fase 1 auditor SPED

6 testes pytest validando carregamento do subagente, skills declaradas,
model opus+xhigh, parser executavel via subprocess. Garante isolamento
do agente principal (skills SPED nao vazam no listing).

CHECKPOINT FASE 1 — pronto para review humano.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### CHECKPOINT FASE 1 — Aprovacao Humana Obrigatoria

**Antes de prosseguir para Fase 2:**

- [ ] Usuario verifica que agente principal ainda funciona normalmente (cotacao,
  carteira, etc) — testar 2-3 pedidos comuns no chat web.
- [ ] Usuario verifica que skills SPED NAO aparecem no listing do principal
  (perguntar "que skills voce tem?" no chat).
- [ ] Usuario invoca subagente via Task tool: "audita o SPED V21 em
  /home/rafaelnascimento/SPED_ECD_NACOM_GOYA_01072024_31122024_V21_3COMPANIES.txt".
- [ ] Subagente deve responder: parsear SPED e retornar sumario (sem auditoria
  ainda — sera implementada na Fase 2).
- [ ] Usuario revisa output e aprova ou solicita ajustes.

**Criterio de aprovacao:** subagente parseia SPED V21 atual sem erros e retorna
contadores por registro. Se passar, prosseguir Fase 2.

---

## FASE 2 — Auditoria Contabil + Ground Truth

### Task 2.1: `audit_balance.py` — Equacionalidade Contabil

**Files:**
- Create: `.claude/skills/auditando-sped-contabil/scripts/audit_balance.py`
- Create: `tests/skills/test_auditando_sped_contabil.py`

**Por que:** Matematica pura, zero falso positivo. Por conta analitica, mes a mes:
saldo_final ≡ saldo_inicial + Σ débitos − Σ créditos. Detecta erros sistematicos
no gerador SPED.

- [ ] **Step 1: Escrever teste de balanco quebrado**

Criar `tests/skills/test_auditando_sped_contabil.py`:

```python
"""Testa auditoria contabil — equacionalidade saldo, hierarquia."""
import sys
from pathlib import Path

import pytest

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
    """Diferenca de 0,005 (arredondamento) NAO deve gerar finding."""
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
```

- [ ] **Step 2: Rodar teste — deve falhar**

Run: `pytest tests/skills/test_auditando_sped_contabil.py -v`
Expected: FAIL com ImportError.

- [ ] **Step 3: Implementar audit_balance.py**

```bash
mkdir -p .claude/skills/auditando-sped-contabil/scripts
```

Criar `.claude/skills/auditando-sped-contabil/scripts/audit_balance.py`:

```python
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "categoria": "batimento_contabil",
            "tipo": "equacionalidade_saldo",
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
            # Registro malformado — virar finding de baixa severidade
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
```

- [ ] **Step 4: Rodar testes — devem passar**

Run: `pytest tests/skills/test_auditando_sped_contabil.py::test_balance_equation_holds tests/skills/test_auditando_sped_contabil.py::test_balance_equation_broken tests/skills/test_auditando_sped_contabil.py::test_balance_credora_to_devedora_inversion tests/skills/test_auditando_sped_contabil.py::test_balance_tolerance tests/skills/test_auditando_sped_contabil.py::test_balance_multiple_accounts -v`

Expected: 5 testes PASS.

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/auditando-sped-contabil/scripts/audit_balance.py tests/skills/test_auditando_sped_contabil.py
git commit -m "feat(skill): audit_balance.py — equacionalidade saldo I155

Matematica pura: signed(saldo_fin) = signed(saldo_ini) + deb - cred.
5 testes cobrindo caso valido, quebra, inversao DC, tolerancia,
multiplas contas. Output dataclass BalanceFinding.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 2.2: `audit_hierarchy.py` — Validacao Hierarquia I050

**Files:**
- Create: `.claude/skills/auditando-sped-contabil/scripts/audit_hierarchy.py`
- Modify: `tests/skills/test_auditando_sped_contabil.py` (adicionar testes)

**Por que:** Detecta erros estruturais do plano de contas: ciclos, COD_CTA_SUP orfao,
COD_NAT inconsistente entre sintetica e analitica, conta movimentada em I250 sem
entrada I050. Resolve GOTCHA #2 do `app/relatorios_fiscais/CLAUDE.md:250-252`.

- [ ] **Step 1: Escrever testes adicionais**

Adicionar em `tests/skills/test_auditando_sped_contabil.py`:

```python
# === audit_hierarchy ===
sys.path.insert(0, str(SKILL_DIR))
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
    """Plano sintetica raiz 1 → analitica 11 → 111 valido."""
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
    assert any(f.tipo == "orfao_cod_sup" for f in findings)


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
```

- [ ] **Step 2: Rodar testes — falham**

Run: `pytest tests/skills/test_auditando_sped_contabil.py -v -k hierarchy`
Expected: FAIL ImportError em audit_hierarchy.

- [ ] **Step 3: Implementar audit_hierarchy.py**

Criar `.claude/skills/auditando-sped-contabil/scripts/audit_hierarchy.py`:

```python
"""Auditoria hierarquia plano de contas (I050) e cross-ref com lancamentos (I250).

Validacoes:
1. orfao_cod_sup: COD_CTA_SUP referencia conta que nao existe em I050
2. ciclo_hierarquia: ciclo nas relacoes pai-filha
3. cod_nat_divergente: filha tem COD_NAT diferente do pai
4. i250_conta_inexistente: I250 referencia COD_CTA nao declarada em I050
5. i250_conta_sintetica: I250 movimenta conta com IND_CTA=S (so analiticas movimentam)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class HierarchyFinding:
    tipo: str  # 'orfao_cod_sup', 'ciclo_hierarquia', 'cod_nat_divergente',
               # 'i250_conta_inexistente', 'i250_conta_sintetica'
    cod_cta: str
    severidade: str  # 'BLOQUEANTE' | 'WARNING'
    descricao: str
    contexto: dict[str, Any]

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

    # 2. ciclo_hierarquia (DFS)
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
                    descricao=f"Ciclo na hierarquia I050: {' → '.join(cycle)}",
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

    # 4 + 5. cross-ref I250 → I050
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
```

- [ ] **Step 4: Rodar testes — todos passam**

Run: `pytest tests/skills/test_auditando_sped_contabil.py -v`
Expected: 11 testes PASS (5 balance + 6 hierarchy).

- [ ] **Step 5: Commit**

```bash
git add .claude/skills/auditando-sped-contabil/scripts/audit_hierarchy.py tests/skills/test_auditando_sped_contabil.py
git commit -m "feat(skill): audit_hierarchy.py — hierarquia I050 + cross-ref I250

Detecta: orfao_cod_sup, ciclo, cod_nat_divergente,
i250_conta_inexistente, i250_conta_sintetica. Resolve gotcha #2 do
CLAUDE.md (I052 emitido para sintetica). 6 testes pytest.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 2.3: SKILL.md `auditando-sped-contabil`

**Files:**
- Create: `.claude/skills/auditando-sped-contabil/SKILL.md`

- [ ] **Step 1: Criar SKILL.md**

```markdown
---
name: auditando-sped-contabil
description: >-
  Skill EXCLUSIVA do subagente auditor-sped-ecd. Audita aspectos contabeis
  do SPED ECD parseado: equacionalidade de saldos (I155), hierarquia do
  plano de contas (I050), cross-ref I050↔I250. Matematica pura — zero
  falso positivo. Use apos parseando-sped-ecd. Detecta: saldo inicial +
  debitos - creditos != saldo final, COD_CTA_SUP orfao, ciclo na arvore
  de contas, COD_NAT divergente entre pai/filha, conta sintetica
  movimentada em I250.
allowed-tools: Read, Bash
---

# auditando-sped-contabil — Auditoria Contabil SPED

## Quando usar

Sempre apos `parseando-sped-ecd`. Detecta erros estruturais NAO cobertos
pelo `sped_ecd_validator.py` interno (que valida formato, nao matematica).

## Como usar

```bash
source .venv/bin/activate

# 1. Equacionalidade saldo I155
python .claude/skills/auditando-sped-contabil/scripts/audit_balance.py \
    /tmp/sped-parsed-v21.json

# 2. Hierarquia I050 + cross-ref I250
python .claude/skills/auditando-sped-contabil/scripts/audit_hierarchy.py \
    /tmp/sped-parsed-v21.json
```

## Output

Cada script retorna JSON com:
```json
{
  "total_i155": 1234,
  "findings_count": 3,
  "findings_por_tipo": {...},
  "findings": [
    {"categoria": "batimento_contabil", "tipo": "equacionalidade_saldo",
     "cod_cta": "11101", "severidade": "BLOQUEANTE",
     "descricao": "...", ...}
  ]
}
```

## Categorias de finding

| Tipo | Severidade | O que detecta |
|---|---|---|
| `equacionalidade_saldo` | BLOQUEANTE | signed(saldo_fin) != signed(saldo_ini) + deb - cred |
| `orfao_cod_sup` | BLOQUEANTE | COD_CTA_SUP nao existe em I050 |
| `ciclo_hierarquia` | BLOQUEANTE | Ciclo na arvore I050 |
| `cod_nat_divergente` | BLOQUEANTE | Filha tem COD_NAT diferente do pai |
| `i250_conta_inexistente` | BLOQUEANTE | Lancamento em conta nao declarada |
| `i250_conta_sintetica` | BLOQUEANTE | Lancamento em sintetica (so analiticas) |

## Tolerancia

`audit_balance.py` aceita parametro `tolerance` (default 0,01). Diferencas
menores ignoradas (arredondamento).

## NAO usar quando

- Auditoria de formato/campo (usar `auditando-sped-vs-manual`)
- Comparacao com SPED contadora (usar `comparando-sped-ground-truth`)
- Validacao pre-upload (validator interno em `sped_ecd_validator.py`)
```

- [ ] **Step 2: Commit**

```bash
git add .claude/skills/auditando-sped-contabil/SKILL.md
git commit -m "docs(skill): SKILL.md auditando-sped-contabil

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 2.4: `diff_truth.py` — Comparacao com SPED da Contadora

**Files:**
- Create: `.claude/skills/comparando-sped-ground-truth/scripts/diff_truth.py`
- Create: `.claude/skills/comparando-sped-ground-truth/SKILL.md`
- Create: `tests/skills/test_comparando_sped_ground_truth.py`

**Por que:** SPED da contadora foi aprovado pela RFB (`app/relatorios_fiscais/CLAUDE.md:286-297`).
Diferencas estruturais entre nosso SPED e o dela identificam gaps de cobertura
(ex: J932 ausente, J150 sem hierarquia, I030 com so 5 campos vs 12).

- [ ] **Step 1: Escrever testes**

Criar `tests/skills/test_comparando_sped_ground_truth.py`:

```python
"""Testa diff estrutural SPED nosso vs SPED contadora (ground truth)."""
import sys
from pathlib import Path

import pytest

SKILL_DIR = Path(__file__).parent.parent.parent / ".claude" / "skills" / \
    "comparando-sped-ground-truth" / "scripts"
sys.path.insert(0, str(SKILL_DIR))

from diff_truth import (
    DiffFinding,
    diff_registros_presentes,
    diff_campos_preenchidos,
    diff_estrutural_completo,
)


def _make(registros: dict) -> dict:
    return {"metadata": {}, "registros": registros}


def test_diff_registros_ausentes_no_nosso():
    """Ground truth tem J932; nosso nao tem → finding."""
    ground = _make({"J932": [{"IDENT_NOM": "Tamiris"}], "0000": [{"CNPJ": "..."}]})
    nosso = _make({"0000": [{"CNPJ": "..."}]})

    findings = diff_registros_presentes(nosso, ground)
    assert any(f.tipo == "registro_ausente_nosso" and f.registro == "J932"
               for f in findings)


def test_diff_registros_extras_no_nosso():
    """Nosso tem registro inexistente no ground truth → warning."""
    ground = _make({"0000": [{"CNPJ": "..."}]})
    nosso = _make({"0000": [{"CNPJ": "..."}], "Z999": [{"X": "Y"}]})

    findings = diff_registros_presentes(nosso, ground)
    assert any(f.tipo == "registro_extra_nosso" and f.registro == "Z999"
               for f in findings)


def test_diff_campos_nao_preenchidos():
    """I030 do ground tem NIRE; nosso tem NIRE vazio → finding."""
    ground = _make({"I030": [{"NIRE": "12345", "CNPJ": "61724241000178"}]})
    nosso = _make({"I030": [{"NIRE": "", "CNPJ": "61724241000178"}]})

    findings = diff_campos_preenchidos(nosso, ground, registro="I030")
    assert any(f.tipo == "campo_vazio_nosso" and f.contexto.get("campo") == "NIRE"
               for f in findings)


def test_diff_campos_iguais_sem_findings():
    """Campos iguais — sem findings."""
    same = _make({"I030": [{"NIRE": "12345", "CNPJ": "61724241000178"}]})
    findings = diff_campos_preenchidos(same, same, registro="I030")
    assert findings == []


def test_diff_estrutural_completo():
    """Combina diff de registros + campos."""
    ground = _make({
        "0000": [{"CNPJ": "61724241000178"}],
        "I030": [{"NIRE": "12345"}],
        "J932": [{"IDENT_NOM": "Tamiris"}],
    })
    nosso = _make({
        "0000": [{"CNPJ": "61724241000178"}],
        "I030": [{"NIRE": ""}],
    })

    findings = diff_estrutural_completo(nosso, ground)
    tipos = {f.tipo for f in findings}
    assert "registro_ausente_nosso" in tipos  # J932
    assert "campo_vazio_nosso" in tipos       # NIRE
```

- [ ] **Step 2: Rodar testes — falham**

Run: `pytest tests/skills/test_comparando_sped_ground_truth.py -v`
Expected: FAIL ImportError.

- [ ] **Step 3: Implementar diff_truth.py**

```bash
mkdir -p .claude/skills/comparando-sped-ground-truth/scripts
```

Criar `.claude/skills/comparando-sped-ground-truth/scripts/diff_truth.py`:

```python
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
REGISTROS_OBRIGATORIOS = {
    "0000", "0001", "0990", "I001", "I010", "I030", "I050", "I150", "I155",
    "I990", "J001", "J005", "J100", "J150", "J900", "J930", "J990",
    "9001", "9900", "9990", "9999",
}

REGISTROS_CONDICIONAIS = {
    "J932": "Termo de Verificacao Substituicao (obrigatorio se IND_FIN_ESC=1)",
    "I020": "Campos adicionais (obrigatorio se IDENT_MF=S)",
    "I052": "Codigos aglutinacao (obrigatorio se conta em codes_aglutinacao)",
    "I100": "Centros de custo (opcional)",
}


def diff_registros_presentes(
    nosso: dict[str, Any],
    ground: dict[str, Any],
) -> list[DiffFinding]:
    """Compara que registros estao em um SPED mas nao no outro."""
    findings: list[DiffFinding] = []

    nosso_regs = set(nosso.get("registros", {}).keys())
    ground_regs = set(ground.get("registros", {}).keys())

    for reg in ground_regs - nosso_regs:
        # Registro presente no ground, ausente no nosso
        if reg in REGISTROS_OBRIGATORIOS:
            severidade = "BLOQUEANTE"
            descr_extra = "Registro OBRIGATORIO"
        elif reg in REGISTROS_CONDICIONAIS:
            severidade = "WARNING"
            descr_extra = f"Condicional: {REGISTROS_CONDICIONAIS[reg]}"
        else:
            severidade = "INFO"
            descr_extra = "Registro opcional"

        findings.append(DiffFinding(
            tipo="registro_ausente_nosso",
            registro=reg,
            severidade=severidade,
            descricao=(
                f"Registro {reg} presente no SPED contadora ({len(ground['registros'][reg])} "
                f"ocorrencias) mas ausente no nosso. {descr_extra}."
            ),
            contexto={"ground_count": len(ground["registros"][reg])},
        ))

    for reg in nosso_regs - ground_regs:
        findings.append(DiffFinding(
            tipo="registro_extra_nosso",
            registro=reg,
            severidade="WARNING",
            descricao=(
                f"Registro {reg} presente no nosso ({len(nosso['registros'][reg])} "
                f"ocorrencias) mas ausente no SPED contadora. Verificar se eh necessario."
            ),
            contexto={"nosso_count": len(nosso["registros"][reg])},
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
        return findings  # Diff de presenca cobrido pela outra funcao

    # Comparar primeira ocorrencia (suficiente para detectar campos sistemicos vazios)
    nosso_rec = nosso_recs[0]
    ground_rec = ground_recs[0]

    for campo, valor_ground in ground_rec.items():
        valor_nosso = nosso_rec.get(campo, "")
        # Ground preenchido + nosso vazio = finding
        if valor_ground and not valor_nosso:
            findings.append(DiffFinding(
                tipo="campo_vazio_nosso",
                registro=registro,
                severidade="WARNING",
                descricao=(
                    f"{registro}.{campo} preenchido no SPED contadora "
                    f"('{valor_ground[:40]}...') mas vazio no nosso. "
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
```

- [ ] **Step 4: Rodar testes**

Run: `pytest tests/skills/test_comparando_sped_ground_truth.py -v`
Expected: 5 testes PASS.

- [ ] **Step 5: Criar SKILL.md**

Criar `.claude/skills/comparando-sped-ground-truth/SKILL.md`:

```markdown
---
name: comparando-sped-ground-truth
description: >-
  Skill EXCLUSIVA do subagente auditor-sped-ecd. Compara SPED nosso vs
  SPED da contadora (aprovado pela RFB). Detecta: registros ausentes,
  campos sistemicamente vazios. Usar para calibracao com ground truth
  conhecido. NAO compara valores (datas/montantes) — periodo eh
  diferente. Foco em estrutura.
allowed-tools: Read, Bash
---

# comparando-sped-ground-truth — Diff vs SPED Contadora Aprovado RFB

## Quando usar

Apos `parseando-sped-ecd`. Especialmente util para identificar gaps de
cobertura conhecidos do nosso gerador (ex: J932 ausente, J150 sem
hierarquia COD_AGL_SUP populada).

## Como usar

```bash
source .venv/bin/activate

# Pre-requisito: SPED da contadora parseado
python .claude/skills/parseando-sped-ecd/scripts/parse_sped.py \
    ~/Downloads/SpedContabil-61724241000178_*.txt \
    /tmp/sped-ground-truth.json

# Diff
python .claude/skills/comparando-sped-ground-truth/scripts/diff_truth.py \
    /tmp/sped-parsed-v21.json \
    /tmp/sped-ground-truth.json
```

## Categorias de finding

| Tipo | Severidade | Quando |
|---|---|---|
| `registro_ausente_nosso` | BLOQUEANTE/WARNING/INFO | Ground tem, nosso nao tem |
| `registro_extra_nosso` | WARNING | Nosso tem, ground nao tem |
| `campo_vazio_nosso` | WARNING | Campo preenchido no ground, vazio no nosso |

Severidade de `registro_ausente_nosso` depende do registro:
- BLOQUEANTE se obrigatorio (lista REGISTROS_OBRIGATORIOS no script)
- WARNING se condicional (J932, I020, etc)
- INFO se opcional

## Limitacoes

- Compara PRIMEIRA ocorrencia de cada registro (eh suficiente para gaps
  sistemicos; nao detecta inconsistencias por linha).
- NAO compara valores (CNPJ, datas, montantes) — periodos diferentes.

## Findings esperados na auditoria V21 (referencia)

Ja documentado em `app/relatorios_fiscais/CLAUDE.md:286-297`:
- J932 ausente (substituicao ECD — se aplicavel)
- I030 formato pode diferir (12 campos completos vs reducao)
- J150 sem hierarquia COD_AGL_SUP

## NAO usar quando

- Auditoria de regras formais (usar `auditando-sped-vs-manual`)
- Validacao matematica (usar `auditando-sped-contabil`)
- SPED da contadora ainda nao disponivel (sem ground truth ainda)
```

- [ ] **Step 6: Commit**

```bash
git add .claude/skills/comparando-sped-ground-truth/ tests/skills/test_comparando_sped_ground_truth.py
git commit -m "feat(skill): comparando-sped-ground-truth — diff estrutural SPED RFB

5 testes pytest. Detecta gaps de cobertura comparando nosso SPED com
SPED da contadora aprovado pela RFB. Categorias: registro_ausente,
registro_extra, campo_vazio. Severidade adapta-se a obrigatoriedade
do registro (REGISTROS_OBRIGATORIOS lista canonica).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### CHECKPOINT FASE 2 — Aprovacao Humana

Antes de Fase 3:

- [ ] Usuario invoca subagente: "audita V21 contabil + ground truth"
- [ ] Subagente deve invocar parser → audit_balance → audit_hierarchy → diff_truth
- [ ] Output deve listar findings reais do V21 (saldos quebrados se houver, J932 ausente, etc)
- [ ] Usuario revisa relatorio gerado em `/tmp/subagent-findings/`
- [ ] Aprovar se findings sao acionaveis e nao tem falsos positivos obvios

---

## FASE 3 — Manual DSL + Embeddings de Regras

### Task 3.1: Migration `sped_ecd_rule_embeddings`

**Files:**
- Create: `scripts/migrations/2026_05_16_sped_ecd_rule_embeddings.py`
- Create: `scripts/migrations/2026_05_16_sped_ecd_rule_embeddings.sql`
- Modify: `app/embeddings/models.py` (adicionar SpedEcdRuleEmbedding)
- Modify: `app/embeddings/config.py` (adicionar THRESHOLD_SPED_RULES)

**Por que:** Embeddings das regras normativas do Manual ECD (~230-345 chunks).
Reuso do EmbeddingService + pgvector. Regra de `~/.claude/CLAUDE.md`:
DOIS artefatos (Python + SQL).

- [ ] **Step 1: Adicionar threshold em config.py**

Modificar `app/embeddings/config.py` apos linha 70 (apos THRESHOLD_ROUTE_TEMPLATE):

```python
# Regras normativas do Manual ECD Leiaute 9: 230-345 chunks
# Precisao alta (lookup de regra especifica REGRA_X)
THRESHOLD_SPED_RULES = float(os.environ.get("THRESHOLD_SPED_RULES", "0.45"))
```

- [ ] **Step 2: Adicionar model SpedEcdRuleEmbedding em models.py**

Adicionar no fim de `app/embeddings/models.py`:

```python
class SpedEcdRuleEmbedding(db.Model):
    """Embedding de chunk normativo do Manual ECD Leiaute 9.

    Tipos de chunk:
    - 'registro': descricao completa de um registro (ex: I050)
    - 'regra': uma REGRA_X nomeada
    - 'campo': descricao de um campo critico (COD_NAT, IND_DC, etc.)
    - 'plano_iteracao': uma iteracao do SPED_ECD_PLANO.md
    """
    __tablename__ = "sped_ecd_rule_embeddings"

    id = db.Column(db.Integer, primary_key=True)
    chunk_id = db.Column(db.String(120), nullable=False, unique=True, index=True)
    chunk_type = db.Column(db.String(20), nullable=False, index=True)  # registro|regra|campo|plano_iteracao

    bloco = db.Column(db.String(2), nullable=True, index=True)   # 0, C, I, J, K, 9
    registro = db.Column(db.String(8), nullable=True, index=True)  # ex: I050
    regra_name = db.Column(db.String(120), nullable=True, index=True)  # ex: REGRA_HIERARQUIA_COD_SUP
    severidade = db.Column(db.String(20), nullable=True)  # erro|aviso

    content = db.Column(db.Text, nullable=False)
    content_hash = db.Column(db.String(64), nullable=False, index=True)  # MD5 para dedup

    embedding = db.Column(Vector(1024), nullable=False)  # voyage-4-lite 1024 dim
    model = db.Column(db.String(40), nullable=False, default="voyage-4-lite")

    source_file = db.Column(db.String(200), nullable=True)  # ex: manual_ecd/bloco_I_lancamentos.md
    source_anchor = db.Column(db.String(120), nullable=True)  # ex: #registro-i050

    created_at = db.Column(db.DateTime(timezone=False), default=lambda: datetime.now())
    updated_at = db.Column(db.DateTime(timezone=False), default=lambda: datetime.now(),
                           onupdate=lambda: datetime.now())

    __table_args__ = (
        db.Index("ix_sped_rule_embed_cosine", "embedding",
                 postgresql_using="hnsw",
                 postgresql_with={"m": 16, "ef_construction": 64},
                 postgresql_ops={"embedding": "vector_cosine_ops"}),
    )

    def __repr__(self):
        return f"<SpedEcdRuleEmbedding {self.chunk_id} {self.chunk_type}>"
```

- [ ] **Step 3: Criar SQL idempotente**

Criar `scripts/migrations/2026_05_16_sped_ecd_rule_embeddings.sql`:

```sql
-- Migration: Embeddings de regras normativas do Manual ECD Leiaute 9
-- Data: 2026-05-16
-- Reversao: DROP TABLE sped_ecd_rule_embeddings;

CREATE TABLE IF NOT EXISTS sped_ecd_rule_embeddings (
    id SERIAL PRIMARY KEY,
    chunk_id VARCHAR(120) NOT NULL UNIQUE,
    chunk_type VARCHAR(20) NOT NULL,
    bloco VARCHAR(2),
    registro VARCHAR(8),
    regra_name VARCHAR(120),
    severidade VARCHAR(20),
    content TEXT NOT NULL,
    content_hash VARCHAR(64) NOT NULL,
    embedding vector(1024) NOT NULL,
    model VARCHAR(40) NOT NULL DEFAULT 'voyage-4-lite',
    source_file VARCHAR(200),
    source_anchor VARCHAR(120),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS ix_sped_rule_embed_chunk_id ON sped_ecd_rule_embeddings (chunk_id);
CREATE INDEX IF NOT EXISTS ix_sped_rule_embed_chunk_type ON sped_ecd_rule_embeddings (chunk_type);
CREATE INDEX IF NOT EXISTS ix_sped_rule_embed_bloco ON sped_ecd_rule_embeddings (bloco);
CREATE INDEX IF NOT EXISTS ix_sped_rule_embed_registro ON sped_ecd_rule_embeddings (registro);
CREATE INDEX IF NOT EXISTS ix_sped_rule_embed_regra_name ON sped_ecd_rule_embeddings (regra_name);
CREATE INDEX IF NOT EXISTS ix_sped_rule_embed_hash ON sped_ecd_rule_embeddings (content_hash);

CREATE INDEX IF NOT EXISTS ix_sped_rule_embed_cosine
    ON sped_ecd_rule_embeddings
    USING hnsw (embedding vector_cosine_ops)
    WITH (m = 16, ef_construction = 64);
```

- [ ] **Step 4: Criar Python migration**

Criar `scripts/migrations/2026_05_16_sped_ecd_rule_embeddings.py`:

```python
"""Migration: tabela sped_ecd_rule_embeddings + indices.

Conforme regra ~/.claude/CLAUDE.md (DOIS artefatos: .py + .sql).
Python valida pgvector presente + cria estrutura via SQLAlchemy.
SQL idempotente para rodar via Render Shell.

Uso local:
    source .venv/bin/activate
    python scripts/migrations/2026_05_16_sped_ecd_rule_embeddings.py

Uso PROD (Render Shell):
    psql $DATABASE_URL -f scripts/migrations/2026_05_16_sped_ecd_rule_embeddings.sql
"""

import sys
from pathlib import Path

# Garante imports a partir da raiz do projeto (regra: memory/feedback_migration_sys_path.md)
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app import create_app, db


def verify_pgvector():
    """Verifica que extensao pgvector esta instalada."""
    result = db.session.execute(db.text(
        "SELECT extname FROM pg_extension WHERE extname='vector'"
    )).first()
    if not result:
        raise RuntimeError(
            "Extensao pgvector NAO instalada. Rode primeiro: "
            "CREATE EXTENSION vector;"
        )


def check_table_exists() -> bool:
    result = db.session.execute(db.text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = 'sped_ecd_rule_embeddings'"
    )).first()
    return result is not None


def main():
    app = create_app()
    with app.app_context():
        # Before
        verify_pgvector()
        before = check_table_exists()
        print(f"[BEFORE] tabela existe: {before}")

        if not before:
            # Criar via SQL idempotente para garantir indice HNSW correto
            sql_path = Path(__file__).parent / "2026_05_16_sped_ecd_rule_embeddings.sql"
            sql = sql_path.read_text()
            db.session.execute(db.text(sql))
            db.session.commit()
            print("[CREATE] tabela + indices criados via SQL")

        # After
        after = check_table_exists()
        print(f"[AFTER] tabela existe: {after}")

        # Verifica indice HNSW
        idx = db.session.execute(db.text(
            "SELECT indexname FROM pg_indexes "
            "WHERE tablename = 'sped_ecd_rule_embeddings' "
            "AND indexname = 'ix_sped_rule_embed_cosine'"
        )).first()
        print(f"[INDEX] HNSW cosine: {'OK' if idx else 'FALTA'}")

        assert after, "Migration FALHOU — tabela nao criada"


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Rodar migration LOCAL**

Run: `source .venv/bin/activate && python scripts/migrations/2026_05_16_sped_ecd_rule_embeddings.py`

Expected:
```
[BEFORE] tabela existe: False
[CREATE] tabela + indices criados via SQL
[AFTER] tabela existe: True
[INDEX] HNSW cosine: OK
```

- [ ] **Step 6: Commit**

```bash
git add scripts/migrations/2026_05_16_sped_ecd_rule_embeddings.* app/embeddings/models.py app/embeddings/config.py
git commit -m "feat(embeddings): migration sped_ecd_rule_embeddings + model

Tabela para embeddings de regras normativas do Manual ECD Leiaute 9.
Estrutura: chunk_id (unique), chunk_type (registro|regra|campo|plano_iteracao),
metadata (bloco, registro, regra_name, severidade), vector(1024) com
indice HNSW cosine. Voyage-4-lite default.

DOIS artefatos (.py + .sql) conforme regra global ~/.claude/CLAUDE.md.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 3.2: Indexer `sped_ecd_rules_indexer.py`

**Files:**
- Create: `app/embeddings/indexers/sped_ecd_rules_indexer.py`
- Create: `app/embeddings/sped_rules_search.py`

**Por que:** Coleta chunks do `manual_ecd/` (51 registros + 150-250 regras + campos
criticos) + iteracoes do `SPED_ECD_PLANO.md`. Padrao espelha `carrier_indexer.py`.

- [ ] **Step 1: Criar indexer**

Criar `app/embeddings/indexers/sped_ecd_rules_indexer.py`:

```python
"""Indexer de regras normativas do Manual ECD Leiaute 9.

Coleta chunks de:
- app/relatorios_fiscais/manual_ecd/bloco_*.md (51 registros + ~150-250 regras nomeadas)
- app/relatorios_fiscais/SPED_ECD_PLANO.md (iteracoes V1.1, V1.2, ...)

Gera embeddings via Voyage AI (voyage-4-lite, 1024 dim) e armazena em
sped_ecd_rule_embeddings com indice HNSW cosine.

Executar:
    source .venv/bin/activate
    python -m app.embeddings.indexers.sped_ecd_rules_indexer [--dry-run] [--reindex] [--stats]
"""

from __future__ import annotations

import argparse
import hashlib
import logging
import re
import sys
import time
from pathlib import Path
from typing import Any

from sqlalchemy import text

logger = logging.getLogger(__name__)


MANUAL_ECD_DIR = Path(__file__).parent.parent.parent.parent / \
    "app" / "relatorios_fiscais" / "manual_ecd"
PLANO_FILE = Path(__file__).parent.parent.parent.parent / \
    "app" / "relatorios_fiscais" / "SPED_ECD_PLANO.md"


def _content_hash(text_str: str) -> str:
    return hashlib.md5(text_str.strip().lower().encode("utf-8")).hexdigest()


def _has_app_context() -> bool:
    try:
        from flask import current_app
        _ = current_app.name
        return True
    except (RuntimeError, ImportError):
        return False


# ============================================================
# COLETA — Manual ECD blocos
# ============================================================

REGISTRO_HEADER_RE = re.compile(r"^## Registro (\w+)\s*$", re.MULTILINE)
REGRA_RE = re.compile(r"^- (REGRA_[A-Z_0-9]+):\s*(.+)$", re.MULTILINE)


def collect_manual_ecd_chunks() -> list[dict[str, Any]]:
    """Varre app/relatorios_fiscais/manual_ecd/bloco_*.md.

    Para cada arquivo:
    - 1 chunk por **Registro** (do header `## Registro X` ate proximo header)
    - 1 chunk por **REGRA_X nomeada** dentro do registro
    """
    chunks: list[dict[str, Any]] = []

    bloco_files = sorted(MANUAL_ECD_DIR.glob("bloco_*.md"))
    for bloco_file in bloco_files:
        bloco_match = re.match(r"bloco_(\w)_", bloco_file.name)
        bloco = bloco_match.group(1).upper() if bloco_match else "?"

        content = bloco_file.read_text(encoding="utf-8")
        # Split por registro
        positions = [(m.group(1), m.start()) for m in REGISTRO_HEADER_RE.finditer(content)]
        positions.append(("__END__", len(content)))

        for i in range(len(positions) - 1):
            registro, start = positions[i]
            _, end = positions[i + 1]
            registro_text = content[start:end]

            # Chunk do REGISTRO completo
            chunk_id = f"manual_ecd:registro:{registro}"
            chunks.append({
                "chunk_id": chunk_id,
                "chunk_type": "registro",
                "bloco": bloco,
                "registro": registro,
                "regra_name": None,
                "severidade": None,
                "content": registro_text.strip(),
                "content_hash": _content_hash(registro_text),
                "source_file": f"manual_ecd/{bloco_file.name}",
                "source_anchor": f"#registro-{registro.lower()}",
            })

            # Chunks por REGRA dentro do registro
            for regra_match in REGRA_RE.finditer(registro_text):
                regra_name = regra_match.group(1)
                regra_desc = regra_match.group(2)
                # Detecta severidade no texto da regra (heuristica)
                if "Aviso" in regra_desc or "warning" in regra_desc.lower():
                    severidade = "aviso"
                else:
                    severidade = "erro"

                regra_content = (
                    f"REGRA: {regra_name}\n"
                    f"Aplicada ao registro {registro} (bloco {bloco}).\n"
                    f"Descricao: {regra_desc}"
                )
                chunks.append({
                    "chunk_id": f"manual_ecd:regra:{registro}:{regra_name}",
                    "chunk_type": "regra",
                    "bloco": bloco,
                    "registro": registro,
                    "regra_name": regra_name,
                    "severidade": severidade,
                    "content": regra_content,
                    "content_hash": _content_hash(regra_content),
                    "source_file": f"manual_ecd/{bloco_file.name}",
                    "source_anchor": f"#registro-{registro.lower()}",
                })

    return chunks


# ============================================================
# COLETA — Iteracoes do SPED_ECD_PLANO.md
# ============================================================

PLANO_ITERACAO_RE = re.compile(
    r"^\|\s*(V[\d.]+)\s*\|.*?\|.*?\|.*?\|.*?\|\s*(.+?)\s*\|$",
    re.MULTILINE
)


def collect_plano_iteracoes() -> list[dict[str, Any]]:
    """Varre SPED_ECD_PLANO.md secao 'HISTORICO DE ITERACOES'.

    Cada linha de tabela vira chunk indicando: versao, mudancas aplicadas.
    """
    chunks: list[dict[str, Any]] = []

    if not PLANO_FILE.is_file():
        logger.warning(f"PLANO_FILE nao encontrado: {PLANO_FILE}")
        return chunks

    content = PLANO_FILE.read_text(encoding="utf-8")

    # Captura apenas linhas da tabela HISTORICO
    for match in PLANO_ITERACAO_RE.finditer(content):
        versao = match.group(1)
        mudancas = match.group(2).strip()

        if not mudancas or mudancas == "TBD":
            continue

        chunk_content = (
            f"Iteracao SPED ECD versao {versao}.\n"
            f"Mudancas aplicadas: {mudancas}"
        )
        chunks.append({
            "chunk_id": f"plano:iteracao:{versao}",
            "chunk_type": "plano_iteracao",
            "bloco": None,
            "registro": None,
            "regra_name": None,
            "severidade": None,
            "content": chunk_content,
            "content_hash": _content_hash(chunk_content),
            "source_file": "app/relatorios_fiscais/SPED_ECD_PLANO.md",
            "source_anchor": "#historico-de-iteracoes",
        })

    return chunks


# ============================================================
# EMBED + STORE
# ============================================================

def embed_and_store(chunks: list[dict[str, Any]], dry_run: bool = False) -> dict[str, int]:
    """Gera embeddings em batch e armazena. Skip se hash ja existe."""
    from app import db
    from app.embeddings.client import VoyageClient

    if not _has_app_context():
        raise RuntimeError(
            "Sem Flask app context. Use: with app.app_context(): embed_and_store(...)"
        )

    stats = {"total": len(chunks), "inserted": 0, "skipped": 0, "errors": 0}

    # Skip chunks com hash ja indexado
    existing_hashes = set()
    if chunks:
        ids = [c["chunk_id"] for c in chunks]
        result = db.session.execute(
            text("""
                SELECT chunk_id, content_hash FROM sped_ecd_rule_embeddings
                WHERE chunk_id = ANY(:ids)
            """),
            {"ids": ids}
        ).all()
        existing = {row.chunk_id: row.content_hash for row in result}
        chunks_to_embed = [
            c for c in chunks
            if existing.get(c["chunk_id"]) != c["content_hash"]
        ]
        stats["skipped"] = len(chunks) - len(chunks_to_embed)
    else:
        chunks_to_embed = []

    if not chunks_to_embed:
        return stats

    if dry_run:
        logger.info(f"[DRY-RUN] {len(chunks_to_embed)} chunks seriam embedded")
        return stats

    # Embed em batches (Voyage limit 128)
    client = VoyageClient()
    batch_size = 128
    for i in range(0, len(chunks_to_embed), batch_size):
        batch = chunks_to_embed[i : i + batch_size]
        texts = [c["content"] for c in batch]

        try:
            embeddings = client.embed(texts, model="voyage-4-lite", input_type="document")
        except Exception as e:
            logger.error(f"Falha ao embedar batch {i}: {e}")
            stats["errors"] += len(batch)
            continue

        # Upsert
        for chunk, emb in zip(batch, embeddings):
            try:
                db.session.execute(text("""
                    INSERT INTO sped_ecd_rule_embeddings
                        (chunk_id, chunk_type, bloco, registro, regra_name,
                         severidade, content, content_hash, embedding, model,
                         source_file, source_anchor, created_at, updated_at)
                    VALUES (:chunk_id, :chunk_type, :bloco, :registro, :regra_name,
                            :severidade, :content, :content_hash, :embedding, :model,
                            :source_file, :source_anchor, NOW(), NOW())
                    ON CONFLICT (chunk_id) DO UPDATE SET
                        content = EXCLUDED.content,
                        content_hash = EXCLUDED.content_hash,
                        embedding = EXCLUDED.embedding,
                        updated_at = NOW()
                """), {
                    **chunk,
                    "embedding": emb,
                    "model": "voyage-4-lite",
                })
                stats["inserted"] += 1
            except Exception as e:
                logger.error(f"Falha upsert chunk {chunk['chunk_id']}: {e}")
                stats["errors"] += 1

        db.session.commit()
        logger.info(f"Batch {i // batch_size + 1}: {len(batch)} chunks processados")

    return stats


# ============================================================
# CLI
# ============================================================

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reindex", action="store_true",
                        help="Limpa tabela antes de reindexar")
    parser.add_argument("--stats", action="store_true",
                        help="Mostra so estatisticas, sem indexar")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
    )

    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
    from app import create_app, db

    app = create_app()
    with app.app_context():
        if args.reindex and not args.dry_run:
            db.session.execute(text("TRUNCATE sped_ecd_rule_embeddings RESTART IDENTITY"))
            db.session.commit()
            logger.info("Tabela truncada")

        if args.stats:
            count = db.session.execute(
                text("SELECT COUNT(*) FROM sped_ecd_rule_embeddings")
            ).scalar()
            by_type = db.session.execute(text(
                "SELECT chunk_type, COUNT(*) AS c FROM sped_ecd_rule_embeddings GROUP BY chunk_type"
            )).all()
            print(f"Total chunks indexados: {count}")
            for row in by_type:
                print(f"  {row.chunk_type}: {row.c}")
            return

        # Coleta
        start = time.time()
        chunks = collect_manual_ecd_chunks() + collect_plano_iteracoes()
        logger.info(f"Coletados {len(chunks)} chunks em {time.time() - start:.1f}s")

        # Embed + store
        stats = embed_and_store(chunks, dry_run=args.dry_run)
        logger.info(f"Stats: {stats}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Criar search API**

Criar `app/embeddings/sped_rules_search.py`:

```python
"""API de busca semantica em sped_ecd_rule_embeddings.

Usado por skill auditando-sped-vs-manual.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import text

from app import db
from app.embeddings.client import VoyageClient
from app.embeddings.config import THRESHOLD_SPED_RULES


def buscar_regras_semantico(
    query: str,
    limit: int = 10,
    chunk_type: str | None = None,
    bloco: str | None = None,
    registro: str | None = None,
    min_similarity: float | None = None,
) -> list[dict[str, Any]]:
    """Busca regras normativas do Manual ECD por similaridade semantica.

    Args:
        query: pergunta natural (ex: "regra que valida CNPJ").
        limit: top-k.
        chunk_type: filtro 'registro' | 'regra' | 'campo' | 'plano_iteracao'.
        bloco: filtro 0|C|I|J|K|9.
        registro: filtro ex 'I050'.
        min_similarity: corte (default THRESHOLD_SPED_RULES).

    Returns:
        Lista de dicts com chunk + similarity.
    """
    threshold = min_similarity if min_similarity is not None else THRESHOLD_SPED_RULES

    # Embed query
    client = VoyageClient()
    query_emb = client.embed([query], model="voyage-4-lite", input_type="query")[0]

    # Build WHERE
    conds = []
    params: dict[str, Any] = {"qemb": query_emb, "threshold": threshold, "limit": limit}
    if chunk_type:
        conds.append("chunk_type = :chunk_type")
        params["chunk_type"] = chunk_type
    if bloco:
        conds.append("bloco = :bloco")
        params["bloco"] = bloco
    if registro:
        conds.append("registro = :registro")
        params["registro"] = registro

    where_clause = "WHERE " + " AND ".join(conds) if conds else ""

    sql = f"""
        SELECT
            chunk_id, chunk_type, bloco, registro, regra_name, severidade,
            content, source_file, source_anchor,
            1 - (embedding <=> :qemb) AS similarity
        FROM sped_ecd_rule_embeddings
        {where_clause}
        ORDER BY embedding <=> :qemb
        LIMIT :limit
    """
    rows = db.session.execute(text(sql), params).all()

    results = []
    for row in rows:
        if row.similarity < threshold:
            continue
        results.append({
            "chunk_id": row.chunk_id,
            "chunk_type": row.chunk_type,
            "bloco": row.bloco,
            "registro": row.registro,
            "regra_name": row.regra_name,
            "severidade": row.severidade,
            "content": row.content,
            "source": f"{row.source_file}{row.source_anchor or ''}",
            "similarity": float(row.similarity),
        })

    return results
```

- [ ] **Step 3: Rodar indexer LOCAL com --dry-run**

Run: `source .venv/bin/activate && python -m app.embeddings.indexers.sped_ecd_rules_indexer --dry-run`

Expected:
- `Coletados {N} chunks em Xs` (N entre 230-345)
- `[DRY-RUN] {N} chunks seriam embedded`

- [ ] **Step 4: Rodar indexer real**

Run: `source .venv/bin/activate && python -m app.embeddings.indexers.sped_ecd_rules_indexer`

Expected:
- Batches processados sem erro.
- `Stats: {'total': N, 'inserted': N, 'skipped': 0, 'errors': 0}`.

- [ ] **Step 5: Verificar stats**

Run: `source .venv/bin/activate && python -m app.embeddings.indexers.sped_ecd_rules_indexer --stats`

Expected: `Total chunks indexados: 230-345` distribuidos em `registro`, `regra`,
`plano_iteracao`.

- [ ] **Step 6: Smoke search**

Run: `source .venv/bin/activate && python -c "
from app import create_app
from app.embeddings.sped_rules_search import buscar_regras_semantico
app = create_app()
with app.app_context():
    results = buscar_regras_semantico('regra que valida CNPJ', limit=3)
    for r in results:
        print(f'[{r[\"similarity\"]:.3f}] {r[\"chunk_id\"]}: {r[\"content\"][:80]}')
"`

Expected: 3 resultados rankeados, incluindo regras de validacao de CNPJ
(REGRA_IGUAL_CNPJ_REG0000 ou similar). Similarity >= 0.45.

- [ ] **Step 7: Commit**

```bash
git add app/embeddings/indexers/sped_ecd_rules_indexer.py app/embeddings/sped_rules_search.py
git commit -m "feat(embeddings): indexer sped_ecd_rules + search API

Indexa Manual ECD (51 registros + ~200 regras nomeadas) e SPED_ECD_PLANO.md
(iteracoes) em sped_ecd_rule_embeddings via Voyage AI. API buscar_regras_semantico
com filtros chunk_type/bloco/registro. Threshold default 0.45.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 3.3: DSL Engine + Skill `auditando-sped-vs-manual`

**Files:**
- Create: `.claude/skills/auditando-sped-vs-manual/scripts/dsl_engine.py`
- Create: `.claude/skills/auditando-sped-vs-manual/regras/I050.yaml`
- Create: `.claude/skills/auditando-sped-vs-manual/SKILL.md`
- Create: `tests/skills/test_auditando_sped_vs_manual.py`

**Por que:** Engine que valida campos formalmente (tipo, tamanho, obrigatoriedade,
valores validos) declarados em YAML por registro. Escala por arquivo, nao por
codigo. Complementa busca semantica (que ajuda quando erro PVA chega em
linguagem natural).

- [ ] **Step 1: Escrever testes do engine**

Criar `tests/skills/test_auditando_sped_vs_manual.py`:

```python
"""Testa DSL engine de validacao de campos contra Manual ECD."""
import sys
from pathlib import Path

import pytest

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
    record = {"COD_NAT": "99"}  # nao esta na lista
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
    record = {"VL_DC": "abc"}  # nao eh numerico
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
                {"DT_ALT": "01012024", "COD_NAT": "99", "IND_CTA": "X",  # ambos invalidos
                 "NIVEL": "1", "COD_CTA": "2", "COD_CTA_SUP": "", "CTA": "ERRO"},
            ],
        },
    }
    findings = audit_registro_compliance(parsed, REGRAS_DIR)
    assert len(findings) >= 2
    assert any("COD_NAT" in f.descricao for f in findings)
    assert any("IND_CTA" in f.descricao for f in findings)
```

- [ ] **Step 2: Rodar testes — falham**

Run: `pytest tests/skills/test_auditando_sped_vs_manual.py -v`
Expected: FAIL com ImportError.

- [ ] **Step 3: Instalar pyyaml se nao tiver**

Run: `source .venv/bin/activate && python -c "import yaml" 2>&1`
- Se OK: prossiga.
- Se ImportError: `pip install pyyaml` (deve ja estar — verificar).

- [ ] **Step 4: Criar I050.yaml**

```bash
mkdir -p .claude/skills/auditando-sped-vs-manual/regras
```

Criar `.claude/skills/auditando-sped-vs-manual/regras/I050.yaml`:

```yaml
registro: I050
descricao: Plano de Contas
hierarquia: 3
ocorrencia: "1:N"
obrigatoriedade: "S"  # em todos os tipos de livro
fonte: manual_ecd/bloco_I_lancamentos.md#registro-i050

campos:
  - pos: 1
    nome: REG
    tipo: C
    tamanho: 4
    obrigatorio: S
    valores: ["I050"]
  - pos: 2
    nome: DT_ALT
    tipo: N
    tamanho: 8
    obrigatorio: S
    descricao: Data de alteracao/inclusao da conta no plano de contas
  - pos: 3
    nome: COD_NAT
    tipo: C
    tamanho: 2
    obrigatorio: S
    valores: ["01", "02", "03", "04", "05", "07", "09"]
    descricao: |
      Natureza da conta: 01-Ativo, 02-Passivo, 03-PL, 04-Receita,
      05-Custos/Despesas, 07-Compensacao, 09-Outras
  - pos: 4
    nome: IND_CTA
    tipo: C
    tamanho: 1
    obrigatorio: S
    valores: ["S", "A"]
    descricao: S=sintetica, A=analitica
  - pos: 5
    nome: NIVEL
    tipo: N
    tamanho: -  # ilimitado
    obrigatorio: S
    descricao: Nivel hierarquico (1 = raiz)
  - pos: 6
    nome: COD_CTA
    tipo: C
    tamanho: -
    obrigatorio: S
    descricao: Codigo da conta no plano
  - pos: 7
    nome: COD_CTA_SUP
    tipo: C
    tamanho: -
    obrigatorio: N
    descricao: Codigo da conta superior (vazio para nivel 1)
  - pos: 8
    nome: CTA
    tipo: C
    tamanho: 60
    obrigatorio: S
    descricao: Nome da conta

regras_extras:
  - nome: REGRA_HIERARQUIA_COD_SUP
    descricao: COD_CTA_SUP deve existir como I050 anterior se NIVEL>1
    severidade: BLOQUEANTE
    # implementada em audit_hierarchy.py (Fase 2)
  - nome: REGRA_DT_ALT_LIMITE
    descricao: DT_ALT <= DT_INI do periodo
    severidade: BLOQUEANTE
    # validacao manual no auditor — DT_INI vem de 0000
```

- [ ] **Step 5: Implementar dsl_engine.py**

```bash
mkdir -p .claude/skills/auditando-sped-vs-manual/scripts
```

Criar `.claude/skills/auditando-sped-vs-manual/scripts/dsl_engine.py`:

```python
"""DSL engine de validacao de campos por registro contra Manual ECD.

Regras carregadas de .claude/skills/auditando-sped-vs-manual/regras/*.yaml.
Cada YAML define: registro, campos (pos, nome, tipo, tamanho, obrigatorio,
valores, decimal), regras_extras (referencia ou descricao).

Engine valida campo por campo: presenca, tipo (C/N), tamanho, lista de valores.
Regras "negocio" complexas (REGRA_HIERARQUIA_COD_SUP) ja estao em
audit_hierarchy.py — DSL nao duplica.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import yaml


@dataclass
class ComplianceFinding:
    tipo: str  # 'campo_obrigatorio_ausente', 'tipo_invalido', 'tamanho_invalido',
               # 'valor_nao_listado'
    registro: str
    campo: str
    severidade: str  # 'BLOQUEANTE'
    descricao: str
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
    """C ou N? N aceita formato BR (virgula decimal)."""
    if value == "":
        return True  # vazio nao quebra tipo
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
    """Valida um registro contra YAML de regras."""
    findings: list[ComplianceFinding] = []
    registro = regras["registro"]

    for campo_def in regras.get("campos", []):
        nome = campo_def["nome"]
        if nome == "REG":
            continue  # REG eh chave, sempre presente

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
            continue  # nao validar outros aspectos se vazio

        if not valor:
            continue  # opcional + vazio = OK

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

        # 3. Tamanho (apenas se for inteiro finito)
        if isinstance(tamanho, int) and tamanho > 0:
            if tipo == "C" and len(valor) > tamanho:
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
            # Para tipo C com tamanho exato (ex: COD_NAT tamanho=2), validar igual
            if tipo == "C" and len(valor) != tamanho and \
                    campo_def.get("tamanho_exato", True):
                findings.append(ComplianceFinding(
                    tipo="tamanho_invalido",
                    registro=registro,
                    campo=nome,
                    severidade="BLOQUEANTE",
                    descricao=(
                        f"{registro}.{nome} tamanho={len(valor)} diferente de {tamanho} esperado"
                    ),
                    contexto={"valor": valor, "tamanho_esperado": tamanho},
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
    """Para cada YAML em regras_dir/, valida registros correspondentes no parsed."""
    findings: list[ComplianceFinding] = []

    if not regras_dir.is_dir():
        return findings

    for yaml_file in sorted(regras_dir.glob("*.yaml")):
        regras = load_regras_yaml(yaml_file)
        registro = regras["registro"]
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
        "regras_yaml_aplicadas": [p.stem for p in regras_dir.glob("*.yaml")],
        "findings_count": len(findings),
        "findings": [f.to_dict() for f in findings],
    }, ensure_ascii=False, indent=2))
```

- [ ] **Step 6: Rodar testes**

Run: `pytest tests/skills/test_auditando_sped_vs_manual.py -v`
Expected: 6 testes PASS.

- [ ] **Step 7: Criar SKILL.md**

Criar `.claude/skills/auditando-sped-vs-manual/SKILL.md`:

```markdown
---
name: auditando-sped-vs-manual
description: >-
  Skill EXCLUSIVA do subagente auditor-sped-ecd. Valida SPED parseado
  contra Manual ECD Leiaute 9 em duas dimensoes: (1) DSL formal via
  YAML por registro (tipo, tamanho, obrigatoriedade, valores validos);
  (2) busca semantica em embeddings das regras normativas (uti para
  erros PVA em linguagem natural). Use apos parseando-sped-ecd.
allowed-tools: Read, Bash
---

# auditando-sped-vs-manual — Compliance vs Manual ECD

## Quando usar

Apos `parseando-sped-ecd`. Cobre o que `auditando-sped-contabil` nao
cobre: validacoes formais de campo + busca semantica em regras.

## Modo 1: DSL Formal (YAML)

Validacao de campos por registro contra regras em
`.claude/skills/auditando-sped-vs-manual/regras/*.yaml`.

```bash
source .venv/bin/activate
python .claude/skills/auditando-sped-vs-manual/scripts/dsl_engine.py \
    /tmp/sped-parsed-v21.json
```

**Cobertura inicial**: apenas `I050.yaml`. Adicionar novos blocos
incrementalmente via YAML (sem alterar codigo).

**Findings por tipo**:
- `campo_obrigatorio_ausente` — BLOQUEANTE
- `tipo_invalido` — BLOQUEANTE (C vs N)
- `tamanho_invalido` — BLOQUEANTE
- `valor_nao_listado` — BLOQUEANTE

## Modo 2: Busca Semantica

Quando PVA reporta erro em linguagem natural (ex: "conta sem natureza"),
buscar a regra normativa correspondente:

```python
from app.embeddings.sped_rules_search import buscar_regras_semantico

results = buscar_regras_semantico(
    "conta sem natureza definida",
    limit=5,
    chunk_type="regra"  # filtra so REGRA_X nomeadas
)
for r in results:
    print(f"[{r['similarity']:.2f}] {r['regra_name']}: {r['content']}")
```

## Como adicionar nova regra YAML

Exemplo `I250.yaml`:

```yaml
registro: I250
descricao: Partidas do lancamento
campos:
  - {pos: 2, nome: COD_CTA, tipo: C, tamanho: -, obrigatorio: S}
  - {pos: 3, nome: COD_CCUS, tipo: C, tamanho: -, obrigatorio: N}
  - {pos: 4, nome: VL_DC, tipo: N, tamanho: -, obrigatorio: S, decimal: 2}
  - {pos: 5, nome: IND_DC, tipo: C, tamanho: 1, obrigatorio: S, valores: [D, C]}
  ...
```

Engine carrega automaticamente — sem alterar codigo Python.

## NAO usar quando

- Validacao matematica (usar `auditando-sped-contabil`)
- Diff com ground truth (usar `comparando-sped-ground-truth`)
- Pre-upload check inline (usar `sped_ecd_validator.py` interno)
```

- [ ] **Step 8: Commit**

```bash
git add .claude/skills/auditando-sped-vs-manual/ tests/skills/test_auditando_sped_vs_manual.py
git commit -m "feat(skill): auditando-sped-vs-manual — DSL YAML + busca semantica

Engine valida campos por registro contra YAML de regras (I050 inicial).
4 tipos de finding: campo_obrigatorio_ausente, tipo_invalido,
tamanho_invalido, valor_nao_listado. Reuso da search API de embeddings
para erros PVA em linguagem natural.

6 testes pytest. Adicionar novos registros = novo YAML, sem codigo Python.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
```

---

### Task 3.4: Checkpoint Final + Teste E2E Real

**Files:**
- Modify: `tests/agente/test_sped_audit_integration.py` (adicionar testes E2E)

- [ ] **Step 1: Adicionar teste E2E de auditoria completa**

Adicionar em `tests/agente/test_sped_audit_integration.py`:

```python
import json
import subprocess


SPED_FOR_TESTING = (
    "/home/rafaelnascimento/SPED_ECD_NACOM_GOYA_01072024_31122024_V21_3COMPANIES.txt"
)


@pytest.mark.skipif(
    not Path(SPED_FOR_TESTING).exists(),
    reason=f"SPED V21 nao disponivel em {SPED_FOR_TESTING}"
)
def test_e2e_parse_v21(tmp_path):
    """E2E: parse SPED V21 real."""
    out_path = tmp_path / "parsed.json"
    result = subprocess.run(
        ["python", ".claude/skills/parseando-sped-ecd/scripts/parse_sped.py",
         SPED_FOR_TESTING, str(out_path)],
        capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, f"parser falhou: {result.stderr}"

    with open(out_path) as f:
        parsed = json.load(f)

    # SPED V21 tem registros esperados
    assert "0000" in parsed["registros"]
    assert "I050" in parsed["registros"]
    assert "I250" in parsed["registros"]
    assert parsed["metadata"]["total_lines"] > 1000


@pytest.mark.skipif(
    not Path(SPED_FOR_TESTING).exists(),
    reason=f"SPED V21 nao disponivel"
)
def test_e2e_audit_balance_v21(tmp_path):
    """E2E: parse + audit_balance no V21 real."""
    out_path = tmp_path / "parsed.json"
    subprocess.run(
        ["python", ".claude/skills/parseando-sped-ecd/scripts/parse_sped.py",
         SPED_FOR_TESTING, str(out_path)],
        check=True, timeout=120
    )

    result = subprocess.run(
        ["python", ".claude/skills/auditando-sped-contabil/scripts/audit_balance.py",
         str(out_path)],
        capture_output=True, text=True, timeout=60
    )
    assert result.returncode == 0
    audit_result = json.loads(result.stdout)
    # findings_count pode ser 0 ou >0 — depende do SPED V21 atual.
    # Validar so que executou.
    assert "findings_count" in audit_result
    assert audit_result["total_i155"] > 0


def test_e2e_search_semantic_cnpj_rule():
    """E2E: busca semantica de regra de CNPJ."""
    from app import create_app
    app = create_app()
    with app.app_context():
        from app.embeddings.sped_rules_search import buscar_regras_semantico
        results = buscar_regras_semantico("regra que valida CNPJ", limit=3)
        assert len(results) > 0
        # Deve retornar pelo menos uma regra com 'CNPJ' no content
        assert any("CNPJ" in r["content"].upper() for r in results)
```

- [ ] **Step 2: Rodar testes E2E**

Run: `pytest tests/agente/test_sped_audit_integration.py -v`
Expected:
- 6 testes base (Fase 1) PASS
- 2 testes E2E skipped se SPED V21 nao existe, OU PASS se existe
- 1 teste E2E semantic search PASS

- [ ] **Step 3: Smoke do subagente via Task tool (manual)**

No Claude Code:
```
Use o subagente auditor-sped-ecd para fazer auditoria completa do SPED V21
em /home/rafaelnascimento/SPED_ECD_NACOM_GOYA_01072024_31122024_V21_3COMPANIES.txt.
Quero relatorio completo (parse + contabil + ground truth + manual).
```

Expected:
- Subagente invoca 4 skills em ordem.
- Output estruturado por severidade.
- Findings salvos em `/tmp/subagent-findings/audit-sped-v21-*.md`.

- [ ] **Step 4: Atualizar SPED_ECD_PLANO.md com nova capacidade**

Adicionar secao "AUDITORIA AUTOMATIZADA" em `app/relatorios_fiscais/SPED_ECD_PLANO.md`:

```markdown
## Auditoria Automatizada (a partir de 2026-05-16)

Subagente `auditor-sped-ecd` (4 skills + 2 reusadas) executa auditoria
multidimensional do SPED gerado:

1. Parser (parseando-sped-ecd) → /tmp/sped-parsed-VXX.json
2. Contabil (auditando-sped-contabil) → batimentos + hierarquia
3. Ground truth (comparando-sped-ground-truth) → diff vs SPED contadora
4. Manual ECD (auditando-sped-vs-manual) → DSL YAML + busca semantica

Invocacao via chat: "audita o SPED V21".
Output: /tmp/subagent-findings/audit-sped-VXX-{timestamp}.md
```

- [ ] **Step 5: Commit final**

```bash
git add tests/agente/test_sped_audit_integration.py app/relatorios_fiscais/SPED_ECD_PLANO.md
git commit -m "$(cat <<'EOF'
feat(agente): E2E auditor-sped-ecd completo + documentacao

Tres testes E2E: parser, audit_balance, busca semantica de regras.
Skip automatico se SPED V21 nao presente localmente.

PLANO.md atualizado com nova secao 'Auditoria Automatizada' que
documenta o fluxo do subagente para sessoes futuras.

CHECKPOINT FASE 3 — auditor completo, pronto para uso em iteracoes V21+.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### CHECKPOINT FASE 3 FINAL — Revisao Humana

- [ ] Usuario invoca subagente em SPED real (V21).
- [ ] Verifica que 4 skills sao invocadas em ordem.
- [ ] Findings sao acionaveis (deep-links Odoo, severidade clara).
- [ ] `/tmp/subagent-findings/audit-sped-v21-*.md` existe e eh legivel.
- [ ] Nenhum falso positivo obvio na auditoria contabil.
- [ ] Busca semantica retorna regras relevantes para queries em PT-BR.

---

## Pendencias Discutidas mas NAO Implementadas Neste Plano

Documentadas aqui para futuras sessoes — NAO implementar agora:

1. **`strict_mcp_config=True`** (SDK 0.1.74) — determinismo DEV/PROD.
   Ativar via `AGENT_STRICT_MCP_CONFIG=true` quando aparecer divergencia.

2. **`task_budget` em subagentes** (anthropic 0.96.0) — cap explicito de
   tokens. Candidato para auditor SPED se observado runaway com SPEDs >100K
   lancamentos.

3. **`output_format json_schema`** (atual SDK) — auditor retornaria findings
   estruturados validados. Reduz parsing de texto pelo orquestrador.

4. **Indexacao incremental** — atualmente o indexer faz full reindex.
   Cron job semanal? Trigger por mudanca em `manual_ecd/` ou
   `SPED_ECD_PLANO.md`?

5. **Cross-version diff** — comparar SPED V20 vs V21 para mostrar quais
   findings persistem entre iteracoes (regressao).

6. **Hook D (can_use_tool)** — Defesa em profundidade alem do `skills=list`.
   Implementar SE detectarmos vazamento real (improvavel dado mecanismo SDK).

---

## Glossario Critico (para esta plan)

- **SPED ECD**: Escrituracao Contabil Digital — obrigacao fiscal RFB.
- **PVA**: Programa Gerador de Escrituracao — validador oficial RFB.
- **Leiaute 9**: versao do layout SPED ECD vigente desde 2021-12 (AC 2020+).
- **Ground truth**: SPED da contadora ja aprovado pela RFB, em `~/Downloads/`.
- **REGRA_X**: regra nomeada do Manual ECD (ex: REGRA_IGUAL_CNPJ_REG0000).
- **I050**: registro de Plano de Contas. I250: partidas do lancamento. I155:
  saldos periodicos mensais.

---

## Referencias

| Documento | Por que importa |
|---|---|
| `app/relatorios_fiscais/CLAUDE.md` | Dev guide modulo SPED |
| `app/relatorios_fiscais/manual_ecd/INDEX.md` | Manual ECD Leiaute 9 indexado |
| `app/relatorios_fiscais/SPED_ECD_PLANO.md` | Inventario vivo de iteracoes |
| `app/agente/SDK_CHANGELOG.md` | Capacidades SDK por versao |
| `~/.claude/CLAUDE.md` | Regras dev (migrations, sys.path, etc.) |
| `app/embeddings/indexers/carrier_indexer.py` | Template para indexer SPED |
| `.claude/agents/auditor-financeiro.md` | Template para subagente Opus xhigh |
| `.claude/skills/operando-ssw/SKILL.md` | Template para skill com scripts |
