# Onda D — Caminho C: Consolidação de `resolver_entidades` em módulo `app/` (PROJETO p/ sessão dedicada)

> Criado 2026-06-01. Companion de `AUDITORIA_SKILLS_ONDA_D_DRIFT_MAP.md` (o MAPA do drift, read-only) e
> `AUDITORIA_SKILLS_PLANO_EXECUCAO.md` (plano-mãe das ondas A-G).
> **Este é o PROJETO para uma SESSÃO SEPARADA executar.** Decisão do Rafael (2026-06-01): caminho C
> (consolidar em módulo `app/`), em sessão própria por causa do tamanho/contexto.
> ✅ **EXECUTADO (2026-06-01)** — as 6 fases concluídas (commit local `c694c6c2f`, branch `skills/onda-d-resolvedores`, NÃO pushada).
> Este projeto é o plano HISTÓRICO. O RESULTADO está na spec executora
> `docs/superpowers/specs/2026-06-01-consolidacao-resolvedores-design.md` (no worktree); status no `AUDITORIA_SKILLS_PLANO_EXECUCAO.md` §Onda D.

---

## 0. Por que existe este projeto (1 parágrafo)

Há **duas implementações divergentes** da mesma lógica de "resolver entidade de negócio por nome/termo →
identificador" (cliente, produto, pedido, cidade, grupo, UF, transportadora):
- **MONOLITO** `.claude/skills/gerindo-expedicao/scripts/resolver_entidades.py` (1458 LOC, ORM, **vivo** — refactor mai/2026).
- **SPLIT** `.claude/skills/resolvendo-entidades/scripts/*.py` (7 arquivos, raw SQL, **stale** — congelado fev/2026).

Os contratos de retorno são **incompatíveis em todas as 6 entidades compartilhadas**, as fontes default
diferem (carteira/separacao vs `entregas_monitoradas`), e a split tem um **bug funcional real** (busca de
cidade accent-sensitive — `'itanhaem'` não casa `'Itanhaém'`). `ABREVIACOES_PRODUTO` está **triplicado**.
Detalhe completo e citações linha-a-linha: **`AUDITORIA_SKILLS_ONDA_D_DRIFT_MAP.md`** (LER PRIMEIRO).

---

## 1. Estado-alvo (target architecture)

Criar **um módulo de serviço de resolução de entidades em `app/`** (a camada de domínio), e converter os
scripts de skill em **wrappers finos** que o importam.

```
app/resolvedores/                      [NOME A VALIDAR — ver §2 Fase 0]
├── __init__.py                        # exporta a API pública canônica
├── constantes.py                      # ABREVIACOES_PRODUTO, UFS_VALIDAS (deduplicadas; 1 só fonte)
│                                       # GRUPOS_EMPRESARIAIS → reusar app/utils/grupo_empresarial.py
├── normalizacao.py                    # normalizar_texto (NFD accent-insensitive), _normalizar_token (stemming-s)
├── cliente.py                         # resolver_cliente(termo, fonte=...) -> contrato canônico
├── produto.py                         # resolver_produto(...) — BLOB+AND (vivo) + DELEGA embeddings a
│                                       # app/embeddings/product_search (NÃO reimplementar)
├── pedido.py                          # resolver_pedido(...)
├── cidade.py                          # resolver_cidade(...) — accent-insensitive REAL (corrige o bug da split)
├── grupo.py                           # resolver_grupo(...) — usa app/utils/grupo_empresarial.py
├── uf.py                              # resolver_uf(...)
└── transportadora.py                  # resolver_transportadora(...) — PORTAR da split (única fonte hoje)
```

Princípios do módulo:
1. **ORM SQLAlchemy** (como o monolito vivo), NÃO raw SQL. Elimina o risco de SQL-injection que a split tem
   (interpola prefixos de grupo direto na string — `resolver_grupo.py` L116, `resolver_pedido.py` L218).
2. **Funções puras de I/O**: recebem o contexto/sessão; **não** chamam `create_app()` internamente (isso fica
   nos wrappers CLI). Assim são testáveis via `pytest` dentro de um `app_context` de teste.
3. **`fonte` é parâmetro**, suportando as 3 fontes que hoje estão espalhadas: `carteira`, `separacao`,
   `entregas` (`entregas_monitoradas`). Não perder a via 'entregas' que só a split tinha.
