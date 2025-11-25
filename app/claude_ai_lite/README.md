# Claude AI Lite - Documentacao do Modulo

## Visao Geral

Modulo de IA conversacional para o sistema de fretes, permitindo consultas em linguagem natural sobre pedidos, produtos e criacao de separacoes.

**Criado em:** Novembro/2025
**Ultima atualizacao:** 24/11/2025
**Versao:** 3.4.1 (Correção de Extração de Datas)

### Novidades v3.4.1
- ✅ **Extração de Datas Específicas**: "dia 27/11", "pro dia 27/11" agora funciona para separações
- ✅ **Datas do Usuário Prevalecem**: Data especificada pelo usuário sobrescreve a calculada

### Novidades v3.4
- ✅ **Self-Consistency Check**: Revisão automática de respostas antes de enviar
- ✅ **Extração de Entidades Compostas**: "sem agendamento", "atrasados", etc
- ✅ **Loop de Feedback Automático**: Análise de gaps e sugestões de melhoria
- ✅ **Contextualização Melhorada**: Campos disponíveis e filtros no prompt
- ✅ **Histórico Rico**: Itens numerados para referência ("o pedido 2")
- ✅ **Validação CLAUDE.md**: Verificação de nomes de campos corretos

---

## 🗺️ MAPA MESTRE - Fluxo de Execução Real

Este é o fluxo **EXATO** de execução, na ordem em que acontece no código:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        FLUXO COMPLETO DE EXECUÇÃO                           │
│                        (orchestrator.py linha a linha)                      │
└─────────────────────────────────────────────────────────────────────────────┘

