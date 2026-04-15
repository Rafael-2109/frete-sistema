# CarVia — Fluxos Financeiros

**Referenciado por**: `app/carvia/CLAUDE.md` (regras R11, R16, R17)
**Atualizado**: 2026-04-15

Cobre: conciliacao bancaria, propagacao FT→CE, pre-vinculo extrato↔cotacao (frete pre-pago) e historico de match aprendido (boost de scoring).

---

## Conciliacao Quita Titulo (R11)

Conciliacao 100% de um documento altera AUTOMATICAMENTE o status de pagamento:

| Documento | Campo | Novo valor | Campos auditoria |
|-----------|-------|-----------|------------------|
| `CarviaFaturaCliente` | `status` | `PAGA` | `pago_em`, `pago_por` |
| `CarviaFaturaTransportadora` | `status_pagamento` | `PAGO` | `pago_em`, `pago_por` |
| `CarviaDespesa` | `status` | `PAGO` | `pago_em`, `pago_por` |
| `CarviaCustoEntrega` | `status` | `PAGO` | `pago_em`, `pago_por` (apenas se `fatura_transportadora_id IS NULL`) |
| `CarviaReceita` | `status` | `RECEBIDO` | `recebido_em`, `recebido_por` |

**Desconciliacao** reverte tudo: status → `PENDENTE`, limpa campos `pago_em`/`pago_por`.

### Propagacao FT → CE (Custos de Entrega)

Quando uma `CarviaFaturaTransportadora` e paga via conciliacao, `_propagar_status_ces_cobertos()` busca todos os CEs vinculados via `fatura_transportadora_id=ft.id` e marca:

```
CE.status = 'PAGO'
CE.pago_por = 'auto:...'
```

**Desconciliacao da FT** reverte os CEs auto-propagados:
```
CE.status = 'VINCULADO_FT'  (mantem FK, volta status)
```

**Integridade CE↔FT**: se `CE.fatura_transportadora_id IS NOT NULL`, o CE fica **bloqueado** para conciliacao direta — so pode ser pago via propagacao automatica da FT. Isso evita pagamento duplo.

---

## Pre-Vinculo Extrato ↔ Cotacao (R16 — frete pre-pago)

### Problema

Clientes CarVia frequentemente pagam fretes **antecipadamente**, gerando linhas de extrato bancario "orfas" (`status_conciliacao=PENDENTE` sem documento para conciliar). Quando a `CarviaFaturaCliente` e finalmente emitida, fica dificil identificar qual linha bancaria corresponde a qual fatura no meio de outras transacoes.

### Solucao — Tabela lateral SOFT

Modelo: `CarviaPreVinculoExtratoCotacao` em `app/carvia/models/financeiro.py`.

**Proposito**: permite o usuario proativamente vincular uma linha de extrato a uma cotacao APROVADA na tela de detalhe (`cotacoes/detalhe.html`).

**Caracteristicas**:
- Vinculo **SOFT** — a linha de extrato permanece `status_conciliacao=PENDENTE`
- NAO e uma `CarviaConciliacao` (nao polui o modelo central de conciliacao financeira)
- Apenas 1 pre-vinculo `ATIVO` por par `(linha, cotacao)` — UNIQUE parcial `WHERE status='ATIVO'`

### Fluxo de Status

```
ATIVO -> RESOLVIDO (automatico quando fatura chega via trigger)
ATIVO -> CANCELADO (usuario desfaz manualmente com motivo)
```

Cancelamento de `RESOLVIDO` e **bloqueado** — o usuario deve primeiro desfazer a conciliacao real via Extrato Bancario.

### Trigger de Resolucao Automatica

`CarviaPreVinculoService.resolver_para_fatura` e chamado em **4 pontos** de `fatura_routes.py` (try/except nao-bloqueante) apos criar/editar fatura cliente. Percorre a cadeia:

```
CarviaFaturaClienteItem.nf_id
  → CarviaNf.numero_nf
  → CarviaPedidoItem.numero_nf (STRING MATCH — gap Refator 2.5)
  → CarviaPedido.cotacao_id
  → CarviaCotacao
```

Para cada cotacao encontrada com pre-vinculo ATIVO:
1. Cria `CarviaConciliacao` real (`tipo_documento='fatura_cliente'`)
2. Marca pre-vinculo como `RESOLVIDO`
3. Preenche `conciliacao_id` + `fatura_cliente_id` para audit trail

### Botao Manual "Resolver Pre-Vinculos"

No extrato bancario, chama `tentar_resolver_todos_ativos(usuario, dias_lookback=90)` que varre pre-vinculos `ATIVO` e tenta resolver contra faturas cliente dos ultimos 90 dias. Cobre casos tardios (NF anexada ao pedido **apos** fatura ja criada).

