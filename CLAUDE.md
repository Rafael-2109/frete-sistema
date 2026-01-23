# [PRECISION MODE] - MODO PRECISION ENGINEER ATIVO

**Ultima Atualizacao**: 16/01/2026

## REGRAS ABSOLUTAS - NUNCA IGNORAR:

### SEMPRE FAZER:
1. **INICIAR TODA RESPOSTA COM**: "CONFIRMACAO DO ENTENDIMENTO: Entendi que voce precisa..."
2. **MOSTRAR EVIDENCIAS**: Citar arquivo:linha ANTES de qualquer modificacao
3. **VERIFICAR TUDO**: Ler arquivos completos, verificar imports, testar mentalmente
4. **QUESTIONAR**: Se algo nao estiver 100% claro, PARAR e PERGUNTAR
5. **AMBIENTE VIRTUAL**: Sempre utilize o ambiente virtual quando for necessário `source .venv/bin/activate`

### NUNCA FAZER:
1. **NUNCA assumir** comportamento pelo nome da funcao
2. **NUNCA inventar** imports ou caminhos
3. **NUNCA modificar** sem mostrar o codigo atual primeiro
4. **NUNCA pular** direto para a solucao
5. **NUNCA mantenha lixo** Caso um codigo seja substituido, REMOVA o anterior, mantenha o codigo limpo.
6. **NUNCA criar tela sem acesso via UI** - TODA tela criada DEVE ter link no menu (base.html) ou em outra tela acessivel

### ANTES DE PROPOR NOVOS ARQUIVOS OU REORGANIZACAO:

**CHECKLIST OBRIGATORIO** - Executar e MOSTRAR output antes de qualquer proposta:

1. **EXECUTAR**: `ls -la .claude/references/` - mostrar arquivos existentes
2. **EXECUTAR**: `ls -la .claude/skills/[skill-em-questao]/` - mostrar arquivos da skill
3. **LER**: Secao "INDICE DE REFERENCIAS" deste arquivo (abaixo)
4. **LISTAR**: O que cada arquivo existente contem (1 linha por arquivo)
5. **VERIFICAR**: O conteudo proposto ja existe? Se SIM → NAO criar novo

**VIOLACAO** = Propor arquivo que ja existe ou duplica conteudo existente

### FORMATO OBRIGATORIO DE RESPOSTA:
```
1. CONFIRMACAO DO ENTENDIMENTO:
   "Entendi que voce precisa [EXATAMENTE o que foi pedido]..."

2. ANALISE DETALHADA:
   "Analisando arquivo X, linhas Y-Z, vejo que..."
   [MOSTRAR CODIGO ATUAL]

3. QUESTOES (se houver):
   "Antes de prosseguir, preciso confirmar:..."

4. IMPLEMENTACAO:
   "Com base na analise completa..."
```

### PALAVRA DE ATIVACAO:
Quando ver **"pense profundamente"** ou **"[PRECISION MODE]"**: DOBRAR o nivel de rigor e detalhe.

---

# REGRA CRITICA: ACESSO VIA UI OBRIGATORIO

## ⚠️ TODA TELA CRIADA DEVE TER ACESSO PELA INTERFACE

**VIOLACAO GRAVE** = Criar tela HTML sem link de acesso no menu ou em outra tela.

### CHECKLIST OBRIGATORIO ao criar nova tela:
1. **Definir rota** no arquivo de views (ex: `views.py`)
2. **Criar template** HTML
3. **ADICIONAR LINK** em uma das opcoes abaixo:
   - Menu principal (`app/templates/base.html`)
   - Botao/link em tela relacionada
   - Dashboard com cards de acesso

### Arquivo de Menu Principal:
```
app/templates/base.html
```

### Exemplo de adicao ao menu:
```html
<li><a class="dropdown-item" href="{{ url_for('modulo_views.nome_da_tela') }}">
    <i class="fas fa-icon"></i> Nome da Tela
  </a></li>
```

### Telas por Modulo (Referencia):

