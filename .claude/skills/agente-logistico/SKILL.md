---
name: agente-logistico
description: "Consultas rapidas sobre carteira, estoque e pedidos da Nacom Goya. Use para: 'tem pedido do Atacadao?', 'quanto tem de palmito?', 'pedidos atrasados', 'status do pedido VCD123', 'estoque de azeitona', 'o que vai dar falta?', 'quando fica disponivel?', 'o que esta travando a carteira?'. Para analise COMPLETA de carteira ou criacao de separacoes em lote, delegue ao subagente 'agente-logistico' via Task tool."
---

# Agente Logistico - Consultas e Separacoes

## Quando Usar Esta Skill

### USE para consultas RAPIDAS:
- "Tem pedido pendente pro Atacadao?"
- "Quanto tem de palmito no estoque?"
- "Pedidos atrasados pra embarcar"
- "Status do pedido VCD123"
- "O que vai dar falta essa semana?"
- "Chegou o cogumelo?"
- "Quando o pedido VCD123 estara disponivel?"
- "O que esta travando a carteira?"

### DELEGUE ao subagente para:
- Analise completa da carteira
- Criacao de separacoes em lote
- Comunicacao com PCP/Comercial
- Decisoes de priorizacao complexas

---

## Scripts Disponiveis

### 1. analisando_disponibilidade.py

**Proposito:** Analisa disponibilidade de estoque para pedidos ou grupos de clientes.

**Queries cobertas:** Q1, Q2, Q3, Q4, Q5, Q6, Q9, Q11, Q12

```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate && \
python .claude/skills/agente-logistico/scripts/analisando_disponibilidade.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--pedido` | Numero do pedido ou "grupo termo" | `--pedido VCD123` ou `--pedido "atacadao 183"` |
| `--grupo` | Grupo empresarial | `--grupo atacadao`, `--grupo assai`, `--grupo tenda` |
| `--loja` | Identificador da loja (em raz_social_red) | `--loja 183` |
| `--uf` | Filtrar por UF | `--uf SP` |
| `--data` | Data para analise (hoje, amanha, dd/mm, YYYY-MM-DD) | `--data amanha` |
| `--sem-agendamento` | Apenas pedidos sem exigencia de agendamento | flag |
| `--sugerir-adiamento` | Sugerir pedidos para adiar (liberar estoque) | flag |
| `--diagnosticar-origem` | Distinguir falta absoluta vs relativa | flag |
| `--completude` | Calcular % faturado vs pendente | flag |
| `--atrasados` | Analisar pedidos com expedicao vencida | flag |
| `--diagnosticar-causa` | Detalhar causa do atraso | flag |
| `--ranking-impacto` | Ranking de pedidos que mais travam carteira | flag |
| `--limit` | Limite de resultados (default: 100) | `--limit 20` |

**Exemplos de uso:**

| Pergunta do Usuario | Comando |
|---------------------|---------|
| "Quando VCD123 estara disponivel?" | `--pedido VCD123` |
| "O que vai ter de ruptura se enviar VCD123 amanha?" | `--pedido VCD123 --data amanha` |
| "Qual pedido adiar pra enviar VCD123 amanha?" | `--pedido VCD123 --data amanha --sugerir-adiamento` |
| "O que falta pro Assai de SP?" | `--grupo assai --uf SP` |
| "Falta absoluta ou relativa?" | `--grupo assai --diagnosticar-origem` |
| "Pedidos sem agendamento para amanha?" | `--data amanha --sem-agendamento` |
| "Falta muito pra matar o Atacadao 183?" | `--grupo atacadao --loja 183 --completude` |
| "Os atrasados sao por falta?" | `--atrasados --diagnosticar-causa` |
| "O que esta travando a carteira?" | `--ranking-impacto` |

---

### 2. consultando_pedidos.py

**Proposito:** Consulta pedidos por diversos filtros e perspectivas.

