# PLANO DE FLEXIBILIZAÇÃO DO CLAUDE AI LITE

**Data:** 26/11/2025
**Objetivo:** Remover limitações artificiais e dar mais autonomia ao Claude

---

## RESUMO DAS MUDANÇAS

| # | Limitação | Arquivo | Impacto | Prioridade |
|---|-----------|---------|---------|------------|
| 1.1 | MAX_ETAPAS=5 fixo | agent_planner.py | ALTO | ALTA |
| 1.2 | Fluxo sequencial rígido | orchestrator.py | ALTO | ALTA |
| 1.3 | Domínios hardcoded | orchestrator.py | MÉDIO | MÉDIA |
| 1.4 | Tipos de ferramenta fixos | tool_registry.py | BAIXO | BAIXA |
| 2.1 | Prompt com SEMPRE/NUNCA | agent_planner.py | ALTO | ALTA |
| 2.2 | Exemplos JSON fixos | agent_planner.py | MÉDIO | MÉDIA |
| 2.3 | CAPABILITIES hardcoded | intelligent_extractor.py | ALTO | ALTA |
| 2.4 | Regras de resposta fixas | system_base.py | BAIXO | BAIXA |
| 2.5 | Opções sempre A/B/C | system_base.py | MÉDIO | MÉDIA |
| 3.1 | MAX_HISTORICO=40 | memory.py | MÉDIO | MÉDIA |
| 3.2 | MAX_TOKENS=8192 | memory.py | BAIXO | BAIXA |
| 3.3 | Cache TTL=300s | tool_registry.py | BAIXO | BAIXA |
| 3.4 | Limite 1000 registros | loader_executor.py | MÉDIO | MÉDIA |
| 3.5 | HABILITAR_REVISAO=True | responder.py | MÉDIO | MÉDIA |
| 4.1 | Schema hardcoded | tool_registry.py | ALTO | ALTA |
| 5.1 | JSON de extração fixo | intelligent_extractor.py | MÉDIO | MÉDIA |
| 5.2 | Flag [REPROCESSAR] | orchestrator.py | BAIXO | BAIXA |

---

## NOVO ARQUIVO: config.py

Criar arquivo centralizado de configuração que permite ajustes sem alterar código.

