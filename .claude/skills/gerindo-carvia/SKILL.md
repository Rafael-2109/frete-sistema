---
name: gerindo-carvia
description: >-
  Operacoes, subcontratos, cotacao e faturas do modulo CarVia (frete
  subcontratado). Gatilhos: "operacoes da CarVia", "subcontratos pendentes",
  "faturas CarVia do Atacadao", "cotar frete p/ SP via Braspress", "resumo
  CarVia". Anti: cotacao frete Nacom -> cotando-frete; doc SSW -> acessando-ssw;
  embarque/separacao Nacom -> gerindo-expedicao.
allowed-tools: Read, Bash, Glob, Grep
---

# Gerindo CarVia

Skill para consultas e operacoes do modulo CarVia (frete subcontratado).

---

## Quando Usar Esta Skill

USE para:
- Consulta de operacoes: "operacoes CarVia por status", "operacoes do cliente X"
- Consulta de subcontratos: "subcontratos pendentes", "subcontratos da Braspress"
- Cotacao subcontratada: "cotar frete para SP via transportadora Y"
- Consulta de faturas: "faturas cliente pendentes", "faturas transportadora em conferencia"
- Resumo geral: "como esta a CarVia?", "dashboard CarVia"

NAO USE para:
- Cotacao frete Nacom (industria, outbound) — use `cotando-frete`
- Documentacao/processos SSW — use `acessando-ssw`
- Criar embarque ou separacao Nacom — use `gerindo-expedicao`

---

## REGRAS CRITICAS (NUNCA VIOLAR)

### 1. GUARDRAIL ANTI-ALUCINACAO
**PROIBIDO** criar, calcular ou inferir dados que NAO foram retornados pelo script.
Se precisar de dado que nao veio no script: EXECUTE o script com flag adequado ou PERGUNTE ao usuario.

Exemplos de violacao:
- Inventar percentuais, tendencias ou comparativos nao presentes no JSON
- Supor causa para dados vazios ("provavelmente nao ha operacoes porque...")
- Fabricar nomes de transportadoras ou valores de cotacao

### 2. FIDELIDADE AO OUTPUT DO SCRIPT
Scripts retornam JSON estruturado. Sua resposta DEVE:
- Usar EXATAMENTE os valores dos campos retornados (nao arredondar, nao converter)
- Quando o script retorna `conferencia.diferenca_vs_cotado`, usar ESSE valor — NAO recalcular manualmente
- Apresentar valores monetarios como R$ com formatacao brasileira (1.234,56)
- Citar o campo do JSON quando houver duvida (ex: "campo `valor_cotado`")

### 3. REGRA DE FALLBACK (NUNCA TRAVAR)
Se um script falhar: SEMPRE responda ao usuario com erro e alternativa.
**NUNCA:** Ficar em silencio, travar, ou tentar criar scripts customizados.

### 4. RESULTADOS VAZIOS
Quando um script retorna `total: 0` ou `sucesso: false`:
- Reportar claramente: "Nenhum resultado encontrado para [filtro]"
- NAO inventar explicacoes para a ausencia de dados
- Sugerir ajustar filtros (status diferente, nome parcial, sem filtro)
- Se `sucesso: false`, mostrar o campo `erro` ao usuario

### 5. DOMINIO CARVIA vs NACOM
CarVia = transportadora que SUBCONTRATA frete (inbound).
Nacom = industria que CONTRATA frete (outbound).
Se o usuario perguntar sobre frete de embarque/pedido VCD: use `cotando-frete`.
Se o usuario perguntar sobre subcontrato/operacao CarVia: use ESTA skill.

**Dica de deteccao**: Se a pergunta menciona peso/cidade SEM operacao_id/subcontrato = provavelmente Nacom (outbound).
Se menciona operacao, subcontrato, fatura transportadora CarVia = ESTA skill.

### 6. CENARIOS COMPOSTOS
Quando o usuario pede "resumo geral" ou "como esta a CarVia?":
- Execute `--resumo` para visao geral
- Se houver subcontratos PENDENTES/COTADOS no resumo, execute tambem `--subcontratos-pendentes`
- Apresente ambos em sequencia: primeiro o panorama, depois os itens que precisam de acao

### 7. CONFERENCIA — GOTCHAS
Ao apresentar dados de conferencia (`--conferencia`):
- `percentual_diferenca_cotado` pode ser `null` quando `soma_valor_cotado = 0` — reportar como "N/A (sem cotacoes)"
- `diferenca_vs_cotado` positiva = fatura MAIOR que soma cotada. Negativa = fatura MENOR
- Campo correto do modelo e `status_conferencia` (NAO `status`) — CarviaFaturaTransportadora
- NAO recalcular diferencas/percentuais: usar EXATAMENTE os valores do JSON retornado

### 8. STATUS DE OPERACOES
Valores validos para `--status`: RASCUNHO, COTADO, CONFIRMADO, FATURADO, CANCELADO
- Fluxo normal: RASCUNHO → COTADO → CONFIRMADO → FATURADO
- Cancelar: qualquer status exceto FATURADO

### 9. ESCRITA EM carvia_fretes — dry-run obrigatorio
`atualizando_frete_carvia.py` e o UNICO script de ESCRITA desta skill. Persiste
valores JA CALCULADOS (`valor_cotado`, `valor_considerado`, `valor_pago`,
`valor_venda`, `tabela_nome_tabela`, `tabela_valor_kg`) em UM frete.
- **dry-run e o DEFAULT**: sem `--confirmar` o script so mostra antes/depois e
  faz rollback. SEMPRE rode o dry-run, mostre o antes/depois ao usuario e so
  rode com `--confirmar` apos confirmacao explicita.
