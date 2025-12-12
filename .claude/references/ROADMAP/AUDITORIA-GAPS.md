# AUDITORIA DE GAPS - Aplicacao de Referencias

**Data**: 12/12/2025
**Responsavel**: Claude
**Status**: ✅ CONCLUIDO (gaps A-D resolvidos, F pendente para tema 02)

---

## Resumo Executivo

Apos revisao de todas as referencias em 00-referencias.md, foram identificados **6 GAPS** que precisam ser corrigidos antes de prosseguir.

| Gap | Prioridade | Impacto | Status |
|-----|------------|---------|--------|
| GAP-A | CRITICO | Agente nao raciocina antes de escolher | ✅ RESOLVIDO |
| GAP-B | CRITICO | SKILL.md sem TOC (434 linhas) | ✅ RESOLVIDO |
| GAP-C | IMPORTANTE | Poucos exemplos (so 2 scripts) | ✅ RESOLVIDO |
| GAP-D | IMPORTANTE | Sem glossario de sinonimos | ✅ RESOLVIDO |
| GAP-E | MODERADO | 12 opcoes no mapeamento | DESCARTADO |
| GAP-F | IMPORTANTE | Termos ambiguos incompletos | PENDENTE (tema 02) |

---

## GAP-A: Falta Instrucao de Raciocinio (scratchpad)

**Referencia**: METAPROMPT.md - "Monologo Interno"

**Problema**: O agente escolhe o script diretamente sem mostrar seu raciocinio, o que dificulta depuracao de erros.

**Solucao**: Adicionar instrucao para usar raciocinio estruturado ANTES de escolher script.

**Conteudo proposto**:
```markdown
### Como Decidir (Raciocinio Obrigatorio)

<instrucao_raciocinio>
ANTES de escolher qualquer script, faca este raciocinio mentalmente:

1. **IDENTIFICAR** - O que o usuario quer saber?
   - E sobre PEDIDOS? (quem, quanto, quando)
   - E sobre ESTOQUE? (tem, vai faltar, chegou)
   - E sobre DISPONIBILIDADE? (quando fica pronto)
   - E uma ACAO? (criar separacao)

2. **VERIFICAR** - Tem cliente/grupo mencionado?
   - SIM + produto → consultando_situacao_pedidos --grupo/--cliente + --produto
   - SIM sem produto → consultando_situacao_pedidos --grupo/--cliente
   - NAO → provavelmente consultando_produtos_estoque

3. **CONFIRMAR** - A escolha faz sentido?
   - Se escolhi estoque mas usuario perguntou "pro atacadao" → ERRADO
   - Se escolhi pedidos mas usuario perguntou "quanto tem em estoque" → ERRADO

4. **PERGUNTAR** - Se ainda em duvida, pergunte ao usuario!
</instrucao_raciocinio>
```

**Local de insercao**: Apos linha 84 (fechamento de `</regras_decisao>`)

---

## GAP-B: SKILL.md sem TOC (Table of Contents)

**Referencia**: Skill best practices - "Structure longer reference files with TOC"

> "For reference files longer than 100 lines, include a table of contents at the top."

**Problema**: SKILL.md tem 434 linhas e nao possui indice navegavel.

**Solucao**: Adicionar TOC apos o frontmatter.

**Conteudo proposto**:
```markdown
## Indice

1. [Quando Usar Esta Skill](#quando-usar-esta-skill)
2. [DECISION TREE - Qual Script Usar?](#decision-tree---qual-script-usar)
   - [Mapeamento Rapido](#mapeamento-rapido)
   - [Regras de Decisao](#regras-de-decisao-em-ordem-de-prioridade)
   - [Como Decidir (Raciocinio)](#como-decidir-raciocinio-obrigatorio)
   - [Termos Ambiguos](#termos-ambiguos---pergunte-antes-de-agir)
   - [Exemplos](#exemplos-de-boas-e-mas-escolhas)
3. [Scripts Disponiveis](#scripts-disponiveis)
   - [1. analisando_disponibilidade_estoque.py](#1-analisando_disponibilidade_estoquepy)
   - [2. consultando_situacao_pedidos.py](#2-consultando_situacao_pedidospy)
   - [3. consultando_produtos_estoque.py](#3-consultando_produtos_estoquepy)
   - [4. calculando_leadtime_entrega.py](#4-calculando_leadtime_entregapy)
   - [5. criando_separacao_pedidos.py](#5-criando_separacao_pedidospy)
   - [6. consultando_programacao_producao.py](#6-consultando_programacao_producaopy)
4. [Fluxo de Criacao de Separacao](#fluxo-de-criacao-de-separacao)
5. [Grupos Empresariais](#grupos-empresariais)
6. [Resolucao de Produtos](#resolucao-de-produtos)
7. [Referencias](#referencias)

---
```

