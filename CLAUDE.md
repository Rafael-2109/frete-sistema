# [PRECISION MODE] - MODO PRECISION ENGINEER ATIVO

**Ultima Atualizacao**: 06/02/2026

## REGRAS ABSOLUTAS - NUNCA IGNORAR:

### SEMPRE FAZER:
1. **INICIAR TODA RESPOSTA COM**: "CONFIRMACAO DO ENTENDIMENTO: Entendi que voce precisa..."
2. **MOSTRAR EVIDENCIAS**: Citar arquivo:linha ANTES de qualquer modificacao
3. **VERIFICAR TUDO**: Ler arquivos completos, verificar imports, testar mentalmente
4. **QUESTIONAR**: Se algo nao estiver 100% claro, PARAR e PERGUNTAR
5. **AMBIENTE VIRTUAL**: Sempre utilize o ambiente virtual quando for necessario `source .venv/bin/activate`

### NUNCA FAZER:
1. **NUNCA assumir** comportamento pelo nome da funcao
2. **NUNCA inventar** imports ou caminhos
3. **NUNCA modificar** sem mostrar o codigo atual primeiro
4. **NUNCA pular** direto para a solucao
5. **NUNCA mantenha lixo** Caso um codigo seja substituido, REMOVA o anterior
6. **NUNCA criar tela sem acesso via UI** - TODA tela criada DEVE ter link no menu (base.html) ou em outra tela

### ANTES DE PROPOR NOVOS ARQUIVOS OU REORGANIZACAO:

**CHECKLIST OBRIGATORIO**:

1. **LER**: Secao "INDICE DE REFERENCIAS" deste arquivo (abaixo)
2. **VERIFICAR**: O conteudo proposto ja existe? Se SIM -> NAO criar novo
3. **MOSTRAR**: Listar o que cada arquivo existente contem antes de criar novo

**VIOLACAO** = Propor arquivo que ja existe ou duplica conteudo existente

### FORMATO OBRIGATORIO DE RESPOSTA:
```
1. CONFIRMACAO DO ENTENDIMENTO: "Entendi que voce precisa [...]"
2. ANALISE DETALHADA: "Analisando arquivo X, linhas Y-Z..."
3. QUESTOES (se houver): "Antes de prosseguir, preciso confirmar..."
4. IMPLEMENTACAO: "Com base na analise completa..."
```

---

# REGRA CRITICA: ACESSO VIA UI OBRIGATORIO

**VIOLACAO GRAVE** = Criar tela HTML sem link de acesso no menu ou em outra tela.

### CHECKLIST ao criar nova tela:
1. Definir rota em views
2. Criar template HTML
3. **ADICIONAR LINK** no menu (`app/templates/base.html`) ou em tela relacionada

---

# FORMATACAO NUMERICA BRASILEIRA

**SEMPRE** exibir numeros no formato brasileiro (decimal: `,` / milhar: `.`).

**Arquivo**: `app/utils/template_filters.py`

```jinja
{{ valor|valor_br }}        {# R$ 1.234,56 (2 decimais) #}
{{ valor|valor_br(4) }}     {# R$ 1.234,5678 (4 decimais) #}
{{ qtd|numero_br }}         {# 1.234,567 (3 decimais) #}
{{ qtd|numero_br(0) }}      {# 1.234 (0 decimais) #}
```

---

# CRIACAO DE TABELAS E CAMPOS

Gerar script python local + script SQL para Render Shell:

```python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))
from app import create_app, db
from sqlalchemy import text

def alterar_campo():
    app = create_app()
    with app.app_context():
        try:
            db.session.execute(text("ALTER TABLE ..."))
            db.session.commit()
        except Exception as e:
            print(f"Erro: {e}")
            db.session.rollback()
```

### APOS ALTERAR MODELOS: Regenerar Schemas do Agente

**OBRIGATORIO** apos adicionar/remover/alterar campos em qualquer modelo SQLAlchemy:

```bash
source .venv/bin/activate
python .claude/skills/consultando-sql/scripts/generate_schemas.py
```

Atualiza `schemas/tables/*.json`, `catalog.json` e `relationships.json`.
Sem isso, o agente web nao enxerga os campos novos.

---

# INDICE DE REFERENCIAS

| Preciso de... | Documento |
|---------------|-----------|
| Regras de CarteiraPrincipal / Separacao (listeners, status, gotchas) | `.claude/references/modelos/REGRAS_CARTEIRA_SEPARACAO.md` |
| Regras de outros modelos (status transitions, gotchas, naming traps) | `.claude/references/modelos/REGRAS_MODELOS.md` |
| Campos e tipos de QUALQUER tabela | Schema auto-gerado: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json` |
| Cadeia Pedido -> Entrega (JOINs, estados, formulas) | `.claude/references/modelos/CADEIA_PEDIDO_ENTREGA.md` |
| Regras de negocio (CNPJ, bonificacao, roteirizacao) | `.claude/references/negocio/REGRAS_NEGOCIO.md` |
| Frete Real vs Teorico (4 valores, divergencias, conta corrente) | `.claude/references/negocio/FRETE_REAL_VS_TEORICO.md` |
| Margem e Custeio (formula margem, tabelas de custo) | `.claude/references/negocio/MARGEM_CUSTEIO.md` |
| Queries SQL e JOINs entre tabelas | `.claude/references/modelos/QUERIES_MAPEAMENTO.md` |
| Indice completo de toda documentacao | `.claude/references/INDEX.md` |

### Documentos Adicionais
| Documento | Localizacao |
|-----------|-------------|
| Card de Separacao | `CARD_SEPARACAO.md` (raiz) |
| API TagPlus | `app/integracoes/tagplus/DOCUMENTACAO_API_TAGPLUS.md` |
| Sistema de Devolucoes | `app/devolucao/README.md` |

---

# ROUTING OBRIGATORIO

**REGRA**: Use a skill MAIS ESPECIFICA. `descobrindo-odoo-estrutura` e ULTIMO RECURSO.

### Passo 1: Identificar o CONTEXTO

| Contexto | Sinais | Proximo passo |
|----------|--------|---------------|
| CONSULTA LOCAL (CarteiraPrincipal, Separacao, etc.) | Campos locais, queries SQL, regras de negocio | -> Consultar REFERENCES (sem skill) |
| CONSULTA ANALITICA (agregacoes, rankings, distribuicoes) | "quantos por estado", "top 10", "valor total por", comparacoes | -> `consultando-sql` |
| OPERACAO ODOO (API, modelos, integracoes) | NF, PO, picking, Odoo, pagamento, extrato | -> Passos 2 e 3 abaixo |
| DESENVOLVIMENTO FRONTEND | Criar tela, dashboard, CSS, template | -> `frontend-design` |
| COTACAO DE FRETE | "qual preco", "quanto custa frete", "tabelas para", "cotacao" | -> `cotando-frete` |
| VISAO 360 PRODUTO | "resumo do produto", "producao vs programado", "visao completa do produto" | -> `visao-produto` |
| EXPORTAR/IMPORTAR DADOS | Gerar Excel, CSV, processar planilha | -> `exportando-arquivos` / `lendo-arquivos` |

### Passo 2 (ODOO): Tem dado ESTATICO ja documentado?

| Preciso de... | Nao use skill, consulte diretamente: |
|---------------|--------------------------------------|
| ID fixo (company, picking_type, journal) | `.claude/references/odoo/IDS_FIXOS.md` |
| Conversao UoM (Milhar, fator_un) | `.claude/references/odoo/CONVERSAO_UOM.md` |
| Campos ja mapeados do Odoo | `.claude/references/odoo/MODELOS_CAMPOS.md` |
| GOTCHAS conhecidos (timeouts, erros) | `.claude/references/odoo/GOTCHAS.md` |

Se a resposta esta no reference -> NAO usar skill.

### Passo 3 (ODOO): Arvore de Decisao de Skills

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

### Desambiguacao (quando 2 skills parecem servir)

| Duvida entre... | Regra de desempate |
|-----------------|-------------------|
| rastreando vs executando-financeiro | READ/consultar -> rastreando. WRITE/criar/modificar -> executando |
| rastreando vs validacao-nf-po | Fluxo completo -> rastreando. Apenas Fase 2 match -> validacao |
| conciliando vs validacao-nf-po | Fase 3 (split/consolidar) -> conciliando. Fase 2 (match) -> validacao |
| integracao vs descobrindo | CRIAR novo service -> integracao. EXPLORAR modelo -> descobrindo |
| Nao sei qual skill Odoo usar | -> Subagente `especialista-odoo` (orquestra todas) |

---

# SKILLS (21 total)

Referencia completa: cada skill tem `SKILL.md` em `.claude/skills/<nome>/`.
O routing table acima (Passo 1) indica QUAL skill usar para QUAL contexto.

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

---

# MODELOS CRITICOS

### REGRA: Campos de Tabelas
NUNCA consultar reference docs para campos/tipos.
SEMPRE usar schemas auto-gerados: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`
References contem APENAS regras de negocio e gotchas.