**Queries cobertas:** Q8, Q10, Q14, Q16, Q19

```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate && \
python .claude/skills/agente-logistico/scripts/consultando_pedidos.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--pedido` | Numero do pedido ou termo de busca | `--pedido VCD123` |
| `--grupo` | Grupo empresarial | `--grupo atacadao` |
| `--atrasados` | Listar pedidos atrasados | flag |
| `--verificar-bonificacao` | Verificar bonificacoes faltando | flag |
| `--status` | Mostrar status detalhado | flag |
| `--consolidar-com` | Buscar pedidos para consolidar | `--consolidar-com "assai 123"` |
| `--produto` | Filtrar por produto | `--produto palmito` |
| `--ate-data` | Data limite de expedicao | `--ate-data amanha`, `--ate-data 15/12` |
| `--em-separacao` | Buscar em Separacao (nao CarteiraPrincipal) | flag |
| `--limit` | Limite de resultados (default: 100) | `--limit 20` |

**Exemplos de uso:**

| Pergunta do Usuario | Comando |
|---------------------|---------|
| "Tem pedido pendente pro Atacadao?" | `--grupo atacadao` |
| "Pedidos atrasados pra embarcar?" | `--atrasados` |
| "Tem pedido faltando bonificacao?" | `--verificar-bonificacao` |
| "Pedido VCD123 ta em separacao?" | `--pedido VCD123 --status` |
| "Tem mais pedido pra mandar junto com Assai 123?" | `--consolidar-com "assai 123"` |
| "Pedidos de palmito ate amanha?" | `--produto palmito --ate-data amanha` |
| "Pedidos de azeitona ja separados?" | `--produto azeitona --em-separacao` |

---

### 3. consultando_estoque.py

**Proposito:** Consulta estoque atual, movimentacoes, pendencias e projecoes.

**Queries cobertas:** Q13, Q17, Q18, Q20

```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate && \
python .claude/skills/agente-logistico/scripts/consultando_estoque.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--produto` | Nome ou termo do produto | `--produto palmito`, `--produto "az verde"` |
| `--entradas` | Mostrar entradas recentes (qtd > 0) | flag |
| `--saidas` | Mostrar saidas recentes (qtd < 0) | flag |
| `--pendente` | Quantidade pendente de embarque + lista pedidos | flag |
| `--sobra` | Calcular sobra de estoque apos demanda | flag |
| `--ruptura` | Previsao de rupturas | flag |
| `--dias` | Horizonte de projecao em dias (default: 7) | `--dias 14` |
| `--limit` | Limite de resultados (default: 100) | `--limit 50` |
| `--limit-entradas` | Limite de movimentacoes por produto (default: 100) | `--limit-entradas 20` |

**Exemplos de uso:**

| Pergunta do Usuario | Comando |
|---------------------|---------|
| "Chegou o palmito?" | `--produto palmito --entradas` |
| "Saiu muito cogumelo?" | `--produto cogumelo --saidas` |
| "Falta embarcar muito pessego?" | `--produto pessego --pendente` |
| "Quanto vai sobrar de pessego?" | `--produto pessego --sobra` |
| "O que vai dar falta essa semana?" | `--ruptura --dias 7` |
| "Rupturas nos proximos 14 dias?" | `--ruptura --dias 14` |

---

### 4. calculando_prazo.py

**Proposito:** Calcula data de entrega baseada em lead time de transportadoras.

**Queries cobertas:** Q7

```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate && \
python .claude/skills/agente-logistico/scripts/calculando_prazo.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--pedido` | Numero do pedido ou termo de busca | `--pedido VCD123`, `--pedido "atacadao 183"` |
| `--data-embarque` | Data de embarque (hoje, amanha, dd/mm, YYYY-MM-DD) | `--data-embarque amanha` |
| `--limit` | Limite de opcoes de transportadora (default: 5) | `--limit 3` |

**Exemplos de uso:**

