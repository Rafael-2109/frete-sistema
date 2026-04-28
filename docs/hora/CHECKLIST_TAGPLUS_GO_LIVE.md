# Checklist TagPlus — Go-Live

## A. TagPlus (portal + ERP)

- [X] **A1** — ERP TagPlus: anotar **código** (string) dos produtos (1 por modelo HORA).
  O campo no POST /nfes aceita o código string (não o ID inteiro).
- [ ] **A2** — Coletar IDs das formas de pagamento (PIX, CARTAO_CREDITO, DINHEIRO).
  - **Caminho rápido**: usar botão **"Listar do TagPlus (via API)"** em `/hora/tagplus/conta/formas-pagamento` (item D2).
  - **Fallback** (se a API não expor): emitir 1 NFe de teste no portal com cada forma e consultar `GET /nfes/{id}` — `faturas[].id_forma_pagamento` traz o ID inteiro.
- [X] **A3** — `developers.tagplus.com.br`: criar app OAuth
- [X] **A4** — App OAuth: setar Redirect URI = `https://sistema-fretes.onrender.com/hora/tagplus/conta/callback`
- [X] **A5** — Scopes: `write:nfes read:clientes write:clientes read:produtos`
  - **Importante**: scopes são enviados em `?scope=` no fluxo OAuth (`/authorize`), **não** configurados no portal `developers.tagplus.com.br`. Edite o campo "Scopes" em `/hora/tagplus/conta` e clique "Re-autorizar OAuth" para ampliar.
  - *(scope atual confirmado funcionando — probe `GET /produtos` retornou 200)*
  - **Para destravar listagem de formas de pagamento** (botão em D2): adicionar `read:formas_pagamento` (ou variante `read:formas_pgto`) ao scope e re-autorizar.
- [X] **A6** — App OAuth: anotar Client ID + Client Secret - HORA_CLIENT_ID e HORA_CLIENT_SECRET

## B. Render (deploy + env)

- [X] **B1** — Gerar Fernet key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- [X] **B2** — Backup da Fernet key em local seguro (1Password)
- [X] **B3** — Render web service: setar env `HORA_TAGPLUS_ENC_KEY` = valor gerado em B1
- [X] **B4** — Render `sistema-fretes-worker-atacadao`: setar mesmo `HORA_TAGPLUS_ENC_KEY`
- [X] **B5** — Push do commit inicial `484d27fd` para `main` (deploy automático)
- [X] **B6** — Aguardar deploy verde do web + worker
- [X] **B7** — Render Shell (web): `python scripts/migrations/hora_18_tagplus.py`
- [X] **B8** — Conferir saída `[AFTER]` com 5 tabelas `existe`
- [X] **B9** — Render Shell (web): `python scripts/migrations/hora_19_tagplus_produto_id_string.py`
  (troca `tagplus_produto_id` INTEGER → VARCHAR(50). Conferir `[AFTER]` com `type=character varying length=50`)
- [X] **B10** — Push do commit `50c80ba5` (correções go-live: nfe_denegada, CFOP 5.403, produto_id string, UX webhook secret, probe checklist) → aguardar deploy verde

## C. Sistema — configuração inicial

- [X] **C1** — Conceder permissão `tagplus.ver` + `tagplus.editar` ao usuário admin TagPlus
- [X] **C2** — Acessar `/hora/tagplus/conta`
- [X] **C3** — Preencher Client ID + Client Secret (de A6); ambiente = Produção; salvar
- [X] **C4** — Copiar **Webhook Secret** mostrado no card
- [X] **C5** — TagPlus: cadastrar webhook
  - URL: `https://sistema-fretes.onrender.com/hora/tagplus/webhook`
  - X-Hub-Secret: valor de C4
  - Eventos: `nfe_aprovada`, `nfe_denegada`, `nfe_cancelada`
  - Nota: TagPlus nao expoe `nfe_rejeitada` na lista publica (ver `scripts/webhook.md`).
    `nfe_denegada` cobre rejeicoes SEFAZ; reconciliacao 30min trata casos perdidos.
