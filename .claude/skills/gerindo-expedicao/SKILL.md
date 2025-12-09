---
name: gerindo-expedicao
description: Consulta e opera dados logisticos da Nacom Goya. Consulta pedidos, estoque, disponibilidade, lead time. Cria separacoes. Resolve entidades (pedido, produto, cliente, grupo). Use para perguntas como 'tem pedido do Atacadao?', 'quanto tem de palmito?', 'quando fica disponivel?', 'crie separacao do VCD123'.
allowed-tools: Read, Bash, Glob, Grep
---

# Gerindo Expedicao

Skill para consultas e operacoes logisticas da Nacom Goya.

## Quando Usar Esta Skill

USE para:
- Consultas de pedidos: "tem pedido do Atacadao?", "pedido VCD123 esta em separacao?"
- Consultas de estoque: "quanto tem de palmito?", "chegou cogumelo?"
- Analise de disponibilidade: "quando VCD123 fica disponivel?", "o que vai dar falta?"
- Calculo de prazo: "se embarcar amanha, quando chega?"
- Criacao de separacao: "crie separacao do VCD123 pra amanha"
- Resolucao de entidades: identificar pedido, produto, cliente por termos parciais

NAO USE para:
- Analise COMPLETA da carteira com decisoes (use o Agent `analista-carteira`)
- Comunicacao com PCP ou Comercial (use o Agent)
- Decisoes de priorizacao P1-P7 (use o Agent)

---

## Scripts Disponiveis

### Ambiente Virtual

Sempre ativar antes de executar:
```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate
```

---

### 1. analisando_disponibilidade_estoque.py

**Proposito:** Analisa disponibilidade de estoque para pedidos ou grupos de clientes.

**Queries cobertas:** Q1, Q2, Q3, Q4, Q5, Q6, Q9, Q11, Q12

```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate && \
python .claude/skills/gerindo-expedicao/scripts/analisando_disponibilidade_estoque.py [parametros]
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

---

### 2. consultando_situacao_pedidos.py

**Proposito:** Consulta pedidos por diversos filtros e perspectivas.

**Queries cobertas:** Q8, Q10, Q14, Q16, Q19

```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate && \
python .claude/skills/gerindo-expedicao/scripts/consultando_situacao_pedidos.py [parametros]
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

---

### 3. consultando_produtos_estoque.py

**Proposito:** Consulta estoque atual, movimentacoes, pendencias, projecoes e SITUACAO COMPLETA.

**Queries cobertas:** Q13, Q17, Q18, Q20 + SITUACAO COMPLETA

```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate && \
python .claude/skills/gerindo-expedicao/scripts/consultando_produtos_estoque.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--produto` | Nome ou termo do produto | `--produto palmito`, `--produto "az verde"` |
| `--completo` | ⭐ **SITUACAO COMPLETA** (estoque, separacoes, demanda, producao, projecao) | flag |
| `--entradas` | Mostrar entradas recentes (qtd > 0) | flag |
| `--saidas` | Mostrar saidas recentes (qtd < 0) | flag |
| `--pendente` | Quantidade pendente de embarque + lista pedidos | flag |
| `--sobra` | Calcular sobra de estoque apos demanda | flag |
| `--ruptura` | Previsao de rupturas | flag |
| `--dias` | Horizonte de projecao em dias (default: 7) | `--dias 14` |
| `--limit` | Limite de resultados (default: 100) | `--limit 50` |
| `--limit-entradas` | Limite de movimentacoes por produto (default: 100) | `--limit-entradas 20` |

**Opcao --completo retorna:**
- Estoque atual e menor estoque nos proximos 7 dias
- Separacoes por data de expedicao (detalhado com pedidos)
- Demanda total (Carteira bruta/liquida + Separacoes)
- Programacao de producao (proximos 14 dias)
- Projecao dia a dia (estoque projetado)
- Indicadores: sobra, cobertura em dias, % disponivel, previsao de ruptura