- **NAO calcula frete**: o valor (peso cubado × tabela) vem de
  `cotando_subcontrato_carvia.py`. Fluxo: cotar → pegar `valor_cotado` →
  persistir. Nunca invente o valor (Regra 1).
- **Gotcha UI lancar-cte** (IMP-2026-06-24-004): a tela
  `/carvia/fretes/lancar-cte` exibe **V.Cotado** vindo de
  `carvia_fretes.valor_cotado`, mas o campo **NAO e editavel na UI** quando nao
  ha CTe vinculado. Antecipe isso: para corrigir um frete com tabela "0" /
  `valor_cotado=0`, oriente direto para este script — NAO mande o usuario tentar
  editar na tela.
- `requer_aprovacao` e recalculado (regra |considerado−cotado|>R$5 ou
  |considerado−pago|>R$5) e reportado em `requer_aprovacao.motivos`; o script
  NAO auto-aprova.

---

## DECISION TREE - Qual Script Usar?

### Mapeamento Rapido

| Se a pergunta menciona... | Use este script | Com estes parametros |
|---------------------------|-----------------|----------------------|
| **Resumo CarVia** ("como esta?") | `consultando_operacoes_carvia.py` | `--resumo` |
| **Operacoes por status** | `consultando_operacoes_carvia.py` | `--status RASCUNHO` |
| **Operacoes de cliente** | `consultando_operacoes_carvia.py` | `--cliente "Atacadao"` |
| **Operacao por ID** | `consultando_operacoes_carvia.py` | `--operacao 123` |
| **Subcontratos por transportadora** | `consultando_operacoes_carvia.py` | `--transportadora "Braspress"` |
| **Subcontratos pendentes** | `consultando_operacoes_carvia.py` | `--subcontratos-pendentes` |
| **Faturas cliente** | `consultando_faturas_carvia.py` | `--tipo cliente` |
| **Faturas transportadora** | `consultando_faturas_carvia.py` | `--tipo transportadora` |
| **Fatura por numero** | `consultando_faturas_carvia.py` | `--numero "FAT-001"` |
| **Faturas pendentes** | `consultando_faturas_carvia.py` | `--tipo cliente --status PENDENTE` |
| **Conferencia fatura** | `consultando_faturas_carvia.py` | `--tipo transportadora --conferencia` |
| **Cotar subcontrato** | `cotando_subcontrato_carvia.py` | `--operacao 123 --transportadora "Braspress"` |
| **Opcoes de transportadora** | `cotando_subcontrato_carvia.py` | `--operacao 123 --listar-opcoes` |
| **Ranking todas transportadoras** | `cotando_subcontrato_carvia.py` | `--operacao 123 --todas` |
| **Detalhe de fatura especifica** | `consultando_faturas_carvia.py` | `--fatura 456` |
| **Atualizar valor de frete** (WRITE; tabela "0"/valor_cotado=0) | `atualizando_frete_carvia.py` | `--frete-id 810 --valor-cotado 226.33 --tabela-nome "9-"` (add `--confirmar` p/ efetivar) |

### Regras de Decisao

1. **OPERACOES/SUBCONTRATOS:** → `consultando_operacoes_carvia.py`
2. **FATURAS (cliente ou transportadora):** → `consultando_faturas_carvia.py`
3. **COTACAO subcontratada:** → `cotando_subcontrato_carvia.py`
4. **DUVIDA entre cotacao Nacom vs CarVia:** → Perguntar ao usuario qual dominio

---

## Scripts — Referencia Detalhada

| # | Script | Proposito |
|---|--------|-----------|
| 1 | `consultando_operacoes_carvia.py` | Operacoes, subcontratos, resumo |
| 2 | `consultando_faturas_carvia.py` | Faturas cliente e transportadora |
| 3 | `cotando_subcontrato_carvia.py` | Cotacao de frete para subcontrato |
| 4 | `atualizando_frete_carvia.py` | **WRITE** — atualiza valor_cotado/considerado/tabela de UM frete (dry-run default, `--confirmar` efetiva) |

---

## Referencia Cruzada

| Skill | Quando usar em vez desta |
|-------|--------------------------|
| **cotando-frete** | Cotacao frete Nacom (industria, outbound) |
| **acessando-ssw** | Documentacao/processos SSW |
| **gerindo-expedicao** | Pedidos, separacao, embarque Nacom |
| **monitorando-entregas** | Status entrega pos-faturamento Nacom |
| **consultando-sql** | Consultas analiticas SQL avancadas |

---

## Tabelas do Dominio

| Tabela | Usada por |
|--------|-----------|
| `carvia_operacoes` | consultando_operacoes_carvia.py |
| `carvia_subcontratos` | consultando_operacoes_carvia.py |
| `carvia_nfs` | consultando_operacoes_carvia.py |
| `carvia_operacao_nfs` | consultando_operacoes_carvia.py |
| `carvia_faturas_cliente` | consultando_faturas_carvia.py |
| `carvia_faturas_transportadora` | consultando_faturas_carvia.py |
| `transportadoras` | cotando_subcontrato_carvia.py |
| `tabelas_frete` | cotando_subcontrato_carvia.py |
| `carvia_fretes` | atualizando_frete_carvia.py (WRITE) |

---

## Leitura de References (Sob Demanda)

| Gatilho na Pergunta | Reference a Ler |
|---------------------|-----------------|
| Termos CarVia (subcontrato, cubagem) | `app/carvia/CLAUDE.md` |
| Como funciona o calculo de frete | `cotando-frete/references/calculo_frete.md` |
| Status e fluxos de operacao | `app/carvia/CLAUDE.md` secao R4 |
