# Claude AI Lite - Documentação do Módulo

## Visão Geral

Módulo de IA conversacional para o sistema de fretes, permitindo consultas em linguagem natural sobre pedidos, produtos e criação de separações.

**Criado em:** Novembro/2025
**Última atualização:** 22/11/2025

---

## Estrutura do Módulo

```
app/claude_ai_lite/
├── README.md                 # Esta documentação
├── __init__.py               # Inicialização e registro do blueprint
├── core.py                   # Orquestrador principal (max 100 linhas)
├── claude_client.py          # Cliente da API Claude (Anthropic)
├── config.py                 # Configurações (modelo, tokens, cache)
├── routes.py                 # Endpoints Flask
│
├── actions/                  # Handlers de ESCRITA (criar, modificar)
│   ├── __init__.py
│   └── separacao_actions.py  # Criar separações via conversa
│
└── domains/                  # Domínios de LEITURA (consultas)
    ├── __init__.py           # Registro de loaders
    ├── base.py               # BaseLoader abstrato
    │
    └── carteira/             # Domínio da carteira de pedidos
        ├── __init__.py
        ├── prompts.py        # Prompts específicos (não usado atualmente)
        │
        ├── loaders/          # Loaders de consulta
        │   ├── __init__.py
        │   ├── pedidos.py          # Consulta pedidos
        │   ├── produtos.py         # Consulta produtos
        │   └── disponibilidade.py  # Análise de quando enviar
        │
        └── services/         # Serviços de negócio
            ├── __init__.py
            ├── opcoes_envio.py     # Gera opções A/B/C de envio
            └── criar_separacao.py  # Cria separações no banco
```

---

## Fluxo de Funcionamento

```
┌─────────────────────────────────────────────────────────────────┐
│                         USUÁRIO                                  │
│                   "Quando posso enviar VCD123?"                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      routes.py                                   │
│  POST /claude-lite/api/query                                    │
│  - Recebe consulta                                              │
│  - Identifica usuário (current_user)                            │
│  - Chama core.processar_consulta()                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                       core.py                                    │
│  processar_consulta()                                           │
│  1. Claude identifica intenção e entidades                      │
│  2. Se dominio="acao" → actions/                                │
│  3. Senão → roteia para loader correto                          │
│  4. Busca dados                                                 │
│  5. Claude elabora resposta                                     │
└─────────────────────────────────────────────────────────────────┘
                              │
              ┌───────────────┴───────────────┐
              ▼                               ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│     domains/loaders/     │     │       actions/          │
│   (LEITURA - consultas)  │     │   (ESCRITA - ações)     │
│                         │     │                         │
│  - PedidosLoader        │     │  - processar_acao_      │
│  - ProdutosLoader       │     │    separacao()          │
│  - DisponibilidadeLoader│     │                         │
└─────────────────────────┘     └─────────────────────────┘
```

---

## Endpoints da API

### 1. Consulta Principal
```
POST /claude-lite/api/query
Content-Type: application/json

{
    "query": "Quando posso enviar o pedido VCD2564344?",
    "usar_claude": true  // opcional, default true
}

Response:
{
    "success": true,
    "response": "O pedido VCD2564344 pode ser enviado em 27/11/2025...",
    "source": "claude_ai_lite",
    "timestamp": "2025-11-22T21:30:00"
}
```

### 2. Consulta Direta (sem NLP)
```
POST /claude-lite/api/query/direct
{
    "valor": "VCD2564344",
    "campo": "num_pedido",
    "dominio": "carteira"
}
```

### 3. Criar Separação
```
POST /claude-lite/api/action/criar-separacao
{
    "num_pedido": "VCD2564344",
    "opcao": "A"  // A, B ou C
}
```

### 4. Health Check
```
GET /claude-lite/health
```

---

## Intenções Reconhecidas

O Claude identifica a intenção do usuário:

| Intenção | Domínio | Exemplo |
|----------|---------|---------|
| `consultar_status` | carteira | "Status do pedido VCD123" |
| `buscar_pedido` | carteira | "Pedido VCD123" |
| `buscar_produto` | carteira | "Azeitona verde na carteira" |
| `analisar_disponibilidade` | carteira | "Quando posso enviar VCD123?" |
| `escolher_opcao` | acao | "Opção A" |
| `criar_separacao` | acao | "Criar separação opção A do pedido VCD123" |
| `confirmar_acao` | acao | "Sim, confirmo" |

