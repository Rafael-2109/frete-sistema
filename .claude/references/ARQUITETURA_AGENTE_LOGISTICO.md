# Arquitetura Hibrida - Agente Logistico

**Versao**: 1.0
**Data**: 06/12/2025
**Baseado em**: Documentacao Oficial Anthropic + Extracao de Conhecimento do Rafael

---

## VISAO GERAL

O Agente Logistico utiliza uma **arquitetura hibrida** combinando:

1. **Skill** (consultas-logistica) - Para consultas rapidas auto-invocadas
2. **Subagente** (agente-logistico) - Para analise completa e criacao de separacoes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        ARQUITETURA HIBRIDA                                  │
└─────────────────────────────────────────────────────────────────────────────┘

USUARIO
   │
   ├──► "Quanto tem de palmito?"
   │         │
   │         ▼
   │    ┌─────────────────────────────────────────┐
   │    │  SKILL: consultas-logistica             │
   │    │  (Auto-invocada por contexto)           │
   │    │                                         │
   │    │  - Consultas rapidas                    │
   │    │  - Status de pedidos                    │
   │    │  - Estoque e projecoes                  │
   │    │  - Leadtimes                            │
   │    └─────────────────────────────────────────┘
   │
   └──► "Analise a carteira e crie separacoes"
             │
             ▼
        ┌─────────────────────────────────────────┐
        │  SUBAGENTE: agente-logistico            │
        │  (Delegacao explicita via Task tool)    │
        │                                         │
        │  - Analise completa da carteira         │
        │  - Decisoes de priorizacao              │
        │  - Comunicacao com PCP/Comercial        │
        │  - Criacao de separacoes                │
        │  - Fluxos multi-step                    │
        └─────────────────────────────────────────┘
```

---

## ESTRUTURA DE ARQUIVOS

```
.claude/
├── agents/
│   └── agente-logistico.md          # Subagente especializado
│
├── skills/
│   └── agente-logistico/
│       ├── SKILL.md                  # Consultas rapidas (auto-invocadas)
│       ├── AGENT.md                  # Documentacao completa de regras
│       ├── reference/
│       │   └── QUERIES.md            # Mapeamento das 20 queries
│       └── scripts/
│           ├── analisando_disponibilidade.py
│           ├── consultando_pedidos.py
│           ├── consultando_estoque.py
│           ├── calculando_prazo.py
│           ├── analisando_programacao.py
│           ├── criando_separacao.py
│           └── resolver_entidades.py
│
└── references/
    ├── REGRAS_NEGOCIO.md             # Regras gerais do sistema
    ├── MODELOS_CAMPOS.md             # Esquema do banco
    └── ARQUITETURA_AGENTE_LOGISTICO.md  # Este arquivo
```

---

## QUANDO USAR CADA COMPONENTE

### SKILL (consultas-logistica)

**Invocacao:** Automatica por contexto (Claude decide)

**Triggers (palavras-chave na pergunta):**
- "tem pedido", "pedidos do", "status do pedido"
- "estoque", "quanto tem", "chegou", "saiu"
- "atrasado", "falta", "ruptura"
- "quando chega", "lead time", "prazo"

**Exemplos de uso:**
```
Usuario: "Tem pedido pendente pro Atacadao?"
         → Skill invocada automaticamente
         → Executa consultando_pedidos.py --grupo atacadao
         → Retorna lista de pedidos

Usuario: "Quanto tem de palmito no estoque?"
         → Skill invocada automaticamente
         → Executa consultando_estoque.py --produto palmito
         → Retorna estoque atual
```

**Caracteristicas:**
- Resposta rapida (1 script)
- Sem necessidade de confirmacao
- Contexto compartilhado com conversa principal
- Foco em LEITURA de dados

---

### SUBAGENTE (agente-logistico)

**Invocacao:** Explicita via Task tool

**Triggers (complexidade da tarefa):**
- "analise a carteira", "analise completa"
- "crie separacao", "gere separacoes"
- "o que devo priorizar", "priorize"
- "comunique o PCP", "informe o comercial"

**Exemplos de uso:**
```
Usuario: "Analise a carteira e me diga o que priorizar hoje"
         → Subagente delegado explicitamente
         → Executa algoritmo de priorizacao completo
         → Retorna relatorio com:
           - Resumo executivo
           - Acoes imediatas
           - Comunicacoes necessarias
           - Separacoes sugeridas

Usuario: "Crie separacao do pedido VCD123 para dia 20/12"
         → Subagente delegado
         → Verifica estoque
         → Verifica agendamento
         → Simula separacao
         → Solicita confirmacao
         → Cria separacao