4. **Produto integra `app/embeddings/product_search`** (o SoT de runtime real, usado por
   `knowledge_graph_service.py:327` e `ai_resolver_service.py`): camada textual BLOB+AND no módulo + delega
   o fallback semântico ao `product_search`. Deduplicar `ABREVIACOES_PRODUTO` (hoje em 3 lugares).
5. **Contrato canônico único por entidade** (objeto/dict tipado). Os wrappers adaptam para os 2 formatos
   legados (Python p/ importadores; JSON p/ CLIs).

---

## 2. Fases (incremental, com teste de regressão entre cada — PARAR p/ revisão do Rafael nos gates)

### Fase 0 — Brainstorming + spec-lock (SEM codar)  ⟶ GATE
- **Reverificar TUDO ao vivo** (protocolo inviolável: números de linha do mapa podem ter mudado; a main já
  mudou de linhagem 2× — ver `AUDITORIA_SKILLS_PLANO_EXECUCAO.md` §forense).
- Validar o **nome/local do módulo** (`app/resolvedores/` é a recomendação; alternativas: `app/utils/resolvedores/`,
  `app/carteira/services/resolvedores/`). Verificar ao vivo que não colide e bate com a convenção do projeto
  (`app/embeddings/` é precedente de pacote top-level cross-domínio).
- Inventariar **o contrato real esperado por CADA caller ao vivo** (não confiar no mapa): os 9 importadores
  Python do monolito + o formato JSON que cada um dos 10 subagentes/agente-PROD consome dos CLIs da split.
- Decidir o **contrato canônico** por entidade (shape + chaves) e como cada wrapper adapta.
- Decidir o **destino da fonte 'entregas'** (manter como param? default de quê?).
- Decidir o **destino da skill `resolvendo-entidades`**: vira fachada de wrappers finos (recomendado — preserva
  os 10 subagentes que a declaram) — NÃO descontinuar sem mapear quem perde acesso.
- Entregar a spec travada e PARAR p/ revisão do Rafael.

### Fase 1 — Construir o módulo `app/` (lógica viva + transportadora + dedup) + pytest
- Portar a lógica **do monolito (vivo)** para o módulo, por entidade, em ORM.
- **Portar `resolver_transportadora` da split** (3 estratégias: CNPJ-normalizado, `carrier_embeddings` via
  EmbeddingService, ILIKE) — é a única entidade que só a split resolve.
- **Corrigir o bug de cidade** no caminho canônico (usar `normalizar_texto` no match, accent-insensitive real).
- **Deduplicar** `ABREVIACOES_PRODUTO` (1 fonte), `GRUPOS_EMPRESARIAIS` (usar `app/utils/grupo_empresarial.py`),
  `UFS_VALIDAS`.
- `pytest` unitário por função (agora testável sem subprocess).

### Fase 2 — Teste de regressão (golden set)  ⟶ GATE
- Golden set por entidade fixando o **contrato** + os casos do MAPA §6:
  acento cidade (`itanhaem→Itanhaém`, `peruibe→Peruíbe`), produto AND multi-termo (`palmito campo belo`),
  plural/stemming (`azeitonas→azeitona`), abreviação (`AZ VF`/`BD`/`mezzani`), token só-em-subcategoria,
  CNPJ edge (`'/'` + poucos dígitos), transportadora (TAC/Transmerc por nome/CNPJ, `id=None` semântico).
- Comparar saída nova vs **monolito atual** onde deve haver paridade; documentar onde diverge **de propósito**
  (ex.: cidade — o módulo CORRIGE o bug, então diverge da split de propósito).
- PARAR p/ revisão.

### Fase 3 — Migrar callers do MONOLITO (compat shim)
- Tornar `gerindo-expedicao/scripts/resolver_entidades.py` um **shim de compatibilidade** que re-exporta de
  `app.resolvedores` mantendo os nomes/contratos que os **9 importadores** esperam (7 irmãos de gerindo-expedicao
  + 2 de visao-produto via `sys.path` hardcoded). Menor risco que refatorar 9 callers de uma vez.
- Rodar os scripts irmãos (smoke) p/ confirmar zero `ImportError`.

### Fase 4 — Reescrever os 7 CLIs da SPLIT como wrappers finos
- Cada `resolvendo-entidades/scripts/resolver_X.py` passa a `from app.resolvedores import ...` + `create_app()`
  + serializa para o **JSON que os subagentes/agente-PROD já consomem** (preservar flags `--termo/--grupo/...`
  e o shape JSON — fixar via **teste de contrato CLI**, pois mudança aqui NÃO dá exceção, degrada o roteamento
  do modelo silenciosamente).
