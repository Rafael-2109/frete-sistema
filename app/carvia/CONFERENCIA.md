# CarVia — Conferencia e Bifurcacao Venda/Compra

**Referenciado por**: `app/carvia/CLAUDE.md` (regras R3, R4)
**Atualizado**: 2026-04-15

CarVia opera em **2 dominios independentes** (venda vs compra) com **conferencia assimetrica** — automatica do lado compra, manual do lado venda. Este documento cobre: bifurcacao de dominio, lifecycle de status, conferencia de `CarviaFrete` (Phase C — 2026-04-14), e gates da `CarviaFaturaTransportadora`.

---

## Bifurcacao Venda/Compra

Comentada explicitamente em `app/carvia/models/frete.py:12-19` — "2 lados: CUSTO + VENDA".

| Dominio | Artefatos | Precificacao | Conferencia | Gate de emissao |
|---------|-----------|--------------|-------------|-----------------|
| **Compra** (custo) | `CarviaFrete` → `CarviaFaturaTransportadora` | Tabela Nacom | **Automatica** via `ConferenciaService` operando no Frete | Gate 1 + Gate 2 (ver abaixo) |
| **Venda** (receita) | `CarviaOperacao` → `CarviaFaturaCliente` | Tabela CarVia | **Manual** gerencial binaria (Refator 2.1) | Nenhum gate — decisao humana com auditoria |

**Regra fundamental**: os dois dominios **NAO tem relacao de bloqueio**. Fatura cliente pode ser emitida com subs/fretes em qualquer status de conferencia. Pagamento (`status=PAGA`) e **INDEPENDENTE** da conferencia gerencial (`status_conferencia=CONFERIDO`).

**Regra de ouro das tabelas** (usada em `CarviaFreteService._criar_frete_completo()`):
- Tabela **CARVIA** (preco VENDA) → `CarViaTabelaService.cotar_carvia()` → `CarviaOperacao.cte_valor`
- Tabela **NACOM** (preco CUSTO) → `CotacaoService.cotar_subcontrato()` → `CarviaSubcontrato.valor_cotado` / `CarviaFrete.valor_cotado`

---

## Lifecycle de Status (irreversivel exceto cancelamento)

```
CTe CarVia:         RASCUNHO → COTADO → CONFIRMADO → FATURADO    [CANCELADO exceto FATURADO]
CTe Subcontrato:    PENDENTE → COTADO → CONFIRMADO → FATURADO → CONFERIDO  [CANCELADO exceto FATURADO]
CTe Complementar:   RASCUNHO → EMITIDO → FATURADO                [CANCELADO exceto FATURADO]
Custo Entrega:      PENDENTE → VINCULADO_FT → PAGO               [CANCELADO exceto PAGO via fluxo caixa]
```

**NUNCA mover status para tras** (ex: CONFIRMADO → COTADO). Cancelar e criar novo.

---

## Conferencia de CarviaFrete (Phase C — 2026-04-14)

**Frete = unidade de analise**. Os campos de conferencia sao colunas de `CarviaFrete`, NAO mais de `CarviaSubcontrato` (ver migration `carvia_drop_sub_conferencia_fields`).

| Campo no `CarviaFrete` | Tipo | Descricao |
|-----------------------|------|-----------|
| `status_conferencia` | String | `PENDENTE → APROVADO \| DIVERGENTE` |
| `conferido_por` | String | Usuario responsavel |
| `conferido_em` | DateTime | Naive UTC |
| `valor_considerado` | Numeric(15,2) | Valor CONFIRMADO para este frete |
| `valor_pago` | Numeric(15,2) | Valor pago efetivo (pode diferir) |
| `detalhes_conferencia` | JSONB | Snapshot de calculo |
| `requer_aprovacao` | Boolean | Flag para tratativa com chefe |

### Cascade de status_conferencia da Fatura Transportadora

A Fatura Transportadora consolida os fretes vinculados:

```
Todos os fretes APROVADO     → Fatura.status_conferencia = CONFERIDO (auto)
Algum frete DIVERGENTE       → Fatura.status_conferencia = DIVERGENTE
Mix APROVADO + PENDENTE      → Fatura.status_conferencia = EM_CONFERENCIA
```

### Gates para aprovar FT manualmente

Fatura Transportadora so aceita `CONFERIDO` manual se:

**Gate 1** — Todos os fretes vinculados tem `status_conferencia = APROVADO`
**Gate 2** — Paridade de valor (tolerancia R$ 1,00):
```
abs(fatura.valor_total - (sum(frete.valor_considerado) + sum(ce.valor))) <= 1.00
```
Onde CEs sao os `CarviaCustoEntrega` ligados a esta FT via `fatura_transportadora_id`.

---

## Conferencia Gerencial da Fatura Cliente (Refator 2.1)

**Manual puro, sem gate automatico.**

```
FaturaCliente.status_conferencia:  PENDENTE → CONFERIDO  (binario, manual)
```

**Ao aprovar** (`POST /faturas-cliente/<id>/aprovar`): grava `conferido_por`, `conferido_em`, `observacoes_conferencia`.

**Apos CONFERIDO**, `pode_editar()` bloqueia TODAS as alteracoes:
- Desanexar operacao
- Editar valor
- Alterar campos qualquer

**Reabertura**: `POST /faturas-cliente/<id>/reabrir-conferencia` (exige motivo). Audit trail em `CarviaAdminAudit` se operacao admin.

---

## Services e Artefatos

| Componente | Arquivo | Funcao |
|------------|---------|--------|
| Service de conferencia | `app/carvia/services/documentos/conferencia_service.py` | Calcular + registrar conferencia no Frete |
| Service de aprovacoes | `app/carvia/services/documentos/aprovacao_frete_service.py` (ex-`AprovacaoSubcontratoService`) | Tratativas de requer_aprovacao |
| Tabela satelite | `carvia_aprovacoes_frete` (ex-`carvia_aprovacoes_subcontrato`) | FK `frete_id` (Phase 14) |
| API conferencia frete | `POST /carvia/api/conferencia-subcontrato/<id>/calcular`, `.../registrar` | Calcular e persistir (nome legado, opera em Frete) |
| API conferencia fatura | `POST /carvia/faturas-transportadora/<id>/conferencia` | Com Gate 1 + Gate 2 |

---

## peso_utilizado (entrada para cotacao)

`peso_utilizado = max(peso_bruto, peso_cubado)` — regra das transportadoras.

**SEMPRE chamar** `operacao.calcular_peso_utilizado()` apos alterar `peso_bruto` ou `peso_cubado`. Valor stale = cotacao errada.

Conceitos distintos (NAO confundir):
- `peso_bruto`: peso real na balanca
- `peso_cubado`: peso volumetrico (dimensoes × fator cubagem)
- `peso_utilizado`: o MAIOR entre os dois

**Distribuicao de peso entre itens e PROPORCIONAL**, NAO exata por unidade. Ex: 3 motos de 100kg cada num CTe de 350kg (embalagem) → cada moto = 350/3 = 116.67kg, NAO 100kg.
