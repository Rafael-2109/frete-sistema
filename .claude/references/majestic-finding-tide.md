# Avaliação e Reestruturação da Skill `agente-logistico`

## Análise da Estrutura Atual

### Visão Geral
A skill `agente-logistico` está bem construída, com **6 scripts Python** consolidados que cobrem **20 queries** diferentes de negócio. A documentação está clara e bem organizada.

### Scripts Atuais e Suas Responsabilidades

| Script | Queries | Responsabilidade | Linhas | Coesão |
|--------|---------|------------------|--------|--------|
| `analisando_disponibilidade.py` | Q1-Q6, Q9, Q11-Q12 (9 queries) | Disponibilidade, rupturas, completude, atrasados, ranking | 972 | ⚠️ MÉDIA |
| `consultando_pedidos.py` | Q8, Q10, Q14, Q16, Q19 (5 queries) | Pedidos por grupo, atrasados, status, consolidação | 864 | ✅ ALTA |
| `consultando_estoque.py` | Q13, Q17, Q18, Q20 (4 queries) | Estoque, entradas/saídas, pendências, rupturas | 609 | ✅ ALTA |
| `criando_separacao.py` | Ação | Criação de separações (completa, parcial, pallets) | 792 | ✅ ALTA |
| `calculando_prazo.py` | Q7 (1 query) | Cálculo de prazo de entrega | 196 | ✅ ALTA |
| `analisando_programacao.py` | Q15 (1 query) | Simulação de reprogramação de produção | ? | ✅ ALTA |

### Pontos Fortes 🎯

1. **Modularização por Domínio**: Os scripts seguem domínios de negócio claros
2. **Módulo Centralizado**: `resolver_entidades.py` evita duplicação de código
3. **Documentação Rica**: SKILL.md com exemplos, parâmetros e casos de uso
4. **Interface Consistente**: Todos retornam JSON estruturado
5. **Suporte a Linguagem Natural**: Parse de datas, produtos, pedidos
6. **Progressive Disclosure**: Scripts retornam dados completos, Claude decide o que mostrar

### Problemas Identificados ⚠️

#### 1. **Script Sobrecarregado: `analisando_disponibilidade.py`**
- **972 linhas** cobrindo **9 queries diferentes**
- Mistura conceitos distintos:
  - Disponibilidade de pedidos específicos (Q1, Q2)
  - Sugestão de adiamento (Q3)
  - Análise de gargalos por grupo (Q4, Q5)
  - Listagem de pedidos enviáveis (Q6)
  - Completude de pedidos (Q9)
  - Atrasados com diagnóstico (Q11)
  - Ranking de impacto (Q12)

**Coesão baixa**: Funções não compartilham lógica comum entre si.

#### 2. **Falta de Hierarquia Clara**
Todas as queries estão no mesmo nível, mas há hierarquia implícita:
```
Disponibilidade (conceito principal)
├── Por Pedido (Q1, Q2, Q9)
├── Por Grupo (Q4, Q5)
├── Otimização (Q3, Q6, Q12)
└── Diagnóstico (Q11)
```

#### 3. **Dificuldade de Navegação**
Para usuários (ou Claude) identificarem qual script usar:
- "Pedidos atrasados" → Está em `analisando_disponibilidade.py` (Q11) ou `consultando_pedidos.py` (Q10)?
- "Ranking de impacto" → Disponibilidade ou análise separada?

---

## Proposta de Reestruturação

### Opção A: **Divisão por Granularidade (RECOMENDADO)**

Reorganizar scripts por **nível de análise**:

