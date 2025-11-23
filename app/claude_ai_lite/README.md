# Claude AI Lite - Documentação do Módulo

## Visão Geral

Módulo de IA conversacional para o sistema de fretes, permitindo consultas em linguagem natural sobre pedidos, produtos e criação de separações.

**Criado em:** Novembro/2025
**Última atualização:** 23/11/2025
**Versão:** 2.0 (Arquitetura de Capacidades)

### Funcionalidades Principais
- Consultas por pedido, cliente, produto
- Análise de disponibilidade de envio (opções A/B/C)
- Consultas por rota, sub-rota e UF
- Análise de estoque e rupturas
- Identificação de gargalos de estoque
- Criação de separações via chat
- **Memória de Conversa** - Lembra das últimas 40 mensagens
- **Aprendizado Permanente** - "Lembre que...", "Esqueça que...", "O que você sabe?"

---

## Arquitetura v2.0 (Nova)

A arquitetura foi refatorada para ser **escalável e modular**, usando o padrão de **Capacidades Auto-Registráveis**.

### Conceito Principal

Cada **Capacidade** é uma unidade independente que:
- Define suas próprias intenções (quando deve ser ativada)
- Define seus campos de busca
- Executa a lógica de negócio
- Formata a resposta

**Benefícios:**
- Adicionar nova feature = criar 1 arquivo
- Prompts gerados automaticamente
- Sem if/elif crescente
- Fácil de testar isoladamente

---

## Estrutura do Módulo v2.0

```
app/claude_ai_lite/
├── README.md                 # Esta documentação
├── __init__.py               # Inicialização e exports
├── core.py                   # Redirecionador (compatibilidade)
├── claude_client.py          # Cliente da API Claude
├── routes.py                 # Endpoints Flask
├── routes_admin.py           # Endpoints de administração
├── memory.py                 # Memória de conversas
├── learning.py               # Aprendizado permanente
├── models.py                 # Modelos de dados
│
├── core/                     # 🆕 NÚCLEO v2.0
│   ├── __init__.py
│   ├── orchestrator.py       # Orquestra o fluxo principal
│   ├── classifier.py         # Classifica intenções
│   └── responder.py          # Gera respostas elaboradas
│
├── capabilities/             # 🆕 CAPACIDADES AUTO-REGISTRÁVEIS
│   ├── __init__.py           # Registry automático
│   ├── base.py               # BaseCapability (contrato)
│   │
│   ├── carteira/             # Domínio: Carteira
│   │   ├── consultar_pedido.py
│   │   ├── consultar_produto.py
│   │   ├── consultar_rota.py
│   │   ├── analisar_disponibilidade.py
│   │   ├── analisar_gargalos.py
│   │   └── criar_separacao.py      # Ação
│   │
│   └── estoque/              # Domínio: Estoque
│       └── consultar_estoque.py
│
├── prompts/                  # 🆕 PROMPTS CENTRALIZADOS
│   ├── __init__.py
│   ├── system_base.py        # Prompt base do sistema
│   └── intent_prompt.py      # Prompt de classificação (gerado)
│
├── actions/                  # Handlers de ações (legado)
│   └── separacao_actions.py
│
└── domains/                  # Loaders (legado, reutilizados)
    └── carteira/
        ├── loaders/
        └── services/
```

---

## Como Adicionar Nova Capacidade

### 1. Criar arquivo em `capabilities/{dominio}/{nome}.py`:

```python
from ..base import BaseCapability

class MinhaNovaCapability(BaseCapability):
    # Metadados obrigatórios
    NOME = "minha_nova_capability"
    DOMINIO = "carteira"  # ou "estoque", "fretes", etc
    TIPO = "consulta"     # ou "acao"
    INTENCOES = ["minha_intencao", "outra_intencao"]
    CAMPOS_BUSCA = ["campo1", "campo2"]
    DESCRICAO = "Descrição curta para o classificador"
    EXEMPLOS = [
        "Exemplo de pergunta 1",
        "Exemplo de pergunta 2"
    ]

    def pode_processar(self, intencao: str, entidades: dict) -> bool:
        """Retorna True se deve processar esta requisição."""
        return intencao in self.INTENCOES

    def executar(self, entidades: dict, contexto: dict) -> dict:
        """Executa a lógica de negócio."""
        # Sua lógica aqui
        return {
            "sucesso": True,
            "total_encontrado": 1,
            "dados": [...]
        }

    def formatar_contexto(self, dados: dict) -> str:
        """Formata resultado para o Claude."""
        return "Texto formatado para o prompt"
```

### 2. Pronto! A capacidade será registrada automaticamente.

O registry em `capabilities/__init__.py` descobre e registra todas as classes que herdam de `BaseCapability`.