| Modulo | Telas | Menu em |
|--------|-------|---------|
| Financeiro | Central Financeira (dashboard), Custeio, Relatorios, Contas a Receber/Pagar | base.html > Financeiro > Central Financeira |
| Fretes | Dashboard Fretes, Listar, Lancar CTe, Aprovacoes, Faturas | base.html > Financeiro > Fretes |
| Recebimento (Fase 1) | Divergencias Fiscais, Primeira Compra, Perfis Fiscais | base.html > Financeiro > Central Fiscal |
| Recebimento (Fase 2) | Validacoes NF×PO, Divergencias NF×PO, De-Para Fornecedor, Preview Consolidacao | base.html > Financeiro > Central Fiscal |
| Recebimento (Fase 4) | Recebimento Fisico, Status Recebimentos | base.html > Financeiro > Central Fiscal |
| Fiscal IBS/CBS | Documentos C/ IBS/CBS, Cadastro NCM IBS/CBS, Pendencias IBS/CBS | base.html > Financeiro > Central Fiscal |
| Carteira | Dashboard, Agrupados Balanceado | base.html > Operacional |
| Separacao | Lista, Card, Agendamento | base.html > Operacional |

---

# FORMATACAO NUMERICA BRASILEIRA

## Padrao Obrigatorio

**SEMPRE** exibir numeros no formato brasileiro:
- **Decimal**: Virgula (`,`)
- **Milhar**: Ponto (`.`)

### Exemplos:
| Valor Original | Formato BR |
|----------------|------------|
| 1234.56 | 1.234,56 |
| 1234567.89 | 1.234.567,89 |
| 0.1234 | 0,1234 |

## Filtros Jinja2 Disponiveis

**Arquivo**: `app/utils/template_filters.py`

### valor_br (valores monetarios)
```jinja
{{ valor|valor_br }}      {# 2 decimais (padrao) -> 1.234,56 #}
{{ valor|valor_br(0) }}   {# 0 decimais -> 1.234 #}
{{ valor|valor_br(4) }}   {# 4 decimais -> 1.234,5678 #}
```

### numero_br (quantidades e numeros genericos)
```jinja
{{ qtd|numero_br }}       {# 3 decimais (padrao) -> 1.234,567 #}
{{ qtd|numero_br(0) }}    {# 0 decimais -> 1.234 #}
{{ qtd|numero_br(4) }}    {# 4 decimais -> 1.234,5678 #}
```

### Uso Correto em Templates
```jinja
{# Quantidade #}
{{ item.qtd_nf|numero_br(3) }}

{# Preco unitario (4 decimais) #}
R$ {{ item.preco_nf|numero_br(4) }}

{# Valor total (2 decimais) #}
R$ {{ (item.qtd * item.preco)|numero_br(2) }}
```

### NUNCA usar format do Python em templates:
```jinja
{# ERRADO - formato americano #}
{{ "%.2f"|format(valor) }}

{# CORRETO - formato brasileiro #}
{{ valor|numero_br(2) }}
```

---

# INDICE DE REFERENCIAS

## Onde Buscar Informacao

| Preciso de... | Documento | Quando Usar |
|---------------|-----------|-------------|
| Campos de Carteira/Separacao | **Este arquivo (abaixo)** | Desenvolvendo features principais |
| Campos de outros modelos | `.claude/references/MODELOS_CAMPOS.md` | Pedido, Embarque, Faturamento, DespesaExtra, ContasAReceber |
| Regras de negocio detalhadas | `.claude/references/REGRAS_NEGOCIO.md` | Grupos CNPJ, bonificacao, roteirizacao, calculos |
| Queries e mapeamentos SQL | `.claude/references/QUERIES_MAPEAMENTO.md` | Consultas SQL, JOINs entre tabelas |
| Consultas estoque/carteira | Skill `gerindo-expedicao` | Perguntas sobre disponibilidade, pedidos, estoque |
| Integracao Odoo | Skill `integracao-odoo` | Lancamentos fiscais, CTe, 16 etapas |
| Memoria do usuario | Skill `memoria-usuario` | Preferencias, correcoes, contexto persistente |
| Indice completo | `.claude/references/INDEX.md` | Navegacao centralizada de toda documentacao |