```

**Caracteristicas:**
- Fluxos multi-step
- Pode solicitar confirmacoes
- Contexto isolado (nao polui conversa principal)
- Acesso completo as regras de negocio
- Pode CRIAR/MODIFICAR dados

---

## FLUXO DE DECISAO

```python
def decidir_componente(pergunta_usuario):
    # SUBAGENTE: Tarefas complexas ou criacao
    if any(termo in pergunta_usuario.lower() for termo in [
        "analise completa", "analise a carteira",
        "crie separacao", "gere separacao",
        "priorizar", "priorizacao",
        "comunique", "informe pcp", "informe comercial"
    ]):
        return "SUBAGENTE: agente-logistico"

    # SKILL: Consultas simples
    if any(termo in pergunta_usuario.lower() for termo in [
        "tem pedido", "status", "estoque",
        "quanto tem", "chegou", "atrasado",
        "falta", "ruptura", "prazo"
    ]):
        return "SKILL: consultas-logistica"

    # DEFAULT: Avaliar contexto
    return "AVALIAR_CONTEXTO"
```

---

## INTEGRACAO COM CLAUDE CODE

### Skill (Auto-invocada)

Quando Claude identifica uma consulta simples:
1. SKILL.md e carregado automaticamente
2. Script apropriado e selecionado
3. Resultado e retornado na mesma conversa

### Subagente (Delegacao)

Quando Claude identifica tarefa complexa:
1. Task tool e invocada com `subagent_type="agente-logistico"`
2. AGENT.md em `.claude/agents/` e carregado
3. Subagente executa com contexto proprio
4. Resultado e retornado para conversa principal

---

## MODELO DE DADOS

### Skill carrega:

```yaml
# .claude/skills/agente-logistico/SKILL.md
name: consultas-logistica
description: "Consultas rapidas sobre carteira, estoque..."

# Conteudo: Scripts e parametros disponiveis
```

### Subagente carrega:

```yaml
# .claude/agents/agente-logistico.md
name: agente-logistico
description: "Analista de carteira especializado..."
tools: Glob, Grep, Read, Bash, Write, Edit
model: opus

# Conteudo: Conhecimento completo da empresa + regras de negocio
```

### Documentacao completa (referencia):

```
# .claude/skills/agente-logistico/AGENT.md
# Documento extenso com TODAS as regras:
- Estrutura da empresa
- Top clientes
- Algoritmo de priorizacao
- Regras de parcial
- Comunicacao PCP/Comercial
- Leadtimes
- etc.
```

---

## ECONOMIA DE CONTEXTO

| Componente | Contexto Usado | Quando |
|------------|----------------|--------|
| Skill | ~2K tokens | Consultas simples |
| Subagente | ~15K tokens | Analise completa |

**Estrategia:**
- Skills para 90% das interacoes (rapido, barato)
- Subagente para 10% (analise profunda, mais caro)

---

## METRICAS DE SUCESSO

### Skill

| Metrica | Meta |
|---------|------|
| Tempo de resposta | < 5 segundos |
| Precisao | > 95% |
| Taxa de invocacao correta | > 90% |

### Subagente

| Metrica | Meta |
|---------|------|
| Tempo de analise completa | < 2 minutos |
| Decisoes corretas | > 90% |
| Economia de tempo do Rafael | 2-3 horas/dia |

---

## EVOLUCAO PLANEJADA

### FASE 1 (Atual): SUGERIR

```
Skill: Consultas autonomas
Subagente: Sugere acoes, usuario confirma
```

### FASE 2 (Futuro): AUTOMATICO

```
Skill: Consultas autonomas
Subagente: Cria separacoes automaticamente
           Envia comunicacoes automaticamente
           Solicita agendamentos automaticamente
```

### FASE 3 (Futuro): PROATIVO

```
Subagente: Analisa carteira automaticamente
           Alerta sobre problemas
           Sugere acoes preventivas
```

---

## TROUBLESHOOTING

### Skill nao esta sendo invocada

1. Verificar se SKILL.md tem `description` com trigger terms corretos
2. Verificar se pergunta contem palavras-chave esperadas
3. Testar com pergunta mais explicita

### Subagente nao aparece na Task tool

1. Verificar se arquivo esta em `.claude/agents/`
2. Verificar frontmatter YAML (name, description)
3. Reiniciar Claude Code

### Subagente nao tem conhecimento completo

1. Verificar se `.claude/skills/agente-logistico/AGENT.md` existe
2. Verificar se AGENT.md do subagente referencia o arquivo correto
3. Atualizar referencias se necessario

---

## REFERENCIAS

| Documento | Conteudo |
|-----------|----------|
| `.claude/agents/agente-logistico.md` | Configuracao do subagente |
| `.claude/skills/agente-logistico/SKILL.md` | Skill de consultas |
| `.claude/skills/agente-logistico/AGENT.md` | Regras completas de negocio |
| `.claude/references/REGRAS_NEGOCIO.md` | Regras gerais do sistema |
| `.claude/references/MODELOS_CAMPOS.md` | Esquema do banco de dados |

---

*Documento criado em 06/12/2025 apos extracao de conhecimento com Rafael (dono)*
