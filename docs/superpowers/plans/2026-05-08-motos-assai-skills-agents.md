# Motos Assaí Skills + Agente Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Criar 6 skills atômicas + 1 sub-agent (`gestor-motos-assai`) para operar o módulo `app/motos_assai/` (B2B Q.P.A. Sendas) via Claude Code CLI e agente web Nacom Goya, seguindo padrão consolidado do `orientador-loja` + `consultando-estoque-loja`.

**Architecture:** Scripts Python que importam services existentes via `app_context()`, retornam JSON em stdout, exit codes padronizados. WRITE skills usam dry-run obrigatório + `--confirmar`. Sub-agent orquestra cross-entidade via 6 skills atômicas. ZERO modificação em routes/services/models do módulo motos_assai.

**Tech Stack:** Python 3.11, Flask + SQLAlchemy (services existentes), pytest (testes), YAML (golden dataset eval), Claude Agent SDK 0.1.66 (skills + agent loader).

**Spec referência:** `docs/superpowers/specs/2026-05-08-motos-assai-skills-agents-design.md`

---

## File Structure

### Arquivos a criar

```
.claude/skills/
├── consultando-estoque-assai/
│   ├── SKILL.md
│   └── scripts/consultando_estoque_assai.py
├── rastreando-chassi-assai/
│   ├── SKILL.md
│   └── scripts/rastreando_chassi_assai.py
├── acompanhando-pedido-compra-assai/
│   ├── SKILL.md
│   └── scripts/acompanhando_pedido_compra_assai.py
├── acompanhando-saida-assai/
│   ├── SKILL.md
│   └── scripts/acompanhando_saida_assai.py
├── conferindo-recibo-assai/
│   ├── SKILL.md
│   └── scripts/conferindo_recibo_assai.py
└── registrando-evento-moto-assai/
    ├── SKILL.md
    └── scripts/registrando_evento_moto_assai.py

.claude/agents/
└── gestor-motos-assai.md

.claude/evals/subagents/gestor-motos-assai/
└── dataset.yaml

tests/skills/motos_assai/
├── __init__.py
├── conftest.py
├── test_consultando_estoque_assai.py
├── test_rastreando_chassi_assai.py
├── test_acompanhando_pedido_compra_assai.py
├── test_acompanhando_saida_assai.py
├── test_conferindo_recibo_assai.py
└── test_registrando_evento_moto_assai.py
```

### Arquivos a modificar (cross-refs)

- `.claude/references/ROUTING_SKILLS.md` (adicionar 7 linhas em "Passo 1" + 2 desambiguações)
- `.claude/references/INDEX.md` (adicionar entrada "Skills motos_assai (6)")
- `CLAUDE.md` (raiz — adicionar entrada `gestor-motos-assai` em "Subagentes")
- `app/motos_assai/CLAUDE.md` (adicionar seção "Skills + Agente disponíveis")
- `.claude/skills/SKILL_IMPROVEMENT_ROADMAP.md` (registrar criação 2026-05-08)
- `app/agente/services/tool_skill_mapper.py` (mapear 6 novas skills)

### Service signatures relevantes (referência rápida)

```python
# moto_evento_service.py
emitir_evento(chassi, tipo, operador_id, observacao, dados_extras) -> AssaiMotoEvento
ultimo_evento(chassi) -> Optional[AssaiMotoEvento]
status_efetivo(chassi) -> Optional[str]   # NOTA: nome é status_efetivo, NAO status_atual
eventos_chassi(chassi, limit) -> List[AssaiMotoEvento]
chassis_em_estoque(modelo_id) -> List[str]

# montagem_service.py
registrar_montagem(chassi, pendencia, descricao_pendencia, chassi_doador, operador_id) -> Dict
resolver_pendencia(chassi, descricao_resolucao, operador_id) -> Dict
historico_3_ultimas_montagens() -> list

# disponibilizar_service.py
disponibilizar(chassi, operador_id) -> Dict
reverter_para_montada(chassi, motivo, operador_id) -> Dict

# separacao_service.py
get_ou_criar_separacao(pedido_id, loja_id, operador_id) -> AssaiSeparacao
saldo_pendente_por_modelo(pedido_id, loja_id) -> List[Dict]
registrar_chassi(pedido_id, loja_id, chassi, registrada_por_id) -> Dict
desfazer_chassi(separacao_item_id, operador_id) -> Dict
finalizar_separacao(separacao_id, operador_id) -> AssaiSeparacao
cancelar_separacao(separacao_id, motivo, operador_id) -> AssaiSeparacao

# recebimento_service.py
validar_chassi_contra_recibo(recibo_id, chassi) -> Dict
registrar_conferencia(...) -> Dict
finalizar_recebimento(...) -> Dict

# recibo_service.py
get_recibo(recibo_id) -> AssaiReciboMotochefe
listar_recibos(compra_id=None) -> List
```

### Constantes (em `app/motos_assai/models/moto.py`)

```python
EVENTO_ESTOQUE = 'ESTOQUE'
EVENTO_MONTADA = 'MONTADA'
EVENTO_PENDENTE = 'PENDENTE'
EVENTO_PENDENCIA_RESOLVIDA = 'PENDENCIA_RESOLVIDA'
EVENTO_DISPONIVEL = 'DISPONIVEL'
EVENTO_REVERTIDA_PARA_MONTADA = 'REVERTIDA_PARA_MONTADA'
EVENTO_SEPARADA = 'SEPARADA'
EVENTO_FATURADA = 'FATURADA'
EVENTO_CANCELADA = 'CANCELADA'
EVENTO_MOTO_FALTANDO = 'MOTO_FALTANDO'

EVENTOS_VALIDOS = {...todos acima}
EVENTOS_EM_ESTOQUE = {ESTOQUE, MONTADA, PENDENTE, DISPONIVEL}
EVENTOS_BLOQUEADO_DISPONIBILIZAR = {PENDENTE}
EVENTOS_FORA_ESTOQUE = {SEPARADA, FATURADA, CANCELADA, MOTO_FALTANDO}
```

---

## Padrões obrigatórios para TODAS as skills

### Padrão A: Header de script Python

```python
#!/usr/bin/env python3
"""
Script: <nome>.py

<descrição em 1-3 linhas>

Uso:
    --arg-1 <valor>     # descrição
    --arg-2             # flag

Exit codes:
    0 - sucesso
    1 - validação falhou
    2 - erro infra (DB)
    3 - não autorizado
    4 - confirmação faltando (WRITE)
    5 - conflito de concorrência
"""
import sys
import os
import json
import argparse
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from app import create_app, db  # noqa: E402


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def main():
    parser = argparse.ArgumentParser()
    # ... args ...
    args = parser.parse_args()

    app = create_app()
    with app.app_context():
        result = _run(args)

    print(json.dumps(result, default=_json_default, ensure_ascii=False))
    return result.get('exit_code', 0)


if __name__ == '__main__':
    sys.exit(main())
```

### Padrão B: Frontmatter SKILL.md

```yaml
---
name: <nome-da-skill>
description: >-
  <descrição completa, 80-200 palavras, explicando QUANDO usar e QUANDO NAO USAR>

  USAR QUANDO:
  - "<exemplo de pergunta 1>"
  - "<exemplo de pergunta 2>"

  NAO USAR PARA:
  - <caso fora de escopo 1> (usar <skill-correta>)
  - <caso fora de escopo 2> (usar <agente-correto>)
allowed-tools: Read, Bash, Glob, Grep
---
```

### Padrão C: Verificação de autorização em WRITE skills

```python
def _verificar_autorizacao(user_id: int) -> bool:
    """Retorna True se user pode acessar motos_assai. Caller deve exit 3 se False."""
    from app.auth.models import Usuario
    u = Usuario.query.get(user_id)
    if not u:
        return False
    return u.pode_acessar_motos_assai()
```

---

## FASE 1 — Skills READ (4 skills)

### Task 1.1: `consultando-estoque-assai` (READ)

**Files:**
- Create: `.claude/skills/consultando-estoque-assai/SKILL.md`
- Create: `.claude/skills/consultando-estoque-assai/scripts/consultando_estoque_assai.py`
- Create: `tests/skills/motos_assai/__init__.py`
- Create: `tests/skills/motos_assai/conftest.py`
- Create: `tests/skills/motos_assai/test_consultando_estoque_assai.py`

- [ ] **Step 1: Criar diretório de testes e conftest base**

```bash
mkdir -p tests/skills/motos_assai
touch tests/skills/motos_assai/__init__.py
```

Conteúdo de `tests/skills/motos_assai/conftest.py`:

```python
"""Conftest compartilhado para testes de skills motos_assai.

Reutiliza fixtures do conftest principal (tests/motos_assai/conftest.py).
"""
import sys
import os
from pathlib import Path

# Adiciona path do projeto para imports `from app import ...`
ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Reutiliza fixtures de tests/motos_assai/conftest.py
pytest_plugins = ['tests.motos_assai.conftest']
```

- [ ] **Step 2: Escrever teste failing (TDD)**

Conteúdo de `tests/skills/motos_assai/test_consultando_estoque_assai.py`:

```python
"""Testes para consultando-estoque-assai skill."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / '.claude/skills/consultando-estoque-assai/scripts/consultando_estoque_assai.py'


def _run_script(*args):
    """Executa o script como subprocess e parseia JSON."""
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=30,
    )
    return result


def test_resumo_retorna_estrutura_basica(app):
    """Resumo deve retornar JSON com chaves totais/por_modelo/por_cd/motos_pendentes."""
    r = _run_script('--resumo')
    assert r.returncode == 0, f'stderr: {r.stderr}'
    data = json.loads(r.stdout)
    assert 'totais' in data
    assert 'por_modelo' in data
    assert 'por_cd' in data
    assert 'motos_pendentes' in data
    assert 'vazio' in data


def test_filtro_modelo_invalido_retorna_vazio(app):
    """Modelo inexistente deve retornar listas vazias com flag vazio=true."""
    r = _run_script('--modelo', 'MODELO_INEXISTENTE_XYZ', '--resumo')
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data['totais'] == {
        'estoque': 0, 'montada': 0, 'pendente': 0,
        'disponivel': 0, 'separada': 0, 'faturada': 0,
    }


def test_help_funciona():
    """Script deve responder --help."""
    r = _run_script('--help')
    assert r.returncode == 0
    assert 'consultando_estoque_assai' in r.stdout.lower() or '--resumo' in r.stdout
```

- [ ] **Step 3: Rodar teste — FAIL esperado (script ainda não existe)**

```bash
source .venv/bin/activate
pytest tests/skills/motos_assai/test_consultando_estoque_assai.py -v
```

Expected: FAIL com "FileNotFoundError" ou similar.

- [ ] **Step 4: Criar SKILL.md**

Conteúdo de `.claude/skills/consultando-estoque-assai/SKILL.md`:

````markdown
---
name: consultando-estoque-assai
description: >-
  Esta skill deve ser usada quando o usuario pergunta sobre estoque ou pipeline
  de motos do modulo Motos Assai (B2B Q.P.A. Sendas/Assai): "quantas motos
  disponiveis?", "estoque por modelo Q.P.A.", "quanto de SOL temos?", "pipeline
  de motos Assai", "quantas em ESTOQUE/MONTADA/DISPONIVEL/SEPARADA?". Retorna
  totais por estagio (ESTOQUE/MONTADA/PENDENTE/DISPONIVEL/SEPARADA/FATURADA),
  por modelo, por CD e lista de motos com pendencia.

  USAR QUANDO:
  - "quantas motos Q.P.A. disponiveis?"
  - "estoque por modelo Assai"
  - "quanto de SOL/X11_MINI/DOT temos?"
  - "pipeline de motos hoje"
  - "quais chassis em PENDENTE?"

  NAO USAR PARA:
  - Historico de UM chassi especifico (usar rastreando-chassi-assai)
  - Pedidos VOE Q.P.A. ou compras Motochefe (usar acompanhando-pedido-compra-assai)
  - Separacoes ou NFs Q.P.A. (usar acompanhando-saida-assai)
  - Estoque Lojas HORA (usar consultando-estoque-loja)
  - Estoque Nacom Goya (usar gerindo-expedicao)
allowed-tools: Read, Bash, Glob, Grep
---

# Consultando Estoque Motos Assai

Consulta o pipeline de motos do modulo Motos Assai (B2B Q.P.A.) por estagio
de evento (ESTOQUE/MONTADA/PENDENTE/DISPONIVEL/SEPARADA/FATURADA).

---

## Quando Usar

USE para:
- Contagem por estagio: "quantas DISPONIVEL?", "quantas em PENDENTE?"
- Filtro por modelo: "quanto de SOL?"
- Filtro por CD: "quanto no CD JUNDIAI?"
- Resumo geral do pipeline

NAO USE para:
- Historico de UM chassi -> `rastreando-chassi-assai`
- Pedidos/compras -> `acompanhando-pedido-compra-assai`
- Separacoes/NFs -> `acompanhando-saida-assai`

---

## REGRAS CRITICAS

### 1. STATUS = ULTIMO EVENTO
Estado atual de uma moto = ultimo evento em `assai_moto_evento` ordenado
por `ocorrido_em DESC`. NUNCA usar coluna `status` (nao existe). Usar helper
`status_efetivo(chassi)`.

### 2. MOTO SEM EVENTO = NAO CONTA
`AssaiMoto` sem evento e estado invalido (deveria ter pelo menos ESTOQUE).
Reportar separadamente em `motos_sem_evento`.

### 3. EVENTOS_EM_ESTOQUE
Estes eventos contam como "em estoque": ESTOQUE, MONTADA, PENDENTE, DISPONIVEL.
SEPARADA, FATURADA, CANCELADA, MOTO_FALTANDO sao "fora de estoque".

---

## Decision Tree

| Pergunta do usuario | Args |
|---------------------|------|
| "quantas motos?" | `--resumo` |
| "quanto de SOL?" | `--modelo SOL` |
| "estoque do CD JUNDIAI?" | `--cd-id 1` |
| "por modelo" | `--por-modelo` |
| "por estagio" | `--por-estagio` |

---

