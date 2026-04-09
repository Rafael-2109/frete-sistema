# Golden Dataset — Avaliacao de Subagents

**Ultima Atualizacao**: 2026-04-09
**Escopo piloto**: 3 agents (analista-carteira, auditor-financeiro, controlador-custo-frete)

---

## Contexto

Este diretorio contem um framework de avaliacao **OFFLINE** para os subagents do sistema de fretes. Runtime = **Claude Code CLI** (ou Task tool em sessao interativa) — **sem chamadas diretas a API Anthropic**.

**Por que offline?** 
1. Evita custos de API nao controlados
2. Usa o mesmo runtime dos agents em producao (Claude Code CLI)
3. Permite comparacao manual pelo usuario/desenvolvedor (sem depender de LLM-as-judge)

---

## Estrutura

```
.claude/evals/subagents/
├── README.md                              # este arquivo
├── run_eval.md                            # instrucoes de execucao
├── analista-carteira/
│   └── dataset.yaml                       # 5 casos piloto
├── auditor-financeiro/
│   └── dataset.yaml                       # 5 casos piloto
└── controlador-custo-frete/
    └── dataset.yaml                       # 5 casos piloto
```

---

## Formato do dataset.yaml

```yaml
agent: analista-carteira
version: 1.0
cases:
  - id: ac-01
    title: "Titulo descritivo do caso"
    input: |
      Mensagem do usuario simulada (o que seria digitado).
    context:
      # Dados conhecidos para executar o teste (nao vao direto ao agent)
      pedido: "VCD123"
      cliente: "Atacadao CD 183"
    expected_behavior:
      - "Comportamento observavel 1 que DEVE acontecer"
      - "Comportamento observavel 2 que DEVE acontecer"
    must_not:
      - "Comportamento proibido 1"
      - "Comportamento proibido 2"
    tags: [p1, fob, atacadao-183]
```

**Campos**:
- `id`: identificador unico (prefixo `ac-` para analista-carteira, `af-` para auditor-financeiro, `ccf-` para controlador-custo-frete)
- `title`: descricao curta do caso
- `input`: mensagem do usuario que seria digitada no Claude Code
- `context`: dados conhecidos sobre o cenario (nao vao para o agent, mas documentam a intencao)
- `expected_behavior`: lista de comportamentos que o agent DEVE demonstrar (observaveis no output)
- `must_not`: lista de comportamentos que o agent NAO pode ter (anti-padroes)
- `tags`: classificacao para filtragem (ex: apenas casos de anti-alucinacao)

---

## Criterios de Pass/Fail

Um caso **passa** quando:
1. TODOS os itens de `expected_behavior` sao observados no output
2. NENHUM item de `must_not` e violado

Um caso **falha** quando:
1. Pelo menos 1 item de `expected_behavior` nao e observado
2. OU pelo menos 1 item de `must_not` e violado

**Julgamento e MANUAL** (nao automatizado por LLM). O desenvolvedor le o output do agent e compara com o dataset.

---

## Quando Rodar Evals

**Obrigatorio**:
- Antes de fazer commit de mudanca em agent modificado
- Antes de release/deploy
- Quando uma regra de negocio relevante mudar (ex: atualizar REGRAS_P1_P7.md)

**Recomendado**:
- Mensalmente como sanity check
- Apos descobrir nova armadilha (adicionar caso e rodar)

---

## Como Adicionar Novos Casos

1. Identificar comportamento observado em producao (certo ou errado)
2. Criar caso no dataset.yaml do agent correspondente
3. Documentar `expected_behavior` e `must_not` com precisao
4. Rodar uma vez para estabelecer baseline
5. Commitar junto com eventual fix/mudanca

---

## Expansao Futura

Piloto cobre 3 agents (criticos: decisao operacional + escrita financeira + custo). Expansao planejada:

- **Fase 2**: adicionar casos para `gestor-ssw` (operacoes POP-A10), `gestor-recebimento` (pipeline 4 fases), `especialista-odoo` (orquestracao cross-area)
- **Fase 3**: cobrir os 6 agents restantes (analista-performance, gestor-estoque, gestor-devolucoes, gestor-carvia, raio-x-pedido, desenvolvedor-integracao-odoo)

Cada fase deve ter ~5-10 casos por agent. Total alvo: 60-120 casos.

---

## Referencias

- `.claude/references/AGENT_TEMPLATES.md` — blocos reusaveis (pre-mortem, self-critique)
- `.claude/references/SUBAGENT_RELIABILITY.md` — protocolo de confiabilidade
- `.claude/references/AGENT_DESIGN_GUIDE.md` — manual de criacao/edicao de agents
- `.claude/references/negocio/REGRAS_P1_P7.md` — regras de priorizacao (base para casos ac-*)
