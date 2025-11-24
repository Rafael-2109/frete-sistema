# Claude AI Lite - Documentacao do Modulo

## Visao Geral

Modulo de IA conversacional para o sistema de fretes, permitindo consultas em linguagem natural sobre pedidos, produtos e criacao de separacoes.

**Criado em:** Novembro/2025
**Ultima atualizacao:** 23/11/2025
**Versao:** 3.2 (LoaderExecutor Estruturado)

---

## Arquitetura Geral

```
Pergunta do Usuario
        |
        v
+------------------+
|   Orchestrator   |  <- Ponto de entrada (core/orchestrator.py)
+------------------+
        |
        v
+------------------+
|   Classifier     |  <- Identifica intencao e entidades (core/classifier.py)
|   + PROMPTS      |  <- Usa prompt dinamico (prompts/intent_prompt.py)
|     APRENDIDOS   |  <- Inclui codigos do IA Trainer
+------------------+
        |
        v
+------------------+     +----------------------+
| find_capability  | --> | NAO ENCONTROU?       |
| (capabilities/)  |     | -> Suggester         |
+------------------+     | -> Log nao respondida|
        |                | -> Sugestoes         |
        v                +----------------------+
+------------------+
| Capability       |  <- Executa logica de negocio
|   .executar()    |  <- Pode delegar para Loader
+------------------+
        |
        v
+------------------+
| Responder        |  <- Gera resposta elaborada (core/responder.py)
+------------------+
```

---

## Estrutura de Arquivos

```
app/claude_ai_lite/
|
|-- README.md                 # Esta documentacao
|-- __init__.py               # Inicializacao e exports
|-- config.py                 # Configuracoes
|-- routes.py                 # Endpoints Flask (API)
|-- routes_admin.py           # Endpoints de administracao
|
|-- # CLIENTE CLAUDE
|-- claude_client.py          # Cliente da API Anthropic Claude
|
|-- # NUCLEO (core/)
|-- core/
|   |-- __init__.py           # Exporta processar_consulta
|   |-- orchestrator.py       # Orquestra fluxo principal
|   |-- classifier.py         # Classifica intencoes via Claude
|   |-- responder.py          # Gera respostas elaboradas
|   +-- suggester.py          # Gera sugestoes quando nao responde
|
|-- # CAPACIDADES (capabilities/)
|-- capabilities/
|   |-- __init__.py           # Registry automatico de capacidades
|   |-- base.py               # BaseCapability (classe base)
|   |
|   |-- carteira/             # Dominio: Carteira
|   |   |-- consultar_pedido.py        # ATIVO - Consulta pedidos
|   |   |-- consultar_produto.py       # ATIVO - Consulta produtos (delega p/ loader)
|   |   |-- consultar_rota.py          # ATIVO - Consulta por rota/UF (delega p/ loader)
|   |   |-- analisar_disponibilidade.py # ATIVO - Analisa opcoes A/B/C
|   |   |-- analisar_gargalos.py       # ATIVO - Identifica gargalos (delega p/ loader)
|   |   |-- analisar_estoque_cliente.py # ATIVO - Pergunta composta cliente+estoque+data
|   |   +-- criar_separacao.py         # ATIVO - Cria separacao via chat
|   |
|   +-- estoque/              # Dominio: Estoque
|       +-- consultar_estoque.py       # ATIVO - Consulta estoque/rupturas (delega p/ loader)
|
|-- # LOADERS (domains/carteira/loaders/)
|-- domains/
|   |-- __init__.py
|   |-- base.py               # BaseLoader (classe base para loaders)
|   |
|   +-- carteira/
|       |-- loaders/
|       |   |-- pedidos.py         # Loader de pedidos (NAO USADO DIRETAMENTE)
|       |   |-- produtos.py        # USADO por ConsultarProdutoCapability
|       |   |-- rotas.py           # USADO por ConsultarRotaCapability
|       |   |-- gargalos.py        # USADO por AnalisarGargalosCapability
|       |   |-- estoque.py         # USADO por ConsultarEstoqueCapability
|       |   |-- disponibilidade.py # NAO USADO (logica movida para OpcoesEnvioService)
|       |   +-- saldo_pedido.py    # NAO USADO
|       |
|       |-- prompts.py             # Prompts especificos do dominio (LEGADO)
|       |
|       +-- services/
|           |-- opcoes_envio.py    # USADO - Gera opcoes A/B/C de envio
|           +-- criar_separacao.py # USADO - Cria separacao no banco
|
|-- # PROMPTS CENTRALIZADOS
|-- prompts/
|   |-- __init__.py           # Exporta funcoes
|   |-- system_base.py        # Prompt base do sistema
|   +-- intent_prompt.py      # Prompt de classificacao (DINAMICO)
|
|-- # ACOES
|-- actions/
|   |-- __init__.py
|   |-- separacao_actions.py  # Handlers de acoes de separacao
|   +-- rascunho_separacao.py # Rascunhos de separacao
|
|-- # MEMORIA E APRENDIZADO
|-- models.py                 # ClaudeHistoricoConversa, ClaudeAprendizado, ClaudePerguntaNaoRespondida
|-- memory.py                 # Funcoes de memoria de conversa
|-- learning.py               # Funcoes de aprendizado permanente
|-- cache.py                  # Cache Redis para o modulo
|
|-- # IA TRAINER (sistema de auto-aprendizado)
+-- ia_trainer/
    |-- __init__.py           # Exports
    |-- models.py             # CodigoSistemaGerado, SessaoEnsinoIA, VersaoCodigoGerado
    |-- routes.py             # Endpoints da interface de ensino
    |
    +-- services/
        |-- __init__.py
        |-- codigo_loader.py   # Carrega codigos ativos (com cache)
        |-- codebase_reader.py # Le codigo-fonte do sistema
        |-- code_validator.py  # Valida seguranca do codigo
        |-- code_executor.py   # Executa codigo com timeout
        |-- code_generator.py  # Gera codigo via Claude
        +-- trainer_service.py # Orquestra fluxo de ensino
```

