<!-- doc:meta
tipo: explanation
camada: L2
sot_de: sincronizacao bidirecional de pedidos de venda HORA <-> TagPlus
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-29
-->

# HORA ↔ TagPlus — Sincronização bidirecional de pedidos de venda (Design)

> **Papel:** spec/design da sincronização de pedidos de venda entre o módulo HORA e o TagPlus (criação, cancelamento, numeração e replicação reversa). Lido antes de executar os planos `docs/superpowers/plans/2026-06-29-hora-tagplus-sync-*`.
>
> **Status (2026-06-29):** **Fase 1 + Fase 2a DEPLOYADAS** (commit `5027048c7`, PROD). **Fase 2b IMPLEMENTADA (flag-OFF, NÃO deployada — commit local)**: payload completo de pedido (reusa `PayloadBuilder`), `criar/atualizar/cancelar` wired nos 4 pontos do `venda_service`, emissão **mantém `POST /nfes` rico** e só adiciona `pedido_os_vinculada` ao corpo (`emissor_nfe._enviar_nfe`) — tudo atrás de `HORA_TAGPLUS_PUSH_PEDIDO` (default OFF, `POST /nfes` intacto). **NÃO usa `to_nfe`** (revisado 2026-06-29 — ver §4). **Fase 3 COMPLETA (flag `HORA_TAGPLUS_REVERSO` default OFF, commit local; migration `hora_63` já em PROD)**: `busca_pedido_por_numero` + `numero_walk` (anti-loop/idempotência) + `replicar` (cria `HoraVenda` INCOMPLETO `origem='TAGPLUS'` + divergência `AGUARDANDO_CHASSI`, sem migration nova) + `descobrir_e_replicar` + cron (`pedido_reverso_worker`); vínculo de chassi reusa a tela de edição existente + badge "TagPlus". **455 testes HORA verdes** (42 novos). Verificações **#1 (write:pedidos)/#2/contrato `/pedidos` resolvidos AO VIVO**; **#1-to_nfe e #3-cancelar-com-NFe** são gate de **ligar a flag** (não de escrever o código). **Pendente (gates do dono):** validar `to_nfe` no go-live + ligar `HORA_TAGPLUS_PUSH_PEDIDO`; agendar cron + ligar `HORA_TAGPLUS_REVERSO`; push. **Handoff:** `docs/superpowers/plans/2026-06-29-hora-tagplus-fase2b-fase3-handoff.md`. Sessão 4-mãos Claude Code (dev).
>
> ⚠️ **Nuance de go-live:** com a flag ON, o push cria o pedido e o `POST /nfes` envia `pedido_os_vinculada` para vincular a NFe a ele (sem auto-criar 2º pedido). Gate: confirmar com o TagPlus que esse vínculo funciona sem duplicar. O faturamento permanece pelo `POST /nfes` rico (decisão do dono — não usar `to_nfe`).

## Indice