```python
# app/claude_ai_lite/config.py
"""
Configurações do Claude AI Lite.

FILOSOFIA:
- Configurações são DIRETRIZES, não regras absolutas
- Claude pode solicitar override em casos justificados
- Valores são defaults que podem ser ajustados por contexto
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum


class NivelAutonomia(Enum):
    """Nível de autonomia do Claude nas decisões."""
    RESTRITO = "restrito"      # Segue regras à risca
    BALANCEADO = "balanceado"  # Default - equilibra regras e julgamento
    AUTONOMO = "autonomo"      # Mais liberdade para decidir


@dataclass
class ConfigPlanejamento:
    """Configurações do AgentPlanner."""

    # Etapas
    max_etapas_default: int = 5
    max_etapas_complexas: int = 10  # Claude pode solicitar se justificar
    permitir_solicitacao_etapas_extras: bool = True

    # Filtros
    filtro_cliente_obrigatorio: bool = True  # SEGURANÇA: manter True
    filtro_pedido_obrigatorio: bool = True   # SEGURANÇA: manter True
    permitir_consultas_agregadas_sem_filtro: bool = True  # Ex: "total faturado hoje"


@dataclass
class ConfigOrquestracao:
    """Configurações do Orchestrator."""

    # Fluxo
    permitir_pular_etapas: bool = True  # Claude decide quais etapas são necessárias
    etapas_obrigatorias: List[str] = field(default_factory=lambda: [
        "extrair_inteligente"  # Esta é sempre necessária
    ])
    etapas_opcionais: List[str] = field(default_factory=lambda: [
        "carregar_conhecimento",
        "buscar_memoria"
    ])

    # Domínios customizáveis
    handlers_customizados: Dict[str, str] = field(default_factory=dict)
    # Exemplo: {"urgente": "processar_urgente", "preview": "processar_preview"}


@dataclass
class ConfigExtracao:
    """Configurações do IntelligentExtractor."""

    # Capabilities
    carregar_capabilities_dinamicamente: bool = True  # Usar ToolRegistry
    permitir_campos_extras_na_resposta: bool = True   # Claude pode adicionar contexto

    # Confiança
    limiar_confianca_minima: float = 0.3  # Abaixo disso, pede clarificação


@dataclass
class ConfigResposta:
    """Configurações do Responder."""

    # Revisão
    revisao_automatica: bool = True
    revisao_condicional: bool = True  # Claude decide se precisa revisar
    limiar_confianca_sem_revisao: float = 0.9  # Acima disso, não revisa

    # Opções
    min_opcoes: int = 2
    max_opcoes: int = 5  # Não mais fixo em 3
    permitir_opcoes_customizadas: bool = True


@dataclass
class ConfigMemoria:
    """Configurações de memória e histórico."""

    # Histórico
    max_mensagens_default: int = 40
    estrategia_historico: str = "recent_and_relevant"  # "recent_only" ou "recent_and_relevant"

    # Tokens
    max_tokens_contexto: int = 8192
    ajustar_por_modelo: bool = True  # Ajusta baseado no modelo Claude usado
    tokens_por_modelo: Dict[str, int] = field(default_factory=lambda: {
        "haiku": 4096,
        "sonnet": 8192,
        "opus": 16384
    })


@dataclass
class ConfigFerramentas:
    """Configurações do ToolRegistry."""

    # Cache
    cache_ttl_segundos: int = 300
    cache_ttl_dinamico: bool = True  # Ajusta baseado em volatilidade

    # Schema
    schema_dinamico: bool = True  # Usar SQLAlchemy inspect
    schema_cache_ttl: int = 3600  # 1 hora (schema muda pouco)

    # Tipos
    tipos_ferramenta_customizados: Dict[str, str] = field(default_factory=dict)
    # Exemplo: {"ml_model": "executar_ml_model"}


@dataclass
class ConfigLimites:
    """Limites de segurança (NÃO FLEXIBILIZAR SEM MOTIVO)."""

    # Resultados
    max_registros_query: int = 1000  # SEGURANÇA: protege o banco
    max_registros_relatorio: int = 5000  # Para relatórios explícitos

    # Tempo
    timeout_query_segundos: int = 30
    timeout_planejamento_segundos: int = 60


@dataclass
class ConfigClaudeAILite:
    """Configuração master do módulo."""

    nivel_autonomia: NivelAutonomia = NivelAutonomia.BALANCEADO

    planejamento: ConfigPlanejamento = field(default_factory=ConfigPlanejamento)
    orquestracao: ConfigOrquestracao = field(default_factory=ConfigOrquestracao)
    extracao: ConfigExtracao = field(default_factory=ConfigExtracao)
    resposta: ConfigResposta = field(default_factory=ConfigResposta)
    memoria: ConfigMemoria = field(default_factory=ConfigMemoria)
    ferramentas: ConfigFerramentas = field(default_factory=ConfigFerramentas)
    limites: ConfigLimites = field(default_factory=ConfigLimites)


# Singleton da configuração
_config: Optional[ConfigClaudeAILite] = None


def get_config() -> ConfigClaudeAILite:
    """Retorna configuração singleton."""
    global _config
    if _config is None:
        _config = ConfigClaudeAILite()
    return _config


def set_config(config: ConfigClaudeAILite):
    """Define configuração customizada."""
    global _config
    _config = config
```

---

## IMPLEMENTAÇÃO 1.1: MAX_ETAPAS DINÂMICO

### Arquivo: agent_planner.py

**ANTES (linha 32):**
```python
MAX_ETAPAS = 5
```

**DEPOIS:**
```python
from ..config import get_config

def _get_max_etapas(plano: Dict = None) -> int:
    """
    Retorna máximo de etapas permitidas.

    Pode aumentar se Claude solicitar com justificativa.
    """
    config = get_config()
    max_default = config.planejamento.max_etapas_default

    # Se plano solicita mais etapas E config permite
    if plano and config.planejamento.permitir_solicitacao_etapas_extras:
        etapas_solicitadas = plano.get('etapas_necessarias')
        justificativa = plano.get('justificativa_etapas_extras')

        if etapas_solicitadas and justificativa:
            max_complexas = config.planejamento.max_etapas_complexas
            return min(etapas_solicitadas, max_complexas)

    return max_default
```

**MUDANÇA NO PROMPT (linha 230):**

**ANTES:**
```python
3. Se precisar combinar dados, use múltiplas etapas (máximo {MAX_ETAPAS})
```

**DEPOIS:**
```python
3. Se precisar combinar dados, use múltiplas etapas (default: {max_etapas_default})
   - Se precisar de MAIS etapas, adicione no JSON:
     "etapas_necessarias": N,
     "justificativa_etapas_extras": "motivo"
   - Máximo absoluto: {max_etapas_complexas} etapas
```