---

## Fluxo de Dados Detalhado

### 1. Pergunta chega via API
```
POST /claude-lite/api/query
{"query": "Quando posso enviar o pedido VCD123?"}
```

### 2. Orchestrator processa
```python
# core/orchestrator.py
def processar_consulta(consulta, usuario_id):
    # 1. Classifica intencao
    intencao = classifier.classificar(consulta, contexto_conversa)
    # {"dominio": "carteira", "intencao": "analisar_disponibilidade", "entidades": {"num_pedido": "VCD123"}}

    # 2. Busca capacidade
    capability = find_capability(intencao["intencao"], intencao["entidades"])
    # AnalisarDisponibilidadeCapability

    # 3. Executa
    resultado = capability.executar(intencao["entidades"], contexto)

    # 4. Gera resposta
    contexto_dados = capability.formatar_contexto(resultado)
    resposta = responder.gerar_resposta(consulta, contexto_dados)
```

### 3. Capability executa logica
```python
# capabilities/carteira/analisar_disponibilidade.py
class AnalisarDisponibilidadeCapability(BaseCapability):
    def executar(self, entidades, contexto):
        # Usa servico existente
        from domains.carteira.services.opcoes_envio import OpcoesEnvioService
        analise = OpcoesEnvioService.analisar_pedido(num_pedido)
        return {"sucesso": True, "opcoes": analise["opcoes"], ...}
```

---

## Capacidades Disponiveis

### Capacidades Simples

| Nome | Intencoes | Delega para | Descricao |
|------|-----------|-------------|-----------|
| `consultar_pedido` | consultar_status, buscar_pedido | - | Busca pedidos na CarteiraPrincipal |
| `consultar_produto` | buscar_produto | ProdutosLoader | Busca produtos na carteira/separacao |
| `consultar_rota` | buscar_rota, buscar_uf | RotasLoader | Busca por rota, sub-rota ou UF |
| `analisar_disponibilidade` | analisar_disponibilidade | OpcoesEnvioService | Gera opcoes A/B/C de envio |
| `analisar_gargalos` | analisar_gargalo | GargalosLoader | Identifica produtos gargalo |
| `consultar_estoque` | consultar_estoque, consultar_ruptura | EstoqueLoader | Consulta estoque e rupturas |