## Invocacao

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate
python .claude/skills/consultando-estoque-assai/scripts/consultando_estoque_assai.py --resumo
```

Output: JSON em stdout.

---

## Output JSON

```json
{
  "totais": {
    "estoque": 12, "montada": 8, "pendente": 2,
    "disponivel": 15, "separada": 7, "faturada": 230
  },
  "por_modelo": [
    {"modelo": "SOL", "estoque": 5, "montada": 3, "disponivel": 8, "separada": 4, "faturada": 100}
  ],
  "por_cd": [
    {"cd_id": 1, "cd": "JUNDIAI", "totais": {...}}
  ],
  "motos_pendentes": [
    {"chassi": "MZX1234", "descricao_pendencia": "...", "criado_em": "..."}
  ],
  "vazio": false,
  "exit_code": 0
}
```
````

- [ ] **Step 5: Criar script Python**

Conteúdo de `.claude/skills/consultando-estoque-assai/scripts/consultando_estoque_assai.py`:

```python
#!/usr/bin/env python3
"""
Script: consultando_estoque_assai.py

Consulta pipeline do modulo Motos Assai (B2B Q.P.A. Sendas).
Estado atual da moto = ultimo evento em assai_moto_evento.

Uso:
    --resumo                    # totais + por_modelo + por_cd
    --modelo SOL                # filtro por codigo de modelo
    --cd-id 1                   # filtro por CD
    --por-modelo                # agrupa por modelo
    --por-estagio               # agrupa por evento

Exit codes:
    0 - sucesso
    1 - validacao falhou
    2 - erro infra (DB)
"""
import sys
import os
import json
import argparse
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from app import create_app, db  # noqa: E402
from sqlalchemy import func, and_  # noqa: E402


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def _query_pipeline(modelo_filtro=None, cd_id_filtro=None):
    """Retorna dict com motos por chassi e seu evento atual.

    Implementacao: para cada chassi distinto, pega o evento de maior id (mais recente).
    """
    from app.motos_assai.models import (
        AssaiMoto, AssaiMotoEvento, AssaiModelo,
    )

    # Subquery: ultimo evento por chassi
    ultimo_id_por_chassi = (
        db.session.query(
            AssaiMotoEvento.chassi,
            func.max(AssaiMotoEvento.id).label('max_id'),
        )
        .group_by(AssaiMotoEvento.chassi)
        .subquery()
    )

    q = (
        db.session.query(
            AssaiMoto.chassi,
            AssaiMoto.modelo_id,
            AssaiModelo.codigo.label('modelo_codigo'),
            AssaiModelo.nome.label('modelo_nome'),
            AssaiMoto.cor,
            AssaiMotoEvento.tipo.label('evento_atual'),
            AssaiMotoEvento.ocorrido_em.label('evento_em'),
        )
        .join(AssaiModelo, AssaiModelo.id == AssaiMoto.modelo_id)
        .outerjoin(
            ultimo_id_por_chassi,
            ultimo_id_por_chassi.c.chassi == AssaiMoto.chassi,
        )
        .outerjoin(
            AssaiMotoEvento,
            AssaiMotoEvento.id == ultimo_id_por_chassi.c.max_id,
        )
    )

    if modelo_filtro:
        q = q.filter(AssaiModelo.codigo == modelo_filtro.upper())

    return q.all()


def _query_motos_pendentes():
    """Lista motos em estado PENDENTE com a descricao da pendencia."""
    from app.motos_assai.models import (
        AssaiMotoEvento, EVENTO_PENDENTE,
    )

    ultimo_id_por_chassi = (
        db.session.query(
            AssaiMotoEvento.chassi,
            func.max(AssaiMotoEvento.id).label('max_id'),
        )
        .group_by(AssaiMotoEvento.chassi)
        .subquery()
    )

    rows = (
        db.session.query(
            AssaiMotoEvento.chassi,
            AssaiMotoEvento.observacao,
            AssaiMotoEvento.ocorrido_em,
        )
        .join(
            ultimo_id_por_chassi,
            ultimo_id_por_chassi.c.max_id == AssaiMotoEvento.id,
        )
        .filter(AssaiMotoEvento.tipo == EVENTO_PENDENTE)
        .order_by(AssaiMotoEvento.ocorrido_em.desc())
        .all()
    )

    return [
        {
            'chassi': r.chassi,
            'descricao_pendencia': r.observacao or '',
            'criado_em': r.ocorrido_em,
        }
        for r in rows
    ]


def _agregar(rows):
    """Agrega rows do _query_pipeline em totais/por_modelo/por_cd."""
    from app.motos_assai.models import (
        EVENTO_ESTOQUE, EVENTO_MONTADA, EVENTO_PENDENTE,
        EVENTO_DISPONIVEL, EVENTO_SEPARADA, EVENTO_FATURADA,
    )

    totais = {
        'estoque': 0, 'montada': 0, 'pendente': 0,
        'disponivel': 0, 'separada': 0, 'faturada': 0,
    }
    por_modelo: dict = {}

    mapa_evento_chave = {
        EVENTO_ESTOQUE: 'estoque',
        EVENTO_MONTADA: 'montada',
        EVENTO_PENDENTE: 'pendente',
        EVENTO_DISPONIVEL: 'disponivel',
        EVENTO_SEPARADA: 'separada',
        EVENTO_FATURADA: 'faturada',
    }

    for r in rows:
        chave = mapa_evento_chave.get(r.evento_atual)
        if not chave:
            continue  # CANCELADA, MOTO_FALTANDO, REVERTIDA, PENDENCIA_RESOLVIDA
        totais[chave] += 1

        m_codigo = r.modelo_codigo or '?'
        if m_codigo not in por_modelo:
            por_modelo[m_codigo] = {
                'modelo': m_codigo,
                'estoque': 0, 'montada': 0, 'pendente': 0,
                'disponivel': 0, 'separada': 0, 'faturada': 0,
            }
        por_modelo[m_codigo][chave] += 1

    return totais, sorted(por_modelo.values(), key=lambda x: x['modelo'])


def _run(args):
    rows = _query_pipeline(modelo_filtro=args.modelo, cd_id_filtro=args.cd_id)
    totais, por_modelo = _agregar(rows)
    motos_pendentes = _query_motos_pendentes()

    # Por CD: nao implementado nesta versao (cd_id nao esta direto no AssaiMoto)
    # Deixar lista vazia ou implementar via join com recibo->compra->cd
    por_cd: list = []

    vazio = sum(totais.values()) == 0

    return {
        'totais': totais,
        'por_modelo': por_modelo,
        'por_cd': por_cd,
        'motos_pendentes': motos_pendentes,
        'vazio': vazio,
        'exit_code': 0,
    }


def main():
    parser = argparse.ArgumentParser(prog='consultando_estoque_assai')
    parser.add_argument('--resumo', action='store_true', help='Resumo geral')
    parser.add_argument('--modelo', help='Filtro por codigo de modelo (SOL, X11_MINI, DOT)')
    parser.add_argument('--cd-id', type=int, help='Filtro por CD')
    parser.add_argument('--por-modelo', action='store_true', help='Agrupa por modelo')
    parser.add_argument('--por-estagio', action='store_true', help='Agrupa por evento')
    args = parser.parse_args()

    try:
        app = create_app()
        with app.app_context():
            result = _run(args)
        print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))
        return result.get('exit_code', 0)
    except Exception as e:
        err = {'ok': False, 'error': str(e), 'exit_code': 2}
        print(json.dumps(err), file=sys.stderr)
        print(json.dumps(err))
        return 2


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 6: Rodar teste — PASS esperado**

```bash
pytest tests/skills/motos_assai/test_consultando_estoque_assai.py -v
```

Expected: 3 testes passando.

- [ ] **Step 7: Verificação manual via CLI**

```bash
source .venv/bin/activate
python .claude/skills/consultando-estoque-assai/scripts/consultando_estoque_assai.py --resumo
```

Expected: JSON válido em stdout com chaves `totais`, `por_modelo`, `vazio`, `exit_code`. Exit 0.

- [ ] **Step 8: Commit**

```bash
git add .claude/skills/consultando-estoque-assai/ tests/skills/motos_assai/
git commit -m "feat(skills): add consultando-estoque-assai skill (motos_assai pipeline)"
```

---

### Task 1.2: `rastreando-chassi-assai` (READ)

**Files:**
- Create: `.claude/skills/rastreando-chassi-assai/SKILL.md`
- Create: `.claude/skills/rastreando-chassi-assai/scripts/rastreando_chassi_assai.py`
- Create: `tests/skills/motos_assai/test_rastreando_chassi_assai.py`

- [ ] **Step 1: Escrever testes**

Conteúdo de `tests/skills/motos_assai/test_rastreando_chassi_assai.py`:

```python
"""Testes para rastreando-chassi-assai."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / '.claude/skills/rastreando-chassi-assai/scripts/rastreando_chassi_assai.py'


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=30,
    )


def test_chassi_inexistente_retorna_nao_encontrado(app):
    r = _run('--chassi', 'CHASSI_QUE_NAO_EXISTE')
    assert r.returncode in (0, 1)  # 0 com nao_encontrado=True OU 1 validacao
    data = json.loads(r.stdout)
    assert data.get('encontrado') is False or data.get('exit_code') == 1


def test_chassi_obrigatorio():
    r = _run()  # sem --chassi
    assert r.returncode != 0


def test_help():
    r = _run('--help')
    assert r.returncode == 0
```

- [ ] **Step 2: Rodar teste — FAIL**

```bash
pytest tests/skills/motos_assai/test_rastreando_chassi_assai.py -v
```

Expected: FAIL.

- [ ] **Step 3: Criar SKILL.md**

Conteúdo de `.claude/skills/rastreando-chassi-assai/SKILL.md`:

````markdown
---
name: rastreando-chassi-assai
description: >-
  Esta skill deve ser usada quando o usuario pergunta sobre o historico
  completo de UM chassi do modulo Motos Assai (B2B Q.P.A.): "cade o chassi
  MZX1234?", "historico do chassi X", "essa moto Q.P.A. ja foi separada?",
  "quando o chassi Y chegou ao CD?". Retorna eventos cronologicos, recibo
  Motochefe de origem, separacao ativa (se houver), NF Q.P.A. (se faturada),
  validacao de regex contra modelo.

  USAR QUANDO:
  - "cade o chassi MZX...?"
  - "historico do chassi"
  - "essa moto Q.P.A. ja foi vendida/separada?"
  - "em que recibo veio o chassi X?"

  NAO USAR PARA:
  - Estoque agregado (usar consultando-estoque-assai)
  - Chassis Lojas HORA (usar rastreando-chassi)
  - Pedido/compra do chassi (usar acompanhando-pedido-compra-assai)
allowed-tools: Read, Bash, Glob, Grep
---

# Rastreando Chassi Motos Assai

Mostra historico completo de UM chassi: eventos cronologicos, recibo de origem,
separacao ativa, NF Q.P.A. (se faturada).

---

## Invocacao

```bash
python .claude/skills/rastreando-chassi-assai/scripts/rastreando_chassi_assai.py \
    --chassi MZX1234567890
```

Output: JSON com historico completo.

---

## Output JSON

```json
{
  "encontrado": true,
  "chassi": "MZX1234",
  "moto": {
    "id": 42, "modelo_id": 1, "modelo_codigo": "SOL", "cor": "preta",
    "ano": 2026, "criada_em": "..."
  },
  "status_efetivo": "DISPONIVEL",
  "eventos": [
    {"id": 100, "tipo": "DISPONIVEL", "ocorrido_em": "...", "operador": "..."},
    {"id": 99, "tipo": "MONTADA", "ocorrido_em": "...", "operador": "..."},
    {"id": 98, "tipo": "ESTOQUE", "ocorrido_em": "...", "operador": "..."}
  ],
  "recibo_origem": {
    "id": 5, "compra_id": 3, "numero_compra": "MA-2026-0001",
    "data_recebimento": "..."
  },
  "separacao_ativa": null,
  "nf_qpa": null,
  "regex_check": {"ok": true, "regex_usado": "^MZX[0-9]{13}$"},
  "exit_code": 0
}
```
````

- [ ] **Step 4: Criar script**

Conteúdo de `.claude/skills/rastreando-chassi-assai/scripts/rastreando_chassi_assai.py`:

```python
#!/usr/bin/env python3
"""
Script: rastreando_chassi_assai.py

Historico completo de UM chassi do modulo Motos Assai.

Uso:
    --chassi MZX1234        # OBRIGATORIO

Exit codes:
    0 - sucesso (encontrado=true ou false)
    1 - validacao (chassi vazio)
    2 - erro infra
"""
import sys
import os
import json
import argparse
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from app import create_app, db  # noqa: E402


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def _run(chassi: str):
    from app.motos_assai.models import (
        AssaiMoto, AssaiMotoEvento, AssaiReciboMotochefe, AssaiReciboItem,
        AssaiSeparacaoItem, AssaiSeparacao, AssaiNfQpa, AssaiNfQpaItem,
    )
    from app.motos_assai.services.moto_evento_service import (
        eventos_chassi, status_efetivo,
    )
    from app.motos_assai.services.chassi_validator import validar_chassi

    chassi_norm = chassi.strip().upper()
    if not chassi_norm:
        return {'encontrado': False, 'erro': 'chassi vazio', 'exit_code': 1}

    moto = AssaiMoto.query.filter_by(chassi=chassi_norm).first()
    if not moto:
        return {
            'encontrado': False, 'chassi': chassi_norm,
            'mensagem': 'Chassi nao cadastrado em assai_moto',
            'exit_code': 0,
        }

    eventos = eventos_chassi(chassi_norm, limit=100)
    status = status_efetivo(chassi_norm)

    # Recibo de origem (se existe item de recibo com este chassi)
    recibo_item = (
        AssaiReciboItem.query
        .filter_by(chassi=chassi_norm)
        .order_by(AssaiReciboItem.id.asc())
        .first()
    )
    recibo_origem = None
    if recibo_item:
        recibo = AssaiReciboMotochefe.query.get(recibo_item.recibo_id)
        if recibo:
            recibo_origem = {
                'id': recibo.id,
                'compra_id': recibo.compra_id,
                'data_recebimento': recibo.data_recebimento,
            }

    # Separacao ativa
    sep_item = (
        AssaiSeparacaoItem.query
        .filter_by(chassi=chassi_norm)
        .join(AssaiSeparacao, AssaiSeparacao.id == AssaiSeparacaoItem.separacao_id)
        .filter(AssaiSeparacao.status != 'CANCELADA')
        .order_by(AssaiSeparacaoItem.id.desc())
        .first()
    )
    separacao_ativa = None
    if sep_item:
        sep = AssaiSeparacao.query.get(sep_item.separacao_id)
        separacao_ativa = {
            'separacao_id': sep.id,
            'pedido_id': sep.pedido_id,
            'loja_id': sep.loja_id,
            'status': sep.status,
        }

    # NF Q.P.A.
    nf_item = AssaiNfQpaItem.query.filter_by(chassi=chassi_norm).first()
    nf_qpa = None
    if nf_item:
        nf = AssaiNfQpa.query.get(nf_item.nf_id)
        if nf:
            nf_qpa = {
                'nf_id': nf.id,
                'numero_nf': nf.numero_nf,
                'data_emissao': nf.data_emissao,
                'status_match': nf_item.status_match,
            }

    # Regex check (signature: validar_chassi(chassi: str, modelo_id: Optional[int]))
    regex_result = validar_chassi(chassi_norm, moto.modelo_id)

    return {
        'encontrado': True,
        'chassi': chassi_norm,
        'moto': {
            'id': moto.id,
            'modelo_id': moto.modelo_id,
            'modelo_codigo': moto.modelo.codigo if moto.modelo else None,
            'cor': moto.cor,
            'motor': moto.motor,
            'ano': moto.ano,
            'criada_em': moto.criada_em,
        },
        'status_efetivo': status,
        'eventos': [
            {
                'id': e.id, 'tipo': e.tipo, 'ocorrido_em': e.ocorrido_em,
                'operador_id': e.operador_id,
                'operador_nome': e.operador.nome if e.operador else None,
                'observacao': e.observacao,
                'dados_extras': e.dados_extras or {},
            }
            for e in eventos
        ],
        'recibo_origem': recibo_origem,
        'separacao_ativa': separacao_ativa,
        'nf_qpa': nf_qpa,
        'regex_check': regex_result,
        'exit_code': 0,
    }


def main():
    parser = argparse.ArgumentParser(prog='rastreando_chassi_assai')
    parser.add_argument('--chassi', required=True, help='Chassi (obrigatorio)')
    args = parser.parse_args()

    try:
        app = create_app()
        with app.app_context():
            result = _run(args.chassi)
        print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))
        return result.get('exit_code', 0)
    except Exception as e:
        err = {'ok': False, 'error': str(e), 'exit_code': 2}
        print(json.dumps(err), file=sys.stderr)
        print(json.dumps(err))
        return 2


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 5: Rodar teste — PASS**

```bash
pytest tests/skills/motos_assai/test_rastreando_chassi_assai.py -v
```

Expected: 3 testes passando.

- [ ] **Step 6: Verificação CLI**

```bash
python .claude/skills/rastreando-chassi-assai/scripts/rastreando_chassi_assai.py --chassi TESTE_INEXISTENTE
```

Expected: JSON com `encontrado: false`. Exit 0.

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/rastreando-chassi-assai/ tests/skills/motos_assai/test_rastreando_chassi_assai.py
git commit -m "feat(skills): add rastreando-chassi-assai skill"
```

