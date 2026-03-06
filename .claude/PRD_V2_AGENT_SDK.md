# PRD v2 — Memoria Compartilhada por Escopo

**Versao:** 2.1
**Data:** 06/03/2026
**Origem:** PRD v1 + revisao critica (Claude Desktop) + contra-revisao (Claude Code) + reflexao Rafael (armazenamento vs injecao)
**Status:** Draft para validacao

---

## 1. Problema

O sistema de memoria tem dois problemas distintos que se acumulam:

**Problema 1 — Salvamento nao acontece.** Gabriella (Compras) definiu em sessao que "integracao de NF" = vinculacao DFe x PO. O agente nao salvou. A sessao encerrou antes de o agente chamar `save_memory` — porque o salvamento depende 100% da iniciativa do agente durante a conversa, e a conversa nao chegou a uma conclusao operacional. O conhecimento nao "morreu silado na Gabriella" — ele nao foi salvo em lugar nenhum, nem para ela.

**Problema 2 — Mesmo que tivesse salvo, ficaria silado.** O sistema armazena tudo por `user_id`. Se o agente tivesse salvo o termo da Gabriella, ele existiria apenas no user_id=69. Rafael perguntaria a mesma coisa e o agente investigaria do zero.

Os dois problemas sao independentes e precisam de solucoes distintas:

| Problema | Causa raiz | Solucao |
|---|---|---|
| Nao salvou | Salvamento depende de o agente decidir salvar antes da sessao encerrar | Hook pos-sessao (secao 5) |
| Ficaria silado | Toda memoria pertence a um user_id unico | Escopo empresa/dominio (secoes 3-4) |

**Gap adicional:** Termos ambiguos sao tratados como desconhecidos mesmo quando ja definidos — o agente lista opcoes genericas em vez de confirmar com a definicao conhecida.

---

## 2. Decisoes de Arquitetura

Cada decisao abaixo foi debatida e tem justificativa.

### 2.1 Tudo no banco, zero XML

O PRD v1 misturava arvore XML no filesystem com ALTER TABLE no banco. Isso criaria duas fontes de verdade que inevitavelmente dessincronizam.

**Decisao:** Usar exclusivamente o modelo `AgentMemory` existente (`agent_memories`) com novas colunas. O modelo ja tem versionamento (`AgentMemoryVersion`), knowledge graph (`AgentMemoryEntity`), importance scoring, categorias e feedback loop. Nao ha razao para criar sistema paralelo.

### 2.2 user_id=0 com usuario "Sistema", nao user_id NULL

O Desktop sugeriu `user_id` nullable. Problemas:
- `user_id` hoje e `NOT NULL` com FK para `usuarios` — mudar para nullable exige ALTER na constraint
- UniqueConstraint `(user_id, path)` nao funciona com NULLs (PostgreSQL trata NULLs como distintos — permitiria paths duplicados para escopo empresa)
- Toda query precisaria de `COALESCE` ou logica especial

**Decisao:** Criar registro `id=0` na tabela `usuarios` (nome="Sistema", perfil="sistema", status="ativo"). Memorias de escopo empresa pertencem a `user_id=0`. A UniqueConstraint existente funciona sem alteracao. Uma coluna `created_by` registra quem originou a memoria para auditoria.

### 2.3 Sem empresa_id multi-tenant

O Desktop sugeriu `empresa_id` antecipando cenario multi-empresa. A Nacom Goya nao e SaaS, nao tem segunda empresa prevista. Adicionar `empresa_id` custa uma coluna na DDL mas custa filtro obrigatorio em toda query, todo MCP tool, todo service. YAGNI.

### 2.4 Dominio inferido do cadastro, nao perguntado

O Desktop sugeriu perguntar o dominio na primeira interacao. Ninguem quer questionario ao abrir o chat pela primeira vez.

**Decisao:** Usar campo `usuarios.cargo` que ja existe no banco. Mapear cargo para dominio:

| cargo (contem) | dominio |
|---|---|
| compras, recebimento | compras |
| expedicao, logistica, separacao | expedicao |
| financeiro, contas, tesouraria | financeiro |
| comercial, vendas, vendedor | comercial |
| pcp, producao, manufatura | producao |
| ti, sistemas, dev | ti |

