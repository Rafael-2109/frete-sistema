# CarVia — Fluxos de Criacao de Fretes

**Referenciado por**: `app/carvia/CLAUDE.md` (regras R10, R12, R13)
**Atualizado**: 2026-04-15

Cobre: orquestrador `CarviaFreteService`, hook da portaria, fluxo unico cotacao→embarque→portaria, condicoes comerciais e deprecacao do wizard manual.

---

## Fluxo Unico (Cotacao → Embarque → Portaria → Frete)

Novos fretes CarVia DEVEM passar pelo pipeline:

```
CarViaCotacao
  ↓ (aprovacao)
CarViaPedido
  ↓ (embarque provisorio)
Embarque
  ↓ (NF emitida)
NF
  ↓ (saida da portaria)
PortariaRegistroEntradaSaida
  ↓ (hook nao-bloqueante)
CarviaFreteService.lancar_frete_carvia()
  ↓ (atomico, por grupo cnpj_emitente + cnpj_destino)
CarviaOperacao + CarviaOperacaoNf + CarviaSubcontrato + CarviaFrete
```

**Criacao manual** de `CarviaOperacao` (wizard/freteiro) e **DEPRECATED** para novos fluxos. Templates `criar_manual.html` e `criar_freteiro.html` exibem alerta de deprecacao.

---

## CarviaFreteService (Orquestrador)

Hook em `portaria/routes.py` chama `CarviaFreteService.lancar_frete_carvia()` — **orquestrador unico** que cria os 4 artefatos em sequencia atomica:

```
1. CarviaOperacao   (CTe CarVia — lado VENDA)
2. CarviaOperacaoNf (junctions NF → Operacao)
3. CarviaSubcontrato (lado CUSTO)
4. CarviaFrete      (operacao_id + subcontrato_id JA populados)
```

### Regras de precificacao

- **VENDA**: `CarViaTabelaService.cotar_carvia()` → `CarviaOperacao.cte_valor`
- **CUSTO**:
  - DIRETA = rateio proporcional (`frete_total × peso_grupo / peso_embarque`)
  - FRACIONADA = `CotacaoService.cotar_subcontrato()` → `CarviaSubcontrato.valor_cotado`

### Deduplicacao

Unique constraint `(embarque_id, cnpj_emitente, cnpj_destino)` no banco previne dupla gravacao.

### NF tardia

Se o `CarviaFrete` ja existe para aquele grupo, o orquestrador **ATUALIZA** totais (nao duplica).

### Nao-bloqueante

Try/except no hook garante que falha no `CarviaFreteService` **nao impede** o registro de saida da portaria.

### Efeitos colaterais

- `CarviaPedido.status` → `EMBARCADO` apos processamento
- Vinculacao retroativa a faturas: ao criar fatura, `CarviaFrete.fatura_*_id` e atualizado

---

## Importacao de CTe Enriquece (nao duplica)

Quando um CTe e importado depois do auto-lancamento pela portaria, o sistema **enriquece** a operacao/subcontrato auto-gerado em vez de criar duplicata:

- **CTe CarVia**: busca operacao `AUTO_PORTARIA` pelas mesmas NFs → se encontra, preenche campos do CTe real
- **CTe Subcontrato**: busca sub auto pelo mesmo `(operacao, transportadora)` → se encontra, preenche campos

**Vinculacao a Fatura permanece MANUAL** (R5 do CLAUDE.md):
- **Fatura Subcontrato**: criada primeiro, depois subcontratos anexados via AJAX
- **Fatura CarVia**: criada vinculando operacoes (CTe antes de Fatura)

---

## Classificacao de CTe por CNPJ Emitente (R6)

Na importacao, CTes sao classificados automaticamente:

- CNPJ emitente == `CARVIA_CNPJ` (env var) → **CTe CarVia** (`CarviaOperacao`)
- CNPJ emitente != `CARVIA_CNPJ` → **CTe Subcontrato** (`CarviaSubcontrato`)

Se `CARVIA_CNPJ` nao configurado: todos CTes tratados como CarVia (compatibilidade legada com alerta).

---

## Numeracao Sequencial (R7 e R8)

### CarviaSubcontrato — sequencial por transportadora

Cada subcontrato recebe `numero_sequencial_transportadora` via `MAX(numero_sequencial_transportadora) + 1` filtrado por `transportadora_id`.