## Documentos de Referencia Adicionais
| Documento | Localizacao | Descricao |
|-----------|-------------|-----------|
| ESPECIFICACAO_SINCRONIZACAO_ODOO.md | `app/odoo/services/` | Processo de sincronizacao com Odoo |
| CARD_SEPARACAO.md | Raiz do projeto | Detalhamento do Card de Separacao |
| DOCUMENTACAO_API_TAGPLUS.md | `app/integracoes/tagplus/` | API TagPlus |
| ROADMAP_FEATURES_AGENTE.md | `.claude/references/` | Roadmap de features do agente |
| ROADMAP_IMPLEMENTACAO.md | `.claude/references/` | Roadmap de implementacao geral |
| historia_organizada.md | `.claude/references/` | Historico de decisoes do projeto |
| README.md (Devolucoes) | `app/devolucao/` | Sistema de Gestao de Devolucoes |
| CONVERSAO_UOM_ODOO.md | `.claude/references/` | Fluxo de conversao de UM no recebimento de compras |

## Cookbooks (Exemplos de Codigo)
- `.claude/references/cookbooks/` - Exemplos praticos de implementacao

---

# CRIACAO DE TABELAS E CAMPOS

**Formato esperado**: Todos os campos ou modelos criados, devera ser gerado um script python para rodar localmente e um script SQL simples para rodar no Shell do Render.

```python
# Exemplo de script python:
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

from app import create_app, db
from sqlalchemy import text

def alterar_campo():
    app = create_app()
    with app.app_context():
        try:
            resultado = db.session.execute(text("""
                ALTER TABLE ...
            """))
            db.session.commit()
        except Exception as e:
            print(f"Erro: {e}")
            db.session.rollback()
```

---

# MODELOS CRITICOS - SEMPRE CONSULTAR

## CarteiraPrincipal (app/carteira/models.py)

**Tabela**: `carteira_principal`
**Uso**: Pedidos originais com saldo pendente (fonte de verdade para demanda)

### Campos de Datas e Agendamento
```python
# CAMPOS CORRETOS - SEMPRE USAR ESTES NOMES:
data_entrega_pedido = db.Column(db.Date, nullable=True)          # Data entrega solicitada pelo comercial
observ_ped_1 = db.Column(db.Text, nullable=True)                 # Observacoes

# CAMPOS QUE NAO EXISTEM - NUNCA USAR:
# data_entrega
# expedicao
# agendamento
# protocolo
# agendamento_confirmado
# hora_agendamento
# data_expedicao_pedido
# data_agendamento_pedido
```

### Campos de Quantidades e Valores
```python
# CAMPOS CORRETOS E USADOS:
qtd_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False)       # Quantidade original
qtd_saldo_produto_pedido = db.Column(db.Numeric(15, 3), nullable=False) # Saldo disponivel
qtd_cancelada_produto_pedido = db.Column(db.Numeric(15, 3), default=0)  # Quantidade cancelada
preco_produto_pedido = db.Column(db.Numeric(15, 2), nullable=True)      # Preco unitario
```

### Campos de Identificacao
```python
# CAMPOS CORRETOS:
num_pedido = db.Column(db.String(50), nullable=False, index=True)       # Numero do pedido
cod_produto = db.Column(db.String(50), nullable=False, index=True)      # Codigo do produto
cnpj_cpf = db.Column(db.String(20), nullable=False, index=True)         # CNPJ/CPF cliente
separacao_lote_id = db.Column(db.String(50), nullable=True, index=True) # ID lote separacao
pedido_cliente = db.Column(db.String(100), nullable=True)               # Pedido de Compra do Cliente
```