Logica: `LOWER(cargo) LIKE '%compras%'` → dominio 'compras'. Se `cargo` e NULL ou nao bate → dominio NULL (sem filtro de dominio, usuario recebe apenas camada empresa + pessoal). Funciona perfeitamente — dominio e otimizacao, nao requisito.

### 2.5 Validacao organica, nao pipeline Haiku→Sonnet

O Desktop sugeriu validacao em dois estagios (Haiku detecta, Sonnet valida) para escopo empresa. Isso adiciona custo, latencia e complexidade para um problema que se resolve organicamente:

**Decisao:** Termos de empresa entram com `status='pendente'` e `importance_score=0.3`. Quando um **segundo usuario diferente** usa o mesmo termo no mesmo sentido, o status muda para `ativo` e `importance_score` sobe para `0.7`. Nenhum modelo extra necessario. O proprio uso confirma.

**Risco mitigado:** Se Haiku extrai errado e salva em escopo empresa, o erro se propaga para todos. Com status pendente, o termo so e injetado como sugestao (confirmacao obrigatoria), nunca como fato. So vira fato apos confirmacao independente.

### 2.6 Termo como chave composta (expressao + dominio)

Nem o PRD v1 nem o Desktop trataram isso: "integracao" em Compras != "integracao" em TI. Um termo nao pode ser chave unica global.

**Decisao:** O path do termo inclui o dominio: `/memories/empresa/termos/compras/integracao-nf` vs `/memories/empresa/termos/ti/integracao-erp`. Termos sem dominio especifico ficam em `/memories/empresa/termos/_geral/`. A unicidade e garantida por `(user_id=0, path)`.

### 2.7 Invalidacao por desuso, nao por TTL

Termos mudam. Processos mudam. TTL arbitrario (90 dias) invalida termos perfeitamente validos so porque ninguem perguntou.

**Decisao:** Campo `last_confirmed_at` (timestamp do ultimo uso confirmado). Termo que ninguem usa em 180 dias → `status='pendente'` novamente (precisa de re-confirmacao). Verificacao via job periodico (semanal), nao em tempo real.

### 2.8 Armazenamento amplo, injecao estreita

O PRD v2 original tratava armazenamento e injecao como a mesma coisa. Sao problemas distintos com estrategias opostas:

| Camada | Estrategia | Risco de errar |
|---|---|---|
| **Armazenar** | Amplo — salvar mais do que o necessario | Perder conhecimento (Gabriella) custa mais que ter memoria sobrando |
| **Injetar no contexto** | Estreito — so o relevante para ESTA conversa | 50 memorias medianas diluem as 3 que importam |

**Salvar demais custa quase nada.** Memorias ficam no banco, `is_cold=True` no pior caso. A ~70 usuarios, mesmo apos 12 meses, o volume de memorias empresa sera centenas, nao milhares.

**Injetar demais degrada a qualidade.** O contexto do agente tem limite. Cada memoria injetada compete por atencao. A solucao e filtrar na hora de injetar, nao na hora de salvar.

**Infraestrutura RAG ja existe e nao esta conectada.** O sistema ja tem:
- `AgentMemoryEmbedding` (tabela `agent_memory_embeddings`) com pgvector Vector(1024)
- Voyage API para gerar embeddings
- Cosine similarity nativo via pgvector (indice HNSW)
- 8 outros modelos de embedding ja em producao (SSW docs, produtos, financeiro, sessoes, SQL templates, rotas, transportadoras, devolucoes)

O que falta e o **wiring**: `memory_mcp_tool.py` consulta memorias por path (`get_by_path`, `list_directory`), nunca por similaridade semantica. O retrieval de memorias hoje e 100% por caminho, 0% por relevancia.

**Decisao — tres fases de operacao:**

