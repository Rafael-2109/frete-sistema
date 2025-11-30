# Projeto: Implementação do Claude Agent SDK

**Versão:** 1.0
**Data:** 30/11/2025
**Modelo:** `claude-opus-4-5-20251101`
**Substitui:** `app/claude_ai_lite/` (será removido)

---

## 1. VISÃO GERAL

### 1.1 Objetivo
Implementar o Claude Agent SDK oficial da Anthropic para criar um agente logístico inteligente que:
- Responde consultas em linguagem natural sobre pedidos, estoque e separações
- Executa ações (criar separações) com confirmação do usuário
- Mantém contexto conversacional entre mensagens
- Usa skills especializadas do domínio logístico

### 1.2 Decisões de Arquitetura

| Decisão | Escolha | Justificativa |
|---------|---------|---------------|
| Ambiente | Flask integrado | Reutiliza infraestrutura existente |
| Interface | Frontend existente (chat) | Mínima alteração de UX |
| Permissões | Leitura + Criação separações | Segurança operacional |
| Sessões | PostgreSQL + Redis | Persistência + Performance |
| Modelo | Opus exclusivo | Qualidade máxima |
| Subagentes | Dinâmico (Claude decide) | Flexibilidade |

### 1.3 Requisitos da Documentação Anthropic

Baseado nas URLs oficiais consultadas:

| Recurso | Requisito | Status |
|---------|-----------|--------|
| Streaming | **OBRIGATÓRIO** para custom tools | ✅ Planejado |
| MCP em processo | `createSdkMcpServer` + `@tool` | ✅ Planejado |
| Skills | `settingSources: ["project"]` | ✅ Existe em .claude/skills |
| Permissions | Callback `canUseTool` | ✅ Planejado |
| Sessions | `session_id` + `resume` | ✅ Planejado |
| System Prompts | Via CLAUDE.md ou append | ✅ Planejado |

---

## 2. ESTRUTURA DE DIRETÓRIOS

```
app/
├── agente/                           # 🆕 NOVO MÓDULO (Agent SDK)
│   ├── __init__.py                   # Blueprint Flask + init
│   ├── PROJETO_AGENT_SDK.md          # Este documento
│   │
│   ├── config/                       # Configurações
│   │   ├── __init__.py
│   │   ├── settings.py               # Configurações do agente
│   │   └── permissions.py            # Callback canUseTool
│   │
│   ├── sdk/                          # Core do Agent SDK
│   │   ├── __init__.py
│   │   ├── client.py                 # Wrapper do SDK (streaming)
│   │   ├── session_manager.py        # Gerenciamento de sessões
│   │   └── cost_tracker.py           # Rastreamento de custos
│   │
│   ├── tools/                        # Custom Tools (MCP em processo)
│   │   ├── __init__.py
│   │   ├── server.py                 # MCP Server com @tool
│   │   ├── carteira_tools.py         # Tools de consulta carteira
│   │   ├── estoque_tools.py          # Tools de consulta estoque
│   │   ├── separacao_tools.py        # Tools de criação separação
│   │   └── prazo_tools.py            # Tools de cálculo de prazo
│   │
│   ├── schemas/                      # Pydantic Schemas (Structured Outputs)
│   │   ├── __init__.py
│   │   ├── pedido.py                 # Schema de pedido
│   │   ├── estoque.py                # Schema de estoque
│   │   ├── disponibilidade.py        # Schema de análise disponibilidade
│   │   └── resposta.py               # Schema de resposta do agente
│   │
│   ├── prompts/                      # System Prompts
│   │   ├── __init__.py
│   │   └── system_prompt.md          # Prompt do agente logístico
│   │
│   ├── sessions/                     # Persistência de sessões
│   │   ├── __init__.py
│   │   ├── redis_store.py            # Armazenamento Redis
│   │   └── postgres_store.py         # Armazenamento PostgreSQL
│   │
│   └── routes.py                     # Endpoints Flask
│
├── .claude/
│   ├── skills/
│   │   └── agente-logistico/         # ✅ JÁ EXISTE
│   │       ├── SKILL.md
│   │       ├── TABELAS.md
│   │       ├── REGRAS_NEGOCIO.md
│   │       ├── reference/
│   │       │   └── QUERIES.md
│   │       └── scripts/
│   │           ├── analisando_disponibilidade.py
│   │           ├── consultando_pedidos.py
│   │           ├── consultando_estoque.py
│   │           ├── calculando_prazo.py
│   │           └── analisando_programacao.py
│   │
│   ├── agents/                       # 🆕 Subagentes (se necessário)
│   │   └── analisador-complexo.md    # Para análises multi-UF
│   │
│   └── commands/                     # 🆕 Slash commands customizados
│       └── consultar.md
```