### Campos de Cliente e Produto
```python
# CAMPOS CORRETOS:
nome_produto = db.Column(db.String(255), nullable=False)        # Nome do produto
raz_social = db.Column(db.String(255), nullable=True)           # Razao Social completa
raz_social_red = db.Column(db.String(100), nullable=True)       # Razao Social reduzida
municipio = db.Column(db.String(100), nullable=True)            # Municipio cliente
estado = db.Column(db.String(2), nullable=True)                 # UF cliente
vendedor = db.Column(db.String(100), nullable=True, index=True) # Vendedor
equipe_vendas = db.Column(db.String(100), nullable=True)        # Equipe de vendas
```

### Campos de Endereco de Entrega
```python
# CAMPOS CORRETOS:
cnpj_endereco_ent = db.Column(db.String(20), nullable=True)      # CNPJ entrega
empresa_endereco_ent = db.Column(db.String(255), nullable=True)  # Nome local entrega
cep_endereco_ent = db.Column(db.String(10), nullable=True)       # CEP
nome_cidade = db.Column(db.String(100), nullable=True)           # Cidade extraida
cod_uf = db.Column(db.String(2), nullable=True)                  # UF extraida
bairro_endereco_ent = db.Column(db.String(100), nullable=True)   # Bairro
rua_endereco_ent = db.Column(db.String(255), nullable=True)      # Rua
endereco_ent = db.Column(db.String(20), nullable=True)           # Numero
telefone_endereco_ent = db.Column(db.String(20), nullable=True)  # Telefone
```

### Tags do Pedido (Odoo)
```python
# CAMPO PARA TAGS DO ODOO:
tags_pedido = db.Column(db.Text, nullable=True)  # JSON: [{"name": "VIP", "color": 5}]

# FORMATO JSON ESPERADO:
# [
#   {"name": "Urgente", "color": 1},
#   {"name": "VIP", "color": 5},
#   {"name": "Grande Volume", "color": 7}
# ]

# SINCRONIZACAO: Vem do campo tag_ids do sale.order no Odoo
# MODELO ODOO: crm.tag com campos id, name, color
```

---

## Separacao (app/separacao/models.py)

**Tabela**: `separacao`
**Uso**: Unica fonte da verdade para projetar as saidas de estoque atraves de sincronizado_nf=False

### REGRA CRITICA: sincronizado_nf
- **sincronizado_nf=False**: Item SEMPRE aparece na carteira e SEMPRE e projetado no estoque
- **sincronizado_nf=True**: Foi faturado (tem NF), NAO aparece na carteira, NAO projeta estoque

### Campos Principais
```python
# CAMPOS CORRETOS:
separacao_lote_id = db.Column(db.String(50), nullable=True, index=True) # ID do lote
num_pedido = db.Column(db.String(50), nullable=True)            # Numero do pedido
cod_produto = db.Column(db.String(50), nullable=True)           # Codigo produto
qtd_saldo = db.Column(db.Float, nullable=True)                  # Quantidade separada
valor_saldo = db.Column(db.Float, nullable=True)                # Valor separado
peso = db.Column(db.Float, nullable=True)                       # Peso
pallet = db.Column(db.Float, nullable=True)                     # Pallet
numero_nf = db.Column(db.String(20), nullable=True)             # NF associada quando sincronizada

# Campos de cliente:
pedido_cliente = db.Column(db.String(100), nullable=True)       # Pedido de Compra do Cliente
cnpj_cpf = db.Column(db.String(20), nullable=True)              # CNPJ cliente
raz_social_red = db.Column(db.String(255), nullable=True)       # Razao Social reduzida
nome_cidade = db.Column(db.String(100), nullable=True)          # Cidade
cod_uf = db.Column(db.String(2), nullable=False)                # UF

# Campos de data:
data_pedido = db.Column(db.Date, nullable=True)                 # Data do pedido
expedicao = db.Column(db.Date, nullable=True)                   # Data expedicao
agendamento = db.Column(db.Date, nullable=True)                 # Data agendamento
protocolo = db.Column(db.String(50), nullable=True)             # Protocolo
criado_em = db.Column(db.DateTime, default=datetime.utcnow)     # Data criacao

# Campos operacionais:
tipo_envio = db.Column(db.String(10), default='total', nullable=True) # total, parcial
observ_ped_1 = db.Column(db.String(700), nullable=True)         # Observacoes (truncado automaticamente)
roteirizacao = db.Column(db.String(255), nullable=True)         # Transportadora sugerida
rota = db.Column(db.String(50), nullable=True)                  # Rota
sub_rota = db.Column(db.String(50), nullable=True)              # Sub-rota

# CAMPOS DE CONTROLE:
status = db.Column(db.String(20), default='ABERTO', nullable=False, index=True)
# Valores comuns de status: 'PREVISAO', 'ABERTO', 'COTADO', 'EMBARCADO', 'FATURADO', 'NF no CD'

nf_cd = db.Column(db.Boolean, default=False, nullable=False)    # NF voltou para o CD
sincronizado_nf = db.Column(db.Boolean, default=False, nullable=True)  # GATILHO PRINCIPAL
```

