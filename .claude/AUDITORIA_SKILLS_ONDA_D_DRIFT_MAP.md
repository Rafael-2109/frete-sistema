# Onda D — Mapa do Drift `resolver_entidades` (DIAGNÓSTICO read-only)

> Gerado 2026-06-01 por workflow forense read-only (wf_32be000f). NENHUM código foi tocado.
> Objetivo: medir o drift ANTES de qualquer consolidação (Onda D do plano de auditoria).
> Status: ✅ **EXECUTADO na Onda D (2026-06-01)** — consolidação concluída (commit local `c694c6c2f`, NÃO pushada).
> Este mapa é o diagnóstico HISTÓRICO. O RESULTADO + correções factuais a este mapa (8 subagentes não 10;
> bug accent era só da split; `grupo_empresarial.py` incompatível) estão na spec
> `docs/superpowers/specs/2026-06-01-consolidacao-resolvedores-design.md` e no `AUDITORIA_SKILLS_PLANO_EXECUCAO.md` §Onda D.

## 1. As duas implementações

| | MONOLITO | SPLIT |
|---|---|---|
| Local | `.claude/skills/gerindo-expedicao/scripts/resolver_entidades.py` | `.claude/skills/resolvendo-entidades/scripts/*.py` (7 arquivos) |
| LOC | 1458 (1 arquivo) | 1616 (7 arquivos) |
| Tecnologia | ORM SQLAlchemy (assume app_context) | raw SQL `text()` + `create_app()` próprio; CLI `main()` |
| mtime / git | 2026-05-26 (refactor `e0ba4f6e6`); 8 commits | **congelado fev/2026** (1-2 commits docs) → **STALE** |
| Fonte default | carteira (cliente/grupo/uf), separacao (cidade) | **entregas** (`entregas_monitoradas`) |
| Entidades | grupo, uf, cliente, pedido, cidade, produto (+ multiplas/unico/na_carteira) | grupo, uf, cliente, pedido, cidade, produto, **transportadora** |

**A SPLIT é a cópia stale.** Mas tem 1 função que o monolito NÃO tem: `resolver_transportadora`.

## 2. Drift por entidade (contratos INCOMPATÍVEIS em todas as 6 compartilhadas)

| Entidade | Monolito retorna | Split retorna | Drift extra |
|---|---|---|---|
| produto | **list[dict]** (BLOB+AND, stemming-s, ~2ms) | **dict** {sucesso,produtos,total} (ILIKE-por-campo + ABREVIACOES + score, ~310ms) | algoritmos totalmente diferentes; split tenta embeddings 1º; blob=5 campos vs OR=6 campos (split inclui subcategoria) |
| cliente | dict {clientes_encontrados, pedidos, resumo} | dict {clientes, total} | fonte carteira(ORM) vs entregas(SQL); split não traz pedidos/valores |
| pedido | **tupla** (itens_ORM, num, info) | **dict** {pedidos:list, multiplos, total} | tupla vs dict; CNPJ edge-case difere |
| cidade | accent-insensitive real (Python NFD) | **BUG**: computa `termo_normalizado` mas usa termo CRU no ILIKE → accent-SENSITIVE | 'itanhaem'≠'Itanhaém' na split (docstring promete o contrário) |
| grupo | dict {pedidos, resumo} | dict {cnpjs, clientes, total}; **SQL não-parametrizado** (interpola prefixo) | GRUPOS_EMPRESARIAIS idênticos |
| uf | dict {pedidos, resumo} | dict {clientes, cidades, total} | UFS_VALIDAS idênticas |
| transportadora | **não existe** | dict {transportadoras:list} (CNPJ-norm / carrier_embeddings / ILIKE) | única entidade só-split |

Notas factuais: **nenhuma** das duas resolve "código IBGE" (ambas retornam nome+UF). **Nenhuma** tem lógica especial de prefixo VCD/VFB (tratam num_pedido como string opaca).

## 3. Raio de impacto (ASSIMÉTRICO)