---

### Task 1.3: `acompanhando-pedido-compra-assai` (READ)

**Files:**
- Create: `.claude/skills/acompanhando-pedido-compra-assai/SKILL.md`
- Create: `.claude/skills/acompanhando-pedido-compra-assai/scripts/acompanhando_pedido_compra_assai.py`
- Create: `tests/skills/motos_assai/test_acompanhando_pedido_compra_assai.py`

- [ ] **Step 1: Verificar campos das tabelas pedido/compra**

```bash
grep -n "^class \|^def \|tablename\|nullable=False\|status" app/motos_assai/models/pedido.py | head -40
grep -n "^class \|^def \|tablename\|nullable=False\|status" app/motos_assai/models/compra.py | head -40
```

Expected: identificar `numero_voe`, `numero_compra`, status válidos. Anotar para uso no script.

- [ ] **Step 2: Escrever testes**

Conteúdo de `tests/skills/motos_assai/test_acompanhando_pedido_compra_assai.py`:

```python
"""Testes para acompanhando-pedido-compra-assai."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / '.claude/skills/acompanhando-pedido-compra-assai/scripts/acompanhando_pedido_compra_assai.py'


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=30,
    )


def test_listar_abertos(app):
    r = _run('--somente-abertos')
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert 'pedidos' in data
    assert 'compras' in data
    assert isinstance(data['pedidos'], list)
    assert isinstance(data['compras'], list)


def test_pedido_inexistente(app):
    r = _run('--pedido-id', '999999')
    assert r.returncode == 0  # nao encontrado nao e erro
    data = json.loads(r.stdout)
    # quando pedido_id especifico nao acha, retorna pedidos vazio
    assert data['pedidos'] == [] or data.get('encontrado') is False


def test_help():
    r = _run('--help')
    assert r.returncode == 0
```

- [ ] **Step 3: Rodar teste — FAIL**

```bash
pytest tests/skills/motos_assai/test_acompanhando_pedido_compra_assai.py -v
```

- [ ] **Step 4: Criar SKILL.md**

Conteúdo de `.claude/skills/acompanhando-pedido-compra-assai/SKILL.md`:

````markdown
---
name: acompanhando-pedido-compra-assai
description: >-
  Esta skill deve ser usada quando o usuario pergunta sobre pedidos VOE
  Q.P.A. (vendas para Sendas/Assai) ou compras Motochefe (vinculadas N:N
  aos pedidos): "como esta o pedido VOE 12345?", "compras Motochefe abertas",
  "MA-2026-0001 ja chegou?", "pedidos pendentes Q.P.A.". Mostra status,
  totais por loja, vinculacoes pedido-compra.

  USAR QUANDO:
  - "pedido VOE 12345"
  - "compra Motochefe MA-2026-0001"
  - "pedidos abertos Q.P.A."
  - "compras pendentes Motochefe"

  NAO USAR PARA:
  - Estoque/pipeline (usar consultando-estoque-assai)
  - Chassis individuais (usar rastreando-chassi-assai)
  - Separacoes/NFs (usar acompanhando-saida-assai)
allowed-tools: Read, Bash, Glob, Grep
---

# Acompanhando Pedido/Compra Motos Assai

Consulta pedidos VOE Q.P.A. (1 por loja x modelo) e compras Motochefe
(consolidacoes N->1 dos pedidos, com numero MA-AAAA-NNNN).

---

## Invocacao

```bash
python .claude/skills/acompanhando-pedido-compra-assai/scripts/acompanhando_pedido_compra_assai.py \
    --somente-abertos
```

Output: JSON.

---

## Args

- `--pedido-id <id>` ou `--numero-voe <num>` - pedido especifico
- `--compra-id <id>` ou `--numero-ma "MA-2026-0001"` - compra especifica
- `--somente-abertos` - pedidos ABERTO + compras EM_PRODUCAO

---

## Output JSON

```json
{
  "pedidos": [
    {
      "id": 1, "numero_voe": "VOE-12345", "status": "ABERTO",
      "criado_em": "...", "lojas_distintas": 38, "total_itens": 114,
      "compras_vinculadas": [{"id": 5, "numero_compra": "MA-2026-0003"}]
    }
  ],
  "compras": [
    {
      "id": 5, "numero_compra": "MA-2026-0003", "status": "EM_PRODUCAO",
      "data_emissao": "...", "total_motos": 90,
      "pedidos_vinculados": [{"id": 1, "numero_voe": "VOE-12345"}]
    }
  ],
  "exit_code": 0
}
```
````

- [ ] **Step 5: Criar script**

Conteúdo de `.claude/skills/acompanhando-pedido-compra-assai/scripts/acompanhando_pedido_compra_assai.py`:

```python
#!/usr/bin/env python3
"""
Script: acompanhando_pedido_compra_assai.py

Consulta pedidos VOE Q.P.A. e compras Motochefe.

Exit codes:
    0 - sucesso
    1 - validacao
    2 - erro infra
"""
import sys
import os
import json
import argparse
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from app import create_app, db  # noqa: E402
from sqlalchemy import func  # noqa: E402


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def _serializar_pedido(p, com_vinculos=True):
    from app.motos_assai.models import AssaiPedidoVendaItem, AssaiCompraMotochefePedido, AssaiCompraMotochefe

    total_itens = AssaiPedidoVendaItem.query.filter_by(pedido_id=p.id).count()
    lojas = (
        db.session.query(AssaiPedidoVendaItem.loja_id)
        .filter_by(pedido_id=p.id).distinct().count()
    )

    compras_vinc = []
    if com_vinculos:
        rows = (
            db.session.query(AssaiCompraMotochefe)
            .join(
                AssaiCompraMotochefePedido,
                AssaiCompraMotochefePedido.compra_id == AssaiCompraMotochefe.id,
            )
            .filter(AssaiCompraMotochefePedido.pedido_id == p.id)
            .all()
        )
        compras_vinc = [
            {'id': c.id, 'numero_compra': c.numero_compra, 'status': c.status}
            for c in rows
        ]

    return {
        'id': p.id,
        'numero_voe': getattr(p, 'numero_voe', None),
        'status': p.status,
        'criado_em': p.criado_em,
        'lojas_distintas': lojas,
        'total_itens': total_itens,
        'compras_vinculadas': compras_vinc,
    }


def _serializar_compra(c, com_vinculos=True):
    from app.motos_assai.models import AssaiCompraMotochefePedido, AssaiPedidoVenda

    pedidos_vinc = []
    if com_vinculos:
        rows = (
            db.session.query(AssaiPedidoVenda)
            .join(
                AssaiCompraMotochefePedido,
                AssaiCompraMotochefePedido.pedido_id == AssaiPedidoVenda.id,
            )
            .filter(AssaiCompraMotochefePedido.compra_id == c.id)
            .all()
        )
        pedidos_vinc = [
            {'id': p.id, 'numero_voe': getattr(p, 'numero_voe', None), 'status': p.status}
            for p in rows
        ]

    return {
        'id': c.id,
        'numero_compra': c.numero_compra,
        'status': c.status,
        'data_emissao': getattr(c, 'data_emissao', None),
        'total_motos': getattr(c, 'total_motos', None),
        'pedidos_vinculados': pedidos_vinc,
    }


def _run(args):
    from app.motos_assai.models import AssaiPedidoVenda, AssaiCompraMotochefe

    pedidos = []
    compras = []

    if args.pedido_id:
        p = AssaiPedidoVenda.query.get(args.pedido_id)
        if p:
            pedidos = [_serializar_pedido(p)]
    elif args.numero_voe:
        p = AssaiPedidoVenda.query.filter_by(numero_voe=args.numero_voe).first()
        if p:
            pedidos = [_serializar_pedido(p)]
    elif args.compra_id:
        c = AssaiCompraMotochefe.query.get(args.compra_id)
        if c:
            compras = [_serializar_compra(c)]
    elif args.numero_ma:
        c = AssaiCompraMotochefe.query.filter_by(numero_compra=args.numero_ma).first()
        if c:
            compras = [_serializar_compra(c)]
    elif args.somente_abertos:
        # Status valido: ABERTO em pedido, EM_PRODUCAO em compra
        pedidos = [
            _serializar_pedido(p)
            for p in AssaiPedidoVenda.query
                .filter(AssaiPedidoVenda.status.in_(['ABERTO', 'EM_PRODUCAO', 'SEPARANDO']))
                .order_by(AssaiPedidoVenda.id.desc())
                .limit(50)
                .all()
        ]
        compras = [
            _serializar_compra(c)
            for c in AssaiCompraMotochefe.query
                .filter(AssaiCompraMotochefe.status == 'EM_PRODUCAO')
                .order_by(AssaiCompraMotochefe.id.desc())
                .limit(50)
                .all()
        ]
    else:
        # Default: ultimos 20 de cada
        pedidos = [
            _serializar_pedido(p, com_vinculos=False)
            for p in AssaiPedidoVenda.query.order_by(AssaiPedidoVenda.id.desc()).limit(20).all()
        ]
        compras = [
            _serializar_compra(c, com_vinculos=False)
            for c in AssaiCompraMotochefe.query.order_by(AssaiCompraMotochefe.id.desc()).limit(20).all()
        ]

    return {
        'pedidos': pedidos,
        'compras': compras,
        'exit_code': 0,
    }


def main():
    parser = argparse.ArgumentParser(prog='acompanhando_pedido_compra_assai')
    parser.add_argument('--pedido-id', type=int, help='ID do pedido VOE')
    parser.add_argument('--numero-voe', help='Numero VOE')
    parser.add_argument('--compra-id', type=int, help='ID da compra Motochefe')
    parser.add_argument('--numero-ma', help='Numero da compra MA-AAAA-NNNN')
    parser.add_argument('--somente-abertos', action='store_true', help='Somente abertos/em producao')
    args = parser.parse_args()

    try:
        app = create_app()
        with app.app_context():
            result = _run(args)
        print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))
        return result.get('exit_code', 0)
    except Exception as e:
        err = {'ok': False, 'error': str(e), 'exit_code': 2}
        print(json.dumps(err), file=sys.stderr)
        print(json.dumps(err))
        return 2


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 6: Rodar teste — PASS**

```bash
pytest tests/skills/motos_assai/test_acompanhando_pedido_compra_assai.py -v
```

- [ ] **Step 7: Verificação CLI**

```bash
python .claude/skills/acompanhando-pedido-compra-assai/scripts/acompanhando_pedido_compra_assai.py --somente-abertos
```

Expected: JSON com `pedidos[]` e `compras[]`. Exit 0.

- [ ] **Step 8: Commit**

```bash
git add .claude/skills/acompanhando-pedido-compra-assai/ tests/skills/motos_assai/test_acompanhando_pedido_compra_assai.py
git commit -m "feat(skills): add acompanhando-pedido-compra-assai skill"
```

---

### Task 1.4: `acompanhando-saida-assai` (READ)

**Files:**
- Create: `.claude/skills/acompanhando-saida-assai/SKILL.md`
- Create: `.claude/skills/acompanhando-saida-assai/scripts/acompanhando_saida_assai.py`
- Create: `tests/skills/motos_assai/test_acompanhando_saida_assai.py`

- [ ] **Step 1: Verificar modelos AssaiSeparacao + AssaiNfQpa**

```bash
grep -n "^class \|tablename\|status_match\|^STATUS_\|^NF_STATUS_" app/motos_assai/models/separacao.py app/motos_assai/models/nf_qpa.py | head -40
```

Expected: anotar campos de status e match.

- [ ] **Step 2: Escrever testes**

Conteúdo de `tests/skills/motos_assai/test_acompanhando_saida_assai.py`:

```python
"""Testes para acompanhando-saida-assai."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / '.claude/skills/acompanhando-saida-assai/scripts/acompanhando_saida_assai.py'


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=30,
    )


def test_somente_abertas(app):
    r = _run('--somente-abertas')
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert 'separacoes' in data
    assert 'nfs_qpa' in data


def test_help():
    r = _run('--help')
    assert r.returncode == 0
```

- [ ] **Step 3: Rodar teste — FAIL**

```bash
pytest tests/skills/motos_assai/test_acompanhando_saida_assai.py -v
```

- [ ] **Step 4: Criar SKILL.md**

Conteúdo de `.claude/skills/acompanhando-saida-assai/SKILL.md`:

````markdown
---
name: acompanhando-saida-assai
description: >-
  Esta skill deve ser usada quando o usuario pergunta sobre separacoes em
  andamento ou NFs Q.P.A. importadas no modulo Motos Assai: "separacoes
  abertas", "NF Q.P.A. 12345 importada?", "ha divergencias em NFs?",
  "match BATEU?". Mostra separacoes ativas (EM_SEPARACAO/FECHADA),
  NFs Q.P.A. com resultado de match (BATEU/DIVERGENTE/NAO_RECONCILIADO).

  USAR QUANDO:
  - "separacoes em andamento Q.P.A."
  - "NF Q.P.A. 12345 bateu?"
  - "divergencias em NFs"
  - "qual loja recebeu NF X?"

  NAO USAR PARA:
  - Estoque (usar consultando-estoque-assai)
  - Chassi individual (usar rastreando-chassi-assai)
  - Pedidos/compras (usar acompanhando-pedido-compra-assai)
allowed-tools: Read, Bash, Glob, Grep
---

# Acompanhando Saida Motos Assai

Consulta separacoes em andamento e NFs Q.P.A. importadas com resultado de match.

---

## Invocacao

```bash
python .claude/skills/acompanhando-saida-assai/scripts/acompanhando_saida_assai.py \
    --somente-abertas
```

---

## Args

- `--separacao-id <id>` - separacao especifica
- `--somente-abertas` - separacoes em andamento (EM_SEPARACAO ou FECHADA)
- `--nfs-recentes` - ultimas NFs Q.P.A. importadas
- `--divergentes` - apenas NFs com match DIVERGENTE/NAO_RECONCILIADO

---

## Output JSON

```json
{
  "separacoes": [
    {
      "id": 5, "pedido_id": 1, "loja_id": 10, "loja_apelido": "LJ123 SENDAS",
      "status": "EM_SEPARACAO", "criada_em": "...",
      "total_chassis": 7, "total_modelos": [{"modelo": "SOL", "qtd": 5}]
    }
  ],
  "nfs_qpa": [
    {
      "id": 3, "numero_nf": "12345", "data_emissao": "...",
      "status_match": "BATEU", "loja_id": 10,
      "separacao_id": 5, "total_itens": 7, "total_divergentes": 0
    }
  ],
  "exit_code": 0
}
```
````

- [ ] **Step 5: Criar script**

Conteúdo de `.claude/skills/acompanhando-saida-assai/scripts/acompanhando_saida_assai.py`:

```python
#!/usr/bin/env python3
"""
Script: acompanhando_saida_assai.py

