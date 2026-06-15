<!-- doc:meta
tipo: explanation
camada: L3
sot_de: design da consolidacao dos 7 resolvedores de entidades em app/resolvedores (Onda D / Caminho C) — EXECUTADA
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-12
-->
# Spec — Consolidação de `resolver_entidades` em `app/resolvedores/` (Onda D / Caminho C)

> **Papel:** Spec — Consolidação de `resolver_entidades` em `app/resolvedores/` (Onda D / Caminho C).

## Indice

- [1. Objetivo](#1-objetivo)
- [2. Achados da Fase 0 (reverificação AO VIVO — correções ao mapa)](#2-achados-da-fase-0-reverificação-ao-vivo-correções-ao-mapa)
- [3. Decisões travadas (aprovadas pelo Rafael 2026-06-01)](#3-decisões-travadas-aprovadas-pelo-rafael-2026-06-01)
- [4. Arquitetura alvo](#4-arquitetura-alvo)
- [5. Contrato por entidade (o que cada função retorna e quem consome)](#5-contrato-por-entidade-o-que-cada-função-retorna-e-quem-consome)
  - [5.1 Núcleo compartilhado (1 implementação, sem divergência)](#51-núcleo-compartilhado-1-implementação-sem-divergência)
  - [5.2 Produto (2 fachadas — Python-rico BLOB+AND vs CLI híbrido via product_search; núcleo `product_search` compartilhado)](#52-produto-2-fachadas-python-rico-bloband-vs-cli-híbrido-via-product_search-núcleo-product_search-compartilhado)
  - [5.3 Pedido (2 fachadas — tupla Python-rica vs CLI achatado; estratégias de busca compartilhadas)](#53-pedido-2-fachadas-tupla-python-rica-vs-cli-achatado-estratégias-de-busca-compartilhadas)
  - [5.4 Cliente (2 fachadas — semânticas distintas)](#54-cliente-2-fachadas-semânticas-distintas)
  - [5.5 Cidade (2 fachadas)](#55-cidade-2-fachadas)
  - [5.6 Grupo (2 fachadas)](#56-grupo-2-fachadas)
  - [5.7 UF (2 fachadas)](#57-uf-2-fachadas)
  - [5.8 Transportadora (núcleo novo — port da split)](#58-transportadora-núcleo-novo-port-da-split)
- [6. Plano de fases (gates onde PARAR para revisão do Rafael)](#6-plano-de-fases-gates-onde-parar-para-revisão-do-rafael)
  - [Fase 1 — Construir `app/resolvedores/` + pytest](#fase-1-construir-appresolvedores-pytest)
  - [Fase 2 — Regressão (golden set + baseline snapshot)  ⟶ **GATE**](#fase-2-regressão-golden-set-baseline-snapshot-gate)
  - [Fase 3 — Shim do monolito](#fase-3-shim-do-monolito)
  - [Fase 4 — Wrappers finos dos 7 CLIs](#fase-4-wrappers-finos-dos-7-clis)
  - [Fase 5 — Pacote-skill completo + remover código morto](#fase-5-pacote-skill-completo-remover-código-morto)
  - [Fase 6 — Verificação final + self-audit  ⟶ **GATE (antes de qualquer commit/merge)**](#fase-6-verificação-final-self-audit-gate-antes-de-qualquer-commitmerge)
- [7. Estratégia de teste](#7-estratégia-de-teste)
- [8. Critérios de aceitação (do §6 do projeto, ajustados) — STATUS FINAL](#8-critérios-de-aceitação-do-6-do-projeto-ajustados-status-final)
  - [Correções extras (decisões Rafael 2026-06-01) + revisão de código](#correções-extras-decisões-rafael-2026-06-01-revisão-de-código)
  - [Escopo do diff](#escopo-do-diff)
- [9. Riscos & mitigações](#9-riscos-mitigações)
- [10. Fora de escopo](#10-fora-de-escopo)
- [Anexo A — Inventário de callers (reverificado ao vivo)](#anexo-a-inventário-de-callers-reverificado-ao-vivo)
- [Contexto](#contexto)

> **Data:** 2026-06-01 · **Autor:** Claude Code (sessão dedicada) · **Status:** SPEC-LOCK (GATE Fase 0 — aguardando revisão do Rafael)
> **Worktree:** `/home/rafaelnascimento/projetos/frete_sistema_resolvedores` · **Branch:** `skills/onda-d-resolvedores` · **Base:** `origin/main` `34924fef2`
> Companion de `.claude/_deprecated/AUDITORIA_SKILLS_ONDA_D_DRIFT_MAP.md`, `.claude/_deprecated/AUDITORIA_SKILLS_ONDA_D_PROJETO_CONSOLIDACAO.md` (arquivados 2026-06-15, Onda D ja mergeada), `.claude/AUDITORIA_SKILLS_PLANO_EXECUCAO.md`.

---

## 1. Objetivo

Consolidar a lógica de "resolver entidade de negócio por nome/termo → identificador" (cliente, produto, pedido, cidade, grupo, UF, transportadora), hoje **duplicada e divergente** em duas implementações, num **único módulo de serviço em `app/resolvedores/`** (SoT testável via `pytest`, sem subprocess). Os scripts de skill viram **wrappers finos**. Meta: contrato unificado num só lugar, dedup de constantes, bug de acento (split) eliminado pelo roteamento, `resolver_transportadora` portado, e **ZERO regressão** nos 9 importadores Python e nos 8 subagentes + agente PROD.

---

## 2. Achados da Fase 0 (reverificação AO VIVO — correções ao mapa)

Reverificado linha-a-linha contra `origin/main` `34924fef2` (fontes idênticas ao working tree; diff vazio).

| # | O mapa dizia | Realidade ao vivo (fonte) | Consequência p/ o design |
|---|---|---|---|
| A | "10 subagentes" consomem a split | **8 subagentes** declaram no frontmatter `skills:` (+ agente PROD = **9 consumidores**): `analista-performance-logistica`, `auditor-financeiro`, `controlador-custo-frete`, `gestor-carvia`, `gestor-devolucoes`, `gestor-estoque-odoo`, `gestor-estoque-producao`, `raio-x-pedido` | superfície de teste CLI menor |
| B | "consolidar no monolito CORRIGE o bug de cidade" | O **monolito JÁ é accent-insensitive correto** (`resolver_entidades.py:963/1002/1028` usa `normalizar_texto` em Python). O bug existe **só na split** (`resolvendo-entidades/scripts/resolver_cidade.py:70` computa `termo_normalizado` mas `:123` usa `cidade` cru no ILIKE) | o núcleo de cidade NÃO precisa de fix; o bug some quando o CLI passa a usar o módulo |
| C | "`ABREVIACOES_PRODUTO` triplicado, deduplicar" | Confirmado em 3 lugares, MAS no **monolito é código MORTO** (`resolver_produto` BLOB+AND não usa; só `detectar_abreviacoes`/`get_abreviacao_produto` órfãos). O **SoT de runtime** é `app/embeddings/product_search.py:46` (usado por `_buscar_texto`) | dedup = módulo importa de `product_search`; remover cópias mortas do monolito na Fase 5 |
| D | "`app/utils/grupo_empresarial.py` é SoT p/ grupos, reusar" | **INCOMPATÍVEL**: formato de prefixo diverge (`'93.209.765/'` 8-díg+barra vs `'93.209.76'` 7-díg sem barra no monolito) e escopo diferente (9 grupos vs 3) → reusar = **regressão silenciosa de matching** | NÃO acoplar; manter `GRUPOS_EMPRESARIAIS` (3 grupos, formato monolito) como constante única do módulo |
| E | (implícito) "1 contrato canônico por entidade" | monolito e split têm **semânticas distintas**, não só shapes: ex. `resolver_cliente` monolito = pedidos da carteira (rico); split = clientes distintos de `entregas_monitoradas` (achatado). Os 9 importadores consomem tupla/list/dict-rico; os 8 subagentes consomem JSON-achatado | **núcleo compartilhado + 2 fachadas finas** (decisão D1) — não forçar 1 shape |

**Models/serviços confirmados p/ o port:** `EntregaMonitorada` (`app/monitoramento/models.py:5`, tabela `entregas_monitoradas`), `Transportadora` (`app/transportadoras/models.py:30`), `EmbeddingService.search_carriers` (`app/embeddings/service.py:1304`) e `.search_products` (`:392`), `buscar_produtos_hibrido` (`app/embeddings/product_search.py:349`).

---

## 3. Decisões travadas (aprovadas pelo Rafael 2026-06-01)

| # | Decisão | Escolha |
|---|---|---|
| D1 | Arquitetura do contrato | **Núcleo compartilhado + 2 fachadas finas.** Onde os shapes divergem genuinamente (cliente/cidade/grupo/uf rico-vs-achatado, carteira-vs-entregas), funções dedicadas por contrato. Sem forçar 1 shape para 2 semânticas. |
| D2 | Nome/local do módulo | **`app/resolvedores/`** (pacote top-level cross-domínio, espelha `app/embeddings/`). |
| D3 | Retrocompatibilidade | **Shim + fachada permanentes.** `resolver_entidades.py` vira shim que re-exporta; os 7 CLIs viram wrappers finos. |
| D4 | Fonte 'entregas' | **Preservar como parâmetro**, `default='entregas'` nas funções CLI-shaped (idêntico à split atual) — obrigatório p/ zero regressão. |
| D5 | Deploy | **Local para revisão, sem push.** Commits locais no worktree; diff entregue no GATE da Fase 6; nada de push/merge sem aprovação. |

---

## 4. Arquitetura alvo

```
app/resolvedores/
├── __init__.py          # API pública: re-exporta tudo (Python-rico + CLI-shaped + constantes + helpers)
├── constantes.py        # GRUPOS_EMPRESARIAIS, UFS_VALIDAS (1 fonte). ABREVIACOES_PRODUTO ← import de product_search
├── normalizacao.py      # normalizar_texto (NFD), _normalizar_token (stemming-s)
├── produto.py           # resolver_produto (BLOB+AND, delega embeddings a product_search), resolver_produto_unico,
│                        #   resolver_produtos_na_carteira_cliente  [PORT monolito]  +  resolver_produto_cli (achatado/product_search)
├── pedido.py            # resolver_pedido (tupla) + helpers  [PORT monolito]  +  resolver_pedido_cli (achatado)
├── cliente.py           # resolver_cliente (rico/carteira)  +  resolver_cliente_cli (achatado/entregas)
├── cidade.py            # resolver_cidade (rico) + resolver_cidades_multiplas  +  resolver_cidade_cli (achatado/entregas)
├── grupo.py             # resolver_grupo (rico) + get_prefixos_grupo + listar_grupos_disponiveis  +  resolver_grupo_cli (achatado/entregas)
├── uf.py                # resolver_uf (rico)  +  resolver_uf_cli (achatado/entregas)
├── transportadora.py    # resolver_transportadora  [PORT da split → ORM Transportadora; 3 estratégias]
└── formatacao.py        # formatar_sugestao_pedido, formatar_sugestao_produto
```

**Princípios:**
1. **ORM SQLAlchemy** (como o monolito vivo). Onde a split usava raw SQL com interpolação de prefixo (`resolver_grupo.py:116`, `resolver_pedido.py:218`) → eliminado pelo ORM (`.like(f'{p}%')` com bind), removendo o vetor de SQL-injection.
2. **Funções puras de I/O**: assumem `app_context` (não chamam `create_app()` internamente). Testáveis por `pytest` num `app_context`. `create_app()` fica nos wrappers CLI.
3. **Produto integra `product_search`** (SoT de runtime): camada BLOB+AND no módulo + fallback semântico delegado. Sem 3ª cópia de `ABREVIACOES_PRODUTO`.
4. **Duas superfícies, núcleo único**: funções "Python-ricas" servem o shim (9 importadores); funções "CLI-shaped" (`*_cli`) servem os wrappers (8 subagentes). Compartilham normalização, constantes, produto, transportadora.

---

## 5. Contrato por entidade (o que cada função retorna e quem consome)

> Legenda fonte: C=carteira, S=separacao, E=entregas_monitoradas.

### 5.1 Núcleo compartilhado (1 implementação, sem divergência)

| Símbolo | Contrato | Origem | Consumidores |
|---|---|---|---|
| `normalizar_texto(t)` | `str` (NFD, lower, strip) | monolito `:61` | módulo + (exportado) |
| `_normalizar_token(t)` | `str` (stemming-s ≥5 chars) | monolito `:1117` | produto |
| `GRUPOS_EMPRESARIAIS` | `dict{str:list[str]}` (3 grupos, prefixos curtos) | monolito `:93` | Python (2 importadores) + grupo/pedido |
| `UFS_VALIDAS` | `list[str]` (27) | monolito `:413` (inline) → extraído p/ constante | uf |
| `ABREVIACOES_PRODUTO` | `dict` | **import de** `product_search.py:46` | produto CLI |
| `get_prefixos_grupo(g)` | `list[str]` | monolito `:196` | Python (2 importadores) |
| `listar_grupos_disponiveis()` | `list[str]` | monolito `:209` | Python (2 importadores) |
| `formatar_sugestao_pedido(info)` | `str\|None` | monolito `:1356` | Python (4 importadores) |
| `formatar_sugestao_produto(info)` | `str\|None` | monolito `:1389` | Python (4 importadores) |

### 5.2 Produto (2 fachadas — Python-rico BLOB+AND vs CLI híbrido via product_search; núcleo `product_search` compartilhado)

| Função | Retorno | Fonte | Consumidores |
|---|---|---|---|
| `resolver_produto(termo, limit=50, modo='hibrida')` (RICO) | **`list[dict]`** `{cod_produto,nome_produto,tipo_embalagem,tipo_materia_prima,categoria_produto,subcategoria,palletizacao,peso_bruto,score,matches}` | `cadastro_palletizacao` + fallback embeddings | Python (`consultando_producao_vs_real` usa só `cod_produto`) |
| `resolver_produto_unico(termo, modo='hibrida')` (RICO) | **`tuple(dict\|None, info)`** info=`{termo_original,encontrado,multiplos,candidatos}` | idem | Python (4 importadores) |
| `resolver_produtos_na_carteira_cliente(termo, cnpjs)` (RICO) | `dict` `{sucesso,candidatos_cadastro,itens_carteira,total_skus,total_quantidade,total_valor,ia_decide}` | `cadastro_palletizacao`+`carteira_principal` | Python (`consultando_situacao_pedidos`) |
| `resolver_produto_cli(termo, limite=50, modo='hibrida')` (ACHATADO) | JSON `{sucesso,termo_original,modo,abreviacoes_detectadas,produtos:[…],total}` | delega `buscar_produtos_hibrido` (product_search) | 8 subagentes |

> O **CLI de produto** mantém o comportamento atual (híbrido via `product_search` + abreviações). Paridade validada por **snapshot baseline** (§7).

### 5.3 Pedido (2 fachadas — tupla Python-rica vs CLI achatado; estratégias de busca compartilhadas)

| Função | Retorno | Fonte | Consumidores |
|---|---|---|---|
| `resolver_pedido(termo, fonte='ambos')` (RICO) | **`tuple(itens_ORM, num_pedido\|None, info)`** info=`{termo_original,estrategia,grupo_identificado,multiplos_encontrados,pedidos_candidatos,fonte,…}` (5 estratégias) | C/S | Python (4 importadores: desempacotam tupla; usam `info['estrategia'/'multiplos_encontrados'/'pedidos_candidatos']` e atributos ORM `itens[0].nome_cidade/.cod_uf/.raz_social_red/.cnpj_cpf/…`) |
| `resolver_pedido_cli(termo, fonte='ambos', limite=50)` (ACHATADO) | JSON `{sucesso,termo_original,estrategia,pedidos:[{num_pedido,cnpj,cliente,cidade,uf,fonte}],multiplos,total,grupo_identificado?,loja_buscada?}` | C/S (default `ambos`) | 8 subagentes |

> O JSON-split de pedido traz `cnpj/cidade/uf` por candidato (a tupla do monolito só expõe `num_pedido/cliente` em `pedidos_candidatos`); por isso `resolver_pedido_cli` monta a lista achatada a partir dos itens ORM — não é serialização direta da tupla.

### 5.4 Cliente (2 fachadas — semânticas distintas)

| Função | Retorno | Fonte | Consumidores |
|---|---|---|---|
| `resolver_cliente(termo, fonte='carteira')` (RICO) | `dict` `{sucesso,termo_original,estrategia,clientes_encontrados:[{cnpj,nome,cidade,uf,num_pedidos,valor_total}],pedidos:[…],resumo:{total_clientes,total_pedidos,total_valor},fonte}` | C/S | Python (`consultando_situacao_pedidos`: usa `clientes_encontrados[].cnpj`, `pedidos`, `resumo.*`) |
| `resolver_cliente_cli(termo, fonte='entregas')` (ACHATADO) | JSON `{sucesso,termo_original,estrategia,clientes:[{cnpj,nome,cidade,uf}],total,fonte}` | C/S/**E** | 8 subagentes |

### 5.5 Cidade (2 fachadas)

| Função | Retorno | Fonte | Consumidores |
|---|---|---|---|
| `resolver_cidade(termo, fonte='separacao', apenas_pendentes=True)` (RICO) | `dict` `{sucesso,termo_original,termo_normalizado,cidades_encontradas:[str],pedidos:[…],total_pedidos}` — accent-insensitive REAL | C/S | (nenhum importador Python direto hoje; re-exportado p/ compat) |
| `resolver_cidades_multiplas(cidades, …)` | `dict` agregado | C/S | re-exportado p/ compat |
| `resolver_cidade_cli(cidade, fonte='entregas')` (ACHATADO) | JSON `{sucesso,cidade_original,termo_normalizado,cidades_encontradas:[{cidade,uf}],clientes:[{cnpj,nome,cidade,uf}],total,fonte}` — **accent-insensitive** (corrige bug split) | C/S/**E** | 8 subagentes |

### 5.6 Grupo (2 fachadas)

| Função | Retorno | Fonte | Consumidores |
|---|---|---|---|
| `resolver_grupo(grupo, uf=None, loja=None, fonte='carteira')` (RICO) | `dict` `{sucesso,grupo,prefixos_cnpj,filtros_aplicados,fonte,pedidos:[…],resumo:{…}}` | C/S | re-exportado p/ compat |
| `resolver_grupo_cli(grupo, uf=None, loja=None, fonte='entregas')` (ACHATADO) | JSON `{sucesso,grupo,prefixos_cnpj,filtros_aplicados,fonte,cnpjs:[…],clientes:[…],total,exibindo}` | C/S/**E** | 8 subagentes |

### 5.7 UF (2 fachadas)

| Função | Retorno | Fonte | Consumidores |
|---|---|---|---|
| `resolver_uf(uf, fonte='carteira')` (RICO) | `dict` `{sucesso,uf,fonte,pedidos:[…],resumo:{…}}` | C/S | re-exportado p/ compat |
| `resolver_uf_cli(uf, fonte='entregas')` (ACHATADO) | JSON `{sucesso,uf,clientes:[…],cidades:[str],total,exibindo,fonte}` | C/S/**E** | 8 subagentes |

### 5.8 Transportadora (núcleo novo — port da split)

| Função | Retorno | Fonte | Consumidores |
|---|---|---|---|
| `resolver_transportadora(termo, limite=10)` | `dict` `{sucesso,termo_original,estrategia('CNPJ'\|'SEMANTICO'\|'ILIKE'),transportadoras:[{id,cnpj,razao_social,cidade,uf,ativo,similaridade?}],total}` | `transportadoras` + `carrier_embeddings` | CLI + 8 subagentes |

> Port da split (`resolvendo-entidades/scripts/resolver_transportadora.py`): 3 estratégias (CNPJ normalizado / `search_carriers` ≥0.65 / ILIKE). Migrar para ORM `Transportadora` onde trivial; a estratégia CNPJ (`REPLACE(...)`) e o lookup de embeddings podem permanecer SQL parametrizado (já seguro). `similaridade` só no modo SEMANTICO.

---

## 6. Plano de fases (gates onde PARAR para revisão do Rafael)

### Fase 1 — Construir `app/resolvedores/` + pytest
- Criar os 11 arquivos do §4. Port fiel do monolito (produto/pedido/normalização/constantes/cliente-rico/cidade-rico/grupo-rico/uf-rico/helpers).
- Portar `resolver_transportadora` da split. Adicionar funções `*_cli` (achatado, fonte entregas).
- `constantes.py` importa `ABREVIACOES_PRODUTO` de `product_search`; extrair `UFS_VALIDAS` p/ constante única.
- `pytest` unitário por função (sem subprocess), num `app_context` contra o banco do `.env`.

### Fase 2 — Regressão (golden set + baseline snapshot)  ⟶ **GATE**
- **Capturar baseline ANTES de tocar os CLIs**: rodar os 7 CLIs atuais da split com termos do golden set, salvar JSON como ouro.
- Golden set por entidade (§7). Comparar saída nova vs baseline (CLI) e vs monolito atual (Python).
- Documentar divergências **intencionais** (cidade split: o módulo corrige o bug → diverge de propósito).
- PARAR p/ revisão.

### Fase 3 — Shim do monolito
- `gerindo-expedicao/scripts/resolver_entidades.py` → shim que `from app.resolvedores import *` (re-exporta todos os símbolos públicos que os 9 importadores esperam: tupla/list/dict-rico/constantes).
- Smoke dos 7 scripts irmãos + 2 de visao-produto (`sys.path` hardcoded preservado): zero `ImportError`, `--help`/execução mínima.

### Fase 4 — Wrappers finos dos 7 CLIs
- Cada `resolvendo-entidades/scripts/resolver_X.py` → `from app.resolvedores import …` + `create_app()` + serializa o **mesmo JSON/flags** (validado vs baseline da Fase 2). Preservar flags `--termo/--fonte/--grupo/--uf/--cidade/--limite/--modo` e defaults (incl. `--fonte entregas`).
- Bug de cidade some (usa o módulo).

### Fase 5 — Pacote-skill completo + remover código morto
- Checklist `feedback_skill_padrao_completo`: `SKILL.md`, `SCRIPTS.md`, `ROUTING_SKILLS.md`, `tool_skill_mapper.py`, cross-refs "NÃO USAR PARA", frontmatter `skills:` dos 8 subagentes, `evals/`.
- Remover do shim/monolito o código morto (`ABREVIACOES_PRODUTO`, `detectar_abreviacoes`, `get_abreviacao_produto`) **após grep exaustivo** provando zero callers; se houver dúvida, manter wrapper fino delegando a `product_search`.
- Corrigir contagem "8 subagentes" onde docs disserem 10.

### Fase 6 — Verificação final + self-audit  ⟶ **GATE (antes de qualquer commit/merge)**
- `pytest` da suite nova + smoke dos 7 CLIs + smoke dos 9 importadores + grep zero refs órfãs.
- Diff completo entregue. Sem commit/merge/push sem aprovação.

---

## 7. Estratégia de teste

**Baseline snapshot (proteção principal contra regressão silenciosa dos CLIs):** antes da Fase 4, executar os 7 CLIs atuais com os termos do golden set e gravar os JSONs. Os wrappers novos devem reproduzir esses JSONs (chaves + valores), salvo divergência intencional documentada.

**Golden set por entidade:**
- **cidade (bug):** `itanhaem→Itanhaém`, `peruibe→Peruíbe`, `sao paulo→São Paulo` (CLI novo deve casar; baseline da split NÃO casava — divergência intencional).
- **produto:** AND multi-termo (`palmito campo belo`), plural/stemming (`azeitonas→azeitona`), abreviação (`AZ VF`, `BD`, `mezzani`), token só-em-subcategoria.
- **pedido:** número exato/parcial, CNPJ edge (`/` + poucos dígitos), grupo+loja (`atacadao 183`), cliente parcial; tupla vs JSON.
- **grupo/uf:** `atacadao`/`SP` — prefixos corretos (formato monolito), sem SQL-injection.
- **transportadora:** por nome (`TAC`, `Transmerc`), por CNPJ, `id=None` quando só em embeddings.
- **cliente:** CNPJ vs nome parcial; rico (carteira: pedidos/resumo) vs achatado (entregas: clientes).

**pytest** unitário direto às funções do módulo (sem subprocess) — é o ganho central de testabilidade.

---

## 8. Critérios de aceitação (do §6 do projeto, ajustados) — STATUS FINAL

- [x] Módulo `app/resolvedores/` único, ORM, testável, 7 entidades (6 do monolito + transportadora). — 12 arquivos, `create_app` OK.
- [x] `GRUPOS_EMPRESARIAIS`/`UFS_VALIDAS` em 1 fonte; `ABREVIACOES_PRODUTO` reusado de `product_search` (sem 3ª cópia). — `test_constantes` prova `is`.
- [x] Bug de acento de cidade eliminado no caminho CLI. — `test_accent_insensitive_corrige_bug` verde + baseline `DIFERE-ESPERADO` (`itanhaem`/`sao paulo` `False→True`).
- [x] Produto integra `product_search` (BLOB+AND no módulo + `_cli` delega `buscar_produtos_hibrido`). — baseline produto paridade perfeita.
- [x] 9 importadores Python funcionam via shim — zero `ImportError`. — 16/16 `--help` OK + teste funcional tupla/list via `from resolver_entidades import`.
- [x] 7 CLIs preservam contrato JSON/flags vs baseline (8 subagentes não regridem). — `baseline_fase4`: todos `[OK]` exceto cidade (`DIFERE-ESPERADO`).
- [x] Suite de regressão (golden set) verde. — **84 pytest** + 2 baselines comparativos.
- [x] Pacote-skill atualizado. — `SCRIPTS.md` (+ seção transportadora + nota rastreabilidade); ROUTING/mapper/cross-refs/agents/evals verificados (nome+contrato preservados → sem mudança). Código morto removido (shim).
- [x] Diff entregue p/ revisão; sem commit/merge/push sem aprovação. — **GATE Fase 6: aguardando Rafael.**

### Correções extras (decisões Rafael 2026-06-01) + revisão de código
**3 code-reviewers** (1 geral + 2 focados: contrato e robustez). Achados triados; 4 eram port-fiel
(não-regressão) e foram preservados ou tratados; os abaixo foram corrigidos via TDD:

1. **`formatar_sugestao_pedido`** (TypeError): branch de múltiplos pedidos fazia `', '.join` sobre dicts.
   Corrigido (junta os `num_pedido`). Decisão Rafael: corrigir.
2. **Guard `None`** (robustez): `resolver_pedido/cliente/uf/grupo/transportadora` faziam `termo.strip()`/
   `uf.upper()` sem proteção → `AttributeError` se `None`. Adicionado `(termo or '')` defensivo (não muda
   comportamento de inputs válidos). `test_robustez.py`.
3. **Fallback do produto CLI**: `resolver_produto_cli` agora cai no BLOB+AND (sem embeddings) se
   `buscar_produtos_hibrido` lançar — restaura a rede de segurança que a split tinha. `test_robustez.py`.
4. **Uniformização separação** (decisão Rafael): `resolver_cliente/grupo/uf` ricos com `fonte='separacao'`
   passam a filtrar `qtd_saldo > 0` (antes só `sincronizado_nf==False`), igualando as `_cli`. **Mudança de
   comportamento** deliberada — afeta `consultando_situacao_pedidos` (exclui itens de separação já zerados).
   `test_separacao_uniformizacao.py` (equivalência vs query de referência).

**Total: 97 pytest verdes.** Kit de verificação versionado: `tests/resolvedores/comparar_antigo_vs_novo.py`
(wrapper novo vs CLI antigo no mesmo banco → zero regressão, exceto cidade-accent intencional).

### Escopo do diff
`-2858 / +132` linhas (monolito vira shim de ~27L; 7 CLIs viram wrappers de ~40L) + novos:
`app/resolvedores/` (12 arq), `tests/resolvedores/` (10 arq, 84 testes), 2 specs/relatórios.
Nenhum código de `app/` (web) modificado — apenas adição de `app/resolvedores/`.

---

## 9. Riscos & mitigações

| Risco | Mitigação |
|---|---|
| Raio assimétrico (monolito quebra por `ImportError`; split quebra por contrato CLI silencioso) | testar AMBOS: smoke dos 9 importadores + baseline JSON dos 7 CLIs |
| Produto CLI: trocar lógica-própria por `buscar_produtos_hibrido` muda ordenação/score | baseline snapshot compara JSON antes/depois; divergência só se justificada |
| `grupo_empresarial.py` incompatível (achado D) | NÃO acoplar; constante própria no módulo |
| `create_app()` regenera ~122 schemas (ruído) + worktree sem `.env` cai em SQLite | `.env` copiado + `.venv` linkado no worktree (feito) |
| Remoção de código morto quebra caller não-detectado | grep exaustivo na Fase 5; manter wrapper fino se houver dúvida |
| `sys.path` hardcoded de visao-produto p/ `../../gerindo-expedicao/scripts` | o shim preserva o path; migração opcional adiada |

---

## 10. Fora de escopo

- Renomes de skills (Onda G).
- Outros resolvers de domínio: `app/odoo/.../resolver_produto`, `app/devolucao/ai_resolver_service`, `app/carvia/.../cliente_service`, `app/financeiro/*resolver*`, `app/hora|motos_assai/modelo_resolver` — domínios distintos, intactos.
- Tocar `app/utils/grupo_empresarial.py` (incompatível, outro domínio).
- Push/deploy sem autorização (D5).

---

## Anexo A — Inventário de callers (reverificado ao vivo)

**9 importadores Python do monolito** (quebram por `ImportError`):
1. `gerindo-expedicao/scripts/analisando_carteira_completa.py:48` → `GRUPOS_EMPRESARIAIS`
2. `…/analisando_disponibilidade_estoque.py:31` → `resolver_pedido`, `get_prefixos_grupo`, `listar_grupos_disponiveis`, `formatar_sugestao_pedido`
3. `…/calculando_leadtime_entrega.py:26` → `resolver_pedido`, `formatar_sugestao_pedido`
4. `…/consultando_produtos_estoque.py:35` → `resolver_produto_unico`, `formatar_sugestao_produto`
5. `…/consultando_programacao_producao.py:29` → `resolver_produto_unico`, `formatar_sugestao_produto` (`resolver_produto` import morto)
6. `…/consultando_situacao_pedidos.py:30` → `resolver_pedido`, `resolver_produto_unico`, `resolver_produtos_na_carteira_cliente`, `resolver_cliente`, `formatar_sugestao_produto`, `get_prefixos_grupo`, `listar_grupos_disponiveis`, `formatar_sugestao_pedido`, `GRUPOS_EMPRESARIAIS`
7. `…/criando_separacao_pedidos.py:29` → `resolver_pedido`, `formatar_sugestao_pedido`
8. `visao-produto/scripts/consultando_producao_vs_real.py:71` (lazy) → `resolver_produto` (usa só `cod_produto`)
9. `visao-produto/scripts/consultando_produto_completo.py:53` (lazy) → `resolver_produto_unico`, `formatar_sugestao_produto`

**8 subagentes consumidores do JSON dos CLIs** (degradam silenciosamente): `analista-performance-logistica`, `auditor-financeiro`, `controlador-custo-frete`, `gestor-carvia`, `gestor-devolucoes`, `gestor-estoque-odoo`, `gestor-estoque-producao`, `raio-x-pedido` (+ agente PROD via `ROUTING_SKILLS.md:206` "utilitários compartilhados"; mapeado em `tool_skill_mapper.py:103`; não está em deny-list de `skills_whitelist.py`).

**Cross-refs "NÃO USAR PARA":** `cotando-frete/SKILL.md:160`, `operando-portal-atacadao/SKILL.md:162/213/281`.

## Contexto

_A completar (PAD-A Onda 4)._
