---
name: gerindo-carvia
description: >-
  Esta skill deve ser usada quando o usuario pergunta sobre operacoes CarVia
  (frete subcontratado): "operacoes da CarVia", "subcontratos pendentes",
  "faturas CarVia do Atacadao", "cotar frete subcontratado para SP",
  "conferencia de fatura transportadora", "resumo CarVia", ou qualquer
  consulta de operacoes, subcontratos, cotacao e faturas do modulo CarVia.
  Nao usar para cotacao de frete Nacom (industria embarca = usar cotando-frete),
  documentacao/processos SSW (usar acessando-ssw), ou criar embarque Nacom
  (usar gerindo-expedicao).
  - Resumo: "como esta a CarVia?", "resumo das operacoes"
  - Cotacao subcontratada: "cotar frete para SP via Braspress"
  - Faturas: "faturas pendentes", "conferencia da fatura X"

  NAO USAR QUANDO:
  - Cotacao frete Nacom (industria, outbound) -> usar **cotando-frete**
  - Documentacao SSW CarVia -> usar **acessando-ssw**
  - Status entrega pos-faturamento Nacom -> usar **monitorando-entregas**
  - Criar embarque/separacao Nacom -> usar **gerindo-expedicao**
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

### 2. REGRA DE FALLBACK (NUNCA TRAVAR)
Se um script falhar: SEMPRE responda ao usuario com erro e alternativa.
**NUNCA:** Ficar em silencio, travar, ou tentar criar scripts customizados.

### 3. DOMINIO CARVIA vs NACOM
CarVia = transportadora que SUBCONTRATA frete (inbound).
Nacom = industria que CONTRATA frete (outbound).
Se o usuario perguntar sobre frete de embarque/pedido VCD: use `cotando-frete`.
Se o usuario perguntar sobre subcontrato/operacao CarVia: use ESTA skill.

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

---

## Leitura de References (Sob Demanda)

| Gatilho na Pergunta | Reference a Ler |
|---------------------|-----------------|
| Termos CarVia (subcontrato, cubagem) | `app/carvia/CLAUDE.md` |
| Como funciona o calculo de frete | `cotando-frete/references/calculo_frete.md` |
| Status e fluxos de operacao | `app/carvia/CLAUDE.md` secao R4 |
