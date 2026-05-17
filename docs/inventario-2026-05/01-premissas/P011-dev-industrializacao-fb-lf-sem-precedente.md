# P011 — dev-industrializacao FB↔LF: fiscal_position por simetria com CD↔LF

**Data:** 2026-05-17
**Decidida por:** Rafael (resposta usuário 17/05)
**Origem:** descoberta G003 (`docs/inventario-2026-05/02-gotchas/G003-cfop-real-divergente-do-prompt.md`)

## Premissa

Direções `(1, 5)` (FB → LF) e `(5, 1)` (LF → FB) para `dev-industrializacao` **não têm precedente histórico** no Odoo. Decisão do dono do projeto: emitir LF→FB e FB→LF **diretamente como 1 NF** (sem cadeia LF→CD→FB), criando o primeiro registro histórico.

Como **não temos** fiscal_position_id real para essas direções, **assumir por simetria com as direções precedentes**:

| Direção sem precedente | Direção espelho (com precedente) | `fiscal_position_id` assumido | Racional |
|---|---|---|---|
| `(1, 5)` FB → LF | `(4, 5)` CD → LF | **74** (SAÍDA - REMESSA P/ RETRABALHO) | Mesma natureza fiscal: saída para retrabalho na LF |
| `(5, 1)` LF → FB | `(5, 4)` LF → CD | **89** (SAÍDA - RETRABALHO) | Mesma natureza fiscal: devolução da LF para origem |

## CFOP esperado

`5949` (saída intra-estadual). Mesmo CFOP de CD↔LF, pois todas as 3 empresas em Santana de Parnaíba/SP.

## Risco

- Contadora pode questionar a operação por ausência de precedente.
- Se fiscal_position_id 74/89 não for válida em FB ou LF (limitações por empresa), Odoo levanta erro ao emitir.

## Mitigação

1. **Canary fiscal obrigatório** antes de bulk: emitir 1 NF de teste em cada direção e validar com contadora.
2. Se Odoo recusar fiscal_position por restrição de empresa, investigar `fiscal_position` válida em FB/LF e atualizar `MATRIZ_INTERCOMPANY`.
3. Logar a decisão no payload da NF (campo `ref` ou `narration`).

## Status

Ativa até primeira NF emitida com sucesso (vira fato) OU contadora orientar diferente.