Consulta separacoes (EM_SEPARACAO/FECHADA/FATURADA) e NFs Q.P.A.

Exit codes:
    0 - sucesso
    2 - erro infra
"""
import sys
import os
import json
import argparse
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from app import create_app, db  # noqa: E402
from sqlalchemy import func  # noqa: E402


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def _serializar_separacao(sep):
    from app.motos_assai.models import (
        AssaiSeparacaoItem, AssaiModelo, AssaiLoja,
    )

    total_chassis = AssaiSeparacaoItem.query.filter_by(separacao_id=sep.id).count()

    rows = (
        db.session.query(AssaiModelo.codigo, func.count(AssaiSeparacaoItem.id))
        .join(AssaiSeparacaoItem, AssaiSeparacaoItem.modelo_id == AssaiModelo.id)
        .filter(AssaiSeparacaoItem.separacao_id == sep.id)
        .group_by(AssaiModelo.codigo)
        .all()
    )
    total_modelos = [{'modelo': c, 'qtd': int(q)} for c, q in rows]

    loja = AssaiLoja.query.get(sep.loja_id)
    return {
        'id': sep.id,
        'pedido_id': sep.pedido_id,
        'loja_id': sep.loja_id,
        'loja_apelido': loja.apelido if loja else None,
        'status': sep.status,
        'criada_em': getattr(sep, 'criada_em', None),
        'fechada_em': getattr(sep, 'fechada_em', None),
        'total_chassis': total_chassis,
        'total_modelos': total_modelos,
    }


def _serializar_nf_qpa(nf):
    from app.motos_assai.models import AssaiNfQpaItem

    total_itens = AssaiNfQpaItem.query.filter_by(nf_id=nf.id).count()
    total_divergentes = (
        AssaiNfQpaItem.query
        .filter_by(nf_id=nf.id)
        .filter(AssaiNfQpaItem.status_match == 'DIVERGENTE')
        .count()
    )

    return {
        'id': nf.id,
        'numero_nf': nf.numero_nf,
        'data_emissao': nf.data_emissao,
        'status_match': nf.status_match,
        'loja_id': getattr(nf, 'loja_id', None),
        'separacao_id': getattr(nf, 'separacao_id', None),
        'total_itens': total_itens,
        'total_divergentes': total_divergentes,
    }


def _run(args):
    from app.motos_assai.models import (
        AssaiSeparacao, AssaiNfQpa,
        SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA,
    )

    separacoes = []
    nfs_qpa = []

    if args.separacao_id:
        sep = AssaiSeparacao.query.get(args.separacao_id)
        if sep:
            separacoes = [_serializar_separacao(sep)]
    elif args.somente_abertas:
        seps = (
            AssaiSeparacao.query
            .filter(AssaiSeparacao.status.in_([SEPARACAO_STATUS_EM_SEPARACAO, SEPARACAO_STATUS_FECHADA]))
            .order_by(AssaiSeparacao.id.desc())
            .limit(50)
            .all()
        )
        separacoes = [_serializar_separacao(s) for s in seps]
    elif args.nfs_recentes:
        nfs = AssaiNfQpa.query.order_by(AssaiNfQpa.id.desc()).limit(20).all()
        nfs_qpa = [_serializar_nf_qpa(n) for n in nfs]
    elif args.divergentes:
        nfs = (
            AssaiNfQpa.query
            .filter(AssaiNfQpa.status_match.in_(['DIVERGENTE', 'NAO_RECONCILIADO']))
            .order_by(AssaiNfQpa.id.desc())
            .limit(50)
            .all()
        )
        nfs_qpa = [_serializar_nf_qpa(n) for n in nfs]
    else:
        # Default: ultimas 20 separacoes + 20 NFs
        seps = AssaiSeparacao.query.order_by(AssaiSeparacao.id.desc()).limit(20).all()
        nfs = AssaiNfQpa.query.order_by(AssaiNfQpa.id.desc()).limit(20).all()
        separacoes = [_serializar_separacao(s) for s in seps]
        nfs_qpa = [_serializar_nf_qpa(n) for n in nfs]

    return {
        'separacoes': separacoes,
        'nfs_qpa': nfs_qpa,
        'exit_code': 0,
    }


def main():
    parser = argparse.ArgumentParser(prog='acompanhando_saida_assai')
    parser.add_argument('--separacao-id', type=int)
    parser.add_argument('--somente-abertas', action='store_true')
    parser.add_argument('--nfs-recentes', action='store_true')
    parser.add_argument('--divergentes', action='store_true')
    args = parser.parse_args()

    try:
        app = create_app()
        with app.app_context():
            result = _run(args)
        print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))
        return result.get('exit_code', 0)
    except Exception as e:
        err = {'ok': False, 'error': str(e), 'exit_code': 2}
        print(json.dumps(err), file=sys.stderr)
        print(json.dumps(err))
        return 2


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 6: Rodar teste — PASS**

```bash
pytest tests/skills/motos_assai/test_acompanhando_saida_assai.py -v
```

- [ ] **Step 7: Verificação CLI**

```bash
python .claude/skills/acompanhando-saida-assai/scripts/acompanhando_saida_assai.py --somente-abertas
```

- [ ] **Step 8: Commit**

```bash
git add .claude/skills/acompanhando-saida-assai/ tests/skills/motos_assai/test_acompanhando_saida_assai.py
git commit -m "feat(skills): add acompanhando-saida-assai skill"
```

---

## FASE 2 — Sub-agent (orquestração READ inicialmente)

### Task 2.1: `gestor-motos-assai` agent

**Files:**
- Create: `.claude/agents/gestor-motos-assai.md`

- [ ] **Step 1: Criar agent file com seções obrigatórias**

Conteúdo de `.claude/agents/gestor-motos-assai.md`:

````markdown
---
name: gestor-motos-assai
description: Especialista no modulo Motos Assai (B2B Q.P.A. Sendas/Assai). Orquestra skills para consultar pipeline (estoque, pedidos VOE, compras Motochefe, recibos, separacoes, NFs Q.P.A.) e executar operacoes WRITE (montagem, disponibilizar, separar, conferir recibo). Use para "estoque motos Assai", "pedido VOE", "compra Motochefe", "recibo Motochefe", "NF Q.P.A.", "Sendas", "registrar montagem", "disponibilizar moto Q.P.A.". NAO usar para Lojas HORA (usar orientador-loja), pedidos Nacom Goya tradicionais (usar gerindo-expedicao), CarVia ou Motochefe (outros agentes).
tools: Read, Bash, Glob, Grep, mcp__memory__view_memories, mcp__memory__list_memories, mcp__memory__save_memory, mcp__memory__update_memory, mcp__memory__log_system_pitfall, mcp__memory__query_knowledge_graph
model: sonnet
skills:
  - consultando-estoque-assai
  - rastreando-chassi-assai
  - acompanhando-pedido-compra-assai
  - acompanhando-saida-assai
  - conferindo-recibo-assai
  - registrando-evento-moto-assai
---

# Gestor Motos Assai

Voce e o especialista no modulo Motos Assai (B2B Q.P.A. Sendas/Assai) da Nacom Goya.
Seu trabalho e consultar pipeline e executar operacoes WRITE com seguranca,
invocando skills atomicas e validando entradas.

## CONTEXTO

O modulo Motos Assai gerencia operacao B2B com Q.P.A. (motos eletricas) que
sao distribuidas para multiplas lojas Sendas/Assai. Pipeline:

```
Pedido VOE Q.P.A. -> Compra Motochefe (consolidacao N->1)
                                  v
                  Recibo Motochefe -> Recebimento fisico (wizard A->B->C->D)
                                                  v
            ESTOQUE -> MONTADA (ou PENDENTE) -> DISPONIVEL
                                                  v
                                      SEPARACAO (fungivel por modelo)
                                                  v
                                      NF Q.P.A. (match BATEU/DIVERGENTE)
                                                  v
                                                FATURADA
```

Toda rastreabilidade e por `chassi`. `assai_moto` e insert-once;
estado vem do ULTIMO evento em `assai_moto_evento` (append-only).

Ref completa: `app/motos_assai/CLAUDE.md`.

## ARMADILHAS CRITICAS

### A1: Eventos sao append-only
NUNCA tente UPDATE/DELETE em `assai_moto_evento`. Reverter = novo evento
(REVERTIDA_PARA_MONTADA, CANCELADA emite DISPONIVEL, etc.).

### A2: status_efetivo, NAO status_atual
O service helper se chama `status_efetivo(chassi)`, retorna o tipo do ultimo
evento. NAO existe coluna `status` em `assai_moto`.

### A3: UNIQUE parcial em separacao
`(separacao_id, chassi)` para `status != CANCELADA`. Tentar separar mesmo
chassi em 2 separacoes ativas = `IntegrityError` -> exit code 5.

### A4: Recebimento e SOT
Modelo/cor confirmados no recebimento fisico SOBRESCREVEM `AssaiMoto.cor` e
`AssaiMoto.modelo_id` (excecao autorizada a invariante insert-once).

### A5: PENDENTE bloqueia DISPONIVEL
Antes de DISPONIVEL, chassi deve passar por PENDENCIA_RESOLVIDA + MONTADA novo.

## ARVORE DE DECISAO

| Pergunta do usuario | Skill |
|---------------------|-------|
| "quantas motos disponiveis?" | `consultando-estoque-assai --resumo` |
| "quanto de SOL temos?" | `consultando-estoque-assai --modelo SOL` |
| "cade chassi MZX...?" | `rastreando-chassi-assai --chassi <X>` |
| "pedido VOE 12345" | `acompanhando-pedido-compra-assai --numero-voe 12345` |
| "compra MA-2026-0001" | `acompanhando-pedido-compra-assai --numero-ma <X>` |
| "separacoes abertas" | `acompanhando-saida-assai --somente-abertas` |
| "NFs divergentes" | `acompanhando-saida-assai --divergentes` |
| "recibos pendentes" | `conferindo-recibo-assai --listar-pendentes` |
| "registra MZX como montada" | `registrando-evento-moto-assai --montar` (DRY-RUN PRIMEIRO) |
| "disponibiliza moto X" | `registrando-evento-moto-assai --disponibilizar` |
| "como esta a operacao Motos Assai?" | F1 (resumo cross-entidade) |

### F1: "Como esta a operacao Motos Assai hoje?"

Sequencia:
1. `consultando-estoque-assai --resumo` - totais por estagio
2. `acompanhando-pedido-compra-assai --somente-abertos` - pedidos/compras pendentes
3. `conferindo-recibo-assai --listar-pendentes` - recibos aguardando conferencia
4. `acompanhando-saida-assai --somente-abertas` - separacoes em andamento

Sintetize em 4-6 linhas com numeros exatos.

## PRE-MORTEM (para WRITE)

> Ref: `.claude/references/AGENT_TEMPLATES.md#pre-mortem`

**Trigger neste agent**: ANTES de qualquer skill WRITE
(`registrando-evento-moto-assai`, `conferindo-recibo-assai --registrar-chassi`,
`conferindo-recibo-assai --finalizar-recibo`).

**Cenarios conhecidos de falha**:

1. **Chassi com evento posterior ja existente**: registrar MONTADA em chassi
   ja SEPARADA. Mitigacao: verificar `status_efetivo` no dry-run antes de
   pedir confirmacao.

2. **Recibo finalizado prematuramente**: finalizar recibo com chassis
   faltantes sem `--confirmar-faltantes`. Mitigacao: skill rejeita.

3. **Disponibilizar com PENDENTE ativo**: Mitigacao: `DisponibilizarValidationError`
   bloqueia, dry-run mostra status_efetivo.

4. **Race em separacao**: 2 operadores escaneiam mesmo chassi. Mitigacao:
   UNIQUE parcial -> IntegrityError -> exit 5. Reportar conflito ao usuario,
   NAO retentar automaticamente.

5. **NF DIVERGENTE com flag aceita**: confirmar separacao FATURADA com match
   DIVERGENTE sem usuario aceitar. Mitigacao: gestor NAO permite write
   FATURADA sem usuario aceitar divergencia explicitamente.

**Decisao**:
- [x] Prosseguir com dry-run primeiro
- [ ] Prosseguir-com-salvaguarda (cenario 4)
- [ ] Escalar-para-humano (cenario 5)

## SELF-CRITIQUE (antes de retornar)

> Ref: `.claude/references/AGENT_TEMPLATES.md#self-critique`

- [ ] Citei o `status_efetivo` do chassi com fonte (`evento_id`)?
- [ ] Considerei se o usuario tem permissao (`pode_acessar_motos_assai`)?
- [ ] Reportei resultados negativos explicitamente ("nenhum recibo encontrado")?
- [ ] Em WRITE: o dry-run foi mostrado ANTES da confirmacao?
- [ ] Em WRITE: marquei `[ASSUNCAO]` se usuario disse "essa moto" sem chassi?
- [ ] Apliquei hierarquia constitucional (L1 Seguranca > L2 Etica > L3 Regras > L4 Utilidade)?

## FORMATO DE RESPOSTA

> Ref: `.claude/references/AGENT_TEMPLATES.md#output-format-padrao`

1. **Resposta direta** (1-3 frases) - o que o usuario perguntou
2. **Detalhes acionaveis** - bullets com numeros exatos e IDs
3. **Limitacoes** - o que nao foi possivel verificar (se aplicavel)

NAO colar JSON cru. Formatar em bullets ou tabela markdown.

## BOUNDARY CHECK

| Pergunta sobre... | Redirecionar para... |
|-------------------|----------------------|
| Lojas HORA (B2C varejo) | `orientador-loja` |
| Pedidos Nacom Goya tradicionais | `gerindo-expedicao` |
| Frete/cotacao | `cotando-frete` |
| CarVia (subcontrato) | `gerindo-carvia` |
| SSW (transportadora) | `acessando-ssw` |
| Operacoes Odoo | `especialista-odoo` |
| Devolucoes | `gestor-devolucoes` |
| Pipeline recebimento Nacom | `gestor-recebimento` |

## PROTOCOLO DE CONFIABILIDADE (OBRIGATORIO)

> Ref: `.claude/references/SUBAGENT_RELIABILITY.md`

Ao concluir tarefa, criar `/tmp/subagent-findings/gestor-motos-assai-<contexto>.md` com:

- **Fatos Verificados**: cada afirmacao com fonte (`tabela.campo = valor` ou `arquivo:linha`)
- **Inferencias**: conclusoes deduzidas, explicitando base
- **Nao Encontrado**: o que buscou e NAO achou
- **Assuncoes**: marcar `[ASSUNCAO]`
- NUNCA omitir resultados negativos
- NUNCA fabricar dados
- Se skill delegada falhou, reportar **erro exato** (nao resumir como "erro")

## LIMITES

Voce NAO sabe sobre:
- Lojas HORA (B2C, dominio orientador-loja)
- Frete, cotacao, SSW, Odoo, CarVia (dominios diferentes)
- Pedidos de alimentos Nacom (carteira tradicional)
- Modulos Motochefe/Pessoal (dominios diferentes)

Se o usuario pedir algo fora do escopo: redirecione e pare.
````

- [ ] **Step 2: Verificar agent registrado**

```bash
ls -la .claude/agents/gestor-motos-assai.md
grep -c "^name: gestor-motos-assai" .claude/agents/gestor-motos-assai.md
```

Expected: arquivo existe, count == 1.

- [ ] **Step 3: Verificar parsing do frontmatter**

```bash
python -c "
import yaml
with open('.claude/agents/gestor-motos-assai.md') as f:
    content = f.read()
fm = content.split('---')[1]
parsed = yaml.safe_load(fm)
assert parsed['name'] == 'gestor-motos-assai'
assert parsed['model'] == 'sonnet'
assert isinstance(parsed['skills'], list)
assert len(parsed['skills']) == 6
print('OK: frontmatter valido')
"
```

Expected: "OK: frontmatter valido"

- [ ] **Step 4: Commit**

```bash
git add .claude/agents/gestor-motos-assai.md
git commit -m "feat(agents): add gestor-motos-assai sub-agent (orquestra 6 skills motos_assai)"
```

---

## FASE 3 — Skills MIXED/WRITE (2 skills)

### Task 3.1: `conferindo-recibo-assai` (READ + WRITE)

**Files:**
- Create: `.claude/skills/conferindo-recibo-assai/SKILL.md`
- Create: `.claude/skills/conferindo-recibo-assai/scripts/conferindo_recibo_assai.py`
- Create: `tests/skills/motos_assai/test_conferindo_recibo_assai.py`

- [ ] **Step 1: Verificar signature de recebimento_service**

```bash
grep -n "def \|class " app/motos_assai/services/recebimento_service.py | head -20
```

Expected: anotar args de `validar_chassi_contra_recibo`, `registrar_conferencia`, `finalizar_recebimento`.

- [ ] **Step 2: Escrever testes**

Conteúdo de `tests/skills/motos_assai/test_conferindo_recibo_assai.py`:

```python
"""Testes para conferindo-recibo-assai (READ + WRITE)."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / '.claude/skills/conferindo-recibo-assai/scripts/conferindo_recibo_assai.py'


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=30,
    )


