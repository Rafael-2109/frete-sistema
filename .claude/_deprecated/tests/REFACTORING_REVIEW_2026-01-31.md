# Review da Refatoracao .claude/ - 31/01/2026

## 1. Resumo Executivo

Refatoracao completa da infraestrutura `.claude/` do sistema de fretes Nacom Goya, abrangendo 6 categorias de mudancas: delecao de comandos GSD, reorganizacao hierarquica de references, overhaul do CLAUDE.md, enhancement de skills com desambiguacao, limpeza de settings/seguranca e adocao de hook de validacao estrutural.

**Resultado dos testes**: 10/10 testes PASS via API Claude (score total 80%), confirmando que o routing de skills e a resolucao de references funcionam corretamente apos a refatoracao.

**Issues criticos encontrados e corrigidos**: 5 (paths quebrados em agents, hook nao configurado, referencia inexistente).

---

## 2. Inventario de Mudancas

### 2.1 Categoria 1: Delecao de Comandos GSD (STAGED)

| Item | Detalhe |
|------|---------|
| Arquivos deletados | 27 (`.claude/commands/gsd/gsd/*.md`) |
| Linhas removidas | ~7.061 |
| Status | STAGED (pronto para commit) |

**Impacto**: Positivo. Remove dependencia do plugin GSD (terceiro), reduz ruido no diretorio de comandos.
**Risco**: Nenhum. Comandos GSD sao providos pelo plugin e nao dependem desses arquivos locais duplicados.

### 2.2 Categoria 2: Reorganizacao de References (UNSTAGED)

| Item | Detalhe |
|------|---------|
| Arquivos movidos | 14 (flat → 5 subdiretorios) |
| Novo arquivo | `modelos/CAMPOS_CARTEIRA_SEPARACAO.md` (+412 linhas) |
| Conteudo preservado | 7.590 linhas (100%) |
| INDEX.md | Atualizado com novos paths |

**Estrutura nova:**
```
.claude/references/
├── design/          (1 arquivo: MAPEAMENTO_CORES.md)
├── modelos/         (3 arquivos: CAMPOS_CARTEIRA_SEPARACAO, MODELOS_CAMPOS, QUERIES_MAPEAMENTO)
├── negocio/         (3 arquivos: RECEBIMENTO_MATERIAIS, REGRAS_NEGOCIO, historia_nacom)
├── odoo/            (6 arquivos: CONVERSAO_UOM, GOTCHAS, IDS_FIXOS, MODELOS_CAMPOS, PADROES_AVANCADOS, PIPELINE_RECEBIMENTO)
├── roadmaps/        (2 arquivos: FEATURES_AGENTE, IMPLEMENTACAO_ODOO)
└── INDEX.md
```

**Impacto**: Altamente positivo. Navegacao hierarquica por dominio, escalavel, sem perda de conteudo.
**Risco**: Paths quebrados em agents (CORRIGIDO — ver secao 3).

### 2.3 Categoria 3: CLAUDE.md Overhaul (UNSTAGED)

| Item | Detalhe |
|------|---------|
| Antes | ~733 linhas |
| Depois | ~260 linhas |
| Reducao | ~473 linhas (-64%) |

**O que foi removido (movido para references externos):**
- Documentacao completa de campos CarteiraPrincipal (73 campos) → `modelos/CAMPOS_CARTEIRA_SEPARACAO.md`
- Documentacao completa de campos Separacao (48 campos) → `modelos/CAMPOS_CARTEIRA_SEPARACAO.md`
- Secao de Pallets (2 grupos, propriedades calculadas) → `modelos/CAMPOS_CARTEIRA_SEPARACAO.md`
- Regras de Ouro e Exemplos de Uso → `modelos/CAMPOS_CARTEIRA_SEPARACAO.md`
- Tabela extensa de references com coluna "Quando Usar" → INDEX.md
- Cookbooks section → removida (conteudo integrado em skills)
- Detalhes de subagentes (138 linhas!) → `.claude/agents/*.md`
- Skills table detalhada (23 linhas) → condensada