- [Contexto](#contexto)
- [Finalidade e objetivo](#finalidade-e-objetivo)
- [Estado atual (com fontes)](#estado-atual-com-fontes)
- [Contrato da API TagPlus /pedidos](#contrato-da-api-tagplus-pedidos)
- [Decisões do usuário](#decisoes-do-usuario)
- [Arquitetura alvo](#arquitetura-alvo)
- [Mudanças no modelo de dados](#mudancas-no-modelo-de-dados)
- [Itens a verificar na API antes de Fase 2/3](#itens-a-verificar-na-api-antes-de-fase-23)
- [Edge cases e riscos](#edge-cases-e-riscos)
- [Estratégia de teste](#estrategia-de-teste)
- [Critérios de aceite (finalidade atingida)](#criterios-de-aceite-finalidade-atingida)
- [Faseamento](#faseamento)
- [Fora de escopo (YAGNI)](#fora-de-escopo-yagni)

---

## Contexto

O módulo HORA (Lojas Motochefe, B2C) cria pedidos de venda 100% localmente e usa o TagPlus apenas para emitir a NFe. O "pedido" que existe no TagPlus hoje é um subproduto auto-criado pelo TagPlus na confirmação da NFe — o sistema nunca cria nem cancela pedido lá. O dono do módulo quer tornar os usuários mais independentes do TagPlus **aumentando** a sincronização: numeração batida, criação/cancelamento espelhados e replicação dos pedidos que nasçam direto no TagPlus. Esta spec consolida a investigação do estado atual, o contrato da API `/pedidos` (confirmado pelo dono), as decisões de escopo e a arquitetura alvo, para uma sessão de implementação começar daqui sem re-descobrir.

## Finalidade e objetivo

**Finalidade (o porquê):** tornar os usuários das Lojas HORA **mais independentes do TagPlus** — operar o dia a dia inteiro dentro do sistema de frete (HORA), sem precisar abrir o TagPlus — **mantendo/aumentando a sincronização** das informações entre os dois sistemas. O HORA passa a ser o **painel único** do pedido de venda; o TagPlus continua sendo o emissor fiscal, mas deixa de ser um lugar que o usuário precisa visitar para criar pedido, conferir número ou cancelar.

**Pedido literal do dono (rastreabilidade):** (1) numeração sincronizada criando o pedido no TagPlus ao criar no sistema e cancelando ao cancelar; (2) corrigir a numeração inconsistente (a coletada parece ser o ID, não o número que o usuário vê); (3) replicar para o sistema pedidos criados direto no TagPlus.

**O que muda para o usuário (independência, na prática):**
- Cria/cancela o pedido **só no HORA** → o TagPlus reflete automaticamente (não precisa recriar lá).
- Vê no HORA o **mesmo número** que apareceria no TagPlus (fim da confusão ID × número).
- Pedido que escapar e nascer direto no TagPlus **volta** para o HORA → nada fica "preso" só no TagPlus.

**Como cada frente serve à finalidade:**

| Frente pedida | Serve à independência porque… | Serve à sincronização porque… |
|---|---|---|
| 1. Criar/cancelar pedido no TagPlus a partir do HORA | o usuário não precisa abrir o TagPlus para ter/baixar o pedido lá | o ciclo de vida (criar/confirmar/cancelar) fica espelhado nos dois lados |
| 2. Número visível correto no HORA | consulta o número sem ir ao TagPlus | o número exibido no HORA = número do TagPlus |
| 3. Replicar pedido nascido no TagPlus | nada exige operar no TagPlus; o que vaza converge para o HORA | os dois lados convergem para o mesmo conjunto de pedidos |

**Tensão reconciliada (por que bidirecional, se o objetivo é independência):** sincronizar dois lados parece *aumentar* o acoplamento. A resolução: o HORA é o **master**; o sentido reverso (item 3) **não** existe para incentivar criar no TagPlus — é uma **rede de convergência** para que, mesmo quando um pedido nasce lá, ele seja puxado para o HORA e o usuário continue operando só no HORA. A bidirecionalidade existe para **reduzir** a dependência operacional do TagPlus, não para mantê-la.

## Estado atual (com fontes)

- O HORA **já é o dono da venda**: `criar_venda_manual` cria a `HoraVenda` localmente (valida CPF/itens, `SELECT FOR UPDATE` no chassi, evento `RESERVADA`), **sem** chamada ao TagPlus (`app/hora/services/venda_service.py:761-872`).
- O TagPlus é chamado **apenas para emitir a NFe** (`POST /nfes`) — `app/hora/services/tagplus/emissor_nfe.py:214`.
- O "pedido" no TagPlus **não é criado pelo sistema**: é auto-criado pelo TagPlus quando a NFe é confirmada (`pedido_os_vinculada`); o HORA só o lê depois (`app/hora/services/tagplus/webhook_handler.py:157-164`; comentário em `app/hora/models/venda.py:197-200`). Não existe `POST /pedidos` no código.
- `cancelar_venda` **não envia nada ao TagPlus** — só muda status local e devolve estoque (`venda_service.py:2083-2163`). Cancelar a NFe (`PATCH /nfes/cancelar`) é operação separada e também não toca o pedido (`cancelador_nfe.py:87-204`).
- **Numeração:** `HoraVenda.tagplus_pedido_id` guarda o **ID interno** (`pedido['id']`), não o número visível. O número visível existe na API (`pedido['numero']`) e já está salvo cru no JSONB `tagplus_pedido_payload`, mas **nunca é extraído nem exibido** (`pedido_backfill_service.py:155-158`, `pedido_service.py:52-54`). A tela mostra `#{tagplus_pedido_id}` rotulado "Pedido TP" (`app/templates/hora/vendas_lista.html:126-128`). **Raiz da inconsistência relatada.**
- O HORA **não tem número de pedido próprio**: usa o `id` PK como identificador visível ("Pedido de Venda #id").
- **Webhooks:** o HORA processa só eventos de NFe (`nfe_aprovada`, `nfe_denegada`, `nfe_cancelada`) — `webhook_handler.py:38-40`. Não há handler nem polling de pedido.
- Existe leitura `GET /pedidos/{id}` (`pedido_service.importar_pedido`) e backfill que **enriquece venda existente** (vendedor, departamento→loja, forma de pagamento) — `pedido_backfill_service._aplicar_pedido_em_venda:113-207`. Não cria venda nem extrai chassi.
- **Problema do chassi:** o pedido TagPlus identifica item por **modelo** (fungível); o HORA exige **chassi** (moto física, chave universal) com lock pessimista. Não há mapeamento automático modelo→chassi físico.

## Contrato da API TagPlus /pedidos

Confirmado pelo dono do módulo a partir do portal (apidoc.tagplus.com.br — "Pedidos/Orçamentos"). A doc local `app/integracoes/tagplus/DOCUMENTACAO_API_TAGPLUS.md` cobria só `/nfes`; este é o contrato novo:

| Verbo | Path | Uso |
|---|---|---|
| GET | `/pedidos` | Lista pedidos. Header `X-Data-Filter` (ex.: `data_criacao`/`data_alteracao`) sobrescreve o campo de data dos filtros `since`/`until`. |
| POST | `/pedidos` | Cria pedido (201). Corpo pode ser vazio. Header `X-Criar-Financeiro` (lança financeiro ao confirmar). |
| GET | `/pedidos/{id}` | Recupera pedido detalhado. |
| PATCH | `/pedidos/{id}` | Atualiza campos (inclui `status`). |
| DELETE | `/pedidos/{id}` | Apaga pedido. Header `X-Apagar-Financeiro` (estorna o financeiro vinculado). |
| GET | `/pedidos/to_nfe/{id}` | **Gera uma NF-e a partir do Pedido/Orçamento.** A NFe resultante traz `pedido_os_vinculada: {id, numero, tipo}`. |
| GET | `/pedidos/to_venda_simples/{id}` | Gera uma venda simples a partir do pedido (não usado). |

**Campos do objeto pedido (POST/PATCH/GET):**
- `id` (int) — ID interno.
- `numero` (int) — **"Número/código do pedido. Gerado automaticamente."** É o número visível; volta na resposta do POST (201).
- `codigo_externo` (string ≤50) — **"Código identificador em aplicações externas."** → usado como elo com `HoraVenda.id`.
- `status` (enum) — `A`=Em aberto · `B`=Confirmado · `C`=Cancelado. Default `A`.
- `departamento` (int), `vendedor` (int), `cliente` (int), `itens[]`, `faturas[]`, valores (`valor_frete`/`valor_desconto`/`valor_acrescimo`/`valor_troco`), `observacoes` (texto livre), `integracao` (string — nome do parceiro de integração), `possui_vinculo` (bool), datas (`data_criacao`/`data_entrega`/`data_confirmacao` + horas).

**Importante:** a NFe (`pedido_os_vinculada`) carrega `{id, numero, tipo}` — ou seja, o número visível do pedido **já chega no webhook** (`GET /nfes/{id}`), sem chamada extra.

## Decisoes do usuário

| Tema | Decisão |
|---|---|
| **Arquitetura** | **Bidirecional real.** HORA empurra para o TagPlus E descobre pedidos criados direto no TagPlus. |
| **Descoberta reversa** | **Numero-walk +3** (algoritmo do usuário, ver Arquitetura §5): a partir do maior número conhecido, varre +1..+3; achando novos, estende +3 a partir do novo máximo; para após 3 ausências seguidas. |
| **Mapeamento de chassi** | **Operador escolhe o chassi.** Pedido replicado entra em `INCOMPLETO` e o operador vincula a moto física antes de confirmar. |
| **Numeração (item 2)** | **Exibir o número visível do TagPlus** (`pedido['numero']`). |
| **Emissão NFe** | **Manter `POST /nfes` rico** (todas as regras fiscais) e vincular ao pedido via `pedido_os_vinculada` p/ não duplicar. **NÃO** usar `to_nfe` (decisão do dono 2026-06-29 — ver §4). |

## Arquitetura alvo

### §1 Vínculo único e prevenção de loop

- No `POST /pedidos`, gravar `codigo_externo = str(HoraVenda.id)` e `integracao = "SISTEMA_HORA"`.
- Persistir na venda: `tagplus_pedido_id` (id interno, já existe) **e** `tagplus_pedido_numero` (número visível, novo).
- **Anti-loop:** na varredura reversa, todo pedido cujo `codigo_externo` resolve uma `HoraVenda` existente é "nosso" → ignora. Pedido sem `codigo_externo` (ou cujo valor não casa) nasceu no TagPlus → replica. Assim um push nunca volta como replicação.

### §2 Mapeamento de status HORA ↔ TagPlus

| HoraVenda.status | TagPlus `status` | Ação no push |
|---|---|---|
| `INCOMPLETO` / `COTACAO` | `A` (Em aberto) | `POST /pedidos` na criação |
| `CONFIRMADO` | `B` (Confirmado) | `PATCH /pedidos/{id}` status=B |
| `FATURADO` | `B` + NFe via `POST /nfes` com `pedido_os_vinculada` | NFe rica vinculada ao pedido (sem duplicar) |
| `CANCELADO` | `C` (Cancelado) | `PATCH /pedidos/{id}` status=C (DELETE só se nunca houve NFe) |

Reverso (TagPlus→HORA): `A`→`INCOMPLETO` (aguardando chassi), `B`→operador vincula chassi e confirma, `C`→`CANCELADO`.

### §3 Fluxo HORA → TagPlus (push — item 1)

Gancho nos pontos de transição de `venda_service`, **após** o commit local (o pedido TagPlus nunca deve travar a venda local; falha de rede vira pendência reprocessável):

- **Criar** (`criar_venda_manual` / `salvar_pedido_completo`, `venda_service.py:761-872`): `POST /pedidos` com `codigo_externo`, `status='A'`, `integracao='SISTEMA_HORA'`, `departamento`/`vendedor`/`cliente`/`itens`/`faturas` quando resolvíveis → grava `tagplus_pedido_id` + `tagplus_pedido_numero`.
- **Confirmar** (`confirmar_venda`, `venda_service.py:1118`): `PATCH status='B'`.
- **Emitir NFe**: manter `POST /nfes` (payload rico) + `pedido_os_vinculada=tagplus_pedido_id` (ver §4).
- **Cancelar** (`cancelar_venda`, `venda_service.py:2083`): `PATCH status='C'` (respeitando os guards atuais de NFe em-voo/aprovada).

Resiliência: push idempotente por `codigo_externo` e tolerante a falha (registra erro + permite reprocesso; o scheduler reverso reconcilia o que faltar). **Não** abortar a operação local se o TagPlus falhar.

### §4 Fluxo de emissão NFe (POST /nfes + `pedido_os_vinculada`) — REVISADO 2026-06-29

`emissor_nfe.processar` **continua fazendo `POST /nfes`** com o payload rico do `PayloadBuilder.build()`. Para evitar o pedido duplicado que o TagPlus auto-cria, a emissão passa a enviar **`pedido_os_vinculada = tagplus_pedido_id`** no corpo do `POST /nfes` (campo confirmado na doc: *"ID do Pedido vinculado a nota"*) — o TagPlus vincula a NFe ao pedido criado no push em vez de criar outro.

> **Decisão do dono (2026-06-29):** **NÃO** usar `GET /pedidos/to_nfe/{id}`. O `to_nfe` geraria a NFe a partir dos dados do *pedido* (pobres), perdendo todas as regras fiscais que o `PayloadBuilder.build()` aplica hoje (`inf_contribuinte` com Modelo/Cor/Chassi/Motor + garantia CONTRAN, CFOP por UF, `consumidor_final`, peças, cortesia de revisão). O faturamento por `POST /nfes` é o caminho rico e específico do sistema; só o **vínculo** muda.
>
> **Gate de go-live (não-validável sem emitir NF):** confirmar que `pedido_os_vinculada` vincula **sem** auto-criar outro pedido. No pior caso a NFe sai correta de qualquer forma — restaria só a duplicação a reconciliar.

### §5 Fluxo TagPlus → HORA (replicação reversa — item 3)

**Descoberta (numero-walk +3, scheduler):**
```
base = max(maior tagplus_pedido_numero conhecido no sistema,
           ultimo_pedido_numero_reconciliado da conta)
cursor = base; ausencias = 0
enquanto ausencias < 3:
    cursor += 1
    pedido = busca_pedido_por_numero(cursor)        # GET /pedidos?numero=cursor (verificar parâmetro)
    se pedido existe:
        ausencias = 0
        se codigo_externo NAO resolve HoraVenda existente:
            replicar(pedido)                         # cria HoraVenda INCOMPLETO
        # se resolve, é nosso -> ignora (anti-loop)
    senao:
        ausencias += 1
persistir ultimo_pedido_numero_reconciliado
```
Exemplo do usuário: sistema até 940 → varre 941,942,943; achou 941 e 942 → estende para 944,945 (= max conhecido +3); para após 3 ausências seguidas.

**Replicação (`pedido` → `HoraVenda`):**
- Cria `HoraVenda` com `origem_criacao='TAGPLUS'` (novo valor), `status='INCOMPLETO'`, `tagplus_pedido_id`/`tagplus_pedido_numero` preenchidos, cliente/CPF/loja resolvidos (loja via `departamento` → `HoraTagPlusDepartamentoMap`, mecanismo já existente em `pedido_service.py:99-111`).
- Itens replicados **por modelo** (sem chassi) — registra pendência/divergência "aguardando vínculo de chassi".
- **Operador vincula o chassi** na UI: ao vincular, dispara reserva (`SELECT FOR UPDATE` + evento `RESERVADA`) e a venda segue o fluxo normal.

### §6 Numeração (item 2)

- Capturar `pedido['numero']` (ou `pedido_os_vinculada['numero']` no webhook) em **três pontos**: webhook `nfe_aprovada` (`webhook_handler.py:160-164`), backfill de enriquecimento (`pedido_backfill_service.py:155-158`), e POST do push.
- Backfill histórico: popular `tagplus_pedido_numero` a partir do JSONB `tagplus_pedido_payload['numero']` já salvo (sem re-chamar a API para a maioria das vendas).
- Exibir `tagplus_pedido_numero` na coluna "Pedido TP" (fallback para `—` quando ausente).

## Mudanças no modelo de dados

| Fase | Mudança | Migration |
|---|---|---|
| 1 | `hora_venda.tagplus_pedido_numero INTEGER NULL` + index `ix_hora_venda_tagplus_pedido_numero` | `hora_62_venda_tagplus_pedido_numero.{sql,py}` |
| 2 | `origem_criacao` aceita `'TAGPLUS'` (sem DDL — `VARCHAR(20)` já existe). Opcional: `hora_tagplus_nfe_emissao.tagplus_pedido_numero` para paridade. | (sem DDL nova) |
| 3 | `hora_tagplus_conta.ultimo_pedido_numero_reconciliado INTEGER NULL` (cursor do numero-walk) | `hora_63_tagplus_conta_cursor_reconciliacao.{sql,py}` |

Após cada migration que altera `hora_venda`, **regenerar** `.claude/skills/consultando-sql/schemas/tables/hora_venda.json` (schema auto-gerado é fonte de verdade dos campos — regra CLAUDE.md).

## Itens a verificar na API antes de Fase 2/3

(TagPlus **não tem ambiente de homologação** — escrita é produção; `models/tagplus.py:47-49`. Verificar com leitura/dry-run.)

1. ⛔ **PENDENTE — `pedido_os_vinculada` no `POST /nfes` vincula a NFe ao pedido SEM auto-criar outro?** **Não testável sem emitir NF real** (sem homologação) — confirmar com TagPlus ou go-live controlado. **Gate de LIGAR a flag.** (O `to_nfe` foi **descartado** — decisão do dono 2026-06-29, ver §4: preserva as regras fiscais do `POST /nfes`. No pior caso a NFe sai correta de qualquer forma.)
2. ✅ **RESOLVIDO (2026-06-29):** `GET /pedidos?numero={n}` filtra por número **exato** (200 + 1 item; testado ao vivo com numero=942). `numero[eq]`→422; `q`→busca fuzzy. É o parâmetro de `busca_pedido_por_numero` (numero-walk, Fase 3 — implementado).
3. 🟡 **PARCIAL (2026-06-29):** `DELETE /pedidos/{id}` funciona em pedido **sem NFe** (comprovado ao vivo: criou+apagou pedido de teste, `{"message":"Deletado com sucesso"}`). Comportamento **com NFe vinculada** ainda não testado (precisa de NF emitida). **Default adotado:** `PATCH status=C` (preserva registro). **Gate do cancelamento com-NFe.**
4. ✅ **RESOLVIDO AO VIVO (2026-06-29):** `write:pedidos` **JÁ está efetivo** no token de PROD — `POST /pedidos` retornou **201** (pedido 1220/nº966, criado e deletado no teste controlado). O `scope_efetivo=null` no banco é **falso-negativo** (o TagPlus não devolve `scope` no refresh response, então o campo nunca foi populado), **não** prova de escopo ausente. **NÃO é preciso reautorizar OAuth.**

**Contrato `POST /pedidos` confirmado ao vivo (2026-06-29, testes controlados cria+apaga):**
- `itens[]` usa **`produto_servico`** (igual `/nfes`); `produto` → 422 "Campo adicional não permitido".
- `cliente` = **id_cliente** (id-space REST), **não** `id_entidade` (que é o do `destinatario` do `/nfes`).
- `departamento`/`vendedor` = `int` (id), **opcionais** (omitidos no v1 — HORA não tem mapa loja→departamento_id; rastreio fiscal já vai no `inf_contribuinte`).
- `faturas[]` = `forma_pagamento`+`parcelas` (igual `/nfes`). → permite **reusar `PayloadBuilder._montar_itens`/`_montar_faturas`**.

## Edge cases e riscos

- **Duplicidade de pedido** se emitir `POST /nfes` com pedido já criado → mitigado por `pedido_os_vinculada` no corpo do `POST /nfes` (§4); confirmar o vínculo com o TagPlus no go-live.
- **Falha de push não pode travar a venda local** — push pós-commit, tolerante a falha, reconciliado pelo scheduler.
- **Numero-walk e gaps reais:** o `numero` é por conta e pode ter saltos legítimos (outros canais). Parar após 3 ausências pode perder pedidos além do gap; mitigação futura: varredura por data como rede de segurança (não nesta versão — decisão foi numero-walk).
- **Chassi fungível:** nunca auto-vincular; sempre operador (evita furar lock pessimista e a máquina de estados).
- **`tagplus_pedido_id` não é UNIQUE** (`hora_venda.json:292-298`): a replicação deve checar duplicidade por `codigo_externo`/`tagplus_pedido_id`/`tagplus_pedido_numero` antes de criar.
- **Idempotência do scheduler:** rodar 2x não pode duplicar venda → checar identificadores antes de inserir.

## Estratégia de teste

- **TDD** em todas as fases (`pytest`, `tests/hora/`).
- Fase 1: captura de `numero` no webhook (de `pedido_os_vinculada.numero`), no backfill (de `pedido['numero']`), e backfill histórico do JSONB; render da coluna.
- Fase 2: push (POST/PATCH/DELETE) com `requests` mockado; mapeamento de status; emissão `to_nfe` (após verificação); guards de cancelamento preservados.
- Fase 3: algoritmo numero-walk (com gaps), anti-loop por `codigo_externo`, replicação→`INCOMPLETO`, idempotência, vínculo de chassi pelo operador (reserva + evento).
- Mock do TagPlus: nunca bater na API real em teste; usar fixtures do contrato acima.

## Critérios de aceite (finalidade atingida)

A finalidade está atingida quando, em produção:

1. **Independência:** o usuário cria, confirma e cancela um pedido de venda **inteiro no HORA**, sem abrir o TagPlus, e o pedido correspondente no TagPlus reflete o mesmo estado (`A`/`B`/`C`).
2. **Número batendo:** a listagem/detalhe do HORA exibe o **número visível** do pedido TagPlus (`pedido['numero']`), idêntico ao que aparece no TagPlus — não o ID interno.
3. **Sem duplicidade:** emitir a NFe de um pedido criado pelo HORA **não** gera um segundo pedido no TagPlus (via `to_nfe`).
4. **Convergência:** um pedido criado direto no TagPlus aparece no HORA (em `INCOMPLETO`, aguardando vínculo de chassi) dentro de um ciclo do scheduler, sem duplicar vendas existentes.
5. **Não-regressão:** nenhuma quebra no fluxo fiscal atual (emissão/cancelamento de NFe) nem na máquina de estados/estoque por chassi.

Mapeamento por fase: a **Fase 1** satisfaz (2); a **Fase 2** satisfaz (1) e (3); a **Fase 3** satisfaz (4); (5) é transversal a todas.

## Faseamento

1. **Fase 1 — Numeração (item 2).** ✅ Implementada + PROD (migration/backfill). Plano: `docs/superpowers/plans/2026-06-29-hora-tagplus-sync-fase1-numeracao.md`.
2. **Fase 2 — Push HORA→TagPlus (item 1).**
   - **2a (parte segura)** ✅ — `pedido_sync_service` (criar/atualizar/cancelar pedido) atrás da flag `HORA_TAGPLUS_PUSH_PEDIDO` (OFF), dry-run, sem caminho fiscal nem wiring. `app/hora/services/tagplus/pedido_sync_service.py`.
   - **2b (gated)** — itens/cliente/faturas no payload + emissão via `to_nfe` (verificação #1) + cancelamento PATCH/DELETE (#3) + wiring em `venda_service` (criar/confirmar/cancelar) + ligar a flag. **Pré-requisito:** reauth OAuth com `write:pedidos` (#4).
3. **Fase 3 — Reverso (item 3).** Verificação #2 ✅ (`?numero=`). Scheduler numero-walk + replicação + UI de vínculo de chassi.

Plano task-by-task da Fase 2b e da Fase 3 é escrito quando #1/#3 forem confirmados com o TagPlus e o OAuth for reautorizado.

## Fora de escopo (YAGNI)

- Webhook de pedido do TagPlus (usaremos numero-walk por decisão do usuário).
- Sincronização de edições campo-a-campo do pedido (só status + criação + cancelamento).
- Matching automático de chassi (operador escolhe — decisão).
- Numeração própria sequencial do HORA (decisão foi exibir o número do TagPlus).
- Multi-emitente / séries por loja (regra fiscal: emitente sempre matriz — `app/hora/CLAUDE.md` §7).