### Diferenca entre Campos de Carteira vs Separacao

| Campo | CarteiraPrincipal | Separacao |
|-------|-------------------|-----------|
| Quantidade | `qtd_saldo_produto_pedido` | `qtd_saldo` |
| Valor | `preco_produto_pedido` | `valor_saldo` |
| Data entrega cliente | `data_entrega_pedido` (cliente solicita, exp = data - leadtime) | NAO TEM |
| Data expedição | NAO TEM | `expedicao` (nós definimos) |
| Agendamento | NAO TEM | `agendamento` (nós solicitamos = exp + leadtime) |
| Protocolo | NAO TEM | `protocolo` |
| Status | NAO TEM | `status` |

Campos Calculados ao Criar Separação


| Campo | Cálculo | Fonte |
|-------|---------|-------|
| peso | qtd_saldo × peso_bruto | CadastroPalletizacao |
| pallet | qtd_saldo / palletizacao | CadastroPalletizacao |
| rota | buscar_rota_por_uf(cod_uf) | app.carteira.utils.separacao_utils |
| sub_rota | buscar_sub_rota_por_uf_cidade(cod_uf, nome_cidade) | app.carteira.utils.separacao_utils |

Referência: .claude/skills/gerindo-expedicao/scripts/criando_separacao_pedidos.py

---

# PALLETS: CÁLCULO TEÓRICO vs CONTROLE FÍSICO

## ⚠️ DOIS CONCEITOS DISTINTOS - NÃO MISTURAR

O sistema possui **dois grupos de campos** de pallet que são **INDEPENDENTES** e não devem ser confundidos:

### GRUPO 1: PALLETS TEÓRICOS (via CadastroPalletizacao)

**Propósito**: Estimativa baseada em pallets padrão (1 produto por pallet)
**Fonte**: `CadastroPalletizacao.palletizacao` (fator de conversão)
**Uso**: Impressão de embarque, estimativa inicial para planejamento

| Modelo | Campo | Cálculo |
|--------|-------|---------|
| `Separacao` | `pallet` | `qtd_saldo / CadastroPalletizacao.palletizacao` |
| `EmbarqueItem` | `pallets` | Soma de `Separacao.pallet` do lote |
| `Embarque` | `pallet_total` | Soma de `EmbarqueItem.pallets` |

**⚠️ LIMITAÇÃO**: O valor TEÓRICO pode divergir da realidade quando:
- Pallets contêm múltiplos produtos misturados
- Montagem real difere do padrão cadastrado

**Listener**: `app/separacao/models.py:318-422` sincroniza automaticamente estes campos

### GRUPO 2: PALLETS FÍSICOS (Controle Real - Gestão de Ativos PBR)

**Propósito**: Rastrear pallets físicos reais para faturamento de NF remessa
**Fonte**: Preenchimento manual pela expedição/logística
**Uso**: Controle de pallets emprestados, NF de pallet, saldo em terceiros

