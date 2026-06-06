<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-06
-->
# TagPlus → WhatsApp: notificação de Pedido criado e NF emitida (réplica do fluxo N8N)

> **Papel:** spec de design da feature que replica, dentro do sistema, o fluxo N8N atual em que **todo pedido criado e toda NF emitida no TagPlus** dispara uma mensagem em um **grupo único de vendas** no WhatsApp. A NF vai com o **PDF da DANFE anexado**. Reusa a infra de webhook TagPlus (recepção) e o gateway OpenClaw (envio) já existentes no projeto.

## Indice

- [Contexto](#contexto)
- [Objetivo e não-objetivos](#objetivo-e-não-objetivos)
- [Decisões aprovadas (Q&A)](#decisões-aprovadas-qa)
- [Estado atual (fatos com fonte)](#estado-atual-fatos-com-fonte)
- [Arquitetura](#arquitetura)
- [Fluxo de dados](#fluxo-de-dados)
- [Componentes (arquivos a criar/modificar)](#componentes-arquivos-a-criarmodificar)
- [Modelo de dados](#modelo-de-dados)
- [Formato das mensagens](#formato-das-mensagens)
- [Envio do anexo PDF](#envio-do-anexo-pdf)
- [Configuração (env vars)](#configuração-env-vars)
- [Pré-requisitos que dependem do usuário](#pré-requisitos-que-dependem-do-usuário)
- [Segurança](#segurança)
- [Idempotência e robustez](#idempotência-e-robustez)
- [Erros e edge cases](#erros-e-edge-cases)
- [Testes](#testes)
- [Riscos e mitigação](#riscos-e-mitigação)
- [Assunções a confirmar](#assunções-a-confirmar)

## Contexto

Hoje um workflow no **N8N** escuta os webhooks do TagPlus e, a cada **pedido criado** e **NF emitida**, posta uma mensagem para o vendedor em um grupo de WhatsApp. O usuário quer **migrar esse comportamento para dentro do sistema**, eliminando a dependência do N8N. Não há acesso ao JSON/lógica interna do N8N — o desenho é feito do zero, fiel ao comportamento observado.

A boa notícia: **as duas pontas já existem no projeto** e serão reusadas:
- **Recepção** — webhooks TagPlus já chegam ao sistema (`app/integracoes/tagplus/webhook_routes.py`), com validação de assinatura e o padrão "webhook traz só o ID → buscar detalhes via API".
- **Envio** — `app/utils/whatsapp_notify.py:send_whatsapp()` envia texto para DM ou grupo via gateway OpenClaw (loopback/túnel), com rate-limit anti-ban e kill switch.

## Objetivo e não-objetivos

**Objetivo:** ao receber `pedido_criado` e `nfe_criada` do TagPlus, enviar uma mensagem formatada ao **grupo único de vendas** no WhatsApp; na NF, anexar o **PDF da DANFE**.

**Não-objetivos (v1):**
- Roteamento por vendedor / múltiplos grupos (decisão: **grupo único**).
- Notificar alteração/cancelamento (`nfe_alterada`, `nfe_apagada`, etc.) — só **criação**. (Gancho fica preparado, mas fora do escopo v1.)
- Tocar no fluxo de importação de faturamento (`/webhook/tagplus/nfe`), que está **ativo** e permanece intacto.
- Anexar PDF de pedido (pedido não é documento fiscal, não tem DANFE).

## Decisões aprovadas (Q&A)

1. **Fonte N8N:** indisponível → desenho do zero.
2. **Destino:** **grupo único** de vendas (sem mapa por vendedor).
3. **Escopo de eventos:** **pedido + NF** (ambos criação).
4. **Formato da mensagem:** **completo, com itens**; **NF com PDF anexado**.
5. **Import de faturamento existente:** **ativa** → não mexer; notificação 100% isolada.
6. **Acoplamento:** **webhook novo dedicado** (URL própria), separado do `/webhook/tagplus/nfe`.
7. **Processamento:** **thread `daemon=False`** (espelha o WhatsApp bot), não RQ.
8. **Tela de histórico/reenvio:** incluída no MVP.

## Estado atual (fatos com fonte)

- **Estrutura do webhook TagPlus** (`scripts/webhook.md:37-47`): `{ "id", "sistema", "uid", "event_type", "data": [ { "id": "1" } ] }`. O `id` do registro vem **como string** dentro de `data[]`. Header de segurança **`X-Hub-Secret`**.
- **Evento de pedido** confirmado: `pedido_criado` (`scripts/webhook.md:30`). Eventos de NF usados pela integração: `nfe_criada`/`nfe_alterada` (`webhook_routes.py:146`).
- **Webhook dispara antes do dado existir na API** → a integração já trata com retry/delay `[1,3,5]s` (`webhook_routes.py:117-131`). Replicar.
- **`GET /nfes/{id}`** retorna: `numero`, `serie`, `chave_acesso`, `valor_nota`, `data_emissao`, `destinatario{razao_social, cnpj}`, `itens[]` com `produto.codigo`/`produto.descricao`/`qtd`/`valor_unitario`/`valor_subtotal` (`DOCUMENTACAO_API_TAGPLUS.md:79-131`). **Não traz vendedor.**
- **`GET /pedidos/{id}`** retorna: `numero`, `status`, `cliente{razao_social, cpf}`, `vendedor{nome}`, `departamento{descricao}`, `valor_total`, `itens[]`, `observacoes`, `data_entrega` (`app/hora/services/tagplus/pedido_service.py:43-81`). **Exige scope `read:pedidos`; sem ele, 401** (`pedido_service.py:30`).
- **DANFE PDF:** `GET /nfes/pdf/recibo_a4/{id}` retorna o PDF (`app/hora/routes/tagplus_routes.py:1459-1473`).
- **Cliente de API da integração principal:** `TagPlusOAuth2V2(api_type='notas')` (`importador_v2.py:31`). `make_request(method, endpoint)` retorna o `response` **cru** (`oauth2_v2.py:309-340`) → `.json()` para dados, `.content` para o PDF binário. `get_headers()` injeta `Authorization`+`X-Api-Version` com refresh automático (`oauth2_v2.py:294-305`).
- **Scope atual da conta `notas`:** `read:nfes read:clientes read:produtos` (`oauth2_v2.py:45`) — **NÃO inclui `read:pedidos`**. ⚠️ Pré-requisito para pedido.
- **Envio WhatsApp:** `send_whatsapp(target, text, *, skip_rate_limit, timeout)` (`app/utils/whatsapp_notify.py:135`). Hoje envia **só texto**: args `{name:"message", args:{action:"send", channel:"whatsapp", target, message}}` (`whatsapp_notify.py:190-198`). Kill switch `OPENCLAW_NOTIFY_ENABLED`.
- **Anexo no gateway OpenClaw** (schema do tool `message` em `/usr/lib/node_modules/openclaw/dist/openclaw-tools-0ftkmYS3.js`): aceita `media` ("URL or local path; data: URLs not supported here, use buffer"), **`buffer`** ("Base64 payload for attachments, optionally a data: URL"), `filename`, `mimeType`, `contentType`, `caption`. → PDF vai **inline em base64 via `buffer`** (não depende de filesystem/URL pública; funciona com PROD chamando o gateway por túnel).
- **Padrão async validado:** `app/whatsapp/services.py` (R1 thread `daemon=False`; R2 `_commit_with_retry`; R3 re-fetch pós-commit; R5 cleanup `finally`). É o molde do serviço de notificação.
- **Registro de blueprint:** webhooks TagPlus registrados em `app/__init__.py:1300-1304` (sem prefixo, paths absolutos nas rotas).

## Arquitetura

Módulo de notificação **desacoplado** dentro de `app/integracoes/tagplus/`, com webhook próprio. Processamento assíncrono em thread (não bloqueia a resposta ao TagPlus; não cria fila RQ nova).

```
TagPlus (nfe_criada / pedido_criado)
  └─POST→ /integracoes/tagplus/webhook/notificacao          (NOVO blueprint)
            1. valida X-Hub-Secret (reusa validar_assinatura)
            2. extrai event_type + data[0].id  (id é string)
            3. dedupe: existe TagPlusNotificacaoWhatsapp(tipo,tagplus_id,event_type) enviado? → 200 (skip)
            4. cria registro status=PENDENTE; commit
            5. Thread(daemon=False) → processar_notificacao_async(app, registro_id)
            6. retorna 200 imediato
                 │
                 ▼ (thread, app_context)
      processar_notificacao_async
        a. status=PROCESSANDO
        b. busca API com retry [1,3,5]s:
             pedido → GET /pedidos/{id}     (scope read:pedidos)
             nfe    → GET /nfes/{id}
        c. formata mensagem (formatador_notificacao)
        d. [nfe] baixa PDF GET /nfes/pdf/recibo_a4/{id} → bytes → base64
        e. send_whatsapp(GRUPO, texto, anexo_b64=..., anexo_filename=..., anexo_mimetype="application/pdf")
        f. status=ENVIADO / ERRO(+msg); cleanup
```

**Por que webhook dedicado e não pendurar no `/webhook/tagplus/nfe`:** isola 100% do faturamento (que está ativo); falha de notificação não afeta importação e vice-versa; e o pedido precisaria de endpoint próprio de qualquer forma. O usuário cadastra **um webhook novo** no painel TagPlus (eventos `nfe_criada` + `pedido_criado`) apontando para a URL nova.

**Por que thread e não RQ:** espelha o padrão já em produção (WhatsApp bot); notificação é best-effort (informativa); evita editar `worker_render.py` + `start_worker_render.sh` e propagar tokens OpenClaw ao worker. Não pode ser síncrono no request (timeout TagPlus + retry de busca 1-5s + base64 do PDF).

## Fluxo de dados

`Request (TagPlus POST) → Route (webhook_notificacao_routes) → Service (notificacao_whatsapp_service, thread) → API TagPlus (oauth_notas.make_request) → Formatador → send_whatsapp → Gateway OpenClaw → Model (TagPlusNotificacaoWhatsapp: status/auditoria) → Template (histórico)`.

## Componentes (arquivos a criar/modificar)

**Criar:**

1. `app/integracoes/tagplus/services/__init__.py` — novo pacote (a pasta `services/` ainda não existe).
2. `app/integracoes/tagplus/webhook_notificacao_routes.py`
   - Blueprint `tagplus_notificacao` (csrf-exempt).
   - `POST /integracoes/tagplus/webhook/notificacao` — valida `X-Hub-Secret` (reusa `webhook_routes.validar_assinatura`), lê `event_type` ∈ {`pedido_criado`, `nfe_criada`}, `tagplus_id = data[0]['id']` (string), faz dedupe, cria registro PENDENTE, dispara thread, retorna 200. Eventos fora do escopo → 200 ignorado (log).
   - `GET /integracoes/tagplus/notificacoes` — tela de histórico (paginada).
   - `POST /integracoes/tagplus/notificacoes/<id>/reenviar` — re-dispara o envio (status ERRO) — `@login_required`.
3. `app/integracoes/tagplus/services/notificacao_whatsapp_service.py`
   - `disparar_thread(app, registro_id)` — `Thread(daemon=False)`.
   - `processar_notificacao_async(app, registro_id)` — orquestra busca+formata+PDF+envio, com `_commit_with_retry`, re-fetch e cleanup no `finally` (R1-R5).
   - `_buscar_pedido_com_retry(api, tagplus_id)` / `_buscar_nfe_com_retry(api, tagplus_id)` — delays `[1,3,5]`.
   - `_baixar_danfe_pdf(api, tagplus_id) -> bytes | None`.
4. `app/integracoes/tagplus/services/formatador_notificacao.py`
   - `formatar_pedido(pedido: dict) -> str` e `formatar_nfe(nfe: dict) -> str` — texto WhatsApp-friendly (sem tabela/markdown header; usa `*bold*`, emojis, listas — regra R8). Reusa `app/utils/template_filters` para `R$`/números BR quando aplicável (ou helper local equivalente).
5. `app/integracoes/tagplus/models_notificacao.py` — model `TagPlusNotificacaoWhatsapp` (ver [Modelo de dados](#modelo-de-dados)).
6. `scripts/migrations/2026_06_06_tagplus_notificacao_whatsapp.py` + `.sql` — DDL dual idempotente (regra MIGRATIONS).
7. `app/templates/integracoes/tagplus_notificacoes.html` — histórico: tipo, número, cliente, status (badge), enviado_em, erro, botão **Reenviar** (quando ERRO). Segue `GUIA_COMPONENTES_UI.md`.

**Modificar:**

8. `app/utils/whatsapp_notify.py` — `send_whatsapp()` ganha kwargs opcionais `anexo_b64: str|None`, `anexo_filename: str|None`, `anexo_mimetype: str="application/pdf"`. Quando `anexo_b64` presente: monta args com `buffer=anexo_b64`, `filename`, `mimeType`, `caption=text` (mantém `message=text` por segurança). Sem anexo → comportamento **idêntico** ao atual. Atualizar docstring.
9. `app/__init__.py` — `register_blueprint(tagplus_notificacao)` junto aos demais TagPlus (~linha 1304).
10. `app/templates/base.html` — link de menu para `/integracoes/tagplus/notificacoes` (regra: toda tela acessível via UI; sob o grupo Integrações/TagPlus).

## Modelo de dados

Tabela `tagplus_notificacao_whatsapp` (dedupe + auditoria + base da tela):

| Coluna | Tipo | Nota |
|---|---|---|
| `id` | PK serial | |
| `tipo` | String(10) | `PEDIDO` \| `NFE` |
| `event_type` | String(30) | `pedido_criado` \| `nfe_criada` |
| `tagplus_id` | String(30) | id do registro no TagPlus (string, como vem) |
| `numero` | String(30) | número do pedido/NF (preenchido após busca) |
| `cliente_nome` | String(255) | resumo p/ a tela |
| `valor` | Numeric(15,2) | resumo p/ a tela |
| `status` | String(15) | `PENDENTE`/`PROCESSANDO`/`ENVIADO`/`ERRO`/`IGNORADO` |
| `erro` | Text | mensagem de erro (quando ERRO) |
| `tentativas` | Integer | nº de tentativas de envio |
| `anexou_pdf` | Boolean | true se PDF foi anexado |
| `enviado_em` | DateTime | timezone naive (Brasil) — `agora_utc_naive` |
| `criado_em` | DateTime | default `agora_utc_naive` |

**Índice/constraint:** `UNIQUE (tipo, tagplus_id, event_type)` — idempotência contra reenvio do TagPlus. Migration dual (py com `create_app()` + verificação; sql idempotente `IF NOT EXISTS`).

> Não usar campo `db.JSON` para payload bruto no v1 (evita necessidade de `sanitize_for_json`); se for guardar o dict da API depois, aplicar `sanitize_for_json` (regra do projeto — `valor_nota`/`valor_total` podem vir como número/Decimal).

## Formato das mensagens

WhatsApp-friendly (R8: sem tabela markdown, sem `##`, sem code block; permitido `*bold*`, `_italic_`, emojis, `- lista`).

**NF (texto + PDF anexado como `caption`):**
```
🧾 *Nova NF emitida — Nº {numero}/{serie}*
👤 Cliente: {destinatario.razao_social}
🧑‍💼 Vendedor: {vendedor}        ← best-effort (ver abaixo); omitido se indisponível
💰 Valor: R$ {valor_nota|valor_br}
📅 {data_emissao dd/mm/aaaa}

Itens:
- {produto.codigo} {produto.descricao} — {qtd} x R$ {valor_unitario}
...
```

**Pedido (texto):**
```
🛒 *Novo pedido — Nº {numero}*
👤 Cliente: {cliente.razao_social}
🧑‍💼 Vendedor: {vendedor.nome}
💰 Valor: R$ {valor_total|valor_br}
🚚 Entrega: {data_entrega}
📝 {observacoes (se houver, truncado)}

Itens:
- {produto_servico.codigo} ... — {qtd} x R$ {valor_unitario}
...
```

**Vendedor na NF (best-effort):** a NF não traz vendedor (`DOCUMENTACAO_API_TAGPLUS.md`). Opção implementada: se `nfe.pedido_os_vinculada.id` existir **e** o scope `read:pedidos` estiver disponível, busca `GET /pedidos/{id}` e usa `vendedor.nome`; caso contrário, **omite a linha de vendedor** na NF (não falha o envio). `[ASSUNÇÃO - CONFIRMAR]`

**Itens longos:** OpenClaw chunka > 4096 chars automaticamente; não chunkar manualmente. Se a lista de itens for muito grande, truncar com `… (+N itens)` para legibilidade. `[ASSUNÇÃO - CONFIRMAR]` limite de itens exibidos (proposta: 30).

## Envio do anexo PDF

- Baixar: `oauth_notas.make_request('GET', f'/nfes/pdf/recibo_a4/{tagplus_id}')` → validar `status_code==200` e `content-type` PDF → `response.content` (bytes).
- Encodar: `base64.b64encode(bytes).decode()`.
- Enviar: `send_whatsapp(GRUPO, texto, anexo_b64=b64, anexo_filename=f"danfe_{numero}.pdf", anexo_mimetype="application/pdf")`.
- O gateway recebe `buffer`(base64) + `filename` + `mimeType` + `caption`(texto). Confirmado no schema do tool `message`.
- **Falha no PDF não aborta a notificação:** se o download falhar, envia **só o texto** e marca `anexou_pdf=false` + nota no `erro` (degradação graciosa).
- **Tamanho:** DANFE A4 costuma ser pequena (dezenas de KB–poucos MB); base64 infla ~33%. `[ASSUNÇÃO - CONFIRMAR]` limite prático do gateway/HTTP; se exceder, fallback para só-texto (monitorar via histórico).

## Configuração (env vars)

```bash
TAGPLUS_NOTIFY_WHATSAPP_GROUP_JID=120363xxxxxxxxxxxx@g.us   # grupo único de vendas (obrigatório)
TAGPLUS_NOTIFY_ENABLED=true                                  # kill switch da feature
# Reusa as já existentes:
# OPENCLAW_GATEWAY_URL, OPENCLAW_GATEWAY_TOKEN, OPENCLAW_NOTIFY_ENABLED (+ HMAC/CF se em túnel)
```
Sem `TAGPLUS_NOTIFY_WHATSAPP_GROUP_JID` → registra `ERRO` (config ausente) e não envia. Sem `OPENCLAW_GATEWAY_TOKEN` → `send_whatsapp` já levanta erro tratado.

## Pré-requisitos que dependem do usuário

1. **Scope OAuth `read:pedidos`** na conta TagPlus `notas` da integração principal. Hoje o scope é `read:nfes read:clientes read:produtos` (`oauth2_v2.py:45`) → o `GET /pedidos/{id}` retornaria **401**. Para notificar **pedido**, é preciso **adicionar `read:pedidos` ao scope e reautorizar o OAuth** (refresh não re-emite scope). **NF funciona sem isso.** Mitigação: se o pedido der 401, registrar `ERRO` claro ("reautorizar OAuth com read:pedidos") sem derrubar o resto.
2. **JID do grupo de vendas** (`...@g.us`) → env var. Como descobrir: via OpenClaw (listar conversas/grupos do gateway) ou observando o `conversation_jid` de uma mensagem do grupo. Será documentado no plano.
3. **Cadastrar o webhook novo no painel TagPlus**: nome livre, URL `https://<dominio>/integracoes/tagplus/webhook/notificacao`, `X-Hub-Secret` (mesmo valor que o sistema valida), eventos `pedido_criado` + `nfe_criada`.

## Segurança

- Validação **`X-Hub-Secret`** reusando `validar_assinatura` (`webhook_routes.py:191`). **Melhoria:** mover o secret hardcoded (`webhook_routes.py:25`) para env var `TAGPLUS_WEBHOOK_SECRET` com fallback ao valor atual (retrocompatível) — sem quebrar o webhook de faturamento existente. `[ASSUNÇÃO - CONFIRMAR]`
- CSRF exempt (webhook externo) — padrão já usado.
- Endpoint csrf-exempt **não** executa nada pesado de forma síncrona; só cria registro + thread.
- Tela e reenvio sob `@login_required`.

## Idempotência e robustez

- **Dedupe** por `UNIQUE (tipo, tagplus_id, event_type)`: reenvio do TagPlus para o mesmo registro não duplica a mensagem (já `ENVIADO` → 200 skip).
- **Race (webhook antes do dado):** retry `[1,3,5]s` na busca da API (padrão `webhook_routes.py`).
- **DB SSL drop (Render):** `_commit_with_retry` + re-fetch (R2/R3).
- **Thread `daemon=False`** garante conclusão em reciclagem do gunicorn (R1).
- **Cleanup** no `finally` (`db.session.remove()`), sem ContextVars MCP (não usa Agent SDK — mais simples que o WhatsApp bot).

## Erros e edge cases

| Cenário | Tratamento |
|---|---|
| `event_type` fora do escopo | 200 + log; status `IGNORADO` (ou nem registra) |
| `data[]` vazio / sem id | 400 + log |
| Assinatura inválida | 401 (igual webhook existente) |
| API TagPlus 404 após retries | status `ERRO`, sem envio |
| Pedido 401 (sem scope) | status `ERRO` com instrução de reautorizar; não afeta NF |
| PDF indisponível/erro | envia só texto, `anexou_pdf=false`, nota no `erro` |
| Gateway OpenClaw down/401 | status `ERRO`; reenvio manual pela tela |
| `GROUP_JID` ausente | status `ERRO` (config) |
| Mensagem > 4096 chars | OpenClaw chunka sozinho; itens truncados se necessário |

## Testes

Determinísticos (pytest), sem LLM (preferência do projeto):
- `formatar_pedido`/`formatar_nfe`: dado dict de exemplo (fixtures dos payloads reais documentados), valida texto esperado (campos, R$ BR, omissão de vendedor na NF sem pedido vinculado, truncamento de itens).
- `send_whatsapp` com `anexo_b64`: monta args com `buffer`/`filename`/`mimeType`/`caption` (mock do `requests.post`, sem rede); sem anexo → args idênticos ao atual (regressão).
- Webhook: dedupe (2º POST mesmo id não cria 2º registro), parsing de `data[0]['id']` string, evento fora do escopo ignorado, assinatura inválida → 401 (mock).
- Service: caminho NF (com/sem PDF), caminho pedido (401 → ERRO), retry de busca (mock 404→200).
- Migration: idempotência (rodar 2x).

## Riscos e mitigação

| Risco | Severidade | Mitigação |
|---|---|---|
| Scope `read:pedidos` ausente → pedido não notifica | Média | Pré-requisito explícito; NF funciona; erro acionável na tela |
| PDF grande estoura gateway/HTTP | Baixa | DANFE A4 é pequena; fallback só-texto + monitorar histórico |
| Thread no gunicorn-sistema sob carga | Baixa | Padrão já em produção (WhatsApp bot); trabalho curto |
| Dois webhooks TagPlus para `nfe_criada` (faturamento + notificação) | Baixa | TagPlus suporta múltiplos webhooks (doc); endpoints independentes |
| Secret hardcoded compartilhado | Baixa | Migrar para env var com fallback |

## Assunções a confirmar

1. NF: vendedor é **best-effort** (via pedido vinculado se scope permitir; senão omite). 
2. Pedido **sem PDF** (não há DANFE de pedido).
3. Limite de itens exibidos na mensagem = **30** (resto truncado).
4. Secret do webhook migra para `TAGPLUS_WEBHOOK_SECRET` com fallback ao valor atual.
5. Apenas eventos de **criação** (`pedido_criado`, `nfe_criada`) no v1.
