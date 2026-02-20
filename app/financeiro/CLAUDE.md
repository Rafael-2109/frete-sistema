# Financeiro — Guia de Desenvolvimento

**66 arquivos** | **40K LOC** | **Atualizado**: 20/02/2026

Contas a receber/pagar, extratos bancarios, conciliacao Odoo, CNAB 400, comprovantes e baixas.

> Campos de tabelas: `.claude/skills/consultando-sql/schemas/tables/{tabela}.json`
> Gotchas completos (80+): `app/financeiro/GOTCHAS.md`

---

## Estrutura

```
app/financeiro/
  ├── routes/       # 18 blueprints (financeiro_bp + cnab400_bp)
  ├── services/     # 26 services (matching, conciliacao, sync, parsers)
  ├── workers/      # 8 RQ jobs (batch processing via Redis)
  ├── parsers/      # 4 parsers (PIX Sicoob, dispatcher)
  ├── models.py     # 40+ models (117K LOC — MAIOR arquivo do projeto)
  ├── constants.py  # Contas contabeis, journals, mapeamentos Odoo
  └── parcela_utils.py  # parcela_to_int/str/odoo (VARCHAR↔INTEGER)
```

---

## Armadilhas que CAUSAM BUGS

### A1: status_match != status em ExtratoItem (e BaixaPagamentoItem)
DOIS campos de status independentes:
- `status_match`: resultado do matching (PENDENTE|MATCH_ENCONTRADO|MULTIPLOS_MATCHES|SEM_MATCH)
- `status`: ciclo de vida (PENDENTE|APROVADO|CONCILIANDO|CONCILIADO|ERRO)
Filtrar "pendentes de conciliacao" = `status`, NAO `status_match`.

### A2: Legacy FK vs M:N — dual binding de titulos
ExtratoItem vincula titulos por DOIS mecanismos:
- Legacy: `titulo_receber_id`/`titulo_pagar_id` (FK 1:1)
- M:N: `titulos_vinculados` via ExtratoItemTitulo (com valor_alocado)
Quando M:N ativo, FKs legacy sao LIMPOS. `tem_multiplos_titulos` retorna True para 1 titulo M:N.
**`titulo_receber_id IS NULL` NAO significa "sem titulo"** — verificar M:N tambem.

### A3: titulo_id — deprecado em ExtratoItem, ATIVO em BaixaPagamentoItem
`ExtratoItem.titulo_id` (1355): DEPRECADO. Usar `titulo_receber_id`/`titulo_pagar_id`.
`BaixaPagamentoItem.titulo_id` (1980): ATIVO — account.move.line ID do Odoo. NAO deprecar.

### A4: nf_cancelada e property N+1, NAO campo SQL
`ContasAReceber.nf_cancelada` faz query a FaturamentoProduto a cada acesso.
`to_dict()` chama — N registros = N queries extras.
Para filtrar em SQL: usar subquery `exists()` em FaturamentoProduto (ver contas_receber.py:99).

### A5: calcular_valor_titulo filtra previsto=False, to_dict soma TUDO
`calcular_valor_titulo()` soma abatimentos REALIZADOS (previsto=False).
`to_dict()` soma TODOS os abatimentos. Valores na UI divergem quando existem previstos.

### A6: valor_titulo e CALCULADO — chamar atualizar_valor_titulo()
Apos criar/editar/excluir abatimento, OBRIGATORIO chamar `conta.atualizar_valor_titulo()`.
Setar `valor_titulo` diretamente resulta em valor inconsistente.

### A7: Dois sistemas de baixa DISTINTOS
`baixas.py` = contas a RECEBER (upload Excel, BaixaTituloLote/Item, `/contas-receber/baixas/`)
`pagamentos_baixas.py` = contas a PAGAR (extrato banco, BaixaPagamentoLote/Item, `/contas-pagar/baixas/`)
Models, rotas e services completamente separados. Nomes similares, fluxos diferentes.

### A8: matches_candidatos e TEXT, nao JSONB
`ExtratoItem.matches_candidatos` (1368) e `BaixaPagamentoItem.matches_candidatos` (2000): TEXT.
Usar `set_matches_candidatos()`/`get_matches_candidatos()`. SEM `flag_modified`, SEM operadores JSON.
`snapshot_antes`/`snapshot_depois` em 3 models tambem sao TEXT com helpers.