---

## 3. ESPECIFICAÇÃO DAS CUSTOM TOOLS

### 3.1 Padrão Anthropic para Tools

Conforme documentação oficial, cada tool deve ter:

```python
@tool
def nome_da_tool(parametro: str) -> dict:
    """
    Descrição detalhada (1-2 frases).

    Quando usar: [cenários de uso]
    Quando NÃO usar: [cenários a evitar]

    Returns:
        Dict com campos: campo1, campo2, campo3
        Limite padrão: N registros
    """
```

### 3.2 Tools Planejadas

#### Tool 1: `consultar_pedidos`

```python
@tool
def consultar_pedidos(
    cliente: str = None,
    num_pedido: str = None,
    cod_uf: str = None,
    atrasados: bool = False,
    limite: int = 50
) -> dict:
    """
    Busca pedidos na carteira de vendas.

    Use para: consultas por cliente (nome parcial), número do pedido (exato),
    UF ou pedidos atrasados.
    NÃO use para: pedidos já faturados (use consultar_faturamento).

    Args:
        cliente: Nome parcial do cliente (ex: "Atacadão", "Assai")
        num_pedido: Número exato do pedido (ex: "VCD2509030")
        cod_uf: UF de destino (ex: "SP", "RJ")
        atrasados: Se True, filtra pedidos com expedição < hoje
        limite: Máximo de registros (default: 50)

    Returns:
        Dict com:
        - success: bool
        - total: int
        - dados: List[{num_pedido, raz_social_red, valor_saldo, qtd_itens, expedicao}]
    """
```

#### Tool 2: `analisar_disponibilidade`

```python
@tool
def analisar_disponibilidade(
    num_pedido: str = None,
    cliente: str = None,
    cod_uf: str = None,
    data_envio: str = None
) -> dict:
    """
    Analisa disponibilidade de estoque para pedidos.

    Use para: verificar quando pedido estará disponível, simular envio em data
    específica, identificar gargalos de estoque.
    NÃO use para: consultas simples de status (use consultar_pedidos).

    Args:
        num_pedido: Número do pedido específico
        cliente: Nome do cliente (agrupa todos os pedidos)
        cod_uf: Filtro por UF
        data_envio: Data para simular envio (formato: DD/MM/YYYY ou "amanha")

    Returns:
        Dict com:
        - success: bool
        - analise: {total_itens, itens_disponiveis, data_disponibilidade_total}
        - opcoes: List[{codigo, titulo, data_envio, valor, percentual, itens}]
        - gargalos: List[{cod_produto, nome_produto, falta, data_disponivel}]
    """
```

#### Tool 3: `consultar_estoque`

```python
@tool
def consultar_estoque(
    produto: str = None,
    cod_produto: str = None,
    dias_projecao: int = 7,
    apenas_ruptura: bool = False
) -> dict:
    """
    Consulta estoque atual e projeção futura de produtos.

    Use para: verificar se produto chegou, projetar estoque futuro,
    identificar rupturas previstas.
    NÃO use para: consultar pedidos de um produto (use consultar_pedidos).

    Args:
        produto: Nome parcial do produto (ex: "palmito", "azeitona")
        cod_produto: Código exato do produto
        dias_projecao: Dias para projetar estoque (default: 7)
        apenas_ruptura: Se True, retorna apenas produtos com ruptura prevista

    Returns:
        Dict com:
        - success: bool
        - dados: List[{cod_produto, nome_produto, estoque_atual, projecao_7d,
                       data_ruptura, demanda_carteira}]
    """
```

#### Tool 4: `calcular_prazo_entrega`