**O que foi adicionado:**
- "INDICE DE REFERENCIAS" simplificado (tabela 2 colunas)
- "Regras Rapidas" para campos criticos (4 regras inline)
- "SKILLS POR DOMINIO" (Agente Web vs Claude Code)
- Arvore de Decisao para routing Odoo

**Impacto**: Muito positivo. CLAUDE.md agora e um documento de NAVEGACAO, nao um repositorio de dados.
**Risco**: Medio — se Claude nao consultar references externos, pode perder contexto. Mitigado pelas "Regras Rapidas" inline.

### 2.4 Categoria 4: Skills Enhancement (UNSTAGED)

| Skill | Linhas adicionadas | Cross-references |
|-------|--------------------|------------------|
| conciliando-odoo-po | +5 | validacao-nf-po, recebimento-fisico-odoo, executando-odoo-financeiro, rastreando-odoo |
| descobrindo-odoo-estrutura | +11 | TODAS as 7 skills (marcado como ULTIMO RECURSO) |
| executando-odoo-financeiro | +5 | rastreando-odoo, descobrindo-odoo-estrutura, validacao-nf-po, razao-geral-odoo |
| integracao-odoo | +4 | rastreando-odoo, descobrindo-odoo-estrutura |
| rastreando-odoo | +10 | validacao-nf-po, conciliando-odoo-po, recebimento-fisico-odoo, executando-odoo-financeiro, descobrindo-odoo-estrutura, integracao-odoo |
| razao-geral-odoo | +4 | executando-odoo-financeiro, rastreando-odoo, descobrindo-odoo-estrutura |
| recebimento-fisico-odoo | +5 | validacao-nf-po, conciliando-odoo-po, executando-odoo-financeiro, rastreando-odoo |
| validacao-nf-po | +5 | conciliando-odoo-po, recebimento-fisico-odoo, executando-odoo-financeiro, rastreando-odoo |

**Impacto**: Muito positivo. Cria malha de desambiguacao — cada skill diz explicitamente o que NAO fazer.
**Risco**: Nenhum.

### 2.5 Categoria 5: Settings & Security (UNSTAGED)

| Item | Mudanca |
|------|---------|
| Plugins desabilitados | agent-sdk-dev, frontend-design, code-simplifier, ralph-wiggum |
| Plugins mantidos | pyright-lsp |
| .gitignore | +4 patterns (`__pycache__`, `flask_session`, `uploads`, `.pyc`) |
| .encryption_key | DELETADA (seguranca) |

**Impacto**: Positivo. Simplifica tooling ativo, melhora seguranca, previne commits acidentais.
**Risco**: Nenhum (plugins desabilitados nao estavam em uso ativo).

### 2.6 Categoria 6: Novo Hook (UNSTAGED)

| Item | Detalhe |
|------|---------|
| Arquivo | `.claude/hooks/validar-estrutura.py` |
| Checks | skills com SKILL.md, sem __pycache__, INDEX.md existe, subpastas modelos/odoo/negocio |
| Comportamento | Non-blocking (retorna 0 sempre) |

**Impacto**: Positivo. Prevencao de regressao estrutural automatica.
**Risco**: Hook NAO estava configurado em settings.json (CORRIGIDO — ver secao 3).

---

## 3. Issues Criticos Encontrados e Corrigidos

| # | Issue | Severidade | Arquivo(s) | Correcao |
|---|-------|-----------|------------|----------|
| 1 | 9+ paths quebrados para references antigos | **ALTA** | `.claude/agents/especialista-odoo.md` | Todos os paths atualizados (ex: `ODOO_IDS_FIXOS.md` → `odoo/IDS_FIXOS.md`) |
| 2 | 6+ paths quebrados + decision tree inline | **ALTA** | `.claude/agents/desenvolvedor-integracao-odoo.md` | Tabela + decision tree + checklist atualizados |
| 3 | Hook nao configurado em settings.json | **MEDIA** | `.claude/settings.json` | Adicionado `python3 .claude/hooks/validar-estrutura.py` ao SessionStart |
| 4 | Referencia a arquivo inexistente | **BAIXA** | `CLAUDE.md` linha 104 | Removida referencia a `ESPECIFICACAO_SINCRONIZACAO_ODOO.md` |
| 5 | Path antigo em skill | **BAIXA** | `.claude/skills/descobrindo-odoo-estrutura/SKILL.md` | `references/MODELOS_CAMPOS.md` → `.claude/references/odoo/MODELOS_CAMPOS.md` |