ENTRADA: processar_consulta(consulta, usuario_id)
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ ETAPA 0: CONTEXTO CONVERSACIONAL                                             │
│ Arquivo: core/conversation_context.py                                        │
│ Função: classificar_e_reconstruir()                                          │
│ ─────────────────────────────────────────────────────────────────────────────│
│ ✔ Entrada: texto do usuário, usuario_id                                      │
│ ✔ Saída: tipo_mensagem, consulta_reconstruida, entidades_contexto            │
│ ✔ Depende de: _estados_conversa (cache em memória)                           │
│ ─────────────────────────────────────────────────────────────────────────────│
│ O que faz:                                                                   │
│ - Detecta se é NOVA_CONSULTA, CONTINUACAO, MODIFICACAO, ACAO, DETALHAMENTO   │
│ - Se MODIFICACAO: "Refaça com nome_produto" + pergunta anterior              │
│ - Se CONTINUACAO: "esse pedido" → busca num_pedido do contexto               │
└──────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ ETAPA 1: BUSCAR MEMÓRIA                                                      │
│ Arquivo: memory.py → MemoryService.formatar_contexto_memoria()               │
│ ─────────────────────────────────────────────────────────────────────────────│
│ ✔ Entrada: usuario_id                                                        │
│ ✔ Saída: contexto_memoria (string com histórico + aprendizados)              │
│ ✔ Depende de: ClaudeHistoricoConversa, ClaudeAprendizado (banco)             │
└──────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ ETAPA 2: VERIFICAR COMANDO DE APRENDIZADO                                    │
│ Arquivo: learning.py → LearningService.detectar_comando()                    │
│ ─────────────────────────────────────────────────────────────────────────────│
│ ✔ Entrada: consulta, usuario_id                                              │
│ ✔ Saída: resultado_aprendizado (ou None se não for comando)                  │
│ ✔ Depende de: ClaudeAprendizado (banco)                                      │
│ ─────────────────────────────────────────────────────────────────────────────│
│ Se for "Lembre que...", "Esqueça que..." → processa e RETORNA AQUI           │
└──────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ ETAPA 3: CLASSIFICAR INTENÇÃO                                                │
│ Arquivo: core/classifier.py → IntentClassifier.classificar()                 │
│ ─────────────────────────────────────────────────────────────────────────────│
│ ✔ Entrada: consulta_reconstruida, contexto_memoria, usuario_id               │
│ ✔ Saída: {dominio, intencao, entidades, confianca}                           │
│ ✔ Depende de: intent_prompt.py, claude_client.py, ClaudeAprendizado,         │
│              CodigoSistemaGerado (prompts/conceitos/entidades)               │
│ ─────────────────────────────────────────────────────────────────────────────│
│ 1. Gera prompt dinâmico via gerar_prompt_classificacao()                     │
│    - Carrega ClaudeAprendizado do usuário (caderno de dicas)                 │
│    - Carrega CodigoSistemaGerado ativos (prompts, conceitos, entidades)      │
│ 2. Chama Claude API para classificar                                         │
│ 3. Retorna JSON com dominio, intencao, entidades, confianca                  │
└──────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼ (se confiança < 0.7)
┌──────────────────────────────────────────────────────────────────────────────┐
│ ETAPA 3.1: RE-CLASSIFICAR COM README (opcional)                              │
│ Arquivo: core/orchestrator.py → _reclassificar_com_readme()                  │
│ ─────────────────────────────────────────────────────────────────────────────│
│ ✔ Depende de: cache.py → carregar_readme_contexto()                          │
│ Se nova confiança > original: usa nova classificação                         │
└──────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ ETAPA 3.2: MAPEAR ENTIDADES                                                  │
│ Arquivo: core/orchestrator.py → _mapear_entidades_para_campos()              │
│ ─────────────────────────────────────────────────────────────────────────────│
│ ✔ Entrada: entidades do classificador                                        │
│ ✔ Saída: entidades mapeadas para nomes de campos do banco                    │
│ ─────────────────────────────────────────────────────────────────────────────│
│ "cliente" → "raz_social_red" | "cnpj" → "cnpj_cpf" | etc (17 mapeamentos)    │
└──────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ ETAPA 3.3: EXTRAIR CONDIÇÕES COMPOSTAS (v3.4)                                │
│ Arquivo: core/composite_extractor.py → enriquecer_entidades()                │
│ ─────────────────────────────────────────────────────────────────────────────│
│ ✔ Entrada: consulta, entidades mapeadas                                      │
│ ✔ Saída: entidades + _filtros_compostos                                      │
│ ─────────────────────────────────────────────────────────────────────────────│
│ "sem agendamento" → {campo: agendamento, operador: is_null}                  │
│ "atrasados" → {campo: expedicao, operador: <, valor: hoje}                   │
└──────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ ETAPA 4: TRATAMENTO ESPECIAL                                                 │
│ ─────────────────────────────────────────────────────────────────────────────│
│ Se dominio == "follow_up": → _processar_follow_up() → RETORNA                │
│ Se dominio == "acao": → _processar_acao() → RETORNA                          │
└──────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ ETAPA 5: ENCONTRAR CAPACIDADE                                                │
│ Arquivo: capabilities/__init__.py → find_capability()                        │
│ ─────────────────────────────────────────────────────────────────────────────│
│ ✔ Entrada: intencao_tipo, entidades                                          │
│ ✔ Saída: instância de BaseCapability (ou None)                               │
│ ✔ Depende de: _capabilities_registry (auto-preenchido no import)             │
│ ─────────────────────────────────────────────────────────────────────────────│
│ Se não encontrou: → _tratar_sem_capacidade() (tenta loader aprendido)        │
└──────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ ETAPA 6: EXTRAIR CRITÉRIO + BUSCAR FILTROS                                   │
│ ─────────────────────────────────────────────────────────────────────────────│
│ 1. capacidade.extrair_valor_busca() → (campo, valor)                         │
│ 2. _buscar_filtros_aprendidos() → filtros do IA Trainer                      │
│ 3. Combina filtros aprendidos + filtros compostos                            │
└──────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ ETAPA 7: EXECUTAR CAPACIDADE                                                 │
│ Arquivo: capabilities/{dominio}/{nome}.py → executar()                       │
│ ─────────────────────────────────────────────────────────────────────────────│
│ ✔ Entrada: entidades, contexto (com filtros_aprendidos)                      │
│ ✔ Saída: {sucesso, dados, total_encontrado, ...}                             │
│ ─────────────────────────────────────────────────────────────────────────────│
│ Capacidade aplica filtros via aplicar_filtros_aprendidos()                   │
└──────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ ETAPA 8: FORMATAR + GERAR RESPOSTA                                           │
│ ─────────────────────────────────────────────────────────────────────────────│
│ 1. capacidade.formatar_contexto() → string de dados                          │
│ 2. _enriquecer_com_conceitos() → adiciona conceitos aprendidos               │
│ 3. responder.gerar_resposta() → Claude elabora resposta                      │
└──────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ ETAPA 9: REVISAR RESPOSTA (v3.4)                                             │
│ Arquivo: core/response_reviewer.py → revisar_resposta()                      │
│ ─────────────────────────────────────────────────────────────────────────────│
│ ✔ Entrada: pergunta, resposta_gerada, contexto_dados                         │
│ ✔ Saída: resposta (revisada ou original)                                     │
│ ─────────────────────────────────────────────────────────────────────────────│
│ Verifica: números inventados, campos incorretos, contradições                │
└──────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ ETAPA 10: REGISTRAR NA MEMÓRIA                                               │
│ ─────────────────────────────────────────────────────────────────────────────│
│ 1. Salva no histórico (ClaudeHistoricoConversa)                              │
│ 2. Atualiza contexto conversacional                                          │
│ 3. Registra itens numerados para referência futura                           │
└──────────────────────────────────────────────────────────────────────────────┘
                    │
                    ▼
                RETORNA: resposta (string)