- **MONOLITO** — ALTO por IMPORT: **9 importadores Python**. 7 scripts irmãos de `gerindo-expedicao` + 2 de `visao-produto` (via `sys.path` hardcoded `../../gerindo-expedicao/scripts` — acoplamento frágil, já flagado na auditoria). Mudar assinatura = ImportError → 2 skills quebram.
- **SPLIT** — ZERO importadores Python. Invocada só como **CLI via Bash subprocess** pelo agente principal Nacom (exposta em PROD — não está em deny-list de `skills_whitelist`) e por **10 subagentes** que a declaram no frontmatter `skills:`. Mudar flag/JSON **não gera exceção** — degrada o roteamento do modelo silenciosamente.
- **RUNTIME real PROD**: NENHUMA das duas roda por `import` dentro do `gunicorn-agente`. A lógica de produto que de fato roda no processo é `app/embeddings/product_search.buscar_produtos_hibrido` (usado por `knowledge_graph_service.py:327` e `ai_resolver_service.py` de devolução). **Esse é o SoT de runtime** — e ambas as skills + o monolito o chamam como fallback semântico.

## 4. Duplicações e código morto detectados

- `ABREVIACOES_PRODUTO` está **triplicado** manualmente: monolito + split + `app/embeddings/product_search.py:43` (comentário "Replicado de resolver_entidades.py"). Editar um dessincroniza match.
- `GRUPOS_EMPRESARIAIS` hardcoded inline em monolito E split; existe `app/utils/grupo_empresarial.py` (SoT natural só p/ grupos) que **nenhum dos dois importa**.
- Código morto no monolito pós-refactor BLOB+AND: `ABREVIACOES_PRODUTO` (L105), `detectar_abreviacoes` (L156), `get_abreviacao_produto` (L142) — órfãos (mas a lógica de abreviação ainda VIVE na split).

## 5. O que o plano original assumia vs a realidade

O plano dizia "consolidar → SoT único em `app/` → migrar com teste de regressão". O mapa mostra que **não há SoT único candidato** em `app/`: só `product_search` (produto) e `grupo_empresarial` (grupo, não usado). As outras 5 entidades não têm casa em `app/`. Consolidar de verdade = extrair 6 entidades para `app/` — esforço grande, runtime PROD, alto risco. Há **decisões estratégicas que são do Rafael** (ver §6).

## 6. Riscos de regressão a cobrir (se consolidar)

1. **Contrato de retorno** (maior): cada caller consome shape específico (tupla/list vs dict; chaves). Fixar por função.
2. **Fonte default**: carteira/separacao vs entregas = universos de dados diferentes. Se descartar 'entregas', perde-se a única via que consulta `entregas_monitoradas`.
3. **Normalização cidade**: consolidar no monolito CORRIGE o bug de acento; na split MANTÉM. Testar 'itanhaem'→'Itanhaém'.
4. **resolver_produto**: AND multi-termo, plural (stemming só-monolito), abreviação (só-split), subcategoria (só-split), determinismo, fallback embeddings.
5. **transportadora**: portar p/ o monolito (3 estratégias) ou a entidade fica não-resolvível.
6. **CNPJ edge** ('/' + poucos dígitos): split-pedido dispara, monolito não.
7. **Segurança**: split interpola prefixo de grupo em SQL cru — parametrizar se mantiver raw SQL.

## 7. Opções de caminho (DECISÃO DO RAFAEL)

- **A. Não consolidar agora — só corrigir o bug + remover stale.** Baixo risco. Corrigir o accent-bug de `resolver_cidade` na split (ou deixar o roteamento usar só o monolito p/ cidade), e decidir o destino da split.
- **B. Aposentar a split, manter o monolito como fonte.** A split tem 0 importadores Python; o monolito é o vivo. Exige: portar `resolver_transportadora` p/ o monolito, decidir sobre a fonte 'entregas', reescrever os SKILL.md/SCRIPTS.md de `resolvendo-entidades` p/ apontar ao monolito (ou descontinuar a skill). Médio-alto risco (10 subagentes + agente PROD usam a CLI da split).
- **C. Consolidar de verdade em `app/`** (plano original): extrair 6 entidades p/ módulo em `app/`, ambas as skills passam a chamar. Maior esforço/risco; melhor fim arquitetural.
- **D. Parar aqui** — mapa entregue, sem mexer; retomar quando você decidir o rumo.

> Recomendação técnica (não-vinculante): o caminho de menor risco/maior valor imediato é **A** (corrigir o bug de acento, que é uma regressão funcional real e silenciosa) e adiar a consolidação estrutural — porque B e C mexem no roteamento que 10 subagentes + o agente PROD usam ao vivo, e merecem onda dedicada com teste de regressão. A escolha é sua.