| Modelo | Campo | Descrição |
|--------|-------|-----------|
| `Embarque` | `nf_pallet_transportadora` | NF remessa de pallet para transportadora |
| `Embarque` | `qtd_pallet_transportadora` | Quantidade na NF remessa |
| `Embarque` | `qtd_pallets_separados` | Pallets físicos expedidos no carregamento |
| `Embarque` | `qtd_pallets_trazidos` | Pallets que a transportadora trouxe de volta |
| `EmbarqueItem` | `nf_pallet_cliente` | NF remessa de pallet para o cliente |
| `EmbarqueItem` | `qtd_pallet_cliente` | Quantidade na NF para o cliente |
| `EmbarqueItem` | `nf_pallet_referencia` | Qual NF de pallet cobre esta NF de venda |
| `EmbarqueItem` | `nf_pallet_origem` | 'EMBARQUE' ou 'ITEM' |

**✅ VALOR REAL**: Campos preenchidos manualmente refletem a realidade da expedição

### REGRA CRÍTICA

```
GRUPO 1 (Teórico) ≠ GRUPO 2 (Físico)

- O cálculo do GRUPO 1 NÃO afeta os campos do GRUPO 2
- Os campos são INDEPENDENTES
- Cada um tem seu propósito específico
```

### Propriedades Calculadas (GRUPO 2)

```python
# Embarque.saldo_pallets_pendentes
# = qtd_pallets_separados - qtd_pallets_trazidos - faturados

# Embarque.pallets_pendentes
# = True se saldo_pallets_pendentes > 0
```

---

# REGRAS DE OURO

### SEMPRE FAZER:
1. **Conferir este arquivo** antes de usar qualquer campo de Carteira/Separacao
2. **Usar nomes exatos** conforme documentado aqui
3. **Verificar se campo existe** no modelo antes de usar
4. **Consultar JOINs** quando campo vem de outra tabela
5. **Para outros modelos**: Consultar `.claude/references/MODELOS_CAMPOS.md`

### NUNCA FAZER:
1. **Inventar nomes de campos** sem consultar este arquivo
2. **Assumir que campo existe** sem verificar
3. **Usar replace_all** sem confirmar impactos
4. **Misturar campos** de tabelas diferentes

### QUANDO EM DUVIDA:
1. **Ler o modelo** no arquivo models.py
2. **Consultar este arquivo** CLAUDE.md
3. **Perguntar ao usuario** se campo nao estiver documentado
4. **Testar em ambiente local** se possivel

---

# EXEMPLOS DE USO CORRETO

### Agendamento - USO CORRETO:
```python
# Ler dados existentes em SEPARACAO:
item.agendamento  # CORRETO
item.expedicao    # CORRETO
item.protocolo    # CORRETO

# Salvar dados em SEPARACAO:
item.agendamento = data_agendamento           # CORRETO
item.expedicao = data_expedicao              # CORRETO
```

### Agendamento - USO INCORRETO:
```python
# NUNCA USAR ESTES CAMPOS (nao existem):
item.data_agendamento_pedido    # ERRO - nao existe
item.data_expedicao_pedido      # ERRO - nao existe
item.agendamento_status         # ERRO - nao existe
```

### Busca de Carteira - USO CORRETO:
```python
# Para buscar itens na carteira:
items = Separacao.query.filter_by(
    sincronizado_nf=False  # CORRETO - Criterio principal
).all()

# NAO fazer JOIN desnecessario com Pedido VIEW
```

---

# CAMINHOS DO SISTEMA

### ARQUIVOS OBSOLETOS DA CARTEIRA DE PEDIDOS (NAO USAR):
- `app/carteira/main_routes.py` - Carteira de pedidos antiga (ainda existe, mas nao usar)

### ARQUIVOS CORRETOS DA CARTEIRA DE PEDIDOS:
- `app/carteira/routes/`
- `app/carteira/services/`
- `app/carteira/utils/`
- `app/templates/carteira/css/`
- `app/templates/carteira/js/`
- `app/templates/carteira/agrupados_balanceado.html`
- `app/templates/carteira/dashboard.html`

### AGENTE LOGISTICO:
- `app/agente/` - Modulo principal (Claude Agent SDK)

---

# AGENTE LOGISTICO WEB

