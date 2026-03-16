# Routing de Skills

**Ultima Atualizacao**: 11/03/2026

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
| SAUDE DO BANCO | "health check", "indices nao usados", "queries lentas", "cache hit rate", "vacuum" | -> `diagnosticando-banco` |
| SSW consulta (sistema transportadora) | "como fazer no SSW", "opcao NNN", "passo a passo", "MDF-e", "CTe no SSW", "CarVia faz X?" | -> `acessando-ssw` |
| SSW escrita (cadastrar/criar no SSW) | "cadastre unidade CGR", "cadastrar cidades MS", "criar unidade parceira no SSW" | -> `operando-ssw` |
| PORTAL ATACADAO (automacao web Hodie Booking) | "portal Atacadao", "site do Atacadao", "Hodie Booking", "entrar no portal", "imprimir protocolo no site", "agendar no portal" + OBRIGATORIO mencionar portal/site/Hodie | -> `operando-portal-atacadao` |
| CARVIA (frete subcontratado) | "operacoes CarVia", "subcontratos pendentes", "cotar subcontrato", "faturas CarVia", "conferencia transportadora" | -> `gerindo-carvia` |
| SENTRY (erros, issues, monitoring) | "issues do Sentry", "erros em producao", "bugs no Sentry", "resolver issue", "root cause analysis", "500 errors", "Seer" | -> `consultando-sentry` |
| LOCALIZAR ROTA/TELA/API | "onde fica X?", "qual URL de Y?", "quais APIs de Z?", "como acesso tela de W?" | -> `buscando-rotas` |
| PROBLEMA COMPLEXO (investigacao, root cause) | "resolver problema complexo em...", "investigar bug em...", "por que X esta...", "analisar modulo completo", "mapear dependencias", "root cause analysis" | -> `resolvendo-problemas` |

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
   |-- Vincular/desvincular PO ↔ NF  -> conciliando-odoo-po
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
| Teams tasks vs diagnostico agente | **TeamsTask** (status task, stale cleanup) → `consultando-sql` direto. **Sessoes/memorias Teams** (filtro `--channel teams`, flags) → `gerindo-agente`. **Teams SSO** (config, webhook) → dev manual |
| cotando-frete vs acessando-ssw | **Nacom** (industria, contrata frete) -> cotando-frete. **CarVia** (transportadora, vende frete) -> acessando-ssw. Sinal: "no SSW", "opcao NNN", "CarVia" -> SSW. Sem qualificador -> Nacom. Sinais adicionais CarVia: "parametros de frete" (opcao 062), "resultado CTRC" (opcao 101), "formacao de preco" (opcao 062/004) |
| cotando-frete vs gerindo-carvia | **Nacom** (cotacao outbound, tabela de frete da Nacom) -> cotando-frete. **CarVia** (cotacao subcontrato inbound, operacao + transportadora) -> gerindo-carvia. Sinal: "subcontrato", "operacao CarVia", "frete subcontratado" -> gerindo-carvia. "frete para Manaus", "pedido VCD" -> cotando-frete |
| gerindo-carvia vs gerindo-expedicao | **CarVia** (frete subcontratado, operacao inbound) -> gerindo-carvia. **Nacom** (separacao, embarque outbound) -> gerindo-expedicao. Sinal: "subcontrato", "fatura CarVia" -> gerindo-carvia. "separacao", "pedido VCD" -> gerindo-expedicao |
| acessando-ssw vs operando-ssw | **Consultar/entender** SSW -> acessando-ssw. **Executar/cadastrar/criar** no SSW -> operando-ssw. Sinal: "cadastre", "crie unidade", "inclua cidade" -> operando. "como funciona", "o que e", "passo a passo" -> acessando |
| gerindo-expedicao vs acessando-ssw | Estoque/separacao/embarque **Nacom** -> gerindo-expedicao. Romaneio/manifesto **SSW** -> acessando-ssw |
| monitorando-entregas vs acessando-ssw | Entrega rastreada no **sistema local** -> monitorando-entregas. Baixa/ocorrencia no **SSW** -> acessando-ssw |
| operando-portal-atacadao vs gerindo-expedicao | **Portal web** do Atacadao (imprimir, agendar, consultar saldo no site) -> operando-portal-atacadao. **Dados locais** do Atacadao (pedidos, separacao, estoque) -> gerindo-expedicao. Sinal: "portal", "site", "Hodie", "navegar" -> operando-portal-atacadao. Sem mencao ao portal -> gerindo-expedicao |
| operando-portal-atacadao vs monitorando-entregas | **Portal web** (verificar agendamento no site) -> operando-portal-atacadao. **Sistema local** (status entrega, NF, canhoto) -> monitorando-entregas. Sinal: "no portal", "no site" -> operando-portal-atacadao. Sem mencao -> monitorando-entregas |
| resolvendo-problemas vs ralph-wiggum | Problema **DESCONHECIDO** (investigar, root cause) -> resolvendo-problemas. Problema **CONHECIDO** + spec clara -> ralph-wiggum. Sinal: "por que X?", "investigar", "root cause" -> resolvendo-problemas. "implementar feature Y" -> ralph-wiggum |
| resolvendo-problemas vs diagnosticando-banco | **Saude** do banco (indices, vacuum, cache) -> diagnosticando-banco. **Bug** envolvendo banco (query errada, dados inconsistentes) -> resolvendo-problemas |
| resolvendo-problemas vs prd-generator | Problema que precisa **solucao** -> resolvendo-problemas. Feature que precisa **spec** antes de implementar -> prd-generator |
| consultando-sentry vs diagnosticando-banco | **Erros de aplicacao** (exceptions, 500, issues) -> consultando-sentry. **Saude do banco** (indices, vacuum, cache) -> diagnosticando-banco. Sinal: "issues", "Sentry", "bugs" -> sentry. "queries lentas", "indices" -> banco |
| consultando-sentry vs resolvendo-problemas | **Diagnostico rapido** (ver issue, stacktrace) -> consultando-sentry. **Investigacao profunda** (multi-arquivo, root cause complexo) -> resolvendo-problemas. Combinavel: sentry para dados + resolvendo-problemas para fix |