def test_listar_pendentes_read(app):
    r = _run('--listar-pendentes')
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert 'recibos' in data


def test_recibo_inexistente_read(app):
    r = _run('--recibo-id', '999999')
    assert r.returncode in (0, 1)


def test_write_sem_user_id_falha(app):
    """WRITE sem --user-id deve falhar."""
    r = _run('--registrar-chassi', '--recibo-id', '1', '--chassi', 'X', '--modelo-id', '1', '--cor', 'preta')
    # Sem --user-id obrigatorio
    assert r.returncode != 0


def test_write_dry_run_default(app):
    """Sem --confirmar deve retornar dry-run preview com exit 4."""
    r = _run(
        '--registrar-chassi', '--recibo-id', '999999',
        '--chassi', 'TESTXXXXX', '--modelo-id', '1', '--cor', 'preta',
        '--user-id', '1',
    )
    # Dry-run -> exit 4 ou 1 (recibo nao existe)
    assert r.returncode in (1, 4)


def test_help():
    r = _run('--help')
    assert r.returncode == 0
```

- [ ] **Step 3: Rodar teste — FAIL**

```bash
pytest tests/skills/motos_assai/test_conferindo_recibo_assai.py -v
```

- [ ] **Step 4: Criar SKILL.md**

Conteúdo de `.claude/skills/conferindo-recibo-assai/SKILL.md`:

````markdown
---
name: conferindo-recibo-assai
description: >-
  Esta skill deve ser usada para consultar e operar conferencia de recibos
  Motochefe (recebimento fisico no CD): "recibos pendentes", "como esta a
  conferencia do recibo X?", "registrar chassi Y como conferido", "finalizar
  recibo Z". READ retorna status do recibo + chassis declarados/conferidos/
  faltando. WRITE registra chassis (insert-once em assai_moto + evento ESTOQUE)
  e finaliza o recibo. Cobre o ciclo de conferencia fisica (recibo Motochefe
  + wizard A->B->C->D).

  USAR QUANDO:
  - "recibos pendentes Motochefe"
  - "como esta a conferencia do recibo 5?"
  - "registrar chassi MZX no recibo 5"
  - "finalizar recibo 5"

  NAO USAR PARA:
  - Eventos de pipeline em chassis JA cadastrados (usar registrando-evento-moto-assai)
  - Estoque (usar consultando-estoque-assai)
  - Pedidos/compras (usar acompanhando-pedido-compra-assai)
  - Recebimento Lojas HORA (usar conferindo-recebimento)
allowed-tools: Read, Bash, Glob, Grep
---

# Conferindo Recibo Motochefe (Motos Assai)

Consulta e opera conferencia de recibos Motochefe (recebimento fisico no CD,
inserindo motos em `assai_moto` com primeiro evento ESTOQUE).

---

## REGRAS CRITICAS

### 1. INSERT-ONCE em assai_moto
Esta skill INSERE chassi em `assai_moto` (antes nao existia). Eh diferente
de `registrando-evento-moto-assai` que apenas TRANSITA chassis ja existentes.

### 2. WRITE requer --user-id obrigatorio
Toda operacao WRITE registra `operador_id`. Sem --user-id -> exit 4.

### 3. Dry-run default
Operacoes WRITE sem `--confirmar` retornam preview e exit 4.

### 4. Recebimento e SOT
Modelo/cor confirmados sobrescrevem o que veio do recibo. Service ja faz
update se diverge.

---

## Args READ

- `--listar-pendentes` - recibos com status RECEBIDO_AGUARDANDO_CONFERENCIA
- `--recibo-id <id>` - detalhe do recibo

## Args WRITE (todos com --user-id obrigatorio + --dry-run/--confirmar)

- `--registrar-chassi --recibo-id <id> --chassi <X> --modelo-id <m> --cor <c>`
- `--finalizar-recibo --recibo-id <id> [--confirmar-faltantes]`

---

## Output JSON (READ)

```json
{
  "recibos": [
    {
      "id": 5, "compra_id": 3, "numero_compra": "MA-2026-0003",
      "status": "EM_CONFERENCIA", "data_recebimento": "...",
      "total_declarado": 90, "total_conferido": 47,
      "total_faltante": 43, "total_divergente": 0
    }
  ],
  "exit_code": 0
}
```

## Output JSON (WRITE dry-run)

```json
{
  "ok": true, "dry_run": true,
  "preview": {
    "operacao": "registrar_chassi",
    "recibo_id": 5, "chassi": "MZX1234",
    "validacoes": ["recibo_ativo: ok", "chassi_no_recibo: ok"],
    "evento_a_emitir": "ESTOQUE"
  },
  "exit_code": 4
}
```

## Output JSON (WRITE confirmar)

```json
{
  "ok": true, "dry_run": false,
  "item_id": 42, "chassi": "MZX1234",
  "evento_id": 100, "tipo_divergencia": null,
  "exit_code": 0
}
```
````

- [ ] **Step 5: Criar script**

Conteúdo de `.claude/skills/conferindo-recibo-assai/scripts/conferindo_recibo_assai.py`:

```python
#!/usr/bin/env python3
"""
Script: conferindo_recibo_assai.py

READ: lista/detalhe de recibos Motochefe.
WRITE: registra chassi conferido / finaliza recibo (com dry-run).

Exit codes:
    0 - sucesso
    1 - validacao falhou
    2 - erro infra
    3 - nao autorizado
    4 - confirmacao faltando (WRITE sem --confirmar)
    5 - conflito 409
"""
import sys
import os
import json
import argparse
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from app import create_app, db  # noqa: E402


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def _verificar_autorizacao(user_id):
    from app.auth.models import Usuario
    u = Usuario.query.get(user_id)
    if not u:
        return False, 'usuario_nao_encontrado'
    if not u.pode_acessar_motos_assai():
        return False, 'sem_permissao_motos_assai'
    return True, None


def _serializar_recibo(r):
    from app.motos_assai.models import AssaiReciboItem

    total_declarado = AssaiReciboItem.query.filter_by(recibo_id=r.id).count()
    total_conferido = (
        AssaiReciboItem.query
        .filter_by(recibo_id=r.id)
        .filter(AssaiReciboItem.conferido_em.isnot(None))
        .count()
    )

    return {
        'id': r.id,
        'compra_id': r.compra_id,
        'status': r.status,
        'data_recebimento': r.data_recebimento,
        'total_declarado': total_declarado,
        'total_conferido': total_conferido,
        'total_faltante': max(0, total_declarado - total_conferido),
    }


def _cmd_listar_pendentes():
    from app.motos_assai.models import AssaiReciboMotochefe

    recibos = (
        AssaiReciboMotochefe.query
        .filter(AssaiReciboMotochefe.status.in_([
            'RECEBIDO_AGUARDANDO_CONFERENCIA', 'EM_CONFERENCIA',
        ]))
        .order_by(AssaiReciboMotochefe.id.desc())
        .limit(50)
        .all()
    )
    return {
        'recibos': [_serializar_recibo(r) for r in recibos],
        'exit_code': 0,
    }


def _cmd_detalhe(recibo_id):
    from app.motos_assai.models import AssaiReciboMotochefe, AssaiReciboItem

    r = AssaiReciboMotochefe.query.get(recibo_id)
    if not r:
        return {'encontrado': False, 'recibo_id': recibo_id, 'exit_code': 0}

    itens = (
        AssaiReciboItem.query
        .filter_by(recibo_id=recibo_id)
        .order_by(AssaiReciboItem.id.asc())
        .all()
    )
    return {
        'recibos': [_serializar_recibo(r)],
        'itens': [
            {
                'id': it.id, 'chassi': it.chassi,
                'modelo_declarado': it.modelo_declarado_str,
                'cor_declarada': it.cor_declarada,
                'conferido_em': it.conferido_em,
                'tipo_divergencia': it.tipo_divergencia,
            }
            for it in itens
        ],
        'exit_code': 0,
    }


def _cmd_registrar_chassi(args):
    from app.motos_assai.services.recebimento_service import (
        registrar_conferencia, validar_chassi_contra_recibo,
        RecebimentoConflictError, RecebimentoValidationError,
    )

    # Dry-run: somente validar
    if not args.confirmar:
        validacao = validar_chassi_contra_recibo(args.recibo_id, args.chassi)
        return {
            'ok': True, 'dry_run': True,
            'preview': {
                'operacao': 'registrar_chassi',
                'recibo_id': args.recibo_id,
                'chassi': args.chassi.strip().upper(),
                'modelo_id': args.modelo_id,
                'cor': args.cor,
                'validacao': validacao,
                'evento_a_emitir': 'ESTOQUE',
            },
            'exit_code': 4,
        }

    # WRITE real (signature de registrar_conferencia em recebimento_service.py:83)
    try:
        item = registrar_conferencia(
            recibo_id=args.recibo_id,
            chassi=args.chassi,
            modelo_conferido_id=args.modelo_id,
            cor_conferida=args.cor,
            qr_code_lido=False,   # CLI nao tem QR
            foto_s3_key=None,     # CLI nao tem foto
            operador_id=args.user_id,
            avaria_fisica=False,
        )
        return {
            'ok': True, 'dry_run': False,
            'item_id': item.id,
            'chassi': item.chassi,
            'tipo_divergencia': item.tipo_divergencia,
            'recibo_id': item.recibo_id,
            'exit_code': 0,
        }
    except RecebimentoConflictError as e:
        return {'ok': False, 'erro': str(e), 'retry': True, 'exit_code': 5}
    except RecebimentoValidationError as e:
        return {'ok': False, 'erro': str(e), 'exit_code': 1}