```python
@tool
def calcular_prazo_entrega(
    num_pedido: str = None,
    cidade: str = None,
    uf: str = None,
    data_embarque: str = None
) -> dict:
    """
    Calcula prazo de entrega considerando transportadoras disponíveis.

    Use para: estimar quando pedido chegará ao cliente, comparar
    opções de transportadoras.

    Args:
        num_pedido: Número do pedido (usa cidade/UF do pedido)
        cidade: Cidade de destino (alternativa ao num_pedido)
        uf: UF de destino
        data_embarque: Data de embarque (default: amanhã)

    Returns:
        Dict com:
        - success: bool
        - opcoes: List[{transportadora, lead_time, data_entrega, custo_estimado}]
    """
```

#### Tool 5: `criar_separacao`

```python
@tool
def criar_separacao(
    num_pedido: str,
    opcao: str = None,
    data_expedicao: str = None,
    itens: list = None,
    confirmar: bool = False
) -> dict:
    """
    Cria separação para um pedido.

    IMPORTANTE: Requer confirmação do usuário (confirmar=True).
    Use após analisar_disponibilidade que retorna opções A, B, C.

    Args:
        num_pedido: Número do pedido
        opcao: Código da opção (A, B, C) retornada por analisar_disponibilidade
        data_expedicao: Data de expedição (formato: DD/MM/YYYY)
        itens: Lista específica de itens (alternativa à opção)
        confirmar: DEVE ser True para executar (segurança)

    Returns:
        Dict com:
        - success: bool
        - separacao_lote_id: str (se criado)
        - mensagem: str
        - itens_separados: int
        - valor_total: float
    """
```

---

## 4. SCHEMAS PYDANTIC (Structured Outputs)

### 4.1 Schema de Resposta do Agente

```python
from pydantic import BaseModel, Field
from typing import List, Optional, Literal
from datetime import date

class ItemPedido(BaseModel):
    """Item de um pedido na carteira."""
    num_pedido: str = Field(description="Número do pedido")
    cod_produto: str = Field(description="Código do produto")
    nome_produto: str = Field(description="Nome do produto")
    quantidade: float = Field(description="Quantidade pendente")
    valor: float = Field(description="Valor do item")
    disponivel: bool = Field(description="Se está disponível em estoque")

class AnalisePedido(BaseModel):
    """Análise de disponibilidade de um pedido."""
    num_pedido: str
    cliente: str
    valor_total: float
    total_itens: int
    itens_disponiveis: int
    percentual_disponivel: float
    data_disponibilidade_total: Optional[date]
    gargalos: List[str] = Field(default_factory=list)

class OpcaoEnvio(BaseModel):
    """Opção de envio gerada pela análise."""
    codigo: Literal["A", "B", "C", "D", "E"]
    titulo: str
    data_envio: date
    dias_para_envio: int
    valor: float
    percentual: float
    qtd_itens: int
    itens: List[ItemPedido]

class RespostaAgente(BaseModel):
    """Resposta estruturada do agente."""
    sucesso: bool
    tipo_resposta: Literal["consulta", "analise", "acao", "clarificacao"]
    mensagem: str
    dados: Optional[List[dict]] = None
    opcoes: Optional[List[OpcaoEnvio]] = None
    proxima_acao: Optional[str] = None
```

---

## 5. GERENCIAMENTO DE SESSÕES

### 5.1 Estrutura da Sessão

```python
class AgentSession:
    """Sessão do agente com persistência híbrida."""

    session_id: str           # UUID único
    user_id: int              # ID do usuário Flask
    created_at: datetime
    last_activity: datetime

    # Contexto conversacional
    messages: List[dict]      # Histórico de mensagens
    current_context: dict     # Entidades ativas (cliente, pedido, etc)

    # Estado do agente
    pending_action: dict      # Ação aguardando confirmação
    last_tool_results: dict   # Resultados da última tool

    # Métricas
    total_tokens: int
    total_cost_usd: float
    tools_called: List[str]
```

### 5.2 Fluxo de Persistência