```
FASE 1: INICIO DE SESSAO (always-on, sem RAG)
  → Perfil do usuario + termos ativos do dominio dele
  → 5-10 memorias fixas, selecionadas por escopo + dominio
  → Custo: 1 query SQL com filtro

FASE 2: DURANTE A CONVERSA (on-demand via RAG)
  → Usuario menciona "integracao de NF"
  → Embedding da frase → cosine_similarity contra agent_memory_embeddings
  → Surfacea 3-5 memorias mais relevantes para ESTE contexto
  → Inclui memorias de todos os escopos (pessoal + dominio + empresa)
  → Nao polui contexto com memorias irrelevantes
  → Custo: 1 embedding Voyage + 1 query pgvector por trigger

FASE 3: POS-SESSAO (amplo, sem filtro)
  → Hook extrai TUDO que parece relevante — melhor sobrar que faltar
  → Salva com status=pendente, importance_score=0.3
  → Gera embedding via Voyage API para cada memoria nova
  → Nao importa se salva demais — RAG filtra na injecao
  → Custo: ~$0.001 por memoria (embedding Voyage)
```

### 2.9 Role Awareness — o que o agente deve aprender

O PRD v2 original focava em ONDE armazenar e COMO validar, mas nao dizia ao agente O QUE prestar atencao. O system_prompt define capacidades (consultar pedidos, criar separacoes) mas nao define **objetivos de aprendizado**. O agente nao sabe que "sou da area de compras" e informacao critica porque ninguem disse a ele que mapear usuarios a dominios faz parte do seu trabalho.

**Decisao:** Adicionar ao system_prompt (R0) uma secao explicita de "aprendizado proativo":

```
Alem de responder perguntas, voce esta construindo conhecimento organizacional.
Preste atencao especial a:

1. VOCABULARIO OPERACIONAL — quando alguem define um termo ("quando digo X, quero dizer Y")
   → Salvar em empresa/termos com dominio do usuario

2. IDENTIDADE PROFISSIONAL — quando alguem revela cargo, setor, equipe
   → Salvar em empresa/usuarios

3. REGRAS POR CLIENTE — "Atacadao sempre pede completo", "Assai aceita parcial"
   → Salvar em empresa/regras com status=pendente

4. CORRECOES — quando o usuario corrige algo que voce disse
   → Salvar em pessoal/corrections E avaliar se eh correcao de escopo empresa

5. PREFERENCIAS DE PROCESSO — "primeiro separa, depois agenda", "nunca embarcar sem NF"
   → Salvar em empresa/processos com status=pendente

Esses tipos de informacao sao MAIS importantes de salvar que o conteudo especifico da conversa.
O conteudo da conversa morre com a sessao. O conhecimento organizacional persiste.
```

Isso e uma mudanca de **prompt**, nao de banco. E possivelmente a mudanca mais impactante do PRD inteiro — porque se o agente nao identifica o que e importante, nenhum hook pos-sessao compensa.

---

## 3. Modelo de Dados

### 3.1 Novas colunas em `agent_memories`

```sql
-- Escopo: pessoal (default, compativel com tudo existente), empresa, dominio
ALTER TABLE agent_memories
ADD COLUMN escopo VARCHAR(20) NOT NULL DEFAULT 'pessoal';

-- Dominio: NULL para pessoal/empresa-geral, 'compras'/'expedicao'/etc para dominio
ALTER TABLE agent_memories
ADD COLUMN dominio VARCHAR(50) NULL;

-- Status de validacao para escopo empresa/dominio
ALTER TABLE agent_memories
ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'ativo';

-- Quem originou (audit trail para memorias empresa)
ALTER TABLE agent_memories
ADD COLUMN created_by INTEGER NULL REFERENCES usuarios(id);

-- Ultima confirmacao independente
ALTER TABLE agent_memories
ADD COLUMN last_confirmed_at TIMESTAMP NULL;

-- Indices
CREATE INDEX idx_am_escopo ON agent_memories (escopo) WHERE escopo != 'pessoal';
CREATE INDEX idx_am_dominio ON agent_memories (dominio) WHERE dominio IS NOT NULL;
CREATE INDEX idx_am_status ON agent_memories (status) WHERE status = 'pendente';
```

### 3.2 Usuario Sistema

```sql
INSERT INTO usuarios (id, nome, email, senha_hash, perfil, status)
VALUES (0, 'Sistema', 'sistema@nacomgoya.local', 'NOLOGIN', 'sistema', 'ativo')
ON CONFLICT (id) DO NOTHING;
```

