---
date: 2026-06-24
run: cron-D8 (#48)
suggestions_evaluated: 9
implemented: 6
rejected: 1
proposed: 2
---

# Improvement Dialogue — 2026-06-24 (cron D8 #48)

> Execucao **cron D8 normal** (distinta da reconciliacao dev 4-maos do mesmo dia —
> `dialogue-2026-06-24.md`, #47). Pega o backlog que o #47 deixou para "o D8 normal"
> (IMP-23-006, IMP-23-007) + as sugestoes CarVia (Barbara id 87) e a critica
> IMP-23-011 (Rayssa id 78). 9 avaliadas, 6 auto-implementadas, 1 rejeitada, 2
> propostas. Persistencia v2 ids 286-294 (HTTP 200). Branch `cron/manutencao`, sem push.

## Sugestoes Avaliadas

### [RESPONDED / IMPLEMENTADA] IMP-2026-06-23-011: vincular_nf_manualmente valida pedido_id mas nao o propaga
- **Categoria**: skill_bug
- **Severidade**: critical
- **Usuario de origem**: Rayssa Alves (id 78)
- **Decisao**: respondido — **BUG REAL** (codigo do fluxo oficial confirmado errado)
- **Implementado**: sim (auto)
- **Arquivos afetados**: `app/motos_assai/services/separacao_service.py`, `app/motos_assai/services/parsers/nf_qpa_adapter.py`
- **Notas**: fix prescrito (a)+(b). `ajustar_separacao_pela_nf` ganhou `pedido_id=None`; quando
  fornecido vira `pedido_inferido_id` ANTES de toda inferencia (curto-circuita o branch ambiguo
  S1=b que exigia exatamente 1 pedido ABERTO/PARCIAL na loja — 98/100 NFs de backfill caiam ali).
  `vincular_nf_manualmente` passa o `pedido_id` ja validado. Outros 2 callers (PDF, dados
  estruturados) inalterados por `pedido_id=None`. **22 testes passaram** (vincular_nf_manual +
  nf_qpa_match + match_v2_cenarios).

### [RESPONDED / IMPLEMENTADA] IMP-2026-06-24-002: gerindo-carvia read-only, sem UPDATE em carvia_fretes
- **Categoria**: skill_bug
- **Severidade**: critical
- **Usuario de origem**: Barbara Ferreira Amaral (id 87)
- **Decisao**: respondido — gap real confirmado
- **Implementado**: sim (auto)
- **Arquivos afetados**: `.claude/skills/gerindo-carvia/scripts/atualizando_frete_carvia.py` (novo), `.claude/skills/gerindo-carvia/SKILL.md`
- **Notas**: criado o 1o script de ESCRITA da skill. Atualiza valor_cotado/considerado/pago/venda/
  tabela_nome_tabela/tabela_valor_kg de UM frete. dry-run DEFAULT (rollback + antes/depois), so
  efetiva com `--confirmar`. Espelha valor_considerado=valor_cotado quando sem CTe; recalcula
  `requer_aprovacao` via `requer_aprovacao_por_valor()` (nao auto-aprova). Validado contra banco
  local (aplica/espelha/recalcula/rollback). Resolve junto IMP-24-001 e IMP-24-003.

### [RESPONDED / IMPLEMENTADA] IMP-2026-06-24-001: sem script de UPDATE para carvia_fretes
- **Categoria**: skill_suggestion
- **Severidade**: warning
- **Usuario de origem**: Barbara Ferreira Amaral (id 87)
- **Decisao**: respondido (mesma implementacao da IMP-24-002)
- **Implementado**: sim (auto)
- **Arquivos afetados**: idem IMP-24-002
- **Notas**: o script atende exatamente o pedido (--frete-id + valores, dry-run obrigatorio, JSON
  antes/depois). Cobre o caso tabela "0" / valor_cotado=0.

### [RESPONDED / IMPLEMENTADA] IMP-2026-06-24-003: skill para atualizar frete CarVia (peso cubado, tabela)
- **Categoria**: skill_suggestion
- **Severidade**: warning
- **Usuario de origem**: Barbara Ferreira Amaral (id 87)
- **Decisao**: respondido (mesma implementacao)
- **Implementado**: sim (auto)
- **Arquivos afetados**: idem IMP-24-002
- **Notas**: a ESCRITA agora existe. O CALCULO (peso cubado × tabela) foi deliberadamente mantido
  FORA do script (constituicao das skills: atomo nao embute outro fluxo) — ja existe
  `cotando_subcontrato_carvia.py` / `CotacaoService.cotar_subcontrato`. Fluxo: cotar → persistir.

### [RESPONDED / IMPLEMENTADA] IMP-2026-06-24-004: tela lancar-cte exibe V.Cotado sem edicao na UI
- **Categoria**: gotcha_report
- **Severidade**: warning
- **Usuario de origem**: Barbara Ferreira Amaral (id 87)
- **Decisao**: respondido — gotcha confirmado no codigo
- **Implementado**: sim (doc)
- **Arquivos afetados**: `.claude/skills/gerindo-carvia/SKILL.md`
- **Notas**: verificado — `lancar_cte_carvia` (GET, so busca+selecao), `editar.html` com valor_cotado
  readonly, form sem campo valor_cotado. Documentado na regra #9 do SKILL.md: o agente antecipa a
  limitacao e direciona ao script `atualizando_frete_carvia.py` em vez da tela.

### [RESPONDED / IMPLEMENTADA] IMP-2026-06-23-007: skill para adicionar item a embarque existente
- **Categoria**: skill_suggestion
- **Severidade**: warning
- **Usuario de origem**: Rafael De Carvalho Nascimento (id 1)
- **Decisao**: respondido (modo Nacom)
- **Implementado**: sim (auto)
- **Arquivos afetados**: `.claude/skills/gerindo-expedicao/scripts/adicionando_item_embarque.py` (novo), `.claude/skills/gerindo-expedicao/SKILL.md`
- **Notas**: criado `adicionando_item_embarque.py` (WRITE, dry-run default). Anexa 1 lote Nacom a
  embarque ATIVO reusando helpers ja testados de `gerar_embarque.py`. **ANTI-INFLACAO**: apos
  add+commit chama `sincronizar_totais_embarque` que recalcula por SOMA dos itens ativos — nunca
  incremento (causa-raiz do bug 1089,35 vs 863,35 kg). Idempotente. **Escopo = Nacom**: itens
  CarVia (CARVIA-*) sao recusados — tem maquina propria `reconciliar_embarque_carvia` (CarVia R1
  modulo isolado), follow-up = expor equivalente na skill gerindo-carvia. Validado contra banco
  local (dry-run caminho-feliz, idempotencia, conflito).

### [RESPONDED / PROPOSTA] IMP-2026-06-23-012: completar FATURADA de chassis SEPARADA em sep ja FATURADA
- **Categoria**: skill_suggestion
- **Severidade**: warning
- **Usuario de origem**: Rayssa Alves (id 78)
- **Decisao**: respondido — **proposta** (nao auto-implementado)
- **Implementado**: nao
- **Arquivos afetados**: nenhum (plano em implementation_notes)
- **Notas**: **causa-raiz confirmada no codigo** — `_calcular_match` (nf_qpa_adapter.py ~734) seta
  `sep.status=FATURADA` para a sep INTEIRA mas emite `EVENTO_FATURADA` so por ITEM-DA-NF com match
  (~738-744); sep parcialmente coberta deixa chassis em SEPARADA. NAO auto-implementado: a correcao
  toca a SEMANTICA do faturamento (decisao de modelo, ja registrada como PENDENTE no
  `app/motos_assai/CLAUDE.md` — split-brain 1727/1729/1737/2037 + blocker IMP-23-005). Plano: FIX A
  (emitir FATURADA p/ todos os chassis da sep ao faturar) + FIX B (funcao idempotente
  `completar_faturada_parcial` na skill corrigindo-dados-assai). Casar com a decisao do IMP-23-005.

### [RESPONDED / PROPOSTA] IMP-2026-06-22-003: agente executou UPDATE sem autorizacao explicita
- **Categoria**: skill_bug
- **Severidade**: info
- **Usuario de origem**: Jessica Tereza da Silva (id 4)
- **Decisao**: respondido — **proposta** (principio ja coberto; nao auto-editei o prompt)
- **Implementado**: nao
- **Arquivos afetados**: nenhum (recomendacao para review trimestral)
- **Notas**: o principio JA existe — system_prompt `<cannot_do>` ("modificar banco diretamente sem
  confirmacao") + R3 ("Aguarde resposta explicita"). Gap fino: R3 nominalmente fala so de "criar
  separacoes" e nao tem clausula anti-ambiguidade (confirmacao que responde a OUTRA pergunta).
  NAO auto-editei por causa da governanca rigida do prompt (PAD-CTX + pre-commit `--check-delta`
  anti-crescimento + review trimestral jul/2026) e da separacao de competencias. Recomendacao
  registrada para o review de jul/2026 (generalizar R3 + clausula anti-ambiguidade, ~1-2 linhas
  com poda compensatoria).

### [REJECTED] IMP-2026-06-23-006: confirmar diario inter-company antes do lote
- **Categoria**: skill_bug
- **Severidade**: info
- **Usuario de origem**: origem desconhecida (sessao sem user_id resolvido)
- **Decisao**: **rejeitado**
- **Implementado**: nao
- **Arquivos afetados**: nenhum
- **Notas**: pausar para confirmar o diario inter-company numa baixa financeira em LOTE e salvaguarda
  CORRETA (R3, operacao irreversivel), nao friccao a remover — um default fixo gravaria no diario
  errado (varia por operacao/empresa). Skill mal-atribuida: aponta `lendo-arquivos` (so LE arquivo,
  nao executa baixa); o fluxo e de `baixando-credores-lote-odoo` / `executando-odoo-financeiro`.
  Descricao vazia + origem desconhecida = sinal fraco. Caminho correto (se desejavel): MEMORIA DE
  PERFIL do usuario, que o R3 ja autoriza.

## Resumo
- Total avaliadas: 9
- Implementadas automaticamente: 6 (IMP-23-011, IMP-24-002, IMP-24-001, IMP-24-003, IMP-24-004, IMP-23-007)
- Rejeitadas: 1 (IMP-23-006)
- Propostas para revisao humana: 2 (IMP-23-012, IMP-22-003)
- Clusters: **CarVia escrita** (IMP-24-001/-002/-003 = 1 script `atualizando_frete_carvia.py`) + **CarVia gotcha** (IMP-24-004 doc) resolvidos numa unidade de trabalho.
- Persistencia: v2 ids 286-294, todos HTTP 200.
- Testes: 22 passed (motos_assai vincular/match); novos scripts validados contra banco local em dry-run.