**Local de insercao**: Apos linha 9 (descricao inicial)

---

## GAP-C: Poucos Exemplos (so 2 scripts cobertos)

**Referencia**: METAPROMPT.md - "Inclua exemplos de boas e mas respostas"

**Problema**: Apenas `consultando_situacao_pedidos` e `consultando_produtos_estoque` tem exemplos. Faltam exemplos para:
- analisando_disponibilidade_estoque
- calculando_leadtime_entrega
- criando_separacao_pedidos
- consultando_programacao_producao

**Solucao**: Adicionar pelo menos 1 par de exemplo (bom/ruim) para cada script.

**Conteudo proposto**:

### Exemplo para analisando_disponibilidade_estoque:
```markdown
<exemplo_bom>
Pergunta: "quando o pedido VCD123 fica disponivel?"
Escolha: analisando_disponibilidade_estoque.py --pedido VCD123
Motivo: Pergunta sobre DISPONIBILIDADE de pedido especifico.
</exemplo_bom>

<exemplo_ruim>
Pergunta: "quando o pedido VCD123 fica disponivel?"
Escolha ERRADA: consultando_situacao_pedidos.py --pedido VCD123 --status
Problema: Mostra status atual, NAO projeta quando fica disponivel.
</exemplo_ruim>
```

### Exemplo para calculando_leadtime_entrega:
```markdown
<exemplo_bom>
Pergunta: "se embarcar amanha, quando chega em Manaus?"
Escolha: calculando_leadtime_entrega.py --pedido X --data-embarque amanha
Motivo: Calculo de prazo de entrega com data de embarque.
</exemplo_bom>

<exemplo_ruim>
Pergunta: "se embarcar amanha, quando chega em Manaus?"
Escolha ERRADA: analisando_disponibilidade_estoque.py --pedido X
Problema: Analisa disponibilidade de estoque, NAO calcula prazo de transporte.
</exemplo_ruim>
```

### Exemplo para criando_separacao_pedidos:
```markdown
<exemplo_bom>
Pergunta: "crie separacao do VCD123 pra segunda"
Escolha: criando_separacao_pedidos.py --pedido VCD123 --expedicao segunda
Motivo: ACAO de criar separacao com data informada. SEMPRE simular primeiro (sem --executar).
</exemplo_bom>

<exemplo_ruim>
Pergunta: "crie separacao do VCD123 pra segunda"
Escolha ERRADA: criando_separacao_pedidos.py --pedido VCD123 --expedicao segunda --executar
Problema: NUNCA usar --executar sem simular primeiro e confirmar com usuario.
</exemplo_ruim>
```

### Exemplo para consultando_programacao_producao:
```markdown
<exemplo_bom>
Pergunta: "o que vai ser produzido essa semana?"
Escolha: consultando_programacao_producao.py --listar --dias 7 --por-dia
Motivo: Consulta de programacao de producao com agrupamento.
</exemplo_bom>

<exemplo_ruim>
Pergunta: "o que vai ser produzido essa semana?"
Escolha ERRADA: consultando_produtos_estoque.py --entradas
Problema: Mostra entradas de estoque (producao JA realizada), NAO programacao futura.
</exemplo_ruim>
```

**Local de insercao**: Apos linha 124 (exemplo_ruim existente)

---

## GAP-D: Falta Glossario de Sinonimos

**Referencia**: Skill best practices - "Use consistent terminology"

> "Use consistent terminology. Choose one term and use it throughout the Skill."

**Problema**: Nao ha mapeamento de sinonimos que o usuario pode usar.

**Solucao**: Criar secao de sinonimos aceitos.

**Conteudo proposto**:
```markdown
## Glossario de Sinonimos

<glossario>
O usuario pode usar diversos termos para a mesma coisa. Normalize antes de processar:

| Termo Usuario | Termo Padrao | Significado |
|---------------|--------------|-------------|
| ketchup, catchup, ketichap | ketchup | Produto ketchup |
| caixa, cx, unidade, un | unidade | Quantidade de produto |
| loja, filial, unidade | loja | Filial do cliente |
| embarque, despacho, saida | expedicao | Data de envio |
| chegada, recebimento | agendamento | Data de entrega |
| pedido, PV, OV, venda | pedido | Ordem de venda |
| cliente, comprador, destinatario | cliente | Quem compra |
| transportadora, frete, carrier | transportadora | Empresa de transporte |
| estoque, saldo, disponivel | estoque | Quantidade em armazem |
| falta, ruptura, stockout | ruptura | Estoque insuficiente |
| separacao, picking, sep | separacao | Preparacao de pedido |
</glossario>
```

