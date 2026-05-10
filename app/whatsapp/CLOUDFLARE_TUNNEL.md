# Cloudflare Tunnel — Setup do gateway OpenClaw para Render

Expoe o gateway OpenClaw local (`loopback:18789`) para o Render via
Cloudflare Tunnel com Cloudflare Access (defense-in-depth).

## Arquitetura final

```
Render (sistema-fretes.onrender.com)
   │  POST https://openclaw.<seu-dominio>/tools/invoke
   │  headers:
   │    Authorization: Bearer <OPENCLAW_GATEWAY_TOKEN>
   │    CF-Access-Client-Id: <SERVICE_TOKEN_ID>
   │    CF-Access-Client-Secret: <SERVICE_TOKEN_SECRET>
   ↓
Cloudflare Edge
   │  Verifica service token (CF Access) ANTES de passar request adiante
   ↓
cloudflared (rodando no WSL2 como systemd service)
   │  Tunnel persistente outbound (sem porta aberta no firewall)
   ↓
http://127.0.0.1:18789  (gateway OpenClaw, bind=loopback)
```

3 camadas de seguranca: TLS Cloudflare + Service Token + Bearer token gateway.

---

## Pre-requisitos

1. **Conta Cloudflare** (gratuita) — https://dash.cloudflare.com/sign-up
2. **Dominio managed pelo Cloudflare** (gratuito se usar registrar deles, ou
   transferir nameservers de outro registrar). Sem dominio nao da pra usar
   Cloudflare Access — a alternativa "TryCloudflare" (sem dominio) gera URL
   volatil e nao suporta Access.
3. **cloudflared** instalado (ja feito por mim em `~/bin/cloudflared`,
   symlink em `~/.local/bin/cloudflared`).

---

## Setup interativo (rode os comandos abaixo)

### Passo 1 — Login Cloudflare (browser)

```bash
cloudflared tunnel login
```

Vai abrir browser pedindo selecionar dominio. Selecione o seu. Cria
`~/.cloudflared/cert.pem` (NUNCA commitar — ja esta gitignorado).

### Passo 2 — Criar named tunnel

```bash
cloudflared tunnel create openclaw-gateway
```

Output salva credenciais em `~/.cloudflared/<UUID>.json`. Anote o **UUID**
do tunnel — vai usar nos proximos passos.

### Passo 3 — Configurar arquivo do tunnel

Crie `~/.cloudflared/config.yml`:

```yaml
tunnel: <UUID-do-passo-2>
credentials-file: /home/rafaelnascimento/.cloudflared/<UUID>.json

ingress:
  - hostname: openclaw.<seu-dominio>.com
    service: http://127.0.0.1:18789
  - service: http_status:404
```

### Passo 4 — Criar DNS route (CNAME automatico)

```bash
cloudflared tunnel route dns openclaw-gateway openclaw.<seu-dominio>.com
```

### Passo 5 — Rodar como systemd service (24/7)

```bash
sudo cloudflared service install
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
sudo systemctl status cloudflared
```

Logs: `journalctl -u cloudflared -f`

### Passo 6 — Testar tunnel SEM Access (so pra confirmar conexao)

```bash
curl -sS https://openclaw.<seu-dominio>.com/healthz \
  -H "Authorization: Bearer <OPENCLAW_GATEWAY_TOKEN>"
# Deve retornar: {"ok":true,"status":"live"}
```

Se retornar isso, **a tunel esta funcional**. Agora adicione a camada de
Cloudflare Access pra impedir que internet aleatoria acesse o gateway.

---

## Cloudflare Access (Service Token)

### Passo 7 — Habilitar Cloudflare Zero Trust

Dashboard Cloudflare → Zero Trust (menu lateral) → primeira vez pede
ativar (gratuito ate 50 users). Aceite.

### Passo 8 — Criar self-hosted application

Zero Trust dashboard → **Access → Applications → Add an application →
Self-hosted**:

- **Application name**: `OpenClaw Gateway (Render)`
- **Session duration**: 24 hours
- **Application domain**: `openclaw.<seu-dominio>.com`
- **Path**: deixe vazio (cobre tudo)

Em **Identity providers**: desmarque tudo — vamos usar service token apenas.

### Passo 9 — Criar Service Token

Zero Trust → **Access → Service Auth → Service Tokens → Create Service
Token**:

- **Service token name**: `render-frete-system`
- **Duration**: `Non-expiring` (ou 1 ano com rotation lembrete)

Copie **Client ID** e **Client Secret** — Secret so aparece UMA VEZ.

### Passo 10 — Criar Access Policy (require token)

De volta na application criada no Passo 8 → **Policies → Add a policy**:

- **Policy name**: `Allow Render service token`
- **Action**: `Service Auth`
- **Configure rules**:
  - **Include** → `Service Token` → selecione `render-frete-system`

(Opcional camada extra) **Adicionar segunda regra Include AND**:

- `IP ranges` → preencha com IPs estaticos Render Oregon do dashboard
  (Connect → Outbound). Se nao tem IP fixo (workspace antiga), pule.

Salve.

### Passo 11 — Configurar Render

Adicione 3 env vars novas no service `sistema-fretes` (e
`sistema-fretes-worker-atacadao`):