## Diferenca entre CLAUDE.md e system_prompt.md

| Arquivo | Publico-Alvo | Contexto | Proposito |
|---------|--------------|----------|-----------|
| **CLAUDE.md** | Claude Code (dev) | IDE/Terminal | Desenvolvimento do sistema |
| **system_prompt.md** | Agente Web | Chat web | Usuarios finais (logistica) |

**NAO MISTURAR**: Regras de negocio P1-P7 pertencem ao `system_prompt.md`, nao ao CLAUDE.md.

## Arquitetura do Agente

```
app/agente/
├── __init__.py
├── models.py              # AgentSession, AgentMemory, AgentEvent
├── routes.py              # API endpoints (/api/agente/...)
├── memory_tool.py         # DatabaseMemoryTool (Memory Tool Anthropic)
├── prompts/
│   └── system_prompt.md   # Prompt do agente web (usuarios finais)
└── hooks/
    ├── memory_agent.py    # Hook de memoria automatica
    └── README.md          # Documentacao dos hooks
```

## Prompt do Agente Web

**Arquivo**: `app/agente/prompts/system_prompt.md`

**Contem**:
- Regras de priorizacao P1-P7
- Regras de envio parcial
- Skills disponiveis para o agente
- Templates de resposta
- Validacoes obrigatorias (FOB, data_entrega, etc.)

**Versao atual**: 3.0.0 (estrutura XML com hierarquia de prioridade)

## Variaveis Injetadas no system_prompt.md

O arquivo `app/agente/sdk/client.py` substitui variaveis antes de enviar ao SDK.

**Codigo**: `client.py:234-261` (`_format_system_prompt`)

| Variavel | Valor Injetado | Fonte |
|----------|----------------|-------|
| `{data_atual}` | `14/12/2025 15:50` | `datetime.now()` |
| `{usuario_nome}` | `Rafael` | `current_user.nome` |
| `{user_id}` | `1` | `current_user.id` |

**Exemplo no system_prompt.md**:
```markdown
Data atual: {data_atual}
Usuario: {usuario_nome}
```

## Tabelas do Agente

| Tabela | Modelo | Campos Principais |
|--------|--------|-------------------|
| `agent_sessions` | AgentSession | session_id, user_id, title, data (JSONB com historico) |
| `agent_memories` | AgentMemory | user_id, path, content, is_directory |
| `agent_events` | AgentEvent | session_id, event_type, data (feedback, erros) |

---

# GATILHOS AUTOMATICOS DE PLUGINS E SKILLS

## MCP Servers

### Context7 (Documentacao de Bibliotecas)
**Usar quando:**
- Usuario pergunta "como fazer X com [biblioteca]?"
- Implementando feature com lib externa (Flask, SQLAlchemy, Pandas, etc.)
- Usuario menciona "documentacao de X"
- Preciso verificar API ou sintaxe de biblioteca

**Exemplo:**
```
Usuario: "Como fazer bulk insert com SQLAlchemy?"
→ resolve-library-id("sqlalchemy") → query-docs("/...", "bulk insert")
```

### Playwright (Testes Visuais - apenas local)
**Usar quando:**
- Usuario pede "testa a tela de..."
- Apos criar/modificar tela HTML
- Debug visual de componentes
- Screenshot de pagina local

**Limitacao:** Requer servidor local rodando (localhost). NAO funciona no Render.

## Skills de Logistica

| Gatilho | Skill | Exemplo |
|---------|-------|---------|
| Consulta estoque/pedidos | `gerindo-expedicao` | "quanto tem de palmito?" |
| Criar separacao | `gerindo-expedicao` | "cria separacao do VCD123" |
| Rastrear documentos | `rastreando-odoo` | "rastreia NF 12345" |
| Exportar dados | `exportando-arquivos` | "exporta em Excel" |
| Analise P1-P7 | `analise-carteira` | "analisa a carteira" |
| Explorar Odoo | `descobrindo-odoo-estrutura` | "campos do res.partner" |
| Validacao NF x PO | `validacao-nf-po` | "erro ao validar DFE", "modal POs nao abre" |
| Conciliar PO/Split | `conciliando-odoo-po` | "consolide POs", "crie PO conciliador", "execute split" |
| Recebimento Fisico | `recebimento-fisico-odoo` | "lote nao criou", "quality check falhou", "picking nao validou" |