Nota: se o sequence de `usuarios.id` inicia em 1, `id=0` nao conflita com nenhum usuario real.

### 3.3 Compatibilidade

Todas as memorias existentes recebem `escopo='pessoal'`, `status='ativo'`, demais campos NULL. Zero quebra. As MCP tools existentes continuam funcionando — filtram por `user_id` do usuario atual, que so retorna escopo pessoal.

---

## 4. Hierarquia de Resolucao

A logica do PRD v1 esta correta. Refino:

```
1. Override pessoal do usuario?
   → SIM: usar direto (sem confirmar)
   → NAO: continua

2. Termo no dominio do usuario? (dominio inferido do cargo)
   → SIM + status=ativo: confirmar com pergunta direta
   → SIM + status=pendente: sugerir como possibilidade, nao como fato
   → NAO: continua

3. Termo na camada empresa geral?
   → SIM + status=ativo: confirmar com pergunta direta
   → SIM + status=pendente: sugerir como possibilidade
   → NAO: pedir esclarecimento aberto

4. Dominio do usuario = NULL?
   → Pula passo 2, vai direto para 3
```

**UC-03 corrigido (mencao a colega):**
```
"a Gabriella precisa de ajuda com integracao de NF"
→ Buscar usuario Gabriella → cargo=Compras → dominio=compras
→ Usar dominio dela como CONTEXTO para confirmar, NAO para resolver automaticamente
→ "Voce esta se referindo a integracao das NFs do DFe aos pedidos de compras (area da Gabriella)?"
```

A diferenca e sutil mas critica: contexto para confirmar != resolver automaticamente.

---

## 5. Hook Pos-Sessao

### 5.1 Estender o pattern_analyzer existente

O `pattern_analyzer.py` ja faz analise de sessoes via Haiku e salva em `/memories/learned/patterns.xml`. Em vez de criar novo service, estender:

```python
# Em pattern_analyzer.py, apos extrair patterns:
# Nova funcao: extrair_termos_empresa(sessions, user_id)
# - Identifica definicoes de termos ("quando digo X, quero dizer Y")
# - Identifica perfis profissionais ("sou de compras")
# - Classifica escopo
# - Salva com status='pendente' e created_by=user_id
```

### 5.2 Regras de extracao para escopo empresa

| Tipo | Escopo | Status inicial | Exemplo |
|---|---|---|---|
| Definicao de termo operacional | empresa | pendente | "integracao de NF = DFe x PO" |
| Perfil profissional | empresa | ativo (auto-identificacao e confiavel) | "sou da area de compras" |
| Regra de negocio | empresa | pendente | "cliente X sempre pede completo" |
| Preferencia de comunicacao | pessoal | ativo | "prefiro tabela, nao texto" |
| Correcao do agente | pessoal | ativo | "errado, o correto e..." |

**Perfil profissional entra como ativo** porque e auto-identificacao direta do usuario — nao faz sentido exigir segundo uso.

### 5.3 Geracao de embeddings para cada memoria salva

Toda memoria salva (pessoal ou empresa) deve gerar embedding em `agent_memory_embeddings`:

```python
# Apos salvar AgentMemory:
from app.embeddings.services import generate_embedding  # Voyage API

embedding_vector = generate_embedding(memory.content)
AgentMemoryEmbedding(
    memory_id=memory.id,
    user_id=memory.user_id,
    path=memory.path,
    texto_embedado=memory.content,
    embedding=embedding_vector,
    model_used='voyage-3-large',
    content_hash=md5(memory.content),
)
```

Sem embedding, a memoria existe mas o RAG nao a encontra. Este passo e obrigatorio.

### 5.4 Promocao pendente → ativo

Job assincrono (pode rodar no hook pos-sessao):
1. Para cada memoria empresa com `status='pendente'`:
2. Buscar nas sessoes recentes se outro `user_id` diferente de `created_by` usou o mesmo termo no mesmo sentido
3. Se sim → `status='ativo'`, `importance_score=0.7`, `last_confirmed_at=now()`
4. Se 90+ dias em pendente sem confirmacao → mover para `is_cold=True`

---

## 6. Mudancas nos MCP Tools