---

## 4. Metodologia de Testes

### 4.1 Abordagem

- **API real**: Anthropic API com `claude-sonnet-4-6`
- **10 test cases** cobrindo 4 categorias
- **System prompt**: CLAUDE.md completo + frontmatter de 8 skills (name + description + QUANDO NAO USAR)
- **Scoring**: 0-5 pontos por teste com 4 criterios
- **Threshold**: 70% para PASS

### 4.2 Criterios de Pontuacao

| Criterio | Pontos | Descricao |
|----------|--------|-----------|
| Skill correta mencionada | 2 | Nome exato da skill esperada aparece na resposta |
| Anti-skills ausentes | 1 | Skills incorretas NAO sugeridas como principal |
| Keywords detectadas | 1 | >=2 keywords especificas presentes |
| Path no formato novo | 1 | Formato `odoo/IDS_FIXOS.md` vs `ODOO_IDS_FIXOS.md` |
| **Total** | **5** | |

### 4.3 Categorias

| Categoria | Testes | O que Valida |
|-----------|--------|-------------|
| Routing (A1-A4) | 4 | Skill correta escolhida para tarefa especifica |
| Reference (B1-B2) | 2 | Arquivo de referencia correto citado com path novo |
| Disambiguation (C1-C2) | 2 | "QUANDO NAO USAR" funciona (skill correta, nao a parecida) |
| Decision Tree (D1-D2) | 2 | Arvore de decisao do CLAUDE.md cobre todos os cenarios |

---

## 5. Resultados dos Testes

### 5.1 Resultado por Teste

| ID | Categoria | Prompt | Score | % | Status |
|----|-----------|--------|-------|---|--------|
| A1 | routing | Criar pagamento no Odoo para NF 54321 | 3.5/5 | 70% | PASS |
| A2 | routing | Rastrear fluxo NF 12345 ate pagamento | 4.0/5 | 80% | PASS |
| A3 | routing | Picking nao valida, lotes nao preenchidos | 4.0/5 | 80% | PASS |
| A4 | routing | Exportar razao geral janeiro 2026 | 4.0/5 | 80% | PASS |
| B1 | reference | Campos CarteiraPrincipal, nome do saldo | 5.0/5 | 100% | PASS |
| B2 | reference | picking_type_id para empresa SC | 4.0/5 | 80% | PASS |
| C1 | disambig | Estrutura modelo purchase.order | 4.0/5 | 80% | PASS |
| C2 | disambig | Consolidar POs, criar PO Conciliador | 4.0/5 | 80% | PASS |
| D1 | decision | Criar integracao para devolucoes | 3.5/5 | 70% | PASS |
| D2 | decision | Validacao NF x PO divergencia De-Para | 4.0/5 | 80% | PASS |

### 5.2 Resultado por Categoria

| Categoria | Score | Max | % | Status |
|-----------|-------|-----|---|--------|
| routing | 15.5 | 20.0 | 78% | PASS |
| reference | 9.0 | 10.0 | 90% | PASS |
| disambiguation | 8.0 | 10.0 | 80% | PASS |
| decision_tree | 7.5 | 10.0 | 75% | PASS |

### 5.3 Veredicto Final

```
╔══════════════════════════════════════════╗
║  SCORE TOTAL: 40.0/50.0 (80%)           ║
║  VEREDICTO: PASS ✓                       ║
║  10/10 testes aprovados                  ║
╚══════════════════════════════════════════╝
```

### 5.4 Observacoes nos Testes

