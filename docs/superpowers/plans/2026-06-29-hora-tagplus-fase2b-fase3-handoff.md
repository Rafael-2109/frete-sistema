<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-29
-->
# HORA ↔ TagPlus — Handoff Fase 2b + Fase 3 (próxima sessão)

> **Papel:** guia de retomada para uma sessão limpa continuar a sincronização bidirecional de pedidos HORA↔TagPlus. Fases 1 e 2a já estão na `main` (deployadas/flag-OFF). Aqui ficam o estado, os pré-requisitos a confirmar e o roteiro das Fases 2b e 3.

> **Spec (SOT do design):** `docs/superpowers/specs/2026-06-29-hora-tagplus-sync-bidirecional-design.md`.

## Progresso (2026-06-29 — sessão de execução; GO-LIVE EXECUTADO, flags ON em PROD)

**Pré-requisitos confirmados AO VIVO (testes controlados cria+apaga, zero resíduo):**
- **#1 `write:pedidos` → ✅ JÁ EFETIVO** (POST /pedidos = 201, pedido 1220/nº966 criado e deletado). `scope_efetivo=null` é falso-negativo (TagPlus não devolve scope no refresh). **NÃO precisa reauth OAuth.**
- **Contrato `POST /pedidos` mapeado:** `itens[].produto_servico` (= /nfes), `cliente`=id_cliente (≠ id_entidade), `departamento`/`vendedor` int opcionais.
- **#2 `?numero=` ✅** (já era). **#3 `DELETE` sem-NFe ✅** comprovado; com-NFe pendente. **#1 `pedido_os_vinculada` no `POST /nfes` vincula sem duplicar? ⛔** não testável sem emitir NF (gate de LIGAR a flag, não de codar). `to_nfe` descartado.

**Fase 2b — IMPLEMENTADA (flag OFF, 23 testes em `tests/hora/test_pedido_sync_fase2b.py`):**
- `PayloadBuilder.resolver_id_cliente` + `montar_corpo_pedido(estrito)` + `_ultimo_id_cliente` (reusa `_montar_itens`/`_montar_faturas`).
- `pedido_sync_service`: `montar_payload_pedido(builder=)`, `criar_pedido(builder=)`, helpers `push_criar_pedido`/`push_atualizar_status`/`push_cancelar` (pós-commit, tolerantes, idempotentes).
- `venda_service`: 4 wirings (`criar_venda_manual`, `salvar_pedido_completo`, `confirmar_venda`, `cancelar_venda`).
- `emissor_nfe._enviar_nfe`: **SEMPRE `POST /nfes` rico** + `pedido_os_vinculada=tagplus_pedido_id` quando flag ON (vincula a NFe ao pedido do push sem duplicar). **`to_nfe` DESCARTADO** (decisão do dono 2026-06-29 — preserva as regras fiscais do `PayloadBuilder`; ver §4 da spec).

**Fase 3 — COMPLETA (15 testes em `tests/hora/test_pedido_sync_fase3.py`):**
- Migration `hora_63` (cursor `ultimo_pedido_numero_reconciliado`) — **aplicada LOCAL e em PROD ✅.**
- `pedido_service.busca_pedido_por_numero`; `pedido_reverso_service`: `_maior_numero_conhecido`, `pedido_e_nosso` (anti-loop+idempotência), `_varrer` (numero-walk +3), `numero_walk` (persiste cursor), `_resolver_loja_id`, `replicar` (cria `HoraVenda` INCOMPLETO `origem_criacao='TAGPLUS'` + `HoraVendaDivergencia` `AGUARDANDO_CHASSI` por item — **sem migration nova**: usa `detalhe`/`valor_esperado`/`numero_chassi`-NULL), `descobrir_e_replicar` (orquestra, tolerante por pedido), `reverso_habilitado` (flag `HORA_TAGPLUS_REVERSO`, default OFF).
- `pedido_reverso_worker.descobrir_e_replicar_job` (entry point do cron, gated pela flag).
- **UI:** vínculo de chassi **reusa a tela de edição de pedido INCOMPLETO** (`pedido_venda_novo.html`, que já exibe a divergência `AGUARDANDO_CHASSI`); badge "TagPlus" na listagem (`vendas_lista.html`).