### 6.1 Carregamento R0 — Fase 1 (inicio de sessao, always-on)

Expandir `memory_mcp_tool.py` para carregar conjunto fixo:
1. Memorias pessoais do usuario (ja existe)
2. Memorias de escopo empresa ativas (`user_id=0, escopo='empresa', status='ativo'`)
3. Memorias de escopo dominio do usuario (`user_id=0, escopo='dominio', dominio=<inferido_do_cargo>`)

Limite: 10-15 memorias no R0. Se houver mais, priorizar por `importance_score DESC, last_confirmed_at DESC`.

### 6.2 Retrieval semantico — Fase 2 (durante conversa, on-demand)

Novo tool interno (nao exposto ao agente — chamado automaticamente pelo pipeline):

```python
def retrieve_relevant_memories(query_text: str, user_id: int, limit: int = 5):
    """
    Busca memorias relevantes via cosine similarity.
    Inclui todos os escopos: pessoal do user + empresa + dominio.
    """
    query_embedding = generate_embedding(query_text)

    results = db.session.query(AgentMemoryEmbedding)\
        .join(AgentMemory, AgentMemory.id == AgentMemoryEmbedding.memory_id)\
        .filter(
            db.or_(
                AgentMemory.user_id == user_id,       # pessoal
                AgentMemory.user_id == 0,              # empresa/dominio
            ),
            AgentMemory.is_cold == False,
            AgentMemory.status.in_(['ativo', 'pendente']),
        )\
        .order_by(AgentMemoryEmbedding.embedding.cosine_distance(query_embedding))\
        .limit(limit)\
        .all()

    return results
```

**Trigger:** Antes de cada chamada ao LLM, se a mensagem do usuario contem termos que nao estao no contexto atual, buscar memorias relevantes e injetar como contexto adicional.

### 6.3 save_memory expandido

Quando o agente chama `save_memory`:
- Se path comeca com `/memories/empresa/` → `user_id=0, escopo='empresa', created_by=<user_atual>`
- Se path comeca com `/memories/dominios/<dom>/` → `user_id=0, escopo='dominio', dominio=<dom>, created_by=<user_atual>`
- Caso contrario → comportamento atual (pessoal)
- **Sempre gerar embedding** apos salvar (secao 5.3)

### 6.4 Novo tool: confirm_empresa_term

Chamado quando segundo usuario confirma um termo pendente:
- Input: `path` do termo
- Logica: se `created_by != usuario_atual` → `status='ativo'`, `last_confirmed_at=now()`
- Se `created_by == usuario_atual` → nao conta como confirmacao independente

---

## 7. Implementacao

### 7.1 Ordem

| Passo | O que | Risco |
|---|---|---|
| 1 | Migration: usuario Sistema + novas colunas | Baixo — additive |
| 2 | Mapear cargo → dominio (funcao pura) | Zero — read-only |
| 3 | Role Awareness no system_prompt (secao 2.9) | Baixo — prompt only, maior impacto |
| 4 | Expandir R0 para carregar empresa/dominio (Fase 1) | Baixo — additive |
| 5 | Expandir save_memory para classificar escopo + gerar embedding | Medio — muda comportamento |
| 6 | Wirar AgentMemoryEmbedding no retrieval (Fase 2 RAG) | Medio — novo pipeline |
| 7 | Resolver de termos no system_prompt | Baixo — prompt only |
| 8 | Estender pattern_analyzer para extracao ampla pos-sessao (Fase 3) | Medio — Haiku |
| 9 | Job de promocao pendente→ativo | Baixo — async |
| 10 | Semear termo "integracao de NF" como prova | Zero |

**Nota:** Passo 3 (Role Awareness) foi promovido para cedo porque e a mudanca de maior impacto com menor risco. Se o agente comecar a identificar conhecimento importante, mesmo sem as secoes 4-9 prontas, o salvamento manual ja melhora.

### 7.2 Termo Semente

