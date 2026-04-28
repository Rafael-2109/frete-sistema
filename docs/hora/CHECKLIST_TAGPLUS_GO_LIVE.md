# Checklist TagPlus — Go-Live

## A. TagPlus (portal + ERP)

- [ ] **A1** — ERP TagPlus: anotar IDs dos produtos (1 por modelo HORA)
- [ ] **A2** — ERP TagPlus: anotar IDs das formas de pagamento (PIX, CARTAO_CREDITO, DINHEIRO)
- [X] **A3** — `developers.tagplus.com.br`: criar app OAuth
- [X] **A4** — App OAuth: setar Redirect URI = `https://sistema-fretes.onrender.com/hora/tagplus/conta/callback`
- [ ] **A5** — App OAuth: solicitar scopes `write:nfes read:clientes write:clientes read:produtos`
- [X] **A6** — App OAuth: anotar Client ID + Client Secret - HORA_CLIENT_ID e HORA_CLIENT_SECRET

## B. Render (deploy + env)

- [X] **B1** — Gerar Fernet key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`
- [X] **B2** — Backup da Fernet key em local seguro (1Password)
- [X] **B3** — Render web service: setar env `HORA_TAGPLUS_ENC_KEY` = valor gerado em B1
- [X] **B4** — Render `sistema-fretes-worker-atacadao`: setar mesmo `HORA_TAGPLUS_ENC_KEY`
- [X] **B5** — Push do commit `484d27fd` para `main` (deploy automático)
- [X] **B6** — Aguardar deploy verde do web + worker
- [X] **B7** — Render Shell (web): `python scripts/migrations/hora_18_tagplus.py`
- [X] **B8** — Conferir saída `[AFTER]` com 5 tabelas `existe`
- [ ] **B9** — Render Shell (web): `python scripts/migrations/hora_19_tagplus_produto_id_string.py`
  (troca `tagplus_produto_id` INTEGER → VARCHAR(50). Conferir `[AFTER]` com `type=character varying length=50`)

## C. Sistema — configuração inicial

- [X] **C1** — Conceder permissão `tagplus.ver` + `tagplus.editar` ao usuário admin TagPlus
- [X] **C2** — Acessar `/hora/tagplus/conta`
- [X] **C3** — Preencher Client ID + Client Secret (de A6); ambiente = Produção; salvar
- [ ] **C4** — Copiar **Webhook Secret** mostrado no card
- [ ] **C5** — TagPlus: cadastrar webhook
  - URL: `https://sistema-fretes.onrender.com/hora/tagplus/webhook`
  - X-Hub-Secret: valor de C4
  - Eventos: `nfe_aprovada`, `nfe_denegada`, `nfe_cancelada`
  - Nota: TagPlus nao expoe `nfe_rejeitada` na lista publica (ver `scripts/webhook.md`).
    `nfe_denegada` cobre rejeicoes SEFAZ; reconciliacao 30min trata casos perdidos.
- [ ] **C6** — Clicar **Autorizar OAuth** → autenticar no TagPlus → confirmar tela de sucesso
- [ ] **C7** — Voltar a `/hora/tagplus/conta`: badge **Token OAuth** verde

## D. Mapeamentos

- [ ] **D1** — `/hora/tagplus/conta/mapeamento`: preencher `tagplus_produto_id` para cada modelo (de A1)
- [ ] **D2** — `/hora/tagplus/conta/formas-pagamento`: preencher IDs de PIX, CARTAO_CREDITO, DINHEIRO (de A2)

## E. Validação

- [ ] **E1** — `/hora/tagplus/conta/checklist`: todos os itens verdes
- [ ] **E2** — Smoketest: emitir NFe de venda real R$ 1,00 → status `APROVADA`
- [ ] **E3** — Cancelar NFe de teste → status `CANCELADA`

## Rollback

Se algo travar em B/C: desativar conta em `/hora/tagplus/conta` (campo `ativo`), corrigir, reautorizar.