**MUDANÇA NA EXECUÇÃO (linha 139):**

**ANTES:**
```python
for i, etapa in enumerate(plano['etapas'][:MAX_ETAPAS]):
```

**DEPOIS:**
```python
max_etapas = _get_max_etapas(plano)
for i, etapa in enumerate(plano['etapas'][:max_etapas]):
```

---

## IMPLEMENTAÇÃO 1.2: FLUXO FLEXÍVEL NO ORCHESTRATOR

### Arquivo: orchestrator.py

**CONCEITO:** Criar uma estrutura de "decisões de roteamento" onde o Claude pode indicar quais etapas pular.

**ANTES (fluxo fixo):**
```python
# 1. Obter estado estruturado
# 2. Carregar conhecimento
# 3. Verificar aprendizado
# 4. Extração inteligente
# 5. Tratamentos especiais
# 6. AgentPlanner
# 7. Gerar resposta
```

**DEPOIS:**
```python
def processar_consulta(...) -> str:
    """Processa consulta com fluxo flexível."""

    config = get_config()

    # 1. SEMPRE: Validação básica
    if not consulta or not consulta.strip():
        return "Por favor, informe sua consulta."

    # 2. SEMPRE: Extração inteligente (retorna também decisões de roteamento)
    resultado_extracao = _extrair_inteligente_com_roteamento(
        consulta,
        usuario_id,
        config.orquestracao.permitir_pular_etapas
    )

    intencao = resultado_extracao['intencao']
    roteamento = resultado_extracao.get('roteamento', {})

    # 3. CONDICIONAL: Carregar conhecimento
    conhecimento_negocio = ""
    if roteamento.get('carregar_conhecimento', True):
        conhecimento_negocio = _carregar_conhecimento_negocio(usuario_id)

    # 4. CONDICIONAL: Buscar memória
    contexto_memoria = None
    if roteamento.get('buscar_memoria', True):
        contexto_memoria = _buscar_memoria(usuario_id)

    # 5. CONDICIONAL: Estado estruturado
    contexto_estruturado = ""
    if roteamento.get('usar_estado', True):
        contexto_estruturado = obter_estado_json(usuario_id)

    # 6. Roteamento por tipo (agora extensível)
    handler = _obter_handler(intencao, config)
    if handler:
        return handler(intencao, usuario_id, usuario, consulta, contexto_memoria)

    # 7. AgentPlanner (default)
    # ...resto do código
```

**NOVA ESTRUTURA DE ROTEAMENTO no prompt do extrator:**
```python
# Adicionar no JSON de resposta do extrator:
"roteamento": {
    "carregar_conhecimento": true/false,  # Default: true
    "buscar_memoria": true/false,         # Default: true
    "usar_estado": true/false,            # Default: true
    "motivo": "explicação se pulou algo"  # Opcional
}
```

---

## IMPLEMENTAÇÃO 1.3: DOMÍNIOS EXTENSÍVEIS

### Arquivo: orchestrator.py

**ANTES (hardcoded):**
```python
if dominio == "clarificacao":
    resposta = _processar_clarificacao(...)

if dominio == "follow_up" or intencao_tipo in ("follow_up", "detalhar"):
    resposta = _processar_follow_up(...)

if dominio == "acao":
    resposta = _processar_acao(...)
```

**DEPOIS:**
```python
# Registry de handlers
_HANDLERS_DOMINIO: Dict[str, Callable] = {
    "clarificacao": _processar_clarificacao,
    "follow_up": _processar_follow_up,
    "acao": _processar_acao,
}


def registrar_handler(dominio: str, handler: Callable):
    """Registra handler customizado para um domínio."""
    _HANDLERS_DOMINIO[dominio] = handler


def _obter_handler(intencao: Dict, config: ConfigClaudeAILite) -> Optional[Callable]:
    """Obtém handler para o domínio/intenção."""
    dominio = intencao.get('dominio', '')
    intencao_tipo = intencao.get('intencao', '')

    # Handlers customizados da config têm prioridade
    if dominio in config.orquestracao.handlers_customizados:
        handler_name = config.orquestracao.handlers_customizados[dominio]
        return globals().get(handler_name)

    # Handlers padrão
    if dominio in _HANDLERS_DOMINIO:
        return _HANDLERS_DOMINIO[dominio]

    # Verifica intenção também
    if intencao_tipo in ("follow_up", "detalhar"):
        return _HANDLERS_DOMINIO.get("follow_up")

    return None
```