```python
# Criar via migration script:
AgentMemory(
    user_id=0,
    path='/memories/empresa/termos/compras/integracao-nf',
    content='<termo expressao="integracao de NF" variacoes="integrar NF, tirar integracao, remover integracao">'
            '<significado>Vinculacao da nota fiscal do DFe ao pedido de compra (PO) no Odoo — Fase 2 do Recebimento</significado>'
            '<confirmacao>Voce esta se referindo a integracao das NFs do DFe aos pedidos de compras?</confirmacao>'
            '</termo>',
    escopo='empresa',
    dominio='compras',
    status='ativo',  # Confirmado por Gabriella + Rafael
    created_by=69,  # Gabriella
    last_confirmed_at=agora_utc_naive(),
    importance_score=0.7,
    category='structural',
    is_permanent=False,
)
```

---

## 8. Criterios de Aceite

**Identificacao (Role Awareness):**
- [ ] Agente identifica proativamente termos operacionais definidos em conversa e salva sem precisar de pedido explicito
- [ ] Agente identifica perfil profissional ("sou de compras") e salva em escopo empresa

**Armazenamento (amplo):**
- [ ] Sessao encerrada sem conclusao → pattern_analyzer extrai e salva com status=pendente
- [ ] Toda memoria salva gera embedding em agent_memory_embeddings
- [ ] Hook pos-sessao salva mais do que o minimo (prefere sobrar a faltar)

**Retrieval (estreito via RAG):**
- [ ] Termo "integracao de NF" mencionado → RAG surfacea memoria empresa relevante
- [ ] Memorias irrelevantes NAO sao injetadas no contexto (maximo 5 por busca)
- [ ] R0 carrega maximo 10-15 memorias fixas (always-on)

**Escopo e validacao:**
- [ ] Termo pendente: injetado como sugestao, nao como fato
- [ ] Segundo usuario independente confirma termo → status muda para ativo
- [ ] "integracao" no dominio compras != "integracao" no dominio ti (paths distintos)
- [ ] Usuario sem cargo preenchido → recebe apenas camada empresa geral + pessoal, sem erro
- [ ] Override pessoal nao afeta resolucao de outros usuarios
- [ ] Termo sem uso em 180 dias → volta a pendente
- [ ] Gabriella mencionada por nome → agente sabe que e de Compras sem perguntar

---

## 9. Fora de Escopo (v1)

- Interface admin para gestao de termos empresa — v2
- Versionamento de definicoes (historico de mudancas de termos) — usa AgentMemoryVersion existente
- Notificacao quando termo e promovido a ativo — v2
- Sincronizacao cross-instancia — ja resolvido via banco
- empresa_id / multi-tenant — YAGNI
- Re-ranking sofisticado (cross-encoder) para resultados RAG — Voyage cosine e suficiente no volume atual

---

## 10. Diferencas do PRD v1

| Aspecto | v1 | v2.1 | Motivo |
|---|---|---|---|
| Storage | XML + banco misturado | Banco unico (AgentMemory) | Fonte unica de verdade |
| user_id empresa | user_id=0 (mencionado como contra) | user_id=0 com usuario Sistema real | Resolve FK + UniqueConstraint |
| Validacao empresa | Nenhuma | status pendente + confirmacao organica | Evita propagacao de erro |
| Dominio do usuario | Perguntar na 1a interacao | Inferir de usuarios.cargo | Zero fricao |
| Pipeline validacao | Nenhum (v1) / Haiku→Sonnet (Desktop) | Uso organico confirma | Sem custo extra |
| Termo como chave | Expressao global unica | (expressao, dominio) via path | "integracao" != "integracao" |
| Invalidacao | Nenhuma | last_confirmed_at + 180d | Termos mortos voltam a pendente |
| UC-03 colega | Resolver automaticamente | Confirmar com contexto | Evita erro com confianca |
| multi-tenant | Nao | Nao (YAGNI) | Nacom nao e SaaS |
| Armazenamento vs injecao | Nao distinguia | Amplo no storage, estreito na injecao (RAG) | Perder conhecimento > ter excesso |
| Role Awareness | Nenhuma | Prompt explicito de aprendizado proativo | Agente nao sabe o que e importante |
| Embeddings | Nao mencionado | AgentMemoryEmbedding obrigatorio p/ toda memoria | RAG sem embedding = inutil |
| Retrieval | Por path apenas | Path (R0) + cosine similarity (on-demand) | Sem RAG, contexto e estatico |