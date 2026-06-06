<!-- doc:meta
tipo: explanation
camada: L3
sot_de: —
hub: docs/superpowers/specs/INDEX.md
superseded_by: —
atualizado: 2026-06-06
-->
# Lojas HORA — Notificação WhatsApp de NF emitida e pedido confirmado (réplica do fluxo N8N)

> **Papel:** spec de design da feature que replica, dentro do módulo **Lojas HORA**, o fluxo N8N em que toda **NFe emitida** e todo **pedido confirmado** dispara mensagem em um **grupo único de vendas** no WhatsApp **e na DM do vendedor**. A NF vai com o **PDF da DANFE anexado**. Domínio: módulo HORA (NÃO a integração TagPlus da Nacom).

## Indice

- [Contexto](#contexto)
- [Histórico — correção de domínio](#histórico--correção-de-domínio)
- [Decisões aprovadas](#decisões-aprovadas)
- [Estado atual (fatos com fonte)](#estado-atual-fatos-com-fonte)
- [Arquitetura](#arquitetura)
- [Componentes](#componentes)
- [Formato das mensagens](#formato-das-mensagens)
- [Pré-requisitos operacionais](#pré-requisitos-operacionais)
- [Erros e edge cases](#erros-e-edge-cases)
- [Testes](#testes)

## Contexto

O TagPlus da **Lojas HORA** emite as NFes das vendas das lojas (a HORA é a emitente). Um workflow N8N escutava os webhooks do TagPlus da HORA e notificava o vendedor no WhatsApp a cada NF/pedido. Esta feature migra esse comportamento para dentro do sistema, dentro do módulo HORA (fronteira estrita, prefixo `hora_`).

A ponta de **envio** (`app.utils.whatsapp_notify.send_whatsapp`, com suporte a anexo base64) é genérica e reusada. A ponta de **recepção** já existe na HORA: o webhook `POST /tagplus/webhook` enfileira no RQ (`hora_nfe`) e o `WebhookHandler` processa `nfe_aprovada`.

## Histórico — correção de domínio

A 1ª implementação foi feita por engano na **integração TagPlus da Nacom** (`app/integracoes/tagplus/`) — domínio errado (tela desacoplada no menu Consultas, auth genérica, badges fora do padrão). Foi **revertida** (commit `revert(tagplus)`), preservando apenas o `send_whatsapp` com anexo. Esta spec descreve a implementação **correta**, no módulo HORA.

## Decisões aprovadas

1. **Domínio:** módulo Lojas HORA (`app/hora/`), não Nacom.
2. **Gatilhos:** **NF aprovada** (webhook `nfe_aprovada`) + **pedido confirmado** (transição para `CONFIRMADO`).
3. **Destino:** **grupo único** de vendas + **DM do vendedor** (best-effort; fallback só-grupo).
4. **NF com PDF da DANFE anexado**; pedido sem PDF (não é documento fiscal).
5. **Auth:** padrão HORA — `require_hora_perm('tagplus', ...)`; webhook valida `X-Hub-Secret` por conta (já existente).
6. **Processamento:** job na fila RQ `hora_nfe` (já roda em PROD); best-effort (não quebra o fluxo principal).

## Estado atual (fatos com fonte)

- Webhook HORA: `POST /tagplus/webhook` (`app/hora/routes/tagplus_routes.py:909`) valida `X-Hub-Secret` por `HoraTagPlusConta` e enfileira na fila `hora_nfe` → `WebhookHandler.processar` (eventos `nfe_aprovada`/`denegada`/`cancelada`).
- `WebhookHandler._handle_aprovada` (`app/hora/services/tagplus/webhook_handler.py`) atualiza a venda quando a NFe é aprovada — ponto natural do gatilho de NF.
- `confirmar_venda` (`app/hora/services/venda_service.py:971`) seta `VENDA_STATUS_CONFIRMADO` (`:994`) — ponto do gatilho de pedido.
- `HoraVenda`: `id`, `nome_cliente`, `valor_total`, `vendedor` (nome), `loja` (→`.nome`), `itens` (→`item.moto`: `numero_chassi`, `cor`, `modelo.nome_modelo`).
- `HoraTagPlusNfeEmissao`: `venda_id`, `tagplus_nfe_id`, `numero_nfe`, `chave_44`, relationship `venda`.
- DANFE PDF: `ApiClient(conta).get('/nfes/pdf/recibo_a4/{tagplus_nfe_id}')` → `.content`.
- Vendedor→telefone: `HoraVenda.vendedor` casado com `usuarios.vendedor_vinculado`/`nome` + `whatsapp_autorizado=True` + `status='ativo'` + `telefone` (padrão HORA, `vendas.py:238`).
- Fila `hora_nfe` roda em PROD (`worker_render.py:143`, `start_worker_render.sh:301`) — alta prioridade.

## Arquitetura

```
NFe aprovada (webhook hora_nfe → WebhookHandler._handle_aprovada)
   └─ apos commit → enfileirar_notificacao('NFE', emissao.id)   [best-effort]
Pedido CONFIRMADO (venda_service.confirmar_venda)
   └─ apos commit → enfileirar_notificacao('PEDIDO', venda.id)  [best-effort]
        │
        ▼  (job na fila hora_nfe)
   processar_notificacao(registro_id)
     - busca HoraVenda (+ HoraTagPlusNfeEmissao se NFE)
     - formata texto (WhatsApp-friendly)
     - resolve vendedor (usuarios) → telefone DM
     - [NFE] baixa DANFE via ApiClient → base64
     - send_whatsapp(GRUPO, txt, anexo) + send_whatsapp(VENDEDOR, txt, anexo)
     - grava status (ENVIADO/PARCIAL/ERRO/IGNORADO) + flags
```

Dedupe por `UNIQUE (tipo, ref_id)` na tabela `hora_tagplus_notificacao_whatsapp`. Idempotente por destino (reenvio não duplica destino já entregue).

## Componentes

| Arquivo | Papel |
|---|---|
| `app/hora/models/tagplus.py` | `HoraTagPlusNotificacaoWhatsapp` (dedupe/auditoria) |
| `scripts/migrations/hora_45_tagplus_notificacao_whatsapp.{py,sql}` | DDL dual |
| `app/hora/services/tagplus/notificacao_whatsapp.py` | `enfileirar_notificacao` / `processar_notificacao` / `reenfileirar` / `_resolver_vendedor` / formatadores / `_baixar_danfe_pdf` |
| `app/hora/workers/emissao_nfe_worker.py` | job `processar_notificacao(registro_id)` |
| `app/hora/services/tagplus/webhook_handler.py` | gatilho NF (`_disparar_notificacao_nfe_safe`) |
| `app/hora/services/venda_service.py` | gatilho pedido (em `confirmar_venda`) |
| `app/hora/routes/tagplus_routes.py` | rotas `/hora/tagplus/notificacoes` + reenviar (`require_hora_perm`) |
| `app/templates/hora/tagplus/notificacoes.html` | tela (padrão HORA: `hora/base.html`) |
| `app/templates/_sidebar.html` | link no grupo Faturamento (TagPlus) HORA |
| `app/utils/whatsapp_notify.py` | `send_whatsapp` com anexo base64 (reuso genérico) |

Env: `HORA_TAGPLUS_NOTIFY_GROUP_JID` (grupo único) + `HORA_TAGPLUS_NOTIFY_ENABLED` (kill switch) + reuso `OPENCLAW_GATEWAY_*`.

## Formato das mensagens

WhatsApp-friendly (`*bold*`, emojis, listas; sem tabela markdown). NF: `🧾 *NF emitida — Nº {numero}*` + cliente + vendedor + valor + loja + chave + itens (chassi · modelo) + **PDF anexado**. Pedido: `🛒 *Novo pedido confirmado — Nº {id}*` + cliente + vendedor + valor + loja + itens.

## Pré-requisitos operacionais

1. Migration em PROD: `hora_45_tagplus_notificacao_whatsapp.sql`.
2. Env `HORA_TAGPLUS_NOTIFY_GROUP_JID` (JID `...@g.us`) + `OPENCLAW_GATEWAY_*`.
3. Webhook TagPlus HORA já cadastrado (reusa o `/tagplus/webhook` existente — sem novo cadastro; o evento `nfe_aprovada` já chega).
4. Vendedores em `usuarios` com `telefone` + `whatsapp_autorizado=True` + `vendedor_vinculado`/`nome` batendo com `HoraVenda.vendedor` (senão fallback só-grupo).

## Erros e edge cases

| Cenário | Tratamento |
|---|---|
| Vendedor não resolvido | só grupo; `enviado_vendedor=NULL`; status `ENVIADO` |
| Grupo OK + vendedor falha | `PARCIAL`; reenvio re-tenta só o pendente |
| PDF indisponível | envia só texto; `anexou_pdf=false` |
| Kill switch off | `IGNORADO`, nada enviado |
| Gatilho falha | best-effort: loga, NÃO quebra webhook/confirmação |
| `GROUP_JID` ausente | `ERRO` (config) |

## Testes

`tests/hora/test_notificacao_whatsapp_model.py` (2), `test_notificacao_whatsapp_service.py` (4), `test_notificacao_gatilhos.py` (4), `test_notificacao_tela.py` (4), `tests/test_whatsapp_notify_anexo.py` (2) — 16 testes determinísticos (mock de `send_whatsapp`/`ApiClient`, sem rede).