- O bug de cidade some automaticamente (agora usa o módulo correto).
- Atualizar `SKILL.md` + `SCRIPTS.md` + `evals/` da skill.

### Fase 5 — Skill = pacote completo + remover código morto
- Checklist `feedback_skill_padrao_completo`: `ROUTING_SKILLS.md`, `tool_skill_mapper.py`, cross-refs
  "NÃO USAR PARA", frontmatter `skills:` dos 10 subagentes, `evals/`.
- Remover do monolito o código morto pós-refactor (`ABREVIACOES_PRODUTO` L105, `detectar_abreviacoes` L156,
  `get_abreviacao_produto` L142) **após** confirmar zero callers ao vivo (a lógica de abreviação migra p/ o módulo).

### Fase 6 — Verificação final + self-audit  ⟶ GATE (revisão antes do merge)
- Rodar `pytest` da nova suite + smoke de cada CLI + grep provando zero refs órfãs.
- Entregar diff completo p/ revisão do Rafael. **Commit/merge só após aprovação.**

---

## 3. Decisões que são do RAFAEL (a sessão DEVE perguntar, não assumir)
1. Nome/local definitivo do módulo (`app/resolvedores/` vs alternativas).
2. Destino da skill `resolvendo-entidades`: fachada de wrappers (recomendado) vs descontinuar.
3. Se manter `resolver_entidades.py` do monolito como shim permanente ou refatorar os 9 importadores.
4. Escopo da fonte 'entregas' no contrato canônico.
5. Se este trabalho será pushado (dispara deploy PROD) ou fica local p/ revisão.

---

## 4. Riscos & gotchas (herdados do mapa + memória)
- **Raio assimétrico**: monolito quebra por `ImportError` (9 callers); split quebra por **contrato CLI/JSON
  silencioso** (10 subagentes + agente PROD). Testar AMBOS os lados.
- **Runtime PROD**: a resolução de produto que roda dentro do `gunicorn-agente` é `app/embeddings/product_search`
  — mudar a assinatura dele atinge `knowledge_graph_service.py` + `ai_resolver_service.py` (devolução). INTEGRAR,
  não quebrar.
- **`sys.path` hardcoded** de visao-produto p/ `../../gerindo-expedicao/scripts` é frágil — o shim da Fase 3
  preserva isso; ao final, considerar migrar visao-produto p/ `from app.resolvedores import ...` direto.
- **Worktree precisa `.env`/`DATABASE_URL`** senão `pytest` cai em SQLite ("no such table") — ver memória
  `gotcha_worktree_testes_env_schemas`. Passar o DATABASE_URL da raiz.
- **SQL injection na split** (interpolação de prefixo) — o módulo ORM elimina; não reintroduzir em wrapper.
- **`create_app()` regenera ~122 schemas** consultando-sql no startup (ruído cosmético em testes).

## 5. Fora de escopo (NÃO fazer)
- Renomes de skills (Onda G — outra onda).
- Mexer em outros resolvers de domínio que NÃO são essa lógica: `app/odoo/.../resolver_produto` (Odoo),
  `app/devolucao/ai_resolver_service` (De-Para NFD), `app/carvia/.../cliente_service`, `app/financeiro/*resolver*`,
  `app/hora|motos_assai/modelo_resolver` — são domínios distintos, deixar intactos.
- Push/deploy sem autorização explícita do Rafael.

## 6. Critérios de aceitação
- [ ] Módulo `app/<nome>/` único, ORM, testável, com as 7 entidades (6 do monolito + transportadora).
- [ ] `ABREVIACOES_PRODUTO`/`GRUPOS_EMPRESARIAIS`/`UFS_VALIDAS` em 1 fonte cada.
- [ ] Bug de acento de cidade corrigido (teste verde).
- [ ] Produto integra `product_search` (sem 3ª cópia de abreviações).
- [ ] 9 importadores do monolito funcionam (shim) — zero `ImportError`.
- [ ] 7 CLIs preservam contrato JSON/flags (teste de contrato verde) — 10 subagentes não regridem.
- [ ] Suite de regressão (golden set §Fase 2) verde.
- [ ] Pacote-skill completo atualizado (ROUTING/mapper/cross-refs/agents/evals/SCRIPTS).
- [ ] Diff entregue p/ revisão; sem commit/merge sem aprovação.