### A9: Float vs Numeric misturados para valores monetarios
~25 campos Float (impreciso) vs ~11 Numeric(15,2) (exato). Mesma informacao em tipos diferentes:
`ExtratoItem.titulo_saldo_antes` = Float. `ExtratoItemTitulo.titulo_saldo_antes` = Numeric.
Comparar diretamente pode falhar.
**REGRA**: Novos campos monetarios DEVEM ser `Numeric(15,2)`. NAO usar Float para valores em R$.

### A10: Parcela VARCHAR em Contas*, INTEGER em Extrato*/Baixa*
`ContasAReceber.parcela` = VARCHAR(10) (pode ter "P3" de CNAB).
`ExtratoItem.titulo_parcela` = INTEGER.
JOIN direto falha. Usar `parcela_utils.py`: `parcela_to_int()`, `parcela_to_str()`, `parcela_to_odoo()`.

---

## Armadilhas Odoo

### O1: TRANSITORIA (22199) -> PENDENTES (26868) obrigatorio
Extrato Odoo usa conta TRANSITORIA. Trocar para PENDENTES via `_safe_write_statement_line()`
ANTES de reconciliar. Sem troca: erro contabil silencioso.

### O2: Write-off wizard ja posta E reconcilia
`account.payment.register` com juros automaticamente cria + posta + reconcilia.
NAO chamar `action_post()` nem `reconcile()` depois — double-posting.

### O3: amount_residual NEGATIVO para contas a pagar
Odoo retorna negativo. Sistema armazena `abs()`. Sempre comparar com abs().

### O4: Parcela 1 no Odoo pode ser 0 ou False
`l10n_br_cobranca_parcela` armazena integer 0 como `False`. Fallback: buscar `[0, False]`.

### O5: CNPJ formatado no Odoo: "XX.XXX.XXX/XXXX-XX"
Busca com digitos limpos retorna vazio. Para raiz: `"33.652.456"` (com pontos).

### O6: "cannot marshal None" = SUCESSO
Wizards Odoo retornam None. XML-RPC nao serializa → excecao. Operacao JA executou.
NAO fazer retry (duplica pagamento). NAO tratar como erro.

### O7: Bug desconto duplo — usar saldo_total, NAO balance
Odoo aplica desconto 2x em `balance`. `saldo_total` tem valor correto (1x).

### O8: Multi-company: pagamento na empresa do TITULO, nao do extrato
Titulo empresa CD + extrato empresa FB = payment na empresa CD.
Conta PENDENTES ponte inter-company.

### O9: draft -> write -> post (Safe Write)
Entries posted bloqueiam write. `button_draft` -> `write` -> `action_post`.
"cannot modify posted entry" = esqueceu `button_draft`.

### O10: Titulos 2000-01-01 sao fantasmas
`DATA_VENCIMENTO_IGNORAR = date(2000, 1, 1)`. Linhas duplicadas de desconto do Odoo.
No matching: agregar com NF real. Na baixa: corrigir antes.

### O11: button_draft REMOVE reconciliacao existente (corrigido 2026-02-18)
Chamar `button_draft` em move com linhas reconciliadas DESFAZ a reconciliacao.
Ordem correta: TODAS as escritas (conta, partner, rotulo) ANTES do reconcile.
Reconcile SEMPRE por ULTIMO. Usar metodo consolidado:
- `baixa_pagamentos_service.preparar_extrato_para_reconciliacao()` — publico, IDs raw (comprovantes)
- `extrato_conciliacao_service._preparar_extrato_para_reconciliacao()` — privado, ExtratoItem
NUNCA fazer as 3 operacoes (trocar conta, atualizar partner, atualizar rotulo) em chamadas separadas.
`_atualizar_campos_extrato()` esta DEPRECADO — NAO chamar apos reconcile.

### O12: account_id DEVE ser ULTIMO write antes de action_post (descoberto 2026-02-18)
Escrever em `account.bank.statement.line` (partner_id, payment_ref) faz Odoo REGENERAR
as `account.move.line` associadas, revertendo qualquer `account_id` ja escrito.
Ordem dentro do metodo consolidado (ambas versoes):
1. `button_draft`
2. Write `partner_id` + `payment_ref` na statement_line (pode regenerar lines)
3. Write `name` nas move_lines (re-buscar IDs!)
4. Write `account_id` TRANSITORIA→PENDENTES (**ULTIMO!** re-buscar IDs!)
5. `action_post`

---

## Armadilhas de Rota/API

### CNAB400 usa `cnab400_bp` (prefix `/cnab400/`), NAO `financeiro_bp`