**ANTES de usar regras de CarteiraPrincipal ou Separacao**:
-> LER `.claude/references/modelos/REGRAS_CARTEIRA_SEPARACAO.md`

**ANTES de usar regras de outros modelos (Embarque, Faturamento, etc.)**:
-> LER `.claude/references/modelos/REGRAS_MODELOS.md`

### Regras Rapidas:
- CarteiraPrincipal: `qtd_saldo_produto_pedido` (NAO `qtd_saldo`)
- Separacao: `qtd_saldo` (NAO `qtd_saldo_produto_pedido`)
- Separacao tem `expedicao`, `agendamento`, `protocolo` (Carteira NAO tem)
- `sincronizado_nf=False` = aparece na carteira, projeta estoque

---

# CAMINHOS DO SISTEMA

### Carteira de Pedidos (CORRETOS):
- `app/carteira/routes/`, `app/carteira/services/`, `app/carteira/utils/`
- `app/templates/carteira/`

### Carteira de Pedidos (OBSOLETO - NAO USAR):
- `app/carteira/main_routes.py`

### Agente Logistico Web:
- `app/agente/` - Modulo principal (Claude Agent SDK)

---

# AGENTE LOGISTICO WEB

| Arquivo | Publico-Alvo | Proposito |
|---------|--------------|-----------|
| **CLAUDE.md** | Claude Code (dev) | Desenvolvimento do sistema |
| **system_prompt.md** | Agente Web | Usuarios finais (logistica) |

**NAO MISTURAR**: Regras P1-P7 pertencem ao `system_prompt.md`, nao ao CLAUDE.md.

### Arquitetura
```
app/agente/
  models.py                    # AgentSession, AgentMemory, AgentMemoryVersion
  routes.py                    # API endpoints, SSE streaming, file upload, insights
  prompts/system_prompt.md     # Prompt agente web (v3.3.0)
  sdk/client.py                # AgentClient — query() + resume, hooks, MCP registration
  sdk/pending_questions.py     # AskUserQuestion: threading.Event wait/set
  tools/text_to_sql_tool.py    # MCP: consultar_sql (in-process)
  tools/memory_mcp_tool.py     # MCP: 6 memory operations (in-process)
  tools/schema_mcp_tool.py     # MCP: schema discovery (in-process)
  tools/session_search_tool.py # MCP: session search (in-process)
  tools/render_logs_tool.py    # MCP: logs/erros/status Render (in-process)
  config/settings.py           # AgentSettings (model, pricing, tools_enabled)
  config/feature_flags.py      # Feature flags (20+, env var based)
  config/permissions.py        # can_use_tool + reversibility check
  services/memory_consolidator.py # Consolidacao Haiku periodica
```

---

# SUBAGENTES