**GO-LIVE EXECUTADO (2026-06-29 ~23:55):** deploy `4c8943800` LIVE (web+worker). Flags LIGADAS em PROD (confirmado via API): **web** `HORA_TAGPLUS_PUSH_PEDIDO=1`+`HORA_TAGPLUS_REVERSO=1`; **worker** (`...worker-atacadao`, queue `hora_nfe`) `HORA_TAGPLUS_PUSH_PEDIDO=1`. Job `HORA TagPlus reverso` registrado no scheduler. Pré-requisito do reverso resolvido antes: backfills (pedidos legados + NF) capturaram o vínculo até nº 965 → **dry-run do numero-walk = 0** (não duplica).

**MONITORAR (validação ao vivo — pendente):**
1. **1º ciclo do reverso** (~30min após o boot): `hora_venda` `origem_criacao='TAGPLUS'` deve seguir baixo/zero e o cursor (`ultimo_pedido_numero_reconciliado`) avançar p/ 965.
2. **Push**: 1ª venda nova ganha `tagplus_pedido_id`; confirmar/cancelar espelham status no TagPlus.
3. **Gate #1 ao vivo (crítico)**: 1ª emissão de NFe com push ON → conferir no TagPlus que `pedido_os_vinculada` **vinculou sem criar 2º pedido**. Se duplicar, a NFe sai correta mesmo assim — só reconciliar.

**Pendência separada (numeração / Fase 1):** captura do `tagplus_pedido_numero` via webhook tinha parado (8 faturadas órfãs); resolvida pelos backfills nesta sessão, mas vale checar por que o webhook `nfe_aprovada` não capturou — pode repetir.

**Melhorias futuras:** label amigável p/ `AGUARDANDO_CHASSI`, UNIQUE em `tagplus_pedido_id` (após limpar 3 dups legadas), reconciliador por `codigo_externo`.

**Review adversarial 2026-06-29 — fixes aplicados (com testes):**
- *Fase 2b:* `push_criar_pedido` no-op para FATURADO/CANCELADO; `resolver_id_cliente` trata CPF ambíguo; warning em `POST /pedidos` 2xx sem id. (Os fixes do caminho `to_nfe` — PATCH validado, cliente estrito — foram **removidos junto com o `to_nfe`** na revisão para `pedido_os_vinculada`.)
- *Fase 3:* cursor avança só até o último pedido replicado OK (falha em `replicar(N)` → cursor em `N-1`, re-tenta); `busca_pedido_por_numero` levanta em 401/403/5xx → `descobrir_e_replicar` aborta sem avançar cursor; lock Redis no worker (anti-concorrência); CPF inválido → placeholder; gate de flag no service; doc `origem_criacao`.