```
OPENCLAW_GATEWAY_URL=https://openclaw.<seu-dominio>.com
CF_ACCESS_CLIENT_ID=<Client ID do Passo 9>
CF_ACCESS_CLIENT_SECRET=<Client Secret do Passo 9>
```

(`OPENCLAW_GATEWAY_TOKEN` e `OPENCLAW_PLUGIN_TOKEN` ja foram setados.)

Render redeploy automatico ao salvar. ~9 min para entrar em vigor.

### Passo 12 — Testar end-to-end

Apos redeploy do Render:

```bash
# Local: deve falhar 403 (sem service token)
curl -i https://openclaw.<seu-dominio>.com/healthz \
  -H "Authorization: Bearer <OPENCLAW_GATEWAY_TOKEN>"
# Esperado: HTTP/2 302 (redirect para login CF Access) ou 403

# Local: deve passar (com service token)
curl -i https://openclaw.<seu-dominio>.com/healthz \
  -H "Authorization: Bearer <OPENCLAW_GATEWAY_TOKEN>" \
  -H "CF-Access-Client-Id: <Client ID>" \
  -H "CF-Access-Client-Secret: <Client Secret>"
# Esperado: HTTP/2 200 + {"ok":true,"status":"live"}
```

### Passo 13 — Smoke test live (do Render)

Mande mensagem WhatsApp pra voce mesmo. Sequencia esperada:

1. Plugin nacom-bridge envia POST → `https://sistema-fretes.onrender.com/api/whatsapp/inbound`
2. Render recebe, valida `OPENCLAW_PLUGIN_TOKEN`, cria task, dispara thread
3. Thread chama Agent SDK, gera resposta
4. Thread chama `send_whatsapp(target, text)` → POST → `https://openclaw.<seu-dominio>.com/tools/invoke`
5. Cloudflare Access valida service token + bearer token
6. cloudflared encaminha pra `127.0.0.1:18789`
7. Gateway envia mensagem WhatsApp

Logs uteis:
- Render: dashboard → Logs (filtre `[WHATSAPP]`)
- Tunnel: `journalctl -u cloudflared -f`
- Plugin: `openclaw gateway logs --tail 50 | grep nacom-bridge`
- Banco: `SELECT id, peer_jid, status, mensagem, resposta FROM whatsapp_tasks ORDER BY created_at DESC LIMIT 3;`

---

## Boas praticas operacionais

### Token rotation

| Token | Frequencia | Como rotacionar |
|-------|------------|-----------------|
| `OPENCLAW_PLUGIN_TOKEN` | 90 dias | gerar novo (`secrets.token_urlsafe`), atualizar simultaneamente em `.env` Render + plugin config + reload gateway |
| `OPENCLAW_GATEWAY_TOKEN` | 90 dias | `openclaw config set gateway.auth.token <novo>` + atualizar `.env` Render + restart gateway |
| `CF_ACCESS_CLIENT_SECRET` | 6 meses | criar novo service token CF, atualizar Render env vars, deletar service token antigo |

### Backup

```bash
# Critico: cert + credentials do tunnel
cp ~/.cloudflared/cert.pem ~/backup/
cp ~/.cloudflared/<UUID>.json ~/backup/
cp ~/.cloudflared/config.yml ~/backup/

# Tambem o pareamento WhatsApp Baileys
cp -r ~/.openclaw/devices/ ~/backup/
cp -r ~/.openclaw/openclaw.json ~/backup/
```

Se perder cert.pem, precisa rodar `cloudflared tunnel login` de novo.
Se perder credentials JSON, precisa recriar tunnel (UUID muda).

### Monitoring

Adicionar uptime monitor para:
- `https://openclaw.<seu-dominio>.com/healthz` (com service token headers)
- `https://sistema-fretes.onrender.com/api/whatsapp/health`

Ambos devem retornar 200. Alertar se 4xx/5xx > 2 min.

### Audit trail

- Cloudflare Zero Trust dashboard → **Logs → Access** mostra todos os hits
  ao service token (timestamp, IP origem, success/fail).
- Postgres `whatsapp_tasks` guarda toda conversa (mensagem + resposta).
  NUNCA delete. Cleanup so de tasks `error/timeout` > 30d.

### Quando algo der errado

| Sintoma | Causa provavel | Acao |
|---------|----------------|------|
| Render WhatsAppAuthError 403 | service token expirou ou foi removido | Recriar service token CF, atualizar Render env vars |
| Tunnel offline | systemctl cloudflared down | `sudo systemctl restart cloudflared` |
| WhatsApp banido | Baileys flagged | Migrar para Cloud API oficial (refator) |
| Latencia > 30s | Render → CF → WSL2 tem overhead | Considerar TEAMS_DEFAULT_MODEL=opus-4-7 → sonnet-4-6 |

---

## Migracao futura — WhatsApp Cloud API

Quando Baileys virar gargalo (ban risk, ou volume > 1000 msgs/dia),
migrar para Cloud API oficial Meta. Refator estimado: 1-2 dias:

1. Substituir plugin nacom-bridge por webhook handler em `bot_routes.py`
2. Configurar Meta Business Account + numero dedicado
3. Validar webhook na Meta (token + signature)
4. Substituir helper `send_whatsapp` por chamada Graph API
5. Desativar tunnel + cloudflared (nao precisa mais — webhooks Meta
   chegam direto no Render)

Ver: https://developers.facebook.com/docs/whatsapp/cloud-api