Unique index parcial: `(transportadora_id, numero_sequencial_transportadora) WHERE NOT NULL`.

### CTe-### e Sub-###

- `CarviaOperacao.cte_numero` = `CTe-001`, `CTe-002`, ... via `gerar_numero_cte()` (static method)
- `CarviaSubcontrato.cte_numero` = `Sub-001`, `Sub-002`, ... via `gerar_numero_sub()` (static method)

Campo `cte_numero VARCHAR(20)` ja existia — implementacao foi apenas backfill.

**Backfill**: `scripts/migrations/backfill_numeracao_sequencial_carvia.py`.

**Identificador unificado para UI** (via macro `carvia_ref`): `CTe-### | CTRC SSW {ctrc_numero}` — ver `SSW_INTEGRATION.md`.

---

## Condicoes Comerciais (R13)

Cotacoes CarVia possuem **5 campos** de controle financeiro:

| Campo | Valores | Observacao |
|-------|---------|------------|
| `condicao_pagamento` | `A_VISTA` / `PRAZO` | — |
| `prazo_dias` | 1-30 | Apenas se `PRAZO` |
| `responsavel_frete` | `100_REMETENTE` / `100_DESTINATARIO` / `50_50` / `PERSONALIZADO` | — |
| `percentual_remetente` | Numeric(5,2) | SEMPRE persistido (ex: 50/50 grava 50.00 e 50.00) |
| `percentual_destinatario` | Numeric(5,2) | idem |

### Propagacao

**Automatica**: `CarviaCotacao` → `CarviaFrete` via `CarviaFreteService._criar_frete_completo()`.

**Campos fisicamente presentes** em:
- `carvia_cotacoes`
- `carvia_operacoes` (mas **NAO sao populados automaticamente** — reservados para uso futuro)
- `carvia_fretes`

**`CarviaFaturaCliente` NAO tem** os campos — exibicao via lookup (fatura → operacoes → fretes).

### Regras de uso

- Campos sao **INFORMATIVOS** — nao bloqueiam transicao de status em nenhum fluxo
- Conciliacao exibe condicoes comerciais como info extra (sem alterar matching)

---

## Estrutura de Telas (Orientacao)

Para criar/editar telas, referencia rapida:

| Entidade | URL base | Principais telas |
|----------|----------|------------------|
| `CarviaNf` | `/carvia/nfs` | Lista, detalhe (com itens) |
| `CarviaOperacao` | `/carvia/operacoes` | Lista, detalhe, criar/editar |
| `CarviaSubcontrato` | `/carvia/subcontratos` | Lista, detalhe |
| `CarviaCteComplementar` | `/carvia/ctes-complementares` | Lista, criar (via operacao), detalhe, editar |
| `CarviaCustoEntrega` | `/carvia/custos-entrega` + `/carvia/despesas-extras` | Lista, criar, detalhe (anexos AJAX), editar |
| `CarviaFaturaCliente` | `/carvia/faturas-cliente` | Lista, nova (operacoes + CTe Comp), detalhe |
| `CarviaFaturaTransportadora` | `/carvia/faturas-transportadora` | Lista, nova, detalhe |
| `CarviaDespesa` | `/carvia/despesas` | Lista, criar, detalhe, editar |
| Importacao | `/carvia/importar` | Upload + review + confirmar |
| Admin | `/carvia/admin/auditoria` | Hard delete, edicao, conversao, re-link (`AUDIT_ADMIN_SERVICE.md`) |
| Configuracoes | `/carvia/configuracoes/modelos-moto` | CRUD inline modelos/empresas/categorias moto |

**Template do wizard criar CTe** (`criar_manual.html`): 2 cards (NFs + Valor R$). **DEPRECATED** — use o fluxo unico via portaria.

**Criar CTe via NF** (`POST /carvia/nfs/<id>/criar-cte`): modal no detalhe da NF, popula automaticamente cliente/destino/peso/valor. Cria operacao 1:1 a partir da NF.

**Autocomplete Transportadora**: input com debounce 300ms + dropdown `.carvia-autocomplete-results`. Busca via `GET /carvia/api/opcoes-transportadora?busca=X&uf_destino=Y`. Ultimo item fixo "Criar Nova Transportadora" → modal `#modalCriarTransportadora` → `POST /carvia/api/cadastrar-transportadora` (auto-seleciona apos cadastro).