### Capacidades Compostas

| Nome | Intencoes | Descricao |
|------|-----------|-----------|
| `analisar_estoque_cliente` | analisar_estoque_cliente | Combina cliente + data + estoque |

**Exemplos de perguntas compostas:**
- "Quais produtos do Atacadao terao estoque dia 26?"
- "O que posso enviar para o cliente Ceratti?"

---

## Loaders Ativos

Loaders sao usados pelas Capabilities para executar queries no banco.

| Loader | Usado por | Campos de busca |
|--------|-----------|-----------------|
| `ProdutosLoader` | ConsultarProdutoCapability | nome_produto, cod_produto |
| `RotasLoader` | ConsultarRotaCapability | rota, sub_rota, cod_uf |
| `GargalosLoader` | AnalisarGargalosCapability | num_pedido, cod_produto, geral |
| `EstoqueLoader` | ConsultarEstoqueCapability | cod_produto, nome_produto, ruptura |

**Loaders NAO usados (legado):**
- `PedidosLoader` - Logica movida para ConsultarPedidoCapability
- `DisponibilidadeLoader` - Substituido por OpcoesEnvioService
- `SaldoPedidoLoader` - Nao usado

---

## IA Trainer - Status Atual

### O que FUNCIONA:

1. **Interface de ensino** (`/claude-lite/trainer/`)
   - Listar perguntas nao respondidas
   - Iniciar sessao de ensino
   - Salvar decomposicao da pergunta
   - Gerar codigo via Claude
   - Debater/refinar codigo

2. **Tipos de codigo suportados:**
   - `prompt` - Regras para classificacao -> **INTEGRADO**
   - `conceito` - Termos de negocio -> **INTEGRADO**
   - `entidade` - Entidades customizadas -> **INTEGRADO**
   - `filtro` - Condicoes SQL simples -> **INTEGRADO**
   - `loader` - JSON estruturado para consultas complexas -> **INTEGRADO (v3.2)**

3. **Integracao com o sistema:**
   - `intent_prompt.py` carrega prompts/conceitos/entidades ativos
   - `BaseCapability.aplicar_filtros_aprendidos()` aplica filtros via `text()`
   - `LoaderExecutor` executa loaders estruturados com JOINs, agregacoes, filtros complexos

---

## LoaderExecutor - Motor de Consultas Estruturadas (v3.2)

O `LoaderExecutor` permite ao Claude compor consultas complexas via **JSON estruturado**,
SEM executar codigo Python arbitrario.

### Funcionalidades:

- **JOINs seguros** entre Models conhecidos
- **Filtros complexos**: ilike, is_null, in, between, contains, etc
- **Agregacoes**: count, sum, avg, min, max
- **Agrupamentos**: GROUP BY com multiplos campos
- **Parametros dinamicos**: $cliente, $data, etc
- **Validacao**: whitelist de Models e operadores
- **Read-only**: impossivel alterar dados
- **Timeout**: protecao contra queries lentas

### Formato JSON:

```json
{
    "modelo_base": "Separacao",
    "joins": [
        {"modelo": "CarteiraPrincipal", "tipo": "left", "on": {"local": "num_pedido", "remoto": "num_pedido"}}
    ],
    "filtros": [
        {"campo": "raz_social_red", "operador": "ilike", "valor": "%Assai%"},
        {"campo": "agendamento", "operador": "is_null"},
        {"campo": "sincronizado_nf", "operador": "==", "valor": false}
    ],
    "campos_retorno": ["num_pedido", "raz_social_red", "qtd_saldo"],
    "agregacao": {
        "tipo": "agrupar",
        "por": ["raz_social_red"],
        "funcoes": [{"func": "sum", "campo": "qtd_saldo", "alias": "total_qtd"}]
    },
    "ordenar": [{"campo": "num_pedido", "direcao": "asc"}],
    "limite": 100
}
```

### Operadores Permitidos:

| Operador | Descricao | Exemplo |
|----------|-----------|---------|
| `==`, `!=` | Igualdade | `{"campo": "status", "operador": "==", "valor": "ABERTO"}` |
| `>`, `>=`, `<`, `<=` | Comparacao | `{"campo": "qtd_saldo", "operador": ">", "valor": 0}` |
| `ilike`, `like` | Texto (% wildcard) | `{"campo": "raz_social_red", "operador": "ilike", "valor": "%Assai%"}` |
| `in`, `not_in` | Lista | `{"campo": "cod_uf", "operador": "in", "valor": ["SP", "RJ"]}` |
| `is_null`, `is_not_null` | Nulos | `{"campo": "agendamento", "operador": "is_null"}` |
| `between` | Intervalo | `{"campo": "data", "operador": "between", "valor": ["2024-01-01", "2024-12-31"]}` |

### Filtros com AND/OR:

```json
{
    "filtros": {
        "and": [
            {"campo": "sincronizado_nf", "operador": "==", "valor": false},
            {
                "or": [
                    {"campo": "raz_social_red", "operador": "ilike", "valor": "%Assai%"},
                    {"campo": "raz_social_red", "operador": "ilike", "valor": "%Atacadao%"}
                ]
            }
        ]
    }
}
```

### JOINs com dot-notation:

```json
{
    "joins": [
        {
            "modelo": "CarteiraPrincipal",
            "tipo": "left",
            "on": {
                "local": "Separacao.num_pedido",
                "remoto": "CarteiraPrincipal.num_pedido"
            }
        }
    ]
}
```

### Uso Programatico:

```python
from app.claude_ai_lite.ia_trainer.services.loader_executor import executar_loader

# Pergunta: "Ha pedidos do cliente Assai sem agendamento?"
definicao = {
    "modelo_base": "Separacao",
    "filtros": [
        {"campo": "raz_social_red", "operador": "ilike", "valor": "%Assai%"},
        {"campo": "agendamento", "operador": "is_null"},
        {"campo": "sincronizado_nf", "operador": "==", "valor": False}
    ],
    "campos_retorno": ["num_pedido", "raz_social_red", "qtd_saldo"],
    "limite": 50
}

resultado = executar_loader(definicao)
# {'sucesso': True, 'total': 50, 'dados': [...]}
```

### O que NAO FUNCIONA ainda:

1. **Tipo `capability`:**
   - Marcado como tipo valido mas **NAO IMPLEMENTADO**
   - Nao ha como criar capacidades dinamicamente

2. **Integracao automatica com Orchestrator:**
   - Loaders gerados precisam ser chamados manualmente
   - Futuro: Capability generica que usa loaders aprendidos

---

## Sistema de Sugestoes

Quando o sistema nao consegue responder, o `Suggester` analisa:

1. **Tipo da pergunta:** simples, composta, ambigua
2. **Dimensoes:** cliente, data, estoque, produto, rota, etc
3. **Gera sugestoes** baseadas nas entidades detectadas

```python
# Exemplo de sugestao para pergunta composta
"Sua pergunta combina varias dimensoes que ainda nao consigo processar juntas.
Tente separar em perguntas mais especificas:
  1. Pedidos do cliente Atacadao
  2. Para cada pedido: 'Quando posso enviar o pedido X?'"
```

---

## Cache Redis

O sistema usa Redis para cache com fallback para memoria.

| Tipo | TTL | Descricao |
|------|-----|-----------|
| `codigos_ativos` | 5 min | Codigos do IA Trainer |
| `readme_contexto` | 1 hora | Contexto para re-classificacao |
| `classificacao` | 1 min | Classificacoes recentes |

---

## Tabelas do Banco

### Memoria e Aprendizado
- `claude_historico_conversa` - Historico de mensagens por usuario
- `claude_aprendizado` - Conhecimento permanente (por usuario ou global)
- `claude_perguntas_nao_respondidas` - Log de falhas para analise

### IA Trainer
- `codigo_sistema_gerado` - Codigo gerado pelo Claude
- `versao_codigo_gerado` - Historico de versoes
- `sessao_ensino_ia` - Sessao de ensino (pergunta -> codigo)

---

## Endpoints da API

