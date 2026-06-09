<!-- doc:meta
tipo: reference
camada: L2
sot_de: —
hub: .claude/references/INDEX.md
superseded_by: —
atualizado: 2026-06-09
-->
# Protocolo de Memoria do Agente

> **Papel:** Protocolo de Memoria do Agente.

## Indice

- [Ciclo de Vida](#ciclo-de-vida)
- [Formato Canonico de Armazenamento (meta JSONB)](#formato-canonico-de-armazenamento-meta-jsonb)
- [Categorias e Decay](#categorias-e-decay)
- [Paths Padrao](#paths-padrao)
- [Criterios de Qualidade](#criterios-de-qualidade)
- [Protecoes](#protecoes)
- [Triggers de Salvamento](#triggers-de-salvamento)
  - [Automatico (silencioso)](#automatico-silencioso)
  - [Explicito (com confirmacao)](#explicito-com-confirmacao)
  - [Extracao pos-sessao automatica (2 pipelines)](#extracao-pos-sessao-automatica-2-pipelines)
- [Formato Narrativo](#formato-narrativo)

**Referencia tecnica** — documento de consulta, NAO implementacao.

---

## Ciclo de Vida

```
create → enrich → consolidate → cold → delete
```

1. **create**: Agente salva memoria via `save_memory` (auto ou explicito)
2. **enrich**: Extracao pos-sessao (`pattern_analyzer.py`) adiciona conhecimento tacito
3. **consolidate**: `memory_consolidator.py` mescla memorias redundantes periodicamente
4. **cold**: Memorias com `usage_count >= 20` e `effective_count/usage_count < 10%` migram para tier frio (`is_cold=True`)
5. **delete**: Memorias cold sem acesso por 90+ dias podem ser removidas

---

## Formato Canonico de Armazenamento (meta JSONB)

> Redesenho 2026-06-08 (formato canonico de memorias). Antes os campos
> discriminantes viviam so no texto do `content`; agora ha uma fonte de verdade
> estruturada.

Memorias estruturadas tem os campos discriminantes em **`agent_memories.meta`
(JSONB) = fonte de verdade** (indice GIN); o **`content` e derivado**, num formato
sentinela legivel: `[kind:dominio] titulo` + linhas `WHEN:` / `DO:` / `META: nivel=N`.

- **Transparente para o agente**: `save_memory` recebe o conteudo narrativo normal
  (ver [Formato Narrativo](#formato-narrativo)) e **popula `meta` + normaliza o
  `content` automaticamente**. O agente NAO monta o formato sentinela na mao.
- **Serializador**: `app/agente/services/memory_format.py` (puro; parseia 5+
  formatos legados).
- **`kind`** ∈ {`heuristica`, `armadilha`, `protocolo`, `correcao`} (+ `geral` para o
  resto); **`dominio`** = area (recebimento, financeiro, ...).
- **Consumidores preferem `meta`** (via `getattr`) com **fallback ao parse do
  `content`** — memorias legadas sem `meta` continuam funcionando (so nao entram no
  agrupamento por kind/dominio do indice ate receberem `meta`).

### Leitura: `list_memories` = INDICE, nao dump

`list_memories` retorna um **INDICE navegavel** (agrupa por kind/dominio + contagens +
paths, **SEM o conteudo**; filtros kind/dominio/escopo/prefix/query/limit; exclui
frias). Para ler o conteudo de uma memoria, usar **`view_memories(path)`**. As memorias
relevantes ja sao injetadas no boot — `list_memories` serve so para **navegar alem do
injetado** (e resolve o estouro de tokens do dump antigo).

---

## Categorias e Decay

Cada memoria tem `category` que determina seu decay temporal na injecao:

| Categoria | Meia-vida | Exemplos | Decay |
|-----------|-----------|----------|-------|
| `permanent` | Sem decay | user.xml, preferences.xml, permissoes | 1.0 (sempre) |
| `structural` | ~60d | Gotchas Odoo, campos que nao existem, armadilhas | Lento |
| `operational` | ~30d (default) | Workflows, preferencias de formato | Medio |
| `contextual` | ~3d | Alertas, estado do sistema, sessoes recentes | Rapido |
| `cold` | N/A | Memorias depreciadas | Sem injecao automatica |

Implementacao: `_calculate_category_decay()` em `app/agente/sdk/memory_injection.py:271`.
Memorias cold so aparecem via busca explicita (`search_cold_memories`).

---

## Paths Padrao

```
/memories/
  preferences.xml          # Preferencias do usuario (permanent)
  user.xml                 # Perfil do usuario (permanent)
  corrections/             # Correcoes (structural)
  learned/
    patterns.xml           # Padroes aprendidos (structural)
  empresa/                 # Memorias compartilhadas (user_id=0)
    protocolos/            # Arvores de investigacao (Nivel 3+)
    armadilhas/            # Dead ends documentados (Nivel 4+)
    heuristicas/           # Padroes recorrentes generalizados (Nivel 5)
```

---

## Criterios de Qualidade

Uma memoria util atende pelo menos 1 criterio:

| Criterio | Descricao | Exemplo |
|----------|-----------|---------|
| **Prescritiva** | Muda como o agente responde | "Atacadao NAO aceita parcial — sempre completo" |
| **Contextual** | Muda interpretacao de dados | "Denise opera 2a-6a, sabado somente urgencias" |
| **Procedimental** | Descreve como executar algo | "Para reativar embarque: verificar NF, reverter status, recriar separacao" |
| **Corretiva** | Previne erro ja ocorrido | "UPDATE valor_frete NAO recalcula margem — chamar recalcular_margem()" |

NAO salvar: resultados pontuais, status temporarios, informacao disponivel no sistema.

---

## Protecoes

- `user.xml` e `preferences.xml` sao **IMUNES** a consolidacao e remocao
  - FONTE: `memory_consolidator.py:62-65` (PROTECTED_PATHS set)
- Memorias `category='permanent'` com `importance >= 0.7` protegidas de consolidacao
- Extracao pos-sessao: dedup via busca semantica (threshold 0.80) antes de salvar
  - FONTE: `pattern_analyzer.py:_find_similar_empresa_memory()`

---

## Triggers de Salvamento

### Automatico (silencioso)
- Correcao do usuario ("na verdade...", "nao eh isso")
- Preferencia detectada ("prefiro tabela", "mostre peso")
- Regra de negocio nova
- Info profissional (cargo, responsabilidade)
- Acao significativa (lancou pedidos, conferiu faturas)
- Padrao repetido (2+ vezes)

### Explicito (com confirmacao)
- Pedido direto: "lembre que...", "salve isso"
- Operacao destrutiva: `clear_memories`, `delete_memory`

### Extracao pos-sessao automatica (2 pipelines)

| Pipeline | Destino | O que extrai | Trigger |
|----------|---------|--------------|---------|
| Empresa (`extrair_conhecimento_sessao`) | user_id=0 | Protocolos, armadilhas, heuristicas (Taxonomia 5 niveis) | Min 3 msgs, daemon thread |
| Pessoal (`extrair_insights_pessoais_sessao`) | user_id do usuario | Correcoes, preferencias, expertise, contexto | Min 3 msgs, daemon thread |

O pipeline pessoal eh rede de seguranca para o R0 auto-save, que depende do modelo
espontaneamente chamar `save_memory` — comportamento inconsistente em sessoes focadas em skills.

---

## Formato Narrativo

Memoria deve responder: **QUEM** fez, **O QUE**, **POR QUE**, **QUANDO**.

- RUIM: `cliente_frequente: atacadao`
- BOM: `Denise lancou 88 pedidos Atacadao para semana de 10/03. Volume alto, provavel rotina semanal.`
