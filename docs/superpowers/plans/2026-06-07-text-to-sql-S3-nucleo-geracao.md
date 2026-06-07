<!-- doc:meta
tipo: how-to
camada: L3
sot_de: plano S3 — nucleo de geracao de SQL (Opus autor unico + correcao + permissao)
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-07
-->

# S3 — Nucleo de Geracao de SQL

> **Papel:** plano executavel da sessao dedicada ao subsistema S3 (coracao da
> arquitetura). Faz o Opus ser o autor unico do SQL, da uma malha de correcao
> deterministica (e, opcionalmente, Haiku-testado) quando ele erra, e separa PERMISSAO
> (DML/tabela proibidos) de GERACAO (a forma certa de fazer SQL, igual para todos).
> Faz parte do pacote `2026-06-07-text-to-sql-arquitetura-MASTER` (ler o MASTER antes).
> Depende de S1 (o Opus precisa do mapa para escrever certo).

## Indice

- [Contexto herdado](#contexto-herdado)
- [Objetivo e criterio de sucesso](#objetivo-e-criterio-de-sucesso)
- [Escopo](#escopo)
- [Arquivos-alvo](#arquivos-alvo)
- [Abordagens](#abordagens)
- [Design proposto](#design-proposto)
- [Edge cases](#edge-cases)
- [Pre-mortem](#pre-mortem)
- [Decisoes em aberto (perguntar na sessao)](#decisoes-em-aberto-perguntar-na-sessao)
- [Testes e verificacao](#testes-e-verificacao)
- [Conformidade](#conformidade)

## Contexto herdado

Diagnostico-raiz (MASTER): o pipeline tem DUAS mentes gerando SQL — o Opus (que chama a
tool) e o Generator Haiku — e o Haiku, inferior, e tratado como AUTOR. O proprio codigo
admite a premissa invertida (`text_to_sql.py:254`: "o chamador real e o Agente (Opus),
que ja sabe SQL"). Furos herdados:

- **F1** Generator truncado a `max_tokens=500` (`text_to_sql.py:862,101,117,137`) → CTE/
  multi-JOIN longo e cortado.
- **F2** `skip_haiku` (`text_to_sql.py:1022`) pula o Evaluator em SELECT puro nao-admin
  quando o validador deterministico aprova — mas o deterministico so pega campo
  INEXISTENTE (`text_to_sql.py:997-1012`), nao campo existente-mas-errado → SQL
  semanticamente errado executa sem revisao.
- **F3** regra 4 do Generator manda "use nomes logicos baseados na descricao"
  (`text_to_sql.py:842`) com exemplos genericos-ancora, ignorando os campos reais.
- **F4** template >=0.92 (`text_to_sql.py:2033`) nao e revalidado contra schema →
  template stale executa SQL com campo velho.
- **F5** `looks_like_raw_sql` (`text_to_sql.py:326`) e heuristica fragil → SQL legitimo
  classificado como NL cai no Generator (downgrade).

Caminhos por perfil hoje (MASTER): admin com SQL-first `on` + SQL bruto → literal (pula
Generator); admin com NL → Generator ainda roda; comum → sempre Generator, e SELECT puro
aprovado → `skip_haiku`. A distincao admin/comum HOJE inclui a forma de gerar SQL — o
usuario quer que a distincao seja SO de permissao.

Decisao do usuario (validada): admin difere apenas em "UPDATE proibido, tabelas e campos
proibidos", NAO na "forma certa de gerar SQL". E: se o Opus nao gerou SQL certo, quer uma
correcao DETERMINISTICA, ou Haiku COM TESTE — nao Haiku as cegas.

Pre-requisito: S1 entrega o progressive disclosure que torna o Opus capaz de achar a
tabela certa. Sem S1, mover o peso para o Opus expoe o problema de descoberta.

## Objetivo e criterio de sucesso

**Objetivo:** o Opus e o autor unico do SQL; o pipeline vira executor seguro + corretor;
admin e comum usam a MESMA geracao, diferindo so em permissao.

**Criterio de sucesso (verificavel):**
1. Caminho primario: o agente envia SQL e ele executa literal (sem reescrita por LLM
   inferior), com guard-rails determinísticos.
2. Erro de campo → o pipeline devolve os campos REAIS + hints e o agente corrige em 1
   nova chamada (loop deterministico), sem Generator Haiku no meio.
3. admin e comum produzem SQL pela mesma via; a unica diferenca e a matriz de permissao
   (DML, tabelas, campos).
4. Se houver corretor automatico Haiku, ele so aceita a correcao apos um TESTE
   (revalidacao deterministica e/ou `EXPLAIN`/dry-run) — nunca as cegas.

## Escopo

**Inclui:**
- Contrato da tool: `sql=` (literal) vs `pergunta=` (fallback NL) (mata F5).
- Caminho primario literal + loop de auto-correcao deterministico (`_build_schema_feedback`
  ja existe em `text_to_sql.py:1862`).
- Remocao do Generator condicionada a auditoria (postura padrao = remover; ver decisoes).
- Fixes F1 (truncamento), F2 (skip_haiku), F4 (template stale).
- Separar permissao de geracao: a MESMA geracao para todos; admin difere so em DML +
  tabelas bloqueadas (SEM bloqueio de campo — fora de escopo).

**Exclui:**
- Idempotencia do gerador (→ S0).
- Descoberta de tabela (→ S1; S3 consome).
- Curadoria de descricao (→ S2; S3 consome).

## Arquivos-alvo

| Arquivo | Mudanca |
|---|---|
| `app/agente/tools/text_to_sql_tool.py` | contrato (`sql=` vs `pergunta=`), matriz de permissao, descricao da tool |
| `.claude/skills/consultando-sql/scripts/text_to_sql.py` | `run()` (caminho literal primario), skip_haiku, max_tokens, template revalidado, Generator (regra 4 / fallback) |
| `app/agente/config/feature_flags.py` | `resolve_sql_first_mode` → politica final (deixar de ser canary) |
| `app/agente/prompts/system_prompt.md` + `sdk/hooks.py` (`sql_admin_context`, `:1335`) | orientar Opus a ser autor; separar permissao de geracao |
| `app/pessoal` (`USUARIOS_SQL_ADMIN`, `TABELAS_PESSOAL`) | matriz de permissao; campos proibidos |

## Abordagens

**A. Opus autor unico + Generator como fallback melhorado (RECOMENDADA p/ rollout).**
Caminho primario = SQL literal do Opus com guard-rails. Generator Haiku so quando o
agente manda NL (raro), e melhorado: regra 4 ancorada em key_fields reais (de S1), sem
truncamento (F1), Evaluator sempre ativo no fallback (mata F2 nesse caminho). Trade-off:
mantem 2 caminhos por um tempo; ganho = sem downgrade no caminho quente + rede para NL.
Medir taxa de NL via shadow antes de remover.

**B. Remover o Generator (executor puro).**
Tool exige SQL; NL retorna erro pedindo SQL (o agente entao usa S1 + escreve). Trade-off:
mais simples e barato; perde rede para callers legados que mandam NL. Evoluir para B
SO depois que a medicao de A mostrar NL → ~0.

**C. Corretor Haiku-testado como malha extra (ORTOGONAL, opcional).**
Quando o loop deterministico nao resolve (ex.: erro nao e campo inexistente), Haiku
propoe correcao E ela so e aceita apos teste: re-passa pelo validador deterministico
e/ou `EXPLAIN`/dry-run read-only. Trade-off: cobre erros que o deterministico nao pega,
sem confiar no Haiku as cegas. Decidir se entra ja ou fica para depois.

Recomendacao: **A** + **C opcional**, com plano explicito de evoluir para **B** por
medicao.

## Design proposto

- **Contrato explicito** (mata F5): `consultar_sql` aceita `sql=<pronto>` OU
  `pergunta=<NL>`. `sql` preenchido → caminho literal; `pergunta` → fallback. Sem
  heuristica `looks_like_raw_sql` no caminho feliz (mantida so como guarda de seguranca
  se vier NL em `sql`).
- **Caminho literal primario** (ja esboçado em `run()` SQL-first, `text_to_sql.py:2021`):
  validador deterministico → campo inexistente devolve schema real + hints
  (`_build_schema_feedback`) para auto-correcao; demais issues viram aviso (Postgres e o
  arbitro). Safety (ETAPA 3) e Executor (ETAPA 4) sempre rodam.
- **Matriz de permissao unica** (separa de geracao): um so ponto define, por `user_id`:
  (a) DML permitido?  (b) tabelas bloqueadas  (c) CAMPOS bloqueados (novo). A GERACAO e
  identica para todos. Admin = permissao ampla; comum = SELECT-only + `pessoal_*` +
  campos sensiveis bloqueados.
- **Sem bloqueio de campo** (decisao 2026-06-07): manter apenas o bloqueio de TABELA
  existente; nao estender o Safety a colunas. Fora de escopo.
- **Fallback Generator melhorado** (se A): regra 4 reescrita (ancora em key_fields reais
  de S1; sem exemplos-ancora), `max_tokens` 500 → ~2000 (F1), Evaluator sempre ativo no
  fallback (F2).
- **Template revalidado** (F4): rodar o validador deterministico no SQL do template
  antes de usar; campo inexistente → descartar template e seguir fluxo.

## Edge cases

- **Agente manda NL em `sql=`** → guarda detecta e roteia para fallback (ou erro claro).
- **DML de admin** → confirmacao humana obrigatoria antes de executar
  (`sql_admin_context`, `hooks.py:1344`); literal, sem reescrita.
- **Comum referencia tabela bloqueada** → bloqueado por Safety com mensagem clara (igual
  ao comportamento atual).
- **Comum tenta DML** → bloqueado por permissao (igual hoje), mas mensagem coerente com a
  nova matriz.
- **Erro semantico (JOIN/FK/agregacao errada)** que nenhum validador pega → e o limite
  conhecido; o Opus e melhor arbitro que o Haiku. Medir via shadow; corretor C so se
  testavel.
- **looks_like_raw_sql legado** → manter so como rede; nao no caminho feliz.

## Pre-mortem

> "3 meses depois, S3 falhou. Por que?"
1. **Liguei Opus-autor para todos e dados errados aumentaram** (erro semantico que nada
   pega) → Mitigacao: medir com shadow ANTES de cortar o Generator; manter A (fallback)
   ate a medicao; corretor C testavel para a cauda.
2. **Removi o Generator (B) cedo demais** e um caller legado quebrou → Mitigacao: so ir
   para B apos shadow mostrar NL → ~0; logar todo fallback.
3. **Corretor Haiku "testado" aprovou lixo** (teste fraco) → Mitigacao: o teste e
   deterministico (re-valida campos) + `EXPLAIN` read-only; nunca "Haiku disse que ta
   ok".
4. **Misturei permissao com geracao de novo** (regra de admin vazou para o autor) →
   Mitigacao: matriz de permissao isolada num modulo, com teste afirmando que admin e
   comum geram pela MESMA via.
5. **Refatorar a permissao quebrou o bloqueio de TABELA existente** (comum escapou de
   `pessoal_*` ou conseguiu DML) → Mitigacao: testes que afirmam que comum continua barrado
   em tabela bloqueada e em DML; nunca regredir o Safety atual.
6. **Contrato `sql=`/`pergunta=` confundiu o agente** → Mitigacao: descricao da tool
   clara + orientacao no system_prompt + exemplos.

## Decisoes fechadas (2026-06-07)

1. **REMOVER o Generator — a menos que prove valor por teste + auditoria.** Postura padrao
   = remover. O Opus vira autor unico (caminho literal). Antes de remover de vez,
   instrumentar auditoria (reusar o shadow `_log_sql_first_shadow`, `text_to_sql.py:1882`)
   que mede: quanto chega como NL vs SQL e, quando NL, se o Generator AGREGA (qualidade
   testavel). Se nao agregar, remover (a tool passa a exigir `sql=`). So sobrevive se a
   auditoria provar valor.
2. **Corretor Haiku-testado: mesma regra** — so entra se provar valor com teste +
   auditoria. Nao entra por padrao. A correcao default e DETERMINISTICA (devolver campos
   reais + hints → o Opus refaz).
3. **Bloqueio so de TABELA (sem bloqueio de campo)** — manter exatamente o que existe hoje
   (`extra_blocked_tables` / `TABELAS_PESSOAL`). NAO adicionar bloqueio por campo (decisao
   do usuario: nao desviar do escopo). Toda mencao a "campo proibido" neste plano esta
   CANCELADA.
4. **Mesma tool, 2 parametros** — `consultar_sql` aceita `sql=` (literal) OU `pergunta=`
   (fallback NL, enquanto o Generator existir). Elimina a heuristica `looks_like_raw_sql`
   no caminho feliz.
5. **SQL-first deixa de ser canary** — vira o comportamento padrao. Com a remocao do
   Generator (item 1), `SQL_AGENT_SQL_FIRST` perde sentido e e aposentada; ate la, default
   "on" para todos apos S1.

## Testes e verificacao

- pytest: SQL literal valido → executa sem reescrita; SQL com campo inexistente →
  retorna schema real + hints (sem Generator).
- pytest: admin e comum sobre a MESMA pergunta → mesmo caminho de geracao; diferenca so
  em permissao (comum bloqueia DML/tabela/campo).
- pytest: bloqueio de TABELA resiste a bypass (alias, subquery) — comportamento atual preservado.
- pytest: template com campo inexistente e descartado (F4).
- pytest: fallback Generator com `max_tokens` novo nao trunca CTE de referencia (F1);
  Evaluator sempre roda no fallback (F2).
- Shadow: medir taxa de entrada NL vs SQL e `would_block` (reusar
  `_log_sql_first_shadow`, `text_to_sql.py:1882`) antes de decidir B.

## Conformidade

- Matriz de permissao: fonte unica (modulo dedicado), reutilizada por executor e por
  `buscar_tabelas` (S1).
- Mudanca de contrato da tool → atualizar descricao (`text_to_sql_tool.py:386`),
  `system_prompt.md` e `sql_admin_context` juntos (R8/coerencia de camadas).
- Sem DDL previsto (so script + tool + prompt).
- Respeitar R12.2 do system_prompt: SQL-first e para LEITURA analitica e DML de admin
  confirmado; nao substituir skills de dominio para WRITE de negocio.
