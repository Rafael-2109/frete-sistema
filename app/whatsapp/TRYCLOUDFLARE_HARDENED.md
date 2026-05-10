# TryCloudflare Hardened — Setup sem dominio Cloudflare

Alternativa ao `CLOUDFLARE_TUNNEL.md` que NAO exige dominio CF. Usa
TryCloudflare quick tunnels (URL volatil) com 4 camadas custom de
seguranca + auto-update da URL no Render via API.

## Quando usar este caminho

- Voce NAO tem dominio Cloudflare e nao quer registrar (R$ 6/ano)
- Aceita ~9-30min/mes de downtime quando URL volatil mudar (PC reboot, etc.)
- Aceita complexidade extra de manter 3 services systemd (cloudflared,
  hmac proxy, url watcher)

Se preferir setup mais simples → `CLOUDFLARE_TUNNEL.md` (com dominio).

## Arquitetura final

```
Render (sistema-fretes.onrender.com)
   │  POST <OPENCLAW_GATEWAY_URL><PATH_PREFIX>/api/tools/invoke
   │  headers:
   │    Authorization: Bearer <OPENCLAW_GATEWAY_TOKEN>
   │    X-Timestamp: <epoch-utc>
   │    X-Nonce:     <uuid4-hex>
   │    X-Signature: <HMAC-SHA256(secret, ts||nonce||method||path||body)>
   │  body: JSON canonico
   ↓
TryCloudflare edge (URL volatil tipo random-name-1234.trycloudflare.com)
   │  TLS termination + roteamento via Cloudflare network
   ↓
cloudflared (systemd user, WSL2)
   │  Tunnel persistente outbound
   ↓
HMAC proxy 127.0.0.1:18790 (systemd user, WSL2)
   │  4 validacoes em ordem:
   │    1. Path prefix bate
   │    2. X-Timestamp dentro de janela 60s
   │    3. X-Signature valida
   │    4. X-Nonce nao usado nos ultimos 120s (anti-replay)
   ↓
Gateway OpenClaw 127.0.0.1:18789 (bind=loopback)
   │  Valida Authorization Bearer
   ↓
Baileys -> WhatsApp

URL watcher (systemd user, WSL2):
   journalctl -u cloudflared | grep trycloudflare.com
   ↓ (URL mudou?)
   PUT https://api.render.com/v1/services/<id>/env-vars
   ↓
   Render redeploy automatico ~9min
```

Camadas de seguranca:
1. **Path prefix secreto** — scanners aleatorios dropam em 404
2. **HMAC signature** — sem secret, body intacto e timestamp valido nao
   da pra forjar (mesmo com URL+token vazados)
3. **Anti-replay nonce + ts window** — request capturado nao pode ser repetido
4. **Bearer token gateway** — ultima camada no proprio gateway

## Pre-requisitos