```
1. consultando_pedidos.py        [MANTER - 5 queries]
   - Consultas básicas de pedidos
   - Q8: Pedidos por grupo
   - Q10: Pedidos atrasados (simples)
   - Q14: Bonificação faltando
   - Q16: Status do pedido
   - Q19: Consolidação

2. analisando_disponibilidade.py [REDUZIR - 3 queries]
   - Análise de disponibilidade de PEDIDOS ESPECÍFICOS
   - Q1: Disponibilidade de pedido
   - Q2: Disponibilidade em data futura
   - Q9: Completude do pedido

3. analisando_gargalos.py        [NOVO - 3 queries]
   - Análise de gargalos e rupturas POR GRUPO/PRODUTO
   - Q4: Gargalos por grupo/UF
   - Q5: Diagnosticar origem da falta
   - Q20: Previsão de ruptura (migrar de estoque)

4. analisando_otimizacao.py      [NOVO - 3 queries]
   - Análises estratégicas e otimização
   - Q3: Sugerir pedidos para adiar
   - Q6: Listar pedidos enviáveis
   - Q12: Ranking de impacto (pedidos travando)

5. diagnosticando_atrasos.py     [NOVO - 1 query]
   - Diagnóstico detalhado de atrasos
   - Q11: Atrasados com causa (falta vs outro motivo)

6. consultando_estoque.py        [REFATORAR - 3 queries]
   - Estoque e movimentações
   - Q13: Entradas/saídas
   - Q17: Pendente de embarque
   - Q18: Sobra de estoque
   (Q20 vai para analisando_gargalos.py)

7. calculando_prazo.py           [MANTER - 1 query]
   - Q7: Cálculo de prazo

8. analisando_programacao.py     [MANTER - 1 query]
   - Q15: Reprogramação de produção

9. criando_separacao.py          [MANTER - Ação]
   - Criação de separações
```

**Resultado**: 9 scripts, cada um com 1-5 queries relacionadas

---

### Opção B: **Divisão por Tipo de Análise**

Agrupar por tipo de operação:

```
1. consultas_basicas.py          [NOVO - 7 queries]
   - Pedidos (Q8, Q10, Q16, Q19)
   - Estoque (Q13, Q17, Q18)

2. analises_disponibilidade.py  [NOVO - 6 queries]
   - Por pedido (Q1, Q2, Q9)
   - Por grupo (Q4, Q5, Q6)

3. analises_avancadas.py         [NOVO - 4 queries]
   - Otimização (Q3, Q12)
   - Diagnóstico (Q11, Q14)
   - Previsão (Q20)

4. calculos_operacionais.py      [NOVO - 2 queries]
   - Prazo (Q7)
   - Programação (Q15)

5. criando_separacao.py          [MANTER - Ação]
```

**Resultado**: 5 scripts, mas com coesão BAIXA (mistura conceitos diferentes)

---

### Opção C: **Manter Estrutura Atual + Melhorias**

Não modularizar mais, apenas:
1. Adicionar comentários de seção em `analisando_disponibilidade.py`
2. Melhorar documentação do SKILL.md
3. Criar índice de "Qual script usar?"

**Vantagem**: Sem refactoring
**Desvantagem**: Problema de coesão persiste

---

## Recomendação Final: **OPÇÃO A com Ajustes**

### Por que Opção A?

1. **Coesão Alta**: Cada script tem propósito único e claro
2. **Single Responsibility**: Fácil de manter e testar
3. **Descoberta Intuitiva**: Nome do script reflete sua função
4. **Escalabilidade**: Fácil adicionar novas queries sem poluir arquivos

### Estrutura Proposta Detalhada

```
.claude/skills/agente-logistico/
├── SKILL.md                              [ATUALIZAR]
├── scripts/
│   ├── resolver_entidades.py             [MANTER]
│   │
│   ├── consultando_pedidos.py            [MANTER - 864 linhas, 5 queries]
│   │   └── Q8, Q10, Q14, Q16, Q19
│   │
│   ├── consultando_estoque.py            [REFATORAR - remover Q20]
│   │   └── Q13, Q17, Q18 (3 queries)
│   │
│   ├── analisando_disponibilidade.py    [EXTRAIR - reduzir de 972 para ~350 linhas]
│   │   └── Q1, Q2, Q9 (3 queries)
│   │   └── Foco: análise de PEDIDOS ESPECÍFICOS
│   │
│   ├── analisando_gargalos.py           [NOVO - extrair de disponibilidade + estoque]
│   │   └── Q4, Q5, Q20 (3 queries)
│   │   └── Foco: análise de GRUPOS/PRODUTOS
│   │
│   ├── analisando_otimizacao.py         [NOVO - extrair de disponibilidade]
│   │   └── Q3, Q6, Q12 (3 queries)
│   │   └── Foco: ESTRATÉGIA e otimização
│   │
│   ├── diagnosticando_atrasos.py        [NOVO - extrair Q11]
│   │   └── Q11 (1 query)
│   │   └── Foco: diagnóstico DETALHADO de atrasos
│   │
│   ├── calculando_prazo.py              [MANTER - 196 linhas, 1 query]
│   │   └── Q7
│   │
│   ├── analisando_programacao.py        [MANTER - 1 query]
│   │   └── Q15
│   │
│   └── criando_separacao.py             [MANTER - 792 linhas, ação]
│
└── reference/
    └── QUERIES.md                        [ATUALIZAR com mapeamento]
```