---

### 4. calculando_leadtime_entrega.py

**Proposito:** Calcula data de entrega OU data de expedicao sugerida (calculo reverso).

**Queries cobertas:** Q7 + CALCULO REVERSO

```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate && \
python .claude/skills/gerindo-expedicao/scripts/calculando_leadtime_entrega.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--pedido` | Numero do pedido ou termo de busca | `--pedido VCD123`, `--pedido "atacadao 183"` |
| `--cidade` | Cidade de destino (alternativa ao pedido) | `--cidade "Sao Paulo"` |
| `--uf` | UF de destino (requerido se usar --cidade) | `--uf SP` |
| `--data-embarque` | Data de embarque (calcula data de entrega) | `--data-embarque amanha` |
| `--data-entrega` | ⭐ **NOVO** Data de entrega desejada (calcula data de embarque) | `--data-entrega 25/12` |
| `--limit` | Limite de opcoes de transportadora (default: 10) | `--limit 3` |

**Modos de operacao:**

| Modo | Parametro | Descricao |
|------|-----------|-----------|
| Previsao de entrega | `--data-embarque` | Se embarcar dia X, quando chega? |
| Sugestao de embarque | `--data-entrega` | Para chegar dia Y, quando embarcar? |
| Auto (usa pedido) | Apenas `--pedido` | Usa data_entrega_pedido para calculo reverso |

---

### 5. criando_separacao_pedidos.py

**Proposito:** Cria separacoes de pedidos via linguagem natural.

**IMPORTANTE:** Sempre executar primeiro SEM `--executar` para simular!

```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate && \
python .claude/skills/gerindo-expedicao/scripts/criando_separacao_pedidos.py [parametros]
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

---

### 6. consultando_programacao_producao.py

**Proposito:** Lista programacao de producao e simula alteracoes para resolver ruptura.

**Queries cobertas:** Q15 + LISTAGEM COMPLETA

```bash
source $([ -d venv ] && echo venv || echo .venv)/bin/activate && \
python .claude/skills/gerindo-expedicao/scripts/consultando_programacao_producao.py [parametros]
```

| Parametro | Descricao | Exemplo |
|-----------|-----------|---------|
| `--listar` | ⭐ **NOVO** Lista TODA a programacao de producao | flag |
| `--dias` | Horizonte em dias (default: 14) | `--dias 7` |
| `--por-dia` | Mostrar detalhes agrupados por dia | flag |
| `--por-linha` | Mostrar detalhes agrupados por linha | flag |
| `--linha` | Filtrar por linha de producao | `--linha "Linha A"` |
| `--produto` | Produto em ruptura (para reprogramacao) | `--produto "VF pouch 150"` |

**Modos de operacao:**

| Modo | Parametro | Descricao |
|------|-----------|-----------|
| Listagem | `--listar` | Toda a programacao dos proximos N dias |
| Reprogramacao | `--produto` | Opcoes para resolver ruptura |

**Exemplo de listagem completa:**
```bash
python .claude/skills/gerindo-expedicao/scripts/consultando_programacao_producao.py --listar --dias 7 --por-dia
```

---

### 7. resolver_entidades.py

**Proposito:** Modulo utilitario para resolver entidades do dominio.

**Uso interno pelos outros scripts.** Resolve:
- Pedidos por numero parcial ou termo
- Produtos por nome ou abreviacoes
- Grupos empresariais por nome
- Cidades por nome (normalizado)

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

## Nivel de Detalhes (Progressive Disclosure)

1. **Resposta inicial**: Resumo com 3-5 itens principais
2. **Se pedir mais**: Mostrar mais itens do mesmo JSON
3. **Se pedir "todos"**: Lista completa

---

## Grupos Empresariais

| Grupo | Prefixos CNPJ | Comando |
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

## Referencias

- [reference.md](reference.md) - Documentacao tecnica (tabelas, campos)
- [examples.md](examples.md) - Exemplos de perguntas e comandos