- WSL2 com systemd habilitado (Ubuntu 22.04+ tem por padrao)
- `cloudflared` instalado (ja feito: `~/.local/bin/cloudflared`)
- Render API key (criar em https://dashboard.render.com/u/account/api-keys)
- Service IDs do Render (os 2 services: web + worker-atacadao)

## Passo 1 — Gerar segredos (uma vez)

```bash
# HMAC secret (64+ chars base64)
HMAC_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")
echo "HMAC_SECRET=$HMAC_SECRET"

# Path prefix obfuscado (8 chars random)
PATH_PREFIX="/$(python3 -c "import secrets,string;print(''.join(secrets.choice(string.ascii_lowercase+string.digits) for _ in range(8)))")"
echo "PATH_PREFIX=$PATH_PREFIX"

# Render API key — voce gera no dashboard
echo "RENDER_API_KEY=rnd_xxx" # cole o valor
```

Anote os 3 valores. Vamos usar nos passos seguintes.

## Passo 2 — Adicionar segredos no .env local

Adicione em `/home/rafaelnascimento/projetos/frete_sistema/.env`:

```bash
# Hardened TryCloudflare
OPENCLAW_HMAC_SECRET=<HMAC_SECRET do passo 1>
OPENCLAW_PATH_PREFIX=<PATH_PREFIX do passo 1, com / inicial>
```

## Passo 3 — Salvar Render API key local (modo 600)

```bash
mkdir -p ~/.openclaw
cat > ~/.openclaw/render.env << EOF
RENDER_API_KEY=<sua-key-do-passo-1>
RENDER_SERVICE_IDS=srv-d13m38vfte5s738t6p60,srv-d2muidggjchc73d4segg
OPENCLAW_PATH_PREFIX=<PATH_PREFIX do passo 1>
EOF
chmod 600 ~/.openclaw/render.env
```

## Passo 4 — Adicionar segredos no Render env vars

Adicione em **ambos** services (web `srv-d13m...` e worker `srv-d2mu...`):

```
OPENCLAW_HMAC_SECRET=<mesmo valor do passo 1>
OPENCLAW_PATH_PREFIX=<mesmo valor do passo 1>
```

`OPENCLAW_GATEWAY_URL` ainda fica vazio/placeholder por enquanto — o
watcher vai preencher automaticamente quando o tunnel subir.

## Passo 5 — Subir HMAC proxy (systemd user)

```bash
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/openclaw-hmac-proxy.service << 'EOF'
[Unit]
Description=OpenClaw HMAC Proxy (gateway 18789 wrapper)
After=network.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/rafaelnascimento/projetos/frete_sistema/scripts/openclaw_hmac_proxy.py
Environment=OPENCLAW_HMAC_SECRET=<HMAC_SECRET do passo 1>
Environment=OPENCLAW_PATH_PREFIX=<PATH_PREFIX do passo 1>
Environment=OPENCLAW_PROXY_PORT=18790
Environment=OPENCLAW_GATEWAY_PORT=18789
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable openclaw-hmac-proxy
systemctl --user start openclaw-hmac-proxy
systemctl --user status openclaw-hmac-proxy
```

Logs: `journalctl --user -u openclaw-hmac-proxy -f`

Teste local (deve aceitar com headers corretos, rejeitar sem):

```bash
# Sem headers HMAC (deve dar 401)
curl -sS -i -X POST http://127.0.0.1:18790${PATH_PREFIX}/api/tools/invoke \
  -H "Authorization: Bearer $OPENCLAW_GATEWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{}'
# Esperado: HTTP/1.0 401 + {"error":"deny"}

# Path errado (deve dar 404)
curl -sS -i http://127.0.0.1:18790/api/tools/invoke
# Esperado: HTTP/1.0 404 + {"error":"deny"}
```

## Passo 6 — Subir cloudflared TryCloudflare (systemd user)

```bash
cat > ~/.config/systemd/user/cloudflared-quick.service << 'EOF'
[Unit]
Description=Cloudflare Quick Tunnel (TryCloudflare) -> HMAC proxy
After=network-online.target openclaw-hmac-proxy.service
Wants=network-online.target

[Service]
Type=simple
ExecStart=%h/.local/bin/cloudflared tunnel --url http://127.0.0.1:18790 --no-autoupdate
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable cloudflared-quick
systemctl --user start cloudflared-quick
```

Aguarde 10s e veja a URL gerada:

```bash
journalctl --user -u cloudflared-quick -n 100 | grep trycloudflare.com
# Output esperado: linha com https://random-words-1234.trycloudflare.com
```

## Passo 7 — Subir URL watcher (systemd user)

```bash
cat > ~/.config/systemd/user/openclaw-url-watcher.service << 'EOF'
[Unit]
Description=OpenClaw URL Watcher (TryCloudflare -> Render env var)
After=cloudflared-quick.service
Wants=cloudflared-quick.service

[Service]
Type=simple
EnvironmentFile=%h/.openclaw/render.env
ExecStart=/usr/bin/python3 /home/rafaelnascimento/projetos/frete_sistema/scripts/openclaw_url_watcher.py
Environment=CLOUDFLARED_LOG_CMD=journalctl --user -u cloudflared-quick -n 200 --no-pager
Environment=CHECK_INTERVAL_SEC=30
Restart=always
RestartSec=10

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable openclaw-url-watcher
systemctl --user start openclaw-url-watcher
```

Logs: `journalctl --user -u openclaw-url-watcher -f`

Esperado nas primeiras 30s:
```
URL mudou: <nada> -> https://random-words-1234.trycloudflare.com
render PATCH ok service=srv-d13m38vfte5s738t6p60 status=200
render PATCH ok service=srv-d2muidggjchc73d4segg status=200
Render env atualizado em todos os services. Redeploy ~9min.
```

## Passo 8 — Habilitar systemd user lingering

Garante que os services rodam mesmo sem voce logado no shell:

```bash
sudo loginctl enable-linger rafaelnascimento
```

(precisa sudo uma vez)

## Passo 9 — Aguardar Render redeploy e testar

```bash
# Esperar deploy (acompanhe no dashboard ou via curl):
watch -n 30 'curl -sS https://sistema-fretes.onrender.com/api/whatsapp/health'

# Quando voltar 200 com gateway_configured=true (apos novo deploy completar):
# Mande mensagem WhatsApp pro proprio numero (+5511991642998).
```

Sequencia esperada no smoke test:
1. Plugin nacom-bridge: POST inbound → Render → 202
2. Render Agent SDK processa
3. Render: helper assina HMAC + chama OPENCLAW_GATEWAY_URL + PATH_PREFIX
4. cloudflared: encaminha → 127.0.0.1:18790 (HMAC proxy)
5. HMAC proxy: valida 4 camadas → 127.0.0.1:18789 (gateway)
6. Gateway: envia mensagem WhatsApp

## Quando algo der errado

| Sintoma | Causa provavel | Acao |
|---------|----------------|------|
| URL nao detectada pelo watcher | log_cmd retornando vazio | `journalctl --user -u cloudflared-quick` manualmente; se vazio, ajustar `CLOUDFLARED_LOG_CMD` |
| Render PATCH 401 | RENDER_API_KEY invalido/expirado | Recriar key no dashboard, atualizar `~/.openclaw/render.env`, reiniciar watcher |
| Proxy 401 signature_mismatch | secret divergente entre Render e proxy | Conferir `OPENCLAW_HMAC_SECRET` em ambos lados |
| Proxy 401 timestamp_out_of_window | clock skew > 60s entre Render e WSL2 | `sudo timedatectl set-ntp on` na WSL2 |
| Proxy 401 nonce_replayed | retry duplo do helper | Helper gera UUID novo a cada call — se repete eh bug; investigar |
| Bot offline > 9min em PC reboot | Watcher demora ate 30s + redeploy 9min | Esperado. Para reduzir: reduzir CHECK_INTERVAL_SEC |

## Token rotation

| Token | Frequencia | Como rotacionar |
|-------|------------|-----------------|
| `OPENCLAW_HMAC_SECRET` | 90 dias | Gerar novo, atualizar Render env vars + systemd unit do proxy + restart proxy. ATENCAO: se rotacionar Render antes do proxy, requests vao falhar 401 ate proxy recarregar. |
| `OPENCLAW_GATEWAY_TOKEN` | 90 dias | Rotacionar no gateway + atualizar Render env vars |
| `OPENCLAW_PATH_PREFIX` | 6 meses | Mudar em ambos lados; restart proxy |
| `RENDER_API_KEY` | 6 meses ou em saida de equipe | Recriar key, atualizar `~/.openclaw/render.env`, reiniciar watcher |

## Comparacao com setup com dominio CF (CLOUDFLARE_TUNNEL.md)

| Aspecto | Hardened TryCloudflare | Com dominio CF + Access |
|---------|------------------------|-------------------------|
| Custo $/ano | R$ 0 | R$ 6-50 (TLD descartavel ate `.com.br`) |
| Setup inicial | ~1h (3 services systemd + script monitor) | ~30min |
| Manutencao continua | Watcher script + 3 services pra monitorar | Apenas tunnel |
| Camadas auth | 4 (path, HMAC, ts/nonce, Bearer) | 3 (CF Access, Bearer, TLS) |
| Audit trail edge | Nao (so logs locais) | Sim (CF Access logs) |
| Downtime/mes | ~9-30min em reboots | ~0 |
| Build minutes Render gastos | Aumentado (re-deploys) | Normal |

Migracao para dominio CF eh trivial: registrar dominio, configurar named tunnel,
remover services TryCloudflare/watcher, reverter helper para usar CF Access
em vez de HMAC.

## Migracao futura — WhatsApp Cloud API

Mesma logica do `CLOUDFLARE_TUNNEL.md` final: substituir Baileys por
Cloud API oficial Meta quando volume justificar (ban risk, > 1000 msgs/dia).