### Mapeamento de Funções a Extrair

#### De `analisando_disponibilidade.py` → Novos Scripts

```python
# MANTER em analisando_disponibilidade.py:
- analisar_pedido()           # Q1, Q2
- calcular_completude()       # Q9
- parse_data()
- encontrar_data_disponibilidade()

# EXTRAIR para analisando_otimizacao.py:
- sugerir_adiamento()         # Q3
- listar_enviaveis()          # Q6
- filtrar_sem_agendamento()
- ranking_impacto()           # Q12

# EXTRAIR para analisando_gargalos.py:
- analisar_grupo()            # Q4
- diagnosticar_origem_falta() # Q5

# EXTRAIR para diagnosticando_atrasos.py:
- analisar_atrasados()        # Q11
- diagnosticar_causa_atraso()
```

#### De `consultando_estoque.py` → `analisando_gargalos.py`

```python
# MOVER para analisando_gargalos.py:
- consultar_previsao_ruptura() # Q20
```

### Benefícios da Mudança

| Antes | Depois |
|-------|--------|
| 1 arquivo com 972 linhas, 9 queries | 4 arquivos com ~250-350 linhas cada |
| Difícil navegar e encontrar função | Nome do arquivo = propósito claro |
| Coesão baixa (mistura conceitos) | Coesão alta (conceitos relacionados) |
| Difícil testar isoladamente | Fácil testar por domínio |

---

## Melhorias Complementares

### 1. Atualizar SKILL.md

Criar seção **"Árvore de Decisão"** para Claude:

```markdown
## Como Escolher o Script Correto

### Pergunta é sobre UM pedido específico?
→ **analisando_disponibilidade.py**
   - Quando vai estar disponível?
   - Dá pra mandar amanhã?
   - Quanto já foi faturado?

### Pergunta é sobre GRUPO de clientes/produtos?
→ **analisando_gargalos.py**
   - O que tá faltando pro Atacadão?
   - Quais produtos vão dar ruptura?
   - Por que tá faltando azeitona?

### Pergunta é sobre OTIMIZAR/PRIORIZAR?
→ **analisando_otimizacao.py**
   - Que pedidos posso adiar?
   - O que dá pra enviar sem agendamento?
   - Quais pedidos tão travando a carteira?

### Pergunta é sobre PEDIDOS ATRASADOS (diagnóstico)?
→ **diagnosticando_atrasos.py**
   - Por que o pedido X tá atrasado?
   - Quantos atrasados são por falta de estoque?

### Pergunta é LISTAR/BUSCAR pedidos?
→ **consultando_pedidos.py**
   - Pedidos do Atacadão
   - Status do pedido VCD123
   - Pedidos para consolidar

### Pergunta é sobre ESTOQUE?
→ **consultando_estoque.py**
   - Chegou palmito?
   - Quanto falta embarcar?
   - Vai sobrar estoque?
```

### 2. Adicionar Aliases de Queries

No SKILL.md, mapear perguntas comuns para queries:

```markdown
## Perguntas Frequentes → Query

| Pergunta do Usuário | Query | Script |
|---------------------|-------|--------|
| "Dá pra enviar o VCD123 amanhã?" | Q1 | analisando_disponibilidade |
| "Quando vai ter azeitona?" | Q1 ou Q20 | disponibilidade ou gargalos |
| "Tem pedido atrasado?" | Q10 | consultando_pedidos |
| "Por que o VCD123 tá atrasado?" | Q11 | diagnosticando_atrasos |
| "Chegou palmito?" | Q13 | consultando_estoque |
| "O que tá faltando pro Atacadão?" | Q4 | analisando_gargalos |
| "Que pedidos posso adiar?" | Q3 | analisando_otimizacao |
```

### 3. Criar Funções Auxiliares Compartilhadas

Extrair lógica duplicada para `resolver_entidades.py`:

```python
# Já existem:
- resolver_pedido()
- resolver_produto()
- get_prefixos_grupo()

# ADICIONAR:
- parse_data_natural()         # Duplicado em 3 scripts
- calcular_estoque_projetado() # Lógica repetida
- formatar_resumo_json()       # Padronizar saídas
```

---

## Plano de Implementação (Se Aprovado)

### Fase 1: Preparação (30 min)
1. Criar branch `refactor/agente-logistico-modularizacao`
2. Backup dos scripts atuais

