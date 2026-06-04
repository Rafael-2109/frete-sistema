<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-04
-->
# HORA — Pedido de Venda: unificação multi-item das 2 telas + submit único (FU-2 + FU-3 + FU-5)

> **Papel:** spec de design do refactor que (FU-2) torna a área de "moto vendida" **idêntica** entre criação e edição via um componente compartilhado de lista; (FU-3) permite **N motos na criação** (hoje cria 1); e (FU-5) reduz os vários "Salvar X" granulares a **um único "Salvar Pedido"** que persiste tudo numa transação. Evolui [2026-06-03-hora-pedido-venda-edicao-autocomplete-design.md](2026-06-03-hora-pedido-venda-edicao-autocomplete-design.md) (seção "Follow-ups v2"). FU-4 (bug do filtro) e FU-1 (listar ao clicar) já tratados — ver "Status dos follow-ups".

## Indice

- [Contexto](#contexto)
- [Status dos follow-ups](#status-dos-follow-ups)
- [Estado atual (fatos com fonte)](#estado-atual-fatos-com-fonte)
- [Decisões aprovadas (Q&A)](#decisões-aprovadas-qa)
- [Arquitetura](#arquitetura)
- [Backend — Criação multi-item](#backend--criação-multi-item)
- [Backend — Edição reconciliadora (`salvar_pedido_completo`)](#backend--edição-reconciliadora-salvar_pedido_completo)
- [Frontend — componente compartilhado de lista](#frontend--componente-compartilhado-de-lista)
- [Rotas](#rotas)
- [Máquina de status e guards](#máquina-de-status-e-guards)
- [Faseamento](#faseamento)
- [Não-objetivos](#não-objetivos)
- [Testes](#testes)
- [Riscos e pontos de atenção](#riscos-e-pontos-de-atenção)

## Contexto

A tela de Pedido de Venda (`HoraVenda`) já é única (`pedido_venda_novo.html`, unificação de 2026-06-03 §18), operando em 2 modos no mesmo template: criação (`{% else %}`) e edição (`{% if venda %}`). Mas a **área de motos diverge** entre os modos: a criação usa o componente cascata+desconto para **1 moto**; a edição usa uma tabela de itens + um form "adicionar moto" à parte. Além disso, a edição tem **vários botões "Salvar X"** (um por seção/form granular). O dono do módulo pediu: mesma área de motos nas 2 telas (FU-2), N motos na criação (FU-3) e um único "Salvar Pedido" (FU-5) — tratados juntos por serem interligados.

## Status dos follow-ups

- **FU-4 (bug — filtro modelo+cor não aplicava)**: diagnosticado como **cache de browser** do `autocomplete.js` antigo (`Cache-Control: immutable, max-age=604800` no `Caddyfile:80`, URL `/static/...` sem `?v=`). Código-fonte (backend + inline script + autocomplete.js dinâmico) estava correto e já em PROD; hard-refresh resolve. Fechado pelo dono. Risco sistêmico latente (qualquer mudança futura em JS/CSS fica invisível por 7d a usuários recorrentes) — conserto opcional (cache-busting global no app factory) fora deste escopo.
- **FU-1 (listar ao clicar)**: **implementado** (commit `32f94d22a` na branch desta entrega). `autocomplete_service.chassis(permitir_vazio=)` + rota lê `vazio_ok=1` + `autocomplete.js` ganhou `data-hora-open-on-focus`; markup do chassi opta-in. 6 testes verdes.
- **FU-2 + FU-3 + FU-5**: esta spec.

## Estado atual (fatos com fonte)

- **Criação**: rota `tagplus_pedido_venda_criar` (`app/hora/routes/tagplus_routes.py:1034-1198`) lê **1 chassi singular** + arrays de pagamentos + header; chama `criar_venda_manual` (`app/hora/services/venda_service.py:635-916`), que cria 1 `HoraVenda` + **1** `HoraVendaItem` + N pagamentos + `RESERVADA` + auditoria, **commit único** (`:915`).
- **Edição**: **13 endpoints granulares** em `app/hora/routes/vendas.py`, cada um com `commit` próprio no service. Os 5 relevantes a este refactor: `vendas_editar` (`:330`, header), `vendas_pagamentos_editar` (`:386`), `vendas_item_adicionar` (`:538`), `vendas_item_remover` (`:566`), `vendas_item_editar` (`:584`, só valor — Frente A).
- **Matriz por status** `_CAMPOS_EDITAVEIS_HEADER` (`venda_service.py:1084-1112`): INCOMPLETO/COTAÇÃO = tudo; CONFIRMADO = sem CPF/nome e sem add/remove item; FATURADO = só `observacoes`; CANCELADO = nada. Itens só editáveis em COTAÇÃO. Defesa extra: NFe em-voo bloqueia tudo exceto `observacoes`.
- **Modelo**: `HoraVendaItem` (`app/hora/models/venda.py:222-276`) tem `numero_chassi`, `preco_tabela_referencia`, `desconto_aplicado`, `desconto_percentual`, `preco_final`. `HoraVendaPagamento` (`:382-445`): `forma_pagamento_hora`, `valor`, `numero_parcelas`, `aut_id`. `HoraVenda.valor_total` = soma de `preco_final`.
- **Gap estrutural**: `adicionar_item_pedido`/`remover_item_pedido` ajustam `venda.valor_total` mas **não** re-rodam `_avaliar_status_pagamento` — a soma das formas fica defasada e o operador tem de salvar pagamentos à parte. Origem da fricção que FU-5 elimina.
- **Componentes**: `_componente_moto_desconto.html` (1 moto, ids `f-modelo/f-cor/f-chassi/f-preco-tabela/f-desconto-pct/f-desconto-rs/f-valor`) incluído 2× (criação L883, "adicionar moto na edição" L503 — branches mutuamente exclusivas). `_pedido_venda_scripts.html` tem `wireDescontoSync(rootEl, preco)` (por-escopo via classes `.js-*` + `data-preco-tabela`) usado nos collapses de edição de item.

## Decisões aprovadas (Q&A)

| # | Decisão | Escolha |
|---|---------|---------|
| 1 | Modelo de persistência | **Form unificado + 1 submit que reconcilia** (criação: 1 POST cria N; edição: 1 POST reconcilia header+itens+pagamentos em 1 transação) |
| 2 | Transições (Confirmar/Voltar-cotação/Cancelar/Descartar/Emitir NFe) | **Continuam botões próprios** — são mudança de estado/permissão, não "salvar" |
| 3 | Peças no pedido (XOR moto) | **Ficam inline (fora do v1)** — add/remove AJAX atuais; unificação só de motos+header+pagamentos. Peças no submit único = v2 |
| 4 | 5 rotas granulares substituídas | **Mantidas deprecadas** (sem link na UI), removendo só os forms do template; cleanup das rotas numa limpeza posterior |
| 5 | Troca de chassi de item | Continua **remover + adicionar** (regra Frente A) — natural na lista (remove a linha, adiciona outra) |

## Arquitetura

Um **componente compartilhado de lista de motos** (`_lista_motos.html`) renderiza N linhas-moto idênticas nas 2 telas (FU-2). Cada tela tem **um único "Salvar Pedido"** (FU-5):

- **Criação**: `POST` → `criar_venda_manual(itens=[...])` cria pedido + N motos + pagamentos numa transação (FU-3).
- **Edição** (COTAÇÃO/INCOMPLETO): `POST` → `salvar_pedido_completo` **reconcilia** o estado submetido (header + itens + pagamentos) contra o banco numa transação. CONFIRMADO/FATURADO: aplica só os campos que a matriz permite; lista de motos e pagamentos renderizam **read-only**.
- **Transições**: botões próprios, inalterados (decisão #2).

Princípio de isolamento: o reconciliador compõe **helpers flush-only** de responsabilidade única (`_aplicar_header`, `_aplicar_itens`, `_aplicar_pagamentos`), cada um testável isoladamente; o commit é **único** e fica no orquestrador (corrige o gap itens↔pagamentos e evita o vazamento de savepoint da memória `gotcha_commit_service_vaza_savepoint`).

## Backend — Criação multi-item

`criar_venda_manual(...)` troca os parâmetros singulares `numero_chassi`/`valor_final` por **`itens: list[dict]`** (`[{'numero_chassi': str, 'valor_final': Decimal}, ...]`, exige ≥1):
- Loop: `_lock_chassi_e_validar_disponivel(chassi)` + resolve preço (`_resolver_preco_tabela`) + cria `HoraVendaItem` + emite `RESERVADA` por item.
- `valor_total` = soma de `preco_final`; `_avaliar_status_pagamento` uma vez no fim; **1 commit**.
- Validação: todos os chassis distintos e disponíveis; falha de qualquer item aborta a transação inteira (nenhum pedido parcial).

Rota `tagplus_pedido_venda_criar`: passa a ler `chassi[]` + `valor[]` (array-form, espelhando os arrays de pagamento já existentes) e montar a lista `itens`. Demais campos (header, pagamentos) inalterados.

## Backend — Edição reconciliadora (`salvar_pedido_completo`)

Nova função `salvar_pedido_completo(venda_id, header: dict, itens: list[dict], pagamentos: list[dict], usuario)` numa **única transação** (flush internos, 1 commit):

1. **Header** → `_aplicar_header`: aplica apenas os campos permitidos pela matriz do status atual (reusa a validação de `editar_venda`/`_validar_campo_editavel`). NFe em-voo → só `observacoes`.
2. **Itens** → `_aplicar_itens` (**só processa em COTAÇÃO**; em CONFIRMADO+ os itens são read-only e a submissão é ignorada). Cada linha submetida traz `item_id` (existente) ou vazio (novo):
   - existente presente → atualiza `valor_final` se mudou (deriva desconto via `_resolver_preco_tabela`; **sem troca de chassi**);
   - existente ausente da submissão → remove (`DEVOLVIDA`), respeitando o guard "não remove o último item";
   - linha nova (sem `item_id`, com chassi) → adiciona (`RESERVADA` + lock).
3. **Pagamentos** → `_aplicar_pagamentos`: substitui todos (reusa a lógica de `editar_pagamentos`) — **só em INCOMPLETO/COTAÇÃO**.
4. Recalcula `valor_total` a partir dos itens e **re-avalia status** (`_avaliar_status_pagamento`) numa só passada → corrige o gap itens↔pagamentos.
5. Auditoria por sub-operação (`EDITOU_HEADER`/`ADICIONOU_ITEM`/`REMOVEU_ITEM`/`EDITOU_ITEM`/pagamentos) preservada.

**Refator de suporte** (risco principal): extrair a lógica de header/itens/pagamentos das funções de service atuais em helpers **flush-only** (`_aplicar_*`); as funções públicas (`editar_venda`, `editar_pagamentos`, `adicionar_item_pedido`, `remover_item_pedido`, `editar_item_pedido`) passam a ser `helper + commit` (preservam comportamento e os testes de `tests/hora/test_pedido_workflow.py`). `salvar_pedido_completo` = helpers + **1 commit**.

## Frontend — componente compartilhado de lista

`app/templates/hora/tagplus/_lista_motos.html`: lista repetível onde cada linha-moto reusa o markup do `_componente_moto_desconto.html` (modelo/cor filtro + chassi autocomplete com `data-hora-open-on-focus` do FU-1 + desconto %/R$/valor), acrescida de hidden `item_id` (vazio na criação/linha nova) e botão "remover linha". Botão "+ Adicionar moto" clona uma linha-template (`<template>`). Bloco de pagamentos no mesmo form. Um `<button type="submit">Salvar Pedido</button>` ao fim.

- **IDs por-linha**: os ids `f-*` globais viram sufixados por índice/`item_id` (`f-chassi-<k>` etc.) — elimina a colisão de ids ao ter N linhas. A sincronia de desconto usa `wireDescontoSync(rootEl, preco)` por-linha (já existe, por-escopo via classes `.js-*` + `data-preco-tabela`). A cascata modelo/cor→chassi (`atualizarFiltroChassi`) é reescrita para operar **por linha** (querySelector dentro da linha, não `getElementById` global).
- **Read-only por status**: em CONFIRMADO/FATURADO/CANCELADO a lista e os pagamentos renderizam travados (display), coerente com a matriz; o "Salvar Pedido" só envia o que é editável.

## Rotas

- `tagplus_pedido_venda_criar` (`tagplus_routes.py`): lê arrays `chassi[]`/`valor[]` (criação multi-item).
- **Nova** `vendas_salvar_pedido` (`POST /vendas/<id>/salvar`, perm `vendas/editar`) → `salvar_pedido_completo`. Lê header + arrays de itens (`item_id[]`, `item_chassi[]`, `item_valor[]`) + arrays de pagamentos.
- **Deprecadas** (decisão #4): `vendas_editar`, `vendas_pagamentos_editar`, `vendas_item_adicionar`, `vendas_item_remover`, `vendas_item_editar` permanecem registradas (sem link na UI, como fallback); **os forms correspondentes saem do template**. Cleanup das rotas + funções de service redundantes numa limpeza posterior.
- Inalteradas: transições, `vendas_definir_loja`, divergências, peças (inline).

## Máquina de status e guards

| Status | Itens | Pagamentos | Header | Salvar Pedido envia |
|---|---|---|---|---|
| INCOMPLETO | editável | editável | tudo | header + itens + pagamentos |
| COTAÇÃO | editável | editável | tudo | header + itens + pagamentos |
| CONFIRMADO | read-only | read-only | contato/endereço/operacional | só campos da matriz |
| FATURADO | read-only | read-only | só observações | só observações |
| CANCELADO | read-only | read-only | nada | nada (form sem submit) |

Guards inalterados: `_lock_chassi_e_validar_disponivel` (SELECT FOR UPDATE), "não remove o último item", NFe em-voo → só `observacoes`, escopo de loja, venda sem loja só admin.

## Faseamento

1. **Backend criação multi-item**: `criar_venda_manual(itens=...)` + arrays na rota + TDD. (FU-3 backend)
2. **Componente `_lista_motos.html` + criação multi-item UI** + "Salvar Pedido" único (criação). (FU-2 + FU-3 + FU-5 criação)
3. **`salvar_pedido_completo` + rota `vendas_salvar_pedido`** + edição usa o MESMO componente + "Salvar Pedido" único + remoção dos forms granulares (rotas deprecadas vivas). (FU-2 + FU-5 edição)
4. **Cleanup + regressão**: smoke render dos 5 status sem 500, testes do reconciliador (add/remove/update/status), validação visual Playwright.

## Não-objetivos

- Não alterar o schema (`HoraVenda`/`HoraVendaItem`/`HoraVendaPagamento`) — sem migration.
- Não unificar **peças** no submit único nesta v1 (decisão #3).
- Não remover as 5 rotas granulares agora (decisão #4) — só os forms.
- Não permitir troca de chassi via edição de item (decisão #5).
- Não tocar transições, TagPlus, Odoo, outros módulos.
- Não fazer o cache-busting global dos estáticos (FU-4 fechado como cache; conserto opcional separado).

## Testes

- `tests/hora/` (pytest, sem LLM):
  - Criação: `criar_venda_manual(itens=[a,b])` cria 2 `HoraVendaItem` + 2 `RESERVADA`; `valor_total` = soma; falha de 1 item aborta tudo; ≥1 item obrigatório.
  - Reconciliador: `salvar_pedido_completo` adiciona linha nova, remove ausente, atualiza valor, recalcula status numa transação; respeita matriz (CONFIRMADO ignora itens/pagamentos; FATURADO só observações); guard "não remove último".
  - Regressão: smoke de render dos 5 status sem 500; helpers flush-only não comitam (1 commit no orquestrador).
- Visual (Playwright, login bot): criar pedido com 2 motos; editar adicionando/removendo moto e salvando com 1 botão; status INCOMPLETO↔COTAÇÃO conforme soma; zero erros de console.

## Riscos e pontos de atenção

- **Reconciliador transacional** (maior risco): o refactor flush-only deve manter 1 commit e não vazar savepoint (`gotcha_commit_service_vaza_savepoint`); os testes de workflow existentes precisam continuar verdes (services públicos = helper + commit).
- **IDs por-linha**: garantir unicidade (`-<k>`/`-<item_id>`) e wiring defensivo (cada linha só inicializa se seus elementos existem) — espelha o cuidado dos collapses da Frente A.
- **Cascata por-linha**: `atualizarFiltroChassi`/`carregarCores`/`preencherDadosDoChassi` hoje são globais (`getElementById`) — reescrever para escopo de linha sem quebrar a criação 1-moto durante o faseamento.
- **Status INCOMPLETO ao adicionar/remover**: ao reconciliar, recalcular status numa passada evita o pedido ficar com soma de pagamentos defasada (bug atual). Validar a transição INCOMPLETO→COTAÇÃO no mesmo submit.
- **Gotcha worktree/testes**: rodar pytest com `DATABASE_URL` da raiz (sem `.env` cai em SQLite); comandos da raiz do worktree (hooks PAD usam path relativo).
- **Frente A (collapse de edição de item)**: é substituída pela lista editável inline — remover o markup do collapse junto com os forms granulares (Fase 3) para não deixar lixo.