---

## 7. DIREÇÃO DOS DOCS (ordem de leitura para a sessão executora)
1. `AUDITORIA_SKILLS_ONDA_D_DRIFT_MAP.md` — **o mapa** (drift por entidade, raio de impacto, §6 riscos). LER 1º.
2. **Este arquivo** (`AUDITORIA_SKILLS_ONDA_D_PROJETO_CONSOLIDACAO.md`) — o projeto/fases.
3. `AUDITORIA_SKILLS_PLANO_EXECUCAO.md` — contexto das ondas A-G, protocolo inviolável, §forense (a main mudou
   de linhagem; B+C já mergeadas e vivas).
4. **Fontes de verdade (código, reverificar AO VIVO):**
   - Monolito vivo: `.claude/skills/gerindo-expedicao/scripts/resolver_entidades.py`
   - Split stale: `.claude/skills/resolvendo-entidades/scripts/*.py` (7 arquivos)
   - SoT runtime produto: `app/embeddings/product_search.py`
   - SoT grupo: `app/utils/grupo_empresarial.py`
   - Importadores monolito: 7 scripts irmãos de `gerindo-expedicao/scripts/` + `visao-produto/scripts/{consultando_produto_completo,consultando_producao_vs_real}.py`
   - Roteamento da skill: `.claude/references/ROUTING_SKILLS.md`, `app/agente/services/tool_skill_mapper.py`,
     frontmatter `skills:` em `.claude/agents/*.md`, `app/agente/config/skills_whitelist.py`
5. **Schemas de tabela** (campos — fonte de verdade): `.claude/skills/consultando-sql/schemas/tables/{carteira_principal,separacao,entregas_monitoradas,transportadoras}.json`
6. **Regras de modelo**: `.claude/references/modelos/REGRAS_CARTEIRA_SEPARACAO.md`
7. **Memórias/gotchas relevantes**: `gotcha_worktree_testes_env_schemas`, `feedback_skill_padrao_completo`,
   `feedback_worktree_branches_paralelas`, `feedback_pedir_permissao_branch`.

---

## 8. PROMPT DE KICKOFF (copiar/colar na sessão nova)

> Trabalho: **Onda D / Caminho C — consolidar a lógica de `resolver_entidades` num módulo único em `app/`**,
> com os scripts de skill (monolito `gerindo-expedicao/scripts/resolver_entidades.py` + os 7 CLIs de
> `resolvendo-entidades/scripts/`) virando wrappers finos. É uma sessão DEDICADA (trabalho grande, runtime PROD).
>
> ANTES de qualquer coisa, LEIA nesta ordem: (1) `.claude/AUDITORIA_SKILLS_ONDA_D_DRIFT_MAP.md`,
> (2) `.claude/AUDITORIA_SKILLS_ONDA_D_PROJETO_CONSOLIDACAO.md` (este projeto — fases, riscos, critérios de
> aceitação, direção dos docs), (3) `.claude/AUDITORIA_SKILLS_PLANO_EXECUCAO.md`.
>
> Protocolo INVIOLÁVEL: reverifique TODA fonte de verdade AO VIVO (a main mudou de linhagem; números de linha
> do mapa podem estar velhos). Trabalhe em **worktree próprio** a partir do HEAD da main (peça permissão antes
> de qualquer `git checkout`). Garanta `.env`/`DATABASE_URL` no worktree (senão pytest cai em SQLite).
> **NÃO commite/mergeie/pushe sem aprovação** — push dispara deploy PROD.
>
> Comece pela **Fase 0 (brainstorming + spec-lock, SEM codar)**: reverifique o drift, valide o nome/local do
> módulo, inventarie o contrato real de CADA caller ao vivo (9 importadores Python do monolito + o JSON que os
> 10 subagentes/agente-PROD consomem dos CLIs), e me traga a spec travada + as 5 decisões do §3 ANTES de seguir.
> PARE nos GATES (fim das Fases 0, 2 e 6) para minha revisão.
>
> Objetivo de qualidade: SoT único testável via pytest (não subprocess), contrato unificado, bug de acento de
> cidade corrigido, `ABREVIACOES_PRODUTO` deduplicado, `resolver_transportadora` portado, e ZERO regressão nos
> 9 importadores e nos 10 subagentes. Critérios de aceitação completos no §6 do projeto.