**Anti-skills mencionadas**: Em 8/10 testes, o modelo mencionou skills alternativas no corpo da explicacao (nao como escolha principal). Isso e esperado quando o prompt pede "por que esta e NAO outra?" — o modelo cita as alternativas para justificar a escolha. O scoring penaliza levemente mas o routing principal esta correto em todos os casos.

**B2 parcial**: O teste de picking_type_id nao citou o path exato `odoo/IDS_FIXOS.md` mas identificou corretamente o campo. Score 80% (vs 100% de B1).

---

## 6. Analise de Custo-Beneficio

### 6.1 Por Categoria de Mudanca

| Categoria | Esforco | Beneficio | Veredicto |
|-----------|---------|-----------|-----------|
| Delecao GSD (27 arquivos) | Baixo (git rm) | Remove 7K linhas de dependencia morta | **VALE A PENA** |
| Reorganizacao References | Medio (mover + paths) | Navegacao hierarquica, escalavel | **VALE A PENA** |
| CLAUDE.md Overhaul (-64%) | Alto (reescrever) | ~1.900 tokens/sessao economizados | **VALE MUITO** |
| Skills QUANDO NAO USAR | Medio (8 edits) | Disambiguation comprovada (80% score) | **VALE MUITO** |
| Settings cleanup | Baixo | Seguranca + limpeza | **VALE A PENA** |
| Hook validacao | Baixo | Prevencao automatica de regressao | **VALE A PENA** |

### 6.2 Token Economy

| Metrica | Antes | Depois | Economia |
|---------|-------|--------|----------|
| CLAUDE.md linhas | ~733 | ~260 | -473 (-64%) |
| CLAUDE.md tokens (est.) | ~2.900 | ~1.000 | ~1.900 tokens/sessao |
| Custo Opus por sessao (est.) | ~$0.043 | ~$0.015 | **~$0.028/sessao** |
| Custo mensal (est. 50 sessoes) | ~$2.15 | ~$0.75 | **~$1.40/mes** |

**Nota**: A economia real depende de quantas vezes CLAUDE.md e carregado (prompt caching pode reduzir o impacto). A economia principal e em **foco cognitivo** — menos ruido no prompt = respostas mais precisas.

### 6.3 Custo dos Testes

| Item | Valor |
|------|-------|
| Tokens input | 63.667 |
| Tokens output | 3.772 |
| Custo total | **$0.25 USD** |
| Tempo execucao | 102.9s |

---

## 7. Melhorias Propostas

### 7.1 Prioridade Alta

- [ ] Hook `validar-estrutura.py`: adicionar check de `design/` e `roadmaps/` ao `check_reference_structure()` (hoje so valida `modelos`, `odoo`, `negocio`)

### 7.2 Prioridade Media

- [ ] Criar script de validacao cruzada: agent files → reference paths (automatizar deteccao de paths quebrados)
- [ ] Considerar remover hooks GSD orfaos (`gsd-check-update.js`, `gsd-statusline.js`) se GSD plugin nao sera mais usado
- [ ] Adicionar secao "QUANDO NAO USAR" no frontmatter `description` das skills que so tem no body (integracao-odoo)

### 7.3 Prioridade Baixa

- [ ] Consolidar 4 `.claude/tests/*.md` antigos (bateria_testes, comparativo_final, resultados_antes, resultados_depois) em um unico arquivo historico
- [ ] Considerar adicionar test B2 com prompt mais explicito para melhorar deteccao de path

---

## 8. Matriz de Risco

| Risco | Prob. Antes | Prob. Depois | Impacto | Mitigacao |
|-------|-------------|-------------|---------|-----------|
| Agent nao encontra reference (path errado) | Alta | **Baixa** | Alto | Fase 1: 15+ paths corrigidos |
| Claude nao consulta references (conteudo fora do CLAUDE.md) | Media | **Baixa** | Medio | "Regras Rapidas" inline + "INDICE DE REFERENCIAS" |
| Hook nao roda (nao configurado) | Alta | **Baixa** | Medio | Adicionado a SessionStart em settings.json |
| Routing errado (skill errada) | Media | **Baixa** | Alto | QUANDO NAO USAR (testado: 80% score) |
| GSD hook files orfaos no repo | Baixa | Baixa | Nenhum | Melhoria futura |
| Regressao estrutural futura | Media | **Baixa** | Medio | Hook automatico no SessionStart |