---

## Estrutura Legada (Ainda Funcional)

Os arquivos antigos ainda funcionam e são reutilizados:

```
└── domains/                  # Domínios de LEITURA (legado)
    ├── __init__.py           # Registro de loaders
    ├── base.py               # BaseLoader abstrato
    │
    └── carteira/             # Domínio da carteira de pedidos
        ├── loaders/          # Loaders de consulta (reutilizados)
        └── services/         # Serviços de negócio
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
| `buscar_rota` | carteira | "Pedidos na rota MG" ou "Tem algo pra rota B?" (sub-rota) |
| `buscar_uf` | carteira | "O que tem para São Paulo?" |
| `consultar_estoque` | estoque | "Qual o estoque de azeitona?" |
| `consultar_ruptura` | estoque | "Quais produtos vão dar ruptura?" |
| `analisar_saldo` | carteira | "Quanto falta separar do VCD123?" |
| `analisar_gargalo` | carteira | "O que está travando o pedido?" |
| `escolher_opcao` | acao | "Opção A" |
| `criar_separacao` | acao | "Criar separação opção A do pedido VCD123" |
| `confirmar_acao` | acao | "Sim, confirmo" |
| `follow_up` | follow_up | "Preciso dos nomes completos desses itens" 🆕 |
| `detalhar` | follow_up | "Mais detalhes sobre esses produtos" 🆕 |

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

### RotasLoader (`carteira_rota`) 🆕
- Busca por: `rota`, `sub_rota`, `cod_uf`
- Retorna: pedidos/separações filtrados por rota, sub-rota ou UF
- **Rotas principais**: BA, MG, ES, NE, NE2, NO, MS-MT, SUL (baseadas em UF/região)
- **Sub-rotas**: CAP, INT, A, B, C, 0, 1, 2 (baseadas em cidade/região interna)
- Exemplos:
  - "Pedidos na rota MG" (rota principal)
  - "O que tem na rota NE?" (rota principal)
  - "Tem mais algo pra rota B?" (sub-rota)
  - "Pedidos da sub-rota CAP" (sub-rota)
  - "O que tem para São Paulo?" (por UF)

### EstoqueLoader (`estoque`) 🆕
- Busca por: `cod_produto`, `nome_produto`, `ruptura`
- Retorna: estoque atual, projeção 7/14 dias, produtos com ruptura
- Exemplos:
  - "Qual o estoque de azeitona verde?"
  - "Quais produtos vão dar ruptura?"
  - "Projeção de estoque do ketchup"

### SaldoPedidoLoader (`carteira_saldo`) 🆕
- Busca por: `num_pedido`, `cnpj_cpf`, `raz_social_red`
- Retorna: comparativo quantidade original vs separada vs restante
- Exemplos:
  - "Quanto falta separar do VCD123?"
  - "Saldo do pedido VCD456"

### GargalosLoader (`carteira_gargalo`) 🆕
- Busca por: `num_pedido`, `geral`, `cod_produto`
- Retorna: produtos que travam pedidos por falta de estoque
- Exemplos:
  - "O que está travando o pedido VCD789?"
  - "Quais produtos são gargalo?"
  - "Por que não consigo enviar o VCD111?"

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

## Memória e Aprendizado

### Memória de Conversa
O sistema mantém as **últimas 40 mensagens** de cada usuário para contexto.

Isso permite:
- Referências a conversas anteriores: "Quais pedidos você falou?"
- Contexto contínuo: "E o pedido 2 da lista?"
- Histórico de interações

**Tabela:** `claude_historico_conversa`

### Aprendizado Permanente
O sistema pode aprender informações de forma permanente:

| Comando | Exemplo | Escopo |
|---------|---------|--------|
| `Lembre que...` | "Lembre que o cliente Ceratti é VIP" | Por usuário |
| `Lembre que... (global)` | "Lembre que o código 123 é Azeitona Verde (global)" | Todos |
| `Esqueça que...` | "Esqueça que o cliente X é VIP" | Remove |
| `O que você sabe?` | "O que você sabe sobre mim?" | Lista |

**Tabela:** `claude_aprendizado`

**Categorias de Aprendizado:**
- `regra_negocio` - Regras e políticas da empresa
- `cliente` - Informações sobre clientes
- `produto` - Informações sobre produtos
- `processo` - Processos e procedimentos
- `fato` - Fatos gerais
- `preferencia` - Preferências do usuário
- `correcao` - Correções de informações

### Administração
Acesse `/claude-lite/admin/` (apenas administradores) para:
- Ver/criar/editar aprendizados
- Consultar histórico de conversas
- Ver estatísticas de uso

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