---

## IMPLEMENTAÇÃO 2.1: PROMPTS MENOS PRESCRITIVOS

### Arquivo: agent_planner.py

**ANTES (linhas 233-246):**
```python
⚠️ REGRAS CRÍTICAS:

FILTROS OBRIGATÓRIOS:
- Se há raz_social_red nas entidades, SEMPRE inclua filtro de cliente em TODAS as queries
- Se há num_pedido nas entidades, SEMPRE inclua filtro de pedido em TODAS as queries
- Se há cod_produto nas entidades, SEMPRE inclua filtro de produto em TODAS as queries
- NUNCA retorne dados de TODOS os clientes quando há um cliente específico no contexto
```

**DEPOIS:**
```python
=== DIRETRIZES DE FILTROS ===

SEGURANÇA DE DADOS (obrigatório):
- Quando há cliente/pedido específico no contexto, INCLUA o filtro correspondente
- Exceção permitida: consultas agregadas/estatísticas (ex: "total faturado hoje")

BOAS PRÁTICAS (recomendado):
- Inclua campos de identificação (raz_social_red, num_pedido) no retorno
- Use "ilike" com "%" para buscas de texto
- Retorne apenas dados relevantes para a pergunta

SE PRECISAR DIVERGIR:
- Adicione "justificativa_filtro": "motivo" no JSON
- Exemplo: consulta de ranking de clientes não filtra por cliente específico
```

---

## IMPLEMENTAÇÃO 2.2: EXEMPLOS MAIS FLEXÍVEIS

### Arquivo: agent_planner.py

**ADICIONAR após os exemplos (linha ~380):**
```python
=== NOTA SOBRE OS EXEMPLOS ===

Os exemplos acima são ILUSTRATIVOS. Você pode:
- Adaptar a estrutura para casos únicos
- Combinar abordagens de diferentes exemplos
- Criar estruturas diferentes se necessário

O importante é que o JSON seja válido e tenha:
- "etapas": lista de etapas a executar
- Cada etapa tenha "ferramenta" e "descricao"
```

---

## IMPLEMENTAÇÃO 2.3: CAPABILITIES DINÂMICAS

### Arquivo: intelligent_extractor.py

**ANTES (linhas 34-145):**
```python
CAPABILITIES_DISPONIVEIS = """
=== CAPABILITIES DISPONÍVEIS ===
...111 linhas de texto fixo...
"""
```

**DEPOIS:**
```python
def _carregar_capabilities_dinamicas() -> str:
    """
    Carrega capabilities dinamicamente do ToolRegistry.

    Benefícios:
    - Sempre atualizado com novas capabilities
    - Inclui códigos gerados ativos
    - Não precisa manutenção manual
    """
    try:
        from .tool_registry import get_tool_registry

        registry = get_tool_registry()
        ferramentas = registry.listar_ferramentas(incluir_generica=False)

        return registry.formatar_para_prompt(ferramentas)
    except Exception as e:
        logger.warning(f"[EXTRACTOR] Erro ao carregar capabilities: {e}")
        return _CAPABILITIES_FALLBACK  # Manter string fixa como fallback


# Manter string original como fallback
_CAPABILITIES_FALLBACK = """...(conteúdo original)..."""


class IntelligentExtractor:
    def extrair(self, texto: str, ...) -> Dict[str, Any]:
        # Carregar capabilities dinamicamente
        config = get_config()
        if config.extracao.carregar_capabilities_dinamicamente:
            capabilities_prompt = _carregar_capabilities_dinamicas()
        else:
            capabilities_prompt = _CAPABILITIES_FALLBACK

        # ...resto do código usa capabilities_prompt
```

---

## IMPLEMENTAÇÃO 2.5: OPÇÕES FLEXÍVEIS

### Arquivo: system_base.py

**ANTES (linhas 42-44):**
```python
* Opção A: Envio TOTAL - aguarda todos os itens terem estoque
* Opção B: Envio PARCIAL - exclui 1 item gargalo (se houver)
* Opção C: Envio PARCIAL - exclui 2 itens gargalo (se houver)
```