---

## Loaders Disponíveis

### PedidosLoader (`carteira`)
- Busca pedidos por: `num_pedido`, `cnpj_cpf`, `raz_social_red`, `pedido_cliente`
- Retorna: dados do pedido, cliente, status de separação

### ProdutosLoader (`carteira_produto`)
- Busca por: `nome_produto`, `cod_produto`
- Retorna: produtos na carteira agrupados

### DisponibilidadeLoader (`carteira_disponibilidade`)
- Busca por: `num_pedido`
- Retorna: **Opções de envio A/B/C** com análise de estoque

---

## Opções de Envio (A/B/C)

Quando o usuário pergunta "quando posso enviar?", o sistema gera até 3 opções:

| Opção | Descrição |
|-------|-----------|
| **A** | Envio Total - aguarda todos os itens |
| **B** | Envio Parcial (-1 item gargalo) |
| **C** | Envio Parcial (-2 itens gargalo) |

Cada opção contém:
- Data de envio
- Valor e percentual do pedido
- Lista de itens incluídos/excluídos

---

## Validações na Criação de Separação

Antes de criar, o sistema valida:

1. **Separação existente**: Não permite duplicar se já existe separação não faturada
2. **Saldo disponível**: Verifica saldo na CarteiraPrincipal menos separações existentes

---

## Campos Importantes

### Separação criada pelo Claude
- `separacao_lote_id`: Padrão `CLAUDE-YYYYMMDDHHMMSS-XXXXXX`
- `criado_por`: Nome do usuário que solicitou
- `criado_em`: Data/hora da criação

---

## Como Adicionar Novo Loader

1. Criar arquivo em `domains/carteira/loaders/novo_loader.py`:
```python
from ...base import BaseLoader

class NovoLoader(BaseLoader):
    DOMINIO = "carteira"
    CAMPOS_BUSCA = ["campo1", "campo2"]

    def buscar(self, valor: str, campo: str) -> Dict[str, Any]:
        # Implementar busca
        pass

    def formatar_contexto(self, dados: Dict[str, Any]) -> str:
        # Formatar para o Claude
        pass
```

2. Registrar em `domains/carteira/__init__.py`:
```python
from .loaders.novo_loader import NovoLoader
registrar_dominio("nome_dominio", NovoLoader)
```

3. Adicionar roteamento em `core.py` se necessário

---

## Como Adicionar Nova Action

1. Criar função em `actions/separacao_actions.py` ou novo arquivo
2. Registrar em `actions/__init__.py`
3. Adicionar tratamento em `core.py`:
```python
if dominio_base == "acao":
    return processar_nova_acao(intencao_tipo, entidades, usuario=usuario)
```

4. Adicionar intenção em `claude_client.py` no prompt de identificação

---

## Configuração

Arquivo `config.py`:
```python
CLAUDE_MODEL = "claude-3-haiku-20240307"  # Modelo rápido e barato
MAX_TOKENS = 1024
CACHE_TTL = 300  # 5 minutos
```

Variável de ambiente necessária:
```
ANTHROPIC_API_KEY=sk-ant-...
```

---

## Regras de Implementação

1. **core.py**: Máximo 100 linhas (atualmente ~110)
2. **Loaders**: Máximo 150 linhas cada
3. **Modularização**:
   - `loaders/` = Consultas (leitura)
   - `services/` = Lógica de negócio
   - `actions/` = Handlers de ações (escrita)
4. **Imports**: Evitar imports circulares, usar imports dentro de funções se necessário

---

## Scripts de Migração Relacionados

- `scripts/migrations/adicionar_campo_criado_por_separacao.py` - Campo criado_por
- `scripts/migrations/adicionar_campo_criado_por_separacao.sql` - Para Render

---

## Histórico de Desenvolvimento

### 22/11/2025
- Criação do módulo base
- Implementação de loaders: Pedidos, Produtos, Disponibilidade
- Opções de envio A/B/C
- Criação de separações via conversa
- Validações de duplicidade e saldo
- Campo `criado_por` na Separação
- Mensagens amigáveis e orientativas