| Pergunta do Usuario | Comando |
|---------------------|---------|
| "Se embarcar VCD123 amanha, quando chega?" | `--pedido VCD123 --data-embarque amanha` |
| "Prazo de entrega pro Atacadao 183?" | `--pedido "atacadao 183" --data-embarque hoje` |

---

### 5. criando_separacao.py

**Proposito:** Cria separacoes de pedidos via linguagem natural.

**IMPORTANTE:** Sempre executar primeiro SEM `--executar` para simular!

```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate && \
python .claude/skills/agente-logistico/scripts/criando_separacao.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--pedido` | Numero do pedido (OBRIGATORIO) | `--pedido VCD123` |
| `--expedicao` | Data de expedicao (OBRIGATORIO) | `--expedicao amanha`, `--expedicao 20/12` |
| `--tipo` | Tipo de separacao | `--tipo completa`, `--tipo parcial` |
| `--pallets` | Quantidade de pallets desejada | `--pallets 28` |
| `--pallets-inteiros` | Forcar pallets inteiros por item | flag |
| `--apenas-estoque` | Separar apenas o que tem em estoque | flag |
| `--excluir-produtos` | JSON array de produtos a excluir | `--excluir-produtos '["KETCHUP","MOSTARDA"]'` |
| `--agendamento` | Data de agendamento | `--agendamento 22/12` |
| `--protocolo` | Protocolo de agendamento | `--protocolo AG12345` |
| `--agendamento-confirmado` | Marcar agendamento como confirmado | flag |
| `--executar` | Efetivamente criar (sem isso, apenas simula) | flag |

**Modos de operacao:**

| Modo | Descricao |
|------|-----------|
| Sem `--executar` | SIMULA e mostra o que seria criado |
| Com `--executar` | CRIA efetivamente a separacao |

**Tipos de separacao:**

| Tipo | Parametros | Descricao |
|------|------------|-----------|
| Completa | `--tipo completa` | Todos os itens com qtd total |
| Parcial | `--tipo parcial` | N itens com qtds especificas |
| Por pallets | `--pallets N` | Distribuir N pallets proporcionalmente |
| Pallets inteiros | `--pallets N --pallets-inteiros` | Cada item = pallets inteiros |
| Apenas estoque | `--apenas-estoque` | So o que tem disponivel |
| Excluindo produtos | `--excluir-produtos '[...]'` | Tudo exceto lista |

**Exemplos de uso:**

| Pedido do Usuario | Comando (simular) |
|-------------------|-------------------|
| "Crie separacao completa do VCD123 pra amanha" | `--pedido VCD123 --expedicao amanha --tipo completa` |
| "Separacao VCD456 com 28 pallets dia 20/12" | `--pedido VCD456 --expedicao 20/12 --pallets 28` |
| "VCD789 com pallets inteiros" | `--pedido VCD789 --expedicao amanha --pallets 28 --pallets-inteiros` |
| "Enviar o que tem do VCD123" | `--pedido VCD123 --expedicao amanha --apenas-estoque` |
| "VCD123 sem ketchup e mostarda" | `--pedido VCD123 --expedicao amanha --excluir-produtos '["KETCHUP","MOSTARDA"]'` |

---

### 6. analisando_carteira_completa.py

**Proposito:** Analisa a carteira completa seguindo o algoritmo de priorizacao do Rafael.

**A CEREJA DO BOLO** - Orquestrador que segue exatamente a ordem de prioridades definida:
1. Pedidos com `data_entrega_pedido` (cliente ja negociou)
2. Cargas diretas fora de SP (>=26 pallets OU >=20.000kg)
3. Atacadao
4. Assai
5. Resto ordenado por CNPJ + Rota

```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate && \
python .claude/skills/agente-logistico/scripts/analisando_carteira_completa.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--resumo` | Mostrar apenas resumo executivo | flag |
| `--prioridade` | Filtrar por prioridade (1-5) | `--prioridade 1`, `--prioridade 3` |
| `--limit` | Limite de pedidos (default: todos) | `--limit 20` |
| `--acoes` | Mostrar apenas acoes imediatas | flag |