**Local de insercao**: Antes de "Grupos Empresariais" (linha 385)

---

## GAP-E: 12 Opcoes no Mapeamento Rapido

**Referencia**: Skill best practices - "Avoid offering too many options"

**Problema**: 12 linhas no mapeamento pode ser demais para decisao rapida.

**Analise**:
- Opcoes estao agrupadas por script (nao sao 12 scripts, sao 6)
- Cada script tem ~2 casos de uso
- Pode ser aceitavel

**Decisao**: MANTER como esta, pois o agrupamento por script ja ajuda.

**Status**: DESCARTADO (nao e gap real)

---

## GAP-F: Termos Ambiguos Incompletos

**Referencia**: 02-termos-ambiguos.md - Conteudo completo

**Problema**: A secao `<termos_ambiguos>` no SKILL.md tem 5 termos, mas o documento 02-termos-ambiguos.md tem mais detalhes:

| Termo | No SKILL.md? | Completo? |
|-------|--------------|-----------|
| "programacao de entrega" | ✅ | ⚠️ Falta opcoes A/B/C/D |
| "quantidade pendente" | ✅ | ❌ Falta acao padrao |
| "pedidos do grupo" (multiplas lojas) | ❌ | ❌ NAO EXISTE |
| "itens" vs "unidades" | ❌ | ❌ NAO EXISTE |
| "quando fica disponivel" | ✅ | ✅ OK |
| "situacao" | ✅ | ✅ OK |
| "crie separacao" | ✅ | ✅ OK |

**Solucao**: Expandir secao de termos ambiguos com conteudo completo de 02-termos-ambiguos.md.

---

## Ordem de Implementacao

1. **GAP-B**: Adicionar TOC (rapido, impacto visual imediato)
2. **GAP-A**: Adicionar instrucao de raciocinio (critico para qualidade)
3. **GAP-C**: Adicionar mais exemplos (melhora entendimento)
4. **GAP-D**: Adicionar glossario de sinonimos (padronizacao)
5. **GAP-F**: Expandir termos ambiguos (sera feito no tema 02)

---

## Checklist de Validacao

Antes de marcar 01-decision-tree como DEFINITIVAMENTE concluido:

- [x] TOC adicionado no inicio do SKILL.md (linhas 13-33)
- [x] Instrucao de raciocinio (scratchpad) adicionada (linhas 112-135)
- [x] Exemplos para todos os 6 scripts (8 pares bom/ruim, linhas 157-225)
- [x] Glossario de sinonimos adicionado (linhas 486-507)

---

## Implementacoes Realizadas

### GAP-A: Instrucao de Raciocinio
- **Arquivo**: SKILL.md
- **Local**: Apos `</regras_decisao>`, secao "Como Decidir (Raciocinio Obrigatorio)"
- **Conteudo**: 4 passos (IDENTIFICAR, VERIFICAR, CONFIRMAR, PERGUNTAR)
- **Tag XML**: `<instrucao_raciocinio>`

### GAP-B: Table of Contents
- **Arquivo**: SKILL.md
- **Local**: Apos descricao inicial
- **Conteudo**: 8 secoes com links navegaveis

### GAP-C: Exemplos Adicionais
- **Arquivo**: SKILL.md
- **Local**: Secao "Exemplos de Boas e Mas Escolhas"
- **Conteudo**: 4 novos pares (analisando_disponibilidade, calculando_leadtime, criando_separacao, consultando_programacao)
- **Total**: 8 pares exemplo_bom/exemplo_ruim

### GAP-D: Glossario de Sinonimos
- **Arquivo**: SKILL.md
- **Local**: Nova secao antes de "Grupos Empresariais"
- **Conteudo**: 12 termos mapeados
- **Tag XML**: `<glossario>`

---

## Historico

| Data | Alteracao | Autor |
|------|-----------|-------|
| 12/12/2025 | Criacao do documento de auditoria | Claude |
| 12/12/2025 | Implementacao GAP-A, GAP-B, GAP-C, GAP-D | Claude |
| 12/12/2025 | Checklist atualizado - 01-decision-tree COMPLETO | Claude |
