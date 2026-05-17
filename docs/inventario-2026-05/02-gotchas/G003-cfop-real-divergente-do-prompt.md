# G003 — CFOP real no Odoo diverge do prompt original

**Descoberto em:** 2026-05-17 (audit 00c)
**Severidade:** ALTA — afeta a definição de `MATRIZ_INTERCOMPANY`

## Contexto

O prompt original (`app/agente/prompts/prompt_inventario.md:101-108`) diz:

```
- "industrializacao" - Saída da FB para LF de produtos [1,2,3] CFOP [5901]
- "perda" - Saída da LF para FB de produtos [1,2,3] CFOP [5903]
- "dev-industrializacao" - Saída entre [FB,LF] de produto [4] CFOP [5949]
- "transf-filial" - Transferencia entre [CD,FB] CFOP [5152]
```

## Achado em 00c (5 NFs recentes por direção)

| Direção | `l10n_br_tipo_pedido` | CFOP real | `fiscal_position_id` | Nome típico |
|---|---|---|---|---|
| **transf-filial CD→FB** | `transf-filial` | **`5151`** ≠ 5152 | 49 SAÍDA - TRANSFERÊNCIA ENTRE FILIAIS | SDTRA/2026/* |
| **dev-industrializacao FB→LF** | `dev-industrializacao` | **`6902`** ≠ 5949 | 128 SAIDA - PRODUTO INDUSTRIALIZADO | SPI/2026/* |
| **dev-industrializacao LF→FB** | `dev-industrializacao` | `5949` ✅ | 89 SAÍDA - RETRABALHO | SARET/2026/* |
| **dev-industrializacao LF→CD** | `dev-industrializacao` | `5949` ✅ | 89 SAÍDA - RETRABALHO | SARET/2026/* |
| **transf-filial FB→CD** (D001) | `transf-filial` | `5152` ✅ | 20 SAÍDA - TRANSFERÊNCIA ENTRE FILIAIS | SDTRA/2026/00832 (NF 94410) |

## Análise

### 1. transf-filial: 5151 ≠ 5152

- `5152` = Transferência de mercadoria **adquirida ou recebida de terceiros** (mercadoria comprada)
- `5151` = Transferência de **produção do estabelecimento** (mercadoria produzida)

CD→FB usa 5151 porque CD é centro de distribuição (recebe produção da FB) e transfere de volta para FB como "produção". O sistema escolhe automaticamente com base no `fiscal_position_id`.

**Implicação para inventário**: `transf-filial` pode usar **5151 OU 5152** dependendo da origem da mercadoria. `account_move_intercompany_service` precisa deixar o Odoo decidir via `fiscal_position_id` ao invés de hardcodar CFOP.

### 2. dev-industrializacao: 5949 vs 6902 (CFOP estadual vs interestadual)

- `5949` = Saída intra-estadual
- `6902` = **Saída interestadual** de produto industrializado

FB→LF usa 6902 porque é **interestadual** (FB e LF em estados diferentes). LF→FB usa 5949 porque LF e FB... espera, se FB→LF é interestadual, LF→FB também deveria ser. Mas o sistema usa 5949 (intra-estadual) em LF→FB.

Possíveis explicações:
- (a) LF e FB ficam no mesmo estado mas direção FB→LF é registrada como interestadual por outro motivo (tipo de operação)
- (b) FB tem mais de um endereço; transferência FB-LF pode ser de uma filial específica
- (c) A operação "SAIDA - PRODUTO INDUSTRIALIZADO" tem regra fiscal própria que sobrescreve

**Decisão pragmática**: deixar o Odoo decidir o CFOP a partir de `l10n_br_tipo_pedido` + `fiscal_position_id`. Não hardcodar.

### 3. Operações "dev-industrializacao" são 3 distintas

- CD→LF (retrabalho intra-estadual, fiscal_pos 74)
- FB→LF (saída interestadual produto industrializado, fiscal_pos 128)
- LF→origem (devolução retrabalho, fiscal_pos 89)

Cada uma tem `fiscal_position_id` diferente. `MATRIZ_INTERCOMPANY['dev-industrializacao']['fiscal_position_id']` precisa de chave composta `(company_origem, company_destino)` ou `(company_origem, 'INTRA'|'INTER')`.

## Decisões propostas

### Decisão 1 — Trocar `cfop` em `MATRIZ_INTERCOMPANY` por `fiscal_position_id` como chave principal

`account_move_intercompany_service.executar()` **não seta CFOP** diretamente. Apenas:
- `move_type`
- `l10n_br_tipo_pedido`
- `partner_id`
- `company_id`
- `fiscal_position_id`

Odoo resolve CFOP automaticamente via posição fiscal + endereço do partner.

### Decisão 2 — Estrutura `fiscal_position_id` por `(company_origem, company_destino)`

```python
'dev-industrializacao': {
    'l10n_br_tipo_pedido': 'dev-industrializacao',
    'move_type': 'out_invoice',
    'tipo_produto': [4],
    'fiscal_position_id': {
        # (company_origem, company_destino): fiscal_position_id
        (1, 5): 128,  # FB → LF: SAIDA - PRODUTO INDUSTRIALIZADO (6902)
        (4, 5): 74,   # CD → LF: SAÍDA - REMESSA PARA RETRABALHO (5949)
        (5, 1): 89,   # LF → FB: SAÍDA - RETRABALHO (5949)
        (5, 4): 89,   # LF → CD: SAÍDA - RETRABALHO (5949)
    },
    'nf_referencia_por_direcao': {
        (4, 5): {'account_move_id': 590839, 'nf_numero': 147772},
        (1, 5): {'account_move_id': 559045},  # SPI/2026/00007 (achado em 00c)
        (5, 1): {'account_move_id': 606403},  # SARET/2026/00002
    },
},
```

Mesma estrutura para `transf-filial`:

```python
'transf-filial': {
    'fiscal_position_id': {
        (1, 4): 20,  # FB → CD: SAÍDA - TRANSFERÊNCIA ENTRE FILIAIS (5152)
        (4, 1): 49,  # CD → FB: SAÍDA - TRANSFERÊNCIA ENTRE FILIAIS (5151)
    },
    ...
},
```

### Decisão 3 — `cfop` no MATRIZ_INTERCOMPANY vira informacional (não usado pelo service)

Mantém para documentação humana, com nota: "real é decidido pelo Odoo a partir do `fiscal_position_id`".

## Ação

1. Atualizar `MATRIZ_INTERCOMPANY` no spec §5.2 e §6.3 para chave `(origem, destino)` de fiscal_position_id
2. `account_move_intercompany_service.executar()` resolve fiscal_position_id via `(company_origem, company_destino)`
3. NÃO setar CFOP no payload — deixar Odoo computar
4. Validar essa decisão com Rafael antes da Fase 1 (impacta o design dos services)