**Riscos residuais conhecidos (v1, caminho flag ON):**
- **`pedido_os_vinculada` vincula sem auto-criar?** Não-validável sem emitir NF (gate #1). A resposta do `POST /nfes` é a mesma de hoje (schema conhecido — polling/webhook inalterados), então **não há** o risco de schema do `to_nfe` (que foi descartado).
- **Não-atomicidade `POST /pedidos` + commit local** (Fase 2b): commit falho logo após POST OK perde o `tagplus_pedido_id`; retry pode duplicar pedido. Mitigação futura: reconciliador por `codigo_externo`.
- **UNIQUE em `hora_venda.tagplus_pedido_id`** não aplicado: PROD tem **3 duplicatas legadas** (ids 185, 477, 571 — vendas FATURADAS). O lock Redis cobre a concorrência do cron; o UNIQUE parcial (migration futura) exige limpar as duplicatas antes.

## Indice

- [Estado atual (o que já está pronto)](#estado-atual-o-que-ja-esta-pronto)
- [Pré-requisitos a confirmar ANTES de codar Fase 2b](#pre-requisitos-a-confirmar-antes-de-codar-fase-2b)
- [Fase 2b — roteiro](#fase-2b-roteiro)
- [Fase 3 — roteiro (numero-walk)](#fase-3-roteiro-numero-walk)
- [Arquivos-chave](#arquivos-chave)
- [Comandos úteis](#comandos-uteis)

## Estado atual (o que já está pronto)

- **Fase 1 (numeração, item 2) — FEITA e em PROD.** Coluna `hora_venda.tagplus_pedido_numero` (migration `hora_62`); captura no webhook `nfe_aprovada` + backfill enriquecimento + `backfill_numero_do_payload()`; listagem exibe "Pedido TP (nº)". **Migration + backfill de 885 vendas já aplicados no banco de PROD** (0 divergências). Código deployado (commit `5027048c7`).
- **Fase 2a (push, parte segura) — FEITA, flag-OFF.** `app/hora/services/tagplus/pedido_sync_service.py`: `mapear_status` (A/B/C), `montar_payload_pedido` (identidade: `codigo_externo=venda.id`, `integracao=SISTEMA_HORA`, status), `criar_pedido`/`atualizar_status_pedido`/`cancelar_pedido` com **dry-run + flag `HORA_TAGPLUS_PUSH_PEDIDO` (default OFF)**. Sem caminho fiscal nem wiring. 9 testes (`tests/hora/test_pedido_sync_service.py`).
- **Scope default do modelo** já inclui `write:pedidos`.
- **Verificações de API:**
  - **#2 ✅** `GET /pedidos?numero={n}` filtra exato (testado ao vivo).
  - **#4 ✅** o token de PROD precisava de `write:pedidos` — `scope_contratado` já atualizado pelo dono.
  - **#1 ⛔ pendente** (`to_nfe` transmite à SEFAZ?) · **#3 ⛔ pendente** (cancelar pedido com NFe: PATCH×DELETE).

## Pré-requisitos a confirmar ANTES de codar Fase 2b

1. **`write:pedidos` realmente concedido ao token.** O DB mostra `scope_contratado` com `write:pedidos`, mas `scope_efetivo` é nulo e o token aparece como **refresh** (`obtido_em` antigo). Refresh **não** concede escopo novo. **Confirmar** fazendo uma chamada controlada `POST /pedidos` (corpo mínimo: `{codigo_externo, status:'A', integracao}`) — se 201, ok; se 401, refazer o **authorize** OAuth (não só refresh) em `/hora/tagplus/conta/oauth`. Apagar o pedido de teste (`DELETE /pedidos/{id}`) se criado.
2. **`GET /pedidos/to_nfe/{id}` transmite à SEFAZ ou gera rascunho?** Aceita `X-Enviar-Nota`/`X-Calculo-Trib-Automatico`? (perguntar ao TagPlus ou teste controlado com 1 pedido real). Decide o desenho da emissão na Fase 2b.
3. **Cancelar pedido com NFe emitida:** `PATCH status=C` (default adotado) vs `DELETE` + `X-Apagar-Financeiro` — comportamento quando há NFe vinculada.

## Fase 2b — roteiro

> **NOTA (2026-06-29):** roteiro ORIGINAL (histórico). O item 2 (emissão) foi **revisado**: NÃO usa `to_nfe`; usa `POST /nfes` rico + `pedido_os_vinculada` (decisão do dono — preserva as regras fiscais). Ver a seção **Progresso** acima e o §4 da spec. O restante foi implementado conforme abaixo.

Objetivo: tornar o push REAL e ligado ao ciclo da venda, sem duplicar pedido no TagPlus. Toca o caminho fiscal → **TDD + dry-run + revisão**.

1. **Payload completo** em `pedido_sync_service.montar_payload_pedido`: incluir `cliente` (resolver/criar via lógica já existente do `PayloadBuilder`), `departamento` (loja), `vendedor`, `itens[]` (reusar `HoraTagPlusProdutoMap` p/ produto; qtd/valores) e `faturas[]` (forma de pagamento via `HoraTagPlusFormaPagamentoMap`). Hoje só monta identidade+status.
2. **Emissão via `to_nfe`** (após confirmar #1): trocar/condicionar `emissor_nfe.processar` para, quando houver `tagplus_pedido_id`, emitir por `GET /pedidos/to_nfe/{id}` em vez de `POST /nfes` — evita o pedido auto-criado duplicado. Preservar todo o fluxo de webhook/polling/status.
3. **Cancelamento** (após #3): `cancelar_pedido` no `cancelar_venda`, respeitando os guards de NFe em-voo/aprovada já existentes.
4. **Wiring no `venda_service`** (pós-commit, tolerante a falha — não travar a venda local):
   - `criar_venda_manual`/`salvar_pedido_completo` → `criar_pedido` → gravar `tagplus_pedido_id` + `tagplus_pedido_numero`.
   - `confirmar_venda` → `atualizar_status_pedido(..., 'B')`.
   - `cancelar_venda` → `cancelar_pedido`.
5. **Ligar a flag** `HORA_TAGPLUS_PUSH_PEDIDO=1` no Render (env var) só após shadow/dry-run validado.
6. **Anti-loop:** garantir `codigo_externo=venda.id` em todo POST (já no `montar_payload_pedido`).

## Fase 3 — roteiro (numero-walk)

Verificação #2 já confirmada (`?numero=`). Objetivo: descobrir pedidos criados direto no TagPlus e replicar.

1. **Migration `hora_63`**: `hora_tagplus_conta.ultimo_pedido_numero_reconciliado INTEGER NULL` (cursor).
2. **`busca_pedido_por_numero(api, n)`**: `GET /pedidos?numero=n` → 1º item ou None.
3. **Scheduler numero-walk +3** (algoritmo do dono): `base = max(maior tagplus_pedido_numero conhecido, ultimo_reconciliado)`; varre +1..+3; estende +3 ao achar; para após 3 ausências; persiste o cursor. **Anti-loop:** pedido cujo `codigo_externo` resolve uma `HoraVenda` existente = ignora.
4. **Replicação → `HoraVenda`** `origem_criacao='TAGPLUS'`, `status='INCOMPLETO'`, itens por **modelo** (sem chassi) + divergência "aguardando chassi"; loja via `HoraTagPlusDepartamentoMap`. Idempotente (checar `tagplus_pedido_id`/`numero` antes de inserir).
5. **UI de vínculo de chassi** pelo operador → dispara reserva (`SELECT FOR UPDATE` + evento `RESERVADA`) e segue o fluxo normal.
6. **Cron**: reusar padrão do `reconciliacao_worker` (cron 30min) / `worker_hora_nfe`.

## Arquivos-chave

- `app/hora/services/tagplus/pedido_sync_service.py` — push (Fase 2a; estender na 2b).
- `app/hora/services/tagplus/emissor_nfe.py` — `_enviar_nfe`: `POST /nfes` + `pedido_os_vinculada` (NÃO `to_nfe`).
- `app/hora/services/tagplus/payload_builder.py` — reuso de cliente/itens/forma.
- `app/hora/services/tagplus/pedido_service.py` — `GET /pedidos/{id}` + extratores (reuso na replicação).
- `app/hora/services/venda_service.py` — `criar_venda_manual:761`, `confirmar_venda:1118`, `cancelar_venda:2083` (pontos de wiring).
- `app/hora/services/tagplus/webhook_handler.py` — captura de número (Fase 1).
- `app/hora/workers/reconciliacao_worker.py` — padrão de cron p/ Fase 3.
- `app/hora/models/tagplus.py` — `HoraTagPlusConta` (cursor na 2c), `HoraTagPlusDepartamentoMap`, `HoraTagPlusProdutoMap`.

## Comandos úteis

```bash
# Testes
.venv/bin/python -m pytest tests/hora/ -q

# Migration em PROD (padrão do projeto)
DBP="$(grep -E '^DATABASE_URL_PROD=' .env | head -1 | cut -d= -f2-)"
DATABASE_URL="$DBP" .venv/bin/python scripts/migrations/hora_63_*.py

# Verificar dados de PROD: Render MCP query_render_postgres (postgresId dpg-d13m38vfte5s738t6p50-a)
```

> **Git:** trabalhar em `main` (commits locais; push só com aval do dono — dispara deploy no Render). Nunca `[skip render]`.