---

| AGENTE (memorias, sessoes, diagnosticos) | "memorias do usuario", "sessoes anteriores", "health score agente", "knowledge graph", "consolidar memorias", "padroes aprendidos" | -> `gerindo-agente` |

---

## Skills — Inventario Completo (30 total)

Cada skill tem `SKILL.md` em `.claude/skills/<nome>/`.

### MCP Custom Tools (agente web, in-process)
`mcp__sql__consultar_sql`, `mcp__memory__*` (6 tools), `mcp__schema__*` (2 tools),
`mcp__sessions__*` (2 tools), `mcp__render__*` (3 tools: logs, erros, status),
`mcp__routes__search_routes` (1 tool: busca semantica rotas)

### Skills Odoo (Claude Code)
`rastreando-odoo`, `executando-odoo-financeiro`, `descobrindo-odoo-estrutura`,
`integracao-odoo`, `validacao-nf-po`, `conciliando-odoo-po`, `recebimento-fisico-odoo`, `razao-geral-odoo`

### Skills Dev (Claude Code)
`frontend-design`, `skill-creator`, `ralph-wiggum`, `prd-generator`, `resolvendo-problemas`

### Skills SSW (Claude Code)
`acessando-ssw`, `operando-ssw`

### Skills Portal Atacadao (Claude Code)
`operando-portal-atacadao`

### Skills CarVia (Claude Code)
`gerindo-carvia`

### Agente (gestao do sistema de agente)
`gerindo-agente` (substitui `memoria-usuario` — deprecated)

### Sentry (monitoramento de erros)
`consultando-sentry` (MCP-first, 20 tools, Seer AI)

### Utilitarios (compartilhados)
`exportando-arquivos`, `lendo-arquivos`, `consultando-sql`, `cotando-frete`,
`visao-produto`, `resolvendo-entidades`, `gerindo-expedicao`, `monitorando-entregas`,
`diagnosticando-banco`, `buscando-rotas`