**DEPOIS:**
```python
**Análise de Disponibilidade (Quando Posso Enviar?):**
- Pergunta: "Quando posso enviar o pedido VCD123?"
- Analisa o estoque atual vs quantidade necessária de cada item
- Gera OPÇÕES DE ENVIO (quantidade varia conforme análise):
  * Pode ter 2, 3, 4 ou mais opções
  * Adapte as opções à situação específica
  * Exemplos de opções:
    - Envio TOTAL: aguarda todos os itens
    - Envio PARCIAL: exclui itens gargalo
    - Envio URGENTE: envia o que tem hoje
    - Envio PROGRAMADO: aguarda data específica
```

---

## IMPLEMENTAÇÃO 3.x: CONFIGURAÇÕES DINÂMICAS

### Arquivo: memory.py

**ANTES:**
```python
MAX_HISTORICO = 40
MAX_TOKENS_CONTEXTO = 8192
```

**DEPOIS:**
```python
from ..config import get_config

def _get_max_historico() -> int:
    """Retorna limite de histórico baseado na config."""
    return get_config().memoria.max_mensagens_default

def _get_max_tokens() -> int:
    """Retorna limite de tokens baseado no modelo."""
    config = get_config()
    if config.memoria.ajustar_por_modelo:
        # TODO: Detectar modelo atual
        modelo = "sonnet"  # Default
        return config.memoria.tokens_por_modelo.get(modelo, 8192)
    return config.memoria.max_tokens_contexto
```

### Arquivo: responder.py

**ANTES:**
```python
HABILITAR_REVISAO = True
```

**DEPOIS:**
```python
from ..config import get_config

def _deve_revisar(confianca: float = 0.5) -> bool:
    """Decide se deve revisar resposta."""
    config = get_config()

    if not config.resposta.revisao_automatica:
        return False

    if config.resposta.revisao_condicional:
        # Alta confiança = não precisa revisar
        return confianca < config.resposta.limiar_confianca_sem_revisao

    return True
```

---

## IMPLEMENTAÇÃO 4.1: SCHEMA DINÂMICO

### Arquivo: tool_registry.py

**ANTES (linhas 262-495):**
```python
def formatar_schema_resumido(self, dominio: str = None) -> str:
    schemas = {
        'carteira': """...""",
        'estoque': """...""",
        # ...233 linhas hardcoded
    }
```

**DEPOIS:**
```python
def formatar_schema_resumido(self, dominio: str = None) -> str:
    """
    Retorna schema das tabelas relevantes.

    Se config.ferramentas.schema_dinamico = True:
        Usa SQLAlchemy inspect para gerar schema
    Senão:
        Usa schema hardcoded (fallback)
    """
    config = get_config()

    if config.ferramentas.schema_dinamico:
        return self._gerar_schema_dinamico(dominio)

    return self._get_schema_hardcoded(dominio)

def _gerar_schema_dinamico(self, dominio: str = None) -> str:
    """Gera schema usando SQLAlchemy inspect."""
    try:
        from sqlalchemy import inspect
        from app import db

        # Mapeia domínios para models
        models_por_dominio = {
            'carteira': ['CarteiraPrincipal', 'Separacao', 'Pedido'],
            'estoque': ['MovimentacaoEstoque', 'CadastroPalletizacao'],
            'fretes': ['Embarque', 'EmbarqueItem', 'Frete'],
            'faturamento': ['FaturamentoProduto']
        }

        models = models_por_dominio.get(dominio, [])
        if not models:
            # Retorna todos
            models = [m for lista in models_por_dominio.values() for m in lista]

        linhas = [f"=== SCHEMA DO BANCO ({dominio or 'geral'}) ===\n"]

        for model_name in models:
            model = self._get_model_class(model_name)
            if model:
                linhas.append(self._formatar_model(model))

        return "\n".join(linhas)

    except Exception as e:
        logger.warning(f"[TOOL_REGISTRY] Schema dinâmico falhou: {e}")
        return self._get_schema_hardcoded(dominio)

def _formatar_model(self, model) -> str:
    """Formata um model para o prompt."""
    from sqlalchemy import inspect

    mapper = inspect(model)
    linhas = [f"\n=== TABELA: {model.__tablename__} ==="]

    # Campos
    linhas.append("Campos:")
    for column in mapper.columns:
        tipo = str(column.type)[:20]
        nullable = "opcional" if column.nullable else "obrigatório"
        linhas.append(f"  - {column.name}: {tipo} ({nullable})")

    # Relacionamentos
    if mapper.relationships:
        linhas.append("Relacionamentos:")
        for rel in mapper.relationships:
            linhas.append(f"  - {rel.key} -> {rel.mapper.class_.__name__}")

    return "\n".join(linhas)

def _get_model_class(self, name: str):
    """Obtém classe do model pelo nome."""
    # Importa models sob demanda
    model_imports = {
        'CarteiraPrincipal': 'app.carteira.models',
        'Separacao': 'app.separacao.models',
        'Pedido': 'app.pedidos.models',
        'MovimentacaoEstoque': 'app.estoque.models',
        'CadastroPalletizacao': 'app.producao.models',
        'Embarque': 'app.embarques.models',
        'EmbarqueItem': 'app.embarques.models',
        'Frete': 'app.fretes.models',
        'FaturamentoProduto': 'app.faturamento.models'
    }

    module_path = model_imports.get(name)
    if module_path:
        import importlib
        module = importlib.import_module(module_path)
        return getattr(module, name, None)

    return None

# Manter schema hardcoded como fallback
def _get_schema_hardcoded(self, dominio: str = None) -> str:
    """Schema hardcoded (fallback)."""
    schemas = {
        # ...manter conteúdo original como fallback
    }
    return schemas.get(dominio, schemas.get('geral', ''))
```