```

---

## 📦 CAIXAS PRETAS - Cada Módulo em 3 Linhas

### Core (Núcleo)

| Módulo | Entrada | Saída | Depende de |
|--------|---------|-------|------------|
| **orchestrator.py** | texto, usuario_id | resposta (string) | TODOS os outros |
| **classifier.py** | texto, contexto, usuario_id | {dominio, intencao, entidades, confianca} | intent_prompt, claude_client |
| **responder.py** | pergunta, contexto_dados | resposta elaborada | system_base, claude_client, response_reviewer |
| **response_reviewer.py** | pergunta, resposta, contexto | resposta revisada | CAMPOS_ERRADOS, claude_client |
| **composite_extractor.py** | texto, entidades | entidades + filtros | PADROES_CONDICOES (regex) |
| **conversation_context.py** | texto, usuario_id | tipo_msg, entidades_ctx | _estados_conversa (memória) |
| **suggester.py** | consulta, intencao | sugestões de perguntas | TEMPLATES_SUGESTOES |
| **feedback_loop.py** | dias | análise de gaps | ClaudePerguntaNaoRespondida |

### Prompts

| Módulo | Entrada | Saída | Depende de |
|--------|---------|-------|------------|
| **intent_prompt.py** | contexto, usuario_id | prompt de classificação | capabilities, ClaudeAprendizado, CodigoSistemaGerado |
| **system_base.py** | contexto_memoria | prompt base do sistema | nenhum |

---

## 🔗 DEPENDÊNCIAS - Quem Precisa de Quem

```
orchestrator.py
├── conversation_context.py
├── memory.py
│   └── models.py (ClaudeHistoricoConversa, ClaudeAprendizado)
├── learning.py
│   └── models.py (ClaudeAprendizado)
├── classifier.py
│   ├── claude_client.py
│   └── prompts/intent_prompt.py
│       ├── capabilities/__init__.py (listar_dominios, listar_intencoes)
│       ├── models.py (ClaudeAprendizado)
│       └── ia_trainer/services/codigo_loader.py (prompts, conceitos, entidades)
│           └── ia_trainer/models.py (CodigoSistemaGerado)
├── composite_extractor.py (standalone - apenas regex)
├── capabilities/__init__.py (find_capability)
│   └── capabilities/*/
│       ├── base.py
│       ├── domains/carteira/loaders/
│       └── domains/carteira/services/
├── ia_trainer/services/codigo_loader.py (buscar_filtros_aprendidos)
├── responder.py
│   ├── claude_client.py
│   ├── prompts/system_base.py
│   └── response_reviewer.py
└── models.py (ClaudePerguntaNaoRespondida)
```

---

## 🎯 ONDE COLOCAR CÓDIGO NOVO

| Se você quer... | Coloque em... | E modifique... |
|-----------------|---------------|----------------|
| Nova intenção reconhecida | prompts/intent_prompt.py | Adicione em REGRAS PARA INTENCAO |
| Nova capacidade de consulta | capabilities/{dominio}/ | Crie classe herdando BaseCapability |
| Novo filtro automático | composite_extractor.py | Adicione em PADROES_CONDICOES |
| Novo mapeamento de entidade | orchestrator.py | Adicione em _mapear_entidades_para_campos |
| Novo modelo no LoaderExecutor | ia_trainer/loader_executor.py | Adicione em MODELS_PERMITIDOS |
| Nova validação de campo | response_reviewer.py | Adicione em CAMPOS_ERRADOS |
| Novo padrão de conversa | conversation_context.py | Adicione em PADROES_* |

---

## Arquitetura Visual Simplificada

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              VISÃO DE ALTO NÍVEL                            │
└─────────────────────────────────────────────────────────────────────────────┘

                         ┌─────────────────┐
                         │   API/Routes    │
                         └────────┬────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                            ORCHESTRATOR                                      │
│  ┌─────────┐  ┌──────────┐  ┌────────────┐  ┌──────────┐  ┌──────────┐     │
│  │ Context │→ │ Memory   │→ │ Classifier │→ │Composite │→ │Capability│     │
│  │ Manager │  │ Service  │  │            │  │ Extractor│  │ Finder   │     │
│  └─────────┘  └──────────┘  └──────────┬─┘  └──────────┘  └────┬─────┘     │
│                                        │                        │           │
│                              ┌─────────┴─────────┐              │           │
│                              │   Intent Prompt   │              │           │
│                              │  ┌─────────────┐  │              │           │
│                              │  │Aprendizados │  │              │           │
│                              │  │IA Trainer   │  │              │           │
│                              │  └─────────────┘  │              │           │
│                              └───────────────────┘              │           │
│                                                                 │           │
│  ┌──────────────────────────────────────────────────────────────┴───┐      │
│  │                         CAPABILITIES                              │      │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐         │      │
│  │  │ Consultar│  │ Analisar │  │ Consultar│  │  Criar   │         │      │
│  │  │  Pedido  │  │Disponib. │  │ Estoque  │  │Separação │         │      │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘         │      │
│  │       │              │             │             │               │      │
│  │       ▼              ▼             ▼             ▼               │      │
│  │  ┌────────────────────────────────────────────────────────┐     │      │
│  │  │               LOADERS / SERVICES                        │     │      │
│  │  └────────────────────────────────────────────────────────┘     │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                                  │                                          │
│                                  ▼                                          │
│  ┌───────────────────────────────────────────────────────────────────┐     │
│  │  Responder → Response Reviewer (v3.4) → Registro/Memória          │     │
│  └───────────────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
                           RESPOSTA (string)
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
|   |-- responder.py          # Gera respostas elaboradas (c/ revisao)
|   |-- suggester.py          # Gera sugestoes quando nao responde
|   |-- conversation_context.py # Contexto conversacional (itens numerados)
|   |-- response_reviewer.py  # NOVO v3.4: Self-Consistency Check
|   |-- composite_extractor.py # NOVO v3.4: Extrai condicoes compostas
|   +-- feedback_loop.py      # NOVO v3.4: Analise de gaps automatica
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
|-- # MEMORIA E APRENDIZADO (Sistema Dual)
|-- models.py                 # ClaudeHistoricoConversa, ClaudeAprendizado, ClaudePerguntaNaoRespondida
|-- memory.py                 # Funcoes de memoria de conversa
|-- learning.py               # Funcoes de aprendizado permanente (via chat)
|-- cache.py                  # Cache Redis para o modulo
|
|-- # IA TRAINER (sistema de auto-aprendizado avancado)
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

## Sistema Dual de Aprendizado

O Claude AI Lite possui **dois sistemas complementares** de aprendizado que trabalham juntos
para melhorar a compreensão e execução das consultas:

### 1. ClaudeAprendizado (Caderno de Dicas)

**Tabela:** `claude_aprendizado`
**Arquivos:** `models.py`, `learning.py`, `memory.py`

Armazena **conhecimento conceitual** do negócio:
- "Cliente Atacadão é prioritário"
- "Rota MG inclui cidades de Minas Gerais"
- "Pedidos VIP devem ter agendamento confirmado"

**Quando é usado:**
1. ✅ **Classificação** - Ajuda a entender o contexto da pergunta
2. ✅ **Geração de resposta** - Formata respostas com conhecimento do negócio
3. ✅ **Re-classificação** - Usado quando confiança está baixa

**Como ensinar:**
- Via chat: "Lembre que o cliente X é VIP"
- Via admin: `/claude-lite/admin/aprendizados`

### 2. CodigoSistemaGerado (Receitas Prontas)

**Tabela:** `codigo_sistema_gerado`
**Arquivos:** `ia_trainer/models.py`, `ia_trainer/services/`

Armazena **código executável** gerado pelo IA Trainer:
- Loaders JSON estruturados (queries complexas)
- Filtros SQL prontos
- Conceitos com gatilhos de ativação
- Prompts customizados para classificação

**Quando é usado:**
1. ✅ **Classificação** - Prompts, conceitos e entidades customizados
2. ✅ **Execução** - Loaders e filtros aprendidos são executados
3. ✅ **Enriquecimento** - Conceitos relevantes adicionados ao contexto

**Como criar:**
- Via IA Trainer: `/claude-lite/trainer/`
- Identificar pergunta não respondida → Gerar código → Testar → Ativar

### Diferença Chave

| Aspecto | ClaudeAprendizado | CodigoSistemaGerado |
|---------|-------------------|---------------------|
| **O que armazena** | Texto/conhecimento | Código/JSON executável |
| **Quem cria** | Usuário via chat | Admin via IA Trainer |
| **Quando usa** | Em TODO o fluxo | Na classificação e execução |
| **Exemplo** | "Cliente X é VIP" | `{"filtro": {"campo": "cliente"}}` |

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

### Models Permitidos no LoaderExecutor

Apenas models listados na whitelist podem ser usados em consultas.
Arquivo: `ia_trainer/services/loader_executor.py`

| Model | Modulo | Descricao |
|-------|--------|-----------|
| `CarteiraPrincipal` | `app.carteira.models` | Itens da carteira de pedidos |
| `Separacao` | `app.separacao.models` | Itens separados/pre-separados |
| `Pedido` | `app.pedidos.models` | **VIEW** agregada de Separacao (read-only!) |
| `PreSeparacaoItem` | `app.carteira.models` | Pre-separacoes (deprecated) |
| `SaldoStandby` | `app.carteira.models` | Saldos em standby |
| `CadastroPalletizacao` | `app.producao.models` | Palletizacao e peso dos produtos |
| `ProgramacaoProducao` | `app.producao.models` | Programacao de producao |
| `MovimentacaoEstoque` | `app.estoque.models` | Movimentacoes de entrada/saida |
| `UnificacaoCodigos` | `app.estoque.models` | Codigos unificados de produtos |
| `FaturamentoProduto` | `app.faturamento.models` | Produtos faturados por NF |
| `Embarque` | `app.embarques.models` | Embarques (cabecalho) |
| `EmbarqueItem` | `app.embarques.models` | Itens do embarque |
| `CadastroRota` | `app.localidades.models` | Rotas principais |
| `CadastroSubRota` | `app.localidades.models` | Sub-rotas |
| `Frete` | `app.fretes.models` | Fretes |

**IMPORTANTE:**
- `Pedido` e uma **VIEW**, nao uma tabela. Funciona apenas para SELECT.
- Para projecao de estoque, use `ServicoEstoqueSimples` (servico em `app.estoque.services`).
- Para adicionar novos models, edite `MODELS_PERMITIDOS` em `loader_executor.py`.

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

## Novos Módulos v3.4 - Documentação Detalhada

### Self-Consistency Check (response_reviewer.py)

Revisa automaticamente as respostas antes de enviar ao usuário:

```python
# Fluxo:
# Dados -> Claude (gera) -> ResponseReviewer (revisa) -> Resposta final

# Verificações realizadas:
# 1. Números não presentes nos dados (detecta alucinações)
# 2. Nomes de campos incorretos (conforme CLAUDE.md)
# 3. Contradições entre resposta e contexto
# 4. Completude da resposta

# Pode ser desativado:
from app.claude_ai_lite.core.responder import HABILITAR_REVISAO
# HABILITAR_REVISAO = False
```

### Extração de Entidades Compostas (composite_extractor.py)

Extrai condições implícitas de perguntas complexas:

```python
# Pergunta: "Pedidos do cliente Assai sem agendamento"
# Antes: cliente = "Assai", filtro "sem agendamento" IGNORADO
# Agora: cliente = "Assai", filtro agendamento IS NULL APLICADO

# Condições suportadas:
# - "sem agendamento" -> agendamento IS NULL
# - "sem expedição" -> expedicao IS NULL
# - "atrasados" -> expedicao < hoje
# - "pendentes" -> sincronizado_nf = False
# - "abertos" -> status = 'ABERTO'
# - "hoje" -> expedicao = data atual
# - "com saldo" -> qtd_saldo > 0

# NOVO v3.4.1: Extração de datas específicas
# - "dia 27/11" -> data_expedicao = 2025-11-27
# - "pro dia 27/11" -> data_expedicao = 2025-11-27
# - "para 28/11/2025" -> data_expedicao = 2025-11-28
# - "data de expedição 30/11" -> data_expedicao = 2025-11-30

# Uso programático:
from app.claude_ai_lite.core.composite_extractor import extrair_condicoes, enriquecer_entidades

resultado = extrair_condicoes("pedidos sem agendamento")
# {'condicoes': [{'campo': 'agendamento', 'operador': 'is_null', ...}], ...}

# Com data específica:
resultado = extrair_condicoes("criar separação pro dia 27/11")
# {'condicoes': [], 'data_especifica': date(2025, 11, 27), ...}

# Enriquecer entidades (usado pelo orchestrator):
entidades, filtros = enriquecer_entidades("criar pro dia 27/11", {'num_pedido': 'VCD123'})
# entidades agora inclui: {'data_expedicao': '2025-11-27', '_data_especifica_usuario': True}
```

### Loop de Feedback Automático (feedback_loop.py)

Analisa perguntas não respondidas e sugere melhorias:

```python
from app.claude_ai_lite.core.feedback_loop import analisar_gaps

# Analisa últimos 7 dias
resultado = analisar_gaps(dias=7)

# Retorna:
# {
#   'total_analisado': 15,
#   'grupos': [
#     {'padrao': 'cliente_sem_condicao', 'total': 7, 'sugestao': 'Criar filtro composto'},
#     {'padrao': 'lista_atrasados', 'total': 3, 'sugestao': 'Criar filtro: data < hoje'},
#   ],
#   'insights': ['🚨 1 padrão crítico encontrado'],
#   'sugestoes_priorizadas': [...]
# }
```

### Histórico Rico com Itens Numerados (conversation_context.py)

Permite referências como "o pedido 2", "quais são os outros?":

```python
from app.claude_ai_lite.core.conversation_context import ConversationContextManager

# Registra itens da resposta (feito automaticamente pelo orchestrator)
ConversationContextManager.registrar_itens_numerados(usuario_id, dados)

# Resolve referências
item = ConversationContextManager.resolver_referencia_numero("o pedido 2", usuario_id)
# Retorna dados do item #2

# Suportado:
# - "o pedido 2", "item 3", "o 2º da lista"
# - "e os outros?", "quais são os outros?"
```

---

## LACUNAS IDENTIFICADAS - O que falta implementar

### 1. ~~Executor de Loaders Gerados~~ - IMPLEMENTADO v3.2
~~O IA Trainer gera codigo tipo `loader`, mas nao ha forma de executar.~~
**Solucao:** `LoaderExecutor` com JSON estruturado (JOINs, filtros, agregacoes).

### 2. ~~Filtros Complexos~~ - IMPLEMENTADO v3.2
~~`aplicar_filtros_aprendidos()` so aceita SQL puro via `text()`.~~
**Solucao:** `LoaderExecutor` suporta ilike, is_null, in, between, contains, etc.

### 3. ~~Entidades Compostas~~ - IMPLEMENTADO v3.4
~~Perguntas como "sem agendamento" nao eram processadas.~~
**Solucao:** `CompositeExtractor` extrai condições implícitas automaticamente.

### 4. ~~Self-Review de Respostas~~ - IMPLEMENTADO v3.4
~~Respostas podiam conter informações inventadas (alucinações).~~
**Solucao:** `ResponseReviewer` valida coerência antes de enviar.

### 5. Integracao Automatica IA Trainer -> Orchestrator (PARCIAL)
Loaders gerados podem ser chamados via gatilhos.
**Melhoria futura:** Criar Capability generica que carrega e executa loaders aprendidos.

### 6. Tipo `capability` (PENDENTE)
Nao ha como criar capacidades dinamicamente.
**Solucao futura:** Avaliar necessidade vs uso de loaders estruturados.

---

## Configuracao

```env
ANTHROPIC_API_KEY=sk-ant-...
REDIS_URL=redis://...  # Opcional
```

Modelo utilizado: `claude-sonnet-4-5-20250929`