- [X] **C6** — Clicar **Autorizar OAuth** → autenticar no TagPlus → confirmar tela de sucesso
- [X] **C7** — Voltar a `/hora/tagplus/conta`: badge **Token OAuth** verde

## D. Mapeamentos

- [ ] **D1** — `/hora/tagplus/conta/mapeamento`: preencher **código string** (de A1) para cada um dos 19 modelos
  - Campo é texto (até 50 chars), não inteiro
  - CFOP padrão `5.403` (intra) — builder ajusta para `6.403` se UF do cliente diferir
- [ ] **D2** — `/hora/tagplus/conta/formas-pagamento`: preencher IDs de PIX, CARTAO_CREDITO, DINHEIRO
  - Clicar **"Listar do TagPlus (via API)"** para puxar a lista direto
  - Se a API não expor: usar fallback descrito em A2

## E. Validação

- [ ] **E1** — `/hora/tagplus/conta/checklist`: todos os itens verdes
  - Após B10: probe é `GET /produtos (probe)` (não mais `/usuario_atual`)
  - Mapeamentos passam a `OK` quando D1 e D2 estiverem preenchidos
- [ ] **E2** — Smoketest: emitir NFe de venda real R$ 1,00 → status `APROVADA`
  - Validar: `chave_44` preenchido, `protocolo_aprovacao` preenchido, evento `NF_EMITIDA` registrado em `hora_moto_evento` por chassi
- [ ] **E3** — Cancelar NFe de teste → status `CANCELADA`
  - Validar: `cancelado_em` preenchido, evento `NF_CANCELADA` registrado por chassi
- [ ] **E4** — (opcional) Forçar denegação SEFAZ → webhook `nfe_denegada` → status `REJEITADA_SEFAZ` com `error_message` preenchido

## Rollback

Se algo travar em B/C: desativar conta em `/hora/tagplus/conta` (campo `ativo`), corrigir, reautorizar.

## Mudança de Scope OAuth

**Sim, qualquer mudança no campo "Scopes" exige re-autorização.**

Mecânica: scope é enviado em `?scope=` na URL `/authorize`. O token recebido na callback fica
travado naqueles scopes específicos. Para ampliar (ex.: adicionar `read:formas_pagamento`):

1. `/hora/tagplus/conta` → editar campo "Scopes" → Salvar.
2. Clicar **"Re-autorizar OAuth"** (gera novo `/authorize` com scope ampliado).
3. Confirmar autorização no portal TagPlus → callback gera novo token.
4. Token antigo vira inválido automaticamente após o `_save_token` reescrever a linha.

Refresh automático **não amplia scope** — só renova access_token dentro do scope que o
refresh_token original tem. Por isso, qualquer mudança de scope exige passar pelo
authorization code flow de novo.

## Esboço (preview de payload)

Disponível em **Faturamento → Esboço** (`/hora/tagplus/esboco`). Permite escolher uma
HoraVenda existente e ver o JSON exato do `POST /nfes` sem fazer chamada de rede. Útil para:
- Validar visualmente CFOP, destinatário, itens, faturas antes do go-live.
- Diagnosticar erros de mapeamento (modelo→produto, forma de pagamento, CPF) — `PayloadBuilderError`
  é capturado e exibido com código + sugestão.
- Comparar com o que o TagPlus aceita antes de submeter de verdade via `/hora/vendas/{id}/nfe`.

## Após Go-Live

- Reconciliação automática roda a cada 30min (`reconciliar_emissoes_job` em `app/hora/workers/reconciliacao_worker.py`) — recupera webhooks perdidos.
- Auto-refresh de token OAuth é transparente (margem 5min antes de expirar) — não precisa intervir.
- `/hora/tagplus/emissoes` lista a fila de emissões com status para gestão.