## Skills de Desenvolvimento

| Gatilho | Skill | Exemplo |
|---------|-------|---------|
| Criar interface | `frontend-design` | "cria tela de cadastro" |
| Review de codigo | `code-review` | "/code-review" |
| Criar documentos | `document-skills` | "cria PDF/Excel/Word" |
| Novo app SDK | `agent-sdk-dev` | "novo app com Agent SDK" |

---

# SKILLS DISPONIVEIS

## Skills de Logistica
| Skill | Diretorio | Descricao |
|-------|-----------|-----------|
| `gerindo-expedicao` | `.claude/skills/gerindo-expedicao/` | Consulta pedidos, estoque, disponibilidade, cria separacoes |

## Skills de Integracao Odoo
| Skill | Diretorio | Descricao |
|-------|-----------|-----------|
| `rastreando-odoo` | `.claude/skills/rastreando-odoo/` | Rastreia fluxos documentais completos (NF compra/venda, PO, SO, titulos, conciliacao) |
| `executando-odoo-financeiro` | `.claude/skills/executando-odoo-financeiro/` | EXECUTA operacoes financeiras: criar pagamentos, reconciliar extratos, baixar titulos |
| `descobrindo-odoo-estrutura` | `.claude/skills/descobrindo-odoo-estrutura/` | Explorar campos/modelos nao mapeados |
| `integracao-odoo` | `.claude/skills/integracao-odoo/` | Criar novas integracoes, lancamentos fiscais |
| `validacao-nf-po` | `.claude/skills/validacao-nf-po/` | Validacao NF x PO (Fase 2): match, De-Para, divergencias, preview local |
| `conciliando-odoo-po` | `.claude/skills/conciliando-odoo-po/` | EXECUTA split/consolidacao de POs: criar PO Conciliador, ajustar saldos, vincular DFe |
| `recebimento-fisico-odoo` | `.claude/skills/recebimento-fisico-odoo/` | Recebimento Fisico (Fase 4): lotes, quality checks, processamento assincrono via RQ |

## Skills Utilitarias
| Skill | Diretorio | Descricao |
|-------|-----------|-----------|
| `memoria-usuario` | `.claude/skills/memoria-usuario/` | Salvar/recuperar preferencias entre sessoes |
| `exportando-arquivos` | `.claude/skills/exportando-arquivos/` | Gerar Excel, CSV, JSON para download |
| `lendo-arquivos` | `.claude/skills/lendo-arquivos/` | Processar Excel/CSV enviados |
| `frontend-design` | `.claude/skills/frontend-design/` | Criar interfaces web, componentes UI |
| `skill_creator` | `.claude/skills/skill_creator/` | Criar/atualizar skills

---

# SUBAGENTES DISPONIVEIS

## analista-carteira

**Arquivo**: `.claude/agents/analista-carteira.md`
**Modelo**: Opus (recomendado para tarefas complexas)
**Tools**: Read, Bash, Write, Edit, Glob, Grep
**Skills**: gerindo-expedicao

**Descricao**: Clone do Rafael para analise de carteira. Substitui analise diaria (2-3h/dia).

**Quando usar**:
- Analise COMPLETA da carteira de pedidos
- Decisoes de priorizacao P1-P7
- Comunicacao estruturada com PCP/Comercial
- Tarefas que requerem contexto profundo de regras de negocio

**Exemplo de invocacao** (via Task tool):
```python
Task(
    subagent_type="analista-carteira",
    prompt="Analise a carteira do Atacadao para semana que vem"
)
```

**Capacidades**:
- Algoritmo P1-P7 de priorizacao
- Decisao parcial vs aguardar
- Templates de comunicacao PCP/Comercial
- Conhecimento de leadtimes e gargalos