### Constraints

- **Linha**: deve ser CREDITO (pagamento entrante), status `IN (PENDENTE, PARCIAL)`
- **Cotacao**: deve estar `APROVADO`
- **Hook nao-bloqueante**: se `resolver_para_fatura` falha (session issue, cadeia ambigua), a criacao da fatura segue normal

### Artefatos

| Componente | Arquivo |
|------------|---------|
| Service | `app/carvia/services/financeiro/previnculo_service.py` (7 metodos) |
| Rotas | `conciliacao_routes.py` — 5 endpoints em `/api/cotacoes/<id>/...` e `/api/previnculos/...` |
| Templates | `_modal_previncular_extrato.html`, `_previnculos_cotacao.html`, includes em `cotacoes/detalhe.html` |

---

## Historico de Match Extrato ↔ Pagador (R17 — append-only)

### Proposito

Conciliacoes de `fatura_cliente` sao **material de aprendizado**: a cada conciliacao criada, o sistema grava um evento novo em `CarviaHistoricoMatchExtrato` com a chave `(descricao_tokens, cnpj_pagador)` para reutilizar em sugestoes futuras.

### Como a chave e formada

- `descricao_tokens` = tokens normalizados da **linha de cima** do extrato (`CarviaExtratoLinha.descricao`) via `_normalizar()` do sugestao_service
- `cnpj_pagador` = `CarviaFaturaCliente.cnpj_cliente` (pagador efetivo da fatura)

### Tabela e append-only (sem UNIQUE)

1 descricao pode fazer match com N CNPJs (e vice-versa). Contagem de ocorrencias e via `COUNT(*) GROUP BY cnpj_pagador` na consulta. **Sem UniqueViolation por design.**

### Boost no Scoring

`pontuar_documentos()` aceita parametro opcional `cnpjs_historico` (dict `{cnpj: ocorrencias}`). Quando um doc sugerido tem `cnpj_cliente` presente no dict, o score recebe boost multiplicativo:

```python
score = min(1.0, score * 1.4)
```

Preserva a calibracao dos 3 sinais originais (valor 50% / data 30% / nome 20%) — so potencializa docs que ja foram conciliados antes para a mesma descricao de extrato.

### Escopo Atual

Apenas `fatura_cliente` (CREDITO/recebimento). O modelo tem campo `tipo_documento` preparado para extensao futura (fatura_transportadora, despesa, custo_entrega, receita).

### Hook Nao-Bloqueante

`registrar_aprendizado()` e chamado dentro de try/except em `conciliar()` — qualquer erro (tabela ausente, cnpj vazio, tokens vazios) apenas loga warning e segue. **Desconciliar NAO remove eventos** (historico e cumulativo, append-only).

### Callsites que Aplicam Boost

| Callsite | Contexto |
|----------|----------|
| `conciliacao_routes.py::api_documentos_elegiveis` | Tela dual-panel |
| `conciliacao_routes.py::api_matches_linha` | Modal inline Extrato Bancario |
| `previnculo_service.py::listar_candidatos_extrato` | Pre-vinculo cotacao (com `cnpj_cliente` via `cotacao.cliente.cnpj`) |

**Fora do escopo**: `api_matches_por_documento` (fluxo inverso doc→linhas) usa scoring inline proprio e NAO foi modificado — requer refator separado.

### Artefatos

| Componente | Arquivo |
|------------|---------|
| Service | `app/carvia/services/financeiro/carvia_historico_match_service.py` |
| Model | `CarviaHistoricoMatchExtrato` (pacote `models/financeiro.py`) |
| Tabela | `carvia_historico_match_extrato` (append-only log, sem UNIQUE) |
| Migration | `scripts/migrations/add_carvia_historico_match_extrato.{py,sql}` |
| UI badge | `<i class="fas fa-history">` em `_modal_conciliar_inline.html` quando `doc.score_historico=true` |

---

## Conciliacao — Telas e Rotas

| Tela | URL | Funcao |
|------|-----|--------|
| Painel Conciliacao | `/carvia/conciliacao` | Dual-panel extrato/documentos + match |
| Extrato Bancario | `/carvia/extrato-bancario` | Importar OFX/CSV, lista linhas |
| Extrato da Conta | `/carvia/extrato-conta` | Movimentacoes com saldo acumulado |
| Fluxo de Caixa | `/carvia/fluxo-de-caixa` | Accordions por dia + Pagar/Desfazer |

**Modelo central**: `CarviaConciliacao` (junction N:N extrato↔documento) com `UNIQUE(extrato_linha_id, tipo_documento, documento_id)`. `valor_alocado` sempre positivo.