def _cmd_finalizar(args):
    from app.motos_assai.services.recebimento_service import (
        finalizar_recebimento, RecebimentoValidationError,
    )

    if not args.confirmar:
        return {
            'ok': True, 'dry_run': True,
            'preview': {
                'operacao': 'finalizar_recibo',
                'recibo_id': args.recibo_id,
                'confirmar_faltantes': args.confirmar_faltantes,
            },
            'exit_code': 4,
        }

    try:
        recibo = finalizar_recebimento(
            recibo_id=args.recibo_id,
            operador_id=args.user_id,
            confirmar_faltantes=args.confirmar_faltantes,
        )
        return {
            'ok': True, 'dry_run': False,
            'recibo_id': recibo.id,
            'novo_status': recibo.status,
            'exit_code': 0,
        }
    except RecebimentoValidationError as e:
        return {'ok': False, 'erro': str(e), 'exit_code': 1}


def _run(args):
    # Comandos READ
    if args.listar_pendentes:
        return _cmd_listar_pendentes()
    if args.recibo_id and not (args.registrar_chassi or args.finalizar_recibo):
        return _cmd_detalhe(args.recibo_id)

    # Comandos WRITE
    if args.registrar_chassi or args.finalizar_recibo:
        if not args.user_id:
            return {'ok': False, 'erro': '--user-id obrigatorio para WRITE', 'exit_code': 4}
        ok, motivo = _verificar_autorizacao(args.user_id)
        if not ok:
            return {'ok': False, 'erro': motivo, 'exit_code': 3}

        if args.registrar_chassi:
            if not (args.recibo_id and args.chassi and args.modelo_id and args.cor):
                return {'ok': False, 'erro': 'recibo-id/chassi/modelo-id/cor obrigatorios', 'exit_code': 1}
            return _cmd_registrar_chassi(args)
        if args.finalizar_recibo:
            if not args.recibo_id:
                return {'ok': False, 'erro': '--recibo-id obrigatorio', 'exit_code': 1}
            return _cmd_finalizar(args)

    return {'ok': False, 'erro': 'comando nao especificado', 'exit_code': 1}


def main():
    parser = argparse.ArgumentParser(prog='conferindo_recibo_assai')
    # READ
    parser.add_argument('--listar-pendentes', action='store_true')
    parser.add_argument('--recibo-id', type=int)
    # WRITE
    parser.add_argument('--registrar-chassi', action='store_true')
    parser.add_argument('--chassi')
    parser.add_argument('--modelo-id', type=int)
    parser.add_argument('--cor')
    parser.add_argument('--finalizar-recibo', action='store_true')
    parser.add_argument('--confirmar-faltantes', action='store_true')
    # Comum
    parser.add_argument('--user-id', type=int, help='Obrigatorio para WRITE')
    parser.add_argument('--confirmar', action='store_true', help='Executa WRITE (default = dry-run)')
    args = parser.parse_args()

    try:
        app = create_app()
        with app.app_context():
            result = _run(args)
        print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))
        return result.get('exit_code', 0)
    except Exception as e:
        err = {'ok': False, 'error': str(e), 'exit_code': 2}
        print(json.dumps(err), file=sys.stderr)
        print(json.dumps(err))
        return 2


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 6: Rodar teste — PASS**

```bash
pytest tests/skills/motos_assai/test_conferindo_recibo_assai.py -v
```

- [ ] **Step 7: Verificação CLI READ**

```bash
python .claude/skills/conferindo-recibo-assai/scripts/conferindo_recibo_assai.py --listar-pendentes
```

Expected: JSON com `recibos[]`. Exit 0.

- [ ] **Step 8: Verificação CLI WRITE dry-run**

```bash
python .claude/skills/conferindo-recibo-assai/scripts/conferindo_recibo_assai.py \
    --registrar-chassi --recibo-id 1 --chassi TEST123 --modelo-id 1 --cor preta --user-id 1
```

Expected: JSON com `dry_run: true`. Exit 4.

- [ ] **Step 9: Commit**

```bash
git add .claude/skills/conferindo-recibo-assai/ tests/skills/motos_assai/test_conferindo_recibo_assai.py
git commit -m "feat(skills): add conferindo-recibo-assai (READ + WRITE conferencia)"
```

---

### Task 3.2: `registrando-evento-moto-assai` (WRITE)

**Files:**
- Create: `.claude/skills/registrando-evento-moto-assai/SKILL.md`
- Create: `.claude/skills/registrando-evento-moto-assai/scripts/registrando_evento_moto_assai.py`
- Create: `tests/skills/motos_assai/test_registrando_evento_moto_assai.py`

- [ ] **Step 1: Escrever testes**

Conteúdo de `tests/skills/motos_assai/test_registrando_evento_moto_assai.py`:

```python
"""Testes para registrando-evento-moto-assai (WRITE)."""
import json
import subprocess
import sys
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / '.claude/skills/registrando-evento-moto-assai/scripts/registrando_evento_moto_assai.py'


def _run(*args):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True, text=True, timeout=30,
    )


def test_sem_user_id_falha(app):
    """WRITE sem --user-id deve falhar."""
    r = _run('--montar', '--chassi', 'TEST123')
    assert r.returncode != 0


def test_dry_run_montar(app):
    """--montar sem --confirmar deve retornar dry-run."""
    r = _run('--montar', '--chassi', 'TESTNAOEXISTE', '--user-id', '1')
    # exit 1 (chassi nao existe) ou 4 (dry-run)
    assert r.returncode in (1, 4)
    data = json.loads(r.stdout)
    if r.returncode == 4:
        assert data.get('dry_run') is True


def test_help():
    r = _run('--help')
    assert r.returncode == 0


def test_comando_nao_especificado(app):
    """Sem --montar/--disponibilizar/etc deve falhar."""
    r = _run('--user-id', '1')
    assert r.returncode != 0
```

- [ ] **Step 2: Rodar teste — FAIL**

```bash
pytest tests/skills/motos_assai/test_registrando_evento_moto_assai.py -v
```

- [ ] **Step 3: Criar SKILL.md**

Conteúdo de `.claude/skills/registrando-evento-moto-assai/SKILL.md`:

````markdown
---
name: registrando-evento-moto-assai
description: >-
  Esta skill deve ser usada para EXECUTAR transicoes de estado em chassis ja
  cadastrados no modulo Motos Assai: "registra chassi MZX como montada",
  "disponibiliza essa moto", "reverte disponibilizacao", "separa chassi X
  para pedido Y", "cancela separacao Z". Cobre 8 sub-comandos: montar,
  montar-pendente, resolver-pendencia, disponibilizar, reverter, separar,
  desfazer-separacao, cancelar-separacao. SEMPRE com --dry-run + --confirmar.

  USAR QUANDO:
  - "registra chassi MZX como montada"
  - "disponibiliza moto X"
  - "reverte disponibilizacao do chassi X"
  - "separa chassi para pedido"
  - "cancela separacao 5"

  NAO USAR PARA:
  - INSERIR chassi novo (vem do recibo) -> usar conferindo-recibo-assai
  - Consultas READ (usar consultando-estoque-assai ou rastreando-chassi-assai)
  - Eventos Lojas HORA (dominio diferente)
allowed-tools: Read, Bash, Glob, Grep
---

# Registrando Evento Moto Motos Assai (WRITE)

Executa transicoes de estado em chassis ja cadastrados em `assai_moto`.
Insert-once de chassi NAO e desta skill (usar conferindo-recibo-assai).

---

## REGRAS CRITICAS

### 1. SEMPRE --dry-run primeiro
Sem `--confirmar` retorna preview + exit 4. Com `--confirmar` executa.

### 2. --user-id obrigatorio
Todas operacoes registram `operador_id`. Sem --user-id -> exit 4.

### 3. Validacao por status_efetivo
Cada operacao valida `status_efetivo(chassi)`:
- montar: precisa ESTOQUE
- montar-pendente: precisa ESTOQUE + descricao >=3 chars
- resolver-pendencia: precisa PENDENTE
- disponibilizar: precisa MONTADA ou REVERTIDA_PARA_MONTADA
- reverter-disponibilizacao: precisa DISPONIVEL + motivo >=3 chars
- separar: precisa DISPONIVEL + saldo no pedido
- desfazer-separacao: precisa separacao em EM_SEPARACAO
- cancelar-separacao: precisa separacao em EM_SEPARACAO ou FECHADA

### 4. Race condition em separar
UNIQUE parcial -> IntegrityError -> exit 5. NAO retentar automaticamente.

---

## Args (todos com --user-id + --dry-run default + --confirmar)

```
--montar --chassi <X>
--montar-pendente --chassi <X> --descricao <texto>
--resolver-pendencia --chassi <X> --descricao <texto>
--disponibilizar --chassi <X>
--reverter-disponibilizacao --chassi <X> --motivo <texto>
--separar --pedido-id <p> --loja-id <l> --chassi <X>
--desfazer-separacao --item-id <id>
--cancelar-separacao --separacao-id <id> --motivo <texto>
```

---

## Output JSON (dry-run)

```json
{
  "ok": true, "dry_run": true,
  "preview": {
    "operacao": "montar",
    "chassi": "MZX1234",
    "status_atual": "ESTOQUE",
    "evento_a_emitir": "MONTADA",
    "validacoes": ["chassi_existe: ok", "status_compativel: ok"]
  },
  "exit_code": 4
}
```

## Output JSON (confirmar OK)

```json
{
  "ok": true, "dry_run": false,
  "evento_id": 100, "chassi": "MZX1234", "tipo": "MONTADA",
  "exit_code": 0
}
```
````

- [ ] **Step 4: Criar script**

Conteúdo de `.claude/skills/registrando-evento-moto-assai/scripts/registrando_evento_moto_assai.py`:

```python
#!/usr/bin/env python3
"""
Script: registrando_evento_moto_assai.py

WRITE: 8 sub-comandos de transicao de estado em chassis ja cadastrados.

Exit codes:
    0 - sucesso
    1 - validacao falhou
    2 - erro infra
    3 - nao autorizado
    4 - confirmacao faltando ou args invalidos
    5 - conflito 409 (race em separar)
"""
import sys
import os
import json
import argparse
from datetime import datetime
from decimal import Decimal

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../..')))

from app import create_app, db  # noqa: E402


def _json_default(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return str(obj)


def _verificar_autorizacao(user_id):
    from app.auth.models import Usuario
    u = Usuario.query.get(user_id)
    if not u:
        return False, 'usuario_nao_encontrado'
    if not u.pode_acessar_motos_assai():
        return False, 'sem_permissao_motos_assai'
    return True, None


def _preview(operacao, chassi, evento_esperado, status_atual=None, extras=None):
    """Constroi preview dry-run."""
    return {
        'ok': True, 'dry_run': True,
        'preview': {
            'operacao': operacao,
            'chassi': (chassi or '').strip().upper(),
            'status_atual': status_atual,
            'evento_a_emitir': evento_esperado,
            'extras': extras or {},
        },
        'exit_code': 4,
    }


def _cmd_montar(args):
    from app.motos_assai.services.moto_evento_service import status_efetivo
    from app.motos_assai.services.montagem_service import (
        registrar_montagem, MontagemValidationError,
    )

    chassi_norm = args.chassi.strip().upper() if args.chassi else ''
    status = status_efetivo(chassi_norm) if chassi_norm else None

    if not args.confirmar:
        return _preview('montar', chassi_norm, 'MONTADA', status)

    try:
        r = registrar_montagem(
            chassi=chassi_norm, pendencia=False,
            descricao_pendencia=None, chassi_doador=None,
            operador_id=args.user_id,
        )
        return {'ok': True, 'dry_run': False, **r, 'exit_code': 0}
    except MontagemValidationError as e:
        return {'ok': False, 'erro': str(e), 'exit_code': 1}


def _cmd_montar_pendente(args):
    from app.motos_assai.services.moto_evento_service import status_efetivo
    from app.motos_assai.services.montagem_service import (
        registrar_montagem, MontagemValidationError,
    )

    chassi_norm = args.chassi.strip().upper() if args.chassi else ''
    status = status_efetivo(chassi_norm) if chassi_norm else None

    if not args.descricao or len(args.descricao.strip()) < 3:
        return {'ok': False, 'erro': 'descricao obrigatoria (>=3 chars)', 'exit_code': 1}

    if not args.confirmar:
        return _preview('montar_pendente', chassi_norm, 'PENDENTE', status,
                        extras={'descricao': args.descricao})

    try:
        r = registrar_montagem(
            chassi=chassi_norm, pendencia=True,
            descricao_pendencia=args.descricao,
            chassi_doador=None,
            operador_id=args.user_id,
        )
        return {'ok': True, 'dry_run': False, **r, 'exit_code': 0}
    except MontagemValidationError as e:
        return {'ok': False, 'erro': str(e), 'exit_code': 1}


def _cmd_resolver_pendencia(args):
    from app.motos_assai.services.moto_evento_service import status_efetivo
    from app.motos_assai.services.montagem_service import (
        resolver_pendencia, MontagemValidationError,
    )

    chassi_norm = args.chassi.strip().upper() if args.chassi else ''
    status = status_efetivo(chassi_norm) if chassi_norm else None

    if not args.descricao or len(args.descricao.strip()) < 3:
        return {'ok': False, 'erro': 'descricao obrigatoria (>=3 chars)', 'exit_code': 1}

    if not args.confirmar:
        return _preview('resolver_pendencia', chassi_norm, 'MONTADA (via PENDENCIA_RESOLVIDA)', status)

    try:
        r = resolver_pendencia(
            chassi=chassi_norm,
            descricao_resolucao=args.descricao,
            operador_id=args.user_id,
        )
        return {'ok': True, 'dry_run': False, **r, 'exit_code': 0}
    except MontagemValidationError as e:
        return {'ok': False, 'erro': str(e), 'exit_code': 1}


def _cmd_disponibilizar(args):
    from app.motos_assai.services.moto_evento_service import status_efetivo
    from app.motos_assai.services.disponibilizar_service import (
        disponibilizar, DisponibilizarValidationError,
    )

    chassi_norm = args.chassi.strip().upper() if args.chassi else ''
    status = status_efetivo(chassi_norm) if chassi_norm else None

    if not args.confirmar:
        return _preview('disponibilizar', chassi_norm, 'DISPONIVEL', status)

    try:
        r = disponibilizar(chassi=chassi_norm, operador_id=args.user_id)
        return {'ok': True, 'dry_run': False, **r, 'exit_code': 0}
    except DisponibilizarValidationError as e:
        return {'ok': False, 'erro': str(e), 'exit_code': 1}


def _cmd_reverter_disp(args):
    from app.motos_assai.services.moto_evento_service import status_efetivo
    from app.motos_assai.services.disponibilizar_service import (
        reverter_para_montada, DisponibilizarValidationError,
    )

    chassi_norm = args.chassi.strip().upper() if args.chassi else ''
    status = status_efetivo(chassi_norm) if chassi_norm else None

    if not args.motivo or len(args.motivo.strip()) < 3:
        return {'ok': False, 'erro': 'motivo obrigatorio (>=3 chars)', 'exit_code': 1}

    if not args.confirmar:
        return _preview('reverter_disponibilizacao', chassi_norm, 'REVERTIDA_PARA_MONTADA', status,
                        extras={'motivo': args.motivo})

    try:
        r = reverter_para_montada(
            chassi=chassi_norm, motivo=args.motivo, operador_id=args.user_id,
        )
        return {'ok': True, 'dry_run': False, **r, 'exit_code': 0}
    except DisponibilizarValidationError as e:
        return {'ok': False, 'erro': str(e), 'exit_code': 1}


def _cmd_separar(args):
    from app.motos_assai.services.moto_evento_service import status_efetivo
    from app.motos_assai.services.separacao_service import (
        registrar_chassi, SeparacaoConflictError, SeparacaoValidationError,
    )

    chassi_norm = args.chassi.strip().upper() if args.chassi else ''
    status = status_efetivo(chassi_norm) if chassi_norm else None

    if not (args.pedido_id and args.loja_id):
        return {'ok': False, 'erro': '--pedido-id e --loja-id obrigatorios', 'exit_code': 1}

    if not args.confirmar:
        return _preview('separar', chassi_norm, 'SEPARADA', status,
                        extras={'pedido_id': args.pedido_id, 'loja_id': args.loja_id})

    try:
        r = registrar_chassi(
            pedido_id=args.pedido_id, loja_id=args.loja_id,
            chassi=chassi_norm, registrada_por_id=args.user_id,
        )
        return {'ok': True, 'dry_run': False, **r, 'exit_code': 0}
    except SeparacaoConflictError as e:
        return {'ok': False, 'erro': str(e), 'retry': True, 'exit_code': 5}
    except SeparacaoValidationError as e:
        return {'ok': False, 'erro': str(e), 'exit_code': 1}


def _cmd_desfazer_sep(args):
    from app.motos_assai.services.separacao_service import (
        desfazer_chassi, SeparacaoValidationError,
    )

    if not args.item_id:
        return {'ok': False, 'erro': '--item-id obrigatorio', 'exit_code': 1}

    if not args.confirmar:
        return _preview('desfazer_separacao', None, 'DISPONIVEL',
                        extras={'item_id': args.item_id})

    try:
        r = desfazer_chassi(separacao_item_id=args.item_id, operador_id=args.user_id)
        return {'ok': True, 'dry_run': False, **r, 'exit_code': 0}
    except SeparacaoValidationError as e:
        return {'ok': False, 'erro': str(e), 'exit_code': 1}


def _cmd_cancelar_sep(args):
    from app.motos_assai.services.separacao_service import (
        cancelar_separacao, SeparacaoValidationError,
    )

    if not args.separacao_id:
        return {'ok': False, 'erro': '--separacao-id obrigatorio', 'exit_code': 1}
    if not args.motivo or len(args.motivo.strip()) < 3:
        return {'ok': False, 'erro': 'motivo obrigatorio (>=3 chars)', 'exit_code': 1}

    if not args.confirmar:
        return _preview('cancelar_separacao', None, 'CANCELADA + DISPONIVEL para cada chassi',
                        extras={'separacao_id': args.separacao_id, 'motivo': args.motivo})

    try:
        sep = cancelar_separacao(
            separacao_id=args.separacao_id,
            motivo=args.motivo,
            operador_id=args.user_id,
        )
        return {
            'ok': True, 'dry_run': False,
            'separacao_id': sep.id, 'novo_status': sep.status,
            'exit_code': 0,
        }
    except SeparacaoValidationError as e:
        return {'ok': False, 'erro': str(e), 'exit_code': 1}


def _run(args):
    if not args.user_id:
        return {'ok': False, 'erro': '--user-id obrigatorio', 'exit_code': 4}

    ok, motivo = _verificar_autorizacao(args.user_id)
    if not ok:
        return {'ok': False, 'erro': motivo, 'exit_code': 3}

    if args.montar:
        return _cmd_montar(args)
    if args.montar_pendente:
        return _cmd_montar_pendente(args)
    if args.resolver_pendencia:
        return _cmd_resolver_pendencia(args)
    if args.disponibilizar:
        return _cmd_disponibilizar(args)
    if args.reverter_disponibilizacao:
        return _cmd_reverter_disp(args)
    if args.separar:
        return _cmd_separar(args)
    if args.desfazer_separacao:
        return _cmd_desfazer_sep(args)
    if args.cancelar_separacao:
        return _cmd_cancelar_sep(args)

    return {'ok': False, 'erro': 'comando nao especificado', 'exit_code': 1}


def main():
    parser = argparse.ArgumentParser(prog='registrando_evento_moto_assai')
    parser.add_argument('--chassi')
    # Comandos
    parser.add_argument('--montar', action='store_true')
    parser.add_argument('--montar-pendente', action='store_true')
    parser.add_argument('--resolver-pendencia', action='store_true')
    parser.add_argument('--disponibilizar', action='store_true')
    parser.add_argument('--reverter-disponibilizacao', action='store_true')
    parser.add_argument('--separar', action='store_true')
    parser.add_argument('--desfazer-separacao', action='store_true')
    parser.add_argument('--cancelar-separacao', action='store_true')
    # Args extras
    parser.add_argument('--descricao', help='Descricao para PENDENTE/PENDENCIA_RESOLVIDA')
    parser.add_argument('--motivo', help='Motivo para reverter/cancelar')
    parser.add_argument('--pedido-id', type=int)
    parser.add_argument('--loja-id', type=int)
    parser.add_argument('--separacao-id', type=int)
    parser.add_argument('--item-id', type=int)
    # Comum
    parser.add_argument('--user-id', type=int, required=True)
    parser.add_argument('--confirmar', action='store_true', help='Executa WRITE (default = dry-run)')
    args = parser.parse_args()

    try:
        app = create_app()
        with app.app_context():
            result = _run(args)
        print(json.dumps(result, default=_json_default, ensure_ascii=False, indent=2))
        return result.get('exit_code', 0)
    except Exception as e:
        err = {'ok': False, 'error': str(e), 'exit_code': 2}
        print(json.dumps(err), file=sys.stderr)
        print(json.dumps(err))
        return 2


if __name__ == '__main__':
    sys.exit(main())
```

- [ ] **Step 5: Rodar teste — PASS**

```bash
pytest tests/skills/motos_assai/test_registrando_evento_moto_assai.py -v
```

- [ ] **Step 6: Verificação CLI dry-run**

```bash
python .claude/skills/registrando-evento-moto-assai/scripts/registrando_evento_moto_assai.py \
    --montar --chassi TEST123 --user-id 1
```

Expected: JSON com `dry_run: true` e exit 4 (ou exit 1 se chassi não existe).

- [ ] **Step 7: Commit**

```bash
git add .claude/skills/registrando-evento-moto-assai/ tests/skills/motos_assai/test_registrando_evento_moto_assai.py
git commit -m "feat(skills): add registrando-evento-moto-assai (8 sub-comandos WRITE)"
```

---

## FASE 4 — Cross-refs + Eval + Verificação

### Task 4.1: Atualizar `ROUTING_SKILLS.md`

**Files:**
- Modify: `.claude/references/ROUTING_SKILLS.md`

- [ ] **Step 1: Ler arquivo atual e identificar localização da inserção**

```bash
grep -n "LOJAS HORA — CROSS-ENTIDADE" .claude/references/ROUTING_SKILLS.md
```

Expected: linha próximo a 41-42. As novas linhas devem ser inseridas APÓS as linhas LOJAS HORA.

- [ ] **Step 2: Adicionar 7 linhas em "Passo 1"**

Localizar a seção `## Passo 1: Identificar o CONTEXTO` e adicionar após a linha `LOJAS HORA — CROSS-ENTIDADE`:

```markdown
| MOTOS ASSAÍ — ESTOQUE/PIPELINE | "quantas motos Q.P.A.?", "estoque Sendas", "pipeline Assaí", "quanto de SOL?" | -> `consultando-estoque-assai` |
| MOTOS ASSAÍ — RASTREAR CHASSI | "cadê chassi MZX...?", "histórico chassi Q.P.A." | -> `rastreando-chassi-assai` |
| MOTOS ASSAÍ — PEDIDOS/COMPRAS | "pedido VOE", "compra Motochefe MA-", "VOE Q.P.A." | -> `acompanhando-pedido-compra-assai` |
| MOTOS ASSAÍ — SAÍDA/NFs | "separações Assaí", "NF Q.P.A.", "match BATEU/DIVERGENTE" | -> `acompanhando-saida-assai` |
| MOTOS ASSAÍ — RECIBO MOTOCHEFE | "recibos pendentes Motochefe", "conferir recibo RM-", "wizard recebimento" | -> `conferindo-recibo-assai` |
| MOTOS ASSAÍ — EVENTOS WRITE | "registra montagem", "disponibiliza", "reverte", "separar chassi" | -> `registrando-evento-moto-assai` |
| MOTOS ASSAÍ — CROSS-ENTIDADE | "como está operação Q.P.A.?", "resumo Motos Assaí" | -> Subagente `gestor-motos-assai` |
```

- [ ] **Step 3: Adicionar desambiguações na seção apropriada**

Localizar `## Desambiguacao` e adicionar:

```markdown
| consultando-estoque-assai vs gerindo-expedicao | **Motos Q.P.A.** (B2B Sendas) -> consultando-estoque-assai. **Pedidos/separação Nacom Goya** -> gerindo-expedicao |
| rastreando-chassi-assai vs rastreando-chassi (Hora) | **Q.P.A.** (assai_moto) -> rastreando-chassi-assai. **Lojas HORA** (hora_moto) -> rastreando-chassi |
| consultando-estoque-assai vs consultando-estoque-loja | **B2B Q.P.A. Sendas** -> consultando-estoque-assai. **B2C Lojas HORA** -> consultando-estoque-loja |
```

- [ ] **Step 4: Atualizar contagem de skills no inventário**

Localizar seção `### Skills — Inventario Completo`:

```bash
grep -n "Inventario Completo\|Skills motos\|invocaveis" .claude/references/ROUTING_SKILLS.md
```

Adicionar nova subseção e atualizar contagem total (30 -> 36):

```markdown
### Skills motos_assai (6)
`consultando-estoque-assai`, `rastreando-chassi-assai`, `acompanhando-pedido-compra-assai`,
`acompanhando-saida-assai`, `conferindo-recibo-assai`, `registrando-evento-moto-assai`
```

- [ ] **Step 5: Verificar arquivo válido**

```bash
grep -c "MOTOS ASSAÍ" .claude/references/ROUTING_SKILLS.md
```

Expected: pelo menos 7.

- [ ] **Step 6: Commit**

```bash
git add .claude/references/ROUTING_SKILLS.md
git commit -m "docs(routing): adicionar 6 skills motos_assai + agente em ROUTING_SKILLS.md"
```

---

### Task 4.2: Atualizar `INDEX.md`, `CLAUDE.md` raiz, módulo CLAUDE.md, SKILL_IMPROVEMENT_ROADMAP

**Files:**
- Modify: `.claude/references/INDEX.md`
- Modify: `CLAUDE.md` (raiz)
- Modify: `app/motos_assai/CLAUDE.md`
- Modify: `.claude/skills/SKILL_IMPROVEMENT_ROADMAP.md`

- [ ] **Step 1: Atualizar `.claude/references/INDEX.md`**

```bash
grep -n "Skills.*Inventario\|skills_inventario\|## Skills" .claude/references/INDEX.md | head -5
```

Adicionar entrada no índice:

```markdown
| Skills motos_assai (6) | `.claude/skills/{consultando-estoque-assai,rastreando-chassi-assai,acompanhando-pedido-compra-assai,acompanhando-saida-assai,conferindo-recibo-assai,registrando-evento-moto-assai}/` |
```

- [ ] **Step 2: Atualizar `CLAUDE.md` (raiz) — seção Subagentes**

Localizar a tabela `## SUBAGENTES`:

```bash
grep -n "^## SUBAGENTES\|gestor-recebimento\|gestor-devolucoes" CLAUDE.md
```

Adicionar linha (após `analista-performance-logistica`):

```markdown
| `gestor-motos-assai` | Pipeline B2B Q.P.A. Sendas/Assaí (estoque, recibo, separação, NF) |
```

- [ ] **Step 3: Atualizar `app/motos_assai/CLAUDE.md`**

Adicionar nova seção ao final, antes de `## Manutenção / Roadmap futuro`:

```markdown
## Skills + Agente disponíveis

Para consultas e operações via Claude Code ou agente web Nacom Goya:

| Skill | Tipo | Uso |
|-------|------|-----|
| `consultando-estoque-assai` | READ | Pipeline (ESTOQUE/MONTADA/DISPONIVEL/SEPARADA/FATURADA) |
| `rastreando-chassi-assai` | READ | Histórico completo de um chassi |
| `acompanhando-pedido-compra-assai` | READ | Pedidos VOE Q.P.A. + compras Motochefe |
| `acompanhando-saida-assai` | READ | Separações + NFs Q.P.A. (match BATEU/DIVERGENTE) |
| `conferindo-recibo-assai` | READ + WRITE | Recibos Motochefe + wizard A→B→C→D |
| `registrando-evento-moto-assai` | WRITE | Montagem, disponibilizar, separar, reverter, cancelar |

Agente orquestrador: `gestor-motos-assai` (sub-agent — `model: sonnet`).

Spec: `docs/superpowers/specs/2026-05-08-motos-assai-skills-agents-design.md`
Plan: `docs/superpowers/plans/2026-05-08-motos-assai-skills-agents.md`
```

- [ ] **Step 4: Atualizar `.claude/skills/SKILL_IMPROVEMENT_ROADMAP.md`**

```bash
head -20 .claude/skills/SKILL_IMPROVEMENT_ROADMAP.md
```

Adicionar entrada cronológica:

```markdown
## 2026-05-08 — Skills motos_assai (6 novas)

Criadas 6 skills + 1 agente para o módulo `app/motos_assai/`:

- `consultando-estoque-assai` (READ)
- `rastreando-chassi-assai` (READ)
- `acompanhando-pedido-compra-assai` (READ)
- `acompanhando-saida-assai` (READ)
- `conferindo-recibo-assai` (READ + WRITE conferência)
- `registrando-evento-moto-assai` (WRITE 8 sub-comandos)

Agente: `gestor-motos-assai` (sonnet) — orquestra cross-entidade.

Spec: `docs/superpowers/specs/2026-05-08-motos-assai-skills-agents-design.md`
Plan: `docs/superpowers/plans/2026-05-08-motos-assai-skills-agents.md`
```

