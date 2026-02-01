# [PRECISION MODE] - MODO PRECISION ENGINEER ATIVO

**Ultima Atualizacao**: 31/01/2026

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

---

# INDICE DE REFERENCIAS

| Preciso de... | Documento |
|---------------|-----------|
| Campos de CarteiraPrincipal / Separacao | `.claude/references/modelos/CAMPOS_CARTEIRA_SEPARACAO.md` |
| Campos de outros modelos (Embarque, Faturamento, etc.) | `.claude/references/modelos/MODELOS_CAMPOS.md` |
| Regras de negocio (CNPJ, bonificacao, roteirizacao) | `.claude/references/negocio/REGRAS_NEGOCIO.md` |
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

# SKILLS POR DOMINIO

## Agente Web (Render/Producao)
Skills usadas exclusivamente pelo agente logistico web:
- `gerindo-expedicao` - Consultas logisticas, estoque, separacoes
- `memoria-usuario` - Memoria persistente entre sessoes

## Claude Code (Desenvolvimento)
Skills para desenvolvimento no Cursor/Terminal:

### Integracao Odoo
| Skill | Responsabilidade |
|-------|-----------------|
| `rastreando-odoo` | Seguir rastro de NF, PO, SO, pagamento |
| `executando-odoo-financeiro` | Criar pagamentos, reconciliar extratos |
| `descobrindo-odoo-estrutura` | Explorar campos/modelos nao mapeados |
| `integracao-odoo` | Criar novas integracoes (16 etapas) |
| `validacao-nf-po` | Fase 2: Match NF x PO |
| `conciliando-odoo-po` | Fase 3: Consolidacao PO |
| `recebimento-fisico-odoo` | Fase 4: Recebimento fisico |
| `razao-geral-odoo` | Exportar razao geral |

### Desenvolvimento
| Skill | Responsabilidade |
|-------|-----------------|
| `frontend-design` | Interfaces Flask/Jinja2 com CSS Nacom |
| `skill_creator` | Criar/atualizar skills |
| `ralph-wiggum` | Loops autonomos de desenvolvimento |
| `prd-generator` | Gerar specs/PRDs |

### Utilitarios (compartilhados)
| Skill | Responsabilidade |
|-------|-----------------|
| `exportando-arquivos` | Gerar Excel, CSV, JSON |
| `lendo-arquivos` | Processar Excel/CSV enviados |
| `consultando-sql` | Consultas analiticas SQL via linguagem natural |

---

# MODELOS CRITICOS

**ANTES de usar campos de CarteiraPrincipal ou Separacao**:
-> LER `.claude/references/modelos/CAMPOS_CARTEIRA_SEPARACAO.md`

**ANTES de usar campos de outros modelos (Embarque, Faturamento, etc.)**:
-> LER `.claude/references/modelos/MODELOS_CAMPOS.md`

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
  models.py              # AgentSession, AgentMemory, AgentEvent
  routes.py              # API endpoints (/api/agente/...)
  memory_tool.py         # DatabaseMemoryTool
  prompts/system_prompt.md  # Prompt agente web (v3.0.0)
  sdk/client.py          # Substitui {data_atual}, {usuario_nome}, {user_id}
```

---

# SUBAGENTES

| Agent | Dominio | Quando Usar |
|-------|---------|-------------|
| `analista-carteira` | Agente Web | Analise P1-P7, comunicacao PCP/Comercial |
| `especialista-odoo` | Agente Web | Problema cross-area Odoo, nao sabe qual skill |
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
