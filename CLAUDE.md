# [PRECISION MODE] - MODO PRECISION ENGINEER ATIVO

**Ultima Atualizacao**: 13/12/2025

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

# MEMORIA PERSISTENTE DO USUARIO

## Arquitetura

A skill `memoria-usuario` usa a **Memory Tool da Anthropic** com armazenamento em banco de dados.
**Persiste entre deploys e sessoes.**

### Tabelas do Agente (app/agente/models.py)

| Tabela | Modelo | Descricao |
|--------|--------|-----------|
| `agent_memories` | AgentMemory | Memorias persistentes (preferencias, fatos, correcoes) |
| `agent_sessions` | AgentSession | Historico de conversas (mensagens, tokens, custos) |

### Estrutura de Paths Virtuais

Os paths sao **virtuais** (armazenados no banco, nao arquivos fisicos):
```
/memories/                      # Raiz (diretorio virtual)
/memories/preferences.xml       # Preferencias do usuario
/memories/context/company.xml   # Informacoes da empresa
/memories/learned/terms.xml     # Termos aprendidos
/memories/corrections/          # Correcoes de terminologia
```

### Comandos da Skill

```bash
# Visualizar todas as memorias
source .venv/bin/activate && python .claude/skills/memoria-usuario/scripts/memoria.py view --user-id 1

# Visualizar path especifico
python .claude/skills/memoria-usuario/scripts/memoria.py view --user-id 1 --path /memories/preferences.xml

# Salvar memoria
python .claude/skills/memoria-usuario/scripts/memoria.py save --user-id 1 --path /memories/preferences.xml --content "<preferencias>...</preferencias>"

# Atualizar (str_replace)
python .claude/skills/memoria-usuario/scripts/memoria.py update --user-id 1 --path /memories/preferences.xml --old "texto" --new "novo"

# Deletar
python .claude/skills/memoria-usuario/scripts/memoria.py delete --user-id 1 --path /memories/preferences.xml
```

### Gatilhos para SALVAR automaticamente:
| Usuario diz... | Path Virtual |
|----------------|--------------|
| "Prefiro respostas curtas" | `/memories/preferences.xml` |
| "Sou gerente de logistica" | `/memories/context/user.xml` |
| "Aqui chamamos de X, nao Y" | `/memories/corrections/terms.xml` |
| "Sempre faco isso antes de..." | `/memories/learned/patterns.xml` |

### User ID padrao: 1 (Rafael - dono do projeto)

---

# INDICE DE REFERENCIAS

## Onde Buscar Informacao

| Preciso de... | Documento | Quando Usar |
|---------------|-----------|-------------|
| Campos de Carteira/Separacao | **Este arquivo (abaixo)** | Desenvolvendo features principais |
| Campos de outros modelos | `.claude/references/MODELOS_CAMPOS.md` | Pedido, Embarque, Faturamento, DespesaExtra, ContasAReceber |
| Regras de negocio detalhadas | `.claude/references/REGRAS_NEGOCIO.md` | Grupos CNPJ, bonificacao, roteirizacao, calculos |
| Queries e mapeamentos SQL | `.claude/references/QUERIES_MAPEAMENTO.md` | Consultas SQL, JOINs entre tabelas |
| Ajustes e fixes pendentes | `.claude/references/AJUSTES.md` | Bugs conhecidos, melhorias planejadas |
| Consultas estoque/carteira | Skill `gerindo-expedicao` | Perguntas sobre disponibilidade, pedidos, estoque |
| Integracao Odoo | Skill `integracao-odoo` | Lancamentos fiscais, CTe, 16 etapas |

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

# SKILLS DISPONIVEIS

## Skills de Logistica
| Skill | Diretorio | Descricao |
|-------|-----------|-----------|
| `gerindo-expedicao` | `.claude/skills/gerindo-expedicao/` | Consulta pedidos, estoque, disponibilidade, cria separacoes |

## Skills de Integracao Odoo
| Skill | Diretorio | Descricao |
|-------|-----------|-----------|
| `rastreando-odoo` | `.claude/skills/rastreando-odoo/` | Rastreia fluxos documentais completos (NF compra/venda, PO, SO, titulos, conciliacao) |
| `descobrindo-odoo-estrutura` | `.claude/skills/descobrindo-odoo-estrutura/` | Explorar campos/modelos nao mapeados |
| `integracao-odoo` | `.claude/skills/integracao-odoo/` | Criar novas integracoes, lancamentos fiscais |

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