---

## 9. Arquivos Modificados/Criados nesta Review

### Correcoes (Fase 1)
| Arquivo | Tipo | Descricao |
|---------|------|-----------|
| `.claude/agents/especialista-odoo.md` | Modificado | 9+ paths corrigidos (tabela + inline) |
| `.claude/agents/desenvolvedor-integracao-odoo.md` | Modificado | 6+ paths + decision tree + checklist |
| `CLAUDE.md` | Modificado | Removida referencia inexistente (linha 104) |
| `.claude/settings.json` | Modificado | Hook validar-estrutura.py adicionado |
| `.claude/skills/descobrindo-odoo-estrutura/SKILL.md` | Modificado | 1 path corrigido (linha 113) |

### Testes (Fases 2-3)
| Arquivo | Tipo | Descricao |
|---------|------|-----------|
| `.claude/tests/test_routing_refactoring.py` | Novo | Script de teste (10 cases, 4 categorias) |
| `.claude/tests/routing_test_results.json` | Novo (gerado) | Resultados raw dos testes |

### Documentacao (Fase 4)
| Arquivo | Tipo | Descricao |
|---------|------|-----------|
| `.claude/tests/REFACTORING_REVIEW_2026-01-31.md` | Novo | Este documento |

---

## 10. Rodada 2: Melhorias no Routing e Decision Tree

### 10.1 Problema Identificado

Apos a Rodada 1 (80% score), analise detalhada revelou 3 padroes de falha:

| Problema | Impacto | Testes Afetados |
|----------|---------|-----------------|
| **Anti-skills por nome**: cada SKILL.md listava skills concorrentes pelo nome na secao "QUANDO NAO USAR", treinando o modelo a MENCIONA-LAS | Score -1 em 8/10 testes | A1-A4, C1-C2, D1-D2 |
| **IDs fixos sem rota**: perguntas sobre config estatica (picking_type_id, journal_id) nao tinham no na arvore, caindo em `descobrindo-odoo-estrutura` | B2 = 80% (deveria ser 100%) | B2 |
| **Contextos misturados**: arvore so cobria Odoo; frontend, exportacao e queries locais nao tinham rota | Nao testado diretamente | - |

### 10.2 Mudancas Implementadas

#### Fase 1: Reestruturar Decision Tree no CLAUDE.md

Substituida arvore de 5 niveis (apenas Odoo) por estrutura de 3 passos:

```
Passo 1: Identificar CONTEXTO (Local / Odoo / Frontend / Export)
Passo 2: Dado ESTATICO ja documentado? (IDS_FIXOS, CONVERSAO_UOM, etc.)
Passo 3: Arvore de decisao Odoo (5 niveis + desambiguacao)
```

**Adicoes**:
- Tabela "Desambiguacao" com regras de desempate entre skills parecidas
- Passo 2 previne uso de skill para dados que ja estao em references
- 4 contextos cobertos (vs 1 antes)

#### Fase 2: Reformular "QUANDO NAO USAR" nas 8 Skills

**Padrao removido** (anti-skill):
```markdown
- Para rastrear NF/PO/SO → use `rastreando-odoo`
- Para explorar modelo desconhecido → use `descobrindo-odoo-estrutura`
```

**Padrao adotado** (cenario-only):
```markdown
- Apenas CONSULTAR/rastrear documentos sem modificar (esta skill EXECUTA operacoes)
- Explorar modelo Odoo desconhecido (esta skill trabalha com modelos financeiros conhecidos)
```

**Skills reformuladas**: 8/8

