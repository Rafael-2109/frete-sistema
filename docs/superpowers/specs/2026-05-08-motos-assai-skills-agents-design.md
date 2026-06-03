<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-02
-->
# Skills e Agentes para Módulo motos_assai — Design Spec

> **Papel:** Skills e Agentes para Módulo motos_assai — Design Spec.

## Indice

- [1. Objetivo](#1-objetivo)
- [2. Decisões de design (resumo da sessão de brainstorming)](#2-decisões-de-design-resumo-da-sessão-de-brainstorming)
- [3. Arquitetura](#3-arquitetura)
  - [3.1 Fronteiras (NÃO fazer)](#31-fronteiras-não-fazer)
  - [3.2 Autorização](#32-autorização)
  - [3.3 Padrão de output](#33-padrão-de-output)
- [4. Componentes detalhados (6 skills + 1 agente)](#4-componentes-detalhados-6-skills-1-agente)
  - [4.1 `consultando-estoque-assai` (READ)](#41-consultando-estoque-assai-read)
  - [4.2 `rastreando-chassi-assai` (READ)](#42-rastreando-chassi-assai-read)
  - [4.3 `acompanhando-pedido-compra-assai` (READ)](#43-acompanhando-pedido-compra-assai-read)
  - [4.4 `acompanhando-saida-assai` (READ)](#44-acompanhando-saida-assai-read)
  - [4.5 `conferindo-recibo-assai` (READ + WRITE)](#45-conferindo-recibo-assai-read-write)
  - [4.6 `registrando-evento-moto-assai` (WRITE)](#46-registrando-evento-moto-assai-write)
  - [4.7 `gestor-motos-assai` (sub-agent)](#47-gestor-motos-assai-sub-agent)
- [5. Pre-mortem (5 cenários específicos do domínio)](#5-pre-mortem-5-cenários-específicos-do-domínio)
  - [Cenário 1: Chassi com evento posterior já existente](#cenário-1-chassi-com-evento-posterior-já-existente)
  - [Cenário 2: Recibo Motochefe finalizado prematuramente](#cenário-2-recibo-motochefe-finalizado-prematuramente)
  - [Cenário 3: Disponibilizar moto com pendência aberta](#cenário-3-disponibilizar-moto-com-pendência-aberta)
  - [Cenário 4: Race condition em separação](#cenário-4-race-condition-em-separação)
  - [Cenário 5: NF Q.P.A. importada com match DIVERGENTE](#cenário-5-nf-qpa-importada-com-match-divergente)
  - [Self-critique (checklist antes de retornar resposta)](#self-critique-checklist-antes-de-retornar-resposta)
- [6. Error handling (exit codes)](#6-error-handling-exit-codes)
  - [Tratamento por skill (READ)](#tratamento-por-skill-read)
  - [Tratamento por skill (WRITE)](#tratamento-por-skill-write)
- [7. Data flow (fluxos típicos)](#7-data-flow-fluxos-típicos)
  - [7.1 Fluxo A — Consulta READ](#71-fluxo-a-consulta-read)
  - [7.2 Fluxo B — Operação WRITE (dry-run + confirmação)](#72-fluxo-b-operação-write-dry-run-confirmação)
  - [7.3 Fluxo C — Cross-entidade (orquestração)](#73-fluxo-c-cross-entidade-orquestração)
- [8. Testing](#8-testing)
  - [8.1 Camada 1 — Testes unitários por skill](#81-camada-1-testes-unitários-por-skill)
  - [8.2 Camada 2 — Testes de integração](#82-camada-2-testes-de-integração)
  - [8.3 Camada 3 — Avaliação offline do agente](#83-camada-3-avaliação-offline-do-agente)
  - [8.4 Casos de teste por skill (mínimo)](#84-casos-de-teste-por-skill-mínimo)
  - [8.5 Golden dataset (exemplo)](#85-golden-dataset-exemplo)
  - [8.6 Fixtures necessárias](#86-fixtures-necessárias)
  - [8.7 Verificação pré-merge](#87-verificação-pré-merge)
- [9. Atualizações em arquivos existentes (cross-refs obrigatórias)](#9-atualizações-em-arquivos-existentes-cross-refs-obrigatórias)
  - [9.1 `.claude/references/ROUTING_SKILLS.md`](#91-claudereferencesrouting_skillsmd)
  - [9.2 `.claude/references/INDEX.md`](#92-claudereferencesindexmd)
  - [9.3 `CLAUDE.md` (raiz)](#93-claudemd-raiz)
  - [9.4 `.claude/skills/SKILL_IMPROVEMENT_ROADMAP.md`](#94-claudeskillsskill_improvement_roadmapmd)
  - [9.5 `app/motos_assai/CLAUDE.md`](#95-appmotos_assaiclaudemd)
- [10. Critérios de aceite](#10-critérios-de-aceite)
- [11. Riscos e mitigações](#11-riscos-e-mitigações)
- [12. Próximos passos](#12-próximos-passos)
- [Contexto](#contexto)

**Data**: 2026-05-08
**Status**: Spec aprovado em sessão de brainstorming, aguardando implementation plan
**Autor**: Rafael Nascimento (via Claude Code)
**Módulo alvo**: `app/motos_assai/` (B2B Q.P.A. Sendas/Assaí)
**Spec do módulo (referência)**: `docs/superpowers/specs/2026-05-07-motos-assai-design.md`
**CLAUDE.md do módulo**: `app/motos_assai/CLAUDE.md`

---

## 1. Objetivo

Criar conjunto de skills atômicas + 1 sub-agent orquestrador que permitam:

1. **Operadores de chão de fábrica** (montagem, recebimento, separação) interagirem com o pipeline motos_assai via voz/chat (agente web Nacom Goya), executando operações WRITE (registrar montagem, disponibilizar, separar) com salvaguardas.
2. **Gestores B2B** consultarem status agregado do pipeline (estoque, pedidos VOE Q.P.A., compras Motochefe, recibos, separações, NFs) sem abrir múltiplas telas.
3. **Claude Code (dev)** debugar e operar o módulo via CLI usando os mesmos scripts.

**Escopo**: 6 skills atômicas + 1 sub-agent + golden dataset para avaliação offline.

**Fora do escopo**: Cross-domain (Hora, Motochefe, CarVia separadas), modificação de routes/services existentes, novas entidades de domínio.

---

## 2. Decisões de design (resumo da sessão de brainstorming)

| # | Decisão | Razão |
|---|---------|-------|
| D1 | **Híbrido** Claude Code + agente Nacom Goya | Mesmo padrão de skills existentes (gerindo-expedicao, monitorando-entregas) |
| D2 | **READ + WRITE completa** | Operadores de chão usam via voz/chat; UI continua disponível |
| D3 | **Skills atômicas + 1 agente orquestrador** | Padrão `orientador-loja` (Lojas HORA) — 5 skills + 1 agente |
| D4 | **Scripts Python com dry-run** | Mesmo padrão do `operando-ssw`; testável isolado, reutilizável CLI + agente |
| D5 | **Model do agente: `sonnet`** | Decisões determinísticas + self-critique; escalar para `opus` se houver problema em produção |

---

## 3. Arquitetura

```
AGENTE WEB Nacom Goya  /  CLAUDE CODE CLI
        │
        ▼ delega quando "motos_assai", "Q.P.A.", "Sendas", "Assaí"
gestor-motos-assai (sub-agent — model: sonnet)
        │ orquestra cross-entidade
        ▼
6 SKILLS (todas em .claude/skills/<skill>/)
├─ consultando-estoque-assai          (READ)
├─ rastreando-chassi-assai            (READ)
├─ acompanhando-pedido-compra-assai   (READ)
├─ acompanhando-saida-assai           (READ)
├─ conferindo-recibo-assai            (READ + WRITE)
└─ registrando-evento-moto-assai      (WRITE)
        │
        ▼ scripts Python com app_context()
SERVICES (existentes — ZERO modificação)
app/motos_assai/services/*.py
├─ montagem_service
├─ disponibilizar_service
├─ separacao_service
├─ recebimento_service
├─ recibo_service
├─ moto_evento_service
└─ ... (14 services no total)
```

### 3.1 Fronteiras (NÃO fazer)

1. **NÃO replicar lógica de service** — scripts importam e chamam, nunca duplicam.
2. **NÃO bypass de autorização** — todo script verifica `Usuario.pode_acessar_motos_assai()` antes de qualquer operação.
3. **NÃO escapar do escopo do módulo** — cross-domain (Hora, CarVia, Motochefe) é para outros agentes.
4. **NÃO chamar routes HTTP** — sempre services diretamente via `app_context()`.

### 3.2 Autorização

- **READ skills**: aceitam `--user-id <X>` opcional para auditoria, sem scope por loja (motos_assai não tem scope tipo HORA).
- **WRITE skills**: requerem `--user-id <X>` obrigatório + verificam `pode_acessar_motos_assai()` antes de qualquer escrita.

### 3.3 Padrão de output

- **Stdout**: JSON limpo (parseável)
- **Stderr**: logs de execução (info, warnings, errors com contexto)
- **Exit codes** padronizados (ver §6).

---

## 4. Componentes detalhados (6 skills + 1 agente)

### 4.1 `consultando-estoque-assai` (READ)

**Trigger conversacional**: "quantas motos disponíveis?", "estoque por modelo", "quanto de SOL temos?", "pipeline de motos"

**Script**: `.claude/skills/consultando-estoque-assai/scripts/consultando_estoque_assai.py`

**Args**:
- `--resumo` — visão geral (totais por estágio do pipeline)
- `--modelo "SOL"` — filtra por modelo
- `--cd-id <id>` — filtra por CD (default: todos)
- `--por-modelo` — agrupa por modelo
- `--por-estagio` — agrupa por evento (ESTOQUE/MONTADA/PENDENTE/DISPONIVEL/SEPARADA/FATURADA)

**Output JSON**:
```json
{
  "totais": {
    "estoque": 12, "montada": 8, "pendente": 2,
    "disponivel": 15, "separada": 7, "faturada": 230
  },
  "por_modelo": [
    {"modelo": "SOL", "estoque": 5, "montada": 3, "disponivel": 8, "separada": 4, "faturada": 100}
  ],
  "por_cd": [
    {"cd_id": 1, "cd": "JUNDIAÍ", "totais": {...}}
  ],
  "motos_pendentes": [
    {"chassi": "MZX1234", "descricao_pendencia": "...", "criado_em": "..."}
  ],
  "vazio": false
}
```

### 4.2 `rastreando-chassi-assai` (READ)

**Trigger conversacional**: "cadê o chassi MZX...?", "histórico do chassi X", "essa moto Q.P.A. já foi separada?"

**Script**: `.claude/skills/rastreando-chassi-assai/scripts/rastreando_chassi_assai.py --chassi <CHASSI>`

**Output JSON**: histórico completo de eventos (`assai_moto_evento` ordenado), recibo de origem, separação ativa (se houver), NF Q.P.A. (se faturada), validação regex contra modelo.

### 4.3 `acompanhando-pedido-compra-assai` (READ)

**Trigger conversacional**: "como está o pedido VOE 12345?", "compras Motochefe abertas", "MA-2026-0001 já chegou?"

**Script**: `.claude/skills/acompanhando-pedido-compra-assai/scripts/acompanhando_pedido_compra_assai.py`

**Args**:
- `--pedido-id <id>` ou `--numero-voe <num>` — pedido específico
- `--compra-id <id>` ou `--numero-ma "MA-2026-0001"` — compra específica
- `--somente-abertos` — pedidos ABERTO + compras EM_PRODUCAO

**Output JSON**: pedidos VOE Q.P.A. (1 por loja×modelo), compras Motochefe consolidadas, status, totais por loja, vinculação N:N pedido↔compra.

### 4.4 `acompanhando-saida-assai` (READ)

**Trigger conversacional**: "separações em andamento?", "NF Q.P.A. 12345 importada?", "há divergências em NFs?"

**Script**: `.claude/skills/acompanhando-saida-assai/scripts/acompanhando_saida_assai.py`

**Args**:
- `--separacao-id <id>` — separação específica
- `--somente-abertas` — separações em andamento (não faturadas/canceladas)
- `--nfs-recentes` — últimas NF Q.P.A. importadas
- `--divergentes` — apenas NFs com match DIVERGENTE/NAO_RECONCILIADO

**Output JSON**: separações com chassis vinculados, NFs Q.P.A. com resultado match (BATEU/DIVERGENTE), divergências detalhadas, link para Excel Q.P.A. gerado (S3 key).

### 4.5 `conferindo-recibo-assai` (READ + WRITE)

**Trigger conversacional**: "recibos Motochefe pendentes", "como está a conferência do recibo X?", "registra chassi Y como conferido"

**Script**: `.claude/skills/conferindo-recibo-assai/scripts/conferindo_recibo_assai.py`

**Args READ**:
- `--listar-pendentes` — recibos não conferidos
- `--recibo-id <id>` — detalhe do recibo (chassis declarados, conferidos, faltando, divergências)

**Args WRITE** (todas com `--dry-run` default + `--confirmar` para executar + `--user-id` obrigatório):
- `--registrar-chassi --recibo-id <id> --chassi <X> --modelo-id <m> --cor <c>`
- `--finalizar-recibo --recibo-id <id> [--confirmar-faltantes]`

**Output JSON**: status do recibo, divergências detectadas, dry-run preview ou resultado da escrita.

**Diferença vs `registrando-evento-moto-assai`**: esta skill cobre o ciclo de **conferência física** (recibo Motochefe + wizard A→B→C→D), incluindo a INSERÇÃO inicial do chassi em `assai_moto` (insert-once com modelo + cor confirmados). A skill `registrando-evento-moto-assai` (§4.6) cobre apenas TRANSIÇÕES de eventos no pipeline para chassis já existentes. Regra: se o chassi ainda não existe no banco, é `conferindo-recibo-assai`. Se já existe, é `registrando-evento-moto-assai`.

### 4.6 `registrando-evento-moto-assai` (WRITE)

**Trigger conversacional**: "registra MZX como montada", "disponibiliza essa moto", "reverte disponibilização", "cancela separação X"

**Script**: `.claude/skills/registrando-evento-moto-assai/scripts/registrando_evento_moto_assai.py`

**Args** (todos com `--dry-run` default + `--confirmar` + `--user-id` obrigatório):
- `--montar --chassi <X>` (ESTOQUE → MONTADA)
- `--montar-pendente --chassi <X> --descricao <texto>` (ESTOQUE → PENDENTE)
- `--resolver-pendencia --chassi <X>` (PENDENTE → MONTADA via PENDENCIA_RESOLVIDA)
- `--disponibilizar --chassi <X>` (MONTADA → DISPONIVEL)
- `--reverter-disponibilizacao --chassi <X> --motivo <texto>` (DISPONIVEL → REVERTIDA_PARA_MONTADA)
- `--separar --separacao-id <id> --chassi <X>` (DISPONIVEL → SEPARADA)
- `--desfazer-separacao --item-id <id>` (SEPARADA → DISPONIVEL)
- `--cancelar-separacao --separacao-id <id>` (todos chassis SEPARADA → DISPONIVEL via novo evento)

**Output JSON**:
- **dry-run**: preview do que vai acontecer (eventos a emitir, status before/after, validações OK/erro)
- **confirmar**: resultado real da escrita (event_id, novo status, conflitos 409 com retry sugerido)

### 4.7 `gestor-motos-assai` (sub-agent)

**Localização**: `.claude/agents/gestor-motos-assai.md`

**Frontmatter**:
```yaml
---
name: gestor-motos-assai
description: Especialista no módulo Motos Assaí (B2B Q.P.A. Sendas/Assaí). Orquestra skills para consultar pipeline (estoque, pedidos VOE, compras Motochefe, recibos, separações, NFs Q.P.A.) e executar operações WRITE (montagem, disponibilizar, separar, conferir recibo). Use para "estoque motos Assaí", "pedido VOE", "compra Motochefe", "recibo Motochefe", "NF Q.P.A.", "Sendas", "registrar montagem", "disponibilizar moto Q.P.A.". NAO usar para Lojas HORA (usar orientador-loja), pedidos Nacom Goya tradicionais (usar gerindo-expedicao), CarVia ou Motochefe (outros agentes).
tools: Read, Bash, Glob, Grep, mcp__memory__view_memories, mcp__memory__list_memories, mcp__memory__save_memory, mcp__memory__update_memory, mcp__memory__log_system_pitfall, mcp__memory__query_knowledge_graph
model: sonnet
skills:
  - consultando-estoque-assai
  - rastreando-chassi-assai
  - acompanhando-pedido-compra-assai
  - acompanhando-saida-assai
  - conferindo-recibo-assai
  - registrando-evento-moto-assai
---
```

**Seções obrigatórias** (per `.claude/references/AGENT_DESIGN_GUIDE.md`):
1. Identidade/Missão — "Você é o gestor do módulo Motos Assaí da Nacom Goya..."
2. Contexto + Referências — pointer para `app/motos_assai/CLAUDE.md`, modelo de eventos append-only
3. Armadilhas críticas — eventos append-only, recebimento como SOT, UNIQUE parcial chassi, status_atual vs último evento
4. Árvore de decisão — qual skill usar para qual pergunta (similar `orientador-loja`)
5. Formato de resposta — referência `AGENT_TEMPLATES.md#output-format-padrao`
6. Boundary check — redirects para outros agentes (orientador-loja, gerindo-expedicao, especialista-odoo)
7. Protocolo confiabilidade — `/tmp/subagent-findings/gestor-motos-assai-*.md`
8. **PRE-MORTEM** (obrigatório por ter WRITE) — 5 cenários listados em §5
9. **SELF-CRITIQUE** (obrigatório por decisões de alto impacto) — checklist em §5

---

## 5. Pre-mortem (5 cenários específicos do domínio)

### Cenário 1: Chassi com evento posterior já existente
- **Risco**: registrar MONTADA em chassi que já está SEPARADA (regrede o pipeline)
- **Sinal de alerta**: status_atual no dry-run não é o esperado para o evento
- **Contramedida**: validador `montagem_service` rejeita se `status_atual != ESTOQUE` — gestor verifica via dry-run antes de pedir confirmação

### Cenário 2: Recibo Motochefe finalizado prematuramente
- **Risco**: finalizar recibo com chassis faltantes sem confirmar `MOTO_FALTANDO`
- **Contramedida**: skill `conferindo-recibo-assai --finalizar-recibo` rejeita se há faltantes sem flag `--confirmar-faltantes`

### Cenário 3: Disponibilizar moto com pendência aberta
- **Risco**: pular DISPONIVEL com status `PENDENTE` ativo
- **Contramedida**: `DisponibilizarError` já bloqueia; pre-mortem força gestor a citar status atual antes de chamar

### Cenário 4: Race condition em separação
- **Risco**: 2 operadores escaneiam mesmo chassi para 2 separações diferentes simultaneamente
- **Contramedida**: UNIQUE parcial em `(separacao_id, chassi)` para `status != CANCELADA` → IntegrityError → exit code 5. Gestor NÃO retenta automaticamente.

### Cenário 5: NF Q.P.A. importada com match DIVERGENTE
- **Risco**: confirmar separação como FATURADA mesmo com match DIVERGENTE (perda de auditoria)
- **Contramedida**: `acompanhando-saida-assai` reporta divergência claramente; gestor NÃO permite write FATURADA sem usuário aceitar divergência explicitamente

### Self-critique (checklist antes de retornar resposta)

- [ ] Citei o status_atual do chassi com fonte (`evento_id` específico)?
- [ ] Considerei se o usuário tem permissão para esta operação (`pode_acessar_motos_assai`)?
- [ ] Reportei resultados negativos explicitamente ("nenhum recibo encontrado" em vez de omitir)?
- [ ] Em WRITE: o dry-run foi mostrado ANTES da confirmação?
- [ ] Em WRITE: marquei `[ASSUNCAO]` se o usuário disse "essa moto" sem chassi explícito?
- [ ] Apliquei a hierarquia constitucional (L1 Segurança > L2 Ética > L3 Regras > L4 Utilidade)?

---

## 6. Error handling (exit codes)

| Exit code | Significado | Ação esperada do agente |
|-----------|-------------|-------------------------|
| 0 | Sucesso (READ ok ou WRITE confirmada) | Continuar fluxo normal |
| 1 | Validação falhou (chassi não existe, modelo errado) | Reportar erro ao usuário, sugerir correção |
| 2 | Erro de infra (DB, S3) | Reportar e parar — pedir intervenção |
| 3 | Não autorizado (`pode_acessar_motos_assai = False`) | Recusar operação, redirecionar para gestor |
| 4 | Confirmação faltando (WRITE sem `--confirmar`) | Mostrar dry-run e pedir aprovação |
| 5 | Conflito de concorrência (409 IntegrityError) | Reportar conflito, sugerir retry manual |

### Tratamento por skill (READ)

- **Sem dados**: retornar JSON com listas vazias + flag `"vazio": true` + mensagem em stderr
- **Filtro inválido**: validar args ANTES de query, exit 1 com mensagem clara
- **Timeout DB**: exit 2 com retry sugerido em stderr

### Tratamento por skill (WRITE)

- **Validação prévia obrigatória**: chassi existe → status_atual compatível → user pode_acessar → emitir evento
- **Atomicidade**: `with db.session.begin()` envolvendo TODA a sequência de validação + emit_evento
- **Auditoria**: TODA operação WRITE registra `usuario_id` e `criado_em` no evento
- **Concorrência**: `with_for_update(of=AssaiMoto)` antes de emitir evento (lock pessimista)

---

## 7. Data flow (fluxos típicos)

### 7.1 Fluxo A — Consulta READ

```
Usuário: "quantas motos disponíveis para Sendas hoje?"
   │
   ▼
[Agente Nacom Goya] reconhece "motos" + "Sendas" → delega gestor-motos-assai
   │
   ▼
[gestor-motos-assai] decide: consultando-estoque-assai
   │
   ▼
Bash: python scripts/consultando_estoque_assai.py --resumo --por-modelo
   │
   ▼ (script importa app + app_context)
   query: SELECT chassi, último_evento.tipo FROM ... WHERE tipo='DISPONIVEL'
   │
   ▼
JSON em stdout → gestor sintetiza resposta humanizada
   │
   ▼
"Você tem 15 motos DISPONIVEL: 8 SOL, 5 X11_MINI, 2 DOT.
 Aguardando montagem: 12 motos em ESTOQUE."
```

### 7.2 Fluxo B — Operação WRITE (dry-run + confirmação)

```
Operador: "registra o chassi MZX1234 como montada"
   │
   ▼
[gestor-motos-assai]
   • PRE-MORTEM: o chassi está em ESTOQUE? Outro evento posterior?
   • Decide: registrando-evento-moto-assai
   │
   ▼
Bash: python scripts/registrando_evento_moto_assai.py \
        --montar --chassi MZX1234 --user-id 5 --dry-run
   │
   ▼
Output JSON dry-run:
{
  "ok": true, "dry_run": true,
  "preview": {
    "chassi": "MZX1234",
    "status_atual": "ESTOQUE",
    "evento_a_emitir": "MONTADA",
    "validacoes": ["chassi_existe: ok", "status_compativel: ok"]
  }
}
   │
   ▼
gestor mostra ao usuário: "Vou registrar MZX1234 como MONTADA. Confirma?"
   │
   ▼ (usuário aprova)
Bash: python scripts/... --montar --chassi MZX1234 --user-id 5 --confirmar
   │
   ▼ (script chama services com app_context + user)
   from app.motos_assai.services.montagem_service import processar_montagem
   processar_montagem(chassi='MZX1234', usuario=u, ok=True)
   │
   ▼
Output JSON real:
{"ok": true, "dry_run": false, "evento_id": 42, "novo_status": "MONTADA"}
   │
   ▼
gestor confirma: "✓ Chassi MZX1234 registrado como MONTADA (evento #42)."
```

### 7.3 Fluxo C — Cross-entidade (orquestração)

```
Usuário: "como está a operação Motos Assaí hoje?"
   │
   ▼ gestor decide F1 (resumo geral):
   1. consultando-estoque-assai --resumo
   2. acompanhando-pedido-compra-assai --somente-abertos
   3. conferindo-recibo-assai --listar-pendentes
   4. acompanhando-saida-assai --somente-abertas
   │
   ▼ sintetiza:
   "• Estoque: 15 disponíveis, 12 em ESTOQUE, 2 PENDENTE (peças)
    • 1 compra MA-2026-0003 EM_PRODUCAO (90 motos)
    • 2 recibos aguardando conferência (RM-001, RM-002)
    • 3 separações em andamento (1 pronta para faturar)"
```

---

## 8. Testing

### 8.1 Camada 1 — Testes unitários por skill

**Localização**: `tests/skills/test_<skill>.py`

- Cada script Python testado com fixtures do `tests/motos_assai/fixtures/`
- READ skills: validar JSON output contra schemas esperados
- WRITE skills: testar dry-run vs `--confirmar`, validações falhas, exit codes
- Mockar `db.session` quando necessário

### 8.2 Camada 2 — Testes de integração

**Localização**: `tests/skills/integration/test_motos_assai_skills.py`

- Subir banco SQLite em memória + criar registros completos
- Executar skill como subprocess (simula uso real)
- Validar JSON parsing + exit codes

### 8.3 Camada 3 — Avaliação offline do agente

**Localização**: `.claude/evals/subagents/gestor-motos-assai/`

- Golden dataset com ~15-20 perguntas representativas
- Cobertura: cada skill 2-3x + fluxos cross-entidade + edge cases
- Estrutura padrão `.claude/evals/subagents/README.md`

### 8.4 Casos de teste por skill (mínimo)

| Skill | Casos de teste obrigatórios |
|-------|----------------------------|
| `consultando-estoque-assai` | resumo geral, filtro por modelo, filtro por CD, vazio (sem motos), output JSON válido |
| `rastreando-chassi-assai` | chassi com histórico completo, chassi faltando (`MOTO_FALTANDO`), chassi não existe, chassi recém-criado |
| `acompanhando-pedido-compra-assai` | pedido aberto, compra em produção, pedido fechado, busca por número VOE/MA, vazio |
| `acompanhando-saida-assai` | separação em andamento, NF BATEU, NF DIVERGENTE, separação cancelada, vazio |
| `conferindo-recibo-assai` | listar pendentes, detalhe recibo, registrar chassi (dry-run + confirmar), conflito 409, finalizar com faltantes |
| `registrando-evento-moto-assai` | montar OK, montar com pendência, disponibilizar, reverter, separar, cancelar separação, status incompatível, race 409 |

### 8.5 Golden dataset (exemplo)

```yaml
# .claude/evals/subagents/gestor-motos-assai/golden.yaml
- prompt: "quantas motos disponíveis hoje?"
  expected_skills: [consultando-estoque-assai]
  expected_keywords: [DISPONIVEL, modelo]

- prompt: "registra MZX1234 como montada"
  expected_skills: [registrando-evento-moto-assai]
  expected_flow: [dry_run, user_confirm, write]
  expected_exit_codes: [0]

- prompt: "como está a operação Motos Assaí?"
  expected_skills:
    - consultando-estoque-assai
    - acompanhando-pedido-compra-assai
    - conferindo-recibo-assai
    - acompanhando-saida-assai
  expected_keywords: [estoque, compra, recibo, separação]

- prompt: "essa NF Q.P.A. 12345 bateu?"
  expected_skills: [acompanhando-saida-assai]
  expected_keywords: [match, BATEU, DIVERGENTE]
```

### 8.6 Fixtures necessárias

- `tests/motos_assai/fixtures/recibo_motochefe_exemplo.pdf` (já existe, gitignore)
- `tests/motos_assai/fixtures/nf_qpa_exemplo.pdf` (criar se não existir — sem dados PII)
- Seeds SQL idempotentes: 1 CD, 3 lojas Sendas, 3 modelos (SOL, X11_MINI, DOT), 5 motos em diferentes estágios

### 8.7 Verificação pré-merge

```bash
pytest tests/skills/ -v
pytest tests/motos_assai/ -v
python .claude/evals/subagents/gestor-motos-assai/run_eval.py
```

---

## 9. Atualizações em arquivos existentes (cross-refs obrigatórias)

Per `feedback_skill_padrao_completo` (memória do projeto, 2026-04-14): ao mexer em skill, atualizar TODOS os cross-refs.

### 9.1 `.claude/references/ROUTING_SKILLS.md`

Adicionar 6 linhas na tabela "Passo 1: Identificar o CONTEXTO":

```markdown
| MOTOS ASSAÍ — ESTOQUE/PIPELINE | "quantas motos Q.P.A.?", "estoque Sendas", "pipeline Assaí" | -> `consultando-estoque-assai` |
| MOTOS ASSAÍ — RASTREAR CHASSI | "cadê chassi MZX...?", "histórico chassi Q.P.A." | -> `rastreando-chassi-assai` |
| MOTOS ASSAÍ — PEDIDOS/COMPRAS | "pedido VOE", "compra Motochefe MA-", "VOE Q.P.A." | -> `acompanhando-pedido-compra-assai` |
| MOTOS ASSAÍ — SAÍDA/NFs | "separações Assaí", "NF Q.P.A.", "match BATEU/DIVERGENTE" | -> `acompanhando-saida-assai` |
| MOTOS ASSAÍ — RECIBO MOTOCHEFE | "recibos pendentes", "conferir recibo RM-", "wizard recebimento" | -> `conferindo-recibo-assai` |
| MOTOS ASSAÍ — EVENTOS WRITE | "registra montagem", "disponibiliza", "reverte", "separar chassi" | -> `registrando-evento-moto-assai` |
| MOTOS ASSAÍ — CROSS-ENTIDADE | "como está operação Q.P.A.?", "resumo Motos Assaí", orquestrar | -> Subagente `gestor-motos-assai` |
```

Adicionar desambiguação:

```markdown
| consultando-estoque-assai vs gerindo-expedicao | **Motos Q.P.A.** (B2B Sendas) -> consultando-estoque-assai. **Pedidos/separação Nacom Goya** -> gerindo-expedicao |
| rastreando-chassi-assai vs rastreando-chassi (Hora) | **Q.P.A.** (assai_moto) -> rastreando-chassi-assai. **Lojas HORA** (hora_moto) -> rastreando-chassi |
```

### 9.2 `.claude/references/INDEX.md`

Adicionar linha em "Skills Inventário Completo":

```markdown
### Skills motos_assai (6)
`consultando-estoque-assai`, `rastreando-chassi-assai`, `acompanhando-pedido-compra-assai`,
`acompanhando-saida-assai`, `conferindo-recibo-assai`, `registrando-evento-moto-assai`
```

### 9.3 `CLAUDE.md` (raiz)

Adicionar entrada em "Subagentes":

```markdown
| `gestor-motos-assai` | Pipeline B2B Q.P.A. Sendas/Assaí (estoque, recibo, separação, NF) |
```

### 9.4 `.claude/skills/SKILL_IMPROVEMENT_ROADMAP.md`

Registrar criação das 6 skills com data 2026-05-08.

### 9.5 `app/motos_assai/CLAUDE.md`

Adicionar seção "Skills + Agente disponíveis":

```markdown
## Skills + Agente disponíveis

Para consultas e operações via Claude Code ou agente web Nacom Goya:

| Skill | Tipo | Uso |
|-------|------|-----|
| `consultando-estoque-assai` | READ | Pipeline (ESTOQUE/MONTADA/DISPONIVEL/SEPARADA/FATURADA) |
| `rastreando-chassi-assai` | READ | Histórico completo de um chassi |
| `acompanhando-pedido-compra-assai` | READ | Pedidos VOE Q.P.A. + compras Motochefe |
| `acompanhando-saida-assai` | READ | Separações + NFs Q.P.A. (match BATEU/DIVERGENTE) |
| `conferindo-recibo-assai` | READ + WRITE | Recibos Motochefe + wizard A→B→C→D |
| `registrando-evento-moto-assai` | WRITE | Montagem, disponibilizar, separar, reverter, cancelar |

Agente orquestrador: `gestor-motos-assai` (sub-agent — `model: sonnet`).

Spec: `docs/superpowers/specs/2026-05-08-motos-assai-skills-agents-design.md`
```

---

## 10. Critérios de aceite

A implementação está completa quando:

1. **6 skills criadas** com SKILL.md + scripts/ + testes unitários (Camada 1) passando.
2. **1 agente criado** em `.claude/agents/gestor-motos-assai.md` com seções obrigatórias.
3. **Cross-refs atualizadas**: ROUTING_SKILLS.md, INDEX.md, CLAUDE.md raiz, SKILL_IMPROVEMENT_ROADMAP.md, app/motos_assai/CLAUDE.md.
4. **Testes integração** (Camada 2) passando para todas as skills WRITE.
5. **Golden dataset** (Camada 3) com 15-20 entradas + script de eval rodando.
6. **`app/agente/services/tool_skill_mapper.py`** atualizado para incluir as 6 skills no mapeamento de tools do agente web.
7. **Verificação manual em CLI**: `python .claude/skills/consultando-estoque-assai/scripts/consultando_estoque_assai.py --resumo` retorna JSON válido.
8. **Verificação manual em agente web**: pergunta "quantas motos Q.P.A. disponíveis?" delega corretamente para `gestor-motos-assai`.

---

## 11. Riscos e mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| WRITE incorreto rompe pipeline (chassi em estado errado) | Média | Alto | Dry-run obrigatório + pre-mortem + self-critique + atomicidade transação |
| Race condition em separação (2 operadores) | Baixa | Médio | UNIQUE parcial existente + with_for_update + exit code 5 |
| Confusão de routing (gestor-motos-assai vs orientador-loja) | Média | Baixo | Description claro + boundary check + ROUTING_SKILLS.md desambiguação |
| Skill quebra após mudança em service | Baixa | Médio | Testes unitários + integração rodam em CI |
| Operador escolhe `--confirmar` sem entender preview | Média | Alto | Mensagem clara em dry-run + auditoria via `usuario_id` |
| Spec do módulo motos_assai mudar (renomear campos) | Baixa | Alto | Schemas auto-gerados em `.claude/skills/consultando-sql/schemas/tables/` validam contra DB real |

---

## 12. Próximos passos

Após aprovação deste spec:

1. Invocar `superpowers:writing-plans` para criar implementation plan detalhado
2. Plan dividirá em fases:
   - **Fase 1**: 4 skills READ (consultando-estoque-assai, rastreando-chassi-assai, acompanhando-pedido-compra-assai, acompanhando-saida-assai)
   - **Fase 2**: agente gestor-motos-assai (apenas READ)
   - **Fase 3**: 2 skills MIXED/WRITE (conferindo-recibo-assai, registrando-evento-moto-assai)
   - **Fase 4**: integrar WRITE no agente + golden dataset + cross-refs
3. Cada fase tem critérios de aceite próprios + verificação intermediária

## Contexto

_A completar (PAD-A Onda 4)._