**Saida inclui:**
- Pedidos classificados por prioridade
- Gestor responsavel (extraido de `equipe_vendas`)
- Acoes imediatas recomendadas
- Separacoes sugeridas
- Status de agendamento

**Exemplos de uso:**

| Pergunta do Usuario | Comando |
|---------------------|---------|
| "Analise a carteira" | sem parametros (mostra tudo) |
| "Resumo da carteira" | `--resumo` |
| "O que precisa de atencao imediata?" | `--resumo --limit 10` |
| "Pedidos com data negociada" | `--prioridade 1` |
| "Status do Atacadao" | `--prioridade 3` |
| "Acoes pra hoje" | `--acoes` |

**Identificacao de Gestores (via `equipe_vendas`):**

| Valor no campo | Gestor | Canal |
|----------------|--------|-------|
| VENDA EXTERNA ATACADÃO | Junior | WhatsApp |
| VENDA EXTERNA SENDAS SP | Junior | WhatsApp |
| VENDA EXTERNA MILER | Miler | WhatsApp |
| VENDA EXTERNA FERNANDO | Fernando | WhatsApp |
| VENDA EXTERNA JUNIOR | Junior | WhatsApp |
| VENDA INTERNA DENISE | Denise | Teams |

---

## Grupos Empresariais

| Grupo | Prefixos CNPJ | Exemplo |
|-------|---------------|---------|
| Atacadao | 93.209.76, 75.315.33, 00.063.96 | `--grupo atacadao` |
| Assai | 06.057.22 | `--grupo assai` |
| Tenda | 01.157.55 | `--grupo tenda` |

---

## Resolucao de Produtos

Usuarios podem usar termos abreviados:

| Abreviacao | Significado |
|------------|-------------|
| AZ | Azeitona |
| PF | Preta Fatiada |
| VF | Verde Fatiada |
| VI | Verde Inteira |
| BD | Balde |
| IND | Industrial |
| POUCH | Pouch |

**Exemplo:** "pf mezzani" = Azeitona Preta Fatiada Mezzani

---

## Termos do Dominio

| Termo | Significado |
|-------|-------------|
| Matar pedido | Completar 100% do pedido |
| Ruptura | Falta de estoque para atender demanda |
| Falta absoluta | Estoque < demanda (mesmo sem outros pedidos) |
| Falta relativa | Estoque comprometido com outros pedidos |
| RED | Redespacho via SP |
| FOB | Cliente coleta no CD |
| BD IND | Balde Industrial |

---

## Nivel de Detalhes (Progressive Disclosure)

1. **Resposta inicial**: Resumo com 3-5 itens principais
2. **Se pedir mais**: Mostrar mais itens do mesmo JSON
3. **Se pedir "todos"**: Lista completa

---

## Fluxo de Criacao de Separacao

### Checklist Obrigatorio

| Campo | Obrigatorio | Como Obter |
|-------|-------------|------------|
| Pedido | SIM | Usuario informa |
| Data expedicao | SIM | Usuario informa |
| Tipo (completa/parcial) | SIM | Perguntar se nao especificado |
| Agendamento | CONDICIONAL | Verificar ContatoAgendamento pelo CNPJ |
| Protocolo | CONDICIONAL | Se exige agendamento |

### Sequencia

1. **SIMULAR** primeiro (sem --executar)
2. Verificar alertas de estoque
3. Mostrar resultado ao usuario
4. Solicitar confirmacao
5. **EXECUTAR** (com --executar)

---

## Referencias

- [AGENT.md](AGENT.md) - Regras completas de negocio
- [QUERIES.md](reference/QUERIES.md) - Mapeamento das 20 queries
- [REGRAS_NEGOCIO.md](../../references/REGRAS_NEGOCIO.md) - Regras gerais