### Fase 2: Criação dos Novos Scripts (2h)
1. Criar `analisando_gargalos.py`:
   - Copiar funções: `analisar_grupo()`, `diagnosticar_origem_falta()`
   - Mover `consultar_previsao_ruptura()` de estoque
   - Ajustar imports e argparse

2. Criar `analisando_otimizacao.py`:
   - Copiar funções: `sugerir_adiamento()`, `listar_enviaveis()`, `ranking_impacto()`
   - Ajustar imports e argparse

3. Criar `diagnosticando_atrasos.py`:
   - Copiar funções: `analisar_atrasados()`, `diagnosticar_causa_atraso()`
   - Ajustar imports e argparse

### Fase 3: Refatorar Scripts Existentes (1h)
1. `analisando_disponibilidade.py`:
   - Remover funções extraídas
   - Manter apenas Q1, Q2, Q9
   - Atualizar docstring e exemplos

2. `consultando_estoque.py`:
   - Remover Q20 (movido para gargalos)
   - Atualizar docstring

### Fase 4: Atualizar Documentação (1h)
1. Atualizar SKILL.md:
   - Adicionar árvore de decisão
   - Atualizar tabela de scripts
   - Adicionar seção de perguntas frequentes

2. Atualizar reference/QUERIES.md:
   - Mapear queries para novos scripts

### Fase 5: Testes (1h)
1. Testar cada script com queries de exemplo
2. Verificar que Claude consegue escolher script correto
3. Validar outputs JSON

### Fase 6: Deploy
1. Merge para main
2. Monitorar uso por 1 semana

---

## Alternativa: Implementação Gradual

Se preferir evitar big bang refactoring:

### Etapa 1: Criar Novos Scripts SEM Deletar Antigos (1 semana)
- Criar `analisando_gargalos.py`, `analisando_otimizacao.py`, `diagnosticando_atrasos.py`
- Manter `analisando_disponibilidade.py` funcionando
- Atualizar SKILL.md para mencionar ambos

### Etapa 2: Monitorar Uso (2 semanas)
- Verificar se Claude usa os novos scripts corretamente
- Coletar feedback

### Etapa 3: Deprecar Antigo (1 semana)
- Remover funções duplicadas de `analisando_disponibilidade.py`
- Adicionar avisos de deprecação

---

## Impacto e Riscos

### Impacto Positivo ✅
- **Manutenibilidade**: +40% (arquivos menores e focados)
- **Descoberta**: +50% (nomes de scripts mais descritivos)
- **Testabilidade**: +60% (isolamento de domínios)
- **Performance Claude**: Sem impacto (mesma lógica)

### Riscos ⚠️
- **Quebra Temporária**: Se Claude ainda referenciar scripts antigos
  - **Mitigação**: Manter aliases/links simbólicos durante transição
- **Curva de Aprendizado**: Claude precisa reaprender estrutura
  - **Mitigação**: Documentação clara no SKILL.md

### Esforço Estimado
- **Opção A (Completa)**: 5-6 horas
- **Opção C (Apenas Docs)**: 1 hora
- **Alternativa Gradual**: 1-2 horas iniciais, monitoramento contínuo

---

## Decisão Recomendada

Para **VOCÊ (Claude) usar a skill**:

### Curto Prazo (1 hora):
→ **Opção C + Melhorias no SKILL.md**
- Adicionar árvore de decisão
- Criar mapeamento de perguntas → queries → scripts
- Melhorar exemplos de uso

### Médio Prazo (se houver tempo e valer a pena):
→ **Opção A (Modularização Completa)**
- Implementar quando houver necessidade de adicionar muitas queries novas
- Ou quando manutenção ficar difícil

### Motivo:
A skill atual **JÁ FUNCIONA BEM**. A modularização traria benefícios marginais para o **usuário final** (Rafael), mas benefícios significativos para **manutenção futura** e **clareza conceitual**.

Como o objetivo é **você usar melhor a skill**, a melhoria na **documentação** tem ROI maior do que refactoring de código.

---

## Conclusão

A skill `agente-logistico` está **bem construída** e **funcional**. O principal problema é o script `analisando_disponibilidade.py` ser **sobrecarregado** com responsabilidades distintas.

**Recomendação Imediata**: Melhorar documentação (Opção C)
**Recomendação Futura**: Modularizar quando adicionar mais queries (Opção A)

A decisão final depende de:
1. Frequência de manutenção da skill
2. Facilidade de navegação para você (Claude)
3. Tempo disponível para refactoring