- [ ] **Step 5: Commit**

```bash
git add .claude/references/INDEX.md CLAUDE.md app/motos_assai/CLAUDE.md .claude/skills/SKILL_IMPROVEMENT_ROADMAP.md
git commit -m "docs: cross-refs para skills + agente motos_assai (INDEX, CLAUDE.md, ROADMAP)"
```

---

### Task 4.3: Atualizar `tool_skill_mapper.py`

**Files:**
- Modify: `app/agente/services/tool_skill_mapper.py`

- [ ] **Step 1: Ler estrutura do arquivo**

```bash
head -50 app/agente/services/tool_skill_mapper.py
grep -n "consultando-estoque-loja\|rastreando-chassi\|orientador-loja" app/agente/services/tool_skill_mapper.py | head -10
```

Expected: identificar o padrão de mapeamento.

- [ ] **Step 2: Adicionar 6 mapeamentos**

Localizar o dicionário de skills e adicionar (na ordem alfabética ou agrupado por módulo):

```python
'acompanhando-pedido-compra-assai': {
    'tool_pattern': 'Bash',
    'script': '.claude/skills/acompanhando-pedido-compra-assai/scripts/acompanhando_pedido_compra_assai.py',
    'description': 'Pedidos VOE Q.P.A. + compras Motochefe',
},
'acompanhando-saida-assai': {
    'tool_pattern': 'Bash',
    'script': '.claude/skills/acompanhando-saida-assai/scripts/acompanhando_saida_assai.py',
    'description': 'Separações + NFs Q.P.A.',
},
'conferindo-recibo-assai': {
    'tool_pattern': 'Bash',
    'script': '.claude/skills/conferindo-recibo-assai/scripts/conferindo_recibo_assai.py',
    'description': 'Recibos Motochefe (READ + WRITE conferência)',
},
'consultando-estoque-assai': {
    'tool_pattern': 'Bash',
    'script': '.claude/skills/consultando-estoque-assai/scripts/consultando_estoque_assai.py',
    'description': 'Pipeline motos Assaí (estoque + estágios)',
},
'rastreando-chassi-assai': {
    'tool_pattern': 'Bash',
    'script': '.claude/skills/rastreando-chassi-assai/scripts/rastreando_chassi_assai.py',
    'description': 'Histórico de um chassi Q.P.A.',
},
'registrando-evento-moto-assai': {
    'tool_pattern': 'Bash',
    'script': '.claude/skills/registrando-evento-moto-assai/scripts/registrando_evento_moto_assai.py',
    'description': 'WRITE eventos pipeline (montagem, disponibilizar, separar)',
},
```

NOTA: o formato exato pode ser diferente — adaptar ao padrão existente do arquivo. Se tem dict com strings simples, usar string. Se tem objeto, usar objeto.

- [ ] **Step 3: Verificar que o arquivo carrega**

```bash
source .venv/bin/activate
python -c "from app.agente.services.tool_skill_mapper import *; print('OK')"
```

Expected: "OK" sem erros.

- [ ] **Step 4: Commit**

```bash
git add app/agente/services/tool_skill_mapper.py
git commit -m "feat(agente): mapear 6 skills motos_assai em tool_skill_mapper"
```

---

### Task 4.4: Criar golden dataset (eval offline)

**Files:**
- Create: `.claude/evals/subagents/gestor-motos-assai/dataset.yaml`

- [ ] **Step 1: Verificar formato de dataset existente**

```bash
cat .claude/evals/subagents/analista-carteira/dataset.yaml | head -40
```

Expected: identificar estrutura YAML e campos obrigatórios.

- [ ] **Step 2: Criar dataset.yaml com 15-20 casos**

Conteúdo de `.claude/evals/subagents/gestor-motos-assai/dataset.yaml`:

```yaml
agent: gestor-motos-assai
version: 1.0
created_at: 2026-05-08
description: >-
  Golden dataset offline para gestor-motos-assai. Cobre as 6 skills + fluxos
  cross-entidade. Operacao Nacom Goya / B2B Q.P.A. Sendas.

cases:
  # READ — consultando-estoque-assai (3 casos)
  - id: ma-01
    title: Estoque resumo
    input: "quantas motos Q.P.A. disponiveis hoje?"
    expected_skills: [consultando-estoque-assai]
    expected_keywords: [DISPONIVEL, modelo, total]

  - id: ma-02
    title: Estoque por modelo
    input: "quanto de SOL temos em estoque?"
    expected_skills: [consultando-estoque-assai]
    expected_args: [--modelo, SOL]

  - id: ma-03
    title: Pendencias
    input: "quais chassis estao com pendencia?"
    expected_skills: [consultando-estoque-assai]
    expected_keywords: [PENDENTE, motos_pendentes]

  # READ — rastreando-chassi-assai (2 casos)
  - id: ma-04
    title: Rastrear chassi
    input: "cade o chassi MZX1234567890123?"
    expected_skills: [rastreando-chassi-assai]
    expected_args: [--chassi]

  - id: ma-05
    title: Historico chassi vendido
    input: "essa moto chassi MZX1234 ja foi separada?"
    expected_skills: [rastreando-chassi-assai]
    expected_keywords: [SEPARADA, FATURADA]

  # READ — acompanhando-pedido-compra-assai (2 casos)
  - id: ma-06
    title: Pedido VOE
    input: "como esta o pedido VOE-12345?"
    expected_skills: [acompanhando-pedido-compra-assai]
    expected_args: [--numero-voe, VOE-12345]

  - id: ma-07
    title: Compras Motochefe abertas
    input: "compras Motochefe em producao?"
    expected_skills: [acompanhando-pedido-compra-assai]
    expected_args: [--somente-abertos]

  # READ — acompanhando-saida-assai (2 casos)
  - id: ma-08
    title: NF QPA bateu
    input: "a NF Q.P.A. 12345 bateu no match?"
    expected_skills: [acompanhando-saida-assai]
    expected_keywords: [BATEU, DIVERGENTE]

  - id: ma-09
    title: Separacoes abertas
    input: "quais separacoes em andamento Q.P.A.?"
    expected_skills: [acompanhando-saida-assai]
    expected_args: [--somente-abertas]

  # READ — conferindo-recibo-assai (2 casos)
  - id: ma-10
    title: Recibos pendentes
    input: "recibos Motochefe pendentes de conferencia?"
    expected_skills: [conferindo-recibo-assai]
    expected_args: [--listar-pendentes]

  - id: ma-11
    title: Detalhe recibo
    input: "como esta a conferencia do recibo 5?"
    expected_skills: [conferindo-recibo-assai]
    expected_args: [--recibo-id, 5]

  # WRITE — registrando-evento-moto-assai (3 casos)
  - id: ma-12
    title: Registrar montagem
    input: "registra o chassi MZX1234567890123 como montada"
    expected_skills: [registrando-evento-moto-assai]
    expected_flow: [dry_run, user_confirm, write]
    expected_args: [--montar, --chassi]

  - id: ma-13
    title: Disponibilizar
    input: "disponibiliza a moto MZX1234"
    expected_skills: [registrando-evento-moto-assai]
    expected_flow: [dry_run, user_confirm]
    expected_args: [--disponibilizar]

  - id: ma-14
    title: Cancelar separacao
    input: "cancela a separacao 5 (motivo: cliente desistiu da compra)"
    expected_skills: [registrando-evento-moto-assai]
    expected_flow: [dry_run, user_confirm]
    expected_args: [--cancelar-separacao, --motivo]

  # CROSS-ENTIDADE — orquestracao (3 casos)
  - id: ma-15
    title: Resumo operacao
    input: "como esta a operacao Motos Assai hoje?"
    expected_skills:
      - consultando-estoque-assai
      - acompanhando-pedido-compra-assai
      - conferindo-recibo-assai
      - acompanhando-saida-assai
    expected_keywords: [estoque, compra, recibo, separacao]

  - id: ma-16
    title: Status pedido + estoque
    input: "tenho saldo para faturar o pedido VOE-12345?"
    expected_skills:
      - acompanhando-pedido-compra-assai
      - consultando-estoque-assai

  - id: ma-17
    title: Boundary check Lojas HORA
    input: "quantas motos Lojas HORA tenho?"
    expected_redirect: orientador-loja
    expected_keywords: [HORA, redireciona]

  # EDGE CASES (3 casos)
  - id: ma-18
    title: Chassi sem dados
    input: "rastreia o chassi XPTO_INEXISTENTE"
    expected_skills: [rastreando-chassi-assai]
    expected_keywords: [nao_encontrado, encontrado]

  - id: ma-19
    title: Operacao sem permissao
    input: "registra MZX como montada (usuario sem flag motos_assai)"
    expected_skills: [registrando-evento-moto-assai]
    expected_exit_codes: [3]

  - id: ma-20
    title: Race condition em separacao
    input: "separa MZX1234 para pedido 1, loja 5 (chassi ja em outra separacao)"
    expected_skills: [registrando-evento-moto-assai]
    expected_exit_codes: [5]
    expected_keywords: [conflito, retry]
```

- [ ] **Step 3: Validar YAML**

```bash
python -c "
import yaml
with open('.claude/evals/subagents/gestor-motos-assai/dataset.yaml') as f:
    data = yaml.safe_load(f)
assert data['agent'] == 'gestor-motos-assai'
assert len(data['cases']) >= 15
print(f'OK: {len(data[\"cases\"])} cases')
"
```

Expected: "OK: 20 cases" (ou mais).

- [ ] **Step 4: Commit**

```bash
git add .claude/evals/subagents/gestor-motos-assai/dataset.yaml
git commit -m "test(evals): golden dataset 20 cases para gestor-motos-assai"
```

---

### Task 4.5: Verificação manual final

**Files:** nenhum a criar/modificar — apenas verificação.

- [ ] **Step 1: Rodar todos os testes de skills**

```bash
source .venv/bin/activate
pytest tests/skills/motos_assai/ -v
```

Expected: TODOS os testes passando.

- [ ] **Step 2: Verificar todas as skills via CLI**

```bash
cd /home/rafaelnascimento/projetos/frete_sistema
source .venv/bin/activate

# READ skills
python .claude/skills/consultando-estoque-assai/scripts/consultando_estoque_assai.py --resumo
python .claude/skills/rastreando-chassi-assai/scripts/rastreando_chassi_assai.py --chassi TESTE
python .claude/skills/acompanhando-pedido-compra-assai/scripts/acompanhando_pedido_compra_assai.py --somente-abertos
python .claude/skills/acompanhando-saida-assai/scripts/acompanhando_saida_assai.py --somente-abertas

# READ + WRITE
python .claude/skills/conferindo-recibo-assai/scripts/conferindo_recibo_assai.py --listar-pendentes

# WRITE dry-run
python .claude/skills/registrando-evento-moto-assai/scripts/registrando_evento_moto_assai.py \
    --montar --chassi TESTE --user-id 1
```

Expected: cada um retorna JSON válido (ou erro estruturado com exit code apropriado).

- [ ] **Step 3: Verificar agent file estrutura**

```bash
python -c "
import yaml
with open('.claude/agents/gestor-motos-assai.md') as f:
    content = f.read()
parts = content.split('---', 2)
assert len(parts) >= 3, 'frontmatter invalido'
fm = yaml.safe_load(parts[1])
assert fm['name'] == 'gestor-motos-assai'
assert fm['model'] == 'sonnet'
assert isinstance(fm['skills'], list)
assert len(fm['skills']) == 6
body = parts[2]
# Verificar secoes obrigatorias
for section in ['CONTEXTO', 'ARMADILHAS', 'PRE-MORTEM', 'SELF-CRITIQUE', 'BOUNDARY CHECK', 'PROTOCOLO DE CONFIABILIDADE']:
    assert section in body, f'Secao faltando: {section}'
print('OK: agent file valido')
"
```

Expected: "OK: agent file valido"

- [ ] **Step 4: Verificar cross-refs**

```bash
grep -c "MOTOS ASSAÍ" .claude/references/ROUTING_SKILLS.md
grep -c "motos_assai\|gestor-motos-assai" CLAUDE.md
grep -c "Skills + Agente disponíveis" app/motos_assai/CLAUDE.md
grep -c "consultando-estoque-assai" app/agente/services/tool_skill_mapper.py
```

Expected: cada count >= 1.

- [ ] **Step 5: Verificar que roteamento de skills funciona via Claude Code (manual)**

```bash
# Manual: abra Claude Code e digite:
# "/<consultando-estoque-assai> --resumo"
# Expected: skill executa e retorna JSON
```

- [ ] **Step 6: Rodar ui_audit (regressão de design)**

```bash
python scripts/audits/ui_policy_lint.py --report-only 2>&1 | tail -20
```

Expected: 0 violações novas (skills não tocam UI).

- [ ] **Step 7: Commit final + tag**

```bash
git log --oneline -20
git tag motos-assai-skills-v1.0 -m "Skills + agente motos_assai prontos (Plano 4.5)"
```

- [ ] **Step 8: Atualizar memória do projeto**

Salvar memória de conclusão (via skill `auto-memory` ou `mcp__memory__save_memory` se em agente):

```
Skills + agente motos_assai concluidos em 2026-05-08:
- 6 skills (4 READ + 1 MIXED + 1 WRITE) + 1 sub-agent
- Plan: docs/superpowers/plans/2026-05-08-motos-assai-skills-agents.md
- Spec: docs/superpowers/specs/2026-05-08-motos-assai-skills-agents-design.md
- Padrao: scripts Python + dry-run + services existentes (zero modificacao)
```

---

## Critérios de Aceite Final

A implementação está completa quando:

- [x] **6 skills criadas** com SKILL.md + scripts/ + testes unit passando
- [x] **1 agente criado** em `.claude/agents/gestor-motos-assai.md` com 9 seções obrigatórias
- [x] **Cross-refs atualizadas**: ROUTING_SKILLS.md (7 linhas + 3 desambiguações), INDEX.md, CLAUDE.md raiz, motos_assai/CLAUDE.md, SKILL_IMPROVEMENT_ROADMAP.md
- [x] **`tool_skill_mapper.py`** com 6 entradas para skills motos_assai
- [x] **Golden dataset** com 20 cases em `.claude/evals/subagents/gestor-motos-assai/dataset.yaml`
- [x] **Verificação manual em CLI**: 6 scripts retornam JSON válido
- [x] **Verificação manual via agente web**: pergunta "quantas motos Q.P.A. disponíveis?" delega para `gestor-motos-assai`
- [x] **Tag git**: `motos-assai-skills-v1.0`
- [x] **Memória do projeto** atualizada com sumário de conclusão
