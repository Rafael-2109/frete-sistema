<!-- doc:meta
tipo: how-to
camada: L3
sot_de: —
hub: docs/superpowers/plans/INDEX.md
superseded_by: —
atualizado: 2026-06-06
-->
# Lojas HORA — Notificação WhatsApp (NF/pedido) — Implementation Plan (executado)

> **Papel:** registro do plano TDD executado para a notificação WhatsApp do módulo HORA. Implementa [2026-06-06-hora-tagplus-notificacao-whatsapp-design.md](../specs/2026-06-06-hora-tagplus-notificacao-whatsapp-design.md). Status: **implementado e testado** (16 testes verdes).

## Indice

- [Tarefas executadas](#tarefas-executadas)
- [Setup de testes](#setup-de-testes)
- [Pré-requisitos para PROD](#pré-requisitos-para-prod)

## Tarefas executadas

**H1 — Model + migration** (`feat(hora): model + migration HoraTagPlusNotificacaoWhatsapp`)
- `HoraTagPlusNotificacaoWhatsapp` em `app/hora/models/tagplus.py` (tipo, ref_id, numero, cliente_nome, vendedor_nome, loja_nome, valor, enviado_grupo, enviado_vendedor, status, erro, tentativas, anexou_pdf, datas; UNIQUE `(tipo, ref_id)`).
- Migration dual `scripts/migrations/hora_45_tagplus_notificacao_whatsapp.{py,sql}` (idempotente).
- Teste: `tests/hora/test_notificacao_whatsapp_model.py` (2).

**H2 — Service** (`feat(hora): service de notificacao WhatsApp`)
- `app/hora/services/tagplus/notificacao_whatsapp.py`: `enfileirar_notificacao(tipo, ref_id)` (dedupe + enqueue `hora_nfe`), `processar_notificacao(registro_id)` (busca + formata + resolve vendedor + PDF + envia grupo/vendedor), `reenfileirar(registro_id)`, `_resolver_vendedor` (usuarios), `_formatar_nfe`/`_formatar_pedido`, `_baixar_danfe_pdf` (ApiClient), `_enviar_para_destinos` (idempotente por destino). Kill switch `HORA_TAGPLUS_NOTIFY_ENABLED`.
- Teste: `tests/hora/test_notificacao_whatsapp_service.py` (4).

**H3 — Gatilhos + worker** (`feat(hora): gatilhos de notificacao + worker job`)
- Worker job `processar_notificacao(registro_id)` em `app/hora/workers/emissao_nfe_worker.py`.
- Gatilho NF: `WebhookHandler.processar` chama `_disparar_notificacao_nfe_safe(emissao.id)` após o commit, só p/ `nfe_aprovada` (best-effort).
- Gatilho pedido: `confirmar_venda` chama `enfileirar_notificacao('PEDIDO', venda.id)` após o commit (best-effort).
- Teste: `tests/hora/test_notificacao_gatilhos.py` (4).

**H4 — Tela + menu + auth** (`feat(hora): tela de notificacoes WhatsApp + reenvio + menu`)
- Rotas `/hora/tagplus/notificacoes` (`require_hora_perm('tagplus','ver')`) + reenviar (`'editar'`) em `app/hora/routes/tagplus_routes.py`.
- Template `app/templates/hora/tagplus/notificacoes.html` (extends `hora/base.html`, badges/botões do padrão HORA, CSRF no form).
- Link no menu HORA (grupo Faturamento TagPlus) em `_sidebar.html`.
- Teste: `tests/hora/test_notificacao_tela.py` (4).

**Reuso preservado da tentativa anterior:** `app/utils/whatsapp_notify.py` (`send_whatsapp` com anexo base64) + `tests/test_whatsapp_notify_anexo.py` (2).

## Setup de testes

```bash
source .venv/bin/activate   # DATABASE_URL vem do .env (Postgres local)
python scripts/migrations/hora_45_tagplus_notificacao_whatsapp.py
pytest tests/hora/test_notificacao_whatsapp_model.py tests/hora/test_notificacao_whatsapp_service.py \
       tests/hora/test_notificacao_gatilhos.py tests/hora/test_notificacao_tela.py \
       tests/test_whatsapp_notify_anexo.py -q
```
Gotcha: a tabela `hora_tagplus_notificacao_whatsapp` em local acumula resíduo de teste se o processo abortar no teardown (erro de shutdown do Sentry). `DELETE FROM hora_tagplus_notificacao_whatsapp` limpa antes de re-rodar.

## Pré-requisitos para PROD

1. Aplicar `hora_45_tagplus_notificacao_whatsapp.sql` no Render Shell.
2. Env: `HORA_TAGPLUS_NOTIFY_GROUP_JID=<jid>@g.us` (+ `OPENCLAW_GATEWAY_*` já existentes; `HORA_TAGPLUS_NOTIFY_ENABLED` opcional).
3. Vendedores em `usuarios` com `telefone` + `whatsapp_autorizado=True` + `vendedor_vinculado`/`nome` = `HoraVenda.vendedor`.
4. O webhook TagPlus HORA já existente (`/tagplus/webhook`) já entrega `nfe_aprovada` — nenhum cadastro novo.