```
1. Nova mensagem chega
   │
   ├─► Redis: Busca sessão (cache, TTL 1h)
   │   │
   │   ├─► HIT: Usa sessão do Redis
   │   │
   │   └─► MISS: PostgreSQL: Busca sessão
   │       │
   │       ├─► ENCONTROU: Carrega + Cacheia no Redis
   │       │
   │       └─► NÃO ENCONTROU: Cria nova sessão
   │
   ├─► Processa mensagem com Agent SDK
   │
   ├─► Atualiza sessão (context, messages, metrics)
   │
   └─► Persiste:
       ├─► Redis: Atualiza cache (sempre)
       └─► PostgreSQL: Persiste async (a cada N mensagens ou timeout)
```

---

## 6. INTEGRAÇÃO FLASK

### 6.1 Blueprint e Rotas

```python
# app/agente/routes.py

from flask import Blueprint, request, jsonify, Response
from flask_login import login_required, current_user

agente_bp = Blueprint('agente', __name__, url_prefix='/agente')

@agente_bp.route('/api/chat', methods=['POST'])
@login_required
async def chat():
    """
    Endpoint principal de chat com streaming.

    POST /agente/api/chat
    {
        "message": "Tem pedido pendente pro Atacadão?",
        "session_id": "uuid-opcional"  // Se omitido, usa/cria sessão do usuário
    }

    Response: Server-Sent Events (SSE)
    """
    pass

@agente_bp.route('/api/chat/sync', methods=['POST'])
@login_required
def chat_sync():
    """
    Endpoint síncrono (fallback sem streaming).
    Mesmo payload, retorna JSON completo.
    """
    pass

@agente_bp.route('/api/session', methods=['GET'])
@login_required
def get_session():
    """Retorna estado atual da sessão."""
    pass

@agente_bp.route('/api/session/clear', methods=['POST'])
@login_required
def clear_session():
    """Limpa sessão do usuário."""
    pass

@agente_bp.route('/api/action/confirm', methods=['POST'])
@login_required
def confirm_action():
    """
    Confirma ação pendente (ex: criar separação).

    POST /agente/api/action/confirm
    {
        "action_id": "uuid-da-acao",
        "confirmed": true
    }
    """
    pass
```

### 6.2 Registro do Blueprint

```python
# app/__init__.py (adicionar)

def create_app():
    # ... código existente ...

    # Registrar blueprint do agente
    from app.agente import agente_bp
    app.register_blueprint(agente_bp)

    return app
```

---

## 7. SYSTEM PROMPT

### 7.1 Estrutura do Prompt

```markdown
# app/agente/prompts/system_prompt.md

<background_information>
Você é um assistente logístico especializado no sistema de fretes.
Sua função é ajudar usuários a consultar pedidos, verificar estoque,
analisar disponibilidade e criar separações.

Data atual: {data_atual}
Usuário: {usuario_nome}
</background_information>

<instructions>
## Comportamento

1. SEMPRE use as ferramentas disponíveis para buscar dados reais
2. NUNCA invente informações - se não encontrar, informe claramente
3. Para criar separações, SEMPRE peça confirmação do usuário
4. Mantenha respostas concisas e focadas no que foi perguntado

## Quando Pedir Clarificação

- Cliente ambíguo (ex: "Atacadão" tem várias lojas)
- Pedido não especificado quando há múltiplos
- Data não informada para análises temporais

## Formato de Resposta

- Use markdown para formatação
- Tabelas para listas de dados
- Emojis para status (✅ disponível, ❌ falta, ⏳ aguardar)
- Sempre inclua totais e resumos
</instructions>

## Ferramentas Disponíveis

- `consultar_pedidos`: Busca pedidos por cliente, número ou UF
- `analisar_disponibilidade`: Verifica estoque e gera opções de envio
- `consultar_estoque`: Consulta estoque atual e projeções
- `calcular_prazo_entrega`: Estima prazos por transportadora
- `criar_separacao`: Cria separação (requer confirmação)

## Conhecimento do Domínio

{conhecimento_negocio}
```

---

## 8. FLUXO DE EXECUÇÃO

### 8.1 Diagrama de Sequência