| Agent | Dominio | Quando Usar |
|-------|---------|-------------|
| `analista-carteira` | Agente Web | Analise P1-P7, comunicacao PCP/Comercial |
| `especialista-odoo` | Agente Web | Problema cross-area Odoo, nao sabe qual skill |
| `raio-x-pedido` | Agente Web | Visao 360 do pedido (carteira+NF+entrega+frete) |
| `desenvolvedor-integracao-odoo` | Claude Code | Criar/modificar integracoes Odoo |

---

# MCP Servers

### Context7 (Documentacao de Bibliotecas)
Usar quando implementando com lib externa (Flask, SQLAlchemy, Pandas, etc.):
```
resolve-library-id("sqlalchemy") -> query-docs("/...", "bulk insert")
``` 

---

# TERMINOLOGIA BRASILEIRA

- Carteira de pedidos (nao "wallet")
- Separacao (nao "separation")
- Embarque (nao "shipment")
- Nota fiscal / NF-e (nao "invoice")
- CNPJ (documentos brasileiros)
- Formato de data: DD/MM/YYYY
- Moeda: R$ (BRL)

---

# INFORMAÇÕES SOBRE DOMINIO E SERVIDOR

## RENDER — MCP Server (OBRIGATORIO)

### REGRA: DADOS DE PRODUCAO = RENDER
Quando o usuario perguntar sobre dados, registros, quantidades, status de servicos,
metricas, logs ou deploys, SEMPRE consultar via MCP Render (`mcp__render__*`).
Os dados reais estao no Render. O banco local existe para desenvolvimento e migrations.

### IDs dos Recursos (usar direto nas tools)

| Recurso | ID | Nome |
|---------|----|------|
| Postgres | `dpg-d13m38vfte5s738t6p50-a` | sistema-fretes-db |
| Web Service (Pro) | `srv-d13m38vfte5s738t6p60` | sistema-fretes |
| Worker | `srv-d2muidggjchc73d4segg` | sistema-fretes-worker-atacadao |
| Web Service (free) | `srv-d1k6gcbe5dus73e5o3hg` | frete-sistema (DEPRECATED) |
| Redis | `red-d1c4jheuk2gs73absk10` | sistema-fretes-redis |

### Ferramentas MCP Disponiveis

| Ferramenta | Uso |
|------------|-----|
| `query_render_postgres` | Consulta SQL read-only no banco de producao |
| `list_services` | Listar servicos e status |
| `list_deploys` | Historico de deploys por servico |
| `get_deploy` | Detalhes de um deploy especifico |
| `get_metrics` | CPU, memoria, HTTP requests, latencia, bandwidth |
| `list_logs` | Logs de app, request e build |
| `list_postgres_instances` | Info do Postgres |
| `list_key_value` | Info do Redis |
| `get_service` | Detalhes de um servico |

### Exemplos de Uso

```
# Consultar dados de producao
mcp__render__query_render_postgres(postgresId="dpg-d13m38vfte5s738t6p50-a", sql="SELECT ...")

# Ver metricas
mcp__render__get_metrics(resourceId="srv-d13m38vfte5s738t6p60", metricTypes=["cpu_usage", "memory_usage"])

# Ver logs recentes
mcp__render__list_logs(resource=["srv-d13m38vfte5s738t6p60"], limit=20)

# Ver ultimos deploys
mcp__render__list_deploys(serviceId="srv-d13m38vfte5s738t6p60", limit=5)
```

### Servicos

| Servico | Tipo | Plano | Dominio |
|---------|------|-------|---------|
| sistema-fretes | Web Service | Pro 4GB 2CPU | sistema-fretes.onrender.com |
| frete-sistema | Web Service | Free | frete-sistema.onrender.com | # Deprecated
| sistema-fretes-worker-atacadao | Background Worker | Standard 2GB 1CPU | — |
| sistema-fretes-redis | Key Value | Starter 256MB | — |
| sistema-fretes-db | Postgres | Basic 1GB | — |

## ODOO

### ERP

- odoo.nacomgoya.com.br

---
