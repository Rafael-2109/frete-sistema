# Routing de Skills

**Ultima Atualizacao**: 08/02/2026

**REGRA**: Use a skill MAIS ESPECIFICA. `descobrindo-odoo-estrutura` e ULTIMO RECURSO.

---

## Passo 1: Identificar o CONTEXTO

| Contexto | Sinais | Proximo passo |
|----------|--------|---------------|
| CONSULTA LOCAL (CarteiraPrincipal, Separacao, etc.) | Campos locais, queries SQL, regras de negocio | -> Consultar REFERENCES (sem skill) |
| CONSULTA ANALITICA (agregacoes, rankings, distribuicoes) | "quantos por estado", "top 10", "valor total por", comparacoes | -> `consultando-sql` |
| OPERACAO ODOO (API, modelos, integracoes) | NF, PO, picking, Odoo, pagamento, extrato | -> Passos 2 e 3 abaixo |
| DESENVOLVIMENTO FRONTEND | Criar tela, dashboard, CSS, template | -> `frontend-design` |
| COTACAO DE FRETE | "qual preco", "quanto custa frete", "tabelas para", "cotacao" | -> `cotando-frete` |
| VISAO 360 PRODUTO | "resumo do produto", "producao vs programado", "visao completa do produto" | -> `visao-produto` |
| EXPORTAR/IMPORTAR DADOS | Gerar Excel, CSV, processar planilha | -> `exportando-arquivos` / `lendo-arquivos` |

---

## Passo 2 (ODOO): Tem dado ESTATICO ja documentado?

| Preciso de... | Nao use skill, consulte diretamente: |
|---------------|--------------------------------------|
| ID fixo (company, picking_type, journal) | `.claude/references/odoo/IDS_FIXOS.md` |
| Conversao UoM (Milhar, fator_un) | `.claude/references/odoo/CONVERSAO_UOM.md` |
| Campos ja mapeados do Odoo | `.claude/references/odoo/MODELOS_CAMPOS.md` |
| GOTCHAS conhecidos (timeouts, erros) | `.claude/references/odoo/GOTCHAS.md` |

Se a resposta esta no reference -> NAO usar skill.

---

## Passo 3 (ODOO): Arvore de Decisao de Skills

```
0. CONFIGURACAO ESTATICA ja documentada?
   |-- SIM -> consultou no Passo 2, PARAR
   |-- NAO -> continuar abaixo

1. RECEBIMENTO de compra?
   |-- Match NF x PO           -> validacao-nf-po
   |-- Split/Consolidar PO     -> conciliando-odoo-po
   |-- Lotes/Quality Check     -> recebimento-fisico-odoo
   |-- Pipeline completo       -> ver odoo/PIPELINE_RECEBIMENTO.md

2. FINANCEIRO?
   |-- Criar pagamento / reconciliar extrato -> executando-odoo-financeiro
   |-- Exportar razao geral                  -> razao-geral-odoo

3. DESENVOLVIMENTO de nova integracao?
   |-- Criar service/route/migration -> integracao-odoo

4. RASTREAMENTO de documento?
   |-- Rastrear NF, PO, SO, pagamento -> rastreando-odoo

5. ESTRUTURA desconhecida (ULTIMO RECURSO)?
   |-- Descobrir campos de modelo NOVO -> descobrindo-odoo-estrutura
```

---

## Desambiguacao (quando 2 skills parecem servir)

| Duvida entre... | Regra de desempate |
|-----------------|-------------------|
| rastreando vs executando-financeiro | READ/consultar -> rastreando. WRITE/criar/modificar -> executando |
| rastreando vs validacao-nf-po | Fluxo completo -> rastreando. Apenas Fase 2 match -> validacao |
| conciliando vs validacao-nf-po | Fase 3 (split/consolidar) -> conciliando. Fase 2 (match) -> validacao |
| integracao vs descobrindo | CRIAR novo service -> integracao. EXPLORAR modelo -> descobrindo |
| Nao sei qual skill Odoo usar | -> Subagente `especialista-odoo` (orquestra todas) |

---

## Skills — Inventario Completo (22 total)

Cada skill tem `SKILL.md` em `.claude/skills/<nome>/`.

### MCP Custom Tools (agente web, in-process)
`mcp__sql__consultar_sql`, `mcp__memory__*` (6 tools), `mcp__schema__*` (2 tools),
`mcp__sessions__*` (2 tools), `mcp__render__*` (3 tools: logs, erros, status)

### Skills Odoo (Claude Code)
`rastreando-odoo`, `executando-odoo-financeiro`, `descobrindo-odoo-estrutura`,
`integracao-odoo`, `validacao-nf-po`, `conciliando-odoo-po`, `recebimento-fisico-odoo`, `razao-geral-odoo`

### Skills Dev (Claude Code)
`frontend-design`, `skill_creator`, `ralph-wiggum`, `prd-generator`

### Utilitarios (compartilhados)
`exportando-arquivos`, `lendo-arquivos`, `consultando-sql`, `cotando-frete`,
`visao-produto`, `resolvendo-entidades`, `gerindo-expedicao`, `monitorando-entregas`, `memoria-usuario`