| Skill | Frontmatter | Body | Total edits |
|-------|:-----------:|:----:|:-----------:|
| conciliando-odoo-po | ✅ | ✅ | 2 |
| descobrindo-odoo-estrutura | N/A | ✅ | 1 |
| executando-odoo-financeiro | ✅ | ✅ | 2 |
| integracao-odoo | N/A | ✅ + nota | 2 |
| rastreando-odoo | ✅ | ✅ | 2 |
| razao-geral-odoo | N/A | ✅ | 1 |
| recebimento-fisico-odoo | ✅ | ✅ | 2 |
| validacao-nf-po | ✅ | ✅ | 2 |

### 10.3 Resultados Rodada 2

#### Comparativo

| Metrica | Rodada 1 | Rodada 2 | Delta |
|---------|:--------:|:--------:|:-----:|
| **Score Total** | 40.0/50 (80%) | 41.5/50 (83%) | **+3%** |
| Routing | 15.5/20 (78%) | 15.5/20 (78%) | = |
| Reference | 9.0/10 (90%) | **10.0/10 (100%)** | **+10%** ✅ |
| Disambiguation | 8.0/10 (80%) | 8.0/10 (80%) | = |
| Decision Tree | 7.5/10 (75%) | **8.0/10 (80%)** | **+5%** ✅ |

#### Detalhamento por Teste

| ID | Cat | Rodada 1 | Rodada 2 | Delta | Nota |
|----|-----|:--------:|:--------:|:-----:|------|
| A1 | routing | 3.5 | **4.0** | +0.5 | Melhora na pontuacao base |
| A2 | routing | 4.0 | 4.0 | = | |
| A3 | routing | 4.0 | 4.0 | = | |
| A4 | routing | 4.0 | 3.5 | -0.5 | Path nao mencionado |
| B1 | reference | 5.0 | 5.0 | = | Perfeito |
| B2 | reference | 4.0 | **5.0** | **+1.0** | **Maior ganho**: Passo 2 funcionou! |
| C1 | disambig | 4.0 | 4.0 | = | |
| C2 | disambig | 4.0 | 4.0 | = | |
| D1 | decision | 3.5 | **4.0** | +0.5 | |
| D2 | decision | 4.0 | 4.0 | = | |

#### Anti-skills

| Rodada | Testes com anti-skills | Reducao |
|--------|:----------------------:|:-------:|
| Rodada 1 | 8/10 | - |
| Rodada 2 | 8/10 | = |

**Analise**: A reformulacao "QUANDO NAO USAR" removeu nomes de skills do conteudo das skills, porem o modelo ainda menciona skills concorrentes na resposta. Isso ocorre porque:
1. Os **nomes** das skills aparecem no system prompt (frontmatter `name:`)
2. O modelo naturalmente cita alternativas ao justificar sua escolha
3. O comportamento e INFORMATIVO (nao roteamento errado)

A metrica "anti-skills" penaliza mencoes informativas, o que infla o problema. O routing PRINCIPAL esta correto em 10/10 testes em ambas as rodadas.

### 10.4 Custo Rodada 2

| Item | Valor |
|------|-------|
| Tokens input | 71.177 |
| Tokens output | 3.578 |
| Custo teste | **$0.27 USD** |
| Tempo execucao | 106.3s |
| **Custo total (2 rodadas)** | **$0.52 USD** |

### 10.5 Conclusao

A Rodada 2 alcancou melhorias pontuais significativas:
- **B2 (IDs fixos)**: 80% → 100% — o "Passo 2" da arvore de decisao previne uso desnecessario de skills para dados estaticos
- **Decision Tree**: 75% → 80% — cobertura de contextos multiplos melhora routing
- **Score geral**: 80% → 83% — melhoria incremental consistente

O teto pratico de score com o framework atual e ~85-90%, pois a metrica "anti-skills" penaliza comportamento informativo natural do modelo.

---

**Gerado**: 31/01/2026 17:30 (Rodada 1) / 31/01/2026 17:55 (Rodada 2)
**Modelo teste**: claude-sonnet-4-6
**Modelo review**: claude-opus-4-6