```
┌─────────┐     ┌─────────┐     ┌──────────┐     ┌───────┐
│ Frontend│     │  Flask  │     │ AgentSDK │     │ Tools │
└────┬────┘     └────┬────┘     └────┬─────┘     └───┬───┘
     │               │               │               │
     │ POST /chat    │               │               │
     │──────────────>│               │               │
     │               │               │               │
     │               │ get_session() │               │
     │               │──────────────>│               │
     │               │               │               │
     │               │ stream_response()             │
     │               │──────────────>│               │
     │               │               │               │
     │               │               │ tool_call     │
     │               │               │──────────────>│
     │               │               │               │
     │               │               │   result      │
     │               │               │<──────────────│
     │               │               │               │
     │  SSE: text    │               │               │
     │<──────────────│<──────────────│               │
     │               │               │               │
     │  SSE: done    │               │               │
     │<──────────────│               │               │
     │               │               │               │
     │               │ save_session()│               │
     │               │──────────────>│               │
```

### 8.2 Fluxo de Confirmação de Ação

```
Usuário: "Crie separação do VCD123 opção A"
     │
     ▼
Agente: Analisa e prepara ação
     │
     ▼
Agente: "Vou criar separação do VCD123 com 15 itens, R$ 45.000.
        Confirma? (responda 'sim' ou 'confirmar')"
     │
     ├─► pending_action salvo na sessão
     │
     ▼
Usuário: "sim"
     │
     ▼
Agente: Detecta confirmação → Executa criar_separacao(confirmar=True)
     │
     ▼
Agente: "✅ Separação criada! Lote: SEP-2024-001234"
```

---

## 9. RASTREAMENTO DE CUSTOS

### 9.1 Estrutura de Métricas

```python
class CostMetrics:
    """Métricas de custo por sessão/usuário."""

    session_id: str
    user_id: int

    # Por requisição
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cost_usd: float

    # Acumulado na sessão
    session_total_tokens: int
    session_total_cost: float

    # Por ferramenta
    tools_usage: Dict[str, int]  # {tool_name: call_count}
```

### 9.2 Cálculo de Custo (Opus)

```python
# Preços Opus (por 1M tokens) - verificar valores atuais
OPUS_INPUT_PRICE = 15.00   # USD por 1M tokens de entrada
OPUS_OUTPUT_PRICE = 75.00  # USD por 1M tokens de saída

def calcular_custo(input_tokens: int, output_tokens: int) -> float:
    input_cost = (input_tokens / 1_000_000) * OPUS_INPUT_PRICE
    output_cost = (output_tokens / 1_000_000) * OPUS_OUTPUT_PRICE
    return input_cost + output_cost
```

---

## 10. PERMISSÕES E SEGURANÇA

### 10.1 Callback canUseTool

```python
# app/agente/config/permissions.py

from typing import Dict, Any

# Tools que requerem confirmação explícita
TOOLS_REQUIRE_CONFIRMATION = {
    'criar_separacao',
}

# Tools de apenas leitura (sempre permitidas)
TOOLS_READ_ONLY = {
    'consultar_pedidos',
    'consultar_estoque',
    'analisar_disponibilidade',
    'calcular_prazo_entrega',
}

async def can_use_tool(
    tool_name: str,
    tool_input: Dict[str, Any],
    session: 'AgentSession'
) -> bool:
    """
    Callback de permissão para uso de ferramentas.

    Retorna True se a ferramenta pode ser usada.
    """
    # Tools de leitura: sempre permitidas
    if tool_name in TOOLS_READ_ONLY:
        return True

    # Tools de escrita: verificar confirmação
    if tool_name in TOOLS_REQUIRE_CONFIRMATION:
        # Verifica se há confirmação pendente para esta ação
        if not tool_input.get('confirmar'):
            # Salva ação pendente para confirmação
            session.pending_action = {
                'tool': tool_name,
                'input': tool_input,
                'awaiting_confirmation': True
            }
            return False  # Não executa ainda
        return True

    return False  # Tool desconhecida: nega por segurança
```

---

## 11. CHECKLIST DE IMPLEMENTAÇÃO

### Fase 1: Fundação (Semana 1)
- [ ] Criar estrutura de diretórios `app/agente/`
- [ ] Implementar `config/settings.py` com configurações
- [ ] Implementar `sdk/client.py` wrapper do Agent SDK
- [ ] Criar `prompts/system_prompt.md`
- [ ] Testar conexão básica com API Anthropic

