<!-- doc:meta
tipo: how-to
camada: L1
sot_de: integracao WhatsApp via N8N + Evolution API
hub: app/whatsapp/CLAUDE.md
superseded_by: —
atualizado: 2026-06-25
-->
# WhatsApp via N8N + Evolution API — Runbook de Montagem

> **Papel:** passo-a-passo para montar o transporte WhatsApp 24/7 (Evolution API + N8N)
> em substituicao ao OpenClaw, que so roda com o PC do operador ligado.

## Indice

- [Visao geral](#visao-geral)
- [Por que esta arquitetura](#por-que-esta-arquitetura)
- [Valores a coletar (preencha ANTES de comecar)](#valores-a-coletar-preencha-antes-de-comecar)
- [Checklist de execucao (faca nesta ordem)](#checklist-de-execucao-faca-nesta-ordem)
- [Pre-requisitos](#pre-requisitos)
- [Passo 1 — Subir a Evolution API (VPS, 24/7)](#passo-1--subir-a-evolution-api-vps-247)
- [Passo 2 — Criar a instancia e parear o numero](#passo-2--criar-a-instancia-e-parear-o-numero)
- [Passo 3 — Montar o workflow no N8N](#passo-3--montar-o-workflow-no-n8n)
- [Passo 4 — Apontar o webhook da Evolution para o N8N](#passo-4--apontar-o-webhook-da-evolution-para-o-n8n)
- [Passo 5 — Configurar as envs no Render](#passo-5--configurar-as-envs-no-render)
- [Passo 6 — Cutover e validacao](#passo-6--cutover-e-validacao)
- [Rollback](#rollback)
- [Troubleshooting](#troubleshooting)

---

## Visao geral

```
INBOUND  (WhatsApp -> agente)
  WhatsApp --> Evolution API (VPS 24/7) --webhook--> N8N (normaliza) --HTTP-->
       POST /api/whatsapp/n8n/inbound   (Bearer N8N_INBOUND_TOKEN)
            --> cria WhatsAppTask --> Agent SDK processa

OUTBOUND (agente -> WhatsApp)
  Flask (_send_whatsapp_reply) --> Evolution API DIRETO (POST /message/sendText)
       (NAO volta pelo N8N — um hop a menos; a resposta nao depende do N8N de pe)
```

Quatro pecas:

| Peca | Onde roda | Papel |
|------|-----------|-------|
| **Evolution API** | VPS seu (Docker) | Fala WhatsApp via Baileys, 24/7. Substitui o Baileys local do OpenClaw |
| **N8N** | self-hosted ou n8n.cloud | Recebe o webhook da Evolution, normaliza e POSTa no Flask |
| **Flask** (este repo) | Render | Cria a task, chama o Agent SDK, envia a resposta direto pela Evolution |
| **Seletor** `WHATSAPP_TRANSPORT` | env no Render | `openclaw` (default) ou `n8n` |

## Por que esta arquitetura

- **Inbound passa pelo N8N**: e onde voce normaliza/roteia/filtra sem mexer em codigo
  (allowlist, ignorar grupos, etc.). O N8N agrega valor aqui.
- **Outbound NAO passa pelo N8N**: a resposta vai do Flask direto na Evolution. Se o N8N
  cair, voce ainda recebe (so para de processar inbound novo) e as respostas em andamento saem.
- **Seletor por env**: OpenClaw continua intacto. Voce vira a chave (`WHATSAPP_TRANSPORT=n8n`)
  e faz rollback instantaneo (`=openclaw`) sem deploy de codigo.

---

## Valores a coletar (preencha ANTES de comecar)

Tenha estes valores em maos / gere-os antes — voce vai reusar em varios passos.
Anote num bloco de notas seguro (NAO commite isso no git):

| Valor | Como obter | Onde usa |
|-------|-----------|----------|
| `EVOLUTION_API_URL` | URL publica HTTPS do seu VPS (ex: `https://evo.seudominio.com`) | Evolution (`SERVER_URL`), Render |
| `EVOLUTION_API_KEY` | Voce inventa uma chave forte (`openssl rand -hex 32`) e poe no compose | Evolution (`AUTHENTICATION_API_KEY`), Render, todos os `curl` |
| `EVOLUTION_INSTANCE` | Nome que voce escolher ao criar a instancia (ex: `nacom`) | Passo 2, Render |
| `N8N_INBOUND_TOKEN` | `python -c "import secrets; print(secrets.token_urlsafe(48))"` | N8N (variavel) **e** Render — MESMO valor nos dois |
| `FLASK_BASE_URL` | URL publica do Render (ex: `https://sistema-fretes.onrender.com`) | N8N (variavel) |
| URL do webhook N8N | Sai no Passo 3 ao ativar o workflow (`https://seu-n8n/webhook/nacom-whatsapp-inbound`) | Passo 4 (apontar Evolution) |

> Regra de ouro: `EVOLUTION_API_KEY` e `N8N_INBOUND_TOKEN` sao segredos. So o `N8N_INBOUND_TOKEN`
> precisa ser **identico** em dois lugares (N8N e Render). Os demais sao 1 lugar so.

---

## Checklist de execucao (faca nesta ordem)

Marque conforme avanca. Cada item linka pro passo detalhado abaixo.

- [ ] **0.** Desconectar o numero do OpenClaw (Aparelhos conectados no WhatsApp) — o numero
      so pode estar pareado em um lugar por vez.
- [ ] **1.** [Subir a Evolution API no VPS](#passo-1--subir-a-evolution-api-vps-247) (`docker compose up -d` + reverse proxy HTTPS).
- [ ] **2.** [Criar a instancia e parear o numero](#passo-2--criar-a-instancia-e-parear-o-numero) (escanear QR). Confirmar `state: open`.
- [ ] **3.** [Importar e ativar o workflow no N8N](#passo-3--montar-o-workflow-no-n8n) + setar `FLASK_BASE_URL` e `N8N_INBOUND_TOKEN`. Copiar a Production URL.
- [ ] **4.** [Apontar o webhook da Evolution pro N8N](#passo-4--apontar-o-webhook-da-evolution-para-o-n8n) (1 curl).
- [ ] **5.** [Setar as envs no Render](#passo-5--configurar-as-envs-no-render) (incluindo `WHATSAPP_TRANSPORT=n8n`) e reiniciar.
- [ ] **6.** [Validar](#passo-6--cutover-e-validacao): `/health` mostra `transport: n8n`, mandar msg de teste de um numero autorizado, receber resposta.
- [ ] **7.** Rodou bem por alguns dias? Pode desligar o OpenClaw de vez (manter as envs OpenClaw no Render por enquanto, custam nada e servem de rollback).

> Travou em algum passo? Vai direto pro [Troubleshooting](#troubleshooting). Deu errado feio?
> [Rollback](#rollback) em 1 env e volta pro OpenClaw na hora.

---

## Pre-requisitos

- Um **VPS** (qualquer: Hetzner, DigitalOcean, Contabo...) com Docker. 1 vCPU / 1GB ja roda Evolution.
- Uma instancia **N8N** acessivel por HTTPS publico (a Evolution precisa alcancar o webhook).
  - Self-hosted no mesmo VPS (Docker) **ou** n8n.cloud.
- Acesso ao dashboard do **Render** para setar envs no servico `sistema-fretes`.
- O numero de WhatsApp que voce ja usa (o mesmo do OpenClaw serve — desconecte la antes de parear aqui).

---

## Passo 1 — Subir a Evolution API (VPS, 24/7)

`docker-compose.yml` minimo (Evolution API v2):

```yaml
services:
  evolution-api:
    image: atendai/evolution-api:v2.1.1
    restart: always
    ports:
      - "8080:8080"
    environment:
      - SERVER_URL=https://evo.SEUDOMINIO.com   # URL publica da Evolution
      - AUTHENTICATION_API_KEY=GERE_UMA_CHAVE_FORTE_AQUI
      - DATABASE_ENABLED=true
      - DATABASE_PROVIDER=postgresql
      - DATABASE_CONNECTION_URI=postgresql://user:pass@postgres:5432/evolution
      - CACHE_REDIS_ENABLED=false
    volumes:
      - evolution_instances:/evolution/instances
    depends_on:
      - postgres
  postgres:
    image: postgres:16-alpine
    restart: always
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=evolution
    volumes:
      - evolution_pg:/var/lib/postgresql/data
volumes:
  evolution_instances:
  evolution_pg:
```

```bash
docker compose up -d
# Ponha um reverse proxy (Caddy/Nginx/Cloudflare Tunnel) na frente para ter
# HTTPS em https://evo.SEUDOMINIO.com -> 127.0.0.1:8080
```

> Guarde o valor de `AUTHENTICATION_API_KEY` — e o `EVOLUTION_API_KEY` que o Render vai usar.

## Passo 2 — Criar a instancia e parear o numero

```bash
# Cria a instancia "nacom"
curl -X POST https://evo.SEUDOMINIO.com/instance/create \
  -H "apikey: SUA_CHAVE_FORTE" -H "Content-Type: application/json" \
  -d '{"instanceName":"nacom","integration":"WHATSAPP-BAILEYS","qrcode":true}'

# Pega o QR code (abra o base64 retornado no navegador OU use o Manager web)
curl https://evo.SEUDOMINIO.com/instance/connect/nacom -H "apikey: SUA_CHAVE_FORTE"
```

Escaneie o QR com o WhatsApp do numero (Aparelhos conectados -> Conectar). Confirme:

```bash
curl https://evo.SEUDOMINIO.com/instance/connectionState/nacom -H "apikey: SUA_CHAVE_FORTE"
# -> {"instance":{"state":"open"}}  = conectado
```

> `instanceName` = "nacom" -> e o `EVOLUTION_INSTANCE` no Render.

## Passo 3 — Montar o workflow no N8N

1. No N8N: **Workflows -> Import from File** -> selecione
   `app/whatsapp/n8n/nacom_whatsapp_inbound.workflow.json` (deste repo).
2. O workflow tem 3 nos:
   - **Webhook (Evolution)** — path `nacom-whatsapp-inbound`.
   - **Normaliza Evento** — Code node que converte o `messages.upsert` da Evolution no
     contrato do Flask (`sender`, `conversation`, `is_group`, `text`, `message_id`, `sender_name`).
     Descarta `fromMe`, mensagens sem texto e eventos que nao sejam `messages.upsert`.
   - **POST Flask /n8n/inbound** — manda pro Flask com `Authorization: Bearer`.
3. Defina **duas variaveis de ambiente no N8N** (Settings -> Variables, ou env do container):
   - `FLASK_BASE_URL` = `https://sistema-fretes.onrender.com` (URL publica do Render)
   - `N8N_INBOUND_TOKEN` = o MESMO segredo que vai no Render (gere no Passo 5)
   > Se sua versao do N8N nao expoe `$env`, edite os dois nos e cole os valores direto
   > (URL no node HTTP, e `Bearer SEU_TOKEN` no header Authorization).
4. **Ative** o workflow (toggle Active). Copie a **Production URL** do webhook
   (algo como `https://SEU-N8N/webhook/nacom-whatsapp-inbound`).

## Passo 4 — Apontar o webhook da Evolution para o N8N

```bash
curl -X POST https://evo.SEUDOMINIO.com/webhook/set/nacom \
  -H "apikey: SUA_CHAVE_FORTE" -H "Content-Type: application/json" \
  -d '{
    "webhook": {
      "enabled": true,
      "url": "https://SEU-N8N/webhook/nacom-whatsapp-inbound",
      "byEvents": false,
      "events": ["MESSAGES_UPSERT"]
    }
  }'
```

> So `MESSAGES_UPSERT` e necessario para o inbound. Outros eventos so geram ruido.

## Passo 5 — Configurar as envs no Render

Gere o token compartilhado:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

No dashboard do Render (servico `sistema-fretes` -> Environment), adicione:

```bash
WHATSAPP_TRANSPORT=n8n                       # vira a chave para o novo transporte
N8N_INBOUND_TOKEN=<token-gerado-acima>       # MESMO valor que voce pos no N8N
EVOLUTION_API_URL=https://evo.SEUDOMINIO.com
EVOLUTION_API_KEY=<AUTHENTICATION_API_KEY da Evolution>
EVOLUTION_INSTANCE=nacom
# EVOLUTION_NOTIFY_ENABLED=true              # opcional (default true; "false" muta o envio)
```

> Mantenha `OPENCLAW_PLUGIN_TOKEN` / `OPENCLAW_GATEWAY_TOKEN` no Render por ora — eles so
> sao usados quando `WHATSAPP_TRANSPORT=openclaw`. Util para rollback.

## Passo 6 — Cutover e validacao

1. **Health check** (sem auth):
   ```bash
   curl https://sistema-fretes.onrender.com/api/whatsapp/health
   ```
   Espere:
   ```json
   {
     "transport": "n8n",
     "n8n_token_configured": true,
     "evolution_configured": true,
     ...
   }
   ```
2. **Inbound real**: mande uma mensagem WhatsApp de um numero **ja autorizado**
   (`usuarios.whatsapp_autorizado = true` + telefone batendo). Acompanhe a execucao no N8N
   (aba Executions) e os logs do Render (`grep WHATSAPP`).
3. **Outbound**: voce deve receber a resposta do agente no mesmo chat.
4. Se algo falhar -> **Rollback** (abaixo) e investigue com o Troubleshooting.

---

## Rollback

Instantaneo, sem deploy de codigo: no Render, mude

```bash
WHATSAPP_TRANSPORT=openclaw
```

e reinicie o servico. O inbound volta para o `/inbound` do plugin OpenClaw e o outbound
volta para o gateway OpenClaw. (O webhook da Evolution continua POSTando no N8N, mas o
`/n8n/inbound` so cria task — se quiser parar 100%, desative o workflow no N8N.)

---

## Troubleshooting

### N8N recebe mas o Flask responde 401 `token invalido`
`N8N_INBOUND_TOKEN` no N8N != no Render. Devem ser identicos. Confira no `/health`
o campo `n8n_token_configured: true`.

### Flask responde 403 `sender_not_authorized`
Mesmo problema do OpenClaw: o telefone do remetente nao esta mapeado/autorizado.
- `SELECT telefone, whatsapp_autorizado FROM usuarios WHERE id=N`
- O `sender` que o N8N manda e so digitos com DDI (ex `5511991642998`).
  `Usuario.find_by_whatsapp_jid` trata variantes BR/E.164.

### A resposta nao chega no WhatsApp
1. `/health` -> `evolution_configured: true`?
2. Instancia conectada? `curl .../instance/connectionState/nacom` -> `state: open`.
3. `EVOLUTION_API_KEY` / `EVOLUTION_INSTANCE` corretos? Logs do Render: `grep WHATSAPP-EVO`.
4. Numero do destinatario valido (com DDI)? O helper normaliza, mas confira o formato no banco.

### O N8N nao e acionado quando chega mensagem
- Webhook da Evolution aponta para a **Production URL** (nao a de teste)?
  `curl .../webhook/find/nacom -H "apikey: ..."`
- Workflow esta **Active** no N8N?
- A Evolution alcanca o N8N por HTTPS publico? (firewall/proxy)

### Mensagens duplicadas
A Evolution pode reentregar webhook. O `message_id` e gravado em
`whatsapp_tasks.openclaw_message_id` — dedup por ele e Fase 6 (hoje nao bloqueia).
