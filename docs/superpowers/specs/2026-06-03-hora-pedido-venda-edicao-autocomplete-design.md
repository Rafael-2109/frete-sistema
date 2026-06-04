<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-03
-->
# HORA — Pedido de Venda: editar item (moto travada), Enter=Próximo, chassi autocomplete + restauração de regressões

> **Papel:** spec de design de quatro frentes na tela unificada de Pedido de Venda (`HoraVenda`) do módulo Lojas HORA: (A) ao editar uma moto já no pedido, só desconto/valor são editáveis — trocar a moto exige remover+readicionar; (B) a tecla Enter avança para o próximo campo em vez de submeter; (C) o chassi vira autocomplete (cascata modelo/cor como filtro opcional); (D) restaurar recursos e proteções CRÍTICOS+ALTOS perdidos na unificação anterior (commit `9a50b5af8`/`e6cc96586`).

## Indice

- [Contexto](#contexto)
- [Escopo e faseamento](#escopo-e-faseamento)
- [Decisões aprovadas (Q&A)](#decisões-aprovadas-qa)
- [Auditoria de regressão (entrada da Frente D)](#auditoria-de-regressão-entrada-da-frente-d)
- [Frente A — Editar item: desconto+valor, moto travada](#frente-a--editar-item-descontovalor-moto-travada)
- [Frente B — Enter = "Próximo"](#frente-b--enter--próximo)
- [Frente C — Chassi autocomplete (cascata + autocomplete)](#frente-c--chassi-autocomplete-cascata--autocomplete)
- [Frente D — Restaurar regressões CRÍTICOS + ALTOS](#frente-d--restaurar-regressões-críticos--altos)
- [Backend (rotas/services)](#backend-rotasservices)
- [Não-objetivos](#não-objetivos)
- [Testes](#testes)
- [Riscos e pontos de atenção](#riscos-e-pontos-de-atenção)

## Contexto

Esta spec **evolui** a tela unificada criada em [2026-06-03-hora-unificar-pedido-venda-design.md](2026-06-03-hora-unificar-pedido-venda-design.md). Após a unificação (que removeu `venda_detalhe.html` e fez `pedido_venda_novo.html` operar em 2 modos), o dono do módulo identificou três necessidades de UX e pediu uma auditoria de regressão da unificação.

**Estado atual relevante**:
- Tela única `app/templates/hora/tagplus/pedido_venda_novo.html`: modo edição em `{% if venda %}` (linhas 9-518), modo criação no `{% else %}` (linhas 520-777).
- Componente de moto/desconto compartilhado: `app/templates/hora/tagplus/_componente_moto_desconto.html` (cascata modelo→cor→chassi via `<select>` + desconto %/R$ + valor final). IDs fixos: `f-modelo`, `f-cor`, `f-chassi`, `f-preco-tabela`, `f-desconto-pct`, `f-desconto-rs`, `f-valor`.
- JS compartilhado: `app/templates/hora/tagplus/_pedido_venda_scripts.html` (cascata AJAX, `recalcular(origem)` para sincronia desconto, ViaCEP, pagamentos, frete CIF). Tudo via `getElementById` (IDs globais únicos).
- Edição de item existente (modo edição): collapse `#item-edit-{{ item.id }}` com **só** "Trocar chassi" (texto) + "Novo valor final" (`pedido_venda_novo.html:378-395`).
- Backend: `vendas_item_editar` (`app/hora/routes/vendas.py:584-612`) lê `novo_chassi`+`valor_final` e chama `venda_service.editar_item_pedido(novo_chassi=, novo_valor=)` (`app/hora/services/venda_service.py:1371-1471`). A matriz de edição de header é `_CAMPOS_EDITAVEIS_HEADER` (`venda_service.py:1063-1081`).
- Autocomplete genérico do módulo: `app/static/js/hora/autocomplete.js` (markup `data-hora-autocomplete="<tipo>"`, `data-hora-extra-params`, `data-hora-target-id`). Endpoint chassi: `/hora/autocomplete/chassi` → `autocomplete_service.chassis` (`app/hora/routes/autocomplete.py:36-43`). Padrão de uso "estilo estoque": `app/templates/hora/estoque_lista.html`.
- API de cascata atual do pedido: `/hora/tagplus/pedido-venda/api/{cores,chassis,preco-modelo}` (`app/hora/routes/tagplus_routes.py:1201-1290`).

## Escopo e faseamento

Quatro frentes, **dentro de `app/hora/`** (templates, rotas, services, testes) + doc. Sem Odoo/TagPlus/outros módulos. Implementação **faseada** (cada fase testável e mergeável de forma independente):

- **Fase 1 — Features pedidas**: A (editar item) + B (Enter) + C (autocomplete chassi).
- **Fase 2 — Regressões CRÍTICAS**: peças, reimportar TagPlus, frete `disabled`, confirm do descarte, aviso de endereço travado.
- **Fase 3 — Regressões ALTAS**: KPIs, parcelamento, auditoria Campo/De/Para, histórico de divergências, frete multi-item, vendedor fallback, pagamentos, modalidade legada.

## Decisões aprovadas (Q&A)

| # | Decisão | Escolha |
|---|---------|---------|
| 1 | Escopo das regressões a restaurar agora | **CRÍTICOS + ALTOS** (médios/baixos = backlog) |
| 2 | Modelo do autocomplete de chassi | **Cascata + chassi autocomplete** (modelo/cor seguem como filtros opcionais; só o chassi vira autocomplete) |
| 3 | O que fica editável ao editar um item | **Desconto (%/R$) + valor final**; modelo/cor/chassi **travados**. Trocar moto = remover + readicionar |
| 4 | Tecla Enter nas telas novo/edição | **Avança para o próximo campo** (não submete); textarea mantém Enter; salvar só por clique |
| 5 | UI da edição de item | **Collapse inline por item** (não modal) — exige IDs sufixados por `item.id` + sincronia desconto↔valor por-escopo |
| 6 | Faseamento | **Sim**, ordem 1→2→3 |
| 7 | P-14 (endereço em FATURADO) | **Não restaurar** — o template novo (`ro_oper = is_faturado or is_cancelado`) está alinhado à matriz `_CAMPOS_EDITAVEIS_HEADER` (FATURADO só aceita `observacoes`). O antigo contrariava o backend. |

## Auditoria de regressão (entrada da Frente D)

Comparação `venda_detalhe.html` antigo (recuperado de `9a50b5af8^`, 1223 linhas) × `pedido_venda_novo.html` modo edição atual. **33 itens perdidos**; restauram-se os CRÍTICOS+ALTOS (Frente D). Confirmação por `grep` no template atual: ausência de `Reimportar`, `itens_peca`, `hora-kpi`, `nf_saida_chave_44`, `campo_alterado`, `Historico de divergencias`, `data-item-chassi`; `confirm()` caiu de 7→5; `valor_frete` usa `readonly`.

**Reclassificado (não é regressão):** P-14 — endereço travado em FATURADO (ver decisão #7).

**Não restaurar agora (backlog médio/baixo):** textos de `confirm()` truncados (Confirmar/Voltar cotação), tooltips, placeholders, "(você)", nº NF no `<h2>`, `origem_criacao`.

## Frente A — Editar item: desconto+valor, moto travada

**Objetivo**: ao editar uma moto já no pedido (status COTACAO, `is_cotacao and pode_editar`), o operador ajusta apenas **desconto %/R$ + valor final**; **modelo/cor/chassi ficam read-only**. Trocar a moto = remover (lixeira) + readicionar (Frente C).

**UI** (`pedido_venda_novo.html`, collapse `#item-edit-{{ item.id }}`, hoje L378-395):
- Substituir os campos "Trocar chassi" + "Novo valor" por:
  - Bloco read-only (display): chassi (mono), modelo, cor.
  - Preço de tabela (ref.) read-only — valor `item.preco_tabela_referencia`.
  - Desconto % (`f-desconto-pct-{{ item.id }}`), Desconto R$ (`f-desconto-rs-{{ item.id }}`), Valor final (`f-valor-{{ item.id }}`) — editáveis, sincronizados, ancorados no preço de tabela do item.
  - Container do collapse com `data-preco-tabela="{{ item.preco_tabela_referencia }}"` para o JS de sincronia.
  - Botão "Salvar item" → POST `hora.vendas_item_editar` enviando **somente `valor_final`** (o backend deriva o desconto via `_resolver_preco_tabela`).

**JS** (`_pedido_venda_scripts.html`): **refatorar** a sincronia desconto%↔R$↔valor de `recalcular(origem)` (hoje em IDs globais) para uma função **por-escopo** `wireDescontoSync(rootEl, precoTabela)` que opera via `querySelector` dentro de `rootEl` (classes `.js-desconto-pct`, `.js-desconto-rs`, `.js-valor`). Aplicar:
- ao componente de criação/adição (1 instância — `_componente_moto_desconto.html` ganha essas classes além dos ids `f-*`);
- a cada collapse `#item-edit-*` (lê `data-preco-tabela` do container).

**Backend** (`vendas.py:584-612`): `vendas_item_editar` **deixa de ler `novo_chassi`** e passa `novo_chassi=None` ao service (defesa em profundidade — a moto nunca é trocada por esta rota). `venda_service.editar_item_pedido` permanece com a capacidade de troca (preserva os testes existentes de troca em `tests/hora/test_pedido_workflow.py`), apenas não é mais exposta pela UI.

## Frente B — Enter = "Próximo"

**Objetivo**: nas telas de novo pedido e edição, Enter num campo não submete o form — avança o foco para o próximo campo.

**JS** (`_pedido_venda_scripts.html`, novo bloco defensivo): para cada `form` de pedido presente (`#form-pedido-venda`, `#form-add-moto-edicao`, e os forms de item/pagamento), interceptar `keydown` com `key === 'Enter'` em elementos `input` (text/number/email/tel/search) e `select` → `preventDefault()` + focar o próximo elemento focável do form (lista ordenada de `input,select,textarea,button` visíveis e habilitados). **Exceções**: `textarea` mantém Enter (nova linha); botões `type=submit` mantêm Enter (acessibilidade ao focar o botão). Submeter passa a ser ação explícita por clique.

## Frente C — Chassi autocomplete (cascata + autocomplete)

**Objetivo**: o campo chassi do componente de moto vira autocomplete "estilo estoque", mantendo modelo/cor como filtros opcionais.

**UI** (`_componente_moto_desconto.html`): trocar `<select id="f-chassi">` (L19-24) por:
```html
<input type="text" id="f-chassi" name="chassi" class="form-control chassi-mono"
       data-hora-autocomplete="chassi" data-hora-min-chars="2"
       data-hora-extra-params="disponivel=1" autocomplete="off" required>
```
Modelo (`f-modelo`) e cor (`f-cor`) **permanecem selects** de filtro **opcionais**. O JS:
- ao mudar modelo/cor, atualiza `data-hora-extra-params` do `#f-chassi` (`disponivel=1&modelo_id=<x>&cor=<y>`) e re-inicializa o autocomplete (`window.HoraAutocomplete.init`);
- ao escolher um chassi (evento `change`), busca os dados do chassi e preenche modelo/cor (se vazios) e o preço de tabela (reusa `/hora/tagplus/pedido-venda/api/preco-modelo`), disparando a sincronia de desconto.

**Backend** (`autocomplete_service.chassis` + `routes/autocomplete.py:36-43`): estender para aceitar `disponivel` (bool), `modelo_id` (int) e `cor` (str). `disponivel=1` filtra por chassis **em estoque** (mesmo critério de `estoque_service` — eventos que mantêm em estoque), respeitando `lojas_permitidas_ids()`. O JSON de cada item passa a incluir `modelo_id`, `modelo_nome`, `cor`, `loja_nome` e flags (avarias/peças faltando), para o preenchimento no front.

**Impacto**: o componente é compartilhado entre modo criação e "adicionar moto na edição" — a mudança beneficia ambos (consistência). A cascata atual via `<select>` de chassi (`/api/chassis`) deixa de ser necessária para popular o select, mas a API permanece (usada para validação/preço).

## Frente D — Restaurar regressões CRÍTICOS + ALTOS

Tudo no modo edição (`{% if venda %}`) de `pedido_venda_novo.html`, reusando markup do `venda_detalhe.html` antigo (referências de linha do arquivo recuperado) e rotas já existentes.

**🔴 Críticos**
1. **Seção "Peças do pedido"** (antigo L857-933): tabela read-only + adicionar via autocomplete de peça (`data-hora-autocomplete="peca"`) + remover com `confirm()`. Rotas `hora.venda_adicionar_item_peca`/`hora.venda_remover_item_peca` já existem (bug de redirect já corrigido na unificação). Guard `is_cotacao and pode_editar`.
2. **Botão "Reimportar do TagPlus"** (antigo L51-67): form POST `hora.tagplus_backfill_nfe_unica` com `tagplus_nfe_id`, guard `pode_criar and tem_emissao and venda.emissao_nfe.tagplus_nfe_id`, com `confirm()` e `title`.
3. **`valor_frete`/`tipo_frete_calc` → `disabled` quando não-CIF** (em vez de `readonly`; novo L318-327): preserva frete FOB legado (inputs `disabled` não são submetidos).
4. **Confirm do "Descartar (NF teste)"** (novo L157): restaurar o aviso `A NFe NÃO será cancelada na SEFAZ`.
5. **Aviso contextual de endereço travado**: NÃO reabrir edição em FATURADO (decisão #7); apenas adicionar `small` por status explicando o que está editável (substitui P-13 sem mudar guard).

**🟠 Altos**
6. **KPIs** (antigo L259-283): loja emitente, chave de acesso 44 díg., data, valor total, itens.
7. **Parcelamento** (antigo L465-496): campos `numero_parcelas` + `intervalo_parcelas_dias` (editáveis em COTACAO/CONFIRMADO conforme matriz) + aviso JS "intervalo < 7 dias".
8. **Auditoria com colunas Campo/De/Para** (novo L504-518): exibir `campo_alterado`/`valor_antes`/`valor_depois`.
9. **Histórico de divergências (resolvidas)** (antigo L975-999): `<details>` listando todas (abertas+resolvidas).
10. **Frete CIF multi-item** (antigo L1082-1218): `data-item-*` nas linhas de item + preview de margem (alerta "abaixo da tabela").
11. **Vendedor — fallback "(não habilitado)"** (antigo L364-366): se `venda.vendedor` não está em `vendedores_disponiveis`, adicionar `<option>` selecionado preservando o valor (evita zerar vendedor legado ao salvar).
12. **Pagamentos**: badge "INCOMPLETO" no card-header + linha "total formas vs pedido" + coluna "Tipo"; e **corrigir os IDs** do editor de edição para casar com o JS (`pag-edit-container`/`pag-edit-soma` vs `pagamentos-container`/`pag-soma`) — ou unificar IDs — restabelecendo soma em tempo real e AUT/ID dinâmico.
13. **Guard de modalidade de frete legada** (antigo L509-513): se `venda.modalidade_frete` ∉ {0,1}, adicionar `<option disabled>` com o valor legado (não troca silenciosamente ao salvar).

## Backend (rotas/services)

- `app/hora/routes/vendas.py` — `vendas_item_editar`: parar de ler `novo_chassi` (Frente A).
- `app/hora/routes/autocomplete.py` — `autocomplete_chassi`: repassar `disponivel`/`modelo_id`/`cor` (Frente C).
- `app/hora/services/autocomplete_service.py` — `chassis(...)`: novos filtros + campos extras no JSON (Frente C).
- Sem migrations (nenhuma mudança de schema). Sem mudança em `editar_item_pedido`, `adicionar_item_pedido`, `remover_item_pedido` (já cobrem o fluxo remover+readicionar).

## Não-objetivos

- Não mudar o modelo de dados (`HoraVenda`/`HoraVendaItem`) nem migrations.
- Não restaurar regressões médias/baixas (backlog).
- Não permitir troca de moto pela edição de item (decisão #3).
- Não tocar Odoo, TagPlus payload, outros módulos.
- Não reabrir edição de endereço/contato em FATURADO (decisão #7).

## Testes

- `tests/hora/` (pytest, sem LLM — preferência do dono):
  - Frente A: `vendas_item_editar` ignora `novo_chassi` (POST com `novo_chassi` não troca a moto); editar item ajusta `preco_final`/desconto.
  - Frente C: `autocomplete_service.chassis(disponivel=1, modelo_id=, cor=)` retorna só chassis em estoque, respeita loja, inclui campos extras.
  - Regressões: smoke de render do modo edição (cobre peças, KPIs, reimportar, auditoria) sem 500; presença dos elementos restaurados.
- Validação visual via Playwright (login bot): collapse de edição com desconto sincroniza; Enter não submete; autocomplete de chassi filtra; zero erros de console.

## Riscos e pontos de atenção

- **Componente compartilhado** (`_componente_moto_desconto.html`): mudança do chassi afeta criação **e** adição na edição — testar ambos.
- **Refator da sincronia de desconto** (IDs globais → por-escopo): risco de regressão no fluxo de criação; manter `recalcular` funcionando ou migrar criação para a nova função na mesma fase.
- **IDs por-item** nos collapses de edição: garantir unicidade (`-{{ item.id }}`) e wiring defensivo (só inicializa se elementos existem).
- **Autocomplete de disponibilidade**: o filtro `disponivel=1` deve excluir chassis fora de estoque (vendidos/reservados/em trânsito) — reusar o critério canônico de `estoque_service`, não reimplementar.
- **Pagamentos (item 12)**: confirmar em runtime se o editor de edição está realmente sem JS (IDs divergentes) antes de "corrigir"; pode exigir só alinhar IDs.
- **Gotcha worktree/testes**: rodar pytest com `DATABASE_URL` da raiz (sem `.env` cai em SQLite); `create_app` regenera schemas (ruído). Rodar comandos da raiz do worktree (hooks PAD usam path relativo).

## Follow-ups v2 (próxima sessão — NÃO implementado nesta entrega)

Reportados pelo dono do módulo em 2026-06-03 após o deploy. São interligados (FU-2 + FU-3 = refactor grande de UI + backend). **Tratar com brainstorming antes de codar** — não começar sem alinhar design. Ordem sugerida: FU-4 (bug, rápido) → FU-1 (UX) → FU-2 + FU-3 (refactor unificado).

- **FU-4 (BUG — prioridade)**: o autocomplete de chassi **não está filtrando por modelo+cor**. `atualizarFiltroChassi()` (`_pedido_venda_scripts.html`) seta `f-chassi.dataset.horaExtraParams = "disponivel=1&modelo_id=..&cor=.."` e `autocomplete.js` lê `data-hora-extra-params` **dinamicamente** no fetch — mas na prática o filtro não está sendo aplicado. Investigar (não assumir): (a) o deploy estava concluído quando testado?; (b) no Network do browser, o GET `/hora/autocomplete/chassi` envia `modelo_id`/`cor`?; (c) os listeners de `#f-modelo`/`#f-cor` atualizam o dataset ANTES do fetch?; (d) `autocomplete_service.chassis(modelo_id, cor)` filtra — há teste verde (`test_chassis_filtra_por_modelo_id`), então o backend está OK. Hipótese: bug no front (dataset desatualizado no momento do fetch, ou ordem de eventos) ou deploy não concluído quando testado.
- **FU-1 (UX)**: o autocomplete deve **permitir clicar para listar ou preencher** — hoje só dispara com ≥2 chars digitados (`data-hora-min-chars="2"`, fetch no `input` e no `focus` apenas se já há texto). Desejado: clicar no campo abre a lista (top-N disponíveis) sem digitar. Afeta `app/static/js/hora/autocomplete.js` (handler de focus/click com `q` vazio) — **tornar opt-in via data-attribute** para não impactar as ~20 telas que já usam autocomplete; o backend pode precisar aceitar `q` vazio retornando top-N (hoje `_MIN_CHARS=2` corta).
- **FU-2 (Refactor UI)**: a **área de "Moto vendida" deve ser IGUAL entre as 2 telas** (criação `{% else %}` vs edição `{% if venda %}` em `pedido_venda_novo.html`). Hoje divergem: criação usa o componente cascata+desconto para **1 moto**; edição usa tabela de itens + form "adicionar moto". Unificar num único componente de lista de itens. Interligado com FU-3.
- **FU-3 (Feature)**: o **pedido deve permitir N motos na CRIAÇÃO** (hoje `criar_venda_manual` / `tagplus_pedido_venda_criar` cria **1 moto** via campos singulares `chassi`/`valor`; a edição já permite N via `adicionar_item_pedido`). Opções de design: (a) criar o pedido e adicionar itens via AJAX antes de confirmar; (b) form com lista repetível de motos → backend aceita arrays e cria N `HoraVendaItem`. Decisão de design significativa — **brainstorming obrigatório**. Unifica com FU-2.
- **FU-5 (UX)**: **um único "Salvar Pedido" no final** — hoje a tela (edição) tem vários botões salvar por seção (cada form granular: "Salvar dados do pedido" → `vendas_editar`, "Salvar pagamentos" → `vendas_pagamentos_editar`, "Salvar item" → `vendas_item_editar`, "Adicionar item/peça", "Definir/Trocar loja"). O dono quer **um botão "Salvar Pedido" ao final** que persista tudo de uma vez. Fortemente ligado a FU-2 + FU-3: a unificação multi-item provavelmente exige repensar os submits granulares → um único submit do pedido inteiro (ou orquestração AJAX com 1 botão). Brainstorming junto.

**Observação de comportamento (registrar p/ investigar, liga com FU-2/bug pré-existente)**: o dono confirmou que as motos **aparecem corretamente** num pedido em **COTAÇÃO** (a tabela de itens da edição funciona — boa notícia, valida a entrega). Dúvida em aberto: em **INCOMPLETO** as motos podem não aparecer. Investigar se o card de itens depende do status ou se um pedido INCOMPLETO antigo simplesmente não tinha itens (criado com erro). O "bug pré-existente" do handoff anterior ("motos não aparecem na edição") está **parcialmente esclarecido** — não é geral; verificar especificamente o status INCOMPLETO.
