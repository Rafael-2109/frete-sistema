---
name: resolvendo-problemas
description: >-
  Workflow estruturado para resolver problemas GRANDES (G/XG) em desenvolvimento.
  7 fases (Escopo, Pesquisa, Analise, Plano, Validacao, Implementacao,
  Verificacao) com subagentes Opus e filesystem como memoria compartilhada.
  DEV-ONLY: nao e para o agente web. APENAS para problemas com 2+ criterios
  de complexidade (>= 2K LOC, >= 5 arquivos, >= 2 modulos, >= 3 niveis de
  call chain, ou >= 3 callers afetados).

  USAR QUANDO:
  - "resolver problema complexo em...", "investigar bug em...", "por que X esta..."
  - "analisar modulo completo", "mapear dependencias de...", "root cause analysis"
  - "implementar com seguranca em sistema grande", "preciso entender todo o modulo antes"
  - Qualquer tarefa classificada como G/XG apos avaliacao inicial
  - "/resolver", "/investigar"

  NAO USAR QUANDO:
  - Bug pontual em 1-4 arquivos, < 2K LOC -> resolver direto (overhead nao se paga)
  - Feature com spec clara -> usar **ralph-wiggum**
  - Consulta de dados -> usar **consultando-sql**
  - Operacao Odoo especifica -> usar skill Odoo apropriada
  - Saude do banco -> usar **diagnosticando-banco**
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, Agent
---

# Resolvendo Problemas Complexos

Protocolo de orquestracao em 7 fases para resolver problemas que excedem a capacidade de analise direta. Usa subagentes como ferramentas de pesquisa e o filesystem (`/tmp/subagent-findings/`) como memoria compartilhada entre fases.

> **ESCOPO**: Skill exclusiva para **desenvolvimento** (Claude Code). NAO e para o agente web nem para usuarios finais.

---

## Regras Comportamentais

### R1: Qualidade > Velocidade (INVIOLAVEL)
- **NUNCA** pular fases para "ir mais rapido"
- **NUNCA** assumir que um finding esta correto sem spot-check
- **NUNCA** implementar sem plano validado (Fase 4)
- Prefira gastar 2x mais contexto pesquisando do que corrigir 1 erro de implementacao
- Se estiver em duvida entre "ja sei o suficiente" e "preciso pesquisar mais": **pesquise mais**

### R2: Apenas Opus para Subagentes
- **TODOS** os subagentes DEVEM usar `model: "opus"` no Agent tool
- Haiku/Sonnet NAO tem capacidade de pesquisa profunda e citacao de fontes necessaria
- Se por qualquer motivo Opus nao estiver disponivel: **parar e informar o usuario**

### R3: Apenas Problemas Grandes (G/XG)
Esta skill so se justifica para problemas que atendam **pelo menos 2** destes criterios:

| Criterio | Limiar |
|----------|--------|
| **LOC afetado** | >= 2K LOC (contando todos os arquivos envolvidos) |
| **Arquivos envolvidos** | >= 5 arquivos |
| **Modulos cruzados** | >= 2 modulos distintos (`app/{modulo}/`) |
| **Dependencias opacas** | Caller/callee chain com >= 3 niveis |
| **Risco de regressao** | Mudanca afeta funcao usada por >= 3 callers |

Se o problema NAO atende 2+ criterios: **sair da skill e resolver direto**. Nao desperdice o overhead de 7 fases em problemas simples.

---

## Quando Usar vs Nao Usar

| Situacao | Acao |
|----------|------|
| Bug pontual, 1 arquivo, < 200 LOC | Resolver direto (sem skill) |
| Bug multi-arquivo, mesmo modulo, < 2K LOC | Resolver direto (skill e overhead) |
| Feature com spec clara | `ralph-wiggum` |
| Problema DESCONHECIDO, G/XG (2+ criterios acima) | **ESTA SKILL** |
| Saude do banco | `diagnosticando-banco` |
| Operacao Odoo | Skill Odoo especifica |

### Desambiguacao

- Problema **DESCONHECIDO** → `resolvendo-problemas`. Problema **CONHECIDO** + spec → `ralph-wiggum`
- **Saude** do banco → `diagnosticando-banco`. **Bug** envolvendo banco → `resolvendo-problemas`
- Operacao Odoo **especifica** → skill Odoo. Problema **cross-system** envolvendo Odoo → `resolvendo-problemas`

---

## Visao Geral das 7 Fases

```
Fase 0: ESCOPO ──────── Delimitar problema, classificar complexidade
  │                      Budget: ~5% contexto
  ▼
Fase 1: PESQUISA ─────── Subagentes atomicos, 1 pergunta = 1 finding
  │                      Budget: ~10% contexto (principal)
  ▼
Fase 2: ANALISE ──────── 5 Porques / CAPDO / Ishikawa
  │                      Budget: ~15% contexto
  ▼
Fase 3: PLANO ────────── Tarefas ordenadas, superestimacao 1.5x
  │                      Budget: ~15% contexto
  ▼
Fase 4: VALIDAR PLANO ── Subagente adversarial tenta QUEBRAR o plano
  │                      Budget: ~5% contexto
  ▼
Fase 5: IMPLEMENTAR ──── Executar 1 tarefa por vez
  │                      Budget: ~30% contexto
  ▼
Fase 6: VALIDAR ───────── Estrutural + funcional + regressao
                          Budget: ~10% contexto
```

> Detalhamento completo de cada fase: [references/fases.md](references/fases.md)

---

## Setup da Sessao

Ao iniciar uma sessao de resolucao:

```bash
# Gerar session-id unico
SESSION_ID=$(date +%Y%m%d-%H%M%S)-$(head -c 4 /dev/urandom | xxd -p)

# Criar estrutura
mkdir -p /tmp/subagent-findings/${SESSION_ID}/{phase1,phase2,phase3,phase4,phase5,phase6}

# Criar session-log
echo "# Session Log: ${SESSION_ID}" > /tmp/subagent-findings/${SESSION_ID}/session-log.md
echo "Inicio: $(date -Iseconds)" >> /tmp/subagent-findings/${SESSION_ID}/session-log.md
```

---

## Classificacao de Complexidade (Fase 0)

| Classe | Escopo | Acao |
|--------|--------|------|
| **P** (pontual) | 1 arquivo, < 200 LOC | Resolver direto, SEM skill |
| **M** (modulo) | Multi-arquivo, mesmo modulo, < 2K LOC | Pesquisa direta pelo principal |
| **G** (grande) | Cross-modulo, < 10K LOC | Subagentes de pesquisa |
| **XG** (extra-grande) | System-wide, 10K+ LOC | Subagentes em ondas |

> Se classificado como P: sair da skill e resolver direto.
> Se classificado como M: pular Fase 1 (subagentes), pesquisar diretamente.

---

## Protocolo de Findings (Filesystem)

Toda comunicacao entre fases vai via filesystem, bypassando compressao lossy de subagentes.

```
/tmp/subagent-findings/
  {session-id}/
    phase1/                        # Pesquisa atomica
      question-1-inventario.md
      question-2-dependencias.md
      question-3-comportamento.md
    phase2/                        # Analise
      analysis.md
    phase3/                        # Plano
      plan.md
    phase4/                        # Validacao adversarial
      review.md
    phase5/                        # Implementacao
      task-1.md
      task-2.md
    phase6/                        # Validacao final
      regression-check.md
    session-log.md                 # Transicoes, decisoes, loop-backs
```

### Formato Obrigatorio de Finding

Todo arquivo de finding DEVE usar:

```markdown
## Fatos Verificados
- {afirmacao} — FONTE: {arquivo-absoluto}:{linhas}

## Inferencias
- {conclusao} — BASEADA EM: {fatos que suportam}

## Nao Encontrado
- {buscado} — BUSCADO EM: {onde}

## Assuncoes
- [ASSUNCAO] {decisao sem confirmacao}
```

> Templates de prompt completos: [references/prompt-templates.md](references/prompt-templates.md)

---

## Modelo de Confianca Incremental

| Nivel | Condicao | Acao |
|-------|----------|------|
| 0 (Sem confianca) | Primeiro output de subagente | Spot-check 50% dos fatos |
| 1 (Parcial) | Spot-check anterior sem erros | Confiar fatos restantes, spot-check 20% |
| 2 (Funcional) | 2 outputs consecutivos sem erros | Confiar fatos, verificar cross-refs |
| 3 (Conquistada) | Fase 4 confirma fatos da Fase 1 | Parar spot-checks |

**NUNCA confiar cegamente em**: dados numericos, claims negativos ("X nao existe"), claims cross-modulo.

---

## Gatilhos de Loop-Back

```
Em qualquer gate de validacao:
  │
  ├── 0 issues ─────────────── PROSSEGUIR
  │
  ├── 1-2 issues menores ───── CORRIGIR INLINE, revalidar mesma fase
  │
  └── 3+ issues OU 1 erro fundamental ── LOOP-BACK:
        │
        ├── Erro nos FATOS ──────────── → Fase 1 (re-pesquisa)
        ├── Erro na ANALISE ─────────── → Fase 2 (re-analise)
        ├── Erro no PLANO ──────────── → Fase 3 (re-plano)
        ├── Erro na IMPLEMENTACAO ──── → Fase 5 (tarefa especifica)
        └── Contradicao entre fases ── → Fase 0 (re-escopo)
```

---

## Integracao com Skills Existentes

| Skill | Ponto de Integracao |
|-------|---------------------|
| `ralph-wiggum` | Fase 5 para XG: plano da Fase 3 vira spec do Ralph loop |
| `prd-generator` | Fase 0: se o "problema" e na verdade uma feature request |
| `consultando-sql` | Fase 1: investigacoes com dados do banco |
| `diagnosticando-banco` | Fase 1: problemas de performance |
| CLAUDE.md de modulo | Fase 1: subagentes DEVEM ler CLAUDE.md do modulo ANTES de pesquisar |

---

## Checklists

> Checklists obrigatorios por fase: [references/checklists.md](references/checklists.md)

## Metodos de Qualidade

> Quick-ref de 5 Porques, CAPDO, Ishikawa: [references/metodos-qualidade.md](references/metodos-qualidade.md)

---

## Exemplo: Iniciando uma Sessao

```
Usuario: "Por que o agente web esta perdendo contexto em sessoes longas?"

Principal:
  Fase 0 - ESCOPO:
  - Problema: Perda de contexto em sessoes longas do agente web
  - Perguntas de pesquisa:
    Q1: Inventario de app/agente/services/ (arquivos, LOC, exports)
    Q2: Trace do fluxo de mensagem entrada→resposta
    Q3: Como o contexto e gerenciado (window, compressao, etc)
    Q4: Quais limites de tokens existem e onde sao aplicados
  - Classificacao: G (cross-modulo, ~6K LOC em services + routes + SDK)
  - CLAUDE.md relevantes: app/agente/CLAUDE.md, app/agente/services/CLAUDE.md
  - Decisao: Usar subagentes para pesquisa atomica

  [Cria session, spawna 4 subagentes em paralelo...]
```