### @login_required adicionado em pagamentos_baixas.py e pendencias.py (2026-02-14)
Corrigido: todas as 10 rotas de pagamentos_baixas.py + responder_pendencia agora protegidas.

### exportar_contas_receber_json() e publica (Power Query)
NAO adicionar @login_required — quebra integracao. Cuidado ao expor campos novos.

### Resposta JSON: comprovantes = `'sucesso'` (pt), demais = `'success'` (en)
NAO migrar — frontend depende dos nomes atuais. Manter consistencia DENTRO de cada arquivo.

### Matching: tipo_transacao='saida' -> PagamentoMatchingService, outros -> ExtratoMatchingService

---

## Armadilhas de Worker

### Lock Redis fail-open e INTENCIONAL
Se Redis indisponivel, prossegue sem lock. NAO "corrigir" para return False.

### success agora reflete erros (padronizado 2026-02-14)
Todos workers: `success = erros == 0`. cnab400_batch: parcial = `success=False` com status `'parcial'`.

### ExtratoLote UNIQUE = (statement_id + tipo_transacao)
Mesmo statement gera lote `entrada` + `saida`. NAO usar statement_id sozinho.

### CASCADE assimetrico
ExtratoItemTitulo cascadeia com ExtratoItem. ContasAReceberReconciliacao NAO cascadeia.

### RQ job.started_at e UTC aware (corrigido 2026-02-14)
`job.started_at`/`job.ended_at` sao `datetime` UTC aware (via `rq.utils.now()`).
Para calcular duracao de job em execucao: usar `datetime.now(timezone.utc)`, NAO `agora_utc_naive()`.

---

## Padroes do Modulo

### Constantes centralizadas em `constants.py`
Contas contabeis, journals e mapeamentos Odoo em arquivo unico.
NAO definir constantes Odoo localmente nos services — importar de `constants.py`.

### Context manager `_app_context_safe` em `workers/utils.py`
Workers usam `from app.financeiro.workers.utils import app_context_safe`.
NAO copiar a funcao localmente — importar do modulo compartilhado.

### Imports Odoo sao LAZY
`get_odoo_connection()` importado DENTRO de metodos (18 services). NAO mover para module-level.

---

## Interdependencias

| Importa de | O que | Cuidado |
|-----------|-------|---------|
| `app.odoo.utils.connection` | `get_odoo_connection` | Lazy (dentro de metodos). 18 services usam |
| `app.faturamento.models` | `FaturamentoProduto` | FK checks + filtro nf_cancelada. 7 arquivos |
| `app.monitoramento.models` | `EntregaMonitorada` | Delivery tracking. 5 arquivos |
| `app.embeddings` | `EmbeddingService` | Feature-flagged, lazy. 3 services |
| `app.portal.workers` | `enqueue_job`, `get_queue` | RQ job queue. 8 workers |

| Exporta para | O que | Cuidado |
|-------------|-------|---------|
| `app/__init__.py` | `financeiro_bp`, `cnab400_bp` | Registro de blueprints |
| `app/scheduler/` | 4 sync services | Sincronizacao incremental (cron jobs) |
| `app/monitoramento/routes.py` | `PendenciaFinanceiraNF` | Lazy import condicional |

---

## Skills Relacionadas

| Skill | Opera neste modulo? | O que faz |
|-------|---------------------|-----------|
| **executando-odoo-financeiro** | Sim | Criar payments, reconciliar extratos, baixar titulos |
| **rastreando-odoo** | Parcial | Rastrear NFs, auditar reconciliacoes (leitura) |
| **razao-geral-odoo** | Parcial | Exportar razao geral (account.move.line em massa) |
| **conciliando-odoo-po** | Nao | Opera em POs, mas compartilha `app.odoo.utils` |

### References da Skill executando-odoo-financeiro

| Arquivo | Conteudo |
|---------|----------|
| `SKILL.md` | Decision tree, fluxos, exemplos de codigo |
| `references/erros-comuns.md` | 12 erros comuns com solucoes (Erro 1-12) |
| `references/fluxo-recebimento.md` | Fluxo completo: identificar → criar payment → preparar extrato → reconciliar |
| `references/contas-por-empresa.md` | IDs de contas de juros por company_id |

### Outras referencias

| Referencia | Conteudo |
|-----------|----------|
| `app/financeiro/GOTCHAS.md` | 80+ gotchas detalhados (versao expandida dos A1-A10 acima) |
| `.claude/references/odoo/GOTCHAS.md` | Gotchas Odoo gerais (timeout, conexao, circuit breaker) |