### Consulta Principal
```
POST /claude-lite/api/query
{"query": "...", "usar_claude": true}
```

### Health Check
```
GET /claude-lite/health
```

### Admin (requer login)
```
GET  /claude-lite/admin/
```

### IA Trainer (requer login admin)
```
GET  /claude-lite/trainer/
GET  /claude-lite/trainer/api/perguntas
POST /claude-lite/trainer/api/sessao/iniciar
POST /claude-lite/trainer/api/sessao/{id}/decomposicao
POST /claude-lite/trainer/api/sessao/{id}/gerar
POST /claude-lite/trainer/api/sessao/{id}/debater
POST /claude-lite/trainer/api/sessao/{id}/testar
POST /claude-lite/trainer/api/sessao/{id}/ativar
```

---

## Intencoes Reconhecidas

| Intencao | Dominio | Exemplo |
|----------|---------|---------|
| `consultar_status` | carteira | "Status do pedido VCD123" |
| `buscar_pedido` | carteira | "Pedido VCD123" |
| `buscar_produto` | carteira | "Azeitona na carteira" |
| `analisar_disponibilidade` | carteira | "Quando posso enviar VCD123?" |
| `analisar_estoque_cliente` | carteira | "O que posso enviar pro Atacadao?" |
| `buscar_rota` | carteira | "Pedidos na rota MG" |
| `buscar_uf` | carteira | "O que tem para SP?" |
| `consultar_estoque` | estoque | "Qual o estoque de azeitona?" |
| `consultar_ruptura` | estoque | "Quais produtos vao dar ruptura?" |
| `analisar_gargalo` | carteira | "O que esta travando o pedido?" |
| `escolher_opcao` | acao | "Opcao A" |
| `criar_separacao` | acao | "Criar separacao opcao A" |
| `confirmar_acao` | acao | "Sim, confirmo" |
| `follow_up` | follow_up | "Mais detalhes sobre esses" |

---

## Como Adicionar Nova Capacidade

1. Criar arquivo em `capabilities/{dominio}/{nome}.py`:

```python
from ..base import BaseCapability

class MinhaCapability(BaseCapability):
    NOME = "minha_capability"
    DOMINIO = "carteira"
    TIPO = "consulta"
    INTENCOES = ["minha_intencao"]
    CAMPOS_BUSCA = ["campo1"]
    DESCRICAO = "Descricao curta"
    EXEMPLOS = ["Exemplo de pergunta"]

    def pode_processar(self, intencao: str, entidades: dict) -> bool:
        return intencao in self.INTENCOES

    def executar(self, entidades: dict, contexto: dict) -> dict:
        # Logica aqui
        return {"sucesso": True, "dados": [...]}

    def formatar_contexto(self, dados: dict) -> str:
        return "Texto formatado"
```

2. Capacidade sera registrada automaticamente pelo `capabilities/__init__.py`

---

## LACUNAS IDENTIFICADAS - O que falta implementar

### 1. ~~Executor de Loaders Gerados~~ - IMPLEMENTADO v3.2
~~O IA Trainer gera codigo tipo `loader`, mas nao ha forma de executar.~~
**Solucao:** `LoaderExecutor` com JSON estruturado (JOINs, filtros, agregacoes).

### 2. ~~Filtros Complexos~~ - IMPLEMENTADO v3.2
~~`aplicar_filtros_aprendidos()` so aceita SQL puro via `text()`.~~
**Solucao:** `LoaderExecutor` suporta ilike, is_null, in, between, contains, etc.

### 3. Integracao Automatica IA Trainer -> Orchestrator (PENDENTE)
Loaders gerados precisam ser chamados manualmente.
**Solucao futura:** Criar Capability generica que carrega e executa loaders aprendidos.

### 4. Tipo `capability` (PENDENTE)
Nao ha como criar capacidades dinamicamente.
**Solucao futura:** Avaliar necessidade vs uso de loaders estruturados.

---

## Configuracao

```env
ANTHROPIC_API_KEY=sk-ant-...
REDIS_URL=redis://...  # Opcional
```

Modelo utilizado: `claude-sonnet-4-5-20250929`
