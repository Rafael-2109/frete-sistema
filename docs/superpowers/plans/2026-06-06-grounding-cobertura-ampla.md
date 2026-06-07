<!-- doc:meta
tipo: how-to
camada: L2
sot_de: plano TDD do grounding de estrutura (cobertura ampla) — item I2 da estrategia de atuadores, redesenhado pos-mineracao 2026-06-06
hub: docs/blueprint-agente/EXECUCAO.md
superseded_by: —
atualizado: 2026-06-06
-->

# Grounding de estrutura (cobertura ampla) — Implementation Plan

> **Papel:** plano de implementação TDD do atuador contra a alucinação de estrutura do Agente Web, redesenhado a partir da causa raiz dissecada (workflow resolvendo-problemas, Fases 0-2) e da mineração PROD. Substitui `2026-06-06-grounding-verificador-turno-principal.md` (DESCARTADO — baseado em premissa refutada).

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:subagent-driven-development (recommended) ou superpowers:executing-plans. Steps com checkbox (`- [ ]`).

## Indice
- [Goal / Architecture / Tech Stack](#goal)
- [O problema (definição validada)](#o-problema-definicao-validada)
- [Por que este desenho (e o que foi descartado)](#por-que-este-desenho-e-o-que-foi-descartado)
- [File Structure](#file-structure)
- [Task 1: MCP tool resolver (fonte-que-prova determinística)](#task-1-mcp-tool-resolver-fonte-que-prova-deterministica)
- [Task 2: Registrar a tool no client](#task-2-registrar-a-tool-no-client)
- [Task 3: Regra constitucional L2 de grounding](#task-3-regra-constitucional-l2-de-grounding)
- [Self-Review](#self-review)
- [Fora de escopo / próximas fatias](#fora-de-escopo-proximas-fatias)

## Goal

Reduzir a alucinação de estrutura do Agente Web instalando **a obrigação de ancorar afirmações sobre artefatos do sistema na fonte que PROVA** — no ponto mais forte possível para o momento-da-afirmação (regra constitucional L2, que vence "responder direto") — e tornando a fonte determinística de entidade **acessível** como ferramenta direta.

**Architecture:** Duas frentes. (A) **Núcleo comportamental** — estende `<constitutional_hierarchy>` L2 (ética, já vence L4-utilidade) com a regra de grounding de estrutura: afirmar existência/tipo de campo/tabela/tela/rota/entidade exige a fonte que prova; "consulta vazia ≠ inexistência"; sem prova, declarar incerteza e nunca delegar a verificação ao usuário. (B) **Apoio técnico** — expõe os `resolvedores/` determinísticos (que consultam o dado real) como MCP tool `mcp__resolver`, reduzindo o atrito de confirmar entidade/produto/transportadora (hoje só via skill opt-in). A regra (A) aponta para as fontes que provam, incluindo a tool (B).

**Ressalva de escopo (validação adversarial I3 — não vender cobertura a mais):** "cobertura ampla" = a **regra (A)** cobre as 3 formas; o **reforço determinístico (B)** cobre só entidade/produto/transportadora. Tela (549) e campo (83) dependem só da regra (A). E `resolvendo-entidades` já era acessível ao agente principal (`skills_whitelist.py:99-104`, fora da deny-list) — a tool (B) reduz ATRITO, não desbloqueia.

**Tech Stack:** Python 3.12 · Claude Agent SDK (`@enhanced_tool` + `create_enhanced_mcp_server`) · `app/resolvedores/` (determinístico, consulta Postgres) · system_prompt.md · pytest.

## O problema (definição validada)

> O agente afirma um fato sobre o sistema — *existe / não existe / é do tipo tal* — apoiado em evidência que **não basta para decidir aquilo** (doc que só descreve; consulta que voltou vazia; primeira correspondência sem confirmar; algo de cabeça) — e apresenta **com certeza**. Às vezes nem confere; às vezes confere mal. Nada o obriga, antes de afirmar, a checar se a evidência prova aquilo.

3 formas (casos PROD reais): **existência+** (549 tela inexistente via doc; 83 campo inexistente), **existência−** (669 "não existe" baseado em consulta vazia — a tabela existe), **identidade** (645 transportadora errada gravada). Detalhe: `/tmp/subagent-findings/20260606-grounding-mecanismo/phase2/analysis.md` + `phase1/question-5-mineracao-ampla.md`.

## Por que este desenho (e o que foi descartado)

- **Verdade técnica:** no instante em que o agente AFIRMA em texto, não há tool nem hook — então **não existe atuador 100% determinístico** ali; o teto é uma regra.
- **Canal = L2 (decidido, com fundamento — após investigar `<user_rules>`):** o `<user_rules>` foi validado em 89% (AgingBench, `memory/avaliacao_memoria_agente_2026_06.md:60,66`) MAS para **correção PESSOAL reincidente** — tem cap de 12 (`MANDATORY_RULES_MAX_COUNT`, `feature_flags.py:506`) ordenado por `correction_count DESC` (`memory_injection_rules.py:39`), então uma regra GLOBAL nova (correction_count=0) seria **cortável**/competiria, e o canal é semanticamente "regras salvas pelo usuário" (`:49`), curado de propósito. Uma regra GLOBAL de comportamento pertence ao **system_prompt** (junto de R0–R12). Divisão de trabalho: **regra geral → L2**; **correção específica que reincide** (uma tela/campo/entidade) → o canal `<user_rules>` via o loop corretivo já existente (§3a, `correction_count`) — exatamente o uso para o qual o canal foi validado. Honestidade: não há evidência de que L2 iguale o `<user_rules>` em força bruta — por isso **medir adesão** por `error_signature` (Self-Review) é parte do plano; se a adesão for baixa, a saída NÃO é mudar este canal, é endurecer (ex.: PostToolUse no WRITE, fatia 2).
- **As ferramentas que provam já existem** — `consultar_schema`, `search_routes`, `Grep`, e os `resolvedores/`. O que falta é a OBRIGAÇÃO de usá-las antes de afirmar + a de entidade estar acessível.
- **Descartado:** detector POST com Haiku (modelo fraco audita forte; rejeitado); `verify_domain` (`verifiers.py:155` — POST + depende da ontologia canônica, que está **vazia na prática**, KG graph=0; shadow); schema-checker isolado (não pega tela/PDF/consulta-vazia — os casos reais).

## File Structure

| Arquivo | Responsabilidade | Task |
|---|---|---|
| `app/agente/tools/resolver_mcp_tool.py` (criar) | MCP tool `mcp__resolver__resolver_entidade` — wrapper fino sobre `app/resolvedores/` (produto/transportadora/cliente). Determinístico. `encontrado=false` explícito. | 1 |
| `tests/agente/test_resolver_mcp_tool.py` (criar) | Testes do núcleo `_resolver_entidade` (mock dos resolvedores — sem banco). | 1 |
| `app/agente/sdk/client.py` (modificar ~:1883) | Registrar `resolver_server` via `_register_mcp("resolver", resolver_server)`. | 2 |
| `app/agente/prompts/system_prompt.md` (modificar `<constitutional_hierarchy>` L2, ~:53) | Regra de grounding de estrutura no nível constitucional. | 3 |
| `tests/agente/test_grounding_l2.py` (criar) | Teste de presença da regra L2 (guard anti-remoção). | 3 |

---

## Task 1: MCP tool resolver (fonte-que-prova determinística)

**Files:**
- Create: `app/agente/tools/resolver_mcp_tool.py`
- Test: `tests/agente/test_resolver_mcp_tool.py`

O núcleo (`_resolver_entidade`) é função pura testável; o `@enhanced_tool` é só o invólucro (espelha `routes_search_tool.py:149/293`). `encontrado` é explícito para a regra L2 poder distinguir "confirmei que não existe" de "não procurei".

- [ ] **Step 1: (CONFIRMADO na validação adversarial — B1)** usar a função CERTA por tipo:
  - cliente → **`resolver_cliente_cli(termo)`** (chave `'clientes'`, shape `{cnpj,nome,cidade,uf}`). **NÃO** `resolver_cliente` — essa retorna `clientes_encontrados` (shape diferente); usá-la faria `encontrado` sair sempre `False` → a tool afirmaria inexistência de cliente que existe = o próprio erro 669 que ela deve curar. FONTE: `app/resolvedores/cliente.py:144,183` (cli) vs `:25,118`.
  - produto → `resolver_produto(termo, limit)` → lista `{cod_produto,nome_produto,score}` (`produto.py:15`).
  - transportadora → `resolver_transportadora(termo, limite)` → `{transportadoras:[...]}` (`transportadora.py:10`).

- [ ] **Step 2: Escrever o teste que falha (núcleo, mock dos resolvedores)**

```python
# tests/agente/test_resolver_mcp_tool.py
"""Testa o nucleo _resolver_entidade com os resolvedores mockados (sem banco).
'encontrado' deve refletir se o resolvedor achou — base para a regra L2
'consulta vazia != inexistencia'."""
from app.agente.tools import resolver_mcp_tool as rt


def test_produto_encontrado(monkeypatch):
    monkeypatch.setattr(rt, '_resolver_produto',
                        lambda termo, limit=10: [{'cod_produto': '12345', 'nome_produto': 'PALMITO', 'score': 9}])
    r = rt._resolver_entidade('produto', 'palmito')
    assert r['encontrado'] is True
    assert r['candidatos'][0]['cod_produto'] == '12345'


def test_produto_inexistente_marca_nao_encontrado(monkeypatch):
    monkeypatch.setattr(rt, '_resolver_produto', lambda termo, limit=10: [])
    r = rt._resolver_entidade('produto', 'xyz_produto_inexistente_999')
    assert r['encontrado'] is False
    assert r['candidatos'] == []


def test_transportadora_encontrada(monkeypatch):
    monkeypatch.setattr(rt, '_resolver_transportadora',
                        lambda termo, limite=10: {'sucesso': True, 'transportadoras': [{'id': 338, 'razao_social': 'ANDRE SILVA BARROS'}], 'total': 1})
    r = rt._resolver_entidade('transportadora', 'andre silva')
    assert r['encontrado'] is True
    assert r['candidatos'][0]['id'] == 338


def test_cliente_usa_funcao_cli_e_chave_clientes(monkeypatch):
    # B1 guard: _resolver_cliente DEVE chamar resolver_cliente_cli (chave 'clientes'),
    # nao resolver_cliente (chave 'clientes_encontrados'). Mock na funcao-fonte CERTA:
    # se a impl usar a funcao errada, o mock nao e' chamado e encontrado sai False -> teste quebra.
    import app.resolvedores.cliente as cli
    monkeypatch.setattr(cli, 'resolver_cliente_cli',
                        lambda termo: {'sucesso': True, 'clientes': [{'cnpj': '123', 'nome': 'ACME'}], 'total': 1})
    r = rt._resolver_entidade('cliente', 'acme')
    assert r['encontrado'] is True
    assert r['candidatos'][0]['nome'] == 'ACME'


def test_tipo_invalido():
    r = rt._resolver_entidade('banana', 'x')
    assert r['encontrado'] is False
    assert 'erro' in r
```

- [ ] **Step 3: Rodar e confirmar falha**

Run: `pytest tests/agente/test_resolver_mcp_tool.py -v`
Expected: FAIL com `ModuleNotFoundError: ... resolver_mcp_tool`

- [ ] **Step 4: Implementar a tool**

```python
# app/agente/tools/resolver_mcp_tool.py
"""MCP tool 'resolver' — expõe os resolvedores DETERMINÍSTICOS (app.resolvedores)
como fonte-que-prova de entidade/produto/transportadora/cliente.

Item grounding (cobertura ampla): a regra constitucional L2 obriga ancorar
afirmações de entidade na fonte que prova; esta tool é essa fonte, acessível
direto (menos atrito que a skill resolvendo-entidades). Consulta o dado real;
'encontrado=false' é EXPLÍCITO para a regra 'consulta vazia != inexistência'
distinguir 'confirmei que não existe' de 'não procurei'.
"""
import logging

logger = logging.getLogger('sistema_fretes')


# Indireções nomeadas (facilitam mock no teste; importam lazy o resolvedor real)
def _resolver_produto(termo, limit=10):
    from app.resolvedores.produto import resolver_produto
    return resolver_produto(termo, limit=limit) or []


def _resolver_transportadora(termo, limite=10):
    from app.resolvedores.transportadora import resolver_transportadora
    return resolver_transportadora(termo, limite=limite) or {}


def _resolver_cliente(termo):
    # B1: resolver_cliente_cli (chave 'clientes'), NAO resolver_cliente (chave 'clientes_encontrados')
    from app.resolvedores.cliente import resolver_cliente_cli
    return resolver_cliente_cli(termo) or {}


def _resolver_entidade(tipo: str, termo: str) -> dict:
    """Núcleo determinístico (testável sem SDK/banco via mock). Retorna dict normalizado."""
    t = (tipo or '').strip().lower()
    termo = (termo or '').strip()
    if not termo:
        return {'tipo': t, 'termo': termo, 'encontrado': False, 'erro': 'termo vazio'}

    if t == 'produto':
        rows = _resolver_produto(termo, limit=10)
        return {'tipo': 'produto', 'termo': termo, 'encontrado': bool(rows), 'candidatos': rows[:10]}
    if t == 'transportadora':
        r = _resolver_transportadora(termo, limite=10)
        cands = r.get('transportadoras', []) if isinstance(r, dict) else []
        return {'tipo': 'transportadora', 'termo': termo, 'encontrado': bool(cands), 'candidatos': cands[:10]}
    if t == 'cliente':
        r = _resolver_cliente(termo)
        cands = r.get('clientes', []) if isinstance(r, dict) else []  # resolver_cliente_cli -> 'clientes' (B1)
        return {'tipo': 'cliente', 'termo': termo, 'encontrado': bool(cands), 'candidatos': cands[:10]}
    return {'tipo': t, 'termo': termo, 'encontrado': False,
            'erro': f"tipo invalido: {tipo} (use produto|transportadora|cliente)"}


def _format_resultado(r: dict) -> str:
    if r.get('erro'):
        return f"resolver({r.get('tipo')},'{r.get('termo')}'): ERRO — {r['erro']}"
    if not r['encontrado']:
        return (f"resolver({r['tipo']},'{r['termo']}'): NÃO ENCONTRADO (busca no banco, inclui "
                f"correspondência aproximada). Indica inexistência PROVÁVEL — confirme em fonte "
                f"exata antes de afirmar 'não existe'. Mas já é diferente de 'não procurei' (M1).")
    return f"resolver({r['tipo']},'{r['termo']}'): {len(r['candidatos'])} encontrado(s) — {r['candidatos'][:5]}"


try:
    from claude_agent_sdk import ToolAnnotations  # noqa: F401
    from app.agente.tools._mcp_enhanced import enhanced_tool, create_enhanced_mcp_server

    @enhanced_tool(
        "resolver_entidade",
        "Resolve (confirma na FONTE REAL do banco) uma entidade do sistema: tipo=produto|transportadora|cliente + termo. "
        "Use ANTES de afirmar que uma entidade existe/é de tal tipo. 'encontrado=false' = confirmado inexistente.",
        {"tipo": str, "termo": str},
    )
    async def resolver_entidade(args):
        try:
            r = _resolver_entidade(args.get("tipo", ""), args.get("termo", ""))
            return {
                "content": [{"type": "text", "text": _format_resultado(r)}],
                "structuredContent": r,
            }
        except Exception as e:
            logger.error(f"[RESOLVER] erro: {e}")
            return {"content": [{"type": "text", "text": f"Erro ao resolver: {str(e)[:200]}"}],
                    "is_error": True}

    resolver_server = create_enhanced_mcp_server(name="resolver", version="1.0.0", tools=[resolver_entidade])
    logger.info("[RESOLVER] Custom Tool MCP 'resolver' registrado (1 tool)")
except ImportError as e:
    resolver_server = None
    logger.debug(f"[RESOLVER] claude_agent_sdk nao disponivel: {e}")
```

- [ ] **Step 5: Rodar e confirmar que passa**

Run: `pytest tests/agente/test_resolver_mcp_tool.py -v`
Expected: 4 passed.

- [ ] **Step 6: Commit**

```bash
git add app/agente/tools/resolver_mcp_tool.py tests/agente/test_resolver_mcp_tool.py
git commit -m "feat(agente/grounding): MCP tool resolver (fonte-que-prova deterministica de entidade)"
```

---

## Task 2: Registrar a tool no client

**Files:**
- Modify: `app/agente/sdk/client.py` (junto ao registro de `schema_server`, ~:1883)

- [ ] **Step 1: Ler o bloco de registro para casar o padrão exato**

Run: `sed -n '1875,1900p' app/agente/sdk/client.py`
Confirmar a forma de `_register_mcp("schema", schema_server)` e replicar.

- [ ] **Step 2: Adicionar o registro (espelhando schema)**

Em bloco try/except PRÓPRIO (M2 — não acoplar ao try do schema; espelhar o registro de `sessions` em `client.py:1891-1900`), logo após o bloco do schema:

```python
            try:
                from ..tools.resolver_mcp_tool import resolver_server
                _register_mcp("resolver", resolver_server)  # mcp__resolver__resolver_entidade
            except Exception as e:
                logger.debug(f"[client] MCP resolver indisponivel: {e}")
```

- [ ] **Step 3: Verificar que o servidor sobe sem erro de import**

Run: `python -c "from app.agente.tools.resolver_mcp_tool import resolver_server; print('resolver_server:', resolver_server is not None)"`
Expected: imprime `resolver_server: True` (ou `False` só se o SDK não estiver instalado no ambiente — aceitável em dev sem SDK; em PROD é True).

- [ ] **Step 4: Commit**

```bash
git add app/agente/sdk/client.py
git commit -m "feat(agente/grounding): registra MCP 'resolver' no client (mcp_servers)"
```

---

## Task 3: Regra constitucional L2 de grounding

**Files:**
- Modify: `app/agente/prompts/system_prompt.md` (bloco `<constitutional_hierarchy>`, nível `L2 — ETICA`, ~:53)
- Test: `tests/agente/test_grounding_l2.py`

Núcleo de cobertura. Vai em L2 (que **já tem precedência sobre L4-utilidade**) — resolve a causa final (veracidade estrutural vence "responder direto"). Princípio + mapa fonte-por-tipo (curto); sem inlinar procedimento (governança do prompt).

- [ ] **Step 1: Escrever o teste de presença (guard)**

```python
# tests/agente/test_grounding_l2.py
def test_l2_tem_grounding_de_estrutura():
    with open('app/agente/prompts/system_prompt.md', encoding='utf-8') as f:
        txt = f.read().lower()
    # I1: ancorar em strings UNICAS (grep=0 hoje). 'resolver' e 'nao encontrei' JA existem
    # no prompt -> dariam falso-verde. 'mcp__resolver' e a frase da regra nao existem ainda.
    assert 'grounding de estrutura' in txt
    assert 'mcp__resolver' in txt                              # tool de entidade citada na regra
    assert 'nao prova inexistencia' in txt or 'não prova inexistência' in txt  # frase unica da regra
```

- [ ] **Step 2: Rodar e confirmar falha**

Run: `pytest tests/agente/test_grounding_l2.py -v`
Expected: FAIL (`assert 'grounding de estrutura' in txt`)

- [ ] **Step 3: Inserir a regra em L2** (após a linha "Distinguir fato verificado de inferencia. ...")

```
      Grounding de estrutura: afirmar existencia/estrutura/tipo de um artefato do sistema
      (campo, tabela, tela, rota, tipo de entidade, modelo/produto) exige a fonte que PROVA:
      consultar_schema (campo/tabela) · search_routes + o template (tela/rota) ·
      mcp__resolver (entidade/produto/transportadora/cliente) · ler o arquivo (codigo).
      Fonte que so DESCREVE (doc, resumo, CLAUDE.md) NAO prova. Consulta VAZIA NAO prova
      inexistencia — "nao encontrei" != "nao existe"; para afirmar que algo NAO existe,
      confirme na fonte autoritativa. Sem a fonte que prova: declare incerteza ("nao confirmei,
      vou verificar") — NUNCA afirme com certeza nem mande o usuario conferir por voce.
      Isto e L2: tem precedencia sobre concisao/rapidez (L4).
```

- [ ] **Step 4: Rodar o teste de presença e confirmar que passa**

Run: `pytest tests/agente/test_grounding_l2.py -v`
Expected: PASS

- [ ] **Step 5: Atualizar baseline de tamanho do prompt (poda consciente — a regra cresce o prompt)**

Run: `python scripts/audits/prompt_size_audit.py --update-baseline --update-claude-md`
Expected: baseline + bloco auto-medido do `app/agente/CLAUDE.md` atualizados.

- [ ] **Step 6: Commit**

```bash
git add app/agente/prompts/system_prompt.md app/agente/CLAUDE.md scripts/audits/prompt_size_baseline.json tests/agente/test_grounding_l2.py
git commit -m "feat(agente/grounding): regra constitucional L2 de grounding de estrutura (nucleo cobertura ampla)"
```

---

## Self-Review

**1. Cobertura (contra a definição validada + 3 formas):**
- existência+ (549/83): L2 obriga a fonte que prova (template/schema) antes de afirmar. ✅
- existência− (669): L2 "consulta vazia ≠ inexistência" + `mcp__resolver` retorna `encontrado=false` EXPLÍCITO (confirma inexistência vs "não procurei"). ✅
- identidade (645): `mcp__resolver` (transportadora ≠ cliente, determinístico) + L2 obriga confirmar antes de afirmar/gravar. ✅
- causa final (utilidade vence veracidade): regra em L2, que vence L4. ✅
- "não delegar verificação ao usuário": explícito na regra. ✅

**2. Honestidade (sem vender determinismo onde não há):** o núcleo é comportamental (regra) — declarado; é o teto possível no momento-da-afirmação (texto não passa por hook). A tool resolver é o apoio determinístico para o tipo de maior dano (entidade). ✅

**3. Placeholder scan:** sem TODO/"add error handling". Único ponto a confirmar (chave de `resolver_cliente`) tem Step explícito (Task 1 Step 1). ✅

**4. Consistência de nomes:** `_resolver_entidade`/`_resolver_produto`/`_resolver_transportadora`/`_resolver_cliente`/`resolver_server` consistentes entre Task 1 e 2; `mcp__resolver` citado na regra (Task 3) = tool registrada (Task 2). ✅

## Fora de escopo / próximas fatias
- Hook determinístico no WRITE de entidade (garantia 100% no subconjunto que vira escrita — ex.: travar UPDATE de frete com transportadora não-confirmada). Decisão "Garantia estreita" foi preterida nesta fatia; vira fatia 2 se a cobertura ampla não bastar.
- Perda de contexto intra-sessão (caso 692) — fenômeno distinto, não tratado aqui.
- Medir efeito: reincidência por `error_signature` das 3 formas após a fatia (não construir antes de medir necessidade).