### Fase 2: Tools (Semana 2)
- [ ] Implementar `tools/server.py` com MCP em processo
- [ ] Implementar `consultar_pedidos` tool
- [ ] Implementar `analisar_disponibilidade` tool
- [ ] Implementar `consultar_estoque` tool
- [ ] Implementar `calcular_prazo_entrega` tool
- [ ] Testar cada tool isoladamente

### Fase 3: Sessões (Semana 3)
- [ ] Implementar `sessions/redis_store.py`
- [ ] Implementar `sessions/postgres_store.py`
- [ ] Implementar `sdk/session_manager.py`
- [ ] Testar persistência e recuperação de sessões

### Fase 4: Integração Flask (Semana 4)
- [ ] Implementar `routes.py` com endpoints
- [ ] Implementar streaming SSE
- [ ] Integrar com autenticação Flask-Login
- [ ] Adaptar frontend existente

### Fase 5: Ações e Segurança (Semana 5)
- [ ] Implementar `criar_separacao` tool
- [ ] Implementar `config/permissions.py`
- [ ] Implementar fluxo de confirmação
- [ ] Testar cenários de segurança

### Fase 6: Otimização (Semana 6)
- [ ] Implementar `sdk/cost_tracker.py`
- [ ] Implementar schemas Pydantic
- [ ] Testes de integração completos
- [ ] Remover `app/claude_ai_lite/`

---

## 12. MIGRAÇÃO DO FRONTEND

### 12.1 Mudanças Necessárias

O frontend existente (`app/templates/claude_ai/chat.html`) precisará:

1. **Alterar endpoint**: `/claude-ai/api/query` → `/agente/api/chat`
2. **Suportar SSE**: Adicionar EventSource para streaming
3. **Confirmação de ações**: Modal para confirmar separações

### 12.2 Exemplo de Código SSE

```javascript
async function sendMessageWithStreaming(message) {
    const eventSource = new EventSource(
        `/agente/api/chat?message=${encodeURIComponent(message)}&session_id=${sessionId}`
    );

    eventSource.onmessage = function(event) {
        const data = JSON.parse(event.data);

        if (data.type === 'text') {
            appendToResponse(data.content);
        } else if (data.type === 'tool_call') {
            showToolIndicator(data.tool_name);
        } else if (data.type === 'action_pending') {
            showConfirmationModal(data.action);
        } else if (data.type === 'done') {
            eventSource.close();
            updateMetrics(data.metrics);
        }
    };

    eventSource.onerror = function(error) {
        eventSource.close();
        showError('Erro na conexão');
    };
}
```

---

## 13. DEPENDÊNCIAS

### 13.1 Novas Dependências Python

```txt
# requirements.txt (adicionar)

anthropic>=0.40.0          # SDK oficial da Anthropic
pydantic>=2.0.0            # Structured outputs
redis>=5.0.0               # Cache de sessões (já existe?)
```

### 13.2 Variáveis de Ambiente

```env
# .env (adicionar/verificar)

ANTHROPIC_API_KEY=sk-ant-...
AGENT_MODEL=claude-opus-4-5-20251101
AGENT_MAX_TOKENS=4096
AGENT_TEMPERATURE=0.7

# Redis (se não existir)
REDIS_URL=redis://localhost:6379/0
```

---

## 14. QUESTÕES PENDENTES PARA O USUÁRIO

Antes de iniciar a implementação, preciso de algumas confirmações:

### 14.1 Redis
- [ ] Redis já está configurado no projeto?
- [ ] Se não, posso usar apenas PostgreSQL para sessões?

### 14.2 Autenticação
- [ ] O `current_user` do Flask-Login tem campo `id` e `nome`?
- [ ] Há alguma restrição de permissão por tipo de usuário?

### 14.3 Frontend
- [ ] Posso modificar o template `chat.html` existente?
- [ ] Ou prefere um novo template em `/agente/chat.html`?

### 14.4 Remoção do claude_ai_lite
- [ ] Posso remover o módulo após a migração?
- [ ] Há dependências externas que usam os endpoints antigos?

---

*Documento gerado em 30/11/2025*
*Baseado na documentação oficial da Anthropic Agent SDK*
