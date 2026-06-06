<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: CLAUDE.md
superseded_by: —
atualizado: 2026-06-06
-->

# Notificação TagPlus → WhatsApp (pedido/NF)

> **Papel:** guia operacional para ativar e operar a notificação WhatsApp de pedido criado / NF emitida no TagPlus.

## Indice

1. [Visão geral](#1-visão-geral)
2. [Variáveis de ambiente](#2-variáveis-de-ambiente)
3. [Cadastro do webhook no painel TagPlus](#3-cadastro-do-webhook-no-painel-tagplus)
4. [Pré-requisito — scope OAuth `read:pedidos`](#4-pré-requisito--scope-oauth-readpedidos)
5. [Pré-requisito — cadastro de vendedores em `usuarios`](#5-pré-requisito--cadastro-de-vendedores-em-usuarios)
6. [Como descobrir o JID do grupo](#6-como-descobrir-o-jid-do-grupo)
7. [Migration](#7-migration)
8. [Operação e observabilidade](#8-operação-e-observabilidade)

---

## 1. Visão geral

Quando o TagPlus dispara um evento `pedido_criado` ou `nfe_criada`, o sistema:

1. Recebe o webhook em `/integracoes/tagplus/webhook/notificacao` (blueprint `tagplus_notificacao`).
2. Registra a notificação na tabela `tagplus_notificacao_whatsapp` com dedupe por `UNIQUE(tipo, tagplus_id, event_type)`.
3. Dispara uma thread assíncrona que monta a mensagem e envia via gateway OpenClaw:
   - **Grupo de vendas** (`TAGPLUS_NOTIFY_WHATSAPP_GROUP_JID`) — sempre.
   - **DM do vendedor** — quando o vendedor for resolvido e tiver WhatsApp autorizado.
4. Para eventos `nfe_criada`, o PDF da DANFE é baixado do TagPlus e anexado à mensagem.

Este webhook é **completamente independente** do webhook de faturamento (`/webhook/tagplus/nfe`). Uma falha aqui não afeta a importação de NFs e vice-versa.

---

## 2. Variáveis de ambiente

| Variável | Obrigatória | Descrição |
|---|---|---|
| `TAGPLUS_NOTIFY_WHATSAPP_GROUP_JID` | **Sim** | JID do grupo de vendas no WhatsApp (`xxxxx@g.us`). Sem este valor, toda notificação termina com status `ERRO`. |
| `TAGPLUS_NOTIFY_ENABLED` | Não | Quando `false` ou `0`, desabilita o envio (as notificações ainda são registradas). Reaproveita também `OPENCLAW_NOTIFY_ENABLED`. |
| `OPENCLAW_GATEWAY_URL` | Sim (gateway) | URL do gateway OpenClaw (ex.: `http://localhost:3000`). |
| `OPENCLAW_GATEWAY_TOKEN` | Sim (gateway) | Token de autenticação do gateway OpenClaw. |

As variáveis do gateway OpenClaw (`OPENCLAW_GATEWAY_URL`, `OPENCLAW_GATEWAY_TOKEN`) são compartilhadas com outras funcionalidades do sistema. Se já estiverem configuradas, não é necessário duplicá-las.

---

## 3. Cadastro do webhook no painel TagPlus

1. Acesse o painel do TagPlus → **Configurações → Webhooks → Novo webhook**.
2. Preencha:
   - **URL de callback:** `https://<seu-dominio>/integracoes/tagplus/webhook/notificacao`
   - **X-Hub-Secret:** mesmo valor de `WEBHOOK_SECRET` definido em `app/integracoes/tagplus/webhook_routes.py` (atualmente `frete2024tagplus#secret`; melhoria futura: mover para env `TAGPLUS_WEBHOOK_SECRET`).
   - **Eventos de disparo:** `pedido_criado` e `nfe_criada`.
3. Salve e ative o webhook.

> **Coexistência:** este webhook pode coexistir com o webhook de faturamento já cadastrado (`/webhook/tagplus/nfe`). São URLs e registros distintos no painel do TagPlus — não há conflito.

---

## 4. Pré-requisito — scope OAuth `read:pedidos`

A conta OAuth `notas` (`app/integracoes/tagplus/oauth2_v2.py`, scope atual `read:nfes read:clientes read:produtos`) **não inclui `read:pedidos`**.

Consequências sem esse scope:

- Notificação de **PEDIDO** falha com 401 ao tentar buscar detalhes do pedido no TagPlus.
- O **vendedor da NF** não é resolvido (a NF segue apenas para o grupo; sem DM do vendedor).

**Para habilitar:** reautorize o fluxo OAuth incluindo `read:pedidos` no escopo. O refresh token não re-emite scopes — é necessário um novo fluxo de autorização completo.

---

## 5. Pré-requisito — cadastro de vendedores em `usuarios`

Para que a DM ao vendedor funcione, o vendedor precisa estar cadastrado na tabela `usuarios` com:

| Campo | Requisito |
|---|---|
| `telefone` | Preenchido (número usado para encontrar o contato no WhatsApp) |
| `whatsapp_autorizado` | `True` |
| `status` | `'ativo'` |
| `vendedor_vinculado` ou `nome` | Deve bater com o nome do vendedor informado pelo TagPlus |

Sem esse cadastro, o sistema cai no **fallback**: envia apenas para o grupo e registra o vendedor como "não notificado" no histórico.

---

## 6. Como descobrir o JID do grupo

O JID é um identificador no formato `XXXXXXXXXXX-XXXXXXXXXX@g.us` (grupos) atribuído pelo WhatsApp.

**Procedimento:**

1. Envie qualquer mensagem no grupo de vendas pelo WhatsApp conectado ao gateway OpenClaw.
2. O `conversation_jid` (`...@g.us`) aparecerá nos logs do gateway OpenClaw.
3. Copie o JID e configure em `TAGPLUS_NOTIFY_WHATSAPP_GROUP_JID`.

**Token do gateway:**

```bash
cat ~/.openclaw/openclaw.json | jq -r .gateway.auth.token
```

Detalhes completos do gateway OpenClaw estão na memória `openclaw_whatsapp_integration`.

---

## 7. Migration

A migration cria a tabela `tagplus_notificacao_whatsapp` com o índice de dedupe.

**Desenvolvimento (banco local):**

```bash
source .venv/bin/activate
export DATABASE_URL="..."
python scripts/migrations/2026_06_06_tagplus_notificacao_whatsapp.py
```

**Produção (Render Shell):**

```sql
-- Aplicar o arquivo SQL idempotente:
\i scripts/migrations/2026_06_06_tagplus_notificacao_whatsapp.sql
```

Ambos os scripts são idempotentes (`IF NOT EXISTS`).

---

## 8. Operação e observabilidade

**Tela de notificações:** `/integracoes/tagplus/notificacoes` (menu **Consultas**)

| Coluna | Descrição |
|---|---|
| Tipo | `PEDIDO` ou `NFE` |
| TagPlus ID | ID do pedido ou NF no TagPlus |
| Status | `ENVIADO`, `PARCIAL` (grupo OK, DM falhou) ou `ERRO` |
| Criado em | Data/hora do recebimento do webhook |
| Ações | Botão **Reenviar** (disponível para `ERRO` e `PARCIAL`) |

**Reenvio:** o botão Reenviar redefine o status para `PENDENTE` e dispara nova tentativa. Útil para reprocessar após corrigir configurações (JID, scope OAuth, cadastro de vendedor).

**Dedupe:** a tabela tem constraint `UNIQUE(tipo, tagplus_id, event_type)`. Webhooks duplicados do TagPlus são detectados e ignorados (status 200, resposta `{"status": "duplicado"}`).

**Diagnóstico rápido por status:**

- `ERRO` sem JID configurado → definir `TAGPLUS_NOTIFY_WHATSAPP_GROUP_JID`.
- `ERRO` em PEDIDO (401) → reautorizar OAuth com `read:pedidos`.
- `PARCIAL` (grupo OK, sem DM) → verificar cadastro do vendedor em `usuarios`.
- `ERRO` de gateway → verificar `OPENCLAW_GATEWAY_URL` e `OPENCLAW_GATEWAY_TOKEN`.