---

## IMPLEMENTAÇÃO 5.1: JSON DE EXTRAÇÃO FLEXÍVEL

### Arquivo: intelligent_extractor.py

**ANTES:**
```python
{{
    "dominio": "carteira|estoque|acao|geral",
    "intencao": "nome_da_intencao",
    ...campos fixos...
}}
```

**DEPOIS:**
```python
{{
    "dominio": "carteira|estoque|acao|geral",
    "intencao": "nome_da_intencao",
    "tipo": "consulta|acao|modificacao|confirmacao|cancelamento|clarificacao",
    "entidades": {{...}},
    "ambiguidade": {{
        "existe": false,
        "pergunta": "...",
        "opcoes": [...]
    }},
    "confianca": 0.0 a 1.0,

    // NOVOS CAMPOS OPCIONAIS - adicione se relevante:
    "roteamento": {{
        "carregar_conhecimento": true,
        "buscar_memoria": true,
        "usar_estado": true,
        "motivo": "explicação se pulou algo"
    }},
    "contexto_adicional": "informação extra que você quer passar",
    "avisos": ["aviso 1", "aviso 2"],
    "sugestao_alternativa": "se detectou que usuário pode querer algo diferente"
}}
```

---

## ORDEM DE IMPLEMENTAÇÃO SUGERIDA

### Fase 1: Fundação (criar primeiro)
1. ✅ Criar `config.py` com todas as configurações
2. ✅ Atualizar imports em todos os arquivos

### Fase 2: Alta Prioridade
3. 1.1 - MAX_ETAPAS dinâmico
4. 2.3 - Capabilities dinâmicas
5. 4.1 - Schema dinâmico

### Fase 3: Média Prioridade
6. 1.2 - Fluxo flexível
7. 2.1 - Prompts menos prescritivos
8. 2.5 - Opções flexíveis
9. 3.x - Configurações dinâmicas
10. 5.1 - JSON flexível

### Fase 4: Baixa Prioridade
11. 1.3 - Domínios extensíveis
12. 1.4 - Tipos de ferramenta plugáveis
13. 5.2 - Flag [REPROCESSAR] estruturado

---

## TESTES NECESSÁRIOS

Para cada mudança, testar:

1. **Caso básico**: Funciona como antes
2. **Caso novo**: Nova flexibilidade funciona
3. **Caso limite**: Limites de segurança respeitados
4. **Regressão**: Fluxos existentes não quebram

### Exemplos de teste:

```python
# Teste 1.1: MAX_ETAPAS
# Consulta que precisa de 7 etapas
consulta = "Compare estoque de todos os produtos do Atacadão com a produção programada, identifique gargalos e sugira data de envio para cada pedido"
# Espera: Claude solicita mais etapas com justificativa

# Teste 2.3: Capabilities dinâmicas
# Criar nova capability e verificar se aparece no prompt
# Sem precisar alterar intelligent_extractor.py

# Teste 4.1: Schema dinâmico
# Adicionar campo em um model e verificar se aparece no schema
```

---

## ROLLBACK

Se algo der errado:

1. Cada mudança é isolada
2. `config.py` tem valores default que replicam comportamento atual
3. Schemas hardcoded mantidos como fallback
4. Basta setar `config.ferramentas.schema_dinamico = False` para voltar ao comportamento antigo

---

**Próximo passo:** Qual implementação você quer que eu faça primeiro?
